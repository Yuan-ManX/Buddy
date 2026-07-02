from __future__ import annotations

"""Agent Cognitive Compass Engine — directional orientation of thought

How an agent orients, drifts, and aligns its thinking toward a true bearing.
A calibrated agent holds a steady heading toward its target; a lost agent's
thoughts wander every which way. Distinct from magnetism, polarization,
coherence, tension, equilibrium, and affinity.
Core capabilities: axis tracking, orientation sources, navigation, calibration.

Architecture:
  AgentCognitiveCompass (singleton)
  ├── CompassReading      (one observation of orientation on one axis)
  ├── CorrectionRecord    (one correction event that changed orientation)
  ├── CompassSnapshot     (aggregate orientation state for one agent)
  ├── CompassPlan         (a plan to correct the heading with a strategy)
  ├── BearingShift        (one stage transition in the calibration lifecycle)
  ├── CompassProfile      (per-agent aggregate orientation tendencies)
  └── CompassStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/correction/etc.

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
    engine with a ``NaN`` or ``None`` compass score. A low-side default is
    safer than a mid-range one for compass-like quantities where a
    spurious high reading would inflate the perceived orientation and
    push the agent's regime toward TRUE.
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
    real calibration intervals and correction magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    correction may apply a large effective magnitude.
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
    against member values (e.g. ``"bearing"``) and then against
    member names (e.g. ``"BEARING"``), so callers may pass either
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


def _determine_regime(avg_compass: float) -> "CompassRegime":
    """Classify a compass regime from the average compass score.

    The average compass is clamped to [0, 1] where higher means a
    more oriented, calibrated posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is LOST
    (no sense of direction, no alignment); below 0.35 it is
    DRIFTING (wandering without a steady heading); below 0.55 it is
    ORIENTING (beginning to find direction); below 0.75 it is ALIGNED
    (holding a steady heading); below 0.9 it is CALIBRATED
    (well-calibrated and aligned); otherwise it is TRUE (perfectly
    oriented to true north).
    """
    avg = _clamp(avg_compass, 0.0, 1.0)
    if avg < 0.15:
        return CompassRegime.LOST
    if avg < 0.35:
        return CompassRegime.DRIFTING
    if avg < 0.55:
        return CompassRegime.ORIENTING
    if avg < 0.75:
        return CompassRegime.ALIGNED
    if avg < 0.9:
        return CompassRegime.CALIBRATED
    return CompassRegime.TRUE


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CompassAxis(str, Enum):
    """The axis along which a compass reading is taken.

    Each axis names a different dimension of the agent's cognitive
    orientation whose alignment can be measured. BEARING is the angle
    from true north to the current direction. HEADING is the direction
    the agent is actually moving. DECLINATION is the offset between
    true and magnetic north. TILT is how far the compass is from
    level. DRIFT is how much the heading wanders over time.
    CALIBRATION is how well the compass is calibrated.
    """
    BEARING = "bearing"          # angle from true north
    HEADING = "heading"          # direction of actual movement
    DECLINATION = "declination"  # offset between true and magnetic north
    TILT = "tilt"                # deviation from level
    DRIFT = "drift"              # heading wander over time
    CALIBRATION = "calibration"  # how well calibrated


class CompassRegime(str, Enum):
    """The regime an agent's compass occupies, classified by orientation.

    Ranges from LOST (no sense of direction, no alignment)
    through DRIFTING (wandering without a steady heading), ORIENTING
    (beginning to find direction), ALIGNED (holding a steady
    heading), and CALIBRATED (well-calibrated and aligned) to TRUE
    (perfectly oriented to true north). The regime is derived from the
    average compass across the agent's readings via
    ``_determine_regime``.
    """
    LOST = "lost"              # no sense of direction
    DRIFTING = "drifting"      # wandering without steady heading
    ORIENTING = "orienting"    # beginning to find direction
    ALIGNED = "aligned"        # holding a steady heading
    CALIBRATED = "calibrated"  # well-calibrated and aligned
    TRUE = "true"              # perfectly oriented to true north


class CompassSource(str, Enum):
    """A source that supplies the orientation reference.

    Each source names a different origin of the directional reference
    the agent orients against. LANDMARK orients from visible landmarks.
    MAGNETIC orients from the magnetic field. INERTIAL orients from
    dead reckoning. SOLAR orients from the sun's position. MAP orients
    from a map. INTUITION orients from the gut feeling. A compass
    reading records which source supplies the reference on the measured
    axis, and a correction record records which source drove a
    change.
    """
    LANDMARK = "landmark"  # orientation from visible landmarks
    MAGNETIC = "magnetic"  # orientation from magnetic field
    INERTIAL = "inertial"  # orientation from dead reckoning
    SOLAR = "solar"        # orientation from sun position
    MAP = "map"            # orientation from a map
    INTUITION = "intuition"  # orientation from gut feeling


class CompassStrategy(str, Enum):
    """Strategy for correcting the heading deliberately.

    ORIENT finds a direction. RECENTER returns to center. CALIBRATE
    calibrates the compass. COMPENSATE compensates for declination or
    tilt. NAVIGATE navigates toward a target. ANCHOR anchors to a
    fixed bearing. Each strategy is suited to a different orientation
    condition, from counteracting a wandering heading to locking in a
    true-north bearing.
    """
    ORIENT = "orient"        # find a direction
    RECENTER = "recenter"    # return to center
    CALIBRATE = "calibrate"  # calibrate the compass
    COMPENSATE = "compensate"  # compensate for declination/tilt
    NAVIGATE = "navigate"    # navigate toward a target
    ANCHOR = "anchor"        # anchor to a fixed bearing


class CompassStage(str, Enum):
    """The lifecycle stage of an agent's orientation process.

    DISORIENTED is the state of no sense of direction. SEARCHING is
    the phase of looking for orientation. ORIENTING is the state of
    beginning to orient. ALIGNED is the state in which the heading
    holds steady. CALIBRATED is the state of being well-calibrated.
    TRUE_NORTH is the final state at which the agent is perfectly
    oriented to true north and unresponsive to drift. The engine
    records transitions between stages as BearingShift entries.
    """
    DISORIENTED = "disoriented"  # no sense of direction
    SEARCHING = "searching"      # looking for orientation
    ORIENTING = "orienting"      # beginning to orient
    ALIGNED = "aligned"          # heading holds steady
    CALIBRATED = "calibrated"    # well-calibrated
    TRUE_NORTH = "true_north"    # perfectly oriented to true north


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CompassReading:
    """One observation of orientation on a particular axis.

    ``axis`` is the ``CompassAxis`` the reading is taken on.
    ``compass_score`` in [0, 1] measures how oriented the agent is
    on that axis — 0 means fully disoriented, 1 means perfectly
    oriented to true north. ``source`` is the ``CompassSource``
    supplying the reference. ``intensity`` in [0, 1] measures how
    emphatic the observation was. ``notes`` is an optional free-form
    annotation.
    """
    reading_id: str
    agent_id: str
    axis: CompassAxis
    compass_score: float    # 0..1, higher = more oriented
    source: CompassSource
    intensity: float        # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CompassAxis, self.axis),
            "compass_score": self.compass_score,
            "source": _enum_value(CompassSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CorrectionRecord:
    """One correction event that changed the orientation on an axis.

    ``axis`` is the ``CompassAxis`` on which the correction occurred.
    ``source`` is the ``CompassSource`` that drove the change.
    ``before_score`` in [0, 1] is the orientation before the event;
    ``after_score`` in [0, 1] is the orientation after.
    ``correction_magnitude`` in [0, ∞) measures how strong the
    correction was. ``notes`` is an optional free-form annotation.
    """
    correction_id: str
    agent_id: str
    axis: CompassAxis
    source: CompassSource
    before_score: float            # 0..1, orientation before correction
    after_score: float             # 0..1, orientation after correction
    correction_magnitude: float    # 0..inf, strength of correction
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this correction record to a plain dict, expanding enums via ``.value``."""
        return {
            "correction_id": self.correction_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CompassAxis, self.axis),
            "source": _enum_value(CompassSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "correction_magnitude": self.correction_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CompassSnapshot:
    """Aggregate orientation state for one agent at one moment.

    ``avg_compass`` in [0, 1] is the mean compass score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``CompassAxis`` among those readings, or
    BEARING if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_compass``. ``correction_count``
    is the number of correction events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_compass: float
    dominant_axis: CompassAxis
    regime: CompassRegime
    correction_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Includes both ``dominant_regime`` and ``regime`` keys (same value)
        so callers may consume whichever naming convention they prefer:
        ``dominant_regime`` for parity with profile/stats, ``regime`` for
        parity with the snapshot's own field name.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_compass": self.avg_compass,
            "dominant_axis": _enum_value(CompassAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CompassRegime, self.regime),
            "regime": _enum_value(CompassRegime, self.regime),
            "correction_count": self.correction_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CompassPlan:
    """A plan to correct the heading with a strategy.

    ``strategy`` is the ``CompassStrategy`` chosen.
    ``target_compass`` in [0, 1] is the orientation the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's orientation condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current orientation — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: CompassStrategy
    target_compass: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(CompassStrategy, self.strategy),
            "target_compass": self.target_compass,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class BearingShift:
    """One record of a stage transition in the calibration lifecycle.

    ``from_stage`` is the ``CompassStage`` the agent was in before
    the transition. ``to_stage`` is the ``CompassStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow orient",
    "sudden calibration", "deliberate anchoring").
    """
    shift_id: str
    agent_id: str
    from_stage: CompassStage
    to_stage: CompassStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this bearing shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(CompassStage, self.from_stage),
            "to_stage": _enum_value(CompassStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class CompassProfile:
    """Per-agent aggregate orientation tendencies.

    ``avg_compass`` in [0, 1] is the mean compass score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``CompassAxis`` among the agent's readings, or
    BEARING if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_compass``. ``total_readings``,
    ``total_corrections``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_compass: float = 0.0
    dominant_axis: CompassAxis = CompassAxis.BEARING
    dominant_regime: CompassRegime = CompassRegime.ORIENTING
    total_readings: int = 0
    total_corrections: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_compass": self.avg_compass,
            "dominant_axis": _enum_value(CompassAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CompassRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_corrections": self.total_corrections,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class CompassStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_compass`` is the mean compass score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or ORIENTING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_corrections: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_compass: float = 0.0
    dominant_regime: CompassRegime = CompassRegime.ORIENTING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_corrections": self.total_corrections,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_compass": self.avg_compass,
            "dominant_regime": _enum_value(CompassRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCompass:
    """Thread-safe engine that models an agent's cognitive compass.

    The engine holds six stores: ``_readings`` (CompassReading lists
    keyed by agent_id), ``_corrections`` (CorrectionRecord lists keyed
    by agent_id), ``_snapshots`` (CompassSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of CompassPlan),
    ``_shifts`` (BearingShift lists keyed by agent_id), and
    ``_profiles`` (CompassProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The compass model is deliberately heuristic: compass scores
    and intensities are caller-supplied observations; compass
    regimes are banded from the average compass; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how orientation is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure orientation itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, corrections, snapshots, or shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``. Plans
    do not invalidate the profile cache, since a plan is a
    forward-looking intervention that does not change the agent's
    measured orientation.
    """

    # Number of most-recent readings whose compass scores feed into
    # a snapshot's average compass. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current orientation posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty compass engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[CompassReading]] = {}
        self._corrections: Dict[str, List[CorrectionRecord]] = {}
        self._snapshots: Dict[str, List[CompassSnapshot]] = {}
        self._plans: List[CompassPlan] = []
        self._shifts: Dict[str, List[BearingShift]] = {}
        self._profiles: Dict[str, CompassProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_compass_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._corrections.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[CompassReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_corrections_locked(
        self, agent_id: str
    ) -> List[CorrectionRecord]:
        """Return one agent's correction records in insertion order. Caller holds the lock."""
        return list(self._corrections.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[CompassSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[CompassPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[BearingShift]:
        """Return one agent's bearing shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[CompassReading]
    ) -> CompassAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns BEARING if the list is
        empty, since BEARING is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return CompassAxis.BEARING
        counts: Counter = Counter()
        first_seen_order: Dict[CompassAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: CompassAxis = readings[0].axis
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
        self, profiles: List[CompassProfile]
    ) -> CompassRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns ORIENTING if the list is empty, since
        ORIENTING is the default regime — the band that
        represents a normally functioning cognitive compass that
        is beginning to find direction, neither lost nor
        perfectly aligned to true north. Caller holds the lock.
        """
        if not profiles:
            return CompassRegime.ORIENTING
        counts: Dict[CompassRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> CompassProfile:
        """Aggregate an agent's readings, corrections, and shifts into a profile.

        See ``CompassProfile`` for field semantics. ``avg_compass``
        is the mean compass score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``CompassAxis`` among the agent's readings, or BEARING
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_compass``.
        ``total_readings``, ``total_corrections``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        corrections = self._agent_corrections_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_compass = sum(
                r.compass_score for r in readings
            ) / len(readings)
        else:
            avg_compass = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_compass)

        return CompassProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_compass=round(avg_compass, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_corrections=len(corrections),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Compass Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        compass_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> CompassReading:
        """Record a compass reading for an agent and return it.

        ``axis`` may be passed as a ``CompassAxis`` member or its
        string name/value. ``compass_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``CompassSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = CompassReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CompassAxis, axis),
                compass_score=_clamp(compass_score, 0.0, 1.0),
                source=_resolve_enum(CompassSource, source),
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
    ) -> List[CompassReading]:
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

    def get_reading(self, reading_id: str) -> CompassReading:
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

    # ── Correction Records ────────────────────────────────────────

    def record_correction(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        correction_magnitude: float,
        notes: Optional[str] = None,
    ) -> CorrectionRecord:
        """Record a correction event for an agent and return it.

        ``axis`` may be passed as a ``CompassAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``CompassSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``correction_magnitude`` is clamped to [0, ∞). The correction
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = CorrectionRecord(
                correction_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CompassAxis, axis),
                source=_resolve_enum(CompassSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                correction_magnitude=_clamp_positive_ms(
                    correction_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._corrections.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_corrections(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CorrectionRecord]:
        """Return correction records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all corrections are considered;
        otherwise only corrections for that agent are returned. The
        most recently recorded ``limit`` corrections are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                corrections = self._agent_corrections_locked(agent_id)
            else:
                corrections = []
                for agent_corrections in self._corrections.values():
                    corrections.extend(agent_corrections)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return corrections[-n:] if n else []

    def get_correction(self, correction_id: str) -> CorrectionRecord:
        """Retrieve a correction record by id.

        Raises ``ValueError`` if no correction exists with that id.
        """
        with self._lock:
            for agent_corrections in self._corrections.values():
                for correction in agent_corrections:
                    if correction.correction_id == correction_id:
                        return correction
        raise ValueError(f"correction {correction_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CompassSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_compass`` is the mean compass score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``CompassAxis`` among
        those readings, or BEARING if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_compass``.
        ``correction_count`` is the number of correction events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_compass = sum(
                    r.compass_score for r in recent
                ) / len(recent)
            else:
                avg_compass = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_compass)
            correction_count = len(
                self._agent_corrections_locked(agent_id)
            )

            snapshot = CompassSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_compass=round(avg_compass, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                correction_count=correction_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CompassSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> CompassSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Correction Plans ────────────────────────────────────────────

    def plan_correction(
        self,
        agent_id: str,
        strategy: Any,
        target_compass: float,
        rationale: str,
    ) -> CompassPlan:
        """Record a correction plan for an agent and return it.

        ``strategy`` may be passed as a ``CompassStrategy`` member
        or its string name/value. ``target_compass`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured orientation.
        """
        with self._lock:
            plan = CompassPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(CompassStrategy, strategy),
                target_compass=_clamp(target_compass, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CompassPlan]:
        """Return correction plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> CompassPlan:
        """Retrieve a correction plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Bearing Shift Records ────────────────────────────────────────

    def record_bearing_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> BearingShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``CompassStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        orient", "sudden calibration", "deliberate anchoring"). The
        bearing shift record is stored and returned; the agent's cached
        profile is invalidated.

        Bearing shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = BearingShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(CompassStage, from_stage),
                to_stage=_resolve_enum(CompassStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_bearing_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BearingShift]:
        """Return bearing shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all bearing shifts are considered;
        otherwise only bearing shifts for that agent are returned. The
        most recently recorded ``limit`` bearing shift records are
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

    def get_bearing_shift(self, shift_id: str) -> BearingShift:
        """Retrieve a bearing shift record by id.

        Raises ``ValueError`` if no bearing shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"bearing shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CompassProfile:
        """Return the agent's compass profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, corrections, snapshots, or
        shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``CompassProfile``
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
    ) -> CompassProfile:
        """Refresh and optionally override fields of an agent's compass profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``CompassProfile`` field names) are applied. Accepted
        overrides: ``avg_compass`` (float), ``dominant_axis``
        (``CompassAxis``), ``dominant_regime``
        (``CompassRegime``), ``total_readings``,
        ``total_corrections``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_compass":
                    try:
                        profile.avg_compass = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            CompassAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            CompassRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_corrections",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CompassProfile]:
        """Return all stored compass profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> CompassStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, corrections, snapshots, and shifts.
        Scalar totals are the counts of each record type.
        ``avg_compass`` is the mean compass score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        ORIENTING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        compass via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._corrections.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            compass_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    compass_sum += reading.compass_score
            avg_compass = (
                round(compass_sum / total_readings, 4) if total_readings else 0.0
            )

            total_corrections = sum(
                len(agent_corrections)
                for agent_corrections in self._corrections.values()
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
                # the regime from the average compass so the stats
                # reflect real state rather than the default
                # ORIENTING.
                dominant_regime = _determine_regime(avg_compass)
            else:
                dominant_regime = CompassRegime.ORIENTING

            return CompassStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_corrections=total_corrections,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_compass=avg_compass,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCompass] = None
_engine_lock = threading.Lock()


def get_compass_engine() -> AgentCognitiveCompass:
    """Get or create the singleton ``AgentCognitiveCompass`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveCompass()
    return _engine


def reset_compass_engine() -> None:
    """Reset the singleton ``AgentCognitiveCompass`` instance.

    Drops the reference to the current engine so the next
    ``get_compass_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
