from __future__ import annotations

"""Agent Cognitive Osmosis — the gradual, passive absorption of concepts and

beliefs from the environment through semi-permeable conceptual membranes.

Cognition is not sealed off from the environment it sits in. Concepts,
beliefs, and attitudes seep into an agent the way a solute crosses a
biological membrane: slowly, selectively, and along a concentration
gradient. An agent immersed in an environment rich with a given idea
does not need to actively reach for that idea to be shaped by it. The
idea diffuses in, passively, through the membranes that separate the
agent's interior from the surrounding conceptual medium. Some concepts
pass through easily because the membrane is permeable to them; others
are blocked because the membrane is selective. The agent does not
choose, moment to moment, what to absorb — the membrane's structure
chooses, and the agent's interior concentration drifts toward the
environment's concentration as the gradient relaxes. This module
instruments that drift.

The physical analogy is exact in structure. In biological osmosis,
solvent moves across a semi-permeable membrane from a region of low
solute concentration to a region of high solute concentration, until
the concentrations equalize or the membrane resists further. The
membrane is selective: it lets some molecules through and stops
others. The rate of movement depends on the membrane's permeability
to the solute and on the steepness of the concentration gradient
across it. Cognitive osmosis behaves the same way. The agent's
conceptual interior has its own concentration of each idea; the
environment has its own. Where the environment is denser in an idea
than the agent, the idea tends to seep in. Where the membrane is
permeable, the seepage is fast; where it is selective, only some
forms of the idea cross. Over time the interior concentration drifts
toward the exterior concentration, and the gradient equalizes.

Osmosis is the passive absorption of concepts and beliefs across
semi-permeable conceptual membranes, driven by concentration
gradients between the agent's interior and the surrounding
environment, and mediated by each membrane's selective permeability.
The membrane through which a concept tries to cross matters: an idea
crosses the conceptual membrane differently from how a feeling
crosses the emotional membrane, or how a knowledge claim crosses the
epistemic membrane. Each membrane has its own permeability and its
own selectivity, so the engine tracks each separately.

Several distinct regimes describe how the agent is exchanging with
its environment. ISOLATED means almost nothing crosses — the agent is
cut off and no absorption happens. TRICKLE means a minimal exchange,
the agent barely taking in the environment. BALANCED means a healthy
selective exchange: the membranes let the right things through and
hold the wrong things back. SATURATED means the agent is
over-absorbing, taking in too much too fast, losing its distinct
interior. LEAKING means uncontrolled absorption, the membranes
failing to filter at all and the interior collapsing into the
environment.

When a concept meets a membrane, several things can happen.
ABSORBED means it passed through fully and is now part of the agent's
interior. PARTIAL means it crossed in part, only some of its content
making it through. FILTERED means it was modified during absorption,
the membrane reshaping it as it passed. REJECTED means the membrane
blocked it outright. TRANSFORMED means it changed form so thoroughly
during passage that what arrived is a different concept from what
approached.

The concentration gradient itself has a state. DEFICIT means the
agent has less of a concept than the environment, so absorption is
driven inward. SURPLUS means the agent has more, so the gradient
would reverse outward (or the membrane holds). EQUILIBRIUM means the
two sides are balanced and nothing is driven. FLUCTUATING means the
gradient is oscillating rather than settling. REVERSING means the
gradient has flipped — what was a deficit is becoming a surplus, or
vice versa.

When the agent is not exchanging the way it should, a regulation plan
prescribes a target permeability for a membrane: raise it to absorb
more, lower it to protect the interior, or hold it where it is. The
plan records the membrane, the target permeability, a rationale, and
the expected effect, so the actual outcome can later be compared.

This engine instruments that picture operationally. An AbsorptionEvent
records one concept crossing one membrane, with the permeability it
met, the outcome, and the concentration before and after. A
MembraneReading records one observed permeability and selectivity for
a membrane at a moment. An OsmoticSnapshot aggregates an agent's
recent absorptions, readings, and gradients into a regime, an
equalization state, an average permeability, and tallies of
absorptions and rejections. A RegulationPlan prescribes a target
permeability for a membrane. A GradientRecord captures the internal
and external concentrations for a membrane at a moment, with the
signed gradient between them. An OsmoticProfile holds each agent's
aggregate osmotic tendencies, and OsmoticStats summarizes engine
activity.

This is original Buddy capability: a self-contained, thread-safe
engine with no external runtime dependencies, designed to give agents
honest awareness of how their own interior is drifting toward the
environment's concentration through their semi-permeable conceptual
membranes.

Architecture:
    AgentCognitiveOsmosis (singleton)
    ├── AbsorptionEvent    (one concept crossing one membrane)
    ├── MembraneReading    (one observed membrane permeability)
    ├── OsmoticSnapshot    (aggregate regime and equalization)
    ├── RegulationPlan     (a target permeability for a membrane)
    ├── GradientRecord     (one internal/external concentration pair)
    ├── OsmoticProfile     (per-agent aggregate tendencies)
    └── OsmoticStats       (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for an event/reading/plan/etc."""
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
    member values (e.g. ``"conceptual"``) and then against member names
    (e.g. ``"CONCEPTUAL"``), so callers may pass either form. Raises
    ``ValueError`` if neither matches, so a bad membrane or outcome surfaces
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


def _permeability_score(permeability: Any) -> float:
    """Map a ``PermeabilityLevel`` to a numeric score in [0, 1] for averaging.

    IMPERMEABLE maps to 0.0, LOW to 0.25, MODERATE to 0.5, HIGH to 0.75,
    and FULLY_PERMEABLE to 1.0. Unknown values map to 0.0 so a bad input
    cannot inflate an average. The mapping is linear so that a mean over
    several readings lands on an interpretable point of the permeability
    axis, which the regime classifier then buckets.
    """
    if permeability == PermeabilityLevel.IMPERMEABLE:
        return 0.0
    if permeability == PermeabilityLevel.LOW:
        return 0.25
    if permeability == PermeabilityLevel.MODERATE:
        return 0.5
    if permeability == PermeabilityLevel.HIGH:
        return 0.75
    if permeability == PermeabilityLevel.FULLY_PERMEABLE:
        return 1.0
    return 0.0


