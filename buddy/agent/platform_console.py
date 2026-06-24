"""Buddy Platform Console — AI-Native Platform Administration Console

Comprehensive administration console for the Buddy platform providing:
- System-wide health monitoring and diagnostics
- Agent fleet management and orchestration
- Resource allocation and quota management
- Usage analytics and cost tracking
- Configuration management and hot-reloading
- Alert management and notification routing
- Audit log aggregation and search
- Performance benchmarking and optimization
- Feature flag management
- Backup and recovery coordination

Operates in simulation mode by default, generating realistic system health
data and pre-populated feature flags for development and testing.
"""
from __future__ import annotations

import logging
import uuid
import time
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.platform_console")

# ══════════════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════════════


class ConsoleAlert(str, Enum):
    """Alert severity levels for the platform console."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemComponent(str, Enum):
    """Platform system components that can be monitored and managed."""
    AGENT_ENGINE = "agent_engine"
    MEMORY = "memory"
    API_GATEWAY = "api_gateway"
    TOOL_EXECUTOR = "tool_executor"
    KNOWLEDGE_FABRIC = "knowledge_fabric"
    SWARM = "swarm"
    WORKSPACE = "workspace"
    PIPELINE = "pipeline"
    RUNTIME = "runtime"
    DATABASE = "database"


class HealthStatus(str, Enum):
    """Health status for system components and overall platform."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


# ══════════════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════════════


@dataclass
class ComponentHealth:
    """Health snapshot for a single system component."""
    component: SystemComponent
    status: HealthStatus = HealthStatus.HEALTHY
    message: str = ""
    latency_ms: float = 0.0
    error_count: int = 0
    last_checked: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "error_count": self.error_count,
            "last_checked": self.last_checked,
            "metrics": self.metrics,
        }


@dataclass
class SystemHealth:
    """Comprehensive system-wide health report."""
    overall_status: HealthStatus = HealthStatus.HEALTHY
    components: dict[str, ComponentHealth] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    uptime_seconds: float = 0.0
    active_agents: int = 0
    total_requests: int = 0
    error_rate: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "alerts": self.alerts[:20],
            "uptime_seconds": round(self.uptime_seconds, 1),
            "active_agents": self.active_agents,
            "total_requests": self.total_requests,
            "error_rate": round(self.error_rate, 4),
            "generated_at": self.generated_at,
        }


