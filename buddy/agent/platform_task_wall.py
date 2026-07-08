"""Buddy Platform Task Wall — central priority queue for multi-agent orchestration

The Task Wall is the orchestration spine for multi-agent teams. Tasks
are posted to the wall with priority levels, dependencies, and role
requirements. Agents pull the highest-priority items they're qualified
for, claim them, and execute. Deadlock detection parks blocked threads
and switches workstreams automatically.

Design principles:
  - Priority-driven: tasks have priority levels (CRITICAL, HIGH, MEDIUM,
    LOW, BACKGROUND) that determine execution order.
  - Role-matched: each task specifies required roles; only qualified
    agents can claim them.
  - Dependency-aware: tasks can declare dependencies; blocked tasks
    are parked and the system switches to other workstreams.
  - Deadlock detection: if all remaining tasks are blocked by circular
    dependencies, the wall detects the deadlock and escalates.
  - Workstream switching: when an agent's current task is blocked, the
    wall assigns the next available task, preventing idle time.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.platform.task_wall")


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class TaskStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARKED = "parked"  # Temporarily parked due to dependency


_PRIORITY_ORDER = {
    TaskPriority.CRITICAL: 0,
    TaskPriority.HIGH: 1,
    TaskPriority.MEDIUM: 2,
    TaskPriority.LOW: 3,
    TaskPriority.BACKGROUND: 4,
}


@dataclass
class WallTask:
    """A task on the Task Wall."""
    task_id: str = ""
    title: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    required_roles: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # task_ids this depends on
    assigned_agent_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    claimed_at: str = ""
    completed_at: str = ""
    workspace_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    estimated_complexity: str = "moderate"  # simple, moderate, complex

    @property
    def is_blocked(self) -> bool:
        return self.status == TaskStatus.BLOCKED

    @property
    def is_claimable(self) -> bool:
        return self.status == TaskStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "required_roles": self.required_roles,
            "dependencies": self.dependencies,
            "assigned_agent_id": self.assigned_agent_id,
            "created_at": self.created_at,
            "claimed_at": self.claimed_at,
            "completed_at": self.completed_at,
            "workspace_id": self.workspace_id,
            "metadata": self.metadata,
            "error": self.error,
            "retry_count": self.retry_count,
            "estimated_complexity": self.estimated_complexity,
        }


class TaskWall:
    """Central priority queue with deadlock detection and workstream switching.

    The Task Wall is the orchestration spine. Tasks are posted with
    priorities and dependencies. Agents pull the highest-priority items
    they're qualified for. Blocked tasks are parked automatically.
    """

    def __init__(self):
        self._tasks: dict[str, WallTask] = {}
        self._lock = threading.RLock()
        self._total_posted = 0
        self._total_completed = 0
        self._total_failed = 0
        self._total_parked = 0
        self._deadlock_count = 0
        self._role_catalog = None
        self._workspace_manager = None

    def attach_role_catalog(self, role_catalog) -> None:
        """Link a role catalog for role-matched task claiming."""
        self._role_catalog = role_catalog

    def attach_workspace_manager(self, workspace_manager) -> None:
        """Link a workspace manager for workspace-scoped task isolation."""
        self._workspace_manager = workspace_manager

    # ── Task lifecycle ───────────────────────────────────

    def post_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        required_roles: Optional[list[str]] = None,
        dependencies: Optional[list[str]] = None,
        workspace_id: str = "",
        estimated_complexity: str = "moderate",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Post a new task to the wall. Returns task_id."""
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        task = WallTask(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority,
            required_roles=required_roles or [],
            dependencies=dependencies or [],
            workspace_id=workspace_id,
            estimated_complexity=estimated_complexity,
            metadata=metadata or {},
        )
        with self._lock:
            self._tasks[task_id] = task
            self._total_posted += 1
            # Check if task is immediately blocked by dependencies
            if task.dependencies:
                unmet = [d for d in task.dependencies if d in self._tasks and self._tasks[d].status != TaskStatus.COMPLETED]
                if unmet:
                    task.status = TaskStatus.BLOCKED
        logger.info("Posted task '%s' (%s, priority=%s)", title, task_id, priority.value)
        return task_id

    def claim_task(
        self,
        agent_id: str,
        agent_roles: Optional[list[str]] = None,
        workspace_id: Optional[str] = None,
    ) -> Optional[WallTask]:
        """Claim the highest-priority available task for an agent.

        Returns the claimed task, or None if no tasks are available.
        """
        with self._lock:
            available = [
                task for task in self._tasks.values()
                if task.is_claimable
                and (workspace_id is None or task.workspace_id == workspace_id)
            ]

            # Filter by role requirements
            if agent_roles:
                qualified = [
                    task for task in available
                    if not task.required_roles or any(r in agent_roles for r in task.required_roles)
                ]
            else:
                qualified = [task for task in available if not task.required_roles]

            if not qualified:
                return None

            # Sort by priority (lower number = higher priority), then by creation time
            qualified.sort(key=lambda t: (_PRIORITY_ORDER.get(t.priority, 99), t.created_at))

            task = qualified[0]
            task.status = TaskStatus.CLAIMED
            task.assigned_agent_id = agent_id
            task.claimed_at = datetime.now(timezone.utc).isoformat()
            return task

    def start_task(self, task_id: str) -> bool:
        """Mark a claimed task as in-progress."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != TaskStatus.CLAIMED:
                return False
            task.status = TaskStatus.IN_PROGRESS
            return True

    def complete_task(self, task_id: str, result: Optional[dict[str, Any]] = None) -> bool:
        """Mark a task as completed and unblock dependents."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            if result:
                task.result = result
            self._total_completed += 1

            # Unblock dependent tasks
            for other in self._tasks.values():
                if task_id in other.dependencies and other.status == TaskStatus.BLOCKED:
                    unmet = [d for d in other.dependencies if d in self._tasks and self._tasks[d].status != TaskStatus.COMPLETED]
                    if not unmet:
                        other.status = TaskStatus.PENDING
            return True

    def fail_task(self, task_id: str, error: str = "") -> bool:
        """Mark a task as failed. May retry if retries remain."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.error = error
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING  # Retry
                task.assigned_agent_id = ""
                logger.info("Task %s failed (retry %d/%d): %s", task_id, task.retry_count, task.max_retries, error)
            else:
                task.status = TaskStatus.FAILED
                self._total_failed += 1
                logger.warning("Task %s permanently failed: %s", task_id, error)
            return True

    def park_task(self, task_id: str, reason: str = "") -> bool:
        """Park a blocked task and switch to another workstream."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.PARKED
            task.metadata["park_reason"] = reason
            task.metadata["parked_at"] = datetime.now(timezone.utc).isoformat()
            self._total_parked += 1
            return True

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.CANCELLED
            return True

    # ── Deadlock detection ───────────────────────────────

    def detect_deadlock(self) -> list[str]:
        """Detect circular dependencies that cause deadlocks.

        Returns a list of task_ids involved in the deadlock.
        """
        with self._lock:
            blocked_tasks = {
                tid: t for tid, t in self._tasks.items()
                if t.status in (TaskStatus.BLOCKED, TaskStatus.PARKED)
            }

            if not blocked_tasks:
                return []

            # Build dependency graph
            graph: dict[str, list[str]] = defaultdict(list)
            for tid, task in blocked_tasks.items():
                for dep in task.dependencies:
                    if dep in blocked_tasks:
                        graph[tid].append(dep)

            # Detect cycles using DFS
            visited: set[str] = set()
            rec_stack: set[str] = set()
            deadlocked: list[str] = []

            def dfs(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)
                for neighbor in graph.get(node, []):
                    if neighbor not in visited:
                        if dfs(neighbor):
                            deadlocked.append(node)
                            return True
                    elif neighbor in rec_stack:
                        deadlocked.append(node)
                        return True
                rec_stack.discard(node)
                return False

            for node in blocked_tasks:
                if node not in visited:
                    dfs(node)

            if deadlocked:
                self._deadlock_count += 1
                logger.warning("Deadlock detected involving %d tasks: %s", len(deadlocked), deadlocked)

            return list(set(deadlocked))

    # ── Queries ──────────────────────────────────────────

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.to_dict() if task else None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        workspace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if workspace_id:
            tasks = [t for t in tasks if t.workspace_id == workspace_id]
        if agent_id:
            tasks = [t for t in tasks if t.assigned_agent_id == agent_id]
        tasks.sort(key=lambda t: (_PRIORITY_ORDER.get(t.priority, 99), t.created_at))
        return [t.to_dict() for t in tasks[:limit]]

    def get_blocked_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            blocked = [t for t in self._tasks.values() if t.is_blocked]
            return [t.to_dict() for t in blocked]

    def get_agent_tasks(self, agent_id: str) -> list[dict[str, Any]]:
        with self._lock:
            tasks = [t for t in self._tasks.values() if t.assigned_agent_id == agent_id]
            return [t.to_dict() for t in tasks]

    # ── Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_posted": self._total_posted,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "total_parked": self._total_parked,
                "deadlock_count": self._deadlock_count,
                "active_tasks": sum(1 for t in self._tasks.values() if t.status in (TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS)),
                "pending_tasks": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
                "blocked_tasks": sum(1 for t in self._tasks.values() if t.status == TaskStatus.BLOCKED),
                "total_tasks": len(self._tasks),
            }


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

_task_wall: Optional[TaskWall] = None
_tw_lock = threading.Lock()


def get_task_wall() -> TaskWall:
    """Get the singleton TaskWall instance."""
    global _task_wall
    if _task_wall is None:
        with _tw_lock:
            if _task_wall is None:
                _task_wall = TaskWall()
    return _task_wall
