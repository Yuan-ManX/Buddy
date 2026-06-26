"""
Agent Multi-Model Conductor - Dynamic model selection and orchestration.

Orchestrates multiple LLM providers with:
- Intelligent model routing based on task complexity analysis
- Load balancing across provider endpoints
- Cost-aware model selection with budget optimization
- Automatic fallback and failover chains
- Performance tracking and provider health monitoring
- Ensemble strategies for high-stakes decisions
- Latency-aware routing with SLA enforcement
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.multi_model_conductor")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class TaskComplexity(str, Enum):
    """Task complexity levels for model routing."""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class ModelTier(str, Enum):
    """Model capability tiers."""
    LIGHTWEIGHT = "lightweight"
    STANDARD = "standard"
    ADVANCED = "advanced"
    PREMIUM = "premium"
    SPECIALIZED = "specialized"


class RoutingStrategy(str, Enum):
    """Model routing strategies."""
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    ENSEMBLE = "ensemble"
    FALLBACK_CHAIN = "fallback_chain"
    ROUND_ROBIN = "round_robin"
    LATENCY_SENSITIVE = "latency_sensitive"


class ProviderHealth(str, Enum):
    """Health status of a model provider."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class EnsembleMethod(str, Enum):
    """Ensemble combination methods."""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    BEST_OF_N = "best_of_n"
    CONSENSUS = "consensus"
    CASCADE = "cascade"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class ModelEndpoint:
    """A single model endpoint configuration."""
    endpoint_id: str
    provider: str
    model_name: str
    tier: ModelTier
    api_base: str = ""
    api_key_env: str = ""
    max_tokens: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    health: ProviderHealth = ProviderHealth.UNKNOWN
    capabilities: list[str] = field(default_factory=list)
    rate_limit_rpm: int = 60
    current_rpm: int = 0
    last_used: datetime | None = None
    failure_count: int = 0
    consecutive_failures: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint_id": self.endpoint_id,
            "provider": self.provider,
            "model_name": self.model_name,
            "tier": self.tier.value,
            "max_tokens": self.max_tokens,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": self.success_rate,
            "health": self.health.value,
            "capabilities": self.capabilities,
            "rate_limit_rpm": self.rate_limit_rpm,
            "current_rpm": self.current_rpm,
        }


@dataclass
class RoutingDecision:
    """Result of a model routing decision."""
    decision_id: str
    endpoint: ModelEndpoint
    strategy: RoutingStrategy
    complexity: TaskComplexity
    reason: str
    estimated_cost: float
    fallback_endpoints: list[ModelEndpoint] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "endpoint": self.endpoint.to_dict(),
            "strategy": self.strategy.value,
            "complexity": self.complexity.value,
            "reason": self.reason,
            "estimated_cost": self.estimated_cost,
            "fallback_count": len(self.fallback_endpoints),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ModelExecution:
    """Record of a model execution."""
    execution_id: str
    endpoint_id: str
    model_name: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost: float
    success: bool
    error: str = ""
    decision_id: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "endpoint_id": self.endpoint_id,
            "model_name": self.model_name,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "success": self.success,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ConductorStats:
    """Statistics for the multi-model conductor."""
    total_requests: int = 0
    total_successful: int = 0
    total_failed: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    endpoint_usage: dict[str, int] = field(default_factory=dict)
    strategy_usage: dict[str, int] = field(default_factory=dict)
    complexity_distribution: dict[str, int] = field(default_factory=dict)
    fallback_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_successful": self.total_successful,
            "total_failed": self.total_failed,
            "success_rate": self.total_successful / max(1, self.total_requests),
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "avg_latency_ms": self.avg_latency_ms,
            "endpoint_usage": self.endpoint_usage,
            "strategy_usage": self.strategy_usage,
            "complexity_distribution": self.complexity_distribution,
            "fallback_count": self.fallback_count,
        }


