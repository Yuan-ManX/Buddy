"""
Buddy Agent Fleet Manager - Multi-agent fleet orchestration.

Manages a fleet of agents as a coordinated system with health monitoring,
load balancing, dynamic scaling, and failover capabilities. Treats agents
as distributed computing resources with lifecycle management.

Key capabilities:
- Fleet-wide health monitoring and heartbeat tracking
- Dynamic load balancing across agent instances
- Automatic failover and recovery
- Resource allocation and quota management
- Fleet-level analytics and performance tracking
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FleetAgentStatus(str, Enum):
    """Status of an agent within the fleet."""
    ONLINE = "online"
    BUSY = "busy"
    IDLE = "idle"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RECOVERING = "recovering"
    DRAINING = "draining"


class FleetHealth(str, Enum):
    """Overall fleet health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class FleetAgent:
    """An agent registered in the fleet."""
    agent_id: str
    agent_name: str
    role: str
    status: FleetAgentStatus = FleetAgentStatus.OFFLINE
    current_load: int = 0
    max_concurrent: int = 5
    health_score: float = 1.0
    last_heartbeat: float = field(default_factory=time.time)
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    avg_response_time_ms: float = 0.0
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        total = self.total_tasks_completed + self.total_tasks_failed
        if total == 0:
            return 1.0
        return self.total_tasks_completed / total

    @property
    def is_available(self) -> bool:
        return (
            self.status in (FleetAgentStatus.ONLINE, FleetAgentStatus.IDLE)
            and self.current_load < self.max_concurrent
            and self.health_score > 0.3
        )


@dataclass
class FleetLoadReport:
    """Load distribution report for the fleet."""
    total_agents: int
    available_agents: int
    total_load: int
    total_capacity: int
    load_percentage: float
    agent_loads: dict[str, int]
    recommended_actions: list[str]


@dataclass
class FleetHealthReport:
    """Health status report for the fleet."""
    overall_health: FleetHealth
    agent_count: int
    healthy_count: int
    degraded_count: int
    offline_count: int
    average_health_score: float
    agent_statuses: dict[str, FleetAgentStatus]
    issues: list[str]
    recommendations: list[str]


