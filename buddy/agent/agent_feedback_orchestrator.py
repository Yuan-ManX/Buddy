"""
Buddy Agent Feedback Orchestrator - Collects, routes, and acts on feedback.

Collects feedback from all sources (user interactions, execution results,
self-reflection, system metrics) to continuously improve agent behavior.
Routes signals through a priority-based routing layer and executes concrete
actions to update skills, memory, personas, model preferences, and strategies.

Key capabilities:
- Multi-source feedback collection (explicit, implicit, execution, self-reflection, system)
- Priority-based routing with configurable routing rules
- Action execution with impact tracking
- Analytics with trend detection, anomaly detection, and velocity tracking
"""

from __future__ import annotations

import json
import logging
import math
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.feedback_orchestrator")


class FeedbackSource(str, Enum):
    """Origin of a feedback signal."""
    USER_EXPLICIT = "user_explicit"
    USER_IMPLICIT = "user_implicit"
    EXECUTION = "execution"
    SELF_REFLECTION = "self_reflection"
    SYSTEM = "system"


class FeedbackSeverity(str, Enum):
    """Severity level of a feedback signal."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    """Concrete action that can be taken based on feedback."""
    UPDATE_SKILL_PARAMETERS = "update_skill_parameters"
    ADJUST_MEMORY_WEIGHTS = "adjust_memory_weights"
    MODIFY_PERSONA_TRAITS = "modify_persona_traits"
    RECALIBRATE_MODEL_PREFERENCES = "recalibrate_model_preferences"
    EVOLVE_STRATEGY = "evolve_strategy"
    FLAG_FOR_REVIEW = "flag_for_review"
    ADJUST_THRESHOLD = "adjust_threshold"
    REBALANCE_PRIORITIES = "rebalance_priorities"


class TargetModule(str, Enum):
    """Module that a feedback signal or action targets."""
    SKILLS = "skills"
    MEMORY = "memory"
    PERSONA = "persona"
    MODEL_SELECTION = "model_selection"
    STRATEGY = "strategy"
    REASONING = "reasoning"
    TOOL_EXECUTION = "tool_execution"
    RESPONSE_GENERATION = "response_generation"
    CONTEXT_MANAGEMENT = "context_management"
    GENERAL = "general"


class ActionStatus(str, Enum):
    """Status of an action after execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RoutingRuleType(str, Enum):
    """Type of routing rule for matching signals."""
    EXACT_SOURCE = "exact_source"
    EXACT_TARGET = "exact_target"
    SEVERITY_THRESHOLD = "severity_threshold"
    PATTERN_MATCH = "pattern_match"
    ALWAYS = "always"


@dataclass
class FeedbackSignal:
    """A feedback signal from a source, targeting a module for improvement.

    Attributes:
        signal_id: Unique identifier for this signal.
        severity: How critical this feedback is.
        confidence: Confidence of the source in this signal (0.0 to 1.0).
        source: Which feedback source generated this signal.
        target_module: Module that should receive this feedback.
        payload: Arbitrary data payload describing the feedback.
        timestamp: When the signal was created.
        metadata: Additional contextual information.
    """
    signal_id: str = field(default_factory=lambda: f"fsig-{uuid.uuid4().hex[:12]}")
    severity: FeedbackSeverity = FeedbackSeverity.MEDIUM
    confidence: float = 0.5
    source: FeedbackSource = FeedbackSource.SYSTEM
    target_module: TargetModule = TargetModule.GENERAL
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "source": self.source.value,
            "target_module": self.target_module.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class RoutingRule:
    """A rule for routing feedback signals to action handlers.

    Attributes:
        rule_id: Unique identifier for this rule.
        rule_type: How this rule matches incoming signals.
        match_value: Value to match against (source, target, severity, or pattern).
        action_type: Action to route matched signals to.
        priority: Priority of this rule (lower number = higher priority).
        enabled: Whether this rule is currently active.
        cooldown_seconds: Minimum seconds between triggering this rule.
        last_triggered: Timestamp of last trigger.
    """
    rule_id: str = field(default_factory=lambda: f"rule-{uuid.uuid4().hex[:8]}")
    rule_type: RoutingRuleType = RoutingRuleType.ALWAYS
    match_value: str = ""
    action_type: ActionType = ActionType.FLAG_FOR_REVIEW
    priority: int = 100
    enabled: bool = True
    cooldown_seconds: float = 0.0
    last_triggered: float = 0.0

    def matches(self, signal: FeedbackSignal) -> bool:
        if not self.enabled:
            return False
        if self.cooldown_seconds > 0:
            elapsed = time.time() - self.last_triggered
            if elapsed < self.cooldown_seconds:
                return False
        if self.rule_type == RoutingRuleType.ALWAYS:
            return True
        if self.rule_type == RoutingRuleType.EXACT_SOURCE:
            return signal.source.value == self.match_value
        if self.rule_type == RoutingRuleType.EXACT_TARGET:
            return signal.target_module.value == self.match_value
        if self.rule_type == RoutingRuleType.SEVERITY_THRESHOLD:
            severities = list(FeedbackSeverity)
            signal_idx = severities.index(signal.severity)
            threshold_idx = severities.index(FeedbackSeverity(self.match_value))
            return signal_idx >= threshold_idx
        if self.rule_type == RoutingRuleType.PATTERN_MATCH:
            payload_str = json.dumps(signal.payload)
            return self.match_value.lower() in payload_str.lower()
        return False


