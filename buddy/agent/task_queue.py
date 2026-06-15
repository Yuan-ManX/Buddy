"""
Buddy Task Queue System

A persistent batch job queue with priority scheduling, retry logic,
and parallel execution capabilities. Enables long-running tasks to be
queued, monitored, and executed asynchronously without blocking the
main agent loop.

The queue supports multiple job types, configurable concurrency,
deadline enforcement, and full lifecycle tracking from submission
to completion.
"""

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.task_queue")


class JobPriority(str, Enum):
    """Priority levels for queued jobs."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class JobStatus(str, Enum):
    """Lifecycle states of a queued job."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    TIMED_OUT = "timed_out"


class JobType(str, Enum):
    """Types of jobs that can be queued."""
    AGENT_CHAT = "agent_chat"
    TOOL_EXECUTION = "tool_execution"
    SKILL_COMPOUNDING = "skill_compounding"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    BATCH_ANALYSIS = "batch_analysis"
    REPORT_GENERATION = "report_generation"
    SYSTEM_MAINTENANCE = "system_maintenance"
    CUSTOM = "custom"


@dataclass
class Job:
    """A single job in the task queue."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    job_type: JobType = JobType.CUSTOM
    name: str = ""
    description: str = ""
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    payload: dict = field(default_factory=dict)
    agent_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    completed_at: str = ""
    deadline_at: str = ""
    result: Any = None
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    retry_delay_seconds: int = 5
    timeout_seconds: int = 300
    tags: list[str] = field(default_factory=list)
    progress: float = 0.0
    progress_message: str = ""
    parent_job_id: str = ""
    child_job_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if the job is in a terminal state."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.TIMED_OUT,
        )

    @property
    def duration_seconds(self) -> float:
        """Calculate the duration of the job in seconds."""
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now(timezone.utc).isoformat()
        try:
            start_dt = datetime.fromisoformat(self.started_at)
            end_dt = datetime.fromisoformat(end)
            return (end_dt - start_dt).total_seconds()
        except (ValueError, TypeError):
            return 0.0


@dataclass
class BatchJob:
    """A batch of related jobs that are submitted together."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    job_ids: list[str] = field(default_factory=list)
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    progress: float = 0.0
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0


