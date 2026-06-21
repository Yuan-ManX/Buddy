"""Buddy Platform Core — runtime ecosystem and system-wide coordination

The Platform Core manages the entire Buddy runtime ecosystem, providing:
- Runtime lifecycle management: start, stop, monitor, restart agent instances
- Sandbox environment provisioning: isolated execution environments
- System-wide health monitoring and alerting
- Cross-agent context sharing and synchronization
- Platform-level identity and authentication
- Resource allocation and quota management
- Agent fleet orchestration: synchronized deployment, scaling, and rollback
- Cross-agent knowledge synchronization with conflict resolution
- Platform event bus with filtering and subscriptions
- Auto-scaling engine based on load metrics
- Per-agent resource quota enforcement with soft/hard limits
"""
from __future__ import annotations
import json
import logging
import uuid
import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("buddy.platform_core")

# ── Enums ─────────────────────────────────────────────────

class RuntimeState(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    RESTARTING = "restarting"


class SandboxType(str, Enum):
    PYTHON = "python"
    NODE = "node"
    SHELL = "shell"
    DOCKER = "docker"
    CUSTOM = "custom"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ResourceType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    TOKENS = "tokens"
    API_CALLS = "api_calls"
    CONCURRENT_SESSIONS = "concurrent_sessions"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class FleetState(str, Enum):
    """Operational state of an agent fleet."""
    DRAFT = "draft"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    SCALING = "scaling"
    ROLLING_BACK = "rolling_back"
    DEGRADED = "degraded"
    INACTIVE = "inactive"


class DeploymentStatus(str, Enum):
    """Status of a fleet deployment operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ConflictResolutionStrategy(str, Enum):
    """Strategy for resolving knowledge conflicts between agents."""
    LAST_WRITE_WINS = "last_write_wins"
    SOURCE_PRIORITY = "source_priority"
    MERGE = "merge"
    MANUAL = "manual"
    KEEP_BOTH = "keep_both"


class EventCategory(str, Enum):
    """Categories for platform-level events."""
    LIFECYCLE = "lifecycle"
    HEALTH = "health"
    DEPLOYMENT = "deployment"
    SCALING = "scaling"
    QUOTA = "quota"
    KNOWLEDGE = "knowledge"
    SYSTEM = "system"
    CUSTOM = "custom"


class QuotaLimitType(str, Enum):
    """Type of resource quota limit."""
    SOFT = "soft"
    HARD = "hard"


# ── Data Classes ──────────────────────────────────────────

@dataclass
class PlatformConfig:
    """Global platform configuration."""
    platform_id: str = field(default_factory=lambda: f"platform-{uuid.uuid4().hex[:8]}")
    max_agents: int = 100
    max_concurrent_sessions: int = 50
    default_sandbox_timeout: int = 30
    health_check_interval: int = 60
    resource_monitor_interval: int = 30
    enable_auto_scaling: bool = False
    enable_telemetry: bool = True
    log_level: str = "INFO"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeInstance:
    """A single agent runtime instance managed by the platform."""
    instance_id: str = field(default_factory=lambda: f"inst-{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    agent_name: str = ""
    state: RuntimeState = RuntimeState.INITIALIZING
    started_at: str = ""
    last_heartbeat: str = ""
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_sessions: int = 0
    total_requests: int = 0
    error_count: int = 0
    sandbox_instances: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "state": self.state.value,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "cpu_usage_percent": round(self.cpu_usage_percent, 2),
            "active_sessions": self.active_sessions,
            "total_requests": self.total_requests,
            "error_count": self.error_count,
        }


@dataclass
class SandboxEnvironment:
    """An isolated sandbox execution environment."""
    sandbox_id: str = field(default_factory=lambda: f"sand-{uuid.uuid4().hex[:8]}")
    sandbox_type: SandboxType = SandboxType.PYTHON
    agent_id: str = ""
    state: RuntimeState = RuntimeState.INITIALIZING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    workspace_path: str = ""
    environment_vars: dict[str, str] = field(default_factory=dict)
    installed_packages: list[str] = field(default_factory=list)
    resource_limits: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "sandbox_type": self.sandbox_type.value,
            "agent_id": self.agent_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "workspace_path": self.workspace_path,
        }


@dataclass
class HealthReport:
    """System-wide health report."""
    report_id: str = field(default_factory=lambda: f"hr-{uuid.uuid4().hex[:8]}")
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    component_statuses: dict[str, HealthStatus] = field(default_factory=dict)
    active_alerts: list[dict[str, Any]] = field(default_factory=list)
    resource_utilization: dict[str, float] = field(default_factory=dict)
    agent_count: int = 0
    healthy_agents: int = 0
    degraded_agents: int = 0
    unhealthy_agents: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "overall_status": self.overall_status.value,
            "component_statuses": {k: v.value for k, v in self.component_statuses.items()},
            "active_alerts": self.active_alerts,
            "resource_utilization": self.resource_utilization,
            "agent_count": self.agent_count,
            "healthy_agents": self.healthy_agents,
            "degraded_agents": self.degraded_agents,
            "unhealthy_agents": self.unhealthy_agents,
            "timestamp": self.timestamp,
        }


@dataclass
class PlatformAlert:
    """A system alert generated by the platform."""
    alert_id: str = field(default_factory=lambda: f"alert-{uuid.uuid4().hex[:8]}")
    severity: AlertSeverity = AlertSeverity.INFO
    component: str = ""
    message: str = ""
    details: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged: bool = False
    resolved_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "component": self.component,
            "message": self.message,
            "details": self.details[:200],
            "created_at": self.created_at,
            "acknowledged": self.acknowledged,
            "resolved_at": self.resolved_at,
        }


@dataclass
class ContextSyncEvent:
    """Cross-agent context synchronization event."""
    event_id: str = field(default_factory=lambda: f"ctxsync-{uuid.uuid4().hex[:8]}")
    source_agent_id: str = ""
    target_agent_ids: list[str] = field(default_factory=list)
    context_type: str = "memory"
    content: dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Fleet Data Classes ────────────────────────────────────

@dataclass
class FleetConfig:
    """Configuration for an agent fleet deployment."""
    fleet_id: str = field(default_factory=lambda: f"fleet-{uuid.uuid4().hex[:8]}")
    fleet_name: str = ""
    min_agents: int = 1
    max_agents: int = 10
    target_agents: int = 1
    deployment_strategy: str = "rolling"  # "rolling", "blue_green", "canary"
    health_check_grace_period: int = 30
    rollback_on_failure: bool = True
    cooldown_period: int = 60  # seconds between scaling operations
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FleetDeployment:
    """Records a deployment operation within a fleet."""
    deployment_id: str = field(default_factory=lambda: f"deploy-{uuid.uuid4().hex[:8]}")
    fleet_id: str = ""
    status: DeploymentStatus = DeploymentStatus.PENDING
    agent_ids: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str | None = None
    version: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "fleet_id": self.fleet_id,
            "status": self.status.value,
            "agent_ids": self.agent_ids,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "version": self.version,
            "error_message": self.error_message[:200],
        }


@dataclass
class Fleet:
    """A managed group of agents operating as a coordinated fleet."""
    fleet_id: str = field(default_factory=lambda: f"fleet-{uuid.uuid4().hex[:8]}")
    fleet_name: str = ""
    agent_ids: list[str] = field(default_factory=list)
    state: FleetState = FleetState.DRAFT
    config: FleetConfig = field(default_factory=FleetConfig)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    deployment_history: list[FleetDeployment] = field(default_factory=list)
    last_scale_time: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fleet_id": self.fleet_id,
            "fleet_name": self.fleet_name,
            "agent_ids": self.agent_ids,
            "state": self.state.value,
            "config": {
                "min_agents": self.config.min_agents,
                "max_agents": self.config.max_agents,
                "target_agents": self.config.target_agents,
                "deployment_strategy": self.config.deployment_strategy,
            },
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "agent_count": len(self.agent_ids),
            "last_deployment": self.deployment_history[-1].to_dict() if self.deployment_history else None,
        }


# ── Knowledge Sync Data Classes ───────────────────────────

@dataclass
class KnowledgeEntry:
    """A single knowledge / memory entry shared across agents."""
    entry_id: str = field(default_factory=lambda: f"kentry-{uuid.uuid4().hex[:8]}")
    source_agent_id: str = ""
    key: str = ""
    value: Any = None
    tags: list[str] = field(default_factory=list)
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl_seconds: float | None = None  # None means no expiry
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "source_agent_id": self.source_agent_id,
            "key": self.key,
            "value": self.value,
            "tags": self.tags,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_expired(self) -> bool:
        """Check if the knowledge entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        updated = datetime.fromisoformat(self.updated_at)
        elapsed = (datetime.now(timezone.utc) - updated).total_seconds()
        return elapsed > self.ttl_seconds


@dataclass
class KnowledgeSyncResult:
    """Result of a cross-agent knowledge synchronization operation."""
    sync_id: str = field(default_factory=lambda: f"ksync-{uuid.uuid4().hex[:8]}")
    fleet_id: str = ""
    entries_synced: int = 0
    entries_conflicted: int = 0
    entries_resolved: int = 0
    entries_skipped: int = 0
    strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "fleet_id": self.fleet_id,
            "entries_synced": self.entries_synced,
            "entries_conflicted": self.entries_conflicted,
            "entries_resolved": self.entries_resolved,
            "entries_skipped": self.entries_skipped,
            "strategy": self.strategy.value,
            "conflicts": self.conflicts[:50],
            "timestamp": self.timestamp,
        }


