from __future__ import annotations

"""Agent Cognitive Storm Engine — modeling fronts and pressures between concepts

How concepts gather, charge, and discharge across the cognitive atmosphere.
A stormy agent holds concepts in turbulent flux; a calm agent's concepts drift
in stable formation. Distinct from polarization, coherence, tension,
equilibrium, and affinity.
Core capabilities: axis tracking, energy sources, storm strategies, front stages.

Architecture:
  AgentCognitiveStorm (singleton)
  ├── StormReading      (one observation of storm on one axis)
  ├── SurgeRecord       (one surge event that changed storm)
  ├── StormSnapshot     (aggregate storm state for one agent)
  ├── StormPlan         (a plan to shape the storm with a strategy)
  ├── FrontShift        (one stage transition in the front lifecycle)
  ├── StormProfile      (per-agent aggregate storm tendencies)
  └── StormStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/surge/etc.

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
    engine with a ``NaN`` or ``None`` storm. A low-side default is
    safer than a mid-range one for storm-like quantities where a
    spurious high reading would inflate the perceived storm and
    push the agent's regime toward CLEARING.
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
    real front shift intervals and surge magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate buildup
    may apply a large effective surge.
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
    against member values (e.g. ``"vorticity"``) and then against
    member names (e.g. ``"VORTICITY"``), so callers may pass either
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


def _determine_regime(avg_storm: float) -> "StormRegime":
    """Classify a storm regime from the average storm score.

    The average storm is clamped to [0, 1] where higher means a
    more intense, active storm. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is CLEAR
    (no storm activity, calm cognitive weather); below 0.35 it is
    BREWING (storm beginning to form, early turbulence); below 0.55
    it is GATHERING (storm gathering strength, organized activity);
    below 0.75 it is RAGING (storm at full intensity, chaotic
    flux); below 0.9 it is BREAKING (storm beginning to break,
    intensity waning); otherwise it is CLEARING (storm clearing,
    returning to calm).
    """
    avg = _clamp(avg_storm, 0.0, 1.0)
    if avg < 0.15:
        return StormRegime.CLEAR
    if avg < 0.35:
        return StormRegime.BREWING
    if avg < 0.55:
        return StormRegime.GATHERING
    if avg < 0.75:
        return StormRegime.RAGING
    if avg < 0.9:
        return StormRegime.BREAKING
    return StormRegime.CLEARING


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class StormAxis(str, Enum):
    """The axis along which a storm reading is taken.

    Each axis names a different dimension of the agent's cognitive
    atmosphere whose storm can be measured. FRONT is the boundary
    between storm masses. PRESSURE is the atmospheric pressure
    gradient. CHARGE is the electrical charge buildup. WIND is the
    wind force and direction. CLOUD is the cloud cover and density.
    STORM is the overall storm strength across the agent's concepts.
    """
    FRONT = "front"        # boundary between storm masses
    PRESSURE = "pressure"  # atmospheric pressure gradient
    CHARGE = "charge"      # electrical charge buildup
    WIND = "wind"          # wind force and direction
    CLOUD = "cloud"        # cloud cover and density
    STORM = "storm"        # overall storm strength


class StormRegime(str, Enum):
    """The regime an agent's storm occupies, classified by storm score.

    Ranges from CLEAR (no storm activity, calm cognitive weather)
    through BREWING (storm beginning to form, early turbulence),
    GATHERING (storm gathering strength, organized activity), RAGING
    (storm at full intensity, chaotic flux), and BREAKING (storm
    beginning to break, intensity waning) to CLEARING (storm
    clearing, returning to calm). The regime is derived from the
    average storm across the agent's readings via
    ``_determine_regime``.
    """
    CLEAR = "clear"          # no storm activity
    BREWING = "brewing"      # storm beginning to form
    GATHERING = "gathering"  # storm gathering strength
    RAGING = "raging"        # storm at full intensity
    BREAKING = "breaking"    # storm beginning to break
    CLEARING = "clearing"    # storm clearing


class StormSource(str, Enum):
    """A source that supplies the storm's energy or driving force.

    Each source names a different origin of the storm's power.
    HEAT supplies thermal energy that lifts and destabilizes.
    MOISTURE supplies water vapor that fuels convection.
    VORTICITY supplies rotational force that organizes rotation.
    CORIOLIS supplies the coriolis effect that deflects flow.
    TOPOGRAPHY supplies terrain influence that channels the storm.
    CONVECTION supplies convective uplift that builds vertically.
    A storm reading records which source supplies the force on the
    measured axis, and a surge record records which source drove a
    change.
    """
    HEAT = "heat"                  # thermal energy
    MOISTURE = "moisture"          # water vapor
    VORTICITY = "vorticity"        # rotational force
    CORIOLIS = "coriolis"          # coriolis effect
    TOPOGRAPHY = "topography"      # terrain influence
    CONVECTION = "convection"      # convective uplift


class StormStrategy(str, Enum):
    """Strategy for shaping the storm deliberately.

    BUILD gathers storm energy. CHARGE builds electrical charge.
    DISCHARGE releases stored energy. DISSIPATE weakens the storm.
    ROTATE changes storm direction. PUSH moves the storm front.
    Each strategy is suited to a different storm condition, from
    gathering a scattered atmosphere to releasing a saturated one.
    """
    BUILD = "build"          # gather storm energy
    CHARGE = "charge"        # build electrical charge
    DISCHARGE = "discharge"  # release stored energy
    DISSIPATE = "dissipate"  # weaken the storm
    ROTATE = "rotate"        # change storm direction
    PUSH = "push"            # move the storm front


class StormStage(str, Enum):
    """The lifecycle stage of an agent's storm-formation process.

    CUMULUS is the state of initial cloud formation. DEVELOPING is
    the phase of storm developing. MATURE is the state of a fully
    formed storm. PEAK is the state of maximum intensity.
    DISSIPATING is the state of the storm weakening. CLEAR is the
    final state at which the storm has cleared and the atmosphere
    is calm. The engine records transitions between stages as
    FrontShift entries.
    """
    CUMULUS = "cumulus"          # initial cloud formation
    DEVELOPING = "developing"    # storm developing
    MATURE = "mature"            # fully formed storm
    PEAK = "peak"                # maximum intensity
    DISSIPATING = "dissipating"  # storm weakening
    CLEAR = "clear"              # storm has cleared


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class StormReading:
    """One observation of storm on a particular axis.

    ``axis`` is the ``StormAxis`` the reading is taken on.
    ``storm_score`` in [0, 1] measures how stormy the agent is
    on that axis — 0 means calm, 1 means fully raging.
    ``source`` is the ``StormSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: StormAxis
    storm_score: float    # 0..1, higher = more intense
    source: StormSource
    intensity: float      # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(StormAxis, self.axis),
            "storm_score": self.storm_score,
            "source": _enum_value(StormSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class SurgeRecord:
    """One surge event that changed the storm on an axis.

    ``axis`` is the ``StormAxis`` on which the surge occurred.
    ``source`` is the ``StormSource`` that drove the change.
    ``before_score`` in [0, 1] is the storm before the event;
    ``after_score`` in [0, 1] is the storm after.
    ``surge_magnitude`` in [0, ∞) measures how strong the
    surge was. ``notes`` is an optional free-form annotation.
    """
    surge_id: str
    agent_id: str
    axis: StormAxis
    source: StormSource
    before_score: float       # 0..1, storm before surge
    after_score: float        # 0..1, storm after surge
    surge_magnitude: float    # 0..inf, strength of surge
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this surge record to a plain dict, expanding enums via ``.value``."""
        return {
            "surge_id": self.surge_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(StormAxis, self.axis),
            "source": _enum_value(StormSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "surge_magnitude": self.surge_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class StormSnapshot:
    """Aggregate storm state for one agent at one moment.

    ``avg_storm`` in [0, 1] is the mean storm score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``StormAxis`` among those readings, or FRONT
    if none. ``dominant_regime`` and ``regime`` are both derived via
    ``_determine_regime`` from ``avg_storm`` and carry the same
    value; both keys are present in ``to_dict`` so callers using
    either name find the regime. ``surge_count`` is the number of
    surge events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_storm: float
    dominant_axis: StormAxis
    dominant_regime: StormRegime
    regime: StormRegime
    surge_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_storm": self.avg_storm,
            "dominant_axis": _enum_value(StormAxis, self.dominant_axis),
            "dominant_regime": _enum_value(StormRegime, self.dominant_regime),
            "regime": _enum_value(StormRegime, self.regime),
            "surge_count": self.surge_count,
            "timestamp": self.timestamp,
        }


