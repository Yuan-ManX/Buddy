from __future__ import annotations

"""Agent Cognitive Confluence Engine — modeling the merging of cognitive streams

How distinct cognitive streams (perception, reasoning, memory, imagination,
affect) flow together and merge into unified understanding. A confluent agent
integrates streams coherently; a non-confluent agent keeps them fragmented.
Distinct from cohesion, equilibrium, resilience, coherence, and tension.
Core capabilities: axis tracking, force analysis, merging strategies, stage lifecycle.

Architecture:
  AgentCognitiveConfluence (singleton)
  ├── ConfluenceReading     (one observation of confluence on one axis)
  ├── ConfluenceRecord      (one confluence event that changed the score)
  ├── ConfluenceSnapshot    (aggregate confluence state for one agent)
  ├── MergePlan             (a plan to merge streams with a strategy)
  ├── UnityRecord           (one stage transition in the merging lifecycle)
  ├── ConfluenceProfile     (per-agent aggregate confluence tendencies)
  └── ConfluenceStats       (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/confluence/etc.

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
    engine with a ``NaN`` or ``None`` confluence score. A low-side
    default is safer than a mid-range one for confluence-like quantities
    where a spurious high reading would inflate the perceived merging
    and push the agent's regime toward ABSOLUTE.
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
    cannot crash the engine. The upper bound is left open because real
    unity intervals and confluence magnitudes can legitimately exceed
    any small bound — a long-stable agent may spend a very long time in
    one stage before transitioning, and a deliberate large merge may
    apply a large effective magnitude.
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
    against member values (e.g. ``"divergent"``) and then against
    member names (e.g. ``"DIVERGENT"``), so callers may pass either
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


def _determine_regime(avg_confluence: float) -> "ConfluenceRegime":
    """Classify a confluence regime from the average confluence score.

    The average confluence is clamped to [0, 1] where higher means a
    more merged, unified posture. The bands are applied in order, so the
    first matching band wins: below 0.15 the agent is DIVERGENT
    (streams flowing apart, no merging at all); below 0.35 it is
    PARALLEL (streams flowing side by side without meeting); below 0.55
    it is CONVERGING (streams beginning to flow together); below 0.75
    it is MERGED (streams have largely merged); below 0.9 it is UNIFIED
    (streams flowing as one with minor residual distinction);
    otherwise it is ABSOLUTE (complete unity, no distinction remains
    between streams).
    """
    avg = _clamp(avg_confluence, 0.0, 1.0)
    if avg < 0.15:
        return ConfluenceRegime.DIVERGENT
    if avg < 0.35:
        return ConfluenceRegime.PARALLEL
    if avg < 0.55:
        return ConfluenceRegime.CONVERGING
    if avg < 0.75:
        return ConfluenceRegime.MERGED
    if avg < 0.9:
        return ConfluenceRegime.UNIFIED
    return ConfluenceRegime.ABSOLUTE


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ConfluenceAxis(str, Enum):
    """The axis along which a confluence reading is taken.

    Each axis names a different dimension of the agent's cognitive
    system whose merging can be measured. STREAM is a primary cognitive
    stream, such as the perception stream or the reasoning stream.
    CHANNEL is a channel through which streams flow, such as the
    attention channel or the memory channel. CURRENT is a current within
    a stream, such as the dominant current or the background current.
    FLOW is the flow characteristic of a stream, such as steady or
    turbulent. MERGE is the merge point where streams meet. DELTA is
    the delta where a stream branches or deposits its contents, such
    as the output delta or the decision delta.
    """
    STREAM = "stream"    # a primary cognitive stream
    CHANNEL = "channel"  # a channel through which streams flow
    CURRENT = "current"  # a current within a stream
    FLOW = "flow"        # the flow characteristic of a stream
    MERGE = "merge"      # the merge point where streams meet
    DELTA = "delta"      # the delta where a stream deposits contents


class ConfluenceRegime(str, Enum):
    """The regime an agent's confluence occupies, classified by merging.

    Ranges from DIVERGENT (streams flowing apart, no merging at all)
    through PARALLEL (streams flowing side by side without meeting),
    CONVERGING (streams beginning to flow together), MERGED (streams
    have largely merged), and UNIFIED (streams flowing as one with
    minor residual distinction) to ABSOLUTE (complete unity, no
    distinction remains between streams). The regime is derived from
    the average confluence across the agent's readings via
    ``_determine_regime``.
    """
    DIVERGENT = "divergent"  # streams flowing apart
    PARALLEL = "parallel"    # streams flowing side by side
    CONVERGING = "converging"  # streams beginning to flow together
    MERGED = "merged"        # streams have largely merged
    UNIFIED = "unified"      # streams flowing as one
    ABSOLUTE = "absolute"    # complete unity, no distinction


class ConfluenceForce(str, Enum):
    """A force that pulls the agent's streams toward or away from merging.

    Each force names a different pull the agent's streams experience.
    ATTRACTION pulls streams toward each other. PRESSURE pushes streams
    together under load. GRAVITY is the natural pull toward merging, as
    water flows downhill to join. MOMENTUM is the carry-over from prior
    merging — once streams have begun to merge, their own motion keeps
    them moving together. AFFINITY is the natural compatibility between
    streams — some streams fit together more readily than others.
    NECESSITY is the imperative to merge, such as to resolve a conflict
    or meet a deadline. A confluence reading records which force is
    acting on the measured axis, and a confluence record records which
    force drove a change.
    """
    ATTRACTION = "attraction"  # pull streams toward each other
    PRESSURE = "pressure"      # push streams together under load
    GRAVITY = "gravity"        # natural pull toward merging
    MOMENTUM = "momentum"      # carry-over from prior merging
    AFFINITY = "affinity"      # natural compatibility between streams
    NECESSITY = "necessity"    # imperative to merge


class ConfluenceStrategy(str, Enum):
    """Strategy for bringing streams together — or keeping them apart.

    CHANNEL guides streams into a common channel so they flow in the
    same direction without forcing contact. GUIDE gently guides streams
    toward each other, encouraging but not forcing convergence. MERGE
    actively merges streams at their boundaries, pressing them
    together. BLEND blends streams so their distinctions dissolve into
    a unified mixture. DISSOLVE dissolves the boundaries between
    streams entirely, leaving no trace of where one ended and another
    began. SEPARATE deliberately keeps streams apart when merging would
    blur what should stay distinct — sometimes the right move is to
    let streams run in parallel without meeting. Each strategy is
    suited to a different confluence situation, from gently channeling
    parallel streams in the same direction to dissolving all
    boundaries into absolute unity.
    """
    CHANNEL = "channel"    # guide streams into a common channel
    GUIDE = "guide"        # gently guide streams toward each other
    MERGE = "merge"        # actively merge streams at their boundaries
    BLEND = "blend"        # blend streams so distinctions dissolve
    DISSOLVE = "dissolve"  # dissolve boundaries between streams
    SEPARATE = "separate"  # deliberately keep streams apart


class ConfluenceStage(str, Enum):
    """The lifecycle stage of an agent's merging process.

    SEPARATE is the state of streams being separate and distant.
    APPROACHING is the phase of streams moving toward each other.
    TOUCHING is the state in which streams have made contact at their
    boundaries. MIXING is the phase of streams actively mixing at their
    boundary. BLENDED is the state in which streams have blended into a
    unified mixture but some residual distinction remains. ONE is the
    final state at which streams are one — no distinction remains
    between them, the merging is complete. The engine records
    transitions between stages as UnityRecord entries.
    """
    SEPARATE = "separate"      # streams are separate and distant
    APPROACHING = "approaching"  # streams moving toward each other
    TOUCHING = "touching"      # streams have made contact
    MIXING = "mixing"          # streams actively mixing
    BLENDED = "blended"        # streams blended, some distinction remains
    ONE = "one"                # streams are one, no distinction


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ConfluenceReading:
    """One observation of confluence on a particular axis.

    ``axis`` is the ``ConfluenceAxis`` the reading is taken on.
    ``confluence_score`` in [0, 1] measures how merged the agent's
    streams are on that axis — 0 means fully divergent, 1 means fully
    unified. ``force`` is the ``ConfluenceForce`` acting on the axis.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: ConfluenceAxis
    confluence_score: float  # 0..1, higher = more merged
    force: ConfluenceForce
    intensity: float         # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(ConfluenceAxis, self.axis),
            "confluence_score": self.confluence_score,
            "force": _enum_value(ConfluenceForce, self.force),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ConfluenceRecord:
    """One confluence event that changed the confluence on an axis.

    ``axis`` is the ``ConfluenceAxis`` on which the confluence event
    occurred. ``force`` is the ``ConfluenceForce`` that drove the
    change. ``before_score`` in [0, 1] is the confluence before the
    event; ``after_score`` in [0, 1] is the confluence after.
    ``confluence_magnitude`` in [0, ∞) measures how strong the
    confluence event was. ``notes`` is an optional free-form
    annotation.
    """
    confluence_id: str
    agent_id: str
    axis: ConfluenceAxis
    force: ConfluenceForce
    before_score: float           # 0..1, confluence before event
    after_score: float            # 0..1, confluence after event
    confluence_magnitude: float   # 0..inf, strength of the confluence
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this confluence record to a plain dict, expanding enums via ``.value``."""
        return {
            "confluence_id": self.confluence_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(ConfluenceAxis, self.axis),
            "force": _enum_value(ConfluenceForce, self.force),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "confluence_magnitude": self.confluence_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ConfluenceSnapshot:
    """Aggregate confluence state for one agent at one moment.

    ``avg_confluence`` in [0, 1] is the mean confluence score across
    the agent's recent readings, or 0.0 if none. ``dominant_axis`` is
    the most frequent ``ConfluenceAxis`` among those readings, or
    STREAM if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_confluence``. ``confluence_count``
    is the number of confluence events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_confluence: float
    dominant_axis: ConfluenceAxis
    dominant_regime: ConfluenceRegime
    confluence_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_confluence": self.avg_confluence,
            "dominant_axis": _enum_value(ConfluenceAxis, self.dominant_axis),
            "dominant_regime": _enum_value(ConfluenceRegime, self.dominant_regime),
            "regime": _enum_value(ConfluenceRegime, self.dominant_regime),
            "confluence_count": self.confluence_count,
            "timestamp": self.timestamp,
        }


