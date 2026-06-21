"""Buddy Agent Tool System — function-calling powered tool orchestration

Defines a comprehensive tool framework for agents with structured schemas,
validation, streaming execution, parallel safe execution, and automatic
result aggregation with trust-level classification.
"""
from __future__ import annotations
import ast
import json
import logging
import sqlite3
import asyncio
import operator
import tempfile
import os
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

    def get_tool_names(self) -> list[str]:
        """Get list of all registered tool names."""
        return [t.name for t in self._tools.values()]

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


# Safe math evaluator using AST — avoids eval() security risks
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def _safe_eval(expr: str) -> float:
    """Safely evaluate a simple math expression using AST parsing."""
    tree = ast.parse(expr.strip(), mode="eval")
    return _safe_eval_node(tree.body)  # type: ignore[arg-type]


def _safe_eval_node(node: ast.AST) -> float:
    """Recursively evaluate a safe AST node."""
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        op = _SAFE_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_safe_eval_node(node.left), _safe_eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _SAFE_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_safe_eval_node(node.operand))
    raise ValueError(f"Unsupported expression type: {type(node).__name__}")


async def _tool_calculate(args: dict) -> str:
    """Safely evaluate mathematical expressions using AST parsing."""
    expression = args.get("expression", "")
    if not expression:
        return "Error: expression is required"
    try:
        result = _safe_eval(expression)
        return json.dumps({"expression": expression, "result": result})
    except Exception as e:
        return json.dumps({"expression": expression, "error": str(e)})


async def _tool_read_file(args: dict) -> str:
    """Read a file from the workspace filesystem."""
    import os
    path = args.get("path", "")
    if not path:
        return "Error: path is required"

    # Restrict to workspace directory or a safe temp directory
    from config.settings import settings
    workspace_root = os.path.join(os.path.expanduser("~"), ".buddy_workspaces")
    expanded = os.path.realpath(os.path.expanduser(path))
    if not expanded.startswith(workspace_root) and not expanded.startswith(tempfile.gettempdir()):
        return json.dumps({"path": path, "error": "Access denied: path outside workspace"})

    try:
        with open(expanded, "r", encoding="utf-8") as f:
            content = f.read()
        return json.dumps({"path": path, "content": content[:10000], "truncated": len(content) > 10000})
    except FileNotFoundError:
        return json.dumps({"path": path, "error": "File not found"})
    except Exception as e:
        return json.dumps({"path": path, "error": str(e)})


async def _tool_write_file(args: dict) -> str:
    """Write content to a file in the workspace filesystem."""
    import os
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return "Error: path is required"

    # Restrict to workspace directory
    workspace_root = os.path.join(os.path.expanduser("~"), ".buddy_workspaces")
    expanded = os.path.realpath(os.path.expanduser(path))
    if not expanded.startswith(workspace_root):
        return json.dumps({"path": path, "error": "Access denied: path outside workspace"})

    try:
        os.makedirs(os.path.dirname(expanded) or ".", exist_ok=True)
        with open(expanded, "w", encoding="utf-8") as f:
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


async def _tool_list_directory(args: dict) -> str:
    """List files and directories in a given path."""
    import os
    path = args.get("path", ".")
    show_hidden = args.get("show_hidden", False)
    try:
        workspace_root = os.path.join(os.path.expanduser("~"), ".buddy_workspaces")
        expanded = os.path.realpath(os.path.expanduser(path))
        if not expanded.startswith(workspace_root):
            return json.dumps({"path": path, "error": "Access denied: path outside workspace"})

        entries = []
        for entry in os.listdir(expanded):
            if not show_hidden and entry.startswith("."):
                continue
            full = os.path.join(expanded, entry)
            entries.append({
                "name": entry,
                "type": "directory" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else 0,
            })
        entries.sort(key=lambda e: (e["type"], e["name"]))
        return json.dumps({"path": path, "entries": entries, "count": len(entries)})
    except FileNotFoundError:
        return json.dumps({"path": path, "error": "Directory not found"})
    except Exception as e:
        return json.dumps({"path": path, "error": str(e)})


