from __future__ import annotations

# Agent Cognitive Phase Transition — detection, prediction, and management of
# phase transitions in understanding, moments where knowledge reorganizes into
# qualitatively new states.
#
# In complex systems, a phase transition is a reorganization from one stable
# configuration into another, often passing through a critical regime where
# fluctuations grow and the system becomes exquisitely sensitive to small
# perturbations. Cognition exhibits analogous dynamics: a learner (or agent)
# may sit in a stable but limited understanding, enter a fluctuating regime
# where contradictions and evidence destabilize that understanding, reach a
# critical point where small catalysts produce large reorganizations, and
# finally settle into a qualitatively new stable state. This module captures
# that process operationally.
#
# The engine models each ongoing learning episode as a TransitionContext tied
# to an agent and a domain. Order parameters (coherence, integration,
# complexity, certainty, fluency, diversity) are measured repeatedly over
# time; their variance and autocorrelation are used to detect critical
# points where the system is approaching a transition. Transition catalysts
# (insights, contradictions, analogies, evidence, reflection, external
# input) are the perturbations that can trigger a transition. When a
# catalyst fires at a critical point, a PhaseTransitionEvent is created and
# moves through a lifecycle (DETECTED -> PREDICTED -> TRIGGERED ->
# FACILITATED -> STABILIZED or ABORTED), recording the from/to phase, the
# interventions applied, and the pre/post state snapshots.
#
# Capabilities: context registration, parameter measurement, critical-point
# detection via variance analysis, catalyst registration, transition
# triggering, intervention facilitation, phase stabilization, and aggregate
# statistics.
#
# Architecture:
#     AgentCognitivePhaseTransition (singleton)
#     ├── TransitionContext (a learning episode for one agent in a domain)
#     │   ├── OrderParameter (a measured value of one cognitive parameter)
#     │   ├── CriticalPoint (a detected critical regime in parameter space)
#     │   ├── TransitionCatalyst (a perturbation that can trigger a transition)
#     │   └── PhaseTransitionEvent (a transition moving through its lifecycle)
#     └── TransitionStats (aggregate engine statistics)

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class TransitionPhase(str, Enum):
    """The phase a cognitive system occupies during a transition cycle.

    A transition cycle moves through qualitatively different regimes.
    STABLE is the resting state: knowledge is coherent and small
    perturbations die out. FLUCTUATING means order parameters are wobbling
    and the system is losing stability. CRITICAL is the regime just before
    a transition where fluctuations are large and the system is sensitive
    to perturbations. TRANSITIONING is the active reorganization itself.
    REORGANIZING is the immediate aftermath where the new structure is
    forming but not yet stable. NEW_STABLE is the settled new state with a
    qualitatively different organization than the original.
    """
    STABLE = "stable"                  # coherent resting state
    FLUCTUATING = "fluctuating"        # order parameters wobbling
    CRITICAL = "critical"              # large fluctuations, high sensitivity
    TRANSITIONING = "transitioning"    # active reorganization
    REORGANIZING = "reorganizing"      # new structure forming, not yet stable
    NEW_STABLE = "new_stable"          # settled qualitatively new state


class ParameterType(str, Enum):
    """The kinds of order parameters measured to detect criticality.

    Order parameters are the macroscopic quantities whose behavior reveals
    the underlying phase of the system. COHERENCE measures how internally
    consistent the knowledge structure is. INTEGRATION measures how well
    separate pieces of knowledge are connected. COMPLEXITY measures the
    richness and depth of the structure. CERTAINTY measures the confidence
    with which the structure is held. FLUENCY measures how readily the
    knowledge can be deployed. DIVERSITY measures the breadth of distinct
    concepts and perspectives represented.
    """
    COHERENCE = "coherence"      # internal consistency of the structure
    INTEGRATION = "integration"  # connectedness of separate pieces
    COMPLEXITY = "complexity"    # richness and depth of the structure
    CERTAINTY = "certainty"      # confidence in the structure
    FLUENCY = "fluency"          # readiness to deploy the knowledge
    DIVERSITY = "diversity"      # breadth of concepts and perspectives


