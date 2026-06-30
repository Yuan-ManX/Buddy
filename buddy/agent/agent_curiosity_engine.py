"""Agent Curiosity Engine — intrinsic motivation for exploration.

This engine drives curiosity-driven behaviour by tracking novelty, surfacing
information gaps, and selecting exploration targets that maximize the agent's
long-term knowledge gain. It is intentionally dependency-free so it can run in
any Buddy runtime without extra packages.

Core capabilities:
  - Curiosity Profiles: per-agent baseline/current curiosity, satiation, and a
    novelty threshold, plus a short exploration history.
  - Novelty Detection: five metrics (euclidean, cosine, entropy, frequency,
    recency) score how novel an item is relative to prior observations.
  - Information Gaps: structured records of what the agent does not yet know,
    each carrying an estimated value and urgency.
  - Exploration Targets: candidate topics competing for selection based on
    novelty, information value, cost, and the agent's curiosity profile.
  - Exploration Results: outcomes that feed back into the profile by adjusting
    satiation and current curiosity, closing the intrinsic-motivation loop.
  - Exploration Modes: exploitation, balanced, exploration, and
    forced_exploration bias how novelty is weighed against value.
  - Thread Safety: all public mutation methods are guarded by a single lock.

Architecture:
    AgentCuriosityEngine (singleton)
    ├── CuriosityProfile      (per-agent curiosity state and history)
    ├── NoveltyScore          (per-item novelty measurement)
    ├── InformationGap        (a structured gap in knowledge)
    ├── ExplorationTarget     (a candidate topic to explore)
    ├── ExplorationResult     (the outcome of an exploration step)
    └── CuriosityStats        (aggregate counters across the whole engine)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CuriosityType(str, Enum):
    """The flavor of curiosity driving a target.

    Mirrors the common psychology taxonomy so downstream components can
    reason about *why* the agent wants to explore something.
    """

    DIVERSIVE = "diversive"      # restless seeking of any new stimulation
    SPECIFIC = "specific"        # targeted seeking of a particular topic
    PERCEPTUAL = "perceptual"    # driven by sensory novelty
    EPISTEMIC = "epistemic"      # driven by a desire for knowledge
    SOCIAL = "social"            # driven by other agents or people


class NoveltyMetric(str, Enum):
    """Metric used to quantify how novel an item is."""

    EUCLIDEAN = "euclidean"      # distance from previously seen items
    COSINE = "cosine"            # angular distance from prior items
    ENTROPY = "entropy"          # distributional entropy of the features
    FREQUENCY = "frequency"      # rarity based on observation count
    RECENCY = "recency"          # rarity based on time since last seen


class ExplorationMode(str, Enum):
    """Policy knob balancing novelty against exploitation."""

    EXPLOITATION = "exploitation"            # favor cheap, high-value targets
    BALANCED = "balanced"                    # weigh novelty and value evenly
    EXPLORATION = "exploration"              # favor novel, uncertain targets
    FORCED_EXPLORATION = "forced_exploration"  # always pick the most novel target


class CuriosityStatus(str, Enum):
    """Lifecycle state of an exploration target and the agent's curiosity."""

    IDLE = "idle"                # no active exploration
    SEEKING = "seeking"          # a target has been proposed and is waiting
    EXPLORING = "exploring"      # a target has been selected and is in progress
    SATISFIED = "satisfied"      # exploration completed and was rewarding
    SATED = "sated"              # exploration completed but yielded little value


class InformationGapType(str, Enum):
    """The shape of a gap in the agent's knowledge."""

    KNOWN_UNKNOWN = "known_unknown"            # aware of the missing piece
    UNKNOWN_UNKNOWN = "unknown_unknown"        # unaware until surfaced
    PARTIAL_KNOWLEDGE = "partial_knowledge"    # some fragments present
    CONFLICTING_KNOWLEDGE = "conflicting_knowledge"  # contradictory fragments


# ═══════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NoveltyScore:
    """How novel an item was judged to be at a point in time.

    ``factors`` carries the per-metric sub-scores that fed the final ``score``.
    """

    item_id: str
    score: float
    metric: NoveltyMetric
    computed_at: float = 0.0
    factors: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "score": self.score,
            "metric": self.metric.value,
            "computed_at": self.computed_at,
            "factors": dict(self.factors),
        }


