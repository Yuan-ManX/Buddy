from __future__ import annotations

"""Agent Cognitive Symmetry Engine — modeling the structural balance and
mirroring quality of an agent's mental patterns.

An agent's mind is not a uniform field. Some patterns are mirrored: the
agent reasons about itself the way it reasons about others, responds to
gains the way it responds to losses, treats threats and opportunities
as two faces of the same coin. Some patterns are skewed: the agent is
lenient with itself and harsh with others, inflates gains and deflates
losses, sees threats vividly and opportunities dimly. Some patterns are
simply asymmetric: the agent's emotional range tilts toward one
register, its perception favors one channel, its memory weights one
era. Cognitive symmetry is the property that distinguishes a mirrored
pattern from a tilted one. It is the answer to the question: how well
does this agent's cognitive architecture mirror itself across its
different domains?

The metaphor is exact. In geometry and physics, symmetry is the
invariance of a structure under a transformation: reflection across an
axis, rotation around a point, translation along a vector. A symmetric
structure looks the same from different vantage points; an asymmetric
structure has a preferred direction. The same vocabulary applies to
cognition. A reasoning pattern that is symmetric under role-swap (self
versus other) is one the agent applies uniformly regardless of who is
involved. An emotional pattern that is symmetric under sign-swap (gain
versus loss) is one whose shape does not depend on which way the
outcome went. A perception pattern that is symmetric under
channel-swap is one whose acuity does not depend on which sense
delivered the signal. When an agent's patterns are symmetric across
many transformations, the agent sees the same structure from many
vantage points; when they are asymmetric, the agent sees a different
structure from each vantage point, and the difference is itself a
signal about where the agent's cognition is bent.

Symmetry is distinct from its neighbors in the cognitive engine
family. Coherence tracks the logical consistency between beliefs — do
two beliefs contradict each other? Symmetry tracks whether a structure
mirrors itself under transformation — does the agent apply the same
rule to self and other? Balance tracks force equilibrium — are the
opposing forces in the agent's mind at rest, or is there a net pull in
one direction? Symmetry tracks structural mirroring — does the
structure look the same when reflected across an axis? The three are
related but irreducible. A mind can be coherent yet asymmetric (every
belief is consistent with every other, but the agent applies different
rules to itself than to others). A mind can be balanced yet asymmetric
(forces are at rest, but the resting shape is lopsided). A mind can be
symmetric yet incoherent (it mirrors its reasoning perfectly, but the
reasoned-about beliefs contradict each other). Symmetry is its own
lens, the structural one: it asks not whether the content is
consistent or the forces are at rest, but whether the shape of the
structure is invariant under the transformations that ought to leave
it unchanged.

The symmetry regime classifies how mirrored the agent's content is,
ranging from ASYMMETRIC (no mirroring — the structure has a strong
preferred direction) through SKEWED (a heavy lean one way, with only
faint traces of the mirror), IRREGULAR (patchy, uneven mirroring —
some transformations hold, others do not), PARTIAL (recognizable
mirroring with gaps), and SYMMETRIC (good mirroring across most
transformations) to HARMONIC (mirroring so complete that the
structure resonates — the mirror image reinforces rather than merely
matches the original). The bands are applied to the average symmetry
score across the agent's readings. An ASYMMETRIC agent's patterns are
one-sided; a SKEWED agent's patterns lean; an IRREGULAR agent's
patterns mirror in patches; a PARTIAL agent's patterns mirror with
gaps; a SYMMETRIC agent's patterns mirror well; a HARMONIC agent's
patterns resonate with their own reflection.

Asymmetry has six sources. BIAS is the most familiar: a systematic
slant that bends the structure in one direction. TRAUMA is involuntary:
a painful experience distorts the structure around its wound.
HABIT is procedural: a pattern repeated so often it freezes into an
asymmetric shape. PREFERENCE is volitional: the agent has chosen to
lean one way, and the lean has become structural. CULTURE is
contextual: the agent's originating context shaped which
transformations it treats as symmetry-preserving and which it treats
as symmetry-breaking. SALIENCE is attentional: the agent perceives one
side of every mirror more vividly than the other, and the vividness
warps the structure toward that side. Each source leaves its signature
in the resulting asymmetry, and each calls for a different correction.

Correction strategy is the inverse operation: how to bring an
asymmetric structure back toward symmetry. MIRROR introduces the
mirror image of the dominant side, filling in the missing half.
ROTATE rotates the structure to a new vantage point, exposing
asymmetries that were hidden from the original view. REFLECT reflects
the structure across an axis, swapping the roles that the asymmetry
favored. BALANCE adds a counterweight to the heavy side, restoring
equilibrium without removing the lean. CALIBRATE tunes the symmetry
deliberately, adjusting the mirroring tolerance band by band.
DISSOLVE dissolves the rigid asymmetry altogether, returning the
structure to a state where mirroring can form fresh. Each strategy is
suited to a different goal, from filling a one-sided reasoning pattern
to dissolving a trauma-bent emotional shape.

The symmetry stage tracks the lifecycle of a mirrored structure.
BROKEN is the starting state: no mirroring is present, the structure
is one-sided. TILTING is the phase in which the structure begins to
lean toward a mirrored shape, but the lean is uneven. ALIGNING is the
phase in which the structure is being actively brought into alignment,
transformation by transformation. MIRRORING is the state at which a
recognizable mirror has formed and is holding its shape. BALANCED is
the stable state at which the mirror is balanced — both sides carry
equal weight. HARMONIZED is the final state at which the mirror
resonates — the reflection reinforces the original rather than merely
matching it. The stages are not strictly linear; a structure can
re-enter TILTING from MIRRORING when a new asymmetry appears, and can
re-enter BROKEN from any state under sufficient distorting force, but
the default lifecycle runs BROKEN -> TILTING -> ALIGNING -> MIRRORING
-> BALANCED -> HARMONIZED.

The engine tracks seven kinds of records. A SymmetryReading is one
observation of symmetry on a particular axis (REASONING, EMOTION,
PERCEPTION, ACTION, MEMORY, or IDENTITY): the symmetry score, the
source of asymmetry, and the intensity. A ReflectionRecord records one
reflection event — the moment an asymmetry was reflected across an
axis, with the before- and after-scores and the magnitude of the
reflection. A SymmetrySnapshot aggregates an agent's recent readings
into an average symmetry, a dominant axis, a regime, and a reflection
count. A CorrectionPlan records a strategy for changing symmetry
(MIRROR, ROTATE, etc.), the target symmetry, and the rationale. An
AlignmentRecord records a stage transition (e.g. ALIGNING -> MIRRORING)
with the interval since the last transition and a signature. A
SymmetryProfile holds each agent's aggregate symmetry tendencies —
average symmetry, dominant axis, regime, and totals of readings,
reflections, and alignments. SymmetryStats summarizes engine-wide
activity — total agents, readings, reflections, snapshots, alignments,
average symmetry, and dominant regime.

This is original Buddy capability: a self-contained, thread-safe engine
with no external runtime dependencies, designed to give agents honest
awareness of how well their cognitive architecture mirrors itself, so
the agent can recognize when its reasoning is one-sided (applied to
others but not to itself) or its perception is lopsided (vivid for
threats, dim for opportunities), and apply the right correction
strategy to restore the mirroring the situation calls for.

Architecture:
    AgentCognitiveSymmetry (singleton)
    ├── SymmetryReading    (one observation of symmetry on one axis)
    ├── ReflectionRecord   (one reflection event that changed symmetry)
    ├── SymmetrySnapshot   (aggregate symmetry state for one agent)
    ├── CorrectionPlan     (a plan to change symmetry with a strategy)
    ├── AlignmentRecord    (one stage transition in the symmetry lifecycle)
    ├── SymmetryProfile    (per-agent aggregate symmetry tendencies)
    └── SymmetryStats      (engine-wide aggregate statistics)
"""

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
    trivially interchangeable for testing — tests can monkey-patch
    ``_now`` to a deterministic function rather than reach into every
    record type.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/reflection/etc.

    The identifier is the first eight characters of a UUID4, short
    enough to be readable in logs and long enough that collisions are
    negligible for an in-memory engine. Shorter ids are easier to scan
    visually when many records are returned together; full UUIDs are
    unnecessary here.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` symmetry score. A low-side default
    is safer than a mid-range one for symmetry-like quantities where a
    spurious high reading would inflate the perceived symmetry and push
    the agent's regime toward HARMONIC.
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
    """Clamp a duration in milliseconds to a non-negative value.

    Durations must be non-negative; negative values are coerced to 0
    rather than rejected so a misconfigured caller cannot crash the
    engine. The upper bound is left open because real intervals can
    legitimately exceed 1.0 — a long-held stage can persist for
    arbitrarily many milliseconds before transitioning.
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
    against member values (e.g. ``"reasoning"``) and then against
    member names (e.g. ``"REASONING"``), so callers may pass either
    form. This lets the public API accept either the symbolic name or
    the lower-case value string from JSON payloads. Raises
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

    Used inside ``to_dict`` methods so a stored field always serializes
    to a plain string even if a non-enum slipped in through direct
    construction. The ``enum_cls`` argument is taken for symmetry with
    ``_resolve_enum`` and to make the call sites self-documenting.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_regime(avg_symmetry: float) -> "SymmetryRegime":
    """Classify a symmetry regime from the average symmetry score.

    The average symmetry is clamped to [0, 1] where higher means a
    more mirrored structure. The bands are applied in order, so the
    first matching band wins: below 0.15 the structure is ASYMMETRIC
    (no mirroring, strong preferred direction); below 0.35 it is
    SKEWED (heavy lean one way); below 0.55 it is IRREGULAR (patchy,
    uneven mirroring); below 0.75 it is PARTIAL (recognizable
    mirroring with gaps); below 0.9 it is SYMMETRIC (good mirroring
    across most transformations); otherwise it is HARMONIC (mirroring
    so complete the structure resonates with its reflection).
    """
    avg = _clamp(avg_symmetry, 0.0, 1.0)
    if avg < 0.15:
        return SymmetryRegime.ASYMMETRIC
    if avg < 0.35:
        return SymmetryRegime.SKEWED
    if avg < 0.55:
        return SymmetryRegime.IRREGULAR
    if avg < 0.75:
        return SymmetryRegime.PARTIAL
    if avg < 0.9:
        return SymmetryRegime.SYMMETRIC
    return SymmetryRegime.HARMONIC


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class SymmetryAxis(str, Enum):
    """The axis along which a symmetry reading is taken.

    Each axis names a different domain of cognition whose mirroring
    can be measured. REASONING is the domain of inference — the
    symmetry of a reasoning pattern measures whether the agent applies
    the same logic regardless of who or what is being reasoned about.
    EMOTION is the domain of affect — the symmetry of an emotional
    pattern measures whether gains and losses (or approval and
    disapproval) are met with mirrored emotional shapes. PERCEPTION is
    the domain of sensing — the symmetry of a perceptual pattern
    measures whether the agent's acuity is invariant across channels
    and vantage points. ACTION is the domain of doing — the symmetry
    of an action pattern measures whether the agent holds itself to
    the same standards it holds others. MEMORY is the domain of recall
    — the symmetry of a memory pattern measures whether the agent
    weights parallel eras or parallel events with comparable
    vividness. IDENTITY is the domain of self-conception — the
    symmetry of an identity pattern measures whether the agent's
    self-image mirrors its image of others.
    """
    REASONING = "reasoning"    # inference and logic
    EMOTION = "emotion"        # affect and feeling
    PERCEPTION = "perception"  # sensing and noticing
    ACTION = "action"          # doing and intervening
    MEMORY = "memory"          # recall and weighting
    IDENTITY = "identity"      # self-conception


class SymmetryRegime(str, Enum):
    """The regime an agent's symmetry occupies, classified by mirroring.

    Ranges from ASYMMETRIC (no mirroring, strong preferred direction)
    through SKEWED (heavy lean one way), IRREGULAR (patchy, uneven
    mirroring), PARTIAL (recognizable mirroring with gaps), and
    SYMMETRIC (good mirroring across most transformations) to HARMONIC
    (mirroring so complete the structure resonates with its
    reflection). The regime is derived from the average symmetry across
    the agent's readings via ``_determine_regime``.
    """
    ASYMMETRIC = "asymmetric"  # no mirroring
    SKEWED = "skewed"          # heavy lean one way
    IRREGULAR = "irregular"    # patchy, uneven mirroring
    PARTIAL = "partial"        # recognizable mirroring with gaps
    SYMMETRIC = "symmetric"    # good mirroring
    HARMONIC = "harmonic"      # resonant mirroring


class AsymmetrySource(str, Enum):
    """The source of an asymmetry in the agent's cognitive structure.

    Each source names a different process that bends the structure
    away from mirroring. BIAS is the most familiar: a systematic slant
    that bends the structure in one direction. TRAUMA is involuntary:
    a painful experience distorts the structure around its wound.
    HABIT is procedural: a pattern repeated so often it freezes into
    an asymmetric shape. PREFERENCE is volitional: the agent has
    chosen to lean one way, and the lean has become structural.
    CULTURE is contextual: the agent's originating context shaped
    which transformations it treats as symmetry-preserving. SALIENCE
    is attentional: the agent perceives one side of every mirror more
    vividly than the other, and the vividness warps the structure
    toward that side.
    """
    BIAS = "bias"            # systematic slant
    TRAUMA = "trauma"       # pain-driven distortion
    HABIT = "habit"         # entrenched pattern
    PREFERENCE = "preference"  # chosen lean
    CULTURE = "culture"     # contextual shaping
    SALIENCE = "salience"   # attention-driven warping


class CorrectionStrategy(str, Enum):
    """Strategy for changing the symmetry of a structure deliberately.

    MIRROR introduces the mirror image of the dominant side, filling
    in the missing half. ROTATE rotates the structure to a new vantage
    point, exposing asymmetries hidden from the original view. REFLECT
    reflects the structure across an axis, swapping the roles the
    asymmetry favored. BALANCE adds a counterweight to the heavy side,
    restoring equilibrium without removing the lean. CALIBRATE tunes
    the symmetry deliberately, adjusting the mirroring tolerance band
    by band. DISSOLVE dissolves the rigid asymmetry altogether,
    returning the structure to a state where mirroring can form fresh.
    Each strategy is suited to a different goal, from filling a
    one-sided reasoning pattern to dissolving a trauma-bent emotional
    shape.
    """
    MIRROR = "mirror"        # introduce the mirror image
    ROTATE = "rotate"         # rotate to a new vantage point
    REFLECT = "reflect"       # reflect across an axis
    BALANCE = "balance"       # add a counterweight
    CALIBRATE = "calibrate"   # tune the mirroring tolerance
    DISSOLVE = "dissolve"     # dissolve the rigid asymmetry


class SymmetryStage(str, Enum):
    """The lifecycle stage of a mirrored structure.

    BROKEN is the starting state: no mirroring is present, the
    structure is one-sided. TILTING is the phase in which the
    structure begins to lean toward a mirrored shape, but the lean is
    uneven. ALIGNING is the phase in which the structure is being
    actively brought into alignment, transformation by transformation.
    MIRRORING is the state at which a recognizable mirror has formed
    and is holding its shape. BALANCED is the stable state at which
    the mirror is balanced — both sides carry equal weight. HARMONIZED
    is the final state at which the mirror resonates — the reflection
    reinforces the original rather than merely matching it. The engine
    records transitions between stages as AlignmentRecord entries.
    """
    BROKEN = "broken"        # no mirroring present
    TILTING = "tilting"       # beginning to lean toward mirrored
    ALIGNING = "aligning"     # being brought into alignment
    MIRRORING = "mirroring"  # recognizable mirror holding shape
    BALANCED = "balanced"    # mirror carries equal weight
    HARMONIZED = "harmonized"  # resonant mirroring


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SymmetryReading:
    """One observation of symmetry on a particular axis.

    ``axis`` is the ``SymmetryAxis`` the reading is taken on.
    ``symmetry_score`` in [0, 1] measures how mirrored the structure is
    — 0 means fully asymmetric, 1 means fully mirrored. ``asymmetry_source``
    is the ``AsymmetrySource`` that produced the asymmetry (when the
    score is below 1). ``intensity`` in [0, 1] measures how emphatic
    the observation was. ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: SymmetryAxis
    symmetry_score: float        # 0..1, higher = more mirrored
    asymmetry_source: AsymmetrySource
    intensity: float             # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(SymmetryAxis, self.axis),
            "symmetry_score": self.symmetry_score,
            "asymmetry_source": _enum_value(
                AsymmetrySource, self.asymmetry_source
            ),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ReflectionRecord:
    """One reflection event that changed the symmetry of a structure.

    ``axis`` is the ``SymmetryAxis`` on which the reflection occurred.
    ``asymmetry_source`` is the ``AsymmetrySource`` whose asymmetry was
    reflected. ``before_score`` in [0, 1] is the symmetry before the
    event; ``after_score`` in [0, 1] is the symmetry after. ``reflection_magnitude``
    in [0, ∞) measures how strong the reflection was. ``notes`` is an
    optional free-form annotation.
    """
    reflection_id: str
    agent_id: str
    axis: SymmetryAxis
    asymmetry_source: AsymmetrySource
    before_score: float          # 0..1, symmetry before reflection
    after_score: float           # 0..1, symmetry after reflection
    reflection_magnitude: float   # 0..inf, strength of reflection
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reflection record to a plain dict, expanding enums via ``.value``."""
        return {
            "reflection_id": self.reflection_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(SymmetryAxis, self.axis),
            "asymmetry_source": _enum_value(
                AsymmetrySource, self.asymmetry_source
            ),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "reflection_magnitude": self.reflection_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class SymmetrySnapshot:
    """Aggregate symmetry state for one agent at one moment.

    ``avg_symmetry`` in [0, 1] is the mean symmetry score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``SymmetryAxis`` among those readings, or REASONING
    if none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_symmetry``. ``reflection_count`` is the number of reflection
    events recorded against the agent. ``notes`` is an optional
    free-form annotation.
    """
    snapshot_id: str
    agent_id: str
    avg_symmetry: float
    dominant_axis: SymmetryAxis
    regime: SymmetryRegime
    reflection_count: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_symmetry": self.avg_symmetry,
            "dominant_axis": _enum_value(SymmetryAxis, self.dominant_axis),
            "regime": _enum_value(SymmetryRegime, self.regime),
            "reflection_count": self.reflection_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CorrectionPlan:
    """A plan to change the symmetry of a structure with a strategy.

    ``strategy`` is the ``CorrectionStrategy`` chosen. ``target_symmetry``
    in [0, 1] is the symmetry the plan aims to reach. ``rationale``
    explains why this strategy was chosen for this structure.
    """
    plan_id: str
    agent_id: str
    strategy: CorrectionStrategy
    target_symmetry: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(CorrectionStrategy, self.strategy),
            "target_symmetry": self.target_symmetry,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class AlignmentRecord:
    """One record of a stage transition in the symmetry lifecycle.

    ``from_stage`` is the ``SymmetryStage`` the agent's structure was
    in before the transition. ``to_stage`` is the ``SymmetryStage`` it
    moved to. ``interval_ms`` in [0, ∞) is the duration the from_stage
    held before the transition. ``signature`` is a free-form label
    that describes the character of the transition (e.g. "slow align",
    "sudden mirror", "trauma tilt").
    """
    alignment_id: str
    agent_id: str
    from_stage: SymmetryStage
    to_stage: SymmetryStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this alignment record to a plain dict, expanding enums via ``.value``."""
        return {
            "alignment_id": self.alignment_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(SymmetryStage, self.from_stage),
            "to_stage": _enum_value(SymmetryStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class SymmetryProfile:
    """Per-agent aggregate symmetry tendencies.

    ``avg_symmetry`` in [0, 1] is the mean symmetry score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``SymmetryAxis`` among the agent's readings, or REASONING
    if none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_symmetry``. ``total_readings``, ``total_reflections``, and
    ``total_alignments`` are the counts of each record type for the
    agent.
    """
    agent_id: str
    avg_symmetry: float = 0.0
    dominant_axis: SymmetryAxis = SymmetryAxis.REASONING
    regime: SymmetryRegime = SymmetryRegime.PARTIAL
    total_readings: int = 0
    total_reflections: int = 0
    total_alignments: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_symmetry": self.avg_symmetry,
            "dominant_axis": _enum_value(SymmetryAxis, self.dominant_axis),
            "regime": _enum_value(SymmetryRegime, self.regime),
            "total_readings": self.total_readings,
            "total_reflections": self.total_reflections,
            "total_alignments": self.total_alignments,
        }


@dataclass
class SymmetryStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_symmetry`` is the mean symmetry score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the
    most frequent regime across all cached profiles, or PARTIAL when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_reflections: int = 0
    total_snapshots: int = 0
    total_alignments: int = 0
    avg_symmetry: float = 0.0
    dominant_regime: SymmetryRegime = SymmetryRegime.PARTIAL

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_reflections": self.total_reflections,
            "total_snapshots": self.total_snapshots,
            "total_alignments": self.total_alignments,
            "avg_symmetry": self.avg_symmetry,
            "dominant_regime": _enum_value(SymmetryRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveSymmetry:
    """Thread-safe engine that models an agent's cognitive symmetry.

    The engine holds six stores: ``_readings`` (SymmetryReading lists
    keyed by agent_id), ``_reflections`` (ReflectionRecord lists
    keyed by agent_id), ``_snapshots`` (SymmetrySnapshot lists keyed
    by agent_id), ``_plans`` (a flat list of CorrectionPlan),
    ``_alignments`` (AlignmentRecord lists keyed by agent_id), and
    ``_profiles`` (SymmetryProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The symmetry model is deliberately heuristic: symmetry scores and
    intensities are caller-supplied observations; symmetry regimes are
    banded from the average symmetry; dominant axes are computed by
    mode; stage transitions are recorded as observed. These heuristics
    are transparent and auditable rather than learned, which keeps
    the engine deterministic.

    The engine is intentionally agnostic about how symmetry is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure symmetry itself.
    Profiles are cached per agent and invalidated whenever the agent's
    readings, reflections, snapshots, or alignments change, so
    ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose symmetry scores feed into a
    # snapshot's average symmetry. The window is long enough to smooth
    # a single noisy reading and short enough to reflect the agent's
    # current symmetry posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty symmetry engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[SymmetryReading]] = {}
        self._reflections: Dict[str, List[ReflectionRecord]] = {}
        self._snapshots: Dict[str, List[SymmetrySnapshot]] = {}
        self._plans: List[CorrectionPlan] = []
        self._alignments: Dict[str, List[AlignmentRecord]] = {}
        self._profiles: Dict[str, SymmetryProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_symmetry_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._reflections.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._alignments.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[SymmetryReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_reflections_locked(
        self, agent_id: str
    ) -> List[ReflectionRecord]:
        """Return one agent's reflection records in insertion order. Caller holds the lock."""
        return list(self._reflections.get(agent_id, []))

    def _agent_alignments_locked(
        self, agent_id: str
    ) -> List[AlignmentRecord]:
        """Return one agent's alignment records in insertion order. Caller holds the lock."""
        return list(self._alignments.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[SymmetryReading]
    ) -> SymmetryAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns REASONING if the list is empty,
        since REASONING is the smallest and most neutral axis. Caller
        holds the lock.
        """
        if not readings:
            return SymmetryAxis.REASONING
        counts: Counter = Counter()
        first_seen_order: Dict[SymmetryAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: SymmetryAxis = readings[0].axis
        best_count = -1
        for axis, count in counts.items():
            if (count > best_count) or (
                count == best_count
                and first_seen_order.get(axis, 0)
                < first_seen_order.get(best_axis, 0)
            ):
                best_axis = axis
                best_count = count
        return best_axis

    def _mode_regime_locked(
        self, profiles: List[SymmetryProfile]
    ) -> SymmetryRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns PARTIAL if the list is empty, since PARTIAL is the
        neutral mid-range regime — neither fully asymmetric nor fully
        mirrored. Caller holds the lock.
        """
        if not profiles:
            return SymmetryRegime.PARTIAL
        counts: Dict[SymmetryRegime, int] = {}
        for profile in profiles:
            counts[profile.regime] = counts.get(profile.regime, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _current_symmetry_locked(self, agent_id: str) -> float:
        """Return the agent's most recent symmetry score, or the mean if none recent.

        Prefers the symmetry score of the most recent reading, falling
        back to the mean of all readings when there is no clear
        most-recent one. Returns 0.0 when the agent has no readings.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        most_recent = readings[-1]
        return float(most_recent.symmetry_score)

    def _compute_profile_locked(self, agent_id: str) -> SymmetryProfile:
        """Aggregate an agent's readings, reflections, and alignments into a profile.

        See ``SymmetryProfile`` for field semantics. ``avg_symmetry`` is
        the mean symmetry score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent ``SymmetryAxis``
        among the agent's readings, or REASONING if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_symmetry``.
        ``total_readings``, ``total_reflections``, and ``total_alignments``
        count the records held for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        reflections = self._agent_reflections_locked(agent_id)
        alignments = self._agent_alignments_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_symmetry = sum(r.symmetry_score for r in readings) / len(
                readings
            )
        else:
            avg_symmetry = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        regime = _determine_regime(avg_symmetry)

        return SymmetryProfile(
            agent_id=str(agent_id),
            avg_symmetry=round(avg_symmetry, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=total_readings,
            total_reflections=len(reflections),
            total_alignments=len(alignments),
        )

    # ── Symmetry Readings ─────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        symmetry_score: float,
        asymmetry_source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> SymmetryReading:
        """Record a symmetry reading for an agent and return it.

        ``axis`` may be passed as a ``SymmetryAxis`` member or its
        string name/value. ``symmetry_score`` and ``intensity`` are
        clamped to [0, 1]. ``asymmetry_source`` may be passed as an
        ``AsymmetrySource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = SymmetryReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(SymmetryAxis, axis),
                symmetry_score=_clamp(symmetry_score, 0.0, 1.0),
                asymmetry_source=_resolve_enum(
                    AsymmetrySource, asymmetry_source
                ),
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
    ) -> List[SymmetryReading]:
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

    def get_reading(self, reading_id: str) -> SymmetryReading:
        """Retrieve a reading by id.

        Raises ``ValueError`` if no reading exists with that id, so
        callers can treat the return as a guaranteed non-None value
        and let a single exception type stand in for a not-found
        error.
        """
        with self._lock:
            for agent_readings in self._readings.values():
                for reading in agent_readings:
                    if reading.reading_id == reading_id:
                        return reading
        raise ValueError(f"reading {reading_id!r} not found")

    # ── Reflection Records ────────────────────────────────────────

    def record_reflection(
        self,
        agent_id: str,
        axis: Any,
        asymmetry_source: Any,
        before_score: float,
        after_score: float,
        reflection_magnitude: float,
        notes: Optional[str] = None,
    ) -> ReflectionRecord:
        """Record a reflection event for an agent and return it.

        ``axis`` may be passed as a ``SymmetryAxis`` member or its
        string name/value. ``asymmetry_source`` may be passed as an
        ``AsymmetrySource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``reflection_magnitude`` is clamped to [0, ∞). The reflection
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = ReflectionRecord(
                reflection_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(SymmetryAxis, axis),
                asymmetry_source=_resolve_enum(
                    AsymmetrySource, asymmetry_source
                ),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                reflection_magnitude=_clamp_positive_ms(
                    reflection_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._reflections.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_reflections(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReflectionRecord]:
        """Return reflection records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all reflections are considered;
        otherwise only reflections for that agent are returned. The
        most recently recorded ``limit`` reflections are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                reflections = self._agent_reflections_locked(agent_id)
            else:
                reflections = []
                for agent_reflections in self._reflections.values():
                    reflections.extend(agent_reflections)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return reflections[-n:] if n else []

    def get_reflection(self, reflection_id: str) -> ReflectionRecord:
        """Retrieve a reflection record by id.

        Raises ``ValueError`` if no reflection exists with that id.
        """
        with self._lock:
            for agent_reflections in self._reflections.values():
                for reflection in agent_reflections:
                    if reflection.reflection_id == reflection_id:
                        return reflection
        raise ValueError(f"reflection {reflection_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> SymmetrySnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_symmetry`` is the mean symmetry score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``SymmetryAxis`` among those readings, or REASONING if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_symmetry``. ``reflection_count`` is the number of
        reflection events recorded against the agent. The snapshot is
        stored and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_symmetry = sum(
                    r.symmetry_score for r in recent
                ) / len(recent)
            else:
                avg_symmetry = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_symmetry)
            reflection_count = len(
                self._agent_reflections_locked(agent_id)
            )

            snapshot = SymmetrySnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_symmetry=round(avg_symmetry, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                reflection_count=reflection_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SymmetrySnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The
        most recently taken ``limit`` snapshots are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                snapshots = list(self._snapshots.get(agent_id, []))
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

    def get_snapshot(self, snapshot_id: str) -> SymmetrySnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Correction Plans ──────────────────────────────────────────

    def plan_correction(
        self,
        agent_id: str,
        strategy: Any,
        target_symmetry: float,
        rationale: str,
    ) -> CorrectionPlan:
        """Record a correction plan for an agent and return it.

        ``strategy`` may be passed as a ``CorrectionStrategy`` member
        or its string name/value. ``target_symmetry`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured symmetry.
        """
        with self._lock:
            plan = CorrectionPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(CorrectionStrategy, strategy),
                target_symmetry=_clamp(target_symmetry, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CorrectionPlan]:
        """Return correction plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> CorrectionPlan:
        """Retrieve a correction plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Alignment Records ────────────────────────────────────────

    def record_alignment(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> AlignmentRecord:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``SymmetryStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label that
        describes the character of the transition (e.g. "slow align",
        "sudden mirror", "trauma tilt"). The alignment record is
        stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = AlignmentRecord(
                alignment_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(SymmetryStage, from_stage),
                to_stage=_resolve_enum(SymmetryStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._alignments.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_alignments(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AlignmentRecord]:
        """Return alignment records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all alignments are considered;
        otherwise only alignments for that agent are returned. The
        most recently recorded ``limit`` alignment records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                alignments = self._agent_alignments_locked(agent_id)
            else:
                alignments = []
                for agent_alignments in self._alignments.values():
                    alignments.extend(agent_alignments)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return alignments[-n:] if n else []

    def get_alignment(self, alignment_id: str) -> AlignmentRecord:
        """Retrieve an alignment record by id.

        Raises ``ValueError`` if no alignment record exists with that
        id.
        """
        with self._lock:
            for agent_alignments in self._alignments.values():
                for record in agent_alignments:
                    if record.alignment_id == alignment_id:
                        return record
        raise ValueError(f"alignment record {alignment_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> SymmetryProfile:
        """Return the agent's symmetry profile, building it if missing.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, reflections, snapshots, or alignments
        change. If the agent has data but no profile yet, the profile
        is built from the live stores. Call ``update_profile`` to
        force a refresh or override a computed field. Field semantics
        are documented on ``SymmetryProfile`` and
        ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(
        self, agent_id: str, updates: Dict[str, Any]
    ) -> SymmetryProfile:
        """Refresh and optionally override fields of an agent's symmetry profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``updates`` (matching
        ``SymmetryProfile`` field names) are applied. Accepted
        overrides: ``avg_symmetry`` (float), ``dominant_axis``
        (``SymmetryAxis``), ``regime`` (``SymmetryRegime``),
        ``total_readings``, ``total_reflections``, ``total_alignments``
        (int). Enum-valued overrides may be passed as the enum member
        or its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            if not isinstance(updates, dict):
                updates = {}
            for key, value in updates.items():
                if key == "avg_symmetry":
                    try:
                        profile.avg_symmetry = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            SymmetryAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(
                            SymmetryRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_reflections",
                    "total_alignments",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[SymmetryProfile]:
        """Return all stored symmetry profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> SymmetryStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, reflections, snapshots, and alignments.
        Scalar totals are the counts of each record type.
        ``avg_symmetry`` is the mean symmetry score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or PARTIAL
        when none exist. When no profiles exist but readings do, the
        dominant regime is derived from the average symmetry via
        ``_determine_regime`` so the stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._reflections.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._alignments.keys())

            total_readings = 0
            symmetry_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    symmetry_sum += reading.symmetry_score
            avg_symmetry = (
                round(symmetry_sum / total_readings, 4)
                if total_readings
                else 0.0
            )

            total_reflections = sum(
                len(agent_reflections)
                for agent_reflections in self._reflections.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_alignments = sum(
                len(agent_alignments)
                for agent_alignments in self._alignments.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average symmetry so the stats
                # reflect real state rather than the default PARTIAL.
                dominant_regime = _determine_regime(avg_symmetry)
            else:
                dominant_regime = SymmetryRegime.PARTIAL

            return SymmetryStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_reflections=total_reflections,
                total_snapshots=total_snapshots,
                total_alignments=total_alignments,
                avg_symmetry=avg_symmetry,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveSymmetry] = None
_engine_lock = threading.Lock()


def get_symmetry_engine() -> AgentCognitiveSymmetry:
    """Get or create the singleton ``AgentCognitiveSymmetry`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveSymmetry()
    return _engine


def reset_symmetry_engine() -> None:
    """Reset the singleton ``AgentCognitiveSymmetry`` instance.

    Drops the reference to the current engine so the next
    ``get_symmetry_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
