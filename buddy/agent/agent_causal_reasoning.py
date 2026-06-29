from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CausalRelation(str, Enum):
    """Types of relationships that can exist between two causal variables."""
    CAUSES = "causes"            # A causes B (positive generative link)
    INHIBITS = "inhibits"        # A prevents or reduces B
    CORRELATES = "correlates"    # non-causal statistical correlation
    CONFOUNDS = "confounds"      # A is a confounder of B and C
    MEDIATES = "mediates"        # A mediates the B -> C pathway
    MODERATES = "moderates"      # A moderates the effect of B on C


class VariableType(str, Enum):
    """Role a variable plays within a causal model."""
    TREATMENT = "treatment"      # actionable cause that can be intervened on
    OUTCOME = "outcome"          # effect / endpoint of interest
    CONFOUNDER = "confounder"    # common cause of treatment and outcome
    MEDIATOR = "mediator"        # intermediate variable on a causal path
    COLLIDER = "collider"        # common effect of two variables
    INSTRUMENT = "instrument"    # proxy variable used for identification
    OBSERVED = "observed"        # passive covariate with no special role


class InterventionStatus(str, Enum):
    """Lifecycle state of a do(...) intervention."""
    PROPOSED = "proposed"        # suggested but not yet applied
    ACTIVE = "active"            # currently being applied
    COMPLETED = "completed"      # finished successfully with recorded effect
    FAILED = "failed"            # could not be applied or aborted
    ROLLED_BACK = "rolled_back"  # applied then reverted to prior state


class EvidenceStrength(str, Enum):
    """Hierarchical strength of the evidence supporting a causal link."""
    HYPOTHETICAL = "hypothetical"              # speculation / prior belief
    CORRELATIONAL = "correlational"            # observed association only
    QUASI_EXPERIMENTAL = "quasi_experimental"  # observational with controls
    EXPERIMENTAL = "experimental"              # randomized manipulation
    ESTABLISHED = "established"                # replicated / canonical


class CounterfactualResult(str, Enum):
    """Outcome of evaluating a counterfactual query."""
    SUPPORTED = "supported"        # estimated outcome consistent with premise
    REFUTED = "refuted"            # estimated outcome contradicts premise
    INCONCLUSIVE = "inconclusive"  # evidence insufficient to decide
    UNTESTABLE = "untestable"      # cannot be evaluated with current model


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

def _copy_value(value: Any) -> Any:
    """Return a fresh copy of mutable containers, pass scalars through.

    Lists and dicts are shallow-copied so that callers cannot mutate the
    internal state by holding a reference to a returned value. Enum values
    are left untouched; callers convert them via ``to_dict``.
    """
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, tuple):
        return list(value)
    return value


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CausalVariable:
    """A single variable within a causal graph.

    A variable represents an attribute, action, or state that can participate
    in causal relationships. Its ``variable_type`` encodes the structural role
    it plays (treatment, outcome, confounder, etc.) and ``current_value``
    holds the most recently observed or assigned value.
    """
    variable_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    variable_type: VariableType = VariableType.OBSERVED
    domain: str = ""                     # e.g. "binary", "continuous", "categorical"
    current_value: Any = None
    observable: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "name": self.name,
            "description": self.description,
            "variable_type": self.variable_type.value
            if isinstance(self.variable_type, VariableType)
            else str(self.variable_type),
            "domain": self.domain,
            "current_value": _copy_value(self.current_value),
            "observable": self.observable,
            "created_at": self.created_at,
        }


