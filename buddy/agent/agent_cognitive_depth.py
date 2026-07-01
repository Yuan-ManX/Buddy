"""
Agent Cognitive Depth Engine — managing the depth dimension of an agent's
reasoning.

Every act of reasoning has a depth. A shallow pass treats the question at
face value: it reads the surface of the problem, produces a single
answer, and stops. A deep pass descends through layers — from the
literal statement of the problem, through the abstractions that organise
it, down to the assumptions that ground it, and back up through the
consequences that follow. Depth is not the same as length, and it is
not the same as chain-of-thought. Chain-of-thought is a generation
technique: it produces explicit intermediate steps. Depth is a
measurement of how far those steps actually descend. A long chain can
stay shallow (restating the same level in different words); a short
chain can be deep (one well-placed "why" can reach a foundation). This
engine measures and manages that depth as a first-class cognitive
dimension, distinct from the generation techniques that produce the
steps whose depth is being measured.

Depth is not a single quantity. It has components, each a distinct axis
along which reasoning can descend:

  * ABSTRACTION    — the number of abstraction levels traversed, from
                     concrete instance up to the categories that contain
                     it. Reasoning that stays at one level has low
                     abstraction depth; reasoning that moves between
                     levels has high.
  * RECURSION      — the depth of recursive self-reference. A reasoning
                     step that applies the same operation to its own
                     output descends a level; repeated application
                     builds recursive depth.
  * FOUNDATIONAL   — the depth of questioning assumptions. Each
                     "why does this hold?" that challenges a premise
                     descends a foundational level; the chain bottoms
                     out at axioms or first principles.
  * COUNTERFACTUAL — the depth of alternative-world exploration. A
                     shallow counterfactual flips one variable; a
                     deeper one flips the flip, or explores worlds
                     where the rules of inference themselves differ.
  * EXPLANATORY    — the depth of why-chains. Each "why?" in succession
                     lengthens the explanatory chain; the depth is the
                     number of links traversed before the chain
                     terminates.
  * TELEOLOGICAL   — the depth of purpose-questioning. "What is this
                     for?" begets "what is that for?" begets "what is
                     that for?" — a chain that can bottom out at
                     intrinsic value or recurse without end.

The engine instruments these components via DepthProbe readings, each
of which scores a single (agent, dimension) pair on a [0, 1] depth
scale and records the number of levels actually traversed. Aggregated
probes yield a DepthAssessment, which classifies the agent's current
depth regime on a ladder from SHALLOW (surface only) through SURFACE,
MODERATE, DEEP, and PROFOUND up to ABYSSAL (bottomless recursion,
where the descent has no terminus).

A regime is a diagnosis, not a verdict. SHALLOW reasoning is
appropriate for routine tasks and dangerous for foundational ones;
ABYSSAL reasoning is appropriate for axiom-hunting and dangerous when
the user needs a quick answer. The engine therefore recommends
deepening moves (ASK_WHY, ABSTRACT_UP, CONCRETIZE_DOWN,
QUESTION_ASSUMPTION, CONSIDER_COUNTERFACTUAL, RECURSE,
GROUND_IN_PRINCIPLE) when the regime is too shallow for the task, and
surfacing moves (SUMMARIZE, ANCHOR_EXAMPLE, STATE_CONCLUSION,
CITE_RESULT, DEFER) when the regime is too deep for the situation.
Each move is recorded as an action with a rationale and an expected
gain or relief, so the agent's depth management is auditable.

Finally, the engine tracks trajectories — the direction of depth
change over time. A trajectory can be DESCENDING (going deeper),
HOLDING (maintaining depth), ASCENDING (surfacing), OSCILLATING
(alternating deep and shallow), PLUNGING (a sudden depth increase),
or BOTTOMING_OUT (hitting a foundational layer). Trajectories make
the depth regime a dynamical quantity rather than a static one, and
let the engine distinguish productive descent from unproductive
plunge.

This is original Buddy work: a self-contained, thread-safe engine
with no external runtime dependencies, designed to give agents honest
awareness of how deep their reasoning actually goes, and the levers
to deepen or surface on demand.

Architecture:
    AgentCognitiveDepth (singleton)
    ├── DepthProbe            (a single depth reading on one dimension)
    ├── DepthAssessment       (aggregate depth across recent probes)
    ├── DeepeningAction       (a recorded decision to push deeper)
    ├── SurfacingAction       (a recorded decision to pull back to surface)
    ├── DepthTrajectoryRecord (a single step in depth direction over time)
    ├── DepthProfile          (per-agent depth summary)
    └── DepthStats            (aggregate engine statistics)
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string.

    Used as the canonical timestamp for every record the engine creates.
    Keeping it centralised here means timestamps are uniform across the
    engine and trivially interchangeable for testing.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a probe/assessment/action/etc.

    The identifier is the first eight characters of a UUID4, which is
    short enough to be readable in logs and long enough that collisions
    are negligible for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is silently coerced to the lower bound, matching
    the behaviour used across the cognitive engines: a missing or
    malformed reading should not crash the engine, and a low-side
    default is safer than a mid-range one for depth-like quantities
    where a spurious high reading would suggest the agent is reasoning
    more deeply than it actually is.
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

    Enum members are returned unchanged. Strings are matched first
    against member values (e.g. ``"abstraction"``) and then against
    member names (e.g. ``"ABSTRACTION"``), so callers may pass either
    form. Raises ``ValueError`` if neither matches. This lets the
    public API accept either the symbolic name or the lower-case value
    string from JSON payloads.
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

    Used inside ``to_dict`` methods so a stored field always serialises
    to a plain string even if a non-enum slipped in through direct
    construction. The ``enum_cls`` argument is taken for symmetry with
    ``_resolve_enum`` and to make the call sites self-documenting.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_regime(depth_score: float) -> "DepthRegime":
    """Band a continuous depth score in [0, 1] into a discrete DepthRegime.

    The bands are chosen so that each regime covers a roughly equal
    slice of the depth range, with the two extremes (SHALLOW and
    ABYSSAL) reserved for the tails where behaviour is qualitatively
    different from the middle of the scale. The score is clamped to
    [0, 1] before banding so out-of-range inputs cannot select an
    unexpected regime.

      * < 0.15      -> SHALLOW     (surface only)
      * < 0.35      -> SURFACE     (one level below surface)
      * < 0.55      -> MODERATE    (multi-level)
      * < 0.75      -> DEEP        (recursive/foundational)
      * < 0.90      -> PROFOUND    (deeply foundational)
      * else        -> ABYSSAL     (bottomless recursion)
    """
    score = _clamp(depth_score)
    if score < 0.15:
        return DepthRegime.SHALLOW
    if score < 0.35:
        return DepthRegime.SURFACE
    if score < 0.55:
        return DepthRegime.MODERATE
    if score < 0.75:
        return DepthRegime.DEEP
    if score < 0.90:
        return DepthRegime.PROFOUND
    return DepthRegime.ABYSSAL


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class DepthDimension(str, Enum):
    """The distinct axes along which reasoning can descend.

    Depth is not a single quantity. Each dimension is an independent
    way in which a reasoning chain can go deep: by climbing
    abstraction levels, by recursing on itself, by questioning its
    own assumptions, by exploring alternative worlds, by extending
    why-chains, or by asking what the reasoning is for. An agent can
    be deep on one dimension and shallow on another, and the engine
    tracks each independently so that deepening and surfacing moves
    can target the dimension that needs them.
    """
    ABSTRACTION = "abstraction"        # levels of abstraction traversed
    RECURSION = "recursion"            # recursive self-reference depth
    FOUNDATIONAL = "foundational"      # questioning assumptions depth
    COUNTERFACTUAL = "counterfactual"  # alternative-worlds depth
    EXPLANATORY = "explanatory"        # why-chains depth
    TELEOLOGICAL = "teleological"      # purpose/why depth


class DepthRegime(str, Enum):
    """The depth regime an agent occupies, classified by aggregate depth.

    The regime is a qualitative characterisation of how deep the
    agent's reasoning currently goes, banded from the surface to the
    abyssal. Each regime carries a different risk profile: SHALLOW is
    fast but brittle, ABYSSAL is rigorous but may never terminate.
    The engine recommends deepening or surfacing moves to keep the
    regime matched to the task at hand.
    """
    SHALLOW = "shallow"        # surface only
    SURFACE = "surface"        # one level below surface
    MODERATE = "moderate"      # multi-level
    DEEP = "deep"              # recursive/foundational
    PROFOUND = "profound"      # deeply foundational
    ABYSSAL = "abyssal"        # bottomless recursion


class DeepeningMove(str, Enum):
    """Moves that increase the depth of reasoning.

    Each move is a distinct lever for pushing the agent's reasoning
    deeper along one of the depth dimensions. ASK_WHY lengthens an
    explanatory chain. ABSTRACT_UP climbs to a higher abstraction
    level. CONCRETIZE_DOWN descends to a concrete instance.
    QUESTION_ASSUMPTION challenges a premise, deepening the
    foundational dimension. CONSIDER_COUNTERFACTUAL opens an
    alternative world. RECURSE applies the same operation to its own
    output. GROUND_IN_PRINCIPLE anchors the reasoning in a
    foundational principle, forcing the descent to terminate at
    something stable rather than continuing without end.
    """
    ASK_WHY = "ask_why"                          # lengthen an explanatory chain
    ABSTRACT_UP = "abstract_up"                  # climb to a higher abstraction
    CONCRETIZE_DOWN = "concretize_down"          # descend to a concrete instance
    QUESTION_ASSUMPTION = "question_assumption"  # challenge a premise
    CONSIDER_COUNTERFACTUAL = "consider_counterfactual"  # open an alternative
    RECURSE = "recurse"                          # apply the same reasoning recursively
    GROUND_IN_PRINCIPLE = "ground_in_principle"  # anchor in a foundational principle


class SurfacingMove(str, Enum):
    """Moves that decrease the depth of reasoning.

    Each move is a distinct lever for pulling the agent's reasoning
    back toward the surface when the current depth is greater than the
    situation requires. SUMMARIZE compresses a deep chain into a
    brief statement. ANCHOR_EXAMPLE returns to a concrete instance.
    STATE_CONCLUSION states the conclusion the deep chain reached.
    CITE_RESULT cites a result without re-deriving it. DEFER
    explicitly defers the deeper inquiry to a later pass or a
    different agent.
    """
    SUMMARIZE = "summarize"            # compress to a summary
    ANCHOR_EXAMPLE = "anchor_example"  # return to a concrete example
    STATE_CONCLUSION = "state_conclusion"  # state the conclusion
    CITE_RESULT = "cite_result"        # cite the result
    DEFER = "defer"                    # defer deeper inquiry


class DepthTrajectory(str, Enum):
    """The direction of depth change over time.

    A trajectory describes how the agent's depth is moving, not where
    it currently sits. DESCENDING means the agent is going deeper.
    HOLDING means depth is being maintained. ASCENDING means the
    agent is surfacing. OSCILLATING means depth is alternating
    between deep and shallow without settling. PLUNGING means depth
    has suddenly increased, which can be productive or can signal a
    loss of control. BOTTOMING_OUT means the descent has hit a
    foundational layer and cannot usefully continue.
    """
    DESCENDING = "descending"        # going deeper
    HOLDING = "holding"              # maintaining depth
    ASCENDING = "ascending"          # surfacing
    OSCILLATING = "oscillating"      # alternating deep/shallow
    PLUNGING = "plunging"            # sudden depth increase
    BOTTOMING_OUT = "bottoming_out"  # hit foundational layer


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DepthProbe:
    """A single reading of an agent's depth on one dimension.

    A probe asks: on this specific depth dimension, how deep did the
    agent's reasoning actually go, and how many levels did it traverse
    to get there? The ``depth_score`` is a [0, 1] scalar where 0 means
    the reasoning stayed at the surface and 1 means it reached the
    deepest possible layer on that dimension. ``levels_traversed`` is
    a discrete count of the abstraction, recursion, or why-levels
    actually crossed, which is more auditable than the score alone:
    two probes can share a score of 0.6 while one crossed two levels
    and the other crossed six. ``evidence`` is a free-text note
    recording what in the agent's output led to the reading.
    """
    probe_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    dimension: DepthDimension = DepthDimension.ABSTRACTION
    depth_score: float = 0.0
    levels_traversed: int = 0
    evidence: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this probe to a plain dict, expanding the enum."""
        return {
            "probe_id": self.probe_id,
            "agent_id": self.agent_id,
            "dimension": _enum_value(DepthDimension, self.dimension),
            "depth_score": self.depth_score,
            "levels_traversed": self.levels_traversed,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class DepthAssessment:
    """An aggregate assessment of an agent's depth across recent probes.

    An assessment rolls up the most recent probes for an agent into a
    single snapshot. ``total_depth`` is the mean depth score across
    those probes; ``dominant_dimension`` is the dimension on which the
    agent has been probing most (the mode), or None if no probes
    exist; ``regime`` is the DepthRegime banded from ``total_depth``
    via ``_determine_regime``; and ``probe_count`` is the number of
    probes that contributed to the aggregate. The assessment is the
    natural unit for answering "how deep is this agent reasoning right
    now?".
    """
    assessment_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    total_depth: float = 0.0
    dominant_dimension: Optional[DepthDimension] = None
    regime: DepthRegime = DepthRegime.SHALLOW
    probe_count: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this assessment to a plain dict, expanding enums.

        ``dominant_dimension`` is optional and serialises to ``None``
        when absent so downstream consumers can distinguish "no
        dominant dimension" from "the dimension whose value happens to
        be the empty string".
        """
        return {
            "assessment_id": self.assessment_id,
            "agent_id": self.agent_id,
            "total_depth": self.total_depth,
            "dominant_dimension": _enum_value(DepthDimension, self.dominant_dimension)
            if self.dominant_dimension is not None
            else None,
            "regime": _enum_value(DepthRegime, self.regime),
            "probe_count": self.probe_count,
            "timestamp": self.timestamp,
        }


@dataclass
class DeepeningAction:
    """A recorded decision to push the agent's reasoning deeper.

    When the current regime is too shallow for the task, the engine
    (or a supervisor) applies a deepening move. The action records
    which dimension to deepen, which move was chosen, the rationale
    for the choice, and the expected gain in depth on a [0, 1] scale.
    Expected gain is a prediction, not a measurement; it can be
    compared against later probes to calibrate the move's
    effectiveness over time.
    """
    action_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    dimension: DepthDimension = DepthDimension.ABSTRACTION
    move: DeepeningMove = DeepeningMove.ASK_WHY
    rationale: str = ""
    expected_gain: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this action to a plain dict, expanding enums."""
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "dimension": _enum_value(DepthDimension, self.dimension),
            "move": _enum_value(DeepeningMove, self.move),
            "rationale": self.rationale,
            "expected_gain": self.expected_gain,
            "timestamp": self.timestamp,
        }


