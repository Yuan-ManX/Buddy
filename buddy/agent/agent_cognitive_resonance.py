from __future__ import annotations

# Agent Cognitive Resonance — detection and leverage of deep structural
# resonance between concepts and ideas, in situations where alignment
# produces amplification, insight, and emergent meaning.
#
# Resonance is the phenomenon where two structures, when aligned, produce
# an effect larger than the sum of their parts. In cognition this appears
# when two concepts share a deep pattern: a wave and a particle resonate
# structurally because both carry frequency and amplitude; a cause and an
# effect resonate causally because one produces the other; two events
# resonate temporally when their rhythms lock into phase. Where resonance
# appears, alignment amplifies: weak signals become strong, latent
# connections become visible, and clusters of mutually resonant concepts
# become natural units of insight.
#
# This engine models that process operationally. Each agent works within a
# ResonanceContext tied to a domain. Concepts are registered with attribute
# vectors (dicts of name to float). The engine detects resonance between
# pairs of concepts by computing the cosine similarity of their attribute
# vectors; the sign and magnitude of that similarity determine whether the
# resonance is constructive (reinforcing), destructive (canceling), or
# merely coupled (moving together without net gain). Each detection
# produces a ResonanceEvent carrying a ResonanceSignature that records the
# frequency, amplitude, and phase of the alignment.
#
# Resonance is not static: it amplifies over time. An AmplificationProfile
# tracks how strongly a given resonance amplifies its constituent concepts,
# moving through a lifecycle from DORMANT through BUILDING and PEAK to a
# DECAYING or DAMPED state. When many resonances accumulate, concepts can
# be grouped into ResonanceClusters: connected components linked by
# sufficiently strong resonance. A cluster carries a coherence score and
# an insight string synthesized from its members. The full web of
# resonances can be exported as a network of nodes and edges.
#
# Architecture:
#     AgentCognitiveResonance (singleton)
#     ├── ResonanceContext (a conceptual workspace for one agent)
#     │   ├── ResonanceSignature (the waveform of one alignment)
#     │   ├── ResonanceEvent (one detected resonance between two concepts)
#     │   ├── AmplificationProfile (how strongly a resonance amplifies)
#     │   └── ResonanceCluster (a connected component of resonant concepts)
#     └── ResonanceStats (aggregate engine statistics)

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ResonanceType(str, Enum):
    """The structural dimension along which two concepts resonate.

    Resonance is not a single phenomenon; it appears along distinct
    dimensions whose alignment produces different kinds of amplification.
    STRUCTURAL resonance means the concepts share an underlying form or
    organization. SEMANTIC resonance means their meanings overlap or
    reinforce each other. CAUSAL resonance means one produces or entails
    the other. TEMPORAL resonance means their patterns align in time.
    FUNCTIONAL resonance means they serve compatible roles. EMOTIONAL
    resonance means they carry convergent affective charge.
    """
    STRUCTURAL = "structural"    # shared underlying form
    SEMANTIC = "semantic"        # overlapping meaning
    CAUSAL = "causal"            # one produces the other
    TEMPORAL = "temporal"        # patterns align in time
    FUNCTIONAL = "functional"    # compatible roles
    EMOTIONAL = "emotional"      # convergent affective charge


class ResonanceMode(str, Enum):
    """How two resonating concepts interact when they align.

    CONSTRUCTIVE resonance means the concepts reinforce each other,
    amplifying their joint effect. DESTRUCTIVE resonance means they
    cancel, damping their joint effect. COUPLED resonance means they move
    in lockstep without net amplification or cancellation. HARMONIC
    resonance means they align at integer multiples of a shared
    frequency, producing a stable periodic relationship.
    """
    CONSTRUCTIVE = "constructive"  # reinforcement, net amplification
    DESTRUCTIVE = "destructive"    # cancellation, net damping
    COUPLED = "coupled"            # lockstep, no net change
    HARMONIC = "harmonic"          # integer-frequency alignment


class DetectionMethod(str, Enum):
    """The algorithm used to detect resonance between two concepts.

    Different methods expose different forms of alignment. CROSS_CORRELATION
    measures the dot-product alignment of attribute vectors. PATTERN_MATCHING
    looks for shared structural motifs. EIGENVALUE analyzes the spectrum of
    the relationship matrix. GRAPH_ALIGNMENT compares positions within a
    concept graph. STATISTICAL compares distributions of attributes. All
    methods collapse their result onto a single strength in [-1, 1].
    """
    CROSS_CORRELATION = "cross_correlation"  # dot-product alignment
    PATTERN_MATCHING = "pattern_matching"    # shared structural motifs
    EIGENVALUE = "eigenvalue"                # spectrum of relationship matrix
    GRAPH_ALIGNMENT = "graph_alignment"      # positions in concept graph
    STATISTICAL = "statistical"              # distribution comparison


