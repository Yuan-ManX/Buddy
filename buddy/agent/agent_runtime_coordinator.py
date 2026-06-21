"""Buddy Runtime Coordinator — unified agent lifecycle orchestration

The Runtime Coordinator serves as the central nervous system of the Buddy platform,
tying together all agent capabilities into a single cohesive runtime. It manages:

- Lifecycle orchestration: initialize, run, pause, resume, shutdown agents
- Cross-module coordination: unified brain, deep reasoning, self-improvement, sessions
- Context synthesis: aggregate context from all subsystems for coherent execution
- State management: track and persist agent state across all modules
- Event propagation: route events between modules and external systems
- Recovery and resilience: graceful degradation and automatic recovery
"""
from __future__ import annotations
import json
import logging
import uuid
import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, AsyncIterator

from config.settings import settings

logger = logging.getLogger("buddy.runtime_coordinator")


# ── Enums ─────────────────────────────────────────────────

class CoordinatorState(str, Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    RECOVERING = "recovering"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ExecutionMode(str, Enum):
    DIRECT = "direct"          # Simple request-response
    REASONED = "reasoned"       # Deep reasoning with planning
    COLLABORATIVE = "collaborative"  # Multi-agent coordination
    AUTONOMOUS = "autonomous"    # Self-directed execution
    REFLECTIVE = "reflective"    # Self-improvement focused


class ModuleType(str, Enum):
    BRAIN = "unified_brain"
    REASONING = "deep_reasoning"
    SELF_IMPROVE = "self_improve"
    SESSION = "agent_session"
    PLATFORM = "platform_core"
    GOVERNANCE = "governance"
    PERSONA = "persona"
    MEMORY = "memory"
    IDENTITY = "identity"
    EVOLUTION = "evolution"


# ── Data Classes ──────────────────────────────────────────

@dataclass
class CoordinatorConfig:
    """Configuration for the runtime coordinator."""
    coordinator_id: str = field(default_factory=lambda: f"coord-{uuid.uuid4().hex[:8]}")
    max_concurrent_agents: int = 10
    execution_timeout_ms: int = 300000
    enable_auto_recovery: bool = True
    enable_telemetry: bool = True
    enable_governance: bool = True
    enable_persona_matching: bool = True
    log_level: str = "INFO"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleStatus:
    """Status of an individual module within the coordinator."""
    module_type: ModuleType
    is_available: bool = False
    is_healthy: bool = True
    last_heartbeat: str = ""
    error_count: int = 0
    total_calls: int = 0
    avg_latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Aggregated context for a single execution."""
    context_id: str = field(default_factory=lambda: f"ctx-{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    agent_name: str = ""
    user_message: str = ""
    system_prompt: str = ""
    conversation_history: list[dict] = field(default_factory=list)
    memory_context: str = ""
    identity_context: str = ""
    persona_context: str = ""
    workspace_context: str = ""
    governance_context: dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    mode: ExecutionMode = ExecutionMode.DIRECT
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Complete result of a coordinated execution."""
    result_id: str = field(default_factory=lambda: f"res-{uuid.uuid4().hex[:8]}")
    content: str = ""
    success: bool = True
    error: str = ""
    mode_used: ExecutionMode = ExecutionMode.DIRECT
    modules_used: list[ModuleType] = field(default_factory=list)
    tokens_used: int = 0
    total_duration_ms: float = 0.0
    brain_cycle: dict[str, Any] = field(default_factory=dict)
    reasoning_trace: dict[str, Any] = field(default_factory=dict)
    improvements: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CoordinatorStats:
    """Aggregate statistics for the coordinator."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_tokens: int = 0
    total_time_ms: float = 0.0
    modes_used: dict[str, int] = field(default_factory=dict)
    modules_used: dict[str, int] = field(default_factory=dict)
    agents_managed: int = 0
    active_agents: int = 0
    uptime_seconds: float = 0.0


# ── Runtime Coordinator ──────────────────────────────────

class RuntimeCoordinator:
    """Central runtime coordinator that orchestrates all agent capabilities.

    Serves as the primary integration point between the Unified Brain,
    Platform Core, Deep Reasoning, Self-Improvement, Session Manager,
    and all other subsystems. Manages complete agent lifecycle with
    graceful degradation and automatic recovery.
    """

    def __init__(self, config: CoordinatorConfig | None = None):
        self._config = config or CoordinatorConfig()
        self._state = CoordinatorState.UNINITIALIZED
        self._modules: dict[ModuleType, ModuleStatus] = {}
        self._execution_history: list[ExecutionResult] = []
        self._contexts: dict[str, ExecutionContext] = {}
        self._stats = CoordinatorStats()
        self._start_time: str = ""
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._recovery_attempts: dict[str, int] = {}
        self._agent_registry: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # ── Lifecycle ────────────────────────────────────────

    async def initialize(self) -> bool:
        """Initialize all modules and prepare the coordinator for operation."""
        if self._state not in (CoordinatorState.UNINITIALIZED, CoordinatorState.STOPPED):
            logger.warning(f"Coordinator already in state {self._state.value}")
            return False

        self._state = CoordinatorState.INITIALIZING
        self._start_time = datetime.now(timezone.utc).isoformat()

        try:
            # Initialize module statuses
            for module_type in ModuleType:
                self._modules[module_type] = ModuleStatus(
                    module_type=module_type,
                    is_available=True,
                    last_heartbeat=datetime.now(timezone.utc).isoformat(),
                )

            self._state = CoordinatorState.READY
            logger.info(f"Runtime coordinator initialized: {self._config.coordinator_id}")
            return True

        except Exception as e:
            logger.error(f"Coordinator initialization failed: {e}")
            self._state = CoordinatorState.ERROR
            return False

    async def start(self) -> bool:
        """Start the coordinator, making it ready to accept executions."""
        if self._state == CoordinatorState.UNINITIALIZED:
            await self.initialize()

        if self._state == CoordinatorState.READY:
            self._state = CoordinatorState.RUNNING
            logger.info("Runtime coordinator started")
            return True

        logger.warning(f"Cannot start coordinator from state {self._state.value}")
        return False

    async def pause(self) -> bool:
        """Pause the coordinator, suspending new executions."""
        if self._state == CoordinatorState.RUNNING:
            self._state = CoordinatorState.PAUSED
            logger.info("Runtime coordinator paused")
            return True
        return False

    async def resume(self) -> bool:
        """Resume the coordinator from paused state."""
        if self._state == CoordinatorState.PAUSED:
            self._state = CoordinatorState.RUNNING
            logger.info("Runtime coordinator resumed")
            return True
        return False

    async def stop(self) -> bool:
        """Gracefully stop the coordinator."""
        self._state = CoordinatorState.STOPPING
        logger.info("Runtime coordinator stopping")
        self._state = CoordinatorState.STOPPED
        return True

    async def shutdown(self):
        """Full shutdown with cleanup."""
        await self.stop()
        self._execution_history.clear()
        self._contexts.clear()
        self._agent_registry.clear()
        logger.info("Runtime coordinator shut down")

    # ── Agent Management ─────────────────────────────────

    def register_agent(self, agent_id: str, agent_name: str, metadata: dict[str, Any] | None = None):
        """Register an agent with the coordinator."""
        self._agent_registry[agent_id] = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "execution_count": 0,
        }
        self._stats.agents_managed = len(self._agent_registry)

    def unregister_agent(self, agent_id: str):
        """Remove an agent from the coordinator."""
        if agent_id in self._agent_registry:
            del self._agent_registry[agent_id]
            self._stats.agents_managed = len(self._agent_registry)

    def get_agent_info(self, agent_id: str) -> dict[str, Any] | None:
        """Get information about a registered agent."""
        return self._agent_registry.get(agent_id)

    # ── Context Assembly ─────────────────────────────────

    async def assemble_context(
        self,
        agent_id: str,
        agent_name: str,
        user_message: str,
        system_prompt: str = "",
        conversation_history: list[dict] | None = None,
        session_id: str = "",
        mode: ExecutionMode = ExecutionMode.DIRECT,
    ) -> ExecutionContext:
        """Assemble a complete execution context from all subsystems.

        Aggregates context from memory, identity, persona, governance,
        and workspace modules to provide a rich context for agent execution.
        """
        context = ExecutionContext(
            agent_id=agent_id,
            agent_name=agent_name,
            user_message=user_message,
            system_prompt=system_prompt or f"You are {agent_name}, a helpful AI assistant.",
            conversation_history=conversation_history or [],
            session_id=session_id or f"session-{uuid.uuid4().hex[:8]}",
            mode=mode,
        )

        # Try to enrich context from available modules
        try:
            from agent.shared import (
                persona_registry, governance_engine, identity_registry,
                workspace_manager, context_manager,
            )

            # Persona context
            if self._config.enable_persona_matching:
                try:
                    persona = persona_registry.match_persona(user_message)
                    if persona:
                        context.persona_context = json.dumps({
                            "name": persona.name,
                            "style": persona.interaction_style.value if persona.interaction_style else "",
                            "traits": persona.traits,
                        })
                except Exception:
                    pass

            # Governance context
            if self._config.enable_governance:
                try:
                    eval_result = governance_engine.evaluate(
                        context={"agent_id": agent_id, "message": user_message},
                        agent_id=agent_id,
                    )
                    context.governance_context = eval_result
                except Exception:
                    pass

            # Identity context
            try:
                profile = identity_registry.get_profile(agent_id)
                if profile:
                    context.identity_context = json.dumps({
                        "traits": profile.get_active_traits(),
                        "preferences": profile.get_preferences(),
                    })
            except Exception:
                pass

        except ImportError:
            pass

        self._contexts[context.context_id] = context
        return context

    # ── Core Execution ───────────────────────────────────

    async def execute(
        self,
        user_message: str,
        agent_id: str = "",
        agent_name: str = "Buddy",
        system_prompt: str = "",
        conversation_history: list[dict] | None = None,
        mode: ExecutionMode = ExecutionMode.DIRECT,
        enable_tools: bool = True,
        enable_reasoning: bool = False,
        session_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a coordinated request through the full agent pipeline.

        This is the primary entry point for agent execution. It assembles
        context, determines the execution mode, routes through the appropriate
        modules, and returns a comprehensive result.
        """
        exec_start = time.time()

        if self._state == CoordinatorState.PAUSED:
            return ExecutionResult(
                content="Coordinator is paused. Please resume to process requests.",
                success=False,
                error="Coordinator paused",
            )

        async with self._lock:
            # Register agent if not already registered
            if agent_id and agent_id not in self._agent_registry:
                self.register_agent(agent_id, agent_name)

            # Assemble context
            context = await self.assemble_context(
                agent_id=agent_id,
                agent_name=agent_name,
                user_message=user_message,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                session_id=session_id,
                mode=mode,
            )

            result = ExecutionResult(
                mode_used=mode,
            )

            try:
                # Route through Unified Brain for perception and cognition
                from agent.agent_unified_brain import BrainContext, BrainMode, unified_brain

                brain_context = BrainContext(
                    user_message=user_message,
                    conversation_history=conversation_history or [],
                    agent_id=agent_id,
                    agent_name=agent_name,
                    system_prompt=system_prompt,
                    session_id=session_id,
                    metadata=metadata or {},
                )

                # Map ExecutionMode to BrainMode
                mode_map = {
                    ExecutionMode.DIRECT: BrainMode.REACTIVE,
                    ExecutionMode.REASONED: BrainMode.DELIBERATIVE,
                    ExecutionMode.COLLABORATIVE: BrainMode.COLLABORATIVE,
                    ExecutionMode.AUTONOMOUS: BrainMode.ANALYTICAL,
                    ExecutionMode.REFLECTIVE: BrainMode.DELIBERATIVE,
                }

                brain_mode = mode_map.get(mode, BrainMode.REACTIVE)

                # Execute through unified brain
                brain_result = await unified_brain.process(brain_context, mode=brain_mode)

                result.brain_cycle = {
                    "cycle_id": brain_result.cycle_id,
                    "mode": brain_result.mode.value,
                    "perception": {
                        "intent": brain_result.perception.intent if brain_result.perception else "",
                        "complexity": brain_result.perception.complexity if brain_result.perception else 0.0,
                    } if brain_result.perception else {},
                    "cognition": {
                        "strategy": brain_result.cognition.reasoning_strategy if brain_result.cognition else "",
                        "confidence": brain_result.cognition.confidence if brain_result.cognition else 0.0,
                    } if brain_result.cognition else {},
                }

                result.content = brain_result.action.content if brain_result.action else ""
                result.success = brain_result.success
                result.error = brain_result.error or ""
                result.tokens_used = brain_result.total_tokens
                result.modules_used.append(ModuleType.BRAIN)

                # If deep reasoning is enabled, enhance with reasoning trace
                if enable_reasoning and brain_result.perception:
                    try:
                        from agent.agent_deep_reasoning import deep_reasoning
                        reasoning_result = await deep_reasoning.reason(
                            query=user_message,
                            strategy="tree_of_thought" if brain_result.perception.complexity > 0.5 else "self_consistency",
                        )
                        result.reasoning_trace = reasoning_result.to_dict()
                        result.modules_used.append(ModuleType.REASONING)
                    except Exception as e:
                        logger.warning(f"Deep reasoning enhancement failed: {e}")

                # Record with platform core
                try:
                    from agent.agent_platform_core import platform_core
                    platform_core.record_request(agent_id, success=result.success)
                    result.modules_used.append(ModuleType.PLATFORM)
                except Exception:
                    pass

                # Update stats
                self._stats.total_executions += 1
                if result.success:
                    self._stats.successful_executions += 1
                else:
                    self._stats.failed_executions += 1

                self._stats.total_tokens += result.tokens_used
                mode_key = mode.value
                self._stats.modes_used[mode_key] = self._stats.modes_used.get(mode_key, 0) + 1

                for module in result.modules_used:
                    mod_key = module.value
                    self._stats.modules_used[mod_key] = self._stats.modules_used.get(mod_key, 0) + 1

                # Update agent registry
                if agent_id in self._agent_registry:
                    self._agent_registry[agent_id]["execution_count"] += 1

            except Exception as e:
                logger.error(f"Coordinated execution failed: {e}")
                result.content = self._fallback_response(user_message)
                result.success = False
                result.error = str(e)
                self._stats.failed_executions += 1

                # Attempt recovery
                if self._config.enable_auto_recovery:
                    await self._attempt_recovery(agent_id, str(e))

            result.total_duration_ms = (time.time() - exec_start) * 1000
            result.timestamp = datetime.now(timezone.utc).isoformat()

            self._stats.total_time_ms += result.total_duration_ms
            self._execution_history.append(result)
            if len(self._execution_history) > 200:
                self._execution_history = self._execution_history[-100:]

            self._stats.uptime_seconds = (
                datetime.now(timezone.utc) - datetime.fromisoformat(self._start_time)
            ).total_seconds() if self._start_time else 0

            return result

    async def execute_stream(
        self,
        user_message: str,
        agent_id: str = "",
        agent_name: str = "Buddy",
        system_prompt: str = "",
        conversation_history: list[dict] | None = None,
        mode: ExecutionMode = ExecutionMode.DIRECT,
        session_id: str = "",
    ) -> AsyncIterator[str]:
        """Execute with streaming output for real-time feedback."""
        from agent.agent_unified_brain import BrainContext, unified_brain

        brain_context = BrainContext(
            user_message=user_message,
            conversation_history=conversation_history or [],
            agent_id=agent_id,
            agent_name=agent_name,
            system_prompt=system_prompt,
            session_id=session_id,
        )

        async for token in unified_brain.process_stream(brain_context):
            yield token

    # ── Multi-Agent Coordination ─────────────────────────

    async def coordinate_agents(
        self,
        task: str,
        agent_ids: list[str],
        mode: ExecutionMode = ExecutionMode.COLLABORATIVE,
    ) -> ExecutionResult:
        """Coordinate multiple agents to collaboratively solve a task."""
        from agent.agent_unified_brain import unified_brain

        brain_result = await unified_brain.coordinate(
            task=task,
            agent_ids=agent_ids,
        )

        result = ExecutionResult(
            content=brain_result.action.content if brain_result.action else "",
            success=brain_result.success,
            error=brain_result.error or "",
            mode_used=ExecutionMode.COLLABORATIVE,
            modules_used=[ModuleType.BRAIN, ModuleType.SESSION],
        )

        # Update stats
        self._stats.total_executions += 1
        if result.success:
            self._stats.successful_executions += 1
        else:
            self._stats.failed_executions += 1

        self._execution_history.append(result)
        return result

    # ── Recovery ─────────────────────────────────────────

    async def _attempt_recovery(self, agent_id: str, error: str):
        """Attempt to recover from a failed execution."""
        if agent_id not in self._recovery_attempts:
            self._recovery_attempts[agent_id] = 0

        self._recovery_attempts[agent_id] += 1
        attempts = self._recovery_attempts[agent_id]

        if attempts > 5:
            logger.warning(f"Too many recovery attempts for {agent_id}, marking as error")
            self._state = CoordinatorState.ERROR
            return

        logger.info(f"Recovery attempt {attempts} for {agent_id}: {error[:100]}")

        # Reset module statuses
        for module_type in ModuleType:
            if module_type in self._modules:
                self._modules[module_type].error_count += 1
                self._modules[module_type].last_heartbeat = datetime.now(timezone.utc).isoformat()

    def _fallback_response(self, message: str) -> str:
        """Generate a fallback response when execution fails."""
        msg_lower = message.lower().strip()
        if any(g in msg_lower for g in ["hello", "hi", "hey"]):
            return "Hello! I'm your Buddy agent. I'm here to help with any task you need."
        if "?" in message:
            return "That's an interesting question. Let me work on providing you with a thoughtful answer. Could you share more details about what you're looking for?"
        return "I received your request. I'm processing it through the Buddy runtime system and will provide you with the best possible response."

    # ── Module Status ────────────────────────────────────

    def update_module_status(self, module_type: ModuleType, is_healthy: bool, metadata: dict[str, Any] | None = None):
        """Update the health status of a module."""
        if module_type in self._modules:
            self._modules[module_type].is_healthy = is_healthy
            self._modules[module_type].last_heartbeat = datetime.now(timezone.utc).isoformat()
            if metadata:
                self._modules[module_type].metadata.update(metadata)

    def get_module_status(self, module_type: ModuleType) -> ModuleStatus | None:
        """Get the status of a specific module."""
        return self._modules.get(module_type)

    def get_all_module_statuses(self) -> dict[str, dict[str, Any]]:
        """Get status of all modules."""
        return {
            mt.value: {
                "is_available": ms.is_available,
                "is_healthy": ms.is_healthy,
                "error_count": ms.error_count,
                "total_calls": ms.total_calls,
                "last_heartbeat": ms.last_heartbeat,
            }
            for mt, ms in self._modules.items()
        }

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive coordinator statistics."""
        self._stats.uptime_seconds = (
            datetime.now(timezone.utc) - datetime.fromisoformat(self._start_time)
        ).total_seconds() if self._start_time else 0

        self._stats.active_agents = sum(
            1 for a in self._agent_registry.values()
            if a.get("execution_count", 0) > 0
        )

        return {
            "coordinator_id": self._config.coordinator_id,
            "state": self._state.value,
            "uptime_seconds": round(self._stats.uptime_seconds, 1),
            "executions": {
                "total": self._stats.total_executions,
                "successful": self._stats.successful_executions,
                "failed": self._stats.failed_executions,
                "success_rate": round(
                    self._stats.successful_executions / max(self._stats.total_executions, 1), 2
                ),
            },
            "tokens": {
                "total": self._stats.total_tokens,
                "avg_per_execution": round(
                    self._stats.total_tokens / max(self._stats.total_executions, 1), 1
                ),
            },
            "modes_used": self._stats.modes_used,
            "modules_used": self._stats.modules_used,
            "agents": {
                "managed": self._stats.agents_managed,
                "active": self._stats.active_agents,
            },
            "modules": self.get_all_module_statuses(),
            "recent_executions": [
                {
                    "result_id": e.result_id,
                    "mode": e.mode_used.value,
                    "success": e.success,
                    "duration_ms": round(e.total_duration_ms, 1),
                    "tokens": e.tokens_used,
                    "timestamp": e.timestamp,
                }
                for e in self._execution_history[-5:]
            ],
            "config": {
                "max_concurrent_agents": self._config.max_concurrent_agents,
                "execution_timeout_ms": self._config.execution_timeout_ms,
                "enable_auto_recovery": self._config.enable_auto_recovery,
                "enable_telemetry": self._config.enable_telemetry,
                "enable_governance": self._config.enable_governance,
            },
        }

    def get_execution_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent execution history."""
        return [
            {
                "result_id": e.result_id,
                "mode": e.mode_used.value,
                "success": e.success,
                "content_preview": e.content[:200],
                "error": e.error[:100] if e.error else "",
                "tokens": e.tokens_used,
                "duration_ms": round(e.total_duration_ms, 1),
                "modules": [m.value for m in e.modules_used],
                "timestamp": e.timestamp,
            }
            for e in self._execution_history[-limit:]
        ]

    def reset(self):
        """Reset all coordinator state."""
        self._execution_history.clear()
        self._contexts.clear()
        self._recovery_attempts.clear()
        self._stats = CoordinatorStats()
        logger.info("Runtime coordinator reset")


# ── Singleton ─────────────────────────────────────────────

runtime_coordinator = RuntimeCoordinator()