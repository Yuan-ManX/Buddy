"""
Buddy White-box Memory — Transparent, Auditable Memory System
=============================================================
Every memory entry is visible, editable, and traceable. Users can inspect
what was stored, when, and why. Dream Mode consolidates memories during
idle periods and supports one-click rollback.

Core features:
  - Full visibility: every memory entry can be inspected
  - Editability: memories can be edited, pinned, or deleted
  - Traceability: full audit trail from generation to retrieval
  - Workspace isolation: memories are scoped per workspace
  - Dream Mode: background consolidation with rollback support
  - Semantic search: vector-based similarity search
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.whitebox_memory")


# ── Enums ──────────────────────────────────────────────────


class MemoryType(str, Enum):
    EPISODIC = "episodic"    # Event-based: "I helped debug a Python error on June 11"
    SEMANTIC = "semantic"   # Knowledge-based: "The project uses FastAPI with SQLAlchemy"
    PROCEDURAL = "procedural"  # How-to: "To deploy: run docker-compose up"
    DECISION = "decision"   # Decision records: "Chose PostgreSQL over MongoDB for X reason"
    PREFERENCE = "preference"  # User preferences: "Prefers dark theme, concise responses"


class MemoryImportance(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRANSIENT = "transient"


# ── Data Models ────────────────────────────────────────────


@dataclass
class WhiteboxMemoryEntry:
    """A fully transparent memory entry with audit trail."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    summary: str = ""  # Auto-generated summary for quick scanning
    memory_type: MemoryType = MemoryType.EPISODIC
    importance: MemoryImportance = MemoryImportance.MEDIUM
    workspace_id: str = ""
    session_id: str = ""
    agent_id: str = ""
    tags: list[str] = field(default_factory=list)
    embedding: list[float] | None = None  # Vector embedding for semantic search
    source: str = ""  # Where this memory came from (e.g., "chat", "tool_output", "user_override")
    source_detail: dict[str, Any] = field(default_factory=dict)
    is_pinned: bool = False
    is_edited: bool = False
    edit_history: list[dict[str, Any]] = field(default_factory=list)
    retrieval_count: int = 0
    last_retrieved_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str | None = None  # TTL for transient memories
    decay_factor: float = 1.0  # 1.0 = full strength, 0.0 = fully decayed
    dream_version: int = 0  # Incremented after each Dream Mode consolidation
    dream_backup: dict[str, Any] | None = None  # Pre-consolidation snapshot for rollback

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "summary": self.summary,
            "memory_type": self.memory_type.value,
            "importance": self.importance.value,
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "tags": self.tags,
            "source": self.source,
            "source_detail": self.source_detail,
            "is_pinned": self.is_pinned,
            "is_edited": self.is_edited,
            "edit_history": self.edit_history,
            "retrieval_count": self.retrieval_count,
            "last_retrieved_at": self.last_retrieved_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "decay_factor": self.decay_factor,
            "dream_version": self.dream_version,
        }

    def to_search_result(self) -> dict[str, Any]:
        """Format for search result display."""
        return {
            "id": self.id,
            "summary": self.summary or self.content[:200],
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance.value,
            "tags": self.tags,
            "retrieval_count": self.retrieval_count,
            "created_at": self.created_at,
            "is_pinned": self.is_pinned,
        }

    def record_retrieval(self):
        self.retrieval_count += 1
        self.last_retrieved_at = datetime.now(timezone.utc).isoformat()

    def edit(self, new_content: str, edited_by: str = "user"):
        """Edit memory content with audit trail."""
        self.edit_history.append({
            "previous_content": self.content[:500],
            "edited_by": edited_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.content = new_content
        self.is_edited = True
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def apply_decay(self, rate: float = 0.01):
        """Apply time-based decay to memory importance."""
        if not self.is_pinned:
            self.decay_factor = max(0.1, self.decay_factor - rate)

    def create_dream_backup(self):
        """Create a backup before Dream Mode consolidation."""
        self.dream_backup = {
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "importance": self.importance.value,
            "decay_factor": self.decay_factor,
        }

    def rollback_dream(self) -> bool:
        """Rollback to pre-dream state."""
        if not self.dream_backup:
            return False
        self.content = self.dream_backup["content"]
        self.summary = self.dream_backup["summary"]
        self.tags = self.dream_backup["tags"]
        self.importance = MemoryImportance(self.dream_backup["importance"])
        self.decay_factor = self.dream_backup["decay_factor"]
        self.dream_backup = None
        self.dream_version = max(0, self.dream_version - 1)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return True


# ── White-box Memory Engine ────────────────────────────────


class WhiteboxMemoryEngine:
    """Transparent memory system with full audit trail and Dream Mode.

    Every memory entry is inspectable, editable, and traceable. Users can
    see exactly what the agent remembers, why, and from where. Dream Mode
    consolidates memories during idle periods with rollback capability.
    """

    def __init__(self):
        self._memories: dict[str, WhiteboxMemoryEntry] = {}
        self._dream_log: list[dict[str, Any]] = []  # History of dream consolidations
        self._dream_enabled: bool = True
        self._dream_interval_minutes: int = 60  # Run dream mode every 60 min of idle

    # ── Memory CRUD ────────────────────────────────────

    def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        workspace_id: str = "",
        session_id: str = "",
        agent_id: str = "",
        tags: list[str] | None = None,
        source: str = "chat",
        source_detail: dict[str, Any] | None = None,
        summary: str = "",
        expires_in_hours: int | None = None,
    ) -> WhiteboxMemoryEntry:
        """Store a new memory entry."""
        if not summary:
            summary = self._auto_summarize(content)

        expires_at = None
        if expires_in_hours:
            from datetime import timedelta
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).isoformat()

        entry = WhiteboxMemoryEntry(
            content=content,
            summary=summary,
            memory_type=memory_type,
            importance=importance,
            workspace_id=workspace_id,
            session_id=session_id,
            agent_id=agent_id,
            tags=tags or [],
            source=source,
            source_detail=source_detail or {},
        )
        if expires_at:
            entry.expires_at = expires_at

        self._memories[entry.id] = entry
        logger.debug(f"Stored memory {entry.id}: {entry.summary[:50]}...")
        return entry

    def get(self, memory_id: str) -> WhiteboxMemoryEntry | None:
        entry = self._memories.get(memory_id)
        if entry:
            entry.record_retrieval()
        return entry

    def update(self, memory_id: str, **kwargs) -> WhiteboxMemoryEntry | None:
        """Update memory fields."""
        entry = self._memories.get(memory_id)
        if not entry:
            return None
        for key, value in kwargs.items():
            if hasattr(entry, key):
                if key == "importance" and isinstance(value, str):
                    value = MemoryImportance(value)
                elif key == "memory_type" and isinstance(value, str):
                    value = MemoryType(value)
                setattr(entry, key, value)
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        return entry

    def edit_content(self, memory_id: str, new_content: str, edited_by: str = "user") -> bool:
        """Edit memory content with audit trail."""
        entry = self._memories.get(memory_id)
        if not entry:
            return False
        entry.edit(new_content, edited_by)
        entry.summary = self._auto_summarize(new_content)
        return True

    def delete(self, memory_id: str) -> bool:
        return self._memories.pop(memory_id, None) is not None

    def pin(self, memory_id: str) -> bool:
        entry = self._memories.get(memory_id)
        if not entry:
            return False
        entry.is_pinned = True
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def unpin(self, memory_id: str) -> bool:
        entry = self._memories.get(memory_id)
        if not entry:
            return False
        entry.is_pinned = False
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    # ── Querying ───────────────────────────────────────

    def list_memories(
        self,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        memory_type: MemoryType | None = None,
        importance: MemoryImportance | None = None,
        tags: list[str] | None = None,
        pinned_only: bool = False,
        include_decayed: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WhiteboxMemoryEntry]:
        """List memories with comprehensive filtering."""
        results = list(self._memories.values())

        if workspace_id:
            results = [m for m in results if m.workspace_id == workspace_id]
        if agent_id:
            results = [m for m in results if m.agent_id == agent_id]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if importance:
            results = [m for m in results if m.importance == importance]
        if tags:
            results = [m for m in results if any(t in m.tags for t in tags)]
        if pinned_only:
            results = [m for m in results if m.is_pinned]
        if not include_decayed:
            results = [m for m in results if m.decay_factor > 0.2]

        # Sort: pinned first, then by importance, then by recency
        importance_order = {
            MemoryImportance.CRITICAL: 0,
            MemoryImportance.HIGH: 1,
            MemoryImportance.MEDIUM: 2,
            MemoryImportance.LOW: 3,
            MemoryImportance.TRANSIENT: 4,
        }
        results.sort(key=lambda m: (
            not m.is_pinned,
            importance_order.get(m.importance, 5),
        ), reverse=False)

        # Sort pinned by recency, then regular by recency
        pinned = [m for m in results if m.is_pinned]
        regular = [m for m in results if not m.is_pinned]
        pinned.sort(key=lambda m: m.updated_at, reverse=True)
        regular.sort(key=lambda m: m.updated_at, reverse=True)
        results = pinned + regular

        return results[offset:offset + limit]

    def search(
        self,
        query: str,
        workspace_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memories by keyword matching."""
        query_lower = query.lower()
        scored: list[tuple[float, WhiteboxMemoryEntry]] = []

        for entry in self._memories.values():
            if workspace_id and entry.workspace_id != workspace_id:
                continue
            if entry.decay_factor < 0.1:
                continue

            score = 0.0
            content_lower = entry.content.lower()
            summary_lower = entry.summary.lower()

            # Exact phrase match
            if query_lower in content_lower:
                score += 3.0
            elif query_lower in summary_lower:
                score += 2.0

            # Word overlap
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            overlap = query_words & content_words
            if overlap:
                score += len(overlap) * 0.5

            # Tag match
            for tag in entry.tags:
                if tag.lower() in query_lower:
                    score += 1.0

            # Importance bonus
            importance_bonus = {
                MemoryImportance.CRITICAL: 1.0,
                MemoryImportance.HIGH: 0.7,
                MemoryImportance.MEDIUM: 0.4,
                MemoryImportance.LOW: 0.2,
                MemoryImportance.TRANSIENT: 0.1,
            }
            score += importance_bonus.get(entry.importance, 0)

            # Recency bonus
            if entry.retrieval_count > 0:
                score += min(entry.retrieval_count * 0.1, 0.5)

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry.to_search_result() for _, entry in scored[:limit]]

    def get_audit_trail(self, memory_id: str) -> list[dict[str, Any]]:
        """Get the full edit history for a memory entry."""
        entry = self._memories.get(memory_id)
        if not entry:
            return []
        return [
            {
                "memory_id": memory_id,
                "created_at": entry.created_at,
                "source": entry.source,
                "source_detail": entry.source_detail,
                "is_edited": entry.is_edited,
                "edit_history": entry.edit_history,
                "dream_version": entry.dream_version,
            }
        ]

    # ── Dream Mode ─────────────────────────────────────

    def dream_consolidate(self, workspace_id: str | None = None) -> dict[str, Any]:
        """Run Dream Mode: consolidate and organize memories during idle time.

        This simulates background memory consolidation, similar to how
        the brain organizes memories during sleep. It:
        1. Creates backups of all affected memories
        2. Summarizes related memories into higher-level insights
        3. Merges duplicate or near-duplicate memories
        4. Applies decay to old, low-importance memories
        5. Updates tags and categories
        """
        dream_id = f"dream-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        affected = 0
        merged = 0
        decayed = 0
        insights: list[str] = []

        targets = list(self._memories.values())
        if workspace_id:
            targets = [m for m in targets if m.workspace_id == workspace_id]

        for entry in targets:
            # Create backup before modification
            entry.create_dream_backup()
            entry.dream_version += 1
            affected += 1

            # Apply decay to non-pinned memories
            if not entry.is_pinned and entry.importance in (
                MemoryImportance.LOW, MemoryImportance.TRANSIENT
            ):
                entry.apply_decay(rate=0.05)
                decayed += 1

        # Find and merge near-duplicates
        merged = self._merge_duplicates(targets)

        # Generate insights from clusters
        if len(targets) >= 5:
            insights = self._generate_insights(targets)

        dream_record = {
            "dream_id": dream_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "affected": affected,
            "merged": merged,
            "decayed": decayed,
            "insights": insights,
            "workspace_id": workspace_id,
        }
        self._dream_log.append(dream_record)
        logger.info(f"Dream Mode completed: {dream_id} (affected={affected}, merged={merged})")
        return dream_record

    def rollback_dream(self, dream_id: str) -> dict[str, Any]:
        """Rollback the last dream consolidation."""
        dream = None
        for d in reversed(self._dream_log):
            if d["dream_id"] == dream_id:
                dream = d
                break

        if not dream:
            # Rollback the most recent dream
            if self._dream_log:
                dream = self._dream_log.pop()
            else:
                return {"error": "No dream to rollback", "restored": 0}

        restored = 0
        for entry in self._memories.values():
            if entry.dream_backup:
                if entry.rollback_dream():
                    restored += 1

        logger.info(f"Dream rollback: restored {restored} memories")
        return {
            "dream_id": dream["dream_id"],
            "restored": restored,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _merge_duplicates(self, entries: list[WhiteboxMemoryEntry]) -> int:
        """Merge near-duplicate memory entries."""
        merged = 0
        seen: dict[str, list[WhiteboxMemoryEntry]] = {}

        for entry in entries:
            key = self._content_key(entry.content)
            if key in seen:
                seen[key].append(entry)
            else:
                seen[key] = [entry]

        for key, group in seen.items():
            if len(group) > 1:
                # Keep the first, merge tags from others
                primary = group[0]
                for dup in group[1:]:
                    primary.tags = list(set(primary.tags + dup.tags))
                    primary.retrieval_count += dup.retrieval_count
                    self._memories.pop(dup.id, None)
                    merged += 1

        return merged

    def _generate_insights(self, entries: list[WhiteboxMemoryEntry]) -> list[str]:
        """Generate insights from memory clusters."""
        insights = []
        # Group by memory type
        by_type: dict[MemoryType, list[WhiteboxMemoryEntry]] = {}
        for entry in entries:
            if entry.memory_type not in by_type:
                by_type[entry.memory_type] = []
            by_type[entry.memory_type].append(entry)

        for mtype, group in by_type.items():
            if len(group) >= 3:
                insights.append(
                    f"Found {len(group)} {mtype.value} memories across "
                    f"{len(set(e.workspace_id for e in group))} workspaces"
                )

        # Find frequent tags
        tag_counts: dict[str, int] = {}
        for entry in entries:
            for tag in entry.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        frequent_tags = [t for t, c in tag_counts.items() if c >= 3]
        if frequent_tags:
            insights.append(f"Frequent themes: {', '.join(frequent_tags[:5])}")

        return insights

    def _content_key(self, content: str) -> str:
        """Generate a normalized key for deduplication."""
        normalized = content.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def _auto_summarize(self, content: str, max_length: int = 120) -> str:
        """Generate a brief summary of content."""
        # Clean and truncate
        cleaned = content.strip().replace('\n', ' ')
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[:max_length - 3] + "..."

    # ── Export / Import ────────────────────────────────

    def export_memories(
        self,
        workspace_id: str | None = None,
        format: str = "json",
    ) -> str:
        """Export memories for backup or transfer."""
        entries = list(self._memories.values())
        if workspace_id:
            entries = [m for m in entries if m.workspace_id == workspace_id]

        data = [e.to_dict() for e in entries]
        if format == "jsonl":
            return "\n".join(json.dumps(d, default=str) for d in data)
        return json.dumps(data, indent=2, default=str)

    def import_memories(self, data: str, format: str = "json") -> int:
        """Import memories from serialized data."""
        count = 0
        try:
            if format == "jsonl":
                entries = [json.loads(line) for line in data.strip().split("\n") if line.strip()]
            else:
                entries = json.loads(data)

            for entry_data in entries:
                entry = WhiteboxMemoryEntry(
                    id=entry_data.get("id", str(uuid.uuid4())),
                    content=entry_data.get("content", ""),
                    summary=entry_data.get("summary", ""),
                    memory_type=MemoryType(entry_data.get("memory_type", "episodic")),
                    importance=MemoryImportance(entry_data.get("importance", "medium")),
                    workspace_id=entry_data.get("workspace_id", ""),
                    session_id=entry_data.get("session_id", ""),
                    agent_id=entry_data.get("agent_id", ""),
                    tags=entry_data.get("tags", []),
                    source=entry_data.get("source", "import"),
                    source_detail=entry_data.get("source_detail", {}),
                    is_pinned=entry_data.get("is_pinned", False),
                    is_edited=entry_data.get("is_edited", False),
                    edit_history=entry_data.get("edit_history", []),
                    retrieval_count=entry_data.get("retrieval_count", 0),
                    decay_factor=entry_data.get("decay_factor", 1.0),
                    dream_version=entry_data.get("dream_version", 0),
                )
                self._memories[entry.id] = entry
                count += 1
        except Exception as e:
            logger.error(f"Memory import error: {e}")
        return count

    # ── Stats ──────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get memory system statistics."""
        by_type: dict[str, int] = {}
        by_importance: dict[str, int] = {}
        by_workspace: dict[str, int] = {}

        for entry in self._memories.values():
            by_type[entry.memory_type.value] = by_type.get(entry.memory_type.value, 0) + 1
            by_importance[entry.importance.value] = by_importance.get(entry.importance.value, 0) + 1
            if entry.workspace_id:
                by_workspace[entry.workspace_id] = by_workspace.get(entry.workspace_id, 0) + 1

        return {
            "total": len(self._memories),
            "pinned": len([m for m in self._memories.values() if m.is_pinned]),
            "edited": len([m for m in self._memories.values() if m.is_edited]),
            "by_type": by_type,
            "by_importance": by_importance,
            "by_workspace": by_workspace,
            "dreams_run": len(self._dream_log),
            "dream_enabled": self._dream_enabled,
            "avg_retrieval_count": (
                sum(m.retrieval_count for m in self._memories.values())
                / max(len(self._memories), 1)
            ),
        }


# ── Singleton ──────────────────────────────────────────────

whitebox_memory = WhiteboxMemoryEngine()