@dataclass
class FeedbackAction:
    """A concrete action derived from a feedback signal.

    Attributes:
        action_id: Unique identifier for this action.
        action_type: Type of action to perform.
        signal_id: Signal that triggered this action.
        target: Target module for this action.
        parameters: Parameters for the action.
        expected_impact: Description of what this action should achieve.
        status: Current execution status.
        created_at: When the action was created.
        executed_at: When the action was executed.
        completed_at: When the action completed.
        error_message: Error message if the action failed.
    """
    action_id: str = field(default_factory=lambda: f"fact-{uuid.uuid4().hex[:12]}")
    action_type: ActionType = ActionType.FLAG_FOR_REVIEW
    signal_id: str = ""
    target: TargetModule = TargetModule.GENERAL
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_impact: str = ""
    status: ActionStatus = ActionStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    executed_at: str = ""
    completed_at: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "signal_id": self.signal_id,
            "target": self.target.value,
            "parameters": self.parameters,
            "expected_impact": self.expected_impact,
            "status": self.status.value,
            "created_at": self.created_at,
            "executed_at": self.executed_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }


@dataclass
class ActionResult:
    """Result of executing a feedback action.

    Attributes:
        action_id: ID of the action that was executed.
        success: Whether the action succeeded.
        impact_score: Measured impact of the action (0.0 to 1.0).
        details: Additional details about the result.
        changed_parameters: Parameters that were actually changed.
        timestamp: When the result was recorded.
    """
    action_id: str = ""
    success: bool = False
    impact_score: float = 0.0
    details: str = ""
    changed_parameters: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "success": self.success,
            "impact_score": self.impact_score,
            "details": self.details,
            "changed_parameters": self.changed_parameters,
            "timestamp": self.timestamp,
        }


@dataclass
class SignalTrend:
    """Trend data for a specific feedback metric over a time window.

    Attributes:
        metric_name: Name of the metric being tracked.
        direction: Trend direction (increasing, decreasing, stable).
        slope: Rate of change per hour.
        data_points: Number of data points in the window.
        current_value: Most recent value.
        window_start: Start of the analysis window.
        window_end: End of the analysis window.
    """
    metric_name: str = ""
    direction: str = "stable"
    slope: float = 0.0
    data_points: int = 0
    current_value: float = 0.0
    window_start: str = ""
    window_end: str = ""


