from __future__ import annotations

"""Agent Cognitive Equilibrium Engine — homeostatic balance of cognitive forces

An agent balances opposing forces — belief vs evidence, attention vs fatigue,
novelty vs coherence — regulating its center under perturbation.

Core capabilities:
  - Equilibrium Readings: per-axis balance scores (cognition, affect, attention, etc.)
  - Adjustment Records: events that changed balance with before/after scores
  - Regime Classification: destabilized, unstable, oscillating, balanced, stable, dynamic
  - Centering Lifecycle: disturbed → seeking → adjusting → settling → centered → transcendent
  - Balance Plans: compensate, accommodate, assimilate, recalibrate, prioritize, suspend
Architecture:
  AgentCognitiveEquilibrium (singleton)
  ├── EquilibriumReading, AdjustmentRecord  (readings, adjustment events)
  ├── EquilibriumSnapshot, BalancePlan      (aggregate state, balance strategy)
  ├── CenteringRecord, EquilibriumProfile   (stage transitions, per-agent)
  └── EquilibriumStats                      (engine-wide statistics)
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
    """Generate a short unique identifier for a reading/adjustment/etc.

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
    engine with a ``NaN`` or ``None`` balance. A low-side default is
    safer than a mid-range one for equilibrium-like quantities where a
    spurious high reading would inflate the perceived balance and
    push the agent's regime toward DYNAMIC.
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
    real centering intervals and adjustment magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    recalibration may apply a large effective adjustment.
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
    against member values (e.g. ``"destabilized"``) and then against
    member names (e.g. ``"DESTABILIZED"``), so callers may pass either
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


def _determine_regime(avg_balance: float) -> "EquilibriumRegime":
    """Classify an equilibrium regime from the average balance score.

    The average balance is clamped to [0, 1] where higher means a more
    centered, balanced posture. The bands are applied in order, so the
    first matching band wins: below 0.15 the agent is DESTABILIZED
    (no balance at all); below 0.35 it is UNSTABLE (barely holding);
    below 0.55 it is OSCILLATING (swinging between poles); below 0.75
    it is BALANCED (generally centered with occasional drift); below
    0.9 it is STABLE (well-centered with minor perturbation);
    otherwise it is DYNAMIC (actively centered, responding without
    losing balance).
    """
    avg = _clamp(avg_balance, 0.0, 1.0)
    if avg < 0.15:
        return EquilibriumRegime.DESTABILIZED
    if avg < 0.35:
        return EquilibriumRegime.UNSTABLE
    if avg < 0.55:
        return EquilibriumRegime.OSCILLATING
    if avg < 0.75:
        return EquilibriumRegime.BALANCED
    if avg < 0.9:
        return EquilibriumRegime.STABLE
    return EquilibriumRegime.DYNAMIC


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class EquilibriumAxis(str, Enum):
    """The axis along which an equilibrium reading is taken.

    Each axis names a different dimension of the agent's cognitive
    system whose balance can be measured. COGNITION is the balance
    between perception and interpretation. AFFECT is the balance
    between reactivity and regulation. ATTENTION is the balance
    between focus and breadth. MOTIVATION is the balance between
    drive and satiety. IDENTITY is the balance between consistency
    and adaptation. SOCIAL is the balance between self and other.
    """
    COGNITION = "cognition"    # perception vs. interpretation
    AFFECT = "affect"          # reactivity vs. regulation
    ATTENTION = "attention"    # focus vs. breadth
    MOTIVATION = "motivation"  # drive vs. satiety
    IDENTITY = "identity"     # consistency vs. adaptation
    SOCIAL = "social"          # self vs. other


class EquilibriumRegime(str, Enum):
    """The regime an agent's equilibrium occupies, classified by balance.

    Ranges from DESTABILIZED (no balance at all) through UNSTABLE
    (barely holding), OSCILLATING (swinging between poles), BALANCED
    (generally centered with occasional drift), and STABLE
    (well-centered with minor perturbation) to DYNAMIC (actively
    centered, responding without losing balance). The regime is
    derived from the average balance across the agent's readings via
    ``_determine_regime``.
    """
    DESTABILIZED = "destabilized"  # no balance at all
    UNSTABLE = "unstable"          # barely holding
    OSCILLATING = "oscillating"    # swinging between poles
    BALANCED = "balanced"          # generally centered
    STABLE = "stable"              # well-centered
    DYNAMIC = "dynamic"            # actively centered


