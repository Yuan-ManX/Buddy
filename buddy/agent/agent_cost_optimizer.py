"""Agent Cost Optimizer — task-difficulty-aware smart routing across models.

Detects task complexity using lightweight heuristics and routes each task to
the most appropriate model tier, optimizing for cost, quality, latency, or a
balanced mix. Maintains a registry of model profiles, records real usage for
post-hoc analysis, and produces optimization reports that quantify the cost
savings achieved by tier-aware routing versus a flagship-only baseline.
"""

from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ══════════════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════════════

class TaskComplexity(Enum):
    """Five-level classification of task difficulty for routing."""

    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class ModelTier(Enum):
    """Capability/cost tiers for registered models."""

    LITE = "lite"
    STANDARD = "standard"
    PREMIUM = "premium"
    FLAGSHIP = "flagship"


class RoutingStrategy(Enum):
    """Strategy that determines how the optimizer ranks candidate models."""

    COST_FIRST = "cost_first"
    QUALITY_FIRST = "quality_first"
    BALANCED = "balanced"
    LATENCY_FIRST = "latency_first"


class OptimizationMetric(Enum):
    """Metrics tracked for optimization reports."""

    COST = "cost"
    LATENCY = "latency"
    QUALITY = "quality"
    THROUGHPUT = "throughput"


# ══════════════════════════════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ModelProfile:
    """Profile describing a registered model's cost, latency and quality."""

    model_id: str
    name: str
    provider: str
    tier: ModelTier
    cost_per_1k_input: float
    cost_per_1k_output: float
    avg_latency_ms: float
    quality_score: float
    max_context: int
    capabilities: list[str] = field(default_factory=list)
    active: bool = True


@dataclass
class TaskProfile:
    """Profile produced by complexity assessment for a single task."""

    task_id: str
    description: str
    detected_complexity: TaskComplexity
    required_capabilities: list[str] = field(default_factory=list)
    estimated_tokens: int = 1000
    created_at: float = field(default_factory=time.time)


@dataclass
class RoutingDecision:
    """Result of a routing decision for a task."""

    decision_id: str
    task_id: str
    selected_model_id: str
    alternative_models: list[str] = field(default_factory=list)
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    estimated_cost: float = 0.0
    estimated_latency: float = 0.0
    estimated_quality: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class CostRecord:
    """Recorded actual usage for a single model invocation."""

    record_id: str
    model_id: str
    task_id: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    quality_score: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class OptimizationReport:
    """Aggregated optimization report over a time window."""

    report_id: str
    period_start: float
    period_end: float
    total_cost: float = 0.0
    total_tasks: int = 0
    avg_cost_per_task: float = 0.0
    cost_savings: float = 0.0
    model_distribution: dict[str, int] = field(default_factory=dict)
    complexity_distribution: dict[str, int] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


# ══════════════════════════════════════════════════════════════════════
# Heuristic complexity detection
# ══════════════════════════════════════════════════════════════════════

# Keyword / regex patterns that increase the complexity score when present in
# a task description. Each pattern contributes a small additive bump.
_COMPLEXITY_PATTERNS: list[tuple[str, float]] = [
    # Multi-step / pipeline-style work
    (r"first.*then.*finally", 0.12),
    (r"step\s*\d", 0.10),
    (r"end.?to.?end", 0.12),
    (r"full\s*pipeline", 0.12),
    (r"plan.*execute", 0.10),
    (r"research.*write.*review", 0.10),
    # Architecture / system design
    (r"architect\w*", 0.15),
    (r"system\s*design", 0.15),
    (r"api\s*design", 0.12),
    (r"database\s*design", 0.12),
    (r"micro.?service\w*", 0.12),
    (r"distributed", 0.12),
    (r"scal\w*", 0.10),
    (r"high.?performance", 0.10),
    (r"low.?latency", 0.10),
    (r"fault.?toleran\w*", 0.12),
    (r"real.?time", 0.10),
    # Advanced engineering
    (r"refactor\w*", 0.10),
    (r"optimiz\w*", 0.10),
    (r"migrat\w*", 0.10),
    (r"concurr\w*", 0.12),
    (r"async\w*", 0.08),
    (r"parallel\w*", 0.08),
    (r"multi.?thread\w*", 0.10),
    (r"multi.?process\w*", 0.10),
    (r"multi.?agent", 0.12),
    # ML / advanced domains
    (r"machine\s*learning", 0.15),
    (r"neural\s*network", 0.15),
    (r"fine.?tun\w*", 0.12),
    (r"deep\s*learning", 0.15),
    # Production / enterprise
    (r"production.?ready", 0.10),
    (r"enterprise.?level", 0.10),
    (r"deploy\w*", 0.08),
    (r"kubernetes", 0.08),
    (r"container\w*", 0.06),
    # Security
    (r"security", 0.10),
    (r"encrypt\w*", 0.10),
    (r"vulnerab\w*", 0.10),
]

