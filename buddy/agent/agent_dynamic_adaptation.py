"""
Buddy Dynamic Adaptation Engine - Real-time plan execution monitoring and adaptation.

Provides intelligent runtime adaptation capabilities:
- Continuous plan execution monitoring with checkpoint tracking
- Automatic deviation detection with severity classification
- Intelligent adaptation strategy selection based on deviation type and context
- Learning from past adaptations to improve future responses
- Graceful degradation and fallback chain management
- Adaptation effectiveness metrics and analytics
"""

from __future__ import annotations

import logging
import statistics
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

try:
    from config.settings import settings
except ImportError:
    settings = None  # type: ignore[assignment]

logger = logging.getLogger("buddy.dynamic_adaptation")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class DeviationType(str, Enum):
    """Types of deviations that can occur during plan execution."""
    UNEXPECTED_OUTPUT = "unexpected_output"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    TOOL_FAILURE = "tool_failure"
    CONTEXT_SHIFT = "context_shift"
    NEW_INFORMATION = "new_information"
    USER_INTERRUPTION = "user_interruption"
    QUALITY_DEGRADATION = "quality_degradation"


class AdaptationStrategy(str, Enum):
    """Strategies for adapting a plan in response to deviations."""
    RETRY = "retry"
    SKIP = "skip"
    REPLACE = "replace"
    RESTRUCTURE = "restructure"
    DELEGATE = "delegate"
    FALLBACK = "fallback"
    ESCALATE = "escalate"


class Severity(str, Enum):
    """Severity levels for deviations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SessionStatus(str, Enum):
    """Status of a monitoring session."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ADAPTING = "adapting"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class Checkpoint:
    """A single checkpoint in a plan execution trace."""
    step_id: str
    step_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    output_summary: str = ""
    error_message: str = ""
    duration_ms: float = 0.0
    resource_usage: dict[str, float] = field(default_factory=dict)


@dataclass
class DeviationReport:
    """Report describing a detected deviation from the execution plan."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: DeviationType = DeviationType.UNEXPECTED_OUTPUT
    severity: Severity = Severity.LOW
    description: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    affected_steps: list[str] = field(default_factory=list)
    root_cause_analysis: str = ""
    impact_assessment: str = ""
    recovery_options: list[str] = field(default_factory=list)


@dataclass
class AdaptedPlan:
    """A modified plan produced by the adaptation engine."""
    original_plan_id: str = ""
    new_steps: list[dict[str, Any]] = field(default_factory=list)
    removed_steps: list[str] = field(default_factory=list)
    modified_steps: list[dict[str, Any]] = field(default_factory=list)
    adaptation_strategy: AdaptationStrategy = AdaptationStrategy.RETRY
    rationale: str = ""
    estimated_impact: str = ""
    confidence: float = 0.0
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MonitorSession:
    """A monitoring session tracking a single plan execution."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    plan_id: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    checkpoints: list[Checkpoint] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


