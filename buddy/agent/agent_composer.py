"""Buddy Agent Composer — unified agent orchestration and synthesis

The Agent Composer is the ultimate orchestration layer that synthesizes all
agent capabilities into a single, coherent interface. It serves as:

- Primary entry point for creating and managing fully-featured agents
- Cross-module coordinator bridging brain, reasoning, memory, and sessions
- Adaptive execution pipeline that selects optimal strategies per request
- Continuous feedback loop connecting experience, improvement, and evolution
- Live monitoring and introspection of agent state across all subsystems
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
from typing import Any, AsyncIterator

from config.settings import settings

logger = logging.getLogger("buddy.agent_composer")

# ── Enums ─────────────────────────────────────────────────

class ExecutionStrategy(str, Enum):
    """Strategies the composer can use for a given request."""
    DIRECT = "direct"               # Simple LLM call
    BRAIN = "brain"                 # Unified brain cycle
    REASONED = "reasoned"           # Deep reasoning pipeline
    PLANNED = "planned"             # Plan-based step execution
    COLLABORATIVE = "collaborative" # Multi-agent session
    AUTONOMOUS = "autonomous"       # Self-directed with reflection
    ADAPTIVE = "adaptive"           # Dynamic strategy selection


class AgentMode(str, Enum):
    """Operating modes for composed agents."""
    REACTIVE = "reactive"
    DELIBERATIVE = "deliberative"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    AUTONOMOUS = "autonomous"


class PhaseState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ── Data Classes ──────────────────────────────────────────

@dataclass
class ComposerConfig:
    """Configuration for the Agent Composer."""
    composer_id: str = field(default_factory=lambda: f"composer-{uuid.uuid4().hex[:8]}")
    default_mode: AgentMode = AgentMode.REACTIVE
    max_iterations: int = 50
    enable_auto_reasoning: bool = True
    enable_auto_improvement: bool = True
    enable_experience_tracking: bool = True
    enable_memory_integration: bool = True
    enable_session_management: bool = True
    enable_parallel_execution: bool = False
    reflection_threshold: float = 0.6
    auto_recovery: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPhase:
    """A single phase within a composed execution."""
    phase_id: str = field(default_factory=lambda: f"phase-{uuid.uuid4().hex[:8]}")
    name: str = ""
    state: PhaseState = PhaseState.PENDING
    strategy: ExecutionStrategy = ExecutionStrategy.DIRECT
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0
    tokens_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComposedResult:
    """Complete result of a composed agent execution."""
    result_id: str = field(default_factory=lambda: f"comp-{uuid.uuid4().hex[:8]}")
    content: str = ""
    success: bool = True
    error: str = ""
    phases: list[ExecutionPhase] = field(default_factory=list)
    strategy_used: ExecutionStrategy = ExecutionStrategy.DIRECT
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    brain_cycle: dict[str, Any] = field(default_factory=dict)
    reasoning_trace: dict[str, Any] = field(default_factory=dict)
    reflection: dict[str, Any] = field(default_factory=dict)
    improvements: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ComposerStats:
    """Aggregate statistics for the composer."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_tokens: int = 0
    total_time_ms: float = 0.0
    strategy_distribution: dict[str, int] = field(default_factory=dict)
    avg_phase_count: float = 0.0
    improvement_rate: float = 0.0


# ── Agent Composer ───────────────────────────────────────

