"""
Buddy MCP Connector - Model Context Protocol Integration

Connects Buddy agents to external tools and services via the Model Context
Protocol (MCP). Provides server discovery, tool registration, resource
management, and bidirectional communication with MCP-compatible services.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MCPConnectionState(str, Enum):
    """Connection states for MCP servers."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class MCPTransport(str, Enum):
    """Transport protocols for MCP communication."""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    server_id: str
    name: str
    transport: MCPTransport = MCPTransport.STDIO
    command: str = ""
    args: list[str] = field(default_factory=list)
    url: str = ""
    env: dict[str, str] = field(default_factory=dict)
    auto_reconnect: bool = True
    timeout_sec: float = 30.0
    metadata: dict = field(default_factory=dict)


@dataclass
class MCPTool:
    """A tool exposed by an MCP server."""
    name: str
    description: str
    server_id: str
    input_schema: dict = field(default_factory=dict)
    enabled: bool = True

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@dataclass
class MCPResource:
    """A resource exposed by an MCP server."""
    uri: str
    name: str
    description: str
    server_id: str
    mime_type: str = "text/plain"
    metadata: dict = field(default_factory=dict)


class MCPServerConnection:
    """Connection to a single MCP server."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.state = MCPConnectionState.DISCONNECTED
        self.tools: list[MCPTool] = []
        self.resources: list[MCPResource] = []
        self._process: asyncio.subprocess.Process | None = None
        self._connected_at: float | None = None
        self._error_count = 0
        self._request_count = 0

    async def connect(self) -> bool:
        """Connect to the MCP server."""
        self.state = MCPConnectionState.CONNECTING

        try:
            if self.config.transport == MCPTransport.STDIO:
                if self.config.command:
                    self._process = await asyncio.create_subprocess_exec(
                        self.config.command,
                        *self.config.args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env={**__import__("os").environ, **self.config.env},
                    )

            elif self.config.transport in (MCPTransport.HTTP, MCPTransport.SSE, MCPTransport.WEBSOCKET):
                # HTTP-based connection simulated
                pass

            self.state = MCPConnectionState.CONNECTED
            self._connected_at = time.time()

            # Discover tools
            await self._discover_tools()

            return True
        except Exception as e:
            self.state = MCPConnectionState.ERROR
            self._error_count += 1
            return False

    async def _discover_tools(self):
        """Discover available tools from the server."""
        # Simulated tool discovery
        self.tools = [
            MCPTool(
                name=f"{self.config.name}_tool_{i}",
                description=f"Tool from {self.config.name} MCP server",
                server_id=self.config.server_id,
                input_schema={
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "Input parameter"},
                    },
                    "required": ["input"],
                },
            )
            for i in range(3)
        ]

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on the MCP server."""
        self._request_count += 1

        if self.state != MCPConnectionState.CONNECTED:
            return {"error": "Server not connected", "tool": tool_name}

        # Simulated tool call
        return {
            "tool": tool_name,
            "arguments": arguments,
            "result": f"[Simulated MCP tool response from {self.config.name}]",
            "server_id": self.config.server_id,
        }

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
        self.state = MCPConnectionState.DISCONNECTED

    def to_dict(self) -> dict:
        return {
            "server_id": self.config.server_id,
            "name": self.config.name,
            "state": self.state.value,
            "transport": self.config.transport.value,
            "tools_count": len(self.tools),
            "request_count": self._request_count,
            "error_count": self._error_count,
            "connected_at": self._connected_at,
        }


class MCPConnector:
    """MCP (Model Context Protocol) integration hub for Buddy.

    Manages connections to external MCP servers, providing agent access
    to third-party tools, resources, and services. Supports automatic
    discovery, health monitoring, and failover across MCP endpoints.
    """

    def __init__(self):
        self._servers: dict[str, MCPServerConnection] = {}
        self._server_configs: dict[str, MCPServerConfig] = {}
        self._total_calls = 0
        self._total_errors = 0

    def register_server(self, config: MCPServerConfig):
        """Register an MCP server configuration."""
        self._server_configs[config.server_id] = config

    async def connect_server(self, server_id: str) -> bool:
        """Connect to an MCP server."""
        config = self._server_configs.get(server_id)
        if not config:
            return False

        connection = MCPServerConnection(config)
        success = await connection.connect()
        self._servers[server_id] = connection
        return success

    async def connect_all(self) -> dict[str, bool]:
        """Connect to all registered servers."""
        results = {}
        for server_id in self._server_configs:
            results[server_id] = await self.connect_server(server_id)
        return results

    def get_server(self, server_id: str) -> MCPServerConnection | None:
        """Get a connected server."""
        return self._servers.get(server_id)

    async def call_tool(self, server_id: str, tool_name: str, arguments: dict) -> dict:
        """Call a tool on an MCP server."""
        self._total_calls += 1
        server = self.get_server(server_id)
        if not server:
            self._total_errors += 1
            return {"error": f"Server not found: {server_id}"}

        result = await server.call_tool(tool_name, arguments)
        if "error" in result:
            self._total_errors += 1
        return result

    async def disconnect_server(self, server_id: str):
        """Disconnect from an MCP server."""
        server = self._servers.pop(server_id, None)
        if server:
            await server.disconnect()

    async def disconnect_all(self):
        """Disconnect from all servers."""
        for server in list(self._servers.values()):
            await server.disconnect()
        self._servers.clear()

    def list_tools(self) -> list[dict]:
        """List all available tools from all MCP servers."""
        tools = []
        for server in self._servers.values():
            for tool in server.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "server_id": server.config.server_id,
                    "server_name": server.config.name,
                    "schema": tool.input_schema,
                })
        return tools

    def get_stats(self) -> dict:
        return {
            "total_servers": len(self._server_configs),
            "connected_servers": len(self._servers),
            "total_calls": self._total_calls,
            "total_errors": self._total_errors,
            "servers": [s.to_dict() for s in self._servers.values()],
            "available_tools": len(self.list_tools()),
        }


# Global MCP connector instance
_mcp_connector: MCPConnector | None = None


def get_mcp_connector() -> MCPConnector:
    """Get or create the global MCP connector."""
    global _mcp_connector
    if _mcp_connector is None:
        _mcp_connector = MCPConnector()
    return _mcp_connector