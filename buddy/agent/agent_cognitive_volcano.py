from __future__ import annotations

"""Agent Cognitive Volcano Engine — modeling pressure buildup and release

How cognitive energy accumulates in chambers, builds pressure along conduits,
and erupts through vents when the system can no longer contain it. A dormant
agent holds energy quietly; an erupting agent releases it in a single burst.
Distinct from tension, arousal, momentum, focus, and intensity.
Core capabilities: axis tracking, pressure sources, venting strategies, eruption stages.

Architecture:
  AgentCognitiveVolcano (singleton)
  ├── VolcanoReading       (one observation of pressure on one axis)
  ├── EruptionRecord       (one eruption event that released pressure)
  ├── VolcanoSnapshot      (aggregate volcano state for one agent)
  ├── VolcanoPlan          (a plan to shape the pressure with a strategy)
  ├── LavaShift            (one stage transition in the eruption lifecycle)
  ├── VolcanoProfile       (per-agent aggregate volcano tendencies)
  └── VolcanoStats         (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/eruption/etc.

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
    engine with a ``NaN`` or ``None`` volcano score. A low-side default is
    safer than a mid-range one for volcano-like quantities where a
    spurious high reading would inflate the perceived pressure and
    push the agent's regime toward COLLAPSING.
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
    real eruption intervals and eruption magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    pressurization may apply a large effective eruption.
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
    against member values (e.g. ``"heat"``) and then against
    member names (e.g. ``"HEAT"``), so callers may pass either
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


def _determine_regime(avg_volcano: float) -> "VolcanoRegime":
    """Classify a volcano regime from the average volcano score.

    The average volcano score is clamped to [0, 1] where higher means a
    more pressurized, volatile posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is DORMANT
    (no activity, quiet pressure); below 0.35 it is FUMING (minor
    gas release, surface venting); below 0.55 it is SWELLING (pressure
    building, chamber filling); below 0.75 it is RUMBLING (seismic
    activity, structure straining); below 0.9 it is ERUPTING (active
    release, full venting); otherwise it is COLLAPSING (structure
    failing, catastrophic release).
    """
    avg = _clamp(avg_volcano, 0.0, 1.0)
    if avg < 0.15:
        return VolcanoRegime.DORMANT
    if avg < 0.35:
        return VolcanoRegime.FUMING
    if avg < 0.55:
        return VolcanoRegime.SWELLING
    if avg < 0.75:
        return VolcanoRegime.RUMBLING
    if avg < 0.9:
        return VolcanoRegime.ERUPTING
    return VolcanoRegime.COLLAPSING


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class VolcanoAxis(str, Enum):
    """The axis along which a volcano reading is taken.

    Each axis names a different dimension of the agent's cognitive
    pressure whose volcano score can be measured. MAGMA is the molten
    energy source. CHAMBER is the reservoir holding the energy. VENT
    is the conduit the energy travels through. CONE is the built-up
    structure around the conduit. FLANK is the side of the structure
    that may give way. CRATER is the opening at the top through which
    energy is released.
    """
    MAGMA = "magma"        # molten rock source
    CHAMBER = "chamber"    # underground reservoir
    VENT = "vent"          # conduit to surface
    CONE = "cone"          # built-up structure
    FLANK = "flank"        # side slope
    CRATER = "crater"      # top opening


class VolcanoRegime(str, Enum):
    """The regime an agent's volcano occupies, classified by volcano score.

    Ranges from DORMANT (no activity, quiet pressure) through FUMING
    (minor gas release, surface venting), SWELLING (pressure building,
    chamber filling), RUMBLING (seismic activity, structure
    straining), and ERUPTING (active release, full venting) to
    COLLAPSING (structure failing, catastrophic release). The regime
    is derived from the average volcano score across the agent's
    readings via ``_determine_regime``.
    """
    DORMANT = "dormant"      # no activity
    FUMING = "fuming"        # minor gas release
    SWELLING = "swelling"    # pressure building
    RUMBLING = "rumbling"    # seismic activity
    ERUPTING = "erupting"    # active eruption
    COLLAPSING = "collapsing"  # structure failing


class VolcanoSource(str, Enum):
    """A source that supplies the pressure or energy.

    Each source names a different origin of the pressure building in
    the agent. HEAT supplies thermal energy from within. PRESSURE
    supplies confining force from above. FRICTION supplies tectonic
    drag from the sides. SUBDUCTION supplies energy from a descending
    plate. DECOMPRESSION supplies energy from pressure-release
    melting. CRYSTALLIZATION supplies energy from volatile release
    during crystal formation. A volcano reading records which source
    supplies the pressure on the measured axis, and an eruption
    record records which source drove a release.
    """
    HEAT = "heat"                    # thermal energy
    PRESSURE = "pressure"            # confining pressure
    FRICTION = "friction"            # tectonic friction
    SUBDUCTION = "subduction"        # plate subduction
    DECOMPRESSION = "decompression"  # pressure-release melting
    CRYSTALLIZATION = "crystallization"  # volatile release


class VolcanoStrategy(str, Enum):
    """Strategy for shaping the pressure deliberately.

    BUILD accumulates pressure in the chamber. PRESSURIZE increases
    the confining pressure further. VENT releases pressure gradually
    through small openings. ERUPT releases pressure violently in a
    single burst. COOL reduces the temperature and pressure. COLLAPSE
    lets the structure give way and shed load. Each strategy is
    suited to a different pressure condition, from relieving a
    swelling chamber to deliberately triggering a collapse.
    """
    BUILD = "build"          # accumulate pressure
    PRESSURIZE = "pressurize"  # increase pressure
    VENT = "vent"            # release gradually
    ERUPT = "erupt"          # release violently
    COOL = "cool"            # reduce temperature
    COLLAPSE = "collapse"    # let structure fail


class VolcanoStage(str, Enum):
    """The lifecycle stage of an agent's eruption process.

    DORMANT is the state of no activity. FUMING is the phase of
    minor surface venting. SWELLING is the state in which the chamber
    fills and pressure builds. RUMBLING is the state of noticeable
    seismic activity. ERUPTING is the state of active release.
    COOLING is the final state in which the system cools and settles
    back toward dormancy. The engine records transitions between
    stages as LavaShift entries.
    """
    DORMANT = "dormant"    # no activity
    FUMING = "fuming"      # minor gas release
    SWELLING = "swelling"  # pressure building
    RUMBLING = "rumbling"  # seismic activity
    ERUPTING = "erupting"  # active eruption
    COOLING = "cooling"    # post-eruption cooling


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VolcanoReading:
    """One observation of volcano pressure on a particular axis.

    ``axis`` is the ``VolcanoAxis`` the reading is taken on.
    ``volcano_score`` in [0, 1] measures how pressurized the agent is
    on that axis — 0 means fully dormant, 1 means fully collapsing.
    ``source`` is the ``VolcanoSource`` supplying the pressure.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: VolcanoAxis
    volcano_score: float    # 0..1, higher = more pressurized
    source: VolcanoSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(VolcanoAxis, self.axis),
            "volcano_score": self.volcano_score,
            "source": _enum_value(VolcanoSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class EruptionRecord:
    """One eruption event that changed the pressure on an axis.

    ``axis`` is the ``VolcanoAxis`` on which the eruption occurred.
    ``source`` is the ``VolcanoSource`` that drove the change.
    ``before_score`` in [0, 1] is the volcano score before the event;
    ``after_score`` in [0, 1] is the volcano score after.
    ``eruption_magnitude`` in [0, ∞) measures how strong the
    eruption was. ``notes`` is an optional free-form annotation.
    """
    eruption_id: str
    agent_id: str
    axis: VolcanoAxis
    source: VolcanoSource
    before_score: float            # 0..1, volcano score before eruption
    after_score: float             # 0..1, volcano score after eruption
    eruption_magnitude: float    # 0..inf, strength of eruption
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this eruption record to a plain dict, expanding enums via ``.value``."""
        return {
            "eruption_id": self.eruption_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(VolcanoAxis, self.axis),
            "source": _enum_value(VolcanoSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "eruption_magnitude": self.eruption_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class VolcanoSnapshot:
    """Aggregate volcano state for one agent at one moment.

    ``avg_volcano`` in [0, 1] is the mean volcano score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``VolcanoAxis`` among those readings, or
    MAGMA if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_volcano``. ``eruption_count``
    is the number of eruption events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_volcano: float
    dominant_axis: VolcanoAxis
    regime: VolcanoRegime
    eruption_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_volcano": self.avg_volcano,
            "dominant_axis": _enum_value(VolcanoAxis, self.dominant_axis),
            "regime": _enum_value(VolcanoRegime, self.regime),
            "dominant_regime": _enum_value(VolcanoRegime, self.regime),
            "eruption_count": self.eruption_count,
            "timestamp": self.timestamp,
        }


