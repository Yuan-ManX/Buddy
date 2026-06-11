"""Buddy Workflow Engine — Agentic task lifecycle management with delegation.

Provides a complete task lifecycle system where agents operate as autonomous
teammates. Tasks go through a defined lifecycle (backlog → in-progress →
review → complete), agents can raise blockers, delegate to other agents,
and track progress. Inspired by Multica's agent-as-teammate model.

Features:
- Full task lifecycle: backlog, todo, in_progress, blocked, review, done, failed
- Agent assignment and delegation with ownership tracking
- Blocker reporting with resolution tracking
- Task dependencies with prerequisite checking
- Priority-based queue with automatic promotion
- Activity timeline for each task
- Task templates for common workflows

Architecture:
    WorkflowEngine (singleton)
    ├── TaskBoard (task CRUD + lifecycle)
    ├── AssignmentManager (agent assignment + delegation)
    ├── ActivityTracker (timeline + status history)
    └── DependencyResolver (DAG-based prerequisite checking)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import logging

logger = logging.getLogger("buddy.workflow")


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════════════════

class TaskState(str, Enum):
    """Complete task lifecycle states."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class BlockerType(str, Enum):
    """Types of blockers that can halt task progress."""
    DEPENDENCY = "dependency"
    EXTERNAL = "external"
    TECHNICAL = "technical"
    RESOURCE = "resource"
    CLARIFICATION = "clarification"
    PERMISSION = "permission"


