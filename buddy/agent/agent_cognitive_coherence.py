"""
Agent Cognitive Coherence Engine — measuring and managing the system-level
relational integrity of an agent's cognitive network.

Coherence is the degree to which the parts of an agent's cognitive state
hang together. A belief, a reasoning trace, a goal, and an action do not
exist in isolation; they stand in relations to one another. One belief may
explain another, a goal may enable an action, a reasoning step may support
a conclusion, or two beliefs may contradict. Coherence is the system-level
property that captures whether these relations mutually support one another
or pull apart. It is distinct from belief_state, which tracks individual
beliefs and their probabilities: coherence tracks the relational integrity
of the entire cognitive network — whether the parts form a coherent whole
or a fragmented collection.

This engine draws on explanatory coherence theory, in particular Thagard's
ECHO model, where coherence is treated as a constraint satisfaction
problem. The cognitive network is modeled as a graph of nodes (beliefs,
reasoning traces, goals, actions) connected by relations that either
cohere (support, explain, enable) or inhibit (contradict, conflict). The
guiding principle is that a coherent system is one where the parts hang
together: positive links pull connected nodes toward mutual activation
while negative links push them apart, and the system is coherent to the
extent that positive links dominate. Coherence is not a single scalar but
a family of facets: explanatory coherence (beliefs explain each other),
logical coherence (no contradictions), teleological coherence (actions
serve goals), narrative coherence (the story makes sense), conceptual
coherence (concepts align), and epistemic coherence (knowledge sources
agree). A snapshot reduces these facets to a single total_coherence score
for tracking, while the facet breakdown is retained for diagnosis.

Operationally, the engine registers CoherenceNodes (beliefs, reasoning
traces, goals, actions, ...) and links them with CoherenceRelations of a
given RelationType and strength. A CoherenceSnapshot aggregates an agent's
nodes and relations into a total_coherence score in [0, 1] — the
support-weighted balance of cohering versus inhibiting relations — and
classifies the agent's CoherenceRegime from FRAGMENTED (parts don't
connect) through LOOSE, PARTIAL, and COHERENT to INTEGRATED and UNIFIED
(single coherent whole). When coherence is low, a RepairAttempt applies a
RepairStrategy such as resolving a contradiction, adding a bridging
belief, reweighting a relation, removing a problematic node, splitting
into separate contexts, or reframing the relation. A TrajectoryRecord
captures whether coherence is stabilizing, stable, destabilizing,
fluctuating, collapsing, or consolidating. A CoherenceProfile holds
per-agent aggregates and CoherenceStats summarizes engine-wide activity.
All state mutations are guarded by a reentrant lock so the engine is safe
to call from multiple threads, including from within its own methods.

Architecture:
    AgentCognitiveCoherence (singleton)
    ├── CoherenceNode      (a belief, reasoning trace, goal, or action)
    ├── CoherenceRelation  (a typed, weighted edge between two nodes)
    ├── CoherenceSnapshot  (aggregate coherence state at a point in time)
    ├── RepairAttempt      (one application of a repair strategy)
    ├── TrajectoryRecord   (a coherence change between two points)
    ├── CoherenceProfile   (per-agent aggregate coherence picture)
    └── CoherenceStats     (engine-wide aggregate statistics)

The engine is intentionally dependency-free so it can run in any Buddy
runtime without extra packages.
"""

from __future__ import annotations

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

class CoherenceFacet(str, Enum):
    """One facet along which cognitive coherence can be assessed.

    Coherence is not a single scalar; it is a family of related but
    distinct properties of the cognitive network. EXPLANATORY coherence
    holds when beliefs explain each other — one belief makes another
    intelligible. LOGICAL coherence holds when there are no
    contradictions among the agent's commitments. TELEOLOGICAL coherence
    holds when actions serve the agent's goals. NARRATIVE coherence holds
    when the agent's evolving story makes sense as a story. CONCEPTUAL
    coherence holds when the concepts the agent deploys align with one
    another. EPISTEMIC coherence holds when the agent's knowledge sources
    agree rather than disagree.
    """
    EXPLANATORY = "explanatory"  # beliefs explain each other
    LOGICAL = "logical"          # no contradictions
    TELEOLOGICAL = "teleological"  # actions serve goals
    NARRATIVE = "narrative"      # the story makes sense
    CONCEPTUAL = "conceptual"    # concepts align
    EPISTEMIC = "epistemic"      # knowledge sources agree


class CoherenceRegime(str, Enum):
    """The overall coherence regime of an agent's cognitive network.

    Regimes are ordered from least to most coherent. FRAGMENTED means the
    parts do not connect at all. LOOSE means there are weak connections
    but no strong mutual support. PARTIAL means some facets are coherent
    while others are not. COHERENT means the network is mostly coherent.
    INTEGRATED means the parts are tightly coherent. UNIFIED means the
    network forms a single coherent whole.
    """
    FRAGMENTED = "fragmented"  # parts don't connect
    LOOSE = "loose"            # weak connections
    PARTIAL = "partial"        # some facets coherent
    COHERENT = "coherent"      # mostly coherent
    INTEGRATED = "integrated"  # tightly coherent
    UNIFIED = "unified"        # single coherent whole


