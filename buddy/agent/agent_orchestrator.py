"""
Buddy Agent Orchestrator - Multi-agent coordination engine.

Coordinates multiple specialized sub-agents under a single orchestrator,
supporting parallel workstreams, tool inheritance, reviewer delegation,
and autonomous lifecycle management. Agents are treated as first-class
teammates with profiles, task assignment, and progress tracking.

Key capabilities:
- Parallel sub-agent delegation with isolated worktrees
- Cross-agent tool inheritance and capability sharing
- Reviewer agent routing for quality assurance
- Full lifecycle management: enqueue, claim, execute, complete
- Squad-based routing with leader agent delegation
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from agent.agent_protocol import ProtocolMessage, MessageType, MessagePriority


class AgentLifecycle(str, Enum):
    """Lifecycle states for an agent within the orchestration system."""
    IDLE = "idle"
    ENQUEUED = "enqueued"
    CLAIMED = "claimed"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class WorkstreamType(str, Enum):
    """Types of workstreams available for agent delegation."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    DEPLOYMENT = "deployment"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    GENERAL = "general"


@dataclass
class SubAgentProfile:
    """Profile defining a sub-agent's capabilities and configuration."""
    agent_id: str
    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    tool_set: list[str] = field(default_factory=list)
    model_id: str = "default"
    max_parallel_tasks: int = 3
    timeout_seconds: int = 300
    retry_count: int = 2
    parent_agent_id: str | None = None


@dataclass
class Workstream:
    """A discrete unit of work delegated to a sub-agent."""
    workstream_id: str
    workstream_type: WorkstreamType
    description: str
    assigned_agent_id: str | None = None
    status: AgentLifecycle = AgentLifecycle.IDLE
    priority: int = 5
    parent_workstream_id: str | None = None
    dependencies: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    reviewer_agent_id: str | None = None
    worktree_path: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    attempt_count: int = 0
    error_message: str | None = None