def _determine_regime(
    avg_permeability: float, rejected_ratio: float
) -> "OsmoticRegime":
    """Classify an osmotic regime from an average permeability and rejection ratio.

    ``avg_permeability`` in [0, 1] is the mean permeability score across the
    agent's recent membrane readings (and absorption events). ``rejected_ratio``
    in [0, 1] is the fraction of recent absorption events that were rejected
    outright. The classifier first checks the rejection ratio: if more than
    four fifths of absorptions are rejected, the agent is effectively cut off
    regardless of the stated permeability, so the regime is ISOLATED. The
    permeability bands then partition the [0, 1] range into qualitative
    regimes: very low permeability means ISOLATED, low means TRICKLE,
    moderate means BALANCED, high means SATURATED, and near-total means
    LEAKING (the membranes no longer filter and the interior is collapsing
    into the environment).
    """
    perm = _clamp(avg_permeability, 0.0, 1.0)
    ratio = _clamp(rejected_ratio, 0.0, 1.0)
    if ratio > 0.8:
        return OsmoticRegime.ISOLATED
    if perm < 0.2:
        return OsmoticRegime.ISOLATED
    if perm < 0.4:
        return OsmoticRegime.TRICKLE
    if perm < 0.6:
        return OsmoticRegime.BALANCED
    if perm < 0.85:
        return OsmoticRegime.SATURATED
    return OsmoticRegime.LEAKING