class RelationType(str, Enum):
    """The kind of relation one cognitive node bears to another.

    SUPPORTS means A supports B (positive, general). CONTRADICTS means A
    contradicts B (negative, logical). EXPLAINS means A explains B
    (positive, explanatory). ENABLES means A enables B (positive,
    teleological). CONFLICTS means A conflicts with B but not on logical
    grounds — a tension rather than a formal contradiction. COHERES_WITH
    means A coheres with B (positive, generic mutual fit).
    """
    SUPPORTS = "supports"        # A supports B
    CONTRADICTS = "contradicts"  # A contradicts B
    EXPLAINS = "explains"        # A explains B
    ENABLES = "enables"          # A enables B
    CONFLICTS = "conflicts"      # A conflicts with B (not logically)
    COHERES_WITH = "coheres_with"  # A coheres with B


class RepairStrategy(str, Enum):
    """A strategy for repairing low coherence in a cognitive network.

    RESOLVE_CONTRADICTION removes a logical contradiction by revising one
    of the contradicting nodes. ADD_BRIDGE introduces a bridging belief
    that connects two otherwise disconnected clusters. REWEIGHT changes
    the strength of a relation so it contributes more or less to
    coherence. REMOVE_NODE removes a problematic node that disrupts
    coherence. SPLIT_CONTEXT separates two conflicting nodes into
    different contexts so they no longer inhibit each other. REFRAME
    reframes the relation itself — for example, recasting a conflict as a
    tension or an explanation as a support.
    """
    RESOLVE_CONTRADICTION = "resolve_contradiction"  # resolve a contradiction
    ADD_BRIDGE = "add_bridge"                         # add a bridging belief
    REWEIGHT = "reweight"                             # reweight a relation
    REMOVE_NODE = "remove_node"                       # remove a node
    SPLIT_CONTEXT = "split_context"                   # split into contexts
    REFRAME = "reframe"                               # reframe the relation


class CoherenceTrajectory(str, Enum):
    """The direction and character of coherence change over time.

    STABILIZING means coherence is increasing. STABLE means coherence is
    holding roughly constant. DESTABILIZING means coherence is
    decreasing. FLUCTUATING means coherence is alternating up and down
    rather than converging. COLLAPSING means coherence is dropping
    rapidly. CONSOLIDATING means coherence is rising rapidly.
    """
    STABILIZING = "stabilizing"    # coherence increasing
    STABLE = "stable"              # coherence holding
    DESTABILIZING = "destabilizing"  # coherence decreasing
    FLUCTUATING = "fluctuating"    # alternating
    COLLAPSING = "collapsing"      # rapid coherence loss
    CONSOLIDATING = "consolidating"  # rapid coherence gain


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a node/relation/snapshot/etc."""
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
    member values (e.g. ``"supports"``) and then against member names
    (e.g. ``"SUPPORTS"``), so callers may pass either form. Raises
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


def _determine_regime(coherence_score: float) -> CoherenceRegime:
    """Classify a total coherence score in [0, 1] into a coherence regime.

    The thresholds partition [0, 1] into six bands: below 0.2 is
    FRAGMENTED (parts don't connect), below 0.4 is LOOSE (weak
    connections), below 0.6 is PARTIAL (some facets coherent), below 0.8
    is COHERENT (mostly coherent), below 0.95 is INTEGRATED (tightly
    coherent), and 0.95 and above is UNIFIED (single coherent whole). The
    input is clamped to [0, 1] before classification so out-of-range
    values cannot produce an inconsistent regime.
    """
    score = _clamp(coherence_score)
    if score < 0.2:
        return CoherenceRegime.FRAGMENTED
    if score < 0.4:
        return CoherenceRegime.LOOSE
    if score < 0.6:
        return CoherenceRegime.PARTIAL
    if score < 0.8:
        return CoherenceRegime.COHERENT
    if score < 0.95:
        return CoherenceRegime.INTEGRATED
    return CoherenceRegime.UNIFIED


def _compute_contradiction_count(relations: List[CoherenceRelation]) -> int:
    """Count relations that are contradictions or conflicts.

    A relation counts as a contradiction when its ``relation`` is
    ``CONTRADICTS`` (a logical contradiction) or ``CONFLICTS`` (a
    non-logical tension). Both inhibit coherence and are reported together
    as the network's contradiction count.
    """
    count = 0
    for relation in relations:
        if relation.relation in (RelationType.CONTRADICTS, RelationType.CONFLICTS):
            count += 1
    return count


# Relation types that pull nodes toward mutual activation (positive links).
_POSITIVE_RELATIONS = frozenset({
    RelationType.SUPPORTS,
    RelationType.EXPLAINS,
    RelationType.ENABLES,
    RelationType.COHERES_WITH,
})

# Relation types that push nodes apart (negative links).
_NEGATIVE_RELATIONS = frozenset({
    RelationType.CONTRADICTS,
    RelationType.CONFLICTS,
})

# Heuristic mapping from a relation type to the coherence facet it most
# contributes to. Used by ``take_snapshot`` to pick a dominant facet from
# the agent's currently held relations.
_RELATION_FACET: Dict[RelationType, CoherenceFacet] = {
    RelationType.SUPPORTS: CoherenceFacet.CONCEPTUAL,
    RelationType.CONTRADICTS: CoherenceFacet.LOGICAL,
    RelationType.EXPLAINS: CoherenceFacet.EXPLANATORY,
    RelationType.ENABLES: CoherenceFacet.TELEOLOGICAL,
    RelationType.CONFLICTS: CoherenceFacet.NARRATIVE,
    RelationType.COHERES_WITH: CoherenceFacet.EPISTEMIC,
}


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CoherenceNode:
    """A single node in an agent's cognitive coherence network.

    A node is one belief, reasoning trace, goal, action, or other
    cognitive element that can stand in relation to other nodes.
    ``node_type`` is a free-form label (e.g. ``"belief"``, ``"goal"``,
    ``"action"``, ``"reasoning"``) used for filtering and display.
    ``content`` is a human-readable description of what the node asserts
    or represents. ``weight`` in [0, 1] is the node's salience — how
    central it is to the agent's current cognitive state — and may be
    used downstream to weight the relations it participates in.
    ``timestamp`` is an ISO-8601 UTC timestamp set at creation.
    """
    node_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    label: str = ""
    node_type: str = ""
    content: str = ""
    weight: float = 0.5
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this node to a plain dict."""
        return {
            "node_id": self.node_id,
            "agent_id": self.agent_id,
            "label": self.label,
            "node_type": self.node_type,
            "content": self.content,
            "weight": self.weight,
            "timestamp": self.timestamp,
        }


