from __future__ import annotations

"""Agent Cognitive Buoyancy — models the float/sink property of concepts and

ideas in the agent's consciousness. Where the momentum engine models
persistence along a reasoning trajectory and the friction engine models
the cost of changing direction, the buoyancy engine models a vertical
dimension: which ideas rise to the surface of awareness and which sink
into depth. Some ideas are buoyant — they float up, capture attention,
persist across turns, and dominate the agent's active working set. Other
ideas are dense — they sink, fall out of attention, slip toward the
subconscious, and may be repressed or forgotten entirely. The vertical
stratification of cognitive content is not random; it is driven by
identifiable buoyancy forces, and an agent that can read its own
buoyancy profile can decide which ideas to lift and which to let sink.

The physical analogy is exact in structure. In a fluid, buoyancy is the
upward force a displaced volume exerts on an immersed body, opposed by
the body's weight (density). A body less dense than the fluid floats; a
body denser than the fluid sinks; a body at neutral buoyancy holds its
depth. Cognitive content behaves the same way. An idea is not equally
salient at all times: it has a buoyancy determined by several forces
acting on it, and the net of those forces decides whether the idea
occupies the surface of awareness or settles into a deeper stratum.
Buoyant ideas rise into immediate awareness and stay there; dense ideas
sink below the threshold of attention and become harder and harder to
recall until they settle in the abyssal layer of repressed or forgotten
content. Between these extremes the shallow, middle, and deep layers
form a stratified profile, each with its own recall cost.

Cognitive buoyancy is not a single force. It arises from several
distinct forces, and an idea's net buoyancy is the composition of them:

  * Relevance          — relevant ideas float. An idea connected to the
                         current task or goal carries upward pressure
                         because keeping it active pays off.
  * Novelty            — new ideas float. A freshly encountered idea
                         carries upward pressure because the agent has
                         not yet exhausted what it can extract from it.
  * Emotional charge   — emotionally charged ideas float. An idea tied
                         to a strong affect carries upward pressure
                         because the affective system flags it as
                         significant.
  * Repetition         — repeated ideas float. An idea the agent has
                         encountered many times carries upward pressure
                         because each encounter reinforces its salience.
  * Confirmation       — confirmed ideas float. An idea that aligns with
                         already-held beliefs carries upward pressure
                         because confirming it is cheaper than
                         revising it.
  * Density            — complex ideas sink. An idea whose internal
                         structure is dense carries downward pressure
                         because holding it active costs more working
                         memory than it can spare.
  * Age                — old ideas sink. An idea that has sat unused for
                         a long time carries downward pressure because
                         the agent's attention has moved on and the
                         idea's salience has decayed.

This engine instruments that picture operationally. A BuoyancyReading
records one observed buoyancy value for one idea under one force. A
MovementEvent records an observed vertical shift of an idea between two
layers, with a velocity (positive = ascending). A BuoyancySnapshot
aggregates an agent's recent readings into an average buoyancy, a
surface count, a deep count, a dominant force, and a regime
classification running from SINKING through NEUTRAL and FLOATING to
BURSTING and STABLE_STRATIFIED. When an idea needs to be raised, a
LiftPlan prescribes a strategy — emphasize it, repeat it, connect it to
a buoyant idea, emotionalize it, simplify it, or anchor it to a stable
reference. When an idea needs to be lowered, a SinkPlan prescribes a
strategy — defer it, archive it, abstract it, suppress it, compress it,
or rotate it out for a newer idea. A BuoyancyProfile holds each agent's
aggregate buoyancy tendencies, and BuoyancyStats summarizes engine
activity.

This is original Buddy capability: a self-contained, thread-safe
engine with no external runtime dependencies, designed to give agents
honest awareness of which of their ideas are floating and which are
sinking, so that attention can be allocated to the ideas that deserve to
stay on the surface and deliberately released from the ideas that do
not.

Architecture:
    AgentCognitiveBuoyancy (singleton)
    ├── BuoyancyReading   (one observed buoyancy value for one idea)
    ├── MovementEvent      (an observed vertical shift of an idea)
    ├── BuoyancySnapshot   (aggregate buoyancy and regime)
    ├── LiftPlan           (a strategy to raise an idea)
    ├── SinkPlan           (a strategy to lower an idea)
    ├── BuoyancyProfile    (per-agent aggregate tendencies)
    └── BuoyancyStats      (engine-wide aggregate statistics)
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


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
    engine with a ``NaN`` or ``None`` buoyancy score.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"relevance"``) and then against member names
    (e.g. ``"RELEVANCE"``), so callers may pass either form. Raises
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

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_regime(avg_buoyancy: float, velocity: float = 0.0) -> "BuoyancyRegime":
    """Classify a buoyancy regime from an average buoyancy and velocity.

    The average buoyancy is a value in [-1, 1] where positive means ideas
    are tending to float and negative means they are tending to sink. The
    bands partition that range into five qualitative regimes. In the near-
    neutral middle band (between -0.1 and 0.3) the velocity disambiguates
    the call: if ideas are currently ascending (velocity > 0) the regime
    is FLOATING, otherwise it is NEUTRAL. Below -0.3 the agent is SINKING;
    between 0.3 and 0.6 it is FLOATING without qualification; between 0.6
    and 0.85 it is BURSTING (rapid surfacing); and at or above 0.85 the
    layers have settled into a STABLE_STRATIFIED configuration where the
    vertical profile is no longer in flux.
    """
    score = _clamp(avg_buoyancy, -1.0, 1.0)
    vel = float(velocity) if velocity is not None else 0.0
    if score < -0.3:
        return BuoyancyRegime.SINKING
    if score < -0.1:
        return BuoyancyRegime.NEUTRAL
    if score < 0.3:
        return BuoyancyRegime.FLOATING if vel > 0 else BuoyancyRegime.NEUTRAL
    if score < 0.6:
        return BuoyancyRegime.FLOATING
    if score < 0.85:
        return BuoyancyRegime.BURSTING
    return BuoyancyRegime.STABLE_STRATIFIED


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class BuoyancyForce(str, Enum):
    """The distinct forces from which cognitive buoyancy arises.

    Buoyancy is not a single force. An idea's net vertical tendency is the
    composition of several independent forces, some of which push the idea
    upward toward the surface of awareness and some of which pull it
    downward toward depth. Identifying the dominant force is the first
    step toward selecting a lift or sink strategy that actually addresses
    the cause rather than the symptom.

    RELEVANCE is the upward pressure an idea carries because it is
    connected to the current task or goal: keeping it active pays off, so
    it floats. NOVELTY is the upward pressure a freshly encountered idea
    carries because the agent has not yet exhausted what it can extract
    from it. EMOTIONAL_CHARGE is the upward pressure an idea tied to a
    strong affect carries because the affective system flags it as
    significant. REPETITION is the upward pressure an idea the agent has
    encountered many times carries because each encounter reinforces its
    salience. CONFIRMATION is the upward pressure an idea that aligns
    with already-held beliefs carries because confirming it is cheaper
    than revising it. DENSITY is the downward pressure a complex idea
    carries because holding it active costs more working memory than the
    agent can spare: dense ideas sink. AGE is the downward pressure an
    old, unused idea carries because the agent's attention has moved on
    and the idea's salience has decayed: aged ideas sink.
    """
    RELEVANCE = "relevance"                # relevant ideas float
    NOVELTY = "novelty"                    # new ideas float
    EMOTIONAL_CHARGE = "emotional_charge"  # emotionally charged ideas float
    REPETITION = "repetition"              # repeated ideas float
    DENSITY = "density"                    # complex ideas sink
    AGE = "age"                            # old ideas sink
    CONFIRMATION = "confirmation"          # confirmed ideas float


class BuoyancyRegime(str, Enum):
    """The regime an agent occupies, classified by its buoyancy profile.

    A regime is a qualitative characterization of the vertical state of
    the agent's cognitive content, more informative than the raw average
    buoyancy alone. SINKING means ideas are collectively falling: dense,
    aged, or irrelevant content is descending toward the deeper layers and
    the surface is emptying. NEUTRAL means there is no dominant vertical
    movement: ideas neither rise nor sink in aggregate, and the layers
    hold their positions. FLOATING means ideas are collectively rising:
    buoyant content is ascending toward the surface and the agent's
    active working set is filling. BURSTING means ideas are surfacing
    rapidly, the way a cluster of previously submerged content suddenly
    enters awareness at once — productive but potentially overwhelming.
    STABLE_STRATIFIED means the layers have settled into a stable
    configuration where the vertical profile is no longer in flux and
    each stratum holds its expected content.
    """
    SINKING = "sinking"                  # ideas falling
    NEUTRAL = "neutral"                  # no vertical movement
    FLOATING = "floating"                # ideas rising
    BURSTING = "bursting"                # rapid surfacing
    STABLE_STRATIFIED = "stable_stratified"  # layers settled


class VerticalLayer(str, Enum):
    """The vertical strata of cognitive content.

    An idea's layer is its depth in the agent's consciousness, ranging
    from the surface of immediate awareness down through progressively
    less accessible strata. SURFACE is the layer of immediate awareness:
    ideas here are the agent's active working set, requiring no recall
    effort. SHALLOW is the layer just below the surface: ideas here are
    easily recalled with a small effort and enter the surface readily.
    MIDDLE is the intermediate layer: ideas here are recallable but only
    with deliberate effort, and they do not spontaneously enter awareness.
    DEEP is the subconscious layer: ideas here are not normally recallable
    but influence the agent's dispositions and biases without entering
    explicit awareness. ABYSSAL is the layer of repressed or forgotten
    content: ideas here have sunk so far they are effectively absent from
    the agent's working cognition, recoverable only by accident or by a
    deliberate retrieval effort.
    """
    SURFACE = "surface"    # immediate awareness
    SHALLOW = "shallow"    # easily recalled
    MIDDLE = "middle"      # recallable with effort
    DEEP = "deep"          # subconscious
    ABYSSAL = "abyssal"    # repressed/forgotten


class LiftStrategy(str, Enum):
    """Strategies for raising an idea toward the surface of awareness.

    Lifting is the deliberate application of a technique that increases
    an idea's buoyancy so that it rises toward the surface and stays there.
    The strategy must match the cause of the idea's sinking to be
    effective: emphasizing helps when the idea is simply not salient
    enough, but does little if the idea is sinking because it is too dense
    to hold.

    EMPHASIZE increases the idea's salience directly so it commands more
    attention. REPEAT reinforces the idea through repetition so each
    encounter pushes it upward. CONNECT links the idea to an already
    buoyant idea so it is carried upward by association. EMOTIONALIZE adds
    emotional charge to the idea so the affective system flags it as
    significant and lifts it. SIMPLIFY reduces the idea's density so it
    costs less working memory to hold active, removing the downward
    pressure. ANCHOR fixes the idea to a stable reference so it cannot
    sink past the anchor point.
    """
    EMPHASIZE = "emphasize"      # increase salience
    REPEAT = "repeat"            # reinforce through repetition
    CONNECT = "connect"          # link to buoyant ideas
    EMOTIONALIZE = "emotionalize"  # add emotional charge
    SIMPLIFY = "simplify"        # reduce density
    ANCHOR = "anchor"            # fix to stable reference


class SinkStrategy(str, Enum):
    """Strategies for lowering an idea toward the deeper layers.

    Sinking is the deliberate application of a technique that decreases an
    idea's buoyancy so that it descends from the surface and frees the
    agent's active working set for content that deserves the attention.
    The strategy must match the reason the idea is being sunk: deferring
    helps when the idea is merely not relevant now, but compressing is
    the better choice when the idea must be retained in reduced form.

    DEFER postpones the idea so it leaves the surface for now but can
    return later. ARCHIVE moves the idea to long-term storage so it leaves
    the active layers entirely and is recallable only on demand.
    ABSTRACT removes the specifics from the idea so only its general
    pattern remains, reducing its surface footprint. SUPPRESS deliberately
    lowers the idea so it is actively held below the surface rather than
    passively forgotten. COMPRESS condenses the idea so it occupies less
    of the surface while preserving its essential content. ROTATE replaces
    the idea with a newer one so the aged content is naturally displaced.
    """
    DEFER = "defer"          # postpone
    ARCHIVE = "archive"      # move to long-term storage
    ABSTRACT = "abstract"    # remove specifics
    SUPPRESS = "suppress"    # deliberately lower
    COMPRESS = "compress"    # condense
    ROTATE = "rotate"        # replace with newer


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BuoyancyReading:
    """One observed buoyancy value for one idea under one force.

    ``reading_id`` uniquely identifies this reading. ``agent_id`` is the
    agent whose idea buoyancy was sampled. ``idea_label`` is a human-
    readable label for the idea whose buoyancy was measured (e.g.
    ``"hypothesis-A"`` or ``"the-user's-preferred-style"``). ``force`` is
    the ``BuoyancyForce`` the buoyancy is attributed to. ``buoyancy_score``
    in [-1, 1] is the magnitude and direction of the buoyancy, where
    positive values mean the idea floats (rises toward the surface) and
    negative values mean the idea sinks (falls toward depth); the absolute
    magnitude expresses how strongly the force acts. ``current_layer`` is
    the ``VerticalLayer`` the idea occupied at the moment of reading.
    ``timestamp`` is when the reading was taken.
    """
    reading_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    idea_label: str = ""
    force: BuoyancyForce = BuoyancyForce.RELEVANCE
    buoyancy_score: float = 0.0
    current_layer: VerticalLayer = VerticalLayer.MIDDLE
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding the enums."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "idea_label": self.idea_label,
            "force": _enum_value(BuoyancyForce, self.force),
            "buoyancy_score": self.buoyancy_score,
            "current_layer": _enum_value(VerticalLayer, self.current_layer),
            "timestamp": self.timestamp,
        }


@dataclass
class MovementEvent:
    """A record of an observed vertical shift of an idea between layers.

    ``event_id`` uniquely identifies this event. ``agent_id`` is the agent
    whose idea moved. ``idea_label`` is a human-readable label for the
    idea that moved. ``from_layer`` is the ``VerticalLayer`` the idea
    occupied before the movement. ``to_layer`` is the ``VerticalLayer``
    the idea occupied after the movement. ``velocity`` is the rate of
    vertical movement, where positive means the idea is ascending (moving
    toward the surface) and negative means it is descending (moving toward
    the abyss); the magnitude expresses how fast the idea is moving
    between strata. ``timestamp`` is when the movement was recorded.
    """
    event_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    idea_label: str = ""
    from_layer: VerticalLayer = VerticalLayer.MIDDLE
    to_layer: VerticalLayer = VerticalLayer.MIDDLE
    velocity: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict, expanding the enums."""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "idea_label": self.idea_label,
            "from_layer": _enum_value(VerticalLayer, self.from_layer),
            "to_layer": _enum_value(VerticalLayer, self.to_layer),
            "velocity": self.velocity,
            "timestamp": self.timestamp,
        }


