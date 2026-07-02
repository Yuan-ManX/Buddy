"""Agent Cognitive Gradient Engine — directional slope of cognitive intensity across the mental field

The gradient is the vector of steepest ascent across the cognitive field: how
sharply attention, arousal, salience, valence, certainty, and urgency change
from region to region. It complements diffusion and momentum by measuring slope.

Core capabilities:
  - Regime: FLAT (uniform, unfocused) through STEEP to VERTICAL (tunnel vision)
  - Sources: INTEREST, THREAT, NOVELTY, GOAL, SOCIAL, INTERNAL
  - Leveling: FLATTEN, DAMPEN, CHANNEL, REDIRECT, AMPLIFY, INVERT
  - Stages: UNIFORM -> RISING -> PEAKING -> DESCENDING -> LEVELING -> SETTLED

Architecture:
  AgentCognitiveGradient (singleton)
  ├── GradientReading, ShiftRecord, GradientSnapshot, CrestRecord
  └── LevelingPlan, GradientProfile, GradientStats
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string.

    Used as the canonical timestamp for every record the engine creates.
    Centralizing it here keeps timestamps uniform across the engine and
    trivially interchangeable for testing — tests can monkey-patch
    ``_now`` to a deterministic function rather than reach into every
    record type.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/shift/etc.

    The identifier is the first eight characters of a UUID4, short
    enough to be readable in logs and long enough that collisions are
    negligible for an in-memory engine. Shorter ids are easier to scan
    visually when many records are returned together; full UUIDs are
    unnecessary here.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` score. A low-side default is
    safer than a mid-range one for gradient-like quantities where a
    spurious high reading would inflate the perceived steepness and
    push the agent's regime toward VERTICAL.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _clamp_positive_ms(value: float) -> float:
    """Clamp an interval or shift magnitude to a non-negative value.

    Durations and magnitudes must be non-negative; negative values are
    coerced to 0 rather than rejected so a misconfigured caller cannot
    crash the engine. The upper bound is left open because real
    intervals can legitimately exceed 1.0 — a long plateau between
    stage transitions or an extreme shift magnitude can span
    arbitrarily large values.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    if f < 0.0:
        return 0.0
    return f


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first
    against member values (e.g. ``"flat"``) and then against member
    names (e.g. ``"FLAT"``), so callers may pass either form. This
    lets the public API accept either the symbolic name or the
    lower-case value string from JSON payloads. Raises ``ValueError``
    if neither matches.
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


