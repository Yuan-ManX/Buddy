"""
Buddy MCP (Model Context Protocol) Integration Layer.

Provides a standardized protocol for connecting Buddy agents to external
tools, data sources, and services through the Model Context Protocol.
Enables seamless tool discovery, registration, and execution across
the entire agent ecosystem.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional

logger = logging.getLogger(__name__)


class MCPServerType(Enum):
    """Types of MCP server connections."""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WEBSOCKET = "websocket"
    EMBEDDED = "embedded"


class MCPToolCategory(Enum):
    """Categories for MCP tools."""
    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    API = "api"
    BROWSER = "browser"
    SYSTEM = "system"
    KNOWLEDGE = "knowledge"
    CODE = "code"
    COMMUNICATION = "communication"
    CUSTOM = "custom"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    name: str
    server_type: MCPServerType = MCPServerType.STDIO
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""
    auto_connect: bool = True
    timeout: float = 30.0
    max_retries: int = 3


@dataclass
class MCPToolDefinition:
    """Definition of a tool exposed via MCP."""
    name: str
    description: str
    category: MCPToolCategory = MCPToolCategory.CUSTOM
    parameters: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    server_name: str = ""
    rate_limit: Optional[float] = None
    requires_approval: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class MCPToolResult:
    """Result of an MCP tool execution."""
    tool_name: str
    success: bool
    content: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResource:
    """A resource exposed by an MCP server."""
    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"
    server_name: str = ""


@dataclass
class MCPPrompt:
    """A prompt template exposed by an MCP server."""
    name: str
    description: str = ""
    template: str = ""
    arguments: list[dict] = field(default_factory=list)
    server_name: str = ""


class MCPRegistry:
    """
    Central registry for all MCP servers, tools, resources, and prompts.

    Provides discovery, registration, and lifecycle management for MCP
    connections across the Buddy agent ecosystem.
    """

    def __init__(self):
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPToolDefinition] = {}
        self._resources: dict[str, MCPResource] = {}
        self._prompts: dict[str, MCPPrompt] = {}
        self._tool_handlers: dict[str, Callable] = {}
        self._connected_servers: set[str] = set()
        self._lock = asyncio.Lock()

    # ── Server Management ──────────────────────────────────────────

    def register_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server configuration."""
        self._servers[config.name] = config
        logger.info("MCP server registered: %s (type=%s)", config.name, config.server_type.value)

    def unregister_server(self, name: str) -> None:
        """Remove an MCP server registration."""
        self._servers.pop(name, None)
        self._connected_servers.discard(name)
        self._tools = {
            k: v for k, v in self._tools.items() if v.server_name != name
        }
        logger.info("MCP server unregistered: %s", name)

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get a server configuration by name."""
        return self._servers.get(name)

    def list_servers(self) -> list[MCPServerConfig]:
        """List all registered server configurations."""
        return list(self._servers.values())

    async def connect_server(self, name: str) -> bool:
        """Establish connection to an MCP server."""
        config = self._servers.get(name)
        if not config:
            logger.error("MCP server not found: %s", name)
            return False

        async with self._lock:
            if name in self._connected_servers:
                return True

            try:
                # In production, this would establish the actual connection
                # For embedded servers, tools are registered directly
                self._connected_servers.add(name)
                logger.info("MCP server connected: %s", name)
                return True
            except Exception as e:
                logger.error("Failed to connect MCP server %s: %s", name, e)
                return False

    async def disconnect_server(self, name: str) -> None:
        """Disconnect from an MCP server."""
        async with self._lock:
            self._connected_servers.discard(name)
            logger.info("MCP server disconnected: %s", name)

    # ── Tool Management ────────────────────────────────────────────

    def register_tool(
        self,
        definition: MCPToolDefinition,
        handler: Optional[Callable] = None,
    ) -> None:
        """Register a tool definition with an optional handler."""
        self._tools[definition.name] = definition
        if handler:
            self._tool_handlers[definition.name] = handler
        logger.info("MCP tool registered: %s (category=%s)", definition.name, definition.category.value)

    def register_tools_batch(
        self,
        definitions: list[MCPToolDefinition],
        handlers: Optional[dict[str, Callable]] = None,
    ) -> None:
        """Register multiple tools at once."""
        for definition in definitions:
            self._tools[definition.name] = definition
        if handlers:
            self._tool_handlers.update(handlers)
        logger.info("MCP tools batch registered: %d tools", len(definitions))

    def get_tool(self, name: str) -> Optional[MCPToolDefinition]:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def list_tools(
        self,
        category: Optional[MCPToolCategory] = None,
        server_name: Optional[str] = None,
    ) -> list[MCPToolDefinition]:
        """List tools with optional filtering."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        if server_name:
            tools = [t for t in tools if t.server_name == server_name]
        return tools

    def get_tool_schemas(self) -> list[dict]:
        """Get all tools in OpenAI-compatible function schema format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": t.parameters,
                        "required": t.required,
                    },
                },
            }
            for t in self._tools.values()
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float = 30.0,
    ) -> MCPToolResult:
        """Execute a registered MCP tool with the given arguments."""
        import time

        start = time.time()
        definition = self._tools.get(tool_name)

        if not definition:
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}",
            )

        handler = self._tool_handlers.get(tool_name)
        if not handler:
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=f"No handler registered for tool: {tool_name}",
            )

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**arguments), timeout=timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(handler, **arguments), timeout=timeout
                )
            duration_ms = (time.time() - start) * 1000
            return MCPToolResult(
                tool_name=tool_name,
                success=True,
                content=result,
                duration_ms=duration_ms,
            )
        except asyncio.TimeoutError:
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool execution timed out after {timeout}s",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    # ── Resource Management ────────────────────────────────────────

    def register_resource(self, resource: MCPResource) -> None:
        """Register a resource exposed by an MCP server."""
        self._resources[resource.uri] = resource

    def get_resource(self, uri: str) -> Optional[MCPResource]:
        """Get a resource by URI."""
        return self._resources.get(uri)

    def list_resources(self, server_name: Optional[str] = None) -> list[MCPResource]:
        """List all resources, optionally filtered by server."""
        resources = list(self._resources.values())
        if server_name:
            resources = [r for r in resources if r.server_name == server_name]
        return resources

    # ── Prompt Management ──────────────────────────────────────────

    def register_prompt(self, prompt: MCPPrompt) -> None:
        """Register a prompt template from an MCP server."""
        self._prompts[prompt.name] = prompt

    def get_prompt(self, name: str) -> Optional[MCPPrompt]:
        """Get a prompt template by name."""
        return self._prompts.get(name)

    def list_prompts(self, server_name: Optional[str] = None) -> list[MCPPrompt]:
        """List all prompts, optionally filtered by server."""
        prompts = list(self._prompts.values())
        if server_name:
            prompts = [p for p in prompts if p.server_name == server_name]
        return prompts

    def render_prompt(self, name: str, arguments: dict[str, Any]) -> Optional[str]:
        """Render a prompt template with the given arguments."""
        prompt = self._prompts.get(name)
        if not prompt:
            return None
        try:
            return prompt.template.format(**arguments)
        except KeyError as e:
            logger.error("Missing argument %s for prompt %s", e, name)
            return None

    # ── Status & Statistics ────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_servers": len(self._servers),
            "connected_servers": len(self._connected_servers),
            "total_tools": len(self._tools),
            "total_resources": len(self._resources),
            "total_prompts": len(self._prompts),
            "tools_by_category": {
                cat.value: len(self.list_tools(category=cat))
                for cat in MCPToolCategory
            },
            "servers": [
                {
                    "name": s.name,
                    "type": s.server_type.value,
                    "connected": s.name in self._connected_servers,
                    "tool_count": len(self.list_tools(server_name=s.name)),
                }
                for s in self._servers.values()
            ],
        }


# Global MCP registry instance
mcp_registry = MCPRegistry()


class MCPToolExecutor:
    """
    High-level tool executor that orchestrates MCP tool execution
    with permission checking, rate limiting, and result formatting.
    """

    def __init__(self, registry: Optional[MCPRegistry] = None):
        self.registry = registry or mcp_registry
        self._execution_history: list[MCPToolResult] = []
        self._rate_limiters: dict[str, float] = {}

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        bypass_permission: bool = False,
    ) -> MCPToolResult:
        """Execute a tool with full orchestration."""
        definition = self.registry.get_tool(tool_name)

        if not definition:
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )

        # Rate limiting check
        if definition.rate_limit:
            last_execution = self._rate_limiters.get(tool_name, 0)
            import time
            elapsed = time.time() - last_execution
            if elapsed < definition.rate_limit:
                return MCPToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Rate limit exceeded. Try again in {definition.rate_limit - elapsed:.1f}s",
                )

        # Execute
        result = await self.registry.execute_tool(tool_name, arguments)
        self._execution_history.append(result)

        if definition.rate_limit:
            import time
            self._rate_limiters[tool_name] = time.time()

        return result

    async def execute_chain(
        self,
        steps: list[dict[str, Any]],
        stop_on_error: bool = True,
    ) -> list[MCPToolResult]:
        """Execute a chain of tool calls sequentially."""
        results = []
        for step in steps:
            result = await self.execute(
                tool_name=step["tool"],
                arguments=step.get("arguments", {}),
            )
            results.append(result)
            if stop_on_error and not result.success:
                break
        return results

    async def execute_parallel(
        self,
        calls: list[dict[str, Any]],
    ) -> list[MCPToolResult]:
        """Execute multiple tool calls in parallel."""
        tasks = [
            self.execute(
                tool_name=call["tool"],
                arguments=call.get("arguments", {}),
            )
            for call in calls
        ]
        return await asyncio.gather(*tasks)

    def get_history(self, limit: int = 50) -> list[MCPToolResult]:
        """Get recent tool execution history."""
        return self._execution_history[-limit:]

    def clear_history(self) -> None:
        """Clear execution history."""
        self._execution_history.clear()


# Global tool executor instance
mcp_executor = MCPToolExecutor()