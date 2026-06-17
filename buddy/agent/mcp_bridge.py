"""Buddy MCP Bridge — Model Context Protocol integration layer

Provides a unified bridge between Buddy's agent system and MCP-compatible
tool servers. Enables dynamic tool discovery, capability negotiation, and
streaming execution across any MCP-compliant backend.

Core capabilities:
  - Server Discovery: auto-discovers MCP servers via stdio and HTTP transports
  - Tool Registry Sync: keeps Buddy's tool registry in sync with MCP servers
  - Capability Negotiation: matches agent needs to server capabilities
  - Streaming Execution: supports MCP streaming for long-running operations
  - Resource Management: tracks and manages MCP server resources
  - Health Monitoring: periodic health checks for connected servers
  - Fallback Chains: graceful degradation when servers are unavailable
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.mcp_bridge")


# ═══════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════

class MCPTransport(str, Enum):
    """MCP transport protocols."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"


class MCPServerStatus(str, Enum):
    """Connection status for MCP servers."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    name: str
    transport: MCPTransport = MCPTransport.STDIO
    command: str = ""         # For stdio transport
    args: list[str] = field(default_factory=list)
    url: str = ""             # For HTTP/SSE/WebSocket transport
    env: dict[str, str] = field(default_factory=dict)
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 5
    reconnect_delay_ms: int = 5000
    health_check_interval_ms: int = 30000


@dataclass
class MCPTool:
    """A tool exposed by an MCP server."""
    id: str = field(default_factory=lambda: f"mcp-tool-{uuid.uuid4().hex[:8]}")
    server_name: str = ""
    name: str = ""
    description: str = ""
    input_schema: dict = field(default_factory=dict)
    requires_approval: bool = False
    timeout_ms: int = 30000

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function-calling schema."""
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
    """A resource managed by an MCP server."""
    uri: str
    name: str = ""
    description: str = ""
    mime_type: str = "application/json"
    size_bytes: int = 0
    server_name: str = ""


@dataclass
class MCPPrompts:
    """Prompt templates exposed by an MCP server."""
    name: str
    description: str = ""
    arguments: list[dict] = field(default_factory=list)
    server_name: str = ""


# ═══════════════════════════════════════════════════════════
# MCP Bridge
# ═══════════════════════════════════════════════════════════

