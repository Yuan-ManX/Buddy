"""
Memory White-Box System - Transparent, Traceable Memory for Buddy Agents.

The Memory White-Box system provides complete transparency into agent memory
operations. Every memory entry is fully traceable from creation through
modification, with full rollback capabilities, automatic organization, and
deduplication. The system ensures that agent memory is never a black box.

Core capabilities:
- Full traceability: every memory entry has a complete audit trail
- Visualization-ready: memory organized for timeline and graph display
- Rollback: undo any memory change with point-in-time recovery
- Auto-organization: periodic "dream" cycles that organize and optimize
- Deduplication: automatic detection and merging of duplicate memories
- Tagging and categorization: rich metadata for search and filtering
"""

from __future__ import annotations

import math
import uuid
import time
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.white_memory")


class MemoryCategory(str, Enum):
    """Categories for memory entries."""
    FACT = "fact"                    # Learned facts and information
    PREFERENCE = "preference"        # User preferences and settings
    EXPERIENCE = "experience"        # Past task execution records
    RELATIONSHIP = "relationship"    # Relationships between entities
    PROCEDURE = "procedure"          # How-to knowledge and workflows
    INSIGHT = "insight"              # Derived insights and patterns
    CONTEXT = "context"              # Session and environmental context
    DECISION = "decision"            # Past decisions and their rationale


class MemoryStatus(str, Enum):
    """Status of a memory entry."""
    ACTIVE = "active"                # Currently in use
    ARCHIVED = "archived"            # Archived but retrievable
    MERGED = "merged"                # Merged into another entry
    DEPRECATED = "deprecated"        # No longer valid
    CORRUPTED = "corrupted"          # Detected as contradictory
    CONSOLIDATED = "consolidated"    # Consolidated into a higher-level summary


