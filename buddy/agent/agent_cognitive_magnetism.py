from __future__ import annotations

"""Agent Cognitive Magnetism Engine — modeling forces between concepts

How concepts attract, repel, align, and form dipoles within the cognitive field.
A magnetized agent holds concepts in tight mutual attraction; a scattered agent's
concepts point every which way. Distinct from polarization, coherence, tension,
equilibrium, and affinity.
Core capabilities: axis tracking, force sources, field strategies, saturation stages.

Architecture:
  AgentCognitiveMagnetism (singleton)
  ├── MagnetismReading      (one observation of magnetism on one axis)
  ├── AttractionRecord      (one attraction event that changed magnetism)
  ├── MagnetismSnapshot     (aggregate magnetism state for one agent)
  ├── AlignmentPlan         (a plan to shape the field with a strategy)
  ├── SaturationRecord      (one stage transition in the saturation lifecycle)
  ├── MagnetismProfile      (per-agent aggregate magnetism tendencies)
  └── MagnetismStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/attraction/etc.

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
    engine with a ``NaN`` or ``None`` magnetism. A low-side default is
    safer than a mid-range one for magnetism-like quantities where a
    spurious high reading would inflate the perceived magnetism and
    push the agent's regime toward ABSOLUTE.
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
    real saturation intervals and attraction magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    amplification may apply a large effective attraction.
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
    against member values (e.g. ``"diamagnetic"``) and then against
    member names (e.g. ``"DIAMAGNETIC"``), so callers may pass either
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


def _determine_regime(avg_magnetism: float) -> "MagnetismRegime":
    """Classify a magnetism regime from the average magnetism score.

    The average magnetism is clamped to [0, 1] where higher means a
    more aligned, magnetized posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is DIAMAGNETIC
    (repelled by all fields, no alignment); below 0.35 it is
    PARAMAGNETIC (weakly attracted, only aligns under external pull);
    below 0.55 it is FERROMAGNETIC (strongly attracted, retains
    alignment); below 0.75 it is ALIGNED (most domains oriented the
    same way); below 0.9 it is SATURATED (fully magnetized, little
    room for more); otherwise it is ABSOLUTE (perfectly locked
    alignment).
    """
    avg = _clamp(avg_magnetism, 0.0, 1.0)
    if avg < 0.15:
        return MagnetismRegime.DIAMAGNETIC
    if avg < 0.35:
        return MagnetismRegime.PARAMAGNETIC
    if avg < 0.55:
        return MagnetismRegime.FERROMAGNETIC
    if avg < 0.75:
        return MagnetismRegime.ALIGNED
    if avg < 0.9:
        return MagnetismRegime.SATURATED
    return MagnetismRegime.ABSOLUTE


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class MagnetismAxis(str, Enum):
    """The axis along which a magnetism reading is taken.

    Each axis names a different dimension of the agent's cognitive
    field whose magnetism can be measured. ATTRACTION is the pull
    toward a concept. REPULSION is the push away from a concept.
    ALIGNMENT is the orientation match between concepts. POLARITY is
    the north/south orientation of a concept. FIELD is the overall
    field strength across the agent's concepts. DIPOLE is the
    paired-pole organization between two opposing concepts.
    """
    ATTRACTION = "attraction"  # pull toward
    REPULSION = "repulsion"    # push away
    ALIGNMENT = "alignment"    # orientation match
    POLARITY = "polarity"      # north/south orientation
    FIELD = "field"            # overall field strength
    DIPOLE = "dipole"          # paired-pole organization


class MagnetismRegime(str, Enum):
    """The regime an agent's magnetism occupies, classified by magnetism.

    Ranges from DIAMAGNETIC (repelled by all fields, no alignment)
    through PARAMAGNETIC (weakly attracted, only aligns under
    external pull), FERROMAGNETIC (strongly attracted, retains
    alignment), ALIGNED (most domains oriented the same way), and
    SATURATED (fully magnetized, little room for more) to ABSOLUTE
    (perfectly locked alignment). The regime is derived from the
    average magnetism across the agent's readings via
    ``_determine_regime``.
    """
    DIAMAGNETIC = "diamagnetic"    # repelled by all fields
    PARAMAGNETIC = "paramagnetic"  # weakly attracted
    FERROMAGNETIC = "ferromagnetic"  # strongly attracted, retains alignment
    ALIGNED = "aligned"            # most domains oriented
    SATURATED = "saturated"        # fully magnetized
    ABSOLUTE = "absolute"          # perfectly locked alignment


class MagnetismSource(str, Enum):
    """A source that supplies the attractive or repulsive force.

    Each source names a different origin of the pull between concepts.
    AFFINITY pulls toward what is naturally liked. VALUES pulls toward
    what is held dear. BELIEF pulls toward what is taken as true.
    EMOTION pulls toward what is felt. LOGIC pulls toward what is
    reasoned. INSTINCT pulls toward the gut response. A magnetism
    reading records which source supplies the force on the measured
    axis, and an attraction record records which source drove a
    change.
    """
    AFFINITY = "affinity"  # pull toward what is liked
    VALUES = "values"      # pull toward what is held dear
    BELIEF = "belief"      # pull toward what is taken as true
    EMOTION = "emotion"    # pull toward what is felt
    LOGIC = "logic"        # pull toward what is reasoned
    INSTINCT = "instinct"  # pull toward the gut response


class MagnetismStrategy(str, Enum):
    """Strategy for shaping the field deliberately.

    ATTRACT pulls concepts together. REPEL pushes concepts apart.
    ALIGN orients concepts toward a common direction. SHIELD protects
    a concept from external influence. AMPLIFY strengthens the field
    around a concept. NEUTRALIZE cancels out an opposing pull. Each
    strategy is suited to a different field condition, from
    counteracting a scattered field to releasing a saturated one.
    """
    ATTRACT = "attract"      # pull concepts together
    REPEL = "repel"          # push concepts apart
    ALIGN = "align"          # orient toward a common direction
    SHIELD = "shield"        # protect from external influence
    AMPLIFY = "amplify"      # strengthen the field
    NEUTRALIZE = "neutralize"  # cancel an opposing pull


class MagnetismStage(str, Enum):
    """The lifecycle stage of an agent's field-formation process.

    SCATTERED is the state of no alignment. ORIENTING is the phase of
    beginning to align. ALIGNED is the state in which most domains
    point the same way. MAGNETIZED is the state of strong mutual
    attraction. SATURATED is the state at capacity, with little room
    for more. LOCKED is the final state at which the field is fully
    locked and unresponsive to new input. The engine records
    transitions between stages as SaturationRecord entries.
    """
    SCATTERED = "scattered"    # no alignment
    ORIENTING = "orienting"    # beginning to align
    ALIGNED = "aligned"        # mostly aligned
    MAGNETIZED = "magnetized"  # strongly magnetized
    SATURATED = "saturated"    # at capacity
    LOCKED = "locked"          # fully locked


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MagnetismReading:
    """One observation of magnetism on a particular axis.

    ``axis`` is the ``MagnetismAxis`` the reading is taken on.
    ``magnetism_score`` in [0, 1] measures how magnetized the agent is
    on that axis — 0 means fully scattered, 1 means fully locked.
    ``source`` is the ``MagnetismSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: MagnetismAxis
    magnetism_score: float    # 0..1, higher = more magnetized
    source: MagnetismSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(MagnetismAxis, self.axis),
            "magnetism_score": self.magnetism_score,
            "source": _enum_value(MagnetismSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class AttractionRecord:
    """One attraction event that changed the magnetism on an axis.

    ``axis`` is the ``MagnetismAxis`` on which the attraction occurred.
    ``source`` is the ``MagnetismSource`` that drove the change.
    ``before_score`` in [0, 1] is the magnetism before the event;
    ``after_score`` in [0, 1] is the magnetism after.
    ``attraction_magnitude`` in [0, ∞) measures how strong the
    attraction was. ``notes`` is an optional free-form annotation.
    """
    attraction_id: str
    agent_id: str
    axis: MagnetismAxis
    source: MagnetismSource
    before_score: float            # 0..1, magnetism before attraction
    after_score: float             # 0..1, magnetism after attraction
    attraction_magnitude: float    # 0..inf, strength of attraction
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this attraction record to a plain dict, expanding enums via ``.value``."""
        return {
            "attraction_id": self.attraction_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(MagnetismAxis, self.axis),
            "source": _enum_value(MagnetismSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "attraction_magnitude": self.attraction_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class MagnetismSnapshot:
    """Aggregate magnetism state for one agent at one moment.

    ``avg_magnetism`` in [0, 1] is the mean magnetism score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``MagnetismAxis`` among those readings, or
    ATTRACTION if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_magnetism``. ``attraction_count``
    is the number of attraction events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_magnetism: float
    dominant_axis: MagnetismAxis
    regime: MagnetismRegime
    attraction_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_magnetism": self.avg_magnetism,
            "dominant_axis": _enum_value(MagnetismAxis, self.dominant_axis),
            "regime": _enum_value(MagnetismRegime, self.regime),
            "attraction_count": self.attraction_count,
            "timestamp": self.timestamp,
        }