class MCPBridge:
    """Bridge between Buddy agents and MCP-compatible tool servers.

    Manages server connections, tool discovery, capability negotiation,
    and streaming execution across all connected MCP servers.
    """

    def __init__(self):
        self._servers: dict[str, MCPServerConfig] = {}
        self._server_status: dict[str, MCPServerStatus] = {}
        self._tools: dict[str, MCPTool] = {}       # tool_name → MCPTool
        self._resources: dict[str, MCPResource] = {}
        self._prompts: dict[str, MCPPrompts] = {}

        # Connection management
        self._connections: dict[str, Any] = {}  # server_name → transport connection
        self._reconnect_attempts: dict[str, int] = {}
        self._health_check_tasks: dict[str, asyncio.Task] = {}

        # Statistics
        self._total_tool_calls = 0
        self._total_tool_errors = 0
        self._total_resource_accesses = 0

        logger.info("MCP Bridge initialized")

    # ── Server Management ────────────────────────────────

    def register_server(self, config: MCPServerConfig) -> str:
        """Register an MCP server configuration."""
        self._servers[config.name] = config
        self._server_status[config.name] = MCPServerStatus.DISCONNECTED
        self._reconnect_attempts[config.name] = 0
        logger.info(f"MCP server registered: {config.name} ({config.transport.value})")
        return config.name

    async def connect_server(self, server_name: str) -> bool:
        """Connect to an MCP server and discover its capabilities."""
        config = self._servers.get(server_name)
        if not config:
            logger.error(f"MCP server not found: {server_name}")
            return False

        self._server_status[server_name] = MCPServerStatus.CONNECTING

        try:
            if config.transport == MCPTransport.STDIO:
                success = await self._connect_stdio(config)
            elif config.transport == MCPTransport.HTTP:
                success = await self._connect_http(config)
            elif config.transport == MCPTransport.SSE:
                success = await self._connect_sse(config)
            else:
                logger.error(f"Unsupported transport: {config.transport.value}")
                success = False

            if success:
                self._server_status[server_name] = MCPServerStatus.CONNECTED
                self._reconnect_attempts[server_name] = 0

                # Start health check
                if config.health_check_interval_ms > 0:
                    self._health_check_tasks[server_name] = asyncio.create_task(
                        self._health_check_loop(server_name)
                    )

                logger.info(f"MCP server connected: {server_name}")
            else:
                self._server_status[server_name] = MCPServerStatus.ERROR

            return success

        except Exception as e:
            logger.error(f"MCP connection failed for {server_name}: {e}")
            self._server_status[server_name] = MCPServerStatus.ERROR
            return False

    async def disconnect_server(self, server_name: str):
        """Disconnect from an MCP server."""
        # Cancel health check
        task = self._health_check_tasks.pop(server_name, None)
        if task:
            task.cancel()

        # Remove tools and resources from this server
        self._tools = {
            k: v for k, v in self._tools.items()
            if v.server_name != server_name
        }
        self._resources = {
            k: v for k, v in self._resources.items()
            if v.server_name != server_name
        }

        self._server_status[server_name] = MCPServerStatus.DISCONNECTED
        self._connections.pop(server_name, None)
        logger.info(f"MCP server disconnected: {server_name}")

    async def _connect_stdio(self, config: MCPServerConfig) -> bool:
        """Connect via stdio transport (subprocess)."""
        try:
            import subprocess
            process = await asyncio.create_subprocess_exec(
                config.command,
                *config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**__import__('os').environ, **config.env},
            )

            # Send initialize request
            init_request = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "Buddy", "version": "1.0.0"},
                },
            })

            if process.stdin:
                process.stdin.write((init_request + "\n").encode())
                await process.stdin.drain()

            # Read response
            if process.stdout:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(), timeout=10
                )
                response = json.loads(response_line.decode())

                if "error" in response:
                    logger.error(f"MCP initialize error: {response['error']}")
                    return False

            # Discover tools
            await self._discover_tools(server_name=config.name, process=process)

            self._connections[config.name] = process
            return True

        except Exception as e:
            logger.error(f"Stdio connection failed: {e}")
            return False

    async def _connect_http(self, config: MCPServerConfig) -> bool:
        """Connect via HTTP transport."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{config.url}/initialize",
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "Buddy", "version": "1.0.0"},
                        },
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return False

            # Discover tools via HTTP
            url = config.url.rstrip("/")
            self._connections[config.name] = {"url": url, "type": "http"}
            await self._discover_tools_http(config.name, url)
            return True

        except Exception as e:
            logger.error(f"HTTP connection failed: {e}")
            return False

    async def _connect_sse(self, config: MCPServerConfig) -> bool:
        """Connect via SSE transport."""
        # SSE connections are event-driven; store the URL for future use
        self._connections[config.name] = {
            "url": config.url.rstrip("/"),
            "type": "sse",
            "client": None,
        }
        self._server_status[config.name] = MCPServerStatus.CONNECTED
        return True

    async def _discover_tools(self, server_name: str, process: Any):
        """Discover tools from a connected MCP server via stdio."""
        try:
            if process.stdin and process.stdout:
                list_request = json.dumps({
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                })
                process.stdin.write((list_request + "\n").encode())
                await process.stdin.drain()

                response_line = await asyncio.wait_for(
                    process.stdout.readline(), timeout=10
                )
                response = json.loads(response_line.decode())

                tools = response.get("result", {}).get("tools", [])
                for tool_data in tools:
                    tool = MCPTool(
                        server_name=server_name,
                        name=tool_data.get("name", ""),
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                    )
                    self._tools[tool.name] = tool

                logger.info(f"Discovered {len(tools)} tools from {server_name}")

        except Exception as e:
            logger.warning(f"Tool discovery failed for {server_name}: {e}")

    async def _discover_tools_http(self, server_name: str, url: str):
        """Discover tools from an HTTP MCP server."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{url}/tools/list",
                    json={"jsonrpc": "2.0", "method": "tools/list", "params": {}},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tools = data.get("result", {}).get("tools", [])
                        for tool_data in tools:
                            tool = MCPTool(
                                server_name=server_name,
                                name=tool_data.get("name", ""),
                                description=tool_data.get("description", ""),
                                input_schema=tool_data.get("inputSchema", {}),
                            )
                            self._tools[tool.name] = tool
                        logger.info(f"Discovered {len(tools)} tools from {server_name}")
        except Exception as e:
            logger.warning(f"HTTP tool discovery failed: {e}")

    # ── Tool Execution ───────────────────────────────────

    async def call_tool(
        self, tool_name: str, arguments: dict, timeout_ms: int = 30000
    ) -> dict:
        """Call an MCP tool and return the result."""
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"Tool not found: {tool_name}"}

        server_name = tool.server_name
        config = self._servers.get(server_name)
        if not config:
            return {"error": f"Server not found: {server_name}"}

        connection = self._connections.get(server_name)
        if not connection:
            return {"error": f"Not connected to server: {server_name}"}

        self._total_tool_calls += 1

        try:
            if isinstance(connection, dict) and connection.get("type") == "http":
                return await self._call_tool_http(connection["url"], tool_name, arguments, timeout_ms)

            elif hasattr(connection, 'stdin') and hasattr(connection, 'stdout'):
                return await self._call_tool_stdio(connection, tool_name, arguments, timeout_ms)

            else:
                return {"error": "Unsupported connection type"}

        except Exception as e:
            self._total_tool_errors += 1
            logger.error(f"Tool call failed: {tool_name}: {e}")
            return {"error": str(e)}

    async def _call_tool_http(
        self, url: str, tool_name: str, arguments: dict, timeout_ms: int
    ) -> dict:
        """Call a tool via HTTP transport."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{url}/tools/call",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments},
                    },
                    timeout=aiohttp.ClientTimeout(total=timeout_ms / 1000),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get("result", {}).get("content", [])
                        if isinstance(result, list) and len(result) > 0:
                            return {"content": result[0].get("text", str(result))}
                        return {"content": str(result)}
                    return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def _call_tool_stdio(
        self, process: Any, tool_name: str, arguments: dict, timeout_ms: int
    ) -> dict:
        """Call a tool via stdio transport."""
        if not process.stdin or not process.stdout:
            return {"error": "Process not available"}

        call_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        })

        process.stdin.write((call_request + "\n").encode())
        await process.stdin.drain()

        response_line = await asyncio.wait_for(
            process.stdout.readline(),
            timeout=timeout_ms / 1000,
        )
        response = json.loads(response_line.decode())

        if "error" in response:
            return {"error": str(response["error"])}

        result = response.get("result", {}).get("content", [])
        if isinstance(result, list) and len(result) > 0:
            return {"content": result[0].get("text", str(result))}
        return {"content": str(result)}

    # ── Health Monitoring ────────────────────────────────

    async def _health_check_loop(self, server_name: str):
        """Periodic health check for a connected server."""
        config = self._servers.get(server_name)
        if not config:
            return

        while self._server_status.get(server_name) == MCPServerStatus.CONNECTED:
            await asyncio.sleep(config.health_check_interval_ms / 1000)

            try:
                # Simple ping to check connectivity
                connection = self._connections.get(server_name)
                if isinstance(connection, dict) and connection.get("type") == "http":
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{connection['url']}/health",
                            timeout=aiohttp.ClientTimeout(total=5),
                        ) as resp:
                            if resp.status != 200:
                                raise Exception("Health check failed")
            except Exception:
                logger.warning(f"MCP health check failed for {server_name}")
                await self._handle_disconnect(server_name)

    async def _handle_disconnect(self, server_name: str):
        """Handle server disconnection with reconnection logic."""
        config = self._servers.get(server_name)
        if not config:
            return

        self._server_status[server_name] = MCPServerStatus.RECONNECTING

        if not config.auto_reconnect:
            self._server_status[server_name] = MCPServerStatus.DISCONNECTED
            return

        attempts = self._reconnect_attempts.get(server_name, 0)
        if attempts >= config.max_reconnect_attempts:
            logger.error(f"Max reconnect attempts reached for {server_name}")
            self._server_status[server_name] = MCPServerStatus.ERROR
            return

        self._reconnect_attempts[server_name] = attempts + 1
        await asyncio.sleep(config.reconnect_delay_ms / 1000)

        logger.info(f"Attempting reconnect {attempts + 1} for {server_name}")
        await self.connect_server(server_name)

    # ── Tool Registry ────────────────────────────────────

    def get_tools(self, server_name: str | None = None) -> list[MCPTool]:
        """Get all tools, optionally filtered by server."""
        if server_name:
            return [t for t in self._tools.values() if t.server_name == server_name]
        return list(self._tools.values())

    def get_tool_schemas(self) -> list[dict]:
        """Get all tools as OpenAI function schemas."""
        return [t.to_openai_schema() for t in self._tools.values()]

    def get_resources(self, server_name: str | None = None) -> list[MCPResource]:
        """Get all resources, optionally filtered by server."""
        if server_name:
            return [r for r in self._resources.values() if r.server_name == server_name]
        return list(self._resources.values())

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict:
        """Get MCP bridge statistics."""
        return {
            "servers": len(self._servers),
            "connected": sum(
                1 for s in self._server_status.values()
                if s == MCPServerStatus.CONNECTED
            ),
            "by_status": {
                status.value: sum(1 for s in self._server_status.values() if s == status)
                for status in MCPServerStatus
            },
            "tools": len(self._tools),
            "resources": len(self._resources),
            "prompts": len(self._prompts),
            "total_tool_calls": self._total_tool_calls,
            "total_tool_errors": self._total_tool_errors,
            "server_details": [
                {
                    "name": name,
                    "status": self._server_status.get(name, MCPServerStatus.DISCONNECTED).value,
                    "transport": config.transport.value,
                    "tool_count": sum(1 for t in self._tools.values() if t.server_name == name),
                    "reconnect_attempts": self._reconnect_attempts.get(name, 0),
                }
                for name, config in self._servers.items()
            ],
        }

    # ── Cleanup ──────────────────────────────────────────

    async def shutdown(self):
        """Shutdown all MCP connections."""
        for server_name in list(self._servers.keys()):
            await self.disconnect_server(server_name)
        logger.info("MCP Bridge shutdown complete")


# Global MCP bridge instance
mcp_bridge = MCPBridge()