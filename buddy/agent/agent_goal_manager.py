"""
Buddy Agent Goal Manager — full-lifecycle goal tracking for the AI agent.

The Agent Goal Manager tracks goals through their complete lifecycle: drafting,
activation, progress monitoring, dependency resolution, achievement evaluation,
and archival. It supports hierarchical decomposition via parent/child links,
priority-based ordering, metric-driven progress, and periodic reviews.

Core capabilities:
- Lifecycle management across nine goal states (draft → active → achieved/failed)
- Five-level priority classification from CRITICAL down to BACKGROUND
- Six goal types covering outcome, process, learning, and maintenance work
- Metric-based achievement evaluation with continuous progress scoring
- Dependency graph with typed relationships (requires, blocks, enables, ...)
- Hierarchical goal trees with path traversal from root to leaf
- Review system for capturing human or agent assessments over time
- Statistics aggregation for fleet-wide goal health monitoring
- Thread-safe state mutations guarded by an internal lock

The manager is intentionally dependency-free so it can run in any Buddy
runtime without extra packages.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════


class GoalStatus(str, Enum):
    """Lifecycle states for a goal."""
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    ACHIEVED = "achieved"
    FAILED = "failed"
    PAUSED = "paused"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class GoalPriority(int, Enum):
    """Priority levels for a goal. Lower value == higher priority."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


class GoalType(str, Enum):
    """Classification of what a goal is trying to accomplish."""
    OUTCOME = "outcome"
    PROCESS = "process"
    LEARNING = "learning"
    MAINTENANCE = "maintenance"
    AVOIDANCE = "avoidance"
    EXPLORATION = "exploration"


class GoalOrigin(str, Enum):
    """Where a goal originated from."""
    USER_REQUEST = "user_request"
    SELF_GENERATED = "self_generated"
    SYSTEM_INITIATED = "system_initiated"
    DERIVED = "derived"
    CALIBRATED = "calibrated"


class AchievementLevel(int, Enum):
    """Discrete achievement levels for a goal."""
    NOT_STARTED = 0
    INITIATED = 1
    IN_PROGRESS = 2
    NEAR_COMPLETION = 3
    ACHIEVED = 4
    EXCEEDED = 5


class DependencyType(str, Enum):
    """Types of relationships between goals."""
    REQUIRES = "requires"        # Source needs target to be achieved
    BLOCKED_BY = "blocked_by"    # Source cannot proceed until target resolved
    ENABLES = "enables"          # Source unblocks or facilitates target
    SUPERSEDES = "supersedes"    # Source replaces target
    REFINES = "refines"          # Source is a more precise version of target


# ═══════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════


@dataclass
class GoalMetric:
    """A measurable indicator attached to a goal."""
    metric_id: str
    name: str
    description: str
    target_value: float
    current_value: float = 0.0
    unit: str = ""
    threshold: float = 0.0
    is_met: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "description": self.description,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "threshold": self.threshold,
            "is_met": self.is_met,
        }


@dataclass
class GoalDependency:
    """A typed relationship between two goals."""
    dependency_id: str
    source_goal_id: str
    target_goal_id: str
    dependency_type: DependencyType
    strength: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "source_goal_id": self.source_goal_id,
            "target_goal_id": self.target_goal_id,
            "dependency_type": self.dependency_type.value
            if isinstance(self.dependency_type, DependencyType)
            else str(self.dependency_type),
            "strength": self.strength,
            "created_at": self.created_at,
        }


