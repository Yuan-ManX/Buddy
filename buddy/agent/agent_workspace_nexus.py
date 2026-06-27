"""
Buddy Agent Workspace Nexus — Unified Workspace Orchestration

Connects all agent subsystems through a central workspace registry, providing
context flow, subsystem connection management, and workspace analytics. The
Nexus serves as the coordination layer between workspaces and the agent
ecosystem: memory, skills, tools, agents, and knowledge graph.

Architecture:
  - Workspace Registry Layer: lifecycle management and metadata
  - Subsystem Connection Layer: bind subsystems to workspaces
  - Context Flow Layer: manage context across subsystem boundaries
  - Workspace Analytics Layer: productivity, resource, and health metrics
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ──


class WorkspaceStatus(str, Enum):
    """Lifecycle status of a workspace."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DELETED = "deleted"


class SubsystemType(str, Enum):
    """Types of subsystems that can connect to a workspace."""
    MEMORY = "memory"
    SKILLS = "skills"
    TOOLS = "tools"
    AGENTS = "agents"
    KNOWLEDGE = "knowledge"


class ConnectionStatus(str, Enum):
    """Status of a subsystem connection."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    PENDING = "pending"


class ContextPriority(str, Enum):
    """Priority level for context flows."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Data Classes ──


@dataclass
class Workspace:
    """A workspace instance managed by the Nexus registry."""
    workspace_id: str
    name: str
    description: str = ""
    status: WorkspaceStatus = WorkspaceStatus.INACTIVE
    template_id: str = ""
    agent_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "template_id": self.template_id,
            "agent_ids": self.agent_ids,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class WorkspaceTemplate:
    """A configurable template for workspace creation."""
    template_id: str
    name: str
    default_tools: list[str] = field(default_factory=list)
    default_skills: list[str] = field(default_factory=list)
    default_prompt: str = ""
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "default_tools": self.default_tools,
            "default_skills": self.default_skills,
            "default_prompt": self.default_prompt,
            "settings": self.settings,
        }


@dataclass
class SubsystemConnection:
    """A connection binding a subsystem to a workspace."""
    connection_id: str
    workspace_id: str
    subsystem_type: SubsystemType
    subsystem_id: str
    config: dict[str, Any] = field(default_factory=dict)
    status: ConnectionStatus = ConnectionStatus.PENDING
    established_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_sync_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "workspace_id": self.workspace_id,
            "subsystem_type": self.subsystem_type.value,
            "subsystem_id": self.subsystem_id,
            "config": self.config,
            "status": self.status.value,
            "established_at": self.established_at,
            "last_sync_at": self.last_sync_at,
        }


@dataclass
class ContextFlow:
    """A context transfer between two subsystems within a workspace."""
    flow_id: str
    workspace_id: str
    source_subsystem: SubsystemType
    target_subsystem: SubsystemType
    content: dict[str, Any] = field(default_factory=dict)
    priority: ContextPriority = ContextPriority.MEDIUM
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "workspace_id": self.workspace_id,
            "source_subsystem": self.source_subsystem.value,
            "target_subsystem": self.target_subsystem.value,
            "content": self.content,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
        }


@dataclass
class WorkspaceAnalytics:
    """Analytics snapshot for a single workspace."""
    workspace_id: str
    productivity_score: float = 0.0
    resource_usage: dict[str, Any] = field(default_factory=dict)
    collaboration_index: float = 0.0
    health_status: str = "unknown"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "productivity_score": self.productivity_score,
            "resource_usage": self.resource_usage,
            "collaboration_index": self.collaboration_index,
            "health_status": self.health_status,
            "generated_at": self.generated_at,
        }


@dataclass
class WorkspaceNexusStats:
    """Aggregate statistics across all workspaces in the Nexus."""
    total_workspaces: int = 0
    active_workspaces: int = 0
    total_connections: int = 0
    context_flows: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_workspaces": self.total_workspaces,
            "active_workspaces": self.active_workspaces,
            "total_connections": self.total_connections,
            "context_flows": self.context_flows,
            "generated_at": self.generated_at,
        }


# ── Built-in Templates ──

