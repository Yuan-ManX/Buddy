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
import math
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


@dataclass
class FusedKnowledge:
    """Unified knowledge from multi-agent fusion with conflict resolution."""
    id: str
    topic: str
    fused_content: str
    source_insights: list[str] = field(default_factory=list)
    confidence: float = 0.0
    dissenting_views: list[str] = field(default_factory=list)
    contributing_agents: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SharedPattern:
    """A pattern shared across agents for collaborative learning."""
    id: str
    pattern_type: InsightType
    description: str
    source_agents: list[str] = field(default_factory=list)
    adoption_count: int = 0
    success_rate: float = 0.0
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EmergentPatternDetail:
    """A pattern detected through cross-agent statistical analysis."""
    id: str
    description: str
    correlation_score: float = 0.0
    anomaly_score: float = 0.0
    participating_agents: list[str] = field(default_factory=list)
    supporting_evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentVote:
    """A vote from an agent on a collective decision."""
    agent_id: str
    agent_name: str
    decision_option: str
    confidence: float = 0.5
    rationale: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CollectiveDecision:
    """Result of multi-agent collective decision making."""
    id: str
    question: str
    options: dict[str, float] = field(default_factory=dict)
    winner: str = ""
    votes: list[AgentVote] = field(default_factory=list)
    consensus_level: float = 0.0
    dissenting_minority: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DistilledKnowledge:
    """Compressed, queryable knowledge from multi-agent insights."""
    id: str
    core_concepts: list[str] = field(default_factory=list)
    compressed_insights: dict[str, str] = field(default_factory=dict)
    source_agent_count: int = 0
    original_insight_count: int = 0
    compression_ratio: float = 0.0
    query_index: dict[str, list[str]] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TrustEdge:
    """A trust relationship between two agents."""
    source_agent: str
    target_agent: str
    trust_score: float = 0.5
    interaction_count: int = 0
    successful_exchanges: int = 0
    last_interaction: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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

        # Fusion and distillation storage
        self._fused_knowledge: list[FusedKnowledge] = []
        self._shared_patterns: list[SharedPattern] = []
        self._emergent_patterns_detailed: list[EmergentPatternDetail] = []
        self._collective_decisions: list[CollectiveDecision] = []
        self._distilled_knowledge_list: list[DistilledKnowledge] = []
        self._agent_expertise: dict[str, dict[str, float]] = defaultdict(dict)
        self._trust_edges: dict[str, dict[str, TrustEdge]] = defaultdict(dict)

        # Configuration
        self._max_contributions = 500
        self._max_reports = 50
        self._agreement_threshold = 0.7
        self._conflict_threshold = 0.5
        self._recency_weight_factor = 0.3
        self._adoption_threshold = 0.6
        self._anomaly_sensitivity = 2.0
        self._compression_target_ratio = 0.3

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

    # ── Cross-Agent Knowledge Fusion ─────────────────────

    def fuse_knowledge(self, min_contributors: int = 2) -> list[FusedKnowledge]:
        """Synthesize insights from multiple agents into unified knowledge.

        Groups contributions by topic, then applies confidence-weighted voting
        to produce a fused representation. Dissenting views are tracked to
        preserve minority perspectives alongside the majority consensus.
        """
        grouped: dict[str, list[AgentContribution]] = defaultdict(list)
        for contrib in self._contributions[-200:]:
            topic_key = self._extract_topic(contrib.content)
            grouped[topic_key].append(contrib)

        fused_results = []
        for topic_key, contributions in grouped.items():
            if len(contributions) < min_contributors:
                continue

            # Confidence-weighted voting for the fused representation
            weighted_sum = 0.0
            total_weight = 0.0
            dissenters: list[str] = []
            agents_seen: set[str] = set()

            for c in contributions:
                trust = self._agent_trust_scores.get(c.agent_id, 0.5)
                weight = c.confidence * trust
                weighted_sum += weight
                total_weight += trust
                agents_seen.add(c.agent_id)

                # Identify dissenting views: low-confidence contributions
                # from agents with decent trust scores
                if c.confidence < 0.4 and trust > 0.4:
                    dissenters.append(f"{c.agent_name}: {c.content[:100]}")

            fused_confidence = weighted_sum / max(total_weight, 0.001)

            # Build the fused content from the highest-confidence contribution
            best = max(contributions, key=lambda c: c.confidence * self._agent_trust_scores.get(c.agent_id, 0.5))
            fused_content = best.content

            fused = FusedKnowledge(
                id=f"fuse-{uuid.uuid4().hex[:8]}",
                topic=topic_key,
                fused_content=fused_content,
                source_insights=[c.content[:80] for c in contributions[:5]],
                confidence=round(fused_confidence, 4),
                dissenting_views=dissenters,
                contributing_agents=list(agents_seen),
            )
            fused_results.append(fused)
            self._fused_knowledge.append(fused)

        # Prune fused knowledge storage
        if len(self._fused_knowledge) > 200:
            self._fused_knowledge = self._fused_knowledge[-200:]

        return sorted(fused_results, key=lambda f: f.confidence, reverse=True)

    # ── Collaborative Learning Protocol ──────────────────

    def collaborative_learn_protocol(self) -> list[SharedPattern]:
        """Enable agents to share learned patterns and strategies.

        Extracts recurring patterns from agent contributions, creates a
        shared pattern repository that agents can adopt, and tracks the
        adoption rate and success of each shared pattern.
        """
        new_patterns = []

        # Cluster contributions by similarity to identify shareable patterns
        pattern_clusters: dict[str, dict[str, Any]] = {}
        for contrib in self._contributions[-150:]:
            key = self._extract_topic(contrib.content)
            if key not in pattern_clusters:
                pattern_clusters[key] = {
                    "descriptions": [],
                    "source_agents": set(),
                    "insight_type": contrib.insight_type,
                    "confidences": [],
                }
            cluster = pattern_clusters[key]
            cluster["descriptions"].append(contrib.content[:150])
            cluster["source_agents"].add(contrib.agent_id)
            cluster["confidences"].append(contrib.confidence)

        for key, cluster in pattern_clusters.items():
            if len(cluster["source_agents"]) < 2:
                continue

            avg_confidence = sum(cluster["confidences"]) / len(cluster["confidences"])
            if avg_confidence < self._adoption_threshold:
                continue

            # Check if this pattern already exists
            existing = any(
                p.description == cluster["descriptions"][0]
                for p in self._shared_patterns
            )
            if existing:
                continue

            pattern = SharedPattern(
                id=f"pat-{uuid.uuid4().hex[:8]}",
                pattern_type=cluster["insight_type"],
                description=cluster["descriptions"][0],
                source_agents=list(cluster["source_agents"]),
                adoption_count=len(cluster["source_agents"]),
                success_rate=avg_confidence,
                metadata={
                    "distinct_sources": len(cluster["source_agents"]),
                    "total_observations": len(cluster["descriptions"]),
                },
            )
            new_patterns.append(pattern)
            self._shared_patterns.append(pattern)

        # Prune shared patterns
        if len(self._shared_patterns) > 100:
            self._shared_patterns = self._shared_patterns[-100:]

        return new_patterns

    def adopt_pattern(self, agent_id: str, pattern_id: str) -> bool:
        """Record that an agent has adopted a shared pattern."""
        for pattern in self._shared_patterns:
            if pattern.id == pattern_id:
                pattern.adoption_count += 1
                if agent_id not in pattern.source_agents:
                    pattern.source_agents.append(agent_id)
                return True
        return False

    def get_shareable_patterns(self, agent_id: str) -> list[SharedPattern]:
        """Get patterns that an agent hasn't yet adopted."""
        return [
            p for p in self._shared_patterns
            if agent_id not in p.source_agents and p.success_rate >= self._adoption_threshold
        ]

    # ── Conflict Resolution Engine ───────────────────────

    def resolve_conflicts_with_provenance(self) -> list[KnowledgeConflict]:
        """Detect and resolve conflicting knowledge with provenance tracking.

        Uses confidence scoring, recency weighting, and source provenance
        to determine which knowledge claims should be preferred when
        multiple agents offer contradictory insights on the same topic.
        """
        resolved = []

        # Group by topic to find competing claims
        topic_groups: dict[str, list[AgentContribution]] = defaultdict(list)
        for contrib in self._contributions[-100:]:
            topic_key = self._extract_topic(contrib.content)
            topic_groups[topic_key].append(contrib)

        now = datetime.now(timezone.utc)

        for topic_key, contributions in topic_groups.items():
            if len(contributions) < 2:
                continue

            # Sort by composite score: confidence * trust * recency
            scored = []
            for c in contributions:
                trust = self._agent_trust_scores.get(c.agent_id, 0.5)
                # Recency weight: newer contributions get higher weight
                try:
                    contrib_time = datetime.fromisoformat(c.timestamp)
                    age_hours = (now - contrib_time).total_seconds() / 3600.0
                    recency = math.exp(-age_hours * self._recency_weight_factor)
                except (ValueError, TypeError):
                    recency = 0.5

                composite = c.confidence * trust * recency
                scored.append((c, trust, recency, composite))

            scored.sort(key=lambda x: x[3], reverse=True)

            best = scored[0]
            worst = scored[-1]

            # Conflict exists if composite scores differ significantly
            if best[3] - worst[3] > self._conflict_threshold and best[0].agent_id != worst[0].agent_id:
                resolution_parts = []
                resolution_parts.append(
                    f"Preferring {best[0].agent_name} (confidence={best[0].confidence:.2f}, "
                    f"trust={best[1]:.2f}, recency={best[2]:.2f})"
                )
                resolution_parts.append(
                    f"Over {worst[0].agent_name} (confidence={worst[0].confidence:.2f}, "
                    f"trust={worst[1]:.2f}, recency={worst[2]:.2f})"
                )

                conflict = KnowledgeConflict(
                    id=f"conf-{uuid.uuid4().hex[:8]}",
                    topic=topic_key,
                    agent_a=best[0].agent_id,
                    agent_b=worst[0].agent_id,
                    insight_a=f"{best[0].content[:100]} (composite={best[3]:.3f})",
                    insight_b=f"{worst[0].content[:100]} (composite={worst[3]:.3f})",
                    resolution=" | ".join(resolution_parts),
                    resolved=True,
                )
                resolved.append(conflict)
                self._conflicts.append(conflict)

        return resolved

    # ── Emergent Pattern Detection ───────────────────────

    def detect_emergent_patterns_statistical(self) -> list[EmergentPatternDetail]:
        """Detect patterns visible only when aggregating across multiple agents.

        Uses statistical correlation and anomaly detection to identify
        patterns that individual agents cannot observe in isolation.
        """
        results = []

        if len(self._contributions) < 10:
            return results

        # Build per-agent confidence vectors for correlation analysis
        agent_confidences: dict[str, list[float]] = defaultdict(list)
        for contrib in self._contributions[-100:]:
            agent_confidences[contrib.agent_id].append(contrib.confidence)

        # Correlation detection: compute pairwise correlation between agents'
        # confidence distributions to find agents whose behavior patterns
        # are statistically linked
        agent_ids = list(agent_confidences.keys())
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                agent_a = agent_ids[i]
                agent_b = agent_ids[j]
                vec_a = agent_confidences[agent_a]
                vec_b = agent_confidences[agent_b]

                correlation = self._compute_correlation(vec_a, vec_b)
                if correlation is not None and abs(correlation) > 0.7:
                    direction = "positively" if correlation > 0 else "negatively"
                    pattern = EmergentPatternDetail(
                        id=f"emer-{uuid.uuid4().hex[:8]}",
                        description=f"Agents {agent_a} and {agent_b} show {direction} "
                                     f"correlated behavior (r={correlation:.3f})",
                        correlation_score=abs(correlation),
                        anomaly_score=0.0,
                        participating_agents=[agent_a, agent_b],
                        supporting_evidence={
                            "correlation_coefficient": round(correlation, 4),
                            "samples_a": len(vec_a),
                            "samples_b": len(vec_b),
                        },
                    )
                    results.append(pattern)

        # Anomaly detection: identify agents whose contribution patterns
        # deviate significantly from the group norm
        all_confidences = [c.confidence for c in self._contributions[-100:]]
        if all_confidences:
            mean_conf = sum(all_confidences) / len(all_confidences)
            variance = sum((c - mean_conf) ** 2 for c in all_confidences) / len(all_confidences)
            std_dev = math.sqrt(variance) if variance > 0 else 0.001

            for agent_id, confidences in agent_confidences.items():
                agent_mean = sum(confidences) / len(confidences)
                z_score = abs(agent_mean - mean_conf) / std_dev

                if z_score > self._anomaly_sensitivity:
                    pattern = EmergentPatternDetail(
                        id=f"emer-{uuid.uuid4().hex[:8]}",
                        description=f"Agent {agent_id} shows anomalous confidence pattern "
                                     f"(z-score={z_score:.2f}, mean={agent_mean:.3f} vs group={mean_conf:.3f})",
                        correlation_score=0.0,
                        anomaly_score=round(z_score, 2),
                        participating_agents=[agent_id],
                        supporting_evidence={
                            "agent_mean": round(agent_mean, 4),
                            "group_mean": round(mean_conf, 4),
                            "group_std": round(std_dev, 4),
                            "z_score": round(z_score, 4),
                        },
                    )
                    results.append(pattern)

        # Store results
        for r in results:
            self._emergent_patterns_detailed.append(r)
        if len(self._emergent_patterns_detailed) > 100:
            self._emergent_patterns_detailed = self._emergent_patterns_detailed[-100:]

        return sorted(results, key=lambda p: p.correlation_score + p.anomaly_score, reverse=True)

    @staticmethod
    def _compute_correlation(vec_a: list[float], vec_b: list[float]) -> float | None:
        """Compute Pearson correlation between two confidence vectors."""
        n = min(len(vec_a), len(vec_b))
        if n < 3:
            return None

        a = vec_a[:n]
        b = vec_b[:n]

        mean_a = sum(a) / n
        mean_b = sum(b) / n

        cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
        std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
        std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b))

        if std_a == 0 or std_b == 0:
            return None

        return cov / (std_a * std_b)

    # ── Collective Decision Making ───────────────────────

    def make_collective_decision(
        self,
        question: str,
        options: list[str],
        agent_votes: list[dict] | None = None,
    ) -> CollectiveDecision:
        """Orchestrate multi-agent voting on a complex decision.

        Each agent's vote is weighted by their trust score and topic-specific
        expertise. The option with the highest weighted score wins. Dissenting
        minority views are preserved for transparency.
        """
        votes: list[AgentVote] = []
        option_scores: dict[str, float] = {opt: 0.0 for opt in options}

        if agent_votes:
            for vote_data in agent_votes:
                agent_id = vote_data.get("agent_id", "")
                agent_name = vote_data.get("agent_name", "")
                option = vote_data.get("option", "")
                confidence = vote_data.get("confidence", 0.5)
                rationale = vote_data.get("rationale", "")

                if option not in options:
                    continue

                vote = AgentVote(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    decision_option=option,
                    confidence=confidence,
                    rationale=rationale,
                )
                votes.append(vote)

                # Weighted contribution: trust score * confidence
                trust = self._agent_trust_scores.get(agent_id, 0.5)
                weight = trust * confidence
                option_scores[option] += weight

                # Update expertise tracking for this topic cluster
                topic = self._extract_topic(question)
                self._agent_expertise[agent_id][topic] = (
                    self._agent_expertise[agent_id].get(topic, 0.5) * 0.8 + confidence * 0.2
                )

        # Determine winner
        if option_scores:
            winner = max(option_scores, key=lambda k: option_scores[k])
        else:
            winner = ""

        # Calculate consensus level: ratio of winner score to total
        total_score = sum(option_scores.values())
        consensus = option_scores[winner] / total_score if total_score > 0 else 0.0

        # Identify dissenting minority
        dissenting = [
            f"{v.agent_name} voted '{v.decision_option}'"
            for v in votes
            if v.decision_option != winner
        ]

        decision = CollectiveDecision(
            id=f"dec-{uuid.uuid4().hex[:8]}",
            question=question,
            options=option_scores,
            winner=winner,
            votes=votes,
            consensus_level=round(consensus, 4),
            dissenting_minority=dissenting,
        )
        self._collective_decisions.append(decision)

        if len(self._collective_decisions) > 50:
            self._collective_decisions = self._collective_decisions[-50:]

        return decision

    # ── Knowledge Distillation ───────────────────────────

    def distill_knowledge(self) -> DistilledKnowledge:
        """Compress collective knowledge into a compact, queryable format.

        Takes the full set of agent contributions and fused knowledge,
        extracts core concepts, builds a compression dictionary, and
        creates an indexed structure for efficient retrieval.
        """
        all_insights = self._fused_knowledge[-50:] or []
        source_contributions = self._contributions[-200:]

        # Extract core concepts by identifying high-confidence, multi-agent topics
        core_concepts = []
        compressed: dict[str, str] = {}
        query_index: dict[str, list[str]] = defaultdict(list)

        for fused in all_insights:
            if fused.confidence >= self._agreement_threshold:
                # Create a compact concept key
                concept_key = f"concept:{fused.topic[:8]}"
                core_concepts.append(concept_key)

                # Compress: store only the fused content
                compressed[concept_key] = fused.fused_content[:200]

                # Build query index: map words to concept keys
                words = fused.fused_content.lower().split()[:10]
                for word in words:
                    word = word.strip(".,!?;:()[]{}\"'")
                    if len(word) > 2 and concept_key not in query_index[word]:
                        query_index[word].append(concept_key)

                # Also index by source agents
                for agent in fused.contributing_agents:
                    if concept_key not in query_index[f"agent:{agent}"]:
                        query_index[f"agent:{agent}"].append(concept_key)

        # Calculate compression ratio
        original_size = len(source_contributions)
        compressed_size = len(compressed)
        compression_ratio = 1.0 - (compressed_size / max(original_size, 1))

        distilled = DistilledKnowledge(
            id=f"dist-{uuid.uuid4().hex[:8]}",
            core_concepts=core_concepts,
            compressed_insights=compressed,
            source_agent_count=len(self._agent_trust_scores),
            original_insight_count=original_size,
            compression_ratio=round(compression_ratio, 4),
            query_index=dict(query_index),
        )
        self._distilled_knowledge_list.append(distilled)

        if len(self._distilled_knowledge_list) > 20:
            self._distilled_knowledge_list = self._distilled_knowledge_list[-20:]

        return distilled

    def query_distilled_knowledge(self, query: str) -> list[str]:
        """Query the most recent distilled knowledge by keyword."""
        if not self._distilled_knowledge_list:
            return []

        latest = self._distilled_knowledge_list[-1]
        results = []

        query_words = query.lower().split()
        for word in query_words:
            matches = latest.query_index.get(word, [])
            for concept_key in matches:
                content = latest.compressed_insights.get(concept_key, "")
                if content and concept_key not in results:
                    results.append(concept_key)

        return results

    # ── Trust Network ────────────────────────────────────

    def maintain_trust_network(
        self,
        from_agent: str,
        to_agent: str,
        interaction_quality: float = 0.5,
        successful: bool = True,
    ) -> TrustEdge:
        """Maintain a dynamic trust graph between agents.

        Updates trust scores based on the quality and reliability of
        knowledge shared between agents. Trust edges are bidirectional
        and decay over time when interactions cease.
        """
        # Get or create trust edge
        edge = self._trust_edges[from_agent].get(to_agent)
        if edge is None:
            edge = TrustEdge(
                source_agent=from_agent,
                target_agent=to_agent,
            )
            self._trust_edges[from_agent][to_agent] = edge

        # Update interaction metrics
        edge.interaction_count += 1
        if successful:
            edge.successful_exchanges += 1
        edge.last_interaction = datetime.now(timezone.utc).isoformat()

        # Update trust score with exponential moving average
        success_rate = edge.successful_exchanges / max(edge.interaction_count, 1)
        old_trust = edge.trust_score
        new_trust = old_trust * 0.85 + interaction_quality * success_rate * 0.15
        edge.trust_score = round(max(0.0, min(1.0, new_trust)), 4)

        # Also update the global agent trust score
        if to_agent in self._agent_trust_scores:
            self._agent_trust_scores[to_agent] = (
                self._agent_trust_scores[to_agent] * 0.9 + new_trust * 0.1
            )

        return edge

    def get_trust_edges(self, agent_id: str) -> list[TrustEdge]:
        """Get all trust relationships for an agent."""
        outgoing = list(self._trust_edges.get(agent_id, {}).values())
        incoming = [
            edge for aid, edges in self._trust_edges.items()
            if aid != agent_id
            for tid, edge in edges.items()
            if tid == agent_id
        ]
        return outgoing + incoming

    def get_trust_score(self, from_agent: str, to_agent: str) -> float:
        """Get the trust score between two agents."""
        edge = self._trust_edges.get(from_agent, {}).get(to_agent)
        return edge.trust_score if edge else 0.5

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict:
        """Get synthesis engine statistics."""
        trust_edge_count = sum(len(edges) for edges in self._trust_edges.values())
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
            "fused_knowledge_count": len(self._fused_knowledge),
            "shared_patterns_count": len(self._shared_patterns),
            "emergent_patterns_detailed": len(self._emergent_patterns_detailed),
            "collective_decisions_count": len(self._collective_decisions),
            "distilled_knowledge_count": len(self._distilled_knowledge_list),
            "trust_edges": trust_edge_count,
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