"""Buddy Provider Abstraction Layer

Unified interface for multiple LLM providers with automatic failover,
cost tracking, and capability detection. Supports OpenAI, Anthropic,
Gemini, Azure, and OpenAI-compatible endpoints.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger("buddy.providers")


class ProviderKind(str, Enum):
    """Supported LLM provider backends."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    AZURE = "azure"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


class ProviderCapability(str, Enum):
    """Capabilities a provider may support."""
    CHAT = "chat"
    VISION = "vision"
    TOOLS = "tools"
    STREAMING = "streaming"
    FUNCTION_CALLING = "function_calling"
    JSON_MODE = "json_mode"
    EMBEDDING = "embedding"
    REASONING = "reasoning"


@dataclass
class ProviderModel:
    """Information about a model available from a provider."""
    id: str
    provider: ProviderKind
    capabilities: list[ProviderCapability] = field(default_factory=list)
    max_tokens: int = 4096
    max_input_tokens: int = 128000
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    is_default: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class ProviderConfig:
    """Configuration for a specific provider."""
    kind: ProviderKind
    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    models: list[ProviderModel] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0  # Lower = higher priority


@dataclass
class ProviderResponse:
    """Standardized response from any provider."""
    content: str
    model: str
    provider: ProviderKind
    tokens_input: int = 0
    tokens_output: int = 0
    finish_reason: str = "stop"
    tool_calls: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    cost: float = 0.0


# ── Model Registry ──────────────────────────────────────────

# Well-known model definitions with accurate capabilities and pricing
MODEL_REGISTRY: dict[str, ProviderModel] = {
    # OpenAI models
    "gpt-4o": ProviderModel(
        id="gpt-4o", provider=ProviderKind.OPENAI,
        capabilities=[ProviderCapability.CHAT, ProviderCapability.VISION,
                      ProviderCapability.TOOLS, ProviderCapability.STREAMING,
                      ProviderCapability.FUNCTION_CALLING, ProviderCapability.JSON_MODE],
        max_tokens=16384, max_input_tokens=128000,
        cost_per_1k_input=0.0025, cost_per_1k_output=0.01,
    ),
    "gpt-4o-mini": ProviderModel(
        id="gpt-4o-mini", provider=ProviderKind.OPENAI,
        capabilities=[ProviderCapability.CHAT, ProviderCapability.VISION,
                      ProviderCapability.TOOLS, ProviderCapability.STREAMING,
                      ProviderCapability.FUNCTION_CALLING, ProviderCapability.JSON_MODE],
        max_tokens=16384, max_input_tokens=128000,
        cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
        is_default=True,
    ),
    "gpt-4.1": ProviderModel(
        id="gpt-4.1", provider=ProviderKind.OPENAI,
        capabilities=[ProviderCapability.CHAT, ProviderCapability.VISION,
                      ProviderCapability.TOOLS, ProviderCapability.STREAMING,
                      ProviderCapability.FUNCTION_CALLING, ProviderCapability.JSON_MODE],
        max_tokens=32768, max_input_tokens=1047576,
        cost_per_1k_input=0.002, cost_per_1k_output=0.008,
    ),
    "o4-mini": ProviderModel(
        id="o4-mini", provider=ProviderKind.OPENAI,
        capabilities=[ProviderCapability.CHAT, ProviderCapability.STREAMING,
                      ProviderCapability.REASONING],
        max_tokens=100000, max_input_tokens=200000,
        cost_per_1k_input=0.0011, cost_per_1k_output=0.0044,
    ),
    # Anthropic models
    "claude-sonnet-4-20250514": ProviderModel(
        id="claude-sonnet-4-20250514", provider=ProviderKind.ANTHROPIC,
        capabilities=[ProviderCapability.CHAT, ProviderCapability.VISION,
                      ProviderCapability.TOOLS, ProviderCapability.STREAMING,
                      ProviderCapability.FUNCTION_CALLING, ProviderCapability.JSON_MODE,
                      ProviderCapability.REASONING],
        max_tokens=64000, max_input_tokens=200000,
        cost_per_1k_input=0.003, cost_per_1k_output=0.015,
    ),
    "claude-3.5-haiku-20241022": ProviderModel(
        id="claude-3.5-haiku-20241022", provider=ProviderKind.ANTHROPIC,
        capabilities=[ProviderCapability.CHAT, ProviderCapability.TOOLS,
                      ProviderCapability.STREAMING, ProviderCapability.FUNCTION_CALLING],
        max_tokens=8192, max_input_tokens=200000,
        cost_per_1k_input=0.0008, cost_per_1k_output=0.004,
    ),
    # Gemini models
    "gemini-2.5-flash": ProviderModel(
        id="gemini-2.5-flash", provider=ProviderKind.GEMINI,
        capabilities=[ProviderCapability.CHAT, ProviderCapability.VISION,
                      ProviderCapability.TOOLS, ProviderCapability.STREAMING,
                      ProviderCapability.FUNCTION_CALLING, ProviderCapability.JSON_MODE],
        max_tokens=8192, max_input_tokens=1048576,
        cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
    ),
    "gemini-2.5-pro": ProviderModel(
        id="gemini-2.5-pro", provider=ProviderKind.GEMINI,
        capabilities=[ProviderCapability.CHAT, ProviderCapability.VISION,
                      ProviderCapability.TOOLS, ProviderCapability.STREAMING,
                      ProviderCapability.FUNCTION_CALLING, ProviderCapability.JSON_MODE,
                      ProviderCapability.REASONING],
        max_tokens=65536, max_input_tokens=1048576,
        cost_per_1k_input=0.00125, cost_per_1k_output=0.01,
    ),
}


