"""Buddy Knowledge Graph — Entity-relationship modeling for agent memory

Provides a graph-based knowledge representation system where entities
and their relationships are stored, queried, and reasoned about. Supports
semantic search, path finding, and knowledge extraction from conversations.

Features:
- Entity creation with typed properties and metadata
- Relationship definition with weights and direction
- Graph traversal with path finding and neighborhood exploration
- Semantic entity search using embedding similarity
- Knowledge extraction from conversation text
- Graph visualization data export
- Subgraph extraction for focused context
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.kg")


# ══════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════

@dataclass
class Entity:
    id: str
    name: str
    entity_type: str  # person, concept, project, tool, event, etc.
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    confidence: float = 1.0
    source: str = ""  # Where this entity was extracted from
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Relationship:
    id: str
    source_id: str
    target_id: str
    relation_type: str  # depends_on, created_by, part_of, similar_to, etc.
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GraphPath:
    entities: list[Entity]
    relationships: list[Relationship]
    total_weight: float = 0.0
    path_length: int = 0


# ══════════════════════════════════════════════════════════════
# Knowledge Graph
# ══════════════════════════════════════════════════════════════

class KnowledgeGraph:
    """Graph-based knowledge representation with entity-relationship modeling.

    Entities represent concepts, people, tools, and other real-world objects.
    Relationships connect entities with typed, weighted edges. The graph
    supports semantic search, path finding, and knowledge extraction.
    """

    MAX_ENTITIES = 10000
    MAX_RELATIONSHIPS = 50000

    def __init__(self, agent_id: str = ""):
        self.agent_id = agent_id
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        self._adjacency: dict[str, list[str]] = {}  # entity_id -> [rel_id, ...]
        self._type_index: dict[str, list[str]] = {}  # entity_type -> [entity_id, ...]
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._stats = {
            "total_queries": 0,
            "total_extractions": 0,
        }

    # ── Entity Management ───────────────────────────────

    def add_entity(self, entity: Entity) -> str:
        """Add an entity to the knowledge graph."""
        if len(self._entities) >= self.MAX_ENTITIES:
            oldest = min(self._entities.values(), key=lambda e: e.created_at)
            self.remove_entity(oldest.id)
            logger.debug(f"KG: pruned oldest entity '{oldest.name}'")

        self._entities[entity.id] = entity
        if entity.entity_type not in self._type_index:
            self._type_index[entity.entity_type] = []
        if entity.id not in self._type_index[entity.entity_type]:
            self._type_index[entity.entity_type].append(entity.id)

        if entity.id not in self._adjacency:
            self._adjacency[entity.id] = []

        return entity.id

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def update_entity(self, entity_id: str, **updates) -> bool:
        """Update entity properties."""
        entity = self._entities.get(entity_id)
        if not entity:
            return False
        for key, value in updates.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
            else:
                entity.properties[key] = value
        entity.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and all its relationships."""
        entity = self._entities.pop(entity_id, None)
        if not entity:
            return False

        # Remove from type index
        if entity.entity_type in self._type_index:
            self._type_index[entity.entity_type] = [
                eid for eid in self._type_index[entity.entity_type] if eid != entity_id
            ]

        # Remove all relationships involving this entity
        rels_to_remove = list(self._adjacency.get(entity_id, []))
        for rel_id in rels_to_remove:
            self._remove_relationship_internal(rel_id)

        self._adjacency.pop(entity_id, None)
        return True

    def find_entities(
        self,
        entity_type: str | None = None,
        name_contains: str = "",
        limit: int = 50,
    ) -> list[Entity]:
        """Find entities by type and/or name substring."""
        results = []

        candidate_ids = (
            self._type_index.get(entity_type, list(self._entities.keys()))
            if entity_type
            else list(self._entities.keys())
        )

        for eid in candidate_ids:
            entity = self._entities.get(eid)
            if not entity:
                continue
            if name_contains and name_contains.lower() not in entity.name.lower():
                continue
            results.append(entity)
            if len(results) >= limit:
                break

        return results

    # ── Relationship Management ─────────────────────────

    def add_relationship(self, rel: Relationship) -> str | None:
        """Add a relationship between two entities."""
        if len(self._relationships) >= self.MAX_RELATIONSHIPS:
            oldest = min(self._relationships.values(), key=lambda r: r.created_at)
            self._remove_relationship_internal(oldest.id)

        if rel.source_id not in self._entities or rel.target_id not in self._entities:
            logger.debug(f"KG: Cannot create relationship — entity not found")
            return None

        self._relationships[rel.id] = rel

        if rel.source_id not in self._adjacency:
            self._adjacency[rel.source_id] = []
        self._adjacency[rel.source_id].append(rel.id)

        if rel.target_id not in self._adjacency:
            self._adjacency[rel.target_id] = []
        self._adjacency[rel.target_id].append(rel.id)

        return rel.id

    def get_relationships(self, entity_id: str) -> list[Relationship]:
        """Get all relationships for an entity."""
        rel_ids = self._adjacency.get(entity_id, [])
        return [self._relationships[rid] for rid in rel_ids if rid in self._relationships]

    def _remove_relationship_internal(self, rel_id: str):
        """Remove a relationship and clean up adjacency."""
        rel = self._relationships.pop(rel_id, None)
        if rel:
            for entity_id in (rel.source_id, rel.target_id):
                if entity_id in self._adjacency:
                    self._adjacency[entity_id] = [
                        rid for rid in self._adjacency[entity_id] if rid != rel_id
                    ]

    def remove_relationship(self, rel_id: str) -> bool:
        if rel_id in self._relationships:
            self._remove_relationship_internal(rel_id)
            return True
        return False

    # ── Graph Traversal ─────────────────────────────────

    def get_neighborhood(
        self,
        entity_id: str,
        depth: int = 1,
        max_entities: int = 50,
    ) -> dict:
        """Get the neighborhood around an entity up to a given depth."""
        visited_entities: dict[str, Entity] = {}
        visited_rels: dict[str, Relationship] = {}
        queue = deque([(entity_id, 0)])

        while queue and len(visited_entities) < max_entities:
            current_id, current_depth = queue.popleft()
            if current_id in visited_entities:
                continue
            entity = self._entities.get(current_id)
            if not entity:
                continue
            visited_entities[current_id] = entity

            if current_depth < depth:
                for rel_id in self._adjacency.get(current_id, []):
                    rel = self._relationships.get(rel_id)
                    if not rel:
                        continue
                    visited_rels[rel_id] = rel
                    neighbor_id = rel.target_id if rel.source_id == current_id else rel.source_id
                    if neighbor_id not in visited_entities:
                        queue.append((neighbor_id, current_depth + 1))

        return {
            "center": entity_id,
            "depth": depth,
            "entities": [
                {"id": e.id, "name": e.name, "type": e.entity_type, "properties": e.properties}
                for e in visited_entities.values()
            ],
            "relationships": [
                {"id": r.id, "source": r.source_id, "target": r.target_id,
                 "type": r.relation_type, "weight": r.weight}
                for r in visited_rels.values()
            ],
        }

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        max_paths: int = 5,
    ) -> list[GraphPath]:
        """Find paths between two entities using BFS."""
        if source_id not in self._entities or target_id not in self._entities:
            return []

        paths = []
        queue = deque()
        queue.append((source_id, [], [], 0.0))

        while queue and len(paths) < max_paths:
            current, visited, rels, total_weight = queue.popleft()

            if len(visited) >= max_depth:
                continue

            for rel_id in self._adjacency.get(current, []):
                rel = self._relationships.get(rel_id)
                if not rel:
                    continue
                neighbor = rel.target_id if rel.source_id == current else rel.source_id
                if neighbor in visited:
                    continue

                new_visited = visited + [current]
                new_rels = rels + [rel]
                new_weight = total_weight + rel.weight

                if neighbor == target_id:
                    path_entities = [self._entities[eid] for eid in new_visited + [neighbor]]
                    paths.append(GraphPath(
                        entities=path_entities,
                        relationships=new_rels,
                        total_weight=new_weight,
                        path_length=len(new_rels),
                    ))
                else:
                    queue.append((neighbor, new_visited, new_rels, new_weight))

        paths.sort(key=lambda p: (p.path_length, -p.total_weight))
        return paths[:max_paths]

    # ── Semantic Search ─────────────────────────────────

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        entity_type: str | None = None,
    ) -> list[dict]:
        """Search entities by semantic similarity to the query."""
        self._stats["total_queries"] += 1

        try:
            query_embedding = await self._get_embedding(query)
        except Exception as e:
            logger.warning(f"KG semantic search embedding failed: {e}")
            return self._fallback_text_search(query, top_k, entity_type)

        candidates = (
            self._type_index.get(entity_type, list(self._entities.keys()))
            if entity_type
            else list(self._entities.keys())
        )

        scored = []
        for eid in candidates:
            entity = self._entities.get(eid)
            if not entity:
                continue
            if entity.embedding:
                similarity = self._cosine_similarity(query_embedding, entity.embedding)
                scored.append((similarity, entity))
            else:
                # Text fallback for entities without embeddings
                if query.lower() in entity.name.lower():
                    scored.append((0.7, entity))

        scored.sort(key=lambda x: -x[0])
        return [
            {
                "entity_id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "similarity": round(s, 4),
                "properties": e.properties,
            }
            for s, e in scored[:top_k]
        ]

    def _fallback_text_search(
        self,
        query: str,
        top_k: int,
        entity_type: str | None,
    ) -> list[dict]:
        """Fallback to text-based search when embeddings fail."""
        candidates = self.find_entities(entity_type=entity_type, name_contains=query, limit=top_k)
        return [
            {
                "entity_id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "similarity": 0.7,
                "properties": e.properties,
            }
            for e in candidates
        ]

    # ── Knowledge Extraction ────────────────────────────

    async def extract_from_text(
        self,
        text: str,
        source: str = "conversation",
    ) -> dict:
        """Extract entities and relationships from natural language text."""
        self._stats["total_extractions"] += 1

        try:
            extraction_result = await self._llm_extract(text)
            new_entities = []
            new_relationships = []

            for ent_data in extraction_result.get("entities", []):
                entity = Entity(
                    id=f"ent-{uuid.uuid4().hex[:12]}",
                    name=ent_data["name"],
                    entity_type=ent_data.get("type", "concept"),
                    properties=ent_data.get("properties", {}),
                    confidence=ent_data.get("confidence", 0.8),
                    source=source,
                )
                self.add_entity(entity)
                new_entities.append(entity.id)

            for rel_data in extraction_result.get("relationships", []):
                source_ent = self._find_entity_by_name(rel_data["source"])
                target_ent = self._find_entity_by_name(rel_data["target"])
                if source_ent and target_ent:
                    relationship = Relationship(
                        id=f"rel-{uuid.uuid4().hex[:12]}",
                        source_id=source_ent.id,
                        target_id=target_ent.id,
                        relation_type=rel_data.get("type", "related_to"),
                        weight=rel_data.get("weight", 1.0),
                        confidence=rel_data.get("confidence", 0.8),
                    )
                    rel_id = self.add_relationship(relationship)
                    if rel_id:
                        new_relationships.append(rel_id)

            return {
                "new_entities": len(new_entities),
                "new_relationships": len(new_relationships),
                "entity_ids": new_entities,
                "relationship_ids": new_relationships,
            }

        except Exception as e:
            logger.error(f"KG extraction failed: {e}")
            return {"new_entities": 0, "new_relationships": 0, "error": str(e)}

    async def _llm_extract(self, text: str) -> dict:
        """Use LLM to extract entities and relationships from text."""
        import json

        prompt = f"""Extract key entities and their relationships from the following text.
Return a JSON object with 'entities' and 'relationships' arrays.

Text:
{text[:4000]}

For entities, include: name, type (person/concept/project/tool/event/organization/location), properties (dict), confidence (0.0-1.0)
For relationships, include: source (entity name), target (entity name), type (depends_on/created_by/part_of/similar_to/related_to/uses/produces/opposes), weight (0.0-1.0), confidence (0.0-1.0)

Return ONLY valid JSON, no other text."""

        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )
        content = response.choices[0].message.content or "{}"

        # Extract JSON from response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                return json.loads(match.group())
            return {"entities": [], "relationships": []}

    def _find_entity_by_name(self, name: str) -> Entity | None:
        """Find an entity by exact or close name match."""
        name_lower = name.lower().strip()
        for entity in self._entities.values():
            if entity.name.lower().strip() == name_lower:
                return entity
        # Partial match fallback
        for entity in self._entities.values():
            if name_lower in entity.name.lower() or entity.name.lower() in name_lower:
                return entity
        return None

    # ── Export / Import ─────────────────────────────────

    def export_subgraph(
        self,
        entity_ids: list[str],
        include_neighbors: bool = False,
    ) -> dict:
        """Export a subgraph for visualization or transfer."""
        export_entities = {}
        export_relationships = {}

        entity_set = set(entity_ids)

        if include_neighbors:
            for eid in list(entity_set):
                for rel_id in self._adjacency.get(eid, []):
                    rel = self._relationships.get(rel_id)
                    if rel:
                        entity_set.add(rel.source_id)
                        entity_set.add(rel.target_id)

        for eid in entity_set:
            entity = self._entities.get(eid)
            if entity:
                export_entities[eid] = {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.entity_type,
                    "properties": entity.properties,
                }

        for rel_id, rel in self._relationships.items():
            if rel.source_id in entity_set and rel.target_id in entity_set:
                export_relationships[rel_id] = {
                    "id": rel.id,
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relation_type,
                    "weight": rel.weight,
                }

        return {
            "entities": list(export_entities.values()),
            "relationships": list(export_relationships.values()),
            "entity_count": len(export_entities),
            "relationship_count": len(export_relationships),
        }

    def get_visualization_data(self, limit: int = 100) -> dict:
        """Export graph data in a format suitable for visualization."""
        entities = list(self._entities.values())[:limit]
        entity_ids = {e.id for e in entities}

        rels = [
            r for r in self._relationships.values()
            if r.source_id in entity_ids and r.target_id in entity_ids
        ]

        return {
            "nodes": [
                {"id": e.id, "label": e.name, "group": e.entity_type}
                for e in entities
            ],
            "edges": [
                {"id": r.id, "from": r.source_id, "to": r.target_id,
                 "label": r.relation_type, "value": r.weight}
                for r in rels
            ],
        }

    # ── Utilities ───────────────────────────────────────

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for semantic search."""
        response = await self._client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],
        )
        return response.data[0].embedding

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        import numpy as np
        a_arr = np.array(a)
        b_arr = np.array(b)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))

    def clear(self):
        """Clear all entities and relationships."""
        self._entities.clear()
        self._relationships.clear()
        self._adjacency.clear()
        self._type_index.clear()

    # ── Statistics ──────────────────────────────────────

    def get_stats(self) -> dict:
        entity_types = {t: len(ids) for t, ids in self._type_index.items()}
        return {
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationships),
            "entity_types": entity_types,
            "total_queries": self._stats["total_queries"],
            "total_extractions": self._stats["total_extractions"],
            "graph_density": (
                len(self._relationships) / max(len(self._entities) * (len(self._entities) - 1), 1)
            ),
        }