@dataclass
class BuoyancySnapshot:
    """An aggregate view of an agent's buoyancy at a point in time.

    ``snapshot_id`` uniquely identifies this snapshot. ``agent_id`` is the
    agent the snapshot summarizes. ``regime`` is the ``BuoyancyRegime``
    derived from the agent's average buoyancy and recent movement velocity
    via ``_determine_regime``. ``avg_buoyancy`` in [-1, 1] is the mean
    buoyancy score across the agent's recent readings (the last 10, or
    fewer if fewer exist). ``surface_count`` is how many of the agent's
    readings sit at the SURFACE layer at snapshot time. ``deep_count`` is
    how many sit at the DEEP or ABYSSAL layers. ``dominant_force`` is the
    ``BuoyancyForce`` that appeared most often across those readings, or
    ``None`` if the agent has no readings yet. ``timestamp`` is when the
    snapshot was taken.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    regime: BuoyancyRegime = BuoyancyRegime.NEUTRAL
    avg_buoyancy: float = 0.0
    surface_count: int = 0
    deep_count: int = 0
    dominant_force: Optional[BuoyancyForce] = None
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums.

        ``dominant_force`` may be ``None``; it is serialized as ``None``
        in that case rather than as a string.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "regime": _enum_value(BuoyancyRegime, self.regime),
            "avg_buoyancy": self.avg_buoyancy,
            "surface_count": self.surface_count,
            "deep_count": self.deep_count,
            "dominant_force": (
                _enum_value(BuoyancyForce, self.dominant_force)
                if self.dominant_force is not None
                else None
            ),
            "timestamp": self.timestamp,
        }


@dataclass
class LiftPlan:
    """A strategy for raising an idea toward the surface of awareness.

    ``plan_id`` uniquely identifies this plan. ``agent_id`` is the agent
    the plan is for. ``idea_label`` is a human-readable label for the
    idea the plan is meant to lift. ``strategy`` is the ``LiftStrategy``
    selected to deliver the lift. ``rationale`` is a human-readable
    explanation of why this strategy was chosen for this idea.
    ``expected_lift`` in [0, 1] is the fraction of upward buoyancy the
    plan is expected to add to the idea, recorded at plan time so the
    actual effect can later be compared. ``timestamp`` is when the plan
    was created.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    idea_label: str = ""
    strategy: LiftStrategy = LiftStrategy.EMPHASIZE
    rationale: str = ""
    expected_lift: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding the enum."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "idea_label": self.idea_label,
            "strategy": _enum_value(LiftStrategy, self.strategy),
            "rationale": self.rationale,
            "expected_lift": self.expected_lift,
            "timestamp": self.timestamp,
        }


