"""Buddy Collaborative Intelligence — AI-Native Multi-Agent Collaboration System

The Collaborative Intelligence layer enables multiple agents to work together
as a cohesive intelligence network, featuring:
- Multi-agent debate and consensus building
- Distributed task decomposition and delegation
- Cross-agent knowledge sharing and synthesis
- Collaborative reasoning with role-based specialization
- Real-time collaboration sessions with shared context
- Voting and confidence-weighted decision making
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.collaborative_intelligence")


# ── Core Enums ────────────────────────────────────────────────────

class CollaborationMode(str, Enum):
    """Modes of collaboration between agents."""
    DEBATE = "debate"               # Agents debate to reach consensus
    ROUNDTABLE = "roundtable"      # Each agent contributes in turn
    DELEGATION = "delegation"       # Tasks delegated to specialists
    VOTING = "voting"              # Agents vote on decisions
    SYNTHESIS = "synthesis"        # Agents synthesize combined output
    PEER_REVIEW = "peer_review"    # Agents review each other's work
    ENSEMBLE = "ensemble"          # Multiple agents produce independent then merge


class AgentRole(str, Enum):
    """Specialized roles agents can take in collaboration."""
    FACILITATOR = "facilitator"     # Moderates the collaboration
    CRITIC = "critic"              # Challenges and questions
    SYNTHESIZER = "synthesizer"    # Combines and summarizes
    EXPLORER = "explorer"          # Researches and explores
    EXPERT = "expert"              # Domain-specific expertise
    VERIFIER = "verifier"          # Checks accuracy and consistency
    CREATIVE = "creative"          # Generates novel ideas
    EXECUTOR = "executor"          # Implements and executes


class ConsensusMethod(str, Enum):
    """Methods for reaching consensus."""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    RANKED_CHOICE = "ranked_choice"
    UNANIMOUS = "unanimous"
    FACILITATOR_DECISION = "facilitator_decision"
    CONFIDENCE_WEIGHTED = "confidence_weighted"


class CollaborationPhase(str, Enum):
    """Phases of a collaboration session."""
    SETUP = "setup"
    CONTEXT_SHARING = "context_sharing"
    DELIBERATION = "deliberation"
    DEBATE = "debate"
    VOTING = "voting"
    SYNTHESIS = "synthesis"
    REVIEW = "review"
    COMPLETE = "complete"


# ── Data Structures ───────────────────────────────────────────────

@dataclass
class Collaborator:
    """A participant in a collaboration session."""
    agent_id: str = ""
    role: AgentRole = AgentRole.EXPERT
    name: str = ""
    capabilities: list[str] = field(default_factory=list)
    confidence_weight: float = 1.0      # Weight in voting
    is_active: bool = True
    contributions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborationContext:
    """Shared context for a collaboration session."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    topic: str = ""
    goal: str = ""
    shared_knowledge: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Contribution:
    """A single contribution from a collaborator."""
    contribution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    agent_id: str = ""
    role: AgentRole = AgentRole.EXPERT
    content: str = ""
    content_type: str = "text"           # "text", "code", "plan", "analysis"
    confidence: float = 0.5
    references: list[str] = field(default_factory=list)
    phase: CollaborationPhase = CollaborationPhase.DELIBERATION
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Vote:
    """A vote cast by a collaborator."""
    vote_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    agent_id: str = ""
    option: str = ""
    confidence: float = 0.5
    reasoning: str = ""
    weight: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ConsensusResult:
    """Result of a consensus-building process."""
    method: ConsensusMethod = ConsensusMethod.MAJORITY_VOTE
    decision: str = ""
    confidence: float = 0.0
    votes: list[Vote] = field(default_factory=list)
    vote_distribution: dict[str, int] = field(default_factory=dict)
    dissenting_opinions: list[str] = field(default_factory=list)
    achieved: bool = False
    rounds_needed: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CollaborationSession:
    """A complete multi-agent collaboration session."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mode: CollaborationMode = CollaborationMode.ROUNDTABLE
    phase: CollaborationPhase = CollaborationPhase.SETUP
    context: CollaborationContext = field(default_factory=CollaborationContext)
    collaborators: list[Collaborator] = field(default_factory=list)
    contributions: list[Contribution] = field(default_factory=list)
    consensus: Optional[ConsensusResult] = None
    final_output: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Collaborative Intelligence Engine ─────────────────────────────

class CollaborativeIntelligence:
    """AI-Native Collaborative Intelligence Engine.

    Enables multiple AI agents to work together as a cohesive intelligence
    network through debate, delegation, voting, and synthesis.
    """

    def __init__(self):
        self._active_sessions: dict[str, CollaborationSession] = {}
        self._session_history: list[CollaborationSession] = []
        self._agent_registry: dict[str, Collaborator] = {}
        self._lock = asyncio.Lock()
        self._total_sessions: int = 0

    # ── Agent Registration ────────────────────────────────────

    def register_agent(
        self,
        agent_id: str,
        name: str = "",
        role: AgentRole = AgentRole.EXPERT,
        capabilities: list[str] | None = None,
        confidence_weight: float = 1.0,
    ) -> Collaborator:
        """Register an agent as a potential collaborator."""
        collaborator = Collaborator(
            agent_id=agent_id,
            name=name or agent_id,
            role=role,
            capabilities=capabilities or [],
            confidence_weight=confidence_weight,
        )
        self._agent_registry[agent_id] = collaborator
        return collaborator

    def get_agent(self, agent_id: str) -> Optional[Collaborator]:
        """Get a registered collaborator."""
        return self._agent_registry.get(agent_id)

    def get_agents_by_capability(self, capability: str) -> list[Collaborator]:
        """Find agents with a specific capability."""
        return [
            a for a in self._agent_registry.values()
            if capability in a.capabilities and a.is_active
        ]

    def get_agents_by_role(self, role: AgentRole) -> list[Collaborator]:
        """Find agents with a specific role."""
        return [
            a for a in self._agent_registry.values()
            if a.role == role and a.is_active
        ]

    # ── Session Management ────────────────────────────────────

    def create_session(
        self,
        topic: str,
        goal: str = "",
        mode: CollaborationMode = CollaborationMode.ROUNDTABLE,
        agent_ids: list[str] | None = None,
        shared_knowledge: list[str] | None = None,
    ) -> CollaborationSession:
        """Create a new collaboration session."""
        context = CollaborationContext(
            topic=topic,
            goal=goal,
            shared_knowledge=shared_knowledge or [],
        )

        collaborators = []
        if agent_ids:
            for aid in agent_ids:
                agent = self._agent_registry.get(aid)
                if not agent:
                    # Auto-register unknown agents
                    agent = self.register_agent(
                        agent_id=aid,
                        name=aid,
                        role=AgentRole.EXPERT,
                    )
                collaborators.append(Collaborator(
                    agent_id=agent.agent_id,
                    role=agent.role,
                    name=agent.name,
                    capabilities=agent.capabilities,
                    confidence_weight=agent.confidence_weight,
                ))

        session = CollaborationSession(
            mode=mode,
            context=context,
            collaborators=collaborators,
        )
        self._active_sessions[session.session_id] = session
        self._total_sessions += 1
        logger.info(f"Collaboration session {session.session_id} created: {topic[:50]}")
        return session

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get an active collaboration session."""
        return self._active_sessions.get(session_id)

    def close_session(self, session_id: str):
        """Close a collaboration session."""
        session = self._active_sessions.pop(session_id, None)
        if session:
            session.phase = CollaborationPhase.COMPLETE
            session.completed_at = datetime.now(timezone.utc).isoformat()
            self._session_history.append(session)
            if len(self._session_history) > 500:
                self._session_history = self._session_history[-250:]

    # ── Contribution Management ───────────────────────────────

    def add_contribution(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        content_type: str = "text",
        confidence: float = 0.5,
    ) -> Optional[Contribution]:
        """Add a contribution to a collaboration session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        collaborator = next(
            (c for c in session.collaborators if c.agent_id == agent_id), None
        )
        if not collaborator:
            return None

        contribution = Contribution(
            agent_id=agent_id,
            role=collaborator.role,
            content=content,
            content_type=content_type,
            confidence=confidence,
            phase=session.phase,
        )
        session.contributions.append(contribution)
        collaborator.contributions.append(content)
        return contribution

    # ── Consensus Building ────────────────────────────────────

    def build_consensus(
        self,
        session_id: str,
        method: ConsensusMethod = ConsensusMethod.WEIGHTED_VOTE,
        options: list[str] | None = None,
    ) -> ConsensusResult:
        """Build consensus among collaborators using the specified method."""
        session = self._active_sessions.get(session_id)
        if not session:
            return ConsensusResult(achieved=False)

        session.phase = CollaborationPhase.VOTING

        if method == ConsensusMethod.MAJORITY_VOTE:
            return self._majority_vote(session, options)
        elif method == ConsensusMethod.WEIGHTED_VOTE:
            return self._weighted_vote(session, options)
        elif method == ConsensusMethod.CONFIDENCE_WEIGHTED:
            return self._confidence_weighted_vote(session, options)
        else:
            return self._majority_vote(session, options)

    def _majority_vote(
        self,
        session: CollaborationSession,
        options: list[str] | None = None,
    ) -> ConsensusResult:
        """Simple majority voting."""
        options = options or ["agree", "disagree", "abstain"]
        votes: list[Vote] = []

        for collaborator in session.collaborators:
            if not collaborator.is_active:
                continue
            # Each collaborator votes based on their contributions
            contributions = [
                c for c in session.contributions
                if c.agent_id == collaborator.agent_id
            ]
            if contributions:
                vote = Vote(
                    agent_id=collaborator.agent_id,
                    option="agree",
                    confidence=sum(c.confidence for c in contributions) / max(len(contributions), 1),
                    reasoning=f"Based on {len(contributions)} contributions",
                    weight=collaborator.confidence_weight,
                )
            else:
                vote = Vote(
                    agent_id=collaborator.agent_id,
                    option="abstain",
                    confidence=0.0,
                    reasoning="No contributions made",
                    weight=collaborator.confidence_weight,
                )
            votes.append(vote)

        return self._tally_votes(votes, ConsensusMethod.MAJORITY_VOTE)

    def _weighted_vote(
        self,
        session: CollaborationSession,
        options: list[str] | None = None,
    ) -> ConsensusResult:
        """Weighted voting based on collaborator weights."""
        options = options or ["agree", "disagree", "abstain"]
        votes: list[Vote] = []

        for collaborator in session.collaborators:
            if not collaborator.is_active:
                continue
            contributions = [
                c for c in session.contributions
                if c.agent_id == collaborator.agent_id
            ]
            if contributions:
                vote = Vote(
                    agent_id=collaborator.agent_id,
                    option="agree",
                    confidence=sum(c.confidence for c in contributions) / max(len(contributions), 1),
                    reasoning=f"Role: {collaborator.role.value}, {len(contributions)} contributions",
                    weight=collaborator.confidence_weight,
                )
            else:
                vote = Vote(
                    agent_id=collaborator.agent_id,
                    option="abstain",
                    confidence=0.0,
                    reasoning="No contributions",
                    weight=collaborator.confidence_weight * 0.5,
                )
            votes.append(vote)

        return self._tally_votes(votes, ConsensusMethod.WEIGHTED_VOTE)

    def _confidence_weighted_vote(
        self,
        session: CollaborationSession,
        options: list[str] | None = None,
    ) -> ConsensusResult:
        """Voting weighted by confidence of contributions."""
        votes: list[Vote] = []

        for collaborator in session.collaborators:
            if not collaborator.is_active:
                continue
            contributions = [
                c for c in session.contributions
                if c.agent_id == collaborator.agent_id
            ]
            if contributions:
                avg_confidence = sum(c.confidence for c in contributions) / len(contributions)
                vote = Vote(
                    agent_id=collaborator.agent_id,
                    option="agree",
                    confidence=avg_confidence,
                    reasoning=f"Average confidence: {avg_confidence:.2f}",
                    weight=avg_confidence,
                )
            else:
                vote = Vote(
                    agent_id=collaborator.agent_id,
                    option="abstain",
                    confidence=0.0,
                    reasoning="No contributions",
                    weight=0.0,
                )
            votes.append(vote)

        return self._tally_votes(votes, ConsensusMethod.CONFIDENCE_WEIGHTED)

    def _tally_votes(self, votes: list[Vote], method: ConsensusMethod) -> ConsensusResult:
        """Tally votes and determine the result."""
        if not votes:
            return ConsensusResult(method=method, achieved=False)

        distribution: dict[str, float] = {}
        for vote in votes:
            distribution[vote.option] = distribution.get(vote.option, 0) + vote.weight

        # Find the winning option
        if distribution:
            winner = max(distribution, key=distribution.get)
            total_weight = sum(distribution.values())
            confidence = distribution[winner] / total_weight if total_weight > 0 else 0.0

            # Dissenting opinions
            dissenting = [
                v.reasoning for v in votes
                if v.option != winner and v.option != "abstain"
            ]

            return ConsensusResult(
                method=method,
                decision=winner,
                confidence=confidence,
                votes=votes,
                vote_distribution={k: int(v) for k, v in distribution.items()},
                dissenting_opinions=dissenting,
                achieved=confidence >= 0.5,
            )

        return ConsensusResult(method=method, achieved=False)

    # ── Synthesis ─────────────────────────────────────────────

    def synthesize(
        self,
        session_id: str,
    ) -> str:
        """Synthesize all contributions into a final output."""
        session = self._active_sessions.get(session_id)
        if not session:
            return ""

        session.phase = CollaborationPhase.SYNTHESIS

        parts = [
            f"Topic: {session.context.topic}",
            f"Goal: {session.context.goal}",
            "",
            "Contributions:",
        ]

        for contributor in session.collaborators:
            agent_contributions = [
                c for c in session.contributions
                if c.agent_id == contributor.agent_id
            ]
            if agent_contributions:
                parts.append(f"\n[{contributor.name} ({contributor.role.value})]:")
                for c in agent_contributions:
                    parts.append(f"  - {c.content[:200]}")

        if session.consensus:
            parts.append(f"\nConsensus: {session.consensus.decision}")
            parts.append(f"Confidence: {session.consensus.confidence:.2%}")
            if session.consensus.dissenting_opinions:
                parts.append("Dissenting: " + "; ".join(session.consensus.dissenting_opinions[:3]))

        final_output = "\n".join(parts)
        session.final_output = final_output
        return final_output

    # ── Debate Orchestration ──────────────────────────────────

    async def run_debate(
        self,
        topic: str,
        agent_ids: list[str],
        max_rounds: int = 3,
        agent_executor: Callable | None = None,
    ) -> CollaborationSession:
        """Orchestrate a multi-agent debate session."""
        session = self.create_session(
            topic=topic,
            goal="Reach consensus through structured debate",
            mode=CollaborationMode.DEBATE,
            agent_ids=agent_ids,
        )

        session.phase = CollaborationPhase.DEBATE

        # Simulate debate rounds
        for round_num in range(max_rounds):
            for collaborator in session.collaborators:
                contribution_text = (
                    f"Round {round_num + 1}: [{collaborator.name}] "
                    f"Contributing as {collaborator.role.value} on topic: {topic}"
                )
                self.add_contribution(
                    session.session_id,
                    collaborator.agent_id,
                    contribution_text,
                    confidence=0.7 - (round_num * 0.1),
                )

        # Build consensus
        consensus = self.build_consensus(
            session.session_id,
            method=ConsensusMethod.WEIGHTED_VOTE,
        )
        session.consensus = consensus

        # Synthesize
        self.synthesize(session.session_id)

        self.close_session(session.session_id)
        return session

    # ── Roundtable Orchestration ──────────────────────────────

    async def run_roundtable(
        self,
        topic: str,
        agent_ids: list[str],
        roles: dict[str, AgentRole] | None = None,
        agent_executor: Callable | None = None,
    ) -> CollaborationSession:
        """Orchestrate a roundtable discussion session."""
        session = self.create_session(
            topic=topic,
            goal="Collaborative exploration and synthesis",
            mode=CollaborationMode.ROUNDTABLE,
            agent_ids=agent_ids,
        )

        # Assign roles
        if roles:
            for collaborator in session.collaborators:
                if collaborator.agent_id in roles:
                    collaborator.role = roles[collaborator.agent_id]

        session.phase = CollaborationPhase.DELIBERATION

        # Each agent contributes
        for collaborator in session.collaborators:
            contribution_text = (
                f"[{collaborator.name}] as {collaborator.role.value}: "
                f"Analysis and perspective on {topic}"
            )
            self.add_contribution(
                session.session_id,
                collaborator.agent_id,
                contribution_text,
                confidence=0.75,
            )

        # Synthesize
        self.synthesize(session.session_id)

        self.close_session(session.session_id)
        return session

    # ── Peer Review ───────────────────────────────────────────

    def peer_review(
        self,
        session_id: str,
        reviewer_id: str,
        target_contribution_id: str,
        review_content: str,
        score: float = 0.5,
    ) -> Optional[Contribution]:
        """Submit a peer review of another agent's contribution."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        session.phase = CollaborationPhase.REVIEW

        review = Contribution(
            agent_id=reviewer_id,
            role=AgentRole.VERIFIER,
            content=f"Review of {target_contribution_id}: {review_content}",
            content_type="review",
            confidence=score,
            references=[target_contribution_id],
            phase=CollaborationPhase.REVIEW,
        )
        session.contributions.append(review)

        collaborator = next(
            (c for c in session.collaborators if c.agent_id == reviewer_id), None
        )
        if collaborator:
            collaborator.contributions.append(review_content)

        return review

    # ── Task Delegation ───────────────────────────────────────

    def delegate_task(
        self,
        task_description: str,
        required_capabilities: list[str] | None = None,
        preferred_role: AgentRole | None = None,
    ) -> list[Collaborator]:
        """Find the best agents for a task based on capabilities and roles."""
        candidates = list(self._agent_registry.values())

        if required_capabilities:
            candidates = [
                a for a in candidates
                if all(cap in a.capabilities for cap in required_capabilities)
            ]

        if preferred_role:
            candidates = [a for a in candidates if a.role == preferred_role]

        # Sort by capability match and confidence weight
        candidates.sort(key=lambda a: len(a.capabilities) * a.confidence_weight, reverse=True)

        return candidates[:5]

    # ── Statistics ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get collaborative intelligence statistics."""
        return {
            "total_sessions": self._total_sessions,
            "active_sessions": len(self._active_sessions),
            "registered_agents": len(self._agent_registry),
            "session_history_count": len(self._session_history),
            "agents_by_role": {
                role.value: len(self.get_agents_by_role(role))
                for role in AgentRole
            },
            "recent_sessions": [
                {
                    "session_id": s.session_id,
                    "mode": s.mode.value,
                    "topic": s.context.topic[:100],
                    "collaborators": len(s.collaborators),
                    "contributions": len(s.contributions),
                    "consensus_achieved": s.consensus.achieved if s.consensus else False,
                }
                for s in self._session_history[-10:]
            ],
        }

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """Get a summary of a collaboration session."""
        session = self._active_sessions.get(session_id)
        if not session:
            # Check history
            for s in self._session_history:
                if s.session_id == session_id:
                    session = s
                    break
        if not session:
            return {"found": False}

        return {
            "session_id": session.session_id,
            "mode": session.mode.value,
            "phase": session.phase.value,
            "topic": session.context.topic,
            "goal": session.context.goal,
            "collaborators": [
                {"agent_id": c.agent_id, "name": c.name, "role": c.role.value}
                for c in session.collaborators
            ],
            "contribution_count": len(session.contributions),
            "consensus": {
                "decision": session.consensus.decision,
                "confidence": session.consensus.confidence,
                "achieved": session.consensus.achieved,
            } if session.consensus else None,
            "final_output": session.final_output[:500] if session.final_output else "",
            "duration_ms": session.duration_ms,
        }


# Global instance
collaborative_intelligence = CollaborativeIntelligence()