@dataclass
class ActivityEntry:
    """A single entry in a task's activity timeline."""
    id: str = field(default_factory=lambda: f"act-{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    action: str = ""  # created, started, blocked, delegated, completed, etc.
    description: str = ""
    actor: str = ""  # agent_id or "user"
    from_state: str = ""
    to_state: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Blocker:
    """A blocker that prevents task progress."""
    id: str = field(default_factory=lambda: f"blk-{uuid.uuid4().hex[:12]}")
    type: BlockerType = BlockerType.DEPENDENCY
    description: str = ""
    reported_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str = ""
    resolution: str = ""
    is_resolved: bool = False


@dataclass
class WorkflowTask:
    """A task in the workflow system."""
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    title: str = "Untitled Task"
    description: str = ""
    state: TaskState = TaskState.BACKLOG
    priority: WorkflowPriority = WorkflowPriority.MEDIUM
    assigned_agent: str = ""
    created_by: str = ""
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # task IDs this depends on
    blockers: list[Blocker] = field(default_factory=list)
    planned_hours: float = 0.0
    actual_hours: float = 0.0
    studio_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    completed_at: str = ""
    activities: list[ActivityEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description[:300],
            "state": self.state.value,
            "priority": self.priority.value,
            "assigned_agent": self.assigned_agent,
            "created_by": self.created_by,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "blockers": [
                {
                    "type": b.type.value,
                    "description": b.description,
                    "is_resolved": b.is_resolved,
                }
                for b in self.blockers
            ],
            "planned_hours": self.planned_hours,
            "actual_hours": self.actual_hours,
            "studio_id": self.studio_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "activity_count": len(self.activities),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Dependency Resolver
# ═══════════════════════════════════════════════════════════════════════════

class DependencyResolver:
    """DAG-based task dependency checking."""

    def __init__(self):
        self._task_states: dict[str, TaskState] = {}  # task_id -> state

    def register_task(self, task_id: str, state: TaskState) -> None:
        self._task_states[task_id] = state

    def unregister_task(self, task_id: str) -> None:
        self._task_states.pop(task_id, None)

    def update_task_state(self, task_id: str, state: TaskState) -> None:
        self._task_states[task_id] = state

    def are_dependencies_met(self, dependency_ids: list[str]) -> tuple[bool, list[str]]:
        """Check if all dependencies are satisfied. Returns (met, unmet_ids)."""
        unmet = []
        for dep_id in dependency_ids:
            state = self._task_states.get(dep_id)
            if state is None:
                unmet.append(dep_id)
            elif state != TaskState.DONE:
                unmet.append(dep_id)

        return len(unmet) == 0, unmet

    def get_blocked_by(self, task_id: str, all_tasks: dict[str, "WorkflowTask"]) -> list[str]:
        """Find all tasks that are blocked by this task's completion."""
        blocked = []
        for tid, task in all_tasks.items():
            if task_id in task.dependencies and task.state != TaskState.DONE:
                blocked.append(tid)
        return blocked


# ═══════════════════════════════════════════════════════════════════════════
# Activity Tracker
# ═══════════════════════════════════════════════════════════════════════════

class ActivityTracker:
    """Tracks and records all task activities."""

    def __init__(self):
        self._activities: dict[str, list[ActivityEntry]] = {}  # task_id -> activities

    def record(
        self,
        task_id: str,
        action: str,
        description: str = "",
        actor: str = "",
        from_state: str = "",
        to_state: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ActivityEntry:
        entry = ActivityEntry(
            task_id=task_id,
            action=action,
            description=description,
            actor=actor,
            from_state=from_state,
            to_state=to_state,
            metadata=metadata or {},
        )
        self._activities.setdefault(task_id, []).append(entry)
        return entry

    def get_timeline(self, task_id: str) -> list[dict[str, Any]]:
        activities = self._activities.get(task_id, [])
        return [
            {
                "id": a.id,
                "action": a.action,
                "description": a.description,
                "actor": a.actor,
                "from_state": a.from_state,
                "to_state": a.to_state,
                "timestamp": a.timestamp,
            }
            for a in sorted(activities, key=lambda a: a.timestamp)
        ]

    def get_recent_activity(self, limit: int = 20) -> list[dict[str, Any]]:
        all_activities = []
        for task_id, activities in self._activities.items():
            all_activities.extend(activities)

        all_activities.sort(key=lambda a: a.timestamp, reverse=True)
        return [
            {
                "task_id": a.task_id,
                "action": a.action,
                "description": a.description,
                "actor": a.actor,
                "timestamp": a.timestamp,
            }
            for a in all_activities[:limit]
        ]


# ═══════════════════════════════════════════════════════════════════════════
# Task Board
# ═══════════════════════════════════════════════════════════════════════════

class TaskBoard:
    """Central task management with full lifecycle support."""

    # Valid state transitions
    _TRANSITIONS: dict[TaskState, list[TaskState]] = {
        TaskState.BACKLOG: [TaskState.TODO, TaskState.CANCELLED],
        TaskState.TODO: [TaskState.IN_PROGRESS, TaskState.BACKLOG, TaskState.CANCELLED],
        TaskState.IN_PROGRESS: [TaskState.BLOCKED, TaskState.REVIEW, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.BLOCKED: [TaskState.IN_PROGRESS, TaskState.CANCELLED],
        TaskState.REVIEW: [TaskState.DONE, TaskState.IN_PROGRESS, TaskState.FAILED],
        TaskState.DONE: [],  # Terminal state
        TaskState.FAILED: [TaskState.TODO, TaskState.CANCELLED],  # Can retry
        TaskState.CANCELLED: [],  # Terminal state
    }

    def __init__(self):
        self._tasks: dict[str, WorkflowTask] = {}
        self._resolver = DependencyResolver()
        self._tracker = ActivityTracker()

    @property
    def resolver(self) -> DependencyResolver:
        return self._resolver

    @property
    def tracker(self) -> ActivityTracker:
        return self._tracker

    # ── Task CRUD ──

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: WorkflowPriority = WorkflowPriority.MEDIUM,
        assigned_agent: str = "",
        created_by: str = "",
        dependencies: list[str] | None = None,
        tags: list[str] | None = None,
        studio_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowTask:
        task = WorkflowTask(
            title=title,
            description=description,
            priority=priority,
            assigned_agent=assigned_agent,
            created_by=created_by,
            dependencies=dependencies or [],
            tags=tags or [],
            studio_id=studio_id,
            metadata=metadata or {},
        )

        self._tasks[task.id] = task
        self._resolver.register_task(task.id, task.state)

        self._tracker.record(
            task.id,
            action="created",
            description=f"Task created: {title}",
            actor=created_by or "user",
            to_state=task.state.value,
        )

        logger.info(f"Task created: {task.id} ({title})")
        return task

    def get_task(self, task_id: str) -> WorkflowTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, state: TaskState | None = None, agent_id: str = "") -> list[WorkflowTask]:
        tasks = list(self._tasks.values())
        if state:
            tasks = [t for t in tasks if t.state == state]
        if agent_id:
            tasks = [t for t in tasks if t.assigned_agent == agent_id]
        return sorted(tasks, key=lambda t: (self._priority_order(t.priority), t.created_at))

    @staticmethod
    def _priority_order(p: WorkflowPriority) -> int:
        order = {WorkflowPriority.URGENT: 0, WorkflowPriority.HIGH: 1,
                 WorkflowPriority.MEDIUM: 2, WorkflowPriority.LOW: 3}
        return order.get(p, 2)

    # ── State Transitions ──

    def transition(self, task_id: str, new_state: TaskState, actor: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False

        allowed = self._TRANSITIONS.get(task.state, [])
        if new_state not in allowed:
            logger.warning(f"Invalid transition: {task.state.value} → {new_state.value}")
            return False

        old_state = task.state
        task.state = new_state
        task.updated_at = datetime.now(timezone.utc).isoformat()

        if new_state == TaskState.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now(timezone.utc).isoformat()
        if new_state in (TaskState.DONE, TaskState.CANCELLED):
            task.completed_at = datetime.now(timezone.utc).isoformat()
        if new_state == TaskState.BLOCKED and task.blockers:
            # If transitioning to blocked, ensure there's an unresolved blocker
            if not any(not b.is_resolved for b in task.blockers):
                logger.warning(f"Task {task_id} blocked but no unresolved blockers")

        self._resolver.update_task_state(task_id, new_state)

        self._tracker.record(
            task_id,
            action=f"state_changed",
            description=f"Moved from {old_state.value} to {new_state.value}",
            actor=actor,
            from_state=old_state.value,
            to_state=new_state.value,
        )

        logger.info(f"Task {task_id}: {old_state.value} → {new_state.value}")
        return True

    # ── Assignment ──

    def assign(self, task_id: str, agent_id: str, actor: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        old_assignee = task.assigned_agent
        task.assigned_agent = agent_id
        task.updated_at = datetime.now(timezone.utc).isoformat()

        self._tracker.record(
            task_id,
            action="assigned",
            description=f"Assigned to {agent_id}" + (f" (was {old_assignee})" if old_assignee else ""),
            actor=actor or agent_id,
        )

        if task.state == TaskState.BACKLOG:
            self.transition(task_id, TaskState.TODO, actor)

        return True

    def delegate(self, task_id: str, from_agent: str, to_agent: str) -> bool:
        """Delegate a task from one agent to another."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.assigned_agent != from_agent:
            logger.warning(f"Cannot delegate: task assigned to {task.assigned_agent}, not {from_agent}")
            return False

        task.assigned_agent = to_agent
        task.updated_at = datetime.now(timezone.utc).isoformat()

        self._tracker.record(
            task_id,
            action="delegated",
            description=f"Delegated from {from_agent} to {to_agent}",
            actor=from_agent,
        )

        return True

    # ── Blockers ──

    def report_blocker(
        self,
        task_id: str,
        blocker_type: BlockerType,
        description: str,
        reported_by: str = "",
    ) -> Blocker | None:
        task = self._tasks.get(task_id)
        if not task:
            return None

        blocker = Blocker(
            type=blocker_type,
            description=description,
            reported_by=reported_by,
        )
        task.blockers.append(blocker)

        self._tracker.record(
            task_id,
            action="blocker_reported",
            description=f"Blocker ({blocker_type.value}): {description}",
            actor=reported_by,
        )

        if task.state != TaskState.BLOCKED:
            self.transition(task_id, TaskState.BLOCKED, reported_by)

        logger.info(f"Blocker reported on {task_id}: {description[:100]}")
        return blocker

    def resolve_blocker(self, task_id: str, blocker_id: str, resolution: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False

        for blocker in task.blockers:
            if blocker.id == blocker_id:
                blocker.is_resolved = True
                blocker.resolved_at = datetime.now(timezone.utc).isoformat()
                blocker.resolution = resolution

                self._tracker.record(
                    task_id,
                    action="blocker_resolved",
                    description=f"Blocker resolved: {resolution[:200]}",
                )
                break

        # If all blockers resolved, transition back to in_progress
        if all(b.is_resolved for b in task.blockers):
            self.transition(task_id, TaskState.IN_PROGRESS)

        return True

    # ── Dependency Checking ──

    def can_start(self, task_id: str) -> tuple[bool, list[str]]:
        """Check if a task's dependencies are met."""
        task = self._tasks.get(task_id)
        if not task:
            return False, []
        return self._resolver.are_dependencies_met(task.dependencies)

    # ── Stats ──

    def get_board_stats(self) -> dict[str, Any]:
        tasks = list(self._tasks.values())
        state_counts: dict[str, int] = {}
        priority_counts: dict[str, int] = {}
        agent_counts: dict[str, int] = {}

        for t in tasks:
            state_counts[t.state.value] = state_counts.get(t.state.value, 0) + 1
            priority_counts[t.priority.value] = priority_counts.get(t.priority.value, 0) + 1
            if t.assigned_agent:
                agent_counts[t.assigned_agent] = agent_counts.get(t.assigned_agent, 0) + 1

        blockered = sum(1 for t in tasks if any(not b.is_resolved for b in t.blockers))

        return {
            "total_tasks": len(tasks),
            "by_state": state_counts,
            "by_priority": priority_counts,
            "by_agent": agent_counts,
            "blocked_tasks": blockered,
        }

    def get_timeline(self, task_id: str) -> list[dict[str, Any]]:
        return self._tracker.get_timeline(task_id)

    def get_recent_activity(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._tracker.get_recent_activity(limit)


# ═══════════════════════════════════════════════════════════════════════════
# Workflow Engine Facade
# ═══════════════════════════════════════════════════════════════════════════

class WorkflowEngine:
    """Central facade for the agentic workflow system.

    Usage:
        wf = WorkflowEngine()
        task = wf.board.create_task(title="Implement login page")
        wf.board.assign(task.id, "agent-engineering-001")
        wf.board.transition(task.id, TaskState.IN_PROGRESS)
        blocker = wf.board.report_blocker(task.id, BlockerType.TECHNICAL, "API key missing")
        wf.board.resolve_blocker(task.id, blocker.id, "Key obtained")
        wf.board.transition(task.id, TaskState.DONE)
        timeline = wf.board.get_timeline(task.id)
    """

    def __init__(self):
        self.board = TaskBoard()

    def get_stats(self) -> dict[str, Any]:
        return self.board.get_board_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

workflow_engine = WorkflowEngine()