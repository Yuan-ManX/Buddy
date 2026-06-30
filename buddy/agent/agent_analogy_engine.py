from __future__ import annotations

"""Agent Analogy Engine — cross-domain analogy construction and transfer.

The engine builds analogies between different domains by mapping structures,
relationships, and attributes from a source domain to a target domain. Each
analogy is a collection of entity-to-entity mappings that carry a mapping
type, a confidence score, and a justification. Analogies move through a
lifecycle (draft -> proposed -> validated -> refined -> archived) and can be
used to transfer knowledge items from the source domain into the target
domain along the discovered mapping.

Core capabilities:
  - Domain Registry: register and query domains, their entities, and the
    relations that connect entities within a domain.
  - Entity & Relation Modeling: each entity carries typed attributes and a
    list of (relation_type, target_entity_id) pairs describing how it links
    to other entities in the same domain.
  - Analogy Construction: given a source and target domain, the engine
    auto-generates entity mappings by scoring type compatibility, attribute
    overlap, and relational structure similarity.
  - Validation & Refinement: external validation scores are folded back into
    mapping confidences and the overall analogy confidence; targeted
    adjustments refine individual mappings.
  - Knowledge Transfer: knowledge items anchored on source entities are
    projected onto target entities through the analogy's mappings, with per
    item transfer status tracking.
  - Domain Search: find domains most analogous to a given source domain,
    ranked by a composite similarity score.
  - Observability: aggregate statistics expose the state of the engine for
    telemetry and self-reflection.

Architecture:
    AgentAnalogyEngine (singleton)
    ├── DomainEntity      (a node within a domain, with attributes & relations)
    ├── DomainRelation    (a typed weighted link between two entities)
    ├── Domain            (a collection of entities and relations)
    ├── AnalogyMapping    (a single source->target entity correspondence)
    ├── Analogy           (a set of mappings + lifecycle + transfer results)
    └── AnalogyStats      (aggregate counters across the engine)

The engine is intentionally dependency-free so it can run in any Buddy
runtime without extra packages. All state mutations are guarded by a single
``threading.Lock`` and reads return fresh copies of mutable structures so
callers cannot mutate internal state by holding a reference.
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

class MappingType(str, Enum):
    """The kind of correspondence a single analogy mapping represents."""
    STRUCTURAL = "structural"    # source and target occupy the same structural role
    FUNCTIONAL = "functional"    # source and target serve the same function
    RELATIONAL = "relational"    # source and target relate to neighbors the same way
    ATTRIBUTE = "attribute"      # source and target share matching attributes
    CAUSAL = "causal"            # source and target sit at the same causal position


class AnalogyStatus(str, Enum):
    """Lifecycle state of an analogy."""
    DRAFT = "draft"            # freshly created, mappings auto-generated
    PROPOSED = "proposed"      # offered for validation
    VALIDATED = "validated"    # passed validation with sufficient confidence
    REJECTED = "rejected"      # failed validation
    REFINED = "refined"        # manually adjusted after validation
    ARCHIVED = "archived"      # no longer active, kept for history


class DomainType(str, Enum):
    """The conceptual nature of a domain."""
    CONCRETE = "concrete"      # tangible, physical entities (e.g. solar system)
    ABSTRACT = "abstract"      # conceptual entities (e.g. atomic model)
    PROCEDURAL = "procedural"  # steps / processes (e.g. recipe)
    CONCEPTUAL = "conceptual"  # ideas and relations (e.g. kinship terms)
    HYBRID = "hybrid"          # mixes more than one of the above


class ConfidenceLevel(str, Enum):
    """Coarse bucketing of a confidence score in [0, 1]."""
    LOW = "low"              # score in [0.0, 0.25)
    MEDIUM = "medium"        # score in [0.25, 0.55)
    HIGH = "high"            # score in [0.55, 0.85)
    VERY_HIGH = "very_high"  # score in [0.85, 1.0]


class TransferStatus(str, Enum):
    """Outcome of projecting a single knowledge item across an analogy."""
    PENDING = "pending"      # not yet attempted
    TRANSFERRED = "transferred"  # successfully projected onto the target
    FAILED = "failed"        # no usable mapping for the item's anchor
    PARTIAL = "partial"      # projected with reduced fidelity


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

def _copy_value(value: Any) -> Any:
    """Return a fresh copy of mutable containers, pass scalars through.

    Lists and dicts are shallow-copied so that callers cannot mutate the
    internal state by holding a reference to a returned value. Tuples are
    converted to lists for friendly serialization. Enum values are left
    untouched; callers convert them via ``to_dict``.
    """
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the closed interval [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _confidence_level(score: float) -> ConfidenceLevel:
    """Bucket a confidence score into a coarse ``ConfidenceLevel``."""
    if score < 0.25:
        return ConfidenceLevel.LOW
    if score < 0.55:
        return ConfidenceLevel.MEDIUM
    if score < 0.85:
        return ConfidenceLevel.HIGH
    return ConfidenceLevel.VERY_HIGH


def _jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity over two sets, defined as |A∩B| / |A∪B|.

    Returns 0.0 when both sets are empty so callers do not have to special
    case the empty/empty situation.
    """
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DomainEntity:
    """A single entity within a domain.

    An entity is a node described by a name, an ``entity_type`` (a free-form
    label such as "object", "role", "step"), a dict of typed ``attributes``,
    and a list of ``relations``. Each relation is a ``(relation_type,
    target_entity_id)`` tuple describing how this entity links to another
    entity in the same domain.
    """
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    domain_id: str = ""
    name: str = ""
    entity_type: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    relations: list[tuple[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "domain_id": self.domain_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "attributes": {k: _copy_value(v) for k, v in self.attributes.items()},
            "relations": [list(pair) for pair in self.relations],
            "created_at": self.created_at,
        }


@dataclass
class DomainRelation:
    """A typed, weighted link between two entities in a domain.

    ``directionality`` is one of "directed", "undirected", or
    "bidirectional". ``weight`` is a magnitude in [0, 1] describing how
    strongly the relation holds.
    """
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = ""
    target_id: str = ""
    relation_type: str = ""
    weight: float = 0.5
    directionality: str = "directed"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relation_id": self.relation_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "weight": self.weight,
            "directionality": self.directionality,
            "created_at": self.created_at,
        }


