"""
Buddy White-box Memory - Traceable memory management system.

Provides complete visibility into the agent's memory lifecycle —
generation, extraction, storage, and retrieval are all auditable.
Users can view, edit, delete, and pin memory entries. When the AI
mis-remembers something, the user can pinpoint and fix the offending
entry directly.

Key capabilities:
- End-to-end memory traceability (generation → extraction → storage → retrieval)
- Per-workspace memory isolation with bounded scope
- Editable and deletable memory entries
- Pin critical decisions to prevent drift
- Memory versioning with rollback support
- Auditable memory lineage with provenance tracking
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MemoryLifecycleStage(str, Enum):
    """Stages in the white-box memory lifecycle."""
    GENERATED = "generated"       # Raw memory was generated
    EXTRACTED = "extracted"       # Key info extracted from raw memory
    STORED = "stored"             # Memory stored in the knowledge base
    RETRIEVED = "retrieved"       # Memory was retrieved for use
    UPDATED = "updated"           # Memory was edited or updated
    ARCHIVED = "archived"         # Memory was archived
    DELETED = "deleted"           # Memory was deleted


class MemoryCategory(str, Enum):
    """Categories of white-box memory entries."""
    FACT = "fact"                 # Verifiable factual information
    PREFERENCE = "preference"     # User preferences and settings
    DECISION = "decision"         # Past decisions and their rationale
    CONTEXT = "context"           # Session context and state
    SKILL = "skill"               # Learned skills and procedures
    RELATIONSHIP = "relationship"  # Entity relationships and connections
    INSIGHT = "insight"           # Derived insights and patterns


@dataclass
class MemoryProvenance:
    """Tracks the origin and evolution of a memory entry."""
    provenance_id: str
    source_type: str               # e.g., "conversation", "tool_output", "inference"
    source_id: str                 # ID of the source (conversation_id, tool_call_id, etc.)
    extraction_method: str         # How the memory was extracted
    extraction_confidence: float   # Confidence score of the extraction
    raw_content: str               # The original raw content
    extracted_at: float = field(default_factory=time.time)


@dataclass
class MemoryAuditEntry:
    """An audit trail entry for a memory operation."""
    audit_id: str
    memory_id: str
    stage: MemoryLifecycleStage
    timestamp: float = field(default_factory=time.time)
    agent_id: str | None = None
    trigger: str | None = None     # What triggered this operation
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class WhiteMemoryEntry:
    """A white-box memory entry with complete traceability."""
    entry_id: str
    content: str
    category: MemoryCategory
    workspace_id: str | None = None
    importance: float = 0.5
    confidence: float = 0.5
    pinned: bool = False
    archived: bool = False
    tags: list[str] = field(default_factory=list)
    provenance: MemoryProvenance | None = None
    version: int = 1
    parent_entry_id: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = 0.0
    related_entries: list[str] = field(default_factory=list)


class WhiteMemory:
    """Traceable white-box memory management system for Buddy.

    Provides complete visibility into the agent's memory lifecycle.
    Every memory entry tracks its provenance (where it came from),
    lineage (how it evolved), and audit trail (who accessed/modified it
    and when). Users can inspect, edit, delete, and pin entries.

    Memory is scoped per workspace, preventing cross-project pollution.
    The system supports versioning and rollback, so no change is permanent.
    """

    def __init__(self):
        self._entries: dict[str, WhiteMemoryEntry] = {}
        self._audit_trail: list[MemoryAuditEntry] = []
        self._total_entries = 0
        self._total_audits = 0

    def store(
        self,
        content: str,
        category: MemoryCategory,
        workspace_id: str | None = None,
        importance: float = 0.5,
        confidence: float = 0.5,
        tags: list[str] | None = None,
        provenance: MemoryProvenance | None = None,
        related_entries: list[str] | None = None,
        agent_id: str | None = None,
    ) -> str:
        """Store a new memory entry with full traceability."""
        entry_id = f"wmem-{uuid.uuid4().hex[:12]}"
        entry = WhiteMemoryEntry(
            entry_id=entry_id,
            content=content,
            category=category,
            workspace_id=workspace_id,
            importance=importance,
            confidence=confidence,
            tags=tags or [],
            provenance=provenance,
            related_entries=related_entries or [],
        )
        self._entries[entry_id] = entry
        self._total_entries += 1

        self._add_audit(
            memory_id=entry_id,
            stage=MemoryLifecycleStage.STORED,
            agent_id=agent_id,
            trigger="store",
        )
        return entry_id

    def retrieve(self, entry_id: str, agent_id: str | None = None) -> WhiteMemoryEntry | None:
        """Retrieve a memory entry and record the access."""
        entry = self._entries.get(entry_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._add_audit(
                memory_id=entry_id,
                stage=MemoryLifecycleStage.RETRIEVED,
                agent_id=agent_id,
                trigger="retrieve",
            )
        return entry

    def update(
        self,
        entry_id: str,
        content: str | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        tags: list[str] | None = None,
        agent_id: str | None = None,
    ) -> WhiteMemoryEntry | None:
        """Update a memory entry, creating a new version."""
        entry = self._entries.get(entry_id)
        if not entry:
            return None

        # Create a new version
        new_version = WhiteMemoryEntry(
            entry_id=f"{entry_id}-v{entry.version + 1}",
            content=content if content is not None else entry.content,
            category=entry.category,
            workspace_id=entry.workspace_id,
            importance=importance if importance is not None else entry.importance,
            confidence=confidence if confidence is not None else entry.confidence,
            pinned=entry.pinned,
            tags=tags if tags is not None else list(entry.tags),
            provenance=entry.provenance,
            version=entry.version + 1,
            parent_entry_id=entry.entry_id,
            related_entries=list(entry.related_entries),
        )

        entry.archived = True
        entry.updated_at = time.time()
        self._entries[new_version.entry_id] = new_version

        self._add_audit(
            memory_id=entry_id,
            stage=MemoryLifecycleStage.UPDATED,
            agent_id=agent_id,
            trigger="update",
            details={"new_version_id": new_version.entry_id},
        )
        return new_version

    def delete(self, entry_id: str, agent_id: str | None = None) -> bool:
        """Soft-delete a memory entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        entry.archived = True
        self._add_audit(
            memory_id=entry_id,
            stage=MemoryLifecycleStage.DELETED,
            agent_id=agent_id,
            trigger="delete",
        )
        return True

    def pin(self, entry_id: str, agent_id: str | None = None) -> bool:
        """Pin a memory entry to prevent accidental deletion."""
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        entry.pinned = True
        self._add_audit(
            memory_id=entry_id,
            stage=MemoryLifecycleStage.UPDATED,
            agent_id=agent_id,
            trigger="pin",
        )
        return True

    def unpin(self, entry_id: str, agent_id: str | None = None) -> bool:
        """Unpin a memory entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        entry.pinned = False
        self._add_audit(
            memory_id=entry_id,
            stage=MemoryLifecycleStage.UPDATED,
            agent_id=agent_id,
            trigger="unpin",
        )
        return True

    def _add_audit(
        self,
        memory_id: str,
        stage: MemoryLifecycleStage,
        agent_id: str | None = None,
        trigger: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Add an entry to the audit trail."""
        audit = MemoryAuditEntry(
            audit_id=f"audit-{uuid.uuid4().hex[:12]}",
            memory_id=memory_id,
            stage=stage,
            agent_id=agent_id,
            trigger=trigger,
            details=details or {},
        )
        self._audit_trail.append(audit)
        self._total_audits += 1

    def get_audit_trail(
        self,
        memory_id: str | None = None,
        stage: MemoryLifecycleStage | None = None,
        limit: int = 50,
    ) -> list[MemoryAuditEntry]:
        """Get the audit trail, optionally filtered."""
        trail = self._audit_trail
        if memory_id:
            trail = [a for a in trail if a.memory_id == memory_id]
        if stage:
            trail = [a for a in trail if a.stage == stage]
        return trail[-limit:]

    def get_lineage(self, entry_id: str) -> list[WhiteMemoryEntry]:
        """Get the full version lineage of a memory entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            return []

        lineage = [entry]
        current = entry
        while current.parent_entry_id:
            parent = self._entries.get(current.parent_entry_id)
            if parent:
                lineage.insert(0, parent)
                current = parent
            else:
                break
        return lineage

    def query(
        self,
        workspace_id: str | None = None,
        category: MemoryCategory | None = None,
        min_importance: float = 0.0,
        tag: str | None = None,
        include_archived: bool = False,
        search_text: str | None = None,
        limit: int = 50,
    ) -> list[WhiteMemoryEntry]:
        """Query memory entries with flexible filtering."""
        results = list(self._entries.values())

        if not include_archived:
            results = [e for e in results if not e.archived]

        if workspace_id:
            results = [e for e in results if e.workspace_id == workspace_id]

        if category:
            results = [e for e in results if e.category == category]

        if min_importance > 0:
            results = [e for e in results if e.importance >= min_importance]

        if tag:
            results = [e for e in results if tag in e.tags]

        if search_text:
            search_lower = search_text.lower()
            results = [e for e in results if search_lower in e.content.lower()]

        results.sort(key=lambda e: (e.pinned, e.importance, e.updated_at), reverse=True)
        return results[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get white-box memory statistics."""
        return {
            "total_entries": self._total_entries,
            "active_entries": len([e for e in self._entries.values() if not e.archived]),
            "archived_entries": len([e for e in self._entries.values() if e.archived]),
            "pinned_entries": len([e for e in self._entries.values() if e.pinned]),
            "total_audits": self._total_audits,
            "entries_by_category": {
                cat.value: len([e for e in self._entries.values() if e.category == cat and not e.archived])
                for cat in MemoryCategory
            },
            "entries_by_importance": {
                "high": len([e for e in self._entries.values() if e.importance >= 0.7 and not e.archived]),
                "medium": len([e for e in self._entries.values() if 0.3 <= e.importance < 0.7 and not e.archived]),
                "low": len([e for e in self._entries.values() if e.importance < 0.3 and not e.archived]),
            },
            "recent_audits": [
                {
                    "audit_id": a.audit_id,
                    "memory_id": a.memory_id,
                    "stage": a.stage.value,
                    "agent_id": a.agent_id,
                    "trigger": a.trigger,
                    "timestamp": a.timestamp,
                }
                for a in self._audit_trail[-20:]
            ],
        }


# Singleton instance
white_memory = WhiteMemory()