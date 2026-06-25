"""Buddy Agent Cognitive Engine — central nervous system for the agent ecosystem

The Cognitive Engine is the unified orchestration layer that drives all
agent cognitive processes. It implements a comprehensive cognitive cycle
(Perceive → Understand → Reason → Plan → Execute → Reflect) that integrates
context fusion, intent resolution, tool selection, and response synthesis
into a single cohesive intelligence kernel.

Core capabilities:
  - Cognitive Loop: configurable multi-phase cycle with per-phase metrics
  - Context Fusion: multi-source context assembly with attention mechanisms
  - Intent Resolution: multi-level intent parsing (explicit, implicit, latent)
  - Tool Selection: semantic tool matching with chain composition
  - Response Synthesis: multi-source generation with tone adaptation
  - Cognitive Metrics: depth, utilization, relevance, and quality tracking
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

logger = logging.getLogger("buddy.cognitive_engine")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════


class CognitivePhase(str, Enum):
    """Phases of the unified cognitive cycle."""
    PERCEIVE = "perceive"
    UNDERSTAND = "understand"
    REASON = "reason"
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"


class CognitiveStrategy(str, Enum):
    """Preconfigured cognitive strategies that tune the loop behavior."""
    FAST = "fast"
    THOROUGH = "thorough"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"


class IntentLevel(str, Enum):
    """Depth levels at which intent can be expressed."""
    EXPLICIT = "explicit"    # Directly stated in the user message
    IMPLICIT = "implicit"    # Inferred from context and history
    LATENT = "latent"        # Underlying need not directly expressed


class ExecutionStrategy(str, Enum):
    """Strategies for orchestrating tool execution."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class ContextSource(str, Enum):
    """Sources from which context can be fused."""
    MEMORY = "memory"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    CURRENT_SESSION = "current_session"
    TOOL_OUTPUTS = "tool_outputs"
    USER_MODEL = "user_model"
    PERSONA = "persona"
    IDENTITY = "identity"


class ConfidenceLevel(str, Enum):
    """Calibrated confidence levels for cognitive outputs."""
    UNCERTAIN = "uncertain"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CERTAIN = "certain"