class CatalystType(str, Enum):
    """The kinds of perturbations that can trigger a phase transition.

    A catalyst is the small input that, at a critical point, produces a
    large reorganization. INSIGHT is a sudden realization that reorganizes
    understanding. CONTRADICTION is a conflict with the current structure
    that forces reorganization. ANALOGY is a mapping from another domain
    that reveals new structure. EVIDENCE is new data that supports or
    undermines the current structure. REFLECTION is introspective
    reconsideration of the structure. EXTERNAL is input from outside the
    agent (an instructor, a peer, a text) that perturbs the structure.
    """
    INSIGHT = "insight"            # a sudden realization
    CONTRADICTION = "contradiction"  # a conflict with current structure
    ANALOGY = "analogy"            # a mapping from another domain
    EVIDENCE = "evidence"          # new data supporting or undermining
    REFLECTION = "reflection"      # introspective reconsideration
    EXTERNAL = "external"          # input from outside the agent


class TransitionStatus(str, Enum):
    """Lifecycle states of a PhaseTransitionEvent.

    DETECTED means a critical point has been identified and a transition
    is anticipated. PREDICTED means the engine forecasts a transition is
    likely imminent based on parameter trends. TRIGGERED means a catalyst
    has fired and the transition is underway. FACILITATED means
    interventions have been applied to support the reorganization.
    STABILIZED is the terminal success state: the system has settled into
    a new stable phase. ABORTED is the terminal failure state: the
    transition did not complete and the system reverted or stalled.
    """
    DETECTED = "detected"        # critical point identified
    PREDICTED = "predicted"      # transition forecast as imminent
    TRIGGERED = "triggered"      # catalyst fired, transition underway
    FACILITATED = "facilitated"  # interventions applied
    STABILIZED = "stabilized"    # settled into a new stable phase
    ABORTED = "aborted"          # transition did not complete


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a context/parameter/event/etc."""
    return str(uuid.uuid4())[:8]


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"coherence"``) and then against member names
    (e.g. ``"COHERENCE"``), so callers may pass either form. Raises
    ``ValueError`` if neither matches.
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            pass
        try:
            return enum_cls[value]
        except KeyError:
            pass
    raise ValueError(f"{value!r} is not a valid {enum_cls.__name__}")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _enum_value(enum_cls: type, value: Any) -> str:
    """Return the ``.value`` of an enum member, or a string fallback.

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _variance(values: List[float]) -> float:
    """Compute the population variance of a list of numeric values.

    Returns 0.0 for empty or single-element lists, since there is no
    spread to measure.
    """
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


def _lag1_autocorrelation(values: List[float]) -> float:
    """Compute the lag-1 autocorrelation of a list of numeric values.

    Lag-1 autocorrelation measures how strongly each value predicts the
    next. Values near 1 indicate a smoothly trending series; values near 0
    indicate rapid, uncorrelated fluctuation; negative values indicate
    oscillation. Returns 0.0 for series shorter than two elements. The
    result is clamped to [-1, 1] to guard against floating-point drift.
    """
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    num = 0.0
    for i in range(n - 1):
        num += (values[i] - mean) * (values[i + 1] - mean)
    den = sum((v - mean) ** 2 for v in values)
    if den == 0.0:
        return 0.0
    r = num / den
    if r > 1.0:
        r = 1.0
    elif r < -1.0:
        r = -1.0
    return r


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class OrderParameter:
    """A single measurement of one cognitive order parameter.

    An order parameter is a macroscopic quantity whose behavior reveals the
    underlying phase of the system. Each measurement pairs a
    ``parameter_type`` (COHERENCE, INTEGRATION, etc.) with a numeric
    ``value`` (typically in [0, 1]) and the ``timestamp`` at which the
    measurement was taken. Measurements are append-only: each new reading
    creates a new record so the parameter's history is preserved for
    variance and autocorrelation analysis.
    """
    parameter_id: str = field(default_factory=_new_id)
    context_id: str = ""
    parameter_type: ParameterType = ParameterType.COHERENCE
    value: float = 0.5
    timestamp: str = field(default_factory=_now)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this measurement to a plain dict, expanding the enum."""
        return {
            "parameter_id": self.parameter_id,
            "context_id": self.context_id,
            "parameter_type": _enum_value(ParameterType, self.parameter_type),
            "value": self.value,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
        }


@dataclass
class CriticalPoint:
    """A detected critical regime in a context's parameter space.

    A critical point is a window in which order parameters exhibit large
    variance and the system is sensitive to perturbations, signaling that
    a phase transition is approaching. ``detected_phase`` is the phase the
    engine believes the system is in (typically FLUCTUATING or CRITICAL).
    ``parameters`` holds the recent measurements the detection was based
    on. ``variance`` is the maximum variance observed across parameter
    types, ``autocorrelation`` is the corresponding lag-1 autocorrelation,
    and ``confidence`` is a value in [0, 1] expressing how strongly the
    engine believes a transition is imminent.
    """
    point_id: str = field(default_factory=_new_id)
    context_id: str = ""
    detected_phase: TransitionPhase = TransitionPhase.CRITICAL
    parameters: List[OrderParameter] = field(default_factory=list)
    variance: float = 0.0
    autocorrelation: float = 0.0
    confidence: float = 0.0
    detected_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this critical point to a plain dict.

        The ``detected_phase`` enum is expanded via ``.value``; the nested
        ``parameters`` list is serialized element-wise via each
        ``OrderParameter``'s ``to_dict``.
        """
        return {
            "point_id": self.point_id,
            "context_id": self.context_id,
            "detected_phase": _enum_value(TransitionPhase, self.detected_phase),
            "parameters": [p.to_dict() for p in self.parameters],
            "variance": self.variance,
            "autocorrelation": self.autocorrelation,
            "confidence": self.confidence,
            "detected_at": self.detected_at,
        }


