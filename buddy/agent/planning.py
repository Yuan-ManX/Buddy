"""Buddy Planning Engine — structured task decomposition and plan execution

Enables agents to decompose complex goals into executable plans with
subtasks, dependencies, and automatic progress tracking.
"""
from __future__ import annotations
import json
import uuid
import logging
import asyncio
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.planning")


class PlanStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class PlanStep:
    id: str
    title: str
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    depends_on: list[str] = field(default_factory=list)
    result: str = ""
    started_at: str = ""
    completed_at: str = ""
    assigned_agent: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "result": self.result[:500],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "assigned_agent": self.assigned_agent,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionPlan:
    id: str
    title: str
    goal: str
    status: PlanStatus = PlanStatus.DRAFT
    steps: list[PlanStep] = field(default_factory=list)
    created_by: str = ""
    created_at: str = ""
    completed_at: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "created_by": self.created_by,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "metadata": self.metadata,
        }

    @property
    def progress(self) -> dict:
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED))
        in_progress = sum(1 for s in self.steps if s.status == StepStatus.IN_PROGRESS)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": total - completed - in_progress - failed,
            "failed": failed,
            "percentage": round(completed / max(total, 1) * 100, 1),
        }

    @property
    def next_step(self) -> PlanStep | None:
        """Get the next ready-to-execute step."""
        completed_ids = {
            s.id for s in self.steps
            if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        }
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.depends_on):
                return step
        return None

    def get_execution_order(self) -> list[list[PlanStep]]:
        """Get steps grouped by dependency level for parallel execution."""
        completed = set()
        remaining = list(self.steps)
        batches = []

        while remaining:
            batch = [
                s for s in remaining
                if all(d in completed for d in s.depends_on)
            ]
            if not batch:
                # Circular dependency or all blocked
                break
            batches.append(batch)
            for s in batch:
                completed.add(s.id)
            remaining = [s for s in remaining if s.id not in completed]

        return batches


