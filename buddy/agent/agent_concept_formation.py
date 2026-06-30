from __future__ import annotations

"""Agent Concept Formation Engine.

Forms new concepts from experience by clustering similar instances,
naming them, and building a concept hierarchy with abstraction levels.
This lets the agent abstract from concrete experiences to general
patterns. The engine is thread-safe and depends only on the Python
standard library.
"""

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ConceptType(str, Enum):
    """Kind of concept being represented.

    Members are lowercase so they can be looked up by value, e.g.
    ``ConceptType('concrete')``.
    """
    concrete = "concrete"          # grounded in specific instances
    abstract = "abstract"          # general idea detached from instances
    procedural = "procedural"      # sequence of actions / steps
    relational = "relational"      # relationship between entities
    composite = "composite"        # combination of several concepts


class FormationStatus(str, Enum):
    """Lifecycle state of a concept being formed."""
    pending = "pending"            # created but not yet processed
    clustering = "clustering"      # currently being clustered
    formed = "formed"              # initial formation complete
    validated = "validated"        # checked against evidence
    refined = "refined"            # adjusted after validation
    deprecated = "deprecated"      # no longer in active use


class SimilarityMetric(str, Enum):
    """Distance / similarity function used to compare feature vectors."""
    cosine = "cosine"              # cosine of the angle between vectors
    euclidean = "euclidean"        # straight-line distance
    jaccard = "jaccard"            # set overlap of nonzero dimensions
    hamming = "hamming"            # count of differing dimensions
    custom = "custom"              # caller-provided fallback (euclidean)


class AbstractionLevel(str, Enum):
    """Position of a concept within an abstraction hierarchy."""
    instance = "instance"          # single concrete example
    prototype = "prototype"        # representative average of instances
    category = "category"          # group of prototypes
    supercategory = "supercategory"  # group of categories
    root = "root"                  # top of the hierarchy


class ClusterMethod(str, Enum):
    """Algorithm used to group instances into clusters."""
    kmeans = "kmeans"              # centroid-based partitioning
    hierarchical = "hierarchical"  # top-down divisive splitting
    dbscan = "dbscan"              # density-based spatial clustering
    agglomerative = "agglomerative"  # bottom-up merging
    manual = "manual"              # caller-supplied grouping (single batch)


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

def _new_id() -> str:
    """Generate a short unique identifier for a record."""
    return str(uuid.uuid4())[:8]


def _coerce_enum(value: Any, enum_cls: type, default: Any) -> Any:
    """Coerce a string or enum member into an enum, falling back to default."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            pass
    return default


def _numeric(value: Any) -> float:
    """Cast a feature value to a float; non-numeric values map via a stable hash."""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return 0.0
    return float(hash(str(value)) % 1000) / 1000.0


def _build_vocabulary(features_list: list[dict[str, Any]]) -> list[str]:
    """Return the sorted union of feature keys across many instances."""
    keys: set[str] = set()
    for features in features_list:
        if isinstance(features, dict):
            keys.update(features.keys())
    return sorted(keys)


def _to_vector(features: dict[str, Any], vocabulary: list[str]) -> list[float]:
    """Project a feature dict onto a numeric vector over ``vocabulary``."""
    if not vocabulary:
        return []
    return [_numeric(features.get(key, 0.0)) for key in vocabulary]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [-1, 1]; 0.0 for zero vectors."""
    if not a or not b:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _euclidean_distance(a: list[float], b: list[float]) -> float:
    """Euclidean distance between two equal-length vectors."""
    total = 0.0
    for x, y in zip(a, b):
        diff = x - y
        total += diff * diff
    return math.sqrt(total)


def _jaccard_similarity(a: list[float], b: list[float]) -> float:
    """Jaccard similarity over the sets of nonzero dimensions."""
    sa = {i for i, v in enumerate(a) if v != 0.0}
    sb = {i for i, v in enumerate(b) if v != 0.0}
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


def _hamming_distance(a: list[float], b: list[float]) -> float:
    """Number of positions at which the two vectors differ."""
    return float(sum(1 for x, y in zip(a, b) if x != y))


