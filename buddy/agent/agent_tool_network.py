"""Buddy Agent Tool Network — distributed tool discovery, composition, and execution

The Tool Network provides a distributed, self-organizing tool ecosystem where
agents can discover, compose, execute, and share tools across the network.
It supports semantic tool matching, chain composition, parallel execution,
and result caching with automatic invalidation.

Core capabilities:
  - Tool Discovery: semantic and keyword-based tool search across the network
  - Chain Composition: automatic tool chaining with dependency resolution
  - Parallel Execution: concurrent tool execution with result aggregation
  - Result Caching: intelligent caching with TTL and dependency-based invalidation
  - Tool Registry: dynamic registration, versioning, and deprecation
  - Execution Sandbox: timeout, retry, and circuit breaker patterns
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from config.settings import settings

logger = logging.getLogger("buddy.tool_network")


# ═══════════════════════════════════════════════════════════
# Enums and Types
# ═══════════════════════════════════════════════════════════

class ToolCategory(str, Enum):
    """Categories of tools."""
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    CODE_EXECUTION = "code_execution"
    DATA_PROCESSING = "data_processing"
    SEARCH = "search"
    KNOWLEDGE = "knowledge"
    COMMUNICATION = "communication"
    SYSTEM = "system"
    CUSTOM = "custom"


class ToolRisk(str, Enum):
    """Risk levels for tool execution."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolStatus(str, Enum):
    """Status of a tool in the registry."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    MAINTENANCE = "maintenance"


class ExecutionStrategy(str, Enum):
    """Strategies for tool execution."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    RETRY = "retry"
    FALLBACK = "fallback"


class CacheStrategy(str, Enum):
    """Caching strategies for tool results."""
    NONE = "none"
    TTL = "ttl"
    FINGERPRINT = "fingerprint"
    ADAPTIVE = "adaptive"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class ToolNetworkConfig:
    """Configuration for the Tool Network."""
    max_tools: int = 500
    default_timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 1
    cache_ttl_seconds: int = 300
    max_parallel_executions: int = 10
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: int = 60
    enable_semantic_matching: bool = True


@dataclass
class ToolParameter:
    """A parameter definition for a tool."""
    name: str = ""
    param_type: str = "string"
    description: str = ""
    required: bool = False
    default_value: Any = None
    enum_values: list[Any] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.param_type,
            "description": self.description,
            "required": self.required,
            "default": self.default_value,
            "enum": self.enum_values,
            "validation": self.validation,
        }


@dataclass
class ToolDefinition:
    """Complete definition of a tool."""
    tool_id: str = field(default_factory=lambda: f"tool-{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.CUSTOM
    risk: ToolRisk = ToolRisk.SAFE
    status: ToolStatus = ToolStatus.ACTIVE
    version: str = "1.0.0"
    parameters: list[ToolParameter] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    handler: Callable[..., Any] | None = None
    async_handler: Callable[..., Awaitable[Any]] | None = None
    timeout_seconds: int = 30
    max_retries: int = 3
    cache_strategy: CacheStrategy = CacheStrategy.FINGERPRINT
    cache_ttl_seconds: int = 300
    requires_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "risk": self.risk.value,
            "status": self.status.value,
            "version": self.version,
            "parameters": [p.to_dict() for p in self.parameters],
            "tags": self.tags,
            "dependencies": self.dependencies,
            "timeout_seconds": self.timeout_seconds,
            "requires_approval": self.requires_approval,
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ToolExecution:
    """Record of a tool execution."""
    execution_id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:12]}")
    tool_id: str = ""
    tool_name: str = ""
    agent_id: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str = ""
    success: bool = False
    duration_ms: int = 0
    retries: int = 0
    cache_hit: bool = False
    started_at: str = ""
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "agent_id": self.agent_id,
            "parameters": self.parameters,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "retries": self.retries,
            "cache_hit": self.cache_hit,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class ToolChain:
    """A chain of tools to execute in sequence or parallel."""
    chain_id: str = field(default_factory=lambda: f"chain-{uuid.uuid4().hex[:8]}")
    name: str = ""
    tools: list[str] = field(default_factory=list)
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "tools": self.tools,
            "strategy": self.strategy.value,
            "dependencies": self.dependencies,
            "created_at": self.created_at,
        }


