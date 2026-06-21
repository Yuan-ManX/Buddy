"""
Buddy Autonomous Loop Engine.

Implements autonomous goal-driven execution loops where agents can
independently pursue objectives, decompose tasks, monitor progress,
and self-correct without continuous human intervention.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class GoalStatus(Enum):
    """Status of an autonomous goal."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    AWAITING_INPUT = "awaiting_input"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Status of a goal execution step."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class GoalStep:
    """A single step within a goal's execution plan."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    action: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.QUEUED
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    depends_on: list[str] = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class AutonomousGoal:
    """A goal to be pursued autonomously by an agent."""
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    title: str = ""
    description: str = ""
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 5
    steps: list[GoalStep] = field(default_factory=list)
    current_step_index: int = 0
    max_iterations: int = 20
    iteration_count: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    parent_goal_id: Optional[str] = None
    sub_goals: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class AutonomousLoopEngine:
    """
    Core engine for autonomous agent goal pursuit.

    Manages the full lifecycle of autonomous goal execution including
    planning, decomposition, execution, monitoring, and self-correction.
    """

    MAX_CONCURRENT_GOALS = 5
    DEFAULT_MAX_ITERATIONS = 20
    GOAL_TIMEOUT = 300.0  # seconds

    def __init__(self):
        self._active_goals: dict[str, AutonomousGoal] = {}
        self._completed_goals: dict[str, AutonomousGoal] = {}
        self._goal_queue: list[AutonomousGoal] = []
        self._step_handlers: dict[str, Callable] = {}
        self._progress_callbacks: list[Callable] = []
        self._lock = asyncio.Lock()
        self._running = False

    # ── Goal Management ────────────────────────────────────────────

    def create_goal(
        self,
        title: str,
        description: str,
        priority: int = 5,
        max_iterations: int = 20,
        context: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ) -> AutonomousGoal:
        """Create a new autonomous goal."""
        goal = AutonomousGoal(
            title=title,
            description=description,
            priority=priority,
            max_iterations=max_iterations,
            context=context or {},
            tags=tags or [],
        )
        self._goal_queue.append(goal)
        self._goal_queue.sort(key=lambda g: g.priority, reverse=True)
        logger.info("Goal created: %s (priority=%d)", title, priority)
        return goal

    def add_step(
        self,
        goal: AutonomousGoal,
        description: str,
        action: str = "",
        tool_name: str = "",
        arguments: Optional[dict[str, Any]] = None,
        depends_on: Optional[list[str]] = None,
        max_retries: int = 3,
    ) -> GoalStep:
        """Add an execution step to a goal."""
        step = GoalStep(
            description=description,
            action=action,
            tool_name=tool_name,
            arguments=arguments or {},
            depends_on=depends_on or [],
            max_retries=max_retries,
        )
        goal.steps.append(step)
        return step

    def add_sub_goal(
        self,
        parent: AutonomousGoal,
        title: str,
        description: str,
        priority: Optional[int] = None,
    ) -> AutonomousGoal:
        """Create a sub-goal linked to a parent goal."""
        sub_goal = self.create_goal(
            title=title,
            description=description,
            priority=priority or parent.priority,
            context=parent.context,
            tags=parent.tags,
        )
        sub_goal.parent_goal_id = parent.goal_id
        parent.sub_goals.append(sub_goal.goal_id)
        return sub_goal

    def get_goal(self, goal_id: str) -> Optional[AutonomousGoal]:
        """Get a goal by ID."""
        return self._active_goals.get(goal_id) or self._completed_goals.get(goal_id)

    def list_active_goals(self) -> list[AutonomousGoal]:
        """List all currently active goals."""
        return list(self._active_goals.values())

    def list_completed_goals(self) -> list[AutonomousGoal]:
        """List all completed goals."""
        return list(self._completed_goals.values())

    # ── Step Handler Registration ──────────────────────────────────

    def register_step_handler(self, action: str, handler: Callable) -> None:
        """Register a handler for a specific action type."""
        self._step_handlers[action] = handler
        logger.info("Step handler registered for action: %s", action)

    def on_progress(self, callback: Callable) -> None:
        """Register a progress callback."""
        self._progress_callbacks.append(callback)

    # ── Execution Loop ─────────────────────────────────────────────

    async def execute_goal(self, goal: AutonomousGoal) -> dict[str, Any]:
        """Execute a single goal to completion."""
        start_time = time.time()
        goal.status = GoalStatus.PLANNING
        self._active_goals[goal.goal_id] = goal

        try:
            # Planning phase
            if not goal.steps:
                await self._plan_goal(goal)

            goal.status = GoalStatus.EXECUTING

            # Execution loop
            while goal.current_step_index < len(goal.steps) and goal.iteration_count < goal.max_iterations:
                # Check timeout
                if time.time() - start_time > self.GOAL_TIMEOUT:
                    goal.status = GoalStatus.FAILED
                    logger.warning("Goal %s timed out", goal.goal_id)
                    break

                step = goal.steps[goal.current_step_index]
                goal.iteration_count += 1

                await self._execute_step(goal, step)

                if step.status == StepStatus.FAILED:
                    if step.retry_count < step.max_retries:
                        step.status = StepStatus.RETRYING
                        step.retry_count += 1
                        logger.info("Retrying step %s (attempt %d)", step.step_id, step.retry_count)
                        continue
                    else:
                        goal.status = GoalStatus.FAILED
                        logger.error("Goal %s failed at step %s", goal.goal_id, step.step_id)
                        break

                if step.status == StepStatus.SUCCESS:
                    goal.current_step_index += 1

                # Check for dependencies
                while goal.current_step_index < len(goal.steps):
                    next_step = goal.steps[goal.current_step_index]
                    if all(
                        self._get_step_status(goal, dep_id) == StepStatus.SUCCESS
                        for dep_id in next_step.depends_on
                    ):
                        break
                    goal.current_step_index += 1

                await self._notify_progress(goal)

            if goal.current_step_index >= len(goal.steps):
                goal.status = GoalStatus.COMPLETED
                goal.completed_at = time.time()

        except Exception as e:
            goal.status = GoalStatus.FAILED
            logger.error("Goal %s execution error: %s", goal.goal_id, e)

        finally:
            self._active_goals.pop(goal.goal_id, None)
            self._completed_goals[goal.goal_id] = goal

        return {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "status": goal.status.value,
            "total_steps": len(goal.steps),
            "completed_steps": sum(1 for s in goal.steps if s.status == StepStatus.SUCCESS),
            "failed_steps": sum(1 for s in goal.steps if s.status == StepStatus.FAILED),
            "iterations": goal.iteration_count,
            "duration_s": round(time.time() - start_time, 2),
        }

    async def execute_all(self) -> list[dict[str, Any]]:
        """Execute all queued goals concurrently within limits."""
        self._running = True
        results = []

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_GOALS)

        async def _execute_with_limit(goal: AutonomousGoal):
            async with semaphore:
                return await self.execute_goal(goal)

        while self._goal_queue:
            batch = self._goal_queue[: self.MAX_CONCURRENT_GOALS]
            self._goal_queue = self._goal_queue[self.MAX_CONCURRENT_GOALS :]

            tasks = [_execute_with_limit(g) for g in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

        self._running = False
        return results

    def pause_goal(self, goal_id: str) -> bool:
        """Pause an active goal."""
        goal = self._active_goals.get(goal_id)
        if goal and goal.status == GoalStatus.EXECUTING:
            goal.status = GoalStatus.PAUSED
            return True
        return False

    def resume_goal(self, goal_id: str) -> bool:
        """Resume a paused goal."""
        goal = self._active_goals.get(goal_id)
        if goal and goal.status == GoalStatus.PAUSED:
            goal.status = GoalStatus.EXECUTING
            return True
        return False

    def cancel_goal(self, goal_id: str) -> bool:
        """Cancel a goal."""
        goal = self._active_goals.get(goal_id)
        if goal:
            goal.status = GoalStatus.CANCELLED
            self._active_goals.pop(goal_id)
            self._completed_goals[goal_id] = goal
            return True
        return False

    # ── Internal Methods ───────────────────────────────────────────

    async def _plan_goal(self, goal: AutonomousGoal) -> None:
        """Generate an execution plan for a goal using AI reasoning."""
        # In production, this would use the LLM to decompose the goal
        # For now, create a minimal plan structure
        goal.steps = [
            GoalStep(
                description=f"Analyze: {goal.description}",
                action="analyze",
            ),
            GoalStep(
                description=f"Execute: {goal.description}",
                action="execute",
            ),
            GoalStep(
                description=f"Verify: {goal.description}",
                action="verify",
            ),
        ]
        logger.info("Plan generated for goal %s: %d steps", goal.goal_id, len(goal.steps))

    async def _execute_step(self, goal: AutonomousGoal, step: GoalStep) -> None:
        """Execute a single goal step."""
        step.status = StepStatus.RUNNING
        step.started_at = time.time()

        try:
            handler = self._step_handlers.get(step.action)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(goal, step)
                else:
                    result = await asyncio.to_thread(handler, goal, step)
                step.result = result
                step.status = StepStatus.SUCCESS
            else:
                # Simulate step execution for testing
                await asyncio.sleep(0.1)
                step.result = {"status": "completed"}
                step.status = StepStatus.SUCCESS

        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED
            logger.error("Step %s failed: %s", step.step_id, e)

        finally:
            step.completed_at = time.time()

    def _get_step_status(self, goal: AutonomousGoal, step_id: str) -> Optional[StepStatus]:
        """Get the status of a step by ID."""
        for step in goal.steps:
            if step.step_id == step_id:
                return step.status
        return None

    async def _notify_progress(self, goal: AutonomousGoal) -> None:
        """Notify all progress callbacks."""
        progress = self.get_goal_progress(goal.goal_id)
        for callback in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.error("Progress callback error: %s", e)

    # ── Statistics ─────────────────────────────────────────────────

    def get_goal_progress(self, goal_id: str) -> dict[str, Any]:
        """Get detailed progress for a goal."""
        goal = self.get_goal(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        completed = sum(1 for s in goal.steps if s.status == StepStatus.SUCCESS)
        failed = sum(1 for s in goal.steps if s.status == StepStatus.FAILED)
        total = len(goal.steps)

        return {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "status": goal.status.value,
            "progress": round(completed / max(total, 1) * 100, 1),
            "completed_steps": completed,
            "failed_steps": failed,
            "total_steps": total,
            "current_step": goal.current_step_index,
            "iterations": goal.iteration_count,
            "sub_goals": len(goal.sub_goals),
        }

    def create_goal_from_decomposition(
        self,
        title: str,
        description: str,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        strategy: str = "dependency_first",
    ) -> AutonomousGoal:
        """Create a goal with sub-goals decomposed from the description.

        Uses the Goal Decomposer to break the task into structured sub-goals
        with dependency management and execution ordering.
        """
        from agent.agent_goal_decomposer import goal_decomposer, DecompositionStrategy

        strategy_enum = DecompositionStrategy(strategy)
        tree = goal_decomposer.decompose(
            description=description,
            strategy=strategy_enum,
            context=context,
            tags=tags,
        )

        goal = self.create_goal(
            title=title or description[:80],
            description=description,
            context=context or {},
            tags=tags or [],
        )

        # Store goal tree reference
        goal.metadata["goal_tree_id"] = tree.goal_id

        # Add sub-goals as steps
        for layer in tree.execution_order:
            for sub_id in layer:
                sg = tree.sub_goals[sub_id]
                self.add_step(
                    goal=goal,
                    description=sg.description,
                    action=sg.sub_type.value,
                    tool_name="agent_core",
                    arguments={
                        "sub_goal_id": sg.sub_id,
                        "sub_goal_type": sg.sub_type.value,
                        "estimated_tokens": sg.estimated_tokens,
                    },
                )

        logger.info(f"Created goal '{title}' with {len(tree.sub_goals)} decomposed sub-goals")
        return goal

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        return {
            "active_goals": len(self._active_goals),
            "completed_goals": len(self._completed_goals),
            "queued_goals": len(self._goal_queue),
            "total_goals": len(self._active_goals) + len(self._completed_goals) + len(self._goal_queue),
            "active_goal_ids": list(self._active_goals.keys()),
            "goals_by_status": {
                status.value: sum(
                    1 for g in list(self._active_goals.values()) + list(self._completed_goals.values())
                    if g.status == status
                )
                for status in GoalStatus
            },
        }


# Global autonomous loop engine instance
autonomous_loop = AutonomousLoopEngine()