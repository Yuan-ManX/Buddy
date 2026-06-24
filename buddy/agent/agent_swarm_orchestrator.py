"""Buddy Swarm Orchestrator — AI-native swarm intelligence orchestration system.

Provides a comprehensive swarm intelligence framework for the Buddy platform,
enabling dynamic agent swarm formation, multi-strategy consensus mechanisms,
parallel task execution, emergent behavior detection, and continuous swarm
optimization.

Core capabilities:
  - Dynamic swarm formation based on task requirements and capability matching
  - Multi-strategy consensus: majority, weighted, ranked choice, delegated, supermajority, unanimous
  - Swarm task decomposition with dependency-aware parallel execution
  - Intelligent role assignment with capability-based scoring
  - Swarm health monitoring and auto-recovery mechanisms
  - Result aggregation and cross-agent synthesis
  - Emergent behavior detection and pattern recognition
  - Swarm composition optimization through role rotation and performance analysis
  - Simulation mode with diverse agent perspectives when real agents are unavailable
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.swarm_orchestrator")


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════

class SwarmRole(str, Enum):
    """Specialized roles within a swarm intelligence system."""
    LEADER = "leader"           # Directs swarm strategy and resolves deadlocks
    CRITIC = "critic"           # Challenges assumptions and identifies flaws
    EXECUTOR = "executor"       # Implements tasks and produces concrete outputs
    VERIFIER = "verifier"       # Validates results and ensures correctness
    SYNTHESIZER = "synthesizer" # Combines multiple outputs into coherent results
    EXPLORER = "explorer"       # Investigates alternatives and gathers information
    MEDIATOR = "mediator"       # Resolves conflicts and facilitates collaboration
    SPECIALIST = "specialist"   # Provides domain-specific deep expertise


class ConsensusMethod(str, Enum):
    """Methods for reaching consensus within a swarm."""
    MAJORITY = "majority"           # Simple majority vote (>50%)
    WEIGHTED = "weighted"           # Weighted vote based on agent confidence/performance
    RANKED_CHOICE = "ranked_choice" # Ranked choice voting with elimination rounds
    DELEGATED = "delegated"         # Delegate decision to the most qualified agent
    SUPERMAJORITY = "supermajority" # Requires >= 2/3 majority for consensus
    UNANIMOUS = "unanimous"         # Requires full agreement from all voting members


class SwarmState(str, Enum):
    """Tuckman's stages of group development adapted for AI swarms."""
    FORMING = "forming"         # Swarm is being assembled and roles assigned
    STORMING = "storming"       # Members negotiate approaches and resolve conflicts
    NORMING = "norming"         # Consensus on approach, cohesive workflow established
    PERFORMING = "performing"   # High-efficiency parallel execution
    ADJOURNING = "adjourning"   # Swarm is dissolving, results archived


