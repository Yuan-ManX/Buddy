from __future__ import annotations

"""Agent Cognitive Friction Engine — resistance when shifting cognitive states

Models the cost of changing direction between concepts, beliefs, and contexts,
driven by anchoring, commitment, context-switching, abstraction distance, and habit.

Core capabilities:
  - Friction Measurements: per-transition resistance from each source
  - Transition Events: state-to-state shifts with friction, duration, completion
  - Lubrication Plans: prime, chunk, bridge, reframe, release, prompt
  - Recovery Assessments: flowing, sluggish, stalled, reversing, recovered
  - Regime Classification: fluid through frozen

Architecture:
  AgentCognitiveFriction (singleton)
  ├── FrictionMeasurement, TransitionEvent, FrictionSnapshot
  ├── LubricationPlan, RecoveryAssessment, FrictionProfile
  └── FrictionStats
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
    """Generate a short unique identifier for a measurement/event/plan/etc."""
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` resistance score.
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
    member values (e.g. ``"fluid"``) and then against member names
    (e.g. ``"FLUID"``), so callers may pass either form. Raises
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


def _determine_regime(resistance_score: float) -> "FrictionRegime":
    """Classify a friction regime from a resistance score in [0, 1].

    The bands partition the [0, 1] range into five qualitative regimes.
    Lower scores mean easier transitions (FLUID, SMOOTH); higher scores
    mean the agent is increasingly stuck (MODERATE, HIGH) until it can no
    longer shift at all (FROZEN).
    """
    score = _clamp(resistance_score)
    if score < 0.2:
        return FrictionRegime.FLUID
    if score < 0.4:
        return FrictionRegime.SMOOTH
    if score < 0.6:
        return FrictionRegime.MODERATE
    if score < 0.8:
        return FrictionRegime.HIGH
    return FrictionRegime.FROZEN


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class FrictionSource(str, Enum):
    """The distinct sources from which cognitive friction arises.

    Friction is not a single force. A transition's resistance is the
    composition of several independent sources, each describing a
    different reason that shifting from the current state to the target
    state is hard. Identifying the dominant source is the first step
    toward selecting a lubrication strategy that actually addresses the
    cause rather than the symptom.

    ANCHORING is over-attachment to the current concept: the agent has
    invested attention in a particular framing and resists leaving it.
    COMMITMENT is sunk cost in the current belief: revising a belief the
    agent has acted on costs more than revising one it merely holds.
    CONTEXT_SWITCH is the cost of swapping the active context, since each
    context carries its own working set that must be torn down and
    rebuilt. ABSTRACTION_GAP is the distance between abstraction levels:
    moving from concrete instance to abstract pattern (or back) crosses a
    gap that scales with the distance. INCOMPATIBILITY is logical
    incompatibility between the two states, which forces a reconciliation
    that is costly in proportion to the contradiction. HABIT is the pull
    of well-worn pathways: the agent's established routines draw it back
    toward the current state and away from the target.
    """
    ANCHORING = "anchoring"            # over-attachment to current concept
    COMMITMENT = "commitment"          # sunk cost in current belief
    CONTEXT_SWITCH = "context_switch"  # cost of swapping active context
    ABSTRACTION_GAP = "abstraction_gap"  # distance between abstraction levels
    INCOMPATIBILITY = "incompatibility"  # logical incompatibility between states
    HABIT = "habit"                    # well-worn pathway resistance


class FrictionRegime(str, Enum):
    """The regime an agent occupies, classified by its friction profile.

    A regime is a qualitative characterization of how hard it is for the
    agent to shift cognitive states, more informative than the raw
    resistance score alone. FLUID means friction is negligible and
    transitions are effortless, which can be healthy or can signal
    flighty, non-committal reasoning. SMOOTH is the healthy low-friction
    regime: enough resistance that transitions are deliberate without
    being blocked. MODERATE means transitions meet noticeable resistance
    but still complete. HIGH means the agent is stuck-prone: transitions
    frequently stall or reverse. FROZEN means the agent cannot shift at
    all — it is locked into its current state regardless of whether that
    state remains productive.
    """
    FLUID = "fluid"      # negligible friction, effortless transitions
    SMOOTH = "smooth"    # healthy low friction, deliberate transitions
    MODERATE = "moderate"  # noticeable resistance, transitions still complete
    HIGH = "high"        # stuck-prone, transitions frequently stall
    FROZEN = "frozen"    # cannot shift, locked into current state


class TransitionType(str, Enum):
    """The kinds of cognitive transitions friction can obstruct.

    A transition is a shift from one cognitive state to another. The
    type of transition determines which sources of friction are most
    likely to apply and which lubrication strategies are most likely to
    help. CONCEPT_SHIFT moves between concepts within the same context.
    BELIEF_REVISION updates a belief the agent already holds, which
    typically meets commitment friction. CONTEXT_PIVOT changes the
    active context, which meets context-switch friction.
    ABSTRACTION_MOVE changes the abstraction level the agent is
    reasoning at, which meets abstraction-gap friction. PERSPECTIVE_SWITCH
    changes the viewpoint the agent is reasoning from, which can meet
    anchoring and habit friction. GOAL_REDIRECT changes the goal the
    agent is pursuing, which can meet all sources at once.
    """
    CONCEPT_SHIFT = "concept_shift"        # between concepts
    BELIEF_REVISION = "belief_revision"    # updating beliefs
    CONTEXT_PIVOT = "context_pivot"        # changing context
    ABSTRACTION_MOVE = "abstraction_move"  # changing abstraction level
    PERSPECTIVE_SWITCH = "perspective_switch"  # changing viewpoint
    GOAL_REDIRECT = "goal_redirect"        # changing goals


class LubricationStrategy(str, Enum):
    """Strategies for reducing the friction on a transition.

    Lubrication is the deliberate application of a technique that lowers
    the resistance a transition meets, so that a shift the agent could
    not complete on its own becomes completable. The strategy must match
    the source of the friction to be effective: priming the target
    context helps with context-switch friction but does little for
    incompatibility, and so on.

    PRIME pre-loads the target context so the context-switch cost is paid
    before the transition begins. CHUNK breaks the transition into
    smaller steps so that each individual step meets less resistance.
    BRIDGE builds an intermediate concept that connects the source and
    target, reducing the apparent distance. REFRAME recasts the
    transition so that the source and target are no longer in opposition.
    ANCHOR_RELEASE deliberately releases the current anchor so that
    anchoring friction no longer holds the agent in place. EXTERNAL_PROMPT
    introduces a cue from outside the agent that prompts the shift,
    bypassing the internal resistance.
    """
    PRIME = "prime"                # pre-load target context
    CHUNK = "chunk"                # break transition into smaller steps
    BRIDGE = "bridge"              # build intermediate concept
    REFRAME = "reframe"            # re-frame the transition
    ANCHOR_RELEASE = "anchor_release"  # deliberately release current anchor
    EXTERNAL_PROMPT = "external_prompt"  # use external cue


class RecoveryState(str, Enum):
    """The state of a transition that was stalled and is being recovered.

    When a transition meets more friction than it can overcome, it stalls.
    A lubrication plan is then applied to reduce the resistance, and the
    recovery is tracked through these states. FLOWING means the
    transition is progressing smoothly after lubrication. SLUGGISH means
    it is still slow but moving forward. STALLED means it has stopped
    mid-transition despite the lubrication. REVERSING means it is
    slipping back toward the source state, losing ground. RECOVERED means
    the transition has completed and the agent has settled into the
    target state.
    """
    FLOWING = "flowing"    # transitioning smoothly
    SLUGGISH = "sluggish"  # slow but progressing
    STALLED = "stalled"    # stopped mid-transition
    REVERSING = "reversing"  # slipping back toward source
    RECOVERED = "recovered"  # transition complete


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionMeasurement:
    """One observed resistance value for one transition type from one source.

    ``measurement_id`` uniquely identifies this measurement. ``agent_id``
    is the agent whose friction was sampled. ``source`` is the
    ``FrictionSource`` the resistance is attributed to. ``transition_type``
    is the ``TransitionType`` the resistance was encountered on.
    ``resistance_score`` in [0, 1] is the magnitude of the resistance,
    where 0 means no resistance at all and 1 means the transition is
    completely blocked. ``timestamp`` is when the measurement was taken.
    ``context`` is an optional free-form dict carrying any additional
    detail the caller wants to preserve (e.g. the source and target
    states, the task that triggered the transition).
    """
    measurement_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    source: FrictionSource = FrictionSource.ANCHORING
    transition_type: TransitionType = TransitionType.CONCEPT_SHIFT
    resistance_score: float = 0.0
    timestamp: str = field(default_factory=_now)
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this measurement to a plain dict, expanding the enums."""
        return {
            "measurement_id": self.measurement_id,
            "agent_id": self.agent_id,
            "source": _enum_value(FrictionSource, self.source),
            "transition_type": _enum_value(TransitionType, self.transition_type),
            "resistance_score": self.resistance_score,
            "timestamp": self.timestamp,
            "context": dict(self.context) if self.context is not None else None,
        }


