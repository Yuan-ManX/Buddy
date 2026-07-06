"""Agent Cognitive Drift Engine — slow semantic motion of concepts

Drift tracks how an agent's meanings and category boundaries shift over
time, distinct from polarization, refraction, diffusion, and osmosis.

Core capabilities:
  - Per-axis readings, boundary shifts, regimes, plans, calibrations, profiles, stats

Architecture:
  AgentCognitiveDrift (singleton)
  ├── DriftReading        (one observation of drift along one axis)
  ├── BoundaryShift       (one boundary-state transition)
  ├── DriftSnapshot       (aggregate drift state for one agent)
  ├── AnchoringPlan       (a plan to reduce or direct drift)
  ├── CalibrationRecord   (one expected-vs-observed drift comparison)
  ├── DriftProfile        (per-agent aggregate drift tendencies)
  └── DriftStats          (engine-wide aggregate statistics)
"""

from __future__ import annotations

import threading
import time
import uuid
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
    trivially interchangeable for testing.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/shift/snapshot/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` drift magnitude. A low-side default
    is safer than a mid-range one for drift-like quantities where a
    spurious high reading would overstate the perceived motion.
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


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first
    against member values (e.g. ``"semantic"``) and then against member
    names (e.g. ``"SEMANTIC"``), so callers may pass either form. This
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


def _determine_regime(avg_drift: float) -> "DriftRegime":
    """Classify a drift regime from the average drift magnitude.

    The average is clamped to [0, 1] where higher means more drift.
    The checks are applied in order, so the first matching band wins:
    below 0.15 the concept is ANCHORED (essentially fixed); below 0.3
    it is CREEPING (small but detectable change); below 0.5 it is
    SLIDING (steady motion, glacier-like); below 0.7 it is DRIFTING
    (substantial motion, current-like); below 0.88 it is MIGRATING
    (large motion, species-range-like); otherwise it is UNMOORED
    (the concept has lost its anchor). The bands mirror the
    geological progression from anchored bedrock through creeping
    fault to unmoored continental fragment.
    """
    avg = _clamp(avg_drift, 0.0, 1.0)
    if avg < 0.15:
        return DriftRegime.ANCHORED
    if avg < 0.3:
        return DriftRegime.CREEPING
    if avg < 0.5:
        return DriftRegime.SLIDING
    if avg < 0.7:
        return DriftRegime.DRIFTING
    if avg < 0.88:
        return DriftRegime.MIGRATING
    return DriftRegime.UNMOORED


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class DriftAxis(str, Enum):
    """The axis along which a concept is drifting.

    Six axes span the kinds of change a concept can undergo. SEMANTIC
    drift is the shift in the meaning of a word or symbol. PRAGMATIC
    drift is the shift in how a concept is used in practice.
    EMOTIONAL drift is the shift in the affective charge. EPISTEMIC
    drift is the shift in claimed knowledge. NORMATIVE drift is the
    shift in rule status. AESTHETIC drift is the shift in taste and
    style. Each axis can drift independently.
    """
    SEMANTIC = "semantic"        # meaning of a word or symbol
    PRAGMATIC = "pragmatic"      # use in practice
    EMOTIONAL = "emotional"      # affective charge
    EPISTEMIC = "epistemic"      # what is claimed to be known
    NORMATIVE = "normative"      # rule status
    AESTHETIC = "aesthetic"      # taste and style


class DriftRegime(str, Enum):
    """The drift regime a concept currently occupies.

    Ranges from ANCHORED (essentially fixed) through CREEPING (small
    change), SLIDING (steady motion), and DRIFTING (substantial
    motion) to MIGRATING (large motion) and UNMOORED (anchor lost).
    See ``_determine_regime`` for the band thresholds.
    """
    ANCHORED = "anchored"        # essentially fixed
    CREEPING = "creeping"        # small but detectable change
    SLIDING = "sliding"          # steady motion
    DRIFTING = "drifting"        # substantial motion
    MIGRATING = "migrating"      # large motion
    UNMOORED = "unmoored"        # anchor lost


class BoundaryState(str, Enum):
    """The state of a concept's category boundary.

    Ranges from RIGID (hard-edged) through FIRM (clear with
    hesitation) and POROUS (admits borderline cases) to BREATHING
    (expands and contracts with context), FLUID (continuous
    gradient), and DISSOLVED (no longer functions as a category).
    """
    RIGID = "rigid"              # hard-edged boundary
    FIRM = "firm"                # clear with hesitation
    POROUS = "porous"            # admits borderline cases
    BREATHING = "breathing"      # expands and contracts with context
    FLUID = "fluid"              # continuous gradient
    DISSOLVED = "dissolved"      # no longer a category


class AnchoringStrategy(str, Enum):
    """Strategy for reducing or directing drift.

    Ranges from full suppression (LOCK, TETHER) through reference
    (MARK) and renewal (RENEW) to controlled release (RELAX,
    RELEASE). Each strategy suits a different regime: LOCK for
    emergency holds, TETHER for long-term resistance, RENEW for
    eroded boundaries, RELAX for planned adjustment, RELEASE for
    deliberate letting-go.
    """
    LOCK = "lock"                # pin at current position
    MARK = "mark"                # place a reference point
    TETHER = "tether"            # attach to external anchor
    RENEW = "renew"              # refresh via canonical examples
    RELAX = "relax"              # loosen anchor slightly
    RELEASE = "release"          # let the concept move


class DriftSignature(str, Enum):
    """The temporal signature of a concept's drift.

    Each signature is a shape on the time series. NEUTRAL is no
    pattern. MONOTONIC moves in one direction. CYCLICAL oscillates.
    EXPONENTIAL accelerates. STEP happens in sudden jumps.
    RANDOM_WALK has independent steps. Recognizing the signature
    helps choose an anchoring strategy.
    """
    NEUTRAL = "neutral"              # no clear pattern
    MONOTONIC = "monotonic"          # one direction
    CYCLICAL = "cyclical"            # oscillates
    EXPONENTIAL = "exponential"      # accelerates
    STEP = "step"                    # sudden jumps
    RANDOM_WALK = "random_walk"      # independent steps


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DriftReading:
    """One observation of drift along one axis at one moment.

    ``drift_magnitude`` in [0, 1] is how much the concept has moved
    along this axis; ``direction`` in [-1, 1] is the sign of the
    motion (positive meaning the concept is moving in the
    conventional direction, negative meaning the opposite).
    ``boundary_state`` is the boundary state observed at the time of
    the reading. ``signature`` is the temporal signature detected in
    the local time series. ``notes`` is optional free-form context.
    """
    reading_id: str
    agent_id: str
    axis: DriftAxis
    drift_magnitude: float      # 0..1
    direction: float            # -1..1
    boundary_state: BoundaryState
    signature: DriftSignature
    timestamp: str
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(DriftAxis, self.axis),
            "drift_magnitude": self.drift_magnitude,
            "direction": self.direction,
            "boundary_state": _enum_value(BoundaryState, self.boundary_state),
            "signature": _enum_value(DriftSignature, self.signature),
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BoundaryShift:
    """One boundary-state transition for an agent.

    ``from_boundary`` and ``to_boundary`` are the ``BoundaryState``
    values before and after the shift. ``magnitude`` in [0, 1] is how
    large the shift was; ``cause`` is a free-form label for what
    drove the shift. ``notes`` is optional free-form context.
    """
    shift_id: str
    agent_id: str
    axis: DriftAxis
    from_boundary: BoundaryState
    to_boundary: BoundaryState
    magnitude: float            # 0..1
    cause: str
    timestamp: str
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(DriftAxis, self.axis),
            "from_boundary": _enum_value(BoundaryState, self.from_boundary),
            "to_boundary": _enum_value(BoundaryState, self.to_boundary),
            "magnitude": self.magnitude,
            "cause": self.cause,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class DriftSnapshot:
    """Aggregate drift state for one agent.

    ``avg_drift`` in [0, 1] is the mean magnitude across the agent's
    recent readings. ``regime`` is derived via ``_determine_regime``.
    ``dominant_axis`` is the axis with the highest mean magnitude
    across the agent's readings, or SEMANTIC if none. ``boundary_state``
    is the most frequent boundary state across the agent's readings,
    or FIRM if none. ``shift_count`` is the number of boundary shifts
    the agent currently has recorded.
    """
    snapshot_id: str
    agent_id: str
    avg_drift: float
    dominant_axis: DriftAxis
    regime: DriftRegime
    boundary_state: BoundaryState
    shift_count: int
    timestamp: str
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_drift": self.avg_drift,
            "dominant_axis": _enum_value(DriftAxis, self.dominant_axis),
            "regime": _enum_value(DriftRegime, self.regime),
            "boundary_state": _enum_value(BoundaryState, self.boundary_state),
            "shift_count": self.shift_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class AnchoringPlan:
    """A plan to reduce or direct drift.

    ``strategy`` is the ``AnchoringStrategy`` chosen. ``target_drift``
    in [0, 1] is the magnitude the plan aims to reach. ``rationale``
    explains why this strategy was chosen for this regime. Plans are
    forward-looking interventions, so they do not change the agent's
    measured drift.
    """
    plan_id: str
    agent_id: str
    strategy: AnchoringStrategy
    target_drift: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(AnchoringStrategy, self.strategy),
            "target_drift": self.target_drift,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class CalibrationRecord:
    """One expected-vs-observed drift comparison.

    ``expected_drift`` in [0, 1] is what the agent's drift model
    predicted; ``observed_drift`` in [0, 1] is what the agent
    actually measured. ``correction`` is the signed difference
    (observed minus expected) the agent should apply to its drift
    model. ``notes`` is optional free-form context.
    """
    calibration_id: str
    agent_id: str
    axis: DriftAxis
    expected_drift: float       # 0..1
    observed_drift: float       # 0..1
    correction: float           # -1..1
    timestamp: str
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this calibration to a plain dict, expanding enums via ``.value``."""
        return {
            "calibration_id": self.calibration_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(DriftAxis, self.axis),
            "expected_drift": self.expected_drift,
            "observed_drift": self.observed_drift,
            "correction": self.correction,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class DriftProfile:
    """Per-agent aggregate drift tendencies.

    ``avg_drift`` is the mean magnitude across the agent's readings
    (0.0 if none). ``dominant_axis`` is the axis with the highest
    mean magnitude, or SEMANTIC if none. ``regime`` is derived via
    ``_determine_regime``. ``total_readings``, ``total_shifts``, and
    ``total_calibrations`` count the records held for the agent.
    """
    agent_id: str
    avg_drift: float = 0.0
    dominant_axis: DriftAxis = DriftAxis.SEMANTIC
    regime: DriftRegime = DriftRegime.ANCHORED
    total_readings: int = 0
    total_shifts: int = 0
    total_calibrations: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_drift": self.avg_drift,
            "dominant_axis": _enum_value(DriftAxis, self.dominant_axis),
            "regime": _enum_value(DriftRegime, self.regime),
            "total_readings": self.total_readings,
            "total_shifts": self.total_shifts,
            "total_calibrations": self.total_calibrations,
            "last_updated": self.last_updated,
        }


@dataclass
class DriftStats:
    """Engine-wide aggregate statistics across all agents and drifts.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_drift`` is the mean magnitude across all readings, or
    0.0 when none exist. ``dominant_regime`` is the most frequent
    regime across all snapshots, or ANCHORED when none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_shifts: int = 0
    total_snapshots: int = 0
    total_calibrations: int = 0
    avg_drift: float = 0.0
    dominant_regime: DriftRegime = DriftRegime.ANCHORED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_shifts": self.total_shifts,
            "total_snapshots": self.total_snapshots,
            "total_calibrations": self.total_calibrations,
            "avg_drift": self.avg_drift,
            "dominant_regime": _enum_value(DriftRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveDrift:
    """Thread-safe engine that models an agent's cognitive drift.

    The engine holds six stores: ``_readings`` (DriftReading lists
    keyed by agent_id), ``_shifts`` (BoundaryShift lists keyed by
    agent_id), ``_snapshots`` (DriftSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of AnchoringPlan),
    ``_calibrations`` (CalibrationRecord lists keyed by agent_id),
    and ``_profiles`` (DriftProfile by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The drift model is deliberately heuristic: drift magnitudes,
    directions, and boundary states are caller-supplied readings;
    regimes are banded from aggregate activity; dominant axes and
    boundary states are computed by mode. These heuristics are
    transparent and auditable rather than learned, which keeps the
    engine deterministic.

    The engine is intentionally agnostic about how drift is measured
    and how boundary shifts are detected — callers may derive them
    from any source. The engine's job is to record, aggregate,
    classify, and profile, not to detect drift itself. Profiles are
    cached per agent and invalidated whenever the agent's readings,
    shifts, snapshots, or calibrations change, so ``get_profile``
    always reflects the current state unless an explicit override has
    been applied via ``update_profile``.
    """

    def __init__(self) -> None:
        """Initialize an empty drift engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[DriftReading]] = {}
        self._shifts: Dict[str, List[BoundaryShift]] = {}
        self._snapshots: Dict[str, List[DriftSnapshot]] = {}
        self._plans: List[AnchoringPlan] = []
        self._calibrations: Dict[str, List[CalibrationRecord]] = {}
        self._profiles: Dict[str, DriftProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_drift_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._shifts.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._calibrations.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[DriftReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_shifts_locked(self, agent_id: str) -> List[BoundaryShift]:
        """Return one agent's boundary shifts in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _agent_calibrations_locked(self, agent_id: str) -> List[CalibrationRecord]:
        """Return one agent's calibration records in insertion order. Caller holds the lock."""
        return list(self._calibrations.get(agent_id, []))

    def _current_drift_locked(self, agent_id: str) -> float:
        """Return the mean drift magnitude across the agent's readings.

        Returns 0.0 when the agent has no readings. Caller holds the
        lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        return sum(r.drift_magnitude for r in readings) / len(readings)

    def _mode_axis_locked(self, readings: List[DriftReading]) -> DriftAxis:
        """Return the axis with the highest mean magnitude.

        Ties are broken by insertion order. Returns SEMANTIC if the
        list is empty, since SEMANTIC is the canonical default axis.
        Caller holds the lock.
        """
        if not readings:
            return DriftAxis.SEMANTIC
        sums: Dict[DriftAxis, float] = {}
        counts: Dict[DriftAxis, int] = {}
        for reading in readings:
            sums[reading.axis] = sums.get(reading.axis, 0.0) + reading.drift_magnitude
            counts[reading.axis] = counts.get(reading.axis, 0) + 1
        means = {axis: sums[axis] / counts[axis] for axis in sums}
        return max(means.items(), key=lambda kv: kv[1])[0]

    def _mode_boundary_locked(self, readings: List[DriftReading]) -> BoundaryState:
        """Return the most frequent boundary state across the readings.

        Ties are broken by insertion order. Returns FIRM if the list
        is empty, since FIRM is the balanced default state. Caller
        holds the lock.
        """
        if not readings:
            return BoundaryState.FIRM
        counts: Dict[BoundaryState, int] = {}
        for reading in readings:
            counts[reading.boundary_state] = counts.get(reading.boundary_state, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    # ── Drift Readings ────────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        drift_magnitude: float,
        direction: float,
        boundary_state: Any,
        signature: Any,
        notes: Optional[str] = None,
    ) -> DriftReading:
        """Record a drift reading for an agent and return it.

        ``axis`` may be passed as a ``DriftAxis`` member or its string
        name/value. ``boundary_state`` may be passed as a
        ``BoundaryState`` member or its string name/value.
        ``signature`` may be passed as a ``DriftSignature`` member or
        its string name/value. ``drift_magnitude`` is clamped to
        [0, 1]; ``direction`` is clamped to [-1, 1]. The reading is
        stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = DriftReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(DriftAxis, axis),
                drift_magnitude=_clamp(drift_magnitude, 0.0, 1.0),
                direction=_clamp(direction, -1.0, 1.0),
                boundary_state=_resolve_enum(BoundaryState, boundary_state),
                signature=_resolve_enum(DriftSignature, signature),
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
    ) -> List[DriftReading]:
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

    def get_reading(self, reading_id: str) -> DriftReading:
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

    # ── Boundary Shifts ───────────────────────────────────────────

    def record_shift(
        self,
        agent_id: str,
        axis: Any,
        from_boundary: Any,
        to_boundary: Any,
        magnitude: float,
        cause: str,
        notes: Optional[str] = None,
    ) -> BoundaryShift:
        """Record a boundary shift for an agent and return it.

        ``axis`` may be passed as a ``DriftAxis`` member or its string
        name/value. ``from_boundary`` and ``to_boundary`` may each be
        passed as a ``BoundaryState`` member or its string name/value.
        ``magnitude`` is clamped to [0, 1]. The shift is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            shift = BoundaryShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(DriftAxis, axis),
                from_boundary=_resolve_enum(BoundaryState, from_boundary),
                to_boundary=_resolve_enum(BoundaryState, to_boundary),
                magnitude=_clamp(magnitude, 0.0, 1.0),
                cause=str(cause),
                timestamp=_now(),
                notes=notes,
            )
            self._shifts.setdefault(agent_id, []).append(shift)
            self._profiles.pop(agent_id, None)
            return shift

    def list_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BoundaryShift]:
        """Return boundary shifts, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all shifts are considered;
        otherwise only shifts for that agent are returned. The most
        recently recorded ``limit`` shifts are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
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

    def get_shift(self, shift_id: str) -> BoundaryShift:
        """Retrieve a boundary shift by id.

        Raises ``ValueError`` if no shift exists with that id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for shift in agent_shifts:
                    if shift.shift_id == shift_id:
                        return shift
        raise ValueError(f"shift {shift_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> DriftSnapshot:
        """Aggregate an agent's recent drift into a snapshot.

        ``avg_drift`` is the mean magnitude across the agent's
        readings, or 0.0 if none. ``regime`` is derived via
        ``_determine_regime``. ``dominant_axis`` is the axis with the
        highest mean magnitude, or SEMANTIC if none.
        ``boundary_state`` is the most frequent boundary state across
        the agent's readings, or FIRM if none. ``shift_count`` is the
        number of boundary shifts the agent currently has recorded.
        The snapshot is stored and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            avg_drift = self._current_drift_locked(agent_id)
            regime = _determine_regime(avg_drift)
            readings = self._agent_readings_locked(agent_id)
            dominant_axis = self._mode_axis_locked(readings)
            boundary_state = self._mode_boundary_locked(readings)
            agent_shifts = self._agent_shifts_locked(agent_id)
            snapshot = DriftSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_drift=round(avg_drift, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                boundary_state=boundary_state,
                shift_count=len(agent_shifts),
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DriftSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The most
        recently taken ``limit`` snapshots are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
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

    def get_snapshot(self, snapshot_id: str) -> DriftSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Anchoring Plans ───────────────────────────────────────────

    def plan_anchoring(
        self,
        agent_id: str,
        strategy: Any,
        target_drift: float,
        rationale: str,
    ) -> AnchoringPlan:
        """Record an anchoring plan for an agent and return it.

        ``strategy`` may be passed as an ``AnchoringStrategy`` member
        or its string name/value. ``target_drift`` is clamped to
        [0, 1]. The plan is stored in a flat list (not keyed by
        agent, since plans are forward-looking interventions rather
        than measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured drift.
        """
        with self._lock:
            plan = AnchoringPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(AnchoringStrategy, strategy),
                target_drift=_clamp(target_drift, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AnchoringPlan]:
        """Return anchoring plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered;
        otherwise only plans for that agent are returned. The most
        recently recorded ``limit`` plans are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            plans = list(self._plans)
        if agent_id is not None:
            plans = [p for p in plans if p.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> AnchoringPlan:
        """Retrieve an anchoring plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Calibration Records ───────────────────────────────────────

    def record_calibration(
        self,
        agent_id: str,
        axis: Any,
        expected_drift: float,
        observed_drift: float,
        correction: float,
        notes: Optional[str] = None,
    ) -> CalibrationRecord:
        """Record a calibration for an agent and return it.

        ``axis`` may be passed as a ``DriftAxis`` member or its string
        name/value. ``expected_drift`` and ``observed_drift`` are
        clamped to [0, 1]; ``correction`` is clamped to [-1, 1]. The
        record is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = CalibrationRecord(
                calibration_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(DriftAxis, axis),
                expected_drift=_clamp(expected_drift, 0.0, 1.0),
                observed_drift=_clamp(observed_drift, 0.0, 1.0),
                correction=_clamp(correction, -1.0, 1.0),
                timestamp=_now(),
                notes=notes,
            )
            self._calibrations.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_calibrations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CalibrationRecord]:
        """Return calibration records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all records are considered;
        otherwise only records for that agent are returned. The most
        recently recorded ``limit`` records are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                records = self._agent_calibrations_locked(agent_id)
            else:
                records = []
                for agent_records in self._calibrations.values():
                    records.extend(agent_records)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return records[-n:] if n else []

    def get_calibration(self, calibration_id: str) -> CalibrationRecord:
        """Retrieve a calibration record by id.

        Raises ``ValueError`` if no record exists with that id.
        """
        with self._lock:
            for agent_records in self._calibrations.values():
                for record in agent_records:
                    if record.calibration_id == calibration_id:
                        return record
        raise ValueError(f"calibration {calibration_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> DriftProfile:
        """Return the agent's drift profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, shifts, snapshots, or
        calibrations change. If the agent has data but no profile
        yet, the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``DriftProfile`` and
        ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> DriftProfile:
        """Refresh and optionally override fields of an agent's drift profile.

        The profile is first recomputed from the live stores, then any
        supplied keyword overrides (matching ``DriftProfile`` field
        names) are applied, and ``last_updated`` is stamped. Accepted
        overrides: ``avg_drift`` (float), ``dominant_axis``
        (``DriftAxis``), ``regime`` (``DriftRegime``),
        ``total_readings``, ``total_shifts``, and ``total_calibrations``
        (int). Enum-valued overrides may be passed as the enum member
        or its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_drift":
                    try:
                        profile.avg_drift = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(DriftAxis, value)
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(DriftRegime, value)
                    except ValueError:
                        pass
                elif key in ("total_readings", "total_shifts", "total_calibrations"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[DriftProfile]:
        """Return all stored drift profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> DriftStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, shifts, snapshots, and calibrations.
        Scalar totals are the counts of each record type.
        ``avg_drift`` is the mean magnitude across all readings, or
        0.0 when none exist. ``dominant_regime`` is the most frequent
        regime across all snapshots, or ANCHORED when none exist. If
        snapshots do not exist but readings do, the regime is derived
        from the average reading magnitude so the stats reflect real
        state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._shifts.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._calibrations.keys())

            total_readings = 0
            magnitude_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    magnitude_sum += reading.drift_magnitude
            avg_drift = (
                round(magnitude_sum / total_readings, 4) if total_readings else 0.0
            )

            total_shifts = sum(
                len(agent_shifts) for agent_shifts in self._shifts.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_calibrations = sum(
                len(agent_records)
                for agent_records in self._calibrations.values()
            )

            regime_counts: Dict[DriftRegime, int] = {}
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    regime_counts[snapshot.regime] = (
                        regime_counts.get(snapshot.regime, 0) + 1
                    )
            if regime_counts:
                dominant_regime = max(
                    regime_counts.items(), key=lambda kv: kv[1]
                )[0]
            elif total_readings:
                # No snapshots yet, but readings exist: derive the
                # regime from the average drift so the stats reflect
                # real state.
                dominant_regime = _determine_regime(avg_drift)
            else:
                dominant_regime = DriftRegime.ANCHORED

            return DriftStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_shifts=total_shifts,
                total_snapshots=total_snapshots,
                total_calibrations=total_calibrations,
                avg_drift=avg_drift,
                dominant_regime=dominant_regime,
            )

    # ── Internal profile computation (caller must hold the lock) ────

    def _compute_profile_locked(self, agent_id: str) -> DriftProfile:
        """Aggregate an agent's readings, shifts, and calibrations into a profile.

        See ``DriftProfile`` for field semantics. ``avg_drift`` is the
        mean magnitude across the agent's readings (0.0 if none).
        ``dominant_axis`` is the axis with the highest mean magnitude,
        or SEMANTIC if none. ``regime`` is derived via
        ``_determine_regime``. ``total_readings``, ``total_shifts``,
        and ``total_calibrations`` count the records held for the
        agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)
        calibrations = self._agent_calibrations_locked(agent_id)

        avg_drift = self._current_drift_locked(agent_id)
        regime = _determine_regime(avg_drift)
        dominant_axis = self._mode_axis_locked(readings)

        return DriftProfile(
            agent_id=agent_id,
            avg_drift=round(avg_drift, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=len(readings),
            total_shifts=len(shifts),
            total_calibrations=len(calibrations),
            last_updated=_now(),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveDrift] = None
_engine_lock = threading.Lock()


def get_drift_engine() -> AgentCognitiveDrift:
    """Get or create the singleton ``AgentCognitiveDrift`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveDrift()
        return _engine


def reset_drift_engine() -> None:
    """Reset the singleton ``AgentCognitiveDrift`` instance.

    Drops the reference to the current engine so the next
    ``get_drift_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
