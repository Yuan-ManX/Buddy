"""
Buddy Issue Board — Kanban-Style Task Management
=================================================
A board-based task workflow system that treats AI agents as team members.
Tasks move through lifecycle stages: queue → claim → execute → review → done.
Features automatic agent assignment, priority queuing, and skill compounding hooks.

Architecture inspired by the concept of managed agent teams where work items
flow through a structured pipeline with clear ownership and state transitions.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.issue_board")


# ── Board Column / Lifecycle States ────────────────────────


class IssueState(str, Enum):
    """Issue lifecycle states mapping to board columns."""
    BACKLOG = "backlog"
    QUEUED = "queued"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IssuePriority(str, Enum):
    """Issue priority levels for queue ordering."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Data Models ────────────────────────────────────────────


@dataclass
class Issue:
    """A work item on the board, assignable to an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    state: IssueState = IssueState.BACKLOG
    priority: IssuePriority = IssuePriority.MEDIUM
    assigned_agent: str | None = None  # agent_id
    assigned_runtime: str | None = None  # runtime_id
    workspace_id: str = ""
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    comments: list[dict[str, Any]] = field(default_factory=list)
    skills_used: list[str] = field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 50

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "state": self.state.value,
            "priority": self.priority.value,
            "assigned_agent": self.assigned_agent,
            "assigned_runtime": self.assigned_runtime,
            "workspace_id": self.workspace_id,
            "tags": self.tags,
            "context": self.context,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "comments": self.comments,
            "skills_used": self.skills_used,
            "iteration_count": self.iteration_count,
        }

    def add_comment(self, author: str, content: str, comment_type: str = "note"):
        self.comments.append({
            "id": str(uuid.uuid4()),
            "author": author,
            "content": content,
            "type": comment_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def transition(self, new_state: IssueState) -> bool:
        """Validate and execute a state transition."""
        valid_transitions = {
            IssueState.BACKLOG: [IssueState.QUEUED, IssueState.CANCELLED],
            IssueState.QUEUED: [IssueState.CLAIMED, IssueState.CANCELLED],
            IssueState.CLAIMED: [IssueState.IN_PROGRESS, IssueState.QUEUED, IssueState.CANCELLED],
            IssueState.IN_PROGRESS: [IssueState.BLOCKED, IssueState.REVIEW, IssueState.FAILED],
            IssueState.BLOCKED: [IssueState.IN_PROGRESS, IssueState.CANCELLED],
            IssueState.REVIEW: [IssueState.DONE, IssueState.IN_PROGRESS, IssueState.FAILED],
            IssueState.DONE: [IssueState.QUEUED],  # re-open
            IssueState.FAILED: [IssueState.QUEUED, IssueState.CANCELLED],  # retry or cancel
            IssueState.CANCELLED: [],  # terminal
        }
        if new_state in valid_transitions.get(self.state, []):
            old_state = self.state
            self.state = new_state
            self.updated_at = datetime.now(timezone.utc).isoformat()
            if new_state == IssueState.IN_PROGRESS and self.started_at is None:
                self.started_at = datetime.now(timezone.utc).isoformat()
            if new_state in (IssueState.DONE, IssueState.FAILED, IssueState.CANCELLED):
                self.completed_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Issue {self.id} transitioned: {old_state.value} → {new_state.value}")
            return True
        logger.warning(f"Invalid transition for {self.id}: {self.state.value} → {new_state.value}")
        return False


@dataclass
class BoardColumn:
    """A column on the Kanban board containing issues in a specific state."""
    state: IssueState
    name: str
    issues: list[Issue] = field(default_factory=list)
    limit: int = 0  # 0 = no limit

    def add(self, issue: Issue) -> bool:
        if self.limit > 0 and len(self.issues) >= self.limit:
            return False
        self.issues.append(issue)
        return True

    def remove(self, issue_id: str) -> Issue | None:
        for i, issue in enumerate(self.issues):
            if issue.id == issue_id:
                return self.issues.pop(i)
        return None

    def find(self, issue_id: str) -> Issue | None:
        for issue in self.issues:
            if issue.id == issue_id:
                return issue
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "name": self.name,
            "count": len(self.issues),
            "limit": self.limit,
            "issues": [i.to_dict() for i in self.issues],
        }


# ── Autopilot Rules ────────────────────────────────────────


@dataclass
class AutopilotRule:
    """A rule that automatically assigns matching issues to an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    agent_id: str = ""
    filters: dict[str, Any] = field(default_factory=dict)  # tag, priority, workspace filters
    enabled: bool = True
    max_concurrent: int = 3
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def matches(self, issue: Issue) -> bool:
        if not self.enabled:
            return False
        if self.filters.get("priority") and issue.priority.value != self.filters["priority"]:
            return False
        if self.filters.get("tags"):
            if not any(t in issue.tags for t in self.filters["tags"]):
                return False
        if self.filters.get("workspace_id") and issue.workspace_id != self.filters["workspace_id"]:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent_id": self.agent_id,
            "filters": self.filters,
            "enabled": self.enabled,
            "max_concurrent": self.max_concurrent,
        }


