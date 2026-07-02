from __future__ import annotations

"""Agent Cognitive Gravity — models idea space as a dynamical system with

attractor basins, where concepts exert gravitational pull based on
salience, evidence weight, and coherence.

Each concept an agent holds is treated as a body with composite mass in
an abstract idea space. Mass is a sum of contributions: evidence,
salience, connectivity, coherence, and emotional charge. A collection of
concepts forms a gravitational field with a center of mass and overall
strength. The field occupies a state (stable, perturbed, collapsing,
expanding) depending on how mass is distributed. Attractor basins are
regions where thoughts settle; their type (point, basin, ridge, saddle,
strange) determines the geometry of attraction. A thought trajectory is a
path through idea space, simulated as a random walk biased by the
gravitational pull of nearby concepts. Trajectories can remain active,
settle into a basin, escape a basin, or orbit a basin without settling.

Architecture:
    AgentCognitiveGravity (singleton)
    ├── GravityContext (a conceptual workspace for one agent)
    │   ├── IdeaMass (a concept with composite mass in idea space)
    │   ├── AttractorBasin (a region where thoughts settle)
    │   ├── ThoughtTrajectory (a simulated path through idea space)
    │   └── GravitationalField (the aggregate field of a context)
    └── GravityStats (aggregate engine statistics)
"""

import math
import random
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

class AttractorType(str, Enum):
    """The geometric form of an attractor in idea space.

    An attractor is a region thoughts tend to move toward and remain
    within. POINT is a single stable concept that draws thoughts to one
    location. BASIN is a broad region of stability surrounding a center.
    RIDGE is an attractor along which thoughts travel rather than settle.
    SADDLE attracts along one axis and repels along another, producing
    divergent flow. STRANGE is a fractal attractor producing chaotic but
    bounded trajectories that never exactly repeat.
    """
    POINT = "point"        # single stable concept
    BASIN = "basin"        # broad region of stability
    RIDGE = "ridge"        # line attractor, thoughts travel along it
    SADDLE = "saddle"      # attracts one axis, repels another
    STRANGE = "strange"    # chaotic bounded attractor


class MassContribution(str, Enum):
    """The components that sum into a concept's gravitational mass.

    Mass is composite rather than scalar so that different qualities of a
    concept can pull thoughts independently. EVIDENCE is the weight of
    supporting data behind the concept. SALIENCE is how relevant the
    concept is to the current task or goal. CONNECTIVITY is how many other
    concepts link to it. COHERENCE is how consistent it is with the
    agent's broader belief structure. EMOTIONAL is the affective charge
    the concept carries, which can attract or repel regardless of
    evidential support.
    """
    EVIDENCE = "evidence"        # weight of supporting data
    SALIENCE = "salience"        # relevance to current task
    CONNECTIVITY = "connectivity"  # number of links to other concepts
    COHERENCE = "coherence"      # consistency with belief structure
    EMOTIONAL = "emotional"      # affective charge


class TrajectoryStatus(str, Enum):
    """The lifecycle state of a thought trajectory.

    ACTIVE means the trajectory is still moving through idea space and has
    not yet reached a terminal condition. SETTLED means the trajectory has
    come to rest inside an attractor basin. ESCAPED means the trajectory
    was within a basin but has left it. ORBITING means the trajectory
    circles a basin without settling into its center.
    """
    ACTIVE = "active"      # still moving, no terminal condition
    SETTLED = "settled"    # at rest inside a basin
    ESCAPED = "escaped"    # left a basin it was within
    ORBITING = "orbiting"  # circling a basin without settling


class FieldState(str, Enum):
    """The dynamical state of a gravitational field.

    STABLE means the field is at equilibrium: mass is distributed without
    recent perturbation and concepts hold their positions. PERTURBED means
    an external force has been applied and the field is responding.
    COLLAPSING means mass is concentrating toward a small number of
    concepts, shrinking the effective idea space. EXPANDING means mass is
    spreading out, enlarging the region the field covers.
    """
    STABLE = "stable"          # at equilibrium
    PERTURBED = "perturbed"    # responding to an external force
    COLLAPSING = "collapsing"  # mass concentrating inward
    EXPANDING = "expanding"    # mass spreading outward


