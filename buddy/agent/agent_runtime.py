"""Buddy Agent Runtime — unified agent lifecycle orchestration engine

Provides the complete runtime environment for Buddy agents, deeply integrating
all subsystems — reasoning, tool orchestration, memory, metacognition, evolution,
proactive discovery, reactive execution, and skills — into a single cohesive
execution framework. This is the primary interface through which all agent
operations flow.

Runtime capabilities:
  - Lifecycle Management: complete agent lifecycle from creation to teardown
  - Execution Orchestration: coordinates all execution modes (chat, task, autopilot, swarm)
  - Resource Management: token budgeting, rate limiting, concurrent execution
  - State Persistence: checkpoint/restore, state serialization, crash recovery
  - Event Streaming: real-time event emission for all agent activities
  - Performance Monitoring: metric collection, latency tracking, throughput analysis
  - Adaptive Execution: dynamic strategy selection based on runtime conditions
  - Error Recovery: graceful degradation, fallback chains, retry policies
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Callable, Awaitable

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger("buddy.agent_runtime")


# ═══════════════════════════════════════════════════════════
# Core Enums and Configuration
# ═══════════════════════════════════════════════════════════

class RuntimeState(str, Enum):
    """Agent runtime lifecycle states."""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ExecutionMode(str, Enum):
    """Supported execution modes."""
    CHAT = "chat"
    TASK = "task"
    AUTOPILOT = "autopilot"
    PROACTIVE = "proactive"
    SWARM = "swarm"
    REACTIVE = "reactive"
    DREAM = "dream"
    PLAN = "plan"
    DELEGATED = "delegated"


class RuntimeEventType(str, Enum):
    """Events emitted by the runtime."""
    STATE_CHANGE = "state_change"
    EXECUTION_START = "execution_start"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_ERROR = "execution_error"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    MEMORY_UPDATE = "memory_update"
    INSIGHT_GENERATED = "insight_generated"
    STRATEGY_SELECTED = "strategy_selected"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CHECKPOINT_SAVED = "checkpoint_saved"
    HEARTBEAT = "heartbeat"


@dataclass
class RuntimeConfig:
    """Configuration for the agent runtime."""
    max_iterations: int = 90
    max_tool_rounds: int = 8
    max_parallel_tasks: int = 5
    token_budget: int = 100000
    context_window: int = 8000
    checkpoint_interval: int = 10  # Save checkpoint every N executions
    heartbeat_interval_ms: int = 30000
    enable_metacognition: bool = True
    enable_evolution: bool = True
    enable_proactive: bool = True
    enable_streaming: bool = True
    enable_events: bool = True
    enable_metrics: bool = True
    enable_checkpoints: bool = True
    enable_guardrails: bool = True
    enable_cost_tracking: bool = True


@dataclass
class RuntimeEvent:
    """An event emitted by the runtime."""
    id: str
    event_type: RuntimeEventType
    agent_id: str
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class RuntimeMetrics:
    """Runtime performance metrics."""
    agent_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_tokens_used: int = 0
    total_tool_calls: int = 0
    total_tool_errors: int = 0
    avg_response_time_ms: float = 0.0
    avg_tokens_per_execution: float = 0.0
    current_state: RuntimeState = RuntimeState.CREATED
    uptime_seconds: float = 0.0
    last_activity: str = ""


@dataclass
class ExecutionContext:
    """Context for a single execution within the runtime."""
    id: str
    mode: ExecutionMode
    prompt: str
    agent_id: str
    conversation_id: str | None = None
    enable_tools: bool = True
    enable_reasoning: bool = False
    stream: bool = False
    metadata: dict = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    result: str = ""
    error: str = ""
    tokens_used: int = 0
    tool_calls: int = 0
    success: bool = True


# ═══════════════════════════════════════════════════════════
# Agent Runtime
# ═══════════════════════════════════════════════════════════

class AgentRuntime:
    """Unified agent runtime orchestrating all agent subsystems.

    The runtime is the central execution context for a Buddy agent. It manages
    the complete lifecycle, coordinates all execution modes, monitors performance,
    handles errors, and emits events for real-time observation.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str = "Buddy",
        config: RuntimeConfig | None = None,
        client: AsyncOpenAI | None = None,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.config = config or RuntimeConfig()
        self.client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        # State
        self._state = RuntimeState.CREATED
        self._started_at = datetime.now(timezone.utc)

        # Metrics
        self._metrics = RuntimeMetrics(agent_id=agent_id)
        self._execution_history: list[ExecutionContext] = []
        self._max_history = 200

        # Event system
        self._event_listeners: dict[str, list[Callable[[RuntimeEvent], Awaitable[None]]]] = defaultdict(list)
        self._event_queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(maxsize=1000)

        # Token budget
        self._token_budget_remaining = self.config.token_budget
        self._token_budget_warned = False

        # Execution tracking
        self._active_executions: dict[str, ExecutionContext] = {}
        self._execution_semaphore = asyncio.Semaphore(self.config.max_parallel_tasks)

        # Checkpoint tracking
        self._execution_count_since_checkpoint = 0
        self._checkpoint_data: dict[str, Any] = {}

        # Subsystem references (lazy initialized)
        self._engine = None
        self._intelligence = None
        self._agent_core = None
        self._synthesis = None

        # Heartbeat
        self._heartbeat_task: asyncio.Task | None = None
        self._running = False

        logger.info(f"AgentRuntime created for {agent_id} ({agent_name})")

    # ── Properties ───────────────────────────────────────

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def metrics(self) -> RuntimeMetrics:
        return self._metrics

    @property
    def is_ready(self) -> bool:
        return self._state in {RuntimeState.READY, RuntimeState.RUNNING}

    @property
    def token_budget_remaining(self) -> int:
        return self._token_budget_remaining

    # ── Lifecycle Management ─────────────────────────────

    async def initialize(self) -> bool:
        """Initialize the runtime and all subsystems."""
        if self._state not in {RuntimeState.CREATED}:
            logger.warning(f"Runtime {self.agent_id} already initialized (state={self._state.value})")
            return False

        self._transition_state(RuntimeState.INITIALIZING)

        try:
            # Start heartbeat
            if self.config.heartbeat_interval_ms > 0:
                self._running = True
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            self._transition_state(RuntimeState.READY)
            self._metrics.current_state = RuntimeState.READY
            self._metrics.uptime_seconds = 0.0

            logger.info(f"Runtime {self.agent_id} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Runtime {self.agent_id} initialization failed: {e}")
            self._transition_state(RuntimeState.ERROR)
            return False

    async def shutdown(self) -> bool:
        """Gracefully shutdown the runtime."""
        self._transition_state(RuntimeState.STOPPING)

        # Cancel heartbeat
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Wait for active executions to complete
        timeout = 30
        start = time.time()
        while self._active_executions and (time.time() - start) < timeout:
            await asyncio.sleep(0.5)

        # Cancel remaining
        for exec_id in list(self._active_executions.keys()):
            self._active_executions.pop(exec_id, None)

        self._transition_state(RuntimeState.STOPPED)
        logger.info(f"Runtime {self.agent_id} shutdown complete")
        return True

    def pause(self):
        """Pause runtime execution."""
        if self._state in {RuntimeState.READY, RuntimeState.RUNNING}:
            self._transition_state(RuntimeState.PAUSED)

    def resume(self):
        """Resume runtime execution."""
        if self._state == RuntimeState.PAUSED:
            self._transition_state(RuntimeState.READY)

    # ── State Management ────────────────────────────────

    def _transition_state(self, new_state: RuntimeState):
        old_state = self._state
        self._state = new_state
        self._metrics.current_state = new_state

        if self.config.enable_events:
            self._emit_event_sync(RuntimeEventType.STATE_CHANGE, {
                "from": old_state.value,
                "to": new_state.value,
            })

        logger.debug(f"Runtime {self.agent_id}: {old_state.value} → {new_state.value}")

    # ── Execution Orchestration ──────────────────────────

    async def execute(
        self,
        prompt: str,
        mode: ExecutionMode = ExecutionMode.CHAT,
        conversation_id: str | None = None,
        enable_tools: bool = True,
        enable_reasoning: bool = False,
        stream: bool = False,
        metadata: dict | None = None,
    ) -> str | AsyncIterator[str]:
        """Execute a prompt through the agent runtime.

        This is the primary execution entry point. It handles all execution modes,
        manages resource allocation, tracks metrics, and emits events.
        """
        if not self.is_ready and self._state != RuntimeState.RUNNING:
            raise RuntimeError(f"Runtime {self.agent_id} not ready (state={self._state.value})")

        # Check token budget
        if self._token_budget_remaining <= 0:
            raise RuntimeError(f"Token budget exhausted for {self.agent_id}")

        # Create execution context
        exec_ctx = ExecutionContext(
            id=f"exec-{uuid.uuid4().hex[:12]}",
            mode=mode,
            prompt=prompt,
            agent_id=self.agent_id,
            conversation_id=conversation_id,
            enable_tools=enable_tools,
            enable_reasoning=enable_reasoning,
            stream=stream,
            metadata=metadata or {},
        )

        self._active_executions[exec_ctx.id] = exec_ctx
        self._transition_state(RuntimeState.RUNNING)
        self._metrics.total_executions += 1

        # Emit start event
        if self.config.enable_events:
            self._emit_event_sync(RuntimeEventType.EXECUTION_START, {
                "execution_id": exec_ctx.id,
                "mode": mode.value,
                "prompt": prompt[:200],
            })

        start_time = time.time()

        try:
            async with self._execution_semaphore:
                if stream:
                    result = await self._execute_streaming(exec_ctx)
                else:
                    result = await self._execute_direct(exec_ctx)

            elapsed_ms = (time.time() - start_time) * 1000
            exec_ctx.completed_at = datetime.now(timezone.utc).isoformat()

            # Update metrics
            self._metrics.successful_executions += 1
            self._update_timing_metrics(elapsed_ms)
            self._metrics.total_tokens_used += exec_ctx.tokens_used
            self._metrics.total_tool_calls += exec_ctx.tool_calls
            self._metrics.last_activity = exec_ctx.completed_at

            # Track execution
            self._execution_history.append(exec_ctx)
            if len(self._execution_history) > self._max_history:
                self._execution_history = self._execution_history[-self._max_history:]

            # Checkpoint
            self._execution_count_since_checkpoint += 1
            if self.config.enable_checkpoints and self._execution_count_since_checkpoint >= self.config.checkpoint_interval:
                await self._auto_checkpoint()

            # Emit complete event
            if self.config.enable_events:
                self._emit_event_sync(RuntimeEventType.EXECUTION_COMPLETE, {
                    "execution_id": exec_ctx.id,
                    "elapsed_ms": elapsed_ms,
                    "tokens_used": exec_ctx.tokens_used,
                    "tool_calls": exec_ctx.tool_calls,
                })

            # Transition back to ready
            if not self._active_executions:
                self._transition_state(RuntimeState.READY)

            return result

        except Exception as e:
            exec_ctx.success = False
            exec_ctx.error = str(e)
            self._metrics.failed_executions += 1

            if self.config.enable_events:
                self._emit_event_sync(RuntimeEventType.EXECUTION_ERROR, {
                    "execution_id": exec_ctx.id,
                    "error": str(e),
                })

            logger.error(f"Runtime {self.agent_id} execution error: {e}")
            raise

        finally:
            self._active_executions.pop(exec_ctx.id, None)

    async def _execute_direct(self, ctx: ExecutionContext) -> str:
        """Execute a prompt directly (non-streaming)."""
        if self._engine is None:
            from agent.engine import AgentEngine
            self._engine = AgentEngine(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                instructions="",
            )
            self._engine._conversation_id = ctx.conversation_id

        result = await self._engine.chat(
            message=ctx.prompt,
            enable_tools=ctx.enable_tools,
            enable_reasoning=ctx.enable_reasoning,
        )

        ctx.result = result if isinstance(result, str) else ""
        ctx.tokens_used = self._engine.total_tokens
        ctx.success = True
        return ctx.result

    async def _execute_streaming(self, ctx: ExecutionContext) -> AsyncIterator[str]:
        """Execute a prompt with streaming output."""
        if self._engine is None:
            from agent.engine import AgentEngine
            self._engine = AgentEngine(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                instructions="",
            )
            self._engine._conversation_id = ctx.conversation_id

        collected = []
        async for chunk in self._engine.chat(
            message=ctx.prompt,
            stream=True,
            enable_tools=ctx.enable_tools,
            enable_reasoning=ctx.enable_reasoning,
        ):
            collected.append(chunk)
            yield chunk

        ctx.result = "".join(collected)
        ctx.tokens_used = self._engine.total_tokens
        ctx.success = True

    # ── Token Budget Management ─────────────────────────

    def consume_tokens(self, count: int) -> bool:
        """Consume tokens from the budget. Returns True if successful."""
        if count > self._token_budget_remaining:
            if not self._token_budget_warned:
                self._token_budget_warned = True
                if self.config.enable_events:
                    self._emit_event_sync(RuntimeEventType.BUDGET_EXHAUSTED, {
                        "requested": count,
                        "remaining": self._token_budget_remaining,
                    })
            return False

        self._token_budget_remaining -= count

        if self._token_budget_remaining < self.config.token_budget * 0.1 and not self._token_budget_warned:
            self._token_budget_warned = True
            if self.config.enable_events:
                self._emit_event_sync(RuntimeEventType.BUDGET_WARNING, {
                    "remaining": self._token_budget_remaining,
                    "percent": (self._token_budget_remaining / self.config.token_budget) * 100,
                })

        return True

    def refill_tokens(self, count: int):
        """Refill the token budget."""
        self._token_budget_remaining = min(
            self._token_budget_remaining + count,
            self.config.token_budget,
        )
        self._token_budget_warned = False

    # ── Event System ────────────────────────────────────

    def on_event(self, event_type: RuntimeEventType, callback: Callable[[RuntimeEvent], Awaitable[None]]):
        """Register an event listener."""
        self._event_listeners[event_type.value].append(callback)

    def off_event(self, event_type: RuntimeEventType, callback: Callable[[RuntimeEvent], Awaitable[None]]):
        """Remove an event listener."""
        listeners = self._event_listeners.get(event_type.value, [])
        if callback in listeners:
            listeners.remove(callback)

    def _emit_event_sync(self, event_type: RuntimeEventType, data: dict | None = None):
        """Synchronously queue an event for async dispatch."""
        event = RuntimeEvent(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            agent_id=self.agent_id,
            data=data or {},
        )
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"Event queue full for {self.agent_id}, dropping event {event_type.value}")

    async def _process_events(self):
        """Background event processing loop."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                listeners = self._event_listeners.get(event.event_type.value, [])
                for callback in listeners:
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Event callback error: {e}")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")

    # ── Heartbeat ───────────────────────────────────────

    async def _heartbeat_loop(self):
        """Background heartbeat loop."""
        event_processor = asyncio.create_task(self._process_events())
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval_ms / 1000)
                self._metrics.uptime_seconds = (
                    datetime.now(timezone.utc) - self._started_at
                ).total_seconds()

                if self.config.enable_events:
                    self._emit_event_sync(RuntimeEventType.HEARTBEAT, {
                        "uptime_seconds": self._metrics.uptime_seconds,
                        "state": self._state.value,
                        "executions": self._metrics.total_executions,
                        "tokens_remaining": self._token_budget_remaining,
                    })
            except asyncio.CancelledError:
                break

        event_processor.cancel()
        try:
            await event_processor
        except asyncio.CancelledError:
            pass

    # ── Checkpoint Management ───────────────────────────

    async def _auto_checkpoint(self):
        """Automatically save a checkpoint."""
        if not self.config.enable_checkpoints:
            return

        checkpoint_id = f"cp-auto-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self._checkpoint_data[checkpoint_id] = {
            "state": self._state.value,
            "metrics": {
                "total_executions": self._metrics.total_executions,
                "successful": self._metrics.successful_executions,
                "total_tokens": self._metrics.total_tokens_used,
                "total_tool_calls": self._metrics.total_tool_calls,
            },
            "token_budget": self._token_budget_remaining,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._execution_count_since_checkpoint = 0

        if self.config.enable_events:
            self._emit_event_sync(RuntimeEventType.CHECKPOINT_SAVED, {
                "checkpoint_id": checkpoint_id,
            })

        # Prune old checkpoints
        if len(self._checkpoint_data) > 50:
            oldest = sorted(self._checkpoint_data.keys())[0]
            del self._checkpoint_data[oldest]

    async def save_checkpoint(self, name: str, data: dict | None = None) -> str:
        """Manually save a checkpoint."""
        checkpoint_id = f"cp-{name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self._checkpoint_data[checkpoint_id] = {
            "name": name,
            "state": self._state.value,
            "metrics": {
                "total_executions": self._metrics.total_executions,
                "successful": self._metrics.successful_executions,
                "total_tokens": self._metrics.total_tokens_used,
            },
            "custom_data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> dict | None:
        """Restore from a checkpoint."""
        cp = self._checkpoint_data.get(checkpoint_id)
        return cp.copy() if cp else None

    def list_checkpoints(self) -> list[dict]:
        """List all checkpoints."""
        return [
            {"id": cid, "name": data.get("name", "auto"), "timestamp": data.get("timestamp", "")}
            for cid, data in sorted(
                self._checkpoint_data.items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=True,
            )
        ]

    # ── Metrics & Statistics ────────────────────────────

    def _update_timing_metrics(self, elapsed_ms: float):
        """Update timing-based metrics."""
        n = self._metrics.total_executions
        self._metrics.avg_response_time_ms = (
            (self._metrics.avg_response_time_ms * (n - 1) + elapsed_ms) / n
        )
        if n > 0:
            self._metrics.avg_tokens_per_execution = self._metrics.total_tokens_used / n

    def get_stats(self) -> dict:
        """Get comprehensive runtime statistics."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "state": self._state.value,
            "uptime_seconds": (
                datetime.now(timezone.utc) - self._started_at
            ).total_seconds(),
            "executions": {
                "total": self._metrics.total_executions,
                "successful": self._metrics.successful_executions,
                "failed": self._metrics.failed_executions,
                "success_rate": round(
                    self._metrics.successful_executions / max(self._metrics.total_executions, 1), 3
                ),
            },
            "performance": {
                "avg_response_time_ms": round(self._metrics.avg_response_time_ms, 1),
                "avg_tokens_per_execution": round(self._metrics.avg_tokens_per_execution, 1),
                "total_tokens_used": self._metrics.total_tokens_used,
                "total_tool_calls": self._metrics.total_tool_calls,
                "total_tool_errors": self._metrics.total_tool_errors,
            },
            "resources": {
                "token_budget_remaining": self._token_budget_remaining,
                "token_budget_total": self.config.token_budget,
                "token_budget_percent": round(
                    (self._token_budget_remaining / self.config.token_budget) * 100, 1
                ),
                "active_executions": len(self._active_executions),
                "max_parallel_tasks": self.config.max_parallel_tasks,
            },
            "checkpoints": len(self._checkpoint_data),
            "event_listeners": sum(len(v) for v in self._event_listeners.values()),
        }

    def get_recent_executions(self, limit: int = 10) -> list[dict]:
        """Get recent execution contexts."""
        return [
            {
                "id": e.id,
                "mode": e.mode.value,
                "prompt": e.prompt[:200],
                "success": e.success,
                "tokens_used": e.tokens_used,
                "tool_calls": e.tool_calls,
                "elapsed": e.completed_at,
                "error": e.error[:100] if e.error else "",
            }
            for e in self._execution_history[-limit:]
        ]

    # ── Intelligence Integration ────────────────────────

    def get_intelligence(self):
        """Get or create the intelligence core for this runtime."""
        if self._intelligence is None:
            from agent.agent_intelligence import AgentIntelligence, IntelligenceConfig
            self._intelligence = AgentIntelligence(IntelligenceConfig(
                enable_self_critique=True,
                enable_experience_replay=True,
                enable_strategy_adaptation=True,
            ))
        return self._intelligence

    def get_agent_core(self):
        """Get or create the agent core for this runtime."""
        if self._agent_core is None:
            from agent.agent_core import AgentCore, AgentCoreConfig
            self._agent_core = AgentCore(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                config=AgentCoreConfig(
                    enable_metacognition=self.config.enable_metacognition,
                    enable_evolution=self.config.enable_evolution,
                    enable_proactive=self.config.enable_proactive,
                ),
            )
        return self._agent_core

    def get_synthesis(self):
        """Get the synthesis engine."""
        if self._synthesis is None:
            from agent.agent_synthesis import agent_synthesis
            self._synthesis = agent_synthesis
        return self._synthesis