class AmplificationStatus(str, Enum):
    """The lifecycle state of an amplification profile.

    Amplification is not instantaneous; it grows, peaks, and fades.
    DORMANT means the resonance has not yet begun to amplify. BUILDING
    means amplification is increasing as the resonance sustains. PEAK
    means amplification has reached its maximum for this resonance.
    DECAYING means amplification is fading as the resonance loses
    coherence. DAMPED means amplification has been suppressed, typically
    because the resonance is destructive.
    """
    DORMANT = "dormant"    # not yet amplifying
    BUILDING = "building"  # amplification increasing
    PEAK = "peak"          # maximum amplification reached
    DECAYING = "decaying"  # amplification fading
    DAMPED = "damped"      # amplification suppressed


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a context/event/cluster/etc."""
    return str(uuid.uuid4())[:8]


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"structural"``) and then against member names
    (e.g. ``"STRUCTURAL"``), so callers may pass either form. Raises
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


def _cosine_similarity(attrs_a: Dict[str, float], attrs_b: Dict[str, float]) -> float:
    """Compute the cosine similarity of two attribute vectors.

    The two attribute dicts are aligned on the union of their keys, with
    missing entries treated as zero. Cosine similarity ranges over [-1, 1]:
    values near 1 mean the vectors point in the same direction (constructive
    alignment), values near -1 mean they point oppositely (destructive
    alignment), and values near 0 mean they are orthogonal (no alignment).
    Returns 0.0 if either vector has zero magnitude or both are empty.
    """
    if not attrs_a or not attrs_b:
        return 0.0
    keys = set(attrs_a) | set(attrs_b)
    dot = 0.0
    for k in keys:
        dot += float(attrs_a.get(k, 0.0)) * float(attrs_b.get(k, 0.0))
    norm_a = sum(float(v) * float(v) for v in attrs_a.values()) ** 0.5
    norm_b = sum(float(v) * float(v) for v in attrs_b.values()) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    sim = dot / (norm_a * norm_b)
    # Clamp to [-1, 1] to guard against floating-point drift.
    if sim > 1.0:
        sim = 1.0
    elif sim < -1.0:
        sim = -1.0
    return sim


def _phase_for_mode(mode: ResonanceMode) -> float:
    """Return a normalized phase in [0, 1] for a resonance mode.

    The phase expresses where in its cycle the alignment sits.
    Constructive resonance is in-phase (0.0); coupled resonance is at
    quarter phase (0.25); destructive resonance is anti-phase (0.5);
    harmonic resonance sits at a stable third-cycle offset (0.75).
    """
    if mode == ResonanceMode.CONSTRUCTIVE:
        return 0.0
    if mode == ResonanceMode.COUPLED:
        return 0.25
    if mode == ResonanceMode.DESTRUCTIVE:
        return 0.5
    return 0.75


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ResonanceSignature:
    """The waveform signature of one alignment between two concepts.

    A resonance signature captures the alignment as a waveform:
    ``frequency`` (how rapidly the alignment oscillates, from the
    attribute overlap ratio), ``amplitude`` (the magnitude, from the
    resonance strength), and ``phase`` (where in its cycle the alignment
    sits, from the resonance mode). The ``method`` records which
    detection algorithm produced the signature.
    """
    signature_id: str = field(default_factory=_new_id)
    concept_a: str = ""
    concept_b: str = ""
    frequency: float = 0.0
    amplitude: float = 0.0
    phase: float = 0.0
    method: DetectionMethod = DetectionMethod.CROSS_CORRELATION
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this signature to a plain dict, expanding the enum."""
        return {
            "signature_id": self.signature_id,
            "concept_a": self.concept_a,
            "concept_b": self.concept_b,
            "frequency": self.frequency,
            "amplitude": self.amplitude,
            "phase": self.phase,
            "method": _enum_value(DetectionMethod, self.method),
            "created_at": self.created_at,
        }


@dataclass
class ResonanceEvent:
    """One detected resonance between two concepts.

    A resonance event records that ``concept_a`` and ``concept_b`` were
    found to resonate with ``strength`` in [-1, 1] along a given
    ``resonance_type``. The ``mode`` records whether the resonance is
    constructive, destructive, coupled, or harmonic. The optional
    ``signature`` carries the waveform of the alignment. ``cluster_id`` is
    set when the event is assigned to a ResonanceCluster; it remains
    ``None`` until clustering runs.
    """
    event_id: str = field(default_factory=_new_id)
    context_id: str = ""
    concept_a: str = ""
    concept_b: str = ""
    resonance_type: ResonanceType = ResonanceType.STRUCTURAL
    mode: ResonanceMode = ResonanceMode.COUPLED
    strength: float = 0.0
    signature: Optional[ResonanceSignature] = None
    detected_at: str = field(default_factory=_now)
    cluster_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict.

        The ``resonance_type`` and ``mode`` enums are expanded via
        ``.value``; the nested ``signature`` is serialized via its own
        ``to_dict`` when present.
        """
        return {
            "event_id": self.event_id,
            "context_id": self.context_id,
            "concept_a": self.concept_a,
            "concept_b": self.concept_b,
            "resonance_type": _enum_value(ResonanceType, self.resonance_type),
            "mode": _enum_value(ResonanceMode, self.mode),
            "strength": self.strength,
            "signature": self.signature.to_dict() if self.signature is not None else None,
            "detected_at": self.detected_at,
            "cluster_id": self.cluster_id,
        }


@dataclass
class AmplificationProfile:
    """How strongly a resonance amplifies its constituent concepts.

    Amplification is the dynamic consequence of resonance: a sustained
    resonance does not just exist, it amplifies. ``peak_amplification``
    is the maximum reached; ``current_level`` is the present level;
    ``decay_rate`` is the rate at which amplification fades when the
    resonance is not sustained. The ``status`` field tracks the
    lifecycle from DORMANT through BUILDING and PEAK to DECAYING or
    DAMPED.
    """
    profile_id: str = field(default_factory=_new_id)
    event_id: str = ""
    status: AmplificationStatus = AmplificationStatus.DORMANT
    peak_amplification: float = 0.0
    current_level: float = 0.0
    decay_rate: float = 0.1
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enum."""
        return {
            "profile_id": self.profile_id,
            "event_id": self.event_id,
            "status": _enum_value(AmplificationStatus, self.status),
            "peak_amplification": self.peak_amplification,
            "current_level": self.current_level,
            "decay_rate": self.decay_rate,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ResonanceCluster:
    """A connected component of mutually resonant concepts.

    When many resonances accumulate, concepts form a graph whose edges are
    resonances above a threshold. The connected components of that graph
    are clusters: groups of concepts that resonate with each other
    transitively. ``concepts`` lists the member concept names;
    ``event_ids`` lists the resonance events that link them;
    ``coherence`` is the average absolute strength of those events;
    ``insight`` is a synthesized description of what the cluster means,
    populated by ``generate_insight``.
    """
    cluster_id: str = field(default_factory=_new_id)
    context_id: str = ""
    concepts: List[str] = field(default_factory=list)
    event_ids: List[str] = field(default_factory=list)
    coherence: float = 0.0
    insight: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this cluster to a plain dict.

        The ``concepts`` and ``event_ids`` lists are copied so the
        serialized form is independent of the live cluster.
        """
        return {
            "cluster_id": self.cluster_id,
            "context_id": self.context_id,
            "concepts": list(self.concepts),
            "event_ids": list(self.event_ids),
            "coherence": self.coherence,
            "insight": self.insight,
            "created_at": self.created_at,
        }


@dataclass
class ResonanceContext:
    """A conceptual workspace for one agent in a domain.

    A context ties an ``agent_id`` to a ``domain`` and an optional
    ``description`` of what the agent is reasoning about. The context
    holds the agent's registered concepts (each a dict of attributes plus
    metadata) and references (by id) to the resonance events and clusters
    that have been derived from them. Mutating the context updates
    ``updated_at``.
    """
    context_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    domain: str = ""
    description: str = ""
    concepts: Dict[str, dict] = field(default_factory=dict)
    event_ids: List[str] = field(default_factory=list)
    cluster_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this context to a plain dict.

        The ``concepts`` dict is shallow-copied so the serialized form is
        independent of the live context; the ``event_ids`` and
        ``cluster_ids`` lists are copied as well.
        """
        return {
            "context_id": self.context_id,
            "agent_id": self.agent_id,
            "domain": self.domain,
            "description": self.description,
            "concepts": dict(self.concepts) if isinstance(self.concepts, dict) else self.concepts,
            "event_ids": list(self.event_ids),
            "cluster_ids": list(self.cluster_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ResonanceStats:
    """Aggregate statistics over the resonance engine's state.

    Counts of contexts, events, amplification profiles, and clusters;
    plus two breakdown dicts (``events_by_type`` and ``events_by_mode``)
    that tally events by their resonance type and mode. Breakdown keys
    are the enum ``.value`` strings so the stats serialize cleanly to
    JSON. ``avg_resonance_strength`` is the mean strength over all
    events (0.0 when no events exist).
    """
    total_contexts: int = 0
    total_events: int = 0
    total_amplifications: int = 0
    total_clusters: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_by_mode: Dict[str, int] = field(default_factory=dict)
    avg_resonance_strength: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict."""
        return {
            "total_contexts": self.total_contexts,
            "total_events": self.total_events,
            "total_amplifications": self.total_amplifications,
            "total_clusters": self.total_clusters,
            "events_by_type": dict(self.events_by_type),
            "events_by_mode": dict(self.events_by_mode),
            "avg_resonance_strength": self.avg_resonance_strength,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveResonance:
    """Resonance engine with context, concept, event, and cluster state.

    The engine maintains registries of resonance contexts, events,
    amplification profiles, and clusters. Each context holds the concepts
    an agent has registered (each with an attribute vector) and references
    the events and clusters derived from them. Resonance is detected by
    computing the cosine similarity of two concepts' attribute vectors;
    the sign and magnitude of that similarity determine the resonance
    mode. Amplification is measured per event and tracked through a
    lifecycle. Clustering groups concepts into connected components of
    sufficiently strong resonance, from which insight can be synthesized.
    All state mutations are guarded by a single lock so the engine is
    safe to call from multiple threads.
    """

    # Capacity limits to bound memory use per engine instance.
    MAX_CONTEXTS: int = 10000
    MAX_CONCEPTS_PER_CONTEXT: int = 5000
    MAX_EVENTS_PER_CONTEXT: int = 5000
    MAX_AMPLIFICATIONS: int = 10000
    MAX_CLUSTERS: int = 5000
    # Detection thresholds.
    CONSTRUCTIVE_THRESHOLD: float = 0.3
    DESTRUCTIVE_THRESHOLD: float = -0.3
    # Default cluster edge threshold.
    DEFAULT_CLUSTER_THRESHOLD: float = 0.5

    def __init__(self) -> None:
        self._contexts: Dict[str, ResonanceContext] = {}
        self._events: Dict[str, ResonanceEvent] = {}
        self._amplifications: Dict[str, AmplificationProfile] = {}
        # Index from event_id to its amplification profile id.
        self._event_amplifications: Dict[str, str] = {}
        self._clusters: Dict[str, ResonanceCluster] = {}
        self._lock = threading.Lock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Context Management ─────────────────────────────────────────

    def register_context(
        self,
        agent_id: str,
        domain: str,
        description: str = "",
    ) -> ResonanceContext:
        """Register a new resonance context and return it.

        ``agent_id`` identifies the agent the context belongs to.
        ``domain`` is the subject area (e.g. "physics", "ethics"). An
        optional ``description`` may give free-form detail about what the
        agent is reasoning about. The new context starts empty (no
        concepts, events, or clusters). Raises ``RuntimeError`` if the
        context registry is full.
        """
        with self._lock:
            if len(self._contexts) >= self.MAX_CONTEXTS:
                raise RuntimeError("context registry is full")
            context = ResonanceContext(
                agent_id=agent_id,
                domain=domain,
                description=description,
            )
            self._contexts[context.context_id] = context
            return context

    def get_context(self, context_id: str) -> Optional[ResonanceContext]:
        """Retrieve a context by id, or ``None`` if absent."""
        with self._lock:
            return self._contexts.get(context_id)

    def list_contexts(self, agent_id: Optional[str] = None) -> list:
        """Return contexts, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all contexts are returned; otherwise
        only contexts belonging to that agent are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            contexts = list(self._contexts.values())
        if agent_id is None:
            return contexts
        return [c for c in contexts if c.agent_id == agent_id]

    # ── Concept Registration ───────────────────────────────────────

    def register_concept(
        self,
        context_id: str,
        concept: str,
        attributes: Optional[Dict[str, float]] = None,
    ) -> dict:
        """Register a concept within a context and return its concept dict.

        ``concept`` is the human-readable name. ``attributes`` is a dict
        mapping attribute names to float values; it is copied so later
        mutation by the caller does not affect the stored concept. If
        ``attributes`` is ``None`` an empty dict is used. The returned
        dict carries the assigned ``concept_id``, the concept ``name``,
        the stored ``attributes``, and a ``created_at`` timestamp.
        Re-registering an existing concept name overwrites the previous
        entry. Raises ``KeyError`` if the context_id is not registered,
        or ``RuntimeError`` if the context's concept table is full.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise KeyError(f"context not found: {context_id}")
            if len(context.concepts) >= self.MAX_CONCEPTS_PER_CONTEXT and concept not in context.concepts:
                raise RuntimeError("concept table is full for context")
            attrs: Dict[str, float] = {}
            if attributes is not None:
                for k, v in attributes.items():
                    try:
                        attrs[str(k)] = float(v)
                    except (TypeError, ValueError):
                        # Skip non-numeric attributes silently; only floats
                        # participate in resonance detection.
                        continue
            concept_dict: Dict[str, Any] = {
                "concept_id": _new_id(),
                "name": str(concept),
                "attributes": attrs,
                "created_at": _now(),
            }
            context.concepts[str(concept)] = concept_dict
            context.updated_at = _now()
            return concept_dict

    # ── Resonance Detection ────────────────────────────────────────

    def detect_resonance(
        self,
        context_id: str,
        concept_a: str,
        concept_b: str,
        resonance_type: Any = ResonanceType.STRUCTURAL,
        method: Any = DetectionMethod.CROSS_CORRELATION,
    ) -> ResonanceEvent:
        """Detect resonance between two concepts in a context.

        The two concepts must already be registered. Their attribute
        vectors are aligned on the union of attribute keys and the cosine
        similarity is computed; that becomes the resonance ``strength`` in
        [-1, 1]. The ``mode`` is CONSTRUCTIVE if strength is above the
        constructive threshold, DESTRUCTIVE if below the destructive
        threshold, COUPLED otherwise. A ResonanceSignature is built whose
        frequency is the attribute overlap ratio, amplitude is the absolute
        strength, and phase is derived from the mode. Raises ``KeyError``
        if the context_id or either concept is not registered, or
        ``RuntimeError`` if the context's event table is full.
        """
        rtype = _resolve_enum(ResonanceType, resonance_type)
        dmethod = _resolve_enum(DetectionMethod, method)
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise KeyError(f"context not found: {context_id}")
            ca = context.concepts.get(concept_a)
            if ca is None:
                raise KeyError(f"concept not found: {concept_a}")
            cb = context.concepts.get(concept_b)
            if cb is None:
                raise KeyError(f"concept not found: {concept_b}")
            if len(context.event_ids) >= self.MAX_EVENTS_PER_CONTEXT:
                raise RuntimeError("event table is full for context")
            attrs_a = ca.get("attributes", {}) or {}
            attrs_b = cb.get("attributes", {}) or {}
            strength = _cosine_similarity(attrs_a, attrs_b)
            # Determine the resonance mode from the strength sign/magnitude.
            if strength > self.CONSTRUCTIVE_THRESHOLD:
                mode = ResonanceMode.CONSTRUCTIVE
            elif strength < self.DESTRUCTIVE_THRESHOLD:
                mode = ResonanceMode.DESTRUCTIVE
            else:
                mode = ResonanceMode.COUPLED
            # Signature frequency: attribute overlap ratio (Jaccard-like).
            keys_a = set(attrs_a)
            keys_b = set(attrs_b)
            union = keys_a | keys_b
            if union:
                frequency = len(keys_a & keys_b) / float(len(union))
            else:
                frequency = 0.0
            amplitude = abs(strength)
            phase = _phase_for_mode(mode)
            signature = ResonanceSignature(
                concept_a=concept_a,
                concept_b=concept_b,
                frequency=frequency,
                amplitude=amplitude,
                phase=phase,
                method=dmethod,
            )
            event = ResonanceEvent(
                context_id=context_id,
                concept_a=concept_a,
                concept_b=concept_b,
                resonance_type=rtype,
                mode=mode,
                strength=strength,
                signature=signature,
            )
            self._events[event.event_id] = event
            context.event_ids.append(event.event_id)
            context.updated_at = _now()
            return event

    def get_event(self, event_id: str) -> Optional[ResonanceEvent]:
        """Retrieve a resonance event by id, or ``None`` if absent."""
        with self._lock:
            return self._events.get(event_id)

    def list_events(
        self,
        context_id: Optional[str] = None,
        resonance_type: Optional[Any] = None,
    ) -> list:
        """Return events, optionally filtered by context and/or type.

        When ``context_id`` is ``None`` all events are returned; otherwise
        only events for that context are returned. When ``resonance_type``
        is ``None`` no type filter is applied; otherwise only events of
        that type are returned (may be passed as a ``ResonanceType`` or
        its string name/value). The returned list is a snapshot copy.
        """
        if resonance_type is not None:
            rtype = _resolve_enum(ResonanceType, resonance_type)
        else:
            rtype = None
        with self._lock:
            events = list(self._events.values())
        if context_id is not None:
            events = [e for e in events if e.context_id == context_id]
        if rtype is not None:
            events = [e for e in events if e.resonance_type == rtype]
        return events

    # ── Amplification ──────────────────────────────────────────────

    def measure_amplification(self, event_id: str) -> AmplificationProfile:
        """Measure how much a resonance amplifies its constituent concepts.

        Amplification is derived from the resonance strength: peak
        amplification is the absolute strength; the current level starts
        slightly below the peak; the decay rate is small for strong
        resonance (it sustains) and larger for weak resonance (it fades).
        The lifecycle status is PEAK for very strong resonance, BUILDING
        for strong, DORMANT for moderate, DAMPED for weak or destructive.

        If a profile already exists for this event it is updated in place;
        otherwise a new profile is created. Raises ``KeyError`` if the
        event_id is not registered.
        """
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                raise KeyError(f"event not found: {event_id}")
            magnitude = abs(event.strength)
            peak = magnitude
            current = magnitude * 0.85
            # Strong resonance sustains (low decay); weak resonance fades.
            decay = 0.05 + 0.1 * (1.0 - magnitude)
            if magnitude >= 0.7:
                status = AmplificationStatus.PEAK
            elif magnitude >= 0.3:
                status = AmplificationStatus.BUILDING
            elif magnitude >= 0.1:
                status = AmplificationStatus.DORMANT
            else:
                status = AmplificationStatus.DAMPED
            existing_pid = self._event_amplifications.get(event_id)
            if existing_pid is not None and existing_pid in self._amplifications:
                profile = self._amplifications[existing_pid]
                profile.peak_amplification = peak
                profile.current_level = current
                profile.decay_rate = decay
                profile.status = status
                profile.updated_at = _now()
                return profile
            if len(self._amplifications) >= self.MAX_AMPLIFICATIONS:
                raise RuntimeError("amplification registry is full")
            profile = AmplificationProfile(
                event_id=event_id,
                status=status,
                peak_amplification=peak,
                current_level=current,
                decay_rate=decay,
            )
            self._amplifications[profile.profile_id] = profile
            self._event_amplifications[event_id] = profile.profile_id
            return profile

    def get_amplification(self, event_id: str) -> Optional[AmplificationProfile]:
        """Retrieve the amplification profile for an event, if one exists.

        Returns ``None`` if no amplification has been measured for the
        given event_id, or if the event_id itself is not registered.
        """
        with self._lock:
            pid = self._event_amplifications.get(event_id)
            if pid is None:
                return None
            return self._amplifications.get(pid)

    def list_amplifications(self, context_id: Optional[str] = None) -> list:
        """Return amplification profiles, optionally filtered by context.

        When ``context_id`` is ``None`` all profiles are returned;
        otherwise only profiles whose owning event belongs to that
        context are returned. The returned list is a snapshot copy.
        """
        with self._lock:
            profiles = list(self._amplifications.values())
            if context_id is None:
                return profiles
            result: List[AmplificationProfile] = []
            for p in profiles:
                event = self._events.get(p.event_id)
                if event is not None and event.context_id == context_id:
                    result.append(p)
            return result

    # ── Clustering ─────────────────────────────────────────────────

    def cluster_resonances(
        self,
        context_id: str,
        threshold: float = 0.5,
    ) -> list:
        """Group resonant concepts into clusters via connected components.

        All events for the context are gathered. An edge is drawn between
        two concepts when the absolute strength of their resonance event
        meets or exceeds ``threshold``. The connected components of the
        resulting graph become clusters; each records its member concepts,
        the event ids that link them, and a coherence score equal to the
        mean absolute strength of those events.

        Existing clusters for the context are replaced, and the affected
        events' ``cluster_id`` fields are updated (or cleared if they fell
        below threshold). Raises ``KeyError`` if the context_id is not
        registered, or ``RuntimeError`` if the cluster registry is full.
        """
        thr = _clamp(threshold, 0.0, 1.0)
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise KeyError(f"context not found: {context_id}")
            # Gather this context's events.
            ctx_events: List[ResonanceEvent] = [
                self._events[eid] for eid in context.event_ids
                if eid in self._events
            ]
            # Build adjacency over concepts, recording the linking event.
            adjacency: Dict[str, set] = {}
            edge_events: List[ResonanceEvent] = []
            for ev in ctx_events:
                if abs(ev.strength) >= thr:
                    adjacency.setdefault(ev.concept_a, set()).add(ev.concept_b)
                    adjacency.setdefault(ev.concept_b, set()).add(ev.concept_a)
                    edge_events.append(ev)
            # Clear cluster_id on all context events first; reassign below.
            for ev in ctx_events:
                ev.cluster_id = None
            # Remove existing clusters for this context.
            for cid in list(context.cluster_ids):
                self._clusters.pop(cid, None)
            context.cluster_ids = []
            # Find connected components via iterative BFS.
            visited: set = set()
            new_clusters: List[ResonanceCluster] = []
            for start in adjacency:
                if start in visited:
                    continue
                component: List[str] = []
                queue: List[str] = [start]
                visited.add(start)
                while queue:
                    cur = queue.pop()
                    component.append(cur)
                    for nb in adjacency.get(cur, ()):
                        if nb not in visited:
                            visited.add(nb)
                            queue.append(nb)
                component_set = set(component)
                # Collect the edge events within this component.
                comp_events = [
                    ev for ev in edge_events
                    if ev.concept_a in component_set and ev.concept_b in component_set
                ]
                if not comp_events:
                    continue
                coherence = sum(abs(ev.strength) for ev in comp_events) / float(len(comp_events))
                if len(self._clusters) >= self.MAX_CLUSTERS:
                    raise RuntimeError("cluster registry is full")
                cluster = ResonanceCluster(
                    context_id=context_id,
                    concepts=sorted(component),
                    event_ids=[ev.event_id for ev in comp_events],
                    coherence=coherence,
                )
                self._clusters[cluster.cluster_id] = cluster
                context.cluster_ids.append(cluster.cluster_id)
                # Point each member event at its new cluster.
                for ev in comp_events:
                    ev.cluster_id = cluster.cluster_id
                new_clusters.append(cluster)
            context.updated_at = _now()
            return new_clusters

    def get_cluster(self, cluster_id: str) -> Optional[ResonanceCluster]:
        """Retrieve a cluster by id, or ``None`` if absent."""
        with self._lock:
            return self._clusters.get(cluster_id)

    def list_clusters(self, context_id: Optional[str] = None) -> list:
        """Return clusters, optionally filtered by context.

        When ``context_id`` is ``None`` all clusters are returned;
        otherwise only clusters belonging to that context are returned.
        The returned list is a snapshot copy.
        """
        with self._lock:
            clusters = list(self._clusters.values())
        if context_id is None:
            return clusters
        return [c for c in clusters if c.context_id == context_id]

    # ── Insight Generation ─────────────────────────────────────────

    def generate_insight(self, cluster_id: str) -> dict:
        """Generate an insight description from a resonance cluster.

        The insight is a short text synthesizing what the cluster means:
        it names the member concepts, the coherence score, the dominant
        resonance mode among the cluster's events, and a note on whether
        the alignment produces amplification or cancellation. The text is
        stored on the cluster's ``insight`` field and returned in a dict
        alongside the cluster id, concept list, coherence, and generation
        timestamp. Raises ``KeyError`` if the cluster_id is not registered.
        """
        with self._lock:
            cluster = self._clusters.get(cluster_id)
            if cluster is None:
                raise KeyError(f"cluster not found: {cluster_id}")
            # Determine the dominant mode among the cluster's events.
            mode_counts: Dict[str, int] = {}
            total_strength = 0.0
            for eid in cluster.event_ids:
                ev = self._events.get(eid)
                if ev is None:
                    continue
                mode_key = ev.mode.value
                mode_counts[mode_key] = mode_counts.get(mode_key, 0) + 1
                total_strength += ev.strength
            if mode_counts:
                dominant_mode = max(mode_counts, key=mode_counts.get)
            else:
                dominant_mode = ResonanceMode.COUPLED.value
            member_count = len(cluster.concepts)
            event_count = len(cluster.event_ids)
            concepts_str = ", ".join(cluster.concepts) if cluster.concepts else "(none)"
            if total_strength >= 0:
                effect = "amplification and emergent meaning"
            else:
                effect = "mutual damping and cancellation"
            insight_text = (
                f"Resonance cluster of {member_count} concept(s) "
                f"({concepts_str}) linked by {event_count} resonance event(s); "
                f"coherence={cluster.coherence:.3f}, dominant mode={dominant_mode}. "
                f"The alignment produces {effect}."
            )
            cluster.insight = insight_text
            cluster_id_out = cluster.cluster_id
            concepts_out = list(cluster.concepts)
            coherence_out = cluster.coherence
            context_id_out = cluster.context_id
            # Touch the owning context's updated_at.
            context = self._contexts.get(context_id_out)
            if context is not None:
                context.updated_at = _now()
            return {
                "cluster_id": cluster_id_out,
                "context_id": context_id_out,
                "insight": insight_text,
                "concepts": concepts_out,
                "coherence": coherence_out,
                "dominant_mode": dominant_mode,
                "generated_at": _now(),
            }

    # ── Network Mapping ────────────────────────────────────────────

    def map_network(self, context_id: str) -> dict:
        """Return the full network of resonance connections for a context.

        The network is a dict with ``nodes`` (one entry per registered
        concept, carrying its name, attribute keys, and concept id),
        ``edges`` (one entry per resonance event, carrying source, target,
        strength, resonance type, mode, and event id), and ``stats``
        summarizing node count, edge count, mean absolute strength, and
        the cluster count. Returns an empty network if the context is
        absent.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return {
                    "context_id": context_id,
                    "nodes": [],
                    "edges": [],
                    "stats": {
                        "node_count": 0,
                        "edge_count": 0,
                        "mean_abs_strength": 0.0,
                        "cluster_count": 0,
                    },
                }
            nodes: List[Dict[str, Any]] = []
            for name, concept_dict in context.concepts.items():
                attrs = concept_dict.get("attributes", {}) or {}
                nodes.append({
                    "concept": name,
                    "concept_id": concept_dict.get("concept_id", ""),
                    "attribute_keys": list(attrs.keys()),
                })
            edges: List[Dict[str, Any]] = []
            strength_sum = 0.0
            for eid in context.event_ids:
                ev = self._events.get(eid)
                if ev is None:
                    continue
                edges.append({
                    "event_id": ev.event_id,
                    "source": ev.concept_a,
                    "target": ev.concept_b,
                    "strength": ev.strength,
                    "resonance_type": _enum_value(ResonanceType, ev.resonance_type),
                    "mode": _enum_value(ResonanceMode, ev.mode),
                    "cluster_id": ev.cluster_id,
                })
                strength_sum += abs(ev.strength)
            edge_count = len(edges)
            mean_abs = strength_sum / edge_count if edge_count else 0.0
            cluster_count = len(context.cluster_ids)
            return {
                "context_id": context_id,
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "node_count": len(nodes),
                    "edge_count": edge_count,
                    "mean_abs_strength": mean_abs,
                    "cluster_count": cluster_count,
                },
            }

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> ResonanceStats:
        """Compute aggregate statistics over the current engine state.

        Counts contexts, events, amplification profiles, and clusters;
        tallies events by resonance type and by mode; and computes the
        mean resonance strength over all events (0.0 when none exist).
        Breakdown dicts are keyed by the enum ``.value`` strings so the
        stats serialize cleanly to JSON.
        """
        with self._lock:
            total_contexts = len(self._contexts)
            total_events = len(self._events)
            total_amplifications = len(self._amplifications)
            total_clusters = len(self._clusters)
            by_type: Dict[str, int] = {}
            by_mode: Dict[str, int] = {}
            strength_sum = 0.0
            for event in self._events.values():
                type_key = event.resonance_type.value
                mode_key = event.mode.value
                by_type[type_key] = by_type.get(type_key, 0) + 1
                by_mode[mode_key] = by_mode.get(mode_key, 0) + 1
                strength_sum += event.strength
            avg_strength = strength_sum / total_events if total_events else 0.0
            return ResonanceStats(
                total_contexts=total_contexts,
                total_events=total_events,
                total_amplifications=total_amplifications,
                total_clusters=total_clusters,
                events_by_type=by_type,
                events_by_mode=by_mode,
                avg_resonance_strength=avg_strength,
            )

    # ── Maintenance ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests."""
        with self._lock:
            self._contexts.clear()
            self._events.clear()
            self._amplifications.clear()
            self._event_amplifications.clear()
            self._clusters.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_resonance_engine() -> AgentCognitiveResonance:
    """Get or create the singleton ``AgentCognitiveResonance`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveResonance()
        return _engine


def reset_resonance_engine() -> None:
    """Reset the singleton ``AgentCognitiveResonance`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_resonance_engine`` call creates a
    fresh instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
