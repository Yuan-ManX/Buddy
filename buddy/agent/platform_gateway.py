"""
Buddy Platform Gateway.

Provides a unified API gateway with provider catalog, intelligent routing,
load balancing, failover, and request transformation for the Buddy platform.
Orchestrates all AI model providers and service backends through a single
entry point.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Types of AI model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    GOOGLE = "google"
    LOCAL = "local"
    CUSTOM = "custom"
    MISTRAL = "mistral"
    COHERE = "cohere"
    DEEPSEEK = "deepseek"
    TOGETHER = "together"


class RoutingStrategy(Enum):
    """Strategies for routing requests to providers."""
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    COST_OPTIMIZED = "cost_optimized"
    CAPABILITY_MATCH = "capability_match"
    FALLBACK = "fallback"


class ProviderStatus(Enum):
    """Status of a provider."""
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"


@dataclass
class ProviderCapability:
    """A specific capability of a provider."""
    name: str
    supported: bool = True
    max_tokens: int = 4096
    max_context: int = 8192
    supports_streaming: bool = True
    supports_function_calling: bool = True
    supports_vision: bool = False
    supports_json_mode: bool = True
    cost_per_1k_tokens: float = 0.0


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""
    provider_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    provider_type: ProviderType = ProviderType.CUSTOM
    api_key: str = ""
    api_base: str = ""
    default_model: str = ""
    available_models: list[str] = field(default_factory=list)
    status: ProviderStatus = ProviderStatus.OFFLINE
    weight: float = 1.0
    max_concurrent: int = 10
    rate_limit_rpm: int = 60
    timeout: float = 30.0
    capabilities: list[ProviderCapability] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingRule:
    """A rule for routing requests to specific providers."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    condition: dict[str, Any] = field(default_factory=dict)
    target_providers: list[str] = field(default_factory=list)
    strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    priority: int = 5
    enabled: bool = True


