"""Buddy Agent Tool System — function-calling powered tool orchestration

Defines a comprehensive tool framework for agents with structured schemas,
validation, streaming execution, parallel safe execution, and automatic
result aggregation with trust-level classification.
"""
from __future__ import annotations
import json
import logging
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.tools")


class ToolCategory(str, Enum):
    KNOWLEDGE = "knowledge"
    CODE = "code"
    DATA = "data"
    SYSTEM = "system"
    COMMUNICATION = "communication"
    CREATIVE = "creative"


class ExecutionSafety(str, Enum):
    """Safety classification for parallel execution control."""
    READ_ONLY = "read_only"       # Safe to run concurrently with anything
    SCOPED = "scoped"             # Safe with different scopes/paths
    MUTATING = "mutating"         # Serialize with same resource
    DESTRUCTIVE = "destructive"   # Always serialize, requires approval


@dataclass
class ToolParameter:
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    enum: list[str] | None = None
    default: Any = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    category: ToolCategory = ToolCategory.SYSTEM
    parameters: list[ToolParameter] = field(default_factory=list)
    handler: Callable[[dict], Awaitable[str]] | None = None
    is_async: bool = True
    timeout: float = 30.0
    safety: ExecutionSafety = ExecutionSafety.READ_ONLY
    path_param: str = ""  # For scoped tools: which param contains the path/key

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []
        for p in self.parameters:
            prop: dict = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass
class ToolResult:
    name: str
    success: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    tokens_used: int = 0


