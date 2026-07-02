from __future__ import annotations

"""Agent Cognitive Momentum Engine — reasoning as a trajectory with mass and velocity.

Treats the tendency of thought to continue in a particular direction as a form
of inertia. Committed inference weight accumulates into mass; the rate of
advancement becomes velocity; their product is momentum. High momentum enables
depth but causes rigidity; low momentum grants flexibility but risks drift.
The engine detects grooves (high momentum, zero curvature) and computes escape
velocity to apply perturbations that restore useful motion.

Architecture:
  AgentCognitiveMomentum (singleton)
  ├── MomentumVector     (a direction with magnitude, velocity, mass)
  ├── TrajectoryPoint    (a sampled position along the reasoning path)
  ├── StuckStateDetection (a diagnosed groove or stall)
  ├── PerturbationEvent  (an applied redirect)
  ├── EscapePlan         (a strategy for leaving a local minimum)
  ├── MomentumProfile    (per-agent momentum history and tendencies)
  └── MomentumStats      (aggregate engine statistics)
"""

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a vector/point/event/etc."""
    return str(uuid.uuid4())[:8]


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"locked"``) and then against member names
    (e.g. ``"LOCKED"``), so callers may pass either form. Raises
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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _enum_value(enum_cls: type, value: Any) -> str:
    """Return the ``.value`` of an enum member, or a string fallback.

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class TrajectoryState(str, Enum):
    """The dynamical state of a reasoning trajectory at a given moment.

    A trajectory moves through states as momentum and progress change.
    ACCELERATING means momentum is building and the direction is
    intensifying. CRUISING means momentum is steady and the agent is
    covering ground without significant change. DECELERATING means
    momentum is bleeding off, whether because the goal is near or
    because energy is spent. STUCK means the trajectory has settled into
    a groove: motion continues but progress does not. DIVERGING means the
    trajectory is spreading outward, exploring alternatives. CONVERGING
    means the trajectory is narrowing toward a conclusion. STALLED means
    motion has effectively ceased without a resolution being reached.
    """
    ACCELERATING = "accelerating"  # momentum building, direction intensifying
    CRUISING = "cruising"          # steady momentum, covering ground
    DECELERATING = "decelerating"  # momentum bleeding off
    STUCK = "stuck"                # motion without progress (groove)
    DIVERGING = "diverging"        # spreading outward, exploring
    CONVERGING = "converging"      # narrowing toward a conclusion
    STALLED = "stalled"            # motion ceased without resolution


class PerturbationType(str, Enum):
    """The kinds of perturbations that can redirect a stuck trajectory.

    A perturbation is an intentional input that disrupts the current
    direction of reasoning to break unproductive inertia. CONTRARIAN
    challenges the current direction with the strongest opposing view.
    REFRAME recasts the problem from a different angle without denying
    the original framing. ANALOGY imports structure from a distant
    domain to suggest a new direction. RANDOM_INJECTION introduces an
    unrelated element to jolt the trajectory out of its groove.
    DECOMPOSITION breaks the problem into independent subproblems so
    that progress can be made on parts. ABSTRACTION lifts the problem
    to a higher level where the current obstacle may not apply.
    CONTEXT_SHIFT changes the surrounding context that gives the current
    direction its momentum.
    """
    CONTRARIAN = "contrarian"        # challenge with the opposing view
    REFRAME = "reframe"              # recast from a different angle
    ANALOGY = "analogy"              # import structure from another domain
    RANDOM_INJECTION = "random_injection"  # unrelated element to jolt
    DECOMPOSITION = "decomposition"  # break into subproblems
    ABSTRACTION = "abstraction"      # lift to a higher level
    CONTEXT_SHIFT = "context_shift"  # change the surrounding context


class MomentumRegime(str, Enum):
    """The regime a trajectory occupies, classified by its momentum profile.

    A regime is a qualitative characterization of how momentum is
    behaving, more informative than the raw magnitude alone. INERT means
    there is effectively no momentum — the agent is not committing
    weight to any direction. DRIFTING means momentum is low and
    unfocused, so the agent moves but without pressing toward anything.
    FOCUSED is the healthy regime: enough momentum to make progress
    without so much that redirection becomes impossible. HEAVY means
    momentum is high and the agent may be rigid, committed to a
    direction regardless of whether it remains productive. LOCKED is the
    groove state: high momentum combined with near-zero progress and
    near-zero curvature, so the agent is stuck in a track it cannot
    leave. BURSTING means momentum is rapidly accelerating, which can be
    productive or can precede a lock-up if the direction is wrong.
    """
    INERT = "inert"        # no momentum committed
    DRIFTING = "drifting"  # low, unfocused momentum
    FOCUSED = "focused"    # healthy momentum
    HEAVY = "heavy"        # high momentum, possibly rigid
    LOCKED = "locked"      # stuck in a groove
    BURSTING = "bursting"  # rapid acceleration


