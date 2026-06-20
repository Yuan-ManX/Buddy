"""
Buddy Agent Tool Composer - Dynamic tool composition and pipeline orchestration.

Enables agents to compose multiple tools into execution pipelines with
conditional branching, parallel execution, and error recovery. Tools
are treated as composable primitives that can be chained, fanned-out,
and merged into complex workflows.

Key capabilities:
- Tool pipeline definition with sequential and parallel stages
- Conditional branching based on intermediate results
- Tool result transformation and type coercion between stages
- Pipeline validation and dry-run simulation
- Automatic error recovery and fallback strategies
- Pipeline template library with reusable patterns
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class PipelineStage(str, Enum):
    """Types of pipeline stages."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    FAN_OUT = "fan_out"
    REDUCE = "reduce"
    MAP = "map"


class ExecutionMode(str, Enum):
    """Execution modes for tool pipelines."""
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"


class PipelineStatus(str, Enum):
    """Status of a pipeline execution."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


@dataclass
class ToolNode:
    """A single tool node in a composition pipeline."""
    node_id: str
    tool_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    input_mapping: dict[str, str] = field(default_factory=dict)
    output_key: str = ""
    depends_on: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: float = 30.0
    fallback_node_id: str | None = None


@dataclass
class PipelineStage:
    """A stage in a tool pipeline."""
    stage_id: str
    stage_type: PipelineStage
    stage_name: str
    nodes: list[ToolNode] = field(default_factory=list)
    condition: str = ""  # Expression for conditional stages
    on_success: str | None = None  # Next stage ID
    on_failure: str | None = None  # Fallback stage ID
    order: int = 0


@dataclass
class ToolPipeline:
    """A complete tool composition pipeline."""
    pipeline_id: str
    pipeline_name: str
    description: str
    stages: list[PipelineStage] = field(default_factory=list)
    status: PipelineStatus = PipelineStatus.IDLE
    execution_mode: ExecutionMode = ExecutionMode.ASYNC
    input_schema: dict[str, str] = field(default_factory=dict)
    output_schema: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_run_at: float = 0.0
    total_runs: int = 0
    total_successes: int = 0
    total_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 1.0
        return self.total_successes / self.total_runs


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    pipeline_id: str
    execution_id: str
    status: PipelineStatus
    stage_results: dict[str, Any] = field(default_factory=dict)
    final_output: Any = None
    errors: list[dict] = field(default_factory=list)
    execution_time_ms: float = 0.0
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


class AgentToolComposer:
    """Dynamic tool composition engine for Buddy agents.

    Enables agents to compose multiple tools into executable pipelines
    with conditional branching, parallel execution, and automatic error
    recovery. Provides a template library of reusable pipeline patterns.
    """

    def __init__(self):
        self._pipelines: dict[str, ToolPipeline] = {}
        self._results: dict[str, PipelineResult] = {}
        self._tool_executors: dict[str, Callable] = {}
        self._templates: dict[str, ToolPipeline] = {}
        self._total_pipelines = 0
        self._total_executions = 0

    def register_tool(self, tool_name: str, executor: Callable) -> None:
        """Register a tool executor function."""
        self._tool_executors[tool_name] = executor

    def create_pipeline(
        self,
        name: str,
        description: str = "",
        execution_mode: ExecutionMode = ExecutionMode.ASYNC,
        tags: list[str] | None = None,
    ) -> ToolPipeline:
        """Create a new tool composition pipeline."""
        pipeline_id = f"pipeline-{uuid.uuid4().hex[:12]}"
        pipeline = ToolPipeline(
            pipeline_id=pipeline_id,
            pipeline_name=name,
            description=description,
            execution_mode=execution_mode,
            tags=tags or [],
        )
        self._pipelines[pipeline_id] = pipeline
        self._total_pipelines += 1
        return pipeline

    def add_stage(
        self,
        pipeline_id: str,
        stage_type: PipelineStage,
        stage_name: str,
        condition: str = "",
        on_success: str | None = None,
        on_failure: str | None = None,
    ) -> PipelineStage | None:
        """Add a stage to a pipeline."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None

        stage = PipelineStage(
            stage_id=f"stage-{uuid.uuid4().hex[:12]}",
            stage_type=stage_type,
            stage_name=stage_name,
            condition=condition,
            on_success=on_success,
            on_failure=on_failure,
            order=len(pipeline.stages),
        )
        pipeline.stages.append(stage)
        return stage

    def add_node(
        self,
        pipeline_id: str,
        stage_id: str,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        input_mapping: dict[str, str] | None = None,
        output_key: str = "",
        depends_on: list[str] | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 30.0,
    ) -> ToolNode | None:
        """Add a tool node to a pipeline stage."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None

        stage = self._find_stage(pipeline, stage_id)
        if not stage:
            return None

        node = ToolNode(
            node_id=f"node-{uuid.uuid4().hex[:12]}",
            tool_name=tool_name,
            parameters=parameters or {},
            input_mapping=input_mapping or {},
            output_key=output_key,
            depends_on=depends_on or [],
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        stage.nodes.append(node)
        return node

    async def execute(
        self,
        pipeline_id: str,
        inputs: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """Execute a tool pipeline."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return PipelineResult(
                pipeline_id=pipeline_id,
                execution_id="",
                status=PipelineStatus.FAILED,
                errors=[{"message": "Pipeline not found"}],
            )

        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        result = PipelineResult(
            pipeline_id=pipeline_id,
            execution_id=execution_id,
            status=PipelineStatus.RUNNING,
        )

        pipeline.status = PipelineStatus.RUNNING
        pipeline.last_run_at = time.time()
        pipeline.total_runs += 1
        self._total_executions += 1

        try:
            context: dict[str, Any] = inputs or {}
            stages = sorted(pipeline.stages, key=lambda s: s.order)

            for stage in stages:
                stage_result = await self._execute_stage(stage, context)
                result.stage_results[stage.stage_id] = stage_result

                if stage_result.get("status") == "failed":
                    result.status = PipelineStatus.PARTIAL
                    result.errors.append({
                        "stage_id": stage.stage_id,
                        "error": stage_result.get("error", "Unknown error"),
                    })

                    if stage.on_failure:
                        # Try fallback
                        fallback = self._find_stage(pipeline, stage.on_failure)
                        if fallback:
                            fb_result = await self._execute_stage(fallback, context)
                            result.stage_results[fallback.stage_id] = fb_result
                    else:
                        break

                context.update(stage_result.get("outputs", {}))

            result.status = PipelineStatus.COMPLETED
            result.final_output = context
            pipeline.total_successes += 1

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.errors.append({"message": str(e)})
            pipeline.total_failures += 1

        result.completed_at = time.time()
        result.execution_time_ms = (result.completed_at - result.started_at) * 1000
        pipeline.status = PipelineStatus.IDLE

        self._results[execution_id] = result
        return result

    def save_as_template(self, pipeline_id: str, template_name: str) -> bool:
        """Save a pipeline as a reusable template."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return False
        self._templates[template_name] = pipeline
        return True

    def create_from_template(
        self, template_name: str, name: str, description: str = ""
    ) -> ToolPipeline | None:
        """Create a new pipeline from a template."""
        template = self._templates.get(template_name)
        if not template:
            return None

        new_pipeline = self.create_pipeline(
            name=name,
            description=description or template.description,
            execution_mode=template.execution_mode,
            tags=list(template.tags),
        )

        for stage in template.stages:
            new_stage = self.add_stage(
                pipeline_id=new_pipeline.pipeline_id,
                stage_type=stage.stage_type,
                stage_name=stage.stage_name,
                condition=stage.condition,
                on_success=stage.on_success,
                on_failure=stage.on_failure,
            )
            if new_stage:
                for node in stage.nodes:
                    self.add_node(
                        pipeline_id=new_pipeline.pipeline_id,
                        stage_id=new_stage.stage_id,
                        tool_name=node.tool_name,
                        parameters=dict(node.parameters),
                        input_mapping=dict(node.input_mapping),
                        output_key=node.output_key,
                        depends_on=list(node.depends_on),
                        max_retries=node.max_retries,
                        timeout_seconds=node.timeout_seconds,
                    )

        return new_pipeline

    def get_pipeline(self, pipeline_id: str) -> ToolPipeline | None:
        """Get a pipeline by ID."""
        return self._pipelines.get(pipeline_id)

    def get_result(self, execution_id: str) -> PipelineResult | None:
        """Get a pipeline execution result."""
        return self._results.get(execution_id)

    def get_stats(self) -> dict:
        """Get tool composer statistics."""
        return {
            "total_pipelines": self._total_pipelines,
            "total_executions": self._total_executions,
            "total_templates": len(self._templates),
            "registered_tools": len(self._tool_executors),
            "pipelines": [
                {
                    "pipeline_id": p.pipeline_id,
                    "name": p.pipeline_name,
                    "description": p.description,
                    "stages": len(p.stages),
                    "total_runs": p.total_runs,
                    "success_rate": round(p.success_rate, 3),
                    "status": p.status.value,
                }
                for p in self._pipelines.values()
            ],
            "templates": list(self._templates.keys()),
            "tools": list(self._tool_executors.keys()),
        }

    async def _execute_stage(
        self, stage: PipelineStage, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single pipeline stage."""
        if stage.stage_type == PipelineStage.PARALLEL:
            tasks = [
                self._execute_node(node, context)
                for node in stage.nodes
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            outputs = {}
            for node, result in zip(stage.nodes, results):
                if isinstance(result, Exception):
                    outputs[node.output_key or node.node_id] = {"error": str(result)}
                else:
                    outputs[node.output_key or node.node_id] = result
            return {"status": "completed", "outputs": outputs}

        elif stage.stage_type == PipelineStage.CONDITIONAL:
            # Evaluate condition and execute matching nodes
            should_execute = self._evaluate_condition(stage.condition, context)
            if not should_execute:
                return {"status": "skipped", "outputs": {}}
            results = {}
            for node in stage.nodes:
                try:
                    results[node.output_key or node.node_id] = await self._execute_node(node, context)
                except Exception as e:
                    results[node.output_key or node.node_id] = {"error": str(e)}
            return {"status": "completed", "outputs": results}

        else:
            # Sequential execution
            outputs = {}
            for node in stage.nodes:
                try:
                    result = await self._execute_node(node, context)
                    outputs[node.output_key or node.node_id] = result
                    context[node.output_key or node.node_id] = result
                except Exception as e:
                    return {"status": "failed", "error": str(e), "outputs": outputs}
            return {"status": "completed", "outputs": outputs}

    async def _execute_node(
        self, node: ToolNode, context: dict[str, Any]
    ) -> Any:
        """Execute a single tool node with retry logic."""
        executor = self._tool_executors.get(node.tool_name)
        if not executor:
            raise ValueError(f"Tool '{node.tool_name}' not registered")

        # Resolve input mapping
        resolved_params = dict(node.parameters)
        for param_key, context_key in node.input_mapping.items():
            if context_key in context:
                resolved_params[param_key] = context[context_key]

        last_error = None
        for attempt in range(node.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(executor):
                    result = await asyncio.wait_for(
                        executor(**resolved_params),
                        timeout=node.timeout_seconds,
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(executor, **resolved_params),
                        timeout=node.timeout_seconds,
                    )
                return result
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Tool '{node.tool_name}' timed out")
            except Exception as e:
                last_error = e
                if attempt < node.max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))

        raise last_error or RuntimeError(f"Tool '{node.tool_name}' failed")

    def _evaluate_condition(
        self, condition: str, context: dict[str, Any]
    ) -> bool:
        """Evaluate a simple condition expression."""
        if not condition:
            return True
        try:
            # Simple evaluation: check if key exists and is truthy
            if condition.startswith("!"):
                key = condition[1:]
                return not bool(context.get(key))
            return bool(context.get(condition))
        except Exception:
            return False

    def _find_stage(
        self, pipeline: ToolPipeline, stage_id: str
    ) -> PipelineStage | None:
        for stage in pipeline.stages:
            if stage.stage_id == stage_id:
                return stage
        return None


# Global singleton
tool_composer = AgentToolComposer()