def _similarity(
    a: list[float], b: list[float], metric: SimilarityMetric
) -> float:
    """Return a similarity score in [0, 1] under the chosen metric.

    Distances are converted to similarities so all metrics share a common
    "higher is more similar" convention.
    """
    metric = _coerce_enum(metric, SimilarityMetric, SimilarityMetric.euclidean)
    if not a or not b:
        return 0.0
    if metric == SimilarityMetric.cosine:
        # cosine is in [-1, 1]; rescale to [0, 1].
        return (_cosine_similarity(a, b) + 1.0) / 2.0
    if metric == SimilarityMetric.jaccard:
        return _jaccard_similarity(a, b)
    if metric == SimilarityMetric.hamming:
        length = max(len(a), len(b))
        if length == 0:
            return 0.0
        return 1.0 - (_hamming_distance(a, b) / length)
    # euclidean and custom both fall through here.
    dist = _euclidean_distance(a, b)
    return 1.0 / (1.0 + dist)


def _vector_mean(vectors: list[list[float]]) -> list[float]:
    """Element-wise mean of a list of equal-length vectors."""
    if not vectors:
        return []
    length = len(vectors[0])
    total = [0.0] * length
    for vec in vectors:
        for i, val in enumerate(vec):
            total[i] += val
    n = len(vectors)
    return [t / n for t in total]


