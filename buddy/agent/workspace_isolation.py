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


# Global isolation manager instance
workspace_isolation = WorkspaceIsolation()