"""Agent Negotiation Protocol — multi-agent debate, negotiation, and consensus building.

Implements structured negotiation between multiple agents with roles, proposals,
counter-proposals, voting, and consensus mechanisms. Supports multiple negotiation
strategies including competitive, collaborative, and mediated approaches.
"""

from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NegotiationStrategy(Enum):
    """Approach to negotiation between agents."""
    COLLABORATIVE = "collaborative"
    COMPETITIVE = "competitive"
    MEDIATED = "mediated"
    CONSENSUS_DRIVEN = "consensus_driven"
    VOTING_BASED = "voting_based"


class RoundType(Enum):
    """Type of a negotiation round."""
    PROPOSAL = "proposal"
    COUNTER = "counter"
    DELIBERATION = "deliberation"
    VOTING = "voting"
    CLOSING = "closing"


class DelegateRole(Enum):
    """Role of a delegate in the negotiation."""
    PROPOSER = "proposer"
    OPPONENT = "opponent"
    MEDIATOR = "mediator"
    OBSERVER = "observer"
    EXPERT = "expert"
    FACILITATOR = "facilitator"


class ResolutionType(Enum):
    """How a negotiation was resolved."""
    CONSENSUS = "consensus"
    MAJORITY_VOTE = "majority_vote"
    MEDIATOR_DECISION = "mediator_decision"
    IMPASSE = "impasse"
    WITHDRAWN = "withdrawn"
    TIMEOUT = "timeout"


