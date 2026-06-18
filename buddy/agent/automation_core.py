"""Buddy Automation Core — Scheduled automation and task orchestration.

Provides a unified automation layer for scheduled tasks, event-driven
workflows, and conditional automation execution. Automations are defined
through templates, scheduled via cron expressions, executed with retry
policies, and monitored through performance analytics.

Features:
- Automation definitions with multiple trigger types
- Cron-based scheduling with timezone support
- Task execution with retry policies and timeouts
- Event watching with filtering and deduplication
- Execution analytics with failure analysis

Architecture:
    AutomationCore (singleton)
    ├── AutomationRegistry (definitions + templates)
    ├── CronScheduler (cron parsing + scheduling)
    ├── AutomationRunner (execution + retries)
    ├── EventWatcher (event triggers + chains)
    └── AutomationAnalytics (metrics + suggestions)
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.automation")


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class AutomationType(str, Enum):
    """Types of automation definitions."""
    SCHEDULED = "scheduled"
    EVENT_TRIGGERED = "event_triggered"
    CONDITIONAL = "conditional"
    MANUAL = "manual"


class TriggerType(str, Enum):
    """Types of automation triggers."""
    CRON = "cron"
    INTERVAL = "interval"
    WEBHOOK = "webhook"
    FILE_CHANGE = "file_change"
    STATE_CHANGE = "state_change"
    API_CALL = "api_call"


class AutomationLifecycle(str, Enum):
    """Lifecycle states for automation definitions."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    DISABLED = "disabled"


class ExecutionStatus(str, Enum):
    """Status of a single automation execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class BackoffStrategy(str, Enum):
    """Retry backoff strategies for failed executions."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class EventType(str, Enum):
    """Types of events that can trigger automations."""
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    API_RESPONSE = "api_response"
    STATE_CHANGE = "state_change"
    AGENT_ACTION = "agent_action"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AutomationTrigger:
    """Configuration for an automation trigger."""
    trigger_type: TriggerType = TriggerType.CRON
    cron_expression: str = ""
    interval_seconds: int = 0
    webhook_token: str = ""
    webhook_url: str = ""
    file_pattern: str = ""
    file_path: str = ""
    state_key: str = ""
    state_value: Any = None
    api_endpoint: str = ""
    api_method: str = "GET"
    timezone: str = "UTC"

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_type": self.trigger_type.value,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "timezone": self.timezone,
        }


@dataclass
class RetryPolicy:
    """Retry configuration for automation execution."""
    max_attempts: int = 3
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0
    retry_on_errors: list[str] = field(default_factory=lambda: ["TimeoutError", "ConnectionError"])
    retry_on_status_codes: list[int] = field(default_factory=lambda: [500, 502, 503, 504])

    def compute_delay(self, attempt: int) -> float:
        """Compute the delay for a given retry attempt."""
        if self.backoff_strategy == BackoffStrategy.FIXED:
            return self.base_delay_seconds
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            return min(self.base_delay_seconds * attempt, self.max_delay_seconds)
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            return min(self.base_delay_seconds * (2 ** (attempt - 1)), self.max_delay_seconds)
        return self.base_delay_seconds


@dataclass
class ExecutionContext:
    """Context for a single automation execution."""
    variables: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)
    parent_execution_id: str = ""
    triggered_by: str = ""
    triggered_by_event: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": {k: str(v)[:200] for k, v in self.variables.items()},
            "environment_keys": list(self.environment.keys()),
            "permissions": self.permissions,
            "triggered_by": self.triggered_by,
        }


@dataclass
class AutomationDefinition:
    """A complete automation definition."""
    id: str = field(default_factory=lambda: f"auto-{uuid.uuid4().hex[:12]}")
    name: str = "Untitled Automation"
    description: str = ""
    automation_type: AutomationType = AutomationType.SCHEDULED
    lifecycle: AutomationLifecycle = AutomationLifecycle.DRAFT
    trigger: AutomationTrigger = field(default_factory=AutomationTrigger)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    task_config: dict[str, Any] = field(default_factory=dict)
    template_id: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_executed_at: str = ""
    next_execution_at: str = ""
    execution_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    avg_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description[:200],
            "automation_type": self.automation_type.value,
            "lifecycle": self.lifecycle.value,
            "trigger": self.trigger.to_dict(),
            "tags": self.tags,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "last_executed_at": self.last_executed_at,
            "next_execution_at": self.next_execution_at,
            "created_at": self.created_at,
        }


@dataclass
class AutomationTemplate:
    """A reusable template for creating automation definitions."""
    id: str = field(default_factory=lambda: f"atpl-{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    automation_type: AutomationType = AutomationType.SCHEDULED
    trigger: AutomationTrigger = field(default_factory=AutomationTrigger)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    default_task_config: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExecutionResult:
    """Result of a single automation execution."""
    id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:12]}")
    automation_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str = ""
    duration_ms: float = 0.0
    output: Any = None
    error: str = ""
    error_type: str = ""
    attempt: int = 1
    context: ExecutionContext = field(default_factory=ExecutionContext)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "automation_id": self.automation_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error": self.error[:500],
            "error_type": self.error_type,
            "attempt": self.attempt,
        }


@dataclass
class WatchedEvent:
    """An event captured by the EventWatcher."""
    id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.STATE_CHANGE
    source: str = ""
    payload: Any = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        """Generate a fingerprint for deduplication."""
        import hashlib
        raw = f"{self.event_type.value}:{self.source}:{str(self.payload)}:{self.correlation_id}"
        return hashlib.md5(raw.encode()).hexdigest()


@dataclass
class EventFilter:
    """Filter criteria for matching events to automations."""
    event_types: list[EventType] = field(default_factory=list)
    source_pattern: str = ""
    payload_key: str = ""
    payload_value: Any = None
    correlation_id: str = ""
    metadata_filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventChain:
    """Chain linking automations through emitted events."""
    id: str = field(default_factory=lambda: f"chain-{uuid.uuid4().hex[:12]}")
    source_automation_id: str = ""
    source_event: EventType = EventType.AGENT_ACTION
    target_automation_id: str = ""
    condition: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FailureRecord:
    """Detailed record of an automation execution failure."""
    execution_id: str = ""
    automation_id: str = ""
    execution_name: str = ""
    error_message: str = ""
    error_type: str = ""
    occurred_at: str = ""
    attempt: int = 1
    stack_trace: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# Automation Registry
