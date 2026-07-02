from __future__ import annotations

"""Agent Cognitive Pendulum Engine — modeling oscillation between cognitive states

How cognitive states swing, damp, resonate, and settle over time. A swinging
agent oscillates between states with visible amplitude; a still agent rests at
equilibrium. Distinct from magnetism, coherence, tension, equilibrium, and
affinity.
Core capabilities: axis tracking, force sources, oscillation strategies, settling stages.

Architecture:
  AgentCognitivePendulum (singleton)
  ├── PendulumReading      (one observation of pendulum on one axis)
  ├── OscillationRecord    (one oscillation event that changed pendulum)
  ├── PendulumSnapshot     (aggregate pendulum state for one agent)
  ├── PendulumPlan         (a plan to shape the oscillation with a strategy)
  ├── AmplitudeShift       (one stage transition in the settling lifecycle)
  ├── PendulumProfile      (per-agent aggregate pendulum tendencies)
  └── PendulumStats        (engine-wide aggregate statistics)
"""

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
    """Generate a short unique identifier for a reading/oscillation/etc.

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
    engine with a ``NaN`` or ``None`` pendulum. A low-side default is
    safer than a mid-range one for pendulum-like quantities where a
    spurious high reading would inflate the perceived pendulum and
    push the agent's regime toward RESONANT.
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
    """Clamp a non-negative quantity (interval, magnitude) to [0, ∞).

    Interval and magnitude values must be non-negative; negative values
    are coerced to 0 rather than rejected so a misconfigured caller
    cannot crash the engine. The upper bound is left open because
    real settling intervals and oscillation magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    amplification may apply a large effective oscillation.
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
    against member values (e.g. ``"gravity"``) and then against
    member names (e.g. ``"GRAVITY"``), so callers may pass either
    form. This lets the public API accept either the symbolic name or
    the lower-case value string from JSON payloads. Raises
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


def _determine_regime(avg_pendulum: float) -> "PendulumRegime":
    """Classify a pendulum regime from the average pendulum score.

    The average pendulum is clamped to [0, 1] where higher means a
    more oscillating, swinging posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is STILL
    (no motion, at rest); below 0.35 it is DAMPED (weak motion, decaying
    quickly); below 0.55 it is OSCILLATING (regular motion, sustained
    cycles); below 0.75 it is SWINGING (large motion, high amplitude);
    below 0.9 it is CHAOTIC (irregular motion, unpredictable); otherwise
    it is RESONANT (amplified motion, driven at natural frequency).
    """
    avg = _clamp(avg_pendulum, 0.0, 1.0)
    if avg < 0.15:
        return PendulumRegime.STILL
    if avg < 0.35:
        return PendulumRegime.DAMPED
    if avg < 0.55:
        return PendulumRegime.OSCILLATING
    if avg < 0.75:
        return PendulumRegime.SWINGING
    if avg < 0.9:
        return PendulumRegime.CHAOTIC
    return PendulumRegime.RESONANT


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class PendulumAxis(str, Enum):
    """The axis along which a pendulum reading is taken.

    Each axis names a different dimension of the agent's cognitive
    oscillation whose pendulum can be measured. SWING is the lateral
    motion between states. AMPLITUDE is the maximum displacement from
    rest. PERIOD is the time for one full cycle. DAMPING is the decay
    rate of oscillation. REST is the equilibrium position. EXTREME is
    the peak displacement reached.
    """
    SWING = "swing"        # lateral motion between states
    AMPLITUDE = "amplitude"  # maximum displacement from rest
    PERIOD = "period"      # time for one full cycle
    DAMPING = "damping"    # decay rate of oscillation
    REST = "rest"          # equilibrium position
    EXTREME = "extreme"    # peak displacement reached


