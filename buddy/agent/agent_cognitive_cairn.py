from __future__ import annotations

"""Agent Cognitive Cairn Engine — stacked stone markers guiding cognitive navigation

How wisdom accumulates into trail-markers the agent follows through the cognitive field.
A guiding agent crowns a landmark of stacked stones; a bare agent's trail is
unmarked and directionless. Distinct from polarization, coherence, tension,
equilibrium, and affinity.
Core capabilities: axis tracking, source forces, stone strategies, stacking stages.

Architecture:
  AgentCognitiveCairn (singleton)
  ├── CairnReading      (one observation of cairn on one axis)
  ├── StoneRecord       (one stone event that changed cairn)
  ├── CairnSnapshot     (aggregate cairn state for one agent)
  ├── CairnPlan         (a plan to shape the trail with a strategy)
  ├── MarkerShift       (one stage transition in the stacking lifecycle)
  ├── CairnProfile      (per-agent aggregate cairn tendencies)
  └── CairnStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/stone/etc.

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
    engine with a ``NaN`` or ``None`` cairn. A low-side default is
    safer than a mid-range one for cairn-like quantities where a
    spurious high reading would inflate the perceived cairn and
    push the agent's regime toward LANDMARK.
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
    real stacking intervals and stone magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    stacking may apply a large effective stone magnitude.
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
    against member values (e.g. ``"bare"``) and then against
    member names (e.g. ``"BARE"``), so callers may pass either
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


def _determine_regime(avg_cairn: float) -> "CairnRegime":
    """Classify a cairn regime from the average cairn score.

    The average cairn is clamped to [0, 1] where higher means a
    more stacked, guiding posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is BARE
    (no stones placed, no markers); below 0.35 it is SCATTERED (loose
    stones, only stacks under external effort); below 0.55 it is
    STACKED (stones organized, retains stack form); below 0.75 it is
    MARKED (most stones marked with trail markers); below 0.9 it is
    GUIDING (fully stacked, little room for more markers); otherwise
    it is LANDMARK (perfectly crowned landmark cairn).
    """
    avg = _clamp(avg_cairn, 0.0, 1.0)
    if avg < 0.15:
        return CairnRegime.BARE
    if avg < 0.35:
        return CairnRegime.SCATTERED
    if avg < 0.55:
        return CairnRegime.STACKED
    if avg < 0.75:
        return CairnRegime.MARKED
    if avg < 0.9:
        return CairnRegime.GUIDING
    return CairnRegime.LANDMARK


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CairnAxis(str, Enum):
    """The axis along which a cairn reading is taken.

    Each axis names a different dimension of the agent's cognitive
    trail whose cairn can be measured. STONE is a single marker
    stone. STACK is the pile of stacked stones. MARKER is the
    trail marker label. TRAIL is the guided path. SUMMIT is the
    peak marker. FOUNDATION is the base stones anchoring the
    stack.
    """
    STONE = "stone"            # single marker stone
    STACK = "stack"            # pile of stacked stones
    MARKER = "marker"          # trail marker label
    TRAIL = "trail"            # guided path
    SUMMIT = "summit"          # peak marker
    FOUNDATION = "foundation"  # base stones


class CairnRegime(str, Enum):
    """The regime an agent's cairn occupies, classified by cairn.

    Ranges from BARE (no stones placed, no markers) through
    SCATTERED (loose stones, only stacks under external effort),
    STACKED (stones organized, retains stack form), MARKED (most
    stones marked with trail markers), and GUIDING (fully stacked,
    little room for more markers) to LANDMARK (perfectly crowned
    landmark cairn). The regime is derived from the average cairn
    across the agent's readings via ``_determine_regime``.
    """
    BARE = "bare"            # no stones placed
    SCATTERED = "scattered"  # loose stones, no order
    STACKED = "stacked"      # stones organized in stacks
    MARKED = "marked"        # stacks with markers
    GUIDING = "guiding"      # markers guide navigation
    LANDMARK = "landmark"    # landmark cairn


class CairnSource(str, Enum):
    """A source that supplies the stacking or marking force.

    Each source names a different origin of the pull toward placing
    stones. OBSERVATION places stones from what is seen. MEMORY
    places stones from what is remembered. TRADITION places stones
    from inherited practice. NAVIGATION places stones to mark a
    route. EXPLORATION places stones to probe new ground. DISCOVERY
    places stones to record a finding. A cairn reading records
    which source supplies the force on the measured axis, and a
    stone record records which source drove a change.
    """
    OBSERVATION = "observation"  # from what is seen
    MEMORY = "memory"            # from what is remembered
    TRADITION = "tradition"      # from inherited practice
    NAVIGATION = "navigation"    # to mark a route
    EXPLORATION = "exploration"  # to probe new ground
    DISCOVERY = "discovery"      # to record a finding


class CairnStrategy(str, Enum):
    """Strategy for shaping the trail deliberately.

    STACK piles stones together. ARRANGE orders stones into a
    pattern. MARK labels stones as trail markers. CLEAR removes
    stones from the trail. ELEVATE raises the stack higher.
    ANCHOR fixes a stone as a foundation. Each strategy is suited
    to a different trail condition, from counteracting a scattered
    trail to releasing a landmark one.
    """
    STACK = "stack"      # pile stones together
    ARRANGE = "arrange"  # order stones into a pattern
    MARK = "mark"        # label stones as trail markers
    CLEAR = "clear"      # remove stones from the trail
    ELEVATE = "elevate"  # raise the stack higher
    ANCHOR = "anchor"    # fix a stone as a foundation


class CairnStage(str, Enum):
    """The lifecycle stage of an agent's stack-building process.

    LOOSE is the state of no stones gathered. GATHERING is the
    phase of collecting stones. STACKING is the state in which
    stones are piled. MARKING is the state of labeling stacks.
    GUIDING is the state at which markers guide navigation.
    CROWNING is the final state at which the stack is crowned
    as a landmark and unresponsive to new stones. The engine
    records transitions between stages as MarkerShift entries.
    """
    LOOSE = "loose"          # no stones gathered
    GATHERING = "gathering"  # collecting stones
    STACKING = "stacking"    # stones are piled
    MARKING = "marking"      # labeling stacks
    GUIDING = "guiding"      # markers guide navigation
    CROWNING = "crowning"    # crowned as a landmark


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CairnReading:
    """One observation of cairn on a particular axis.

    ``axis`` is the ``CairnAxis`` the reading is taken on.
    ``cairn_score`` in [0, 1] measures how stacked the agent is
    on that axis — 0 means fully bare, 1 means fully crowned.
    ``source`` is the ``CairnSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: CairnAxis
    cairn_score: float    # 0..1, higher = more stacked
    source: CairnSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CairnAxis, self.axis),
            "cairn_score": self.cairn_score,
            "source": _enum_value(CairnSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class StoneRecord:
    """One stone event that changed the cairn on an axis.

    ``axis`` is the ``CairnAxis`` on which the stone event occurred.
    ``source`` is the ``CairnSource`` that drove the change.
    ``before_score`` in [0, 1] is the cairn before the event;
    ``after_score`` in [0, 1] is the cairn after.
    ``stone_magnitude`` in [0, ∞) measures how strong the
    stone event was. ``notes`` is an optional free-form annotation.
    """
    stone_id: str
    agent_id: str
    axis: CairnAxis
    source: CairnSource
    before_score: float            # 0..1, cairn before stone event
    after_score: float             # 0..1, cairn after stone event
    stone_magnitude: float    # 0..inf, strength of stone event
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this stone record to a plain dict, expanding enums via ``.value``."""
        return {
            "stone_id": self.stone_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CairnAxis, self.axis),
            "source": _enum_value(CairnSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "stone_magnitude": self.stone_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CairnSnapshot:
    """Aggregate cairn state for one agent at one moment.

    ``avg_cairn`` in [0, 1] is the mean cairn score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``CairnAxis`` among those readings, or
    STONE if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_cairn``. ``stone_count``
    is the number of stone events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_cairn: float
    dominant_axis: CairnAxis
    regime: CairnRegime
    stone_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Emits both ``"dominant_regime"`` and ``"regime"`` keys pointing
        to the same value so consumers keyed on either name can read
        the regime without special-casing.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_cairn": self.avg_cairn,
            "dominant_axis": _enum_value(CairnAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CairnRegime, self.regime),
            "regime": _enum_value(CairnRegime, self.regime),
            "stone_count": self.stone_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CairnPlan:
    """A plan to shape the trail with a strategy.

    ``strategy`` is the ``CairnStrategy`` chosen.
    ``target_cairn`` in [0, 1] is the cairn the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's trail condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current cairn — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: CairnStrategy
    target_cairn: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(CairnStrategy, self.strategy),
            "target_cairn": self.target_cairn,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class MarkerShift:
    """One record of a stage transition in the stacking lifecycle.

    ``from_stage`` is the ``CairnStage`` the agent was in before
    the transition. ``to_stage`` is the ``CairnStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow gather",
    "sudden stacking", "deliberate elevation").
    """
    shift_id: str
    agent_id: str
    from_stage: CairnStage
    to_stage: CairnStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this marker shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(CairnStage, self.from_stage),
            "to_stage": _enum_value(CairnStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class CairnProfile:
    """Per-agent aggregate cairn tendencies.

    ``avg_cairn`` in [0, 1] is the mean cairn score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``CairnAxis`` among the agent's readings, or
    STONE if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_cairn``. ``total_readings``,
    ``total_stones``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_cairn: float = 0.0
    dominant_axis: CairnAxis = CairnAxis.STONE
    dominant_regime: CairnRegime = CairnRegime.STACKED
    total_readings: int = 0
    total_stones: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_cairn": self.avg_cairn,
            "dominant_axis": _enum_value(CairnAxis, self.dominant_axis),
            "dominant_regime": _enum_value(CairnRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_stones": self.total_stones,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class CairnStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_cairn`` is the mean cairn score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or STACKED when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_stones: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_cairn: float = 0.0
    dominant_regime: CairnRegime = CairnRegime.STACKED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_stones": self.total_stones,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_cairn": self.avg_cairn,
            "dominant_regime": _enum_value(CairnRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCairn:
    """Thread-safe engine that models an agent's cognitive cairn.

    The engine holds six stores: ``_readings`` (CairnReading lists
    keyed by agent_id), ``_stones`` (StoneRecord lists keyed by
    agent_id), ``_snapshots`` (CairnSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of CairnPlan),
    ``_shifts`` (MarkerShift lists keyed by agent_id), and
    ``_profiles`` (CairnProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The cairn model is deliberately heuristic: cairn scores
    and intensities are caller-supplied observations; cairn
    regimes are banded from the average cairn; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how cairn is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure cairn itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, stones, snapshots, or marker shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose cairn scores feed into
    # a snapshot's average cairn. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current cairn posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty cairn engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[CairnReading]] = {}
        self._stones: Dict[str, List[StoneRecord]] = {}
        self._snapshots: Dict[str, List[CairnSnapshot]] = {}
        self._plans: List[CairnPlan] = []
        self._shifts: Dict[str, List[MarkerShift]] = {}
        self._profiles: Dict[str, CairnProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_cairn_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._stones.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[CairnReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_stones_locked(
        self, agent_id: str
    ) -> List[StoneRecord]:
        """Return one agent's stone records in insertion order. Caller holds the lock."""
        return list(self._stones.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[CairnSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[CairnPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[MarkerShift]:
        """Return one agent's marker shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[CairnReading]
    ) -> CairnAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns STONE if the list is
        empty, since STONE is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return CairnAxis.STONE
        counts: Counter = Counter()
        first_seen_order: Dict[CairnAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: CairnAxis = readings[0].axis
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
        self, profiles: List[CairnProfile]
    ) -> CairnRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns STACKED if the list is empty, since
        STACKED is the default regime — the band that
        represents a normally functioning cognitive trail that
        retains stack form without being a landmark, neither
        bare nor landmark. Caller holds the lock.
        """
        if not profiles:
            return CairnRegime.STACKED
        counts: Dict[CairnRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> CairnProfile:
        """Aggregate an agent's readings, stones, and shifts into a profile.

        See ``CairnProfile`` for field semantics. ``avg_cairn``
        is the mean cairn score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``CairnAxis`` among the agent's readings, or STONE
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_cairn``.
        ``total_readings``, ``total_stones``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        stones = self._agent_stones_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_cairn = sum(
                r.cairn_score for r in readings
            ) / len(readings)
        else:
            avg_cairn = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_cairn)

        return CairnProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_cairn=round(avg_cairn, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_stones=len(stones),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Cairn Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        cairn_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> CairnReading:
        """Record a cairn reading for an agent and return it.

        ``axis`` may be passed as a ``CairnAxis`` member or its
        string name/value. ``cairn_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``CairnSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = CairnReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CairnAxis, axis),
                cairn_score=_clamp(cairn_score, 0.0, 1.0),
                source=_resolve_enum(CairnSource, source),
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
    ) -> List[CairnReading]:
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

    def get_reading(self, reading_id: str) -> CairnReading:
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

    # ── Stone Records ────────────────────────────────────────

    def record_stone(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        stone_magnitude: float,
        notes: Optional[str] = None,
    ) -> StoneRecord:
        """Record a stone event for an agent and return it.

        ``axis`` may be passed as a ``CairnAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``CairnSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``stone_magnitude`` is clamped to [0, ∞). The stone event
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = StoneRecord(
                stone_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CairnAxis, axis),
                source=_resolve_enum(CairnSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                stone_magnitude=_clamp_positive_ms(
                    stone_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._stones.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_stones(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StoneRecord]:
        """Return stone records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all stones are considered;
        otherwise only stones for that agent are returned. The
        most recently recorded ``limit`` stones are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                stones = self._agent_stones_locked(agent_id)
            else:
                stones = []
                for agent_stones in self._stones.values():
                    stones.extend(agent_stones)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return stones[-n:] if n else []

    def get_stone(self, stone_id: str) -> StoneRecord:
        """Retrieve a stone record by id.

        Raises ``ValueError`` if no stone exists with that id.
        """
        with self._lock:
            for agent_stones in self._stones.values():
                for stone in agent_stones:
                    if stone.stone_id == stone_id:
                        return stone
        raise ValueError(f"stone {stone_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CairnSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_cairn`` is the mean cairn score across the agent's most
        recent readings (the last ``_SNAPSHOT_READING_WINDOW`` = 20), or
        0.0 if none. ``dominant_axis`` is the most frequent ``CairnAxis``
        among those readings, or STONE if none. ``regime`` is derived
        via ``_determine_regime`` from ``avg_cairn``. ``stone_count`` is
        the number of stone events recorded against the agent. The
        snapshot is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_cairn = sum(
                    r.cairn_score for r in recent
                ) / len(recent)
            else:
                avg_cairn = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_cairn)
            stone_count = len(
                self._agent_stones_locked(agent_id)
            )

            snapshot = CairnSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_cairn=round(avg_cairn, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                stone_count=stone_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CairnSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> CairnSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Cairn Plans ────────────────────────────────────────────

    def plan_stone(
        self,
        agent_id: str,
        strategy: Any,
        target_cairn: float,
        rationale: str,
    ) -> CairnPlan:
        """Record a cairn plan for an agent and return it.

        ``strategy`` may be passed as a ``CairnStrategy`` member
        or its string name/value. ``target_cairn`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured cairn.
        """
        with self._lock:
            plan = CairnPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(CairnStrategy, strategy),
                target_cairn=_clamp(target_cairn, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CairnPlan]:
        """Return cairn plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> CairnPlan:
        """Retrieve a cairn plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Marker Shift Records ────────────────────────────────

    def record_marker_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> MarkerShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``CairnStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        gather", "sudden stacking", "deliberate elevation"). The
        marker shift record is stored and returned; the agent's cached
        profile is invalidated.

        Marker shifts carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = MarkerShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(CairnStage, from_stage),
                to_stage=_resolve_enum(CairnStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_marker_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MarkerShift]:
        """Return marker shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all marker shifts are considered;
        otherwise only marker shifts for that agent are returned. The
        most recently recorded ``limit`` marker shift records are
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

    def get_marker_shift(self, shift_id: str) -> MarkerShift:
        """Retrieve a marker shift record by id.

        Raises ``ValueError`` if no marker shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"marker shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CairnProfile:
        """Return the agent's cairn profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, stones, snapshots, or
        marker shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``CairnProfile``
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
    ) -> CairnProfile:
        """Refresh and optionally override fields of an agent's cairn profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``CairnProfile`` field names) are applied. Accepted
        overrides: ``avg_cairn`` (float), ``dominant_axis``
        (``CairnAxis``), ``dominant_regime``
        (``CairnRegime``), ``total_readings``,
        ``total_stones``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_cairn":
                    try:
                        profile.avg_cairn = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            CairnAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            CairnRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_stones",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CairnProfile]:
        """Return all stored cairn profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> CairnStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, stones, snapshots, and marker shifts.
        Scalar totals are the counts of each record type.
        ``avg_cairn`` is the mean cairn score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        STACKED when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        cairn via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._stones.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            cairn_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    cairn_sum += reading.cairn_score
            avg_cairn = (
                round(cairn_sum / total_readings, 4) if total_readings else 0.0
            )

            total_stones = sum(
                len(agent_stones)
                for agent_stones in self._stones.values()
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
                # the regime from the average cairn so the stats
                # reflect real state rather than the default
                # STACKED.
                dominant_regime = _determine_regime(avg_cairn)
            else:
                dominant_regime = CairnRegime.STACKED

            return CairnStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_stones=total_stones,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_cairn=avg_cairn,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCairn] = None
_engine_lock = threading.Lock()


def get_cairn_engine() -> AgentCognitiveCairn:
    """Get or create the singleton ``AgentCognitiveCairn`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveCairn()
    return _engine


def reset_cairn_engine() -> None:
    """Reset the singleton ``AgentCognitiveCairn`` instance.

    Drops the reference to the current engine so the next
    ``get_cairn_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
