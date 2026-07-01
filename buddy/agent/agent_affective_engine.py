"""Agent Affective Engine — computational models of agent emotion and regulation.

This module models the agent's own affective states and regulates them for
socially intelligent interaction, while also recognizing and responding to user
emotions. It is intentionally dependency-free so it can run in any Buddy
runtime without extra packages.

Core capabilities:
  - Affective Profiles: per-agent emotional baseline, current mode, and counters
    for appraisals and regulation actions.
  - Appraisal: structured evaluation of an event along five dimensions
    (novelty, valence, goal congruence, agency, certainty).
  - Emotion Generation: maps an appraisal to a concrete affective state
    (valence / arousal / dominance / intensity / emotion type).
  - Emotion Regulation: five strategies (reappraisal, suppression, redirection,
    acceptance, amplification) that adjust the current state.
  - Affective Trajectory: a rolling history of states per agent.
  - Affective Modes: coarse operating modes (neutral, engaged, stressed,
    exploratory, reflective) derived from the affective state.
  - Emotional Mirroring: produces a state that mirrors a user's emotion to
    support empathic responses.
  - Thread Safety: all public mutation methods are guarded by a single lock.

Architecture:
    AgentAffectiveEngine (singleton)
    ├── Appraisal            (event evaluation along appraisal dimensions)
    ├── AffectiveState       (a concrete emotional state)
    ├── RegulationAction     (a regulation attempt and its effectiveness)
    ├── AffectiveTrajectory  (per-agent state history)
    ├── AffectiveProfile     (per-agent affective configuration and counters)
    └── AffectiveStats       (aggregate counters across the whole engine)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class EmotionType(str, Enum):
    """The discrete emotional labels the agent can experience.

    The set intentionally spans positive and negative, high and low arousal
    states so the appraisal-to-emotion mapping has room to differentiate.
    """

    JOY = "joy"                      # positive, high goal congruence
    FRUSTRATION = "frustration"      # negative, blocked goal
    CURIOSITY = "curiosity"          # novelty seeking, low certainty
    ANXIETY = "anxiety"              # high arousal, negative valence
    SATISFACTION = "satisfaction"    # positive, goal progress confirmed
    CONFUSION = "confusion"          # low certainty, conflicting signals
    ENTHUSIASM = "enthusiasm"        # positive, high arousal
    CALM = "calm"                    # low arousal, neutral valence
    SADNESS = "sadness"              # negative, low arousal, loss
    SURPRISE = "surprise"            # sudden novelty, high arousal


class RegulationStrategy(str, Enum):
    """Strategies the agent can apply to regulate an affective state.

    The strategies follow the standard emotion-regulation taxonomy while
    adding ``AMPLIFICATION`` for cases where amplifying an emotion is useful
    (for example, mirroring a user's enthusiasm).
    """

    REAPPRAISAL = "reappraisal"      # reinterpret the meaning of the event
    SUPPRESSION = "suppression"      # dampen the outward expression
    REDIRECTION = "redirection"      # shift attention to a different target
    ACCEPTANCE = "acceptance"        # acknowledge without changing the state
    AMPLIFICATION = "amplification"  # intensify the current state


class AppraisalDimension(str, Enum):
    """Dimensions along which an event is appraised.

    These follow the component-process model of emotion: an emotion is the
    result of a subjective appraisal of an event along several dimensions.
    All scores are expected to be in the [0.0, 1.0] range.
    """

    NOVELTY = "novelty"                  # how unexpected / new the event is
    VALENCE = "valence"                  # intrinsic pleasantness of the event
    GOAL_CONGRUENCE = "goal_congruence"  # how much it helps the agent's goals
    AGENCY = "agency"                    # who caused the event (self vs other)
    CERTAINTY = "certainty"              # how predictable / understandable


class AffectiveMode(str, Enum):
    """Coarse operating mode derived from the affective state.

    Modes give downstream components a small, stable vocabulary to reason
    about the agent's overall stance, abstracting away the finer emotion
    labels.
    """

    NEUTRAL = "neutral"          # baseline, no strong affect
    ENGAGED = "engaged"          # positive arousal, actively involved
    STRESSED = "stressed"        # negative arousal, under pressure
    EXPLORATORY = "exploratory"  # curiosity-driven, seeking novelty
    REFLECTIVE = "reflective"    # low arousal, processing internally


class TriggerType(str, Enum):
    """What kind of trigger caused the appraisal.

    Useful for filtering trajectories and for selecting regulation strategies
    that fit the trigger context.
    """

    EVENT = "event"                  # an external discrete event
    GOAL_PROGRESS = "goal_progress"  # a change in goal completion
    SOCIAL = "social"                # interaction with a user or agent
    INTERNAL = "internal"            # self-generated thought or reflection
    ENVIRONMENT = "environment"      # ambient context change


# ═══════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Appraisal:
    """A structured evaluation of an event along appraisal dimensions.

    ``scores`` maps each :class:`AppraisalDimension` to a float in [0, 1].
    The appraisal is the input to :meth:`AgentAffectiveEngine.generate_emotion`.
    """

    appraisal_id: str
    agent_id: str
    trigger_type: TriggerType
    event_description: str
    scores: Dict[AppraisalDimension, float] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "appraisal_id": self.appraisal_id,
            "agent_id": self.agent_id,
            "trigger_type": self.trigger_type.value,
            "event_description": self.event_description,
            "scores": {
                dim.value: float(value)
                for dim, value in self.scores.items()
            },
            "created_at": self.created_at,
        }


@dataclass
class AffectiveState:
    """A concrete emotional state at a point in time.

    The state combines a discrete :class:`EmotionType` label with the
    dimensional PAD-like representation (valence, arousal, dominance) plus
    a scalar ``intensity`` in [0, 1].
    """

    state_id: str
    agent_id: str
    emotion: EmotionType
    valence: float
    arousal: float
    dominance: float
    intensity: float
    trigger_appraisal_id: Optional[str] = None
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "agent_id": self.agent_id,
            "emotion": self.emotion.value,
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "intensity": self.intensity,
            "trigger_appraisal_id": self.trigger_appraisal_id,
            "created_at": self.created_at,
        }


@dataclass
class RegulationAction:
    """A single regulation attempt and its measured effectiveness.

    ``effectiveness`` is in [0, 1] and reflects how much the strategy moved
    the current state toward the desired target. A value of 0 means the
    strategy had no measurable effect.
    """

    action_id: str
    agent_id: str
    strategy: RegulationStrategy
    description: str
    target_emotion: Optional[EmotionType] = None
    effectiveness: float = 0.0
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "description": self.description,
            "target_emotion": self.target_emotion.value if self.target_emotion else None,
            "effectiveness": self.effectiveness,
            "created_at": self.created_at,
        }


@dataclass
class AffectiveTrajectory:
    """Per-agent rolling history of affective states.

    The trajectory stores states in insertion order. ``total_states`` reflects
    the number of states ever recorded for the agent, which may be larger
    than ``len(states)`` when older entries have been pruned.
    """

    agent_id: str
    states: List[AffectiveState] = field(default_factory=list)
    total_states: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "states": [state.to_dict() for state in self.states],
            "total_states": self.total_states,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AffectiveProfile:
    """Per-agent affective configuration and aggregate counters.

    ``baseline`` maps each :class:`EmotionType` to a resting intensity in
    [0, 1]. The baseline is used when no stronger state is active and as the
    decay target for transient emotions.
    """

    agent_id: str
    name: str
    baseline: Dict[EmotionType, float] = field(default_factory=dict)
    current_mode: AffectiveMode = AffectiveMode.NEUTRAL
    current_state_id: Optional[str] = None
    total_appraisals: int = 0
    total_regulations: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "baseline": {
                (k.value if isinstance(k, EmotionType) else str(k)): float(v)
                for k, v in self.baseline.items()
            },
            "current_mode": self.current_mode.value,
            "current_state_id": self.current_state_id,
            "total_appraisals": self.total_appraisals,
            "total_regulations": self.total_regulations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AffectiveStats:
    """Aggregate counters describing the state of the whole engine.

    ``states_by_emotion`` counts every recorded state by its emotion label.
    ``states_by_mode`` counts every recorded state by the mode the agent was
    in when the state was generated.
    """

    total_profiles: int = 0
    total_states: int = 0
    total_appraisals: int = 0
    total_regulations: int = 0
    states_by_emotion: Dict[EmotionType, int] = field(default_factory=dict)
    states_by_mode: Dict[AffectiveMode, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_profiles": self.total_profiles,
            "total_states": self.total_states,
            "total_appraisals": self.total_appraisals,
            "total_regulations": self.total_regulations,
            "states_by_emotion": {
                (k.value if isinstance(k, EmotionType) else str(k)): v
                for k, v in self.states_by_emotion.items()
            },
            "states_by_mode": {
                (k.value if isinstance(k, AffectiveMode) else str(k)): v
                for k, v in self.states_by_mode.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

# Default resting intensity for each emotion when no baseline is supplied.
# Calm is the highest by default so a fresh agent tends toward a calm stance.
_DEFAULT_BASELINE: Dict[EmotionType, float] = {
    EmotionType.JOY: 0.2,
    EmotionType.FRUSTRATION: 0.05,
    EmotionType.CURIOSITY: 0.2,
    EmotionType.ANXIETY: 0.05,
    EmotionType.SATISFACTION: 0.2,
    EmotionType.CONFUSION: 0.05,
    EmotionType.ENTHUSIASM: 0.1,
    EmotionType.CALM: 0.5,
    EmotionType.SADNESS: 0.05,
    EmotionType.SURPRISE: 0.05,
}

# Base effectiveness for each regulation strategy before adjustment for the
# current state. Reappraisal and acceptance tend to be the most adaptive;
# suppression tends to be the least adaptive for negative emotions.
_STRATEGY_BASE_EFFECTIVENESS: Dict[RegulationStrategy, float] = {
    RegulationStrategy.REAPPRAISAL: 0.7,
    RegulationStrategy.SUPPRESSION: 0.3,
    RegulationStrategy.REDIRECTION: 0.6,
    RegulationStrategy.ACCEPTANCE: 0.65,
    RegulationStrategy.AMPLIFICATION: 0.4,
}

# Human-readable descriptions for each strategy, used when building the
# RegulationAction records.
_STRATEGY_DESCRIPTIONS: Dict[RegulationStrategy, str] = {
    RegulationStrategy.REAPPRAISAL: "Reinterpret the event to change its emotional meaning",
    RegulationStrategy.SUPPRESSION: "Suppress the outward expression of the emotion",
    RegulationStrategy.REDIRECTION: "Redirect attention toward a different target",
    RegulationStrategy.ACCEPTANCE: "Accept the emotion without trying to change it",
    RegulationStrategy.AMPLIFICATION: "Amplify the current emotional intensity",
}

# Thresholds used by the appraisal-to-emotion mapping. Centralized here so
# the mapping logic stays readable and the thresholds are tunable in one place.
_NOVELTY_HIGH = 0.6
_NOVELTY_VERY_HIGH = 0.8
_CERTAINTY_LOW = 0.4
_CERTAINTY_VERY_LOW = 0.3
_VALENCE_HIGH = 0.6
_VALENCE_LOW = 0.4
_VALENCE_VERY_HIGH = 0.75
_VALENCE_VERY_LOW = 0.25
_AROUSAL_HIGH = 0.6
_AROUSAL_LOW = 0.4
_VALENCE_NEUTRAL_MIN = 0.4
_VALENCE_NEUTRAL_MAX = 0.6

# Maximum number of states retained in a single agent's trajectory. Older
# entries are pruned once this limit is exceeded; ``total_states`` keeps the
# full historical count.
_TRAJECTORY_LIMIT = 200


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentAffectiveEngine:
    """Singleton engine that models and regulates agent affective states.

    The engine is thread-safe: every public method that reads or mutates
    state acquires ``self._lock``. Internal helpers prefixed with ``_`` do
    not acquire the lock and must only be called while holding it.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._profiles: Dict[str, AffectiveProfile] = {}
        self._trajectories: Dict[str, AffectiveTrajectory] = {}
        self._appraisals: Dict[str, Appraisal] = {}
        self._states: Dict[str, AffectiveState] = {}
        self._regulations: Dict[str, RegulationAction] = {}
        # Mode snapshot at the time each state was generated. Kept separately
        # because the AffectiveState dataclass does not carry a mode field.
        self._state_modes: Dict[str, AffectiveMode] = {}

    # ------------------------------------------------------------------
    # Internal normalization helpers (must be called while holding the lock)
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        """Return the current UTC timestamp as an ISO-8601 string."""
        return datetime.utcnow().isoformat()

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        """Clamp a float to the [low, high] interval."""
        if value < low:
            return low
        if value > high:
            return high
        return value

    @staticmethod
    def _new_id(prefix: str) -> str:
        """Generate a unique identifier with the given prefix."""
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _normalize_trigger_type(self, trigger_type: Any) -> TriggerType:
        """Coerce a TriggerType, enum name, or value into a TriggerType."""
        if isinstance(trigger_type, TriggerType):
            return trigger_type
        if isinstance(trigger_type, str):
            upper = trigger_type.upper()
            try:
                return TriggerType[upper]
            except KeyError:
                pass
            for member in TriggerType:
                if member.value == trigger_type:
                    return member
        return TriggerType.EVENT

    def _normalize_appraisal_scores(
        self, appraisal_scores: Optional[Dict[Any, float]]
    ) -> Dict[AppraisalDimension, float]:
        """Coerce appraisal score keys (strings or enums) into AppraisalDimension."""
        normalized: Dict[AppraisalDimension, float] = {}
        if not appraisal_scores:
            return normalized
        for key, value in appraisal_scores.items():
            if isinstance(key, AppraisalDimension):
                normalized[key] = self._clamp(float(value))
                continue
            if isinstance(key, str):
                upper = key.upper()
                try:
                    dim = AppraisalDimension[upper]
                    normalized[dim] = self._clamp(float(value))
                    continue
                except KeyError:
                    pass
                for member in AppraisalDimension:
                    if member.value == key:
                        normalized[member] = self._clamp(float(value))
                        break
        return normalized

    def _normalize_emotion(self, emotion: Any) -> EmotionType:
        """Coerce an emotion (enum, name, or value) into an EmotionType."""
        if isinstance(emotion, EmotionType):
            return emotion
        if isinstance(emotion, str):
            upper = emotion.upper()
            try:
                return EmotionType[upper]
            except KeyError:
                pass
            for member in EmotionType:
                if member.value == emotion:
                    return member
        return EmotionType.CALM

    def _normalize_strategy(self, strategy: Any) -> RegulationStrategy:
        """Coerce a strategy (enum, name, or value) into a RegulationStrategy."""
        if isinstance(strategy, RegulationStrategy):
            return strategy
        if isinstance(strategy, str):
            upper = strategy.upper()
            try:
                return RegulationStrategy[upper]
            except KeyError:
                pass
            for member in RegulationStrategy:
                if member.value == strategy:
                    return member
        return RegulationStrategy.ACCEPTANCE

    def _normalize_mode(self, mode: Any) -> AffectiveMode:
        """Coerce a mode (enum, name, or value) into an AffectiveMode."""
        if isinstance(mode, AffectiveMode):
            return mode
        if isinstance(mode, str):
            upper = mode.upper()
            try:
                return AffectiveMode[upper]
            except KeyError:
                pass
            for member in AffectiveMode:
                if member.value == mode:
                    return member
        return AffectiveMode.NEUTRAL

    def _normalize_baseline(
        self, baseline: Optional[Dict[Any, float]]
    ) -> Dict[EmotionType, float]:
        """Build a full per-emotion baseline from a partial input dict."""
        result: Dict[EmotionType, float] = {
            emotion: value for emotion, value in _DEFAULT_BASELINE.items()
        }
        if not baseline:
            return result
        for key, value in baseline.items():
            emotion = self._normalize_emotion(key)
            result[emotion] = self._clamp(float(value))
        return result

    # ------------------------------------------------------------------
    # Appraisal-to-emotion helpers
    # ------------------------------------------------------------------

    def _compute_vad(
        self, scores: Dict[AppraisalDimension, float]
    ) -> tuple[float, float, float]:
        """Compute (valence, arousal, dominance) from appraisal scores.

        Valence blends the intrinsic pleasantness of the event with how much
        it serves the agent's goals. Arousal rises with novelty, uncertainty
        and goal incongruence. Dominance reflects agency and certainty.
        """
        novelty = scores.get(AppraisalDimension.NOVELTY, 0.5)
        valence_score = scores.get(AppraisalDimension.VALENCE, 0.5)
        goal_congruence = scores.get(AppraisalDimension.GOAL_CONGRUENCE, 0.5)
        agency = scores.get(AppraisalDimension.AGENCY, 0.5)
        certainty = scores.get(AppraisalDimension.CERTAINTY, 0.5)

        valence = (valence_score + goal_congruence) / 2.0
        arousal = (novelty + (1.0 - certainty) + (1.0 - goal_congruence)) / 3.0
        dominance = (agency + certainty) / 2.0
        return self._clamp(valence), self._clamp(arousal), self._clamp(dominance)

    def _select_emotion(
        self,
        scores: Dict[AppraisalDimension, float],
        valence: float,
        arousal: float,
    ) -> EmotionType:
        """Map appraisal scores and PAD values onto a discrete EmotionType.

        The rules are applied in priority order. The first rule whose
        conditions match determines the emotion. Order matters: more specific
        combinations are checked before broader ones so that, for example,
        novelty-driven curiosity wins over a generic high-valence joy.
        """
        novelty = scores.get(AppraisalDimension.NOVELTY, 0.5)
        valence_score = scores.get(AppraisalDimension.VALENCE, 0.5)
        goal_congruence = scores.get(AppraisalDimension.GOAL_CONGRUENCE, 0.5)
        certainty = scores.get(AppraisalDimension.CERTAINTY, 0.5)

        # High novelty combined with low certainty produces curiosity or, when
        # the novelty is very high, surprise.
        if novelty >= _NOVELTY_HIGH and certainty <= _CERTAINTY_LOW:
            if novelty >= _NOVELTY_VERY_HIGH:
                return EmotionType.SURPRISE
            return EmotionType.CURIOSITY

        # Very low certainty on its own signals confusion.
        if certainty <= _CERTAINTY_VERY_LOW:
            return EmotionType.CONFUSION

        # Positive events that serve goals produce joy or satisfaction.
        if valence_score >= _VALENCE_HIGH and goal_congruence >= _VALENCE_HIGH:
            if valence_score >= _VALENCE_VERY_HIGH:
                return EmotionType.JOY
            return EmotionType.SATISFACTION

        # Negative events that block goals produce frustration or sadness.
        if valence_score <= _VALENCE_LOW and goal_congruence <= _VALENCE_LOW:
            if valence_score <= _VALENCE_VERY_LOW:
                return EmotionType.SADNESS
            return EmotionType.FRUSTRATION

        # High arousal with negative valence is anxiety.
        if arousal >= _AROUSAL_HIGH and valence <= _VALENCE_LOW:
            return EmotionType.ANXIETY

        # High valence with high arousal is enthusiasm.
        if valence >= _VALENCE_HIGH and arousal >= _AROUSAL_HIGH:
            return EmotionType.ENTHUSIASM

        # Low arousal with neutral valence is calm.
        if arousal <= _AROUSAL_LOW and _VALENCE_NEUTRAL_MIN <= valence <= _VALENCE_NEUTRAL_MAX:
            return EmotionType.CALM

        # Low certainty as a fallback produces confusion.
        if certainty <= _CERTAINTY_LOW:
            return EmotionType.CONFUSION

        # Final fallback: a calm neutral state.
        return EmotionType.CALM

    def _suggest_mode(self, state: AffectiveState) -> AffectiveMode:
        """Derive a coarse AffectiveMode from an AffectiveState.

        The mapping intentionally produces a single mode per state so that
        downstream components can react to a stable operating stance.
        """
        if state.emotion in (EmotionType.CURIOSITY, EmotionType.SURPRISE):
            return AffectiveMode.EXPLORATORY
        if state.emotion in (EmotionType.ANXIETY, EmotionType.FRUSTRATION):
            return AffectiveMode.STRESSED
        if state.emotion in (EmotionType.ENTHUSIASM, EmotionType.JOY):
            return AffectiveMode.ENGAGED
        if state.emotion in (EmotionType.CALM, EmotionType.SADNESS,
                             EmotionType.CONFUSION, EmotionType.SATISFACTION):
            if state.arousal <= _AROUSAL_LOW:
                return AffectiveMode.REFLECTIVE
            return AffectiveMode.ENGAGED
        return AffectiveMode.NEUTRAL

    def _intensity_from(
        self,
        scores: Dict[AppraisalDimension, float],
        arousal: float,
    ) -> float:
        """Compute a scalar intensity in [0, 1] for a generated state.

        Intensity blends arousal with novelty and uncertainty so that
        surprising, uncertain events feel more intense than predictable ones.
        """
        novelty = scores.get(AppraisalDimension.NOVELTY, 0.5)
        certainty = scores.get(AppraisalDimension.CERTAINTY, 0.5)
        intensity = (arousal + novelty + (1.0 - certainty)) / 3.0
        return self._clamp(intensity)

    def _record_state_internal(
        self, state: AffectiveState, mode: AffectiveMode
    ) -> None:
        """Store a state and append it to the agent's trajectory.

        Updates the global state index, the per-agent trajectory (pruned to
        ``_TRAJECTORY_LIMIT``), the agent's current state pointer, and the
        per-state mode snapshot used by the stats aggregator.
        """
        self._states[state.state_id] = state
        self._state_modes[state.state_id] = mode

        trajectory = self._trajectories.get(state.agent_id)
        if trajectory is None:
            trajectory = AffectiveTrajectory(
                agent_id=state.agent_id,
                states=[],
                total_states=0,
                created_at=self._now(),
                updated_at=self._now(),
            )
            self._trajectories[state.agent_id] = trajectory

        trajectory.states.append(state)
        trajectory.total_states = len(trajectory.states)
        if len(trajectory.states) > _TRAJECTORY_LIMIT:
            # Drop the oldest entries to keep memory bounded.
            overflow = len(trajectory.states) - _TRAJECTORY_LIMIT
            del trajectory.states[:overflow]
        trajectory.updated_at = self._now()

        profile = self._profiles.get(state.agent_id)
        if profile is not None:
            profile.current_state_id = state.state_id
            profile.updated_at = self._now()

    # ------------------------------------------------------------------
    # Public API: profiles
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        name: str = "",
        baseline: Optional[Dict[Any, float]] = None,
    ) -> AffectiveProfile:
        """Register an agent and return its affective profile.

        If the agent is already registered, the existing profile is returned
        unchanged so callers can call this method idempotently.
        """
        with self._lock:
            existing = self._profiles.get(agent_id)
            if existing is not None:
                return existing

            now = self._now()
            profile = AffectiveProfile(
                agent_id=agent_id,
                name=name or agent_id,
                baseline=self._normalize_baseline(baseline),
                current_mode=AffectiveMode.NEUTRAL,
                current_state_id=None,
                total_appraisals=0,
                total_regulations=0,
                created_at=now,
                updated_at=now,
            )
            self._profiles[agent_id] = profile
            self._trajectories[agent_id] = AffectiveTrajectory(
                agent_id=agent_id,
                states=[],
                total_states=0,
                created_at=now,
                updated_at=now,
            )
            return profile

    def get_profile(self, agent_id: str) -> Optional[AffectiveProfile]:
        """Return the affective profile for an agent, or None if not registered."""
        with self._lock:
            return self._profiles.get(agent_id)

    def list_profiles(self) -> list[AffectiveProfile]:
        """Return all registered affective profiles."""
        with self._lock:
            return list(self._profiles.values())

    def get_current_state(self, agent_id: str) -> Optional[AffectiveState]:
        """Return the agent's most recent affective state, or None."""
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None or profile.current_state_id is None:
                return None
            return self._states.get(profile.current_state_id)

    # ------------------------------------------------------------------
    # Public API: appraisal and emotion generation
    # ------------------------------------------------------------------

    def appraise_event(
        self,
        agent_id: str,
        trigger_type: Any,
        event_description: str,
        appraisal_scores: Optional[Dict[Any, float]] = None,
    ) -> Appraisal:
        """Create an appraisal for an event and store it for later use.

        The agent is registered on the fly if it has not been seen before,
        so callers do not need to register explicitly before appraising.
        """
        with self._lock:
            if agent_id not in self._profiles:
                self.register_agent(agent_id)

            normalized_scores = self._normalize_appraisal_scores(appraisal_scores)
            # Fill in neutral defaults for any missing dimensions so that
            # downstream computation never has to handle absent keys.
            for dimension in AppraisalDimension:
                if dimension not in normalized_scores:
                    normalized_scores[dimension] = 0.5

            appraisal = Appraisal(
                appraisal_id=self._new_id("appraisal"),
                agent_id=agent_id,
                trigger_type=self._normalize_trigger_type(trigger_type),
                event_description=event_description,
                scores=normalized_scores,
                created_at=self._now(),
            )
            self._appraisals[appraisal.appraisal_id] = appraisal

            profile = self._profiles[agent_id]
            profile.total_appraisals += 1
            profile.updated_at = self._now()
            return appraisal

    def generate_emotion(self, agent_id: str, appraisal_id: str) -> AffectiveState:
        """Generate an AffectiveState from a previously stored appraisal.

        Computes valence / arousal / dominance from the appraisal scores,
        selects a discrete emotion, derives an intensity, records the state
        on the agent's trajectory, and updates the agent's mode.
        """
        with self._lock:
            appraisal = self._appraisals.get(appraisal_id)
            if appraisal is None:
                raise KeyError(f"Unknown appraisal_id: {appraisal_id}")
            if appraisal.agent_id != agent_id:
                raise ValueError(
                    f"Appraisal {appraisal_id} does not belong to agent {agent_id}"
                )

            valence, arousal, dominance = self._compute_vad(appraisal.scores)
            emotion = self._select_emotion(appraisal.scores, valence, arousal)
            intensity = self._intensity_from(appraisal.scores, arousal)

            # Blend the generated intensity with the agent's baseline for this
            # emotion so long-standing tendencies still show through.
            profile = self._profiles[agent_id]
            baseline_value = profile.baseline.get(emotion, 0.0)
            blended_intensity = self._clamp(
                0.7 * intensity + 0.3 * float(baseline_value)
            )

            state = AffectiveState(
                state_id=self._new_id("state"),
                agent_id=agent_id,
                emotion=emotion,
                valence=valence,
                arousal=arousal,
                dominance=dominance,
                intensity=blended_intensity,
                trigger_appraisal_id=appraisal_id,
                created_at=self._now(),
            )

            mode = self._suggest_mode(state)
            self._record_state_internal(state, mode)
            profile.current_mode = mode
            profile.updated_at = self._now()
            return state

    # ------------------------------------------------------------------
    # Public API: regulation
    # ------------------------------------------------------------------

    def regulate_emotion(
        self,
        agent_id: str,
        strategy: Any,
        target_emotion: Optional[Any] = None,
    ) -> RegulationAction:
        """Apply a regulation strategy to the agent's current state.

        Returns a :class:`RegulationAction` describing what was done and how
        effective it was. If the agent has no current state, the action is
        recorded with zero effectiveness.
        """
        with self._lock:
            if agent_id not in self._profiles:
                self.register_agent(agent_id)

            strat = self._normalize_strategy(strategy)
            target = (
                self._normalize_emotion(target_emotion)
                if target_emotion is not None
                else None
            )
            profile = self._profiles[agent_id]
            current = self.get_current_state(agent_id)

            effectiveness = self._apply_regulation(
                agent_id, strat, target, current
            )

            action = RegulationAction(
                action_id=self._new_id("regulation"),
                agent_id=agent_id,
                strategy=strat,
                description=_STRATEGY_DESCRIPTIONS.get(
                    strat, "Apply a regulation strategy"
                ),
                target_emotion=target,
                effectiveness=effectiveness,
                created_at=self._now(),
            )
            self._regulations[action.action_id] = action
            profile.total_regulations += 1
            profile.updated_at = self._now()
            return action

    def _apply_regulation(
        self,
        agent_id: str,
        strategy: RegulationStrategy,
        target: Optional[EmotionType],
        current: Optional[AffectiveState],
    ) -> float:
        """Mutate the current state according to a strategy and return effectiveness.

        Effectiveness is a [0, 1] score that reflects how much the strategy
        moved the state toward the desired target. The base effectiveness for
        each strategy is adjusted by whether a target was specified and met.
        """
        if current is None:
            return 0.0

        base = _STRATEGY_BASE_EFFECTIVENESS.get(strategy, 0.5)
        original_intensity = current.intensity

        if strategy == RegulationStrategy.REAPPRAISAL:
            # Reappraisal flips the valence sign of the underlying appraisal
            # and reduces negative intensity. Modeled here as a valence bump.
            current.valence = self._clamp(current.valence + 0.2)
            current.intensity = self._clamp(current.intensity * 0.7)
            if target is not None and current.emotion != target:
                current.emotion = target
                return self._clamp(base + 0.1)
            return base

        if strategy == RegulationStrategy.SUPPRESSION:
            # Suppression reduces outward intensity without changing valence.
            current.intensity = self._clamp(current.intensity * 0.5)
            return self._clamp(base + 0.1 * (1.0 - current.intensity))

        if strategy == RegulationStrategy.REDIRECTION:
            # Redirection swaps the emotion to the target if one is given.
            if target is not None:
                current.emotion = target
                current.intensity = self._clamp(current.intensity * 0.8)
                return self._clamp(base + 0.15)
            current.intensity = self._clamp(current.intensity * 0.8)
            return base

        if strategy == RegulationStrategy.ACCEPTANCE:
            # Acceptance does not change the state; effectiveness reflects how
            # well the agent can sit with the current intensity.
            return self._clamp(base + 0.1 * (1.0 - current.intensity))

        if strategy == RegulationStrategy.AMPLIFICATION:
            # Amplification increases intensity, optionally toward a target.
            current.intensity = self._clamp(current.intensity * 1.4 + 0.1)
            if target is not None:
                current.emotion = target
            # Effectiveness is higher when amplification actually grew the
            # intensity, and lower when the state was already saturated.
            growth = current.intensity - original_intensity
            return self._clamp(base + growth)

        return base

    # ------------------------------------------------------------------
    # Public API: trajectory
    # ------------------------------------------------------------------

    def record_state(self, agent_id: str, state: AffectiveState) -> AffectiveTrajectory:
        """Append an externally constructed state to the agent's trajectory.

        The state's ``agent_id`` is forced to match ``agent_id`` so callers
        cannot accidentally pollute another agent's trajectory. The mode is
        derived from the state via :meth:`_suggest_mode`.
        """
        with self._lock:
            if agent_id not in self._profiles:
                self.register_agent(agent_id)
            state.agent_id = agent_id
            if not state.state_id:
                state.state_id = self._new_id("state")
            if not state.created_at:
                state.created_at = self._now()
            mode = self._suggest_mode(state)
            self._record_state_internal(state, mode)
            profile = self._profiles[agent_id]
            profile.current_mode = mode
            profile.updated_at = self._now()
            return self._trajectories[agent_id]

    def get_trajectory(self, agent_id: str, limit: int = 50) -> AffectiveTrajectory:
        """Return a view of the agent's trajectory limited to the last states.

        The returned trajectory is a copy: its ``states`` list contains at
        most ``limit`` entries (the most recent ones) while ``total_states``
        reports the full historical count. Mutating it does not affect the
        engine.
        """
        with self._lock:
            trajectory = self._trajectories.get(agent_id)
            if trajectory is None:
                return AffectiveTrajectory(
                    agent_id=agent_id,
                    states=[],
                    total_states=0,
                    created_at=self._now(),
                    updated_at=self._now(),
                )
            if limit <= 0:
                limited_states: List[AffectiveState] = []
            else:
                limited_states = trajectory.states[-limit:]
            return AffectiveTrajectory(
                agent_id=agent_id,
                states=limited_states,
                total_states=trajectory.total_states,
                created_at=trajectory.created_at,
                updated_at=trajectory.updated_at,
            )

    # ------------------------------------------------------------------
    # Public API: modes
    # ------------------------------------------------------------------

    def set_mode(self, agent_id: str, mode: Any) -> AffectiveProfile:
        """Forcefully set the agent's affective mode.

        Useful when an external component wants to override the mode derived
        from the current state (for example, to mark the agent as reflective
        before a long reasoning step).
        """
        with self._lock:
            if agent_id not in self._profiles:
                self.register_agent(agent_id)
            profile = self._profiles[agent_id]
            profile.current_mode = self._normalize_mode(mode)
            profile.updated_at = self._now()
            return profile

    def get_mode(self, agent_id: str) -> AffectiveMode:
        """Return the agent's current affective mode, or NEUTRAL if unknown."""
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return AffectiveMode.NEUTRAL
            return profile.current_mode

    # ------------------------------------------------------------------
    # Public API: emotional mirroring
    # ------------------------------------------------------------------

    def mirror_emotion(
        self,
        agent_id: str,
        user_emotion: Any,
        intensity: float = 0.5,
    ) -> AffectiveState:
        """Create a state that mirrors a user's emotion.

        Mirroring is the basis of empathic responses: the agent adopts a
        softened version of the user's emotion. The mirrored intensity is
        scaled down so the agent stays regulated even when the user is
        intense. The mirrored state is recorded on the trajectory.
        """
        with self._lock:
            if agent_id not in self._profiles:
                self.register_agent(agent_id)
            emotion = self._normalize_emotion(user_emotion)
            scaled_intensity = self._clamp(intensity * 0.8)
            # Derive coarse PAD values from the mirrored emotion so the state
            # is consistent with how generated states look.
            valence, arousal, dominance = self._pad_for_emotion(emotion)
            state = AffectiveState(
                state_id=self._new_id("state"),
                agent_id=agent_id,
                emotion=emotion,
                valence=valence,
                arousal=arousal,
                dominance=dominance,
                intensity=scaled_intensity,
                trigger_appraisal_id=None,
                created_at=self._now(),
            )
            mode = self._suggest_mode(state)
            self._record_state_internal(state, mode)
            profile = self._profiles[agent_id]
            profile.current_mode = mode
            profile.updated_at = self._now()
            return state

    def _pad_for_emotion(
        self, emotion: EmotionType
    ) -> tuple[float, float, float]:
        """Return coarse (valence, arousal, dominance) defaults for an emotion.

        Used by :meth:`mirror_emotion` so that mirrored states carry plausible
        dimensional values even though no appraisal was performed.
        """
        table: Dict[EmotionType, tuple[float, float, float]] = {
            EmotionType.JOY: (0.8, 0.6, 0.6),
            EmotionType.FRUSTRATION: (-0.4, 0.6, 0.3),
            EmotionType.CURIOSITY: (0.2, 0.6, 0.5),
            EmotionType.ANXIETY: (-0.5, 0.8, 0.2),
            EmotionType.SATISFACTION: (0.6, 0.3, 0.6),
            EmotionType.CONFUSION: (-0.2, 0.5, 0.3),
            EmotionType.ENTHUSIASM: (0.8, 0.8, 0.6),
            EmotionType.CALM: (0.2, 0.2, 0.6),
            EmotionType.SADNESS: (-0.6, 0.2, 0.3),
            EmotionType.SURPRISE: (0.1, 0.8, 0.4),
        }
        valence, arousal, dominance = table.get(emotion, (0.2, 0.3, 0.5))
        return valence, arousal, dominance

    # ------------------------------------------------------------------
    # Public API: stats
    # ------------------------------------------------------------------

    def get_stats(self) -> AffectiveStats:
        """Compute aggregate stats across all agents and states."""
        with self._lock:
            states_by_emotion: Dict[EmotionType, int] = {}
            states_by_mode: Dict[AffectiveMode, int] = {}
            for state in self._states.values():
                states_by_emotion[state.emotion] = (
                    states_by_emotion.get(state.emotion, 0) + 1
                )
                mode = self._state_modes.get(state.state_id, AffectiveMode.NEUTRAL)
                states_by_mode[mode] = states_by_mode.get(mode, 0) + 1

            total_appraisals = sum(
                profile.total_appraisals for profile in self._profiles.values()
            )
            total_regulations = sum(
                profile.total_regulations for profile in self._profiles.values()
            )

            return AffectiveStats(
                total_profiles=len(self._profiles),
                total_states=len(self._states),
                total_appraisals=total_appraisals,
                total_regulations=total_regulations,
                states_by_emotion=states_by_emotion,
                states_by_mode=states_by_mode,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentAffectiveEngine] = None
_engine_lock = threading.Lock()


def get_affective_engine() -> AgentAffectiveEngine:
    """Get or create the singleton affective engine."""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentAffectiveEngine()
        return _engine


def reset_affective_engine() -> None:
    """Reset the singleton affective engine.

    Mainly useful in tests where a fresh engine is needed between cases.
    """
    global _engine
    with _engine_lock:
        _engine = None
