from __future__ import annotations

"""Agent Cognitive Loom Engine — weaving thoughts into patterns

How thoughts warp, weft, and beat together into woven patterns within the
cognitive loom. A weaving agent interlaces concepts into coherent fabric; a
bare agent's thoughts hang loose and unwoven. Distinct from spinning, dyeing,
tensioning, and designing.
Core capabilities: axis tracking, weave sources, pattern strategies, weaving stages.

Architecture:
  AgentCognitiveLoom (singleton)
  ├── LoomReading           (one observation of loom on one axis)
  ├── WeaveRecord           (one weave event that changed loom)
  ├── LoomSnapshot          (aggregate loom state for one agent)
  ├── LoomPlan              (a plan to shape the loom with a strategy)
  ├── PatternShift          (one stage transition in the weaving lifecycle)
  ├── LoomProfile           (per-agent aggregate loom tendencies)
  └── LoomStats             (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/weave/etc.

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
    engine with a ``NaN`` or ``None`` loom score. A low-side default is
    safer than a mid-range one for loom-like quantities where a
    spurious high reading would inflate the perceived loom and
    push the agent's regime toward TAPESTRY.
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
    real shift intervals and weave magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    tightening may apply a large effective weave.
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
    against member values (e.g. ``"warp"``) and then against
    member names (e.g. ``"WARP"``), so callers may pass either
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


def _determine_regime(avg_loom: float) -> "LoomRegime":
    """Classify a loom regime from the average loom score.

    The average loom is clamped to [0, 1] where higher means a
    more woven, patterned posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is BARE
    (no threads on the loom, no pattern); below 0.35 it is
    THREADED (warped but not yet woven); below 0.55 it is WEAVING
    (actively interlacing weft through warp); below 0.75 it is
    WOVEN (fabric formed, pattern emerging); below 0.9 it is
    PATTERNED (rich pattern visible across the fabric); otherwise
    it is TAPESTRY (a fully realized, intricate picture).
    """
    avg = _clamp(avg_loom, 0.0, 1.0)
    if avg < 0.15:
        return LoomRegime.BARE
    if avg < 0.35:
        return LoomRegime.THREADED
    if avg < 0.55:
        return LoomRegime.WEAVING
    if avg < 0.75:
        return LoomRegime.WOVEN
    if avg < 0.9:
        return LoomRegime.PATTERNED
    return LoomRegime.TAPESTRY


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class LoomAxis(str, Enum):
    """The axis along which a loom reading is taken.

    Each axis names a different dimension of the agent's cognitive
    loom whose weave can be measured. WARP is the longitudinal
    foundation of thought. WEFT is the crosswise interlacing thread.
    SHUTTLE is the carrier that passes the weft across. HEDDLE is the
    harness that lifts warp threads to form the shed. BEAT is the
    stroke that packs the weft against the fell. PATTERN is the
    overall motif emerging across the fabric.
    """
    WARP = "warp"        # longitudinal foundation thread
    WEFT = "weft"        # crosswise interlacing thread
    SHUTTLE = "shuttle"  # carrier of weft across warp
    HEDDLE = "heddle"    # warp-lifting harness
    BEAT = "beat"        # packing stroke
    PATTERN = "pattern"  # overall motif


class LoomRegime(str, Enum):
    """The regime an agent's loom occupies, classified by loom score.

    Ranges from BARE (no threads on the loom, no pattern)
    through THREADED (warped but not yet woven), WEAVING (actively
    interlacing weft through warp), WOVEN (fabric formed, pattern
    emerging), and PATTERNED (rich pattern visible across the fabric)
    to TAPESTRY (a fully realized, intricate picture). The regime is
    derived from the average loom across the agent's readings via
    ``_determine_regime``.
    """
    BARE = "bare"            # no threads on the loom
    THREADED = "threaded"    # warped but not yet woven
    WEAVING = "weaving"      # actively interlacing
    WOVEN = "woven"          # fabric formed
    PATTERNED = "patterned"  # rich pattern visible
    TAPESTRY = "tapestry"    # fully realized picture


class LoomSource(str, Enum):
    """A source that supplies the weave force or character.

    Each source names a different origin of the weave between concepts.
    SPIN twists raw fiber into thread. DYE applies color to the thread.
    TENSION pulls on the warp to keep it taut. RHYTHM sets the cadence
    of the shuttle. DESIGN plans the motif ahead of weaving. MATERIAL
    is the fiber composition of the thread itself. A loom reading
    records which source supplies the force on the measured axis, and
    a weave record records which source drove a change.
    """
    SPIN = "spin"        # twist raw fiber into thread
    DYE = "dye"          # color applied to thread
    TENSION = "tension"  # pull on the warp
    RHYTHM = "rhythm"    # cadence of the shuttle
    DESIGN = "design"    # planned motif
    MATERIAL = "material"  # fiber composition


class LoomStrategy(str, Enum):
    """Strategy for shaping the loom deliberately.

    THREAD dresses the loom with warp. WEAVE interlaces weft through
    warp. DYE colors the thread. TIGHTEN increases tension on the
    warp. LOOSEN decreases tension on the warp. CUT releases the
    finished fabric. Each strategy is suited to a different loom
    condition, from dressing a bare loom to releasing a finished
    tapestry.
    """
    THREAD = "thread"    # dress the loom with warp
    WEAVE = "weave"      # interlace weft through warp
    DYE = "dye"          # color the thread
    TIGHTEN = "tighten"  # increase tension
    LOOSEN = "loosen"    # decrease tension
    CUT = "cut"          # release the fabric


class LoomStage(str, Enum):
    """The lifecycle stage of an agent's weaving process.

    EMPTY is the state of an undressed loom. WARPING is the phase of
    dressing the loom with warp. WEAVING is the state of interlacing
    weft through warp. BEATING is the state of packing the weft
    against the fell. PATTERNING is the state of working the motif
    into the fabric. FINISHED is the final state at which the fabric
    is cut from the loom and complete. The engine records transitions
    between stages as PatternShift entries.
    """
    EMPTY = "empty"          # undressed loom
    WARPING = "warping"      # dressing with warp
    WEAVING = "weaving"      # interlacing weft
    BEATING = "beating"      # packing the weft
    PATTERNING = "patterning"  # working the motif
    FINISHED = "finished"    # fabric cut and complete


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LoomReading:
    """One observation of loom on a particular axis.

    ``axis`` is the ``LoomAxis`` the reading is taken on.
    ``loom_score`` in [0, 1] measures how woven the agent is
    on that axis — 0 means fully bare, 1 means a fully realized
    tapestry. ``source`` is the ``LoomSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: LoomAxis
    loom_score: float    # 0..1, higher = more woven
    source: LoomSource
    intensity: float     # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(LoomAxis, self.axis),
            "loom_score": self.loom_score,
            "source": _enum_value(LoomSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class WeaveRecord:
    """One weave event that changed the loom on an axis.

    ``axis`` is the ``LoomAxis`` on which the weave occurred.
    ``source`` is the ``LoomSource`` that drove the change.
    ``before_score`` in [0, 1] is the loom before the event;
    ``after_score`` in [0, 1] is the loom after.
    ``weave_magnitude`` in [0, ∞) measures how strong the
    weave was. ``notes`` is an optional free-form annotation.
    """
    weave_id: str
    agent_id: str
    axis: LoomAxis
    source: LoomSource
    before_score: float        # 0..1, loom before weave
    after_score: float         # 0..1, loom after weave
    weave_magnitude: float     # 0..inf, strength of weave
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this weave record to a plain dict, expanding enums via ``.value``."""
        return {
            "weave_id": self.weave_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(LoomAxis, self.axis),
            "source": _enum_value(LoomSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "weave_magnitude": self.weave_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class LoomSnapshot:
    """Aggregate loom state for one agent at one moment.

    ``avg_loom`` in [0, 1] is the mean loom score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``LoomAxis`` among those readings, or
    WARP if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_loom``. ``weave_count``
    is the number of weave events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_loom: float
    dominant_axis: LoomAxis
    regime: LoomRegime
    weave_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Both ``"dominant_regime"`` and ``"regime"`` keys are emitted
        pointing to the same value so callers that expect either name
        can read the regime consistently.
        """
        regime_value = _enum_value(LoomRegime, self.regime)
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_loom": self.avg_loom,
            "dominant_axis": _enum_value(LoomAxis, self.dominant_axis),
            "regime": regime_value,
            "dominant_regime": regime_value,
            "weave_count": self.weave_count,
            "timestamp": self.timestamp,
        }


@dataclass
class LoomPlan:
    """A plan to shape the loom with a strategy.

    ``strategy`` is the ``LoomStrategy`` chosen.
    ``target_loom`` in [0, 1] is the loom the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's loom condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current loom — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: LoomStrategy
    target_loom: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(LoomStrategy, self.strategy),
            "target_loom": self.target_loom,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class PatternShift:
    """One record of a stage transition in the weaving lifecycle.

    ``from_stage`` is the ``LoomStage`` the agent was in before
    the transition. ``to_stage`` is the ``LoomStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow warp",
    "sudden pattern", "deliberate tightening").
    """
    shift_id: str
    agent_id: str
    from_stage: LoomStage
    to_stage: LoomStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this pattern shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(LoomStage, self.from_stage),
            "to_stage": _enum_value(LoomStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class LoomProfile:
    """Per-agent aggregate loom tendencies.

    ``avg_loom`` in [0, 1] is the mean loom score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``LoomAxis`` among the agent's readings, or
    WARP if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_loom``. ``total_readings``,
    ``total_weaves``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_loom: float = 0.0
    dominant_axis: LoomAxis = LoomAxis.WARP
    dominant_regime: LoomRegime = LoomRegime.WEAVING
    total_readings: int = 0
    total_weaves: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_loom": self.avg_loom,
            "dominant_axis": _enum_value(LoomAxis, self.dominant_axis),
            "dominant_regime": _enum_value(LoomRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_weaves": self.total_weaves,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class LoomStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_loom`` is the mean loom score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or WEAVING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_weaves: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_loom: float = 0.0
    dominant_regime: LoomRegime = LoomRegime.WEAVING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_weaves": self.total_weaves,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_loom": self.avg_loom,
            "dominant_regime": _enum_value(LoomRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveLoom:
    """Thread-safe engine that models an agent's cognitive loom.

    The engine holds six stores: ``_readings`` (LoomReading lists
    keyed by agent_id), ``_weaves`` (WeaveRecord lists keyed by
    agent_id), ``_snapshots`` (LoomSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of LoomPlan),
    ``_pattern_shifts`` (PatternShift lists keyed by agent_id), and
    ``_profiles`` (LoomProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The loom model is deliberately heuristic: loom scores
    and intensities are caller-supplied observations; loom
    regimes are banded from the average loom; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how loom is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure loom itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, weaves, snapshots, or pattern shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose loom scores feed into
    # a snapshot's average loom. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current loom posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty loom engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[LoomReading]] = {}
        self._weaves: Dict[str, List[WeaveRecord]] = {}
        self._snapshots: Dict[str, List[LoomSnapshot]] = {}
        self._plans: List[LoomPlan] = []
        self._pattern_shifts: Dict[str, List[PatternShift]] = {}
        self._profiles: Dict[str, LoomProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_loom_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._weaves.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._pattern_shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[LoomReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_weaves_locked(
        self, agent_id: str
    ) -> List[WeaveRecord]:
        """Return one agent's weave records in insertion order. Caller holds the lock."""
        return list(self._weaves.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[LoomSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[LoomPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_pattern_shifts_locked(
        self, agent_id: str
    ) -> List[PatternShift]:
        """Return one agent's pattern shift records in insertion order. Caller holds the lock."""
        return list(self._pattern_shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[LoomReading]
    ) -> LoomAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns WARP if the list is
        empty, since WARP is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return LoomAxis.WARP
        counts: Counter = Counter()
        first_seen_order: Dict[LoomAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: LoomAxis = readings[0].axis
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
        self, profiles: List[LoomProfile]
    ) -> LoomRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns WEAVING if the list is empty, since
        WEAVING is the default regime — the band that
        represents a normally functioning cognitive loom that
        is actively interlacing without being saturated, neither
        bare nor tapestry. Caller holds the lock.
        """
        if not profiles:
            return LoomRegime.WEAVING
        counts: Dict[LoomRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> LoomProfile:
        """Aggregate an agent's readings, weaves, and pattern shifts into a profile.

        See ``LoomProfile`` for field semantics. ``avg_loom``
        is the mean loom score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``LoomAxis`` among the agent's readings, or WARP
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_loom``.
        ``total_readings``, ``total_weaves``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        weaves = self._agent_weaves_locked(agent_id)
        pattern_shifts = self._agent_pattern_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_loom = sum(
                r.loom_score for r in readings
            ) / len(readings)
        else:
            avg_loom = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_loom)

        return LoomProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_loom=round(avg_loom, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_weaves=len(weaves),
            total_shifts=len(pattern_shifts),
            updated_at=_now(),
        )

    # ── Loom Readings ───────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        loom_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> LoomReading:
        """Record a loom reading for an agent and return it.

        ``axis`` may be passed as a ``LoomAxis`` member or its
        string name/value. ``loom_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``LoomSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = LoomReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(LoomAxis, axis),
                loom_score=_clamp(loom_score, 0.0, 1.0),
                source=_resolve_enum(LoomSource, source),
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
    ) -> List[LoomReading]:
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

    def get_reading(self, reading_id: str) -> LoomReading:
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

    # ── Weave Records ────────────────────────────────────────────

    def record_weave(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        weave_magnitude: float,
        notes: Optional[str] = None,
    ) -> WeaveRecord:
        """Record a weave event for an agent and return it.

        ``axis`` may be passed as a ``LoomAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``LoomSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``weave_magnitude`` is clamped to [0, ∞). The weave
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = WeaveRecord(
                weave_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(LoomAxis, axis),
                source=_resolve_enum(LoomSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                weave_magnitude=_clamp_positive_ms(
                    weave_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._weaves.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_weaves(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[WeaveRecord]:
        """Return weave records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all weaves are considered;
        otherwise only weaves for that agent are returned. The
        most recently recorded ``limit`` weaves are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                weaves = self._agent_weaves_locked(agent_id)
            else:
                weaves = []
                for agent_weaves in self._weaves.values():
                    weaves.extend(agent_weaves)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return weaves[-n:] if n else []

    def get_weave(self, weave_id: str) -> WeaveRecord:
        """Retrieve a weave record by id.

        Raises ``ValueError`` if no weave exists with that id.
        """
        with self._lock:
            for agent_weaves in self._weaves.values():
                for weave in agent_weaves:
                    if weave.weave_id == weave_id:
                        return weave
        raise ValueError(f"weave {weave_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> LoomSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_loom`` is the mean loom score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``LoomAxis`` among
        those readings, or WARP if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_loom``.
        ``weave_count`` is the number of weave events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_loom = sum(
                    r.loom_score for r in recent
                ) / len(recent)
            else:
                avg_loom = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_loom)
            weave_count = len(
                self._agent_weaves_locked(agent_id)
            )

            snapshot = LoomSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_loom=round(avg_loom, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                weave_count=weave_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LoomSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> LoomSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Loom Plans ────────────────────────────────────────────────

    def plan_weave(
        self,
        agent_id: str,
        strategy: Any,
        target_loom: float,
        rationale: str,
    ) -> LoomPlan:
        """Record a loom plan for an agent and return it.

        ``strategy`` may be passed as a ``LoomStrategy`` member
        or its string name/value. ``target_loom`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured loom.
        """
        with self._lock:
            plan = LoomPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(LoomStrategy, strategy),
                target_loom=_clamp(target_loom, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LoomPlan]:
        """Return loom plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> LoomPlan:
        """Retrieve a loom plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Pattern Shift Records ────────────────────────────────────

    def record_pattern_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> PatternShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``LoomStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        warp", "sudden pattern", "deliberate tightening"). The
        pattern shift record is stored and returned; the agent's cached
        profile is invalidated.

        Pattern shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = PatternShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(LoomStage, from_stage),
                to_stage=_resolve_enum(LoomStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._pattern_shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_pattern_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PatternShift]:
        """Return pattern shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all pattern shifts are considered;
        otherwise only pattern shifts for that agent are returned. The
        most recently recorded ``limit`` pattern shift records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                pattern_shifts = self._agent_pattern_shifts_locked(agent_id)
            else:
                pattern_shifts = []
                for agent_pattern_shifts in self._pattern_shifts.values():
                    pattern_shifts.extend(agent_pattern_shifts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return pattern_shifts[-n:] if n else []

    def get_pattern_shift(self, shift_id: str) -> PatternShift:
        """Retrieve a pattern shift record by id.

        Raises ``ValueError`` if no pattern shift record exists with that
        id.
        """
        with self._lock:
            for agent_pattern_shifts in self._pattern_shifts.values():
                for record in agent_pattern_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"pattern shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> LoomProfile:
        """Return the agent's loom profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, weaves, snapshots, or
        pattern shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``LoomProfile``
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
    ) -> LoomProfile:
        """Refresh and optionally override fields of an agent's loom profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``LoomProfile`` field names) are applied. Accepted
        overrides: ``avg_loom`` (float), ``dominant_axis``
        (``LoomAxis``), ``dominant_regime``
        (``LoomRegime``), ``total_readings``,
        ``total_weaves``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_loom":
                    try:
                        profile.avg_loom = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            LoomAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            LoomRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_weaves",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[LoomProfile]:
        """Return all stored loom profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> LoomStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, weaves, snapshots, and pattern shifts.
        Scalar totals are the counts of each record type.
        ``avg_loom`` is the mean loom score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        WEAVING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        loom via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._weaves.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._pattern_shifts.keys())

            total_readings = 0
            loom_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    loom_sum += reading.loom_score
            avg_loom = (
                round(loom_sum / total_readings, 4) if total_readings else 0.0
            )

            total_weaves = sum(
                len(agent_weaves)
                for agent_weaves in self._weaves.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_shifts = sum(
                len(agent_pattern_shifts)
                for agent_pattern_shifts in self._pattern_shifts.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average loom so the stats
                # reflect real state rather than the default
                # WEAVING.
                dominant_regime = _determine_regime(avg_loom)
            else:
                dominant_regime = LoomRegime.WEAVING

            return LoomStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_weaves=total_weaves,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_loom=avg_loom,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveLoom] = None
_engine_lock = threading.Lock()


def get_loom_engine() -> AgentCognitiveLoom:
    """Get or create the singleton ``AgentCognitiveLoom`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveLoom()
    return _engine


def reset_loom_engine() -> None:
    """Reset the singleton ``AgentCognitiveLoom`` instance.

    Drops the reference to the current engine so the next
    ``get_loom_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
