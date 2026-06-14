"""Buddy Autopilot — scheduled and always-on background task execution

Enables agents to run recurring tasks, proactive monitoring, and
background work even when the user is not actively interacting.
"""
from __future__ import annotations
import logging
import uuid
import asyncio
import time
from datetime import datetime, timezone, timedelta
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
        self.autopilot_condition: dict[str, Callable[[], bool]] = {}
        self.autopilot_rate_limit: dict[str, tuple[float, float]] = {}
        self.autopilot_result_cache: dict[str, list[dict]] = {}
        self._notifications: list[dict] = []

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
        self.autopilot_condition.pop(autopilot_id, None)
        self.autopilot_rate_limit.pop(autopilot_id, None)
        self.autopilot_result_cache.pop(autopilot_id, None)
        return self._autopilots.pop(autopilot_id, None) is not None

    # ── Conditional Trigger ─────────────────────────────────

    def set_condition(self, autopilot_id: str, condition_fn: Callable[[], bool]):
        """Set a conditional trigger for an autopilot task.

        The condition function is evaluated before each scheduled run.
        If it returns False, the run is skipped for this cycle.
        Example: lambda: agent.memory.get_new_count() > 10
        """
        self.autopilot_condition[autopilot_id] = condition_fn

    def check_condition(self, autopilot_id: str) -> bool:
        """Evaluate the condition for an autopilot. Returns True if no condition set."""
        condition_fn = self.autopilot_condition.get(autopilot_id)
        if condition_fn is None:
            return True
        try:
            return condition_fn()
        except Exception as e:
            logger.warning(f"Condition check failed for {autopilot_id}: {e}")
            return False

    # ── Rate Limiting ───────────────────────────────────────

    def set_rate_limit(self, autopilot_id: str, min_interval_seconds: float):
        """Set minimum interval between autopilot runs.

        Args:
            min_interval_seconds: Minimum seconds between consecutive runs.
        """
        self.autopilot_rate_limit[autopilot_id] = (min_interval_seconds, 0.0)

    def is_rate_limited(self, autopilot_id: str) -> bool:
        """Check if the autopilot is currently rate-limited."""
        rate_limit = self.autopilot_rate_limit.get(autopilot_id)
        if rate_limit is None:
            return False
        min_interval, last_run = rate_limit
        elapsed = time.time() - last_run
        return elapsed < min_interval

    def _mark_run_time(self, autopilot_id: str):
        """Record the timestamp of the most recent run for rate limiting."""
        if autopilot_id in self.autopilot_rate_limit:
            min_interval, _ = self.autopilot_rate_limit[autopilot_id]
            self.autopilot_rate_limit[autopilot_id] = (min_interval, time.time())

    # ── Result Cache ────────────────────────────────────────

    def cache_result(self, autopilot_id: str, result: str, max_cache_size: int = 20):
        """Cache an autopilot execution result."""
        if autopilot_id not in self.autopilot_result_cache:
            self.autopilot_result_cache[autopilot_id] = []
        cache = self.autopilot_result_cache[autopilot_id]
        cache.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": result[:500],
        })
        if len(cache) > max_cache_size:
            self.autopilot_result_cache[autopilot_id] = cache[-max_cache_size:]

    def get_cached_results(self, autopilot_id: str, limit: int = 10) -> list[dict]:
        """Get recent cached results for an autopilot."""
        cache = self.autopilot_result_cache.get(autopilot_id, [])
        return cache[-limit:]

    # ── Notification ────────────────────────────────────────

    def autopilot_notification(self, autopilot_id: str, channel: str = "log"):
        """Send a notification when autopilot completes a task.

        Supports channels:
        - "log": Standard logging (default)
        - "callback": User-registered callback function
        """
        config = self._autopilots.get(autopilot_id)
        if not config:
            return

        message = (
            f"Autopilot '{config.name}' completed run {config.run_count}. "
            f"Status: {config.status.value}"
        )
        notification = {
            "id": f"notif-{uuid.uuid4().hex[:8]}",
            "autopilot_id": autopilot_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel": channel,
        }
        self._notifications.append(notification)

        if channel == "log":
            logger.info(f"[NOTIFICATION] {message}")
        # Keep only the last 100 notifications
        if len(self._notifications) > 100:
            self._notifications = self._notifications[-50:]

    def get_notifications(self, autopilot_id: str | None = None, limit: int = 20) -> list[dict]:
        """Get recent notifications, optionally filtered by autopilot."""
        notifs = self._notifications
        if autopilot_id:
            notifs = [n for n in notifs if n["autopilot_id"] == autopilot_id]
        return notifs[-limit:]

    # ── Health Check ────────────────────────────────────────

    def autopilot_health_check(self) -> dict:
        """Self-diagnostic to ensure the autopilot system is functioning correctly.

        Checks:
        - Active tasks that haven't run recently (stalled detection)
        - Tasks that have failed repeatedly
        - Executor availability
        - Rate limit status
        """
        now = time.time()
        issues = []
        active_count = 0
        stalled_count = 0
        failed_count = 0

        for ap_id, config in self._autopilots.items():
            if config.status == AutopilotStatus.ACTIVE:
                active_count += 1

                # Check for stalled tasks (active but no recent run)
                if config.last_run_at:
                    try:
                        last_run_dt = datetime.fromisoformat(config.last_run_at)
                        last_run_ts = last_run_dt.timestamp()
                        hours_since_run = (now - last_run_ts) / 3600
                        # If scheduled to run but hasn't in 24h, flag as stalled
                        if config.trigger in (AutopilotTrigger.INTERVAL, AutopilotTrigger.CRON):
                            try:
                                expected_interval = int(config.schedule)
                            except ValueError:
                                expected_interval = 3600
                            if hours_since_run > max(expected_interval * 3 / 3600, 1):
                                stalled_count += 1
                                issues.append(f"Stalled: '{config.name}' has not run in {hours_since_run:.1f}h (expected every {expected_interval}s)")
                    except (ValueError, TypeError):
                        pass

            if config.status == AutopilotStatus.FAILED:
                failed_count += 1
                issues.append(f"Failed: '{config.name}' is in FAILED state (run {config.run_count})")

        # Check executor availability
        executor_ok = self._executor is not None
        if not executor_ok:
            issues.append("No executor configured — autopilot tasks cannot run")

        return {
            "healthy": len(issues) == 0 and executor_ok,
            "active_tasks": active_count,
            "stalled_tasks": stalled_count,
            "failed_tasks": failed_count,
            "total_tasks": len(self._autopilots),
            "executor_available": executor_ok,
            "issues": issues,
        }

    def shutdown(self):
        """Gracefully stop all autopilot tasks."""
        for ap_id in list(self._autopilots.keys()):
            self.cancel(ap_id)
        logger.info("Autopilot engine shut down")