@dataclass
class SurfacingAction:
    """A recorded decision to pull the agent's reasoning back toward the surface.

    When the current regime is deeper than the situation requires, the
    engine (or a supervisor) applies a surfacing move. The action
    records which dimension to surface on, which move was chosen, the
    rationale for the choice, and the expected relief — the expected
    reduction in depth on a [0, 1] scale. Like expected gain, expected
    relief is a prediction that can be calibrated against later
    probes.
    """
    action_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    dimension: DepthDimension = DepthDimension.ABSTRACTION
    move: SurfacingMove = SurfacingMove.SUMMARIZE
    rationale: str = ""
    expected_relief: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this action to a plain dict, expanding enums."""
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "dimension": _enum_value(DepthDimension, self.dimension),
            "move": _enum_value(SurfacingMove, self.move),
            "rationale": self.rationale,
            "expected_relief": self.expected_relief,
            "timestamp": self.timestamp,
        }


@dataclass
class DepthTrajectoryRecord:
    """A recorded change in the agent's depth over a single step.

    A trajectory record captures the direction of depth change
    (DESCENDING, HOLDING, ASCENDING, OSCILLATING, PLUNGING, or
    BOTTOMING_OUT), the depth the agent moved from, the depth it
    moved to, and the signed delta between them. The delta is
    positive when the agent descended and negative when it surfaced,
    which lets callers sum deltas over a window to recover the net
    depth change for that window.
    """
    record_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    trajectory: DepthTrajectory = DepthTrajectory.HOLDING
    from_depth: float = 0.0
    to_depth: float = 0.0
    delta: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this record to a plain dict, expanding the enum."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "trajectory": _enum_value(DepthTrajectory, self.trajectory),
            "from_depth": self.from_depth,
            "to_depth": self.to_depth,
            "delta": self.delta,
            "timestamp": self.timestamp,
        }


@dataclass
class DepthProfile:
    """A snapshot of an agent's depth behaviour across all dimensions.

    The profile aggregates the agent's recent depth activity into a
    single record: the average depth across recent assessments, the
    dimension on which the agent has been deepest, the regime that
    characterises that depth, the total number of probes recorded,
    and the number of deepening and surfacing actions applied. It is
    the natural unit for answering "how deep does this agent
    reason?" and is the structure returned by ``get_profile``.
    """
    agent_id: str = ""
    avg_depth: float = 0.0
    dominant_dimension: Optional[DepthDimension] = None
    regime: DepthRegime = DepthRegime.SHALLOW
    total_probes: int = 0
    deepening_count: int = 0
    surfacing_count: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this profile to a plain dict, expanding enums.

        ``dominant_dimension`` is optional and serialises to ``None``
        when absent so downstream consumers can distinguish "no
        dominant dimension" from a present-but-empty value.
        """
        return {
            "agent_id": self.agent_id,
            "avg_depth": self.avg_depth,
            "dominant_dimension": _enum_value(DepthDimension, self.dominant_dimension)
            if self.dominant_dimension is not None
            else None,
            "regime": _enum_value(DepthRegime, self.regime),
            "total_probes": self.total_probes,
            "deepening_count": self.deepening_count,
            "surfacing_count": self.surfacing_count,
            "last_updated": self.last_updated,
        }