class PlanningEngine:
    """Structured planning engine for complex task decomposition."""

    PLAN_GENERATION_PROMPT = """You are a planning system. Given a high-level goal, create a structured execution plan.

Rules:
1. Break the goal into 3-8 concrete, actionable steps
2. Each step should be independently verifiable
3. Identify dependencies between steps (step B depends on step A's output)
4. Order steps logically
5. Estimate what each step produces

Return a JSON plan with this structure:
{
  "title": "Short descriptive title",
  "steps": [
    {
      "title": "Step name",
      "description": "What this step accomplishes",
      "depends_on": []  // indices of steps this depends on (0-based)
    }
  ]
}"""

    def __init__(self, client: AsyncOpenAI | None = None):
        self.client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._plans: dict[str, ExecutionPlan] = {}

    async def generate_plan(self, goal: str, agent_id: str, model: str = "gpt-4o-mini") -> ExecutionPlan:
        """Generate an execution plan from a goal description."""
        plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.PLAN_GENERATION_PROMPT},
                    {"role": "user", "content": goal},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content or "{}"
            plan_data = json.loads(content)

        except Exception as e:
            logger.warning(f"Plan generation with LLM failed: {e}. Using structured fallback.")
            plan_data = self._fallback_plan(goal)

        steps = []
        for i, step_data in enumerate(plan_data.get("steps", [])):
            depends_on_indices = step_data.get("depends_on", [])
            depends_on_ids = []
            for idx in depends_on_indices:
                if 0 <= idx < len(plan_data.get("steps", [])):
                    depends_on_ids.append(f"step-{plan_id}-{idx}")

            steps.append(PlanStep(
                id=f"step-{plan_id}-{i}",
                title=step_data.get("title", f"Step {i+1}"),
                description=step_data.get("description", ""),
                depends_on=depends_on_ids,
            ))

        plan = ExecutionPlan(
            id=plan_id,
            title=plan_data.get("title", "Execution Plan"),
            goal=goal,
            steps=steps,
            created_by=agent_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._plans[plan_id] = plan
        logger.info(f"Plan generated: {plan_id} with {len(steps)} steps")
        return plan

    def _fallback_plan(self, goal: str) -> dict:
        """Generate a basic plan without LLM."""
        return {
            "title": f"Plan: {goal[:60]}",
            "steps": [
                {"title": "Analyze requirements", "description": "Understand the goal and gather context", "depends_on": []},
                {"title": "Research approach", "description": "Identify best methods and tools", "depends_on": [0]},
                {"title": "Execute core task", "description": "Perform the main work", "depends_on": [1]},
                {"title": "Verify results", "description": "Check outputs against requirements", "depends_on": [2]},
                {"title": "Finalize and report", "description": "Summarize findings and deliverables", "depends_on": [3]},
            ],
        }

    def get_plan(self, plan_id: str) -> ExecutionPlan | None:
        return self._plans.get(plan_id)

    def list_plans(self, agent_id: str | None = None) -> list[ExecutionPlan]:
        plans = list(self._plans.values())
        if agent_id:
            plans = [p for p in plans if p.created_by == agent_id]
        return sorted(plans, key=lambda p: p.created_at, reverse=True)

    def update_step_status(self, plan_id: str, step_id: str, status: StepStatus, result: str = "") -> bool:
        plan = self._plans.get(plan_id)
        if not plan:
            return False

        for step in plan.steps:
            if step.id == step_id:
                step.status = status
                if status == StepStatus.IN_PROGRESS and not step.started_at:
                    step.started_at = datetime.now(timezone.utc).isoformat()
                if status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED):
                    step.completed_at = datetime.now(timezone.utc).isoformat()
                if result:
                    step.result = result
                break

        # Update plan status
        self._sync_plan_status(plan)
        return True

    def _sync_plan_status(self, plan: ExecutionPlan):
        statuses = {s.status for s in plan.steps}
        if all(s in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in plan.steps):
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now(timezone.utc).isoformat()
        elif StepStatus.FAILED in statuses and all(
            s in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED)
            for s in plan.steps
        ):
            plan.status = PlanStatus.FAILED
        elif any(s == StepStatus.IN_PROGRESS for s in plan.steps):
            plan.status = PlanStatus.IN_PROGRESS
        elif plan.status == PlanStatus.DRAFT:
            plan.status = PlanStatus.APPROVED

    async def execute_plan(
        self,
        plan_id: str,
        step_executor: Any,
        model: str = "gpt-4o-mini",
    ) -> ExecutionPlan:
        """Execute all steps in a plan sequentially, respecting dependencies."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        plan.status = PlanStatus.IN_PROGRESS
        batches = plan.get_execution_order()

        for batch in batches:
            # Steps within the same batch can run in parallel
            tasks = []
            for step in batch:
                task = self._execute_step(step, plan.goal, step_executor, model)
                tasks.append(task)

            await asyncio.gather(*tasks)

        self._sync_plan_status(plan)
        return plan

    async def _execute_step(
        self,
        step: PlanStep,
        goal: str,
        executor: Any,
        model: str,
    ):
        """Execute a single plan step."""
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now(timezone.utc).isoformat()

        try:
            prompt = (
                f"Goal: {goal}\n\n"
                f"Current step: {step.title}\n"
                f"Description: {step.description}\n\n"
                f"Execute this step. Provide the result concisely."
            )
            result = await executor(prompt, model)
            step.result = result
            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.result = f"Error: {str(e)}"
            step.status = StepStatus.FAILED
            logger.error(f"Step {step.id} failed: {e}")

        step.completed_at = datetime.now(timezone.utc).isoformat()

    def cancel_plan(self, plan_id: str) -> bool:
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        plan.status = PlanStatus.CANCELLED
        for step in plan.steps:
            if step.status in (StepStatus.PENDING, StepStatus.BLOCKED):
                step.status = StepStatus.SKIPPED
        return True

    def delete_plan(self, plan_id: str) -> bool:
        return self._plans.pop(plan_id, None) is not None

    def get_stats(self) -> dict:
        plans = list(self._plans.values())
        return {
            "total_plans": len(plans),
            "by_status": {
                status.value: sum(1 for p in plans if p.status == status)
                for status in PlanStatus
            },
            "average_steps": round(sum(len(p.steps) for p in plans) / max(len(plans), 1), 1),
        }


planning_engine = PlanningEngine()