@dataclass
class TransitionEvent:
    """A record of an attempted state-to-state cognitive shift.

    ``event_id`` uniquely identifies this event. ``agent_id`` is the agent
    that attempted the transition. ``transition_type`` is the
    ``TransitionType`` of the shift. ``from_state`` and ``to_state`` are
    human-readable labels for the source and target cognitive states
    (e.g. ``"hypothesis-A"`` -> ``"hypothesis-B"``). ``friction_score`` in
    [0, 1] is the resistance the transition actually met, which may
    differ from any single measurement because a transition typically
    composes several. ``duration`` is how long the transition took (or
    has been taking, if still in progress), in seconds.
    ``completed`` is whether the transition reached the target state.
    ``timestamp`` is when the event was recorded.
    """
    event_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    transition_type: TransitionType = TransitionType.CONCEPT_SHIFT
    from_state: str = ""
    to_state: str = ""
    friction_score: float = 0.0
    duration: float = 0.0
    completed: bool = False
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict, expanding the enum."""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "transition_type": _enum_value(TransitionType, self.transition_type),
            "from_state": self.from_state,
            "to_state": self.to_state,
            "friction_score": self.friction_score,
            "duration": self.duration,
            "completed": self.completed,
            "timestamp": self.timestamp,
        }


@dataclass
class FrictionSnapshot:
    """An aggregate view of an agent's friction at a point in time.

    ``snapshot_id`` uniquely identifies this snapshot. ``agent_id`` is the
    agent the snapshot summarizes. ``total_resistance`` in [0, 1] is the
    mean resistance score across the agent's recent measurements (the
    last 10, or fewer if fewer exist). ``dominant_source`` is the
    ``FrictionSource`` that appeared most often across those measurements,
    or ``None`` if the agent has no measurements yet. ``regime`` is the
    ``FrictionRegime`` derived from ``total_resistance`` via
    ``_determine_regime``. ``measurement_count`` is how many measurements
    the agent has on record at snapshot time. ``timestamp`` is when the
    snapshot was taken.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    total_resistance: float = 0.0
    dominant_source: Optional[FrictionSource] = None
    regime: FrictionRegime = FrictionRegime.FLUID
    measurement_count: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums.

        ``dominant_source`` may be ``None``; it is serialized as ``None``
        in that case rather than as a string.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "total_resistance": self.total_resistance,
            "dominant_source": (
                _enum_value(FrictionSource, self.dominant_source)
                if self.dominant_source is not None
                else None
            ),
            "regime": _enum_value(FrictionRegime, self.regime),
            "measurement_count": self.measurement_count,
            "timestamp": self.timestamp,
        }


