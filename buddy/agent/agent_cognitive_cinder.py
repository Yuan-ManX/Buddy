from __future__ import annotations

"""Agent Cognitive Cinder Engine — modeling smoldering cognitive potential

How latent cognitive embers wait to ignite into active ideas within an agent.
A blazing agent holds ideas in active flame; an extinct agent's potential has
cooled to ash. Distinct from attention, salience, arousal, momentum, and energy.
Core capabilities: axis tracking, spark sources, ignition strategies, burn stages.

Architecture:
  AgentCognitiveCinder (singleton)
  ├── CinderReading      (one observation of cinder on one axis)
  ├── SparkRecord        (one spark event that changed cinder)
  ├── CinderSnapshot     (aggregate cinder state for one agent)
  ├── CinderPlan         (a plan to shape the field with a strategy)
  ├── EmberShift         (one stage transition in the burn lifecycle)
  ├── CinderProfile      (per-agent aggregate cinder tendencies)
  └── CinderStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/spark/etc.

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
    engine with a ``NaN`` or ``None`` cinder. A low-side default is
    safer than a mid-range one for cinder-like quantities where a
    spurious high reading would inflate the perceived cinder and
    push the agent's regime toward BLAZING.
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
    real shift intervals and spark magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    ignition may apply a large effective spark.
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
    against member values (e.g. ``"friction"``) and then against
    member names (e.g. ``"FRICTION"``), so callers may pass either
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


def _determine_regime(avg_cinder: float) -> "CinderRegime":
    """Classify a cinder regime from the average cinder score.

    The average cinder is clamped to [0, 1] where higher means a
    more ignited, blazing posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is EXTINCT
    (no heat, no potential); below 0.35 it is SMOLDERING (latent,
    waiting to ignite); below 0.55 it is GLOWING (warming up,
    visible heat); below 0.75 it is FLICKERING (unstable,
    intermittent); below 0.9 it is BURNING (active, steady);
    otherwise it is BLAZING (fully ignited, intense).
    """
    avg = _clamp(avg_cinder, 0.0, 1.0)
    if avg < 0.15:
        return CinderRegime.EXTINCT
    if avg < 0.35:
        return CinderRegime.SMOLDERING
    if avg < 0.55:
        return CinderRegime.GLOWING
    if avg < 0.75:
        return CinderRegime.FLICKERING
    if avg < 0.9:
        return CinderRegime.BURNING
    return CinderRegime.BLAZING


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CinderAxis(str, Enum):
    """The axis along which a cinder reading is taken.

    Each axis names a different dimension of the agent's cognitive
    field whose cinder can be measured. EMBER is the latent potential
    held in reserve. ASH is the residue of past burning. SOOT is the
    accumulated deposit of spent ideas. HEAT is the thermal intensity
    of the current state. SPARK is the ignition potential. FLAME is
    the active burning of an idea.
    """
    EMBER = "ember"    # latent potential held in reserve
    ASH = "ash"        # residue of past burning
    SOOT = "soot"      # accumulated deposit of spent ideas
    HEAT = "heat"      # thermal intensity of the current state
    SPARK = "spark"    # ignition potential
    FLAME = "flame"    # active burning of an idea


class CinderRegime(str, Enum):
    """The regime an agent's cinder occupies, classified by cinder score.

    Ranges from EXTINCT (no heat, no potential) through SMOLDERING
    (latent, waiting to ignite), GLOWING (warming up, visible heat),
    FLICKERING (unstable, intermittent), and BURNING (active, steady)
    to BLAZING (fully ignited, intense). The regime is derived from the
    average cinder across the agent's readings via
    ``_determine_regime``.
    """
    EXTINCT = "extinct"          # no heat, no potential
    SMOLDERING = "smoldering"    # latent, waiting to ignite
    GLOWING = "glowing"          # warming up, visible heat
    FLICKERING = "flickering"    # unstable, intermittent
    BURNING = "burning"          # active, steady
    BLAZING = "blazing"          # fully ignited, intense


class CinderSource(str, Enum):
    """A source that supplies the heat or ignition for cinder.

    Each source names a different origin of the thermal energy behind
    cinder. FRICTION warms gradually through interaction. COMBUSTION
    sustains a chemical reaction. OXYGEN enables from outside. FUEL
    supplies material to burn. IGNITION starts directly. RESIDUAL
    lingers as leftover heat. A cinder reading records which source
    supplies the heat on the measured axis, and a spark record records
    which source drove a change.
    """
    FRICTION = "friction"      # gradual warming through interaction
    COMBUSTION = "combustion"  # sustained chemical reaction
    OXYGEN = "oxygen"          # external enabling supply
    FUEL = "fuel"              # material to burn
    IGNITION = "ignition"      # direct initiation
    RESIDUAL = "residual"      # lingering leftover heat


class CinderStrategy(str, Enum):
    """Strategy for shaping the cinder deliberately.

    IGNITE starts the fire. SMOTHER suppresses by cutting off oxygen.
    FAN encourages by increasing oxygen. BANK reduces to save for
    later. KINDLE nurtures by building up slowly. EXTINGUISH puts out
    completely. Each strategy is suited to a different field
    condition, from coaxing a cold ember to releasing a blazing one.
    """
    IGNITE = "ignite"          # start the fire
    SMOTHER = "smother"        # suppress by cutting off oxygen
    FAN = "fan"                # encourage by increasing oxygen
    BANK = "bank"              # reduce to save for later
    KINDLE = "kindle"          # nurture by building up slowly
    EXTINGUISH = "extinguish"  # put out completely


class CinderStage(str, Enum):
    """The lifecycle stage of an agent's burn process.

    COLD is the state of no heat. WARMING is the phase of beginning
    to heat. SMOLDERING is the state of latent heat. GLOWING is the
    state of visible heat. FLICKERING is the state of unstable flame.
    BURNING is the final state of active flame. The engine records
    transitions between stages as EmberShift entries.
    """
    COLD = "cold"              # no heat
    WARMING = "warming"        # beginning to heat
    SMOLDERING = "smoldering"  # latent heat
    GLOWING = "glowing"        # visible heat
    FLICKERING = "flickering"  # unstable flame
    BURNING = "burning"        # active flame


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CinderReading:
    """One observation of cinder on a particular axis.

    ``axis`` is the ``CinderAxis`` the reading is taken on.
    ``cinder_score`` in [0, 1] measures how ignited the agent is
    on that axis — 0 means fully cold, 1 means fully blazing.
    ``source`` is the ``CinderSource`` supplying the heat.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: CinderAxis
    cinder_score: float    # 0..1, higher = more ignited
    source: CinderSource
    intensity: float       # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CinderAxis, self.axis),
            "cinder_score": self.cinder_score,
            "source": _enum_value(CinderSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class SparkRecord:
    """One spark event that changed the cinder on an axis.

    ``axis`` is the ``CinderAxis`` on which the spark occurred.
    ``source`` is the ``CinderSource`` that drove the change.
    ``before_score`` in [0, 1] is the cinder before the event;
    ``after_score`` in [0, 1] is the cinder after.
    ``spark_magnitude`` in [0, ∞) measures how strong the
    spark was. ``notes`` is an optional free-form annotation.
    """
    spark_id: str
    agent_id: str
    axis: CinderAxis
    source: CinderSource
    before_score: float        # 0..1, cinder before spark
    after_score: float         # 0..1, cinder after spark
    spark_magnitude: float     # 0..inf, strength of spark
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this spark record to a plain dict, expanding enums via ``.value``."""
        return {
            "spark_id": self.spark_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CinderAxis, self.axis),
            "source": _enum_value(CinderSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "spark_magnitude": self.spark_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CinderSnapshot:
    """Aggregate cinder state for one agent at one moment.

    ``avg_cinder`` in [0, 1] is the mean cinder score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``CinderAxis`` among those readings, or
    EMBER if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_cinder``. ``spark_count``
    is the number of spark events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_cinder: float
    dominant_axis: CinderAxis
    regime: CinderRegime
    spark_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Emits both ``"dominant_regime"`` and ``"regime"`` keys pointing
        to the same value, so consumers that expect either name both
        resolve correctly.
        """
        regime_value = _enum_value(CinderRegime, self.regime)
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_cinder": self.avg_cinder,
            "dominant_axis": _enum_value(CinderAxis, self.dominant_axis),
            "dominant_regime": regime_value,
            "regime": regime_value,
            "spark_count": self.spark_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CinderPlan:
    """A plan to shape the cinder with a strategy.

    ``strategy`` is the ``CinderStrategy`` chosen.
    ``target_cinder`` in [0, 1] is the cinder the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's field condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current cinder — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: CinderStrategy
    target_cinder: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(CinderStrategy, self.strategy),
            "target_cinder": self.target_cinder,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class EmberShift:
    """One record of a stage transition in the burn lifecycle.

    ``from_stage`` is the ``CinderStage`` the agent was in before
    the transition. ``to_stage`` is the ``CinderStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow warm",
    "sudden ignition", "deliberate kindling").
    """
    shift_id: str
    agent_id: str
    from_stage: CinderStage
    to_stage: CinderStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this ember shift record to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(CinderStage, self.from_stage),
            "to_stage": _enum_value(CinderStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class CinderProfile:
    """Per-agent aggregate cinder tendencies.

    ``avg_cinder`` in [0, 1] is the mean cinder score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``CinderAxis`` among the agent's readings, or
    EMBER if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_cinder``. ``total_readings``,
    ``total_sparks``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_cinder: float = 0.0
    dominant_axis: CinderAxis = CinderAxis.EMBER
    dominant_regime: CinderRegime = CinderRegime.SMOLDERING
    total_readings: int = 0
    total_sparks: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_cinder": self.avg_cinder,
            "dominant_axis": _enum_value(CinderAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CinderRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_sparks": self.total_sparks,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class CinderStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_cinder`` is the mean cinder score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or SMOLDERING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_sparks: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_cinder: float = 0.0
    dominant_regime: CinderRegime = CinderRegime.SMOLDERING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_sparks": self.total_sparks,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_cinder": self.avg_cinder,
            "dominant_regime": _enum_value(CinderRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCinder:
    """Thread-safe engine that models an agent's cognitive cinder.

    The engine holds six stores: ``_readings`` (CinderReading lists
    keyed by agent_id), ``_sparks`` (SparkRecord lists keyed by
    agent_id), ``_snapshots`` (CinderSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of CinderPlan),
    ``_shifts`` (EmberShift lists keyed by agent_id), and
    ``_profiles`` (CinderProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The cinder model is deliberately heuristic: cinder scores
    and intensities are caller-supplied observations; cinder
    regimes are banded from the average cinder; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how cinder is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure cinder itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, sparks, snapshots, or shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose cinder scores feed into
    # a snapshot's average cinder. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current cinder posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty cinder engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[CinderReading]] = {}
        self._sparks: Dict[str, List[SparkRecord]] = {}
        self._snapshots: Dict[str, List[CinderSnapshot]] = {}
        self._plans: List[CinderPlan] = []
        self._shifts: Dict[str, List[EmberShift]] = {}
        self._profiles: Dict[str, CinderProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_cinder_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._sparks.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[CinderReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_sparks_locked(
        self, agent_id: str
    ) -> List[SparkRecord]:
        """Return one agent's spark records in insertion order. Caller holds the lock."""
        return list(self._sparks.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[CinderSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[CinderPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[EmberShift]:
        """Return one agent's ember shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[CinderReading]
    ) -> CinderAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns EMBER if the list is
        empty, since EMBER is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return CinderAxis.EMBER
        counts: Counter = Counter()
        first_seen_order: Dict[CinderAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: CinderAxis = readings[0].axis
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
        self, profiles: List[CinderProfile]
    ) -> CinderRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns SMOLDERING if the list is empty, since
        SMOLDERING is the default regime — the band that
        represents a normally functioning cognitive field that
        holds latent potential without being extinguished or
        blazing. Caller holds the lock.
        """
        if not profiles:
            return CinderRegime.SMOLDERING
        counts: Dict[CinderRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> CinderProfile:
        """Aggregate an agent's readings, sparks, and shifts into a profile.

        See ``CinderProfile`` for field semantics. ``avg_cinder``
        is the mean cinder score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``CinderAxis`` among the agent's readings, or EMBER
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_cinder``.
        ``total_readings``, ``total_sparks``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        sparks = self._agent_sparks_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_cinder = sum(
                r.cinder_score for r in readings
            ) / len(readings)
        else:
            avg_cinder = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_cinder)

        return CinderProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_cinder=round(avg_cinder, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_sparks=len(sparks),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Cinder Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        cinder_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> CinderReading:
        """Record a cinder reading for an agent and return it.

        ``axis`` may be passed as a ``CinderAxis`` member or its
        string name/value. ``cinder_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``CinderSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = CinderReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CinderAxis, axis),
                cinder_score=_clamp(cinder_score, 0.0, 1.0),
                source=_resolve_enum(CinderSource, source),
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
    ) -> List[CinderReading]:
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

    def get_reading(self, reading_id: str) -> CinderReading:
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

    # ── Spark Records ────────────────────────────────────────

    def record_spark(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        spark_magnitude: float,
        notes: Optional[str] = None,
    ) -> SparkRecord:
        """Record a spark event for an agent and return it.

        ``axis`` may be passed as a ``CinderAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``CinderSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``spark_magnitude`` is clamped to [0, ∞). The spark
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = SparkRecord(
                spark_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CinderAxis, axis),
                source=_resolve_enum(CinderSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                spark_magnitude=_clamp_positive_ms(
                    spark_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._sparks.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_sparks(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SparkRecord]:
        """Return spark records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all sparks are considered;
        otherwise only sparks for that agent are returned. The
        most recently recorded ``limit`` sparks are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                sparks = self._agent_sparks_locked(agent_id)
            else:
                sparks = []
                for agent_sparks in self._sparks.values():
                    sparks.extend(agent_sparks)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return sparks[-n:] if n else []

    def get_spark(self, spark_id: str) -> SparkRecord:
        """Retrieve a spark record by id.

        Raises ``ValueError`` if no spark exists with that id.
        """
        with self._lock:
            for agent_sparks in self._sparks.values():
                for spark in agent_sparks:
                    if spark.spark_id == spark_id:
                        return spark
        raise ValueError(f"spark {spark_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CinderSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_cinder`` is the mean cinder score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``CinderAxis`` among
        those readings, or EMBER if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_cinder``.
        ``spark_count`` is the number of spark events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_cinder = sum(
                    r.cinder_score for r in recent
                ) / len(recent)
            else:
                avg_cinder = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_cinder)
            spark_count = len(
                self._agent_sparks_locked(agent_id)
            )

            snapshot = CinderSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_cinder=round(avg_cinder, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                spark_count=spark_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CinderSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> CinderSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Cinder Plans ────────────────────────────────────────────

    def plan_spark(
        self,
        agent_id: str,
        strategy: Any,
        target_cinder: float,
        rationale: str,
    ) -> CinderPlan:
        """Record a cinder plan for an agent and return it.

        ``strategy`` may be passed as a ``CinderStrategy`` member
        or its string name/value. ``target_cinder`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured cinder.
        """
        with self._lock:
            plan = CinderPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(CinderStrategy, strategy),
                target_cinder=_clamp(target_cinder, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CinderPlan]:
        """Return cinder plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> CinderPlan:
        """Retrieve a cinder plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Ember Shift Records ─────────────────────────────────────

    def record_ember_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> EmberShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``CinderStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        warm", "sudden ignition", "deliberate kindling"). The
        ember shift record is stored and returned; the agent's cached
        profile is invalidated.

        Ember shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = EmberShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(CinderStage, from_stage),
                to_stage=_resolve_enum(CinderStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_ember_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EmberShift]:
        """Return ember shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all shifts are considered;
        otherwise only shifts for that agent are returned. The
        most recently recorded ``limit`` ember shift records are
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

    def get_ember_shift(self, shift_id: str) -> EmberShift:
        """Retrieve an ember shift record by id.

        Raises ``ValueError`` if no ember shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"ember shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CinderProfile:
        """Return the agent's cinder profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, sparks, snapshots, or
        shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``CinderProfile``
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
    ) -> CinderProfile:
        """Refresh and optionally override fields of an agent's cinder profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``CinderProfile`` field names) are applied. Accepted
        overrides: ``avg_cinder`` (float), ``dominant_axis``
        (``CinderAxis``), ``dominant_regime``
        (``CinderRegime``), ``total_readings``,
        ``total_sparks``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_cinder":
                    try:
                        profile.avg_cinder = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            CinderAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            CinderRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_sparks",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CinderProfile]:
        """Return all stored cinder profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> CinderStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, sparks, snapshots, and shifts.
        Scalar totals are the counts of each record type.
        ``avg_cinder`` is the mean cinder score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        SMOLDERING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        cinder via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._sparks.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            cinder_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    cinder_sum += reading.cinder_score
            avg_cinder = (
                round(cinder_sum / total_readings, 4) if total_readings else 0.0
            )

            total_sparks = sum(
                len(agent_sparks)
                for agent_sparks in self._sparks.values()
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
                # the regime from the average cinder so the stats
                # reflect real state rather than the default
                # SMOLDERING.
                dominant_regime = _determine_regime(avg_cinder)
            else:
                dominant_regime = CinderRegime.SMOLDERING

            return CinderStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_sparks=total_sparks,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_cinder=avg_cinder,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCinder] = None
_engine_lock = threading.Lock()


def get_cinder_engine() -> AgentCognitiveCinder:
    """Get or create the singleton ``AgentCognitiveCinder`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveCinder()
    return _engine


def reset_cinder_engine() -> None:
    """Reset the singleton ``AgentCognitiveCinder`` instance.

    Drops the reference to the current engine so the next
    ``get_cinder_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
