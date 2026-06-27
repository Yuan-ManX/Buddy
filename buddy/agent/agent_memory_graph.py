"""
Buddy Contextual Memory Graph - Graph-based semantic memory with rich connections.

A graph-based memory system that connects related memories through semantic
relationships, supports multi-hop retrieval, and builds rich knowledge graphs
that evolve with every interaction. Goes beyond simple key-value storage to
create a living, interconnected memory fabric.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EdgeType(str, Enum):
    """Types of relationships between memory nodes."""
    RELATED_TO = "related_to"
    CAUSES = "causes"
    PRECEDES = "precedes"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    EXTENDS = "extends"
    EXEMPLIFIES = "exemplifies"
    SUMMARIZES = "summarizes"
    REFERENCES = "references"
    DERIVED_FROM = "derived_from"


class NodeCategory(str, Enum):
    """Categories of memory nodes."""
    FACT = "fact"
    CONCEPT = "concept"
    EVENT = "event"
    PERSON = "person"
    PLACE = "place"
    PROCEDURE = "procedure"
    OPINION = "opinion"
    GOAL = "goal"
    DECISION = "decision"
    LEARNING = "learning"


class RetrievalStrategy(str, Enum):
    """Strategies for retrieving from the memory graph."""
    DIRECT = "direct"               # Direct node lookup
    BFS = "breadth_first"           # Breadth-first traversal
    DFS = "depth_first"             # Depth-first traversal
    SEMANTIC = "semantic"           # Semantic similarity search
    MULTI_HOP = "multi_hop"         # Multi-hop traversal
    SUBGRAPH = "subgraph"           # Extract subgraph around node


@dataclass
class MemoryNode:
    """A single node in the contextual memory graph."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    category: NodeCategory = NodeCategory.FACT
    importance: float = 0.5
    confidence: float = 0.5
    access_count: int = 0
    last_accessed: float = 0.0
    tags: list[str] = field(default_factory=list)
    embedding_hint: str = ""  # Semantic hint for similarity search
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class MemoryEdge:
    """A directed edge between two memory nodes."""
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = ""
    target_id: str = ""
    edge_type: EdgeType = EdgeType.RELATED_TO
    weight: float = 0.5
    description: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class MemorySubgraph:
    """A subgraph extracted from the memory graph."""
    subgraph_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    center_node_id: str = ""
    nodes: list[MemoryNode] = field(default_factory=list)
    edges: list[MemoryEdge] = field(default_factory=list)
    depth: int = 1
    extracted_at: float = field(default_factory=time.time)


@dataclass
class RetrievalResult:
    """Result of a memory graph retrieval operation."""
    query: str = ""
    nodes: list[MemoryNode] = field(default_factory=list)
    edges: list[MemoryEdge] = field(default_factory=list)
    strategy: RetrievalStrategy = RetrievalStrategy.DIRECT
    relevance_scores: dict[str, float] = field(default_factory=dict)
    traversal_path: list[str] = field(default_factory=list)
    retrieved_at: float = field(default_factory=time.time)