def _enum_value(enum_cls: type, value: Any) -> str:
    """Return the ``.value`` of an enum member, or a string fallback.

    Used inside ``to_dict`` methods so a stored field always serializes
    to a plain string even if a non-enum slipped in through direct
    construction. The ``enum_cls`` argument is taken for symmetry with
    ``_resolve_enum`` and to make the call sites self-documenting.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_regime(avg_gradient: float) -> "GradientRegime":
    """Classify a gradient regime from the average gradient score.

    The average gradient is clamped to [0, 1] where higher means a
    steeper slope. The bands are applied in order, so the first
    matching band wins: below 0.15 the field is FLAT (negligible
    slope — intensity is uniform); below 0.35 it is SHALLOW (gentle
    slope — intensity drifts slowly); below 0.55 it is SLOPED (clear
    slope — intensity changes at a noticeable rate); below 0.75 it is
    STEEP (pronounced slope — intensity ramps sharply); below 0.9 it
    is PRECIPITOUS (near-cliff — intensity climbs or drops over a
    very short span); otherwise it is VERTICAL (cliff — intensity
    jumps discontinuously, the field is locally discontinuous).
    """
    avg = _clamp(avg_gradient, 0.0, 1.0)
    if avg < 0.15:
        return GradientRegime.FLAT
    if avg < 0.35:
        return GradientRegime.SHALLOW
    if avg < 0.55:
        return GradientRegime.SLOPED
    if avg < 0.75:
        return GradientRegime.STEEP
    if avg < 0.9:
        return GradientRegime.PRECIPITOUS
    return GradientRegime.VERTICAL


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class GradientAxis(str, Enum):
    """The axis along which a gradient reading is taken.

    Each axis names a different dimension of cognitive intensity whose
    slope can be measured. ATTENTION is the steepness of focus — how
    sharply concentration rises toward a target. AROUSAL is the
    steepness of activation — how sharply energy climbs from baseline
    to alert. SALIENCE is the steepness of prominence — how markedly
    something stands out against its background. VALENCE is the
    steepness of affective tone — how sharply pleasantness or
    unpleasantness shifts across the field. CERTAINTY is the steepness
    of confidence — how sharply conviction ramps from doubt to
    assurance. URGENCY is the steepness of pressure-to-act — how
    sharply the demand for action mounts from idle to pressing.
    """
    ATTENTION = "attention"    # steepness of focus
    AROUSAL = "arousal"        # steepness of activation
    SALIENCE = "salience"      # steepness of prominence
    VALENCE = "valence"        # steepness of affective tone
    CERTAINTY = "certainty"    # steepness of confidence
    URGENCY = "urgency"        # steepness of pressure-to-act


class GradientRegime(str, Enum):
    """The regime an agent's gradient occupies, classified by steepness.

    Ranges from FLAT (negligible slope — intensity is uniform across
    the field) through SHALLOW (gentle slope — intensity drifts
    slowly), SLOPED (clear slope — intensity changes at a noticeable
    rate), STEEP (pronounced slope — intensity ramps sharply), and
    PRECIPITOUS (near-cliff — intensity climbs or drops over a very
    short span) to VERTICAL (cliff — intensity jumps discontinuously,
    the field is locally discontinuous). The regime is derived from
    the average gradient score across the agent's readings via
    ``_determine_regime``.
    """
    FLAT = "flat"                  # negligible slope, uniform intensity
    SHALLOW = "shallow"            # gentle slope, slow drift
    SLOPED = "sloped"              # clear slope, noticeable change
    STEEP = "steep"                # pronounced slope, sharp ramp
    PRECIPITOUS = "precipitous"    # near-cliff, very short span
    VERTICAL = "vertical"          # cliff, discontinuous jump


class GradientSource(str, Enum):
    """The source that produced a gradient in the intensity field.

    Each source names a different process that tilts the field.
    INTEREST is the pull of curiosity: an engaging topic tilts the
    field toward itself, steepening the slope of attention. THREAT is
    the spike of danger: a perceived threat throws the field into a
    sharp cliff, collapsing urgency toward the threat. NOVELTY is the
    jolt of the new: an unexpected stimulus abruptly raises salience,
    creating a fresh slope. GOAL is the concentration of aim: an
    active goal aligns the field, directing intensity toward the goal.
    SOCIAL is the tilt of other minds: the presence or attention of
    other agents bends the field, raising salience where attention is
    mutual. INTERNAL is the pressure of homeostasis: the agent's own
    internal state shifts the baseline of arousal and valence across
    the whole field.
    """
    INTEREST = "interest"    # pull of curiosity
    THREAT = "threat"        # spike of danger
    NOVELTY = "novelty"      # jolt of the new
    GOAL = "goal"            # concentration of aim
    SOCIAL = "social"        # tilt of other minds
    INTERNAL = "internal"    # pressure of homeostasis


class LevelingStrategy(str, Enum):
    """Strategy for reshaping the slope of the field deliberately.

    FLATTEN reduces the gradient toward zero, evening out intensity
    across the field — useful when an agent is over-focused and needs
    to widen its view. DAMPEN reduces the magnitude of the slope
    without eliminating its direction, softening a too-sharp
    concentration. CHANNEL narrows the slope to a single axis,
    focusing diffuse intensity into a directed beam. REDIRECT turns
    the slope toward a different target, re-pointing attention without
    changing its steepness. AMPLIFY increases the magnitude of the
    slope, sharpening concentration on what already stands out. INVERT
    reverses the direction of the slope, flipping high to low and low
    to high — useful when the agent's field is pointing the wrong way.
    """
    FLATTEN = "flatten"      # reduce gradient toward zero
    DAMPEN = "dampen"        # soften the slope's magnitude
    CHANNEL = "channel"      # narrow to a single axis
    REDIRECT = "redirect"    # re-point toward a different target
    AMPLIFY = "amplify"      # sharpen the slope's magnitude
    INVERT = "invert"        # reverse the slope's direction


class GradientStage(str, Enum):
    """The lifecycle stage of a gradient slope.

    UNIFORM is the starting state: the field is flat, intensity is
    the same everywhere. RISING is the phase in which a slope is
    forming — intensity is beginning to differentiate, climbing in
    one region. PEAKING is the state at which the slope reaches its
    maximum steepness. DESCENDING is the phase in which the slope is
    easing — intensity is leveling out as the peak softens. LEVELING
    is the state at which the field is actively being flattened back
    toward uniform. SETTLED is the stable state at which the field
    has come to rest at its new baseline slope. The engine records
    transitions between stages as CrestRecord entries.
    """
    UNIFORM = "uniform"        # flat, intensity uniform everywhere
    RISING = "rising"           # slope forming, intensity differentiating
    PEAKING = "peaking"         # slope at maximum steepness
    DESCENDING = "descending"   # slope easing, peak softening
    LEVELING = "leveling"       # field being flattened toward uniform
    SETTLED = "settled"         # field at rest at new baseline


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GradientReading:
    """One observation of gradient on a particular axis.

    ``axis`` is the ``GradientAxis`` the reading is taken on.
    ``gradient_score`` in [0, 1] measures how steep the slope is —
    0 means flat (uniform intensity), 1 means vertical (a cliff).
    ``gradient_source`` is the ``GradientSource`` that produced the
    slope. ``intensity`` in [0, 1] measures how emphatic the
    observation was. ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: GradientAxis
    gradient_score: float       # 0..1, higher = steeper slope
    gradient_source: GradientSource
    intensity: float            # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(GradientAxis, self.axis),
            "gradient_score": self.gradient_score,
            "gradient_source": _enum_value(GradientSource, self.gradient_source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ShiftRecord:
    """One shift event that changed the gradient of a slope.

    ``axis`` is the ``GradientAxis`` on which the shift occurred.
    ``gradient_source`` is the ``GradientSource`` that drove the
    change. ``before_score`` in [0, 1] is the gradient before the
    event; ``after_score`` in [0, 1] is the gradient after.
    ``shift_magnitude`` in [0, inf) measures how large the change
    was. ``notes`` is an optional free-form annotation.
    """
    shift_id: str
    agent_id: str
    axis: GradientAxis
    gradient_source: GradientSource
    before_score: float         # 0..1, gradient before the shift
    after_score: float          # 0..1, gradient after the shift
    shift_magnitude: float      # 0..inf, size of the change
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this shift record to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(GradientAxis, self.axis),
            "gradient_source": _enum_value(GradientSource, self.gradient_source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "shift_magnitude": self.shift_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class GradientSnapshot:
    """Aggregate gradient state for one agent at one moment.

    ``avg_gradient`` in [0, 1] is the mean gradient score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``GradientAxis`` among those readings, or ATTENTION
    if none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_gradient``. ``shift_count`` is the number of shift events
    recorded against the agent. ``notes`` is an optional free-form
    annotation.
    """
    snapshot_id: str
    agent_id: str
    avg_gradient: float
    dominant_axis: GradientAxis
    regime: GradientRegime
    shift_count: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_gradient": self.avg_gradient,
            "dominant_axis": _enum_value(GradientAxis, self.dominant_axis),
            "regime": _enum_value(GradientRegime, self.regime),
            "shift_count": self.shift_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class LevelingPlan:
    """A plan to reshape the slope of the field with a strategy.

    ``strategy`` is the ``LevelingStrategy`` chosen. ``target_gradient``
    in [0, 1] is the gradient the plan aims to reach. ``rationale``
    explains why this strategy was chosen for this field.
    """
    plan_id: str
    agent_id: str
    strategy: LevelingStrategy
    target_gradient: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(LevelingStrategy, self.strategy),
            "target_gradient": self.target_gradient,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class CrestRecord:
    """One record of a stage transition in the gradient lifecycle.

    ``from_stage`` is the ``GradientStage`` the agent's field was in
    before the transition. ``to_stage`` is the ``GradientStage`` it
    moved to. ``interval_ms`` in [0, inf) is the duration the
    from_stage held before the transition. ``signature`` is a
    free-form label that describes the character of the transition
    (e.g. "slow rise", "sudden peak", "smooth settle").
    """
    crest_id: str
    agent_id: str
    from_stage: GradientStage
    to_stage: GradientStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this crest record to a plain dict, expanding enums via ``.value``."""
        return {
            "crest_id": self.crest_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(GradientStage, self.from_stage),
            "to_stage": _enum_value(GradientStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class GradientProfile:
    """Per-agent aggregate gradient tendencies.

    ``avg_gradient`` in [0, 1] is the mean gradient score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``GradientAxis`` among the agent's readings, or
    ATTENTION if none. ``regime`` is derived via ``_determine_regime``
    from ``avg_gradient``. ``total_readings``, ``total_shifts``, and
    ``total_crests`` are the counts of each record type for the
    agent.
    """
    agent_id: str
    avg_gradient: float = 0.0
    dominant_axis: GradientAxis = GradientAxis.ATTENTION
    regime: GradientRegime = GradientRegime.SLOPED
    total_readings: int = 0
    total_shifts: int = 0
    total_crests: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_gradient": self.avg_gradient,
            "dominant_axis": _enum_value(GradientAxis, self.dominant_axis),
            "regime": _enum_value(GradientRegime, self.regime),
            "total_readings": self.total_readings,
            "total_shifts": self.total_shifts,
            "total_crests": self.total_crests,
        }


@dataclass
class GradientStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_gradient`` is the mean gradient score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the
    most frequent regime across all cached profiles, or SLOPED when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_shifts: int = 0
    total_snapshots: int = 0
    total_crests: int = 0
    avg_gradient: float = 0.0
    dominant_regime: GradientRegime = GradientRegime.SLOPED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_shifts": self.total_shifts,
            "total_snapshots": self.total_snapshots,
            "total_crests": self.total_crests,
            "avg_gradient": self.avg_gradient,
            "dominant_regime": _enum_value(GradientRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveGradient:
    """Thread-safe engine that models an agent's cognitive gradient.

    The engine holds six stores: ``_readings`` (GradientReading lists
    keyed by agent_id), ``_shifts`` (ShiftRecord lists keyed by
    agent_id), ``_snapshots`` (GradientSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of LevelingPlan), ``_crests``
    (CrestRecord lists keyed by agent_id), and ``_profiles``
    (GradientProfile keyed by agent_id, cached and invalidated on
    mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The gradient model is deliberately heuristic: gradient scores and
    intensities are caller-supplied observations; gradient regimes are
    banded from the average gradient; dominant axes are computed by
    mode; stage transitions are recorded as observed. These heuristics
    are transparent and auditable rather than learned, which keeps the
    engine deterministic.

    The engine is intentionally agnostic about how gradient is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure gradient itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, shifts, snapshots, or crests change, so
    ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose gradient scores feed into a
    # snapshot's average gradient. The window is long enough to smooth
    # a single noisy reading and short enough to reflect the agent's
    # current gradient posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty gradient engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[GradientReading]] = {}
        self._shifts: Dict[str, List[ShiftRecord]] = {}
        self._snapshots: Dict[str, List[GradientSnapshot]] = {}
        self._plans: List[LevelingPlan] = []
        self._crests: Dict[str, List[CrestRecord]] = {}
        self._profiles: Dict[str, GradientProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_gradient_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._shifts.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._crests.clear()
            self._profiles.clear()

    # -- Internal helpers (callers must already hold the lock) -------

    def _agent_readings_locked(self, agent_id: str) -> List[GradientReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[ShiftRecord]:
        """Return one agent's shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _agent_crests_locked(
        self, agent_id: str
    ) -> List[CrestRecord]:
        """Return one agent's crest records in insertion order. Caller holds the lock."""
        return list(self._crests.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[GradientReading]
    ) -> GradientAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns ATTENTION if the list is empty,
        since ATTENTION is the smallest and most neutral axis. Caller
        holds the lock.
        """
        if not readings:
            return GradientAxis.ATTENTION
        counts: Counter = Counter()
        first_seen_order: Dict[GradientAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: GradientAxis = readings[0].axis
        best_count = -1
        for axis, count in counts.items():
            if (count > best_count) or (
                count == best_count
                and first_seen_order.get(axis, 0)
                < first_seen_order.get(best_axis, 0)
            ):
                best_axis = axis
                best_count = count
        return best_axis

    def _mode_regime_locked(
        self, profiles: List[GradientProfile]
    ) -> GradientRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns SLOPED if the list is empty, since SLOPED is the
        neutral mid-range regime — neither too flat nor too steep.
        Caller holds the lock.
        """
        if not profiles:
            return GradientRegime.SLOPED
        counts: Dict[GradientRegime, int] = {}
        for profile in profiles:
            counts[profile.regime] = counts.get(profile.regime, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _current_gradient_locked(self, agent_id: str) -> float:
        """Return the agent's most recent gradient score, or the mean if none recent.

        Prefers the gradient score of the most recent reading, falling
        back to the mean of all readings when there is no clear
        most-recent one. Returns 0.0 when the agent has no readings.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        most_recent = readings[-1]
        return float(most_recent.gradient_score)

    def _compute_profile_locked(self, agent_id: str) -> GradientProfile:
        """Aggregate an agent's readings, shifts, and crests into a profile.

        See ``GradientProfile`` for field semantics. ``avg_gradient`` is
        the mean gradient score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent ``GradientAxis``
        among the agent's readings, or ATTENTION if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_gradient``.
        ``total_readings``, ``total_shifts``, and ``total_crests``
        count the records held for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)
        crests = self._agent_crests_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_gradient = sum(r.gradient_score for r in readings) / len(
                readings
            )
        else:
            avg_gradient = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        regime = _determine_regime(avg_gradient)

        return GradientProfile(
            agent_id=str(agent_id),
            avg_gradient=round(avg_gradient, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=total_readings,
            total_shifts=len(shifts),
            total_crests=len(crests),
        )

    # -- Gradient Readings -------------------------------------------

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        gradient_score: float,
        gradient_source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> GradientReading:
        """Record a gradient reading for an agent and return it.

        ``axis`` may be passed as a ``GradientAxis`` member or its
        string name/value. ``gradient_score`` and ``intensity`` are
        clamped to [0, 1]. ``gradient_source`` may be passed as a
        ``GradientSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = GradientReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(GradientAxis, axis),
                gradient_score=_clamp(gradient_score, 0.0, 1.0),
                gradient_source=_resolve_enum(GradientSource, gradient_source),
                intensity=_clamp(intensity, 0.0, 1.0),
                timestamp=_now(),
                notes=notes,
            )
            self._readings.setdefault(agent_id, []).append(reading)
            self._profiles.pop(agent_id, None)
            return reading

    def list_readings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[GradientReading]:
        """Return readings, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all readings are considered;
        otherwise only readings for that agent are returned. The most
        recently recorded ``limit`` readings are returned (insertion
        order is chronological, so the tail is the most recent). The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                readings = self._agent_readings_locked(agent_id)
            else:
                readings = []
                for agent_readings in self._readings.values():
                    readings.extend(agent_readings)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return readings[-n:] if n else []

    def get_reading(self, reading_id: str) -> GradientReading:
        """Retrieve a reading by id.

        Raises ``ValueError`` if no reading exists with that id, so
        callers can treat the return as a guaranteed non-None value
        and let a single exception type stand in for a not-found
        error.
        """
        with self._lock:
            for agent_readings in self._readings.values():
                for reading in agent_readings:
                    if reading.reading_id == reading_id:
                        return reading
        raise ValueError(f"reading {reading_id!r} not found")

    # -- Shift Records -----------------------------------------------

    def record_shift(
        self,
        agent_id: str,
        axis: Any,
        gradient_source: Any,
        before_score: float,
        after_score: float,
        shift_magnitude: float,
        notes: Optional[str] = None,
    ) -> ShiftRecord:
        """Record a shift event for an agent and return it.

        ``axis`` may be passed as a ``GradientAxis`` member or its
        string name/value. ``gradient_source`` may be passed as a
        ``GradientSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``shift_magnitude`` is clamped to [0, inf). The shift is stored
        and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            record = ShiftRecord(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(GradientAxis, axis),
                gradient_source=_resolve_enum(GradientSource, gradient_source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                shift_magnitude=_clamp_positive_ms(shift_magnitude),
                timestamp=_now(),
                notes=notes,
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ShiftRecord]:
        """Return shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all shifts are considered;
        otherwise only shifts for that agent are returned. The most
        recently recorded ``limit`` shifts are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                shifts = self._agent_shifts_locked(agent_id)
            else:
                shifts = []
                for agent_shifts in self._shifts.values():
                    shifts.extend(agent_shifts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return shifts[-n:] if n else []

    def get_shift(self, shift_id: str) -> ShiftRecord:
        """Retrieve a shift record by id.

        Raises ``ValueError`` if no shift exists with that id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for shift in agent_shifts:
                    if shift.shift_id == shift_id:
                        return shift
        raise ValueError(f"shift {shift_id!r} not found")

    # -- Snapshots --------------------------------------------------

    def take_snapshot(self, agent_id: str) -> GradientSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_gradient`` is the mean gradient score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``GradientAxis`` among those readings, or ATTENTION if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_gradient``. ``shift_count`` is the number of shift
        events recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_gradient = sum(r.gradient_score for r in recent) / len(
                    recent
                )
            else:
                avg_gradient = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_gradient)
            shift_count = len(self._agent_shifts_locked(agent_id))

            snapshot = GradientSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_gradient=round(avg_gradient, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                shift_count=shift_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[GradientSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The most
        recently taken ``limit`` snapshots are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                snapshots = list(self._snapshots.get(agent_id, []))
            else:
                snapshots = []
                for agent_snapshots in self._snapshots.values():
                    snapshots.extend(agent_snapshots)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return snapshots[-n:] if n else []

    def get_snapshot(self, snapshot_id: str) -> GradientSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # -- Leveling Plans ---------------------------------------------

    def plan_leveling(
        self,
        agent_id: str,
        strategy: Any,
        target_gradient: float,
        rationale: str,
    ) -> LevelingPlan:
        """Record a leveling plan for an agent and return it.

        ``strategy`` may be passed as a ``LevelingStrategy`` member or
        its string name/value. ``target_gradient`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached profile
        is not invalidated, since a plan does not change the agent's
        measured gradient.
        """
        with self._lock:
            plan = LevelingPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(LevelingStrategy, strategy),
                target_gradient=_clamp(target_gradient, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LevelingPlan]:
        """Return leveling plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered;
        otherwise only plans for that agent are returned. The most
        recently recorded ``limit`` plans are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                plans = [p for p in self._plans if p.agent_id == agent_id]
            else:
                plans = list(self._plans)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> LevelingPlan:
        """Retrieve a leveling plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # -- Crest Records ----------------------------------------------

    def record_crest(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> CrestRecord:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``GradientStage`` member or its string name/value.
        ``interval_ms`` in [0, inf) is the duration the from_stage
        held before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        rise", "sudden peak", "smooth settle"). The crest record is
        stored and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            record = CrestRecord(
                crest_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(GradientStage, from_stage),
                to_stage=_resolve_enum(GradientStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._crests.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_crests(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CrestRecord]:
        """Return crest records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all crests are considered;
        otherwise only crests for that agent are returned. The most
        recently recorded ``limit`` crest records are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                crests = self._agent_crests_locked(agent_id)
            else:
                crests = []
                for agent_crests in self._crests.values():
                    crests.extend(agent_crests)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return crests[-n:] if n else []

    def get_crest(self, crest_id: str) -> CrestRecord:
        """Retrieve a crest record by id.

        Raises ``ValueError`` if no crest record exists with that id.
        """
        with self._lock:
            for agent_crests in self._crests.values():
                for record in agent_crests:
                    if record.crest_id == crest_id:
                        return record
        raise ValueError(f"crest record {crest_id!r} not found")

    # -- Profiles ---------------------------------------------------

    def get_profile(self, agent_id: str) -> GradientProfile:
        """Return the agent's gradient profile, building it if missing.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, shifts, snapshots, or crests change. If
        the agent has data but no profile yet, the profile is built
        from the live stores. Call ``update_profile`` to force a
        refresh or override a computed field. Field semantics are
        documented on ``GradientProfile`` and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> GradientProfile:
        """Refresh and optionally override fields of an agent's gradient profile.

        The profile is first recomputed from the live stores, then
        any supplied keyword overrides (matching ``GradientProfile``
        field names) are applied. Accepted overrides: ``avg_gradient``
        (float), ``dominant_axis`` (``GradientAxis``), ``regime``
        (``GradientRegime``), ``total_readings``, ``total_shifts``,
        ``total_crests`` (int). Enum-valued overrides may be passed as
        the enum member or its string name/value. Unknown keys are
        ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_gradient":
                    try:
                        profile.avg_gradient = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            GradientAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(
                            GradientRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_shifts",
                    "total_crests",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[GradientProfile]:
        """Return all stored gradient profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # -- Statistics --------------------------------------------------

    def get_stats(self) -> GradientStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, shifts, snapshots, and crests. Scalar
        totals are the counts of each record type. ``avg_gradient`` is
        the mean gradient score across all readings, or 0.0 when none
        exist. ``dominant_regime`` is the most frequent regime across
        all cached profiles, or SLOPED when none exist. When no
        profiles exist but readings do, the dominant regime is derived
        from the average gradient via ``_determine_regime`` so the
        stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._shifts.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._crests.keys())

            total_readings = 0
            gradient_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    gradient_sum += reading.gradient_score
            avg_gradient = (
                round(gradient_sum / total_readings, 4) if total_readings else 0.0
            )

            total_shifts = sum(
                len(agent_shifts)
                for agent_shifts in self._shifts.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_crests = sum(
                len(agent_crests) for agent_crests in self._crests.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average gradient so the stats
                # reflect real state rather than the default SLOPED.
                dominant_regime = _determine_regime(avg_gradient)
            else:
                dominant_regime = GradientRegime.SLOPED

            return GradientStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_shifts=total_shifts,
                total_snapshots=total_snapshots,
                total_crests=total_crests,
                avg_gradient=avg_gradient,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveGradient] = None
_engine_lock = threading.Lock()


def get_gradient_engine() -> AgentCognitiveGradient:
    """Get or create the singleton ``AgentCognitiveGradient`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveGradient()
    return _engine


def reset_gradient_engine() -> None:
    """Reset the singleton ``AgentCognitiveGradient`` instance.

    Drops the reference to the current engine so the next
    ``get_gradient_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