@dataclass
class AlignmentPlan:
    """A plan to shape the field with a strategy.

    ``strategy`` is the ``MagnetismStrategy`` chosen.
    ``target_magnetism`` in [0, 1] is the magnetism the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's field condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current magnetism — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: MagnetismStrategy
    target_magnetism: float
    rationale: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(MagnetismStrategy, self.strategy),
            "target_magnetism": self.target_magnetism,
            "rationale": self.rationale,
            "created_at": self.created_at,
        }


@dataclass
class SaturationRecord:
    """One record of a stage transition in the saturation lifecycle.

    ``from_stage`` is the ``MagnetismStage`` the agent was in before
    the transition. ``to_stage`` is the ``MagnetismStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow orient",
    "sudden saturation", "deliberate amplification").
    """
    saturation_id: str
    agent_id: str
    from_stage: MagnetismStage
    to_stage: MagnetismStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this saturation record to a plain dict, expanding enums via ``.value``."""
        return {
            "saturation_id": self.saturation_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(MagnetismStage, self.from_stage),
            "to_stage": _enum_value(MagnetismStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class MagnetismProfile:
    """Per-agent aggregate magnetism tendencies.

    ``avg_magnetism`` in [0, 1] is the mean magnetism score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``MagnetismAxis`` among the agent's readings, or
    ATTRACTION if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_magnetism``. ``total_readings``,
    ``total_attractions``, and ``total_saturations`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_magnetism: float = 0.0
    dominant_axis: MagnetismAxis = MagnetismAxis.ATTRACTION
    dominant_regime: MagnetismRegime = MagnetismRegime.FERROMAGNETIC
    total_readings: int = 0
    total_attractions: int = 0
    total_saturations: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_magnetism": self.avg_magnetism,
            "dominant_axis": _enum_value(MagnetismAxis, self.dominant_axis),
            "dominant_regime": _enum_value(MagnetismRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_attractions": self.total_attractions,
            "total_saturations": self.total_saturations,
            "updated_at": self.updated_at,
        }


@dataclass
class MagnetismStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_magnetism`` is the mean magnetism score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or FERROMAGNETIC when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_attractions: int = 0
    total_snapshots: int = 0
    total_saturations: int = 0
    avg_magnetism: float = 0.0
    dominant_regime: MagnetismRegime = MagnetismRegime.FERROMAGNETIC

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_attractions": self.total_attractions,
            "total_snapshots": self.total_snapshots,
            "total_saturations": self.total_saturations,
            "avg_magnetism": self.avg_magnetism,
            "dominant_regime": _enum_value(MagnetismRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveMagnetism:
    """Thread-safe engine that models an agent's cognitive magnetism.

    The engine holds six stores: ``_readings`` (MagnetismReading lists
    keyed by agent_id), ``_attractions`` (AttractionRecord lists keyed
    by agent_id), ``_snapshots`` (MagnetismSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of AlignmentPlan),
    ``_saturations`` (SaturationRecord lists keyed by agent_id), and
    ``_profiles`` (MagnetismProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The magnetism model is deliberately heuristic: magnetism scores
    and intensities are caller-supplied observations; magnetism
    regimes are banded from the average magnetism; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how magnetism is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure magnetism itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, attractions, snapshots, or saturations change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose magnetism scores feed into
    # a snapshot's average magnetism. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current magnetism posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty magnetism engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[MagnetismReading]] = {}
        self._attractions: Dict[str, List[AttractionRecord]] = {}
        self._snapshots: Dict[str, List[MagnetismSnapshot]] = {}
        self._plans: List[AlignmentPlan] = []
        self._saturations: Dict[str, List[SaturationRecord]] = {}
        self._profiles: Dict[str, MagnetismProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_magnetism_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._attractions.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._saturations.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[MagnetismReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_attractions_locked(
        self, agent_id: str
    ) -> List[AttractionRecord]:
        """Return one agent's attraction records in insertion order. Caller holds the lock."""
        return list(self._attractions.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[MagnetismSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[AlignmentPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_saturations_locked(
        self, agent_id: str
    ) -> List[SaturationRecord]:
        """Return one agent's saturation records in insertion order. Caller holds the lock."""
        return list(self._saturations.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[MagnetismReading]
    ) -> MagnetismAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns ATTRACTION if the list is
        empty, since ATTRACTION is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return MagnetismAxis.ATTRACTION
        counts: Counter = Counter()
        first_seen_order: Dict[MagnetismAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: MagnetismAxis = readings[0].axis
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
        self, profiles: List[MagnetismProfile]
    ) -> MagnetismRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns FERROMAGNETIC if the list is empty, since
        FERROMAGNETIC is the default regime — the band that
        represents a normally functioning cognitive field that
        retains alignment without being saturated, neither
        diamagnetic nor absolute. Caller holds the lock.
        """
        if not profiles:
            return MagnetismRegime.FERROMAGNETIC
        counts: Dict[MagnetismRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> MagnetismProfile:
        """Aggregate an agent's readings, attractions, and saturations into a profile.

        See ``MagnetismProfile`` for field semantics. ``avg_magnetism``
        is the mean magnetism score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``MagnetismAxis`` among the agent's readings, or ATTRACTION
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_magnetism``.
        ``total_readings``, ``total_attractions``, and
        ``total_saturations`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        attractions = self._agent_attractions_locked(agent_id)
        saturations = self._agent_saturations_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_magnetism = sum(
                r.magnetism_score for r in readings
            ) / len(readings)
        else:
            avg_magnetism = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_magnetism)

        return MagnetismProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_magnetism=round(avg_magnetism, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_attractions=len(attractions),
            total_saturations=len(saturations),
            updated_at=_now(),
        )

    # ── Magnetism Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        magnetism_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> MagnetismReading:
        """Record a magnetism reading for an agent and return it.

        ``axis`` may be passed as a ``MagnetismAxis`` member or its
        string name/value. ``magnetism_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``MagnetismSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = MagnetismReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(MagnetismAxis, axis),
                magnetism_score=_clamp(magnetism_score, 0.0, 1.0),
                source=_resolve_enum(MagnetismSource, source),
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
    ) -> List[MagnetismReading]:
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

    def get_reading(self, reading_id: str) -> MagnetismReading:
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

    # ── Attraction Records ────────────────────────────────────────

    def record_attraction(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        attraction_magnitude: float,
        notes: Optional[str] = None,
    ) -> AttractionRecord:
        """Record an attraction event for an agent and return it.

        ``axis`` may be passed as a ``MagnetismAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``MagnetismSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``attraction_magnitude`` is clamped to [0, ∞). The attraction
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = AttractionRecord(
                attraction_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(MagnetismAxis, axis),
                source=_resolve_enum(MagnetismSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                attraction_magnitude=_clamp_positive_ms(
                    attraction_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._attractions.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_attractions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AttractionRecord]:
        """Return attraction records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all attractions are considered;
        otherwise only attractions for that agent are returned. The
        most recently recorded ``limit`` attractions are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                attractions = self._agent_attractions_locked(agent_id)
            else:
                attractions = []
                for agent_attractions in self._attractions.values():
                    attractions.extend(agent_attractions)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return attractions[-n:] if n else []

    def get_attraction(self, attraction_id: str) -> AttractionRecord:
        """Retrieve an attraction record by id.

        Raises ``ValueError`` if no attraction exists with that id.
        """
        with self._lock:
            for agent_attractions in self._attractions.values():
                for attraction in agent_attractions:
                    if attraction.attraction_id == attraction_id:
                        return attraction
        raise ValueError(f"attraction {attraction_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> MagnetismSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_magnetism`` is the mean magnetism score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``MagnetismAxis`` among
        those readings, or ATTRACTION if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_magnetism``.
        ``attraction_count`` is the number of attraction events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_magnetism = sum(
                    r.magnetism_score for r in recent
                ) / len(recent)
            else:
                avg_magnetism = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_magnetism)
            attraction_count = len(
                self._agent_attractions_locked(agent_id)
            )

            snapshot = MagnetismSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_magnetism=round(avg_magnetism, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                attraction_count=attraction_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MagnetismSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> MagnetismSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Alignment Plans ────────────────────────────────────────────

    def plan_alignment(
        self,
        agent_id: str,
        strategy: Any,
        target_magnetism: float,
        rationale: str,
    ) -> AlignmentPlan:
        """Record an alignment plan for an agent and return it.

        ``strategy`` may be passed as a ``MagnetismStrategy`` member
        or its string name/value. ``target_magnetism`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured magnetism.
        """
        with self._lock:
            plan = AlignmentPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(MagnetismStrategy, strategy),
                target_magnetism=_clamp(target_magnetism, 0.0, 1.0),
                rationale=str(rationale),
                created_at=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AlignmentPlan]:
        """Return alignment plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> AlignmentPlan:
        """Retrieve an alignment plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Saturation Records ────────────────────────────────────────

    def record_saturation(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> SaturationRecord:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``MagnetismStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        orient", "sudden saturation", "deliberate amplification"). The
        saturation record is stored and returned; the agent's cached
        profile is invalidated.

        Saturation records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = SaturationRecord(
                saturation_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(MagnetismStage, from_stage),
                to_stage=_resolve_enum(MagnetismStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._saturations.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_saturations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SaturationRecord]:
        """Return saturation records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all saturations are considered;
        otherwise only saturations for that agent are returned. The
        most recently recorded ``limit`` saturation records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                saturations = self._agent_saturations_locked(agent_id)
            else:
                saturations = []
                for agent_saturations in self._saturations.values():
                    saturations.extend(agent_saturations)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return saturations[-n:] if n else []

    def get_saturation(self, saturation_id: str) -> SaturationRecord:
        """Retrieve a saturation record by id.

        Raises ``ValueError`` if no saturation record exists with that
        id.
        """
        with self._lock:
            for agent_saturations in self._saturations.values():
                for record in agent_saturations:
                    if record.saturation_id == saturation_id:
                        return record
        raise ValueError(
            f"saturation record {saturation_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> MagnetismProfile:
        """Return the agent's magnetism profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, attractions, snapshots, or
        saturations change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``MagnetismProfile``
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
    ) -> MagnetismProfile:
        """Refresh and optionally override fields of an agent's magnetism profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``MagnetismProfile`` field names) are applied. Accepted
        overrides: ``avg_magnetism`` (float), ``dominant_axis``
        (``MagnetismAxis``), ``dominant_regime``
        (``MagnetismRegime``), ``total_readings``,
        ``total_attractions``, ``total_saturations`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_magnetism":
                    try:
                        profile.avg_magnetism = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            MagnetismAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            MagnetismRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_attractions",
                    "total_saturations",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[MagnetismProfile]:
        """Return all stored magnetism profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> MagnetismStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, attractions, snapshots, and saturations.
        Scalar totals are the counts of each record type.
        ``avg_magnetism`` is the mean magnetism score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        FERROMAGNETIC when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        magnetism via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._attractions.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._saturations.keys())

            total_readings = 0
            magnetism_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    magnetism_sum += reading.magnetism_score
            avg_magnetism = (
                round(magnetism_sum / total_readings, 4) if total_readings else 0.0
            )

            total_attractions = sum(
                len(agent_attractions)
                for agent_attractions in self._attractions.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_saturations = sum(
                len(agent_saturations)
                for agent_saturations in self._saturations.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average magnetism so the stats
                # reflect real state rather than the default
                # FERROMAGNETIC.
                dominant_regime = _determine_regime(avg_magnetism)
            else:
                dominant_regime = MagnetismRegime.FERROMAGNETIC

            return MagnetismStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_attractions=total_attractions,
                total_snapshots=total_snapshots,
                total_saturations=total_saturations,
                avg_magnetism=avg_magnetism,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveMagnetism] = None
_engine_lock = threading.Lock()


def get_magnetism_engine() -> AgentCognitiveMagnetism:
    """Get or create the singleton ``AgentCognitiveMagnetism`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveMagnetism()
    return _engine


def reset_magnetism_engine() -> None:
    """Reset the singleton ``AgentCognitiveMagnetism`` instance.

    Drops the reference to the current engine so the next
    ``get_magnetism_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
