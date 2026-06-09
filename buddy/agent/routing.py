"""Buddy Smart Model Router — difficulty-aware model selection and cost optimization

Routes tasks to the appropriate model tier based on complexity analysis,
reducing token costs without sacrificing quality on critical operations.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("buddy.routing")


class TaskComplexity(str, Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class ModelTier(str, Enum):
    LIGHT = "light"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class RoutingDecision:
    complexity: TaskComplexity
    tier: ModelTier
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    reasoning: str = ""


@dataclass
class ModelTierConfig:
    tier: ModelTier
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    cost_multiplier: float = 1.0


class ModelRouter:
    """Intelligent model router that analyzes task complexity and selects optimal model tier."""

    COMPLEXITY_INDICATORS = {
        TaskComplexity.TRIVIAL: [
            "hello", "hi", "hey", "thanks", "ok", "yes", "no",
            "what is your name", "who are you",
        ],
        TaskComplexity.COMPLEX: [
            "analyze", "architecture", "design", "implement", "optimize",
            "debug", "refactor", "deploy", "migrate", "scale",
            "security", "performance", "algorithm", "system",
            "comprehensive", "thorough", "detailed", "in-depth",
        ],
        TaskComplexity.EXPERT: [
            "research", "scientific", "machine learning", "neural network",
            "distributed", "microservices", "kubernetes", "infrastructure",
            "cryptography", "compiler", "operating system", "database engine",
        ],
    }

    def __init__(self):
        self.tiers: dict[ModelTier, ModelTierConfig] = {
            ModelTier.LIGHT: ModelTierConfig(
                tier=ModelTier.LIGHT,
                model="gpt-4o-mini",
                temperature=0.5,
                max_tokens=2048,
                cost_multiplier=0.1,
            ),
            ModelTier.STANDARD: ModelTierConfig(
                tier=ModelTier.STANDARD,
                model="gpt-4o",
                temperature=0.7,
                max_tokens=4096,
                cost_multiplier=1.0,
            ),
            ModelTier.PREMIUM: ModelTierConfig(
                tier=ModelTier.PREMIUM,
                model="gpt-4o",
                temperature=0.3,
                max_tokens=8192,
                cost_multiplier=2.5,
            ),
        }
        self._usage_stats: dict[ModelTier, int] = {t: 0 for t in ModelTier}

    def configure_tier(self, tier: ModelTier, config: ModelTierConfig):
        self.tiers[tier] = config

    def analyze_complexity(self, message: str) -> TaskComplexity:
        msg_lower = message.lower().strip()

        if len(msg_lower) < 10:
            return TaskComplexity.TRIVIAL

        for indicator in self.COMPLEXITY_INDICATORS[TaskComplexity.EXPERT]:
            if indicator in msg_lower:
                return TaskComplexity.EXPERT

        for indicator in self.COMPLEXITY_INDICATORS[TaskComplexity.COMPLEX]:
            if indicator in msg_lower:
                return TaskComplexity.COMPLEX

        for indicator in self.COMPLEXITY_INDICATORS[TaskComplexity.TRIVIAL]:
            if indicator == msg_lower:
                return TaskComplexity.TRIVIAL

        word_count = len(msg_lower.split())
        if word_count < 5:
            return TaskComplexity.TRIVIAL
        elif word_count < 20:
            return TaskComplexity.SIMPLE
        elif word_count < 80:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.COMPLEX

    def route(self, message: str, context_depth: int = 0) -> RoutingDecision:
        complexity = self.analyze_complexity(message)

        tier_mapping = {
            TaskComplexity.TRIVIAL: ModelTier.LIGHT,
            TaskComplexity.SIMPLE: ModelTier.LIGHT,
            TaskComplexity.MODERATE: ModelTier.STANDARD,
            TaskComplexity.COMPLEX: ModelTier.STANDARD,
            TaskComplexity.EXPERT: ModelTier.PREMIUM,
        }

        if context_depth > 50:
            tier_mapping[TaskComplexity.SIMPLE] = ModelTier.STANDARD
            tier_mapping[TaskComplexity.MODERATE] = ModelTier.PREMIUM

        tier = tier_mapping[complexity]
        config = self.tiers[tier]
        self._usage_stats[tier] += 1

        reasoning_lines = [
            f"Complexity: {complexity.value}",
            f"Model tier: {tier.value}",
            f"Word count: {len(message.split())}",
        ]
        if context_depth:
            reasoning_lines.append(f"Context depth: {context_depth} messages")

        return RoutingDecision(
            complexity=complexity,
            tier=tier,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            reasoning=" | ".join(reasoning_lines),
        )

    def get_usage_stats(self) -> dict:
        total = sum(self._usage_stats.values())
        total_cost = sum(
            self._usage_stats[t] * self.tiers[t].cost_multiplier
            for t in ModelTier
        )
        avg_cost = f"${total_cost / total:.4f}" if total > 0 else "$0.0000"
        return {
            "tiers": {t.value: c for t, c in self._usage_stats.items()},
            "total": total,
            "total_requests": total,
            "tier_distribution": {t.value: c for t, c in self._usage_stats.items()},
            "average_cost": avg_cost,
            "estimated_savings": f"{self._estimate_savings():.0f}%",
        }

    def _estimate_savings(self) -> float:
        total_calls = sum(self._usage_stats.values())
        if total_calls == 0:
            return 0.0

        actual_cost = sum(
            self._usage_stats[t] * self.tiers[t].cost_multiplier
            for t in ModelTier
        )
        premium_cost = total_calls * self.tiers[ModelTier.PREMIUM].cost_multiplier
        return (1 - actual_cost / premium_cost) * 100 if premium_cost > 0 else 0.0


model_router = ModelRouter()