@dataclass
class MergePlan:
    """A plan to bring streams together with a strategy.

    ``strategy`` is the ``ConfluenceStrategy`` chosen. ``target_confluence``
    in [0, 1] is the confluence the plan aims to reach. ``rationale``
    explains why this strategy was chosen for this agent's confluence
    situation. A plan is a forward-looking intervention rather than a
    measurement of state, so it does not record the agent's current
    confluence — callers who need that should take a snapshot alongside
    the plan.
    """
    plan_id: str
    agent_id: str
    strategy: ConfluenceStrategy
    target_confluence: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(ConfluenceStrategy, self.strategy),
            "target_confluence": self.target_confluence,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class UnityRecord:
    """One record of a stage transition in the merging lifecycle.

    ``from_stage`` is the ``ConfluenceStage`` the agent was in before
    the transition. ``to_stage`` is the ``ConfluenceStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow approach",
    "sudden merge", "deliberate dissolution").
    """
    unity_id: str
    agent_id: str
    from_stage: ConfluenceStage
    to_stage: ConfluenceStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this unity record to a plain dict, expanding enums via ``.value``."""
        return {
            "unity_id": self.unity_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(ConfluenceStage, self.from_stage),
            "to_stage": _enum_value(ConfluenceStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class ConfluenceProfile:
    """Per-agent aggregate confluence tendencies.

    ``profile_id`` is a short unique identifier for this profile
    computation. ``avg_confluence`` in [0, 1] is the mean confluence
    score across the agent's readings (0.0 if none). ``dominant_axis``
    is the most frequent ``ConfluenceAxis`` among the agent's readings,
    or STREAM if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_confluence``. ``total_readings``,
    ``total_confluences``, and ``total_unities`` are the counts of each
    record type for the agent. ``last_updated`` is the timestamp of the
    last profile computation.
    """
    profile_id: str
    agent_id: str
    avg_confluence: float = 0.0
    dominant_axis: ConfluenceAxis = ConfluenceAxis.STREAM
    dominant_regime: ConfluenceRegime = ConfluenceRegime.CONVERGING
    total_readings: int = 0
    total_confluences: int = 0
    total_unities: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_confluence": self.avg_confluence,
            "dominant_axis": _enum_value(ConfluenceAxis, self.dominant_axis),
            "dominant_regime": _enum_value(ConfluenceRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_confluences": self.total_confluences,
            "total_unities": self.total_unities,
            "last_updated": self.last_updated,
        }


@dataclass
class ConfluenceStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_confluence`` is the mean confluence score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or CONVERGING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_confluences: int = 0
    total_snapshots: int = 0
    total_unities: int = 0
    avg_confluence: float = 0.0
    dominant_regime: ConfluenceRegime = ConfluenceRegime.CONVERGING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_confluences": self.total_confluences,
            "total_snapshots": self.total_snapshots,
            "total_unities": self.total_unities,
            "avg_confluence": self.avg_confluence,
            "dominant_regime": _enum_value(ConfluenceRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveConfluence:
    """Thread-safe engine that models an agent's cognitive confluence.

    The engine holds six stores: ``_readings`` (ConfluenceReading
    lists keyed by agent_id), ``_confluences`` (ConfluenceRecord
    lists keyed by agent_id), ``_snapshots`` (ConfluenceSnapshot
    lists keyed by agent_id), ``_plans`` (a flat list of MergePlan),
    ``_unities`` (UnityRecord lists keyed by agent_id), and
    ``_profiles`` (ConfluenceProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The confluence model is deliberately heuristic: confluence scores
    and intensities are caller-supplied observations; confluence
    regimes are banded from the average confluence; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how confluence is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure confluence
    itself. Profiles are cached per agent and invalidated whenever the
    agent's readings, confluences, snapshots, or unities change, so
    ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose confluence scores feed into
    # a snapshot's average confluence. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current confluence posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty confluence engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[ConfluenceReading]] = {}
        self._confluences: Dict[str, List[ConfluenceRecord]] = {}
        self._snapshots: Dict[str, List[ConfluenceSnapshot]] = {}
        self._plans: List[MergePlan] = []
        self._unities: Dict[str, List[UnityRecord]] = {}
        self._profiles: Dict[str, ConfluenceProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton instance is not touched;
        callers that want a fresh singleton should use
        ``reset_confluence_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._confluences.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._unities.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[ConfluenceReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_confluences_locked(
        self, agent_id: str
    ) -> List[ConfluenceRecord]:
        """Return one agent's confluence records in insertion order. Caller holds the lock."""
        return list(self._confluences.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[ConfluenceSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[MergePlan]:
        """Return one agent's merge plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id``. The returned
        list preserves insertion order.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_unities_locked(
        self, agent_id: str
    ) -> List[UnityRecord]:
        """Return one agent's unity records in insertion order. Caller holds the lock."""
        return list(self._unities.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[ConfluenceReading]
    ) -> ConfluenceAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns STREAM if the list is empty,
        since STREAM is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return ConfluenceAxis.STREAM
        counts: Counter = Counter()
        first_seen_order: Dict[ConfluenceAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: ConfluenceAxis = readings[0].axis
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
        self, profiles: List[ConfluenceProfile]
    ) -> ConfluenceRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns CONVERGING if the list is empty, since CONVERGING
        is the neutral mid-range regime — the band that contains the
        midpoint of the confluence scale, neither divergent nor
        absolute. Caller holds the lock.
        """
        if not profiles:
            return ConfluenceRegime.CONVERGING
        counts: Dict[ConfluenceRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> ConfluenceProfile:
        """Aggregate an agent's readings, confluences, and unities into a profile.

        See ``ConfluenceProfile`` for field semantics. ``avg_confluence``
        is the mean confluence score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent
        ``ConfluenceAxis`` among the agent's readings, or STREAM if
        none. ``dominant_regime`` is derived via ``_determine_regime``
        from ``avg_confluence``. ``total_readings``,
        ``total_confluences``, and ``total_unities`` count the records
        held for the agent. ``profile_id`` and ``last_updated`` are
        generated fresh on each computation. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        confluences = self._agent_confluences_locked(agent_id)
        unities = self._agent_unities_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_confluence = sum(
                r.confluence_score for r in readings
            ) / len(readings)
        else:
            avg_confluence = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_confluence)

        return ConfluenceProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_confluence=round(avg_confluence, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_confluences=len(confluences),
            total_unities=len(unities),
            last_updated=_now(),
        )

    # ── Confluence Readings ─────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        confluence_score: float,
        force: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> ConfluenceReading:
        """Record a confluence reading for an agent and return it.

        ``axis`` may be passed as a ``ConfluenceAxis`` member or its
        string name/value. ``confluence_score`` and ``intensity`` are
        clamped to [0, 1]. ``force`` may be passed as a
        ``ConfluenceForce`` member or its string name/value. The reading
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = ConfluenceReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(ConfluenceAxis, axis),
                confluence_score=_clamp(confluence_score, 0.0, 1.0),
                force=_resolve_enum(ConfluenceForce, force),
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
    ) -> List[ConfluenceReading]:
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

    def get_reading(self, reading_id: str) -> ConfluenceReading:
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

    # ── Confluence Records ────────────────────────────────────────

    def record_confluence(
        self,
        agent_id: str,
        axis: Any,
        force: Any,
        before_score: float,
        after_score: float,
        confluence_magnitude: float,
        notes: Optional[str] = None,
    ) -> ConfluenceRecord:
        """Record a confluence event for an agent and return it.

        ``axis`` may be passed as a ``ConfluenceAxis`` member or
        its string name/value. ``force`` may be passed as a
        ``ConfluenceForce`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``confluence_magnitude`` is clamped to [0, ∞). The confluence
        event is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = ConfluenceRecord(
                confluence_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(ConfluenceAxis, axis),
                force=_resolve_enum(ConfluenceForce, force),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                confluence_magnitude=_clamp_positive_ms(
                    confluence_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._confluences.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_confluences(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ConfluenceRecord]:
        """Return confluence records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all confluences are considered;
        otherwise only confluences for that agent are returned. The
        most recently recorded ``limit`` confluences are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                confluences = self._agent_confluences_locked(agent_id)
            else:
                confluences = []
                for agent_confluences in self._confluences.values():
                    confluences.extend(agent_confluences)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return confluences[-n:] if n else []

    def get_confluence(self, confluence_id: str) -> ConfluenceRecord:
        """Retrieve a confluence record by id.

        Raises ``ValueError`` if no confluence record exists with that
        id.
        """
        with self._lock:
            for agent_confluences in self._confluences.values():
                for confluence in agent_confluences:
                    if confluence.confluence_id == confluence_id:
                        return confluence
        raise ValueError(f"confluence {confluence_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> ConfluenceSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_confluence`` is the mean confluence score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``ConfluenceAxis``
        among those readings, or STREAM if none. ``dominant_regime`` is
        derived via ``_determine_regime`` from ``avg_confluence``.
        ``confluence_count`` is the number of confluence events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_confluence = sum(
                    r.confluence_score for r in recent
                ) / len(recent)
            else:
                avg_confluence = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            dominant_regime = _determine_regime(avg_confluence)
            confluence_count = len(
                self._agent_confluences_locked(agent_id)
            )

            snapshot = ConfluenceSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_confluence=round(avg_confluence, 4),
                dominant_axis=dominant_axis,
                dominant_regime=dominant_regime,
                confluence_count=confluence_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ConfluenceSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> ConfluenceSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Merge Plans ──────────────────────────────────────────────

    def plan_merge(
        self,
        agent_id: str,
        strategy: Any,
        target_confluence: float,
        rationale: str,
    ) -> MergePlan:
        """Record a merge plan for an agent and return it.

        ``strategy`` may be passed as a ``ConfluenceStrategy`` member
        or its string name/value. ``target_confluence`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured confluence.
        """
        with self._lock:
            plan = MergePlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(ConfluenceStrategy, strategy),
                target_confluence=_clamp(target_confluence, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MergePlan]:
        """Return merge plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> MergePlan:
        """Retrieve a merge plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Unity Records ────────────────────────────────────────────

    def record_unity(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> UnityRecord:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``ConfluenceStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label that
        describes the character of the transition (e.g. "slow
        approach", "sudden merge", "deliberate dissolution"). The
        unity record is stored and returned; the agent's cached
        profile is invalidated.

        Note that unity records do not carry a notes field — the
        ``signature`` parameter serves as the free-form annotation
        for a stage transition.
        """
        with self._lock:
            record = UnityRecord(
                unity_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(ConfluenceStage, from_stage),
                to_stage=_resolve_enum(ConfluenceStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._unities.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_unities(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[UnityRecord]:
        """Return unity records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all unities are considered;
        otherwise only unities for that agent are returned. The most
        recently recorded ``limit`` unity records are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                unities = self._agent_unities_locked(agent_id)
            else:
                unities = []
                for agent_unities in self._unities.values():
                    unities.extend(agent_unities)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return unities[-n:] if n else []

    def get_unity(self, unity_id: str) -> UnityRecord:
        """Retrieve a unity record by id.

        Raises ``ValueError`` if no unity record exists with that id.
        """
        with self._lock:
            for agent_unities in self._unities.values():
                for record in agent_unities:
                    if record.unity_id == unity_id:
                        return record
        raise ValueError(f"unity record {unity_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> ConfluenceProfile:
        """Return the agent's confluence profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, confluences, snapshots, or
        unities change. If the agent has data but no profile yet, the
        profile is built from the live stores. Call ``update_profile``
        to force a refresh or override a computed field. Field
        semantics are documented on ``ConfluenceProfile`` and
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
    ) -> ConfluenceProfile:
        """Refresh and optionally override fields of an agent's confluence profile.

        The profile is first recomputed from the live stores, then any
        supplied overrides in ``kwargs`` (matching ``ConfluenceProfile``
        field names) are applied. Accepted overrides: ``avg_confluence``
        (float), ``dominant_axis`` (``ConfluenceAxis``),
        ``dominant_regime`` (``ConfluenceRegime``), ``total_readings``,
        ``total_confluences``, ``total_unities`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_confluence":
                    try:
                        profile.avg_confluence = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            ConfluenceAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            ConfluenceRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_confluences",
                    "total_unities",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[ConfluenceProfile]:
        """Return all stored confluence profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> ConfluenceStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, confluences, snapshots, and unities.
        Scalar totals are the counts of each record type.
        ``avg_confluence`` is the mean confluence score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or CONVERGING
        when none exist. When no profiles exist but readings do, the
        dominant regime is derived from the average confluence via
        ``_determine_regime`` so the stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._confluences.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._unities.keys())

            total_readings = 0
            confluence_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    confluence_sum += reading.confluence_score
            avg_confluence = (
                round(confluence_sum / total_readings, 4)
                if total_readings
                else 0.0
            )

            total_confluences = sum(
                len(agent_confluences)
                for agent_confluences in self._confluences.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_unities = sum(
                len(agent_unities)
                for agent_unities in self._unities.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average confluence so the stats
                # reflect real state rather than the default
                # CONVERGING.
                dominant_regime = _determine_regime(avg_confluence)
            else:
                dominant_regime = ConfluenceRegime.CONVERGING

            return ConfluenceStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_confluences=total_confluences,
                total_snapshots=total_snapshots,
                total_unities=total_unities,
                avg_confluence=avg_confluence,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveConfluence] = None
_engine_lock = threading.Lock()


def get_confluence_engine() -> AgentCognitiveConfluence:
    """Get or create the singleton ``AgentCognitiveConfluence`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveConfluence()
    return _engine


def reset_confluence_engine() -> None:
    """Reset the singleton ``AgentCognitiveConfluence`` instance.

    Drops the current engine so the next
    ``get_confluence_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
