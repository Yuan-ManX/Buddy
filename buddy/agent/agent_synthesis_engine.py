"""
Buddy Collaborative Synthesis Engine - Multi-agent output fusion and orchestration.

A sophisticated synthesis engine that combines outputs from multiple specialized
agents into coherent, unified results. Supports weighted fusion, conflict
resolution, consensus building, and quality assurance across agent contributions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FusionStrategy(str, Enum):
    """Strategies for fusing multiple agent outputs."""
    WEIGHTED_AVERAGE = "weighted_average"
    BEST_OF_N = "best_of_n"
    CONSENSUS = "consensus"
    HIERARCHICAL = "hierarchical"
    ENSEMBLE = "ensemble"
    ROUND_ROBIN = "round_robin"


class ConflictResolution(str, Enum):
    """How to resolve conflicts between agent outputs."""
    MAJORITY_VOTE = "majority_vote"
    HIGHEST_CONFIDENCE = "highest_confidence"
    EXPERT_OVERRIDE = "expert_override"
    MEDIATION = "mediation"
    HYBRID = "hybrid"


class ContributionRole(str, Enum):
    """Role of an agent in the synthesis process."""
    PRIMARY = "primary"
    REVIEWER = "reviewer"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"
    CREATIVE = "creative"


@dataclass
class AgentContribution:
    """A single agent's contribution to the synthesis."""
    contribution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: str = ""
    agent_role: ContributionRole = ContributionRole.PRIMARY
    content: str = ""
    confidence: float = 0.0
    quality_score: float = 0.0
    key_points: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class SynthesisSession:
    """A multi-agent synthesis session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    description: str = ""
    contributions: list[AgentContribution] = field(default_factory=list)
    fusion_strategy: FusionStrategy = FusionStrategy.WEIGHTED_AVERAGE
    conflict_resolution: ConflictResolution = ConflictResolution.HIGHEST_CONFIDENCE
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


@dataclass
class SynthesisResult:
    """The final synthesized output."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = ""
    topic: str = ""
    final_content: str = ""
    confidence: float = 0.0
    quality_score: float = 0.0
    consensus_level: float = 0.0
    contributions_count: int = 0
    conflicts_resolved: int = 0
    key_insights: list[str] = field(default_factory=list)
    dissenting_views: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class CollaborativeSynthesisEngine:
    """Multi-agent output fusion and synthesis orchestration engine.

    Combines contributions from multiple specialized agents into coherent,
    unified results. Manages the full synthesis lifecycle from session
    creation through contribution collection, conflict resolution, and
    final output generation.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SynthesisSession] = {}
        self._results: list[SynthesisResult] = []
        self._total_sessions: int = 0
        self._total_syntheses: int = 0

    # ── Session Management ───────────────────────────────────────

    def create_session(
        self,
        topic: str,
        description: str = "",
        fusion_strategy: FusionStrategy = FusionStrategy.WEIGHTED_AVERAGE,
        conflict_resolution: ConflictResolution = ConflictResolution.HIGHEST_CONFIDENCE,
    ) -> SynthesisSession:
        """Create a new synthesis session.

        Args:
            topic: The topic or question to synthesize.
            description: Detailed description of the synthesis goal.
            fusion_strategy: How to combine agent outputs.
            conflict_resolution: How to resolve disagreements.

        Returns:
            The created SynthesisSession.
        """
        session = SynthesisSession(
            topic=topic,
            description=description,
            fusion_strategy=fusion_strategy,
            conflict_resolution=conflict_resolution,
        )
        self._sessions[session.session_id] = session
        self._total_sessions += 1
        return session

    def add_contribution(
        self,
        session_id: str,
        agent_name: str,
        content: str,
        agent_role: ContributionRole = ContributionRole.PRIMARY,
        confidence: float = 0.5,
        quality_score: float = 0.5,
        key_points: list[str] | None = None,
        references: list[str] | None = None,
    ) -> AgentContribution | None:
        """Add an agent's contribution to a synthesis session.

        Args:
            session_id: The session to contribute to.
            agent_name: Name of the contributing agent.
            content: The agent's output content.
            agent_role: The agent's role in synthesis.
            confidence: Agent's confidence in its contribution.
            quality_score: Quality assessment of the contribution.
            key_points: Key points extracted from the contribution.
            references: References or sources cited.

        Returns:
            The created AgentContribution or None if session not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        contribution = AgentContribution(
            agent_name=agent_name,
            agent_role=agent_role,
            content=content,
            confidence=confidence,
            quality_score=quality_score,
            key_points=key_points or [],
            references=references or [],
        )
        session.contributions.append(contribution)
        return contribution

    def synthesize(self, session_id: str) -> SynthesisResult | None:
        """Execute the synthesis process for a session.

        Collects all contributions, applies the fusion strategy, resolves
        conflicts, and generates the final synthesized output.

        Args:
            session_id: The session to synthesize.

        Returns:
            The SynthesisResult or None if session not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        if not session.contributions:
            return None

        # Resolve conflicts
        conflicts_resolved = self._resolve_conflicts(session)

        # Apply fusion strategy
        final_content, confidence = self._apply_fusion(session)

        # Extract key insights
        key_insights = self._extract_insights(session)

        # Identify dissenting views
        dissenting = self._identify_dissenting(session)

        # Compute consensus level
        consensus = self._compute_consensus(session)

        result = SynthesisResult(
            session_id=session_id,
            topic=session.topic,
            final_content=final_content,
            confidence=confidence,
            quality_score=self._compute_quality(session),
            consensus_level=consensus,
            contributions_count=len(session.contributions),
            conflicts_resolved=conflicts_resolved,
            key_insights=key_insights,
            dissenting_views=dissenting,
        )

        session.status = "completed"
        session.completed_at = time.time()
        self._results.append(result)
        self._total_syntheses += 1
        return result

    def _resolve_conflicts(self, session: SynthesisSession) -> int:
        """Resolve conflicts between agent contributions."""
        conflicts = 0
        if len(session.contributions) < 2:
            return 0

        strategy = session.conflict_resolution

        for i, contrib_a in enumerate(session.contributions):
            for contrib_b in session.contributions[i + 1:]:
                # Simple conflict detection: check for contradictory key points
                if self._has_conflict(contrib_a, contrib_b):
                    conflicts += 1
                    if strategy == ConflictResolution.HIGHEST_CONFIDENCE:
                        # Lower confidence contribution gets adjusted
                        if contrib_a.confidence < contrib_b.confidence:
                            contrib_a.quality_score *= 0.8
                        else:
                            contrib_b.quality_score *= 0.8
                    elif strategy == ConflictResolution.EXPERT_OVERRIDE:
                        # Primary/reviewer roles override others
                        self._apply_expert_override(contrib_a, contrib_b)
                    elif strategy == ConflictResolution.MAJORITY_VOTE:
                        # Both get slight penalty until consensus
                        contrib_a.quality_score *= 0.9
                        contrib_b.quality_score *= 0.9

        return conflicts

    def _has_conflict(
        self, a: AgentContribution, b: AgentContribution
    ) -> bool:
        """Detect if two contributions have conflicting viewpoints."""
        # Simple heuristic: check confidence-weighted content similarity
        if a.confidence > 0.7 and b.confidence > 0.7:
            # Both are confident - check if key points diverge
            a_points = set(a.key_points)
            b_points = set(b.key_points)
            if a_points and b_points:
                overlap = len(a_points & b_points)
                total = len(a_points | b_points)
                if total > 0 and overlap / total < 0.3:
                    return True
        return False

    def _apply_expert_override(
        self, a: AgentContribution, b: AgentContribution
    ) -> None:
        """Apply expert role-based override for conflict resolution."""
        role_priority = {
            ContributionRole.PRIMARY: 4,
            ContributionRole.REVIEWER: 3,
            ContributionRole.VALIDATOR: 3,
            ContributionRole.SYNTHESIZER: 2,
            ContributionRole.CRITIC: 1,
            ContributionRole.CREATIVE: 1,
        }
        if role_priority.get(a.agent_role, 0) > role_priority.get(b.agent_role, 0):
            b.quality_score *= 0.7
        else:
            a.quality_score *= 0.7

    def _apply_fusion(
        self, session: SynthesisSession
    ) -> tuple[str, float]:
        """Apply the fusion strategy to combine contributions."""
        strategy = session.fusion_strategy
        contributions = session.contributions

        if strategy == FusionStrategy.BEST_OF_N:
            best = max(contributions, key=lambda c: c.confidence * c.quality_score)
            return best.content, best.confidence

        elif strategy == FusionStrategy.CONSENSUS:
            return self._consensus_fusion(contributions)

        elif strategy == FusionStrategy.HIERARCHICAL:
            return self._hierarchical_fusion(contributions)

        elif strategy == FusionStrategy.ENSEMBLE:
            return self._ensemble_fusion(contributions)

        elif strategy == FusionStrategy.ROUND_ROBIN:
            return self._round_robin_fusion(contributions)

        else:  # WEIGHTED_AVERAGE
            return self._weighted_fusion(contributions)

    def _weighted_fusion(
        self, contributions: list[AgentContribution]
    ) -> tuple[str, float]:
        """Weighted average fusion based on confidence and quality."""
        total_weight = sum(
            c.confidence * c.quality_score for c in contributions
        )
        if total_weight == 0:
            return "No consensus reached.", 0.0

        # Build weighted summary
        parts: list[str] = []
        for c in sorted(
            contributions,
            key=lambda x: x.confidence * x.quality_score,
            reverse=True,
        ):
            weight = (c.confidence * c.quality_score) / total_weight
            parts.append(f"[{c.agent_name} (weight: {weight:.2f})]: {c.content}")

        fused = (
            f"Weighted Synthesis ({len(contributions)} contributors):\n\n"
            + "\n\n".join(parts)
        )
        avg_confidence = sum(c.confidence for c in contributions) / len(contributions)
        return fused, avg_confidence

    def _consensus_fusion(
        self, contributions: list[AgentContribution]
    ) -> tuple[str, float]:
        """Consensus-based fusion seeking agreement."""
        # Find commonly agreed points
        all_points: list[str] = []
        for c in contributions:
            all_points.extend(c.key_points)

        # Count point frequency
        from collections import Counter
        point_counts = Counter(all_points)
        consensus_points = [
            point for point, count in point_counts.items()
            if count >= len(contributions) * 0.5
        ]

        fused = (
            f"Consensus Synthesis ({len(contributions)} agents):\n\n"
            f"Agreed Points: {', '.join(consensus_points) if consensus_points else 'None'}\n\n"
            + "\n\n".join(c.content for c in contributions)
        )
        consensus_level = (
            len(consensus_points) / len(set(all_points)) if all_points else 0.0
        )
        return fused, consensus_level

    def _hierarchical_fusion(
        self, contributions: list[AgentContribution]
    ) -> tuple[str, float]:
        """Hierarchical fusion prioritizing primary contributors."""
        # Sort by role priority
        role_priority = {
            ContributionRole.PRIMARY: 0,
            ContributionRole.SYNTHESIZER: 1,
            ContributionRole.REVIEWER: 2,
            ContributionRole.VALIDATOR: 3,
            ContributionRole.CREATIVE: 4,
            ContributionRole.CRITIC: 5,
        }
        sorted_contribs = sorted(
            contributions, key=lambda c: role_priority.get(c.agent_role, 3)
        )

        primary = sorted_contribs[0]
        others = sorted_contribs[1:]

        fused = (
            f"Hierarchical Synthesis:\n\n"
            f"Primary ({primary.agent_name}): {primary.content}\n\n"
            f"Supporting Contributions:\n"
            + "\n".join(f"- {c.agent_name}: {c.content[:200]}..." for c in others)
        )
        return fused, primary.confidence

    def _ensemble_fusion(
        self, contributions: list[AgentContribution]
    ) -> tuple[str, float]:
        """Ensemble fusion combining all contributions equally."""
        parts = [
            f"Agent {c.agent_name} ({c.agent_role.value}): {c.content}"
            for c in contributions
        ]
        fused = (
            f"Ensemble Synthesis ({len(contributions)} agents):\n\n"
            + "\n\n---\n\n".join(parts)
        )
        avg_conf = sum(c.confidence for c in contributions) / len(contributions)
        return fused, avg_conf

    def _round_robin_fusion(
        self, contributions: list[AgentContribution]
    ) -> tuple[str, float]:
        """Round-robin fusion taking turns from each agent."""
        fused = "Round-Robin Synthesis:\n\n"
        for i, c in enumerate(contributions):
            fused += f"Round {i+1} - {c.agent_name}: {c.content[:300]}\n\n"
        avg_conf = sum(c.confidence for c in contributions) / len(contributions)
        return fused, avg_conf

    def _extract_insights(self, session: SynthesisSession) -> list[str]:
        """Extract key insights from all contributions."""
        insights: list[str] = []
        for c in session.contributions:
            if c.key_points:
                insights.extend(c.key_points)
        # Deduplicate and return top insights
        seen: set[str] = set()
        unique: list[str] = []
        for insight in insights:
            if insight.lower() not in seen:
                seen.add(insight.lower())
                unique.append(insight)
        return unique[:10]

    def _identify_dissenting(self, session: SynthesisSession) -> list[str]:
        """Identify dissenting views from contributions."""
        if len(session.contributions) < 2:
            return []

        # Find the majority view
        points_counter: dict[str, int] = {}
        for c in session.contributions:
            for point in c.key_points:
                points_counter[point] = points_counter.get(point, 0) + 1

        majority_threshold = len(session.contributions) * 0.5
        dissenting: list[str] = []
        for point, count in points_counter.items():
            if count == 1:  # Only one agent holds this view
                dissenting.append(point)

        return dissenting[:5]

    def _compute_consensus(self, session: SynthesisSession) -> float:
        """Compute the consensus level across contributions."""
        if len(session.contributions) < 2:
            return 1.0

        # Compute confidence variance
        confidences = [c.confidence for c in session.contributions]
        mean_conf = sum(confidences) / len(confidences)
        variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)

        # Lower variance = higher consensus
        consensus = max(0.0, 1.0 - variance)
        return round(consensus, 3)

    def _compute_quality(self, session: SynthesisSession) -> float:
        """Compute overall quality score."""
        if not session.contributions:
            return 0.0
        return sum(c.quality_score for c in session.contributions) / len(
            session.contributions
        )

    # ── Query & Stats ────────────────────────────────────────────

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        return {
            "session_id": session.session_id,
            "topic": session.topic,
            "description": session.description,
            "contributions_count": len(session.contributions),
            "fusion_strategy": session.fusion_strategy.value,
            "conflict_resolution": session.conflict_resolution.value,
            "status": session.status,
            "contributions": [
                {
                    "contribution_id": c.contribution_id,
                    "agent_name": c.agent_name,
                    "agent_role": c.agent_role.value,
                    "confidence": c.confidence,
                    "quality_score": c.quality_score,
                    "key_points": c.key_points,
                }
                for c in session.contributions
            ],
        }

    def get_stats(self) -> dict[str, Any]:
        """Get synthesis engine statistics."""
        return {
            "total_sessions": self._total_sessions,
            "total_syntheses": self._total_syntheses,
            "active_sessions": len(self._sessions),
            "total_results": len(self._results),
            "avg_confidence": round(
                sum(r.confidence for r in self._results) / len(self._results), 3
            ) if self._results else 0.0,
            "avg_consensus": round(
                sum(r.consensus_level for r in self._results) / len(self._results), 3
            ) if self._results else 0.0,
        }

    def get_recent_results(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent synthesis results."""
        return [
            {
                "result_id": r.result_id,
                "topic": r.topic,
                "final_content": r.final_content[:500],
                "confidence": r.confidence,
                "quality_score": r.quality_score,
                "consensus_level": r.consensus_level,
                "contributions_count": r.contributions_count,
                "conflicts_resolved": r.conflicts_resolved,
                "key_insights": r.key_insights,
                "dissenting_views": r.dissenting_views,
            }
            for r in self._results[-limit:]
        ]

    def reset(self) -> None:
        """Reset the synthesis engine to initial state."""
        self._sessions.clear()
        self._results.clear()
        self._total_sessions = 0
        self._total_syntheses = 0


# ── Singleton Access ───────────────────────────────────────────────

_synthesis_engine: CollaborativeSynthesisEngine | None = None


def get_synthesis_engine() -> CollaborativeSynthesisEngine:
    """Get or create the singleton synthesis engine instance."""
    global _synthesis_engine
    if _synthesis_engine is None:
        _synthesis_engine = CollaborativeSynthesisEngine()
    return _synthesis_engine


def reset_synthesis_engine() -> None:
    """Reset the singleton synthesis engine."""
    global _synthesis_engine
    if _synthesis_engine:
        _synthesis_engine.reset()
    _synthesis_engine = None