# ═══════════════════════════════════════════════════════════
# Multi-Model Conductor
# ═══════════════════════════════════════════════════════════

class MultiModelConductor:
    """
    Orchestrates multiple LLM providers with intelligent routing.
    
    Features:
    - Task complexity analysis for model selection
    - Cost-aware routing with budget optimization
    - Automatic failover and health monitoring
    - Ensemble strategies for critical decisions
    - Performance tracking and adaptive routing
    - Provider load balancing
    """

    def __init__(self, config: ConductorConfig | None = None):
        self.config = config or ConductorConfig()
        self._endpoints: dict[str, ModelEndpoint] = {}
        self._executions: list[ModelExecution] = []
        self._decisions: dict[str, RoutingDecision] = {}
        self._stats = ConductorStats()
        self._complexity_analyzer = ComplexityAnalyzer()
        self._health_checker = HealthChecker()
        self._init_default_endpoints()

    def _init_default_endpoints(self) -> None:
        """Initialize default model endpoints."""
        defaults = [
            ModelEndpoint(
                endpoint_id="openai-gpt4o",
                provider="openai",
                model_name="gpt-4o",
                tier=ModelTier.PREMIUM,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                capabilities=["reasoning", "coding", "analysis", "creative"],
                rate_limit_rpm=500,
            ),
            ModelEndpoint(
                endpoint_id="openai-gpt4o-mini",
                provider="openai",
                model_name="gpt-4o-mini",
                tier=ModelTier.STANDARD,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                capabilities=["chat", "summarization", "classification"],
                rate_limit_rpm=3000,
            ),
            ModelEndpoint(
                endpoint_id="openai-o1",
                provider="openai",
                model_name="o1",
                tier=ModelTier.SPECIALIZED,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.06,
                capabilities=["deep_reasoning", "math", "science", "coding"],
                rate_limit_rpm=100,
            ),
            ModelEndpoint(
                endpoint_id="openai-o3-mini",
                provider="openai",
                model_name="o3-mini",
                tier=ModelTier.ADVANCED,
                cost_per_1k_input=0.0011,
                cost_per_1k_output=0.0044,
                capabilities=["reasoning", "coding", "math"],
                rate_limit_rpm=200,
            ),
            ModelEndpoint(
                endpoint_id="anthropic-claude-sonnet",
                provider="anthropic",
                model_name="claude-sonnet-4-20250514",
                tier=ModelTier.PREMIUM,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                capabilities=["reasoning", "coding", "analysis", "creative"],
                rate_limit_rpm=400,
            ),
            ModelEndpoint(
                endpoint_id="anthropic-claude-haiku",
                provider="anthropic",
                model_name="claude-haiku-3-5",
                tier=ModelTier.LIGHTWEIGHT,
                cost_per_1k_input=0.0008,
                cost_per_1k_output=0.004,
                capabilities=["chat", "summarization", "quick_tasks"],
                rate_limit_rpm=1000,
            ),
        ]

        for ep in defaults:
            self.register_endpoint(ep)

    def register_endpoint(self, endpoint: ModelEndpoint) -> None:
        """Register a model endpoint."""
        self._endpoints[endpoint.endpoint_id] = endpoint
        logger.info(
            "Registered endpoint %s: %s/%s (tier=%s)",
            endpoint.endpoint_id, endpoint.provider,
            endpoint.model_name, endpoint.tier.value,
        )

    def remove_endpoint(self, endpoint_id: str) -> bool:
        """Remove a model endpoint."""
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            return True
        return False

    # ── Routing ──

    def route(
        self,
        prompt: str,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        required_capabilities: list[str] | None = None,
        max_cost: float | None = None,
        preferred_tier: ModelTier | None = None,
    ) -> RoutingDecision:
        """
        Route a request to the optimal model endpoint.
        
        Args:
            prompt: The user prompt to analyze
            strategy: Routing strategy to use
            required_capabilities: Required model capabilities
            max_cost: Maximum acceptable cost
            preferred_tier: Preferred model tier
            
        Returns:
            RoutingDecision with selected endpoint and fallbacks
        """
        # Analyze task complexity
        complexity = self._complexity_analyzer.analyze(prompt)

        # Filter available endpoints
        candidates = self._filter_candidates(
            complexity=complexity,
            required_capabilities=required_capabilities,
            max_cost=max_cost,
            preferred_tier=preferred_tier,
        )

        if not candidates:
            # Fallback to any healthy endpoint
            candidates = [
                ep for ep in self._endpoints.values()
                if ep.health != ProviderHealth.UNHEALTHY
            ]

        if not candidates:
            # Last resort: use any endpoint
            candidates = list(self._endpoints.values())

        # Select best endpoint based on strategy
        selected, fallbacks = self._select_endpoint(candidates, strategy, complexity)

        decision = RoutingDecision(
            decision_id=str(uuid.uuid4())[:8],
            endpoint=selected,
            strategy=strategy,
            complexity=complexity,
            reason=self._generate_routing_reason(selected, complexity, strategy),
            estimated_cost=self._estimate_cost(selected, prompt),
            fallback_endpoints=fallbacks,
        )

        self._decisions[decision.decision_id] = decision
        self._stats.strategy_usage[strategy.value] = (
            self._stats.strategy_usage.get(strategy.value, 0) + 1
        )
        self._stats.complexity_distribution[complexity.value] = (
            self._stats.complexity_distribution.get(complexity.value, 0) + 1
        )

        return decision

    def _filter_candidates(
        self,
        complexity: TaskComplexity,
        required_capabilities: list[str] | None = None,
        max_cost: float | None = None,
        preferred_tier: ModelTier | None = None,
    ) -> list[ModelEndpoint]:
        """Filter endpoints based on criteria."""
        candidates = []

        # Tier requirements based on complexity
        tier_requirements = {
            TaskComplexity.TRIVIAL: [ModelTier.LIGHTWEIGHT, ModelTier.STANDARD],
            TaskComplexity.SIMPLE: [ModelTier.LIGHTWEIGHT, ModelTier.STANDARD, ModelTier.ADVANCED],
            TaskComplexity.MODERATE: [ModelTier.STANDARD, ModelTier.ADVANCED, ModelTier.PREMIUM],
            TaskComplexity.COMPLEX: [ModelTier.ADVANCED, ModelTier.PREMIUM, ModelTier.SPECIALIZED],
            TaskComplexity.EXPERT: [ModelTier.PREMIUM, ModelTier.SPECIALIZED],
        }

        allowed_tiers = tier_requirements.get(complexity, [])
        if preferred_tier and preferred_tier in allowed_tiers:
            allowed_tiers = [preferred_tier] + [t for t in allowed_tiers if t != preferred_tier]

        for ep in self._endpoints.values():
            # Health check
            if ep.health == ProviderHealth.UNHEALTHY:
                continue

            # Tier check
            if ep.tier not in allowed_tiers:
                continue

            # Capability check
            if required_capabilities:
                if not all(c in ep.capabilities for c in required_capabilities):
                    continue

            # Cost check
            if max_cost is not None and ep.cost_per_1k_input > max_cost:
                continue

            # Rate limit check
            if ep.current_rpm >= ep.rate_limit_rpm:
                continue

            candidates.append(ep)

        return candidates

    def _select_endpoint(
        self,
        candidates: list[ModelEndpoint],
        strategy: RoutingStrategy,
        complexity: TaskComplexity,
    ) -> tuple[ModelEndpoint, list[ModelEndpoint]]:
        """Select the best endpoint based on strategy."""
        if not candidates:
            raise ValueError("No candidates available for routing")

        if strategy == RoutingStrategy.COST_OPTIMIZED:
            candidates.sort(key=lambda e: e.cost_per_1k_input + e.cost_per_1k_output)
        elif strategy == RoutingStrategy.PERFORMANCE:
            candidates.sort(key=lambda e: e.avg_latency_ms if e.avg_latency_ms > 0 else 99999)
        elif strategy == RoutingStrategy.LATENCY_SENSITIVE:
            candidates.sort(key=lambda e: e.avg_latency_ms if e.avg_latency_ms > 0 else 99999)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            candidates.sort(key=lambda e: e.last_used or datetime.min)
        elif strategy == RoutingStrategy.BALANCED:
            candidates.sort(key=lambda e: (
                (e.cost_per_1k_input + e.cost_per_1k_output) * (1.0 - e.success_rate + 0.1)
            ))
        elif strategy == RoutingStrategy.ENSEMBLE:
            candidates.sort(key=lambda e: e.success_rate, reverse=True)
        elif strategy == RoutingStrategy.FALLBACK_CHAIN:
            candidates.sort(key=lambda e: e.success_rate, reverse=True)

        selected = candidates[0]
        fallbacks = candidates[1:4] if len(candidates) > 1 else []

        selected.last_used = datetime.now(timezone.utc)
        selected.current_rpm += 1

        return selected, fallbacks

    def _generate_routing_reason(
        self,
        endpoint: ModelEndpoint,
        complexity: TaskComplexity,
        strategy: RoutingStrategy,
    ) -> str:
        """Generate a human-readable routing reason."""
        return (
            f"Routed {complexity.value} task to {endpoint.provider}/{endpoint.model_name} "
            f"({endpoint.tier.value} tier) using {strategy.value} strategy"
        )

    def _estimate_cost(self, endpoint: ModelEndpoint, prompt: str) -> float:
        """Estimate cost for a prompt."""
        estimated_input_tokens = len(prompt) // 4
        estimated_output_tokens = min(estimated_input_tokens, endpoint.max_tokens)
        return round(
            (estimated_input_tokens / 1000) * endpoint.cost_per_1k_input +
            (estimated_output_tokens / 1000) * endpoint.cost_per_1k_output,
            6,
        )

    # ── Execution ──

    def record_execution(
        self,
        decision_id: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        error: str = "",
    ) -> ModelExecution:
        """Record a model execution result."""
        decision = self._decisions.get(decision_id)
        endpoint = decision.endpoint if decision else None

        if not endpoint:
            return ModelExecution(
                execution_id=str(uuid.uuid4())[:8],
                endpoint_id="unknown",
                model_name="unknown",
                provider="unknown",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost=0.0,
                success=success,
                error=error,
            )

        execution = ModelExecution(
            execution_id=str(uuid.uuid4())[:8],
            endpoint_id=endpoint.endpoint_id,
            model_name=endpoint.model_name,
            provider=endpoint.provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost=round(
                (input_tokens / 1000) * endpoint.cost_per_1k_input +
                (output_tokens / 1000) * endpoint.cost_per_1k_output,
                6,
            ),
            success=success,
            error=error,
            decision_id=decision_id,
            completed_at=datetime.now(timezone.utc),
        )

        # Update endpoint metrics
        self._update_endpoint_metrics(endpoint, execution)

        self._executions.append(execution)
        self._update_execution_stats(execution)

        return execution

    def _update_endpoint_metrics(
        self, endpoint: ModelEndpoint, execution: ModelExecution
    ) -> None:
        """Update endpoint performance metrics."""
        # Update average latency
        if endpoint.avg_latency_ms == 0:
            endpoint.avg_latency_ms = execution.latency_ms
        else:
            endpoint.avg_latency_ms = (
                endpoint.avg_latency_ms * 0.9 + execution.latency_ms * 0.1
            )

        # Update success rate
        total = endpoint.failure_count + (self._stats.endpoint_usage.get(endpoint.endpoint_id, 0) + 1)
        successes = (self._stats.endpoint_usage.get(endpoint.endpoint_id, 0) + 1) - endpoint.failure_count
        endpoint.success_rate = successes / max(1, total)

        if execution.success:
            endpoint.consecutive_failures = 0
        else:
            endpoint.failure_count += 1
            endpoint.consecutive_failures += 1

        # Health check
        if endpoint.consecutive_failures >= 3:
            endpoint.health = ProviderHealth.UNHEALTHY
        elif endpoint.consecutive_failures >= 1:
            endpoint.health = ProviderHealth.DEGRADED
        else:
            endpoint.health = ProviderHealth.HEALTHY

    # ── Ensemble ──

    def ensemble_route(
        self,
        prompt: str,
        method: EnsembleMethod = EnsembleMethod.MAJORITY_VOTE,
        num_models: int = 3,
        required_capabilities: list[str] | None = None,
    ) -> list[RoutingDecision]:
        """
        Route to multiple models for ensemble decision-making.
        
        Returns multiple routing decisions for ensemble execution.
        """
        decisions = []
        used_endpoints: set[str] = set()

        for _ in range(num_models):
            candidates = self._filter_candidates(
                complexity=TaskComplexity.COMPLEX,
                required_capabilities=required_capabilities,
            )
            # Filter out already selected endpoints
            candidates = [c for c in candidates if c.endpoint_id not in used_endpoints]

            if not candidates:
                break

            selected, _ = self._select_endpoint(
                candidates, RoutingStrategy.PERFORMANCE, TaskComplexity.COMPLEX
            )

            decision = RoutingDecision(
                decision_id=str(uuid.uuid4())[:8],
                endpoint=selected,
                strategy=RoutingStrategy.ENSEMBLE,
                complexity=TaskComplexity.COMPLEX,
                reason=f"Ensemble member {len(decisions) + 1}/{num_models}: {selected.model_name}",
                estimated_cost=self._estimate_cost(selected, prompt),
            )
            decisions.append(decision)
            used_endpoints.add(selected.endpoint_id)
            self._decisions[decision.decision_id] = decision

        return decisions

    # ── Health Monitoring ──

    def check_health(self) -> dict[str, ProviderHealth]:
        """Check health of all endpoints."""
        statuses = {}
        for ep_id, ep in self._endpoints.items():
            if ep.consecutive_failures >= 3:
                ep.health = ProviderHealth.UNHEALTHY
            statuses[ep_id] = ep.health
        return statuses

    def get_healthy_endpoints(self) -> list[ModelEndpoint]:
        """Get all healthy endpoints."""
        return [
            ep for ep in self._endpoints.values()
            if ep.health == ProviderHealth.HEALTHY
        ]

    # ── Statistics ──

    def _update_execution_stats(self, execution: ModelExecution) -> None:
        """Update conductor statistics."""
        self._stats.total_requests += 1
        if execution.success:
            self._stats.total_successful += 1
        else:
            self._stats.total_failed += 1

        self._stats.total_tokens += execution.input_tokens + execution.output_tokens
        self._stats.total_cost += execution.cost

        n = self._stats.total_requests
        self._stats.avg_latency_ms = (
            (self._stats.avg_latency_ms * (n - 1) + execution.latency_ms) / n
        )

        self._stats.endpoint_usage[execution.endpoint_id] = (
            self._stats.endpoint_usage.get(execution.endpoint_id, 0) + 1
        )

    def get_stats(self) -> ConductorStats:
        """Get current conductor statistics."""
        return self._stats

    def get_endpoints(self) -> list[ModelEndpoint]:
        """Get all registered endpoints."""
        return list(self._endpoints.values())

    def get_executions(self, limit: int = 100) -> list[ModelExecution]:
        """Get recent executions."""
        return self._executions[-limit:]

    def reset(self) -> None:
        """Reset the conductor."""
        self._executions.clear()
        self._decisions.clear()
        self._stats = ConductorStats()
        self._init_default_endpoints()
        logger.info("Multi-model conductor reset")