# ── Resource Quota Data Classes ───────────────────────────

@dataclass
class ResourceQuota:
    """Per-agent resource quota with soft and hard limits."""
    agent_id: str = ""
    limits: dict[ResourceType, dict[str, float]] = field(default_factory=dict)
    # limits format: {ResourceType.CPU: {"soft": 2.0, "hard": 4.0}, ...}
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "limits": {
                rt.value: limits for rt, limits in self.limits.items()
            },
            "enabled": self.enabled,
        }

    def get_limit(self, resource_type: ResourceType, limit_type: QuotaLimitType) -> float | None:
        """Get a specific limit for a resource type."""
        resource_limits = self.limits.get(resource_type, {})
        return resource_limits.get(limit_type.value)


@dataclass
class ResourceQuotaStatus:
    """Current resource usage status against defined quotas."""
    agent_id: str = ""
    usage: dict[ResourceType, float] = field(default_factory=dict)
    # usage format: {ResourceType.CPU: 1.5, ResourceType.MEMORY: 512.0, ...}
    quota: ResourceQuota | None = None
    violations: list[str] = field(default_factory=list)
    within_soft_limits: bool = True
    within_hard_limits: bool = True
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "usage": {rt.value: val for rt, val in self.usage.items()},
            "violations": self.violations,
            "within_soft_limits": self.within_soft_limits,
            "within_hard_limits": self.within_hard_limits,
            "checked_at": self.checked_at,
        }


# ── Event Bus Data Classes ────────────────────────────────