@dataclass
class FeedbackAnomaly:
    """A detected anomaly in feedback patterns.

    Attributes:
        anomaly_id: Unique identifier for this anomaly.
        description: Human-readable description of the anomaly.
        metric_name: Which metric showed the anomaly.
        expected_value: Expected normal value.
        actual_value: Detected value.
        deviation_std: Number of standard deviations from mean.
        severity: Severity of the anomaly.
        detected_at: When the anomaly was detected.
    """
    anomaly_id: str = field(default_factory=lambda: f"anom-{uuid.uuid4().hex[:8]}")
    description: str = ""
    metric_name: str = ""
    expected_value: float = 0.0
    actual_value: float = 0.0
    deviation_std: float = 0.0
    severity: FeedbackSeverity = FeedbackSeverity.MEDIUM
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FeedbackAnalytics:
    """Analytics collected from feedback signals over time.

    Attributes:
        trends: Detected trends across metrics.
        anomalies: Detected anomalies.
        velocity: Rate of improvement (signal processing rate).
        impact_scores: Impact scores of recent actions.
        window_hours: Analysis window size in hours.
        total_signals_in_window: Number of signals in the window.
        signals_by_source: Breakdown of signals by source.
        signals_by_severity: Breakdown of signals by severity.
        average_confidence: Average confidence of signals in the window.
        generated_at: When this analytics snapshot was generated.
    """
    trends: list[SignalTrend] = field(default_factory=list)
    anomalies: list[FeedbackAnomaly] = field(default_factory=list)
    velocity: float = 0.0
    impact_scores: list[float] = field(default_factory=list)
    window_hours: float = 0.0
    total_signals_in_window: int = 0
    signals_by_source: dict[str, int] = field(default_factory=dict)
    signals_by_severity: dict[str, int] = field(default_factory=dict)
    average_confidence: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "trends": [{"metric": t.metric_name, "direction": t.direction, "slope": t.slope}
                       for t in self.trends],
            "anomalies": [{"id": a.anomaly_id, "description": a.description, "severity": a.severity.value}
                          for a in self.anomalies],
            "velocity": self.velocity,
            "impact_scores": self.impact_scores,
            "window_hours": self.window_hours,
            "total_signals_in_window": self.total_signals_in_window,
            "signals_by_source": self.signals_by_source,
            "signals_by_severity": self.signals_by_severity,
            "average_confidence": self.average_confidence,
            "generated_at": self.generated_at,
        }


@dataclass
class FeedbackOrchestratorStats:
    """Runtime statistics for the feedback orchestrator.

    Attributes:
        total_signals: Total signals collected since start or reset.
        routed_count: Total signals that matched at least one routing rule.
        actioned_count: Total actions executed.
        action_success_count: Total actions that succeeded.
        action_failure_count: Total actions that failed.
        average_routing_time_ms: Average time to route a signal in milliseconds.
        average_action_time_ms: Average time to execute an action in milliseconds.
        registered_rules: Number of registered routing rules.
        pending_actions: Number of actions still pending.
        uptime_seconds: Seconds since orchestrator was created or reset.
    """
    total_signals: int = 0
    routed_count: int = 0
    actioned_count: int = 0
    action_success_count: int = 0
    action_failure_count: int = 0
    average_routing_time_ms: float = 0.0
    average_action_time_ms: float = 0.0
    registered_rules: int = 0
    pending_actions: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_signals": self.total_signals,
            "routed_count": self.routed_count,
            "actioned_count": self.actioned_count,
            "action_success_count": self.action_success_count,
            "action_failure_count": self.action_failure_count,
            "success_rate": (
                self.action_success_count / max(self.actioned_count, 1)
            ),
            "average_routing_time_ms": self.average_routing_time_ms,
            "average_action_time_ms": self.average_action_time_ms,
            "registered_rules": self.registered_rules,
            "pending_actions": self.pending_actions,
            "uptime_seconds": self.uptime_seconds,
        }