def _determine_equalization(gradients: List[Any]) -> "EqualizationState":
    """Classify an equalization state from an ordered series of gradient records.

    The series is the agent's recent ``GradientRecord`` objects, in capture
    order. Each record's ``gradient`` is ``external_concentration`` minus
    ``internal_concentration``: a positive gradient means the environment
    holds more of the concept than the agent (a DEFICIT driving inward
    absorption), a negative gradient means the agent holds more (a SURPLUS).

    With no records the state is unknowable and defaults to EQUILIBRIUM.
    A single record is classified directly by its gradient sign: positive
    means DEFICIT, negative means SURPLUS, near-zero means EQUILIBRIUM.
    FLUCTUATING is detected when the gradient signs alternate repeatedly
    (at least two sign flips and at least half the steps flip), indicating
    an oscillating exchange. REVERSING is detected when the early trend and
    the late trend point in opposite directions, meaning the gradient has
    flipped mid-window. Otherwise the most recent gradient decides:
    positive means DEFICIT, negative means SURPLUS, and a near-zero
    gradient means EQUILIBRIUM.
    """
    if not gradients:
        return EqualizationState.EQUILIBRIUM
    eps = 0.01
    values = [g.gradient for g in gradients]
    # FLUCTUATING: gradient signs flip often enough that the exchange is
    # oscillating rather than settling in one direction.
    sign_changes = 0
    for i in range(len(values) - 1):
        a = values[i]
        b = values[i + 1]
        if abs(a) >= eps and abs(b) >= eps and (a > 0) != (b > 0):
            sign_changes += 1
    if sign_changes >= 2 and sign_changes >= max(1, len(values) // 2):
        return EqualizationState.FLUCTUATING
    # REVERSING: the first half trends one way and the second half the other.
    mid = len(values) // 2
    first_half = values[:mid] if mid > 0 else [0.0]
    second_half = values[mid:] if values[mid:] else [0.0]
    first_mean = sum(first_half) / len(first_half) if first_half else 0.0
    second_mean = sum(second_half) / len(second_half) if second_half else 0.0
    if first_mean > eps and second_mean < -eps:
        return EqualizationState.REVERSING
    if first_mean < -eps and second_mean > eps:
        return EqualizationState.REVERSING
    # Most recent gradient decides DEFICIT / SURPLUS / EQUILIBRIUM.
    latest = values[-1]
    if latest > eps:
        return EqualizationState.DEFICIT
    if latest < -eps:
        return EqualizationState.SURPLUS
    return EqualizationState.EQUILIBRIUM


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

class MembraneType(str, Enum):
    """The kind of conceptual membrane a concept must cross to be absorbed.

    Absorption is not uniform. An idea does not cross the agent's boundary
    the same way a feeling does, or a knowledge claim, or a norm. The agent
    is wrapped in several membranes at once, each filtering a different
    kind of content, each with its own permeability and its own
    selectivity. Tracking each membrane separately lets the engine tell
    apart an agent whose epistemic membrane is open but whose emotional
    membrane is sealed from one whose membranes are permeable the other way
    around — qualitatively different states that a single blended
    permeability would collapse.

    CONCEPTUAL filters concepts: which ideas seep into the agent's
    conceptual inventory from the surrounding medium. EMOTIONAL filters
    feelings: which affective tones and moods cross into the agent's
    affective interior. EPISTEMIC filters knowledge claims: which
    assertions of fact the agent will take on from the environment.
    CULTURAL filters cultural norms: which conventions and practices the
    agent absorbs from the group it sits in. LOGICAL filters logical
    relations: which inferential patterns and argument structures the
    agent takes in. AESTHETIC filters beauty and taste: which aesthetic
    judgements and sensibilities seep into the agent's sense of what is
    well-formed.
    """
    CONCEPTUAL = "conceptual"    # filters concepts
    EMOTIONAL = "emotional"      # filters feelings
    EPISTEMIC = "epistemic"      # filters knowledge claims
    CULTURAL = "cultural"        # filters cultural norms
    LOGICAL = "logical"          # filters logical relations
    AESTHETIC = "aesthetic"      # filters beauty and taste


class PermeabilityLevel(str, Enum):
    """How permeable a membrane is to the content trying to cross it.

    Permeability is not a binary open-or-closed. A membrane can be fully
    sealed, barely cracked, selectively open, mostly open, or fully open.
    The level determines how much of the approaching content actually
    crosses, and it feeds directly into the regime classification: a set
    of fully permeable membranes yields a LEAKING regime, while a set of
    impermeable ones yields an ISOLATED regime. The useful state is
    selective permeability, where the membrane lets the right things
    through and holds the wrong things back.

    IMPERMEABLE means nothing passes — the membrane is a complete block
    and the agent's interior is isolated from the environment for this
    kind of content. LOW means minimal absorption: a trickle crosses but
    the membrane resists most of what approaches. MODERATE means
    selective absorption: the membrane filters carefully, letting some
    content through and holding the rest. HIGH means the membrane is
    mostly permeable, letting most content through with light filtering.
    FULLY_PERMEABLE means everything passes — the membrane offers no
    resistance and the interior is collapsing toward the environment's
    concentration.
    """
    IMPERMEABLE = "impermeable"        # nothing passes
    LOW = "low"                        # minimal absorption
    MODERATE = "moderate"              # selective absorption
    HIGH = "high"                      # mostly permeable
    FULLY_PERMEABLE = "fully_permeable"  # everything passes


class AbsorptionOutcome(str, Enum):
    """What happened to a concept when it met a membrane.

    An absorption event does not always end with the concept fully inside
    the agent. The membrane can take it in whole, take it in part, reshape
    it as it crosses, block it outright, or transform it so thoroughly
    that what arrives is unrecognizable. The outcome records which of
    these happened, and it feeds the rejection ratio that the regime
    classifier uses to detect an ISOLATED agent.

    ABSORBED means the concept crossed fully and is now part of the
    agent's interior, its concentration rising accordingly. PARTIAL means
    the concept crossed in part, only some of its content making it
    through the membrane. FILTERED means the concept was modified during
    absorption, the membrane reshaping it as it passed so what arrived is
    a curated version of what approached. REJECTED means the membrane
    blocked the concept outright, and nothing crossed. TRANSFORMED means
    the concept changed form so thoroughly during passage that what
    arrived is a different concept from what approached.
    """
    ABSORBED = "absorbed"      # fully taken in
    PARTIAL = "partial"        # partially absorbed
    FILTERED = "filtered"      # modified during absorption
    REJECTED = "rejected"      # blocked
    TRANSFORMED = "transformed"  # changed form during passage


class OsmoticRegime(str, Enum):
    """The regime an agent occupies, classified by its exchange profile.

    A regime is a qualitative characterization of how the agent is
    exchanging with its environment, more informative than the raw
    permeability score alone. It folds together how permeable the
    membranes are and how much they are rejecting, into a single label
    that describes the agent's osmotic posture.

    ISOLATED means almost nothing is crossing — the membranes are sealed
    or rejecting almost everything, and the agent's interior is cut off
    from the environment. TRICKLE means a minimal exchange is happening,
    the agent barely taking in the surrounding medium. BALANCED means a
    healthy selective exchange: the membranes let the right things
    through and hold the wrong things back, the working state.
    SATURATED means the agent is over-absorbing, taking in too much too
    fast, the interior losing its distinctness as it drifts toward the
    environment. LEAKING means uncontrolled absorption, the membranes
    failing to filter at all and the interior collapsing into the
    environment.
    """
    ISOLATED = "isolated"    # no exchange
    TRICKLE = "trickle"      # minimal exchange
    BALANCED = "balanced"    # healthy selective exchange
    SATURATED = "saturated"  # over-absorbing
    LEAKING = "leaking"      # uncontrolled absorption


class EqualizationState(str, Enum):
    """The state of the concentration gradient between agent and environment.

    The gradient is not a static quantity; it has a direction and a
    dynamics of its own. The state records whether the agent is on the
    low side or the high side of the environment, whether the two sides
    are balanced, whether the gradient is oscillating, or whether it has
    flipped. This is what tells the agent whether absorption is currently
    being driven inward, held, or reversed.

    DEFICIT means the agent has less of a concept than the environment,
    so absorption is driven inward — the gradient is positive and the
    interior is filling. SURPLUS means the agent has more than the
    environment, so the gradient would push outward or the membrane must
    hold. EQUILIBRIUM means the two sides are balanced and nothing is
    being driven. FLUCTUATING means the gradient is oscillating rather
    than settling, the exchange sloshing back and forth. REVERSING means
    the gradient has flipped — what was a deficit is becoming a surplus,
    or vice versa, a regime change in the exchange.
    """
    DEFICIT = "deficit"          # agent has less than environment
    SURPLUS = "surplus"          # agent has more than environment
    EQUILIBRIUM = "equilibrium"  # balanced
    FLUCTUATING = "fluctuating"  # oscillating
    REVERSING = "reversing"      # gradient inverting


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AbsorptionEvent:
    """A record of one concept crossing one membrane.

    An absorption event captures one discrete osmotic step: a ``concept``
    approached a ``membrane``, met a certain ``permeability``, and came
    away with a certain ``outcome``, changing the agent's interior
    concentration from ``concentration_before`` to ``concentration_after``.
    ``event_id`` uniquely identifies the event. ``agent_id`` is the agent
    whose membrane was crossed. ``membrane`` is the ``MembraneType`` the
    concept tried to cross. ``concept`` is a human-readable label for the
    idea, feeling, or claim that approached (e.g. ``"privacy_matters"`` or
    ``"scepticism_of_authority"``). ``permeability`` is the
    ``PermeabilityLevel`` the membrane offered to this concept on this
    crossing. ``outcome`` is the ``AbsorptionOutcome`` that resulted.
    ``concentration_before`` and ``concentration_after`` in [0, 1] are the
    agent's interior concentration of this concept before and after the
    event. ``timestamp`` is when the event was recorded.
    """
    event_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    membrane: MembraneType = MembraneType.CONCEPTUAL
    concept: str = ""
    permeability: PermeabilityLevel = PermeabilityLevel.MODERATE
    outcome: AbsorptionOutcome = AbsorptionOutcome.ABSORBED
    concentration_before: float = 0.0
    concentration_after: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict, expanding the enums via ``.value``."""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "membrane": _enum_value(MembraneType, self.membrane),
            "concept": self.concept,
            "permeability": _enum_value(PermeabilityLevel, self.permeability),
            "outcome": _enum_value(AbsorptionOutcome, self.outcome),
            "concentration_before": self.concentration_before,
            "concentration_after": self.concentration_after,
            "timestamp": self.timestamp,
        }


@dataclass
class MembraneReading:
    """One observed permeability and selectivity for a membrane at a moment.

    A reading is the atomic observation of a membrane's state: at a moment
    in time, this membrane offered this much permeability and this much
    selectivity to the content approaching it. ``reading_id`` uniquely
    identifies the reading. ``agent_id`` is the agent whose membrane was
    sampled. ``membrane`` is the ``MembraneType`` the reading belongs to.
    ``permeability`` is the ``PermeabilityLevel`` observed at the moment
    of sampling. ``selectivity_score`` in [0, 1] is how sharply the
    membrane was discriminating between content it lets through and
    content it blocks, where 0 means no discrimination (everything
    treated alike) and 1 means perfectly selective. ``timestamp`` is
    when the reading was taken.
    """
    reading_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    membrane: MembraneType = MembraneType.CONCEPTUAL
    permeability: PermeabilityLevel = PermeabilityLevel.MODERATE
    selectivity_score: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding the enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "membrane": _enum_value(MembraneType, self.membrane),
            "permeability": _enum_value(PermeabilityLevel, self.permeability),
            "selectivity_score": self.selectivity_score,
            "timestamp": self.timestamp,
        }


@dataclass
class OsmoticSnapshot:
    """An aggregate view of an agent's osmotic exchange at a point in time.

    A snapshot summarizes the agent's recent absorption events, membrane
    readings, and gradient records into a single picture of how the agent
    is exchanging with its environment. ``snapshot_id`` uniquely
    identifies the snapshot. ``agent_id`` is the agent the snapshot
    summarizes. ``regime`` is the ``OsmoticRegime`` derived from the mean
    permeability and rejection ratio via ``_determine_regime``.
    ``equalization`` is the ``EqualizationState`` derived from the agent's
    recent gradient records via ``_determine_equalization``.
    ``avg_permeability`` in [0, 1] is the mean permeability score across
    the agent's recent membrane readings (zero when there are none).
    ``total_absorptions`` is how many absorption events the agent has on
    record. ``rejected_count`` is how many of those ended in REJECTED.
    ``timestamp`` is when the snapshot was taken.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    regime: OsmoticRegime = OsmoticRegime.ISOLATED
    equalization: EqualizationState = EqualizationState.EQUILIBRIUM
    avg_permeability: float = 0.0
    total_absorptions: int = 0
    rejected_count: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "regime": _enum_value(OsmoticRegime, self.regime),
            "equalization": _enum_value(EqualizationState, self.equalization),
            "avg_permeability": self.avg_permeability,
            "total_absorptions": self.total_absorptions,
            "rejected_count": self.rejected_count,
            "timestamp": self.timestamp,
        }