@dataclass
class InformationGap:
    """A structured record of something the agent does not yet know."""
    gap_id: str
    agent_id: str
    topic: str
    gap_type: InformationGapType
    description: str = ""
    estimated_value: float = 0.5
    urgency: float = 0.0
    status: str = "open"  # "open" or "resolved"
    resolution: str = ""
    created_at: float = 0.0
    resolved_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "agent_id": self.agent_id,
            "topic": self.topic,
            "gap_type": self.gap_type.value,
            "description": self.description,
            "estimated_value": self.estimated_value,
            "urgency": self.urgency,
            "status": self.status,
            "resolution": self.resolution,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class ExplorationTarget:
    """A candidate topic the agent might explore.

    Priority is derived by the engine from the agent's profile and mode; a
    higher priority means the target is more likely to be selected.
    """

    target_id: str
    agent_id: str
    topic: str
    curiosity_type: CuriosityType = CuriosityType.EPISTEMIC
    novelty_score: float = 0.0
    information_value: float = 0.0
    estimated_cost: float = 0.0
    priority: float = 0.0
    status: CuriosityStatus = CuriosityStatus.SEEKING
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "agent_id": self.agent_id,
            "topic": self.topic,
            "curiosity_type": self.curiosity_type.value,
            "novelty_score": self.novelty_score,
            "information_value": self.information_value,
            "estimated_cost": self.estimated_cost,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at,
        }


@dataclass
class ExplorationResult:
    """The outcome of exploring a single target."""

    result_id: str
    target_id: str
    agent_id: str
    findings: str = ""
    knowledge_gained: float = 0.0
    satisfaction_score: float = 0.0
    duration: float = 0.0
    timestamp: float = 0.0
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "target_id": self.target_id,
            "agent_id": self.agent_id,
            "findings": self.findings,
            "knowledge_gained": self.knowledge_gained,
            "satisfaction_score": self.satisfaction_score,
            "duration": self.duration,
            "timestamp": self.timestamp,
            "success": self.success,
        }


@dataclass
class CuriosityProfile:
    """Per-agent curiosity state.

    ``current_curiosity`` drifts toward ``baseline_curiosity`` as
    ``satiation_level`` (raised by rewarding explorations) decays over time.
    """

    agent_id: str
    mode: ExplorationMode = ExplorationMode.BALANCED
    baseline_curiosity: float = 0.5
    current_curiosity: float = 0.5
    satiation_level: float = 0.0
    novelty_threshold: float = 0.3
    exploration_history: list[str] = field(default_factory=list)
    last_exploration_at: float = 0.0
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "mode": self.mode.value,
            "baseline_curiosity": self.baseline_curiosity,
            "current_curiosity": self.current_curiosity,
            "satiation_level": self.satiation_level,
            "novelty_threshold": self.novelty_threshold,
            "exploration_history": list(self.exploration_history),
            "last_exploration_at": self.last_exploration_at,
            "created_at": self.created_at,
        }


@dataclass
class CuriosityStats:
    """Aggregate counters describing the state of the whole engine."""

    total_targets: int = 0
    total_results: int = 0
    total_gaps: int = 0
    avg_satisfaction: float = 0.0
    targets_by_type: dict[str, int] = field(default_factory=dict)
    results_by_status: dict[str, int] = field(default_factory=dict)
    avg_novelty: float = 0.0
    avg_information_value: float = 0.0
    exploration_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_targets": self.total_targets,
            "total_results": self.total_results,
            "total_gaps": self.total_gaps,
            "avg_satisfaction": self.avg_satisfaction,
            "targets_by_type": dict(self.targets_by_type),
            "results_by_status": dict(self.results_by_status),
            "avg_novelty": self.avg_novelty,
            "avg_information_value": self.avg_information_value,
            "exploration_rate": self.exploration_rate,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

# How strongly each exploration mode biases toward novelty versus value.
# 0.0 means pure exploitation (value-driven), 1.0 means pure exploration
# (novelty-driven). The balanced mode sits in the middle.
_MODE_NOVELTY_BIAS: dict[ExplorationMode, float] = {
    ExplorationMode.EXPLOITATION: 0.1,
    ExplorationMode.BALANCED: 0.5,
    ExplorationMode.EXPLORATION: 0.8,
    ExplorationMode.FORCED_EXPLORATION: 1.0,
}

# Relative weight each curiosity type contributes to target priority.
# Epistemic curiosity tends to yield the most durable knowledge gain, so it
# gets the largest weight; perceptual curiosity is the most fleeting.
_CURIOSITY_TYPE_WEIGHT: dict[CuriosityType, float] = {
    CuriosityType.DIVERSIVE: 0.5,
    CuriosityType.SPECIFIC: 0.8,
    CuriosityType.PERCEPTUAL: 0.4,
    CuriosityType.EPISTEMIC: 1.0,
    CuriosityType.SOCIAL: 0.7,
}

