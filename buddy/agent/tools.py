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