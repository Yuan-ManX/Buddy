"""
Buddy Experience Engine — comprehensive agentic experience management

Central experience system that captures, compresses, replays, and evolves
agent behavior through structured experience records. Provides the foundation
for continuous learning, strategy adaptation, and cross-agent knowledge sharing.

Core subsystems:
  - ExperienceRecorder: structured capture of agent interactions
  - ExperienceReplayBuffer: prioritized sampling for learning
  - AgentTrajectoryCompressor: efficient trajectory compression
  - ExperienceEvolver: behavior evolution from historical patterns
  - ExperienceAnalytics: performance insights and trend analysis
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.experience_engine")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExperienceKind(str, Enum):
    """Categories of agent experiences."""
    CONVERSATION = "conversation"
    TOOL_EXECUTION = "tool_execution"
    TASK_COMPLETION = "task_completion"
    ERROR_RECOVERY = "error_recovery"
    COLLABORATION = "collaboration"
    DECISION_MAKING = "decision_making"


class ExperienceResult(str, Enum):
    """Possible outcomes of an agent experience."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    ABORTED = "aborted"


class EmotionalValence(str, Enum):
    """Emotional tone of agent interactions."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"
    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ExperienceEntry:
    """A structured record of a single agent interaction or event."""

    id: str = field(default_factory=lambda: f"exp-{uuid.uuid4().hex[:12]}")
    kind: ExperienceKind = ExperienceKind.CONVERSATION
    result: ExperienceResult = ExperienceResult.SUCCESS
    agent_id: str = ""
    session_id: str = ""
    task_signature: str = ""

    # Rich metadata
    context: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL

    # Content
    action_description: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)

    # Learning metadata
    reward: float = 0.0
    priority: float = 0.5
    importance_weight: float = 1.0
    confidence: float = 0.5

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    compressed_at: str | None = None
    evolved_at: str | None = None

    # Compression state
    is_compressed: bool = False
    compressed_summary: str = ""
    original_size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "result": self.result.value,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "task_signature": self.task_signature,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "cost": round(self.cost, 6),
            "emotional_valence": self.emotional_valence.value,
            "action_description": self.action_description[:300],
            "tool_name": self.tool_name,
            "observations": self.observations,
            "insights": self.insights,
            "reward": round(self.reward, 4),
            "priority": round(self.priority, 4),
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "is_compressed": self.is_compressed,
            "compressed_summary": self.compressed_summary[:500],
        }

    def compute_priority(self) -> float:
        """Compute priority score based on multiple signals."""
        base = 0.5

        # Outcome-based adjustments
        if self.result == ExperienceResult.FAILURE:
            base = max(base, 0.75)
        elif self.result == ExperienceResult.ABORTED:
            base = max(base, 0.7)
        elif self.result == ExperienceResult.PARTIAL:
            base = max(base, 0.6)

        # Reward-based adjustment
        if self.reward < -0.5:
            base = max(base, 0.8)
        elif self.reward > 0.5:
            base = max(base, 0.6)

        # Emotional valence signals
        if self.emotional_valence in (EmotionalValence.FRUSTRATED, EmotionalValence.NEGATIVE):
            base = max(base, 0.7)

        # Novelty bonus for error recovery
        if self.kind == ExperienceKind.ERROR_RECOVERY:
            base = min(1.0, base + 0.1)

        self.priority = round(min(1.0, max(0.01, base)), 4)
        return self.priority


@dataclass
class CompressedTrajectory:
    """A compressed version of an agent execution trajectory."""

    id: str = field(default_factory=lambda: f"ct-{uuid.uuid4().hex[:8]}")
    source_experience_ids: list[str] = field(default_factory=list)
    agent_id: str = ""
    session_id: str = ""

    # Compressed content
    summary: str = ""
    key_decision_points: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    critical_context: dict[str, Any] = field(default_factory=dict)
    extracted_patterns: list[str] = field(default_factory=list)

    # Metrics
    original_step_count: int = 0
    compressed_step_count: int = 0
    tokens_saved: int = 0
    compression_ratio: float = 0.0
    result: str = "success"

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "summary": self.summary,
            "key_decision_points": self.key_decision_points,
            "tools_used": self.tools_used,
            "extracted_patterns": self.extracted_patterns,
            "original_step_count": self.original_step_count,
            "compressed_step_count": self.compressed_step_count,
            "tokens_saved": self.tokens_saved,
            "compression_ratio": round(self.compression_ratio, 2),
            "result": self.result,
            "created_at": self.created_at,
        }


@dataclass
class StrategyAdaptation:
    """A strategy adaptation derived from experience evolution."""

    id: str = field(default_factory=lambda: f"strat-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    trigger_pattern: str = ""
    adapted_from: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    confidence: float = 0.5
    usage_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AnalyticsReport:
    """Analytics summary for experience data."""

    total_experiences: int = 0
    total_compressed: int = 0
    total_strategies: int = 0
    success_rate: float = 0.0
    avg_tokens_per_experience: float = 0.0
    avg_latency_ms: float = 0.0
    total_cost: float = 0.0
    result_distribution: dict[str, int] = field(default_factory=dict)
    kind_distribution: dict[str, int] = field(default_factory=dict)
    tool_success_rates: dict[str, float] = field(default_factory=dict)
    bottleneck_tools: list[str] = field(default_factory=list)
    learning_curve_data: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# 1. Experience Recorder
# ---------------------------------------------------------------------------

class ExperienceRecorder:
    """Captures agent interactions as structured experiences.

    Records agent actions, tool executions, conversations, and decisions
    with full metadata. Supports automatic compression of old experiences
    while preserving key learnings in the compressed summaries.
    """

    DEFAULT_MAX_EXPERIENCES = 10000
    AUTO_COMPRESS_THRESHOLD = 1000
    COMPRESS_BATCH_SIZE = 100

    def __init__(self, max_experiences: int = DEFAULT_MAX_EXPERIENCES):
        self.max_experiences = max_experiences
        self._experiences: dict[str, ExperienceEntry] = {}
        self._by_agent: dict[str, list[str]] = defaultdict(list)
        self._by_session: dict[str, list[str]] = defaultdict(list)
        self._by_kind: dict[str, list[str]] = defaultdict(list)
        self._total_recorded: int = 0

    def record(
        self,
        agent_id: str,
        kind: ExperienceKind,
        result: ExperienceResult,
        *,
        session_id: str = "",
        task_signature: str = "",
        context: dict[str, Any] | None = None,
        tokens_used: int = 0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL,
        action_description: str = "",
        tool_name: str = "",
        tool_args: dict[str, Any] | None = None,
        observations: list[str] | None = None,
        insights: list[str] | None = None,
        reward: float = 0.0,
        confidence: float = 0.5,
    ) -> ExperienceEntry:
        """Record a new agent experience with full metadata.

        Returns the created ExperienceEntry for further processing.
        """
        entry = ExperienceEntry(
            kind=kind,
            result=result,
            agent_id=agent_id,
            session_id=session_id,
            task_signature=task_signature,
            context=context or {},
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            cost=cost,
            emotional_valence=emotional_valence,
            action_description=action_description,
            tool_name=tool_name,
            tool_args=tool_args or {},
            observations=observations or [],
            insights=insights or [],
            reward=reward,
            confidence=confidence,
        )

        # Compute priority from outcome signals
        entry.compute_priority()

        # Store original size estimate for compression metrics
        entry.original_size_bytes = len(json.dumps(entry.to_dict(), default=str).encode("utf-8"))

        self._experiences[entry.id] = entry
        self._by_agent[agent_id].append(entry.id)
        if session_id:
            self._by_session[session_id].append(entry.id)
        self._by_kind[kind.value].append(entry.id)
        self._total_recorded += 1

        # Enforce capacity
        if len(self._experiences) > self.max_experiences:
            self._prune_oldest()

        logger.debug(
            f"Experience recorded: {entry.id} kind={kind.value} "
            f"result={result.value} priority={entry.priority:.3f}"
        )
        return entry

    def record_conversation(
        self,
        agent_id: str,
        result: ExperienceResult,
        context: dict[str, Any],
        *,
        session_id: str = "",
        tokens_used: int = 0,
        cost: float = 0.0,
        insights: list[str] | None = None,
    ) -> ExperienceEntry:
        """Shorthand for recording a conversation experience."""
        return self.record(
            agent_id=agent_id,
            kind=ExperienceKind.CONVERSATION,
            result=result,
            session_id=session_id,
            context=context,
            tokens_used=tokens_used,
            cost=cost,
            insights=insights or [],
        )

    def record_tool_execution(
        self,
        agent_id: str,
        tool_name: str,
        result: ExperienceResult,
        *,
        session_id: str = "",
        tool_args: dict[str, Any] | None = None,
        latency_ms: float = 0.0,
        tokens_used: int = 0,
        cost: float = 0.0,
        reward: float = 0.0,
        observations: list[str] | None = None,
    ) -> ExperienceEntry:
        """Shorthand for recording a tool execution experience."""
        return self.record(
            agent_id=agent_id,
            kind=ExperienceKind.TOOL_EXECUTION,
            result=result,
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args or {},
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost=cost,
            reward=reward,
            observations=observations or [],
        )

    def record_task_completion(
        self,
        agent_id: str,
        task_signature: str,
        result: ExperienceResult,
        *,
        session_id: str = "",
        tokens_used: int = 0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        reward: float = 0.0,
        insights: list[str] | None = None,
    ) -> ExperienceEntry:
        """Shorthand for recording a task completion experience."""
        return self.record(
            agent_id=agent_id,
            kind=ExperienceKind.TASK_COMPLETION,
            result=result,
            session_id=session_id,
            task_signature=task_signature,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            cost=cost,
            reward=reward,
            insights=insights or [],
        )

    def record_error_recovery(
        self,
        agent_id: str,
        error_context: dict[str, Any],
        result: ExperienceResult,
        *,
        session_id: str = "",
        insights: list[str] | None = None,
    ) -> ExperienceEntry:
        """Shorthand for recording an error recovery experience."""
        return self.record(
            agent_id=agent_id,
            kind=ExperienceKind.ERROR_RECOVERY,
            result=result,
            session_id=session_id,
            context=error_context,
            emotional_valence=EmotionalValence.FRUSTRATED if result == ExperienceResult.FAILURE else EmotionalValence.CONFIDENT,
            insights=insights or [],
        )

    def get(self, experience_id: str) -> ExperienceEntry | None:
        """Retrieve an experience by ID."""
        return self._experiences.get(experience_id)

    def get_by_agent(
        self,
        agent_id: str,
        limit: int = 100,
        kind: ExperienceKind | None = None,
    ) -> list[ExperienceEntry]:
        """Get experiences for a specific agent, optionally filtered by kind."""
        ids = self._by_agent.get(agent_id, [])
        entries = [self._experiences[eid] for eid in ids if eid in self._experiences]
        if kind:
            entries = [e for e in entries if e.kind == kind]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    def get_by_session(self, session_id: str, limit: int = 100) -> list[ExperienceEntry]:
        """Get all experiences for a session."""
        ids = self._by_session.get(session_id, [])
        entries = [self._experiences[eid] for eid in ids if eid in self._experiences]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    def get_by_kind(self, kind: ExperienceKind, limit: int = 100) -> list[ExperienceEntry]:
        """Get experiences by kind."""
        ids = self._by_kind.get(kind.value, [])
        entries = [self._experiences[eid] for eid in ids if eid in self._experiences]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    def auto_compress_old(self) -> list[ExperienceEntry]:
        """Compress old experiences by summarizing them.

        Experiences older than the auto-compress threshold are marked
        as compressed and their key learnings are preserved in
        compressed_summary while discarding detailed context.
        """
        if len(self._experiences) < self.AUTO_COMPRESS_THRESHOLD:
            return []

        sorted_entries = sorted(
            self._experiences.values(),
            key=lambda e: e.created_at,
        )

        compressed: list[ExperienceEntry] = []
        for entry in sorted_entries[:self.COMPRESS_BATCH_SIZE]:
            if entry.is_compressed:
                continue

            # Generate compressed summary
            parts = [
                f"Kind: {entry.kind.value}",
                f"Result: {entry.result.value}",
            ]
            if entry.action_description:
                parts.append(f"Action: {entry.action_description[:100]}")
            if entry.tool_name:
                parts.append(f"Tool: {entry.tool_name}")
            if entry.insights:
                parts.append(f"Insights: {'; '.join(entry.insights[:3])}")

            entry.compressed_summary = " | ".join(parts)
            entry.is_compressed = True
            entry.compressed_at = datetime.now(timezone.utc).isoformat()

            # Clear detailed context to save memory
            entry.context = {}
            entry.observations = []

            compressed.append(entry)

        if compressed:
            logger.info(
                f"Auto-compressed {len(compressed)} old experiences "
                f"(threshold={self.AUTO_COMPRESS_THRESHOLD})"
            )

        return compressed

    def _prune_oldest(self):
        """Remove the oldest experiences when over capacity."""
        if not self._experiences:
            return

        # Sort by creation time, remove oldest first
        sorted_ids = sorted(
            self._experiences.keys(),
            key=lambda eid: self._experiences[eid].created_at,
        )
        to_remove = sorted_ids[: len(self._experiences) - self.max_experiences]

        for eid in to_remove:
            entry = self._experiences.pop(eid, None)
            if entry:
                self._by_agent[entry.agent_id].remove(eid)
                if entry.session_id:
                    self._by_session[entry.session_id].remove(eid)
                self._by_kind[entry.kind.value].remove(eid)

        if to_remove:
            logger.debug(f"Pruned {len(to_remove)} oldest experiences (capacity={self.max_experiences})")

    def get_stats(self) -> dict[str, Any]:
        """Get recorder statistics."""
        total = len(self._experiences)
        compressed_count = sum(1 for e in self._experiences.values() if e.is_compressed)

        results = defaultdict(int)
        kinds = defaultdict(int)
        for e in self._experiences.values():
            results[e.result.value] += 1
            kinds[e.kind.value] += 1

        return {
            "total_experiences": total,
            "total_recorded": self._total_recorded,
            "compressed": compressed_count,
            "compression_ratio": f"{compressed_count / max(total, 1) * 100:.1f}%",
            "max_capacity": self.max_experiences,
            "utilization": f"{total / max(self.max_experiences, 1) * 100:.1f}%",
            "result_distribution": dict(results),
            "kind_distribution": dict(kinds),
            "agents_tracked": len(self._by_agent),
            "sessions_tracked": len(self._by_session),
        }

    def export(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Export experiences for persistence."""
        return [e.to_dict() for e in list(self._experiences.values())[:limit]]

    def import_experiences(self, data: list[dict[str, Any]]):
        """Import experiences from exported data."""
        for d in data:
            entry = ExperienceEntry(
                id=d.get("id", f"exp-{uuid.uuid4().hex[:12]}"),
                kind=ExperienceKind(d.get("kind", "conversation")),
                result=ExperienceResult(d.get("result", "success")),
                agent_id=d.get("agent_id", ""),
                session_id=d.get("session_id", ""),
                task_signature=d.get("task_signature", ""),
                tokens_used=d.get("tokens_used", 0),
                latency_ms=d.get("latency_ms", 0.0),
                cost=d.get("cost", 0.0),
                emotional_valence=EmotionalValence(d.get("emotional_valence", "neutral")),
                action_description=d.get("action_description", ""),
                tool_name=d.get("tool_name", ""),
                tool_args=d.get("tool_args", {}),
                insights=d.get("insights", []),
                reward=d.get("reward", 0.0),
                priority=d.get("priority", 0.5),
                confidence=d.get("confidence", 0.5),
                is_compressed=d.get("is_compressed", False),
                compressed_summary=d.get("compressed_summary", ""),
            )
            self._experiences[entry.id] = entry
            self._by_agent[entry.agent_id].append(entry.id)
            if entry.session_id:
                self._by_session[entry.session_id].append(entry.id)
            self._by_kind[entry.kind.value].append(entry.id)