@dataclass
class AdaptationLesson:
    """A learned pattern from a past adaptation."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    deviation_type: DeviationType = DeviationType.UNEXPECTED_OUTPUT
    learned_pattern: str = ""
    effectiveness: float = 0.0
    times_encountered: int = 0
    strategy_used: AdaptationStrategy = AdaptationStrategy.RETRY
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ImprovementSuggestion:
    """A proactive suggestion for improving a plan."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    plan_id: str = ""
    category: str = ""
    description: str = ""
    expected_benefit: str = ""
    priority: Severity = Severity.MEDIUM
    suggested_steps: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AdaptationRecord:
    """A complete record of an adaptation event."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    plan_id: str = ""
    session_id: str = ""
    deviation: DeviationReport | None = None
    adapted_plan: AdaptedPlan | None = None
    lesson: AdaptationLesson | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolution_status: str = "pending"


# ═══════════════════════════════════════════════════════════
# Strategy Selection Rules
# ═══════════════════════════════════════════════════════════

# Mapping from deviation type to preferred adaptation strategies in priority order
_STRATEGY_PRIORITY: dict[DeviationType, list[AdaptationStrategy]] = {
    DeviationType.UNEXPECTED_OUTPUT: [
        AdaptationStrategy.REPLACE,
        AdaptationStrategy.RESTRUCTURE,
        AdaptationStrategy.DELEGATE,
    ],
    DeviationType.TIMEOUT: [
        AdaptationStrategy.RETRY,
        AdaptationStrategy.RESTRUCTURE,
        AdaptationStrategy.FALLBACK,
    ],
    DeviationType.RESOURCE_EXHAUSTED: [
        AdaptationStrategy.DELEGATE,
        AdaptationStrategy.FALLBACK,
        AdaptationStrategy.ESCALATE,
    ],
    DeviationType.TOOL_FAILURE: [
        AdaptationStrategy.REPLACE,
        AdaptationStrategy.RETRY,
        AdaptationStrategy.FALLBACK,
    ],
    DeviationType.CONTEXT_SHIFT: [
        AdaptationStrategy.RESTRUCTURE,
        AdaptationStrategy.REPLACE,
        AdaptationStrategy.ESCALATE,
    ],
    DeviationType.NEW_INFORMATION: [
        AdaptationStrategy.RESTRUCTURE,
        AdaptationStrategy.REPLACE,
        AdaptationStrategy.DELEGATE,
    ],
    DeviationType.USER_INTERRUPTION: [
        AdaptationStrategy.RESTRUCTURE,
        AdaptationStrategy.SKIP,
        AdaptationStrategy.ESCALATE,
    ],
    DeviationType.QUALITY_DEGRADATION: [
        AdaptationStrategy.REPLACE,
        AdaptationStrategy.RESTRUCTURE,
        AdaptationStrategy.ESCALATE,
    ],
}

# Severity weight for scoring strategies
_SEVERITY_WEIGHT: dict[Severity, float] = {
    Severity.LOW: 1.0,
    Severity.MEDIUM: 2.0,
    Severity.HIGH: 4.0,
    Severity.CRITICAL: 8.0,
}

# Fallback chains: if primary strategy fails, try next in sequence
_FALLBACK_CHAINS: dict[AdaptationStrategy, list[AdaptationStrategy]] = {
    AdaptationStrategy.RETRY: [AdaptationStrategy.REPLACE, AdaptationStrategy.FALLBACK],
    AdaptationStrategy.SKIP: [AdaptationStrategy.REPLACE, AdaptationStrategy.ESCALATE],
    AdaptationStrategy.REPLACE: [AdaptationStrategy.RESTRUCTURE, AdaptationStrategy.FALLBACK],
    AdaptationStrategy.RESTRUCTURE: [AdaptationStrategy.DELEGATE, AdaptationStrategy.ESCALATE],
    AdaptationStrategy.DELEGATE: [AdaptationStrategy.FALLBACK, AdaptationStrategy.ESCALATE],
    AdaptationStrategy.FALLBACK: [AdaptationStrategy.ESCALATE],
    AdaptationStrategy.ESCALATE: [],
}


# ═══════════════════════════════════════════════════════════
# Dynamic Adaptation Engine
# ═══════════════════════════════════════════════════════════

class DynamicAdaptationEngine:
    """Real-time plan execution monitoring and intelligent adaptation.

    The engine watches plan executions, detects deviations, selects
    appropriate adaptation strategies, and learns from each adaptation
    to improve future responses.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, MonitorSession] = {}
        self._deviations: dict[str, DeviationReport] = {}
        self._adapted_plans: dict[str, AdaptedPlan] = {}
        self._lessons: dict[str, AdaptationLesson] = {}
        self._records: list[AdaptationRecord] = []
        self._callback_registry: dict[str, Callable[[Checkpoint], None]] = {}
        self._strategy_scores: dict[AdaptationStrategy, float] = defaultdict(float)
        self._adaptation_counts: dict[str, int] = defaultdict(int)
        self._fallback_failures: int = 0
        self._total_adaptations: int = 0

    # ── Monitoring ──────────────────────────────────────────────────

    def monitor_execution(
        self, plan_id: str, callback: Callable[[Checkpoint], None] | None = None
    ) -> MonitorSession:
        """Start monitoring a plan execution.

        Creates a new monitoring session that tracks checkpoints, metrics,
        and alerts throughout the plan's lifecycle.

        Args:
            plan_id: Identifier of the plan to monitor.
            callback: Optional callback invoked at each checkpoint.

        Returns:
            A new MonitorSession instance.
        """
        session = MonitorSession(plan_id=plan_id)
        self._sessions[session.id] = session

        if callback is not None:
            self._callback_registry[session.id] = callback

        logger.info(
            f"Monitoring session started: session={session.id} plan={plan_id}"
        )
        return session

    def _record_checkpoint(
        self,
        session_id: str,
        step_id: str,
        step_name: str,
        status: str,
        output_summary: str = "",
        error_message: str = "",
        duration_ms: float = 0.0,
        resource_usage: dict[str, float] | None = None,
    ) -> None:
        """Internal: record a checkpoint in a monitoring session."""
        session = self._sessions.get(session_id)
        if session is None:
            logger.warning(f"Unknown session for checkpoint: {session_id}")
            return

        checkpoint = Checkpoint(
            step_id=step_id,
            step_name=step_name,
            status=status,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            output_summary=output_summary,
            error_message=error_message,
            duration_ms=duration_ms,
            resource_usage=resource_usage or {},
        )
        session.checkpoints.append(checkpoint)

        # Update session-level metrics
        session.metrics["total_steps"] = len(session.checkpoints)
        session.metrics["last_checkpoint_at"] = datetime.now(timezone.utc).isoformat()

        durations = [c.duration_ms for c in session.checkpoints if c.duration_ms > 0]
        if durations:
            session.metrics["avg_step_duration_ms"] = statistics.mean(durations)
            session.metrics["max_step_duration_ms"] = max(durations)

        # Invoke the registered callback
        callback = self._callback_registry.get(session_id)
        if callback is not None:
            try:
                callback(checkpoint)
            except Exception as exc:
                logger.error(f"Callback error for session {session_id}: {exc}")

    # ── Deviation Detection ─────────────────────────────────────────

    def detect_deviation(self, session_id: str) -> DeviationReport | None:
        """Check for deviations in a monitored session.

        Analyzes the session's checkpoints and metrics to detect anomalies
        in execution flow, timing, resource usage, or output quality.

        Args:
            session_id: The monitoring session to analyze.

        Returns:
            A DeviationReport if a deviation is detected, or None.
        """
        session = self._sessions.get(session_id)
        if session is None:
            logger.warning(f"Unknown session for deviation detection: {session_id}")
            return None

        deviation = self._analyze_session_for_deviations(session)
        if deviation is not None:
            self._deviations[deviation.id] = deviation
            self._adaptation_counts[session_id] = (
                self._adaptation_counts.get(session_id, 0) + 1
            )
            session.alerts.append(
                f"[{deviation.severity.value.upper()}] {deviation.type.value}: {deviation.description}"
            )
            session.status = SessionStatus.ADAPTING
            logger.warning(
                f"Deviation detected: {deviation.id} type={deviation.type.value} "
                f"severity={deviation.severity.value} session={session_id}"
            )
        return deviation

    def _analyze_session_for_deviations(
        self, session: MonitorSession
    ) -> DeviationReport | None:
        """Internal: run all deviation detectors against a session."""
        detectors = [
            self._detect_timeout,
            self._detect_tool_failure,
            self._detect_resource_exhaustion,
            self._detect_quality_degradation,
            self._detect_context_shift,
        ]

        for detector in detectors:
            result = detector(session)
            if result is not None:
                return result

        return None

    def _detect_timeout(self, session: MonitorSession) -> DeviationReport | None:
        """Detect if any step has exceeded its timeout threshold."""
        timeout_threshold_ms = getattr(
            settings, "ADAPTATION_TIMEOUT_THRESHOLD_MS", 30000
        ) if settings else 30000
        for cp in session.checkpoints:
            if cp.duration_ms > timeout_threshold_ms and cp.status == "running":
                return DeviationReport(
                    type=DeviationType.TIMEOUT,
                    severity=Severity.HIGH,
                    description=f"Step '{cp.step_name}' exceeded timeout threshold "
                    f"({cp.duration_ms:.0f}ms > {timeout_threshold_ms}ms)",
                    affected_steps=[cp.step_id],
                    root_cause_analysis=(
                        f"Step {cp.step_id} ({cp.step_name}) took longer than "
                        f"the configured timeout of {timeout_threshold_ms}ms. "
                        f"Possible causes: external service latency, large input "
                        f"processing, or infinite loop."
                    ),
                    impact_assessment=(
                        "Blocked execution pipeline; downstream steps cannot "
                        "proceed until this step completes or is skipped."
                    ),
                    recovery_options=[
                        "Retry with reduced input size",
                        "Skip the step and continue with available data",
                        "Delegate to a faster alternative implementation",
                    ],
                )
        return None

    def _detect_tool_failure(self, session: MonitorSession) -> DeviationReport | None:
        """Detect if any tool call has failed."""
        for cp in session.checkpoints:
            if cp.status == "failed" and cp.error_message:
                return DeviationReport(
                    type=DeviationType.TOOL_FAILURE,
                    severity=Severity.HIGH,
                    description=f"Tool failure at step '{cp.step_name}': {cp.error_message}",
                    affected_steps=[cp.step_id],
                    root_cause_analysis=(
                        f"Step {cp.step_id} ({cp.step_name}) failed with error: "
                        f"{cp.error_message}. This may indicate an unavailable "
                        f"tool, invalid input, or permission issue."
                    ),
                    impact_assessment=(
                        "Tool-dependent steps cannot execute. Output quality "
                        "may be degraded if the tool is essential."
                    ),
                    recovery_options=[
                        "Replace the failed tool with an equivalent",
                        "Retry the step with corrected parameters",
                        "Fall back to a manual or simplified approach",
                    ],
                )
        return None

    def _detect_resource_exhaustion(
        self, session: MonitorSession
    ) -> DeviationReport | None:
        """Detect if resource usage has exceeded safe thresholds."""
        memory_threshold = getattr(settings, "ADAPTATION_MEMORY_THRESHOLD_MB", 2048) if settings else 2048
        for cp in session.checkpoints:
            usage = cp.resource_usage
            if usage.get("memory_mb", 0) > memory_threshold:
                return DeviationReport(
                    type=DeviationType.RESOURCE_EXHAUSTED,
                    severity=Severity.CRITICAL,
                    description=(
                        f"Memory usage exceeded threshold at step '{cp.step_name}': "
                        f"{usage['memory_mb']:.0f}MB > {memory_threshold}MB"
                    ),
                    affected_steps=[cp.step_id],
                    root_cause_analysis=(
                        f"Memory usage of {usage['memory_mb']:.0f}MB at step "
                        f"{cp.step_id} exceeds the configured limit of "
                        f"{memory_threshold}MB. Possible memory leak or "
                        f"unusually large intermediate data."
                    ),
                    impact_assessment=(
                        "Critical: system may become unstable. All active "
                        "sessions are at risk of termination."
                    ),
                    recovery_options=[
                        "Delegate processing to a larger instance",
                        "Truncate input data and restart the step",
                        "Escalate to operator for manual intervention",
                    ],
                )
        return None

    def _detect_quality_degradation(
        self, session: MonitorSession
    ) -> DeviationReport | None:
        """Detect if output quality has degraded below acceptable levels."""
        quality_threshold = getattr(settings, "ADAPTATION_QUALITY_THRESHOLD", 0.6) if settings else 0.6
        for cp in session.checkpoints:
            quality = cp.resource_usage.get("quality_score", 1.0)
            if quality < quality_threshold and cp.status == "completed":
                return DeviationReport(
                    type=DeviationType.QUALITY_DEGRADATION,
                    severity=Severity.MEDIUM,
                    description=(
                        f"Output quality below threshold at step '{cp.step_name}': "
                        f"{quality:.2f} < {quality_threshold}"
                    ),
                    affected_steps=[cp.step_id],
                    root_cause_analysis=(
                        f"Quality score of {quality:.2f} for step {cp.step_id} "
                        f"indicates the output may be incomplete, inaccurate, "
                        f"or insufficiently detailed."
                    ),
                    impact_assessment=(
                        "End-user experience may be negatively affected. "
                        "Downstream steps building on low-quality output "
                        "may compound errors."
                    ),
                    recovery_options=[
                        "Replace the step with a higher-quality approach",
                        "Restructure the plan to include a verification step",
                        "Escalate for human review of the output",
                    ],
                )
        return None

    def _detect_context_shift(
        self, session: MonitorSession
    ) -> DeviationReport | None:
        """Detect if the execution context has shifted from the original plan."""
        if len(session.checkpoints) < 2:
            return None

        # Compare recent outputs to detect semantic drift
        recent = session.checkpoints[-3:]
        outputs = [cp.output_summary for cp in recent if cp.output_summary]

        context_drift_threshold = getattr(
            settings, "ADAPTATION_CONTEXT_DRIFT_THRESHOLD", 0.7
        ) if settings else 0.7
        drift_score = self._compute_context_drift(outputs)

        if drift_score > context_drift_threshold:
            return DeviationReport(
                type=DeviationType.CONTEXT_SHIFT,
                severity=Severity.MEDIUM,
                description=(
                    f"Execution context drift detected: score={drift_score:.2f} "
                    f"> threshold={context_drift_threshold}"
                ),
                affected_steps=[cp.step_id for cp in recent],
                root_cause_analysis=(
                    f"Recent step outputs have diverged from the expected "
                    f"execution path (drift score: {drift_score:.2f}). "
                    f"This may indicate the plan is no longer aligned with "
                    f"the original objective."
                ),
                impact_assessment=(
                    "The plan may be pursuing an incorrect or outdated "
                    "objective. Remaining steps may be irrelevant."
                ),
                recovery_options=[
                    "Restructure the remaining plan to align with new context",
                    "Replace divergent steps with corrected alternatives",
                    "Escalate for human review of the plan direction",
                ],
            )
        return None

    def _compute_context_drift(self, outputs: list[str]) -> float:
        """Compute a simple drift score from recent outputs.

        Uses output length variance as a proxy for drift detection.
        """
        if len(outputs) < 2:
            return 0.0

        lengths = [len(o) for o in outputs]
        mean_len = statistics.mean(lengths)
        if mean_len == 0:
            return 0.0

        variance = statistics.variance(lengths) if len(lengths) > 1 else 0.0
        return min(variance / (mean_len * mean_len), 1.0)

    # ── Plan Adaptation ──────────────────────────────────────────────

    def adapt_plan(self, plan_id: str, deviation: DeviationReport) -> AdaptedPlan:
        """Modify a plan based on a detected deviation.

        Selects the best adaptation strategy using historical effectiveness
        data, applies it to restructure the plan, and records the result.

        Args:
            plan_id: Identifier of the plan to adapt.
            deviation: The deviation that triggered the adaptation.

        Returns:
            An AdaptedPlan with the modifications.
        """
        strategy = self._select_strategy(deviation)
        logger.info(
            f"Adapting plan {plan_id}: deviation={deviation.type.value} "
            f"strategy={strategy.value}"
        )

        # Ensure the deviation is registered
        if deviation.id not in self._deviations:
            self._deviations[deviation.id] = deviation

        adapted = self._apply_strategy(plan_id, deviation, strategy)
        self._adapted_plans[adapted.original_plan_id] = adapted
        self._total_adaptations += 1

        # Record the adaptation
        record = AdaptationRecord(
            plan_id=plan_id,
            session_id="",
            deviation=deviation,
            adapted_plan=adapted,
        )
        self._records.append(record)

        return adapted

    def _select_strategy(self, deviation: DeviationReport) -> AdaptationStrategy:
        """Select the best adaptation strategy for a given deviation.

        Considers the deviation type, severity, historical effectiveness of
        each strategy, and applies a scoring model to choose the optimal one.
        """
        candidates = _STRATEGY_PRIORITY.get(deviation.type, [AdaptationStrategy.ESCALATE])
        severity_weight = _SEVERITY_WEIGHT.get(deviation.severity, 1.0)

        best_strategy = AdaptationStrategy.ESCALATE
        best_score = -1.0

        for strategy in candidates:
            # Base score from priority position (higher = earlier in list)
            position = len(candidates) - candidates.index(strategy)
            base_score = float(position) / len(candidates)

            # Historical effectiveness bonus
            historical_score = self._strategy_scores.get(strategy, 0.5)

            # Combined score
            score = (base_score * 0.4) + (historical_score * 0.6)

            # For critical deviations, prefer fallback and escalate
            if deviation.severity == Severity.CRITICAL:
                if strategy in (AdaptationStrategy.FALLBACK, AdaptationStrategy.ESCALATE):
                    score *= 1.5

            if score > best_score:
                best_score = score
                best_strategy = strategy

        return best_strategy

    def _apply_strategy(
        self,
        plan_id: str,
        deviation: DeviationReport,
        strategy: AdaptationStrategy,
    ) -> AdaptedPlan:
        """Apply the selected adaptation strategy to the plan.

        Each strategy modifies the plan differently based on its nature.
        """
        confidence = self._estimate_confidence(strategy, deviation)

        if strategy == AdaptationStrategy.RETRY:
            return AdaptedPlan(
                original_plan_id=plan_id,
                new_steps=[],
                removed_steps=[],
                modified_steps=[
                    {
                        "step_id": step_id,
                        "action": "retry",
                        "max_attempts": 3,
                        "backoff_ms": 1000,
                        "reason": deviation.description,
                    }
                    for step_id in deviation.affected_steps
                ],
                adaptation_strategy=strategy,
                rationale=f"Retrying affected steps with exponential backoff. "
                f"Deviation: {deviation.description}",
                estimated_impact="Minimal delay; plan structure unchanged.",
                confidence=confidence,
            )

        elif strategy == AdaptationStrategy.SKIP:
            return AdaptedPlan(
                original_plan_id=plan_id,
                new_steps=[],
                removed_steps=deviation.affected_steps,
                modified_steps=[],
                adaptation_strategy=strategy,
                rationale=f"Skipping affected steps to preserve plan momentum. "
                f"Deviation: {deviation.description}",
                estimated_impact="Remaining steps proceed; skipped steps may "
                "cause gaps in output.",
                confidence=confidence,
            )

        elif strategy == AdaptationStrategy.REPLACE:
            new_step = {
                "step_id": uuid.uuid4().hex[:12],
                "action": "replacement",
                "replaces": deviation.affected_steps,
                "description": f"Alternative approach for: {deviation.description}",
                "fallback_available": True,
            }
            return AdaptedPlan(
                original_plan_id=plan_id,
                new_steps=[new_step],
                removed_steps=deviation.affected_steps,
                modified_steps=[],
                adaptation_strategy=strategy,
                rationale=f"Replacing affected steps with an alternative. "
                f"Deviation: {deviation.description}",
                estimated_impact="Plan continues with substituted steps; "
                "output parity expected.",
                confidence=confidence,
            )

        elif strategy == AdaptationStrategy.RESTRUCTURE:
            return AdaptedPlan(
                original_plan_id=plan_id,
                new_steps=[
                    {
                        "step_id": uuid.uuid4().hex[:12],
                        "action": "restructured_block",
                        "description": "Restructured plan segment to address deviation",
                        "sub_steps": [
                            {"action": "validate_context", "priority": "high"},
                            {"action": "recompute_dependencies"},
                            {"action": "resume_execution"},
                        ],
                    }
                ],
                removed_steps=deviation.affected_steps,
                modified_steps=[
                    {
                        "step_id": step_id,
                        "action": "reorder",
                        "reason": "Dependency chain restructured",
                    }
                    for step_id in deviation.affected_steps
                ],
                adaptation_strategy=strategy,
                rationale=f"Restructuring plan to accommodate the deviation. "
                f"Deviation: {deviation.description}",
                estimated_impact="Plan topology modified; re-execution of "
                "dependent steps may be required.",
                confidence=confidence,
            )

        elif strategy == AdaptationStrategy.DELEGATE:
            return AdaptedPlan(
                original_plan_id=plan_id,
                new_steps=[
                    {
                        "step_id": uuid.uuid4().hex[:12],
                        "action": "delegate",
                        "target": "specialized_agent",
                        "payload": {
                            "original_step_ids": deviation.affected_steps,
                            "context": deviation.description,
                        },
                    }
                ],
                removed_steps=deviation.affected_steps,
                modified_steps=[],
                adaptation_strategy=strategy,
                rationale=f"Delegating affected steps to a specialized handler. "
                f"Deviation: {deviation.description}",
                estimated_impact="Execution continues in parallel via delegate; "
                "results merged asynchronously.",
                confidence=confidence,
            )

        elif strategy == AdaptationStrategy.FALLBACK:
            return AdaptedPlan(
                original_plan_id=plan_id,
                new_steps=[
                    {
                        "step_id": uuid.uuid4().hex[:12],
                        "action": "fallback",
                        "description": "Simplified fallback execution path",
                        "mode": "degraded",
                    }
                ],
                removed_steps=deviation.affected_steps,
                modified_steps=[],
                adaptation_strategy=strategy,
                rationale=f"Activating fallback path due to unresolved deviation. "
                f"Deviation: {deviation.description}",
                estimated_impact="Reduced functionality; core objectives "
                "preserved through degraded mode.",
                confidence=confidence,
            )

        else:  # ESCALATE
            return AdaptedPlan(
                original_plan_id=plan_id,
                new_steps=[],
                removed_steps=[],
                modified_steps=[
                    {
                        "step_id": step_id,
                        "action": "escalate",
                        "target": "human_operator",
                        "reason": deviation.description,
                    }
                    for step_id in deviation.affected_steps
                ],
                adaptation_strategy=strategy,
                rationale=f"Escalating to human operator. "
                f"Deviation: {deviation.description}",
                estimated_impact="Plan execution paused pending operator input.",
                confidence=confidence,
            )

    def _estimate_confidence(
        self, strategy: AdaptationStrategy, deviation: DeviationReport
    ) -> float:
        """Estimate confidence in the selected strategy.

        Factors in historical effectiveness for this deviation type and
        strategy, plus the severity of the deviation.
        """
        base_confidence = 0.7

        # Historical effectiveness for this strategy
        historical = self._strategy_scores.get(strategy, 0.5)
        base_confidence = (base_confidence + historical) / 2.0

        # Reduce confidence for higher severity
        severity_penalty = {
            Severity.LOW: 0.0,
            Severity.MEDIUM: 0.05,
            Severity.HIGH: 0.15,
            Severity.CRITICAL: 0.25,
        }
        base_confidence -= severity_penalty.get(deviation.severity, 0.0)

        # Boost for frequently successful strategies
        if self._adaptation_counts.get(strategy.value, 0) > 5 and historical > 0.7:
            base_confidence = min(base_confidence + 0.1, 1.0)

        return max(0.1, min(base_confidence, 1.0))

    # ── Learning ─────────────────────────────────────────────────────

    def learn_from_deviation(self, deviation_id: str) -> AdaptationLesson | None:
        """Learn from a past deviation to improve future adaptations.

        Analyzes the deviation and its resolution to extract patterns
        that can be reused for similar future deviations.

        Args:
            deviation_id: Identifier of the deviation to learn from.

        Returns:
            An AdaptationLesson with the learned pattern, or None.
        """
        deviation = self._deviations.get(deviation_id)
        if deviation is None:
            logger.warning(f"Unknown deviation for learning: {deviation_id}")
            return None

        # Find related adaptation records
        related_records = [
            r for r in self._records
            if r.deviation is not None and r.deviation.id == deviation_id
        ]

        # Determine the strategy that was used
        strategy_used = AdaptationStrategy.ESCALATE
        if related_records and related_records[0].adapted_plan is not None:
            strategy_used = related_records[0].adapted_plan.adaptation_strategy

        # Check if we already have a lesson for this deviation type
        existing_lesson = self._find_existing_lesson(deviation.type)
        if existing_lesson is not None:
            existing_lesson.times_encountered += 1
            existing_lesson.last_updated = datetime.now(timezone.utc)
            existing_lesson.effectiveness = self._compute_lesson_effectiveness(
                deviation.type, strategy_used
            )
            self._update_strategy_score(strategy_used, existing_lesson.effectiveness)
            logger.info(
                f"Updated existing lesson: {existing_lesson.id} "
                f"type={deviation.type.value} times={existing_lesson.times_encountered}"
            )
            return existing_lesson

        # Create a new lesson
        lesson = AdaptationLesson(
            deviation_type=deviation.type,
            learned_pattern=self._extract_pattern(deviation),
            effectiveness=0.5,
            times_encountered=1,
            strategy_used=strategy_used,
        )
        self._lessons[lesson.id] = lesson

        # Update the strategy score based on this initial learning
        self._update_strategy_score(strategy_used, 0.5)

        # Link the lesson to the adaptation records
        for record in related_records:
            record.lesson = lesson
            record.resolution_status = "learned"

        logger.info(
            f"New lesson created: {lesson.id} type={deviation.type.value} "
            f"pattern='{lesson.learned_pattern}'"
        )
        return lesson

    def _find_existing_lesson(
        self, deviation_type: DeviationType
    ) -> AdaptationLesson | None:
        """Find an existing lesson for the given deviation type."""
        for lesson in self._lessons.values():
            if lesson.deviation_type == deviation_type:
                return lesson
        return None

    def _extract_pattern(self, deviation: DeviationReport) -> str:
        """Extract a reusable pattern from a deviation report."""
        return (
            f"When {deviation.type.value.replace('_', ' ')} occurs at "
            f"step(s) {', '.join(deviation.affected_steps[:3])}, "
            f"with severity {deviation.severity.value}, "
            f"root cause: {deviation.root_cause_analysis[:100]}"
        )

    def _compute_lesson_effectiveness(
        self, deviation_type: DeviationType, strategy: AdaptationStrategy
    ) -> float:
        """Compute how effective the learned pattern has been."""
        related_records = [
            r for r in self._records
            if r.deviation is not None
            and r.deviation.type == deviation_type
            and r.adapted_plan is not None
            and r.adapted_plan.adaptation_strategy == strategy
        ]

        if not related_records:
            return 0.5

        resolved = sum(1 for r in related_records if r.resolution_status == "resolved")
        return resolved / len(related_records)

    def _update_strategy_score(
        self, strategy: AdaptationStrategy, effectiveness: float
    ) -> None:
        """Update the rolling score for an adaptation strategy.

        Uses exponential moving average to smooth score changes.
        """
        alpha = 0.3
        current = self._strategy_scores.get(strategy, 0.5)
        self._strategy_scores[strategy] = (alpha * effectiveness) + (
            (1 - alpha) * current
        )

    # ── Proactive Suggestions ────────────────────────────────────────

    def suggest_improvements(self, plan_id: str) -> list[ImprovementSuggestion]:
        """Generate proactive suggestions for improving a plan.

        Analyzes adaptation history, lesson effectiveness, and common
        failure patterns to propose plan improvements before deviations occur.

        Args:
            plan_id: Identifier of the plan to analyze.

        Returns:
            A list of ImprovementSuggestion instances.
        """
        suggestions: list[ImprovementSuggestion] = []

        # Suggestion 1: Add verification steps for plans with quality degradation history
        quality_degradation_count = sum(
            1 for r in self._records
            if r.deviation is not None
            and r.deviation.type == DeviationType.QUALITY_DEGRADATION
            and r.plan_id == plan_id
        )
        if quality_degradation_count > 0:
            suggestions.append(
                ImprovementSuggestion(
                    plan_id=plan_id,
                    category="quality_assurance",
                    description=(
                        "Add automated verification steps after critical plan "
                        "stages to catch quality degradation early."
                    ),
                    expected_benefit=(
                        f"Based on {quality_degradation_count} previous quality "
                        "degradation events, adding verification could reduce "
                        "rework by 40-60%."
                    ),
                    priority=Severity.HIGH,
                    suggested_steps=[
                        {
                            "action": "verify_output",
                            "stage": "post_execution",
                            "criteria": ["completeness", "accuracy", "format"],
                        }
                    ],
                )
            )

        # Suggestion 2: Add timeouts for plans with timeout history
        timeout_count = sum(
            1 for r in self._records
            if r.deviation is not None
            and r.deviation.type == DeviationType.TIMEOUT
            and r.plan_id == plan_id
        )
        if timeout_count > 0:
            suggestions.append(
                ImprovementSuggestion(
                    plan_id=plan_id,
                    category="resilience",
                    description=(
                        "Add explicit timeout boundaries and circuit breakers "
                        "to prevent execution stalls."
                    ),
                    expected_benefit=(
                        f"With {timeout_count} previous timeouts, circuit "
                        "breakers would enable automatic fallback and reduce "
                        "total execution time."
                    ),
                    priority=Severity.HIGH,
                    suggested_steps=[
                        {
                            "action": "add_timeout",
                            "timeout_ms": 30000,
                            "on_timeout": "fallback",
                        },
                        {
                            "action": "add_circuit_breaker",
                            "failure_threshold": 3,
                            "recovery_timeout_ms": 60000,
                        },
                    ],
                )
            )

        # Suggestion 3: Parallelize independent steps based on dependency analysis
        if len(self._records) > 0:
            suggestions.append(
                ImprovementSuggestion(
                    plan_id=plan_id,
                    category="performance",
                    description=(
                        "Identify and parallelize independent steps to reduce "
                        "total execution time."
                    ),
                    expected_benefit=(
                        "Parallelizing independent steps can reduce execution "
                        "time by 30-50% for multi-step plans."
                    ),
                    priority=Severity.MEDIUM,
                    suggested_steps=[
                        {
                            "action": "analyze_dependencies",
                            "output": "dependency_graph",
                        },
                        {
                            "action": "parallelize",
                            "target": "independent_branches",
                        },
                    ],
                )
            )

        # Suggestion 4: Lessons-based suggestions
        for lesson in self._lessons.values():
            if lesson.times_encountered >= 3 and lesson.effectiveness > 0.6:
                suggestions.append(
                    ImprovementSuggestion(
                        plan_id=plan_id,
                        category="learned_pattern",
                        description=(
                            f"Apply learned pattern for {lesson.deviation_type.value}: "
                            f"{lesson.learned_pattern[:80]}..."
                        ),
                        expected_benefit=(
                            f"This pattern has been effective {lesson.effectiveness:.0%} "
                            f"of the time across {lesson.times_encountered} encounters."
                        ),
                        priority=Severity.LOW,
                        suggested_steps=[
                            {
                                "action": "apply_learned_pattern",
                                "lesson_id": lesson.id,
                                "strategy": lesson.strategy_used.value,
                            }
                        ],
                    )
                )

        return suggestions

    # ── History & Metrics ─────────────────────────────────────────────

    def get_adaptation_history(self) -> list[AdaptationRecord]:
        """Get the full adaptation history.

        Returns:
            All recorded adaptation events in chronological order.
        """
        return list(self._records)

    def get_effectiveness_metrics(self) -> dict[str, Any]:
        """Get aggregated adaptation effectiveness metrics."""
        if not self._records:
            return {
                "total_adaptations": 0,
                "strategy_scores": {},
                "avg_confidence": 0.0,
                "lessons_count": 0,
                "fallback_failures": 0,
            }

        confidences = [
            r.adapted_plan.confidence
            for r in self._records
            if r.adapted_plan is not None
        ]

        return {
            "total_adaptations": self._total_adaptations,
            "total_records": len(self._records),
            "strategy_scores": {
                s.value: round(score, 3)
                for s, score in self._strategy_scores.items()
            },
            "avg_confidence": round(statistics.mean(confidences), 3) if confidences else 0.0,
            "lessons_count": len(self._lessons),
            "fallback_failures": self._fallback_failures,
            "strategy_usage": dict(self._adaptation_counts),
        }

    # ── State Management ──────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all state: sessions, deviations, plans, lessons, and records."""
        self._sessions.clear()
        self._deviations.clear()
        self._adapted_plans.clear()
        self._lessons.clear()
        self._records.clear()
        self._callback_registry.clear()
        self._strategy_scores.clear()
        self._adaptation_counts.clear()
        self._fallback_failures = 0
        self._total_adaptations = 0
        logger.info("DynamicAdaptationEngine state fully reset")


# ═══════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════

_dynamic_adaptation_instance: DynamicAdaptationEngine | None = None


def get_dynamic_adaptation() -> DynamicAdaptationEngine:
    """Get or create the global singleton DynamicAdaptationEngine instance.

    Returns:
        The global DynamicAdaptationEngine singleton.
    """
    global _dynamic_adaptation_instance
    if _dynamic_adaptation_instance is None:
        _dynamic_adaptation_instance = DynamicAdaptationEngine()
        logger.info("Global dynamic adaptation engine singleton created")
    return _dynamic_adaptation_instance


def reset_dynamic_adaptation() -> None:
    """Reset the global dynamic adaptation engine singleton."""
    global _dynamic_adaptation_instance
    if _dynamic_adaptation_instance is not None:
        _dynamic_adaptation_instance.reset()
    _dynamic_adaptation_instance = None
    logger.info("Global dynamic adaptation engine singleton reset")