@dataclass
class StormPlan:
    """A plan to shape the storm with a strategy.

    ``strategy`` is the ``StormStrategy`` chosen.
    ``target_storm`` in [0, 1] is the storm the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's storm condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current storm — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: StormStrategy
    target_storm: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(StormStrategy, self.strategy),
            "target_storm": self.target_storm,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class FrontShift:
    """One record of a stage transition in the front lifecycle.

    ``from_stage`` is the ``StormStage`` the agent was in before
    the transition. ``to_stage`` is the ``StormStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow gather",
    "sudden peak", "deliberate buildup").
    """
    shift_id: str
    agent_id: str
    from_stage: StormStage
    to_stage: StormStage
    interval_ms: int
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this front shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(StormStage, self.from_stage),
            "to_stage": _enum_value(StormStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class StormProfile:
    """Per-agent aggregate storm tendencies.

    ``avg_storm`` in [0, 1] is the mean storm score across the
    agent's readings (0.0 if none). ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_storm``. ``total_readings``,
    ``total_surges``, ``total_snapshots``, and ``total_shifts`` are
    the counts of each record type for the agent. ``updated_at`` is
    the timestamp at which the profile was last computed or
    overridden.
    """
    agent_id: str
    dominant_regime: StormRegime = StormRegime.GATHERING
    avg_storm: float = 0.0
    total_readings: int = 0
    total_surges: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "dominant_regime": _enum_value(StormRegime, self.dominant_regime),
            "avg_storm": self.avg_storm,
            "total_readings": self.total_readings,
            "total_surges": self.total_surges,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class StormStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_storm`` is the mean storm score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or GATHERING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_surges: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_storm: float = 0.0
    dominant_regime: StormRegime = StormRegime.GATHERING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_surges": self.total_surges,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_storm": self.avg_storm,
            "dominant_regime": _enum_value(StormRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveStorm:
    """Thread-safe engine that models an agent's cognitive storm.

    The engine holds six stores: ``_readings`` (StormReading lists
    keyed by agent_id), ``_surges`` (SurgeRecord lists keyed by
    agent_id), ``_snapshots`` (StormSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of StormPlan),
    ``_front_shifts`` (FrontShift lists keyed by agent_id), and
    ``_profiles`` (StormProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The storm model is deliberately heuristic: storm scores
    and intensities are caller-supplied observations; storm
    regimes are banded from the average storm; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how storm is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure storm itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, surges, snapshots, or front shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose storm scores feed into
    # a snapshot's average storm. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current storm posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty storm engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[StormReading]] = {}
        self._surges: Dict[str, List[SurgeRecord]] = {}
        self._snapshots: Dict[str, List[StormSnapshot]] = {}
        self._plans: List[StormPlan] = []
        self._front_shifts: Dict[str, List[FrontShift]] = {}
        self._profiles: Dict[str, StormProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton instance is not touched;
        callers that want a fresh singleton should use
        ``reset_storm_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._surges.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._front_shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[StormReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_surges_locked(
        self, agent_id: str
    ) -> List[SurgeRecord]:
        """Return one agent's surge records in insertion order. Caller holds the lock."""
        return list(self._surges.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[StormSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[StormPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_front_shifts_locked(
        self, agent_id: str
    ) -> List[FrontShift]:
        """Return one agent's front shift records in insertion order. Caller holds the lock."""
        return list(self._front_shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[StormReading]
    ) -> StormAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns FRONT if the list is
        empty, since FRONT is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return StormAxis.FRONT
        counts: Counter = Counter()
        first_seen_order: Dict[StormAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: StormAxis = readings[0].axis
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
        self, profiles: List[StormProfile]
    ) -> StormRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns GATHERING if the list is empty, since
        GATHERING is the default regime — the band that
        represents a normally functioning cognitive atmosphere that
        holds organized activity without being saturated, neither
        clear nor clearing.
        Caller holds the lock.
        """
        if not profiles:
            return StormRegime.GATHERING
        counts: Dict[StormRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> StormProfile:
        """Aggregate an agent's readings, surges, snapshots, and shifts into a profile.

        See ``StormProfile`` for field semantics. ``avg_storm``
        is the mean storm score across the agent's readings (0.0
        if none). ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_storm``.
        ``total_readings``, ``total_surges``, ``total_snapshots``,
        and ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        surges = self._agent_surges_locked(agent_id)
        snapshots = self._agent_snapshots_locked(agent_id)
        front_shifts = self._agent_front_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_storm = sum(
                r.storm_score for r in readings
            ) / len(readings)
        else:
            avg_storm = 0.0

        dominant_regime = _determine_regime(avg_storm)

        return StormProfile(
            agent_id=str(agent_id),
            dominant_regime=dominant_regime,
            avg_storm=round(avg_storm, 4),
            total_readings=total_readings,
            total_surges=len(surges),
            total_snapshots=len(snapshots),
            total_shifts=len(front_shifts),
            updated_at=_now(),
        )

    # ── Storm Readings ───────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        storm_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> StormReading:
        """Record a storm reading for an agent and return it.

        ``axis`` may be passed as a ``StormAxis`` member or its
        string name/value. ``storm_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``StormSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = StormReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(StormAxis, axis),
                storm_score=_clamp(storm_score, 0.0, 1.0),
                source=_resolve_enum(StormSource, source),
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
    ) -> List[StormReading]:
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

    def get_reading(self, reading_id: str) -> StormReading:
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

    # ── Surge Records ────────────────────────────────────────────

    def record_surge(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        surge_magnitude: float,
        notes: Optional[str] = None,
    ) -> SurgeRecord:
        """Record a surge event for an agent and return it.

        ``axis`` may be passed as a ``StormAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``StormSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``surge_magnitude`` is clamped to [0, ∞). The surge
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = SurgeRecord(
                surge_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(StormAxis, axis),
                source=_resolve_enum(StormSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                surge_magnitude=_clamp_positive_ms(
                    surge_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._surges.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_surges(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SurgeRecord]:
        """Return surge records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all surges are considered;
        otherwise only surges for that agent are returned. The
        most recently recorded ``limit`` surges are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                surges = self._agent_surges_locked(agent_id)
            else:
                surges = []
                for agent_surges in self._surges.values():
                    surges.extend(agent_surges)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return surges[-n:] if n else []

    def get_surge(self, surge_id: str) -> SurgeRecord:
        """Retrieve a surge record by id.

        Raises ``ValueError`` if no surge exists with that id.
        """
        with self._lock:
            for agent_surges in self._surges.values():
                for surge in agent_surges:
                    if surge.surge_id == surge_id:
                        return surge
        raise ValueError(f"surge {surge_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> StormSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_storm`` is the mean storm score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``StormAxis`` among
        those readings, or FRONT if none. ``dominant_regime`` and
        ``regime`` are both derived via ``_determine_regime`` from
        ``avg_storm`` and carry the same value. ``surge_count``
        is the number of surge events recorded against the agent.
        The snapshot is stored and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_storm = sum(
                    r.storm_score for r in recent
                ) / len(recent)
            else:
                avg_storm = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_storm)
            surge_count = len(
                self._agent_surges_locked(agent_id)
            )

            snapshot = StormSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_storm=round(avg_storm, 4),
                dominant_axis=dominant_axis,
                dominant_regime=regime,
                regime=regime,
                surge_count=surge_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StormSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> StormSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Storm Plans ────────────────────────────────────────────────

    def plan_surge(
        self,
        agent_id: str,
        strategy: Any,
        target_storm: float,
        rationale: str,
    ) -> StormPlan:
        """Record a storm plan for an agent and return it.

        ``strategy`` may be passed as a ``StormStrategy`` member
        or its string name/value. ``target_storm`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured storm.
        """
        with self._lock:
            plan = StormPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(StormStrategy, strategy),
                target_storm=_clamp(target_storm, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StormPlan]:
        """Return storm plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> StormPlan:
        """Retrieve a storm plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Front Shift Records ────────────────────────────────────────

    def record_front_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> FrontShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``StormStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        gather", "sudden peak", "deliberate buildup"). The front
        shift record is stored and returned; the agent's cached
        profile is invalidated.

        Front shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = FrontShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(StormStage, from_stage),
                to_stage=_resolve_enum(StormStage, to_stage),
                interval_ms=int(_clamp_positive_ms(interval_ms)),
                signature=str(signature),
                timestamp=_now(),
            )
            self._front_shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_front_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FrontShift]:
        """Return front shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all front shifts are considered;
        otherwise only front shifts for that agent are returned. The
        most recently recorded ``limit`` front shift records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                front_shifts = self._agent_front_shifts_locked(agent_id)
            else:
                front_shifts = []
                for agent_front_shifts in self._front_shifts.values():
                    front_shifts.extend(agent_front_shifts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return front_shifts[-n:] if n else []

    def get_front_shift(self, shift_id: str) -> FrontShift:
        """Retrieve a front shift record by id.

        Raises ``ValueError`` if no front shift record exists with that
        id.
        """
        with self._lock:
            for agent_front_shifts in self._front_shifts.values():
                for record in agent_front_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"front shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> StormProfile:
        """Return the agent's storm profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, surges, snapshots, or
        front shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``StormProfile``
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
    ) -> StormProfile:
        """Refresh and optionally override fields of an agent's storm profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``StormProfile`` field names) are applied. Accepted
        overrides: ``avg_storm`` (float), ``dominant_regime``
        (``StormRegime``), ``total_readings``,
        ``total_surges``, ``total_snapshots``, ``total_shifts``
        (int). Enum-valued overrides may be passed as the enum
        member or its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_storm":
                    try:
                        profile.avg_storm = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            StormRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_surges",
                    "total_snapshots",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[StormProfile]:
        """Return all stored storm profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> StormStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, surges, snapshots, and front shifts.
        Scalar totals are the counts of each record type.
        ``avg_storm`` is the mean storm score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        GATHERING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        storm via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._surges.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._front_shifts.keys())

            total_readings = 0
            storm_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    storm_sum += reading.storm_score
            avg_storm = (
                round(storm_sum / total_readings, 4) if total_readings else 0.0
            )

            total_surges = sum(
                len(agent_surges)
                for agent_surges in self._surges.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_shifts = sum(
                len(agent_front_shifts)
                for agent_front_shifts in self._front_shifts.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average storm so the stats
                # reflect real state rather than the default
                # GATHERING.
                dominant_regime = _determine_regime(avg_storm)
            else:
                dominant_regime = StormRegime.GATHERING

            return StormStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_surges=total_surges,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_storm=avg_storm,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveStorm] = None
_engine_lock = threading.Lock()


def get_storm_engine() -> AgentCognitiveStorm:
    """Get or create the singleton ``AgentCognitiveStorm`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveStorm()
    return _engine


def reset_storm_engine() -> None:
    """Reset the singleton ``AgentCognitiveStorm`` instance.

    Drops the handle to the current engine so the next
    ``get_storm_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
