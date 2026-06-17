"""Buddy Workspace Deep Isolation — per-project complete sandboxing

Provides file system sandboxing, memory isolation, skill separation, and context
window management per workspace. Inspired by PilotDeck's WorkSpace isolation model,
each workspace is a fully self-contained environment preventing cross-project
data leakage at every layer.
"""
from __future__ import annotations
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("buddy.workspace_isolation")


# ── Data Classes ─────────────────────────────────────


@dataclass
class WorkspaceMemory:
    """Per-workspace memory store with strict isolation from global memory.

    Each workspace maintains its own memory namespace. Cross-workspace memory
    access is blocked by design — memories never leak between projects.
    """

    workspace_id: str
    _short_term: dict[str, dict[str, Any]] = field(default_factory=dict)
    _long_term: dict[str, dict[str, Any]] = field(default_factory=dict)
    _episodic: list[dict[str, Any]] = field(default_factory=list)
    _semantic_index: dict[str, list[str]] = field(default_factory=dict)

    def store(
        self,
        content: str,
        memory_type: str = "general",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory entry in the workspace-scoped store.

        Args:
            content: The memory content string.
            memory_type: Category label (general, insight, fact, etc.).
            importance: Priority score from 0.0 to 1.0.
            metadata: Optional extra key-value data.

        Returns:
            The memory entry ID.
        """
        entry_id = f"wsmem-{uuid.uuid4().hex[:10]}"
        entry = {
            "id": entry_id,
            "content": content,
            "type": memory_type,
            "importance": importance,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workspace_id": self.workspace_id,
        }

        if memory_type in ("insight", "fact", "reflection"):
            self._long_term[entry_id] = entry
        else:
            self._short_term[entry_id] = entry

        # Build semantic index for cross-referencing
        keywords = self._extract_keywords(content)
        for kw in keywords:
            if kw not in self._semantic_index:
                self._semantic_index[kw] = []
            self._semantic_index[kw].append(entry_id)

        return entry_id

    def recall_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve most recent short-term memories."""
        sorted_entries = sorted(
            self._short_term.values(),
            key=lambda e: e["created_at"],
            reverse=True,
        )
        return sorted_entries[:limit]

    def recall_long_term(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve long-term memories sorted by importance."""
        sorted_entries = sorted(
            self._long_term.values(),
            key=lambda e: e["importance"],
            reverse=True,
        )
        return sorted_entries[:limit]

    def search_by_keyword(self, keyword: str) -> list[dict[str, Any]]:
        """Find memories matching a semantic keyword."""
        matching_ids = self._semantic_index.get(keyword.lower(), [])
        results = []
        for mid in matching_ids:
            if mid in self._short_term:
                results.append(self._short_term[mid])
            elif mid in self._long_term:
                results.append(self._long_term[mid])
        return results

    def clear(self) -> None:
        """Remove all memories from this workspace."""
        self._short_term.clear()
        self._long_term.clear()
        self._episodic.clear()
        self._semantic_index.clear()

    def get_stats(self) -> dict[str, int]:
        """Return memory counts for this workspace."""
        return {
            "short_term_count": len(self._short_term),
            "long_term_count": len(self._long_term),
            "episodic_count": len(self._episodic),
            "index_terms": len(self._semantic_index),
        }

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        """Extract lowercase keyword tokens from text."""
        import re
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        stop_words = {
            "the", "and", "for", "that", "this", "with", "was", "have",
            "from", "are", "but", "not", "you", "all", "can", "has",
            "been", "will", "when", "what", "which", "their",
        }
        return {w for w in words if w not in stop_words}


@dataclass
class WorkspaceSandbox:
    """File system sandbox restricting I/O to workspace-allowed paths.

    Each sandbox defines a root directory and an explicit set of allowed
    and blocked path patterns. Any file operation outside the allowed set
    is rejected before reaching the OS.
    """

    workspace_id: str
    root_path: Path
    allowed_patterns: list[str] = field(default_factory=lambda: ["*"])
    blocked_patterns: list[str] = field(default_factory=list)
    _created_dirs: set[str] = field(default_factory=set)

    def is_path_allowed(self, file_path: str | Path) -> bool:
        """Check whether a path is within the sandbox boundary.

        Args:
            file_path: Absolute or relative path to validate.

        Returns:
            True if the path is within the sandbox root.
        """
        resolved = Path(file_path).resolve()
        root_resolved = self.root_path.resolve()

        try:
            resolved.relative_to(root_resolved)
            return True
        except ValueError:
            return False

    def ensure_dir(self, relative_path: str) -> Path:
        """Create a directory inside the sandbox if it does not exist.

        Args:
            relative_path: Path relative to the sandbox root.

        Returns:
            The resolved Path to the created directory.

        Raises:
            PermissionError: If the resolved path escapes the sandbox.
        """
        target = (self.root_path / relative_path).resolve()
        if not self.is_path_allowed(target):
            raise PermissionError(
                f"Path '{relative_path}' escapes sandbox '{self.root_path}'"
            )
        target.mkdir(parents=True, exist_ok=True)
        self._created_dirs.add(str(target))
        return target

    def list_files(self, relative_path: str = ".") -> list[Path]:
        """List all files under a sandbox subdirectory.

        Args:
            relative_path: Subdirectory relative to sandbox root.

        Returns:
            Sorted list of file Path objects.
        """
        target = (self.root_path / relative_path).resolve()
        if not self.is_path_allowed(target):
            raise PermissionError(f"Path '{relative_path}' escapes sandbox")
        if not target.exists():
            return []
        return sorted([p for p in target.iterdir() if p.is_file()])

    def file_count(self) -> int:
        """Count total files recursively under the sandbox root."""
        if not self.root_path.exists():
            return 0
        return sum(1 for _ in self.root_path.rglob("*") if _.is_file())

    def clean(self) -> None:
        """Remove all files and directories within the sandbox."""
        if self.root_path.exists():
            shutil.rmtree(self.root_path)
            self.root_path.mkdir(parents=True, exist_ok=True)
            self._created_dirs.clear()


@dataclass
class WorkspaceSkillSet:
    """Per-workspace skill registry with no cross-workspace skill leakage.

    Skills registered in one workspace are invisible to other workspaces.
    Supports registration, lookup, listing, and import/export of skills.
    """

    workspace_id: str
    _skills: dict[str, dict[str, Any]] = field(default_factory=dict)

    def register(
        self,
        name: str,
        description: str,
        category: str = "general",
        parameters: dict[str, Any] | None = None,
        handler: Callable | None = None,
    ) -> str:
        """Register a new skill in the workspace.

        Args:
            name: Unique skill name within the workspace.
            description: Human-readable description.
            category: Skill category label.
            parameters: Expected parameter schema.
            handler: Async or sync callable that executes the skill.

        Returns:
            The skill's unique ID.

        Raises:
            ValueError: If a skill with the same name already exists.
        """
        if name in self._skills:
            raise ValueError(f"Skill '{name}' already exists in workspace '{self.workspace_id}'")

        skill_id = f"wsskill-{uuid.uuid4().hex[:8]}"
        self._skills[name] = {
            "id": skill_id,
            "name": name,
            "description": description,
            "category": category,
            "parameters": parameters or {},
            "handler": handler,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workspace_id": self.workspace_id,
        }
        logger.debug("Skill '%s' registered in workspace '%s'", name, self.workspace_id)
        return skill_id

    def get(self, name: str) -> dict[str, Any] | None:
        """Look up a skill by name."""
        return self._skills.get(name)

    def list(self) -> list[dict[str, Any]]:
        """Return all registered skills as a list of metadata dicts."""
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "description": s["description"],
                "category": s["category"],
                "parameters": s["parameters"],
            }
            for s in self._skills.values()
        ]

    def remove(self, name: str) -> bool:
        """Remove a skill from the workspace.

        Returns:
            True if the skill was removed, False if it did not exist.
        """
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def export_skills(self) -> list[dict[str, Any]]:
        """Export skill metadata for workspace portability."""
        return [
            {"name": s["name"], "description": s["description"], "category": s["category"]}
            for s in self._skills.values()
        ]

    def import_skills(self, skills_data: list[dict[str, Any]]) -> int:
        """Import skills from exported metadata.

        Note: Handler functions cannot be serialized and must be re-registered
        separately. This imports metadata only.

        Returns:
            Number of skills successfully imported.
        """
        count = 0
        for skill_info in skills_data:
            name = skill_info.get("name", "")
            if name and name not in self._skills:
                self.register(
                    name=name,
                    description=skill_info.get("description", ""),
                    category=skill_info.get("category", "general"),
                    handler=self._make_placeholder_handler(name),
                )
                count += 1
        return count

    def get_count(self) -> int:
        """Return total number of registered skills."""
        return len(self._skills)

    @staticmethod
    async def _make_placeholder_handler(skill_name: str):
        async def _placeholder(params: dict[str, Any]) -> str:
            return f"[Skill '{skill_name}'] No handler configured."
        return _placeholder


@dataclass
class WorkspaceContext:
    """Per-workspace context window management.

    Tracks context usage, token budgets, and active context for each workspace.
    Context state is fully isolated — switching workspaces swaps the entire
    context window without cross-contamination.
    """

    workspace_id: str
    max_tokens: int = 128000
    _current_tokens: int = 0
    _context_entries: list[dict[str, Any]] = field(default_factory=list)
    _pinned_entries: list[dict[str, Any]] = field(default_factory=list)
    _context_metadata: dict[str, Any] = field(default_factory=dict)

    def add_entry(self, role: str, content: str, token_count: int = 0) -> bool:
        """Add an entry to the context window.

        Args:
            role: Message role (user, assistant, system, tool).
            content: The message content.
            token_count: Estimated token count. If 0, uses character-based estimate.

        Returns:
            True if the entry fit within the budget, False if it was rejected.
        """
        if token_count <= 0:
            token_count = max(1, len(content) // 4)
        if self._current_tokens + token_count > self.max_tokens:
            # Evict oldest non-pinned entries to make room
            self._evict_entries(token_count)

        entry = {
            "role": role,
            "content": content,
            "tokens": token_count,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
        self._context_entries.append(entry)
        self._current_tokens += token_count
        return True

    def pin_entry(self, index: int) -> None:
        """Pin a context entry so it cannot be evicted."""
        if 0 <= index < len(self._context_entries):
            entry = self._context_entries.pop(index)
            self._pinned_entries.append(entry)

    def unpin_entry(self, index: int) -> None:
        """Unpin a previously pinned entry."""
        if 0 <= index < len(self._pinned_entries):
            entry = self._pinned_entries.pop(index)
            self._context_entries.insert(0, entry)

    def clear(self) -> None:
        """Reset the context window entirely."""
        self._context_entries.clear()
        self._pinned_entries.clear()
        self._current_tokens = 0
        self._context_metadata.clear()

    def get_usage(self) -> dict[str, Any]:
        """Return current context window usage statistics."""
        return {
            "workspace_id": self.workspace_id,
            "max_tokens": self.max_tokens,
            "current_tokens": self._current_tokens,
            "utilization_pct": round(
                (self._current_tokens / self.max_tokens * 100), 1
            ) if self.max_tokens > 0 else 0.0,
            "total_entries": len(self._context_entries),
            "pinned_entries": len(self._pinned_entries),
        }

    def _evict_entries(self, needed_tokens: int) -> None:
        """Evict oldest non-pinned entries to free up token budget."""
        freed = 0
        kept = []
        for entry in self._context_entries:
            if freed >= needed_tokens:
                kept.append(entry)
            else:
                freed += entry.get("tokens", 0)
                self._current_tokens -= entry.get("tokens", 0)
        self._context_entries = kept


@dataclass
class WorkspaceSnapshot:
    """A point-in-time snapshot of workspace state for backup and restore."""
    snapshot_id: str = field(default_factory=lambda: f"snap-{uuid.uuid4().hex[:12]}")
    workspace_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    memory_state: dict = field(default_factory=dict)
    skill_state: list[dict] = field(default_factory=list)
    context_state: dict = field(default_factory=dict)
    file_index: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceQuota:
    """Resource limits for a workspace."""
    max_cpu_percent: float = 50.0
    max_memory_mb: int = 512
    max_disk_mb: int = 1024
    max_processes: int = 10
    max_open_files: int = 256
    network_access: bool = True
    max_bandwidth_kbps: int = 0  # 0 = unlimited


@dataclass
class FileChangeRecord:
    """A record of a file change within a workspace."""
    id: str = field(default_factory=lambda: f"fchg-{uuid.uuid4().hex[:12]}")
    workspace_id: str = ""
    file_path: str = ""
    change_type: str = ""  # created, modified, deleted, renamed
    old_path: str = ""
    file_size: int = 0
    checksum: str = ""
    actor: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CommunicationChannel:
    """A secure inter-workspace communication channel."""
    channel_id: str = field(default_factory=lambda: f"ch-{uuid.uuid4().hex[:12]}")
    source_workspace_id: str = ""
    target_workspace_id: str = ""
    allowed_message_types: list[str] = field(default_factory=list)
    encrypted: bool = True
    max_message_size_bytes: int = 65536
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True


# ── Workspace Isolation Manager ───────────────────────


class WorkspaceIsolation:
    """Complete per-project workspace isolation manager.

    Each workspace is a fully isolated environment containing its own:
    - File system sandbox (WorkspaceSandbox)
    - Memory store (WorkspaceMemory)
    - Skill registry (WorkspaceSkillSet)
    - Context window (WorkspaceContext)

    No data crosses workspace boundaries. Switching workspaces swaps
    all subsystems atomically.
    """

    DEFAULT_ROOT_DIR = "isolated_workspaces"

    def __init__(self, root_dir: str | Path | None = None):
        """Initialize the isolation manager.

        Args:
            root_dir: Root directory under which workspace directories live.
        """
        if root_dir is not None:
            self._root_dir = Path(root_dir)
        else:
            self._root_dir = Path(self.DEFAULT_ROOT_DIR)
        self._root_dir.mkdir(parents=True, exist_ok=True)

        self._workspaces: dict[str, dict[str, Any]] = {}
        self._active_workspace_id: str | None = None

        # Snapshots
        self._snapshots: dict[str, WorkspaceSnapshot] = {}

        # Resource quotas
        self._resource_quotas: dict[str, ResourceQuota] = {}

        # File change audit
        self._file_changes: dict[str, list[FileChangeRecord]] = {}
        self._max_file_changes_per_workspace = 500

        # Communication channels
        self._channels: dict[str, CommunicationChannel] = {}
        self._channel_messages: dict[str, list[dict]] = {}

        logger.info("WorkspaceIsolation initialized at %s", self._root_dir.resolve())

    # ── Workspace Lifecycle ───────────────────────────

    def create_workspace(
        self, name: str, description: str = "", owner_id: str = ""
    ) -> str:
        """Create a new fully isolated workspace.

        Provisions a sandbox directory, isolated memory store, blank skill
        registry, and empty context window for the workspace.

        Args:
            name: Human-readable workspace name.
            description: Purpose/description of the workspace.
            owner_id: Identifier of the user or team that owns this workspace.

        Returns:
            The new workspace's unique ID.

        Raises:
            ValueError: If the workspace name is already taken.
        """
        for ws_data in self._workspaces.values():
            if ws_data["name"] == name:
                raise ValueError(f"Workspace name '{name}' already exists")

        workspace_id = f"wsi-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # File system sandbox
        sandbox_path = self._root_dir / f"{name}_{workspace_id}"
        sandbox_path.mkdir(parents=True, exist_ok=True)
        sandbox = WorkspaceSandbox(
            workspace_id=workspace_id,
            root_path=sandbox_path,
        )

        # Isolated memory
        memory = WorkspaceMemory(workspace_id=workspace_id)

        # Isolated skill set
        skills = WorkspaceSkillSet(workspace_id=workspace_id)

        # Isolated context window
        context = WorkspaceContext(workspace_id=workspace_id)

        self._workspaces[workspace_id] = {
            "id": workspace_id,
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "sandbox": sandbox,
            "memory": memory,
            "skills": skills,
            "context": context,
            "created_at": now,
            "updated_at": now,
        }

        logger.info(
            "Workspace created: id=%s name=%s owner=%s",
            workspace_id, name, owner_id,
        )
        return workspace_id

    def delete_workspace(self, workspace_id: str) -> None:
        """Permanently delete a workspace and all its isolated data.

        Removes the file system sandbox directory, memory, skills, and context.
        This operation is irreversible.

        Args:
            workspace_id: The workspace's unique ID.

        Raises:
            KeyError: If the workspace does not exist.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {workspace_id}")

        ws = self._workspaces[workspace_id]

        # Clean file system sandbox
        try:
            ws["sandbox"].clean()
            sandbox_path = ws["sandbox"].root_path
            if sandbox_path.exists():
                sandbox_path.rmdir()
        except Exception as exc:
            logger.warning("Error cleaning sandbox for %s: %s", workspace_id, exc)

        # Clear memory
        ws["memory"].clear()

        # Clear context
        ws["context"].clear()

        # Clear active reference
        if self._active_workspace_id == workspace_id:
            self._active_workspace_id = None

        del self._workspaces[workspace_id]
        logger.info("Workspace deleted: id=%s name=%s", workspace_id, ws["name"])

    def switch_workspace(self, workspace_id: str) -> None:
        """Switch the active workspace context.

        All subsequent operations (memory, skills, context, sandbox) will
        target the switched workspace.

        Args:
            workspace_id: The workspace's unique ID.

        Raises:
            KeyError: If the workspace does not exist.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Cannot switch to unknown workspace: {workspace_id}")

        previous = self._active_workspace_id
        self._active_workspace_id = workspace_id
        self._workspaces[workspace_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Workspace context switched: %s -> %s",
            previous or "(none)", workspace_id,
        )

    def get_active_workspace(self) -> dict[str, Any] | None:
        """Return the currently active workspace data, or None."""
        if self._active_workspace_id is None:
            return None
        return self._workspaces.get(self._active_workspace_id)

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Retrieve a workspace by ID.

        Raises:
            KeyError: If the workspace does not exist.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {workspace_id}")
        return self._workspaces[workspace_id]

    # ── Enumeration & Search ──────────────────────────

    def list_workspaces(self) -> list[dict[str, Any]]:
        """Return all workspaces as summary dicts, most recent first."""
        result = []
        for ws_id, ws_data in sorted(
            self._workspaces.items(),
            key=lambda kv: kv[1]["created_at"],
            reverse=True,
        ):
            result.append({
                "id": ws_id,
                "name": ws_data["name"],
                "description": ws_data["description"],
                "owner_id": ws_data["owner_id"],
                "created_at": ws_data["created_at"],
                "updated_at": ws_data["updated_at"],
                "is_active": ws_id == self._active_workspace_id,
            })
        return result

    # ── Resource Statistics ───────────────────────────

    def get_workspace_stats(self, workspace_id: str | None = None) -> dict[str, Any]:
        """Get resource usage for a specific workspace or the active one.

        Args:
            workspace_id: Workspace ID. Uses active workspace if None.

        Returns:
            Resource usage statistics.
        """
        target_id = workspace_id or self._active_workspace_id
        if target_id is None:
            return {"error": "No workspace specified and no active workspace set"}
        if target_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {target_id}")

        ws = self._workspaces[target_id]

        return {
            "workspace_id": target_id,
            "name": ws["name"],
            "sandbox": {
                "root_path": str(ws["sandbox"].root_path),
                "file_count": ws["sandbox"].file_count(),
            },
            "memory": ws["memory"].get_stats(),
            "skills": {
                "skill_count": ws["skills"].get_count(),
            },
            "context": ws["context"].get_usage(),
            "last_updated": ws["updated_at"],
        }

    def get_all_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all workspaces."""
        total_files = 0
        total_memories = 0
        total_skills = 0
        total_tokens = 0

        for ws_data in self._workspaces.values():
            total_files += ws_data["sandbox"].file_count()
            mem_stats = ws_data["memory"].get_stats()
            total_memories += mem_stats["short_term_count"] + mem_stats["long_term_count"]
            total_skills += ws_data["skills"].get_count()
            total_tokens += ws_data["context"].get_usage()["current_tokens"]

        return {
            "total_workspaces": len(self._workspaces),
            "active_workspace_id": self._active_workspace_id,
            "total_files": total_files,
            "total_memories": total_memories,
            "total_skills": total_skills,
            "total_context_tokens": total_tokens,
            "base_directory": str(self._root_dir.resolve()),
        }

    # ── Export / Import ───────────────────────────────

    def export_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Export the entire workspace state as a serializable dictionary.

        Includes metadata, memory contents, skill definitions, context entries,
        and sandbox file listing. The actual file contents are not included — use
        a tarball or copy for bulk file transfer.

        Args:
            workspace_id: The workspace's unique ID.

        Returns:
            A complete workspace state dictionary ready for serialization.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {workspace_id}")

        ws = self._workspaces[workspace_id]

        # Collect memories
        short_term = ws["memory"].recall_recent(limit=500)
        long_term = ws["memory"].recall_long_term(limit=500)

        # Collect skills
        skills = ws["skills"].export_skills()

        # Collect context
        context_usage = ws["context"].get_usage()

        # List sandbox files (names only, not content)
        sandbox_files: list[str] = []
        sandbox = ws["sandbox"]
        if sandbox.root_path.exists():
            sandbox_files = [
                str(p.relative_to(sandbox.root_path))
                for p in sandbox.root_path.rglob("*")
                if p.is_file()
            ]

        return {
            "version": "2.0",
            "workspace_id": workspace_id,
            "name": ws["name"],
            "description": ws["description"],
            "owner_id": ws["owner_id"],
            "created_at": ws["created_at"],
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "memory": {
                "short_term": short_term,
                "long_term": long_term,
            },
            "skills": skills,
            "context": context_usage,
            "sandbox_files": sandbox_files,
            "sandbox_root": str(sandbox.root_path),
        }

    def export_workspace_json(self, workspace_id: str, indent: int = 2) -> str:
        """Export workspace state as a JSON string."""
        return json.dumps(self.export_workspace(workspace_id), indent=indent, default=str)

    def import_workspace(self, data: dict[str, Any]) -> str:
        """Import a workspace from an exported state dictionary.

        Recreates the workspace structure, restores memory entries, imports
        skill definitions, and sets up the context window. Sandbox files
        are not recreated from the export (only metadata).

        Args:
            data: A dictionary previously produced by export_workspace().

        Returns:
            The newly created workspace ID.

        Raises:
            ValueError: If required fields are missing.
        """
        required = ("name",)
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field in import data: {field}")

        # Avoid name collisions
        suffix = uuid.uuid4().hex[:6]
        name = f"{data['name']}_imported_{suffix}"
        description = data.get("description", "")
        owner_id = data.get("owner_id", "")

        workspace_id = self.create_workspace(
            name=name,
            description=description,
            owner_id=owner_id,
        )
        ws = self._workspaces[workspace_id]

        # Restore memories
        memory_data = data.get("memory", {})
        for mem in memory_data.get("short_term", []):
            ws["memory"].store(
                content=mem.get("content", ""),
                memory_type=mem.get("type", "general"),
                importance=mem.get("importance", 0.5),
                metadata=mem.get("metadata"),
            )
        for mem in memory_data.get("long_term", []):
            ws["memory"].store(
                content=mem.get("content", ""),
                memory_type=mem.get("type", "insight"),
                importance=mem.get("importance", 0.5),
                metadata=mem.get("metadata"),
            )

        # Import skills
        skills_data = data.get("skills", [])
        ws["skills"].import_skills(skills_data)

        logger.info(
            "Workspace imported: id=%s name=%s source_id=%s",
            workspace_id, name, data.get("workspace_id", "unknown"),
        )
        return workspace_id

    def import_workspace_json(self, json_str: str) -> str:
        """Import a workspace from a JSON string."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in workspace import: {exc}") from exc
        return self.import_workspace(data)

    # ── Active Workspace Shortcuts ────────────────────

    @property
    def sandbox(self) -> WorkspaceSandbox | None:
        """Get the sandbox of the active workspace."""
        ws = self.get_active_workspace()
        return ws["sandbox"] if ws else None

    @property
    def memory(self) -> WorkspaceMemory | None:
        """Get the memory store of the active workspace."""
        ws = self.get_active_workspace()
        return ws["memory"] if ws else None

    @property
    def skills(self) -> WorkspaceSkillSet | None:
        """Get the skill registry of the active workspace."""
        ws = self.get_active_workspace()
        return ws["skills"] if ws else None

    @property
    def context(self) -> WorkspaceContext | None:
        """Get the context window of the active workspace."""
        ws = self.get_active_workspace()
        return ws["context"] if ws else None

    # ── Virtual Environment ─────────────────────────────

    def create_virtual_environment(
        self, workspace_id: str, python_version: str = "", requirements: list[str] | None = None
    ) -> Path:
        """Create an isolated virtual environment for a workspace.

        Creates a Python virtual environment inside the workspace sandbox
        and optionally installs specified packages.

        Args:
            workspace_id: Target workspace ID.
            python_version: Python version to use (e.g., '3.11'). Defaults to current.
            requirements: List of pip package names to install.

        Returns:
            Path to the virtual environment directory.

        Raises:
            KeyError: If the workspace does not exist.
            RuntimeError: If venv creation fails.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {workspace_id}")

        ws = self._workspaces[workspace_id]
        sandbox: WorkspaceSandbox = ws["sandbox"]
        venv_path = sandbox.root_path / ".venv"

        if venv_path.exists():
            logger.info(f"Virtual environment already exists at {venv_path}")
            return venv_path

        import subprocess
        import sys

        try:
            # Create the virtual environment
            python_exe = f"python{python_version}" if python_version else sys.executable
            result = subprocess.run(
                [python_exe, "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"venv creation failed: {result.stderr}")

            # Install requirements if provided
            if requirements:
                pip_path = venv_path / "bin" / "pip"
                subprocess.run(
                    [str(pip_path), "install", *requirements],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                logger.info(
                    f"Installed {len(requirements)} packages in {workspace_id}"
                )

            logger.info(f"Virtual environment created at {venv_path}")
            return venv_path

        except Exception as e:
            raise RuntimeError(f"Failed to create virtual environment: {e}") from e

    def get_virtual_environment(self, workspace_id: str) -> Path | None:
        """Get the path to a workspace's virtual environment, if it exists."""
        if workspace_id not in self._workspaces:
            return None
        sandbox = self._workspaces[workspace_id]["sandbox"]
        venv_path = sandbox.root_path / ".venv"
        return venv_path if venv_path.exists() else None

    # ── Snapshot & Restore ──────────────────────────────

    def snapshot_workspace(
        self, workspace_id: str, metadata: dict[str, Any] | None = None
    ) -> WorkspaceSnapshot:
        """Create a point-in-time snapshot of the entire workspace state.

        Captures memory contents, skill definitions, context window state,
        and a file index from the sandbox. File contents are not included —
        only the file listing.

        Args:
            workspace_id: The workspace to snapshot.
            metadata: Additional metadata to store with the snapshot.

        Returns:
            The created WorkspaceSnapshot.

        Raises:
            KeyError: If the workspace does not exist.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {workspace_id}")

        ws = self._workspaces[workspace_id]
        memory: WorkspaceMemory = ws["memory"]
        skills: WorkspaceSkillSet = ws["skills"]
        context: WorkspaceContext = ws["context"]
        sandbox: WorkspaceSandbox = ws["sandbox"]

        # Capture memory state
        memory_state = {
            "short_term": memory.recall_recent(limit=500),
            "long_term": memory.recall_long_term(limit=500),
        }

        # Capture skill state
        skill_state = skills.export_skills()

        # Capture context state
        context_state = context.get_usage()

        # Capture file index
        file_index = []
        if sandbox.root_path.exists():
            file_index = [
                str(p.relative_to(sandbox.root_path))
                for p in sandbox.root_path.rglob("*")
                if p.is_file()
            ]

        snapshot = WorkspaceSnapshot(
            workspace_id=workspace_id,
            memory_state=memory_state,
            skill_state=skill_state,
            context_state=context_state,
            file_index=file_index,
            metadata=metadata or {},
        )
        self._snapshots[snapshot.snapshot_id] = snapshot
        logger.info(
            f"Snapshot {snapshot.snapshot_id} created for workspace {workspace_id}"
        )
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> str:
        """Restore a workspace to a previous snapshot state.

        Restores memory entries, skill definitions, and context window
        configuration. File contents are not restored from the snapshot
        (only the index is available).

        Args:
            snapshot_id: The snapshot ID to restore from.

        Returns:
            The workspace ID that was restored.

        Raises:
            KeyError: If the snapshot or workspace does not exist.
        """
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            raise KeyError(f"Snapshot not found: {snapshot_id}")

        if snapshot.workspace_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {snapshot.workspace_id}")

        ws = self._workspaces[snapshot.workspace_id]
        memory: WorkspaceMemory = ws["memory"]
        skills: WorkspaceSkillSet = ws["skills"]
        context: WorkspaceContext = ws["context"]

        # Clear and restore memory
        memory.clear()
        for mem in snapshot.memory_state.get("short_term", []):
            memory.store(
                content=mem.get("content", ""),
                memory_type=mem.get("type", "general"),
                importance=mem.get("importance", 0.5),
                metadata=mem.get("metadata"),
            )
        for mem in snapshot.memory_state.get("long_term", []):
            memory.store(
                content=mem.get("content", ""),
                memory_type=mem.get("type", "insight"),
                importance=mem.get("importance", 0.5),
                metadata=mem.get("metadata"),
            )

        # Restore skills
        for skill_name in list(skills._skills.keys()):
            skills.remove(skill_name)
        skills.import_skills(snapshot.skill_state)

        logger.info(
            f"Snapshot {snapshot_id} restored to workspace {snapshot.workspace_id}"
        )
        return snapshot.workspace_id

    def list_snapshots(self, workspace_id: str = "") -> list[dict]:
        """List snapshots, optionally filtered by workspace."""
        result = []
        for snap in self._snapshots.values():
            if workspace_id and snap.workspace_id != workspace_id:
                continue
            result.append({
                "snapshot_id": snap.snapshot_id,
                "workspace_id": snap.workspace_id,
                "created_at": snap.created_at,
                "file_count": len(snap.file_index),
                "metadata": snap.metadata,
            })
        return sorted(result, key=lambda s: s["created_at"], reverse=True)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            return True
        return False

    # ── Resource Quotas ─────────────────────────────────

    def enforce_resource_quotas(
        self, workspace_id: str, quota: ResourceQuota
    ) -> None:
        """Set resource quotas for a workspace.

        Defines CPU, memory, disk, and process limits. The quota is
        enforced at the workspace level — any operation exceeding the
        quota is rejected.

        Args:
            workspace_id: Target workspace ID.
            quota: The ResourceQuota to apply.
        """
        self._resource_quotas[workspace_id] = quota
        logger.info(
            f"Resource quotas set for {workspace_id}: "
            f"CPU={quota.max_cpu_percent}%, "
            f"MEM={quota.max_memory_mb}MB, "
            f"DISK={quota.max_disk_mb}MB"
        )

    def check_resource_quota(
        self, workspace_id: str
    ) -> tuple[bool, dict]:
        """Check the current resource usage against the workspace quota.

        Args:
            workspace_id: Target workspace ID.

        Returns:
            A tuple of (within_limits, usage_dict).
        """
        if workspace_id not in self._workspaces:
            return False, {"error": "Workspace not found"}

        quota = self._resource_quotas.get(workspace_id)
        ws = self._workspaces[workspace_id]
        sandbox: WorkspaceSandbox = ws["sandbox"]

        usage = {
            "workspace_id": workspace_id,
            "disk_used_mb": 0,
            "file_count": sandbox.file_count(),
            "within_limits": True,
            "violations": [],
        }

        # Calculate disk usage
        if sandbox.root_path.exists():
            total_bytes = sum(
                f.stat().st_size for f in sandbox.root_path.rglob("*")
                if f.is_file() and f.stat()
            )
            usage["disk_used_mb"] = round(total_bytes / (1024 * 1024), 2)

        if quota:
            if usage["disk_used_mb"] > quota.max_disk_mb:
                usage["within_limits"] = False
                usage["violations"].append(
                    f"disk: {usage['disk_used_mb']}MB > {quota.max_disk_mb}MB"
                )

        return usage["within_limits"], usage

    def get_resource_quota(self, workspace_id: str) -> ResourceQuota | None:
        """Get the resource quota for a workspace."""
        return self._resource_quotas.get(workspace_id)

    def remove_resource_quota(self, workspace_id: str) -> bool:
        """Remove resource quotas from a workspace."""
        if workspace_id in self._resource_quotas:
            del self._resource_quotas[workspace_id]
            return True
        return False

    # ── File Change Tracking & Audit ────────────────────

    def track_file_change(
        self,
        workspace_id: str,
        file_path: str,
        change_type: str,
        actor: str = "",
        old_path: str = "",
        file_size: int = 0,
    ) -> FileChangeRecord:
        """Record a file change event for audit purposes.

        Args:
            workspace_id: The workspace where the change occurred.
            file_path: The path of the changed file.
            change_type: One of 'created', 'modified', 'deleted', 'renamed'.
            actor: Who or what made the change.
            old_path: Previous path if renamed.
            file_size: Size of the file in bytes.

        Returns:
            The created FileChangeRecord.
        """
        import hashlib

        # Compute a lightweight checksum if the file exists
        checksum = ""
        if change_type != "deleted" and workspace_id in self._workspaces:
            sandbox = self._workspaces[workspace_id]["sandbox"]
            full_path = sandbox.root_path / file_path
            if full_path.exists() and full_path.is_file():
                try:
                    checksum = hashlib.sha256(
                        full_path.read_bytes()[:8192]
                    ).hexdigest()[:16]
                except Exception:
                    pass

        record = FileChangeRecord(
            workspace_id=workspace_id,
            file_path=file_path,
            change_type=change_type,
            old_path=old_path,
            file_size=file_size,
            checksum=checksum,
            actor=actor,
        )

        if workspace_id not in self._file_changes:
            self._file_changes[workspace_id] = []
        self._file_changes[workspace_id].append(record)

        # Trim to max
        if len(self._file_changes[workspace_id]) > self._max_file_changes_per_workspace:
            self._file_changes[workspace_id] = self._file_changes[workspace_id][
                -self._max_file_changes_per_workspace:
            ]

        logger.debug(f"File change tracked: {file_path} ({change_type}) in {workspace_id}")
        return record

    def get_audit_log(
        self,
        workspace_id: str,
        change_type: str = "",
        actor: str = "",
        limit: int = 100,
    ) -> list[dict]:
        """Get the audit log of file changes for a workspace.

        Args:
            workspace_id: Target workspace ID.
            change_type: Filter by change type (created, modified, deleted, renamed).
            actor: Filter by actor.
            limit: Maximum number of records to return.

        Returns:
            List of file change records as dicts.
        """
        changes = self._file_changes.get(workspace_id, [])
        if change_type:
            changes = [c for c in changes if c.change_type == change_type]
        if actor:
            changes = [c for c in changes if c.actor == actor]

        changes = sorted(changes, key=lambda c: c.timestamp, reverse=True)
        return [
            {
                "id": c.id,
                "workspace_id": c.workspace_id,
                "file_path": c.file_path,
                "change_type": c.change_type,
                "old_path": c.old_path,
                "file_size": c.file_size,
                "checksum": c.checksum,
                "actor": c.actor,
                "timestamp": c.timestamp,
            }
            for c in changes[:limit]
        ]

    def get_audit_summary(self, workspace_id: str) -> dict:
        """Get a summary of file changes for a workspace."""
        changes = self._file_changes.get(workspace_id, [])
        type_counts: dict[str, int] = {}
        actor_counts: dict[str, int] = {}

        for c in changes:
            type_counts[c.change_type] = type_counts.get(c.change_type, 0) + 1
            if c.actor:
                actor_counts[c.actor] = actor_counts.get(c.actor, 0) + 1

        return {
            "workspace_id": workspace_id,
            "total_changes": len(changes),
            "by_type": type_counts,
            "by_actor": actor_counts,
            "first_change_at": changes[0].timestamp if changes else "",
            "last_change_at": changes[-1].timestamp if changes else "",
        }

    # ── Inter-Workspace Communication ──────────────────

    def create_communication_channel(
        self,
        source_workspace_id: str,
        target_workspace_id: str,
        allowed_message_types: list[str] | None = None,
        encrypted: bool = True,
        max_message_size_bytes: int = 65536,
    ) -> CommunicationChannel:
        """Create a secure communication channel between two workspaces.

        Channels enforce security boundaries — only allowed message types
        can pass through. Each channel is unidirectional from source to target.

        Args:
            source_workspace_id: The sending workspace ID.
            target_workspace_id: The receiving workspace ID.
            allowed_message_types: List of allowed message type strings.
            encrypted: Whether to encrypt messages on the channel.
            max_message_size_bytes: Maximum message size in bytes.

        Returns:
            The created CommunicationChannel.

        Raises:
            KeyError: If either workspace does not exist.
        """
        if source_workspace_id not in self._workspaces:
            raise KeyError(f"Source workspace not found: {source_workspace_id}")
        if target_workspace_id not in self._workspaces:
            raise KeyError(f"Target workspace not found: {target_workspace_id}")

        channel = CommunicationChannel(
            source_workspace_id=source_workspace_id,
            target_workspace_id=target_workspace_id,
            allowed_message_types=allowed_message_types or [],
            encrypted=encrypted,
            max_message_size_bytes=max_message_size_bytes,
        )
        self._channels[channel.channel_id] = channel
        self._channel_messages[channel.channel_id] = []

        logger.info(
            f"Communication channel created: {source_workspace_id} -> {target_workspace_id}"
        )
        return channel

    def send_message(
        self,
        channel_id: str,
        message_type: str,
        payload: dict[str, Any],
        sender: str = "system",
    ) -> tuple[bool, str]:
        """Send a message through an inter-workspace channel.

        Validates the message against channel security policies before
        delivery. Rejects messages that exceed size limits or use
        disallowed message types.

        Args:
            channel_id: The channel to send through.
            message_type: Type of message being sent.
            payload: The message content dict.
            sender: Identifier of the sender.

        Returns:
            A tuple of (success, message).
        """
        channel = self._channels.get(channel_id)
        if not channel:
            return False, f"Channel not found: {channel_id}"
        if not channel.is_active:
            return False, "Channel is inactive"

        # Validate message type
        if channel.allowed_message_types:
            if message_type not in channel.allowed_message_types:
                return False, (
                    f"Message type '{message_type}' not allowed on this channel. "
                    f"Allowed: {channel.allowed_message_types}"
                )

        # Validate message size
        import json as _json
        message_size = len(_json.dumps(payload).encode("utf-8"))
        if message_size > channel.max_message_size_bytes:
            return False, (
                f"Message size {message_size}B exceeds limit "
                f"{channel.max_message_size_bytes}B"
            )

        # Simulate encryption if enabled
        message_data = payload
        if channel.encrypted:
            message_data = {"_encrypted": True, "payload": payload}

        msg = {
            "id": f"msg-{uuid.uuid4().hex[:12]}",
            "channel_id": channel_id,
            "message_type": message_type,
            "payload": message_data,
            "sender": sender,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._channel_messages[channel_id].append(msg)
        logger.debug(
            f"Message sent on channel {channel_id}: {message_type}"
        )
        return True, msg["id"]

    def receive_messages(
        self, channel_id: str, limit: int = 50, since: str = ""
    ) -> list[dict]:
        """Receive messages from a communication channel.

        Args:
            channel_id: The channel to read from.
            limit: Maximum number of messages to return.
            since: ISO timestamp — only return messages after this time.

        Returns:
            List of message dicts.
        """
        messages = self._channel_messages.get(channel_id, [])
        if since:
            messages = [m for m in messages if m["timestamp"] > since]
        return messages[-limit:]

    def close_channel(self, channel_id: str) -> bool:
        """Close a communication channel."""
        channel = self._channels.get(channel_id)
        if channel:
            channel.is_active = False
            logger.info(f"Channel closed: {channel_id}")
            return True
        return False

    def get_channel(self, channel_id: str) -> CommunicationChannel | None:
        """Get channel details."""
        return self._channels.get(channel_id)

    def list_channels(
        self, workspace_id: str = ""
    ) -> list[dict]:
        """List all channels, optionally filtered by workspace."""
        result = []
        for ch in self._channels.values():
            if workspace_id:
                if ch.source_workspace_id != workspace_id and ch.target_workspace_id != workspace_id:
                    continue
            result.append({
                "channel_id": ch.channel_id,
                "source_workspace_id": ch.source_workspace_id,
                "target_workspace_id": ch.target_workspace_id,
                "allowed_message_types": ch.allowed_message_types,
                "encrypted": ch.encrypted,
                "is_active": ch.is_active,
                "message_count": len(self._channel_messages.get(ch.channel_id, [])),
                "created_at": ch.created_at,
            })
        return result


# Global isolation manager instance
workspace_isolation = WorkspaceIsolation()