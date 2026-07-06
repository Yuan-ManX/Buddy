from __future__ import annotations

"""Agent Cognitive Canopy Engine — modeling layers of cognitive shelter and reach

How concepts grow upward, branch outward, and layer into a sheltering crown
within the cognitive canopy. A lush agent spreads a wide canopy that shelters
many concepts beneath its reach; a sparse agent's concepts barely leaf.
Distinct from depth, density, reach, exposure, and rootedness.
Core capabilities: axis tracking, growth sources, canopy strategies, season stages.

Architecture:
  AgentCognitiveCanopy (singleton)
  ├── CanopyReading      (one observation of canopy on one axis)
  ├── LeafRecord         (one leaf event that changed canopy)
  ├── CanopySnapshot     (aggregate canopy state for one agent)
  ├── CanopyPlan         (a plan to shape the canopy with a strategy)
  ├── SeasonShift        (one stage transition in the season lifecycle)
  ├── CanopyProfile      (per-agent aggregate canopy tendencies)
  └── CanopyStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/leaf/etc.

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
    engine with a ``NaN`` or ``None`` canopy. A low-side default is
    safer than a mid-range one for canopy-like quantities where a
    spurious high reading would inflate the perceived canopy and
    push the agent's regime toward MAJESTIC.
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
    real season intervals and leaf magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    branching may apply a large effective leaf.
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
    against member values (e.g. ``"sparse"``) and then against
    member names (e.g. ``"SPARSE"``), so callers may pass either
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


def _determine_regime(avg_canopy: float) -> "CanopyRegime":
    """Classify a canopy regime from the average canopy score.

    The average canopy is clamped to [0, 1] where higher means a
    more layered, sheltering posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is SPARSE
    (few leaves, little shelter); below 0.35 it is SPROUTING
    (beginning to grow, only under external nurturing); below 0.55 it
    is SPREADING (widening reach, retains foliage); below 0.75 it is
    DENSE (most layers thickly intertwined); below 0.9 it is LUSH
    (richly foliaged, little room for more); otherwise it is MAJESTIC
    (perfectly crowned layering).
    """
    avg = _clamp(avg_canopy, 0.0, 1.0)
    if avg < 0.15:
        return CanopyRegime.SPARSE
    if avg < 0.35:
        return CanopyRegime.SPROUTING
    if avg < 0.55:
        return CanopyRegime.SPREADING
    if avg < 0.75:
        return CanopyRegime.DENSE
    if avg < 0.9:
        return CanopyRegime.LUSH
    return CanopyRegime.MAJESTIC


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CanopyAxis(str, Enum):
    """The axis along which a canopy reading is taken.

    Each axis names a different dimension of the agent's cognitive
    canopy whose growth can be measured. TRUNK is the central support
    of a concept. BRANCH is the outward extension of a concept.
    LEAF is the surface exposure of a concept. CROWN is the upper
    reach of a concept. ROOT is the grounded anchor of a concept.
    CANOPY is the overall layering across the agent's concepts.
    """
    TRUNK = "trunk"      # central support
    BRANCH = "branch"    # outward extension
    LEAF = "leaf"        # surface exposure
    CROWN = "crown"      # upper reach
    ROOT = "root"        # grounded anchor
    CANOPY = "canopy"    # overall layering


class CanopyRegime(str, Enum):
    """The regime an agent's canopy occupies, classified by canopy.

    Ranges from SPARSE (few leaves, little shelter) through SPROUTING
    (beginning to grow, only under external nurturing), SPREADING
    (widening reach, retains foliage), DENSE (most layers thickly
    intertwined), and LUSH (richly foliaged, little room for more) to
    MAJESTIC (perfectly crowned layering). The regime is derived from
    the average canopy across the agent's readings via
    ``_determine_regime``.
    """
    SPARSE = "sparse"            # few leaves, little shelter
    SPROUTING = "sprouting"      # beginning to grow
    SPREADING = "spreading"      # widening reach
    DENSE = "dense"              # thickly layered
    LUSH = "lush"                # richly foliaged
    MAJESTIC = "majestic"        # fully crowned


class CanopySource(str, Enum):
    """A source that supplies the growth within the canopy.

    Each source names a different origin of the growth within the
    canopy. SUNLIGHT grows from energy above. WATER grows from
    sustaining flow. SOIL grows from grounded nourishment. WIND grows
    from dispersing force. SEASON grows from cyclical timing.
    SYMBIOSIS grows from mutual support. A canopy reading records
    which source supplies the growth on the measured axis, and a leaf
    record records which source drove a change.
    """
    SUNLIGHT = "sunlight"    # energy from above
    WATER = "water"          # sustaining flow
    SOIL = "soil"            # grounded nourishment
    WIND = "wind"            # dispersing force
    SEASON = "season"        # cyclical timing
    SYMBIOSIS = "symbiosis"  # mutual support


class CanopyStrategy(str, Enum):
    """Strategy for shaping the canopy deliberately.

    GROW extends concepts upward. BRANCH spreads concepts outward.
    SHELTER protects concepts beneath. SHED releases concepts' leaves.
    ROOT anchors concepts deeper. REACH extends concepts further. Each
    strategy is suited to a different canopy condition, from
    counteracting a sparse canopy to releasing a lush one.
    """
    GROW = "grow"        # extend upward
    BRANCH = "branch"    # spread outward
    SHELTER = "shelter"  # protect beneath
    SHED = "shed"        # release leaves
    ROOT = "root"        # anchor deeper
    REACH = "reach"      # extend further


class CanopyStage(str, Enum):
    """The lifecycle stage of an agent's canopy-formation process.

    SEED is the state of no growth yet. SPROUT is the phase of first
    emergence. SAPLING is the state in which the young canopy is
    growing. GROWING is the state of actively extending. MATURE is
    the state of full formation. CANOPY is the final state at which
    the crown is fully layered and unresponsive to new input. The
    engine records transitions between stages as SeasonShift entries.
    """
    SEED = "seed"        # not yet sprouted
    SPROUT = "sprout"    # first emergence
    SAPLING = "sapling"  # young and growing
    GROWING = "growing"  # actively extending
    MATURE = "mature"    # fully formed
    CANOPY = "canopy"    # layered crown complete


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CanopyReading:
    """One observation of canopy on a particular axis.

    ``axis`` is the ``CanopyAxis`` the reading is taken on.
    ``canopy_score`` in [0, 1] measures how lush the agent is on that
    axis — 0 means fully sparse, 1 means fully majestic.
    ``source`` is the ``CanopySource`` supplying the growth.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: CanopyAxis
    canopy_score: float    # 0..1, higher = more lush
    source: CanopySource
    intensity: float       # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CanopyAxis, self.axis),
            "canopy_score": self.canopy_score,
            "source": _enum_value(CanopySource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class LeafRecord:
    """One leaf event that changed the canopy on an axis.

    ``axis`` is the ``CanopyAxis`` on which the leaf occurred.
    ``source`` is the ``CanopySource`` that drove the change.
    ``before_score`` in [0, 1] is the canopy before the event;
    ``after_score`` in [0, 1] is the canopy after.
    ``leaf_magnitude`` in [0, ∞) measures how strong the leaf was.
    ``notes`` is an optional free-form annotation.
    """
    leaf_id: str
    agent_id: str
    axis: CanopyAxis
    source: CanopySource
    before_score: float        # 0..1, canopy before leaf
    after_score: float         # 0..1, canopy after leaf
    leaf_magnitude: float      # 0..inf, strength of leaf
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this leaf record to a plain dict, expanding enums via ``.value``."""
        return {
            "leaf_id": self.leaf_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CanopyAxis, self.axis),
            "source": _enum_value(CanopySource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "leaf_magnitude": self.leaf_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CanopySnapshot:
    """Aggregate canopy state for one agent at one moment.

    ``avg_canopy`` in [0, 1] is the mean canopy score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``CanopyAxis`` among those readings, or TRUNK if
    none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_canopy``. ``leaf_count`` is the number of leaf events
    recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_canopy: float
    dominant_axis: CanopyAxis
    regime: CanopyRegime
    leaf_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_canopy": self.avg_canopy,
            "dominant_axis": _enum_value(CanopyAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CanopyRegime, self.regime),
            "regime": _enum_value(CanopyRegime, self.regime),
            "leaf_count": self.leaf_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CanopyPlan:
    """A plan to shape the canopy with a strategy.

    ``strategy`` is the ``CanopyStrategy`` chosen.
    ``target_canopy`` in [0, 1] is the canopy the plan aims to reach.
    ``rationale`` explains why this strategy was chosen for this
    agent's canopy condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current canopy — callers who need that should
    take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: CanopyStrategy
    target_canopy: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(CanopyStrategy, self.strategy),
            "target_canopy": self.target_canopy,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class SeasonShift:
    """One record of a stage transition in the season lifecycle.

    ``from_stage`` is the ``CanopyStage`` the agent was in before the
    transition. ``to_stage`` is the ``CanopyStage`` it moved to.
    ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow sprout",
    "sudden lushness", "deliberate branching").
    """
    shift_id: str
    agent_id: str
    from_stage: CanopyStage
    to_stage: CanopyStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this season shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(CanopyStage, self.from_stage),
            "to_stage": _enum_value(CanopyStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class CanopyProfile:
    """Per-agent aggregate canopy tendencies.

    ``avg_canopy`` in [0, 1] is the mean canopy score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``CanopyAxis`` among the agent's readings, or TRUNK if
    none. ``dominant_regime`` is derived via ``_determine_regime``
    from ``avg_canopy``. ``total_readings``, ``total_leafs``, and
    ``total_shifts`` are the counts of each record type for the
    agent. ``updated_at`` is the timestamp at which the profile was
    last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_canopy: float = 0.0
    dominant_axis: CanopyAxis = CanopyAxis.TRUNK
    dominant_regime: CanopyRegime = CanopyRegime.SPREADING
    total_readings: int = 0
    total_leafs: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_canopy": self.avg_canopy,
            "dominant_axis": _enum_value(CanopyAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CanopyRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_leafs": self.total_leafs,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class CanopyStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_canopy`` is the mean canopy score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or SPREADING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_leafs: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_canopy: float = 0.0
    dominant_regime: CanopyRegime = CanopyRegime.SPREADING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_leafs": self.total_leafs,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_canopy": self.avg_canopy,
            "dominant_regime": _enum_value(CanopyRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCanopy:
    """Thread-safe engine that models an agent's cognitive canopy.

    The engine holds six stores: ``_readings`` (CanopyReading lists
    keyed by agent_id), ``_leafs`` (LeafRecord lists keyed by
    agent_id), ``_snapshots`` (CanopySnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of CanopyPlan), ``_shifts``
    (SeasonShift lists keyed by agent_id), and ``_profiles``
    (CanopyProfile keyed by agent_id, cached and invalidated on
    mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The canopy model is deliberately heuristic: canopy scores and
    intensities are caller-supplied observations; canopy regimes are
    banded from the average canopy; dominant axes are computed by
    mode; stage transitions are recorded as observed. These
    heuristics are transparent and auditable rather than learned,
    which keeps the engine deterministic.

    The engine is intentionally agnostic about how canopy is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure canopy itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, leafs, snapshots, or shifts change, so
    ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose canopy scores feed into
    # a snapshot's average canopy. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current canopy posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty canopy engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[CanopyReading]] = {}
        self._leafs: Dict[str, List[LeafRecord]] = {}
        self._snapshots: Dict[str, List[CanopySnapshot]] = {}
        self._plans: List[CanopyPlan] = []
        self._shifts: Dict[str, List[SeasonShift]] = {}
        self._profiles: Dict[str, CanopyProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_canopy_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._leafs.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[CanopyReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_leafs_locked(
        self, agent_id: str
    ) -> List[LeafRecord]:
        """Return one agent's leaf records in insertion order. Caller holds the lock."""
        return list(self._leafs.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[CanopySnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[CanopyPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[SeasonShift]:
        """Return one agent's season shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[CanopyReading]
    ) -> CanopyAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns TRUNK if the list is empty,
        since TRUNK is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return CanopyAxis.TRUNK
        counts: Counter = Counter()
        first_seen_order: Dict[CanopyAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: CanopyAxis = readings[0].axis
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
        self, profiles: List[CanopyProfile]
    ) -> CanopyRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns SPREADING if the list is empty, since SPREADING is
        the default regime — the band that represents a normally
        functioning cognitive canopy that is widening its reach
        without being dense, neither sparse nor majestic. Caller
        holds the lock.
        """
        if not profiles:
            return CanopyRegime.SPREADING
        counts: Dict[CanopyRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> CanopyProfile:
        """Aggregate an agent's readings, leafs, and shifts into a profile.

        See ``CanopyProfile`` for field semantics. ``avg_canopy`` is
        the mean canopy score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent ``CanopyAxis``
        among the agent's readings, or TRUNK if none.
        ``dominant_regime`` is derived via ``_determine_regime`` from
        ``avg_canopy``. ``total_readings``, ``total_leafs``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        leafs = self._agent_leafs_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_canopy = sum(
                r.canopy_score for r in readings
            ) / len(readings)
        else:
            avg_canopy = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_canopy)

        return CanopyProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_canopy=round(avg_canopy, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_leafs=len(leafs),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Canopy Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        canopy_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> CanopyReading:
        """Record a canopy reading for an agent and return it.

        ``axis`` may be passed as a ``CanopyAxis`` member or its
        string name/value. ``canopy_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``CanopySource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = CanopyReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CanopyAxis, axis),
                canopy_score=_clamp(canopy_score, 0.0, 1.0),
                source=_resolve_enum(CanopySource, source),
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
    ) -> List[CanopyReading]:
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

    def get_reading(self, reading_id: str) -> CanopyReading:
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

    # ── Leaf Records ────────────────────────────────────────────

    def record_leaf(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        leaf_magnitude: float,
        notes: Optional[str] = None,
    ) -> LeafRecord:
        """Record a leaf event for an agent and return it.

        ``axis`` may be passed as a ``CanopyAxis`` member or its
        string name/value. ``source`` may be passed as a
        ``CanopySource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``leaf_magnitude`` is clamped to [0, ∞). The leaf is stored
        and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            record = LeafRecord(
                leaf_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CanopyAxis, axis),
                source=_resolve_enum(CanopySource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                leaf_magnitude=_clamp_positive_ms(
                    leaf_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._leafs.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_leafs(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LeafRecord]:
        """Return leaf records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all leafs are considered;
        otherwise only leafs for that agent are returned. The most
        recently recorded ``limit`` leafs are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                leafs = self._agent_leafs_locked(agent_id)
            else:
                leafs = []
                for agent_leafs in self._leafs.values():
                    leafs.extend(agent_leafs)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return leafs[-n:] if n else []

    def get_leaf(self, leaf_id: str) -> LeafRecord:
        """Retrieve a leaf record by id.

        Raises ``ValueError`` if no leaf exists with that id.
        """
        with self._lock:
            for agent_leafs in self._leafs.values():
                for leaf in agent_leafs:
                    if leaf.leaf_id == leaf_id:
                        return leaf
        raise ValueError(f"leaf {leaf_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CanopySnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_canopy`` is the mean canopy score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``CanopyAxis`` among those readings, or TRUNK if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_canopy``. ``leaf_count`` is the number of leaf events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_canopy = sum(
                    r.canopy_score for r in recent
                ) / len(recent)
            else:
                avg_canopy = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_canopy)
            leaf_count = len(
                self._agent_leafs_locked(agent_id)
            )

            snapshot = CanopySnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_canopy=round(avg_canopy, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                leaf_count=leaf_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CanopySnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> CanopySnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Canopy Plans ────────────────────────────────────────────

    def plan_leaf(
        self,
        agent_id: str,
        strategy: Any,
        target_canopy: float,
        rationale: str,
    ) -> CanopyPlan:
        """Record a canopy plan for an agent and return it.

        ``strategy`` may be passed as a ``CanopyStrategy`` member or
        its string name/value. ``target_canopy`` is clamped to [0, 1].
        ``rationale`` explains why this strategy was chosen. The plan
        is stored in a flat list (not keyed by agent, since plans
        are forward-looking interventions rather than measurements of
        state) and returned. The agent's cached profile is not
        invalidated, since a plan does not change the agent's
        measured canopy.
        """
        with self._lock:
            plan = CanopyPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(CanopyStrategy, strategy),
                target_canopy=_clamp(target_canopy, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CanopyPlan]:
        """Return canopy plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> CanopyPlan:
        """Retrieve a canopy plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Season Shift Records ────────────────────────────────────

    def record_season_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> SeasonShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``CanopyStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        sprout", "sudden lushness", "deliberate branching"). The
        season shift record is stored and returned; the agent's
        cached profile is invalidated.

        Season shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = SeasonShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(CanopyStage, from_stage),
                to_stage=_resolve_enum(CanopyStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_season_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SeasonShift]:
        """Return season shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all shifts are considered;
        otherwise only shifts for that agent are returned. The most
        recently recorded ``limit`` season shift records are
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

    def get_season_shift(self, shift_id: str) -> SeasonShift:
        """Retrieve a season shift record by id.

        Raises ``ValueError`` if no season shift record exists with
        that id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"season shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CanopyProfile:
        """Return the agent's canopy profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, leafs, snapshots, or shifts
        change. If the agent has data but no profile yet, the
        profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``CanopyProfile``
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
    ) -> CanopyProfile:
        """Refresh and optionally override fields of an agent's canopy profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``CanopyProfile`` field names) are applied. Accepted
        overrides: ``avg_canopy`` (float), ``dominant_axis``
        (``CanopyAxis``), ``dominant_regime``
        (``CanopyRegime``), ``total_readings``, ``total_leafs``,
        ``total_shifts`` (int). Enum-valued overrides may be passed
        as the enum member or its string name/value. Unknown keys
        are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_canopy":
                    try:
                        profile.avg_canopy = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            CanopyAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            CanopyRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_leafs",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CanopyProfile]:
        """Return all stored canopy profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> CanopyStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, leafs, snapshots, and shifts. Scalar
        totals are the counts of each record type. ``avg_canopy`` is
        the mean canopy score across all readings, or 0.0 when none
        exist. ``dominant_regime`` is the most frequent regime
        across all cached profiles, or SPREADING when none exist.
        When no profiles exist but readings do, the dominant regime
        is derived from the average canopy via ``_determine_regime``
        so the stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._leafs.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            canopy_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    canopy_sum += reading.canopy_score
            avg_canopy = (
                round(canopy_sum / total_readings, 4) if total_readings else 0.0
            )

            total_leafs = sum(
                len(agent_leafs)
                for agent_leafs in self._leafs.values()
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
                # the regime from the average canopy so the stats
                # reflect real state rather than the default
                # SPREADING.
                dominant_regime = _determine_regime(avg_canopy)
            else:
                dominant_regime = CanopyRegime.SPREADING

            return CanopyStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_leafs=total_leafs,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_canopy=avg_canopy,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCanopy] = None
_engine_lock = threading.Lock()


def get_canopy_engine() -> AgentCognitiveCanopy:
    """Get or create the singleton ``AgentCognitiveCanopy`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveCanopy()
    return _engine


def reset_canopy_engine() -> None:
    """Reset the singleton ``AgentCognitiveCanopy`` instance.

    Drops the reference to the current engine so the next
    ``get_canopy_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
