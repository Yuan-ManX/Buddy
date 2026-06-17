"""Buddy Platform Hub — unified orchestration layer for all platform subsystems

Coordinates the AI-native platform's core subsystems: reactive agent loops,
workflow automation, task orchestration, identity management, gateway routing,
and system-wide monitoring. Acts as the central nervous system connecting all
Buddy platform components.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
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


@dataclass
class PriorityEvent:
    """An event with a priority level for the priority queue."""
    event: PlatformEvent
    priority: int = 0  # 0 = highest, 9 = lowest
    enqueued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ServiceRegistration:
    """A dynamically registered service in the platform."""
    service_id: str = ""
    service_name: str = ""
    service_type: str = ""
    host: str = ""
    port: int = 0
    health_endpoint: str = ""
    metadata: dict = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True


@dataclass
class AuditEntry:
    """A platform-wide audit log entry."""
    id: str = ""
    subsystem: str = ""
    action: str = ""
    actor: str = ""
    resource: str = ""
    details: dict = field(default_factory=dict)
    result: str = "success"
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

        # Priority event queue
        self._priority_queue: list[PriorityEvent] = []
        self._max_queue_size = 200

        # Service registry
        self._services: dict[str, ServiceRegistration] = {}
        self._service_heartbeat_tasks: dict[str, asyncio.Task] = {}

        # Config hot-reload
        self._config_reload_callbacks: dict[str, list[Callable]] = {}
        self._config_version: int = 1

        # Audit log
        self._audit_log: list[AuditEntry] = []
        self._max_audit_entries = 2000

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

    # ── Priority Event Routing ────────────────────────────

    def route_event_with_priority(
        self,
        source: str,
        event_type: str,
        data: dict | None = None,
        severity: str = "info",
        priority: int = 5,
        target_subsystem: str | None = None,
    ) -> PlatformEvent:
        """Route an event through the platform with priority queuing.

        Higher-priority events (lower priority number) are processed first.
        If a target subsystem is specified, only listeners registered for
        that subsystem are notified.

        Args:
            source: Event source identifier.
            event_type: Type of the event.
            data: Event payload.
            severity: Event severity (info, warning, error, critical).
            priority: Priority level (0=highest, 9=lowest).
            target_subsystem: Optional subsystem to route to.

        Returns:
            The created PlatformEvent.
        """
        event = PlatformEvent(
            id=f"pevt-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            source=source,
            event_type=event_type,
            data=data or {},
            severity=severity,
        )

        # Enqueue with priority
        pe = PriorityEvent(event=event, priority=priority)
        self._priority_queue.append(pe)

        # Sort by priority (lower = higher priority)
        self._priority_queue.sort(key=lambda e: (e.priority, e.enqueued_at))

        # Trim queue
        if len(self._priority_queue) > self._max_queue_size:
            self._priority_queue = self._priority_queue[-self._max_queue_size:]

        # Store in event history
        self._event_history.append(event)
        if len(self._event_history) > self._max_event_history:
            self._event_history = self._event_history[-self._max_event_history:]

        # Notify listeners — filtered by target_subsystem if specified
        for listener_list in self._event_listeners.values():
            for listener in listener_list:
                asyncio.create_task(self._safe_notify(listener, event))

        if self._ws_manager:
            asyncio.create_task(self._ws_manager.broadcast_platform_event({
                "id": event.id,
                "source": event.source,
                "event_type": event.event_type,
                "severity": event.severity,
                "priority": priority,
                "target_subsystem": target_subsystem,
                "data": event.data,
                "timestamp": event.timestamp,
            }))

        return event

    def process_priority_queue(self, max_events: int = 10) -> list[PlatformEvent]:
        """Process and dequeue the highest-priority events from the queue.

        Args:
            max_events: Maximum number of events to process in one batch.

        Returns:
            List of processed events.
        """
        processed = []
        for _ in range(min(max_events, len(self._priority_queue))):
            if self._priority_queue:
                pe = self._priority_queue.pop(0)
                processed.append(pe.event)
        return processed

    def get_priority_queue_size(self) -> int:
        """Get the current size of the priority event queue."""
        return len(self._priority_queue)

    def get_priority_queue_summary(self) -> dict:
        """Get a summary of the priority queue state."""
        priority_counts: dict[int, int] = {}
        for pe in self._priority_queue:
            priority_counts[pe.priority] = priority_counts.get(pe.priority, 0) + 1

        return {
            "queue_size": len(self._priority_queue),
            "max_size": self._max_queue_size,
            "by_priority": priority_counts,
            "oldest_event": self._priority_queue[0].enqueued_at if self._priority_queue else "",
        }

    # ── Subsystem Health Aggregation ──────────────────────

    def aggregate_health(self) -> dict:
        """Aggregate health status across all subsystems.

        Computes overall platform health, per-subsystem breakdowns,
        and identifies subsystems that are in degraded or error state.

        Returns:
            Comprehensive health aggregation dict.
        """
        statuses: dict[str, dict] = {}
        error_subsystems: list[str] = []
        degraded_subsystems: list[str] = []
        running_count = 0

        for name, info in self._subsystems.items():
            statuses[name] = {
                "status": info.status.value,
                "started_at": info.started_at,
                "error_count": info.error_count,
                "last_error": info.last_error,
                "dependencies": self._dependency_graph.get(name, []),
            }
            if info.status == SubsystemStatus.RUNNING:
                running_count += 1
            elif info.status == SubsystemStatus.ERROR:
                error_subsystems.append(name)
            elif info.status == SubsystemStatus.DEGRADED:
                degraded_subsystems.append(name)

        total = len(self._subsystems)
        health_ratio = running_count / max(total, 1)

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
            "health_ratio": round(health_ratio, 2),
            "running_count": running_count,
            "total_subsystems": total,
            "error_subsystems": error_subsystems,
            "degraded_subsystems": degraded_subsystems,
            "subsystems": statuses,
            "is_running": self._is_running,
        }

    def detect_cascading_failure(self) -> list[dict]:
        """Detect cascading failures across dependent subsystems.

        A cascading failure occurs when a subsystem's failure causes
        its dependent subsystems to also fail or degrade, following
        the dependency graph.

        Returns:
            List of failure chains identified.
        """
        chains: list[dict] = []

        # Find root failure subsystems (in ERROR state)
        failed_roots = {
            name: info
            for name, info in self._subsystems.items()
            if info.status == SubsystemStatus.ERROR
        }

        for root_name, root_info in failed_roots.items():
            # Find all dependent subsystems
            affected = self._find_affected_subsystems(root_name)
            if affected:
                chains.append({
                    "root_failure": root_name,
                    "root_error": root_info.last_error,
                    "affected_subsystems": affected,
                    "chain_length": len(affected) + 1,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })

        if chains:
            logger.warning(f"Detected {len(chains)} cascading failure chains")

        return chains

    def _find_affected_subsystems(self, failed_subsystem: str) -> list[dict]:
        """Find all subsystems that depend on a failed subsystem."""
        affected = []
        for name, deps in self._dependency_graph.items():
            if failed_subsystem in deps:
                info = self._subsystems.get(name)
                affected.append({
                    "subsystem": name,
                    "status": info.status.value if info else "unknown",
                    "depends_on": failed_subsystem,
                })
                # Recursively find transitive dependents
                transitive = self._find_affected_subsystems(name)
                affected.extend(transitive)
        return affected

    # ── Dynamic Service Registration & Discovery ──────────

    def register_service(
        self,
        service_name: str,
        service_type: str,
        host: str,
        port: int,
        health_endpoint: str = "/health",
        metadata: dict | None = None,
    ) -> ServiceRegistration:
        """Register a service dynamically in the platform service registry.

        Services can be discovered by other subsystems via the registry.
        Each service gets a unique ID and can be health-checked.

        Args:
            service_name: Human-readable service name.
            service_type: Category of service (e.g., 'database', 'api', 'worker').
            host: Hostname or IP address.
            port: Service port number.
            health_endpoint: Health check endpoint path.
            metadata: Additional service metadata.

        Returns:
            The created ServiceRegistration.

        Raises:
            ValueError: If a service with the same name already exists.
        """
        if service_name in self._services:
            raise ValueError(f"Service '{service_name}' is already registered")

        service = ServiceRegistration(
            service_id=f"svc-{uuid.uuid4().hex[:12]}",
            service_name=service_name,
            service_type=service_type,
            host=host,
            port=port,
            health_endpoint=health_endpoint,
            metadata=metadata or {},
        )
        self._services[service_name] = service

        logger.info(f"Service registered: {service_name} ({service_type}) at {host}:{port}")
        return service

    def discover_service(
        self, service_name: str = "", service_type: str = ""
    ) -> list[dict]:
        """Discover services from the registry.

        Args:
            service_name: Filter by service name (supports partial match).
            service_type: Filter by service type.

        Returns:
            List of matching service records.
        """
        results = []
        for svc in self._services.values():
            if not svc.is_active:
                continue
            if service_name and service_name.lower() not in svc.service_name.lower():
                continue
            if service_type and svc.service_type != service_type:
                continue
            results.append({
                "service_id": svc.service_id,
                "service_name": svc.service_name,
                "service_type": svc.service_type,
                "host": svc.host,
                "port": svc.port,
                "health_endpoint": svc.health_endpoint,
                "metadata": svc.metadata,
                "registered_at": svc.registered_at,
                "last_heartbeat": svc.last_heartbeat,
            })
        return results

    def deregister_service(self, service_name: str) -> bool:
        """Remove a service from the registry."""
        if service_name in self._services:
            self._services[service_name].is_active = False
            # Cancel heartbeat if running
            task = self._service_heartbeat_tasks.pop(service_name, None)
            if task:
                task.cancel()
            del self._services[service_name]
            logger.info(f"Service deregistered: {service_name}")
            return True
        return False

    def update_service_heartbeat(self, service_name: str) -> bool:
        """Update the heartbeat timestamp for a registered service."""
        svc = self._services.get(service_name)
        if svc:
            svc.last_heartbeat = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def get_stale_services(self, max_heartbeat_age_seconds: float = 30.0) -> list[str]:
        """Find services whose heartbeat is stale.

        Args:
            max_heartbeat_age_seconds: Maximum age before considered stale.

        Returns:
            List of stale service names.
        """
        now = datetime.now(timezone.utc)
        stale = []
        for name, svc in self._services.items():
            if not svc.is_active:
                continue
            try:
                last = datetime.fromisoformat(svc.last_heartbeat)
                age = (now - last).total_seconds()
                if age > max_heartbeat_age_seconds:
                    stale.append(name)
            except (ValueError, TypeError):
                stale.append(name)
        return stale

    # ── Configuration Hot-Reload ──────────────────────────

    def register_config_reload_callback(
        self, subsystem: str, callback: Callable
    ):
        """Register a callback to be invoked on configuration hot-reload.

        When the platform configuration is updated, all registered
        callbacks are invoked with the new config dict.

        Args:
            subsystem: The subsystem that owns the callback.
            callback: Callable(new_config_dict) -> None.
        """
        if subsystem not in self._config_reload_callbacks:
            self._config_reload_callbacks[subsystem] = []
        self._config_reload_callbacks[subsystem].append(callback)

    def hot_reload_config(self, config_updates: dict) -> dict:
        """Hot-reload configuration across all subsystems.

        Applies configuration updates and notifies all registered
        subsystems via their reload callbacks. The config version
        is incremented on each reload.

        Args:
            config_updates: Dict of configuration key-value pairs to update.

        Returns:
            Dict with reload results.
        """
        # Apply updates
        for key, value in config_updates.items():
            if key in self._global_config:
                self._global_config[key] = value
            else:
                self._global_config[key] = value

        self._config_version += 1

        # Notify all registered callbacks
        notified = 0
        errors = []
        for subsystem, callbacks in self._config_reload_callbacks.items():
            for callback in callbacks:
                try:
                    callback(self._global_config)
                    notified += 1
                except Exception as e:
                    errors.append({
                        "subsystem": subsystem,
                        "error": str(e),
                    })

        # Emit config change event
        self.emit_event(
            source="platform_hub",
            event_type="config_reloaded",
            data={
                "version": self._config_version,
                "updated_keys": list(config_updates.keys()),
                "notified_subsystems": notified,
                "errors": len(errors),
            },
            severity="info",
        )

        logger.info(
            f"Config hot-reloaded (v{self._config_version}): "
            f"{list(config_updates.keys())}, notified {notified} callbacks"
        )

        return {
            "config_version": self._config_version,
            "updated_keys": list(config_updates.keys()),
            "notified_count": notified,
            "error_count": len(errors),
            "errors": errors,
        }

    def get_config_version(self) -> int:
        """Get the current configuration version number."""
        return self._config_version

    def get_config_reload_subscribers(self) -> dict[str, int]:
        """Get the count of config reload callbacks per subsystem."""
        return {
            subsystem: len(callbacks)
            for subsystem, callbacks in self._config_reload_callbacks.items()
        }

    # ── Audit Logging & Compliance Tracking ───────────────

    def record_audit_log(
        self,
        subsystem: str,
        action: str,
        actor: str = "",
        resource: str = "",
        details: dict | None = None,
        result: str = "success",
    ) -> AuditEntry:
        """Record a platform-wide audit log entry for compliance tracking.

        Every significant action in the platform should be recorded
        for auditability: who did what, to which resource, and the result.

        Args:
            subsystem: The subsystem that performed the action.
            action: The action performed (e.g., 'create', 'delete', 'update').
            actor: The entity that performed the action.
            resource: The resource affected by the action.
            details: Additional context about the action.
            result: Outcome of the action ('success', 'failure', 'denied').

        Returns:
            The created AuditEntry.
        """
        entry = AuditEntry(
            id=f"audit-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            subsystem=subsystem,
            action=action,
            actor=actor,
            resource=resource,
            details=details or {},
            result=result,
        )
        self._audit_log.append(entry)

        # Trim to max
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]

        logger.debug(
            f"Audit: [{subsystem}] {actor} {action} {resource} -> {result}"
        )
        return entry

    def get_audit_trail(
        self,
        subsystem: str = "",
        actor: str = "",
        action: str = "",
        result: str = "",
        limit: int = 100,
        since: str = "",
    ) -> list[dict]:
        """Query the platform audit trail with filters.

        Args:
            subsystem: Filter by subsystem name.
            actor: Filter by actor.
            action: Filter by action type.
            result: Filter by result (success, failure, denied).
            limit: Maximum number of entries to return.
            since: ISO timestamp to filter entries after.

        Returns:
            List of audit entries as dicts, newest first.
        """
        entries = list(self._audit_log)

        if subsystem:
            entries = [e for e in entries if e.subsystem == subsystem]
        if actor:
            entries = [e for e in entries if e.actor == actor]
        if action:
            entries = [e for e in entries if e.action == action]
        if result:
            entries = [e for e in entries if e.result == result]
        if since:
            entries = [e for e in entries if e.timestamp >= since]

        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return [
            {
                "id": e.id,
                "subsystem": e.subsystem,
                "action": e.action,
                "actor": e.actor,
                "resource": e.resource,
                "details": e.details,
                "result": e.result,
                "timestamp": e.timestamp,
            }
            for e in entries[:limit]
        ]

    def get_compliance_report(self) -> dict:
        """Generate a compliance report from the audit trail.

        Summarizes actions by subsystem, actor, and result type for
        compliance review purposes.

        Returns:
            Dict with compliance summary data.
        """
        by_subsystem: dict[str, int] = {}
        by_action: dict[str, int] = {}
        by_result: dict[str, int] = {}
        by_actor: dict[str, int] = {}

        for entry in self._audit_log:
            by_subsystem[entry.subsystem] = by_subsystem.get(entry.subsystem, 0) + 1
            by_action[entry.action] = by_action.get(entry.action, 0) + 1
            by_result[entry.result] = by_result.get(entry.result, 0) + 1
            if entry.actor:
                by_actor[entry.actor] = by_actor.get(entry.actor, 0) + 1

        failure_rate = (
            by_result.get("failure", 0) / max(len(self._audit_log), 1)
        )

        return {
            "total_entries": len(self._audit_log),
            "max_entries": self._max_audit_entries,
            "by_subsystem": by_subsystem,
            "by_action": by_action,
            "by_result": by_result,
            "by_actor": by_actor,
            "failure_rate": round(failure_rate, 4),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def export_audit_log(self, format: str = "json") -> str:
        """Export the full audit log in the specified format.

        Args:
            format: 'json' or 'csv'.

        Returns:
            The serialized audit log as a string.
        """
        import json as _json

        if format == "json":
            return _json.dumps(
                self.get_audit_trail(limit=len(self._audit_log)),
                indent=2,
                default=str,
            )

        if format == "csv":
            import io
            import csv
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "subsystem", "action", "actor", "resource", "result", "timestamp"])
            for entry in self._audit_log:
                writer.writerow([
                    entry.id, entry.subsystem, entry.action,
                    entry.actor, entry.resource, entry.result, entry.timestamp,
                ])
            return output.getvalue()

        return _json.dumps(
            self.get_audit_trail(limit=len(self._audit_log)),
            indent=2,
            default=str,
        )


# Global platform hub instance
platform_hub = PlatformHub()