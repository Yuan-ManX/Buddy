"""
Buddy Tool Executor - Unified Tool Execution Engine

Central execution engine for all agent tool operations. Provides a unified
interface for tool registration, validation, execution, and result handling.
Supports built-in tools, custom tools, and MCP tool integration.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class ToolCategory(str, Enum):
    """Categories of executable tools."""
    FILE = "file"              # File system operations
    TERMINAL = "terminal"      # Shell/terminal commands
    BROWSER = "browser"        # Web browser automation
    API = "api"                # External API calls
    CODE = "code"              # Code execution/evaluation
    SEARCH = "search"          # Search operations
    DATA = "data"              # Data processing/transformation
    COMMUNICATION = "comm"     # Communication tools
    SYSTEM = "system"          # System-level operations
    CUSTOM = "custom"          # User-defined tools


class ToolRisk(str, Enum):
    """Risk level for tool operations."""
    SAFE = "safe"              # No side effects
    LOW = "low"                # Minor side effects
    MEDIUM = "medium"          # Moderate risk
    HIGH = "high"              # Significant risk
    CRITICAL = "critical"      # System-level risk


@dataclass
class ToolDefinition:
    """Definition of an executable tool."""
    name: str
    description: str
    category: ToolCategory
    risk: ToolRisk = ToolRisk.LOW
    parameters: dict[str, Any] = field(default_factory=dict)
    required_parameters: list[str] = field(default_factory=list)
    handler: Callable | None = None
    requires_approval: bool = False
    timeout_sec: float = 30.0
    retry_count: int = 0
    metadata: dict = field(default_factory=dict)

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling schema."""
        properties = {}
        for name, spec in self.parameters.items():
            properties[name] = {
                "type": spec.get("type", "string"),
                "description": spec.get("description", ""),
            }
            if "enum" in spec:
                properties[name]["enum"] = spec["enum"]

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": self.required_parameters,
                },
            },
        }


@dataclass
class ToolExecution:
    """Record of a single tool execution."""
    execution_id: str
    tool_name: str
    arguments: dict
    result: Any = None
    error: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    success: bool = False

    def complete(self, result: Any = None, error: str | None = None):
        self.end_time = time.time()
        self.result = result
        self.error = error
        self.success = error is None

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }


class ToolRegistry:
    """Registry of all available tools with validation and execution."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._execution_history: list[ToolExecution] = []
        self._total_executions = 0
        self._total_errors = 0

    def register(self, tool: ToolDefinition):
        """Register a tool definition."""
        self._tools[tool.name] = tool

    def unregister(self, name: str):
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def list_tools(self, category: ToolCategory | None = None) -> list[ToolDefinition]:
        """List all registered tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_openai_schemas(self) -> list[dict]:
        """Get all tools as OpenAI function schemas."""
        return [t.to_openai_schema() for t in self._tools.values()]

    def validate_arguments(self, tool_name: str, arguments: dict) -> tuple[bool, str]:
        """Validate arguments against tool definition."""
        tool = self.get(tool_name)
        if not tool:
            return False, f"Unknown tool: {tool_name}"

        # Check required parameters
        for param in tool.required_parameters:
            if param not in arguments:
                return False, f"Missing required parameter: {param}"

        # Check parameter types
        for name, value in arguments.items():
            if name in tool.parameters:
                expected_type = tool.parameters[name].get("type", "string")
                if not self._check_type(value, expected_type):
                    return False, f"Type mismatch for {name}: expected {expected_type}"

        return True, ""

    async def execute(
        self,
        tool_name: str,
        arguments: dict,
        timeout: float | None = None,
    ) -> ToolExecution:
        """Execute a tool with validation and timeout."""
        execution = ToolExecution(
            execution_id=f"exec-{uuid.uuid4().hex[:8]}",
            tool_name=tool_name,
            arguments=arguments,
        )

        self._total_executions += 1

        # Validate
        is_valid, error = self.validate_arguments(tool_name, arguments)
        if not is_valid:
            execution.complete(error=error)
            self._total_errors += 1
            self._execution_history.append(execution)
            return execution

        tool = self._tools[tool_name]
        effective_timeout = timeout or tool.timeout_sec

        try:
            if tool.handler is None:
                execution.complete(error="Tool has no handler")
                self._total_errors += 1
            elif asyncio.iscoroutinefunction(tool.handler):
                result = await asyncio.wait_for(
                    tool.handler(**arguments), timeout=effective_timeout
                )
                execution.complete(result=result)
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(tool.handler, **arguments),
                    timeout=effective_timeout,
                )
                execution.complete(result=result)
        except asyncio.TimeoutError:
            execution.complete(error=f"Tool execution timed out after {effective_timeout}s")
            self._total_errors += 1
        except Exception as e:
            execution.complete(error=str(e))
            self._total_errors += 1

        self._execution_history.append(execution)
        return execution

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type, str)
        if isinstance(expected, tuple):
            return isinstance(value, expected)
        return isinstance(value, expected)

    def get_history(self, limit: int = 50) -> list[dict]:
        return [e.to_dict() for e in self._execution_history[-limit:]]

    def get_stats(self) -> dict:
        return {
            "total_tools": len(self._tools),
            "total_executions": self._total_executions,
            "total_errors": self._total_errors,
            "tools": [
                {"name": t.name, "category": t.category.value, "risk": t.risk.value}
                for t in self._tools.values()
            ],
        }