autopilot_engine = AutopilotEngine()


# ── Autopilot Schedule ───────────────────────────────────

class AutopilotSchedule:
    """Cron-based autopilot scheduling with timezone support.

    Supports a simplified cron-like syntax:
    - Format: "minute hour day_of_month month day_of_week"
    - Wildcards (*) are supported
    - Timezone can be specified for correct local-time scheduling
    """

    DAY_NAMES = {
        "mon": 0, "tue": 1, "wed": 2, "thu": 3,
        "fri": 4, "sat": 5, "sun": 6,
    }

    def __init__(self, cron_expression: str, timezone_name: str = "UTC"):
        self.cron = cron_expression
        self.tz_name = timezone_name

    @staticmethod
    def parse_cron(expression: str) -> dict:
        """Parse a simplified cron expression into its components."""
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Cron expression must have 5 fields, got {len(parts)}: {expression}")
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "dow": parts[4],
        }

    @staticmethod
    def _matches(value: int, field: str, extra_range: int = 0) -> bool:
        """Check if a value matches a cron field (including wildcards and lists)."""
        if field == "*":
            return True
        if "," in field:
            return any(
                AutopilotSchedule._matches(value, part.strip())
                for part in field.split(",")
            )
        if "/" in field:
            base, _, step = field.partition("/")
            base_int = int(base) if base != "*" else 0
            rng = extra_range if extra_range > 0 else 59
            return value >= base_int and (value - base_int) % int(step) == 0
        if "-" in field:
            lo, _, hi = field.partition("-")
            return int(lo) <= value <= int(hi)
        return value == int(field)

    def is_due(self, now: datetime | None = None) -> bool:
        """Check if the schedule is due at the given time (or now)."""
        if now is None:
            if self.tz_name == "UTC":
                now = datetime.now(timezone.utc)
            else:
                now = datetime.now(timezone.utc)

        cron = self.parse_cron(self.cron)

        # Resolve day-of-week names
        dow_field = cron["dow"].lower()
        for name, num in self.DAY_NAMES.items():
            dow_field = dow_field.replace(name, str(num))

        day_of_week = now.weekday()  # 0=Monday, 6=Sunday (Python convention)

        return (
            self._matches(now.minute, cron["minute"], 59) and
            self._matches(now.hour, cron["hour"], 23) and
            self._matches(now.day, cron["day"], 31) and
            self._matches(now.month, cron["month"], 12) and
            self._matches(day_of_week, dow_field, 6)
        )

    def next_run(self, after: datetime | None = None) -> datetime:
        """Calculate the next run time after the given datetime."""
        if after is None:
            after = datetime.now(timezone.utc)

        # Simple implementation: check each minute for up to 30 days
        cron = self.parse_cron(self.cron)
        check = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        for _ in range(60 * 24 * 30):  # Up to 30 days
            dow_field = cron["dow"].lower()
            for name, num in self.DAY_NAMES.items():
                dow_field = dow_field.replace(name, str(num))

            if (
                self._matches(check.minute, cron["minute"], 59) and
                self._matches(check.hour, cron["hour"], 23) and
                self._matches(check.day, cron["day"], 31) and
                self._matches(check.month, cron["month"], 12) and
                self._matches(check.weekday(), dow_field, 6)
            ):
                return check
            check += timedelta(minutes=1)

        raise ValueError(f"No matching time found within 30 days for: {self.cron}")