class ContextualMemoryGraph:
    """Graph-based semantic memory with rich interconnected relationships.

    Stores memories as nodes in a graph connected by typed edges. Supports
    multiple retrieval strategies including multi-hop traversal, semantic
    search, and subgraph extraction. The graph evolves with every interaction,
    strengthening frequently accessed connections and pruning weak ones.
    """

    # Graph parameters
    MAX_HOPS: int = 5
    PRUNE_THRESHOLD: float = 0.1

    def __init__(self) -> None:
        self._nodes: dict[str, MemoryNode] = {}
        self._edges: dict[str, MemoryEdge] = {}
        self._adjacency: dict[str, list[str]] = defaultdict(list)  # source -> [edge_ids]
        self._total_nodes: int = 0
        self._total_edges: int = 0
        self._total_retrievals: int = 0

    # ── Node Operations ──────────────────────────────────────────

    def add_node(
        self,
        content: str,
        category: NodeCategory = NodeCategory.FACT,
        importance: float = 0.5,
        confidence: float = 0.5,
        tags: list[str] | None = None,
        embedding_hint: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryNode:
        """Add a new node to the memory graph.

        Args:
            content: The memory content.
            category: Node category.
            importance: Importance score (0.0-1.0).
            confidence: Confidence in the memory (0.0-1.0).
            tags: Categorization tags.
            embedding_hint: Semantic hint for search.
            metadata: Additional metadata.

        Returns:
            The created MemoryNode.
        """
        node = MemoryNode(
            content=content,
            category=category,
            importance=importance,
            confidence=confidence,
            tags=tags or [],
            embedding_hint=embedding_hint or content[:100],
            metadata=metadata or {},
        )
        self._nodes[node.node_id] = node
        self._total_nodes += 1
        return node

    def update_node(
        self,
        node_id: str,
        content: str | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        tags: list[str] | None = None,
    ) -> MemoryNode | None:
        """Update an existing node's properties.

        Args:
            node_id: The node ID to update.
            content: New content.
            importance: New importance score.
            confidence: New confidence.
            tags: New tags.

        Returns:
            The updated MemoryNode or None.
        """
        node = self._nodes.get(node_id)
        if not node:
            return None
        if content is not None:
            node.content = content
        if importance is not None:
            node.importance = importance
        if confidence is not None:
            node.confidence = confidence
        if tags is not None:
            node.tags = tags
        node.updated_at = time.time()
        return node

    def access_node(self, node_id: str) -> MemoryNode | None:
        """Record access to a node, incrementing its access count.

        Args:
            node_id: The node ID being accessed.

        Returns:
            The accessed MemoryNode or None.
        """
        node = self._nodes.get(node_id)
        if node:
            node.access_count += 1
            node.last_accessed = time.time()
        return node

    def get_node(self, node_id: str) -> MemoryNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its connected edges.

        Args:
            node_id: The node ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        if node_id not in self._nodes:
            return False

        # Remove all connected edges
        edges_to_remove = []
        for edge_id, edge in self._edges.items():
            if edge.source_id == node_id or edge.target_id == node_id:
                edges_to_remove.append(edge_id)

        for edge_id in edges_to_remove:
            del self._edges[edge_id]
            self._total_edges -= 1

        # Remove from adjacency
        if node_id in self._adjacency:
            del self._adjacency[node_id]

        del self._nodes[node_id]
        self._total_nodes -= 1
        return True

    # ── Edge Operations ──────────────────────────────────────────

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.RELATED_TO,
        weight: float = 0.5,
        description: str = "",
    ) -> MemoryEdge | None:
        """Add a directed edge between two nodes.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            edge_type: Type of relationship.
            weight: Edge weight (0.0-1.0).
            description: Description of the relationship.

        Returns:
            The created MemoryEdge or None if nodes don't exist.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        edge = MemoryEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            description=description,
        )
        self._edges[edge.edge_id] = edge
        self._adjacency[source_id].append(edge.edge_id)
        self._total_edges += 1
        return edge

    def get_neighbors(
        self, node_id: str, edge_type: EdgeType | None = None
    ) -> list[tuple[MemoryNode, MemoryEdge]]:
        """Get all neighbors of a node.

        Args:
            node_id: The node ID.
            edge_type: Optional filter by edge type.

        Returns:
            List of (neighbor_node, connecting_edge) tuples.
        """
        neighbors: list[tuple[MemoryNode, MemoryEdge]] = []
        edge_ids = self._adjacency.get(node_id, [])

        for edge_id in edge_ids:
            edge = self._edges.get(edge_id)
            if not edge:
                continue
            if edge_type and edge.edge_type != edge_type:
                continue
            target = self._nodes.get(edge.target_id)
            if target:
                neighbors.append((target, edge))

        return neighbors

    # ── Retrieval Operations ─────────────────────────────────────

    def retrieve(
        self,
        query: str = "",
        strategy: RetrievalStrategy = RetrievalStrategy.SEMANTIC,
        start_node_id: str | None = None,
        max_hops: int | None = None,
        category: NodeCategory | None = None,
        tags: list[str] | None = None,
        min_importance: float = 0.0,
        limit: int = 20,
    ) -> RetrievalResult:
        """Retrieve nodes from the memory graph.

        Args:
            query: Search query for semantic retrieval.
            strategy: Retrieval strategy to use.
            start_node_id: Starting node for traversal strategies.
            max_hops: Maximum traversal hops.
            category: Filter by node category.
            tags: Filter by tags.
            min_importance: Minimum importance threshold.
            limit: Maximum results.

        Returns:
            A RetrievalResult with matching nodes and edges.
        """
        max_hops = max_hops or self.MAX_HOPS
        nodes: list[MemoryNode] = []
        edges: list[MemoryEdge] = []
        traversal_path: list[str] = []
        relevance_scores: dict[str, float] = {}

        if strategy == RetrievalStrategy.DIRECT and start_node_id:
            node = self._nodes.get(start_node_id)
            if node:
                self.access_node(start_node_id)
                nodes = [node]
                traversal_path = [start_node_id]
                relevance_scores[start_node_id] = 1.0

        elif strategy == RetrievalStrategy.BFS:
            nodes, edges, traversal_path = self._bfs_retrieve(
                start_node_id, max_hops, category, tags, min_importance, limit
            )

        elif strategy == RetrievalStrategy.DFS:
            nodes, edges, traversal_path = self._dfs_retrieve(
                start_node_id, max_hops, category, tags, min_importance, limit
            )

        elif strategy == RetrievalStrategy.SEMANTIC:
            nodes = self._semantic_retrieve(
                query, category, tags, min_importance, limit
            )
            relevance_scores = {n.node_id: self._compute_similarity(query, n) for n in nodes}

        elif strategy == RetrievalStrategy.MULTI_HOP:
            nodes, edges, traversal_path = self._multi_hop_retrieve(
                start_node_id, query, max_hops, limit
            )

        elif strategy == RetrievalStrategy.SUBGRAPH:
            nodes, edges = self._subgraph_retrieve(
                start_node_id, max_hops, limit
            )

        self._total_retrievals += 1

        return RetrievalResult(
            query=query,
            nodes=nodes,
            edges=edges,
            strategy=strategy,
            relevance_scores=relevance_scores,
            traversal_path=traversal_path,
        )

    def _bfs_retrieve(
        self,
        start_node_id: str | None,
        max_hops: int,
        category: NodeCategory | None,
        tags: list[str] | None,
        min_importance: float,
        limit: int,
    ) -> tuple[list[MemoryNode], list[MemoryEdge], list[str]]:
        """Breadth-first traversal retrieval."""
        if not start_node_id or start_node_id not in self._nodes:
            return [], [], []

        visited: set[str] = {start_node_id}
        nodes: list[MemoryNode] = [self._nodes[start_node_id]]
        edges: list[MemoryEdge] = []
        traversal: list[str] = [start_node_id]
        queue: list[tuple[str, int]] = [(start_node_id, 0)]

        while queue and len(nodes) < limit:
            current_id, depth = queue.pop(0)
            if depth >= max_hops:
                continue

            for edge_id in self._adjacency.get(current_id, []):
                edge = self._edges.get(edge_id)
                if not edge or edge.target_id in visited:
                    continue

                target = self._nodes.get(edge.target_id)
                if not target:
                    continue

                # Apply filters
                if category and target.category != category:
                    continue
                if tags and not any(t in target.tags for t in tags):
                    continue
                if target.importance < min_importance:
                    continue

                visited.add(edge.target_id)
                self.access_node(edge.target_id)
                nodes.append(target)
                edges.append(edge)
                traversal.append(edge.target_id)
                queue.append((edge.target_id, depth + 1))

        return nodes, edges, traversal

    def _dfs_retrieve(
        self,
        start_node_id: str | None,
        max_hops: int,
        category: NodeCategory | None,
        tags: list[str] | None,
        min_importance: float,
        limit: int,
    ) -> tuple[list[MemoryNode], list[MemoryEdge], list[str]]:
        """Depth-first traversal retrieval."""
        if not start_node_id or start_node_id not in self._nodes:
            return [], [], []

        visited: set[str] = {start_node_id}
        nodes: list[MemoryNode] = [self._nodes[start_node_id]]
        edges: list[MemoryEdge] = []
        traversal: list[str] = [start_node_id]

        def dfs(current_id: str, depth: int) -> None:
            if depth >= max_hops or len(nodes) >= limit:
                return
            for edge_id in self._adjacency.get(current_id, []):
                if len(nodes) >= limit:
                    return
                edge = self._edges.get(edge_id)
                if not edge or edge.target_id in visited:
                    continue
                target = self._nodes.get(edge.target_id)
                if not target:
                    continue
                if category and target.category != category:
                    continue
                if tags and not any(t in target.tags for t in tags):
                    continue
                if target.importance < min_importance:
                    continue
                visited.add(edge.target_id)
                self.access_node(edge.target_id)
                nodes.append(target)
                edges.append(edge)
                traversal.append(edge.target_id)
                dfs(edge.target_id, depth + 1)

        dfs(start_node_id, 0)
        return nodes, edges, traversal

    def _semantic_retrieve(
        self,
        query: str,
        category: NodeCategory | None,
        tags: list[str] | None,
        min_importance: float,
        limit: int,
    ) -> list[MemoryNode]:
        """Semantic similarity-based retrieval."""
        if not query:
            return list(self._nodes.values())[:limit]

        scored: list[tuple[MemoryNode, float]] = []
        for node in self._nodes.values():
            if category and node.category != category:
                continue
            if tags and not any(t in node.tags for t in tags):
                continue
            if node.importance < min_importance:
                continue
            score = self._compute_similarity(query, node)
            scored.append((node, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in scored[:limit]]

    def _multi_hop_retrieve(
        self,
        start_node_id: str | None,
        query: str,
        max_hops: int,
        limit: int,
    ) -> tuple[list[MemoryNode], list[MemoryEdge], list[str]]:
        """Multi-hop retrieval combining traversal and semantic search."""
        # First, do BFS from start node
        bf_nodes, bf_edges, traversal = self._bfs_retrieve(
            start_node_id, max_hops, None, None, 0.0, limit * 2
        )

        # Then, semantically re-rank based on query
        if query:
            scored = [(n, self._compute_similarity(query, n)) for n in bf_nodes]
            scored.sort(key=lambda x: x[1], reverse=True)
            bf_nodes = [n for n, _ in scored[:limit]]

        return bf_nodes, bf_edges, traversal

    def _subgraph_retrieve(
        self,
        start_node_id: str | None,
        max_hops: int,
        limit: int,
    ) -> tuple[list[MemoryNode], list[MemoryEdge]]:
        """Extract a subgraph around a center node."""
        nodes, edges, _ = self._bfs_retrieve(
            start_node_id, max_hops, None, None, 0.0, limit
        )

        # Also include reverse edges (incoming to any node in subgraph)
        node_ids = {n.node_id for n in nodes}
        for edge in self._edges.values():
            if edge.target_id in node_ids and edge.source_id in node_ids:
                if edge not in edges:
                    edges.append(edge)

        return nodes, edges

    def _compute_similarity(self, query: str, node: MemoryNode) -> float:
        """Compute semantic similarity between query and node."""
        query_lower = query.lower()
        content_lower = node.content.lower()
        hint_lower = node.embedding_hint.lower()

        # Simple word overlap similarity
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        hint_words = set(hint_lower.split())

        if not query_words:
            return 0.0

        content_overlap = len(query_words & content_words) / len(query_words | content_words) if content_words else 0.0
        hint_overlap = len(query_words & hint_words) / len(query_words | hint_words) if hint_words else 0.0

        # Direct substring match bonus
        substring_bonus = 0.3 if query_lower in content_lower else 0.0

        # Tag match bonus
        tag_bonus = 0.2 if any(q in tag.lower() for tag in node.tags for q in query_words) else 0.0

        # Weighted combination
        score = 0.4 * content_overlap + 0.2 * hint_overlap + substring_bonus + tag_bonus
        return min(1.0, score * node.importance)

    # ── Graph Analysis ───────────────────────────────────────────

    def get_subgraph(
        self, center_node_id: str, depth: int = 2
    ) -> MemorySubgraph | None:
        """Extract a subgraph centered on a node.

        Args:
            center_node_id: The center node ID.
            depth: How many hops out to include.

        Returns:
            A MemorySubgraph or None if center not found.
        """
        if center_node_id not in self._nodes:
            return None

        nodes, edges = self._subgraph_retrieve(center_node_id, depth, 100)
        return MemorySubgraph(
            center_node_id=center_node_id,
            nodes=nodes,
            edges=edges,
            depth=depth,
        )

    def find_path(
        self, source_id: str, target_id: str, max_hops: int = 5
    ) -> list[str] | None:
        """Find the shortest path between two nodes.

        Args:
            source_id: Starting node.
            target_id: Target node.
            max_hops: Maximum hops to search.

        Returns:
            List of node IDs in the path, or None if no path found.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        if source_id == target_id:
            return [source_id]

        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current_id, path = queue.pop(0)
            if len(path) > max_hops + 1:
                continue

            for edge_id in self._adjacency.get(current_id, []):
                edge = self._edges.get(edge_id)
                if not edge:
                    continue
                if edge.target_id == target_id:
                    return path + [target_id]
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, path + [edge.target_id]))

        return None

    def get_central_nodes(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most central nodes by connectivity.

        Args:
            limit: Maximum results.

        Returns:
            List of node info sorted by connectivity.
        """
        connectivity: dict[str, int] = defaultdict(int)
        for edge in self._edges.values():
            connectivity[edge.source_id] += 1
            connectivity[edge.target_id] += 1

        ranked = sorted(connectivity.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "node_id": nid,
                "content": (self._nodes[nid].content[:100] if nid in self._nodes else ""),
                "connections": count,
                "importance": self._nodes[nid].importance if nid in self._nodes else 0.0,
            }
            for nid, count in ranked[:limit]
        ]

    def prune_weak_connections(self) -> int:
        """Remove weak edges and low-importance nodes.

        Returns:
            Number of elements pruned.
        """
        pruned = 0

        # Prune weak edges
        edges_to_remove = []
        for edge_id, edge in self._edges.items():
            if edge.weight < self.PRUNE_THRESHOLD:
                edges_to_remove.append(edge_id)

        for edge_id in edges_to_remove:
            edge = self._edges.pop(edge_id, None)
            if edge and edge.source_id in self._adjacency:
                self._adjacency[edge.source_id] = [
                    e for e in self._adjacency[edge.source_id] if e != edge_id
                ]
            pruned += 1

        # Prune isolated low-importance nodes
        connected = set()
        for edge in self._edges.values():
            connected.add(edge.source_id)
            connected.add(edge.target_id)

        nodes_to_remove = []
        for node_id, node in self._nodes.items():
            if node_id not in connected and node.importance < self.PRUNE_THRESHOLD:
                nodes_to_remove.append(node_id)

        for node_id in nodes_to_remove:
            del self._nodes[node_id]
            pruned += 1

        self._total_edges -= len(edges_to_remove)
        self._total_nodes -= len(nodes_to_remove)
        return pruned

    # ── Query & Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get memory graph statistics."""
        categories = defaultdict(int)
        for node in self._nodes.values():
            categories[node.category.value] += 1

        edge_types = defaultdict(int)
        for edge in self._edges.values():
            edge_types[edge.edge_type.value] += 1

        return {
            "total_nodes": self._total_nodes,
            "total_edges": self._total_edges,
            "total_retrievals": self._total_retrievals,
            "categories": dict(categories),
            "edge_types": dict(edge_types),
            "avg_importance": round(
                sum(n.importance for n in self._nodes.values()) / len(self._nodes), 3
            ) if self._nodes else 0.0,
            "avg_confidence": round(
                sum(n.confidence for n in self._nodes.values()) / len(self._nodes), 3
            ) if self._nodes else 0.0,
            "graph_density": round(
                self._total_edges / (self._total_nodes * (self._total_nodes - 1)), 4
            ) if self._total_nodes > 1 else 0.0,
        }

    def reset(self) -> None:
        """Reset the memory graph to initial state."""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._total_nodes = 0
        self._total_edges = 0
        self._total_retrievals = 0


# ── Singleton Access ───────────────────────────────────────────────

_memory_graph: ContextualMemoryGraph | None = None


def get_memory_graph() -> ContextualMemoryGraph:
    """Get or create the singleton memory graph instance."""
    global _memory_graph
    if _memory_graph is None:
        _memory_graph = ContextualMemoryGraph()
    return _memory_graph


def reset_memory_graph() -> None:
    """Reset the singleton memory graph."""
    global _memory_graph
    if _memory_graph:
        _memory_graph.reset()
    _memory_graph = None