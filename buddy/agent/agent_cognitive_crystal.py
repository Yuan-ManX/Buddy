from __future__ import annotations

"""Agent Cognitive Crystal Engine — how mental structures form, grow, and facet

How concepts nucleate, grow, facet, and cleave within the cognitive lattice.
A crystallized agent holds concepts in a stable lattice with sharp facets; an
amorphous agent's concepts are dissolved and unstructured. Distinct from
magnetism, coherence, tension, equilibrium, and affinity.
Core capabilities: axis tracking, growth sources, crystallization strategies,
lifecycle stages.

Architecture:
  AgentCognitiveCrystal (singleton)
  ├── CrystalReading        (one observation of crystallization on one axis)
  ├── GrowthRecord          (one growth event that changed crystallization)
  ├── CrystalSnapshot       (aggregate crystal state for one agent)
  ├── CrystalPlan           (a plan to grow the lattice with a strategy)
  ├── FacetShift            (one stage transition in the crystallization lifecycle)
  ├── CrystalProfile        (per-agent aggregate crystal tendencies)
  └── CrystalStats          (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/growth/etc.

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
    engine with a ``NaN`` or ``None`` crystallization. A low-side default is
    safer than a mid-range one for crystal-like quantities where a
    spurious high reading would inflate the perceived crystallization and
    push the agent's regime toward PERFECT.
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
    real facet-shift intervals and growth magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    accretion may apply a large effective growth.
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
    against member values (e.g. ``"amorphous"``) and then against
    member names (e.g. ``"AMORPHOUS"``), so callers may pass either
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


def _determine_regime(avg_crystal: float) -> "CrystalRegime":
    """Classify a crystal regime from the average crystal score.

    The average crystal is clamped to [0, 1] where higher means a
    more crystallized, faceted posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is AMORPHOUS
    (no structure, concepts dissolved); below 0.35 it is NUCLEATING
    (beginning to form seeds, weak structure); below 0.55 it is
    CRYSTALLIZING (active growth, structure forming); below 0.75 it is
    CRYSTALLINE (stable lattice, mostly structured); below 0.9 it is
    FACETED (sharp facets, well-defined structure); otherwise it is
    PERFECT (flawlessly faceted, fully structured).
    """
    avg = _clamp(avg_crystal, 0.0, 1.0)
    if avg < 0.15:
        return CrystalRegime.AMORPHOUS
    if avg < 0.35:
        return CrystalRegime.NUCLEATING
    if avg < 0.55:
        return CrystalRegime.CRYSTALLIZING
    if avg < 0.75:
        return CrystalRegime.CRYSTALLINE
    if avg < 0.9:
        return CrystalRegime.FACETED
    return CrystalRegime.PERFECT


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CrystalAxis(str, Enum):
    """The axis along which a crystal reading is taken.

    Each axis names a different dimension of the agent's cognitive
    lattice whose crystallization can be measured. LATTICE is the
    underlying structural grid. FACET is the sharpness of the surface
    faces. GROWTH is the rate of accretion onto the structure.
    CLEAVAGE is the tendency to split along planes. INCLUSION is the
    incorporation of foreign material. HABIT is the overall growth
    form the crystal takes.
    """
    LATTICE = "lattice"    # underlying structural grid
    FACET = "facet"        # sharpness of surface faces
    GROWTH = "growth"      # rate of accretion
    CLEAVAGE = "cleavage"  # tendency to split along planes
    INCLUSION = "inclusion"  # incorporation of foreign material
    HABIT = "habit"        # overall growth form


class CrystalRegime(str, Enum):
    """The regime an agent's crystal occupies, classified by crystallization.

    Ranges from AMORPHOUS (no structure, concepts dissolved) through
    NUCLEATING (beginning to form seeds, weak structure),
    CRYSTALLIZING (active growth, structure forming), CRYSTALLINE
    (stable lattice, mostly structured), and FACETED (sharp facets,
    well-defined structure) to PERFECT (flawlessly faceted, fully
    structured). The regime is derived from the average crystal
    across the agent's readings via ``_determine_regime``.
    """
    AMORPHOUS = "amorphous"        # no structure
    NUCLEATING = "nucleating"      # beginning to form seeds
    CRYSTALLIZING = "crystallizing"  # active growth
    CRYSTALLINE = "crystalline"    # stable lattice
    FACETED = "faceted"            # sharp facets
    PERFECT = "perfect"            # flawlessly faceted


class CrystalSource(str, Enum):
    """A source that supplies the crystallizing force.

    Each source names a different origin of the structural pull on
    concepts. SATURATION drives precipitation from a supersaturated
    solution. PRESSURE compacts concepts into denser structure.
    TEMPERATURE controls the energy available for rearrangement.
    TIME allows slow growth and annealing. IMPURITY seeds nucleation
    at defect sites. SOLUTION provides the medium in which concepts
    dissolve and reprecipitate. A crystal reading records which source
    supplies the force on the measured axis, and a growth record
    records which source drove a change.
    """
    SATURATION = "saturation"  # precipitation from supersaturation
    PRESSURE = "pressure"      # compaction into denser structure
    TEMPERATURE = "temperature"  # energy for rearrangement
    TIME = "time"              # slow growth and annealing
    IMPURITY = "impurity"      # nucleation at defect sites
    SOLUTION = "solution"      # medium for dissolution


class CrystalStrategy(str, Enum):
    """Strategy for growing the lattice deliberately.

    NUCLEATE seeds new crystallization sites. GROW accretes material
    onto existing structure. CLEAVE splits the lattice along planes.
    POLISH refines the facets to sharpness. DOP introduces impurities
    to tune properties. ANNEAL relieves internal stress through
    controlled heating. Each strategy is suited to a different
    crystallization condition, from seeding an amorphous field to
    perfecting a faceted one.
    """
    NUCLEATE = "nucleate"  # seed new crystallization sites
    GROW = "grow"          # accrete onto existing structure
    CLEAVE = "cleave"      # split along planes
    POLISH = "polish"      # refine facets to sharpness
    DOP = "dop"            # introduce impurities
    ANNEAL = "anneal"      # relieve stress through heating


class CrystalStage(str, Enum):
    """The lifecycle stage of an agent's crystallization process.

    DISSOLVED is the state of no structure. SUPERSATURATED is the
    state of being primed for nucleation. NUCLEATING is the phase of
    seed formation. GROWING is the phase of active accretion. FACETED
    is the state with well-defined faces. PERFECT is the final state
    at which the lattice is fully faceted and unresponsive to further
    growth. The engine records transitions between stages as
    FacetShift entries.
    """
    DISSOLVED = "dissolved"          # no structure
    SUPERSATURATED = "supersaturated"  # primed for nucleation
    NUCLEATING = "nucleating"        # seed formation
    GROWING = "growing"              # active accretion
    FACETED = "faceted"              # well-defined faces
    PERFECT = "perfect"              # fully faceted


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CrystalReading:
    """One observation of crystallization on a particular axis.

    ``axis`` is the ``CrystalAxis`` the reading is taken on.
    ``crystal_score`` in [0, 1] measures how crystallized the agent is
    on that axis — 0 means fully dissolved, 1 means perfectly faceted.
    ``source`` is the ``CrystalSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: CrystalAxis
    crystal_score: float    # 0..1, higher = more crystallized
    source: CrystalSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CrystalAxis, self.axis),
            "crystal_score": self.crystal_score,
            "source": _enum_value(CrystalSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class GrowthRecord:
    """One growth event that changed the crystallization on an axis.

    ``axis`` is the ``CrystalAxis`` on which the growth occurred.
    ``source`` is the ``CrystalSource`` that drove the change.
    ``before_score`` in [0, 1] is the crystallization before the event;
    ``after_score`` in [0, 1] is the crystallization after.
    ``growth_magnitude`` in [0, ∞) measures how strong the growth was.
    ``notes`` is an optional free-form annotation.
    """
    growth_id: str
    agent_id: str
    axis: CrystalAxis
    source: CrystalSource
    before_score: float            # 0..1, crystallization before growth
    after_score: float             # 0..1, crystallization after growth
    growth_magnitude: float    # 0..inf, strength of growth
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this growth record to a plain dict, expanding enums via ``.value``."""
        return {
            "growth_id": self.growth_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CrystalAxis, self.axis),
            "source": _enum_value(CrystalSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "growth_magnitude": self.growth_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CrystalSnapshot:
    """Aggregate crystal state for one agent at one moment.

    ``avg_crystal`` in [0, 1] is the mean crystal score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``CrystalAxis`` among those readings, or LATTICE
    if none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_crystal``. ``growth_count`` is the number of growth events
    recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_crystal: float
    dominant_axis: CrystalAxis
    regime: CrystalRegime
    growth_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_crystal": self.avg_crystal,
            "dominant_axis": _enum_value(CrystalAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CrystalRegime, self.regime),
            "regime": _enum_value(CrystalRegime, self.regime),
            "growth_count": self.growth_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CrystalPlan:
    """A plan to grow the lattice with a strategy.

    ``strategy`` is the ``CrystalStrategy`` chosen.
    ``target_crystal`` in [0, 1] is the crystallization the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's crystallization condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current crystallization — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: CrystalStrategy
    target_crystal: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(CrystalStrategy, self.strategy),
            "target_crystal": self.target_crystal,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class FacetShift:
    """One record of a stage transition in the crystallization lifecycle.

    ``from_stage`` is the ``CrystalStage`` the agent was in before
    the transition. ``to_stage`` is the ``CrystalStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow nucleate",
    "sudden facet", "deliberate anneal").
    """
    shift_id: str
    agent_id: str
    from_stage: CrystalStage
    to_stage: CrystalStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this facet shift record to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(CrystalStage, self.from_stage),
            "to_stage": _enum_value(CrystalStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class CrystalProfile:
    """Per-agent aggregate crystal tendencies.

    ``avg_crystal`` in [0, 1] is the mean crystal score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``CrystalAxis`` among the agent's readings, or LATTICE
    if none. ``dominant_regime`` is derived via ``_determine_regime``
    from ``avg_crystal``. ``total_readings``, ``total_growths``, and
    ``total_shifts`` are the counts of each record type for the agent.
    ``updated_at`` is the timestamp at which the profile was last
    computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_crystal: float = 0.0
    dominant_axis: CrystalAxis = CrystalAxis.LATTICE
    dominant_regime: CrystalRegime = CrystalRegime.NUCLEATING
    total_readings: int = 0
    total_growths: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_crystal": self.avg_crystal,
            "dominant_axis": _enum_value(CrystalAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CrystalRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_growths": self.total_growths,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class CrystalStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_crystal`` is the mean crystal score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or NUCLEATING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_growths: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_crystal: float = 0.0
    dominant_regime: CrystalRegime = CrystalRegime.NUCLEATING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_growths": self.total_growths,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_crystal": self.avg_crystal,
            "dominant_regime": _enum_value(CrystalRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCrystal:
    """Thread-safe engine that models an agent's cognitive crystal.

    The engine holds six stores: ``_readings`` (CrystalReading lists
    keyed by agent_id), ``_growths`` (GrowthRecord lists keyed by
    agent_id), ``_snapshots`` (CrystalSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of CrystalPlan),
    ``_shifts`` (FacetShift lists keyed by agent_id), and
    ``_profiles`` (CrystalProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The crystal model is deliberately heuristic: crystal scores
    and intensities are caller-supplied observations; crystal
    regimes are banded from the average crystal; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how crystallization is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure crystallization itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, growths, snapshots, or facet shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose crystal scores feed into
    # a snapshot's average crystal. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current crystal posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty crystal engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[CrystalReading]] = {}
        self._growths: Dict[str, List[GrowthRecord]] = {}
        self._snapshots: Dict[str, List[CrystalSnapshot]] = {}
        self._plans: List[CrystalPlan] = []
        self._shifts: Dict[str, List[FacetShift]] = {}
        self._profiles: Dict[str, CrystalProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_crystal_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._growths.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[CrystalReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_growths_locked(
        self, agent_id: str
    ) -> List[GrowthRecord]:
        """Return one agent's growth records in insertion order. Caller holds the lock."""
        return list(self._growths.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[CrystalSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[CrystalPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[FacetShift]:
        """Return one agent's facet shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[CrystalReading]
    ) -> CrystalAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns LATTICE if the list is
        empty, since LATTICE is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return CrystalAxis.LATTICE
        counts: Counter = Counter()
        first_seen_order: Dict[CrystalAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: CrystalAxis = readings[0].axis
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
        self, profiles: List[CrystalProfile]
    ) -> CrystalRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns NUCLEATING if the list is empty, since
        NUCLEATING is the default regime — the band that
        represents a normally functioning cognitive lattice that
        is forming seeds without being fully faceted, neither
        amorphous nor perfect. Caller holds the lock.
        """
        if not profiles:
            return CrystalRegime.NUCLEATING
        counts: Dict[CrystalRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> CrystalProfile:
        """Aggregate an agent's readings, growths, and facet shifts into a profile.

        See ``CrystalProfile`` for field semantics. ``avg_crystal``
        is the mean crystal score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``CrystalAxis`` among the agent's readings, or LATTICE
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_crystal``.
        ``total_readings``, ``total_growths``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        growths = self._agent_growths_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_crystal = sum(
                r.crystal_score for r in readings
            ) / len(readings)
        else:
            avg_crystal = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_crystal)

        return CrystalProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_crystal=round(avg_crystal, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_growths=len(growths),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Crystal Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        crystal_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> CrystalReading:
        """Record a crystal reading for an agent and return it.

        ``axis`` may be passed as a ``CrystalAxis`` member or its
        string name/value. ``crystal_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``CrystalSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = CrystalReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CrystalAxis, axis),
                crystal_score=_clamp(crystal_score, 0.0, 1.0),
                source=_resolve_enum(CrystalSource, source),
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
    ) -> List[CrystalReading]:
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

    def get_reading(self, reading_id: str) -> CrystalReading:
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

    # ── Growth Records ────────────────────────────────────────

    def record_growth(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        growth_magnitude: float,
        notes: Optional[str] = None,
    ) -> GrowthRecord:
        """Record a growth event for an agent and return it.

        ``axis`` may be passed as a ``CrystalAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``CrystalSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``growth_magnitude`` is clamped to [0, ∞). The growth
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = GrowthRecord(
                growth_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CrystalAxis, axis),
                source=_resolve_enum(CrystalSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                growth_magnitude=_clamp_positive_ms(
                    growth_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._growths.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_growths(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[GrowthRecord]:
        """Return growth records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all growths are considered;
        otherwise only growths for that agent are returned. The
        most recently recorded ``limit`` growths are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                growths = self._agent_growths_locked(agent_id)
            else:
                growths = []
                for agent_growths in self._growths.values():
                    growths.extend(agent_growths)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return growths[-n:] if n else []

    def get_growth(self, growth_id: str) -> GrowthRecord:
        """Retrieve a growth record by id.

        Raises ``ValueError`` if no growth exists with that id.
        """
        with self._lock:
            for agent_growths in self._growths.values():
                for growth in agent_growths:
                    if growth.growth_id == growth_id:
                        return growth
        raise ValueError(f"growth {growth_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CrystalSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_crystal`` is the mean crystal score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``CrystalAxis`` among
        those readings, or LATTICE if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_crystal``.
        ``growth_count`` is the number of growth events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_crystal = sum(
                    r.crystal_score for r in recent
                ) / len(recent)
            else:
                avg_crystal = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_crystal)
            growth_count = len(
                self._agent_growths_locked(agent_id)
            )

            snapshot = CrystalSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_crystal=round(avg_crystal, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                growth_count=growth_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CrystalSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> CrystalSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Crystal Plans ────────────────────────────────────────────

    def plan_growth(
        self,
        agent_id: str,
        strategy: Any,
        target_crystal: float,
        rationale: str,
    ) -> CrystalPlan:
        """Record a crystal plan for an agent and return it.

        ``strategy`` may be passed as a ``CrystalStrategy`` member
        or its string name/value. ``target_crystal`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured crystallization.
        """
        with self._lock:
            plan = CrystalPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(CrystalStrategy, strategy),
                target_crystal=_clamp(target_crystal, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CrystalPlan]:
        """Return crystal plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> CrystalPlan:
        """Retrieve a crystal plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Facet Shift Records ────────────────────────────────────────

    def record_facet_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> FacetShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``CrystalStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        nucleate", "sudden facet", "deliberate anneal"). The
        facet shift record is stored and returned; the agent's cached
        profile is invalidated.

        Facet shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = FacetShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(CrystalStage, from_stage),
                to_stage=_resolve_enum(CrystalStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_facet_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FacetShift]:
        """Return facet shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all facet shifts are considered;
        otherwise only facet shifts for that agent are returned. The
        most recently recorded ``limit`` facet shift records are
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

    def get_facet_shift(self, shift_id: str) -> FacetShift:
        """Retrieve a facet shift record by id.

        Raises ``ValueError`` if no facet shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"facet shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CrystalProfile:
        """Return the agent's crystal profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, growths, snapshots, or facet
        shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``CrystalProfile``
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
    ) -> CrystalProfile:
        """Refresh and optionally override fields of an agent's crystal profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``CrystalProfile`` field names) are applied. Accepted
        overrides: ``avg_crystal`` (float), ``dominant_axis``
        (``CrystalAxis``), ``dominant_regime``
        (``CrystalRegime``), ``total_readings``,
        ``total_growths``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_crystal":
                    try:
                        profile.avg_crystal = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            CrystalAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            CrystalRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_growths",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CrystalProfile]:
        """Return all stored crystal profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> CrystalStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, growths, snapshots, and facet shifts.
        Scalar totals are the counts of each record type.
        ``avg_crystal`` is the mean crystal score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        NUCLEATING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        crystal via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._growths.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            crystal_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    crystal_sum += reading.crystal_score
            avg_crystal = (
                round(crystal_sum / total_readings, 4) if total_readings else 0.0
            )

            total_growths = sum(
                len(agent_growths)
                for agent_growths in self._growths.values()
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
                # the regime from the average crystal so the stats
                # reflect real state rather than the default
                # NUCLEATING.
                dominant_regime = _determine_regime(avg_crystal)
            else:
                dominant_regime = CrystalRegime.NUCLEATING

            return CrystalStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_growths=total_growths,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_crystal=avg_crystal,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCrystal] = None
_engine_lock = threading.Lock()


def get_crystal_engine() -> AgentCognitiveCrystal:
    """Get or create the singleton ``AgentCognitiveCrystal`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveCrystal()
    return _engine


def reset_crystal_engine() -> None:
    """Reset the singleton ``AgentCognitiveCrystal`` instance.

    Drops the reference to the current engine so the next
    ``get_crystal_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
