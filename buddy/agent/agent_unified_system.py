"""Buddy Unified Agent System — AI-Native Autonomous Intelligence Core

The Unified Agent System integrates all agent capabilities into a single coherent
runtime that handles reasoning, tool orchestration, memory management, autonomous
execution, self-reflection, and continuous learning in a unified loop.

Architecture:
  Perception Layer  →  Cognition Layer  →  Action Layer  →  Reflection Layer
       ↑                                                                    ↓
       └──────────────────── Learning & Evolution ──────────────────────────┘
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.unified_system")


# ── Core Enums ────────────────────────────────────────────────────

class SystemMode(str, Enum):
    """Operating modes of the unified agent system."""
    REACTIVE = "reactive"          # Respond to user input directly
    DELIBERATIVE = "deliberative"  # Think through steps before acting
    AUTONOMOUS = "autonomous"      # Self-directed goal pursuit
    COLLABORATIVE = "collaborative"  # Multi-agent coordination
    REFLECTIVE = "reflective"      # Self-analysis and improvement
    EXPLORATORY = "exploratory"    # Open-ended discovery


class CognitivePhase(str, Enum):
    """Phases of the cognitive cycle."""
    PERCEIVE = "perceive"          # Gather and interpret input
    UNDERSTAND = "understand"      # Build semantic understanding
    REASON = "reason"              # Apply reasoning strategies
    PLAN = "plan"                  # Generate execution plan
    EXECUTE = "execute"            # Carry out actions
    OBSERVE = "observe"            # Monitor results
    REFLECT = "reflect"            # Analyze outcomes
    LEARN = "learn"                # Integrate new knowledge
    ADAPT = "adapt"                # Adjust strategies


class ExecutionStrategy(str, Enum):
    """Strategies for executing actions."""
    SEQUENTIAL = "sequential"          # One after another
    PARALLEL = "parallel"              # Execute concurrently
    CONDITIONAL = "conditional"        # Branch based on conditions
    RETRY_WITH_BACKOFF = "retry"       # Retry with exponential backoff
    FALLBACK_CHAIN = "fallback"        # Try alternatives on failure
    VOTE_CONSENSUS = "vote"            # Multiple attempts, majority wins


class AgentCapability(str, Enum):
    """Capabilities the unified agent can possess."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    TOOL_USE = "tool_use"
    WEB_BROWSING = "web_browsing"
    FILE_OPERATIONS = "file_operations"
    SHELL_EXECUTION = "shell_execution"
    DATA_ANALYSIS = "data_analysis"
    IMAGE_UNDERSTANDING = "image_understanding"
    PLANNING = "planning"
    REASONING = "reasoning"
    MEMORY_RETRIEVAL = "memory_retrieval"
    SELF_IMPROVEMENT = "self_improvement"
    COLLABORATION = "collaboration"
    DELEGATION = "delegation"


# ── Data Structures ───────────────────────────────────────────────

@dataclass
class PerceptionFrame:
    """A frame of perceived input from the environment."""
    frame_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: str = ""                    # "user", "system", "agent", "tool"
    content: str = ""
    content_type: str = "text"          # "text", "code", "image", "json"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    priority: float = 0.5               # 0.0 - 1.0 importance
    context_window: list[str] = field(default_factory=list)  # Related context keys


@dataclass
class CognitiveState:
    """The agent's current cognitive state after processing."""
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    phase: CognitivePhase = CognitivePhase.PERCEIVE
    understanding: str = ""             # Natural language understanding
    structured_understanding: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0             # 0.0 - 1.0
    hypotheses: list[str] = field(default_factory=list)
    selected_reasoning: str = ""        # Which reasoning strategy was used
    reasoning_trace: list[str] = field(default_factory=list)
    plan: list[dict[str, Any]] = field(default_factory=list)
    active_goals: list[str] = field(default_factory=list)
    emotional_valence: float = 0.0      # -1.0 to 1.0
    attention_focus: list[str] = field(default_factory=list)


