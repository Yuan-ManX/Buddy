"""Buddy Scheduler — Cron-based task scheduling engine with platform delivery.

Provides a unified scheduling layer for recurring tasks, one-shot jobs, and
event-driven triggers. Tasks can be delivered to any connected platform
(Web, Telegram, Discord, etc.) when they fire.

Features:
- Cron expression scheduling (standard 5-field + seconds)
- Interval-based scheduling (every N seconds/minutes/hours)
- Webhook-triggered execution
- Event-driven triggers (on agent start, on memory threshold, etc.)
- Task priority queue with concurrency control
- Per-task execution history and status tracking
- Platform-aware delivery (push results to IM, WebSocket, etc.)
- Natural-language schedule parsing ("every Monday at 9am")

Architecture:
    BuddyScheduler (singleton)
    ├── ScheduleRegistry (task definitions)
    ├── CronEngine (expression parsing + matching)
    ├── TaskRunner (execution + history)
    └── DeliveryManager (platform routing)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.scheduler")


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════════════════

class ScheduleType(str, Enum):
    """Types of scheduling triggers."""
    CRON = "cron"
    INTERVAL = "interval"
    ONE_SHOT = "one_shot"
    WEBHOOK = "webhook"
    EVENT = "event"


class ScheduleStatus(str, Enum):
    """Lifecycle states for scheduled tasks."""
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(int, Enum):
    """Priority levels for task execution."""
    LOW = 0
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class DeliveryPlatform(str, Enum):
    """Target platforms for delivering scheduled task results."""
    WEB = "web"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    FILE = "file"


@dataclass
class ScheduleConfig:
    """Configuration for a scheduled task trigger.

    For CRON type: cron_expression like "0 9 * * 1" (9am every Monday)
    For INTERVAL type: interval_seconds (e.g., 3600 for hourly)
    For ONE_SHOT type: execute_at (ISO datetime string)
    For WEBHOOK type: webhook_token for authentication
    For EVENT type: event_name to listen for
    """
    schedule_type: ScheduleType = ScheduleType.INTERVAL
    cron_expression: str = ""
    interval_seconds: int = 3600
    execute_at: str = ""  # ISO datetime for one_shot
    timezone_str: str = "UTC"
    webhook_token: str = ""
    event_name: str = ""
    max_retries: int = 3
    retry_delay_seconds: int = 60


@dataclass
class DeliveryConfig:
    """Configuration for result delivery."""
    platforms: list[DeliveryPlatform] = field(default_factory=lambda: [DeliveryPlatform.WEB])
    webhook_url: str = ""
    chat_id: str = ""
    channel: str = ""
    file_path: str = ""
    format: str = "text"  # text, markdown, json


@dataclass
class ScheduledTask:
    """A scheduled task definition."""
    id: str = field(default_factory=lambda: f"sched-{uuid.uuid4().hex[:12]}")
    name: str = "Untitled Task"
    description: str = ""
    agent_id: str = ""
    prompt: str = ""
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)
    priority: JobPriority = JobPriority.NORMAL
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run_at: str = ""
    next_run_at: str = ""
    run_count: int = 0
    fail_count: int = 0
    last_result: str = ""
    is_system_task: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "prompt": self.prompt[:200],
            "schedule": {
                "type": self.schedule.schedule_type.value,
                "cron_expression": self.schedule.cron_expression,
                "interval_seconds": self.schedule.interval_seconds,
                "execute_at": self.schedule.execute_at,
            },
            "delivery": {
                "platforms": [p.value for p in self.delivery.platforms],
            },
            "priority": self.priority.value,
            "status": self.status.value,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "run_count": self.run_count,
            "fail_count": self.fail_count,
        }


@dataclass
class ExecutionRecord:
    """Record of a single task execution."""
    id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    status: ScheduleStatus = ScheduleStatus.RUNNING
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str = ""
    duration_ms: float = 0.0
    result: str = ""
    error: str = ""
    retry_count: int = 0
    delivery_results: dict[str, bool] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# Cron Expression Parser
# ═══════════════════════════════════════════════════════════════════════════

class CronParser:
    """Parses and matches standard cron expressions (seconds minutes hours day month weekday)."""

    _FIELD_NAMES = ["second", "minute", "hour", "day", "month", "weekday"]
    _FIELD_RANGES = {
        "second": (0, 59),
        "minute": (0, 59),
        "hour": (0, 23),
        "day": (1, 31),
        "month": (1, 12),
        "weekday": (0, 6),  # 0 = Sunday
    }
    _MONTH_ALIASES = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    _WEEKDAY_ALIASES = {
        "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
    }

    @classmethod
    def parse_field(cls, field: str, field_name: str) -> set[int]:
        """Parse a single cron field into a set of matching values."""
        low, high = cls._FIELD_RANGES[field_name]
        values: set[int] = set()

        if field == "*":
            return set(range(low, high + 1))

        # Handle aliases
        field_lower = field.lower()
        if field_name == "month":
            for alias, num in cls._MONTH_ALIASES.items():
                field_lower = field_lower.replace(alias, str(num))
        elif field_name == "weekday":
            for alias, num in cls._WEEKDAY_ALIASES.items():
                field_lower = field_lower.replace(alias, str(num))

        parts = field_lower.split(",")
        for part in parts:
            part = part.strip()

            # Step values: */5 or 1-10/2
            if "/" in part:
                range_part, step_str = part.split("/", 1)
                step = int(step_str)
                if range_part == "*":
                    start, end = low, high
                elif "-" in range_part:
                    start, end = map(int, range_part.split("-"))
                else:
                    start = int(range_part)
                    end = high
                for v in range(start, end + 1, step):
                    if low <= v <= high:
                        values.add(v)
                continue

            # Range: 1-5
            if "-" in part:
                start, end = map(int, part.split("-"))
                for v in range(start, end + 1):
                    if low <= v <= high:
                        values.add(v)
                continue

            # Single value
            try:
                v = int(part)
                if low <= v <= high:
                    values.add(v)
            except ValueError:
                pass

        return values

    @classmethod
    def matches(cls, expression: str, dt: datetime) -> bool:
        """Check if a cron expression matches a datetime."""
        fields = expression.strip().split()
        if len(fields) < 5:
            fields = ["0"] + fields  # Add seconds

        while len(fields) < 6:
            fields.append("*")

        checks = [
            (fields[0], "second", dt.second),
            (fields[1], "minute", dt.minute),
            (fields[2], "hour", dt.hour),
            (fields[3], "day", dt.day),
            (fields[4], "month", dt.month),
            (fields[5], "weekday", (dt.weekday() + 1) % 7),  # Convert to 0=Sunday
        ]

        for field_expr, field_name, current_val in checks:
            allowed = cls.parse_field(field_expr, field_name)
            if current_val not in allowed:
                return False

        return True


# ═══════════════════════════════════════════════════════════════════════════
# Natural Language Schedule Parser
# ═══════════════════════════════════════════════════════════════════════════

class NaturalScheduleParser:
    """Parses natural language schedule descriptions into cron expressions.

    Examples:
        "every monday at 9am"     → "0 0 9 * * 1"
        "every hour"              → "0 0 * * * *"
        "daily at midnight"       → "0 0 0 * * *"
        "every 30 minutes"        → interval: 1800s
    """

    @classmethod
    def parse(cls, text: str) -> tuple[ScheduleType, str, int]:
        """Returns (schedule_type, cron_expression, interval_seconds)."""
        text = text.lower().strip()

        # Interval patterns
        interval_match = re.match(r"every\s+(\d+)\s*(second|sec|minute|min|hour|hr|day)s?", text)
        if interval_match:
            num = int(interval_match.group(1))
            unit = interval_match.group(2)
            multipliers = {"second": 1, "sec": 1, "minute": 60, "min": 60, "hour": 3600, "hr": 3600, "day": 86400}
            interval = num * multipliers.get(unit, 3600)
            return ScheduleType.INTERVAL, "", interval

        # "every hour"
        if text == "every hour" or text == "hourly":
            return ScheduleType.CRON, "0 0 * * * *", 0
        if text in ("every minute", "minutely"):
            return ScheduleType.CRON, "0 * * * * *", 0

        # "daily at [time]" / "every day at [time]"
        daily_match = re.match(r"(?:daily|every\s*day)\s*(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
        if daily_match:
            hour = int(daily_match.group(1))
            minute = int(daily_match.group(2) or 0)
            ampm = daily_match.group(3)
            if ampm == "pm" and hour < 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
            return ScheduleType.CRON, f"0 {minute} {hour} * * *", 0

        # Weekly patterns
        weekday_map = {"monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
                       "friday": 5, "saturday": 6, "sunday": 0,
                       "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}

        for day_name, day_num in weekday_map.items():
            pattern = rf"every\s+{day_name}\s*(?:at\s*)?(\d{{1,2}})(?::(\d{{2}}))?\s*(am|pm)?"
            match = re.match(pattern, text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2) or 0)
                ampm = match.group(3)
                if ampm == "pm" and hour < 12:
                    hour += 12
                if ampm == "am" and hour == 12:
                    hour = 0
                return ScheduleType.CRON, f"0 {minute} {hour} * * {day_num}", 0

        # "every X hours" / "every X minutes"
        every_x_match = re.match(r"every\s+(\d+)\s+(second|minute|hour|day|week)s?", text)
        if every_x_match:
            num = int(every_x_match.group(1))
            unit = every_x_match.group(2)
            multipliers = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}
            interval = num * multipliers.get(unit, 3600)
            return ScheduleType.INTERVAL, "", interval

        # Midnight / Noon
        if text == "midnight":
            return ScheduleType.CRON, "0 0 0 * * *", 0
        if text == "noon":
            return ScheduleType.CRON, "0 0 12 * * *", 0

        # Default: hourly
        return ScheduleType.INTERVAL, "", 3600


# ═══════════════════════════════════════════════════════════════════════════
# Task Registry
# ═══════════════════════════════════════════════════════════════════════════

class ScheduleRegistry:
    """Manages scheduled task definitions and execution records."""

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._execution_history: dict[str, list[ExecutionRecord]] = {}
        self._executor: Callable[[ScheduledTask], Awaitable[str]] | None = None

    def set_executor(self, executor: Callable[[ScheduledTask], Awaitable[str]]) -> None:
        """Set the function that executes scheduled tasks."""
        self._executor = executor

    def add_task(self, task: ScheduledTask) -> ScheduledTask:
        self._tasks[task.id] = task
        self._execution_history.setdefault(task.id, [])
        logger.info(f"Scheduled task registered: {task.id} ({task.name})")
        return task

    def remove_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._execution_history.pop(task_id, None)
            logger.info(f"Scheduled task removed: {task_id}")
            return True
        return False

    def get_task(self, task_id: str) -> ScheduledTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, status: ScheduleStatus | None = None) -> list[ScheduledTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: (t.priority.value, t.created_at), reverse=True)

    def get_active_tasks(self) -> list[ScheduledTask]:
        return [t for t in self._tasks.values() if t.status == ScheduleStatus.ACTIVE]

    def record_execution(self, record: ExecutionRecord) -> None:
        history = self._execution_history.setdefault(record.task_id, [])
        history.append(record)
        if len(history) > 50:
            self._execution_history[record.task_id] = history[-50:]

        task = self._tasks.get(record.task_id)
        if task:
            task.run_count += 1
            if record.status == ScheduleStatus.FAILED:
                task.fail_count += 1
            task.last_run_at = record.finished_at or record.started_at
            task.last_result = record.result[:500] if record.result else ""

    def get_history(self, task_id: str) -> list[ExecutionRecord]:
        return self._execution_history.get(task_id, [])

    def pause_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status == ScheduleStatus.ACTIVE:
            task.status = ScheduleStatus.PAUSED
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status == ScheduleStatus.PAUSED:
            task.status = ScheduleStatus.ACTIVE
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Delivery Manager
# ═══════════════════════════════════════════════════════════════════════════

class DeliveryManager:
    """Routes task execution results to configured delivery platforms."""

    def __init__(self):
        self._deliverers: dict[DeliveryPlatform, Callable[[str, DeliveryConfig], Awaitable[bool]]] = {}

    def register_deliverer(
        self,
        platform: DeliveryPlatform,
        handler: Callable[[str, DeliveryConfig], Awaitable[bool]],
    ) -> None:
        self._deliverers[platform] = handler

    async def deliver(self, result: str, config: DeliveryConfig) -> dict[str, bool]:
        """Deliver a result to all configured platforms."""
        outcomes: dict[str, bool] = {}
        for platform in config.platforms:
            handler = self._deliverers.get(platform)
            if handler:
                try:
                    outcomes[platform.value] = await handler(result, config)
                except Exception as e:
                    logger.error(f"Delivery to {platform.value} failed: {e}")
                    outcomes[platform.value] = False
            else:
                outcomes[platform.value] = False
                logger.warning(f"No deliverer registered for platform: {platform.value}")
        return outcomes


# ═══════════════════════════════════════════════════════════════════════════
# Scheduler Engine
# ═══════════════════════════════════════════════════════════════════════════

class SchedulerEngine:
    """Main scheduling loop that checks tasks and triggers execution."""

    def __init__(self, registry: ScheduleRegistry):
        self._registry = registry
        self._delivery = DeliveryManager()
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._tick_interval = 15  # seconds
        self._max_concurrent = 3
        self._running_executions: set[str] = set()
        self._execution_lock = asyncio.Lock()

    @property
    def delivery(self) -> DeliveryManager:
        return self._delivery

    async def start(self, tick_interval: int = 15) -> None:
        self._tick_interval = tick_interval
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Scheduler engine started (tick={tick_interval}s, max_concurrent={self._max_concurrent})")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler engine stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Scheduler tick error: {e}")
            await asyncio.sleep(self._tick_interval)

    async def _tick(self) -> None:
        """Check all active tasks and execute those due to run."""
        active_tasks = self._registry.get_active_tasks()
        now = datetime.now(timezone.utc)

        for task in active_tasks:
            if len(self._running_executions) >= self._max_concurrent:
                break

            if task.id in self._running_executions:
                continue

            if self._should_run(task, now):
                asyncio.create_task(self._execute_task(task))

    def _should_run(self, task: ScheduledTask, now: datetime) -> bool:
        """Determine if a task is due to run."""
        config = task.schedule

        if config.schedule_type == ScheduleType.INTERVAL:
            if not task.last_run_at:
                return True
            last = datetime.fromisoformat(task.last_run_at)
            elapsed = (now - last).total_seconds()
            return elapsed >= config.interval_seconds

        if config.schedule_type == ScheduleType.CRON:
            if not config.cron_expression:
                return False
            # Don't re-execute within the same minute
            if task.last_run_at:
                last = datetime.fromisoformat(task.last_run_at)
                if (now - last).total_seconds() < 60:
                    return False
            return CronParser.matches(config.cron_expression, now)

        if config.schedule_type == ScheduleType.ONE_SHOT:
            if not config.execute_at:
                return False
            if task.last_run_at:
                return False  # Already executed
            execute_time = datetime.fromisoformat(config.execute_at)
            return now >= execute_time

        return False

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single scheduled task."""
        self._running_executions.add(task.id)
        task.status = ScheduleStatus.RUNNING

        record = ExecutionRecord(task_id=task.id)
        started = time.time()

        try:
            if self._registry._executor:
                result = await self._registry._executor(task)
                record.result = result or ""
                record.status = ScheduleStatus.COMPLETED
                task.status = ScheduleStatus.ACTIVE
            else:
                record.result = "[No executor configured]"
                record.status = ScheduleStatus.COMPLETED
                task.status = ScheduleStatus.ACTIVE

            # Deliver results
            if record.result:
                delivery_outcomes = await self._delivery.deliver(record.result, task.delivery)
                record.delivery_results = delivery_outcomes

        except Exception as e:
            logger.error(f"Task {task.id} ({task.name}) failed: {e}")
            record.error = str(e)
            record.status = ScheduleStatus.FAILED
            task.status = ScheduleStatus.FAILED

        finally:
            record.finished_at = datetime.now(timezone.utc).isoformat()
            record.duration_ms = (time.time() - started) * 1000
            self._registry.record_execution(record)
            self._running_executions.discard(task.id)
            task.next_run_at = datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════
