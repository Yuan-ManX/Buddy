"""Buddy Agent Pipeline — Composable execution chains with parallel branching

Provides a declarative pipeline system where agent operations can be chained,
branched in parallel, and composed into complex workflows. Pipelines support
conditional execution, error recovery, state propagation, and real-time
progress tracking.

Architecture:
    PipelineEngine (singleton)
    ├── PipelineRegistry (named pipeline definitions)
    ├── PipelineRunner (execution with state management)
    ├── BranchManager (parallel execution with fan-in/fan-out)
    └── ProgressTracker (real-time step monitoring)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.pipeline")


# ══════════════════════════════════════════════════════════════
# Enums & Data Classes
# ══════════════════════════════════════════════════════════════

class StepKind(str, Enum):
    CHAT = "chat"
    TOOL = "tool"
    SKILL = "skill"
    CODE = "code"
    CONDITION = "condition"
    PARALLEL = "parallel"
    WAIT = "wait"
    SUBPIPELINE = "subpipeline"
    TRANSFORM = "transform"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class ErrorPolicy(str, Enum):
    ABORT = "abort"
    SKIP = "skip"
    RETRY = "retry"
    FALLBACK = "fallback"


@dataclass
class StepConfig:
    kind: StepKind
    name: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    error_policy: ErrorPolicy = ErrorPolicy.ABORT
    max_retries: int = 2
    timeout_seconds: float = 120.0
    condition: str = ""  # Jinja2-style expression evaluated against state
    fallback_step: str = ""  # Step to execute on failure


@dataclass
class StepResult:
    step_name: str
    status: StepStatus
    output: Any = None
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineDefinition:
    id: str
    name: str
    description: str = ""
    steps: list[StepConfig] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PipelineRun:
    id: str
    pipeline_id: str
    status: PipelineStatus = PipelineStatus.PENDING
    steps: dict[str, StepResult] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    total_duration_ms: float = 0.0
    progress: float = 0.0


# ══════════════════════════════════════════════════════════════
# Pipeline Engine
# ══════════════════════════════════════════════════════════════

class PipelineEngine:
    """Composable execution engine for agent pipeline workflows.

    Supports sequential chains, parallel branches, conditional execution,
    error recovery with retry policies, and state propagation between steps.
    """

    MAX_PARALLEL_BRANCHES = 10

    def __init__(self):
        self._pipelines: dict[str, PipelineDefinition] = {}
        self._runs: dict[str, PipelineRun] = {}
        self._executors: dict[StepKind, Callable] = {}
        self._run_history: list[PipelineRun] = []

    # ── Registration ─────────────────────────────────────

    def register_executor(self, kind: StepKind, executor: Callable):
        """Register a step executor for a given step kind."""
        self._executors[kind] = executor

    def define_pipeline(self, definition: PipelineDefinition) -> str:
        """Register a pipeline definition and return its ID."""
        self._pipelines[definition.id] = definition
        logger.info(f"Pipeline defined: {definition.name} ({len(definition.steps)} steps)")
        return definition.id

    def get_pipeline(self, pipeline_id: str) -> PipelineDefinition | None:
        return self._pipelines.get(pipeline_id)

    def list_pipelines(self) -> list[dict]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "step_count": len(p.steps),
                "steps": [
                    {"name": s.name, "kind": s.kind.value, "depends_on": s.depends_on}
                    for s in p.steps
                ],
                "created_at": p.created_at,
            }
            for p in self._pipelines.values()
        ]

    def delete_pipeline(self, pipeline_id: str) -> bool:
        if pipeline_id in self._pipelines:
            del self._pipelines[pipeline_id]
            return True
        return False

    # ── Execution ────────────────────────────────────────

    async def run(
        self,
        pipeline_id: str,
        initial_state: dict[str, Any] | None = None,
        executor_context: dict[str, Any] | None = None,
    ) -> PipelineRun:
        """Execute a pipeline with the given initial state and context."""
        definition = self._pipelines.get(pipeline_id)
        if not definition:
            raise ValueError(f"Pipeline not found: {pipeline_id}")

        run = PipelineRun(
            id=f"run-{uuid.uuid4().hex[:12]}",
            pipeline_id=pipeline_id,
            state=initial_state or {},
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        run.status = PipelineStatus.RUNNING
        self._runs[run.id] = run

        try:
            await self._execute_steps(definition, run, executor_context or {})
            # Determine final status
            failures = [r for r in run.steps.values() if r.status == StepStatus.FAILED]
            if failures:
                run.status = PipelineStatus.PARTIAL if any(
                    r.status == StepStatus.COMPLETED for r in run.steps.values()
                ) else PipelineStatus.FAILED
            else:
                run.status = PipelineStatus.COMPLETED
        except asyncio.CancelledError:
            run.status = PipelineStatus.CANCELLED
            logger.warning(f"Pipeline run {run.id} cancelled")
        except Exception as e:
            run.status = PipelineStatus.FAILED
            logger.error(f"Pipeline run {run.id} failed: {e}")

        run.completed_at = datetime.now(timezone.utc).isoformat()
        if run.started_at:
            start_dt = datetime.fromisoformat(run.started_at)
            end_dt = datetime.fromisoformat(run.completed_at)
            run.total_duration_ms = (end_dt - start_dt).total_seconds() * 1000

        self._run_history.append(run)
        if len(self._run_history) > 100:
            self._run_history = self._run_history[-50:]

        return run

    async def _execute_steps(
        self,
        definition: PipelineDefinition,
        run: PipelineRun,
        context: dict[str, Any],
    ):
        """Execute all steps respecting dependencies with parallel execution."""
        total = len(definition.steps)
        completed: set[str] = set()
        failed: set[str] = set()
        skipped: set[str] = set()

        while len(completed) + len(failed) + len(skipped) < total:
            ready = []
            for step in definition.steps:
                name = step.name
                if name in completed or name in failed or name in skipped:
                    continue
                if all(
                    dep in completed or dep in skipped
                    for dep in step.depends_on
                ):
                    ready.append(step)

            if not ready:
                # Handle deadlock: remaining steps have unmet dependencies
                remaining = [
                    s.name for s in definition.steps
                    if s.name not in completed and s.name not in failed and s.name not in skipped
                ]
                for name in remaining:
                    run.steps[name] = StepResult(
                        step_name=name,
                        status=StepStatus.FAILED,
                        error="Unmet dependencies — deadlock detected",
                    )
                    failed.add(name)
                break

            # Group parallel steps vs sequential stepss
            parallel_group = [s for s in ready if s.kind == StepKind.PARALLEL]
            sequential = [s for s in ready if s.kind != StepKind.PARALLEL]

            # Execute parallel group first
            if parallel_group:
                parallel_tasks = []
                for step in parallel_group[:self.MAX_PARALLEL_BRANCHES]:
                    parallel_tasks.append(
                        self._run_step(step, run, context)
                    )
                results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
                for step, result in zip(parallel_group, results):
                    if isinstance(result, Exception):
                        run.steps[step.name] = StepResult(
                            step_name=step.name,
                            status=StepStatus.FAILED,
                            error=str(result),
                        )
                        if step.error_policy == ErrorPolicy.ABORT:
                            failed.add(step.name)
                        else:
                            skipped.add(step.name)
                    else:
                        run.steps[step.name] = result
                        if result.status == StepStatus.COMPLETED:
                            completed.add(step.name)
                        elif result.status == StepStatus.SKIPPED:
                            skipped.add(step.name)
                        else:
                            if step.error_policy == ErrorPolicy.ABORT:
                                failed.add(step.name)
                            else:
                                skipped.add(step.name)

            # Execute sequential steps
            for step in sequential:
                result = await self._run_step(step, run, context)
                run.steps[step.name] = result
                if result.status == StepStatus.COMPLETED:
                    completed.add(step.name)
                elif result.status == StepStatus.SKIPPED:
                    skipped.add(step.name)
                else:
                    if step.error_policy == ErrorPolicy.ABORT:
                        failed.add(step.name)
                        if step.fallback_step:
                            fallback_result = await self._run_fallback(
                                step.fallback_step, definition, run, context
                            )
                            if fallback_result:
                                run.steps[step.fallback_step] = fallback_result
                                completed.add(step.fallback_step)
                    else:
                        skipped.add(step.name)

            # Update progress
            run.progress = (len(completed) + len(failed) + len(skipped)) / total

    async def _run_step(
        self,
        step: StepConfig,
        run: PipelineRun,
        context: dict[str, Any],
    ) -> StepResult:
        """Execute a single pipeline step with retry logic."""
        start = datetime.now(timezone.utc)

        # Evaluate condition
        if step.condition and not self._evaluate_condition(step.condition, run.state):
            return StepResult(
                step_name=step.name,
                status=StepStatus.SKIPPED,
                started_at=start.isoformat(),
            )

        executor = self._executors.get(step.kind)
        if not executor:
            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                error=f"No executor registered for step kind: {step.kind.value}",
                started_at=start.isoformat(),
            )

        last_error = ""
        for attempt in range(step.max_retries + 1):
            try:
                result_data = await asyncio.wait_for(
                    executor(step.config, run.state, context),
                    timeout=step.timeout_seconds,
                )
                # Propagate result to state under step name
                if isinstance(result_data, dict):
                    run.state[step.name] = result_data
                else:
                    run.state[step.name] = {"result": result_data}

                end = datetime.now(timezone.utc)
                return StepResult(
                    step_name=step.name,
                    status=StepStatus.COMPLETED,
                    output=result_data,
                    started_at=start.isoformat(),
                    completed_at=end.isoformat(),
                    duration_ms=(end - start).total_seconds() * 1000,
                    retries=attempt,
                )
            except asyncio.TimeoutError:
                last_error = f"Step timed out after {step.timeout_seconds}s"
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Step '{step.name}' attempt {attempt + 1} failed: {e}")

        end = datetime.now(timezone.utc)
        return StepResult(
            step_name=step.name,
            status=StepStatus.FAILED,
            error=last_error,
            started_at=start.isoformat(),
            completed_at=end.isoformat(),
            duration_ms=(end - start).total_seconds() * 1000,
            retries=step.max_retries,
        )

    async def _run_fallback(
        self,
        fallback_name: str,
        definition: PipelineDefinition,
        run: PipelineRun,
        context: dict[str, Any],
    ) -> StepResult | None:
        """Execute a fallback step."""
        for step in definition.steps:
            if step.name == fallback_name:
                return await self._run_step(step, run, context)
        return None

    def _evaluate_condition(self, condition: str, state: dict[str, Any]) -> bool:
        """Evaluate a condition expression against pipeline state."""
        try:
            safe_builtins = {
                "True": True, "False": False, "None": None,
                "len": len, "str": str, "int": int, "float": float,
                "bool": bool, "any": any, "all": all,
            }
            return bool(eval(condition, {"__builtins__": safe_builtins}, state))
        except Exception as e:
            logger.warning(f"Condition evaluation failed: '{condition}' -> {e}")
            return True  # Default to executing on evaluation error

    # ── Builders ─────────────────────────────────────────

    def build_chat_pipeline(
        self,
        name: str,
        agent_id: str,
        messages: list[dict],
        description: str = "",
    ) -> str:
        """Build a simple sequential chat pipeline."""
        steps = []
        for i, msg in enumerate(messages):
            steps.append(StepConfig(
                kind=StepKind.CHAT,
                name=f"chat_{i}",
                config={"agent_id": agent_id, "message": msg.get("content", ""), "role": msg.get("role", "user")},
                depends_on=[f"chat_{i-1}"] if i > 0 else [],
            ))
        definition = PipelineDefinition(
            id=f"pipeline-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            steps=steps,
        )
        return self.define_pipeline(definition)

    def build_parallel_analysis(
        self,
        name: str,
        agent_ids: list[str],
        query: str,
        description: str = "",
    ) -> str:
        """Build a parallel analysis pipeline with multiple agents."""
        step_configs = []
        for agent_id in agent_ids:
            step_configs.append(StepConfig(
                kind=StepKind.CHAT,
                name=f"analyze_{agent_id}",
                config={"agent_id": agent_id, "message": query},
            ))

        synthesize_step = StepConfig(
            kind=StepKind.CHAT,
            name="synthesize",
            config={"agent_id": agent_ids[0], "message": "Synthesize the parallel analysis results."},
            depends_on=[f"analyze_{aid}" for aid in agent_ids],
        )

        definition = PipelineDefinition(
            id=f"pipeline-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            steps=step_configs + [synthesize_step],
        )
        return self.define_pipeline(definition)

    # ── Run Management ───────────────────────────────────

    def get_run(self, run_id: str) -> PipelineRun | None:
        return self._runs.get(run_id)

    def cancel_run(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run and run.status == PipelineStatus.RUNNING:
            run.status = PipelineStatus.CANCELLED
            return True
        return False

    def list_runs(self, pipeline_id: str | None = None, limit: int = 20) -> list[dict]:
        runs = self._run_history
        if pipeline_id:
            runs = [r for r in runs if r.pipeline_id == pipeline_id]
        runs = runs[-limit:]
        return [
            {
                "id": r.id,
                "pipeline_id": r.pipeline_id,
                "status": r.status.value,
                "progress": r.progress,
                "step_count": len(r.steps),
                "completed_count": sum(1 for s in r.steps.values() if s.status == StepStatus.COMPLETED),
                "failed_count": sum(1 for s in r.steps.values() if s.status == StepStatus.FAILED),
                "total_duration_ms": r.total_duration_ms,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
            for r in reversed(runs)
        ]

    def get_stats(self) -> dict:
        total = len(self._run_history)
        successful = sum(1 for r in self._run_history if r.status == PipelineStatus.COMPLETED)
        failed = sum(1 for r in self._run_history if r.status in (PipelineStatus.FAILED, PipelineStatus.PARTIAL))
        return {
            "total_pipelines": len(self._pipelines),
            "total_runs": total,
            "successful_runs": successful,
            "failed_runs": failed,
            "success_rate": f"{(successful / max(total, 1) * 100):.1f}%",
            "active_runs": sum(1 for r in self._runs.values() if r.status == PipelineStatus.RUNNING),
        }


# ── Singleton ────────────────────────────────────────────

pipeline_engine = PipelineEngine()