@dataclass
class Goal:
    """A single goal tracked by the manager."""
    goal_id: str
    title: str
    description: str
    goal_type: GoalType
    origin: GoalOrigin
    priority: GoalPriority
    status: GoalStatus
    parent_goal_id: str | None
    agent_id: str
    user_id: str
    metrics: list[GoalMetric] = field(default_factory=list)
    dependencies: list[GoalDependency] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    achievement_level: AchievementLevel = AchievementLevel.NOT_STARTED
    progress_score: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deadline: float | None = None
    achieved_at: float | None = None
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "goal_type": self.goal_type.value
            if isinstance(self.goal_type, GoalType)
            else str(self.goal_type),
            "origin": self.origin.value
            if isinstance(self.origin, GoalOrigin)
            else str(self.origin),
            "priority": int(self.priority.value)
            if isinstance(self.priority, GoalPriority)
            else int(self.priority),
            "status": self.status.value
            if isinstance(self.status, GoalStatus)
            else str(self.status),
            "parent_goal_id": self.parent_goal_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "metrics": [m.to_dict() if hasattr(m, "to_dict") else dict(m) for m in self.metrics],
            "dependencies": [
                d.to_dict() if hasattr(d, "to_dict") else dict(d) for d in self.dependencies
            ],
            "tags": list(self.tags),
            "achievement_level": int(self.achievement_level.value)
            if isinstance(self.achievement_level, AchievementLevel)
            else int(self.achievement_level),
            "progress_score": self.progress_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deadline": self.deadline,
            "achieved_at": self.achieved_at,
            "notes": self.notes,
            "metadata": dict(self.metadata),
        }


@dataclass
class GoalReview:
    """A recorded assessment of a goal at a point in time."""
    review_id: str
    goal_id: str
    reviewer: str
    review_time: float
    achievement_assessment: AchievementLevel
    progress_notes: str
    recommended_actions: list[str] = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "goal_id": self.goal_id,
            "reviewer": self.reviewer,
            "review_time": self.review_time,
            "achievement_assessment": int(self.achievement_assessment.value)
            if isinstance(self.achievement_assessment, AchievementLevel)
            else int(self.achievement_assessment),
            "progress_notes": self.progress_notes,
            "recommended_actions": list(self.recommended_actions),
            "score": self.score,
        }


@dataclass
class GoalManagerStats:
    """Aggregate statistics about the managed goal population."""
    total_goals: int
    goals_by_status: dict[str, int]
    goals_by_priority: dict[str, int]
    goals_by_type: dict[str, int]
    achievement_rate: float
    avg_progress: float
    overdue_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_goals": self.total_goals,
            "goals_by_status": dict(self.goals_by_status),
            "goals_by_priority": dict(self.goals_by_priority),
            "goals_by_type": dict(self.goals_by_type),
            "achievement_rate": self.achievement_rate,
            "avg_progress": self.avg_progress,
            "overdue_count": self.overdue_count,
        }


# ═══════════════════════════════════════════════════════════
# Manager
# ═══════════════════════════════════════════════════════════


