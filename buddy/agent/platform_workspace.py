"""Buddy Platform Workspace — per-project isolation boundary

Every project gets its own memory store, skill set, and file namespace.
This atomic isolation prevents cross-project context bleed and gives
bounded retrieval scope — a project's memory search never leaks into
another project's results.

Design principles (synthesized from platform engineering patterns):
  - Workspace as atomic unit: memory, skills, files, and cognitive
    profiles are all scoped to a workspace. No cross-workspace access
    without explicit delegation.
  - White-box memory: every memory entry is traceable to its source,
    editable, and rollback-able. Memory is an auditable artifact, not
    a black-box vector store.
  - Dream Mode: idle-triggered memory consolidation that merges
    duplicate entries, compresses long histories, and strengthens
    high-relevance memories.
  - Snapshot and restore: workspaces can be snapshotted at any point
    and restored, enabling experiment branching.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("buddy.platform.workspace")


# ═══════════════════════════════════════════════════════════
# Workspace data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class WorkspaceMemoryEntry:
    """A white-box memory entry in a workspace."""
    id: str = ""
    content: str = ""
    source: str = ""  # conversation, tool, dream, import
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    relevance_score: float = 0.5
    revision: int = 1
    previous_content: Optional[str] = None  # For rollback

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "relevance_score": self.relevance_score,
            "revision": self.revision,
        }


@dataclass
class WorkspaceSnapshot:
    """A point-in-time snapshot of a workspace for branching/restore."""
    snapshot_id: str = ""
    workspace_id: str = ""
    label: str = ""
    memory_count: int = 0
    skill_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    memory_entries: list[WorkspaceMemoryEntry] = field(default_factory=list)
    skill_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "workspace_id": self.workspace_id,
            "label": self.label,
            "memory_count": self.memory_count,
            "skill_count": self.skill_count,
            "timestamp": self.timestamp,
        }


@dataclass
class Workspace:
    """A project-scoped isolation boundary.

    Each workspace has its own memory store, skill set, and file
    namespace. This prevents cross-project context pollution.
    """
    workspace_id: str = ""
    name: str = ""
    owner_agent_id: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: str = ""
    memory_entries: list[WorkspaceMemoryEntry] = field(default_factory=list)
    skill_ids: list[str] = field(default_factory=list)
    file_namespace: str = ""  # Root path for workspace files
    metadata: dict[str, Any] = field(default_factory=dict)
    is_archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "owner_agent_id": self.owner_agent_id,
            "description": self.description,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "memory_count": len(self.memory_entries),
            "skill_count": len(self.skill_ids),
            "file_namespace": self.file_namespace,
            "is_archived": self.is_archived,
            "metadata": self.metadata,
        }


# ═══════════════════════════════════════════════════════════
# Workspace Manager
# ═══════════════════════════════════════════════════════════

class WorkspaceManager:
    """Manages workspace lifecycle, memory, skills, and snapshots.

    Workspaces are the atomic isolation boundary. All agent operations
    happen within a workspace context — memory searches, skill
    invocations, and file access are all scoped to the current workspace.
    """

    def __init__(self):
        self._workspaces: dict[str, Workspace] = {}
        self._snapshots: dict[str, list[WorkspaceSnapshot]] = {}
        self._active_workspace: dict[str, str] = {}  # agent_id -> workspace_id
        self._lock = threading.RLock()

    # ── Workspace lifecycle ──────────────────────────────

    def create_workspace(
        self,
        name: str,
        owner_agent_id: str,
        description: str = "",
        file_namespace: Optional[str] = None,
    ) -> Workspace:
        """Create a new isolated workspace."""
        workspace_id = f"ws-{uuid.uuid4().hex[:12]}"
        workspace = Workspace(
            workspace_id=workspace_id,
            name=name,
            owner_agent_id=owner_agent_id,
            description=description,
            file_namespace=file_namespace or f"/workspaces/{workspace_id}",
        )
        with self._lock:
            self._workspaces[workspace_id] = workspace
        logger.info("Created workspace '%s' (%s) for agent %s", name, workspace_id, owner_agent_id)
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def list_workspaces(
        self, agent_id: Optional[str] = None, include_archived: bool = False
    ) -> list[dict[str, Any]]:
        with self._lock:
            workspaces = list(self._workspaces.values())
        if agent_id:
            workspaces = [w for w in workspaces if w.owner_agent_id == agent_id]
        if not include_archived:
            workspaces = [w for w in workspaces if not w.is_archived]
        return [w.to_dict() for w in workspaces]

    def archive_workspace(self, workspace_id: str) -> bool:
        """Archive a workspace (non-destructive)."""
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return False
            workspace.is_archived = True
            return True

    def set_active_workspace(self, agent_id: str, workspace_id: str) -> bool:
        """Set the active workspace for an agent."""
        with self._lock:
            if workspace_id not in self._workspaces:
                return False
            self._active_workspace[agent_id] = workspace_id
            self._workspaces[workspace_id].last_active = datetime.now(timezone.utc).isoformat()
            return True

    def get_active_workspace(self, agent_id: str) -> Optional[Workspace]:
        with self._lock:
            ws_id = self._active_workspace.get(agent_id)
            if ws_id is None:
                return None
            return self._workspaces.get(ws_id)

    # ── White-box memory operations ──────────────────────

    def add_memory(
        self,
        workspace_id: str,
        content: str,
        source: str = "conversation",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Add a memory entry to a workspace. Returns entry ID."""
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return None
            entry_id = f"mem-{uuid.uuid4().hex[:12]}"
            entry = WorkspaceMemoryEntry(
                id=entry_id,
                content=content,
                source=source,
                metadata=metadata or {},
            )
            workspace.memory_entries.append(entry)
            workspace.last_active = datetime.now(timezone.utc).isoformat()
            return entry_id

    def search_memory(
        self,
        workspace_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search memory within a workspace (scoped, no cross-workspace leak)."""
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return []
            entries = workspace.memory_entries

        # Keyword-based scoring
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scored: list[tuple[float, WorkspaceMemoryEntry]] = []

        for entry in entries:
            content_lower = entry.content.lower()
            if query_lower in content_lower:
                score = 1.0
            else:
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                score = overlap / max(1, len(query_words))
            if score > 0:
                entry.relevance_score = score
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e.to_dict() for _, e in scored[:limit]]

    def edit_memory(
        self,
        workspace_id: str,
        entry_id: str,
        new_content: str,
    ) -> bool:
        """Edit a memory entry (white-box, with rollback support)."""
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return False
            for entry in workspace.memory_entries:
                if entry.id == entry_id:
                    entry.previous_content = entry.content
                    entry.content = new_content
                    entry.revision += 1
                    return True
            return False

    def rollback_memory(
        self,
        workspace_id: str,
        entry_id: str,
    ) -> bool:
        """Rollback a memory entry to its previous content."""
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return False
            for entry in workspace.memory_entries:
                if entry.id == entry_id and entry.previous_content is not None:
                    entry.content = entry.previous_content
                    entry.previous_content = None
                    entry.revision += 1
                    return True
            return False

    def delete_memory(self, workspace_id: str, entry_id: str) -> bool:
        """Delete a memory entry from a workspace."""
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return False
            original_len = len(workspace.memory_entries)
            workspace.memory_entries = [
                e for e in workspace.memory_entries if e.id != entry_id
            ]
            return len(workspace.memory_entries) < original_len

    # ── Skill management ─────────────────────────────────

    def add_skill(self, workspace_id: str, skill_id: str) -> bool:
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return False
            if skill_id not in workspace.skill_ids:
                workspace.skill_ids.append(skill_id)
            return True

    def get_skills(self, workspace_id: str) -> list[str]:
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return []
            return list(workspace.skill_ids)

    # ── Snapshot and restore ─────────────────────────────

    def snapshot_workspace(
        self,
        workspace_id: str,
        label: str = "",
    ) -> Optional[str]:
        """Create a point-in-time snapshot for branching/restore."""
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return None
            snapshot_id = f"snap-{uuid.uuid4().hex[:12]}"
            snapshot = WorkspaceSnapshot(
                snapshot_id=snapshot_id,
                workspace_id=workspace_id,
                label=label or f"Snapshot at {datetime.now(timezone.utc).isoformat()}",
                memory_count=len(workspace.memory_entries),
                skill_count=len(workspace.skill_ids),
                memory_entries=list(workspace.memory_entries),
                skill_ids=list(workspace.skill_ids),
            )
            if workspace_id not in self._snapshots:
                self._snapshots[workspace_id] = []
            self._snapshots[workspace_id].append(snapshot)
            return snapshot_id

    def restore_snapshot(self, workspace_id: str, snapshot_id: str) -> bool:
        """Restore a workspace to a previous snapshot."""
        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            snapshots = self._snapshots.get(workspace_id, [])
            snapshot = next((s for s in snapshots if s.snapshot_id == snapshot_id), None)
            if workspace is None or snapshot is None:
                return False
            workspace.memory_entries = list(snapshot.memory_entries)
            workspace.skill_ids = list(snapshot.skill_ids)
            return True

    def list_snapshots(self, workspace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            snapshots = self._snapshots.get(workspace_id, [])
            return [s.to_dict() for s in snapshots]

    # ── Dream Mode — idle memory consolidation ───────────

    def dream_consolidate(self, workspace_id: str) -> dict[str, Any]:
        """Idle-triggered memory consolidation.

        Merges duplicate entries, compresses long histories, and
        strengthens high-relevance memories. Called when the workspace
        has been idle.
        """
        start_time = time.time()
        result = {"merged": 0, "compressed": 0, "strengthened": 0}

        with self._lock:
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                return result
            entries = workspace.memory_entries

        # Merge near-duplicates (same first 80 chars)
        seen_prefixes: dict[str, int] = {}
        to_remove: list[int] = []

        for idx, entry in enumerate(entries):
            prefix = entry.content[:80].lower().strip()
            if prefix in seen_prefixes:
                # Merge: keep the first, remove this one
                first_idx = seen_prefixes[prefix]
                entries[first_idx].metadata["merged_count"] = (
                    entries[first_idx].metadata.get("merged_count", 1) + 1
                )
                to_remove.append(idx)
                result["merged"] += 1
            else:
                seen_prefixes[prefix] = idx

        for idx in reversed(to_remove):
            entries.pop(idx)

        # Strengthen high-relevance memories
        for entry in entries:
            if entry.relevance_score >= 0.8:
                entry.metadata["strengthened"] = True
                result["strengthened"] += 1

        # Compress: if more than 100 entries, keep top 80 by relevance
        if len(entries) > 100:
            entries.sort(key=lambda e: e.relevance_score, reverse=True)
            result["compressed"] = len(entries) - 80
            workspace.memory_entries = entries[:80]
        else:
            workspace.memory_entries = entries

        result["elapsed_ms"] = (time.time() - start_time) * 1000
        logger.info(
            "Dream consolidation for %s: %d merged, %d compressed, %d strengthened",
            workspace_id,
            result["merged"],
            result["compressed"],
            result["strengthened"],
        )
        return result

    # ── Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            total_memory = sum(len(w.memory_entries) for w in self._workspaces.values())
            total_skills = sum(len(w.skill_ids) for w in self._workspaces.values())
            return {
                "total_workspaces": len(self._workspaces),
                "active_workspaces": sum(1 for w in self._workspaces.values() if not w.is_archived),
                "archived_workspaces": sum(1 for w in self._workspaces.values() if w.is_archived),
                "total_memory_entries": total_memory,
                "total_skills": total_skills,
                "total_snapshots": sum(len(s) for s in self._snapshots.values()),
                "active_agents": len(self._active_workspace),
            }


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

_workspace_manager: Optional[WorkspaceManager] = None
_wm_lock = threading.Lock()


def get_workspace_manager() -> WorkspaceManager:
    """Get the singleton WorkspaceManager instance."""
    global _workspace_manager
    if _workspace_manager is None:
        with _wm_lock:
            if _workspace_manager is None:
                _workspace_manager = WorkspaceManager()
    return _workspace_manager
