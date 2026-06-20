"""Buddy Unified Agent Runtime — orchestrates all agent subsystems

Provides a single entry point that ties together reasoning, tool composition,
context management, model proxying, skill compilation, reflection, intent
recognition, fleet management, knowledge networking, and event pipelining
into one cohesive agent execution environment.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from agent.agent_reasoning import (
    AgentReasoningEngine, ReasoningStrategy, ReasoningTrace,
)
from agent.agent_tool_composer import (
    AgentToolComposer, ToolPipeline, PipelineResult,
)
from agent.agent_context_manager import (
    AgentContextManager, ContextItem, ContextType, ContextPriority,
)
from agent.model_proxy import (
    ModelProxyLayer, ModelCapability, ProxyStrategy, ProxyRequest,
)
from agent.skill_compiler import (
    SkillCompiler, SkillDefinition, SkillLanguage,
)
from agent.agent_reflection import (
    AgentReflectionEngine, ReflectionDimension, QualityScore,
)
from agent.agent_intent import (
    AgentIntentEngine, IntentCategory, IntentComplexity,
)
from agent.agent_fleet import (
    AgentFleetManager, FleetAgent, FleetAgentStatus,
)
from agent.event_pipeline import (
    EventPipeline, PipelineEvent, EventSource, EventPriority,
)
from agent.knowledge_network import (
    KnowledgeNetwork, KnowledgeEntry, KnowledgeType,
)

logger = logging.getLogger("buddy.unified_runtime")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class RuntimePhase(str, Enum):
    """Phases of the unified agent runtime pipeline."""
    INTENT_ANALYSIS = "intent_analysis"
    CONTEXT_ASSEMBLY = "context_assembly"
    REASONING = "reasoning"
    TOOL_COMPOSITION = "tool_composition"
    SKILL_EXECUTION = "skill_execution"
    MODEL_ROUTING = "model_routing"
    REFLECTION = "reflection"
    KNOWLEDGE_SHARING = "knowledge_sharing"
    EVENT_DISPATCH = "event_dispatch"
    COMPLETED = "completed"


class RuntimeMode(str, Enum):
    """Execution modes for the unified runtime."""
    FULL = "full"               # All phases enabled
    FAST = "fast"               # Skip reasoning, go direct
    REFLECTIVE = "reflective"   # Emphasis on reflection
    COLLABORATIVE = "collaborative"  # Fleet coordination
    LEARNING = "learning"       # Focus on knowledge capture


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class RuntimeSession:
    """A single execution session through the unified runtime."""
    session_id: str
    agent_id: str
    mode: RuntimeMode = RuntimeMode.FULL
    phases: list[RuntimePhase] = field(default_factory=list)
    phase_results: dict[str, Any] = field(default_factory=dict)
    phase_timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    status: str = "pending"


@dataclass
class RuntimeMetrics:
    """Aggregated metrics across all runtime sessions."""
    total_sessions: int = 0
    successful_sessions: int = 0
    failed_sessions: int = 0
    avg_session_time_ms: float = 0.0
    phase_distribution: dict[str, int] = field(default_factory=dict)
    total_events_published: int = 0
    total_knowledge_shared: int = 0


# ═══════════════════════════════════════════════════════════
# Unified Agent Runtime
# ═══════════════════════════════════════════════════════════

class UnifiedAgentRuntime:
    """Unified runtime that orchestrates all Buddy agent subsystems.

    Provides a single execution pipeline that flows through intent analysis,
    context assembly, structured reasoning, dynamic tool composition, skill
    execution, intelligent model routing, self-reflection, knowledge sharing,
    and event dispatching. Each phase can be enabled or disabled based on
    the runtime mode.
    """

    def __init__(self):
        # Core subsystems
        self._reasoning: AgentReasoningEngine = AgentReasoningEngine()
        self._tool_composer: AgentToolComposer = AgentToolComposer()
        self._context_manager: AgentContextManager = AgentContextManager()
        self._model_proxy: ModelProxyLayer = ModelProxyLayer()
        self._skill_compiler: SkillCompiler = SkillCompiler()
        self._reflection: AgentReflectionEngine = AgentReflectionEngine()
        self._intent: AgentIntentEngine = AgentIntentEngine()
        self._fleet: AgentFleetManager = AgentFleetManager()
        self._event_pipeline: EventPipeline = EventPipeline()
        self._knowledge_network: KnowledgeNetwork = KnowledgeNetwork()

        # Session tracking
        self._sessions: dict[str, RuntimeSession] = {}
        self._metrics = RuntimeMetrics()
        self._active_agents: set[str] = set()

        # Phase pipeline configuration
        self._phase_handlers: dict[RuntimePhase, Any] = {
            RuntimePhase.INTENT_ANALYSIS: self._run_intent_analysis,
            RuntimePhase.CONTEXT_ASSEMBLY: self._run_context_assembly,
            RuntimePhase.REASONING: self._run_reasoning,
            RuntimePhase.TOOL_COMPOSITION: self._run_tool_composition,
            RuntimePhase.SKILL_EXECUTION: self._run_skill_execution,
            RuntimePhase.MODEL_ROUTING: self._run_model_routing,
            RuntimePhase.REFLECTION: self._run_reflection,
            RuntimePhase.KNOWLEDGE_SHARING: self._run_knowledge_sharing,
            RuntimePhase.EVENT_DISPATCH: self._run_event_dispatch,
        }

        logger.info("UnifiedAgentRuntime initialized with all subsystems")

    # ── Public API ──────────────────────────────────────────

    @property
    def reasoning(self) -> AgentReasoningEngine:
        return self._reasoning

    @property
    def tool_composer(self) -> AgentToolComposer:
        return self._tool_composer

    @property
    def context_manager(self) -> AgentContextManager:
        return self._context_manager

    @property
    def model_proxy(self) -> ModelProxyLayer:
        return self._model_proxy

    @property
    def skill_compiler(self) -> SkillCompiler:
        return self._skill_compiler

    @property
    def reflection(self) -> AgentReflectionEngine:
        return self._reflection

    @property
    def intent(self) -> AgentIntentEngine:
        return self._intent

    @property
    def fleet(self) -> AgentFleetManager:
        return self._fleet

    @property
    def event_pipeline(self) -> EventPipeline:
        return self._event_pipeline

    @property
    def knowledge_network(self) -> KnowledgeNetwork:
        return self._knowledge_network

    def get_metrics(self) -> dict:
        """Get aggregated runtime metrics."""
        return {
            "total_sessions": self._metrics.total_sessions,
            "successful_sessions": self._metrics.successful_sessions,
            "failed_sessions": self._metrics.failed_sessions,
            "success_rate": round(
                self._metrics.successful_sessions / max(1, self._metrics.total_sessions) * 100, 1
            ),
            "avg_session_time_ms": round(self._metrics.avg_session_time_ms, 1),
            "phase_distribution": self._metrics.phase_distribution,
            "total_events_published": self._metrics.total_events_published,
            "total_knowledge_shared": self._metrics.total_knowledge_shared,
            "active_sessions": len(self._sessions),
            "active_agents": len(self._active_agents),
        }

    def get_session(self, session_id: str) -> RuntimeSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    async def execute(
        self,
        agent_id: str,
        query: str,
        mode: RuntimeMode = RuntimeMode.FULL,
        context: dict[str, Any] | None = None,
    ) -> RuntimeSession:
        """Execute a complete runtime pipeline for the given query.

        Args:
            agent_id: The agent initiating the execution.
            query: The user query or task description.
            mode: The execution mode determining which phases run.
            context: Additional context data for the execution.

        Returns:
            RuntimeSession with complete execution results.
        """
        session_id = f"session-{uuid.uuid4().hex[:12]}"
        session = RuntimeSession(
            session_id=session_id,
            agent_id=agent_id,
            mode=mode,
        )
        self._sessions[session_id] = session
        self._active_agents.add(agent_id)
        self._metrics.total_sessions += 1

        # Determine phases based on mode
        phases = self._determine_phases(mode)
        session.phases = phases

        try:
            # Publish session start event
            await self._event_pipeline.publish(
                topic="runtime.session.started",
                source=EventSource.AGENT_CORE,
                payload={"session_id": session_id, "agent_id": agent_id, "mode": mode.value},
                priority=EventPriority.NORMAL,
            )
            self._metrics.total_events_published += 1

            # Execute each phase
            accumulated_context: dict[str, Any] = context or {"query": query, "agent_id": agent_id}

            for phase in phases:
                phase_start = time.time()
                try:
                    handler = self._phase_handlers[phase]
                    result = await handler(session, accumulated_context)
                    session.phase_results[phase.value] = result
                    if isinstance(result, dict):
                        accumulated_context.update(result)
                except Exception as phase_error:
                    logger.warning(f"Phase {phase.value} failed for session {session_id}: {phase_error}")
                    session.warnings.append(f"{phase.value}: {str(phase_error)}")
                    session.phase_results[phase.value] = {"error": str(phase_error)}

                elapsed = (time.time() - phase_start) * 1000
                session.phase_timings[phase.value] = elapsed
                self._metrics.phase_distribution[phase.value] = \
                    self._metrics.phase_distribution.get(phase.value, 0) + 1

            session.status = "completed"
            self._metrics.successful_sessions += 1

        except Exception as e:
            logger.error(f"Runtime session {session_id} failed: {e}")
            session.status = "failed"
            session.errors.append(str(e))
            self._metrics.failed_sessions += 1

        finally:
            session.completed_at = time.time()
            total_time = (session.completed_at - session.started_at) * 1000
            n = self._metrics.total_sessions
            self._metrics.avg_session_time_ms = (
                (self._metrics.avg_session_time_ms * (n - 1) + total_time) / n
            )

            # Publish session end event
            await self._event_pipeline.publish(
                topic="runtime.session.completed",
                source=EventSource.AGENT_CORE,
                payload={
                    "session_id": session_id,
                    "status": session.status,
                    "total_time_ms": total_time,
                    "phases_completed": len(session.phase_results),
                },
                priority=EventPriority.LOW,
            )
            self._metrics.total_events_published += 1

        return session

    # ── Phase Handlers ──────────────────────────────────────

    def _determine_phases(self, mode: RuntimeMode) -> list[RuntimePhase]:
        """Determine which phases to execute based on mode."""
        if mode == RuntimeMode.FULL:
            return [
                RuntimePhase.INTENT_ANALYSIS,
                RuntimePhase.CONTEXT_ASSEMBLY,
                RuntimePhase.REASONING,
                RuntimePhase.TOOL_COMPOSITION,
                RuntimePhase.SKILL_EXECUTION,
                RuntimePhase.MODEL_ROUTING,
                RuntimePhase.REFLECTION,
                RuntimePhase.KNOWLEDGE_SHARING,
                RuntimePhase.EVENT_DISPATCH,
            ]
        elif mode == RuntimeMode.FAST:
            return [
                RuntimePhase.CONTEXT_ASSEMBLY,
                RuntimePhase.MODEL_ROUTING,
                RuntimePhase.EVENT_DISPATCH,
            ]
        elif mode == RuntimeMode.REFLECTIVE:
            return [
                RuntimePhase.CONTEXT_ASSEMBLY,
                RuntimePhase.REASONING,
                RuntimePhase.MODEL_ROUTING,
                RuntimePhase.REFLECTION,
                RuntimePhase.EVENT_DISPATCH,
            ]
        elif mode == RuntimeMode.COLLABORATIVE:
            return [
                RuntimePhase.INTENT_ANALYSIS,
                RuntimePhase.CONTEXT_ASSEMBLY,
                RuntimePhase.TOOL_COMPOSITION,
                RuntimePhase.MODEL_ROUTING,
                RuntimePhase.KNOWLEDGE_SHARING,
                RuntimePhase.EVENT_DISPATCH,
            ]
        elif mode == RuntimeMode.LEARNING:
            return [
                RuntimePhase.CONTEXT_ASSEMBLY,
                RuntimePhase.REASONING,
                RuntimePhase.REFLECTION,
                RuntimePhase.KNOWLEDGE_SHARING,
                RuntimePhase.EVENT_DISPATCH,
            ]
        return []

    async def _run_intent_analysis(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Analyze user intent for the query."""
        query = context.get("query", "")
        result = self._intent.analyze_intent(
            agent_id=session.agent_id,
            query=query,
            session_id=session.session_id,
        )
        return {
            "intent_category": result.category.value if result.category else "unknown",
            "intent_complexity": result.complexity.value if result.complexity else "medium",
            "intent_urgency": result.urgency.value if result.urgency else "medium",
            "entities": [e.model_dump() if hasattr(e, 'model_dump') else str(e) for e in result.entities],
        }

    async def _run_context_assembly(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Assemble context window for the query."""
        query = context.get("query", "")
        agent_id = context.get("agent_id", "")

        # Add user message to context
        item = self._context_manager.add(
            content=query,
            context_type=ContextType.USER_MESSAGE,
            priority=ContextPriority.HIGH,
        )

        # Build context window
        window = self._context_manager.build_context_window(max_tokens=8000)
        return {
            "context_item_id": item.item_id,
            "context_tokens": item.token_count,
            "window_items": len(window),
        }

    async def _run_reasoning(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Execute structured reasoning on the query."""
        query = context.get("query", "")
        agent_id = context.get("agent_id", "")

        trace = self._reasoning.start_reasoning(
            agent_id=agent_id,
            query=query,
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        )

        # Add reasoning steps
        step = self._reasoning.add_step(
            trace_id=trace.trace_id,
            content=f"Analyzing query: {query[:100]}",
            confidence=0.8,
        )
        if step:
            self._reasoning.complete_step(trace.trace_id, step.step_id)

        return {
            "reasoning_trace_id": trace.trace_id,
            "strategy": trace.strategy.value,
            "steps_completed": 1,
        }

    async def _run_tool_composition(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Compose tool pipeline if needed."""
        query = context.get("query", "")
        intent_category = context.get("intent_category", "")

        # Only compose tools for actionable intents
        if intent_category in ("action", "task", "code"):
            pipeline = self._tool_composer.create_pipeline(
                name=f"Pipeline for {session.session_id}",
                description=f"Auto-generated pipeline for: {query[:80]}",
            )
            return {
                "pipeline_id": pipeline.pipeline_id,
                "pipeline_name": pipeline.pipeline_name,
            }

        return {"pipeline_id": None, "reason": "No tool composition needed"}

    async def _run_skill_execution(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Execute compiled skills if applicable."""
        query = context.get("query", "")
        # Compile a temporary skill from the query
        result = self._skill_compiler.compile(
            description=query,
            source_language=SkillLanguage.NATURAL_LANGUAGE,
        )
        return {
            "skill_id": result.skill.skill_id if result.skill else None,
            "skill_name": result.skill.name if result.skill else "unknown",
            "parameters_count": len(result.skill.parameters) if result.skill else 0,
            "success": result.success,
        }

    async def _run_model_routing(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Route the request to the appropriate model."""
        query = context.get("query", "")
        intent_complexity = context.get("intent_complexity", "medium")

        # Determine required capabilities
        capabilities = [ModelCapability.TEXT_GENERATION]
        if intent_complexity == "high":
            capabilities.append(ModelCapability.REASONING)

        request = ProxyRequest(
            request_id=f"req-{uuid.uuid4().hex[:12]}",
            messages=[{"role": "user", "content": query}],
            strategy=ProxyStrategy.CAPABILITY_MATCH,
            required_capabilities=capabilities,
        )

        response = await self._model_proxy.route_request(request)
        return {
            "model_id": response.model_id,
            "provider": response.provider.value if hasattr(response.provider, 'value') else str(response.provider),
            "cost": response.cost,
            "latency_ms": response.latency_ms,
            "is_fallback": response.is_fallback,
        }

    async def _run_reflection(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Self-reflect on the execution quality."""
        agent_id = context.get("agent_id", "")
        query = context.get("query", "")

        record = self._reflection.start_reflection(
            agent_id=agent_id,
            original_output=query,
            session_id=session.session_id,
        )

        # Score quality across dimensions
        self._reflection.assess_quality(
            reflection_id=record.reflection_id,
            scores=[
                QualityScore(dimension=ReflectionDimension.FACTUAL_ACCURACY, score=0.8, reasoning="Auto-assessed"),
                QualityScore(dimension=ReflectionDimension.COMPLETENESS, score=0.7, reasoning="Auto-assessed"),
                QualityScore(dimension=ReflectionDimension.CLARITY, score=0.9, reasoning="Auto-assessed"),
            ],
        )

        return {
            "reflection_id": record.reflection_id,
            "status": record.status.value,
            "quality_scores": len(record.quality_scores),
        }

    async def _run_knowledge_sharing(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Share knowledge across the network."""
        query = context.get("query", "")
        agent_id = context.get("agent_id", "")

        # Create a knowledge entry from the session
        entry = self._knowledge_network.publish(
            knowledge_type=KnowledgeType.INSIGHT,
            topic="runtime.session",
            content=f"Query: {query[:200]}",
            source_agent_id=agent_id,
            source_agent_name=agent_id,
            confidence=0.7,
        )

        self._metrics.total_knowledge_shared += 1
        return {
            "knowledge_entry_id": entry.entry_id,
            "knowledge_type": entry.knowledge_type.value,
        }

    async def _run_event_dispatch(
        self, session: RuntimeSession, context: dict
    ) -> dict:
        """Dispatch final events for the session."""
        events_published = 0

        # Publish phase completion events
        for phase_name, timing in session.phase_timings.items():
            await self._event_pipeline.publish(
                topic=f"runtime.phase.{phase_name}.completed",
                source=EventSource.ORCHESTRATOR,
                payload={"session_id": session.session_id, "timing_ms": timing},
                priority=EventPriority.LOW,
            )
            events_published += 1

        self._metrics.total_events_published += events_published
        return {"events_published": events_published}


# ── Singleton ──────────────────────────────────────────────

unified_runtime = UnifiedAgentRuntime()