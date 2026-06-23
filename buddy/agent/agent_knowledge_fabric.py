"""Buddy Knowledge Fabric — AI-Native Interconnected Knowledge System

The Knowledge Fabric weaves all knowledge sources into a single, queryable,
self-organizing intelligence layer. It provides:
- Semantic knowledge graph with automatic entity extraction
- Cross-domain knowledge linking and inference
- Real-time knowledge synthesis from multiple sources
- Self-organizing topic clusters and taxonomies
- Knowledge provenance tracking and versioning
- Query-time knowledge assembly and ranking
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.knowledge_fabric")


# ── Core Enums ────────────────────────────────────────────────────

class KnowledgeDomain(str, Enum):
    """Knowledge domains for categorization."""
    TECHNOLOGY = "technology"
    SCIENCE = "science"
    BUSINESS = "business"
    CREATIVE = "creative"
    PERSONAL = "personal"
    SYSTEM = "system"
    AGENT = "agent"
    CUSTOM = "custom"


class KnowledgeType(str, Enum):
    """Types of knowledge entries."""
    FACT = "fact"                   # Verified factual information
    CONCEPT = "concept"             # Abstract concept or idea
    PROCEDURE = "procedure"         # Step-by-step procedure
    INSIGHT = "insight"             # Derived insight or pattern
    CODE = "code"                   # Code snippet or algorithm
    DOCUMENT = "document"           # Reference document
    CONVERSATION = "conversation"   # Conversation-derived knowledge
    MEMORY = "memory"               # Agent memory entry
    EXTERNAL = "external"           # External source knowledge


class KnowledgeStatus(str, Enum):
    """Lifecycle status of a knowledge entry."""
    DRAFT = "draft"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class RelationType(str, Enum):
    """Types of relationships between knowledge nodes."""
    IS_A = "is_a"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    PRECEDES = "precedes"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    DERIVES_FROM = "derives_from"
    RELATES_TO = "relates_to"
    EXAMPLE_OF = "example_of"
    ALTERNATIVE_TO = "alternative_to"
    CAUSES = "causes"
    SOLVES = "solves"


# ── Data Structures ───────────────────────────────────────────────

@dataclass
class KnowledgeNode:
    """A single node in the knowledge fabric."""
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    content: str = ""
    summary: str = ""
    domain: KnowledgeDomain = KnowledgeDomain.CUSTOM
    knowledge_type: KnowledgeType = KnowledgeType.FACT
    status: KnowledgeStatus = KnowledgeStatus.DRAFT
    tags: list[str] = field(default_factory=list)
    source: str = ""                        # Where this knowledge came from
    source_url: str = ""
    confidence: float = 0.5                 # 0.0 - 1.0
    importance: float = 0.5                 # 0.0 - 1.0
    access_count: int = 0
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None    # Semantic embedding vector


@dataclass
class KnowledgeEdge:
    """A relationship between two knowledge nodes."""
    edge_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATES_TO
    weight: float = 0.5                     # 0.0 - 1.0
    confidence: float = 0.5
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    bidirectional: bool = False


@dataclass
class TopicCluster:
    """A self-organizing cluster of related knowledge nodes."""
    cluster_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    nodes: list[str] = field(default_factory=list)      # node_ids
    sub_clusters: list[str] = field(default_factory=list)  # cluster_ids
    centroid_embedding: list[float] | None = None
    coherence_score: float = 0.0
    size: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class KnowledgeQuery:
    """A query against the knowledge fabric."""
    query_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    text: str = ""
    domains: list[KnowledgeDomain] = field(default_factory=list)
    knowledge_types: list[KnowledgeType] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    max_results: int = 10
    min_confidence: float = 0.0
    include_related: bool = True
    semantic_search: bool = True
    sort_by: str = "relevance"              # "relevance", "recency", "importance"


@dataclass
class KnowledgeQueryResult:
    """Result of a knowledge fabric query."""
    query_id: str = ""
    nodes: list[KnowledgeNode] = field(default_factory=list)
    edges: list[KnowledgeEdge] = field(default_factory=list)
    clusters: list[TopicCluster] = field(default_factory=list)
    total_matches: int = 0
    query_time_ms: float = 0.0
    suggested_related: list[str] = field(default_factory=list)


# ── Knowledge Fabric ──────────────────────────────────────────────

class KnowledgeFabric:
    """AI-Native Knowledge Fabric that interconnects all knowledge.

    The fabric is a self-organizing, queryable intelligence layer that
    automatically links, clusters, and synthesizes knowledge from all
    sources across the platform.
    """

    def __init__(self):
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: dict[str, KnowledgeEdge] = {}
        self._clusters: dict[str, TopicCluster] = {}
        self._domain_index: dict[str, set[str]] = {}     # domain → node_ids
        self._tag_index: dict[str, set[str]] = {}         # tag → node_ids
        self._type_index: dict[str, set[str]] = {}        # knowledge_type → node_ids
        self._lock = asyncio.Lock()
        self._total_queries: int = 0

    # ── Node Management ───────────────────────────────────────

    def add_node(self, node: KnowledgeNode) -> str:
        """Add a knowledge node to the fabric."""
        self._nodes[node.node_id] = node

        # Update domain index
        domain_key = node.domain.value
        self._domain_index.setdefault(domain_key, set()).add(node.node_id)

        # Update tag index
        for tag in node.tags:
            self._tag_index.setdefault(tag, set()).add(node.node_id)

        # Update type index
        type_key = node.knowledge_type.value
        self._type_index.setdefault(type_key, set()).add(node.node_id)

        logger.debug(f"Knowledge node {node.node_id} added: {node.title[:50]}")
        return node.node_id

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Get a knowledge node by ID."""
        return self._nodes.get(node_id)

    def update_node(self, node_id: str, **kwargs) -> Optional[KnowledgeNode]:
        """Update a knowledge node's fields."""
        node = self._nodes.get(node_id)
        if not node:
            return None

        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)

        node.updated_at = datetime.now(timezone.utc).isoformat()
        node.version += 1
        return node

    def delete_node(self, node_id: str) -> bool:
        """Delete a knowledge node and its edges."""
        if node_id not in self._nodes:
            return False

        node = self._nodes.pop(node_id)

        # Remove from indexes
        domain_key = node.domain.value
        self._domain_index.get(domain_key, set()).discard(node_id)
        for tag in node.tags:
            self._tag_index.get(tag, set()).discard(node_id)
        type_key = node.knowledge_type.value
        self._type_index.get(type_key, set()).discard(node_id)

        # Remove edges
        to_remove = [
            eid for eid, edge in self._edges.items()
            if edge.source_id == node_id or edge.target_id == node_id
        ]
        for eid in to_remove:
            del self._edges[eid]

        return True

    # ── Edge Management ───────────────────────────────────────

    def add_edge(self, edge: KnowledgeEdge) -> str:
        """Add a relationship edge between two knowledge nodes."""
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            logger.warning(f"Cannot add edge: source or target node not found")
            return ""

        self._edges[edge.edge_id] = edge
        logger.debug(f"Knowledge edge {edge.edge_id} added: {edge.relation_type.value}")
        return edge.edge_id

    def get_edges_for_node(self, node_id: str) -> list[KnowledgeEdge]:
        """Get all edges connected to a node."""
        return [
            e for e in self._edges.values()
            if e.source_id == node_id or e.target_id == node_id
        ]

    def get_related_nodes(
        self,
        node_id: str,
        relation_types: list[RelationType] | None = None,
        max_depth: int = 2,
    ) -> list[KnowledgeNode]:
        """Get all nodes related to a given node."""
        visited: set[str] = {node_id}
        related: list[KnowledgeNode] = []

        current_ids = {node_id}
        for _ in range(max_depth):
            next_ids: set[str] = set()
            for cur_id in current_ids:
                for edge in self._edges.values():
                    if edge.source_id == cur_id and edge.target_id not in visited:
                        if relation_types is None or edge.relation_type in relation_types:
                            next_ids.add(edge.target_id)
                            target = self._nodes.get(edge.target_id)
                            if target:
                                related.append(target)
                    elif edge.target_id == cur_id and edge.source_id not in visited:
                        if relation_types is None or edge.relation_type in relation_types:
                            next_ids.add(edge.source_id)
                            source = self._nodes.get(edge.source_id)
                            if source:
                                related.append(source)

            visited.update(next_ids)
            current_ids = next_ids

        return related

    # ── Querying ──────────────────────────────────────────────

    def query(self, query: KnowledgeQuery) -> KnowledgeQueryResult:
        """Query the knowledge fabric for relevant knowledge."""
        start_time = time.time()

        matching_ids: set[str] = set()

        # Filter by domain
        if query.domains:
            for domain in query.domains:
                matching_ids.update(self._domain_index.get(domain.value, set()))
        else:
            matching_ids = set(self._nodes.keys())

        # Filter by knowledge type
        if query.knowledge_types:
            type_ids = set()
            for kt in query.knowledge_types:
                type_ids.update(self._type_index.get(kt.value, set()))
            matching_ids &= type_ids

        # Filter by tags
        if query.tags:
            tag_ids = set()
            for tag in query.tags:
                tag_ids.update(self._tag_index.get(tag, set()))
            matching_ids &= tag_ids

        # Filter by confidence
        if query.min_confidence > 0:
            matching_ids = {
                nid for nid in matching_ids
                if self._nodes[nid].confidence >= query.min_confidence
            }

        # Text search (keyword-based)
        if query.text:
            search_terms = query.text.lower().split()
            text_matches = set()
            for nid in matching_ids:
                node = self._nodes[nid]
                searchable = f"{node.title} {node.content} {node.summary} {' '.join(node.tags)}".lower()
                if all(term in searchable for term in search_terms):
                    text_matches.add(nid)
            matching_ids = text_matches

        # Sort and score results
        scored_nodes: list[tuple[KnowledgeNode, float]] = []
        for nid in matching_ids:
            node = self._nodes[nid]
            score = self._calculate_relevance_score(node, query)
            scored_nodes.append((node, score))

        # Sort
        if query.sort_by == "importance":
            scored_nodes.sort(key=lambda x: x[0].importance, reverse=True)
        elif query.sort_by == "recency":
            scored_nodes.sort(key=lambda x: x[0].updated_at, reverse=True)
        else:  # relevance
            scored_nodes.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        top_nodes = [n for n, _ in scored_nodes[:query.max_results]]

        # Get related nodes if requested
        edges: list[KnowledgeEdge] = []
        if query.include_related:
            for node in top_nodes:
                edges.extend(self.get_edges_for_node(node.node_id))

        query_time = (time.time() - start_time) * 1000
        self._total_queries += 1

        # Update access counts
        for node in top_nodes:
            node.access_count += 1

        return KnowledgeQueryResult(
            query_id=query.query_id,
            nodes=top_nodes,
            edges=edges[:50],  # Limit edges
            total_matches=len(matching_ids),
            query_time_ms=query_time,
        )

    def _calculate_relevance_score(self, node: KnowledgeNode, query: KnowledgeQuery) -> float:
        """Calculate relevance score for a node against a query."""
        score = 0.0

        if query.text:
            search_terms = query.text.lower().split()
            searchable = f"{node.title} {node.summary} {' '.join(node.tags)}".lower()

            # Title matches are most important
            title_lower = node.title.lower()
            for term in search_terms:
                if term in title_lower:
                    score += 3.0
                elif term in searchable:
                    score += 1.0

        # Confidence boost
        score += node.confidence * 0.5

        # Importance boost
        score += node.importance * 0.3

        # Recency boost
        try:
            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(node.updated_at)).days
            score += max(0, 1.0 - age_days / 30) * 0.2
        except Exception:
            pass

        return score

    # ── Cluster Management ────────────────────────────────────

    def create_cluster(
        self,
        name: str,
        description: str = "",
        node_ids: list[str] | None = None,
    ) -> TopicCluster:
        """Create a new topic cluster."""
        cluster = TopicCluster(
            name=name,
            description=description,
            nodes=node_ids or [],
            size=len(node_ids) if node_ids else 0,
        )
        self._clusters[cluster.cluster_id] = cluster
        return cluster

    def add_to_cluster(self, cluster_id: str, node_id: str):
        """Add a node to a cluster."""
        cluster = self._clusters.get(cluster_id)
        if cluster and node_id not in cluster.nodes:
            cluster.nodes.append(node_id)
            cluster.size = len(cluster.nodes)
            cluster.updated_at = datetime.now(timezone.utc).isoformat()

    def get_cluster(self, cluster_id: str) -> Optional[TopicCluster]:
        """Get a topic cluster by ID."""
        return self._clusters.get(cluster_id)

    def list_clusters(self) -> list[TopicCluster]:
        """List all topic clusters."""
        return list(self._clusters.values())

    # ── Knowledge Synthesis ───────────────────────────────────

    def synthesize(
        self,
        query_text: str,
        max_sources: int = 5,
    ) -> dict[str, Any]:
        """Synthesize knowledge from multiple sources into a coherent summary."""
        query_obj = KnowledgeQuery(
            text=query_text,
            max_results=max_sources,
            sort_by="relevance",
        )
        result = self.query(query_obj)

        if not result.nodes:
            return {"summary": "No relevant knowledge found.", "sources": []}

        # Build synthesis from top nodes
        synthesis_parts = []
        sources = []

        for node in result.nodes:
            synthesis_parts.append(f"From {node.title}: {node.summary or node.content[:200]}")
            sources.append({
                "node_id": node.node_id,
                "title": node.title,
                "domain": node.domain.value,
                "confidence": node.confidence,
                "source": node.source,
            })

        return {
            "summary": " | ".join(synthesis_parts),
            "sources": sources,
            "total_sources_found": result.total_matches,
            "query_time_ms": result.query_time_ms,
        }

    # ── Auto-Linking ──────────────────────────────────────────

    def auto_link_nodes(self, similarity_threshold: float = 0.3) -> int:
        """Automatically discover and create edges between related nodes."""
        new_edges = 0
        node_ids = list(self._nodes.keys())

        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                node_a = self._nodes[node_ids[i]]
                node_b = self._nodes[node_ids[j]]

                # Skip if same domain
                if node_a.domain == node_b.domain:
                    # Check for tag overlap
                    shared_tags = set(node_a.tags) & set(node_b.tags)
                    if len(shared_tags) >= 2:
                        edge = KnowledgeEdge(
                            source_id=node_a.node_id,
                            target_id=node_b.node_id,
                            relation_type=RelationType.RELATES_TO,
                            weight=min(len(shared_tags) * 0.3, 1.0),
                            description=f"Shared tags: {', '.join(shared_tags)}",
                        )
                        self._edges[edge.edge_id] = edge
                        new_edges += 1

                # Check for content overlap via keyword matching
                content_words_a = set(node_a.content.lower().split()[:50])
                content_words_b = set(node_b.content.lower().split()[:50])
                overlap = content_words_a & content_words_b
                overlap_ratio = len(overlap) / max(len(content_words_a | content_words_b), 1)

                if overlap_ratio > similarity_threshold and node_a.domain != node_b.domain:
                    # Cross-domain relationship
                    edge = KnowledgeEdge(
                        source_id=node_a.node_id,
                        target_id=node_b.node_id,
                        relation_type=RelationType.RELATES_TO,
                        weight=overlap_ratio,
                        description=f"Cross-domain content overlap: {overlap_ratio:.2f}",
                    )
                    self._edges[edge.edge_id] = edge
                    new_edges += 1

        logger.info(f"Auto-linked {new_edges} new edges in knowledge fabric")
        return new_edges

    # ── Import/Export ─────────────────────────────────────────

    def export_fabric(self) -> dict[str, Any]:
        """Export the entire knowledge fabric."""
        return {
            "nodes": {
                nid: {
                    "node_id": n.node_id,
                    "title": n.title,
                    "content": n.content[:500],
                    "summary": n.summary,
                    "domain": n.domain.value,
                    "knowledge_type": n.knowledge_type.value,
                    "status": n.status.value,
                    "tags": n.tags,
                    "source": n.source,
                    "confidence": n.confidence,
                    "importance": n.importance,
                    "version": n.version,
                    "created_at": n.created_at,
                    "updated_at": n.updated_at,
                }
                for nid, n in self._nodes.items()
            },
            "edges": [
                {
                    "edge_id": e.edge_id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation_type": e.relation_type.value,
                    "weight": e.weight,
                    "description": e.description,
                }
                for e in self._edges.values()
            ],
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "name": c.name,
                    "description": c.description,
                    "nodes": c.nodes,
                    "size": c.size,
                }
                for c in self._clusters.values()
            ],
        }

    # ── Statistics ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get knowledge fabric statistics."""
        domain_counts = {}
        for domain_key, node_ids in self._domain_index.items():
            domain_counts[domain_key] = len(node_ids)

        type_counts = {}
        for type_key, node_ids in self._type_index.items():
            type_counts[type_key] = len(node_ids)

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "total_clusters": len(self._clusters),
            "total_queries": self._total_queries,
            "nodes_by_domain": domain_counts,
            "nodes_by_type": type_counts,
            "total_tags": len(self._tag_index),
            "avg_confidence": (
                sum(n.confidence for n in self._nodes.values()) / max(len(self._nodes), 1)
            ),
        }


# Global instance
knowledge_fabric = KnowledgeFabric()