@dataclass
class LubricationPlan:
    """A strategy and step sequence for reducing friction on a transition.

    ``plan_id`` uniquely identifies this plan. ``agent_id`` is the agent
    the plan is for. ``transition_type`` is the ``TransitionType`` the
    plan is meant to lubricate. ``strategy`` is the ``LubricationStrategy``
    selected to deliver the reduction. ``expected_relief`` in [0, 1] is
    the fraction of the current friction the plan is expected to remove,
    recorded at plan time so the actual effect can later be compared.
    ``steps`` is the ordered list of actions to execute. ``timestamp`` is
    when the plan was created.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    transition_type: TransitionType = TransitionType.CONCEPT_SHIFT
    strategy: LubricationStrategy = LubricationStrategy.PRIME
    expected_relief: float = 0.0
    steps: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding the enums."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "transition_type": _enum_value(TransitionType, self.transition_type),
            "strategy": _enum_value(LubricationStrategy, self.strategy),
            "expected_relief": self.expected_relief,
            "steps": list(self.steps),
            "timestamp": self.timestamp,
        }


@dataclass
class RecoveryAssessment:
    """An assessment of a stalled transition's progress toward recovery.

    ``assessment_id`` uniquely identifies this assessment.
    ``agent_id`` is the agent whose transition is being assessed.
    ``transition_event_id`` links back to the ``TransitionEvent`` that
    stalled and is being recovered. ``state`` is the current
    ``RecoveryState`` of the recovery. ``progress`` in [0, 1] is how far
    the transition has progressed toward the target state, where 0 means
    still at the source and 1 means fully arrived. ``blockers`` is a list
    of human-readable descriptions of whatever is still obstructing
    completion (empty if nothing is). ``timestamp`` is when the assessment
    was made.
    """
    assessment_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    transition_event_id: str = ""
    state: RecoveryState = RecoveryState.STALLED
    progress: float = 0.0
    blockers: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this assessment to a plain dict, expanding the enum."""
        return {
            "assessment_id": self.assessment_id,
            "agent_id": self.agent_id,
            "transition_event_id": self.transition_event_id,
            "state": _enum_value(RecoveryState, self.state),
            "progress": self.progress,
            "blockers": list(self.blockers),
            "timestamp": self.timestamp,
        }