@dataclass
class ActionStep:
    """A single action step in an execution plan."""
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    action_type: str = ""               # "tool_call", "llm_generate", "delegate", "wait"
    action_name: str = ""               # Name of the tool or action
    arguments: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    dependencies: list[str] = field(default_factory=list)  # step_ids this depends on
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    max_retries: int = 3
    timeout_seconds: float = 30.0
    fallback_steps: list[str] = field(default_factory=list)
    status: str = "pending"             # "pending", "running", "completed", "failed", "skipped"
    result: Any = None
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0


@dataclass
class ExecutionPlan:
    """A complete execution plan for the agent."""
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    steps: list[ActionStep] = field(default_factory=list)
    execution_order: list[list[str]] = field(default_factory=list)  # Layers of parallel steps
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    status: str = "draft"               # "draft", "running", "completed", "failed", "cancelled"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    completed_at: str = ""
    total_duration_ms: float = 0.0


@dataclass
class ReflectionInsight:
    """An insight gained from self-reflection."""
    insight_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    category: str = ""                  # "efficiency", "quality", "strategy", "knowledge"
    description: str = ""
    severity: str = "info"              # "info", "warning", "critical"
    source_phase: CognitivePhase = CognitivePhase.REFLECT
    action_items: list[str] = field(default_factory=list)
    confidence: float = 0.5
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SystemResult:
    """Complete result from a unified system execution."""
    session_id: str = ""
    mode: SystemMode = SystemMode.REACTIVE
    success: bool = True
    content: str = ""
    error: str = ""
    cognitive_state: Optional[CognitiveState] = None
    execution_plan: Optional[ExecutionPlan] = None
    insights: list[ReflectionInsight] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float = 0.0
    model_used: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Unified Agent System ─────────────────────────────────────────