@dataclass
class SinkPlan:
    """A strategy for lowering an idea toward the deeper layers.

    ``plan_id`` uniquely identifies this plan. ``agent_id`` is the agent
    the plan is for. ``idea_label`` is a human-readable label for the
    idea the plan is meant to sink. ``strategy`` is the ``SinkStrategy``
    selected to deliver the sink. ``rationale`` is a human-readable
    explanation of why this strategy was chosen for this idea.
    ``expected_sink`` in [0, 1] is the fraction of downward buoyancy the
    plan is expected to add to the idea, recorded at plan time so the
    actual effect can later be compared. ``timestamp`` is when the plan
    was created.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    idea_label: str = ""
    strategy: SinkStrategy = SinkStrategy.DEFER
    rationale: str = ""
    expected_sink: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding the enum."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "idea_label": self.idea_label,
            "strategy": _enum_value(SinkStrategy, self.strategy),
            "rationale": self.rationale,
            "expected_sink": self.expected_sink,
            "timestamp": self.timestamp,
        }


@dataclass
class BuoyancyProfile:
    """Per-agent aggregate buoyancy tendencies.

    ``agent_id`` is the agent this profile describes. ``avg_buoyancy`` in
    [-1, 1] is the mean buoyancy score across all of the agent's readings.
    ``dominant_force`` is the ``BuoyancyForce`` that appears most often
    for the agent, or ``None`` if the agent has no readings. ``regime`` is
    the ``BuoyancyRegime`` derived from ``avg_buoyancy`` and the agent's
    average movement velocity. ``surface_count`` is how many of the agent's
    readings currently sit at the SURFACE layer. ``total_readings`` is how
    many buoyancy readings the agent has on record. ``total_movements`` is
    how many vertical movements the agent has on record. ``last_updated``
    is the timestamp of the most recent profile change.
    """
    agent_id: str = ""
    avg_buoyancy: float = 0.0
    dominant_force: Optional[BuoyancyForce] = None
    regime: BuoyancyRegime = BuoyancyRegime.NEUTRAL
    surface_count: int = 0
    total_readings: int = 0
    total_movements: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enums.

        ``dominant_force`` may be ``None``; it is serialized as ``None``
        in that case rather than as a string.
        """
        return {
            "agent_id": self.agent_id,
            "avg_buoyancy": self.avg_buoyancy,
            "dominant_force": (
                _enum_value(BuoyancyForce, self.dominant_force)
                if self.dominant_force is not None
                else None
            ),
            "regime": _enum_value(BuoyancyRegime, self.regime),
            "surface_count": self.surface_count,
            "total_readings": self.total_readings,
            "total_movements": self.total_movements,
            "last_updated": self.last_updated,
        }