class BalanceForce(str, Enum):
    """A force that acts on the agent and pulls it away from or toward center.

    Each force names a different pull the agent must regulate. NOVELTY
    pulls toward new input. CONFIRMATION pulls toward what is already
    believed. DISSONANCE pulls toward unresolved conflict. COHERENCE
    pulls toward internal consistency. STRESS pulls toward overload.
    REWARD pulls toward what has paid off before. An equilibrium
    reading records which force is acting on the measured axis, and
    an adjustment record records which force drove a change.
    """
    NOVELTY = "novelty"            # pull toward new input
    CONFIRMATION = "confirmation"  # pull toward existing beliefs
    DISSONANCE = "dissonance"      # pull toward unresolved conflict
    COHERENCE = "coherence"        # pull toward internal consistency
    STRESS = "stress"              # pull toward overload
    REWARD = "reward"              # pull toward prior payoffs


class BalanceStrategy(str, Enum):
    """Strategy for restoring or shifting balance deliberately.

    COMPENSATE countervails against the dominant pull. ACCOMMODATE
    adjusts to absorb the perturbation. ASSIMILATE folds the new
    input into the existing structure. RECALIBRATE resets the center
    deliberately. PRIORITIZE re-weights which axis matters most.
    SUSPEND temporarily releases one axis to regain balance elsewhere.
    Each strategy is suited to a different imbalance, from
    counteracting a strong novelty pull to suspending an overloaded
    axis while the rest of the system re-centers.
    """
    COMPENSATE = "compensate"    # countervail against dominant pull
    ACCOMMODATE = "accommodate"  # adjust to absorb perturbation
    ASSIMILATE = "assimilate"    # fold new input into existing structure
    RECALIBRATE = "recalibrate"  # reset center deliberately
    PRIORITIZE = "prioritize"    # re-weight which axis matters most
    SUSPEND = "suspend"          # temporarily release an axis


