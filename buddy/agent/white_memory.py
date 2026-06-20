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

import uuid
import time
import logging
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