# Patterns that decrease the complexity score (simple / conversational tasks).
_SIMPLIFYING_PATTERNS: list[tuple[str, float]] = [
    (r"what\s+is", -0.08),
    (r"how\s+to", -0.06),
    (r"explain\s*(briefly|simply)?", -0.06),
    (r"summariz\w*", -0.06),
    (r"translate", -0.06),
    (r"define", -0.08),
    (r"list\s*(all|the)?", -0.04),
    (r"^(hi|hello|hey|thanks|thank\s+you|ok|okay|yes|no|sure)\b", -0.15),
    (r"how\s+are\s+you", -0.15),
    (r"what('s|\s+is)\s+up", -0.15),
]


def _score_description(description: str) -> float:
    """Compute a normalized complexity score in [0.0, 1.0] from text.

    Combines length-based scoring with keyword matching. Longer prompts and
    prompts containing technical / multi-step indicators raise the score,
    while simple conversational prompts lower it.
    """
    if not description:
        return 0.0

    text = description.lower()
    score = 0.0

    # ── Length-based scoring ──
    length = len(description)
    if length > 2000:
        score += 0.30
    elif length > 1000:
        score += 0.22
    elif length > 500:
        score += 0.15
    elif length > 200:
        score += 0.08
    elif length > 50:
        score += 0.03

    # ── Complexity-increasing keyword patterns ──
    matched_complex = 0
    for pattern, weight in _COMPLEXITY_PATTERNS:
        if re.search(pattern, text):
            score += weight
            matched_complex += 1
            if matched_complex >= 6:
                break

    # ── Complexity-decreasing keyword patterns ──
    for pattern, weight in _SIMPLIFYING_PATTERNS:
        if re.search(pattern, text):
            score += weight

    return max(0.0, min(1.0, score))


def _score_to_complexity(score: float) -> TaskComplexity:
    """Map a normalized complexity score to a TaskComplexity level."""
    if score < 0.15:
        return TaskComplexity.TRIVIAL
    if score < 0.30:
        return TaskComplexity.SIMPLE
    if score < 0.55:
        return TaskComplexity.MODERATE
    if score < 0.75:
        return TaskComplexity.COMPLEX
    return TaskComplexity.EXPERT


# ══════════════════════════════════════════════════════════════════════
# AgentCostOptimizer
# ══════════════════════════════════════════════════════════════════════

# Mapping from task complexity to the model tier the optimizer prefers.
_COMPLEXITY_TIER_MAP: dict[TaskComplexity, ModelTier] = {
    TaskComplexity.TRIVIAL: ModelTier.LITE,
    TaskComplexity.SIMPLE: ModelTier.LITE,
    TaskComplexity.MODERATE: ModelTier.STANDARD,
    TaskComplexity.COMPLEX: ModelTier.PREMIUM,
    TaskComplexity.EXPERT: ModelTier.FLAGSHIP,
}

# Ordered tiers from cheapest to most capable.
_TIER_ORDER: list[ModelTier] = [
    ModelTier.LITE,
    ModelTier.STANDARD,
    ModelTier.PREMIUM,
    ModelTier.FLAGSHIP,
]