def _compute_prototype(features_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Average numeric features across instances into a prototype dict."""
    if not features_list:
        return {}
    keys = _build_vocabulary(features_list)
    prototype: dict[str, Any] = {}
    for key in keys:
        vals: list[float] = []
        for features in features_list:
            if not isinstance(features, dict):
                continue
            raw = features.get(key)
            if isinstance(raw, bool) or raw is None:
                continue
            if isinstance(raw, (int, float)):
                vals.append(float(raw))
        if vals:
            prototype[key] = sum(vals) / len(vals)
    return prototype


def _compute_feature_importance(
    features_list: list[dict[str, Any]], prototype: dict[str, Any]
) -> dict[str, float]:
    """Score each feature by consistency across instances.

    Lower variance yields higher importance, since a feature that barely
    changes is more defining of the concept.
    """
    if len(features_list) <= 1:
        return {key: 1.0 for key in prototype}
    importance: dict[str, float] = {}
    for key in prototype:
        vals: list[float] = []
        for features in features_list:
            if not isinstance(features, dict):
                continue
            raw = features.get(key)
            if isinstance(raw, bool) or raw is None:
                continue
            if isinstance(raw, (int, float)):
                vals.append(float(raw))
        if len(vals) <= 1:
            importance[key] = 1.0
            continue
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        importance[key] = 1.0 / (1.0 + variance)
    return importance


def _clamp_confidence(value: Any) -> float:
    """Clamp a confidence value into [0, 1]."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.5
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


# ═══════════════════════════════════════════════════════════════════════════
# Clustering algorithms (stdlib-only)
# ═══════════════════════════════════════════════════════════════════════════

def _kmeans_cluster(
    vectors: list[list[float]], k: int, max_iter: int = 50
) -> list[list[int]]:
    """Partition ``vectors`` into ``k`` groups using Lloyd's algorithm.

    Returns a list of clusters, each a list of original indices. Centroids
    are seeded by even sampling to stay deterministic.
    """
    n = len(vectors)
    if n == 0 or k <= 0:
        return []
    k = min(k, n)
    step = max(1, n // k)
    centroids = [list(vectors[i]) for i in range(0, n, step)][:k]
    idx = 0
    while len(centroids) < k:
        centroids.append(list(vectors[idx % n]))
        idx += 1
    assignments = [0] * n
    for _ in range(max_iter):
        changed = False
        for i, vec in enumerate(vectors):
            best = 0
            best_dist = _euclidean_distance(vec, centroids[0])
            for c in range(1, k):
                dist = _euclidean_distance(vec, centroids[c])
                if dist < best_dist:
                    best_dist = dist
                    best = c
            if assignments[i] != best:
                assignments[i] = best
                changed = True
        sums = [[0.0] * len(vectors[0]) for _ in range(k)]
        counts = [0] * k
        for i, vec in enumerate(vectors):
            c = assignments[i]
            counts[c] += 1
            for j, val in enumerate(vec):
                sums[c][j] += val
        for c in range(k):
            if counts[c] > 0:
                centroids[c] = [s / counts[c] for s in sums[c]]
        if not changed:
            break
    groups: dict[int, list[int]] = {}
    for i, c in enumerate(assignments):
        groups.setdefault(c, []).append(i)
    return list(groups.values())


def _agglomerative_cluster(
    vectors: list[list[float]], k: int
) -> list[list[int]]:
    """Bottom-up merging with average linkage until ``k`` clusters remain."""
    n = len(vectors)
    if n == 0:
        return []
    k = max(1, min(k, n))
    clusters: list[list[int]] = [[i] for i in range(n)]
    while len(clusters) > k:
        best_pair = (0, 1)
        best_dist = float("inf")
        for a in range(len(clusters)):
            for b in range(a + 1, len(clusters)):
                total = 0.0
                count = 0
                for i in clusters[a]:
                    for j in clusters[b]:
                        total += _euclidean_distance(vectors[i], vectors[j])
                        count += 1
                dist = total / count if count > 0 else 0.0
                if dist < best_dist:
                    best_dist = dist
                    best_pair = (a, b)
        a, b = best_pair
        clusters[a].extend(clusters[b])
        clusters.pop(b)
    return clusters


def _hierarchical_cluster(
    vectors: list[list[float]], k: int
) -> list[list[int]]:
    """Top-down divisive clustering via repeated bisecting k-means."""
    n = len(vectors)
    if n == 0:
        return []
    k = max(1, min(k, n))
    clusters: list[list[int]] = [list(range(n))]
    while len(clusters) < k:
        target = max(range(len(clusters)), key=lambda i: len(clusters[i]))
        if len(clusters[target]) < 2:
            break
        sub_vectors = [vectors[i] for i in clusters[target]]
        sub_groups = _kmeans_cluster(sub_vectors, 2)
        if len(sub_groups) <= 1:
            break
        new_clusters: list[list[int]] = []
        for idx, cluster in enumerate(clusters):
            if idx == target:
                for group in sub_groups:
                    new_clusters.append([clusters[target][i] for i in group])
            else:
                new_clusters.append(cluster)
        clusters = new_clusters
    return clusters


def _dbscan_cluster(
    vectors: list[list[float]], eps: float = 1.0, min_samples: int = 2
) -> list[list[int]]:
    """Density-based clustering; noise points become singleton clusters."""
    n = len(vectors)
    if n == 0:
        return []
    labels = [-1] * n  # -1 means unassigned / noise
    visited = [False] * n
    cluster_id = 0
    for i in range(n):
        if visited[i]:
            continue
        visited[i] = True
        neighbors = [
            j for j in range(n)
            if j != i and _euclidean_distance(vectors[i], vectors[j]) <= eps
        ]
        if len(neighbors) < min_samples:
            labels[i] = -1  # noise for now
        else:
            labels[i] = cluster_id
            queue = list(neighbors)
            cursor = 0
            while cursor < len(queue):
                j = queue[cursor]
                cursor += 1
                if not visited[j]:
                    visited[j] = True
                    j_neighbors = [
                        m for m in range(n)
                        if m != j and _euclidean_distance(vectors[j], vectors[m]) <= eps
                    ]
                    if len(j_neighbors) >= min_samples:
                        for m in j_neighbors:
                            if m not in queue:
                                queue.append(m)
                if labels[j] == -1:
                    labels[j] = cluster_id
            cluster_id += 1
    groups: dict[Any, list[int]] = {}
    for i, label in enumerate(labels):
        if label == -1:
            groups[("noise", i)] = [i]
        else:
            groups.setdefault(label, []).append(i)
    return list(groups.values())


def _manual_cluster(vectors: list[list[float]]) -> list[list[int]]:
    """Place all instances into a single cluster for manual refinement."""
    n = len(vectors)
    if n == 0:
        return []
    return [list(range(n))]


def _cluster_cohesion(vectors: list[list[float]]) -> float:
    """Intra-cluster similarity in [0, 1]; 1.0 for singletons."""
    if len(vectors) <= 1:
        return 1.0
    total = 0.0
    count = 0
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            total += _euclidean_distance(vectors[i], vectors[j])
            count += 1
    avg = total / count if count > 0 else 0.0
    return 1.0 / (1.0 + avg)


def _cluster_separation(
    centroid: list[float], other_centroids: list[list[float]]
) -> float:
    """Distance to the nearest other centroid, mapped to [0, 1]."""
    if not other_centroids or not centroid:
        return 1.0
    min_dist = min(
        _euclidean_distance(centroid, other) for other in other_centroids
    )
    return 1.0 / (1.0 + min_dist)


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ConceptInstance:
    """A single concrete observation, potentially belonging to a concept."""
    instance_id: str = field(default_factory=_new_id)
    concept_id: str = ""
    agent_id: str = ""
    features: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "concept_id": self.concept_id,
            "agent_id": self.agent_id,
            "features": dict(self.features),
            "timestamp": self.timestamp,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class Concept:
    """A grouping of instances with a prototype and hierarchy position."""
    concept_id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    concept_type: ConceptType = ConceptType.concrete
    abstraction_level: AbstractionLevel = AbstractionLevel.prototype
    parent_id: str = ""
    children_ids: list[str] = field(default_factory=list)
    instances: list[str] = field(default_factory=list)
    prototype_features: dict[str, Any] = field(default_factory=dict)
    formation_status: FormationStatus = FormationStatus.pending
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    confidence_score: float = 0.5
    feature_importance: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "name": self.name,
            "description": self.description,
            "concept_type": self.concept_type.value
            if isinstance(self.concept_type, ConceptType)
            else str(self.concept_type),
            "abstraction_level": self.abstraction_level.value
            if isinstance(self.abstraction_level, AbstractionLevel)
            else str(self.abstraction_level),
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "instances": list(self.instances),
            "prototype_features": dict(self.prototype_features),
            "formation_status": self.formation_status.value
            if isinstance(self.formation_status, FormationStatus)
            else str(self.formation_status),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "confidence_score": self.confidence_score,
            "feature_importance": dict(self.feature_importance),
        }


@dataclass
class ConceptCluster:
    """Output of a clustering pass: members, centroid, cohesion, separation."""
    cluster_id: str = field(default_factory=_new_id)
    concept_id: str = ""
    instance_ids: list[str] = field(default_factory=list)
    centroid: dict[str, Any] = field(default_factory=dict)
    cohesion: float = 0.0
    separation: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "concept_id": self.concept_id,
            "instance_ids": list(self.instance_ids),
            "centroid": dict(self.centroid),
            "cohesion": self.cohesion,
            "separation": self.separation,
            "created_at": self.created_at,
        }