@dataclass
class CausalEdge:
    """A directed causal relationship between two variables.

    Edges carry a ``relation`` describing the nature of the link, a
    ``strength`` in [0, 1] quantifying the magnitude of the effect, the
    ``evidence`` supporting the link, and a ``confidence`` in [0, 1]
    expressing belief that the link is genuine.
    """
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = ""
    target_id: str = ""
    relation: CausalRelation = CausalRelation.CAUSES
    strength: float = 0.5
    evidence: EvidenceStrength = EvidenceStrength.HYPOTHETICAL
    description: str = ""
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value
            if isinstance(self.relation, CausalRelation)
            else str(self.relation),
            "strength": self.strength,
            "evidence": self.evidence.value
            if isinstance(self.evidence, EvidenceStrength)
            else str(self.evidence),
            "description": self.description,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class CausalGraph:
    """A directed causal graph composed of variables and edges.

    The ``adjacency`` map stores, for each source variable id, the list of
    target variable ids it points to via any edge. It is kept in sync with
    ``edges`` and is the substrate used for path queries.
    """
    graph_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    variables: dict[str, CausalVariable] = field(default_factory=dict)
    edges: list[CausalEdge] = field(default_factory=list)
    adjacency: dict[str, list[str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "description": self.description,
            "variables": {
                vid: v.to_dict() if hasattr(v, "to_dict") else dict(v)
                for vid, v in self.variables.items()
            },
            "edges": [e.to_dict() if hasattr(e, "to_dict") else dict(e) for e in self.edges],
            "adjacency": {k: list(v) for k, v in self.adjacency.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Intervention:
    """A do(X = x) intervention applied to a variable in a causal graph.

    Interventions represent hypothetical or actual manipulations. The
    ``expected_effect`` captures the predicted change to downstream
    variables, while ``actual_effect`` records the observed change once the
    intervention has been completed.
    """
    intervention_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    graph_id: str = ""
    variable_id: str = ""
    target_value: Any = None
    rationale: str = ""
    status: InterventionStatus = InterventionStatus.PROPOSED
    expected_effect: dict[str, float] = field(default_factory=dict)
    actual_effect: dict[str, float] | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intervention_id": self.intervention_id,
            "graph_id": self.graph_id,
            "variable_id": self.variable_id,
            "target_value": _copy_value(self.target_value),
            "rationale": self.rationale,
            "status": self.status.value
            if isinstance(self.status, InterventionStatus)
            else str(self.status),
            "expected_effect": dict(self.expected_effect),
            "actual_effect": dict(self.actual_effect) if self.actual_effect is not None else None,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class Counterfactual:
    """A counterfactual query: "what if X had been x instead of x_observed?".

    The ``observed_outcome`` is the factual outcome recorded in the world,
    while ``estimated_outcome`` is the model's estimate of the outcome under
    the hypothesized value of the intervention variable.
    """
    counterfactual_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    graph_id: str = ""
    premise: str = ""
    intervention_variable_id: str = ""
    observed_value: Any = None
    hypothesized_value: Any = None
    observed_outcome: dict[str, Any] = field(default_factory=dict)
    estimated_outcome: dict[str, Any] | None = None
    result: CounterfactualResult = CounterfactualResult.INCONCLUSIVE
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "counterfactual_id": self.counterfactual_id,
            "graph_id": self.graph_id,
            "premise": self.premise,
            "intervention_variable_id": self.intervention_variable_id,
            "observed_value": _copy_value(self.observed_value),
            "hypothesized_value": _copy_value(self.hypothesized_value),
            "observed_outcome": dict(self.observed_outcome),
            "estimated_outcome": dict(self.estimated_outcome)
            if self.estimated_outcome is not None
            else None,
            "result": self.result.value
            if isinstance(self.result, CounterfactualResult)
            else str(self.result),
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class ConfounderReport:
    """Report identifying confounders within a causal graph.

    A confounder is a common cause of both a treatment and an outcome.
    Failing to control for confounders biases causal effect estimates, so
    the report also lists recommended control strategies.
    """
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    graph_id: str = ""
    confounder_ids: list[str] = field(default_factory=list)
    affected_pairs: list[tuple[str, str]] = field(default_factory=list)
    control_recommendations: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "graph_id": self.graph_id,
            "confounder_ids": list(self.confounder_ids),
            "affected_pairs": [list(pair) for pair in self.affected_pairs],
            "control_recommendations": list(self.control_recommendations),
            "created_at": self.created_at,
        }


@dataclass
class CausalEngineStats:
    """Aggregate statistics describing the state of the causal engine."""
    total_graphs: int = 0
    total_variables: int = 0
    total_edges: int = 0
    total_interventions: int = 0
    active_interventions: int = 0
    total_counterfactuals: int = 0
    avg_graph_density: float = 0.0
    total_confounder_reports: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_graphs": self.total_graphs,
            "total_variables": self.total_variables,
            "total_edges": self.total_edges,
            "total_interventions": self.total_interventions,
            "active_interventions": self.active_interventions,
            "total_counterfactuals": self.total_counterfactuals,
            "avg_graph_density": self.avg_graph_density,
            "total_confounder_reports": self.total_confounder_reports,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Agent Causal Engine
# ═══════════════════════════════════════════════════════════════════════════

# Relations considered as directly causal for traversal and effect propagation.
_CAUSAL_RELATIONS = frozenset({
    CausalRelation.CAUSES,
    CausalRelation.INHIBITS,
    CausalRelation.MEDIATES,
})


class AgentCausalEngine:
    """Causal reasoning engine with graphs, do-interventions, and counterfactuals.

    The engine maintains a collection of causal graphs, each composed of typed
    variables and directed edges. It supports Pearl-style do(X = x)
    interventions, simplified effect estimation via edge-strength
    propagation, counterfactual queries, confounder detection, and causal
    path search.

    All state mutations are guarded by a single ``threading.Lock`` so the
    engine is safe to invoke from concurrent agent threads. Reads return
    fresh copies of mutable structures to prevent external mutation of
    internal state.

    Capabilities:
      - Build and query causal graphs (variables, edges, adjacency).
      - Detect confounders (common causes of treatments and outcomes).
      - Propose and track do(X = x) interventions through their lifecycle.
      - Estimate intervention effects by propagating deltas over edges.
      - Pose counterfactual questions and record their evaluation.
      - Find causal paths between variables via BFS over adjacency.
    """

    # Capacity limits guarding unbounded growth.
    MAX_GRAPHS: int = 100
    MAX_VARIABLES_PER_GRAPH: int = 200

    def __init__(self) -> None:
        self._graphs: dict[str, CausalGraph] = {}
        self._interventions: dict[str, Intervention] = {}
        self._counterfactuals: list[Counterfactual] = []
        self._confounder_reports: dict[str, ConfounderReport] = {}
        self._lock = threading.Lock()

    # ── Graph Management ─────────────────────────────────────────────

    def create_graph(self, name: str, description: str = "") -> CausalGraph:
        """Create and register a new causal graph.

        Args:
            name: Human-readable name for the graph.
            description: Optional longer description of the graph's purpose.

        Returns:
            The newly created ``CausalGraph`` registered with the engine.
        """
        with self._lock:
            if len(self._graphs) >= self.MAX_GRAPHS:
                # Evict the oldest graph to make room for the new one.
                oldest_id = min(
                    self._graphs.keys(),
                    key=lambda gid: self._graphs[gid].created_at,
                )
                self._evict_graph(oldest_id)
            graph = CausalGraph(name=name, description=description)
            self._graphs[graph.graph_id] = graph
            return graph

    def get_graph(self, graph_id: str) -> CausalGraph | None:
        """Retrieve a causal graph by its identifier."""
        with self._lock:
            return self._graphs.get(graph_id)

    def list_graphs(self) -> list[CausalGraph]:
        """List all registered causal graphs."""
        with self._lock:
            return list(self._graphs.values())

    def _evict_graph(self, graph_id: str) -> None:
        """Remove a graph and any interventions/counterfactuals tied to it.

        Must be called while holding ``self._lock``.
        """
        self._graphs.pop(graph_id, None)
        for iid in [iid for iid, iv in self._interventions.items() if iv.graph_id == graph_id]:
            self._interventions.pop(iid, None)
        self._counterfactuals = [c for c in self._counterfactuals if c.graph_id != graph_id]
        for rid in [rid for rid, r in self._confounder_reports.items() if r.graph_id == graph_id]:
            self._confounder_reports.pop(rid, None)

    # ── Variable CRUD ────────────────────────────────────────────────

    def add_variable(
        self,
        graph_id: str,
        name: str,
        description: str = "",
        variable_type: VariableType = VariableType.OBSERVED,
        domain: str = "",
        current_value: Any = None,
        observable: bool = True,
    ) -> CausalVariable | None:
        """Add a new variable to a causal graph.

        Args:
            graph_id: The graph to add the variable to.
            name: Human-readable name of the variable.
            description: Longer description of what the variable represents.
            variable_type: Structural role of the variable.
            domain: Domain hint, e.g. "binary" or "continuous".
            current_value: The currently observed or assigned value.
            observable: Whether the variable can be directly observed.

        Returns:
            The created ``CausalVariable``, or ``None`` if the graph is
            missing or has reached its variable capacity.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            if len(graph.variables) >= self.MAX_VARIABLES_PER_GRAPH:
                return None
            variable = CausalVariable(
                name=name,
                description=description,
                variable_type=variable_type,
                domain=domain,
                current_value=current_value,
                observable=observable,
            )
            graph.variables[variable.variable_id] = variable
            graph.adjacency.setdefault(variable.variable_id, [])
            graph.updated_at = time.time()
            return variable

    def get_variable(self, graph_id: str, variable_id: str) -> CausalVariable | None:
        """Retrieve a variable from a graph by its identifier."""
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            return graph.variables.get(variable_id)

    def list_variables(
        self,
        graph_id: str,
        variable_type: VariableType | None = None,
    ) -> list[CausalVariable]:
        """List variables in a graph, optionally filtered by type.

        Args:
            graph_id: The graph to query.
            variable_type: Optional ``VariableType`` to filter by.

        Returns:
            A list of matching ``CausalVariable`` objects (empty if the
            graph does not exist).
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return []
            if variable_type is None:
                return list(graph.variables.values())
            return [
                v for v in graph.variables.values() if v.variable_type == variable_type
            ]

    # ── Edge CRUD ────────────────────────────────────────────────────

    def add_edge(
        self,
        graph_id: str,
        source_id: str,
        target_id: str,
        relation: CausalRelation,
        strength: float = 0.5,
        evidence: EvidenceStrength = EvidenceStrength.HYPOTHETICAL,
        description: str = "",
        confidence: float = 0.5,
    ) -> CausalEdge | None:
        """Add a causal edge between two variables and update adjacency.

        Args:
            graph_id: The graph to add the edge to.
            source_id: The cause / parent variable id.
            target_id: The effect / child variable id.
            relation: The nature of the causal relationship.
            strength: Effect magnitude in [0, 1].
            evidence: Strength of evidence supporting the edge.
            description: Human-readable description of the edge.
            confidence: Belief that the edge is genuine, in [0, 1].

        Returns:
            The created ``CausalEdge``, or ``None`` if the graph or either
            endpoint variable does not exist.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            if source_id not in graph.variables or target_id not in graph.variables:
                return None
            edge = CausalEdge(
                source_id=source_id,
                target_id=target_id,
                relation=relation,
                strength=max(0.0, min(1.0, float(strength))),
                evidence=evidence,
                description=description,
                confidence=max(0.0, min(1.0, float(confidence))),
            )
            graph.edges.append(edge)
            neighbors = graph.adjacency.setdefault(source_id, [])
            if target_id not in neighbors:
                neighbors.append(target_id)
            graph.updated_at = time.time()
            return edge

    def remove_edge(self, graph_id: str, edge_id: str) -> bool:
        """Remove an edge from a graph and rebuild its adjacency.

        Args:
            graph_id: The graph containing the edge.
            edge_id: The identifier of the edge to remove.

        Returns:
            ``True`` if the edge was removed, ``False`` otherwise.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False
            original_len = len(graph.edges)
            graph.edges = [e for e in graph.edges if e.edge_id != edge_id]
            if len(graph.edges) == original_len:
                return False
            self._rebuild_adjacency(graph)
            graph.updated_at = time.time()
            return True

    def _rebuild_adjacency(self, graph: CausalGraph) -> None:
        """Recompute the adjacency map from the current edge list.

        Must be called while holding ``self._lock``.
        """
        adjacency: dict[str, list[str]] = {vid: [] for vid in graph.variables}
        for edge in graph.edges:
            neighbors = adjacency.setdefault(edge.source_id, [])
            if edge.target_id not in neighbors:
                neighbors.append(edge.target_id)
            adjacency.setdefault(edge.target_id, [])
        graph.adjacency = adjacency

    def list_edges(
        self,
        graph_id: str,
        source_id: str | None = None,
        target_id: str | None = None,
        relation: CausalRelation | None = None,
    ) -> list[CausalEdge]:
        """List edges in a graph, optionally filtered by endpoint or relation.

        Args:
            graph_id: The graph to query.
            source_id: Optional filter on the cause variable.
            target_id: Optional filter on the effect variable.
            relation: Optional filter on the relationship type.

        Returns:
            A list of matching ``CausalEdge`` objects (empty if the graph
            does not exist).
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return []
            result: list[CausalEdge] = []
            for edge in graph.edges:
                if source_id is not None and edge.source_id != source_id:
                    continue
                if target_id is not None and edge.target_id != target_id:
                    continue
                if relation is not None and edge.relation != relation:
                    continue
                result.append(edge)
            return result

    # ── Graph Queries ────────────────────────────────────────────────

    def get_direct_causes(self, graph_id: str, variable_id: str) -> list[str]:
        """Return the ids of variables that directly cause the given variable.

        A direct cause is any variable that has a causal edge (CAUSES,
        INHIBITS, or MEDIATES) pointing into ``variable_id``.

        Args:
            graph_id: The graph to query.
            variable_id: The variable whose direct causes are sought.

        Returns:
            A list of source variable ids (empty if the graph or variable
            does not exist).
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None or variable_id not in graph.variables:
                return []
            causes: list[str] = []
            seen: set[str] = set()
            for edge in graph.edges:
                if edge.target_id != variable_id:
                    continue
                if edge.relation not in _CAUSAL_RELATIONS:
                    continue
                if edge.source_id in seen:
                    continue
                seen.add(edge.source_id)
                causes.append(edge.source_id)
            return causes

    def get_effects(self, graph_id: str, variable_id: str) -> list[str]:
        """Return the ids of variables directly affected by the given variable.

        An effect is any variable that ``variable_id`` has a causal edge
        (CAUSES, INHIBITS, or MEDIATES) pointing to.

        Args:
            graph_id: The graph to query.
            variable_id: The variable whose direct effects are sought.

        Returns:
            A list of target variable ids (empty if the graph or variable
            does not exist).
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None or variable_id not in graph.variables:
                return []
            effects: list[str] = []
            seen: set[str] = set()
            for edge in graph.edges:
                if edge.source_id != variable_id:
                    continue
                if edge.relation not in _CAUSAL_RELATIONS:
                    continue
                if edge.target_id in seen:
                    continue
                seen.add(edge.target_id)
                effects.append(edge.target_id)
            return effects

    def get_causal_path(self, graph_id: str, source_id: str, target_id: str) -> list[str]:
        """Find a causal path from ``source_id`` to ``target_id`` via BFS.

        Traverses the graph's adjacency map (which encodes all directed
        edges) using breadth-first search and returns the first discovered
        path as an ordered list of variable ids.

        Args:
            graph_id: The graph to search.
            source_id: The starting variable id.
            target_id: The destination variable id.

        Returns:
            The path as a list of variable ids from source to target, or an
            empty list if no path exists or the graph/variables are missing.
            A path from a variable to itself is ``[source_id]``.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return []
            if source_id not in graph.variables or target_id not in graph.variables:
                return []
            if source_id == target_id:
                return [source_id]
            adjacency = {k: list(v) for k, v in graph.adjacency.items()}
            queue: list[str] = [source_id]
            visited: set[str] = {source_id}
            parent: dict[str, str] = {}
            index = 0
            while index < len(queue):
                current = queue[index]
                index += 1
                for neighbor in adjacency.get(current, []):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    parent[neighbor] = current
                    if neighbor == target_id:
                        path = [target_id]
                        node = target_id
                        while node in parent:
                            node = parent[node]
                            path.append(node)
                        path.reverse()
                        return path
                    queue.append(neighbor)
            return []

    # ── Confounder Detection ─────────────────────────────────────────

    def find_confounders(self, graph_id: str) -> ConfounderReport | None:
        """Detect confounders: common causes of treatments and outcomes.

        A variable is flagged as a confounder when it has causal edges
        (CAUSES or CONFOUNDS) pointing to both a TREATMENT variable and an
        OUTCOME variable, or when it is explicitly typed as a CONFOUNDER
        and causally affects an outcome. The report records affected
        treatment/outcome pairs and recommended control strategies.

        Args:
            graph_id: The graph to analyze.

        Returns:
            A ``ConfounderReport``, or ``None`` if the graph does not exist.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None

            treatments = [
                v for v in graph.variables.values()
                if v.variable_type == VariableType.TREATMENT
            ]
            outcomes = [
                v for v in graph.variables.values()
                if v.variable_type == VariableType.OUTCOME
            ]
            treatment_ids = {v.variable_id for v in treatments}
            outcome_ids = {v.variable_id for v in outcomes}

            # Map each variable to the set of variables it causally affects.
            caused: dict[str, set[str]] = {}
            for edge in graph.edges:
                if edge.relation in (CausalRelation.CAUSES, CausalRelation.CONFOUNDS):
                    caused.setdefault(edge.source_id, set()).add(edge.target_id)

            confounder_ids: list[str] = []
            affected_pairs: list[tuple[str, str]] = []
            recommendations: list[str] = []
            seen_pairs: set[tuple[str, str]] = set()

            for variable in graph.variables.values():
                targets = caused.get(variable.variable_id, set())
                hits_treatment = bool(targets & treatment_ids)
                hits_outcome = bool(targets & outcome_ids)
                is_confounder_type = variable.variable_type == VariableType.CONFOUNDER
                if not ((hits_treatment and hits_outcome) or (is_confounder_type and hits_outcome)):
                    continue
                confounder_ids.append(variable.variable_id)
                for treatment in treatments:
                    if treatment.variable_id not in targets:
                        continue
                    for outcome in outcomes:
                        if outcome.variable_id not in targets:
                            continue
                        pair = (treatment.variable_id, outcome.variable_id)
                        if pair in seen_pairs:
                            continue
                        seen_pairs.add(pair)
                        affected_pairs.append(pair)
                        recommendations.append(
                            f"Control for '{variable.name}' when estimating "
                            f"the effect of '{treatment.name}' on '{outcome.name}'."
                        )
                if is_confounder_type and not hits_treatment:
                    for outcome in outcomes:
                        if outcome.variable_id not in targets:
                            continue
                        recommendations.append(
                            f"Treat '{variable.name}' as a confounder of "
                            f"outcome '{outcome.name}'."
                        )

            report = ConfounderReport(
                graph_id=graph_id,
                confounder_ids=confounder_ids,
                affected_pairs=affected_pairs,
                control_recommendations=recommendations,
            )
            self._confounder_reports[report.report_id] = report
            return report

    # ── Interventions ────────────────────────────────────────────────

    def propose_intervention(
        self,
        graph_id: str,
        variable_id: str,
        target_value: Any,
        rationale: str = "",
        expected_effect: dict[str, float] | None = None,
    ) -> Intervention | None:
        """Propose a do(X = x) intervention on a variable.

        Args:
            graph_id: The graph containing the variable.
            variable_id: The variable to intervene on.
            target_value: The value to set the variable to under intervention.
            rationale: Justification for the intervention.
            expected_effect: Optional predicted effect on downstream
                variables, mapping variable id to expected change.

        Returns:
            The created ``Intervention`` in PROPOSED status, or ``None`` if
            the graph or variable does not exist.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            if variable_id not in graph.variables:
                return None
            intervention = Intervention(
                graph_id=graph_id,
                variable_id=variable_id,
                target_value=target_value,
                rationale=rationale,
                expected_effect=dict(expected_effect) if expected_effect else {},
            )
            self._interventions[intervention.intervention_id] = intervention
            return intervention

    def update_intervention_status(
        self,
        intervention_id: str,
        status: InterventionStatus,
        actual_effect: dict[str, float] | None = None,
    ) -> Intervention | None:
        """Update the status (and optionally the actual effect) of an intervention.

        When the status transitions to a terminal state (COMPLETED, FAILED,
        or ROLLED_BACK), the ``completed_at`` timestamp is recorded.

        Args:
            intervention_id: The intervention to update.
            status: The new intervention status.
            actual_effect: Optional observed effect on downstream variables.

        Returns:
            The updated ``Intervention``, or ``None`` if not found.
        """
        with self._lock:
            intervention = self._interventions.get(intervention_id)
            if intervention is None:
                return None
            intervention.status = status
            if actual_effect is not None:
                intervention.actual_effect = dict(actual_effect)
            if status in (
                InterventionStatus.COMPLETED,
                InterventionStatus.FAILED,
                InterventionStatus.ROLLED_BACK,
            ):
                intervention.completed_at = time.time()
            return intervention

    def list_interventions(
        self,
        graph_id: str | None = None,
        status: InterventionStatus | None = None,
    ) -> list[Intervention]:
        """List interventions, optionally filtered by graph or status.

        Args:
            graph_id: Optional filter on the owning graph.
            status: Optional filter on the intervention status.

        Returns:
            A list of matching ``Intervention`` objects.
        """
        with self._lock:
            result: list[Intervention] = []
            for intervention in self._interventions.values():
                if graph_id is not None and intervention.graph_id != graph_id:
                    continue
                if status is not None and intervention.status != status:
                    continue
                result.append(intervention)
            return result

    def estimate_effect(self, graph_id: str, intervention_id: str) -> dict[str, float]:
        """Estimate the effect of an intervention by propagating over edges.

        Implements a simplified linear propagation: the intervention delta
        (target_value - current_value for numeric variables, or 1.0 for a
        categorical activation) is multiplied by each outgoing causal edge's
        strength and sign (negative for INHIBITS) and accumulated per
        downstream variable.

        Args:
            graph_id: The graph containing the intervention.
            intervention_id: The intervention to evaluate.

        Returns:
            A mapping from downstream variable id to estimated change. The
            dict is empty if the graph or intervention is missing, or if the
            intervened variable has no outgoing causal edges.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return {}
            intervention = self._interventions.get(intervention_id)
            if intervention is None or intervention.graph_id != graph_id:
                return {}
            variable = graph.variables.get(intervention.variable_id)
            if variable is None:
                return {}

            current = variable.current_value
            target = intervention.target_value
            if isinstance(current, (int, float)) and isinstance(target, (int, float)):
                delta = float(target) - float(current)
            elif target != current:
                delta = 1.0
            else:
                delta = 0.0

            if delta == 0.0:
                return {}

            effects: dict[str, float] = {}
            for edge in graph.edges:
                if edge.source_id != intervention.variable_id:
                    continue
                if edge.relation not in _CAUSAL_RELATIONS:
                    continue
                if edge.target_id == intervention.variable_id:
                    continue
                sign = -1.0 if edge.relation == CausalRelation.INHIBITS else 1.0
                contribution = sign * edge.strength * delta
                effects[edge.target_id] = effects.get(edge.target_id, 0.0) + contribution
            return effects

    # ── Counterfactuals ──────────────────────────────────────────────

    def create_counterfactual(
        self,
        graph_id: str,
        premise: str,
        intervention_variable_id: str,
        observed_value: Any,
        hypothesized_value: Any,
        observed_outcome: dict[str, Any],
        estimated_outcome: dict[str, Any] | None = None,
    ) -> Counterfactual | None:
        """Create a counterfactual query against a causal graph.

        Args:
            graph_id: The graph the counterfactual refers to.
            premise: Natural-language statement of the counterfactual.
            intervention_variable_id: The variable whose value is changed.
            observed_value: The factual value that was observed.
            hypothesized_value: The value posited by the counterfactual.
            observed_outcome: The factual outcome recorded in the world.
            estimated_outcome: Optional model-estimated outcome under the
                hypothesized value. When provided it is used to derive an
                initial ``result``.

        Returns:
            The created ``Counterfactual``, or ``None`` if the graph does
            not exist.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            counterfactual = Counterfactual(
                graph_id=graph_id,
                premise=premise,
                intervention_variable_id=intervention_variable_id,
                observed_value=observed_value,
                hypothesized_value=hypothesized_value,
                observed_outcome=dict(observed_outcome),
                estimated_outcome=dict(estimated_outcome) if estimated_outcome else None,
                result=CounterfactualResult.INCONCLUSIVE,
                confidence=0.5,
            )
            if estimated_outcome is not None:
                counterfactual.result = self._evaluate_counterfactual(
                    observed_outcome, estimated_outcome
                )
            self._counterfactuals.append(counterfactual)
            return counterfactual

    def _evaluate_counterfactual(
        self,
        observed_outcome: dict[str, Any],
        estimated_outcome: dict[str, Any],
    ) -> CounterfactualResult:
        """Classify a counterfactual as SUPPORTED, REFUTED, or INCONCLUSIVE.

        Compares the estimated outcome to the observed outcome for every key
        present in the observed outcome. If all comparable numeric entries
        move in a consistent direction (away from the observed value), the
        counterfactual is SUPPORTED; if any entry contradicts the premise,
        it is REFUTED; otherwise INCONCLUSIVE.

        Must be called while holding ``self._lock``.
        """
        consistent = 0
        contradictory = 0
        for key, observed_val in observed_outcome.items():
            if key not in estimated_outcome:
                continue
            estimated_val = estimated_outcome[key]
            if isinstance(observed_val, (int, float)) and isinstance(estimated_val, (int, float)):
                if abs(float(estimated_val) - float(observed_val)) > 1e-9:
                    consistent += 1
                else:
                    contradictory += 1
            elif estimated_val != observed_val:
                consistent += 1
            else:
                contradictory += 1
        if consistent > 0 and contradictory == 0:
            return CounterfactualResult.SUPPORTED
        if contradictory > 0 and consistent == 0:
            return CounterfactualResult.REFUTED
        return CounterfactualResult.INCONCLUSIVE

    def list_counterfactuals(self, graph_id: str | None = None) -> list[Counterfactual]:
        """List counterfactuals, optionally filtered by graph.

        Args:
            graph_id: Optional filter on the owning graph.

        Returns:
            A list of matching ``Counterfactual`` objects.
        """
        with self._lock:
            if graph_id is None:
                return list(self._counterfactuals)
            return [c for c in self._counterfactuals if c.graph_id == graph_id]

    # ── Statistics & Maintenance ─────────────────────────────────────

    def get_stats(self) -> CausalEngineStats:
        """Compute aggregate statistics across the entire causal engine."""
        with self._lock:
            total_variables = sum(len(g.variables) for g in self._graphs.values())
            total_edges = sum(len(g.edges) for g in self._graphs.values())
            active_interventions = sum(
                1
                for iv in self._interventions.values()
                if iv.status == InterventionStatus.ACTIVE
            )
            densities: list[float] = []
            for graph in self._graphs.values():
                n = len(graph.variables)
                if n >= 2:
                    max_edges = n * (n - 1)
                    densities.append(len(graph.edges) / max_edges if max_edges > 0 else 0.0)
            avg_density = sum(densities) / len(densities) if densities else 0.0
            return CausalEngineStats(
                total_graphs=len(self._graphs),
                total_variables=total_variables,
                total_edges=total_edges,
                total_interventions=len(self._interventions),
                active_interventions=active_interventions,
                total_counterfactuals=len(self._counterfactuals),
                avg_graph_density=avg_density,
                total_confounder_reports=len(self._confounder_reports),
            )

    def clear(self) -> int:
        """Clear all engine state and return the number of items removed.

        The count is the sum of removed graphs, interventions,
        counterfactuals, and confounder reports.
        """
        with self._lock:
            removed = (
                len(self._graphs)
                + len(self._interventions)
                + len(self._counterfactuals)
                + len(self._confounder_reports)
            )
            self._graphs.clear()
            self._interventions.clear()
            self._counterfactuals.clear()
            self._confounder_reports.clear()
            return removed


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_global_causal_engine: AgentCausalEngine | None = None


def get_causal_engine() -> AgentCausalEngine:
    """Get or create the singleton AgentCausalEngine instance."""
    global _global_causal_engine
    if _global_causal_engine is None:
        _global_causal_engine = AgentCausalEngine()
    return _global_causal_engine


def reset_causal_engine() -> None:
    """Reset the singleton AgentCausalEngine instance."""
    global _global_causal_engine
    _global_causal_engine = None