class AgentFleetManager:
    """Fleet management system for Buddy agents.

    Orchestrates a fleet of agents with health monitoring, load balancing,
    and dynamic resource allocation. Provides fleet-level visibility and
    automated recovery mechanisms.
    """

    def __init__(self):
        self._agents: dict[str, FleetAgent] = {}
        self._heartbeat_timeout: float = 30.0  # seconds
        self._health_check_interval: float = 10.0
        self._max_agents_per_fleet: int = 100
        self._total_tasks_processed: int = 0

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        role: str,
        capabilities: list[str] | None = None,
        max_concurrent: int = 5,
        tags: list[str] | None = None,
    ) -> FleetAgent:
        """Register a new agent in the fleet."""
        if len(self._agents) >= self._max_agents_per_fleet:
            raise RuntimeError("Fleet capacity reached")

        agent = FleetAgent(
            agent_id=agent_id,
            agent_name=agent_name,
            role=role,
            status=FleetAgentStatus.ONLINE,
            max_concurrent=max_concurrent,
            capabilities=capabilities or [],
            tags=tags or [],
        )
        self._agents[agent_id] = agent
        return agent

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the fleet."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def heartbeat(self, agent_id: str, load: int = 0) -> bool:
        """Record a heartbeat from an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        agent.last_heartbeat = time.time()
        agent.current_load = load

        if agent.status == FleetAgentStatus.OFFLINE:
            agent.status = FleetAgentStatus.RECOVERING
        elif agent.status == FleetAgentStatus.RECOVERING:
            agent.status = FleetAgentStatus.ONLINE

        if load >= agent.max_concurrent:
            agent.status = FleetAgentStatus.BUSY
        elif load == 0 and agent.status == FleetAgentStatus.BUSY:
            agent.status = FleetAgentStatus.IDLE

        return True

    def update_health(
        self,
        agent_id: str,
        health_score: float,
        status: FleetAgentStatus | None = None,
    ) -> bool:
        """Update the health status of an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        agent.health_score = max(0.0, min(1.0, health_score))
        if status:
            agent.status = status
        elif agent.health_score < 0.3:
            agent.status = FleetAgentStatus.DEGRADED

        return True

    def record_task_completion(
        self,
        agent_id: str,
        success: bool,
        response_time_ms: float = 0.0,
    ) -> bool:
        """Record a task completion for an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        if success:
            agent.total_tasks_completed += 1
        else:
            agent.total_tasks_failed += 1

        # Update average response time with EMA
        if agent.avg_response_time_ms == 0:
            agent.avg_response_time_ms = response_time_ms
        else:
            agent.avg_response_time_ms = (
                agent.avg_response_time_ms * 0.9 + response_time_ms * 0.1
            )

        agent.current_load = max(0, agent.current_load - 1)
        self._total_tasks_processed += 1
        return True

    def assign_task(
        self,
        required_capabilities: list[str] | None = None,
        preferred_tags: list[str] | None = None,
        exclude_agents: list[str] | None = None,
    ) -> FleetAgent | None:
        """Assign a task to the best available agent using load-balanced selection."""
        exclude = set(exclude_agents or [])
        candidates = [
            a for a in self._agents.values()
            if a.is_available and a.agent_id not in exclude
        ]

        if not candidates:
            return None

        # Filter by capabilities
        if required_capabilities:
            candidates = [
                a for a in candidates
                if all(c in a.capabilities for c in required_capabilities)
            ]
            if not candidates:
                return None

        # Filter by preferred tags
        if preferred_tags:
            tagged = [a for a in candidates if any(t in a.tags for t in preferred_tags)]
            if tagged:
                candidates = tagged

        # Select agent with lowest load (round-robin weighted by capacity)
        candidates.sort(key=lambda a: (
            a.current_load / max(a.max_concurrent, 1),
            -a.health_score,
        ))

        selected = candidates[0]
        selected.current_load += 1
        if selected.current_load >= selected.max_concurrent:
            selected.status = FleetAgentStatus.BUSY

        return selected

    def get_load_report(self) -> FleetLoadReport:
        """Generate a load distribution report."""
        total_load = sum(a.current_load for a in self._agents.values())
        total_capacity = sum(a.max_concurrent for a in self._agents.values())
        available = sum(1 for a in self._agents.values() if a.is_available)

        actions = []
        if total_load > total_capacity * 0.8:
            actions.append("Scale up: fleet near capacity")
        if available < 2:
            actions.append("Low availability: consider adding agents")

        return FleetLoadReport(
            total_agents=len(self._agents),
            available_agents=available,
            total_load=total_load,
            total_capacity=total_capacity,
            load_percentage=round(total_load / max(total_capacity, 1) * 100, 1),
            agent_loads={aid: a.current_load for aid, a in self._agents.items()},
            recommended_actions=actions,
        )

    def get_health_report(self) -> FleetHealthReport:
        """Generate a fleet health report."""
        self._check_timeouts()

        healthy = sum(
            1 for a in self._agents.values()
            if a.status in (FleetAgentStatus.ONLINE, FleetAgentStatus.IDLE, FleetAgentStatus.BUSY)
        )
        degraded = sum(
            1 for a in self._agents.values()
            if a.status == FleetAgentStatus.DEGRADED
        )
        offline = sum(
            1 for a in self._agents.values()
            if a.status == FleetAgentStatus.OFFLINE
        )

        avg_health = (
            sum(a.health_score for a in self._agents.values()) / len(self._agents)
            if self._agents else 0.0
        )

        # Determine overall health
        if offline > len(self._agents) * 0.5:
            overall = FleetHealth.CRITICAL
        elif degraded > 0 or offline > 0:
            overall = FleetHealth.DEGRADED
        elif len(self._agents) == 0:
            overall = FleetHealth.OFFLINE
        else:
            overall = FleetHealth.HEALTHY

        issues = []
        recommendations = []
        if offline > 0:
            issues.append(f"{offline} agents offline")
            recommendations.append("Restart offline agents")
        if degraded > 0:
            issues.append(f"{degraded} agents degraded")
            recommendations.append("Investigate degraded agent health")

        return FleetHealthReport(
            overall_health=overall,
            agent_count=len(self._agents),
            healthy_count=healthy,
            degraded_count=degraded,
            offline_count=offline,
            average_health_score=round(avg_health, 3),
            agent_statuses={aid: a.status for aid, a in self._agents.items()},
            issues=issues,
            recommendations=recommendations,
        )

    def get_agent(self, agent_id: str) -> FleetAgent | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def get_all_agents(self) -> list[FleetAgent]:
        """Get all registered agents."""
        return list(self._agents.values())

    def get_stats(self) -> dict:
        """Get fleet statistics."""
        report = self.get_health_report()
        load = self.get_load_report()
        return {
            "total_agents": len(self._agents),
            "overall_health": report.overall_health.value,
            "healthy_agents": report.healthy_count,
            "degraded_agents": report.degraded_count,
            "offline_agents": report.offline_count,
            "average_health_score": report.average_health_score,
            "total_tasks_processed": self._total_tasks_processed,
            "total_load": load.total_load,
            "total_capacity": load.total_capacity,
            "load_percentage": load.load_percentage,
            "available_agents": load.available_agents,
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "agent_name": a.agent_name,
                    "role": a.role,
                    "status": a.status.value,
                    "current_load": a.current_load,
                    "health_score": a.health_score,
                    "success_rate": round(a.success_rate, 3),
                    "avg_response_time_ms": round(a.avg_response_time_ms, 1),
                    "capabilities": a.capabilities,
                }
                for a in self._agents.values()
            ],
            "issues": report.issues,
            "recommendations": report.recommendations,
        }

    def _check_timeouts(self) -> None:
        """Check for agent heartbeat timeouts and mark offline."""
        now = time.time()
        for agent in self._agents.values():
            if agent.status != FleetAgentStatus.OFFLINE:
                if now - agent.last_heartbeat > self._heartbeat_timeout:
                    agent.status = FleetAgentStatus.OFFLINE
                    agent.health_score = max(0.0, agent.health_score - 0.2)


# Global singleton
fleet_manager = AgentFleetManager()