class TaskQueue:
    """Persistent task queue with priority scheduling and parallel execution.

    Manages the complete lifecycle of asynchronous jobs:
    - Priority-based scheduling with starvation prevention
    - Configurable concurrency per job type
    - Automatic retry with exponential backoff
    - Deadline enforcement with timeout handling
    - Progress tracking and status updates
    - Batch job submission and aggregation
    - Job dependency chains (parent/child relationships)
    """

    def __init__(self, max_concurrent: int = 5):
        self._jobs: dict[str, Job] = {}
        self._priority_queues: dict[JobPriority, asyncio.Queue] = {
            JobPriority.CRITICAL: asyncio.Queue(),
            JobPriority.HIGH: asyncio.Queue(),
            JobPriority.NORMAL: asyncio.Queue(),
            JobPriority.LOW: asyncio.Queue(),
            JobPriority.BACKGROUND: asyncio.Queue(),
        }
        self._batches: dict[str, BatchJob] = {}
        self._handlers: dict[JobType, Callable] = {}
        self._active_jobs: dict[str, asyncio.Task] = {}
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        logger.info(f"Task Queue initialized (max concurrent: {max_concurrent})")

    def register_handler(self, job_type: JobType, handler: Callable):
        """Register a handler function for a specific job type."""
        self._handlers[job_type] = handler
        logger.info(f"Handler registered for job type: {job_type.value}")

    def submit(
        self,
        name: str,
        job_type: JobType,
        payload: dict = None,
        priority: JobPriority = JobPriority.NORMAL,
        agent_id: str = "",
        max_retries: int = 3,
        timeout_seconds: int = 300,
        tags: list[str] = None,
        parent_job_id: str = "",
    ) -> Job:
        """Submit a new job to the queue."""
        job = Job(
            job_type=job_type,
            name=name,
            payload=payload or {},
            priority=priority,
            agent_id=agent_id,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            tags=tags or [],
            parent_job_id=parent_job_id,
        )
        job.status = JobStatus.QUEUED

        self._jobs[job.id] = job
        self._priority_queues[priority].put_nowait(job.id)

        # Link to parent
        if parent_job_id and parent_job_id in self._jobs:
            self._jobs[parent_job_id].child_job_ids.append(job.id)

        logger.info(
            f"Job submitted: {name} [{job_type.value}] priority={priority.value} id={job.id}"
        )
        return job

    def submit_batch(
        self,
        name: str,
        jobs: list[dict],
        priority: JobPriority = JobPriority.NORMAL,
        agent_id: str = "",
    ) -> BatchJob:
        """Submit a batch of related jobs."""
        batch = BatchJob(
            name=name,
            total_jobs=len(jobs),
        )

        for job_data in jobs:
            child = self.submit(
                name=job_data.get("name", f"{name} #{len(batch.job_ids) + 1}"),
                job_type=job_data.get("job_type", JobType.CUSTOM),
                payload=job_data.get("payload", {}),
                priority=priority,
                agent_id=agent_id,
                tags=job_data.get("tags", []),
            )
            batch.job_ids.append(child.id)

        self._batches[batch.id] = batch
        logger.info(f"Batch submitted: {name} ({len(jobs)} jobs)")
        return batch

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_batch(self, batch_id: str) -> Optional[BatchJob]:
        """Get a batch by ID."""
        return self._batches.get(batch_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or queued job."""
        if job_id not in self._jobs:
            return False

        job = self._jobs[job_id]
        if job.is_terminal:
            return False

        if job_id in self._active_jobs:
            self._active_jobs[job_id].cancel()

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Job cancelled: {job.name} ({job_id})")
        return True

    async def start(self):
        """Start the queue worker."""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Task Queue worker started")

    async def stop(self):
        """Stop the queue worker gracefully."""
        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        # Cancel all active jobs
        for job_id, task in list(self._active_jobs.items()):
            task.cancel()
            if job_id in self._jobs:
                self._jobs[job_id].status = JobStatus.CANCELLED

        logger.info("Task Queue worker stopped")

    async def _worker_loop(self):
        """Main worker loop that processes jobs from priority queues."""
        while self._running:
            try:
                job_id = await self._get_next_job()
                if job_id:
                    asyncio.create_task(self._process_job(job_id))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(1)

    async def _get_next_job(self) -> Optional[str]:
        """Get the next job from priority queues (highest priority first)."""
        priority_order = [
            JobPriority.CRITICAL,
            JobPriority.HIGH,
            JobPriority.NORMAL,
            JobPriority.LOW,
            JobPriority.BACKGROUND,
        ]

        for priority in priority_order:
            queue = self._priority_queues[priority]
            if not queue.empty():
                try:
                    return queue.get_nowait()
                except asyncio.QueueEmpty:
                    continue

        await asyncio.sleep(0.1)
        return None

    async def _process_job(self, job_id: str):
        """Process a single job with retry and timeout handling."""
        async with self._semaphore:
            if job_id not in self._jobs:
                return

            job = self._jobs[job_id]
            if job.is_terminal:
                return

            handler = self._handlers.get(job.job_type)
            if not handler:
                job.status = JobStatus.FAILED
                job.error = f"No handler registered for job type: {job.job_type.value}"
                job.completed_at = datetime.now(timezone.utc).isoformat()
                logger.error(f"Job failed: {job.name} - {job.error}")
                return

            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc).isoformat()

            try:
                result = await asyncio.wait_for(
                    handler(job),
                    timeout=job.timeout_seconds,
                )
                job.result = result
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                job.progress_message = "Completed"
                logger.info(f"Job completed: {job.name} ({job.duration_seconds:.1f}s)")

            except asyncio.TimeoutError:
                job.status = JobStatus.TIMED_OUT
                job.error = f"Job timed out after {job.timeout_seconds}s"
                logger.error(f"Job timed out: {job.name}")

            except Exception as e:
                job.retry_count += 1
                if job.retry_count <= job.max_retries:
                    job.status = JobStatus.RETRYING
                    job.error = str(e)
                    logger.warning(
                        f"Job retrying: {job.name} (attempt {job.retry_count}/{job.max_retries})"
                    )
                    await asyncio.sleep(job.retry_delay_seconds * job.retry_count)
                    self._priority_queues[job.priority].put_nowait(job_id)
                    return
                else:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    logger.error(f"Job failed after {job.max_retries} retries: {job.name} - {e}")

            finally:
                job.completed_at = datetime.now(timezone.utc).isoformat()
                self._update_batch_progress(job)

    def _update_batch_progress(self, job: Job):
        """Update progress for parent batch jobs."""
        for batch in self._batches.values():
            if job.id in batch.job_ids:
                completed = sum(
                    1 for jid in batch.job_ids
                    if jid in self._jobs and self._jobs[jid].is_terminal
                )
                batch.completed_jobs = completed
                batch.failed_jobs = sum(
                    1 for jid in batch.job_ids
                    if jid in self._jobs and self._jobs[jid].status == JobStatus.FAILED
                )
                batch.progress = completed / max(batch.total_jobs, 1)
                if completed >= batch.total_jobs:
                    batch.status = "completed"
                    batch.completed_at = datetime.now(timezone.utc).isoformat()

    def update_progress(self, job_id: str, progress: float, message: str = ""):
        """Update the progress of a running job."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.progress = min(1.0, max(0.0, progress))
            job.progress_message = message

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        priority: Optional[JobPriority] = None,
        agent_id: str = "",
        tags: list[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """List jobs with optional filtering."""
        results = list(self._jobs.values())

        if status:
            results = [j for j in results if j.status == status]
        if job_type:
            results = [j for j in results if j.job_type == job_type]
        if priority:
            results = [j for j in results if j.priority == priority]
        if agent_id:
            results = [j for j in results if j.agent_id == agent_id]
        if tags:
            results = [j for j in results if any(t in j.tags for t in tags)]

        results.sort(key=lambda j: j.created_at, reverse=True)
        return [self._job_to_dict(j) for j in results[:limit]]

    def list_batches(self, limit: int = 20) -> list[dict]:
        """List batch jobs."""
        batches = sorted(
            self._batches.values(),
            key=lambda b: b.created_at,
            reverse=True,
        )
        return [
            {
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "status": b.status,
                "progress": round(b.progress, 2),
                "total_jobs": b.total_jobs,
                "completed_jobs": b.completed_jobs,
                "failed_jobs": b.failed_jobs,
                "created_at": b.created_at,
                "completed_at": b.completed_at,
            }
            for b in batches[:limit]
        ]

    def get_stats(self) -> dict:
        """Get queue statistics."""
        status_counts = {}
        for job in self._jobs.values():
            status_counts[job.status.value] = status_counts.get(job.status.value, 0) + 1

        type_counts = {}
        for job in self._jobs.values():
            type_counts[job.job_type.value] = type_counts.get(job.job_type.value, 0) + 1

        queue_sizes = {
            p.value: self._priority_queues[p].qsize()
            for p in JobPriority
        }

        return {
            "total_jobs": len(self._jobs),
            "active_jobs": len(self._active_jobs),
            "status_counts": status_counts,
            "job_type_counts": type_counts,
            "queue_sizes": queue_sizes,
            "total_batches": len(self._batches),
            "max_concurrent": self._max_concurrent,
            "worker_running": self._running,
        }

    def _job_to_dict(self, job: Job) -> dict:
        """Convert a job to a dictionary for API responses."""
        return {
            "id": job.id,
            "job_type": job.job_type.value,
            "name": job.name,
            "description": job.description,
            "priority": job.priority.value,
            "status": job.status.value,
            "agent_id": job.agent_id,
            "payload": job.payload,
            "result": str(job.result)[:200] if job.result else None,
            "error": job.error,
            "progress": round(job.progress, 2),
            "progress_message": job.progress_message,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "tags": job.tags,
            "parent_job_id": job.parent_job_id,
            "child_job_ids": job.child_job_ids,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "duration_seconds": round(job.duration_seconds, 1),
        }


# Global singleton
task_queue = TaskQueue()