# Buddy Scheduler Facade
# ═══════════════════════════════════════════════════════════════════════════

class BuddyScheduler:
    """Central facade for task scheduling and execution.

    Usage:
        scheduler = BuddyScheduler()

        # Create a task
        task = scheduler.schedule(
            name="Daily Report",
            prompt="Generate a daily summary report",
            cron_expression="0 0 9 * * *",
        )

        # Start the engine
        await scheduler.start()

        # Parse natural language
        sched_type, cron, interval = NaturalScheduleParser.parse("every monday at 9am")
        task = scheduler.schedule(name="Weekly Standup", prompt="...", cron_expression=cron)
    """

    def __init__(self):
        self.registry = ScheduleRegistry()
        self.engine = SchedulerEngine(self.registry)

    def set_executor(self, executor: Callable[[ScheduledTask], Awaitable[str]]) -> None:
        self.registry.set_executor(executor)
        logger.info("Scheduler executor wired")

    def schedule(
        self,
        name: str,
        prompt: str,
        agent_id: str = "",
        cron_expression: str = "",
        interval_seconds: int = 3600,
        schedule_type: ScheduleType | None = None,
        description: str = "",
        platforms: list[DeliveryPlatform] | None = None,
        priority: JobPriority = JobPriority.NORMAL,
        tags: list[str] | None = None,
        is_system_task: bool = False,
    ) -> ScheduledTask:
        """Create and register a new scheduled task."""
        if schedule_type is None:
            if cron_expression:
                schedule_type = ScheduleType.CRON
            elif interval_seconds:
                schedule_type = ScheduleType.INTERVAL
            else:
                schedule_type = ScheduleType.INTERVAL

        config = ScheduleConfig(
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
        )

        delivery = DeliveryConfig(
            platforms=platforms or [DeliveryPlatform.WEB],
        )

        task = ScheduledTask(
            name=name,
            description=description,
            agent_id=agent_id,
            prompt=prompt,
            schedule=config,
            delivery=delivery,
            priority=priority,
            tags=tags or [],
            is_system_task=is_system_task,
        )

        self.registry.add_task(task)
        return task

    def schedule_natural(self, name: str, prompt: str, natural_schedule: str, **kwargs: Any) -> ScheduledTask:
        """Schedule a task using natural language description."""
        sched_type, cron_expr, interval = NaturalScheduleParser.parse(natural_schedule)
        return self.schedule(
            name=name,
            prompt=prompt,
            cron_expression=cron_expr,
            interval_seconds=interval,
            schedule_type=sched_type,
            **kwargs,
        )

    def cancel_task(self, task_id: str) -> bool:
        task = self.registry.get_task(task_id)
        if task:
            task.status = ScheduleStatus.CANCELLED
            return True
        return False

    def pause_task(self, task_id: str) -> bool:
        return self.registry.pause_task(task_id)

    def resume_task(self, task_id: str) -> bool:
        return self.registry.resume_task(task_id)

    def get_task(self, task_id: str) -> ScheduledTask | None:
        return self.registry.get_task(task_id)

    def list_tasks(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.registry.list_tasks()]

    def get_history(self, task_id: str) -> list[dict[str, Any]]:
        records = self.registry.get_history(task_id)
        return [
            {
                "id": r.id,
                "status": r.status.value,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "duration_ms": r.duration_ms,
                "result": r.result[:500],
                "error": r.error,
                "delivery_results": r.delivery_results,
            }
            for r in records
        ]

    async def start(self) -> None:
        await self.engine.start()

    async def stop(self) -> None:
        await self.engine.stop()

    def get_stats(self) -> dict[str, Any]:
        tasks = self.registry.list_tasks()
        total = len(tasks)
        status_counts: dict[str, int] = {}
        for t in tasks:
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1

        total_runs = sum(t.run_count for t in tasks)
        total_fails = sum(t.fail_count for t in tasks)

        return {
            "total_tasks": total,
            "by_status": status_counts,
            "total_runs": total_runs,
            "total_failures": total_fails,
            "engine_running": self.engine._running,
            "active_executions": len(self.engine._running_executions),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

buddy_scheduler = BuddyScheduler()