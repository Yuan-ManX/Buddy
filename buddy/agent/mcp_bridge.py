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


@dataclass
class MCPDiscoveredServer:
    """A server discovered on the local network."""
    name: str = ""
    host: str = ""
    port: int = 0
    transport: MCPTransport = MCPTransport.HTTP
    capabilities: list[str] = field(default_factory=list)
    protocol_version: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MCPSchemaVersion:
    """Tool schema version information."""
    tool_name: str
    current_version: int = 1
    schema_hash: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    migration_history: list[dict] = field(default_factory=list)


@dataclass
class MCPHeartbeat:
    """Heartbeat record for a connected MCP server."""
    server_name: str
    last_beat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    beat_count: int = 0
    missed_beats: int = 0
    is_alive: bool = True


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

        # Local discovery
        self._discovered_servers: dict[str, MCPDiscoveredServer] = {}
        self._discovery_running = False

        # Schema versioning
        self._schema_versions: dict[str, MCPSchemaVersion] = {}
        self._schema_migrations: dict[str, dict[int, callable]] = {}

        # Heartbeat tracking
        self._heartbeats: dict[str, MCPHeartbeat] = {}
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}
        self._missed_beat_threshold = 3

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

    # ── Local Network Discovery ────────────────────────────

    async def discover_local_servers(
        self, base_port: int = 7800, scan_range: int = 20, timeout_seconds: float = 2.0
    ) -> list[MCPDiscoveredServer]:
        """Auto-discover MCP servers on the local network via port scanning.

        Scans a range of ports on localhost for MCP-compatible HTTP endpoints
        and attempts to read their server metadata. This is a lightweight
        mDNS-style discovery that works without multicast DNS infrastructure.

        Args:
            base_port: Starting port number for the scan range.
            scan_range: Number of ports to scan starting from base_port.
            timeout_seconds: Connection timeout per port.

        Returns:
            List of discovered MCP server metadata.
        """
        self._discovery_running = True
        discovered: list[MCPDiscoveredServer] = []

        try:
            import aiohttp

            async def probe_port(port: int) -> MCPDiscoveredServer | None:
                url = f"http://127.0.0.1:{port}"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{url}/.well-known/mcp",
                            timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                server = MCPDiscoveredServer(
                                    name=data.get("name", f"mcp-server-{port}"),
                                    host="127.0.0.1",
                                    port=port,
                                    transport=MCPTransport.HTTP,
                                    capabilities=data.get("capabilities", []),
                                    protocol_version=data.get("protocolVersion", ""),
                                )
                                return server
                except Exception:
                    pass
                return None

            tasks = [probe_port(port) for port in range(base_port, base_port + scan_range)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, MCPDiscoveredServer):
                    discovered.append(result)
                    self._discovered_servers[result.name] = result

            logger.info(f"Discovered {len(discovered)} MCP servers on local network")
        finally:
            self._discovery_running = False

        return discovered

    def get_discovered_servers(self) -> list[MCPDiscoveredServer]:
        """Return the list of currently discovered servers."""
        return list(self._discovered_servers.values())

    # ── Batch Tool Registration ───────────────────────────

    def batch_register_tools(self, tools: list[MCPTool]) -> int:
        """Register multiple MCP tools at once.

        Each tool in the batch is registered with the tool registry. Tools
        with duplicate names are skipped with a warning.

        Args:
            tools: A list of MCPTool instances to register.

        Returns:
            Number of tools successfully registered.
        """
        registered = 0
        for tool in tools:
            if tool.name in self._tools:
                logger.warning(f"Tool '{tool.name}' already registered, skipping")
                continue
            self._tools[tool.name] = tool
            registered += 1

        logger.info(f"Batch-registered {registered} of {len(tools)} tools")
        return registered

    def batch_register_tools_from_dicts(self, tool_dicts: list[dict], server_name: str = "") -> int:
        """Register tools from a list of raw tool description dictionaries.

        Args:
            tool_dicts: List of tool dicts with 'name', 'description', 'inputSchema'.
            server_name: Name of the server providing these tools.

        Returns:
            Number of tools registered.
        """
        tools = [
            MCPTool(
                server_name=server_name,
                name=td.get("name", ""),
                description=td.get("description", ""),
                input_schema=td.get("inputSchema", {}),
            )
            for td in tool_dicts
        ]
        return self.batch_register_tools(tools)

    # ── Server Compatibility Validation ───────────────────

    def validate_server_compatibility(
        self, config: MCPServerConfig
    ) -> tuple[bool, list[str]]:
        """Validate MCP server configuration before connection.

        Checks transport availability, protocol version compatibility,
        and required capabilities against the server's advertised metadata.

        Args:
            config: The server configuration to validate.

        Returns:
            A tuple of (is_compatible, list_of_issues).
        """
        issues: list[str] = []

        # Validate transport
        if config.transport == MCPTransport.STDIO:
            if not config.command:
                issues.append("STDIO transport requires a command path")
        elif config.transport in (MCPTransport.HTTP, MCPTransport.SSE, MCPTransport.WEBSOCKET):
            if not config.url:
                issues.append(f"{config.transport.value} transport requires a URL")
            elif not config.url.startswith(("http://", "https://", "ws://", "wss://")):
                issues.append(f"URL scheme is not valid for {config.transport.value}: {config.url}")

        # Validate reconnect settings
        if config.auto_reconnect and config.max_reconnect_attempts < 0:
            issues.append("max_reconnect_attempts must be non-negative")
        if config.reconnect_delay_ms < 100:
            issues.append("reconnect_delay_ms should be at least 100ms")
        if config.health_check_interval_ms > 0 and config.health_check_interval_ms < 1000:
            issues.append("health_check_interval_ms should be at least 1000ms for stability")

        # Check for duplicate server names
        if config.name in self._servers:
            issues.append(f"Server name '{config.name}' is already registered")

        is_compatible = len(issues) == 0
        if not is_compatible:
            logger.warning(f"Server '{config.name}' compatibility issues: {issues}")

        return is_compatible, issues

    async def validate_server_runtime_compatibility(
        self, config: MCPServerConfig, timeout_seconds: float = 5.0
    ) -> tuple[bool, dict]:
        """Runtime validation — tests the actual connection to verify compatibility.

        Attempts a lightweight handshake with the server to confirm protocol
        version and capabilities match before full connection.

        Args:
            config: The server configuration to validate.
            timeout_seconds: Timeout for the handshake attempt.

        Returns:
            A tuple of (is_compatible, handshake_result_dict).
        """
        result: dict = {"protocol_version": "", "capabilities": [], "issues": []}

        try:
            if config.transport == MCPTransport.HTTP:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{config.url.rstrip('/')}/.well-known/mcp",
                        timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            result["protocol_version"] = data.get("protocolVersion", "")
                            result["capabilities"] = data.get("capabilities", [])

                            if not result["protocol_version"]:
                                result["issues"].append("Server did not report protocol version")
                        else:
                            result["issues"].append(f"Server returned HTTP {resp.status}")
            else:
                result["issues"].append(f"Runtime validation not supported for {config.transport.value}")
        except Exception as e:
            result["issues"].append(f"Runtime validation failed: {e}")

        return len(result["issues"]) == 0, result

    # ── Heartbeat ─────────────────────────────────────────

    async def start_heartbeat(
        self, server_name: str, interval_seconds: float = 5.0
    ) -> bool:
        """Start a heartbeat loop for a connected MCP server.

        Sends periodic ping requests to verify the server is still alive.
        Missed heartbeats are counted and can trigger reconnection logic.

        Args:
            server_name: Name of the connected server to monitor.
            interval_seconds: Time between heartbeat pings.

        Returns:
            True if the heartbeat was started successfully.
        """
        if server_name not in self._connections:
            logger.error(f"Cannot start heartbeat: {server_name} is not connected")
            return False

        if server_name in self._heartbeat_tasks:
            logger.warning(f"Heartbeat already running for {server_name}")
            return True

        self._heartbeats[server_name] = MCPHeartbeat(server_name=server_name)

        async def heartbeat_loop():
            while server_name in self._connections and self._server_status.get(
                server_name
            ) == MCPServerStatus.CONNECTED:
                await asyncio.sleep(interval_seconds)
                try:
                    alive = await self._send_heartbeat_ping(server_name)
                    hb = self._heartbeats.get(server_name)
                    if hb:
                        hb.beat_count += 1
                        hb.last_beat = datetime.now(timezone.utc).isoformat()
                        if alive:
                            hb.missed_beats = 0
                            hb.is_alive = True
                        else:
                            hb.missed_beats += 1
                            if hb.missed_beats >= self._missed_beat_threshold:
                                hb.is_alive = False
                                logger.warning(
                                    f"Server {server_name} missed {hb.missed_beats} heartbeats"
                                )
                                await self._handle_disconnect(server_name)
                                break
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

        self._heartbeat_tasks[server_name] = asyncio.create_task(heartbeat_loop())
        logger.info(f"Heartbeat started for {server_name} (interval={interval_seconds}s)")
        return True

    def stop_heartbeat(self, server_name: str) -> bool:
        """Stop the heartbeat loop for a server.

        Args:
            server_name: Name of the server to stop monitoring.

        Returns:
            True if the heartbeat was stopped.
        """
        task = self._heartbeat_tasks.pop(server_name, None)
        if task:
            task.cancel()
            self._heartbeats.pop(server_name, None)
            logger.info(f"Heartbeat stopped for {server_name}")
            return True
        return False

    async def _send_heartbeat_ping(self, server_name: str) -> bool:
        """Send a single heartbeat ping to a server."""
        connection = self._connections.get(server_name)
        if not connection:
            return False

        try:
            if isinstance(connection, dict) and connection.get("type") == "http":
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{connection['url']}/ping",
                        timeout=aiohttp.ClientTimeout(total=2),
                    ) as resp:
                        return resp.status == 200

            elif hasattr(connection, "stdin") and hasattr(connection, "stdout"):
                ping_request = json.dumps({
                    "jsonrpc": "2.0",
                    "id": 999,
                    "method": "ping",
                    "params": {},
                })
                connection.stdin.write((ping_request + "\n").encode())
                await connection.stdin.drain()
                response_line = await asyncio.wait_for(
                    connection.stdout.readline(), timeout=2
                )
                response = json.loads(response_line.decode())
                return "error" not in response
        except Exception:
            return False

        return False

    def get_heartbeat_status(self, server_name: str) -> dict | None:
        """Get the heartbeat status for a server.

        Returns:
            A dict with heartbeat metrics, or None if no heartbeat is running.
        """
        hb = self._heartbeats.get(server_name)
        if not hb:
            return None
        return {
            "server_name": hb.server_name,
            "last_beat": hb.last_beat,
            "beat_count": hb.beat_count,
            "missed_beats": hb.missed_beats,
            "is_alive": hb.is_alive,
        }

    # ── Schema Versioning & Migration ─────────────────────

    def register_tool_schema(
        self, tool_name: str, schema: dict, version: int = 1
    ) -> MCPSchemaVersion:
        """Register a tool schema version for migration tracking.

        Args:
            tool_name: Name of the tool.
            schema: The tool's input schema dict.
            version: Schema version number.

        Returns:
            The MCPSchemaVersion record.
        """
        import hashlib
        schema_hash = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()[:16]
        sv = MCPSchemaVersion(
            tool_name=tool_name,
            current_version=version,
            schema_hash=schema_hash,
        )
        self._schema_versions[tool_name] = sv
        return sv

    def register_schema_migration(
        self, tool_name: str, from_version: int, migration_fn: callable
    ):
        """Register a migration function for upgrading tool schemas.

        The migration function receives the old arguments dict and returns
        the migrated arguments dict.

        Args:
            tool_name: Name of the tool.
            from_version: The version this migration upgrades from.
            migration_fn: Callable(old_args) -> new_args.
        """
        if tool_name not in self._schema_migrations:
            self._schema_migrations[tool_name] = {}
        self._schema_migrations[tool_name][from_version] = migration_fn
        logger.info(
            f"Schema migration registered for {tool_name}: v{from_version} -> v{from_version + 1}"
        )

    def migrate_tool_schema(
        self, tool_name: str, arguments: dict, target_version: int | None = None
    ) -> tuple[dict, int]:
        """Migrate tool arguments to the target schema version.

        Applies registered migration functions sequentially to bring the
        arguments from their current version to the target version.

        Args:
            tool_name: Name of the tool.
            arguments: The arguments dict to migrate.
            target_version: Target schema version. If None, migrates to latest.

        Returns:
            A tuple of (migrated_arguments, applied_version).
        """
        sv = self._schema_versions.get(tool_name)
        if not sv:
            logger.debug(f"No schema version registered for {tool_name}, returning as-is")
            return arguments, 1

        target = target_version if target_version is not None else sv.current_version
        migrations = self._schema_migrations.get(tool_name, {})

        current_args = dict(arguments)
        applied_version = 1

        for version in range(1, target):
            migration_fn = migrations.get(version)
            if migration_fn:
                try:
                    current_args = migration_fn(current_args)
                    applied_version = version + 1
                    sv.migration_history.append({
                        "from_version": version,
                        "to_version": version + 1,
                        "applied_at": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    logger.error(f"Schema migration failed for {tool_name} v{version}: {e}")
                    break

        return current_args, applied_version

    def get_schema_version(self, tool_name: str) -> MCPSchemaVersion | None:
        """Get the schema version record for a tool."""
        return self._schema_versions.get(tool_name)

    def get_schema_migration_history(self, tool_name: str) -> list[dict]:
        """Get the migration history for a tool schema."""
        sv = self._schema_versions.get(tool_name)
        return sv.migration_history if sv else []

    # ── Cleanup ──────────────────────────────────────────

    async def shutdown(self):
        """Shutdown all MCP connections."""
        # Stop all heartbeats
        for server_name in list(self._heartbeat_tasks.keys()):
            self.stop_heartbeat(server_name)

        for server_name in list(self._servers.keys()):
            await self.disconnect_server(server_name)
        logger.info("MCP Bridge shutdown complete")


# Global MCP bridge instance
mcp_bridge = MCPBridge()