@dataclass
class ResourceSnapshot:
    """Current resource usage snapshot across the platform."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    active_connections: int = 0
    queue_depth: int = 0
    token_usage: int = 0
    snapshot_id: str = field(default_factory=lambda: f"rsnap-{uuid.uuid4().hex[:8]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_percent": round(self.memory_percent, 2),
            "disk_percent": round(self.disk_percent, 2),
            "active_connections": self.active_connections,
            "queue_depth": self.queue_depth,
            "token_usage": self.token_usage,
            "timestamp": self.timestamp,
        }


@dataclass
class FeatureFlag:
    """A feature flag controlling platform capabilities."""
    flag_id: str = field(default_factory=lambda: f"ff-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    enabled: bool = False
    rollout_percentage: int = 0
    target_agents: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "flag_id": self.flag_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "rollout_percentage": self.rollout_percentage,
            "target_agents": self.target_agents,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AuditEntry:
    """A single audit log entry recording an action or event."""
    entry_id: str = field(default_factory=lambda: f"audit-{uuid.uuid4().hex[:8]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    component: SystemComponent = SystemComponent.AGENT_ENGINE
    action: str = ""
    agent_id: str = ""
    detail: str = ""
    severity: ConsoleAlert = ConsoleAlert.INFO
    ip_address: str = "127.0.0.1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "component": self.component.value,
            "action": self.action,
            "agent_id": self.agent_id,
            "detail": self.detail,
            "severity": self.severity.value,
            "ip_address": self.ip_address,
        }


# ══════════════════════════════════════════════════════════════════════
# Pre-populated Feature Flags
# ══════════════════════════════════════════════════════════════════════

_DEFAULT_FEATURE_FLAGS: list[dict[str, Any]] = [
    {
        "name": "auto_evolution",
        "description": "Enable automatic agent evolution and self-improvement",
        "enabled": False,
        "rollout_percentage": 5,
    },
    {
        "name": "deep_reasoning",
        "description": "Enable deep multi-step reasoning for complex tasks",
        "enabled": True,
        "rollout_percentage": 80,
    },
    {
        "name": "collaborative_intelligence",
        "description": "Enable inter-agent collaboration and knowledge sharing",
        "enabled": True,
        "rollout_percentage": 60,
    },
    {
        "name": "streaming_responses",
        "description": "Enable streaming response output for real-time feedback",
        "enabled": True,
        "rollout_percentage": 100,
    },
    {
        "name": "experimental_tools",
        "description": "Enable experimental and beta tool integrations",
        "enabled": False,
        "rollout_percentage": 10,
    },
    {
        "name": "semantic_cache",
        "description": "Enable semantic caching for repeated queries",
        "enabled": True,
        "rollout_percentage": 90,
    },
    {
        "name": "auto_approval",
        "description": "Enable automatic approval for low-risk operations",
        "enabled": True,
        "rollout_percentage": 50,
    },
    {
        "name": "cost_optimization",
        "description": "Enable automatic model tier selection for cost savings",
        "enabled": True,
        "rollout_percentage": 100,
    },
    {
        "name": "workspace_isolation",
        "description": "Enable strict workspace isolation per agent session",
        "enabled": True,
        "rollout_percentage": 100,
    },
    {
        "name": "telemetry_export",
        "description": "Enable telemetry data export to external observability platforms",
        "enabled": False,
        "rollout_percentage": 0,
    },
    {
        "name": "dark_mode",
        "description": "Enable dark mode UI for the platform console",
        "enabled": True,
        "rollout_percentage": 70,
    },
    {
        "name": "knowledge_graph",
        "description": "Enable knowledge graph-based memory retrieval",
        "enabled": True,
        "rollout_percentage": 40,
    },
]

# ══════════════════════════════════════════════════════════════════════
# Mock Audit Log Templates
# ══════════════════════════════════════════════════════════════════════

_MOCK_AUDIT_ACTIONS: list[dict[str, Any]] = [
    {"component": SystemComponent.AGENT_ENGINE, "action": "agent.created", "detail": "New agent instance registered"},
    {"component": SystemComponent.AGENT_ENGINE, "action": "agent.stopped", "detail": "Agent instance stopped gracefully"},
    {"component": SystemComponent.AGENT_ENGINE, "action": "agent.restarted", "detail": "Agent instance restarted after error"},
    {"component": SystemComponent.MEMORY, "action": "memory.consolidated", "detail": "Memory consolidation completed"},
    {"component": SystemComponent.MEMORY, "action": "memory.pruned", "detail": "Old memory entries pruned"},
    {"component": SystemComponent.API_GATEWAY, "action": "gateway.rate_limited", "detail": "Rate limit applied to incoming request"},
    {"component": SystemComponent.API_GATEWAY, "action": "gateway.route_updated", "detail": "API route configuration updated"},
    {"component": SystemComponent.TOOL_EXECUTOR, "action": "tool.executed", "detail": "Tool execution completed successfully"},
    {"component": SystemComponent.TOOL_EXECUTOR, "action": "tool.registered", "detail": "New tool registered in executor"},
    {"component": SystemComponent.KNOWLEDGE_FABRIC, "action": "fabric.indexed", "detail": "Knowledge fabric index rebuilt"},
    {"component": SystemComponent.SWARM, "action": "swarm.formed", "detail": "New agent swarm formed"},
    {"component": SystemComponent.SWARM, "action": "swarm.disbanded", "detail": "Agent swarm disbanded"},
    {"component": SystemComponent.WORKSPACE, "action": "workspace.created", "detail": "New workspace provisioned"},
    {"component": SystemComponent.WORKSPACE, "action": "workspace.cleaned", "detail": "Workspace cleanup completed"},
    {"component": SystemComponent.PIPELINE, "action": "pipeline.started", "detail": "Pipeline execution started"},
    {"component": SystemComponent.PIPELINE, "action": "pipeline.completed", "detail": "Pipeline execution completed successfully"},
    {"component": SystemComponent.RUNTIME, "action": "runtime.scaled", "detail": "Runtime auto-scaled based on load"},
    {"component": SystemComponent.DATABASE, "action": "database.backup", "detail": "Database backup completed"},
    {"component": SystemComponent.DATABASE, "action": "database.migrated", "detail": "Database schema migration applied"},
    {"component": SystemComponent.AGENT_ENGINE, "action": "config.updated", "detail": "Configuration hot-reloaded"},
    {"component": SystemComponent.AGENT_ENGINE, "action": "feature_flag.toggled", "detail": "Feature flag toggled"},
    {"component": SystemComponent.RUNTIME, "action": "runtime.health_check", "detail": "Health check passed"},
    {"component": SystemComponent.API_GATEWAY, "action": "gateway.auth_failed", "detail": "Authentication attempt failed"},
    {"component": SystemComponent.TOOL_EXECUTOR, "action": "tool.timeout", "detail": "Tool execution timed out"},
]

# ══════════════════════════════════════════════════════════════════════
# Platform Console
# ══════════════════════════════════════════════════════════════════════


class PlatformConsole:
    """AI-native administration console for the Buddy platform.

    Provides a unified interface for monitoring, managing, and optimizing
    all platform components. Operates in simulation mode, generating
    realistic data for development and testing environments.

    Capabilities:
    - System-wide health monitoring and diagnostics
    - Agent fleet management and orchestration
    - Resource allocation and quota management
    - Usage analytics and cost tracking
    - Configuration management and hot-reloading
    - Alert management and notification routing
    - Audit log aggregation and search
    - Performance benchmarking and optimization
    - Feature flag management
    - Backup and recovery coordination
    """

    def __init__(self):
        self._start_time: float = time.time()
        self._total_requests: int = 0
        self._total_errors: int = 0
        self._active_agents: int = 0

        # Feature flags
        self._feature_flags: dict[str, FeatureFlag] = {}
        self._init_feature_flags()

        # Audit log
        self._audit_log: list[AuditEntry] = []
        self._init_audit_log()

        # Alert store
        self._alerts: list[dict[str, Any]] = []
        self._init_alerts()

        # Component health tracking
        self._component_health: dict[str, ComponentHealth] = {}
        self._init_component_health()

        # Configuration
        self._config: dict[str, Any] = {}
        self._init_config()

        # Resource tracking
        self._resource_history: list[ResourceSnapshot] = []

        # Agent fleet tracking
        self._agent_fleet: dict[str, dict[str, Any]] = {}
        self._init_agent_fleet()

        logger.info("PlatformConsole initialized (simulation mode)")

    # ── Initialization ─────────────────────────────────────

    def _init_feature_flags(self):
        """Pre-populate feature flags with common settings."""
        for flag_data in _DEFAULT_FEATURE_FLAGS:
            flag = FeatureFlag(
                name=flag_data["name"],
                description=flag_data["description"],
                enabled=flag_data["enabled"],
                rollout_percentage=flag_data["rollout_percentage"],
            )
            self._feature_flags[flag.flag_id] = flag

    def _init_audit_log(self):
        """Generate mock audit log entries for simulation mode."""
        base_time = datetime.now(timezone.utc) - timedelta(hours=24)
        mock_agent_ids = [f"agent-{uuid.uuid4().hex[:6]}" for _ in range(8)]
        mock_ips = [
            "192.168.1.101", "192.168.1.102", "10.0.0.5",
            "10.0.0.8", "172.16.0.12", "172.16.0.20",
        ]

        for i in range(80):
            template = random.choice(_MOCK_AUDIT_ACTIONS)
            entry_time = base_time + timedelta(
                seconds=random.randint(0, 86400)
            )
            entry = AuditEntry(
                timestamp=entry_time.isoformat(),
                component=template["component"],
                action=template["action"],
                agent_id=random.choice(mock_agent_ids) if random.random() > 0.2 else "",
                detail=template["detail"],
                severity=ConsoleAlert.INFO if random.random() > 0.15 else random.choice(
                    [ConsoleAlert.WARNING, ConsoleAlert.ERROR]
                ),
                ip_address=random.choice(mock_ips),
            )
            self._audit_log.append(entry)

        self._audit_log.sort(key=lambda e: e.timestamp)

    def _init_alerts(self):
        """Pre-populate with a few simulated alerts."""
        self._alerts = [
            {
                "alert_id": f"alert-{uuid.uuid4().hex[:8]}",
                "severity": ConsoleAlert.WARNING.value,
                "component": SystemComponent.API_GATEWAY.value,
                "message": "API gateway latency above threshold (320ms)",
                "created_at": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
                "acknowledged": False,
            },
            {
                "alert_id": f"alert-{uuid.uuid4().hex[:8]}",
                "severity": ConsoleAlert.INFO.value,
                "component": SystemComponent.DATABASE.value,
                "message": "Database backup completed successfully",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                "acknowledged": True,
            },
            {
                "alert_id": f"alert-{uuid.uuid4().hex[:8]}",
                "severity": ConsoleAlert.ERROR.value,
                "component": SystemComponent.TOOL_EXECUTOR.value,
                "message": "Tool executor experiencing elevated error rate (8.5%)",
                "created_at": (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat(),
                "acknowledged": False,
            },
        ]

    def _init_component_health(self):
        """Initialize component health tracking with simulated data."""
        for component in SystemComponent:
            # Simulate varied health statuses
            roll = random.random()
            if roll < 0.75:
                status = HealthStatus.HEALTHY
                latency = random.uniform(5, 80)
            elif roll < 0.92:
                status = HealthStatus.DEGRADED
                latency = random.uniform(80, 300)
            else:
                status = HealthStatus.UNHEALTHY
                latency = random.uniform(300, 800)

            health = ComponentHealth(
                component=component,
                status=status,
                message=f"{component.value} operating normally" if status == HealthStatus.HEALTHY else f"{component.value} experiencing issues",
                latency_ms=round(latency, 2),
                error_count=random.randint(0, 5) if status != HealthStatus.HEALTHY else 0,
                metrics={
                    "throughput_rps": round(random.uniform(10, 500), 1),
                    "success_rate": round(random.uniform(0.92, 1.0), 3),
                    "p99_latency_ms": round(latency * random.uniform(1.5, 4.0), 2),
                },
            )
            self._component_health[component.value] = health

    def _init_config(self):
        """Initialize default platform configuration."""
        self._config = {
            "max_agents": 100,
            "max_concurrent_sessions": 500,
            "default_model": "gpt-4o",
            "fallback_model": "gpt-4o-mini",
            "log_level": "INFO",
            "health_check_interval_seconds": 30,
            "resource_monitor_interval_seconds": 15,
            "auto_scaling_enabled": True,
            "telemetry_enabled": True,
            "audit_log_retention_days": 90,
            "max_tool_timeout_seconds": 120,
            "backup_schedule": "0 2 * * *",
            "alert_routing": {
                "info": ["log"],
                "warning": ["log", "dashboard"],
                "error": ["log", "dashboard", "email"],
                "critical": ["log", "dashboard", "email", "pager"],
            },
        }

    def _init_agent_fleet(self):
        """Initialize simulated agent fleet data."""
        agent_roles = ["reasoning", "coding", "browser", "data_analysis", "planning", "review"]
        for i in range(12):
            agent_id = f"agent-{uuid.uuid4().hex[:6]}"
            self._agent_fleet[agent_id] = {
                "agent_id": agent_id,
                "agent_name": f"agent-{agent_roles[i % len(agent_roles)]}-{i + 1}",
                "role": agent_roles[i % len(agent_roles)],
                "status": random.choice(["online", "online", "online", "busy", "idle"]),
                "uptime_seconds": random.uniform(3600, 86400 * 3),
                "active_sessions": random.randint(0, 5),
                "total_requests": random.randint(100, 5000),
                "error_count": random.randint(0, 15),
                "cpu_percent": round(random.uniform(5, 65), 1),
                "memory_mb": round(random.uniform(128, 1024), 1),
                "last_heartbeat": (datetime.now(timezone.utc) - timedelta(seconds=random.randint(5, 60))).isoformat(),
            }
        self._active_agents = sum(
            1 for a in self._agent_fleet.values()
            if a["status"] in ("online", "busy", "idle")
        )
        self._total_requests = sum(a["total_requests"] for a in self._agent_fleet.values())
        self._total_errors = sum(a["error_count"] for a in self._agent_fleet.values())

    # ── Health Monitoring ──────────────────────────────────

    async def get_system_health(self) -> SystemHealth:
        """Get a comprehensive system-wide health report.

        Returns a SystemHealth dataclass containing overall platform status,
        per-component health details, active alerts, and key metrics.
        """
        # Refresh component health with slight variations
        for component in SystemComponent:
            health = self._component_health[component.value]
            health.latency_ms += random.uniform(-5, 5)
            health.latency_ms = max(1, health.latency_ms)
            health.last_checked = datetime.now(timezone.utc).isoformat()
            health.metrics["throughput_rps"] = round(
                health.metrics.get("throughput_rps", 100) + random.uniform(-20, 20), 1
            )
            if health.error_count > 0 and random.random() < 0.3:
                health.error_count = max(0, health.error_count - 1)

        # Determine overall status
        statuses = [h.status for h in self._component_health.values()]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif HealthStatus.OFFLINE in statuses:
            overall = HealthStatus.OFFLINE
        else:
            overall = HealthStatus.HEALTHY

        total_req = self._total_requests
        total_err = self._total_errors
        error_rate = total_err / max(total_req, 1)

        return SystemHealth(
            overall_status=overall,
            components={k: v for k, v in self._component_health.items()},
            alerts=[a for a in self._alerts if not a.get("acknowledged", True)],
            uptime_seconds=round(time.time() - self._start_time, 1),
            active_agents=self._active_agents,
            total_requests=total_req,
            error_rate=round(error_rate, 4),
        )

    async def get_component_status(self, component: SystemComponent) -> ComponentHealth:
        """Get the current health status of a specific system component.

        Args:
            component: The SystemComponent to query.

        Returns:
            ComponentHealth dataclass with current status and metrics.
        """
        health = self._component_health.get(component.value)
        if health is None:
            health = ComponentHealth(
                component=component,
                status=HealthStatus.OFFLINE,
                message=f"Component {component.value} not found",
            )
        health.last_checked = datetime.now(timezone.utc).isoformat()
        return health

    async def run_diagnostics(self) -> dict[str, Any]:
        """Run a full system diagnostics sweep across all components.

        Checks each component's health, latency, error rates, and generates
        a consolidated diagnostic report with recommendations.

        Returns:
            Dict with diagnostic results, per-component details, and
            recommendations for any issues found.
        """
        results: dict[str, Any] = {
            "diagnostic_id": f"diag-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {},
            "overall_health": HealthStatus.HEALTHY.value,
            "recommendations": [],
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
        }

        for component in SystemComponent:
            health = self._component_health[component.value]
            health.last_checked = datetime.now(timezone.utc).isoformat()
            health.latency_ms += random.uniform(-3, 3)

            check_result = {
                "component": component.value,
                "status": health.status.value,
                "latency_ms": round(health.latency_ms, 2),
                "error_count": health.error_count,
                "checks": {
                    "connectivity": health.status != HealthStatus.OFFLINE,
                    "latency_ok": health.latency_ms < 200,
                    "error_rate_ok": health.error_count < 10,
                },
            }

            results["total_checks"] += 1
            all_checks_ok = all(check_result["checks"].values())
            if all_checks_ok:
                results["passed"] += 1
            elif health.status == HealthStatus.UNHEALTHY:
                results["failed"] += 1
                results["recommendations"].append(
                    f"[{component.value}] Action required: {health.message}"
                )
            else:
                results["warnings"] += 1
                results["recommendations"].append(
                    f"[{component.value}] Monitor closely: {health.message}"
                )

            results["components"][component.value] = check_result

        # Determine overall health
        if results["failed"] > 0:
            results["overall_health"] = HealthStatus.UNHEALTHY.value
        elif results["warnings"] > 0:
            results["overall_health"] = HealthStatus.DEGRADED.value
        else:
            results["overall_health"] = HealthStatus.HEALTHY.value

        logger.info(
            f"Diagnostics complete: {results['passed']} passed, "
            f"{results['warnings']} warnings, {results['failed']} failed"
        )
        return results

    # ── Resource Management ────────────────────────────────

    async def get_resource_snapshot(self) -> ResourceSnapshot:
        """Get a snapshot of current platform resource usage.

        Returns a ResourceSnapshot with CPU, memory, disk, connection,
        queue depth, and token usage metrics.
        """
        snapshot = ResourceSnapshot(
            cpu_percent=round(random.uniform(15, 75), 2),
            memory_percent=round(random.uniform(30, 80), 2),
            disk_percent=round(random.uniform(20, 60), 2),
            active_connections=random.randint(50, 300),
            queue_depth=random.randint(0, 25),
            token_usage=random.randint(50000, 2000000),
        )
        self._resource_history.append(snapshot)
        if len(self._resource_history) > 200:
            self._resource_history = self._resource_history[-100:]
        return snapshot

    async def optimize_resources(self) -> dict[str, Any]:
        """Analyze resource usage and suggest optimizations.

        Evaluates current resource utilization patterns and generates
        actionable recommendations for reducing costs and improving
        performance.

        Returns:
            Dict with optimization suggestions, potential savings,
            and resource reallocation proposals.
        """
        snapshot = await self.get_resource_snapshot()

        suggestions: list[dict[str, Any]] = []
        potential_savings: list[dict[str, Any]] = []

        if snapshot.cpu_percent > 70:
            suggestions.append({
                "type": "scale_up",
                "target": "cpu",
                "current": snapshot.cpu_percent,
                "recommendation": "Consider scaling up CPU resources or distributing load",
                "priority": "high",
            })
        elif snapshot.cpu_percent < 25:
            suggestions.append({
                "type": "scale_down",
                "target": "cpu",
                "current": snapshot.cpu_percent,
                "recommendation": "CPU underutilized; consider reducing allocated cores",
                "priority": "low",
            })
            potential_savings.append({
                "resource": "cpu",
                "estimated_monthly_savings_usd": round(random.uniform(15, 50), 2),
            })

        if snapshot.memory_percent > 80:
            suggestions.append({
                "type": "increase",
                "target": "memory",
                "current": snapshot.memory_percent,
                "recommendation": "Memory usage critical; increase allocation or enable swap",
                "priority": "high",
            })
        elif snapshot.memory_percent < 35:
            suggestions.append({
                "type": "decrease",
                "target": "memory",
                "current": snapshot.memory_percent,
                "recommendation": "Memory over-provisioned; consider reducing allocation",
                "priority": "low",
            })
            potential_savings.append({
                "resource": "memory",
                "estimated_monthly_savings_usd": round(random.uniform(10, 40), 2),
            })

        if snapshot.queue_depth > 15:
            suggestions.append({
                "type": "bottleneck",
                "target": "queue",
                "current": snapshot.queue_depth,
                "recommendation": "Queue depth elevated; increase worker count or optimize processing",
                "priority": "medium",
            })

        if snapshot.token_usage > 1500000:
            suggestions.append({
                "type": "cost_optimization",
                "target": "tokens",
                "current": snapshot.token_usage,
                "recommendation": "High token usage detected; review model tier selection and caching",
                "priority": "medium",
            })
            potential_savings.append({
                "resource": "tokens",
                "estimated_monthly_savings_usd": round(random.uniform(30, 200), 2),
            })

        total_potential_savings = round(
            sum(s["estimated_monthly_savings_usd"] for s in potential_savings), 2
        )

        logger.info(f"Resource optimization: {len(suggestions)} suggestions, "
                     f"${total_potential_savings} potential monthly savings")

        return {
            "timestamp": snapshot.timestamp,
            "current_snapshot": snapshot.to_dict(),
            "suggestions": suggestions,
            "potential_savings": potential_savings,
            "total_potential_monthly_savings_usd": total_potential_savings,
            "idle_resources_detected": len(potential_savings) > 0,
        }

    # ── Usage Analytics and Cost Tracking ──────────────────

    async def get_usage_analytics(self, time_range: str = "24h") -> dict[str, Any]:
        """Get platform usage statistics for a given time range.

        Args:
            time_range: Time range for analytics. One of "1h", "6h", "24h",
                        "7d", "30d".

        Returns:
            Dict with usage metrics including request counts, token usage,
            active sessions, error rates, and per-component breakdown.
        """
        time_multipliers = {
            "1h": 1,
            "6h": 6,
            "24h": 24,
            "7d": 168,
            "30d": 720,
        }
        multiplier = time_multipliers.get(time_range, 24)

        total_requests = int(self._total_requests * (multiplier / 24))
        total_errors = int(self._total_errors * (multiplier / 24))
        total_tokens = int(random.uniform(100000, 5000000) * (multiplier / 24))
        avg_latency = round(random.uniform(45, 180), 2)

        # Per-component breakdown
        component_usage: dict[str, dict[str, Any]] = {}
        for component in SystemComponent:
            component_usage[component.value] = {
                "requests": random.randint(50, 5000) * int(multiplier / 24 + 1),
                "avg_latency_ms": round(random.uniform(10, 250), 2),
                "error_count": random.randint(0, 20) * int(multiplier / 24 + 1),
                "tokens_consumed": random.randint(1000, 200000) * int(multiplier / 24 + 1),
            }

        # Model tier distribution
        model_usage = {
            "premium": {"requests": int(total_requests * 0.15), "tokens": int(total_tokens * 0.10)},
            "standard": {"requests": int(total_requests * 0.45), "tokens": int(total_tokens * 0.50)},
            "light": {"requests": int(total_requests * 0.40), "tokens": int(total_tokens * 0.40)},
        }

        error_rate = total_errors / max(total_requests, 1)

        return {
            "time_range": time_range,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": round(error_rate, 4),
                "total_tokens": total_tokens,
                "avg_latency_ms": avg_latency,
                "unique_agents": self._active_agents,
                "active_sessions": sum(
                    a["active_sessions"] for a in self._agent_fleet.values()
                ),
            },
            "by_component": component_usage,
            "by_model_tier": model_usage,
        }

    async def get_cost_breakdown(self, time_range: str = "24h") -> dict[str, Any]:
        """Get detailed cost analysis for the specified time range.

        Args:
            time_range: Time range for cost analysis. One of "1h", "6h",
                        "24h", "7d", "30d".

        Returns:
            Dict with cost breakdown by model tier, component, and agent,
            along with daily run rate and projected monthly costs.
        """
        time_multipliers = {
            "1h": 1 / 24,
            "6h": 0.25,
            "24h": 1,
            "7d": 7,
            "30d": 30,
        }
        multiplier = time_multipliers.get(time_range, 1)

        # Simulated pricing: premium $0.01/1K, standard $0.003/1K, light $0.0005/1K
        premium_tokens = int(random.uniform(50000, 300000) * multiplier)
        standard_tokens = int(random.uniform(200000, 800000) * multiplier)
        light_tokens = int(random.uniform(100000, 500000) * multiplier)

        premium_cost = premium_tokens * 0.01 / 1000
        standard_cost = standard_tokens * 0.003 / 1000
        light_cost = light_tokens * 0.0005 / 1000

        total_tokens = premium_tokens + standard_tokens + light_tokens
        total_cost = round(premium_cost + standard_cost + light_cost, 2)

        # Per-component costs
        component_costs: dict[str, dict[str, Any]] = {}
        for component in SystemComponent:
            comp_tokens = int(random.uniform(10000, 200000) * multiplier)
            comp_cost = round(comp_tokens * random.uniform(0.0005, 0.008) / 1000, 2)
            component_costs[component.value] = {
                "tokens": comp_tokens,
                "cost_usd": comp_cost,
            }

        # Per-agent costs
        agent_costs: list[dict[str, Any]] = []
        for agent_id, agent in list(self._agent_fleet.items())[:8]:
            agent_tokens = int(random.uniform(5000, 100000) * multiplier)
            agent_cost = round(agent_tokens * random.uniform(0.001, 0.005) / 1000, 2)
            agent_costs.append({
                "agent_id": agent_id,
                "agent_name": agent["agent_name"],
                "tokens": agent_tokens,
                "cost_usd": agent_cost,
            })
        agent_costs.sort(key=lambda a: a["cost_usd"], reverse=True)

        daily_run_rate = round(total_cost / max(multiplier, 1), 2)
        projected_monthly = round(daily_run_rate * 30, 2)

        return {
            "time_range": time_range,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_cost_usd": total_cost,
                "total_tokens": total_tokens,
                "daily_run_rate_usd": daily_run_rate,
                "projected_monthly_cost_usd": projected_monthly,
            },
            "by_model_tier": {
                "premium": {"tokens": premium_tokens, "cost_usd": round(premium_cost, 2)},
                "standard": {"tokens": standard_tokens, "cost_usd": round(standard_cost, 2)},
                "light": {"tokens": light_tokens, "cost_usd": round(light_cost, 2)},
            },
            "by_component": component_costs,
            "by_agent": agent_costs,
        }

    # ── Feature Flag Management ────────────────────────────

    async def get_feature_flags(self) -> list[dict[str, Any]]:
        """List all feature flags with their current state.

        Returns:
            List of feature flag dictionaries with id, name, description,
            enabled status, rollout percentage, and target agents.
        """
        return [flag.to_dict() for flag in self._feature_flags.values()]

    async def set_feature_flag(
        self,
        flag_id: str,
        enabled: bool | None = None,
        rollout_percentage: int | None = None,
    ) -> dict[str, Any]:
        """Update a feature flag's enabled state or rollout percentage.

        Args:
            flag_id: The ID of the feature flag to update.
            enabled: Whether to enable or disable the flag.
            rollout_percentage: New rollout percentage (0-100).

        Returns:
            Dict with the updated flag details.

        Raises:
            ValueError: If the flag_id is not found.
        """
        flag = self._feature_flags.get(flag_id)
        if flag is None:
            raise ValueError(f"Feature flag not found: {flag_id}")

        if enabled is not None:
            flag.enabled = enabled
        if rollout_percentage is not None:
            if not 0 <= rollout_percentage <= 100:
                raise ValueError("rollout_percentage must be between 0 and 100")
            flag.rollout_percentage = rollout_percentage

        flag.updated_at = datetime.now(timezone.utc).isoformat()

        # Log the change
        self._audit_log.append(AuditEntry(
            component=SystemComponent.AGENT_ENGINE,
            action="feature_flag.toggled",
            detail=f"Flag '{flag.name}' updated: enabled={flag.enabled}, rollout={flag.rollout_percentage}%",
            severity=ConsoleAlert.INFO,
        ))

        logger.info(
            f"Feature flag '{flag.name}' ({flag_id}) updated: "
            f"enabled={flag.enabled}, rollout={flag.rollout_percentage}%"
        )
        return flag.to_dict()

    # ── Audit Log Management ───────────────────────────────

    async def get_audit_logs(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query audit logs with optional filters.

        Args:
            filters: Optional dict with filter keys: component, action,
                     agent_id, severity, start_time, end_time.
            limit: Maximum number of entries to return (default 50).

        Returns:
            List of matching audit entry dictionaries, sorted newest first.
        """
        entries = list(self._audit_log)

        if filters:
            if "component" in filters:
                comp = filters["component"]
                if isinstance(comp, str):
                    entries = [e for e in entries if e.component.value == comp]
                else:
                    entries = [e for e in entries if e.component == comp]

            if "action" in filters:
                entries = [e for e in entries if filters["action"] in e.action]

            if "agent_id" in filters:
                entries = [e for e in entries if e.agent_id == filters["agent_id"]]

            if "severity" in filters:
                sev = filters["severity"]
                if isinstance(sev, str):
                    entries = [e for e in entries if e.severity.value == sev]
                else:
                    entries = [e for e in entries if e.severity == sev]

            if "start_time" in filters:
                entries = [e for e in entries if e.timestamp >= filters["start_time"]]

            if "end_time" in filters:
                entries = [e for e in entries if e.timestamp <= filters["end_time"]]

        # Sort newest first
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in entries[:limit]]

    # ── Agent Fleet Management ─────────────────────────────

    async def get_agent_fleet_status(self) -> dict[str, Any]:
        """Get the current status of all agents in the fleet.

        Returns:
            Dict with overall fleet statistics and per-agent status details.
        """
        agents = list(self._agent_fleet.values())
        status_counts: dict[str, int] = {}
        for agent in agents:
            st = agent["status"]
            status_counts[st] = status_counts.get(st, 0) + 1

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_agents": len(agents),
            "status_counts": status_counts,
            "active_agents": self._active_agents,
            "agents": [
                {
                    "agent_id": a["agent_id"],
                    "agent_name": a["agent_name"],
                    "role": a["role"],
                    "status": a["status"],
                    "uptime_seconds": round(a["uptime_seconds"], 1),
                    "active_sessions": a["active_sessions"],
                    "cpu_percent": a["cpu_percent"],
                    "memory_mb": a["memory_mb"],
                    "error_count": a["error_count"],
                    "last_heartbeat": a["last_heartbeat"],
                }
                for a in agents
            ],
        }

    # ── Maintenance and Recovery ───────────────────────────

    async def trigger_maintenance(self, component: SystemComponent) -> dict[str, Any]:
        """Trigger a maintenance routine for the specified component.

        Runs diagnostic checks, performs cleanup operations, and restores
        the component to a healthy state if possible.

        Args:
            component: The SystemComponent to perform maintenance on.

        Returns:
            Dict with maintenance results including before/after status,
            actions taken, and success status.
        """
        health = self._component_health.get(component.value)
        before_status = health.status.value if health else HealthStatus.OFFLINE.value

        actions_taken: list[str] = []
        actions_taken.append(f"Diagnostic scan for {component.value}")
        actions_taken.append(f"Cache cleared for {component.value}")
        actions_taken.append(f"Connection pool reset for {component.value}")

        if component == SystemComponent.MEMORY:
            actions_taken.append("Memory compaction triggered")
            actions_taken.append("Index optimization completed")
        elif component == SystemComponent.DATABASE:
            actions_taken.append("Index rebuild initiated")
            actions_taken.append("Query plan cache invalidated")
        elif component == SystemComponent.WORKSPACE:
            actions_taken.append("Orphaned workspace cleanup")
            actions_taken.append("Disk space reclaimed")
        elif component == SystemComponent.TOOL_EXECUTOR:
            actions_taken.append("Tool registry refreshed")
            actions_taken.append("Stale tool processes terminated")
        elif component == SystemComponent.PIPELINE:
            actions_taken.append("Stalled pipeline recovery")
            actions_taken.append("Queue drain completed")

        # Restore component health
        if health:
            health.status = HealthStatus.HEALTHY
            health.message = f"{component.value} maintenance completed successfully"
            health.latency_ms = random.uniform(5, 50)
            health.error_count = 0
            health.last_checked = datetime.now(timezone.utc).isoformat()
            health.metrics["success_rate"] = 1.0
        else:
            health = ComponentHealth(
                component=component,
                status=HealthStatus.HEALTHY,
                message=f"{component.value} restored after maintenance",
                latency_ms=random.uniform(5, 50),
            )
            self._component_health[component.value] = health

        after_status = health.status.value

        # Log maintenance in audit log
        self._audit_log.append(AuditEntry(
            component=component,
            action="maintenance.triggered",
            detail=f"Maintenance completed for {component.value}: {before_status} -> {after_status}",
            severity=ConsoleAlert.INFO,
        ))

        logger.info(
            f"Maintenance on {component.value}: {before_status} -> {after_status}"
        )

        return {
            "component": component.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "before_status": before_status,
            "after_status": after_status,
            "actions_taken": actions_taken,
            "success": after_status == HealthStatus.HEALTHY.value,
        }

    # ── Configuration Management ───────────────────────────

    async def get_config(self) -> dict[str, Any]:
        """Get the current platform configuration.

        Returns:
            Dict with all current configuration key-value pairs.
        """
        return dict(self._config)

    async def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update platform configuration values (hot-reload).

        Applies configuration changes immediately without requiring a
        platform restart. Invalid keys are silently ignored.

        Args:
            updates: Dict of configuration key-value pairs to update.

        Returns:
            Dict with the updated configuration.
        """
        for key, value in updates.items():
            if key in self._config:
                old_value = self._config[key]
                self._config[key] = value
                logger.info(f"Config hot-reloaded: {key} = {value} (was: {old_value})")

                self._audit_log.append(AuditEntry(
                    component=SystemComponent.AGENT_ENGINE,
                    action="config.updated",
                    detail=f"Config '{key}' changed from '{old_value}' to '{value}'",
                    severity=ConsoleAlert.INFO,
                ))
            else:
                logger.warning(f"Unknown config key ignored: {key}")

        return dict(self._config)

    # ── Backup and Recovery ────────────────────────────────

    async def create_backup(self) -> dict[str, Any]:
        """Create a platform-wide backup snapshot.

        Backs up configuration, feature flags, and audit logs. In simulation
        mode, this generates a simulated backup record.

        Returns:
            Dict with backup metadata including ID, size, and timestamp.
        """
        backup_id = f"backup-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        backup_data = {
            "backup_id": backup_id,
            "timestamp": timestamp,
            "size_bytes": random.randint(500000, 5000000),
            "components_included": [
                "configuration",
                "feature_flags",
                "audit_logs",
                "agent_registry",
                "component_health",
            ],
            "entry_counts": {
                "feature_flags": len(self._feature_flags),
                "audit_entries": len(self._audit_log),
                "config_keys": len(self._config),
                "agent_fleet": len(self._agent_fleet),
            },
            "checksum": uuid.uuid4().hex,
            "status": "completed",
        }

        self._audit_log.append(AuditEntry(
            component=SystemComponent.DATABASE,
            action="backup.created",
            detail=f"Platform backup {backup_id} created ({backup_data['size_bytes']} bytes)",
            severity=ConsoleAlert.INFO,
        ))

        logger.info(f"Backup created: {backup_id}")
        return backup_data

    async def restore_from_backup(self, backup_id: str) -> dict[str, Any]:
        """Restore platform state from a backup.

        In simulation mode, simulates a restore operation from a given
        backup identifier.

        Args:
            backup_id: The backup identifier to restore from.

        Returns:
            Dict with restore results including components restored
            and verification status.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        restore_result = {
            "backup_id": backup_id,
            "timestamp": timestamp,
            "status": "completed",
            "components_restored": [
                {"component": "configuration", "status": "restored", "items": len(self._config)},
                {"component": "feature_flags", "status": "restored", "items": len(self._feature_flags)},
                {"component": "audit_logs", "status": "restored", "items": len(self._audit_log)},
                {"component": "agent_registry", "status": "restored", "items": len(self._agent_fleet)},
            ],
            "verification": "passed",
            "notes": f"Restored from backup {backup_id} at {timestamp}",
        }

        self._audit_log.append(AuditEntry(
            component=SystemComponent.DATABASE,
            action="backup.restored",
            detail=f"Platform restored from backup {backup_id}",
            severity=ConsoleAlert.WARNING,
        ))

        logger.info(f"Restore from backup {backup_id} completed")
        return restore_result

    # ── Statistics ─────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive console statistics.

        Returns:
            Dict with uptime, fleet size, log counts, and config summary.
        """
        return {
            "console_id": "platform-console",
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "feature_flags_count": len(self._feature_flags),
            "audit_entries_count": len(self._audit_log),
            "alerts_count": len(self._alerts),
            "active_agents": self._active_agents,
            "total_agents_tracked": len(self._agent_fleet),
            "config_keys": len(self._config),
            "resource_snapshots": len(self._resource_history),
            "simulation_mode": True,
        }


# ══════════════════════════════════════════════════════════════════════
# Module-Level Singleton
# ══════════════════════════════════════════════════════════════════════

platform_console = PlatformConsole()