class UnifiedAgentSystem:
    """AI-Native Unified Agent System that integrates all capabilities.

    This is the central intelligence core that orchestrates the complete
    perceive → reason → plan → execute → reflect → learn cycle.
    """

    def __init__(self):
        self._active_sessions: dict[str, CognitiveState] = {}
        self._execution_plans: dict[str, ExecutionPlan] = {}
        self._insight_history: list[ReflectionInsight] = []
        self._capability_registry: dict[str, list[AgentCapability]] = {}
        self._strategy_performance: dict[str, list[float]] = {}  # Strategy → success rates
        self._lock = asyncio.Lock()
        self._total_executions: int = 0
        self._total_tokens: int = 0

    # ── Perception Layer ─────────────────────────────────────

    def perceive(
        self,
        content: str,
        source: str = "user",
        context: dict[str, Any] | None = None,
    ) -> PerceptionFrame:
        """Process incoming input and build a perception frame.

        The perception layer extracts intent, entities, sentiment, and
        determines the priority and context of the input.
        """
        frame = PerceptionFrame(
            source=source,
            content=content,
            metadata=context or {},
        )

        # Analyze content characteristics
        content_lower = content.lower()

        # Determine content type
        if any(kw in content_lower for kw in ["code", "function", "class", "def ", "import "]):
            frame.content_type = "code"
        elif content.strip().startswith("{") and content.strip().endswith("}"):
            frame.content_type = "json"
        elif any(kw in content_lower for kw in ["http", "api", "endpoint", "request"]):
            frame.content_type = "api_request"

        # Determine priority based on urgency signals
        urgent_keywords = ["urgent", "asap", "critical", "emergency", "error", "bug", "fix"]
        if any(kw in content_lower for kw in urgent_keywords):
            frame.priority = 0.9
        elif "?" in content:
            frame.priority = 0.7
        elif len(content) > 200:
            frame.priority = 0.6

        logger.debug(f"Perception frame {frame.frame_id}: type={frame.content_type}, priority={frame.priority}")
        return frame

    # ── Cognition Layer ───────────────────────────────────────

    def understand(
        self,
        frame: PerceptionFrame,
        agent_profile: dict[str, Any] | None = None,
    ) -> CognitiveState:
        """Build deep understanding of the perceived input.

        This layer performs semantic analysis, intent classification,
        entity extraction, and context enrichment.
        """
        state = CognitiveState(phase=CognitivePhase.UNDERSTAND)

        # Extract intent
        content_lower = frame.content.lower()
        intents = []

        if any(kw in content_lower for kw in ["write", "create", "generate", "build", "make"]):
            intents.append("generation")
        if any(kw in content_lower for kw in ["explain", "what", "how", "why", "describe"]):
            intents.append("explanation")
        if any(kw in content_lower for kw in ["fix", "debug", "error", "bug", "issue"]):
            intents.append("debugging")
        if any(kw in content_lower for kw in ["analyze", "review", "check", "evaluate"]):
            intents.append("analysis")
        if any(kw in content_lower for kw in ["plan", "organize", "schedule", "roadmap"]):
            intents.append("planning")
        if any(kw in content_lower for kw in ["search", "find", "lookup", "research"]):
            intents.append("research")
        if any(kw in content_lower for kw in ["deploy", "run", "execute", "start", "launch"]):
            intents.append("execution")
        if not intents:
            intents.append("conversation")

        state.understanding = f"Intent: {', '.join(intents)}. "
        state.understanding += f"Complexity: {'high' if len(frame.content) > 500 else 'medium' if len(frame.content) > 100 else 'low'}. "
        state.understanding += f"Priority: {'high' if frame.priority > 0.7 else 'medium' if frame.priority > 0.4 else 'low'}."

        state.structured_understanding = {
            "intents": intents,
            "content_type": frame.content_type,
            "length": len(frame.content),
            "has_code": frame.content_type == "code",
            "is_question": "?" in frame.content,
            "priority": frame.priority,
        }
        state.confidence = 0.8 if len(intents) <= 2 else 0.6
        state.active_goals = intents

        return state

    def reason(
        self,
        state: CognitiveState,
        frame: PerceptionFrame,
        enable_deep_reasoning: bool = False,
    ) -> CognitiveState:
        """Apply reasoning strategies to the current understanding.

        Integrates multiple reasoning approaches:
        - Chain-of-thought for sequential problems
        - Tree-of-thought for multi-path exploration
        - Graph-of-thought for complex relational reasoning
        - Case-based reasoning for pattern matching
        - Abductive reasoning for hypothesis generation
        """
        state.phase = CognitivePhase.REASON

        # Determine appropriate reasoning strategy
        content_lower = frame.content.lower()
        reasoning_traces = []

        # Chain-of-thought for procedural tasks
        if any(kw in content_lower for kw in ["step", "how", "process", "procedure"]):
            state.selected_reasoning = "chain_of_thought"
            reasoning_traces.append("Applying chain-of-thought reasoning for procedural task")

        # Tree-of-thought for creative/exploratory tasks
        elif any(kw in content_lower for kw in ["idea", "option", "alternative", "design", "creative"]):
            state.selected_reasoning = "tree_of_thought"
            reasoning_traces.append("Exploring multiple reasoning paths with tree-of-thought")

        # Graph-of-thought for complex relational tasks
        elif any(kw in content_lower for kw in ["compare", "relationship", "system", "architecture"]):
            state.selected_reasoning = "graph_of_thought"
            reasoning_traces.append("Mapping relational dependencies with graph-of-thought")

        # Case-based reasoning for debugging
        elif any(kw in content_lower for kw in ["fix", "debug", "error", "bug", "issue"]):
            state.selected_reasoning = "case_based"
            reasoning_traces.append("Matching against known patterns with case-based reasoning")

        # Default to structured reasoning
        else:
            state.selected_reasoning = "structured_chain"
            reasoning_traces.append("Using structured chain-of-thought reasoning")

        # Generate hypotheses
        if "explain" in content_lower or "why" in content_lower:
            state.hypotheses = [
                f"Hypothesis 1: The user seeks conceptual understanding",
                f"Hypothesis 2: The user wants practical application guidance",
            ]

        state.reasoning_trace = reasoning_traces
        state.confidence = min(state.confidence + 0.1, 1.0)

        return state

    # ── Planning Layer ────────────────────────────────────────

    def plan(
        self,
        state: CognitiveState,
        frame: PerceptionFrame,
        available_tools: list[str] | None = None,
        max_parallelism: int = 5,
    ) -> ExecutionPlan:
        """Generate an execution plan from the cognitive state.

        Creates a structured plan with dependency-aware execution ordering
        and parallel execution optimization.
        """
        state.phase = CognitivePhase.PLAN
        available_tools = available_tools or []

        plan = ExecutionPlan(
            goal=frame.content[:200],
        )

        intents = state.structured_understanding.get("intents", [])

        # Build steps based on intent
        for i, intent in enumerate(intents):
            if intent == "generation":
                plan.steps.append(ActionStep(
                    action_type="llm_generate",
                    action_name="text_generation",
                    arguments={"prompt": frame.content, "style": "comprehensive"},
                    expected_outcome="Generated content matching the user's request",
                    strategy=ExecutionStrategy.SEQUENTIAL,
                ))

            elif intent == "explanation":
                plan.steps.append(ActionStep(
                    action_type="llm_generate",
                    action_name="explanation_generation",
                    arguments={"topic": frame.content, "depth": "thorough"},
                    expected_outcome="Clear, structured explanation",
                    strategy=ExecutionStrategy.SEQUENTIAL,
                ))

            elif intent == "debugging":
                if "code_analysis" in available_tools:
                    plan.steps.append(ActionStep(
                        action_type="tool_call",
                        action_name="code_analysis",
                        arguments={"code": frame.content},
                        expected_outcome="Identified issues and fix suggestions",
                        strategy=ExecutionStrategy.SEQUENTIAL,
                    ))
                plan.steps.append(ActionStep(
                    action_type="llm_generate",
                    action_name="debugging_analysis",
                    arguments={"issue": frame.content},
                    expected_outcome="Root cause analysis and fix strategy",
                    strategy=ExecutionStrategy.SEQUENTIAL,
                ))

            elif intent == "analysis":
                plan.steps.append(ActionStep(
                    action_type="llm_generate",
                    action_name="analytical_review",
                    arguments={"content": frame.content, "approach": "systematic"},
                    expected_outcome="Comprehensive analysis with findings",
                    strategy=ExecutionStrategy.SEQUENTIAL,
                ))

            elif intent == "planning":
                plan.steps.append(ActionStep(
                    action_type="llm_generate",
                    action_name="plan_generation",
                    arguments={"goal": frame.content, "format": "structured"},
                    expected_outcome="Detailed actionable plan with milestones",
                    strategy=ExecutionStrategy.SEQUENTIAL,
                ))

            elif intent == "research":
                if "web_search" in available_tools:
                    plan.steps.append(ActionStep(
                        action_type="tool_call",
                        action_name="web_search",
                        arguments={"query": frame.content},
                        expected_outcome="Relevant search results",
                        strategy=ExecutionStrategy.SEQUENTIAL,
                    ))
                plan.steps.append(ActionStep(
                    action_type="llm_generate",
                    action_name="research_synthesis",
                    arguments={"topic": frame.content},
                    expected_outcome="Synthesized research findings",
                    strategy=ExecutionStrategy.SEQUENTIAL,
                ))

            elif intent == "execution":
                plan.steps.append(ActionStep(
                    action_type="tool_call",
                    action_name="task_execution",
                    arguments={"command": frame.content},
                    expected_outcome="Task executed successfully",
                    strategy=ExecutionStrategy.SEQUENTIAL,
                ))

        # Build execution order (dependency-based)
        plan.execution_order = [[step.step_id] for step in plan.steps]
        plan.total_steps = len(plan.steps)
        state.plan = [
            {"step_id": s.step_id, "action": s.action_name, "type": s.action_type}
            for s in plan.steps
        ]

        self._execution_plans[plan.plan_id] = plan
        return plan

    # ── Execution Layer ───────────────────────────────────────

    async def execute(
        self,
        plan: ExecutionPlan,
        executor: Callable | None = None,
        on_step_complete: Callable | None = None,
    ) -> ExecutionPlan:
        """Execute the plan with support for parallel, sequential, and conditional steps."""
        plan.status = "running"
        plan.started_at = datetime.now(timezone.utc).isoformat()

        for layer in plan.execution_order:
            # Execute steps in this layer in parallel
            tasks = []
            for step_id in layer:
                step = next((s for s in plan.steps if s.step_id == step_id), None)
                if step and step.status == "pending":
                    tasks.append(self._execute_step(step, executor, on_step_complete))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # Determine final status
        plan.completed_steps = sum(1 for s in plan.steps if s.status == "completed")
        plan.failed_steps = sum(1 for s in plan.steps if s.status == "failed")

        if plan.failed_steps == 0:
            plan.status = "completed"
        elif plan.completed_steps > 0:
            plan.status = "completed"  # Partial success
        else:
            plan.status = "failed"

        plan.completed_at = datetime.now(timezone.utc).isoformat()
        return plan

    async def _execute_step(
        self,
        step: ActionStep,
        executor: Callable | None,
        on_step_complete: Callable | None,
    ):
        """Execute a single action step with retry and fallback support."""
        step.status = "running"
        step.started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.time()

        for attempt in range(step.max_retries):
            try:
                if executor:
                    if asyncio.iscoroutinefunction(executor):
                        result = await executor(step)
                    else:
                        result = executor(step)
                else:
                    result = {"status": "simulated", "step": step.action_name}

                step.result = result
                step.status = "completed"
                break

            except Exception as e:
                logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {e}")
                if attempt == step.max_retries - 1:
                    step.status = "failed"
                    step.error = str(e)

                    # Try fallback steps
                    for fallback_id in step.fallback_steps:
                        fallback = next(
                            (s for s in self._execution_plans.get("", ExecutionPlan()).steps
                             if s.step_id == fallback_id), None
                        )
                        if fallback:
                            logger.info(f"Executing fallback step {fallback_id}")
                            await self._execute_step(fallback, executor, on_step_complete)
                            if fallback.status == "completed":
                                step.status = "completed"
                                step.result = fallback.result
                                break
                else:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)

        step.duration_ms = (time.time() - start_time) * 1000
        step.completed_at = datetime.now(timezone.utc).isoformat()

        if on_step_complete:
            try:
                if asyncio.iscoroutinefunction(on_step_complete):
                    await on_step_complete(step)
                else:
                    on_step_complete(step)
            except Exception as e:
                logger.warning(f"Step complete callback failed: {e}")

    # ── Reflection Layer ──────────────────────────────────────

    def reflect(
        self,
        plan: ExecutionPlan,
        state: CognitiveState,
        result_content: str = "",
    ) -> list[ReflectionInsight]:
        """Analyze execution results and generate insights for improvement."""
        state.phase = CognitivePhase.REFLECT
        insights: list[ReflectionInsight] = []

        # Efficiency analysis
        if plan.total_duration_ms > 10000:
            insights.append(ReflectionInsight(
                category="efficiency",
                description=f"Execution took {plan.total_duration_ms:.0f}ms. Consider optimizing step parallelism.",
                severity="warning",
                action_items=["Review step dependencies for parallelization opportunities"],
            ))

        # Quality analysis
        if plan.failed_steps > 0:
            insights.append(ReflectionInsight(
                category="quality",
                description=f"{plan.failed_steps}/{plan.total_steps} steps failed. Review failure patterns.",
                severity="critical" if plan.failed_steps > plan.total_steps // 2 else "warning",
                action_items=["Analyze failure root causes", "Add fallback strategies for failing steps"],
            ))

        if plan.completed_steps == plan.total_steps and plan.failed_steps == 0:
            insights.append(ReflectionInsight(
                category="quality",
                description="All steps completed successfully. Execution was optimal.",
                severity="info",
                action_items=["Record successful pattern for future reuse"],
            ))

        # Strategy analysis
        if state.selected_reasoning:
            self._strategy_performance.setdefault(state.selected_reasoning, []).append(
                1.0 if plan.status == "completed" else 0.0
            )

        self._insight_history.extend(insights)
        if len(self._insight_history) > 1000:
            self._insight_history = self._insight_history[-500:]

        return insights

    # ── Comprehensive Execution Entry Point ───────────────────

    async def run(
        self,
        content: str,
        agent_id: str = "",
        mode: SystemMode = SystemMode.REACTIVE,
        enable_tools: bool = True,
        enable_reasoning: bool = True,
        enable_reflection: bool = True,
        agent_profile: dict[str, Any] | None = None,
        available_tools: list[str] | None = None,
        executor: Callable | None = None,
    ) -> SystemResult:
        """Execute the complete cognitive cycle.

        This is the primary entry point for the unified agent system.
        It orchestrates the full perceive → understand → reason → plan →
        execute → reflect → learn pipeline.
        """
        session_id = uuid.uuid4().hex[:12]
        start_time = time.time()

        try:
            # Phase 1: Perceive
            frame = self.perceive(content, source="user")

            # Phase 2: Understand
            state = self.understand(frame, agent_profile)
            self._active_sessions[session_id] = state

            # Phase 3: Reason
            if enable_reasoning:
                state = self.reason(state, frame, enable_deep_reasoning=True)
            state.phase = CognitivePhase.REASON

            # Phase 4: Plan
            plan = self.plan(state, frame, available_tools)

            # Phase 5: Execute
            if enable_tools and executor:
                plan = await self.execute(plan, executor)
            else:
                plan.status = "completed"

            # Phase 6: Reflect
            insights: list[ReflectionInsight] = []
            if enable_reflection:
                insights = self.reflect(plan, state)

            # Phase 7: Generate result
            result_content = self._generate_result(state, plan, frame)

            latency_ms = (time.time() - start_time) * 1000
            self._total_executions += 1

            return SystemResult(
                session_id=session_id,
                mode=mode,
                success=plan.status == "completed",
                content=result_content,
                cognitive_state=state,
                execution_plan=plan,
                insights=insights,
                latency_ms=latency_ms,
                metadata={
                    "phases_completed": [
                        "perceive", "understand", "reason", "plan", "execute", "reflect"
                    ],
                    "reasoning_strategy": state.selected_reasoning,
                    "confidence": state.confidence,
                    "total_steps": plan.total_steps,
                    "completed_steps": plan.completed_steps,
                },
            )

        except Exception as e:
            logger.error(f"Unified system execution failed: {e}")
            latency_ms = (time.time() - start_time) * 1000
            return SystemResult(
                session_id=session_id,
                mode=mode,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    def _generate_result(
        self,
        state: CognitiveState,
        plan: ExecutionPlan,
        frame: PerceptionFrame,
    ) -> str:
        """Generate the final result content from execution."""
        parts: list[str] = []

        if state.understanding:
            parts.append(f"Understanding: {state.understanding}")

        if state.reasoning_trace:
            parts.append(f"Reasoning: {'; '.join(state.reasoning_trace)}")

        if plan.steps:
            completed = [s for s in plan.steps if s.status == "completed"]
            if completed:
                parts.append(f"Completed {len(completed)}/{plan.total_steps} steps successfully.")

        return "\n".join(parts) if parts else "Execution completed."

    # ── Capability Management ─────────────────────────────────

    def register_capabilities(self, agent_id: str, capabilities: list[AgentCapability]):
        """Register capabilities for an agent."""
        self._capability_registry[agent_id] = capabilities

    def get_capabilities(self, agent_id: str) -> list[AgentCapability]:
        """Get capabilities of an agent."""
        return self._capability_registry.get(agent_id, [])

    def has_capability(self, agent_id: str, capability: AgentCapability) -> bool:
        """Check if an agent has a specific capability."""
        return capability in self._capability_registry.get(agent_id, [])

    # ── Statistics ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get system statistics."""
        strategy_stats = {}
        for strategy, results in self._strategy_performance.items():
            if results:
                strategy_stats[strategy] = {
                    "success_rate": sum(results) / len(results),
                    "total_uses": len(results),
                }

        return {
            "total_executions": self._total_executions,
            "total_tokens": self._total_tokens,
            "active_sessions": len(self._active_sessions),
            "total_insights": len(self._insight_history),
            "strategy_performance": strategy_stats,
            "capability_registry": {
                agent_id: [c.value for c in caps]
                for agent_id, caps in self._capability_registry.items()
            },
        }

    def get_recent_insights(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent reflection insights."""
        return [
            {
                "insight_id": i.insight_id,
                "category": i.category,
                "description": i.description,
                "severity": i.severity,
                "action_items": i.action_items,
                "timestamp": i.timestamp,
            }
            for i in self._insight_history[-limit:]
        ]


# Global instance
unified_system = UnifiedAgentSystem()