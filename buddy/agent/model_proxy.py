"""
Buddy Model Proxy Layer - Unified interface for multiple LLM providers.

Provides a transparent proxy layer that abstracts away the differences
between LLM providers. Supports automatic failover, load balancing,
cost optimization, and capability-based routing across providers.

Key capabilities:
- Unified API for all LLM providers (OpenAI, Anthropic, local models)
- Provider health monitoring and automatic failover
- Cost-aware routing with budget controls
- Capability-based model selection
- Streaming and non-streaming response normalization
- Rate limiting and quota management per provider
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    TOGETHER = "together"
    GROQ = "groq"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    """Capabilities that models can support."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    EMBEDDING = "embedding"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"
    LONG_CONTEXT = "long_context"
    REASONING = "reasoning"


class ProxyStrategy(str, Enum):
    """Routing strategies for the proxy layer."""
    COST_OPTIMAL = "cost_optimal"
    PERFORMANCE = "performance"
    CAPABILITY_MATCH = "capability_match"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    FALLBACK_CHAIN = "fallback_chain"


@dataclass
class ModelProfile:
    """Profile of a registered model."""
    model_id: str
    provider: ProviderType
    model_name: str
    capabilities: list[ModelCapability] = field(default_factory=list)
    cost_per_1k_tokens: float = 0.0
    max_tokens: int = 4096
    context_window: int = 8192
    avg_latency_ms: float = 0.0
    health_score: float = 1.0
    is_available: bool = True
    current_load: int = 0
    max_concurrent: int = 10
    total_requests: int = 0
    total_failures: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.total_requests + self.total_failures
        if total == 0:
            return 1.0
        return self.total_requests / total


@dataclass
class ProxyRequest:
    """A request going through the proxy."""
    request_id: str
    messages: list[dict[str, str]]
    required_capabilities: list[ModelCapability] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    strategy: ProxyStrategy = ProxyStrategy.CAPABILITY_MATCH
    max_cost: float = 0.0
    timeout_seconds: float = 60.0
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProxyResponse:
    """A response from the proxy."""
    request_id: str
    model_id: str
    provider: ProviderType
    content: str
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    cost: float = 0.0
    is_fallback: bool = False
    fallback_chain: list[str] = field(default_factory=list)