# ═══════════════════════════════════════════════════════════════════════════

class AutomationRegistry:
    """Manages automation definitions, templates, and lifecycle transitions.

    Stores all automation definitions and templates, handles lifecycle
    state transitions, and supports template-based automation creation.
    """

    def __init__(self):
        self._automations: dict[str, AutomationDefinition] = {}
        self._templates: dict[str, AutomationTemplate] = {}
        self._execution_history: dict[str, list[ExecutionResult]] = {}

    # ── Automation CRUD ───────────────────────────────────────

    def add_automation(self, automation: AutomationDefinition) -> AutomationDefinition:
        """Register a new automation definition."""
        self._automations[automation.id] = automation
        self._execution_history.setdefault(automation.id, [])
        logger.info(f"Automation registered: {automation.id} ({automation.name})")
        return automation

    def get_automation(self, automation_id: str) -> AutomationDefinition | None:
        """Get an automation by ID."""
        return self._automations.get(automation_id)

    def list_automations(
        self,
        lifecycle: AutomationLifecycle | None = None,
        automation_type: AutomationType | None = None,
        tags: list[str] | None = None,
    ) -> list[AutomationDefinition]:
        """List automations with optional filters."""
        results = list(self._automations.values())
        if lifecycle:
            results = [a for a in results if a.lifecycle == lifecycle]
        if automation_type:
            results = [a for a in results if a.automation_type == automation_type]
        if tags:
            results = [a for a in results if any(t in a.tags for t in tags)]
        return sorted(results, key=lambda a: a.created_at, reverse=True)

    def get_active_automations(self) -> list[AutomationDefinition]:
        """Get all automations in the active lifecycle state."""
        return [a for a in self._automations.values() if a.lifecycle == AutomationLifecycle.ACTIVE]

    def get_by_trigger(self, trigger_type: TriggerType) -> list[AutomationDefinition]:
        """Get automations that use a specific trigger type."""
        return [
            a for a in self._automations.values()
            if a.trigger.trigger_type == trigger_type and a.lifecycle == AutomationLifecycle.ACTIVE
        ]

    def remove_automation(self, automation_id: str) -> bool:
        """Remove an automation definition."""
        if automation_id in self._automations:
            del self._automations[automation_id]
            self._execution_history.pop(automation_id, None)
            logger.info(f"Automation removed: {automation_id}")
            return True
        return False

    # ── Lifecycle Management ──────────────────────────────────

    def set_lifecycle(self, automation_id: str, state: AutomationLifecycle) -> bool:
        """Transition an automation to a new lifecycle state."""
        automation = self._automations.get(automation_id)
        if not automation:
            logger.warning(f"Automation not found: {automation_id}")
            return False

        valid_transitions = {
            AutomationLifecycle.DRAFT: [AutomationLifecycle.ACTIVE, AutomationLifecycle.DISABLED],
            AutomationLifecycle.ACTIVE: [AutomationLifecycle.PAUSED, AutomationLifecycle.COMPLETED,
                                         AutomationLifecycle.ERROR, AutomationLifecycle.DISABLED],
            AutomationLifecycle.PAUSED: [AutomationLifecycle.ACTIVE, AutomationLifecycle.DISABLED],
            AutomationLifecycle.ERROR: [AutomationLifecycle.DRAFT, AutomationLifecycle.DISABLED],
            AutomationLifecycle.COMPLETED: [AutomationLifecycle.DRAFT],
            AutomationLifecycle.DISABLED: [AutomationLifecycle.DRAFT],
        }

        allowed = valid_transitions.get(automation.lifecycle, [])
        if state not in allowed:
            logger.warning(
                f"Invalid lifecycle transition: {automation.lifecycle.value} -> {state.value}"
            )
            return False

        automation.lifecycle = state
        automation.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Automation {automation_id}: {automation.lifecycle.value} -> {state.value}")
        return True

    def pause_automation(self, automation_id: str) -> bool:
        """Pause an active automation."""
        return self.set_lifecycle(automation_id, AutomationLifecycle.PAUSED)

    def resume_automation(self, automation_id: str) -> bool:
        """Resume a paused automation."""
        return self.set_lifecycle(automation_id, AutomationLifecycle.ACTIVE)

    def disable_automation(self, automation_id: str) -> bool:
        """Disable an automation."""
        return self.set_lifecycle(automation_id, AutomationLifecycle.DISABLED)

    # ── Template Management ───────────────────────────────────

    def add_template(self, template: AutomationTemplate) -> AutomationTemplate:
        """Register a new automation template."""
        self._templates[template.id] = template
        logger.info(f"Automation template registered: {template.id} ({template.name})")
        return template

    def get_template(self, template_id: str) -> AutomationTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> list[AutomationTemplate]:
        """List all registered templates."""
        return list(self._templates.values())

    def create_from_template(
        self,
        template_id: str,
        name: str,
        parameter_overrides: dict[str, Any] | None = None,
        trigger_overrides: dict[str, Any] | None = None,
    ) -> AutomationDefinition | None:
        """Create a new automation from a template with optional overrides."""
        template = self._templates.get(template_id)
        if not template:
            logger.warning(f"Template not found: {template_id}")
            return None

        overrides = parameter_overrides or {}

        # Merge parameters from template defaults and overrides
        merged_config = dict(template.default_task_config)
        for key, value in overrides.items():
            if isinstance(value, dict) and key in merged_config and isinstance(merged_config[key], dict):
                merged_config[key] = {**merged_config[key], **value}
            else:
                merged_config[key] = value

        # Build trigger, applying overrides if provided
        trigger = AutomationTrigger(
            trigger_type=template.trigger.trigger_type,
            cron_expression=template.trigger.cron_expression,
            interval_seconds=template.trigger.interval_seconds,
            webhook_token=template.trigger.webhook_token,
            timezone=template.trigger.timezone,
        )
        if trigger_overrides:
            for key, value in trigger_overrides.items():
                if hasattr(trigger, key):
                    setattr(trigger, key, value)

        automation = AutomationDefinition(
            name=name,
            description=template.description,
            automation_type=template.automation_type,
            trigger=trigger,
            retry_policy=RetryPolicy(
                max_attempts=template.retry_policy.max_attempts,
                backoff_strategy=template.retry_policy.backoff_strategy,
                base_delay_seconds=template.retry_policy.base_delay_seconds,
                max_delay_seconds=template.retry_policy.max_delay_seconds,
            ),
            task_config=merged_config,
            template_id=template_id,
            tags=list(template.tags),
        )

        self.add_automation(automation)
        logger.info(f"Automation created from template '{template.name}': {automation.id}")
        return automation

    # ── Execution History ─────────────────────────────────────

    def record_execution(self, result: ExecutionResult) -> None:
        """Record an execution result in the history."""
        history = self._execution_history.setdefault(result.automation_id, [])
        history.append(result)
        if len(history) > 200:
            self._execution_history[result.automation_id] = history[-200:]

        # Update automation counters
        automation = self._automations.get(result.automation_id)
        if automation:
            automation.execution_count += 1
            automation.last_executed_at = result.finished_at or result.started_at
            if result.status == ExecutionStatus.COMPLETED:
                automation.success_count += 1
            elif result.status == ExecutionStatus.FAILED:
                automation.fail_count += 1
            # Update rolling average duration
            if automation.avg_duration_ms == 0.0:
                automation.avg_duration_ms = result.duration_ms
            else:
                automation.avg_duration_ms = (
                    automation.avg_duration_ms * 0.9 + result.duration_ms * 0.1
                )

    def get_execution_history(
        self, automation_id: str, limit: int = 50
    ) -> list[ExecutionResult]:
        """Get execution history for an automation."""
        history = self._execution_history.get(automation_id, [])
        return history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get registry-level statistics."""
        automations = list(self._automations.values())
        total = len(automations)
        lifecycle_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for a in automations:
            lifecycle_counts[a.lifecycle.value] = lifecycle_counts.get(a.lifecycle.value, 0) + 1
            type_counts[a.automation_type.value] = type_counts.get(a.automation_type.value, 0) + 1

        return {
            "total_automations": total,
            "total_templates": len(self._templates),
            "by_lifecycle": lifecycle_counts,
            "by_type": type_counts,
            "active_count": lifecycle_counts.get("active", 0),
            "total_executions": sum(a.execution_count for a in automations),
            "total_failures": sum(a.fail_count for a in automations),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Cron Scheduler
# ═══════════════════════════════════════════════════════════════════════════

class CronScheduler:
    """Cron-based scheduling system with expression parsing and timezone support.

    Parses standard cron expressions (minute, hour, day, month, weekday),
    computes next run times, provides human-readable descriptions, and detects
    scheduling conflicts between automations.
    """

    _FIELD_NAMES = ["minute", "hour", "day", "month", "weekday"]
    _FIELD_RANGES = {
        "minute": (0, 59),
        "hour": (0, 23),
        "day": (1, 31),
        "month": (1, 12),
        "weekday": (0, 6),  # 0 = Sunday
    }
    _MONTH_NAMES = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    _WEEKDAY_NAMES = [
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    ]

    def __init__(self):
        self._schedules: dict[str, str] = {}  # automation_id -> cron_expression

    def register(self, automation_id: str, cron_expression: str) -> None:
        """Register a cron expression for an automation."""
        if self._validate_expression(cron_expression):
            self._schedules[automation_id] = cron_expression
            logger.info(f"Cron schedule registered for {automation_id}: {cron_expression}")
        else:
            raise ValueError(f"Invalid cron expression: {cron_expression}")

    def unregister(self, automation_id: str) -> None:
        """Remove a registered cron schedule."""
        self._schedules.pop(automation_id, None)

    # ── Expression Validation ─────────────────────────────────

    def _validate_expression(self, expression: str) -> bool:
        """Validate a standard 5-field cron expression."""
        fields = expression.strip().split()
        if len(fields) != 5:
            return False
        for i, field in enumerate(fields):
            field_name = self._FIELD_NAMES[i]
            low, high = self._FIELD_RANGES[field_name]
            try:
                self._parse_field(field, field_name, low, high)
            except ValueError:
                return False
        return True

    @classmethod
    def _parse_field(cls, field: str, field_name: str, low: int, high: int) -> set[int]:
        """Parse a single cron field into a set of matching values."""
        values: set[int] = set()

        if field == "*":
            return set(range(low, high + 1))

        parts = field.split(",")
        for part in parts:
            part = part.strip()

            # Step values: */5 or 1-10/2
            if "/" in part:
                range_part, step_str = part.split("/", 1)
                step = int(step_str)
                if step <= 0:
                    raise ValueError(f"Invalid step value: {step}")
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
            v = int(part)
            if low <= v <= high:
                values.add(v)

        return values

    # ── Matching and Next Run ─────────────────────────────────

    def matches(self, expression: str, dt: datetime) -> bool:
        """Check if a cron expression matches a given datetime."""
        fields = expression.strip().split()
        if len(fields) != 5:
            return False

        checks = [
            (fields[0], "minute", dt.minute),
            (fields[1], "hour", dt.hour),
            (fields[2], "day", dt.day),
            (fields[3], "month", dt.month),
            (fields[4], "weekday", (dt.weekday() + 1) % 7),
        ]

        for field_expr, field_name, current_val in checks:
            low, high = self._FIELD_RANGES[field_name]
            allowed = self._parse_field(field_expr, field_name, low, high)
            if current_val not in allowed:
                return False

        return True

    def get_next_run(
        self, expression: str, from_time: datetime | None = None, tz: str = "UTC"
    ) -> datetime | None:
        """Calculate the next run time for a cron expression.

        Scans forward minute by minute from the given time until a match is
        found. Returns None if no match is found within a reasonable window.
        """
        if not self._validate_expression(expression):
            return None

        current = from_time or datetime.now(timezone.utc)
        # Start from the next minute
        current = current.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search up to 2 years ahead
        max_iterations = 365 * 24 * 60 * 2
        for _ in range(max_iterations):
            if self.matches(expression, current):
                return current
            current += timedelta(minutes=1)

        return None

    def get_next_runs(
        self, expression: str, count: int = 5, from_time: datetime | None = None
    ) -> list[datetime]:
        """Get the next N run times for a cron expression."""
        runs: list[datetime] = []
        current = from_time or datetime.now(timezone.utc)
        for _ in range(count):
            next_run = self.get_next_run(expression, current)
            if next_run is None:
                break
            runs.append(next_run)
            current = next_run
        return runs

    # ── Human-Readable Descriptions ───────────────────────────

    def describe(self, expression: str) -> str:
        """Generate a human-readable description of a cron expression."""
        if not self._validate_expression(expression):
            return "Invalid expression"

        fields = expression.strip().split()
        parts: list[str] = []

        # Minute
        if fields[0] == "*":
            parts.append("every minute")
        elif fields[0].startswith("*/"):
            step = fields[0].split("/")[1]
            parts.append(f"every {step} minutes")
        else:
            parts.append(f"at minute {fields[0]}")

        # Hour
        if fields[1] == "*":
            if parts[-1] == "every minute":
                parts[-1] = "every minute of every hour"
            else:
                parts.append("of every hour")
        elif fields[1].startswith("*/"):
            step = fields[1].split("/")[1]
            parts.append(f"every {step} hours")
        else:
            if "every minute" in parts[-1]:
                parts[-1] = f"every minute past hour {fields[1]}"
            else:
                parts.append(f"past hour {fields[1]}")

        # Day
        if fields[2] == "*":
            parts.append("every day")
        elif fields[2] != "*":
            parts.append(f"on day {fields[2]}")

        # Month
        if fields[3] != "*":
            try:
                month_idx = int(fields[3])
                if 1 <= month_idx <= 12:
                    parts.append(f"in {self._MONTH_NAMES[month_idx]}")
            except ValueError:
                parts.append(f"in month {fields[3]}")

        # Weekday
        if fields[4] != "*":
            try:
                weekday_idx = int(fields[4])
                if 0 <= weekday_idx <= 6:
                    parts.append(f"on {self._WEEKDAY_NAMES[weekday_idx]}")
            except ValueError:
                parts.append(f"on weekday {fields[4]}")

        if not parts:
            parts.append("every minute")

        return " ".join(parts)

    # ── Conflict Detection ─────────────────────────────────────

    def detect_conflicts(self, tolerance_minutes: int = 1) -> list[dict[str, Any]]:
        """Detect scheduling conflicts between registered automations.

        Two automations conflict if they are scheduled to run within the
        tolerance window of each other.
        """
        conflicts: list[dict[str, Any]] = []
        ids = list(self._schedules.keys())

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                id_a, id_b = ids[i], ids[j]
                expr_a = self._schedules[id_a]
                expr_b = self._schedules[id_b]

                next_a = self.get_next_run(expr_a)
                next_b = self.get_next_run(expr_b)

                if next_a and next_b:
                    diff = abs((next_a - next_b).total_seconds())
                    if diff <= tolerance_minutes * 60:
                        conflicts.append({
                            "automation_a": id_a,
                            "automation_b": id_b,
                            "next_run_a": next_a.isoformat(),
                            "next_run_b": next_b.isoformat(),
                            "difference_seconds": diff,
                            "expression_a": expr_a,
                            "expression_b": expr_b,
                        })

        if conflicts:
            logger.warning(f"Detected {len(conflicts)} scheduling conflicts")
        return conflicts

    def get_schedule(self, automation_id: str) -> str | None:
        """Get the cron expression for an automation."""
        return self._schedules.get(automation_id)

    def list_schedules(self) -> dict[str, str]:
        """List all registered cron schedules."""
        return dict(self._schedules)


# ═══════════════════════════════════════════════════════════════════════════
# Automation Runner
# ═══════════════════════════════════════════════════════════════════════════

class AutomationRunner:
    """Executes automation tasks with timeout, retry, and parallel execution support.

    Manages the execution lifecycle of automation tasks, applying retry
    policies with configurable backoff strategies, capturing results, and
    maintaining execution context through variables and environment.
    """

    _MAX_PARALLEL = 10

    def __init__(self):
        self._executor: Callable[[AutomationDefinition, ExecutionContext], Awaitable[Any]] | None = None
        self._registry: AutomationRegistry | None = None
        self._running_executions: set[str] = set()
        self._execution_lock = asyncio.Lock()
        self._parallel_semaphore = asyncio.Semaphore(self._MAX_PARALLEL)

    def wire(
        self,
        executor: Callable[[AutomationDefinition, ExecutionContext], Awaitable[Any]],
        registry: AutomationRegistry,
    ) -> None:
        """Wire the executor function and registry for execution."""
        self._executor = executor
        self._registry = registry
        logger.info("AutomationRunner wired with executor and registry")

    async def execute(
        self,
        automation: AutomationDefinition,
        context: ExecutionContext | None = None,
        timeout_seconds: float = 300.0,
    ) -> ExecutionResult:
        """Execute a single automation with retry support.

        Runs the automation task, applying the retry policy on failure.
        Captures the result, duration, and any error information.
        """
        ctx = context or ExecutionContext()
        result = ExecutionResult(
            automation_id=automation.id,
            context=ctx,
        )

        self._running_executions.add(automation.id)
        result.status = ExecutionStatus.RUNNING
        started = time.time()

        try:
            for attempt in range(1, automation.retry_policy.max_attempts + 1):
                result.attempt = attempt
                try:
                    if self._executor:
                        output = await asyncio.wait_for(
                            self._executor(automation, ctx),
                            timeout=timeout_seconds,
                        )
                        result.output = output
                        result.status = ExecutionStatus.COMPLETED
                    else:
                        result.status = ExecutionStatus.COMPLETED
                        result.output = {"message": "No executor configured"}
                    break
                except asyncio.TimeoutError:
                    result.error = f"Execution timed out after {timeout_seconds}s"
                    result.error_type = "TimeoutError"
                    result.status = ExecutionStatus.TIMED_OUT
                    if attempt < automation.retry_policy.max_attempts:
                        delay = automation.retry_policy.compute_delay(attempt)
                        logger.warning(
                            f"Automation {automation.id} timed out, "
                            f"retrying in {delay:.1f}s (attempt {attempt}/{automation.retry_policy.max_attempts})"
                        )
                        await asyncio.sleep(delay)
                    else:
                        result.status = ExecutionStatus.FAILED
                except Exception as e:
                    error_type = type(e).__name__
                    result.error = str(e)
                    result.error_type = error_type
                    result.status = ExecutionStatus.FAILED
                    # Check if this error is retryable
                    if attempt < automation.retry_policy.max_attempts:
                        retryable = (
                            error_type in automation.retry_policy.retry_on_errors
                            or any(
                                err_type in error_type
                                for err_type in automation.retry_policy.retry_on_errors
                            )
                        )
                        if retryable:
                            delay = automation.retry_policy.compute_delay(attempt)
                            logger.warning(
                                f"Automation {automation.id} failed with {error_type}, "
                                f"retrying in {delay:.1f}s (attempt {attempt}/{automation.retry_policy.max_attempts})"
                            )
                            await asyncio.sleep(delay)
                            continue
                    break

        except asyncio.CancelledError:
            result.status = ExecutionStatus.CANCELLED
            result.error = "Execution cancelled"
        finally:
            result.finished_at = datetime.now(timezone.utc).isoformat()
            result.duration_ms = (time.time() - started) * 1000
            self._running_executions.discard(automation.id)

            if self._registry:
                self._registry.record_execution(result)

        return result

    async def execute_parallel(
        self,
        automations: list[AutomationDefinition],
        context: ExecutionContext | None = None,
        timeout_seconds: float = 300.0,
    ) -> list[ExecutionResult]:
        """Execute multiple automations in parallel with a semaphore limit.

        Runs all provided automations concurrently, bounded by the maximum
        parallel execution limit. Results are returned in the same order
        as the input automations.
        """
        ctx = context or ExecutionContext()

        async def _run_with_semaphore(auto: AutomationDefinition) -> ExecutionResult:
            async with self._parallel_semaphore:
                return await self.execute(auto, ctx, timeout_seconds)

        tasks = [_run_with_semaphore(a) for a in automations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results: list[ExecutionResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                fallback = ExecutionResult(
                    automation_id=automations[i].id,
                    status=ExecutionStatus.FAILED,
                    error=str(result),
                    error_type=type(result).__name__,
                )
                fallback.finished_at = datetime.now(timezone.utc).isoformat()
                final_results.append(fallback)
            else:
                final_results.append(result)

        return final_results

    def is_running(self, automation_id: str) -> bool:
        """Check if an automation is currently executing."""
        return automation_id in self._running_executions

    def get_running_count(self) -> int:
        """Get the number of currently running executions."""
        return len(self._running_executions)

    def get_running_ids(self) -> list[str]:
        """Get the IDs of currently running automations."""
        return list(self._running_executions)


# ═══════════════════════════════════════════════════════════════════════════
# Event Watcher
# ═══════════════════════════════════════════════════════════════════════════

class EventWatcher:
    """Watches for events and triggers matching automations.

    Captures events of various types, applies filters to match them to
    automations, supports deduplication via fingerprinting, and manages
    event chains where one automation's completion triggers another.
    """

    _MAX_EVENT_HISTORY = 1000
    _DEDUP_WINDOW_SECONDS = 30

    def __init__(self):
        self._event_history: list[WatchedEvent] = []
        self._event_handlers: dict[EventType, list[Callable[[WatchedEvent], Awaitable[None]]]] = {}
        self._automation_filters: dict[str, EventFilter] = {}  # automation_id -> filter
        self._fingerprint_cache: dict[str, float] = {}  # fingerprint -> timestamp
        self._event_chains: dict[str, list[EventChain]] = {}
        self._dedup_enabled: bool = True
        self._debounce_seconds: float = 5.0

    # ── Event Ingestion ───────────────────────────────────────

    async def emit(
        self,
        event_type: EventType,
        source: str,
        payload: Any = None,
        correlation_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WatchedEvent:
        """Emit a new event and trigger matching automations."""
        event = WatchedEvent(
            event_type=event_type,
            source=source,
            payload=payload,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )

        # Deduplication check
        if self._dedup_enabled and self._is_duplicate(event):
            logger.debug(f"Duplicate event suppressed: {event.fingerprint()}")
            return event

        self._fingerprint_cache[event.fingerprint()] = time.time()

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._MAX_EVENT_HISTORY:
            self._event_history = self._event_history[-self._MAX_EVENT_HISTORY:]

        logger.debug(f"Event emitted: {event_type.value} from {source}")

        # Notify registered handlers
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event_type.value}: {e}")

        return event

    def _is_duplicate(self, event: WatchedEvent) -> bool:
        """Check if an event is a duplicate within the dedup window."""
        fingerprint = event.fingerprint()
        last_seen = self._fingerprint_cache.get(fingerprint)
        if last_seen and (time.time() - last_seen) < self._DEDUP_WINDOW_SECONDS:
            return True
        # Cleanup old fingerprints
        now = time.time()
        expired = [
            fp for fp, ts in self._fingerprint_cache.items()
            if now - ts > self._DEDUP_WINDOW_SECONDS * 2
        ]
        for fp in expired:
            del self._fingerprint_cache[fp]
        return False

    # ── Handler Registration ──────────────────────────────────

    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[WatchedEvent], Awaitable[None]],
    ) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        logger.debug(f"Handler registered for event type: {event_type.value}")

    def unregister_handler(
        self,
        event_type: EventType,
        handler: Callable[[WatchedEvent], Awaitable[None]],
    ) -> None:
        """Remove a handler for a specific event type."""
        handlers = self._event_handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    # ── Event Filtering ───────────────────────────────────────

    def set_automation_filter(
        self, automation_id: str, event_filter: EventFilter
    ) -> None:
        """Set the event filter for an automation."""
        self._automation_filters[automation_id] = event_filter

    def remove_automation_filter(self, automation_id: str) -> None:
        """Remove the event filter for an automation."""
        self._automation_filters.pop(automation_id, None)

    def matches_filter(self, event: WatchedEvent, event_filter: EventFilter) -> bool:
        """Check if an event matches a given filter."""
        # Check event type
        if event_filter.event_types and event.event_type not in event_filter.event_types:
            return False

        # Check source pattern (simple glob-style)
        if event_filter.source_pattern:
            if not self._match_pattern(event.source, event_filter.source_pattern):
                return False

        # Check correlation ID
        if event_filter.correlation_id and event.correlation_id != event_filter.correlation_id:
            return False

        # Check payload key/value
        if event_filter.payload_key:
            payload_value = self._get_payload_value(event.payload, event_filter.payload_key)
            if payload_value != event_filter.payload_value:
                return False

        # Check metadata filters
        for key, expected in event_filter.metadata_filters.items():
            if event.metadata.get(key) != expected:
                return False

        return True

    def find_matching_automations(self, event: WatchedEvent) -> list[str]:
        """Find all automations whose filters match the given event."""
        matching: list[str] = []
        for automation_id, event_filter in self._automation_filters.items():
            if self.matches_filter(event, event_filter):
                matching.append(automation_id)
        return matching

    @staticmethod
    def _match_pattern(value: str, pattern: str) -> bool:
        """Simple pattern matching with * wildcard support."""
        if pattern == "*":
            return True
        if "*" not in pattern:
            return value == pattern
        regex = re.escape(pattern).replace(r"\*", ".*")
        return bool(re.match(f"^{regex}$", value))

    @staticmethod
    def _get_payload_value(payload: Any, key: str) -> Any:
        """Extract a value from the payload by key."""
        if isinstance(payload, dict):
            return payload.get(key)
        if hasattr(payload, key):
            return getattr(payload, key)
        return None

    # ── Event Chains ──────────────────────────────────────────

    def add_event_chain(self, chain: EventChain) -> None:
        """Add an event chain linking two automations."""
        chains = self._event_chains.setdefault(chain.source_automation_id, [])
        chains.append(chain)
        logger.info(
            f"Event chain added: {chain.source_automation_id} "
            f"-[{chain.source_event.value}]-> {chain.target_automation_id}"
        )

    def remove_event_chain(self, chain_id: str) -> bool:
        """Remove an event chain by ID."""
        for auto_id, chains in self._event_chains.items():
            for chain in chains:
                if chain.id == chain_id:
                    chains.remove(chain)
                    return True
        return False

    def get_chains_for_source(self, source_automation_id: str) -> list[EventChain]:
        """Get all event chains originating from a given automation."""
        return list(self._event_chains.get(source_automation_id, []))

    def get_chains_for_target(self, target_automation_id: str) -> list[EventChain]:
        """Get all event chains targeting a given automation."""
        result: list[EventChain] = []
        for chains in self._event_chains.values():
            for chain in chains:
                if chain.target_automation_id == target_automation_id:
                    result.append(chain)
        return result

    def get_all_chains(self) -> dict[str, list[EventChain]]:
        """Get all event chains."""
        return dict(self._event_chains)

    # ── History & Stats ───────────────────────────────────────

    def get_event_history(
        self,
        event_type: EventType | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get recent events with optional type filtering."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "source": e.source,
                "timestamp": e.timestamp,
                "correlation_id": e.correlation_id,
            }
            for e in events[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get event watcher statistics."""
        type_counts: dict[str, int] = {}
        for e in self._event_history:
            type_counts[e.event_type.value] = type_counts.get(e.event_type.value, 0) + 1

        return {
            "total_events": len(self._event_history),
            "by_type": type_counts,
            "registered_handlers": sum(len(h) for h in self._event_handlers.values()),
            "active_filters": len(self._automation_filters),
            "event_chains": sum(len(c) for c in self._event_chains.values()),
            "dedup_enabled": self._dedup_enabled,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Automation Analytics
# ═══════════════════════════════════════════════════════════════════════════

class AutomationAnalytics:
    """Analyzes automation execution performance and provides optimization suggestions.

    Tracks execution history to compute success rates, average durations,
    failure patterns, and generates actionable recommendations for improving
    automation reliability and performance.
    """

    _HISTORY_RETENTION = 500
    _ANALYSIS_WINDOW_DAYS = 30

    def __init__(self):
        self._execution_records: dict[str, list[ExecutionResult]] = {}
        self._failure_records: list[FailureRecord] = []

    def feed(self, result: ExecutionResult, automation_name: str = "") -> None:
        """Feed an execution result into the analytics engine."""
        history = self._execution_records.setdefault(result.automation_id, [])
        history.append(result)
        if len(history) > self._HISTORY_RETENTION:
            self._execution_records[result.automation_id] = history[-self._HISTORY_RETENTION:]

        # Track failures
        if result.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT):
            self._failure_records.append(FailureRecord(
                execution_id=result.id,
                automation_id=result.automation_id,
                execution_name=automation_name,
                error_message=result.error,
                error_type=result.error_type,
                occurred_at=result.finished_at or result.started_at,
                attempt=result.attempt,
            ))
            if len(self._failure_records) > self._HISTORY_RETENTION:
                self._failure_records = self._failure_records[-self._HISTORY_RETENTION:]

    def get_success_rate(self, automation_id: str) -> dict[str, Any]:
        """Calculate the success rate for an automation."""
        history = self._execution_records.get(automation_id, [])
        total = len(history)
        if total == 0:
            return {"automation_id": automation_id, "total": 0, "success_rate": 0.0}

        completed = sum(1 for r in history if r.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for r in history if r.status == ExecutionStatus.FAILED)
        timed_out = sum(1 for r in history if r.status == ExecutionStatus.TIMED_OUT)
        cancelled = sum(1 for r in history if r.status == ExecutionStatus.CANCELLED)

        return {
            "automation_id": automation_id,
            "total": total,
            "completed": completed,
            "failed": failed,
            "timed_out": timed_out,
            "cancelled": cancelled,
            "success_rate": round(completed / total * 100, 2) if total > 0 else 0.0,
        }

    def get_average_duration(self, automation_id: str) -> dict[str, Any]:
        """Compute average duration statistics for an automation."""
        history = self._execution_records.get(automation_id, [])
        completed = [r for r in history if r.status == ExecutionStatus.COMPLETED]

        if not completed:
            return {
                "automation_id": automation_id,
                "sample_count": 0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": 0.0,
                "max_duration_ms": 0.0,
            }

        durations = [r.duration_ms for r in completed]
        return {
            "automation_id": automation_id,
            "sample_count": len(durations),
            "avg_duration_ms": round(sum(durations) / len(durations), 2),
            "min_duration_ms": round(min(durations), 2),
            "max_duration_ms": round(max(durations), 2),
            "p50_duration_ms": round(self._percentile(durations, 50), 2),
            "p95_duration_ms": round(self._percentile(durations, 95), 2),
            "p99_duration_ms": round(self._percentile(durations, 99), 2),
        }

    def get_failure_analysis(self, automation_id: str) -> dict[str, Any]:
        """Analyze failure patterns for an automation."""
        failures = [
            f for f in self._failure_records
            if f.automation_id == automation_id
        ]
        if not failures:
            return {"automation_id": automation_id, "total_failures": 0, "error_types": {}}

        error_type_counts: dict[str, int] = {}
        error_messages: dict[str, int] = {}
        for f in failures:
            error_type_counts[f.error_type] = error_type_counts.get(f.error_type, 0) + 1
            msg_key = f.error_message[:100] if f.error_message else "Unknown"
            error_messages[msg_key] = error_messages.get(msg_key, 0) + 1

        # Sort by frequency
        top_errors = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "automation_id": automation_id,
            "total_failures": len(failures),
            "error_types": error_type_counts,
            "top_error_messages": [{"message": msg, "count": cnt} for msg, cnt in top_errors],
            "avg_attempts_before_failure": round(
                sum(f.attempt for f in failures) / len(failures), 2
            ),
        }

    def get_optimization_suggestions(self, automation_id: str) -> list[dict[str, Any]]:
        """Generate optimization suggestions based on execution history.

        Analyzes patterns in execution data to produce actionable
        recommendations for improving reliability, reducing duration,
        and optimizing retry policies.
        """
        suggestions: list[dict[str, Any]] = []
        history = self._execution_records.get(automation_id, [])
        if not history:
            return suggestions

        success_rate = self.get_success_rate(automation_id)
        duration = self.get_average_duration(automation_id)
        failure_analysis = self.get_failure_analysis(automation_id)

        # Suggestion: Low success rate -> increase retries
        if success_rate["success_rate"] < 80 and success_rate["total"] >= 5:
            suggestions.append({
                "type": "reliability",
                "severity": "high",
                "description": (
                    f"Success rate is {success_rate['success_rate']}%. "
                    "Consider increasing max_attempts in the retry policy."
                ),
                "metric": "success_rate",
                "current_value": f"{success_rate['success_rate']}%",
                "threshold": "80%",
            })

        # Suggestion: High timeout rate
        if failure_analysis.get("error_types", {}).get("TimeoutError", 0) > 0:
            timeout_count = failure_analysis["error_types"]["TimeoutError"]
            timeout_rate = timeout_count / max(success_rate["total"], 1) * 100
            if timeout_rate > 20:
                suggestions.append({
                    "type": "performance",
                    "severity": "high",
                    "description": (
                        f"{timeout_rate:.0f}% of executions timeout. "
                        "Consider increasing the timeout or optimizing the task."
                    ),
                    "metric": "timeout_rate",
                    "current_value": f"{timeout_rate:.0f}%",
                    "threshold": "20%",
                })

        # Suggestion: High duration -> optimize task
        if duration["p95_duration_ms"] > 60000:  # 1 minute
            suggestions.append({
                "type": "performance",
                "severity": "medium",
                "description": (
                    f"P95 duration is {duration['p95_duration_ms']:.0f}ms. "
                    "Consider breaking the task into smaller steps."
                ),
                "metric": "p95_duration",
                "current_value": f"{duration['p95_duration_ms']:.0f}ms",
                "threshold": "60000ms",
            })

        # Suggestion: High failure rate despite retries -> retry policy may be insufficient
        if success_rate["total"] >= 10 and success_rate["failed"] >= 3:
            failure_rate = success_rate["failed"] / success_rate["total"] * 100
            if failure_rate > 30:
                suggestions.append({
                    "type": "reliability",
                    "severity": "medium",
                    "description": (
                        f"Failure rate is {failure_rate:.0f}% after retries. "
                        "Review the retry policy and consider adding a fallback mechanism."
                    ),
                    "metric": "failure_rate",
                    "current_value": f"{failure_rate:.0f}%",
                    "threshold": "30%",
                })

        # Suggestion: High variance -> inconsistent performance
        if duration["sample_count"] >= 10:
            history_durations = [r.duration_ms for r in history if r.duration_ms > 0]
            if len(history_durations) >= 5:
                avg = sum(history_durations) / len(history_durations)
                variance = sum((d - avg) ** 2 for d in history_durations) / len(history_durations)
                std_dev = variance ** 0.5
                if std_dev > avg:  # Standard deviation exceeds average
                    suggestions.append({
                        "type": "performance",
                        "severity": "low",
                        "description": (
                            "High execution time variance detected. "
                            "The task may depend on external resources with variable latency."
                        ),
                        "metric": "duration_variance",
                        "current_value": f"std_dev={std_dev:.0f}ms",
                        "threshold": f"avg={avg:.0f}ms",
                    })

        return suggestions

    def get_global_stats(self) -> dict[str, Any]:
        """Get global analytics across all automations."""
        all_records = [
            r for records in self._execution_records.values() for r in records
        ]
        total = len(all_records)
        if total == 0:
            return {"total_executions": 0}

        completed = sum(1 for r in all_records if r.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for r in all_records if r.status == ExecutionStatus.FAILED)
        timed_out = sum(1 for r in all_records if r.status == ExecutionStatus.TIMED_OUT)

        durations = [r.duration_ms for r in all_records if r.duration_ms > 0]
        avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

        return {
            "total_executions": total,
            "total_completed": completed,
            "total_failed": failed,
            "total_timed_out": timed_out,
            "global_success_rate": round(completed / total * 100, 2) if total > 0 else 0.0,
            "global_avg_duration_ms": avg_duration,
            "automations_tracked": len(self._execution_records),
            "total_failure_records": len(self._failure_records),
        }

    def get_all_suggestions(self) -> dict[str, list[dict[str, Any]]]:
        """Get optimization suggestions for all tracked automations."""
        return {
            auto_id: self.get_optimization_suggestions(auto_id)
            for auto_id in self._execution_records
        }

    def reset(self, automation_id: str | None = None) -> None:
        """Reset analytics data for a specific automation or all automations."""
        if automation_id:
            self._execution_records.pop(automation_id, None)
            self._failure_records = [
                f for f in self._failure_records
                if f.automation_id != automation_id
            ]
        else:
            self._execution_records.clear()
            self._failure_records.clear()

    @staticmethod
    def _percentile(data: list[float], percentile: float) -> float:
        """Compute the percentile of a sorted list of values."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[-1]
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


# ═══════════════════════════════════════════════════════════════════════════
# Automation Core Facade
# ═══════════════════════════════════════════════════════════════════════════

class AutomationCore:
    """Central facade for the automation system.

    Provides a unified interface to the registry, scheduler, runner,
    event watcher, and analytics components. Orchestrates the full
    automation lifecycle from definition to execution to analysis.

    Usage:
        core = AutomationCore()

        # Create from template
        core.registry.add_template(my_template)
        auto = core.registry.create_from_template("my_template", "Daily Report")

        # Schedule it
        core.scheduler.register(auto.id, "0 9 * * *")

        # Execute
        result = await core.runner.execute(auto)

        # Analyze
        suggestions = core.analytics.get_optimization_suggestions(auto.id)
    """

    def __init__(self):
        self.registry = AutomationRegistry()
        self.scheduler = CronScheduler()
        self.runner = AutomationRunner()
        self.watcher = EventWatcher()
        self.analytics = AutomationAnalytics()

    def wire_executor(
        self,
        executor: Callable[[AutomationDefinition, ExecutionContext], Awaitable[Any]],
    ) -> None:
        """Wire the executor function to the runner and analytics."""
        self.runner.wire(executor, self.registry)

    async def trigger_event(
        self,
        event_type: EventType,
        source: str,
        payload: Any = None,
        correlation_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> list[ExecutionResult]:
        """Emit an event and execute all matching automations.

        Emits the event through the watcher, finds matching automations
        via registered filters, and executes them through the runner.
        """
        event = await self.watcher.emit(
            event_type=event_type,
            source=source,
            payload=payload,
            correlation_id=correlation_id,
            metadata=metadata,
        )

        matching_ids = self.watcher.find_matching_automations(event)
        automations = []
        for auto_id in matching_ids:
            auto = self.registry.get_automation(auto_id)
            if auto and auto.lifecycle == AutomationLifecycle.ACTIVE:
                automations.append(auto)

        if not automations:
            return []

        context = ExecutionContext(
            triggered_by=source,
            triggered_by_event=event_type.value,
        )

        results = await self.runner.execute_parallel(automations, context)

        # Feed analytics
        for result in results:
            auto = self.registry.get_automation(result.automation_id)
            self.analytics.feed(result, automation_name=auto.name if auto else "")

        # Process event chains
        for result in results:
            if result.status == ExecutionStatus.COMPLETED:
                chains = self.watcher.get_chains_for_source(result.automation_id)
                for chain in chains:
                    if chain.enabled:
                        await self.watcher.emit(
                            event_type=chain.source_event,
                            source=result.automation_id,
                            payload=result.output,
                            correlation_id=chain.id,
                            metadata={"chain_id": chain.id, "target": chain.target_automation_id},
                        )

        return results

    async def execute_automation(
        self,
        automation_id: str,
        context: ExecutionContext | None = None,
        timeout_seconds: float = 300.0,
    ) -> ExecutionResult | None:
        """Execute a single automation by ID."""
        auto = self.registry.get_automation(automation_id)
        if not auto:
            logger.warning(f"Automation not found: {automation_id}")
            return None

        result = await self.runner.execute(auto, context, timeout_seconds)
        self.analytics.feed(result, automation_name=auto.name)
        return result

    async def execute_scheduled(self) -> list[ExecutionResult]:
        """Execute all active automations that are due to run.

        Checks each active scheduled automation against its cron
        expression and executes any that match the current time.
        """
        now = datetime.now(timezone.utc)
        active = self.registry.get_active_automations()
        due: list[AutomationDefinition] = []

        for auto in active:
            if auto.automation_type != AutomationType.SCHEDULED:
                continue
            if auto.trigger.trigger_type == TriggerType.CRON:
                expression = auto.trigger.cron_expression
                if expression and self.scheduler.matches(expression, now):
                    # Avoid re-executing within the same minute
                    if auto.last_executed_at:
                        last = datetime.fromisoformat(auto.last_executed_at)
                        if (now - last).total_seconds() < 60:
                            continue
                    due.append(auto)
            elif auto.trigger.trigger_type == TriggerType.INTERVAL:
                interval = auto.trigger.interval_seconds
                if interval > 0:
                    if not auto.last_executed_at:
                        due.append(auto)
                    else:
                        last = datetime.fromisoformat(auto.last_executed_at)
                        if (now - last).total_seconds() >= interval:
                            due.append(auto)

        if not due:
            return []

        results = await self.runner.execute_parallel(due)

        for result in results:
            auto = self.registry.get_automation(result.automation_id)
            self.analytics.feed(result, automation_name=auto.name if auto else "")

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics across all components."""
        registry_stats = self.registry.get_stats()
        event_stats = self.watcher.get_stats()
        analytics_stats = self.analytics.get_global_stats()

        return {
            "registry": registry_stats,
            "events": event_stats,
            "analytics": analytics_stats,
            "running_executions": self.runner.get_running_count(),
            "schedules_registered": len(self.scheduler.list_schedules()),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

automation_core = AutomationCore()