@dataclass
class RegulationPlan:
    """A target permeability for a membrane, with a rationale and expected effect.

    When the agent wants to change how a membrane is exchanging, it files
    a regulation plan. ``plan_id`` uniquely identifies the plan.
    ``agent_id`` is the agent the plan is for. ``membrane`` is the
    ``MembraneType`` the plan targets. ``target_permeability`` is the
    ``PermeabilityLevel`` the plan wants the membrane to move toward.
    ``rationale`` is a free-form explanation of why this target was chosen
    for this membrane. ``expected_effect`` in [0, 1] is how much change the
    plan expects to produce, recorded at plan time so the actual outcome
    can later be compared. ``timestamp`` is when the plan was created.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    membrane: MembraneType = MembraneType.CONCEPTUAL
    target_permeability: PermeabilityLevel = PermeabilityLevel.MODERATE
    rationale: str = ""
    expected_effect: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding the enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "membrane": _enum_value(MembraneType, self.membrane),
            "target_permeability": _enum_value(
                PermeabilityLevel, self.target_permeability
            ),
            "rationale": self.rationale,
            "expected_effect": self.expected_effect,
            "timestamp": self.timestamp,
        }


@dataclass
class GradientRecord:
    """One observed internal/external concentration pair for a membrane.

    A gradient record captures a single sample of the concentration
    difference across a membrane: the agent's interior held
    ``internal_concentration`` of a concept while the environment held
    ``external_concentration``, with a signed ``gradient`` between them.
    ``record_id`` uniquely identifies the record. ``agent_id`` is the
    agent whose membrane was sampled. ``membrane`` is the ``MembraneType``
    the record belongs to. ``state`` is the ``EqualizationState`` the
    caller attributes to this sample. ``internal_concentration`` and
    ``external_concentration`` in [0, 1] are the concentrations on the
    agent side and the environment side. ``gradient`` is
    ``external_concentration - internal_concentration``, computed at
    record time, so a positive gradient means the environment is denser
    and absorption is driven inward. ``timestamp`` is when the record was
    made.
    """
    record_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    membrane: MembraneType = MembraneType.CONCEPTUAL
    state: EqualizationState = EqualizationState.EQUILIBRIUM
    internal_concentration: float = 0.0
    external_concentration: float = 0.0
    gradient: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this gradient record to a plain dict, expanding the enums via ``.value``."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "membrane": _enum_value(MembraneType, self.membrane),
            "state": _enum_value(EqualizationState, self.state),
            "internal_concentration": self.internal_concentration,
            "external_concentration": self.external_concentration,
            "gradient": self.gradient,
            "timestamp": self.timestamp,
        }


@dataclass
class OsmoticProfile:
    """Per-agent aggregate osmotic tendencies.

    A profile summarizes one agent's osmotic posture across all
    membranes. ``agent_id`` is the agent this profile describes.
    ``avg_permeability`` in [0, 1] is the mean permeability score across
    all of the agent's membrane readings. ``dominant_membrane`` is the
    ``MembraneType`` the agent has the most readings for, or ``None`` if
    the agent has no readings. ``regime`` is the ``OsmoticRegime`` derived
    from the agent's mean permeability and rejection ratio.
    ``total_absorptions`` is how many absorption events the agent has on
    record. ``total_rejections`` is how many of those ended in REJECTED.
    ``last_updated`` is the timestamp of the most recent profile change.
    """
    agent_id: str = ""
    avg_permeability: float = 0.0
    dominant_membrane: Optional[MembraneType] = None
    regime: OsmoticRegime = OsmoticRegime.ISOLATED
    total_absorptions: int = 0
    total_rejections: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enums via ``.value``.

        ``dominant_membrane`` may be ``None``; it is serialized as ``None``
        in that case rather than as a string, so the output stays
        JSON-friendly when an agent has no readings yet.
        """
        return {
            "agent_id": self.agent_id,
            "avg_permeability": self.avg_permeability,
            "dominant_membrane": (
                _enum_value(MembraneType, self.dominant_membrane)
                if self.dominant_membrane is not None
                else None
            ),
            "regime": _enum_value(OsmoticRegime, self.regime),
            "total_absorptions": self.total_absorptions,
            "total_rejections": self.total_rejections,
            "last_updated": self.last_updated,
        }