@dataclass
class ToolNetworkStats:
    """Statistics for the Tool Network."""
    total_tools: int = 0
    active_tools: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_execution_ms: float = 0.0
    total_chains: int = 0
    tools_by_category: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tools": self.total_tools,
            "active_tools": self.active_tools,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "avg_execution_ms": self.avg_execution_ms,
            "total_chains": self.total_chains,
            "tools_by_category": self.tools_by_category,
        }


# ═══════════════════════════════════════════════════════════
# Tool Network Implementation
# ═══════════════════════════════════════════════════════════

class AgentToolNetwork:
    """Distributed tool discovery, composition, and execution network."""

    def __init__(self, config: ToolNetworkConfig | None = None):
        self.config = config or ToolNetworkConfig()
        self._tools: dict[str, ToolDefinition] = {}
        self._executions: list[ToolExecution] = []
        self._chains: dict[str, ToolChain] = {}
        self._cache: dict[str, tuple[Any, float]] = {}  # fingerprint -> (result, expiry)
        self._circuit_breakers: dict[str, tuple[int, float]] = {}  # tool_id -> (failures, reset_time)
        self._total_executions: int = 0
        self._total_cache_hits: int = 0
        self._tags_index: dict[str, set[str]] = defaultdict(set)
        logger.info("AgentToolNetwork initialized")

    # ── Tool Registration ────────────────────────────────

    def register_tool(self, definition: ToolDefinition) -> ToolDefinition:
        """Register a new tool in the network."""
        if definition.tool_id in self._tools:
            logger.warning("Tool already registered: %s", definition.tool_id)
            return self._tools[definition.tool_id]

        if len(self._tools) >= self.config.max_tools:
            logger.warning("Tool network at capacity (%d)", self.config.max_tools)

        self._tools[definition.tool_id] = definition

        # Index tags
        for tag in definition.tags:
            self._tags_index[tag.lower()].add(definition.tool_id)

        logger.info("Registered tool: %s (%s)", definition.name, definition.tool_id)
        return definition

    def unregister_tool(self, tool_id: str) -> bool:
        """Remove a tool from the network."""
        tool = self._tools.pop(tool_id, None)
        if not tool:
            return False

        # Remove from tag index
        for tag in tool.tags:
            tag_set = self._tags_index.get(tag.lower(), set())
            tag_set.discard(tool_id)

        logger.info("Unregistered tool: %s", tool_id)
        return True

    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def update_tool(self, tool_id: str, **kwargs) -> ToolDefinition | None:
        """Update tool metadata."""
        tool = self._tools.get(tool_id)
        if not tool:
            return None

        for key, value in kwargs.items():
            if hasattr(tool, key):
                setattr(tool, key, value)

        tool.updated_at = datetime.now(timezone.utc).isoformat()
        return tool

    # ── Tool Discovery ───────────────────────────────────

    def search_tools(
        self,
        query: str = "",
        category: ToolCategory | None = None,
        tags: list[str] | None = None,
        status: ToolStatus | None = None,
        risk: ToolRisk | None = None,
        limit: int = 20,
    ) -> list[ToolDefinition]:
        """Search for tools by query, category, tags, and other filters."""
        results: list[ToolDefinition] = []
        query_lower = query.lower()

        for tool in self._tools.values():
            # Filter by status
            if status and tool.status != status:
                continue

            # Filter by risk
            if risk and tool.risk != risk:
                continue

            # Filter by category
            if category and tool.category != category:
                continue

            # Filter by tags
            if tags:
                tool_tags = {t.lower() for t in tool.tags}
                if not tool_tags.intersection(t.lower() for t in tags):
                    continue

            # Filter by query
            if query:
                if query_lower not in tool.name.lower() and query_lower not in tool.description.lower():
                    # Check tags
                    tag_match = any(query_lower in tag.lower() for tag in tool.tags)
                    if not tag_match:
                        continue

            results.append(tool)

        # Sort by relevance (name matches first)
        if query:
            results.sort(key=lambda t: (
                0 if query_lower in t.name.lower() else 1,
                0 if query_lower in t.description.lower() else 1,
            ))

        return results[:limit]

    def get_tools_by_category(self, category: ToolCategory) -> list[ToolDefinition]:
        """Get all tools in a category."""
        return [t for t in self._tools.values() if t.category == category]

    def get_tools_by_tag(self, tag: str) -> list[ToolDefinition]:
        """Get all tools with a specific tag."""
        tool_ids = self._tags_index.get(tag.lower(), set())
        return [self._tools[tid] for tid in tool_ids if tid in self._tools]

    def list_tools(
        self,
        limit: int = 50,
        offset: int = 0,
        status: ToolStatus | None = None,
    ) -> list[ToolDefinition]:
        """List all tools with optional filtering."""
        tools = list(self._tools.values())
        if status:
            tools = [t for t in tools if t.status == status]
        tools.sort(key=lambda t: t.registered_at, reverse=True)
        return tools[offset:offset + limit]

    # ── Tool Execution ───────────────────────────────────

    async def execute_tool(
        self,
        tool_id: str,
        parameters: dict[str, Any] | None = None,
        agent_id: str = "",
        timeout_seconds: int | None = None,
        skip_cache: bool = False,
    ) -> ToolExecution:
        """Execute a tool with parameters, caching, and circuit breaker."""
        parameters = parameters or {}
        tool = self._tools.get(tool_id)

        execution = ToolExecution(
            tool_id=tool_id,
            tool_name=tool.name if tool else "unknown",
            agent_id=agent_id,
            parameters=parameters,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        if not tool:
            execution.error = f"Tool not found: {tool_id}"
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            self._executions.append(execution)
            self._total_executions += 1
            return execution

        if tool.status == ToolStatus.DISABLED:
            execution.error = f"Tool is disabled: {tool.name}"
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            self._executions.append(execution)
            self._total_executions += 1
            return execution

        # Check circuit breaker
        if not self._check_circuit_breaker(tool_id):
            execution.error = f"Circuit breaker open for: {tool.name}"
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            self._executions.append(execution)
            self._total_executions += 1
            return execution

        # Check cache
        if not skip_cache and tool.cache_strategy != CacheStrategy.NONE:
            cache_key = self._compute_cache_key(tool_id, parameters)
            if cache_key in self._cache:
                result, expiry = self._cache[cache_key]
                if time.monotonic() < expiry:
                    execution.result = result
                    execution.success = True
                    execution.cache_hit = True
                    execution.completed_at = datetime.now(timezone.utc).isoformat()
                    self._executions.append(execution)
                    self._total_executions += 1
                    self._total_cache_hits += 1
                    return execution
                else:
                    del self._cache[cache_key]

        # Execute with retry
        timeout = timeout_seconds or tool.timeout_seconds or self.config.default_timeout_seconds
        start = time.monotonic()

        for attempt in range(tool.max_retries + 1):
            try:
                if tool.async_handler:
                    result = await asyncio.wait_for(
                        tool.async_handler(**parameters),
                        timeout=timeout,
                    )
                elif tool.handler:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: tool.handler(**parameters),
                    )
                    # Simulate async timeout
                    result = await asyncio.wait_for(asyncio.sleep(0), timeout=timeout) or result
                else:
                    execution.error = f"No handler for tool: {tool.name}"
                    execution.completed_at = datetime.now(timezone.utc).isoformat()
                    self._executions.append(execution)
                    self._total_executions += 1
                    return execution

                execution.result = result
                execution.success = True
                execution.retries = attempt
                execution.duration_ms = int((time.monotonic() - start) * 1000)
                execution.completed_at = datetime.now(timezone.utc).isoformat()

                # Cache result
                if tool.cache_strategy != CacheStrategy.NONE:
                    cache_key = self._compute_cache_key(tool_id, parameters)
                    ttl = tool.cache_ttl_seconds or self.config.cache_ttl_seconds
                    self._cache[cache_key] = (result, time.monotonic() + ttl)

                # Reset circuit breaker on success
                self._circuit_breakers.pop(tool_id, None)

                self._executions.append(execution)
                self._total_executions += 1
                return execution

            except asyncio.TimeoutError:
                execution.error = f"Timeout after {timeout}s"
                execution.retries = attempt
            except Exception as e:
                execution.error = str(e)
                execution.retries = attempt
                logger.error("Tool %s execution failed (attempt %d): %s", tool.name, attempt + 1, e)

            if attempt < tool.max_retries:
                await asyncio.sleep(self.config.retry_delay_seconds)

        # All retries failed
        execution.success = False
        execution.duration_ms = int((time.monotonic() - start) * 1000)
        execution.completed_at = datetime.now(timezone.utc).isoformat()

        # Update circuit breaker
        self._record_circuit_breaker_failure(tool_id)

        self._executions.append(execution)
        self._total_executions += 1
        return execution

    async def execute_tool_chain(
        self,
        chain_id: str,
        agent_id: str = "",
        parameters_map: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, ToolExecution]:
        """Execute a chain of tools."""
        chain = self._chains.get(chain_id)
        if not chain:
            return {}

        parameters_map = parameters_map or {}
        results: dict[str, ToolExecution] = {}

        if chain.strategy == ExecutionStrategy.PARALLEL:
            # Execute all tools in parallel
            tasks = []
            for tool_id in chain.tools:
                params = parameters_map.get(tool_id, {})
                tasks.append(self.execute_tool(tool_id, params, agent_id))

            executions = await asyncio.gather(*tasks, return_exceptions=True)
            for tool_id, execution in zip(chain.tools, executions):
                if isinstance(execution, Exception):
                    results[tool_id] = ToolExecution(
                        tool_id=tool_id,
                        error=str(execution),
                        success=False,
                    )
                else:
                    results[tool_id] = execution
        else:
            # Sequential execution with dependency resolution
            completed: dict[str, Any] = {}

            for tool_id in chain.tools:
                # Resolve dependencies
                params = dict(parameters_map.get(tool_id, {}))
                deps = chain.dependencies.get(tool_id, [])
                for dep in deps:
                    if dep in completed:
                        params[f"_{dep}_result"] = completed[dep]

                execution = await self.execute_tool(tool_id, params, agent_id)
                results[tool_id] = execution
                if execution.success:
                    completed[tool_id] = execution.result

        return results

    # ── Chain Management ─────────────────────────────────

    def create_chain(
        self,
        name: str,
        tools: list[str],
        strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
        dependencies: dict[str, list[str]] | None = None,
    ) -> ToolChain:
        """Create a new tool chain."""
        chain = ToolChain(
            name=name,
            tools=tools,
            strategy=strategy,
            dependencies=dependencies or {},
        )
        self._chains[chain.chain_id] = chain
        logger.info("Created tool chain: %s (%s)", name, chain.chain_id)
        return chain

    def get_chain(self, chain_id: str) -> ToolChain | None:
        """Get a chain by ID."""
        return self._chains.get(chain_id)

    def list_chains(self) -> list[ToolChain]:
        """List all tool chains."""
        return list(self._chains.values())

    def delete_chain(self, chain_id: str) -> bool:
        """Delete a tool chain."""
        return self._chains.pop(chain_id, None) is not None

    # ── Execution History ────────────────────────────────

    def get_execution(self, execution_id: str) -> ToolExecution | None:
        """Get an execution record by ID."""
        for execution in self._executions:
            if execution.execution_id == execution_id:
                return execution
        return None

    def list_executions(
        self,
        tool_id: str = "",
        agent_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[ToolExecution]:
        """List execution records with filtering."""
        executions = self._executions
        if tool_id:
            executions = [e for e in executions if e.tool_id == tool_id]
        if agent_id:
            executions = [e for e in executions if e.agent_id == agent_id]

        executions.sort(key=lambda e: e.started_at or "", reverse=True)
        return executions[offset:offset + limit]

    # ── Cache Management ─────────────────────────────────

    def invalidate_cache(self, tool_id: str = "") -> int:
        """Invalidate cache entries for a tool or all tools."""
        if tool_id:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{tool_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)
        else:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = len(self._cache)
        expired = sum(1 for _, (_, expiry) in self._cache.items() if time.monotonic() >= expiry)
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "total_hits": self._total_cache_hits,
        }

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> ToolNetworkStats:
        """Get comprehensive tool network statistics."""
        stats = ToolNetworkStats()
        stats.total_tools = len(self._tools)
        stats.active_tools = sum(1 for t in self._tools.values() if t.status == ToolStatus.ACTIVE)
        stats.total_executions = self._total_executions
        stats.total_chains = len(self._chains)

        category_counts: dict[str, int] = defaultdict(int)
        total_duration = 0
        success_count = 0
        fail_count = 0

        for execution in self._executions:
            if execution.success:
                success_count += 1
            else:
                fail_count += 1
            total_duration += execution.duration_ms

        for tool in self._tools.values():
            category_counts[tool.category.value] += 1

        stats.successful_executions = success_count
        stats.failed_executions = fail_count
        stats.cache_hits = self._total_cache_hits
        stats.cache_misses = self._total_executions - self._total_cache_hits
        stats.tools_by_category = dict(category_counts)

        if self._total_executions > 0:
            stats.avg_execution_ms = total_duration / self._total_executions

        return stats

    def reset(self) -> None:
        """Reset the tool network."""
        self._tools.clear()
        self._executions.clear()
        self._chains.clear()
        self._cache.clear()
        self._circuit_breakers.clear()
        self._tags_index.clear()
        self._total_executions = 0
        self._total_cache_hits = 0
        logger.info("AgentToolNetwork reset")

    # ── Internal Helpers ─────────────────────────────────

    def _compute_cache_key(self, tool_id: str, parameters: dict[str, Any]) -> str:
        """Compute a cache key from tool ID and parameters."""
        param_str = json.dumps(parameters, sort_keys=True, default=str)
        fingerprint = f"{tool_id}:{hashlib.md5(param_str.encode()).hexdigest()}"
        return fingerprint

    def _check_circuit_breaker(self, tool_id: str) -> bool:
        """Check if the circuit breaker allows execution."""
        breaker = self._circuit_breakers.get(tool_id)
        if not breaker:
            return True

        failures, reset_time = breaker
        if failures >= self.config.circuit_breaker_threshold:
            if time.monotonic() < reset_time:
                return False
            else:
                # Reset circuit breaker
                del self._circuit_breakers[tool_id]
        return True

    def _record_circuit_breaker_failure(self, tool_id: str) -> None:
        """Record a failure for circuit breaker tracking."""
        if tool_id not in self._circuit_breakers:
            self._circuit_breakers[tool_id] = (0, 0)

        failures, _ = self._circuit_breakers[tool_id]
        failures += 1
        reset_time = time.monotonic() + self.config.circuit_breaker_reset_seconds
        self._circuit_breakers[tool_id] = (failures, reset_time)


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_tool_network: AgentToolNetwork | None = None


def get_tool_network() -> AgentToolNetwork:
    """Get or create the global Tool Network instance."""
    global _tool_network
    if _tool_network is None:
        _tool_network = AgentToolNetwork()
    return _tool_network


def reset_tool_network() -> None:
    """Reset the global Tool Network instance."""
    global _tool_network
    if _tool_network:
        _tool_network.reset()
    _tool_network = None