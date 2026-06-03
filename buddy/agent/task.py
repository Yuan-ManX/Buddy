"""Buddy Task Lifecycle — Autonomous task execution with state machine

Inspired by agent-native task management patterns:
- Six-state lifecycle: queued → dispatched → running → completed/failed/cancelled
- WebSocket real-time progress streaming
- Automatic retry with configurable attempts
- Task-scoped context isolation
"""
from __future__ import annotations
import enum
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from database.db import async_session
from database.models import Task as TaskModel
from sqlalchemy import select, desc, func

logger = logging.getLogger("buddy.task")


class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def terminal_states(cls) -> set["TaskStatus"]:
        return {cls.COMPLETED, cls.FAILED, cls.CANCELLED}

    @classmethod
    def active_states(cls) -> set["TaskStatus"]:
        return {cls.QUEUED, cls.DISPATCHED, cls.RUNNING}


class TaskKind(str, enum.Enum):
    CHAT = "chat"
    DIRECT = "direct"
    AUTOPILOT = "autopilot"
    QUICK = "quick"


class TaskLifecycle:
    """Manages the full task lifecycle with state machine enforcement."""

    VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
        TaskStatus.QUEUED: {TaskStatus.DISPATCHED, TaskStatus.CANCELLED},
        TaskStatus.DISPATCHED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
        TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.FAILED: set(),
        TaskStatus.CANCELLED: set(),
    }

    RETRYABLE_FAILURES = {"runtime_error", "timeout", "llm_error", "network_error"}

    def __init__(self):
        self._progress_callbacks: dict[str, list] = {}

    async def enqueue(
        self,
        agent_id: str,
        title: str,
        kind: TaskKind = TaskKind.DIRECT,
        payload: dict | None = None,
        conversation_id: str | None = None,
        max_attempts: int = 3,
        parent_task_id: str | None = None,
    ) -> TaskModel:
        async with async_session() as session:
            task = TaskModel(
                id=f"task-{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                title=title,
                status=TaskStatus.QUEUED.value,
                kind=kind.value,
                payload=payload or {},
                conversation_id=conversation_id,
                max_attempts=max_attempts,
                attempt=0,
                parent_task_id=parent_task_id,
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            logger.info(f"Task enqueued: {task.id} ({kind.value}) -> agent {agent_id}")
            return task

    async def transition(self, task_id: str, to_status: TaskStatus, result: dict | None = None, error: str | None = None) -> TaskModel | None:
        async with async_session() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result_set = await session.execute(stmt)
            task = result_set.scalars().first()
            if not task:
                logger.warning(f"Task not found: {task_id}")
                return None

            current = TaskStatus(task.status)
            if to_status not in self.VALID_TRANSITIONS.get(current, set()):
                logger.warning(f"Invalid transition: {current.value} -> {to_status.value} for {task_id}")
                return None

            task.status = to_status.value
            if to_status == TaskStatus.RUNNING:
                task.started_at = datetime.now(timezone.utc)
            elif to_status in TaskStatus.terminal_states():
                task.completed_at = datetime.now(timezone.utc)
            if result:
                task.result = result
            if error:
                task.error = error
            task.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(task)

            logger.info(f"Task {task_id}: {current.value} -> {to_status.value}")
            await self._notify_progress(task_id, to_status.value, result, error)
            return task

    async def claim(self, agent_id: str) -> TaskModel | None:
        async with async_session() as session:
            stmt = (
                select(TaskModel)
                .where(TaskModel.agent_id == agent_id, TaskModel.status == TaskStatus.QUEUED.value)
                .order_by(TaskModel.created_at)
                .limit(1)
            )
            result = await session.execute(stmt)
            task = result.scalars().first()
            if not task:
                return None
            return await self.transition(task.id, TaskStatus.DISPATCHED)

    async def should_retry(self, task: TaskModel) -> bool:
        if task.attempt >= task.max_attempts:
            return False
        failure_reason = (task.error or "").lower()
        return any(r in failure_reason for r in self.RETRYABLE_FAILURES)

    async def retry(self, task_id: str) -> TaskModel | None:
        async with async_session() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            task = result.scalars().first()
            if not task:
                return None
            if not await self.should_retry(task):
                return None

            task.status = TaskStatus.QUEUED.value
            task.attempt += 1
            task.error = None
            task.result = None
            task.started_at = None
            task.completed_at = None
            task.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(task)
            logger.info(f"Task {task_id} retry {task.attempt}/{task.max_attempts}")
            return task

    async def list_tasks(
        self,
        agent_id: str | None = None,
        status: TaskStatus | None = None,
        kind: TaskKind | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[TaskModel]:
        async with async_session() as session:
            stmt = select(TaskModel)
            if agent_id:
                stmt = stmt.where(TaskModel.agent_id == agent_id)
            if status:
                stmt = stmt.where(TaskModel.status == status.value)
            if kind:
                stmt = stmt.where(TaskModel.kind == kind.value)
            stmt = stmt.order_by(desc(TaskModel.created_at)).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_task(self, task_id: str) -> TaskModel | None:
        async with async_session() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def cancel(self, task_id: str) -> TaskModel | None:
        return await self.transition(task_id, TaskStatus.CANCELLED)

    def on_progress(self, task_id: str, callback):
        if task_id not in self._progress_callbacks:
            self._progress_callbacks[task_id] = []
        self._progress_callbacks[task_id].append(callback)

    async def _notify_progress(self, task_id: str, status: str, result: dict | None, error: str | None):
        callbacks = self._progress_callbacks.pop(task_id, [])
        for cb in callbacks:
            try:
                await cb({"task_id": task_id, "status": status, "result": result, "error": error})
            except Exception as e:
                logger.error(f"Progress callback error: {e}")


task_lifecycle = TaskLifecycle()