class EscapeStrategy(str, Enum):
    """Strategies for supplying the energy needed to leave a local minimum.

    WAIT observes the trajectory without intervention, on the hypothesis
    that momentum will decay on its own and a productive direction will
    emerge. NUDGE applies a small perturbation, enough to test
    responsiveness without committing to a redirection. PIVOT commits to
    a new direction, applying a large impulse to overcome inertia. RESET
    halts the current reasoning entirely and restarts from the last
    stable point, discarding accumulated weight. EXTERNAL_INPUT brings
    in information from outside the agent to perturb the trajectory with
    evidence the agent could not generate itself. DECOMPOSE breaks the
    problem into subproblems so that the stuck component can be bypassed.
    ABSTRACT lifts the problem to a level where the current obstacle
    dissolves.
    """
    WAIT = "wait"              # observe, let momentum decay
    NUDGE = "nudge"            # small perturbation to test response
    PIVOT = "pivot"            # large impulse to a new direction
    RESET = "reset"            # halt and restart from last stable point
    EXTERNAL_INPUT = "external_input"  # bring in outside information
    DECOMPOSE = "decompose"    # break into subproblems
    ABSTRACT = "abstract"      # lift to a higher level


class ProgressSignal(str, Enum):
    """The directional quality of progress at a trajectory point.

    FORWARD means the trajectory advanced toward its goal. LATERAL means
    the trajectory moved without advancing — useful exploration, but not
    progress in the strict sense. BACKWARD means the trajectory moved
    away from its goal, undoing prior progress. NONE means no movement
    was registered, which combined with high momentum is the signature
    of a groove.
    """
    FORWARD = "forward"    # advanced toward the goal
    LATERAL = "lateral"    # moved without advancing
    BACKWARD = "backward"  # moved away from the goal
    NONE = "none"          # no movement registered


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MomentumVector:
    """A reasoning direction with magnitude, velocity, and accumulated mass.

    ``direction`` is a human-readable label for the line of reasoning
    (e.g. ``"forward"``, ``"refine hypothesis"``). ``magnitude`` in
    [0, 1] is the strength of commitment to the direction. ``velocity``
    is the per-step change in magnitude, so positive velocity means the
    commitment is intensifying. ``acceleration`` is the rate of change of
    velocity. ``curvature`` measures change in direction (not speed): low
    curvature means the reasoning is going straight, high curvature means
    it is turning. ``mass`` is the accumulated inference weight behind
    the direction, which governs how hard it is to redirect.
    ``computed_at`` is the timestamp of the most recent computation.
    """
    vector_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    direction: str = ""
    magnitude: float = 0.0
    velocity: float = 0.0
    acceleration: float = 0.0
    curvature: float = 0.0
    mass: float = 1.0
    computed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this vector to a plain dict."""
        return {
            "vector_id": self.vector_id,
            "agent_id": self.agent_id,
            "direction": self.direction,
            "magnitude": self.magnitude,
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "curvature": self.curvature,
            "mass": self.mass,
            "computed_at": self.computed_at,
        }


@dataclass
class TrajectoryPoint:
    """A sampled position along an agent's reasoning trajectory.

    ``step`` is the integer index of the sample in trajectory order.
    ``position`` is a sparse coordinate map (e.g. ``{"clarity": 0.4,
    "depth": 0.7}``) describing where the reasoning currently sits in
    the agent's problem space. ``momentum`` is the ``MomentumVector``
    measured at this point, or ``None`` if momentum was not recorded.
    ``progress`` classifies the directional quality of the step.
    ``reward`` is the scalar payoff observed at this point, which the
    agent may use to reinforce or dampen the current direction.
    ``recorded_at`` is the timestamp of the sample.
    """
    point_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    step: int = 0
    position: Dict[str, float] = field(default_factory=dict)
    momentum: Optional[MomentumVector] = None
    progress: ProgressSignal = ProgressSignal.FORWARD
    reward: float = 0.0
    recorded_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this point to a plain dict.

        The nested ``momentum`` is serialized via its own ``to_dict`` when
        present, or left as ``None``.
        """
        return {
            "point_id": self.point_id,
            "agent_id": self.agent_id,
            "step": self.step,
            "position": dict(self.position),
            "momentum": self.momentum.to_dict() if self.momentum is not None else None,
            "progress": _enum_value(ProgressSignal, self.progress),
            "reward": self.reward,
            "recorded_at": self.recorded_at,
        }


@dataclass
class StuckStateDetection:
    """A diagnosed groove or stall in a reasoning trajectory.

    ``trajectory_id`` identifies the trajectory under examination.
    ``momentum_magnitude``, ``progress_rate``, and ``curvature`` are the
    raw signals used to classify the regime. ``regime`` is the resulting
    ``MomentumRegime``. ``confidence`` in [0, 1] measures how strongly
    the signals support the diagnosis. ``suggested_perturbations`` lists
    the perturbation types the engine recommends to escape this state,
    ordered by expected usefulness. ``detected_at`` is the timestamp.
    """
    detection_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    trajectory_id: str = ""
    momentum_magnitude: float = 0.0
    progress_rate: float = 0.0
    curvature: float = 0.0
    regime: MomentumRegime = MomentumRegime.FOCUSED
    detected_at: str = field(default_factory=_now)
    confidence: float = 0.0
    suggested_perturbations: List[PerturbationType] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this detection to a plain dict, expanding the enums."""
        return {
            "detection_id": self.detection_id,
            "agent_id": self.agent_id,
            "trajectory_id": self.trajectory_id,
            "momentum_magnitude": self.momentum_magnitude,
            "progress_rate": self.progress_rate,
            "curvature": self.curvature,
            "regime": _enum_value(MomentumRegime, self.regime),
            "detected_at": self.detected_at,
            "confidence": self.confidence,
            "suggested_perturbations": [
                _enum_value(PerturbationType, p) for p in self.suggested_perturbations
            ],
        }


@dataclass
class PerturbationEvent:
    """A record of a perturbation applied to redirect a trajectory.

    ``perturbation_type`` is the kind of redirect applied.
    ``target_trajectory`` identifies the trajectory that received the
    perturbation. ``intensity`` in [0, 1] is the strength of the applied
    impulse. ``expected_impact`` is the anticipated magnitude of effect
    on the trajectory's direction, recorded at application time so the
    actual effect can later be compared. ``applied_at`` is the timestamp.
    ``outcome`` is a free-form status string, defaulting to ``"applied"``
    and updated as the effect is observed.
    """
    event_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    perturbation_type: PerturbationType = PerturbationType.REFRAME
    target_trajectory: str = ""
    intensity: float = 0.5
    expected_impact: float = 0.3
    applied_at: str = field(default_factory=_now)
    outcome: str = "applied"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict, expanding the enum."""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "perturbation_type": _enum_value(PerturbationType, self.perturbation_type),
            "target_trajectory": self.target_trajectory,
            "intensity": self.intensity,
            "expected_impact": self.expected_impact,
            "applied_at": self.applied_at,
            "outcome": self.outcome,
        }


