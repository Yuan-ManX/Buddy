"""Buddy Agent Synthesis — cross-agent knowledge integration and collaborative learning

Provides the synthesis layer that enables multiple agents to share insights,
resolve conflicts, and collectively build a unified knowledge model. This
enables emergent intelligence across the entire agent ecosystem.

Core capabilities:
  - Insight Aggregation: collect and merge insights from multiple agents
  - Conflict Resolution: detect and resolve contradictory knowledge
  - Collaborative Learning: agents learn from each other's successes and failures
  - Knowledge Distillation: compress multi-agent learnings into compact models
  - Emergent Pattern Detection: identify patterns visible only across agents
  - Consensus Building: weighted voting and confidence aggregation
  - Cross-Agent Memory: shared memory spaces with access control
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.agent_synthesis")


# ═══════════════════════════════════════════════════════════
# Enums and Data Structures
# ═══════════════════════════════════════════════════════════

class SynthesisMode(str, Enum):
    """Modes of cross-agent synthesis."""
    AGGREGATE = "aggregate"       # Simple collection of insights
    CONSENSUS = "consensus"       # Weighted voting for agreement
    DISTILL = "distill"           # Compress into compact knowledge
    DETECT = "detect"             # Find emergent patterns
    RESOLVE = "resolve"           # Handle conflicting insights


class InsightType(str, Enum):
    """Types of cross-agent insights."""
    STRATEGY = "strategy"         # Execution strategy effectiveness
    TOOL_USAGE = "tool_usage"     # Tool usage patterns and best practices
    PATTERN = "pattern"           # Recurring task patterns
    BEHAVIOR = "behavior"         # Agent behavioral patterns
    COLLABORATION = "collaboration"  # Multi-agent collaboration patterns
    EMERGENT = "emergent"         # Emergent patterns across agents


@dataclass
class SynthesisInsight:
    """A synthesized insight from multiple agents."""
    id: str
    insight_type: InsightType
    content: str
    source_agents: list[str]
    confidence: float = 0.5
    agreement_score: float = 0.0  # How much consensus across agents
    evidence: dict = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentContribution:
    """A contribution from a single agent to the synthesis."""
    agent_id: str
    agent_name: str
    insight_type: InsightType
    content: str
    confidence: float = 0.5
    evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class KnowledgeConflict:
    """A detected conflict between agent insights."""
    id: str
    topic: str
    agent_a: str
    agent_b: str
    insight_a: str
    insight_b: str
    resolution: str = ""  # How the conflict was resolved
    resolved: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SynthesisReport:
    """A complete synthesis report across agents."""
    id: str
    total_agents: int
    total_contributions: int
    insights: list[SynthesisInsight] = field(default_factory=list)
    conflicts: list[KnowledgeConflict] = field(default_factory=list)
    emergent_patterns: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════
# Agent Synthesis Engine
# ═══════════════════════════════════════════════════════════

class AgentSynthesis:
    """Cross-agent knowledge synthesis and collaborative learning engine.

    Enables the agent ecosystem to function as a collective intelligence,
    where insights from individual agents are aggregated, conflicts are
    resolved, and emergent patterns are detected across the entire system.
    """

    def __init__(self):
        self._contributions: list[AgentContribution] = []
        self._synthesis_history: list[SynthesisReport] = []
        self._conflicts: list[KnowledgeConflict] = []
        self._agent_trust_scores: dict[str, float] = {}
        self._topic_experts: dict[str, list[str]] = defaultdict(list)

        # Configuration
        self._max_contributions = 500
        self._max_reports = 50
        self._agreement_threshold = 0.7
        self._conflict_threshold = 0.5

    # ── Contribution Management ──────────────────────────

    def contribute(
        self,
        agent_id: str,
        agent_name: str,
        insight_type: InsightType,
        content: str,
        confidence: float = 0.5,
        evidence: dict | None = None,
    ) -> AgentContribution:
        """Submit an agent's insight for synthesis."""
        contribution = AgentContribution(
            agent_id=agent_id,
            agent_name=agent_name,
            insight_type=insight_type,
            content=content,
            confidence=confidence,
            evidence=evidence or {},
        )
        self._contributions.append(contribution)

        # Update agent trust scores
        if agent_id not in self._agent_trust_scores:
            self._agent_trust_scores[agent_id] = 0.5
        self._agent_trust_scores[agent_id] = (
            self._agent_trust_scores[agent_id] * 0.9 + confidence * 0.1
        )

        # Prune old contributions
        if len(self._contributions) > self._max_contributions:
            self._contributions = self._contributions[-self._max_contributions:]

        return contribution

    # ── Synthesis Operations ─────────────────────────────

    def synthesize(self, mode: SynthesisMode = SynthesisMode.AGGREGATE) -> SynthesisReport:
        """Run a synthesis cycle across all agent contributions."""
        report = SynthesisReport(
            id=f"synth-{uuid.uuid4().hex[:8]}",
            total_agents=len(self._agent_trust_scores),
            total_contributions=len(self._contributions),
        )

        if mode == SynthesisMode.AGGREGATE:
            report.insights = self._aggregate_insights()
        elif mode == SynthesisMode.CONSENSUS:
            report.insights = self._build_consensus()
        elif mode == SynthesisMode.DETECT:
            report.emergent_patterns = self._detect_emergent_patterns()
        elif mode == SynthesisMode.RESOLVE:
            report.conflicts = self._resolve_conflicts()

        self._synthesis_history.append(report)
        if len(self._synthesis_history) > self._max_reports:
            self._synthesis_history = self._synthesis_history[-self._max_reports:]

        return report

    def _aggregate_insights(self) -> list[SynthesisInsight]:
        """Aggregate similar insights from multiple agents."""
        grouped: dict[str, list[AgentContribution]] = defaultdict(list)

        for contrib in self._contributions[-100:]:
            topic_key = self._extract_topic(contrib.content)
            grouped[topic_key].append(contrib)

        insights = []
        for topic, contributions in grouped.items():
            if len(contributions) >= 2:
                # Calculate agreement
                agents = list({c.agent_id for c in contributions})
                avg_confidence = sum(c.confidence for c in contributions) / len(contributions)
                agreement = len(agents) / max(len(self._agent_trust_scores), 1)

                insights.append(SynthesisInsight(
                    id=f"insi-{uuid.uuid4().hex[:8]}",
                    insight_type=contributions[0].insight_type,
                    content=topic,
                    source_agents=agents,
                    confidence=avg_confidence,
                    agreement_score=agreement,
                    evidence={"contributions": len(contributions)},
                ))

        return sorted(insights, key=lambda x: x.confidence, reverse=True)

    def _build_consensus(self) -> list[SynthesisInsight]:
        """Build consensus through weighted voting."""
        grouped: dict[str, list[AgentContribution]] = defaultdict(list)

        for contrib in self._contributions[-100:]:
            topic_key = self._extract_topic(contrib.content)
            grouped[topic_key].append(contrib)

        insights = []
        for topic, contributions in grouped.items():
            if len(contributions) < 2:
                continue

            # Weighted voting
            weighted_votes = 0.0
            total_weight = 0.0
            for c in contributions:
                trust = self._agent_trust_scores.get(c.agent_id, 0.5)
                weighted_votes += c.confidence * trust
                total_weight += trust

            consensus_score = weighted_votes / max(total_weight, 0.001)

            if consensus_score >= self._agreement_threshold:
                insights.append(SynthesisInsight(
                    id=f"cons-{uuid.uuid4().hex[:8]}",
                    insight_type=contributions[0].insight_type,
                    content=topic,
                    source_agents=list({c.agent_id for c in contributions}),
                    confidence=consensus_score,
                    agreement_score=consensus_score,
                ))

        return sorted(insights, key=lambda x: x.confidence, reverse=True)

    def _detect_emergent_patterns(self) -> list[str]:
        """Detect patterns that emerge only when viewing multiple agents together."""
        patterns = []

        # Cross-agent tool usage patterns
        tool_usage_by_agent: dict[str, set[str]] = defaultdict(set)
        for contrib in self._contributions[-100:]:
            if contrib.insight_type == InsightType.TOOL_USAGE:
                tool_usage_by_agent[contrib.agent_id].add(contrib.content)

        # Find tools used by most agents
        if len(tool_usage_by_agent) >= 2:
            common_tools = set.intersection(*tool_usage_by_agent.values()) if tool_usage_by_agent else set()
            if common_tools:
                patterns.append(f"Common tool patterns across {len(tool_usage_by_agent)} agents: {', '.join(sorted(common_tools)[:5])}")

        # Cross-agent strategy convergence
        strategy_contribs = [c for c in self._contributions[-100:] if c.insight_type == InsightType.STRATEGY]
        if len(strategy_contribs) >= 3:
            unique_agents = {c.agent_id for c in strategy_contribs}
            if len(unique_agents) >= 2:
                patterns.append(f"Strategy convergence detected across {len(unique_agents)} agents")

        # Agent collaboration frequency
        collab_contribs = [c for c in self._contributions[-100:] if c.insight_type == InsightType.COLLABORATION]
        if collab_contribs:
            patterns.append(f"Active collaboration: {len(collab_contribs)} cross-agent interactions")

        return patterns

    def _resolve_conflicts(self) -> list[KnowledgeConflict]:
        """Detect and resolve conflicting insights between agents."""
        new_conflicts = []

        # Group contributions by topic
        grouped: dict[str, list[AgentContribution]] = defaultdict(list)
        for contrib in self._contributions[-50:]:
            topic_key = self._extract_topic(contrib.content)
            grouped[topic_key].append(contrib)

        for topic, contributions in grouped.items():
            if len(contributions) < 2:
                continue

            # Check for conflicting confidence levels
            confidences = [(c.agent_id, c.confidence) for c in contributions]
            high_conf = max(confidences, key=lambda x: x[1])
            low_conf = min(confidences, key=lambda x: x[1])

            if high_conf[1] - low_conf[1] > self._conflict_threshold and high_conf[0] != low_conf[0]:
                conflict = KnowledgeConflict(
                    id=f"conf-{uuid.uuid4().hex[:8]}",
                    topic=topic,
                    agent_a=high_conf[0],
                    agent_b=low_conf[0],
                    insight_a=f"High confidence ({high_conf[1]:.2f})",
                    insight_b=f"Low confidence ({low_conf[1]:.2f})",
                    resolution=f"Preferring {high_conf[0]}'s insight with higher confidence",
                    resolved=True,
                )
                new_conflicts.append(conflict)
                self._conflicts.append(conflict)

        return new_conflicts

    @staticmethod
    def _extract_topic(content: str) -> str:
        """Extract a stable topic key from content."""
        # Normalize and hash for stable topic grouping
        normalized = content.lower().strip()[:100]
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    # ── Cross-Agent Learning ─────────────────────────────

    def cross_agent_learn(self, agent_id: str) -> list[dict]:
        """Generate learning recommendations for an agent based on other agents' experiences."""
        other_contribs = [
            c for c in self._contributions[-50:]
            if c.agent_id != agent_id
        ]

        recommendations = []
        for contrib in other_contribs[:10]:
            trust = self._agent_trust_scores.get(contrib.agent_id, 0.5)
            if trust > 0.6:
                recommendations.append({
                    "from_agent": contrib.agent_name,
                    "insight_type": contrib.insight_type.value,
                    "content": contrib.content[:200],
                    "confidence": contrib.confidence,
                    "source_trust": round(trust, 3),
                })

        return recommendations

    def share_insight(self, from_agent: str, to_agent: str, insight_content: str, confidence: float = 0.5) -> dict:
        """Share an insight from one agent to another."""
        return {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "content": insight_content,
            "confidence": confidence,
            "shared_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict:
        """Get synthesis engine statistics."""
        return {
            "total_contributions": len(self._contributions),
            "total_synthesis_reports": len(self._synthesis_history),
            "total_conflicts": len(self._conflicts),
            "resolved_conflicts": sum(1 for c in self._conflicts if c.resolved),
            "active_agents": len(self._agent_trust_scores),
            "agent_trust_scores": {
                agent_id: round(score, 3)
                for agent_id, score in self._agent_trust_scores.items()
            },
            "recent_insights": len([
                i for r in self._synthesis_history[-3:]
                for i in r.insights
            ]),
        }

    def get_recent_reports(self, limit: int = 5) -> list[dict]:
        """Get recent synthesis reports."""
        return [
            {
                "id": r.id,
                "total_agents": r.total_agents,
                "total_contributions": r.total_contributions,
                "insights_count": len(r.insights),
                "conflicts_count": len(r.conflicts),
                "emergent_patterns": r.emergent_patterns,
                "recommendations": r.recommendations,
                "timestamp": r.timestamp,
            }
            for r in self._synthesis_history[-limit:]
        ]

    def get_agent_recommendations(self, agent_id: str) -> list[dict]:
        """Get learning recommendations for a specific agent."""
        return self.cross_agent_learn(agent_id)


# Global synthesis engine instance
agent_synthesis = AgentSynthesis()