@dataclass
class Delegate:
    """A participant in the negotiation."""
    delegate_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    role: DelegateRole = DelegateRole.PROPOSER
    stance: str = ""
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    """A proposal made during negotiation."""
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    delegate_id: str = ""
    round_number: int = 0
    content: str = ""
    rationale: str = ""
    confidence: float = 0.5
    alternatives: list[str] = field(default_factory=list)
    votes_for: int = 0
    votes_against: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class NegotiationRound:
    """A single round in the negotiation process."""
    round_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    round_number: int = 0
    round_type: RoundType = RoundType.PROPOSAL
    proposals: list[Proposal] = field(default_factory=list)
    summary: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class NegotiationSession:
    """A complete negotiation session between agents."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    description: str = ""
    strategy: NegotiationStrategy = NegotiationStrategy.COLLABORATIVE
    delegates: dict[str, Delegate] = field(default_factory=dict)
    rounds: list[NegotiationRound] = field(default_factory=list)
    current_round: int = 0
    resolution: ResolutionType | None = None
    resolution_detail: str = ""
    status: str = "active"
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None


class AgentNegotiationProtocol:
    """Multi-agent negotiation and consensus protocol engine.

    Orchestrates structured negotiation between multiple agents, managing
    the full lifecycle from initialization through proposal rounds, deliberation,
    voting, and resolution. Supports multiple negotiation strategies adapted
    from game theory and collaborative decision-making frameworks.

    The protocol tracks delegate positions, proposals, counter-proposals,
    and builds toward consensus or majority resolution through iterative rounds.
    """

    MAX_ROUNDS: int = 10
    CONSENSUS_THRESHOLD: float = 0.75
    MAJORITY_THRESHOLD: float = 0.5

    def __init__(self) -> None:
        self._sessions: dict[str, NegotiationSession] = {}
        self._total_sessions: int = 0
        self._total_rounds: int = 0
        self._total_proposals: int = 0

    def create_session(
        self,
        topic: str,
        description: str = "",
        strategy: NegotiationStrategy = NegotiationStrategy.COLLABORATIVE,
    ) -> NegotiationSession:
        """Create a new negotiation session.

        Args:
            topic: The topic to negotiate.
            description: Context about the negotiation.
            strategy: The negotiation approach to use.

        Returns:
            A new NegotiationSession ready for delegates.
        """
        session = NegotiationSession(
            topic=topic,
            description=description,
            strategy=strategy,
        )
        self._sessions[session.session_id] = session
        self._total_sessions += 1
        return session

    def add_delegate(
        self,
        session_id: str,
        name: str,
        role: DelegateRole = DelegateRole.PROPOSER,
        stance: str = "",
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> Delegate | None:
        """Add a delegate to a negotiation session.

        Args:
            session_id: The session to add the delegate to.
            name: Name of the delegate.
            role: Their role in the negotiation.
            stance: Their initial position.
            priority: Priority level for weighted voting.
            metadata: Additional delegate information.

        Returns:
            The created Delegate, or None if session not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        delegate = Delegate(
            name=name,
            role=role,
            stance=stance,
            priority=priority,
            metadata=metadata or {},
        )
        session.delegates[delegate.delegate_id] = delegate
        return delegate

    def propose(
        self,
        session_id: str,
        delegate_id: str,
        content: str,
        rationale: str = "",
        confidence: float = 0.5,
        alternatives: list[str] | None = None,
    ) -> Proposal | None:
        """Submit a proposal from a delegate.

        Args:
            session_id: The session to propose in.
            delegate_id: The delegate making the proposal.
            content: The proposal content.
            rationale: Reasoning behind the proposal.
            confidence: Confidence in the proposal.
            alternatives: Alternative approaches considered.

        Returns:
            The created Proposal, or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        if delegate_id not in session.delegates:
            return None

        # Create or advance to next round
        if not session.rounds or session.rounds[-1].round_type in (
            RoundType.VOTING, RoundType.CLOSING
        ):
            session.current_round += 1
            if session.current_round > self.MAX_ROUNDS:
                session.resolution = ResolutionType.TIMEOUT
                session.resolution_detail = "Maximum rounds exceeded"
                session.status = "resolved"
                session.resolved_at = time.time()
                return None

            round_obj = NegotiationRound(
                round_number=session.current_round,
                round_type=RoundType.PROPOSAL,
            )
            session.rounds.append(round_obj)
            self._total_rounds += 1

        current_round = session.rounds[-1]
        proposal = Proposal(
            delegate_id=delegate_id,
            round_number=session.current_round,
            content=content,
            rationale=rationale,
            confidence=confidence,
            alternatives=alternatives or [],
        )
        current_round.proposals.append(proposal)
        self._total_proposals += 1
        return proposal

    def vote(
        self,
        session_id: str,
        proposal_id: str,
        delegate_id: str,
        approve: bool,
    ) -> bool:
        """Cast a vote on a proposal.

        Args:
            session_id: The session to vote in.
            proposal_id: The proposal to vote on.
            delegate_id: The delegate casting the vote.
            approve: Whether the delegate approves.

        Returns:
            True if vote was recorded, False otherwise.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        if delegate_id not in session.delegates:
            return False

        for rd in session.rounds:
            for prop in rd.proposals:
                if prop.proposal_id == proposal_id:
                    if approve:
                        prop.votes_for += 1
                    else:
                        prop.votes_against += 1
                    return True
        return False

    def deliberate(
        self,
        session_id: str,
        summary: str,
    ) -> NegotiationRound | None:
        """Add a deliberation round to the negotiation.

        Args:
            session_id: The session to deliberate in.
            summary: Summary of the deliberation.

        Returns:
            The created deliberation round, or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        session.current_round += 1
        if session.current_round > self.MAX_ROUNDS:
            session.resolution = ResolutionType.TIMEOUT
            session.resolution_detail = "Maximum rounds exceeded"
            session.status = "resolved"
            session.resolved_at = time.time()
            return None

        round_obj = NegotiationRound(
            round_number=session.current_round,
            round_type=RoundType.DELIBERATION,
            summary=summary,
        )
        session.rounds.append(round_obj)
        self._total_rounds += 1
        return round_obj

    def resolve(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Attempt to resolve the negotiation session.

        Analyzes all proposals and votes to determine the resolution.
        Uses the session's strategy to determine the resolution approach.

        Args:
            session_id: The session to resolve.

        Returns:
            Resolution summary dict, or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        total_delegates = len(session.delegates)
        if total_delegates == 0:
            session.resolution = ResolutionType.IMPASSE
            session.resolution_detail = "No delegates"
            session.status = "resolved"
            session.resolved_at = time.time()
            return {"resolution": "impasse", "detail": "No delegates"}

        # Collect all proposals
        all_proposals: list[Proposal] = []
        for rd in session.rounds:
            all_proposals.extend(rd.proposals)

        if not all_proposals:
            session.resolution = ResolutionType.IMPASSE
            session.resolution_detail = "No proposals made"
            session.status = "resolved"
            session.resolved_at = time.time()
            return {"resolution": "impasse", "detail": "No proposals made"}

        # Find the best proposal based on strategy
        if session.strategy == NegotiationStrategy.VOTING_BASED:
            best = max(all_proposals, key=lambda p: p.votes_for - p.votes_against)
            approval = best.votes_for / max(total_delegates, 1)
            if approval >= self.MAJORITY_THRESHOLD:
                session.resolution = ResolutionType.MAJORITY_VOTE
                session.resolution_detail = best.content
            else:
                session.resolution = ResolutionType.IMPASSE
                session.resolution_detail = "No majority reached"

        elif session.strategy == NegotiationStrategy.CONSENSUS_DRIVEN:
            best = max(all_proposals, key=lambda p: p.votes_for)
            approval = best.votes_for / max(total_delegates, 1)
            if approval >= self.CONSENSUS_THRESHOLD:
                session.resolution = ResolutionType.CONSENSUS
                session.resolution_detail = best.content
            else:
                session.resolution = ResolutionType.IMPASSE
                session.resolution_detail = "Consensus threshold not met"

        elif session.strategy == NegotiationStrategy.MEDIATED:
            # Mediator's decision is the highest-confidence proposal
            best = max(all_proposals, key=lambda p: p.confidence)
            session.resolution = ResolutionType.MEDIATOR_DECISION
            session.resolution_detail = best.content

        else:
            # Collaborative: pick proposal with highest net votes
            best = max(all_proposals, key=lambda p: p.votes_for - p.votes_against)
            approval = best.votes_for / max(total_delegates, 1)
            if approval >= self.MAJORITY_THRESHOLD:
                session.resolution = ResolutionType.MAJORITY_VOTE
            else:
                session.resolution = ResolutionType.CONSENSUS
            session.resolution_detail = best.content

        session.status = "resolved"
        session.resolved_at = time.time()

        return {
            "resolution": session.resolution.value if session.resolution else "unknown",
            "detail": session.resolution_detail,
            "total_rounds": session.current_round,
            "total_proposals": len(all_proposals),
            "total_delegates": total_delegates,
            "strategy": session.strategy.value,
            "session_id": session_id,
            "topic": session.topic,
        }

    def get_summary(self, session_id: str) -> dict[str, Any] | None:
        """Get a summary of the negotiation session.

        Args:
            session_id: The session to summarize.

        Returns:
            Summary dict with session state and statistics.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        all_proposals = []
        for rd in session.rounds:
            all_proposals.extend(rd.proposals)

        return {
            "session_id": session.session_id,
            "topic": session.topic,
            "strategy": session.strategy.value,
            "status": session.status,
            "current_round": session.current_round,
            "total_rounds": len(session.rounds),
            "total_delegates": len(session.delegates),
            "total_proposals": len(all_proposals),
            "delegates": [
                {
                    "delegate_id": d.delegate_id,
                    "name": d.name,
                    "role": d.role.value,
                    "stance": d.stance,
                }
                for d in session.delegates.values()
            ],
            "resolution": session.resolution.value if session.resolution else None,
            "resolution_detail": session.resolution_detail,
            "recent_proposals": [
                {
                    "proposal_id": p.proposal_id,
                    "content": p.content[:120],
                    "votes_for": p.votes_for,
                    "votes_against": p.votes_against,
                    "confidence": p.confidence,
                }
                for p in all_proposals[-5:]
            ],
        }

    def get_stats(self) -> dict[str, Any]:
        """Get protocol statistics."""
        resolution_counts: dict[str, int] = {}
        for session in self._sessions.values():
            if session.resolution:
                resolution_counts[session.resolution.value] = (
                    resolution_counts.get(session.resolution.value, 0) + 1
                )

        strategy_counts: dict[str, int] = {}
        for session in self._sessions.values():
            strategy_counts[session.strategy.value] = (
                strategy_counts.get(session.strategy.value, 0) + 1
            )

        return {
            "total_sessions": self._total_sessions,
            "total_rounds": self._total_rounds,
            "total_proposals": self._total_proposals,
            "active_sessions": sum(
                1 for s in self._sessions.values() if s.status == "active"
            ),
            "resolved_sessions": sum(
                1 for s in self._sessions.values() if s.status == "resolved"
            ),
            "resolution_distribution": resolution_counts,
            "strategy_usage": strategy_counts,
            "avg_rounds_per_session": round(
                self._total_rounds / max(self._total_sessions, 1), 1
            ),
            "avg_proposals_per_session": round(
                self._total_proposals / max(self._total_sessions, 1), 1
            ),
        }

    def reset(self) -> None:
        """Reset the protocol to initial state."""
        self._sessions.clear()
        self._total_sessions = 0
        self._total_rounds = 0
        self._total_proposals = 0


# ── Singleton accessors ──

_negotiation_protocol: AgentNegotiationProtocol | None = None


def get_negotiation_protocol() -> AgentNegotiationProtocol:
    """Get or create the singleton negotiation protocol."""
    global _negotiation_protocol
    if _negotiation_protocol is None:
        _negotiation_protocol = AgentNegotiationProtocol()
    return _negotiation_protocol


def reset_negotiation_protocol() -> None:
    """Reset the singleton negotiation protocol."""
    global _negotiation_protocol
    if _negotiation_protocol is not None:
        _negotiation_protocol.reset()
    _negotiation_protocol = None