@dataclass
class DepthStats:
    """Engine-wide aggregate statistics across all agents and dimensions.

    Scalar totals are the rolling counts of each record type the
    engine stores. The two distributions break those counts down by
    regime and by dimension, so callers can see at a glance which
    regimes and which dimensions dominate the engine's activity.
    ``avg_depth`` is the mean depth score across all probes ever
    recorded, or 0.0 if no probes exist.
    """
    total_probes: int = 0
    total_assessments: int = 0
    total_deepenings: int = 0
    total_surfacings: int = 0
    total_trajectories: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    dimension_distribution: Dict[str, int] = field(default_factory=dict)
    avg_depth: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialise these stats to a plain dict.

        The distribution dicts are already keyed by ``str`` (the
        ``.value`` of each enum), so they are copied verbatim; no
        further enum expansion is needed.
        """
        return {
            "total_probes": self.total_probes,
            "total_assessments": self.total_assessments,
            "total_deepenings": self.total_deepenings,
            "total_surfacings": self.total_surfacings,
            "total_trajectories": self.total_trajectories,
            "regime_distribution": dict(self.regime_distribution),
            "dimension_distribution": dict(self.dimension_distribution),
            "avg_depth": self.avg_depth,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Agent Cognitive Depth Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveDepth:
    """Thread-safe engine that tracks and manages the depth of an agent's reasoning.

    The engine holds seven stores keyed by identifier:

      * ``_probes``        — DepthProbe by probe_id
      * ``_assessments``   — DepthAssessment by assessment_id
      * ``_deepenings``    — DeepeningAction by action_id
      * ``_surfacings``    — SurfacingAction by action_id
      * ``_trajectories``  — DepthTrajectoryRecord by record_id
      * ``_profiles``      — DepthProfile by agent_id
      * ``_stats``         — rolling counters for fast aggregate reads

    All mutations are guarded by a single reentrant lock so that public
    methods may safely call one another without self-deadlock. The
    depth model is deliberately heuristic: depth scores are
    caller-supplied readings, regimes are banded from aggregate
    scores, and dominant dimensions are computed by mode. These
    heuristics are transparent and auditable rather than learned,
    which keeps the engine deterministic and easy to reason about.

    The engine is intentionally agnostic about how depth scores are
    produced. Callers may derive them from chain-of-thought length,
    from explicit "why" markers in the agent's output, from
    abstraction-level tagging, or from any other source. The engine's
    job is to record, aggregate, classify, and recommend — not to
    measure depth itself.
    """

    # Number of most-recent probes that contribute to an assessment.
    # The window is short enough to reflect the agent's current depth
    # behaviour and long enough to smooth out a single noisy reading.
    _ASSESSMENT_WINDOW: int = 10

    def __init__(self) -> None:
        """Initialise an empty depth engine with fresh stores and counters."""
        self._lock = threading.RLock()
        self._probes: Dict[str, DepthProbe] = {}
        self._assessments: Dict[str, DepthAssessment] = {}
        self._deepenings: Dict[str, DeepeningAction] = {}
        self._surfacings: Dict[str, SurfacingAction] = {}
        self._trajectories: Dict[str, DepthTrajectoryRecord] = {}
        self._profiles: Dict[str, DepthProfile] = {}
        # Rolling counters kept in sync with the stores above. They
        # mirror the lengths of the primary stores and let get_stats()
        # avoid full scans for the scalar totals; distributions are
        # still computed by scanning so they always reflect the
        # current state even after out-of-band mutations.
        self._stats: Dict[str, int] = {
            "total_probes": 0,
            "total_assessments": 0,
            "total_deepenings": 0,
            "total_surfacings": 0,
            "total_trajectories": 0,
        }

    # ── Probes ───────────────────────────────────────────────────────

    def probe_depth(
        self,
        agent_id: str,
        dimension: DepthDimension,
        depth_score: float,
        levels_traversed: int,
        evidence: str = "",
    ) -> DepthProbe:
        """Record a depth probe for an (agent, dimension) pair.

        ``dimension`` may be passed as a DepthDimension member or as
        its string name or value. ``depth_score`` is clamped to
        [0, 1]. ``levels_traversed`` is clamped to a non-negative
        integer. The probe is timestamped, stored, counted, and
        returned; the agent's cached profile is invalidated so the
        next access recomputes from fresh data.
        """
        with self._lock:
            dimension = _resolve_enum(DepthDimension, dimension)
            depth_score = _clamp(depth_score)
            levels_traversed = max(0, int(levels_traversed))
            probe = DepthProbe(
                probe_id=_new_id(),
                agent_id=agent_id,
                dimension=dimension,
                depth_score=depth_score,
                levels_traversed=levels_traversed,
                evidence=evidence,
                timestamp=_now(),
            )
            self._probes[probe.probe_id] = probe
            self._stats["total_probes"] += 1
            # A new probe changes the agent's depth picture, so
            # invalidate any cached profile so the next access
            # recomputes from the fresh probe set.
            self._profiles.pop(agent_id, None)
            return probe

    def list_probes(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DepthProbe]:
        """List depth probes, optionally filtered by agent.

        Probes are returned in insertion order (oldest first). A
        negative or zero ``limit`` returns an empty list; a limit
        larger than the available count returns all available probes.
        When ``agent_id`` is supplied, only probes for that agent are
        returned.
        """
        with self._lock:
            if limit <= 0:
                return []
            results: List[DepthProbe] = []
            for probe in self._probes.values():
                if agent_id is not None and probe.agent_id != agent_id:
                    continue
                results.append(probe)
                if len(results) >= limit:
                    break
            return results

    def get_probe(self, probe_id: str) -> Optional[DepthProbe]:
        """Retrieve a depth probe by its identifier.

        Returns ``None`` if no probe with the given identifier exists.
        """
        with self._lock:
            return self._probes.get(probe_id)

    # ── Assessments ──────────────────────────────────────────────────

    def assess_depth(self, agent_id: str) -> DepthAssessment:
        """Aggregate an agent's recent probes into a depth assessment.

        The assessment considers the most recent
        ``_ASSESSMENT_WINDOW`` probes for the agent.
        ``total_depth`` is the mean of their depth scores (0.0 if
        there are none). ``dominant_dimension`` is the mode of their
        dimensions, or None if there are no probes. ``regime`` is
        banded from ``total_depth`` via ``_determine_regime``.
        ``probe_count`` is the number of probes that contributed. The
        assessment is stored, counted, and returned.
        """
        with self._lock:
            agent_probes = [
                p for p in self._probes.values() if p.agent_id == agent_id
            ]
            recent = agent_probes[-self._ASSESSMENT_WINDOW:]

            if recent:
                total_depth = sum(p.depth_score for p in recent) / len(recent)
                dominant_dimension = self._mode_dimension_locked(recent)
                probe_count = len(recent)
            else:
                total_depth = 0.0
                dominant_dimension = None
                probe_count = 0

            regime = _determine_regime(total_depth)
            assessment = DepthAssessment(
                assessment_id=_new_id(),
                agent_id=agent_id,
                total_depth=round(total_depth, 4),
                dominant_dimension=dominant_dimension,
                regime=regime,
                probe_count=probe_count,
                timestamp=_now(),
            )
            self._assessments[assessment.assessment_id] = assessment
            self._stats["total_assessments"] += 1
            self._profiles.pop(agent_id, None)
            return assessment

    def list_assessments(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DepthAssessment]:
        """List depth assessments, optionally filtered by agent.

        Assessments are returned in insertion order (oldest first). A
        negative or zero ``limit`` returns an empty list; a limit
        larger than the available count returns all available
        assessments.
        """
        with self._lock:
            if limit <= 0:
                return []
            results: List[DepthAssessment] = []
            for assessment in self._assessments.values():
                if agent_id is not None and assessment.agent_id != agent_id:
                    continue
                results.append(assessment)
                if len(results) >= limit:
                    break
            return results

    def get_assessment(self, assessment_id: str) -> Optional[DepthAssessment]:
        """Retrieve a depth assessment by its identifier.

        Returns ``None`` if no assessment with the given identifier
        exists.
        """
        with self._lock:
            return self._assessments.get(assessment_id)

    # ── Deepening Actions ────────────────────────────────────────────

    def apply_deepening(
        self,
        agent_id: str,
        dimension: DepthDimension,
        move: DeepeningMove,
        rationale: str = "",
        expected_gain: float = 0.0,
    ) -> DeepeningAction:
        """Record a decision to push the agent's reasoning deeper.

        ``dimension`` and ``move`` may be passed as enum members or
        as their string names or values. ``expected_gain`` is clamped
        to [0, 1] and represents the predicted increase in depth on
        the chosen dimension. The action is timestamped, stored,
        counted, and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            dimension = _resolve_enum(DepthDimension, dimension)
            move = _resolve_enum(DeepeningMove, move)
            expected_gain = _clamp(expected_gain)
            action = DeepeningAction(
                action_id=_new_id(),
                agent_id=agent_id,
                dimension=dimension,
                move=move,
                rationale=rationale,
                expected_gain=expected_gain,
                timestamp=_now(),
            )
            self._deepenings[action.action_id] = action
            self._stats["total_deepenings"] += 1
            self._profiles.pop(agent_id, None)
            return action

    def list_deepenings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DeepeningAction]:
        """List deepening actions, optionally filtered by agent.

        Actions are returned in insertion order (oldest first). A
        negative or zero ``limit`` returns an empty list; a limit
        larger than the available count returns all available
        actions.
        """
        with self._lock:
            if limit <= 0:
                return []
            results: List[DeepeningAction] = []
            for action in self._deepenings.values():
                if agent_id is not None and action.agent_id != agent_id:
                    continue
                results.append(action)
                if len(results) >= limit:
                    break
            return results

    def get_deepening(self, action_id: str) -> Optional[DeepeningAction]:
        """Retrieve a deepening action by its identifier.

        Returns ``None`` if no action with the given identifier
        exists.
        """
        with self._lock:
            return self._deepenings.get(action_id)

    # ── Surfacing Actions ────────────────────────────────────────────

    def apply_surfacing(
        self,
        agent_id: str,
        dimension: DepthDimension,
        move: SurfacingMove,
        rationale: str = "",
        expected_relief: float = 0.0,
    ) -> SurfacingAction:
        """Record a decision to pull the agent's reasoning back toward the surface.

        ``dimension`` and ``move`` may be passed as enum members or
        as their string names or values. ``expected_relief`` is
        clamped to [0, 1] and represents the predicted reduction in
        depth on the chosen dimension. The action is timestamped,
        stored, counted, and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            dimension = _resolve_enum(DepthDimension, dimension)
            move = _resolve_enum(SurfacingMove, move)
            expected_relief = _clamp(expected_relief)
            action = SurfacingAction(
                action_id=_new_id(),
                agent_id=agent_id,
                dimension=dimension,
                move=move,
                rationale=rationale,
                expected_relief=expected_relief,
                timestamp=_now(),
            )
            self._surfacings[action.action_id] = action
            self._stats["total_surfacings"] += 1
            self._profiles.pop(agent_id, None)
            return action

    def list_surfacings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SurfacingAction]:
        """List surfacing actions, optionally filtered by agent.

        Actions are returned in insertion order (oldest first). A
        negative or zero ``limit`` returns an empty list; a limit
        larger than the available count returns all available
        actions.
        """
        with self._lock:
            if limit <= 0:
                return []
            results: List[SurfacingAction] = []
            for action in self._surfacings.values():
                if agent_id is not None and action.agent_id != agent_id:
                    continue
                results.append(action)
                if len(results) >= limit:
                    break
            return results

    def get_surfacing(self, action_id: str) -> Optional[SurfacingAction]:
        """Retrieve a surfacing action by its identifier.

        Returns ``None`` if no action with the given identifier
        exists.
        """
        with self._lock:
            return self._surfacings.get(action_id)

    # ── Trajectories ─────────────────────────────────────────────────

    def record_trajectory(
        self,
        agent_id: str,
        trajectory: DepthTrajectory,
        from_depth: float,
        to_depth: float,
    ) -> DepthTrajectoryRecord:
        """Record a single step in the agent's depth trajectory.

        ``trajectory`` may be passed as a DepthTrajectory member or
        as its string name or value. ``from_depth`` and ``to_depth``
        are clamped to [0, 1]. The signed ``delta`` is computed as
        ``to_depth - from_depth`` and is positive when the agent
        descended, negative when it surfaced. The record is
        timestamped, stored, counted, and returned.
        """
        with self._lock:
            trajectory = _resolve_enum(DepthTrajectory, trajectory)
            from_depth = _clamp(from_depth)
            to_depth = _clamp(to_depth)
            delta = round(to_depth - from_depth, 4)
            record = DepthTrajectoryRecord(
                record_id=_new_id(),
                agent_id=agent_id,
                trajectory=trajectory,
                from_depth=from_depth,
                to_depth=to_depth,
                delta=delta,
                timestamp=_now(),
            )
            self._trajectories[record.record_id] = record
            self._stats["total_trajectories"] += 1
            self._profiles.pop(agent_id, None)
            return record

    def list_trajectories(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DepthTrajectoryRecord]:
        """List trajectory records, optionally filtered by agent.

        Records are returned in insertion order (oldest first). A
        negative or zero ``limit`` returns an empty list; a limit
        larger than the available count returns all available
        records.
        """
        with self._lock:
            if limit <= 0:
                return []
            results: List[DepthTrajectoryRecord] = []
            for record in self._trajectories.values():
                if agent_id is not None and record.agent_id != agent_id:
                    continue
                results.append(record)
                if len(results) >= limit:
                    break
            return results

    def get_trajectory(self, record_id: str) -> Optional[DepthTrajectoryRecord]:
        """Retrieve a trajectory record by its identifier.

        Returns ``None`` if no record with the given identifier
        exists.
        """
        with self._lock:
            return self._trajectories.get(record_id)

    # ── Profiles ─────────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> DepthProfile:
        """Return the agent's cached depth profile, computing it if absent.

        The profile is a snapshot computed from the current stores.
        It is cached on the agent_id and invalidated whenever the
        agent's probes, assessments, or actions change. Call
        ``update_profile`` to force a refresh after out-of-band
        changes. The returned profile is a live reference into the
        cache; mutate it only via ``update_profile`` to keep the
        cache consistent.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> DepthProfile:
        """Refresh and optionally override fields of an agent's depth profile.

        The profile is first recomputed from the live stores, then
        any supplied keyword overrides (matching DepthProfile field
        names) are applied, and finally ``last_updated`` is stamped.
        This is the supported way to force a profile refresh after
        out-of-band changes, and the supported way to override a
        computed field with a caller-supplied value.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            allowed = {
                "avg_depth",
                "dominant_dimension",
                "regime",
                "total_probes",
                "deepening_count",
                "surfacing_count",
            }
            for key, value in kwargs.items():
                if key in allowed:
                    setattr(profile, key, value)
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    # ── Statistics & Reset ───────────────────────────────────────────

    def get_stats(self) -> DepthStats:
        """Compute engine-wide aggregate statistics.

        Scalar totals are read from the rolling ``_stats`` counters
        (which stay in sync with the primary stores). The regime
        distribution is computed by scanning assessments; the
        dimension distribution is computed by scanning probes.
        ``avg_depth`` is the mean depth score across all probes ever
        recorded, or 0.0 if no probes exist. Distributions are keyed
        by the ``.value`` string of each enum so the result is
        JSON-serialisable.
        """
        with self._lock:
            regime_distribution: Dict[str, int] = {}
            for assessment in self._assessments.values():
                key = _enum_value(DepthRegime, assessment.regime)
                regime_distribution[key] = regime_distribution.get(key, 0) + 1

            dimension_distribution: Dict[str, int] = {}
            depth_sum = 0.0
            for probe in self._probes.values():
                key = _enum_value(DepthDimension, probe.dimension)
                dimension_distribution[key] = dimension_distribution.get(key, 0) + 1
                depth_sum += probe.depth_score

            avg_depth = (
                round(depth_sum / len(self._probes), 4)
                if self._probes
                else 0.0
            )

            return DepthStats(
                total_probes=self._stats["total_probes"],
                total_assessments=self._stats["total_assessments"],
                total_deepenings=self._stats["total_deepenings"],
                total_surfacings=self._stats["total_surfacings"],
                total_trajectories=self._stats["total_trajectories"],
                regime_distribution=regime_distribution,
                dimension_distribution=dimension_distribution,
                avg_depth=avg_depth,
            )

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store and zeroes every rolling counter. The
        singleton reference is not touched; callers that want a fresh
        singleton should use ``reset_depth_engine`` instead.
        """
        with self._lock:
            self._probes.clear()
            self._assessments.clear()
            self._deepenings.clear()
            self._surfacings.clear()
            self._trajectories.clear()
            self._profiles.clear()
            self._stats["total_probes"] = 0
            self._stats["total_assessments"] = 0
            self._stats["total_deepenings"] = 0
            self._stats["total_surfacings"] = 0
            self._stats["total_trajectories"] = 0

    # ── Internal Helpers (callers must already hold the lock) ────────

    def _mode_dimension_locked(
        self, probes: List[DepthProbe]
    ) -> Optional[DepthDimension]:
        """Return the most frequent dimension among the supplied probes.

        Ties are broken by insertion order (the first dimension to
        reach the winning count wins, because ``dict`` preserves
        insertion order and ``max`` returns the first maximal item).
        Returns ``None`` if the list is empty.
        """
        if not probes:
            return None
        counts: Dict[DepthDimension, int] = {}
        for probe in probes:
            counts[probe.dimension] = counts.get(probe.dimension, 0) + 1
        # max over items, with stable order for ties via the dict's
        # insertion ordering.
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> DepthProfile:
        """Aggregate an agent's probes, assessments, and actions into a profile.

        ``avg_depth`` is taken from the agent's most recent assessment
        if one exists (so the profile reflects the most recent
        aggregate reading rather than a full-history mean), otherwise
        from the mean of all the agent's probes, otherwise 0.0.
        ``dominant_dimension`` and ``regime`` follow the most recent
        assessment if available, otherwise they are derived from the
        agent's probes, otherwise they default to None and SHALLOW
        respectively. ``total_probes``, ``deepening_count``, and
        ``surfacing_count`` are direct counts over the agent's
        records in the corresponding stores.
        """
        agent_probes = [
            p for p in self._probes.values() if p.agent_id == agent_id
        ]
        agent_assessments = [
            a for a in self._assessments.values() if a.agent_id == agent_id
        ]
        agent_deepenings = [
            d for d in self._deepenings.values() if d.agent_id == agent_id
        ]
        agent_surfacings = [
            s for s in self._surfacings.values() if s.agent_id == agent_id
        ]

        if agent_assessments:
            latest = agent_assessments[-1]
            avg_depth = latest.total_depth
            dominant_dimension = latest.dominant_dimension
            regime = latest.regime
        elif agent_probes:
            avg_depth = sum(p.depth_score for p in agent_probes) / len(agent_probes)
            dominant_dimension = self._mode_dimension_locked(agent_probes)
            regime = _determine_regime(avg_depth)
        else:
            avg_depth = 0.0
            dominant_dimension = None
            regime = DepthRegime.SHALLOW

        return DepthProfile(
            agent_id=agent_id,
            avg_depth=round(avg_depth, 4),
            dominant_dimension=dominant_dimension,
            regime=regime,
            total_probes=len(agent_probes),
            deepening_count=len(agent_deepenings),
            surfacing_count=len(agent_surfacings),
            last_updated=_now(),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveDepth] = None
_engine_lock = threading.Lock()


def get_depth_engine() -> AgentCognitiveDepth:
    """Get or create the singleton ``AgentCognitiveDepth`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialise from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveDepth()
        return _engine


def reset_depth_engine() -> None:
    """Reset the singleton ``AgentCognitiveDepth`` instance.

    Clears any state held by the current engine (if one exists) and
    drops the reference so the next ``get_depth_engine`` call creates
    a fresh instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
