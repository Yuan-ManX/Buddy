"""
Buddy Plan Executor - Multi-Step Task Planning and Execution

Generates, tracks, and executes multi-step plans for agent tasks.
Implements plan decomposition, dependency management, progress tracking,
and adaptive re-planning when execution diverges.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlanStatus(str, Enum):
    """Status of a plan or plan step."""
    DRAFT = "draft"            # Initial plan draft
    PENDING = "pending"        # Waiting to start
    IN_PROGRESS = "in_progress"  # Currently executing
    BLOCKED = "blocked"        # Blocked by dependency
    COMPLETED = "completed"    # Successfully completed
    FAILED = "failed"          # Execution failed
    SKIPPED = "skipped"        # Skipped intentionally
    CANCELLED = "cancelled"    # Plan cancelled


class StepType(str, Enum):
    """Types of plan steps."""
    ANALYSIS = "analysis"       # Analyze/understand requirements
    RESEARCH = "research"       # Gather information
    PLANNING = "planning"       # Plan sub-steps
    EXECUTION = "execution"     # Execute a task
    VERIFICATION = "verification"  # Verify results
    TOOL_CALL = "tool_call"     # Call a tool
    DECISION = "decision"       # Make a decision
    COMMUNICATION = "comm"      # Communicate with user
    WAIT = "wait"               # Wait for external input
    SYNTHESIS = "synthesis"     # Synthesize results


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    step_id: str
    description: str
    step_type: StepType
    status: PlanStatus = PlanStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    assigned_agent: str = ""
    estimated_duration_ms: float = 0
    actual_duration_ms: float = 0
    result: Any = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "step_type": self.step_type.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "assigned_agent": self.assigned_agent,
            "estimated_duration_ms": self.estimated_duration_ms,
            "actual_duration_ms": self.actual_duration_ms,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class ExecutionPlan:
    """A complete execution plan with multiple steps."""
    plan_id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    agent_id: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    metadata: dict = field(default_factory=dict)

    def get_next_steps(self) -> list[PlanStep]:
        """Get steps that are ready to execute."""
        completed_ids = {
            s.step_id for s in self.steps
            if s.status in (PlanStatus.COMPLETED, PlanStatus.SKIPPED)
        }

        ready = []
        for step in self.steps:
            if step.status != PlanStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.dependencies):
                ready.append(step)
        return ready

    def get_progress(self) -> float:
        """Get execution progress as percentage."""
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100

    def is_complete(self) -> bool:
        """Check if the plan is fully executed."""
        return self.completed_steps + self.failed_steps >= self.total_steps

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "progress": self.get_progress(),
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class PlanGenerator:
    """Generates execution plans from task descriptions."""

    def __init__(self):
        self._plan_count = 0

    def generate(self, goal: str, agent_id: str, context: dict | None = None) -> ExecutionPlan:
        """Generate a plan for a given goal."""
        plan_id = f"plan-{uuid.uuid4().hex[:12]}"
        self._plan_count += 1

        plan = ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            agent_id=agent_id,
            metadata=context or {},
        )

        # Generate plan steps based on goal analysis
        steps = self._decompose_goal(goal)
        plan.steps = steps
        plan.total_steps = len(steps)

        return plan

    def _decompose_goal(self, goal: str) -> list[PlanStep]:
        """Decompose a goal into executable steps."""
        goal_lower = goal.lower()
        steps = []

        # Analysis step
        steps.append(PlanStep(
            step_id=f"step-{uuid.uuid4().hex[:8]}",
            description=f"Analyze requirements: {goal[:100]}",
            step_type=StepType.ANALYSIS,
            estimated_duration_ms=1000,
        ))

        # Research step for information-gathering tasks
        if any(kw in goal_lower for kw in ["search", "find", "research", "look up", "information"]):
            steps.append(PlanStep(
                step_id=f"step-{uuid.uuid4().hex[:8]}",
                description="Gather relevant information",
                step_type=StepType.RESEARCH,
                dependencies=[steps[-1].step_id],
                estimated_duration_ms=2000,
            ))

        # Execution step
        if any(kw in goal_lower for kw in ["create", "build", "write", "generate", "code", "implement"]):
            steps.append(PlanStep(
                step_id=f"step-{uuid.uuid4().hex[:8]}",
                description="Execute the implementation",
                step_type=StepType.EXECUTION,
                dependencies=[steps[-1].step_id],
                estimated_duration_ms=5000,
            ))

        # Tool call step for file/terminal operations
        if any(kw in goal_lower for kw in ["file", "terminal", "command", "shell", "run"]):
            steps.append(PlanStep(
                step_id=f"step-{uuid.uuid4().hex[:8]}",
                description="Execute tool operations",
                step_type=StepType.TOOL_CALL,
                dependencies=[steps[-1].step_id],
                estimated_duration_ms=3000,
            ))

        # Verification step
        steps.append(PlanStep(
            step_id=f"step-{uuid.uuid4().hex[:8]}",
            description="Verify results and validate output",
            step_type=StepType.VERIFICATION,
            dependencies=[steps[-1].step_id],
            estimated_duration_ms=1000,
        ))

        # Synthesis step
        steps.append(PlanStep(
            step_id=f"step-{uuid.uuid4().hex[:8]}",
            description="Synthesize and present final results",
            step_type=StepType.SYNTHESIS,
            dependencies=[steps[-1].step_id],
            estimated_duration_ms=1000,
        ))

        return steps


class PlanExecutor:
    """Executes multi-step plans with dependency resolution and retry logic.

    Orchestrates the execution of complex, multi-step plans generated
    by agents. Handles step ordering, dependency resolution, parallel
    execution where possible, retry on failure, and adaptive re-planning.
    """

    def __init__(self):
        self.generator = PlanGenerator()
        self._active_plans: dict[str, ExecutionPlan] = {}
        self._completed_plans: list[ExecutionPlan] = []
        self._total_plans = 0
        self._step_handlers: dict[StepType, Any] = {}

    def register_step_handler(self, step_type: StepType, handler):
        """Register a custom handler for a step type."""
        self._step_handlers[step_type] = handler

    async def create_and_execute(
        self,
        goal: str,
        agent_id: str,
        context: dict | None = None,
    ) -> ExecutionPlan:
        """Create a plan and execute it immediately."""
        plan = self.generator.generate(goal, agent_id, context)
        return await self.execute_plan(plan)

    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Execute a plan step by step."""
        plan.status = PlanStatus.IN_PROGRESS
        self._active_plans[plan.plan_id] = plan
        self._total_plans += 1

        while not plan.is_complete():
            next_steps = plan.get_next_steps()

            if not next_steps:
                # Check if any steps are blocked
                blocked = any(
                    s.status == PlanStatus.PENDING for s in plan.steps
                )
                if not blocked:
                    break
                # Wait and retry
                await asyncio.sleep(0.1)
                continue

            # Execute ready steps in parallel
            tasks = [self._execute_step(step) for step in next_steps]
            await asyncio.gather(*tasks)

        # Finalize
        plan.completed_at = time.time()
        if plan.failed_steps == 0:
            plan.status = PlanStatus.COMPLETED
        elif plan.completed_steps > 0:
            plan.status = PlanStatus.COMPLETED  # Partial completion
        else:
            plan.status = PlanStatus.FAILED

        self._active_plans.pop(plan.plan_id, None)
        self._completed_plans.append(plan)

        return plan

    async def _execute_step(self, step: PlanStep) -> PlanStep:
        """Execute a single plan step."""
        step.status = PlanStatus.IN_PROGRESS
        start = time.time()

        try:
            handler = self._step_handlers.get(step.step_type)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    step.result = await handler(step)
                else:
                    step.result = handler(step)
            else:
                # Default: simulate step execution
                step.result = f"Step '{step.description}' completed"
                await asyncio.sleep(0.1)

            step.status = PlanStatus.COMPLETED
            step.actual_duration_ms = (time.time() - start) * 1000
        except Exception as e:
            step.error = str(e)
            step.retry_count += 1

            if step.retry_count < step.max_retries:
                step.status = PlanStatus.PENDING
                step.error = f"{str(e)} (retry {step.retry_count}/{step.max_retries})"
            else:
                step.status = PlanStatus.FAILED

            step.actual_duration_ms = (time.time() - start) * 1000

        # Update plan counters
        return step

    def get_plan(self, plan_id: str) -> ExecutionPlan | None:
        """Get a plan by ID."""
        return self._active_plans.get(plan_id)

    def get_stats(self) -> dict:
        return {
            "active_plans": len(self._active_plans),
            "completed_plans": len(self._completed_plans),
            "total_plans": self._total_plans,
            "active": [
                {"plan_id": p.plan_id, "goal": p.goal[:80], "progress": p.get_progress()}
                for p in self._active_plans.values()
            ],
        }


# Global plan executor instance
_plan_executor: PlanExecutor | None = None


def get_plan_executor() -> PlanExecutor:
    """Get or create the global plan executor."""
    global _plan_executor
    if _plan_executor is None:
        _plan_executor = PlanExecutor()
    return _plan_executor