class FeedbackOrchestrator:
    """Collects, routes, and acts on feedback from all sources.

    Implements a feedback loop that continuously improves agent behavior
    by collecting signals from multiple sources, routing them through
    priority-based rules, and executing concrete improvement actions.

    Usage:
        orchestrator = FeedbackOrchestrator()
        signal = orchestrator.collect_feedback(FeedbackSource.USER_EXPLICIT, {
            "rating": 4, "comment": "Good answer but too verbose"
        })
        actions = orchestrator.route_feedback(signal)
        results = orchestrator.execute_actions(actions)
        analytics = orchestrator.get_analytics(window_hours=24)
    """

    # Default routing rules applied to all new orchestrators
    DEFAULT_RULES: list[dict[str, Any]] = [
        {"rule_type": "exact_source", "match_value": "user_explicit",
         "action_type": "modify_persona_traits", "priority": 1},
        {"rule_type": "exact_source", "match_value": "user_implicit",
         "action_type": "adjust_memory_weights", "priority": 2},
        {"rule_type": "exact_source", "match_value": "execution",
         "action_type": "update_skill_parameters", "priority": 1},
        {"rule_type": "exact_source", "match_value": "self_reflection",
         "action_type": "recalibrate_model_preferences", "priority": 2},
        {"rule_type": "exact_source", "match_value": "system",
         "action_type": "evolve_strategy", "priority": 3},
        {"rule_type": "severity_threshold", "match_value": "critical",
         "action_type": "flag_for_review", "priority": 0, "cooldown_seconds": 60},
        {"rule_type": "severity_threshold", "match_value": "high",
         "action_type": "adjust_threshold", "priority": 5},
        {"rule_type": "pattern_match", "match_value": "error",
         "action_type": "flag_for_review", "priority": 3, "cooldown_seconds": 30},
    ]

    def __init__(self) -> None:
        self._signal_history: deque[FeedbackSignal] = deque(maxlen=10000)
        self._action_history: deque[FeedbackAction] = deque(maxlen=5000)
        self._result_history: deque[ActionResult] = deque(maxlen=5000)
        self._routing_rules: list[RoutingRule] = []
        self._pending_actions: list[FeedbackAction] = []
        self._start_time: float = time.time()
        self._routing_times: deque[float] = deque(maxlen=1000)
        self._action_times: deque[float] = deque(maxlen=1000)

        self._load_default_rules()

    def _load_default_rules(self) -> None:
        for rule_def in self.DEFAULT_RULES:
            rule = RoutingRule(
                rule_type=RoutingRuleType(rule_def["rule_type"]),
                match_value=rule_def.get("match_value", ""),
                action_type=ActionType(rule_def["action_type"]),
                priority=rule_def.get("priority", 100),
                cooldown_seconds=rule_def.get("cooldown_seconds", 0.0),
            )
            self._routing_rules.append(rule)

    def collect_feedback(self, source: FeedbackSource, signal_data: dict[str, Any]) -> FeedbackSignal:
        """Collect a feedback signal from a source.

        Args:
            source: The origin of the feedback.
            signal_data: Raw feedback data including severity, confidence,
                target_module, and payload.

        Returns:
            The constructed FeedbackSignal.
        """
        severity_str = signal_data.get("severity", "medium")
        severity = FeedbackSeverity(severity_str) if severity_str in (
            s.value for s in FeedbackSeverity) else FeedbackSeverity.MEDIUM

        target_str = signal_data.get("target_module", "general")
        target = TargetModule(target_str) if target_str in (
            t.value for t in TargetModule) else TargetModule.GENERAL

        signal = FeedbackSignal(
            severity=severity,
            confidence=float(signal_data.get("confidence", 0.5)),
            source=source,
            target_module=target,
            payload=signal_data.get("payload", signal_data),
            metadata=signal_data.get("metadata", {}),
        )

        self._signal_history.append(signal)
        logger.debug(
            "Collected feedback signal %s from %s (severity=%s, target=%s)",
            signal.signal_id, source.value, severity.value, target.value,
        )
        return signal

    def route_feedback(self, signal: FeedbackSignal) -> list[FeedbackAction]:
        """Route a feedback signal through matching rules to generate actions.

        Rules are sorted by priority (lower number first). Each matching rule
        generates one action. Cooldown rules are respected.

        Args:
            signal: The feedback signal to route.

        Returns:
            List of generated FeedbackAction instances.
        """
        t_start = time.time()
        actions: list[FeedbackAction] = []
        sorted_rules = sorted(self._routing_rules, key=lambda r: r.priority)

        for rule in sorted_rules:
            if rule.matches(signal):
                action = FeedbackAction(
                    action_type=rule.action_type,
                    signal_id=signal.signal_id,
                    target=signal.target_module,
                    parameters={
                        "source": signal.source.value,
                        "severity": signal.severity.value,
                        "confidence": signal.confidence,
                        "payload": signal.payload,
                        "rule_id": rule.rule_id,
                    },
                    expected_impact=self._describe_impact(
                        rule.action_type, signal.target_module
                    ),
                )
                actions.append(action)
                self._action_history.append(action)
                rule.last_triggered = time.time()
                logger.debug(
                    "Routed signal %s via rule %s -> action %s (%s)",
                    signal.signal_id, rule.rule_id, action.action_id,
                    action.action_type.value,
                )

        elapsed_ms = (time.time() - t_start) * 1000
        self._routing_times.append(elapsed_ms)

        return actions

    def execute_actions(self, actions: list[FeedbackAction]) -> list[ActionResult]:
        """Execute a list of feedback actions and return results.

        Each action is executed sequentially. Results include success/failure
        status and impact scores.

        Args:
            actions: List of actions to execute.

        Returns:
            List of ActionResult instances.
        """
        results: list[ActionResult] = []
        for action in actions:
            t_start = time.time()
            action.status = ActionStatus.EXECUTING
            action.executed_at = datetime.now(timezone.utc).isoformat()

            try:
                result = self._execute_single_action(action)
                action.status = ActionStatus.COMPLETED
                action.completed_at = datetime.now(timezone.utc).isoformat()
            except Exception as exc:
                result = ActionResult(
                    action_id=action.action_id,
                    success=False,
                    impact_score=0.0,
                    details=f"Action failed: {exc}",
                )
                action.status = ActionStatus.FAILED
                action.error_message = str(exc)
                action.completed_at = datetime.now(timezone.utc).isoformat()
                logger.warning("Action %s failed: %s", action.action_id, exc)

            elapsed_ms = (time.time() - t_start) * 1000
            self._action_times.append(elapsed_ms)
            self._result_history.append(result)
            results.append(result)

        return results

    def _execute_single_action(self, action: FeedbackAction) -> ActionResult:
        """Execute a single action based on its type.

        Each action type maps to a specific handler that simulates
        the corresponding system change and returns an impact score.
        """
        confidence = action.parameters.get("confidence", 0.5)
        severity = action.parameters.get("severity", "medium")

        if action.action_type == ActionType.UPDATE_SKILL_PARAMETERS:
            return self._handle_update_skill_parameters(action, confidence)
        elif action.action_type == ActionType.ADJUST_MEMORY_WEIGHTS:
            return self._handle_adjust_memory_weights(action, confidence)
        elif action.action_type == ActionType.MODIFY_PERSONA_TRAITS:
            return self._handle_modify_persona_traits(action, confidence)
        elif action.action_type == ActionType.RECALIBRATE_MODEL_PREFERENCES:
            return self._handle_recalibrate_model_preferences(action, confidence)
        elif action.action_type == ActionType.EVOLVE_STRATEGY:
            return self._handle_evolve_strategy(action, confidence)
        elif action.action_type == ActionType.FLAG_FOR_REVIEW:
            return self._handle_flag_for_review(action, severity)
        elif action.action_type == ActionType.ADJUST_THRESHOLD:
            return self._handle_adjust_threshold(action, confidence)
        elif action.action_type == ActionType.REBALANCE_PRIORITIES:
            return self._handle_rebalance_priorities(action, confidence)
        else:
            return ActionResult(
                action_id=action.action_id,
                success=True,
                impact_score=0.1,
                details=f"Unknown action type: {action.action_type.value}",
            )

    def _handle_update_skill_parameters(
        self, action: FeedbackAction, confidence: float
    ) -> ActionResult:
        impact = confidence * 0.8
        params = action.parameters.get("payload", {})
        changed = {
            "skill_weight_adjustment": round(impact, 3),
            "affected_keys": list(params.keys())[:5],
        }
        logger.info("Updated skill parameters: impact=%.3f", impact)
        return ActionResult(
            action_id=action.action_id, success=True, impact_score=impact,
            details="Skill parameters updated based on execution feedback",
            changed_parameters=changed,
        )

    def _handle_adjust_memory_weights(
        self, action: FeedbackAction, confidence: float
    ) -> ActionResult:
        impact = confidence * 0.7
        changed = {
            "importance_boost": round(impact, 3),
            "consolidation_priority": "increased" if impact > 0.5 else "moderate",
        }
        logger.info("Adjusted memory weights: impact=%.3f", impact)
        return ActionResult(
            action_id=action.action_id, success=True, impact_score=impact,
            details="Memory importance weights adjusted based on implicit feedback",
            changed_parameters=changed,
        )

    def _handle_modify_persona_traits(
        self, action: FeedbackAction, confidence: float
    ) -> ActionResult:
        impact = confidence * 0.75
        changed = {
            "trait_modification": round(impact, 3),
            "adaptation_speed": "fast" if impact > 0.7 else "gradual",
        }
        logger.info("Modified persona traits: impact=%.3f", impact)
        return ActionResult(
            action_id=action.action_id, success=True, impact_score=impact,
            details="Persona traits modified based on explicit user feedback",
            changed_parameters=changed,
        )

    def _handle_recalibrate_model_preferences(
        self, action: FeedbackAction, confidence: float
    ) -> ActionResult:
        impact = confidence * 0.65
        changed = {
            "preference_shift": round(impact, 3),
            "recalibration_factor": round(1.0 + (impact - 0.5) * 0.2, 3),
        }
        logger.info("Recalibrated model preferences: impact=%.3f", impact)
        return ActionResult(
            action_id=action.action_id, success=True, impact_score=impact,
            details="Model preferences recalibrated based on self-reflection",
            changed_parameters=changed,
        )

    def _handle_evolve_strategy(
        self, action: FeedbackAction, confidence: float
    ) -> ActionResult:
        impact = confidence * 0.6
        changed = {
            "strategy_evolution": round(impact, 3),
            "new_approach_weight": round(impact, 3),
        }
        logger.info("Evolved strategy: impact=%.3f", impact)
        return ActionResult(
            action_id=action.action_id, success=True, impact_score=impact,
            details="Execution strategy evolved based on system feedback",
            changed_parameters=changed,
        )

    def _handle_flag_for_review(
        self, action: FeedbackAction, severity: str
    ) -> ActionResult:
        impact = 0.9 if severity == "critical" else 0.6
        logger.warning("Flagged signal %s for review (severity=%s)", action.signal_id, severity)
        return ActionResult(
            action_id=action.action_id, success=True, impact_score=impact,
            details=f"Flagged for human review due to {severity} severity",
            changed_parameters={"review_priority": severity},
        )

    def _handle_adjust_threshold(
        self, action: FeedbackAction, confidence: float
    ) -> ActionResult:
        impact = confidence * 0.5
        changed = {"threshold_delta": round((confidence - 0.5) * 0.2, 3)}
        logger.info("Adjusted threshold: impact=%.3f", impact)
        return ActionResult(
            action_id=action.action_id, success=True, impact_score=impact,
            details="Threshold adjusted based on high-severity feedback",
            changed_parameters=changed,
        )

    def _handle_rebalance_priorities(
        self, action: FeedbackAction, confidence: float
    ) -> ActionResult:
        impact = confidence * 0.55
        changed = {"priority_rebalance": round(impact, 3)}
        logger.info("Rebalanced priorities: impact=%.3f", impact)
        return ActionResult(
            action_id=action.action_id, success=True, impact_score=impact,
            details="Priorities rebalanced based on feedback patterns",
            changed_parameters=changed,
        )

    def get_analytics(self, window_hours: float = 24.0) -> FeedbackAnalytics:
        """Generate analytics for feedback signals within a time window.

        Analyzes trends, detects anomalies, computes improvement velocity,
        and assesses impact of past actions.

        Args:
            window_hours: Size of the analysis window in hours.

        Returns:
            A FeedbackAnalytics instance with computed metrics.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        cutoff_str = cutoff.isoformat()

        signals_in_window = [
            s for s in self._signal_history if s.timestamp >= cutoff_str
        ]

        analytics = FeedbackAnalytics(
            window_hours=window_hours,
            total_signals_in_window=len(signals_in_window),
        )

        if not signals_in_window:
            return analytics

        source_counts: dict[str, int] = defaultdict(int)
        severity_counts: dict[str, int] = defaultdict(int)
        confidence_sum = 0.0
        for s in signals_in_window:
            source_counts[s.source.value] += 1
            severity_counts[s.severity.value] += 1
            confidence_sum += s.confidence

        analytics.signals_by_source = dict(source_counts)
        analytics.signals_by_severity = dict(severity_counts)
        analytics.average_confidence = (
            confidence_sum / len(signals_in_window) if signals_in_window else 0.0
        )

        analytics.trends = self._detect_trends(signals_in_window, window_hours)
        analytics.anomalies = self._detect_anomalies(signals_in_window)
        analytics.velocity = self._compute_velocity(signals_in_window, window_hours)

        results_in_window = [
            r for r in self._result_history
            if r.timestamp >= cutoff_str
        ]
        analytics.impact_scores = [r.impact_score for r in results_in_window]

        logger.info(
            "Generated analytics: %d signals, %d trends, %d anomalies, velocity=%.3f",
            analytics.total_signals_in_window, len(analytics.trends),
            len(analytics.anomalies), analytics.velocity,
        )
        return analytics

    def _detect_trends(
        self, signals: list[FeedbackSignal], window_hours: float
    ) -> list[SignalTrend]:
        """Detect trends in signal metrics over the time window."""
        trends: list[SignalTrend] = []
        if len(signals) < 2:
            return trends

        sorted_signals = sorted(signals, key=lambda s: s.timestamp)

        confidences = [s.confidence for s in sorted_signals]
        confidence_trend = self._compute_trend(confidences, window_hours)
        trends.append(SignalTrend(
            metric_name="average_confidence",
            direction=confidence_trend[0],
            slope=confidence_trend[1],
            data_points=len(confidences),
            current_value=confidences[-1] if confidences else 0.0,
            window_start=sorted_signals[0].timestamp,
            window_end=sorted_signals[-1].timestamp,
        ))

        severity_scores = [
            float(list(FeedbackSeverity).index(s.severity)) for s in sorted_signals
        ]
        severity_trend = self._compute_trend(severity_scores, window_hours)
        trends.append(SignalTrend(
            metric_name="severity_level",
            direction=severity_trend[0],
            slope=severity_trend[1],
            data_points=len(severity_scores),
            current_value=severity_scores[-1] if severity_scores else 0.0,
            window_start=sorted_signals[0].timestamp,
            window_end=sorted_signals[-1].timestamp,
        ))

        return trends

    def _detect_anomalies(
        self, signals: list[FeedbackSignal]
    ) -> list[FeedbackAnomaly]:
        """Detect anomalies in signal confidence using standard deviation."""
        anomalies: list[FeedbackAnomaly] = []
        if len(signals) < 5:
            return anomalies

        confidences = [s.confidence for s in signals]
        mean_c = sum(confidences) / len(confidences)
        variance = sum((c - mean_c) ** 2 for c in confidences) / len(confidences)
        std_dev = math.sqrt(variance) if variance > 0 else 0.001

        for s in signals:
            deviation = abs(s.confidence - mean_c) / std_dev if std_dev > 0 else 0
            if deviation > 2.5:
                anomalies.append(FeedbackAnomaly(
                    description=f"Confidence {s.confidence:.2f} deviates "
                                f"{deviation:.1f}σ from mean {mean_c:.2f}",
                    metric_name="confidence",
                    expected_value=mean_c,
                    actual_value=s.confidence,
                    deviation_std=deviation,
                    severity=FeedbackSeverity.HIGH if deviation > 3.5 else FeedbackSeverity.MEDIUM,
                ))

        return anomalies

    def _compute_velocity(
        self, signals: list[FeedbackSignal], window_hours: float
    ) -> float:
        """Compute improvement velocity as signals processed per hour."""
        if window_hours <= 0 or len(signals) < 2:
            return 0.0

        sorted_signals = sorted(signals, key=lambda s: s.timestamp)
        first_ts = sorted_signals[0].timestamp
        last_ts = sorted_signals[-1].timestamp

        try:
            t0 = datetime.fromisoformat(first_ts)
            t1 = datetime.fromisoformat(last_ts)
            actual_hours = (t1 - t0).total_seconds() / 3600.0
        except (ValueError, TypeError):
            actual_hours = window_hours

        if actual_hours <= 0:
            return 0.0

        return len(signals) / actual_hours

    def _compute_trend(
        self, values: list[float], _window_hours: float
    ) -> tuple[str, float]:
        """Compute linear trend direction and slope for a series of values."""
        n = len(values)
        if n < 2:
            return ("stable", 0.0)

        mean_x = (n - 1) / 2.0
        mean_y = sum(values) / n

        numerator = sum((i - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((i - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            return ("stable", 0.0)

        slope = numerator / denominator
        threshold = 0.01
        if slope > threshold:
            direction = "increasing"
        elif slope < -threshold:
            direction = "decreasing"
        else:
            direction = "stable"

        return (direction, slope)

    def get_stats(self) -> FeedbackOrchestratorStats:
        """Get current runtime statistics for the orchestrator.

        Returns:
            A FeedbackOrchestratorStats with cumulative metrics.
        """
        routing_times = list(self._routing_times)
        action_times = list(self._action_times)
        total_actions = len(self._action_history)
        succeeded = sum(
            1 for a in self._action_history if a.status == ActionStatus.COMPLETED
        )
        failed = sum(
            1 for a in self._action_history if a.status == ActionStatus.FAILED
        )

        stats = FeedbackOrchestratorStats(
            total_signals=len(self._signal_history),
            routed_count=total_actions,
            actioned_count=total_actions,
            action_success_count=succeeded,
            action_failure_count=failed,
            average_routing_time_ms=(
                sum(routing_times) / len(routing_times) if routing_times else 0.0
            ),
            average_action_time_ms=(
                sum(action_times) / len(action_times) if action_times else 0.0
            ),
            registered_rules=len(self._routing_rules),
            pending_actions=len(self._pending_actions),
            uptime_seconds=time.time() - self._start_time,
        )

        logger.debug(
            "Stats: signals=%d, actions=%d, success=%d, failed=%d",
            stats.total_signals, stats.actioned_count,
            stats.action_success_count, stats.action_failure_count,
        )
        return stats

    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Register a new routing rule.

        Args:
            rule: The RoutingRule to add.
        """
        # Ensure enum fields are properly typed
        if isinstance(rule.rule_type, str):
            rule.rule_type = RoutingRuleType(rule.rule_type)
        if isinstance(rule.action_type, str):
            rule.action_type = ActionType(rule.action_type)
        self._routing_rules.append(rule)
        rule_type_val = rule.rule_type.value if isinstance(rule.rule_type, RoutingRuleType) else str(rule.rule_type)
        action_type_val = rule.action_type.value if isinstance(rule.action_type, ActionType) else str(rule.action_type)
        logger.info("Added routing rule %s (type=%s, action=%s, priority=%d)",
                     rule.rule_id, rule_type_val,
                     action_type_val, rule.priority)

    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule by ID.

        Args:
            rule_id: ID of the rule to remove.

        Returns:
            True if a rule was removed, False otherwise.
        """
        initial_count = len(self._routing_rules)
        self._routing_rules = [
            r for r in self._routing_rules if r.rule_id != rule_id
        ]
        removed = len(self._routing_rules) < initial_count
        if removed:
            logger.info("Removed routing rule %s", rule_id)
        return removed

    def reset(self) -> None:
        """Reset the orchestrator to initial state, clearing all history."""
        self._signal_history.clear()
        self._action_history.clear()
        self._result_history.clear()
        self._pending_actions.clear()
        self._routing_times.clear()
        self._action_times.clear()
        self._routing_rules.clear()
        self._start_time = time.time()
        self._load_default_rules()
        logger.info("Feedback orchestrator reset to initial state")

    @staticmethod
    def _describe_impact(action_type: ActionType, target: TargetModule) -> str:
        """Generate a human-readable description of expected impact."""
        descriptions = {
            ActionType.UPDATE_SKILL_PARAMETERS: (
                f"Adjust {target.value} parameters to improve execution quality"
            ),
            ActionType.ADJUST_MEMORY_WEIGHTS: (
                f"Modify memory importance weights for {target.value} retention"
            ),
            ActionType.MODIFY_PERSONA_TRAITS: (
                f"Adapt persona traits to better align with user preferences"
            ),
            ActionType.RECALIBRATE_MODEL_PREFERENCES: (
                f"Recalibrate model selection preferences for {target.value}"
            ),
            ActionType.EVOLVE_STRATEGY: (
                f"Evolve execution strategy for {target.value} operations"
            ),
            ActionType.FLAG_FOR_REVIEW: (
                f"Flag {target.value} signal for human review"
            ),
            ActionType.ADJUST_THRESHOLD: (
                f"Adjust sensitivity thresholds for {target.value} detection"
            ),
            ActionType.REBALANCE_PRIORITIES: (
                f"Rebalance routing priorities for {target.value} feedback"
            ),
        }
        return descriptions.get(action_type, f"Apply {action_type.value} to {target.value}")


feedback_orchestrator = FeedbackOrchestrator()