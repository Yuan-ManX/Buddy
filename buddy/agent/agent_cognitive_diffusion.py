from __future__ import annotations

"""Agent Cognitive Diffusion — spread of conceptual activation through the cognitive network

Activation spreads from highly active nodes to their neighbours along the
cognitive graph, like a solute diffusing through a solvent, until equalized.

Core capabilities:
  - Concentration Readings: per-node activation levels in each medium
  - Diffusion Events: spreads from source to targets with rate and barrier
  - Regime Classification: stagnant, slow, steady, rapid, saturated, oscillatory
  - Gradient Direction: expanding, contracting, stable, reversing, pulsing
  - Equalization Plans: accelerate, dampen, channel, insulate, seed, drain
Architecture:
  AgentCognitiveDiffusion (singleton)
  ├── ConcentrationReading, DiffusionEvent  (readings, spread events)
  ├── DiffusionSnapshot, EqualizationPlan   (aggregate regime, strategy)
  ├── GradientRecord, DiffusionProfile      (concentration deltas, per-agent)
  └── DiffusionStats                        (engine-wide statistics)
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/event/plan/etc."""
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` concentration. This keeps the field
    values honest even when upstream producers are loose with types.
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


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"belief_network"``) and then against member names
    (e.g. ``"BELIEF_NETWORK"``), so callers may pass either form. Raises
    ``ValueError`` if neither matches, so a bad medium or strategy surfaces
    immediately rather than silently falling back.
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

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction. The fallback keeps serialization from raising when a
    caller has stuffed a raw string into an enum-typed field.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_regime(avg_rate: float, spread_count: int) -> "DiffusionRegime":
    """Classify a diffusion regime from an average rate and spread count.

    ``avg_rate`` in [0, 1] is the mean rate of recent diffusion events.
    ``spread_count`` is how many target nodes the recent spread reached.
    The bands partition the [0, 1] rate range into qualitative regimes.
    Lower rates mean activation is barely moving (STAGNANT, SLOW);
    moderate rates mean a consistent spread (STEADY); high rates mean a
    fast spread (RAPID); near-total rates mean the field has fully
    diffused (SATURATED). If no spreading happened at all
    (``spread_count == 0``) the regime is STAGNANT regardless of rate,
    since a rate without spread is meaningless.
    """
    if spread_count == 0:
        return DiffusionRegime.STAGNANT
    rate = _clamp(avg_rate, 0.0, 1.0)
    if rate < 0.1:
        return DiffusionRegime.STAGNANT
    if rate < 0.3:
        return DiffusionRegime.SLOW
    if rate < 0.6:
        return DiffusionRegime.STEADY
    if rate < 0.85:
        return DiffusionRegime.RAPID
    return DiffusionRegime.SATURATED


def _determine_gradient_direction(
    concentrations: List[float],
) -> "GradientDirection":
    """Classify a gradient direction from an ordered concentration series.

    The series is the agent's recent ``ConcentrationReading`` values for a
    single medium, in capture order. The classifier inspects the deltas
    between consecutive readings to decide how the gradient is moving.

    With fewer than two readings the gradient is unknowable and defaults
    to STABLE. PULSING is detected when the deltas alternate sign
    repeatedly (at least two sign flips and at least half the deltas flip),
    indicating rhythmic expansion and contraction. REVERSING is detected
    when the early trend and the late trend point in opposite directions,
    meaning the gradient has flipped mid-window. Otherwise the overall
    trend decides: rising concentrations mean EXPANDING, falling mean
    CONTRACTING, and a flat series means STABLE.
    """
    if len(concentrations) < 2:
        return GradientDirection.STABLE
    eps = 0.01
    deltas = [
        concentrations[i + 1] - concentrations[i]
        for i in range(len(concentrations) - 1)
    ]
    # PULSING: deltas flip sign often enough that the field is oscillating.
    sign_changes = 0
    for i in range(len(deltas) - 1):
        a = deltas[i]
        b = deltas[i + 1]
        if abs(a) >= eps and abs(b) >= eps and (a > 0) != (b > 0):
            sign_changes += 1
    if sign_changes >= 2 and sign_changes >= max(1, len(deltas) // 2):
        return GradientDirection.PULSING
    # REVERSING: the first half trends one way and the second half the other.
    mid = len(deltas) // 2
    first_half = deltas[:mid] if mid > 0 else [0.0]
    second_half = deltas[mid:] if deltas[mid:] else [0.0]
    first_mean = sum(first_half) / len(first_half) if first_half else 0.0
    second_mean = sum(second_half) / len(second_half) if second_half else 0.0
    if first_mean > eps and second_mean < -eps:
        return GradientDirection.REVERSING
    if first_mean < -eps and second_mean > eps:
        return GradientDirection.REVERSING
    # Overall trend across the whole window.
    overall = concentrations[-1] - concentrations[0]
    if overall > eps:
        return GradientDirection.EXPANDING
    if overall < -eps:
        return GradientDirection.CONTRACTING
    return GradientDirection.STABLE


def _safe_int(value: Any, default: int) -> int:
    """Coerce ``value`` to a non-negative int, falling back to ``default``."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    if n < 0:
        n = 0
    return n


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class DiffusionMedium(str, Enum):
    """The medium through which conceptual activation spreads.

    Activation does not spread through a single uniform substrate. The
    cognitive graph is layered, and each layer has its own topology and
    its own resistance to flow. Tracking each medium separately lets the
    engine tell apart an agent whose beliefs are stuck but whose
    attention is fluid from one whose attention is stuck but whose
    concepts are fluid — qualitatively different states that a single
    blended field would collapse.

    BELIEF_NETWORK spreads activation through belief connections: when
    one belief fires, the beliefs that support or depend on it warm too.
    CONCEPT_GRAPH spreads through concept-similarity links: an active
    concept primes its semantic neighbours. MEMORY_FIELD spreads through
    associative memory: a salient cue evokes linked memories.
    ATTENTION_FIELD spreads through attention allocation: attending to
    one thing pulls attention to related things. EMOTIONAL_FIELD spreads
    through affective links: an affective state tints the concepts and
    beliefs associated with it.
    """
    BELIEF_NETWORK = "belief_network"    # through belief connections
    CONCEPT_GRAPH = "concept_graph"      # through concept similarity links
    MEMORY_FIELD = "memory_field"       # through associative memory
    ATTENTION_FIELD = "attention_field"  # through attention allocation
    EMOTIONAL_FIELD = "emotional_field"  # through affective links


class DiffusionRegime(str, Enum):
    """The regime a medium occupies, classified by its spread rate.

    A regime is a qualitative characterization of how fast activation is
    moving through the medium, more informative than the raw rate alone.
    STAGNANT means almost nothing is spreading — the field is frozen and
    the gradient is doing no work. SLOW means activation is moving but
    barely, as if through a viscous medium. STEADY means a consistent,
    moderate spread, the healthy working state. RAPID means activation is
    flooding outward quickly, which can be generative or can wash out
    structure. SATURATED means the field has already equalized: there is
    no gradient left to drive spread, and the medium has reached a
    uniform level. OSCILLATORY means activation is sloshing back and
    forth rather than monotonically equalizing, the way a standing wave
    refuses to settle.
    """
    STAGNANT = "stagnant"        # minimal spread, field frozen
    SLOW = "slow"                # gradual spread, viscous medium
    STEADY = "steady"            # consistent spread, working state
    RAPID = "rapid"              # fast spread, flooding outward
    SATURATED = "saturated"      # fully diffused, gradient gone
    OSCILLATORY = "oscillatory"  # back-and-forth spread, sloshing


class GradientDirection(str, Enum):
    """The direction in which the concentration gradient is moving.

    A gradient is not a static quantity; it has a direction of change.
    EXPANDING means the high-concentration region is spreading outward,
    the gradient is doing work and the field is opening up.
    CONTRACTING means the high-concentration region is receding inward,
    the spread is losing ground and the field is closing down. STABLE
    means the field is at or near equilibrium, the gradient is flat and
    nothing is moving. REVERSING means the direction has flipped — what
    was expanding is now contracting, or vice versa — a regime change in
    the field. PULSING means the gradient is oscillating rhythmically
    between expansion and contraction, neither settling nor collapsing.
    """
    EXPANDING = "expanding"    # spreading outward
    CONTRACTING = "contracting"  # receding inward
    STABLE = "stable"          # at equilibrium
    REVERSING = "reversing"    # direction changing
    PULSING = "pulsing"        # rhythmic expansion/contraction


class DiffusionBarrier(str, Enum):
    """The resistance a region of the cognitive graph offers to diffusion.

    Barriers are not defects. A cognitive field with no barriers at all
    would equalize instantly and lose all structure: every concept would
    carry the same activation, and no region could hold a distinct
    posture. The useful state is enough permeability that activation can
    reach where it is needed, with enough barriers that distinct regions
    keep their identity and a gradient can persist.

    NONE offers no resistance; activation flows freely. PARTIAL offers
    some resistance, slowing but not stopping the spread. SELECTIVE is
    permeable to some concepts but not others — a belief may be open to
    revision by evidence from one source but not another. STRONG offers
    high resistance, holding a region nearly intact against outside
    activation. IMPERMEABLE is a complete block, isolating one region
    of the cognitive graph from the rest entirely.
    """
    NONE = "none"              # no barrier, free flow
    PARTIAL = "partial"        # some resistance
    SELECTIVE = "selective"    # permeable to some concepts only
    STRONG = "strong"          # high resistance
    IMPERMEABLE = "impermeable"  # complete block


class EqualizationStrategy(str, Enum):
    """Strategies for steering a medium toward or away from equalization.

    Equalization is not always desirable. Sometimes the agent wants the
    field to equalize — to let a stuck belief absorb activation from its
    neighbours so the gradient relaxes. Sometimes the agent wants the
    opposite — to keep a region concentrated, or to drain an
    over-activated region. The strategy must match the intent.

    ACCELERATE speeds up equalization so the gradient relaxes faster.
    DAMPEN slows the spread so a region keeps its concentration longer.
    CHANNEL directs the spread through a specific path rather than letting
    it diffuse omnidirectionally. INSULATE isolates a region to protect
    or contain it, raising a barrier against outside flow. SEED injects
    new concentration at a node to start a spread where there was none.
    DRAIN removes concentration from a node to stop a spread that has
    gone too far.
    """
    ACCELERATE = "accelerate"  # speed up equalization
    DAMPEN = "dampen"          # slow down spread
    CHANNEL = "channel"        # direct through a specific path
    INSULATE = "insulate"      # isolate a region
    SEED = "seed"              # inject new concentration
    DRAIN = "drain"            # remove concentration


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ConcentrationReading:
    """One observed activation level at one node in one medium.

    A reading is the atomic observation of the diffusion field: at a
    moment in time, this node of the cognitive graph carried this much
    activation in this medium. ``reading_id`` uniquely identifies the
    reading. ``agent_id`` is the agent whose field was sampled.
    ``medium`` is the ``DiffusionMedium`` the reading belongs to, since
    the same node can carry different concentrations in different media.
    ``node_id`` is a human-readable label for the node (e.g. a concept
    name, a belief id, a memory handle). ``concentration`` in [0, 1] is
    the activation level at the node, where 0 means the node is dark and
    1 means it is fully lit. ``timestamp`` is when the reading was taken.
    """
    reading_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    medium: DiffusionMedium = DiffusionMedium.CONCEPT_GRAPH
    node_id: str = ""
    concentration: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding the enum via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "medium": _enum_value(DiffusionMedium, self.medium),
            "node_id": self.node_id,
            "concentration": self.concentration,
            "timestamp": self.timestamp,
        }


@dataclass
class DiffusionEvent:
    """A record of one spread of activation from a source to its targets.

    An event captures one discrete diffusion step: activation moved from
    ``source_node`` to the nodes in ``target_nodes``, at a certain
    ``rate``, against a certain ``barrier``. ``event_id`` uniquely
    identifies the event. ``agent_id`` is the agent whose field spread.
    ``medium`` is the ``DiffusionMedium`` the spread occurred in.
    ``source_node`` is the node the activation flowed out of.
    ``target_nodes`` is the ordered list of nodes it flowed into.
    ``rate`` in [0, 1] is how much of the source's concentration
    transferred, clamped to that range. ``barrier`` is the
    ``DiffusionBarrier`` the spread had to overcome. ``timestamp`` is
    when the event was recorded.
    """
    event_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    medium: DiffusionMedium = DiffusionMedium.CONCEPT_GRAPH
    source_node: str = ""
    target_nodes: List[str] = field(default_factory=list)
    rate: float = 0.0
    barrier: DiffusionBarrier = DiffusionBarrier.NONE
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict, expanding the enums via ``.value``."""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "medium": _enum_value(DiffusionMedium, self.medium),
            "source_node": self.source_node,
            "target_nodes": list(self.target_nodes),
            "rate": self.rate,
            "barrier": _enum_value(DiffusionBarrier, self.barrier),
            "timestamp": self.timestamp,
        }


@dataclass
class DiffusionSnapshot:
    """An aggregate view of an agent's diffusion in one medium at a point in time.

    A snapshot summarizes the agent's recent readings and events for a
    single medium. ``snapshot_id`` uniquely identifies the snapshot.
    ``agent_id`` is the agent the snapshot summarizes. ``medium`` is the
    ``DiffusionMedium`` the snapshot covers. ``regime`` is the
    ``DiffusionRegime`` derived from the mean event rate and spread count
    via ``_determine_regime``. ``gradient_direction`` is the
    ``GradientDirection`` derived from the recent concentration series
    via ``_determine_gradient_direction``. ``avg_concentration`` in [0, 1]
    is the mean concentration across the agent's recent readings in this
    medium. ``spread_count`` is how many target nodes the recent spread
    reached. ``timestamp`` is when the snapshot was taken.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    medium: DiffusionMedium = DiffusionMedium.CONCEPT_GRAPH
    regime: DiffusionRegime = DiffusionRegime.STAGNANT
    gradient_direction: GradientDirection = GradientDirection.STABLE
    avg_concentration: float = 0.0
    spread_count: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "medium": _enum_value(DiffusionMedium, self.medium),
            "regime": _enum_value(DiffusionRegime, self.regime),
            "gradient_direction": _enum_value(
                GradientDirection, self.gradient_direction
            ),
            "avg_concentration": self.avg_concentration,
            "spread_count": self.spread_count,
            "timestamp": self.timestamp,
        }


@dataclass
class EqualizationPlan:
    """A strategy and target set for steering a medium's diffusion.

    When the agent wants to change how a medium is equalizing, it files
    a plan. ``plan_id`` uniquely identifies the plan. ``agent_id`` is the
    agent the plan is for. ``medium`` is the ``DiffusionMedium`` the plan
    targets. ``strategy`` is the ``EqualizationStrategy`` selected to
    steer the field. ``target_nodes`` is the ordered list of nodes the
    strategy should act on. ``expected_rate`` in [0, 1] is the rate the
    plan expects to achieve, recorded at plan time so the actual effect
    can later be compared. ``rationale`` is a free-form explanation of
    why this strategy was chosen for these targets. ``timestamp`` is
    when the plan was created.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    medium: DiffusionMedium = DiffusionMedium.CONCEPT_GRAPH
    strategy: EqualizationStrategy = EqualizationStrategy.ACCELERATE
    target_nodes: List[str] = field(default_factory=list)
    expected_rate: float = 0.0
    rationale: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding the enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "medium": _enum_value(DiffusionMedium, self.medium),
            "strategy": _enum_value(EqualizationStrategy, self.strategy),
            "target_nodes": list(self.target_nodes),
            "expected_rate": self.expected_rate,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class GradientRecord:
    """One observed concentration change at a node, with its direction.

    A gradient record captures a single step in the field's evolution:
    the concentration at a node moved from ``from_concentration`` to
    ``to_concentration``, with a signed ``delta``. ``record_id`` uniquely
    identifies the record. ``agent_id`` is the agent whose field changed.
    ``medium`` is the ``DiffusionMedium`` the change occurred in.
    ``direction`` is the ``GradientDirection`` the caller attributes the
    change to. ``from_concentration`` and ``to_concentration`` in [0, 1]
    are the concentration before and after the change. ``delta`` is
    ``to_concentration - from_concentration``, computed at record time.
    ``timestamp`` is when the change was recorded.
    """
    record_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    medium: DiffusionMedium = DiffusionMedium.CONCEPT_GRAPH
    direction: GradientDirection = GradientDirection.STABLE
    from_concentration: float = 0.0
    to_concentration: float = 0.0
    delta: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this gradient record to a plain dict, expanding the enums via ``.value``."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "medium": _enum_value(DiffusionMedium, self.medium),
            "direction": _enum_value(GradientDirection, self.direction),
            "from_concentration": self.from_concentration,
            "to_concentration": self.to_concentration,
            "delta": self.delta,
            "timestamp": self.timestamp,
        }


@dataclass
class DiffusionProfile:
    """Per-agent aggregate diffusion tendencies.

    A profile summarizes one agent's diffusion posture across all media.
    ``agent_id`` is the agent this profile describes. ``avg_concentration``
    in [0, 1] is the mean concentration across all of the agent's
    readings. ``dominant_medium`` is the ``DiffusionMedium`` the agent has
    the most readings in, or ``None`` if the agent has no readings.
    ``regime`` is the ``DiffusionRegime`` derived from the agent's event
    rates and spread count. ``total_readings``, ``total_events``, and
    ``total_plans`` are the counts of those records for the agent.
    ``last_updated`` is the timestamp of the most recent profile change.
    """
    agent_id: str = ""
    avg_concentration: float = 0.0
    dominant_medium: Optional[DiffusionMedium] = None
    regime: DiffusionRegime = DiffusionRegime.STAGNANT
    total_readings: int = 0
    total_events: int = 0
    total_plans: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enums via ``.value``.

        ``dominant_medium`` may be ``None``; it is serialized as ``None``
        in that case rather than as a string, so the output stays
        JSON-friendly when an agent has no readings yet.
        """
        return {
            "agent_id": self.agent_id,
            "avg_concentration": self.avg_concentration,
            "dominant_medium": (
                _enum_value(DiffusionMedium, self.dominant_medium)
                if self.dominant_medium is not None
                else None
            ),
            "regime": _enum_value(DiffusionRegime, self.regime),
            "total_readings": self.total_readings,
            "total_events": self.total_events,
            "total_plans": self.total_plans,
            "last_updated": self.last_updated,
        }


@dataclass
class DiffusionStats:
    """Aggregate statistics over the current engine state.

    ``total_readings`` counts all recorded ``ConcentrationReading``
    records. ``total_events`` counts all recorded ``DiffusionEvent``
    records. ``total_snapshots`` counts all recorded ``DiffusionSnapshot``
    records. ``total_plans`` counts all recorded ``EqualizationPlan``
    records. ``total_gradients`` counts all recorded ``GradientRecord``
    records. ``regime_distribution`` tallies snapshots by their diagnosed
    regime, keyed by the regime's ``.value`` string. ``medium_distribution``
    tallies readings by their medium, keyed by the medium's ``.value``
    string. ``avg_concentration`` is the mean concentration across all
    readings (zero when there are none). Both distribution dicts are plain
    ``Dict[str, int]`` so they are already JSON-serializable.
    """
    total_readings: int = 0
    total_events: int = 0
    total_snapshots: int = 0
    total_plans: int = 0
    total_gradients: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    medium_distribution: Dict[str, int] = field(default_factory=dict)
    avg_concentration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The distribution dicts are already keyed by ``.value`` strings, so
        they are copied as-is. This keeps the output JSON-serializable
        without further conversion.
        """
        return {
            "total_readings": self.total_readings,
            "total_events": self.total_events,
            "total_snapshots": self.total_snapshots,
            "total_plans": self.total_plans,
            "total_gradients": self.total_gradients,
            "regime_distribution": dict(self.regime_distribution),
            "medium_distribution": dict(self.medium_distribution),
            "avg_concentration": self.avg_concentration,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveDiffusion:
    """Singleton engine modeling how conceptual activation diffuses through the cognitive network.

    Holds concentration readings, diffusion events, snapshots,
    equalization plans, gradient records, and per-agent profiles. All
    state mutations are guarded by a single reentrant lock so the engine
    is safe to call from multiple threads, including from within its own
    methods (for example, ``update_profile`` calls ``get_profile``). The
    engine is intentionally dependency-free so it can run in any Buddy
    runtime without extra packages.

    The engine is a measurement instrument first and a steering system
    second. It records how activation actually spread on each event,
    aggregates those observations into a regime and gradient direction,
    and — when the field is not equalizing the way the agent wants —
    files an equalization plan to steer it. It does not itself force
    activation to move; it makes the spread of activation legible so
    that the agent (or its orchestrator) can decide whether to
    accelerate, dampen, channel, insulate, seed, or drain.
    """

    # Caps to keep the in-memory engine bounded under runaway callers.
    MAX_READINGS: int = 5000
    MAX_EVENTS: int = 5000
    MAX_SNAPSHOTS: int = 5000
    MAX_PLANS: int = 5000
    MAX_GRADIENTS: int = 5000
    # How many recent readings and events a snapshot considers when
    # computing its aggregate fields. Kept small so a snapshot reflects
    # the current state of the field rather than the agent's full history.
    MAX_RECENT_FOR_SNAPSHOT: int = 10
    # Default list size cap applied when a list method is called without
    # an explicit limit.
    DEFAULT_LIST_LIMIT: int = 50

    def __init__(self) -> None:
        self._readings: Dict[str, ConcentrationReading] = {}
        self._events: Dict[str, DiffusionEvent] = {}
        self._snapshots: Dict[str, DiffusionSnapshot] = {}
        self._plans: Dict[str, EqualizationPlan] = {}
        self._gradients: Dict[str, GradientRecord] = {}
        self._profiles: Dict[str, DiffusionProfile] = {}
        # Running integer counters, kept in sync with the registries above.
        self._stats: Dict[str, int] = {
            "total_readings": 0,
            "total_events": 0,
            "total_snapshots": 0,
            "total_plans": 0,
            "total_gradients": 0,
        }
        # Reentrant lock so public methods may call one another safely.
        self._lock: threading.RLock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _init_stats() -> Dict[str, int]:
        """Return a fresh running-counter dict for engine statistics."""
        return {
            "total_readings": 0,
            "total_events": 0,
            "total_snapshots": 0,
            "total_plans": 0,
            "total_gradients": 0,
        }

    def _medium_readings(
        self, agent_id: str, medium: DiffusionMedium
    ) -> List[ConcentrationReading]:
        """Return this agent's readings in a medium, in insertion order (no lock)."""
        return [
            r
            for r in self._readings.values()
            if r.agent_id == agent_id and r.medium == medium
        ]

    def _medium_events(
        self, agent_id: str, medium: DiffusionMedium
    ) -> List[DiffusionEvent]:
        """Return this agent's events in a medium, in insertion order (no lock)."""
        return [
            e
            for e in self._events.values()
            if e.agent_id == agent_id and e.medium == medium
        ]

    # ── Concentration Readings ────────────────────────────────────

    def read_concentration(
        self,
        agent_id: str,
        medium: Any,
        node_id: str,
        concentration: float,
    ) -> ConcentrationReading:
        """Record a concentration reading for an agent and return it.

        ``medium`` accepts a ``DiffusionMedium`` member or its value/name
        string. ``node_id`` is a human-readable label for the node whose
        concentration was sampled. ``concentration`` in [0, 1] is clamped
        to that range. Raises ``RuntimeError`` if the reading registry is
        full, so runaway callers surface rather than silently dropping
        observations.
        """
        with self._lock:
            if len(self._readings) >= self.MAX_READINGS:
                raise RuntimeError("concentration reading registry is full")
            reading = ConcentrationReading(
                agent_id=agent_id,
                medium=_resolve_enum(DiffusionMedium, medium),
                node_id=str(node_id),
                concentration=_clamp(concentration, 0.0, 1.0),
                timestamp=_now(),
            )
            self._readings[reading.reading_id] = reading
            self._stats["total_readings"] += 1
            return reading

    def list_readings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ConcentrationReading]:
        """Return readings, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to readings recorded for that agent.
        ``limit`` caps the number of results, applied after filtering.
        The returned list is ordered most-recent-last (insertion order)
        and is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            readings = list(self._readings.values())
        if agent_id is not None:
            readings = [r for r in readings if r.agent_id == agent_id]
        n = _safe_int(limit, self.DEFAULT_LIST_LIMIT)
        return readings[-n:] if n else []

    def get_reading(self, reading_id: str) -> Optional[ConcentrationReading]:
        """Retrieve a reading by id, or ``None`` if no reading exists with that id."""
        with self._lock:
            return self._readings.get(reading_id)

    # ── Diffusion Events ──────────────────────────────────────────

    def record_event(
        self,
        agent_id: str,
        medium: Any,
        source_node: str,
        target_nodes: List[str],
        rate: float,
        barrier: DiffusionBarrier = DiffusionBarrier.NONE,
    ) -> DiffusionEvent:
        """Record a diffusion event for an agent and return it.

        ``medium`` accepts a ``DiffusionMedium`` member or its value/name
        string. ``source_node`` is the node the activation flowed out of.
        ``target_nodes`` is the list of nodes it flowed into; the list is
        copied so external mutation does not affect the stored event.
        ``rate`` in [0, 1] is how much of the source's concentration
        transferred, clamped to that range. ``barrier`` accepts a
        ``DiffusionBarrier`` member or its value/name string and defaults
        to NONE. Raises ``RuntimeError`` if the event registry is full.
        """
        with self._lock:
            if len(self._events) >= self.MAX_EVENTS:
                raise RuntimeError("diffusion event registry is full")
            event = DiffusionEvent(
                agent_id=agent_id,
                medium=_resolve_enum(DiffusionMedium, medium),
                source_node=str(source_node),
                target_nodes=[str(n) for n in (target_nodes or [])],
                rate=_clamp(rate, 0.0, 1.0),
                barrier=_resolve_enum(DiffusionBarrier, barrier),
                timestamp=_now(),
            )
            self._events[event.event_id] = event
            self._stats["total_events"] += 1
            return event

    def list_events(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DiffusionEvent]:
        """Return events, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to events recorded for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            events = list(self._events.values())
        if agent_id is not None:
            events = [e for e in events if e.agent_id == agent_id]
        n = _safe_int(limit, self.DEFAULT_LIST_LIMIT)
        return events[-n:] if n else []

    def get_event(self, event_id: str) -> Optional[DiffusionEvent]:
        """Retrieve an event by id, or ``None`` if no event exists with that id."""
        with self._lock:
            return self._events.get(event_id)

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(
        self,
        agent_id: str,
        medium: Any,
    ) -> DiffusionSnapshot:
        """Aggregate an agent's recent readings and events in a medium into a snapshot.

        ``medium`` accepts a ``DiffusionMedium`` member or its value/name
        string. The snapshot considers the agent's most recent
        ``MAX_RECENT_FOR_SNAPSHOT`` readings and events in that medium.
        ``avg_concentration`` is the mean concentration across those
        recent readings (zero when there are none). ``spread_count`` is
        the total number of target nodes the recent events reached (zero
        when there are no events). ``regime`` is derived from the mean
        event rate and spread count via ``_determine_regime``.
        ``gradient_direction`` is derived from the recent concentration
        series via ``_determine_gradient_direction``. The snapshot is
        stored and reflected in the engine stats.
        """
        with self._lock:
            medium_enum = _resolve_enum(DiffusionMedium, medium)
            recent_readings = self._medium_readings(
                agent_id, medium_enum
            )[-self.MAX_RECENT_FOR_SNAPSHOT:]
            recent_events = self._medium_events(
                agent_id, medium_enum
            )[-self.MAX_RECENT_FOR_SNAPSHOT:]
            if recent_readings:
                avg_concentration = sum(
                    r.concentration for r in recent_readings
                ) / len(recent_readings)
            else:
                avg_concentration = 0.0
            if recent_events:
                avg_rate = sum(e.rate for e in recent_events) / len(recent_events)
            else:
                avg_rate = 0.0
            spread_count = sum(len(e.target_nodes) for e in recent_events)
            regime = _determine_regime(avg_rate, spread_count)
            gradient_direction = _determine_gradient_direction(
                [r.concentration for r in recent_readings]
            )
            snapshot = DiffusionSnapshot(
                agent_id=agent_id,
                medium=medium_enum,
                regime=regime,
                gradient_direction=gradient_direction,
                avg_concentration=avg_concentration,
                spread_count=spread_count,
                timestamp=_now(),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._stats["total_snapshots"] += 1
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DiffusionSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to snapshots taken for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            snapshots = list(self._snapshots.values())
        if agent_id is not None:
            snapshots = [s for s in snapshots if s.agent_id == agent_id]
        n = _safe_int(limit, self.DEFAULT_LIST_LIMIT)
        return snapshots[-n:] if n else []

    def get_snapshot(self, snapshot_id: str) -> Optional[DiffusionSnapshot]:
        """Retrieve a snapshot by id, or ``None`` if no snapshot exists with that id."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    # ── Equalization Plans ────────────────────────────────────────

    def plan_equalization(
        self,
        agent_id: str,
        medium: Any,
        strategy: Any,
        target_nodes: List[str],
        expected_rate: float,
        rationale: str,
    ) -> EqualizationPlan:
        """Create an equalization plan for a medium and return it.

        ``medium`` accepts a ``DiffusionMedium`` member or its value/name
        string. ``strategy`` accepts an ``EqualizationStrategy`` member
        or its value/name string. ``target_nodes`` is the list of nodes
        the strategy should act on; the list is copied so external
        mutation does not affect the stored plan. ``expected_rate`` in
        [0, 1] is the rate the plan expects to achieve, clamped to that
        range. ``rationale`` is a free-form explanation of why this
        strategy was chosen for these targets. Raises ``RuntimeError`` if
        the plan registry is full.
        """
        with self._lock:
            if len(self._plans) >= self.MAX_PLANS:
                raise RuntimeError("equalization plan registry is full")
            plan = EqualizationPlan(
                agent_id=agent_id,
                medium=_resolve_enum(DiffusionMedium, medium),
                strategy=_resolve_enum(EqualizationStrategy, strategy),
                target_nodes=[str(n) for n in (target_nodes or [])],
                expected_rate=_clamp(expected_rate, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans[plan.plan_id] = plan
            self._stats["total_plans"] += 1
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EqualizationPlan]:
        """Return equalization plans, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to plans created for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            plans = list(self._plans.values())
        if agent_id is not None:
            plans = [p for p in plans if p.agent_id == agent_id]
        n = _safe_int(limit, self.DEFAULT_LIST_LIMIT)
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> Optional[EqualizationPlan]:
        """Retrieve a plan by id, or ``None`` if no plan exists with that id."""
        with self._lock:
            return self._plans.get(plan_id)

    # ── Gradient Records ──────────────────────────────────────────

    def record_gradient(
        self,
        agent_id: str,
        medium: Any,
        direction: Any,
        from_concentration: float,
        to_concentration: float,
    ) -> GradientRecord:
        """Record a concentration change at a node and return it.

        ``medium`` accepts a ``DiffusionMedium`` member or its value/name
        string. ``direction`` accepts a ``GradientDirection`` member or
        its value/name string. ``from_concentration`` and
        ``to_concentration`` in [0, 1] are the concentration before and
        after the change, clamped to that range. ``delta`` is computed as
        ``to_concentration - from_concentration`` at record time, so the
        stored delta is always consistent with the stored endpoints.
        Raises ``RuntimeError`` if the gradient registry is full.
        """
        with self._lock:
            if len(self._gradients) >= self.MAX_GRADIENTS:
                raise RuntimeError("gradient record registry is full")
            from_c = _clamp(from_concentration, 0.0, 1.0)
            to_c = _clamp(to_concentration, 0.0, 1.0)
            gradient = GradientRecord(
                agent_id=agent_id,
                medium=_resolve_enum(DiffusionMedium, medium),
                direction=_resolve_enum(GradientDirection, direction),
                from_concentration=from_c,
                to_concentration=to_c,
                delta=to_c - from_c,
                timestamp=_now(),
            )
            self._gradients[gradient.record_id] = gradient
            self._stats["total_gradients"] += 1
            return gradient

    def list_gradients(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[GradientRecord]:
        """Return gradient records, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to records created for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            gradients = list(self._gradients.values())
        if agent_id is not None:
            gradients = [g for g in gradients if g.agent_id == agent_id]
        n = _safe_int(limit, self.DEFAULT_LIST_LIMIT)
        return gradients[-n:] if n else []

    def get_gradient(self, record_id: str) -> Optional[GradientRecord]:
        """Retrieve a gradient record by id, or ``None`` if none exists with that id."""
        with self._lock:
            return self._gradients.get(record_id)

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> DiffusionProfile:
        """Return the agent's diffusion profile, creating it if absent.

        When a profile does not yet exist for the agent, a fresh one is
        computed from the agent's currently recorded readings, events, and
        plans: ``avg_concentration`` is the mean concentration across all
        of the agent's readings, ``dominant_medium`` is the modal medium
        (or ``None`` if the agent has no readings), ``regime`` is derived
        from the agent's mean event rate and spread count, and
        ``total_readings``, ``total_events``, and ``total_plans`` tally
        the agent's records of each kind. The profile is then stored so
        subsequent calls return the same object; callers may refresh it
        via ``update_profile``.
        """
        with self._lock:
            existing = self._profiles.get(agent_id)
            if existing is not None:
                return existing
            agent_readings = [
                r for r in self._readings.values() if r.agent_id == agent_id
            ]
            agent_events = [
                e for e in self._events.values() if e.agent_id == agent_id
            ]
            agent_plans = [
                p for p in self._plans.values() if p.agent_id == agent_id
            ]
            if agent_readings:
                avg_concentration = sum(
                    r.concentration for r in agent_readings
                ) / len(agent_readings)
                medium_counts: Dict[DiffusionMedium, int] = {}
                for r in agent_readings:
                    medium_counts[r.medium] = medium_counts.get(r.medium, 0) + 1
                dominant_medium = max(
                    medium_counts.items(), key=lambda kv: kv[1]
                )[0]
            else:
                avg_concentration = 0.0
                dominant_medium = None
            if agent_events:
                avg_rate = sum(e.rate for e in agent_events) / len(agent_events)
                spread_count = sum(len(e.target_nodes) for e in agent_events)
            else:
                avg_rate = 0.0
                spread_count = 0
            regime = _determine_regime(avg_rate, spread_count)
            profile = DiffusionProfile(
                agent_id=agent_id,
                avg_concentration=avg_concentration,
                dominant_medium=dominant_medium,
                regime=regime,
                total_readings=len(agent_readings),
                total_events=len(agent_events),
                total_plans=len(agent_plans),
                last_updated=_now(),
            )
            self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> DiffusionProfile:
        """Update fields on an agent's diffusion profile and return it.

        The profile is fetched (or created) first, then each keyword in
        ``kwargs`` is applied to the matching attribute. ``dominant_medium``
        and ``regime`` may be supplied as enum members or their value/name
        strings; they are normalized to enum members. ``avg_concentration``
        is coerced to float, and the count fields (``total_readings``,
        ``total_events``, ``total_plans``) are coerced to int. Unknown
        keys are ignored so callers can pass through generic update
        payloads safely. ``last_updated`` is always refreshed.
        """
        with self._lock:
            profile = self.get_profile(agent_id)
            for key, value in kwargs.items():
                if key == "dominant_medium":
                    if value is None:
                        profile.dominant_medium = None
                    else:
                        profile.dominant_medium = _resolve_enum(
                            DiffusionMedium, value
                        )
                elif key == "regime":
                    profile.regime = _resolve_enum(DiffusionRegime, value)
                elif key == "avg_concentration":
                    try:
                        profile.avg_concentration = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key in ("total_readings", "total_events", "total_plans"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
                elif hasattr(profile, key):
                    setattr(profile, key, value)
            profile.last_updated = _now()
            return profile

    def list_profiles(self) -> List[DiffusionProfile]:
        """Return all stored diffusion profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> DiffusionStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counter dict maintained by the
        record methods. ``regime_distribution`` is tallied from stored
        snapshots and keyed by the regime ``.value`` string.
        ``medium_distribution`` is tallied from stored readings and keyed
        by the medium ``.value`` string. ``avg_concentration`` is the mean
        concentration across all stored readings (zero when there are
        none). Both distribution dicts are plain ``Dict[str, int]`` so
        the result is JSON-serializable directly.
        """
        with self._lock:
            s = self._stats
            regime_dist: Dict[str, int] = {}
            for snap in self._snapshots.values():
                key = _enum_value(DiffusionRegime, snap.regime)
                regime_dist[key] = regime_dist.get(key, 0) + 1
            medium_dist: Dict[str, int] = {}
            concentration_sum = 0.0
            readings_count = 0
            for r in self._readings.values():
                key = _enum_value(DiffusionMedium, r.medium)
                medium_dist[key] = medium_dist.get(key, 0) + 1
                concentration_sum += r.concentration
                readings_count += 1
            avg_concentration = (
                concentration_sum / readings_count if readings_count else 0.0
            )
            return DiffusionStats(
                total_readings=int(s["total_readings"]),
                total_events=int(s["total_events"]),
                total_snapshots=int(s["total_snapshots"]),
                total_plans=int(s["total_plans"]),
                total_gradients=int(s["total_gradients"]),
                regime_distribution=regime_dist,
                medium_distribution=medium_dist,
                avg_concentration=avg_concentration,
            )

    # ── Maintenance ───────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Drops every reading, event, snapshot, plan, gradient record, and
        profile, and re-initializes the running counters. The lock itself
        is not replaced.
        """
        with self._lock:
            self._readings.clear()
            self._events.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._gradients.clear()
            self._profiles.clear()
            self._stats = self._init_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional["AgentCognitiveDiffusion"] = None
_engine_lock = threading.Lock()


def get_diffusion_engine() -> AgentCognitiveDiffusion:
    """Get or create the singleton ``AgentCognitiveDiffusion`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads. Uses double-checked locking
    so the common path does not take the lock once the engine exists.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveDiffusion()
    return _engine


def reset_diffusion_engine() -> None:
    """Reset the singleton ``AgentCognitiveDiffusion`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_diffusion_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