DEFAULT_TEMPLATES: dict[str, WorkspaceTemplate] = {
    "general": WorkspaceTemplate(
        template_id="general",
        name="General Purpose",
        default_tools=["file_editor", "code_executor", "web_search"],
        default_skills=["reasoning", "summarization"],
        default_prompt="A general-purpose workspace for everyday tasks.",
        settings={"token_budget": 8192, "max_agents": 5},
    ),
    "code-review": WorkspaceTemplate(
        template_id="code-review",
        name="Code Review",
        default_tools=["code_analyzer", "linter", "diff_viewer", "test_runner"],
        default_skills=["code_review", "static_analysis", "test_generation"],
        default_prompt="A workspace tuned for systematic code review.",
        settings={"token_budget": 16384, "max_agents": 3},
    ),
    "research": WorkspaceTemplate(
        template_id="research",
        name="Research & Analysis",
        default_tools=["web_search", "document_parser", "data_visualizer"],
        default_skills=["research", "critical_analysis", "report_writing"],
        default_prompt="A workspace for deep research and analysis.",
        settings={"token_budget": 16384, "max_agents": 4},
    ),
    "development": WorkspaceTemplate(
        template_id="development",
        name="Software Development",
        default_tools=["code_editor", "terminal", "git", "debugger", "package_manager"],
        default_skills=["coding", "debugging", "refactoring", "testing"],
        default_prompt="A workspace for full-cycle software development.",
        settings={"token_budget": 32768, "max_agents": 8},
    ),
    "planning": WorkspaceTemplate(
        template_id="planning",
        name="Strategic Planning",
        default_tools=["task_manager", "gantt_chart", "dependency_graph"],
        default_skills=["planning", "decomposition", "estimation"],
        default_prompt="A workspace for strategic planning and task breakdown.",
        settings={"token_budget": 8192, "max_agents": 3},
    ),
}


# ── Workspace Nexus ──