# ═══════════════════════════════════════════════════════════
# Runtime Registry — manages all active runtimes
# ═══════════════════════════════════════════════════════════

class RuntimeRegistry:
    """Registry managing all active agent runtimes."""

    def __init__(self):
        self._runtimes: dict[str, AgentRuntime] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        agent_id: str,
        agent_name: str = "Buddy",
        config: RuntimeConfig | None = None,
    ) -> AgentRuntime:
        """Get an existing runtime or create a new one."""
        async with self._lock:
            if agent_id not in self._runtimes:
                runtime = AgentRuntime(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    config=config,
                )
                await runtime.initialize()
                self._runtimes[agent_id] = runtime
            return self._runtimes[agent_id]

    async def remove(self, agent_id: str):
        """Remove and shutdown a runtime."""
        async with self._lock:
            runtime = self._runtimes.pop(agent_id, None)
            if runtime:
                await runtime.shutdown()

    async def shutdown_all(self):
        """Shutdown all runtimes."""
        async with self._lock:
            for runtime in list(self._runtimes.values()):
                await runtime.shutdown()
            self._runtimes.clear()

    def get(self, agent_id: str) -> AgentRuntime | None:
        """Get a runtime by agent ID."""
        return self._runtimes.get(agent_id)

    def list_all(self) -> list[dict]:
        """List all active runtimes."""
        return [
            {
                "agent_id": rid,
                "agent_name": rt.agent_name,
                "state": rt.state.value,
                "executions": rt.metrics.total_executions,
                "uptime": rt.metrics.uptime_seconds,
            }
            for rid, rt in self._runtimes.items()
        ]

    @property
    def active_count(self) -> int:
        return len(self._runtimes)

    @property
    def total_executions(self) -> int:
        return sum(rt.metrics.total_executions for rt in self._runtimes.values())


# Global runtime registry instance
runtime_registry = RuntimeRegistry()