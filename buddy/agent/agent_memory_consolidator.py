"""
Buddy Memory Consolidator - Hierarchical Memory Compression and Organization.

Compresses episodic memories into semantic knowledge, consolidates procedural
patterns, manages memory decay, and maintains long-term knowledge coherence.
Part of the AI-Native Buddy Agent system.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import logging

logger = logging.getLogger("buddy.memory_consolidator")


class ConsolidationStrategy(str, Enum):
    """Strategies for memory consolidation."""
    SUMMARIZE = "summarize"       # Compress multiple entries into one summary
    ABSTRACT = "abstract"         # Extract abstract concepts
    CLUSTER = "cluster"           # Group similar memories
    PRUNE = "prune"               # Remove low-importance memories
    REINFORCE = "reinforce"       # Strengthen frequently accessed memories
    FORGET = "forget"             # Decay old, unused memories


class MemoryImportance(str, Enum):
    """Importance levels for memory entries."""
    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    PINNED = "pinned"  # Never decays


@dataclass
class MemoryEntry:
    """A single memory entry."""
    entry_id: str
    content: str
    layer: str  # episodic, semantic, procedural
    importance: MemoryImportance = MemoryImportance.MEDIUM
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    decay_rate: float = 0.01  # Rate of importance decay per day
    tags: list[str] = field(default_factory=list)
    embeddings: list[float] | None = None
    source_entries: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsolidatedMemory:
    """A consolidated (compressed) memory."""
    memory_id: str
    summary: str
    concepts: list[str]
    source_count: int
    consolidation_strategy: ConsolidationStrategy
    importance: MemoryImportance
    created_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryConsolidator:
    """Hierarchical memory consolidation engine.

    Manages the full memory lifecycle:
    1. Collect episodic memories
    2. Extract semantic concepts
    3. Consolidate into procedural knowledge
    4. Prune and decay low-importance memories
    5. Reinforce high-value memories
    """

    MAX_EPISODIC = 1000
    MAX_SEMANTIC = 500
    MAX_PROCEDURAL = 200
    CONSOLIDATION_THRESHOLD = 50  # Number of episodic entries before consolidation
    DECAY_CHECK_INTERVAL = 3600  # Check decay every hour

    def __init__(self) -> None:
        self._episodic: list[MemoryEntry] = []
        self._semantic: list[MemoryEntry] = []
        self._procedural: list[MemoryEntry] = []
        self._consolidated: list[ConsolidatedMemory] = []
        self._concept_index: dict[str, list[str]] = defaultdict(list)  # concept -> entry_ids
        self._total_consolidations: int = 0
        self._last_decay_check: float = time.time()

    # ── Public API ────────────────────────────────────────────────

    def store_episodic(
        self,
        content: str,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a new episodic memory."""
        entry = MemoryEntry(
            entry_id=f"mem-{uuid.uuid4().hex[:8]}",
            content=content,
            layer="episodic",
            importance=importance,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._episodic.append(entry)

        # Index concepts
        for tag in entry.tags:
            self._concept_index[tag].append(entry.entry_id)

        # Trim if over capacity
        if len(self._episodic) > self.MAX_EPISODIC:
            self._prune_episodic()

        # Auto-consolidate if threshold reached
        if len(self._episodic) % self.CONSOLIDATION_THRESHOLD == 0:
            self.consolidate(ConsolidationStrategy.SUMMARIZE)

        return entry

    def store_semantic(
        self,
        content: str,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        tags: list[str] | None = None,
        source_entries: list[str] | None = None,
    ) -> MemoryEntry:
        """Store a semantic memory (extracted concept)."""
        entry = MemoryEntry(
            entry_id=f"sem-{uuid.uuid4().hex[:8]}",
            content=content,
            layer="semantic",
            importance=importance,
            tags=tags or [],
            source_entries=source_entries or [],
        )
        self._semantic.append(entry)

        for tag in entry.tags:
            self._concept_index[tag].append(entry.entry_id)

        if len(self._semantic) > self.MAX_SEMANTIC:
            self._prune_semantic()

        return entry

    def store_procedural(
        self,
        content: str,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """Store a procedural memory (learned pattern)."""
        entry = MemoryEntry(
            entry_id=f"proc-{uuid.uuid4().hex[:8]}",
            content=content,
            layer="procedural",
            importance=importance,
            tags=tags or [],
        )
        self._procedural.append(entry)

        if len(self._procedural) > self.MAX_PROCEDURAL:
            self._prune_procedural()

        return entry

    def consolidate(
        self,
        strategy: ConsolidationStrategy = ConsolidationStrategy.SUMMARIZE,
        target_layer: str = "episodic",
        limit: int = 50,
    ) -> list[ConsolidatedMemory]:
        """Consolidate memories using the specified strategy."""
        entries = self._get_entries_by_layer(target_layer)
        if not entries:
            return []

        if strategy == ConsolidationStrategy.SUMMARIZE:
            return self._consolidate_summarize(entries, limit)
        elif strategy == ConsolidationStrategy.ABSTRACT:
            return self._consolidate_abstract(entries, limit)
        elif strategy == ConsolidationStrategy.CLUSTER:
            return self._consolidate_cluster(entries, limit)
        elif strategy == ConsolidationStrategy.PRUNE:
            self._consolidate_prune(entries)
            return []
        elif strategy == ConsolidationStrategy.REINFORCE:
            return self._consolidate_reinforce(entries, limit)
        elif strategy == ConsolidationStrategy.FORGET:
            self._consolidate_forget(entries)
            return []

        return []

    def access(self, entry_id: str) -> MemoryEntry | None:
        """Access a memory entry, updating access count."""
        for layer in [self._episodic, self._semantic, self._procedural]:
            for entry in layer:
                if entry.entry_id == entry_id:
                    entry.access_count += 1
                    entry.last_accessed = time.time()
                    # Reinforce: slow decay for frequently accessed
                    entry.decay_rate = max(0.001, entry.decay_rate * 0.9)
                    return entry
        return None

    def search(
        self,
        query: str,
        layer: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search memories by content and tags."""
        results: list[tuple[MemoryEntry, float]] = []

        entries = self._get_entries_by_layer(layer) if layer else (
            self._episodic + self._semantic + self._procedural
        )

        for entry in entries:
            score = 0.0

            # Content match
            query_lower = query.lower()
            if query_lower in entry.content.lower():
                score += 0.5 + (len(query_lower) / len(entry.content) if entry.content else 0)

            # Tag match
            if tags:
                matches = sum(1 for t in tags if t in entry.tags)
                if matches > 0:
                    score += 0.3 * matches

            # Importance boost
            importance_weights = {
                "pinned": 0.5, "critical": 0.4, "high": 0.3,
                "medium": 0.2, "low": 0.1, "trivial": 0.0,
            }
            score += importance_weights.get(entry.importance.value, 0.0)

            # Recency boost
            hours_ago = (time.time() - entry.last_accessed) / 3600
            score += max(0.0, 0.2 - hours_ago * 0.01)

            if score > 0:
                results.append((entry, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in results[:limit]]

    def get_concept_map(self) -> dict[str, list[str]]:
        """Get the concept-to-entry mapping."""
        return dict(self._concept_index)

    def get_stats(self) -> dict[str, Any]:
        return {
            "episodic_count": len(self._episodic),
            "semantic_count": len(self._semantic),
            "procedural_count": len(self._procedural),
            "consolidated_count": len(self._consolidated),
            "total_consolidations": self._total_consolidations,
            "total_concepts": len(self._concept_index),
            "episodic_capacity": f"{len(self._episodic)}/{self.MAX_EPISODIC}",
            "semantic_capacity": f"{len(self._semantic)}/{self.MAX_SEMANTIC}",
            "procedural_capacity": f"{len(self._procedural)}/{self.MAX_PROCEDURAL}",
            "needs_consolidation": len(self._episodic) >= self.CONSOLIDATION_THRESHOLD,
            "last_decay_check": self._last_decay_check,
        }

    def check_decay(self) -> dict[str, int]:
        """Apply memory decay. Returns counts of pruned entries."""
        self._last_decay_check = time.time()
        pruned = {"episodic": 0, "semantic": 0, "procedural": 0}

        for layer_name, layer in [
            ("episodic", self._episodic),
            ("semantic", self._semantic),
            ("procedural", self._procedural),
        ]:
            now = time.time()
            keep = []
            for entry in layer:
                if entry.importance == MemoryImportance.PINNED:
                    keep.append(entry)
                    continue

                days_since_access = (now - entry.last_accessed) / 86400
                decay = entry.decay_rate * days_since_access

                importance_values = {
                    "critical": 5, "high": 4, "medium": 3, "low": 2, "trivial": 1,
                }
                base = importance_values.get(entry.importance.value, 3)
                adjusted = base - decay

                if adjusted <= 0:
                    pruned[layer_name] += 1
                else:
                    # Degrade importance if decayed significantly
                    if adjusted <= 1:
                        entry.importance = MemoryImportance.TRIVIAL
                    elif adjusted <= 2:
                        entry.importance = MemoryImportance.LOW
                    keep.append(entry)

            if layer_name == "episodic":
                self._episodic = keep
            elif layer_name == "semantic":
                self._semantic = keep
            else:
                self._procedural = keep

        total_pruned = sum(pruned.values())
        if total_pruned > 0:
            logger.info(f"Memory decay: pruned {total_pruned} entries ({pruned})")

        return pruned

    # ── Consolidation Strategies ─────────────────────────────────

    def _consolidate_summarize(
        self, entries: list[MemoryEntry], limit: int
    ) -> list[ConsolidatedMemory]:
        """Summarize: compress similar entries into a single summary."""
        if len(entries) < 2:
            return []

        # Group by tags
        groups: dict[str, list[MemoryEntry]] = defaultdict(list)
        for entry in entries:
            key = ",".join(sorted(entry.tags)) if entry.tags else "untagged"
            groups[key].append(entry)

        consolidated: list[ConsolidatedMemory] = []
        for tag_key, group in groups.items():
            if len(group) < 2:
                continue

            # Create summary from group
            contents = [e.content for e in group]
            summary = self._generate_summary(contents)
            concepts = list(set(tag for e in group for tag in e.tags))
            max_importance = max(group, key=lambda e: {
                "pinned": 6, "critical": 5, "high": 4, "medium": 3, "low": 2, "trivial": 1,
            }.get(e.importance.value, 3)).importance

            cm = ConsolidatedMemory(
                memory_id=f"cons-{uuid.uuid4().hex[:8]}",
                summary=summary,
                concepts=concepts,
                source_count=len(group),
                consolidation_strategy=ConsolidationStrategy.SUMMARIZE,
                importance=max_importance,
                tags=list(set(t for e in group for t in e.tags)),
                metadata={"source_ids": [e.entry_id for e in group]},
            )
            consolidated.append(cm)

            # Remove original entries (they're now consolidated)
            for e in group:
                if e in self._episodic:
                    self._episodic.remove(e)
                elif e in self._semantic:
                    self._semantic.remove(e)

        self._consolidated.extend(consolidated)
        self._total_consolidations += len(consolidated)

        logger.info(f"Summarized {len(entries)} entries into {len(consolidated)} consolidated memories")
        return consolidated

    def _consolidate_abstract(
        self, entries: list[MemoryEntry], limit: int
    ) -> list[ConsolidatedMemory]:
        """Abstract: extract high-level concepts from entries."""
        consolidated: list[ConsolidatedMemory] = []

        # Extract common concepts from tags
        tag_counts: dict[str, int] = defaultdict(int)
        for entry in entries:
            for tag in entry.tags:
                tag_counts[tag] += 1

        # Top concepts
        top_concepts = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_concepts:
            cm = ConsolidatedMemory(
                memory_id=f"abs-{uuid.uuid4().hex[:8]}",
                summary=f"Abstracted concepts: {', '.join(c for c, _ in top_concepts)}",
                concepts=[c for c, _ in top_concepts],
                source_count=len(entries),
                consolidation_strategy=ConsolidationStrategy.ABSTRACT,
                importance=MemoryImportance.HIGH,
                tags=[c for c, _ in top_concepts],
                metadata={"tag_frequencies": dict(top_concepts)},
            )
            consolidated.append(cm)
            self._consolidated.append(cm)
            self._total_consolidations += 1

        return consolidated

    def _consolidate_cluster(
        self, entries: list[MemoryEntry], limit: int
    ) -> list[ConsolidatedMemory]:
        """Cluster: group similar memories together."""
        # Simple clustering by tag overlap
        consolidated: list[ConsolidatedMemory] = []
        used: set[str] = set()

        for i, e1 in enumerate(entries):
            if e1.entry_id in used:
                continue
            cluster = [e1]
            used.add(e1.entry_id)

            for j, e2 in enumerate(entries):
                if i == j or e2.entry_id in used:
                    continue
                overlap = set(e1.tags) & set(e2.tags)
                if len(overlap) >= 2:
                    cluster.append(e2)
                    used.add(e2.entry_id)

            if len(cluster) >= 2:
                tags = list(set(t for e in cluster for t in e.tags))
                cm = ConsolidatedMemory(
                    memory_id=f"clust-{uuid.uuid4().hex[:8]}",
                    summary=f"Cluster of {len(cluster)} related memories: {tags[:5]}",
                    concepts=tags[:10],
                    source_count=len(cluster),
                    consolidation_strategy=ConsolidationStrategy.CLUSTER,
                    importance=MemoryImportance.MEDIUM,
                    tags=tags,
                    metadata={"cluster_size": len(cluster)},
                )
                consolidated.append(cm)
                self._consolidated.append(cm)
                self._total_consolidations += 1

        return consolidated

    def _consolidate_prune(self, entries: list[MemoryEntry]) -> None:
        """Prune: remove low-importance entries."""
        removed = 0
        for entry in entries[:]:
            if entry.importance in (MemoryImportance.TRIVIAL, MemoryImportance.LOW):
                if entry in self._episodic:
                    self._episodic.remove(entry)
                elif entry in self._semantic:
                    self._semantic.remove(entry)
                elif entry in self._procedural:
                    self._procedural.remove(entry)
                removed += 1

        if removed > 0:
            logger.info(f"Pruned {removed} low-importance entries")

    def _consolidate_reinforce(
        self, entries: list[MemoryEntry], limit: int
    ) -> list[ConsolidatedMemory]:
        """Reinforce: strengthen frequently accessed memories."""
        consolidated: list[ConsolidatedMemory] = []
        frequently_accessed = [e for e in entries if e.access_count >= 5]

        if frequently_accessed:
            cm = ConsolidatedMemory(
                memory_id=f"reinf-{uuid.uuid4().hex[:8]}",
                summary=f"Reinforced {len(frequently_accessed)} frequently accessed memories",
                concepts=[e.content[:50] for e in frequently_accessed[:5]],
                source_count=len(frequently_accessed),
                consolidation_strategy=ConsolidationStrategy.REINFORCE,
                importance=MemoryImportance.HIGH,
                tags=list(set(t for e in frequently_accessed for t in e.tags)),
            )
            consolidated.append(cm)
            self._consolidated.append(cm)
            self._total_consolidations += 1

        return consolidated

    def _consolidate_forget(self, entries: list[MemoryEntry]) -> None:
        """Forget: apply aggressive decay to old, unused memories."""
        now = time.time()
        removed = 0
        for entry in entries[:]:
            days_old = (now - entry.created_at) / 86400
            if days_old > 30 and entry.access_count < 3:
                if entry in self._episodic:
                    self._episodic.remove(entry)
                elif entry in self._semantic:
                    self._semantic.remove(entry)
                elif entry in self._procedural:
                    self._procedural.remove(entry)
                removed += 1

        if removed > 0:
            logger.info(f"Forgot {removed} old, unused entries")

    # ── Internal Helpers ─────────────────────────────────────────

    def _get_entries_by_layer(self, layer: str) -> list[MemoryEntry]:
        if layer == "episodic":
            return self._episodic
        elif layer == "semantic":
            return self._semantic
        elif layer == "procedural":
            return self._procedural
        return self._episodic

    def _prune_episodic(self) -> None:
        """Remove least important episodic entries."""
        self._episodic.sort(key=lambda e: {
            "pinned": 6, "critical": 5, "high": 4, "medium": 3, "low": 2, "trivial": 1,
        }.get(e.importance.value, 3))
        self._episodic = self._episodic[-(self.MAX_EPISODIC // 2):]

    def _prune_semantic(self) -> None:
        self._semantic.sort(key=lambda e: e.access_count, reverse=True)
        self._semantic = self._semantic[:self.MAX_SEMANTIC // 2]

    def _prune_procedural(self) -> None:
        self._procedural.sort(key=lambda e: e.access_count, reverse=True)
        self._procedural = self._procedural[:self.MAX_PROCEDURAL // 2]

    def _generate_summary(self, contents: list[str]) -> str:
        """Generate a summary from multiple content strings."""
        if not contents:
            return ""
        if len(contents) == 1:
            return contents[0][:200]

        # Simple extraction: first sentences + common words
        first_sentences = [c.split(".")[0][:100] for c in contents if c]
        summary = " | ".join(first_sentences[:5])
        return summary[:500]


# ── Global Singleton ─────────────────────────────────────────────

memory_consolidator = MemoryConsolidator()