@dataclass
class VolcanoPlan:
    """A plan to shape the pressure with a strategy.

    ``strategy`` is the ``VolcanoStrategy`` chosen.
    ``target_volcano`` in [0, 1] is the volcano score the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's pressure condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current pressure — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: VolcanoStrategy
    target_volcano: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(VolcanoStrategy, self.strategy),
            "target_volcano": self.target_volcano,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class LavaShift:
    """One record of a stage transition in the eruption lifecycle.

    ``from_stage`` is the ``VolcanoStage`` the agent was in before
    the transition. ``to_stage`` is the ``VolcanoStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow swell",
    "sudden eruption", "deliberate venting").
    """
    shift_id: str
    agent_id: str
    from_stage: VolcanoStage
    to_stage: VolcanoStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this lava shift record to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(VolcanoStage, self.from_stage),
            "to_stage": _enum_value(VolcanoStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class VolcanoProfile:
    """Per-agent aggregate volcano tendencies.

    ``avg_volcano`` in [0, 1] is the mean volcano score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``VolcanoAxis`` among the agent's readings, or
    MAGMA if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_volcano``. ``total_readings``,
    ``total_eruptions``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_volcano: float = 0.0
    dominant_axis: VolcanoAxis = VolcanoAxis.MAGMA
    dominant_regime: VolcanoRegime = VolcanoRegime.SWELLING
    total_readings: int = 0
    total_eruptions: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_volcano": self.avg_volcano,
            "dominant_axis": _enum_value(VolcanoAxis, self.dominant_axis),
            "dominant_regime": _enum_value(VolcanoRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_eruptions": self.total_eruptions,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class VolcanoStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_volcano`` is the mean volcano score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or SWELLING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_eruptions: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_volcano: float = 0.0
    dominant_regime: VolcanoRegime = VolcanoRegime.SWELLING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_eruptions": self.total_eruptions,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_volcano": self.avg_volcano,
            "dominant_regime": _enum_value(VolcanoRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveVolcano:
    """Thread-safe engine that models an agent's cognitive volcano.

    The engine holds six stores: ``_readings`` (VolcanoReading lists
    keyed by agent_id), ``_eruptions`` (EruptionRecord lists keyed by
    agent_id), ``_snapshots`` (VolcanoSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of VolcanoPlan),
    ``_shifts`` (LavaShift lists keyed by agent_id), and
    ``_profiles`` (VolcanoProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The volcano model is deliberately heuristic: volcano scores
    and intensities are caller-supplied observations; volcano
    regimes are banded from the average volcano score; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how pressure is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure pressure itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, eruptions, snapshots, or lava shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose volcano scores feed into
    # a snapshot's average volcano score. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current pressure posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty volcano engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[VolcanoReading]] = {}
        self._eruptions: Dict[str, List[EruptionRecord]] = {}
        self._snapshots: Dict[str, List[VolcanoSnapshot]] = {}
        self._plans: List[VolcanoPlan] = []
        self._shifts: Dict[str, List[LavaShift]] = {}
        self._profiles: Dict[str, VolcanoProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_volcano_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._eruptions.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[VolcanoReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_eruptions_locked(
        self, agent_id: str
    ) -> List[EruptionRecord]:
        """Return one agent's eruption records in insertion order. Caller holds the lock."""
        return list(self._eruptions.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[VolcanoSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[VolcanoPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_lava_shifts_locked(
        self, agent_id: str
    ) -> List[LavaShift]:
        """Return one agent's lava shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[VolcanoReading]
    ) -> VolcanoAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns MAGMA if the list is
        empty, since MAGMA is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return VolcanoAxis.MAGMA
        counts: Counter = Counter()
        first_seen_order: Dict[VolcanoAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: VolcanoAxis = readings[0].axis
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
        self, profiles: List[VolcanoProfile]
    ) -> VolcanoRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns SWELLING if the list is empty, since
        SWELLING is the default regime — the band that
        represents a normally functioning cognitive volcano that
        is building pressure without being erupting, neither
        dormant nor collapsing. Caller holds the lock.
        """
        if not profiles:
            return VolcanoRegime.SWELLING
        counts: Dict[VolcanoRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> VolcanoProfile:
        """Aggregate an agent's readings, eruptions, and shifts into a profile.

        See ``VolcanoProfile`` for field semantics. ``avg_volcano``
        is the mean volcano score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``VolcanoAxis`` among the agent's readings, or MAGMA
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_volcano``.
        ``total_readings``, ``total_eruptions``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        eruptions = self._agent_eruptions_locked(agent_id)
        shifts = self._agent_lava_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_volcano = sum(
                r.volcano_score for r in readings
            ) / len(readings)
        else:
            avg_volcano = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_volcano)

        return VolcanoProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_volcano=round(avg_volcano, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_eruptions=len(eruptions),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Volcano Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        volcano_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> VolcanoReading:
        """Record a volcano reading for an agent and return it.

        ``axis`` may be passed as a ``VolcanoAxis`` member or its
        string name/value. ``volcano_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``VolcanoSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = VolcanoReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(VolcanoAxis, axis),
                volcano_score=_clamp(volcano_score, 0.0, 1.0),
                source=_resolve_enum(VolcanoSource, source),
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
    ) -> List[VolcanoReading]:
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

    def get_reading(self, reading_id: str) -> VolcanoReading:
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

    # ── Eruption Records ────────────────────────────────────────

    def record_eruption(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        eruption_magnitude: float,
        notes: Optional[str] = None,
    ) -> EruptionRecord:
        """Record an eruption event for an agent and return it.

        ``axis`` may be passed as a ``VolcanoAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``VolcanoSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``eruption_magnitude`` is clamped to [0, ∞). The eruption
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = EruptionRecord(
                eruption_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(VolcanoAxis, axis),
                source=_resolve_enum(VolcanoSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                eruption_magnitude=_clamp_positive_ms(
                    eruption_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._eruptions.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_eruptions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EruptionRecord]:
        """Return eruption records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all eruptions are considered;
        otherwise only eruptions for that agent are returned. The
        most recently recorded ``limit`` eruptions are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                eruptions = self._agent_eruptions_locked(agent_id)
            else:
                eruptions = []
                for agent_eruptions in self._eruptions.values():
                    eruptions.extend(agent_eruptions)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return eruptions[-n:] if n else []

    def get_eruption(self, eruption_id: str) -> EruptionRecord:
        """Retrieve an eruption record by id.

        Raises ``ValueError`` if no eruption exists with that id.
        """
        with self._lock:
            for agent_eruptions in self._eruptions.values():
                for eruption in agent_eruptions:
                    if eruption.eruption_id == eruption_id:
                        return eruption
        raise ValueError(f"eruption {eruption_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> VolcanoSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_volcano`` is the mean volcano score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``VolcanoAxis`` among
        those readings, or MAGMA if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_volcano``.
        ``eruption_count`` is the number of eruption events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_volcano = sum(
                    r.volcano_score for r in recent
                ) / len(recent)
            else:
                avg_volcano = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_volcano)
            eruption_count = len(
                self._agent_eruptions_locked(agent_id)
            )

            snapshot = VolcanoSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_volcano=round(avg_volcano, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                eruption_count=eruption_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[VolcanoSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> VolcanoSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Eruption Plans ────────────────────────────────────────────

    def plan_eruption(
        self,
        agent_id: str,
        strategy: Any,
        target_volcano: float,
        rationale: str,
    ) -> VolcanoPlan:
        """Record an eruption plan for an agent and return it.

        ``strategy`` may be passed as a ``VolcanoStrategy`` member
        or its string name/value. ``target_volcano`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured pressure.
        """
        with self._lock:
            plan = VolcanoPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(VolcanoStrategy, strategy),
                target_volcano=_clamp(target_volcano, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[VolcanoPlan]:
        """Return eruption plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> VolcanoPlan:
        """Retrieve an eruption plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Lava Shift Records ────────────────────────────────────────

    def record_lava_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> LavaShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``VolcanoStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        swell", "sudden eruption", "deliberate venting"). The
        lava shift record is stored and returned; the agent's cached
        profile is invalidated.

        Lava shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = LavaShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(VolcanoStage, from_stage),
                to_stage=_resolve_enum(VolcanoStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_lava_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LavaShift]:
        """Return lava shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all lava shifts are considered;
        otherwise only lava shifts for that agent are returned. The
        most recently recorded ``limit`` lava shift records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                shifts = self._agent_lava_shifts_locked(agent_id)
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

    def get_lava_shift(self, shift_id: str) -> LavaShift:
        """Retrieve a lava shift record by id.

        Raises ``ValueError`` if no lava shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"lava shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> VolcanoProfile:
        """Return the agent's volcano profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, eruptions, snapshots, or
        lava shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``VolcanoProfile``
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
    ) -> VolcanoProfile:
        """Refresh and optionally override fields of an agent's volcano profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``VolcanoProfile`` field names) are applied. Accepted
        overrides: ``avg_volcano`` (float), ``dominant_axis``
        (``VolcanoAxis``), ``dominant_regime``
        (``VolcanoRegime``), ``total_readings``,
        ``total_eruptions``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_volcano":
                    try:
                        profile.avg_volcano = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            VolcanoAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            VolcanoRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_eruptions",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[VolcanoProfile]:
        """Return all stored volcano profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> VolcanoStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, eruptions, snapshots, and lava shifts.
        Scalar totals are the counts of each record type.
        ``avg_volcano`` is the mean volcano score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        SWELLING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        volcano score via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._eruptions.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            volcano_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    volcano_sum += reading.volcano_score
            avg_volcano = (
                round(volcano_sum / total_readings, 4) if total_readings else 0.0
            )

            total_eruptions = sum(
                len(agent_eruptions)
                for agent_eruptions in self._eruptions.values()
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
                # the regime from the average volcano score so the stats
                # reflect real state rather than the default
                # SWELLING.
                dominant_regime = _determine_regime(avg_volcano)
            else:
                dominant_regime = VolcanoRegime.SWELLING

            return VolcanoStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_eruptions=total_eruptions,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_volcano=avg_volcano,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveVolcano] = None
_engine_lock = threading.Lock()


def get_volcano_engine() -> AgentCognitiveVolcano:
    """Get or create the singleton ``AgentCognitiveVolcano`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveVolcano()
    return _engine


def reset_volcano_engine() -> None:
    """Reset the singleton ``AgentCognitiveVolcano`` instance.

    Drops the reference to the current engine so the next
    ``get_volcano_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