class PendulumRegime(str, Enum):
    """The regime an agent's pendulum occupies, classified by pendulum.

    Ranges from STILL (no motion, at rest) through DAMPED (weak motion,
    decaying quickly), OSCILLATING (regular motion, sustained cycles),
    SWINGING (large motion, high amplitude), and CHAOTIC (irregular
    motion, unpredictable) to RESONANT (amplified motion, driven at
    natural frequency). The regime is derived from the average pendulum
    across the agent's readings via ``_determine_regime``.
    """
    STILL = "still"            # no motion, at rest
    DAMPED = "damped"          # weak motion, decaying
    OSCILLATING = "oscillating"  # regular motion, sustained
    SWINGING = "swinging"      # large motion, high amplitude
    CHAOTIC = "chaotic"        # irregular motion, unpredictable
    RESONANT = "resonant"      # amplified motion, driven


class PendulumSource(str, Enum):
    """A source that supplies the driving or damping force.

    Each source names a different origin of the force driving the
    oscillation. GRAVITY pulls toward the resting state. IMPULSE is a
    sudden push that starts motion. FRICTION is the resistance that
    damps motion. RESONANCE is the matching frequency that amplifies.
    TENSION is the stored energy that releases. MOMENTUM is the carried
    motion from previous swings. A pendulum reading records which
    source supplies the force on the measured axis, and an oscillation
    record records which source drove a change.
    """
    GRAVITY = "gravity"    # pull toward rest
    IMPULSE = "impulse"    # sudden push
    FRICTION = "friction"  # resistance that damps
    RESONANCE = "resonance"  # matching frequency
    TENSION = "tension"    # stored energy
    MOMENTUM = "momentum"  # carried motion


class PendulumStrategy(str, Enum):
    """Strategy for shaping the oscillation deliberately.

    DAMP reduces amplitude. AMPLIFY increases amplitude. RELEASE lets
    the pendulum swing freely. ARREST brings it to rest. TUNE adjusts
    the period. INVERT reverses the phase. Each strategy is suited to
    a different oscillation condition, from calming a chaotic swing to
    releasing a stuck one.
    """
    DAMP = "damp"          # reduce amplitude
    AMPLIFY = "amplify"    # increase amplitude
    RELEASE = "release"    # let swing freely
    ARREST = "arrest"      # bring to rest
    TUNE = "tune"          # adjust period
    INVERT = "invert"      # reverse phase