@dataclass
class Domain:
    """A collection of entities and the relations connecting them.

    The domain is the unit that participates in an analogy: a source domain
    is mapped onto a target domain entity by entity.
    """
    domain_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    domain_type: DomainType = DomainType.CONCEPTUAL
    entities: dict[str, DomainEntity] = field(default_factory=dict)
    relations: list[DomainRelation] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "description": self.description,
            "domain_type": self.domain_type.value
            if isinstance(self.domain_type, DomainType)
            else str(self.domain_type),
            "entities": {
                eid: e.to_dict() if hasattr(e, "to_dict") else dict(e)
                for eid, e in self.entities.items()
            },
            "relations": [
                r.to_dict() if hasattr(r, "to_dict") else dict(r)
                for r in self.relations
            ],
            "created_at": self.created_at,
        }


@dataclass
class AnalogyMapping:
    """A single source->target entity correspondence within an analogy.

    The ``mapping_type`` describes the nature of the correspondence, while
    ``confidence`` in [0, 1] expresses belief that the mapping is apt.
    ``justification`` is a short human-readable rationale.
    """
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_entity_id: str = ""
    target_entity_id: str = ""
    mapping_type: MappingType = MappingType.STRUCTURAL
    confidence: float = 0.5
    justification: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "mapping_type": self.mapping_type.value
            if isinstance(self.mapping_type, MappingType)
            else str(self.mapping_type),
            "confidence": self.confidence,
            "justification": self.justification,
            "created_at": self.created_at,
        }


