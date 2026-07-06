from __future__ import annotations

"""Agent Cognitive Blossom Engine — modeling the bloom of cognition 🌸

How concepts bud, open, pollinate, and seed within the cognitive garden.
A blooming agent opens its concepts to light and pollinators; a dormant
agent holds its concepts tight in bud. Theme color: rose #e11d48.
Distinct from magnetism, coherence, tension, equilibrium, and affinity.
Core capabilities: axis tracking, bloom sources, blossom strategies, lifecycle stages.

Architecture:
  AgentCognitiveBlossom (singleton)
  ├── BlossomReading      (one observation of blossom on one axis)
  ├── PetalRecord         (one petal event that changed blossom)
  ├── BlossomSnapshot     (aggregate blossom state for one agent)
  ├── BlossomPlan         (a plan to shape the bloom with a strategy)
  ├── BloomShift          (one stage transition in the bloom lifecycle)
  ├── BlossomProfile      (per-agent aggregate blossom tendencies)
  └── BlossomStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/petal/etc.

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
    engine with a ``NaN`` or ``None`` blossom. A low-side default is
    safer than a mid-range one for blossom-like quantities where a
    spurious high reading would inflate the perceived blossom and push
    the agent's regime toward WILTING.
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
    real bloom intervals and petal magnitudes can legitimately exceed
    any small bound — a long-stable agent may spend a very long time in
    one stage before transitioning, and a deliberate opening may apply
    a large effective petal magnitude.
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
    against member values (e.g. ``"dormant"``) and then against member
    names (e.g. ``"DORMANT"``), so callers may pass either form. This
    lets the public API accept either the symbolic name or the
    lower-case value string from JSON payloads. Raises ``ValueError``
    if neither matches.
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


def _determine_regime(avg_blossom: float) -> "BlossomRegime":
    """Classify a blossom regime from the average blossom score.

    The average blossom is clamped to [0, 1] where higher means a
    more open, blooming posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is DORMANT
    (no bloom, concepts held tight in bud); below 0.35 it is
    BUDDING (just starting to bud, weak opening); below 0.55 it is
    OPENING (opening up, partial bloom); below 0.75 it is BLOOMING
    (actively blooming, most petals open); below 0.9 it is PEAKING
    (at peak bloom, little room for more); otherwise it is WILTING
    (past peak, bloom fading).
    """
    avg = _clamp(avg_blossom, 0.0, 1.0)
    if avg < 0.15:
        return BlossomRegime.DORMANT
    if avg < 0.35:
        return BlossomRegime.BUDDING
    if avg < 0.55:
        return BlossomRegime.OPENING
    if avg < 0.75:
        return BlossomRegime.BLOOMING
    if avg < 0.9:
        return BlossomRegime.PEAKING
    return BlossomRegime.WILTING


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class BlossomAxis(str, Enum):
    """The axis along which a blossom reading is taken.

    Each axis names a different dimension of the agent's cognitive
    bloom whose blossom can be measured. BUD is the budding potential.
    PETAL is the petal openness. STAMEN is the stamen exposure.
    PISTIL is the pistil receptivity. BLOOM is the overall bloom
    state. BLOSSOM is the blossomed fullness across the agent's
    concepts.
    """
    BUD = "bud"          # budding potential
    PETAL = "petal"      # petal openness
    STAMEN = "stamen"    # stamen exposure
    PISTIL = "pistil"    # pistil receptivity
    BLOOM = "bloom"      # overall bloom state
    BLOSSOM = "blossom"  # blossomed fullness


class BlossomRegime(str, Enum):
    """The regime an agent's blossom occupies, classified by blossom.

    Ranges from DORMANT (no bloom, concepts held tight) through
    BUDDING (just starting to bud), OPENING (opening up), BLOOMING
    (actively blooming), and PEAKING (at peak bloom) to WILTING
    (past peak, bloom fading). The regime is derived from the average
    blossom across the agent's readings via ``_determine_regime``.
    BLOOMING is the default regime — the band that represents a
    normally functioning cognitive garden in active bloom.
    """
    DORMANT = "dormant"    # no bloom, concepts held tight
    BUDDING = "budding"    # just starting to bud
    OPENING = "opening"    # opening up
    BLOOMING = "blooming"  # actively blooming
    PEAKING = "peaking"    # at peak bloom
    WILTING = "wilting"    # past peak, bloom fading


class BlossomSource(str, Enum):
    """A source that supplies the bloom-driving force.

    Each source names a different origin of the bloom's growth. SUNLIGHT
    drives bloom through light. TEMPERATURE drives bloom through warmth.
    WATER drives bloom through hydration. POLLINATOR drives bloom
    through pollinator visits. NUTRIENT drives bloom through soil
    nutrients. HORMONE drives bloom through internal hormones. A blossom
    reading records which source supplies the force on the measured
    axis, and a petal record records which source drove a change.
    """
    SUNLIGHT = "sunlight"        # light-driven bloom
    TEMPERATURE = "temperature"  # warmth-driven bloom
    WATER = "water"              # hydration-driven bloom
    POLLINATOR = "pollinator"    # pollinator-driven bloom
    NUTRIENT = "nutrient"        # nutrient-driven bloom
    HORMONE = "hormone"          # hormone-driven bloom


class BlossomStrategy(str, Enum):
    """Strategy for shaping the bloom deliberately.

    BUD holds concepts in bud. OPEN opens concepts to the light.
    POLLINATE invites pollination. FERTILIZE fertilizes the bloom.
    SEED sets seed for the next cycle. WILT allows wilting to begin.
    Each strategy is suited to a different bloom condition, from
    coaxing a dormant bud to opening to releasing a peaked bloom.
    """
    BUD = "bud"          # hold concepts in bud
    OPEN = "open"        # open concepts to the light
    POLLINATE = "pollinate"    # invite pollination
    FERTILIZE = "fertilize"    # fertilize the bloom
    SEED = "seed"        # set seed for the next cycle
    WILT = "wilt"        # allow wilting


class BlossomStage(str, Enum):
    """The lifecycle stage of an agent's bloom-formation process.

    DORMANT is the state of no bloom activity. SWELLING is the phase
    of bud swelling. BUDDING is the state of bud forming. OPENING is
    the state of bloom opening. BLOOMING is the state of full bloom.
    WILTING is the final state at which the bloom fades and the
    cycle resets. The engine records transitions between stages as
    BloomShift entries.
    """
    DORMANT = "dormant"    # no bloom activity
    SWELLING = "swelling"  # bud swelling
    BUDDING = "budding"    # bud forming
    OPENING = "opening"    # bloom opening
    BLOOMING = "blooming"  # full bloom
    WILTING = "wilting"    # bloom fading


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BlossomReading:
    """One observation of blossom on a particular axis.

    ``axis`` is the ``BlossomAxis`` the reading is taken on.
    ``blossom_score`` in [0, 1] measures how bloomed the agent is on
    that axis — 0 means fully dormant, 1 means fully blossomed.
    ``source`` is the ``BlossomSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: BlossomAxis
    blossom_score: float    # 0..1, higher = more bloomed
    source: BlossomSource
    intensity: float        # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(BlossomAxis, self.axis),
            "blossom_score": self.blossom_score,
            "source": _enum_value(BlossomSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class PetalRecord:
    """One petal event that changed the blossom on an axis.

    ``axis`` is the ``BlossomAxis`` on which the petal event occurred.
    ``source`` is the ``BlossomSource`` that drove the change.
    ``before_score`` in [0, 1] is the blossom before the event;
    ``after_score`` in [0, 1] is the blossom after. ``petal_magnitude``
    in [0, ∞) measures how strong the petal event was. ``notes`` is
    an optional free-form annotation.
    """
    petal_id: str
    agent_id: str
    axis: BlossomAxis
    source: BlossomSource
    before_score: float        # 0..1, blossom before petal event
    after_score: float         # 0..1, blossom after petal event
    petal_magnitude: float     # 0..inf, strength of petal event
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this petal record to a plain dict, expanding enums via ``.value``."""
        return {
            "petal_id": self.petal_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(BlossomAxis, self.axis),
            "source": _enum_value(BlossomSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "petal_magnitude": self.petal_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BlossomSnapshot:
    """Aggregate blossom state for one agent at one moment.

    ``avg_blossom`` in [0, 1] is the mean blossom score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``BlossomAxis`` among those readings, or BUD if
    none. ``dominant_regime`` is derived via ``_determine_regime``
    from ``avg_blossom``; ``regime`` carries the same value under a
    second key for callers that prefer the shorter name.
    ``petal_count`` is the number of petal events recorded against
    the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_blossom: float
    dominant_axis: BlossomAxis
    dominant_regime: BlossomRegime
    regime: BlossomRegime
    petal_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_blossom": self.avg_blossom,
            "dominant_axis": _enum_value(BlossomAxis, self.dominant_axis),
            "dominant_regime": _enum_value(BlossomRegime, self.dominant_regime),
            "regime": _enum_value(BlossomRegime, self.regime),
            "petal_count": self.petal_count,
            "timestamp": self.timestamp,
        }