@dataclass
class TransitionCatalyst:
    """A perturbation that can trigger a phase transition.

    A catalyst is the small input that, at a critical point, produces a
    large reorganization. Each catalyst has a ``catalyst_type``
    (INSIGHT, CONTRADICTION, etc.), a free-form ``description`` of what
    the perturbation is, and a ``strength`` in [0, 1] expressing how
    forceful the perturbation is. ``applied`` records whether the catalyst
    has been used to trigger a transition; a catalyst can be applied at
    most once.
    """
    catalyst_id: str = field(default_factory=_new_id)
    context_id: str = ""
    catalyst_type: CatalystType = CatalystType.INSIGHT
    description: str = ""
    strength: float = 0.5
    applied: bool = False
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this catalyst to a plain dict, expanding the enum."""
        return {
            "catalyst_id": self.catalyst_id,
            "context_id": self.context_id,
            "catalyst_type": _enum_value(CatalystType, self.catalyst_type),
            "description": self.description,
            "strength": self.strength,
            "applied": self.applied,
            "created_at": self.created_at,
        }


@dataclass
class PhaseTransitionEvent:
    """A transition moving through its lifecycle.

    A transition event is created when a catalyst fires, recording the
    ``from_phase`` the system is leaving, the ``to_phase`` it is moving
    toward, and a free-form ``description``. The ``status`` field tracks
    the lifecycle from TRIGGERED through FACILITATED to a terminal
    STABILIZED or ABORTED. ``interventions`` is an append-only list of
    free-form intervention descriptions applied to support the
    reorganization. ``pre_state`` and ``post_state`` are free-form dicts
    capturing snapshots of the system before and after the transition;
    ``pre_state`` is populated at creation and ``post_state`` at
    stabilization. ``completed_at`` records when the event reached a
    terminal state.
    """
    event_id: str = field(default_factory=_new_id)
    context_id: str = ""
    catalyst_id: str = ""
    from_phase: TransitionPhase = TransitionPhase.STABLE
    to_phase: TransitionPhase = TransitionPhase.NEW_STABLE
    description: str = ""
    status: TransitionStatus = TransitionStatus.TRIGGERED
    interventions: List[str] = field(default_factory=list)
    pre_state: Dict[str, Any] = field(default_factory=dict)
    post_state: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict.

        The ``from_phase``, ``to_phase``, and ``status`` enums are
        expanded via ``.value``; the ``interventions`` list is copied and
        the ``pre_state``/``post_state`` dicts are deep-copied so the
        serialized form is independent of the live event.
        """
        return {
            "event_id": self.event_id,
            "context_id": self.context_id,
            "catalyst_id": self.catalyst_id,
            "from_phase": _enum_value(TransitionPhase, self.from_phase),
            "to_phase": _enum_value(TransitionPhase, self.to_phase),
            "description": self.description,
            "status": _enum_value(TransitionStatus, self.status),
            "interventions": list(self.interventions),
            "pre_state": dict(self.pre_state) if isinstance(self.pre_state, dict) else self.pre_state,
            "post_state": dict(self.post_state) if isinstance(self.post_state, dict) else self.post_state,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class TransitionContext:
    """A learning episode for one agent in a domain.

    A context ties an ``agent_id`` to a ``domain`` and an optional
    ``description`` of what the agent is learning or working through. The
    context holds references (by id) to its parameter history, catalysts,
    and transition events, so the full record can be reconstructed without
    duplicating state. ``current_phase`` tracks the phase the engine
    believes the context is currently in; it is updated as critical points
    are detected and transitions fire.
    """
    context_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    domain: str = ""
    description: str = ""
    parameter_history: List[str] = field(default_factory=list)
    catalyst_ids: List[str] = field(default_factory=list)
    event_ids: List[str] = field(default_factory=list)
    current_phase: TransitionPhase = TransitionPhase.STABLE
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this context to a plain dict, expanding the enum."""
        return {
            "context_id": self.context_id,
            "agent_id": self.agent_id,
            "domain": self.domain,
            "description": self.description,
            "parameter_history": list(self.parameter_history),
            "catalyst_ids": list(self.catalyst_ids),
            "event_ids": list(self.event_ids),
            "current_phase": _enum_value(TransitionPhase, self.current_phase),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class TransitionStats:
    """Aggregate statistics over the phase-transition engine's state.

    Counts of contexts, parameters, critical points, catalysts, and
    events; plus two breakdown dicts (``events_by_status`` and
    ``events_by_phase``) that tally events by their status and by the
    ``to_phase`` they targeted. Breakdown keys are the enum ``.value``
    strings so the stats serialize cleanly to JSON.
    """
    total_contexts: int = 0
    total_parameters: int = 0
    total_critical_points: int = 0
    total_catalysts: int = 0
    total_events: int = 0
    events_by_status: Dict[str, int] = field(default_factory=dict)
    events_by_phase: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict."""
        return {
            "total_contexts": self.total_contexts,
            "total_parameters": self.total_parameters,
            "total_critical_points": self.total_critical_points,
            "total_catalysts": self.total_catalysts,
            "total_events": self.total_events,
            "events_by_status": dict(self.events_by_status),
            "events_by_phase": dict(self.events_by_phase),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitivePhaseTransition:
    """Phase-transition engine with context, parameter, and event state.

    The engine maintains registries of transition contexts, order
    parameters, critical points, catalysts, and transition events. Each
    context tracks its current phase, and the engine analyzes parameter
    variance to detect critical points where a transition is approaching.
    Catalysts can then trigger transitions, which move through a lifecycle
    from TRIGGERED through FACILITATED to a terminal STABILIZED or
    ABORTED. All state mutations are guarded by a single lock so the
    engine is safe to call from multiple threads.

    The engine is intended to support both human learners and the agent
    itself: an agent working through a difficult domain can register a
    context, record its order parameters as it learns, and let the engine
    flag when its understanding is approaching a reorganization.
    """

    # Capacity limits to bound memory use per engine instance.
    MAX_CONTEXTS: int = 10000
    MAX_PARAMETERS_PER_CONTEXT: int = 5000
    MAX_CATALYSTS_PER_CONTEXT: int = 500
    MAX_EVENTS_PER_CONTEXT: int = 500
    # Detection thresholds.
    MIN_PARAMETERS_FOR_DETECTION: int = 3
    VARIANCE_CRITICAL_THRESHOLD: float = 0.05
    VARIANCE_FLUCTUATING_THRESHOLD: float = 0.02
    RECENT_WINDOW: int = 20

    def __init__(self) -> None:
        self._contexts: Dict[str, TransitionContext] = {}
        self._parameters: Dict[str, OrderParameter] = {}
        self._critical_points: Dict[str, CriticalPoint] = {}
        self._catalysts: Dict[str, TransitionCatalyst] = {}
        self._events: Dict[str, PhaseTransitionEvent] = {}
        # Index from context_id to the list of critical point ids for it.
        self._context_critical_points: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Context Management ─────────────────────────────────────────

    def register_context(
        self,
        agent_id: str,
        domain: str,
        description: str = "",
    ) -> TransitionContext:
        """Register a new transition context and return it.

        ``agent_id`` identifies the agent (or learner) the context belongs
        to. ``domain`` is the subject area (e.g. "math", "python"). An
        optional ``description`` may give free-form detail about what the
        agent is working through. The new context starts in the STABLE
        phase. Raises ``RuntimeError`` if the context registry is full.
        """
        with self._lock:
            if len(self._contexts) >= self.MAX_CONTEXTS:
                raise RuntimeError("context registry is full")
            context = TransitionContext(
                agent_id=agent_id,
                domain=domain,
                description=description,
            )
            self._contexts[context.context_id] = context
            self._context_critical_points[context.context_id] = []
            return context

    def get_context(self, context_id: str) -> Optional[TransitionContext]:
        """Retrieve a context by id, or ``None`` if absent."""
        with self._lock:
            return self._contexts.get(context_id)

    def list_contexts(self, agent_id: Optional[str] = None) -> list:
        """Return contexts, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all contexts are returned. Otherwise
        only contexts belonging to that agent are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            contexts = list(self._contexts.values())
        if agent_id is None:
            return contexts
        return [c for c in contexts if c.agent_id == agent_id]

    # ── Parameter Measurement ──────────────────────────────────────

    def record_parameter(
        self,
        context_id: str,
        parameter_type: Any,
        value: float,
        timestamp: Optional[str] = None,
    ) -> OrderParameter:
        """Record a measurement of one order parameter for a context.

        ``parameter_type`` may be passed as a ``ParameterType`` or its
        string name/value (e.g. ``"COHERENCE"`` or ``"coherence"``).
        ``value`` is clamped to [0, 1]. ``timestamp`` defaults to the
        current UTC time; it is the time the measurement refers to, which
        may differ from the time it was recorded. The new parameter id is
        appended to the context's parameter history. Raises ``KeyError``
        if the context_id is not registered, or ``RuntimeError`` if the
        context's parameter history is full.
        """
        ptype = _resolve_enum(ParameterType, parameter_type)
        val = _clamp(value)
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise KeyError(f"context not found: {context_id}")
            if len(context.parameter_history) >= self.MAX_PARAMETERS_PER_CONTEXT:
                raise RuntimeError("parameter history is full for context")
            ts = timestamp if timestamp is not None else _now()
            param = OrderParameter(
                context_id=context_id,
                parameter_type=ptype,
                value=val,
                timestamp=ts,
            )
            self._parameters[param.parameter_id] = param
            context.parameter_history.append(param.parameter_id)
            context.updated_at = _now()
            return param

    def get_parameter_history(
        self,
        context_id: str,
        parameter_type: Optional[Any] = None,
    ) -> list:
        """Return parameter history for a context, optionally filtered.

        When ``parameter_type`` is ``None`` all parameters for the context
        are returned in insertion order. Otherwise only parameters of the
        given type are returned. ``parameter_type`` may be passed as a
        ``ParameterType`` or its string name/value. Returns an empty list
        if the context is absent or has no parameters.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return []
            params: List[OrderParameter] = [
                self._parameters[pid]
                for pid in context.parameter_history
                if pid in self._parameters
            ]
        if parameter_type is None:
            return params
        ptype = _resolve_enum(ParameterType, parameter_type)
        return [p for p in params if p.parameter_type == ptype]

    # ── Critical Point Detection ───────────────────────────────────

    def detect_critical_point(self, context_id: str) -> Optional[CriticalPoint]:
        """Analyze parameter variance to detect a critical point.

        The method gathers the most recent measurements of each parameter
        type for the context, computes the variance and lag-1
        autocorrelation of each type's recent series, and takes the
        maximum variance across types as the signal of criticality. High
        variance indicates the system is fluctuating and approaching a
        phase transition; the detected phase is set accordingly (CRITICAL
        for variance above the critical threshold, FLUCTUATING for
        variance above the fluctuating threshold, STABLE otherwise).

        Confidence is a function of both the variance magnitude and the
        amount of data available, scaled into [0, 1]. The detected
        critical point is stored against the context and the context's
        ``current_phase`` is updated to the detected phase. Returns
        ``None`` if there is insufficient data (fewer than
        ``MIN_PARAMETERS_FOR_DETECTION`` measurements, or no parameter
        type with at least two recent values).
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return None
            # Collect the most recent measurements per parameter type.
            recent_by_type: Dict[ParameterType, List[OrderParameter]] = {}
            for pid in context.parameter_history:
                param = self._parameters.get(pid)
                if param is None:
                    continue
                recent_by_type.setdefault(param.parameter_type, []).append(param)
            if not recent_by_type:
                return None
            total_recent = sum(len(v) for v in recent_by_type.values())
            if total_recent < self.MIN_PARAMETERS_FOR_DETECTION:
                return None
            # Trim each series to the recent window and compute stats.
            max_variance = 0.0
            autocorr_at_max = 0.0
            contributing: List[OrderParameter] = []
            for ptype, series in recent_by_type.items():
                window = series[-self.RECENT_WINDOW:]
                if len(window) < 2:
                    continue
                values = [p.value for p in window]
                var = _variance(values)
                if var >= max_variance:
                    max_variance = var
                    autocorr_at_max = _lag1_autocorrelation(values)
                    contributing = list(window)
            if not contributing:
                return None
            # Determine the detected phase from the variance magnitude.
            if max_variance >= self.VARIANCE_CRITICAL_THRESHOLD:
                detected_phase = TransitionPhase.CRITICAL
            elif max_variance >= self.VARIANCE_FLUCTUATING_THRESHOLD:
                detected_phase = TransitionPhase.FLUCTUATING
            else:
                detected_phase = TransitionPhase.STABLE
            # Confidence grows with both variance magnitude and data volume.
            data_factor = min(1.0, len(contributing) / float(self.RECENT_WINDOW))
            variance_factor = min(1.0, max_variance / self.VARIANCE_CRITICAL_THRESHOLD)
            confidence = _clamp(0.5 * variance_factor + 0.5 * data_factor)
            point = CriticalPoint(
                context_id=context_id,
                detected_phase=detected_phase,
                parameters=contributing,
                variance=max_variance,
                autocorrelation=autocorr_at_max,
                confidence=confidence,
            )
            self._critical_points[point.point_id] = point
            self._context_critical_points.setdefault(context_id, []).append(point.point_id)
            context.current_phase = detected_phase
            context.updated_at = _now()
            return point

    def get_critical_point(self, point_id: str) -> Optional[CriticalPoint]:
        """Retrieve a critical point by id, or ``None`` if absent."""
        with self._lock:
            return self._critical_points.get(point_id)

    def list_critical_points(self, context_id: str) -> list:
        """Return all critical points detected for a context.

        The points are returned in detection order. Returns an empty list
        if the context is absent or has no detected critical points.
        """
        with self._lock:
            ids = self._context_critical_points.get(context_id, [])
            return [self._critical_points[i] for i in ids if i in self._critical_points]

    # ── Catalyst Management ────────────────────────────────────────

    def register_catalyst(
        self,
        context_id: str,
        catalyst_type: Any,
        description: str,
        strength: float = 0.5,
    ) -> TransitionCatalyst:
        """Register a new transition catalyst for a context.

        ``catalyst_type`` may be passed as a ``CatalystType`` or its
        string name/value. ``description`` is a free-form explanation of
        the perturbation. ``strength`` is clamped to [0, 1] and expresses
        how forceful the perturbation is. The new catalyst id is appended
        to the context's catalyst list. A catalyst is created with
        ``applied=False``; it is marked applied when used to trigger a
        transition. Raises ``KeyError`` if the context_id is not
        registered, or ``RuntimeError`` if the context's catalyst list is
        full.
        """
        ctype = _resolve_enum(CatalystType, catalyst_type)
        str_val = _clamp(strength)
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise KeyError(f"context not found: {context_id}")
            if len(context.catalyst_ids) >= self.MAX_CATALYSTS_PER_CONTEXT:
                raise RuntimeError("catalyst list is full for context")
            catalyst = TransitionCatalyst(
                context_id=context_id,
                catalyst_type=ctype,
                description=description,
                strength=str_val,
            )
            self._catalysts[catalyst.catalyst_id] = catalyst
            context.catalyst_ids.append(catalyst.catalyst_id)
            context.updated_at = _now()
            return catalyst

    def get_catalyst(self, catalyst_id: str) -> Optional[TransitionCatalyst]:
        """Retrieve a catalyst by id, or ``None`` if absent."""
        with self._lock:
            return self._catalysts.get(catalyst_id)

    def list_catalysts(
        self,
        context_id: str,
        catalyst_type: Optional[Any] = None,
    ) -> list:
        """Return catalysts for a context, optionally filtered by type.

        When ``catalyst_type`` is ``None`` all catalysts for the context
        are returned in registration order. Otherwise only catalysts of
        the given type are returned. ``catalyst_type`` may be passed as a
        ``CatalystType`` or its string name/value. Returns an empty list
        if the context is absent or has no catalysts.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return []
            catalysts: List[TransitionCatalyst] = [
                self._catalysts[cid]
                for cid in context.catalyst_ids
                if cid in self._catalysts
            ]
        if catalyst_type is None:
            return catalysts
        ctype = _resolve_enum(CatalystType, catalyst_type)
        return [c for c in catalysts if c.catalyst_type == ctype]

    # ── Transition Events ──────────────────────────────────────────

    def trigger_transition(
        self,
        context_id: str,
        catalyst_id: str,
        description: str = "",
    ) -> PhaseTransitionEvent:
        """Trigger a transition by firing a catalyst against a context.

        The catalyst is marked applied, and a new PhaseTransitionEvent is
        created with status TRIGGERED. The ``from_phase`` is the context's
        current phase; the ``to_phase`` is REORGANIZING, since firing a
        catalyst initiates the active reorganization. A ``pre_state``
        snapshot is recorded capturing the context's phase and the
        catalyst's strength at trigger time. The new event id is appended
        to the context's event list and the context's current phase is
        advanced to TRANSITIONING. Raises ``KeyError`` if the context or
        catalyst is not registered, or if the catalyst does not belong to
        the given context. Raises ``RuntimeError`` if the catalyst has
        already been applied or the context's event list is full.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise KeyError(f"context not found: {context_id}")
            catalyst = self._catalysts.get(catalyst_id)
            if catalyst is None:
                raise KeyError(f"catalyst not found: {catalyst_id}")
            if catalyst.context_id != context_id:
                raise KeyError(f"catalyst {catalyst_id} does not belong to context {context_id}")
            if catalyst.applied:
                raise RuntimeError(f"catalyst {catalyst_id} already applied")
            if len(context.event_ids) >= self.MAX_EVENTS_PER_CONTEXT:
                raise RuntimeError("event list is full for context")
            from_phase = context.current_phase
            to_phase = TransitionPhase.REORGANIZING
            pre_state: Dict[str, Any] = {
                "from_phase": _enum_value(TransitionPhase, from_phase),
                "catalyst_type": _enum_value(CatalystType, catalyst.catalyst_type),
                "catalyst_strength": catalyst.strength,
                "captured_at": _now(),
            }
            event = PhaseTransitionEvent(
                context_id=context_id,
                catalyst_id=catalyst_id,
                from_phase=from_phase,
                to_phase=to_phase,
                description=description,
                status=TransitionStatus.TRIGGERED,
                pre_state=pre_state,
            )
            self._events[event.event_id] = event
            context.event_ids.append(event.event_id)
            catalyst.applied = True
            context.current_phase = TransitionPhase.TRANSITIONING
            context.updated_at = _now()
            return event

    def get_event(self, event_id: str) -> Optional[PhaseTransitionEvent]:
        """Retrieve a transition event by id, or ``None`` if absent."""
        with self._lock:
            return self._events.get(event_id)

    def list_events(
        self,
        context_id: Optional[str] = None,
        status: Optional[Any] = None,
    ) -> list:
        """Return transition events, optionally filtered.

        When ``context_id`` is ``None`` all events are returned; otherwise
        only events for that context are returned. When ``status`` is
        ``None`` events of any status are returned; otherwise only events
        matching that status are returned. ``status`` may be passed as a
        ``TransitionStatus`` or its string name/value. Filters combine
        with AND. The returned list is a snapshot copy.
        """
        with self._lock:
            if context_id is None:
                events = list(self._events.values())
            else:
                context = self._contexts.get(context_id)
                if context is None:
                    return []
                events = [
                    self._events[eid]
                    for eid in context.event_ids
                    if eid in self._events
                ]
        if status is None:
            return events
        s = _resolve_enum(TransitionStatus, status)
        return [e for e in events if e.status == s]

    def facilitate_transition(
        self,
        event_id: str,
        interventions: Optional[List[str]] = None,
    ) -> PhaseTransitionEvent:
        """Apply interventions to support an in-progress transition.

        ``interventions`` is an optional list of free-form intervention
        descriptions (e.g. "provide worked example", "surface the
        contradiction explicitly"). Each is appended to the event's
        intervention history. The event's status is advanced to
        FACILITATED if it was TRIGGERED (or left unchanged if already
        FACILITATED). Events in a terminal state (STABILIZED or ABORTED)
        cannot be facilitated and raise ``RuntimeError``. Raises
        ``KeyError`` if the event_id is not registered.
        """
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                raise KeyError(f"event not found: {event_id}")
            if event.status in (TransitionStatus.STABILIZED, TransitionStatus.ABORTED):
                raise RuntimeError(f"event {event_id} is in terminal state {event.status.value}")
            if interventions:
                for iv in interventions:
                    event.interventions.append(str(iv))
            if event.status == TransitionStatus.TRIGGERED:
                event.status = TransitionStatus.FACILITATED
            context = self._contexts.get(event.context_id)
            if context is not None:
                context.updated_at = _now()
            return event

    def stabilize_phase(
        self,
        event_id: str,
        description: str = "",
    ) -> PhaseTransitionEvent:
        """Mark a transition as stabilized in a new stable phase.

        The event's status is set to STABILIZED, its ``to_phase`` is set
        to NEW_STABLE, its ``completed_at`` is recorded, and a
        ``post_state`` snapshot is taken capturing the final phase and the
        number of interventions applied. The owning context's
        ``current_phase`` is advanced to NEW_STABLE. If ``description`` is
        provided it is appended to the event's description to record the
        stabilization note. Events already in a terminal state raise
        ``RuntimeError``. Raises ``KeyError`` if the event_id is not
        registered.
        """
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                raise KeyError(f"event not found: {event_id}")
            if event.status in (TransitionStatus.STABILIZED, TransitionStatus.ABORTED):
                raise RuntimeError(f"event {event_id} is already in terminal state {event.status.value}")
            event.status = TransitionStatus.STABILIZED
            event.to_phase = TransitionPhase.NEW_STABLE
            event.completed_at = _now()
            post_state: Dict[str, Any] = {
                "to_phase": _enum_value(TransitionPhase, event.to_phase),
                "intervention_count": len(event.interventions),
                "captured_at": event.completed_at,
            }
            event.post_state = post_state
            if description:
                if event.description:
                    event.description = f"{event.description} | {description}"
                else:
                    event.description = description
            context = self._contexts.get(event.context_id)
            if context is not None:
                context.current_phase = TransitionPhase.NEW_STABLE
                context.updated_at = _now()
            return event

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> TransitionStats:
        """Compute aggregate statistics over the current engine state.

        Counts contexts, parameters, critical points, catalysts, and
        events; tallies events by status and by the ``to_phase`` they
        targeted. The breakdown dicts are keyed by the enum ``.value``
        strings so the stats serialize cleanly to JSON.
        """
        with self._lock:
            total_contexts = len(self._contexts)
            total_parameters = len(self._parameters)
            total_critical_points = len(self._critical_points)
            total_catalysts = len(self._catalysts)
            total_events = len(self._events)
            by_status: Dict[str, int] = {}
            by_phase: Dict[str, int] = {}
            for event in self._events.values():
                status_key = event.status.value
                phase_key = event.to_phase.value
                by_status[status_key] = by_status.get(status_key, 0) + 1
                by_phase[phase_key] = by_phase.get(phase_key, 0) + 1
            return TransitionStats(
                total_contexts=total_contexts,
                total_parameters=total_parameters,
                total_critical_points=total_critical_points,
                total_catalysts=total_catalysts,
                total_events=total_events,
                events_by_status=by_status,
                events_by_phase=by_phase,
            )

    # ── Maintenance ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests."""
        with self._lock:
            self._contexts.clear()
            self._parameters.clear()
            self._critical_points.clear()
            self._catalysts.clear()
            self._events.clear()
            self._context_critical_points.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_phase_transition_engine() -> AgentCognitivePhaseTransition:
    """Get or create the singleton ``AgentCognitivePhaseTransition`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitivePhaseTransition()
        return _engine


def reset_phase_transition_engine() -> None:
    """Reset the singleton ``AgentCognitivePhaseTransition`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_phase_transition_engine`` call creates
    a fresh instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