# ── Issue Board Engine ─────────────────────────────────────


class IssueBoard:
    """Core board engine that manages the Kanban workflow.

    Provides full issue lifecycle management, automatic agent assignment
    via autopilot rules, and integration hooks for skill compounding.
    """

    COLUMN_NAMES: dict[IssueState, str] = {
        IssueState.BACKLOG: "Backlog",
        IssueState.QUEUED: "Queued",
        IssueState.CLAIMED: "Claimed",
        IssueState.IN_PROGRESS: "In Progress",
        IssueState.BLOCKED: "Blocked",
        IssueState.REVIEW: "Review",
        IssueState.DONE: "Done",
        IssueState.FAILED: "Failed",
        IssueState.CANCELLED: "Cancelled",
    }

    def __init__(self):
        self._issues: dict[str, Issue] = {}
        self._columns: dict[IssueState, BoardColumn] = {}
        self._autopilot_rules: dict[str, AutopilotRule] = {}
        self._issue_counter: int = 0

        # Initialize columns
        for state in IssueState:
            self._columns[state] = BoardColumn(
                state=state,
                name=self.COLUMN_NAMES.get(state, state.value),
            )

        # Completion callbacks for skill compounding
        self._on_complete_callbacks: list[Callable] = []

    # ── Issue CRUD ─────────────────────────────────────

    def create_issue(
        self,
        title: str,
        description: str = "",
        priority: IssuePriority = IssuePriority.MEDIUM,
        tags: list[str] | None = None,
        workspace_id: str = "",
        context: dict[str, Any] | None = None,
        auto_assign: bool = True,
    ) -> Issue:
        """Create a new issue and add it to the board."""
        issue = Issue(
            title=title,
            description=description,
            priority=priority,
            tags=tags or [],
            workspace_id=workspace_id,
            context=context or {},
        )
        self._issues[issue.id] = issue
        self._columns[IssueState.BACKLOG].add(issue)
        self._issue_counter += 1

        if auto_assign:
            self._try_autopilot(issue)

        logger.info(f"Created issue {issue.id}: {title}")
        return issue

    def get_issue(self, issue_id: str) -> Issue | None:
        return self._issues.get(issue_id)

    def list_issues(
        self,
        state: IssueState | None = None,
        agent_id: str | None = None,
        workspace_id: str | None = None,
        priority: IssuePriority | None = None,
    ) -> list[Issue]:
        """List issues with optional filtering."""
        issues = list(self._issues.values())
        if state:
            issues = [i for i in issues if i.state == state]
        if agent_id:
            issues = [i for i in issues if i.assigned_agent == agent_id]
        if workspace_id:
            issues = [i for i in issues if i.workspace_id == workspace_id]
        if priority:
            issues = [i for i in issues if i.priority == priority]
        return sorted(issues, key=lambda i: i.updated_at, reverse=True)

    def update_issue(self, issue_id: str, **kwargs) -> Issue | None:
        """Update issue fields."""
        issue = self._issues.get(issue_id)
        if not issue:
            return None
        for key, value in kwargs.items():
            if hasattr(issue, key):
                setattr(issue, key, value)
        issue.updated_at = datetime.now(timezone.utc).isoformat()
        return issue

    def delete_issue(self, issue_id: str) -> bool:
        issue = self._issues.pop(issue_id, None)
        if issue:
            for col in self._columns.values():
                col.remove(issue_id)
            return True
        return False

    # ── State Transitions ──────────────────────────────

    def move_issue(self, issue_id: str, new_state: IssueState) -> bool:
        """Move an issue to a new column."""
        issue = self._issues.get(issue_id)
        if not issue:
            return False
        if not issue.transition(new_state):
            return False

        # Remove from old column
        for col in self._columns.values():
            col.remove(issue_id)

        # Add to new column
        self._columns[new_state].add(issue)

        # Trigger callbacks on completion
        if new_state == IssueState.DONE:
            for cb in self._on_complete_callbacks:
                try:
                    cb(issue)
                except Exception as e:
                    logger.error(f"Completion callback error: {e}")

        return True

    def assign_issue(self, issue_id: str, agent_id: str) -> bool:
        """Assign an issue to an agent."""
        issue = self._issues.get(issue_id)
        if not issue:
            return False
        issue.assigned_agent = agent_id
        issue.updated_at = datetime.now(timezone.utc).isoformat()
        if issue.state == IssueState.BACKLOG:
            self.move_issue(issue_id, IssueState.QUEUED)
        return True

    def claim_issue(self, issue_id: str, agent_id: str) -> bool:
        """An agent claims an issue."""
        issue = self._issues.get(issue_id)
        if not issue:
            return False
        if issue.assigned_agent and issue.assigned_agent != agent_id:
            return False  # Already assigned to another agent
        issue.assigned_agent = agent_id
        return self.move_issue(issue_id, IssueState.CLAIMED)

    def start_issue(self, issue_id: str) -> bool:
        return self.move_issue(issue_id, IssueState.IN_PROGRESS)

    def block_issue(self, issue_id: str, reason: str = "") -> bool:
        issue = self._issues.get(issue_id)
        if issue and reason:
            issue.add_comment("system", reason, "blocker")
        return self.move_issue(issue_id, IssueState.BLOCKED)

    def request_review(self, issue_id: str) -> bool:
        return self.move_issue(issue_id, IssueState.REVIEW)

    def complete_issue(self, issue_id: str, result: dict[str, Any] | None = None) -> bool:
        issue = self._issues.get(issue_id)
        if issue and result:
            issue.result = result
        return self.move_issue(issue_id, IssueState.DONE)

    def fail_issue(self, issue_id: str, error: str = "") -> bool:
        issue = self._issues.get(issue_id)
        if issue and error:
            issue.add_comment("system", error, "error")
            issue.result["error"] = error
        return self.move_issue(issue_id, IssueState.FAILED)

    # ── Autopilot ──────────────────────────────────────

    def add_autopilot_rule(
        self,
        name: str,
        agent_id: str,
        filters: dict[str, Any] | None = None,
        max_concurrent: int = 3,
    ) -> AutopilotRule:
        rule = AutopilotRule(
            name=name,
            agent_id=agent_id,
            filters=filters or {},
            max_concurrent=max_concurrent,
        )
        self._autopilot_rules[rule.id] = rule
        logger.info(f"Added autopilot rule: {name} → {agent_id}")
        return rule

    def remove_autopilot_rule(self, rule_id: str) -> bool:
        return self._autopilot_rules.pop(rule_id, None) is not None

    def list_autopilot_rules(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._autopilot_rules.values()]

    def _try_autopilot(self, issue: Issue):
        """Try to auto-assign an issue using autopilot rules."""
        for rule in self._autopilot_rules.values():
            if rule.matches(issue):
                # Check concurrent limit
                active_count = len([
                    i for i in self._issues.values()
                    if i.assigned_agent == rule.agent_id
                    and i.state in (IssueState.QUEUED, IssueState.CLAIMED, IssueState.IN_PROGRESS)
                ])
                if active_count < rule.max_concurrent:
                    self.assign_issue(issue.id, rule.agent_id)
                    self.move_issue(issue.id, IssueState.QUEUED)
                    logger.info(f"Autopilot assigned {issue.id} to {rule.agent_id}")
                    break

    # ── Callbacks ──────────────────────────────────────

    def on_complete(self, callback: Callable):
        """Register a callback for when an issue is completed."""
        self._on_complete_callbacks.append(callback)

    # ── Board State ────────────────────────────────────

    def get_board(self) -> dict[str, Any]:
        """Get the full board state for rendering."""
        columns = {}
        for state, col in self._columns.items():
            columns[state.value] = col.to_dict()
        return {
            "columns": columns,
            "total_issues": self._issue_counter,
            "active_issues": len([
                i for i in self._issues.values()
                if i.state not in (IssueState.DONE, IssueState.FAILED, IssueState.CANCELLED)
            ]),
            "autopilot_rules": self.list_autopilot_rules(),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get board statistics."""
        by_state = {}
        for state in IssueState:
            by_state[state.value] = len(self._columns[state].issues)
        by_priority = {}
        for p in IssuePriority:
            by_priority[p.value] = len([
                i for i in self._issues.values() if i.priority == p
            ])
        by_agent: dict[str, int] = {}
        for issue in self._issues.values():
            if issue.assigned_agent:
                by_agent[issue.assigned_agent] = by_agent.get(issue.assigned_agent, 0) + 1

        return {
            "total": self._issue_counter,
            "by_state": by_state,
            "by_priority": by_priority,
            "by_agent": by_agent,
            "autopilot_rules": len(self._autopilot_rules),
        }


# ── Singleton ──────────────────────────────────────────────

issue_board = IssueBoard()