class WorkspaceNexus:
    """Central orchestration hub connecting workspaces to all agent subsystems.

    The Nexus manages workspace lifecycle, binds subsystems (memory, skills,
    tools, agents, knowledge) to workspaces, orchestrates context flow between
    them, and collects analytics on workspace activity.
    """

    def __init__(self):
        self._workspaces: dict[str, Workspace] = {}
        self._templates: dict[str, WorkspaceTemplate] = dict(DEFAULT_TEMPLATES)
        self._connections: dict[str, SubsystemConnection] = {}
        self._context_flows: list[ContextFlow] = []
        self._analytics: dict[str, WorkspaceAnalytics] = {}

        # Metrics counters
        self._task_completions: dict[str, int] = {}
        self._error_counts: dict[str, int] = {}
        self._agent_interactions: dict[str, int] = {}
        self._resource_consumption: dict[str, dict[str, float]] = {}

    # ── Workspace Registry Layer ──

    def create_workspace(
        self,
        name: str,
        template_id: str = "general",
        description: str = "",
    ) -> Workspace:
        """Create a new workspace from a template.

        Args:
            name: Human-readable name for the workspace.
            template_id: Identifier of the template to use.
            description: Optional description of the workspace purpose.

        Returns:
            The newly created Workspace instance.
        """
        workspace_id = str(uuid.uuid4())[:12]
        template = self._templates.get(template_id, self._templates["general"])

        workspace = Workspace(
            workspace_id=workspace_id,
            name=name,
            description=description,
            template_id=template_id,
            tags=[],
            metadata={
                "template_name": template.name,
                "default_tools": template.default_tools,
                "default_skills": template.default_skills,
                "default_prompt": template.default_prompt,
                "settings": template.settings,
            },
        )
        self._workspaces[workspace_id] = workspace
        self._task_completions[workspace_id] = 0
        self._error_counts[workspace_id] = 0
        self._agent_interactions[workspace_id] = 0
        self._resource_consumption[workspace_id] = {"tokens": 0.0, "compute_seconds": 0.0, "storage_mb": 0.0}
        logger.info("Workspace created: %s (%s) from template %s", name, workspace_id, template_id)
        return workspace

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Retrieve a workspace by its identifier."""
        return self._workspaces.get(workspace_id)

    def list_workspaces(
        self, status_filter: WorkspaceStatus | None = None
    ) -> list[Workspace]:
        """List all workspaces, optionally filtered by status."""
        workspaces = list(self._workspaces.values())
        if status_filter is not None:
            workspaces = [w for w in workspaces if w.status == status_filter]
        return workspaces

    def activate_workspace(self, workspace_id: str) -> bool:
        """Activate a workspace, making it ready for operations.

        Returns True if the workspace was found and activated.
        """
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            logger.warning("Cannot activate unknown workspace: %s", workspace_id)
            return False
        if ws.status == WorkspaceStatus.ARCHIVED:
            logger.warning("Cannot activate archived workspace: %s", workspace_id)
            return False
        ws.status = WorkspaceStatus.ACTIVE
        ws.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info("Workspace activated: %s (%s)", ws.name, workspace_id)
        return True

    def deactivate_workspace(self, workspace_id: str) -> bool:
        """Deactivate a workspace, pausing all associated operations."""
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.status = WorkspaceStatus.INACTIVE
        ws.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info("Workspace deactivated: %s (%s)", ws.name, workspace_id)
        return True

    def archive_workspace(self, workspace_id: str) -> bool:
        """Archive a workspace, preserving its data but halting all activity.

        Archived workspaces cannot be activated until restored.
        """
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.status = WorkspaceStatus.ARCHIVED
        ws.updated_at = datetime.now(timezone.utc).isoformat()
        # Disconnect all subsystem connections
        for conn in list(self._connections.values()):
            if conn.workspace_id == workspace_id:
                conn.status = ConnectionStatus.DISCONNECTED
        logger.info("Workspace archived: %s (%s)", ws.name, workspace_id)
        return True

    def delete_workspace(self, workspace_id: str) -> bool:
        """Permanently delete a workspace and all its connections."""
        ws = self._workspaces.pop(workspace_id, None)
        if ws is None:
            return False
        # Remove all connections for this workspace
        self._connections = {
            cid: conn for cid, conn in self._connections.items()
            if conn.workspace_id != workspace_id
        }
        # Remove all context flows for this workspace
        self._context_flows = [
            cf for cf in self._context_flows
            if cf.workspace_id != workspace_id
        ]
        # Clean up analytics and metrics
        self._analytics.pop(workspace_id, None)
        self._task_completions.pop(workspace_id, None)
        self._error_counts.pop(workspace_id, None)
        self._agent_interactions.pop(workspace_id, None)
        self._resource_consumption.pop(workspace_id, None)
        logger.info("Workspace deleted: %s (%s)", ws.name, workspace_id)
        return True

    def update_workspace_tags(self, workspace_id: str, tags: list[str]) -> bool:
        """Replace the tags on a workspace."""
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.tags = list(tags)
        ws.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def update_workspace_metadata(
        self, workspace_id: str, key: str, value: Any
    ) -> bool:
        """Set a metadata key-value pair on a workspace."""
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.metadata[key] = value
        ws.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    # ── Template Management ──

    def register_template(self, template: WorkspaceTemplate) -> None:
        """Register a custom workspace template."""
        self._templates[template.template_id] = template
        logger.info("Template registered: %s (%s)", template.name, template.template_id)

    def get_template(self, template_id: str) -> WorkspaceTemplate | None:
        """Retrieve a workspace template by its identifier."""
        return self._templates.get(template_id)

    def list_templates(self) -> list[WorkspaceTemplate]:
        """List all registered workspace templates."""
        return list(self._templates.values())

    # ── Subsystem Connection Layer ──

    def connect_subsystem(
        self,
        workspace_id: str,
        subsystem_type: SubsystemType,
        subsystem_id: str,
        config: dict[str, Any] | None = None,
    ) -> SubsystemConnection | None:
        """Bind a subsystem to a workspace.

        Args:
            workspace_id: The workspace to connect to.
            subsystem_type: Type of subsystem (memory, skills, tools, agents, knowledge).
            subsystem_id: Identifier of the subsystem instance.
            config: Optional configuration for the connection.

        Returns:
            The SubsystemConnection if successful, None if the workspace does not exist.
        """
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            logger.warning("Cannot connect to unknown workspace: %s", workspace_id)
            return None

        connection_id = str(uuid.uuid4())[:12]
        connection = SubsystemConnection(
            connection_id=connection_id,
            workspace_id=workspace_id,
            subsystem_type=subsystem_type,
            subsystem_id=subsystem_id,
            config=config or {},
            status=ConnectionStatus.CONNECTED,
        )

        if subsystem_type == SubsystemType.AGENTS:
            if subsystem_id not in ws.agent_ids:
                ws.agent_ids.append(subsystem_id)

        self._connections[connection_id] = connection
        ws.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Subsystem connected: %s -> %s (type=%s)",
            subsystem_id, workspace_id, subsystem_type.value,
        )
        return connection

    def disconnect_subsystem(self, connection_id: str) -> bool:
        """Disconnect a subsystem from its workspace.

        Returns True if the connection was found and disconnected.
        """
        conn = self._connections.get(connection_id)
        if conn is None:
            return False
        conn.status = ConnectionStatus.DISCONNECTED
        ws = self._workspaces.get(conn.workspace_id)
        if ws and conn.subsystem_type == SubsystemType.AGENTS:
            if conn.subsystem_id in ws.agent_ids:
                ws.agent_ids.remove(conn.subsystem_id)
        logger.info("Subsystem disconnected: %s", connection_id)
        return True

    def get_connections(
        self,
        workspace_id: str,
        subsystem_type: SubsystemType | None = None,
    ) -> list[SubsystemConnection]:
        """Retrieve all connections for a workspace, optionally filtered by type."""
        results = [
            conn for conn in self._connections.values()
            if conn.workspace_id == workspace_id
        ]
        if subsystem_type is not None:
            results = [c for c in results if c.subsystem_type == subsystem_type]
        return results

    def get_connection(self, connection_id: str) -> SubsystemConnection | None:
        """Retrieve a single connection by its identifier."""
        return self._connections.get(connection_id)

    def update_connection_status(
        self, connection_id: str, status: ConnectionStatus
    ) -> bool:
        """Update the status of a subsystem connection."""
        conn = self._connections.get(connection_id)
        if conn is None:
            return False
        conn.status = status
        if status == ConnectionStatus.CONNECTED:
            conn.last_sync_at = datetime.now(timezone.utc).isoformat()
        return True

    # ── Context Flow Layer ──

    def create_context_flow(
        self,
        workspace_id: str,
        source: SubsystemType,
        target: SubsystemType,
        content: dict[str, Any],
        priority: ContextPriority = ContextPriority.MEDIUM,
    ) -> ContextFlow | None:
        """Create a context transfer between two subsystems.

        Args:
            workspace_id: The workspace scope for this flow.
            source: The subsystem producing the context.
            target: The subsystem receiving the context.
            content: The context payload.
            priority: The priority of this flow.

        Returns:
            The ContextFlow instance, or None if the workspace does not exist.
        """
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            logger.warning("Cannot create context flow for unknown workspace: %s", workspace_id)
            return None

        flow = ContextFlow(
            flow_id=str(uuid.uuid4())[:12],
            workspace_id=workspace_id,
            source_subsystem=source,
            target_subsystem=target,
            content=content,
            priority=priority,
        )
        self._context_flows.append(flow)
        if len(self._context_flows) > 1000:
            self._context_flows = self._context_flows[-1000:]
        logger.debug(
            "Context flow created: %s -> %s (workspace=%s, priority=%s)",
            source.value, target.value, workspace_id, priority.value,
        )
        return flow

    def get_context_flows(
        self,
        workspace_id: str,
        source: SubsystemType | None = None,
        target: SubsystemType | None = None,
        limit: int = 50,
    ) -> list[ContextFlow]:
        """Retrieve context flows for a workspace with optional filters."""
        results = [
            cf for cf in self._context_flows
            if cf.workspace_id == workspace_id
        ]
        if source is not None:
            results = [cf for cf in results if cf.source_subsystem == source]
        if target is not None:
            results = [cf for cf in results if cf.target_subsystem == target]
        results.sort(key=lambda cf: cf.timestamp, reverse=True)
        return results[:limit]

    def sync_context(self, workspace_id: str) -> bool:
        """Synchronize context across all connected subsystems in a workspace.

        This ensures all subsystems have a consistent view of the workspace
        context state. Marks all connections as synced.

        Returns True if the workspace exists and sync was performed.
        """
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False

        now = datetime.now(timezone.utc).isoformat()
        synced_count = 0
        for conn in self._connections.values():
            if conn.workspace_id == workspace_id and conn.status == ConnectionStatus.CONNECTED:
                conn.last_sync_at = now
                synced_count += 1

        ws.updated_at = now
        logger.info("Context synced for workspace %s: %d connections updated", workspace_id, synced_count)
        return True

    def get_context_version(self, workspace_id: str) -> int:
        """Get the current context version for a workspace (number of flows as version)."""
        flows = [cf for cf in self._context_flows if cf.workspace_id == workspace_id]
        return len(flows)

    # ── Workspace Analytics Layer ──

    def get_analytics(self, workspace_id: str) -> WorkspaceAnalytics | None:
        """Compute and return analytics for a workspace.

        Returns None if the workspace does not exist.
        """
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return None

        # Compute productivity score from task completions and errors
        completed = self._task_completions.get(workspace_id, 0)
        errors = self._error_counts.get(workspace_id, 0)
        total = completed + errors
        productivity_score = (completed / total) if total > 0 else 0.0

        # Resource usage
        resource_usage = dict(self._resource_consumption.get(workspace_id, {
            "tokens": 0.0, "compute_seconds": 0.0, "storage_mb": 0.0,
        }))

        # Collaboration index from agent interactions
        interactions = self._agent_interactions.get(workspace_id, 0)
        agent_count = max(len(ws.agent_ids), 1)
        collaboration_index = interactions / agent_count if agent_count > 0 else 0.0

        # Health status derivation
        connections = self.get_connections(workspace_id)
        degraded_count = sum(1 for c in connections if c.status == ConnectionStatus.DEGRADED)
        disconnected_count = sum(1 for c in connections if c.status == ConnectionStatus.DISCONNECTED)
        if disconnected_count > len(connections) * 0.5:
            health_status = "critical"
        elif degraded_count > 0:
            health_status = "degraded"
        else:
            health_status = "healthy"

        analytics = WorkspaceAnalytics(
            workspace_id=workspace_id,
            productivity_score=round(productivity_score, 4),
            resource_usage=resource_usage,
            collaboration_index=round(collaboration_index, 4),
            health_status=health_status,
        )
        self._analytics[workspace_id] = analytics
        return analytics

    def record_task_completion(self, workspace_id: str) -> None:
        """Increment the task completion counter for a workspace."""
        self._task_completions[workspace_id] = self._task_completions.get(workspace_id, 0) + 1

    def record_error(self, workspace_id: str) -> None:
        """Increment the error counter for a workspace."""
        self._error_counts[workspace_id] = self._error_counts.get(workspace_id, 0) + 1

    def record_agent_interaction(self, workspace_id: str) -> None:
        """Increment the agent interaction counter for a workspace."""
        self._agent_interactions[workspace_id] = self._agent_interactions.get(workspace_id, 0) + 1

    def record_resource_usage(
        self,
        workspace_id: str,
        tokens: float = 0.0,
        compute_seconds: float = 0.0,
        storage_mb: float = 0.0,
    ) -> None:
        """Accumulate resource consumption metrics for a workspace."""
        if workspace_id not in self._resource_consumption:
            self._resource_consumption[workspace_id] = {
                "tokens": 0.0, "compute_seconds": 0.0, "storage_mb": 0.0,
            }
        usage = self._resource_consumption[workspace_id]
        usage["tokens"] += tokens
        usage["compute_seconds"] += compute_seconds
        usage["storage_mb"] += storage_mb

    # ── Aggregate Statistics ──

    def get_stats(self) -> WorkspaceNexusStats:
        """Compute aggregate statistics across all workspaces."""
        total_workspaces = len(self._workspaces)
        active_workspaces = sum(
            1 for w in self._workspaces.values()
            if w.status == WorkspaceStatus.ACTIVE
        )
        total_connections = len(self._connections)
        context_flows = len(self._context_flows)

        return WorkspaceNexusStats(
            total_workspaces=total_workspaces,
            active_workspaces=active_workspaces,
            total_connections=total_connections,
            context_flows=context_flows,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a human-readable summary of the Nexus state."""
        stats = self.get_stats()
        ws_list = []
        for ws in self._workspaces.values():
            connections = self.get_connections(ws.workspace_id)
            ws_list.append({
                "id": ws.workspace_id,
                "name": ws.name,
                "status": ws.status.value,
                "template": ws.template_id,
                "agent_count": len(ws.agent_ids),
                "connection_count": len(connections),
                "context_flows": len([cf for cf in self._context_flows if cf.workspace_id == ws.workspace_id]),
            })
        return {
            "stats": stats.to_dict(),
            "workspaces": ws_list,
            "template_count": len(self._templates),
        }

    # ── Lifecycle ──

    def reset(self) -> None:
        """Reset the Nexus to its initial state, clearing all data."""
        self._workspaces.clear()
        self._templates = dict(DEFAULT_TEMPLATES)
        self._connections.clear()
        self._context_flows.clear()
        self._analytics.clear()
        self._task_completions.clear()
        self._error_counts.clear()
        self._agent_interactions.clear()
        self._resource_consumption.clear()
        logger.info("WorkspaceNexus has been reset to initial state")


# ── Global Instance ──

workspace_nexus = WorkspaceNexus()