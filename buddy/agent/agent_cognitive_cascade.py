from __future__ import annotations

"""Agent Cognitive Cascade Engine — thought flow through hierarchical tiers

Thoughts flow through an agent's cognitive tiers like water cascading down,
trickling through layers, pooling, and overflowing when capacity is exceeded.

Core capabilities:
  - Cascade Readings: per-axis flow scores (tier, layer, stream, fall, pool, drain)
  - Flow Records: events that changed cascade with before/after scores
  - Regime Classification: dry, trickle, flowing, cascading, torrent, flood
  - Flow Lifecycle: source → trickling → falling → cascading → pooled → overflow
  - Cascade Plans: strategies to route, accelerate, pool, divert, merge, release
Architecture:
  AgentCognitiveCascade (singleton)
  ├── CascadeReading, FlowRecord         (readings, flow events)
  ├── CascadeSnapshot, CascadePlan       (aggregate state, shaping strategy)
  ├── TierTransition, CascadeProfile     (stage transitions, per-agent)
  └── CascadeStats                       (engine-wide statistics)
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
    """Generate a short unique identifier for a reading/flow/etc.

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
    engine with a ``NaN`` or ``None`` cascade. A low-side default is
    safer than a mid-range one for cascade-like quantities where a
    spurious high reading would inflate the perceived cascade and push
    the agent's regime toward FLOOD.
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
    real transition intervals and flow magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    acceleration may apply a large effective flow.
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
    against member values (e.g. ``"dry"``) and then against member
    names (e.g. ``"DRY"``), so callers may pass either form. This lets
    the public API accept either the symbolic name or the lower-case
    value string from JSON payloads. Raises ``ValueError`` if neither
    matches.
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


def _determine_regime(avg_cascade: float) -> "CascadeRegime":
    """Classify a cascade regime from the average cascade score.

    The average cascade is clamped to [0, 1] where higher means a
    stronger, more voluminous flow posture. The bands are applied in
    order, so the first matching band wins: below 0.15 the agent is DRY
    (no flow, thoughts stuck at the source); below 0.35 it is TRICKLE
    (weak seepage, only the topmost tiers active); below 0.55 it is
    FLOWING (steady moderate flow across most tiers); below 0.75 it is
    CASCADING (strong directed flow, thoughts falling freely); below
    0.9 it is TORRENT (heavy flow near capacity, pools filling fast);
    otherwise it is FLOOD (overflow, thoughts spilling out
    uncontrolled).
    """
    avg = _clamp(avg_cascade, 0.0, 1.0)
    if avg < 0.15:
        return CascadeRegime.DRY
    if avg < 0.35:
        return CascadeRegime.TRICKLE
    if avg < 0.55:
        return CascadeRegime.FLOWING
    if avg < 0.75:
        return CascadeRegime.CASCADING
    if avg < 0.9:
        return CascadeRegime.TORRENT
    return CascadeRegime.FLOOD


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CascadeAxis(str, Enum):
    """The axis along which a cascade reading is taken.

    Each axis names a different dimension of the agent's cognitive
    cascade whose flow can be measured. TIER is a single level in the
    hierarchy. LAYER is a stratum spanning multiple tiers. STREAM is a
    parallel channel of flow. FALL is the drop between two tiers. POOL
    is an accumulation point where thoughts gather. DRAIN is the exit
    point at the bottom of the cascade.
    """
    TIER = "tier"        # a single level in the hierarchy
    LAYER = "layer"      # a stratum spanning multiple tiers
    STREAM = "stream"    # a parallel channel of flow
    FALL = "fall"        # the drop between two tiers
    POOL = "pool"        # an accumulation point
    DRAIN = "drain"      # the exit point at the bottom


