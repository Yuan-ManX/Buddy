"""Buddy Platform Smart Router — difficulty-based model routing

Classifies task difficulty and routes to the appropriate model tier.
Simple tasks go to lightweight models (cost savings), complex tasks
go to flagship models (quality). Per-task token accounting tracks
cost savings and quality outcomes.

Routing tiers:
  - ECONOMY: trivial tasks (greetings, simple lookups) → cheapest model
  - STANDARD: moderate tasks (summaries, basic code) → mid-tier model
  - FLAGSHIP: complex tasks (architecture, reasoning) → best model
  - EXPERIMENTAL: novel tasks (research, creative) → experimental model

The router learns from outcomes: if a task routed to ECONOMY fails,
similar tasks are upgraded to STANDARD. If a FLAGSHIP task succeeds
easily, similar tasks are downgraded.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.platform.smart_router")


class RoutingTier(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    FLAGSHIP = "flagship"
    EXPERIMENTAL = "experimental"


class TaskDifficulty(str, Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    NOVEL = "novel"


# Default model per tier (can be overridden via config)
_DEFAULT_MODELS = {
    RoutingTier.ECONOMY: "gpt-4o-mini",
    RoutingTier.STANDARD: "gpt-4o",
    RoutingTier.FLAGSHIP: "o1-preview",
    RoutingTier.EXPERIMENTAL: "o1-preview",
}

_DIFFICULTY_TO_TIER = {
    TaskDifficulty.TRIVIAL: RoutingTier.ECONOMY,
    TaskDifficulty.SIMPLE: RoutingTier.ECONOMY,
    TaskDifficulty.MODERATE: RoutingTier.STANDARD,
    TaskDifficulty.COMPLEX: RoutingTier.FLAGSHIP,
    TaskDifficulty.NOVEL: RoutingTier.EXPERIMENTAL,
}


@dataclass
class RoutingDecision:
    """A single routing decision."""
    decision_id: str = ""
    task_description: str = ""
    difficulty: TaskDifficulty = TaskDifficulty.MODERATE
    tier: RoutingTier = RoutingTier.STANDARD
    model: str = ""
    confidence: float = 0.5
    reasoning: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    estimated_tokens: int = 0
    actual_tokens: int = 0
    cost_saved: float = 0.0  # Savings vs always using flagship
    success: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "task_description": self.task_description[:100],
            "difficulty": self.difficulty.value,
            "tier": self.tier.value,
            "model": self.model,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "estimated_tokens": self.estimated_tokens,
            "actual_tokens": self.actual_tokens,
            "cost_saved": round(self.cost_saved, 4),
            "success": self.success,
        }


class SmartRouter:
    """Difficulty-based model router with learning feedback loop.

    Classifies task difficulty using heuristics and historical outcomes,
    then routes to the appropriate model tier. Per-task token accounting
    tracks cost savings.
    """

    def __init__(self, model_overrides: Optional[dict[RoutingTier, str]] = None):
        self._models = {**_DEFAULT_MODELS, **(model_overrides or {})}
        self._decisions: deque[RoutingDecision] = deque(maxlen=500)
        self._difficulty_history: dict[str, list[tuple[TaskDifficulty, bool]]] = defaultdict(list)
        self._lock = threading.RLock()
        self._total_cost_saved = 0.0
        self._total_tokens = 0
        self._routing_counts: dict[RoutingTier, int] = defaultdict(int)

        # Difficulty classification heuristics
        self._trivial_patterns = re.compile(
            r"^(hi|hello|hey|thanks|ok|yes|no|bye|done|stop|start)\b",
            re.IGNORECASE,
        )
        self._complex_keywords = {
            "architecture", "design", "refactor", "optimize", "analyze",
            "implement", "debug", "investigate", "research", "compare",
            "evaluate", "synthesize", "orchestrate",
        }
        self._novel_keywords = {
            "invent", "create new", "brainstorm", "explore", "novel",
            "innovative", "experimental", "prototype",
        }
        self._failure_alchemy = None

    def attach_failure_alchemy(self, failure_alchemy) -> None:
        """Link a failure alchemy instance for failure-aware routing."""
        self._failure_alchemy = failure_alchemy

    def classify_difficulty(self, task_description: str) -> tuple[TaskDifficulty, float, str]:
        """Classify task difficulty using heuristics and history.

        Returns (difficulty, confidence, reasoning).
        """
        desc_lower = task_description.lower().strip()

        # Trivial: greetings, single-word commands
        if self._trivial_patterns.match(desc_lower) or len(desc_lower) < 10:
            return TaskDifficulty.TRIVIAL, 0.9, "Trivial: short input or greeting pattern"

        # Count complexity indicators
        words = set(desc_lower.split())
        word_count = len(words)

        novel_matches = words & self._novel_keywords
        complex_matches = words & self._complex_keywords

        # Novel: creative/exploratory keywords
        if novel_matches:
            return TaskDifficulty.NOVEL, 0.8, f"Novel keywords: {novel_matches}"

        # Complex: complex keywords or long description
        if complex_matches or word_count > 50:
            confidence = min(0.9, 0.6 + len(complex_matches) * 0.1)
            return TaskDifficulty.COMPLEX, confidence, f"Complex keywords: {complex_matches or 'long description'}"

        # Moderate: medium-length with some substance
        if word_count > 15:
            return TaskDifficulty.MODERATE, 0.7, "Moderate: medium-length task description"

        # Simple: short but not trivial
        return TaskDifficulty.SIMPLE, 0.75, "Simple: short task description"

    def route(
        self,
        task_description: str,
        force_tier: Optional[RoutingTier] = None,
    ) -> RoutingDecision:
        """Route a task to the appropriate model tier.

        Args:
            task_description: The task to route.
            force_tier: Override the automatic classification.

        Returns:
            RoutingDecision with the chosen tier, model, and reasoning.
        """
        if force_tier:
            tier = force_tier
            difficulty = TaskDifficulty.MODERATE  # Unknown when forced
            confidence = 1.0
            reasoning = f"Forced to {tier.value}"
        else:
            difficulty, confidence, reasoning = self.classify_difficulty(task_description)
            tier = _DIFFICULTY_TO_TIER.get(difficulty, RoutingTier.STANDARD)

        model = self._models.get(tier, self._models[RoutingTier.STANDARD])

        # Estimate tokens (rough heuristic: 1.5 tokens per word)
        estimated_tokens = int(len(task_description.split()) * 1.5)

        # Calculate cost savings vs always using flagship
        cost_saved = self._estimate_cost_savings(tier, estimated_tokens)

        decision = RoutingDecision(
            decision_id=f"route-{int(time.time() * 1000)}",
            task_description=task_description,
            difficulty=difficulty,
            tier=tier,
            model=model,
            confidence=confidence,
            reasoning=reasoning,
            estimated_tokens=estimated_tokens,
            cost_saved=cost_saved,
        )

        with self._lock:
            self._decisions.append(decision)
            self._total_cost_saved += cost_saved
            self._total_tokens += estimated_tokens
            self._routing_counts[tier] += 1

        return decision

    def _estimate_cost_savings(self, tier: RoutingTier, tokens: int) -> float:
        """Estimate cost savings vs always using the flagship model."""
        # Rough per-1K-token costs (illustrative)
        costs_per_1k = {
            RoutingTier.ECONOMY: 0.15,
            RoutingTier.STANDARD: 2.50,
            RoutingTier.FLAGSHIP: 15.00,
            RoutingTier.EXPERIMENTAL: 15.00,
        }
        flagship_cost = (tokens / 1000) * costs_per_1k[RoutingTier.FLAGSHIP]
        actual_cost = (tokens / 1000) * costs_per_1k.get(tier, costs_per_1k[RoutingTier.STANDARD])
        return max(0.0, flagship_cost - actual_cost)

    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        actual_tokens: int = 0,
    ) -> None:
        """Record the outcome of a routing decision for learning.

        If a task routed to ECONOMY fails, similar tasks are upgraded.
        If a FLAGSHIP task succeeds easily, similar tasks are downgraded.
        """
        with self._lock:
            for decision in reversed(self._decisions):
                if decision.decision_id == decision_id:
                    decision.success = success
                    decision.actual_tokens = actual_tokens

                    # Record in difficulty history for learning
                    pattern = self._extract_pattern(decision.task_description)
                    self._difficulty_history[pattern].append((decision.difficulty, success))
                    break

    def _extract_pattern(self, description: str) -> str:
        """Extract a pattern signature from a task description for learning."""
        words = description.lower().split()
        # Use first 3 significant words as pattern
        return " ".join(words[:3])

    def get_recommended_tier(self, task_description: str) -> RoutingTier:
        """Get a tier recommendation adjusted by historical outcomes."""
        difficulty, _, _ = self.classify_difficulty(task_description)
        base_tier = _DIFFICULTY_TO_TIER.get(difficulty, RoutingTier.STANDARD)

        # Check history for similar patterns
        pattern = self._extract_pattern(task_description)
        history = self._difficulty_history.get(pattern, [])

        if len(history) >= 2:
            success_rate = sum(1 for _, s in history if s) / len(history)
            if success_rate < 0.5 and base_tier != RoutingTier.FLAGSHIP:
                # Upgrade: failures at current tier
                tiers = list(RoutingTier)
                current_idx = tiers.index(base_tier)
                return tiers[min(current_idx + 1, len(tiers) - 1)]
            elif success_rate > 0.9 and base_tier != RoutingTier.ECONOMY:
                # Downgrade: consistent success, can use cheaper model
                tiers = list(RoutingTier)
                current_idx = tiers.index(base_tier)
                return tiers[max(current_idx - 1, 0)]

        return base_tier

    # ── Configuration ────────────────────────────────────

    def set_model(self, tier: RoutingTier, model: str) -> None:
        with self._lock:
            self._models[tier] = model

    def get_models(self) -> dict[str, str]:
        return {tier.value: model for tier, model in self._models.items()}

    # ── Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_decisions": len(self._decisions),
                "total_cost_saved": round(self._total_cost_saved, 4),
                "total_tokens": self._total_tokens,
                "routing_distribution": {tier.value: count for tier, count in self._routing_counts.items()},
                "models": self.get_models(),
                "success_rates": {
                    tier.value: (
                        sum(1 for d in self._decisions if d.tier == tier and d.success is True)
                        / max(1, sum(1 for d in self._decisions if d.tier == tier and d.success is not None))
                    )
                    for tier in RoutingTier
                },
            }

    def get_recent_decisions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return [d.to_dict() for d in list(self._decisions)[-limit:]]


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

_smart_router: Optional[SmartRouter] = None
_sr_lock = threading.Lock()


def get_smart_router() -> SmartRouter:
    """Get the singleton SmartRouter instance."""
    global _smart_router
    if _smart_router is None:
        with _sr_lock:
            if _smart_router is None:
                _smart_router = SmartRouter()
    return _smart_router
