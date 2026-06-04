"""Buddy MCP Integration — Model Context Protocol server connectivity

Enables agents to connect to MCP-compatible tool servers, discover their
capabilities, and invoke remote tools through a standardized protocol.
"""
from __future__ import annotations
import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.mcp")


class MCPServerStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MCPTransport(str, Enum):
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class MCPServerConfig:
    id: str
    name: str
    transport: MCPTransport = MCPTransport.HTTP
    endpoint: str = ""
    command: str = ""  # For stdio transport
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    auto_reconnect: bool = True
    max_retries: int = 3


@dataclass
class MCPTool:
    name: str
    description: str = ""
    server_id: str = ""
    input_schema: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "server_id": self.server_id,
            "input_schema": self.input_schema,
        }


@dataclass
class MCPResource:
    uri: str
    name: str = ""
    description: str = ""
    mime_type: str = "text/plain"
    server_id: str = ""


@dataclass
class MCPServerState:
    config: MCPServerConfig
    status: MCPServerStatus = MCPServerStatus.DISCONNECTED
    tools: list[MCPTool] = field(default_factory=list)
    resources: list[MCPResource] = field(default_factory=list)
    connected_at: str = ""
    last_error: str = ""


class MCPRegistry:
    """Registry for MCP-compatible tool server connections."""

    def __init__(self):
        self._servers: dict[str, MCPServerState] = {}
        self._tools: dict[str, MCPTool] = {}
        self._connection_tasks: dict[str, asyncio.Task] = {}

    def register_server(self, config: MCPServerConfig) -> MCPServerState:
        """Register an MCP server configuration."""
        state = MCPServerState(config=config)
        self._servers[config.id] = state
        logger.info(f"MCP server registered: {config.name} ({config.transport.value})")
        return state

    def unregister_server(self, server_id: str) -> bool:
        """Remove a server registration."""
        if server_id in self._connection_tasks:
            self._connection_tasks[server_id].cancel()
            del self._connection_tasks[server_id]

        state = self._servers.pop(server_id, None)
        if state:
            # Remove tools from this server
            for tool in state.tools:
                self._tools.pop(tool.name, None)
            logger.info(f"MCP server unregistered: {state.config.name}")
            return True
        return False

    async def connect_server(self, server_id: str) -> bool:
        """Connect to an MCP server and discover its tools."""
        state = self._servers.get(server_id)
        if not state:
            return False

        state.status = MCPServerStatus.CONNECTING
        config = state.config

        try:
            if config.transport == MCPTransport.HTTP:
                success = await self._connect_http(state)
            elif config.transport == MCPTransport.STDIO:
                success = await self._connect_stdio(state)
            elif config.transport == MCPTransport.WEBSOCKET:
                success = await self._connect_websocket(state)
            else:
                state.status = MCPServerStatus.ERROR
                state.last_error = f"Unsupported transport: {config.transport.value}"
                return False

            if success:
                state.status = MCPServerStatus.CONNECTED
                state.connected_at = datetime.now(timezone.utc).isoformat()
                # Register discovered tools
                for tool in state.tools:
                    self._tools[tool.name] = tool
                logger.info(f"MCP server connected: {config.name} ({len(state.tools)} tools)")
                return True
            else:
                state.status = MCPServerStatus.ERROR
                return False

        except Exception as e:
            state.status = MCPServerStatus.ERROR
            state.last_error = str(e)
            logger.error(f"MCP connection failed for {config.name}: {e}")
            return False

    async def _connect_http(self, state: MCPServerState) -> bool:
        """Connect via HTTP transport with tool discovery."""
        import aiohttp

        config = state.config
        try:
            async with aiohttp.ClientSession() as session:
                # Initialize connection
                init_url = f"{config.endpoint}/initialize"
                async with session.post(init_url, json={
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "Buddy", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                }) as resp:
                    if resp.status != 200:
                        state.last_error = f"HTTP {resp.status}"
                        return False
                    init_data = await resp.json()

                # Discover tools
                tools_url = f"{config.endpoint}/tools/list"
                async with session.get(tools_url) as resp:
                    if resp.status == 200:
                        tools_data = await resp.json()
                        for td in tools_data.get("tools", []):
                            tool = MCPTool(
                                name=td.get("name", ""),
                                description=td.get("description", ""),
                                server_id=config.id,
                                input_schema=td.get("inputSchema", {}),
                            )
                            state.tools.append(tool)

                # Discover resources
                resources_url = f"{config.endpoint}/resources/list"
                async with session.get(resources_url) as resp:
                    if resp.status == 200:
                        resources_data = await resp.json()
                        for rd in resources_data.get("resources", []):
                            resource = MCPResource(
                                uri=rd.get("uri", ""),
                                name=rd.get("name", ""),
                                description=rd.get("description", ""),
                                mime_type=rd.get("mimeType", "text/plain"),
                                server_id=config.id,
                            )
                            state.resources.append(resource)

                return True

        except Exception as e:
            state.last_error = str(e)
            logger.error(f"MCP HTTP connection error: {e}")
            return False

    async def _connect_stdio(self, state: MCPServerState) -> bool:
        """Connect via stdio transport (subprocess)."""
        state.last_error = "Stdio transport requires subprocess management — not yet implemented"
        logger.warning(f"Stdio MCP transport not implemented for {state.config.name}")
        return False

    async def _connect_websocket(self, state: MCPServerState) -> bool:
        """Connect via WebSocket transport."""
        state.last_error = "WebSocket transport requires aiohttp session — not yet implemented"
        logger.warning(f"WebSocket MCP transport not implemented for {state.config.name}")
        return False

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Invoke a tool on a connected MCP server."""
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"MCP tool not found: {tool_name}"}

        state = self._servers.get(tool.server_id)
        if not state or state.status != MCPServerStatus.CONNECTED:
            return {"error": f"Server not connected: {tool.server_id}"}

        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                call_url = f"{state.config.endpoint}/tools/call"
                async with session.post(call_url, json={
                    "name": tool_name,
                    "arguments": arguments,
                }) as resp:
                    return await resp.json()
        except Exception as e:
            logger.error(f"MCP tool call failed: {tool_name} -> {e}")
            return {"error": str(e)}

    def get_tools(self, server_id: str | None = None) -> list[MCPTool]:
        """Get all discovered tools, optionally filtered by server."""
        tools = list(self._tools.values())
        if server_id:
            tools = [t for t in tools if t.server_id == server_id]
        return tools

    def get_resources(self, server_id: str | None = None) -> list[MCPResource]:
        """Get all discovered resources."""
        all_resources = []
        for state in self._servers.values():
            if server_id and state.config.id != server_id:
                continue
            all_resources.extend(state.resources)
        return all_resources

    def get_server_states(self) -> list[dict]:
        """Get all server states."""
        return [
            {
                "id": s.config.id,
                "name": s.config.name,
                "transport": s.config.transport.value,
                "endpoint": s.config.endpoint,
                "status": s.status.value,
                "tool_count": len(s.tools),
                "resource_count": len(s.resources),
                "connected_at": s.connected_at,
                "last_error": s.last_error,
            }
            for s in self._servers.values()
        ]

    def get_tool_count(self, server_id: str) -> int:
        """Get the number of tools discovered from a server."""
        state = self._servers.get(server_id)
        return len(state.tools) if state else 0

    def get_resource_count(self, server_id: str) -> int:
        """Get the number of resources discovered from a server."""
        state = self._servers.get(server_id)
        return len(state.resources) if state else 0

    def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from an MCP server."""
        state = self._servers.get(server_id)
        if not state:
            return False

        # Remove tools from global registry
        for tool in state.tools:
            self._tools.pop(tool.name, None)

        state.tools.clear()
        state.resources.clear()
        state.status = MCPServerStatus.DISCONNECTED
        logger.info(f"MCP server disconnected: {state.config.name}")
        return True

    async def connect_all(self) -> dict[str, bool]:
        """Connect to all registered servers."""
        results = {}
        for server_id in self._servers:
            results[server_id] = await self.connect_server(server_id)
        return results


mcp_registry = MCPRegistry()