@dataclass
class Squad:
    """A group of agents led by a leader for stable task routing."""
    squad_id: str
    name: str
    description: str
    leader_agent_id: str
    member_agent_ids: list[str] = field(default_factory=list)
    routing_policy: str = "leader_delegated"
    active_workstreams: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class AgentOrchestrator:
    """Multi-agent orchestration engine for Buddy.

    Coordinates multiple specialized sub-agents under a single orchestrator.
    Supports parallel workstream execution, cross-agent tool inheritance,
    reviewer delegation, and squad-based routing. Agents are treated as
    first-class teammates with full lifecycle management.

    The orchestrator maintains a pool of registered sub-agents, each with
    specific capabilities and tool sets. Workstreams are dispatched to the
    most suitable agent based on capability matching and current load.
    """

    def __init__(self):
        self._agents: dict[str, SubAgentProfile] = {}
        self._workstreams: dict[str, Workstream] = {}
        self._squads: dict[str, Squad] = {}
        self._active_delegations: dict[str, list[str]] = {}
        self._tool_inheritance_map: dict[str, dict[str, list[str]]] = {}
        self._total_workstreams = 0
        self._total_completed = 0
        self._total_failed = 0
        self._register_default_agents()

    def _register_default_agents(self):
        """Register the built-in sub-agent profiles."""
        defaults = [
            SubAgentProfile(
                agent_id="buddy-coder",
                name="Buddy Coder",
                description="Specialized code generation and refactoring agent",
                capabilities=["code_generation", "refactoring", "debugging"],
                tool_set=["read_file", "write_file", "execute_command", "search_code"],
                model_id="code-model",
            ),
            SubAgentProfile(
                agent_id="buddy-reviewer",
                name="Buddy Reviewer",
                description="Code review and quality assurance agent",
                capabilities=["code_review", "security_audit", "style_check"],
                tool_set=["read_file", "search_code", "run_tests"],
                model_id="review-model",
            ),
            SubAgentProfile(
                agent_id="buddy-researcher",
                name="Buddy Researcher",
                description="Web research and information gathering agent",
                capabilities=["web_search", "data_collection", "summarization"],
                tool_set=["web_search", "fetch_url", "read_file"],
                model_id="research-model",
            ),
            SubAgentProfile(
                agent_id="buddy-analyst",
                name="Buddy Analyst",
                description="Data analysis and insight generation agent",
                capabilities=["data_analysis", "visualization", "reporting"],
                tool_set=["read_file", "execute_command", "web_search"],
                model_id="analysis-model",
            ),
            SubAgentProfile(
                agent_id="buddy-tester",
                name="Buddy Tester",
                description="Automated testing and quality assurance agent",
                capabilities=["unit_testing", "integration_testing", "e2e_testing"],
                tool_set=["read_file", "execute_command", "run_tests", "write_file"],
                model_id="test-model",
            ),
            SubAgentProfile(
                agent_id="buddy-devops",
                name="Buddy DevOps",
                description="Deployment and infrastructure management agent",
                capabilities=["deployment", "containerization", "monitoring"],
                tool_set=["execute_command", "read_file", "write_file"],
                model_id="devops-model",
            ),
        ]
        for agent in defaults:
            self._agents[agent.agent_id] = agent

    def register_agent(self, profile: SubAgentProfile) -> str:
        """Register a new sub-agent profile."""
        self._agents[profile.agent_id] = profile
        return profile.agent_id

    def remove_agent(self, agent_id: str) -> bool:
        """Remove a sub-agent profile."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> SubAgentProfile | None:
        """Get a sub-agent profile by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[SubAgentProfile]:
        """List all registered sub-agents."""
        return list(self._agents.values())

    def find_agents_by_capability(self, capability: str) -> list[SubAgentProfile]:
        """Find agents that have a specific capability."""
        return [
            a for a in self._agents.values()
            if capability in a.capabilities
        ]

    def create_workstream(
        self,
        workstream_type: WorkstreamType,
        description: str,
        priority: int = 5,
        dependencies: list[str] | None = None,
        reviewer_agent_id: str | None = None,
        parent_workstream_id: str | None = None,
    ) -> Workstream:
        """Create a new workstream for agent delegation."""
        ws_id = f"ws-{uuid.uuid4().hex[:12]}"
        ws = Workstream(
            workstream_id=ws_id,
            workstream_type=workstream_type,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            reviewer_agent_id=reviewer_agent_id,
            parent_workstream_id=parent_workstream_id,
        )
        self._workstreams[ws_id] = ws
        self._total_workstreams += 1
        return ws

    def assign_workstream(
        self,
        workstream_id: str,
        agent_id: str,
    ) -> Workstream | None:
        """Assign a workstream to a specific agent."""
        ws = self._workstreams.get(workstream_id)
        if not ws:
            return None
        if agent_id not in self._agents:
            return None

        ws.assigned_agent_id = agent_id
        ws.status = AgentLifecycle.ENQUEUED

        if agent_id not in self._active_delegations:
            self._active_delegations[agent_id] = []
        self._active_delegations[agent_id].append(workstream_id)

        return ws

    def auto_assign_workstream(self, workstream_id: str) -> Workstream | None:
        """Auto-assign a workstream to the best-matching agent."""
        ws = self._workstreams.get(workstream_id)
        if not ws:
            return None

        capability_map = {
            WorkstreamType.CODE_GENERATION: "code_generation",
            WorkstreamType.CODE_REVIEW: "code_review",
            WorkstreamType.RESEARCH: "web_search",
            WorkstreamType.ANALYSIS: "data_analysis",
            WorkstreamType.DEPLOYMENT: "deployment",
            WorkstreamType.TESTING: "unit_testing",
            WorkstreamType.DOCUMENTATION: "code_generation",
            WorkstreamType.GENERAL: "code_generation",
        }

        target_capability = capability_map.get(ws.workstream_type, "code_generation")
        candidates = self.find_agents_by_capability(target_capability)

        if not candidates:
            return None

        # Pick the agent with the fewest active workstreams
        best_agent = min(
            candidates,
            key=lambda a: len(self._active_delegations.get(a.agent_id, [])),
        )

        return self.assign_workstream(workstream_id, best_agent.agent_id)

    async def execute_workstream(
        self,
        workstream_id: str,
    ) -> Workstream | None:
        """Execute a workstream through its assigned agent (simulated)."""
        ws = self._workstreams.get(workstream_id)
        if not ws:
            return None

        if ws.status not in (AgentLifecycle.ENQUEUED, AgentLifecycle.CLAIMED):
            return None

        ws.status = AgentLifecycle.EXECUTING
        ws.attempt_count += 1

        try:
            # Simulate agent execution with a brief delay
            await asyncio.sleep(0.1)

            # Simulate successful execution
            ws.result = {
                "success": True,
                "agent_id": ws.assigned_agent_id,
                "workstream_type": ws.workstream_type.value,
                "output": f"Completed: {ws.description}",
                "execution_time_ms": 100,
                "tokens_used": 150,
            }
            ws.status = AgentLifecycle.COMPLETED
            ws.completed_at = time.time()
            self._total_completed += 1

        except Exception as e:
            ws.error_message = str(e)
            if ws.attempt_count < 3:
                ws.status = AgentLifecycle.ENQUEUED
            else:
                ws.status = AgentLifecycle.FAILED
                self._total_failed += 1

        return ws

    async def execute_workstreams_parallel(
        self,
        workstream_ids: list[str],
    ) -> list[Workstream]:
        """Execute multiple workstreams in parallel."""
        tasks = [
            self.execute_workstream(ws_id)
            for ws_id in workstream_ids
        ]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    def create_squad(
        self,
        name: str,
        description: str,
        leader_agent_id: str,
        member_agent_ids: list[str],
    ) -> Squad | None:
        """Create a squad with a leader agent for stable routing."""
        if leader_agent_id not in self._agents:
            return None
        for mid in member_agent_ids:
            if mid not in self._agents:
                return None

        squad_id = f"squad-{uuid.uuid4().hex[:12]}"
        squad = Squad(
            squad_id=squad_id,
            name=name,
            description=description,
            leader_agent_id=leader_agent_id,
            member_agent_ids=member_agent_ids,
        )
        self._squads[squad_id] = squad
        return squad

    def route_to_squad(self, squad_id: str, workstream_id: str) -> bool:
        """Route a workstream to a squad for leader-based delegation."""
        squad = self._squads.get(squad_id)
        ws = self._workstreams.get(workstream_id)
        if not squad or not ws:
            return False

        # Leader agent decides which member to assign to
        # Simple strategy: round-robin among members
        members = squad.member_agent_ids
        if not members:
            return False

        active_counts = {
            mid: len(self._active_delegations.get(mid, []))
            for mid in members
        }
        best_member = min(members, key=lambda m: active_counts.get(m, 0))

        ws.assigned_agent_id = best_member
        ws.status = AgentLifecycle.ENQUEUED
        squad.active_workstreams.append(workstream_id)

        if best_member not in self._active_delegations:
            self._active_delegations[best_member] = []
        self._active_delegations[best_member].append(workstream_id)

        return True

    def inherit_tools(
        self,
        parent_agent_id: str,
        child_agent_id: str,
        tools: list[str],
    ) -> bool:
        """Grant tool inheritance from parent to child agent."""
        if parent_agent_id not in self._agents:
            return False
        if child_agent_id not in self._agents:
            return False

        parent = self._agents[parent_agent_id]
        child = self._agents[child_agent_id]

        inheritable = [t for t in tools if t in parent.tool_set]
        child.tool_set = list(set(child.tool_set + inheritable))

        if parent_agent_id not in self._tool_inheritance_map:
            self._tool_inheritance_map[parent_agent_id] = {}
        self._tool_inheritance_map[parent_agent_id][child_agent_id] = inheritable

        return True

    def set_reviewer(self, workstream_id: str, reviewer_agent_id: str) -> bool:
        """Set a reviewer agent for a workstream for quality assurance."""
        ws = self._workstreams.get(workstream_id)
        if not ws:
            return False
        if reviewer_agent_id not in self._agents:
            return False
        ws.reviewer_agent_id = reviewer_agent_id
        return True

    def get_workstream(self, workstream_id: str) -> Workstream | None:
        """Get a workstream by ID."""
        return self._workstreams.get(workstream_id)

    def list_workstreams(
        self,
        status: AgentLifecycle | None = None,
    ) -> list[Workstream]:
        """List workstreams, optionally filtered by status."""
        wss = list(self._workstreams.values())
        if status:
            wss = [ws for ws in wss if ws.status == status]
        return wss

    def get_agent_load(self, agent_id: str) -> int:
        """Get the current load (active workstreams) for an agent."""
        return len(self._active_delegations.get(agent_id, []))

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "total_agents": len(self._agents),
            "total_workstreams": self._total_workstreams,
            "total_completed": self._total_completed,
            "total_failed": self._total_failed,
            "active_workstreams": len([
                ws for ws in self._workstreams.values()
                if ws.status in (AgentLifecycle.ENQUEUED, AgentLifecycle.CLAIMED, AgentLifecycle.EXECUTING)
            ]),
            "total_squads": len(self._squads),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "capabilities": a.capabilities,
                    "current_load": self.get_agent_load(a.agent_id),
                    "tool_count": len(a.tool_set),
                }
                for a in self._agents.values()
            ],
            "squads": [
                {
                    "squad_id": s.squad_id,
                    "name": s.name,
                    "leader_id": s.leader_agent_id,
                    "member_count": len(s.member_agent_ids),
                    "active_workstreams": len(s.active_workstreams),
                }
                for s in self._squads.values()
            ],
            "workstreams_by_status": {
                status.value: len([
                    ws for ws in self._workstreams.values()
                    if ws.status == status
                ])
                for status in AgentLifecycle
            },
        }


# Singleton instance
agent_orchestrator = AgentOrchestrator()