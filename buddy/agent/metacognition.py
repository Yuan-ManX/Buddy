"""Buddy Meta-Cognition — adaptive reasoning strategy selection and self-optimization

Provides a neural-inspired layer that dynamically evaluates incoming tasks
and selects the optimal combination of reasoning style, model tier, tool
context, and execution strategy. Continuously learns from past outcomes
to refine its selection heuristics over time.

Core capabilities:
  - Dynamic Strategy Selection: chooses reasoning style, model, and tools per task
  - Outcome Tracking: records success/failure patterns to refine future decisions
  - Cost-Aware Routing: balances quality against token cost for each decision
  - Context Optimization: determines optimal context window size and pruning
  - Confidence Calibration: adjusts confidence scores based on historical accuracy
  - Strategy Learning: builds a decision graph from past execution traces
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.metacognition")


class DecisionAxis(str, Enum):
    """Dimensions along which the meta-cognition layer makes decisions."""
    REASONING_STYLE = "reasoning_style"
    MODEL_TIER = "model_tier"
    TOOL_CONTEXT = "tool_context"
    CONTEXT_WINDOW = "context_window"
    EXECUTION_MODE = "execution_mode"


class ExecutionMode(str, Enum):
    """High-level execution strategies."""
    DIRECT = "direct"              # Single-pass, no reasoning overhead
    REASONED = "reasoned"          # Standard observe-think-act-reflect cycle
    PLAN_DRIVEN = "plan_driven"    # Decompose into plan, execute step by step
    DELEGATED = "delegated"        # Distribute to sub-agents or swarm
    EXPLORATORY = "exploratory"    # Tree-of-thought or parallel perspectives
    VERIFIED = "verified"          # Self-consistency with multiple samples


@dataclass
class StrategyDecision:
    """A complete strategy decision for handling a task."""
    reasoning_style: str = "balanced"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096
    execution_mode: ExecutionMode = ExecutionMode.DIRECT
    enable_tools: bool = True
    enable_reasoning: bool = False
    context_window_size: int = 40
    estimated_cost: float = 0.0
    confidence: float = 0.7
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "reasoning_style": self.reasoning_style,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "execution_mode": self.execution_mode.value,
            "enable_tools": self.enable_tools,
            "enable_reasoning": self.enable_reasoning,
            "context_window_size": self.context_window_size,
            "estimated_cost": self.estimated_cost,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


@dataclass
class OutcomeRecord:
    """Record of a strategy decision outcome for learning."""
    task_signature: str          # Hashed task fingerprint
    decision: StrategyDecision
    success: bool
    quality_score: float         # 0.0-1.0
    actual_tokens: int
    actual_time_ms: float
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "task_signature": self.task_signature,
            "decision": self.decision.to_dict(),
            "success": self.success,
            "quality_score": self.quality_score,
            "actual_tokens": self.actual_tokens,
            "actual_time_ms": self.actual_time_ms,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }


class MetaCognition:
    """Adaptive strategy selection layer with self-optimization.

    Analyzes incoming tasks to determine the optimal execution strategy
    by combining lexical heuristics, historical outcome data, and cost
    modeling. Learns from past decisions to continuously improve.
    """

    # Model tier definitions with cost multipliers
    MODEL_TIERS = {
        "light": {
            "models": ["gpt-4o-mini", "gpt-3.5-turbo"],
            "cost_per_1k_tokens": 0.00015,
            "suitable_for": ["simple_factual", "greeting", "quick_lookup"],
        },
        "standard": {
            "models": ["gpt-4o", "gpt-4-turbo"],
            "cost_per_1k_tokens": 0.003,
            "suitable_for": ["coding_technical", "general", "creative_brainstorm"],
        },
        "premium": {
            "models": ["gpt-4.5-preview", "claude-3-5-sonnet"],
            "cost_per_1k_tokens": 0.015,
            "suitable_for": ["complex_multi_step", "math_logic", "architecture_design"],
        },
    }

    # Task complexity to execution mode mapping
    COMPLEXITY_MODE_MAP = {
        "simple_factual": ExecutionMode.DIRECT,
        "greeting": ExecutionMode.DIRECT,
        "quick_lookup": ExecutionMode.DIRECT,
        "general": ExecutionMode.REASONED,
        "coding_technical": ExecutionMode.REASONED,
        "creative_brainstorm": ExecutionMode.EXPLORATORY,
        "complex_multi_step": ExecutionMode.PLAN_DRIVEN,
        "math_logic": ExecutionMode.VERIFIED,
        "architecture_design": ExecutionMode.EXPLORATORY,
        "research_deep": ExecutionMode.DELEGATED,
        "multi_agent_task": ExecutionMode.DELEGATED,
    }

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._outcome_history: list[OutcomeRecord] = []
        self._strategy_stats: dict[str, dict] = defaultdict(
            lambda: {"successes": 0, "failures": 0, "total_tokens": 0, "total_time_ms": 0.0}
        )
        self._max_history = 500
        self._decision_count = 0
        self._last_decision_at: str = ""

    # ── Decision Engine ──────────────────────────────────

    def decide(
        self,
        task_signature: str,
        task_complexity: str = "general",
        context_depth: int = 0,
        user_preference: str | None = None,
        cost_budget: float | None = None,
        urgency: str = "normal",
    ) -> StrategyDecision:
        """Determine the optimal execution strategy for a given task.

        Args:
            task_signature: A hashed fingerprint of the task content.
            task_complexity: The complexity classification (e.g., 'simple_factual').
            context_depth: Current conversation depth (message count).
            user_preference: Optional user-specified preference (e.g., 'fast', 'thorough').
            cost_budget: Optional cost budget constraint.
            urgency: Urgency level ('low', 'normal', 'high', 'critical').

        Returns:
            A StrategyDecision with the recommended execution parameters.
        """
        self._decision_count += 1
        self._last_decision_at = datetime.now(timezone.utc).isoformat()
        start = time.time()

        # ── Step 1: Determine execution mode ──
        execution_mode = self.COMPLEXITY_MODE_MAP.get(
            task_complexity, ExecutionMode.REASONED
        )

        # Override based on user preference
        if user_preference == "fast":
            execution_mode = ExecutionMode.DIRECT
        elif user_preference == "thorough":
            if execution_mode in (ExecutionMode.DIRECT, ExecutionMode.REASONED):
                execution_mode = ExecutionMode.VERIFIED

        # ── Step 2: Select model tier ──
        model_tier = "standard"
        if task_complexity in ("simple_factual", "greeting", "quick_lookup"):
            model_tier = "light"
        elif task_complexity in ("complex_multi_step", "math_logic", "architecture_design"):
            model_tier = "premium"
        elif execution_mode == ExecutionMode.EXPLORATORY:
            model_tier = "standard"
        elif execution_mode == ExecutionMode.VERIFIED:
            model_tier = "premium"

        # Downgrade if cost budget is constrained
        if cost_budget is not None and cost_budget < 0.01:
            model_tier = "light"
        elif cost_budget is not None and cost_budget < 0.05:
            model_tier = "standard" if model_tier == "premium" else model_tier

        # Upgrade for critical urgency
        if urgency == "critical":
            model_tier = "premium"

        tier_config = self.MODEL_TIERS[model_tier]
        model = tier_config["models"][0]

        # ── Step 3: Determine reasoning style ──
        reasoning_style = "balanced"
        reason_map = {
            "simple_factual": "concise",
            "greeting": "concise",
            "quick_lookup": "concise",
            "coding_technical": "coding",
            "creative_brainstorm": "creative",
            "complex_multi_step": "tree",
            "math_logic": "self_consistency",
            "architecture_design": "parallel",
            "research_deep": "thorough",
            "general": "balanced",
        }
        reasoning_style = reason_map.get(task_complexity, "balanced")

        # ── Step 4: Determine tool and reasoning enabling ──
        enable_tools = task_complexity not in ("greeting", "simple_factual")
        enable_reasoning = execution_mode in (
            ExecutionMode.REASONED, ExecutionMode.PLAN_DRIVEN,
            ExecutionMode.EXPLORATORY, ExecutionMode.VERIFIED,
        )

        # ── Step 5: Context window sizing ──
        context_window_size = 40
        if execution_mode == ExecutionMode.DIRECT:
            context_window_size = 20
        elif execution_mode == ExecutionMode.PLAN_DRIVEN:
            context_window_size = 60
        elif execution_mode == ExecutionMode.EXPLORATORY:
            context_window_size = 50
        elif context_depth > 30:
            context_window_size = min(context_depth + 10, 80)

        # ── Step 6: Temperature calibration ──
        temperature = 0.7
        if reasoning_style == "concise":
            temperature = 0.3
        elif reasoning_style == "coding":
            temperature = 0.4
        elif reasoning_style == "creative":
            temperature = 0.9
        elif reasoning_style == "self_consistency":
            temperature = 0.7

        # ── Step 7: Estimate cost ──
        estimated_tokens = context_window_size * 200 + 1000
        estimated_cost = tier_config["cost_per_1k_tokens"] * (estimated_tokens / 1000)

        # ── Step 8: Learn from history ──
        confidence = 0.7
        learned = self._learn_from_history(task_complexity, execution_mode, model_tier)
        if learned:
            confidence = learned.get("confidence", 0.7)
            if learned.get("downgrade_mode"):
                execution_mode = ExecutionMode.DIRECT

        rationale = (
            f"Task classified as '{task_complexity}' with {context_depth} context messages. "
            f"Selected {model_tier} tier ({model}) in {execution_mode.value} mode "
            f"with {reasoning_style} reasoning. "
            f"Confidence: {confidence:.2f}, est. cost: ${estimated_cost:.4f}."
        )

        decision = StrategyDecision(
            reasoning_style=reasoning_style,
            model=model,
            temperature=temperature,
            max_tokens=4096,
            execution_mode=execution_mode,
            enable_tools=enable_tools,
            enable_reasoning=enable_reasoning,
            context_window_size=context_window_size,
            estimated_cost=estimated_cost,
            confidence=confidence,
            rationale=rationale,
        )

        logger.debug(
            f"Meta-cognition decision for {self.agent_id}: "
            f"mode={execution_mode.value}, model={model}, "
            f"reasoning={reasoning_style}, confidence={confidence:.2f}"
        )

        return decision

    def _learn_from_history(
        self,
        task_complexity: str,
        execution_mode: ExecutionMode,
        model_tier: str,
    ) -> dict | None:
        """Analyze historical outcomes to refine the current decision.

        Returns a dict with adjustment recommendations, or None if no
        relevant history exists.
        """
        if not self._outcome_history:
            return None

        # Filter relevant outcomes: same task complexity
        relevant = [
            o for o in self._outcome_history[-100:]
            if o.decision.execution_mode.value == execution_mode.value
            or o.decision.reasoning_style in self.COMPLEXITY_MODE_MAP
        ]

        if not relevant:
            return None

        # Calculate success rate for similar decisions
        successes = sum(1 for o in relevant if o.success)
        total = len(relevant)
        success_rate = successes / total if total > 0 else 0.5

        result = {"confidence": success_rate, "downgrade_mode": False}

        # If similar decisions have low success rate, suggest downgrade
        if success_rate < 0.3 and total >= 3:
            result["downgrade_mode"] = True
            result["confidence"] = 0.3

        # If consistently high success, boost confidence
        if success_rate > 0.85 and total >= 5:
            result["confidence"] = min(0.95, success_rate + 0.05)

        return result

    # ── Outcome Recording ────────────────────────────────

    def record_outcome(
        self,
        task_signature: str,
        decision: StrategyDecision,
        success: bool,
        quality_score: float = 0.5,
        actual_tokens: int = 0,
        actual_time_ms: float = 0.0,
        error_message: str = "",
    ):
        """Record the outcome of a strategy decision for future learning."""
        record = OutcomeRecord(
            task_signature=task_signature,
            decision=decision,
            success=success,
            quality_score=quality_score,
            actual_tokens=actual_tokens,
            actual_time_ms=actual_time_ms,
            error_message=error_message,
        )

        self._outcome_history.append(record)
        if len(self._outcome_history) > self._max_history:
            self._outcome_history = self._outcome_history[-self._max_history:]

        # Update aggregate stats
        key = decision.execution_mode.value
        stats = self._strategy_stats[key]
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        stats["total_tokens"] += actual_tokens
        stats["total_time_ms"] += actual_time_ms

    # ── Task Fingerprinting ──────────────────────────────

    @staticmethod
    def fingerprint(text: str) -> str:
        """Create a compact task signature from text content.

        Uses a simple hash of key structural features: length, first/last
        characters, keyword density, and character distribution.
        """
        import hashlib

        # Extract structural features
        features = [
            str(len(text)),
            text[:50] if len(text) > 50 else text,
            text[-50:] if len(text) > 50 else "",
            str(len(text.split())),
            str(text.count("?")),
            str(text.count("\n")),
            str(text.count("```")),
        ]
        feature_str = "|".join(features)
        return hashlib.md5(feature_str.encode()).hexdigest()[:12]

    # ── Statistics & Introspection ───────────────────────

    def get_stats(self) -> dict:
        """Get meta-cognition statistics."""
        total_outcomes = len(self._outcome_history)
        recent = self._outcome_history[-50:]
        recent_successes = sum(1 for o in recent if o.success)
        recent_rate = recent_successes / max(len(recent), 1)

        # Most used execution modes
        mode_counts: dict[str, int] = defaultdict(int)
        for o in self._outcome_history:
            mode_counts[o.decision.execution_mode.value] += 1

        # Average cost per decision
        total_cost = sum(o.decision.estimated_cost for o in self._outcome_history)
        avg_cost = total_cost / max(total_outcomes, 1)

        return {
            "agent_id": self.agent_id,
            "total_decisions": self._decision_count,
            "total_outcomes": total_outcomes,
            "success_rate": f"{recent_rate:.1%}",
            "recent_successes": recent_successes,
            "recent_total": len(recent),
            "mode_distribution": dict(mode_counts),
            "avg_estimated_cost": round(avg_cost, 6),
            "strategy_stats": {
                k: {
                    "successes": v["successes"],
                    "failures": v["failures"],
                    "success_rate": f"{v['successes'] / max(v['successes'] + v['failures'], 1):.1%}",
                    "avg_tokens": v["total_tokens"] // max(v["successes"] + v["failures"], 1),
                }
                for k, v in self._strategy_stats.items()
            },
            "last_decision_at": self._last_decision_at,
        }

    def get_recent_decisions(self, limit: int = 20) -> list[dict]:
        """Get recent strategy decisions with their outcomes."""
        return [
            {
                "task_signature": o.task_signature,
                "decision": o.decision.to_dict(),
                "success": o.success,
                "quality_score": o.quality_score,
                "actual_tokens": o.actual_tokens,
                "actual_time_ms": o.actual_time_ms,
                "timestamp": o.timestamp,
            }
            for o in self._outcome_history[-limit:]
        ]

    def get_decision_insights(self) -> list[str]:
        """Generate actionable insights from outcome history."""
        insights = []

        if len(self._outcome_history) < 10:
            insights.append("Collecting data — at least 10 decisions needed for insights.")
            return insights

        # Check for mode-specific patterns
        for mode, stats in self._strategy_stats.items():
            total = stats["successes"] + stats["failures"]
            if total >= 5:
                rate = stats["successes"] / total
                if rate < 0.4:
                    insights.append(
                        f"Low success rate for '{mode}' mode ({rate:.0%}). "
                        f"Consider exploring alternative strategies."
                    )
                elif rate > 0.9:
                    insights.append(
                        f"High success rate for '{mode}' mode ({rate:.0%}). "
                        f"This is a reliable strategy for similar tasks."
                    )

        # Check for cost efficiency
        premium_outcomes = [
            o for o in self._outcome_history
            if o.decision.model in self.MODEL_TIERS["premium"]["models"]
        ]
        if premium_outcomes:
            premium_success = sum(1 for o in premium_outcomes if o.success) / len(premium_outcomes)
            if premium_success < 0.5:
                insights.append(
                    f"Premium models have low success rate ({premium_success:.0%}). "
                    f"Consider using standard tier for similar tasks."
                )

        return insights