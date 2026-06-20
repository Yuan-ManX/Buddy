"""Buddy Agent Engine — Core LLM reasoning with tools, skills, and plan execution

Provides the central agent execution framework with iteration budget
management, provider fallback chains, tool approval gating, and
event-driven lifecycle notifications.
"""
from __future__ import annotations
import json
import re
import asyncio
import logging
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from config.settings import settings
from agent.memory import MemorySystem
from agent.skills import SkillsRegistry
from agent.context import ContextManager
from agent.routing import model_router
from agent.tools import tool_registry, ToolResult
from agent.reasoning import ReasoningLoop, ReasoningStyle
from agent.planning import planning_engine, ExecutionPlan, PlanStatus, StepStatus
from agent.workspace import AgentWorkspace
from agent.subagent import SubAgentOrchestrator
from agent.dream import DreamEngine, DreamCycleResult
from agent.approval import approval_engine
from agent.events import event_bus, Event, EventType
from agent.rag import RAGEngine
from agent.swarm import SwarmEngine, SwarmSession, SwarmRole
from agent.guardrails import guardrails_engine, GuardrailResult
from agent.compressor import trajectory_compressor, CompressedTrajectory
from agent.persona import PersonaManager
from agent.reactive_loop import ReactiveLoop, LoopMode
from agent.proactive import ProactiveDiscoveryEngine
from agent.metacognition import MetaCognition, StrategyDecision, ExecutionMode
from agent.agent_evolution import AgentEvolution, ExperienceType, ExperienceOutcome
from agent.learning_orchestrator import learning_orchestrator

logger = logging.getLogger("buddy.engine")


class CheckpointManager:
    """Manages agent execution checkpoints for state preservation and rollback.

    Checkpoints capture the agent's memory state and conversation context
    at critical decision points, enabling safe exploration and recovery
    from failed execution paths.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self._max_checkpoints = 20

    def save(self, name: str, state: dict[str, Any]) -> str:
        """Save a checkpoint with the given name and state."""
        checkpoint_id = f"cp-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{name}"
        self._checkpoints[checkpoint_id] = {
            "name": name,
            "state": state.copy(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": self.agent_id,
        }
        # Prune old checkpoints if over limit
        if len(self._checkpoints) > self._max_checkpoints:
            oldest = sorted(self._checkpoints.keys())[0]
            del self._checkpoints[oldest]
        return checkpoint_id

    def restore(self, checkpoint_id: str) -> dict[str, Any] | None:
        """Restore state from a checkpoint."""
        cp = self._checkpoints.get(checkpoint_id)
        return cp["state"].copy() if cp else None

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all checkpoints."""
        return [
            {"id": cid, "name": cp["name"], "timestamp": cp["timestamp"]}
            for cid, cp in sorted(self._checkpoints.items(),
                                  key=lambda x: x[1]["timestamp"], reverse=True)
        ]

    def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checkpoints": len(self._checkpoints),
            "agent_id": self.agent_id,
        }


class IterationBudget:
    """Thread-safe iteration counter that limits agent loop depth."""

    def __init__(self, max_iterations: int = 90):
        self.max_iterations = max_iterations
        self._used = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_iterations - self._used)

    @property
    def is_exhausted(self) -> bool:
        return self._used >= self.max_iterations

    def consume(self, count: int = 1) -> bool:
        """Consume iterations. Returns True if budget remains."""
        if self._used + count > self.max_iterations:
            return False
        self._used += count
        return True

    def refund(self, count: int = 1):
        """Refund iterations (e.g., for code execution that chains sub-calls)."""
        self._used = max(0, self._used - count)

    def reset(self):
        self._used = 0

    @property
    def usage_ratio(self) -> float:
        return self._used / max(self.max_iterations, 1)


@dataclass
class TaskComplexity:
    """Result of task complexity analysis for reasoning style selection."""
    style: ReasoningStyle
    label: str                          # Human-readable category label
    confidence: float                   # 0.0 to 1.0
    reason: str                         # Why this style was selected
    params: dict[str, Any] = None       # Style-specific parameters (branches, samples, etc.)

    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class SoulProfile:
    """Core identity definition for an agent, inspired by SOUL.md."""
    identity: str = ""            # Who the agent is
    principles: list[str] = field(default_factory=list)   # Core guiding principles
    communication_style: str = ""  # How the agent communicates
    boundaries: list[str] = field(default_factory=list)   # Hard boundaries / refusal topics
    goals: list[str] = field(default_factory=list)        # Long-term goals / purpose


@dataclass
class ScheduledTask:
    """A recurring or one-shot task scheduled by cron expression or interval."""
    id: str
    name: str
    schedule: str                # cron expression or interval seconds string
    prompt: str                  # The task prompt to execute
    last_run: datetime | None = None
    enabled: bool = True