@dataclass
class EscapePlan:
    """A strategy and step sequence for leaving a local minimum.

    ``current_momentum`` is the momentum the trajectory carries at plan
    creation. ``escape_velocity`` is the impulse magnitude the engine
    computed as necessary to break free. ``strategy`` is the
    ``EscapeStrategy`` selected to deliver that impulse. ``steps`` is the
    ordered list of actions to execute. ``estimated_steps`` is the
    expected length of the escape, used for planning and timeout.
    ``created_at`` is the timestamp.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    trajectory_id: str = ""
    current_momentum: float = 0.0
    escape_velocity: float = 0.0
    strategy: EscapeStrategy = EscapeStrategy.NUDGE
    steps: List[str] = field(default_factory=list)
    estimated_steps: int = 3
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding the enum."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "trajectory_id": self.trajectory_id,
            "current_momentum": self.current_momentum,
            "escape_velocity": self.escape_velocity,
            "strategy": _enum_value(EscapeStrategy, self.strategy),
            "steps": list(self.steps),
            "estimated_steps": self.estimated_steps,
            "created_at": self.created_at,
        }


@dataclass
class MomentumProfile:
    """Per-agent momentum history and tendencies.

    ``baseline_momentum`` is the agent's typical resting momentum, taken
    from the first recorded vector. ``peak_momentum`` is the highest
    magnitude observed. ``avg_curvature`` is the mean curvature across
    the agent's vectors, indicating how much the agent tends to turn.
    ``regime_distribution`` tallies how often each regime has been
    diagnosed for the agent. ``total_vectors`` and
    ``total_perturbations`` count those records. ``stuck_rate`` is the
    fraction of detections that landed in the LOCKED regime.
    ``updated_at`` is the timestamp of the most recent profile change.
    """
    agent_id: str = ""
    baseline_momentum: float = 0.0
    peak_momentum: float = 0.0
    avg_curvature: float = 0.0
    regime_distribution: Dict[MomentumRegime, int] = field(default_factory=dict)
    total_vectors: int = 0
    total_perturbations: int = 0
    stuck_rate: float = 0.0
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict.

        The ``regime_distribution`` dict is keyed by ``MomentumRegime``
        enums; each key is converted to its ``.value`` string so the
        result is JSON-serializable.
        """
        return {
            "agent_id": self.agent_id,
            "baseline_momentum": self.baseline_momentum,
            "peak_momentum": self.peak_momentum,
            "avg_curvature": self.avg_curvature,
            "regime_distribution": {
                _enum_value(MomentumRegime, k): v
                for k, v in self.regime_distribution.items()
            },
            "total_vectors": self.total_vectors,
            "total_perturbations": self.total_perturbations,
            "stuck_rate": self.stuck_rate,
            "updated_at": self.updated_at,
        }