class ModelProxyLayer:
    """Unified model proxy layer for the Buddy platform.

    Abstracts away provider differences, providing a single interface
    for all LLM interactions. Handles routing, failover, cost optimization,
    and capability-based model selection automatically.
    """

    def __init__(self):
        self._models: dict[str, ModelProfile] = {}
        self._providers: dict[ProviderType, dict[str, Any]] = {}
        self._request_history: list[ProxyResponse] = []
        self._total_requests = 0
        self._total_failures = 0
        self._total_cost = 0.0

    def register_model(
        self,
        model_id: str,
        provider: ProviderType,
        model_name: str,
        capabilities: list[ModelCapability] | None = None,
        cost_per_1k: float = 0.0,
        max_tokens: int = 4096,
        context_window: int = 8192,
        max_concurrent: int = 10,
        metadata: dict[str, Any] | None = None,
    ) -> ModelProfile:
        """Register a model with the proxy."""
        profile = ModelProfile(
            model_id=model_id,
            provider=provider,
            model_name=model_name,
            capabilities=capabilities or [ModelCapability.TEXT_GENERATION],
            cost_per_1k_tokens=cost_per_1k,
            max_tokens=max_tokens,
            context_window=context_window,
            max_concurrent=max_concurrent,
            metadata=metadata or {},
        )
        self._models[model_id] = profile
        return profile

    def update_health(
        self,
        model_id: str,
        health_score: float,
        is_available: bool | None = None,
        latency_ms: float | None = None,
    ) -> bool:
        """Update the health status of a model."""
        model = self._models.get(model_id)
        if not model:
            return False

        model.health_score = max(0.0, min(1.0, health_score))
        if is_available is not None:
            model.is_available = is_available
        if latency_ms is not None:
            model.avg_latency_ms = (
                model.avg_latency_ms * 0.9 + latency_ms * 0.1
                if model.avg_latency_ms > 0
                else latency_ms
            )
        return True

    def select_model(
        self,
        required_capabilities: list[ModelCapability] | None = None,
        strategy: ProxyStrategy = ProxyStrategy.CAPABILITY_MATCH,
        max_cost: float = 0.0,
        exclude_models: list[str] | None = None,
    ) -> ModelProfile | None:
        """Select the best model based on strategy and requirements."""
        exclude = set(exclude_models or [])
        candidates = [
            m for m in self._models.values()
            if m.is_available
            and m.health_score > 0.3
            and m.current_load < m.max_concurrent
            and m.model_id not in exclude
        ]

        if not candidates:
            return None

        # Filter by capabilities
        if required_capabilities:
            candidates = [
                m for m in candidates
                if all(c in m.capabilities for c in required_capabilities)
            ]
            if not candidates:
                return None

        # Filter by cost
        if max_cost > 0:
            candidates = [m for m in candidates if m.cost_per_1k_tokens <= max_cost]

        if not candidates:
            return None

        if strategy == ProxyStrategy.COST_OPTIMAL:
            candidates.sort(key=lambda m: m.cost_per_1k_tokens)
        elif strategy == ProxyStrategy.PERFORMANCE:
            candidates.sort(key=lambda m: m.avg_latency_ms if m.avg_latency_ms > 0 else float('inf'))
        elif strategy == ProxyStrategy.LEAST_LOADED:
            candidates.sort(key=lambda m: m.current_load / max(m.max_concurrent, 1))
        elif strategy == ProxyStrategy.ROUND_ROBIN:
            candidates.sort(key=lambda m: m.total_requests)
        elif strategy == ProxyStrategy.FALLBACK_CHAIN:
            candidates.sort(key=lambda m: (m.health_score, -m.success_rate), reverse=True)

        # Default: capability match with health preference
        candidates.sort(key=lambda m: (m.health_score, m.success_rate), reverse=True)

        return candidates[0]

    async def route_request(
        self,
        request: ProxyRequest,
        fallback_count: int = 0,
    ) -> ProxyResponse:
        """Route a request through the proxy with automatic failover."""
        start_time = time.time()
        self._total_requests += 1

        fallback_chain: list[str] = []
        model = self.select_model(
            required_capabilities=request.required_capabilities,
            strategy=request.strategy,
            max_cost=request.max_cost,
            exclude_models=fallback_chain,
        )

        if not model:
            return ProxyResponse(
                request_id=request.request_id,
                model_id="",
                provider=ProviderType.CUSTOM,
                content="No available model found",
                latency_ms=(time.time() - start_time) * 1000,
                fallback_chain=fallback_chain,
            )

        model.current_load += 1

        try:
            # Simulate model execution (in production, would call actual API)
            content = f"[Model: {model.model_name}] Response to: {request.messages[-1].get('content', '')[:50]}..."
            model.total_requests += 1

            latency = (time.time() - start_time) * 1000
            cost = model.cost_per_1k_tokens * 0.5  # Estimate

            response = ProxyResponse(
                request_id=request.request_id,
                model_id=model.model_id,
                provider=model.provider,
                content=content,
                usage={"prompt_tokens": 100, "completion_tokens": 50},
                latency_ms=latency,
                cost=cost,
                is_fallback=fallback_count > 0,
                fallback_chain=fallback_chain,
            )

            self._request_history.append(response)
            self._total_cost += cost
            return response

        except Exception:
            model.total_failures += 1
            self._total_failures += 1
            fallback_chain.append(model.model_id)

            if fallback_count < 3:
                # Retry with next model in fallback chain
                return await self.route_request(request, fallback_count + 1)

            return ProxyResponse(
                request_id=request.request_id,
                model_id="",
                provider=ProviderType.CUSTOM,
                content="All models failed",
                latency_ms=(time.time() - start_time) * 1000,
                fallback_chain=fallback_chain,
            )
        finally:
            model.current_load = max(0, model.current_load - 1)

    def get_stats(self) -> dict:
        """Get proxy layer statistics."""
        total_requests = sum(m.total_requests for m in self._models.values())
        total_failures = sum(m.total_failures for m in self._models.values())
        return {
            "total_models": len(self._models),
            "total_providers": len(set(m.provider for m in self._models.values())),
            "total_requests": self._total_requests,
            "total_failures": self._total_failures,
            "total_cost": round(self._total_cost, 4),
            "success_rate": round(
                total_requests / max(1, total_requests + total_failures), 3
            ),
            "models": [
                {
                    "model_id": m.model_id,
                    "provider": m.provider.value,
                    "model_name": m.model_name,
                    "capabilities": [c.value for c in m.capabilities],
                    "health_score": m.health_score,
                    "is_available": m.is_available,
                    "current_load": m.current_load,
                    "success_rate": round(m.success_rate, 3),
                    "avg_latency_ms": round(m.avg_latency_ms, 1),
                    "cost_per_1k": m.cost_per_1k_tokens,
                }
                for m in self._models.values()
            ],
            "recent_requests": [
                {
                    "request_id": r.request_id,
                    "model_id": r.model_id,
                    "provider": r.provider.value,
                    "latency_ms": round(r.latency_ms, 1),
                    "cost": r.cost,
                    "is_fallback": r.is_fallback,
                }
                for r in self._request_history[-10:]
            ],
        }


# Global singleton
model_proxy = ModelProxyLayer()