class TaskStatus(str, Enum):
    """Status of a task within the swarm."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class MemberStatus(str, Enum):
    """Operational status of a swarm member."""
    IDLE = "idle"
    WORKING = "working"
    DONE = "done"
    FAILED = "failed"
    RECOVERING = "recovering"
    OFFLINE = "offline"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SwarmMember:
    """A member of a swarm with role, capabilities, and performance tracking."""
    agent_id: str
    role: SwarmRole
    capabilities: list[str] = field(default_factory=list)
    weight: float = 1.0
    status: MemberStatus = MemberStatus.IDLE
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_count: int = 0
    success_rate: float = 1.0
    total_contributions: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    specialization_score: dict[str, float] = field(default_factory=dict)
    consensus_participation: int = 0
    emergent_contributions: list[str] = field(default_factory=list)

    def update_success(self, success: bool) -> None:
        """Update success rate after a task completion."""
        self.task_count += 1
        total = self.task_count
        if total == 0:
            self.success_rate = 1.0
        else:
            # Exponential moving average of success
            self.success_rate = self.success_rate * 0.9 + (1.0 if success else 0.0) * 0.1

    def record_heartbeat(self) -> None:
        """Record a heartbeat to show the member is active."""
        self.last_heartbeat = time.time()

    @property
    def is_available(self) -> bool:
        """Check if the member is available for task assignment."""
        return self.status in (MemberStatus.IDLE, MemberStatus.DONE)


@dataclass
class SwarmTask:
    """A task to be executed by the swarm."""
    task_id: str
    description: str
    complexity: float = 0.5
    required_capabilities: list[str] = field(default_factory=list)
    assigned_to: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    priority: int = 5
    dependencies: list[str] = field(default_factory=list)
    subtasks: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """The result of a consensus decision within a swarm."""
    decision: str
    confidence: float
    method: ConsensusMethod
    votes: dict[str, str] = field(default_factory=dict)
    dissenting_opinions: list[str] = field(default_factory=list)
    rounds_taken: int = 1
    vote_distribution: dict[str, int] = field(default_factory=dict)
    reached_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    deliberation_log: list[str] = field(default_factory=list)


@dataclass
class SwarmSession:
    """An active swarm intelligence collaboration session."""
    session_id: str
    topic: str
    members: list[SwarmMember] = field(default_factory=list)
    tasks: list[SwarmTask] = field(default_factory=list)
    consensus_history: list[ConsensusResult] = field(default_factory=list)
    state: SwarmState = SwarmState.FORMING
    formed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: dict[str, Any] = field(default_factory=dict)
    completed_at: str | None = None
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_consensus_rounds: int = 0
    emergent_patterns_detected: int = 0
    simulation_mode: bool = False


@dataclass
class EmergentPattern:
    """A detected emergent behavior pattern from swarm interactions."""
    pattern_id: str
    pattern_type: str
    description: str
    confidence: float
    occurrences: int = 1
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    contributing_members: list[str] = field(default_factory=list)
    related_consensus: list[str] = field(default_factory=list)
    impact_score: float = 0.0


# ═══════════════════════════════════════════════════════════════════
# Simulated Agent Profiles
# ═══════════════════════════════════════════════════════════════════

SIMULATED_AGENT_PROFILES: list[dict[str, Any]] = [
    {
        "agent_id": "sim-agent-alpha",
        "name": "Alpha",
        "capabilities": ["reasoning", "analysis", "strategy", "planning", "architecture"],
        "base_weight": 0.92,
        "persona": "analytical",
        "response_style": "precise and structured",
    },
    {
        "agent_id": "sim-agent-beta",
        "name": "Beta",
        "capabilities": ["code_generation", "implementation", "debugging", "testing", "optimization"],
        "base_weight": 0.88,
        "persona": "pragmatic",
        "response_style": "concise and action-oriented",
    },
    {
        "agent_id": "sim-agent-gamma",
        "name": "Gamma",
        "capabilities": ["research", "information_retrieval", "data_analysis", "summarization", "trend_analysis"],
        "base_weight": 0.85,
        "persona": "curious",
        "response_style": "thorough and exploratory",
    },
    {
        "agent_id": "sim-agent-delta",
        "name": "Delta",
        "capabilities": ["review", "validation", "security", "compliance", "quality_assurance"],
        "base_weight": 0.90,
        "persona": "cautious",
        "response_style": "critical and detail-oriented",
    },
    {
        "agent_id": "sim-agent-epsilon",
        "name": "Epsilon",
        "capabilities": ["creative_design", "ideation", "innovation", "brainstorming", "prototyping"],
        "base_weight": 0.82,
        "persona": "creative",
        "response_style": "imaginative and divergent",
    },
    {
        "agent_id": "sim-agent-zeta",
        "name": "Zeta",
        "capabilities": ["coordination", "facilitation", "conflict_resolution", "synthesis", "delegation"],
        "base_weight": 0.87,
        "persona": "diplomatic",
        "response_style": "balanced and integrative",
    },
    {
        "agent_id": "sim-agent-eta",
        "name": "Eta",
        "capabilities": ["data_science", "statistics", "modeling", "visualization", "prediction"],
        "base_weight": 0.86,
        "persona": "empirical",
        "response_style": "data-driven and quantitative",
    },
    {
        "agent_id": "sim-agent-theta",
        "name": "Theta",
        "capabilities": ["writing", "documentation", "communication", "explanation", "translation"],
        "base_weight": 0.83,
        "persona": "articulate",
        "response_style": "clear and narrative",
    },
]

CAPABILITY_TO_ROLE_MAP: dict[str, list[SwarmRole]] = {
    "reasoning": [SwarmRole.LEADER, SwarmRole.CRITIC],
    "analysis": [SwarmRole.CRITIC, SwarmRole.VERIFIER],
    "strategy": [SwarmRole.LEADER, SwarmRole.MEDIATOR],
    "planning": [SwarmRole.LEADER, SwarmRole.EXECUTOR],
    "architecture": [SwarmRole.LEADER, SwarmRole.SPECIALIST],
    "code_generation": [SwarmRole.EXECUTOR, SwarmRole.SPECIALIST],
    "implementation": [SwarmRole.EXECUTOR],
    "debugging": [SwarmRole.EXECUTOR, SwarmRole.VERIFIER],
    "testing": [SwarmRole.VERIFIER, SwarmRole.EXECUTOR],
    "optimization": [SwarmRole.SPECIALIST, SwarmRole.EXECUTOR],
    "research": [SwarmRole.EXPLORER, SwarmRole.SPECIALIST],
    "information_retrieval": [SwarmRole.EXPLORER],
    "data_analysis": [SwarmRole.EXPLORER, SwarmRole.VERIFIER],
    "summarization": [SwarmRole.SYNTHESIZER],
    "trend_analysis": [SwarmRole.EXPLORER, SwarmRole.LEADER],
    "review": [SwarmRole.VERIFIER, SwarmRole.CRITIC],
    "validation": [SwarmRole.VERIFIER],
    "security": [SwarmRole.CRITIC, SwarmRole.SPECIALIST],
    "compliance": [SwarmRole.VERIFIER, SwarmRole.CRITIC],
    "quality_assurance": [SwarmRole.VERIFIER],
    "creative_design": [SwarmRole.EXPLORER, SwarmRole.SPECIALIST],
    "ideation": [SwarmRole.EXPLORER],
    "innovation": [SwarmRole.EXPLORER, SwarmRole.LEADER],
    "brainstorming": [SwarmRole.EXPLORER],
    "prototyping": [SwarmRole.EXECUTOR, SwarmRole.EXPLORER],
    "coordination": [SwarmRole.LEADER, SwarmRole.MEDIATOR],
    "facilitation": [SwarmRole.MEDIATOR, SwarmRole.LEADER],
    "conflict_resolution": [SwarmRole.MEDIATOR],
    "synthesis": [SwarmRole.SYNTHESIZER],
    "delegation": [SwarmRole.LEADER],
    "data_science": [SwarmRole.SPECIALIST, SwarmRole.EXPLORER],
    "statistics": [SwarmRole.SPECIALIST, SwarmRole.VERIFIER],
    "modeling": [SwarmRole.SPECIALIST, SwarmRole.EXECUTOR],
    "visualization": [SwarmRole.EXECUTOR, SwarmRole.SYNTHESIZER],
    "prediction": [SwarmRole.SPECIALIST, SwarmRole.LEADER],
    "writing": [SwarmRole.SYNTHESIZER, SwarmRole.EXECUTOR],
    "documentation": [SwarmRole.SYNTHESIZER],
    "communication": [SwarmRole.MEDIATOR, SwarmRole.SYNTHESIZER],
    "explanation": [SwarmRole.SYNTHESIZER, SwarmRole.MEDIATOR],
    "translation": [SwarmRole.SPECIALIST, SwarmRole.SYNTHESIZER],
}


# ═══════════════════════════════════════════════════════════════════
# SwarmOrchestrator
# ═══════════════════════════════════════════════════════════════════

class SwarmOrchestrator:
    """AI-native swarm intelligence orchestration system for the Buddy platform.

    Orchestrates dynamic agent swarms with intelligent role assignment,
    multi-strategy consensus, parallel task execution, emergent behavior
    detection, and continuous performance optimization.

    When no real agents are available, falls back to simulation mode with
    diverse simulated agent profiles that generate realistic responses.
    """

    # Configuration constants
    DEFAULT_MIN_MEMBERS = 3
    DEFAULT_MAX_MEMBERS = 8
    MAX_PARALLEL_TASKS = 10
    HEALTH_CHECK_INTERVAL = 30.0  # seconds
    MEMBER_TIMEOUT = 120.0  # seconds
    EMERGENCE_DETECTION_THRESHOLD = 3  # occurrences before pattern recognized
    ROLE_ROTATION_INTERVAL = 5  # tasks before considering rotation

    def __init__(self):
        self._sessions: dict[str, SwarmSession] = {}
        self._emergent_patterns: dict[str, list[EmergentPattern]] = {}
        self._global_metrics: dict[str, Any] = {
            "total_swarms_formed": 0,
            "total_tasks_executed": 0,
            "total_consensus_rounds": 0,
            "emergent_patterns_detected": 0,
            "swarms_active": 0,
            "average_swarm_size": 0.0,
            "average_consensus_confidence": 0.0,
            "simulation_sessions": 0,
        }
        self._agent_registry: dict[str, dict[str, Any]] = {}
        self._chat_executors: dict[str, Callable[[str, str], Awaitable[str]]] = {}
        self._simulation_enabled: bool = True
        self._running: bool = False
        self._monitor_task: asyncio.Task | None = None

    # ── Agent Registration ────────────────────────────────────────

    def register_agent(
        self,
        agent_id: str,
        capabilities: list[str] | None = None,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a real agent for swarm participation."""
        self._agent_registry[agent_id] = {
            "agent_id": agent_id,
            "capabilities": capabilities or [],
            "weight": weight,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "active": True,
        }
        logger.info("Agent registered for swarm: %s (capabilities: %s)", agent_id, capabilities)

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the swarm registry."""
        if agent_id in self._agent_registry:
            del self._agent_registry[agent_id]
            return True
        return False

    def register_chat_executor(
        self,
        executor_id: str,
        executor: Callable[[str, str], Awaitable[str]],
    ) -> None:
        """Register a chat executor function for real agent communication."""
        self._chat_executors[executor_id] = executor

    # ── Swarm Formation ───────────────────────────────────────────

    async def form_swarm(
        self,
        topic: str,
        required_capabilities: list[str] | None = None,
        min_members: int | None = None,
        max_members: int | None = None,
    ) -> SwarmSession:
        """Dynamically form a swarm based on topic and required capabilities.

        Automatically selects the best agents (real or simulated) and assigns
        initial roles based on capability matching. If no real agents are
        available and simulation mode is enabled, creates a simulated swarm.
        """
        min_members = min_members or self.DEFAULT_MIN_MEMBERS
        max_members = max_members or self.DEFAULT_MAX_MEMBERS
        required_capabilities = required_capabilities or []

        session_id = f"swarm-{uuid.uuid4().hex[:12]}"
        session = SwarmSession(
            session_id=session_id,
            topic=topic,
            state=SwarmState.FORMING,
        )

        # Determine if we have enough real agents
        available_real = [
            a for a in self._agent_registry.values()
            if a.get("active", True)
        ]

        use_simulation = len(available_real) < min_members and self._simulation_enabled
        session.simulation_mode = use_simulation

        if use_simulation:
            logger.info("Swarm '%s' forming in simulation mode (available real agents: %d)",
                        topic, len(available_real))
            self._global_metrics["simulation_sessions"] += 1
            members = await self._form_simulated_swarm(topic, required_capabilities, min_members, max_members)
        else:
            logger.info("Swarm '%s' forming with %d real agents", topic, len(available_real))
            members = await self._form_real_swarm(available_real, required_capabilities, min_members, max_members)

        session.members = members
        session.state = SwarmState.STORMING

        self._sessions[session_id] = session
        self._global_metrics["total_swarms_formed"] += 1
        self._global_metrics["swarms_active"] += 1

        # Assign initial roles
        await self.assign_roles(session_id)

        logger.info("Swarm formed: %s (%d members, simulation=%s)",
                     session_id, len(members), use_simulation)
        return session

    async def _form_simulated_swarm(
        self,
        topic: str,
        required_capabilities: list[str],
        min_members: int,
        max_members: int,
    ) -> list[SwarmMember]:
        """Form a swarm using simulated agent profiles."""
        # Score simulated agents by capability match to topic and requirements
        scored = []
        topic_lower = topic.lower()

        for profile in SIMULATED_AGENT_PROFILES:
            score = 0
            for cap in profile["capabilities"]:
                if cap in required_capabilities:
                    score += 3
                if cap.replace("_", " ") in topic_lower:
                    score += 2
            # Add diversity bonus
            score += random.uniform(0, 1)
            scored.append((score, profile))

        scored.sort(key=lambda x: -x[0])
        selected_count = min(max(len(required_capabilities), min_members), max_members, len(scored))

        members = []
        for _, profile in scored[:selected_count]:
            member = SwarmMember(
                agent_id=profile["agent_id"],
                role=SwarmRole.EXPLORER,  # Initial role, will be assigned later
                capabilities=profile["capabilities"],
                weight=profile["base_weight"],
                status=MemberStatus.IDLE,
            )
            members.append(member)

        return members

    async def _form_real_swarm(
        self,
        available_agents: list[dict],
        required_capabilities: list[str],
        min_members: int,
        max_members: int,
    ) -> list[SwarmMember]:
        """Form a swarm using real registered agents."""
        scored = []
        for agent in available_agents:
            score = 0
            agent_caps = agent.get("capabilities", [])
            for cap in required_capabilities:
                if cap in agent_caps:
                    score += 3
            # Bonus for diverse capabilities
            score += len(set(agent_caps) & set(required_capabilities)) * 0.5
            scored.append((score, agent))

        scored.sort(key=lambda x: -x[0])
        selected_count = min(max(len(required_capabilities), min_members), max_members, len(scored))

        members = []
        for _, agent in scored[:selected_count]:
            member = SwarmMember(
                agent_id=agent["agent_id"],
                role=SwarmRole.EXPLORER,
                capabilities=agent.get("capabilities", []),
                weight=agent.get("weight", 1.0),
                status=MemberStatus.IDLE,
            )
            members.append(member)

        return members

    # ── Role Assignment ───────────────────────────────────────────

    async def assign_roles(self, swarm_id: str) -> list[SwarmMember]:
        """Assign specialized roles to swarm members based on capability matching.

        Uses a scoring algorithm that considers:
        - Direct capability-to-role mapping
        - Agent historical performance in similar roles
        - Role diversity (avoiding concentration of similar roles)
        - Weight-based prioritization for critical roles
        """
        session = self._sessions.get(swarm_id)
        if not session:
            raise ValueError(f"Swarm session not found: {swarm_id}")

        members = session.members
        if not members:
            return []

        # Define role priority order (critical roles first)
        role_priority = [
            SwarmRole.LEADER,
            SwarmRole.SPECIALIST,
            SwarmRole.CRITIC,
            SwarmRole.VERIFIER,
            SwarmRole.SYNTHESIZER,
            SwarmRole.EXECUTOR,
            SwarmRole.EXPLORER,
            SwarmRole.MEDIATOR,
        ]

        assigned_roles: set[SwarmRole] = set()
        assigned_members: set[str] = set()

        # Phase 1: Assign critical roles
        for role in role_priority:
            if len(assigned_members) >= len(members):
                break

            best_member = None
            best_score = -1.0

            for member in members:
                if member.agent_id in assigned_members:
                    continue

                score = self._score_member_for_role(member, role, session.topic)
                if score > best_score:
                    best_score = score
                    best_member = member

            if best_member and best_score > 0:
                best_member.role = role
                assigned_roles.add(role)
                assigned_members.add(best_member.agent_id)
                logger.debug("Assigned %s as %s (score: %.2f)", best_member.agent_id, role.value, best_score)

        # Phase 2: Assign remaining roles to unassigned members
        remaining_roles = [r for r in role_priority if r not in assigned_roles]
        for member in members:
            if member.agent_id in assigned_members:
                continue
            if remaining_roles:
                member.role = remaining_roles.pop(0)
            else:
                member.role = SwarmRole.EXECUTOR
            assigned_members.add(member.agent_id)

        logger.info("Swarm %s: roles assigned to %d members", swarm_id, len(assigned_members))
        return members

    def _score_member_for_role(self, member: SwarmMember, role: SwarmRole, topic: str) -> float:
        """Score a member's suitability for a specific role."""
        score = 0.0

        # Check capability-to-role mapping
        for cap in member.capabilities:
            if role in CAPABILITY_TO_ROLE_MAP.get(cap, []):
                score += 2.0

        # Weight-based bonus
        score += member.weight * 1.5

        # Success rate bonus
        score += member.success_rate * 1.0

        # Topic relevance bonus
        topic_lower = topic.lower()
        for cap in member.capabilities:
            if cap.replace("_", " ") in topic_lower:
                score += 1.5

        # Specialization bonus
        role_key = role.value
        if role_key in member.specialization_score:
            score += member.specialization_score[role_key] * 2.0

        return score

    # ── Consensus Mechanisms ──────────────────────────────────────

    async def reach_consensus(
        self,
        swarm_id: str,
        question: str,
        options: list[str],
        method: ConsensusMethod = ConsensusMethod.WEIGHTED,
    ) -> ConsensusResult:
        """Reach consensus within the swarm using the specified method.

        Each consensus method provides different trade-offs between speed,
        accuracy, and inclusiveness:

        - MAJORITY: Fastest, simple >50% threshold
        - WEIGHTED: Accounts for agent reliability and expertise
        - RANKED_CHOICE: Most democratic, handles many options well
        - DELEGATED: Fastest single-decision, trusts the expert
        - SUPERMAJORITY: High confidence decisions, >=2/3 threshold
        - UNANIMOUS: Maximum agreement, requires full consensus
        """
        session = self._sessions.get(swarm_id)
        if not session:
            raise ValueError(f"Swarm session not found: {swarm_id}")

        if len(options) < 2:
            return ConsensusResult(
                decision=options[0] if options else "",
                confidence=1.0,
                method=method,
                votes={},
                rounds_taken=0,
            )

        session.state = SwarmState.STORMING

        if session.simulation_mode:
            result = await self._simulate_consensus(session, question, options, method)
        else:
            result = await self._execute_consensus(session, question, options, method)

        session.consensus_history.append(result)
        session.total_consensus_rounds += 1
        self._global_metrics["total_consensus_rounds"] += 1

        # Update rolling average confidence
        total_confidence = self._global_metrics["average_consensus_confidence"]
        total_rounds = self._global_metrics["total_consensus_rounds"]
        self._global_metrics["average_consensus_confidence"] = (
            (total_confidence * (total_rounds - 1) + result.confidence) / total_rounds
        )

        session.state = SwarmState.NORMING
        logger.info("Swarm %s consensus reached: '%s' (method=%s, confidence=%.2f)",
                     swarm_id, result.decision[:50], method.value, result.confidence)
        return result

    async def _execute_consensus(
        self,
        session: SwarmSession,
        question: str,
        options: list[str],
        method: ConsensusMethod,
    ) -> ConsensusResult:
        """Execute consensus with real agents via chat executors."""
        votes: dict[str, str] = {}
        vote_distribution: dict[str, int] = defaultdict(int)
        dissenting: list[str] = []
        deliberation_log: list[str] = []

        voting_members = [m for m in session.members if m.status != MemberStatus.OFFLINE]
        if not voting_members:
            return ConsensusResult(
                decision=options[0],
                confidence=0.1,
                method=method,
                dissenting_opinions=["No active members available for voting"],
            )

        if method == ConsensusMethod.DELEGATED:
            # Delegate to the leader or highest-weight member
            delegate = next(
                (m for m in voting_members if m.role == SwarmRole.LEADER),
                max(voting_members, key=lambda m: m.weight),
            )
            votes[delegate.agent_id] = options[0]
            return ConsensusResult(
                decision=options[0],
                confidence=delegate.weight * delegate.success_rate,
                method=method,
                votes=votes,
                deliberation_log=[f"Delegated to {delegate.agent_id} ({delegate.role.value})"],
            )

        # Collect votes from all members
        for member in voting_members:
            vote = await self._get_member_vote(member, question, options)
            votes[member.agent_id] = vote
            vote_distribution[vote] += 1
            member.consensus_participation += 1

        # Determine decision based on method
        decision, confidence, dissenting, rounds = self._resolve_consensus(
            votes, vote_distribution, options, method, voting_members,
        )

        return ConsensusResult(
            decision=decision,
            confidence=confidence,
            method=method,
            votes=votes,
            dissenting_opinions=dissenting,
            rounds_taken=rounds,
            vote_distribution=dict(vote_distribution),
            deliberation_log=deliberation_log,
        )

    async def _simulate_consensus(
        self,
        session: SwarmSession,
        question: str,
        options: list[str],
        method: ConsensusMethod,
    ) -> ConsensusResult:
        """Simulate consensus with diverse simulated agent perspectives.

        Each simulated agent votes based on its persona and capabilities,
        creating realistic voting patterns with dissenting opinions.
        """
        votes: dict[str, str] = {}
        vote_distribution: dict[str, int] = defaultdict(int)
        dissenting: list[str] = []

        voting_members = session.members
        if not voting_members:
            return ConsensusResult(
                decision=options[0],
                confidence=0.1,
                method=method,
                dissenting_opinions=["No members available for voting"],
            )

        if method == ConsensusMethod.DELEGATED:
            delegate = next(
                (m for m in voting_members if m.role == SwarmRole.LEADER),
                voting_members[0],
            )
            votes[delegate.agent_id] = options[0]
            return ConsensusResult(
                decision=options[0],
                confidence=delegate.weight * 0.9,
                method=method,
                votes=votes,
                deliberation_log=[f"Delegated to {delegate.agent_id} ({delegate.role.value})"],
            )

        # Simulate diverse voting patterns
        question_lower = question.lower()
        for member in voting_members:
            profile = next(
                (p for p in SIMULATED_AGENT_PROFILES if p["agent_id"] == member.agent_id),
                None,
            )

            # Generate vote based on agent persona and capabilities
            if profile:
                persona = profile.get("persona", "analytical")
                agent_caps = profile.get("capabilities", [])

                # Assign preference based on persona and capability alignment
                preference_scores = []
                for i, option in enumerate(options):
                    score = self._simulate_option_preference(
                        option, persona, agent_caps, question_lower, i,
                    )
                    preference_scores.append((score, option))

                preference_scores.sort(key=lambda x: -x[0])
                vote = preference_scores[0][1]
            else:
                vote = random.choice(options)

            votes[member.agent_id] = vote
            vote_distribution[vote] += 1
            member.consensus_participation += 1

        # Resolve consensus
        decision, confidence, dissenting, rounds = self._resolve_consensus(
            votes, vote_distribution, options, method, voting_members,
        )

        return ConsensusResult(
            decision=decision,
            confidence=confidence,
            method=method,
            votes=votes,
            dissenting_opinions=dissenting,
            rounds_taken=rounds,
            vote_distribution=dict(vote_distribution),
        )

    def _simulate_option_preference(
        self,
        option: str,
        persona: str,
        agent_caps: list[str],
        question_lower: str,
        option_index: int,
    ) -> float:
        """Simulate how an agent would prefer an option based on its persona."""
        option_lower = option.lower()
        score = random.uniform(0.3, 0.7)  # base randomness

        # Persona-based scoring
        persona_weights = {
            "analytical": {"analyze": 0.2, "data": 0.2, "systematic": 0.15, "precise": 0.15},
            "pragmatic": {"implement": 0.2, "execute": 0.2, "practical": 0.15, "direct": 0.15},
            "curious": {"explore": 0.2, "research": 0.2, "investigate": 0.15, "discover": 0.15},
            "cautious": {"verify": 0.2, "validate": 0.2, "safe": 0.15, "reliable": 0.15},
            "creative": {"innovate": 0.2, "design": 0.2, "novel": 0.15, "create": 0.15},
            "diplomatic": {"balance": 0.2, "collaborate": 0.2, "harmonize": 0.15, "integrate": 0.15},
            "empirical": {"evidence": 0.2, "data": 0.2, "measure": 0.15, "quantify": 0.15},
            "articulate": {"explain": 0.2, "clarify": 0.2, "document": 0.15, "describe": 0.15},
        }

        weights = persona_weights.get(persona, {})
        for keyword, weight in weights.items():
            if keyword in option_lower:
                score += weight

        # Capability alignment
        for cap in agent_caps:
            if cap.replace("_", " ") in option_lower:
                score += 0.15

        # Slight preference for earlier options (primacy effect)
        score += (len(agent_caps) - option_index) * 0.02

        return score

    def _resolve_consensus(
        self,
        votes: dict[str, str],
        vote_distribution: dict[str, int],
        options: list[str],
        method: ConsensusMethod,
        members: list[SwarmMember],
    ) -> tuple[str, float, list[str], int]:
        """Resolve votes into a decision based on the consensus method."""
        total_votes = len(votes)
        dissenting: list[str] = []
        rounds = 1

        if method == ConsensusMethod.UNANIMOUS:
            # All must agree; if not, return no consensus with low confidence
            unique_votes = set(votes.values())
            if len(unique_votes) == 1:
                decision = list(unique_votes)[0]
                confidence = 1.0
            else:
                # Find the most common and treat as partial
                decision = max(vote_distribution, key=lambda k: vote_distribution[k])
                confidence = vote_distribution[decision] / total_votes * 0.5
                for agent_id, vote in votes.items():
                    if vote != decision:
                        dissenting.append(f"Agent {agent_id} voted for '{vote}'")

        elif method == ConsensusMethod.SUPERMAJORITY:
            threshold = 2 / 3
            decision = max(vote_distribution, key=lambda k: vote_distribution[k])
            vote_count = vote_distribution[decision]
            ratio = vote_count / total_votes
            if ratio >= threshold:
                confidence = ratio
            else:
                confidence = ratio * 0.7
            for agent_id, vote in votes.items():
                if vote != decision:
                    dissenting.append(f"Agent {agent_id} voted for '{vote}'")

        elif method == ConsensusMethod.WEIGHTED:
            # Weight votes by member weight and success rate
            weighted: dict[str, float] = defaultdict(float)
            for member in members:
                if member.agent_id in votes:
                    vote_weight = member.weight * member.success_rate
                    weighted[votes[member.agent_id]] += vote_weight

            total_weight = sum(weighted.values())
            decision = max(weighted, key=lambda k: weighted[k])
            confidence = weighted[decision] / max(total_weight, 0.001)

            for agent_id, vote in votes.items():
                if vote != decision:
                    member = next((m for m in members if m.agent_id == agent_id), None)
                    weight_str = f" (weight: {member.weight:.2f})" if member else ""
                    dissenting.append(f"Agent {agent_id}{weight_str} voted for '{vote}'")

        elif method == ConsensusMethod.RANKED_CHOICE:
            # Simulate ranked choice with elimination rounds
            decision, confidence, rounds = self._ranked_choice_resolution(
                votes, vote_distribution, options, members,
            )
            for agent_id, vote in votes.items():
                if vote != decision:
                    dissenting.append(f"Agent {agent_id} preferred '{vote}'")

        else:  # MAJORITY (default)
            decision = max(vote_distribution, key=lambda k: vote_distribution[k])
            vote_count = vote_distribution[decision]
            confidence = vote_count / total_votes if total_votes > 0 else 0.0

            for agent_id, vote in votes.items():
                if vote != decision:
                    dissenting.append(f"Agent {agent_id} voted for '{vote}'")

        return decision, confidence, dissenting, rounds

    def _ranked_choice_resolution(
        self,
        votes: dict[str, str],
        vote_distribution: dict[str, int],
        options: list[str],
        members: list[SwarmMember],
    ) -> tuple[str, float, int]:
        """Simulate ranked choice voting with elimination rounds."""
        total_votes = len(votes)
        if total_votes == 0:
            return options[0] if options else "", 0.0, 0

        round_num = 1
        remaining = list(options)
        current_dist = dict(vote_distribution)

        while len(remaining) > 1:
            # Check if any option has majority
            for opt in remaining:
                if current_dist.get(opt, 0) > total_votes / 2:
                    return opt, current_dist[opt] / total_votes, round_num

            # Eliminate the option with fewest votes
            if remaining:
                min_opt = min(remaining, key=lambda o: current_dist.get(o, 0))
                remaining.remove(min_opt)

                # Redistribute votes from eliminated option
                redistributed = current_dist.pop(min_opt, 0)
                if remaining and redistributed > 0:
                    # Distribute to remaining options proportionally
                    for opt in remaining:
                        current_dist[opt] = current_dist.get(opt, 0) + redistributed // len(remaining)

            round_num += 1

            # Safety break
            if round_num > 10:
                break

        decision = remaining[0] if remaining else options[0]
        confidence = current_dist.get(decision, 0) / total_votes
        return decision, confidence, round_num

    async def _get_member_vote(
        self,
        member: SwarmMember,
        question: str,
        options: list[str],
    ) -> str:
        """Get a vote from a real agent via chat executor."""
        # Try to use a registered chat executor
        executor = self._chat_executors.get(member.agent_id)
        if not executor:
            # Fallback to simulation
            profile = next(
                (p for p in SIMULATED_AGENT_PROFILES if p["agent_id"] == member.agent_id),
                None,
            )
            if profile:
                persona = profile.get("persona", "analytical")
                agent_caps = profile.get("capabilities", [])
                question_lower = question.lower()
                scores = [
                    (self._simulate_option_preference(opt, persona, agent_caps, question_lower, i), opt)
                    for i, opt in enumerate(options)
                ]
                scores.sort(key=lambda x: -x[0])
                return scores[0][1]
            return random.choice(options)

        options_text = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))
        prompt = (
            f"Question: {question}\n\n"
            f"Options:\n{options_text}\n\n"
            f"As a {member.role.value}, provide your vote by stating only the "
            f"number of your chosen option. Be decisive."
        )
        try:
            response = await executor(member.agent_id, prompt)
            # Try to parse the response as a number
            for i, opt in enumerate(options):
                if str(i + 1) in response:
                    return opt
            return options[0]
        except Exception as e:
            logger.error("Failed to get vote from %s: %s", member.agent_id, e)
            return options[0]

    # ── Task Execution ────────────────────────────────────────────

    async def execute_swarm_task(
        self,
        swarm_id: str,
        task_description: str,
        complexity: float = 0.5,
        required_capabilities: list[str] | None = None,
        priority: int = 5,
    ) -> SwarmTask:
        """Execute a task across the swarm with decomposition and parallel execution.

        The task is analyzed for complexity, decomposed into subtasks if needed,
        and assigned to the most suitable swarm members. Results are collected
        and synthesized.
        """
        session = self._sessions.get(swarm_id)
        if not session:
            raise ValueError(f"Swarm session not found: {swarm_id}")

        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = SwarmTask(
            task_id=task_id,
            description=task_description,
            complexity=complexity,
            required_capabilities=required_capabilities or [],
            priority=priority,
        )

        # Decompose if high complexity
        if complexity > 0.6:
            subtasks = self._decompose_task(task_description, complexity, required_capabilities or [])
            task.subtasks = [st.task_id for st in subtasks]
            session.tasks.extend(subtasks)
            logger.info("Task %s decomposed into %d subtasks", task_id, len(subtasks))
        else:
            session.tasks.append(task)

        # Assign to best member
        assigned = await self._assign_task(task, session)
        if assigned:
            task.status = TaskStatus.ASSIGNED
            task.assigned_to = assigned.agent_id
            task.started_at = datetime.now(timezone.utc).isoformat()

            # Execute the task
            result = await self._execute_single_task(task, assigned, session)
            if result is not None:
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc).isoformat()
                assigned.update_success(True)
                session.total_tasks_completed += 1
            else:
                task.status = TaskStatus.FAILED
                assigned.update_success(False)
                session.total_tasks_failed += 1

        self._global_metrics["total_tasks_executed"] += 1
        return task

    def _decompose_task(
        self,
        description: str,
        complexity: float,
        required_capabilities: list[str],
    ) -> list[SwarmTask]:
        """Decompose a complex task into subtasks based on capability requirements."""
        subtasks = []
        desc_lower = description.lower()

        # Phase 1: Research/Exploration
        if any(kw in desc_lower for kw in ["research", "analyze", "investigate", "explore", "find"]):
            subtasks.append(SwarmTask(
                task_id=f"subtask-{uuid.uuid4().hex[:8]}",
                description=f"Research and gather information: {description}",
                complexity=complexity * 0.6,
                required_capabilities=["research", "information_retrieval"],
                priority=10,
            ))

        # Phase 2: Analysis/Critique
        if any(kw in desc_lower for kw in ["analyze", "review", "evaluate", "assess", "audit"]):
            subtasks.append(SwarmTask(
                task_id=f"subtask-{uuid.uuid4().hex[:8]}",
                description=f"Analyze and evaluate: {description}",
                complexity=complexity * 0.7,
                required_capabilities=["analysis", "review"],
                priority=8,
            ))

        # Phase 3: Implementation
        if any(kw in desc_lower for kw in ["implement", "build", "code", "develop", "create", "deploy"]):
            subtasks.append(SwarmTask(
                task_id=f"subtask-{uuid.uuid4().hex[:8]}",
                description=f"Implement solution: {description}",
                complexity=complexity * 0.8,
                required_capabilities=["implementation", "code_generation"],
                priority=6,
            ))

        # Phase 4: Verification
        subtasks.append(SwarmTask(
            task_id=f"subtask-{uuid.uuid4().hex[:8]}",
            description=f"Verify and validate: {description}",
            complexity=complexity * 0.5,
            required_capabilities=["validation", "verification"] if "validation" in required_capabilities else ["review"],
            priority=4,
        ))

        # Set dependencies between phases
        for i in range(1, len(subtasks)):
            subtasks[i].dependencies = [subtasks[i - 1].task_id]

        return subtasks

    async def _assign_task(self, task: SwarmTask, session: SwarmSession) -> SwarmMember | None:
        """Assign a task to the best available swarm member."""
        available = [m for m in session.members if m.is_available]

        if not available:
            return None

        # Score members for this task
        scored = []
        for member in available:
            score = 0.0

            # Capability match
            for cap in task.required_capabilities:
                if cap in member.capabilities:
                    score += 3.0

            # Role alignment
            if task.required_capabilities:
                for cap in task.required_capabilities:
                    if member.role in CAPABILITY_TO_ROLE_MAP.get(cap, []):
                        score += 2.0

            # Performance weighting
            score += member.success_rate * 2.0
            score += member.weight * 1.0

            # Load balancing (prefer less busy members)
            score -= member.task_count * 0.1

            scored.append((score, member))

        if not scored:
            return None

        scored.sort(key=lambda x: -x[0])
        best_member = scored[0][1]
        best_member.status = MemberStatus.WORKING
        return best_member

    async def _execute_single_task(
        self,
        task: SwarmTask,
        member: SwarmMember,
        session: SwarmSession,
    ) -> str | None:
        """Execute a single task with a specific member."""
        task.status = TaskStatus.IN_PROGRESS

        if session.simulation_mode:
            return await self._simulate_task_execution(task, member, session)

        # Try real execution via chat executor
        executor = self._chat_executors.get(member.agent_id)
        if not executor:
            return await self._simulate_task_execution(task, member, session)

        context = (
            f"Swarm Topic: {session.topic}\n"
            f"Your Role: {member.role.value}\n"
            f"Task: {task.description}\n\n"
            f"Complete this task thoroughly. Provide your findings and any relevant output."
        )

        try:
            result = await executor(member.agent_id, context)
            member.status = MemberStatus.DONE
            return result
        except Exception as e:
            logger.error("Task execution failed for %s: %s", member.agent_id, e)
            member.status = MemberStatus.FAILED
            return None

    async def _simulate_task_execution(
        self,
        task: SwarmTask,
        member: SwarmMember,
        session: SwarmSession,
    ) -> str:
        """Simulate task execution with realistic agent response."""
        # Simulate processing time based on complexity
        delay = task.complexity * random.uniform(0.3, 1.5)
        await asyncio.sleep(delay)

        profile = next(
            (p for p in SIMULATED_AGENT_PROFILES if p["agent_id"] == member.agent_id),
            None,
        )

        persona = profile.get("persona", "analytical") if profile else "analytical"
        style = profile.get("response_style", "structured") if profile else "structured"

        # Generate a simulated response based on persona and task
        response_templates = {
            "analytical": (
                f"## Analysis: {task.description}\n\n"
                f"After systematic evaluation, I've identified the following key points:\n\n"
                f"1. **Primary Consideration**: {task.description} requires careful decomposition "
                f"into manageable components.\n"
                f"2. **Risk Assessment**: Moderate complexity (score: {task.complexity:.2f}), "
                f"with manageable interdependencies.\n"
                f"3. **Recommended Approach**: A phased strategy with iterative validation "
                f"at each stage.\n\n"
                f"**Confidence**: {random.uniform(0.75, 0.95):.2f}"
            ),
            "pragmatic": (
                f"## Implementation Plan: {task.description}\n\n"
                f"Here's a practical approach:\n\n"
                f"- **Step 1**: Set up the foundation and verify prerequisites\n"
                f"- **Step 2**: Implement core functionality with minimal viable scope\n"
                f"- **Step 3**: Test and iterate based on results\n\n"
                f"**Estimated effort**: {random.randint(2, 8)} units\n"
                f"**Key dependencies**: Context awareness, tool availability"
            ),
            "curious": (
                f"## Exploration: {task.description}\n\n"
                f"I've investigated multiple angles on this:\n\n"
                f"- **Finding 1**: There are several approaches worth exploring, "
                f"including both conventional and novel methods.\n"
                f"- **Finding 2**: Cross-domain patterns suggest potential synergies "
                f"with related problem spaces.\n"
                f"- **Finding 3**: Preliminary data indicates {random.randint(60, 90)}% "
                f"feasibility for the proposed direction.\n\n"
                f"**Open Questions**: Several edge cases need further investigation."
            ),
            "cautious": (
                f"## Review: {task.description}\n\n"
                f"After thorough examination, I note the following concerns:\n\n"
                f"- **Risk 1**: Potential edge cases in complex scenarios\n"
                f"- **Risk 2**: Consistency verification needed across components\n"
                f"- **Risk 3**: Security implications should be assessed\n\n"
                f"**Recommendation**: Proceed with additional validation gates "
                f"at each milestone. Overall risk level: "
                f"{'MODERATE' if task.complexity < 0.7 else 'ELEVATED'}"
            ),
            "creative": (
                f"## Innovation: {task.description}\n\n"
                f"I've generated several novel approaches:\n\n"
                f"1. **Approach A**: A paradigm-shifting method that leverages "
                f"cross-domain patterns\n"
                f"2. **Approach B**: An unconventional synthesis of existing solutions "
                f"with a creative twist\n"
                f"3. **Approach C**: A minimalist solution that challenges core assumptions\n\n"
                f"**Most promising**: Approach {random.choice(['A', 'B', 'C'])} "
                f"offers the best balance of novelty and feasibility."
            ),
            "diplomatic": (
                f"## Synthesis: {task.description}\n\n"
                f"Integrating perspectives from the swarm, here's a balanced view:\n\n"
                f"- **Consensus View**: The team generally agrees on the core direction\n"
                f"- **Divergent Views**: Some members prefer alternative approaches, "
                f"which should be acknowledged\n"
                f"- **Recommended Path**: A hybrid approach that incorporates the "
                f"strongest elements from each perspective\n\n"
                f"**Collaboration Score**: {random.uniform(0.7, 0.95):.2f}"
            ),
            "empirical": (
                f"## Data-Driven Analysis: {task.description}\n\n"
                f"Based on quantitative assessment:\n\n"
                f"- **Metric 1**: Performance projection = {random.uniform(0.7, 0.95):.2f}\n"
                f"- **Metric 2**: Resource utilization estimate = {random.randint(40, 80)}%\n"
                f"- **Metric 3**: Success probability = {random.uniform(0.65, 0.92):.2f}\n\n"
                f"**Statistical Significance**: High confidence in the primary findings."
            ),
            "articulate": (
                f"## Documentation: {task.description}\n\n"
                f"Here is a clear explanation of the findings:\n\n"
                f"### Overview\n"
                f"The task involves {task.description.lower()}. After careful consideration, "
                f"the following key insights emerge:\n\n"
                f"### Key Findings\n"
                f"1. The primary factor is well-understood and manageable\n"
                f"2. Secondary considerations add nuance but don't change the core direction\n"
                f"3. Implementation requires attention to detail but is straightforward\n\n"
                f"### Summary\n"
                f"The approach is sound and ready for execution."
            ),
        }

        response = response_templates.get(persona, response_templates["analytical"])
        member.status = MemberStatus.DONE
        member.update_success(True)
        return response

    # ── Result Synthesis ──────────────────────────────────────────

    async def synthesize_results(self, swarm_id: str) -> str:
        """Aggregate and synthesize all task results from the swarm.

        Uses the SYNTHESIZER role member (or LEADER as fallback) to combine
        all task outputs into a coherent, comprehensive result.
        """
        session = self._sessions.get(swarm_id)
        if not session:
            raise ValueError(f"Swarm session not found: {swarm_id}")

        completed_tasks = [t for t in session.tasks if t.status == TaskStatus.COMPLETED and t.result]

        if not completed_tasks:
            return "No completed tasks to synthesize."

        # Find synthesizer
        synthesizer = next(
            (m for m in session.members if m.role == SwarmRole.SYNTHESIZER),
            next((m for m in session.members if m.role == SwarmRole.LEADER), session.members[0]),
        )

        if session.simulation_mode:
            synthesis = await self._simulate_synthesis(completed_tasks, synthesizer, session)
        else:
            synthesis = await self._execute_synthesis(completed_tasks, synthesizer, session)

        logger.info("Swarm %s: results synthesized (%d tasks)", swarm_id, len(completed_tasks))
        return synthesis

    async def _simulate_synthesis(
        self,
        completed_tasks: list[SwarmTask],
        synthesizer: SwarmMember,
        session: SwarmSession,
    ) -> str:
        """Simulate result synthesis."""
        parts = []
        parts.append(f"# Swarm Synthesis: {session.topic}\n")
        parts.append(f"*Synthesized by {synthesizer.agent_id} ({synthesizer.role.value})*\n")

        for i, task in enumerate(completed_tasks):
            parts.append(f"## Task {i + 1}: {task.description[:100]}\n")
            parts.append(f"{task.result[:300]}\n")
            if len(task.result or "") > 300:
                parts.append("... *(truncated)*\n")

        parts.append("\n## Integrated Summary\n")
        parts.append(
            f"The swarm completed {len(completed_tasks)} tasks successfully. "
            f"The collective intelligence of {len(session.members)} agents "
            f"working in parallel produced comprehensive coverage of the topic. "
            f"Key insights from each specialized role were integrated into a "
            f"coherent overall result. "
            f"Swarm efficiency: {session.total_tasks_completed / max(len(session.tasks), 1):.1%} "
            f"task completion rate."
        )

        return "\n".join(parts)

    async def _execute_synthesis(
        self,
        completed_tasks: list[SwarmTask],
        synthesizer: SwarmMember,
        session: SwarmSession,
    ) -> str:
        """Execute real synthesis via chat executor."""
        executor = self._chat_executors.get(synthesizer.agent_id)
        if not executor:
            return await self._simulate_synthesis(completed_tasks, synthesizer, session)

        task_summaries = "\n\n".join(
            f"## Task: {t.description}\n{t.result[:500]}"
            for t in completed_tasks
        )

        prompt = (
            f"Swarm Topic: {session.topic}\n\n"
            f"As the {synthesizer.role.value}, synthesize the following "
            f"{len(completed_tasks)} task results into a single comprehensive output.\n\n"
            f"{task_summaries}\n\n"
            f"Provide a well-structured synthesis that integrates all findings."
        )

        try:
            return await executor(synthesizer.agent_id, prompt)
        except Exception as e:
            logger.error("Synthesis execution failed: %s", e)
            return f"Synthesis failed: {e}"

    # ── Parallel Exploration ──────────────────────────────────────

    async def parallel_explore(
        self,
        swarm_id: str,
        topic: str,
        num_explorers: int | None = None,
    ) -> list[dict[str, Any]]:
        """Execute parallel exploration with multiple agents investigating a topic.

        Each explorer investigates from a different angle based on their role
        and capabilities, producing diverse perspectives that are later synthesized.
        """
        session = self._sessions.get(swarm_id)
        if not session:
            raise ValueError(f"Swarm session not found: {swarm_id}")

        explorers = [m for m in session.members if m.is_available]
        if num_explorers:
            # Prefer EXPLORER role, then fill with others
            explorer_role = [m for m in explorers if m.role == SwarmRole.EXPLORER]
            others = [m for m in explorers if m.role != SwarmRole.EXPLORER]
            explorers = (explorer_role + others)[:num_explorers]

        if not explorers:
            return []

        # Create exploration tasks with different angles
        angles = [
            "technical feasibility and implementation approaches",
            "risks, challenges, and potential pitfalls",
            "innovative and unconventional solutions",
            "data-driven analysis and quantitative assessment",
            "stakeholder perspectives and impact analysis",
            "comparative evaluation of alternative approaches",
            "scalability and long-term sustainability",
            "integration with existing systems and workflows",
        ]

        exploration_tasks = []
        for i, explorer in enumerate(explorers):
            angle = angles[i % len(angles)]
            task_desc = f"Explore {topic} from the perspective of {angle}"
            task = SwarmTask(
                task_id=f"explore-{uuid.uuid4().hex[:8]}",
                description=task_desc,
                complexity=0.4,
                required_capabilities=explorer.capabilities[:3],
                priority=7,
            )
            exploration_tasks.append((task, explorer))

        # Execute all explorations in parallel
        async def run_exploration(task: SwarmTask, member: SwarmMember) -> dict[str, Any]:
            result = await self._execute_single_task(task, member, session)
            member.status = MemberStatus.DONE
            return {
                "explorer_id": member.agent_id,
                "role": member.role.value,
                "angle": task.description,
                "findings": result or "No findings produced",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        futures = [run_exploration(t, m) for t, m in exploration_tasks]
        results = await asyncio.gather(*futures, return_exceptions=True)

        exploration_results = []
        for r in results:
            if isinstance(r, Exception):
                exploration_results.append({
                    "error": str(r),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                })
            else:
                exploration_results.append(r)

        logger.info("Swarm %s: parallel exploration completed (%d explorers, %d results)",
                     swarm_id, len(explorers), len(exploration_results))
        return exploration_results

    # ── Emergent Behavior Detection ───────────────────────────────

    def detect_emergent_behavior(self, swarm_id: str) -> list[EmergentPattern]:
        """Detect emergent patterns from swarm interactions.

        Analyzes consensus history, task outcomes, and member interactions
        to identify patterns that emerge from the collective intelligence
        rather than from individual agents. These include:

        - Consensus convergence: The swarm naturally converges on solutions
        - Role specialization: Members gravitate toward specific expertise
        - Collective intelligence gain: Swarm outperforms individual best
        - Innovation emergence: Novel solutions arise from interaction
        - Self-organization: Spontaneous role adaptation
        """
        session = self._sessions.get(swarm_id)
        if not session:
            raise ValueError(f"Swarm session not found: {swarm_id}")

        patterns: list[EmergentPattern] = []

        # Pattern 1: Consensus convergence
        if len(session.consensus_history) >= 3:
            confidences = [c.confidence for c in session.consensus_history[-5:]]
            if len(confidences) >= 3 and all(c > 0.7 for c in confidences):
                # Check if confidence is trending upward
                if confidences[-1] > confidences[0] * 1.1:
                    pattern = EmergentPattern(
                        pattern_id=f"emergent-{uuid.uuid4().hex[:8]}",
                        pattern_type="consensus_convergence",
                        description="Swarm is showing increasing consensus alignment over time",
                        confidence=0.85,
                        occurrences=len(session.consensus_history),
                        contributing_members=[m.agent_id for m in session.members],
                        impact_score=0.7,
                    )
                    patterns.append(pattern)

        # Pattern 2: Role specialization emergence
        role_specialization = self._check_role_specialization(session)
        if role_specialization:
            patterns.append(role_specialization)

        # Pattern 3: Collective intelligence gain
        if session.total_tasks_completed >= 5:
            avg_success = sum(m.success_rate for m in session.members) / max(len(session.members), 1)
            if avg_success > 0.8:
                pattern = EmergentPattern(
                    pattern_id=f"emergent-{uuid.uuid4().hex[:8]}",
                    pattern_type="collective_intelligence_gain",
                    description=f"Swarm achieving high collective success rate ({avg_success:.2%})",
                    confidence=0.75,
                    occurrences=session.total_tasks_completed,
                    contributing_members=[m.agent_id for m in session.members if m.success_rate > 0.8],
                    impact_score=0.65,
                )
                patterns.append(pattern)

        # Pattern 4: Innovation through diversity
        unique_roles = len(set(m.role for m in session.members))
        if unique_roles >= 5 and session.total_tasks_completed >= 3:
            pattern = EmergentPattern(
                pattern_id=f"emergent-{uuid.uuid4().hex[:8]}",
                pattern_type="diversity_driven_innovation",
                description=f"High role diversity ({unique_roles} unique roles) driving innovative solutions",
                confidence=0.7,
                occurrences=unique_roles,
                contributing_members=[m.agent_id for m in session.members],
                impact_score=0.6,
            )
            patterns.append(pattern)

        # Pattern 5: Self-organization
        if len(session.members) >= 4 and session.total_consensus_rounds >= 2:
            # Check if members are adapting roles naturally
            role_distribution = defaultdict(int)
            for m in session.members:
                role_distribution[m.role.value] += 1

            if len(role_distribution) >= 5:
                pattern = EmergentPattern(
                    pattern_id=f"emergent-{uuid.uuid4().hex[:8]}",
                    pattern_type="self_organization",
                    description="Swarm members spontaneously organizing into complementary roles",
                    confidence=0.7,
                    occurrences=len(role_distribution),
                    contributing_members=[m.agent_id for m in session.members],
                    impact_score=0.55,
                )
                patterns.append(pattern)

        # Store patterns
        if patterns:
            self._emergent_patterns.setdefault(swarm_id, []).extend(patterns)
            session.emergent_patterns_detected += len(patterns)
            self._global_metrics["emergent_patterns_detected"] += len(patterns)

        logger.info("Swarm %s: detected %d emergent patterns", swarm_id, len(patterns))
        return patterns

    def _check_role_specialization(self, session: SwarmSession) -> EmergentPattern | None:
        """Check if members are developing role specializations."""
        # Look for members with high task counts in specific roles
        specialists = []
        for member in session.members:
            if member.task_count >= 3 and member.success_rate > 0.75:
                specialists.append(member)

        if len(specialists) >= 2:
            return EmergentPattern(
                pattern_id=f"emergent-{uuid.uuid4().hex[:8]}",
                pattern_type="role_specialization",
                description=f"{len(specialists)} members developing specialized expertise in their roles",
                confidence=0.8,
                occurrences=len(specialists),
                contributing_members=[m.agent_id for m in specialists],
                impact_score=0.6,
            )
        return None

    # ── Swarm Optimization ────────────────────────────────────────

    async def optimize_swarm_composition(self, swarm_id: str) -> dict[str, Any]:
        """Optimize role assignments and swarm composition based on performance data.

        Analyzes task completion rates, consensus effectiveness, and member
        performance to suggest and apply role rotations that improve overall
        swarm efficiency. Implements role rotation for members who have
        completed enough tasks to show reliable performance patterns.
        """
        session = self._sessions.get(swarm_id)
        if not session:
            raise ValueError(f"Swarm session not found: {swarm_id}")

        changes = []
        optimization_metrics = {
            "before": {
                "avg_success_rate": sum(m.success_rate for m in session.members) / max(len(session.members), 1),
                "role_distribution": {m.agent_id: m.role.value for m in session.members},
            },
        }

        # Check for role rotation candidates
        for member in session.members:
            if member.task_count >= self.ROLE_ROTATION_INTERVAL:
                # Evaluate if role change would improve performance
                current_role = member.role
                best_alt_role = None
                best_alt_score = -1.0

                for alt_role in SwarmRole:
                    if alt_role == current_role:
                        continue
                    score = self._score_member_for_role(member, alt_role, session.topic)
                    if score > best_alt_score:
                        best_alt_score = score
                        best_alt_role = alt_role

                current_score = self._score_member_for_role(member, current_role, session.topic)

                if best_alt_role and best_alt_score > current_score * 1.2:
                    old_role = member.role
                    member.role = best_alt_role
                    changes.append({
                        "agent_id": member.agent_id,
                        "from_role": old_role.value,
                        "to_role": best_alt_role.value,
                        "score_improvement": best_alt_score - current_score,
                    })
                    logger.info("Swarm %s: rotated %s from %s to %s (score: %.2f -> %.2f)",
                                swarm_id, member.agent_id, old_role.value, best_alt_role.value,
                                current_score, best_alt_score)

        # Update specialization scores
        for member in session.members:
            role_key = member.role.value
            current = member.specialization_score.get(role_key, 0.0)
            member.specialization_score[role_key] = current * 0.8 + member.success_rate * 0.2

        # Check for underperforming members and mark for recovery
        for member in session.members:
            if member.task_count >= 3 and member.success_rate < 0.5:
                if member.status != MemberStatus.RECOVERING:
                    member.status = MemberStatus.RECOVERING
                    changes.append({
                        "agent_id": member.agent_id,
                        "action": "marked_for_recovery",
                        "success_rate": member.success_rate,
                    })

        optimization_metrics["after"] = {
            "avg_success_rate": sum(m.success_rate for m in session.members) / max(len(session.members), 1),
            "role_distribution": {m.agent_id: m.role.value for m in session.members},
        }
        optimization_metrics["changes"] = changes

        session.metrics["last_optimization"] = optimization_metrics
        return optimization_metrics

    # ── Health Monitoring ─────────────────────────────────────────

    async def _monitor_swarm_health(self, swarm_id: str) -> dict[str, Any]:
        """Monitor swarm health and trigger auto-recovery for unhealthy members."""
        session = self._sessions.get(swarm_id)
        if not session:
            return {"error": "Session not found"}

        now = time.time()
        health_report = {
            "swarm_id": swarm_id,
            "state": session.state.value,
            "total_members": len(session.members),
            "healthy_members": 0,
            "degraded_members": 0,
            "offline_members": 0,
            "recovery_actions": [],
        }

        for member in session.members:
            # Check heartbeat timeout
            if now - member.last_heartbeat > self.MEMBER_TIMEOUT:
                if member.status != MemberStatus.OFFLINE:
                    member.status = MemberStatus.OFFLINE
                    health_report["recovery_actions"].append({
                        "agent_id": member.agent_id,
                        "action": "marked_offline",
                        "reason": "heartbeat_timeout",
                    })
                    logger.warning("Swarm %s: member %s marked offline (heartbeat timeout)",
                                   swarm_id, member.agent_id)

            # Count statuses
            if member.status == MemberStatus.OFFLINE:
                health_report["offline_members"] += 1
            elif member.status in (MemberStatus.FAILED, MemberStatus.RECOVERING):
                health_report["degraded_members"] += 1
            else:
                health_report["healthy_members"] += 1

        # Auto-recovery: if leader is offline, promote a new leader
        leader = next((m for m in session.members if m.role == SwarmRole.LEADER), None)
        if leader and leader.status == MemberStatus.OFFLINE:
            candidates = [m for m in session.members if m.status not in (MemberStatus.OFFLINE, MemberStatus.FAILED)]
            if candidates:
                new_leader = max(candidates, key=lambda m: m.weight * m.success_rate)
                if new_leader.role != SwarmRole.LEADER:
                    old_role = new_leader.role
                    new_leader.role = SwarmRole.LEADER
                    health_report["recovery_actions"].append({
                        "agent_id": new_leader.agent_id,
                        "action": "promoted_to_leader",
                        "previous_role": old_role.value,
                    })
                    logger.info("Swarm %s: promoted %s to leader (replacing %s)",
                                swarm_id, new_leader.agent_id, leader.agent_id)

        # Update session metrics
        session.metrics["health"] = health_report
        return health_report

    # ── Swarm Lifecycle ───────────────────────────────────────────

    async def dissolve_swarm(self, swarm_id: str) -> SwarmSession:
        """Clean up and archive a swarm session.

        Marks the swarm as adjourning, archives all results and metrics,
        resets member states, and removes the session from active tracking.
        """
        session = self._sessions.get(swarm_id)
        if not session:
            raise ValueError(f"Swarm session not found: {swarm_id}")

        session.state = SwarmState.ADJOURNING

        # Finalize any pending tasks
        for task in session.tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS):
                task.status = TaskStatus.BLOCKED
                task.completed_at = datetime.now(timezone.utc).isoformat()

        # Reset member states
        for member in session.members:
            if member.status == MemberStatus.WORKING:
                member.status = MemberStatus.DONE
            member.task_count = 0

        # Archive metrics
        session.metrics["final"] = {
            "total_tasks": len(session.tasks),
            "completed_tasks": session.total_tasks_completed,
            "failed_tasks": session.total_tasks_failed,
            "consensus_rounds": session.total_consensus_rounds,
            "emergent_patterns": session.emergent_patterns_detected,
            "duration_seconds": (
                datetime.now(timezone.utc) - datetime.fromisoformat(session.formed_at)
            ).total_seconds(),
            "member_count": len(session.members),
            "simulation_mode": session.simulation_mode,
        }

        session.completed_at = datetime.now(timezone.utc).isoformat()
        self._global_metrics["swarms_active"] = max(0, self._global_metrics["swarms_active"] - 1)

        # Update average swarm size
        total_swarms = self._global_metrics["total_swarms_formed"]
        old_avg = self._global_metrics["average_swarm_size"]
        self._global_metrics["average_swarm_size"] = (
            (old_avg * (total_swarms - 1) + len(session.members)) / total_swarms
        )

        logger.info("Swarm '%s' dissolved: %d tasks completed, %d patterns detected",
                     swarm_id, session.total_tasks_completed, session.emergent_patterns_detected)
        return session

    # ── Metrics and Reporting ─────────────────────────────────────

    def get_swarm_metrics(self) -> dict[str, Any]:
        """Get comprehensive performance metrics across all swarms.

        Returns aggregated metrics including swarm counts, task completion
        rates, consensus effectiveness, emergent pattern statistics, and
        per-swarm detailed breakdowns.
        """
        swarm_details = []
        for session_id, session in self._sessions.items():
            swarm_details.append({
                "session_id": session_id,
                "topic": session.topic,
                "state": session.state.value,
                "members": len(session.members),
                "tasks_completed": session.total_tasks_completed,
                "tasks_failed": session.total_tasks_failed,
                "consensus_rounds": session.total_consensus_rounds,
                "emergent_patterns": session.emergent_patterns_detected,
                "simulation_mode": session.simulation_mode,
                "formed_at": session.formed_at,
                "completed_at": session.completed_at,
                "duration_seconds": (
                    (datetime.now(timezone.utc) - datetime.fromisoformat(session.formed_at)).total_seconds()
                    if not session.completed_at
                    else (datetime.fromisoformat(session.completed_at) - datetime.fromisoformat(session.formed_at)).total_seconds()
                ),
                "role_distribution": {
                    m.agent_id: m.role.value for m in session.members
                },
            })

        return {
            **self._global_metrics,
            "active_swarms": sum(1 for s in self._sessions.values() if s.state != SwarmState.ADJOURNING),
            "total_swarms": len(self._sessions),
            "registered_agents": len(self._agent_registry),
            "swarm_details": swarm_details,
            "emergent_patterns_by_swarm": {
                sid: [
                    {
                        "pattern_id": p.pattern_id,
                        "pattern_type": p.pattern_type,
                        "description": p.description,
                        "confidence": p.confidence,
                        "occurrences": p.occurrences,
                    }
                    for p in patterns
                ]
                for sid, patterns in self._emergent_patterns.items()
            },
        }

    def get_session(self, swarm_id: str) -> SwarmSession | None:
        """Get a swarm session by ID."""
        return self._sessions.get(swarm_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all swarm sessions with summary information."""
        return [
            {
                "session_id": s.session_id,
                "topic": s.topic,
                "state": s.state.value,
                "member_count": len(s.members),
                "tasks_completed": s.total_tasks_completed,
                "simulation_mode": s.simulation_mode,
                "formed_at": s.formed_at,
            }
            for s in self._sessions.values()
        ]

    # ── Health Monitoring Loop ────────────────────────────────────

    async def start_health_monitor(self, interval: float = 30.0) -> None:
        """Start the background health monitoring loop."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._health_monitor_loop(interval))
        logger.info("Swarm health monitor started (interval: %.1fs)", interval)

    async def stop_health_monitor(self) -> None:
        """Stop the health monitoring loop."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Swarm health monitor stopped")

    async def _health_monitor_loop(self, interval: float) -> None:
        """Background loop for monitoring swarm health."""
        while self._running:
            try:
                for swarm_id in list(self._sessions.keys()):
                    await self._monitor_swarm_health(swarm_id)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health monitor error: %s", e)
                await asyncio.sleep(interval)

    # ── Simulation Control ────────────────────────────────────────

    def enable_simulation(self) -> None:
        """Enable simulation mode for when real agents are unavailable."""
        self._simulation_enabled = True
        logger.info("Swarm simulation mode enabled")

    def disable_simulation(self) -> None:
        """Disable simulation mode, requiring real agents."""
        self._simulation_enabled = False
        logger.info("Swarm simulation mode disabled")


# ═══════════════════════════════════════════════════════════════════
# Module-level Singleton
# ═══════════════════════════════════════════════════════════════════

swarm_orchestrator = SwarmOrchestrator()