@dataclass
class PlatformEvent:
    """A platform-level event broadcast to all subscribing agents."""
    event_id: str = field(default_factory=lambda: f"pevent-{uuid.uuid4().hex[:8]}")
    category: EventCategory = EventCategory.SYSTEM
    event_type: str = ""
    source: str = "platform"
    data: dict[str, Any] = field(default_factory=dict)
    target_agent_ids: list[str] = field(default_factory=list)  # empty = all agents
    target_fleet_ids: list[str] = field(default_factory=list)  # empty = all fleets
    priority: int = 5  # 1=highest, 10=lowest
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl_seconds: float | None = None  # None = no expiry
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "category": self.category.value,
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "priority": self.priority,
            "timestamp": self.timestamp,
        }

    def matches_filter(
        self,
        categories: list[EventCategory] | None = None,
        event_types: list[str] | None = None,
        agent_id: str | None = None,
        fleet_id: str | None = None,
    ) -> bool:
        """Check if this event matches a given subscription filter."""
        if categories and self.category not in categories:
            return False
        if event_types and self.event_type not in event_types:
            return False
        if agent_id is not None:
            if self.target_agent_ids and agent_id not in self.target_agent_ids:
                return False
        if fleet_id is not None:
            if self.target_fleet_ids and fleet_id not in self.target_fleet_ids:
                return False
        return True

    def is_expired(self) -> bool:
        """Check if the event has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        created = datetime.fromisoformat(self.timestamp)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        return elapsed > self.ttl_seconds


# ── Health Dashboard Data Class ───────────────────────────

@dataclass
class HealthDashboard:
    """Comprehensive platform health dashboard aggregating all components."""
    dashboard_id: str = field(default_factory=lambda: f"dash-{uuid.uuid4().hex[:8]}")
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Overall platform status
    platform_status: HealthStatus = HealthStatus.UNKNOWN
    platform_uptime_seconds: float = 0.0
    total_requests_served: int = 0
    total_errors: int = 0

    # Agent metrics
    total_agents: int = 0
    agents_by_state: dict[str, int] = field(default_factory=dict)
    # { "running": 5, "stopped": 1, "error": 0, ... }

    # Fleet metrics
    total_fleets: int = 0
    fleets_by_state: dict[str, int] = field(default_factory=dict)
    # { "active": 2, "draft": 1, ... }

    # Resource utilization
    resource_utilization: dict[str, float] = field(default_factory=dict)
    # { "cpu": 0.45, "memory": 0.62, "disk": 0.30, ... }

    # Alert summary
    active_alerts: int = 0
    alerts_by_severity: dict[str, int] = field(default_factory=dict)
    # { "critical": 0, "warning": 2, "info": 5, ... }

    # Quota summary
    agents_over_soft_quota: int = 0
    agents_over_hard_quota: int = 0

    # Event bus summary
    total_events_published: int = 0
    events_by_category: dict[str, int] = field(default_factory=dict)

    # Knowledge sync summary
    knowledge_entries_total: int = 0
    last_sync_timestamp: str = ""

    # Component health
    component_statuses: dict[str, str] = field(default_factory=dict)
    # { "agent_runtime": "healthy", "sandbox_system": "healthy", ... }

    # Top agents by resource usage
    top_cpu_agents: list[dict[str, Any]] = field(default_factory=list)
    top_memory_agents: list[dict[str, Any]] = field(default_factory=list)

    # Recent system events
    recent_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "generated_at": self.generated_at,
            "platform_status": self.platform_status.value,
            "platform_uptime_seconds": round(self.platform_uptime_seconds, 1),
            "total_requests_served": self.total_requests_served,
            "total_errors": self.total_errors,
            "total_agents": self.total_agents,
            "agents_by_state": self.agents_by_state,
            "total_fleets": self.total_fleets,
            "fleets_by_state": self.fleets_by_state,
            "resource_utilization": self.resource_utilization,
            "active_alerts": self.active_alerts,
            "alerts_by_severity": self.alerts_by_severity,
            "agents_over_soft_quota": self.agents_over_soft_quota,
            "agents_over_hard_quota": self.agents_over_hard_quota,
            "total_events_published": self.total_events_published,
            "events_by_category": self.events_by_category,
            "knowledge_entries_total": self.knowledge_entries_total,
            "last_sync_timestamp": self.last_sync_timestamp,
            "component_statuses": self.component_statuses,
            "top_cpu_agents": self.top_cpu_agents[:10],
            "top_memory_agents": self.top_memory_agents[:10],
            "recent_events": self.recent_events[:20],
        }


# ── Platform Core Engine ──────────────────────────────────

class PlatformCore:
    """Central platform management engine for the Buddy ecosystem.

    Manages the entire runtime lifecycle including agent instances,
    sandbox environments, health monitoring, resource allocation,
    cross-agent context synchronization, system alerts, fleet
    orchestration, knowledge sync, auto-scaling, quota enforcement,
    and the platform event bus.
    """

    def __init__(self):
        self._instances: dict[str, RuntimeInstance] = {}
        self._sandboxes: dict[str, SandboxEnvironment] = {}
        self._alerts: list[PlatformAlert] = []
        self._context_sync_events: list[ContextSyncEvent] = []
        self._health_history: list[HealthReport] = []
        self._config = PlatformConfig()
        self._is_running: bool = False
        self._start_time: str = ""
        self._total_requests_served: int = 0
        self._total_errors: int = 0
        self._health_check_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None

        # Fleet management
        self._fleets: dict[str, Fleet] = {}

        # Knowledge sync
        self._knowledge_store: dict[str, KnowledgeEntry] = {}
        self._knowledge_sync_history: list[KnowledgeSyncResult] = []

        # Resource quotas
        self._agent_quotas: dict[str, ResourceQuota] = {}

        # Event bus
        self._event_bus: list[PlatformEvent] = []
        self._event_subscriptions: dict[str, list[dict[str, Any]]] = {}
        # subscription format: {"subscriber_id": "agent-123", "categories": [...], "event_types": [...], "callback": ...}

    # ── Runtime Lifecycle ─────────────────────────────────

    def register_instance(self, agent_id: str, agent_name: str) -> RuntimeInstance:
        """Register a new agent runtime instance with the platform."""
        instance = RuntimeInstance(
            agent_id=agent_id,
            agent_name=agent_name,
            state=RuntimeState.INITIALIZING,
            started_at=datetime.now(timezone.utc).isoformat(),
            last_heartbeat=datetime.now(timezone.utc).isoformat(),
        )
        self._instances[agent_id] = instance
        logger.info(f"Runtime instance registered: {agent_name} ({agent_id})")
        return instance

    def update_instance_state(self, agent_id: str, state: RuntimeState):
        """Update the state of a runtime instance."""
        if agent_id in self._instances:
            self._instances[agent_id].state = state
            if state == RuntimeState.RUNNING:
                self._instances[agent_id].started_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Instance {agent_id} state -> {state.value}")

    def heartbeat(self, agent_id: str):
        """Record a heartbeat from an agent instance."""
        if agent_id in self._instances:
            inst = self._instances[agent_id]
            inst.last_heartbeat = datetime.now(timezone.utc).isoformat()
            if inst.state == RuntimeState.INITIALIZING:
                inst.state = RuntimeState.RUNNING

    def unregister_instance(self, agent_id: str):
        """Remove a runtime instance from the platform."""
        if agent_id in self._instances:
            inst = self._instances[agent_id]
            inst.state = RuntimeState.STOPPED
            # Clean up associated sandboxes
            for sandbox_id in list(inst.sandbox_instances):
                self.destroy_sandbox(sandbox_id)
            del self._instances[agent_id]
            logger.info(f"Runtime instance unregistered: {agent_id}")

    def get_instance(self, agent_id: str) -> RuntimeInstance | None:
        """Get a runtime instance by agent ID."""
        return self._instances.get(agent_id)

    def list_instances(
        self,
        state_filter: RuntimeState | None = None,
    ) -> list[RuntimeInstance]:
        """List all runtime instances, optionally filtered by state."""
        instances = list(self._instances.values())
        if state_filter:
            instances = [i for i in instances if i.state == state_filter]
        return instances

    # ── Sandbox Management ────────────────────────────────

    def create_sandbox(
        self,
        agent_id: str,
        sandbox_type: SandboxType = SandboxType.PYTHON,
        workspace_path: str = "",
        env_vars: dict[str, str] | None = None,
    ) -> SandboxEnvironment:
        """Create a new sandbox environment for an agent."""
        sandbox = SandboxEnvironment(
            sandbox_type=sandbox_type,
            agent_id=agent_id,
            workspace_path=workspace_path or f"/tmp/buddy-sandbox-{uuid.uuid4().hex[:8]}",
            environment_vars=env_vars or {},
        )
        sandbox.state = RuntimeState.RUNNING
        self._sandboxes[sandbox.sandbox_id] = sandbox

        # Link sandbox to agent instance
        if agent_id in self._instances:
            self._instances[agent_id].sandbox_instances.append(sandbox.sandbox_id)

        logger.info(f"Sandbox created: {sandbox.sandbox_id} ({sandbox_type.value}) for {agent_id}")
        return sandbox

    def get_sandbox(self, sandbox_id: str) -> SandboxEnvironment | None:
        """Get a sandbox by ID."""
        return self._sandboxes.get(sandbox_id)

    def list_sandboxes(self, agent_id: str | None = None) -> list[SandboxEnvironment]:
        """List all sandboxes, optionally filtered by agent."""
        sandboxes = list(self._sandboxes.values())
        if agent_id:
            sandboxes = [s for s in sandboxes if s.agent_id == agent_id]
        return sandboxes

    def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy a sandbox environment."""
        if sandbox_id in self._sandboxes:
            sandbox = self._sandboxes[sandbox_id]
            sandbox.state = RuntimeState.STOPPED
            del self._sandboxes[sandbox_id]
            logger.info(f"Sandbox destroyed: {sandbox_id}")
            return True
        return False

    # ── Health Monitoring ─────────────────────────────────

    async def generate_health_report(self) -> HealthReport:
        """Generate a comprehensive system health report."""
        report = HealthReport()

        # Agent health
        report.agent_count = len(self._instances)
        for inst in self._instances.values():
            state = inst.state
            if state == RuntimeState.RUNNING:
                report.healthy_agents += 1
            elif state in (RuntimeState.ERROR, RuntimeState.STOPPED):
                report.unhealthy_agents += 1
            else:
                report.degraded_agents += 1

        # Component statuses
        report.component_statuses = {
            "agent_runtime": HealthStatus.HEALTHY if report.healthy_agents > 0 else HealthStatus.DEGRADED,
            "sandbox_system": HealthStatus.HEALTHY,
            "memory_system": HealthStatus.HEALTHY,
            "api_gateway": HealthStatus.HEALTHY,
            "database": HealthStatus.HEALTHY,
        }

        # Resource utilization
        report.resource_utilization = {
            "agents": len(self._instances) / max(self._config.max_agents, 1),
            "active_sessions": sum(i.active_sessions for i in self._instances.values()) / max(self._config.max_concurrent_sessions, 1),
        }

        # Active alerts
        report.active_alerts = [
            a.to_dict() for a in self._alerts
            if not a.resolved_at
        ]

        # Overall status
        if report.unhealthy_agents > 0:
            report.overall_status = HealthStatus.UNHEALTHY
        elif report.degraded_agents > 0:
            report.overall_status = HealthStatus.DEGRADED
        else:
            report.overall_status = HealthStatus.HEALTHY

        self._health_history.append(report)
        if len(self._health_history) > 100:
            self._health_history = self._health_history[-50:]

        return report

    async def start_health_monitoring(self, interval: int = 60):
        """Start background health monitoring."""
        self._config.health_check_interval = interval
        self._is_running = True
        self._start_time = datetime.now(timezone.utc).isoformat()
        logger.info(f"Health monitoring started (interval: {interval}s)")

    async def stop_health_monitoring(self):
        """Stop background health monitoring."""
        self._is_running = False
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("Health monitoring stopped")

    # ── Alert Management ──────────────────────────────────

    def create_alert(
        self,
        severity: AlertSeverity,
        component: str,
        message: str,
        details: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> PlatformAlert:
        """Create a new system alert."""
        alert = PlatformAlert(
            severity=severity,
            component=component,
            message=message,
            details=details,
            metadata=metadata or {},
        )
        self._alerts.append(alert)
        logger.warning(f"Alert [{severity.value}] {component}: {message}")
        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def list_alerts(
        self,
        severity: AlertSeverity | None = None,
        include_resolved: bool = False,
    ) -> list[PlatformAlert]:
        """List alerts, optionally filtered."""
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if not include_resolved:
            alerts = [a for a in alerts if not a.resolved_at]
        return alerts

    # ── Context Synchronization ───────────────────────────

    def sync_context(
        self,
        source_agent_id: str,
        target_agent_ids: list[str],
        context_type: str,
        content: dict[str, Any],
        priority: int = 5,
    ) -> ContextSyncEvent:
        """Synchronize context between agents."""
        event = ContextSyncEvent(
            source_agent_id=source_agent_id,
            target_agent_ids=target_agent_ids,
            context_type=context_type,
            content=content,
            priority=priority,
        )
        self._context_sync_events.append(event)
        logger.info(
            f"Context sync: {source_agent_id} -> {target_agent_ids} "
            f"({context_type}, priority={priority})"
        )
        return event

    def get_sync_events(
        self,
        agent_id: str | None = None,
        context_type: str | None = None,
        limit: int = 50,
    ) -> list[ContextSyncEvent]:
        """Get context sync events, optionally filtered."""
        events = self._context_sync_events
        if agent_id:
            events = [
                e for e in events
                if e.source_agent_id == agent_id or agent_id in e.target_agent_ids
            ]
        if context_type:
            events = [e for e in events if e.context_type == context_type]
        return events[-limit:]

    # ── Resource Management ───────────────────────────────

    def check_resource_limits(self, agent_id: str) -> dict[str, Any]:
        """Check if an agent is within resource limits."""
        instance = self._instances.get(agent_id)
        if not instance:
            return {"within_limits": True, "message": "No instance found"}

        limits = {
            "active_sessions": instance.active_sessions <= self._config.max_concurrent_sessions,
            "agent_count": len(self._instances) <= self._config.max_agents,
        }

        return {
            "within_limits": all(limits.values()),
            "limits": limits,
            "current": {
                "active_sessions": instance.active_sessions,
                "total_agents": len(self._instances),
            },
        }

    # ── Statistics ─────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive platform statistics."""
        instances = list(self._instances.values())
        return {
            "platform_id": self._config.platform_id,
            "is_running": self._is_running,
            "uptime_seconds": (
                (datetime.now(timezone.utc) - datetime.fromisoformat(self._start_time)).total_seconds()
                if self._start_time else 0
            ),
            "instances": {
                "total": len(instances),
                "running": sum(1 for i in instances if i.state == RuntimeState.RUNNING),
                "stopped": sum(1 for i in instances if i.state == RuntimeState.STOPPED),
                "error": sum(1 for i in instances if i.state == RuntimeState.ERROR),
            },
            "sandboxes": {
                "total": len(self._sandboxes),
                "active": sum(1 for s in self._sandboxes.values() if s.state == RuntimeState.RUNNING),
            },
            "alerts": {
                "total": len(self._alerts),
                "active": sum(1 for a in self._alerts if not a.resolved_at),
                "acknowledged": sum(1 for a in self._alerts if a.acknowledged),
            },
            "resources": {
                "max_agents": self._config.max_agents,
                "max_concurrent_sessions": self._config.max_concurrent_sessions,
            },
            "total_requests_served": self._total_requests_served,
            "total_errors": self._total_errors,
            "sync_events_total": len(self._context_sync_events),
        }

    def get_instance_details(self, agent_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific instance."""
        instance = self._instances.get(agent_id)
        if not instance:
            return None

        return {
            **instance.to_dict(),
            "sandboxes": [
                self._sandboxes[sid].to_dict()
                for sid in instance.sandbox_instances
                if sid in self._sandboxes
            ],
            "resource_limits": self.check_resource_limits(agent_id),
        }

    def record_request(self, agent_id: str, success: bool = True):
        """Record an API request for statistics."""
        self._total_requests_served += 1
        if not success:
            self._total_errors += 1
        if agent_id in self._instances:
            self._instances[agent_id].total_requests += 1
            if not success:
                self._instances[agent_id].error_count += 1

    def reset(self):
        """Reset all platform state."""
        self._instances.clear()
        self._sandboxes.clear()
        self._alerts.clear()
        self._context_sync_events.clear()
        self._health_history.clear()
        self._total_requests_served = 0
        self._total_errors = 0
        self._fleets.clear()
        self._knowledge_store.clear()
        self._knowledge_sync_history.clear()
        self._agent_quotas.clear()
        self._event_bus.clear()
        self._event_subscriptions.clear()
        logger.info("Platform core reset")

    # ── Agent Fleet Orchestration ──────────────────────────

    def create_fleet(
        self,
        fleet_name: str,
        agent_ids: list[str] | None = None,
        config: FleetConfig | None = None,
    ) -> Fleet:
        """Create a new agent fleet for coordinated management.

        Args:
            fleet_name: Human-readable name for the fleet.
            agent_ids: Initial list of agent IDs to include. Defaults to empty.
            config: Fleet configuration. Uses defaults if not provided.

        Returns:
            The newly created Fleet object.
        """
        fleet_config = config or FleetConfig()
        fleet_config.fleet_name = fleet_name

        fleet = Fleet(
            fleet_name=fleet_name,
            agent_ids=agent_ids or [],
            config=fleet_config,
            state=FleetState.DRAFT,
        )

        # Ensure fleet_id consistency between fleet and its config
        fleet_config.fleet_id = fleet.fleet_id

        self._fleets[fleet.fleet_id] = fleet
        logger.info(f"Fleet created: {fleet_name} ({fleet.fleet_id}) with {len(agent_ids or [])} agents")
        return fleet

    def add_agent_to_fleet(self, fleet_id: str, agent_id: str) -> bool:
        """Add an agent to a fleet.

        Args:
            fleet_id: ID of the target fleet.
            agent_id: ID of the agent to add.

        Returns:
            True if the agent was added, False if fleet or agent not found.
        """
        fleet = self._fleets.get(fleet_id)
        if not fleet:
            logger.warning(f"Fleet not found: {fleet_id}")
            return False

        if agent_id not in self._instances:
            logger.warning(f"Agent not registered: {agent_id}")
            return False

        if agent_id in fleet.agent_ids:
            logger.info(f"Agent {agent_id} already in fleet {fleet_id}")
            return True

        # Check fleet capacity
        if len(fleet.agent_ids) >= fleet.config.max_agents:
            logger.warning(f"Fleet {fleet_id} at max capacity ({fleet.config.max_agents})")
            return False

        fleet.agent_ids.append(agent_id)
        fleet.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Agent {agent_id} added to fleet {fleet.fleet_name} ({fleet_id})")
        return True

    def remove_agent_from_fleet(self, fleet_id: str, agent_id: str) -> bool:
        """Remove an agent from a fleet.

        Args:
            fleet_id: ID of the target fleet.
            agent_id: ID of the agent to remove.

        Returns:
            True if removed, False if fleet or agent not found.
        """
        fleet = self._fleets.get(fleet_id)
        if not fleet:
            return False

        if agent_id not in fleet.agent_ids:
            return False

        # Prevent scaling below minimum
        if len(fleet.agent_ids) <= fleet.config.min_agents:
            logger.warning(
                f"Cannot remove agent {agent_id} from fleet {fleet_id}: "
                f"at minimum capacity ({fleet.config.min_agents})"
            )
            return False

        fleet.agent_ids.remove(agent_id)
        fleet.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Agent {agent_id} removed from fleet {fleet.fleet_name} ({fleet_id})")
        return True

    def deploy_fleet(
        self,
        fleet_id: str,
        version: str = "",
        strategy: str | None = None,
    ) -> FleetDeployment:
        """Deploy all agents in a fleet synchronously.

        Sets all agents in the fleet to RUNNING state following the configured
        deployment strategy (rolling, blue-green, or canary).

        Args:
            fleet_id: ID of the fleet to deploy.
            version: Deployment version identifier.
            strategy: Override the fleet's deployment strategy.

        Returns:
            FleetDeployment record with the result of the deployment.
        """
        fleet = self._fleets.get(fleet_id)
        deployment = FleetDeployment(
            fleet_id=fleet_id,
            agent_ids=list(fleet.agent_ids) if fleet else [],
            version=version or datetime.now(timezone.utc).isoformat(),
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        if not fleet:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = f"Fleet not found: {fleet_id}"
            logger.error(deployment.error_message)
            return deployment

        if not fleet.agent_ids:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = f"Fleet {fleet_id} has no agents"
            logger.error(deployment.error_message)
            return deployment

        deploy_strategy = strategy or fleet.config.deployment_strategy
        deployment.metadata["strategy"] = deploy_strategy
        deployment.status = DeploymentStatus.IN_PROGRESS
        fleet.state = FleetState.DEPLOYING

        failed_agents: list[str] = []
        for agent_id in fleet.agent_ids:
            try:
                instance = self._instances.get(agent_id)
                if instance:
                    instance.state = RuntimeState.RUNNING
                    instance.started_at = datetime.now(timezone.utc).isoformat()
                    instance.metadata["fleet_id"] = fleet_id
                    instance.metadata["deployment_version"] = deployment.version
            except Exception as e:
                failed_agents.append(agent_id)
                logger.error(f"Failed to deploy agent {agent_id}: {e}")

        if failed_agents:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = f"Failed agents: {failed_agents}"
            fleet.state = FleetState.DEGRADED

            if fleet.config.rollback_on_failure:
                logger.info(f"Rolling back fleet {fleet_id} due to deployment failures")
                self.rollback_fleet(fleet_id, deployment.deployment_id)
                deployment.status = DeploymentStatus.ROLLED_BACK
        else:
            deployment.status = DeploymentStatus.SUCCEEDED
            fleet.state = FleetState.ACTIVE
            logger.info(f"Fleet {fleet.fleet_name} ({fleet_id}) deployed successfully")

        deployment.completed_at = datetime.now(timezone.utc).isoformat()
        fleet.deployment_history.append(deployment)
        fleet.updated_at = datetime.now(timezone.utc).isoformat()

        return deployment

    def rollback_fleet(
        self,
        fleet_id: str,
        deployment_id: str | None = None,
    ) -> FleetDeployment:
        """Roll back a fleet deployment to the previous successful deployment.

        Args:
            fleet_id: ID of the fleet to roll back.
            deployment_id: Specific deployment to roll back from. If None,
                           rolls back the most recent deployment.

        Returns:
            FleetDeployment record for the rollback operation.
        """
        fleet = self._fleets.get(fleet_id)
        rollback = FleetDeployment(
            fleet_id=fleet_id,
            status=DeploymentStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc).isoformat(),
            version=f"rollback-{datetime.now(timezone.utc).isoformat()}",
        )

        if not fleet:
            rollback.status = DeploymentStatus.FAILED
            rollback.error_message = f"Fleet not found: {fleet_id}"
            return rollback

        fleet.state = FleetState.ROLLING_BACK

        # Find the previous successful deployment
        successful_deployments = [
            d for d in fleet.deployment_history
            if d.status == DeploymentStatus.SUCCEEDED
        ]
        if len(successful_deployments) < 1:
            rollback.status = DeploymentStatus.FAILED
            rollback.error_message = "No previous successful deployment to roll back to"
            fleet.state = FleetState.DEGRADED
            return rollback

        previous = successful_deployments[-1]
        rollback.version = previous.version
        rollback.agent_ids = list(previous.agent_ids)

        # Restore agents to previous deployment state
        for agent_id in previous.agent_ids:
            instance = self._instances.get(agent_id)
            if instance:
                instance.state = RuntimeState.RUNNING
                instance.metadata["deployment_version"] = previous.version

        rollback.status = DeploymentStatus.SUCCEEDED
        rollback.completed_at = datetime.now(timezone.utc).isoformat()
        fleet.state = FleetState.ACTIVE
        fleet.deployment_history.append(rollback)
        fleet.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Fleet {fleet.fleet_name} ({fleet_id}) rolled back to {previous.version}")
        return rollback

    def scale_fleet(
        self,
        fleet_id: str,
        target_count: int,
    ) -> dict[str, Any]:
        """Scale a fleet to a target number of agent instances.

        Args:
            fleet_id: ID of the fleet to scale.
            target_count: Desired number of agents in the fleet.

        Returns:
            Dict with scaling result: previous_count, target_count, actual_count,
            status, and message.
        """
        fleet = self._fleets.get(fleet_id)
        result: dict[str, Any] = {
            "fleet_id": fleet_id,
            "previous_count": 0,
            "target_count": target_count,
            "actual_count": 0,
            "status": "failed",
            "message": "",
        }

        if not fleet:
            result["message"] = f"Fleet not found: {fleet_id}"
            return result

        result["previous_count"] = len(fleet.agent_ids)

        # Enforce cooldown period
        if fleet.last_scale_time:
            last_scale = datetime.fromisoformat(fleet.last_scale_time)
            cooldown_elapsed = (datetime.now(timezone.utc) - last_scale).total_seconds()
            if cooldown_elapsed < fleet.config.cooldown_period:
                result["status"] = "cooldown"
                result["message"] = (
                    f"Scaling in cooldown. "
                    f"Wait {fleet.config.cooldown_period - cooldown_elapsed:.0f}s"
                )
                result["actual_count"] = len(fleet.agent_ids)
                return result

        # Clamp to configured limits
        target_count = max(fleet.config.min_agents, min(target_count, fleet.config.max_agents))

        previous_state = fleet.state
        fleet.state = FleetState.SCALING

        current_count = len(fleet.agent_ids)
        if target_count > current_count:
            # Scale up: need to add new agents
            needed = target_count - current_count
            added = 0
            for _ in range(needed):
                new_agent_id = f"agent-{uuid.uuid4().hex[:8]}"
                new_agent_name = f"{fleet.fleet_name}-agent-{new_agent_id[:6]}"
                self.register_instance(new_agent_id, new_agent_name)
                fleet.agent_ids.append(new_agent_id)
                added += 1
            result["message"] = f"Scaled up by {added} agents"
        elif target_count < current_count:
            # Scale down: remove excess agents
            removed = 0
            to_remove = current_count - target_count
            # Remove agents that are not RUNNING first, then from the end
            for agent_id in list(fleet.agent_ids):
                if removed >= to_remove:
                    break
                instance = self._instances.get(agent_id)
                if instance and instance.state != RuntimeState.RUNNING:
                    self.unregister_instance(agent_id)
                    fleet.agent_ids.remove(agent_id)
                    removed += 1
            # If still need to remove, take from the end
            for agent_id in list(fleet.agent_ids):
                if removed >= to_remove:
                    break
                self.unregister_instance(agent_id)
                fleet.agent_ids.remove(agent_id)
                removed += 1
            result["message"] = f"Scaled down by {removed} agents"
        else:
            result["message"] = "Already at target count"

        result["actual_count"] = len(fleet.agent_ids)
        result["status"] = "success"
        fleet.state = FleetState.ACTIVE if previous_state == FleetState.ACTIVE else previous_state
        fleet.last_scale_time = datetime.now(timezone.utc).isoformat()
        fleet.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Fleet {fleet.fleet_name} ({fleet_id}) scaled: {current_count} -> {len(fleet.agent_ids)}")
        return result

    def get_fleet(self, fleet_id: str) -> Fleet | None:
        """Get a fleet by ID."""
        return self._fleets.get(fleet_id)

    def get_fleet_status(self, fleet_id: str) -> dict[str, Any] | None:
        """Get detailed status of a fleet including all agent states.

        Args:
            fleet_id: ID of the fleet.

        Returns:
            Dict with fleet status or None if fleet not found.
        """
        fleet = self._fleets.get(fleet_id)
        if not fleet:
            return None

        agent_statuses = {}
        for agent_id in fleet.agent_ids:
            instance = self._instances.get(agent_id)
            agent_statuses[agent_id] = {
                "state": instance.state.value if instance else "unknown",
                "agent_name": instance.agent_name if instance else "",
                "uptime_seconds": instance.uptime_seconds if instance else 0,
                "active_sessions": instance.active_sessions if instance else 0,
                "error_count": instance.error_count if instance else 0,
            }

        return {
            "fleet_id": fleet.fleet_id,
            "fleet_name": fleet.fleet_name,
            "state": fleet.state.value,
            "agent_count": len(fleet.agent_ids),
            "agents": agent_statuses,
            "config": {
                "min_agents": fleet.config.min_agents,
                "max_agents": fleet.config.max_agents,
                "deployment_strategy": fleet.config.deployment_strategy,
            },
            "last_deployment": fleet.deployment_history[-1].to_dict() if fleet.deployment_history else None,
            "updated_at": fleet.updated_at,
        }

    def list_fleets(self, state_filter: FleetState | None = None) -> list[Fleet]:
        """List all fleets, optionally filtered by state."""
        fleets = list(self._fleets.values())
        if state_filter:
            fleets = [f for f in fleets if f.state == state_filter]
        return fleets

    # ── Cross-Agent Knowledge Sync ────────────────────────

    def sync_knowledge(
        self,
        fleet_id: str | None = None,
        agent_ids: list[str] | None = None,
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
    ) -> KnowledgeSyncResult:
        """Synchronize knowledge / memories across agents in a fleet.

        Collects knowledge entries from all source agents in the fleet or
        specified agent list, resolves conflicts using the chosen strategy,
        and distributes the resolved entries back to all agents.

        Args:
            fleet_id: Fleet ID to sync knowledge across. If provided, all agents
                      in the fleet are used as both sources and targets.
            agent_ids: Explicit list of agent IDs to sync. Used if fleet_id is None.
            strategy: Conflict resolution strategy for handling conflicting entries.

        Returns:
            KnowledgeSyncResult summarizing the sync operation.
        """
        result = KnowledgeSyncResult(
            fleet_id=fleet_id or "",
            strategy=strategy,
        )

        # Determine the set of agents to sync
        sync_agent_ids: list[str] = []
        if fleet_id:
            fleet = self._fleets.get(fleet_id)
            if fleet:
                sync_agent_ids = list(fleet.agent_ids)
        elif agent_ids:
            sync_agent_ids = list(agent_ids)

        if not sync_agent_ids:
            result.entries_skipped = 0
            logger.warning("Knowledge sync: no agents to sync")
            return result

        # Collect all knowledge entries from the sync agents
        agent_entries: dict[str, list[KnowledgeEntry]] = {}
        for agent_id in sync_agent_ids:
            entries = [
                e for e in self._knowledge_store.values()
                if e.source_agent_id == agent_id and not e.is_expired()
            ]
            agent_entries[agent_id] = entries

        # Group entries by key to detect conflicts
        entries_by_key: dict[str, list[KnowledgeEntry]] = {}
        for entries in agent_entries.values():
            for entry in entries:
                if entry.key not in entries_by_key:
                    entries_by_key[entry.key] = []
                entries_by_key[entry.key].append(entry)

        # Resolve conflicts and build the final set of entries
        for key, entries in entries_by_key.items():
            if len(entries) == 1:
                # No conflict: store the single entry
                self._knowledge_store[entries[0].entry_id] = entries[0]
                result.entries_synced += 1
            else:
                # Conflict detected
                result.entries_conflicted += 1
                resolved = self._resolve_knowledge_conflict(entries, strategy)
                if resolved:
                    self._knowledge_store[resolved.entry_id] = resolved
                    result.entries_resolved += 1
                    result.conflicts.append({
                        "key": key,
                        "conflicting_versions": [e.version for e in entries],
                        "resolved_version": resolved.version,
                        "strategy": strategy.value,
                    })
                else:
                    result.entries_skipped += 1

        # Purge expired entries
        expired_keys = [
            eid for eid, entry in self._knowledge_store.items()
            if entry.is_expired()
        ]
        for eid in expired_keys:
            del self._knowledge_store[eid]
            result.entries_skipped += 1

        self._knowledge_sync_history.append(result)
        logger.info(
            f"Knowledge sync complete: {result.entries_synced} synced, "
            f"{result.entries_conflicted} conflicted, "
            f"{result.entries_resolved} resolved, "
            f"{result.entries_skipped} skipped"
        )
        return result

    def _resolve_knowledge_conflict(
        self,
        entries: list[KnowledgeEntry],
        strategy: ConflictResolutionStrategy,
    ) -> KnowledgeEntry | None:
        """Resolve a conflict between multiple knowledge entries for the same key.

        Args:
            entries: Conflicting KnowledgeEntry objects.
            strategy: Resolution strategy to apply.

        Returns:
            The resolved KnowledgeEntry, or None if the conflict cannot be resolved.
        """
        if not entries:
            return None

        if strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            # Pick the entry with the most recent updated_at timestamp
            entries.sort(key=lambda e: e.updated_at, reverse=True)
            winner = entries[0]
            winner.version += 1
            winner.updated_at = datetime.now(timezone.utc).isoformat()
            return winner

        elif strategy == ConflictResolutionStrategy.SOURCE_PRIORITY:
            # Source agent with the lowest lexicographic ID wins
            entries.sort(key=lambda e: e.source_agent_id)
            winner = entries[0]
            winner.version += 1
            winner.updated_at = datetime.now(timezone.utc).isoformat()
            return winner

        elif strategy == ConflictResolutionStrategy.MERGE:
            # Merge all values into a list and combine tags
            merged_entry = KnowledgeEntry(
                key=entries[0].key,
                source_agent_id="platform",
                value=[e.value for e in entries],
                tags=list(set(tag for e in entries for tag in e.tags)),
                version=max(e.version for e in entries) + 1,
            )
            return merged_entry

        elif strategy == ConflictResolutionStrategy.KEEP_BOTH:
            # Keep all entries with versioned keys
            # Return the latest one as primary, others remain in store
            entries.sort(key=lambda e: e.updated_at, reverse=True)
            for e in entries[1:]:
                e.key = f"{e.key}__v{e.version}"
            winner = entries[0]
            winner.version += 1
            winner.updated_at = datetime.now(timezone.utc).isoformat()
            return winner

        elif strategy == ConflictResolutionStrategy.MANUAL:
            # Mark as conflicting without automatic resolution
            logger.info(f"Manual resolution required for key: {entries[0].key}")
            return None

        return None

    def store_knowledge(
        self,
        source_agent_id: str,
        key: str,
        value: Any,
        tags: list[str] | None = None,
        ttl_seconds: float | None = None,
    ) -> KnowledgeEntry:
        """Store a knowledge entry for an agent.

        Args:
            source_agent_id: ID of the agent that owns this knowledge.
            key: Unique key for the knowledge entry.
            value: The knowledge content.
            tags: Optional tags for categorization.
            ttl_seconds: Optional time-to-live in seconds.

        Returns:
            The stored KnowledgeEntry.
        """
        entry = KnowledgeEntry(
            source_agent_id=source_agent_id,
            key=key,
            value=value,
            tags=tags or [],
            ttl_seconds=ttl_seconds,
        )
        self._knowledge_store[entry.entry_id] = entry
        logger.debug(f"Knowledge stored: {key} from {source_agent_id}")
        return entry

    def get_knowledge(
        self,
        key: str | None = None,
        agent_id: str | None = None,
        tags: list[str] | None = None,
    ) -> list[KnowledgeEntry]:
        """Retrieve knowledge entries, optionally filtered.

        Args:
            key: Filter by exact key match.
            agent_id: Filter by source agent ID.
            tags: Filter by tags (entries must have at least one matching tag).

        Returns:
            List of matching KnowledgeEntry objects.
        """
        entries = list(self._knowledge_store.values())

        # Remove expired entries
        entries = [e for e in entries if not e.is_expired()]

        if key:
            entries = [e for e in entries if e.key == key]
        if agent_id:
            entries = [e for e in entries if e.source_agent_id == agent_id]
        if tags:
            entries = [e for e in entries if any(t in e.tags for t in tags)]

        return entries

    def get_knowledge_sync_history(
        self,
        fleet_id: str | None = None,
        limit: int = 20,
    ) -> list[KnowledgeSyncResult]:
        """Get knowledge sync history, optionally filtered by fleet."""
        history = self._knowledge_sync_history
        if fleet_id:
            history = [h for h in history if h.fleet_id == fleet_id]
        return history[-limit:]

    # ── Platform Health Dashboard ─────────────────────────

    def generate_health_dashboard(self) -> HealthDashboard:
        """Generate a comprehensive platform health dashboard.

        Aggregates all agent statuses, fleet statuses, resource usage,
        alerts, quotas, events, and knowledge sync metrics into a single
        dashboard view.

        Returns:
            HealthDashboard with full platform health snapshot.
        """
        dashboard = HealthDashboard()

        # Platform uptime
        if self._start_time:
            start = datetime.fromisoformat(self._start_time)
            dashboard.platform_uptime_seconds = (datetime.now(timezone.utc) - start).total_seconds()

        dashboard.total_requests_served = self._total_requests_served
        dashboard.total_errors = self._total_errors

        # Agent metrics
        instances = list(self._instances.values())
        dashboard.total_agents = len(instances)
        for inst in instances:
            state_key = inst.state.value
            dashboard.agents_by_state[state_key] = dashboard.agents_by_state.get(state_key, 0) + 1

        # Fleet metrics
        fleets = list(self._fleets.values())
        dashboard.total_fleets = len(fleets)
        for fleet in fleets:
            state_key = fleet.state.value
            dashboard.fleets_by_state[state_key] = dashboard.fleets_by_state.get(state_key, 0) + 1

        # Resource utilization
        all_agents = list(self._instances.values())
        if all_agents:
            total_cpu = sum(i.cpu_usage_percent for i in all_agents)
            total_memory = sum(i.memory_usage_mb for i in all_agents)
            dashboard.resource_utilization = {
                "cpu_percent": round(total_cpu / len(all_agents), 2),
                "memory_mb": round(total_memory, 2),
                "agent_capacity": round(len(self._instances) / max(self._config.max_agents, 1), 2),
                "active_sessions": sum(i.active_sessions for i in all_agents),
                "session_capacity": round(
                    sum(i.active_sessions for i in all_agents) / max(self._config.max_concurrent_sessions, 1), 2
                ),
            }

        # Alert summary
        for alert in self._alerts:
            if not alert.resolved_at:
                dashboard.active_alerts += 1
                sev = alert.severity.value
                dashboard.alerts_by_severity[sev] = dashboard.alerts_by_severity.get(sev, 0) + 1

        # Component statuses
        dashboard.component_statuses = {
            "agent_runtime": "healthy" if dashboard.agents_by_state.get("running", 0) > 0 else "degraded",
            "sandbox_system": "healthy" if self._sandboxes else "unknown",
            "fleet_orchestrator": "healthy" if self._fleets else "unknown",
            "event_bus": "healthy",
            "knowledge_store": "healthy",
            "quota_enforcer": "healthy",
            "api_gateway": "healthy",
        }

        # Overall platform status
        if dashboard.agents_by_state.get("error", 0) > 0:
            dashboard.platform_status = HealthStatus.UNHEALTHY
        elif dashboard.agents_by_state.get("stopped", 0) > 0 or dashboard.agents_by_state.get("restarting", 0) > 0:
            dashboard.platform_status = HealthStatus.DEGRADED
        elif dashboard.active_alerts > 0:
            dashboard.platform_status = HealthStatus.DEGRADED
        else:
            dashboard.platform_status = HealthStatus.HEALTHY

        # Quota summary
        for agent_id, quota in self._agent_quotas.items():
            if not quota.enabled:
                continue
            status = self.check_quota(agent_id)
            if status and not status.within_soft_limits:
                dashboard.agents_over_soft_quota += 1
            if status and not status.within_hard_limits:
                dashboard.agents_over_hard_quota += 1

        # Event bus summary
        dashboard.total_events_published = len(self._event_bus)
        for event in self._event_bus:
            cat = event.category.value
            dashboard.events_by_category[cat] = dashboard.events_by_category.get(cat, 0) + 1

        # Knowledge sync summary
        dashboard.knowledge_entries_total = len(self._knowledge_store)
        if self._knowledge_sync_history:
            dashboard.last_sync_timestamp = self._knowledge_sync_history[-1].timestamp

        # Top agents by resource usage
        sorted_by_cpu = sorted(all_agents, key=lambda i: i.cpu_usage_percent, reverse=True)
        dashboard.top_cpu_agents = [
            {"agent_id": i.agent_id, "agent_name": i.agent_name, "cpu_percent": i.cpu_usage_percent}
            for i in sorted_by_cpu[:5]
        ]
        sorted_by_memory = sorted(all_agents, key=lambda i: i.memory_usage_mb, reverse=True)
        dashboard.top_memory_agents = [
            {"agent_id": i.agent_id, "agent_name": i.agent_name, "memory_mb": i.memory_usage_mb}
            for i in sorted_by_memory[:5]
        ]

        # Recent events
        recent = sorted(self._event_bus, key=lambda e: e.timestamp, reverse=True)[:20]
        dashboard.recent_events = [e.to_dict() for e in recent]

        logger.info(f"Health dashboard generated: {dashboard.platform_status.value}")
        return dashboard

    # ── Auto-Scaling Engine ───────────────────────────────

    def auto_scale(
        self,
        fleet_id: str | None = None,
        cpu_threshold_high: float = 80.0,
        cpu_threshold_low: float = 20.0,
        memory_threshold_high: float = 80.0,
        memory_threshold_low: float = 20.0,
        session_threshold_high: int = 100,
        session_threshold_low: int = 10,
        scale_up_factor: float = 1.5,
        scale_down_factor: float = 0.5,
    ) -> dict[str, Any]:
        """Automatically scale agent instances up or down based on load metrics.

        Evaluates CPU, memory, and session load for the specified fleet (or
        all fleets) and scales accordingly. Scaling decisions respect the
        fleet's configured min/max agent limits.

        Args:
            fleet_id: Specific fleet to auto-scale. If None, scales all fleets.
            cpu_threshold_high: CPU percentage above which to scale up.
            cpu_threshold_low: CPU percentage below which to scale down.
            memory_threshold_high: Memory percentage above which to scale up.
            memory_threshold_low: Memory percentage below which to scale down.
            session_threshold_high: Active sessions above which to scale up.
            session_threshold_low: Active sessions below which to scale down.
            scale_up_factor: Multiplier to increase agent count by.
            scale_down_factor: Multiplier to decrease agent count by.

        Returns:
            Dict with decisions made, scaling results, and summary.
        """
        result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decisions": [],
            "scaling_results": [],
            "summary": {"scaled_up": 0, "scaled_down": 0, "no_change": 0},
        }

        target_fleets = (
            [self._fleets[fleet_id]] if fleet_id and fleet_id in self._fleets
            else list(self._fleets.values())
        )

        if not target_fleets:
            result["summary"]["message"] = "No fleets to evaluate"
            return result

        for fleet in target_fleets:
            if fleet.state not in (FleetState.ACTIVE, FleetState.DEGRADED):
                result["decisions"].append({
                    "fleet_id": fleet.fleet_id,
                    "action": "skip",
                    "reason": f"Fleet state is {fleet.state.value}",
                })
                result["summary"]["no_change"] += 1
                continue

            # Collect metrics for agents in this fleet
            fleet_agents = [
                self._instances[aid] for aid in fleet.agent_ids
                if aid in self._instances
            ]

            if not fleet_agents:
                result["decisions"].append({
                    "fleet_id": fleet.fleet_id,
                    "action": "skip",
                    "reason": "No active agents",
                })
                result["summary"]["no_change"] += 1
                continue

            # Calculate average metrics
            avg_cpu = sum(i.cpu_usage_percent for i in fleet_agents) / len(fleet_agents)
            avg_memory = sum(i.memory_usage_mb for i in fleet_agents) / len(fleet_agents)
            total_sessions = sum(i.active_sessions for i in fleet_agents)

            current_count = len(fleet.agent_ids)
            decision = {
                "fleet_id": fleet.fleet_id,
                "fleet_name": fleet.fleet_name,
                "current_count": current_count,
                "avg_cpu": round(avg_cpu, 1),
                "avg_memory_mb": round(avg_memory, 1),
                "total_sessions": total_sessions,
            }

            # Determine if scaling is needed
            need_scale_up = (
                avg_cpu > cpu_threshold_high
                or avg_memory > memory_threshold_high
                or total_sessions > session_threshold_high
            )
            need_scale_down = (
                avg_cpu < cpu_threshold_low
                and avg_memory < memory_threshold_low
                and total_sessions < session_threshold_low
            )

            if need_scale_up:
                target_count = min(
                    fleet.config.max_agents,
                    max(fleet.config.min_agents, int(current_count * scale_up_factor) + 1)
                )
                if target_count > current_count:
                    decision["action"] = "scale_up"
                    decision["target_count"] = target_count
                    scale_result = self.scale_fleet(fleet.fleet_id, target_count)
                    result["scaling_results"].append(scale_result)
                    result["summary"]["scaled_up"] += 1
                else:
                    decision["action"] = "no_change"
                    decision["reason"] = f"Already at max capacity ({fleet.config.max_agents})"
                    result["summary"]["no_change"] += 1
            elif need_scale_down:
                target_count = max(
                    fleet.config.min_agents,
                    min(current_count - 1, int(current_count * scale_down_factor))
                )
                if target_count < current_count:
                    decision["action"] = "scale_down"
                    decision["target_count"] = target_count
                    scale_result = self.scale_fleet(fleet.fleet_id, target_count)
                    result["scaling_results"].append(scale_result)
                    result["summary"]["scaled_down"] += 1
                else:
                    decision["action"] = "no_change"
                    decision["reason"] = f"Already at min capacity ({fleet.config.min_agents})"
                    result["summary"]["no_change"] += 1
            else:
                decision["action"] = "no_change"
                decision["reason"] = "Metrics within thresholds"
                result["summary"]["no_change"] += 1

            result["decisions"].append(decision)

        logger.info(
            f"Auto-scale complete: {result['summary']['scaled_up']} up, "
            f"{result['summary']['scaled_down']} down, "
            f"{result['summary']['no_change']} unchanged"
        )
        return result

    # ── Resource Quota Enforcement ────────────────────────

    def set_resource_quota(
        self,
        agent_id: str,
        limits: dict[ResourceType, dict[str, float]],
    ) -> ResourceQuota:
        """Set per-agent resource quotas with soft and hard limits.

        Example limits format:
        {
            ResourceType.CPU: {"soft": 2.0, "hard": 4.0},
            ResourceType.MEMORY: {"soft": 512.0, "hard": 1024.0},
        }

        Args:
            agent_id: ID of the agent to set quotas for.
            limits: Dict mapping ResourceType to {"soft": value, "hard": value}.

        Returns:
            The created or updated ResourceQuota.
        """
        if agent_id in self._agent_quotas:
            quota = self._agent_quotas[agent_id]
            quota.limits = limits
            quota.updated_at = datetime.now(timezone.utc).isoformat()
        else:
            quota = ResourceQuota(
                agent_id=agent_id,
                limits=limits,
            )
            self._agent_quotas[agent_id] = quota

        logger.info(f"Resource quota set for {agent_id}: {len(limits)} resource types")
        return quota

    def get_resource_quota(self, agent_id: str) -> ResourceQuota | None:
        """Get the resource quota for an agent."""
        return self._agent_quotas.get(agent_id)

    def remove_resource_quota(self, agent_id: str) -> bool:
        """Remove the resource quota for an agent."""
        if agent_id in self._agent_quotas:
            del self._agent_quotas[agent_id]
            logger.info(f"Resource quota removed for {agent_id}")
            return True
        return False

    def check_quota(self, agent_id: str) -> ResourceQuotaStatus | None:
        """Check current resource usage against defined quotas for an agent.

        Args:
            agent_id: ID of the agent to check.

        Returns:
            ResourceQuotaStatus with usage vs. limits, or None if no quota defined.
        """
        quota = self._agent_quotas.get(agent_id)
        if not quota or not quota.enabled:
            return None

        instance = self._instances.get(agent_id)
        usage: dict[ResourceType, float] = {}
        if instance:
            usage = {
                ResourceType.CPU: instance.cpu_usage_percent,
                ResourceType.MEMORY: instance.memory_usage_mb,
                ResourceType.CONCURRENT_SESSIONS: float(instance.active_sessions),
                ResourceType.API_CALLS: float(instance.total_requests),
                ResourceType.TOKENS: instance.metadata.get("tokens_used", 0.0),
            }

        status = ResourceQuotaStatus(
            agent_id=agent_id,
            usage=usage,
            quota=quota,
        )

        violations: list[str] = []
        for resource_type, current_value in usage.items():
            resource_limits = quota.limits.get(resource_type, {})
            soft_limit = resource_limits.get("soft")
            hard_limit = resource_limits.get("hard")

            if hard_limit is not None and current_value > hard_limit:
                status.within_hard_limits = False
                violations.append(
                    f"{resource_type.value}: {current_value} > hard limit {hard_limit}"
                )
            if soft_limit is not None and current_value > soft_limit:
                status.within_soft_limits = False
                violations.append(
                    f"{resource_type.value}: {current_value} > soft limit {soft_limit}"
                )

        status.violations = violations
        return status

    def enforce_quotas(
        self,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Enforce per-agent resource quotas across the platform.

        For agents exceeding hard limits, generates a CRITICAL alert.
        For agents exceeding soft limits, generates a WARNING alert.
        Agents exceeding hard limits will have their state set to PAUSED.

        Args:
            agent_id: Specific agent to enforce quotas for. If None, enforces
                      quotas for all agents with defined quotas.

        Returns:
            Dict with enforcement results: agents_checked, soft_violations,
            hard_violations, alerts_generated.
        """
        result: dict[str, Any] = {
            "agents_checked": 0,
            "soft_violations": 0,
            "hard_violations": 0,
            "alerts_generated": 0,
            "details": [],
        }

        target_agents = [agent_id] if agent_id else list(self._agent_quotas.keys())

        for aid in target_agents:
            status = self.check_quota(aid)
            if status is None:
                continue

            result["agents_checked"] += 1
            detail = {
                "agent_id": aid,
                "within_soft_limits": status.within_soft_limits,
                "within_hard_limits": status.within_hard_limits,
                "violations": status.violations,
            }

            if not status.within_hard_limits:
                result["hard_violations"] += 1
                detail["action"] = "paused"
                # Pause the agent instance
                if aid in self._instances:
                    self._instances[aid].state = RuntimeState.PAUSED
                # Generate critical alert
                self.create_alert(
                    severity=AlertSeverity.CRITICAL,
                    component="quota_enforcer",
                    message=f"Agent {aid} exceeded hard resource limits",
                    details="; ".join(status.violations),
                )
                result["alerts_generated"] += 1
            elif not status.within_soft_limits:
                result["soft_violations"] += 1
                detail["action"] = "warning"
                # Generate warning alert
                self.create_alert(
                    severity=AlertSeverity.WARNING,
                    component="quota_enforcer",
                    message=f"Agent {aid} exceeded soft resource limits",
                    details="; ".join(status.violations),
                )
                result["alerts_generated"] += 1
            else:
                detail["action"] = "none"

            result["details"].append(detail)

        logger.info(
            f"Quota enforcement: {result['agents_checked']} checked, "
            f"{result['soft_violations']} soft, {result['hard_violations']} hard"
        )
        return result

    def list_all_quota_statuses(self) -> list[ResourceQuotaStatus]:
        """Get quota status for all agents with defined quotas."""
        statuses: list[ResourceQuotaStatus] = []
        for agent_id in self._agent_quotas:
            status = self.check_quota(agent_id)
            if status:
                statuses.append(status)
        return statuses

    # ── Platform Event Bus ────────────────────────────────

    def publish_event(
        self,
        category: EventCategory,
        event_type: str,
        data: dict[str, Any] | None = None,
        source: str = "platform",
        target_agent_ids: list[str] | None = None,
        target_fleet_ids: list[str] | None = None,
        priority: int = 5,
        ttl_seconds: float | None = None,
    ) -> PlatformEvent:
        """Publish a platform-level event to the event bus.

        Args:
            category: Event category (lifecycle, health, deployment, etc.).
            event_type: Specific event type string.
            data: Event payload data.
            source: Origin of the event.
            target_agent_ids: Specific agent IDs to target (empty = all).
            target_fleet_ids: Specific fleet IDs to target (empty = all).
            priority: Event priority (1=highest, 10=lowest).
            ttl_seconds: Optional time-to-live in seconds.

        Returns:
            The published PlatformEvent.
        """
        event = PlatformEvent(
            category=category,
            event_type=event_type,
            data=data or {},
            source=source,
            target_agent_ids=target_agent_ids or [],
            target_fleet_ids=target_fleet_ids or [],
            priority=priority,
            ttl_seconds=ttl_seconds,
        )
        self._event_bus.append(event)
        logger.debug(f"Event published: [{category.value}] {event_type} (priority={priority})")
        return event

    def broadcast_event(
        self,
        category: EventCategory,
        event_type: str,
        data: dict[str, Any] | None = None,
        source: str = "platform",
        priority: int = 5,
    ) -> PlatformEvent:
        """Broadcast a platform-level event to all agents without filtering.

        This is a convenience wrapper around publish_event that targets all
        agents and all fleets by default.

        Args:
            category: Event category.
            event_type: Specific event type string.
            data: Event payload data.
            source: Origin of the event.
            priority: Event priority (1=highest, 10=lowest).

        Returns:
            The published PlatformEvent.
        """
        return self.publish_event(
            category=category,
            event_type=event_type,
            data=data,
            source=source,
            target_agent_ids=[],
            target_fleet_ids=[],
            priority=priority,
        )

    def subscribe_to_events(
        self,
        subscriber_id: str,
        categories: list[EventCategory] | None = None,
        event_types: list[str] | None = None,
        callback: Callable[[PlatformEvent], None] | None = None,
    ) -> str:
        """Subscribe to platform events with optional filtering.

        Args:
            subscriber_id: Unique ID for the subscriber (typically an agent ID).
            categories: Filter by event categories. None = all categories.
            event_types: Filter by specific event types. None = all types.
            callback: Optional callback function invoked when matching events
                      are published. If not provided, events must be polled.

        Returns:
            The subscription ID.
        """
        subscription_id = f"sub-{uuid.uuid4().hex[:8]}"
        subscription = {
            "subscription_id": subscription_id,
            "subscriber_id": subscriber_id,
            "categories": categories,
            "event_types": event_types,
            "callback": callback,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if subscriber_id not in self._event_subscriptions:
            self._event_subscriptions[subscriber_id] = []
        self._event_subscriptions[subscriber_id].append(subscription)

        logger.info(f"Event subscription created: {subscription_id} for {subscriber_id}")
        return subscription_id

    def unsubscribe_from_events(self, subscription_id: str) -> bool:
        """Remove an event subscription.

        Args:
            subscription_id: The subscription ID to remove.

        Returns:
            True if the subscription was found and removed.
        """
        for subscriber_id, subs in list(self._event_subscriptions.items()):
            for sub in subs:
                if sub["subscription_id"] == subscription_id:
                    subs.remove(sub)
                    if not subs:
                        del self._event_subscriptions[subscriber_id]
                    logger.info(f"Event subscription removed: {subscription_id}")
                    return True
        return False

    def get_events(
        self,
        categories: list[EventCategory] | None = None,
        event_types: list[str] | None = None,
        agent_id: str | None = None,
        fleet_id: str | None = None,
        limit: int = 50,
        include_expired: bool = False,
    ) -> list[PlatformEvent]:
        """Get platform events with optional filtering.

        Args:
            categories: Filter by event categories.
            event_types: Filter by specific event types.
            agent_id: Filter events targeting this agent.
            fleet_id: Filter events targeting this fleet.
            limit: Maximum number of events to return.
            include_expired: Whether to include expired events.

        Returns:
            List of matching PlatformEvent objects.
        """
        events = self._event_bus

        if not include_expired:
            events = [e for e in events if not e.is_expired()]

        matching = []
        for event in events:
            if event.matches_filter(
                categories=categories,
                event_types=event_types,
                agent_id=agent_id,
                fleet_id=fleet_id,
            ):
                matching.append(event)

        # Sort by priority (lowest number first) then by timestamp (newest first)
        matching.sort(key=lambda e: (e.priority, e.timestamp), reverse=False)
        matching.sort(key=lambda e: e.timestamp, reverse=True)

        return matching[:limit]

    def poll_events(
        self,
        agent_id: str,
        categories: list[EventCategory] | None = None,
        event_types: list[str] | None = None,
        limit: int = 20,
    ) -> list[PlatformEvent]:
        """Poll for events relevant to a specific agent.

        Convenience method that gets events targeting the agent and also
        invokes any registered callbacks for matching subscriptions.

        Args:
            agent_id: The agent ID to poll events for.
            categories: Optional category filter.
            event_types: Optional event type filter.
            limit: Maximum number of events to return.

        Returns:
            List of matching PlatformEvent objects.
        """
        events = self.get_events(
            categories=categories,
            event_types=event_types,
            agent_id=agent_id,
            limit=limit,
        )

        # Invoke callbacks for matching subscriptions
        if agent_id in self._event_subscriptions:
            for sub in self._event_subscriptions[agent_id]:
                callback = sub.get("callback")
                if callback:
                    sub_categories = sub.get("categories")
                    sub_types = sub.get("event_types")
                    for event in events:
                        if event.matches_filter(
                            categories=sub_categories,
                            event_types=sub_types,
                        ):
                            try:
                                callback(event)
                            except Exception as e:
                                logger.error(f"Event callback error for {agent_id}: {e}")

        return events

    def purge_expired_events(self) -> int:
        """Remove all expired events from the event bus.

        Returns:
            Number of events purged.
        """
        before = len(self._event_bus)
        self._event_bus = [e for e in self._event_bus if not e.is_expired()]
        purged = before - len(self._event_bus)
        if purged > 0:
            logger.info(f"Purged {purged} expired events from event bus")
        return purged


# ── Singleton ─────────────────────────────────────────────

platform_core = PlatformCore()