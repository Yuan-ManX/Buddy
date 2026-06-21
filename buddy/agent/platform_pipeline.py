"""
Buddy Platform Pipeline Engine.

Provides a comprehensive pipeline system for training, fine-tuning,
deploying, and managing AI models and agent configurations. Supports
multi-stage pipelines with checkpoints, rollbacks, and progress tracking.
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


class PipelineStatus(Enum):
    """Status of a pipeline execution."""
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"


class StageStatus(Enum):
    """Status of a pipeline stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PipelineType(Enum):
    """Types of pipelines."""
    TRAINING = "training"
    FINE_TUNING = "fine_tuning"
    DEPLOYMENT = "deployment"
    EVALUATION = "evaluation"
    DATA_PROCESSING = "data_processing"
    PROFILE_SYNC = "profile_sync"
    KNOWLEDGE_INGESTION = "knowledge_ingestion"
    CUSTOM = "custom"


@dataclass
class PipelineStage:
    """A single stage within a pipeline."""
    stage_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    status: StageStatus = StageStatus.PENDING
    handler: Optional[str] = None
    config: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    timeout_seconds: float = 300.0
    retry_count: int = 0
    max_retries: int = 1
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    output: Any = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class Pipeline:
    """A complete pipeline definition."""
    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    pipeline_type: PipelineType = PipelineType.CUSTOM
    status: PipelineStatus = PipelineStatus.DRAFT
    stages: list[PipelineStage] = field(default_factory=list)
    current_stage_index: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    version: int = 1
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    checkpoint_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineCheckpoint:
    """A checkpoint for pipeline rollback."""
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    pipeline_id: str = ""
    stage_index: int = 0
    stage_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class PipelineEngine:
    """
    Pipeline execution engine for the Buddy platform.

    Manages multi-stage pipelines for training, deployment, evaluation,
    and data processing with checkpointing, rollback, and progress tracking.
    """

    MAX_CONCURRENT_PIPELINES = 3

    def __init__(self):
        self._pipelines: dict[str, Pipeline] = {}
        self._checkpoints: dict[str, list[PipelineCheckpoint]] = {}
        self._stage_handlers: dict[str, Callable] = {}
        self._execution_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_PIPELINES)

    # ── Pipeline Management ────────────────────────────────────────

    def create_pipeline(
        self,
        name: str,
        pipeline_type: PipelineType = PipelineType.CUSTOM,
        description: str = "",
        stages: Optional[list[PipelineStage]] = None,
        tags: Optional[list[str]] = None,
        **metadata,
    ) -> Pipeline:
        """Create a new pipeline."""
        pipeline = Pipeline(
            name=name,
            description=description,
            pipeline_type=pipeline_type,
            stages=stages or [],
            tags=tags or [],
            metadata=metadata,
        )
        self._pipelines[pipeline.pipeline_id] = pipeline
        logger.info("Pipeline created: %s (type=%s)", name, pipeline_type.value)
        return pipeline

    def add_stage(
        self,
        pipeline: Pipeline,
        name: str,
        handler: Optional[str] = None,
        description: str = "",
        config: Optional[dict[str, Any]] = None,
        dependencies: Optional[list[str]] = None,
        timeout_seconds: float = 300.0,
        max_retries: int = 1,
    ) -> PipelineStage:
        """Add a stage to a pipeline."""
        stage = PipelineStage(
            name=name,
            description=description,
            handler=handler,
            config=config or {},
            dependencies=dependencies or [],
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        pipeline.stages.append(stage)
        return stage

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get a pipeline by ID."""
        return self._pipelines.get(pipeline_id)

    def list_pipelines(
        self,
        pipeline_type: Optional[PipelineType] = None,
        status: Optional[PipelineStatus] = None,
    ) -> list[Pipeline]:
        """List pipelines with optional filtering."""
        pipelines = list(self._pipelines.values())
        if pipeline_type:
            pipelines = [p for p in pipelines if p.pipeline_type == pipeline_type]
        if status:
            pipelines = [p for p in pipelines if p.status == status]
        return pipelines

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline."""
        if pipeline_id in self._pipelines:
            del self._pipelines[pipeline_id]
            self._checkpoints.pop(pipeline_id, None)
            return True
        return False

    # ── Stage Handler Registration ─────────────────────────────────

    def register_handler(self, handler_name: str, handler: Callable) -> None:
        """Register a stage handler function."""
        self._stage_handlers[handler_name] = handler
        logger.info("Stage handler registered: %s", handler_name)

    # ── Pipeline Execution ─────────────────────────────────────────

    async def execute_pipeline(self, pipeline_id: str) -> dict[str, Any]:
        """Execute a pipeline to completion."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not found"}

        async with self._execution_semaphore:
            start_time = time.time()
            pipeline.status = PipelineStatus.RUNNING
            pipeline.started_at = time.time()

            results = []

            try:
                for i, stage in enumerate(pipeline.stages):
                    pipeline.current_stage_index = i

                    # Check dependencies
                    if not self._dependencies_met(pipeline, stage):
                        stage.status = StageStatus.SKIPPED
                        logger.info("Stage %s skipped: dependencies not met", stage.name)
                        continue

                    # Execute stage
                    stage_result = await self._execute_stage(pipeline, stage)
                    results.append(stage_result)

                    if stage.status == StageStatus.FAILED:
                        await self._handle_failure(pipeline, stage)
                        break

                    # Create checkpoint
                    await self._create_checkpoint(pipeline, stage)

                # Determine final status
                all_completed = all(
                    s.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
                    for s in pipeline.stages
                )
                if all_completed:
                    pipeline.status = PipelineStatus.COMPLETED
                    pipeline.completed_at = time.time()

            except Exception as e:
                pipeline.status = PipelineStatus.FAILED
                logger.error("Pipeline %s failed: %s", pipeline.pipeline_id, e)

            return {
                "pipeline_id": pipeline.pipeline_id,
                "name": pipeline.name,
                "status": pipeline.status.value,
                "total_stages": len(pipeline.stages),
                "completed_stages": sum(
                    1 for s in pipeline.stages
                    if s.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
                ),
                "failed_stages": sum(1 for s in pipeline.stages if s.status == StageStatus.FAILED),
                "duration_s": round(time.time() - start_time, 2),
                "stage_results": results,
            }

    async def execute_all_queued(self) -> list[dict[str, Any]]:
        """Execute all queued pipelines."""
        queued = self.list_pipelines(status=PipelineStatus.QUEUED)
        tasks = [self.execute_pipeline(p.pipeline_id) for p in queued]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def pause_pipeline(self, pipeline_id: str) -> bool:
        """Pause a running pipeline."""
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline and pipeline.status == PipelineStatus.RUNNING:
            pipeline.status = PipelineStatus.PAUSED
            return True
        return False

    def resume_pipeline(self, pipeline_id: str) -> bool:
        """Resume a paused pipeline."""
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline and pipeline.status == PipelineStatus.PAUSED:
            pipeline.status = PipelineStatus.RUNNING
            return True
        return False

    def cancel_pipeline(self, pipeline_id: str) -> bool:
        """Cancel a pipeline."""
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline and pipeline.status in (PipelineStatus.RUNNING, PipelineStatus.PAUSED, PipelineStatus.QUEUED):
            pipeline.status = PipelineStatus.CANCELLED
            return True
        return False

    # ── Rollback ───────────────────────────────────────────────────

    async def rollback_pipeline(self, pipeline_id: str, to_stage_index: int = 0) -> dict[str, Any]:
        """Rollback a pipeline to a specific stage checkpoint."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not found"}

        checkpoints = self._checkpoints.get(pipeline_id, [])
        target_checkpoint = None

        for cp in reversed(checkpoints):
            if cp.stage_index <= to_stage_index:
                target_checkpoint = cp
                break

        if not target_checkpoint:
            return {"error": f"No checkpoint found for stage {to_stage_index}"}

        pipeline.status = PipelineStatus.ROLLING_BACK
        pipeline.checkpoint_data = target_checkpoint.data

        # Reset stages after checkpoint
        for i in range(target_checkpoint.stage_index + 1, len(pipeline.stages)):
            pipeline.stages[i].status = StageStatus.PENDING
            pipeline.stages[i].output = None

        pipeline.status = PipelineStatus.PAUSED
        pipeline.current_stage_index = target_checkpoint.stage_index

        return {
            "pipeline_id": pipeline_id,
            "rolled_back_to": target_checkpoint.stage_index,
            "stage_id": target_checkpoint.stage_id,
            "status": "paused",
        }

    # ── Internal Methods ───────────────────────────────────────────

    async def _execute_stage(self, pipeline: Pipeline, stage: PipelineStage) -> dict[str, Any]:
        """Execute a single pipeline stage."""
        stage.status = StageStatus.RUNNING
        stage.started_at = time.time()

        try:
            if stage.handler and stage.handler in self._stage_handlers:
                handler = self._stage_handlers[stage.handler]
                if asyncio.iscoroutinefunction(handler):
                    result = await asyncio.wait_for(
                        handler(pipeline, stage),
                        timeout=stage.timeout_seconds,
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(handler, pipeline, stage),
                        timeout=stage.timeout_seconds,
                    )
                stage.output = result
            else:
                # Simulate stage execution
                await asyncio.sleep(0.1)
                stage.output = {"status": "completed", "stage": stage.name}

            stage.status = StageStatus.COMPLETED
            stage.completed_at = time.time()

        except asyncio.TimeoutError:
            stage.status = StageStatus.FAILED
            stage.error = f"Stage timed out after {stage.timeout_seconds}s"
        except Exception as e:
            stage.status = StageStatus.FAILED
            stage.error = str(e)

        finally:
            if stage.completed_at is None:
                stage.completed_at = time.time()

        return {
            "stage_id": stage.stage_id,
            "name": stage.name,
            "status": stage.status.value,
            "error": stage.error,
            "duration_s": round((stage.completed_at - (stage.started_at or stage.completed_at)), 2),
        }

    async def _create_checkpoint(self, pipeline: Pipeline, stage: PipelineStage) -> None:
        """Create a checkpoint after a stage completes."""
        checkpoint = PipelineCheckpoint(
            pipeline_id=pipeline.pipeline_id,
            stage_index=pipeline.stages.index(stage),
            stage_id=stage.stage_id,
            data={
                "pipeline_status": pipeline.status.value,
                "stage_outputs": {
                    s.stage_id: s.output
                    for s in pipeline.stages
                    if s.status == StageStatus.COMPLETED
                },
                "checkpoint_data": dict(pipeline.checkpoint_data),
            },
        )
        if pipeline.pipeline_id not in self._checkpoints:
            self._checkpoints[pipeline.pipeline_id] = []
        self._checkpoints[pipeline.pipeline_id].append(checkpoint)

    async def _handle_failure(self, pipeline: Pipeline, stage: PipelineStage) -> None:
        """Handle a stage failure."""
        if stage.retry_count < stage.max_retries:
            stage.retry_count += 1
            stage.status = StageStatus.PENDING
            stage.error = None
            logger.info("Retrying stage %s (attempt %d)", stage.name, stage.retry_count)
        else:
            pipeline.status = PipelineStatus.FAILED
            logger.error("Pipeline %s failed at stage %s", pipeline.pipeline_id, stage.name)

    def _dependencies_met(self, pipeline: Pipeline, stage: PipelineStage) -> bool:
        """Check if all dependencies for a stage are met."""
        if not stage.dependencies:
            return True
        for dep_name in stage.dependencies:
            dep_stage = next(
                (s for s in pipeline.stages if s.name == dep_name or s.stage_id == dep_name),
                None,
            )
            if not dep_stage or dep_stage.status != StageStatus.COMPLETED:
                return False
        return True

    # ── Pipeline Templates ─────────────────────────────────────────

    def create_training_pipeline(
        self,
        name: str,
        data_source: str = "",
        model_name: str = "",
    ) -> Pipeline:
        """Create a standard training pipeline template."""
        pipeline = self.create_pipeline(
            name=name,
            pipeline_type=PipelineType.TRAINING,
            description=f"Training pipeline for {model_name or 'model'}",
        )
        self.add_stage(pipeline, "data_preparation", "prepare_data",
                       config={"source": data_source})
        self.add_stage(pipeline, "data_validation", "validate_data",
                       dependencies=["data_preparation"])
        self.add_stage(pipeline, "training", "train_model",
                       dependencies=["data_validation"],
                       config={"model": model_name})
        self.add_stage(pipeline, "evaluation", "evaluate_model",
                       dependencies=["training"])
        self.add_stage(pipeline, "export", "export_model",
                       dependencies=["evaluation"])
        return pipeline

    def create_deployment_pipeline(
        self,
        name: str,
        model_name: str = "",
        target: str = "production",
    ) -> Pipeline:
        """Create a standard deployment pipeline template."""
        pipeline = self.create_pipeline(
            name=name,
            pipeline_type=PipelineType.DEPLOYMENT,
            description=f"Deployment pipeline for {model_name or 'model'}",
        )
        self.add_stage(pipeline, "validation", "validate_deployment",
                       config={"model": model_name})
        self.add_stage(pipeline, "staging", "deploy_staging",
                       dependencies=["validation"])
        self.add_stage(pipeline, "integration_tests", "run_integration_tests",
                       dependencies=["staging"])
        self.add_stage(pipeline, "production", "deploy_production",
                       dependencies=["integration_tests"],
                       config={"target": target})
        self.add_stage(pipeline, "health_check", "health_check",
                       dependencies=["production"])
        return pipeline

    def create_knowledge_ingestion_pipeline(
        self,
        name: str,
        source: str = "",
    ) -> Pipeline:
        """Create a knowledge ingestion pipeline template."""
        pipeline = self.create_pipeline(
            name=name,
            pipeline_type=PipelineType.KNOWLEDGE_INGESTION,
            description="Knowledge ingestion pipeline",
        )
        self.add_stage(pipeline, "extract", "extract_knowledge",
                       config={"source": source})
        self.add_stage(pipeline, "transform", "transform_knowledge",
                       dependencies=["extract"])
        self.add_stage(pipeline, "embed", "embed_knowledge",
                       dependencies=["transform"])
        self.add_stage(pipeline, "index", "index_knowledge",
                       dependencies=["embed"])
        self.add_stage(pipeline, "verify", "verify_knowledge",
                       dependencies=["index"])
        return pipeline

    # ── Statistics ─────────────────────────────────────────────────

    def list_runs(self, pipeline_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """List pipeline runs, optionally filtered by pipeline_id."""
        runs = []
        for p in self._pipelines.values():
            if pipeline_id and p.pipeline_id != pipeline_id:
                continue
            runs.append({
                "pipeline_id": p.pipeline_id,
                "name": p.name,
                "pipeline_type": p.pipeline_type.value,
                "status": p.status.value,
                "current_stage": p.current_stage_index,
                "total_stages": len(p.stages),
                "started_at": p.started_at,
                "completed_at": p.completed_at,
                "version": p.version,
            })
        runs.sort(key=lambda r: r.get("started_at") or 0, reverse=True)
        return runs[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get pipeline engine statistics."""
        return {
            "total_pipelines": len(self._pipelines),
            "active_pipelines": len(
                self.list_pipelines(status=PipelineStatus.RUNNING)
            ),
            "queued_pipelines": len(
                self.list_pipelines(status=PipelineStatus.QUEUED)
            ),
            "completed_pipelines": len(
                self.list_pipelines(status=PipelineStatus.COMPLETED)
            ),
            "failed_pipelines": len(
                self.list_pipelines(status=PipelineStatus.FAILED)
            ),
            "pipelines_by_type": {
                t.value: len(self.list_pipelines(pipeline_type=t))
                for t in PipelineType
            },
            "total_stage_handlers": len(self._stage_handlers),
        }

    def get_pipeline_progress(self, pipeline_id: str) -> dict[str, Any]:
        """Get detailed progress for a pipeline."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not found"}

        return {
            "pipeline_id": pipeline.pipeline_id,
            "name": pipeline.name,
            "status": pipeline.status.value,
            "progress": round(
                pipeline.current_stage_index / max(len(pipeline.stages), 1) * 100, 1
            ),
            "current_stage": pipeline.current_stage_index,
            "total_stages": len(pipeline.stages),
            "stages": [
                {
                    "stage_id": s.stage_id,
                    "name": s.name,
                    "status": s.status.value,
                    "error": s.error,
                }
                for s in pipeline.stages
            ],
        }


# Global pipeline engine instance
pipeline_engine = PipelineEngine()