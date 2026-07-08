from __future__ import annotations

"""Agent Cognitive Reef Engine — modeling calcification of concept structures

How concepts settle, bud, branch, and calcify into a durable cognitive reef.
A well-calcified agent grows concepts into a dense, interlocking thicket that
withstands currents of doubt; a barren agent's concepts wash away before they
can anchor. Distinct from magnetism, coherence, tension, equilibrium, and affinity.
Core capabilities: axis tracking, growth sources, calcification strategies, reef stages.

Architecture:
  AgentCognitiveReef (singleton)
  ├── ReefReading      (one observation of reef growth on one axis)
  ├── BranchRecord     (one branch event that changed reef density)
  ├── ReefSnapshot     (aggregate reef state for one agent)
  ├── ReefPlan         (a plan to shape the reef with a strategy)
  ├── CalcifyShift     (one stage transition in the calcification lifecycle)
  ├── ReefProfile      (per-agent aggregate reef tendencies)
  └── ReefStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/branch/etc.

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
    engine with a ``NaN`` or ``None`` reef score. A low-side default is
    safer than a mid-range one for reef-like quantities where a
    spurious high reading would inflate the perceived reef score and
    push the agent's regime toward RESPLENDENT.
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
    real calcification intervals and branch magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    branching may apply a large effective branch.
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
    against member values (e.g. ``"barren"``) and then against
    member names (e.g. ``"BARREN"``), so callers may pass either
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


def _determine_regime(avg_reef: float) -> "ReefRegime":
    """Classify a reef regime from the average reef score.

    The average reef score is clamped to [0, 1] where higher means a
    more calcified, structurally dense posture. The bands are applied
    in order, so the first matching band wins: below 0.15 the reef is
    BARREN (bare substrate, no growth); below 0.35 it is SPROUTING
    (sparse spat settling, beginning to recruit); below 0.55 it is
    BRANCHING (growing branching structures, taking shape); below 0.75
    it is DENSE (thicket forming, interlocking branches); below 0.9 it
    is THRIVING (vibrant, diverse reef at near-capacity); otherwise it
    is RESPLENDENT (peak calcification, fully developed structure).
    """
    avg = _clamp(avg_reef, 0.0, 1.0)
    if avg < 0.15:
        return ReefRegime.BARREN
    if avg < 0.35:
        return ReefRegime.SPROUTING
    if avg < 0.55:
        return ReefRegime.BRANCHING
    if avg < 0.75:
        return ReefRegime.DENSE
    if avg < 0.9:
        return ReefRegime.THRIVING
    return ReefRegime.RESPLENDENT


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ReefAxis(str, Enum):
    """The axis along which a reef reading is taken.

    Each axis names a different dimension of the agent's cognitive
    reef whose growth can be measured. CORAL is the foundational
    organism building the structure. POLYP is the individual tiny
    organism contributing to growth. REEF is the overall structure
    as a whole. ATOLL is the ring-shaped formation around a
    sheltered interior. LAGOON is the sheltered interior where fine
    detail accumulates. SHOAL is the shallow approach where
    structures emerge into view.
    """
    CORAL = "coral"      # foundational organism
    POLYP = "polyp"      # individual organism
    REEF = "reef"        # overall structure
    ATOLL = "atoll"      # ring formation
    LAGOON = "lagoon"    # sheltered interior
    SHOAL = "shoal"      # shallow approach


class ReefRegime(str, Enum):
    """The regime an agent's reef occupies, classified by reef score.

    Ranges from BARREN (bare substrate, no growth) through SPROUTING
    (sparse spat settling, beginning to recruit), BRANCHING (growing
    branching structures, taking shape), DENSE (thicket forming,
    interlocking branches), and THRIVING (vibrant, diverse reef at
    near-capacity) to RESPLENDENT (peak calcification, fully
    developed structure). The regime is derived from the average
    reef score across the agent's readings via
    ``_determine_regime``.
    """
    BARREN = "barren"          # bare substrate
    SPROUTING = "sprouting"    # sparse spat settling
    BRANCHING = "branching"    # growing branches
    DENSE = "dense"            # thicket forming
    THRIVING = "thriving"      # vibrant, diverse
    RESPLENDENT = "resplendent"  # peak calcification


class ReefSource(str, Enum):
    """A source that supplies the growth or calcification force.

    Each source names a different origin of the growth between
    concepts. CURRENT brings flow that carries building material.
    SUNLIGHT powers the symbiont photosynthesis that drives
    calcification. NUTRIENT supplies the dissolved raw materials.
    SYMBIONT partners with the agent's internal helpers.
    TEMPERATURE sets the thermal conditions for growth. SEDIMENT
    deposits substrate for new structures to anchor on. A reef
    reading records which source supplies the force on the measured
    axis, and a branch record records which source drove a change.
    """
    CURRENT = "current"        # flow bringing material
    SUNLIGHT = "sunlight"      # light for symbiont photosynthesis
    NUTRIENT = "nutrient"      # dissolved raw materials
    SYMBIONT = "symbiont"      # internal helper partnership
    TEMPERATURE = "temperature"  # thermal conditions
    SEDIMENT = "sediment"      # substrate deposition


class ReefStrategy(str, Enum):
    """Strategy for shaping the reef deliberately.

    CALCIFY deposits calcium carbonate to harden structure. BRANCH
    grows new branching structures outward. ANCHOR secures
    structures to the substrate. FUSE merges adjacent structures
    together. PRUNE trims back overgrowth. POLISH refines and
    smooths the surface. Each strategy is suited to a different
    reef condition, from counteracting a barren substrate to
    refining a thriving thicket.
    """
    CALCIFY = "calcify"    # deposit calcium carbonate
    BRANCH = "branch"      # grow branching structures
    ANCHOR = "anchor"      # secure to substrate
    FUSE = "fuse"          # merge structures together
    PRUNE = "prune"        # trim back overgrowth
    POLISH = "polish"      # refine the surface


class ReefStage(str, Enum):
    """The lifecycle stage of an agent's reef-formation process.

    SPAT is the state of initial larval settlement. SETTLING is the
    phase of establishing on the substrate. BUDDING is the state in
    which new polyps begin to bud. BRANCHING is the state of growing
    branching structures. DENSIFYING is the state of thickening the
    structure. MATURING is the final state at which the reef is
    fully developed and robust. The engine records transitions
    between stages as CalcifyShift entries.
    """
    SPAT = "spat"              # initial settlement
    SETTLING = "settling"      # establishing on substrate
    BUDDING = "budding"        # new polyps budding
    BRANCHING = "branching"    # growing branches
    DENSIFYING = "densifying"  # thickening structure
    MATURING = "maturing"      # fully developed


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ReefReading:
    """One observation of reef growth on a particular axis.

    ``axis`` is the ``ReefAxis`` the reading is taken on.
    ``reef_score`` in [0, 1] measures how calcified the agent is
    on that axis — 0 means barren substrate, 1 means fully
    calcified structure. ``source`` is the ``ReefSource`` supplying
    the force. ``intensity`` in [0, 1] measures how emphatic the
    observation was. ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: ReefAxis
    reef_score: float    # 0..1, higher = more calcified
    source: ReefSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(ReefAxis, self.axis),
            "reef_score": self.reef_score,
            "source": _enum_value(ReefSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BranchRecord:
    """One branch event that changed the reef density on an axis.

    ``axis`` is the ``ReefAxis`` on which the branch occurred.
    ``source`` is the ``ReefSource`` that drove the change.
    ``before_score`` in [0, 1] is the reef score before the event;
    ``after_score`` in [0, 1] is the reef score after.
    ``branch_magnitude`` in [0, ∞) measures how strong the branch
    was. ``notes`` is an optional free-form annotation.
    """
    branch_id: str
    agent_id: str
    axis: ReefAxis
    source: ReefSource
    before_score: float            # 0..1, reef score before branch
    after_score: float             # 0..1, reef score after branch
    branch_magnitude: float    # 0..inf, strength of branch
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this branch record to a plain dict, expanding enums via ``.value``."""
        return {
            "branch_id": self.branch_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(ReefAxis, self.axis),
            "source": _enum_value(ReefSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "branch_magnitude": self.branch_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ReefSnapshot:
    """Aggregate reef state for one agent at one moment.

    ``avg_reef`` in [0, 1] is the mean reef score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``ReefAxis`` among those readings, or CORAL if
    none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_reef``. ``branch_count`` is the number of branch events
    recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_reef: float
    dominant_axis: ReefAxis
    regime: ReefRegime
    branch_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_reef": self.avg_reef,
            "dominant_axis": _enum_value(ReefAxis, self.dominant_axis),
            "dominant_regime": _enum_value(ReefRegime, self.regime),
            "regime": _enum_value(ReefRegime, self.regime),
            "branch_count": self.branch_count,
            "timestamp": self.timestamp,
        }