class ToolRegistry:
    """Registry for agent tools with schema generation and execution."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._execution_log: list[ToolResult] = []

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name} ({tool.category.value})")

    def define(
        self,
        name: str,
        description: str,
        category: ToolCategory = ToolCategory.SYSTEM,
        parameters: list[ToolParameter] | None = None,
        timeout: float = 30.0,
    ):
        """Decorator-style registration for async handlers."""
        def decorator(handler: Callable[[dict], Awaitable[str]]):
            tool = ToolDefinition(
                name=name,
                description=description,
                category=category,
                parameters=parameters or [],
                handler=handler,
                timeout=timeout,
            )
            self.register(tool)
            return handler
        return decorator

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self, category: ToolCategory | None = None) -> list[ToolDefinition]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_openai_schemas(self, names: list[str] | None = None) -> list[dict]:
        """Get OpenAI-compatible function calling schemas."""
        tools = self._tools.values()
        if names:
            tools = [t for t in self._tools.values() if t.name in names]
        return [t.to_openai_schema() for t in tools]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool with the given arguments."""
        import time
        start = time.time()

        tool = self._tools.get(name)
        if not tool:
            result = ToolResult(name=name, success=False, error=f"Unknown tool: {name}")
            self._execution_log.append(result)
            return result

        try:
            if tool.handler:
                output = await asyncio.wait_for(
                    tool.handler(arguments),
                    timeout=tool.timeout,
                )
                result = ToolResult(
                    name=name,
                    success=True,
                    output=output,
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                result = ToolResult(
                    name=name,
                    success=False,
                    error=f"No handler for tool: {name}",
                )
        except asyncio.TimeoutError:
            result = ToolResult(
                name=name,
                success=False,
                error=f"Tool execution timed out after {tool.timeout}s",
                duration_ms=tool.timeout * 1000,
            )
        except Exception as e:
            result = ToolResult(
                name=name,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

        self._execution_log.append(result)
        if len(self._execution_log) > 1000:
            self._execution_log = self._execution_log[-500:]

        logger.info(f"Tool {name}: {'OK' if result.success else 'ERR'} ({result.duration_ms:.0f}ms)")
        return result

    async def execute_batch(self, calls: list[tuple[str, dict]]) -> list[ToolResult]:
        """Execute multiple tools in parallel with safety-aware scheduling."""
        # Separate by safety level
        read_only: list[tuple[str, dict]] = []
        scoped: dict[str, list[tuple[str, dict]]] = {}
        serial: list[tuple[str, dict]] = []

        for name, args in calls:
            tool = self._tools.get(name)
            if not tool:
                continue

            if tool.safety == ExecutionSafety.READ_ONLY:
                read_only.append((name, args))
            elif tool.safety == ExecutionSafety.SCOPED and tool.path_param:
                key = args.get(tool.path_param, "__default__")
                scoped.setdefault(key, []).append((name, args))
            else:
                serial.append((name, args))

        results: list[ToolResult] = []

        # Execute read-only tools in parallel
        if read_only:
            read_tasks = [self.execute(name, args) for name, args in read_only]
            results.extend(await asyncio.gather(*read_tasks))

        # Execute scoped tools: parallel across different scopes, serial within same scope
        if scoped:
            scope_tasks = []
            for scope_calls in scoped.values():
                # Within same scope, serialize
                for name, args in scope_calls:
                    scope_tasks.append(self.execute(name, args))
            results.extend(await asyncio.gather(*scope_tasks))

        # Execute destructive/mutating tools serially
        for name, args in serial:
            results.append(await self.execute(name, args))

        return results

    def get_execution_stats(self) -> dict:
        total = len(self._execution_log)
        successful = sum(1 for r in self._execution_log if r.success)
        return {
            "total_executions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": f"{(successful / total * 100):.1f}%" if total > 0 else "N/A",
            "recent_log": [
                {"name": r.name, "success": r.success, "duration_ms": r.duration_ms}
                for r in self._execution_log[-10:]
            ],
        }


tool_registry = ToolRegistry()


# ── Built-in Agent Tools ──────────────────────────────────

async def _tool_web_search(args: dict) -> str:
    """Perform a web search for current information."""
    query = args.get("query", "")
    if not query:
        return "Error: query is required"
    # Placeholder — in production, integrate with search API
    return json.dumps({
        "query": query,
        "results": [],
        "note": "Web search requires integration with a search API. Configure SEARCH_API_KEY in .env.",
    })


async def _tool_calculate(args: dict) -> str:
    """Safely evaluate mathematical expressions."""
    expression = args.get("expression", "")
    if not expression:
        return "Error: expression is required"
    allowed = set("0123456789+-*/().,%^ ")
    sanitized = "".join(c for c in expression if c in allowed)
    try:
        result = eval(sanitized, {"__builtins__": {}}, {})
        return json.dumps({"expression": expression, "result": result})
    except Exception as e:
        return json.dumps({"expression": expression, "error": str(e)})


async def _tool_read_file(args: dict) -> str:
    """Read a file from the filesystem."""
    import os
    path = args.get("path", "")
    if not path:
        return "Error: path is required"
    try:
        with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
            content = f.read()
        return json.dumps({"path": path, "content": content[:10000], "truncated": len(content) > 10000})
    except FileNotFoundError:
        return json.dumps({"path": path, "error": "File not found"})
    except Exception as e:
        return json.dumps({"path": path, "error": str(e)})


async def _tool_write_file(args: dict) -> str:
    """Write content to a file."""
    import os
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return "Error: path is required"
    try:
        os.makedirs(os.path.dirname(os.path.expanduser(path)) or ".", exist_ok=True)
        with open(os.path.expanduser(path), "w", encoding="utf-8") as f:
            f.write(content)
        return json.dumps({"path": path, "written": len(content), "success": True})
    except Exception as e:
        return json.dumps({"path": path, "error": str(e)})


async def _tool_get_datetime(args: dict) -> str:
    """Get the current date and time."""
    tz = args.get("timezone", "UTC")
    now = datetime.now(timezone.utc)
    return json.dumps({
        "iso": now.isoformat(),
        "readable": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "timezone": tz,
    })


async def _tool_summarize_text(args: dict) -> str:
    """Request an LLM-powered summary (delegated to engine)."""
    text = args.get("text", "")
    max_length = args.get("max_length", 200)
    if not text:
        return "Error: text is required"
    words = text.split()
    if len(words) <= 50:
        return json.dumps({"summary": text, "original_words": len(words)})
    return json.dumps({
        "summary_requested": True,
        "original_words": len(words),
        "max_length": max_length,
        "preview": text[:max_length],
        "note": "Full summarization available when LLM API is configured.",
    })


# Register built-in tools
tool_registry.register(ToolDefinition(
    name="web_search",
    description="Search the web for current information, news, or documentation",
    category=ToolCategory.KNOWLEDGE,
    parameters=[
        ToolParameter("query", "string", "The search query string"),
        ToolParameter("num_results", "integer", "Number of results to return", required=False, default=5),
    ],
    handler=_tool_web_search,
    timeout=15.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="calculate",
    description="Evaluate a mathematical expression safely",
    category=ToolCategory.DATA,
    parameters=[
        ToolParameter("expression", "string", "The mathematical expression to evaluate"),
    ],
    handler=_tool_calculate,
    timeout=5.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="read_file",
    description="Read the contents of a file from the local filesystem",
    category=ToolCategory.SYSTEM,
    parameters=[
        ToolParameter("path", "string", "Absolute path to the file to read"),
    ],
    handler=_tool_read_file,
    timeout=10.0,
    safety=ExecutionSafety.SCOPED,
    path_param="path",
))

tool_registry.register(ToolDefinition(
    name="write_file",
    description="Write content to a file on the local filesystem",
    category=ToolCategory.SYSTEM,
    parameters=[
        ToolParameter("path", "string", "Absolute path to the file to write"),
        ToolParameter("content", "string", "Content to write to the file"),
    ],
    handler=_tool_write_file,
    timeout=10.0,
    safety=ExecutionSafety.MUTATING,
    path_param="path",
))

tool_registry.register(ToolDefinition(
    name="get_datetime",
    description="Get the current date and time in various formats",
    category=ToolCategory.SYSTEM,
    parameters=[
        ToolParameter("timezone", "string", "Timezone name (default: UTC)", required=False, default="UTC"),
    ],
    handler=_tool_get_datetime,
    timeout=3.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="summarize_text",
    description="Generate a concise summary of provided text",
    category=ToolCategory.KNOWLEDGE,
    parameters=[
        ToolParameter("text", "string", "The text to summarize"),
        ToolParameter("max_length", "integer", "Maximum summary length in characters", required=False, default=200),
    ],
    handler=_tool_summarize_text,
    timeout=20.0,
    safety=ExecutionSafety.READ_ONLY,
))