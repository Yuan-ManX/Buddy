from __future__ import annotations

"""Agent Cognitive Prime — computational models of priming effects on cognition.

This module models semantic, associative, and affective priming effects on
perception, reasoning, and decision-making. It is intentionally dependency-free
so it can run in any Buddy runtime without extra packages.

Priming is the phenomenon whereby exposure to one stimulus influences the
response to a subsequent stimulus, often without conscious awareness. The
engine captures this phenomenon with a small set of primitives:

  - PrimeContext: the working context (an agent plus a set of active concepts)
    within which primes are activated and measured.
  - PrimeActivation: a concrete priming stimulus applied to a concept with a
    given type, strength, and spreading mode.
  - PrimeEffect: the measured influence of an activation on a target concept,
    expressed as a signed magnitude and a confidence score.
  - PrimeTarget: a concept that can receive activation, carrying the set of
    concepts associated with it for spreading activation.
  - PrimeSession: a bounded episode that groups activations and effects under
    a single goal.
  - PrimeStats: aggregate counters describing the state of the whole engine.

Core capabilities:
  - Context registration with active concepts that seed the association graph.
  - Prime activation across six types (semantic, associative, affective, goal,
    perceptual, conceptual) and four strengths.
  - Spreading activation that propagates decayed activation to associated
    concepts under four modes (spreading, focused, diffuse, cascade).
  - Effect measurement with signed magnitudes and confidence scoring.
  - Interference detection between two activations (competitive, retroactive,
    proactive) based on target overlap and temporal order.
  - Session grouping and activation decay with configurable decay factors.
  - Thread safety: all public mutation methods are guarded by a single lock.

Architecture:
    AgentCognitivePrime (singleton)
    ├── PrimeTarget      (a concept and its associated concepts)
    ├── PrimeActivation  (a priming stimulus applied to a concept)
    ├── PrimeEffect      (the measured influence on a target concept)
    ├── PrimeContext     (the working context for an agent)
    ├── PrimeSession     (a bounded episode of activations and effects)
    └── PrimeStats       (aggregate counters across the whole engine)
"""

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

class PrimeType(str, Enum):
    """The kind of relationship between a prime and its target concept.

    The taxonomy separates meaning-based priming (semantic, conceptual) from
    co-occurrence-based priming (associative) and from priming driven by
    internal states or goals (affective, goal, perceptual).
    """

    SEMANTIC = "semantic"          # meaning-based relatedness
    ASSOCIATIVE = "associative"    # learned co-occurrence links
    AFFECTIVE = "affective"        # emotion-driven valence transfer
    GOAL = "goal"                  # goal-directed attentional bias
    PERCEPTUAL = "perceptual"      # feature-level perceptual overlap
    CONCEPTUAL = "conceptual"      # category-level relatedness


class PrimeStrength(str, Enum):
    """How strongly a prime is applied to its target concept.

    Strength maps to a baseline activation level in [0, 1]. SUBTLE primes are
    near the threshold of awareness; OVERWHELMING primes dominate downstream
    processing.
    """

    SUBTLE = "subtle"
    MODERATE = "moderate"
    STRONG = "strong"
    OVERWHELMING = "overwhelming"


class ActivationMode(str, Enum):
    """How activation spreads from a prime to associated concepts.

    The mode controls the fan-out and decay profile of spreading activation.
    FOCUSED spreads narrowly with slow decay; DIFFUSE spreads widely with fast
    decay; CASCADE chains across hops; SPREADING is the balanced default.
    """

    SPREADING = "spreading"
    FOCUSED = "focused"
    DIFFUSE = "diffuse"
    CASCADE = "cascade"


class InterferenceType(str, Enum):
    """The kind of interference between two competing activations.

    NONE means the activations do not meaningfully compete. COMPETITIVE means
    they target overlapping concepts at the same time. RETROACTIVE means a
    newer activation interferes with retrieval of an older one. PROACTIVE
    means an older activation interferes with encoding of a newer one.
    """

    NONE = "none"
    COMPETITIVE = "competitive"
    RETROACTIVE = "retroactive"
    PROACTIVE = "proactive"