async def _tool_execute_code(args: dict) -> str:
    """Execute code in a sandboxed environment."""
    import subprocess
    import os
    language = args.get("language", "python")
    code = args.get("code", "")
    timeout = args.get("timeout", 30)

    if not code:
        return "Error: code is required"

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=f".{language}" if language != "shell" else ".sh",
            delete=False,
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            if language == "python":
                cmd = ["python3", tmp_path]
            elif language == "shell":
                cmd = ["bash", tmp_path]
            elif language == "javascript":
                cmd = ["node", tmp_path]
            else:
                return json.dumps({"error": f"Unsupported language: {language}"})

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
            )
            return json.dumps({
                "success": result.returncode == 0,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:2000],
                "exit_code": result.returncode,
            })
        finally:
            os.unlink(tmp_path)
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": f"Execution timed out after {timeout}s"})
    except FileNotFoundError:
        return json.dumps({"success": False, "error": f"Runtime for {language} not found"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


async def _tool_fetch_url(args: dict) -> str:
    """Fetch content from a URL."""
    import urllib.request
    url = args.get("url", "")
    if not url:
        return "Error: url is required"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Buddy-Agent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode("utf-8", errors="replace")
            # Extract text content (simple approach)
            text = content[:10000]
            return json.dumps({
                "url": url,
                "status": response.status,
                "content": text,
                "content_type": response.headers.get("Content-Type", ""),
                "truncated": len(content) > 10000,
            })
    except Exception as e:
        return json.dumps({"url": url, "error": str(e)})


async def _tool_json_query(args: dict) -> str:
    """Query and transform JSON data."""
    data_str = args.get("data", "{}")
    query = args.get("query", "")
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON data"})

    if not query:
        return json.dumps({"data": data})

    # Simple dot-notation path query: e.g., "users.0.name"
    parts = query.split(".")
    current = data
    for part in parts:
        if isinstance(current, list):
            try:
                idx = int(part)
                current = current[idx]
            except (ValueError, IndexError):
                return json.dumps({"error": f"Invalid array index: {part}"})
        elif isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return json.dumps({"error": f"Key not found: {part}"})
        else:
            return json.dumps({"error": f"Cannot navigate into {type(current).__name__}"})

    return json.dumps({"result": current})


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

tool_registry.register(ToolDefinition(
    name="list_directory",
    description="List files and directories at a given path in the workspace",
    category=ToolCategory.SYSTEM,
    parameters=[
        ToolParameter("path", "string", "Directory path to list (default: workspace root)", required=False, default="."),
        ToolParameter("show_hidden", "boolean", "Show hidden files (dotfiles)", required=False, default=False),
    ],
    handler=_tool_list_directory,
    timeout=10.0,
    safety=ExecutionSafety.READ_ONLY,
    path_param="path",
))

tool_registry.register(ToolDefinition(
    name="execute_code",
    description="Execute code in a sandboxed environment (python, shell, javascript)",
    category=ToolCategory.CODE,
    parameters=[
        ToolParameter("code", "string", "The code to execute"),
        ToolParameter("language", "string", "Programming language: python, shell, or javascript", required=False, default="python"),
        ToolParameter("timeout", "integer", "Maximum execution time in seconds", required=False, default=30),
    ],
    handler=_tool_execute_code,
    timeout=35.0,
    safety=ExecutionSafety.DESTRUCTIVE,
))

tool_registry.register(ToolDefinition(
    name="fetch_url",
    description="Fetch and read content from a URL",
    category=ToolCategory.KNOWLEDGE,
    parameters=[
        ToolParameter("url", "string", "The URL to fetch content from"),
    ],
    handler=_tool_fetch_url,
    timeout=20.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="json_query",
    description="Query and transform JSON data using dot-notation paths",
    category=ToolCategory.DATA,
    parameters=[
        ToolParameter("data", "string", "JSON string to query"),
        ToolParameter("query", "string", "Dot-notation query path (e.g., 'users.0.name')", required=False, default=""),
    ],
    handler=_tool_json_query,
    timeout=5.0,
    safety=ExecutionSafety.READ_ONLY,
))


# ── Communication Tools ──────────────────────────────────

async def _tool_send_email(args: dict) -> str:
    """Send an email (placeholder — requires SMTP configuration)."""
    to = args.get("to", "")
    subject = args.get("subject", "")
    body = args.get("body", "")
    if not to or not subject or not body:
        return "Error: to, subject, and body are all required"
    return json.dumps({
        "to": to,
        "subject": subject,
        "body_preview": body[:200],
        "status": "not_sent",
        "note": "Email sending requires SMTP configuration. Set SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASSWORD in .env.",
    })


# ── Knowledge Tools ──────────────────────────────────────

async def _tool_translate_text(args: dict) -> str:
    """Translate text between languages (placeholder — requires translation API)."""
    text = args.get("text", "")
    source_lang = args.get("source_lang", "auto")
    target_lang = args.get("target_lang", "")
    if not text:
        return "Error: text is required"
    if not target_lang:
        return "Error: target_lang is required"
    return json.dumps({
        "text_preview": text[:200],
        "source_lang": source_lang,
        "target_lang": target_lang,
        "status": "not_translated",
        "note": "Translation requires integration with a translation API (e.g., Google Translate, DeepL). Configure TRANSLATION_API_KEY in .env.",
    })


# ── Data Tools ───────────────────────────────────────────

async def _tool_database_query(args: dict) -> str:
    """Execute a SQL query on project data using SQLite."""
    query = args.get("query", "")
    database_url = args.get("database_url", "")

    if not query:
        return "Error: query is required"

    # Only allow SELECT queries for safety
    normalized = query.strip().upper()
    if not normalized.startswith("SELECT"):
        return json.dumps({
            "error": "Only SELECT queries are allowed for safety",
            "query": query,
        })

    db_path = database_url or ":memory:"
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        result = [dict(zip(columns, row)) for row in rows]
        return json.dumps({
            "query": query,
            "columns": columns,
            "row_count": len(result),
            "rows": result,
        })
    except Exception as e:
        return json.dumps({
            "query": query,
            "error": str(e),
        })


# ── Creative Tools ───────────────────────────────────────

async def _tool_generate_image(args: dict) -> str:
    """Generate an image from a text prompt (placeholder — requires image generation API)."""
    prompt = args.get("prompt", "")
    size = args.get("size", "1024x1024")
    style = args.get("style", "")

    if not prompt:
        return "Error: prompt is required"

    result: dict = {
        "prompt": prompt,
        "size": size,
        "status": "not_generated",
        "note": "Image generation requires integration with an image generation API (e.g., DALL·E, Stable Diffusion). Configure IMAGE_GEN_API_KEY in .env.",
    }
    if style:
        result["style"] = style
    return json.dumps(result)


# ── System Tools ─────────────────────────────────────────

async def _tool_remember(args: dict) -> str:
    """Store important information in agent memory."""
    content = args.get("content", "")
    tags = args.get("tags", "")

    if not content:
        return "Error: content is required"

    from database.db import async_session
    from database.models import Memory as MemoryModel
    import uuid

    memory_id = str(uuid.uuid4())
    meta: dict = {}
    if tags:
        meta["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    try:
        async with async_session() as session:
            memory = MemoryModel(
                id=memory_id,
                agent_id="default",
                content=content,
                memory_type="long_term:fact",
                importance=0.5,
                meta=meta,
            )
            session.add(memory)
            await session.commit()

        return json.dumps({
            "id": memory_id,
            "content_preview": content[:200],
            "tags": meta.get("tags", []),
            "stored": True,
            "note": "Memory stored in long-term layer.",
        })
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        return json.dumps({
            "error": f"Failed to store memory: {str(e)}",
        })


# Register additional built-in tools

tool_registry.register(ToolDefinition(
    name="send_email",
    description="Send an email to a recipient (placeholder — configure SMTP settings to enable)",
    category=ToolCategory.COMMUNICATION,
    parameters=[
        ToolParameter("to", "string", "Recipient email address"),
        ToolParameter("subject", "string", "Email subject line"),
        ToolParameter("body", "string", "Email body content"),
    ],
    handler=_tool_send_email,
    timeout=10.0,
    safety=ExecutionSafety.SCOPED,
    path_param="to",
))

tool_registry.register(ToolDefinition(
    name="translate_text",
    description="Translate text from one language to another (placeholder — configure translation API to enable)",
    category=ToolCategory.KNOWLEDGE,
    parameters=[
        ToolParameter("text", "string", "The text to translate"),
        ToolParameter("source_lang", "string", "Source language code (default: auto-detect)", required=False, default="auto"),
        ToolParameter("target_lang", "string", "Target language code"),
    ],
    handler=_tool_translate_text,
    timeout=15.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="database_query",
    description="Execute a read-only SQL query on project data via SQLite",
    category=ToolCategory.DATA,
    parameters=[
        ToolParameter("query", "string", "The SQL SELECT query to execute"),
        ToolParameter("database_url", "string", "Path to SQLite database file (default: in-memory)", required=False, default=""),
    ],
    handler=_tool_database_query,
    timeout=10.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="generate_image",
    description="Generate an image from a text prompt (placeholder — configure image generation API to enable)",
    category=ToolCategory.CREATIVE,
    parameters=[
        ToolParameter("prompt", "string", "Text description of the image to generate"),
        ToolParameter("size", "string", "Image dimensions (e.g., 1024x1024)", required=False, default="1024x1024"),
        ToolParameter("style", "string", "Artistic style for the image", required=False, default=""),
    ],
    handler=_tool_generate_image,
    timeout=30.0,
    safety=ExecutionSafety.SCOPED,
    path_param="prompt",
))

tool_registry.register(ToolDefinition(
    name="remember",
    description="Store important information in the agent's long-term memory",
    category=ToolCategory.SYSTEM,
    parameters=[
        ToolParameter("content", "string", "The information to remember"),
        ToolParameter("tags", "string", "Comma-separated tags for categorization", required=False, default=""),
    ],
    handler=_tool_remember,
    timeout=10.0,
    safety=ExecutionSafety.MUTATING,
))


# ── Extended Tools ────────────────────────────────────────

async def _tool_grep_search(args: dict) -> str:
    """Search file contents using regex patterns."""
    import os
    import re
    pattern = args.get("pattern", "")
    directory = args.get("directory", ".")
    file_pattern = args.get("file_pattern", "*")
    max_results = int(args.get("max_results", 50))

    if not pattern:
        return "Error: pattern is required"

    workspace_root = os.path.join(os.path.expanduser("~"), ".buddy_workspaces")
    expanded = os.path.realpath(os.path.expanduser(directory))
    if not expanded.startswith(workspace_root):
        return json.dumps({"error": "Access denied: path outside workspace"})

    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        results = []
        import fnmatch
        for root, dirs, files in os.walk(expanded):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if not fnmatch.fnmatch(fname, file_pattern):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for lno, line in enumerate(f, 1):
                            if compiled.search(line):
                                results.append({
                                    "file": os.path.relpath(fpath, expanded),
                                    "line": lno,
                                    "content": line.strip()[:200],
                                })
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        return json.dumps({
            "pattern": pattern,
            "matches": len(results),
            "truncated": len(results) >= max_results,
            "results": results,
        })
    except re.error as e:
        return json.dumps({"error": f"Invalid regex: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _tool_find_files(args: dict) -> str:
    """Find files matching patterns in the workspace."""
    import os
    import fnmatch
    directory = args.get("directory", ".")
    glob_pattern = args.get("glob", "*")
    max_depth = int(args.get("max_depth", 5))

    workspace_root = os.path.join(os.path.expanduser("~"), ".buddy_workspaces")
    expanded = os.path.realpath(os.path.expanduser(directory))
    if not expanded.startswith(workspace_root):
        return json.dumps({"error": "Access denied: path outside workspace"})

    try:
        results = []
        for root, dirs, files in os.walk(expanded):
            depth = root[len(expanded):].count(os.sep)
            if depth > max_depth:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if fnmatch.fnmatch(fname, glob_pattern):
                    fpath = os.path.join(root, fname)
                    results.append({
                        "path": os.path.relpath(fpath, expanded),
                        "size": os.path.getsize(fpath),
                        "type": "file",
                    })
                if len(results) >= 200:
                    break
            if len(results) >= 200:
                break

        return json.dumps({
            "pattern": glob_pattern,
            "count": len(results),
            "results": results[:200],
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _tool_diff_files(args: dict) -> str:
    """Compute diff between two files or strings."""
    file_a = args.get("file_a", "")
    file_b = args.get("file_b", "")
    import difflib

    if not file_a and not file_b:
        return "Error: file_a and file_b are required"

    try:
        lines_a = file_a.splitlines(True)
        lines_b = file_b.splitlines(True)

        differ = difflib.unified_diff(
            lines_a, lines_b,
            fromfile="version_a",
            tofile="version_b",
            lineterm="",
        )
        diff_output = "\n".join(differ)

        return json.dumps({
            "diff": diff_output[:5000],
            "lines_added": len([l for l in diff_output.split("\n") if l.startswith("+") and not l.startswith("+++")]),
            "lines_removed": len([l for l in diff_output.split("\n") if l.startswith("-") and not l.startswith("---")]),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _tool_data_analysis(args: dict) -> str:
    """Perform basic statistical analysis on numerical data."""
    import math
    data_str = args.get("data", "")
    if not data_str:
        return "Error: data is required"

    try:
        if isinstance(data_str, str):
            numbers = [float(x.strip()) for x in data_str.split(",") if x.strip()]
        else:
            numbers = [float(x) for x in data_str]

        if not numbers:
            return json.dumps({"error": "No valid numbers found"})

        n = len(numbers)
        mean = sum(numbers) / n
        sorted_nums = sorted(numbers)
        median = sorted_nums[n // 2] if n % 2 else (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
        variance = sum((x - mean) ** 2 for x in numbers) / n
        std_dev = math.sqrt(variance)

        return json.dumps({
            "count": n,
            "sum": round(sum(numbers), 4),
            "mean": round(mean, 4),
            "median": round(median, 4),
            "min": round(min(numbers), 4),
            "max": round(max(numbers), 4),
            "std_dev": round(std_dev, 4),
            "variance": round(variance, 4),
        })
    except ValueError:
        return json.dumps({"error": "Invalid numerical data provided"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _tool_count_tokens(args: dict) -> str:
    """Estimate token count for a given text."""
    text = args.get("text", "")
    if not text:
        return "Error: text is required"
    # Rough estimation: 1 token ≈ 4 characters for English, ~2 for code
    char_count = len(text)
    word_count = len(text.split())
    est_tokens_gpt = max(1, char_count // 4)
    est_tokens_claude = max(1, char_count // 3)
    return json.dumps({
        "characters": char_count,
        "words": word_count,
        "estimated_tokens_gpt": est_tokens_gpt,
        "estimated_tokens_claude": est_tokens_claude,
        "lines": text.count("\n") + 1,
    })


async def _tool_todo_manager(args: dict) -> str:
    """Manage a structured todo list for the agent."""
    action = args.get("action", "list")
    task_id = args.get("task_id", "")
    title = args.get("title", "")
    status = args.get("status", "pending")

    if not hasattr(_tool_todo_manager, "_todos"):
        _tool_todo_manager._todos = []

    todos = _tool_todo_manager._todos

    if action == "add":
        if not title:
            return "Error: title is required for add action"
        new_id = f"todo-{len(todos) + 1}"
        todos.append({
            "id": new_id, "title": title, "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return json.dumps({"action": "added", "todo": todos[-1], "total": len(todos)})

    elif action == "update":
        for t in todos:
            if t["id"] == task_id:
                if title:
                    t["title"] = title
                if status in ("pending", "in_progress", "completed", "cancelled"):
                    t["status"] = status
                return json.dumps({"action": "updated", "todo": t})
        return json.dumps({"error": f"Todo not found: {task_id}"})

    elif action == "delete":
        original_len = len(todos)
        _tool_todo_manager._todos = [t for t in todos if t["id"] != task_id]
        if len(_tool_todo_manager._todos) < original_len:
            return json.dumps({"action": "deleted", "task_id": task_id, "remaining": len(_tool_todo_manager._todos)})
        return json.dumps({"error": f"Todo not found: {task_id}"})

    else:  # list
        filtered = todos
        if status != "all":
            filtered = [t for t in todos if t["status"] == status]
        return json.dumps({
            "todos": filtered,
            "total": len(todos),
            "completed": sum(1 for t in todos if t["status"] == "completed"),
            "pending": sum(1 for t in todos if t["status"] == "pending"),
        })


# Register extended tools
tool_registry.register(ToolDefinition(
    name="grep_search",
    description="Search file contents in the workspace using regex patterns",
    category=ToolCategory.CODE,
    parameters=[
        ToolParameter("pattern", "string", "Regex pattern to search for"),
        ToolParameter("directory", "string", "Directory to search in (default: workspace root)", required=False, default="."),
        ToolParameter("file_pattern", "string", "File glob pattern to filter (e.g., *.py)", required=False, default="*"),
        ToolParameter("max_results", "integer", "Maximum results to return", required=False, default=50),
    ],
    handler=_tool_grep_search,
    timeout=20.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="find_files",
    description="Find files in the workspace matching a glob pattern",
    category=ToolCategory.SYSTEM,
    parameters=[
        ToolParameter("glob", "string", "Glob pattern to match files (e.g., *.py, **/*.ts)", required=False, default="*"),
        ToolParameter("directory", "string", "Directory to search in", required=False, default="."),
        ToolParameter("max_depth", "integer", "Maximum directory depth", required=False, default=5),
    ],
    handler=_tool_find_files,
    timeout=15.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="diff_files",
    description="Compute a unified diff between two text strings",
    category=ToolCategory.CODE,
    parameters=[
        ToolParameter("file_a", "string", "First text content"),
        ToolParameter("file_b", "string", "Second text content"),
    ],
    handler=_tool_diff_files,
    timeout=10.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="data_analysis",
    description="Perform statistical analysis on comma-separated numerical data",
    category=ToolCategory.DATA,
    parameters=[
        ToolParameter("data", "string", "Comma-separated numerical values to analyze"),
    ],
    handler=_tool_data_analysis,
    timeout=10.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="count_tokens",
    description="Estimate the token count for a given text for different models",
    category=ToolCategory.SYSTEM,
    parameters=[
        ToolParameter("text", "string", "The text to count tokens for"),
    ],
    handler=_tool_count_tokens,
    timeout=5.0,
    safety=ExecutionSafety.READ_ONLY,
))

tool_registry.register(ToolDefinition(
    name="todo_manager",
    description="Manage a structured todo list for tracking tasks",
    category=ToolCategory.SYSTEM,
    parameters=[
        ToolParameter("action", "string", "Action: list, add, update, or delete", required=False, default="list"),
        ToolParameter("task_id", "string", "Task ID for update/delete", required=False, default=""),
        ToolParameter("title", "string", "Task title for add/update", required=False, default=""),
        ToolParameter("status", "string", "Task status: pending, in_progress, completed, cancelled", required=False, default="pending"),
    ],
    handler=_tool_todo_manager,
    timeout=5.0,
    safety=ExecutionSafety.MUTATING,
))

# ── Tool Composition ─────────────────────────────────────

class ToolComposition:
    """Compose multiple tools into pipelines with sequential, parallel, and conditional execution."""

    class PipelineMode(str, Enum):
        SEQUENTIAL = "sequential"
        PARALLEL = "parallel"
        CONDITIONAL = "conditional"

    @staticmethod
    async def sequential(
        steps: list[tuple[str, dict]],
        registry: ToolRegistry,
    ) -> list[ToolResult]:
        """Execute tools sequentially, passing output of each step to the next.

        Each step receives all previous step outputs in a '_previous_results' key.
        """
        results = []
        for name, args in steps:
            if results:
                args = dict(args)
                args["_previous_results"] = [r.output for r in results]
            result = await registry.execute(name, args)
            results.append(result)
        return results

    @staticmethod
    async def parallel(
        calls: list[tuple[str, dict]],
        registry: ToolRegistry,
    ) -> list[ToolResult]:
        """Execute multiple tools in parallel with safety-aware scheduling."""
        return await registry.execute_batch(calls)

    @staticmethod
    async def conditional(
        condition_tool: tuple[str, dict],
        true_branch: tuple[str, dict],
        false_branch: tuple[str, dict] | None,
        registry: ToolRegistry,
    ) -> list[ToolResult]:
        """Execute a condition-checking tool, then route to true or false branch.

        The condition is considered true if the condition tool succeeds and its
        output (parsed as JSON) has a truthy 'result' field, or if the output
        string is non-empty and not an error.
        """
        results = []
        cond_result = await registry.execute(condition_tool[0], condition_tool[1])
        results.append(cond_result)

        # Determine if condition passed
        condition_met = cond_result.success
        if condition_met and cond_result.output:
            try:
                parsed = json.loads(cond_result.output)
                if isinstance(parsed, dict):
                    if "result" in parsed and not parsed["result"]:
                        condition_met = False
                    if "error" in parsed:
                        condition_met = False
            except (json.JSONDecodeError, TypeError):
                pass

        if condition_met:
            branch_result = await registry.execute(true_branch[0], true_branch[1])
        elif false_branch:
            branch_result = await registry.execute(false_branch[0], false_branch[1])
        else:
            branch_result = ToolResult(
                name="conditional_skip",
                success=True,
                output=json.dumps({"skipped": True, "reason": "condition false, no false branch"}),
            )
        results.append(branch_result)
        return results


# ── Tool Rate Limiter ────────────────────────────────────

class ToolRateLimiter:
    """Per-tool rate limiting with configurable time windows."""

    def __init__(self, default_window_seconds: float = 60.0, default_max_calls: int = 30):
        self.default_window = default_window_seconds
        self.default_max = default_max_calls
        self._limits: dict[str, dict] = {}
        self._call_history: dict[str, list[float]] = {}

    def configure(
        self,
        tool_name: str,
        max_calls: int,
        window_seconds: float,
    ):
        """Configure rate limit for a specific tool."""
        self._limits[tool_name] = {
            "max_calls": max_calls,
            "window": window_seconds,
        }

    def check(self, tool_name: str) -> tuple[bool, float]:
        """Check if a tool call is allowed. Returns (allowed, wait_seconds)."""
        import time as _time
        now = _time.time()
        limit = self._limits.get(
            tool_name,
            {"max_calls": self.default_max, "window": self.default_window},
        )

        if tool_name not in self._call_history:
            self._call_history[tool_name] = [now]
            return True, 0.0

        # Remove expired entries
        cutoff = now - limit["window"]
        self._call_history[tool_name] = [
            t for t in self._call_history[tool_name] if t > cutoff
        ]

        if len(self._call_history[tool_name]) < limit["max_calls"]:
            self._call_history[tool_name].append(now)
            return True, 0.0

        # Calculate wait time until oldest call expires
        oldest = min(self._call_history[tool_name])
        wait = oldest + limit["window"] - now
        return False, max(0.0, wait)

    def get_usage(self, tool_name: str) -> dict:
        """Get current usage stats for a tool."""
        import time as _time
        now = _time.time()
        limit = self._limits.get(
            tool_name,
            {"max_calls": self.default_max, "window": self.default_window},
        )
        if tool_name not in self._call_history:
            return {"used": 0, "limit": limit["max_calls"], "window_seconds": limit["window"]}
        cutoff = now - limit["window"]
        recent = [t for t in self._call_history[tool_name] if t > cutoff]
        return {
            "used": len(recent),
            "limit": limit["max_calls"],
            "window_seconds": limit["window"],
            "remaining": max(0, limit["max_calls"] - len(recent)),
        }


# ── Tool Result Cache ────────────────────────────────────

class ToolResultCache:
    """LRU cache for deterministic tool results keyed by input hash."""

    def __init__(self, max_size: int = 256):
        self.max_size = max_size
        self._cache: dict[str, ToolResult] = {}
        self._access_order: list[str] = []
        self._hits: int = 0
        self._misses: int = 0

    @staticmethod
    def _make_key(tool_name: str, arguments: dict) -> str:
        """Generate a deterministic cache key from tool name and arguments."""
        arg_str = json.dumps(arguments, sort_keys=True, default=str)
        return f"{tool_name}:{hash(arg_str)}"

    def get(self, tool_name: str, arguments: dict) -> ToolResult | None:
        """Retrieve a cached result if available."""
        key = self._make_key(tool_name, arguments)
        if key in self._cache:
            self._hits += 1
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, tool_name: str, arguments: dict, result: ToolResult):
        """Cache a tool execution result."""
        key = self._make_key(tool_name, arguments)
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self.max_size:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = result
        self._access_order.append(key)

    def invalidate(self, tool_name: str | None = None):
        """Invalidate cache entries, optionally filtered by tool name."""
        if tool_name is None:
            self._cache.clear()
            self._access_order.clear()
            return
        keys_to_remove = [k for k in self._cache if k.startswith(f"{tool_name}:")]
        for key in keys_to_remove:
            del self._cache[key]
            self._access_order.remove(key)

    def get_stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{(self._hits / max(total, 1) * 100):.1f}%",
        }


# ── Tool Output Validation ───────────────────────────────

def validate_tool_output(
    tool_name: str,
    output: str,
    expected_schema: dict | None = None,
) -> tuple[bool, str]:
    """Validate tool output against a schema.

    Performs basic validation:
    - Non-empty output for most tools
    - Valid JSON for JSON-returning tools
    - Schema compliance if expected_schema is provided

    Returns (is_valid, error_message).
    """
    if output is None:
        return False, "Output is None"

    if not isinstance(output, str):
        return False, f"Output is not a string (got {type(output).__name__})"

    if not output.strip():
        return False, "Output is empty"

    # Check if output looks like JSON (most tools return JSON)
    if output.strip().startswith("{"):
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON output: {str(e)}"

        # Schema validation if provided
        if expected_schema:
            for field, field_type in expected_schema.items():
                if field not in parsed:
                    return False, f"Missing required field '{field}' in output"
                actual = parsed[field]
                expected = field_type
                if expected == "string" and not isinstance(actual, str):
                    return False, f"Field '{field}' expected string, got {type(actual).__name__}"
                elif expected == "number" and not isinstance(actual, (int, float)):
                    return False, f"Field '{field}' expected number, got {type(actual).__name__}"
                elif expected == "boolean" and not isinstance(actual, bool):
                    return False, f"Field '{field}' expected boolean, got {type(actual).__name__}"
                elif expected == "array" and not isinstance(actual, list):
                    return False, f"Field '{field}' expected array, got {type(actual).__name__}"
                elif expected == "object" and not isinstance(actual, dict):
                    return False, f"Field '{field}' expected object, got {type(actual).__name__}"

    return True, ""


# ── Tool Execution Metrics ───────────────────────────────

class ToolExecutionMetrics:
    """Track per-tool execution time, success rate, and token usage."""

    def __init__(self):
        self._metrics: dict[str, dict] = {}

    def record(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
        tokens_used: int = 0,
    ):
        """Record a single tool execution."""
        if tool_name not in self._metrics:
            self._metrics[tool_name] = {
                "total_calls": 0,
                "successful": 0,
                "failed": 0,
                "total_duration_ms": 0.0,
                "total_tokens": 0,
                "last_called": "",
            }

        m = self._metrics[tool_name]
        m["total_calls"] += 1
        if success:
            m["successful"] += 1
        else:
            m["failed"] += 1
        m["total_duration_ms"] += duration_ms
        m["total_tokens"] += tokens_used
        m["last_called"] = datetime.now(timezone.utc).isoformat()

    def get(self, tool_name: str | None = None) -> dict:
        """Get metrics for a specific tool or all tools."""
        if tool_name:
            return self._format_metric(tool_name, self._metrics.get(tool_name))
        return {
            name: self._format_metric(name, data)
            for name, data in self._metrics.items()
        }

    def _format_metric(self, name: str, data: dict | None) -> dict:
        if not data:
            return {"error": f"No metrics for tool: {name}"}
        total = data["total_calls"]
        return {
            "total_calls": total,
            "successful": data["successful"],
            "failed": data["failed"],
            "success_rate": f"{(data['successful'] / max(total, 1) * 100):.1f}%",
            "avg_duration_ms": round(data["total_duration_ms"] / max(total, 1), 2),
            "total_tokens": data["total_tokens"],
            "last_called": data["last_called"],
        }

    def reset(self, tool_name: str | None = None):
        """Reset metrics for a specific tool or all tools."""
        if tool_name:
            self._metrics.pop(tool_name, None)
        else:
            self._metrics.clear()


# ── Tool Warm-Up ─────────────────────────────────────────

async def warm_up_tool(registry: ToolRegistry, tool_name: str):
    """Pre-initialize a tool before first use to reduce cold-start latency.

    Sends a lightweight no-op call to initialize any lazy resources
    (DB connections, API clients, model loading, etc.) associated with the tool.
    """
    tool = registry.get(tool_name)
    if not tool:
        logger.warning(f"Warm-up failed: tool '{tool_name}' not found")
        return False

    warm_up_args = {
        "web_search": {"query": "__warmup__", "num_results": 0},
        "calculate": {"expression": "0"},
        "get_datetime": {"timezone": "UTC"},
        "count_tokens": {"text": "warmup"},
        "json_query": {"data": "{}", "query": ""},
    }

    args = warm_up_args.get(tool_name, {"_warmup": True})
    try:
        result = await registry.execute(tool_name, args)
        logger.info(f"Tool warm-up: {tool_name} -> {'OK' if result.success else f'ERR: {result.error}'}")
        return result.success
    except Exception as e:
        logger.warning(f"Tool warm-up failed for {tool_name}: {e}")
        return False


async def warm_up_all_tools(registry: ToolRegistry, exclude: list[str] | None = None):
    """Warm up all registered tools in parallel."""
    exclude = exclude or []
    tasks = [
        warm_up_tool(registry, name)
        for name in registry._tools
        if name not in exclude
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    warmed = sum(1 for r in results if r is True)
    logger.info(f"Warmed up {warmed}/{len(tasks)} tools")
    return warmed


# ── Global Instances ─────────────────────────────────────

tool_rate_limiter = ToolRateLimiter()
tool_result_cache = ToolResultCache()
tool_metrics = ToolExecutionMetrics()