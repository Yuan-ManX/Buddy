"""Buddy Experience Replay — prioritized experience buffer for agent learning

Implements a replay buffer that stores agent experiences with priority-based
sampling, enabling agents to learn from past successes and failures. Uses
temporal difference error-style prioritization to focus on high-value experiences.

Core capabilities:
  - Prioritized Experience Buffer: importance-weighted sampling
  - Experience Clustering: group similar experiences for pattern discovery
  - Success/Failure Ratio Tracking: monitor learning progress
  - Temporal Decay: gradually reduce importance of old experiences
  - Cross-Session Learning: persistent experience storage across sessions
  - Strategy Attribution: link outcomes to specific strategies
"""
from __future__ import annotations

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

logger = logging.getLogger("buddy.experience_replay")


class ExperienceCategory(str, Enum):
    TOOL_SUCCESS = "tool_success"
    TOOL_FAILURE = "tool_failure"
    REASONING_SUCCESS = "reasoning_success"
    REASONING_FAILURE = "reasoning_failure"
    COLLABORATION = "collaboration"
    NEGOTIATION = "negotiation"
    ERROR_RECOVERY = "error_recovery"
    USER_FEEDBACK = "user_feedback"


@dataclass
class ReplayExperience:
    """A single experience stored in the replay buffer."""
    id: str = field(default_factory=lambda: f"exp-{uuid.uuid4().hex[:8]}")
    category: ExperienceCategory = ExperienceCategory.TOOL_SUCCESS
    agent_id: str = ""
    task_signature: str = ""
    context: dict = field(default_factory=dict)
    action: str = ""
    outcome: str = "success"  # success, partial, failure
    reward: float = 0.0       # -1.0 to 1.0
    priority: float = 0.5     # sampling priority
    strategy_used: dict = field(default_factory=dict)
    tokens_consumed: int = 0
    latency_ms: float = 0.0
    insights: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    replay_count: int = 0
    last_replayed: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "agent_id": self.agent_id,
            "task_signature": self.task_signature,
            "action": self.action[:200],
            "outcome": self.outcome,
            "reward": self.reward,
            "priority": round(self.priority, 4),
            "strategy_used": self.strategy_used,
            "tokens_consumed": self.tokens_consumed,
            "latency_ms": self.latency_ms,
            "insights": self.insights,
            "replay_count": self.replay_count,
            "created_at": self.created_at,
        }