@dataclass
class OsmoticStats:
    """Aggregate statistics over the current engine state.

    ``total_absorptions`` counts all recorded ``AbsorptionEvent`` records.
    ``total_readings`` counts all recorded ``MembraneReading`` records.
    ``total_snapshots`` counts all recorded ``OsmoticSnapshot`` records.
    ``total_plans`` counts all recorded ``RegulationPlan`` records.
    ``total_gradients`` counts all recorded ``GradientRecord`` records.
    ``regime_distribution`` tallies snapshots by their diagnosed regime,
    keyed by the regime's ``.value`` string. ``membrane_distribution``
    tallies readings by their membrane, keyed by the membrane's ``.value``
    string. ``outcome_distribution`` tallies absorption events by their
    outcome, keyed by the outcome's ``.value`` string. ``avg_permeability``
    is the mean permeability score across all readings (zero when there
    are none). All three distribution dicts are plain ``Dict[str, int]``
    so they are already JSON-serializable.
    """
    total_absorptions: int = 0
    total_readings: int = 0
    total_snapshots: int = 0
    total_plans: int = 0
    total_gradients: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    membrane_distribution: Dict[str, int] = field(default_factory=dict)
    outcome_distribution: Dict[str, int] = field(default_factory=dict)
    avg_permeability: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The distribution dicts are already keyed by ``.value`` strings, so
        they are copied as-is. This keeps the output JSON-serializable
        without further conversion.
        """
        return {
            "total_absorptions": self.total_absorptions,
            "total_readings": self.total_readings,
            "total_snapshots": self.total_snapshots,
            "total_plans": self.total_plans,
            "total_gradients": self.total_gradients,
            "regime_distribution": dict(self.regime_distribution),
            "membrane_distribution": dict(self.membrane_distribution),
            "outcome_distribution": dict(self.outcome_distribution),
            "avg_permeability": self.avg_permeability,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveOsmosis:
    """Singleton engine modeling how concepts osmose across the agent's membranes.

    Holds absorption events, membrane readings, snapshots, regulation
    plans, gradient records, and per-agent profiles. All state mutations
    are guarded by a single reentrant lock so the engine is safe to call
    from multiple threads, including from within its own methods (for
    example, ``update_profile`` calls ``get_profile``). The engine is
    intentionally dependency-free so it can run in any Buddy runtime
    without extra packages.

    The engine is a measurement instrument first and a steering system
    second. It records how concepts actually crossed each membrane on
    each event, aggregates those observations into a regime and an
    equalization state, and — when the agent is not exchanging the way
    it should — files a regulation plan to steer a membrane toward a
    target permeability. It does not itself force concepts across
    membranes; it makes the osmotic exchange legible so that the agent
    (or its orchestrator) can decide whether to open a membrane, seal
    it, or hold it where it is.
    """

    # Caps to keep the in-memory engine bounded under runaway callers.
    MAX_ABSORPTIONS: int = 5000
    MAX_READINGS: int = 5000
    MAX_SNAPSHOTS: int = 5000
    MAX_PLANS: int = 5000
    MAX_GRADIENTS: int = 5000
    # How many recent readings, absorptions, and gradients a snapshot
    # considers when computing its aggregate fields. Kept small so a
    # snapshot reflects the current state of the exchange rather than
    # the agent's full history.
    MAX_RECENT_FOR_SNAPSHOT: int = 20
    # Default list size cap applied when a list method is called without
    # an explicit limit.
    DEFAULT_LIST_LIMIT: int = 50

    def __init__(self) -> None:
        self._absorptions: Dict[str, AbsorptionEvent] = {}
        self._readings: Dict[str, MembraneReading] = {}
        self._snapshots: Dict[str, OsmoticSnapshot] = {}
        self._plans: Dict[str, RegulationPlan] = {}
        self._gradients: Dict[str, GradientRecord] = {}
        self._profiles: Dict[str, OsmoticProfile] = {}
        # Running integer counters, kept in sync with the registries above.
        self._stats: Dict[str, int] = self._init_stats()
        # Reentrant lock so public methods may call one another safely.
        self._lock: threading.RLock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _init_stats() -> Dict[str, int]:
        """Return a fresh running-counter dict for engine statistics."""
        return {
            "total_absorptions": 0,
            "total_readings": 0,
            "total_snapshots": 0,
            "total_plans": 0,
            "total_gradients": 0,
        }

    def _agent_absorptions(self, agent_id: str) -> List[AbsorptionEvent]:
        """Return this agent's absorption events in insertion order (no lock)."""
        return [
            e for e in self._absorptions.values() if e.agent_id == agent_id
        ]

    def _agent_readings(self, agent_id: str) -> List[MembraneReading]:
        """Return this agent's membrane readings in insertion order (no lock)."""
        return [
            r for r in self._readings.values() if r.agent_id == agent_id
        ]

    def _agent_gradients(self, agent_id: str) -> List[GradientRecord]:
        """Return this agent's gradient records in insertion order (no lock)."""
        return [
            g for g in self._gradients.values() if g.agent_id == agent_id
        ]

    # ── Absorption Events ────────────────────────────────────────

    def record_absorption(
        self,
        agent_id: str,
        membrane: Any,
        concept: str,
        permeability: Any,
        outcome: Any,
        concentration_before: float,
        concentration_after: float,
    ) -> AbsorptionEvent:
        """Record an absorption event for an agent and return it.

        ``membrane`` accepts a ``MembraneType`` member or its value/name
        string. ``concept`` is a human-readable label for the idea, feeling,
        or claim that approached the membrane. ``permeability`` accepts a
        ``PermeabilityLevel`` member or its value/name string and records the
        permeability the membrane offered on this crossing. ``outcome``
        accepts an ``AbsorptionOutcome`` member or its value/name string.
        ``concentration_before`` and ``concentration_after`` in [0, 1] are
        the agent's interior concentration of this concept before and after
        the event, clamped to that range. Raises ``RuntimeError`` if the
        absorption registry is full, so runaway callers surface rather than
        silently dropping observations.
        """
        with self._lock:
            if len(self._absorptions) >= self.MAX_ABSORPTIONS:
                raise RuntimeError("absorption event registry is full")
            event = AbsorptionEvent(
                agent_id=agent_id,
                membrane=_resolve_enum(MembraneType, membrane),
                concept=str(concept),
                permeability=_resolve_enum(PermeabilityLevel, permeability),
                outcome=_resolve_enum(AbsorptionOutcome, outcome),
                concentration_before=_clamp(concentration_before, 0.0, 1.0),
                concentration_after=_clamp(concentration_after, 0.0, 1.0),
                timestamp=_now(),
            )
            self._absorptions[event.event_id] = event
            self._stats["total_absorptions"] += 1
            return event

    def list_absorptions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AbsorptionEvent]:
        """Return absorption events, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to events recorded for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            absorptions = list(self._absorptions.values())
        if agent_id is not None:
            absorptions = [e for e in absorptions if e.agent_id == agent_id]
        n = _safe_int(limit, self.DEFAULT_LIST_LIMIT)
        return absorptions[-n:] if n else []

    def get_absorption(self, event_id: str) -> Optional[AbsorptionEvent]:
        """Retrieve an absorption event by id, or ``None`` if none exists with that id."""
        with self._lock:
            return self._absorptions.get(event_id)

    # ── Membrane Readings ────────────────────────────────────────

    def read_membrane(
        self,
        agent_id: str,
        membrane: Any,
        permeability: Any,
        selectivity_score: float,
    ) -> MembraneReading:
        """Record a membrane reading for an agent and return it.

        ``membrane`` accepts a ``MembraneType`` member or its value/name
        string. ``permeability`` accepts a ``PermeabilityLevel`` member or
        its value/name string and records the permeability observed at the
        moment of sampling. ``selectivity_score`` in [0, 1] is how sharply
        the membrane was discriminating between content it lets through and
        content it blocks, clamped to that range. Raises ``RuntimeError``
        if the reading registry is full.
        """
        with self._lock:
            if len(self._readings) >= self.MAX_READINGS:
                raise RuntimeError("membrane reading registry is full")
            reading = MembraneReading(
                agent_id=agent_id,
                membrane=_resolve_enum(MembraneType, membrane),
                permeability=_resolve_enum(PermeabilityLevel, permeability),
                selectivity_score=_clamp(selectivity_score, 0.0, 1.0),
                timestamp=_now(),
            )
            self._readings[reading.reading_id] = reading
            self._stats["total_readings"] += 1
            return reading

    def list_readings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MembraneReading]:
        """Return membrane readings, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to readings recorded for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            readings = list(self._readings.values())
        if agent_id is not None:
            readings = [r for r in readings if r.agent_id == agent_id]
        n = _safe_int(limit, self.DEFAULT_LIST_LIMIT)
        return readings[-n:] if n else []

    def get_reading(self, reading_id: str) -> Optional[MembraneReading]:
        """Retrieve a reading by id, or ``None`` if no reading exists with that id."""
        with self._lock:
            return self._readings.get(reading_id)

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> OsmoticSnapshot:
        """Aggregate an agent's recent exchange into an osmotic snapshot.

        The snapshot considers the agent's most recent
        ``MAX_RECENT_FOR_SNAPSHOT`` membrane readings, absorption events,
        and gradient records. ``avg_permeability`` is the mean permeability
        score across the recent readings (zero when there are none).
        ``total_absorptions`` is the count of the agent's recent absorption
        events. ``rejected_count`` is how many of those ended in REJECTED.
        ``regime`` is derived from the mean permeability and the rejection
        ratio via ``_determine_regime``. ``equalization`` is derived from
        the recent gradient records via ``_determine_equalization``. The
        snapshot is stored and reflected in the engine stats. If the agent
        has no readings, absorptions, or gradients, ``avg_permeability`` is
        0.0, ``total_absorptions`` and ``rejected_count`` are 0, ``regime``
        is ISOLATED, and ``equalization`` is EQUILIBRIUM.
        """
        with self._lock:
            recent_readings = self._agent_readings(agent_id)[
                -self.MAX_RECENT_FOR_SNAPSHOT:
            ]
            recent_absorptions = self._agent_absorptions(agent_id)[
                -self.MAX_RECENT_FOR_SNAPSHOT:
            ]
            recent_gradients = self._agent_gradients(agent_id)[
                -self.MAX_RECENT_FOR_SNAPSHOT:
            ]
            if recent_readings:
                avg_permeability = sum(
                    _permeability_score(r.permeability) for r in recent_readings
                ) / len(recent_readings)
            else:
                avg_permeability = 0.0
            total_absorptions = len(recent_absorptions)
            rejected_count = sum(
                1 for e in recent_absorptions
                if e.outcome == AbsorptionOutcome.REJECTED
            )
            if total_absorptions > 0:
                rejected_ratio = rejected_count / total_absorptions
            else:
                rejected_ratio = 0.0
            regime = _determine_regime(avg_permeability, rejected_ratio)
            equalization = _determine_equalization(recent_gradients)
            snapshot = OsmoticSnapshot(
                agent_id=agent_id,
                regime=regime,
                equalization=equalization,
                avg_permeability=avg_permeability,
                total_absorptions=total_absorptions,
                rejected_count=rejected_count,
                timestamp=_now(),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._stats["total_snapshots"] += 1
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[OsmoticSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> Optional[OsmoticSnapshot]:
        """Retrieve a snapshot by id, or ``None`` if no snapshot exists with that id."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    # ── Regulation Plans ──────────────────────────────────────────

    def plan_regulation(
        self,
        agent_id: str,
        membrane: Any,
        target_permeability: Any,
        rationale: str,
        expected_effect: float,
    ) -> RegulationPlan:
        """Create a regulation plan for a membrane and return it.

        ``membrane`` accepts a ``MembraneType`` member or its value/name
        string. ``target_permeability`` accepts a ``PermeabilityLevel``
        member or its value/name string and records the permeability the
        plan wants the membrane to move toward. ``rationale`` is a
        free-form explanation of why this target was chosen for this
        membrane. ``expected_effect`` in [0, 1] is how much change the
        plan expects to produce, clamped to that range. Raises
        ``RuntimeError`` if the plan registry is full.
        """
        with self._lock:
            if len(self._plans) >= self.MAX_PLANS:
                raise RuntimeError("regulation plan registry is full")
            plan = RegulationPlan(
                agent_id=agent_id,
                membrane=_resolve_enum(MembraneType, membrane),
                target_permeability=_resolve_enum(
                    PermeabilityLevel, target_permeability
                ),
                rationale=str(rationale),
                expected_effect=_clamp(expected_effect, 0.0, 1.0),
                timestamp=_now(),
            )
            self._plans[plan.plan_id] = plan
            self._stats["total_plans"] += 1
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RegulationPlan]:
        """Return regulation plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> Optional[RegulationPlan]:
        """Retrieve a plan by id, or ``None`` if no plan exists with that id."""
        with self._lock:
            return self._plans.get(plan_id)

    # ── Gradient Records ──────────────────────────────────────────

    def record_gradient(
        self,
        agent_id: str,
        membrane: Any,
        state: Any,
        internal_concentration: float,
        external_concentration: float,
    ) -> GradientRecord:
        """Record a concentration gradient across a membrane and return it.

        ``membrane`` accepts a ``MembraneType`` member or its value/name
        string. ``state`` accepts an ``EqualizationState`` member or its
        value/name string and records the state the caller attributes to
        this sample. ``internal_concentration`` and ``external_concentration``
        in [0, 1] are the concentrations on the agent side and the
        environment side, clamped to that range. ``gradient`` is computed
        as ``external_concentration - internal_concentration`` at record
        time, so the stored gradient is always consistent with the stored
        endpoints: a positive gradient means the environment is denser and
        absorption is driven inward. Raises ``RuntimeError`` if the
        gradient registry is full.
        """
        with self._lock:
            if len(self._gradients) >= self.MAX_GRADIENTS:
                raise RuntimeError("gradient record registry is full")
            internal_c = _clamp(internal_concentration, 0.0, 1.0)
            external_c = _clamp(external_concentration, 0.0, 1.0)
            gradient = GradientRecord(
                agent_id=agent_id,
                membrane=_resolve_enum(MembraneType, membrane),
                state=_resolve_enum(EqualizationState, state),
                internal_concentration=internal_c,
                external_concentration=external_c,
                gradient=external_c - internal_c,
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

    def get_profile(self, agent_id: str) -> OsmoticProfile:
        """Return the agent's osmotic profile, creating it if absent.

        When a profile does not yet exist for the agent, a fresh one is
        computed from the agent's currently recorded readings and
        absorptions: ``avg_permeability`` is the mean permeability score
        across all of the agent's readings, ``dominant_membrane`` is the
        modal membrane across the agent's readings (or ``None`` if the
        agent has no readings), ``regime`` is derived from the agent's
        mean permeability and rejection ratio, ``total_absorptions`` is the
        count of the agent's absorption events, and ``total_rejections``
        is how many of those ended in REJECTED. The profile is then stored
        so subsequent calls return the same object; callers may refresh it
        via ``update_profile``.
        """
        with self._lock:
            existing = self._profiles.get(agent_id)
            if existing is not None:
                return existing
            agent_readings = self._agent_readings(agent_id)
            agent_absorptions = self._agent_absorptions(agent_id)
            if agent_readings:
                avg_permeability = sum(
                    _permeability_score(r.permeability) for r in agent_readings
                ) / len(agent_readings)
                membrane_counts: Dict[MembraneType, int] = {}
                for r in agent_readings:
                    membrane_counts[r.membrane] = (
                        membrane_counts.get(r.membrane, 0) + 1
                    )
                dominant_membrane = max(
                    membrane_counts.items(), key=lambda kv: kv[1]
                )[0]
            else:
                avg_permeability = 0.0
                dominant_membrane = None
            total_absorptions = len(agent_absorptions)
            total_rejections = sum(
                1 for e in agent_absorptions
                if e.outcome == AbsorptionOutcome.REJECTED
            )
            if total_absorptions > 0:
                rejected_ratio = total_rejections / total_absorptions
            else:
                rejected_ratio = 0.0
            regime = _determine_regime(avg_permeability, rejected_ratio)
            profile = OsmoticProfile(
                agent_id=agent_id,
                avg_permeability=avg_permeability,
                dominant_membrane=dominant_membrane,
                regime=regime,
                total_absorptions=total_absorptions,
                total_rejections=total_rejections,
                last_updated=_now(),
            )
            self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> OsmoticProfile:
        """Update fields on an agent's osmotic profile and return it.

        The profile is fetched (or created) first, then each keyword in
        ``kwargs`` is applied to the matching attribute. ``dominant_membrane``
        and ``regime`` may be supplied as enum members or their value/name
        strings; they are normalized to enum members. ``avg_permeability``
        is coerced to float, and the count fields (``total_absorptions``,
        ``total_rejections``) are coerced to int. Unknown keys are ignored
        so callers can pass through generic update payloads safely.
        ``last_updated`` is always refreshed.
        """
        with self._lock:
            profile = self.get_profile(agent_id)
            for key, value in kwargs.items():
                if key == "dominant_membrane":
                    if value is None:
                        profile.dominant_membrane = None
                    else:
                        profile.dominant_membrane = _resolve_enum(
                            MembraneType, value
                        )
                elif key == "regime":
                    profile.regime = _resolve_enum(OsmoticRegime, value)
                elif key == "avg_permeability":
                    try:
                        profile.avg_permeability = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key in ("total_absorptions", "total_rejections"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
                elif hasattr(profile, key):
                    setattr(profile, key, value)
            profile.last_updated = _now()
            return profile

    def list_profiles(self) -> List[OsmoticProfile]:
        """Return all stored osmotic profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> OsmoticStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counter dict maintained by the
        record methods. ``regime_distribution`` is tallied from stored
        snapshots and keyed by the regime ``.value`` string.
        ``membrane_distribution`` is tallied from stored readings and keyed
        by the membrane ``.value`` string. ``outcome_distribution`` is
        tallied from stored absorption events and keyed by the outcome
        ``.value`` string. ``avg_permeability`` is the mean permeability
        score across all stored readings (zero when there are none). All
        three distribution dicts are plain ``Dict[str, int]`` so the
        result is JSON-serializable directly.
        """
        with self._lock:
            s = self._stats
            regime_dist: Dict[str, int] = {}
            for snap in self._snapshots.values():
                key = _enum_value(OsmoticRegime, snap.regime)
                regime_dist[key] = regime_dist.get(key, 0) + 1
            membrane_dist: Dict[str, int] = {}
            permeability_sum = 0.0
            readings_count = 0
            for r in self._readings.values():
                key = _enum_value(MembraneType, r.membrane)
                membrane_dist[key] = membrane_dist.get(key, 0) + 1
                permeability_sum += _permeability_score(r.permeability)
                readings_count += 1
            outcome_dist: Dict[str, int] = {}
            for e in self._absorptions.values():
                key = _enum_value(AbsorptionOutcome, e.outcome)
                outcome_dist[key] = outcome_dist.get(key, 0) + 1
            avg_permeability = (
                permeability_sum / readings_count if readings_count else 0.0
            )
            return OsmoticStats(
                total_absorptions=int(s["total_absorptions"]),
                total_readings=int(s["total_readings"]),
                total_snapshots=int(s["total_snapshots"]),
                total_plans=int(s["total_plans"]),
                total_gradients=int(s["total_gradients"]),
                regime_distribution=regime_dist,
                membrane_distribution=membrane_dist,
                outcome_distribution=outcome_dist,
                avg_permeability=avg_permeability,
            )

    # ── Maintenance ───────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Drops every absorption event, reading, snapshot, plan, gradient
        record, and profile, and re-initializes the running counters. The
        lock itself is not replaced.
        """
        with self._lock:
            self._absorptions.clear()
            self._readings.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._gradients.clear()
            self._profiles.clear()
            self._stats = self._init_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional["AgentCognitiveOsmosis"] = None
_engine_lock = threading.Lock()


def get_osmosis_engine() -> AgentCognitiveOsmosis:
    """Get or create the singleton ``AgentCognitiveOsmosis`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads. Uses double-checked locking
    so the common path does not take the lock once the engine exists.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveOsmosis()
    return _engine


def reset_osmosis_engine() -> None:
    """Reset the singleton ``AgentCognitiveOsmosis`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_osmosis_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