class AgentGoalManager:
    """Full-lifecycle goal manager for the AI agent.

    Tracks goals from draft through achievement, decomposes them into
    hierarchical sub-goals via parent links, monitors progress through
    metrics, and records periodic reviews. All state mutations are
    guarded by an internal lock to support multi-threaded runtimes.
    """

    MAX_GOALS = 500
    MAX_REVIEWS = 2000

    # Terminal states where a goal is no longer actively pursued.
    _TERMINAL_STATUSES = frozenset({
        GoalStatus.ACHIEVED,
        GoalStatus.FAILED,
        GoalStatus.ARCHIVED,
        GoalStatus.DEPRECATED,
    })

    # Active states where a goal is in flight and counts toward urgency.
    _ACTIVE_STATUSES = frozenset({
        GoalStatus.ACTIVE,
        GoalStatus.IN_PROGRESS,
        GoalStatus.BLOCKED,
        GoalStatus.PAUSED,
    })

    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}
        self._reviews: dict[str, list[GoalReview]] = {}
        self._lock = threading.Lock()

    # ── Public API: Goal CRUD ───────────────────────────────────

    def create_goal(
        self,
        title: str,
        description: str,
        goal_type: GoalType,
        origin: GoalOrigin,
        priority: GoalPriority,
        agent_id: str,
        user_id: str,
        parent_goal_id: str | None = None,
        deadline: float | None = None,
        tags: list[str] | None = None,
        metrics: list[GoalMetric] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Goal:
        """Create and register a new goal.

        The goal starts in the ``DRAFT`` status. Callers should transition
        it to ``ACTIVE`` once it has been validated and is ready for
        execution. When ``parent_goal_id`` is supplied the goal becomes a
        sub-goal of the referenced parent, enabling hierarchical
        decomposition. Optional ``metrics`` can be supplied to drive
        automatic progress and achievement evaluation; otherwise metrics
        can be attached later via :meth:`add_metric`.

        Raises:
            RuntimeError: if the manager has reached ``MAX_GOALS``.
        """
        with self._lock:
            if len(self._goals) >= self.MAX_GOALS:
                raise RuntimeError(
                    f"Goal limit reached ({self.MAX_GOALS}); "
                    "archive or delete goals before creating new ones"
                )

            goal_id = f"goal-{uuid.uuid4().hex[:12]}"
            now = time.time()
            goal = Goal(
                goal_id=goal_id,
                title=title,
                description=description,
                goal_type=goal_type,
                origin=origin,
                priority=priority,
                status=GoalStatus.DRAFT,
                parent_goal_id=parent_goal_id,
                agent_id=agent_id,
                user_id=user_id,
                metrics=list(metrics) if metrics else [],
                dependencies=[],
                tags=list(tags) if tags else [],
                achievement_level=AchievementLevel.NOT_STARTED,
                progress_score=0.0,
                created_at=now,
                updated_at=now,
                deadline=deadline,
                achieved_at=None,
                notes="",
                metadata=dict(metadata) if metadata else {},
            )
            self._goals[goal_id] = goal
            return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        """Retrieve a goal by id."""
        with self._lock:
            return self._goals.get(goal_id)

    def update_goal(self, goal_id: str, **kwargs: Any) -> Goal | None:
        """Update mutable fields on a goal.

        Only known, non-identity fields are updated. ``goal_id`` and
        ``created_at`` cannot be changed through this method.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None

            immutable = {"goal_id", "created_at"}
            changed = False
            for key, value in kwargs.items():
                if key in immutable:
                    continue
                if hasattr(goal, key):
                    setattr(goal, key, value)
                    changed = True

            if changed:
                goal.updated_at = time.time()
            return goal

    def delete_goal(self, goal_id: str) -> bool:
        """Remove a goal and any reviews attached to it."""
        with self._lock:
            if goal_id not in self._goals:
                return False
            del self._goals[goal_id]
            self._reviews.pop(goal_id, None)
            # Detach children by clearing their parent reference is intentionally
            # avoided here: callers can re-parent explicitly via update_goal.
            return True

    def set_goal_status(self, goal_id: str, status: GoalStatus) -> Goal | None:
        """Transition a goal to a new status."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = status
            goal.updated_at = time.time()
            if status == GoalStatus.ACHIEVED and goal.achieved_at is None:
                goal.achieved_at = time.time()
                goal.progress_score = 1.0
                goal.achievement_level = AchievementLevel.ACHIEVED
            elif status in self._TERMINAL_STATUSES and goal.achieved_at is None:
                # Failed / archived goals are not marked as achieved.
                pass
            return goal

    def set_goal_priority(self, goal_id: str, priority: GoalPriority) -> Goal | None:
        """Re-prioritize a goal."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.priority = priority
            goal.updated_at = time.time()
            return goal

    def list_goals(
        self,
        status: GoalStatus | None = None,
        priority: GoalPriority | None = None,
        goal_type: GoalType | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        parent: str | None = None,
    ) -> list[Goal]:
        """List goals filtered by the provided criteria.

        All filters are optional and combine with logical AND semantics.
        Passing ``parent=None`` (the default) does not restrict by parent;
        pass an explicit parent id to fetch the direct children of a goal.
        Returns a fresh list snapshot taken under the lock.
        """
        with self._lock:
            results: list[Goal] = []
            for goal in self._goals.values():
                if status is not None and goal.status != status:
                    continue
                if priority is not None and goal.priority != priority:
                    continue
                if goal_type is not None and goal.goal_type != goal_type:
                    continue
                if agent_id is not None and goal.agent_id != agent_id:
                    continue
                if user_id is not None and goal.user_id != user_id:
                    continue
                if parent is not None and goal.parent_goal_id != parent:
                    continue
                results.append(goal)
            return results

    # ── Public API: Metrics ─────────────────────────────────────

    def add_metric(
        self,
        goal_id: str,
        name: str,
        description: str,
        target_value: float,
        unit: str = "",
        threshold: float = 0.0,
    ) -> GoalMetric:
        """Attach a new metric to a goal."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                raise ValueError(f"Goal not found: {goal_id}")

            metric = GoalMetric(
                metric_id=f"metric-{uuid.uuid4().hex[:8]}",
                name=name,
                description=description,
                target_value=target_value,
                current_value=0.0,
                unit=unit,
                threshold=threshold,
                is_met=False,
            )
            goal.metrics.append(metric)
            goal.updated_at = time.time()
            return metric

    def update_metric(self, goal_id: str, metric_id: str, current_value: float) -> Goal | None:
        """Update a metric's current value and refresh derived goal fields."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None

            for metric in goal.metrics:
                if metric.metric_id != metric_id:
                    continue
                metric.current_value = current_value
                metric.is_met = self._is_metric_met(metric)
                goal.updated_at = time.time()
                self._recalculate_progress_locked(goal)
                self._refresh_achievement_locked(goal)
                return goal
            return goal

    # ── Public API: Dependencies ────────────────────────────────

    def add_dependency(
        self,
        source_goal_id: str,
        target_goal_id: str,
        dependency_type: DependencyType,
        strength: float = 1.0,
    ) -> GoalDependency:
        """Create a typed dependency between two goals.

        The dependency is recorded on the source goal. When the
        relationship is ``BLOCKED_BY`` and the source is currently
        ``ACTIVE``, its status is automatically transitioned to
        ``BLOCKED`` so it surfaces in :meth:`get_blocked_goals`.

        Raises:
            ValueError: if either goal id is unknown or a goal is
                linked to itself.
        """
        with self._lock:
            source = self._goals.get(source_goal_id)
            if source is None:
                raise ValueError(f"Source goal not found: {source_goal_id}")
            if target_goal_id not in self._goals:
                raise ValueError(f"Target goal not found: {target_goal_id}")
            if source_goal_id == target_goal_id:
                raise ValueError("A goal cannot depend on itself")

            dependency = GoalDependency(
                dependency_id=f"dep-{uuid.uuid4().hex[:8]}",
                source_goal_id=source_goal_id,
                target_goal_id=target_goal_id,
                dependency_type=dependency_type,
                strength=max(0.0, min(1.0, strength)),
                created_at=time.time(),
            )
            source.dependencies.append(dependency)
            source.updated_at = time.time()

            # If the relationship blocks the source, reflect it in status.
            if dependency_type == DependencyType.BLOCKED_BY and source.status == GoalStatus.ACTIVE:
                source.status = GoalStatus.BLOCKED

            return dependency

    def remove_dependency(self, goal_id: str, dependency_id: str) -> bool:
        """Remove a dependency from a goal."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return False
            before = len(goal.dependencies)
            goal.dependencies = [
                d for d in goal.dependencies if d.dependency_id != dependency_id
            ]
            removed = len(goal.dependencies) < before
            if removed:
                goal.updated_at = time.time()
            return removed

    # ── Public API: Hierarchy ───────────────────────────────────

    def get_sub_goals(self, goal_id: str) -> list[Goal]:
        """Return the direct children of a goal."""
        with self._lock:
            return [
                g for g in self._goals.values() if g.parent_goal_id == goal_id
            ]

    def get_goal_path(self, goal_id: str) -> list[Goal]:
        """Return the path from the root goal down to the given goal.

        If the goal does not exist an empty list is returned. The path
        includes the goal itself as the final element.
        """
        with self._lock:
            if goal_id not in self._goals:
                return []
            path: list[Goal] = []
            current_id: str | None = goal_id
            visited: set[str] = set()
            while current_id is not None and current_id not in visited:
                visited.add(current_id)
                goal = self._goals.get(current_id)
                if goal is None:
                    break
                path.append(goal)
                current_id = goal.parent_goal_id
            path.reverse()
            return path

    # ── Public API: Achievement & Progress ──────────────────────

    def check_achievement(self, goal_id: str) -> AchievementLevel:
        """Evaluate the achievement level of a goal based on its metrics.

        The level is derived from the ratio of met metrics to total
        metrics. When all metrics are met the goal is marked ``ACHIEVED``,
        or ``EXCEEDED`` if any positive-target metric is over-fulfilled.
        Goals without metrics infer their level from the progress score.
        The evaluated level is written back to the goal when it differs
        from the stored value.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return AchievementLevel.NOT_STARTED
            level = self._evaluate_achievement_locked(goal)
            if level != goal.achievement_level:
                goal.achievement_level = level
                goal.updated_at = time.time()
                if level == AchievementLevel.ACHIEVED and goal.achieved_at is None:
                    goal.achieved_at = time.time()
                    goal.progress_score = 1.0
            return level

    def recalculate_progress(self, goal_id: str) -> float:
        """Recompute the progress score (0.0 to 1.0) for a goal.

        The score is the mean of per-metric progress ratios
        (``current_value / target_value``), each clamped to ``[0.0, 1.0]``.
        Goals without metrics fall back to a coarse mapping derived from
        the current achievement level. The recomputed score is stored on
        the goal and also returned to the caller.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return 0.0
            return self._recalculate_progress_locked(goal)

    # ── Public API: Reviews ─────────────────────────────────────

    def review_goal(
        self,
        goal_id: str,
        reviewer: str,
        achievement_assessment: AchievementLevel,
        progress_notes: str,
        recommended_actions: list[str] | None = None,
        score: float = 0.0,
    ) -> GoalReview:
        """Record a review against a goal.

        Reviews are append-only and capped at ``MAX_REVIEWS`` per goal;
        the oldest entry is evicted when the cap is reached. The review's
        achievement assessment is mirrored onto the goal, and an
        ``ACHIEVED`` assessment will also transition a non-terminal goal
        to the ``ACHIEVED`` status and stamp ``achieved_at``.

        Raises:
            ValueError: if the goal id is unknown.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                raise ValueError(f"Goal not found: {goal_id}")

            reviews = self._reviews.setdefault(goal_id, [])
            if len(reviews) >= self.MAX_REVIEWS:
                # Drop oldest to make room; keeps recent reviews authoritative.
                reviews.pop(0)

            review = GoalReview(
                review_id=f"review-{uuid.uuid4().hex[:8]}",
                goal_id=goal_id,
                reviewer=reviewer,
                review_time=time.time(),
                achievement_assessment=achievement_assessment,
                progress_notes=progress_notes,
                recommended_actions=list(recommended_actions) if recommended_actions else [],
                score=max(0.0, min(1.0, score)),
            )
            reviews.append(review)

            # Reflect the review's assessment back onto the goal.
            goal.achievement_level = achievement_assessment
            goal.updated_at = time.time()
            if achievement_assessment == AchievementLevel.ACHIEVED and goal.achieved_at is None:
                goal.achieved_at = time.time()
                goal.progress_score = 1.0
                if goal.status not in self._TERMINAL_STATUSES:
                    goal.status = GoalStatus.ACHIEVED

            return review

    def get_reviews(self, goal_id: str) -> list[GoalReview]:
        """Return all reviews recorded for a goal, oldest first."""
        with self._lock:
            return list(self._reviews.get(goal_id, []))

    # ── Public API: Queries ─────────────────────────────────────

    def get_overdue_goals(self) -> list[Goal]:
        """Return all non-terminal goals whose deadline has passed."""
        now = time.time()
        with self._lock:
            return [
                g for g in self._goals.values()
                if g.deadline is not None
                and g.deadline < now
                and g.status not in self._TERMINAL_STATUSES
            ]

    def get_blocked_goals(self) -> list[Goal]:
        """Return all goals currently in the BLOCKED status."""
        with self._lock:
            return [
                g for g in self._goals.values() if g.status == GoalStatus.BLOCKED
            ]

    def prioritize_goals(self, agent_id: str | None = None) -> list[Goal]:
        """Return active goals sorted by priority then deadline urgency.

        Lower priority values come first (CRITICAL before BACKGROUND).
        Within the same priority band, goals with earlier deadlines rank
        higher. Goals without deadlines sink to the back of their band.
        """
        with self._lock:
            candidates = [
                g for g in self._goals.values()
                if g.status in self._ACTIVE_STATUSES
                and (agent_id is None or g.agent_id == agent_id)
            ]

            now = time.time()

            def urgency_key(goal: Goal) -> tuple:
                # Lower tuple sorts first. Priority value already lower == higher.
                priority_rank = goal.priority.value
                if goal.deadline is not None:
                    # Negative slack => overdue; smaller slack sorts first.
                    slack = goal.deadline - now
                    deadline_rank = (0, slack)
                else:
                    # No deadline: rank after all deadline-bearing goals.
                    deadline_rank = (1, 0.0)
                # Tie-break by progress so goals closer to done surface first.
                return (priority_rank, deadline_rank, -goal.progress_score)

            return sorted(candidates, key=urgency_key)

    def get_stats(self) -> GoalManagerStats:
        """Compute aggregate statistics over the managed goals.

        Aggregates counts by status, priority, and type, plus the overall
        achievement rate (fraction of goals in the ``ACHIEVED`` status),
        the average progress score across all goals, and the number of
        non-terminal goals whose deadline has already passed. The snapshot
        is computed atomically under the lock.
        """
        with self._lock:
            total = len(self._goals)
            by_status: dict[str, int] = {}
            by_priority: dict[str, int] = {}
            by_type: dict[str, int] = {}
            achieved = 0
            progress_sum = 0.0
            overdue = 0
            now = time.time()

            for goal in self._goals.values():
                status_key = goal.status.value
                priority_key = goal.priority.name
                type_key = goal.goal_type.value
                by_status[status_key] = by_status.get(status_key, 0) + 1
                by_priority[priority_key] = by_priority.get(priority_key, 0) + 1
                by_type[type_key] = by_type.get(type_key, 0) + 1

                if goal.status == GoalStatus.ACHIEVED:
                    achieved += 1
                progress_sum += goal.progress_score

                if (
                    goal.deadline is not None
                    and goal.deadline < now
                    and goal.status not in self._TERMINAL_STATUSES
                ):
                    overdue += 1

            achievement_rate = (achieved / total) if total else 0.0
            avg_progress = (progress_sum / total) if total else 0.0

            return GoalManagerStats(
                total_goals=total,
                goals_by_status=by_status,
                goals_by_priority=by_priority,
                goals_by_type=by_type,
                achievement_rate=round(achievement_rate, 4),
                avg_progress=round(avg_progress, 4),
                overdue_count=overdue,
            )

    def reset(self) -> None:
        """Clear all goals and reviews from the manager."""
        with self._lock:
            self._goals.clear()
            self._reviews.clear()

    # ── Internal Helpers ────────────────────────────────────────

    def _is_metric_met(self, metric: GoalMetric) -> bool:
        """Determine whether a metric has reached its target."""
        if metric.target_value == 0:
            # Zero-target metrics are met when current reaches the threshold.
            return metric.current_value >= metric.threshold
        if metric.target_value > 0:
            return metric.current_value >= metric.target_value
        # Negative target (e.g. avoidance): met when current is at or below.
        return metric.current_value <= metric.target_value

    def _recalculate_progress_locked(self, goal: Goal) -> float:
        """Recompute the progress score without acquiring the lock.

        Progress is the mean of per-metric progress ratios
        (current / target), clamped to [0.0, 1.0]. Goals without
        metrics fall back to a coarse mapping from achievement level.
        """
        if not goal.metrics:
            fallback = goal.achievement_level.value / max(
                AchievementLevel.EXCEEDED.value, 1
            )
            goal.progress_score = round(max(0.0, min(1.0, fallback)), 4)
            return goal.progress_score

        ratios: list[float] = []
        for metric in goal.metrics:
            if metric.target_value == 0:
                # Use threshold as the denominator when target is zero.
                denom = metric.threshold if metric.threshold != 0 else 1.0
                ratio = metric.current_value / denom if denom > 0 else 0.0
            else:
                ratio = metric.current_value / metric.target_value
                if metric.target_value < 0:
                    # Inverted metric: closer to target is better.
                    ratio = 1.0 - ratio
            ratios.append(max(0.0, min(1.0, ratio)))

        progress = sum(ratios) / len(ratios)
        goal.progress_score = round(progress, 4)
        return goal.progress_score

    def _evaluate_achievement_locked(self, goal: Goal) -> AchievementLevel:
        """Evaluate the achievement level from current metrics."""
        if not goal.metrics:
            # Without metrics, infer from progress score.
            if goal.progress_score >= 1.0:
                return AchievementLevel.ACHIEVED
            if goal.progress_score >= 0.75:
                return AchievementLevel.NEAR_COMPLETION
            if goal.progress_score >= 0.25:
                return AchievementLevel.IN_PROGRESS
            if goal.progress_score > 0.0:
                return AchievementLevel.INITIATED
            return AchievementLevel.NOT_STARTED

        met_count = sum(1 for m in goal.metrics if self._is_metric_met(m))
        total = len(goal.metrics)
        ratio = met_count / total

        if ratio == 1.0:
            # All metrics met; check for over-performance (exceeded).
            exceeded = any(
                m.current_value > m.target_value
                for m in goal.metrics
                if m.target_value > 0 and m.current_value > m.target_value
            )
            return AchievementLevel.EXCEEDED if exceeded else AchievementLevel.ACHIEVED
        if ratio >= 0.75:
            return AchievementLevel.NEAR_COMPLETION
        if ratio >= 0.25:
            return AchievementLevel.IN_PROGRESS
        if ratio > 0.0:
            return AchievementLevel.INITIATED
        return AchievementLevel.NOT_STARTED

    def _refresh_achievement_locked(self, goal: Goal) -> None:
        """Refresh achievement level after a metric update (lock held)."""
        level = self._evaluate_achievement_locked(goal)
        if level != goal.achievement_level:
            goal.achievement_level = level
            if level == AchievementLevel.ACHIEVED and goal.achieved_at is None:
                goal.achieved_at = time.time()
                goal.progress_score = 1.0


# ═══════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════

_goal_manager_instance: AgentGoalManager | None = None


def get_goal_manager() -> AgentGoalManager:
    """Get or create the global goal manager singleton."""
    global _goal_manager_instance
    if _goal_manager_instance is None:
        _goal_manager_instance = AgentGoalManager()
    return _goal_manager_instance


def reset_goal_manager() -> None:
    """Reset the global goal manager singleton."""
    global _goal_manager_instance
    if _goal_manager_instance is not None:
        _goal_manager_instance.reset()
    _goal_manager_instance = None