# Time constant (seconds) used by the recency novelty metric. Items not seen
# for roughly this long are treated as fully novel again.
_RECENCY_TAU: float = 3600.0

# Per-second decay rate applied to satiation between explorations.
_SATIATION_DECAY_RATE: float = 1.0 / 1800.0  # ~30 minute half-life-ish

# Maximum number of exploration history entries retained per profile.
_MAX_HISTORY: int = 50

# Number of prior items a novelty comparison considers. Keeping a bound on the
# comparison set keeps novelty detection cheap as the agent's memory grows.
_NOVELTY_MEMORY_LIMIT: int = 256


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCuriosityEngine:
    """Intrinsic-motivation engine driving curiosity-driven exploration.

    Maintains per-agent curiosity profiles, a memory of observed items for
    novelty comparison, structured information gaps, exploration targets, and
    the results of past explorations. All public mutation methods are guarded
    by a single lock so the engine is safe to call from multiple threads.
    """

    MAX_TARGETS_PER_AGENT: int = 500
    MAX_GAPS_PER_AGENT: int = 500
    MAX_RESULTS_PER_TARGET: int = 100

    def __init__(self) -> None:
        self._profiles: dict[str, CuriosityProfile] = {}            # agent_id -> profile
        self._item_features: dict[str, dict[str, list[float]]] = {}  # agent_id -> {item_id -> vector}
        self._item_frequency: dict[str, dict[str, int]] = {}        # agent_id -> {item_id -> count}
        self._item_recency: dict[str, dict[str, float]] = {}        # agent_id -> {item_id -> last_seen}
        self._novelty_scores: dict[str, list[NoveltyScore]] = {}    # agent_id -> scores (newest last)
        self._gaps: dict[str, InformationGap] = {}                  # gap_id -> gap
        self._agent_gaps: dict[str, list[str]] = {}                 # agent_id -> [gap_id]
        self._targets: dict[str, ExplorationTarget] = {}            # target_id -> target
        self._agent_targets: dict[str, list[str]] = {}              # agent_id -> [target_id]
        self._results: dict[str, ExplorationResult] = {}            # result_id -> result
        self._target_results: dict[str, list[str]] = {}             # target_id -> [result_id]
        self._agent_results: dict[str, list[str]] = {}              # agent_id -> [result_id]
        self._lock = threading.Lock()

    # ───────────────────────────────────────────────────────────────────
    # Profile lifecycle
    # ───────────────────────────────────────────────────────────────────

    def register_profile(
        self,
        agent_id: str,
        mode: ExplorationMode = ExplorationMode.BALANCED,
        baseline_curiosity: float = 0.5,
    ) -> CuriosityProfile:
        """Register a curiosity profile for an agent, replacing any existing one.

        The agent's novelty memory is preserved across re-registration.
        """
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        if not (0.0 <= baseline_curiosity <= 1.0):
            raise ValueError("baseline_curiosity must be in [0.0, 1.0]")

        now = time.time()
        profile = CuriosityProfile(
            agent_id=agent_id,
            mode=mode,
            baseline_curiosity=baseline_curiosity,
            current_curiosity=baseline_curiosity,
            satiation_level=0.0,
            novelty_threshold=0.3,
            exploration_history=[],
            last_exploration_at=0.0,
            created_at=now,
        )
        with self._lock:
            self._profiles[agent_id] = profile
            self._item_features.setdefault(agent_id, {})
            self._item_frequency.setdefault(agent_id, {})
            self._item_recency.setdefault(agent_id, {})
            self._novelty_scores.setdefault(agent_id, [])
            self._agent_gaps.setdefault(agent_id, [])
            self._agent_targets.setdefault(agent_id, [])
            self._agent_results.setdefault(agent_id, [])
        return profile

    def get_profile(self, agent_id: str) -> CuriosityProfile | None:
        """Return the curiosity profile for ``agent_id``, or None."""
        with self._lock:
            return self._profiles.get(agent_id)

    def set_mode(self, agent_id: str, mode: ExplorationMode) -> CuriosityProfile:
        """Change an agent's exploration mode and recompute pending priorities."""
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                raise KeyError(f"Unknown agent_id: {agent_id}")
            profile.mode = mode
            # Recompute priorities for all of this agent's pending targets.
            for target_id in self._agent_targets.get(agent_id, []):
                target = self._targets.get(target_id)
                if target is None:
                    continue
                if target.status == CuriosityStatus.SEEKING:
                    target.priority = self._compute_priority_locked(profile, target)
            return profile

    # ───────────────────────────────────────────────────────────────────
    # Novelty detection
    # ───────────────────────────────────────────────────────────────────

    def detect_novelty(
        self,
        agent_id: str,
        item_id: str,
        features: list[float] | dict[str, float],
        metric: NoveltyMetric = NoveltyMetric.EUCLIDEAN,
    ) -> NoveltyScore:
        """Score how novel ``item_id`` is for ``agent_id``.

        ``features`` may be a dense vector or a sparse dict (converted using
        stable key ordering). The item is recorded in the agent's memory so
        later detections compare against it.
        """
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        if not item_id:
            raise ValueError("item_id must not be empty")

        vector = self._normalize_features(features)

        with self._lock:
            # Lazily create a profile if the agent was not registered, so
            # novelty detection works out of the box for new agents.
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = CuriosityProfile(
                    agent_id=agent_id,
                    mode=ExplorationMode.BALANCED,
                    baseline_curiosity=0.5,
                    current_curiosity=0.5,
                    created_at=time.time(),
                )
                self._profiles[agent_id] = profile

            memory = self._item_features.setdefault(agent_id, {})
            frequency = self._item_frequency.setdefault(agent_id, {})
            recency = self._item_recency.setdefault(agent_id, {})
            scores = self._novelty_scores.setdefault(agent_id, [])

            now = time.time()
            prior_vectors = list(memory.values())[-_NOVELTY_MEMORY_LIMIT:]
            count = frequency.get(item_id, 0)
            last_seen = recency.get(item_id, 0.0)

            factors: dict[str, Any] = {
                "observation_count": count,
                "memory_size": len(memory),
                "vector_dim": len(vector),
            }

            if metric == NoveltyMetric.EUCLIDEAN:
                score = self._novelty_euclidean(vector, prior_vectors)
            elif metric == NoveltyMetric.COSINE:
                score = self._novelty_cosine(vector, prior_vectors)
            elif metric == NoveltyMetric.ENTROPY:
                score = self._novelty_entropy(vector)
            elif metric == NoveltyMetric.FREQUENCY:
                score = self._novelty_frequency(count)
            elif metric == NoveltyMetric.RECENCY:
                score = self._novelty_recency(now, last_seen)
            else:  # pragma: no cover - guarded by the enum
                raise ValueError(f"Unknown novelty metric: {metric}")

            # Record the item in memory after computing the score so the
            # current item does not compare against itself.
            memory[item_id] = vector
            frequency[item_id] = count + 1
            recency[item_id] = now

            novelty = NoveltyScore(
                item_id=item_id,
                score=score,
                metric=metric,
                computed_at=now,
                factors=factors,
            )
            scores.append(novelty)
            # Cap the score log so it does not grow without bound.
            if len(scores) > _NOVELTY_MEMORY_LIMIT:
                del scores[: len(scores) - _NOVELTY_MEMORY_LIMIT]
            return novelty

    # ───────────────────────────────────────────────────────────────────
    # Information gaps
    # ───────────────────────────────────────────────────────────────────

    def identify_gap(
        self,
        agent_id: str,
        topic: str,
        gap_type: InformationGapType,
        description: str,
        estimated_value: float = 0.5,
        urgency: float = 0.0,
    ) -> InformationGap:
        """Record a new information gap for an agent."""
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        if not topic:
            raise ValueError("topic must not be empty")
        if not (0.0 <= estimated_value <= 1.0):
            raise ValueError("estimated_value must be in [0.0, 1.0]")
        if not (0.0 <= urgency <= 1.0):
            raise ValueError("urgency must be in [0.0, 1.0]")

        now = time.time()
        gap = InformationGap(
            gap_id=str(uuid.uuid4()),
            agent_id=agent_id,
            topic=topic,
            gap_type=gap_type,
            description=description,
            estimated_value=estimated_value,
            urgency=urgency,
            status="open",
            resolution="",
            created_at=now,
            resolved_at=None,
        )
        with self._lock:
            gap_ids = self._agent_gaps.setdefault(agent_id, [])
            open_count = sum(
                1
                for gid in gap_ids
                if self._gaps.get(gid) is not None
                and self._gaps[gid].status == "open"
            )
            if open_count >= self.MAX_GAPS_PER_AGENT:
                raise RuntimeError(
                    f"Agent {agent_id} already has the maximum of "
                    f"{self.MAX_GAPS_PER_AGENT} open gaps"
                )
            self._gaps[gap.gap_id] = gap
            gap_ids.append(gap.gap_id)
        return gap

    def get_gap(self, gap_id: str) -> InformationGap | None:
        """Return the gap with ``gap_id``, or None if not found."""
        with self._lock:
            return self._gaps.get(gap_id)

    def list_gaps(
        self,
        agent_id: str,
        status: str | None = None,
    ) -> list[InformationGap]:
        """Return gaps for ``agent_id``, optionally filtered by status."""
        with self._lock:
            gap_ids = self._agent_gaps.get(agent_id, [])
            gaps = [self._gaps[gid] for gid in gap_ids if gid in self._gaps]
            if status is None:
                return gaps
            return [g for g in gaps if g.status == status]

    def resolve_gap(self, gap_id: str, resolution: str) -> InformationGap:
        """Mark an information gap as resolved.

        Resolving a gap nudges the agent's current curiosity upward, since
        closing one gap often surfaces adjacent unknowns.
        """
        with self._lock:
            gap = self._gaps.get(gap_id)
            if gap is None:
                raise KeyError(f"Unknown gap_id: {gap_id}")
            if gap.status == "resolved":
                # Idempotent: re-resolving just updates the resolution text.
                gap.resolution = resolution
                return gap
            gap.status = "resolved"
            gap.resolution = resolution
            gap.resolved_at = time.time()
            # Closing a gap nudges curiosity upward for the owning agent.
            profile = self._profiles.get(gap.agent_id)
            if profile is not None:
                self._decay_satiation_locked(profile, gap.resolved_at)
                profile.current_curiosity = min(
                    1.0,
                    profile.current_curiosity + 0.05 * gap.estimated_value,
                )
            return gap

    # ───────────────────────────────────────────────────────────────────
    # Exploration targets
    # ───────────────────────────────────────────────────────────────────

    def propose_target(
        self,
        agent_id: str,
        topic: str,
        curiosity_type: CuriosityType = CuriosityType.EPISTEMIC,
        novelty_score: float = 0.0,
        information_value: float = 0.0,
        estimated_cost: float = 0.0,
    ) -> ExplorationTarget:
        """Propose a new exploration target for an agent."""
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        if not topic:
            raise ValueError("topic must not be empty")
        if not (0.0 <= novelty_score <= 1.0):
            raise ValueError("novelty_score must be in [0.0, 1.0]")
        if not (0.0 <= information_value <= 1.0):
            raise ValueError("information_value must be in [0.0, 1.0]")
        if estimated_cost < 0.0:
            raise ValueError("estimated_cost must be non-negative")

        now = time.time()
        target = ExplorationTarget(
            target_id=str(uuid.uuid4()),
            agent_id=agent_id,
            topic=topic,
            curiosity_type=curiosity_type,
            novelty_score=novelty_score,
            information_value=information_value,
            estimated_cost=estimated_cost,
            priority=0.0,
            status=CuriosityStatus.SEEKING,
            created_at=now,
        )
        with self._lock:
            target_ids = self._agent_targets.setdefault(agent_id, [])
            seeking_count = sum(
                1
                for tid in target_ids
                if self._targets.get(tid) is not None
                and self._targets[tid].status == CuriosityStatus.SEEKING
            )
            if seeking_count >= self.MAX_TARGETS_PER_AGENT:
                raise RuntimeError(
                    f"Agent {agent_id} already has the maximum of "
                    f"{self.MAX_TARGETS_PER_AGENT} seeking targets"
                )
            profile = self._profiles.get(agent_id)
            if profile is None:
                # Auto-register a default profile so targets can be proposed
                # without an explicit register_profile call.
                profile = CuriosityProfile(
                    agent_id=agent_id,
                    mode=ExplorationMode.BALANCED,
                    baseline_curiosity=0.5,
                    current_curiosity=0.5,
                    created_at=now,
                )
                self._profiles[agent_id] = profile
            target.priority = self._compute_priority_locked(profile, target)
            self._targets[target.target_id] = target
            target_ids.append(target.target_id)
        return target

    def get_target(self, target_id: str) -> ExplorationTarget | None:
        """Return the target with ``target_id``, or None if not found."""
        with self._lock:
            return self._targets.get(target_id)

    def list_targets(
        self,
        agent_id: str,
        status: CuriosityStatus | None = None,
    ) -> list[ExplorationTarget]:
        """Return targets for ``agent_id`` (optionally filtered) in priority order."""
        with self._lock:
            target_ids = self._agent_targets.get(agent_id, [])
            targets = [
                self._targets[tid] for tid in target_ids if tid in self._targets
            ]
            if status is not None:
                targets = [t for t in targets if t.status == status]
            targets.sort(key=lambda t: t.priority, reverse=True)
            return targets

    def select_target(self, agent_id: str) -> ExplorationTarget | None:
        """Select the best pending target for ``agent_id``.

        Selection considers the exploration mode, current curiosity,
        satiation, and each target's derived priority. The chosen target is
        moved to ``EXPLORING`` so it will not be picked again. Returns None
        when no pending target exists or the agent is too sated to explore.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return None
            now = time.time()
            # Apply time-based satiation decay before deciding.
            self._decay_satiation_locked(profile, now)

            # If the agent is completely sated it will not seek new targets.
            if profile.satiation_level >= 0.95:
                return None

            target_ids = self._agent_targets.get(agent_id, [])
            candidates: list[ExplorationTarget] = []
            for tid in target_ids:
                target = self._targets.get(tid)
                if target is None:
                    continue
                if target.status != CuriosityStatus.SEEKING:
                    continue
                # Recompute priority so time-decayed curiosity is reflected.
                target.priority = self._compute_priority_locked(profile, target)
                candidates.append(target)

            if not candidates:
                return None

            # Forced exploration always picks the most novel candidate.
            if profile.mode == ExplorationMode.FORCED_EXPLORATION:
                candidates.sort(key=lambda t: t.novelty_score, reverse=True)
            else:
                candidates.sort(key=lambda t: t.priority, reverse=True)

            chosen = candidates[0]
            chosen.status = CuriosityStatus.EXPLORING
            profile.last_exploration_at = now
            profile.current_curiosity = max(
                0.0, profile.current_curiosity - 0.02
            )
            return chosen

    # ───────────────────────────────────────────────────────────────────
    # Exploration results
    # ───────────────────────────────────────────────────────────────────

    def record_result(
        self,
        target_id: str,
        findings: str,
        knowledge_gained: float,
        satisfaction_score: float,
        duration: float,
        success: bool,
    ) -> ExplorationResult:
        """Record the outcome of exploring a target.

        Feeds back into the agent's profile: satiation rises with
        satisfaction, current curiosity moves toward baseline, and the
        target's status becomes ``SATISFIED`` or ``SATED``.
        """
        if not (0.0 <= knowledge_gained <= 1.0):
            raise ValueError("knowledge_gained must be in [0.0, 1.0]")
        if not (0.0 <= satisfaction_score <= 1.0):
            raise ValueError("satisfaction_score must be in [0.0, 1.0]")
        if duration < 0.0:
            raise ValueError("duration must be non-negative")

        now = time.time()
        with self._lock:
            target = self._targets.get(target_id)
            if target is None:
                raise KeyError(f"Unknown target_id: {target_id}")
            agent_id = target.agent_id

            result = ExplorationResult(
                result_id=str(uuid.uuid4()),
                target_id=target_id,
                agent_id=agent_id,
                findings=findings,
                knowledge_gained=knowledge_gained,
                satisfaction_score=satisfaction_score,
                duration=duration,
                timestamp=now,
                success=success,
            )
            self._results[result.result_id] = result

            target_results = self._target_results.setdefault(target_id, [])
            target_results.append(result.result_id)
            if len(target_results) > self.MAX_RESULTS_PER_TARGET:
                del target_results[: len(target_results) - self.MAX_RESULTS_PER_TARGET]

            agent_results = self._agent_results.setdefault(agent_id, [])
            agent_results.append(result.result_id)

            # Update the target's lifecycle status.
            if success and satisfaction_score >= 0.5:
                target.status = CuriosityStatus.SATISFIED
            else:
                target.status = CuriosityStatus.SATED

            # Feed back into the agent's curiosity profile.
            profile = self._profiles.get(agent_id)
            if profile is not None:
                self._decay_satiation_locked(profile, now)
                # Satiation rises with satisfaction, capped at 1.0.
                profile.satiation_level = min(
                    1.0,
                    profile.satiation_level + 0.3 * satisfaction_score,
                )
                # Satisfying explorations move curiosity toward baseline;
                # unsatisfying ones nudge curiosity up to keep searching.
                if satisfaction_score >= 0.5:
                    profile.current_curiosity = max(
                        profile.baseline_curiosity * 0.5,
                        profile.current_curiosity - 0.1 * satisfaction_score,
                    )
                else:
                    profile.current_curiosity = min(
                        1.0,
                        profile.current_curiosity + 0.05 * (1.0 - satisfaction_score),
                    )
                profile.last_exploration_at = now
                profile.exploration_history.append(target_id)
                if len(profile.exploration_history) > _MAX_HISTORY:
                    del profile.exploration_history[
                        : len(profile.exploration_history) - _MAX_HISTORY
                    ]
            return result

    def list_results(
        self,
        agent_id: str,
        target_id: str | None = None,
    ) -> list[ExplorationResult]:
        """Return results for ``agent_id`` (optionally filtered to a target), newest-first."""
        with self._lock:
            if target_id is not None:
                target = self._targets.get(target_id)
                if target is None or target.agent_id != agent_id:
                    return []
                result_ids = self._target_results.get(target_id, [])
                results = [
                    self._results[rid] for rid in result_ids if rid in self._results
                ]
                return list(reversed(results))
            result_ids = self._agent_results.get(agent_id, [])
            results = [
                self._results[rid] for rid in result_ids if rid in self._results
            ]
            return list(reversed(results))

    # ───────────────────────────────────────────────────────────────────
    # Stats
    # ───────────────────────────────────────────────────────────────────

    def get_stats(self) -> CuriosityStats:
        """Aggregate counters across the whole engine."""
        with self._lock:
            total_targets = len(self._targets)
            total_results = len(self._results)
            total_gaps = len(self._gaps)

            avg_satisfaction = (
                sum(r.satisfaction_score for r in self._results.values()) / total_results
                if total_results > 0
                else 0.0
            )

            if total_targets > 0:
                avg_novelty = sum(
                    t.novelty_score for t in self._targets.values()
                ) / total_targets
                avg_information_value = sum(
                    t.information_value for t in self._targets.values()
                ) / total_targets
            else:
                avg_novelty = 0.0
                avg_information_value = 0.0

            targets_by_type: dict[str, int] = {}
            for target in self._targets.values():
                key = target.curiosity_type.value
                targets_by_type[key] = targets_by_type.get(key, 0) + 1

            results_by_status: dict[str, int] = {}
            # Tally terminal target statuses as a proxy for result outcomes.
            for target in self._targets.values():
                if target.status in (CuriosityStatus.SATISFIED, CuriosityStatus.SATED):
                    key = target.status.value
                    results_by_status[key] = results_by_status.get(key, 0) + 1
            # Fold in the explicit success/failure flag from results.
            for result in self._results.values():
                key = "success" if result.success else "failure"
                results_by_status[key] = results_by_status.get(key, 0) + 1

            # Exploration rate: fraction of targets with at least one result.
            if total_targets > 0:
                explored = sum(
                    1 for tid in self._targets if self._target_results.get(tid)
                )
                exploration_rate = explored / total_targets
            else:
                exploration_rate = 0.0

            return CuriosityStats(
                total_targets=total_targets,
                total_results=total_results,
                total_gaps=total_gaps,
                avg_satisfaction=avg_satisfaction,
                targets_by_type=targets_by_type,
                results_by_status=results_by_status,
                avg_novelty=avg_novelty,
                avg_information_value=avg_information_value,
                exploration_rate=exploration_rate,
            )

    # ───────────────────────────────────────────────────────────────────
    # Internal helpers (must be called while holding self._lock)
    # ───────────────────────────────────────────────────────────────────

    def _compute_priority_locked(
        self,
        profile: CuriosityProfile,
        target: ExplorationTarget,
    ) -> float:
        """Compute a target's priority given the agent's profile.

        Blends novelty and information value per the exploration mode, scales
        by the curiosity type weight and current curiosity, penalizes cost,
        and suppresses via satiation. Caller must hold ``self._lock``.
        """
        novelty_bias = _MODE_NOVELTY_BIAS.get(profile.mode, 0.5)
        type_weight = _CURIOSITY_TYPE_WEIGHT.get(target.curiosity_type, 0.5)

        # novelty_bias=0 → purely value-driven; =1 → purely novelty-driven.
        blended = (
            novelty_bias * target.novelty_score
            + (1.0 - novelty_bias) * target.information_value
        )
        cost_penalty = 1.0 / (1.0 + target.estimated_cost)
        curiosity_drive = max(0.0, profile.current_curiosity - profile.satiation_level)

        priority = (
            blended
            * type_weight
            * cost_penalty
            * (0.25 + 0.75 * curiosity_drive)
        )
        return max(0.0, priority)

    def _decay_satiation_locked(
        self,
        profile: CuriosityProfile,
        now: float,
    ) -> None:
        """Apply time-based decay to satiation and curiosity drift to baseline.

        Caller must hold ``self._lock``.
        """
        if profile.last_exploration_at <= 0.0:
            return
        elapsed = now - profile.last_exploration_at
        if elapsed <= 0.0:
            return
        decay = math.exp(-_SATIATION_DECAY_RATE * elapsed)
        profile.satiation_level = profile.satiation_level * decay
        delta = profile.baseline_curiosity - profile.current_curiosity
        profile.current_curiosity = profile.current_curiosity + delta * (1.0 - decay)

    @staticmethod
    def _normalize_features(
        features: list[float] | dict[str, float],
    ) -> list[float]:
        """Convert a feature argument into a dense float vector.

        Sparse dicts are ordered by key for deterministic output. Non-numeric
        values are coerced to float; values that cannot be coerced become 0.0.
        """
        if isinstance(features, dict):
            ordered = sorted(features.items())
            vector: list[float] = []
            for _, raw in ordered:
                try:
                    vector.append(float(raw))
                except (TypeError, ValueError):
                    vector.append(0.0)
            return vector
        if isinstance(features, list):
            vector = []
            for raw in features:
                try:
                    vector.append(float(raw))
                except (TypeError, ValueError):
                    vector.append(0.0)
            return vector
        raise TypeError(
            "features must be a list[float] or dict[str, float], "
            f"got {type(features).__name__}"
        )

    @staticmethod
    def _novelty_euclidean(
        vector: list[float],
        prior: list[list[float]],
    ) -> float:
        """Euclidean novelty: normalized distance to the nearest prior item."""
        if not prior:
            return 1.0
        dim = max(1, len(vector))
        norm = math.sqrt(dim)
        best = float("inf")
        for other in prior:
            dist = AgentCuriosityEngine._euclidean_distance(vector, other)
            if dist < best:
                best = dist
        return max(0.0, min(1.0, best / norm))

    @staticmethod
    def _novelty_cosine(
        vector: list[float],
        prior: list[list[float]],
    ) -> float:
        """Cosine novelty: 1 minus the maximum cosine similarity to priors."""
        if not prior:
            return 1.0
        best_sim = 0.0
        for other in prior:
            sim = AgentCuriosityEngine._cosine_similarity(vector, other)
            if sim > best_sim:
                best_sim = sim
        # Clamp into [0, 1]; negative similarities are treated as fully novel.
        best_sim = max(0.0, min(1.0, best_sim))
        return max(0.0, min(1.0, 1.0 - best_sim))

    @staticmethod
    def _novelty_entropy(vector: list[float]) -> float:
        """Entropy novelty: normalized Shannon entropy of the feature vector.

        A uniform feature distribution yields the highest entropy and is
        treated as the most novel. Non-positive values are clamped to zero.
        """
        if not vector:
            return 0.0
        clamped = [max(0.0, float(v)) for v in vector]
        total = sum(clamped)
        if total <= 0.0:
            return 0.0
        entropy = 0.0
        for v in clamped:
            p = v / total
            if p > 0.0:
                entropy -= p * math.log(p)
        max_entropy = math.log(len(clamped))
        if max_entropy <= 0.0:
            return 0.0
        return max(0.0, min(1.0, entropy / max_entropy))

    @staticmethod
    def _novelty_frequency(count: int) -> float:
        """Frequency novelty: 1 / (1 + count). Unseen items score 1.0."""
        return 1.0 / (1.0 + float(max(0, count)))

    @staticmethod
    def _novelty_recency(now: float, last_seen: float) -> float:
        """Recency novelty: 1 - exp(-elapsed / tau). Unseen items score 1.0."""
        if last_seen <= 0.0:
            return 1.0
        elapsed = max(0.0, now - last_seen)
        return 1.0 - math.exp(-elapsed / _RECENCY_TAU)

    @staticmethod
    def _euclidean_distance(a: list[float], b: list[float]) -> float:
        """Euclidean distance between two vectors of possibly differing length."""
        n = max(len(a), len(b))
        total = 0.0
        for i in range(n):
            av = a[i] if i < len(a) else 0.0
            bv = b[i] if i < len(b) else 0.0
            diff = av - bv
            total += diff * diff
        return math.sqrt(total)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors of possibly differing length."""
        n = max(len(a), len(b))
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for i in range(n):
            av = a[i] if i < len(a) else 0.0
            bv = b[i] if i < len(b) else 0.0
            dot += av * bv
            norm_a += av * av
            norm_b += bv * bv
        if norm_a <= 0.0 or norm_b <= 0.0:
            return 0.0
        return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


# ═══════════════════════════════════════════════════════════════════════════
# Singleton access
# ═══════════════════════════════════════════════════════════════════════════

_global_curiosity_engine: AgentCuriosityEngine | None = None
_global_curiosity_engine_lock = threading.Lock()


def get_curiosity_engine() -> AgentCuriosityEngine:
    """Get or create the singleton curiosity engine."""
    global _global_curiosity_engine
    with _global_curiosity_engine_lock:
        if _global_curiosity_engine is None:
            _global_curiosity_engine = AgentCuriosityEngine()
        return _global_curiosity_engine


def reset_curiosity_engine() -> None:
    """Reset the singleton curiosity engine.

    Mainly useful in tests where a fresh engine is needed between cases.
    """
    global _global_curiosity_engine
    with _global_curiosity_engine_lock:
        _global_curiosity_engine = None
