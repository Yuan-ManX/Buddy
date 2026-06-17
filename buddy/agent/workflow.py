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


@dataclass
class BranchCondition:
    """A condition for conditional branching in workflows."""
    task_id: str
    field: str = "state"          # field to evaluate (state, priority, metadata key)
    operator: str = "equals"      # equals, not_equals, contains, greater_than
    value: Any = None
    target_task_id: str = ""      # task to execute if condition is met


@dataclass
class WorkflowTemplate:
    """A reusable workflow template with parameterized task definitions."""
    id: str = field(default_factory=lambda: f"wftpl-{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    task_definitions: list[dict] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExecutionMetrics:
    """Metrics for workflow execution analysis."""
    task_id: str
    total_duration_ms: float = 0.0
    wait_duration_ms: float = 0.0
    blocked_duration_ms: float = 0.0
    delegation_count: int = 0
    state_transitions: int = 0
    dependency_chain_depth: int = 0


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
        self._templates: dict[str, WorkflowTemplate] = {}
        self._branches: dict[str, list[BranchCondition]] = {}
        self._execution_metrics: dict[str, ExecutionMetrics] = {}
        self._fan_out_groups: dict[str, list[str]] = {}

    def get_stats(self) -> dict[str, Any]:
        return self.board.get_board_stats()

    # ── Conditional Branching ──────────────────────────────

    def add_conditional_branch(
        self,
        task_id: str,
        field: str,
        operator: str,
        value: Any,
        target_task_id: str,
    ) -> BranchCondition:
        """Add a conditional branch to a workflow task.

        When the source task completes, the condition is evaluated. If
        the condition is met, the target task is automatically created
        or transitioned. If the condition is not met, the else branch
        (if any) is taken.

        Supported operators: equals, not_equals, contains, greater_than, less_than.

        Args:
            task_id: The source task whose result triggers the branch.
            field: Field to evaluate: 'state', 'priority', or a metadata key.
            operator: Comparison operator.
            value: The value to compare against.
            target_task_id: The task to activate if condition is met.

        Returns:
            The created BranchCondition record.
        """
        condition = BranchCondition(
            task_id=task_id,
            field=field,
            operator=operator,
            value=value,
            target_task_id=target_task_id,
        )
        if task_id not in self._branches:
            self._branches[task_id] = []
        self._branches[task_id].append(condition)
        logger.info(
            f"Conditional branch added: {task_id} -> {target_task_id} "
            f"({field} {operator} {value})"
        )
        return condition

    def evaluate_branches(self, task_id: str) -> list[str]:
        """Evaluate all conditional branches for a task and return triggered targets.

        Args:
            task_id: The source task ID.

        Returns:
            List of target task IDs whose conditions were met.
        """
        conditions = self._branches.get(task_id, [])
        triggered: list[str] = []

        task = self.board.get_task(task_id)
        if not task:
            return triggered

        for condition in conditions:
            try:
                actual_value = self._resolve_field_value(task, condition.field)
                if self._evaluate_condition(actual_value, condition.operator, condition.value):
                    triggered.append(condition.target_task_id)
                    logger.info(
                        f"Branch triggered: {task_id} -> {condition.target_task_id}"
                    )
            except Exception as e:
                logger.warning(f"Branch evaluation failed for {task_id}: {e}")

        return triggered

    def get_branches(self, task_id: str) -> list[BranchCondition]:
        """Get all conditional branches for a task."""
        return list(self._branches.get(task_id, []))

    def get_all_branches(self) -> dict[str, list[BranchCondition]]:
        """Get all conditional branches in the workflow."""
        return dict(self._branches)

    @staticmethod
    def _resolve_field_value(task: WorkflowTask, field: str) -> Any:
        """Resolve a field value from a task for condition evaluation."""
        if field == "state":
            return task.state.value
        if field == "priority":
            return task.priority.value
        if field == "title":
            return task.title
        if field == "description":
            return task.description
        if field == "assigned_agent":
            return task.assigned_agent
        # Try metadata
        if field in task.metadata:
            return task.metadata[field]
        return None

    @staticmethod
    def _evaluate_condition(actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a single condition against actual and expected values."""
        if operator == "equals":
            return actual == expected
        if operator == "not_equals":
            return actual != expected
        if operator == "contains":
            return str(expected) in str(actual) if actual else False
        if operator == "greater_than":
            try:
                return float(actual) > float(expected)
            except (TypeError, ValueError):
                return False
        if operator == "less_than":
            try:
                return float(actual) < float(expected)
            except (TypeError, ValueError):
                return False
        return False

    # ── Parallel Task Fan-Out / Fan-In ─────────────────────

    def fan_out(
        self, parent_task_id: str, sub_tasks: list[dict], agent_id: str = ""
    ) -> list[str]:
        """Create multiple sub-tasks that execute in parallel.

        Each sub-task is created and linked to the parent. The parent
        task is blocked until all sub-tasks are complete (fan-in).

        Args:
            parent_task_id: The parent task that spawns sub-tasks.
            sub_tasks: List of dicts with 'title', 'description', 'priority'.
            agent_id: Default agent to assign to sub-tasks.

        Returns:
            List of created sub-task IDs.
        """
        parent = self.board.get_task(parent_task_id)
        if not parent:
            logger.error(f"Parent task not found: {parent_task_id}")
            return []

        sub_task_ids: list[str] = []
        for sub_def in sub_tasks:
            sub_task = self.board.create_task(
                title=sub_def.get("title", f"Sub-task of {parent_task_id}"),
                description=sub_def.get("description", ""),
                priority=WorkflowPriority(sub_def.get("priority", "medium")),
                assigned_agent=sub_def.get("agent_id", agent_id),
                created_by=parent.created_by,
                studio_id=parent.studio_id,
            )
            self.board.transition(sub_task.id, TaskState.TODO)
            sub_task_ids.append(sub_task.id)

        # Register the fan-out group
        self._fan_out_groups[parent_task_id] = sub_task_ids

        # Block parent until all sub-tasks are done
        self.board.report_blocker(
            parent_task_id,
            BlockerType.DEPENDENCY,
            f"Waiting for {len(sub_task_ids)} parallel sub-tasks to complete",
            reported_by=parent.assigned_agent or "system",
        )

        logger.info(
            f"Fan-out: {parent_task_id} spawned {len(sub_task_ids)} parallel sub-tasks"
        )
        return sub_task_ids

    def fan_in(self, parent_task_id: str) -> dict:
        """Aggregate results from completed parallel sub-tasks.

        Checks if all sub-tasks in the fan-out group are complete, then
        resolves the parent's blocker and returns aggregated results.

        Args:
            parent_task_id: The parent task ID.

        Returns:
            Dict with 'all_complete', 'completed_count', 'total_count',
            'sub_task_states', and 'sub_task_ids'.
        """
        sub_task_ids = self._fan_out_groups.get(parent_task_id, [])
        completed = 0
        states: dict[str, str] = {}

        for sub_id in sub_task_ids:
            sub_task = self.board.get_task(sub_id)
            if sub_task:
                states[sub_id] = sub_task.state.value
                if sub_task.state in (TaskState.DONE, TaskState.CANCELLED, TaskState.FAILED):
                    completed += 1

        all_complete = completed == len(sub_task_ids) if sub_task_ids else True

        if all_complete:
            # Resolve parent blocker
            parent = self.board.get_task(parent_task_id)
            if parent and parent.state == TaskState.BLOCKED:
                for blocker in parent.blockers:
                    if not blocker.is_resolved:
                        self.board.resolve_blocker(
                            parent_task_id, blocker.id,
                            f"All {completed} sub-tasks completed"
                        )
                        break

            logger.info(f"Fan-in complete: {parent_task_id} ({completed}/{len(sub_task_ids)})")

        return {
            "all_complete": all_complete,
            "completed_count": completed,
            "total_count": len(sub_task_ids),
            "sub_task_states": states,
            "sub_task_ids": sub_task_ids,
        }

    def get_fan_out_group(self, parent_task_id: str) -> list[str]:
        """Get the sub-task IDs for a fan-out group."""
        return list(self._fan_out_groups.get(parent_task_id, []))

    # ── Workflow Templates ─────────────────────────────────

    def create_workflow_template(
        self,
        name: str,
        task_definitions: list[dict],
        parameters: dict[str, Any] | None = None,
        description: str = "",
    ) -> WorkflowTemplate:
        """Create a reusable workflow template with parameterized tasks.

        Task definitions use {param_name} placeholders that are substituted
        when the template is instantiated.

        Args:
            name: Unique template name.
            task_definitions: List of task dicts with parameter placeholders.
            parameters: Default parameter values.
            description: Template description.

        Returns:
            The created WorkflowTemplate.
        """
        if name in self._templates:
            raise ValueError(f"Template '{name}' already exists")

        template = WorkflowTemplate(
            name=name,
            description=description,
            task_definitions=task_definitions,
            parameters=parameters or {},
        )
        self._templates[name] = template
        logger.info(f"Workflow template created: '{name}' with {len(task_definitions)} tasks")
        return template

    def instantiate_template(
        self, template_name: str, parameter_values: dict[str, Any] | None = None
    ) -> list[str]:
        """Instantiate a workflow template with parameter substitution.

        Replaces {param_name} placeholders in task definitions with the
        provided values and creates all tasks in the workflow.

        Args:
            template_name: Name of the template to instantiate.
            parameter_values: Values to substitute for template parameters.

        Returns:
            List of created task IDs.

        Raises:
            ValueError: If the template or required parameters are missing.
        """
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: '{template_name}'")

        params = dict(template.parameters)
        if parameter_values:
            params.update(parameter_values)

        created_ids: list[str] = []
        task_id_map: dict[str, str] = {}  # template_id -> real_id

        for task_def in template.task_definitions:
            # Perform parameter substitution
            title = self._substitute_params(task_def.get("title", ""), params)
            description = self._substitute_params(task_def.get("description", ""), params)

            task = self.board.create_task(
                title=title,
                description=description,
                priority=WorkflowPriority(task_def.get("priority", "medium")),
                assigned_agent=self._substitute_params(task_def.get("assigned_agent", ""), params),
                created_by=params.get("created_by", "template"),
                tags=task_def.get("tags", []),
            )

            # Map template ID to real ID for dependency resolution
            tpl_id = task_def.get("template_id", "")
            if tpl_id:
                task_id_map[tpl_id] = task.id

            created_ids.append(task.id)
            self.board.transition(task.id, TaskState.TODO)

        # Resolve dependencies using the ID map
        for task_def in template.task_definitions:
            tpl_id = task_def.get("template_id", "")
            real_id = task_id_map.get(tpl_id, "")
            if real_id:
                task = self.board.get_task(real_id)
                if task:
                    resolved_deps = [
                        task_id_map.get(dep, dep)
                        for dep in task_def.get("dependencies", [])
                    ]
                    task.dependencies = [d for d in resolved_deps if d]

        logger.info(
            f"Template '{template_name}' instantiated: {len(created_ids)} tasks created"
        )
        return created_ids

    def get_template(self, template_name: str) -> WorkflowTemplate | None:
        """Get a workflow template by name."""
        return self._templates.get(template_name)

    def list_templates(self) -> list[dict]:
        """List all workflow templates."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "task_count": len(t.task_definitions),
                "parameters": t.parameters,
                "created_at": t.created_at,
            }
            for t in self._templates.values()
        ]

    @staticmethod
    def _substitute_params(text: str, params: dict[str, Any]) -> str:
        """Substitute {param_name} placeholders in a string."""
        import re
        def replacer(match):
            key = match.group(1)
            return str(params.get(key, match.group(0)))
        return re.sub(r"\{(\w+)\}", replacer, text)

    # ── Circular Dependency Detection ──────────────────────

    def detect_circular_dependencies(self) -> list[list[str]]:
        """Detect circular dependencies in the task dependency graph.

        Uses DFS with a visited set to find cycles in the directed
        dependency graph across all tasks.

        Returns:
            List of cycles, where each cycle is a list of task IDs.
        """
        all_tasks = self.board._tasks
        cycles: list[list[str]] = []
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(task_id: str, path: list[str]) -> None:
            if task_id in in_stack:
                # Found a cycle — extract the cycle portion
                cycle_start = path.index(task_id)
                cycle = path[cycle_start:]
                cycles.append(cycle)
                return
            if task_id in visited:
                return

            visited.add(task_id)
            in_stack.add(task_id)
            path.append(task_id)

            task = all_tasks.get(task_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id in all_tasks:
                        dfs(dep_id, list(path))

            in_stack.discard(task_id)
            path.pop()

        for task_id in all_tasks:
            if task_id not in visited:
                dfs(task_id, [])

        if cycles:
            logger.warning(f"Detected {len(cycles)} circular dependency cycles")
        return cycles

    def resolve_circular_dependency(
        self, cycle: list[str], strategy: str = "remove_last"
    ) -> bool:
        """Resolve a circular dependency cycle.

        Strategies:
            - 'remove_last': Remove the last dependency edge in the cycle.
            - 'break_all': Remove all dependency edges in the cycle.

        Args:
            cycle: The cycle of task IDs to resolve.
            strategy: Resolution strategy to apply.

        Returns:
            True if the cycle was resolved.
        """
        if len(cycle) < 2:
            return False

        if strategy == "remove_last":
            # Remove the dependency from the last task in the cycle
            last_task = self.board.get_task(cycle[-1])
            if last_task:
                dep_to_remove = cycle[0] if len(cycle) == 2 else cycle[-2]
                if dep_to_remove in last_task.dependencies:
                    last_task.dependencies.remove(dep_to_remove)
                    logger.info(
                        f"Removed dependency {cycle[-1]} -> {dep_to_remove} to break cycle"
                    )
                    return True

        elif strategy == "break_all":
            removed = 0
            for i, task_id in enumerate(cycle):
                task = self.board.get_task(task_id)
                if task:
                    dep_target = cycle[(i + 1) % len(cycle)]
                    if dep_target in task.dependencies:
                        task.dependencies.remove(dep_target)
                        removed += 1
            logger.info(f"Removed {removed} dependency edges to break cycle")
            return removed > 0

        return False

    def get_dependency_chain_depth(self, task_id: str) -> int:
        """Get the maximum depth of the dependency chain for a task.

        Args:
            task_id: The task ID to analyze.

        Returns:
            The maximum number of dependency hops.
        """
        task = self.board.get_task(task_id)
        if not task:
            return 0

        all_tasks = self.board._tasks
        visited: set[str] = set()

        def max_depth(tid: str) -> int:
            if tid in visited:
                return 0
            visited.add(tid)
            t = all_tasks.get(tid)
            if not t or not t.dependencies:
                return 0
            return 1 + max(
                (max_depth(dep) for dep in t.dependencies if dep in all_tasks),
                default=0,
            )

        return max_depth(task_id)

    # ── Execution Metrics & Bottleneck Detection ───────────

    def get_execution_metrics(self, task_id: str) -> ExecutionMetrics:
        """Compute execution metrics for a workflow task.

        Analyzes the task's activity timeline to calculate total duration,
        wait time, blocked time, delegation count, and dependency depth.

        Args:
            task_id: The task ID to analyze.

        Returns:
            An ExecutionMetrics record with detailed timing data.
        """
        task = self.board.get_task(task_id)
        if not task:
            return ExecutionMetrics(task_id=task_id)

        metrics = ExecutionMetrics(task_id=task_id)

        # Count state transitions from activity log
        metrics.state_transitions = sum(
            1 for a in task.activities if a.action == "state_changed"
        )

        # Count delegations
        metrics.delegation_count = sum(
            1 for a in task.activities if a.action == "delegated"
        )

        # Calculate dependency chain depth
        metrics.dependency_chain_depth = self.get_dependency_chain_depth(task_id)

        # Calculate durations from activity timestamps
        activities = sorted(task.activities, key=lambda a: a.timestamp)

        if task.started_at and task.completed_at:
            try:
                start = datetime.fromisoformat(task.started_at)
                end = datetime.fromisoformat(task.completed_at)
                metrics.total_duration_ms = (end - start).total_seconds() * 1000
            except (ValueError, TypeError):
                pass

        # Calculate blocked duration
        blocked_start: str = ""
        for a in activities:
            if a.action == "state_changed" and a.to_state == "blocked":
                blocked_start = a.timestamp
            elif a.action == "state_changed" and a.from_state == "blocked" and blocked_start:
                try:
                    b_start = datetime.fromisoformat(blocked_start)
                    b_end = datetime.fromisoformat(a.timestamp)
                    metrics.blocked_duration_ms += (b_end - b_start).total_seconds() * 1000
                except (ValueError, TypeError):
                    pass
                blocked_start = ""

        # Calculate wait time (time between creation and start)
        if task.created_at and task.started_at:
            try:
                created = datetime.fromisoformat(task.created_at)
                started = datetime.fromisoformat(task.started_at)
                metrics.wait_duration_ms = (started - created).total_seconds() * 1000
            except (ValueError, TypeError):
                pass

        self._execution_metrics[task_id] = metrics
        return metrics

    def detect_bottlenecks(self, threshold_ms: float = 60000.0) -> list[dict]:
        """Detect workflow bottlenecks — tasks that exceed the duration threshold.

        Scans all tasks in the workflow and identifies those whose total
        duration or blocked time exceeds the specified threshold.

        Args:
            threshold_ms: Duration threshold in milliseconds to flag as bottleneck.

        Returns:
            List of bottleneck records with task ID, duration, and reason.
        """
        bottlenecks: list[dict] = []
        all_tasks = self.board._tasks

        for task_id in all_tasks:
            metrics = self.get_execution_metrics(task_id)

            reasons: list[str] = []
            if metrics.total_duration_ms > threshold_ms:
                reasons.append(f"total_duration={metrics.total_duration_ms:.0f}ms")
            if metrics.blocked_duration_ms > threshold_ms:
                reasons.append(f"blocked_duration={metrics.blocked_duration_ms:.0f}ms")
            if metrics.wait_duration_ms > threshold_ms:
                reasons.append(f"wait_duration={metrics.wait_duration_ms:.0f}ms")
            if metrics.dependency_chain_depth > 3:
                reasons.append(f"deep_dependency_chain={metrics.dependency_chain_depth}")

            if reasons:
                bottlenecks.append({
                    "task_id": task_id,
                    "title": all_tasks[task_id].title,
                    "state": all_tasks[task_id].state.value,
                    "duration_ms": metrics.total_duration_ms,
                    "blocked_ms": metrics.blocked_duration_ms,
                    "wait_ms": metrics.wait_duration_ms,
                    "dependency_depth": metrics.dependency_chain_depth,
                    "reasons": reasons,
                })

        bottlenecks.sort(key=lambda b: b["duration_ms"], reverse=True)
        logger.info(f"Detected {len(bottlenecks)} workflow bottlenecks")
        return bottlenecks

    def get_all_execution_metrics(self) -> dict[str, dict]:
        """Get execution metrics for all tasks in the workflow."""
        result = {}
        for task_id in self.board._tasks:
            metrics = self.get_execution_metrics(task_id)
            result[task_id] = {
                "total_duration_ms": metrics.total_duration_ms,
                "wait_duration_ms": metrics.wait_duration_ms,
                "blocked_duration_ms": metrics.blocked_duration_ms,
                "delegation_count": metrics.delegation_count,
                "state_transitions": metrics.state_transitions,
                "dependency_chain_depth": metrics.dependency_chain_depth,
            }
        return result


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

workflow_engine = WorkflowEngine()