@dataclass
class ConceptHierarchy:
    """A tree of concepts rooted at a single concept, keyed by depth."""
    hierarchy_id: str = field(default_factory=_new_id)
    root_concept_id: str = ""
    levels: dict[int, list[str]] = field(default_factory=dict)
    depth: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hierarchy_id": self.hierarchy_id,
            "root_concept_id": self.root_concept_id,
            "levels": {str(k): list(v) for k, v in self.levels.items()},
            "depth": self.depth,
            "created_at": self.created_at,
        }


@dataclass
class FormationSession:
    """A batch of concept-formation work attributed to one agent."""
    session_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    instances_processed: int = 0
    concepts_formed: int = 0
    clusters_created: int = 0
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    status: FormationStatus = FormationStatus.pending

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "instances_processed": self.instances_processed,
            "concepts_formed": self.concepts_formed,
            "clusters_created": self.clusters_created,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value
            if isinstance(self.status, FormationStatus)
            else str(self.status),
        }


@dataclass
class FormationStats:
    """Aggregate statistics describing the state of the formation engine."""
    total_instances: int = 0
    total_concepts: int = 0
    total_clusters: int = 0
    total_hierarchies: int = 0
    concepts_by_type: dict[str, int] = field(default_factory=dict)
    concepts_by_status: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_hierarchy_depth: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_instances": self.total_instances,
            "total_concepts": self.total_concepts,
            "total_clusters": self.total_clusters,
            "total_hierarchies": self.total_hierarchies,
            "concepts_by_type": dict(self.concepts_by_type),
            "concepts_by_status": dict(self.concepts_by_status),
            "avg_confidence": self.avg_confidence,
            "avg_hierarchy_depth": self.avg_hierarchy_depth,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Agent Concept Formation Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentConceptFormationEngine:
    """Forms concepts from experience via clustering and hierarchy building.

    Maintains instances, concepts, clusters, hierarchies, and sessions.
    Supports the full concept-formation lifecycle: register instances,
    form concepts with computed prototypes, cluster with five algorithms,
    build abstraction hierarchies, find similar concepts, and report
    statistics. All mutations are guarded by a single ``threading.Lock``.
    """

    # Capacity limits guarding unbounded growth.
    MAX_INSTANCES: int = 5000
    MAX_CONCEPTS: int = 2000
    MAX_CLUSTERS: int = 2000
    MAX_HIERARCHIES: int = 500
    MAX_SESSIONS: int = 500

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._instances: dict[str, ConceptInstance] = {}
        self._concepts: dict[str, Concept] = {}
        self._clusters: dict[str, ConceptCluster] = {}
        self._hierarchies: dict[str, ConceptHierarchy] = {}
        self._sessions: dict[str, FormationSession] = {}

    # ── Instance Management ──────────────────────────────────────────

    def register_instance(
        self,
        agent_id: str,
        features: dict[str, Any],
        source: str = "",
        confidence: float = 0.5,
    ) -> ConceptInstance:
        """Register a concrete observation as a concept instance.

        The oldest instance is evicted if the store is full.
        """
        with self._lock:
            if len(self._instances) >= self.MAX_INSTANCES:
                oldest_id = min(
                    self._instances.keys(),
                    key=lambda iid: self._instances[iid].timestamp,
                )
                self._instances.pop(oldest_id, None)
            if not isinstance(features, dict):
                features = {}
            confidence = _clamp_confidence(confidence)
            instance = ConceptInstance(
                agent_id=agent_id,
                features=dict(features),
                source=source,
                confidence=confidence,
            )
            self._instances[instance.instance_id] = instance
            return instance

    def get_instance(self, instance_id: str) -> ConceptInstance | None:
        """Retrieve an instance by its identifier."""
        with self._lock:
            return self._instances.get(instance_id)

    def list_instances(
        self,
        concept_id: str | None = None,
        agent_id: str | None = None,
    ) -> list[ConceptInstance]:
        """List instances, optionally filtered by concept or agent."""
        with self._lock:
            result: list[ConceptInstance] = []
            for instance in self._instances.values():
                if concept_id is not None and instance.concept_id != concept_id:
                    continue
                if agent_id is not None and instance.agent_id != agent_id:
                    continue
                result.append(instance)
            return result

    # ── Concept Management ───────────────────────────────────────────

    def form_concept(
        self,
        name: str,
        description: str,
        concept_type: Any,
        instance_ids: list[str],
        abstraction_level: Any = AbstractionLevel.prototype,
        parent_id: str = "",
    ) -> Concept:
        """Form a new concept from a set of registered instances.

        Computes the prototype and per-feature importance from members,
        links members back to the concept, and links to a parent if given.
        """
        with self._lock:
            if len(self._concepts) >= self.MAX_CONCEPTS:
                oldest_id = min(
                    self._concepts.keys(),
                    key=lambda cid: self._concepts[cid].created_at,
                )
                self._evict_concept(oldest_id)

            ctype = _coerce_enum(concept_type, ConceptType, ConceptType.concrete)
            level = _coerce_enum(abstraction_level, AbstractionLevel, AbstractionLevel.prototype)
            valid_ids = [iid for iid in instance_ids if iid in self._instances]
            features_list = [
                self._instances[iid].features for iid in valid_ids
                if isinstance(self._instances[iid].features, dict)
            ]
            prototype = _compute_prototype(features_list)
            importance = _compute_feature_importance(features_list, prototype)
            if valid_ids:
                avg_conf = sum(
                    self._instances[iid].confidence for iid in valid_ids
                ) / len(valid_ids)
            else:
                avg_conf = 0.0

            concept = Concept(
                name=name,
                description=description,
                concept_type=ctype,
                abstraction_level=level,
                parent_id=parent_id,
                instances=list(valid_ids),
                prototype_features=prototype,
                formation_status=FormationStatus.formed,
                confidence_score=avg_conf,
                feature_importance=importance,
            )
            for iid in valid_ids:
                self._instances[iid].concept_id = concept.concept_id
            if parent_id and parent_id in self._concepts:
                parent = self._concepts[parent_id]
                if concept.concept_id not in parent.children_ids:
                    parent.children_ids.append(concept.concept_id)
                parent.updated_at = time.time()
            self._concepts[concept.concept_id] = concept
            return concept

    def get_concept(self, concept_id: str) -> Concept | None:
        """Retrieve a concept by its identifier."""
        with self._lock:
            return self._concepts.get(concept_id)

    def list_concepts(
        self,
        concept_type: Any | None = None,
        abstraction_level: Any | None = None,
        status: Any | None = None,
    ) -> list[Concept]:
        """List concepts, optionally filtered by type, level, or status."""
        ctype = _coerce_enum(concept_type, ConceptType, ConceptType.concrete) if concept_type is not None else None
        level = _coerce_enum(abstraction_level, AbstractionLevel, AbstractionLevel.prototype) if abstraction_level is not None else None
        fstatus = _coerce_enum(status, FormationStatus, FormationStatus.pending) if status is not None else None
        with self._lock:
            result: list[Concept] = []
            for concept in self._concepts.values():
                if ctype is not None and concept.concept_type != ctype:
                    continue
                if level is not None and concept.abstraction_level != level:
                    continue
                if fstatus is not None and concept.formation_status != fstatus:
                    continue
                result.append(concept)
            return result

    def update_concept(
        self,
        concept_id: str,
        name: str | None = None,
        description: str | None = None,
        status: Any | None = None,
    ) -> Concept | None:
        """Update mutable fields of a concept. Returns None if missing."""
        with self._lock:
            concept = self._concepts.get(concept_id)
            if concept is None:
                return None
            if name is not None:
                concept.name = name
            if description is not None:
                concept.description = description
            if status is not None:
                concept.formation_status = _coerce_enum(status, FormationStatus, FormationStatus.pending)
            concept.updated_at = time.time()
            return concept

    def delete_concept(self, concept_id: str) -> bool:
        """Delete a concept, detaching its instances and children."""
        with self._lock:
            concept = self._concepts.get(concept_id)
            if concept is None:
                return False
            for iid in concept.instances:
                instance = self._instances.get(iid)
                if instance is not None and instance.concept_id == concept_id:
                    instance.concept_id = ""
            for child_id in concept.children_ids:
                child = self._concepts.get(child_id)
                if child is not None and child.parent_id == concept_id:
                    child.parent_id = ""
            if concept.parent_id:
                parent = self._concepts.get(concept.parent_id)
                if parent is not None and concept_id in parent.children_ids:
                    parent.children_ids.remove(concept_id)
            self._concepts.pop(concept_id, None)
            return True

    def _evict_concept(self, concept_id: str) -> None:
        """Remove a concept and detach its instances. Caller holds the lock."""
        concept = self._concepts.get(concept_id)
        if concept is None:
            return
        for iid in concept.instances:
            instance = self._instances.get(iid)
            if instance is not None and instance.concept_id == concept_id:
                instance.concept_id = ""
        self._concepts.pop(concept_id, None)

    # ── Clustering ───────────────────────────────────────────────────

    def cluster_instances(
        self,
        instance_ids: list[str],
        method: Any = ClusterMethod.kmeans,
        num_clusters: int = 2,
    ) -> list[ConceptCluster]:
        """Cluster instances into ``ConceptCluster`` records.

        Builds a shared feature vocabulary, projects each instance onto a
        numeric vector, runs the chosen algorithm, and packages each group
        with computed cohesion and separation. Unknown ids are skipped.
        """
        with self._lock:
            valid_ids = [iid for iid in instance_ids if iid in self._instances]
            if not valid_ids:
                return []
            if len(self._clusters) >= self.MAX_CLUSTERS:
                oldest_id = min(
                    self._clusters.keys(),
                    key=lambda cid: self._clusters[cid].created_at,
                )
                self._clusters.pop(oldest_id, None)

            features_list = [
                self._instances[iid].features for iid in valid_ids
                if isinstance(self._instances[iid].features, dict)
            ]
            vocabulary = _build_vocabulary(features_list)
            vectors = [_to_vector(self._instances[iid].features, vocabulary) for iid in valid_ids]
            algo = _coerce_enum(method, ClusterMethod, ClusterMethod.kmeans)

            if algo == ClusterMethod.kmeans:
                groups = _kmeans_cluster(vectors, max(1, num_clusters))
            elif algo == ClusterMethod.hierarchical:
                groups = _hierarchical_cluster(vectors, max(1, num_clusters))
            elif algo == ClusterMethod.agglomerative:
                groups = _agglomerative_cluster(vectors, max(1, num_clusters))
            elif algo == ClusterMethod.dbscan:
                groups = _dbscan_cluster(vectors)
            else:
                groups = _manual_cluster(vectors)

            centroids = [_vector_mean([vectors[i] for i in group]) for group in groups]
            clusters: list[ConceptCluster] = []
            for index, group in enumerate(groups):
                member_vectors = [vectors[i] for i in group]
                centroid = centroids[index]
                other_centroids = [centroids[j] for j in range(len(centroids)) if j != index]
                centroid_dict = {
                    vocabulary[k]: centroid[k]
                    for k in range(len(vocabulary))
                } if vocabulary else {}
                cohesion = _cluster_cohesion(member_vectors)
                separation = _cluster_separation(centroid, other_centroids)
                cluster = ConceptCluster(
                    instance_ids=[valid_ids[i] for i in group],
                    centroid=centroid_dict,
                    cohesion=cohesion,
                    separation=separation,
                )
                self._clusters[cluster.cluster_id] = cluster
                clusters.append(cluster)
            return clusters

    def get_cluster(self, cluster_id: str) -> ConceptCluster | None:
        """Retrieve a cluster by its identifier."""
        with self._lock:
            return self._clusters.get(cluster_id)

    # ── Hierarchy Management ─────────────────────────────────────────

    def build_hierarchy(self, root_concept_id: str) -> ConceptHierarchy | None:
        """Build an abstraction hierarchy rooted at the given concept.

        Assembled by BFS over ``children_ids`` links; levels are keyed by
        depth (0 at the root). Returns None if the root concept is missing.
        """
        with self._lock:
            if root_concept_id not in self._concepts:
                return None
            if len(self._hierarchies) >= self.MAX_HIERARCHIES:
                oldest_id = min(
                    self._hierarchies.keys(),
                    key=lambda hid: self._hierarchies[hid].created_at,
                )
                self._hierarchies.pop(oldest_id, None)

            levels: dict[int, list[str]] = {0: [root_concept_id]}
            visited: set[str] = {root_concept_id}
            frontier: list[str] = [root_concept_id]
            depth = 0
            while frontier:
                depth += 1
                next_frontier: list[str] = []
                for concept_id in frontier:
                    concept = self._concepts.get(concept_id)
                    if concept is None:
                        continue
                    for child_id in concept.children_ids:
                        if child_id in visited:
                            continue
                        visited.add(child_id)
                        next_frontier.append(child_id)
                if next_frontier:
                    levels[depth] = next_frontier
                    frontier = next_frontier
                else:
                    break
            hierarchy = ConceptHierarchy(
                root_concept_id=root_concept_id,
                levels=levels,
                depth=max(levels.keys()) if levels else 0,
            )
            self._hierarchies[hierarchy.hierarchy_id] = hierarchy
            return hierarchy

    def get_hierarchy(self, hierarchy_id: str) -> ConceptHierarchy | None:
        """Retrieve a hierarchy by its identifier."""
        with self._lock:
            return self._hierarchies.get(hierarchy_id)

    def list_hierarchies(self) -> list[ConceptHierarchy]:
        """List all stored hierarchies."""
        with self._lock:
            return list(self._hierarchies.values())

    # ── Similarity Search ────────────────────────────────────────────

    def find_similar_concepts(
        self,
        features: dict[str, Any],
        metric: Any = SimilarityMetric.cosine,
        top_k: int = 5,
    ) -> list[tuple[Concept, float]]:
        """Find the concepts most similar to a query feature vector.

        Each concept's prototype is projected onto the union vocabulary of
        the query and the prototype, then compared under the chosen metric.
        Returns ``(concept, similarity)`` pairs sorted descending.
        """
        with self._lock:
            if not isinstance(features, dict):
                features = {}
            metric_enum = _coerce_enum(metric, SimilarityMetric, SimilarityMetric.euclidean)
            top_k = max(1, top_k)
            scored: list[tuple[Concept, float]] = []
            for concept in self._concepts.values():
                if not concept.prototype_features:
                    continue
                vocabulary = _build_vocabulary([features, concept.prototype_features])
                query_vec = _to_vector(features, vocabulary)
                proto_vec = _to_vector(concept.prototype_features, vocabulary)
                score = _similarity(query_vec, proto_vec, metric_enum)
                scored.append((concept, score))
            scored.sort(key=lambda pair: pair[1], reverse=True)
            return scored[:top_k]

    # ── Sessions ─────────────────────────────────────────────────────

    def start_session(self, agent_id: str) -> FormationSession:
        """Begin a new formation session for an agent (pending status)."""
        with self._lock:
            if len(self._sessions) >= self.MAX_SESSIONS:
                oldest_id = min(
                    self._sessions.keys(),
                    key=lambda sid: self._sessions[sid].started_at,
                )
                self._sessions.pop(oldest_id, None)
            session = FormationSession(agent_id=agent_id)
            self._sessions[session.session_id] = session
            return session

    def complete_session(self, session_id: str) -> FormationSession | None:
        """Mark a session as completed and stamp its completion time."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = FormationStatus.refined
            session.completed_at = time.time()
            return session

    # ── Statistics & Maintenance ─────────────────────────────────────

    def get_stats(self) -> FormationStats:
        """Compute aggregate statistics across the entire engine."""
        with self._lock:
            by_type: dict[str, int] = {}
            by_status: dict[str, int] = {}
            confidence_sum = 0.0
            for concept in self._concepts.values():
                type_key = (
                    concept.concept_type.value
                    if isinstance(concept.concept_type, ConceptType)
                    else str(concept.concept_type)
                )
                status_key = (
                    concept.formation_status.value
                    if isinstance(concept.formation_status, FormationStatus)
                    else str(concept.formation_status)
                )
                by_type[type_key] = by_type.get(type_key, 0) + 1
                by_status[status_key] = by_status.get(status_key, 0) + 1
                confidence_sum += concept.confidence_score
            avg_confidence = (
                confidence_sum / len(self._concepts)
                if self._concepts
                else 0.0
            )
            depth_sum = 0
            for hierarchy in self._hierarchies.values():
                depth_sum += hierarchy.depth
            avg_depth = (
                depth_sum / len(self._hierarchies)
                if self._hierarchies
                else 0.0
            )
            return FormationStats(
                total_instances=len(self._instances),
                total_concepts=len(self._concepts),
                total_clusters=len(self._clusters),
                total_hierarchies=len(self._hierarchies),
                concepts_by_type=by_type,
                concepts_by_status=by_status,
                avg_confidence=avg_confidence,
                avg_hierarchy_depth=avg_depth,
            )

    def clear(self) -> int:
        """Clear all engine state and return the number of items removed."""
        with self._lock:
            removed = (
                len(self._instances)
                + len(self._concepts)
                + len(self._clusters)
                + len(self._hierarchies)
                + len(self._sessions)
            )
            self._instances.clear()
            self._concepts.clear()
            self._clusters.clear()
            self._hierarchies.clear()
            self._sessions.clear()
            return removed


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: AgentConceptFormationEngine | None = None
_engine_lock = threading.Lock()


def get_concept_formation_engine() -> AgentConceptFormationEngine:
    """Get or create the singleton AgentConceptFormationEngine instance."""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentConceptFormationEngine()
        return _engine


def reset_concept_formation_engine() -> None:
    """Reset the singleton AgentConceptFormationEngine instance."""
    global _engine
    with _engine_lock:
        _engine = None