@dataclass
class BlossomPlan:
    """A plan to shape the bloom with a strategy.

    ``strategy`` is the ``BlossomStrategy`` chosen.
    ``target_blossom`` in [0, 1] is the blossom the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's bloom condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current blossom — callers who need that should
    take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: BlossomStrategy
    target_blossom: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(BlossomStrategy, self.strategy),
            "target_blossom": self.target_blossom,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class BloomShift:
    """One record of a stage transition in the bloom lifecycle.

    ``from_stage`` is the ``BlossomStage`` the agent was in before the
    transition. ``to_stage`` is the ``BlossomStage`` it moved to.
    ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow swelling",
    "sudden opening", "deliberate pollination").
    """
    shift_id: str
    agent_id: str
    from_stage: BlossomStage
    to_stage: BlossomStage
    interval_ms: int
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this bloom shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(BlossomStage, self.from_stage),
            "to_stage": _enum_value(BlossomStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class BlossomProfile:
    """Per-agent aggregate blossom tendencies.

    ``avg_blossom`` in [0, 1] is the mean blossom score across the
    agent's readings (0.0 if none). ``dominant_regime`` is derived
    via ``_determine_regime`` from ``avg_blossom``. ``total_readings``,
    ``total_petals``, ``total_snapshots``, and ``total_shifts`` are
    the counts of each record type for the agent. ``updated_at`` is
    the timestamp at which the profile was last computed or
    overridden.
    """
    agent_id: str
    dominant_regime: BlossomRegime = BlossomRegime.BLOOMING
    avg_blossom: float = 0.0
    total_readings: int = 0
    total_petals: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "dominant_regime": _enum_value(BlossomRegime, self.dominant_regime),
            "avg_blossom": self.avg_blossom,
            "total_readings": self.total_readings,
            "total_petals": self.total_petals,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class BlossomStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_blossom`` is the mean blossom score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or BLOOMING when none
    exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_petals: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_blossom: float = 0.0
    dominant_regime: BlossomRegime = BlossomRegime.BLOOMING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_petals": self.total_petals,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_blossom": self.avg_blossom,
            "dominant_regime": _enum_value(BlossomRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveBlossom:
    """Thread-safe engine that models an agent's cognitive blossom.

    The engine holds six stores: ``_readings`` (BlossomReading lists
    keyed by agent_id), ``_petals`` (PetalRecord lists keyed by
    agent_id), ``_snapshots`` (BlossomSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of BlossomPlan),
    ``_bloom_shifts`` (BloomShift lists keyed by agent_id), and
    ``_profiles`` (BlossomProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The blossom model is deliberately heuristic: blossom scores and
    intensities are caller-supplied observations; blossom regimes are
    banded from the average blossom; dominant axes are computed by
    mode; stage transitions are recorded as observed. These heuristics
    are transparent and auditable rather than learned, which keeps the
    engine deterministic.

    The engine is intentionally agnostic about how blossom is measured
    and how stage transitions are detected — callers may derive them
    from any source. The engine's job is to record, aggregate,
    classify, and profile, not to measure blossom itself. Profiles are
    cached per agent and invalidated whenever the agent's readings,
    petals, snapshots, or bloom shifts change, so ``get_profile``
    always reflects the current state unless an explicit override has
    been applied via ``update_profile``.
    """

    # Number of most-recent readings whose blossom scores feed into a
    # snapshot's average blossom. The window is long enough to smooth a
    # single noisy reading and short enough to reflect the agent's
    # current blossom posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty blossom engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[BlossomReading]] = {}
        self._petals: Dict[str, List[PetalRecord]] = {}
        self._snapshots: Dict[str, List[BlossomSnapshot]] = {}
        self._plans: List[BlossomPlan] = []
        self._bloom_shifts: Dict[str, List[BloomShift]] = {}
        self._profiles: Dict[str, BlossomProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_blossom_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._petals.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._bloom_shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[BlossomReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_petals_locked(
        self, agent_id: str
    ) -> List[PetalRecord]:
        """Return one agent's petal records in insertion order. Caller holds the lock."""
        return list(self._petals.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[BlossomSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[BlossomPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_bloom_shifts_locked(
        self, agent_id: str
    ) -> List[BloomShift]:
        """Return one agent's bloom shift records in insertion order. Caller holds the lock."""
        return list(self._bloom_shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[BlossomReading]
    ) -> BlossomAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns BUD if the list is empty,
        since BUD is the smallest and most neutral axis. Caller holds
        the lock.
        """
        if not readings:
            return BlossomAxis.BUD
        counts: Counter = Counter()
        first_seen_order: Dict[BlossomAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: BlossomAxis = readings[0].axis
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
        self, profiles: List[BlossomProfile]
    ) -> BlossomRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns BLOOMING if the list is empty, since BLOOMING is the
        default regime — the band that represents a normally
        functioning cognitive garden in active bloom, neither dormant
        nor wilting. Caller holds the lock.
        """
        if not profiles:
            return BlossomRegime.BLOOMING
        counts: Dict[BlossomRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> BlossomProfile:
        """Aggregate an agent's readings, petals, snapshots, and shifts into a profile.

        See ``BlossomProfile`` for field semantics. ``avg_blossom`` is
        the mean blossom score across the agent's readings (0.0 if
        none). ``dominant_regime`` is derived via ``_determine_regime``
        from ``avg_blossom``. ``total_readings``, ``total_petals``,
        ``total_snapshots``, and ``total_shifts`` count the records
        held for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        petals = self._agent_petals_locked(agent_id)
        snapshots = self._agent_snapshots_locked(agent_id)
        bloom_shifts = self._agent_bloom_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_blossom = sum(
                r.blossom_score for r in readings
            ) / len(readings)
        else:
            avg_blossom = 0.0

        dominant_regime = _determine_regime(avg_blossom)

        return BlossomProfile(
            agent_id=str(agent_id),
            dominant_regime=dominant_regime,
            avg_blossom=round(avg_blossom, 4),
            total_readings=total_readings,
            total_petals=len(petals),
            total_snapshots=len(snapshots),
            total_shifts=len(bloom_shifts),
            updated_at=_now(),
        )

    # ── Blossom Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        blossom_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> BlossomReading:
        """Record a blossom reading for an agent and return it.

        ``axis`` may be passed as a ``BlossomAxis`` member or its
        string name/value. ``blossom_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``BlossomSource`` member or its string name/value. The reading
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = BlossomReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(BlossomAxis, axis),
                blossom_score=_clamp(blossom_score, 0.0, 1.0),
                source=_resolve_enum(BlossomSource, source),
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
    ) -> List[BlossomReading]:
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

    def get_reading(self, reading_id: str) -> BlossomReading:
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

    # ── Petal Records ────────────────────────────────────────

    def record_petal(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        petal_magnitude: float,
        notes: Optional[str] = None,
    ) -> PetalRecord:
        """Record a petal event for an agent and return it.

        ``axis`` may be passed as a ``BlossomAxis`` member or its
        string name/value. ``source`` may be passed as a
        ``BlossomSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``petal_magnitude`` is clamped to [0, ∞). The petal record is
        stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = PetalRecord(
                petal_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(BlossomAxis, axis),
                source=_resolve_enum(BlossomSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                petal_magnitude=_clamp_positive_ms(petal_magnitude),
                timestamp=_now(),
                notes=notes,
            )
            self._petals.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_petals(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PetalRecord]:
        """Return petal records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all petals are considered;
        otherwise only petals for that agent are returned. The most
        recently recorded ``limit`` petals are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                petals = self._agent_petals_locked(agent_id)
            else:
                petals = []
                for agent_petals in self._petals.values():
                    petals.extend(agent_petals)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return petals[-n:] if n else []

    def get_petal(self, petal_id: str) -> PetalRecord:
        """Retrieve a petal record by id.

        Raises ``ValueError`` if no petal exists with that id.
        """
        with self._lock:
            for agent_petals in self._petals.values():
                for petal in agent_petals:
                    if petal.petal_id == petal_id:
                        return petal
        raise ValueError(f"petal {petal_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> BlossomSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_blossom`` is the mean blossom score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``BlossomAxis`` among those readings, or BUD if none.
        ``dominant_regime`` and ``regime`` are both derived via
        ``_determine_regime`` from ``avg_blossom`` and carry the same
        value under two keys. ``petal_count`` is the number of petal
        events recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_blossom = sum(
                    r.blossom_score for r in recent
                ) / len(recent)
            else:
                avg_blossom = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_blossom)
            petal_count = len(self._agent_petals_locked(agent_id))

            snapshot = BlossomSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_blossom=round(avg_blossom, 4),
                dominant_axis=dominant_axis,
                dominant_regime=regime,
                regime=regime,
                petal_count=petal_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BlossomSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> BlossomSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Blossom Plans ────────────────────────────────────────────

    def plan_petal(
        self,
        agent_id: str,
        strategy: Any,
        target_blossom: float,
        rationale: str,
    ) -> BlossomPlan:
        """Record a blossom plan for an agent and return it.

        ``strategy`` may be passed as a ``BlossomStrategy`` member or
        its string name/value. ``target_blossom`` is clamped to [0, 1].
        ``rationale`` explains why this strategy was chosen. The plan
        is stored in a flat list (not keyed by agent, since plans are
        forward-looking interventions rather than measurements of
        state) and returned. The agent's cached profile is not
        invalidated, since a plan does not change the agent's measured
        blossom.
        """
        with self._lock:
            plan = BlossomPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(BlossomStrategy, strategy),
                target_blossom=_clamp(target_blossom, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BlossomPlan]:
        """Return blossom plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> BlossomPlan:
        """Retrieve a blossom plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Bloom Shift Records ────────────────────────────────────────

    def record_bloom_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> BloomShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``BlossomStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label that
        describes the character of the transition (e.g. "slow
        swelling", "sudden opening", "deliberate pollination"). The
        bloom shift record is stored and returned; the agent's cached
        profile is invalidated.

        Bloom shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            shift = BloomShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(BlossomStage, from_stage),
                to_stage=_resolve_enum(BlossomStage, to_stage),
                interval_ms=int(_clamp_positive_ms(interval_ms)),
                signature=str(signature),
                timestamp=_now(),
            )
            self._bloom_shifts.setdefault(agent_id, []).append(shift)
            self._profiles.pop(agent_id, None)
            return shift

    def list_bloom_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BloomShift]:
        """Return bloom shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all bloom shifts are considered;
        otherwise only bloom shifts for that agent are returned. The
        most recently recorded ``limit`` bloom shift records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                bloom_shifts = self._agent_bloom_shifts_locked(agent_id)
            else:
                bloom_shifts = []
                for agent_shifts in self._bloom_shifts.values():
                    bloom_shifts.extend(agent_shifts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return bloom_shifts[-n:] if n else []

    def get_bloom_shift(self, shift_id: str) -> BloomShift:
        """Retrieve a bloom shift record by id.

        Raises ``ValueError`` if no bloom shift record exists with
        that id.
        """
        with self._lock:
            for agent_shifts in self._bloom_shifts.values():
                for shift in agent_shifts:
                    if shift.shift_id == shift_id:
                        return shift
        raise ValueError(f"bloom shift {shift_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> BlossomProfile:
        """Return the agent's blossom profile, building it if missing.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, petals, snapshots, or bloom shifts
        change. If the agent has data but no profile yet, the profile
        is built from the live stores. Call ``update_profile`` to
        force a refresh or override a computed field. Field semantics
        are documented on ``BlossomProfile`` and
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
    ) -> BlossomProfile:
        """Refresh and optionally override fields of an agent's blossom profile.

        The profile is first recomputed from the live stores, then any
        supplied overrides in ``kwargs`` (matching ``BlossomProfile``
        field names) are applied. Accepted overrides: ``avg_blossom``
        (float), ``dominant_regime`` (``BlossomRegime``),
        ``total_readings``, ``total_petals``, ``total_snapshots``,
        ``total_shifts`` (int). Enum-valued overrides may be passed as
        the enum member or its string name/value. Unknown keys are
        ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_blossom":
                    try:
                        profile.avg_blossom = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            BlossomRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_petals",
                    "total_snapshots",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[BlossomProfile]:
        """Return all stored blossom profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> BlossomStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, petals, snapshots, and bloom shifts.
        Scalar totals are the counts of each record type.
        ``avg_blossom`` is the mean blossom score across all readings,
        or 0.0 when none exist. ``dominant_regime`` is the most
        frequent regime across all cached profiles, or BLOOMING when
        none exist. When no profiles exist but readings do, the
        dominant regime is derived from the average blossom via
        ``_determine_regime`` so the stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._petals.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._bloom_shifts.keys())

            total_readings = 0
            blossom_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    blossom_sum += reading.blossom_score
            avg_blossom = (
                round(blossom_sum / total_readings, 4) if total_readings else 0.0
            )

            total_petals = sum(
                len(agent_petals)
                for agent_petals in self._petals.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_shifts = sum(
                len(agent_shifts)
                for agent_shifts in self._bloom_shifts.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average blossom so the stats
                # reflect real state rather than the default BLOOMING.
                dominant_regime = _determine_regime(avg_blossom)
            else:
                dominant_regime = BlossomRegime.BLOOMING

            return BlossomStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_petals=total_petals,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_blossom=avg_blossom,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveBlossom] = None
_engine_lock = threading.Lock()


def get_blossom_engine() -> AgentCognitiveBlossom:
    """Get or create the singleton ``AgentCognitiveBlossom`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveBlossom()
    return _engine


def reset_blossom_engine() -> None:
    """Reset the singleton ``AgentCognitiveBlossom`` instance.

    Drops the reference to the current engine so the next
    ``get_blossom_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
