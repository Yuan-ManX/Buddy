"""
Buddy Goal Decomposer - Hierarchical Task Planning Engine.

Breaks complex tasks into manageable sub-goals with dependency management,
priority ordering, resource estimation, and parallel execution planning.
Part of the AI-Native Buddy Agent system.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import logging

logger = logging.getLogger(__name__)


class DecompositionStrategy(str, Enum):
    """Strategies for breaking down goals."""
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    DEPENDENCY_FIRST = "dependency_first"
    PARALLEL_OPTIMAL = "parallel_optimal"
    COST_AWARE = "cost_aware"


class SubGoalType(str, Enum):
    """Classification of sub-goal types."""
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    SYNTHESIS = "synthesis"
    DECISION = "decision"
    COMMUNICATION = "communication"


class DependencyType(str, Enum):
    """Types of dependencies between sub-goals."""
    HARD = "hard"          # Must complete before successor starts
    SOFT = "soft"          # Should complete before, but can proceed
    DATA = "data"          # Output data is input to successor
    APPROVAL = "approval"  # Requires human approval
    CONDITIONAL = "conditional"  # Only if certain condition met


@dataclass
class SubGoal:
    """A single sub-goal within a decomposed task."""
    sub_id: str
    description: str
    sub_type: SubGoalType
    parent_id: str | None = None
    dependencies: list[str] = field(default_factory=list)
    dependency_types: dict[str, DependencyType] = field(default_factory=dict)
    priority: int = 0
    estimated_tokens: int = 0
    estimated_duration_ms: float = 0.0
    status: str = "pending"
    assigned_agent: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalTree:
    """A hierarchical decomposition of a complex goal."""
    goal_id: str
    root_description: str
    sub_goals: dict[str, SubGoal] = field(default_factory=dict)
    execution_order: list[list[str]] = field(default_factory=list)  # Topological layers
    strategy: DecompositionStrategy = DecompositionStrategy.DEPENDENCY_FIRST
    total_estimated_tokens: int = 0
    total_estimated_duration_ms: float = 0.0
    max_parallelism: int = 1
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    context: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def get_executable_layer(self) -> list[SubGoal]:
        """Get the next layer of sub-goals ready for execution."""
        ready = []
        completed_ids = {
            sg.sub_id for sg in self.sub_goals.values()
            if sg.status in ("completed", "skipped")
        }
        for sg in self.sub_goals.values():
            if sg.status != "pending":
                continue
            deps_met = all(
                dep in completed_ids or self.sub_goals.get(dep, SubGoal(sub_id=dep, description="", sub_type=SubGoalType.EXECUTION)).status == "skipped"
                for dep in sg.dependencies
            )
            if deps_met:
                ready.append(sg)
        ready.sort(key=lambda s: s.priority, reverse=True)
        return ready

    def get_progress(self) -> dict[str, Any]:
        total = len(self.sub_goals)
        if total == 0:
            return {"total": 0, "completed": 0, "in_progress": 0, "pending": 0, "failed": 0, "percentage": 0.0}
        completed = sum(1 for s in self.sub_goals.values() if s.status == "completed")
        in_progress = sum(1 for s in self.sub_goals.values() if s.status == "in_progress")
        failed = sum(1 for s in self.sub_goals.values() if s.status == "failed")
        pending = total - completed - in_progress - failed
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "failed": failed,
            "percentage": round(completed / total * 100, 1),
        }

    def get_critical_path(self) -> list[str]:
        """Compute the critical path through the dependency graph."""
        durations: dict[str, float] = {}
        for sg in self.sub_goals.values():
            durations[sg.sub_id] = sg.estimated_duration_ms or 1.0

        longest_path: dict[str, float] = {}
        predecessor: dict[str, str | None] = {}

        def dfs(node_id: str) -> float:
            if node_id in longest_path:
                return longest_path[node_id]
            sg = self.sub_goals.get(node_id)
            if not sg:
                return 0.0
            max_pred = 0.0
            best_pred: str | None = None
            for dep in sg.dependencies:
                d = dfs(dep)
                if d > max_pred:
                    max_pred = d
                    best_pred = dep
            longest_path[node_id] = max_pred + durations.get(node_id, 1.0)
            predecessor[node_id] = best_pred
            return longest_path[node_id]

        for sg_id in self.sub_goals:
            dfs(sg_id)

        if not longest_path:
            return []

        end_node = max(longest_path, key=lambda k: longest_path[k])
        path: list[str] = []
        current: str | None = end_node
        while current is not None:
            path.append(current)
            current = predecessor.get(current)
        path.reverse()
        return path


class GoalDecomposer:
    """Hierarchical task decomposition engine.

    Breaks complex goals into structured sub-goal trees with dependency
    management, parallel execution planning, and critical path analysis.
    """

    MAX_DEPTH = 8
    MAX_SUB_GOALS = 100
    DEFAULT_PARALLELISM = 4

    def __init__(self) -> None:
        self._goal_trees: dict[str, GoalTree] = {}
        self._decomposition_strategies: dict[str, Callable] = {
            DecompositionStrategy.BREADTH_FIRST: self._decompose_breadth_first,
            DecompositionStrategy.DEPTH_FIRST: self._decompose_depth_first,
            DecompositionStrategy.DEPENDENCY_FIRST: self._decompose_dependency_first,
            DecompositionStrategy.PARALLEL_OPTIMAL: self._decompose_parallel_optimal,
            DecompositionStrategy.COST_AWARE: self._decompose_cost_aware,
        }
        self._total_decompositions: int = 0
        self._total_sub_goals: int = 0

    # ── Public API ────────────────────────────────────────────────

    def decompose(
        self,
        description: str,
        strategy: DecompositionStrategy = DecompositionStrategy.DEPENDENCY_FIRST,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        max_parallelism: int = DEFAULT_PARALLELISM,
    ) -> GoalTree:
        """Decompose a complex goal into a hierarchical sub-goal tree."""
        goal_id = f"goal-{uuid.uuid4().hex[:12]}"
        tree = GoalTree(
            goal_id=goal_id,
            root_description=description,
            strategy=strategy,
            max_parallelism=max_parallelism,
            context=context or {},
            tags=tags or [],
        )

        decomposer_fn = self._decomposition_strategies.get(strategy, self._decompose_dependency_first)
        decomposer_fn(tree, description, depth=0, parent_id=None)

        self._compute_execution_order(tree)
        self._estimate_resources(tree)
        self._goal_trees[goal_id] = tree
        self._total_decompositions += 1
        self._total_sub_goals += len(tree.sub_goals)

        logger.info(f"Decomposed goal '{description[:60]}' into {len(tree.sub_goals)} sub-goals with {tree.max_parallelism} max parallelism")
        return tree

    def recompose(self, goal_id: str, feedback: str) -> GoalTree:
        """Re-decompose a goal based on execution feedback."""
        existing = self._goal_trees.get(goal_id)
        if not existing:
            raise ValueError(f"Goal tree not found: {goal_id}")

        new_tree = self.decompose(
            description=existing.root_description,
            strategy=existing.strategy,
            context={**existing.context, "feedback": feedback},
            tags=existing.tags,
            max_parallelism=existing.max_parallelism,
        )
        new_tree.goal_id = goal_id
        self._goal_trees[goal_id] = new_tree
        return new_tree

    def get_tree(self, goal_id: str) -> GoalTree | None:
        return self._goal_trees.get(goal_id)

    def update_sub_goal(
        self,
        goal_id: str,
        sub_id: str,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        assigned_agent: str | None = None,
    ) -> SubGoal | None:
        """Update the status of a sub-goal within a goal tree."""
        tree = self._goal_trees.get(goal_id)
        if not tree:
            return None
        sg = tree.sub_goals.get(sub_id)
        if not sg:
            return None

        if status:
            sg.status = status
            if status == "in_progress" and sg.started_at is None:
                sg.started_at = time.time()
            elif status in ("completed", "failed", "skipped"):
                sg.completed_at = time.time()
        if result is not None:
            sg.result = result
        if error is not None:
            sg.error = error
        if assigned_agent is not None:
            sg.assigned_agent = assigned_agent

        if tree.completed_at is None:
            progress = tree.get_progress()
            if progress["pending"] == 0 and progress["in_progress"] == 0:
                tree.completed_at = time.time()
                logger.info(f"Goal tree '{goal_id}' fully executed")

        return sg

    def get_next_layer(self, goal_id: str) -> list[SubGoal]:
        """Get the next layer of executable sub-goals."""
        tree = self._goal_trees.get(goal_id)
        if not tree:
            return []
        return tree.get_executable_layer()

    def get_progress(self, goal_id: str) -> dict[str, Any]:
        tree = self._goal_trees.get(goal_id)
        if not tree:
            return {"error": "Goal tree not found"}
        return tree.get_progress()

    def get_critical_path(self, goal_id: str) -> list[str]:
        tree = self._goal_trees.get(goal_id)
        if not tree:
            return []
        return tree.get_critical_path()

    def list_trees(self) -> list[dict[str, Any]]:
        return [
            {
                "goal_id": t.goal_id,
                "description": t.root_description[:100],
                "strategy": t.strategy.value,
                "sub_goals": len(t.sub_goals),
                "progress": t.get_progress(),
                "created_at": t.created_at,
                "completed_at": t.completed_at,
                "tags": t.tags,
            }
            for t in self._goal_trees.values()
        ]

    def get_stats(self) -> dict[str, Any]:
        active = sum(1 for t in self._goal_trees.values() if t.completed_at is None)
        completed = self._total_decompositions - active
        return {
            "total_decompositions": self._total_decompositions,
            "total_sub_goals": self._total_sub_goals,
            "active_goal_trees": active,
            "completed_goal_trees": completed,
            "avg_sub_goals_per_tree": round(self._total_sub_goals / max(self._total_decompositions, 1), 1),
        }

    # ── Decomposition Strategies ─────────────────────────────────

    def _decompose_dependency_first(
        self,
        tree: GoalTree,
        description: str,
        depth: int,
        parent_id: str | None,
    ) -> None:
        """Dependency-first: break into phases where each phase depends on the previous."""
        if depth >= self.MAX_DEPTH or len(tree.sub_goals) >= self.MAX_SUB_GOALS:
            return

        phases = self._identify_phases(description)
        prev_id: str | None = None

        for i, phase in enumerate(phases):
            sub_id = f"sg-{uuid.uuid4().hex[:8]}"
            sg = SubGoal(
                sub_id=sub_id,
                description=phase["description"],
                sub_type=SubGoalType(phase.get("type", "execution")),
                parent_id=parent_id,
                priority=len(phases) - i,
                estimated_tokens=phase.get("estimated_tokens", 500),
                estimated_duration_ms=phase.get("estimated_duration_ms", 2000),
            )
            if prev_id:
                sg.dependencies.append(prev_id)
                sg.dependency_types[prev_id] = DependencyType.HARD
            tree.sub_goals[sub_id] = sg

            if phase.get("sub_phases"):
                self._decompose_dependency_first(tree, phase["description"], depth + 1, sub_id)
            prev_id = sub_id

    def _decompose_breadth_first(
        self,
        tree: GoalTree,
        description: str,
        depth: int,
        parent_id: str | None,
    ) -> None:
        """Breadth-first: all sub-tasks at same level, maximally parallel."""
        if depth >= self.MAX_DEPTH or len(tree.sub_goals) >= self.MAX_SUB_GOALS:
            return

        tasks = self._identify_parallel_tasks(description)
        for i, task in enumerate(tasks):
            sub_id = f"sg-{uuid.uuid4().hex[:8]}"
            sg = SubGoal(
                sub_id=sub_id,
                description=task["description"],
                sub_type=SubGoalType(task.get("type", "execution")),
                parent_id=parent_id,
                priority=10 - i,
                estimated_tokens=task.get("estimated_tokens", 300),
                estimated_duration_ms=task.get("estimated_duration_ms", 1000),
            )
            tree.sub_goals[sub_id] = sg

    def _decompose_depth_first(
        self,
        tree: GoalTree,
        description: str,
        depth: int,
        parent_id: str | None,
    ) -> None:
        """Depth-first: break into sequential steps, deeply decompose each."""
        if depth >= self.MAX_DEPTH or len(tree.sub_goals) >= self.MAX_SUB_GOALS:
            return

        steps = self._identify_sequential_steps(description)
        for i, step in enumerate(steps):
            sub_id = f"sg-{uuid.uuid4().hex[:8]}"
            sg = SubGoal(
                sub_id=sub_id,
                description=step["description"],
                sub_type=SubGoalType(step.get("type", "execution")),
                parent_id=parent_id,
                priority=len(steps) - i,
                estimated_tokens=step.get("estimated_tokens", 400),
                estimated_duration_ms=step.get("estimated_duration_ms", 1500),
            )
            if i > 0:
                prev_id = list(tree.sub_goals.keys())[-1] if tree.sub_goals else None
                if prev_id:
                    sg.dependencies.append(prev_id)
                    sg.dependency_types[prev_id] = DependencyType.HARD
            tree.sub_goals[sub_id] = sg

            if step.get("decomposable", True):
                self._decompose_depth_first(tree, step["description"], depth + 1, sub_id)

    def _decompose_parallel_optimal(
        self,
        tree: GoalTree,
        description: str,
        depth: int,
        parent_id: str | None,
    ) -> None:
        """Parallel-optimal: maximize parallel execution while respecting dependencies."""
        if depth >= self.MAX_DEPTH or len(tree.sub_goals) >= self.MAX_SUB_GOALS:
            return

        # Identify independent and dependent tasks
        independent = self._identify_parallel_tasks(description)
        dependent = self._identify_dependent_tasks(description)

        # Add independent tasks (no dependencies)
        for i, task in enumerate(independent):
            sub_id = f"sg-{uuid.uuid4().hex[:8]}"
            sg = SubGoal(
                sub_id=sub_id,
                description=task["description"],
                sub_type=SubGoalType(task.get("type", "execution")),
                parent_id=parent_id,
                priority=10,
                estimated_tokens=task.get("estimated_tokens", 300),
                estimated_duration_ms=task.get("estimated_duration_ms", 1000),
            )
            tree.sub_goals[sub_id] = sg

        # Add dependent tasks (depend on specific independent ones)
        for i, task in enumerate(dependent):
            sub_id = f"sg-{uuid.uuid4().hex[:8]}"
            sg = SubGoal(
                sub_id=sub_id,
                description=task["description"],
                sub_type=SubGoalType(task.get("type", "synthesis")),
                parent_id=parent_id,
                priority=5,
                estimated_tokens=task.get("estimated_tokens", 500),
                estimated_duration_ms=task.get("estimated_duration_ms", 1500),
            )
            # Depend on all independent tasks (synthesis phase)
            for ind_sg in tree.sub_goals.values():
                if ind_sg.priority == 10 and ind_sg.parent_id == parent_id:
                    sg.dependencies.append(ind_sg.sub_id)
                    sg.dependency_types[ind_sg.sub_id] = DependencyType.DATA
            tree.sub_goals[sub_id] = sg

    def _decompose_cost_aware(
        self,
        tree: GoalTree,
        description: str,
        depth: int,
        parent_id: str | None,
    ) -> None:
        """Cost-aware: minimize token usage by ordering cheap tasks first."""
        if depth >= self.MAX_DEPTH or len(tree.sub_goals) >= self.MAX_SUB_GOALS:
            return

        tasks = self._identify_parallel_tasks(description)
        for task in tasks:
            sub_id = f"sg-{uuid.uuid4().hex[:8]}"
            sg = SubGoal(
                sub_id=sub_id,
                description=task["description"],
                sub_type=SubGoalType(task.get("type", "execution")),
                parent_id=parent_id,
                priority=task.get("estimated_tokens", 500),  # Lower tokens = higher priority
                estimated_tokens=task.get("estimated_tokens", 300),
                estimated_duration_ms=task.get("estimated_duration_ms", 1000),
            )
            tree.sub_goals[sub_id] = sg

    # ── Task Analysis ────────────────────────────────────────────

    def _identify_phases(self, description: str) -> list[dict[str, Any]]:
        """Identify sequential phases in a task description."""
        phase_keywords = {
            "analyze": "analysis",
            "understand": "analysis",
            "research": "analysis",
            "plan": "planning",
            "design": "planning",
            "architect": "planning",
            "implement": "execution",
            "build": "execution",
            "develop": "execution",
            "code": "execution",
            "test": "validation",
            "verify": "validation",
            "validate": "validation",
            "review": "validation",
            "deploy": "execution",
            "release": "execution",
            "document": "communication",
            "summarize": "synthesis",
            "integrate": "synthesis",
            "refactor": "execution",
            "optimize": "execution",
            "debug": "validation",
            "fix": "execution",
        }

        phases: list[dict[str, Any]] = []
        desc_lower = description.lower()

        for keyword, phase_type in phase_keywords.items():
            if keyword in desc_lower:
                phases.append({
                    "description": f"{keyword.capitalize()} phase: {description}",
                    "type": phase_type,
                    "estimated_tokens": 500,
                    "estimated_duration_ms": 2000,
                    "sub_phases": False,
                })

        if not phases:
            phases = [
                {"description": f"Analyze: {description}", "type": "analysis", "estimated_tokens": 400, "estimated_duration_ms": 1500, "sub_phases": False},
                {"description": f"Execute: {description}", "type": "execution", "estimated_tokens": 600, "estimated_duration_ms": 3000, "sub_phases": False},
                {"description": f"Validate: {description}", "type": "validation", "estimated_tokens": 300, "estimated_duration_ms": 1000, "sub_phases": False},
            ]

        return phases[:8]

    def _identify_parallel_tasks(self, description: str) -> list[dict[str, Any]]:
        """Identify tasks that can run in parallel."""
        conjunctions = [" and ", " also ", " plus ", " while ", " simultaneously "]
        tasks: list[dict[str, Any]] = []

        for conj in conjunctions:
            if conj in description.lower():
                parts = description.lower().split(conj)
                for part in parts:
                    if part.strip():
                        tasks.append({
                            "description": part.strip().capitalize(),
                            "type": "execution",
                            "estimated_tokens": 300,
                            "estimated_duration_ms": 1000,
                        })
                break

        if not tasks:
            tasks = [{"description": description, "type": "execution", "estimated_tokens": 500, "estimated_duration_ms": 2000}]

        return tasks[:6]

    def _identify_sequential_steps(self, description: str) -> list[dict[str, Any]]:
        """Identify steps that must execute sequentially."""
        sequential_markers = [" then ", " after ", " before ", " next ", " finally ", " subsequently "]
        steps: list[dict[str, Any]] = []

        for marker in sequential_markers:
            if marker in description.lower():
                parts = description.lower().split(marker)
                for part in parts:
                    if part.strip():
                        steps.append({
                            "description": part.strip().capitalize(),
                            "type": "execution",
                            "estimated_tokens": 400,
                            "estimated_duration_ms": 1500,
                            "decomposable": True,
                        })
                break

        if not steps:
            steps = [
                {"description": f"Prepare: {description}", "type": "planning", "estimated_tokens": 300, "estimated_duration_ms": 1000, "decomposable": True},
                {"description": f"Execute: {description}", "type": "execution", "estimated_tokens": 500, "estimated_duration_ms": 2500, "decomposable": True},
                {"description": f"Finalize: {description}", "type": "synthesis", "estimated_tokens": 300, "estimated_duration_ms": 1000, "decomposable": False},
            ]

        return steps[:8]

    def _identify_dependent_tasks(self, description: str) -> list[dict[str, Any]]:
        """Identify tasks that depend on other tasks."""
        dependent_markers = ["based on", "depends on", "requires", "after", "following"]
        tasks: list[dict[str, Any]] = []

        for marker in dependent_markers:
            if marker in description.lower():
                tasks.append({
                    "description": f"Synthesis: {description}",
                    "type": "synthesis",
                    "estimated_tokens": 500,
                    "estimated_duration_ms": 1500,
                })
                break

        if not tasks:
            tasks.append({
                "description": f"Integrate: {description}",
                "type": "synthesis",
                "estimated_tokens": 400,
                "estimated_duration_ms": 1200,
            })

        return tasks[:3]

    # ── Internal Helpers ─────────────────────────────────────────

    def _compute_execution_order(self, tree: GoalTree) -> None:
        """Compute topological execution layers for the goal tree."""
        in_degree: dict[str, int] = {sg_id: len(sg.dependencies) for sg_id, sg in tree.sub_goals.items()}
        ready: list[str] = [sg_id for sg_id, deg in in_degree.items() if deg == 0]
        layers: list[list[str]] = []
        visited: set[str] = set()

        while ready:
            layer = sorted(ready, key=lambda sid: tree.sub_goals[sid].priority, reverse=True)
            layers.append(layer)
            visited.update(ready)
            next_ready: list[str] = []

            for sid in ready:
                for sg_id, sg in tree.sub_goals.items():
                    if sid in sg.dependencies and sg_id not in visited:
                        in_degree[sg_id] -= 1
                        if in_degree[sg_id] == 0:
                            next_ready.append(sg_id)

            ready = list(set(next_ready))

        tree.execution_order = layers
        tree.max_parallelism = max((len(l) for l in layers), default=1)

    def _estimate_resources(self, tree: GoalTree) -> None:
        """Estimate total resources required for the goal tree."""
        tree.total_estimated_tokens = sum(sg.estimated_tokens for sg in tree.sub_goals.values())
        tree.total_estimated_duration_ms = sum(sg.estimated_duration_ms for sg in tree.sub_goals.values())


# ── Global Singleton ─────────────────────────────────────────────

goal_decomposer = GoalDecomposer()