@dataclass
class MomentumStats:
    """Aggregate statistics over the current engine state.

    ``regime_distribution`` tallies detections by regime.
    ``progress_distribution`` tallies trajectory points by progress
    signal. ``avg_momentum`` is the mean vector magnitude across all
    recorded vectors. ``avg_escape_velocity`` is the mean escape
    velocity across all escape plans. Both distribution dicts are keyed
    by enum members; ``to_dict`` converts the keys to their ``.value``
    strings for JSON serialization.
    """
    total_vectors: int = 0
    total_points: int = 0
    total_stuck_detections: int = 0
    total_perturbations: int = 0
    total_escapes: int = 0
    regime_distribution: Dict[MomentumRegime, int] = field(default_factory=dict)
    progress_distribution: Dict[ProgressSignal, int] = field(default_factory=dict)
    avg_momentum: float = 0.0
    avg_escape_velocity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enum keys."""
        return {
            "total_vectors": self.total_vectors,
            "total_points": self.total_points,
            "total_stuck_detections": self.total_stuck_detections,
            "total_perturbations": self.total_perturbations,
            "total_escapes": self.total_escapes,
            "regime_distribution": {
                _enum_value(MomentumRegime, k): v
                for k, v in self.regime_distribution.items()
            },
            "progress_distribution": {
                _enum_value(ProgressSignal, k): v
                for k, v in self.progress_distribution.items()
            },
            "avg_momentum": self.avg_momentum,
            "avg_escape_velocity": self.avg_escape_velocity,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveMomentum:
    """Singleton engine tracking reasoning momentum and escaping stuck states.

    Holds momentum vectors, trajectory points, stuck-state detections,
    perturbation events, escape plans, and per-agent profiles. All state
    mutations are guarded by a single reentrant lock so the engine is
    safe to call from multiple threads. The engine also maintains a
    per-agent trajectory history (an ordered list of points) so that
    downstream consumers can replay an agent's reasoning path.
    """

    # Caps to keep the in-memory engine bounded under runaway callers.
    MAX_VECTORS: int = 5000
    MAX_POINTS: int = 10000
    MAX_DETECTIONS: int = 5000
    MAX_PERTURBATIONS: int = 5000
    MAX_ESCAPES: int = 5000
    MAX_TRAJECTORY_HISTORY: int = 500

    # Default step sequences for each escape strategy, used when the
    # caller does not supply explicit steps. Each is three actions so the
    # default ``estimated_steps`` of 3 stays consistent.
    _DEFAULT_ESCAPE_STEPS: Dict[EscapeStrategy, List[str]] = {
        EscapeStrategy.WAIT: [
            "observe trajectory without intervening",
            "measure momentum decay over interval",
            "reassess regime and pick next action",
        ],
        EscapeStrategy.NUDGE: [
            "apply small perturbation at low intensity",
            "observe trajectory response",
            "reinforce direction if response is productive",
        ],
        EscapeStrategy.PIVOT: [
            "select a new reasoning direction",
            "apply large contrarian impulse to overcome inertia",
            "commit accumulated weight to the new direction",
        ],
        EscapeStrategy.RESET: [
            "halt the current line of reasoning",
            "clear accumulated inference weight",
            "restart from the last stable trajectory point",
        ],
        EscapeStrategy.EXTERNAL_INPUT: [
            "request information the agent cannot generate itself",
            "integrate the new evidence into the trajectory",
            "recompute momentum under the updated context",
        ],
        EscapeStrategy.DECOMPOSE: [
            "break the problem into independent subproblems",
            "advance each subproblem along its own trajectory",
            "recombine the subproblem results into a whole",
        ],
        EscapeStrategy.ABSTRACT: [
            "identify the pattern shared by the stuck components",
            "lift the problem to a higher abstraction level",
            "re-derive specifics once the obstacle dissolves",
        ],
    }

    def __init__(self) -> None:
        self._vectors: Dict[str, MomentumVector] = {}
        self._points: Dict[str, TrajectoryPoint] = {}
        self._detections: Dict[str, StuckStateDetection] = {}
        self._perturbations: Dict[str, PerturbationEvent] = {}
        self._escapes: Dict[str, EscapePlan] = {}
        self._profiles: Dict[str, MomentumProfile] = {}
        self._stats: Dict[str, float] = self._init_stats()
        self._trajectory_history: Dict[str, List[TrajectoryPoint]] = {}
        self._lock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _init_stats() -> Dict[str, float]:
        """Return a fresh running-counter dict for engine statistics."""
        return {
            "total_vectors": 0,
            "total_points": 0,
            "total_stuck_detections": 0,
            "total_perturbations": 0,
            "total_escapes": 0,
            "momentum_sum": 0.0,
            "escape_velocity_sum": 0.0,
        }

    @staticmethod
    def _compute_regime(
        magnitude: float,
        velocity: float,
        curvature: float,
    ) -> MomentumRegime:
        """Classify a momentum regime from raw signals.

        Pure function with no engine state. The checks are ordered so
        that the most specific and severe diagnoses win first:

        * LOCKED — high momentum, low progress, near-zero curvature: the
          agent is committed to a direction that is going nowhere and is
          not turning. This is the groove.
        * HEAVY — high momentum with low progress but enough curvature
          that the agent is not yet fully locked: rigidity is developing.
        * INERT — momentum has effectively collapsed: the agent is not
          committing weight to any direction.
        * DRIFTING — low momentum with high curvature: the agent is
          turning frequently without pressing in any direction.
        * BURSTING — velocity is high: momentum is rapidly accelerating,
          which can be productive or can precede a lock-up.
        * FOCUSED — the healthy default: enough momentum to progress
          without the pathologies above.
        """
        if magnitude > 0.8 and velocity < 0.1 and curvature < 0.05:
            return MomentumRegime.LOCKED
        if magnitude > 0.6 and velocity < 0.2:
            return MomentumRegime.HEAVY
        if magnitude < 0.2:
            return MomentumRegime.INERT
        if magnitude < 0.4 and curvature > 0.3:
            return MomentumRegime.DRIFTING
        if velocity > 0.5:
            return MomentumRegime.BURSTING
        return MomentumRegime.FOCUSED

    @staticmethod
    def _classification_for_regime(
        regime: MomentumRegime,
        momentum: float,
        progress_rate: float,
        curvature: float,
    ) -> Tuple[float, List[PerturbationType]]:
        """Return ``(confidence, suggested_perturbations)`` for a regime.

        Confidence measures how strongly the signals support the stuck
        diagnosis; it is high when the regime is clearly unproductive and
        low when the regime is healthy. The suggested perturbations are
        the redirects the engine recommends, ordered by expected
        usefulness for that regime. Healthy regimes (BURSTING, FOCUSED)
        carry an empty suggestion list since no escape is needed.
        """
        if regime == MomentumRegime.LOCKED:
            # Strong signal: high momentum + no progress + no turning.
            confidence = 0.5 + 0.5 * (1.0 - progress_rate)
            perturbations = [
                PerturbationType.CONTRARIAN,
                PerturbationType.REFRAME,
                PerturbationType.RANDOM_INJECTION,
            ]
        elif regime == MomentumRegime.HEAVY:
            # Moderate signal: rigidity is developing but not locked yet.
            confidence = 0.4 + 0.3 * (1.0 - progress_rate)
            perturbations = [
                PerturbationType.DECOMPOSITION,
                PerturbationType.ABSTRACTION,
            ]
        elif regime == MomentumRegime.INERT:
            # Low momentum starves progress; small chance the agent is
            # intentionally resting, so confidence is moderate.
            confidence = 0.3 + 0.2 * (1.0 - momentum)
            perturbations = [
                PerturbationType.ANALOGY,
                PerturbationType.CONTEXT_SHIFT,
            ]
        elif regime == MomentumRegime.DRIFTING:
            # High curvature with low momentum means unfocused turning.
            confidence = 0.3 + 0.2 * min(curvature, 1.0)
            perturbations = [
                PerturbationType.DECOMPOSITION,
                PerturbationType.REFRAME,
            ]
        elif regime == MomentumRegime.BURSTING:
            # Rapid acceleration is not itself a stuck state.
            confidence = 0.2
            perturbations = []
        else:  # FOCUSED
            confidence = 0.15
            perturbations = []
        return _clamp(confidence, 0.0, 1.0), perturbations

    def _update_profile_on_vector(self, agent_id: str, vector: MomentumVector) -> None:
        """Refresh an existing profile with a newly recorded vector.

        Only mutates the profile if one already exists for the agent;
        profiles are created lazily via ``get_or_create_profile``. The
        baseline momentum is intentionally left untouched once set, since
        it represents the agent's resting tendency rather than the
        current value.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            return
        n = profile.total_vectors
        # Running mean of curvature: incorporate the new sample.
        if n <= 0:
            profile.avg_curvature = vector.curvature
            profile.baseline_momentum = vector.magnitude
        else:
            profile.avg_curvature = (
                (profile.avg_curvature * n) + vector.curvature
            ) / (n + 1)
        profile.total_vectors = n + 1
        if vector.magnitude > profile.peak_momentum:
            profile.peak_momentum = vector.magnitude
        profile.updated_at = _now()

    def _update_profile_on_detection(self, agent_id: str, detection: StuckStateDetection) -> None:
        """Refresh an existing profile with a newly recorded detection.

        Recomputes ``stuck_rate`` as the fraction of the agent's
        detections that landed in the LOCKED regime.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            return
        regime_dist = profile.regime_distribution
        regime_dist[detection.regime] = regime_dist.get(detection.regime, 0) + 1
        # Recompute stuck rate from the agent's full detection history.
        agent_detections = [
            d for d in self._detections.values() if d.agent_id == agent_id
        ]
        total = len(agent_detections)
        if total > 0:
            locked = sum(
                1 for d in agent_detections if d.regime == MomentumRegime.LOCKED
            )
            profile.stuck_rate = locked / total
        profile.updated_at = _now()

    def _update_profile_on_perturbation(self, agent_id: str) -> None:
        """Increment the per-agent perturbation counter on an existing profile."""
        profile = self._profiles.get(agent_id)
        if profile is None:
            return
        profile.total_perturbations += 1
        profile.updated_at = _now()

    # ── Momentum Vectors ──────────────────────────────────────────

    def record_vector(
        self,
        agent_id: str,
        direction: str,
        magnitude: float,
        velocity: float = 0.0,
        acceleration: float = 0.0,
        curvature: float = 0.0,
        mass: float = 1.0,
    ) -> MomentumVector:
        """Record a momentum vector for an agent and return it.

        ``direction`` is a human-readable label for the reasoning
        direction. ``magnitude`` in [0, 1] is clamped to that range.
        ``velocity`` is the per-step change in magnitude. ``acceleration``
        is the rate of change of velocity. ``curvature`` is the change in
        direction (turning rate). ``mass`` is the accumulated inference
        weight, defaulting to 1.0. Raises ``RuntimeError`` if the vector
        registry is full.
        """
        with self._lock:
            if len(self._vectors) >= self.MAX_VECTORS:
                raise RuntimeError("vector registry is full")
            vector = MomentumVector(
                agent_id=agent_id,
                direction=str(direction),
                magnitude=_clamp(magnitude, 0.0, 1.0),
                velocity=float(velocity),
                acceleration=float(acceleration),
                curvature=float(curvature),
                mass=float(mass),
                computed_at=_now(),
            )
            self._vectors[vector.vector_id] = vector
            self._stats["total_vectors"] += 1
            self._stats["momentum_sum"] += vector.magnitude
            self._update_profile_on_vector(agent_id, vector)
            return vector

    def get_vector(self, vector_id: str) -> Optional[MomentumVector]:
        """Retrieve a vector by id, or ``None`` if absent."""
        with self._lock:
            return self._vectors.get(vector_id)

    def list_vectors(
        self,
        agent_id: Optional[str] = None,
        regime: Optional[Any] = None,
    ) -> List[MomentumVector]:
        """Return vectors, optionally filtered by agent and regime.

        ``agent_id`` filters to vectors recorded for that agent.
        ``regime`` accepts a ``MomentumRegime`` member or its value/name
        string; because vectors do not store a regime directly, the
        regime is computed from each vector's magnitude, velocity, and
        curvature via ``_compute_regime`` and matched against the
        requested value. The returned list is a snapshot copy; mutating
        it does not affect the engine.
        """
        with self._lock:
            vectors = list(self._vectors.values())
        if agent_id is not None:
            vectors = [v for v in vectors if v.agent_id == agent_id]
        if regime is not None:
            member = _resolve_enum(MomentumRegime, regime)
            vectors = [
                v for v in vectors
                if self._compute_regime(v.magnitude, v.velocity, v.curvature) == member
            ]
        return vectors

    # ── Trajectory Points ─────────────────────────────────────────

    def record_trajectory_point(
        self,
        agent_id: str,
        step: int,
        position: Dict[str, float],
        momentum: Optional[MomentumVector] = None,
        progress: ProgressSignal = ProgressSignal.FORWARD,
        reward: float = 0.0,
    ) -> TrajectoryPoint:
        """Record a trajectory point for an agent and return it.

        The point is appended to ``_trajectory_history[agent_id]`` so the
        agent's reasoning path can be replayed in order. ``position`` is
        a sparse coordinate map copied so external mutation does not
        affect the stored record. ``momentum`` may be a previously
        recorded ``MomentumVector`` or ``None``. ``progress`` classifies
        the step's directional quality. ``reward`` is the scalar payoff
        observed at this point. Raises ``RuntimeError`` if the point
        registry is full.
        """
        with self._lock:
            if len(self._points) >= self.MAX_POINTS:
                raise RuntimeError("point registry is full")
            point = TrajectoryPoint(
                agent_id=agent_id,
                step=int(step),
                position={str(k): float(v) for k, v in (position or {}).items()},
                momentum=momentum,
                progress=_resolve_enum(ProgressSignal, progress),
                reward=float(reward),
                recorded_at=_now(),
            )
            self._points[point.point_id] = point
            history = self._trajectory_history.setdefault(agent_id, [])
            history.append(point)
            # Bound the per-agent history to avoid unbounded growth.
            if len(history) > self.MAX_TRAJECTORY_HISTORY:
                del history[: len(history) - self.MAX_TRAJECTORY_HISTORY]
            self._stats["total_points"] += 1
            return point

    def get_trajectory_point(self, point_id: str) -> Optional[TrajectoryPoint]:
        """Retrieve a trajectory point by id, or ``None`` if absent."""
        with self._lock:
            return self._points.get(point_id)

    def list_trajectory_points(self, agent_id: Optional[str] = None) -> List[TrajectoryPoint]:
        """Return trajectory points, optionally filtered by agent.

        When ``agent_id`` is ``None`` all points are returned in insertion
        order. Otherwise only points belonging to that agent are returned,
        preserving their trajectory order. The returned list is a snapshot
        copy; mutating it does not affect the engine.
        """
        with self._lock:
            if agent_id is None:
                return list(self._points.values())
            return list(self._trajectory_history.get(agent_id, []))

    # ── Stuck-State Detection ─────────────────────────────────────

    def detect_stuck_state(
        self,
        agent_id: str,
        trajectory_id: str,
        momentum_magnitude: float,
        progress_rate: float,
        curvature: float,
    ) -> StuckStateDetection:
        """Diagnose whether a trajectory is stuck and return the detection.

        The regime is computed by ``_compute_regime`` with
        ``progress_rate`` serving as the velocity signal (the rate at
        which the agent is covering useful ground). Confidence and
        suggested perturbations are derived from the resulting regime.
        The detection is stored and reflected in the agent's profile and
        the engine stats.
        """
        with self._lock:
            momentum = _clamp(momentum_magnitude, 0.0, 1.0)
            progress = _clamp(progress_rate, 0.0, 1.0)
            curv = float(curvature)
            regime = self._compute_regime(momentum, progress, curv)
            confidence, perturbations = self._classification_for_regime(
                regime, momentum, progress, curv
            )
            detection = StuckStateDetection(
                agent_id=agent_id,
                trajectory_id=str(trajectory_id),
                momentum_magnitude=momentum,
                progress_rate=progress,
                curvature=curv,
                regime=regime,
                detected_at=_now(),
                confidence=confidence,
                suggested_perturbations=list(perturbations),
            )
            self._detections[detection.detection_id] = detection
            self._stats["total_stuck_detections"] += 1
            self._update_profile_on_detection(agent_id, detection)
            return detection

    def get_detection(self, detection_id: str) -> Optional[StuckStateDetection]:
        """Retrieve a stuck-state detection by id, or ``None`` if absent."""
        with self._lock:
            return self._detections.get(detection_id)

    def list_detections(
        self,
        agent_id: Optional[str] = None,
        regime: Optional[Any] = None,
    ) -> List[StuckStateDetection]:
        """Return detections, optionally filtered by agent and regime.

        ``agent_id`` filters to detections for that agent. ``regime``
        accepts a ``MomentumRegime`` member or its value/name string and
        filters by the diagnosed regime. The returned list is a snapshot
        copy; mutating it does not affect the engine.
        """
        with self._lock:
            detections = list(self._detections.values())
        if agent_id is not None:
            detections = [d for d in detections if d.agent_id == agent_id]
        if regime is not None:
            member = _resolve_enum(MomentumRegime, regime)
            detections = [d for d in detections if d.regime == member]
        return detections

    # ── Perturbations ─────────────────────────────────────────────

    def apply_perturbation(
        self,
        agent_id: str,
        perturbation_type: Any,
        target_trajectory: str,
        intensity: float = 0.5,
        expected_impact: float = 0.3,
    ) -> PerturbationEvent:
        """Apply a perturbation to a trajectory and return the event record.

        ``perturbation_type`` accepts a ``PerturbationType`` member or its
        value/name string. ``target_trajectory`` identifies the trajectory
        to redirect. ``intensity`` in [0, 1] is clamped to that range and
        represents the strength of the applied impulse.
        ``expected_impact`` is the anticipated magnitude of effect,
        recorded at application time so the actual effect can later be
        compared. Raises ``RuntimeError`` if the perturbation registry is
        full.
        """
        with self._lock:
            if len(self._perturbations) >= self.MAX_PERTURBATIONS:
                raise RuntimeError("perturbation registry is full")
            event = PerturbationEvent(
                agent_id=agent_id,
                perturbation_type=_resolve_enum(PerturbationType, perturbation_type),
                target_trajectory=str(target_trajectory),
                intensity=_clamp(intensity, 0.0, 1.0),
                expected_impact=float(expected_impact),
                applied_at=_now(),
                outcome="applied",
            )
            self._perturbations[event.event_id] = event
            self._stats["total_perturbations"] += 1
            self._update_profile_on_perturbation(agent_id)
            return event

    def get_perturbation(self, event_id: str) -> Optional[PerturbationEvent]:
        """Retrieve a perturbation event by id, or ``None`` if absent."""
        with self._lock:
            return self._perturbations.get(event_id)

    def list_perturbations(
        self,
        agent_id: Optional[str] = None,
        perturbation_type: Optional[Any] = None,
    ) -> List[PerturbationEvent]:
        """Return perturbation events, optionally filtered.

        ``agent_id`` filters to events for that agent.
        ``perturbation_type`` accepts a ``PerturbationType`` member or its
        value/name string and filters by event type. The returned list is
        a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            events = list(self._perturbations.values())
        if agent_id is not None:
            events = [e for e in events if e.agent_id == agent_id]
        if perturbation_type is not None:
            member = _resolve_enum(PerturbationType, perturbation_type)
            events = [e for e in events if e.perturbation_type == member]
        return events

    # ── Escape Velocity & Plans ───────────────────────────────────

    def compute_escape_velocity(self, current_momentum: float, well_depth: float) -> float:
        """Compute the impulse magnitude needed to escape a local minimum.

        Physics-inspired: ``escape_velocity = sqrt(2 * well_depth *
        current_momentum)``. Both ``well_depth`` (the depth of the local
        minimum the trajectory is trapped in) and ``current_momentum``
        (the inertia pinning it there) increase the energy required to
        break free. Inputs are clamped to be non-negative so the
        radicand cannot go negative and produce a ``NaN``.
        """
        momentum = max(0.0, float(current_momentum))
        depth = max(0.0, float(well_depth))
        return math.sqrt(2.0 * depth * momentum)

    def create_escape_plan(
        self,
        agent_id: str,
        trajectory_id: str,
        current_momentum: float,
        escape_velocity: float,
        strategy: Any,
        steps: Optional[List[str]] = None,
        estimated_steps: int = 3,
    ) -> EscapePlan:
        """Create an escape plan for a trapped trajectory and return it.

        ``current_momentum`` is the momentum the trajectory carries at
        plan creation. ``escape_velocity`` is the impulse magnitude
        computed by ``compute_escape_velocity``. ``strategy`` accepts an
        ``EscapeStrategy`` member or its value/name string. ``steps`` is
        an optional explicit action sequence; when ``None`` a default
        three-step sequence is selected from the strategy. ``estimated_steps``
        is the expected length of the escape, defaulting to 3. Raises
        ``RuntimeError`` if the escape registry is full.
        """
        with self._lock:
            if len(self._escapes) >= self.MAX_ESCAPES:
                raise RuntimeError("escape plan registry is full")
            member = _resolve_enum(EscapeStrategy, strategy)
            if steps is None:
                plan_steps = list(self._DEFAULT_ESCAPE_STEPS.get(member, []))
            else:
                plan_steps = [str(s) for s in steps]
            plan = EscapePlan(
                agent_id=agent_id,
                trajectory_id=str(trajectory_id),
                current_momentum=float(current_momentum),
                escape_velocity=float(escape_velocity),
                strategy=member,
                steps=plan_steps,
                estimated_steps=int(estimated_steps),
                created_at=_now(),
            )
            self._escapes[plan.plan_id] = plan
            self._stats["total_escapes"] += 1
            self._stats["escape_velocity_sum"] += plan.escape_velocity
            return plan

    def get_escape_plan(self, plan_id: str) -> Optional[EscapePlan]:
        """Retrieve an escape plan by id, or ``None`` if absent."""
        with self._lock:
            return self._escapes.get(plan_id)

    def list_escape_plans(
        self,
        agent_id: Optional[str] = None,
        strategy: Optional[Any] = None,
    ) -> List[EscapePlan]:
        """Return escape plans, optionally filtered by agent and strategy.

        ``agent_id`` filters to plans for that agent. ``strategy`` accepts
        an ``EscapeStrategy`` member or its value/name string and filters
        by the selected strategy. The returned list is a snapshot copy;
        mutating it does not affect the engine.
        """
        with self._lock:
            plans = list(self._escapes.values())
        if agent_id is not None:
            plans = [p for p in plans if p.agent_id == agent_id]
        if strategy is not None:
            member = _resolve_enum(EscapeStrategy, strategy)
            plans = [p for p in plans if p.strategy == member]
        return plans

    # ── Profiles ──────────────────────────────────────────────────

    def get_or_create_profile(self, agent_id: str) -> MomentumProfile:
        """Return the agent's momentum profile, creating it if absent.

        When a profile does not yet exist for the agent, a fresh one is
        computed from the agent's currently recorded vectors, detections,
        and perturbations: ``baseline_momentum`` is the first vector's
        magnitude, ``peak_momentum`` is the maximum, ``avg_curvature`` is
        the mean, ``regime_distribution`` and ``stuck_rate`` are tallied
        from detections, and the counters reflect the agent's totals. The
        profile is then stored so subsequent record calls can update it
        incrementally.
        """
        with self._lock:
            existing = self._profiles.get(agent_id)
            if existing is not None:
                return existing
            agent_vectors = [
                v for v in self._vectors.values() if v.agent_id == agent_id
            ]
            agent_detections = [
                d for d in self._detections.values() if d.agent_id == agent_id
            ]
            agent_perturbations = [
                e for e in self._perturbations.values() if e.agent_id == agent_id
            ]
            regime_dist: Dict[MomentumRegime, int] = {}
            for d in agent_detections:
                regime_dist[d.regime] = regime_dist.get(d.regime, 0) + 1
            baseline = agent_vectors[0].magnitude if agent_vectors else 0.0
            peak = max((v.magnitude for v in agent_vectors), default=0.0)
            avg_curv = (
                sum(v.curvature for v in agent_vectors) / len(agent_vectors)
                if agent_vectors else 0.0
            )
            total_detections = len(agent_detections)
            locked = sum(
                1 for d in agent_detections if d.regime == MomentumRegime.LOCKED
            )
            stuck_rate = (locked / total_detections) if total_detections > 0 else 0.0
            profile = MomentumProfile(
                agent_id=agent_id,
                baseline_momentum=baseline,
                peak_momentum=peak,
                avg_curvature=avg_curv,
                regime_distribution=regime_dist,
                total_vectors=len(agent_vectors),
                total_perturbations=len(agent_perturbations),
                stuck_rate=stuck_rate,
                updated_at=_now(),
            )
            self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> MomentumProfile:
        """Update fields on an agent's momentum profile and return it.

        The profile is fetched (or created) first, then each keyword in
        ``kwargs`` is applied to the matching attribute. ``regime_distribution``
        may be supplied as a dict keyed by ``MomentumRegime`` members or
        their value/name strings; keys are normalized to enum members.
        Unknown keys are ignored so callers can pass through generic
        update payloads safely.
        """
        with self._lock:
            profile = self.get_or_create_profile(agent_id)
            for key, value in kwargs.items():
                if key == "regime_distribution" and isinstance(value, dict):
                    normalized: Dict[MomentumRegime, int] = {}
                    for k, v in value.items():
                        member = _resolve_enum(MomentumRegime, k)
                        normalized[member] = int(v)
                    profile.regime_distribution = normalized
                elif hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = _now()
            return profile

    def list_profiles(self) -> List[MomentumProfile]:
        """Return all stored momentum profiles as a snapshot list."""
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> MomentumStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counter dict maintained by the
        record methods. ``regime_distribution`` is tallied from stored
        detections and ``progress_distribution`` from stored trajectory
        points. ``avg_momentum`` is the mean vector magnitude and
        ``avg_escape_velocity`` is the mean escape velocity across plans.
        Both distribution dicts are keyed by enum members so callers can
        serialize them via ``MomentumStats.to_dict``.
        """
        with self._lock:
            s = self._stats
            total_vectors = int(s["total_vectors"])
            total_points = int(s["total_points"])
            total_stuck = int(s["total_stuck_detections"])
            total_perturb = int(s["total_perturbations"])
            total_escapes = int(s["total_escapes"])
            regime_dist: Dict[MomentumRegime, int] = {}
            for d in self._detections.values():
                regime_dist[d.regime] = regime_dist.get(d.regime, 0) + 1
            progress_dist: Dict[ProgressSignal, int] = {}
            for p in self._points.values():
                progress_dist[p.progress] = progress_dist.get(p.progress, 0) + 1
            avg_momentum = (
                s["momentum_sum"] / total_vectors if total_vectors > 0 else 0.0
            )
            avg_escape = (
                s["escape_velocity_sum"] / total_escapes if total_escapes > 0 else 0.0
            )
            return MomentumStats(
                total_vectors=total_vectors,
                total_points=total_points,
                total_stuck_detections=total_stuck,
                total_perturbations=total_perturb,
                total_escapes=total_escapes,
                regime_distribution=regime_dist,
                progress_distribution=progress_dist,
                avg_momentum=avg_momentum,
                avg_escape_velocity=avg_escape,
            )

    # ── Maintenance ───────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests."""
        with self._lock:
            self._vectors.clear()
            self._points.clear()
            self._detections.clear()
            self._perturbations.clear()
            self._escapes.clear()
            self._profiles.clear()
            self._trajectory_history.clear()
            self._stats = self._init_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_momentum_engine() -> AgentCognitiveMomentum:
    """Get or create the singleton ``AgentCognitiveMomentum`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveMomentum()
        return _engine


def reset_momentum_engine() -> None:
    """Reset the singleton ``AgentCognitiveMomentum`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_momentum_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