@dataclass
class CoherenceRelation:
    """A typed, weighted edge between two coherence nodes.

    A relation asserts that ``source_id`` bears ``relation`` to
    ``target_id``. ``relation`` is the ``RelationType`` (SUPPORTS,
    CONTRADICTS, EXPLAINS, ENABLES, CONFLICTS, COHERES_WITH).
    ``strength`` in [0, 1] is how strongly the relation holds — a weak
    support contributes less to coherence than a strong one, and a weak
    contradiction detracts less than a strong one. ``timestamp`` is an
    ISO-8601 UTC timestamp set at creation.
    """
    relation_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    source_id: str = ""
    target_id: str = ""
    relation: RelationType = RelationType.SUPPORTS
    strength: float = 0.5
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this relation to a plain dict, expanding the enum."""
        return {
            "relation_id": self.relation_id,
            "agent_id": self.agent_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": _enum_value(RelationType, self.relation),
            "strength": self.strength,
            "timestamp": self.timestamp,
        }


@dataclass
class CoherenceSnapshot:
    """A point-in-time summary of an agent's cognitive coherence.

    A snapshot aggregates the agent's currently registered nodes and
    relations into a single ``total_coherence`` score in [0, 1] — the
    support-weighted balance of cohering versus inhibiting relations.
    ``dominant_facet`` is the coherence facet with the most supporting
    relations at snapshot time (or ``None`` when there are no supporting
    relations). ``regime`` classifies the score from FRAGMENTED through
    UNIFIED. ``contradiction_count`` is the number of CONTRADICTS or
    CONFLICTS relations currently held. ``node_count`` and
    ``relation_count`` record the size of the network at snapshot time.
    ``timestamp`` is an ISO-8601 UTC timestamp set at creation.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    total_coherence: float = 0.0
    dominant_facet: Optional[CoherenceFacet] = None
    regime: CoherenceRegime = CoherenceRegime.FRAGMENTED
    node_count: int = 0
    relation_count: int = 0
    contradiction_count: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums.

        The optional ``dominant_facet`` is emitted as ``None`` when absent
        and as its enum ``.value`` otherwise, so the serialized form is
        JSON-clean and unambiguous.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "total_coherence": self.total_coherence,
            "dominant_facet": (
                self.dominant_facet.value
                if isinstance(self.dominant_facet, CoherenceFacet)
                else self.dominant_facet
            ),
            "regime": _enum_value(CoherenceRegime, self.regime),
            "node_count": self.node_count,
            "relation_count": self.relation_count,
            "contradiction_count": self.contradiction_count,
            "timestamp": self.timestamp,
        }