class PendulumStage(str, Enum):
    """The lifecycle stage of an agent's oscillation process.

    REST is the state of no motion. RELEASED is the phase of starting
    to move. SWINGING is the state of active oscillation. PEAK is the
    state at maximum displacement. RETURNING is the state moving back
    toward rest. SETTLING is the final state damping toward rest. The
    engine records transitions between stages as AmplitudeShift
    entries.
    """
    REST = "rest"            # no motion
    RELEASED = "released"    # starting to move
    SWINGING = "swinging"    # active oscillation
    PEAK = "peak"            # maximum displacement
    RETURNING = "returning"  # moving back toward rest
    SETTLING = "settling"    # damping toward rest


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PendulumReading:
    """One observation of pendulum on a particular axis.

    ``axis`` is the ``PendulumAxis`` the reading is taken on.
    ``pendulum_score`` in [0, 1] measures how oscillating the agent is
    on that axis — 0 means fully still, 1 means fully resonant.
    ``source`` is the ``PendulumSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: PendulumAxis
    pendulum_score: float    # 0..1, higher = more oscillating
    source: PendulumSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(PendulumAxis, self.axis),
            "pendulum_score": self.pendulum_score,
            "source": _enum_value(PendulumSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class OscillationRecord:
    """One oscillation event that changed the pendulum on an axis.

    ``axis`` is the ``PendulumAxis`` on which the oscillation occurred.
    ``source`` is the ``PendulumSource`` that drove the change.
    ``before_score`` in [0, 1] is the pendulum before the event;
    ``after_score`` in [0, 1] is the pendulum after.
    ``oscillation_magnitude`` in [0, ∞) measures how strong the
    oscillation was. ``notes`` is an optional free-form annotation.
    """
    oscillation_id: str
    agent_id: str
    axis: PendulumAxis
    source: PendulumSource
    before_score: float              # 0..1, pendulum before oscillation
    after_score: float               # 0..1, pendulum after oscillation
    oscillation_magnitude: float     # 0..inf, strength of oscillation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this oscillation record to a plain dict, expanding enums via ``.value``."""
        return {
            "oscillation_id": self.oscillation_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(PendulumAxis, self.axis),
            "source": _enum_value(PendulumSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "oscillation_magnitude": self.oscillation_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class PendulumSnapshot:
    """Aggregate pendulum state for one agent at one moment.

    ``avg_pendulum`` in [0, 1] is the mean pendulum score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``PendulumAxis`` among those readings, or
    SWING if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_pendulum``. ``oscillation_count``
    is the number of oscillation events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_pendulum: float
    dominant_axis: PendulumAxis
    regime: PendulumRegime
    oscillation_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_pendulum": self.avg_pendulum,
            "dominant_axis": _enum_value(PendulumAxis, self.dominant_axis),
            "dominant_regime": _enum_value(PendulumRegime, self.regime),
            "regime": _enum_value(PendulumRegime, self.regime),
            "oscillation_count": self.oscillation_count,
            "timestamp": self.timestamp,
        }


@dataclass
class PendulumPlan:
    """A plan to shape the oscillation with a strategy.

    ``strategy`` is the ``PendulumStrategy`` chosen.
    ``target_pendulum`` in [0, 1] is the pendulum the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's oscillation condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current pendulum — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: PendulumStrategy
    target_pendulum: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(PendulumStrategy, self.strategy),
            "target_pendulum": self.target_pendulum,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class AmplitudeShift:
    """One record of a stage transition in the settling lifecycle.

    ``from_stage`` is the ``PendulumStage`` the agent was in before
    the transition. ``to_stage`` is the ``PendulumStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow release",
    "sudden peak", "deliberate amplification").
    """
    shift_id: str
    agent_id: str
    from_stage: PendulumStage
    to_stage: PendulumStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this amplitude shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(PendulumStage, self.from_stage),
            "to_stage": _enum_value(PendulumStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class PendulumProfile:
    """Per-agent aggregate pendulum tendencies.

    ``avg_pendulum`` in [0, 1] is the mean pendulum score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``PendulumAxis`` among the agent's readings, or
    SWING if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_pendulum``. ``total_readings``,
    ``total_oscillations``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_pendulum: float = 0.0
    dominant_axis: PendulumAxis = PendulumAxis.SWING
    dominant_regime: PendulumRegime = PendulumRegime.OSCILLATING
    total_readings: int = 0
    total_oscillations: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_pendulum": self.avg_pendulum,
            "dominant_axis": _enum_value(PendulumAxis, self.dominant_axis),
            "dominant_regime": _enum_value(PendulumRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_oscillations": self.total_oscillations,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class PendulumStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_pendulum`` is the mean pendulum score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or OSCILLATING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_oscillations: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_pendulum: float = 0.0
    dominant_regime: PendulumRegime = PendulumRegime.OSCILLATING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_oscillations": self.total_oscillations,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_pendulum": self.avg_pendulum,
            "dominant_regime": _enum_value(PendulumRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitivePendulum:
    """Thread-safe engine that models an agent's cognitive pendulum.

    The engine holds six stores: ``_readings`` (PendulumReading lists
    keyed by agent_id), ``_oscillations`` (OscillationRecord lists keyed
    by agent_id), ``_snapshots`` (PendulumSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of PendulumPlan),
    ``_shifts`` (AmplitudeShift lists keyed by agent_id), and
    ``_profiles`` (PendulumProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The pendulum model is deliberately heuristic: pendulum scores
    and intensities are caller-supplied observations; pendulum
    regimes are banded from the average pendulum; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how pendulum is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure pendulum itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, oscillations, snapshots, or shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose pendulum scores feed into
    # a snapshot's average pendulum. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current pendulum posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty pendulum engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[PendulumReading]] = {}
        self._oscillations: Dict[str, List[OscillationRecord]] = {}
        self._snapshots: Dict[str, List[PendulumSnapshot]] = {}
        self._plans: List[PendulumPlan] = []
        self._shifts: Dict[str, List[AmplitudeShift]] = {}
        self._profiles: Dict[str, PendulumProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_pendulum_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._oscillations.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[PendulumReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_oscillations_locked(
        self, agent_id: str
    ) -> List[OscillationRecord]:
        """Return one agent's oscillation records in insertion order. Caller holds the lock."""
        return list(self._oscillations.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[PendulumSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[PendulumPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[AmplitudeShift]:
        """Return one agent's amplitude shifts in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[PendulumReading]
    ) -> PendulumAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns SWING if the list is
        empty, since SWING is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return PendulumAxis.SWING
        counts: Counter = Counter()
        first_seen_order: Dict[PendulumAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: PendulumAxis = readings[0].axis
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
        self, profiles: List[PendulumProfile]
    ) -> PendulumRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns OSCILLATING if the list is empty, since
        OSCILLATING is the default regime — the band that
        represents a normally functioning cognitive pendulum that
        sustains regular cycles without being still or resonant,
        neither damped nor chaotic. Caller holds the lock.
        """
        if not profiles:
            return PendulumRegime.OSCILLATING
        counts: Dict[PendulumRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> PendulumProfile:
        """Aggregate an agent's readings, oscillations, and shifts into a profile.

        See ``PendulumProfile`` for field semantics. ``avg_pendulum``
        is the mean pendulum score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``PendulumAxis`` among the agent's readings, or SWING
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_pendulum``.
        ``total_readings``, ``total_oscillations``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        oscillations = self._agent_oscillations_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_pendulum = sum(
                r.pendulum_score for r in readings
            ) / len(readings)
        else:
            avg_pendulum = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_pendulum)

        return PendulumProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_pendulum=round(avg_pendulum, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_oscillations=len(oscillations),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Pendulum Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        pendulum_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> PendulumReading:
        """Record a pendulum reading for an agent and return it.

        ``axis`` may be passed as a ``PendulumAxis`` member or its
        string name/value. ``pendulum_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``PendulumSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = PendulumReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(PendulumAxis, axis),
                pendulum_score=_clamp(pendulum_score, 0.0, 1.0),
                source=_resolve_enum(PendulumSource, source),
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
    ) -> List[PendulumReading]:
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

    def get_reading(self, reading_id: str) -> PendulumReading:
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

    # ── Oscillation Records ────────────────────────────────────────

    def record_oscillation(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        oscillation_magnitude: float,
        notes: Optional[str] = None,
    ) -> OscillationRecord:
        """Record an oscillation event for an agent and return it.

        ``axis`` may be passed as a ``PendulumAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``PendulumSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``oscillation_magnitude`` is clamped to [0, ∞). The oscillation
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = OscillationRecord(
                oscillation_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(PendulumAxis, axis),
                source=_resolve_enum(PendulumSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                oscillation_magnitude=_clamp_positive_ms(
                    oscillation_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._oscillations.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_oscillations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[OscillationRecord]:
        """Return oscillation records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all oscillations are considered;
        otherwise only oscillations for that agent are returned. The
        most recently recorded ``limit`` oscillations are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                oscillations = self._agent_oscillations_locked(agent_id)
            else:
                oscillations = []
                for agent_oscillations in self._oscillations.values():
                    oscillations.extend(agent_oscillations)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return oscillations[-n:] if n else []

    def get_oscillation(self, oscillation_id: str) -> OscillationRecord:
        """Retrieve an oscillation record by id.

        Raises ``ValueError`` if no oscillation exists with that id.
        """
        with self._lock:
            for agent_oscillations in self._oscillations.values():
                for oscillation in agent_oscillations:
                    if oscillation.oscillation_id == oscillation_id:
                        return oscillation
        raise ValueError(f"oscillation {oscillation_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> PendulumSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_pendulum`` is the mean pendulum score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``PendulumAxis`` among
        those readings, or SWING if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_pendulum``.
        ``oscillation_count`` is the number of oscillation events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_pendulum = sum(
                    r.pendulum_score for r in recent
                ) / len(recent)
            else:
                avg_pendulum = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_pendulum)
            oscillation_count = len(
                self._agent_oscillations_locked(agent_id)
            )

            snapshot = PendulumSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_pendulum=round(avg_pendulum, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                oscillation_count=oscillation_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PendulumSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The
        most recently taken ``limit`` snapshots are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                snapshots = self._agent_snapshots_locked(agent_id)
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

    def get_snapshot(self, snapshot_id: str) -> PendulumSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Pendulum Plans ────────────────────────────────────────────

    def plan_oscillation(
        self,
        agent_id: str,
        strategy: Any,
        target_pendulum: float,
        rationale: str,
    ) -> PendulumPlan:
        """Record a pendulum plan for an agent and return it.

        ``strategy`` may be passed as a ``PendulumStrategy`` member
        or its string name/value. ``target_pendulum`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured pendulum.
        """
        with self._lock:
            plan = PendulumPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(PendulumStrategy, strategy),
                target_pendulum=_clamp(target_pendulum, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PendulumPlan]:
        """Return pendulum plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered;
        otherwise only plans for that agent are returned. The most
        recently recorded ``limit`` plans are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                plans = self._agent_plans_locked(agent_id)
            else:
                plans = list(self._plans)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> PendulumPlan:
        """Retrieve a pendulum plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Amplitude Shift Records ────────────────────────────────────

    def record_amplitude_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> AmplitudeShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``PendulumStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        release", "sudden peak", "deliberate amplification"). The
        amplitude shift is stored and returned; the agent's cached
        profile is invalidated.

        Amplitude shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = AmplitudeShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(PendulumStage, from_stage),
                to_stage=_resolve_enum(PendulumStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_amplitude_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AmplitudeShift]:
        """Return amplitude shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all amplitude shifts are considered;
        otherwise only amplitude shifts for that agent are returned. The
        most recently recorded ``limit`` amplitude shift records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
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

    def get_amplitude_shift(self, shift_id: str) -> AmplitudeShift:
        """Retrieve an amplitude shift record by id.

        Raises ``ValueError`` if no amplitude shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"amplitude shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> PendulumProfile:
        """Return the agent's pendulum profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, oscillations, snapshots, or
        shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``PendulumProfile``
        and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(
        self, agent_id: str, **kwargs: Any
    ) -> PendulumProfile:
        """Refresh and optionally override fields of an agent's pendulum profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``PendulumProfile`` field names) are applied. Accepted
        overrides: ``avg_pendulum`` (float), ``dominant_axis``
        (``PendulumAxis``), ``dominant_regime``
        (``PendulumRegime``), ``total_readings``,
        ``total_oscillations``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_pendulum":
                    try:
                        profile.avg_pendulum = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            PendulumAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            PendulumRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_oscillations",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[PendulumProfile]:
        """Return all stored pendulum profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> PendulumStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, oscillations, snapshots, and shifts.
        Scalar totals are the counts of each record type.
        ``avg_pendulum`` is the mean pendulum score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        OSCILLATING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        pendulum via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._oscillations.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            pendulum_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    pendulum_sum += reading.pendulum_score
            avg_pendulum = (
                round(pendulum_sum / total_readings, 4) if total_readings else 0.0
            )

            total_oscillations = sum(
                len(agent_oscillations)
                for agent_oscillations in self._oscillations.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_shifts = sum(
                len(agent_shifts)
                for agent_shifts in self._shifts.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average pendulum so the stats
                # reflect real state rather than the default
                # OSCILLATING.
                dominant_regime = _determine_regime(avg_pendulum)
            else:
                dominant_regime = PendulumRegime.OSCILLATING

            return PendulumStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_oscillations=total_oscillations,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_pendulum=avg_pendulum,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitivePendulum] = None
_engine_lock = threading.Lock()


def get_pendulum_engine() -> AgentCognitivePendulum:
    """Get or create the singleton ``AgentCognitivePendulum`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitivePendulum()
    return _engine


def reset_pendulum_engine() -> None:
    """Reset the singleton ``AgentCognitivePendulum`` instance.

    Drops the reference to the current engine so the next
    ``get_pendulum_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