class ProviderHub:
    """Central hub for managing multiple LLM providers.

    Handles provider registration, health checking, model discovery,
    automatic failover, and cost estimation.
    """

    def __init__(self):
        self._providers: dict[ProviderKind, ProviderConfig] = {}
        self._clients: dict[ProviderKind, AsyncOpenAI] = {}
        self._health: dict[ProviderKind, bool] = {}
        self._failover_counts: dict[ProviderKind, int] = {}
        self._total_requests: dict[ProviderKind, int] = {}
        self._total_tokens: dict[ProviderKind, int] = {}
        self._total_cost: dict[ProviderKind, float] = {}

        # Auto-register OpenAI from settings
        if settings.OPENAI_API_KEY:
            self.register(
                ProviderConfig(
                    kind=ProviderKind.OPENAI,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    default_model=settings.LLM_MODEL,
                )
            )

    def register(self, config: ProviderConfig) -> None:
        """Register a provider with its configuration."""
        if not config.api_key:
            logger.warning(f"Provider {config.kind.value} registered without API key")
            return

        self._providers[config.kind] = config
        self._health[config.kind] = True
        self._failover_counts[config.kind] = 0
        self._total_requests[config.kind] = 0
        self._total_tokens[config.kind] = 0
        self._total_cost[config.kind] = 0.0

        # Create OpenAI-compatible client (most providers support this)
        if config.kind == ProviderKind.ANTHROPIC:
            base = config.base_url or "https://api.anthropic.com/v1"
        elif config.kind == ProviderKind.GEMINI:
            base = config.base_url or "https://generativelanguage.googleapis.com/v1beta/openai"
        elif config.kind == ProviderKind.OPENROUTER:
            base = config.base_url or "https://openrouter.ai/api/v1"
        else:
            base = config.base_url or "https://api.openai.com/v1"

        self._clients[config.kind] = AsyncOpenAI(
            api_key=config.api_key,
            base_url=base,
        )

        logger.info(f"Provider registered: {config.kind.value} (default model: {config.default_model or 'auto'})")

    def unregister(self, kind: ProviderKind) -> None:
        """Remove a provider."""
        self._providers.pop(kind, None)
        self._clients.pop(kind, None)
        self._health.pop(kind, None)
        logger.info(f"Provider unregistered: {kind.value}")

    def get_client(self, kind: ProviderKind | None = None) -> AsyncOpenAI | None:
        """Get the OpenAI-compatible client for a provider."""
        if kind and kind in self._clients:
            return self._clients[kind]

        # Return first available healthy client
        for pk, client in self._clients.items():
            if self._health.get(pk, False):
                return client
        return None

    def get_model_info(self, model_id: str) -> ProviderModel | None:
        """Look up model information from the registry."""
        return MODEL_REGISTRY.get(model_id)

    def estimate_cost(
        self, model_id: str, tokens_input: int, tokens_output: int
    ) -> float:
        """Estimate the cost of a request based on token counts."""
        info = self.get_model_info(model_id)
        if not info:
            return 0.0

        input_cost = (tokens_input / 1000) * info.cost_per_1k_input
        output_cost = (tokens_output / 1000) * info.cost_per_1k_output
        return round(input_cost + output_cost, 6)

    def get_available_models(self) -> list[ProviderModel]:
        """Get all models available across registered providers."""
        models = []
        for config in self._providers.values():
            if config.models:
                models.extend(config.models)
            else:
                # Default to known models for this provider
                for model in MODEL_REGISTRY.values():
                    if model.provider == config.kind:
                        models.append(model)
        return models

    def resolve_model(self, preferred: str | None = None) -> tuple[ProviderKind, str]:
        """Resolve which provider and model to use.

        Priority: explicit preference > settings default > first available model.
        """
        if preferred:
            info = self.get_model_info(preferred)
            if info and info.provider in self._providers and self._health.get(info.provider, False):
                return info.provider, preferred

        # Use settings default
        default_model = settings.LLM_MODEL
        default_info = self.get_model_info(default_model)
        if default_info and default_info.provider in self._providers:
            return default_info.provider, default_model

        # Fallback to first available
        for pk, config in self._providers.items():
            if self._health.get(pk, False) and config.default_model:
                return pk, config.default_model

        raise RuntimeError("No healthy providers available")

    def record_usage(
        self, kind: ProviderKind, tokens_input: int, tokens_output: int, cost: float
    ) -> None:
        """Record token usage and cost for analytics."""
        self._total_requests[kind] = self._total_requests.get(kind, 0) + 1
        self._total_tokens[kind] = self._total_tokens.get(kind, 0) + tokens_input + tokens_output
        self._total_cost[kind] = self._total_cost.get(kind, 0) + cost

    def mark_unhealthy(self, kind: ProviderKind) -> None:
        """Mark a provider as unhealthy after a failure."""
        self._health[kind] = False
        self._failover_counts[kind] = self._failover_counts.get(kind, 0) + 1
        logger.warning(f"Provider {kind.value} marked unhealthy (failover count: {self._failover_counts[kind]})")

    def mark_healthy(self, kind: ProviderKind) -> None:
        """Restore a provider to healthy status."""
        self._health[kind] = True
        logger.info(f"Provider {kind.value} restored to healthy")

    async def health_check(self, kind: ProviderKind) -> bool:
        """Check if a provider is responsive."""
        if kind not in self._clients:
            return False

        try:
            client = self._clients[kind]
            # Quick model list call to verify connectivity
            await asyncio.wait_for(client.models.list(), timeout=5.0)
            self.mark_healthy(kind)
            return True
        except Exception:
            self.mark_unhealthy(kind)
            return False

    async def health_check_all(self) -> dict[ProviderKind, bool]:
        """Check health of all registered providers."""
        results = {}
        for kind in self._providers:
            results[kind] = await self.health_check(kind)
        return results

    def get_stats(self) -> dict:
        """Get comprehensive provider statistics."""
        return {
            "providers": {
                pk.value: {
                    "healthy": self._health.get(pk, False),
                    "total_requests": self._total_requests.get(pk, 0),
                    "total_tokens": self._total_tokens.get(pk, 0),
                    "total_cost": round(self._total_cost.get(pk, 0.0), 6),
                    "failover_count": self._failover_counts.get(pk, 0),
                }
                for pk in self._providers
            },
            "total_providers": len(self._providers),
            "healthy_providers": sum(1 for v in self._health.values() if v),
            "models_available": len(self.get_available_models()),
        }


# Global singleton
provider_hub = ProviderHub()