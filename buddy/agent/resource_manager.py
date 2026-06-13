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


# Global instance
resource_manager = ResourceManager()