class ResonanceMode(str, Enum):
    """How two fields or basins interact when they overlap.

    CONSTRUCTIVE resonance means the interacting fields reinforce each
    other, increasing local mass. DESTRUCTIVE resonance means they cancel,
    reducing local mass. COUPLED resonance means they move in lockstep,
    sharing dynamics without net gain or loss.
    """
    CONSTRUCTIVE = "constructive"  # fields reinforce
    DESTRUCTIVE = "destructive"    # fields cancel
    COUPLED = "coupled"            # fields move in lockstep


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a context/concept/basin/etc."""
    return str(uuid.uuid4())[:8]


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"basin"``) and then against member names
    (e.g. ``"BASIN"``), so callers may pass either form. Raises
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


def _default_position(dim: int = 3) -> List[float]:
    """Return a zero vector of the given dimension as a default position."""
    return [0.0 for _ in range(dim)]


def _vector_distance(a: List[float], b: List[float]) -> float:
    """Euclidean distance between two equal-length vectors.

    Returns 0.0 when the vectors differ in length, since positions of
    mismatched dimension cannot be meaningfully compared.
    """
    if len(a) != len(b):
        return 0.0
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(a))))


def _sum_mass(concepts: Dict[str, "IdeaMass"]) -> float:
    """Sum the total mass across a dict of concepts."""
    return sum(c.mass for c in concepts.values())


def _center_of_mass(concepts: Dict[str, "IdeaMass"]) -> List[float]:
    """Compute the mass-weighted center of a set of concepts.

    Returns a zero vector when there are no concepts or total mass is
    zero, since the center is undefined in those cases.
    """
    if not concepts:
        return _default_position()
    total = _sum_mass(concepts)
    if total <= 0.0:
        # Fall back to an unweighted mean when masses are non-positive.
        n = len(concepts)
        dim = max((len(c.position) for c in concepts.values()), default=0)
        if dim == 0 or n == 0:
            return _default_position()
        acc = [0.0 for _ in range(dim)]
        for c in concepts.values():
            for i in range(min(dim, len(c.position))):
                acc[i] += c.position[i]
        return [v / n for v in acc]
    # Weighted mean across the longest dimension present.
    dim = max((len(c.position) for c in concepts.values()), default=0)
    if dim == 0:
        return _default_position()
    acc = [0.0 for _ in range(dim)]
    for c in concepts.values():
        w = c.mass
        for i in range(min(dim, len(c.position))):
            acc[i] += w * c.position[i]
    return [v / total for v in acc]


def _dispersion(concepts: Dict[str, "IdeaMass"], center: List[float]) -> float:
    """Mean distance of concepts from a center point.

    Returns 0.0 when there are no concepts, since dispersion is undefined
    for an empty set.
    """
    if not concepts:
        return 0.0
    total = sum(_vector_distance(c.position, center) for c in concepts.values())
    return total / len(concepts)


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class IdeaMass:
    """A concept treated as a body with composite mass in idea space.

    ``concept`` is the human-readable label. ``mass`` is the total
    gravitational mass, normally the sum of the ``contributions``.
    ``position`` is the concept's location in idea space (a vector of
    floats). ``contributions`` maps each ``MassContribution`` to a
    non-negative weight; the engine sums these to produce ``mass`` when a
    concept is added, but ``mass`` is stored independently so it can be
    tuned directly when needed.
    """
    concept_id: str = field(default_factory=_new_id)
    context_id: str = ""
    concept: str = ""
    mass: float = 1.0
    position: List[float] = field(default_factory=_default_position)
    contributions: Dict[MassContribution, float] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this concept to a plain dict.

        The ``contributions`` dict is keyed by ``MassContribution`` enums;
        each key is converted to its ``.value`` string so the result is
        JSON-serializable.
        """
        return {
            "concept_id": self.concept_id,
            "context_id": self.context_id,
            "concept": self.concept,
            "mass": self.mass,
            "position": list(self.position),
            "contributions": {
                _enum_value(MassContribution, k): v
                for k, v in self.contributions.items()
            },
            "created_at": self.created_at,
        }