# ═══════════════════════════════════════════════════════════
# Complexity Analyzer
# ═══════════════════════════════════════════════════════════

class ComplexityAnalyzer:
    """Analyzes task complexity for model routing."""

    def analyze(self, prompt: str) -> TaskComplexity:
        """Analyze the complexity of a task from its prompt."""
        score = 0.0
        prompt_lower = prompt.lower()

        # Length-based scoring
        if len(prompt) > 2000:
            score += 2.0
        elif len(prompt) > 1000:
            score += 1.5
        elif len(prompt) > 500:
            score += 1.0
        elif len(prompt) > 100:
            score += 0.5

        # Keyword-based scoring
        complex_keywords = {
            "analyze": 1.0, "evaluate": 1.0, "compare": 0.8,
            "design": 1.5, "architect": 1.5, "implement": 1.0,
            "debug": 1.0, "optimize": 1.2, "refactor": 1.0,
            "explain": 0.5, "reason": 0.8, "solve": 1.0,
            "create": 0.8, "build": 0.8, "develop": 1.0,
            "mathematical": 1.5, "proof": 1.5, "algorithm": 1.5,
            "research": 1.2, "investigate": 1.0,
            "translate": 0.5, "summarize": 0.3, "classify": 0.3,
        }

        for keyword, weight in complex_keywords.items():
            if keyword in prompt_lower:
                score += weight

        # Multi-step detection
        if any(sep in prompt for sep in ["\n\n", "\n- ", "\n1.", "\n2.", "\n3."]):
            score += 0.5

        # Code-related
        if any(kw in prompt_lower for kw in ["code", "function", "class", "bug", "error"]):
            score += 0.5

        # Determine complexity level
        if score >= 4.0:
            return TaskComplexity.EXPERT
        if score >= 2.5:
            return TaskComplexity.COMPLEX
        if score >= 1.5:
            return TaskComplexity.MODERATE
        if score >= 0.5:
            return TaskComplexity.SIMPLE
        return TaskComplexity.TRIVIAL