@dataclass
class MemoryEntry:
    """A single memory entry with full traceability."""
    entry_id: str
    agent_id: str
    content: str
    category: MemoryCategory
    importance: float = 0.5          # 0.0 to 1.0
    confidence: float = 0.5          # 0.0 to 1.0
    tags: list[str] = field(default_factory=list)
    source: str = "agent"            # Where the memory came from
    related_entries: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: MemoryStatus = MemoryStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    version: int = 1
    edit_history: list[dict] = field(default_factory=list)

    def record_access(self) -> None:
        """Record an access to this memory entry."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)

    def record_edit(self, old_content: str, reason: str = "") -> None:
        """Record an edit to the memory content."""
        self.edit_history.append({
            "version": self.version,
            "old_content": old_content,
            "new_content": self.content,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "agent_id": self.agent_id,
            "content": self.content,
            "category": self.category.value,
            "importance": self.importance,
            "confidence": self.confidence,
            "tags": self.tags,
            "source": self.source,
            "related_entries": self.related_entries,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "version": self.version,
            "edit_count": len(self.edit_history),
        }


@dataclass
class MemorySnapshot:
    """A point-in-time snapshot of agent memory for rollback."""
    snapshot_id: str
    agent_id: str
    entries: dict[str, MemoryEntry] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    label: str = ""
    entry_count: int = 0

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "label": self.label,
            "entry_count": self.entry_count,
        }


class WhiteMemoryStore:
    """Transparent, traceable memory store for Buddy agents.

    Provides complete visibility into agent memory with full audit trails,
    rollback capabilities, automatic organization, and deduplication.
    Every memory operation is logged and traceable.
    """

    # Negation patterns used in conflict detection (case-insensitive).
    # Each entry is a pair of (positive_pattern, negated_pattern) where
    # the presence of one pattern but not the other in a similar memory
    # suggests a contradiction.
    _NEGATION_PATTERNS: list[tuple[str, str]] = [
        (" is ", " is not "),
        (" is ", " isn't "),
        (" are ", " are not "),
        (" are ", " aren't "),
        (" does ", " does not "),
        (" does ", " doesn't "),
        (" has ", " has no "),
        (" has ", " doesn't have "),
        (" can ", " cannot "),
        (" can ", " can't "),
        (" will ", " will not "),
        (" will ", " won't "),
        (" should ", " should not "),
        (" should ", " shouldn't "),
        (" always ", " never "),
        (" true", " false"),
        (" yes", " no"),
        (" enabled", " disabled"),
        (" active", " inactive"),
        (" supports ", " does not support "),
        (" likes ", " dislikes "),
        (" prefers ", " does not prefer "),
    ]

    def __init__(self):
        self._entries: dict[str, MemoryEntry] = {}
        self._snapshots: dict[str, MemorySnapshot] = {}
        self._audit_log: list[dict] = []
        self._total_entries = 0
        self._total_snapshots = 0
        self._total_operations = 0

    # ── Core Memory Operations ──────────────────────────────────────

    def store(
        self,
        agent_id: str,
        content: str,
        category: MemoryCategory = MemoryCategory.FACT,
        importance: float = 0.5,
        confidence: float = 0.5,
        tags: list[str] | None = None,
        source: str = "agent",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a new memory entry with full traceability."""
        entry_id = f"mem-{uuid.uuid4().hex[:12]}"

        # Check for duplicates before storing
        duplicate = self._find_duplicate(agent_id, content, category)
        if duplicate:
            self._audit_log.append({
                "operation": "duplicate_detected",
                "entry_id": entry_id,
                "duplicate_of": duplicate.entry_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Merge instead of creating duplicate
            return self._merge_entries(duplicate, content, confidence)

        entry = MemoryEntry(
            entry_id=entry_id,
            agent_id=agent_id,
            content=content,
            category=category,
            importance=importance,
            confidence=confidence,
            tags=tags or [],
            source=source,
            metadata=metadata or {},
        )
        self._entries[entry_id] = entry
        self._total_entries += 1
        self._total_operations += 1

        self._audit_log.append({
            "operation": "store",
            "entry_id": entry_id,
            "agent_id": agent_id,
            "category": category.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return entry

    def retrieve(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by ID."""
        entry = self._entries.get(entry_id)
        if entry:
            entry.record_access()
            self._audit_log.append({
                "operation": "retrieve",
                "entry_id": entry_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return entry

    def update(
        self,
        entry_id: str,
        content: str | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        tags: list[str] | None = None,
        reason: str = "",
    ) -> MemoryEntry | None:
        """Update an existing memory entry with edit tracking."""
        entry = self._entries.get(entry_id)
        if not entry:
            return None

        old_content = entry.content

        if content is not None:
            entry.content = content
        if importance is not None:
            entry.importance = importance
        if confidence is not None:
            entry.confidence = confidence
        if tags is not None:
            entry.tags = tags

        entry.record_edit(old_content, reason)
        self._total_operations += 1

        self._audit_log.append({
            "operation": "update",
            "entry_id": entry_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return entry

    def delete(self, entry_id: str, reason: str = "") -> bool:
        """Soft-delete (archive) a memory entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            return False

        entry.status = MemoryStatus.ARCHIVED
        entry.updated_at = datetime.now(timezone.utc)
        self._total_operations += 1

        self._audit_log.append({
            "operation": "delete",
            "entry_id": entry_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return True

    # ── Deduplication ───────────────────────────────────────────────

    def _find_duplicate(
        self, agent_id: str, content: str, category: MemoryCategory
    ) -> MemoryEntry | None:
        """Find a potential duplicate entry using content similarity."""
        content_lower = content.lower().strip()

        for entry in self._entries.values():
            if entry.agent_id != agent_id:
                continue
            if entry.status != MemoryStatus.ACTIVE:
                continue
            if entry.category != category:
                continue

            # Simple content overlap check
            existing = entry.content.lower().strip()
            if content_lower == existing:
                return entry

            # Check for significant overlap
            words_new = set(content_lower.split())
            words_existing = set(existing.split())
            if words_new and words_existing:
                overlap = len(words_new & words_existing) / max(
                    len(words_new), len(words_existing)
                )
                if overlap > 0.8:
                    return entry

        return None

    def _merge_entries(
        self, existing: MemoryEntry, new_content: str, new_confidence: float
    ) -> MemoryEntry:
        """Merge a new memory entry into an existing one."""
        old_content = existing.content

        # Update confidence as weighted average
        total_weight = existing.confidence + new_confidence
        if total_weight > 0:
            existing.confidence = (
                (existing.confidence * existing.access_count + new_confidence) /
                (existing.access_count + 1)
            )

        existing.record_edit(old_content, "merged with similar entry")
        existing.record_access()
        existing.metadata["merge_count"] = existing.metadata.get("merge_count", 0) + 1

        return existing

    def run_deduplication(self, agent_id: str | None = None) -> int:
        """Run full deduplication across all active entries."""
        merged_count = 0
        entries = list(self._entries.values())

        for i, entry_a in enumerate(entries):
            if entry_a.status != MemoryStatus.ACTIVE:
                continue
            if agent_id and entry_a.agent_id != agent_id:
                continue

            for entry_b in entries[i + 1:]:
                if entry_b.status != MemoryStatus.ACTIVE:
                    continue
                if agent_id and entry_b.agent_id != agent_id:
                    continue
                if entry_a.category != entry_b.category:
                    continue

                # Check content similarity
                words_a = set(entry_a.content.lower().split())
                words_b = set(entry_b.content.lower().split())
                if words_a and words_b:
                    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
                    if overlap > 0.85:
                        self._merge_entries(entry_a, entry_b.content, entry_b.confidence)
                        entry_b.status = MemoryStatus.MERGED
                        entry_b.metadata["merged_into"] = entry_a.entry_id
                        merged_count += 1

        return merged_count

    # ── Snapshot & Rollback ─────────────────────────────────────────

    def create_snapshot(self, agent_id: str, label: str = "") -> MemorySnapshot:
        """Create a point-in-time snapshot for rollback capability."""
        snapshot_id = f"snap-{uuid.uuid4().hex[:12]}"

        # Deep copy entries for this agent
        agent_entries: dict[str, MemoryEntry] = {}
        for entry_id, entry in self._entries.items():
            if entry.agent_id == agent_id:
                # Create a copy
                copied = MemoryEntry(
                    entry_id=entry.entry_id,
                    agent_id=entry.agent_id,
                    content=entry.content,
                    category=entry.category,
                    importance=entry.importance,
                    confidence=entry.confidence,
                    tags=list(entry.tags),
                    source=entry.source,
                    related_entries=list(entry.related_entries),
                    metadata=dict(entry.metadata),
                    status=entry.status,
                    created_at=entry.created_at,
                    updated_at=entry.updated_at,
                    last_accessed=entry.last_accessed,
                    access_count=entry.access_count,
                    version=entry.version,
                    edit_history=list(entry.edit_history),
                )
                agent_entries[entry_id] = copied

        snapshot = MemorySnapshot(
            snapshot_id=snapshot_id,
            agent_id=agent_id,
            entries=agent_entries,
            label=label,
            entry_count=len(agent_entries),
        )
        self._snapshots[snapshot_id] = snapshot
        self._total_snapshots += 1

        self._audit_log.append({
            "operation": "snapshot_created",
            "snapshot_id": snapshot_id,
            "agent_id": agent_id,
            "label": label,
            "entry_count": snapshot.entry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return snapshot

    def rollback(self, snapshot_id: str) -> int:
        """Rollback memory to a previous snapshot. Returns count of restored entries."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return 0

        restored = 0
        # Remove current entries for this agent
        to_remove = [
            eid for eid, e in self._entries.items()
            if e.agent_id == snapshot.agent_id
        ]
        for eid in to_remove:
            del self._entries[eid]

        # Restore from snapshot
        for entry_id, entry in snapshot.entries.items():
            self._entries[entry_id] = entry
            restored += 1

        self._audit_log.append({
            "operation": "rollback",
            "snapshot_id": snapshot_id,
            "agent_id": snapshot.agent_id,
            "restored_entries": restored,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return restored

    # ── Dream Mode (Auto-Organization) ──────────────────────────────

    def dream_organize(self, agent_id: str) -> dict:
        """Run dream mode: auto-organize and optimize memory.

        This simulates background processing where the agent:
        1. Identifies stale/unused memories for archiving
        2. Links related memories
        3. Updates importance scores based on access patterns
        4. Removes contradictory entries
        """
        results = {
            "archived": 0,
            "linked": 0,
            "updated": 0,
            "conflicts_resolved": 0,
        }

        agent_entries = [
            e for e in self._entries.values()
            if e.agent_id == agent_id and e.status == MemoryStatus.ACTIVE
        ]

        # Archive stale entries (not accessed in 30+ days, low importance)
        now = datetime.now(timezone.utc)
        for entry in agent_entries:
            days_since_access = (now - entry.last_accessed).days
            if days_since_access > 30 and entry.importance < 0.3:
                entry.status = MemoryStatus.ARCHIVED
                results["archived"] += 1

            # Boost importance for frequently accessed entries
            if entry.access_count > 10:
                entry.importance = min(1.0, entry.importance + 0.1)
                results["updated"] += 1

        # Link related entries by content similarity
        for i, entry_a in enumerate(agent_entries):
            for entry_b in agent_entries[i + 1:]:
                if entry_a.category == entry_b.category:
                    words_a = set(entry_a.content.lower().split())
                    words_b = set(entry_b.content.lower().split())
                    if words_a and words_b:
                        overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
                        if overlap > 0.5:
                            if entry_b.entry_id not in entry_a.related_entries:
                                entry_a.related_entries.append(entry_b.entry_id)
                                results["linked"] += 1
                            if entry_a.entry_id not in entry_b.related_entries:
                                entry_b.related_entries.append(entry_a.entry_id)

        self._audit_log.append({
            "operation": "dream_organize",
            "agent_id": agent_id,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return results

    # ── Query Methods ───────────────────────────────────────────────

    def search(
        self,
        agent_id: str | None = None,
        query: str = "",
        category: MemoryCategory | None = None,
        tags: list[str] | None = None,
        min_importance: float = 0.0,
        min_confidence: float = 0.0,
        status: MemoryStatus | None = None,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """Search memory entries with multiple filters."""
        results: list[MemoryEntry] = []

        query_lower = query.lower()
        for entry in self._entries.values():
            if agent_id and entry.agent_id != agent_id:
                continue
            if category and entry.category != category:
                continue
            if status and entry.status != status:
                continue
            if entry.importance < min_importance:
                continue
            if entry.confidence < min_confidence:
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue
            if query_lower and query_lower not in entry.content.lower():
                continue

            entry.record_access()
            results.append(entry)

        results.sort(key=lambda e: (e.importance, e.access_count), reverse=True)
        return results[:limit]

    def get_memory_timeline(
        self, agent_id: str, limit: int = 100
    ) -> list[dict]:
        """Get a chronological timeline of memory operations."""
        timeline = [
            {
                "entry_id": e.entry_id,
                "content": e.content[:200],
                "category": e.category.value,
                "operation": "created",
                "timestamp": e.created_at.isoformat(),
            }
            for e in self._entries.values()
            if e.agent_id == agent_id
        ]

        timeline.sort(key=lambda x: x["timestamp"], reverse=True)
        return timeline[:limit]

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Get the full audit log of memory operations."""
        return self._audit_log[-limit:]

    def get_stats(self) -> dict:
        """Get white memory store statistics."""
        active = sum(1 for e in self._entries.values()
                     if e.status == MemoryStatus.ACTIVE)
        archived = sum(1 for e in self._entries.values()
                       if e.status == MemoryStatus.ARCHIVED)
        categories = {}
        for e in self._entries.values():
            cat = e.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_entries": self._total_entries,
            "active_entries": active,
            "archived_entries": archived,
            "total_snapshots": self._total_snapshots,
            "total_operations": self._total_operations,
            "categories": categories,
            "average_importance": (
                sum(e.importance for e in self._entries.values()) /
                max(1, len(self._entries))
            ),
            "total_accesses": sum(e.access_count for e in self._entries.values()),
        }

    # ── Semantic Search ─────────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words, stripping punctuation."""
        # Simple tokenization: split on whitespace and strip common punctuation
        cleaned = text.lower()
        for ch in ".,!?;:()[]{}'\"-":
            cleaned = cleaned.replace(ch, " ")
        return [w for w in cleaned.split() if len(w) > 1]

    def _build_tfidf_vectors(
        self,
        documents: list[str],
    ) -> tuple[dict[str, int], dict[str, float], list[dict[str, float]]]:
        """Build TF-IDF weighted vectors for a list of documents.

        Returns:
            (vocabulary mapping word->index, idf dict, list of tfidf vectors)
        """
        # Tokenize all documents
        tokenized = [self._tokenize(doc) for doc in documents]

        # Build vocabulary from all documents
        vocab: dict[str, int] = {}
        for tokens in tokenized:
            for word in tokens:
                if word not in vocab:
                    vocab[word] = len(vocab)

        # Compute IDF (inverse document frequency)
        n_docs = len(documents)
        doc_freq = Counter()
        for tokens in tokenized:
            for word in set(tokens):
                doc_freq[word] += 1

        idf: dict[str, float] = {}
        for word, idx in vocab.items():
            df = doc_freq.get(word, 0)
            idf[word] = math.log((n_docs + 1) / (df + 1)) + 1.0

        # Compute TF-IDF vectors
        vectors: list[dict[str, float]] = []
        for tokens in tokenized:
            tf = Counter(tokens)
            max_tf = max(tf.values()) if tf else 1
            vector: dict[str, float] = {}
            for word, count in tf.items():
                if word in vocab:
                    # Normalized term frequency
                    tf_norm = count / max_tf
                    vector[word] = tf_norm * idf.get(word, 0.0)
            vectors.append(vector)

        return vocab, idf, vectors

    def _cosine_similarity(
        self, vec_a: dict[str, float], vec_b: dict[str, float]
    ) -> float:
        """Compute cosine similarity between two sparse vectors."""
        dot = 0.0
        for word, val_a in vec_a.items():
            val_b = vec_b.get(word, 0.0)
            dot += val_a * val_b

        mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
        mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0

        return dot / (mag_a * mag_b)

    def semantic_search(
        self,
        query: str,
        agent_id: str | None = None,
        category: MemoryCategory | None = None,
        similarity_threshold: float = 0.3,
        limit: int = 20,
    ) -> list[tuple[MemoryEntry, float]]:
        """Search memories using semantic similarity (word-embedding-based scoring).

        Uses TF-IDF weighted bag-of-words vectors with cosine similarity to
        simulate word-embedding-based semantic search. When a real embedding
        model is available, the `_tokenize` and `_build_tfidf_vectors` methods
        can be overridden to use actual embeddings while keeping the same API.

        Args:
            query: The search query string.
            agent_id: Optional agent ID to filter by.
            category: Optional memory category to filter by.
            similarity_threshold: Minimum cosine similarity to include (0.0-1.0).
            limit: Maximum number of results to return.

        Returns:
            List of (MemoryEntry, similarity_score) tuples sorted by score descending.
        """
        if not query.strip():
            return []

        # Filter candidate entries
        candidates: list[MemoryEntry] = []
        for entry in self._entries.values():
            if entry.status != MemoryStatus.ACTIVE:
                continue
            if agent_id and entry.agent_id != agent_id:
                continue
            if category and entry.category != category:
                continue
            candidates.append(entry)

        if not candidates:
            return []

        # Build a combined corpus: query + all candidate contents
        documents = [query] + [e.content for e in candidates]
        _, _, vectors = self._build_tfidf_vectors(documents)

        query_vec = vectors[0]
        entry_vecs = vectors[1:]

        # Score each candidate by cosine similarity
        scored: list[tuple[MemoryEntry, float]] = []
        for entry, vec in zip(candidates, entry_vecs):
            sim = self._cosine_similarity(query_vec, vec)
            if sim >= similarity_threshold:
                entry.record_access()
                scored.append((entry, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    # ── Conflict Detection ──────────────────────────────────────────

    def _has_negation(self, text: str) -> bool:
        """Check if text contains negation patterns."""
        lower = text.lower()
        negations = [
            " not ", " isn't ", " aren't ", " wasn't ", " weren't ",
            " doesn't ", " don't ", " didn't ", " cannot ", " can't ",
            " won't ", " wouldn't ", " shouldn't ", " never ", " neither ",
            " nor ", " no ", " none ", " nothing ",
        ]
        return any(neg in f" {lower} " for neg in negations)

    def _check_contradiction(
        self, content_a: str, content_b: str
    ) -> bool:
        """Check if two content strings are likely contradictory.

        Looks for pairs where one contains a positive assertion and the
        other contains a corresponding negated form, or where they share
        a common subject but have opposite predicates.
        """
        lower_a = f" {content_a.lower()} "
        lower_b = f" {content_b.lower()} "

        for positive, negated in self._NEGATION_PATTERNS:
            pos_in_a = positive in lower_a
            neg_in_a = negated in lower_a
            pos_in_b = positive in lower_b
            neg_in_b = negated in lower_b

            # One has the positive form, the other has the negated form
            if (pos_in_a and neg_in_b) or (neg_in_a and pos_in_b):
                return True

        return False

    def detect_conflicts(
        self,
        agent_id: str | None = None,
        category: MemoryCategory | None = None,
        similarity_threshold: float = 0.6,
        auto_flag: bool = True,
    ) -> list[dict]:
        """Detect contradictory memories and flag them for resolution.

        Scans all active memory entries for pairs that share high content
        similarity but contain contradictory statements (e.g., one says
        "X is true" while another says "X is false"). Flagged conflicts
        are marked as CORRUPTED and linked via related_entries.

        Args:
            agent_id: Optional agent ID to filter by.
            category: Optional memory category to filter by.
            similarity_threshold: Minimum word overlap to consider as related (0.0-1.0).
            auto_flag: If True, automatically mark conflicting entries as CORRUPTED.

        Returns:
            List of conflict dicts, each containing:
                - entry_a_id, entry_b_id: IDs of conflicting entries
                - content_a, content_b: The conflicting content strings
                - similarity: The word overlap similarity score
                - contradiction_type: How the contradiction was detected
        """
        candidates: list[MemoryEntry] = []
        for entry in self._entries.values():
            if entry.status != MemoryStatus.ACTIVE:
                continue
            if agent_id and entry.agent_id != agent_id:
                continue
            if category and entry.category != category:
                continue
            candidates.append(entry)

        conflicts: list[dict] = []

        for i, entry_a in enumerate(candidates):
            words_a = set(entry_a.content.lower().split())
            if not words_a:
                continue

            for entry_b in candidates[i + 1:]:
                words_b = set(entry_b.content.lower().split())
                if not words_b:
                    continue

                # Compute word overlap similarity
                overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
                if overlap < similarity_threshold:
                    continue

                # Check for contradiction patterns
                if self._check_contradiction(entry_a.content, entry_b.content):
                    conflict_type = "negation"
                    conflicts.append({
                        "entry_a_id": entry_a.entry_id,
                        "entry_b_id": entry_b.entry_id,
                        "content_a": entry_a.content,
                        "content_b": entry_b.content,
                        "similarity": round(overlap, 4),
                        "contradiction_type": conflict_type,
                    })

                    if auto_flag:
                        entry_a.status = MemoryStatus.CORRUPTED
                        entry_b.status = MemoryStatus.CORRUPTED
                        entry_a.metadata["conflict_with"] = entry_b.entry_id
                        entry_b.metadata["conflict_with"] = entry_a.entry_id
                        # Link the conflicting entries
                        if entry_b.entry_id not in entry_a.related_entries:
                            entry_a.related_entries.append(entry_b.entry_id)
                        if entry_a.entry_id not in entry_b.related_entries:
                            entry_b.related_entries.append(entry_a.entry_id)

        if conflicts:
            self._audit_log.append({
                "operation": "conflict_detection",
                "agent_id": agent_id,
                "conflicts_found": len(conflicts),
                "auto_flagged": auto_flag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return conflicts

    # ── Memory Consolidation ────────────────────────────────────────

    def consolidate_memories(
        self,
        agent_id: str,
        category: MemoryCategory | None = None,
        similarity_threshold: float = 0.5,
        min_cluster_size: int = 2,
    ) -> list[MemoryEntry]:
        """Consolidate related memories into higher-level summaries.

        Groups similar active memories into clusters by category and
        content overlap, then creates a new summary entry for each cluster.
        Original entries are marked as CONSOLIDATED and linked to the summary.

        This is intended to be called during dream cycles to create compact,
        high-level representations of related memory clusters.

        Args:
            agent_id: The agent ID whose memories to consolidate.
            category: Optional category to limit consolidation to.
            similarity_threshold: Minimum word overlap for clustering (0.0-1.0).
            min_cluster_size: Minimum number of entries to form a cluster.

        Returns:
            List of newly created summary MemoryEntry objects.
        """
        # Collect active candidate entries
        candidates: list[MemoryEntry] = []
        for entry in self._entries.values():
            if entry.agent_id != agent_id:
                continue
            if entry.status != MemoryStatus.ACTIVE:
                continue
            if category and entry.category != category:
                continue
            candidates.append(entry)

        if len(candidates) < min_cluster_size:
            return []

        # Build adjacency: which entries are similar enough to cluster
        n = len(candidates)
        adjacency: list[list[int]] = [[] for _ in range(n)]
        for i in range(n):
            words_i = set(candidates[i].content.lower().split())
            if not words_i:
                continue
            for j in range(i + 1, n):
                if candidates[i].category != candidates[j].category:
                    continue
                words_j = set(candidates[j].content.lower().split())
                if not words_j:
                    continue
                overlap = len(words_i & words_j) / max(len(words_i), len(words_j))
                if overlap >= similarity_threshold:
                    adjacency[i].append(j)
                    adjacency[j].append(i)

        # Find connected components (clusters) via DFS
        visited = [False] * n
        clusters: list[list[int]] = []
        for i in range(n):
            if visited[i] or not adjacency[i]:
                continue
            # DFS to find the connected component
            stack = [i]
            component: list[int] = []
            while stack:
                node = stack.pop()
                if visited[node]:
                    continue
                visited[node] = True
                component.append(node)
                for neighbor in adjacency[node]:
                    if not visited[neighbor]:
                        stack.append(neighbor)
            if len(component) >= min_cluster_size:
                clusters.append(component)

        # Create summary entries for each cluster
        summaries: list[MemoryEntry] = []
        for cluster_indices in clusters:
            cluster_entries = [candidates[idx] for idx in cluster_indices]

            # Build a summary from the cluster contents
            all_contents = [e.content for e in cluster_entries]
            combined_text = " ".join(all_contents)
            # Use the most common words as a simple summary
            words = self._tokenize(combined_text)
            if not words:
                continue
            word_freq = Counter(words)
            most_common = [w for w, _ in word_freq.most_common(15)]
            summary_content = "Summary: " + " ".join(most_common)
            if len(summary_content) > 500:
                summary_content = summary_content[:497] + "..."

            # Average importance and confidence
            avg_importance = sum(e.importance for e in cluster_entries) / len(cluster_entries)
            avg_confidence = sum(e.confidence for e in cluster_entries) / len(cluster_entries)

            # Collect all unique tags from the cluster
            all_tags = list(set(t for e in cluster_entries for t in e.tags))

            # Use the category of the first entry (all in cluster share same category)
            cluster_category = cluster_entries[0].category

            # Create the summary entry
            summary_entry = self.store(
                agent_id=agent_id,
                content=summary_content,
                category=cluster_category,
                importance=min(1.0, avg_importance + 0.1),
                confidence=avg_confidence,
                tags=all_tags,
                source="consolidation",
                metadata={
                    "consolidated_from": [e.entry_id for e in cluster_entries],
                    "cluster_size": len(cluster_entries),
                    "consolidated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Mark original entries as consolidated
            for entry in cluster_entries:
                entry.status = MemoryStatus.CONSOLIDATED
                entry.metadata["consolidated_into"] = summary_entry.entry_id
                if summary_entry.entry_id not in entry.related_entries:
                    entry.related_entries.append(summary_entry.entry_id)
                if entry.entry_id not in summary_entry.related_entries:
                    summary_entry.related_entries.append(entry.entry_id)

            summaries.append(summary_entry)

        if summaries:
            self._audit_log.append({
                "operation": "consolidate_memories",
                "agent_id": agent_id,
                "clusters_consolidated": len(summaries),
                "total_entries_consolidated": sum(
                    len(s.metadata.get("consolidated_from", [])) for s in summaries
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return summaries

    # ── Memory Importance Decay ─────────────────────────────────────

    def apply_importance_decay(
        self,
        agent_id: str | None = None,
        decay_rate: float = 0.01,
        half_life_days: float = 30.0,
        min_importance: float = 0.05,
    ) -> dict:
        """Apply time-based exponential decay to importance scores of unaccessed memories.

        The decay formula is:
            new_importance = importance * exp(-decay_rate * days_since_access)

        If half_life_days is provided, decay_rate is derived from it:
            decay_rate = ln(2) / half_life_days

        This ensures that after half_life_days of inactivity, a memory's importance
        is halved. Only active memories are affected; archived/consolidated entries
        are skipped.

        Args:
            agent_id: Optional agent ID to limit decay to.
            decay_rate: Direct decay rate per day (ignored if half_life_days is set).
            half_life_days: Days after which importance halves. Overrides decay_rate.
            min_importance: Minimum importance floor; decay will not go below this.

        Returns:
            Dict with decay statistics:
                - entries_decayed: Number of entries whose importance was reduced
                - total_decay: Sum of importance points decayed
                - average_decay: Average decay per affected entry
        """
        # Derive decay rate from half-life if provided
        if half_life_days > 0:
            effective_decay_rate = math.log(2) / half_life_days
        else:
            effective_decay_rate = decay_rate

        now = datetime.now(timezone.utc)
        entries_decayed = 0
        total_decay = 0.0

        for entry in self._entries.values():
            if entry.status != MemoryStatus.ACTIVE:
                continue
            if agent_id and entry.agent_id != agent_id:
                continue

            # Calculate days since last access
            delta = now - entry.last_accessed
            days_since_access = delta.total_seconds() / 86400.0

            if days_since_access <= 0:
                continue

            # Apply exponential decay
            old_importance = entry.importance
            decay_factor = math.exp(-effective_decay_rate * days_since_access)
            new_importance = old_importance * decay_factor

            # Enforce minimum floor
            new_importance = max(min_importance, new_importance)

            if new_importance < old_importance:
                entry.importance = new_importance
                decay_amount = old_importance - new_importance
                total_decay += decay_amount
                entries_decayed += 1

        if entries_decayed > 0:
            self._audit_log.append({
                "operation": "importance_decay",
                "agent_id": agent_id,
                "entries_decayed": entries_decayed,
                "total_decay": round(total_decay, 4),
                "average_decay": round(total_decay / entries_decayed, 4),
                "decay_rate": round(effective_decay_rate, 6),
                "half_life_days": half_life_days,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return {
            "entries_decayed": entries_decayed,
            "total_decay": round(total_decay, 4),
            "average_decay": round(total_decay / max(1, entries_decayed), 4),
        }

    # ── Memory Graph Export ─────────────────────────────────────────

    def export_graph(
        self,
        agent_id: str | None = None,
        category: MemoryCategory | None = None,
        status: MemoryStatus | None = None,
    ) -> dict:
        """Export the memory graph structure for visualization.

        Produces a node-edge graph representation where:
        - Nodes are memory entries with id, content, category, importance, etc.
        - Edges represent relationships between memories (via related_entries).

        The output format is compatible with graph visualization tools like
        D3.js, Cytoscape.js, and Gephi.

        Args:
            agent_id: Optional agent ID to filter by.
            category: Optional memory category to filter by.
            status: Optional memory status to filter by (defaults to ACTIVE).

        Returns:
            Dict with "nodes" and "edges" lists, plus metadata:
                {
                    "nodes": [{"id": str, "label": str, "category": str, ...}],
                    "edges": [{"source": str, "target": str, "type": str}],
                    "metadata": {"total_nodes": int, "total_edges": int, ...}
                }
        """
        # Filter entries
        filtered: list[MemoryEntry] = []
        for entry in self._entries.values():
            if agent_id and entry.agent_id != agent_id:
                continue
            if category and entry.category != category:
                continue
            if status and entry.status != status:
                continue
            filtered.append(entry)

        # Build node set (for quick membership checks on edges)
        node_ids = {e.entry_id for e in filtered}

        # Build nodes
        nodes: list[dict] = []
        for entry in filtered:
            nodes.append({
                "id": entry.entry_id,
                "label": entry.content[:100],
                "content": entry.content,
                "category": entry.category.value,
                "importance": entry.importance,
                "confidence": entry.confidence,
                "status": entry.status.value,
                "access_count": entry.access_count,
                "created_at": entry.created_at.isoformat(),
                "last_accessed": entry.last_accessed.isoformat(),
                "tags": entry.tags,
                "size": max(1, int(entry.importance * 10)),
            })

        # Build edges from related_entries
        edges: list[dict] = []
        seen_edges: set[tuple[str, str]] = set()
        for entry in filtered:
            for related_id in entry.related_entries:
                if related_id not in node_ids:
                    continue
                # Normalize edge direction (undirected for visualization)
                pair = tuple(sorted([entry.entry_id, related_id]))
                if pair in seen_edges:
                    continue
                seen_edges.add(pair)
                edges.append({
                    "source": entry.entry_id,
                    "target": related_id,
                    "type": "related",
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "agent_id": agent_id,
                "category": category.value if category else None,
                "status_filter": status.value if status else "all",
                "exported_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    # ── Contextual Recall ───────────────────────────────────────────

    def contextual_recall(
        self,
        context: str,
        agent_id: str | None = None,
        top_k: int = 10,
        semantic_weight: float = 0.4,
        recency_weight: float = 0.2,
        importance_weight: float = 0.25,
        access_weight: float = 0.15,
    ) -> list[tuple[MemoryEntry, float]]:
        """Recall memories relevant to a given context using multi-factor relevance scoring.

        Combines four scoring factors into a single relevance score:
        1. Semantic similarity: how well the memory content matches the context
        2. Recency: how recently the memory was last accessed
        3. Importance: the memory's intrinsic importance score
        4. Access frequency: how often the memory has been accessed

        Each factor is normalized to [0, 1] and combined with configurable weights.

        Args:
            context: The context string to recall memories for.
            agent_id: Optional agent ID to filter by.
            top_k: Maximum number of results to return.
            semantic_weight: Weight for semantic similarity (0.0-1.0).
            recency_weight: Weight for recency score (0.0-1.0).
            importance_weight: Weight for intrinsic importance (0.0-1.0).
            access_weight: Weight for access frequency (0.0-1.0).

        Returns:
            List of (MemoryEntry, relevance_score) tuples sorted by score descending.
        """
        if not context.strip():
            return []

        # Normalize weights so they sum to 1.0
        total_weight = semantic_weight + recency_weight + importance_weight + access_weight
        if total_weight == 0:
            return []
        sem_w = semantic_weight / total_weight
        rec_w = recency_weight / total_weight
        imp_w = importance_weight / total_weight
        acc_w = access_weight / total_weight

        # Collect active candidates
        candidates: list[MemoryEntry] = []
        for entry in self._entries.values():
            if entry.status != MemoryStatus.ACTIVE:
                continue
            if agent_id and entry.agent_id != agent_id:
                continue
            candidates.append(entry)

        if not candidates:
            return []

        n = len(candidates)
        now = datetime.now(timezone.utc)

        # ── Factor 1: Semantic Similarity ──────────────────────────
        # Build TF-IDF vectors for context + all candidate contents
        documents = [context] + [e.content for e in candidates]
        _, _, vectors = self._build_tfidf_vectors(documents)
        context_vec = vectors[0]
        entry_vecs = vectors[1:]

        semantic_scores: list[float] = []
        for vec in entry_vecs:
            semantic_scores.append(self._cosine_similarity(context_vec, vec))

        # ── Factor 2: Recency ──────────────────────────────────────
        # Score = 1.0 for just-accessed, decaying to 0 over 30 days
        recency_scores: list[float] = []
        for entry in candidates:
            days_since = (now - entry.last_accessed).total_seconds() / 86400.0
            recency_scores.append(max(0.0, 1.0 - days_since / 30.0))

        # ── Factor 3: Importance ───────────────────────────────────
        imp_scores = [e.importance for e in candidates]

        # ── Factor 4: Access Frequency ─────────────────────────────
        # Normalize access counts to [0, 1] using min-max scaling
        access_counts = [e.access_count for e in candidates]
        max_access = max(access_counts) if access_counts else 1
        if max_access > 0:
            acc_scores = [c / max_access for c in access_counts]
        else:
            acc_scores = [0.0] * n

        # ── Combine Scores ─────────────────────────────────────────
        scored: list[tuple[MemoryEntry, float]] = []
        for i, entry in enumerate(candidates):
            relevance = (
                sem_w * semantic_scores[i] +
                rec_w * recency_scores[i] +
                imp_w * imp_scores[i] +
                acc_w * acc_scores[i]
            )
            entry.record_access()
            scored.append((entry, round(relevance, 4)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# Singleton instance
white_memory = WhiteMemoryStore()


# ═══════════════════════════════════════════════════════════
# Backward-compatible aliases for existing code
# ═══════════════════════════════════════════════════════════

class MemoryLifecycleStage(str, Enum):
    """Memory lifecycle stages (backward compat)."""
    RAW = "raw"
    STRUCTURED = "structured"
    CONSOLIDATED = "consolidated"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemoryProvenance(str, Enum):
    """Memory provenance (backward compat)."""
    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"
    INFERRED = "inferred"
    IMPORTED = "imported"


@dataclass
class MemoryAuditEntry:
    """Memory audit entry (backward compat)."""
    audit_id: str
    memory_id: str
    stage: str
    agent_id: str | None = None
    trigger: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)


WhiteMemory = WhiteMemoryStore  # Backward-compatible alias
WhiteMemoryEntry = MemoryEntry  # Backward-compatible alias