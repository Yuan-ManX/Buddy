"""Buddy Platform Hub — unified orchestration layer for all platform subsystems

Coordinates the AI-native platform's core subsystems: reactive agent loops,
workflow automation, task orchestration, identity management, gateway routing,
and system-wide monitoring. Acts as the central nervous system connecting all
Buddy platform components.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.platform_hub")


class PlatformSubsystem(str, Enum):
    """Platform subsystems managed by the hub."""
    AGENT_RUNTIME = "agent_runtime"
    WORKFLOW_ENGINE = "workflow_engine"
    TASK_ORCHESTRATOR = "task_orchestrator"
    GATEWAY_HUB = "gateway_hub"
    SCHEDULER = "scheduler"
    REACTIVE_LOOP = "reactive_loop"
    MEMORY_SYNC = "memory_sync"
    MONITORING = "monitoring"
    GUARDRAILS = "guardrails"
    EVOLUTION = "evolution"
    METACOGNITION = "metacognition"
    PROACTIVE = "proactive"


class SubsystemStatus(str, Enum):
    UNINITIALIZED = "uninitialized"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SubsystemInfo:
    """Information about a platform subsystem."""
    name: PlatformSubsystem
    status: SubsystemStatus = SubsystemStatus.UNINITIALIZED
    started_at: str = ""
    error_count: int = 0
    last_error: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class PlatformEvent:
    """An event emitted by the platform hub."""
    id: str
    source: str
    event_type: str
    data: dict = field(default_factory=dict)
    severity: str = "info"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PlatformHub:
    """Central orchestration hub for the Buddy AI-native platform.

    Manages lifecycle of all subsystems, handles cross-subsystem communication,
    provides unified health monitoring, agent orchestration routing, and enables
    graceful startup/shutdown of the entire platform.
    """

    def __init__(self):
        self._subsystems: dict[str, SubsystemInfo] = {}
        self._event_listeners: dict[str, list[Callable[[PlatformEvent], Awaitable[None]]]] = {}
        self._event_history: list[PlatformEvent] = []
        self._max_event_history = 500
        self._is_running = False
        self._startup_time: str = ""
        self._global_config: dict = {
            "auto_restart_subsystems": True,
            "health_check_interval_ms": 30000,
            "max_subsystem_restarts": 3,
        }
        self._ws_manager = None  # Will be set after import
        self._agent_routing_table: dict[str, str] = {}  # task_type -> agent_id
        self._performance_metrics: dict[str, list[float]] = {}  # subsystem -> [latency_ms]
        self._max_metrics_per_subsystem = 100

        # Subsystem dependency graph for ordered startup/shutdown
        self._dependency_graph: dict[str, list[str]] = {
            PlatformSubsystem.GUARDRAILS.value: [],
            PlatformSubsystem.MONITORING.value: [],
            PlatformSubsystem.AGENT_RUNTIME.value: [PlatformSubsystem.GUARDRAILS.value],
            PlatformSubsystem.GATEWAY_HUB.value: [PlatformSubsystem.AGENT_RUNTIME.value],
            PlatformSubsystem.WORKFLOW_ENGINE.value: [PlatformSubsystem.AGENT_RUNTIME.value],
            PlatformSubsystem.TASK_ORCHESTRATOR.value: [PlatformSubsystem.WORKFLOW_ENGINE.value],
            PlatformSubsystem.SCHEDULER.value: [PlatformSubsystem.TASK_ORCHESTRATOR.value],
            PlatformSubsystem.REACTIVE_LOOP.value: [PlatformSubsystem.AGENT_RUNTIME.value],
            PlatformSubsystem.MEMORY_SYNC.value: [PlatformSubsystem.AGENT_RUNTIME.value],
            PlatformSubsystem.EVOLUTION.value: [PlatformSubsystem.AGENT_RUNTIME.value, PlatformSubsystem.METACOGNITION.value],
            PlatformSubsystem.METACOGNITION.value: [PlatformSubsystem.AGENT_RUNTIME.value],
            PlatformSubsystem.PROACTIVE.value: [PlatformSubsystem.AGENT_RUNTIME.value, PlatformSubsystem.MEMORY_SYNC.value],
        }

        # Initialize subsystem tracking
        for subsystem in PlatformSubsystem:
            self._subsystems[subsystem.value] = SubsystemInfo(name=subsystem)

    def set_ws_manager(self, ws_manager):
        """Set WebSocket manager reference for real-time event broadcasting."""
        self._ws_manager = ws_manager

    # ── Lifecycle ────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self):
        """Start the platform hub and initialize all subsystems."""
        if self._is_running:
            return
        self._is_running = True
        self._startup_time = datetime.now(timezone.utc).isoformat()

        logger.info("Platform Hub starting...")

        # Start subsystems in dependency order
        startup_order = [
            PlatformSubsystem.GUARDRAILS,
            PlatformSubsystem.MONITORING,
            PlatformSubsystem.AGENT_RUNTIME,
            PlatformSubsystem.GATEWAY_HUB,
            PlatformSubsystem.WORKFLOW_ENGINE,
            PlatformSubsystem.TASK_ORCHESTRATOR,
            PlatformSubsystem.SCHEDULER,
            PlatformSubsystem.REACTIVE_LOOP,
            PlatformSubsystem.MEMORY_SYNC,
            PlatformSubsystem.METACOGNITION,
            PlatformSubsystem.EVOLUTION,
            PlatformSubsystem.PROACTIVE,
        ]

        for subsystem in startup_order:
            await self._start_subsystem(subsystem)

        logger.info(f"Platform Hub started with {len(self._subsystems)} subsystems")

    async def stop(self):
        """Gracefully stop the platform hub and all subsystems."""
        self._is_running = False

        shutdown_order = reversed([
            PlatformSubsystem.PROACTIVE,
            PlatformSubsystem.EVOLUTION,
            PlatformSubsystem.METACOGNITION,
            PlatformSubsystem.MEMORY_SYNC,
            PlatformSubsystem.REACTIVE_LOOP,
            PlatformSubsystem.SCHEDULER,
            PlatformSubsystem.TASK_ORCHESTRATOR,
            PlatformSubsystem.WORKFLOW_ENGINE,
            PlatformSubsystem.GATEWAY_HUB,
            PlatformSubsystem.AGENT_RUNTIME,
            PlatformSubsystem.MONITORING,
            PlatformSubsystem.GUARDRAILS,
        ])

        for subsystem in shutdown_order:
            await self._stop_subsystem(subsystem)

        logger.info("Platform Hub stopped")

    async def _start_subsystem(self, subsystem: PlatformSubsystem):
        """Start a single subsystem."""
        info = self._subsystems[subsystem.value]
        info.status = SubsystemStatus.STARTING

        try:
            # Subsystem-specific initialization
            await self._initialize_subsystem(subsystem)
            info.status = SubsystemStatus.RUNNING
            info.started_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Subsystem started: {subsystem.value}")
        except Exception as e:
            info.status = SubsystemStatus.ERROR
            info.error_count += 1
            info.last_error = str(e)
            logger.error(f"Subsystem {subsystem.value} failed to start: {e}")

    async def _stop_subsystem(self, subsystem: PlatformSubsystem):
        """Stop a single subsystem."""
        info = self._subsystems[subsystem.value]
        try:
            await self._shutdown_subsystem(subsystem)
            info.status = SubsystemStatus.STOPPED
            logger.info(f"Subsystem stopped: {subsystem.value}")
        except Exception as e:
            logger.warning(f"Error stopping {subsystem.value}: {e}")

    async def _initialize_subsystem(self, subsystem: PlatformSubsystem):
        """Initialize a specific subsystem with actual integration logic."""
        try:
            if subsystem == PlatformSubsystem.REACTIVE_LOOP:
                # Reactive loop is initialized per-agent via the engine
                self._subsystems[subsystem.value].metadata["status"] = "ready"
                self._subsystems[subsystem.value].metadata["active_agents"] = 0
            elif subsystem == PlatformSubsystem.AGENT_RUNTIME:
                self._subsystems[subsystem.value].metadata["status"] = "ready"
                self._subsystems[subsystem.value].metadata["engines_loaded"] = 0
            elif subsystem == PlatformSubsystem.TASK_ORCHESTRATOR:
                self._subsystems[subsystem.value].metadata["status"] = "ready"
                self._subsystems[subsystem.value].metadata["active_tasks"] = 0
            elif subsystem == PlatformSubsystem.MEMORY_SYNC:
                self._subsystems[subsystem.value].metadata["status"] = "ready"
                self._subsystems[subsystem.value].metadata["sync_groups"] = 0
            elif subsystem == PlatformSubsystem.SCHEDULER:
                self._subsystems[subsystem.value].metadata["status"] = "ready"
                self._subsystems[subsystem.value].metadata["scheduled_tasks"] = 0
            elif subsystem == PlatformSubsystem.WORKFLOW_ENGINE:
                self._subsystems[subsystem.value].metadata["status"] = "ready"
                self._subsystems[subsystem.value].metadata["active_workflows"] = 0
        except Exception as e:
            logger.debug(f"Subsystem init note for {subsystem.value}: {e}")

    async def _shutdown_subsystem(self, subsystem: PlatformSubsystem):
        """Shutdown a specific subsystem."""
        pass

    # ── Event System ─────────────────────────────────────

    def emit_event(
        self,
        source: str,
        event_type: str,
        data: dict | None = None,
        severity: str = "info",
    ) -> PlatformEvent:
        """Emit a platform event and notify all listeners."""
        event = PlatformEvent(
            id=f"pevt-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            source=source,
            event_type=event_type,
            data=data or {},
            severity=severity,
        )

        self._event_history.append(event)
        if len(self._event_history) > self._max_event_history:
            self._event_history = self._event_history[-self._max_event_history:]

        # Notify listeners (fire-and-forget)
        for listener_list in self._event_listeners.values():
            for listener in listener_list:
                asyncio.create_task(self._safe_notify(listener, event))

        # Broadcast via WebSocket if available
        if self._ws_manager:
            asyncio.create_task(self._ws_manager.broadcast_platform_event({
                "id": event.id,
                "source": event.source,
                "event_type": event.event_type,
                "severity": event.severity,
                "data": event.data,
                "timestamp": event.timestamp,
            }))

        return event

    async def _safe_notify(self, listener, event: PlatformEvent):
        """Safely notify a listener without blocking."""
        try:
            await listener(event)
        except Exception as e:
            logger.debug(f"Event listener error: {e}")

    def on_event(self, event_type: str, listener: Callable[[PlatformEvent], Awaitable[None]]):
        """Register a listener for a specific event type."""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(listener)

    def get_recent_events(self, limit: int = 50, event_type: str | None = None) -> list[dict]:
        """Get recent platform events."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [
            {
                "id": e.id,
                "source": e.source,
                "event_type": e.event_type,
                "severity": e.severity,
                "data": e.data,
                "timestamp": e.timestamp,
            }
            for e in events[-limit:]
        ]

    # ── Health Monitoring ────────────────────────────────

    def get_health(self) -> dict:
        """Get comprehensive platform health status."""
        subsystem_statuses = {}
        for name, info in self._subsystems.items():
            subsystem_statuses[name] = {
                "status": info.status.value,
                "started_at": info.started_at,
                "error_count": info.error_count,
                "last_error": info.last_error,
            }

        running_count = sum(
            1 for s in self._subsystems.values()
            if s.status == SubsystemStatus.RUNNING
        )
        total_count = len(self._subsystems)
        health_ratio = running_count / max(total_count, 1)

        if health_ratio >= 1.0:
            overall = "healthy"
        elif health_ratio >= 0.7:
            overall = "degraded"
        elif health_ratio >= 0.3:
            overall = "unhealthy"
        else:
            overall = "critical"

        return {
            "overall": overall,
            "is_running": self._is_running,
            "startup_time": self._startup_time,
            "uptime_seconds": (
                (datetime.now(timezone.utc) - datetime.fromisoformat(self._startup_time)).total_seconds()
                if self._startup_time else 0
            ),
            "subsystems": subsystem_statuses,
            "health_ratio": round(health_ratio, 2),
            "subsystem_count": {
                "total": total_count,
                "running": running_count,
                "degraded": sum(1 for s in self._subsystems.values() if s.status == SubsystemStatus.DEGRADED),
                "error": sum(1 for s in self._subsystems.values() if s.status == SubsystemStatus.ERROR),
                "stopped": sum(1 for s in self._subsystems.values() if s.status == SubsystemStatus.STOPPED),
            },
        }

    def get_subsystem_info(self, subsystem_name: str) -> dict | None:
        """Get detailed info for a specific subsystem."""
        info = self._subsystems.get(subsystem_name)
        if not info:
            return None
        return {
            "name": info.name.value,
            "status": info.status.value,
            "started_at": info.started_at,
            "error_count": info.error_count,
            "last_error": info.last_error,
            "metadata": info.metadata,
        }

    def update_subsystem_status(
        self,
        subsystem_name: str,
        status: SubsystemStatus,
        error: str = "",
    ):
        """Update the status of a subsystem."""
        info = self._subsystems.get(subsystem_name)
        if not info:
            return

        old_status = info.status
        info.status = status

        if error:
            info.last_error = error
            info.error_count += 1

        if old_status != status:
            self.emit_event(
                source=f"subsystem:{subsystem_name}",
                event_type="subsystem_status_change",
                data={
                    "subsystem": subsystem_name,
                    "old_status": old_status.value,
                    "new_status": status.value,
                    "error": error,
                },
                severity="warning" if status == SubsystemStatus.ERROR else "info",
            )

    # ── Configuration ────────────────────────────────────

    def get_config(self) -> dict:
        """Get platform hub configuration."""
        return {
            **self._global_config,
            "subsystems": {
                name: {
                    "status": info.status.value,
                    "started_at": info.started_at,
                }
                for name, info in self._subsystems.items()
            },
        }

    def update_config(self, updates: dict):
        """Update platform hub configuration."""
        for key, value in updates.items():
            if key in self._global_config:
                self._global_config[key] = value
        logger.info(f"Platform config updated: {list(updates.keys())}")

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict:
        """Get comprehensive platform statistics."""
        return {
            "is_running": self._is_running,
            "startup_time": self._startup_time,
            "uptime_seconds": (
                (datetime.now(timezone.utc) - datetime.fromisoformat(self._startup_time)).total_seconds()
                if self._startup_time else 0
            ),
            "subsystem_count": len(self._subsystems),
            "events": {
                "total": len(self._event_history),
                "max": self._max_event_history,
            },
            "listener_count": sum(len(v) for v in self._event_listeners.values()),
            "health": self.get_health(),
        }

    # ── Agent Orchestration Routing ────────────────────

    def register_agent_route(self, task_type: str, agent_id: str):
        """Register an agent as the handler for a specific task type."""
        self._agent_routing_table[task_type] = agent_id
        logger.info(f"Agent route registered: {task_type} -> {agent_id}")

    def resolve_agent_route(self, task_type: str) -> str | None:
        """Resolve which agent should handle a given task type."""
        return self._agent_routing_table.get(task_type)

    def get_routing_table(self) -> dict:
        """Get the complete agent routing table."""
        return dict(self._agent_routing_table)

    # ── Performance Metrics ────────────────────────────

    def record_metric(self, subsystem: str, latency_ms: float):
        """Record a performance metric for a subsystem."""
        if subsystem not in self._performance_metrics:
            self._performance_metrics[subsystem] = []
        self._performance_metrics[subsystem].append(latency_ms)
        if len(self._performance_metrics[subsystem]) > self._max_metrics_per_subsystem:
            self._performance_metrics[subsystem] = self._performance_metrics[subsystem][-self._max_metrics_per_subsystem:]

    def get_performance_metrics(self) -> dict:
        """Get aggregated performance metrics for all subsystems."""
        result = {}
        for subsystem, latencies in self._performance_metrics.items():
            if not latencies:
                continue
            sorted_lat = sorted(latencies)
            result[subsystem] = {
                "count": len(latencies),
                "avg_ms": round(sum(latencies) / len(latencies), 2),
                "p50_ms": sorted_lat[len(sorted_lat) // 2],
                "p95_ms": sorted_lat[int(len(sorted_lat) * 0.95)],
                "p99_ms": sorted_lat[int(len(sorted_lat) * 0.99)],
                "min_ms": sorted_lat[0],
                "max_ms": sorted_lat[-1],
            }
        return result

    def get_dependency_graph(self) -> dict:
        """Get the subsystem dependency graph."""
        return dict(self._dependency_graph)


# Global platform hub instance
platform_hub = PlatformHub()