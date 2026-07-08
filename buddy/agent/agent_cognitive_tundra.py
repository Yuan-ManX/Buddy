from __future__ import annotations

"""Agent Cognitive Tundra Engine — modeling growth across the frozen field

How concepts freeze, thaw, sprout, and bloom across the cognitive tundra.
A frozen agent holds concepts still beneath ice; a flowering agent's
concepts bloom across the open ground. Distinct from polarization,
coherence, tension, equilibrium, and affinity.
Core capabilities: axis tracking, growth sources, seasonal strategies,
frost-shift stages.

Architecture:
  AgentCognitiveTundra (singleton)
  ├── TundraReading      (one observation of tundra on one axis)
  ├── LichenRecord       (one lichen event that changed tundra)
  ├── TundraSnapshot     (aggregate tundra state for one agent)
  ├── TundraPlan         (a plan to shape the field with a strategy)
  ├── FrostShift         (one stage transition in the frost-shift lifecycle)
  ├── TundraProfile      (per-agent aggregate tundra tendencies)
  └── TundraStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/lichen/etc.

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
    engine with a ``NaN`` or ``None`` tundra. A low-side default is
    safer than a mid-range one for tundra-like quantities where a
    spurious high reading would inflate the perceived tundra and
    push the agent's regime toward DORMANT.
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
    real frost-shift intervals and lichen magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    sprout may apply a large effective lichen.
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
    against member values (e.g. ``"frozen"``) and then against
    member names (e.g. ``"FROZEN"``), so callers may pass either
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


def _determine_regime(avg_tundra: float) -> "TundraRegime":
    """Classify a tundra regime from the average tundra score.

    The average tundra is clamped to [0, 1] where higher means a
    more bloomed, flowering posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is FROZEN
    (locked beneath ice, no growth); below 0.35 it is
    THAWING (weakly warmed, only sprouts under external sun);
    below 0.55 it is SPROUTING (warmly sprouted, retains growth);
    below 0.75 it is FLOWERING (most blooms oriented the
    same way); below 0.9 it is FREEZING (fully chilled, little
    room for more); otherwise it is DORMANT (perfectly locked
    dormancy).
    """
    avg = _clamp(avg_tundra, 0.0, 1.0)
    if avg < 0.15:
        return TundraRegime.FROZEN
    if avg < 0.35:
        return TundraRegime.THAWING
    if avg < 0.55:
        return TundraRegime.SPROUTING
    if avg < 0.75:
        return TundraRegime.FLOWERING
    if avg < 0.9:
        return TundraRegime.FREEZING
    return TundraRegime.DORMANT


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class TundraAxis(str, Enum):
    """The axis along which a tundra reading is taken.

    Each axis names a different dimension of the agent's cognitive
    field whose tundra can be measured. PERMAFROST is the deep
    frozen layer. LICHEN is the crustose cover. MOSS is the soft
    carpet. SHRUB is the woody growth. MIRE is the boggy ground.
    TUNDRA is the overall expanse.
    """
    PERMAFROST = "permafrost"  # deep frozen layer
    LICHEN = "lichen"          # crustose cover
    MOSS = "moss"              # soft carpet
    SHRUB = "shrub"            # woody growth
    MIRE = "mire"              # boggy ground
    TUNDRA = "tundra"          # overall expanse


class TundraRegime(str, Enum):
    """The regime an agent's tundra occupies, classified by tundra.

    Ranges from FROZEN (locked beneath ice, no growth)
    through THAWING (weakly warmed, only sprouts under
    external sun), SPROUTING (warmly sprouted, retains growth),
    FLOWERING (most blooms oriented the same way), and
    FREEZING (fully chilled, little room for more) to DORMANT
    (perfectly locked dormancy). The regime is derived from the
    average tundra across the agent's readings via
    ``_determine_regime``.
    """
    FROZEN = "frozen"          # locked beneath ice
    THAWING = "thawing"        # weakly warmed
    SPROUTING = "sprouting"    # warmly sprouted, retains growth
    FLOWERING = "flowering"    # most blooms oriented
    FREEZING = "freezing"      # fully chilled
    DORMANT = "dormant"        # perfectly locked dormancy


class TundraSource(str, Enum):
    """A source that supplies the warming or cooling force.

    Each source names a different origin of the pull between concepts.
    WIND blows chill across the field. FROST settles cold from above.
    SUN warms the surface. RAIN softens the ground. GRAZER trims the
    growth back. FIRE clears the field entirely. A tundra
    reading records which source supplies the force on the measured
    axis, and a lichen record records which source drove a
    change.
    """
    WIND = "wind"      # blowing chill
    FROST = "frost"    # settling cold
    SUN = "sun"        # warming ray
    RAIN = "rain"      # softening water
    GRAZER = "grazer"  # trimming browser
    FIRE = "fire"      # clearing burn


class TundraStrategy(str, Enum):
    """Strategy for shaping the field deliberately.

    ACCUMULATE packs snow and frost together. THAW warms the ground
    loose. SPROUT pushes new growth up. FLOWER opens the bloom wide.
    FREEZE locks the field still. REST lets the field lie fallow. Each
    strategy is suited to a different field condition, from
    counteracting a frozen field to releasing a flowering one.
    """
    ACCUMULATE = "accumulate"  # pack snow and frost
    THAW = "thaw"              # warm the ground loose
    SPROUT = "sprout"          # push new growth up
    FLOWER = "flower"          # open the bloom wide
    FREEZE = "freeze"          # lock the field still
    REST = "rest"              # let the field lie fallow


class TundraStage(str, Enum):
    """The lifecycle stage of an agent's field-growth process.

    ICE is the state of no growth. THAW is the phase of
    beginning to soften. SPROUT is the state in which most shoots
    push the same way. GROW is the state of strong mutual
    growth. BLOOM is the state at capacity, with little room
    for more. FROST is the final state at which the field is fully
    frosted and unresponsive to new input. The engine records
    transitions between stages as FrostShift entries.
    """
    ICE = "ice"        # no growth
    THAW = "thaw"      # beginning to soften
    SPROUT = "sprout"  # mostly sprouting
    GROW = "grow"      # strongly growing
    BLOOM = "bloom"    # at capacity
    FROST = "frost"    # fully frosted


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TundraReading:
    """One observation of tundra on a particular axis.

    ``axis`` is the ``TundraAxis`` the reading is taken on.
    ``tundra_score`` in [0, 1] measures how flowering the agent is
    on that axis — 0 means fully frozen, 1 means fully blooming.
    ``source`` is the ``TundraSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: TundraAxis
    tundra_score: float    # 0..1, higher = more flowering
    source: TundraSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(TundraAxis, self.axis),
            "tundra_score": self.tundra_score,
            "source": _enum_value(TundraSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class LichenRecord:
    """One lichen event that changed the tundra on an axis.

    ``axis`` is the ``TundraAxis`` on which the lichen occurred.
    ``source`` is the ``TundraSource`` that drove the change.
    ``before_score`` in [0, 1] is the tundra before the event;
    ``after_score`` in [0, 1] is the tundra after.
    ``lichen_magnitude`` in [0, ∞) measures how strong the
    lichen was. ``notes`` is an optional free-form annotation.
    """
    lichen_id: str
    agent_id: str
    axis: TundraAxis
    source: TundraSource
    before_score: float            # 0..1, tundra before lichen
    after_score: float             # 0..1, tundra after lichen
    lichen_magnitude: float    # 0..inf, strength of lichen
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this lichen record to a plain dict, expanding enums via ``.value``."""
        return {
            "lichen_id": self.lichen_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(TundraAxis, self.axis),
            "source": _enum_value(TundraSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "lichen_magnitude": self.lichen_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class TundraSnapshot:
    """Aggregate tundra state for one agent at one moment.

    ``avg_tundra`` in [0, 1] is the mean tundra score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``TundraAxis`` among those readings, or
    PERMAFROST if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_tundra``. ``lichen_count``
    is the number of lichen events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_tundra: float
    dominant_axis: TundraAxis
    regime: TundraRegime
    lichen_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_tundra": self.avg_tundra,
            "dominant_axis": _enum_value(TundraAxis, self.dominant_axis),
            "dominant_regime": _enum_value(TundraRegime, self.regime),
            "regime": _enum_value(TundraRegime, self.regime),
            "lichen_count": self.lichen_count,
            "timestamp": self.timestamp,
        }