class PrioritizedReplayBuffer:
    """Priority-based experience replay buffer for agent learning.

    Stores experiences with priority scores and samples them proportionally
    during replay. High-priority experiences (failures, high rewards) are
    sampled more frequently to accelerate learning from important events.
    """

    DEFAULT_CAPACITY = 5000
    PRIORITY_EPSILON = 0.01
    ALPHA = 0.6   # priority exponent
    BETA = 0.4    # importance sampling exponent
    DECAY_RATE = 0.001  # daily priority decay

    def __init__(self, agent_id: str, capacity: int = DEFAULT_CAPACITY):
        self.agent_id = agent_id
        self.capacity = capacity
        self._buffer: list[ReplayExperience] = []
        self._category_stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_reward": 0.0})
        self._total_stored: int = 0
        self._total_sampled: int = 0
        self._cluster_cache: dict[str, list[str]] = {}

    def add(self, experience: ReplayExperience):
        """Add an experience to the buffer with priority scoring."""
        experience.agent_id = self.agent_id

        # Calculate priority based on outcome and reward
        if experience.outcome == "failure":
            experience.priority = max(0.7, experience.priority)
        elif experience.reward > 0.5:
            experience.priority = max(0.6, experience.priority)
        elif experience.reward < -0.3:
            experience.priority = max(0.65, experience.priority)

        # Boost priority for rare categories
        cat_stats = self._category_stats[experience.category.value]
        if cat_stats["count"] < 10:
            experience.priority = min(1.0, experience.priority + 0.15)

        self._buffer.append(experience)
        self._total_stored += 1
        cat_stats["count"] += 1
        cat_stats["total_reward"] += experience.reward

        # Evict oldest/lowest priority if over capacity
        if len(self._buffer) > self.capacity:
            self._evict()

        logger.debug(
            f"Experience added: {experience.id} (category={experience.category.value}, "
            f"priority={experience.priority:.3f})"
        )

    def sample(self, batch_size: int = 10, category: ExperienceCategory | None = None) -> list[ReplayExperience]:
        """Sample a batch of experiences prioritized by importance.

        Uses importance-weighted sampling where higher priority experiences
        are more likely to be selected. Optionally filters by category.
        """
        candidates = self._buffer
        if category:
            candidates = [e for e in candidates if e.category == category]

        if not candidates:
            return []

        # Calculate sampling probabilities using priority^alpha
        priorities = [max(e.priority, self.PRIORITY_EPSILON) ** self.ALPHA for e in candidates]
        total_priority = sum(priorities)
        if total_priority == 0:
            return random.sample(candidates, min(batch_size, len(candidates)))

        probs = [p / total_priority for p in priorities]

        # Sample without replacement
        sampled_indices = set()
        sampled = []
        attempts = 0
        while len(sampled) < batch_size and attempts < batch_size * 3:
            idx = random.choices(range(len(candidates)), weights=probs, k=1)[0]
            if idx not in sampled_indices:
                sampled_indices.add(idx)
                exp = candidates[idx]
                exp.replay_count += 1
                exp.last_replayed = datetime.now(timezone.utc).isoformat()

                # Slightly decay priority after replay to encourage diversity
                exp.priority = max(self.PRIORITY_EPSILON, exp.priority * 0.95)
                sampled.append(exp)
            attempts += 1

        self._total_sampled += len(sampled)
        return sampled

    def sample_success_failure_pair(self) -> tuple[ReplayExperience | None, ReplayExperience | None]:
        """Sample one success and one failure experience for contrastive learning."""
        successes = [e for e in self._buffer if e.outcome == "success"]
        failures = [e for e in self._buffer if e.outcome == "failure"]

        success = random.choice(successes) if successes else None
        failure = random.choice(failures) if failures else None

        if success:
            success.replay_count += 1
        if failure:
            failure.replay_count += 1

        return success, failure

    def get_high_value_experiences(self, min_reward: float = 0.5, limit: int = 20) -> list[ReplayExperience]:
        """Get experiences with high positive reward."""
        return sorted(
            [e for e in self._buffer if e.reward >= min_reward],
            key=lambda e: -e.reward,
        )[:limit]

    def get_lessons_learned(self, limit: int = 20) -> list[dict]:
        """Extract actionable lessons from failures and recoveries."""
        failures = [e for e in self._buffer if e.outcome == "failure"]
        recoveries = [e for e in self._buffer if e.category == ExperienceCategory.ERROR_RECOVERY]

        lessons = []
        for exp in failures[:limit]:
            lessons.append({
                "id": exp.id,
                "category": exp.category.value,
                "action": exp.action[:100],
                "insights": exp.insights,
                "strategy": exp.strategy_used,
            })
        for exp in recoveries[:limit]:
            if len(lessons) >= limit:
                break
            lessons.append({
                "id": exp.id,
                "category": exp.category.value,
                "action": exp.action[:100],
                "insights": exp.insights,
            })

        return lessons

    def cluster_experiences(self) -> dict[str, list[str]]:
        """Cluster similar experiences by task signature for pattern analysis."""
        clusters = defaultdict(list)
        for exp in self._buffer:
            key = exp.task_signature[:50] if exp.task_signature else "unknown"
            clusters[key].append(exp.id)
        self._cluster_cache = dict(clusters)
        return self._cluster_cache

    def get_cluster_summary(self, cluster_key: str) -> dict | None:
        """Get summary statistics for an experience cluster."""
        exp_ids = self._cluster_cache.get(cluster_key, [])
        if not exp_ids:
            return None

        experiences = [e for e in self._buffer if e.id in exp_ids]
        if not experiences:
            return None

        successes = sum(1 for e in experiences if e.outcome == "success")
        avg_reward = sum(e.reward for e in experiences) / len(experiences)
        top_strategies = defaultdict(int)
        for e in experiences:
            strategy = e.strategy_used.get("execution_mode", "unknown")
            top_strategies[strategy] += 1

        return {
            "cluster_key": cluster_key,
            "total_experiences": len(experiences),
            "success_rate": f"{successes / len(experiences) * 100:.1f}%",
            "avg_reward": round(avg_reward, 3),
            "top_strategies": dict(top_strategies.most_common(3) if hasattr(top_strategies, 'most_common') else sorted(top_strategies.items(), key=lambda x: -x[1])[:3]),
            "avg_tokens": sum(e.tokens_consumed for e in experiences) // len(experiences),
        }

    def apply_temporal_decay(self):
        """Apply time-based decay to all experience priorities."""
        now = datetime.now(timezone.utc)
        decayed = 0
        for exp in self._buffer:
            if exp.created_at:
                created = datetime.fromisoformat(exp.created_at)
                days_old = (now - created).days
                if days_old > 1:
                    old_priority = exp.priority
                    exp.priority = max(self.PRIORITY_EPSILON, exp.priority * (1 - self.DECAY_RATE * days_old))
                    if exp.priority < old_priority:
                        decayed += 1
        if decayed:
            logger.debug(f"Temporal decay applied to {decayed} experiences")

    def _evict(self):
        """Remove lowest priority experience when buffer is full."""
        if not self._buffer:
            return
        # Keep the highest-priority experiences
        self._buffer.sort(key=lambda e: e.priority, reverse=True)
        evicted = self._buffer[self.capacity:]
        self._buffer = self._buffer[:self.capacity]

        for exp in evicted:
            cat_stats = self._category_stats[exp.category.value]
            cat_stats["count"] = max(0, cat_stats["count"] - 1)
        logger.debug(f"Evicted {len(evicted)} low-priority experiences")

    def get_stats(self) -> dict:
        """Get comprehensive buffer statistics."""
        if not self._buffer:
            return {"agent_id": self.agent_id, "total_stored": 0, "is_empty": True}

        outcomes = defaultdict(int)
        total_reward = 0.0
        for exp in self._buffer:
            outcomes[exp.outcome] += 1
            total_reward += exp.reward

        total = len(self._buffer)
        return {
            "agent_id": self.agent_id,
            "total_experiences": total,
            "capacity": self.capacity,
            "utilization": f"{total / self.capacity * 100:.1f}%",
            "total_stored": self._total_stored,
            "total_sampled": self._total_sampled,
            "outcome_distribution": dict(outcomes),
            "success_rate": f"{outcomes.get('success', 0) / max(total, 1) * 100:.1f}%",
            "avg_reward": round(total_reward / max(total, 1), 3),
            "avg_priority": round(sum(e.priority for e in self._buffer) / max(total, 1), 3),
            "category_stats": dict(self._category_stats),
            "clusters": len(self._cluster_cache),
        }

    def clear(self):
        """Clear all experiences from the buffer."""
        self._buffer.clear()
        self._category_stats.clear()
        self._cluster_cache.clear()
        logger.info(f"Experience buffer cleared for agent {self.agent_id}")

    def export(self, limit: int = 1000) -> list[dict]:
        """Export experiences for persistence or transfer."""
        return [e.to_dict() for e in self._buffer[:limit]]

    def import_experiences(self, experiences: list[dict]):
        """Import experiences from exported data."""
        for data in experiences:
            exp = ReplayExperience(
                id=data.get("id", f"exp-{uuid.uuid4().hex[:8]}"),
                category=ExperienceCategory(data.get("category", "tool_success")),
                task_signature=data.get("task_signature", ""),
                action=data.get("action", ""),
                outcome=data.get("outcome", "success"),
                reward=data.get("reward", 0.0),
                priority=data.get("priority", 0.5),
                strategy_used=data.get("strategy_used", {}),
                tokens_consumed=data.get("tokens_consumed", 0),
                latency_ms=data.get("latency_ms", 0.0),
                insights=data.get("insights", []),
            )
            self.add(exp)