@dataclass
class FrictionProfile:
    """Per-agent aggregate friction tendencies.

    ``agent_id`` is the agent this profile describes. ``avg_resistance``
    is the mean resistance score across all of the agent's measurements.
    ``dominant_source`` is the ``FrictionSource`` that appears most often
    for the agent, or ``None`` if the agent has no measurements.
    ``regime`` is the ``FrictionRegime`` derived from ``avg_resistance``.
    ``transition_count`` is how many transitions the agent has attempted.
    ``completed_count`` is how many of those transitions completed.
    ``abandoned_count`` is how many did not complete. ``last_updated`` is
    the timestamp of the most recent profile change.
    """
    agent_id: str = ""
    avg_resistance: float = 0.0
    dominant_source: Optional[FrictionSource] = None
    regime: FrictionRegime = FrictionRegime.FLUID
    transition_count: int = 0
    completed_count: int = 0
    abandoned_count: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enums.

        ``dominant_source`` may be ``None``; it is serialized as ``None``
        in that case rather than as a string.
        """
        return {
            "agent_id": self.agent_id,
            "avg_resistance": self.avg_resistance,
            "dominant_source": (
                _enum_value(FrictionSource, self.dominant_source)
                if self.dominant_source is not None
                else None
            ),
            "regime": _enum_value(FrictionRegime, self.regime),
            "transition_count": self.transition_count,
            "completed_count": self.completed_count,
            "abandoned_count": self.abandoned_count,
            "last_updated": self.last_updated,
        }


@dataclass
class FrictionStats:
    """Aggregate statistics over the current engine state.

    ``total_measurements`` counts all recorded ``FrictionMeasurement``
    records. ``total_transitions`` counts all recorded ``TransitionEvent``
    records. ``total_lubrications`` counts all recorded ``LubricationPlan``
    records. ``total_recoveries`` counts all recorded ``RecoveryAssessment``
    records. ``regime_distribution`` tallies snapshots by their diagnosed
    regime, keyed by the regime's ``.value`` string. ``source_distribution``
    tallies measurements by their friction source, keyed by the source's
    ``.value`` string. Both distribution dicts are plain ``Dict[str, int]``
    so they are already JSON-serializable.
    """
    total_measurements: int = 0
    total_transitions: int = 0
    total_lubrications: int = 0
    total_recoveries: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    source_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The distribution dicts are already keyed by ``.value`` strings, so
        they are copied as-is. This keeps the output JSON-serializable
        without further conversion.
        """
        return {
            "total_measurements": self.total_measurements,
            "total_transitions": self.total_transitions,
            "total_lubrications": self.total_lubrications,
            "total_recoveries": self.total_recoveries,
            "regime_distribution": dict(self.regime_distribution),
            "source_distribution": dict(self.source_distribution),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveFriction:
    """Singleton engine measuring the friction of cognitive transitions.

    Holds friction measurements, transition events, snapshots,
    lubrication plans, recovery assessments, and per-agent profiles. All
    state mutations are guarded by a single reentrant lock so the engine
    is safe to call from multiple threads, including from within its own
    methods. The engine is intentionally dependency-free so it can run in
    any Buddy runtime without extra packages.

    The engine is a measurement instrument first and a control system
    second. It records what friction the agent actually encountered on
    each transition, aggregates those measurements into a regime
    classification, and — when friction is blocking a transition —
    prescribes a lubrication strategy and tracks the recovery. It does
    not itself force transitions; it makes the cost of transitions
    legible so that the agent (or its orchestrator) can decide whether a
    shift is worth its cost and how to make it cheaper.
    """

    # Caps to keep the in-memory engine bounded under runaway callers.
    MAX_MEASUREMENTS: int = 5000
    MAX_TRANSITIONS: int = 5000
    MAX_SNAPSHOTS: int = 5000
    MAX_LUBRICATIONS: int = 5000
    MAX_RECOVERIES: int = 5000
    MAX_RECENT_FOR_SNAPSHOT: int = 10

    # Default step sequences for each lubrication strategy, used when the
    # caller does not supply explicit steps. Each is three actions so the
    # plan always carries a concrete, executable sequence.
    _DEFAULT_LUBRICATION_STEPS: Dict[LubricationStrategy, List[str]] = {
        LubricationStrategy.PRIME: [
            "identify the target context the transition is moving toward",
            "pre-load the target context's working set into active memory",
            "execute the transition with the target already partially active",
        ],
        LubricationStrategy.CHUNK: [
            "decompose the transition into a sequence of smaller sub-shifts",
            "execute each sub-shift in order, completing one before the next",
            "recompose the sub-shifts into the full transition at the end",
        ],
        LubricationStrategy.BRIDGE: [
            "locate or construct an intermediate concept shared by source and target",
            "shift from the source state to the intermediate concept",
            "shift from the intermediate concept to the target state",
        ],
        LubricationStrategy.REFRAME: [
            "identify the framing that puts source and target in opposition",
            "construct an alternative framing under which both coexist",
            "execute the transition under the new framing",
        ],
        LubricationStrategy.ANCHOR_RELEASE: [
            "identify the current anchor holding the agent in the source state",
            "deliberately release the anchor and mark it as suspended",
            "execute the transition with the anchor no longer active",
        ],
        LubricationStrategy.EXTERNAL_PROMPT: [
            "select an external cue whose content prompts the target state",
            "introduce the cue into the agent's input stream",
            "execute the transition as the cue directs",
        ],
    }

    def __init__(self) -> None:
        self._measurements: Dict[str, FrictionMeasurement] = {}
        self._transitions: Dict[str, TransitionEvent] = {}
        self._snapshots: Dict[str, FrictionSnapshot] = {}
        self._lubrications: Dict[str, LubricationPlan] = {}
        self._recoveries: Dict[str, RecoveryAssessment] = {}
        self._profiles: Dict[str, FrictionProfile] = {}
        self._stats: Dict[str, float] = self._init_stats()
        self._lock: threading.RLock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _init_stats() -> Dict[str, float]:
        """Return a fresh running-counter dict for engine statistics."""
        return {
            "total_measurements": 0,
            "total_transitions": 0,
            "total_snapshots": 0,
            "total_lubrications": 0,
            "total_recoveries": 0,
            "resistance_sum": 0.0,
        }

    def _agent_measurements(self, agent_id: str) -> List[FrictionMeasurement]:
        """Return this agent's measurements in insertion order (no lock)."""
        return [m for m in self._measurements.values() if m.agent_id == agent_id]

    def _update_profile_on_transition(self, agent_id: str, event: TransitionEvent) -> None:
        """Refresh an existing profile with a newly recorded transition.

        Increments the per-agent transition counter and either the
        completed or abandoned counter depending on the event outcome.
        Only mutates the profile if one already exists for the agent;
        profiles are created lazily via ``get_profile``.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            return
        profile.transition_count += 1
        if event.completed:
            profile.completed_count += 1
        else:
            profile.abandoned_count += 1
        profile.last_updated = _now()

    # ── Friction Measurements ─────────────────────────────────────

    def measure_friction(
        self,
        agent_id: str,
        source: Any,
        transition_type: Any,
        resistance_score: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> FrictionMeasurement:
        """Record a friction measurement for an agent and return it.

        ``source`` accepts a ``FrictionSource`` member or its value/name
        string. ``transition_type`` accepts a ``TransitionType`` member or
        its value/name string. ``resistance_score`` in [0, 1] is clamped
        to that range. ``context`` is an optional free-form dict copied
        so external mutation does not affect the stored record. Raises
        ``RuntimeError`` if the measurement registry is full.
        """
        with self._lock:
            if len(self._measurements) >= self.MAX_MEASUREMENTS:
                raise RuntimeError("measurement registry is full")
            measurement = FrictionMeasurement(
                agent_id=agent_id,
                source=_resolve_enum(FrictionSource, source),
                transition_type=_resolve_enum(TransitionType, transition_type),
                resistance_score=_clamp(resistance_score, 0.0, 1.0),
                timestamp=_now(),
                context=dict(context) if context is not None else None,
            )
            self._measurements[measurement.measurement_id] = measurement
            self._stats["total_measurements"] += 1
            self._stats["resistance_sum"] += measurement.resistance_score
            return measurement

    def list_measurements(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FrictionMeasurement]:
        """Return measurements, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to measurements recorded for that agent.
        ``limit`` caps the number of results, applied after filtering.
        The returned list is ordered most-recent-last (insertion order)
        and is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            measurements = list(self._measurements.values())
        if agent_id is not None:
            measurements = [m for m in measurements if m.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return measurements[-n:] if n else []

    def get_measurement(self, measurement_id: str) -> FrictionMeasurement:
        """Retrieve a measurement by id.

        Raises ``ValueError`` if no measurement exists with that id, so
        callers can treat the return as a guaranteed non-None value and
        let a single exception type stand in for a not-found HTTP error.
        """
        with self._lock:
            measurement = self._measurements.get(measurement_id)
        if measurement is None:
            raise ValueError(f"measurement {measurement_id!r} not found")
        return measurement

    # ── Transition Events ─────────────────────────────────────────

    def record_transition(
        self,
        agent_id: str,
        transition_type: Any,
        from_state: str,
        to_state: str,
        friction_score: float,
        duration: float,
        completed: bool,
    ) -> TransitionEvent:
        """Record a transition event for an agent and return it.

        ``transition_type`` accepts a ``TransitionType`` member or its
        value/name string. ``from_state`` and ``to_state`` are
        human-readable labels for the source and target cognitive states.
        ``friction_score`` in [0, 1] is the resistance the transition
        actually met, clamped to that range. ``duration`` is the time the
        transition took (or has been taking) in seconds. ``completed`` is
        whether the transition reached the target state. Raises
        ``RuntimeError`` if the transition registry is full.
        """
        with self._lock:
            if len(self._transitions) >= self.MAX_TRANSITIONS:
                raise RuntimeError("transition registry is full")
            event = TransitionEvent(
                agent_id=agent_id,
                transition_type=_resolve_enum(TransitionType, transition_type),
                from_state=str(from_state),
                to_state=str(to_state),
                friction_score=_clamp(friction_score, 0.0, 1.0),
                duration=float(duration),
                completed=bool(completed),
                timestamp=_now(),
            )
            self._transitions[event.event_id] = event
            self._stats["total_transitions"] += 1
            self._update_profile_on_transition(agent_id, event)
            return event

    def list_transitions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TransitionEvent]:
        """Return transitions, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to transitions recorded for that agent.
        ``limit`` caps the number of results, applied after filtering.
        The returned list is ordered most-recent-last (insertion order)
        and is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            transitions = list(self._transitions.values())
        if agent_id is not None:
            transitions = [t for t in transitions if t.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return transitions[-n:] if n else []

    def get_transition(self, event_id: str) -> TransitionEvent:
        """Retrieve a transition event by id.

        Raises ``ValueError`` if no transition exists with that id.
        """
        with self._lock:
            event = self._transitions.get(event_id)
        if event is None:
            raise ValueError(f"transition {event_id!r} not found")
        return event

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> FrictionSnapshot:
        """Aggregate an agent's recent measurements into a snapshot.

        ``total_resistance`` is the mean ``resistance_score`` of the
        agent's most recent measurements, capped at the last
        ``MAX_RECENT_FOR_SNAPSHOT`` (10). ``dominant_source`` is the mode
        of the friction source across all of the agent's measurements, or
        ``None`` if the agent has none. ``regime`` is derived from
        ``total_resistance`` via ``_determine_regime``.
        ``measurement_count`` is the agent's total measurement count at
        snapshot time. The snapshot is stored and reflected in the engine
        stats. If the agent has no measurements, ``total_resistance`` is
        0.0, ``dominant_source`` is ``None``, and ``regime`` is FLUID.
        """
        with self._lock:
            agent_measurements = self._agent_measurements(agent_id)
            recent = agent_measurements[-self.MAX_RECENT_FOR_SNAPSHOT:]
            if recent:
                total_resistance = sum(m.resistance_score for m in recent) / len(recent)
            else:
                total_resistance = 0.0
            # Dominant source is the mode across ALL of the agent's
            # measurements, so a single recent outlier cannot dominate.
            source_counts: Dict[FrictionSource, int] = {}
            for m in agent_measurements:
                source_counts[m.source] = source_counts.get(m.source, 0) + 1
            if source_counts:
                dominant_source = max(
                    source_counts.items(), key=lambda kv: kv[1]
                )[0]
            else:
                dominant_source = None
            regime = _determine_regime(total_resistance)
            snapshot = FrictionSnapshot(
                agent_id=agent_id,
                total_resistance=total_resistance,
                dominant_source=dominant_source,
                regime=regime,
                measurement_count=len(agent_measurements),
                timestamp=_now(),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._stats["total_snapshots"] += 1
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FrictionSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> FrictionSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise ValueError(f"snapshot {snapshot_id!r} not found")
        return snapshot

    # ── Lubrication Plans ─────────────────────────────────────────

    def plan_lubrication(
        self,
        agent_id: str,
        transition_type: Any,
        strategy: Any,
        expected_relief: float,
        steps: Optional[List[str]] = None,
    ) -> LubricationPlan:
        """Create a lubrication plan for a transition and return it.

        ``transition_type`` accepts a ``TransitionType`` member or its
        value/name string. ``strategy`` accepts a ``LubricationStrategy``
        member or its value/name string. ``expected_relief`` in [0, 1] is
        the fraction of the current friction the plan is expected to
        remove, clamped to that range. ``steps`` is an optional explicit
        action sequence; when ``None`` a default three-step sequence is
        selected from the strategy. Raises ``RuntimeError`` if the
        lubrication registry is full.
        """
        with self._lock:
            if len(self._lubrications) >= self.MAX_LUBRICATIONS:
                raise RuntimeError("lubrication registry is full")
            member_strategy = _resolve_enum(LubricationStrategy, strategy)
            member_transition = _resolve_enum(TransitionType, transition_type)
            if steps is None:
                plan_steps = list(
                    self._DEFAULT_LUBRICATION_STEPS.get(member_strategy, [])
                )
            else:
                plan_steps = [str(s) for s in steps]
            plan = LubricationPlan(
                agent_id=agent_id,
                transition_type=member_transition,
                strategy=member_strategy,
                expected_relief=_clamp(expected_relief, 0.0, 1.0),
                steps=plan_steps,
                timestamp=_now(),
            )
            self._lubrications[plan.plan_id] = plan
            self._stats["total_lubrications"] += 1
            return plan

    def list_lubrications(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LubricationPlan]:
        """Return lubrication plans, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to plans created for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            lubrications = list(self._lubrications.values())
        if agent_id is not None:
            lubrications = [p for p in lubrications if p.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return lubrications[-n:] if n else []

    def get_lubrication(self, plan_id: str) -> LubricationPlan:
        """Retrieve a lubrication plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            plan = self._lubrications.get(plan_id)
        if plan is None:
            raise ValueError(f"lubrication plan {plan_id!r} not found")
        return plan

    # ── Recovery Assessments ──────────────────────────────────────

    def assess_recovery(
        self,
        agent_id: str,
        transition_event_id: str,
        state: Any,
        progress: float,
        blockers: Optional[List[str]] = None,
    ) -> RecoveryAssessment:
        """Create a recovery assessment for a stalled transition and return it.

        ``transition_event_id`` links back to the ``TransitionEvent`` that
        stalled and is being recovered. ``state`` accepts a
        ``RecoveryState`` member or its value/name string. ``progress`` in
        [0, 1] is how far the transition has progressed toward the target
        state, clamped to that range. ``blockers`` is an optional list of
        human-readable descriptions of whatever is still obstructing
        completion. Raises ``RuntimeError`` if the recovery registry is
        full.
        """
        with self._lock:
            if len(self._recoveries) >= self.MAX_RECOVERIES:
                raise RuntimeError("recovery registry is full")
            assessment = RecoveryAssessment(
                agent_id=agent_id,
                transition_event_id=str(transition_event_id),
                state=_resolve_enum(RecoveryState, state),
                progress=_clamp(progress, 0.0, 1.0),
                blockers=[str(b) for b in (blockers or [])],
                timestamp=_now(),
            )
            self._recoveries[assessment.assessment_id] = assessment
            self._stats["total_recoveries"] += 1
            return assessment

    def list_recoveries(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RecoveryAssessment]:
        """Return recovery assessments, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to assessments recorded for that agent.
        ``limit`` caps the number of results, applied after filtering.
        The returned list is ordered most-recent-last (insertion order)
        and is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            recoveries = list(self._recoveries.values())
        if agent_id is not None:
            recoveries = [a for a in recoveries if a.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return recoveries[-n:] if n else []

    def get_recovery(self, assessment_id: str) -> RecoveryAssessment:
        """Retrieve a recovery assessment by id.

        Raises ``ValueError`` if no assessment exists with that id.
        """
        with self._lock:
            assessment = self._recoveries.get(assessment_id)
        if assessment is None:
            raise ValueError(f"recovery assessment {assessment_id!r} not found")
        return assessment

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> FrictionProfile:
        """Return the agent's friction profile, creating it if absent.

        When a profile does not yet exist for the agent, a fresh one is
        computed from the agent's currently recorded measurements and
        transitions: ``avg_resistance`` is the mean resistance score,
        ``dominant_source`` is the modal source (or ``None`` if no
        measurements), ``regime`` is derived from ``avg_resistance``,
        ``transition_count`` is the total transitions attempted, and
        ``completed_count`` / ``abandoned_count`` split that total by
        outcome. The profile is then stored so subsequent record calls
        can update it incrementally.
        """
        with self._lock:
            existing = self._profiles.get(agent_id)
            if existing is not None:
                return existing
            agent_measurements = self._agent_measurements(agent_id)
            agent_transitions = [
                t for t in self._transitions.values() if t.agent_id == agent_id
            ]
            if agent_measurements:
                avg_resistance = sum(
                    m.resistance_score for m in agent_measurements
                ) / len(agent_measurements)
                source_counts: Dict[FrictionSource, int] = {}
                for m in agent_measurements:
                    source_counts[m.source] = source_counts.get(m.source, 0) + 1
                dominant_source = max(
                    source_counts.items(), key=lambda kv: kv[1]
                )[0]
            else:
                avg_resistance = 0.0
                dominant_source = None
            completed = sum(1 for t in agent_transitions if t.completed)
            abandoned = len(agent_transitions) - completed
            profile = FrictionProfile(
                agent_id=agent_id,
                avg_resistance=avg_resistance,
                dominant_source=dominant_source,
                regime=_determine_regime(avg_resistance),
                transition_count=len(agent_transitions),
                completed_count=completed,
                abandoned_count=abandoned,
                last_updated=_now(),
            )
            self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> FrictionProfile:
        """Update fields on an agent's friction profile and return it.

        The profile is fetched (or created) first, then each keyword in
        ``kwargs`` is applied to the matching attribute. ``dominant_source``
        and ``regime`` may be supplied as enum members or their value/name
        strings; they are normalized to enum members. Unknown keys are
        ignored so callers can pass through generic update payloads safely.
        """
        with self._lock:
            profile = self.get_profile(agent_id)
            for key, value in kwargs.items():
                if key == "dominant_source" and value is not None:
                    profile.dominant_source = _resolve_enum(FrictionSource, value)
                elif key == "regime":
                    profile.regime = _resolve_enum(FrictionRegime, value)
                elif hasattr(profile, key):
                    setattr(profile, key, value)
            profile.last_updated = _now()
            return profile

    def list_profiles(self) -> List[FrictionProfile]:
        """Return all stored friction profiles as a snapshot list."""
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> FrictionStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counter dict maintained by the
        record methods. ``regime_distribution`` is tallied from stored
        snapshots and keyed by the regime ``.value`` string.
        ``source_distribution`` is tallied from stored measurements and
        keyed by the source ``.value`` string. Both dicts are plain
        ``Dict[str, int]`` so the result is JSON-serializable directly.
        """
        with self._lock:
            s = self._stats
            regime_dist: Dict[str, int] = {}
            for snap in self._snapshots.values():
                key = _enum_value(FrictionRegime, snap.regime)
                regime_dist[key] = regime_dist.get(key, 0) + 1
            source_dist: Dict[str, int] = {}
            for m in self._measurements.values():
                key = _enum_value(FrictionSource, m.source)
                source_dist[key] = source_dist.get(key, 0) + 1
            return FrictionStats(
                total_measurements=int(s["total_measurements"]),
                total_transitions=int(s["total_transitions"]),
                total_lubrications=int(s["total_lubrications"]),
                total_recoveries=int(s["total_recoveries"]),
                regime_distribution=regime_dist,
                source_distribution=source_dist,
            )

    # ── Maintenance ───────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Drops every measurement, transition, snapshot, lubrication plan,
        recovery assessment, and profile, and re-initializes the running
        counters. The lock itself is not replaced.
        """
        with self._lock:
            self._measurements.clear()
            self._transitions.clear()
            self._snapshots.clear()
            self._lubrications.clear()
            self._recoveries.clear()
            self._profiles.clear()
            self._stats = self._init_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional["AgentCognitiveFriction"] = None
_engine_lock = threading.Lock()


def get_friction_engine() -> AgentCognitiveFriction:
    """Get or create the singleton ``AgentCognitiveFriction`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveFriction()
    return _engine


def reset_friction_engine() -> None:
    """Reset the singleton ``AgentCognitiveFriction`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_friction_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