@dataclass
class Analogy:
    """A set of mappings from a source domain onto a target domain.

    The analogy carries its lifecycle ``status``, an ``overall_confidence``
    in [0, 1] aggregated from its mappings, and a list of ``transfer_results``
    recording knowledge transfer attempts performed through the analogy.
    """
    analogy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_domain_id: str = ""
    target_domain_id: str = ""
    mappings: list[AnalogyMapping] = field(default_factory=list)
    overall_confidence: float = 0.0
    status: AnalogyStatus = AnalogyStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    validated_at: float | None = None
    transfer_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analogy_id": self.analogy_id,
            "source_domain_id": self.source_domain_id,
            "target_domain_id": self.target_domain_id,
            "mappings": [
                m.to_dict() if hasattr(m, "to_dict") else dict(m)
                for m in self.mappings
            ],
            "overall_confidence": self.overall_confidence,
            "status": self.status.value
            if isinstance(self.status, AnalogyStatus)
            else str(self.status),
            "created_at": self.created_at,
            "validated_at": self.validated_at,
            "transfer_results": [dict(r) for r in self.transfer_results],
        }


@dataclass
class AnalogyStats:
    """Aggregate statistics describing the state of the analogy engine."""
    total_domains: int = 0
    total_analogies: int = 0
    analogies_by_status: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    total_mappings: int = 0
    total_transfers: int = 0
    successful_transfers: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_domains": self.total_domains,
            "total_analogies": self.total_analogies,
            "analogies_by_status": dict(self.analogies_by_status),
            "avg_confidence": self.avg_confidence,
            "total_mappings": self.total_mappings,
            "total_transfers": self.total_transfers,
            "successful_transfers": self.successful_transfers,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Agent Analogy Engine
# ═══════════════════════════════════════════════════════════════════════════

# Mapping types considered when scoring relational similarity between two
# entities. Relation types are matched by exact string equality.
_RELATIONAL_MATCH_TYPES = frozenset({
    MappingType.RELATIONAL,
    MappingType.CAUSAL,
})