@dataclass
class RepairAttempt:
    """One application of a repair strategy to improve coherence.

    When coherence is low the engine (or its caller) may attempt a
    repair. ``strategy`` is the ``RepairStrategy`` applied;
    ``target_relation_id`` is the relation the repair targets, when
    applicable; ``snapshot_id`` is the snapshot that motivated the repair,
    when known; ``rationale`` is a free-form explanation of why the
    strategy was chosen; ``success`` records whether the repair is
    considered to have succeeded. ``timestamp`` is an ISO-8601 UTC
    timestamp set at creation.
    """
    attempt_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    snapshot_id: Optional[str] = None
    strategy: RepairStrategy = RepairStrategy.RESOLVE_CONTRADICTION
    target_relation_id: Optional[str] = None
    rationale: str = ""
    success: bool = True
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this repair attempt to a plain dict, expanding the enum."""
        return {
            "attempt_id": self.attempt_id,
            "agent_id": self.agent_id,
            "snapshot_id": self.snapshot_id,
            "strategy": _enum_value(RepairStrategy, self.strategy),
            "target_relation_id": self.target_relation_id,
            "rationale": self.rationale,
            "success": self.success,
            "timestamp": self.timestamp,
        }


@dataclass
class TrajectoryRecord:
    """A recorded change in coherence between two points in time.

    A trajectory record captures a single step in the agent's coherence
    history. ``trajectory`` is the ``CoherenceTrajectory`` classification
    of the step (stabilizing, stable, destabilizing, fluctuating,
    collapsing, consolidating). ``from_coherence`` and ``to_coherence``
    are the total coherence scores at the start and end of the step;
    ``delta`` is ``to_coherence - from_coherence``. ``timestamp`` is an
    ISO-8601 UTC timestamp set at creation.
    """
    record_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    trajectory: CoherenceTrajectory = CoherenceTrajectory.STABLE
    from_coherence: float = 0.0
    to_coherence: float = 0.0
    delta: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this trajectory record to a plain dict, expanding the enum."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "trajectory": _enum_value(CoherenceTrajectory, self.trajectory),
            "from_coherence": self.from_coherence,
            "to_coherence": self.to_coherence,
            "delta": self.delta,
            "timestamp": self.timestamp,
        }


@dataclass
class CoherenceProfile:
    """Per-agent aggregate coherence picture.

    ``avg_coherence`` is the mean ``total_coherence`` over the agent's
    currently held snapshots. ``dominant_facet`` is the facet that has
    appeared most often as the snapshot's dominant facet, and ``regime``
    is the regime implied by ``avg_coherence``. ``total_nodes``,
    ``total_relations``, and ``total_repairs`` are counts of the agent's
    currently held nodes, relations, and repair attempts.
    ``last_updated`` is an ISO-8601 UTC timestamp refreshed whenever the
    profile is recomputed.
    """
    agent_id: str = ""
    avg_coherence: float = 0.0
    dominant_facet: Optional[CoherenceFacet] = None
    regime: CoherenceRegime = CoherenceRegime.FRAGMENTED
    total_nodes: int = 0
    total_relations: int = 0
    total_repairs: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enums.

        The optional ``dominant_facet`` is emitted as ``None`` when absent
        and as its enum ``.value`` otherwise.
        """
        return {
            "agent_id": self.agent_id,
            "avg_coherence": self.avg_coherence,
            "dominant_facet": (
                self.dominant_facet.value
                if isinstance(self.dominant_facet, CoherenceFacet)
                else self.dominant_facet
            ),
            "regime": _enum_value(CoherenceRegime, self.regime),
            "total_nodes": self.total_nodes,
            "total_relations": self.total_relations,
            "total_repairs": self.total_repairs,
            "last_updated": self.last_updated,
        }