# ---------------------------------------------------------------------------
# 2. Experience Replay Buffer
# ---------------------------------------------------------------------------

class ExperienceReplayBuffer:
    """Prioritized replay buffer for agent learning from experiences.

    Maintains a buffer of experiences with priority-based sampling.
    Uses importance weighting to focus learning on high-value experiences
    (failures, errors, high-reward outcomes) while still providing
    exposure to diverse experiences through stochastic sampling.

    Temporal difference storage tracks how priorities change over time,
    enabling the buffer to identify experiences that are consistently
    valuable for learning.
    """

    DEFAULT_CAPACITY = 5000
    PRIORITY_EPSILON = 0.01
    ALPHA = 0.6  # Priority exponent for sampling
    BETA = 0.4   # Importance sampling correction exponent
    NOVELTY_BOOST = 0.15
    ERROR_BOOST = 0.2
    DECAY_FACTOR = 0.95

    def __init__(self, capacity: int = DEFAULT_CAPACITY):
        self.capacity = capacity
        self._buffer: list[ExperienceEntry] = []
        self._priority_history: dict[str, list[float]] = defaultdict(list)
        self._total_sampled: int = 0
        self._total_added: int = 0

    def add(self, entry: ExperienceEntry):
        """Add an experience to the replay buffer.

        Priority is boosted for failures, errors, and novel experiences
        to ensure they are sampled more frequently during replay.
        """
        # Boost priority for learning-relevant experiences
        if entry.result == ExperienceResult.FAILURE:
            entry.priority = min(1.0, entry.priority + self.ERROR_BOOST)
        if entry.kind == ExperienceKind.ERROR_RECOVERY:
            entry.priority = min(1.0, entry.priority + self.NOVELTY_BOOST)

        # Track priority history
        self._priority_history[entry.id].append(entry.priority)

        self._buffer.append(entry)
        self._total_added += 1

        # Evict if over capacity
        if len(self._buffer) > self.capacity:
            self._evict_lowest_priority()

        logger.debug(
            f"Buffer added: {entry.id} priority={entry.priority:.3f} "
            f"buffer_size={len(self._buffer)}"
        )

    def sample(
        self,
        batch_size: int = 10,
        kind: ExperienceKind | None = None,
        min_priority: float = 0.0,
    ) -> list[ExperienceEntry]:
        """Sample a batch of experiences using priority-weighted selection.

        Higher priority experiences are more likely to be selected.
        Importance weights are attached to correct for sampling bias.
        """
        candidates = self._buffer
        if kind:
            candidates = [e for e in candidates if e.kind == kind]
        if min_priority > 0:
            candidates = [e for e in candidates if e.priority >= min_priority]

        if not candidates:
            return []

        if len(candidates) <= batch_size:
            for e in candidates:
                self._total_sampled += 1
            return candidates

        # Compute sampling probabilities
        priorities = [
            max(e.priority, self.PRIORITY_EPSILON) ** self.ALPHA
            for e in candidates
        ]
        total_p = sum(priorities)
        if total_p == 0:
            selected = random.sample(candidates, batch_size)
        else:
            probs = [p / total_p for p in priorities]
            indices = set()
            selected = []
            attempts = 0
            while len(selected) < batch_size and attempts < batch_size * 5:
                idx = random.choices(range(len(candidates)), weights=probs, k=1)[0]
                if idx not in indices:
                    indices.add(idx)
                    exp = candidates[idx]

                    # Compute importance weight
                    n = len(candidates)
                    exp.importance_weight = (1.0 / (n * probs[idx])) ** self.BETA

                    # Decay priority slightly after sampling to encourage diversity
                    exp.priority = max(self.PRIORITY_EPSILON, exp.priority * self.DECAY_FACTOR)
                    self._priority_history[exp.id].append(exp.priority)

                    selected.append(exp)
                attempts += 1

        self._total_sampled += len(selected)
        return selected

    def sample_contrastive_pair(self) -> tuple[ExperienceEntry | None, ExperienceEntry | None]:
        """Sample one success and one failure for contrastive learning."""
        successes = [e for e in self._buffer if e.result == ExperienceResult.SUCCESS]
        failures = [e for e in self._buffer if e.result == ExperienceResult.FAILURE]

        success = random.choice(successes) if successes else None
        failure = random.choice(failures) if failures else None

        self._total_sampled += (1 if success else 0) + (1 if failure else 0)
        return success, failure

    def sample_by_temporal_difference(
        self,
        batch_size: int = 10,
    ) -> list[ExperienceEntry]:
        """Sample experiences with high temporal difference in priorities.

        Experiences whose priority has changed significantly over time
        are more informative for learning and are sampled preferentially.
        """
        scores: list[tuple[ExperienceEntry, float]] = []
        for exp in self._buffer:
            history = self._priority_history.get(exp.id, [])
            td_score = 0.0
            if len(history) >= 2:
                # Compute variance of priority changes
                diffs = [abs(history[i] - history[i - 1]) for i in range(1, len(history))]
                td_score = sum(diffs) / len(diffs)
            else:
                td_score = exp.priority

            scores.append((exp, td_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        selected = [e for e, _ in scores[:batch_size]]
        self._total_sampled += len(selected)
        return selected

    def get_high_priority(self, min_priority: float = 0.7, limit: int = 50) -> list[ExperienceEntry]:
        """Get experiences with priority above the threshold."""
        return sorted(
            [e for e in self._buffer if e.priority >= min_priority],
            key=lambda e: -e.priority,
        )[:limit]

    def apply_temporal_decay(self, days_threshold: int = 7):
        """Decay priorities of experiences older than the threshold."""
        now = datetime.now(timezone.utc)
        decayed = 0
        for exp in self._buffer:
            if exp.created_at:
                created = datetime.fromisoformat(exp.created_at)
                days_old = (now - created).days
                if days_old > days_threshold:
                    factor = max(0.01, 1.0 - 0.001 * (days_old - days_threshold))
                    exp.priority = max(self.PRIORITY_EPSILON, exp.priority * factor)
                    self._priority_history[exp.id].append(exp.priority)
                    decayed += 1

        if decayed:
            logger.debug(f"Temporal decay applied to {decayed} experiences")

    def _evict_lowest_priority(self):
        """Remove the lowest priority experience when buffer is full."""
        if not self._buffer:
            return
        self._buffer.sort(key=lambda e: e.priority)
        evicted = self._buffer[0]
        self._buffer = self._buffer[1:]
        self._priority_history.pop(evicted.id, None)
        logger.debug(f"Evicted low-priority experience: {evicted.id}")

    def get_stats(self) -> dict[str, Any]:
        """Get buffer statistics."""
        if not self._buffer:
            return {"total": 0, "is_empty": True}

        results = defaultdict(int)
        kinds = defaultdict(int)
        priorities = []
        for e in self._buffer:
            results[e.result.value] += 1
            kinds[e.kind.value] += 1
            priorities.append(e.priority)

        total = len(self._buffer)
        return {
            "total_experiences": total,
            "capacity": self.capacity,
            "utilization": f"{total / self.capacity * 100:.1f}%",
            "total_added": self._total_added,
            "total_sampled": self._total_sampled,
            "avg_priority": round(sum(priorities) / max(total, 1), 4),
            "max_priority": round(max(priorities) if priorities else 0, 4),
            "result_distribution": dict(results),
            "kind_distribution": dict(kinds),
            "success_rate": f"{results.get('success', 0) / max(total, 1) * 100:.1f}%",
            "priority_history_entries": sum(len(h) for h in self._priority_history.values()),
        }

    def clear(self):
        """Clear all experiences from the buffer."""
        self._buffer.clear()
        self._priority_history.clear()
        logger.info("Experience replay buffer cleared")


# ---------------------------------------------------------------------------
# 3. Trajectory Compressor
# ---------------------------------------------------------------------------

class AgentTrajectoryCompressor:
    """Compresses agent execution trajectories for efficient storage.

    Identifies key decision points, removes redundant intermediate steps,
    preserves critical context and outcomes, and generates compact
    summaries that retain the essential information for learning.
    """

    MAX_COMPRESSED = 2000
    KEY_DECISION_ACTIONS = {"tool_execution", "decision_making", "error_recovery"}
    REDUNDANT_ACTIONS = {"conversation"}

    def __init__(self):
        self._compressed: dict[str, CompressedTrajectory] = {}
        self._by_session: dict[str, list[str]] = defaultdict(list)

    def compress_session(
        self,
        experiences: list[ExperienceEntry],
        agent_id: str,
        session_id: str,
    ) -> CompressedTrajectory:
        """Compress a session's experiences into a single trajectory summary.

        The compression preserves:
          - Key decision points (tool executions, decisions, error recoveries)
          - The overall task goal and outcome
          - Tools used and their success rates
          - Critical context needed for future learning

        It discards:
          - Redundant conversation turns
          - Intermediate observations that don't change decisions
          - No-op or trivial steps
        """
        if not experiences:
            return self._create_empty_trajectory(agent_id, session_id)

        # Sort by creation time
        sorted_exp = sorted(experiences, key=lambda e: e.created_at)
        source_ids = [e.id for e in sorted_exp]

        # Extract key decision points
        key_decisions = self._extract_key_decisions(sorted_exp)

        # Collect tools used
        tools_used = list(dict.fromkeys(
            e.tool_name for e in sorted_exp if e.tool_name
        ))

        # Determine overall result
        results = [e.result for e in sorted_exp]
        if all(r == ExperienceResult.SUCCESS for r in results):
            overall_result = "success"
        elif any(r == ExperienceResult.FAILURE for r in results):
            overall_result = "failure"
        elif any(r == ExperienceResult.ABORTED for r in results):
            overall_result = "aborted"
        else:
            overall_result = "partial"

        # Extract patterns
        patterns = self._extract_patterns(sorted_exp)

        # Generate summary
        summary = self._generate_summary(sorted_exp, key_decisions, tools_used, overall_result)

        # Calculate compression metrics
        original_steps = len(sorted_exp)
        compressed_steps = len(key_decisions) + 1  # +1 for summary
        original_tokens = sum(e.tokens_used for e in sorted_exp)
        compressed_tokens = len(summary) // 4  # rough estimate

        compressed = CompressedTrajectory(
            source_experience_ids=source_ids,
            agent_id=agent_id,
            session_id=session_id,
            summary=summary,
            key_decision_points=key_decisions,
            tools_used=tools_used,
            critical_context=self._extract_critical_context(sorted_exp),
            extracted_patterns=patterns,
            original_step_count=original_steps,
            compressed_step_count=compressed_steps,
            tokens_saved=max(0, original_tokens - compressed_tokens),
            compression_ratio=(
                original_steps / max(compressed_steps, 1)
            ),
            result=overall_result,
        )

        self._compressed[compressed.id] = compressed
        self._by_session[session_id].append(compressed.id)

        # Enforce max capacity
        if len(self._compressed) > self.MAX_COMPRESSED:
            self._prune_oldest()

        logger.info(
            f"Compressed session {session_id}: {original_steps} steps -> "
            f"{compressed_steps} points ({compressed.compression_ratio:.1f}x)"
        )
        return compressed

    def _extract_key_decisions(
        self,
        experiences: list[ExperienceEntry],
    ) -> list[dict[str, Any]]:
        """Identify key decision points from experiences."""
        decisions = []
        for i, exp in enumerate(experiences):
            if exp.kind.value in self.KEY_DECISION_ACTIONS:
                decision = {
                    "step": i,
                    "kind": exp.kind.value,
                    "action": exp.action_description[:200],
                    "tool": exp.tool_name,
                    "result": exp.result.value,
                    "confidence": exp.confidence,
                    "reward": exp.reward,
                }
                if exp.insights:
                    decision["insights"] = exp.insights[:3]
                decisions.append(decision)
            elif exp.kind == ExperienceKind.DECISION_MAKING:
                decision = {
                    "step": i,
                    "kind": "decision",
                    "action": exp.action_description[:200],
                    "result": exp.result.value,
                    "context": {
                        k: str(v)[:100]
                        for k, v in exp.context.items()
                    },
                }
                decisions.append(decision)

        return decisions[:20]

    def _extract_patterns(self, experiences: list[ExperienceEntry]) -> list[str]:
        """Extract behavioral patterns from a sequence of experiences."""
        patterns = []

        # Tool sequence pattern
        tool_seq = [e.tool_name for e in experiences if e.tool_name]
        if len(tool_seq) >= 2:
            sig = hashlib.md5("->".join(tool_seq).encode()).hexdigest()[:8]
            patterns.append(f"tool_sequence:{sig}")

        # Error recovery pattern
        for i in range(len(experiences) - 1):
            if (
                experiences[i].result == ExperienceResult.FAILURE
                and experiences[i + 1].result == ExperienceResult.SUCCESS
            ):
                patterns.append(
                    f"error_recovery: {experiences[i].tool_name} -> {experiences[i + 1].tool_name}"
                )

        # Result pattern
        result_seq = "".join(
            "S" if e.result == ExperienceResult.SUCCESS else
            "F" if e.result == ExperienceResult.FAILURE else
            "P" if e.result == ExperienceResult.PARTIAL else "A"
            for e in experiences
        )
        sig = hashlib.md5(result_seq.encode()).hexdigest()[:8]
        patterns.append(f"result_pattern:{sig}")

        return patterns

    def _extract_critical_context(
        self,
        experiences: list[ExperienceEntry],
    ) -> dict[str, Any]:
        """Extract context that is critical for future learning."""
        critical = {
            "task_signatures": list(dict.fromkeys(
                e.task_signature for e in experiences if e.task_signature
            )),
            "total_tokens": sum(e.tokens_used for e in experiences),
            "total_cost": sum(e.cost for e in experiences),
            "total_latency_ms": sum(e.latency_ms for e in experiences),
            "emotional_arc": [
                e.emotional_valence.value for e in experiences
                if e.emotional_valence != EmotionalValence.NEUTRAL
            ],
        }

        # Collect unique insights
        all_insights = []
        for e in experiences:
            all_insights.extend(e.insights)
        critical["unique_insights"] = list(dict.fromkeys(all_insights))

        return critical

    def _generate_summary(
        self,
        experiences: list[ExperienceEntry],
        key_decisions: list[dict[str, Any]],
        tools_used: list[str],
        result: str,
    ) -> str:
        """Generate a human-readable summary of the trajectory."""
        first = experiences[0] if experiences else None
        task = first.task_signature if first and first.task_signature else "Unknown task"

        parts = [f"Task: {task}"]

        if tools_used:
            parts.append(f"Tools: {', '.join(tools_used[:5])}")

        parts.append(f"Steps: {len(experiences)}, Decisions: {len(key_decisions)}")
        parts.append(f"Result: {result}")

        # Include success rate
        successes = sum(1 for e in experiences if e.result == ExperienceResult.SUCCESS)
        parts.append(f"Success rate: {successes}/{len(experiences)}")

        return " | ".join(parts)

    def _create_empty_trajectory(
        self,
        agent_id: str,
        session_id: str,
    ) -> CompressedTrajectory:
        """Create an empty trajectory placeholder."""
        return CompressedTrajectory(
            agent_id=agent_id,
            session_id=session_id,
            summary="Empty session - no experiences recorded",
            result="success",
        )

    def _prune_oldest(self):
        """Remove oldest compressed trajectories when over capacity."""
        if not self._compressed:
            return
        sorted_ids = sorted(
            self._compressed.keys(),
            key=lambda cid: self._compressed[cid].created_at,
        )
        to_remove = sorted_ids[: len(self._compressed) - self.MAX_COMPRESSED]
        for cid in to_remove:
            entry = self._compressed.pop(cid, None)
            if entry and entry.session_id:
                self._by_session[entry.session_id].remove(cid)

    def get(self, trajectory_id: str) -> CompressedTrajectory | None:
        """Get a compressed trajectory by ID."""
        return self._compressed.get(trajectory_id)

    def get_by_session(self, session_id: str) -> list[CompressedTrajectory]:
        """Get compressed trajectories for a session."""
        ids = self._by_session.get(session_id, [])
        return [self._compressed[cid] for cid in ids if cid in self._compressed]

    def get_by_agent(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[CompressedTrajectory]:
        """Get compressed trajectories for an agent."""
        results = [
            ct for ct in self._compressed.values()
            if ct.agent_id == agent_id
        ]
        results.sort(key=lambda ct: ct.created_at, reverse=True)
        return results[:limit]

    def get_all(self, limit: int = 100) -> list[CompressedTrajectory]:
        """Get all compressed trajectories."""
        results = list(self._compressed.values())
        results.sort(key=lambda ct: ct.created_at, reverse=True)
        return results[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get compressor statistics."""
        total = len(self._compressed)
        if total == 0:
            return {"total_compressed": 0, "is_empty": True}

        ratios = [ct.compression_ratio for ct in self._compressed.values()]
        tokens_saved = sum(ct.tokens_saved for ct in self._compressed.values())
        results = defaultdict(int)
        for ct in self._compressed.values():
            results[ct.result] += 1

        return {
            "total_compressed": total,
            "max_capacity": self.MAX_COMPRESSED,
            "avg_compression_ratio": round(sum(ratios) / max(total, 1), 2),
            "max_compression_ratio": round(max(ratios) if ratios else 0, 2),
            "total_tokens_saved": tokens_saved,
            "result_distribution": dict(results),
            "sessions_tracked": len(self._by_session),
        }


# ---------------------------------------------------------------------------
# 4. Experience Evolution
# ---------------------------------------------------------------------------

class ExperienceEvolver:
    """Evolves agent behavior from accumulated experience data.

    Analyzes experience patterns to recognize recurring strategies,
    adapt behavior based on outcome data, calibrate confidence from
    historical performance, and enable cross-agent experience sharing.
    """

    MIN_EXPERIENCES_FOR_EVOLUTION = 10
    MIN_CONFIDENCE_FOR_ADAPTATION = 0.6
    PATTERN_SIMILARITY_THRESHOLD = 0.7

    def __init__(self):
        self._strategies: dict[str, StrategyAdaptation] = {}
        self._confidence_scores: dict[str, list[float]] = defaultdict(list)
        self._shared_experiences: dict[str, list[str]] = defaultdict(list)
        self._evolution_log: list[dict[str, Any]] = []

    def recognize_patterns(
        self,
        experiences: list[ExperienceEntry],
    ) -> list[dict[str, Any]]:
        """Recognize recurring patterns across a set of experiences.

        Groups experiences by kind, tool, and outcome to identify
        common sequences and strategies that can inform evolution.
        """
        if len(experiences) < self.MIN_EXPERIENCES_FOR_EVOLUTION:
            return []

        patterns: list[dict[str, Any]] = []

        # Group by tool name
        tool_groups: dict[str, list[ExperienceEntry]] = defaultdict(list)
        for exp in experiences:
            if exp.tool_name:
                tool_groups[exp.tool_name].append(exp)

        for tool_name, group in tool_groups.items():
            if len(group) < 3:
                continue

            successes = sum(1 for e in group if e.result == ExperienceResult.SUCCESS)
            success_rate = successes / len(group)
            avg_latency = sum(e.latency_ms for e in group) / len(group)
            avg_tokens = sum(e.tokens_used for e in group) / len(group)

            patterns.append({
                "pattern_type": "tool_usage",
                "tool": tool_name,
                "frequency": len(group),
                "success_rate": round(success_rate, 3),
                "avg_latency_ms": round(avg_latency, 1),
                "avg_tokens": round(avg_tokens, 1),
                "is_reliable": success_rate >= 0.8,
            })

        # Group by kind + result
        strategy_groups: dict[str, list[ExperienceEntry]] = defaultdict(list)
        for exp in experiences:
            key = f"{exp.kind.value}:{exp.result.value}"
            strategy_groups[key].append(exp)

        for key, group in strategy_groups.items():
            if len(group) < 3:
                continue
            kind, result = key.split(":", 1)
            patterns.append({
                "pattern_type": "strategy_outcome",
                "kind": kind,
                "result": result,
                "frequency": len(group),
                "avg_priority": round(sum(e.priority for e in group) / len(group), 3),
            })

        return patterns

    def adapt_strategies(
        self,
        experiences: list[ExperienceEntry],
        existing_strategies: list[StrategyAdaptation] | None = None,
    ) -> list[StrategyAdaptation]:
        """Adapt agent strategies based on experience outcomes.

        Analyzes which strategies lead to successful outcomes and
        generates new or refined strategy adaptations.
        """
        if len(experiences) < self.MIN_EXPERIENCES_FOR_EVOLUTION:
            return []

        new_adaptations: list[StrategyAdaptation] = []

        # Analyze tool-level strategies
        tool_results: dict[str, list[ExperienceResult]] = defaultdict(list)
        for exp in experiences:
            if exp.tool_name:
                tool_results[exp.tool_name].append(exp.result)

        for tool_name, results in tool_results.items():
            if len(results) < 3:
                continue

            successes = sum(1 for r in results if r == ExperienceResult.SUCCESS)
            success_rate = successes / len(results)

            if success_rate >= self.MIN_CONFIDENCE_FOR_ADAPTATION:
                strategy = StrategyAdaptation(
                    name=f"prefer_{tool_name}",
                    description=f"Prioritize tool '{tool_name}' with proven {success_rate:.0%} success rate",
                    trigger_pattern=tool_name,
                    success_rate=success_rate,
                    confidence=min(0.9, success_rate),
                )
                new_adaptations.append(strategy)
                self._strategies[strategy.id] = strategy

            elif success_rate <= 0.3 and len(results) >= 5:
                strategy = StrategyAdaptation(
                    name=f"avoid_{tool_name}",
                    description=f"Tool '{tool_name}' has low success rate ({success_rate:.0%}); consider alternatives",
                    trigger_pattern=f"!{tool_name}",
                    success_rate=success_rate,
                    confidence=min(0.9, 1.0 - success_rate),
                )
                new_adaptations.append(strategy)
                self._strategies[strategy.id] = strategy

        # Log evolution event
        if new_adaptations:
            self._evolution_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "strategy_adaptation",
                "new_strategies": len(new_adaptations),
                "strategy_ids": [s.id for s in new_adaptations],
            })

        return new_adaptations

    def calibrate_confidence(
        self,
        agent_id: str,
        experiences: list[ExperienceEntry],
    ) -> dict[str, float]:
        """Calibrate confidence scores based on historical performance.

        Computes actual success rates for different action types and
        compares them against the agent's self-reported confidence
        to produce calibrated confidence estimates.
        """
        if not experiences:
            return {}

        # Group by kind for calibration
        kind_results: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for exp in experiences:
            kind_results[exp.kind.value].append({
                "result": exp.result,
                "confidence": exp.confidence,
            })

        calibrated: dict[str, float] = {}
        for kind, entries in kind_results.items():
            actual_success = sum(
                1 for e in entries
                if e["result"] == ExperienceResult.SUCCESS
            )
            actual_rate = actual_success / len(entries)
            avg_confidence = sum(e["confidence"] for e in entries) / len(entries)

            # Calibration: blend actual with confidence
            calibration_gap = actual_rate - avg_confidence
            calibrated_score = avg_confidence + calibration_gap * 0.5
            calibrated[kind] = round(min(1.0, max(0.0, calibrated_score)), 4)

            self._confidence_scores[kind].append(calibrated[kind])

        return calibrated

    def share_experiences(
        self,
        source_agent_id: str,
        target_agent_ids: list[str],
        experiences: list[ExperienceEntry],
        min_priority: float = 0.5,
    ) -> dict[str, int]:
        """Share high-value experiences between agents.

        Filters experiences by priority threshold and distributes
        them to target agents for cross-agent learning.
        """
        shared_count: dict[str, int] = {}
        high_value = [e for e in experiences if e.priority >= min_priority]

        if not high_value:
            return shared_count

        for target_id in target_agent_ids:
            self._shared_experiences[target_id].extend(
                e.id for e in high_value
            )
            shared_count[target_id] = len(high_value)

        logger.info(
            f"Shared {len(high_value)} experiences from {source_agent_id} "
            f"to {len(target_agent_ids)} agents"
        )
        return shared_count

    def get_shared_experience_ids(self, agent_id: str) -> list[str]:
        """Get experience IDs shared with an agent."""
        return self._shared_experiences.get(agent_id, [])

    def get_strategies(
        self,
        min_success_rate: float = 0.0,
        min_confidence: float = 0.0,
    ) -> list[StrategyAdaptation]:
        """Get evolved strategies, optionally filtered."""
        strategies = list(self._strategies.values())
        if min_success_rate > 0:
            strategies = [s for s in strategies if s.success_rate >= min_success_rate]
        if min_confidence > 0:
            strategies = [s for s in strategies if s.confidence >= min_confidence]
        strategies.sort(key=lambda s: -s.success_rate)
        return strategies

    def get_confidence_calibration(self, kind: str | None = None) -> dict[str, float]:
        """Get calibrated confidence scores."""
        if kind:
            scores = self._confidence_scores.get(kind, [])
            return {
                kind: round(sum(scores) / len(scores), 4) if scores else 0.5,
            }

        result: dict[str, float] = {}
        for k, scores in self._confidence_scores.items():
            result[k] = round(sum(scores) / len(scores), 4) if scores else 0.5
        return result

    def get_evolution_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get evolution event log."""
        return self._evolution_log[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get evolution statistics."""
        return {
            "total_strategies": len(self._strategies),
            "avg_strategy_success_rate": round(
                sum(s.success_rate for s in self._strategies.values()) / max(len(self._strategies), 1),
                3,
            ),
            "confidence_calibrated_kinds": len(self._confidence_scores),
            "total_shared_experiences": sum(
                len(ids) for ids in self._shared_experiences.values()
            ),
            "agents_with_shared_experiences": len(self._shared_experiences),
            "evolution_events": len(self._evolution_log),
        }


# ---------------------------------------------------------------------------
# 5. Experience Analytics
# ---------------------------------------------------------------------------

class ExperienceAnalytics:
    """Analytics and insights engine for experience data.

    Generates performance trends, identifies bottlenecks, computes
    success rates by tool and action type, and produces learning
    curve visualization data for monitoring agent improvement.
    """

    def __init__(self):
        self._reports: list[AnalyticsReport] = []
        self._performance_history: list[dict[str, Any]] = []

    def generate_report(
        self,
        recorder: ExperienceRecorder,
        compressor: AgentTrajectoryCompressor,
        evolver: ExperienceEvolver,
        time_window_days: int | None = None,
    ) -> AnalyticsReport:
        """Generate a comprehensive analytics report from all subsystems.

        Optionally filters experiences to a time window for trend analysis.
        """
        # Gather experiences
        all_experiences = list(recorder._experiences.values())

        if time_window_days is not None:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=time_window_days)).isoformat()
            all_experiences = [e for e in all_experiences if e.created_at >= cutoff]

        total = len(all_experiences)

        # Result distribution
        result_dist: dict[str, int] = defaultdict(int)
        kind_dist: dict[str, int] = defaultdict(int)
        total_tokens = 0
        total_latency = 0.0
        total_cost = 0.0

        # Tool success rates
        tool_results: dict[str, list[ExperienceResult]] = defaultdict(list)

        for exp in all_experiences:
            result_dist[exp.result.value] += 1
            kind_dist[exp.kind.value] += 1
            total_tokens += exp.tokens_used
            total_latency += exp.latency_ms
            total_cost += exp.cost

            if exp.tool_name:
                tool_results[exp.tool_name].append(exp.result)

        # Tool success rates
        tool_success_rates: dict[str, float] = {}
        bottleneck_tools: list[str] = []
        for tool_name, results in tool_results.items():
            if len(results) >= 3:
                rate = sum(1 for r in results if r == ExperienceResult.SUCCESS) / len(results)
                tool_success_rates[tool_name] = round(rate, 3)
                if rate < 0.5:
                    bottleneck_tools.append(tool_name)

        # Success rate
        success_count = result_dist.get("success", 0)
        success_rate = success_count / max(total, 1)

        # Learning curve data
        learning_curve = self._compute_learning_curve(all_experiences)

        # Compressor stats
        compressor_stats = compressor.get_stats()
        evolver_stats = evolver.get_stats()

        report = AnalyticsReport(
            total_experiences=total,
            total_compressed=compressor_stats.get("total_compressed", 0),
            total_strategies=evolver_stats.get("total_strategies", 0),
            success_rate=round(success_rate, 3),
            avg_tokens_per_experience=round(total_tokens / max(total, 1), 1),
            avg_latency_ms=round(total_latency / max(total, 1), 1),
            total_cost=round(total_cost, 6),
            result_distribution=dict(result_dist),
            kind_distribution=dict(kind_dist),
            tool_success_rates=tool_success_rates,
            bottleneck_tools=bottleneck_tools,
            learning_curve_data=learning_curve,
        )

        self._reports.append(report)
        if len(self._reports) > 100:
            self._reports = self._reports[-100:]

        # Track performance history
        self._performance_history.append({
            "timestamp": report.generated_at,
            "total_experiences": total,
            "success_rate": report.success_rate,
            "avg_latency_ms": report.avg_latency_ms,
            "total_cost": report.total_cost,
        })

        return report

    def _compute_learning_curve(
        self,
        experiences: list[ExperienceEntry],
        bucket_size: int = 50,
    ) -> list[dict[str, Any]]:
        """Compute learning curve data by bucketing experiences chronologically."""
        if not experiences:
            return []

        sorted_exp = sorted(experiences, key=lambda e: e.created_at)

        curve_data: list[dict[str, Any]] = []
        for i in range(0, len(sorted_exp), bucket_size):
            bucket = sorted_exp[i : i + bucket_size]
            successes = sum(1 for e in bucket if e.result == ExperienceResult.SUCCESS)
            avg_priority = sum(e.priority for e in bucket) / len(bucket)
            avg_latency = sum(e.latency_ms for e in bucket) / len(bucket)
            avg_tokens = sum(e.tokens_used for e in bucket) / len(bucket)

            curve_data.append({
                "bucket_start": bucket[0].created_at,
                "bucket_end": bucket[-1].created_at,
                "experience_count": len(bucket),
                "success_rate": round(successes / len(bucket), 3),
                "avg_priority": round(avg_priority, 3),
                "avg_latency_ms": round(avg_latency, 1),
                "avg_tokens": round(avg_tokens, 1),
            })

        return curve_data

    def analyze_bottlenecks(
        self,
        recorder: ExperienceRecorder,
        min_samples: int = 5,
    ) -> list[dict[str, Any]]:
        """Identify performance bottlenecks from experience data."""
        bottlenecks: list[dict[str, Any]] = []

        # Analyze tool latency
        tool_latencies: dict[str, list[float]] = defaultdict(list)
        for exp in recorder._experiences.values():
            if exp.tool_name and exp.latency_ms > 0:
                tool_latencies[exp.tool_name].append(exp.latency_ms)

        for tool_name, latencies in tool_latencies.items():
            if len(latencies) >= min_samples:
                avg_lat = sum(latencies) / len(latencies)
                if avg_lat > 2000:  # Tools taking over 2 seconds
                    bottlenecks.append({
                        "type": "high_latency",
                        "tool": tool_name,
                        "avg_latency_ms": round(avg_lat, 1),
                        "sample_count": len(latencies),
                        "severity": "high" if avg_lat > 5000 else "medium",
                    })

        # Analyze cost concentrations
        tool_costs: dict[str, list[float]] = defaultdict(list)
        for exp in recorder._experiences.values():
            if exp.tool_name and exp.cost > 0:
                tool_costs[exp.tool_name].append(exp.cost)

        for tool_name, costs in tool_costs.items():
            if len(costs) >= min_samples:
                total_tool_cost = sum(costs)
                if total_tool_cost > 0.1:  # High-cost tools
                    bottlenecks.append({
                        "type": "high_cost",
                        "tool": tool_name,
                        "total_cost": round(total_tool_cost, 4),
                        "avg_cost_per_call": round(total_tool_cost / len(costs), 6),
                        "sample_count": len(costs),
                    })

        return bottlenecks

    def get_performance_trends(
        self,
        lookback_entries: int = 10,
    ) -> list[dict[str, Any]]:
        """Get performance trend data from recent reports."""
        return self._performance_history[-lookback_entries:]

    def get_latest_report(self) -> AnalyticsReport | None:
        """Get the most recent analytics report."""
        return self._reports[-1] if self._reports else None

    def get_stats(self) -> dict[str, Any]:
        """Get analytics statistics."""
        latest = self.get_latest_report()
        return {
            "total_reports_generated": len(self._reports),
            "performance_history_entries": len(self._performance_history),
            "latest_success_rate": latest.success_rate if latest else 0.0,
            "latest_bottleneck_count": len(latest.bottleneck_tools) if latest else 0,
            "latest_avg_latency_ms": latest.avg_latency_ms if latest else 0.0,
        }


# ---------------------------------------------------------------------------
# Experience Engine — Main Coordinator
# ---------------------------------------------------------------------------

class ExperienceEngine:
    """Central coordinator for the agentic experience management system.

    Integrates the five core subsystems:
      - ExperienceRecorder: captures agent interactions
      - ExperienceReplayBuffer: prioritized replay for learning
      - AgentTrajectoryCompressor: efficient trajectory storage
      - ExperienceEvolver: behavior evolution from patterns
      - ExperienceAnalytics: performance insights and trends

    Provides a unified interface for recording, replaying, compressing,
    evolving, and analyzing agent experiences across the platform.
    """

    def __init__(self):
        self.recorder = ExperienceRecorder()
        self.replay_buffer = ExperienceReplayBuffer()
        self.compressor = AgentTrajectoryCompressor()
        self.evolver = ExperienceEvolver()
        self.analytics = ExperienceAnalytics()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        agent_id: str,
        kind: ExperienceKind,
        result: ExperienceResult,
        **kwargs: Any,
    ) -> ExperienceEntry:
        """Record an experience and add it to the replay buffer."""
        entry = self.recorder.record(
            agent_id=agent_id,
            kind=kind,
            result=result,
            **kwargs,
        )
        self.replay_buffer.add(entry)
        return entry

    def record_conversation(
        self,
        agent_id: str,
        result: ExperienceResult,
        context: dict[str, Any],
        **kwargs: Any,
    ) -> ExperienceEntry:
        """Record a conversation experience."""
        entry = self.recorder.record_conversation(
            agent_id=agent_id,
            result=result,
            context=context,
            **kwargs,
        )
        self.replay_buffer.add(entry)
        return entry

    def record_tool_execution(
        self,
        agent_id: str,
        tool_name: str,
        result: ExperienceResult,
        **kwargs: Any,
    ) -> ExperienceEntry:
        """Record a tool execution experience."""
        entry = self.recorder.record_tool_execution(
            agent_id=agent_id,
            tool_name=tool_name,
            result=result,
            **kwargs,
        )
        self.replay_buffer.add(entry)
        return entry

    def record_task_completion(
        self,
        agent_id: str,
        task_signature: str,
        result: ExperienceResult,
        **kwargs: Any,
    ) -> ExperienceEntry:
        """Record a task completion experience."""
        entry = self.recorder.record_task_completion(
            agent_id=agent_id,
            task_signature=task_signature,
            result=result,
            **kwargs,
        )
        self.replay_buffer.add(entry)
        return entry

    def record_error_recovery(
        self,
        agent_id: str,
        error_context: dict[str, Any],
        result: ExperienceResult,
        **kwargs: Any,
    ) -> ExperienceEntry:
        """Record an error recovery experience."""
        entry = self.recorder.record_error_recovery(
            agent_id=agent_id,
            error_context=error_context,
            result=result,
            **kwargs,
        )
        self.replay_buffer.add(entry)
        return entry

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def finalize_session(self, agent_id: str, session_id: str) -> CompressedTrajectory | None:
        """Compress a session's experiences into a trajectory.

        Gathers all experiences for the session, compresses them,
        and triggers evolution analysis on the session data.
        """
        experiences = self.recorder.get_by_session(session_id)
        if not experiences:
            return None

        # Compress the session
        compressed = self.compressor.compress_session(
            experiences=experiences,
            agent_id=agent_id,
            session_id=session_id,
        )

        return compressed

    def evolve_from_session(
        self,
        agent_id: str,
        session_id: str,
    ) -> list[StrategyAdaptation]:
        """Evolve strategies from a completed session's experiences."""
        experiences = self.recorder.get_by_session(session_id)
        if not experiences:
            return []

        # Recognize patterns
        patterns = self.evolver.recognize_patterns(experiences)

        # Adapt strategies
        adaptations = self.evolver.adapt_strategies(experiences)

        # Calibrate confidence
        self.evolver.calibrate_confidence(agent_id, experiences)

        return adaptations

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def sample_for_learning(
        self,
        batch_size: int = 10,
        kind: ExperienceKind | None = None,
    ) -> list[ExperienceEntry]:
        """Sample experiences from the replay buffer for learning."""
        return self.replay_buffer.sample(batch_size=batch_size, kind=kind)

    def sample_contrastive(self) -> tuple[ExperienceEntry | None, ExperienceEntry | None]:
        """Sample a success/failure pair for contrastive learning."""
        return self.replay_buffer.sample_contrastive_pair()

    def sample_temporal_difference(
        self,
        batch_size: int = 10,
    ) -> list[ExperienceEntry]:
        """Sample experiences with high temporal difference in priorities."""
        return self.replay_buffer.sample_by_temporal_difference(batch_size)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def generate_report(
        self,
        time_window_days: int | None = None,
    ) -> AnalyticsReport:
        """Generate a comprehensive analytics report."""
        return self.analytics.generate_report(
            recorder=self.recorder,
            compressor=self.compressor,
            evolver=self.evolver,
            time_window_days=time_window_days,
        )

    def get_bottlenecks(self) -> list[dict[str, Any]]:
        """Identify performance bottlenecks."""
        return self.analytics.analyze_bottlenecks(self.recorder)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def run_maintenance(self):
        """Run periodic maintenance tasks.

        Applies temporal decay to replay buffer priorities and
        auto-compresses old experiences to free memory.
        """
        self.replay_buffer.apply_temporal_decay()
        self.recorder.auto_compress_old()

    # ------------------------------------------------------------------
    # Cross-Agent
    # ------------------------------------------------------------------

    def share_with_agents(
        self,
        source_agent_id: str,
        target_agent_ids: list[str],
        min_priority: float = 0.5,
    ):
        """Share high-value experiences from source agent to target agents."""
        experiences = self.recorder.get_by_agent(source_agent_id)
        self.evolver.share_experiences(
            source_agent_id=source_agent_id,
            target_agent_ids=target_agent_ids,
            experiences=experiences,
            min_priority=min_priority,
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_full_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics from all subsystems."""
        return {
            "recorder": self.recorder.get_stats(),
            "replay_buffer": self.replay_buffer.get_stats(),
            "compressor": self.compressor.get_stats(),
            "evolver": self.evolver.get_stats(),
            "analytics": self.analytics.get_stats(),
        }

    def get_learning_insights(self) -> list[dict[str, Any]]:
        """Get actionable learning insights."""
        insights: list[dict[str, Any]] = []

        recorder_stats = self.recorder.get_stats()
        total = recorder_stats.get("total_experiences", 0)

        if total > 0:
            success_rate = float(
                recorder_stats.get("result_distribution", {}).get("success", 0)
            ) / max(total, 1)
            insights.append({
                "type": "success_rate",
                "value": round(success_rate, 3),
                "description": f"Overall success rate: {success_rate:.1%}",
            })

        buffer_stats = self.replay_buffer.get_stats()
        if buffer_stats.get("success_rate"):
            insights.append({
                "type": "buffer_health",
                "value": buffer_stats["success_rate"],
                "description": f"Replay buffer has {buffer_stats.get('total_experiences', 0)} experiences",
            })

        evolver_strategies = self.evolver.get_strategies()
        if evolver_strategies:
            insights.append({
                "type": "evolved_strategies",
                "value": len(evolver_strategies),
                "description": f"{len(evolver_strategies)} strategies evolved from experience",
            })

        bottlenecks = self.get_bottlenecks()
        if bottlenecks:
            insights.append({
                "type": "bottlenecks",
                "value": len(bottlenecks),
                "description": f"{len(bottlenecks)} performance bottlenecks identified",
            })

        return insights


# ---------------------------------------------------------------------------
# Global Instance
# ---------------------------------------------------------------------------

experience_engine = ExperienceEngine()