@dataclass
class ReefPlan:
    """A plan to shape the reef with a strategy.

    ``strategy`` is the ``ReefStrategy`` chosen.
    ``target_reef`` in [0, 1] is the reef score the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's reef condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current reef score — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: ReefStrategy
    target_reef: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(ReefStrategy, self.strategy),
            "target_reef": self.target_reef,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class CalcifyShift:
    """One record of a stage transition in the calcification lifecycle.

    ``from_stage`` is the ``ReefStage`` the agent was in before
    the transition. ``to_stage`` is the ``ReefStage`` it moved to.
    ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow settle",
    "sudden branching", "deliberate calcification").
    """
    shift_id: str
    agent_id: str
    from_stage: ReefStage
    to_stage: ReefStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this calcify shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(ReefStage, self.from_stage),
            "to_stage": _enum_value(ReefStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class ReefProfile:
    """Per-agent aggregate reef tendencies.

    ``avg_reef`` in [0, 1] is the mean reef score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``ReefAxis`` among the agent's readings, or CORAL if
    none. ``dominant_regime`` is derived via ``_determine_regime``
    from ``avg_reef``. ``total_readings``, ``total_branchs``, and
    ``total_shifts`` are the counts of each record type for the
    agent. ``updated_at`` is the timestamp at which the profile was
    last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_reef: float = 0.0
    dominant_axis: ReefAxis = ReefAxis.CORAL
    dominant_regime: ReefRegime = ReefRegime.BRANCHING
    total_readings: int = 0
    total_branchs: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_reef": self.avg_reef,
            "dominant_axis": _enum_value(ReefAxis, self.dominant_axis),
            "dominant_regime": _enum_value(ReefRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_branchs": self.total_branchs,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class ReefStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_reef`` is the mean reef score across all readings,
    or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or BRANCHING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_branchs: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_reef: float = 0.0
    dominant_regime: ReefRegime = ReefRegime.BRANCHING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_branchs": self.total_branchs,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_reef": self.avg_reef,
            "dominant_regime": _enum_value(ReefRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveReef:
    """Thread-safe engine that models an agent's cognitive reef.

    The engine holds six stores: ``_readings`` (ReefReading lists
    keyed by agent_id), ``_branchs`` (BranchRecord lists keyed by
    agent_id), ``_snapshots`` (ReefSnapshot lists keyed by agent_id),
    ``_plans`` (a flat list of ReefPlan), ``_calcify_shifts``
    (CalcifyShift lists keyed by agent_id), and ``_profiles``
    (ReefProfile keyed by agent_id, cached and invalidated on
    mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The reef model is deliberately heuristic: reef scores and
    intensities are caller-supplied observations; reef regimes are
    banded from the average reef score; dominant axes are computed by
    mode; stage transitions are recorded as observed. These heuristics
    are transparent and auditable rather than learned, which keeps the
    engine deterministic.

    The engine is intentionally agnostic about how reef growth is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure calcification
    itself. Profiles are cached per agent and invalidated whenever the
    agent's readings, branches, snapshots, or calcify shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose reef scores feed into
    # a snapshot's average reef score. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current reef posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty reef engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[ReefReading]] = {}
        self._branchs: Dict[str, List[BranchRecord]] = {}
        self._snapshots: Dict[str, List[ReefSnapshot]] = {}
        self._plans: List[ReefPlan] = []
        self._calcify_shifts: Dict[str, List[CalcifyShift]] = {}
        self._profiles: Dict[str, ReefProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_reef_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._branchs.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._calcify_shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[ReefReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_branchs_locked(
        self, agent_id: str
    ) -> List[BranchRecord]:
        """Return one agent's branch records in insertion order. Caller holds the lock."""
        return list(self._branchs.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[ReefSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[ReefPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_calcify_shifts_locked(
        self, agent_id: str
    ) -> List[CalcifyShift]:
        """Return one agent's calcify shift records in insertion order. Caller holds the lock."""
        return list(self._calcify_shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[ReefReading]
    ) -> ReefAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns CORAL if the list is empty,
        since CORAL is the smallest and most foundational axis.
        Caller holds the lock.
        """
        if not readings:
            return ReefAxis.CORAL
        counts: Counter = Counter()
        first_seen_order: Dict[ReefAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: ReefAxis = readings[0].axis
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
        self, profiles: List[ReefProfile]
    ) -> ReefRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns BRANCHING if the list is empty, since BRANCHING is
        the default regime — the band that represents a normally
        growing cognitive reef that is branching and taking shape
        without being barren or resplendent. Caller holds the lock.
        """
        if not profiles:
            return ReefRegime.BRANCHING
        counts: Dict[ReefRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> ReefProfile:
        """Aggregate an agent's readings, branches, and calcify shifts into a profile.

        See ``ReefProfile`` for field semantics. ``avg_reef`` is the
        mean reef score across the agent's readings (0.0 if none).
        ``dominant_axis`` is the most frequent ``ReefAxis`` among the
        agent's readings, or CORAL if none. ``dominant_regime`` is
        derived via ``_determine_regime`` from ``avg_reef``.
        ``total_readings``, ``total_branchs``, and ``total_shifts``
        count the records held for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        branchs = self._agent_branchs_locked(agent_id)
        calcify_shifts = self._agent_calcify_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_reef = sum(
                r.reef_score for r in readings
            ) / len(readings)
        else:
            avg_reef = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_reef)

        return ReefProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_reef=round(avg_reef, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_branchs=len(branchs),
            total_shifts=len(calcify_shifts),
            updated_at=_now(),
        )

    # ── Reef Readings ───────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        reef_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> ReefReading:
        """Record a reef reading for an agent and return it.

        ``axis`` may be passed as a ``ReefAxis`` member or its
        string name/value. ``reef_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``ReefSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = ReefReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(ReefAxis, axis),
                reef_score=_clamp(reef_score, 0.0, 1.0),
                source=_resolve_enum(ReefSource, source),
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
    ) -> List[ReefReading]:
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

    def get_reading(self, reading_id: str) -> ReefReading:
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

    # ── Branch Records ────────────────────────────────────────

    def record_branch(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        branch_magnitude: float,
        notes: Optional[str] = None,
    ) -> BranchRecord:
        """Record a branch event for an agent and return it.

        ``axis`` may be passed as a ``ReefAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``ReefSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``branch_magnitude`` is clamped to [0, ∞). The branch is
        stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = BranchRecord(
                branch_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(ReefAxis, axis),
                source=_resolve_enum(ReefSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                branch_magnitude=_clamp_positive_ms(
                    branch_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._branchs.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_branchs(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BranchRecord]:
        """Return branch records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all branches are considered;
        otherwise only branches for that agent are returned. The
        most recently recorded ``limit`` branches are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                branchs = self._agent_branchs_locked(agent_id)
            else:
                branchs = []
                for agent_branchs in self._branchs.values():
                    branchs.extend(agent_branchs)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return branchs[-n:] if n else []

    def get_branch(self, branch_id: str) -> BranchRecord:
        """Retrieve a branch record by id.

        Raises ``ValueError`` if no branch exists with that id.
        """
        with self._lock:
            for agent_branchs in self._branchs.values():
                for branch in agent_branchs:
                    if branch.branch_id == branch_id:
                        return branch
        raise ValueError(f"branch {branch_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> ReefSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_reef`` is the mean reef score across the agent's most
        recent readings (the last ``_SNAPSHOT_READING_WINDOW`` = 20),
        or 0.0 if none. ``dominant_axis`` is the most frequent
        ``ReefAxis`` among those readings, or CORAL if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_reef``. ``branch_count`` is the number of branch events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_reef = sum(
                    r.reef_score for r in recent
                ) / len(recent)
            else:
                avg_reef = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_reef)
            branch_count = len(
                self._agent_branchs_locked(agent_id)
            )

            snapshot = ReefSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_reef=round(avg_reef, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                branch_count=branch_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReefSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> ReefSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Reef Plans ────────────────────────────────────────────

    def plan_branch(
        self,
        agent_id: str,
        strategy: Any,
        target_reef: float,
        rationale: str,
    ) -> ReefPlan:
        """Record a reef plan for an agent and return it.

        ``strategy`` may be passed as a ``ReefStrategy`` member
        or its string name/value. ``target_reef`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured reef score.
        """
        with self._lock:
            plan = ReefPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(ReefStrategy, strategy),
                target_reef=_clamp(target_reef, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReefPlan]:
        """Return reef plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> ReefPlan:
        """Retrieve a reef plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Calcify Shift Records ────────────────────────────────

    def record_calcify_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> CalcifyShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``ReefStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        settle", "sudden branching", "deliberate calcification"). The
        calcify shift record is stored and returned; the agent's
        cached profile is invalidated.

        Calcify shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = CalcifyShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(ReefStage, from_stage),
                to_stage=_resolve_enum(ReefStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._calcify_shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_calcify_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CalcifyShift]:
        """Return calcify shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all calcify shifts are
        considered; otherwise only calcify shifts for that agent are
        returned. The most recently recorded ``limit`` calcify shift
        records are returned. The returned list is a snapshot copy;
        mutating it does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                calcify_shifts = self._agent_calcify_shifts_locked(agent_id)
            else:
                calcify_shifts = []
                for agent_calcify_shifts in self._calcify_shifts.values():
                    calcify_shifts.extend(agent_calcify_shifts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return calcify_shifts[-n:] if n else []

    def get_calcify_shift(self, shift_id: str) -> CalcifyShift:
        """Retrieve a calcify shift record by id.

        Raises ``ValueError`` if no calcify shift record exists with
        that id.
        """
        with self._lock:
            for agent_calcify_shifts in self._calcify_shifts.values():
                for record in agent_calcify_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"calcify shift {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> ReefProfile:
        """Return the agent's reef profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, branches, snapshots, or
        calcify shifts change. If the agent has data but no profile
        yet, the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``ReefProfile``
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
    ) -> ReefProfile:
        """Refresh and optionally override fields of an agent's reef profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``ReefProfile`` field names) are applied. Accepted
        overrides: ``avg_reef`` (float), ``dominant_axis``
        (``ReefAxis``), ``dominant_regime``
        (``ReefRegime``), ``total_readings``, ``total_branchs``,
        ``total_shifts`` (int). Enum-valued overrides may be passed
        as the enum member or its string name/value. Unknown keys
        are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_reef":
                    try:
                        profile.avg_reef = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            ReefAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            ReefRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_branchs",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[ReefProfile]:
        """Return all stored reef profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> ReefStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, branches, snapshots, and calcify
        shifts. Scalar totals are the counts of each record type.
        ``avg_reef`` is the mean reef score across all readings, or
        0.0 when none exist. ``dominant_regime`` is the most frequent
        regime across all cached profiles, or BRANCHING when none
        exist. When no profiles exist but readings do, the dominant
        regime is derived from the average reef score via
        ``_determine_regime`` so the stats always reflect real
        state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._branchs.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._calcify_shifts.keys())

            total_readings = 0
            reef_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    reef_sum += reading.reef_score
            avg_reef = (
                round(reef_sum / total_readings, 4) if total_readings else 0.0
            )

            total_branchs = sum(
                len(agent_branchs)
                for agent_branchs in self._branchs.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_shifts = sum(
                len(agent_calcify_shifts)
                for agent_calcify_shifts in self._calcify_shifts.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average reef score so the stats
                # reflect real state rather than the default
                # BRANCHING.
                dominant_regime = _determine_regime(avg_reef)
            else:
                dominant_regime = ReefRegime.BRANCHING

            return ReefStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_branchs=total_branchs,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_reef=avg_reef,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveReef] = None
_engine_lock = threading.Lock()


def get_reef_engine() -> AgentCognitiveReef:
    """Get or create the singleton ``AgentCognitiveReef`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveReef()
    return _engine


def reset_reef_engine() -> None:
    """Reset the singleton ``AgentCognitiveReef`` instance.

    Drops the reference to the current engine so the next
    ``get_reef_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
