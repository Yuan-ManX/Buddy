"""
Buddy Model Orchestrator - Multi-Model Coordination

Orchestrates multiple language models for agent operations, providing
intelligent model selection, load balancing, fallback chains, and
cost-optimized routing across different providers.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    LOCAL = "local"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    """Capabilities of a model."""
    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    VISION = "vision"
    TOOL_USE = "tool_use"
    STREAMING = "streaming"
    LONG_CONTEXT = "long_context"
    FAST = "fast"


@dataclass
class ModelConfig:
    """Configuration for a model instance."""
    model_id: str
    provider: ModelProvider
    capabilities: list[ModelCapability] = field(default_factory=list)
    context_window: int = 128000
    max_output_tokens: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    base_url: str = ""
    api_key_env: str = ""
    priority: int = 0
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class ModelRequest:
    """A request to be processed by a model."""
    request_id: str
    messages: list[dict]
    model_id: str | None = None
    required_capabilities: list[ModelCapability] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    tools: list[dict] | None = None
    stream: bool = False
    timeout_sec: float = 60.0
    priority: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class ModelResponse:
    """Response from a model."""
    request_id: str
    model_id: str
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: float = 0
    cost: float = 0.0
    finish_reason: str = "stop"
    error: str | None = None
    success: bool = True

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "duration_ms": self.duration_ms,
            "cost": self.cost,
            "finish_reason": self.finish_reason,
            "error": self.error,
            "success": self.success,
        }


class ModelRouter:
    """Routes requests to the most appropriate model based on requirements."""

    def __init__(self):
        self._models: dict[str, ModelConfig] = {}
        self._default_model = ""

    def register_model(self, config: ModelConfig):
        """Register a model configuration."""
        self._models[config.model_id] = config
        if not self._default_model:
            self._default_model = config.model_id

    def set_default(self, model_id: str):
        """Set the default model."""
        self._default_model = model_id

    def select_model(
        self,
        required_capabilities: list[ModelCapability] | None = None,
        preferred_model: str | None = None,
    ) -> ModelConfig | None:
        """Select the best model for the given requirements."""
        if preferred_model and preferred_model in self._models:
            model = self._models[preferred_model]
            if model.enabled:
                return model

        # Filter by capabilities
        candidates = list(self._models.values())
        if required_capabilities:
            candidates = [
                m for m in candidates
                if all(cap in m.capabilities for cap in required_capabilities)
            ]

        # Sort by priority (lower is better)
        candidates.sort(key=lambda m: m.priority)

        if candidates:
            return candidates[0]
        return self._models.get(self._default_model)

    def list_models(self) -> list[dict]:
        return [
            {
                "model_id": m.model_id,
                "provider": m.provider.value,
                "capabilities": [c.value for c in m.capabilities],
                "context_window": m.context_window,
                "enabled": m.enabled,
            }
            for m in self._models.values()
        ]


class ModelOrchestrator:
    """Multi-model orchestration engine for Buddy.

    Coordinates multiple language models, providing intelligent routing,
    load balancing, fallback chains, cost tracking, and response streaming
    across different providers and model configurations.
    """

    def __init__(self):
        self.router = ModelRouter()
        self._total_requests = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._request_history: list[ModelResponse] = []
        self._register_default_models()

    def _register_default_models(self):
        """Register default model configurations."""
        self.router.register_model(ModelConfig(
            model_id="gpt-4o-mini",
            provider=ModelProvider.OPENAI,
            capabilities=[
                ModelCapability.CHAT, ModelCapability.CODE,
                ModelCapability.TOOL_USE, ModelCapability.STREAMING,
                ModelCapability.FAST,
            ],
            context_window=128000,
            max_output_tokens=16384,
            cost_per_1k_input=0.00015,
            cost_per_1k_output=0.0006,
            priority=0,
        ))

        self.router.register_model(ModelConfig(
            model_id="gpt-4o",
            provider=ModelProvider.OPENAI,
            capabilities=[
                ModelCapability.CHAT, ModelCapability.CODE,
                ModelCapability.REASONING, ModelCapability.VISION,
                ModelCapability.TOOL_USE, ModelCapability.STREAMING,
            ],
            context_window=128000,
            max_output_tokens=16384,
            cost_per_1k_input=0.0025,
            cost_per_1k_output=0.01,
            priority=1,
        ))

        self.router.register_model(ModelConfig(
            model_id="claude-sonnet-4-20250514",
            provider=ModelProvider.ANTHROPIC,
            capabilities=[
                ModelCapability.CHAT, ModelCapability.CODE,
                ModelCapability.REASONING, ModelCapability.TOOL_USE,
                ModelCapability.LONG_CONTEXT,
            ],
            context_window=200000,
            max_output_tokens=8192,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            priority=1,
        ))

        self.router.register_model(ModelConfig(
            model_id="local-model",
            provider=ModelProvider.LOCAL,
            capabilities=[ModelCapability.CHAT, ModelCapability.CODE],
            context_window=8192,
            max_output_tokens=4096,
            priority=2,
            enabled=False,
        ))

        self.router.set_default("gpt-4o-mini")

    async def process(
        self,
        request: ModelRequest,
        fallback_chain: list[str] | None = None,
    ) -> ModelResponse:
        """Process a request through the model orchestrator."""
        self._total_requests += 1
        start = time.time()

        # Select model
        model = self.router.select_model(
            required_capabilities=request.required_capabilities,
            preferred_model=request.model_id,
        )

        if not model:
            return ModelResponse(
                request_id=request.request_id,
                model_id="none",
                content="",
                error="No suitable model available",
                success=False,
            )

        # Simulate model processing (in production, this would call the actual API)
        response = await self._simulate_response(request, model)

        duration = (time.time() - start) * 1000
        response.duration_ms = duration
        response.cost = self._calculate_cost(response.tokens_input, response.tokens_output, model)

        self._total_tokens += response.tokens_input + response.tokens_output
        self._total_cost += response.cost
        self._request_history.append(response)

        # If failed and fallback chain exists, try next model
        if not response.success and fallback_chain:
            for fallback_id in fallback_chain:
                fallback_model = self.router.select_model(preferred_model=fallback_id)
                if fallback_model and fallback_model.model_id != model.model_id:
                    response = await self._simulate_response(request, fallback_model)
                    if response.success:
                        break

        return response

    async def process_stream(self, request: ModelRequest):
        """Process a request with streaming response."""
        model = self.router.select_model(
            required_capabilities=request.required_capabilities,
            preferred_model=request.model_id,
        )

        if not model:
            yield {"error": "No suitable model available"}
            return

        # Simulate streaming chunks
        simulated_content = f"[Simulated response from {model.model_id} for: {request.messages[-1].get('content', '')[:100]}]"
        words = simulated_content.split()
        for i, word in enumerate(words):
            yield {
                "model_id": model.model_id,
                "chunk": word + (" " if i < len(words) - 1 else ""),
                "index": i,
            }
            await asyncio.sleep(0.05)

    async def _simulate_response(self, request: ModelRequest, model: ModelConfig) -> ModelResponse:
        """Simulate a model response for testing."""
        last_message = request.messages[-1].get("content", "") if request.messages else ""

        return ModelResponse(
            request_id=request.request_id,
            model_id=model.model_id,
            content=f"[Simulated response from {model.model_id}] Processing your request. "
                    f"Configure {model.api_key_env or 'API key'} to enable real responses.",
            tool_calls=[],
            tokens_input=len(last_message) // 4,
            tokens_output=50,
            success=True,
        )

    def _calculate_cost(self, tokens_in: int, tokens_out: int, model: ModelConfig) -> float:
        """Calculate the cost of a request."""
        return (tokens_in / 1000 * model.cost_per_1k_input) + (tokens_out / 1000 * model.cost_per_1k_output)

    def get_stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "total_cost": round(self._total_cost, 6),
            "models": self.router.list_models(),
            "recent_requests": [r.to_dict() for r in self._request_history[-10:]],
        }


# Global model orchestrator instance
_model_orchestrator: ModelOrchestrator | None = None


def get_model_orchestrator() -> ModelOrchestrator:
    """Get or create the global model orchestrator."""
    global _model_orchestrator
    if _model_orchestrator is None:
        _model_orchestrator = ModelOrchestrator()
    return _model_orchestrator