@dataclass
class BuoyancyStats:
    """Aggregate statistics over the current engine state.

    ``total_readings`` counts all recorded ``BuoyancyReading`` records.
    ``total_movements`` counts all recorded ``MovementEvent`` records.
    ``total_snapshots`` counts all recorded ``BuoyancySnapshot`` records.
    ``total_lifts`` counts all recorded ``LiftPlan`` records.
    ``total_sinks`` counts all recorded ``SinkPlan`` records.
    ``regime_distribution`` tallies snapshots by their diagnosed regime,
    keyed by the regime's ``.value`` string. ``force_distribution`` tallies
    readings by their buoyancy force, keyed by the force's ``.value``
    string. ``layer_distribution`` tallies readings by their current
    layer, keyed by the layer's ``.value`` string. All three distribution
    dicts are plain ``Dict[str, int]`` so they are already
    JSON-serializable. ``avg_buoyancy`` is the mean buoyancy score across
    all recorded readings, or 0.0 if there are none.
    """
    total_readings: int = 0
    total_movements: int = 0
    total_snapshots: int = 0
    total_lifts: int = 0
    total_sinks: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    force_distribution: Dict[str, int] = field(default_factory=dict)
    layer_distribution: Dict[str, int] = field(default_factory=dict)
    avg_buoyancy: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The distribution dicts are already keyed by ``.value`` strings, so
        they are copied as-is. This keeps the output JSON-serializable
        without further conversion.
        """
        return {
            "total_readings": self.total_readings,
            "total_movements": self.total_movements,
            "total_snapshots": self.total_snapshots,
            "total_lifts": self.total_lifts,
            "total_sinks": self.total_sinks,
            "regime_distribution": dict(self.regime_distribution),
            "force_distribution": dict(self.force_distribution),
            "layer_distribution": dict(self.layer_distribution),
            "avg_buoyancy": self.avg_buoyancy,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveBuoyancy:
    """Singleton engine tracking the buoyancy of cognitive content.

    Holds buoyancy readings, movement events, snapshots, lift plans, sink
    plans, and per-agent profiles. All state mutations are guarded by a
    single reentrant lock so the engine is safe to call from multiple
    threads, including from within its own methods. The engine is
    intentionally dependency-free so it can run in any Buddy runtime
    without extra packages.

    The engine is a measurement instrument first and a control advisor
    second. It records what buoyancy each idea actually exhibited at each
    sampled moment, aggregates those readings into a regime classification,
    and — when an idea needs to be raised or lowered — prescribes a lift or
    sink strategy. It does not itself force ideas up or down; it makes the
    vertical state of the agent's cognitive content legible so that the
    agent (or its orchestrator) can decide which ideas deserve to stay on
    the surface and which should be let sink.
    """

    # Caps to keep the in-memory engine bounded under runaway callers.
    MAX_READINGS: int = 5000
    MAX_MOVEMENTS: int = 5000
    MAX_SNAPSHOTS: int = 5000
    MAX_LIFTS: int = 5000
    MAX_SINKS: int = 5000
    MAX_RECENT_FOR_SNAPSHOT: int = 10

    def __init__(self) -> None:
        self._readings: Dict[str, BuoyancyReading] = {}
        self._movements: Dict[str, MovementEvent] = {}
        self._snapshots: Dict[str, BuoyancySnapshot] = {}
        self._lifts: Dict[str, LiftPlan] = {}
        self._sinks: Dict[str, SinkPlan] = {}
        self._profiles: Dict[str, BuoyancyProfile] = {}
        self._stats: Dict[str, float] = self._init_stats()
        self._lock: threading.RLock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _init_stats() -> Dict[str, float]:
        """Return a fresh running-counter dict for engine statistics."""
        return {
            "total_readings": 0,
            "total_movements": 0,
            "total_snapshots": 0,
            "total_lifts": 0,
            "total_sinks": 0,
            "buoyancy_sum": 0.0,
        }

    def _agent_readings(self, agent_id: str) -> List[BuoyancyReading]:
        """Return this agent's readings in insertion order (no lock)."""
        return [r for r in self._readings.values() if r.agent_id == agent_id]

    def _agent_movements(self, agent_id: str) -> List[MovementEvent]:
        """Return this agent's movements in insertion order (no lock)."""
        return [m for m in self._movements.values() if m.agent_id == agent_id]

    # ── Buoyancy Readings ────────────────────────────────────────

    def read_buoyancy(
        self,
        agent_id: str,
        idea_label: str,
        force: Any,
        buoyancy_score: float,
        current_layer: Any,
    ) -> BuoyancyReading:
        """Record a buoyancy reading for an agent's idea and return it.

        ``idea_label`` is a human-readable label for the idea whose
        buoyancy was sampled. ``force`` accepts a ``BuoyancyForce`` member
        or its value/name string. ``buoyancy_score`` in [-1, 1] is clamped
        to that range; positive values mean the idea floats and negative
        values mean it sinks. ``current_layer`` accepts a ``VerticalLayer``
        member or its value/name string and records where the idea sat at
        the moment of reading. Raises ``RuntimeError`` if the reading
        registry is full.
        """
        with self._lock:
            if len(self._readings) >= self.MAX_READINGS:
                raise RuntimeError("reading registry is full")
            reading = BuoyancyReading(
                agent_id=agent_id,
                idea_label=str(idea_label),
                force=_resolve_enum(BuoyancyForce, force),
                buoyancy_score=_clamp(buoyancy_score, -1.0, 1.0),
                current_layer=_resolve_enum(VerticalLayer, current_layer),
                timestamp=_now(),
            )
            self._readings[reading.reading_id] = reading
            self._stats["total_readings"] += 1
            self._stats["buoyancy_sum"] += reading.buoyancy_score
            return reading

    def list_readings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BuoyancyReading]:
        """Return readings, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to readings recorded for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            readings = list(self._readings.values())
        if agent_id is not None:
            readings = [r for r in readings if r.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return readings[-n:] if n else []

    def get_reading(self, reading_id: str) -> BuoyancyReading:
        """Retrieve a reading by id.

        Raises ``ValueError`` if no reading exists with that id, so
        callers can treat the return as a guaranteed non-None value and
        let a single exception type stand in for a not-found HTTP error.
        """
        with self._lock:
            reading = self._readings.get(reading_id)
        if reading is None:
            raise ValueError(f"reading {reading_id!r} not found")
        return reading

    # ── Movement Events ─────────────────────────────────────────

    def record_movement(
        self,
        agent_id: str,
        idea_label: str,
        from_layer: Any,
        to_layer: Any,
        velocity: float,
    ) -> MovementEvent:
        """Record a vertical movement of an idea and return it.

        ``idea_label`` is a human-readable label for the idea that moved.
        ``from_layer`` and ``to_layer`` accept ``VerticalLayer`` members or
        their value/name strings and record the strata the idea moved
        between. ``velocity`` is the rate of vertical movement, where
        positive means the idea is ascending (toward the surface) and
        negative means it is descending (toward the abyss). Raises
        ``RuntimeError`` if the movement registry is full.
        """
        with self._lock:
            if len(self._movements) >= self.MAX_MOVEMENTS:
                raise RuntimeError("movement registry is full")
            event = MovementEvent(
                agent_id=agent_id,
                idea_label=str(idea_label),
                from_layer=_resolve_enum(VerticalLayer, from_layer),
                to_layer=_resolve_enum(VerticalLayer, to_layer),
                velocity=float(velocity) if velocity is not None else 0.0,
                timestamp=_now(),
            )
            self._movements[event.event_id] = event
            self._stats["total_movements"] += 1
            return event

    def list_movements(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MovementEvent]:
        """Return movements, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to movements recorded for that agent.
        ``limit`` caps the number of results, applied after filtering. The
        returned list is ordered most-recent-last (insertion order) and is
        a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            movements = list(self._movements.values())
        if agent_id is not None:
            movements = [m for m in movements if m.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return movements[-n:] if n else []

    def get_movement(self, event_id: str) -> MovementEvent:
        """Retrieve a movement event by id.

        Raises ``ValueError`` if no movement exists with that id.
        """
        with self._lock:
            event = self._movements.get(event_id)
        if event is None:
            raise ValueError(f"movement {event_id!r} not found")
        return event

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> BuoyancySnapshot:
        """Aggregate an agent's recent readings into a buoyancy snapshot.

        ``avg_buoyancy`` is the mean ``buoyancy_score`` of the agent's
        most recent readings, capped at the last
        ``MAX_RECENT_FOR_SNAPSHOT`` (10). ``surface_count`` is how many of
        the agent's readings sit at the SURFACE layer at snapshot time.
        ``deep_count`` is how many sit at the DEEP or ABYSSAL layers.
        ``dominant_force`` is the mode of the buoyancy force across ALL of
        the agent's readings (so a single recent outlier cannot dominate),
        or ``None`` if the agent has no readings. ``regime`` is derived
        from ``avg_buoyancy`` and the mean velocity of the agent's recent
        movements via ``_determine_regime``. The snapshot is stored and
        reflected in the engine stats. If the agent has no readings,
        ``avg_buoyancy`` is 0.0, ``dominant_force`` is ``None``,
        ``surface_count`` and ``deep_count`` are 0, and ``regime`` is
        NEUTRAL.
        """
        with self._lock:
            agent_readings = self._agent_readings(agent_id)
            agent_movements = self._agent_movements(agent_id)

            recent = agent_readings[-self.MAX_RECENT_FOR_SNAPSHOT:]
            if recent:
                avg_buoyancy = sum(r.buoyancy_score for r in recent) / len(recent)
            else:
                avg_buoyancy = 0.0

            surface_count = sum(
                1 for r in agent_readings if r.current_layer == VerticalLayer.SURFACE
            )
            deep_count = sum(
                1 for r in agent_readings
                if r.current_layer in (VerticalLayer.DEEP, VerticalLayer.ABYSSAL)
            )

            # Dominant force is the mode across ALL of the agent's
            # readings, so a single recent outlier cannot dominate.
            force_counts: Dict[BuoyancyForce, int] = {}
            for r in agent_readings:
                force_counts[r.force] = force_counts.get(r.force, 0) + 1
            if force_counts:
                dominant_force = max(
                    force_counts.items(), key=lambda kv: kv[1]
                )[0]
            else:
                dominant_force = None

            # Average velocity of recent movements disambiguates the
            # near-neutral regime band.
            recent_moves = agent_movements[-self.MAX_RECENT_FOR_SNAPSHOT:]
            if recent_moves:
                avg_velocity = sum(m.velocity for m in recent_moves) / len(recent_moves)
            else:
                avg_velocity = 0.0

            regime = _determine_regime(avg_buoyancy, avg_velocity)
            snapshot = BuoyancySnapshot(
                agent_id=agent_id,
                regime=regime,
                avg_buoyancy=avg_buoyancy,
                surface_count=surface_count,
                deep_count=deep_count,
                dominant_force=dominant_force,
                timestamp=_now(),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._stats["total_snapshots"] += 1
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BuoyancySnapshot]:
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
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return snapshots[-n:] if n else []

    def get_snapshot(self, snapshot_id: str) -> BuoyancySnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise ValueError(f"snapshot {snapshot_id!r} not found")
        return snapshot

    # ── Lift Plans ───────────────────────────────────────────────

    def plan_lift(
        self,
        agent_id: str,
        idea_label: str,
        strategy: Any,
        rationale: str,
        expected_lift: float,
    ) -> LiftPlan:
        """Create a lift plan for an idea and return it.

        ``idea_label`` is a human-readable label for the idea the plan is
        meant to raise. ``strategy`` accepts a ``LiftStrategy`` member or
        its value/name string. ``rationale`` is a human-readable
        explanation of why this strategy was chosen for this idea.
        ``expected_lift`` in [0, 1] is the fraction of upward buoyancy the
        plan is expected to add, clamped to that range. Raises
        ``RuntimeError`` if the lift registry is full.
        """
        with self._lock:
            if len(self._lifts) >= self.MAX_LIFTS:
                raise RuntimeError("lift registry is full")
            plan = LiftPlan(
                agent_id=agent_id,
                idea_label=str(idea_label),
                strategy=_resolve_enum(LiftStrategy, strategy),
                rationale=str(rationale),
                expected_lift=_clamp(expected_lift, 0.0, 1.0),
                timestamp=_now(),
            )
            self._lifts[plan.plan_id] = plan
            self._stats["total_lifts"] += 1
            return plan

    def list_lifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LiftPlan]:
        """Return lift plans, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to plans created for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            lifts = list(self._lifts.values())
        if agent_id is not None:
            lifts = [p for p in lifts if p.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return lifts[-n:] if n else []

    def get_lift(self, plan_id: str) -> LiftPlan:
        """Retrieve a lift plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            plan = self._lifts.get(plan_id)
        if plan is None:
            raise ValueError(f"lift plan {plan_id!r} not found")
        return plan

    # ── Sink Plans ───────────────────────────────────────────────

    def plan_sink(
        self,
        agent_id: str,
        idea_label: str,
        strategy: Any,
        rationale: str,
        expected_sink: float,
    ) -> SinkPlan:
        """Create a sink plan for an idea and return it.

        ``idea_label`` is a human-readable label for the idea the plan is
        meant to lower. ``strategy`` accepts a ``SinkStrategy`` member or
        its value/name string. ``rationale`` is a human-readable
        explanation of why this strategy was chosen for this idea.
        ``expected_sink`` in [0, 1] is the fraction of downward buoyancy
        the plan is expected to add, clamped to that range. Raises
        ``RuntimeError`` if the sink registry is full.
        """
        with self._lock:
            if len(self._sinks) >= self.MAX_SINKS:
                raise RuntimeError("sink registry is full")
            plan = SinkPlan(
                agent_id=agent_id,
                idea_label=str(idea_label),
                strategy=_resolve_enum(SinkStrategy, strategy),
                rationale=str(rationale),
                expected_sink=_clamp(expected_sink, 0.0, 1.0),
                timestamp=_now(),
            )
            self._sinks[plan.plan_id] = plan
            self._stats["total_sinks"] += 1
            return plan

    def list_sinks(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SinkPlan]:
        """Return sink plans, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to plans created for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            sinks = list(self._sinks.values())
        if agent_id is not None:
            sinks = [p for p in sinks if p.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return sinks[-n:] if n else []

    def get_sink(self, plan_id: str) -> SinkPlan:
        """Retrieve a sink plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            plan = self._sinks.get(plan_id)
        if plan is None:
            raise ValueError(f"sink plan {plan_id!r} not found")
        return plan

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> BuoyancyProfile:
        """Return the agent's buoyancy profile, creating it if absent.

        When a profile does not yet exist for the agent, a fresh one is
        computed from the agent's currently recorded readings and
        movements: ``avg_buoyancy`` is the mean buoyancy score,
        ``dominant_force`` is the modal force (or ``None`` if no
        readings), ``regime`` is derived from ``avg_buoyancy`` and the
        mean movement velocity, ``surface_count`` is how many readings sit
        at the SURFACE layer, ``total_readings`` is the agent's reading
        count, and ``total_movements`` is the agent's movement count. The
        profile is then stored so subsequent record calls can update it
        incrementally.
        """
        with self._lock:
            existing = self._profiles.get(agent_id)
            if existing is not None:
                return existing

            agent_readings = self._agent_readings(agent_id)
            agent_movements = self._agent_movements(agent_id)

            if agent_readings:
                avg_buoyancy = sum(
                    r.buoyancy_score for r in agent_readings
                ) / len(agent_readings)
                force_counts: Dict[BuoyancyForce, int] = {}
                for r in agent_readings:
                    force_counts[r.force] = force_counts.get(r.force, 0) + 1
                dominant_force = max(
                    force_counts.items(), key=lambda kv: kv[1]
                )[0]
                surface_count = sum(
                    1 for r in agent_readings
                    if r.current_layer == VerticalLayer.SURFACE
                )
            else:
                avg_buoyancy = 0.0
                dominant_force = None
                surface_count = 0

            if agent_movements:
                avg_velocity = sum(
                    m.velocity for m in agent_movements
                ) / len(agent_movements)
            else:
                avg_velocity = 0.0

            profile = BuoyancyProfile(
                agent_id=agent_id,
                avg_buoyancy=avg_buoyancy,
                dominant_force=dominant_force,
                regime=_determine_regime(avg_buoyancy, avg_velocity),
                surface_count=surface_count,
                total_readings=len(agent_readings),
                total_movements=len(agent_movements),
                last_updated=_now(),
            )
            self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> BuoyancyProfile:
        """Update fields on an agent's buoyancy profile and return it.

        The profile is fetched (or created) first, then each keyword in
        ``kwargs`` is applied to the matching attribute. ``dominant_force``
        and ``regime`` may be supplied as enum members or their value/name
        strings; they are normalized to enum members. Numeric fields
        (``avg_buoyancy``) are coerced to floats. Integer fields
        (``surface_count``, ``total_readings``, ``total_movements``) are
        coerced to ints. Unknown keys are ignored so callers can pass
        through generic update payloads safely.
        """
        with self._lock:
            profile = self.get_profile(agent_id)
            for key, value in kwargs.items():
                if key == "dominant_force" and value is not None:
                    profile.dominant_force = _resolve_enum(BuoyancyForce, value)
                elif key == "regime":
                    profile.regime = _resolve_enum(BuoyancyRegime, value)
                elif key == "avg_buoyancy":
                    try:
                        setattr(profile, key, float(value))
                    except (TypeError, ValueError):
                        pass
                elif key in ("surface_count", "total_readings", "total_movements"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
                elif hasattr(profile, key):
                    setattr(profile, key, value)
            profile.last_updated = _now()
            return profile

    def list_profiles(self) -> List[BuoyancyProfile]:
        """Return all stored buoyancy profiles as a snapshot list."""
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> BuoyancyStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counter dict maintained by the
        record methods. ``regime_distribution`` is tallied from stored
        snapshots and keyed by the regime ``.value`` string.
        ``force_distribution`` is tallied from stored readings and keyed
        by the force ``.value`` string. ``layer_distribution`` is tallied
        from stored readings and keyed by the layer ``.value`` string. All
        three dicts are plain ``Dict[str, int]`` so the result is
        JSON-serializable directly. ``avg_buoyancy`` is the mean buoyancy
        score across all recorded readings, or 0.0 if there are none.
        """
        with self._lock:
            s = self._stats
            regime_dist: Dict[str, int] = {}
            for snap in self._snapshots.values():
                key = _enum_value(BuoyancyRegime, snap.regime)
                regime_dist[key] = regime_dist.get(key, 0) + 1
            force_dist: Dict[str, int] = {}
            layer_dist: Dict[str, int] = {}
            for r in self._readings.values():
                fkey = _enum_value(BuoyancyForce, r.force)
                force_dist[fkey] = force_dist.get(fkey, 0) + 1
                lkey = _enum_value(VerticalLayer, r.current_layer)
                layer_dist[lkey] = layer_dist.get(lkey, 0) + 1
            total_readings = int(s["total_readings"])
            if total_readings > 0:
                avg_buoyancy = float(s["buoyancy_sum"]) / total_readings
            else:
                avg_buoyancy = 0.0
            return BuoyancyStats(
                total_readings=total_readings,
                total_movements=int(s["total_movements"]),
                total_snapshots=int(s["total_snapshots"]),
                total_lifts=int(s["total_lifts"]),
                total_sinks=int(s["total_sinks"]),
                regime_distribution=regime_dist,
                force_distribution=force_dist,
                layer_distribution=layer_dist,
                avg_buoyancy=avg_buoyancy,
            )

    # ── Maintenance ───────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Drops every reading, movement, snapshot, lift plan, sink plan, and
        profile, and re-initializes the running counters. The lock itself
        is not replaced.
        """
        with self._lock:
            self._readings.clear()
            self._movements.clear()
            self._snapshots.clear()
            self._lifts.clear()
            self._sinks.clear()
            self._profiles.clear()
            self._stats = self._init_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional["AgentCognitiveBuoyancy"] = None
_engine_lock = threading.Lock()


def get_buoyancy_engine() -> AgentCognitiveBuoyancy:
    """Get or create the singleton ``AgentCognitiveBuoyancy`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveBuoyancy()
    return _engine


def reset_buoyancy_engine() -> None:
    """Reset the singleton ``AgentCognitiveBuoyancy`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_buoyancy_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