class EffectDirection(str, Enum):
    """The sign of a priming effect on a target concept.

    POSITIVE effects facilitate processing of the target; NEGATIVE effects
    inhibit it; NEUTRAL effects are present but do not bias the target in
    either direction.
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ═══════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PrimeTarget:
    """A concept that can receive priming activation.

    ``associated_concepts`` lists the concepts that are linked to this target
    and therefore eligible to receive spreading activation. ``activation_level``
    is the current accumulated activation in [0, 1].
    """

    target_id: str
    concept: str
    activation_level: float = 0.0
    associated_concepts: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "concept": self.concept,
            "activation_level": self.activation_level,
            "associated_concepts": list(self.associated_concepts),
            "created_at": self.created_at,
        }


@dataclass
class PrimeActivation:
    """A concrete priming stimulus applied to a concept.

    The activation carries its type, strength, and spreading mode plus a
    scalar ``activation_level`` in [0, 1] that decays over time. ``decayed``
    is set to True once the activation level falls below the removal
    threshold.
    """

    activation_id: str
    context_id: str
    prime_concept: str
    prime_type: PrimeType
    strength: PrimeStrength
    activation_level: float
    mode: ActivationMode
    description: str = ""
    created_at: str = ""
    decayed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activation_id": self.activation_id,
            "context_id": self.context_id,
            "prime_concept": self.prime_concept,
            "prime_type": self.prime_type.value,
            "strength": self.strength.value,
            "activation_level": self.activation_level,
            "mode": self.mode.value,
            "description": self.description,
            "created_at": self.created_at,
            "decayed": self.decayed,
        }


@dataclass
class PrimeEffect:
    """The measured influence of an activation on a target concept.

    ``magnitude`` is a signed value in [-1, 1] whose sign comes from
    ``direction``. ``confidence`` in [0, 1] reflects how reliably the
    activation is expected to produce the measured effect.
    """

    effect_id: str
    activation_id: str
    target_concept: str
    direction: EffectDirection
    magnitude: float
    confidence: float
    measured_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "activation_id": self.activation_id,
            "target_concept": self.target_concept,
            "direction": self.direction.value,
            "magnitude": self.magnitude,
            "confidence": self.confidence,
            "measured_at": self.measured_at,
        }


@dataclass
class PrimeContext:
    """The working context within which primes are activated.

    A context binds an agent to a set of ``active_concepts`` that seed the
    association graph used by spreading activation. ``activation_ids`` lists
    the activations that have been issued under this context, in insertion
    order.
    """

    context_id: str
    agent_id: str
    description: str = ""
    active_concepts: List[str] = field(default_factory=list)
    activation_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "active_concepts": list(self.active_concepts),
            "activation_ids": list(self.activation_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PrimeSession:
    """A bounded episode that groups activations and effects under a goal.

    Sessions let callers collect a contiguous run of priming activity under a
    single goal and close it with a ``completed_at`` timestamp when finished.
    """

    session_id: str
    context_id: str
    goal: str = ""
    description: str = ""
    activation_ids: List[str] = field(default_factory=list)
    effect_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "context_id": self.context_id,
            "goal": self.goal,
            "description": self.description,
            "activation_ids": list(self.activation_ids),
            "effect_ids": list(self.effect_ids),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class PrimeStats:
    """Aggregate counters describing the state of the whole engine.

    ``activations_by_type`` counts every activation by its PrimeType.
    ``effects_by_direction`` counts every effect by its EffectDirection.
    Both dicts are keyed by the enum value (string) for easy serialization.
    """

    total_contexts: int = 0
    total_activations: int = 0
    active_activations: int = 0
    total_effects: int = 0
    total_sessions: int = 0
    activations_by_type: Dict[str, int] = field(default_factory=dict)
    effects_by_direction: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_contexts": self.total_contexts,
            "total_activations": self.total_activations,
            "active_activations": self.active_activations,
            "total_effects": self.total_effects,
            "total_sessions": self.total_sessions,
            "activations_by_type": dict(self.activations_by_type),
            "effects_by_direction": dict(self.effects_by_direction),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

# Baseline activation level contributed by each prime strength. Strength is
# the primary driver of the initial activation_level before decay and mode
# adjustments are applied.
_STRENGTH_LEVEL: Dict[PrimeStrength, float] = {
    PrimeStrength.SUBTLE: 0.25,
    PrimeStrength.MODERATE: 0.5,
    PrimeStrength.STRONG: 0.75,
    PrimeStrength.OVERWHELMING: 1.0,
}

# Multiplier applied to the fan-out and decay profile for each spreading
# mode. FOCUSED narrows the spread; DIFFUSE widens it; CASCADE and SPREADING
# sit in between with slightly different chaining behavior.
_MODE_SPREAD_FACTOR: Dict[ActivationMode, float] = {
    ActivationMode.SPREADING: 1.0,
    ActivationMode.FOCUSED: 0.6,
    ActivationMode.DIFFUSE: 1.4,
    ActivationMode.CASCADE: 1.2,
}

# Sign applied to the effect magnitude for each direction. POSITIVE effects
# produce positive magnitudes (facilitation); NEGATIVE effects produce
# negative magnitudes (inhibition); NEUTRAL effects zero out the magnitude.
_DIRECTION_SIGN: Dict[EffectDirection, float] = {
    EffectDirection.POSITIVE: 1.0,
    EffectDirection.NEGATIVE: -1.0,
    EffectDirection.NEUTRAL: 0.0,
}

# Activation level at or below which an activation is considered fully decayed
# and is removed from the active set. Tuned so that a SUBTLE prime (0.25)
# survives one moderate decay pass but not several.
_DECAY_REMOVAL_THRESHOLD = 0.05

# Default fan-out and decay used by spread_activation when callers omit them.
_DEFAULT_FAN_OUT = 3
_DEFAULT_DECAY = 0.5

# Confidence baseline for a measured effect before adjustment for activation
# level and direction. Effects measured from stronger activations are more
# confident; neutral effects are less confident because their sign is zero.
_EFFECT_CONFIDENCE_BASE = 0.5

# Concepts that are always excluded from spreading activation targets: the
# prime concept itself (self-spread would be a no-op) and the empty string
# (used as a sentinel for missing concept names).
_SPREAD_EXCLUDE = {"", }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitivePrime:
    """Singleton engine that models priming effects on agent cognition.

    The engine is thread-safe: every public method that reads or mutates
    state acquires ``self._lock``. Internal helpers prefixed with ``_`` do
    not acquire the lock and must only be called while holding it.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._contexts: Dict[str, PrimeContext] = {}
        self._activations: Dict[str, PrimeActivation] = {}
        self._effects: Dict[str, PrimeEffect] = {}
        self._targets: Dict[str, PrimeTarget] = {}
        self._sessions: Dict[str, PrimeSession] = {}
        # Wall-clock seconds at which each activation was created. Used to
        # determine temporal order for retroactive vs proactive interference
        # without parsing ISO timestamps.
        self._activation_ts: Dict[str, float] = {}

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

    def _normalize_prime_type(self, prime_type: Any) -> PrimeType:
        """Coerce a PrimeType, enum name, or value into a PrimeType.

        Accepts the enum directly, the enum member name (e.g. ``"SEMANTIC"``),
        or the enum value (e.g. ``"semantic"``). Falls back to SEMANTIC when
        the input cannot be recognized.
        """
        if isinstance(prime_type, PrimeType):
            return prime_type
        if isinstance(prime_type, str):
            upper = prime_type.upper()
            try:
                return PrimeType[upper]
            except KeyError:
                pass
            for member in PrimeType:
                if member.value == prime_type:
                    return member
        return PrimeType.SEMANTIC

    def _normalize_strength(self, strength: Any) -> PrimeStrength:
        """Coerce a strength (enum, name, or value) into a PrimeStrength."""
        if isinstance(strength, PrimeStrength):
            return strength
        if isinstance(strength, str):
            upper = strength.upper()
            try:
                return PrimeStrength[upper]
            except KeyError:
                pass
            for member in PrimeStrength:
                if member.value == strength:
                    return member
        return PrimeStrength.MODERATE

    def _normalize_mode(self, mode: Any) -> ActivationMode:
        """Coerce a mode (enum, name, or value) into an ActivationMode."""
        if isinstance(mode, ActivationMode):
            return mode
        if isinstance(mode, str):
            upper = mode.upper()
            try:
                return ActivationMode[upper]
            except KeyError:
                pass
            for member in ActivationMode:
                if member.value == mode:
                    return member
        return ActivationMode.SPREADING

    def _normalize_direction(self, direction: Any) -> EffectDirection:
        """Coerce a direction (enum, name, or value) into an EffectDirection."""
        if isinstance(direction, EffectDirection):
            return direction
        if isinstance(direction, str):
            upper = direction.upper()
            try:
                return EffectDirection[upper]
            except KeyError:
                pass
            for member in EffectDirection:
                if member.value == direction:
                    return member
        return EffectDirection.POSITIVE

    def _normalize_concepts(self, concepts: Any) -> List[str]:
        """Coerce an iterable of concepts into a clean list of strings.

        Drops empty strings and de-duplicates while preserving insertion
        order so the association graph stays stable across calls.
        """
        if not concepts:
            return []
        seen: Dict[str, None] = {}
        for concept in concepts:
            if not isinstance(concept, str):
                concept = str(concept)
            concept = concept.strip()
            if concept in _SPREAD_EXCLUDE:
                continue
            if concept not in seen:
                seen[concept] = None
        return list(seen.keys())

    def _target_key(self, context_id: str, concept: str) -> str:
        """Build the composite key used to store per-context targets."""
        return f"{context_id}::{concept}"

    def _ensure_target(
        self, context_id: str, concept: str, associated: List[str]
    ) -> PrimeTarget:
        """Get or create the PrimeTarget for a concept within a context.

        Associated concepts supplied here are merged into the target's
        existing associations so repeated activations accumulate links rather
        than overwriting them.
        """
        key = self._target_key(context_id, concept)
        target = self._targets.get(key)
        if target is None:
            target = PrimeTarget(
                target_id=self._new_id("target"),
                concept=concept,
                activation_level=0.0,
                associated_concepts=[],
                created_at=self._now(),
            )
            self._targets[key] = target
        # Merge associations without duplicating the concept itself.
        for linked in associated:
            if linked and linked != concept and linked not in target.associated_concepts:
                target.associated_concepts.append(linked)
        return target

    def _associated_for(self, context_id: str, concept: str) -> List[str]:
        """Return the concepts associated with ``concept`` in a context.

        Falls back to the context's active concepts (minus the concept itself)
        when no explicit target associations have been recorded yet, so that
        spreading activation always has somewhere to go on first use.
        """
        key = self._target_key(context_id, concept)
        target = self._targets.get(key)
        if target is not None and target.associated_concepts:
            return list(target.associated_concepts)
        context = self._contexts.get(context_id)
        if context is None:
            return []
        return [
            c for c in context.active_concepts if c and c != concept
        ]

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def register_context(
        self,
        agent_id: str,
        description: str = "",
        active_concepts: Optional[List[str]] = None,
    ) -> PrimeContext:
        """Register a new priming context for an agent.

        ``active_concepts`` seeds the association graph used by spreading
        activation. Returns the newly created PrimeContext.
        """
        with self._lock:
            concepts = self._normalize_concepts(active_concepts)
            context_id = self._new_id("ctx")
            now = self._now()
            context = PrimeContext(
                context_id=context_id,
                agent_id=agent_id,
                description=description,
                active_concepts=concepts,
                activation_ids=[],
                created_at=now,
                updated_at=now,
            )
            self._contexts[context_id] = context
            # Pre-seed targets for each active concept so that the very first
            # spreading activation has a populated association graph.
            for concept in concepts:
                others = [c for c in concepts if c != concept]
                self._ensure_target(context_id, concept, others)
            return context

    def get_context(self, context_id: str) -> Optional[PrimeContext]:
        """Return the context with the given id, or None if not found."""
        with self._lock:
            return self._contexts.get(context_id)

    def list_contexts(self, agent_id: Optional[str] = None) -> List[PrimeContext]:
        """List contexts, optionally filtered by agent id."""
        with self._lock:
            if agent_id is None:
                return list(self._contexts.values())
            return [
                ctx for ctx in self._contexts.values() if ctx.agent_id == agent_id
            ]

    # ------------------------------------------------------------------
    # Activation management
    # ------------------------------------------------------------------

    def activate_prime(
        self,
        context_id: str,
        prime_concept: str,
        prime_type: Any,
        strength: Any = PrimeStrength.MODERATE,
        description: str = "",
    ) -> PrimeActivation:
        """Activate a prime on ``prime_concept`` within a context.

        ``prime_type`` and ``strength`` accept the enum directly or its name
        or value as a string. Raises ValueError if the context does not exist.
        Returns the newly created PrimeActivation.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise ValueError(f"Unknown context_id: {context_id}")
            p_type = self._normalize_prime_type(prime_type)
            p_strength = self._normalize_strength(strength)
            base_level = _STRENGTH_LEVEL.get(p_strength, 0.5)
            activation = PrimeActivation(
                activation_id=self._new_id("act"),
                context_id=context_id,
                prime_concept=prime_concept,
                prime_type=p_type,
                strength=p_strength,
                activation_level=base_level,
                mode=ActivationMode.SPREADING,
                description=description,
                created_at=self._now(),
                decayed=False,
            )
            self._activations[activation.activation_id] = activation
            self._activation_ts[activation.activation_id] = time.time()
            context.activation_ids.append(activation.activation_id)
            context.updated_at = activation.created_at
            # Register the prime concept as a target and link it to the
            # context's active concepts so spreading activation can reach them.
            associated = [c for c in context.active_concepts if c != prime_concept]
            target = self._ensure_target(context_id, prime_concept, associated)
            # Accumulate activation onto the target concept as well, so that
            # repeated primes on the same concept build up over time.
            target.activation_level = self._clamp(
                target.activation_level + base_level
            )
            # Back-link: make each active concept associate back to the prime
            # concept, producing a bidirectional association graph.
            for linked in associated:
                self._ensure_target(context_id, linked, [prime_concept])
            return activation

    def get_activation(self, activation_id: str) -> Optional[PrimeActivation]:
        """Return the activation with the given id, or None if not found."""
        with self._lock:
            return self._activations.get(activation_id)

    def list_activations(
        self,
        context_id: Optional[str] = None,
        prime_type: Optional[Any] = None,
    ) -> List[PrimeActivation]:
        """List activations, optionally filtered by context and/or prime type."""
        with self._lock:
            items = list(self._activations.values())
            if context_id is not None:
                items = [a for a in items if a.context_id == context_id]
            if prime_type is not None:
                wanted = self._normalize_prime_type(prime_type)
                items = [a for a in items if a.prime_type == wanted]
            return items

    def spread_activation(
        self,
        activation_id: str,
        mode: Any = ActivationMode.SPREADING,
        fan_out: int = _DEFAULT_FAN_OUT,
        decay: float = _DEFAULT_DECAY,
    ) -> List[PrimeActivation]:
        """Spread activation from a source prime to associated concepts.

        Creates a new PrimeActivation for each associated concept (up to
        ``fan_out``), with activation levels decayed by ``decay`` relative to
        the source. The new activations inherit the source's prime type and
        the context's association graph. Returns the list of new activations;
        returns an empty list if the source is missing, fully decayed, or has
        no associated concepts to spread to.
        """
        with self._lock:
            source = self._activations.get(activation_id)
            if source is None or source.decayed:
                return []
            spread_mode = self._normalize_mode(mode)
            # Adjust fan-out by the mode factor so FOCUSED spreads to fewer
            # targets and DIFFUSE spreads to more.
            effective_fan = max(1, int(round(fan_out * _MODE_SPREAD_FACTOR.get(spread_mode, 1.0))))
            candidates = self._associated_for(source.context_id, source.prime_concept)
            if not candidates:
                return []
            # In CASCADE mode the most recently activated concepts spread
            # first; otherwise we preserve association order for stability.
            if spread_mode == ActivationMode.CASCADE:
                candidates = list(reversed(candidates))
            selected = candidates[:effective_fan]
            new_activations: List[PrimeActivation] = []
            source_level = source.activation_level
            for concept in selected:
                if not concept or concept == source.prime_concept:
                    continue
                child_level = self._clamp(source_level * decay)
                if child_level <= _DECAY_REMOVAL_THRESHOLD:
                    # Too weak to seed a meaningful child activation; skip
                    # rather than creating a near-dead record.
                    continue
                child = PrimeActivation(
                    activation_id=self._new_id("act"),
                    context_id=source.context_id,
                    prime_concept=concept,
                    prime_type=source.prime_type,
                    # Children are one step weaker than the source.
                    strength=(
                        PrimeStrength.SUBTLE
                        if child_level < 0.3
                        else PrimeStrength.MODERATE
                    ),
                    activation_level=child_level,
                    mode=spread_mode,
                    description=f"spread from {source.activation_id}",
                    created_at=self._now(),
                    decayed=False,
                )
                self._activations[child.activation_id] = child
                self._activation_ts[child.activation_id] = time.time()
                context = self._contexts.get(source.context_id)
                if context is not None:
                    context.activation_ids.append(child.activation_id)
                    context.updated_at = child.created_at
                # Propagate activation onto the child target so subsequent
                # spreads can chain further in CASCADE mode.
                child_target = self._ensure_target(
                    source.context_id, concept, [source.prime_concept]
                )
                child_target.activation_level = self._clamp(
                    child_target.activation_level + child_level
                )
                new_activations.append(child)
            return new_activations

    # ------------------------------------------------------------------
    # Effect measurement
    # ------------------------------------------------------------------

    def measure_effect(
        self,
        activation_id: str,
        target_concept: str,
        direction: Any = EffectDirection.POSITIVE,
    ) -> PrimeEffect:
        """Measure the effect of an activation on a target concept.

        The magnitude is the activation level scaled by the direction sign;
        the confidence blends the activation level with a baseline so weak
        primes produce low-confidence effects. Raises ValueError if the
        activation does not exist. Returns the newly created PrimeEffect.
        """
        with self._lock:
            activation = self._activations.get(activation_id)
            if activation is None:
                raise ValueError(f"Unknown activation_id: {activation_id}")
            effect_dir = self._normalize_direction(direction)
            sign = _DIRECTION_SIGN.get(effect_dir, 0.0)
            level = activation.activation_level
            magnitude = self._clamp(level * sign, low=-1.0, high=1.0)
            # Confidence grows with activation level; neutral effects are
            # less confident because their sign (and thus magnitude) is zero.
            confidence = self._clamp(
                _EFFECT_CONFIDENCE_BASE + (level * 0.4) - (0.1 if effect_dir == EffectDirection.NEUTRAL else 0.0)
            )
            effect = PrimeEffect(
                effect_id=self._new_id("fx"),
                activation_id=activation_id,
                target_concept=target_concept,
                direction=effect_dir,
                magnitude=magnitude,
                confidence=confidence,
                measured_at=self._now(),
            )
            self._effects[effect.effect_id] = effect
            # Record the effect against any open session for this context so
            # callers can collect a session's effects without manual bookkeeping.
            for session in self._sessions.values():
                if (
                    session.context_id == activation.context_id
                    and session.completed_at is None
                ):
                    session.effect_ids.append(effect.effect_id)
            return effect

    def get_effect(self, effect_id: str) -> Optional[PrimeEffect]:
        """Return the effect with the given id, or None if not found."""
        with self._lock:
            return self._effects.get(effect_id)

    def list_effects(self, activation_id: Optional[str] = None) -> List[PrimeEffect]:
        """List effects, optionally filtered by the activation that produced them."""
        with self._lock:
            if activation_id is None:
                return list(self._effects.values())
            return [e for e in self._effects.values() if e.activation_id == activation_id]

    # ------------------------------------------------------------------
    # Interference detection
    # ------------------------------------------------------------------

    def check_interference(
        self, activation_id: str, other_activation_id: str
    ) -> dict:
        """Detect interference between two activations.

        Compares the two activations' prime concepts and their associated
        concepts to decide whether they compete for the same target material.
        Temporal order (oldest vs newest) decides between retroactive and
        proactive interference when the activations overlap. Returns a dict
        with the interference type (as a string value) and a magnitude in
        [0, 1]. Returns NONE interference if either activation is missing.
        """
        with self._lock:
            a = self._activations.get(activation_id)
            b = self._activations.get(other_activation_id)
            if a is None or b is None:
                return {
                    "interference_type": InterferenceType.NONE.value,
                    "magnitude": 0.0,
                    "reason": "missing activation",
                }
            # Gather the concept sets each activation touches: its own prime
            # concept plus the concepts it would spread to.
            a_concepts = {a.prime_concept}
            a_concepts.update(self._associated_for(a.context_id, a.prime_concept))
            b_concepts = {b.prime_concept}
            b_concepts.update(self._associated_for(b.context_id, b.prime_concept))
            overlap = a_concepts & b_concepts
            overlap_count = len(overlap)
            if overlap_count == 0:
                return {
                    "interference_type": InterferenceType.NONE.value,
                    "magnitude": 0.0,
                    "reason": "no shared target concepts",
                    "overlap": [],
                }
            # Magnitude scales with how much the two sets overlap, weighted by
            # the combined activation levels so stronger primes interfere more.
            union = len(a_concepts | b_concepts) or 1
            overlap_ratio = overlap_count / union
            combined_level = (a.activation_level + b.activation_level) / 2.0
            magnitude = self._clamp(overlap_ratio * combined_level)
            # Decide the interference type from temporal order. The newer
            # activation interferes with the older one (retroactive) when it
            # arrives after it; the older one interferes with the newer one
            # (proactive) when it was encoded first. When they were issued
            # effectively simultaneously, treat it as competitive.
            a_ts = self._activation_ts.get(activation_id, 0.0)
            b_ts = self._activation_ts.get(other_activation_id, 0.0)
            if abs(a_ts - b_ts) < 1e-6:
                itype = InterferenceType.COMPETITIVE
                reason = "simultaneous overlap on target concepts"
            elif b_ts > a_ts:
                # b is newer: it interferes with retrieval of a.
                itype = InterferenceType.RETROACTIVE
                reason = "newer activation interferes with older retrieval"
            else:
                # a is newer: the older b interferes with encoding of a.
                itype = InterferenceType.PROACTIVE
                reason = "older activation interferes with newer encoding"
            return {
                "interference_type": itype.value,
                "magnitude": magnitude,
                "reason": reason,
                "overlap": sorted(overlap),
            }

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        context_id: str,
        goal: str = "",
        description: str = "",
    ) -> PrimeSession:
        """Create a new priming session bound to a context.

        Sessions collect activations and effects under a single goal. Returns
        the newly created PrimeSession. Raises ValueError if the context does
        not exist.
        """
        with self._lock:
            if context_id not in self._contexts:
                raise ValueError(f"Unknown context_id: {context_id}")
            now = self._now()
            session = PrimeSession(
                session_id=self._new_id("sess"),
                context_id=context_id,
                goal=goal,
                description=description,
                activation_ids=[],
                effect_ids=[],
                created_at=now,
                completed_at=None,
            )
            self._sessions[session.session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[PrimeSession]:
        """Return the session with the given id, or None if not found."""
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, context_id: Optional[str] = None) -> List[PrimeSession]:
        """List sessions, optionally filtered by context id."""
        with self._lock:
            if context_id is None:
                return list(self._sessions.values())
            return [s for s in self._sessions.values() if s.context_id == context_id]

    # ------------------------------------------------------------------
    # Decay and stats
    # ------------------------------------------------------------------

    def decay_activations(
        self, context_id: str, decay_factor: float = 0.3
    ) -> int:
        """Decay all activations in a context by ``decay_factor``.

        Each activation's activation_level is reduced by ``activation_level *
        decay_factor``. Activations whose level falls at or below the removal
        threshold are marked decayed. Returns the number of activations that
        were decayed or removed. Returns 0 if the context does not exist.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return 0
            affected = 0
            for activation_id in context.activation_ids:
                activation = self._activations.get(activation_id)
                if activation is None or activation.decayed:
                    continue
                reduction = activation.activation_level * decay_factor
                activation.activation_level = self._clamp(
                    activation.activation_level - reduction
                )
                affected += 1
                if activation.activation_level <= _DECAY_REMOVAL_THRESHOLD:
                    activation.decayed = True
                    activation.activation_level = 0.0
            context.updated_at = self._now()
            return affected

    def get_stats(self) -> PrimeStats:
        """Compute aggregate statistics over the whole engine."""
        with self._lock:
            total_contexts = len(self._contexts)
            total_activations = len(self._activations)
            active_activations = sum(
                1 for a in self._activations.values() if not a.decayed
            )
            total_effects = len(self._effects)
            total_sessions = len(self._sessions)
            by_type: Dict[str, int] = {}
            for activation in self._activations.values():
                key = activation.prime_type.value
                by_type[key] = by_type.get(key, 0) + 1
            by_direction: Dict[str, int] = {}
            for effect in self._effects.values():
                key = effect.direction.value
                by_direction[key] = by_direction.get(key, 0) + 1
            return PrimeStats(
                total_contexts=total_contexts,
                total_activations=total_activations,
                active_activations=active_activations,
                total_effects=total_effects,
                total_sessions=total_sessions,
                activations_by_type=by_type,
                effects_by_direction=by_direction,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_prime_engine() -> AgentCognitivePrime:
    """Get or create the singleton cognitive prime engine."""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitivePrime()
        return _engine


def reset_prime_engine() -> None:
    """Reset the singleton cognitive prime engine.

    Mainly useful in tests where a fresh engine is needed between cases.
    """
    global _engine
    with _engine_lock:
        _engine = None
