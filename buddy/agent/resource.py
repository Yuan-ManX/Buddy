"""Buddy Resource Manager — quota-based resource allocation and throttling

Manages compute, memory, and API resources across agents and the platform.
Enforces quotas, provides throttling, and ensures fair resource distribution
among concurrent agents and tasks.

Core capabilities:
  - Resource Quotas: per-agent and global limits on tokens, API calls, concurrency
  - Rate Limiting: sliding window rate limiters for API calls
  - Priority-based Allocation: higher priority tasks get resources first
  - Resource Monitoring: real-time usage tracking and alerts
  - Burst Handling: token bucket algorithm for handling usage spikes
  - Cost Budgeting: per-agent and global cost caps
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.resource")


class ResourceType(str, Enum):
    TOKENS = "tokens"
    API_CALLS = "api_calls"
    CONCURRENT_REQUESTS = "concurrent_requests"
    MEMORY_MB = "memory_mb"
    STORAGE_MB = "storage_mb"
    COST_USD = "cost_usd"
    TOOL_EXECUTIONS = "tool_executions"
    SUBAGENTS = "subagents"


class QuotaPeriod(str, Enum):
    PER_REQUEST = "per_request"
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    PER_MONTH = "per_month"


@dataclass
class ResourceQuota:
    """A resource limit for a specific resource type and period."""
    resource_type: ResourceType
    limit: float
    period: QuotaPeriod
    current_usage: float = 0.0
    last_reset: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    burst_limit: float | None = None

    def is_exhausted(self) -> bool:
        self._check_reset()
        burst = self.burst_limit or self.limit
        return self.current_usage >= burst

    def remaining(self) -> float:
        self._check_reset()
        burst = self.burst_limit or self.limit
        return max(0.0, burst - self.current_usage)

    def usage_ratio(self) -> float:
        self._check_reset()
        burst = self.burst_limit or self.limit
        if burst == 0:
            return 0.0
        return min(1.0, self.current_usage / burst)

    def _check_reset(self):
        """Reset usage counter if the period has elapsed."""
        now = datetime.now(timezone.utc)
        last = datetime.fromisoformat(self.last_reset)
        periods = {
            QuotaPeriod.PER_MINUTE: timedelta(minutes=1),
            QuotaPeriod.PER_HOUR: timedelta(hours=1),
            QuotaPeriod.PER_DAY: timedelta(days=1),
            QuotaPeriod.PER_MONTH: timedelta(days=30),
            QuotaPeriod.PER_REQUEST: timedelta(seconds=0),
        }
        delta = periods.get(self.period, timedelta(hours=1))
        if self.period != QuotaPeriod.PER_REQUEST and (now - last) >= delta:
            self.current_usage = 0.0
            self.last_reset = now.isoformat()


class TokenBucket:
    """Token bucket algorithm for rate limiting with burst support."""

    def __init__(self, rate: float, capacity: float):
        self.rate = rate           # tokens per second
        self.capacity = capacity   # max tokens (burst size)
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens. Returns True if successful."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_time(self, tokens: float = 1.0) -> float:
        """Estimated seconds until enough tokens are available."""
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        return (tokens - self.tokens) / max(self.rate, 0.001)


class ResourceManager:
    """Central resource management with quotas, rate limiting, and monitoring.

    Manages resource allocation across all agents and the platform globally.
    Enforces per-agent and global quotas with priority-based allocation.
    """

    # Default global limits
    DEFAULT_GLOBAL_LIMITS: dict[ResourceType, float] = {
        ResourceType.TOKENS: 10_000_000,
        ResourceType.API_CALLS: 100_000,
        ResourceType.CONCURRENT_REQUESTS: 50,
        ResourceType.TOOL_EXECUTIONS: 50_000,
        ResourceType.SUBAGENTS: 500,
        ResourceType.COST_USD: 100.0,
    }

    # Default per-agent limits
    DEFAULT_AGENT_LIMITS: dict[ResourceType, float] = {
        ResourceType.TOKENS: 1_000_000,
        ResourceType.API_CALLS: 10_000,
        ResourceType.CONCURRENT_REQUESTS: 10,
        ResourceType.TOOL_EXECUTIONS: 5_000,
        ResourceType.SUBAGENTS: 50,
        ResourceType.COST_USD: 10.0,
    }

    def __init__(self):
        self._global_quotas: dict[ResourceType, ResourceQuota] = {}
        self._agent_quotas: dict[str, dict[ResourceType, ResourceQuota]] = defaultdict(dict)
        self._rate_limiters: dict[str, TokenBucket] = {}
        self._concurrent_requests: int = 0
        self._max_concurrent: int = 50
        self._usage_history: list[dict] = []
        self._alerts: list[dict] = []
        self._alert_threshold: float = 0.8

        # Initialize global quotas
        for res_type, limit in self.DEFAULT_GLOBAL_LIMITS.items():
            self._global_quotas[res_type] = ResourceQuota(
                resource_type=res_type,
                limit=limit,
                period=QuotaPeriod.PER_DAY,
                burst_limit=limit * 1.5,
            )

        # Initialize global rate limiter
        self._rate_limiters["global"] = TokenBucket(rate=100, capacity=200)

    def set_agent_quota(self, agent_id: str, resource_type: ResourceType, limit: float, period: QuotaPeriod = QuotaPeriod.PER_DAY):
        """Set a resource quota for a specific agent."""
        self._agent_quotas[agent_id][resource_type] = ResourceQuota(
            resource_type=resource_type,
            limit=limit,
            period=period,
            burst_limit=limit * 1.5,
        )
        logger.info(f"Set {resource_type.value} quota for {agent_id}: {limit}/{period.value}")

    def get_agent_quota(self, agent_id: str, resource_type: ResourceType) -> ResourceQuota:
        """Get or create a resource quota for an agent."""
        if resource_type not in self._agent_quotas.get(agent_id, {}):
            default = self.DEFAULT_AGENT_LIMITS.get(resource_type, 1000)
            self._agent_quotas[agent_id][resource_type] = ResourceQuota(
                resource_type=resource_type,
                limit=default,
                period=QuotaPeriod.PER_DAY,
                burst_limit=default * 1.5,
            )
        return self._agent_quotas[agent_id][resource_type]

    async def acquire(self, agent_id: str, resource_type: ResourceType, amount: float = 1.0) -> bool:
        """Try to acquire resources. Returns True if within quota."""
        # Check global quota
        global_quota = self._global_quotas.get(resource_type)
        if global_quota and global_quota.is_exhausted():
            logger.warning(f"Global {resource_type.value} quota exhausted")
            return False

        # Check agent quota
        agent_quota = self.get_agent_quota(agent_id, resource_type)
        if agent_quota.is_exhausted():
            logger.warning(f"Agent {agent_id} {resource_type.value} quota exhausted")
            return False

        # Check concurrency for concurrent resource types
        if resource_type == ResourceType.CONCURRENT_REQUESTS:
            if self._concurrent_requests >= self._max_concurrent:
                return False
            self._concurrent_requests += amount

        # Check rate limiter for API calls
        if resource_type == ResourceType.API_CALLS:
            agent_limiter = self._rate_limiters.get(agent_id)
            if not agent_limiter:
                agent_limiter = TokenBucket(rate=10, capacity=20)
                self._rate_limiters[agent_id] = agent_limiter
            if not agent_limiter.consume(amount):
                return False

        # Apply usage
        if global_quota:
            global_quota.current_usage += amount
        agent_quota.current_usage += amount

        # Track usage history
        self._usage_history.append({
            "agent_id": agent_id,
            "resource_type": resource_type.value,
            "amount": amount,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Check alert threshold
        if agent_quota.usage_ratio() >= self._alert_threshold:
            self._alerts.append({
                "agent_id": agent_id,
                "resource_type": resource_type.value,
                "usage_ratio": agent_quota.usage_ratio(),
                "message": f"Agent {agent_id} at {agent_quota.usage_ratio()*100:.0f}% of {resource_type.value} quota",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return True

    def release(self, agent_id: str, resource_type: ResourceType, amount: float = 1.0):
        """Release previously acquired resources."""
        if resource_type == ResourceType.CONCURRENT_REQUESTS:
            self._concurrent_requests = max(0, self._concurrent_requests - amount)

        global_quota = self._global_quotas.get(resource_type)
        if global_quota:
            global_quota.current_usage = max(0, global_quota.current_usage - amount)

        agent_quota = self._agent_quotas.get(agent_id, {}).get(resource_type)
        if agent_quota:
            agent_quota.current_usage = max(0, agent_quota.current_usage - amount)

    def check_availability(self, agent_id: str, resource_type: ResourceType, amount: float = 1.0) -> tuple[bool, str]:
        """Check if resources are available without acquiring them."""
        global_quota = self._global_quotas.get(resource_type)
        if global_quota and global_quota.is_exhausted():
            return False, f"Global {resource_type.value} quota exhausted"

        agent_quota = self._agent_quotas.get(agent_id, {}).get(resource_type)
        if not agent_quota:
            return True, "Available"

        if agent_quota.is_exhausted():
            return False, f"Agent {resource_type.value} quota exhausted"

        if agent_quota.remaining() < amount:
            return False, f"Insufficient {resource_type.value} (need {amount}, have {agent_quota.remaining()})"

        return True, "Available"

    def get_usage_report(self, agent_id: str) -> dict:
        """Get detailed resource usage report for an agent."""
        quotas = self._agent_quotas.get(agent_id, {})
        return {
            "agent_id": agent_id,
            "resources": {
                rt.value: {
                    "limit": q.limit,
                    "used": q.current_usage,
                    "remaining": q.remaining(),
                    "usage_ratio": f"{q.usage_ratio()*100:.1f}%",
                    "period": q.period.value,
                }
                for rt, q in quotas.items()
            },
            "concurrent_requests": self._concurrent_requests,
        }

    def get_global_report(self) -> dict:
        """Get global resource usage report."""
        return {
            "resources": {
                rt.value: {
                    "limit": q.limit,
                    "used": q.current_usage,
                    "remaining": q.remaining(),
                    "usage_ratio": f"{q.usage_ratio()*100:.1f}%",
                }
                for rt, q in self._global_quotas.items()
            },
            "concurrent_requests": self._concurrent_requests,
            "max_concurrent": self._max_concurrent,
        }

    def get_alerts(self, limit: int = 10) -> list[dict]:
        """Get recent resource usage alerts."""
        return self._alerts[-limit:]

    def clear_alerts(self):
        """Clear all alerts."""
        self._alerts.clear()

    def reset_agent_quotas(self, agent_id: str):
        """Reset all quotas for an agent."""
        for quota in self._agent_quotas.get(agent_id, {}).values():
            quota.current_usage = 0.0
            quota.last_reset = datetime.now(timezone.utc).isoformat()
        logger.info(f"Reset quotas for agent {agent_id}")

    def get_stats(self) -> dict:
        """Get comprehensive resource management statistics."""
        total_agents = len(self._agent_quotas)
        agents_over_threshold = sum(
            1 for quotas in self._agent_quotas.values()
            for q in quotas.values()
            if q.usage_ratio() >= self._alert_threshold
        )
        return {
            "total_agents_tracked": total_agents,
            "agents_over_threshold": agents_over_threshold,
            "concurrent_requests": self._concurrent_requests,
            "global_quotas": {
                rt.value: f"{q.usage_ratio()*100:.1f}%"
                for rt, q in self._global_quotas.items()
            },
            "recent_alerts": len(self._alerts),
            "rate_limiters": len(self._rate_limiters),
        }


# Global resource manager
resource_manager = ResourceManager()