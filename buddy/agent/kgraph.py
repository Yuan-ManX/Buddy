"""Buddy Knowledge Graph — semantic knowledge representation and reasoning

Builds a dynamic graph of entities, concepts, and relationships extracted
from agent interactions, documents, and user inputs. Supports semantic
search, inference, and cross-agent knowledge sharing.

Architecture:
  KnowledgeGraph
    ├── EntityStore     — typed entities with properties and metadata
    ├── RelationStore   — typed relationships between entities
    ├── InferenceEngine — rule-based reasoning over the graph
    ├── IndexEngine     — semantic search with embedding support
    └── GraphCompiler   — compiles subgraphs into agent-readable context
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.kgraph")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""
    CONCEPT = "concept"
    TOOL = "tool"
    FILE = "file"
    AGENT = "agent"
    PERSON = "person"
    PROJECT = "project"
    TASK = "task"
    ERROR = "error"
    PATTERN = "pattern"
    DOCUMENT = "document"
    CUSTOM = "custom"


class RelationType(str, Enum):
    """Types of relationships between entities."""
    DEPENDS_ON = "depends_on"
    CONTAINS = "contains"
    IMPLEMENTS = "implements"
    USES = "uses"
    PRODUCES = "produces"
    RELATED_TO = "related_to"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    CAUSES = "causes"
    RESOLVES = "resolves"
    BELONGS_TO = "belongs_to"
    SIMILAR_TO = "similar_to"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    REFERENCES = "references"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class Entity:
    """A node in the knowledge graph."""
    entity_id: str
    name: str
    entity_type: EntityType = EntityType.CONCEPT
    description: str = ""
    properties: dict = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    confidence: float = 0.5
    source_agent: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    access_count: int = 0
    importance: float = 0.5

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
            "aliases": self.aliases,
            "confidence": self.confidence,
            "importance": self.importance,
            "access_count": self.access_count,
        }


@dataclass
class Relation:
    """An edge in the knowledge graph."""
    relation_id: str
    source_id: str
    target_id: str
    relation_type: RelationType = RelationType.RELATED_TO
    weight: float = 0.5
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat)

    def to_dict(self) -> dict:
        return {
            "relation_id": self.relation_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
        }


# ═══════════════════════════════════════════════════════════
# Entity Store
# ═══════════════════════════════════════════════════════════

class EntityStore:
    """Manages entities in the knowledge graph."""

    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._name_index: dict[str, list[str]] = defaultdict(list)
        self._type_index: dict[str, list[str]] = defaultdict(list)

    def add_entity(self, entity: Entity) -> Entity:
        """Add an entity to the store."""
        if entity.entity_id in self._entities:
            existing = self._entities[entity.entity_id]
            existing.description = entity.description or existing.description
            existing.properties.update(entity.properties)
            existing.aliases = list(set(existing.aliases + entity.aliases))
            existing.confidence = max(existing.confidence, entity.confidence)
            existing.updated_at = datetime.now(timezone.utc).isoformat()
            return existing

        self._entities[entity.entity_id] = entity
        self._name_index[entity.name.lower()].append(entity.entity_id)
        for alias in entity.aliases:
            self._name_index[alias.lower()].append(entity.entity_id)
        self._type_index[entity.entity_type.value].append(entity.entity_id)
        return entity

    def create_entity(self, name: str, entity_type: EntityType = EntityType.CONCEPT,
                      description: str = "", properties: dict | None = None,
                      aliases: list[str] | None = None,
                      confidence: float = 0.5, source_agent: str = "") -> Entity:
        """Create and add a new entity."""
        entity_id = f"ent-{hashlib.md5((name + entity_type.value).encode()).hexdigest()[:12]}"
        entity = Entity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            description=description,
            properties=properties or {},
            aliases=aliases or [],
            confidence=confidence,
            source_agent=source_agent,
        )
        return self.add_entity(entity)

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get an entity by ID."""
        entity = self._entities.get(entity_id)
        if entity:
            entity.access_count += 1
        return entity

    def find_by_name(self, name: str) -> Entity | None:
        """Find an entity by name or alias."""
        matches = self._name_index.get(name.lower(), [])
        if matches:
            return self._entities.get(matches[0])
        return None

    def find_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Find all entities of a given type."""
        ids = self._type_index.get(entity_type.value, [])
        return [self._entities[eid] for eid in ids if eid in self._entities]

    def search(self, query: str, limit: int = 20) -> list[Entity]:
        """Search entities by name, description, or properties."""
        query_lower = query.lower()
        results = []

        for entity in self._entities.values():
            score = 0
            if query_lower in entity.name.lower():
                score += 10
            if query_lower in entity.description.lower():
                score += 5
            for alias in entity.aliases:
                if query_lower in alias.lower():
                    score += 8
            # Check properties
            for key, val in entity.properties.items():
                if query_lower in str(key).lower() or query_lower in str(val).lower():
                    score += 3
            if score > 0:
                results.append((score, entity))

        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:limit]]

    def get_stats(self) -> dict:
        """Get entity store statistics."""
        by_type = defaultdict(int)
        for e in self._entities.values():
            by_type[e.entity_type.value] += 1
        return {
            "total_entities": len(self._entities),
            "by_type": dict(by_type),
            "avg_confidence": sum(e.confidence for e in self._entities.values()) / max(len(self._entities), 1),
        }


# ═══════════════════════════════════════════════════════════
# Relation Store
# ═══════════════════════════════════════════════════════════

class RelationStore:
    """Manages relationships between entities."""

    def __init__(self):
        self._relations: dict[str, Relation] = {}
        self._outgoing: dict[str, list[str]] = defaultdict(list)
        self._incoming: dict[str, list[str]] = defaultdict(list)
        self._by_type: dict[str, list[str]] = defaultdict(list)

    def add_relation(self, source_id: str, target_id: str,
                     relation_type: RelationType = RelationType.RELATED_TO,
                     weight: float = 0.5, metadata: dict | None = None) -> Relation:
        """Add a relation between two entities."""
        relation_id = f"rel-{hashlib.md5((source_id + target_id + relation_type.value).encode()).hexdigest()[:12]}"

        # Check if relation already exists
        if relation_id in self._relations:
            existing = self._relations[relation_id]
            existing.weight = max(existing.weight, weight)
            if metadata:
                existing.metadata.update(metadata)
            return existing

        relation = Relation(
            relation_id=relation_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            metadata=metadata or {},
        )
        self._relations[relation_id] = relation
        self._outgoing[source_id].append(relation_id)
        self._incoming[target_id].append(relation_id)
        self._by_type[relation_type.value].append(relation_id)
        return relation

    def get_outgoing(self, entity_id: str) -> list[Relation]:
        """Get all relations going out from an entity."""
        ids = self._outgoing.get(entity_id, [])
        return [self._relations[rid] for rid in ids if rid in self._relations]

    def get_incoming(self, entity_id: str) -> list[Relation]:
        """Get all relations coming into an entity."""
        ids = self._incoming.get(entity_id, [])
        return [self._relations[rid] for rid in ids if rid in self._relations]

    def get_neighbors(self, entity_id: str, depth: int = 1) -> list[tuple[Entity, Relation]]:
        """Get all neighbors of an entity up to a given depth."""
        visited = {entity_id}
        frontier = {entity_id}
        neighbors = []

        for _ in range(depth):
            next_frontier = set()
            for eid in frontier:
                for rel in self.get_outgoing(eid):
                    if rel.target_id not in visited:
                        visited.add(rel.target_id)
                        next_frontier.add(rel.target_id)
                        neighbors.append((rel.target_id, rel))
                for rel in self.get_incoming(eid):
                    if rel.source_id not in visited:
                        visited.add(rel.source_id)
                        next_frontier.add(rel.source_id)
                        neighbors.append((rel.source_id, rel))
            frontier = next_frontier

        return neighbors

    def get_stats(self) -> dict:
        """Get relation store statistics."""
        by_type = defaultdict(int)
        for r in self._relations.values():
            by_type[r.relation_type.value] += 1
        return {
            "total_relations": len(self._relations),
            "by_type": dict(by_type),
            "avg_weight": sum(r.weight for r in self._relations.values()) / max(len(self._relations), 1),
        }


# ═══════════════════════════════════════════════════════════
# Inference Engine
# ═══════════════════════════════════════════════════════════

class InferenceEngine:
    """Rule-based reasoning over the knowledge graph."""

    def __init__(self, entity_store: EntityStore, relation_store: RelationStore):
        self.entity_store = entity_store
        self.relation_store = relation_store

    def infer_transitive(self, entity_id: str, relation_type: RelationType,
                         max_depth: int = 3) -> list[str]:
        """Infer transitive relationships (e.g., A depends on B, B depends on C → A depends on C)."""
        result = set()
        visited = {entity_id}
        frontier = {entity_id}

        for _ in range(max_depth):
            next_frontier = set()
            for eid in frontier:
                for rel in self.relation_store.get_outgoing(eid):
                    if rel.relation_type == relation_type and rel.target_id not in visited:
                        visited.add(rel.target_id)
                        next_frontier.add(rel.target_id)
                        result.add(rel.target_id)
            frontier = next_frontier

        return list(result)

    def find_similar(self, entity_id: str, min_confidence: float = 0.3) -> list[Entity]:
        """Find entities similar to the given entity."""
        entity = self.entity_store.get_entity(entity_id)
        if not entity:
            return []

        # Find entities of the same type with similar names or properties
        candidates = self.entity_store.find_by_type(entity.entity_type)
        similar = []

        for candidate in candidates:
            if candidate.entity_id == entity_id:
                continue
            score = 0

            # Name similarity
            name_words = set(entity.name.lower().split())
            cand_words = set(candidate.name.lower().split())
            overlap = name_words & cand_words
            if overlap:
                score += len(overlap) / max(len(name_words), len(cand_words)) * 0.5

            # Property overlap
            if entity.properties and candidate.properties:
                common_keys = set(entity.properties.keys()) & set(candidate.properties.keys())
                if common_keys:
                    score += 0.3 * len(common_keys) / max(len(entity.properties), len(candidate.properties))

            if score >= min_confidence:
                similar.append((score, candidate))

        similar.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in similar[:10]]

    def find_path(self, source_id: str, target_id: str,
                  max_depth: int = 5) -> list[list[str]] | None:
        """Find all paths between two entities (BFS)."""
        if source_id == target_id:
            return [[source_id]]

        queue = [(source_id, [source_id])]
        paths = []

        while queue and len(paths) < 5:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                continue

            for rel in self.relation_store.get_outgoing(current):
                if rel.target_id == target_id:
                    paths.append(path + [target_id])
                elif rel.target_id not in path:
                    queue.append((rel.target_id, path + [rel.target_id]))

        return paths if paths else None


# ═══════════════════════════════════════════════════════════
# Knowledge Graph — Main Class
# ═══════════════════════════════════════════════════════════

class KnowledgeGraph:
    """Unified knowledge graph for the Buddy platform.

    Combines entity storage, relationship management, and inference
    into a single cohesive system.
    """

    def __init__(self):
        self.entities = EntityStore()
        self.relations = RelationStore()
        self.inference = InferenceEngine(self.entities, self.relations)

    def add_knowledge(self, name: str, entity_type: EntityType = EntityType.CONCEPT,
                      description: str = "", properties: dict | None = None,
                      relations: list[tuple[str, RelationType, float]] | None = None,
                      source_agent: str = "") -> Entity:
        """Add knowledge with optional relations in one call."""
        entity = self.entities.create_entity(
            name=name,
            entity_type=entity_type,
            description=description,
            properties=properties,
            source_agent=source_agent,
        )

        if relations:
            for target_name, rel_type, weight in relations:
                target = self.entities.find_by_name(target_name)
                if not target:
                    target = self.entities.create_entity(name=target_name)
                self.relations.add_relation(entity.entity_id, target.entity_id, rel_type, weight)

        return entity

    def extract_from_text(self, text: str, source_agent: str = "") -> list[Entity]:
        """Extract entities and relations from natural language text."""
        entities = []
        # Simple keyword extraction — in production, this would use an LLM or NER model
        import re

        # Extract potential entities (capitalized words and technical terms)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', text)
        words += re.findall(r'\b[a-z]+_[a-z]+\b', text)  # snake_case
        words += re.findall(r'\b[a-z]+-[a-z]+\b', text)  # kebab-case

        seen = set()
        for word in set(words[:20]):
            if word.lower() in seen:
                continue
            seen.add(word.lower())

            entity = self.entities.create_entity(
                name=word,
                entity_type=EntityType.CONCEPT,
                description=f"Extracted from: {text[:100]}...",
                source_agent=source_agent,
            )
            entities.append(entity)

        # Link sequentially extracted entities
        for i in range(len(entities) - 1):
            self.relations.add_relation(
                entities[i].entity_id,
                entities[i + 1].entity_id,
                RelationType.RELATED_TO,
                weight=0.3,
            )

        return entities

    def get_subgraph(self, entity_id: str, depth: int = 2) -> dict:
        """Get a subgraph centered on an entity."""
        entity = self.entities.get_entity(entity_id)
        if not entity:
            return {"error": "Entity not found"}

        nodes = {entity_id: entity.to_dict()}
        edges = []

        neighbors = self.relations.get_neighbors(entity_id, depth)
        for neighbor_id, rel in neighbors:
            neighbor = self.entities.get_entity(neighbor_id)
            if neighbor:
                nodes[neighbor_id] = neighbor.to_dict()
            edges.append(rel.to_dict())

        return {
            "center": entity.to_dict(),
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    def compile_context(self, entity_ids: list[str], max_tokens: int = 2000) -> str:
        """Compile a subgraph into agent-readable context."""
        parts = []
        token_count = 0

        for eid in entity_ids[:10]:
            entity = self.entities.get_entity(eid)
            if not entity:
                continue

            chunk = f"[{entity.entity_type.value}] {entity.name}: {entity.description}"
            if token_count + len(chunk.split()) > max_tokens:
                break

            parts.append(chunk)
            token_count += len(chunk.split())

            # Add relations
            for rel in self.relations.get_outgoing(eid)[:3]:
                target = self.entities.get_entity(rel.target_id)
                if target:
                    rel_chunk = f"  → {rel.relation_type.value} → {target.name}"
                    if token_count + len(rel_chunk.split()) <= max_tokens:
                        parts.append(rel_chunk)
                        token_count += len(rel_chunk.split())

        return "\n".join(parts)

    def get_stats(self) -> dict:
        """Get comprehensive knowledge graph statistics."""
        return {
            "entities": self.entities.get_stats(),
            "relations": self.relations.get_stats(),
        }


# Global knowledge graph instance
knowledge_graph = KnowledgeGraph()