class CascadeRegime(str, Enum):
    """The regime an agent's cascade occupies, classified by cascade.

    Ranges from DRY (no flow, thoughts stuck at the source) through
    TRICKLE (weak seepage, only the topmost tiers active), FLOWING
    (steady moderate flow across most tiers), CASCADING (strong
    directed flow, thoughts falling freely), and TORRENT (heavy flow
    near capacity, pools filling fast) to FLOOD (overflow, thoughts
    spilling out uncontrolled). The regime is derived from the average
    cascade across the agent's readings via ``_determine_regime``.
    """
    DRY = "dry"                  # no flow, thoughts stuck at the source
    TRICKLE = "trickle"          # weak seepage, topmost tiers active
    FLOWING = "flowing"          # steady moderate flow across most tiers
    CASCADING = "cascading"      # strong directed flow, thoughts falling freely
    TORRENT = "torrent"          # heavy flow near capacity, pools filling fast
    FLOOD = "flood"              # overflow, thoughts spilling out uncontrolled


class CascadeSource(str, Enum):
    """A source that supplies the force driving the flow.

    Each source names a different origin of the force that moves
    thoughts through the cascade. GRAVITY pulls thoughts down toward
    lower tiers. PRESSURE forces flow when upstream volume builds.
    VOLUME drives flow by sheer quantity of thought. CHANNEL
    constrains flow into a particular path. SLOPE accelerates or
    decelerates flow by the steepness between tiers. OBSTRUCTION
    impedes flow by blocking a channel. A cascade reading records
    which source supplies the force on the measured axis, and a flow
    record records which source drove a change.
    """
    GRAVITY = "gravity"        # pulls thoughts down toward lower tiers
    PRESSURE = "pressure"      # forces flow when upstream volume builds
    VOLUME = "volume"          # drives flow by sheer quantity of thought
    CHANNEL = "channel"        # constrains flow into a particular path
    SLOPE = "slope"            # accelerates/decelerates by steepness
    OBSTRUCTION = "obstruction"  # impedes flow by blocking a channel


class CascadeStrategy(str, Enum):
    """Strategy for shaping the flow deliberately.

    ROUTE directs flow along a chosen channel. ACCELERATE speeds up the
    fall between tiers. POOL deliberately accumulates thoughts at a
    tier. DIVERT redirects flow around an obstruction. MERGE combines
    multiple streams into one. RELEASE lets a pool drain to relieve
    pressure. Each strategy is suited to a different flow condition,
    from counteracting a dry cascade to releasing a flooded one.
    """
    ROUTE = "route"            # direct flow along a chosen channel
    ACCELERATE = "accelerate"  # speed up the fall between tiers
    POOL = "pool"              # deliberately accumulate thoughts at a tier
    DIVERT = "divert"          # redirect flow around an obstruction
    MERGE = "merge"            # combine multiple streams into one
    RELEASE = "release"        # let a pool drain to relieve pressure