@dataclass
class CoherenceStats:
    """Aggregate statistics over the coherence engine's state.

    Counts of nodes, relations, snapshots, repairs, and trajectories are
    taken from the cumulative telemetry counters (which survive registry
    trimming). ``regime_distribution`` tallies the currently held
    snapshots by regime; ``facet_distribution`` tallies them by dominant
    facet. ``avg_coherence`` is the mean ``total_coherence`` over the
    currently held snapshots (0.0 when none exist).
    """
    total_nodes: int = 0
    total_relations: int = 0
    total_snapshots: int = 0
    total_repairs: int = 0
    total_trajectories: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    facet_distribution: Dict[str, int] = field(default_factory=dict)
    avg_coherence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict with JSON-clean keys.

        The distribution dicts are copied so the serialized form is
        independent of the live stats object.
        """
        return {
            "total_nodes": self.total_nodes,
            "total_relations": self.total_relations,
            "total_snapshots": self.total_snapshots,
            "total_repairs": self.total_repairs,
            "total_trajectories": self.total_trajectories,
            "regime_distribution": dict(self.regime_distribution),
            "facet_distribution": dict(self.facet_distribution),
            "avg_coherence": self.avg_coherence,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCoherence:
    """Cognitive coherence engine with nodes, relations, snapshots, and repairs.

    The engine maintains registries of coherence nodes, relations,
    snapshots, repair attempts, trajectory records, and per-agent
    coherence profiles. Nodes are the beliefs, reasoning traces, goals,
    and actions of the cognitive network; relations are the typed, weighted
    edges between them. A snapshot aggregates an agent's nodes and
    relations into a total coherence score and a regime classification.
    When coherence is low, a repair attempt records an applied repair
    strategy. A trajectory record captures the direction of coherence
    change between two points in time. Cumulative counters in ``_stats``
    survive trimming of the bounded registries so lifetime telemetry is
    preserved. All state mutations are guarded by a single reentrant lock
    so the engine is safe to call from multiple threads, including from
    within its own locked methods.
    """

    # Capacity limits to bound memory use per engine instance.
    MAX_NODES: int = 5000
    MAX_RELATIONS: int = 10000
    MAX_SNAPSHOTS: int = 5000
    MAX_REPAIRS: int = 2000
    MAX_TRAJECTORIES: int = 2000
    MAX_PROFILES: int = 1000

    def __init__(self) -> None:
        self._nodes: Dict[str, CoherenceNode] = {}
        self._relations: Dict[str, CoherenceRelation] = {}
        self._snapshots: Dict[str, CoherenceSnapshot] = {}
        self._repairs: Dict[str, RepairAttempt] = {}
        self._trajectories: Dict[str, TrajectoryRecord] = {}
        self._profiles: Dict[str, CoherenceProfile] = {}
        # Cumulative telemetry counters that survive registry trimming.
        self._stats: Dict[str, int] = {}
        self._lock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal helpers ───────────────────────────────────────────

    def _bump(self, key: str, amount: int = 1) -> None:
        """Increment a cumulative telemetry counter. Caller holds the lock."""
        self._stats[key] = self._stats.get(key, 0) + amount

    def _trim(self, registry: Dict[str, Any], limit: int) -> None:
        """Drop the oldest entry from a registry if it exceeds ``limit``.

        Caller holds the lock. Uses dict insertion order (Python 3.7+) to
        identify the oldest entry in O(1).
        """
        if len(registry) > limit:
            oldest = next(iter(registry))
            del registry[oldest]

    def _refresh_profile(self, profile: CoherenceProfile, agent_id: str) -> None:
        """Recompute the aggregate fields of ``profile`` from engine state.

        Recomputes ``avg_coherence``, ``dominant_facet``, ``regime``,
        ``total_nodes``, ``total_relations``, and ``total_repairs`` from
        the currently held snapshots, nodes, relations, and repairs for
        ``agent_id``. Caller holds the lock.
        """
        snapshots = [s for s in self._snapshots.values() if s.agent_id == agent_id]
        nodes = [n for n in self._nodes.values() if n.agent_id == agent_id]
        relations = [r for r in self._relations.values() if r.agent_id == agent_id]
        repairs = [r for r in self._repairs.values() if r.agent_id == agent_id]

        if snapshots:
            avg = sum(s.total_coherence for s in snapshots) / len(snapshots)
        else:
            avg = 0.0
        profile.avg_coherence = avg
        profile.regime = _determine_regime(avg)

        # Dominant facet is the one that appeared most often as a snapshot's
        # dominant facet. Ties are broken toward the facet whose enum value
        # sorts first so the choice is deterministic.
        facet_counts: Dict[CoherenceFacet, int] = {}
        for snap in snapshots:
            if snap.dominant_facet is not None:
                facet_counts[snap.dominant_facet] = (
                    facet_counts.get(snap.dominant_facet, 0) + 1
                )
        if facet_counts:
            profile.dominant_facet = min(
                facet_counts.items(),
                key=lambda kv: (-kv[1], kv[0].value),
            )[0]
        else:
            profile.dominant_facet = None

        profile.total_nodes = len(nodes)
        profile.total_relations = len(relations)
        profile.total_repairs = len(repairs)
        profile.last_updated = _now()

    # ── Coherence Node ─────────────────────────────────────────────

    def register_node(
        self,
        agent_id: str,
        label: str,
        node_type: str,
        content: str,
        weight: float = 0.5,
    ) -> CoherenceNode:
        """Register a single coherence node and return it.

        ``weight`` is clamped to [0, 1] and records the node's salience.
        The node is stored in the engine's node registry, which trims
        itself to ``MAX_NODES`` entries by dropping the oldest when full.
        """
        node = CoherenceNode(
            agent_id=agent_id,
            label=str(label),
            node_type=str(node_type),
            content=str(content),
            weight=_clamp(weight),
        )
        with self._lock:
            self._nodes[node.node_id] = node
            self._trim(self._nodes, self.MAX_NODES)
            self._bump("total_nodes")
            return node

    def list_nodes(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CoherenceNode]:
        """Return nodes, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all nodes are considered; otherwise
        only nodes for that agent are returned. The most recently
        registered ``limit`` nodes are returned (insertion order is
        chronological, so the tail is the most recent). The returned list
        is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            nodes = list(self._nodes.values())
        if agent_id is not None:
            nodes = [n for n in nodes if n.agent_id == agent_id]
        try:
            n_limit = int(limit)
        except (TypeError, ValueError):
            n_limit = 50
        if n_limit < 0:
            n_limit = 0
        return nodes[-n_limit:] if n_limit else []

    def get_node(self, node_id: str) -> Optional[CoherenceNode]:
        """Retrieve a node by id, or ``None`` if absent."""
        with self._lock:
            return self._nodes.get(node_id)

    # ── Coherence Relation ─────────────────────────────────────────

    def link_relation(
        self,
        agent_id: str,
        source_id: str,
        target_id: str,
        relation: RelationType,
        strength: float = 0.5,
    ) -> CoherenceRelation:
        """Create a coherence relation between two nodes and return it.

        ``relation`` may be passed as a ``RelationType`` member or as its
        string value/name. ``strength`` is clamped to [0, 1]. The relation
        is stored in the engine's relation registry, which trims itself to
        ``MAX_RELATIONS`` entries by dropping the oldest when full. The
        source and target nodes need not be registered for the relation to
        be recorded — callers may link nodes that live outside this engine.
        """
        resolved = _resolve_enum(RelationType, relation)
        rel = CoherenceRelation(
            agent_id=agent_id,
            source_id=str(source_id),
            target_id=str(target_id),
            relation=resolved,
            strength=_clamp(strength),
        )
        with self._lock:
            self._relations[rel.relation_id] = rel
            self._trim(self._relations, self.MAX_RELATIONS)
            self._bump("total_relations")
            return rel

    def list_relations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CoherenceRelation]:
        """Return relations, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all relations are considered;
        otherwise only relations for that agent are returned. The most
        recently linked ``limit`` relations are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            relations = list(self._relations.values())
        if agent_id is not None:
            relations = [r for r in relations if r.agent_id == agent_id]
        try:
            n_limit = int(limit)
        except (TypeError, ValueError):
            n_limit = 50
        if n_limit < 0:
            n_limit = 0
        return relations[-n_limit:] if n_limit else []

    def get_relation(self, relation_id: str) -> Optional[CoherenceRelation]:
        """Retrieve a relation by id, or ``None`` if absent."""
        with self._lock:
            return self._relations.get(relation_id)

    # ── Coherence Snapshot ─────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CoherenceSnapshot:
        """Aggregate an agent's nodes and relations into a coherence snapshot.

        Collects every node and relation currently registered for the
        agent. ``total_coherence`` is computed as the support-weighted
        balance of cohering versus inhibiting relations: let ``positive``
        be the sum of strengths of SUPPORTS, EXPLAINS, ENABLES, and
        COHERES_WITH relations, and ``negative`` be the sum of strengths
        of CONTRADICTS and CONFLICTS relations. When ``positive + negative
        > 0`` the coherence score is ``positive / (positive + negative)``
        (the fraction of total relation weight that is supportive); when
        the agent has no relations at all the score is ``0.0`` (a
        fragmented network where nothing connects). The score is clamped
        to [0, 1] and mapped onto a ``CoherenceRegime``.

        ``dominant_facet`` is the coherence facet with the most supporting
        relations, using the heuristic ``_RELATION_FACET`` mapping from
        relation type to facet. When there are no supporting relations
        the dominant facet is ``None``. ``contradiction_count`` is the
        number of CONTRADICTS or CONFLICTS relations. The agent's profile
        is refreshed after the snapshot is recorded.
        """
        with self._lock:
            agent_nodes = [n for n in self._nodes.values() if n.agent_id == agent_id]
            agent_relations = [
                r for r in self._relations.values() if r.agent_id == agent_id
            ]

            positive_sum = 0.0
            negative_sum = 0.0
            facet_counts: Dict[CoherenceFacet, int] = {}
            for rel in agent_relations:
                if rel.relation in _POSITIVE_RELATIONS:
                    positive_sum += rel.strength
                    facet = _RELATION_FACET.get(rel.relation)
                    if facet is not None:
                        facet_counts[facet] = facet_counts.get(facet, 0) + 1
                elif rel.relation in _NEGATIVE_RELATIONS:
                    negative_sum += rel.strength

            denom = positive_sum + negative_sum
            if denom > 0.0:
                total_coherence = _clamp(positive_sum / denom)
            else:
                total_coherence = 0.0

            regime = _determine_regime(total_coherence)
            if facet_counts:
                # Pick the facet with the highest supporting-relation count;
                # ties break toward the facet whose enum value sorts first so
                # the choice is deterministic.
                dominant_facet = min(
                    facet_counts.items(),
                    key=lambda kv: (-kv[1], kv[0].value),
                )[0]
            else:
                dominant_facet = None

            contradiction_count = _compute_contradiction_count(agent_relations)

            snapshot = CoherenceSnapshot(
                agent_id=agent_id,
                total_coherence=total_coherence,
                dominant_facet=dominant_facet,
                regime=regime,
                node_count=len(agent_nodes),
                relation_count=len(agent_relations),
                contradiction_count=contradiction_count,
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._trim(self._snapshots, self.MAX_SNAPSHOTS)
            self._bump("total_snapshots")
            # Refresh the profile so its aggregates reflect this snapshot.
            profile = self.get_profile(agent_id)
            self._refresh_profile(profile, agent_id)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CoherenceSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The most
        recently taken ``limit`` snapshots are returned. The returned list
        is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            snapshots = list(self._snapshots.values())
        if agent_id is not None:
            snapshots = [s for s in snapshots if s.agent_id == agent_id]
        try:
            n_limit = int(limit)
        except (TypeError, ValueError):
            n_limit = 50
        if n_limit < 0:
            n_limit = 0
        return snapshots[-n_limit:] if n_limit else []

    def get_snapshot(self, snapshot_id: str) -> Optional[CoherenceSnapshot]:
        """Retrieve a snapshot by id, or ``None`` if absent."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    # ── Repair Attempt ─────────────────────────────────────────────

    def attempt_repair(
        self,
        agent_id: str,
        strategy: RepairStrategy,
        target_relation_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        rationale: str = "",
        success: bool = True,
    ) -> RepairAttempt:
        """Record a single repair attempt and return it.

        ``strategy`` may be passed as a ``RepairStrategy`` member or as
        its string value/name. ``target_relation_id`` is the relation the
        repair targets, when applicable; ``snapshot_id`` is the snapshot
        that motivated the repair, when known. ``rationale`` is a
        free-form explanation of why the strategy was chosen.
        ``success`` records whether the repair is considered to have
        succeeded. The attempt is stored in the engine's repair registry,
        which trims itself to ``MAX_REPAIRS`` entries by dropping the
        oldest when full.
        """
        resolved_strategy = _resolve_enum(RepairStrategy, strategy)
        attempt = RepairAttempt(
            agent_id=agent_id,
            snapshot_id=snapshot_id,
            strategy=resolved_strategy,
            target_relation_id=target_relation_id,
            rationale=str(rationale),
            success=bool(success),
        )
        with self._lock:
            self._repairs[attempt.attempt_id] = attempt
            self._trim(self._repairs, self.MAX_REPAIRS)
            self._bump("total_repairs")
            return attempt

    def list_repairs(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RepairAttempt]:
        """Return repair attempts, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all repair attempts are considered;
        otherwise only attempts for that agent are returned. The most
        recently recorded ``limit`` attempts are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            repairs = list(self._repairs.values())
        if agent_id is not None:
            repairs = [r for r in repairs if r.agent_id == agent_id]
        try:
            n_limit = int(limit)
        except (TypeError, ValueError):
            n_limit = 50
        if n_limit < 0:
            n_limit = 0
        return repairs[-n_limit:] if n_limit else []

    def get_repair(self, attempt_id: str) -> Optional[RepairAttempt]:
        """Retrieve a repair attempt by id, or ``None`` if absent."""
        with self._lock:
            return self._repairs.get(attempt_id)

    # ── Trajectory Record ──────────────────────────────────────────

    def record_trajectory(
        self,
        agent_id: str,
        trajectory: CoherenceTrajectory,
        from_coherence: float,
        to_coherence: float,
    ) -> TrajectoryRecord:
        """Record a single coherence trajectory step and return it.

        ``trajectory`` may be passed as a ``CoherenceTrajectory`` member
        or as its string value/name. ``from_coherence`` and
        ``to_coherence`` are the total coherence scores at the start and
        end of the step; both are clamped to [0, 1]. ``delta`` is computed
        as ``to_coherence - from_coherence`` after clamping. The record is
        stored in the engine's trajectory registry, which trims itself to
        ``MAX_TRAJECTORIES`` entries by dropping the oldest when full.
        """
        resolved = _resolve_enum(CoherenceTrajectory, trajectory)
        from_c = _clamp(from_coherence)
        to_c = _clamp(to_coherence)
        record = TrajectoryRecord(
            agent_id=agent_id,
            trajectory=resolved,
            from_coherence=from_c,
            to_coherence=to_c,
            delta=to_c - from_c,
        )
        with self._lock:
            self._trajectories[record.record_id] = record
            self._trim(self._trajectories, self.MAX_TRAJECTORIES)
            self._bump("total_trajectories")
            return record

    def list_trajectories(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TrajectoryRecord]:
        """Return trajectory records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all trajectory records are
        considered; otherwise only records for that agent are returned.
        The most recently recorded ``limit`` records are returned. The
        returned list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            trajectories = list(self._trajectories.values())
        if agent_id is not None:
            trajectories = [t for t in trajectories if t.agent_id == agent_id]
        try:
            n_limit = int(limit)
        except (TypeError, ValueError):
            n_limit = 50
        if n_limit < 0:
            n_limit = 0
        return trajectories[-n_limit:] if n_limit else []

    def get_trajectory(self, record_id: str) -> Optional[TrajectoryRecord]:
        """Retrieve a trajectory record by id, or ``None`` if absent."""
        with self._lock:
            return self._trajectories.get(record_id)

    # ── Coherence Profile ──────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CoherenceProfile:
        """Get the coherence profile for ``agent_id``, creating it if needed.

        A new profile starts with zero averages, a FRAGMENTED regime, no
        dominant facet, and zero counts. Its aggregate fields are then
        refreshed from the engine's current snapshots, nodes, relations,
        and repairs for the agent, so callers always see up-to-date
        aggregates. If the profile registry is full the oldest profile is
        dropped to make room.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                if len(self._profiles) >= self.MAX_PROFILES:
                    # Drop the oldest profile to make room for a new agent.
                    oldest = next(iter(self._profiles))
                    del self._profiles[oldest]
                profile = CoherenceProfile(agent_id=agent_id)
                self._profiles[agent_id] = profile
            self._refresh_profile(profile, agent_id)
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> CoherenceProfile:
        """Update fields on an agent's coherence profile.

        Accepted keyword arguments are ``avg_coherence`` (coerced to
        float), ``dominant_facet`` (a ``CoherenceFacet`` or its string
        name/value, or ``None`` to clear), ``regime`` (a
        ``CoherenceRegime`` or its string name/value), ``total_nodes``,
        ``total_relations``, and ``total_repairs`` (coerced to int).
        Unknown keys are ignored. The profile's ``last_updated`` timestamp
        is refreshed. The profile is created on the fly if it does not yet
        exist.
        """
        with self._lock:
            profile = self.get_profile(agent_id)
            if "avg_coherence" in kwargs:
                try:
                    profile.avg_coherence = _clamp(float(kwargs["avg_coherence"]))
                except (TypeError, ValueError):
                    pass
            if "dominant_facet" in kwargs:
                value = kwargs["dominant_facet"]
                if value is None:
                    profile.dominant_facet = None
                else:
                    try:
                        profile.dominant_facet = _resolve_enum(CoherenceFacet, value)
                    except ValueError:
                        pass
            if "regime" in kwargs:
                try:
                    profile.regime = _resolve_enum(CoherenceRegime, kwargs["regime"])
                except ValueError:
                    pass
            for key in ("total_nodes", "total_relations", "total_repairs"):
                if key in kwargs:
                    try:
                        setattr(profile, key, int(kwargs[key]))
                    except (TypeError, ValueError):
                        continue
            profile.last_updated = _now()
            return profile

    def list_profiles(self) -> List[CoherenceProfile]:
        """Return all coherence profiles currently registered.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics & Maintenance ────────────────────────────────────

    def get_stats(self) -> CoherenceStats:
        """Compute aggregate statistics over the current engine state.

        Counts of nodes, relations, snapshots, repairs, and trajectories
        are taken from the cumulative telemetry counters (which survive
        registry trimming). ``regime_distribution`` tallies the currently
        held snapshots by regime (using the regime's ``.value`` string as
        key); ``facet_distribution`` tallies them by dominant facet (or
        ``"none"`` when a snapshot has no dominant facet).
        ``avg_coherence`` is the mean ``total_coherence`` over the
        currently held snapshots (0.0 when none exist).
        """
        with self._lock:
            regime_dist: Dict[str, int] = {}
            facet_dist: Dict[str, int] = {}
            coherence_sum = 0.0
            snapshot_count = len(self._snapshots)
            for snap in self._snapshots.values():
                regime_key = _enum_value(CoherenceRegime, snap.regime)
                regime_dist[regime_key] = regime_dist.get(regime_key, 0) + 1
                if snap.dominant_facet is None:
                    facet_key = "none"
                else:
                    facet_key = _enum_value(CoherenceFacet, snap.dominant_facet)
                facet_dist[facet_key] = facet_dist.get(facet_key, 0) + 1
                coherence_sum += snap.total_coherence
            avg_coherence = (
                coherence_sum / snapshot_count if snapshot_count else 0.0
            )
            return CoherenceStats(
                total_nodes=self._stats.get("total_nodes", 0),
                total_relations=self._stats.get("total_relations", 0),
                total_snapshots=self._stats.get("total_snapshots", 0),
                total_repairs=self._stats.get("total_repairs", 0),
                total_trajectories=self._stats.get("total_trajectories", 0),
                regime_distribution=regime_dist,
                facet_distribution=facet_dist,
                avg_coherence=avg_coherence,
            )

    # ── Maintenance ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Empties every registry, resets the cumulative telemetry counters,
        and drops all per-agent profiles. After reset the engine behaves
        as if freshly constructed.
        """
        with self._lock:
            self._nodes.clear()
            self._relations.clear()
            self._snapshots.clear()
            self._repairs.clear()
            self._trajectories.clear()
            self._profiles.clear()
            self._stats.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_coherence_engine() -> AgentCognitiveCoherence:
    """Get or create the singleton ``AgentCognitiveCoherence`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveCoherence()
        return _engine


def reset_coherence_engine() -> None:
    """Reset the singleton ``AgentCognitiveCoherence`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_coherence_engine`` call creates a
    fresh instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
