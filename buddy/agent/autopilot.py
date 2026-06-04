"""Buddy Autopilot — scheduled and always-on background task execution

Enables agents to run recurring tasks, proactive monitoring, and
background work even when the user is not actively interacting.
"""
from __future__ import annotations
import logging
import uuid
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.autopilot")


class AutopilotStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AutopilotTrigger(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    WEBHOOK = "webhook"
    MANUAL = "manual"


@dataclass
class AutopilotConfig:
    id: str = ""
    agent_id: str = ""
    name: str = ""
    description: str = ""
    trigger: AutopilotTrigger = AutopilotTrigger.INTERVAL
    schedule: str = ""  # cron expression or interval in seconds
    task_template: str = ""  # natural language task description
    status: AutopilotStatus = AutopilotStatus.ACTIVE
    max_runs: int = 0  # 0 = unlimited
    run_count: int = 0
    last_run_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger.value,
            "schedule": self.schedule,
            "task_template": self.task_template,
            "status": self.status.value,
            "max_runs": self.max_runs,
            "run_count": self.run_count,
            "last_run_at": self.last_run_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AutopilotEngine:
    """Manages scheduled and background task execution for agents."""

    def __init__(self):
        self._autopilots: dict[str, AutopilotConfig] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._executor: Callable[[str, str], Awaitable[str]] | None = None

    def set_executor(self, executor: Callable[[str, str], Awaitable[str]]):
        self._executor = executor

    def create(self, agent_id: str, name: str, task_template: str, trigger: AutopilotTrigger = AutopilotTrigger.INTERVAL, schedule: str = "3600", max_runs: int = 0, description: str = "") -> AutopilotConfig:
        config = AutopilotConfig(
            id=f"ap-{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            name=name,
            description=description,
            trigger=trigger,
            schedule=schedule,
            task_template=task_template,
            max_runs=max_runs,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._autopilots[config.id] = config
        logger.info(f"Autopilot created: {name} ({trigger.value}) for agent {agent_id}")

        if trigger == AutopilotTrigger.INTERVAL:
            self._start_interval(config)

        return config

    def _start_interval(self, config: AutopilotConfig):
        async def _runner():
            try:
                interval = int(config.schedule)
            except ValueError:
                interval = 3600

            while config.status == AutopilotStatus.ACTIVE:
                if config.max_runs > 0 and config.run_count >= config.max_runs:
                    config.status = AutopilotStatus.COMPLETED
                    break

                await asyncio.sleep(interval)
                if config.status != AutopilotStatus.ACTIVE:
                    break

                await self._execute_run(config)

        task = asyncio.create_task(_runner())
        self._tasks[config.id] = task

    async def _execute_run(self, config: AutopilotConfig):
        if not self._executor:
            logger.warning(f"No executor set for autopilot {config.id}")
            return

        config.run_count += 1
        config.last_run_at = datetime.now(timezone.utc).isoformat()
        config.updated_at = config.last_run_at

        try:
            logger.info(f"Autopilot running: {config.name} (run {config.run_count})")
            result = await self._executor(config.agent_id, config.task_template)
            logger.info(f"Autopilot completed: {config.name} -> {result[:100]}")
        except Exception as e:
            logger.error(f"Autopilot failed: {config.name} -> {e}")
            if config.max_runs > 0 and config.run_count >= config.max_runs:
                config.status = AutopilotStatus.FAILED

    def pause(self, autopilot_id: str) -> bool:
        config = self._autopilots.get(autopilot_id)
        if not config:
            return False
        config.status = AutopilotStatus.PAUSED
        config.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def resume(self, autopilot_id: str) -> bool:
        config = self._autopilots.get(autopilot_id)
        if not config:
            return False
        config.status = AutopilotStatus.ACTIVE
        config.updated_at = datetime.now(timezone.utc).isoformat()
        if config.trigger == AutopilotTrigger.INTERVAL:
            self._start_interval(config)
        return True

    def cancel(self, autopilot_id: str) -> bool:
        config = self._autopilots.get(autopilot_id)
        if not config:
            return False
        config.status = AutopilotStatus.FAILED
        config.updated_at = datetime.now(timezone.utc).isoformat()

        task = self._tasks.pop(autopilot_id, None)
        if task and not task.done():
            task.cancel()
        return True

    def get(self, autopilot_id: str) -> AutopilotConfig | None:
        return self._autopilots.get(autopilot_id)

    def list_by_agent(self, agent_id: str) -> list[dict]:
        return [
            c.to_dict()
            for c in self._autopilots.values()
            if c.agent_id == agent_id
        ]

    def list_all(self) -> list[dict]:
        return [c.to_dict() for c in self._autopilots.values()]

    def delete(self, autopilot_id: str) -> bool:
        self.cancel(autopilot_id)
        return self._autopilots.pop(autopilot_id, None) is not None

    def shutdown(self):
        """Gracefully stop all autopilot tasks."""
        for ap_id in list(self._autopilots.keys()):
            self.cancel(ap_id)
        logger.info("Autopilot engine shut down")


autopilot_engine = AutopilotEngine()