@dataclass
class GatewayRequest:
    """A request to be routed through the gateway."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    model: str = ""
    messages: list[dict] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 1024
    stream: bool = False
    tools: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayResponse:
    """A response from the gateway."""
    request_id: str = ""
    provider_id: str = ""
    model: str = ""
    content: str = ""
    success: bool = False
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderCatalog:
    """
    Catalog of all available AI model providers.

    Manages provider registration, discovery, and capability
    matching for the gateway routing system.
    """

    def __init__(self):
        self._providers: dict[str, ProviderConfig] = {}

    def register(self, config: ProviderConfig) -> None:
        """Register a provider in the catalog."""
        self._providers[config.provider_id] = config
        logger.info("Provider registered: %s (%s)", config.name, config.provider_type.value)

    def unregister(self, provider_id: str) -> None:
        """Remove a provider from the catalog."""
        self._providers.pop(provider_id, None)

    def get(self, provider_id: str) -> Optional[ProviderConfig]:
        """Get a provider by ID."""
        return self._providers.get(provider_id)

    def list_providers(
        self,
        provider_type: Optional[ProviderType] = None,
        status: Optional[ProviderStatus] = None,
    ) -> list[ProviderConfig]:
        """List providers with optional filtering."""
        providers = list(self._providers.values())
        if provider_type:
            providers = [p for p in providers if p.provider_type == provider_type]
        if status:
            providers = [p for p in providers if p.status == status]
        return providers

    def find_by_capability(
        self,
        capability_name: str,
        min_context: int = 0,
    ) -> list[ProviderConfig]:
        """Find providers supporting a specific capability."""
        matches = []
        for provider in self._providers.values():
            if provider.status == ProviderStatus.OFFLINE:
                continue
            for cap in provider.capabilities:
                if cap.name == capability_name and cap.supported:
                    if min_context and cap.max_context < min_context:
                        continue
                    matches.append(provider)
                    break
        return matches

    def get_available_models(self) -> list[dict[str, Any]]:
        """Get all available models across all providers."""
        models = []
        for provider in self._providers.values():
            if provider.status == ProviderStatus.OFFLINE:
                continue
            for model in provider.available_models:
                models.append({
                    "model": model,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.name,
                    "provider_type": provider.provider_type.value,
                })
        return models

    def get_stats(self) -> dict[str, Any]:
        """Get catalog statistics."""
        return {
            "total_providers": len(self._providers),
            "online_providers": len(self.list_providers(status=ProviderStatus.ONLINE)),
            "providers_by_type": {
                t.value: len(self.list_providers(provider_type=t))
                for t in ProviderType
            },
            "total_models": len(self.get_available_models()),
        }


class PlatformGateway:
    """
    Unified API gateway for the Buddy platform.

    Routes requests to the optimal provider based on routing rules,
    handles failover, load balancing, and request transformation.
    """

    def __init__(self):
        self.catalog = ProviderCatalog()
        self._routing_rules: dict[str, RoutingRule] = {}
        self._request_history: list[GatewayResponse] = []
        self._round_robin_counters: dict[str, int] = {}
        self._provider_latencies: dict[str, list[float]] = {}
        self._provider_connections: dict[str, int] = {}

    # ── Routing Rule Management ────────────────────────────────────

    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule to the gateway."""
        self._routing_rules[rule.rule_id] = rule
        logger.info("Routing rule added: %s (strategy=%s)", rule.name, rule.strategy.value)

    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule."""
        if rule_id in self._routing_rules:
            del self._routing_rules[rule_id]
            return True
        return False

    def list_rules(self, enabled_only: bool = True) -> list[RoutingRule]:
        """List routing rules."""
        rules = list(self._routing_rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return sorted(rules, key=lambda r: r.priority, reverse=True)

    # ── Request Routing ────────────────────────────────────────────

    async def route_request(self, request: GatewayRequest) -> GatewayResponse:
        """Route a request through the gateway to the optimal provider."""
        start = time.time()

        # Find matching routing rule
        rule = self._find_matching_rule(request)

        # Select provider based on strategy
        provider_id = self._select_provider(rule, request) if rule else None

        if not provider_id:
            # Fallback: find any online provider supporting the model
            for provider in self.catalog.list_providers(status=ProviderStatus.ONLINE):
                if request.model in provider.available_models or not request.model:
                    provider_id = provider.provider_id
                    break

        if not provider_id:
            return GatewayResponse(
                request_id=request.request_id,
                success=False,
                error="No available provider found for this request",
                latency_ms=(time.time() - start) * 1000,
            )

        provider = self.catalog.get(provider_id)
        if not provider:
            return GatewayResponse(
                request_id=request.request_id,
                success=False,
                error=f"Provider {provider_id} not found",
                latency_ms=(time.time() - start) * 1000,
            )

        # Simulate provider call
        await asyncio.sleep(0.05)

        model = request.model or provider.default_model
        response = GatewayResponse(
            request_id=request.request_id,
            provider_id=provider_id,
            model=model,
            content=f"Response from {provider.name} via {model}",
            success=True,
            latency_ms=(time.time() - start) * 1000,
            tokens_used=len(request.messages) * 10,
            cost=0.001,
            metadata={
                "routing_strategy": rule.strategy.value if rule else "fallback",
                "provider_type": provider.provider_type.value,
            },
        )

        self._request_history.append(response)
        return response

    async def route_streaming(
        self,
        request: GatewayRequest,
    ) -> Any:
        """Route a streaming request through the gateway."""
        start = time.time()

        provider_id = self._select_provider(None, request)
        if not provider_id:
            for provider in self.catalog.list_providers(status=ProviderStatus.ONLINE):
                provider_id = provider.provider_id
                break

        if not provider_id:
            yield f"data: {json.dumps({'error': 'No provider available'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        provider = self.catalog.get(provider_id)
        import json

        # Simulate streaming tokens
        words = f"Streaming response from {provider.name}".split()
        for word in words:
            await asyncio.sleep(0.1)
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

        yield "data: [DONE]\n\n"

    # ── Multi-Provider Execution ───────────────────────────────────

    async def execute_across_providers(
        self,
        request: GatewayRequest,
        provider_ids: list[str],
        strategy: str = "parallel",
    ) -> list[GatewayResponse]:
        """Execute a request across multiple providers simultaneously."""
        if strategy == "parallel":
            tasks = []
            for pid in provider_ids:
                req = GatewayRequest(
                    model=request.model,
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
                tasks.append(self._execute_with_provider(pid, req))
            return await asyncio.gather(*tasks)
        else:
            # Sequential execution
            results = []
            for pid in provider_ids:
                req = GatewayRequest(
                    model=request.model,
                    messages=request.messages,
                )
                result = await self._execute_with_provider(pid, req)
                results.append(result)
            return results

    async def _execute_with_provider(
        self, provider_id: str, request: GatewayRequest
    ) -> GatewayResponse:
        """Execute a request with a specific provider."""
        start = time.time()
        provider = self.catalog.get(provider_id)

        if not provider:
            return GatewayResponse(
                request_id=request.request_id,
                provider_id=provider_id,
                success=False,
                error="Provider not found",
                latency_ms=(time.time() - start) * 1000,
            )

        await asyncio.sleep(0.05)

        return GatewayResponse(
            request_id=request.request_id,
            provider_id=provider_id,
            model=request.model or provider.default_model,
            content=f"Response from {provider.name}",
            success=True,
            latency_ms=(time.time() - start) * 1000,
        )

    # ── Internal Methods ───────────────────────────────────────────

    def _find_matching_rule(self, request: GatewayRequest) -> Optional[RoutingRule]:
        """Find the matching routing rule for a request."""
        for rule in self.list_rules():
            conditions = rule.condition
            if not conditions:
                return rule

            # Check model condition
            if "model" in conditions:
                if conditions["model"] != request.model:
                    continue

            # Check metadata conditions
            if "metadata" in conditions:
                match = True
                for key, value in conditions["metadata"].items():
                    if request.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            return rule

        return None

    def _select_provider(
        self, rule: Optional[RoutingRule], request: GatewayRequest
    ) -> Optional[str]:
        """Select a provider based on the routing strategy."""
        if rule and rule.target_providers:
            available = [
                pid for pid in rule.target_providers
                if self.catalog.get(pid) and self.catalog.get(pid).status == ProviderStatus.ONLINE
            ]
            if not available:
                return None

            strategy = rule.strategy
            if strategy == RoutingStrategy.ROUND_ROBIN:
                counter = self._round_robin_counters.get(rule.rule_id, 0)
                selected = available[counter % len(available)]
                self._round_robin_counters[rule.rule_id] = counter + 1
                return selected
            elif strategy == RoutingStrategy.LEAST_LATENCY:
                return min(available, key=lambda pid: self._get_avg_latency(pid))
            elif strategy == RoutingStrategy.LEAST_CONNECTIONS:
                return min(available, key=lambda pid: self._provider_connections.get(pid, 0))
            elif strategy == RoutingStrategy.WEIGHTED:
                return available[0]  # Simplified
            else:
                return available[0]

        # No rule: find any online provider
        online = self.catalog.list_providers(status=ProviderStatus.ONLINE)
        if not online:
            return None

        # Try to match model
        for provider in online:
            if request.model in provider.available_models:
                return provider.provider_id

        return online[0].provider_id

    def _get_avg_latency(self, provider_id: str) -> float:
        """Get average latency for a provider."""
        latencies = self._provider_latencies.get(provider_id, [])
        if not latencies:
            return 0.0
        return sum(latencies) / len(latencies)

    def update_provider_latency(self, provider_id: str, latency_ms: float) -> None:
        """Update latency tracking for a provider."""
        if provider_id not in self._provider_latencies:
            self._provider_latencies[provider_id] = []
        self._provider_latencies[provider_id].append(latency_ms)
        # Keep only last 100 measurements
        if len(self._provider_latencies[provider_id]) > 100:
            self._provider_latencies[provider_id] = self._provider_latencies[provider_id][-100:]

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get gateway statistics."""
        return {
            "catalog": self.catalog.get_stats(),
            "total_routing_rules": len(self._routing_rules),
            "active_rules": len(self.list_rules()),
            "total_requests": len(self._request_history),
            "successful_requests": sum(1 for r in self._request_history if r.success),
            "failed_requests": sum(1 for r in self._request_history if not r.success),
            "avg_latency_ms": round(
                sum(r.latency_ms for r in self._request_history) / max(len(self._request_history), 1), 1
            ),
            "recent_requests": [
                {
                    "request_id": r.request_id,
                    "provider_id": r.provider_id,
                    "model": r.model,
                    "success": r.success,
                    "latency_ms": r.latency_ms,
                }
                for r in self._request_history[-10:]
            ],
        }

    def get_request_history(self, limit: int = 50) -> list[GatewayResponse]:
        """Get recent request history."""
        return self._request_history[-limit:]


# Global gateway instance
platform_gateway = PlatformGateway()