class ToolExecutor:
    """Unified tool execution engine for Buddy agents.

    Coordinates tool registration, validation, execution, streaming,
    and result handling across all agent operations. Integrates with
    sandbox for secure execution and approval for risky operations.
    """

    def __init__(self):
        self.registry = ToolRegistry()
        self._active_executions: dict[str, ToolExecution] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register built-in tools available to all agents."""
        # File read tool
        self.registry.register(ToolDefinition(
            name="read_file",
            description="Read contents of a file",
            category=ToolCategory.FILE,
            risk=ToolRisk.SAFE,
            parameters={
                "path": {"type": "string", "description": "File path to read"},
                "encoding": {"type": "string", "description": "File encoding (default: utf-8)"},
            },
            required_parameters=["path"],
            handler=self._read_file,
        ))

        # File write tool
        self.registry.register(ToolDefinition(
            name="write_file",
            description="Write content to a file",
            category=ToolCategory.FILE,
            risk=ToolRisk.LOW,
            parameters={
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            required_parameters=["path", "content"],
            requires_approval=True,
            handler=self._write_file,
        ))

        # List directory tool
        self.registry.register(ToolDefinition(
            name="list_directory",
            description="List contents of a directory",
            category=ToolCategory.FILE,
            risk=ToolRisk.SAFE,
            parameters={
                "path": {"type": "string", "description": "Directory path"},
            },
            required_parameters=["path"],
            handler=self._list_directory,
        ))

        # Web search tool
        self.registry.register(ToolDefinition(
            name="web_search",
            description="Search the web for information",
            category=ToolCategory.SEARCH,
            risk=ToolRisk.LOW,
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results (default: 5)"},
            },
            required_parameters=["query"],
            handler=self._web_search,
        ))

        # Code execution tool
        self.registry.register(ToolDefinition(
            name="execute_code",
            description="Execute code in a sandboxed environment",
            category=ToolCategory.CODE,
            risk=ToolRisk.MEDIUM,
            parameters={
                "code": {"type": "string", "description": "Code to execute"},
                "language": {"type": "string", "description": "Programming language"},
            },
            required_parameters=["code", "language"],
            requires_approval=True,
            timeout_sec=15.0,
            handler=self._execute_code,
        ))

        # Shell command tool
        self.registry.register(ToolDefinition(
            name="shell_command",
            description="Execute a shell command in sandbox",
            category=ToolCategory.TERMINAL,
            risk=ToolRisk.HIGH,
            parameters={
                "command": {"type": "string", "description": "Shell command to execute"},
            },
            required_parameters=["command"],
            requires_approval=True,
            timeout_sec=30.0,
            handler=self._shell_command,
        ))

        # HTTP request tool
        self.registry.register(ToolDefinition(
            name="http_request",
            description="Make an HTTP request",
            category=ToolCategory.API,
            risk=ToolRisk.LOW,
            parameters={
                "url": {"type": "string", "description": "URL to request"},
                "method": {"type": "string", "description": "HTTP method", "enum": ["GET", "POST", "PUT", "DELETE"]},
                "headers": {"type": "object", "description": "Request headers"},
                "body": {"type": "string", "description": "Request body"},
            },
            required_parameters=["url"],
            handler=self._http_request,
        ))

    async def _read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Built-in file read handler."""
        with open(path, "r", encoding=encoding) as f:
            return f.read()

    async def _write_file(self, path: str, content: str) -> dict:
        """Built-in file write handler."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"path": path, "bytes_written": len(content)}

    async def _list_directory(self, path: str) -> list[str]:
        """Built-in directory listing handler."""
        import os
        return os.listdir(path)

    async def _web_search(self, query: str, num_results: int = 5) -> dict:
        """Built-in web search handler (simulated)."""
        return {
            "query": query,
            "results": [],
            "note": "Web search requires API configuration. Configure SEARCH_API_KEY to enable.",
        }

    async def _execute_code(self, code: str, language: str) -> dict:
        """Built-in code execution handler."""
        from agent.sandbox import get_sandbox_engine, SandboxPolicy
        sandbox = get_sandbox_engine()
        session_id = sandbox.create_session("tool-executor", SandboxPolicy.STANDARD)

        if language.lower() == "python":
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                tmp_path = f.name
            result = await sandbox.execute(session_id, f"python {tmp_path}")
            import os
            os.unlink(tmp_path)
        else:
            result = await sandbox.execute(session_id, code)

        sandbox.close_session(session_id)
        return result.to_dict()

    async def _shell_command(self, command: str) -> dict:
        """Built-in shell command handler."""
        from agent.sandbox import get_sandbox_engine, SandboxPolicy
        sandbox = get_sandbox_engine()
        session_id = sandbox.create_session("tool-executor", SandboxPolicy.STANDARD)
        result = await sandbox.execute(session_id, command)
        sandbox.close_session(session_id)
        return result.to_dict()

    async def _http_request(self, url: str, method: str = "GET", headers: dict | None = None, body: str | None = None) -> dict:
        """Built-in HTTP request handler."""
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body,
            )
            return {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text[:10000],
            }

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        timeout: float | None = None,
    ) -> ToolExecution:
        """Execute a tool and return the execution record."""
        execution = await self.registry.execute(tool_name, arguments, timeout)
        self._active_executions[execution.execution_id] = execution
        return execution

    async def execute_tools_parallel(
        self,
        tool_calls: list[dict],
    ) -> list[ToolExecution]:
        """Execute multiple tools in parallel."""
        tasks = [
            self.registry.execute(tc["name"], tc.get("arguments", {}))
            for tc in tool_calls
        ]
        return await asyncio.gather(*tasks)

    async def execute_tools_sequential(
        self,
        tool_calls: list[dict],
    ) -> list[ToolExecution]:
        """Execute multiple tools sequentially."""
        results = []
        for tc in tool_calls:
            result = await self.registry.execute(tc["name"], tc.get("arguments", {}))
            results.append(result)
        return results

    def get_stats(self) -> dict:
        return self.registry.get_stats()


# Global tool executor instance
_tool_executor: ToolExecutor | None = None


def get_tool_executor() -> ToolExecutor:
    """Get or create the global tool executor."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor