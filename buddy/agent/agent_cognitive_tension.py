from __future__ import annotations

# Agent Cognitive Tension Engine — dialectical and paradoxical tension
# between competing hypotheses, ideas, and frameworks.
#
# Cognition is not a march toward a single settled view. An agent that
# holds only one hypothesis at a time is brittle: it cannot represent the
# live possibility that its current best guess is wrong, and it cannot do
# the creative work of letting two incompatible frameworks rub against each
# other until something new emerges. Healthy cognition keeps contradictory
# material in play simultaneously. This module instruments that capacity.
#
# Tension, in this framing, is the cognitive resource that exists between
# two poles that cannot both be fully accepted and cannot both be fully
# rejected. A thesis stands against an antithesis; a self-contradictory
# proposition refuses to dissolve under inspection; two viable but mutually
# exclusive options refuse to collapse into a single choice. The engine
# does not treat tension as a defect to be eliminated. It treats tension as
# a creative resource: the friction between two poles is precisely where
# synthesis becomes possible. Forcing premature resolution destroys that
# resource; the art is knowing when to hold the tension, when to resolve
# it, and when to let one side dissolve on its own.
#
# The engine is grounded in two classical pictures of contradiction. The
# Hegelian dialectic describes tension as the relationship between a thesis
# and its antithesis, out of which a synthesis emerges that preserves what
# was true in both while transcending their opposition — Aufhebung, the
# cancellation that also preserves. The Hegelian move is not compromise
# (splitting the difference) but sublation: the synthesis is a new
# standpoint from which the original opposition no longer looks
# fundamental. Janusian thinking, named for the two-faced Roman god, is the
# cognitive capacity to hold two contradictory ideas in mind simultaneously
# without forcing a resolution — the posture that, in its strongest form,
# lets the contradiction itself become generative. Creative cognition
# across domains, from scientific discovery to poetic composition,
# repeatedly passes through such held contradictions on the way to insight.
#
# A tension pair is the engine's central object: two poles, a kind
# (dialectic, paradoxical, competing, conflicting, ambivalent,
# complementary), an intensity in [0, 1], a state (latent, acknowledged,
# held, resolving, resolved, dissolved), and a polarity (positive,
# negative, neutral, mixed) describing whether the tension is productive
# or destructive. The engine manages the lifecycle of each pair. A pair
# that is merely recognized begins in the ACKNOWLEDGED state. When the
# agent deliberately holds the tension to let synthesis gestate, the pair
# moves to HELD and a holding strategy is recorded (observe, rotate
# attention, deepen each pole, seek unifying context, articulate, enact).
# When the agent moves to resolve the tension, a resolution attempt is
# recorded with a mode (synthesis, selection, compromise, transcendence,
# dissolution, defer) and, on success, the pair reaches RESOLVED with an
# optional synthesis statement. When one pole collapses outright — the
# agent abandons it, or evidence removes it — the pair is DISSOLVED rather
# than resolved, since no synthesis occurred.
#
# Tension is not always beneficial. A productive (POSITIVE) tension
# energizes inquiry and pulls the agent toward a richer view; a destructive
# (NEGATIVE) tension paralyzes the agent, locking it in indecision or
# oscillation; a MIXED tension has aspects of both; a NEUTRAL tension
# neither moves the agent forward nor holds it back. The polarity is
# classified from the kind and intensity: a high-intensity dialectic is
# generative (the clash of thesis and antithesis is doing real work), a
# high-intensity conflict is destructive (the poles genuinely contradict
# and the friction yields nothing), ambivalence is intrinsically mixed,
# and complementary tension is intrinsically positive (the poles enrich
# each other rather than oppose).
#
# Architecture:
#     AgentCognitiveTension (thread-safe singleton)
#     ├── TensionPole          (one side of a potential or actual pair)
#     ├── TensionPair          (two poles held in tension, with state)
#     ├── TensionSnapshot      (a point-in-time aggregate for one agent)
#     ├── ResolutionAttempt    (one attempt to resolve a pair)
#     ├── HoldingDecision      (one decision to hold a pair rather than resolve)
#     ├── TensionProfile       (per-agent aggregate posture)
#     └── TensionStats         (engine-wide aggregate statistics)
#
# The engine is intentionally dependency-free so it can run in any Buddy
# runtime without extra packages. All state mutations are guarded by a
# reentrant lock so the engine is safe to call from multiple threads.

import threading
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class TensionKind(str, Enum):
    """The structural form of a tension between two poles.

    Each kind describes a different way two ideas can stand in opposition.
    DIALECTIC is the classical thesis-vs-antithesis pair out of which a
    synthesis may emerge. PARADOXICAL is a single object or proposition
    that is self-contradictory yet possibly true — the kind of tension
    that cannot be resolved by picking a side. COMPETING is a pair of
    viable but incompatible options where only one can be chosen.
    CONFLICTING is a pair that is logically contradictory and cannot both
    hold. AMBIVALENT is mixed feeling toward one object rather than a
    clash between two objects. COMPLEMENTARY is a tension that enriches
    both poles rather than opposing them — the friction itself is the
    value.
    """
    DIALECTIC = "dialectic"          # thesis vs antithesis
    PARADOXICAL = "paradoxical"      # self-contradictory but possibly true
    COMPETING = "competing"          # two viable but incompatible options
    CONFLICTING = "conflicting"      # logically contradictory
    AMBIVALENT = "ambivalent"        # mixed feelings toward one object
    COMPLEMENTARY = "complementary"  # tension that enriches both poles


class TensionState(str, Enum):
    """The lifecycle state of a tension pair.

    LATENT means the tension exists but has not been acknowledged by the
    agent — the poles coexist without the agent recognizing the
    contradiction. ACKNOWLEDGED means the tension has been recognized but
    not yet acted on. HELD means the agent has deliberately decided to
    keep the tension in play, typically to allow synthesis to gestate.
    RESOLVING means the agent is actively moving the pair toward a
    synthesis. RESOLVED means a synthesis has been achieved and the
    tension is no longer live. DISSOLVED means one pole collapsed or was
    removed, so the tension evaporated without a synthesis.
    """
    LATENT = "latent"            # tension exists but unacknowledged
    ACKNOWLEDGED = "acknowledged"  # recognized but unresolved
    HELD = "held"                # deliberately held for synthesis
    RESOLVING = "resolving"      # actively moving toward synthesis
    RESOLVED = "resolved"        # synthesis achieved
    DISSOLVED = "dissolved"      # one pole collapsed or removed


class ResolutionMode(str, Enum):
    """The strategy by which a tension is brought to resolution.

    SYNTHESIS integrates both poles into a higher unity that preserves
    what was true in each — the Hegelian move. SELECTION chooses one pole
    and drops the other. COMPROMISE partially integrates the poles by
    accepting a watered-down version of each. TRANSCENDENCE moves beyond
    both poles to a standpoint from which the original opposition no
    longer applies. DISSOLUTION drops both poles, treating the tension as
    malformed. DEFER holds the tension indefinitely without commitment,
    declining to resolve now.
    """
    SYNTHESIS = "synthesis"        # integrate both into higher unity
    SELECTION = "selection"        # choose one pole
    COMPROMISE = "compromise"      # partial integration
    TRANSCENDENCE = "transcendence"  # move beyond both
    DISSOLUTION = "dissolution"    # drop both
    DEFER = "defer"                # hold indefinitely


class TensionPolarity(str, Enum):
    """Whether a tension is productive or destructive for the agent.

    POSITIVE tension is creative and productive — the friction between
    the poles pulls the agent toward a richer view. NEGATIVE tension is
    destructive or paralyzing — the friction locks the agent in
    indecision or oscillation without yielding insight. NEUTRAL tension
    is neither productive nor destructive — it simply coexists. MIXED
    tension has both positive and negative aspects, with some friction
    generative and some paralyzing.
    """
    POSITIVE = "positive"    # creative, productive tension
    NEGATIVE = "negative"    # destructive, paralyzing tension
    NEUTRAL = "neutral"      # neither productive nor destructive
    MIXED = "mixed"          # both positive and negative aspects


class HoldingStrategy(str, Enum):
    """A strategy for deliberately holding a tension rather than resolving it.

    HOLD_AND_OBSERVE keeps the tension in awareness without acting on it,
    letting the contradiction sit. ROTATE_ATTENTION alternates focus
    between the poles so each is examined in turn. DEEPLY_CONSIDER
    deepens each pole separately before any attempt at synthesis, so
    neither is flattened. SEEK_CONTEXT searches for a unifying context in
    which the opposition dissolves into a larger picture. ARTICULATE
    verbalizes the tension, putting the contradiction into words so its
    structure becomes inspectable. ENACT acts within the tension, taking
    action that does not resolve the opposition but moves forward inside
    it.
    """
    HOLD_AND_OBSERVE = "hold_and_observe"  # deliberately hold and watch
    ROTATE_ATTENTION = "rotate_attention"  # alternate focus between poles
    DEEPLY_CONSIDER = "deeply_consider"    # deepen each pole separately
    SEEK_CONTEXT = "seek_context"          # find unifying context
    ARTICULATE = "articulate"              # verbalize the tension
    ENACT = "enact"                        # act within the tension


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a pole/pair/snapshot/etc."""
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric inputs are coerced to ``low`` so callers can pass loosely
    typed values without raising.
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
    member values (e.g. ``"dialectic"``) and then against member names
    (e.g. ``"DIALECTIC"``), so callers may pass either form. Raises
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


def _classify_polarity(intensity: float, kind: TensionKind) -> TensionPolarity:
    """Classify the polarity of a tension from its intensity and kind.

    A high-intensity dialectic is POSITIVE — the clash of thesis and
    antithesis is doing real generative work. A high-intensity conflict is
    NEGATIVE — the poles genuinely contradict and the friction yields
    nothing productive. Ambivalence is intrinsically MIXED, since it is
    mixed feeling toward one object rather than a clean opposition.
    Complementary tension is intrinsically POSITIVE, since the friction
    enriches both poles rather than opposing them. Everything else falls
    to NEUTRAL, including low-intensity dialectics and conflicts where the
    friction has not yet become either productive or destructive.
    """
    inten = _clamp(intensity, 0.0, 1.0)
    if kind == TensionKind.DIALECTIC and inten > 0.7:
        return TensionPolarity.POSITIVE
    if kind == TensionKind.CONFLICTING and inten > 0.7:
        return TensionPolarity.NEGATIVE
    if kind == TensionKind.AMBIVALENT:
        return TensionPolarity.MIXED
    if kind == TensionKind.COMPLEMENTARY:
        return TensionPolarity.POSITIVE
    return TensionPolarity.NEUTRAL


def _empty_state_distribution() -> Dict[TensionState, int]:
    """Return a fresh state counter initialized to zero for every state."""
    return {state: 0 for state in TensionState}


def _empty_kind_distribution() -> Dict[TensionKind, int]:
    """Return a fresh kind counter initialized to zero for every kind."""
    return {kind: 0 for kind in TensionKind}


def _empty_polarity_distribution() -> Dict[TensionPolarity, int]:
    """Return a fresh polarity counter initialized to zero for every polarity."""
    return {polarity: 0 for polarity in TensionPolarity}


def _dominant(counter: Dict[Any, int]) -> Optional[Any]:
    """Return the key with the highest count, or ``None`` if all are zero.

    Ties are broken by first occurrence in iteration order. Returns
    ``None`` when the counter is empty or every count is zero, so a fresh
    agent with no pairs reports no dominant kind or polarity.
    """
    best_key: Optional[Any] = None
    best_count = 0
    for key, count in counter.items():
        if count > best_count:
            best_key = key
            best_count = count
    return best_key


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TensionPole:
    """One side of a potential or actual tension pair.

    A pole is a single idea, hypothesis, option, or framework that may
    stand in tension with another. ``strength`` in [0, 1] expresses how
    firmly the agent currently holds this pole — how much credence or
    commitment it carries. Poles are independent of pairs: a pole may be
    registered before any pair is formed, and the same pole may
    participate in multiple pairs (an idea can stand in tension with
    several others simultaneously).
    """
    pole_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    label: str = ""
    description: str = ""
    strength: float = 0.5
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this pole to a plain dict."""
        return {
            "pole_id": self.pole_id,
            "agent_id": self.agent_id,
            "label": self.label,
            "description": self.description,
            "strength": self.strength,
            "timestamp": self.timestamp,
        }


@dataclass
class TensionPair:
    """Two poles held in tension, with a state and polarity.

    A pair binds two previously registered poles into a single tension.
    ``kind`` describes the structural form of the opposition (dialectic,
    paradoxical, competing, conflicting, ambivalent, complementary).
    ``intensity`` in [0, 1] measures how strongly the poles pull against
    each other. ``state`` tracks the pair through its lifecycle from
    LATENT through ACKNOWLEDGED, HELD, RESOLVING, to RESOLVED or
    DISSOLVED. ``polarity`` records whether the tension is productive or
    destructive. ``resolution_mode`` is set when the agent commits to a
    particular resolution strategy and remains ``None`` until then.
    """
    pair_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    kind: TensionKind = TensionKind.DIALECTIC
    pole_a_id: str = ""
    pole_b_id: str = ""
    intensity: float = 0.5
    state: TensionState = TensionState.ACKNOWLEDGED
    polarity: TensionPolarity = TensionPolarity.NEUTRAL
    timestamp: str = field(default_factory=_now)
    resolution_mode: Optional[ResolutionMode] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this pair to a plain dict, expanding enums via ``.value``.

        The optional ``resolution_mode`` is emitted as ``None`` when
        unset, or as its enum ``.value`` string when set, so the
        serialized form is JSON-friendly.
        """
        return {
            "pair_id": self.pair_id,
            "agent_id": self.agent_id,
            "kind": _enum_value(TensionKind, self.kind),
            "pole_a_id": self.pole_a_id,
            "pole_b_id": self.pole_b_id,
            "intensity": self.intensity,
            "state": _enum_value(TensionState, self.state),
            "polarity": _enum_value(TensionPolarity, self.polarity),
            "timestamp": self.timestamp,
            "resolution_mode": (
                _enum_value(ResolutionMode, self.resolution_mode)
                if self.resolution_mode is not None
                else None
            ),
        }


@dataclass
class TensionSnapshot:
    """A point-in-time aggregate of an agent's tension landscape.

    A snapshot summarizes the agent's pairs at the moment it was taken.
    ``total_pairs`` is the count of pairs for the agent. ``avg_intensity``
    is the mean intensity across those pairs (zero when there are none).
    ``dominant_kind`` is the most common kind among the pairs, or ``None``
    when there are no pairs. ``held_count`` and ``resolved_count`` tally
    pairs currently in the HELD and RESOLVED states respectively.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    total_pairs: int = 0
    avg_intensity: float = 0.0
    dominant_kind: Optional[TensionKind] = None
    held_count: int = 0
    resolved_count: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        The optional ``dominant_kind`` is emitted as ``None`` when unset,
        or as its enum ``.value`` string when set.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "total_pairs": self.total_pairs,
            "avg_intensity": self.avg_intensity,
            "dominant_kind": (
                _enum_value(TensionKind, self.dominant_kind)
                if self.dominant_kind is not None
                else None
            ),
            "held_count": self.held_count,
            "resolved_count": self.resolved_count,
            "timestamp": self.timestamp,
        }


@dataclass
class ResolutionAttempt:
    """One attempt to bring a tension pair to resolution.

    Records the ``mode`` used (synthesis, selection, compromise,
    transcendence, dissolution, defer), a free-form ``outcome``
    description, and an optional ``synthesis`` statement expressing the
    higher unity reached (relevant for SYNTHESIS and TRANSCENDENCE modes).
    ``success`` indicates whether the attempt achieved resolution; on
    success the engine marks the underlying pair as RESOLVED.
    """
    attempt_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    pair_id: str = ""
    mode: ResolutionMode = ResolutionMode.SYNTHESIS
    outcome: str = ""
    synthesis: Optional[str] = None
    success: bool = True
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this resolution attempt to a plain dict, expanding enums.

        The optional ``synthesis`` is emitted as ``None`` when unset, or
        as the stored string when set.
        """
        return {
            "attempt_id": self.attempt_id,
            "agent_id": self.agent_id,
            "pair_id": self.pair_id,
            "mode": _enum_value(ResolutionMode, self.mode),
            "outcome": self.outcome,
            "synthesis": self.synthesis,
            "success": self.success,
            "timestamp": self.timestamp,
        }


@dataclass
class HoldingDecision:
    """A decision to hold a tension rather than resolve it.

    Records the ``strategy`` chosen (hold and observe, rotate attention,
    deeply consider, seek context, articulate, enact), a free-form
    ``rationale`` explaining why the tension is being held rather than
    resolved, and a ``duration`` in seconds for how long the agent intends
    to hold before revisiting. On creation the engine marks the
    underlying pair as HELD.
    """
    decision_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    pair_id: str = ""
    strategy: HoldingStrategy = HoldingStrategy.HOLD_AND_OBSERVE
    rationale: str = ""
    duration: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this holding decision to a plain dict, expanding the enum."""
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "pair_id": self.pair_id,
            "strategy": _enum_value(HoldingStrategy, self.strategy),
            "rationale": self.rationale,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }


@dataclass
class TensionProfile:
    """Per-agent aggregate tension profile.

    A profile summarizes one agent's tension posture. ``total_pairs`` is
    the count of pairs registered for the agent. ``avg_intensity`` is the
    mean intensity across those pairs. ``dominant_kind`` is the most
    common kind, or ``None`` when there are no pairs. ``dominant_polarity``
    is the most common polarity, or ``None`` when there are no pairs.
    ``held_count`` and ``resolved_count`` tally pairs currently in the
    HELD and RESOLVED states. ``last_updated`` records when the profile
    was last refreshed.
    """
    agent_id: str = ""
    total_pairs: int = 0
    avg_intensity: float = 0.0
    dominant_kind: Optional[TensionKind] = None
    dominant_polarity: Optional[TensionPolarity] = None
    held_count: int = 0
    resolved_count: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict.

        The optional ``dominant_kind`` and ``dominant_polarity`` are
        emitted as ``None`` when unset, or as their enum ``.value``
        strings when set, so the serialized form is JSON-friendly.
        """
        return {
            "agent_id": self.agent_id,
            "total_pairs": self.total_pairs,
            "avg_intensity": self.avg_intensity,
            "dominant_kind": (
                _enum_value(TensionKind, self.dominant_kind)
                if self.dominant_kind is not None
                else None
            ),
            "dominant_polarity": (
                _enum_value(TensionPolarity, self.dominant_polarity)
                if self.dominant_polarity is not None
                else None
            ),
            "held_count": self.held_count,
            "resolved_count": self.resolved_count,
            "last_updated": self.last_updated,
        }


@dataclass
class TensionStats:
    """Engine-wide aggregate statistics.

    Counts of poles, pairs, resolution attempts, and holding decisions
    across all agents. ``state_distribution`` tallies all pairs by their
    current state. ``kind_distribution`` tallies all pairs by their kind.
    ``polarity_distribution`` tallies all pairs by their polarity. The
    breakdown dicts are keyed by enum ``.value`` strings in the
    serialized form so the stats serialize cleanly to JSON.
    """
    total_poles: int = 0
    total_pairs: int = 0
    total_resolutions: int = 0
    total_holdings: int = 0
    state_distribution: Dict[str, int] = field(default_factory=dict)
    kind_distribution: Dict[str, int] = field(default_factory=dict)
    polarity_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The breakdown dicts are shallow-copied so the serialized form is
        independent of the live stats.
        """
        return {
            "total_poles": self.total_poles,
            "total_pairs": self.total_pairs,
            "total_resolutions": self.total_resolutions,
            "total_holdings": self.total_holdings,
            "state_distribution": dict(self.state_distribution),
            "kind_distribution": dict(self.kind_distribution),
            "polarity_distribution": dict(self.polarity_distribution),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveTension:
    """Thread-safe engine for managing agent cognitive tension.

    The engine maintains registries of tension poles, tension pairs,
    snapshots, resolution attempts, holding decisions, and per-agent
    profiles. Poles are the atomic units — single ideas, hypotheses, or
    frameworks. Pairs bind two poles into a managed tension with a kind,
    intensity, state, and polarity. The engine classifies polarity from
    kind and intensity when a pair is formed, tracks each pair through
    its lifecycle (ACKNOWLEDGED -> HELD -> RESOLVING -> RESOLVED, or
    DISSOLVED when a pole collapses), and records resolution attempts and
    holding decisions as the agent acts on each pair.

    The engine treats tension as a creative resource. The HOLD state is
    first-class: an agent may deliberately keep a tension in play — by
    observing it, rotating attention between its poles, deepening each
    pole, seeking a unifying context, articulating it, or enacting action
    within it — rather than rushing to resolve. Synthesis, when it
    comes, is recorded as a free-form statement so the agent can later
    inspect what higher unity emerged from a given opposition.

    All state mutations are guarded by a single reentrant lock so the
    engine is safe to call from multiple threads. The reentrant lock
    allows public methods to delegate to one another (for example,
    ``update_profile`` calls ``get_profile``) without self-deadlock.
    """

    # Default strength assigned to a pole when the caller omits it.
    DEFAULT_POLE_STRENGTH: float = 0.5
    # Default intensity assigned to a pair when the caller omits it.
    DEFAULT_PAIR_INTENSITY: float = 0.5
    # Default list size cap applied when a list method is called without
    # an explicit limit.
    DEFAULT_LIST_LIMIT: int = 50

    def __init__(self) -> None:
        self._poles: Dict[str, TensionPole] = {}
        self._pairs: Dict[str, TensionPair] = {}
        self._snapshots: Dict[str, TensionSnapshot] = {}
        self._resolutions: Dict[str, ResolutionAttempt] = {}
        self._holdings: Dict[str, HoldingDecision] = {}
        self._profiles: Dict[str, TensionProfile] = {}
        # Running integer counters, kept in sync with the registries above.
        self._stats: Dict[str, int] = {
            "total_poles": 0,
            "total_pairs": 0,
            "total_resolutions": 0,
            "total_holdings": 0,
        }
        # Reentrant lock so public methods may call one another safely.
        self._lock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Poles ─────────────────────────────────────────────────────

    def register_pole(
        self,
        agent_id: str,
        label: str,
        description: str,
        strength: float = DEFAULT_POLE_STRENGTH,
    ) -> TensionPole:
        """Register a single tension pole for ``agent_id``.

        A pole is one side of a potential or actual tension — a single
        idea, hypothesis, option, or framework. ``strength`` in [0, 1]
        expresses how firmly the agent holds this pole; it is clamped to
        range. The pole is stored in the engine and counted in the engine
        stats. Poles are independent of pairs: register a pole before
        forming any pair that references it.
        """
        pole = TensionPole(
            agent_id=agent_id,
            label=label,
            description=description,
            strength=_clamp(strength, 0.0, 1.0),
        )
        with self._lock:
            self._poles[pole.pole_id] = pole
            self._stats["total_poles"] += 1
            return pole

    def list_poles(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[TensionPole]:
        """Return poles, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all poles are returned; otherwise
        only poles for that agent are returned. The returned list is
        capped at ``limit`` entries (most recent first by registration
        order) and is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            poles = list(self._poles.values())
        if agent_id is not None:
            poles = [p for p in poles if p.agent_id == agent_id]
        # Most recent first: reverse the insertion-ordered snapshot.
        poles.reverse()
        try:
            cap = int(limit)
        except (TypeError, ValueError):
            cap = self.DEFAULT_LIST_LIMIT
        if cap < 0:
            cap = 0
        return poles[:cap]

    def get_pole(self, pole_id: str) -> Optional[TensionPole]:
        """Retrieve a pole by id, or ``None`` if absent."""
        with self._lock:
            return self._poles.get(pole_id)

    # ── Pairs ─────────────────────────────────────────────────────

    def form_pair(
        self,
        agent_id: str,
        kind: Any,
        pole_a_id: str,
        pole_b_id: str,
        intensity: float = DEFAULT_PAIR_INTENSITY,
        polarity: Optional[Any] = None,
    ) -> TensionPair:
        """Form a tension pair binding two previously registered poles.

        ``kind`` may be passed as a ``TensionKind`` or its string
        name/value (e.g. ``"DIALECTIC"`` or ``"dialectic"``).
        ``intensity`` in [0, 1] is clamped to range. ``polarity`` may be
        passed explicitly as a ``TensionPolarity`` or its string
        name/value; when ``None`` the engine classifies the polarity from
        the kind and intensity using ``_classify_polarity``. The new pair
        begins in the ACKNOWLEDGED state — the tension has been
        recognized but not yet acted on. ``resolution_mode`` is left
        unset; it is populated only when the agent commits to a
        resolution strategy.
        """
        kind_enum = _resolve_enum(TensionKind, kind)
        inten = _clamp(intensity, 0.0, 1.0)
        if polarity is None:
            polarity_enum = _classify_polarity(inten, kind_enum)
        else:
            polarity_enum = _resolve_enum(TensionPolarity, polarity)
        pair = TensionPair(
            agent_id=agent_id,
            kind=kind_enum,
            pole_a_id=pole_a_id,
            pole_b_id=pole_b_id,
            intensity=inten,
            state=TensionState.ACKNOWLEDGED,
            polarity=polarity_enum,
        )
        with self._lock:
            self._pairs[pair.pair_id] = pair
            self._stats["total_pairs"] += 1
            return pair

    def list_pairs(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[TensionPair]:
        """Return pairs, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all pairs are returned; otherwise
        only pairs for that agent are returned. The returned list is
        capped at ``limit`` entries (most recent first by formation
        order) and is a snapshot copy.
        """
        with self._lock:
            pairs = list(self._pairs.values())
        if agent_id is not None:
            pairs = [p for p in pairs if p.agent_id == agent_id]
        pairs.reverse()
        try:
            cap = int(limit)
        except (TypeError, ValueError):
            cap = self.DEFAULT_LIST_LIMIT
        if cap < 0:
            cap = 0
        return pairs[:cap]

    def get_pair(self, pair_id: str) -> Optional[TensionPair]:
        """Retrieve a pair by id, or ``None`` if absent."""
        with self._lock:
            return self._pairs.get(pair_id)

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> TensionSnapshot:
        """Take a point-in-time snapshot of an agent's tension landscape.

        Aggregates all pairs currently registered for ``agent_id``.
        ``total_pairs`` is the count. ``avg_intensity`` is the mean
        intensity across those pairs (zero when there are none).
        ``dominant_kind`` is the most common kind among the pairs, or
        ``None`` when there are no pairs. ``held_count`` and
        ``resolved_count`` tally pairs currently in the HELD and RESOLVED
        states respectively. The snapshot is stored in the engine and
        returned.
        """
        with self._lock:
            agent_pairs = [p for p in self._pairs.values() if p.agent_id == agent_id]
            total = len(agent_pairs)
            if total > 0:
                avg_intensity = sum(p.intensity for p in agent_pairs) / total
                kind_counter: Counter = Counter(p.kind for p in agent_pairs)
                dominant_kind = kind_counter.most_common(1)[0][0]
            else:
                avg_intensity = 0.0
                dominant_kind = None
            held_count = sum(
                1 for p in agent_pairs if p.state == TensionState.HELD
            )
            resolved_count = sum(
                1 for p in agent_pairs if p.state == TensionState.RESOLVED
            )
            snapshot = TensionSnapshot(
                agent_id=agent_id,
                total_pairs=total,
                avg_intensity=avg_intensity,
                dominant_kind=dominant_kind,
                held_count=held_count,
                resolved_count=resolved_count,
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[TensionSnapshot]:
        """Return snapshots, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all snapshots are returned;
        otherwise only snapshots for that agent are returned. The
        returned list is capped at ``limit`` entries (most recent first
        by capture order) and is a snapshot copy.
        """
        with self._lock:
            snapshots = list(self._snapshots.values())
        if agent_id is not None:
            snapshots = [s for s in snapshots if s.agent_id == agent_id]
        snapshots.reverse()
        try:
            cap = int(limit)
        except (TypeError, ValueError):
            cap = self.DEFAULT_LIST_LIMIT
        if cap < 0:
            cap = 0
        return snapshots[:cap]

    def get_snapshot(self, snapshot_id: str) -> Optional[TensionSnapshot]:
        """Retrieve a snapshot by id, or ``None`` if absent."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    # ── Resolution ────────────────────────────────────────────────

    def attempt_resolution(
        self,
        agent_id: str,
        pair_id: str,
        mode: Any,
        outcome: str,
        synthesis: Optional[str] = None,
        success: bool = True,
    ) -> ResolutionAttempt:
        """Record an attempt to resolve a tension pair.

        ``mode`` may be passed as a ``ResolutionMode`` or its string
        name/value. ``outcome`` is a free-form description of what
        happened. ``synthesis`` is an optional statement of the higher
        unity reached, relevant for SYNTHESIS and TRANSCENDENCE modes;
        it is emitted as ``None`` for modes that do not produce a
        synthesis. ``success`` indicates whether the attempt achieved
        resolution.

        On success, the underlying pair is marked RESOLVED and its
        ``resolution_mode`` is set to the attempted mode. If the pair
        does not exist, the attempt is still recorded (so callers can
        log failed resolutions against stale pair ids) but no pair state
        is mutated.
        """
        mode_enum = _resolve_enum(ResolutionMode, mode)
        attempt = ResolutionAttempt(
            agent_id=agent_id,
            pair_id=pair_id,
            mode=mode_enum,
            outcome=outcome,
            synthesis=synthesis,
            success=success,
        )
        with self._lock:
            self._resolutions[attempt.attempt_id] = attempt
            self._stats["total_resolutions"] += 1
            if success:
                pair = self._pairs.get(pair_id)
                if pair is not None:
                    pair.state = TensionState.RESOLVED
                    pair.resolution_mode = mode_enum
            return attempt

    def list_resolutions(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[ResolutionAttempt]:
        """Return resolution attempts, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all attempts are returned;
        otherwise only attempts for that agent are returned. The returned
        list is capped at ``limit`` entries (most recent first by attempt
        order) and is a snapshot copy.
        """
        with self._lock:
            attempts = list(self._resolutions.values())
        if agent_id is not None:
            attempts = [a for a in attempts if a.agent_id == agent_id]
        attempts.reverse()
        try:
            cap = int(limit)
        except (TypeError, ValueError):
            cap = self.DEFAULT_LIST_LIMIT
        if cap < 0:
            cap = 0
        return attempts[:cap]

    def get_resolution(self, attempt_id: str) -> Optional[ResolutionAttempt]:
        """Retrieve a resolution attempt by id, or ``None`` if absent."""
        with self._lock:
            return self._resolutions.get(attempt_id)

    # ── Holding ───────────────────────────────────────────────────

    def decide_holding(
        self,
        agent_id: str,
        pair_id: str,
        strategy: Any,
        rationale: str,
        duration: float,
    ) -> HoldingDecision:
        """Record a decision to hold a tension rather than resolve it.

        ``strategy`` may be passed as a ``HoldingStrategy`` or its string
        name/value. ``rationale`` is a free-form explanation of why the
        tension is being held — what the agent expects to gain from
        keeping the contradiction in play. ``duration`` in seconds is how
        long the agent intends to hold before revisiting; it is coerced
        to a non-negative float.

        On creation, the underlying pair is marked HELD so its lifecycle
        reflects the deliberate hold. If the pair does not exist, the
        decision is still recorded but no pair state is mutated.
        """
        strategy_enum = _resolve_enum(HoldingStrategy, strategy)
        try:
            dur = float(duration)
        except (TypeError, ValueError):
            dur = 0.0
        if dur < 0.0:
            dur = 0.0
        decision = HoldingDecision(
            agent_id=agent_id,
            pair_id=pair_id,
            strategy=strategy_enum,
            rationale=rationale,
            duration=dur,
        )
        with self._lock:
            self._holdings[decision.decision_id] = decision
            self._stats["total_holdings"] += 1
            pair = self._pairs.get(pair_id)
            if pair is not None:
                pair.state = TensionState.HELD
            return decision

    def list_holdings(
        self,
        agent_id: Optional[str] = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> List[HoldingDecision]:
        """Return holding decisions, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all decisions are returned;
        otherwise only decisions for that agent are returned. The
        returned list is capped at ``limit`` entries (most recent first
        by decision order) and is a snapshot copy.
        """
        with self._lock:
            decisions = list(self._holdings.values())
        if agent_id is not None:
            decisions = [d for d in decisions if d.agent_id == agent_id]
        decisions.reverse()
        try:
            cap = int(limit)
        except (TypeError, ValueError):
            cap = self.DEFAULT_LIST_LIMIT
        if cap < 0:
            cap = 0
        return decisions[:cap]

    def get_holding(self, decision_id: str) -> Optional[HoldingDecision]:
        """Retrieve a holding decision by id, or ``None`` if absent."""
        with self._lock:
            return self._holdings.get(decision_id)

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> TensionProfile:
        """Get the tension profile for ``agent_id``, creating it if absent.

        A fresh profile starts with zero pairs, zero average intensity,
        no dominant kind or polarity, and zero held and resolved counts.
        Subsequent calls return the same profile object. Unlike a
        snapshot, a profile is a long-lived aggregate that callers may
        update incrementally via ``update_profile``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = TensionProfile(agent_id=agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> TensionProfile:
        """Update fields on an agent's tension profile.

        Accepts keyword arguments matching ``TensionProfile`` field names:
        ``total_pairs``, ``avg_intensity``, ``dominant_kind`` (a
        ``TensionKind`` or its string name/value), ``dominant_polarity``
        (a ``TensionPolarity`` or its string name/value), ``held_count``,
        and ``resolved_count``. Unknown keys are ignored. The profile's
        ``last_updated`` timestamp is refreshed. The profile is created
        on the fly if it does not yet exist.
        """
        with self._lock:
            profile = self.get_profile(agent_id)
            for key in ("total_pairs", "held_count", "resolved_count"):
                if key in kwargs:
                    try:
                        setattr(profile, key, int(kwargs[key]))
                    except (TypeError, ValueError):
                        pass
            if "avg_intensity" in kwargs:
                try:
                    profile.avg_intensity = float(kwargs["avg_intensity"])
                except (TypeError, ValueError):
                    pass
            if "dominant_kind" in kwargs:
                value = kwargs["dominant_kind"]
                if value is None:
                    profile.dominant_kind = None
                else:
                    profile.dominant_kind = _resolve_enum(TensionKind, value)
            if "dominant_polarity" in kwargs:
                value = kwargs["dominant_polarity"]
                if value is None:
                    profile.dominant_polarity = None
                else:
                    profile.dominant_polarity = _resolve_enum(
                        TensionPolarity, value
                    )
            profile.last_updated = _now()
            return profile

    def list_profiles(self) -> List[TensionProfile]:
        """Return all tension profiles currently registered.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> TensionStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counters (kept in sync with the
        registries). ``state_distribution`` tallies each pair by its
        current state. ``kind_distribution`` tallies each pair by its
        kind. ``polarity_distribution`` tallies each pair by its
        polarity. The breakdown dicts are fully populated with a zero
        entry for every enum member so callers can rely on key presence,
        and are keyed by enum ``.value`` strings for JSON-friendliness.
        """
        with self._lock:
            pairs = list(self._pairs.values())

            state_dist = _empty_state_distribution()
            kind_dist = _empty_kind_distribution()
            polarity_dist = _empty_polarity_distribution()
            for pair in pairs:
                state_dist[pair.state] += 1
                kind_dist[pair.kind] += 1
                polarity_dist[pair.polarity] += 1

            return TensionStats(
                total_poles=self._stats["total_poles"],
                total_pairs=self._stats["total_pairs"],
                total_resolutions=self._stats["total_resolutions"],
                total_holdings=self._stats["total_holdings"],
                state_distribution={
                    _enum_value(TensionState, k): v
                    for k, v in state_dist.items()
                },
                kind_distribution={
                    _enum_value(TensionKind, k): v
                    for k, v in kind_dist.items()
                },
                polarity_distribution={
                    _enum_value(TensionPolarity, k): v
                    for k, v in polarity_dist.items()
                },
            )

    # ── Maintenance ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Empties every registry, resets the running counters, and drops
        all per-agent profiles. After reset the engine behaves as if
        freshly constructed.
        """
        with self._lock:
            self._poles.clear()
            self._pairs.clear()
            self._snapshots.clear()
            self._resolutions.clear()
            self._holdings.clear()
            self._profiles.clear()
            self._stats.clear()
            self._stats.update(
                {
                    "total_poles": 0,
                    "total_pairs": 0,
                    "total_resolutions": 0,
                    "total_holdings": 0,
                }
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_tension_engine() -> AgentCognitiveTension:
    """Get or create the singleton ``AgentCognitiveTension`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveTension()
        return _engine


def reset_tension_engine() -> None:
    """Reset the singleton ``AgentCognitiveTension`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_tension_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