@dataclass
class TundraPlan:
    """A plan to shape the field with a strategy.

    ``strategy`` is the ``TundraStrategy`` chosen.
    ``target_tundra`` in [0, 1] is the tundra the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's field condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current tundra — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: TundraStrategy
    target_tundra: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(TundraStrategy, self.strategy),
            "target_tundra": self.target_tundra,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class FrostShift:
    """One record of a stage transition in the frost-shift lifecycle.

    ``from_stage`` is the ``TundraStage`` the agent was in before
    the transition. ``to_stage`` is the ``TundraStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow thaw",
    "sudden bloom", "deliberate sprout").
    """
    shift_id: str
    agent_id: str
    from_stage: TundraStage
    to_stage: TundraStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this frost-shift record to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(TundraStage, self.from_stage),
            "to_stage": _enum_value(TundraStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class TundraProfile:
    """Per-agent aggregate tundra tendencies.

    ``avg_tundra`` in [0, 1] is the mean tundra score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``TundraAxis`` among the agent's readings, or
    PERMAFROST if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_tundra``. ``total_readings``,
    ``total_lichens``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_tundra: float = 0.0
    dominant_axis: TundraAxis = TundraAxis.PERMAFROST
    dominant_regime: TundraRegime = TundraRegime.SPROUTING
    total_readings: int = 0
    total_lichens: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_tundra": self.avg_tundra,
            "dominant_axis": _enum_value(TundraAxis, self.dominant_axis),
            "dominant_regime": _enum_value(TundraRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_lichens": self.total_lichens,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class TundraStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_tundra`` is the mean tundra score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or SPROUTING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_lichens: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_tundra: float = 0.0
    dominant_regime: TundraRegime = TundraRegime.SPROUTING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_lichens": self.total_lichens,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_tundra": self.avg_tundra,
            "dominant_regime": _enum_value(TundraRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveTundra:
    """Thread-safe engine that models an agent's cognitive tundra.

    The engine holds six stores: ``_readings`` (TundraReading lists
    keyed by agent_id), ``_lichens`` (LichenRecord lists keyed by
    agent_id), ``_snapshots`` (TundraSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of TundraPlan),
    ``_frost_shifts`` (FrostShift lists keyed by agent_id), and
    ``_profiles`` (TundraProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The tundra model is deliberately heuristic: tundra scores
    and intensities are caller-supplied observations; tundra
    regimes are banded from the average tundra; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how tundra is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure tundra itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, lichens, snapshots, or frost shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose tundra scores feed into
    # a snapshot's average tundra. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current tundra posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty tundra engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[TundraReading]] = {}
        self._lichens: Dict[str, List[LichenRecord]] = {}
        self._snapshots: Dict[str, List[TundraSnapshot]] = {}
        self._plans: List[TundraPlan] = []
        self._frost_shifts: Dict[str, List[FrostShift]] = {}
        self._profiles: Dict[str, TundraProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton instance is not touched;
        callers that want a fresh singleton should use
        ``reset_tundra_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._lichens.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._frost_shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[TundraReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_lichens_locked(
        self, agent_id: str
    ) -> List[LichenRecord]:
        """Return one agent's lichen records in insertion order. Caller holds the lock."""
        return list(self._lichens.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[TundraSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[TundraPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_frost_shifts_locked(
        self, agent_id: str
    ) -> List[FrostShift]:
        """Return one agent's frost-shift records in insertion order. Caller holds the lock."""
        return list(self._frost_shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[TundraReading]
    ) -> TundraAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns PERMAFROST if the list is
        empty, since PERMAFROST is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return TundraAxis.PERMAFROST
        counts: Counter = Counter()
        first_seen_order: Dict[TundraAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: TundraAxis = readings[0].axis
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
        self, profiles: List[TundraProfile]
    ) -> TundraRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns SPROUTING if the list is empty, since
        SPROUTING is the default regime — the band that
        represents a normally functioning cognitive field that
        retains growth without being flowering, neither
        frozen nor dormant. Caller holds the lock.
        """
        if not profiles:
            return TundraRegime.SPROUTING
        counts: Dict[TundraRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> TundraProfile:
        """Aggregate an agent's readings, lichens, and frost shifts into a profile.

        See ``TundraProfile`` for field semantics. ``avg_tundra``
        is the mean tundra score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``TundraAxis`` among the agent's readings, or PERMAFROST
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_tundra``.
        ``total_readings``, ``total_lichens``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        lichens = self._agent_lichens_locked(agent_id)
        frost_shifts = self._agent_frost_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_tundra = sum(
                r.tundra_score for r in readings
            ) / len(readings)
        else:
            avg_tundra = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_tundra)

        return TundraProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_tundra=round(avg_tundra, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_lichens=len(lichens),
            total_shifts=len(frost_shifts),
            updated_at=_now(),
        )

    # ── Tundra Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        tundra_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> TundraReading:
        """Record a tundra reading for an agent and return it.

        ``axis`` may be passed as a ``TundraAxis`` member or its
        string name/value. ``tundra_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``TundraSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = TundraReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(TundraAxis, axis),
                tundra_score=_clamp(tundra_score, 0.0, 1.0),
                source=_resolve_enum(TundraSource, source),
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
    ) -> List[TundraReading]:
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

    def get_reading(self, reading_id: str) -> TundraReading:
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

    # ── Lichen Records ────────────────────────────────────────

    def record_lichen(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        lichen_magnitude: float,
        notes: Optional[str] = None,
    ) -> LichenRecord:
        """Record a lichen event for an agent and return it.

        ``axis`` may be passed as a ``TundraAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``TundraSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``lichen_magnitude`` is clamped to [0, ∞). The lichen
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = LichenRecord(
                lichen_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(TundraAxis, axis),
                source=_resolve_enum(TundraSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                lichen_magnitude=_clamp_positive_ms(
                    lichen_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._lichens.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_lichens(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LichenRecord]:
        """Return lichen records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all lichens are considered;
        otherwise only lichens for that agent are returned. The
        most recently recorded ``limit`` lichens are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                lichens = self._agent_lichens_locked(agent_id)
            else:
                lichens = []
                for agent_lichens in self._lichens.values():
                    lichens.extend(agent_lichens)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return lichens[-n:] if n else []

    def get_lichen(self, lichen_id: str) -> LichenRecord:
        """Retrieve a lichen record by id.

        Raises ``ValueError`` if no lichen exists with that id.
        """
        with self._lock:
            for agent_lichens in self._lichens.values():
                for lichen in agent_lichens:
                    if lichen.lichen_id == lichen_id:
                        return lichen
        raise ValueError(f"lichen {lichen_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> TundraSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_tundra`` is the mean tundra score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``TundraAxis`` among
        those readings, or PERMAFROST if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_tundra``.
        ``lichen_count`` is the number of lichen events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_tundra = sum(
                    r.tundra_score for r in recent
                ) / len(recent)
            else:
                avg_tundra = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_tundra)
            lichen_count = len(
                self._agent_lichens_locked(agent_id)
            )

            snapshot = TundraSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_tundra=round(avg_tundra, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                lichen_count=lichen_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TundraSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> TundraSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Tundra Plans ────────────────────────────────────────────

    def plan_lichen(
        self,
        agent_id: str,
        strategy: Any,
        target_tundra: float,
        rationale: str,
    ) -> TundraPlan:
        """Record a tundra plan for an agent and return it.

        ``strategy`` may be passed as a ``TundraStrategy`` member
        or its string name/value. ``target_tundra`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured tundra.
        """
        with self._lock:
            plan = TundraPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(TundraStrategy, strategy),
                target_tundra=_clamp(target_tundra, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TundraPlan]:
        """Return tundra plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> TundraPlan:
        """Retrieve a tundra plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Frost-Shift Records ────────────────────────────────────────

    def record_frost_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> FrostShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``TundraStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        thaw", "sudden bloom", "deliberate sprout"). The
        frost-shift record is stored and returned; the agent's cached
        profile is invalidated.

        Frost-shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = FrostShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(TundraStage, from_stage),
                to_stage=_resolve_enum(TundraStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._frost_shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_frost_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FrostShift]:
        """Return frost-shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all frost shifts are considered;
        otherwise only frost shifts for that agent are returned. The
        most recently recorded ``limit`` frost-shift records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                frost_shifts = self._agent_frost_shifts_locked(agent_id)
            else:
                frost_shifts = []
                for agent_frost_shifts in self._frost_shifts.values():
                    frost_shifts.extend(agent_frost_shifts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return frost_shifts[-n:] if n else []

    def get_frost_shift(self, shift_id: str) -> FrostShift:
        """Retrieve a frost-shift record by id.

        Raises ``ValueError`` if no frost-shift record exists with that
        id.
        """
        with self._lock:
            for agent_frost_shifts in self._frost_shifts.values():
                for record in agent_frost_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"frost-shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> TundraProfile:
        """Return the agent's tundra profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, lichens, snapshots, or
        frost shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``TundraProfile``
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
    ) -> TundraProfile:
        """Refresh and optionally override fields of an agent's tundra profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``TundraProfile`` field names) are applied. Accepted
        overrides: ``avg_tundra`` (float), ``dominant_axis``
        (``TundraAxis``), ``dominant_regime``
        (``TundraRegime``), ``total_readings``,
        ``total_lichens``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_tundra":
                    try:
                        profile.avg_tundra = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            TundraAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            TundraRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_lichens",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[TundraProfile]:
        """Return all stored tundra profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> TundraStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, lichens, snapshots, and frost shifts.
        Scalar totals are the counts of each record type.
        ``avg_tundra`` is the mean tundra score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        SPROUTING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        tundra via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._lichens.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._frost_shifts.keys())

            total_readings = 0
            tundra_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    tundra_sum += reading.tundra_score
            avg_tundra = (
                round(tundra_sum / total_readings, 4) if total_readings else 0.0
            )

            total_lichens = sum(
                len(agent_lichens)
                for agent_lichens in self._lichens.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_shifts = sum(
                len(agent_frost_shifts)
                for agent_frost_shifts in self._frost_shifts.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average tundra so the stats
                # reflect real state rather than the default
                # SPROUTING.
                dominant_regime = _determine_regime(avg_tundra)
            else:
                dominant_regime = TundraRegime.SPROUTING

            return TundraStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_lichens=total_lichens,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_tundra=avg_tundra,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveTundra] = None
_engine_lock = threading.Lock()


def get_tundra_engine() -> AgentCognitiveTundra:
    """Get or create the singleton ``AgentCognitiveTundra`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveTundra()
    return _engine


def reset_tundra_engine() -> None:
    """Reset the singleton ``AgentCognitiveTundra`` instance.

    Drops the hold on the current engine so the next
    ``get_tundra_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
