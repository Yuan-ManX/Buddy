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


@dataclass
class PlanTemplate:
    """Predefined plan template for common task types."""
    name: str
    category: str
    description: str = ""
    default_steps: list[dict] = field(default_factory=list)

    @classmethod
    def for_research(cls) -> "PlanTemplate":
        return cls(
            name="Research Task",
            category="research",
            description="Investigate a topic and produce a comprehensive report",
            default_steps=[
                {"title": "Define research scope", "description": "Clarify the research question and boundaries", "depends_on": []},
                {"title": "Gather sources", "description": "Collect relevant information from multiple sources", "depends_on": [0]},
                {"title": "Analyze findings", "description": "Synthesize and cross-reference information", "depends_on": [1]},
                {"title": "Draft report", "description": "Write structured findings with citations", "depends_on": [2]},
                {"title": "Review and refine", "description": "Verify accuracy and improve clarity", "depends_on": [3]},
            ],
        )

    @classmethod
    def for_code_review(cls) -> "PlanTemplate":
        return cls(
            name="Code Review",
            category="code-review",
            description="Systematic code review with quality assessment",
            default_steps=[
                {"title": "Understand codebase context", "description": "Review project structure and dependencies", "depends_on": []},
                {"title": "Read changed files", "description": "Examine all modified and new files", "depends_on": [0]},
                {"title": "Check correctness", "description": "Verify logic, edge cases, and error handling", "depends_on": [1]},
                {"title": "Assess code quality", "description": "Evaluate style, readability, and maintainability", "depends_on": [1]},
                {"title": "Security review", "description": "Check for vulnerabilities and insecure patterns", "depends_on": [1]},
                {"title": "Generate review report", "description": "Compile findings with actionable feedback", "depends_on": [2, 3, 4]},
            ],
        )

    @classmethod
    def for_data_analysis(cls) -> "PlanTemplate":
        return cls(
            name="Data Analysis",
            category="data-analysis",
            description="Analyze data and produce insights",
            default_steps=[
                {"title": "Load and inspect data", "description": "Import data and check structure", "depends_on": []},
                {"title": "Clean data", "description": "Handle missing values and outliers", "depends_on": [0]},
                {"title": "Explore distributions", "description": "Compute summary statistics and visualizations", "depends_on": [1]},
                {"title": "Identify patterns", "description": "Find correlations, trends, and anomalies", "depends_on": [2]},
                {"title": "Draw conclusions", "description": "Interpret findings and formulate recommendations", "depends_on": [3]},
            ],
        )

    @classmethod
    def for_content_creation(cls) -> "PlanTemplate":
        return cls(
            name="Content Creation",
            category="content-creation",
            description="Create structured content from requirements",
            default_steps=[
                {"title": "Analyze requirements", "description": "Understand target audience and goals", "depends_on": []},
                {"title": "Research topic", "description": "Gather background information and references", "depends_on": [0]},
                {"title": "Create outline", "description": "Structure the content with sections", "depends_on": [1]},
                {"title": "Draft content", "description": "Write the full content following the outline", "depends_on": [2]},
                {"title": "Edit and polish", "description": "Refine language, check grammar, improve flow", "depends_on": [3]},
                {"title": "Final review", "description": "Verify against requirements and publish", "depends_on": [4]},
            ],
        )

    @classmethod
    def get_all_templates(cls) -> dict[str, "PlanTemplate"]:
        return {
            "research": cls.for_research(),
            "code-review": cls.for_code_review(),
            "data-analysis": cls.for_data_analysis(),
            "content-creation": cls.for_content_creation(),
        }

    def to_plan_steps(self, plan_id: str) -> list[PlanStep]:
        """Convert template steps into PlanStep instances."""
        return [
            PlanStep(
                id=f"step-{plan_id}-{i}",
                title=s["title"],
                description=s.get("description", ""),
                depends_on=[f"step-{plan_id}-{dep}" for dep in s.get("depends_on", [])],
            )
            for i, s in enumerate(self.default_steps)
        ]


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
        self.plan_dependency_graph: dict[str, set[str]] = {}

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
        """Execute a single plan step, passing dependency results."""
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now(timezone.utc).isoformat()

        # Collect results from dependency steps
        dep_results = []
        for dep_id in step.depends_on:
            for plan in self._plans.values():
                for s in plan.steps:
                    if s.id == dep_id and s.result:
                        dep_results.append({"step": s.title, "result": s.result[:500]})

        # Build context from dependency results
        dep_context = ""
        if dep_results:
            dep_context = "\n\nPrevious step results:\n" + "\n".join(
                f"- {d['step']}: {d['result']}" for d in dep_results
            )

        try:
            prompt = (
                f"Goal: {goal}\n\n"
                f"Current step: {step.title}\n"
                f"Description: {step.description}"
                f"{dep_context}\n\n"
                f"Execute this step using the context from previous steps. Provide the result concisely."
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
        result = self._plans.pop(plan_id, None) is not None
        if result and plan_id in self.plan_dependency_graph:
            del self.plan_dependency_graph[plan_id]
        return result

    # ── Advanced Planning Methods ───────────────────────────

    async def plan_critique(
        self,
        plan: ExecutionPlan,
        model: str = "gpt-4o-mini",
    ) -> dict:
        """Have the LLM review a plan for completeness before execution.

        Returns a dict with 'score', 'issues', and 'suggestions'.
        """
        plan_text = json.dumps(plan.to_dict(), indent=2)
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": (
                        "You are a plan reviewer. Evaluate the given execution plan for completeness, "
                        "feasibility, and logical ordering. Identify gaps, missing steps, unclear descriptions, "
                        "and dependency issues. Return JSON with: "
                        "{'score': 0.0-1.0, 'issues': ['issue1', ...], 'suggestions': ['suggestion1', ...]}"
                    )},
                    {"role": "user", "content": f"Review this plan:\n\n{plan_text}"},
                ],
                response_format={"type": "json_object"},
                max_tokens=1000,
                temperature=0.3,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Plan critique failed: {e}")
            return {
                "score": 0.5,
                "issues": [f"Critique generation failed: {str(e)}"],
                "suggestions": ["Review the plan manually."],
            }

    def plan_quality_score(self, plan: ExecutionPlan) -> float:
        """Assign a quality score (0-1) to a plan based on completeness, specificity, and feasibility.

        Scoring dimensions:
        - Completeness: Are all necessary phases covered? (0-0.4)
        - Specificity: Are steps clearly described? (0-0.3)
        - Feasibility: Are dependencies well-formed? (0-0.2)
        - Structure: Is step count reasonable? (0-0.1)
        """
        if not plan.steps:
            return 0.0

        score = 0.0

        # Completeness: check for essential phases
        titles_lower = " ".join(s.title.lower() for s in plan.steps)
        essentials = [
            ("analyze" in titles_lower or "understand" in titles_lower or "assess" in titles_lower, 0.15),
            ("execute" in titles_lower or "implement" in titles_lower or "build" in titles_lower or "perform" in titles_lower or "do" in titles_lower, 0.1),
            ("verify" in titles_lower or "test" in titles_lower or "check" in titles_lower or "review" in titles_lower or "validate" in titles_lower, 0.1),
            ("report" in titles_lower or "summarize" in titles_lower or "finalize" in titles_lower or "deliver" in titles_lower, 0.05),
        ]
        for condition, weight in essentials:
            if condition:
                score += weight

        # Specificity: descriptions should be non-trivial
        described = sum(1 for s in plan.steps if len(s.description) > 20)
        score += min(0.3, (described / max(len(plan.steps), 1)) * 0.3)

        # Feasibility: dependencies should reference valid step IDs
        valid_ids = {s.id for s in plan.steps}
        valid_deps = 0
        total_deps = 0
        for s in plan.steps:
            for dep in s.depends_on:
                total_deps += 1
                if dep in valid_ids:
                    valid_deps += 1
        if total_deps > 0:
            score += (valid_deps / total_deps) * 0.2
        else:
            score += 0.1  # No dependencies is acceptable for simple plans

        # Structure: step count
        n = len(plan.steps)
        if 3 <= n <= 8:
            score += 0.1
        elif n < 3:
            score += 0.05
        else:
            score += max(0, 0.1 - (n - 8) * 0.02)

        return round(min(1.0, score), 3)

    def parallelize_steps(self, plan: ExecutionPlan) -> list[list[PlanStep]]:
        """Identify independent plan steps that can run concurrently.

        Returns a list of batches where each batch contains steps that
        can execute in parallel (no inter-dependencies within a batch).
        """
        # Build dependency graph
        step_map = {s.id: s for s in plan.steps}
        in_degree: dict[str, int] = {s.id: 0 for s in plan.steps}
        dependents: dict[str, list[str]] = {s.id: [] for s in plan.steps}

        for step in plan.steps:
            for dep_id in step.depends_on:
                if dep_id in in_degree:
                    in_degree[step.id] += 1
                    dependents.setdefault(dep_id, []).append(step.id)

        # Topological sort into batches
        batches = []
        ready = [sid for sid, deg in in_degree.items() if deg == 0]

        while ready:
            batch = [step_map[sid] for sid in sorted(ready)]
            batches.append(batch)

            next_ready = []
            for sid in ready:
                for dependent_id in dependents.get(sid, []):
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        next_ready.append(dependent_id)
            ready = next_ready

        # Update the dependency graph cache
        self.plan_dependency_graph[plan.id] = {
            sid: set(deps) for sid, deps in dependents.items()
        }

        return batches

    async def adaptive_replan(
        self,
        plan: ExecutionPlan,
        model: str = "gpt-4o-mini",
    ) -> ExecutionPlan | None:
        """During execution, detect when a plan is going off-track and re-plan mid-execution.

        Analyzes step statuses, identifies stuck or failed steps, and generates
        a revised set of remaining steps to salvage the plan. Returns a new
        ExecutionPlan if replanning was needed, or None if the plan is on track.
        """
        # Determine if replanning is needed
        completed = sum(1 for s in plan.steps if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED))
        failed = sum(1 for s in plan.steps if s.status == StepStatus.FAILED)
        total = len(plan.steps)

        # Only replan if there are failures or progress is stuck
        if failed == 0 and completed < total:
            # Check for blocked steps
            blocked = sum(1 for s in plan.steps if s.status == StepStatus.BLOCKED)
            if blocked == 0:
                return None  # Plan is progressing normally

        # Build context about what's been done and what failed
        completed_context = "\n".join(
            f"- [COMPLETED] {s.title}: {s.result[:200]}"
            for s in plan.steps
            if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        )
        failed_context = "\n".join(
            f"- [FAILED] {s.title}: {s.result[:200]}"
            for s in plan.steps if s.status == StepStatus.FAILED
        )
        pending_context = "\n".join(
            f"- [PENDING] {s.title}"
            for s in plan.steps
            if s.status == StepStatus.PENDING
        )

        try:
            replan_response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": (
                        "You are a replanning system. Given a partially executed plan with some failures, "
                        "create a revised set of remaining steps to complete the original goal. Consider "
                        "what has already been done and what failed. Return JSON: "
                        "{'should_replan': true/false, 'reason': '...', "
                        "'revised_steps': [{'title': '...', 'description': '...', 'depends_on': []}]}"
                    )},
                    {"role": "user", "content": (
                        f"Original goal: {plan.goal}\n\n"
                        f"Completed steps:\n{completed_context or 'None'}\n\n"
                        f"Failed steps:\n{failed_context or 'None'}\n\n"
                        f"Pending steps:\n{pending_context or 'None'}\n\n"
                        "Should we replan? If so, what are the revised remaining steps?"
                    )},
                ],
                response_format={"type": "json_object"},
                max_tokens=1000,
                temperature=0.4,
            )
            content = response.choices[0].message.content or "{}"
            replan_data = json.loads(content)

            if not replan_data.get("should_replan", False):
                return None

            # Create revised plan with new steps
            revised_plan = ExecutionPlan(
                id=f"{plan.id}-r{len([k for k in self._plans if k.startswith(plan.id)])}",
                title=f"{plan.title} (Revised)",
                goal=plan.goal,
                created_by=plan.created_by,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            revised_steps = replan_data.get("revised_steps", [])
            for i, step_data in enumerate(revised_steps):
                revised_plan.steps.append(PlanStep(
                    id=f"step-{revised_plan.id}-{i}",
                    title=step_data.get("title", f"Step {i+1}"),
                    description=step_data.get("description", ""),
                ))

            self._plans[revised_plan.id] = revised_plan
            logger.info(f"Adaptive replan: {plan.id} -> {revised_plan.id} ({len(revised_steps)} new steps)")
            return revised_plan

        except Exception as e:
            logger.warning(f"Adaptive replan failed: {e}")
            return None

    def _rebuild_dependency_graph(self, plan_id: str):
        """Rebuild the internal dependency graph for a plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return
        dependents: dict[str, set[str]] = {}
        for step in plan.steps:
            dependents[step.id] = set()
            for dep_id in step.depends_on:
                dependents.setdefault(dep_id, set()).add(step.id)
        self.plan_dependency_graph[plan_id] = dependents

    def get_dependency_graph(self, plan_id: str) -> dict[str, list[str]]:
        """Get the dependency graph for a plan as {step_id: [dependent_step_ids]}."""
        graph = self.plan_dependency_graph.get(plan_id)
        if not graph:
            self._rebuild_dependency_graph(plan_id)
            graph = self.plan_dependency_graph.get(plan_id, {})
        return {k: list(v) for k, v in graph.items()}

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