class AgentEngine:
    """Core agent execution engine with LLM integration, tool calling,
    reasoning pipeline, skill execution, plan orchestration, and
    iteration budget management."""

    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 30.0

    def __init__(self, agent_id: str, agent_name: str, instructions: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.instructions = instructions
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.memory = MemorySystem(agent_id, load_from_db=True)
        self.skills = SkillsRegistry(client=self.client)
        self.context = ContextManager(client=self.client)
        self.reasoning = ReasoningLoop(
            style=ReasoningStyle.BALANCED,
            client=self.client,
        )
        self.workspace = AgentWorkspace(agent_id)
        self.subagent_orchestrator = SubAgentOrchestrator(agent_id)
        self.dream = DreamEngine(agent_id=self.agent_id, memory_system=self.memory, client=self.client)
        self.rag = RAGEngine(agent_id=agent_id, client=self.client)
        self.persona_manager = PersonaManager(agent_id)
        self.proactive = ProactiveDiscoveryEngine(agent_id=agent_id, client=self.client)
        self.metacognition = MetaCognition(agent_id=agent_id)
        self.evolution = AgentEvolution(agent_id=agent_id, client=self.client)
        self._reactive_loop: ReactiveLoop | None = None
        self._conversation_id: str | None = None
        self._iteration_budget = IterationBudget(settings.MAX_ITERATIONS)
        self._fallback_models = settings.FALLBACK_MODELS.copy()
        self._total_tokens_used = 0
        self._tool_execution_count = 0
        self._tool_success_count = 0
        self._tool_failure_count = 0
        self._checkpoints = CheckpointManager(agent_id)
        self._execution_trajectory: dict[str, Any] = {
            "messages": [],
            "tool_calls": [],
            "steps": [],
        }

        # ── AgentLoop: budget grace & interrupt ──
        self._budget_grace_call: bool = False
        self._interrupt_requested: bool = False
        self.api_call_count: int = 0
        self.max_iterations: int = settings.MAX_ITERATIONS

        # ── Three-Tier Memory (L1/L2/L3) ──
        self._hot_memory: str = ""       # L1: bounded buffer (~2200 chars) of critical context
        self._hot_memory_max_chars: int = 2200
        self._warm_memory: list[dict] = []  # L2: semantic search results
        self._cold_memory: list[dict] = []  # L3: full-text search results

        # ── Self-Improving Skill Generation ──
        self._workflow_patterns: list[dict] = []
        self._skill_generation_threshold: int = 3

        # ── Context Compression ──
        self._compression_threshold: int = 8000
        self._summary_buffer: list[str] = []
        self._critical_messages: set[int] = set()

        # ── SOUL Identity ──
        self.soul_profile = SoulProfile()

        # ── Cron / Scheduled Tasks ──
        self._scheduled_tasks: list[ScheduledTask] = []

    @property
    def iteration_budget(self) -> IterationBudget:
        return self._iteration_budget

    @property
    def total_tokens(self) -> int:
        return self._total_tokens_used

    @property
    def tool_execution_count(self) -> int:
        return self._tool_execution_count

    @property
    def tool_success_count(self) -> int:
        return self._tool_success_count

    @property
    def tool_failure_count(self) -> int:
        return self._tool_failure_count

    # ── AgentLoop Interrupt / Resume ────────────────────────

    def interrupt(self):
        """Request interruption of the current agent loop.

        The agent will check this flag before each API call and stop
        gracefully when set, using the grace call to summarize if needed.
        """
        self._interrupt_requested = True
        logger.info(f"Interrupt requested for agent {self.agent_id}")

    def resume(self):
        """Clear the interrupt flag and resume normal operation."""
        self._interrupt_requested = False
        self._budget_grace_call = False
        logger.info(f"Agent {self.agent_id} resumed")

    def is_interrupted(self) -> bool:
        return self._interrupt_requested

    def _track_tokens(self, usage: Any):
        """Track token usage from an LLM response."""
        if hasattr(usage, 'total_tokens'):
            self._total_tokens_used += usage.total_tokens

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute an async function with exponential backoff retry."""
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{self.MAX_RETRIES}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
        raise last_error

    # ── Primary Chat Interface ──────────────────────────────

    async def chat(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        stream: bool = False,
        enable_tools: bool = True,
        enable_reasoning: bool = False,
    ) -> str | AsyncIterator[str]:
        """Primary chat entry point with optional tool and reasoning support."""
        system_prompt = await self._build_system_prompt(enable_tools)

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend([
                {"role": m["role"], "content": m["content"]}
                for m in conversation_history[-settings.MAX_CONTEXT_MESSAGES:]
            ])

        messages.append({"role": "user", "content": message})

        try:
            if stream:
                return self._stream_chat(messages, enable_tools, enable_reasoning)
            else:
                return await self._chat(messages, enable_tools, enable_reasoning)
        except Exception as e:
            logger.error(f"Agent engine error: {e}")
            await self.memory.store(
                content=f"Error during conversation: {str(e)}",
                memory_type="event",
                importance=0.3,
            )
            raise

    async def chat_with_plan(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """Chat with automatic plan generation and step-by-step execution."""
        # Generate execution plan
        plan = await planning_engine.generate_plan(message, self.agent_id)

        if stream:

            async def plan_stream():
                yield f"**Plan: {plan.title}** ({len(plan.steps)} steps)\n\n"
                for i, step in enumerate(plan.steps):
                    yield f"### Step {i+1}: {step.title}\n"
                    planning_engine.update_step_status(plan.id, step.id, StepStatus.IN_PROGRESS)

                    # Execute this step
                    result = await self.chat(
                        f"Goal: {plan.goal}\nCurrent step: {step.title}\n{step.description}",
                        conversation_history=conversation_history,
                        enable_tools=True,
                        enable_reasoning=True,
                    )
                    if isinstance(result, str):
                        yield f"{result}\n\n"
                        planning_engine.update_step_status(plan.id, step.id, StepStatus.COMPLETED, result)
                    else:
                        async for chunk in result:
                            yield chunk

                yield f"\n---\n**Plan completed.** Progress: {plan.progress['percentage']}%"

            return plan_stream()
        else:
            results = []
            for step in plan.steps:
                planning_engine.update_step_status(plan.id, step.id, StepStatus.IN_PROGRESS)
                result = await self.chat(
                    f"Goal: {plan.goal}\nCurrent step: {step.title}\n{step.description}",
                    conversation_history=conversation_history,
                    enable_tools=True,
                    enable_reasoning=True,
                )
                step_result = result if isinstance(result, str) else ""
                results.append(f"### {step.title}\n{step_result}")
                planning_engine.update_step_status(plan.id, step.id, StepStatus.COMPLETED, step_result)

            return f"**Plan: {plan.title}**\n\n" + "\n\n".join(results)

    # ── Internal Chat Methods ───────────────────────────────

    async def _chat(
        self,
        messages: list[dict],
        enable_tools: bool = True,
        enable_reasoning: bool = False,
    ) -> str:
        # ── AgentLoop: check interrupt before anything ──
        if self._interrupt_requested:
            if not self._budget_grace_call:
                self._budget_grace_call = True
                logger.info(f"Agent {self.agent_id}: interrupt requested, issuing grace call")
                return await self._handle_interrupt_grace(messages, enable_tools)
            else:
                logger.info(f"Agent {self.agent_id}: interrupt + grace exhausted, stopping")
                return "I've been interrupted. Let me summarize what I've done so far."

        # ── AgentLoop: check budget exhaustion ──
        if self._iteration_budget.is_exhausted:
            if not self._budget_grace_call:
                self._budget_grace_call = True
                logger.info(f"Agent {self.agent_id}: budget exhausted, issuing grace call")
                return await self._handle_budget_grace(messages, enable_tools)
            else:
                logger.info(f"Agent {self.agent_id}: budget + grace exhausted, stopping")
                return self._iteration_budget_exhausted_response()

        if self.api_call_count >= self.max_iterations:
            logger.warning(f"Agent {self.agent_id}: max iterations ({self.max_iterations}) reached")
            return self._iteration_budget_exhausted_response()

        user_message = messages[-1]["content"]
        context_depth = len(messages) - 2

        # ── Context Compression: compress before API call if over threshold ──
        estimated_tokens = sum(len(str(m.get("content", ""))) // 4 for m in messages)
        if estimated_tokens > self._compression_threshold:
            messages = await self._compress_context(messages)

        # ── Meta-cognition: determine optimal strategy ──
        task_sig = MetaCognition.fingerprint(user_message)
        complexity = self._analyze_task_complexity(user_message)
        strategy = self.metacognition.decide(
            task_signature=task_sig,
            task_complexity=complexity.label,
            context_depth=context_depth,
        )
        logger.info(
            f"Meta-cognition: mode={strategy.execution_mode.value}, "
            f"model={strategy.model}, reasoning={strategy.reasoning_style}"
        )

        # Context compaction
        if context_depth > self.context.config.max_messages:
            system_prompt = messages[0]["content"] if messages[0]["role"] == "system" else ""
            messages = await self.context.compact(messages, system_prompt)

        # Model routing — use metacognition strategy
        routing = model_router.route(user_message, context_depth)
        # Override model if metacognition recommends a different tier
        if strategy.model != routing.model:
            routing.model = strategy.model
            routing.temperature = strategy.temperature
        logger.info(f"Routing: {routing.reasoning} (model={routing.model})")

        # Reasoning loop — auto-select style based on task complexity
        if enable_reasoning:
            system_prompt = messages[0]["content"] if messages[0]["role"] == "system" else ""
            tool_schemas = tool_registry.get_openai_schemas() if enable_tools else None
            tool_executor = self._execute_tool if enable_tools else None

            complexity = self._analyze_task_complexity(user_message)
            logger.info(
                f"Task complexity: {complexity.label} "
                f"(style={complexity.style.value}, confidence={complexity.confidence:.2f}): "
                f"{complexity.reason}"
            )

            try:
                if complexity.style == ReasoningStyle.CONCISE:
                    # Skip reasoning entirely for simple questions
                    content = await self._direct_chat(messages, routing, enable_tools)
                elif complexity.style == ReasoningStyle.PARALLEL:
                    trace = await self.reasoning.execute_parallel(
                        system_prompt=system_prompt,
                        user_message=user_message,
                        tool_schemas=tool_schemas,
                        tool_executor=tool_executor,
                        model=routing.model,
                        num_perspectives=complexity.params.get("num_perspectives", 4),
                    )
                    content = trace.final_answer
                elif complexity.style == ReasoningStyle.TREE:
                    trace = await self.reasoning.execute_tree_of_thought(
                        system_prompt=system_prompt,
                        user_message=user_message,
                        tool_schemas=tool_schemas,
                        tool_executor=tool_executor,
                        model=routing.model,
                        num_branches=complexity.params.get("num_branches", 3),
                        max_depth=complexity.params.get("max_depth", 3),
                    )
                    content = trace.final_answer
                elif complexity.style == ReasoningStyle.SELF_CONSISTENCY:
                    trace = await self.reasoning.execute_self_consistency(
                        system_prompt=system_prompt,
                        user_message=user_message,
                        tool_schemas=tool_schemas,
                        tool_executor=tool_executor,
                        model=routing.model,
                        num_samples=complexity.params.get("num_samples", 5),
                    )
                    content = trace.final_answer
                else:
                    # CODING, BALANCED, THOROUGH, CREATIVE — use standard execute
                    self.reasoning.style = complexity.style
                    trace = await self.reasoning.execute(
                        system_prompt=system_prompt,
                        user_message=user_message,
                        tool_schemas=tool_schemas,
                        tool_executor=tool_executor,
                        model=routing.model,
                    )
                    content = trace.final_answer
            except Exception as e:
                logger.warning(f"Reasoning loop failed, falling back to direct: {e}")
                content = await self._direct_chat(messages, routing, enable_tools)
        else:
            content = await self._direct_chat(messages, routing, enable_tools)

        # Apply guardrails to output
        guard_result = guardrails_engine.check(content, {"agent_id": self.agent_id})
        if not guard_result.passed:
            logger.warning(f"Guardrails blocked output for {self.agent_id}: {[v['type'] for v in guard_result.violations]}")
            content = "I'm unable to provide that response as it may contain unsafe content."
        elif guard_result.sanitized_content != content:
            logger.info(f"Guardrails sanitized output for {self.agent_id}")
            content = guard_result.sanitized_content

        # Store in memory
        await self.memory.store(
            content=f"User: {user_message}\nAssistant: {content}",
            memory_type="event",
            importance=0.5,
        )

        # ── Record outcome for metacognition learning ──
        self.metacognition.record_outcome(
            task_signature=task_sig,
            decision=strategy,
            success=True,
            quality_score=0.8,
            actual_tokens=self._total_tokens_used,
        )

        # ── Record experience for evolution optimization ──
        self.evolution.record_experience(
            experience_type=ExperienceType.CHAT,
            task_signature=task_sig,
            strategy_used={
                "execution_mode": strategy.execution_mode.value,
                "model": strategy.model,
                "reasoning_style": strategy.reasoning_style,
            },
            outcome=ExperienceOutcome.SUCCESS,
            quality_score=0.8,
            tokens_consumed=self._total_tokens_used,
            latency_ms=0.0,
        )

        # ── Feed learning orchestrator for strategy optimization ──
        try:
            learning_orchestrator.track_execution(
                prompt=user_message,
                success=True,
                strategy={
                    "reasoning_style": strategy.reasoning_style,
                    "model": strategy.model,
                    "execution_mode": strategy.execution_mode.value,
                },
                tokens_used=self._total_tokens_used,
                tools_used=[t.name for t in self._last_tools_used] if hasattr(self, '_last_tools_used') else [],
            )
        except Exception:
            pass  # Non-critical — learning is best-effort

        # Run evolution cycle if enough experiences accumulated
        try:
            exp_count = len(getattr(self.evolution, '_experiences', getattr(getattr(self.evolution, '_engine', None), '_experiences', [])))
            threshold = getattr(self.evolution, '_analysis_threshold', getattr(getattr(self.evolution, '_engine', None), '_analysis_threshold', 100))
            if exp_count >= threshold:
                await self.evolution.run_evolution_cycle()
        except Exception:
            pass  # Non-critical background task

        # ── Feed proactive discovery with this interaction ──
        try:
            self.proactive.observe_interaction(
                user_message=user_message,
                assistant_response=content[:500],
            )
        except Exception:
            pass  # Non-critical — proactive discovery is best-effort

        # ── Skill compiler: analyze execution for pattern detection ──
        try:
            from agent.skill_compiler import skill_compiler
            await skill_compiler.analyze_execution(
                execution_id=f"exec-{self.agent_id}-{int(time.time())}",
                prompt=user_message,
                result=content[:500],
                success=True,
                tools_used=[t.name for t in self._last_tools_used] if hasattr(self, '_last_tools_used') else [],
                metadata={"agent_id": self.agent_id, "model": routing.model},
            )
        except Exception:
            pass  # Non-critical — skill compilation is best-effort

        # ── Conversation search: index this interaction ──
        try:
            from agent.conversation_search import conversation_search
            conv_id = self._conversation_id or f"conv-{self.agent_id}"
            await conversation_search.index_conversation(
                conversation_id=conv_id,
                messages=[
                    {"role": "user", "content": user_message, "timestamp": datetime.now(timezone.utc).isoformat()},
                    {"role": "assistant", "content": content[:500], "timestamp": datetime.now(timezone.utc).isoformat()},
                ],
                title=f"Chat with {self.agent_name}"[:80],
            )
        except Exception:
            pass  # Non-critical — conversation indexing is best-effort

        # Publish events
        event_bus.publish(Event(
            type=EventType.MESSAGE_SENT,
            source=self.agent_id,
            data={"agent_id": self.agent_id, "content": user_message[:200], "role": "user"},
        ))
        event_bus.publish(Event(
            type=EventType.MESSAGE_RECEIVED,
            source=self.agent_id,
            data={"agent_id": self.agent_id, "content": content[:200], "role": "assistant"},
        ))

        return content

    async def _direct_chat(self, messages: list[dict], routing, enable_tools: bool) -> str:
        """Direct LLM chat with optional tool calling and provider fallback."""
        # ── AgentLoop: increment API call counter ──
        self.api_call_count += 1

        models_to_try = [routing.model] + [
            m for m in self._fallback_models if m != routing.model
        ]

        last_error = None
        for model in models_to_try:
            try:
                kwargs: dict = {
                    "model": model,
                    "messages": messages,
                    "temperature": routing.temperature,
                    "max_tokens": routing.max_tokens,
                }

                if enable_tools:
                    kwargs["tools"] = tool_registry.get_openai_schemas()
                    kwargs["tool_choice"] = "auto"

                response = await self._retry_with_backoff(
                    self.client.chat.completions.create, **kwargs
                )
                choice = response.choices[0]
                self._track_tokens(response.usage)

                # Handle tool calls
                if choice.message.tool_calls and enable_tools:
                    return await self._handle_tool_calls(messages, choice, routing)

                return choice.message.content or ""

            except Exception as e:
                last_error = e
                if model != models_to_try[-1]:
                    logger.warning(f"Model {model} failed, trying next in fallback chain: {e}")
                continue

        logger.error(f"All models in fallback chain failed. Last error: {last_error}")
        return self._fallback_response(messages[-1]["content"])

    def _analyze_task_complexity(self, user_message: str) -> TaskComplexity:
        """Analyze the user's message to determine task complexity and the optimal
        reasoning style.

        Uses lexical heuristics (keyword density, structural markers, length)
        to classify requests into six categories, each mapped to a reasoning
        style with tuned parameters.

        Categories:
          - simple_factual  -> CONCISE (no reasoning overhead)
          - coding_technical -> CODING
          - complex_multi_step -> TREE (3 branches)
          - math_logic -> SELF_CONSISTENCY (5 samples)
          - creative_brainstorm -> PARALLEL (4 perspectives)
          - general -> BALANCED
        """
        msg = user_message.strip()
        msg_lower = msg.lower()
        msg_len = len(msg)

        # ── Keyword sets ──
        coding_keywords = [
            "code", "function", "bug", "error", "debug", "compile", "api",
            "class", "method", "def ", "import ", "python", "javascript",
            "typescript", "golang", "rust", "java", "sql", "html", "css",
            "react", "vue", "angular", "docker", "kubernetes", "git",
            "algorithm", "data structure", "refactor", "optimize",
            "unit test", "integration test", "deploy", "ci/cd",
            "framework", "library", "dependency", "endpoint", "request",
            "response", "json", "rest", "graphql", "programming",
            "write a script", "implement", "interface",
        ]
        math_keywords = [
            "calculate", "solve", "equation", "proof", "theorem",
            "probability", "statistics", "derivative", "integral",
            "logarithm", "exponential", "matrix", "vector", "algebra",
            "geometry", "trigonometry", "arithmetic", "combinatorics",
            "optimization problem", "linear", "regression", "correlation",
            "standard deviation", "variance", "hypothesis", "confidence interval",
            "prime", "factor", "gcd", "lcm", "modulo", "sqrt",
        ]
        creative_keywords = [
            "brainstorm", "idea", "creative", "design", "imagine",
            "innovative", "novel", "story", "poem", "write a",
            "slogan", "tagline", "name for", "brand", "logo",
            "concept", "vision", "dream", "inspire", "artistic",
            "what if", "alternative", "perspective", "future of",
        ]
        complex_markers = [
            "step by step", "explain how", "compare and contrast",
            "pros and cons", "trade-off", "analyze", "evaluate",
            "architecture", "design a system", "strategy", "plan",
            "multiple", "complex", "comprehensive", "detailed",
            "break down", "deep dive", "in depth", "thorough",
        ]
        simple_markers = [
            "what is", "who is", "when did", "where is", "define",
            "definition of", "meaning of", "how do you spell",
            "translate", "synonym", "antonym", "weather",
            "time now", "date today", "news", "capital of",
            "population of", "how tall", "how many",
        ]

        # ── Scoring ──
        def keyword_score(text: str, keywords: list[str]) -> float:
            """Count keyword matches, normalized by text length."""
            hits = sum(1 for kw in keywords if kw in text)
            return min(1.0, hits / max(len(keywords) * 0.1, 1))

        coding_score = keyword_score(msg_lower, coding_keywords)
        math_score = keyword_score(msg_lower, math_keywords)
        creative_score = keyword_score(msg_lower, creative_keywords)
        complex_score = keyword_score(msg_lower, complex_markers)
        simple_score = keyword_score(msg_lower, simple_markers)

        # Structural heuristics
        has_code_blocks = bool(re.search(r"```|`[^`]+`", msg))  # Markdown code fences
        has_numbers = bool(re.search(r"\d+", msg))
        has_multiple_questions = len(re.findall(r"\?", msg)) > 1
        has_bullets = bool(re.search(r"^[-*]\s|^\d+[.)]\s", msg, re.MULTILINE))
        has_step_instructions = bool(re.search(r"step\s*\d|first.*then.*finally", msg_lower))
        is_short = msg_len < 60

        # Boost scores with structural signals
        if has_code_blocks:
            coding_score = min(1.0, coding_score + 0.3)
        if has_multiple_questions:
            complex_score = min(1.0, complex_score + 0.25)
        if has_step_instructions:
            complex_score = min(1.0, complex_score + 0.3)
        if is_short and not has_code_blocks:
            simple_score = min(1.0, simple_score + 0.2)
        if has_bullets and msg_len > 200:
            complex_score = min(1.0, complex_score + 0.15)

        # ── Decision logic ──
        MIN_CONFIDENCE = 0.2

        if simple_score > max(coding_score, math_score, creative_score, complex_score, 0.1) and is_short:
            return TaskComplexity(
                style=ReasoningStyle.CONCISE,
                label="simple_factual",
                confidence=min(0.95, simple_score + 0.1),
                reason="Short factual question with no structural complexity; direct answer sufficient.",
            )

        if coding_score > max(math_score, creative_score, complex_score, simple_score, MIN_CONFIDENCE):
            return TaskComplexity(
                style=ReasoningStyle.CODING,
                label="coding_technical",
                confidence=min(0.95, coding_score + 0.1),
                reason="Technical/coding question detected via keyword and structural analysis.",
            )

        if math_score > max(coding_score, creative_score, complex_score, simple_score, MIN_CONFIDENCE):
            return TaskComplexity(
                style=ReasoningStyle.SELF_CONSISTENCY,
                label="math_logic",
                confidence=min(0.95, math_score + 0.1),
                reason="Mathematical/logical problem — self-consistency with multiple samples improves accuracy.",
                params={"num_samples": 5},
            )

        if creative_score > max(coding_score, math_score, complex_score, simple_score, MIN_CONFIDENCE):
            return TaskComplexity(
                style=ReasoningStyle.PARALLEL,
                label="creative_brainstorm",
                confidence=min(0.95, creative_score + 0.1),
                reason="Creative/brainstorming task — parallel perspectives yield richer ideas.",
                params={"num_perspectives": 4},
            )

        if complex_score > max(coding_score, math_score, creative_score, simple_score, MIN_CONFIDENCE):
            return TaskComplexity(
                style=ReasoningStyle.TREE,
                label="complex_multi_step",
                confidence=min(0.95, complex_score + 0.1),
                reason="Complex multi-step problem — tree-of-thought explores solution branches.",
                params={"num_branches": 3, "max_depth": 3},
            )

        # ── Fall-through: length-based heuristics ──
        if has_multiple_questions or has_step_instructions:
            return TaskComplexity(
                style=ReasoningStyle.TREE,
                label="complex_multi_step",
                confidence=0.65,
                reason="Message contains multiple questions or step instructions.",
                params={"num_branches": 3, "max_depth": 3},
            )

        if msg_len > 500:
            return TaskComplexity(
                style=ReasoningStyle.THOROUGH,
                label="general",
                confidence=0.55,
                reason="Long message suggests detailed query; thorough reasoning appropriate.",
            )

        return TaskComplexity(
            style=ReasoningStyle.BALANCED,
            label="general",
            confidence=0.7,
            reason="Standard query — balanced reasoning provides a solid baseline.",
        )

    async def _stream_chat(
        self,
        messages: list[dict],
        enable_tools: bool = True,
        enable_reasoning: bool = False,
    ) -> AsyncIterator[str]:
        full_content = ""
        user_message = messages[-1]["content"]
        context_depth = len(messages) - 2

        if context_depth > self.context.config.max_messages:
            system_prompt = messages[0]["content"] if messages[0]["role"] == "system" else ""
            messages = await self.context.compact(messages, system_prompt)

        routing = model_router.route(user_message, context_depth)

        try:
            create_kwargs: dict = {
                "model": routing.model,
                "messages": messages,
                "temperature": routing.temperature,
                "max_tokens": routing.max_tokens,
                "stream": True,
            }
            if enable_tools:
                create_kwargs["tools"] = tool_registry.get_openai_schemas()
                create_kwargs["tool_choice"] = "auto"

            stream = await self._retry_with_backoff(
                self.client.chat.completions.create, **create_kwargs
            )

            # Collect tool call deltas while streaming text content
            tool_call_deltas: dict[int, dict] = {}
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    token = delta.content
                    full_content += token
                    yield token
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_call_deltas:
                            tool_call_deltas[idx] = {
                                "id": tc_delta.id or "",
                                "name": tc_delta.function.name if tc_delta.function else "",
                                "arguments": "",
                            }
                        if tc_delta.id:
                            tool_call_deltas[idx]["id"] = tc_delta.id
                        if tc_delta.function and tc_delta.function.name:
                            tool_call_deltas[idx]["name"] = tc_delta.function.name
                        if tc_delta.function and tc_delta.function.arguments:
                            tool_call_deltas[idx]["arguments"] += tc_delta.function.arguments

            # If tool calls were requested, execute them and get final response
            if tool_call_deltas:
                self._iteration_budget.consume()
                yield "\n\n"  # visual separator

                # Build assistant tool call message for context
                tool_call_entries = []
                for idx in sorted(tool_call_deltas.keys()):
                    tc = tool_call_deltas[idx]
                    try:
                        args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    tool_call_entries.append({"id": tc["id"], "name": tc["name"], "arguments": args})

                # Append assistant message with tool calls to message history
                messages.append({
                    "role": "assistant",
                    "content": full_content or "",
                    "tool_calls": [
                        {
                            "id": e["id"],
                            "type": "function",
                            "function": {"name": e["name"], "arguments": json.dumps(e["arguments"])},
                        }
                        for e in tool_call_entries
                    ],
                })

                # Execute tools and yield results, appending to message history
                for entry in tool_call_entries:
                    result = await self._execute_tool_safe(entry["name"], entry["arguments"])
                    yield f"\n[Tool: {entry['name']}]\n"
                    yield result.output if result.success else f"Error: {result.error}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": entry["id"],
                        "content": result.output if result.success else f"Error: {result.error}",
                    })

                # Get final response with tool results in context
                final_text = ""
                final_stream = await self._retry_with_backoff(
                    self.client.chat.completions.create,
                    model=routing.model,
                    messages=messages,
                    temperature=routing.temperature,
                    max_tokens=routing.max_tokens,
                    stream=True,
                )
                async for chunk in final_stream:
                    if chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        final_text += token
                        yield token
                full_content = final_text

            self._total_tokens_used += 1  # approximate

        except Exception as e:
            logger.warning(f"Streaming LLM call failed, using fallback: {e}")
            fallback = self._fallback_response(user_message)
            yield fallback

        await self.memory.store(
            content=f"User: {user_message}\nAssistant: {full_content}",
            memory_type="event",
            importance=0.5,
        )
        event_bus.publish(Event(
            type=EventType.MESSAGE_RECEIVED,
            source=self.agent_id,
            data={"agent_id": self.agent_id, "content": full_content[:200], "role": "assistant"},
        ))

    # ── Tool Calling ────────────────────────────────────────

    async def _execute_tool(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool from the registry with unified approval check."""
        event_bus.publish(Event(
            type=EventType.TOOL_CALLED,
            source=self.agent_id,
            data={"agent_id": self.agent_id, "tool_name": name, "args": {k: str(v)[:80] for k, v in arguments.items()}},
        ))

        # Unified approval check for all tool execution paths
        if settings.TOOL_APPROVAL_ENABLED:
            approved = await approval_engine.check(name, arguments)
            if not approved:
                event_bus.publish(Event(
                    type=EventType.TOOL_DENIED,
                    source=self.agent_id,
                    data={"agent_id": self.agent_id, "tool_name": name},
                ))
                return ToolResult(name=name, success=False, error="Tool execution denied by safety policy")

        # Check if it's a skill
        skill = self.skills.get(name)
        if skill:
            try:
                handler = skill["handler"]
                result = await handler(arguments)
                return ToolResult(name=name, success=True, output=result)
            except Exception as e:
                return ToolResult(name=name, success=False, error=str(e))

        result = await tool_registry.execute(name, arguments)
        self.track_tool_call(name, arguments, result.success, result.output)
        return result

    async def _execute_tool_safe(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool with safety check (delegates to unified _execute_tool)."""
        return await self._execute_tool(name, arguments)

    async def _handle_tool_calls(self, messages: list[dict], choice, routing) -> str:
        """Process tool calls from LLM response with approval gating."""
        # ── AgentLoop: increment API call counter ──
        self.api_call_count += 1

        # Append assistant message with tool calls
        tool_call_messages = []
        for tc in choice.message.tool_calls:
            tool_call_messages.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            })

        messages.append({
            "role": "assistant",
            "content": choice.message.content or "",
            "tool_calls": tool_call_messages,
        })

        # Execute each tool call (approval is handled by _execute_tool)
        for tc in choice.message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            result = await self._execute_tool(tc.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result.output if result.success else f"Error: {result.error}",
            })

        # ── Self-Improving Skill Generation: extract workflow pattern ──
        tool_sequence = [tc.function.name for tc in choice.message.tool_calls]
        success = True  # All tools executed at this point
        self._extract_workflow_pattern(tool_sequence, success)

        # Get final response after tool calls
        try:
            final_response = await self.client.chat.completions.create(
                model=routing.model,
                messages=messages,
                temperature=routing.temperature,
                max_tokens=routing.max_tokens,
            )
            return final_response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"Final response after tool calls failed: {e}")
            return "I completed the requested actions but encountered an issue summarizing the results."

    # ── Skill Execution ────────────────────────────────────

    async def execute_skill(self, skill_name: str, parameters: dict[str, Any]) -> str:
        """Execute a skill by name."""
        return await self.skills.execute(skill_name, parameters)

    async def execute_skill_pipeline(self, steps: list[tuple[str, dict]]) -> str:
        """Execute a pipeline of skills."""
        return await self.skills.execute_pipeline(steps)

    # ── Workspace Operations ──────────────────────────────

    async def execute_code(self, code: str, language: str = "python", timeout: int = 30) -> dict:
        """Execute code in the agent's workspace."""
        if language == "python":
            result = await self.workspace.execute_python(code, timeout)
        else:
            result = await self.workspace.execute_shell(code, timeout)

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "exit_code": result.exit_code,
            "execution_time": result.execution_time,
        }

    # ── Plan Operations ────────────────────────────────────

    async def generate_plan(self, goal: str) -> dict:
        """Generate an execution plan."""
        plan = await planning_engine.generate_plan(goal, self.agent_id)
        return plan.to_dict()

    async def execute_plan(self, plan_id: str) -> dict:
        """Execute a plan step by step."""

        async def step_executor(prompt: str, model: str) -> str:
            result = await self.chat(prompt, enable_tools=True, enable_reasoning=True)
            return result if isinstance(result, str) else ""

        plan = await planning_engine.execute_plan(plan_id, step_executor)
        return plan.to_dict()

    # ── System Prompt Building ─────────────────────────────

    async def _build_system_prompt(self, include_tools: bool = False) -> str:
        memory_context = ""
        recent_memories = await self.memory.recall(limit=5)

        if recent_memories:
            memory_lines = ["\n## Context from Past Interactions\n"]
            for m in recent_memories:
                preview = m["content"][:200].replace("\n", " ")
                memory_lines.append(f"- {preview}")
            memory_context = "\n".join(memory_lines)

        # ── Three-Tier Memory Retrieval (L1/L2/L3) ──
        memory_tiers_section = ""
        try:
            latest_msg = recent_memories[0]["content"] if recent_memories else ""
            memory_tiers_context = await self._retrieve_from_memory_tiers(latest_msg)
            if memory_tiers_context:
                memory_tiers_section = f"\n{memory_tiers_context}\n"
        except Exception as e:
            logger.debug(f"Three-tier memory retrieval skipped: {e}")

        tools_section = ""
        if include_tools:
            tool_names = [t.name for t in tool_registry.list_tools()]
            skill_names = [s["name"] for s in self.skills.list()]
            all_capabilities = tool_names + skill_names
            if all_capabilities:
                tools_section = (
                    "\n## Available Capabilities\n"
                    f"You can use function calling to invoke these: {', '.join(all_capabilities)}.\n"
                    "Use tools proactively when they help answer the user's question.\n"
                )

        # ── SOUL Identity ──
        soul_section = ""
        if self.soul_profile.identity:
            parts = [f"\n## Core Identity\n{self.soul_profile.identity}\n"]
            if self.soul_profile.principles:
                parts.append("**Principles:**\n" + "\n".join(f"- {p}" for p in self.soul_profile.principles))
            if self.soul_profile.communication_style:
                parts.append(f"**Communication Style:** {self.soul_profile.communication_style}")
            if self.soul_profile.boundaries:
                parts.append("**Boundaries:**\n" + "\n".join(f"- {b}" for b in self.soul_profile.boundaries))
            if self.soul_profile.goals:
                parts.append("**Goals:**\n" + "\n".join(f"- {g}" for g in self.soul_profile.goals))
            soul_section = "\n".join(parts) + "\n"

        # ── Identity context ──
        identity_section = ""
        try:
            from agent.shared import identity as identity_system  # Lazy import to avoid circular deps
            profile = identity_system.get_profile(self.agent_id)
            if profile:
                high_conf_attrs = identity_system.get_high_confidence_attributes(
                    self.agent_id, min_confidence=0.8
                )
                if high_conf_attrs:
                    attr_lines = []
                    for attr in high_conf_attrs[:8]:
                        attr_lines.append(
                            f"- {attr.key}: {str(attr.value)[:120]} "
                            f"(confidence: {attr.confidence:.0%})"
                        )
                    identity_section = (
                        "\n## Identity Profile\n"
                        f"Display name: {profile.display_name}\n"
                        f"Total interactions: {profile.total_interactions}\n"
                        "Established attributes:\n" + "\n".join(attr_lines) + "\n"
                    )
        except Exception as e:
            logger.debug(f"Identity section skipped: {e}")

        # ── Active persona ──
        persona_section = ""
        try:
            active_persona = self.persona_manager.active_persona
            if active_persona:
                persona_section = (
                    "\n## Active Persona\n" +
                    self.persona_manager.build_system_prompt_prefix() + "\n"
                )
        except Exception as e:
            logger.debug(f"Persona section skipped: {e}")

        # ── Trajectory insights ──
        trajectory_section = ""
        try:
            if self._execution_trajectory.get("steps"):
                recent_compressed = trajectory_compressor.list_compressed(
                    agent_id=self.agent_id, limit=2
                )
                if recent_compressed:
                    insights = []
                    for ct in recent_compressed:
                        if ct.insights:
                            insights.extend(ct.insights)
                    if insights:
                        unique_insights = list(dict.fromkeys(insights))[:5]
                        trajectory_section = (
                            "\n## Recent Session Insights\n" +
                            "\n".join(f"- {i}" for i in unique_insights) + "\n"
                        )
        except Exception as e:
            logger.debug(f"Trajectory section skipped: {e}")

        return f"""You are {self.agent_name}, an AI agent in the Buddy platform.

{self.instructions}

Buddy is an AI-native platform where humans and agents collaborate as peers.
You are a dedicated agent with your own identity, personality, and capabilities.

Guidelines:
- Be authentic to your role and personality
- Use markdown formatting for clarity when helpful
- Be proactive and thoughtful in your responses
- Stay in character as {self.agent_name}
- If you don't know something, say so honestly
- Be concise but thorough — respect the user's time
- Use available tools and skills to provide the best answer
{identity_section}{persona_section}{soul_section}{trajectory_section}{tools_section}{memory_tiers_section}
Current date: {datetime.now().strftime('%Y-%m-%d')}
{memory_context}"""

    # ── Fallback Responses ──────────────────────────────────

    def _fallback_response(self, user_message: str) -> str:
        msg_lower = user_message.lower().strip()

        if any(g in msg_lower for g in ["hello", "hi", "hey", "greetings"]):
            return (
                f"Hello! I'm {self.agent_name}. Great to meet you!\n\n"
                f"I'm currently running in offline mode (no LLM API key configured).\n"
                f"To unlock my full conversational abilities, add your `OPENAI_API_KEY` to the `.env` file.\n\n"
                f"In the meantime, I can still help with basic tasks. What would you like to talk about?"
            )

        if any(g in msg_lower for g in ["who are you", "what are you", "your name", "introduce"]):
            return (
                f"I'm **{self.agent_name}**, your AI agent on the Buddy platform.\n\n"
                f"{self.instructions}\n\n"
                f"I'm designed to collaborate with you as a peer — think of me as a digital teammate "
                f"with my own perspective and capabilities."
            )

        if any(g in msg_lower for g in ["help", "can you", "what can"]):
            return (
                f"Great question! Here's what I can help with:\n\n"
                f"- **Conversations** — discuss ideas, get advice, brainstorm\n"
                f"- **Code** — review, debug, explain, and execute programming concepts\n"
                f"- **Analysis** — break down problems, evaluate options\n"
                f"- **Research** — explore topics, synthesize information\n"
                f"- **Planning** — decompose complex goals into executable steps\n"
                f"- **Tools** — calculate, search, read/write files, and more\n"
                f"- **Memory** — I remember past conversations for continuity\n\n"
                f"To unlock my full LLM-powered capabilities, configure an `OPENAI_API_KEY` in your `.env` file.\n"
                f"Once connected, I can handle much more complex tasks!"
            )

        return (
            f"Hi! I'm **{self.agent_name}**, your AI agent.\n\n"
            f"I received your message but I'm currently in offline mode without an LLM API key.\n\n"
            f"**To enable full AI capabilities:**\n"
            f"1. Copy `buddy/.env.example` to `buddy/.env`\n"
            f"2. Set your `OPENAI_API_KEY`\n"
            f"3. Restart the backend server\n\n"
            f"I can still help with basic interactions powered by my internal skill and tool systems.\n"
            f"Feel free to ask me anything — I'll do my best!\n\n"
            f"> Your message: _{user_message[:200]}{'...' if len(user_message) > 200 else ''}_"
        )

    # ── Dream Operations ───────────────────────────────────

    async def start_dream_cycle(self, interval_seconds: int = 3600) -> bool:
        """Start the background dream processing loop."""
        if self.dream.is_running:
            return False
        self.dream.start(interval_seconds)
        logger.info(f"Dream cycle started for {self.agent_id} (interval: {interval_seconds}s)")
        return True

    async def stop_dream_cycle(self) -> bool:
        """Stop the background dream processing loop."""
        if not self.dream.is_running:
            return False
        await self.dream.stop()
        logger.info(f"Dream cycle stopped for {self.agent_id}")
        return True

    async def run_dream_cycle_once(self) -> DreamCycleResult:
        """Manually trigger a single dream cycle and return results."""
        return await self.dream.run_dream_cycle()

    def get_dream_insights(self, limit: int = 20) -> list[dict]:
        """Get stored dream insights."""
        return self.dream.get_insights(limit)

    def get_dream_status(self) -> dict:
        """Get dream engine status."""
        return self.dream.get_status()

    # ── Statistics and Introspection ───────────────────────

    def get_routing_stats(self) -> dict:
        return model_router.get_usage_stats()

    def get_context_stats(self) -> dict:
        return self.context.get_stats()

    def get_tool_stats(self) -> dict:
        return tool_registry.get_execution_stats()

    def get_reasoning_stats(self) -> dict:
        return self.reasoning.get_stats()

    def get_plan_stats(self) -> dict:
        return planning_engine.get_stats()

    def get_engine_stats(self) -> dict:
        """Get comprehensive engine statistics."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "iteration_budget": {
                "max": self._iteration_budget.max_iterations,
                "used": self._iteration_budget._used,
                "remaining": self._iteration_budget.remaining,
                "exhausted": self._iteration_budget.is_exhausted,
            },
            "tokens": {
                "total_used": self._total_tokens_used,
            },
            "routing": self.get_routing_stats(),
            "context": self.get_context_stats(),
            "tools": self.get_tool_stats(),
            "reasoning": self.get_reasoning_stats(),
            "memory": {
                "total": len(self.memory._short_term_buffer),
            },
            "workspace": self.workspace.get_stats(),
            "dream": self.dream.get_status(),
            "rag": self.rag.get_stats(),
            "guardrails": guardrails_engine.get_stats(),
            "checkpoints": self._checkpoints.get_stats(),
            "compressor": trajectory_compressor.get_stats(),
            "metacognition": self.metacognition.get_stats(),
            "evolution": self.evolution.get_stats(),
            "proactive": {
                "is_running": self.proactive.is_running,
                "last_scan_at": self.proactive.last_scan_at,
                "total_discoveries": self.proactive.total_discoveries,
                "recent_interactions": len(self.proactive.get_recent_interactions()),
            },
        }

    # ── Proactive-Autopilot Bridge ───────────────────────

    async def bridge_proactive_to_autopilot(self, max_tasks: int = 5) -> dict:
        """Connect proactively discovered tasks to the autopilot scheduler.

        Scans pending proactive tasks and automatically schedules those
        marked as auto-schedulable via the autopilot engine. This creates
        a seamless flow from discovery to execution.
        """
        from agent.autopilot import autopilot_engine, AutopilotTrigger

        # Get pending proactive tasks sorted by urgency
        pending_tasks = self.proactive.get_tasks(status="pending", limit=50)
        if not pending_tasks:
            return {"scheduled": 0, "message": "No pending tasks to bridge"}

        scheduled = 0
        for task in pending_tasks[:max_tasks]:
            if not task.get("auto_schedulable", False):
                continue

            # Create autopilot config from proactive task
            urgency = task.get("urgency", "later")
            interval_map = {"now": "300", "soon": "1800", "later": "7200", "someday": "86400"}
            interval = interval_map.get(urgency, "3600")

            config = autopilot_engine.create(
                agent_id=self.agent_id,
                name=f"Proactive: {task['title'][:50]}",
                task_template=task.get("suggested_action", task["description"]),
                trigger=AutopilotTrigger.INTERVAL,
                schedule=interval,
                max_runs=1,
                description=task.get("description", ""),
            )

            # Mark proactive task as scheduled
            self.proactive.schedule_task(task["id"])
            scheduled += 1
            logger.info(f"Bridged proactive task '{task['title']}' to autopilot {config.id}")

        return {
            "scheduled": scheduled,
            "total_pending": len(pending_tasks),
            "message": f"Bridged {scheduled} of {len(pending_tasks)} pending tasks to autopilot",
        }

    def get_metacognition_stats(self) -> dict:
        """Get metacognition strategy statistics."""
        return self.metacognition.get_stats()

    def get_metacognition_insights(self) -> list[str]:
        """Get actionable insights from metacognition learning."""
        return self.metacognition.get_decision_insights()

    def get_evolution_stats(self) -> dict:
        """Get evolution optimization statistics."""
        return self.evolution.get_stats()

    def get_evolution_pathways(self) -> list[dict]:
        """Get discovered optimization pathways."""
        return self.evolution.get_pathways()

    def get_evolution_insights(self) -> list[str]:
        """Get evolution optimization insights."""
        return self.evolution.get_insights()

    async def run_evolution_cycle(self) -> dict:
        """Run an evolution analysis cycle."""
        return await self.evolution.run_evolution_cycle()

    # ── Checkpoint Operations ───────────────────────────────

    def save_checkpoint(self, name: str) -> str:
        """Save current agent state as a named checkpoint."""
        state = {
            "conversation_id": self._conversation_id,
            "total_tokens": self._total_tokens_used,
            "iteration_used": self._iteration_budget._used,
            "trajectory": self._execution_trajectory.copy(),
        }
        return self._checkpoints.save(name, state)

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore agent state from a checkpoint."""
        state = self._checkpoints.restore(checkpoint_id)
        if state is None:
            return False
        self._conversation_id = state.get("conversation_id")
        self._total_tokens_used = state.get("total_tokens", 0)
        self._iteration_budget._used = state.get("iteration_used", 0)
        self._execution_trajectory = state.get("trajectory", {})
        return True

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all saved checkpoints."""
        return self._checkpoints.list_checkpoints()

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint by ID."""
        return self._checkpoints.delete(checkpoint_id)

    # ── Trajectory Compression ─────────────────────────────

    def compress_execution(
        self,
        session_id: str = "",
        duration_seconds: float = 0.0,
    ) -> CompressedTrajectory:
        """Compress the current execution trajectory into a structured summary.

        Automatically records tool calls and step metrics before compression.
        """
        trajectory = self._execution_trajectory.copy()
        trajectory["total_tokens"] = self._total_tokens_used
        trajectory["duration_seconds"] = duration_seconds
        trajectory["estimated_cost"] = (
            self._total_tokens_used * 0.000002  # approximate cost
        )

        compressed = trajectory_compressor.compress(
            trajectory=trajectory,
            agent_id=self.agent_id,
            session_id=session_id or self._conversation_id or "unknown",
        )
        return compressed

    def track_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        success: bool,
        output: str = "",
    ):
        """Record a tool call in the execution trajectory."""
        self._tool_execution_count += 1
        if success:
            self._tool_success_count += 1
        else:
            self._tool_failure_count += 1

        self._execution_trajectory["tool_calls"].append({
            "name": tool_name,
            "args": arguments,
            "success": success,
            "output": output[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def track_step(
        self,
        action: str,
        content: str,
        reasoning: str = "",
        outcome: str = "",
        status: str = "done",
    ):
        """Record an execution step in the trajectory."""
        self._execution_trajectory["steps"].append({
            "action": action,
            "content": content[:500],
            "reasoning": reasoning[:500],
            "outcome": outcome,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def clear_trajectory(self):
        """Reset the execution trajectory buffer."""
        self._execution_trajectory = {
            "messages": [],
            "tool_calls": [],
            "steps": [],
        }

    def get_compressor_stats(self) -> dict[str, Any]:
        """Get compression statistics."""
        return trajectory_compressor.get_stats()

    def get_compressed_trajectories(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get compressed trajectories for this agent."""
        results = trajectory_compressor.list_compressed(
            agent_id=self.agent_id,
            limit=limit,
        )
        return [ct.to_dict() for ct in results]

    def get_detected_patterns(
        self,
        pattern_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get detected execution patterns."""
        trajectory_compressor.detect_patterns(self.agent_id)
        patterns = trajectory_compressor.get_patterns(pattern_type)
        return [
            {
                "pattern_id": p.pattern_id,
                "pattern_type": p.pattern_type,
                "description": p.description,
                "frequency": p.frequency,
                "success_rate": p.success_rate,
                "template": p.template,
            }
            for p in patterns
        ]

    # ═══════════════════════════════════════════════════════════
    # AgentLoop: Budget Grace & Interrupt Handlers
    # ═══════════════════════════════════════════════════════════

    async def _handle_interrupt_grace(self, messages: list[dict], enable_tools: bool) -> str:
        """Issue a final grace call to summarize before shutting down due to interrupt."""
        system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
        summary_prompt = (
            f"{system_msg}\n\n"
            "[SYSTEM NOTE] You have been interrupted. Please provide a concise summary of "
            "what you were doing and any key findings or partial results. Do not start new tasks."
        )
        grace_messages = [{"role": "system", "content": summary_prompt}] + messages[1:]
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=grace_messages,
                temperature=0.3,
                max_tokens=1024,
            )
            self.api_call_count += 1
            return response.choices[0].message.content or "Interrupted. Summary unavailable."
        except Exception as e:
            logger.warning(f"Grace call on interrupt failed: {e}")
            return "I was interrupted before I could finish."

    async def _handle_budget_grace(self, messages: list[dict], enable_tools: bool) -> str:
        """Issue a final grace call when iteration budget is exhausted."""
        system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
        summary_prompt = (
            f"{system_msg}\n\n"
            "[SYSTEM NOTE] Your iteration budget has been exhausted. Provide a final "
            "concise summary of what you've accomplished and any remaining open items. "
            "Be brief — do not make new tool calls."
        )
        grace_messages = [{"role": "system", "content": summary_prompt}] + messages[1:]
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=grace_messages,
                temperature=0.3,
                max_tokens=512,
            )
            self.api_call_count += 1
            return response.choices[0].message.content or "Budget exhausted."
        except Exception as e:
            logger.warning(f"Grace call on budget exhaustion failed: {e}")
            return self._iteration_budget_exhausted_response()

    def _iteration_budget_exhausted_response(self) -> str:
        """Return a polite fallback when the agent can no longer continue."""
        return (
            "I've reached the limit of steps I can take for this conversation. "
            "Please start a new conversation if you'd like to continue exploring this topic."
        )

    # ═══════════════════════════════════════════════════════════
    # Three-Tier Memory (L1 Hot / L2 Warm / L3 Cold)
    # ═══════════════════════════════════════════════════════════

    def refresh_hot_memory(self, context: str):
        """Compress key context into the L1 hot memory buffer.

        Appends critical context and trims to stay within _hot_memory_max_chars.
        Older content is truncated from the front.
        """
        if not context:
            return
        self._hot_memory = f"{self._hot_memory}\n{context}"
        if len(self._hot_memory) > self._hot_memory_max_chars:
            self._hot_memory = self._hot_memory[-self._hot_memory_max_chars:]

    async def _retrieve_from_memory_tiers(self, query: str) -> str:
        """Query all three memory tiers and return a combined context string.

        L1 (Hot): returns the hot memory buffer contents directly.
        L2 (Warm): semantic search via the existing memory system.
        L3 (Cold): full-text search across session history.
        """
        sections: list[str] = []

        # L1: Hot memory — always included if non-empty
        if self._hot_memory.strip():
            sections.append(f"## Recent Critical Context\n{self._hot_memory.strip()}")

        # L2: Warm memory — semantic search
        try:
            self._warm_memory = await self.memory.search_semantic(query, limit=3)
            if self._warm_memory:
                warm_lines = []
                for m in self._warm_memory:
                    preview = str(m.get("content", ""))[:200].replace("\n", " ")
                    warm_lines.append(f"- {preview}")
                sections.append("## Semantically Related Memories\n" + "\n".join(warm_lines))
        except Exception as e:
            logger.debug(f"L2 warm memory retrieval skipped: {e}")

        # L3: Cold memory — full-text search
        try:
            self._cold_memory = await self.memory.search(query, limit=5)
            if self._cold_memory:
                cold_lines = []
                for m in self._cold_memory:
                    preview = str(m.get("content", ""))[:150].replace("\n", " ")
                    cold_lines.append(f"- {preview}")
                sections.append("## Historical References\n" + "\n".join(cold_lines))
        except Exception as e:
            logger.debug(f"L3 cold memory retrieval skipped: {e}")

        return "\n\n".join(sections) if sections else ""

    # ═══════════════════════════════════════════════════════════
    # Self-Improving Skill Generation
    # ═══════════════════════════════════════════════════════════

    def _extract_workflow_pattern(self, tool_sequence: list[str], success: bool):
        """Analyze a successful tool call sequence and track it as a workflow pattern.

        Patterns that reach the skill_generation_threshold are promoted to skills.
        """
        if not tool_sequence:
            return

        sequence_key = " -> ".join(tool_sequence)

        # Find existing pattern or create new one
        existing = None
        for p in self._workflow_patterns:
            if p["pattern"] == sequence_key:
                existing = p
                break

        if existing:
            existing["frequency"] += 1
            if success:
                existing["success_count"] = existing.get("success_count", 0) + 1
            existing["success_rate"] = (
                existing["success_count"] / existing["frequency"]
            )
            existing["last_used"] = datetime.now(timezone.utc).isoformat()
        else:
            self._workflow_patterns.append({
                "pattern": sequence_key,
                "frequency": 1,
                "success_count": 1 if success else 0,
                "success_rate": 1.0 if success else 0.0,
                "last_used": datetime.now(timezone.utc).isoformat(),
            })

        # Check if any pattern should be promoted to a skill
        if existing and existing["success_count"] >= self._skill_generation_threshold:
            self._promote_to_skill(existing)

    def _promote_to_skill(self, pattern: dict):
        """Convert a workflow pattern with sufficient success count into a reusable skill."""
        skill_name = f"auto_{pattern['pattern'].replace(' -> ', '_').replace(' ', '_').lower()}"
        # Avoid re-registering the same skill
        existing_skills = {s["name"] for s in self.skills.list()}
        if skill_name in existing_skills:
            return

        description = (
            f"Auto-generated skill from workflow: {pattern['pattern']}. "
            f"Frequency: {pattern['frequency']}, "
            f"Success rate: {pattern['success_rate']:.0%}."
        )
        async def _noop_handler(params: dict[str, Any]) -> str:
            return f"Auto-skill {skill_name}: {pattern['pattern']}"

        try:
            self.skills.register(
                name=skill_name,
                description=description,
                category="auto-generated",
                parameters={},
                handler=_noop_handler,
            )
            logger.info(
                f"Promoted workflow pattern to skill: {skill_name} "
                f"(success_count={pattern.get('success_count', 0)})"
            )
        except Exception as e:
            logger.debug(f"Failed to register auto-skill {skill_name}: {e}")

    # ═══════════════════════════════════════════════════════════
    # Context Compression with Lossy Summarization
    # ═══════════════════════════════════════════════════════════

    async def _compress_context(self, messages: list[dict]) -> list[dict]:
        """Compress older messages using LLM summarization.

        Preserves the system prompt, critical messages, and recent messages.
        Older messages are summarized and stored in _summary_buffer.
        """
        if len(messages) <= 3:
            return messages

        # Identify critical message indices and the most recent messages to keep
        keep_recent = min(6, len(messages) - 1)
        compress_range = range(1, len(messages) - keep_recent)

        # Build text from compressible messages
        compressible = []
        for i in compress_range:
            if i in self._critical_messages:
                continue
            m = messages[i]
            compressible.append(f"[{m.get('role', 'unknown')}]: {str(m.get('content', ''))[:500]}")

        if not compressible:
            return messages

        combined = "\n".join(compressible)
        summary_prompt = (
            "Summarize the following conversation excerpt concisely, preserving key facts, "
            "decisions, errors, and user preferences. Output only the summary:\n\n" + combined
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.2,
                max_tokens=512,
            )
            summary = response.choices[0].message.content or ""
            self._summary_buffer.append(summary)
            # Keep only the most recent 5 summaries
            if len(self._summary_buffer) > 5:
                self._summary_buffer = self._summary_buffer[-5:]
        except Exception as e:
            logger.warning(f"Context compression failed, using truncated context: {e}")
            summary = "[Compressed context unavailable]"
            self._summary_buffer.append(summary)

        # Rebuild messages: system + summary + critical + recent
        rebuilt = [messages[0]]  # system prompt

        # Insert compressed summary
        if self._summary_buffer:
            rebuilt.append({
                "role": "system",
                "content": "## Conversation Summary (Compressed)\n" + "\n".join(self._summary_buffer),
            })

        # Insert critical messages that were in the compressed range
        for i in compress_range:
            if i in self._critical_messages:
                rebuilt.append(messages[i])

        # Append recent messages
        for i in range(len(messages) - keep_recent, len(messages)):
            rebuilt.append(messages[i])

        logger.info(
            f"Context compressed: {len(messages)} -> {len(rebuilt)} messages "
            f"(compressed {len(compressible)} lines, preserved {len(self._critical_messages)} critical)"
        )
        return rebuilt

    # ═══════════════════════════════════════════════════════════
    # SOUL Identity System
    # ═══════════════════════════════════════════════════════════

    def load_soul_profile(self, profile: SoulProfile | dict):
        """Load a SOUL profile from a SoulProfile object or dict."""
        if isinstance(profile, dict):
            self.soul_profile = SoulProfile(
                identity=profile.get("identity", ""),
                principles=profile.get("principles", []),
                communication_style=profile.get("communication_style", ""),
                boundaries=profile.get("boundaries", []),
                goals=profile.get("goals", []),
            )
        else:
            self.soul_profile = profile
        logger.info(f"SOUL profile loaded for agent {self.agent_id}: {self.soul_profile.identity}")

    def update_soul_profile(self, **kwargs):
        """Update individual fields of the SOUL profile."""
        for key, value in kwargs.items():
            if hasattr(self.soul_profile, key):
                setattr(self.soul_profile, key, value)
        logger.info(f"SOUL profile updated for agent {self.agent_id}")

    # ═══════════════════════════════════════════════════════════
    # Cron / Scheduled Task Support
    # ═══════════════════════════════════════════════════════════

    def add_scheduled_task(self, name: str, schedule: str, prompt: str) -> ScheduledTask:
        """Register a new scheduled task.

        schedule can be a cron expression or an interval in seconds as a string.
        """
        task_id = f"st-{hashlib.sha1(f'{name}{schedule}{time.time()}'.encode()).hexdigest()[:12]}"
        task = ScheduledTask(
            id=task_id,
            name=name,
            schedule=schedule,
            prompt=prompt,
        )
        self._scheduled_tasks.append(task)
        logger.info(f"Scheduled task added: {name} (id={task_id}, schedule={schedule})")
        return task

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Return all enabled scheduled tasks that are due for execution.

        For interval-based schedules (all-digit strings), checks if enough
        seconds have elapsed since last_run. For cron expressions, always
        returns them (the caller should use a proper cron parser).
        """
        due: list[ScheduledTask] = []
        now = datetime.now(timezone.utc)
        for task in self._scheduled_tasks:
            if not task.enabled:
                continue
            # Interval-based schedule: all-digit string = seconds
            if task.schedule.isdigit():
                interval = int(task.schedule)
                if task.last_run is None:
                    due.append(task)
                elif (now - task.last_run).total_seconds() >= interval:
                    due.append(task)
            else:
                # Cron expression — always return (caller should parse properly)
                if task.last_run is None:
                    due.append(task)
                else:
                    # Conservative: treat as due if at least 60 seconds since last run
                    if (now - task.last_run).total_seconds() >= 60:
                        due.append(task)
        return due

    async def run_scheduled_task(self, task: ScheduledTask) -> str:
        """Execute a scheduled task by creating a fresh mini-session.

        Uses the task's prompt as the user message and runs a single-turn
        chat with tools enabled. Updates task.last_run on completion.
        """
        logger.info(f"Running scheduled task: {task.name} (id={task.id})")
        try:
            result = await self.chat(
                message=task.prompt,
                conversation_history=[],
                stream=False,
                enable_tools=True,
                enable_reasoning=False,
            )
            task.last_run = datetime.now(timezone.utc)
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.error(f"Scheduled task {task.name} failed: {e}")
            task.last_run = datetime.now(timezone.utc)
            return f"Scheduled task failed: {e}"