@dataclass
class AttractorBasin:
    """A region of idea space where thoughts tend to settle.

    ``center_concept`` is the concept at the basin's center. The
    ``attractor_type`` determines the geometry of attraction (point, basin,
    ridge, saddle, strange). ``radius`` is the effective reach of the
    attractor: a thought within this distance of the center is considered
    inside the basin. ``stability`` in [0, 1] measures how strongly the
    basin retains thoughts that enter it. ``contained_concepts`` lists the
    concept ids that fall within the basin at creation time.
    """
    basin_id: str = field(default_factory=_new_id)
    context_id: str = ""
    center_concept: str = ""
    attractor_type: AttractorType = AttractorType.BASIN
    radius: float = 1.0
    stability: float = 0.5
    contained_concepts: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this basin to a plain dict, expanding the enum."""
        return {
            "basin_id": self.basin_id,
            "context_id": self.context_id,
            "center_concept": self.center_concept,
            "attractor_type": _enum_value(AttractorType, self.attractor_type),
            "radius": self.radius,
            "stability": self.stability,
            "contained_concepts": list(self.contained_concepts),
            "created_at": self.created_at,
        }


@dataclass
class ThoughtTrajectory:
    """A simulated path through idea space.

    ``path`` is the sequence of concept labels nearest to each visited
    position. ``positions`` is the sequence of position vectors the
    trajectory passed through. ``steps`` is the number of steps simulated.
    ``status`` tracks whether the trajectory is active, settled, escaped,
    or orbiting. ``settled_at_basin`` holds the basin id where the
    trajectory came to rest, or ``None`` if it did not settle.
    """
    trajectory_id: str = field(default_factory=_new_id)
    context_id: str = ""
    start_concept: str = ""
    path: List[str] = field(default_factory=list)
    positions: List[List[float]] = field(default_factory=list)
    steps: int = 0
    status: TrajectoryStatus = TrajectoryStatus.ACTIVE
    settled_at_basin: Optional[str] = None
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this trajectory to a plain dict, expanding the enum."""
        return {
            "trajectory_id": self.trajectory_id,
            "context_id": self.context_id,
            "start_concept": self.start_concept,
            "path": list(self.path),
            "positions": [list(p) for p in self.positions],
            "steps": self.steps,
            "status": _enum_value(TrajectoryStatus, self.status),
            "settled_at_basin": self.settled_at_basin,
            "created_at": self.created_at,
        }