class EquilibriumStage(str, Enum):
    """The lifecycle stage of an agent's centering process.

    DISTURBED is the state of being pushed off center. SEEKING is the
    phase of looking for a new balance point. ADJUSTING is the phase
    of applying a strategy to re-center. SETTLING is the state in
    which the new balance is taking hold. CENTERED is the stable
    state of restored balance. TRANSCENDENT is the final state at
    which balance is maintained through change rather than against
    it — the agent responds without losing its center. The engine
    records transitions between stages as CenteringRecord entries.
    """
    DISTURBED = "disturbed"        # pushed off center
    SEEKING = "seeking"            # looking for a new balance point
    ADJUSTING = "adjusting"        # applying a strategy to re-center
    SETTLING = "settling"          # new balance taking hold
    CENTERED = "centered"          # balance restored
    TRANSCENDENT = "transcendent"  # balance maintained through change


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class EquilibriumReading:
    """One observation of balance on a particular axis.

    ``axis`` is the ``EquilibriumAxis`` the reading is taken on.
    ``balance_score`` in [0, 1] measures how centered the agent is on
    that axis — 0 means fully destabilized, 1 means fully centered.
    ``force`` is the ``BalanceForce`` acting on the axis. ``intensity``
    in [0, 1] measures how emphatic the observation was. ``notes`` is
    an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: EquilibriumAxis
    balance_score: float       # 0..1, higher = more centered
    force: BalanceForce
    intensity: float           # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(EquilibriumAxis, self.axis),
            "balance_score": self.balance_score,
            "force": _enum_value(BalanceForce, self.force),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class AdjustmentRecord:
    """One adjustment event that changed the balance on an axis.

    ``axis`` is the ``EquilibriumAxis`` on which the adjustment
    occurred. ``force`` is the ``BalanceForce`` that drove the change.
    ``before_score`` in [0, 1] is the balance before the event;
    ``after_score`` in [0, 1] is the balance after.
    ``adjustment_magnitude`` in [0, ∞) measures how strong the
    adjustment was. ``notes`` is an optional free-form annotation.
    """
    adjustment_id: str
    agent_id: str
    axis: EquilibriumAxis
    force: BalanceForce
    before_score: float          # 0..1, balance before adjustment
    after_score: float           # 0..1, balance after adjustment
    adjustment_magnitude: float  # 0..inf, strength of adjustment
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this adjustment record to a plain dict, expanding enums via ``.value``."""
        return {
            "adjustment_id": self.adjustment_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(EquilibriumAxis, self.axis),
            "force": _enum_value(BalanceForce, self.force),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "adjustment_magnitude": self.adjustment_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class EquilibriumSnapshot:
    """Aggregate equilibrium state for one agent at one moment.

    ``avg_balance`` in [0, 1] is the mean balance score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is
    the most frequent ``EquilibriumAxis`` among those readings, or
    COGNITION if none. ``regime`` is derived via ``_determine_regime``
    from ``avg_balance``. ``adjustment_count`` is the number of
    adjustment events recorded against the agent. ``notes`` is an
    optional free-form annotation.
    """
    snapshot_id: str
    agent_id: str
    avg_balance: float
    dominant_axis: EquilibriumAxis
    regime: EquilibriumRegime
    adjustment_count: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_balance": self.avg_balance,
            "dominant_axis": _enum_value(EquilibriumAxis, self.dominant_axis),
            "regime": _enum_value(EquilibriumRegime, self.regime),
            "adjustment_count": self.adjustment_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BalancePlan:
    """A plan to restore or shift balance with a strategy.

    ``strategy`` is the ``BalanceStrategy`` chosen. ``target_balance``
    in [0, 1] is the balance the plan aims to reach. ``rationale``
    explains why this strategy was chosen for this agent's imbalance.
    A plan is a forward-looking intervention rather than a measurement
    of state, so it does not record the agent's current balance —
    callers who need that should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: BalanceStrategy
    target_balance: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(BalanceStrategy, self.strategy),
            "target_balance": self.target_balance,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class CenteringRecord:
    """One record of a stage transition in the centering lifecycle.

    ``from_stage`` is the ``EquilibriumStage`` the agent was in before
    the transition. ``to_stage`` is the ``EquilibriumStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow seek",
    "sudden centering", "deliberate recalibration").
    """
    center_id: str
    agent_id: str
    from_stage: EquilibriumStage
    to_stage: EquilibriumStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this centering record to a plain dict, expanding enums via ``.value``."""
        return {
            "center_id": self.center_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(EquilibriumStage, self.from_stage),
            "to_stage": _enum_value(EquilibriumStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class EquilibriumProfile:
    """Per-agent aggregate equilibrium tendencies.

    ``avg_balance`` in [0, 1] is the mean balance score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``EquilibriumAxis`` among the agent's readings, or
    COGNITION if none. ``regime`` is derived via ``_determine_regime``
    from ``avg_balance``. ``total_readings``, ``total_adjustments``,
    and ``total_centerings`` are the counts of each record type for
    the agent.
    """
    agent_id: str
    avg_balance: float = 0.0
    dominant_axis: EquilibriumAxis = EquilibriumAxis.COGNITION
    regime: EquilibriumRegime = EquilibriumRegime.OSCILLATING
    total_readings: int = 0
    total_adjustments: int = 0
    total_centerings: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_balance": self.avg_balance,
            "dominant_axis": _enum_value(EquilibriumAxis, self.dominant_axis),
            "regime": _enum_value(EquilibriumRegime, self.regime),
            "total_readings": self.total_readings,
            "total_adjustments": self.total_adjustments,
            "total_centerings": self.total_centerings,
        }


@dataclass
class EquilibriumStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_balance`` is the mean balance score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the
    most frequent regime across all cached profiles, or OSCILLATING
    when none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_adjustments: int = 0
    total_snapshots: int = 0
    total_centerings: int = 0
    avg_balance: float = 0.0
    dominant_regime: EquilibriumRegime = EquilibriumRegime.OSCILLATING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_adjustments": self.total_adjustments,
            "total_snapshots": self.total_snapshots,
            "total_centerings": self.total_centerings,
            "avg_balance": self.avg_balance,
            "dominant_regime": _enum_value(EquilibriumRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveEquilibrium:
    """Thread-safe engine that models an agent's cognitive equilibrium.

    The engine holds six stores: ``_readings`` (EquilibriumReading
    lists keyed by agent_id), ``_adjustments`` (AdjustmentRecord
    lists keyed by agent_id), ``_snapshots`` (EquilibriumSnapshot
    lists keyed by agent_id), ``_plans`` (a flat list of BalancePlan),
    ``_centerings`` (CenteringRecord lists keyed by agent_id), and
    ``_profiles`` (EquilibriumProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The equilibrium model is deliberately heuristic: balance scores
    and intensities are caller-supplied observations; equilibrium
    regimes are banded from the average balance; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how balance is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure balance itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, adjustments, snapshots, or centerings change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose balance scores feed into
    # a snapshot's average balance. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current equilibrium posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty equilibrium engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[EquilibriumReading]] = {}
        self._adjustments: Dict[str, List[AdjustmentRecord]] = {}
        self._snapshots: Dict[str, List[EquilibriumSnapshot]] = {}
        self._plans: List[BalancePlan] = []
        self._centerings: Dict[str, List[CenteringRecord]] = {}
        self._profiles: Dict[str, EquilibriumProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_equilibrium_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._adjustments.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._centerings.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[EquilibriumReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_adjustments_locked(
        self, agent_id: str
    ) -> List[AdjustmentRecord]:
        """Return one agent's adjustment records in insertion order. Caller holds the lock."""
        return list(self._adjustments.get(agent_id, []))

    def _agent_centerings_locked(
        self, agent_id: str
    ) -> List[CenteringRecord]:
        """Return one agent's centering records in insertion order. Caller holds the lock."""
        return list(self._centerings.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[EquilibriumReading]
    ) -> EquilibriumAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns COGNITION if the list is
        empty, since COGNITION is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return EquilibriumAxis.COGNITION
        counts: Counter = Counter()
        first_seen_order: Dict[EquilibriumAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: EquilibriumAxis = readings[0].axis
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
        self, profiles: List[EquilibriumProfile]
    ) -> EquilibriumRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns OSCILLATING if the list is empty, since OSCILLATING
        is the neutral mid-range regime — the band that contains the
        midpoint of the balance scale, neither destabilized nor
        stable. Caller holds the lock.
        """
        if not profiles:
            return EquilibriumRegime.OSCILLATING
        counts: Dict[EquilibriumRegime, int] = {}
        for profile in profiles:
            counts[profile.regime] = counts.get(profile.regime, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> EquilibriumProfile:
        """Aggregate an agent's readings, adjustments, and centerings into a profile.

        See ``EquilibriumProfile`` for field semantics. ``avg_balance``
        is the mean balance score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent
        ``EquilibriumAxis`` among the agent's readings, or COGNITION
        if none. ``regime`` is derived via ``_determine_regime`` from
        ``avg_balance``. ``total_readings``, ``total_adjustments``,
        and ``total_centerings`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        adjustments = self._agent_adjustments_locked(agent_id)
        centerings = self._agent_centerings_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_balance = sum(r.balance_score for r in readings) / len(
                readings
            )
        else:
            avg_balance = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        regime = _determine_regime(avg_balance)

        return EquilibriumProfile(
            agent_id=str(agent_id),
            avg_balance=round(avg_balance, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=total_readings,
            total_adjustments=len(adjustments),
            total_centerings=len(centerings),
        )

    # ── Equilibrium Readings ─────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        balance_score: float,
        force: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> EquilibriumReading:
        """Record an equilibrium reading for an agent and return it.

        ``axis`` may be passed as an ``EquilibriumAxis`` member or its
        string name/value. ``balance_score`` and ``intensity`` are
        clamped to [0, 1]. ``force`` may be passed as a
        ``BalanceForce`` member or its string name/value. The reading
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = EquilibriumReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(EquilibriumAxis, axis),
                balance_score=_clamp(balance_score, 0.0, 1.0),
                force=_resolve_enum(BalanceForce, force),
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
    ) -> List[EquilibriumReading]:
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

    def get_reading(self, reading_id: str) -> EquilibriumReading:
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

    # ── Adjustment Records ────────────────────────────────────────

    def record_adjustment(
        self,
        agent_id: str,
        axis: Any,
        force: Any,
        before_score: float,
        after_score: float,
        adjustment_magnitude: float,
        notes: Optional[str] = None,
    ) -> AdjustmentRecord:
        """Record an adjustment event for an agent and return it.

        ``axis`` may be passed as an ``EquilibriumAxis`` member or
        its string name/value. ``force`` may be passed as a
        ``BalanceForce`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``adjustment_magnitude`` is clamped to [0, ∞). The adjustment
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = AdjustmentRecord(
                adjustment_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(EquilibriumAxis, axis),
                force=_resolve_enum(BalanceForce, force),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                adjustment_magnitude=_clamp_positive_ms(
                    adjustment_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._adjustments.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_adjustments(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AdjustmentRecord]:
        """Return adjustment records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all adjustments are considered;
        otherwise only adjustments for that agent are returned. The
        most recently recorded ``limit`` adjustments are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                adjustments = self._agent_adjustments_locked(agent_id)
            else:
                adjustments = []
                for agent_adjustments in self._adjustments.values():
                    adjustments.extend(agent_adjustments)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return adjustments[-n:] if n else []

    def get_adjustment(self, adjustment_id: str) -> AdjustmentRecord:
        """Retrieve an adjustment record by id.

        Raises ``ValueError`` if no adjustment exists with that id.
        """
        with self._lock:
            for agent_adjustments in self._adjustments.values():
                for adjustment in agent_adjustments:
                    if adjustment.adjustment_id == adjustment_id:
                        return adjustment
        raise ValueError(f"adjustment {adjustment_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> EquilibriumSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_balance`` is the mean balance score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``EquilibriumAxis`` among those readings, or COGNITION if
        none. ``regime`` is derived via ``_determine_regime`` from
        ``avg_balance``. ``adjustment_count`` is the number of
        adjustment events recorded against the agent. The snapshot
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_balance = sum(
                    r.balance_score for r in recent
                ) / len(recent)
            else:
                avg_balance = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_balance)
            adjustment_count = len(
                self._agent_adjustments_locked(agent_id)
            )

            snapshot = EquilibriumSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_balance=round(avg_balance, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                adjustment_count=adjustment_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EquilibriumSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The
        most recently taken ``limit`` snapshots are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                snapshots = list(self._snapshots.get(agent_id, []))
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

    def get_snapshot(self, snapshot_id: str) -> EquilibriumSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Balance Plans ────────────────────────────────────────────

    def plan_balance(
        self,
        agent_id: str,
        strategy: Any,
        target_balance: float,
        rationale: str,
    ) -> BalancePlan:
        """Record a balance plan for an agent and return it.

        ``strategy`` may be passed as a ``BalanceStrategy`` member
        or its string name/value. ``target_balance`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured balance.
        """
        with self._lock:
            plan = BalancePlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(BalanceStrategy, strategy),
                target_balance=_clamp(target_balance, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BalancePlan]:
        """Return balance plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered;
        otherwise only plans for that agent are returned. The most
        recently recorded ``limit`` plans are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                plans = [p for p in self._plans if p.agent_id == agent_id]
            else:
                plans = list(self._plans)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> BalancePlan:
        """Retrieve a balance plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Centering Records ────────────────────────────────────────

    def record_centering(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> CenteringRecord:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as an
        ``EquilibriumStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        seek", "sudden centering", "deliberate recalibration"). The
        centering record is stored and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            record = CenteringRecord(
                center_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(EquilibriumStage, from_stage),
                to_stage=_resolve_enum(EquilibriumStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._centerings.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_centerings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CenteringRecord]:
        """Return centering records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all centerings are considered;
        otherwise only centerings for that agent are returned. The
        most recently recorded ``limit`` centering records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                centerings = self._agent_centerings_locked(agent_id)
            else:
                centerings = []
                for agent_centerings in self._centerings.values():
                    centerings.extend(agent_centerings)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return centerings[-n:] if n else []

    def get_centering(self, center_id: str) -> CenteringRecord:
        """Retrieve a centering record by id.

        Raises ``ValueError`` if no centering record exists with that
        id.
        """
        with self._lock:
            for agent_centerings in self._centerings.values():
                for record in agent_centerings:
                    if record.center_id == center_id:
                        return record
        raise ValueError(f"centering record {center_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> EquilibriumProfile:
        """Return the agent's equilibrium profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, adjustments, snapshots, or
        centerings change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on
        ``EquilibriumProfile`` and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(
        self, agent_id: str, updates: Optional[Dict[str, Any]] = None
    ) -> EquilibriumProfile:
        """Refresh and optionally override fields of an agent's equilibrium profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``updates`` (matching
        ``EquilibriumProfile`` field names) are applied. Accepted
        overrides: ``avg_balance`` (float), ``dominant_axis``
        (``EquilibriumAxis``), ``regime`` (``EquilibriumRegime``),
        ``total_readings``, ``total_adjustments``,
        ``total_centerings`` (int). Enum-valued overrides may be
        passed as the enum member or its string name/value. Unknown
        keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            if updates:
                for key, value in updates.items():
                    if key == "avg_balance":
                        try:
                            profile.avg_balance = float(value)
                        except (TypeError, ValueError):
                            pass
                    elif key == "dominant_axis":
                        try:
                            profile.dominant_axis = _resolve_enum(
                                EquilibriumAxis, value
                            )
                        except ValueError:
                            pass
                    elif key == "regime":
                        try:
                            profile.regime = _resolve_enum(
                                EquilibriumRegime, value
                            )
                        except ValueError:
                            pass
                    elif key in (
                        "total_readings",
                        "total_adjustments",
                        "total_centerings",
                    ):
                        try:
                            setattr(profile, key, int(value))
                        except (TypeError, ValueError):
                            pass
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[EquilibriumProfile]:
        """Return all stored equilibrium profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> EquilibriumStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, adjustments, snapshots, and centerings.
        Scalar totals are the counts of each record type.
        ``avg_balance`` is the mean balance score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        OSCILLATING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        balance via ``_determine_regime`` so the stats always reflect
        real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._adjustments.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._centerings.keys())

            total_readings = 0
            balance_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    balance_sum += reading.balance_score
            avg_balance = (
                round(balance_sum / total_readings, 4) if total_readings else 0.0
            )

            total_adjustments = sum(
                len(agent_adjustments)
                for agent_adjustments in self._adjustments.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_centerings = sum(
                len(agent_centerings)
                for agent_centerings in self._centerings.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average balance so the stats
                # reflect real state rather than the default
                # OSCILLATING.
                dominant_regime = _determine_regime(avg_balance)
            else:
                dominant_regime = EquilibriumRegime.OSCILLATING

            return EquilibriumStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_adjustments=total_adjustments,
                total_snapshots=total_snapshots,
                total_centerings=total_centerings,
                avg_balance=avg_balance,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveEquilibrium] = None
_engine_lock = threading.Lock()


def get_equilibrium_engine() -> AgentCognitiveEquilibrium:
    """Get or create the singleton ``AgentCognitiveEquilibrium`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveEquilibrium()
    return _engine


def reset_equilibrium_engine() -> None:
    """Reset the singleton ``AgentCognitiveEquilibrium`` instance.

    Drops the reference to the current engine so the next
    ``get_equilibrium_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
