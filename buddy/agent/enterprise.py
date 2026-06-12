"""Buddy Enterprise Workspace System — multi-tenant workspace management

Provides enterprise-grade workspace isolation with independent filesystems,
memory stores, and skill registries per workspace. Enables teams to maintain
fully isolated AI agent contexts within a single Buddy deployment.
"""
from __future__ import annotations
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.memory import HierarchicalMemory
from agent.skills import SkillsRegistry

logger = logging.getLogger("buddy.enterprise")


# ── Data Classes ─────────────────────────────────────


@dataclass
class WorkspaceStats:
    """Aggregated statistics for a single workspace."""

    total_files: int = 0
    total_memories: int = 0
    total_skills: int = 0
    last_activity: str = ""


@dataclass
class Workspace:
    """An isolated enterprise workspace with dedicated filesystem, memory, and skills.

    Each workspace is a self-contained environment that prevents cross-workspace
    data leakage at the filesystem, memory, and skill levels.
    """

    id: str
    name: str
    description: str
    filesystem_path: Path
    memory_store: HierarchicalMemory
    skill_set: SkillsRegistry
    created_at: str
    updated_at: str


# ── Enterprise Hub ────────────────────────────────────


class EnterpriseHub:
    """Central manager for multiple isolated enterprise workspaces.

    Each workspace is fully isolated with its own:
    - File system directory under the configurable base directory
    - HierarchicalMemory store scoped to the workspace ID
    - SkillsRegistry for workspace-specific skill registration

    Usage::

        hub = EnterpriseHub()
        dev_ws = hub.create_workspace("dev-team", "Development environment")
        hub.switch_context(dev_ws.id)
        active = hub.get_active_workspace()
    """

    DEFAULT_BASE_DIR_NAME = "workspaces"

    def __init__(self, base_dir: str | Path | None = None):
        """Initialize the enterprise hub.

        Args:
            base_dir: Root directory under which per-workspace directories live.
                      Defaults to ``workspaces/`` relative to the current working directory.
        """
        self._workspaces: dict[str, Workspace] = {}
        self._active_workspace_id: str | None = None

        if base_dir is not None:
            self._base_dir = Path(base_dir)
        else:
            self._base_dir = Path(self.DEFAULT_BASE_DIR_NAME)

        self._base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("EnterpriseHub initialized at %s", self._base_dir.resolve())

    # ── Workspace CRUD ────────────────────────────────

    def create_workspace(self, name: str, description: str = "") -> Workspace:
        """Create a new isolated workspace.

        Automatically creates a dedicated filesystem directory under the hub's
        base directory, initializes a scoped memory store, and provisions a
        blank skill registry for the workspace.

        Args:
            name: Human-readable workspace name.
            description: Optional description of the workspace's purpose.

        Returns:
            The newly created Workspace instance.

        Raises:
            ValueError: If a workspace with the same name already exists.
        """
        # Enforce name uniqueness
        for ws in self._workspaces.values():
            if ws.name == name:
                raise ValueError(f"Workspace with name '{name}' already exists")

        workspace_id = f"ews-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Create isolated filesystem directory
        fs_path = self._base_dir / f"{name}_{workspace_id}"
        fs_path.mkdir(parents=True, exist_ok=True)

        # Create scoped memory store (workspace_id used as agent_id for isolation)
        memory_store = HierarchicalMemory(agent_id=workspace_id)

        # Create isolated skill registry
        skill_set = SkillsRegistry()

        workspace = Workspace(
            id=workspace_id,
            name=name,
            description=description,
            filesystem_path=fs_path,
            memory_store=memory_store,
            skill_set=skill_set,
            created_at=now,
            updated_at=now,
        )

        self._workspaces[workspace_id] = workspace
        logger.info(
            "Workspace created: id=%s name=%s path=%s",
            workspace_id, name, fs_path,
        )
        return workspace

    def get_workspace(self, workspace_id: str) -> Workspace:
        """Retrieve a workspace by its unique identifier.

        Args:
            workspace_id: The workspace's unique ID.

        Returns:
            The matching Workspace instance.

        Raises:
            KeyError: If no workspace exists with the given ID.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {workspace_id}")
        return self._workspaces[workspace_id]

    def list_workspaces(self) -> list[Workspace]:
        """Return all registered workspaces, ordered by creation time (most recent first).

        Returns:
            A list of Workspace instances.
        """
        return sorted(
            self._workspaces.values(),
            key=lambda ws: ws.created_at,
            reverse=True,
        )

    def delete_workspace(self, workspace_id: str) -> None:
        """Permanently delete a workspace and all of its data.

        Removes the workspace's filesystem directory and all its contents,
        then unregisters the workspace from the hub. Memory records stored
        in the database are *not* automatically purged — use the memory
        store's ``clear_layer`` for that.

        Args:
            workspace_id: The workspace's unique ID.

        Raises:
            KeyError: If no workspace exists with the given ID.
        """
        ws = self.get_workspace(workspace_id)

        # Remove filesystem directory
        if ws.filesystem_path.exists():
            shutil.rmtree(ws.filesystem_path)
            logger.info("Workspace filesystem removed: %s", ws.filesystem_path)

        # Clear active reference if this was the active workspace
        if self._active_workspace_id == workspace_id:
            self._active_workspace_id = None

        del self._workspaces[workspace_id]
        logger.info("Workspace deleted: id=%s name=%s", workspace_id, ws.name)

    # ── Context Switching ─────────────────────────────

    def switch_context(self, workspace_id: str) -> None:
        """Set the given workspace as the currently active context.

        Subsequent calls to :meth:`get_active_workspace` will return this workspace.

        Args:
            workspace_id: The workspace's unique ID.

        Raises:
            KeyError: If no workspace exists with the given ID.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Cannot switch to unknown workspace: {workspace_id}")

        previous = self._active_workspace_id
        self._active_workspace_id = workspace_id

        # Touch the updated_at timestamp
        self._workspaces[workspace_id].updated_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Context switched: %s -> %s",
            previous or "(none)", workspace_id,
        )

    def get_active_workspace(self) -> Workspace | None:
        """Return the currently active workspace, or None if no context is set.

        Returns:
            The active Workspace, or None.
        """
        if self._active_workspace_id is None:
            return None
        return self._workspaces.get(self._active_workspace_id)

    # ── Statistics ────────────────────────────────────

    def get_workspace_stats(self, workspace_id: str) -> WorkspaceStats:
        """Compute aggregate statistics for a workspace.

        Counts files on disk, skills in the registry, and retrieves
        memory statistics from the scoped memory store.

        Args:
            workspace_id: The workspace's unique ID.

        Returns:
            A WorkspaceStats dataclass with current counts.

        Raises:
            KeyError: If no workspace exists with the given ID.
        """
        ws = self.get_workspace(workspace_id)

        # Count files recursively under the workspace directory
        total_files = 0
        if ws.filesystem_path.exists():
            total_files = sum(1 for _ in ws.filesystem_path.rglob("*") if _.is_file())

        # Count registered skills
        total_skills = len(ws.skill_set.list())

        # Count memories — this is best-effort since the DB may not be accessible
        total_memories = 0
        try:
            # Use a lightweight heuristic: count entries in the short-term buffer
            total_memories = len(ws.memory_store._short_term_buffer)
        except Exception:
            pass

        return WorkspaceStats(
            total_files=total_files,
            total_memories=total_memories,
            total_skills=total_skills,
            last_activity=ws.updated_at,
        )

    # ── Import / Export ───────────────────────────────

    def export_workspace_config(self, workspace_id: str) -> dict[str, Any]:
        """Export workspace metadata and configuration as a serializable dictionary.

        Includes name, description, and the list of registered skills. Excludes
        memory data and filesystem contents (those must be exported separately).

        Args:
            workspace_id: The workspace's unique ID.

        Returns:
            A dictionary suitable for JSON serialization.

        Raises:
            KeyError: If no workspace exists with the given ID.
        """
        ws = self.get_workspace(workspace_id)

        skills = ws.skill_set.list()

        return {
            "version": "1.0",
            "workspace_id": ws.id,
            "name": ws.name,
            "description": ws.description,
            "created_at": ws.created_at,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "filesystem_path": str(ws.filesystem_path),
            "skills": [{"name": s["name"], "category": s["category"]} for s in skills],
        }

    def export_workspace_config_json(self, workspace_id: str, indent: int = 2) -> str:
        """Export workspace configuration as a JSON string.

        Args:
            workspace_id: The workspace's unique ID.
            indent: JSON indentation level.

        Returns:
            A formatted JSON string.

        Raises:
            KeyError: If no workspace exists with the given ID.
        """
        return json.dumps(self.export_workspace_config(workspace_id), indent=indent)

    def import_workspace_config(self, config: dict[str, Any]) -> Workspace:
        """Create a new workspace from an exported configuration dictionary.

        The workspace name is suffixed with a short random token to avoid
        collisions with existing workspaces. Skills listed in the config are
        not automatically re-registered since they require handler functions;
        only basic metadata skills are created as placeholders.

        Args:
            config: A dictionary previously produced by :meth:`export_workspace_config`.

        Returns:
            The newly created Workspace instance.

        Raises:
            ValueError: If required fields are missing from the config.
        """
        required_fields = ("name",)
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field in config: {field}")

        name = config["name"]
        description = config.get("description", "")
        suffix = uuid.uuid4().hex[:6]
        unique_name = f"{name}_imported_{suffix}"

        workspace = self.create_workspace(name=unique_name, description=description)

        # Register skills from the exported config as stub entries
        for skill_info in config.get("skills", []):
            skill_name = skill_info.get("name", "")
            skill_category = skill_info.get("category", "general")
            if skill_name and not workspace.skill_set.get(skill_name):
                try:
                    workspace.skill_set.register(
                        name=skill_name,
                        description=f"Imported skill: {skill_name}",
                        category=skill_category,
                        parameters={},
                        handler=self._make_imported_skill_handler(skill_name),
                    )
                except Exception:
                    logger.debug("Failed to register imported skill: %s", skill_name)

        logger.info(
            "Workspace imported from config: id=%s name=%s",
            workspace.id, workspace.name,
        )
        return workspace

    def import_workspace_config_json(self, json_str: str) -> Workspace:
        """Create a new workspace from an exported JSON configuration string.

        Args:
            json_str: A JSON string previously produced by
                      :meth:`export_workspace_config_json`.

        Returns:
            The newly created Workspace instance.

        Raises:
            ValueError: If the JSON is invalid or required fields are missing.
        """
        try:
            config = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in workspace config: {exc}") from exc
        return self.import_workspace_config(config)

    @staticmethod
    async def _make_imported_skill_handler(skill_name: str):
        """Create a no-op async handler for imported skills lacking implementations."""

        async def _imported_handler(params: dict[str, Any]) -> str:
            return f"[Imported skill '{skill_name}'] No handler configured. Parameters: {params}"

        return _imported_handler

    # ── Utility ───────────────────────────────────────

    def get_hub_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all workspaces.

        Returns:
            A dictionary with total workspace count, active workspace ID,
            and per-workspace summary counts.
        """
        workspace_list = self.list_workspaces()
        total_files = 0
        for ws in workspace_list:
            if ws.filesystem_path.exists():
                total_files += sum(
                    1 for _ in ws.filesystem_path.rglob("*") if _.is_file()
                )

        return {
            "total_workspaces": len(workspace_list),
            "active_workspace_id": self._active_workspace_id,
            "base_directory": str(self._base_dir.resolve()),
            "total_files_across_workspaces": total_files,
            "workspaces": [
                {
                    "id": ws.id,
                    "name": ws.name,
                    "description": ws.description,
                    "skills_count": len(ws.skill_set.list()),
                    "created_at": ws.created_at,
                    "updated_at": ws.updated_at,
                }
                for ws in workspace_list
            ],
        }


# Global enterprise hub instance
enterprise_hub = EnterpriseHub()