@dataclass
class GravitationalField:
    """The aggregate gravitational field of a context's concepts.

    ``total_mass`` is the sum of all concept masses. ``center_of_mass`` is
    the mass-weighted mean position. ``field_strength`` is a scalar
    measure of how strongly the field pulls thoughts, derived from total
    mass and how concentrated it is. ``state`` records whether the field
    is stable, perturbed, collapsing, or expanding. ``concept_count`` is
    the number of concepts contributing to the field. ``computed_at`` is
    the timestamp of the most recent computation.
    """
    field_id: str = field(default_factory=_new_id)
    context_id: str = ""
    total_mass: float = 0.0
    center_of_mass: List[float] = field(default_factory=_default_position)
    field_strength: float = 0.0
    state: FieldState = FieldState.STABLE
    concept_count: int = 0
    computed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this field to a plain dict, expanding the enum."""
        return {
            "field_id": self.field_id,
            "context_id": self.context_id,
            "total_mass": self.total_mass,
            "center_of_mass": list(self.center_of_mass),
            "field_strength": self.field_strength,
            "state": _enum_value(FieldState, self.state),
            "concept_count": self.concept_count,
            "computed_at": self.computed_at,
        }


@dataclass
class GravityContext:
    """A conceptual workspace holding one agent's concepts and basins.

    ``concepts`` maps concept labels to their ``IdeaMass`` records.
    ``basins`` lists the basin ids created for this context. ``field_id``
    points to the most recently computed gravitational field, if any.
    ``trajectory_ids`` lists the trajectories simulated within this
    context. ``updated_at`` is refreshed whenever the context is mutated.
    """
    context_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    description: str = ""
    concepts: Dict[str, IdeaMass] = field(default_factory=dict)
    basins: List[str] = field(default_factory=list)
    field_id: Optional[str] = None
    trajectory_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this context to a plain dict.

        The nested ``concepts`` dict is serialized value-by-value via each
        ``IdeaMass``'s ``to_dict``.
        """
        return {
            "context_id": self.context_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "concepts": {
                k: v.to_dict() for k, v in self.concepts.items()
            },
            "basins": list(self.basins),
            "field_id": self.field_id,
            "trajectory_ids": list(self.trajectory_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class GravityStats:
    """Aggregate statistics over the current engine state.

    ``trajectories_by_status`` tallies trajectories keyed by their status
    ``.value``. ``basins_by_type`` tallies basins keyed by their
    attractor type ``.value``. Both dicts are keyed by strings so the
    stats serialize cleanly to JSON.
    """
    total_contexts: int = 0
    total_concepts: int = 0
    total_basins: int = 0
    total_trajectories: int = 0
    total_fields: int = 0
    trajectories_by_status: Dict[str, int] = field(default_factory=dict)
    basins_by_type: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict."""
        return {
            "total_contexts": self.total_contexts,
            "total_concepts": self.total_concepts,
            "total_basins": self.total_basins,
            "total_trajectories": self.total_trajectories,
            "total_fields": self.total_fields,
            "trajectories_by_status": dict(self.trajectories_by_status),
            "basins_by_type": dict(self.basins_by_type),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveGravity:
    """Singleton engine modeling idea space as a gravitational dynamical system.

    Holds contexts (one per agent workspace), the concepts within them,
    the attractor basins constructed over those concepts, the
    gravitational fields computed from them, and the thought trajectories
    simulated through them. All state mutations are guarded by a single
    reentrant lock so the engine is safe to call from multiple threads.
    """

    MAX_CONTEXTS: int = 500
    MAX_CONCEPTS_PER_CONTEXT: int = 1000
    MAX_TRAJECTORY_STEPS: int = 200
    # Distance below which a trajectory is considered "at" a concept.
    SETTLE_DISTANCE: float = 0.15
    # Distance below which a trajectory is considered inside a basin.
    BASIN_ENTRY_FACTOR: float = 1.0
    # Smoothing constant added to distance squared to avoid division by zero.
    GRAVITY_EPSILON: float = 1e-3
    # Weight of random noise in the trajectory step, relative to pull.
    NOISE_WEIGHT: float = 0.35

    def __init__(self) -> None:
        self._contexts: Dict[str, GravityContext] = {}
        self._basins: Dict[str, AttractorBasin] = {}
        self._trajectories: Dict[str, ThoughtTrajectory] = {}
        self._fields: Dict[str, GravitationalField] = {}
        # Index from context_id to field ids computed for that context.
        self._context_fields: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Context Management ─────────────────────────────────────────

    def register_context(
        self,
        agent_id: str,
        description: str = "",
        initial_concepts: Optional[List[Dict[str, Any]]] = None,
    ) -> GravityContext:
        """Register a new gravity context and return it.

        ``agent_id`` identifies the agent the context belongs to. An
        optional ``description`` may give free-form detail. An optional
        ``initial_concepts`` list seeds the context: each item is a dict
        with keys ``concept`` (str), ``mass`` (float), and ``position``
        (list[float]). Raises ``RuntimeError`` if the context registry is
        full.
        """
        with self._lock:
            if len(self._contexts) >= self.MAX_CONTEXTS:
                raise RuntimeError("context registry is full")
            context = GravityContext(
                agent_id=agent_id,
                description=description,
            )
            self._contexts[context.context_id] = context
            self._context_fields[context.context_id] = []
            # Seed any initial concepts provided by the caller.
            if initial_concepts:
                for item in initial_concepts:
                    concept_label = str(item.get("concept", "")).strip()
                    if not concept_label:
                        continue
                    mass = float(item.get("mass", 1.0))
                    position = item.get("position")
                    if position is None:
                        position = _default_position()
                    else:
                        position = [float(p) for p in position]
                    idea = IdeaMass(
                        context_id=context.context_id,
                        concept=concept_label,
                        mass=mass,
                        position=position,
                        contributions={},
                    )
                    context.concepts[concept_label] = idea
                context.updated_at = _now()
            return context

    def get_context(self, context_id: str) -> Optional[GravityContext]:
        """Retrieve a context by id, or ``None`` if absent."""
        with self._lock:
            return self._contexts.get(context_id)

    def list_contexts(self, agent_id: Optional[str] = None) -> list:
        """Return contexts, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all contexts are returned. Otherwise
        only contexts belonging to that agent are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            contexts = list(self._contexts.values())
        if agent_id is None:
            return contexts
        return [c for c in contexts if c.agent_id == agent_id]

    # ── Concept Management ─────────────────────────────────────────

    def add_concept(
        self,
        context_id: str,
        concept: str,
        mass: float = 1.0,
        position: Optional[List[float]] = None,
        contributions: Optional[Dict[Any, float]] = None,
    ) -> IdeaMass:
        """Add a concept to a context and return its ``IdeaMass`` record.

        ``mass`` defaults to 1.0. ``position`` defaults to a zero vector;
        when provided, it is copied so external mutation does not affect
        the stored record. ``contributions`` maps ``MassContribution``
        enums (or their value/name strings) to floats; the total mass is
        taken as the sum of contributions when present, otherwise the
        ``mass`` argument is used directly. Raises ``RuntimeError`` if the
        context is unknown or the per-context concept cap is reached.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise RuntimeError(f"unknown context {context_id!r}")
            if len(context.concepts) >= self.MAX_CONCEPTS_PER_CONTEXT:
                raise RuntimeError("concept cap reached for context")
            label = str(concept).strip()
            if not label:
                raise RuntimeError("concept label must be non-empty")
            # Resolve and normalize the position vector.
            if position is None:
                pos = _default_position()
            else:
                pos = [float(p) for p in position]
            # Resolve and normalize the contributions dict.
            resolved: Dict[MassContribution, float] = {}
            if contributions:
                for key, val in contributions.items():
                    member = _resolve_enum(MassContribution, key)
                    resolved[member] = float(val)
            # Use the contributions sum as the mass when provided and
            # non-empty; otherwise honor the explicit mass argument.
            if resolved:
                total_mass = sum(resolved.values())
            else:
                total_mass = float(mass)
            idea = IdeaMass(
                context_id=context_id,
                concept=label,
                mass=total_mass,
                position=pos,
                contributions=resolved,
            )
            context.concepts[label] = idea
            context.updated_at = _now()
            return idea

    def get_concept(self, context_id: str, concept: str) -> Optional[IdeaMass]:
        """Retrieve a concept by label within a context, or ``None``."""
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return None
            return context.concepts.get(str(concept).strip())

    def list_concepts(self, context_id: str) -> list:
        """Return the concepts registered in a context.

        Returns an empty list if the context is unknown. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return []
            return list(context.concepts.values())

    # ── Field Computation ──────────────────────────────────────────

    def compute_field(self, context_id: str) -> GravitationalField:
        """Compute the gravitational field for a context from its concepts.

        Sums all concept masses, computes the mass-weighted center of
        mass, and derives a scalar field strength from the total mass and
        the dispersion of concepts around the center. The field state is
        inferred from these metrics: empty or very low mass fields are
        collapsing, highly dispersed fields are expanding, and otherwise
        the field is stable. Raises ``RuntimeError`` if the context is
        unknown.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise RuntimeError(f"unknown context {context_id!r}")
            concepts = context.concepts
            total_mass = _sum_mass(concepts)
            center = _center_of_mass(concepts)
            disp = _dispersion(concepts, center)
            # Field strength grows with total mass and shrinks with
            # dispersion: concentrated mass pulls more strongly.
            strength = total_mass / (1.0 + disp)
            # Infer the field state from the mass distribution.
            if total_mass <= 0.0 or len(concepts) == 0:
                state = FieldState.COLLAPSING
            elif disp > 2.5 and len(concepts) >= 4:
                state = FieldState.EXPANDING
            else:
                state = FieldState.STABLE
            field = GravitationalField(
                context_id=context_id,
                total_mass=total_mass,
                center_of_mass=center,
                field_strength=strength,
                state=state,
                concept_count=len(concepts),
                computed_at=_now(),
            )
            self._fields[field.field_id] = field
            self._context_fields.setdefault(context_id, []).append(field.field_id)
            context.field_id = field.field_id
            context.updated_at = _now()
            return field

    def get_field(self, context_id: str) -> Optional[GravitationalField]:
        """Return the most recently computed field for a context, if any."""
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None or context.field_id is None:
                return None
            return self._fields.get(context.field_id)

    # ── Basin Management ───────────────────────────────────────────

    def create_basin(
        self,
        context_id: str,
        center_concept: str,
        attractor_type: AttractorType = AttractorType.BASIN,
        radius: float = 1.0,
        stability: float = 0.5,
    ) -> AttractorBasin:
        """Create an attractor basin centered on a concept.

        ``center_concept`` must be a concept already registered in the
        context; its position becomes the basin's center. ``radius`` is
        the effective reach of the attractor. ``stability`` in [0, 1] is
        clamped into range. Concepts whose distance from the center is
        within ``radius`` are listed in ``contained_concepts``. Raises
        ``RuntimeError`` if the context or center concept is unknown.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise RuntimeError(f"unknown context {context_id!r}")
            label = str(center_concept).strip()
            center_idea = context.concepts.get(label)
            if center_idea is None:
                raise RuntimeError(f"unknown center concept {label!r}")
            atype = _resolve_enum(AttractorType, attractor_type)
            rad = max(0.0, float(radius))
            stab = _clamp(float(stability))
            # Find all concepts within the basin's radius of the center.
            contained: List[str] = []
            for concept_label, idea in context.concepts.items():
                if _vector_distance(idea.position, center_idea.position) <= rad:
                    contained.append(concept_label)
            basin = AttractorBasin(
                context_id=context_id,
                center_concept=label,
                attractor_type=atype,
                radius=rad,
                stability=stab,
                contained_concepts=contained,
            )
            self._basins[basin.basin_id] = basin
            context.basins.append(basin.basin_id)
            context.updated_at = _now()
            return basin

    def get_basin(self, basin_id: str) -> Optional[AttractorBasin]:
        """Retrieve a basin by id, or ``None`` if absent."""
        with self._lock:
            return self._basins.get(basin_id)

    def list_basins(self, context_id: str) -> list:
        """Return the basins created for a context.

        Returns an empty list if the context is unknown. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return []
            basins = []
            for bid in context.basins:
                basin = self._basins.get(bid)
                if basin is not None:
                    basins.append(basin)
            return basins

    # ── Trajectory Prediction ──────────────────────────────────────

    def predict_trajectory(
        self,
        context_id: str,
        start_concept: str,
        steps: int = 10,
        step_size: float = 0.1,
    ) -> ThoughtTrajectory:
        """Predict a thought path through idea space from a starting concept.

        Simulates a random walk biased by gravitational pull: at each step
        the net force from all concepts is computed (force proportional to
        mass over squared distance, directed toward each concept), a small
        random noise component is added, and the position advances by
        ``step_size`` along the resulting direction.

        The trajectory records the nearest concept label at each step as
        its ``path`` and the full position sequence as its ``positions``.
        Entering a basin and reaching the settle distance sets status
        SETTLED (with ``settled_at_basin``); leaving a basin after entry
        sets ESCAPED; lingering near a basin without settling sets
        ORBITING; otherwise the status stays ACTIVE.

        Raises ``RuntimeError`` if the context or start concept is
        unknown, or if ``steps`` is non-positive.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise RuntimeError(f"unknown context {context_id!r}")
            label = str(start_concept).strip()
            start_idea = context.concepts.get(label)
            if start_idea is None:
                raise RuntimeError(f"unknown start concept {label!r}")
            n_steps = int(steps)
            if n_steps <= 0:
                raise RuntimeError("steps must be positive")
            if n_steps > self.MAX_TRAJECTORY_STEPS:
                n_steps = self.MAX_TRAJECTORY_STEPS
            ssize = max(0.0, float(step_size))
            # Snapshot the concepts and basins to operate on stable data.
            concepts = list(context.concepts.values())
            basins = [
                self._basins.get(bid) for bid in context.basins
            ]
            basins = [b for b in basins if b is not None]

            current = list(start_idea.position)
            dim = len(current)
            path: List[str] = [label]
            positions: List[List[float]] = [list(current)]
            status = TrajectoryStatus.ACTIVE
            settled_basin: Optional[str] = None

            # Track whether the trajectory has ever entered a basin, so
            # that leaving one can be flagged as ESCAPED.
            entered_basin: Optional[str] = None
            orbit_counter = 0

            for _ in range(n_steps):
                if status == TrajectoryStatus.SETTLED:
                    # Once settled, the trajectory stays put.
                    positions.append(list(current))
                    path.append(path[-1])
                    continue
                # Compute the net gravitational pull from every concept.
                force = [0.0 for _ in range(dim)]
                for idea in concepts:
                    if idea.mass <= 0.0:
                        continue
                    diff = [
                        idea.position[i] - current[i]
                        for i in range(min(dim, len(idea.position)))
                    ]
                    dist_sq = sum(d * d for d in diff)
                    denom = dist_sq + self.GRAVITY_EPSILON
                    # Inverse-square pull scaled by mass.
                    mag = idea.mass / denom
                    for i in range(len(diff)):
                        force[i] += diff[i] * mag
                # Add a random noise component so the walk is stochastic.
                noise = [
                    (random.random() - 0.5) * 2.0 * self.NOISE_WEIGHT
                    for _ in range(dim)
                ]
                step = [force[i] + noise[i] for i in range(dim)]
                # Normalize the step to the requested step size when the
                # combined vector is non-negligible; otherwise drift by
                # the noise alone.
                step_norm = math.sqrt(sum(s * s for s in step))
                if step_norm > 1e-9 and ssize > 0.0:
                    step = [s * ssize / step_norm for s in step]
                elif step_norm > 1e-9:
                    step = [s / step_norm for s in step]
                # Advance the current position.
                current = [current[i] + step[i] for i in range(dim)]
                positions.append(list(current))
                # Record the nearest concept as the visited node.
                nearest_label = label
                nearest_dist = float("inf")
                for idea in concepts:
                    d = _vector_distance(idea.position, current)
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest_label = idea.concept
                path.append(nearest_label)
                # Check basin interactions to update status.
                inside_any = False
                for basin in basins:
                    center_idea = context.concepts.get(basin.center_concept)
                    if center_idea is None:
                        continue
                    bd = _vector_distance(center_idea.position, current)
                    if bd <= basin.radius * self.BASIN_ENTRY_FACTOR:
                        inside_any = True
                        if entered_basin is None:
                            entered_basin = basin.basin_id
                        # Settle if close enough to the center, scaled by
                        # the basin's stability.
                        settle_thr = self.SETTLE_DISTANCE * (1.0 + basin.stability)
                        if bd <= settle_thr:
                            status = TrajectoryStatus.SETTLED
                            settled_basin = basin.basin_id
                            break
                if status == TrajectoryStatus.SETTLED:
                    continue
                # If we were in a basin before but are not now, escape.
                if entered_basin is not None and not inside_any:
                    status = TrajectoryStatus.ESCAPED
                    settled_basin = None
                    continue
                # If we keep re-entering the same basin without settling,
                # count it as orbiting after a few cycles.
                if entered_basin is not None and inside_any:
                    orbit_counter += 1
                    if orbit_counter >= 3 and status == TrajectoryStatus.ACTIVE:
                        status = TrajectoryStatus.ORBITING

            trajectory = ThoughtTrajectory(
                context_id=context_id,
                start_concept=label,
                path=path,
                positions=positions,
                steps=n_steps,
                status=status,
                settled_at_basin=settled_basin,
            )
            self._trajectories[trajectory.trajectory_id] = trajectory
            context.trajectory_ids.append(trajectory.trajectory_id)
            context.updated_at = _now()
            return trajectory

    def get_trajectory(self, trajectory_id: str) -> Optional[ThoughtTrajectory]:
        """Retrieve a trajectory by id, or ``None`` if absent."""
        with self._lock:
            return self._trajectories.get(trajectory_id)

    def list_trajectories(
        self,
        context_id: Optional[str] = None,
        status: Optional[Any] = None,
    ) -> list:
        """Return trajectories, optionally filtered by context and status.

        ``context_id`` filters to trajectories in a given context.
        ``status`` accepts a ``TrajectoryStatus`` member or its value/name
        string and filters by lifecycle state. The returned list is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            trajectories = list(self._trajectories.values())
        if context_id is not None:
            trajectories = [t for t in trajectories if t.context_id == context_id]
        if status is not None:
            member = _resolve_enum(TrajectoryStatus, status)
            trajectories = [t for t in trajectories if t.status == member]
        return trajectories

    def check_basin_escape(self, trajectory_id: str) -> dict:
        """Check whether a trajectory has escaped a basin.

        Returns a dict with keys ``trajectory_id``, ``escaped`` (bool),
        ``status`` (the trajectory's current status value), ``basin_id``
        (the associated basin or ``None``), and ``reason`` (a short
        explanation). A trajectory counts as escaped only if it entered a
        basin and then left it. Returns ``escaped=False`` with
        ``reason="unknown trajectory"`` if the id is not found.
        """
        with self._lock:
            trajectory = self._trajectories.get(trajectory_id)
            if trajectory is None:
                return {
                    "trajectory_id": trajectory_id,
                    "escaped": False,
                    "status": None,
                    "basin_id": None,
                    "reason": "unknown trajectory",
                }
            status_value = trajectory.status.value
            basin_id = trajectory.settled_at_basin
            if trajectory.status == TrajectoryStatus.ESCAPED:
                return {
                    "trajectory_id": trajectory_id,
                    "escaped": True,
                    "status": status_value,
                    "basin_id": basin_id,
                    "reason": "trajectory status is ESCAPED",
                }
            # Re-examine the trajectory's positions to see whether it
            # currently lies inside any basin of its context.
            context = self._contexts.get(trajectory.context_id)
            basins = []
            if context is not None:
                for bid in context.basins:
                    b = self._basins.get(bid)
                    if b is not None:
                        basins.append(b)
            if not basins or not trajectory.positions:
                if trajectory.status == TrajectoryStatus.SETTLED:
                    return {
                        "trajectory_id": trajectory_id,
                        "escaped": False,
                        "status": status_value,
                        "basin_id": basin_id,
                        "reason": "trajectory is settled in a basin",
                    }
                return {
                    "trajectory_id": trajectory_id,
                    "escaped": False,
                    "status": status_value,
                    "basin_id": basin_id,
                    "reason": "no basin entry recorded",
                }
            # Look at the last position to decide current containment.
            last_pos = trajectory.positions[-1]
            currently_inside = False
            for basin in basins:
                center_idea = context.concepts.get(basin.center_concept)
                if center_idea is None:
                    continue
                if _vector_distance(center_idea.position, last_pos) <= basin.radius:
                    currently_inside = True
                    break
            if currently_inside:
                return {
                    "trajectory_id": trajectory_id,
                    "escaped": False,
                    "status": status_value,
                    "basin_id": basin_id,
                    "reason": "trajectory is currently inside a basin",
                }
            return {
                "trajectory_id": trajectory_id,
                "escaped": True,
                "status": status_value,
                "basin_id": basin_id,
                "reason": "trajectory is outside all basins",
            }

    # ── Perturbation ───────────────────────────────────────────────

    def perturb_field(
        self,
        context_id: str,
        concept: str,
        force_vector: List[float],
    ) -> GravitationalField:
        """Apply a perturbation to a concept and recompute the field.

        The ``force_vector`` is added to the named concept's position,
        shifting it through idea space. This models an external
        perturbation (a new argument, a contradictory observation) pushing
        on one concept. The field is then recomputed; its state is set to
        PERTURBED regardless of the inferred state, since a perturbation
        has just been applied. Raises ``RuntimeError`` if the context or
        concept is unknown.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise RuntimeError(f"unknown context {context_id!r}")
            label = str(concept).strip()
            idea = context.concepts.get(label)
            if idea is None:
                raise RuntimeError(f"unknown concept {label!r}")
            force = [float(f) for f in force_vector]
            # Shift the concept's position by the force vector.
            new_pos = list(idea.position)
            for i in range(min(len(new_pos), len(force))):
                new_pos[i] += force[i]
            # Extend the position vector if the force is higher-dimensional.
            if len(force) > len(new_pos):
                new_pos.extend(force[len(new_pos):])
            idea.position = new_pos
            context.updated_at = _now()
            # Recompute the field, then override the state to PERTURBED.
            concepts = context.concepts
            total_mass = _sum_mass(concepts)
            center = _center_of_mass(concepts)
            disp = _dispersion(concepts, center)
            strength = total_mass / (1.0 + disp)
            field = GravitationalField(
                context_id=context_id,
                total_mass=total_mass,
                center_of_mass=center,
                field_strength=strength,
                state=FieldState.PERTURBED,
                concept_count=len(concepts),
                computed_at=_now(),
            )
            self._fields[field.field_id] = field
            self._context_fields.setdefault(context_id, []).append(field.field_id)
            context.field_id = field.field_id
            context.updated_at = _now()
            return field

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> GravityStats:
        """Compute aggregate statistics over the current engine state.

        Counts contexts, concepts, basins, trajectories, and fields;
        tallies trajectories by status and basins by attractor type. The
        breakdown dicts are keyed by the enum ``.value`` strings so the
        stats serialize cleanly to JSON.
        """
        with self._lock:
            total_contexts = len(self._contexts)
            total_concepts = sum(len(c.concepts) for c in self._contexts.values())
            total_basins = len(self._basins)
            total_trajectories = len(self._trajectories)
            total_fields = len(self._fields)
            by_status: Dict[str, int] = {}
            for traj in self._trajectories.values():
                key = traj.status.value
                by_status[key] = by_status.get(key, 0) + 1
            by_type: Dict[str, int] = {}
            for basin in self._basins.values():
                key = basin.attractor_type.value
                by_type[key] = by_type.get(key, 0) + 1
            return GravityStats(
                total_contexts=total_contexts,
                total_concepts=total_concepts,
                total_basins=total_basins,
                total_trajectories=total_trajectories,
                total_fields=total_fields,
                trajectories_by_status=by_status,
                basins_by_type=by_type,
            )

    # ── Maintenance ────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests."""
        with self._lock:
            self._contexts.clear()
            self._basins.clear()
            self._trajectories.clear()
            self._fields.clear()
            self._context_fields.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_gravity_engine() -> AgentCognitiveGravity:
    """Get or create the singleton ``AgentCognitiveGravity`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveGravity()
        return _engine


def reset_gravity_engine() -> None:
    """Reset the singleton ``AgentCognitiveGravity`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_gravity_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
