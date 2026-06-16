"""Buddy Agent Discovery — automatic capability and service registration

Provides a service discovery layer where agents can register their capabilities,
discover other agents' services, and dynamically form collaboration networks.
Enables decentralized agent coordination without hard-coded dependencies.

Core capabilities:
  - Capability Registration: agents declare what they can do
  - Service Discovery: find agents by capability, role, or expertise
  - Health Monitoring: periodic health checks with heartbeat
  - Dynamic Networking: agents discover and connect to peers automatically
  - Load-aware Discovery: route requests to least-loaded capable agents
  - Capability Evolution: agents update capabilities as they learn
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.discovery")


class AgentCapability(str, Enum):
    """Well-known agent capabilities for discovery."""
    CHAT = "chat"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DATA_ANALYSIS = "data_analysis"
    RESEARCH = "research"
    WRITING = "writing"
    PLANNING = "planning"
    TOOL_EXECUTION = "tool_execution"
    WEB_SEARCH = "web_search"
    FILE_OPERATIONS = "file_operations"
    SCHEDULING = "scheduling"
    MONITORING = "monitoring"
    COORDINATION = "coordination"
    REASONING = "reasoning"
    CREATIVE = "creative"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


@dataclass
class AgentRegistration:
    """Registration record for an agent in the discovery service."""
    agent_id: str
    agent_name: str
    capabilities: list[str] = field(default_factory=list)
    expertise_domains: list[str] = field(default_factory=list)
    model: str = ""
    max_concurrency: int = 5
    current_load: int = 0
    status: str = "active"  # active, idle, busy, offline
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    heartbeat_interval: int = 30  # seconds
    metadata: dict = field(default_factory=dict)
    score: float = 0.5  # quality/reliability score

    def is_healthy(self) -> bool:
        """Check if agent is considered healthy based on heartbeat."""
        last = datetime.fromisoformat(self.last_heartbeat)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed < self.heartbeat_interval * 3 and self.status != "offline"

    def availability(self) -> float:
        """Calculate availability score (0.0 to 1.0)."""
        if self.max_concurrency == 0:
            return 0.0
        return max(0.0, 1.0 - (self.current_load / self.max_concurrency))


class AgentDiscoveryService:
    """Decentralized agent discovery and capability registry.

    Agents register their capabilities and the service provides lookup
    by capability, role, expertise domain, or availability. Supports
    health monitoring through periodic heartbeats.
    """

    HEARTBEAT_TIMEOUT = 90  # seconds before marking agent as offline
    CLEANUP_INTERVAL = 60   # seconds between cleanup cycles

    def __init__(self):
        self._registry: dict[str, AgentRegistration] = {}
        self._capability_index: dict[str, set[str]] = defaultdict(set)
        self._domain_index: dict[str, set[str]] = defaultdict(set)
        self._cleanup_task: asyncio.Task | None = None
        self._is_running: bool = False
        self._discovery_hooks: list[callable] = []

    def register(self, registration: AgentRegistration) -> str:
        """Register an agent with its capabilities."""
        agent_id = registration.agent_id

        # Update indices
        old_reg = self._registry.get(agent_id)
        if old_reg:
            self._remove_from_indices(old_reg)

        self._registry[agent_id] = registration
        self._add_to_indices(registration)

        logger.info(
            f"Agent registered: {registration.agent_name} "
            f"({len(registration.capabilities)} capabilities)"
        )
        return agent_id

    def unregister(self, agent_id: str):
        """Remove an agent from the registry."""
        reg = self._registry.pop(agent_id, None)
        if reg:
            self._remove_from_indices(reg)
            logger.info(f"Agent unregistered: {agent_id}")

    def heartbeat(self, agent_id: str) -> bool:
        """Record a heartbeat from an agent, keeping it marked as healthy."""
        reg = self._registry.get(agent_id)
        if not reg:
            return False
        reg.last_heartbeat = datetime.now(timezone.utc).isoformat()
        if reg.status == "offline":
            reg.status = "active"
        return True

    def update_load(self, agent_id: str, load: int):
        """Update the current load of an agent."""
        reg = self._registry.get(agent_id)
        if reg:
            reg.current_load = max(0, min(load, reg.max_concurrency))

    def update_capabilities(self, agent_id: str, capabilities: list[str]):
        """Update an agent's capability list."""
        reg = self._registry.get(agent_id)
        if reg:
            self._remove_from_indices(reg)
            reg.capabilities = capabilities
            self._add_to_indices(reg)
            logger.debug(f"Updated capabilities for {agent_id}: {capabilities}")

    def update_score(self, agent_id: str, score: float):
        """Update agent quality/reliability score."""
        reg = self._registry.get(agent_id)
        if reg:
            reg.score = max(0.0, min(1.0, score))

    def discover_by_capability(
        self,
        capability: str,
        min_score: float = 0.3,
        exclude_ids: list[str] | None = None,
    ) -> list[AgentRegistration]:
        """Find agents with a specific capability."""
        exclude = set(exclude_ids or [])
        agent_ids = self._capability_index.get(capability, set())
        return [
            self._registry[aid]
            for aid in agent_ids
            if aid in self._registry
            and self._registry[aid].score >= min_score
            and aid not in exclude
            and self._registry[aid].is_healthy()
        ]

    def discover_by_domain(
        self,
        domain: str,
        min_score: float = 0.3,
    ) -> list[AgentRegistration]:
        """Find agents with expertise in a specific domain."""
        agent_ids = self._domain_index.get(domain, set())
        return [
            self._registry[aid]
            for aid in agent_ids
            if aid in self._registry
            and self._registry[aid].score >= min_score
            and self._registry[aid].is_healthy()
        ]

    def discover_by_name(self, query: str) -> list[AgentRegistration]:
        """Find agents by partial name match."""
        query_lower = query.lower()
        return [
            reg for reg in self._registry.values()
            if query_lower in reg.agent_name.lower() and reg.is_healthy()
        ]

    def discover_best_agent(
        self,
        capability: str,
        strategy: str = "balanced",
    ) -> AgentRegistration | None:
        """Find the best agent for a capability using the specified strategy.

        Strategies:
          - balanced: balance between score and availability
          - fastest: highest availability (least loaded)
          - best_quality: highest quality score
          - least_loaded: lowest current load
        """
        candidates = self.discover_by_capability(capability)
        if not candidates:
            return None

        if strategy == "fastest" or strategy == "least_loaded":
            return min(candidates, key=lambda a: a.current_load)
        elif strategy == "best_quality":
            return max(candidates, key=lambda a: a.score)
        else:  # balanced
            return max(candidates, key=lambda a: a.score * a.availability())

    def discover_by_multiple_capabilities(
        self,
        capabilities: list[str],
        require_all: bool = False,
    ) -> list[AgentRegistration]:
        """Find agents matching multiple capabilities."""
        if not capabilities:
            return []

        if require_all:
            agent_sets = [self._capability_index.get(c, set()) for c in capabilities]
            common_agents = agent_sets[0].intersection(*agent_sets[1:]) if agent_sets else set()
            return [
                self._registry[aid] for aid in common_agents
                if aid in self._registry and self._registry[aid].is_healthy()
            ]
        else:
            all_agents = set()
            for cap in capabilities:
                all_agents.update(self._capability_index.get(cap, set()))
            # Rank by number of matching capabilities
            scored = []
            for aid in all_agents:
                if aid not in self._registry or not self._registry[aid].is_healthy():
                    continue
                reg = self._registry[aid]
                matches = sum(1 for c in capabilities if c in reg.capabilities)
                scored.append((matches, reg))
            scored.sort(key=lambda x: -x[0])
            return [reg for _, reg in scored]

    def list_all_agents(self) -> list[AgentRegistration]:
        """List all registered agents."""
        return list(self._registry.values())

    def list_healthy_agents(self) -> list[AgentRegistration]:
        """List all healthy agents."""
        return [reg for reg in self._registry.values() if reg.is_healthy()]

    def list_offline_agents(self) -> list[AgentRegistration]:
        """List agents considered offline."""
        return [reg for reg in self._registry.values() if not reg.is_healthy()]

    def list_capabilities(self) -> list[dict]:
        """List all registered capabilities with agent counts."""
        return [
            {"capability": cap, "agent_count": len(agents)}
            for cap, agents in sorted(self._capability_index.items())
        ]

    def on_discovery(self, hook: callable):
        """Register a hook called when a new agent is discovered."""
        self._discovery_hooks.append(hook)

    async def start_cleanup(self):
        """Start periodic cleanup of offline agents."""
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Agent discovery cleanup started")

    async def stop_cleanup(self):
        """Stop the cleanup loop."""
        self._is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self):
        """Periodically mark agents without recent heartbeats as offline."""
        while self._is_running:
            try:
                now = datetime.now(timezone.utc)
                for agent_id, reg in list(self._registry.items()):
                    last_hb = datetime.fromisoformat(reg.last_heartbeat)
                    if (now - last_hb).total_seconds() > self.HEARTBEAT_TIMEOUT:
                        if reg.status != "offline":
                            reg.status = "offline"
                            logger.info(f"Agent marked offline: {agent_id} ({reg.agent_name})")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

            await asyncio.sleep(self.CLEANUP_INTERVAL)

    def _add_to_indices(self, reg: AgentRegistration):
        """Add an agent to all capability and domain indices."""
        for cap in reg.capabilities:
            self._capability_index[cap].add(reg.agent_id)
        for domain in reg.expertise_domains:
            self._domain_index[domain].add(reg.agent_id)

    def _remove_from_indices(self, reg: AgentRegistration):
        """Remove an agent from all indices."""
        for cap in reg.capabilities:
            self._capability_index[cap].discard(reg.agent_id)
        for domain in reg.expertise_domains:
            self._domain_index[domain].discard(reg.agent_id)

        # Clean up empty index entries
        for cap in list(self._capability_index.keys()):
            if not self._capability_index[cap]:
                del self._capability_index[cap]
        for domain in list(self._domain_index.keys()):
            if not self._domain_index[domain]:
                del self._domain_index[domain]

    def get_stats(self) -> dict:
        """Get comprehensive discovery service statistics."""
        healthy = self.list_healthy_agents()
        offline = self.list_offline_agents()
        return {
            "total_registered": len(self._registry),
            "healthy_agents": len(healthy),
            "offline_agents": len(offline),
            "total_capabilities": len(self._capability_index),
            "total_domains": len(self._domain_index),
            "agents": [
                {
                    "id": reg.agent_id,
                    "name": reg.agent_name,
                    "capabilities": reg.capabilities,
                    "status": reg.status,
                    "score": reg.score,
                    "availability": reg.availability(),
                    "load": f"{reg.current_load}/{reg.max_concurrency}",
                }
                for reg in healthy[:20]
            ],
        }

    def get_agent_info(self, agent_id: str) -> dict | None:
        """Get detailed information about a registered agent."""
        reg = self._registry.get(agent_id)
        if not reg:
            return None
        return {
            "agent_id": reg.agent_id,
            "agent_name": reg.agent_name,
            "capabilities": reg.capabilities,
            "expertise_domains": reg.expertise_domains,
            "model": reg.model,
            "status": reg.status,
            "score": reg.score,
            "availability": reg.availability(),
            "current_load": reg.current_load,
            "max_concurrency": reg.max_concurrency,
            "last_heartbeat": reg.last_heartbeat,
            "registered_at": reg.registered_at,
            "metadata": reg.metadata,
        }


# Global discovery service
agent_discovery = AgentDiscoveryService()