# ═══════════════════════════════════════════════════════════
# Health Checker
# ═══════════════════════════════════════════════════════════

class HealthChecker:
    """Monitors endpoint health and performance."""

    def __init__(self):
        self._check_history: dict[str, list[tuple[datetime, bool]]] = defaultdict(list)

    def record_check(self, endpoint_id: str, healthy: bool) -> None:
        """Record a health check result."""
        self._check_history[endpoint_id].append((datetime.now(timezone.utc), healthy))
        # Keep only last 100 checks
        if len(self._check_history[endpoint_id]) > 100:
            self._check_history[endpoint_id] = self._check_history[endpoint_id][-100:]

    def get_health_score(self, endpoint_id: str) -> float:
        """Calculate health score from recent checks."""
        history = self._check_history.get(endpoint_id, [])
        if not history:
            return 1.0

        recent = history[-20:]
        healthy_count = sum(1 for _, h in recent if h)
        return healthy_count / len(recent)


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@dataclass
class ConductorConfig:
    """Configuration for the multi-model conductor."""
    default_strategy: RoutingStrategy = RoutingStrategy.BALANCED
    max_fallback_attempts: int = 3
    health_check_interval_seconds: int = 60
    max_consecutive_failures: int = 3
    latency_sla_ms: int = 5000
    cost_budget_daily: float = 10.0
    ensemble_default_count: int = 3
    collect_metrics: bool = True
    auto_health_check: bool = True


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_multi_model_conductor: MultiModelConductor | None = None


def get_multi_model_conductor() -> MultiModelConductor:
    """Get or create the singleton multi-model conductor."""
    global _multi_model_conductor
    if _multi_model_conductor is None:
        _multi_model_conductor = MultiModelConductor()
    return _multi_model_conductor


def reset_multi_model_conductor() -> None:
    """Reset the singleton multi-model conductor."""
    global _multi_model_conductor
    if _multi_model_conductor:
        _multi_model_conductor.reset()
    _multi_model_conductor = None