class AgentCostOptimizer:
    """Task-difficulty-aware cost optimizer and model router.

    Maintains a registry of model profiles, assesses task complexity from
    free-text descriptions, routes each task to the most appropriate model
    according to a configurable strategy, and records actual usage so that
    optimization reports can quantify cost savings over time.
    """

    # Class constants
    MAX_MODELS: int = 50
    MAX_RECORDS: int = 10000
    COMPLEXITY_THRESHOLD: float = 0.7

    def __init__(self) -> None:
        """Initialize empty storage and counters."""
        self._models: dict[str, ModelProfile] = {}
        self._tasks: dict[str, TaskProfile] = {}
        self._decisions: dict[str, RoutingDecision] = {}
        self._records: dict[str, CostRecord] = {}
        self._total_tasks: int = 0
        self._total_decisions: int = 0

    # ── Model registry ───────────────────────────────────────────

    def register_model(
        self,
        name: str,
        provider: str,
        tier: ModelTier,
        cost_per_1k_input: float,
        cost_per_1k_output: float,
        avg_latency_ms: float,
        quality_score: float,
        max_context: int,
        capabilities: list[str] | None = None,
    ) -> ModelProfile:
        """Register a new model and return its profile.

        Raises:
            RuntimeError: If the model registry is at capacity.
        """
        if len(self._models) >= self.MAX_MODELS:
            raise RuntimeError(
                f"Cannot register model: registry at capacity ({self.MAX_MODELS})"
            )

        model_id = str(uuid.uuid4())
        profile = ModelProfile(
            model_id=model_id,
            name=name,
            provider=provider,
            tier=tier,
            cost_per_1k_input=cost_per_1k_input,
            cost_per_1k_output=cost_per_1k_output,
            avg_latency_ms=avg_latency_ms,
            quality_score=quality_score,
            max_context=max_context,
            capabilities=list(capabilities) if capabilities else [],
            active=True,
        )
        self._models[model_id] = profile
        return profile

    def update_model(
        self,
        model_id: str,
        cost_per_1k_input: float | None = None,
        cost_per_1k_output: float | None = None,
        avg_latency_ms: float | None = None,
        quality_score: float | None = None,
        active: bool | None = None,
    ) -> ModelProfile | None:
        """Update mutable fields of a registered model. Returns None if missing."""
        model = self._models.get(model_id)
        if model is None:
            return None

        if cost_per_1k_input is not None:
            model.cost_per_1k_input = cost_per_1k_input
        if cost_per_1k_output is not None:
            model.cost_per_1k_output = cost_per_1k_output
        if avg_latency_ms is not None:
            model.avg_latency_ms = avg_latency_ms
        if quality_score is not None:
            model.quality_score = quality_score
        if active is not None:
            model.active = active
        return model

    def remove_model(self, model_id: str) -> bool:
        """Remove a model from the registry. Returns True if removed."""
        if model_id in self._models:
            del self._models[model_id]
            return True
        return False

    def get_model(self, model_id: str) -> ModelProfile | None:
        """Retrieve a model profile by ID."""
        return self._models.get(model_id)

    def list_models(
        self,
        tier: ModelTier | None = None,
        active_only: bool = True,
    ) -> list[ModelProfile]:
        """List registered models, optionally filtered by tier and active state."""
        result: list[ModelProfile] = []
        for model in self._models.values():
            if tier is not None and model.tier is not tier:
                continue
            if active_only and not model.active:
                continue
            result.append(model)
        return result

    # ── Complexity assessment ────────────────────────────────────

    def assess_complexity(
        self,
        description: str,
        required_capabilities: list[str] | None = None,
        estimated_tokens: int = 1000,
    ) -> TaskProfile:
        """Assess task complexity from a free-text description.

        Uses heuristic complexity detection combining:
        - Prompt length
        - Keyword / regex matching for technical and multi-step indicators
        - Required capability count (each required capability adds a small bump)

        Returns a TaskProfile with the detected complexity.
        """
        score = _score_description(description)

        # Each required capability nudges the score upward — tasks that need
        # more specialized capabilities tend to be harder.
        caps = list(required_capabilities) if required_capabilities else []
        if caps:
            score += min(0.20, len(caps) * 0.04)
            score = max(0.0, min(1.0, score))

        complexity = _score_to_complexity(score)

        task_profile = TaskProfile(
            task_id=str(uuid.uuid4()),
            description=description,
            detected_complexity=complexity,
            required_capabilities=caps,
            estimated_tokens=estimated_tokens,
            created_at=time.time(),
        )
        self._tasks[task_profile.task_id] = task_profile
        self._total_tasks += 1
        return task_profile

    # ── Routing ──────────────────────────────────────────────────

    def route(
        self,
        task_profile: TaskProfile,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    ) -> RoutingDecision:
        """Select the best model for a task according to the chosen strategy.

        The optimizer filters candidates by required capabilities and context
        window, then scores each remaining model using a strategy-specific
        scoring function. A confidence value reflects how dominant the winner
        is among the candidates.
        """
        complexity = task_profile.detected_complexity
        target_tier = _COMPLEXITY_TIER_MAP[complexity]
        required_caps = set(task_profile.required_capabilities)

        # ── Build candidate pool ──
        candidates: list[ModelProfile] = [
            m for m in self._models.values() if m.active
        ]

        # Filter by required capabilities
        if required_caps:
            candidates = [
                m for m in candidates
                if required_caps.issubset(set(m.capabilities))
            ]

        # Filter by context window
        candidates = [
            m for m in candidates
            if m.max_context >= task_profile.estimated_tokens
        ]

        # Fallback: drop the capability requirement if it wiped out everything
        if not candidates and required_caps:
            candidates = [
                m for m in self._models.values()
                if m.active and m.max_context >= task_profile.estimated_tokens
            ]

        # Fallback: ignore context limit as well
        if not candidates:
            candidates = [m for m in self._models.values() if m.active]

        # Final fallback: use a synthetic placeholder so routing still returns
        # a decision instead of raising.
        if not candidates:
            placeholder = ModelProfile(
                model_id="placeholder",
                name="placeholder-model",
                provider="unknown",
                tier=target_tier,
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.004,
                avg_latency_ms=500.0,
                quality_score=0.5,
                max_context=4096,
                capabilities=[],
                active=True,
            )
            candidates = [placeholder]

        # ── Score candidates ──
        # Prefer candidates in the target tier by giving them a small bonus.
        scored: list[tuple[float, ModelProfile]] = []
        for model in candidates:
            base = self._score_model(model, task_profile, strategy)
            tier_bonus = 0.10 if model.tier is target_tier else 0.0
            scored.append((base + tier_bonus, model))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        best_score, selected = scored[0]

        # Confidence: ratio of the winner's score to the sum of all candidate
        # scores (bounded to [0, 1]).
        total_score = sum(s for s, _ in scored) or 1.0
        confidence = max(0.0, min(1.0, best_score / total_score))

        # Alternative models: the next best candidates (up to 3).
        alternatives = [m.model_id for _, m in scored[1:4] if m.model_id != selected.model_id]

        # ── Estimate cost / latency / quality ──
        est_cost = self._estimate_cost(selected, task_profile.estimated_tokens)
        est_latency = selected.avg_latency_ms
        est_quality = selected.quality_score

        # Build reasoning string
        reasoning = (
            f"Complexity={complexity.value} → target tier={target_tier.value}; "
            f"strategy={strategy.value}; selected {selected.provider}/{selected.name} "
            f"(tier={selected.tier.value}, quality={selected.quality_score:.2f})"
        )

        decision = RoutingDecision(
            decision_id=str(uuid.uuid4()),
            task_id=task_profile.task_id,
            selected_model_id=selected.model_id,
            alternative_models=alternatives,
            strategy=strategy,
            estimated_cost=est_cost,
            estimated_latency=est_latency,
            estimated_quality=est_quality,
            confidence=confidence,
            reasoning=reasoning,
            created_at=time.time(),
        )
        self._decisions[decision.decision_id] = decision
        self._total_decisions += 1
        return decision

    def _score_model(
        self,
        model: ModelProfile,
        task_profile: TaskProfile,
        strategy: RoutingStrategy,
    ) -> float:
        """Score a candidate model under the chosen strategy (higher is better)."""
        est_cost = self._estimate_cost(model, task_profile.estimated_tokens)
        # Avoid division by zero for free models
        cost_component = 1.0 / (1.0 + est_cost * 1000.0)
        quality_component = max(0.0, min(1.0, model.quality_score))
        latency_component = 1.0 / (1.0 + model.avg_latency_ms / 1000.0)

        if strategy is RoutingStrategy.COST_FIRST:
            return 0.7 * cost_component + 0.2 * quality_component + 0.1 * latency_component
        if strategy is RoutingStrategy.QUALITY_FIRST:
            return 0.7 * quality_component + 0.2 * cost_component + 0.1 * latency_component
        if strategy is RoutingStrategy.LATENCY_FIRST:
            return 0.7 * latency_component + 0.2 * cost_component + 0.1 * quality_component
        # BALANCED default
        return 0.4 * cost_component + 0.4 * quality_component + 0.2 * latency_component

    @staticmethod
    def _estimate_cost(model: ModelProfile, estimated_tokens: int) -> float:
        """Estimate the dollar cost for a task on a given model.

        Splits the estimated tokens evenly between input and output as a
        conservative default when actual token usage is unknown.
        """
        half = estimated_tokens / 2.0
        input_cost = (half / 1000.0) * model.cost_per_1k_input
        output_cost = (half / 1000.0) * model.cost_per_1k_output
        return round(input_cost + output_cost, 6)

    def get_decision(self, decision_id: str) -> RoutingDecision | None:
        """Retrieve a routing decision by ID."""
        return self._decisions.get(decision_id)

    # ── Usage recording ──────────────────────────────────────────

    def record_usage(
        self,
        model_id: str,
        task_id: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        quality_score: float | None = None,
    ) -> CostRecord:
        """Record actual usage for a model invocation and return the record.

        The cost is computed from the model's registered pricing. If the
        model is unknown a default pricing is used. When the record store is
        at capacity the oldest records are evicted.
        """
        model = self._models.get(model_id)
        if model is not None:
            cost = (
                (input_tokens / 1000.0) * model.cost_per_1k_input
                + (output_tokens / 1000.0) * model.cost_per_1k_output
            )
            recorded_quality = quality_score if quality_score is not None else model.quality_score
        else:
            # Default fallback pricing when model is not registered
            cost = (
                (input_tokens / 1000.0) * 0.001
                + (output_tokens / 1000.0) * 0.004
            )
            recorded_quality = quality_score if quality_score is not None else 0.0

        record = CostRecord(
            record_id=str(uuid.uuid4()),
            model_id=model_id,
            task_id=task_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=round(cost, 6),
            latency_ms=latency_ms,
            quality_score=recorded_quality,
            created_at=time.time(),
        )
        self._records[record.record_id] = record

        # Evict oldest records if over capacity
        if len(self._records) > self.MAX_RECORDS:
            # Sort by created_at ascending and drop the oldest surplus records
            sorted_ids = sorted(
                self._records,
                key=lambda rid: self._records[rid].created_at,
            )
            surplus = len(self._records) - self.MAX_RECORDS
            for rid in sorted_ids[:surplus]:
                del self._records[rid]

        return record

    # ── Reporting & stats ────────────────────────────────────────

    def generate_report(
        self,
        period_start: float | None = None,
        period_end: float | None = None,
    ) -> OptimizationReport:
        """Generate an optimization report for a time window (defaults to all)."""
        end = period_end if period_end is not None else time.time()
        start = period_start if period_start is not None else 0.0

        # Filter records to the requested window
        in_window: list[CostRecord] = [
            r for r in self._records.values()
            if start <= r.created_at <= end
        ]

        total_cost = sum(r.cost for r in in_window)
        total_tasks = len(in_window)
        avg_cost_per_task = (total_cost / total_tasks) if total_tasks else 0.0

        # ── Cost savings vs. flagship baseline ──
        # For each record, estimate what the same tokens would have cost on
        # the most expensive registered flagship model. If no flagship is
        # registered, fall back to a notional flagship price.
        flagship_models = [m for m in self._models.values() if m.tier is ModelTier.FLAGSHIP]
        if flagship_models:
            flagship = max(
                flagship_models,
                key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output,
            )
            flagship_in = flagship.cost_per_1k_input
            flagship_out = flagship.cost_per_1k_output
        else:
            flagship_in = 0.015
            flagship_out = 0.075

        baseline_cost = 0.0
        for r in in_window:
            baseline_cost += (
                (r.input_tokens / 1000.0) * flagship_in
                + (r.output_tokens / 1000.0) * flagship_out
            )
        cost_savings = max(0.0, baseline_cost - total_cost)

        # ── Distributions ──
        model_distribution: dict[str, int] = defaultdict(int)
        for r in in_window:
            model_distribution[r.model_id] += 1

        complexity_distribution: dict[str, int] = defaultdict(int)
        for task in self._tasks.values():
            if start <= task.created_at <= end:
                complexity_distribution[task.detected_complexity.value] += 1

        report = OptimizationReport(
            report_id=str(uuid.uuid4()),
            period_start=start,
            period_end=end,
            total_cost=round(total_cost, 6),
            total_tasks=total_tasks,
            avg_cost_per_task=round(avg_cost_per_task, 6),
            cost_savings=round(cost_savings, 6),
            model_distribution=dict(model_distribution),
            complexity_distribution=dict(complexity_distribution),
            created_at=time.time(),
        )
        return report

    def get_stats(self) -> dict[str, Any]:
        """Return a snapshot of optimizer state for dashboards."""
        records = list(self._records.values())
        record_count = len(records)
        total_cost = sum(r.cost for r in records)
        avg_cost_per_task = (total_cost / record_count) if record_count else 0.0
        avg_quality = (
            sum(r.quality_score for r in records) / record_count
            if record_count else 0.0
        )

        model_distribution: dict[str, int] = defaultdict(int)
        for r in records:
            model_distribution[r.model_id] += 1

        complexity_distribution: dict[str, int] = defaultdict(int)
        for task in self._tasks.values():
            complexity_distribution[task.detected_complexity.value] += 1

        tier_distribution: dict[str, int] = defaultdict(int)
        for model in self._models.values():
            tier_distribution[model.tier.value] += 1

        return {
            "total_models": len(self._models),
            "active_models": sum(1 for m in self._models.values() if m.active),
            "total_tasks": self._total_tasks,
            "total_decisions": self._total_decisions,
            "total_cost": round(total_cost, 6),
            "avg_cost_per_task": round(avg_cost_per_task, 6),
            "avg_quality": round(avg_quality, 4),
            "model_distribution": dict(model_distribution),
            "complexity_distribution": dict(complexity_distribution),
            "tier_distribution": dict(tier_distribution),
        }

    # ── Lifecycle ────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset the optimizer to its initial empty state."""
        self._models.clear()
        self._tasks.clear()
        self._decisions.clear()
        self._records.clear()
        self._total_tasks = 0
        self._total_decisions = 0


# ══════════════════════════════════════════════════════════════════════
# Singleton accessors
# ══════════════════════════════════════════════════════════════════════

_cost_optimizer: AgentCostOptimizer | None = None


def get_cost_optimizer() -> AgentCostOptimizer:
    """Get or create the singleton cost optimizer instance."""
    global _cost_optimizer
    if _cost_optimizer is None:
        _cost_optimizer = AgentCostOptimizer()
    return _cost_optimizer


def reset_cost_optimizer() -> None:
    """Reset the singleton cost optimizer instance."""
    global _cost_optimizer
    if _cost_optimizer is not None:
        _cost_optimizer.reset()
    _cost_optimizer = None
