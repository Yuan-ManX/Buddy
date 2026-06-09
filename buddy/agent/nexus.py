"""
Buddy Nexus — Central Intelligence Hub

Orchestrates all Buddy subsystems: routing, agent lifecycle, multi-platform
connectivity, and autonomous execution management. Serves as the single entry
point for all agent coordination, inspired by the concept of a "gateway" that
unifies heterogeneous agent runtimes under one control plane.

The Nexus manages:
  - Agent registry and lifecycle (create, configure, start, stop, destroy)
  - Multi-platform connectivity (CLI, HTTP, messaging platforms)
  - Runtime auto-detection and health monitoring
  - Unified event streaming across all subsystems
  - Resource scheduling and capacity management
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("buddy.nexus")


# ── Platform Types ──

class PlatformType(str, Enum):
    CLI = "cli"
    HTTP = "http"
    WEBSOCKET = "websocket"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    EMAIL = "email"


# ── Runtime Status ──

class RuntimeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class RuntimeInfo:
    """Information about a connected agent runtime."""
    runtime_id: str
    platform: PlatformType
    status: RuntimeStatus = RuntimeStatus.OFFLINE
    agent_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    connected_at: str = ""
    last_heartbeat: str = ""
    request_count: int = 0
    error_count: int = 0

    def dict(self) -> dict:
        return {
            "runtime_id": self.runtime_id,
            "platform": self.platform.value,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "request_count": self.request_count,
            "error_count": self.error_count,
        }


# ── Connection Adapter ──

class PlatformAdapter:
    """Base adapter for platform connectivity.

    Each platform (Telegram, Discord, Slack, CLI, etc.) implements this
    interface to plug into the Nexus. The Nexus handles routing, the adapter
    handles transport.
    """

    def __init__(self, platform: PlatformType):
        self.platform = platform
        self._handlers: dict[str, Callable] = {}

    async def connect(self) -> RuntimeInfo:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError

    async def send(self, target: str, message: dict) -> bool:
        raise NotImplementedError

    async def health_check(self) -> RuntimeStatus:
        raise NotImplementedError

    def on_message(self, event_type: str, handler: Callable):
        self._handlers[event_type] = handler


# ── Nexus Core ──

@dataclass
class NexusConfig:
    """Configuration for the Buddy Nexus."""
    max_runtimes: int = 50
    heartbeat_interval: int = 30  # seconds
    health_check_interval: int = 60  # seconds
    request_timeout: int = 300  # seconds
    auto_reconnect: bool = True
    auto_reconnect_max_attempts: int = 5
    platform_adapters: dict[PlatformType, PlatformAdapter] = field(default_factory=dict)


class BuddyNexus:
    """Central coordination hub for all Buddy agent subsystems.

    The Nexus is the brain stem of Buddy — it connects every runtime,
    routes every request, monitors every heartbeat, and ensures the
    entire system operates as one coherent intelligence.
    """

    def __init__(self, config: NexusConfig | None = None):
        self._config = config or NexusConfig()
        self._runtimes: dict[str, RuntimeInfo] = {}
        self._adapters: dict[PlatformType, PlatformAdapter] = {}
        self._event_listeners: dict[str, list[Callable]] = {}
        self._request_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._monitor_task: asyncio.Task | None = None

    # ── Runtime Management ──

    def register_runtime(self, info: RuntimeInfo) -> str:
        """Register a new runtime with the Nexus."""
        if len(self._runtimes) >= self._config.max_runtimes:
            raise RuntimeError("Maximum runtime limit reached")

        now = datetime.now(timezone.utc).isoformat()
        info.connected_at = now
        info.last_heartbeat = now
        info.status = RuntimeStatus.STARTING
        self._runtimes[info.runtime_id] = info
        logger.info(f"Nexus registered runtime: {info.runtime_id} ({info.platform.value})")
        self._emit("runtime.registered", info.dict())
        return info.runtime_id

    def unregister_runtime(self, runtime_id: str) -> bool:
        """Remove a runtime from the Nexus."""
        if runtime_id not in self._runtimes:
            return False
        info = self._runtimes.pop(runtime_id)
        logger.info(f"Nexus unregistered runtime: {runtime_id}")
        self._emit("runtime.unregistered", info.dict())
        return True

    def get_runtime(self, runtime_id: str) -> RuntimeInfo | None:
        return self._runtimes.get(runtime_id)

    def list_runtimes(
        self,
        platform: PlatformType | None = None,
        status: RuntimeStatus | None = None,
    ) -> list[RuntimeInfo]:
        results = list(self._runtimes.values())
        if platform:
            results = [r for r in results if r.platform == platform]
        if status:
            results = [r for r in results if r.status == status]
        return results

    def update_runtime_status(self, runtime_id: str, status: RuntimeStatus):
        if runtime_id in self._runtimes:
            self._runtimes[runtime_id].status = status
            self._runtimes[runtime_id].last_heartbeat = datetime.now(timezone.utc).isoformat()
            self._emit("runtime.status_changed", {
                "runtime_id": runtime_id,
                "status": status.value,
            })

    def heartbeat(self, runtime_id: str) -> bool:
        """Record a heartbeat from a runtime."""
        if runtime_id not in self._runtimes:
            return False
        self._runtimes[runtime_id].last_heartbeat = datetime.now(timezone.utc).isoformat()
        if self._runtimes[runtime_id].status == RuntimeStatus.OFFLINE:
            self._runtimes[runtime_id].status = RuntimeStatus.ONLINE
        return True

    # ── Platform Adapters ──

    def register_adapter(self, adapter: PlatformAdapter):
        """Plug in a platform adapter."""
        self._adapters[adapter.platform] = adapter
        logger.info(f"Nexus registered adapter: {adapter.platform.value}")

    async def connect_platform(self, platform: PlatformType) -> RuntimeInfo:
        """Connect a platform adapter through the Nexus."""
        adapter = self._adapters.get(platform)
        if not adapter:
            raise ValueError(f"No adapter for platform: {platform.value}")
        runtime_info = await adapter.connect()
        self.register_runtime(runtime_info)
        return runtime_info

    async def disconnect_platform(self, platform: PlatformType):
        """Disconnect a platform adapter."""
        adapter = self._adapters.get(platform)
        if adapter:
            await adapter.disconnect()

    # ── Request Routing ──

    async def route_request(
        self,
        runtime_id: str,
        payload: dict,
        priority: int = 0,
    ) -> dict:
        """Route a request through the Nexus to the appropriate subsystem."""
        if runtime_id not in self._runtimes:
            raise ValueError(f"Unknown runtime: {runtime_id}")

        runtime = self._runtimes[runtime_id]
        runtime.request_count += 1

        self._emit("request.received", {
            "runtime_id": runtime_id,
            "platform": runtime.platform.value,
            "priority": priority,
        })

        # In a production system, this would dispatch to the appropriate
        # agent engine, skill system, or tool executor based on the payload.
        return {
            "status": "routed",
            "runtime_id": runtime_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Event System ──

    def on(self, event_type: str, listener: Callable):
        """Subscribe to Nexus events."""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(listener)

    def _emit(self, event_type: str, data: dict):
        """Emit an event to all listeners."""
        listeners = self._event_listeners.get(event_type, []) + \
                    self._event_listeners.get("*", [])
        for listener in listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.error(f"Event listener error for {event_type}: {e}")

    # ── Health Monitoring ──

    async def start_monitor(self):
        """Start the health monitoring loop."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Nexus health monitor started")

    async def stop_monitor(self):
        """Stop the health monitoring loop."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Nexus health monitor stopped")

    async def _monitor_loop(self):
        """Continuously monitor runtime health."""
        while self._running:
            await asyncio.sleep(self._config.heartbeat_interval)
            now = datetime.now(timezone.utc)

            for runtime_id, info in list(self._runtimes.items()):
                if info.last_heartbeat:
                    try:
                        last = datetime.fromisoformat(info.last_heartbeat)
                        elapsed = (now - last).total_seconds()
                        if elapsed > self._config.health_check_interval:
                            info.status = RuntimeStatus.DEGRADED
                            self._emit("runtime.degraded", {
                                "runtime_id": runtime_id,
                                "seconds_since_heartbeat": elapsed,
                            })
                            logger.warning(
                                f"Runtime {runtime_id} degraded: {elapsed:.0f}s since last heartbeat"
                            )
                    except (ValueError, TypeError):
                        pass

    # ── Summary ──

    def get_summary(self) -> dict:
        """Get a summary of the Nexus state."""
        platform_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        for info in self._runtimes.values():
            p = info.platform.value
            s = info.status.value
            platform_counts[p] = platform_counts.get(p, 0) + 1
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            "total_runtimes": len(self._runtimes),
            "connected_platforms": len(self._adapters),
            "platform_distribution": platform_counts,
            "status_distribution": status_counts,
            "monitor_running": self._running,
            "total_requests": sum(r.request_count for r in self._runtimes.values()),
            "total_errors": sum(r.error_count for r in self._runtimes.values()),
        }