class PhaseState(str, Enum):
    """State machine for individual cognitive phases."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class CognitiveLoad(str, Enum):
    """Cognitive load levels for adaptive throttling."""
    LIGHT = "light"
    NORMAL = "normal"
    ELEVATED = "elevated"
    HEAVY = "heavy"
    OVERLOADED = "overloaded"


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════


@dataclass
class CognitiveEngineConfig:
    """Configuration for the Agent Cognitive Engine.

    Attributes:
        max_context_window_tokens: Maximum tokens allowed in the fused context window.
        attention_top_k: Number of top-scoring context items to retain after attention.
        min_confidence_threshold: Minimum confidence for intent resolution to proceed.
        max_tool_chain_depth: Maximum depth of composed tool chains.
        reasoning_depth: Maximum steps in the reasoning phase.
        reflection_depth: Maximum depth of self-reflection analysis.
        enable_attention_mechanism: Whether to apply attention-based context ranking.
        enable_cognitive_load_monitoring: Whether to track and throttle based on load.
        enable_intent_disambiguation: Whether to disambiguate ambiguous intents.
        enable_source_attribution: Whether to attribute facts in responses.
        parallel_tool_limit: Max number of tools to execute in parallel.
        context_prune_ratio: Fraction of context to prune when over budget.
        strategy_overrides: Phase-specific overrides for each cognitive strategy.
    """
    max_context_window_tokens: int = 16384
    attention_top_k: int = 20
    min_confidence_threshold: float = 0.6
    max_tool_chain_depth: int = 5
    reasoning_depth: int = 8
    reflection_depth: int = 4
    enable_attention_mechanism: bool = True
    enable_cognitive_load_monitoring: bool = True
    enable_intent_disambiguation: bool = True
    enable_source_attribution: bool = True
    parallel_tool_limit: int = 4
    context_prune_ratio: float = 0.3
    strategy_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.strategy_overrides:
            self.strategy_overrides = {
                CognitiveStrategy.FAST.value: {
                    "reasoning_depth": 3,
                    "reflection_depth": 1,
                    "max_tool_chain_depth": 2,
                },
                CognitiveStrategy.THOROUGH.value: {
                    "reasoning_depth": 12,
                    "reflection_depth": 6,
                    "max_tool_chain_depth": 8,
                },
                CognitiveStrategy.CREATIVE.value: {
                    "reasoning_depth": 8,
                    "reflection_depth": 3,
                    "max_tool_chain_depth": 5,
                },
                CognitiveStrategy.ANALYTICAL.value: {
                    "reasoning_depth": 10,
                    "reflection_depth": 5,
                    "max_tool_chain_depth": 6,
                },
            }

    def get_effective_config(self, strategy: CognitiveStrategy) -> dict[str, Any]:
        """Return configuration values overridden for the given strategy."""
        overrides = self.strategy_overrides.get(strategy.value, {})
        return {
            "reasoning_depth": overrides.get("reasoning_depth", self.reasoning_depth),
            "reflection_depth": overrides.get("reflection_depth", self.reflection_depth),
            "max_tool_chain_depth": overrides.get("max_tool_chain_depth", self.max_tool_chain_depth),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_context_window_tokens": self.max_context_window_tokens,
            "attention_top_k": self.attention_top_k,
            "min_confidence_threshold": self.min_confidence_threshold,
            "max_tool_chain_depth": self.max_tool_chain_depth,
            "reasoning_depth": self.reasoning_depth,
            "reflection_depth": self.reflection_depth,
            "enable_attention_mechanism": self.enable_attention_mechanism,
            "enable_cognitive_load_monitoring": self.enable_cognitive_load_monitoring,
            "enable_intent_disambiguation": self.enable_intent_disambiguation,
            "enable_source_attribution": self.enable_source_attribution,
            "parallel_tool_limit": self.parallel_tool_limit,
            "context_prune_ratio": self.context_prune_ratio,
            "strategy_overrides": self.strategy_overrides,
        }


# ═══════════════════════════════════════════════════════════
# Data Classes — Phase Results
# ═══════════════════════════════════════════════════════════


@dataclass
class PhaseMetrics:
    """Metrics collected during a single cognitive phase."""
    phase: CognitivePhase
    state: PhaseState = PhaseState.PENDING
    started_at: str = ""
    completed_at: str = ""
    elapsed_ms: float = 0.0
    token_count: int = 0
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "state": self.state.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "token_count": self.token_count,
            "confidence": round(self.confidence, 3),
            "metadata": self.metadata,
        }


@dataclass
class PerceptionInput:
    """Raw input entering the perception phase."""
    input_id: str = field(default_factory=lambda: f"pin-{uuid.uuid4().hex[:8]}")
    content: str = ""
    content_type: str = "text"
    source: str = "user"
    session_id: str = ""
    agent_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_id": self.input_id,
            "content_preview": self.content[:200],
            "content_type": self.content_type,
            "source": self.source,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class PerceptionResult:
    """Output of the perception phase."""
    perception_id: str = field(default_factory=lambda: f"perc-{uuid.uuid4().hex[:8]}")
    raw_input: PerceptionInput | None = None
    extracted_entities: list[dict[str, Any]] = field(default_factory=list)
    detected_language: str = "en"
    sentiment: str = "neutral"
    complexity_estimate: float = 0.5
    keyword_set: list[str] = field(default_factory=list)
    phase_metrics: PhaseMetrics = field(default_factory=lambda: PhaseMetrics(phase=CognitivePhase.PERCEIVE))

    def to_dict(self) -> dict[str, Any]:
        return {
            "perception_id": self.perception_id,
            "raw_input": self.raw_input.to_dict() if self.raw_input else None,
            "extracted_entities": self.extracted_entities,
            "detected_language": self.detected_language,
            "sentiment": self.sentiment,
            "complexity_estimate": round(self.complexity_estimate, 3),
            "keyword_set": self.keyword_set,
            "phase_metrics": self.phase_metrics.to_dict(),
        }


@dataclass
class UnderstandingResult:
    """Output of the understanding phase."""
    understanding_id: str = field(default_factory=lambda: f"und-{uuid.uuid4().hex[:8]}")
    semantic_parse: dict[str, Any] = field(default_factory=dict)
    domain_classification: str = "general"
    task_type: str = "chat"
    identified_constraints: list[dict[str, Any]] = field(default_factory=list)
    ambiguity_flags: list[str] = field(default_factory=list)
    phase_metrics: PhaseMetrics = field(default_factory=lambda: PhaseMetrics(phase=CognitivePhase.UNDERSTAND))

    def to_dict(self) -> dict[str, Any]:
        return {
            "understanding_id": self.understanding_id,
            "semantic_parse": self.semantic_parse,
            "domain_classification": self.domain_classification,
            "task_type": self.task_type,
            "identified_constraints": self.identified_constraints,
            "ambiguity_flags": self.ambiguity_flags,
            "phase_metrics": self.phase_metrics.to_dict(),
        }


@dataclass
class ReasoningResult:
    """Output of the reasoning phase."""
    reasoning_id: str = field(default_factory=lambda: f"rea-{uuid.uuid4().hex[:8]}")
    reasoning_strategy: str = "balanced"
    reasoning_trace: list[dict[str, Any]] = field(default_factory=list)
    intermediate_conclusions: list[str] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    evidence_chain: list[dict[str, Any]] = field(default_factory=list)
    phase_metrics: PhaseMetrics = field(default_factory=lambda: PhaseMetrics(phase=CognitivePhase.REASON))

    def to_dict(self) -> dict[str, Any]:
        return {
            "reasoning_id": self.reasoning_id,
            "reasoning_strategy": self.reasoning_strategy,
            "reasoning_trace": self.reasoning_trace,
            "intermediate_conclusions": self.intermediate_conclusions,
            "hypotheses": self.hypotheses,
            "evidence_chain": self.evidence_chain,
            "phase_metrics": self.phase_metrics.to_dict(),
        }


@dataclass
class PlanResult:
    """Output of the planning phase."""
    plan_id: str = field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:8]}")
    sub_tasks: list[dict[str, Any]] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)
    total_estimated_effort: str = "medium"
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    phase_metrics: PhaseMetrics = field(default_factory=lambda: PhaseMetrics(phase=CognitivePhase.PLAN))

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "sub_tasks": self.sub_tasks,
            "parallel_groups": self.parallel_groups,
            "critical_path": self.critical_path,
            "total_estimated_effort": self.total_estimated_effort,
            "dependency_graph": self.dependency_graph,
            "phase_metrics": self.phase_metrics.to_dict(),
        }


@dataclass
class ExecutionResult:
    """Output of the execution phase."""
    execution_id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}")
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    completed_steps: int = 0
    failed_steps: int = 0
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    phase_metrics: PhaseMetrics = field(default_factory=lambda: PhaseMetrics(phase=CognitivePhase.EXECUTE))

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "execution_strategy": self.execution_strategy.value,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "artifacts": self.artifacts,
            "phase_metrics": self.phase_metrics.to_dict(),
        }


@dataclass
class ReflectionResult:
    """Output of the reflection phase."""
    reflection_id: str = field(default_factory=lambda: f"refl-{uuid.uuid4().hex[:8]}")
    self_assessment_score: float = 0.0
    quality_issues: list[str] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)
    lessons_learned: list[dict[str, Any]] = field(default_factory=list)
    correctness_check: bool = True
    phase_metrics: PhaseMetrics = field(default_factory=lambda: PhaseMetrics(phase=CognitivePhase.REFLECT))

    def to_dict(self) -> dict[str, Any]:
        return {
            "reflection_id": self.reflection_id,
            "self_assessment_score": round(self.self_assessment_score, 3),
            "quality_issues": self.quality_issues,
            "improvement_suggestions": self.improvement_suggestions,
            "lessons_learned": self.lessons_learned,
            "correctness_check": self.correctness_check,
            "phase_metrics": self.phase_metrics.to_dict(),
        }


# ═══════════════════════════════════════════════════════════
# Data Classes — Engine Components
# ═══════════════════════════════════════════════════════════


@dataclass
class ContextFragment:
    """A single fragment of context from a specific source."""
    fragment_id: str = field(default_factory=lambda: f"ctxf-{uuid.uuid4().hex[:8]}")
    source: ContextSource = ContextSource.MEMORY
    content: str = ""
    relevance_score: float = 0.5
    attention_weight: float = 0.0
    token_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "source": self.source.value,
            "content_preview": self.content[:150],
            "relevance_score": round(self.relevance_score, 3),
            "attention_weight": round(self.attention_weight, 3),
            "token_count": self.token_count,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ContextFusion:
    """Result of the context fusion layer."""
    fusion_id: str = field(default_factory=lambda: f"cfu-{uuid.uuid4().hex[:8]}")
    fragments: list[ContextFragment] = field(default_factory=list)
    fused_context: str = ""
    total_tokens: int = 0
    pruned_fragments: int = 0
    attention_distribution: dict[str, float] = field(default_factory=dict)
    source_breakdown: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fusion_id": self.fusion_id,
            "fragment_count": len(self.fragments),
            "fragments": [f.to_dict() for f in self.fragments],
            "fused_context_preview": self.fused_context[:200],
            "total_tokens": self.total_tokens,
            "pruned_fragments": self.pruned_fragments,
            "attention_distribution": self.attention_distribution,
            "source_breakdown": self.source_breakdown,
        }


@dataclass
class IntentResolution:
    """Result of the intent resolution pipeline."""
    resolution_id: str = field(default_factory=lambda: f"intr-{uuid.uuid4().hex[:8]}")
    primary_intent: str = ""
    intent_level: IntentLevel = IntentLevel.EXPLICIT
    intent_category: str = "general"
    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.UNCERTAIN
    alternative_intents: list[dict[str, Any]] = field(default_factory=list)
    disambiguation_notes: str = ""
    intent_to_action_mapping: dict[str, Any] = field(default_factory=dict)
    user_model_insights: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution_id": self.resolution_id,
            "primary_intent": self.primary_intent,
            "intent_level": self.intent_level.value,
            "intent_category": self.intent_category,
            "confidence": round(self.confidence, 3),
            "confidence_level": self.confidence_level.value,
            "alternative_intents": self.alternative_intents,
            "disambiguation_notes": self.disambiguation_notes,
            "intent_to_action_mapping": self.intent_to_action_mapping,
            "user_model_insights": self.user_model_insights,
        }


@dataclass
class ToolSelection:
    """Result of the tool selection router."""
    selection_id: str = field(default_factory=lambda: f"tsel-{uuid.uuid4().hex[:8]}")
    selected_tools: list[dict[str, Any]] = field(default_factory=list)
    tool_chain: list[list[str]] = field(default_factory=list)
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    dependency_resolution: dict[str, list[str]] = field(default_factory=dict)
    semantic_match_scores: dict[str, float] = field(default_factory=dict)
    fallback_tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "selected_tools": self.selected_tools,
            "tool_chain": self.tool_chain,
            "execution_strategy": self.execution_strategy.value,
            "dependency_resolution": self.dependency_resolution,
            "semantic_match_scores": self.semantic_match_scores,
            "fallback_tools": self.fallback_tools,
        }


@dataclass
class ResponseSynthesis:
    """Result of the response synthesis phase."""
    synthesis_id: str = field(default_factory=lambda: f"rsyn-{uuid.uuid4().hex[:8]}")
    final_response: str = ""
    tone: str = "neutral"
    style: str = "professional"
    source_attributions: list[dict[str, Any]] = field(default_factory=list)
    fact_grounding: list[dict[str, Any]] = field(default_factory=list)
    alternative_formulations: list[str] = field(default_factory=list)
    response_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "final_response_preview": self.final_response[:300],
            "tone": self.tone,
            "style": self.style,
            "source_attributions": self.source_attributions,
            "fact_grounding": self.fact_grounding,
            "alternative_formulations": self.alternative_formulations,
            "response_metadata": self.response_metadata,
        }


@dataclass
class CognitiveMetrics:
    """Aggregated cognitive metrics across all cycles."""
    cycles_completed: int = 0
    cycles_failed: int = 0
    total_tokens_consumed: int = 0
    total_time_ms: float = 0.0
    reasoning_depth_avg: float = 0.0
    tool_utilization_rate: float = 0.0
    context_relevance_avg: float = 0.0
    response_quality_avg: float = 0.0
    cognitive_load: CognitiveLoad = CognitiveLoad.NORMAL
    phase_breakdown: dict[str, float] = field(default_factory=dict)
    cycle_history: list[dict[str, Any]] = field(default_factory=list)
    strategy_effectiveness: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycles_completed": self.cycles_completed,
            "cycles_failed": self.cycles_failed,
            "total_tokens_consumed": self.total_tokens_consumed,
            "total_time_ms": round(self.total_time_ms, 2),
            "reasoning_depth_avg": round(self.reasoning_depth_avg, 2),
            "tool_utilization_rate": round(self.tool_utilization_rate, 3),
            "context_relevance_avg": round(self.context_relevance_avg, 3),
            "response_quality_avg": round(self.response_quality_avg, 3),
            "cognitive_load": self.cognitive_load.value,
            "phase_breakdown": self.phase_breakdown,
            "cycle_history": self.cycle_history[-20:],
            "strategy_effectiveness": self.strategy_effectiveness,
        }


@dataclass
class CognitiveCycleResult:
    """Complete result of a single cognitive cycle."""
    cycle_id: str = field(default_factory=lambda: f"ccy-{uuid.uuid4().hex[:12]}")
    strategy: CognitiveStrategy = CognitiveStrategy.FAST
    perception: PerceptionResult | None = None
    understanding: UnderstandingResult | None = None
    reasoning: ReasoningResult | None = None
    plan: PlanResult | None = None
    execution: ExecutionResult | None = None
    reflection: ReflectionResult | None = None
    context_fusion: ContextFusion | None = None
    intent_resolution: IntentResolution | None = None
    tool_selection: ToolSelection | None = None
    response_synthesis: ResponseSynthesis | None = None
    success: bool = True
    error_message: str = ""
    total_elapsed_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "strategy": self.strategy.value,
            "perception": self.perception.to_dict() if self.perception else None,
            "understanding": self.understanding.to_dict() if self.understanding else None,
            "reasoning": self.reasoning.to_dict() if self.reasoning else None,
            "plan": self.plan.to_dict() if self.plan else None,
            "execution": self.execution.to_dict() if self.execution else None,
            "reflection": self.reflection.to_dict() if self.reflection else None,
            "context_fusion": self.context_fusion.to_dict() if self.context_fusion else None,
            "intent_resolution": self.intent_resolution.to_dict() if self.intent_resolution else None,
            "tool_selection": self.tool_selection.to_dict() if self.tool_selection else None,
            "response_synthesis": self.response_synthesis.to_dict() if self.response_synthesis else None,
            "success": self.success,
            "error_message": self.error_message,
            "total_elapsed_ms": round(self.total_elapsed_ms, 2),
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════
# Agent Cognitive Engine
# ═══════════════════════════════════════════════════════════


class AgentCognitiveEngine:
    """Central nervous system for the Buddy agent ecosystem.

    Implements the unified cognitive loop that orchestrates all agent
    subsystems through a configurable Perceive → Understand → Reason →
    Plan → Execute → Reflect cycle. Provides context fusion, intent
    resolution, tool selection, and response synthesis as integrated
    cognitive services.

    Usage::

        engine = AgentCognitiveEngine(agent_id="buddy-001")
        result = await engine.run_cycle(
            user_input="Explain quantum computing",
            strategy=CognitiveStrategy.ANALYTICAL,
        )
        print(result.response_synthesis.final_response)
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str = "Buddy",
        config: CognitiveEngineConfig | None = None,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.config = config or CognitiveEngineConfig()

        # Cycle tracking
        self._cycle_history: list[CognitiveCycleResult] = []
        self._active_cycle: CognitiveCycleResult | None = None

        # Metrics
        self._metrics = CognitiveMetrics()

        # Context store
        self._context_store: dict[ContextSource, list[ContextFragment]] = defaultdict(list)

        # Intent history for disambiguation
        self._intent_history: list[IntentResolution] = []

        # Tool registry reference (external)
        self._tool_semantic_index: dict[str, list[str]] = {}
        self._tool_dependency_map: dict[str, list[str]] = {}

        # User model reference
        self._user_preferences: dict[str, Any] = {}
        self._user_tone_profile: dict[str, Any] = {}

        # Performance tracking
        self._phase_timers: dict[CognitivePhase, list[float]] = defaultdict(list)
        self._strategy_stats: dict[str, dict[str, float]] = defaultdict(
            lambda: {"successes": 0, "failures": 0, "avg_time_ms": 0.0}
        )

        logger.info(
            f"Cognitive Engine initialized: agent={agent_id}, "
            f"strategy_overrides={list(self.config.strategy_overrides.keys())}"
        )

    # ── Properties ───────────────────────────────────────

    @property
    def metrics(self) -> CognitiveMetrics:
        """Get the current cognitive metrics snapshot."""
        return self._metrics

    @property
    def cycle_count(self) -> int:
        """Total number of completed cognitive cycles."""
        return self._metrics.cycles_completed + self._metrics.cycles_failed

    @property
    def success_rate(self) -> float:
        """Success rate across all completed cycles."""
        total = self.cycle_count
        if total == 0:
            return 0.0
        return self._metrics.cycles_completed / total

    # ── Cognitive Loop ───────────────────────────────────

    async def run_cycle(
        self,
        user_input: str,
        strategy: CognitiveStrategy = CognitiveStrategy.FAST,
        session_id: str = "",
        available_tools: list[str] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        external_context: dict[str, Any] | None = None,
    ) -> CognitiveCycleResult:
        """Execute a complete cognitive cycle.

        This is the primary entry point. It orchestrates all six phases
        of the cognitive loop, applying the selected strategy to tune
        depth, breadth, and resource allocation.

        Args:
            user_input: The raw user message or task description.
            strategy: Cognitive strategy to apply (fast, thorough, creative, analytical).
            session_id: Optional session identifier for context linking.
            available_tools: List of tool names available for execution.
            conversation_history: Recent conversation turns for context.
            external_context: Additional context from external sources.

        Returns:
            A complete CognitiveCycleResult with all phase outputs and metrics.
        """
        cycle_start = time.time()
        effective = self.config.get_effective_config(strategy)

        cycle_result = CognitiveCycleResult(strategy=strategy)
        self._active_cycle = cycle_result

        logger.info(
            f"Starting cognitive cycle {cycle_result.cycle_id} "
            f"with strategy={strategy.value}, input_len={len(user_input)}"
        )

        try:
            # Phase 1: Perceive
            perception = await self._phase_perceive(user_input, session_id)
            cycle_result.perception = perception
            self._record_phase_metrics(CognitivePhase.PERCEIVE, perception.phase_metrics)

            # Phase 2: Understand
            understanding = await self._phase_understand(
                perception, conversation_history or []
            )
            cycle_result.understanding = understanding
            self._record_phase_metrics(CognitivePhase.UNDERSTAND, understanding.phase_metrics)

            # Context Fusion (cross-cutting)
            context_fusion = await self._context_fusion(
                user_input=user_input,
                perception=perception,
                understanding=understanding,
                session_id=session_id,
                conversation_history=conversation_history,
                external_context=external_context,
            )
            cycle_result.context_fusion = context_fusion

            # Intent Resolution (cross-cutting)
            intent_resolution = await self._resolve_intent(
                user_input=user_input,
                perception=perception,
                understanding=understanding,
                context_fusion=context_fusion,
                conversation_history=conversation_history,
            )
            cycle_result.intent_resolution = intent_resolution

            # Phase 3: Reason
            reasoning = await self._phase_reason(
                understanding=understanding,
                context_fusion=context_fusion,
                intent_resolution=intent_resolution,
                strategy=strategy,
                effective=effective,
            )
            cycle_result.reasoning = reasoning
            self._record_phase_metrics(CognitivePhase.REASON, reasoning.phase_metrics)

            # Phase 4: Plan
            plan = await self._phase_plan(
                reasoning=reasoning,
                intent_resolution=intent_resolution,
                available_tools=available_tools or [],
                effective=effective,
            )
            cycle_result.plan = plan
            self._record_phase_metrics(CognitivePhase.PLAN, plan.phase_metrics)

            # Tool Selection (cross-cutting)
            tool_selection = await self._select_tools(
                intent_resolution=intent_resolution,
                plan=plan,
                reasoning=reasoning,
                available_tools=available_tools or [],
                context_fusion=context_fusion,
                effective=effective,
            )
            cycle_result.tool_selection = tool_selection

            # Phase 5: Execute
            execution = await self._phase_execute(
                plan=plan,
                tool_selection=tool_selection,
                context_fusion=context_fusion,
            )
            cycle_result.execution = execution
            self._record_phase_metrics(CognitivePhase.EXECUTE, execution.phase_metrics)

            # Phase 6: Reflect
            reflection = await self._phase_reflect(
                cycle_result=cycle_result,
                strategy=strategy,
                effective=effective,
            )
            cycle_result.reflection = reflection
            self._record_phase_metrics(CognitivePhase.REFLECT, reflection.phase_metrics)

            # Response Synthesis
            response_synthesis = await self._synthesize_response(
                cycle_result=cycle_result,
                context_fusion=context_fusion,
                intent_resolution=intent_resolution,
            )
            cycle_result.response_synthesis = response_synthesis

            cycle_result.success = True

        except Exception as exc:
            logger.error(
                f"Cognitive cycle {cycle_result.cycle_id} failed: {exc}",
                exc_info=True,
            )
            cycle_result.success = False
            cycle_result.error_message = str(exc)

        cycle_result.total_elapsed_ms = (time.time() - cycle_start) * 1000

        # Update metrics
        self._update_metrics(cycle_result, strategy)

        # Store cycle
        self._cycle_history.append(cycle_result)
        if len(self._cycle_history) > 200:
            self._cycle_history = self._cycle_history[-100:]

        self._active_cycle = None

        logger.info(
            f"Cognitive cycle {cycle_result.cycle_id} completed: "
            f"success={cycle_result.success}, "
            f"elapsed={cycle_result.total_elapsed_ms:.0f}ms"
        )
        return cycle_result

    # ── Phase 1: Perceive ────────────────────────────────

    async def _phase_perceive(
        self, user_input: str, session_id: str,
    ) -> PerceptionResult:
        """Perceive raw input: extract entities, detect language, estimate complexity."""
        phase_start = time.time()
        metrics = PhaseMetrics(
            phase=CognitivePhase.PERCEIVE,
            state=PhaseState.IN_PROGRESS,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        perception = PerceptionResult(
            raw_input=PerceptionInput(
                content=user_input,
                session_id=session_id,
                agent_id=self.agent_id,
            ),
        )

        # Entity extraction (keyword-based for offline operation)
        perception.keyword_set = self._extract_keywords(user_input)
        perception.extracted_entities = self._extract_entities_heuristic(user_input)

        # Complexity estimation
        perception.complexity_estimate = self._estimate_complexity(user_input)

        # Sentiment heuristic
        perception.sentiment = self._detect_sentiment_heuristic(user_input)

        metrics.state = PhaseState.COMPLETED
        metrics.completed_at = datetime.now(timezone.utc).isoformat()
        metrics.elapsed_ms = (time.time() - phase_start) * 1000
        metrics.confidence = 0.9
        metrics.metadata = {
            "keyword_count": len(perception.keyword_set),
            "entity_count": len(perception.extracted_entities),
        }
        perception.phase_metrics = metrics

        logger.debug(
            f"Perception complete: {len(perception.keyword_set)} keywords, "
            f"{len(perception.extracted_entities)} entities, "
            f"complexity={perception.complexity_estimate:.2f}"
        )
        return perception

    # ── Phase 2: Understand ──────────────────────────────

    async def _phase_understand(
        self,
        perception: PerceptionResult,
        conversation_history: list[dict[str, Any]],
    ) -> UnderstandingResult:
        """Understand: semantic parsing, domain classification, constraint identification."""
        phase_start = time.time()
        metrics = PhaseMetrics(
            phase=CognitivePhase.UNDERSTAND,
            state=PhaseState.IN_PROGRESS,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        user_input = perception.raw_input.content if perception.raw_input else ""

        understanding = UnderstandingResult()

        # Domain classification
        understanding.domain_classification = self._classify_domain(
            user_input, perception.keyword_set
        )

        # Task type inference
        understanding.task_type = self._infer_task_type(
            user_input, understanding.domain_classification
        )

        # Semantic parse
        understanding.semantic_parse = {
            "subject": self._extract_subject_heuristic(user_input),
            "action": self._extract_action_heuristic(user_input),
            "object": self._extract_object_heuristic(user_input),
            "modifiers": self._extract_modifiers_heuristic(user_input),
        }

        # Constraint identification
        understanding.identified_constraints = self._identify_constraints(user_input)

        # Ambiguity detection
        understanding.ambiguity_flags = self._detect_ambiguity(
            user_input, conversation_history
        )

        metrics.state = PhaseState.COMPLETED
        metrics.completed_at = datetime.now(timezone.utc).isoformat()
        metrics.elapsed_ms = (time.time() - phase_start) * 1000
        metrics.confidence = 0.85
        metrics.metadata = {
            "domain": understanding.domain_classification,
            "task_type": understanding.task_type,
            "ambiguity_count": len(understanding.ambiguity_flags),
        }
        understanding.phase_metrics = metrics

        logger.debug(
            f"Understanding complete: domain={understanding.domain_classification}, "
            f"task={understanding.task_type}, "
            f"ambiguities={len(understanding.ambiguity_flags)}"
        )
        return understanding

    # ── Phase 3: Reason ──────────────────────────────────

    async def _phase_reason(
        self,
        understanding: UnderstandingResult,
        context_fusion: ContextFusion,
        intent_resolution: IntentResolution,
        strategy: CognitiveStrategy,
        effective: dict[str, Any],
    ) -> ReasoningResult:
        """Reason: apply reasoning strategy, generate hypotheses, trace evidence."""
        phase_start = time.time()
        metrics = PhaseMetrics(
            phase=CognitivePhase.REASON,
            state=PhaseState.IN_PROGRESS,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        reasoning = ReasoningResult()

        # Select reasoning strategy based on cognitive strategy
        reasoning.reasoning_strategy = self._select_reasoning_strategy(
            strategy, understanding.task_type
        )

        # Generate reasoning trace
        max_depth = effective.get("reasoning_depth", self.config.reasoning_depth)
        reasoning.reasoning_trace = self._generate_reasoning_trace(
            understanding=understanding,
            intent=intent_resolution,
            context_fusion=context_fusion,
            max_depth=max_depth,
        )

        # Generate hypotheses
        reasoning.hypotheses = self._generate_hypotheses(
            understanding=understanding,
            context_fusion=context_fusion,
        )

        # Extract intermediate conclusions
        reasoning.intermediate_conclusions = self._extract_conclusions(
            reasoning.reasoning_trace
        )

        # Build evidence chain
        reasoning.evidence_chain = self._build_evidence_chain(
            context_fusion=context_fusion,
            reasoning_trace=reasoning.reasoning_trace,
        )

        metrics.state = PhaseState.COMPLETED
        metrics.completed_at = datetime.now(timezone.utc).isoformat()
        metrics.elapsed_ms = (time.time() - phase_start) * 1000
        metrics.confidence = 0.8
        metrics.metadata = {
            "strategy": reasoning.reasoning_strategy,
            "trace_depth": len(reasoning.reasoning_trace),
            "hypothesis_count": len(reasoning.hypotheses),
        }
        reasoning.phase_metrics = metrics

        logger.debug(
            f"Reasoning complete: strategy={reasoning.reasoning_strategy}, "
            f"depth={len(reasoning.reasoning_trace)}, "
            f"hypotheses={len(reasoning.hypotheses)}"
        )
        return reasoning

    # ── Phase 4: Plan ────────────────────────────────────

    async def _phase_plan(
        self,
        reasoning: ReasoningResult,
        intent_resolution: IntentResolution,
        available_tools: list[str],
        effective: dict[str, Any],
    ) -> PlanResult:
        """Plan: decompose into sub-tasks, identify dependencies, find parallel groups."""
        phase_start = time.time()
        metrics = PhaseMetrics(
            phase=CognitivePhase.PLAN,
            state=PhaseState.IN_PROGRESS,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        plan = PlanResult()

        # Decompose based on intent and reasoning
        plan.sub_tasks = self._decompose_task(
            intent=intent_resolution,
            reasoning=reasoning,
            available_tools=available_tools,
        )

        # Build dependency graph
        plan.dependency_graph = self._build_dependency_graph(plan.sub_tasks)

        # Identify parallel groups
        plan.parallel_groups = self._identify_parallel_groups(
            plan.sub_tasks, plan.dependency_graph
        )

        # Determine critical path
        plan.critical_path = self._compute_critical_path(
            plan.sub_tasks, plan.dependency_graph
        )

        # Estimate effort
        plan.total_estimated_effort = self._estimate_effort(plan.sub_tasks)

        metrics.state = PhaseState.COMPLETED
        metrics.completed_at = datetime.now(timezone.utc).isoformat()
        metrics.elapsed_ms = (time.time() - phase_start) * 1000
        metrics.confidence = 0.75
        metrics.metadata = {
            "sub_task_count": len(plan.sub_tasks),
            "parallel_groups": len(plan.parallel_groups),
            "critical_path_len": len(plan.critical_path),
        }
        plan.phase_metrics = metrics

        logger.debug(
            f"Planning complete: {len(plan.sub_tasks)} sub-tasks, "
            f"{len(plan.parallel_groups)} parallel groups"
        )
        return plan

    # ── Phase 5: Execute ─────────────────────────────────

    async def _phase_execute(
        self,
        plan: PlanResult,
        tool_selection: ToolSelection,
        context_fusion: ContextFusion,
    ) -> ExecutionResult:
        """Execute: dispatch tool calls, collect results, handle failures."""
        phase_start = time.time()
        metrics = PhaseMetrics(
            phase=CognitivePhase.EXECUTE,
            state=PhaseState.IN_PROGRESS,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        execution = ExecutionResult(
            execution_strategy=tool_selection.execution_strategy,
        )

        # Record tool calls from selection
        for tool_info in tool_selection.selected_tools:
            execution.tool_calls.append({
                "tool": tool_info.get("name", "unknown"),
                "arguments": tool_info.get("arguments", {}),
                "reason": tool_info.get("reason", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # Simulate tool results (in production, actual tool execution is delegated)
        for tool_call in execution.tool_calls:
            execution.tool_results.append({
                "tool": tool_call["tool"],
                "status": "dispatched",
                "result_preview": f"Tool '{tool_call['tool']}' dispatched for execution",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            execution.completed_steps += 1

        execution.failed_steps = 0

        metrics.state = PhaseState.COMPLETED
        metrics.completed_at = datetime.now(timezone.utc).isoformat()
        metrics.elapsed_ms = (time.time() - phase_start) * 1000
        metrics.confidence = 0.7
        metrics.metadata = {
            "tools_dispatched": len(execution.tool_calls),
            "strategy": execution.execution_strategy.value,
        }
        execution.phase_metrics = metrics

        logger.debug(
            f"Execution complete: {execution.completed_steps} tools dispatched, "
            f"strategy={execution.execution_strategy.value}"
        )
        return execution

    # ── Phase 6: Reflect ─────────────────────────────────

    async def _phase_reflect(
        self,
        cycle_result: CognitiveCycleResult,
        strategy: CognitiveStrategy,
        effective: dict[str, Any],
    ) -> ReflectionResult:
        """Reflect: self-assess quality, identify issues, generate lessons learned."""
        phase_start = time.time()
        metrics = PhaseMetrics(
            phase=CognitivePhase.REFLECT,
            state=PhaseState.IN_PROGRESS,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        reflection = ReflectionResult()

        max_depth = effective.get("reflection_depth", self.config.reflection_depth)

        # Self-assessment scoring
        reflection.self_assessment_score = self._compute_self_assessment(cycle_result)

        # Quality issue detection
        reflection.quality_issues = self._detect_quality_issues(
            cycle_result, max_depth
        )

        # Improvement suggestions
        reflection.improvement_suggestions = self._generate_improvement_suggestions(
            cycle_result, reflection.quality_issues
        )

        # Lessons learned
        reflection.lessons_learned = self._extract_lessons(cycle_result)

        # Correctness check
        reflection.correctness_check = self._check_correctness(cycle_result)

        metrics.state = PhaseState.COMPLETED
        metrics.completed_at = datetime.now(timezone.utc).isoformat()
        metrics.elapsed_ms = (time.time() - phase_start) * 1000
        metrics.confidence = 0.65
        metrics.metadata = {
            "self_assessment": reflection.self_assessment_score,
            "issues_found": len(reflection.quality_issues),
            "correctness": reflection.correctness_check,
        }
        reflection.phase_metrics = metrics

        logger.debug(
            f"Reflection complete: score={reflection.self_assessment_score:.2f}, "
            f"issues={len(reflection.quality_issues)}, "
            f"correct={reflection.correctness_check}"
        )
        return reflection

    # ── Context Fusion Layer ─────────────────────────────

    async def _context_fusion(
        self,
        user_input: str,
        perception: PerceptionResult,
        understanding: UnderstandingResult,
        session_id: str,
        conversation_history: list[dict[str, Any]] | None,
        external_context: dict[str, Any] | None,
    ) -> ContextFusion:
        """Combine context from multiple sources with attention-based ranking.

        This is the Context Fusion Layer that aggregates context from memory,
        knowledge graph, current session, tool outputs, and user model, then
        applies attention mechanisms to prioritize the most relevant fragments.
        """
        fragments: list[ContextFragment] = []

        # Source 1: Current session / conversation history
        if conversation_history:
            for i, turn in enumerate(conversation_history[-10:]):
                content = turn.get("content", "") if isinstance(turn, dict) else str(turn)
                fragments.append(ContextFragment(
                    source=ContextSource.CURRENT_SESSION,
                    content=content,
                    relevance_score=0.7 + (i * 0.02),  # recent = more relevant
                    token_count=self._estimate_tokens(content),
                ))

        # Source 2: Memory store
        for stored in self._context_store.get(ContextSource.MEMORY, []):
            relevance = self._compute_memory_relevance(stored, user_input, perception.keyword_set)
            if relevance > 0.3:
                fragments.append(ContextFragment(
                    source=ContextSource.MEMORY,
                    content=stored.content,
                    relevance_score=relevance,
                    token_count=stored.token_count,
                    metadata=stored.metadata,
                ))

        # Source 3: Knowledge graph
        for stored in self._context_store.get(ContextSource.KNOWLEDGE_GRAPH, []):
            relevance = self._compute_knowledge_relevance(stored, understanding)
            if relevance > 0.4:
                fragments.append(ContextFragment(
                    source=ContextSource.KNOWLEDGE_GRAPH,
                    content=stored.content,
                    relevance_score=relevance,
                    token_count=stored.token_count,
                    metadata=stored.metadata,
                ))

        # Source 4: User model
        if self._user_preferences:
            user_context = json.dumps(self._user_preferences, ensure_ascii=False)
            fragments.append(ContextFragment(
                source=ContextSource.USER_MODEL,
                content=user_context,
                relevance_score=0.6,
                token_count=self._estimate_tokens(user_context),
            ))

        # Source 5: External context
        if external_context:
            for key, value in external_context.items():
                content = f"{key}: {value}"
                fragments.append(ContextFragment(
                    source=ContextSource.TOOL_OUTPUTS,
                    content=content,
                    relevance_score=0.5,
                    token_count=self._estimate_tokens(content),
                    metadata={"source_key": key},
                ))

        # Apply attention mechanism
        if self.config.enable_attention_mechanism and fragments:
            fragments = self._apply_attention_ranking(fragments, user_input)

        # Sort by attention weight (descending)
        fragments.sort(key=lambda f: f.attention_weight, reverse=True)

        # Context window management with intelligent truncation
        total_tokens = 0
        kept_fragments: list[ContextFragment] = []
        pruned_count = 0

        for fragment in fragments:
            if total_tokens + fragment.token_count <= self.config.max_context_window_tokens:
                kept_fragments.append(fragment)
                total_tokens += fragment.token_count
            else:
                pruned_count += 1

        # Build fused context string
        fused_parts = []
        for fragment in kept_fragments:
            fused_parts.append(f"[{fragment.source.value}] {fragment.content}")

        fused_context = "\n\n".join(fused_parts)

        # Compute attention distribution
        attention_dist: dict[str, float] = {}
        for fragment in kept_fragments:
            source_key = fragment.source.value
            attention_dist[source_key] = attention_dist.get(source_key, 0.0) + fragment.attention_weight

        # Normalize attention distribution
        total_attention = sum(attention_dist.values()) or 1.0
        attention_dist = {k: round(v / total_attention, 3) for k, v in attention_dist.items()}

        # Source breakdown
        source_breakdown: dict[str, int] = {}
        for fragment in kept_fragments:
            source_key = fragment.source.value
            source_breakdown[source_key] = source_breakdown.get(source_key, 0) + 1

        fusion = ContextFusion(
            fragments=kept_fragments,
            fused_context=fused_context,
            total_tokens=total_tokens,
            pruned_fragments=pruned_count,
            attention_distribution=attention_dist,
            source_breakdown=source_breakdown,
        )

        logger.debug(
            f"Context fusion: {len(kept_fragments)} fragments kept, "
            f"{pruned_count} pruned, {total_tokens} tokens, "
            f"attention={attention_dist}"
        )
        return fusion

    def _apply_attention_ranking(
        self, fragments: list[ContextFragment], query: str,
    ) -> list[ContextFragment]:
        """Apply attention mechanism to rank context fragments by relevance.

        Uses a multi-factor attention scoring:
          1. Semantic similarity to the user query (keyword overlap)
          2. Source priority weighting
          3. Recency bias
          4. Metadata quality indicators
        """
        query_lower = query.lower()
        query_keywords = set(query_lower.split())

        source_weights = {
            ContextSource.CURRENT_SESSION: 1.0,
            ContextSource.MEMORY: 0.7,
            ContextSource.KNOWLEDGE_GRAPH: 0.8,
            ContextSource.USER_MODEL: 0.6,
            ContextSource.PERSONA: 0.5,
            ContextSource.IDENTITY: 0.5,
            ContextSource.TOOL_OUTPUTS: 0.4,
        }

        for fragment in fragments:
            content_lower = fragment.content.lower()

            # Factor 1: Keyword overlap (semantic similarity proxy)
            content_words = set(content_lower.split())
            overlap = len(query_keywords & content_words)
            keyword_score = min(overlap / max(len(query_keywords), 1), 1.0)

            # Factor 2: Source priority
            source_weight = source_weights.get(fragment.source, 0.5)

            # Factor 3: Recency (more recent = higher)
            recency_score = 0.5
            try:
                ts = datetime.fromisoformat(fragment.timestamp.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                recency_score = max(0.1, 1.0 - (age_hours / 168))  # decay over 1 week
            except (ValueError, TypeError):
                pass

            # Factor 4: Metadata quality
            metadata_score = 0.5
            if fragment.metadata:
                meta = fragment.metadata
                if meta.get("confidence", 0) > 0.7:
                    metadata_score += 0.2
                if meta.get("verified", False):
                    metadata_score += 0.3

            # Composite attention weight
            fragment.attention_weight = (
                keyword_score * 0.40
                + source_weight * 0.25
                + recency_score * 0.15
                + fragment.relevance_score * 0.10
                + metadata_score * 0.10
            )

        # Keep only top_k
        if len(fragments) > self.config.attention_top_k:
            fragments.sort(key=lambda f: f.attention_weight, reverse=True)
            fragments = fragments[:self.config.attention_top_k]

        return fragments

    # ── Intent Resolution Pipeline ──────────────────────

    async def _resolve_intent(
        self,
        user_input: str,
        perception: PerceptionResult,
        understanding: UnderstandingResult,
        context_fusion: ContextFusion,
        conversation_history: list[dict[str, Any]] | None,
    ) -> IntentResolution:
        """Multi-level intent parsing: explicit, implicit, latent.

        The Intent Resolution Pipeline performs:
          1. Explicit intent extraction from the surface text
          2. Implicit intent inference from conversation history
          3. Latent intent discovery from user model and context patterns
          4. Intent disambiguation when multiple candidates exist
          5. Intent-to-action mapping with confidence scoring
        """
        resolution = IntentResolution()

        # Level 1: Explicit intent
        explicit_intent = self._extract_explicit_intent(
            user_input, perception.keyword_set, understanding.task_type
        )
        resolution.primary_intent = explicit_intent["intent"]
        resolution.intent_category = explicit_intent["category"]
        resolution.confidence = explicit_intent["confidence"]
        resolution.intent_level = IntentLevel.EXPLICIT

        # Level 2: Implicit intent (from conversation history)
        if conversation_history and len(conversation_history) >= 2:
            implicit_intent = self._infer_implicit_intent(
                user_input, conversation_history, understanding
            )
            if implicit_intent["confidence"] > resolution.confidence:
                resolution.primary_intent = implicit_intent["intent"]
                resolution.intent_level = IntentLevel.IMPLICIT
                resolution.confidence = implicit_intent["confidence"]

        # Level 3: Latent intent (from user model)
        if self._user_preferences:
            latent_intent = self._discover_latent_intent(
                user_input, self._user_preferences, understanding
            )
            if latent_intent["confidence"] > 0.5:
                resolution.alternative_intents.append(latent_intent)

        # Intent disambiguation
        if (
            self.config.enable_intent_disambiguation
            and resolution.confidence < self.config.min_confidence_threshold
        ):
            resolution = self._disambiguate_intent(
                resolution, understanding, conversation_history
            )

        # Confidence level assignment
        resolution.confidence_level = self._confidence_to_level(resolution.confidence)

        # Intent-to-action mapping
        resolution.intent_to_action_mapping = self._map_intent_to_action(
            resolution, understanding
        )

        # Store in intent history
        self._intent_history.append(resolution)
        if len(self._intent_history) > 50:
            self._intent_history = self._intent_history[-25:]

        logger.debug(
            f"Intent resolution: '{resolution.primary_intent}' "
            f"(level={resolution.intent_level.value}, "
            f"confidence={resolution.confidence:.2f})"
        )
        return resolution

    def _extract_explicit_intent(
        self, user_input: str, keywords: list[str], task_type: str,
    ) -> dict[str, Any]:
        """Extract explicitly stated intent from the surface text."""
        input_lower = user_input.lower()

        intent_patterns = {
            "explain": {"category": "information_query", "keywords": ["explain", "what is", "how does", "describe", "tell me about"]},
            "create": {"category": "task_execution", "keywords": ["create", "build", "make", "generate", "write", "implement"]},
            "analyze": {"category": "analysis", "keywords": ["analyze", "examine", "evaluate", "assess", "review", "audit"]},
            "debug": {"category": "troubleshooting", "keywords": ["debug", "fix", "error", "bug", "issue", "problem", "not working"]},
            "plan": {"category": "planning", "keywords": ["plan", "schedule", "organize", "roadmap", "strategy", "approach"]},
            "search": {"category": "information_query", "keywords": ["search", "find", "look up", "lookup", "research"]},
            "learn": {"category": "learning", "keywords": ["learn", "study", "understand", "teach", "tutorial", "guide"]},
            "summarize": {"category": "information_query", "keywords": ["summarize", "summary", "tldr", "brief", "recap"]},
            "code": {"category": "code_generation", "keywords": ["code", "function", "class", "script", "program", "refactor"]},
            "decide": {"category": "decision_support", "keywords": ["should i", "which", "better", "recommend", "suggest", "advice"]},
        }

        best_match = {"intent": "general_chat", "category": "conversation", "confidence": 0.5}
        best_score = 0

        for intent_name, pattern in intent_patterns.items():
            score = 0
            for kw in pattern["keywords"]:
                if kw in input_lower:
                    score += 1
            score = score / max(len(pattern["keywords"]), 1)

            # Boost if task_type matches
            if task_type == pattern["category"]:
                score += 0.2

            if score > best_score:
                best_score = score
                best_match = {
                    "intent": intent_name,
                    "category": pattern["category"],
                    "confidence": min(score, 0.95),
                }

        return best_match

    def _infer_implicit_intent(
        self,
        user_input: str,
        conversation_history: list[dict[str, Any]],
        understanding: UnderstandingResult,
    ) -> dict[str, Any]:
        """Infer implicit intent from conversation history and context."""
        # Look at the last few turns for patterns
        recent_turns = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history

        follow_up_patterns = {
            "tell me more": "explain",
            "why": "explain",
            "how": "explain",
            "what about": "search",
            "can you also": "create",
            "and then": "plan",
            "what else": "search",
            "is that correct": "analyze",
            "check": "analyze",
        }

        for turn in recent_turns:
            content = turn.get("content", "") if isinstance(turn, dict) else str(turn)
            content_lower = content.lower()
            for pattern, intent in follow_up_patterns.items():
                if pattern in content_lower:
                    return {
                        "intent": intent,
                        "category": understanding.task_type,
                        "confidence": 0.75,
                        "reason": f"follow-up pattern: '{pattern}'",
                    }

        return {"intent": "general_chat", "category": "conversation", "confidence": 0.3}

    def _discover_latent_intent(
        self,
        user_input: str,
        user_preferences: dict[str, Any],
        understanding: UnderstandingResult,
    ) -> dict[str, Any]:
        """Discover latent intent from user model patterns."""
        input_lower = user_input.lower()

        # Check if user has a history of certain patterns
        frequent_domains = user_preferences.get("frequent_domains", [])
        preferred_tools = user_preferences.get("preferred_tools", [])

        for domain in frequent_domains:
            if domain in input_lower:
                return {
                    "intent": f"latent_{domain}_exploration",
                    "category": understanding.task_type,
                    "confidence": 0.55,
                    "reason": f"user frequently explores {domain}",
                }

        return {"intent": "general_chat", "category": "conversation", "confidence": 0.2}

    def _disambiguate_intent(
        self,
        resolution: IntentResolution,
        understanding: UnderstandingResult,
        conversation_history: list[dict[str, Any]] | None,
    ) -> IntentResolution:
        """Disambiguate intent when confidence is below threshold."""
        if understanding.ambiguity_flags:
            resolution.disambiguation_notes = (
                f"Ambiguity detected: {', '.join(understanding.ambiguity_flags)}. "
                f"Using best-guess intent '{resolution.primary_intent}' "
                f"with adjusted confidence."
            )
            # Slightly reduce confidence to reflect uncertainty
            resolution.confidence = max(resolution.confidence * 0.85, 0.3)

        # Check intent history for patterns
        if self._intent_history:
            recent_intents = [
                h.primary_intent for h in self._intent_history[-5:]
            ]
            if resolution.primary_intent in recent_intents:
                resolution.confidence = min(resolution.confidence * 1.1, 0.95)

        return resolution

    def _map_intent_to_action(
        self,
        resolution: IntentResolution,
        understanding: UnderstandingResult,
    ) -> dict[str, Any]:
        """Map resolved intent to concrete actions."""
        action_map = {
            "explain": {"action_type": "generate_explanation", "requires_tools": False, "expected_depth": "comprehensive"},
            "create": {"action_type": "execute_task", "requires_tools": True, "expected_depth": "thorough"},
            "analyze": {"action_type": "perform_analysis", "requires_tools": True, "expected_depth": "deep"},
            "debug": {"action_type": "troubleshoot", "requires_tools": True, "expected_depth": "iterative"},
            "plan": {"action_type": "generate_plan", "requires_tools": False, "expected_depth": "structured"},
            "search": {"action_type": "information_retrieval", "requires_tools": True, "expected_depth": "broad"},
            "learn": {"action_type": "educational_response", "requires_tools": False, "expected_depth": "scaffolded"},
            "summarize": {"action_type": "summarize_content", "requires_tools": False, "expected_depth": "concise"},
            "code": {"action_type": "code_generation", "requires_tools": True, "expected_depth": "precise"},
            "decide": {"action_type": "decision_support", "requires_tools": False, "expected_depth": "comparative"},
            "general_chat": {"action_type": "conversational_response", "requires_tools": False, "expected_depth": "natural"},
        }

        return action_map.get(
            resolution.primary_intent,
            {"action_type": "general_response", "requires_tools": False, "expected_depth": "balanced"},
        )

    # ── Tool Selection Router ────────────────────────────

    async def _select_tools(
        self,
        intent_resolution: IntentResolution,
        plan: PlanResult,
        reasoning: ReasoningResult,
        available_tools: list[str],
        context_fusion: ContextFusion,
        effective: dict[str, Any],
    ) -> ToolSelection:
        """Semantic tool matching based on intent and context.

        The Tool Selection Router performs:
          1. Semantic matching of tools to intent and plan
          2. Tool chain composition with dependency resolution
          3. Execution strategy selection (sequential, parallel, conditional)
        """
        selection = ToolSelection()

        if not available_tools:
            logger.debug("No tools available for selection")
            return selection

        # Semantic matching
        semantic_scores = self._semantic_tool_match(
            intent=intent_resolution,
            plan=plan,
            available_tools=available_tools,
            context_fusion=context_fusion,
        )
        selection.semantic_match_scores = semantic_scores

        # Select top tools
        sorted_tools = sorted(semantic_scores.items(), key=lambda x: x[1], reverse=True)
        max_depth = effective.get("max_tool_chain_depth", self.config.max_tool_chain_depth)
        top_tools = sorted_tools[:max_depth]

        for tool_name, score in top_tools:
            if score > 0.2:
                selection.selected_tools.append({
                    "name": tool_name,
                    "score": round(score, 3),
                    "reason": f"semantic match to intent '{intent_resolution.primary_intent}'",
                    "arguments": self._infer_tool_arguments(tool_name, intent_resolution),
                })

        # Tool chain composition
        if len(selection.selected_tools) > 1:
            selection.tool_chain = self._compose_tool_chain(
                selection.selected_tools, plan
            )
            selection.dependency_resolution = self._resolve_tool_dependencies(
                selection.tool_chain
            )

        # Execution strategy selection
        selection.execution_strategy = self._select_execution_strategy(
            selection.selected_tools, plan, intent_resolution
        )

        # Fallback tools
        selection.fallback_tools = self._determine_fallback_tools(
            selection.selected_tools, available_tools
        )

        logger.debug(
            f"Tool selection: {len(selection.selected_tools)} tools, "
            f"strategy={selection.execution_strategy.value}, "
            f"chain_depth={len(selection.tool_chain)}"
        )
        return selection

    def _semantic_tool_match(
        self,
        intent: IntentResolution,
        plan: PlanResult,
        available_tools: list[str],
        context_fusion: ContextFusion,
    ) -> dict[str, float]:
        """Compute semantic relevance scores between tools and the current intent/context."""
        scores: dict[str, float] = {}

        # Tool-intent keyword mapping
        intent_tool_map: dict[str, dict[str, float]] = {
            "search": {"web_search": 0.9, "web_fetch": 0.8, "memory_search": 0.6, "read_file": 0.4},
            "explain": {"web_search": 0.7, "memory_search": 0.5, "read_file": 0.4},
            "create": {"write_file": 0.9, "execute_code": 0.7, "web_search": 0.5},
            "analyze": {"read_file": 0.8, "execute_code": 0.7, "web_search": 0.6, "analyze_data": 0.9},
            "debug": {"read_file": 0.9, "execute_code": 0.9, "web_search": 0.6},
            "code": {"write_file": 0.9, "execute_code": 0.9, "read_file": 0.8},
            "plan": {"web_search": 0.5, "read_file": 0.4},
            "summarize": {"read_file": 0.6, "web_fetch": 0.6},
            "learn": {"web_search": 0.8, "web_fetch": 0.7, "read_file": 0.5},
        }

        tool_scores = intent_tool_map.get(intent.primary_intent, {})

        for tool in available_tools:
            base_score = tool_scores.get(tool, 0.2)

            # Boost from semantic index
            if tool in self._tool_semantic_index:
                index_keywords = self._tool_semantic_index[tool]
                context_text = context_fusion.fused_context.lower()
                matches = sum(1 for kw in index_keywords if kw in context_text)
                base_score += min(matches * 0.05, 0.3)

            # Boost from plan relevance
            for sub_task in plan.sub_tasks:
                task_tools = sub_task.get("tools", [])
                if tool in task_tools:
                    base_score += 0.15
                    break

            scores[tool] = min(base_score, 1.0)

        return scores

    def _compose_tool_chain(
        self,
        selected_tools: list[dict[str, Any]],
        plan: PlanResult,
    ) -> list[list[str]]:
        """Compose selected tools into execution chains with dependency ordering."""
        tool_names = [t["name"] for t in selected_tools]

        # Standard chain patterns
        chain_patterns = {
            "research": [["web_search", "web_fetch"], ["read_file"], ["analyze_data"]],
            "coding": [["read_file"], ["web_search"], ["write_file", "execute_code"]],
            "debugging": [["read_file"], ["execute_code", "web_search"], ["write_file"]],
            "analysis": [["read_file", "web_search"], ["analyze_data", "execute_code"]],
        }

        # Try to match a known pattern
        all_tool_names = set(tool_names)
        for pattern_key, stages in chain_patterns.items():
            pattern_tools = set(t for stage in stages for t in stage)
            if pattern_tools & all_tool_names:
                # Filter stages to only include available tools
                filtered_stages = [
                    [t for t in stage if t in all_tool_names]
                    for stage in stages
                ]
                return [s for s in filtered_stages if s]

        # Default: single-stage chain
        return [tool_names]

    def _resolve_tool_dependencies(
        self, tool_chain: list[list[str]],
    ) -> dict[str, list[str]]:
        """Resolve dependencies between tools in a chain."""
        dependencies: dict[str, list[str]] = {}

        for i, stage in enumerate(tool_chain):
            for tool in stage:
                if i == 0:
                    dependencies[tool] = []
                else:
                    dependencies[tool] = [t for prev_stage in tool_chain[:i] for t in prev_stage]

        return dependencies

    def _select_execution_strategy(
        self,
        selected_tools: list[dict[str, Any]],
        plan: PlanResult,
        intent: IntentResolution,
    ) -> ExecutionStrategy:
        """Select the optimal tool execution strategy."""
        if len(selected_tools) <= 1:
            return ExecutionStrategy.SEQUENTIAL

        if plan.parallel_groups:
            return ExecutionStrategy.PARALLEL

        # For complex intents, prefer conditional execution
        if intent.confidence < 0.7:
            return ExecutionStrategy.CONDITIONAL

        if len(selected_tools) <= self.config.parallel_tool_limit:
            return ExecutionStrategy.PARALLEL

        return ExecutionStrategy.SEQUENTIAL

    def _determine_fallback_tools(
        self,
        selected_tools: list[dict[str, Any]],
        available_tools: list[str],
    ) -> list[str]:
        """Determine fallback tools in case selected tools fail."""
        selected_names = {t["name"] for t in selected_tools}
        return [t for t in available_tools if t not in selected_names][:3]

    def _infer_tool_arguments(
        self, tool_name: str, intent: IntentResolution,
    ) -> dict[str, Any]:
        """Infer reasonable default arguments for a tool based on intent."""
        arg_templates = {
            "web_search": {"query": intent.primary_intent, "max_results": 5},
            "web_fetch": {"url": "", "format": "markdown"},
            "read_file": {"file_path": "", "limit": 500},
            "write_file": {"file_path": "", "content": ""},
            "execute_code": {"language": "python", "code": ""},
            "memory_search": {"query": intent.primary_intent, "limit": 10},
            "analyze_data": {"data_source": "", "analysis_type": intent.primary_intent},
        }
        return arg_templates.get(tool_name, {})

    # ── Response Synthesis ───────────────────────────────

    async def _synthesize_response(
        self,
        cycle_result: CognitiveCycleResult,
        context_fusion: ContextFusion,
        intent_resolution: IntentResolution,
    ) -> ResponseSynthesis:
        """Multi-source response generation combining reasoning, tool outputs, and knowledge.

        The Response Synthesis module:
          1. Combines outputs from reasoning, execution, and context
          2. Adapts tone and style based on user preferences
          3. Provides factual grounding with source attribution
        """
        synthesis = ResponseSynthesis()

        # Determine tone and style from user preferences
        synthesis.tone = self._user_tone_profile.get("tone", "neutral")
        synthesis.style = self._user_tone_profile.get("style", "professional")

        # Build response from multiple sources
        response_parts = []

        # Source 1: Reasoning conclusions
        if cycle_result.reasoning and cycle_result.reasoning.intermediate_conclusions:
            response_parts.append(
                "Based on analysis:\n" +
                "\n".join(f"- {c}" for c in cycle_result.reasoning.intermediate_conclusions[:3])
            )

        # Source 2: Execution results
        if cycle_result.execution and cycle_result.execution.tool_results:
            for result in cycle_result.execution.tool_results[:3]:
                response_parts.append(
                    f"[{result.get('tool', 'tool')}]: {result.get('result_preview', '')}"
                )

        # Source 3: Context fusion insights
        if context_fusion and context_fusion.fragments:
            top_fragments = sorted(
                context_fusion.fragments,
                key=lambda f: f.attention_weight,
                reverse=True,
            )[:3]
            for fragment in top_fragments:
                if fragment.attention_weight > 0.5:
                    response_parts.append(
                        f"[from {fragment.source.value}]: {fragment.content[:200]}"
                    )

        synthesis.final_response = "\n\n".join(response_parts) if response_parts else (
            f"Processed intent '{intent_resolution.primary_intent}' "
            f"with confidence {intent_resolution.confidence:.2f}."
        )

        # Source attribution
        if self.config.enable_source_attribution:
            synthesis.source_attributions = self._build_source_attributions(
                context_fusion, cycle_result
            )
            synthesis.fact_grounding = self._build_fact_grounding(
                context_fusion, cycle_result
            )

        # Alternative formulations
        synthesis.alternative_formulations = self._generate_alternatives(
            synthesis.final_response, synthesis.tone
        )

        synthesis.response_metadata = {
            "intent": intent_resolution.primary_intent,
            "confidence": intent_resolution.confidence,
            "strategy": cycle_result.strategy.value,
            "sources_used": list(context_fusion.source_breakdown.keys()) if context_fusion else [],
        }

        logger.debug(
            f"Response synthesis: tone={synthesis.tone}, "
            f"attributions={len(synthesis.source_attributions)}, "
            f"length={len(synthesis.final_response)}"
        )
        return synthesis

    def _build_source_attributions(
        self,
        context_fusion: ContextFusion,
        cycle_result: CognitiveCycleResult,
    ) -> list[dict[str, Any]]:
        """Build source attribution records for response grounding."""
        attributions = []
        for fragment in context_fusion.fragments[:10]:
            attributions.append({
                "source": fragment.source.value,
                "relevance": round(fragment.attention_weight, 3),
                "fragment_id": fragment.fragment_id,
                "content_preview": fragment.content[:100],
            })
        return attributions

    def _build_fact_grounding(
        self,
        context_fusion: ContextFusion,
        cycle_result: CognitiveCycleResult,
    ) -> list[dict[str, Any]]:
        """Build fact grounding records from verified context."""
        grounding = []
        for fragment in context_fusion.fragments:
            if fragment.metadata.get("verified", False):
                grounding.append({
                    "claim": fragment.content[:200],
                    "source": fragment.source.value,
                    "verification": fragment.metadata.get("verification_method", "unknown"),
                    "confidence": fragment.metadata.get("confidence", 0.5),
                })
        return grounding

    def _generate_alternatives(
        self, primary_response: str, tone: str,
    ) -> list[str]:
        """Generate alternative formulations of the response."""
        if not primary_response:
            return []

        alternatives = []
        if tone == "neutral":
            alternatives.append(primary_response.replace("Based on analysis:", "Here's what I found:"))
        elif tone == "casual":
            alternatives.append(primary_response.replace("Based on analysis:", "So here's the thing:"))
        elif tone == "professional":
            alternatives.append(primary_response.replace("Based on analysis:", "Analysis indicates:"))

        return alternatives[:3]

    # ── Cognitive Metrics ────────────────────────────────

    def _update_metrics(
        self, cycle_result: CognitiveCycleResult, strategy: CognitiveStrategy,
    ):
        """Update cognitive metrics after a completed cycle."""
        if cycle_result.success:
            self._metrics.cycles_completed += 1
        else:
            self._metrics.cycles_failed += 1

        self._metrics.total_time_ms += cycle_result.total_elapsed_ms

        # Reasoning depth
        if cycle_result.reasoning:
            depth = len(cycle_result.reasoning.reasoning_trace)
            n = self._metrics.cycles_completed + self._metrics.cycles_failed
            self._metrics.reasoning_depth_avg = (
                (self._metrics.reasoning_depth_avg * (n - 1) + depth) / max(n, 1)
            )

        # Tool utilization
        if cycle_result.execution:
            total_tools = len(cycle_result.execution.tool_calls)
            completed = cycle_result.execution.completed_steps
            if total_tools > 0:
                util_rate = completed / total_tools
                n = self._metrics.cycles_completed + self._metrics.cycles_failed
                self._metrics.tool_utilization_rate = (
                    (self._metrics.tool_utilization_rate * (n - 1) + util_rate) / max(n, 1)
                )

        # Context relevance
        if cycle_result.context_fusion:
            avg_attention = 0.0
            if cycle_result.context_fusion.fragments:
                avg_attention = sum(
                    f.attention_weight for f in cycle_result.context_fusion.fragments
                ) / max(len(cycle_result.context_fusion.fragments), 1)
            n = self._metrics.cycles_completed + self._metrics.cycles_failed
            self._metrics.context_relevance_avg = (
                (self._metrics.context_relevance_avg * (n - 1) + avg_attention) / max(n, 1)
            )

        # Response quality (from reflection)
        if cycle_result.reflection:
            quality = cycle_result.reflection.self_assessment_score
            n = self._metrics.cycles_completed + self._metrics.cycles_failed
            self._metrics.response_quality_avg = (
                (self._metrics.response_quality_avg * (n - 1) + quality) / max(n, 1)
            )

        # Cognitive load monitoring
        if self.config.enable_cognitive_load_monitoring:
            self._metrics.cognitive_load = self._assess_cognitive_load()

        # Phase breakdown
        for phase in CognitivePhase:
            timers = self._phase_timers.get(phase, [])
            if timers:
                self._metrics.phase_breakdown[phase.value] = sum(timers) / len(timers)

        # Strategy effectiveness
        stats = self._strategy_stats[strategy.value]
        if cycle_result.success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        total = stats["successes"] + stats["failures"]
        stats["avg_time_ms"] = (
            (stats["avg_time_ms"] * (total - 1) + cycle_result.total_elapsed_ms) / max(total, 1)
        )

        self._metrics.strategy_effectiveness = {
            k: {
                "success_rate": round(v["successes"] / max(v["successes"] + v["failures"], 1), 3),
                "total_cycles": int(v["successes"] + v["failures"]),
                "avg_time_ms": round(v["avg_time_ms"], 1),
            }
            for k, v in self._strategy_stats.items()
        }

        # Cycle history
        self._metrics.cycle_history.append({
            "cycle_id": cycle_result.cycle_id,
            "strategy": cycle_result.strategy.value,
            "success": cycle_result.success,
            "elapsed_ms": round(cycle_result.total_elapsed_ms, 1),
            "timestamp": cycle_result.timestamp,
        })

    def _assess_cognitive_load(self) -> CognitiveLoad:
        """Assess current cognitive load based on recent cycle metrics."""
        recent = self._metrics.cycle_history[-10:]
        if not recent:
            return CognitiveLoad.LIGHT

        avg_time = sum(c.get("elapsed_ms", 0) for c in recent) / len(recent)
        failure_rate = sum(1 for c in recent if not c.get("success", True)) / len(recent)

        if failure_rate > 0.3:
            return CognitiveLoad.OVERLOADED
        if avg_time > 5000:
            return CognitiveLoad.HEAVY
        if avg_time > 2000 or failure_rate > 0.15:
            return CognitiveLoad.ELEVATED
        if avg_time > 1000:
            return CognitiveLoad.NORMAL
        return CognitiveLoad.LIGHT

    def _record_phase_metrics(self, phase: CognitivePhase, metrics: PhaseMetrics):
        """Record timing metrics for a phase."""
        self._phase_timers[phase].append(metrics.elapsed_ms)
        if len(self._phase_timers[phase]) > 100:
            self._phase_timers[phase] = self._phase_timers[phase][-50:]

    # ── Context Management ───────────────────────────────

    def inject_context(
        self,
        source: ContextSource,
        content: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Inject context into the engine's context store for future cycles.

        Args:
            source: The source of the context (memory, knowledge graph, etc.).
            content: The context content string.
            metadata: Optional metadata for relevance scoring.
        """
        fragment = ContextFragment(
            source=source,
            content=content,
            token_count=self._estimate_tokens(content),
            metadata=metadata or {},
        )
        self._context_store[source].append(fragment)

        # Prune old entries per source
        if len(self._context_store[source]) > 100:
            self._context_store[source] = self._context_store[source][-50:]

        logger.debug(
            f"Context injected: source={source.value}, "
            f"tokens={fragment.token_count}, "
            f"store_size={len(self._context_store[source])}"
        )

    def set_user_preferences(
        self,
        preferences: dict[str, Any],
        tone_profile: dict[str, Any] | None = None,
    ):
        """Set user model preferences for personalized behavior.

        Args:
            preferences: Dictionary of user preference data.
            tone_profile: Optional tone and style preferences.
        """
        self._user_preferences = preferences
        if tone_profile:
            self._user_tone_profile = tone_profile
        logger.debug(
            f"User preferences updated: {len(preferences)} keys, "
            f"tone={self._user_tone_profile.get('tone', 'neutral')}"
        )

    def register_tool_semantics(
        self,
        tool_name: str,
        semantic_keywords: list[str],
        dependencies: list[str] | None = None,
    ):
        """Register semantic information for a tool to improve matching.

        Args:
            tool_name: The name of the tool.
            semantic_keywords: Keywords that describe the tool's purpose.
            dependencies: Optional list of tools this tool depends on.
        """
        self._tool_semantic_index[tool_name] = semantic_keywords
        if dependencies:
            self._tool_dependency_map[tool_name] = dependencies
        logger.debug(
            f"Tool semantics registered: {tool_name} "
            f"({len(semantic_keywords)} keywords)"
        )

    def clear_context(self, source: ContextSource | None = None):
        """Clear context from the store.

        Args:
            source: Specific source to clear, or None to clear all.
        """
        if source:
            self._context_store[source].clear()
            logger.debug(f"Context cleared for source: {source.value}")
        else:
            self._context_store.clear()
            logger.debug("All context cleared")

    # ── Heuristic Helpers ────────────────────────────────

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "i", "you", "he", "she", "it", "we", "they", "me", "him",
            "her", "us", "them", "my", "your", "his", "its", "our",
            "their", "this", "that", "these", "those", "and", "or",
            "but", "not", "in", "on", "at", "to", "for", "of", "with",
            "from", "by", "about", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "can",
            "will", "just", "should", "now", "do", "does", "did",
            "have", "has", "had", "what", "which", "who", "whom",
            "when", "where", "why", "how", "all", "each", "every",
        }
        words = text.lower().split()
        return list(dict.fromkeys(
            w.strip(".,!?;:()[]{}'\"") for w in words
            if w.strip(".,!?;:()[]{}'\"") not in stop_words
            and len(w.strip(".,!?;:()[]{}'\"")) > 1
        ))[:30]

    def _extract_entities_heuristic(self, text: str) -> list[dict[str, Any]]:
        """Heuristic entity extraction from text."""
        entities = []
        # Simple capitalization-based entity detection
        words = text.split()
        for i, word in enumerate(words):
            clean = word.strip(".,!?;:()[]{}'\"")
            if clean and clean[0].isupper() and len(clean) > 2 and clean.lower() not in {"The", "This", "That", "These", "Those", "There", "Here", "What", "When", "Where", "Why", "How", "Which", "Would", "Could", "Should"}:
                # Check if it's a multi-word entity
                entity_words = [clean]
                j = i + 1
                while j < len(words) and j < i + 3:
                    next_word = words[j].strip(".,!?;:()[]{}'\"")
                    if next_word and next_word[0].isupper():
                        entity_words.append(next_word)
                        j += 1
                    else:
                        break
                entity_name = " ".join(entity_words)
                entities.append({
                    "name": entity_name,
                    "entity_type": "proper_noun",
                    "position": i,
                    "confidence": 0.7,
                })
        return entities[:10]

    def _estimate_complexity(self, text: str) -> float:
        """Estimate the complexity of the input text."""
        word_count = len(text.split())
        char_count = len(text)
        question_count = text.count("?")

        # Base complexity from length
        if word_count < 10:
            base = 0.2
        elif word_count < 50:
            base = 0.4
        elif word_count < 200:
            base = 0.6
        elif word_count < 500:
            base = 0.8
        else:
            base = 0.95

        # Adjust for questions
        if question_count > 1:
            base = min(base + 0.1, 1.0)

        # Adjust for code-like patterns
        code_indicators = ["def ", "class ", "import ", "function", "```", "const ", "let ", "var "]
        if any(ind in text for ind in code_indicators):
            base = min(base + 0.15, 1.0)

        return round(base, 3)

    def _detect_sentiment_heuristic(self, text: str) -> str:
        """Heuristic sentiment detection."""
        text_lower = text.lower()
        positive_words = {"great", "good", "awesome", "excellent", "thanks", "love", "amazing", "wonderful", "fantastic", "happy", "pleased", "helpful"}
        negative_words = {"bad", "terrible", "awful", "hate", "angry", "frustrated", "broken", "error", "wrong", "poor", "useless", "annoying"}

        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def _classify_domain(self, text: str, keywords: list[str]) -> str:
        """Classify the domain of the input."""
        domain_keywords = {
            "technology": ["code", "programming", "software", "api", "server", "database", "algorithm", "app", "website", "cloud", "docker", "git"],
            "science": ["physics", "chemistry", "biology", "math", "science", "experiment", "theory", "formula"],
            "business": ["business", "marketing", "sales", "revenue", "strategy", "startup", "investment", "finance"],
            "creative": ["design", "art", "story", "poem", "music", "creative", "writing", "visual"],
            "education": ["learn", "study", "course", "tutorial", "education", "student", "teacher", "exam"],
            "health": ["health", "medical", "fitness", "diet", "exercise", "doctor", "medicine"],
        }

        text_lower = text.lower()
        scores = {}
        for domain, dom_keywords in domain_keywords.items():
            score = sum(1 for kw in dom_keywords if kw in text_lower)
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"

    def _infer_task_type(self, text: str, domain: str) -> str:
        """Infer the task type from text and domain."""
        text_lower = text.lower()
        patterns = {
            "code": ["implement", "code", "function", "class", "debug", "fix bug", "refactor", "write a script", "program"],
            "research": ["research", "find information", "look up", "what is", "how does", "explain"],
            "analysis": ["analyze", "compare", "evaluate", "assess", "review"],
            "planning": ["plan", "schedule", "organize", "roadmap", "strategy"],
            "creative": ["write a story", "poem", "creative", "design", "brainstorm"],
            "summarization": ["summarize", "summary", "tldr", "brief", "recap"],
            "chat": ["hello", "hi", "hey", "thanks", "how are you"],
        }

        for task_type, keywords in patterns.items():
            if any(kw in text_lower for kw in keywords):
                return task_type

        return "chat"

    def _extract_subject_heuristic(self, text: str) -> str:
        """Extract subject from text heuristically."""
        words = text.split()
        if len(words) >= 3:
            # Try to find subject after "about" or leading noun phrase
            for i, w in enumerate(words):
                if w.lower() == "about" and i + 1 < len(words):
                    return " ".join(words[i + 1:i + 4])
            return words[0] if words[0].lower() not in {"can", "could", "would", "please", "i"} else " ".join(words[:3])
        return text[:50]

    def _extract_action_heuristic(self, text: str) -> str:
        """Extract action verb from text."""
        action_verbs = [
            "explain", "create", "build", "analyze", "debug", "fix", "implement",
            "design", "review", "optimize", "research", "summarize", "translate",
            "compare", "calculate", "generate", "refactor", "test", "deploy",
            "monitor", "schedule", "search", "find", "write", "read", "run",
            "execute", "check", "verify", "validate", "update", "delete", "install",
        ]
        text_lower = text.lower()
        for verb in action_verbs:
            if verb in text_lower:
                return verb
        return "process"

    def _extract_object_heuristic(self, text: str) -> str:
        """Extract object of the action from text."""
        action_verb = self._extract_action_heuristic(text)
        words = text.split()
        for i, w in enumerate(words):
            if w.lower() == action_verb and i + 1 < len(words):
                return " ".join(words[i + 1:i + 5])
        return text.split()[-1] if text.split() else ""

    def _extract_modifiers_heuristic(self, text: str) -> list[str]:
        """Extract modifiers/constraints from text."""
        modifiers = []
        constraint_indicators = ["must", "should", "need to", "have to", "required", "important", "only", "exactly", "at least", "at most", "within", "by", "using", "without"]
        text_lower = text.lower()
        for indicator in constraint_indicators:
            if indicator in text_lower:
                idx = text_lower.index(indicator)
                modifiers.append(text[idx:idx + 50].strip())
        return modifiers[:5]

    def _identify_constraints(self, text: str) -> list[dict[str, Any]]:
        """Identify constraints in the user input."""
        constraints = []
        text_lower = text.lower()

        constraint_patterns = [
            ("time", ["within", "by", "before", "after", "deadline", "in n minutes", "in n hours", "in n days"]),
            ("format", ["in json", "in markdown", "as csv", "as table", "as list", "as bullet"]),
            ("scope", ["only", "just", "specifically", "focus on", "limited to"]),
            ("quality", ["accurately", "precisely", "correctly", "properly", "thoroughly"]),
            ("language", ["in english", "in chinese", "in spanish", "in french", "in german"]),
        ]

        for constraint_type, indicators in constraint_patterns:
            for indicator in indicators:
                if indicator in text_lower:
                    constraints.append({
                        "constraint_type": constraint_type,
                        "indicator": indicator,
                        "is_hard": indicator in {"must", "only", "specifically", "exactly"},
                    })
                    break

        return constraints

    def _detect_ambiguity(
        self,
        text: str,
        conversation_history: list[dict[str, Any]],
    ) -> list[str]:
        """Detect ambiguous elements in the input."""
        ambiguities = []
        text_lower = text.lower()

        ambiguous_terms = {
            "it": "Unclear what 'it' refers to",
            "this": "Unclear what 'this' refers to",
            "that": "Unclear what 'that' refers to",
            "them": "Unclear what 'them' refers to",
            "the thing": "Unclear what 'the thing' is",
            "the same": "Unclear what 'the same' refers to",
        }

        for term, description in ambiguous_terms.items():
            if f" {term} " in f" {text_lower} ":
                if not conversation_history or len(conversation_history) < 1:
                    ambiguities.append(description)

        return ambiguities

    def _select_reasoning_strategy(
        self, strategy: CognitiveStrategy, task_type: str,
    ) -> str:
        """Select the reasoning strategy based on cognitive strategy and task type."""
        mapping = {
            CognitiveStrategy.FAST: {
                "code": "direct",
                "research": "chain_of_thought",
                "default": "balanced",
            },
            CognitiveStrategy.THOROUGH: {
                "code": "decomposition",
                "research": "tree_of_thought",
                "analysis": "decomposition",
                "default": "thorough",
            },
            CognitiveStrategy.CREATIVE: {
                "creative": "tree_of_thought",
                "default": "lateral",
            },
            CognitiveStrategy.ANALYTICAL: {
                "analysis": "decomposition",
                "research": "chain_of_thought",
                "code": "decomposition",
                "default": "analytical",
            },
        }

        strategy_map = mapping.get(strategy, {})
        return strategy_map.get(task_type, strategy_map.get("default", "balanced"))

    def _generate_reasoning_trace(
        self,
        understanding: UnderstandingResult,
        intent: IntentResolution,
        context_fusion: ContextFusion,
        max_depth: int,
    ) -> list[dict[str, Any]]:
        """Generate a structured reasoning trace."""
        trace = []

        # Step 1: Problem framing
        trace.append({
            "step": 1,
            "type": "problem_framing",
            "content": f"Task identified as '{understanding.task_type}' in domain '{understanding.domain_classification}'",
            "confidence": 0.9,
        })

        # Step 2: Intent analysis
        trace.append({
            "step": 2,
            "type": "intent_analysis",
            "content": f"Primary intent: {intent.primary_intent} (confidence: {intent.confidence:.2f})",
            "confidence": intent.confidence,
        })

        # Step 3: Context integration
        context_summary = f"Fused context with {len(context_fusion.fragments)} fragments from {len(context_fusion.source_breakdown)} sources"
        trace.append({
            "step": 3,
            "type": "context_integration",
            "content": context_summary,
            "confidence": 0.8,
        })

        # Step 4-N: Deep reasoning steps
        reasoning_steps = [
            "Identify key entities and relationships",
            "Analyze constraints and requirements",
            "Generate initial hypotheses",
            "Evaluate hypotheses against evidence",
            "Refine conclusions based on context",
            "Formulate final reasoning position",
        ]

        for i, step_content in enumerate(reasoning_steps[:max_depth - 3]):
            trace.append({
                "step": 4 + i,
                "type": "deep_reasoning",
                "content": step_content,
                "confidence": 0.75 - (i * 0.05),
            })

        return trace

    def _generate_hypotheses(
        self,
        understanding: UnderstandingResult,
        context_fusion: ContextFusion,
    ) -> list[dict[str, Any]]:
        """Generate hypotheses from understanding and context."""
        hypotheses = []
        if understanding.ambiguity_flags:
            for flag in understanding.ambiguity_flags:
                hypotheses.append({
                    "hypothesis": f"Address ambiguity: {flag}",
                    "confidence": 0.5,
                    "evidence": ["contextual ambiguity detected"],
                    "status": "pending_verification",
                })

        # Add a primary hypothesis
        hypotheses.append({
            "hypothesis": f"Task is a {understanding.task_type} request in {understanding.domain_classification} domain",
            "confidence": 0.85,
            "evidence": ["keyword analysis", "domain classification", "intent resolution"],
            "status": "accepted",
        })

        return hypotheses

    def _extract_conclusions(
        self, reasoning_trace: list[dict[str, Any]],
    ) -> list[str]:
        """Extract intermediate conclusions from reasoning trace."""
        conclusions = []
        for step in reasoning_trace:
            if step.get("confidence", 0) > 0.7:
                conclusions.append(step["content"])
        return conclusions

    def _build_evidence_chain(
        self,
        context_fusion: ContextFusion,
        reasoning_trace: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build evidence chain from context and reasoning."""
        evidence = []
        for fragment in context_fusion.fragments[:5]:
            if fragment.attention_weight > 0.4:
                evidence.append({
                    "source": fragment.source.value,
                    "content": fragment.content[:150],
                    "weight": round(fragment.attention_weight, 3),
                    "supports": "contextual grounding",
                })
        return evidence

    def _decompose_task(
        self,
        intent: IntentResolution,
        reasoning: ReasoningResult,
        available_tools: list[str],
    ) -> list[dict[str, Any]]:
        """Decompose a task into sub-tasks."""
        sub_tasks = []

        # Standard decomposition patterns
        patterns = {
            "explain": [
                {"id": "s1", "title": "Gather relevant information", "tools": ["web_search", "memory_search"], "estimated_effort": "medium"},
                {"id": "s2", "title": "Organize explanation structure", "tools": [], "estimated_effort": "low"},
                {"id": "s3", "title": "Generate explanation", "tools": [], "estimated_effort": "medium"},
            ],
            "create": [
                {"id": "s1", "title": "Research requirements", "tools": ["web_search", "read_file"], "estimated_effort": "medium"},
                {"id": "s2", "title": "Plan implementation approach", "tools": [], "estimated_effort": "medium"},
                {"id": "s3", "title": "Execute creation", "tools": ["write_file", "execute_code"], "estimated_effort": "high"},
                {"id": "s4", "title": "Verify outcome", "tools": ["execute_code", "read_file"], "estimated_effort": "medium"},
            ],
            "debug": [
                {"id": "s1", "title": "Reproduce the issue", "tools": ["read_file", "execute_code"], "estimated_effort": "medium"},
                {"id": "s2", "title": "Identify root cause", "tools": ["execute_code", "web_search"], "estimated_effort": "high"},
                {"id": "s3", "title": "Implement fix", "tools": ["write_file"], "estimated_effort": "medium"},
                {"id": "s4", "title": "Verify the fix", "tools": ["execute_code"], "estimated_effort": "medium"},
            ],
            "analyze": [
                {"id": "s1", "title": "Collect data", "tools": ["read_file", "web_search"], "estimated_effort": "medium"},
                {"id": "s2", "title": "Process and analyze", "tools": ["execute_code", "analyze_data"], "estimated_effort": "high"},
                {"id": "s3", "title": "Draw conclusions", "tools": [], "estimated_effort": "medium"},
            ],
            "search": [
                {"id": "s1", "title": "Execute search queries", "tools": ["web_search"], "estimated_effort": "medium"},
                {"id": "s2", "title": "Fetch relevant sources", "tools": ["web_fetch"], "estimated_effort": "medium"},
                {"id": "s3", "title": "Synthesize results", "tools": [], "estimated_effort": "low"},
            ],
        }

        pattern = patterns.get(intent.primary_intent, [
            {"id": "s1", "title": "Understand the request", "tools": [], "estimated_effort": "low"},
            {"id": "s2", "title": "Execute the task", "tools": available_tools[:2] if available_tools else [], "estimated_effort": "medium"},
            {"id": "s3", "title": "Verify completion", "tools": [], "estimated_effort": "low"},
        ])

        for task in pattern:
            # Filter tools to only available ones
            task["tools"] = [t for t in task["tools"] if t in available_tools] if available_tools else task["tools"]
            # Add dependencies
            prev_id = f"s{int(task['id'][1:]) - 1}"
            if int(task["id"][1:]) > 1:
                task["depends_on"] = [prev_id]
            else:
                task["depends_on"] = []
            sub_tasks.append(task)

        return sub_tasks

    def _build_dependency_graph(
        self, sub_tasks: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Build a dependency graph from sub-tasks."""
        graph: dict[str, list[str]] = {}
        for task in sub_tasks:
            task_id = task["id"]
            graph[task_id] = task.get("depends_on", [])
        return graph

    def _identify_parallel_groups(
        self,
        sub_tasks: list[dict[str, Any]],
        dependency_graph: dict[str, list[str]],
    ) -> list[list[str]]:
        """Identify groups of sub-tasks that can execute in parallel."""
        # Simple approach: group by dependency level
        levels: dict[int, list[str]] = {}
        resolved: set[str] = set()

        while len(resolved) < len(sub_tasks):
            level = len(levels)
            current_level = []
            for task in sub_tasks:
                task_id = task["id"]
                if task_id in resolved:
                    continue
                deps = dependency_graph.get(task_id, [])
                if all(d in resolved for d in deps):
                    current_level.append(task_id)
                    resolved.add(task_id)
            if current_level:
                levels[level] = current_level

        return [group for group in levels.values() if len(group) > 1]

    def _compute_critical_path(
        self,
        sub_tasks: list[dict[str, Any]],
        dependency_graph: dict[str, list[str]],
    ) -> list[str]:
        """Compute the critical path through sub-tasks."""
        # Simple: collect all task IDs in dependency order
        path = []
        resolved: set[str] = set()
        while len(resolved) < len(sub_tasks):
            for task in sub_tasks:
                task_id = task["id"]
                if task_id in resolved:
                    continue
                deps = dependency_graph.get(task_id, [])
                if all(d in resolved for d in deps):
                    path.append(task_id)
                    resolved.add(task_id)
        return path

    def _estimate_effort(self, sub_tasks: list[dict[str, Any]]) -> str:
        """Estimate total effort across sub-tasks."""
        effort_scores = {"low": 1, "medium": 2, "high": 3}
        total = sum(effort_scores.get(t.get("estimated_effort", "medium"), 2) for t in sub_tasks)
        avg = total / max(len(sub_tasks), 1)
        if avg < 1.5:
            return "low"
        elif avg < 2.5:
            return "medium"
        return "high"

    def _compute_self_assessment(
        self, cycle_result: CognitiveCycleResult,
    ) -> float:
        """Compute a self-assessment score for the cycle."""
        score = 0.5  # baseline

        if cycle_result.perception:
            score += 0.05
        if cycle_result.understanding and not cycle_result.understanding.ambiguity_flags:
            score += 0.1
        if cycle_result.reasoning and len(cycle_result.reasoning.reasoning_trace) > 2:
            score += 0.1
        if cycle_result.plan and cycle_result.plan.sub_tasks:
            score += 0.1
        if cycle_result.execution and cycle_result.execution.completed_steps > 0:
            score += 0.1
        if cycle_result.intent_resolution and cycle_result.intent_resolution.confidence > 0.7:
            score += 0.05

        return min(score, 1.0)

    def _detect_quality_issues(
        self, cycle_result: CognitiveCycleResult, max_depth: int,
    ) -> list[str]:
        """Detect quality issues in the cycle result."""
        issues = []

        if cycle_result.understanding and cycle_result.understanding.ambiguity_flags:
            for flag in cycle_result.understanding.ambiguity_flags[:max_depth]:
                issues.append(f"Ambiguity: {flag}")

        if cycle_result.intent_resolution and cycle_result.intent_resolution.confidence < 0.6:
            issues.append(f"Low intent confidence: {cycle_result.intent_resolution.confidence:.2f}")

        if cycle_result.execution and cycle_result.execution.failed_steps > 0:
            issues.append(f"{cycle_result.execution.failed_steps} execution steps failed")

        if cycle_result.reasoning and len(cycle_result.reasoning.reasoning_trace) < 2:
            issues.append("Insufficient reasoning depth")

        return issues[:max_depth]

    def _generate_improvement_suggestions(
        self,
        cycle_result: CognitiveCycleResult,
        quality_issues: list[str],
    ) -> list[str]:
        """Generate improvement suggestions based on quality issues."""
        suggestions = []

        if any("Ambiguity" in issue for issue in quality_issues):
            suggestions.append("Consider asking clarifying questions before proceeding")

        if any("Low intent confidence" in issue for issue in quality_issues):
            suggestions.append("Enable intent disambiguation or request more context")

        if any("failed" in issue.lower() for issue in quality_issues):
            suggestions.append("Review tool execution failures and adjust tool selection")

        if any("Insufficient reasoning" in issue for issue in quality_issues):
            suggestions.append("Increase reasoning depth for more thorough analysis")

        if not suggestions:
            suggestions.append("Continue with current approach; no issues detected")

        return suggestions

    def _extract_lessons(
        self, cycle_result: CognitiveCycleResult,
    ) -> list[dict[str, Any]]:
        """Extract lessons learned from the cycle."""
        lessons = []

        if cycle_result.success:
            lessons.append({
                "lesson": f"Strategy '{cycle_result.strategy.value}' was effective",
                "category": "strategy_effectiveness",
                "confidence": 0.8,
            })

        if cycle_result.intent_resolution:
            lessons.append({
                "lesson": f"Intent '{cycle_result.intent_resolution.primary_intent}' resolved at {cycle_result.intent_resolution.intent_level.value} level",
                "category": "intent_understanding",
                "confidence": cycle_result.intent_resolution.confidence,
            })

        if cycle_result.reflection and cycle_result.reflection.quality_issues:
            lessons.append({
                "lesson": f"Quality issues detected: {len(cycle_result.reflection.quality_issues)}",
                "category": "quality_awareness",
                "confidence": 0.7,
            })

        return lessons

    def _check_correctness(
        self, cycle_result: CognitiveCycleResult,
    ) -> bool:
        """Check the overall correctness of the cycle."""
        # A cycle is considered correct if:
        # 1. It completed successfully
        # 2. Intent confidence is above threshold
        # 3. No critical quality issues
        if not cycle_result.success:
            return False

        if cycle_result.intent_resolution:
            if cycle_result.intent_resolution.confidence < 0.3:
                return False

        if cycle_result.reflection:
            critical_issues = [
                i for i in cycle_result.reflection.quality_issues
                if "critical" in i.lower() or "error" in i.lower()
            ]
            if critical_issues:
                return False

        return True

    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Map a numeric confidence to a confidence level."""
        if confidence >= 0.9:
            return ConfidenceLevel.CERTAIN
        if confidence >= 0.75:
            return ConfidenceLevel.HIGH
        if confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        if confidence >= 0.3:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNCERTAIN

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the token count of a text string."""
        # Rough estimate: ~4 characters per token
        return max(1, len(text) // 4)

    def _compute_memory_relevance(
        self,
        fragment: ContextFragment,
        user_input: str,
        keywords: list[str],
    ) -> float:
        """Compute relevance of a memory fragment to the current input."""
        content_lower = fragment.content.lower()
        input_lower = user_input.lower()

        # Keyword overlap
        matches = sum(1 for kw in keywords if kw in content_lower)
        keyword_score = matches / max(len(keywords), 1)

        # Direct substring match
        substring_score = 0.0
        if len(input_lower) > 10:
            for i in range(0, len(input_lower) - 10, 10):
                chunk = input_lower[i:i + 20]
                if chunk in content_lower:
                    substring_score = 0.3
                    break

        return min(keyword_score * 0.7 + substring_score + 0.1, 1.0)

    def _compute_knowledge_relevance(
        self,
        fragment: ContextFragment,
        understanding: UnderstandingResult,
    ) -> float:
        """Compute relevance of a knowledge graph fragment."""
        domain = understanding.domain_classification
        content_lower = fragment.content.lower()

        if domain in content_lower:
            return 0.7

        # Check keyword overlap with semantic parse
        semantic_parse = understanding.semantic_parse
        relevant_terms = [
            semantic_parse.get("subject", ""),
            semantic_parse.get("object", ""),
        ]
        matches = sum(1 for term in relevant_terms if term and term.lower() in content_lower)
        return min(0.3 + matches * 0.2, 0.9)

    # ── Statistics & Reporting ───────────────────────────

    def get_metrics_report(self) -> dict[str, Any]:
        """Get a comprehensive metrics report."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "metrics": self._metrics.to_dict(),
            "config": self.config.to_dict(),
            "context_store_sizes": {
                source.value: len(fragments)
                for source, fragments in self._context_store.items()
            },
            "semantic_index_size": len(self._tool_semantic_index),
            "intent_history_size": len(self._intent_history),
            "success_rate": round(self.success_rate, 3),
            "cognitive_load": self._metrics.cognitive_load.value,
        }

    def get_recent_cycles(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent cognitive cycle results."""
        return [c.to_dict() for c in self._cycle_history[-limit:]]

    def get_phase_performance(self) -> dict[str, dict[str, float]]:
        """Get performance statistics per cognitive phase."""
        report = {}
        for phase in CognitivePhase:
            timers = self._phase_timers.get(phase, [])
            if timers:
                report[phase.value] = {
                    "avg_ms": round(sum(timers) / len(timers), 2),
                    "min_ms": round(min(timers), 2),
                    "max_ms": round(max(timers), 2),
                    "count": len(timers),
                }
        return report

    def reset_metrics(self):
        """Reset all cognitive metrics."""
        self._metrics = CognitiveMetrics()
        self._phase_timers.clear()
        self._cycle_history.clear()
        self._strategy_stats.clear()
        logger.info(f"Cognitive metrics reset for agent {self.agent_id}")


# ═══════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════

_cognitive_engine_instance: AgentCognitiveEngine | None = None


def get_cognitive_engine(
    agent_id: str = "default",
    agent_name: str = "Buddy",
    config: CognitiveEngineConfig | None = None,
) -> AgentCognitiveEngine:
    """Get or create the global singleton cognitive engine instance.

    Args:
        agent_id: Identifier for the agent.
        agent_name: Human-readable name for the agent.
        config: Optional configuration. Uses defaults on first creation.

    Returns:
        The global AgentCognitiveEngine singleton.
    """
    global _cognitive_engine_instance
    if _cognitive_engine_instance is None:
        _cognitive_engine_instance = AgentCognitiveEngine(
            agent_id=agent_id,
            agent_name=agent_name,
            config=config,
        )
        logger.info(f"Global cognitive engine singleton created: agent={agent_id}")
    return _cognitive_engine_instance


def reset_cognitive_engine():
    """Reset the global cognitive engine singleton."""
    global _cognitive_engine_instance
    _cognitive_engine_instance = None
    logger.info("Global cognitive engine singleton reset")