"""Buddy Resource Manager — intelligent allocation and governance of platform resources

Monitors and manages system resources across the Buddy platform, including
LLM token budgets, memory usage, concurrent execution limits, and compute
quotas. Provides throttling, prioritization, and graceful degradation
under resource pressure.

Core capabilities:
  - Token Budget Management: per-agent and global token quotas
  - Concurrency Control: max concurrent LLM calls, tool executions, sub-agents
  - Memory Pressure Handling: adaptive memory pruning and compaction
  - Rate Limiting: per-agent and per-endpoint request throttling
  - Priority Scheduling: weighted fair queuing for resource allocation
  - Resource Alerts: proactive notifications when approaching limits
  - Usage Analytics: historical resource consumption tracking
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.resource_manager")


class ResourceType(str, Enum):
    """Types of platform resources that can be managed."""
    TOKENS = "tokens"               # LLM token consumption
    CONCURRENT_CALLS = "concurrent_calls"  # Simultaneous LLM API calls
    MEMORY = "memory"               # Agent memory storage
    TOOL_EXECUTIONS = "tool_executions"    # Concurrent tool invocations
    SUB_AGENTS = "sub_agents"       # Active sub-agent workers
    WORKSPACE = "workspace"         # File system and code execution
    NETWORK = "network"             # API request bandwidth
    COMPUTE = "compute"             # CPU/memory for code execution


class ResourceStatus(str, Enum):
    """Resource availability status."""
    ABUNDANT = "abundant"    # Well below limits, no restrictions
    NORMAL = "normal"        # Within normal operating range
    CONSTRAINED = "constrained"  # Approaching limits, some throttling
    CRITICAL = "critical"    # At or near limits, strict throttling
    EXHAUSTED = "exhausted"  # Limits reached, new requests blocked


@dataclass
class ResourceQuota:
    """A quota definition for a specific resource."""
    resource_type: ResourceType
    max_limit: int               # Hard limit
    soft_limit: int = 0          # Limit at which throttling begins
    current_usage: int = 0
    alert_threshold: float = 0.8  # Fraction of max_limit to trigger alert
    reset_interval_seconds: int = 3600  # How often the quota resets
    last_reset_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResourceUsage:
    """A single usage record for a resource."""
    resource_type: ResourceType
    agent_id: str = ""
    amount: int = 0
    operation: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResourceAlert:
    """Alert generated when a resource threshold is crossed."""
    id: str = ""
    resource_type: ResourceType = ResourceType.TOKENS
    agent_id: str = ""
    severity: str = "warning"  # info, warning, critical
    message: str = ""
    current_usage: int = 0
    limit: int = 0
    usage_fraction: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CostEntry:
    """A cost allocation record for chargeback."""
    id: str = ""
    agent_id: str = ""
    resource_type: ResourceType = ResourceType.TOKENS
    amount: int = 0
    unit_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "USD"
    operation: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResourceForecast:
    """A forecast of future resource usage."""
    resource_type: ResourceType
    predicted_usage: int = 0
    confidence: float = 0.0
    trend: str = "stable"  # rising, falling, stable
    forecast_horizon_minutes: int = 60
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DeadlockRecord:
    """A record of a detected resource deadlock."""
    id: str = ""
    involved_agents: list[str] = field(default_factory=list)
    involved_resources: list[ResourceType] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str = ""
    resolution: str = ""
    is_resolved: bool = False


class ResourceManager:
    """Central resource manager for the Buddy platform.

    Manages quotas, throttling, and alerts for all platform resources.
    Provides per-agent resource tracking and global system-wide limits.
    """

    def __init__(self):
        # Global quotas for each resource type
        self._global_quotas: dict[ResourceType, ResourceQuota] = {
            ResourceType.TOKENS: ResourceQuota(
                resource_type=ResourceType.TOKENS,
                max_limit=1_000_000,
                soft_limit=800_000,
                reset_interval_seconds=86400,
            ),
            ResourceType.CONCURRENT_CALLS: ResourceQuota(
                resource_type=ResourceType.CONCURRENT_CALLS,
                max_limit=10,
                soft_limit=7,
                reset_interval_seconds=60,
            ),
            ResourceType.MEMORY: ResourceQuota(
                resource_type=ResourceType.MEMORY,
                max_limit=10_000,
                soft_limit=8_000,
                reset_interval_seconds=86400,
            ),
            ResourceType.TOOL_EXECUTIONS: ResourceQuota(
                resource_type=ResourceType.TOOL_EXECUTIONS,
                max_limit=5,
                soft_limit=3,
                reset_interval_seconds=60,
            ),
            ResourceType.SUB_AGENTS: ResourceQuota(
                resource_type=ResourceType.SUB_AGENTS,
                max_limit=settings.MAX_WORKERS,
                soft_limit=max(1, settings.MAX_WORKERS - 2),
                reset_interval_seconds=300,
            ),
            ResourceType.WORKSPACE: ResourceQuota(
                resource_type=ResourceType.WORKSPACE,
                max_limit=100,
                soft_limit=80,
                reset_interval_seconds=86400,
            ),
            ResourceType.NETWORK: ResourceQuota(
                resource_type=ResourceType.NETWORK,
                max_limit=1000,
                soft_limit=800,
                reset_interval_seconds=60,
            ),
            ResourceType.COMPUTE: ResourceQuota(
                resource_type=ResourceType.COMPUTE,
                max_limit=20,
                soft_limit=15,
                reset_interval_seconds=60,
            ),
        }

        # Per-agent quotas
        self._agent_quotas: dict[str, dict[ResourceType, ResourceQuota]] = {}

        # Active usage tracking
        self._active_usage: dict[ResourceType, int] = {rt: 0 for rt in ResourceType}

        # Usage history for analytics
        self._usage_history: list[ResourceUsage] = []
        self._max_history = 2000

        # Alerts
        self._alerts: list[ResourceAlert] = []
        self._max_alerts = 200

        # Concurrency tracking
        self._active_concurrent: dict[ResourceType, int] = {
            rt: 0 for rt in ResourceType
        }

        # Throttling state
        self._throttled_until: dict[ResourceType, float] = {}
        self._throttle_duration = 5.0  # seconds

        # Cost tracking
        self._cost_entries: list[CostEntry] = []
        self._cost_rates: dict[ResourceType, float] = {
            ResourceType.TOKENS: 0.00001,          # per token
            ResourceType.COMPUTE: 0.05,            # per execution
            ResourceType.MEMORY: 0.001,            # per entry
            ResourceType.NETWORK: 0.0001,          # per request
        }
        self._max_cost_entries = 1000

        # Deadlock detection
        self._resource_holders: dict[str, set[ResourceType]] = {}  # agent_id -> held resources
        self._resource_waiters: dict[str, set[ResourceType]] = {}  # agent_id -> waiting resources
        self._deadlock_history: list[DeadlockRecord] = []
        self._max_deadlock_records = 50

    # ── Quota Management ──────────────────────────────────

    def set_global_quota(self, resource_type: ResourceType, max_limit: int, soft_limit: int = 0):
        """Set a global quota for a resource type."""
        quota = self._global_quotas.get(resource_type)
        if quota:
            quota.max_limit = max_limit
            quota.soft_limit = soft_limit or int(max_limit * 0.8)
        else:
            self._global_quotas[resource_type] = ResourceQuota(
                resource_type=resource_type,
                max_limit=max_limit,
                soft_limit=soft_limit or int(max_limit * 0.8),
            )

    def set_agent_quota(
        self, agent_id: str, resource_type: ResourceType, max_limit: int, soft_limit: int = 0
    ):
        """Set a per-agent quota for a resource type."""
        if agent_id not in self._agent_quotas:
            self._agent_quotas[agent_id] = {}
        self._agent_quotas[agent_id][resource_type] = ResourceQuota(
            resource_type=resource_type,
            max_limit=max_limit,
            soft_limit=soft_limit or int(max_limit * 0.8),
        )

    def get_quota(self, resource_type: ResourceType, agent_id: str = "") -> ResourceQuota:
        """Get the effective quota for a resource, considering agent-specific overrides."""
        if agent_id and agent_id in self._agent_quotas:
            agent_quota = self._agent_quotas[agent_id].get(resource_type)
            if agent_quota:
                return agent_quota
        return self._global_quotas.get(resource_type, ResourceQuota(resource_type=resource_type, max_limit=100))

    # ── Resource Allocation ───────────────────────────────

    def get_status(self, resource_type: ResourceType, agent_id: str = "") -> ResourceStatus:
        """Get the current availability status of a resource."""
        quota = self.get_quota(resource_type, agent_id)
        usage = quota.current_usage

        if usage >= quota.max_limit:
            return ResourceStatus.EXHAUSTED
        if usage >= quota.soft_limit:
            return ResourceStatus.CRITICAL
        if usage >= quota.soft_limit * 0.7:
            return ResourceStatus.CONSTRAINED
        if usage >= quota.soft_limit * 0.3:
            return ResourceStatus.NORMAL
        return ResourceStatus.ABUNDANT

    def can_allocate(self, resource_type: ResourceType, amount: int = 1, agent_id: str = "") -> tuple[bool, str]:
        """Check if a resource allocation can be made."""
        quota = self.get_quota(resource_type, agent_id)

        if quota.current_usage + amount > quota.max_limit:
            return False, f"Resource {resource_type.value} exhausted: {quota.current_usage}/{quota.max_limit}"

        # Check throttling state
        if resource_type in self._throttled_until:
            if time.time() < self._throttled_until[resource_type]:
                return False, f"Resource {resource_type.value} is throttled"

        # Check concurrent limits
        if resource_type == ResourceType.CONCURRENT_CALLS:
            if self._active_concurrent[resource_type] >= quota.max_limit:
                return False, f"Max concurrent calls reached: {quota.max_limit}"

        return True, ""

    def allocate(
        self, resource_type: ResourceType, amount: int = 1, agent_id: str = "",
        operation: str = ""
    ) -> bool:
        """Attempt to allocate a resource. Returns True if successful."""
        ok, _ = self.can_allocate(resource_type, amount, agent_id)
        if not ok:
            return False

        quota = self.get_quota(resource_type, agent_id)
        quota.current_usage += amount

        # Track active concurrent usage
        if resource_type in (ResourceType.CONCURRENT_CALLS, ResourceType.TOOL_EXECUTIONS, ResourceType.SUB_AGENTS):
            self._active_concurrent[resource_type] += amount

        # Record usage
        self._record_usage(resource_type, agent_id, amount, operation)

        # Check alert thresholds
        self._check_alerts(resource_type, agent_id, quota)

        return True

    def release(self, resource_type: ResourceType, amount: int = 1):
        """Release a previously allocated resource."""
        if resource_type in (ResourceType.CONCURRENT_CALLS, ResourceType.TOOL_EXECUTIONS, ResourceType.SUB_AGENTS):
            self._active_concurrent[resource_type] = max(0, self._active_concurrent[resource_type] - amount)

    def throttle(self, resource_type: ResourceType, duration_seconds: float | None = None):
        """Temporarily throttle a resource type."""
        duration = duration_seconds or self._throttle_duration
        self._throttled_until[resource_type] = time.time() + duration
        logger.warning(f"Resource {resource_type.value} throttled for {duration}s")

    def reset_quota(self, resource_type: ResourceType, agent_id: str = ""):
        """Reset a quota's usage counter."""
        quota = self.get_quota(resource_type, agent_id)
        quota.current_usage = 0
        quota.last_reset_at = datetime.now(timezone.utc).isoformat()

    def reset_all_quotas(self):
        """Reset all quotas."""
        for quota in self._global_quotas.values():
            quota.current_usage = 0
            quota.last_reset_at = datetime.now(timezone.utc).isoformat()
        for agent_quotas in self._agent_quotas.values():
            for quota in agent_quotas.values():
                quota.current_usage = 0
                quota.last_reset_at = datetime.now(timezone.utc).isoformat()
        self._active_concurrent = {rt: 0 for rt in ResourceType}

    # ── Internal Helpers ──────────────────────────────────

    def _record_usage(self, resource_type: ResourceType, agent_id: str, amount: int, operation: str):
        """Record a usage entry in the history."""
        usage = ResourceUsage(
            resource_type=resource_type,
            agent_id=agent_id,
            amount=amount,
            operation=operation,
        )
        self._usage_history.append(usage)
        if len(self._usage_history) > self._max_history:
            self._usage_history = self._usage_history[-self._max_history:]

    def _check_alerts(self, resource_type: ResourceType, agent_id: str, quota: ResourceQuota):
        """Check if an alert should be generated for this resource."""
        fraction = quota.current_usage / max(quota.max_limit, 1)

        if fraction >= 1.0:
            severity = "critical"
            message = f"Resource {resource_type.value} exhausted ({quota.current_usage}/{quota.max_limit})"
        elif fraction >= quota.alert_threshold:
            severity = "warning"
            message = f"Resource {resource_type.value} approaching limit ({quota.current_usage}/{quota.max_limit})"
        else:
            return

        alert = ResourceAlert(
            id=f"alert-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            resource_type=resource_type,
            agent_id=agent_id,
            severity=severity,
            message=message,
            current_usage=quota.current_usage,
            limit=quota.max_limit,
            usage_fraction=fraction,
        )
        self._alerts.append(alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]

        logger.warning(f"Resource alert: {message}")

    # ── Statistics ────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get comprehensive resource management statistics."""
        quotas = {}
        for rt, quota in self._global_quotas.items():
            quotas[rt.value] = {
                "max_limit": quota.max_limit,
                "soft_limit": quota.soft_limit,
                "current_usage": quota.current_usage,
                "status": self.get_status(rt).value,
                "usage_fraction": round(quota.current_usage / max(quota.max_limit, 1), 3),
                "active_concurrent": self._active_concurrent.get(rt, 0),
            }

        return {
            "quotas": quotas,
            "total_alerts": len(self._alerts),
            "recent_alerts": [
                {
                    "id": a.id,
                    "resource_type": a.resource_type.value,
                    "agent_id": a.agent_id,
                    "severity": a.severity,
                    "message": a.message,
                    "usage_fraction": round(a.usage_fraction, 3),
                    "timestamp": a.timestamp,
                }
                for a in self._alerts[-10:]
            ],
            "usage_history_count": len(self._usage_history),
            "throttled_resources": list(self._throttled_until.keys()),
        }

    def get_agent_usage(self, agent_id: str) -> dict:
        """Get resource usage summary for a specific agent."""
        agent_usage = {}
        for rt in ResourceType:
            quota = self.get_quota(rt, agent_id)
            # Count agent-specific usage from history
            recent_usage = [
                u for u in self._usage_history[-500:]
                if u.agent_id == agent_id and u.resource_type == rt
            ]
            total_used = sum(u.amount for u in recent_usage)

            agent_usage[rt.value] = {
                "total_used": total_used,
                "quota_max": quota.max_limit,
                "quota_soft": quota.soft_limit,
                "usage_fraction": round(total_used / max(quota.max_limit, 1), 3),
                "status": self.get_status(rt, agent_id).value,
            }

        return agent_usage

    def get_alerts(self, limit: int = 20, severity: str | None = None) -> list[dict]:
        """Get recent resource alerts."""
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return [
            {
                "id": a.id,
                "resource_type": a.resource_type.value,
                "agent_id": a.agent_id,
                "severity": a.severity,
                "message": a.message,
                "current_usage": a.current_usage,
                "limit": a.limit,
                "usage_fraction": round(a.usage_fraction, 3),
                "timestamp": a.timestamp,
            }
            for a in alerts[-limit:]
        ]

    # ── Predictive Resource Scaling ────────────────────────

    def predict_resource_scaling(
        self, resource_type: ResourceType, forecast_minutes: int = 60
    ) -> ResourceForecast:
        """Predict resource needs based on historical usage patterns.

        Uses simple linear regression on recent usage history to forecast
        future resource consumption. The forecast can be used to
        proactively scale quotas up or down.

        Args:
            resource_type: The resource type to forecast.
            forecast_minutes: How far ahead to forecast in minutes.

        Returns:
            A ResourceForecast with predicted usage and confidence.
        """
        # Gather recent usage data for this resource type
        recent = [
            u for u in self._usage_history[-200:]
            if u.resource_type == resource_type
        ]

        if len(recent) < 5:
            return ResourceForecast(
                resource_type=resource_type,
                predicted_usage=self._global_quotas[resource_type].current_usage,
                confidence=0.1,
                trend="stable",
                forecast_horizon_minutes=forecast_minutes,
            )

        # Extract timestamps and amounts as a simple time series
        data_points = []
        for u in recent:
            try:
                ts = datetime.fromisoformat(u.timestamp)
                data_points.append((ts.timestamp(), u.amount))
            except (ValueError, TypeError):
                continue

        if len(data_points) < 5:
            return ResourceForecast(
                resource_type=resource_type,
                predicted_usage=recent[-1].amount if recent else 0,
                confidence=0.2,
                trend="stable",
                forecast_horizon_minutes=forecast_minutes,
            )

        # Simple linear regression: y = mx + b
        n = len(data_points)
        sum_x = sum(p[0] for p in data_points)
        sum_y = sum(p[1] for p in data_points)
        sum_xy = sum(p[0] * p[1] for p in data_points)
        sum_x2 = sum(p[0] ** 2 for p in data_points)

        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator

        intercept = (sum_y - slope * sum_x) / n

        # Forecast to the target time
        forecast_time = time.time() + (forecast_minutes * 60)
        predicted = slope * forecast_time + intercept
        predicted = max(0, int(predicted))

        # Determine trend
        if slope > 0.01:
            trend = "rising"
        elif slope < -0.01:
            trend = "falling"
        else:
            trend = "stable"

        # Confidence based on data variance
        mean_y = sum_y / n
        variance = sum((p[1] - mean_y) ** 2 for p in data_points) / n
        confidence = min(0.95, 1.0 / (1.0 + variance / max(mean_y, 1)))

        return ResourceForecast(
            resource_type=resource_type,
            predicted_usage=predicted,
            confidence=round(confidence, 2),
            trend=trend,
            forecast_horizon_minutes=forecast_minutes,
        )

    def apply_scaling_recommendation(self, resource_type: ResourceType) -> dict:
        """Apply a scaling recommendation based on forecast.

        If the forecast predicts usage exceeding the current soft limit,
        the quota is automatically scaled up. If usage is predicted to
        fall significantly, the quota is scaled down.

        Returns:
            Dict with action taken and new limits.
        """
        forecast = self.predict_resource_scaling(resource_type)
        quota = self._global_quotas.get(resource_type)
        if not quota:
            return {"action": "none", "reason": "No quota defined"}

        result = {
            "action": "none",
            "resource_type": resource_type.value,
            "current_max": quota.max_limit,
            "predicted_usage": forecast.predicted_usage,
            "confidence": forecast.confidence,
        }

        if forecast.confidence < 0.3:
            result["action"] = "insufficient_data"
            return result

        if forecast.predicted_usage > quota.soft_limit and forecast.trend == "rising":
            new_limit = int(forecast.predicted_usage * 1.2)
            old_limit = quota.max_limit
            self.set_global_quota(resource_type, new_limit)
            result["action"] = "scaled_up"
            result["new_max"] = new_limit
            result["old_max"] = old_limit
            logger.info(f"Scaled up {resource_type.value}: {old_limit} -> {new_limit}")

        elif forecast.predicted_usage < quota.soft_limit * 0.3 and forecast.trend == "falling":
            new_limit = max(1, int(forecast.predicted_usage * 1.5))
            old_limit = quota.max_limit
            self.set_global_quota(resource_type, new_limit)
            result["action"] = "scaled_down"
            result["new_max"] = new_limit
            result["old_max"] = old_limit
            logger.info(f"Scaled down {resource_type.value}: {old_limit} -> {new_limit}")

        return result

    # ── Cost Allocation & Chargeback ──────────────────────

    def set_cost_rate(
        self, resource_type: ResourceType, unit_cost: float
    ):
        """Set the cost per unit for a resource type.

        Args:
            resource_type: The resource type.
            unit_cost: Cost per unit in the configured currency.
        """
        self._cost_rates[resource_type] = unit_cost

    def allocate_cost(
        self,
        agent_id: str,
        resource_type: ResourceType,
        amount: int,
        operation: str = "",
    ) -> CostEntry:
        """Record a cost entry for chargeback to an agent.

        Calculates the cost based on the configured rate for the resource
        type and records it for later reporting.

        Args:
            agent_id: The agent consuming the resource.
            resource_type: The type of resource consumed.
            amount: Number of units consumed.
            operation: Description of the operation.

        Returns:
            The created CostEntry.
        """
        unit_cost = self._cost_rates.get(resource_type, 0.0)
        total_cost = round(amount * unit_cost, 6)

        entry = CostEntry(
            id=f"cost-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            agent_id=agent_id,
            resource_type=resource_type,
            amount=amount,
            unit_cost=unit_cost,
            total_cost=total_cost,
            operation=operation,
        )
        self._cost_entries.append(entry)
        if len(self._cost_entries) > self._max_cost_entries:
            self._cost_entries = self._cost_entries[-self._max_cost_entries:]

        logger.debug(
            f"Cost allocated: {agent_id} {resource_type.value} "
            f"x{amount} = ${total_cost:.6f}"
        )
        return entry

    def get_cost_report(
        self, agent_id: str = "", since: str = ""
    ) -> dict:
        """Generate a cost allocation report.

        Args:
            agent_id: Filter by agent. Empty string for all agents.
            since: ISO timestamp to filter entries after.

        Returns:
            Dict with per-agent and per-resource cost breakdowns.
        """
        entries = self._cost_entries
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        if since:
            entries = [
                e for e in entries
                if e.timestamp >= since
            ]

        # Aggregate by agent
        by_agent: dict[str, float] = {}
        for e in entries:
            by_agent[e.agent_id] = by_agent.get(e.agent_id, 0.0) + e.total_cost

        # Aggregate by resource type
        by_resource: dict[str, float] = {}
        for e in entries:
            by_resource[e.resource_type.value] = (
                by_resource.get(e.resource_type.value, 0.0) + e.total_cost
            )

        total = sum(by_agent.values())

        return {
            "total_cost": round(total, 6),
            "currency": "USD",
            "entry_count": len(entries),
            "by_agent": {
                agent: round(cost, 6) for agent, cost in by_agent.items()
            },
            "by_resource": {
                rt: round(cost, 6) for rt, cost in by_resource.items()
            },
        }

    def get_cost_rates(self) -> dict[str, float]:
        """Get current cost rates for all resource types."""
        return {
            rt.value: self._cost_rates.get(rt, 0.0)
            for rt in ResourceType
        }

    # ── Resource Throttling with Graceful Degradation ─────

    def throttle_with_degradation(
        self,
        resource_type: ResourceType,
        degradation_level: str = "moderate",
        duration_seconds: float | None = None,
    ) -> dict:
        """Apply throttling with graceful degradation options.

        Instead of a hard block, degradation allows reduced functionality.
        The degradation level determines how much capacity is maintained.

        Levels:
            - 'light': 80% capacity maintained
            - 'moderate': 50% capacity maintained
            - 'severe': 20% capacity maintained
            - 'critical': 0% capacity (full block)

        Args:
            resource_type: The resource to throttle.
            degradation_level: Level of degradation to apply.
            duration_seconds: How long the throttle lasts.

        Returns:
            Dict with degradation details.
        """
        levels = {
            "light": 0.8,
            "moderate": 0.5,
            "severe": 0.2,
            "critical": 0.0,
        }
        factor = levels.get(degradation_level, 0.5)

        quota = self._global_quotas.get(resource_type)
        if not quota:
            return {"error": "Resource type not found"}

        original_max = quota.max_limit
        original_soft = quota.soft_limit

        # Apply degradation by reducing limits
        quota.max_limit = max(1, int(original_max * factor))
        quota.soft_limit = max(1, int(original_soft * factor))

        if duration_seconds:
            self.throttle(resource_type, duration_seconds)

        logger.warning(
            f"Degradation applied to {resource_type.value}: "
            f"level={degradation_level}, limit={original_max} -> {quota.max_limit}"
        )

        return {
            "resource_type": resource_type.value,
            "degradation_level": degradation_level,
            "capacity_factor": factor,
            "original_max_limit": original_max,
            "degraded_max_limit": quota.max_limit,
            "original_soft_limit": original_soft,
            "degraded_soft_limit": quota.soft_limit,
            "status": self.get_status(resource_type).value,
        }

    def restore_degradation(
        self, resource_type: ResourceType, original_max: int, original_soft: int
    ) -> bool:
        """Restore a resource from a degraded state to its original limits.

        Args:
            resource_type: The resource type to restore.
            original_max: The original max limit to restore.
            original_soft: The original soft limit to restore.

        Returns:
            True if restored successfully.
        """
        quota = self._global_quotas.get(resource_type)
        if not quota:
            return False
        quota.max_limit = original_max
        quota.soft_limit = original_soft
        self._throttled_until.pop(resource_type, None)
        logger.info(f"Degradation restored for {resource_type.value}")
        return True

    # ── Resource Usage Forecasting ────────────────────────

    def forecast_resource_usage(
        self,
        resource_type: ResourceType,
        forecast_horizon_minutes: int = 60,
        method: str = "linear",
    ) -> ResourceForecast:
        """Forecast future resource usage with trend analysis.

        Supports multiple forecasting methods:
            - 'linear': Simple linear regression on recent history.
            - 'moving_average': Moving average of the last N data points.

        Args:
            resource_type: The resource type to forecast.
            forecast_horizon_minutes: How far ahead to forecast.
            method: Forecasting method to use.

        Returns:
            A ResourceForecast with predicted usage and trend.
        """
        if method == "linear":
            return self.predict_resource_scaling(
                resource_type, forecast_horizon_minutes
            )

        if method == "moving_average":
            recent = [
                u for u in self._usage_history[-200:]
                if u.resource_type == resource_type
            ]
            if len(recent) < 3:
                return ResourceForecast(
                    resource_type=resource_type,
                    predicted_usage=0,
                    confidence=0.1,
                    trend="stable",
                    forecast_horizon_minutes=forecast_horizon_minutes,
                )

            # Simple moving average
            window = min(10, len(recent))
            recent_window = recent[-window:]
            avg_usage = sum(u.amount for u in recent_window) / len(recent_window)

            # Determine trend from recent vs older
            if len(recent) >= window * 2:
                older_window = recent[-window * 2:-window]
                older_avg = sum(u.amount for u in older_window) / len(older_window)
                if avg_usage > older_avg * 1.1:
                    trend = "rising"
                elif avg_usage < older_avg * 0.9:
                    trend = "falling"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            return ResourceForecast(
                resource_type=resource_type,
                predicted_usage=int(avg_usage),
                confidence=0.5,
                trend=trend,
                forecast_horizon_minutes=forecast_horizon_minutes,
            )

        # Default to linear
        return self.predict_resource_scaling(
            resource_type, forecast_horizon_minutes
        )

    def get_usage_trend(self, resource_type: ResourceType) -> dict:
        """Get a trend analysis of resource usage over the last hour.

        Returns:
            Dict with trend direction, slope, and recent usage samples.
        """
        one_hour_ago = time.time() - 3600
        recent = [
            u for u in self._usage_history[-500:]
            if u.resource_type == resource_type
        ]
        recent = [
            u for u in recent
            if datetime.fromisoformat(u.timestamp).timestamp() >= one_hour_ago
        ]

        if len(recent) < 3:
            return {
                "resource_type": resource_type.value,
                "trend": "unknown",
                "sample_count": len(recent),
                "samples": [],
            }

        samples = [
            {
                "amount": u.amount,
                "timestamp": u.timestamp,
                "agent_id": u.agent_id,
            }
            for u in recent[-20:]
        ]

        total = sum(u.amount for u in recent)
        avg = total / len(recent)

        return {
            "resource_type": resource_type.value,
            "trend": "rising" if total > 0 and recent[-1].amount > avg else "stable",
            "sample_count": len(recent),
            "total_usage": total,
            "average_usage": round(avg, 2),
            "samples": samples,
        }

    # ── Deadlock Detection & Resolution ───────────────────

    def register_resource_holder(
        self, agent_id: str, resource_type: ResourceType
    ):
        """Register that an agent holds a resource.

        This is used for deadlock detection — when agents hold resources
        while waiting for others, a deadlock cycle can form.

        Args:
            agent_id: The agent holding the resource.
            resource_type: The resource being held.
        """
        if agent_id not in self._resource_holders:
            self._resource_holders[agent_id] = set()
        self._resource_holders[agent_id].add(resource_type)

    def register_resource_waiter(
        self, agent_id: str, resource_type: ResourceType
    ):
        """Register that an agent is waiting on a resource.

        Args:
            agent_id: The agent waiting.
            resource_type: The resource being waited on.
        """
        if agent_id not in self._resource_waiters:
            self._resource_waiters[agent_id] = set()
        self._resource_waiters[agent_id].add(resource_type)

    def release_resource_holder(
        self, agent_id: str, resource_type: ResourceType
    ):
        """Release a resource held by an agent."""
        if agent_id in self._resource_holders:
            self._resource_holders[agent_id].discard(resource_type)

    def detect_deadlocks(self) -> list[DeadlockRecord]:
        """Detect resource deadlocks across all agents.

        A deadlock occurs when agent A holds resource X and waits for Y,
        while agent B holds Y and waits for X — forming a cycle.

        Returns:
            List of detected DeadlockRecords.
        """
        deadlocks: list[DeadlockRecord] = []

        # Build a wait-for graph: agent -> set of agents it's waiting on
        wait_for_graph: dict[str, set[str]] = {}

        for agent_id, waiting_resources in self._resource_waiters.items():
            if not waiting_resources:
                continue
            wait_for_graph[agent_id] = set()

            for resource in waiting_resources:
                # Find agents holding this resource
                for holder_id, held_resources in self._resource_holders.items():
                    if holder_id == agent_id:
                        continue
                    if resource in held_resources:
                        wait_for_graph[agent_id].add(holder_id)

        # Detect cycles using DFS
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(agent_id: str, path: list[str]) -> None:
            if agent_id in in_stack:
                cycle_start = path.index(agent_id)
                cycle = path[cycle_start:]
                involved_resources = set()
                for i, aid in enumerate(cycle):
                    next_aid = cycle[(i + 1) % len(cycle)]
                    for res in self._resource_waiters.get(aid, set()):
                        if res in self._resource_holders.get(next_aid, set()):
                            involved_resources.add(res)
                deadlocks.append(DeadlockRecord(
                    id=f"ddlk-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                    involved_agents=list(cycle),
                    involved_resources=list(involved_resources),
                ))
                return
            if agent_id in visited:
                return

            visited.add(agent_id)
            in_stack.add(agent_id)
            path.append(agent_id)

            for neighbor in wait_for_graph.get(agent_id, set()):
                dfs(neighbor, list(path))

            in_stack.discard(agent_id)
            path.pop()

        for agent_id in wait_for_graph:
            if agent_id not in visited:
                dfs(agent_id, [])

        if deadlocks:
            self._deadlock_history.extend(deadlocks)
            if len(self._deadlock_history) > self._max_deadlock_records:
                self._deadlock_history = self._deadlock_history[-self._max_deadlock_records:]
            logger.warning(f"Detected {len(deadlocks)} resource deadlocks")

        return deadlocks

    def resolve_deadlock(
        self, deadlock_id: str, strategy: str = "abort_youngest"
    ) -> bool:
        """Resolve a detected deadlock.

        Strategies:
            - 'abort_youngest': Release resources from the most recently
              registered agent in the deadlock cycle.
            - 'abort_all': Release all resources from all involved agents.

        Args:
            deadlock_id: The deadlock record ID to resolve.
            strategy: Resolution strategy to apply.

        Returns:
            True if the deadlock was resolved.
        """
        for record in self._deadlock_history:
            if record.id == deadlock_id:
                if strategy == "abort_youngest":
                    # Release the last agent in the cycle
                    victim = record.involved_agents[-1]
                    if victim in self._resource_holders:
                        self._resource_holders[victim].clear()
                    if victim in self._resource_waiters:
                        self._resource_waiters[victim].clear()
                    record.resolution = f"Aborted {victim} (youngest)"
                    record.resolved_at = datetime.now(timezone.utc).isoformat()
                    record.is_resolved = True
                    logger.info(f"Deadlock resolved by aborting {victim}")
                    return True

                elif strategy == "abort_all":
                    for agent_id in record.involved_agents:
                        if agent_id in self._resource_holders:
                            self._resource_holders[agent_id].clear()
                        if agent_id in self._resource_waiters:
                            self._resource_waiters[agent_id].clear()
                    record.resolution = "Aborted all involved agents"
                    record.resolved_at = datetime.now(timezone.utc).isoformat()
                    record.is_resolved = True
                    logger.info(f"Deadlock resolved by aborting all agents")
                    return True

        return False

    def get_deadlock_history(self) -> list[dict]:
        """Get the history of detected deadlocks."""
        return [
            {
                "id": r.id,
                "involved_agents": r.involved_agents,
                "involved_resources": [rt.value for rt in r.involved_resources],
                "detected_at": r.detected_at,
                "resolved_at": r.resolved_at,
                "resolution": r.resolution,
                "is_resolved": r.is_resolved,
            }
            for r in self._deadlock_history
        ]


# Global instance
resource_manager = ResourceManager()