class CascadeStage(str, Enum):
    """The lifecycle stage of an agent's cascade-formation process.

    SOURCE is the state of thoughts at the origin, not yet flowing.
    TRICKLING is the phase of slow initial movement. FALLING is the
    state of active descent between tiers. CASCADING is the state of
    strong directed flow. POOLED is the state in which thoughts have
    accumulated at a tier. OVERFLOW is the final state at which
    capacity is exceeded and thoughts spill out uncontrolled. The
    engine records transitions between stages as TierTransition
    entries.
    """
    SOURCE = "source"          # thoughts at the origin, not yet flowing
    TRICKLING = "trickling"    # slow initial movement
    FALLING = "falling"        # active descent between tiers
    CASCADING = "cascading"    # strong directed flow
    POOLED = "pooled"          # thoughts accumulated at a tier
    OVERFLOW = "overflow"      # capacity exceeded, thoughts spilling out


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CascadeReading:
    """One observation of cascade on a particular axis.

    ``axis`` is the ``CascadeAxis`` the reading is taken on.
    ``cascade_score`` in [0, 1] measures how strongly the agent's
    thoughts are flowing on that axis — 0 means fully dry, 1 means
    flooding. ``source`` is the ``CascadeSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: CascadeAxis
    cascade_score: float    # 0..1, higher = more flow
    source: CascadeSource
    intensity: float        # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CascadeAxis, self.axis),
            "cascade_score": self.cascade_score,
            "source": _enum_value(CascadeSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class FlowRecord:
    """One flow event that changed the cascade on an axis.

    ``axis`` is the ``CascadeAxis`` on which the flow occurred.
    ``source`` is the ``CascadeSource`` that drove the change.
    ``before_score`` in [0, 1] is the cascade before the event;
    ``after_score`` in [0, 1] is the cascade after.
    ``flow_magnitude`` in [0, ∞) measures how strong the flow was.
    ``notes`` is an optional free-form annotation.
    """
    flow_id: str
    agent_id: str
    axis: CascadeAxis
    source: CascadeSource
    before_score: float            # 0..1, cascade before flow
    after_score: float             # 0..1, cascade after flow
    flow_magnitude: float          # 0..inf, strength of flow
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this flow record to a plain dict, expanding enums via ``.value``."""
        return {
            "flow_id": self.flow_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CascadeAxis, self.axis),
            "source": _enum_value(CascadeSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "flow_magnitude": self.flow_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CascadeSnapshot:
    """Aggregate cascade state for one agent at one moment.

    ``avg_cascade`` in [0, 1] is the mean cascade score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``CascadeAxis`` among those readings, or TIER if
    none. ``dominant_regime`` is derived via ``_determine_regime`` from
    ``avg_cascade``. ``flow_count`` is the number of flow events
    recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_cascade: float
    dominant_axis: CascadeAxis
    dominant_regime: CascadeRegime
    flow_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Includes both ``dominant_regime`` and ``regime`` keys (both
        pointing to the same value) so callers may read either name —
        ``dominant_regime`` for consistency with the profile and stats
        payloads, and ``regime`` for callers that expect the shorter
        alias used elsewhere in the engine family.
        """
        regime_value = _enum_value(CascadeRegime, self.dominant_regime)
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_cascade": self.avg_cascade,
            "dominant_axis": _enum_value(CascadeAxis, self.dominant_axis),
            "dominant_regime": regime_value,
            "regime": regime_value,
            "flow_count": self.flow_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CascadePlan:
    """A plan to shape the flow with a strategy.

    ``strategy`` is the ``CascadeStrategy`` chosen.
    ``target_cascade`` in [0, 1] is the cascade the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's flow condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current cascade — callers who need that should
    take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: CascadeStrategy
    target_cascade: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(CascadeStrategy, self.strategy),
            "target_cascade": self.target_cascade,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class TierTransition:
    """One record of a stage transition in the cascade lifecycle.

    ``from_stage`` is the ``CascadeStage`` the agent was in before the
    transition. ``to_stage`` is the ``CascadeStage`` it moved to.
    ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow trickle",
    "sudden cascade", "deliberate pooling").
    """
    transition_id: str
    agent_id: str
    from_stage: CascadeStage
    to_stage: CascadeStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this tier transition to a plain dict, expanding enums via ``.value``."""
        return {
            "transition_id": self.transition_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(CascadeStage, self.from_stage),
            "to_stage": _enum_value(CascadeStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class CascadeProfile:
    """Per-agent aggregate cascade tendencies.

    ``avg_cascade`` in [0, 1] is the mean cascade score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``CascadeAxis`` among the agent's readings, or TIER if
    none. ``dominant_regime`` is derived via ``_determine_regime`` from
    ``avg_cascade``. ``total_readings``, ``total_flows``, and
    ``total_transitions`` are the counts of each record type for the
    agent. ``updated_at`` is the timestamp at which the profile was
    last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_cascade: float = 0.0
    dominant_axis: CascadeAxis = CascadeAxis.TIER
    dominant_regime: CascadeRegime = CascadeRegime.FLOWING
    total_readings: int = 0
    total_flows: int = 0
    total_transitions: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_cascade": self.avg_cascade,
            "dominant_axis": _enum_value(CascadeAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CascadeRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_flows": self.total_flows,
            "total_transitions": self.total_transitions,
            "updated_at": self.updated_at,
        }


@dataclass
class CascadeStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_cascade`` is the mean cascade score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or FLOWING when none
    exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_flows: int = 0
    total_snapshots: int = 0
    total_transitions: int = 0
    avg_cascade: float = 0.0
    dominant_regime: CascadeRegime = CascadeRegime.FLOWING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_flows": self.total_flows,
            "total_snapshots": self.total_snapshots,
            "total_transitions": self.total_transitions,
            "avg_cascade": self.avg_cascade,
            "dominant_regime": _enum_value(CascadeRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCascade:
    """Thread-safe engine that models an agent's cognitive cascade.

    The engine holds six stores: ``_readings`` (CascadeReading lists
    keyed by agent_id), ``_flows`` (FlowRecord lists keyed by
    agent_id), ``_snapshots`` (CascadeSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of CascadePlan),
    ``_transitions`` (TierTransition lists keyed by agent_id), and
    ``_profiles`` (CascadeProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The cascade model is deliberately heuristic: cascade scores and
    intensities are caller-supplied observations; cascade regimes are
    banded from the average cascade; dominant axes are computed by
    mode; stage transitions are recorded as observed. These heuristics
    are transparent and auditable rather than learned, which keeps the
    engine deterministic.

    The engine is intentionally agnostic about how cascade is measured
    and how stage transitions are detected — callers may derive them
    from any source. The engine's job is to record, aggregate,
    classify, and profile, not to measure cascade itself. Profiles are
    cached per agent and invalidated whenever the agent's readings,
    flows, snapshots, or transitions change, so ``get_profile`` always
    reflects the current state unless an explicit override has been
    applied via ``update_profile``.
    """

    # Number of most-recent readings whose cascade scores feed into a
    # snapshot's average cascade. The window is long enough to smooth
    # a single noisy reading and short enough to reflect the agent's
    # current cascade posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty cascade engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[CascadeReading]] = {}
        self._flows: Dict[str, List[FlowRecord]] = {}
        self._snapshots: Dict[str, List[CascadeSnapshot]] = {}
        self._plans: List[CascadePlan] = []
        self._transitions: Dict[str, List[TierTransition]] = {}
        self._profiles: Dict[str, CascadeProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_cascade_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._flows.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._transitions.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[CascadeReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_flows_locked(self, agent_id: str) -> List[FlowRecord]:
        """Return one agent's flow records in insertion order. Caller holds the lock."""
        return list(self._flows.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[CascadeSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[CascadePlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_transitions_locked(
        self, agent_id: str
    ) -> List[TierTransition]:
        """Return one agent's tier transition records in insertion order. Caller holds the lock."""
        return list(self._transitions.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[CascadeReading]
    ) -> CascadeAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns TIER if the list is empty,
        since TIER is the smallest and most neutral axis. Caller
        holds the lock.
        """
        if not readings:
            return CascadeAxis.TIER
        counts: Counter = Counter()
        first_seen_order: Dict[CascadeAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: CascadeAxis = readings[0].axis
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
        self, profiles: List[CascadeProfile]
    ) -> CascadeRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns FLOWING if the list is empty, since FLOWING is the
        default regime — the band that represents a normally
        functioning cognitive cascade that moves thoughts through
        tiers at a sustainable pace without overflowing, neither dry
        nor flooded. Caller holds the lock.
        """
        if not profiles:
            return CascadeRegime.FLOWING
        counts: Dict[CascadeRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> CascadeProfile:
        """Aggregate an agent's readings, flows, and transitions into a profile.

        See ``CascadeProfile`` for field semantics. ``avg_cascade`` is
        the mean cascade score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent ``CascadeAxis``
        among the agent's readings, or TIER if none.
        ``dominant_regime`` is derived via ``_determine_regime`` from
        ``avg_cascade``. ``total_readings``, ``total_flows``, and
        ``total_transitions`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        flows = self._agent_flows_locked(agent_id)
        transitions = self._agent_transitions_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_cascade = sum(
                r.cascade_score for r in readings
            ) / len(readings)
        else:
            avg_cascade = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_cascade)

        return CascadeProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_cascade=round(avg_cascade, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_flows=len(flows),
            total_transitions=len(transitions),
            updated_at=_now(),
        )

    # ── Cascade Readings ─────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        cascade_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> CascadeReading:
        """Record a cascade reading for an agent and return it.

        ``axis`` may be passed as a ``CascadeAxis`` member or its
        string name/value. ``cascade_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``CascadeSource`` member or its string name/value. The reading
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = CascadeReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CascadeAxis, axis),
                cascade_score=_clamp(cascade_score, 0.0, 1.0),
                source=_resolve_enum(CascadeSource, source),
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
    ) -> List[CascadeReading]:
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

    def get_reading(self, reading_id: str) -> CascadeReading:
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

    # ── Flow Records ─────────────────────────────────────────────

    def record_flow(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        flow_magnitude: float,
        notes: Optional[str] = None,
    ) -> FlowRecord:
        """Record a flow event for an agent and return it.

        ``axis`` may be passed as a ``CascadeAxis`` member or its
        string name/value. ``source`` may be passed as a
        ``CascadeSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``flow_magnitude`` is clamped to [0, ∞). The flow is stored
        and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            record = FlowRecord(
                flow_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CascadeAxis, axis),
                source=_resolve_enum(CascadeSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                flow_magnitude=_clamp_positive_ms(flow_magnitude),
                timestamp=_now(),
                notes=notes,
            )
            self._flows.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_flows(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FlowRecord]:
        """Return flow records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all flows are considered;
        otherwise only flows for that agent are returned. The most
        recently recorded ``limit`` flows are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                flows = self._agent_flows_locked(agent_id)
            else:
                flows = []
                for agent_flows in self._flows.values():
                    flows.extend(agent_flows)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return flows[-n:] if n else []

    def get_flow(self, flow_id: str) -> FlowRecord:
        """Retrieve a flow record by id.

        Raises ``ValueError`` if no flow exists with that id.
        """
        with self._lock:
            for agent_flows in self._flows.values():
                for flow in agent_flows:
                    if flow.flow_id == flow_id:
                        return flow
        raise ValueError(f"flow {flow_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CascadeSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_cascade`` is the mean cascade score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``CascadeAxis`` among those readings, or TIER if none.
        ``dominant_regime`` is derived via ``_determine_regime`` from
        ``avg_cascade``. ``flow_count`` is the number of flow events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_cascade = sum(
                    r.cascade_score for r in recent
                ) / len(recent)
            else:
                avg_cascade = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            dominant_regime = _determine_regime(avg_cascade)
            flow_count = len(self._agent_flows_locked(agent_id))

            snapshot = CascadeSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_cascade=round(avg_cascade, 4),
                dominant_axis=dominant_axis,
                dominant_regime=dominant_regime,
                flow_count=flow_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CascadeSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> CascadeSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Cascade Plans ──────────────────────────────────────────────

    def plan_flow(
        self,
        agent_id: str,
        strategy: Any,
        target_cascade: float,
        rationale: str,
    ) -> CascadePlan:
        """Record a cascade plan for an agent and return it.

        ``strategy`` may be passed as a ``CascadeStrategy`` member or
        its string name/value. ``target_cascade`` is clamped to [0, 1].
        ``rationale`` explains why this strategy was chosen. The plan
        is stored in a flat list (not keyed by agent, since plans are
        forward-looking interventions rather than measurements of
        state) and returned. The agent's cached profile is not
        invalidated, since a plan does not change the agent's measured
        cascade.
        """
        with self._lock:
            plan = CascadePlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(CascadeStrategy, strategy),
                target_cascade=_clamp(target_cascade, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CascadePlan]:
        """Return cascade plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> CascadePlan:
        """Retrieve a cascade plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Tier Transitions ──────────────────────────────────────────

    def record_tier_transition(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> TierTransition:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``CascadeStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label that
        describes the character of the transition (e.g. "slow
        trickle", "sudden cascade", "deliberate pooling"). The tier
        transition record is stored and returned; the agent's cached
        profile is invalidated.

        Tier transition records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = TierTransition(
                transition_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(CascadeStage, from_stage),
                to_stage=_resolve_enum(CascadeStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._transitions.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_tier_transitions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TierTransition]:
        """Return tier transition records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all tier transitions are
        considered; otherwise only transitions for that agent are
        returned. The most recently recorded ``limit`` tier transition
        records are returned. The returned list is a snapshot copy;
        mutating it does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                transitions = self._agent_transitions_locked(agent_id)
            else:
                transitions = []
                for agent_transitions in self._transitions.values():
                    transitions.extend(agent_transitions)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return transitions[-n:] if n else []

    def get_tier_transition(self, transition_id: str) -> TierTransition:
        """Retrieve a tier transition record by id.

        Raises ``ValueError`` if no tier transition record exists with
        that id.
        """
        with self._lock:
            for agent_transitions in self._transitions.values():
                for record in agent_transitions:
                    if record.transition_id == transition_id:
                        return record
        raise ValueError(
            f"tier transition {transition_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CascadeProfile:
        """Return the agent's cascade profile, building it if missing.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, flows, snapshots, or transitions change.
        If the agent has data but no profile yet, the profile is built
        from the live stores. Call ``update_profile`` to force a
        refresh or override a computed field. Field semantics are
        documented on ``CascadeProfile`` and
        ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(
        self, agent_id: str, **kwargs: Any
    ) -> CascadeProfile:
        """Refresh and optionally override fields of an agent's cascade profile.

        The profile is first recomputed from the live stores, then any
        supplied overrides in ``kwargs`` (matching ``CascadeProfile``
        field names) are applied. Accepted overrides: ``avg_cascade``
        (float), ``dominant_axis`` (``CascadeAxis``),
        ``dominant_regime`` (``CascadeRegime``), ``total_readings``,
        ``total_flows``, ``total_transitions`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_cascade":
                    try:
                        profile.avg_cascade = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            CascadeAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            CascadeRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_flows",
                    "total_transitions",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CascadeProfile]:
        """Return all stored cascade profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> CascadeStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, flows, snapshots, and transitions.
        Scalar totals are the counts of each record type.
        ``avg_cascade`` is the mean cascade score across all readings,
        or 0.0 when none exist. ``dominant_regime`` is the most
        frequent regime across all cached profiles, or FLOWING when
        none exist. When no profiles exist but readings do, the
        dominant regime is derived from the average cascade via
        ``_determine_regime`` so the stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._flows.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._transitions.keys())

            total_readings = 0
            cascade_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    cascade_sum += reading.cascade_score
            avg_cascade = (
                round(cascade_sum / total_readings, 4) if total_readings else 0.0
            )

            total_flows = sum(
                len(agent_flows) for agent_flows in self._flows.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_transitions = sum(
                len(agent_transitions)
                for agent_transitions in self._transitions.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average cascade so the stats
                # reflect real state rather than the default FLOWING.
                dominant_regime = _determine_regime(avg_cascade)
            else:
                dominant_regime = CascadeRegime.FLOWING

            return CascadeStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_flows=total_flows,
                total_snapshots=total_snapshots,
                total_transitions=total_transitions,
                avg_cascade=avg_cascade,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCascade] = None
_engine_lock = threading.Lock()


def get_cascade_engine() -> AgentCognitiveCascade:
    """Get or create the singleton ``AgentCognitiveCascade`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveCascade()
    return _engine


def reset_cascade_engine() -> None:
    """Reset the singleton ``AgentCognitiveCascade`` instance.

    Drops the reference to the current engine so the next
    ``get_cascade_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
