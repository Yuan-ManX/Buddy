"""
Buddy WorkSpace Manager

Complete project-level isolation with independent file systems, memory
stores, skill sets, and configuration. Each WorkSpace operates as a
self-contained environment preventing cross-project context pollution
while enabling natural accretion of project-specific knowledge.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorkSpaceConfig:
    """Configuration for a WorkSpace environment."""

    name: str
    description: str = ""
    workspace_id: str = ""

    # Isolation settings
    isolate_files: bool = True
    isolate_memory: bool = True
    isolate_skills: bool = True
    isolate_models: bool = False

    # Resource limits
    max_file_size_mb: int = 100
    max_total_size_mb: int = 1000
    max_memory_entries: int = 1000
    max_skills: int = 50

    # Auto-management
    auto_cleanup_days: int = 0
    auto_snapshot_enabled: bool = False
    snapshot_interval_hours: int = 24

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "isolate_files": self.isolate_files,
            "isolate_memory": self.isolate_memory,
            "isolate_skills": self.isolate_skills,
            "isolate_models": self.isolate_models,
            "max_file_size_mb": self.max_file_size_mb,
            "max_total_size_mb": self.max_total_size_mb,
            "max_memory_entries": self.max_memory_entries,
            "max_skills": self.max_skills,
            "auto_cleanup_days": self.auto_cleanup_days,
            "auto_snapshot_enabled": self.auto_snapshot_enabled,
            "snapshot_interval_hours": self.snapshot_interval_hours,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class WorkSpaceSnapshot:
    """A point-in-time snapshot of a WorkSpace state."""

    snapshot_id: str
    workspace_id: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    file_count: int = 0
    memory_entries: int = 0
    skill_count: int = 0
    total_size_bytes: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "workspace_id": self.workspace_id,
            "description": self.description,
            "created_at": self.created_at,
            "file_count": self.file_count,
            "memory_entries": self.memory_entries,
            "skill_count": self.skill_count,
            "total_size_bytes": self.total_size_bytes,
            "metadata": self.metadata,
        }


class WorkSpace:
    """An isolated project environment with independent resources."""

    def __init__(self, config: WorkSpaceConfig, base_path: str = ""):
        self.config = config
        self.base_path = base_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".buddy_data", "workspaces", config.workspace_id
        )
        self._files: dict[str, dict] = {}
        self._memory_entries: dict[str, dict] = {}
        self._skills: dict[str, dict] = {}
        self._snapshots: dict[str, WorkSpaceSnapshot] = {}
        self._activity_log: list[dict] = []
        self._stats = {
            "total_operations": 0,
            "total_file_reads": 0,
            "total_file_writes": 0,
            "total_memory_ops": 0,
            "total_skill_uses": 0,
        }

        self._ensure_directories()

    def _ensure_directories(self):
        """Create workspace directory structure."""
        os.makedirs(self.base_path, exist_ok=True)
        if self.config.isolate_files:
            os.makedirs(os.path.join(self.base_path, "files"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "snapshots"), exist_ok=True)

    def _log_activity(self, action: str, details: dict | None = None):
        """Log workspace activity."""
        self._stats["total_operations"] += 1
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details or {},
        }
        self._activity_log.append(entry)
        if len(self._activity_log) > 500:
            self._activity_log = self._activity_log[-500:]

    # ── File Operations ──

    def write_file(self, path: str, content: str) -> dict:
        """Write content to a file within the workspace."""
        if not self.config.isolate_files:
            return {"error": "File isolation disabled"}

        full_path = os.path.join(self.base_path, "files", path.lstrip("/"))

        # Security: prevent path traversal
        real_base = os.path.realpath(os.path.join(self.base_path, "files"))
        real_path = os.path.realpath(full_path)
        if not real_path.startswith(real_base):
            return {"error": "Path traversal not allowed"}

        # Size check
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > self.config.max_file_size_mb * 1024 * 1024:
            return {"error": f"File exceeds max size of {self.config.max_file_size_mb}MB"}

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        self._files[path] = {
            "path": path,
            "size": content_bytes,
            "modified_at": datetime.now(timezone.utc).isoformat(),
        }
        self._stats["total_file_writes"] += 1
        self._log_activity("file_write", {"path": path, "size": content_bytes})
        return {"success": True, "path": path, "size": content_bytes}

    def read_file(self, path: str) -> dict:
        """Read content from a file within the workspace."""
        if not self.config.isolate_files:
            return {"error": "File isolation disabled"}

        full_path = os.path.join(self.base_path, "files", path.lstrip("/"))

        real_base = os.path.realpath(os.path.join(self.base_path, "files"))
        real_path = os.path.realpath(full_path)
        if not real_path.startswith(real_base):
            return {"error": "Path traversal not allowed"}

        if not os.path.exists(full_path):
            return {"error": "File not found"}

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._stats["total_file_reads"] += 1
        self._log_activity("file_read", {"path": path})
        return {"success": True, "path": path, "content": content}

    def list_files(self, prefix: str = "") -> list[dict]:
        """List files in the workspace."""
        if not self.config.isolate_files:
            return []

        files_dir = os.path.join(self.base_path, "files")
        if not os.path.exists(files_dir):
            return []

        result = []
        for root, _, files in os.walk(files_dir):
            for filename in files:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, files_dir)
                if prefix and not rel_path.startswith(prefix):
                    continue
                result.append({
                    "path": rel_path,
                    "size": os.path.getsize(full_path),
                    "modified_at": datetime.fromtimestamp(
                        os.path.getmtime(full_path), tz=timezone.utc
                    ).isoformat(),
                })
        return result

    # ── Memory Operations ──

    def add_memory(self, key: str, value: Any, tags: list[str] | None = None) -> dict:
        """Add a memory entry to the workspace."""
        if not self.config.isolate_memory:
            return {"error": "Memory isolation disabled"}

        if len(self._memory_entries) >= self.config.max_memory_entries:
            return {"error": "Memory store full"}

        self._memory_entries[key] = {
            "key": key,
            "value": value,
            "tags": tags or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "access_count": 0,
        }
        self._stats["total_memory_ops"] += 1
        self._log_activity("memory_add", {"key": key, "tags": tags})
        return {"success": True, "key": key}

    def get_memory(self, key: str) -> dict | None:
        """Retrieve a memory entry."""
        entry = self._memory_entries.get(key)
        if entry:
            entry["access_count"] += 1
            self._stats["total_memory_ops"] += 1
        return entry

    def list_memories(self, tag: str | None = None) -> list[dict]:
        """List memory entries, optionally filtered by tag."""
        entries = list(self._memory_entries.values())
        if tag:
            entries = [e for e in entries if tag in e.get("tags", [])]
        return entries

    # ── Skill Operations ──

    def add_skill(self, name: str, definition: dict) -> dict:
        """Register a skill in the workspace."""
        if not self.config.isolate_skills:
            return {"error": "Skill isolation disabled"}

        if len(self._skills) >= self.config.max_skills:
            return {"error": "Skill store full"}

        self._skills[name] = {
            "name": name,
            "definition": definition,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "use_count": 0,
        }
        self._log_activity("skill_add", {"name": name})
        return {"success": True, "name": name}

    def list_skills(self) -> list[dict]:
        """List all skills in the workspace."""
        return list(self._skills.values())

    # ── Snapshot Operations ──

    def create_snapshot(self, description: str = "") -> WorkSpaceSnapshot:
        """Create a point-in-time snapshot of the workspace."""
        import uuid
        snapshot_id = str(uuid.uuid4())[:8]
        snapshot = WorkSpaceSnapshot(
            snapshot_id=snapshot_id,
            workspace_id=self.config.workspace_id,
            description=description,
            file_count=len(self._files),
            memory_entries=len(self._memory_entries),
            skill_count=len(self._skills),
        )
        self._snapshots[snapshot_id] = snapshot
        self._log_activity("snapshot_created", {"snapshot_id": snapshot_id})
        return snapshot

    def list_snapshots(self) -> list[dict]:
        """List all snapshots."""
        return [s.to_dict() for s in self._snapshots.values()]

    # ── Stats ──

    def get_stats(self) -> dict:
        """Get comprehensive workspace statistics."""
        return {
            "workspace_id": self.config.workspace_id,
            "name": self.config.name,
            "description": self.config.description,
            "file_count": len(self._files),
            "memory_entries": len(self._memory_entries),
            "skill_count": len(self._skills),
            "snapshot_count": len(self._snapshots),
            "operations": self._stats,
            "activity_count": len(self._activity_log),
            "recent_activity": self._activity_log[-10:],
            "config": self.config.to_dict(),
        }


class WorkSpaceManager:
    """Central manager for all WorkSpaces."""

    def __init__(self):
        self._workspaces: dict[str, WorkSpace] = {}
        self._active_workspace_id: str | None = None
        self._base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".buddy_data", "workspaces")

        # Initialize default workspace
        self._init_default()

    def _init_default(self):
        """Create a default workspace."""
        config = WorkSpaceConfig(
            name="Default",
            description="Default workspace for general tasks",
            workspace_id="default",
            tags=["default"],
        )
        ws = WorkSpace(config, os.path.join(self._base_path, "default"))
        self._workspaces["default"] = ws
        self._active_workspace_id = "default"

    def create(self, name: str, description: str = "", **kwargs) -> WorkSpace:
        """Create a new workspace."""
        import uuid
        ws_id = str(uuid.uuid4())[:8]

        config = WorkSpaceConfig(
            name=name,
            description=description,
            workspace_id=ws_id,
            **kwargs,
        )
        ws = WorkSpace(config, os.path.join(self._base_path, ws_id))
        self._workspaces[ws_id] = ws
        logger.info("Created workspace: %s (%s)", name, ws_id)
        return ws

    def get(self, workspace_id: str) -> WorkSpace | None:
        return self._workspaces.get(workspace_id)

    def get_active(self) -> WorkSpace | None:
        if self._active_workspace_id:
            return self._workspaces.get(self._active_workspace_id)
        return None

    def set_active(self, workspace_id: str) -> bool:
        if workspace_id in self._workspaces:
            self._active_workspace_id = workspace_id
            return True
        return False

    def delete(self, workspace_id: str) -> bool:
        if workspace_id == "default":
            return False
        ws = self._workspaces.pop(workspace_id, None)
        if ws:
            if self._active_workspace_id == workspace_id:
                self._active_workspace_id = "default"
            # Clean up files
            if os.path.exists(ws.base_path):
                shutil.rmtree(ws.base_path, ignore_errors=True)
            logger.info("Deleted workspace: %s", workspace_id)
            return True
        return False

    def list_all(self) -> list[dict]:
        return [
            {
                "workspace_id": ws.config.workspace_id,
                "name": ws.config.name,
                "description": ws.config.description,
                "file_count": len(ws._files),
                "memory_entries": len(ws._memory_entries),
                "skill_count": len(ws._skills),
                "is_active": ws.config.workspace_id == self._active_workspace_id,
                "created_at": ws.config.created_at,
                "tags": ws.config.tags,
            }
            for ws in self._workspaces.values()
        ]

    def get_stats(self) -> dict:
        """Get aggregate workspace manager statistics."""
        total_files = sum(len(ws._files) for ws in self._workspaces.values())
        total_memories = sum(len(ws._memory_entries) for ws in self._workspaces.values())
        total_skills = sum(len(ws._skills) for ws in self._workspaces.values())
        return {
            "total_workspaces": len(self._workspaces),
            "active_workspace": self._active_workspace_id,
            "total_files": total_files,
            "total_memories": total_memories,
            "total_skills": total_skills,
            "workspaces": self.list_all(),
        }


# Global instance
workspace_manager = WorkSpaceManager()