class AgentAnalogyEngine:
    """Cross-domain analogy engine with mapping, validation, and transfer.

    The engine maintains a registry of domains (each a graph of entities and
    relations) and a collection of analogies. An analogy is built by mapping
    each source entity onto the best-matching target entity; the matching
    score blends entity-type agreement, attribute-key overlap, and the
    similarity of each entity's neighborhood of relations.

    Once proposed, an analogy can be validated against external scores and
    refined through targeted adjustments. Knowledge items anchored on source
    entities can then be projected onto target entities through the analogy's
    mappings, with per-item transfer status tracking.

    All state mutations are guarded by a single ``threading.Lock`` so the
    engine is safe to invoke from concurrent agent threads. Reads return
    fresh copies of mutable structures to prevent external mutation of
    internal state.

    Capabilities:
      - Register and query domains, entities, and relations.
      - Auto-construct analogies with typed, confidence-scored mappings.
      - Validate analogies against external per-mapping scores.
      - Refine analogies through targeted confidence/justification edits.
      - Transfer knowledge items from source to target along mappings.
      - Rank domains by structural analogy to a given source domain.
    """

    # Capacity limits guarding unbounded growth.
    MAX_DOMAINS: int = 100
    MAX_ENTITIES_PER_DOMAIN: int = 200
    MAX_RELATIONS_PER_DOMAIN: int = 500
    MAX_ANALOGIES: int = 200
    # Confidence thresholds used during validation.
    VALIDATION_ACCEPT_THRESHOLD: float = 0.55
    VALIDATION_REJECT_THRESHOLD: float = 0.30

    def __init__(self) -> None:
        self._domains: dict[str, Domain] = {}
        self._analogies: dict[str, Analogy] = {}
        self._lock = threading.Lock()

    # ── Domain Management ───────────────────────────────────────────

    def register_domain(
        self,
        name: str,
        description: str = "",
        domain_type: DomainType = DomainType.CONCEPTUAL,
    ) -> Domain:
        """Create and register a new domain.

        Args:
            name: Human-readable name for the domain.
            description: Optional longer description of the domain's scope.
            domain_type: The conceptual nature of the domain.

        Returns:
            The newly created ``Domain`` registered with the engine.
        """
        with self._lock:
            if len(self._domains) >= self.MAX_DOMAINS:
                # Evict the oldest domain to make room for the new one.
                oldest_id = min(
                    self._domains.keys(),
                    key=lambda did: self._domains[did].created_at,
                )
                self._evict_domain(oldest_id)
            domain = Domain(
                name=name,
                description=description,
                domain_type=domain_type,
            )
            self._domains[domain.domain_id] = domain
            return domain

    def get_domain(self, domain_id: str) -> Domain | None:
        """Retrieve a domain by its identifier."""
        with self._lock:
            return self._domains.get(domain_id)

    def list_domains(
        self, domain_type: DomainType | None = None
    ) -> list[Domain]:
        """List registered domains, optionally filtered by type.

        Args:
            domain_type: Optional ``DomainType`` to filter by.

        Returns:
            A list of matching ``Domain`` objects.
        """
        with self._lock:
            if domain_type is None:
                return list(self._domains.values())
            return [
                d for d in self._domains.values() if d.domain_type == domain_type
            ]

    def _evict_domain(self, domain_id: str) -> None:
        """Remove a domain and any analogies referencing it.

        Must be called while holding ``self._lock``.
        """
        self._domains.pop(domain_id, None)
        for aid in [
            aid for aid, a in self._analogies.items()
            if a.source_domain_id == domain_id or a.target_domain_id == domain_id
        ]:
            self._analogies.pop(aid, None)

    # ── Entity CRUD ─────────────────────────────────────────────────

    def add_entity(
        self,
        domain_id: str,
        name: str,
        entity_type: str = "",
        attributes: dict[str, Any] | None = None,
    ) -> DomainEntity | None:
        """Add a new entity to a domain.

        Args:
            domain_id: The domain to add the entity to.
            name: Human-readable name of the entity.
            entity_type: Free-form type label (e.g. "object", "role").
            attributes: Optional dict of typed attributes.

        Returns:
            The created ``DomainEntity``, or ``None`` if the domain is
            missing or has reached its entity capacity.
        """
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return None
            if len(domain.entities) >= self.MAX_ENTITIES_PER_DOMAIN:
                return None
            entity = DomainEntity(
                domain_id=domain_id,
                name=name,
                entity_type=entity_type,
                attributes=dict(attributes) if attributes else {},
            )
            domain.entities[entity.entity_id] = entity
            return entity

    def get_entity(
        self, domain_id: str, entity_id: str
    ) -> DomainEntity | None:
        """Retrieve an entity from a domain by its identifier."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return None
            return domain.entities.get(entity_id)

    def list_entities(self, domain_id: str) -> list[DomainEntity]:
        """List all entities in a domain.

        Returns:
            A list of ``DomainEntity`` objects (empty if the domain does
            not exist).
        """
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return []
            return list(domain.entities.values())

    # ── Relation CRUD ───────────────────────────────────────────────

    def add_relation(
        self,
        domain_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 0.5,
        directionality: str = "directed",
    ) -> DomainRelation | None:
        """Add a relation between two entities in a domain.

        The relation is appended to the domain's ``relations`` list and also
        recorded on the source entity's ``relations`` field as a
        ``(relation_type, target_entity_id)`` tuple.

        Args:
            domain_id: The domain containing both entities.
            source_id: The source entity id.
            target_id: The target entity id.
            relation_type: Free-form label for the relation.
            weight: Magnitude in [0, 1].
            directionality: "directed", "undirected", or "bidirectional".

        Returns:
            The created ``DomainRelation``, or ``None`` if the domain or
            either endpoint is missing, or the relation capacity is reached.
        """
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return None
            if source_id not in domain.entities or target_id not in domain.entities:
                return None
            if len(domain.relations) >= self.MAX_RELATIONS_PER_DOMAIN:
                return None
            relation = DomainRelation(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                weight=_clamp(weight),
                directionality=directionality,
            )
            domain.relations.append(relation)
            source_entity = domain.entities[source_id]
            source_entity.relations.append((relation_type, target_id))
            if directionality in ("undirected", "bidirectional"):
                target_entity = domain.entities[target_id]
                target_entity.relations.append((relation_type, source_id))
            return relation

    def list_relations(self, domain_id: str) -> list[DomainRelation]:
        """List all relations in a domain.

        Returns:
            A list of ``DomainRelation`` objects (empty if the domain does
            not exist).
        """
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return []
            return list(domain.relations)

    # ── Analogy Construction ────────────────────────────────────────

    def create_analogy(
        self, source_domain_id: str, target_domain_id: str
    ) -> Analogy | None:
        """Construct an analogy by auto-mapping source entities to targets.

        For each entity in the source domain the engine scores every entity
        in the target domain by blending:
          - entity type agreement (exact match -> 1.0),
          - attribute key overlap (Jaccard over attribute keys),
          - relational neighborhood similarity (Jaccard over the multiset
            of neighbor relation types).
        The best scoring target is selected, a mapping is created, and the
        mapping type is derived from which signal dominated the score. The
        analogy's ``overall_confidence`` is the mean mapping confidence.

        Args:
            source_domain_id: The domain whose entities are mapped from.
            target_domain_id: The domain whose entities are mapped onto.

        Returns:
            The newly created ``Analogy`` in ``DRAFT`` status, or ``None``
            if either domain does not exist.
        """
        with self._lock:
            source = self._domains.get(source_domain_id)
            target = self._domains.get(target_domain_id)
            if source is None or target is None:
                return None
            if len(self._analogies) >= self.MAX_ANALOGIES:
                # Evict the oldest analogy to make room for the new one.
                oldest_id = min(
                    self._analogies.keys(),
                    key=lambda aid: self._analogies[aid].created_at,
                )
                self._analogies.pop(oldest_id, None)

            analogy = Analogy(
                source_domain_id=source_domain_id,
                target_domain_id=target_domain_id,
                status=AnalogyStatus.DRAFT,
            )
            used_targets: set[str] = set()
            for src_entity in source.entities.values():
                best_target_id, best_score, best_signal = self._best_target_match(
                    src_entity, target, used_targets
                )
                if best_target_id is None:
                    continue
                used_targets.add(best_target_id)
                confidence = _clamp(math.tanh(best_score))
                mapping_type = self._mapping_type_for_signal(best_signal)
                justification = self._justify_mapping(
                    src_entity, target.entities[best_target_id], best_score, best_signal
                )
                analogy.mappings.append(AnalogyMapping(
                    source_entity_id=src_entity.entity_id,
                    target_entity_id=best_target_id,
                    mapping_type=mapping_type,
                    confidence=confidence,
                    justification=justification,
                ))
            analogy.overall_confidence = self._mean_confidence(analogy.mappings)
            self._analogies[analogy.analogy_id] = analogy
            return analogy

    def _best_target_match(
        self,
        source_entity: DomainEntity,
        target_domain: Domain,
        used_targets: set[str],
    ) -> tuple[str | None, float, str]:
        """Find the best unused target entity for a source entity.

        Returns a ``(target_entity_id, score, signal)`` tuple where
        ``signal`` is one of "type", "attribute", "relational", "default".
        Returns ``(None, 0.0, "default")`` when the target domain has no
        available entities.

        Must be called while holding ``self._lock``.
        """
        best_id: str | None = None
        best_score = -1.0
        best_signal = "default"
        for candidate in target_domain.entities.values():
            if candidate.entity_id in used_targets:
                continue
            type_score = 1.0 if (
                source_entity.entity_type
                and source_entity.entity_type == candidate.entity_type
            ) else 0.0
            attr_score = _jaccard(
                set(source_entity.attributes.keys()),
                set(candidate.attributes.keys()),
            )
            src_neighbor_types = {rt for rt, _ in source_entity.relations}
            cand_neighbor_types = {rt for rt, _ in candidate.relations}
            rel_score = _jaccard(src_neighbor_types, cand_neighbor_types)
            # Blend: type agreement is the strongest single signal, then
            # relational structure, then attribute overlap.
            combined = 0.4 * type_score + 0.35 * rel_score + 0.25 * attr_score
            if combined > best_score:
                best_score = combined
                best_id = candidate.entity_id
                if type_score >= rel_score and type_score >= attr_score and type_score > 0.0:
                    best_signal = "type"
                elif rel_score >= attr_score and rel_score > 0.0:
                    best_signal = "relational"
                elif attr_score > 0.0:
                    best_signal = "attribute"
                else:
                    best_signal = "default"
        return best_id, best_score, best_signal

    def _mapping_type_for_signal(self, signal: str) -> MappingType:
        """Map a similarity signal label to a ``MappingType``."""
        if signal == "type":
            return MappingType.STRUCTURAL
        if signal == "relational":
            return MappingType.RELATIONAL
        if signal == "attribute":
            return MappingType.ATTRIBUTE
        return MappingType.FUNCTIONAL

    def _justify_mapping(
        self,
        source_entity: DomainEntity,
        target_entity: DomainEntity,
        score: float,
        signal: str,
    ) -> str:
        """Produce a short human-readable justification for a mapping."""
        level = _confidence_level(_clamp(math.tanh(score))).value
        if signal == "type":
            return (
                f"{source_entity.name} -> {target_entity.name}: "
                f"matching type '{source_entity.entity_type}' ({level})"
            )
        if signal == "relational":
            return (
                f"{source_entity.name} -> {target_entity.name}: "
                f"similar relational neighborhood ({level})"
            )
        if signal == "attribute":
            return (
                f"{source_entity.name} -> {target_entity.name}: "
                f"overlapping attributes ({level})"
            )
        return (
            f"{source_entity.name} -> {target_entity.name}: "
            f"best available match ({level})"
        )

    def _mean_confidence(self, mappings: list[AnalogyMapping]) -> float:
        """Compute the mean confidence across a list of mappings."""
        if not mappings:
            return 0.0
        total = sum(m.confidence for m in mappings)
        return total / len(mappings)

    def get_analogy(self, analogy_id: str) -> Analogy | None:
        """Retrieve an analogy by its identifier."""
        with self._lock:
            return self._analogies.get(analogy_id)

    def list_analogies(
        self, status: AnalogyStatus | None = None
    ) -> list[Analogy]:
        """List analogies, optionally filtered by status.

        Args:
            status: Optional ``AnalogyStatus`` to filter by.

        Returns:
            A list of matching ``Analogy`` objects.
        """
        with self._lock:
            if status is None:
                return list(self._analogies.values())
            return [a for a in self._analogies.values() if a.status == status]

    # ── Validation & Refinement ─────────────────────────────────────

    def validate_analogy(
        self,
        analogy_id: str,
        validation_scores: dict[str, float],
    ) -> Analogy | None:
        """Fold external validation scores into an analogy.

        ``validation_scores`` maps mapping ids to a score in [0, 1]. Each
        referenced mapping has its confidence replaced by the provided
        score (clamped to [0, 1]); mappings not present in the scores keep
        their current confidence. The analogy's ``overall_confidence`` is
        recomputed and its status is set to ``VALIDATED`` or ``REJECTED``
        based on the accept/reject thresholds. ``validated_at`` is stamped.

        Args:
            analogy_id: The analogy to validate.
            validation_scores: Mapping from mapping id to validation score.

        Returns:
            The updated ``Analogy``, or ``None`` if it does not exist.
        """
        with self._lock:
            analogy = self._analogies.get(analogy_id)
            if analogy is None:
                return None
            for mapping in analogy.mappings:
                if mapping.mapping_id in validation_scores:
                    mapping.confidence = _clamp(validation_scores[mapping.mapping_id])
            analogy.overall_confidence = self._mean_confidence(analogy.mappings)
            if analogy.overall_confidence >= self.VALIDATION_ACCEPT_THRESHOLD:
                analogy.status = AnalogyStatus.VALIDATED
            elif analogy.overall_confidence < self.VALIDATION_REJECT_THRESHOLD:
                analogy.status = AnalogyStatus.REJECTED
            else:
                # Mid-confidence: mark as proposed so it can be refined.
                analogy.status = AnalogyStatus.PROPOSED
            analogy.validated_at = time.time()
            return analogy

    def refine_analogy(
        self,
        analogy_id: str,
        adjustments: dict[str, dict[str, Any]],
    ) -> Analogy | None:
        """Apply targeted adjustments to an analogy's mappings.

        ``adjustments`` maps mapping ids to dicts that may contain
        ``confidence`` (a float in [0, 1]) and ``justification`` (a str).
        Only the supplied fields are overwritten. The analogy's
        ``overall_confidence`` is recomputed and its status is set to
        ``REFINED``.

        Args:
            analogy_id: The analogy to refine.
            adjustments: Mapping from mapping id to the fields to update.

        Returns:
            The updated ``Analogy``, or ``None`` if it does not exist.
        """
        with self._lock:
            analogy = self._analogies.get(analogy_id)
            if analogy is None:
                return None
            for mapping in analogy.mappings:
                if mapping.mapping_id not in adjustments:
                    continue
                change = adjustments[mapping.mapping_id]
                if "confidence" in change:
                    mapping.confidence = _clamp(float(change["confidence"]))
                if "justification" in change:
                    mapping.justification = str(change["justification"])
            analogy.overall_confidence = self._mean_confidence(analogy.mappings)
            analogy.status = AnalogyStatus.REFINED
            return analogy

    # ── Knowledge Transfer ──────────────────────────────────────────

    def transfer_knowledge(
        self,
        analogy_id: str,
        knowledge_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Project knowledge items from source to target along an analogy.

        Each item in ``knowledge_items`` is a dict that must carry an
        ``entity_id`` (the source anchor) and a ``content`` payload. The
        engine looks up the mapping whose ``source_entity_id`` matches the
        anchor and, if found, projects the item onto the mapping's target
        entity. Projection fidelity is derived from the mapping confidence:
        confidence >= 0.7 -> ``TRANSFERRED``, 0.4 <= confidence < 0.7 ->
        ``PARTIAL``, otherwise -> ``FAILED``.

        Each result records the source entity id, target entity id (or
        ``None``), the transfer status, and the projected content. Results
        are appended to the analogy's ``transfer_results``.

        Args:
            analogy_id: The analogy to transfer through.
            knowledge_items: List of item dicts to project.

        Returns:
            A summary dict with ``total``, ``transferred``, ``partial``,
            ``failed``, and ``results`` keys. If the analogy does not
            exist, ``total`` is 0 and ``results`` is empty.
        """
        with self._lock:
            analogy = self._analogies.get(analogy_id)
            if analogy is None:
                return {
                    "total": 0,
                    "transferred": 0,
                    "partial": 0,
                    "failed": 0,
                    "results": [],
                }
            mapping_by_source: dict[str, AnalogyMapping] = {
                m.source_entity_id: m for m in analogy.mappings
            }
            transferred = 0
            partial = 0
            failed = 0
            results: list[dict[str, Any]] = []
            for item in knowledge_items:
                source_entity_id = item.get("entity_id")
                content = item.get("content")
                mapping = mapping_by_source.get(source_entity_id) if source_entity_id else None
                if mapping is None:
                    failed += 1
                    status = TransferStatus.FAILED
                    target_entity_id = None
                    projected = None
                else:
                    target_entity_id = mapping.target_entity_id
                    confidence = mapping.confidence
                    if confidence >= 0.7:
                        transferred += 1
                        status = TransferStatus.TRANSFERRED
                        projected = _copy_value(content)
                    elif confidence >= 0.4:
                        partial += 1
                        status = TransferStatus.PARTIAL
                        projected = _copy_value(content)
                    else:
                        failed += 1
                        status = TransferStatus.FAILED
                        projected = None
                result = {
                    "source_entity_id": source_entity_id,
                    "target_entity_id": target_entity_id,
                    "status": status.value if isinstance(status, TransferStatus) else str(status),
                    "projected_content": projected,
                }
                results.append(result)
                analogy.transfer_results.append(dict(result))
            return {
                "total": len(knowledge_items),
                "transferred": transferred,
                "partial": partial,
                "failed": failed,
                "results": results,
            }

    # ── Domain Search ───────────────────────────────────────────────

    def find_analogous_domains(
        self,
        source_domain_id: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Rank domains by structural analogy to a given source domain.

        Each candidate domain (every registered domain except the source)
        is scored by blending:
          - entity count ratio (min/max of the two counts),
          - relation count ratio (min/max),
          - attribute key overlap (Jaccard over the union of attribute keys
            across all entities in each domain),
          - domain type compatibility bonus (same type -> 1.0, otherwise a
            small partial credit so hybrid domains stay competitive).
        The score is squashed through ``math.tanh`` into [0, 1].

        Args:
            source_domain_id: The domain to compare against.
            top_k: Maximum number of results to return.

        Returns:
            A list of dicts ``{"domain_id", "name", "score"}`` sorted by
            descending score, truncated to ``top_k``. Empty if the source
            domain does not exist or there are no other domains.
        """
        with self._lock:
            source = self._domains.get(source_domain_id)
            if source is None:
                return []
            source_entity_count = len(source.entities)
            source_relation_count = len(source.relations)
            source_attr_keys: set[str] = set()
            for e in source.entities.values():
                source_attr_keys.update(e.attributes.keys())
            scored: list[dict[str, Any]] = []
            for candidate in self._domains.values():
                if candidate.domain_id == source_domain_id:
                    continue
                count_ratio = self._safe_ratio(
                    source_entity_count, len(candidate.entities)
                )
                rel_ratio = self._safe_ratio(
                    source_relation_count, len(candidate.relations)
                )
                cand_attr_keys: set[str] = set()
                for e in candidate.entities.values():
                    cand_attr_keys.update(e.attributes.keys())
                attr_overlap = _jaccard(source_attr_keys, cand_attr_keys)
                type_compat = self._domain_type_compat(
                    source.domain_type, candidate.domain_type
                )
                raw = (
                    0.35 * count_ratio
                    + 0.25 * rel_ratio
                    + 0.25 * attr_overlap
                    + 0.15 * type_compat
                )
                score = _clamp(math.tanh(raw))
                scored.append({
                    "domain_id": candidate.domain_id,
                    "name": candidate.name,
                    "score": score,
                })
            scored.sort(key=lambda item: item["score"], reverse=True)
            if top_k > 0:
                scored = scored[:top_k]
            return scored

    def _safe_ratio(self, a: int, b: int) -> float:
        """min(a, b) / max(a, b), defined as 0.0 when both are zero."""
        if a == 0 and b == 0:
            return 0.0
        denom = max(a, b)
        if denom == 0:
            return 0.0
        return min(a, b) / denom

    def _domain_type_compat(
        self, a: DomainType, b: DomainType
    ) -> float:
        """Score compatibility between two domain types in [0, 1].

        Same type scores 1.0. Hybrid domains score 0.5 against any other
        type since they can bridge across categories. Otherwise 0.2.
        """
        if a == b:
            return 1.0
        if a == DomainType.HYBRID or b == DomainType.HYBRID:
            return 0.5
        return 0.2

    # ── Statistics & Maintenance ────────────────────────────────────

    def get_stats(self) -> AnalogyStats:
        """Compute aggregate statistics across the entire analogy engine."""
        with self._lock:
            total_analogies = len(self._analogies)
            by_status: dict[str, int] = {}
            confidence_sum = 0.0
            total_mappings = 0
            total_transfers = 0
            successful_transfers = 0
            for analogy in self._analogies.values():
                status_key = analogy.status.value if isinstance(
                    analogy.status, AnalogyStatus
                ) else str(analogy.status)
                by_status[status_key] = by_status.get(status_key, 0) + 1
                confidence_sum += analogy.overall_confidence
                total_mappings += len(analogy.mappings)
                for result in analogy.transfer_results:
                    total_transfers += 1
                    if result.get("status") == TransferStatus.TRANSFERRED.value:
                        successful_transfers += 1
            avg_confidence = (
                confidence_sum / total_analogies if total_analogies else 0.0
            )
            return AnalogyStats(
                total_domains=len(self._domains),
                total_analogies=total_analogies,
                analogies_by_status=by_status,
                avg_confidence=avg_confidence,
                total_mappings=total_mappings,
                total_transfers=total_transfers,
                successful_transfers=successful_transfers,
            )

    def clear(self) -> int:
        """Clear all engine state and return the number of items removed.

        The count is the sum of removed domains and analogies.
        """
        with self._lock:
            removed = len(self._domains) + len(self._analogies)
            self._domains.clear()
            self._analogies.clear()
            return removed


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_global_analogy_engine: AgentAnalogyEngine | None = None


def get_analogy_engine() -> AgentAnalogyEngine:
    """Get or create the singleton AgentAnalogyEngine instance."""
    global _global_analogy_engine
    if _global_analogy_engine is None:
        _global_analogy_engine = AgentAnalogyEngine()
    return _global_analogy_engine


def reset_analogy_engine() -> None:
    """Reset the singleton AgentAnalogyEngine instance."""
    global _global_analogy_engine
    _global_analogy_engine = None