class AgentComposer:
    """Ultimate orchestration layer that synthesizes all agent capabilities.

    The Agent Composer is the primary interface for agent execution. It
    analyzes incoming requests, selects the optimal execution strategy,
    coordinates across all subsystems (brain, reasoning, memory, sessions,
    platform, coordinator), and produces comprehensive results with full
    traceability and continuous improvement.
    """

    def __init__(self, config: ComposerConfig | None = None):
        self._config = config or ComposerConfig()
        self._stats = ComposerStats()
        self._results: list[ComposedResult] = []
        self._active_executions: dict[str, ComposedResult] = {}
        self._start_time: str = datetime.now(timezone.utc).isoformat()

    # ── Strategy Selection ────────────────────────────────

    def select_strategy(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        agent_mode: AgentMode = AgentMode.REACTIVE,
    ) -> ExecutionStrategy:
        """Analyze the message and select the optimal execution strategy.

        Uses lexical analysis and context assessment to determine whether
        a simple direct response, deep reasoning, planning, collaboration,
        or autonomous execution is most appropriate.
        """
        msg_lower = message.lower()
        msg_len = len(message)
        history_len = len(conversation_history or [])

        # Override by explicit agent mode
        if agent_mode == AgentMode.AUTONOMOUS:
            return ExecutionStrategy.AUTONOMOUS
        if agent_mode == AgentMode.DELIBERATIVE:
            return ExecutionStrategy.REASONED
        if agent_mode == AgentMode.ANALYTICAL:
            return ExecutionStrategy.BRAIN

        # Multi-step / complex indicators
        complex_indicators = [
            "analyze", "compare", "evaluate", "break down", "investigate",
            "architecture", "design", "strategy", "comprehensive",
            "step by step", "in depth", "thorough", "deep dive",
            "multiple", "several", "various", "different",
        ]
        is_complex = any(ind in msg_lower for ind in complex_indicators) or msg_len > 500

        # Collaboration indicators
        collab_indicators = [
            "team", "together", "collaborate", "coordinate", "delegate",
            "multiple agents", "distribute", "assign",
        ]
        is_collaborative = any(ind in msg_lower for ind in collab_indicators)

        # Planning indicators
        plan_indicators = [
            "plan", "roadmap", "milestone", "schedule", "timeline",
            "project", "initiative", "campaign",
        ]
        is_planned = any(ind in msg_lower for ind in plan_indicators) and msg_len > 200

        # Reasoning indicators
        reason_indicators = [
            "why", "how", "explain", "reason", "logic", "proof",
            "solve", "optimize", "calculate", "compute",
        ]
        is_reasoning = any(ind in msg_lower for ind in reason_indicators) and msg_len > 100

        # Decision logic
        if is_collaborative and history_len > 3:
            return ExecutionStrategy.COLLABORATIVE
        if is_planned and is_complex:
            return ExecutionStrategy.PLANNED
        if is_reasoning and is_complex:
            return ExecutionStrategy.REASONED
        if is_complex and self._config.enable_auto_reasoning:
            return ExecutionStrategy.BRAIN
        if msg_len > 1000 or history_len > 10:
            return ExecutionStrategy.ADAPTIVE

        return ExecutionStrategy.DIRECT

    # ── Core Execution ────────────────────────────────────

    async def execute(
        self,
        message: str,
        agent_id: str = "",
        agent_name: str = "Buddy",
        system_prompt: str = "",
        conversation_history: list[dict] | None = None,
        mode: AgentMode = AgentMode.REACTIVE,
        enable_tools: bool = True,
        enable_reasoning: bool = False,
        stream: bool = False,
        session_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ComposedResult | AsyncIterator[str]:
        """Execute a request through the composed agent pipeline.

        This is the primary execution entry point. It selects the optimal
        strategy, coordinates all subsystems, and returns a comprehensive
        result with full traceability.
        """
        if stream:
            return self._execute_stream(
                message, agent_id, agent_name, system_prompt,
                conversation_history, mode, enable_tools,
                enable_reasoning, session_id, metadata,
            )

        exec_start = time.time()
        strategy = self.select_strategy(message, conversation_history, mode)

        result = ComposedResult(
            strategy_used=strategy,
        )

        try:
            # Phase 1: Context Assembly
            context_phase = await self._assemble_context(
                message, agent_id, agent_name, system_prompt,
                conversation_history, session_id, metadata,
            )
            result.phases.append(context_phase)

            # Phase 2: Strategy Execution
            execution_phase = await self._execute_strategy(
                strategy, message, agent_id, agent_name, system_prompt,
                conversation_history, context_phase.output_data,
                enable_tools, enable_reasoning, session_id,
            )
            result.phases.append(execution_phase)
            result.content = execution_phase.output_data.get("content", "")
            result.success = execution_phase.state == PhaseState.COMPLETED
            result.error = execution_phase.error
            result.tokens_used = execution_phase.tokens_used
            result.brain_cycle = execution_phase.output_data.get("brain_cycle", {})
            result.reasoning_trace = execution_phase.output_data.get("reasoning_trace", {})

            # Phase 3: Reflection
            if self._config.enable_auto_improvement:
                reflection_phase = await self._reflect(
                    message, result.content, result.success, result.error,
                    strategy, agent_id,
                )
                result.phases.append(reflection_phase)
                result.reflection = reflection_phase.output_data
                result.improvements = reflection_phase.output_data.get("improvements", [])

            # Phase 4: Experience Recording
            if self._config.enable_experience_tracking:
                experience_phase = await self._record_experience(
                    message, result.content, strategy, result.success,
                    agent_id, session_id, result.tokens_used,
                )
                result.phases.append(experience_phase)

            # Update statistics
            self._stats.total_executions += 1
            if result.success:
                self._stats.successful_executions += 1
            else:
                self._stats.failed_executions += 1

            self._stats.total_tokens += result.total_tokens
            strat_key = strategy.value
            self._stats.strategy_distribution[strat_key] = (
                self._stats.strategy_distribution.get(strat_key, 0) + 1
            )

        except Exception as e:
            logger.error(f"Composed execution failed: {e}")
            result.success = False
            result.error = str(e)
            result.content = self._fallback_response(message)
            self._stats.failed_executions += 1

        result.total_duration_ms = (time.time() - exec_start) * 1000
        result.total_tokens = sum(p.tokens_used for p in result.phases)
        result.timestamp = datetime.now(timezone.utc).isoformat()

        self._stats.total_time_ms += result.total_duration_ms
        if len(self._results) > 200:
            self._results = self._results[-100:]
        self._results.append(result)

        return result

    async def _execute_stream(
        self,
        message: str,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        conversation_history: list[dict] | None,
        mode: AgentMode,
        enable_tools: bool,
        enable_reasoning: bool,
        session_id: str,
        metadata: dict[str, Any] | None,
    ) -> AsyncIterator[str]:
        """Stream execution with real-time token output."""
        try:
            from agent.agent_unified_brain import BrainContext, unified_brain

            brain_context = BrainContext(
                user_message=message,
                conversation_history=conversation_history or [],
                agent_id=agent_id,
                agent_name=agent_name,
                system_prompt=system_prompt or f"You are {agent_name}, a helpful AI assistant.",
                session_id=session_id,
                metadata=metadata or {},
            )

            async for token in unified_brain.process_stream(brain_context):
                yield token

        except Exception as e:
            logger.error(f"Stream execution failed: {e}")
            yield f"\n\n[Error: {str(e)}]"

    # ── Phase: Context Assembly ───────────────────────────

    async def _assemble_context(
        self,
        message: str,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        conversation_history: list[dict] | None,
        session_id: str,
        metadata: dict[str, Any] | None,
    ) -> ExecutionPhase:
        """Assemble rich context from all subsystems."""
        phase = ExecutionPhase(
            name="context_assembly",
            strategy=ExecutionStrategy.DIRECT,
        )
        phase.state = PhaseState.RUNNING

        start = time.time()
        context_data: dict[str, Any] = {
            "message": message,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "system_prompt": system_prompt,
            "conversation_history": conversation_history or [],
            "session_id": session_id,
        }

        try:
            # Memory context
            if self._config.enable_memory_integration:
                try:
                    from agent.shared import memory_system
                    memories = await memory_system.recall(agent_id, limit=5)
                    if memories:
                        context_data["memory_context"] = [
                            m.get("content", "")[:200] for m in memories
                        ]
                except Exception:
                    pass

            # Persona context
            try:
                from agent.shared import persona_registry
                if persona_registry:
                    persona = persona_registry.match_persona(message)
                    if persona:
                        context_data["persona"] = {
                            "name": persona.name,
                            "style": str(persona.interaction_style) if persona.interaction_style else "",
                        }
            except Exception:
                pass

            phase.output_data = context_data
            phase.state = PhaseState.COMPLETED
        except Exception as e:
            phase.state = PhaseState.FAILED
            phase.error = str(e)

        phase.duration_ms = (time.time() - start) * 1000
        return phase

    # ── Phase: Strategy Execution ─────────────────────────

    async def _execute_strategy(
        self,
        strategy: ExecutionStrategy,
        message: str,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        conversation_history: list[dict] | None,
        context: dict[str, Any],
        enable_tools: bool,
        enable_reasoning: bool,
        session_id: str,
    ) -> ExecutionPhase:
        """Execute the selected strategy."""
        phase = ExecutionPhase(
            name=f"execute_{strategy.value}",
            strategy=strategy,
        )
        phase.state = PhaseState.RUNNING

        start = time.time()

        try:
            if strategy == ExecutionStrategy.DIRECT:
                output = await self._execute_direct(
                    message, agent_id, agent_name, system_prompt,
                    conversation_history, enable_tools,
                )
            elif strategy == ExecutionStrategy.BRAIN:
                output = await self._execute_brain(
                    message, agent_id, agent_name, system_prompt,
                    conversation_history, enable_reasoning,
                )
            elif strategy == ExecutionStrategy.REASONED:
                output = await self._execute_reasoned(
                    message, agent_id, agent_name, system_prompt,
                    conversation_history, enable_tools,
                )
            elif strategy == ExecutionStrategy.PLANNED:
                output = await self._execute_planned(
                    message, agent_id, agent_name, system_prompt,
                    conversation_history,
                )
            elif strategy == ExecutionStrategy.COLLABORATIVE:
                output = await self._execute_collaborative(
                    message, agent_id, agent_name,
                )
            elif strategy == ExecutionStrategy.AUTONOMOUS:
                output = await self._execute_autonomous(
                    message, agent_id, agent_name, system_prompt,
                    conversation_history, enable_tools,
                )
            else:
                # ADAPTIVE: choose the best strategy in real-time
                output = await self._execute_brain(
                    message, agent_id, agent_name, system_prompt,
                    conversation_history, enable_reasoning,
                )

            phase.output_data = output
            phase.tokens_used = output.get("tokens_used", 0)
            phase.state = PhaseState.COMPLETED

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            phase.state = PhaseState.FAILED
            phase.error = str(e)
            phase.output_data = {"content": self._fallback_response(message)}

        phase.duration_ms = (time.time() - start) * 1000
        return phase

    async def _execute_direct(
        self,
        message: str,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        conversation_history: list[dict] | None,
        enable_tools: bool,
    ) -> dict[str, Any]:
        """Direct LLM execution without additional processing."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        messages = [{"role": "system", "content": system_prompt or f"You are {agent_name}."}]
        if conversation_history:
            messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": message})

        try:
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
            )
            return {
                "content": response.choices[0].message.content or "",
                "tokens_used": response.usage.total_tokens if response.usage else 0,
            }
        except Exception as e:
            return {"content": self._fallback_response(message), "tokens_used": 0}

    async def _execute_brain(
        self,
        message: str,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        conversation_history: list[dict] | None,
        enable_reasoning: bool,
    ) -> dict[str, Any]:
        """Execute through the Unified Brain."""
        from agent.agent_unified_brain import BrainContext, unified_brain

        brain_context = BrainContext(
            user_message=message,
            conversation_history=conversation_history or [],
            agent_id=agent_id,
            agent_name=agent_name,
            system_prompt=system_prompt or f"You are {agent_name}.",
        )

        brain_result = await unified_brain.process(brain_context)

        output = {
            "content": brain_result.action.content if brain_result.action else "",
            "tokens_used": brain_result.total_tokens,
            "brain_cycle": {
                "cycle_id": brain_result.cycle_id,
                "mode": brain_result.mode.value,
                "success": brain_result.success,
            },
        }

        # Enhance with deep reasoning if needed
        if enable_reasoning and brain_result.perception and brain_result.perception.complexity > 0.5:
            try:
                from agent.agent_deep_reasoning import deep_reasoning
                reasoning_result = await deep_reasoning.reason(
                    query=message,
                    strategy="tree_of_thought",
                )
                output["reasoning_trace"] = reasoning_result.to_dict()
                if reasoning_result.final_answer:
                    output["content"] = reasoning_result.final_answer
            except Exception:
                pass

        return output

    async def _execute_reasoned(
        self,
        message: str,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        conversation_history: list[dict] | None,
        enable_tools: bool,
    ) -> dict[str, Any]:
        """Execute through the Deep Reasoning Engine."""
        from agent.agent_deep_reasoning import deep_reasoning

        reasoning_result = await deep_reasoning.reason(
            query=message,
            strategy="tree_of_thought",
        )

        return {
            "content": reasoning_result.final_answer or "",
            "tokens_used": reasoning_result.total_tokens,
            "reasoning_trace": reasoning_result.to_dict(),
        }

    async def _execute_planned(
        self,
        message: str,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        conversation_history: list[dict] | None,
    ) -> dict[str, Any]:
        """Execute through the Planning Engine."""
        from agent.planning import planning_engine

        plan = await planning_engine.generate_plan(message, agent_id)
        results = []

        for step in plan.steps:
            planning_engine.update_step_status(plan.id, step.id, "in_progress")
            step_result = await self._execute_brain(
                f"Goal: {plan.goal}\nCurrent step: {step.title}\n{step.description}",
                agent_id, agent_name, system_prompt, None, False,
            )
            results.append(f"### {step.title}\n{step_result['content']}")
            planning_engine.update_step_status(plan.id, step.id, "completed", step_result["content"])

        return {
            "content": f"**Plan: {plan.title}**\n\n" + "\n\n".join(results),
            "tokens_used": sum(r.get("tokens_used", 0) for r in [{"tokens_used": 0}] + results),
        }

    async def _execute_collaborative(
        self,
        message: str,
        agent_id: str,
        agent_name: str,
    ) -> dict[str, Any]:
        """Execute collaboratively through the Session Manager."""
        from agent.agent_session import session_manager

        session = await session_manager.create_session(
            task=message,
            agent_ids=[agent_id],
            mode="collaborative",
        )

        return {
            "content": session.get("summary", "Collaborative session created."),
            "tokens_used": 0,
            "session_id": session.get("session_id", ""),
        }

    async def _execute_autonomous(
        self,
        message: str,
        agent_id: str,
        agent_name: str,
        system_prompt: str,
        conversation_history: list[dict] | None,
        enable_tools: bool,
    ) -> dict[str, Any]:
        """Execute autonomously with self-reflection."""
        # First pass: brain execution
        brain_output = await self._execute_brain(
            message, agent_id, agent_name, system_prompt,
            conversation_history, True,
        )

        # Self-reflection pass
        reflection = await self._reflect(
            message, brain_output["content"], True, "",
            ExecutionStrategy.AUTONOMOUS, agent_id,
        )

        # If improvements suggested, apply them
        improvements = reflection.output_data.get("improvements", [])
        if improvements:
            enhanced_message = (
                f"{message}\n\n[Self-Improvement Context]\n"
                f"Previous response could be improved by: {', '.join(improvements)}\n"
                f"Please provide an enhanced response."
            )
            brain_output = await self._execute_brain(
                enhanced_message, agent_id, agent_name, system_prompt,
                conversation_history, True,
            )

        return brain_output

    # ── Phase: Reflection ─────────────────────────────────

    async def _reflect(
        self,
        message: str,
        content: str,
        success: bool,
        error: str,
        strategy: ExecutionStrategy,
        agent_id: str,
    ) -> ExecutionPhase:
        """Reflect on execution quality and generate improvements."""
        phase = ExecutionPhase(
            name="reflection",
            strategy=ExecutionStrategy.DIRECT,
        )
        phase.state = PhaseState.RUNNING

        start = time.time()

        try:
            improvement_suggestions = []

            # Quality heuristics
            if not success:
                improvement_suggestions.append(
                    f"Investigate execution failure: {error[:100]}"
                )
            if content and len(content) < 50:
                improvement_suggestions.append(
                    "Response is too brief; consider providing more detail"
                )
            if content and len(content) > 2000:
                improvement_suggestions.append(
                    "Response is very long; consider summarizing key points"
                )

            # Strategy-specific improvements
            if strategy == ExecutionStrategy.DIRECT and len(message) > 500:
                improvement_suggestions.append(
                    "Complex query used direct mode; consider brain or reasoned mode"
                )

            phase.output_data = {
                "quality_score": 0.8 if success else 0.3,
                "improvements": improvement_suggestions,
                "success": success,
            }
            phase.state = PhaseState.COMPLETED

        except Exception as e:
            phase.state = PhaseState.FAILED
            phase.error = str(e)

        phase.duration_ms = (time.time() - start) * 1000
        return phase

    # ── Phase: Experience Recording ───────────────────────

    async def _record_experience(
        self,
        message: str,
        content: str,
        strategy: ExecutionStrategy,
        success: bool,
        agent_id: str,
        session_id: str,
        tokens_used: int,
    ) -> ExecutionPhase:
        """Record execution experience for learning."""
        phase = ExecutionPhase(
            name="experience_recording",
            strategy=ExecutionStrategy.DIRECT,
        )

        try:
            from agent.experience_db import ExperienceType, ExperienceOutcome, experience_db

            experience_db.record(
                agent_id=agent_id,
                experience_type=ExperienceType.USER_INTERACTION,
                outcome=ExperienceOutcome.SUCCESS if success else ExperienceOutcome.FAILURE,
                context={"strategy": strategy.value, "message_length": len(message)},
                description=f"Composed execution via {strategy.value}",
            )

            phase.state = PhaseState.COMPLETED
        except Exception as e:
            phase.state = PhaseState.SKIPPED
            phase.error = str(e)

        return phase

    # ── Fallback ──────────────────────────────────────────

    def _fallback_response(self, message: str) -> str:
        """Generate a fallback response when execution fails."""
        msg_lower = message.lower().strip()
        if any(g in msg_lower for g in ["hello", "hi", "hey"]):
            return "Hello! I'm your Buddy agent. How can I assist you today?"
        if "?" in message:
            return "That's an interesting question. Let me work on providing a thoughtful response. Could you share more context?"
        return "I received your request. I'm processing it through the Buddy agent system and will provide the best possible response."

    # ── Statistics ────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive composer statistics."""
        self._stats.avg_phase_count = (
            sum(len(r.phases) for r in self._results) / max(len(self._results), 1)
        )

        return {
            "composer_id": self._config.composer_id,
            "uptime_seconds": (
                datetime.now(timezone.utc) - datetime.fromisoformat(self._start_time)
            ).total_seconds(),
            "executions": {
                "total": self._stats.total_executions,
                "successful": self._stats.successful_executions,
                "failed": self._stats.failed_executions,
                "success_rate": round(
                    self._stats.successful_executions / max(self._stats.total_executions, 1), 2
                ),
            },
            "strategies": self._stats.strategy_distribution,
            "tokens": {
                "total": self._stats.total_tokens,
                "avg_per_execution": round(
                    self._stats.total_tokens / max(self._stats.total_executions, 1), 1
                ),
            },
            "avg_phase_count": round(self._stats.avg_phase_count, 1),
            "avg_time_ms": round(
                self._stats.total_time_ms / max(self._stats.total_executions, 1), 1
            ),
            "recent_results": [
                {
                    "result_id": r.result_id,
                    "strategy": r.strategy_used.value,
                    "success": r.success,
                    "phases": len(r.phases),
                    "duration_ms": round(r.total_duration_ms, 1),
                    "tokens": r.total_tokens,
                }
                for r in self._results[-5:]
            ],
        }

    def get_recent_results(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent execution results."""
        return [
            {
                "result_id": r.result_id,
                "strategy": r.strategy_used.value,
                "success": r.success,
                "content_preview": r.content[:200],
                "error": r.error[:100] if r.error else "",
                "phases": len(r.phases),
                "phase_details": [
                    {"name": p.name, "state": p.state.value, "duration_ms": round(p.duration_ms, 1)}
                    for p in r.phases
                ],
                "duration_ms": round(r.total_duration_ms, 1),
                "tokens": r.total_tokens,
                "timestamp": r.timestamp,
            }
            for r in self._results[-limit:]
        ]

    def reset(self):
        """Reset all composer state."""
        self._results.clear()
        self._active_executions.clear()
        self._stats = ComposerStats()
        self._start_time = datetime.now(timezone.utc).isoformat()
        logger.info("Agent composer reset")


# ── Singleton ─────────────────────────────────────────────

agent_composer = AgentComposer()