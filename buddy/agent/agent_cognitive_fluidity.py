"""Agent Cognitive Fluidity Engine — smoothness of mental flow

Fluidity measures how gracefully ideas move through the cognitive stream,
distinct from cadence, momentum, inertia, and resonance.

Core capabilities:
  - Per-axis readings, stutters, regimes, plans, cascades, profiles, stats

Architecture:
  AgentCognitiveFluidity (singleton)
  ├── FluidityReading       (one observation of cognitive flow)
  ├── StutterRecord         (one recorded interruption of flow)
  ├── FluiditySnapshot      (aggregate fluidity state for one agent)
  ├── FlowPlan              (a plan to restore fluidity)
  ├── CascadeRecord         (one record of a fluidity-stage transition)
  ├── FluidityProfile       (per-agent aggregate fluidity tendencies)
  └── FluidityStats         (engine-wide aggregate statistics)
"""

from __future__ import annotations

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
    trivially interchangeable for testing.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/stutter/snapshot/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` flow score. A low-side default is
    safer than a mid-range one for fluidity-like quantities where a
    spurious high reading would inflate the perceived flow and mask
    real blockage.
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
    """Clamp a millisecond interval to a non-negative value.

    Recovery times must be non-negative; negative values are coerced to
    0 rather than rejected so a misconfigured caller cannot crash the
    engine. The upper bound is left open because real recovery times
    can legitimately span seconds or minutes when the agent has been
    badly stuck.
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
    against member values (e.g. ``"choked"``) and then against member
    names (e.g. ``"CHOKED"``), so callers may pass either form. This
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


def _determine_regime(avg_flow: float) -> "FluidityRegime":
    """Classify a fluidity regime from the average flow score.

    The average is clamped to [0, 1] where higher means more fluid.
    The checks are applied in order, so the first matching band wins:
    below 0.15 the mind is CHOKED (total blockage, no flow); below
    0.35 it is LABORED (heavy, effortful flow); below 0.55 it is
    SMOOTH (normal, untroubled flow); below 0.75 it is FLOWING (good
    easy flow); below 0.9 it is STREAMING (fast, smooth, sustained
    flow); otherwise it is EFFORTLESS (flow without effort). The
    bands mirror the fluid-dynamics progression from a stopped pipe
    through a turbulent stream to a supersonic jet.
    """
    avg = _clamp(avg_flow, 0.0, 1.0)
    if avg < 0.15:
        return FluidityRegime.CHOKED
    if avg < 0.35:
        return FluidityRegime.LABORED
    if avg < 0.55:
        return FluidityRegime.SMOOTH
    if avg < 0.75:
        return FluidityRegime.FLOWING
    if avg < 0.9:
        return FluidityRegime.STREAMING
    return FluidityRegime.EFFORTLESS


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class FluidityAxis(str, Enum):
    """The channel of cognitive flow a reading or record pertains to.

    The agent's thought stream is a confluence of channels, each of
    which can have its own fluidity. REASONING is the flow of deductive
    and inductive inference. ASSOCIATION is the flow of associative
    connections between ideas. EXPRESSION is the flow of verbal and
    symbolic articulation. TRANSITION is the flow between topics or
    frames. INTEGRATION is the flow of synthesis that combines
    disparate pieces into a whole. RESPONSE is the flow of reactive
    answers to inputs and questions. The engine tracks fluidity on
    each axis independently so an agent can be fluid in one channel
    and stuck in another.
    """
    REASONING = "reasoning"        # deductive/inductive inference
    ASSOCIATION = "association"    # associative connections
    EXPRESSION = "expression"      # verbal/symbolic articulation
    TRANSITION = "transition"      # movement between topics/frames
    INTEGRATION = "integration"    # synthesis of disparate pieces
    RESPONSE = "response"          # reactive answers to inputs


class FluidityRegime(str, Enum):
    """The regime of fluidity an agent occupies, classified by flow score.

    Ranges from CHOKED (total blockage) through LABORED (heavy
    effortful flow), SMOOTH (normal untroubled flow), FLOWING (good
    easy flow), and STREAMING (fast smooth sustained flow) to
    EFFORTLESS (flow without effort). See ``_determine_regime`` for
    the band thresholds. The labels are borrowed from fluid-dynamics
    imagery to give the bands an intuitive feel.
    """
    CHOKED = "choked"          # total blockage, no flow
    LABORED = "labored"        # heavy, effortful flow
    SMOOTH = "smooth"          # normal, untroubled flow
    FLOWING = "flowing"        # good, easy flow
    STREAMING = "streaming"    # fast, smooth, sustained flow
    EFFORTLESS = "effortless"  # flow without effort


class BlockerKind(str, Enum):
    """What is in the way of smooth cognitive flow.

    CONFUSION is uncertainty about which way to go. RIGIDITY is
    fixation on a single approach. FATIGUE is exhaustion. DOUBT is
    second-guessing. OVERLOAD is too much at once. STUCK is total
    gridlock. The blocker labels the cause of the stutter so the
    right flow strategy can be chosen.
    """
    CONFUSION = "confusion"    # uncertainty about direction
    RIGIDITY = "rigidity"      # fixation on one approach
    FATIGUE = "fatigue"        # exhaustion
    DOUBT = "doubt"            # second-guessing
    OVERLOAD = "overload"      # too much at once
    STUCK = "stuck"            # total gridlock


class FlowStrategy(str, Enum):
    """Strategy for restoring fluidity when flow is low.

    CLEAR removes the immediate blocker. EASE reduces the effort
    required. GUIDE directs the flow when the agent is lost.
    CHANNEL focuses the flow when the agent is spreading too thin.
    ACCELERATE pushes the flow forward. RELEASE lets go of what is
    blocking — surrendering a fixation, dropping a doubt, releasing a
    tension. Each strategy suits a different blocker and regime.
    """
    CLEAR = "clear"            # remove the immediate blocker
    EASE = "ease"              # reduce the effort required
    GUIDE = "guide"            # direct the flow
    CHANNEL = "channel"        # focus the flow
    ACCELERATE = "accelerate"  # push the flow forward
    RELEASE = "release"        # let go of what is blocking


class FluidityStage(str, Enum):
    """The lifecycle stage of the agent's fluidity.

    STALLED is total arrest. UNCLOGGING is the first signs of flow
    returning. GLIDING is established smooth flow. SURGING is
    accelerating high-energy flow. CRESTING is the peak of the
    current cycle. SETTLING is flow coming to rest. The engine
    records transitions between these stages as CascadeRecord
    entries, capturing the from-stage, to-stage, and the interval.
    """
    STALLED = "stalled"        # total arrest
    UNCLOGGING = "unclogging"  # first signs of flow
    GLIDING = "gliding"        # established smooth flow
    SURGING = "surging"        # accelerating high-energy flow
    CRESTING = "cresting"      # peak of current cycle
    SETTLING = "settling"      # flow coming to rest


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FluidityReading:
    """One observation of cognitive flow on one axis.

    ``axis`` is the ``FluidityAxis`` the reading pertains to.
    ``flow_score`` in [0, 1] is the observed smoothness of flow at the
    moment of the reading (0 = total blockage, 1 = perfect flow).
    ``blocker`` is the ``BlockerKind`` in the way, or ``None`` when no
    specific blocker is observed. ``intensity`` in [0, 1] is how
    strongly the flow was felt — a high-intensity reading is one the
    agent noticed and registered; a low-intensity reading is one that
    passed in the background. ``notes`` is an optional free-form
    annotation.
    """
    reading_id: str
    agent_id: str
    axis: FluidityAxis
    flow_score: float           # 0..1, observed smoothness of flow
    blocker: Optional[BlockerKind]
    intensity: float            # 0..1, strength of the reading
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``.

        The ``blocker`` may be ``None``; if so it is serialized as
        ``None``. The ``axis`` and ``blocker`` enums are expanded to
        their lower-case value strings so the result is JSON-clean.
        """
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(FluidityAxis, self.axis),
            "flow_score": self.flow_score,
            "blocker": _enum_value(BlockerKind, self.blocker) if self.blocker is not None else None,
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class StutterRecord:
    """One recorded interruption of cognitive flow.

    ``axis`` is the ``FluidityAxis`` where the stutter occurred.
    ``blocker`` is the ``BlockerKind`` that caused the stutter.
    ``before_score`` in [0, 1] is the flow score immediately before
    the stutter; ``after_score`` in [0, 1] is the flow score
    immediately after the stutter resolved. ``recovery_ms`` in [0, ∞)
    is the wall-clock milliseconds it took to recover. ``notes`` is
    an optional free-form annotation.
    """
    stutter_id: str
    agent_id: str
    axis: FluidityAxis
    blocker: BlockerKind
    before_score: float         # 0..1, flow before stutter
    after_score: float          # 0..1, flow after recovery
    recovery_ms: float          # 0..inf, time to recover
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this stutter record to a plain dict, expanding enums."""
        return {
            "stutter_id": self.stutter_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(FluidityAxis, self.axis),
            "blocker": _enum_value(BlockerKind, self.blocker),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "recovery_ms": self.recovery_ms,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class FluiditySnapshot:
    """Aggregate fluidity state for one agent at one moment.

    ``avg_flow`` in [0, 1] is the mean flow score across the agent's
    recent readings, or 0.0 if none. ``dominant_axis`` is the most
    frequent ``FluidityAxis`` among those readings, or REASONING if
    none. ``regime`` is derived from ``avg_flow`` via
    ``_determine_regime``. ``stutter_count`` is the number of stutter
    records the agent currently has. ``notes`` is an optional
    free-form annotation.
    """
    snapshot_id: str
    agent_id: str
    avg_flow: float
    dominant_axis: FluidityAxis
    regime: FluidityRegime
    stutter_count: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_flow": self.avg_flow,
            "dominant_axis": _enum_value(FluidityAxis, self.dominant_axis),
            "regime": _enum_value(FluidityRegime, self.regime),
            "stutter_count": self.stutter_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class FlowPlan:
    """A plan to restore or enhance an agent's fluidity.

    ``strategy`` is the ``FlowStrategy`` chosen. ``target_flow`` in
    [0, 1] is the flow score the plan aims to reach; ``current_flow``
    in [0, 1] is the flow score at the time the plan was made.
    ``rationale`` explains why this strategy was chosen for this
    blocker or regime. The plan is forward-looking — it does not
    itself change the agent's measured fluidity, only records an
    intention to act.
    """
    plan_id: str
    agent_id: str
    strategy: FlowStrategy
    target_flow: float
    current_flow: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(FlowStrategy, self.strategy),
            "target_flow": self.target_flow,
            "current_flow": self.current_flow,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class CascadeRecord:
    """One record of a fluidity-stage transition.

    ``from_stage`` is the ``FluidityStage`` the agent was in before
    the transition. ``to_stage`` is the ``FluidityStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the milliseconds the from-stage
    held before the transition. ``signature`` is a short free-form
    label for the transition (e.g. ``"cleared-blocker"``,
    ``"accelerated-into-flow"``). ``notes`` is an optional free-form
    annotation.
    """
    cascade_id: str
    agent_id: str
    from_stage: FluidityStage
    to_stage: FluidityStage
    interval_ms: float
    signature: str
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this cascade record to a plain dict, expanding enums via ``.value``."""
        return {
            "cascade_id": self.cascade_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(FluidityStage, self.from_stage),
            "to_stage": _enum_value(FluidityStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class FluidityProfile:
    """Per-agent aggregate fluidity tendencies.

    ``avg_flow`` in [0, 1] is the mean flow score across the agent's
    readings (0.0 if none). ``dominant_axis`` is the most frequent
    ``FluidityAxis`` among the agent's readings, or REASONING if none.
    ``regime`` is derived via ``_determine_regime`` from ``avg_flow``.
    ``total_readings``, ``total_stutters``, and ``total_cascades`` are
    the counts of each record type for the agent.
    """
    agent_id: str
    avg_flow: float = 0.0
    dominant_axis: FluidityAxis = FluidityAxis.REASONING
    regime: FluidityRegime = FluidityRegime.SMOOTH
    total_readings: int = 0
    total_stutters: int = 0
    total_cascades: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_flow": self.avg_flow,
            "dominant_axis": _enum_value(FluidityAxis, self.dominant_axis),
            "regime": _enum_value(FluidityRegime, self.regime),
            "total_readings": self.total_readings,
            "total_stutters": self.total_stutters,
            "total_cascades": self.total_cascades,
            "last_updated": self.last_updated,
        }


@dataclass
class FluidityStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids that have at
    least one record. ``avg_flow`` is the mean flow score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all agent profiles, or SMOOTH when none
    exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_stutters: int = 0
    total_snapshots: int = 0
    total_cascades: int = 0
    avg_flow: float = 0.0
    dominant_regime: FluidityRegime = FluidityRegime.SMOOTH

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_stutters": self.total_stutters,
            "total_snapshots": self.total_snapshots,
            "total_cascades": self.total_cascades,
            "avg_flow": self.avg_flow,
            "dominant_regime": _enum_value(FluidityRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveFluidity:
    """Thread-safe engine that models an agent's cognitive fluidity.

    The engine holds six stores: ``_readings`` (FluidityReading lists
    keyed by agent_id), ``_stutters`` (StutterRecord lists keyed by
    agent_id), ``_snapshots`` (FluiditySnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of FlowPlan), ``_cascades``
    (CascadeRecord lists keyed by agent_id), and ``_profiles``
    (FluidityProfile by agent_id, cached and invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The fluidity model is deliberately heuristic: flow scores, blocker
    labels, and intensities are caller-supplied observations; regimes
    are banded from the agent's average flow; dominant axes are
    computed by mode. These heuristics are transparent and auditable
    rather than learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how flow scores are
    measured and how blockers are detected — callers may derive them
    from any source. The engine's job is to record, aggregate,
    classify, and plan, not to detect fluidity itself. Profiles are
    cached per agent and invalidated whenever the agent's readings,
    stutters, snapshots, or cascades change, so ``get_profile`` always
    reflects the current state unless an explicit override has been
    applied via ``update_profile``.
    """

    # Number of most-recent readings whose flow scores feed into a
    # snapshot's average flow. The window is long enough to smooth a
    # single noisy reading and short enough to reflect the agent's
    # current fluidity posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty fluidity engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[FluidityReading]] = {}
        self._stutters: Dict[str, List[StutterRecord]] = {}
        self._snapshots: Dict[str, List[FluiditySnapshot]] = {}
        self._plans: List[FlowPlan] = []
        self._cascades: Dict[str, List[CascadeRecord]] = {}
        self._profiles: Dict[str, FluidityProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_fluidity_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._stutters.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._cascades.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[FluidityReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_stutters_locked(self, agent_id: str) -> List[StutterRecord]:
        """Return one agent's stutter records in insertion order. Caller holds the lock."""
        return list(self._stutters.get(agent_id, []))

    def _agent_snapshots_locked(self, agent_id: str) -> List[FluiditySnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_cascades_locked(self, agent_id: str) -> List[CascadeRecord]:
        """Return one agent's cascade records in insertion order. Caller holds the lock."""
        return list(self._cascades.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[FluidityReading]
    ) -> Optional[FluidityAxis]:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns ``None`` if the list is empty.
        Caller holds the lock.
        """
        if not readings:
            return None
        counts: Counter = Counter()
        first_seen_order: Dict[FluidityAxis, int] = {}
        for index, reading in enumerate(readings):
            ax = reading.axis
            counts[ax] += 1
            if ax not in first_seen_order:
                first_seen_order[ax] = index
        best_axis: FluidityAxis = readings[0].axis
        best_count = -1
        for ax, count in counts.items():
            if (count > best_count) or (
                count == best_count
                and first_seen_order.get(ax, 0) < first_seen_order.get(best_axis, 0)
            ):
                best_axis = ax
                best_count = count
        return best_axis

    def _avg_flow_locked(self, agent_id: str) -> float:
        """Return the mean flow score across the agent's readings.

        Returns 0.0 when the agent has no readings. Caller holds the
        lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        return sum(r.flow_score for r in readings) / len(readings)

    def _current_flow_locked(self, agent_id: str) -> float:
        """Return the agent's most recent flow score, or the mean if no recent.

        Prefers the flow score of the most recent reading, falling back
        to the mean of all readings when there is no clear most recent
        one. Returns 0.0 when the agent has no readings. Caller holds
        the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        most_recent = readings[-1]
        if most_recent.flow_score is not None:
            return float(most_recent.flow_score)
        return self._avg_flow_locked(agent_id)

    def _mode_regime_locked(
        self, profiles: List[FluidityProfile]
    ) -> FluidityRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns SMOOTH if the list is empty, since SMOOTH is the
        neutral regime. Caller holds the lock.
        """
        if not profiles:
            return FluidityRegime.SMOOTH
        counts: Dict[FluidityRegime, int] = {}
        for profile in profiles:
            counts[profile.regime] = counts.get(profile.regime, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> FluidityProfile:
        """Aggregate an agent's readings, stutters, and cascades into a profile.

        See ``FluidityProfile`` for field semantics. ``avg_flow`` is
        the mean flow score across the agent's readings, or 0.0 if
        none. ``dominant_axis`` is the most frequent ``FluidityAxis``
        among the agent's readings, or REASONING if none. ``regime``
        is derived via ``_determine_regime`` from ``avg_flow``.
        ``total_readings``, ``total_stutters``, and ``total_cascades``
        count the records held for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        stutters = self._agent_stutters_locked(agent_id)
        cascades = self._agent_cascades_locked(agent_id)

        avg_flow = self._avg_flow_locked(agent_id)
        regime = _determine_regime(avg_flow)
        dominant_axis = self._mode_axis_locked(readings)
        if dominant_axis is None:
            dominant_axis = FluidityAxis.REASONING

        return FluidityProfile(
            agent_id=str(agent_id),
            avg_flow=round(avg_flow, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=len(readings),
            total_stutters=len(stutters),
            total_cascades=len(cascades),
            last_updated=_now(),
        )

    # ── Fluidity Readings ──────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        flow_score: float,
        blocker: Any = None,
        intensity: float = 0.5,
        notes: Optional[str] = None,
    ) -> FluidityReading:
        """Record a fluidity reading for an agent and return it.

        ``axis`` may be passed as a ``FluidityAxis`` member or its
        string name/value. ``flow_score`` in [0, 1] is clamped to
        that range. ``blocker`` may be passed as a ``BlockerKind``
        member, its string name/value, or ``None`` for no blocker.
        ``intensity`` in [0, 1] is clamped to that range. The reading
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        # Resolve blocker outside the lock to keep the lock scope tight.
        # ``None`` is permitted; passing any other value goes through
        # ``_resolve_enum`` so callers may pass names or values.
        resolved_blocker: Optional[BlockerKind]
        if blocker is None:
            resolved_blocker = None
        else:
            resolved_blocker = _resolve_enum(BlockerKind, blocker)
        with self._lock:
            reading = FluidityReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(FluidityAxis, axis),
                flow_score=_clamp(flow_score, 0.0, 1.0),
                blocker=resolved_blocker,
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
    ) -> List[FluidityReading]:
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

    def get_reading(self, reading_id: str) -> FluidityReading:
        """Retrieve a reading by id.

        Raises ``ValueError`` if no reading exists with that id, so
        callers can treat the return as a guaranteed non-None value
        and let a single exception type stand in for a not-found error.
        """
        with self._lock:
            for agent_readings in self._readings.values():
                for reading in agent_readings:
                    if reading.reading_id == reading_id:
                        return reading
        raise ValueError(f"reading {reading_id!r} not found")

    # ── Stutter Records ───────────────────────────────────────────

    def record_stutter(
        self,
        agent_id: str,
        axis: Any,
        blocker: Any,
        before_score: float,
        after_score: float,
        recovery_ms: float,
        notes: Optional[str] = None,
    ) -> StutterRecord:
        """Record a stutter for an agent and return it.

        ``axis`` may be passed as a ``FluidityAxis`` member or its
        string name/value. ``blocker`` may be passed as a
        ``BlockerKind`` member or its string name/value.
        ``before_score`` and ``after_score`` in [0, 1] are clamped to
        that range. ``recovery_ms`` in [0, ∞) is clamped to that
        range. The stutter is stored and returned; the agent's
        cached profile is invalidated.
        """
        with self._lock:
            stutter = StutterRecord(
                stutter_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(FluidityAxis, axis),
                blocker=_resolve_enum(BlockerKind, blocker),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                recovery_ms=_clamp_positive_ms(recovery_ms),
                timestamp=_now(),
                notes=notes,
            )
            self._stutters.setdefault(agent_id, []).append(stutter)
            self._profiles.pop(agent_id, None)
            return stutter

    def list_stutters(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StutterRecord]:
        """Return stutter records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all stutters are considered;
        otherwise only stutters for that agent are returned. The most
        recently recorded ``limit`` stutters are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                stutters = self._agent_stutters_locked(agent_id)
            else:
                stutters = []
                for agent_stutters in self._stutters.values():
                    stutters.extend(agent_stutters)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return stutters[-n:] if n else []

    def get_stutter(self, stutter_id: str) -> StutterRecord:
        """Retrieve a stutter record by id.

        Raises ``ValueError`` if no stutter exists with that id.
        """
        with self._lock:
            for agent_stutters in self._stutters.values():
                for stutter in agent_stutters:
                    if stutter.stutter_id == stutter_id:
                        return stutter
        raise ValueError(f"stutter {stutter_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> FluiditySnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_flow`` is the mean flow score across the agent's most
        recent readings (the last ``_SNAPSHOT_READING_WINDOW`` = 20),
        or 0.0 if none. ``dominant_axis`` is the most frequent
        ``FluidityAxis`` among those readings, or REASONING if none.
        ``regime`` is derived from ``avg_flow`` via
        ``_determine_regime``. ``stutter_count`` is the number of
        stutter records the agent currently has. The snapshot is
        stored and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_flow = sum(r.flow_score for r in recent) / len(recent)
            else:
                avg_flow = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            if dominant_axis is None:
                dominant_axis = FluidityAxis.REASONING

            regime = _determine_regime(avg_flow)
            stutter_count = len(self._agent_stutters_locked(agent_id))

            snapshot = FluiditySnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_flow=round(avg_flow, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                stutter_count=stutter_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FluiditySnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> FluiditySnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Flow Plans ────────────────────────────────────────────────

    def plan_flow(
        self,
        agent_id: str,
        strategy: Any,
        target_flow: float,
        rationale: str,
    ) -> FlowPlan:
        """Record a flow plan for an agent and return it.

        ``strategy`` may be passed as a ``FlowStrategy`` member or its
        string name/value. ``target_flow`` in [0, 1] is clamped to
        that range. ``current_flow`` is derived from the agent's
        readings (most-recent flow score or mean if none) and clamped
        to [0, 1]. ``rationale`` explains why this strategy was
        chosen for this blocker or regime. The plan is stored in a
        flat list (not keyed by agent, since plans are forward-looking
        interventions rather than measurements of state) and returned.
        The agent's cached profile is not invalidated, since a plan
        does not change the agent's measured fluidity.
        """
        with self._lock:
            current_flow = _clamp(
                self._current_flow_locked(agent_id), 0.0, 1.0
            )
            plan = FlowPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(FlowStrategy, strategy),
                target_flow=_clamp(target_flow, 0.0, 1.0),
                current_flow=current_flow,
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FlowPlan]:
        """Return flow plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> FlowPlan:
        """Retrieve a flow plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Cascade Records ───────────────────────────────────────────

    def record_cascade(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str = "",
        notes: Optional[str] = None,
    ) -> CascadeRecord:
        """Record a cascade (stage transition) for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``FluidityStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is clamped to that range.
        ``signature`` is a short free-form label for the transition
        (e.g. ``"cleared-blocker"``, ``"accelerated-into-flow"``). The
        cascade is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            cascade = CascadeRecord(
                cascade_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(FluidityStage, from_stage),
                to_stage=_resolve_enum(FluidityStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
                notes=notes,
            )
            self._cascades.setdefault(agent_id, []).append(cascade)
            self._profiles.pop(agent_id, None)
            return cascade

    def list_cascades(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CascadeRecord]:
        """Return cascade records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all cascades are considered;
        otherwise only cascades for that agent are returned. The most
        recently recorded ``limit`` cascades are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                cascades = self._agent_cascades_locked(agent_id)
            else:
                cascades = []
                for agent_cascades in self._cascades.values():
                    cascades.extend(agent_cascades)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return cascades[-n:] if n else []

    def get_cascade(self, cascade_id: str) -> CascadeRecord:
        """Retrieve a cascade record by id.

        Raises ``ValueError`` if no cascade exists with that id.
        """
        with self._lock:
            for agent_cascades in self._cascades.values():
                for cascade in agent_cascades:
                    if cascade.cascade_id == cascade_id:
                        return cascade
        raise ValueError(f"cascade {cascade_id!r} not found")

    # ── Profiles ───────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> FluidityProfile:
        """Return the agent's fluidity profile, computing it if absent.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, stutters, snapshots, or cascades change.
        If the agent has data but no profile yet, one is built from
        the existing data. Call ``update_profile`` to force a refresh
        or override a computed field. Field semantics are documented
        on ``FluidityProfile`` and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> FluidityProfile:
        """Refresh and optionally override fields of an agent's fluidity profile.

        The profile is first recomputed from the live stores, then any
        supplied keyword overrides (matching ``FluidityProfile`` field
        names) are applied, and ``last_updated`` is stamped. Accepted
        overrides: ``avg_flow`` (float), ``dominant_axis``
        (``FluidityAxis``), ``regime`` (``FluidityRegime``),
        ``total_readings``, ``total_stutters``, ``total_cascades``
        (int). Enum-valued overrides may be passed as the enum member
        or its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_flow":
                    try:
                        profile.avg_flow = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(FluidityAxis, value)
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(FluidityRegime, value)
                    except ValueError:
                        pass
                elif key in ("total_readings", "total_stutters", "total_cascades"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[FluidityProfile]:
        """Return all stored fluidity profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> FluidityStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids that
        appear in any store. ``total_readings``, ``total_stutters``,
        ``total_snapshots``, and ``total_cascades`` are the counts of
        each record type. ``avg_flow`` is the mean flow score across
        all readings, or 0.0 when none exist. ``dominant_regime`` is
        the most frequent regime across all cached profiles, or
        SMOOTH when none exist. When no profiles are cached but
        readings exist, the dominant regime is derived from the
        average flow via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            total_readings = 0
            flow_sum = 0.0
            for agent_id, readings in self._readings.items():
                agent_ids.add(agent_id)
                total_readings += len(readings)
                for reading in readings:
                    flow_sum += reading.flow_score

            total_stutters = 0
            for agent_id, stutters in self._stutters.items():
                agent_ids.add(agent_id)
                total_stutters += len(stutters)

            total_snapshots = 0
            for agent_id, snapshots in self._snapshots.items():
                agent_ids.add(agent_id)
                total_snapshots += len(snapshots)

            total_cascades = 0
            for agent_id, cascades in self._cascades.items():
                agent_ids.add(agent_id)
                total_cascades += len(cascades)

            for plan in self._plans:
                agent_ids.add(plan.agent_id)

            avg_flow = (
                round(flow_sum / total_readings, 4) if total_readings else 0.0
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive the
                # regime from the average flow so the stats reflect real
                # state rather than the default SMOOTH.
                dominant_regime = _determine_regime(avg_flow)
            else:
                dominant_regime = FluidityRegime.SMOOTH

            return FluidityStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_stutters=total_stutters,
                total_snapshots=total_snapshots,
                total_cascades=total_cascades,
                avg_flow=avg_flow,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveFluidity] = None
_engine_lock = threading.Lock()


def get_fluidity_engine() -> AgentCognitiveFluidity:
    """Get or create the singleton ``AgentCognitiveFluidity`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveFluidity()
    return _engine


def reset_fluidity_engine() -> None:
    """Reset the singleton ``AgentCognitiveFluidity`` instance.

    Drops the reference so the next ``get_fluidity_engine`` call
    creates a fresh instance. Useful for tests that need a clean
    engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
