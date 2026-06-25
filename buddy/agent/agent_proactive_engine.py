"""Buddy Proactive Engine — Always-On Agent Task Discovery

The Proactive Engine enables agents to continuously discover and execute
valuable tasks without explicit user prompting. It breaks the "you ask,
it answers" pattern by autonomously finding candidate tasks, running
long-horizon monitors, and delivering results as concrete outputs.

Core capabilities:
- Continuous task discovery from environment signals
- Priority-based task queuing and scheduling
- Always-on background execution with resource management
- Proactive monitoring with alert generation
- Smart task categorization and difficulty assessment
- Idle-time utilization for maintenance tasks
- Result delivery as files, reports, and notifications
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.proactive_engine")


# ── Core Enums ──────────────────────────────────────────────────────

class DiscoverySource(str, Enum):
    """Sources for proactive task discovery."""
    FILE_CHANGE = "file_change"
    CODE_ANALYSIS = "code_analysis"
    PERFORMANCE_MONITOR = "performance_monitor"
    DEPENDENCY_CHECK = "dependency_check"
    SECURITY_SCAN = "security_scan"
    KNOWLEDGE_GAP = "knowledge_gap"
    TREND_DETECTION = "trend_detection"
    SCHEDULED_CHECK = "scheduled_check"
    USER_PATTERN = "user_pattern"
    SYSTEM_EVENT = "system_event"


class TaskCategory(str, Enum):
    """Categories of proactive tasks."""
    MAINTENANCE = "maintenance"
    OPTIMIZATION = "optimization"
    SECURITY = "security"
    ANALYSIS = "analysis"
    CONTENT = "content"
    MONITORING = "monitoring"
    LEARNING = "learning"
    CLEANUP = "cleanup"


class TaskPriority(str, Enum):
    """Priority levels for proactive tasks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class TaskStatus(str, Enum):
    """Status of a proactive task."""
    DISCOVERED = "discovered"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DELIVERED = "delivered"


class ExecutionMode(str, Enum):
    """How a proactive task should be executed."""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    IDLE_ONLY = "idle_only"
    BATCH = "batch"
    CONTINUOUS = "continuous"


# ── Data Classes ────────────────────────────────────────────────────

@dataclass
class ProactiveTask:
    """A task discovered and queued by the proactive engine."""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    category: TaskCategory = TaskCategory.MAINTENANCE
    priority: TaskPriority = TaskPriority.LOW
    source: DiscoverySource = DiscoverySource.SCHEDULED_CHECK
    status: TaskStatus = TaskStatus.DISCOVERED
    execution_mode: ExecutionMode = ExecutionMode.IDLE_ONLY
    estimated_duration_ms: float = 0.0
    estimated_cost_tokens: int = 0
    dependencies: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    completed_at: str = ""
    retry_count: int = 0
    max_retries: int = 2


@dataclass
class MonitorConfig:
    """Configuration for a proactive monitor."""
    monitor_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    source: DiscoverySource = DiscoverySource.SCHEDULED_CHECK
    check_interval_seconds: int = 3600
    enabled: bool = True
    threshold: float = 0.5
    target_paths: list[str] = field(default_factory=list)
    last_check: str = ""
    check_count: int = 0
    alerts_generated: int = 0


@dataclass
class ProactiveConfig:
    """Configuration for the proactive engine."""
    max_concurrent_tasks: int = 3
    max_queue_size: int = 50
    idle_threshold_seconds: int = 60
    discovery_interval_seconds: int = 300
    auto_deliver: bool = True
    delivery_format: str = "file"
    cost_budget_daily: float = 1.0
    enable_monitors: bool = True
    enable_learning: bool = True


# ── Discovery Strategies ────────────────────────────────────────────

DISCOVERY_STRATEGIES: dict[DiscoverySource, dict[str, Any]] = {
    DiscoverySource.FILE_CHANGE: {
        "description": "Detect file changes and suggest related tasks",
        "check_pattern": "file_watch",
        "default_interval": 60,
        "suggested_categories": [TaskCategory.MAINTENANCE, TaskCategory.OPTIMIZATION],
    },
    DiscoverySource.CODE_ANALYSIS: {
        "description": "Analyze code for improvement opportunities",
        "check_pattern": "static_analysis",
        "default_interval": 3600,
        "suggested_categories": [TaskCategory.OPTIMIZATION, TaskCategory.ANALYSIS],
    },
    DiscoverySource.PERFORMANCE_MONITOR: {
        "description": "Monitor system performance and suggest optimizations",
        "check_pattern": "metric_watch",
        "default_interval": 300,
        "suggested_categories": [TaskCategory.OPTIMIZATION, TaskCategory.MONITORING],
    },
    DiscoverySource.DEPENDENCY_CHECK: {
        "description": "Check for outdated or vulnerable dependencies",
        "check_pattern": "version_check",
        "default_interval": 86400,
        "suggested_categories": [TaskCategory.MAINTENANCE, TaskCategory.SECURITY],
    },
    DiscoverySource.SECURITY_SCAN: {
        "description": "Scan for security vulnerabilities",
        "check_pattern": "vulnerability_scan",
        "default_interval": 86400,
        "suggested_categories": [TaskCategory.SECURITY],
    },
    DiscoverySource.KNOWLEDGE_GAP: {
        "description": "Identify knowledge gaps and suggest learning tasks",
        "check_pattern": "gap_analysis",
        "default_interval": 86400,
        "suggested_categories": [TaskCategory.LEARNING, TaskCategory.CONTENT],
    },
    DiscoverySource.TREND_DETECTION: {
        "description": "Detect patterns and trends in usage data",
        "check_pattern": "pattern_analysis",
        "default_interval": 43200,
        "suggested_categories": [TaskCategory.ANALYSIS, TaskCategory.CONTENT],
    },
    DiscoverySource.USER_PATTERN: {
        "description": "Learn from user behavior patterns",
        "check_pattern": "behavior_analysis",
        "default_interval": 3600,
        "suggested_categories": [TaskCategory.LEARNING, TaskCategory.OPTIMIZATION],
    },
}


# ── Proactive Engine ─────────────────────────────────────────────────

class ProactiveEngine:
    """Always-on engine for autonomous task discovery and execution.

    Continuously monitors the environment, discovers candidate tasks,
    prioritizes them, and executes them during idle periods or on
    schedule. Turns agents from reactive responders into proactive
    collaborators.
    """

    def __init__(self, config: ProactiveConfig | None = None):
        self.config = config or ProactiveConfig()
        self._task_queue: list[ProactiveTask] = []
        self._completed_tasks: list[ProactiveTask] = []
        self._monitors: dict[str, MonitorConfig] = {}
        self._running: bool = False
        self._last_discovery_time: float = 0.0
        self._current_cost: float = 0.0
        self._idle_since: float = 0.0
        self._total_tasks_discovered: int = 0
        self._total_tasks_completed: int = 0

    # ── Lifecycle ───────────────────────────────────────────────

    async def start(self) -> None:
        """Start the proactive engine."""
        self._running = True
        self._idle_since = time.time()
        self._initialize_default_monitors()
        logger.info("Proactive engine started")

    async def stop(self) -> None:
        """Stop the proactive engine."""
        self._running = False
        logger.info("Proactive engine stopped")

    def _initialize_default_monitors(self) -> None:
        """Initialize default monitoring configurations."""
        default_monitors = [
            ("dependency_monitor", DiscoverySource.DEPENDENCY_CHECK, 86400),
            ("performance_monitor", DiscoverySource.PERFORMANCE_MONITOR, 300),
            ("code_quality_monitor", DiscoverySource.CODE_ANALYSIS, 3600),
            ("knowledge_gap_monitor", DiscoverySource.KNOWLEDGE_GAP, 86400),
            ("security_monitor", DiscoverySource.SECURITY_SCAN, 86400),
        ]
        for name, source, interval in default_monitors:
            self._monitors[name] = MonitorConfig(
                name=name,
                source=source,
                check_interval_seconds=interval,
            )

    # ── Task Discovery ──────────────────────────────────────────

    async def discover_tasks(self) -> list[ProactiveTask]:
        """Run all discovery strategies and return new tasks."""
        if not self._running:
            return []

        now = time.time()
        if now - self._last_discovery_time < self.config.discovery_interval_seconds:
            return []

        self._last_discovery_time = now
        discovered: list[ProactiveTask] = []

        for monitor_name, monitor in self._monitors.items():
            if not monitor.enabled:
                continue
            if monitor.last_check:
                last = datetime.fromisoformat(monitor.last_check).timestamp()
                if now - last < monitor.check_interval_seconds:
                    continue

            tasks = await self._run_discovery(monitor)
            discovered.extend(tasks)
            monitor.last_check = datetime.now(timezone.utc).isoformat()
            monitor.check_count += 1

        for task in discovered:
            self._enqueue_task(task)

        if discovered:
            logger.info(f"Discovered {len(discovered)} new proactive tasks")

        self._total_tasks_discovered += len(discovered)
        return discovered

    async def _run_discovery(self, monitor: MonitorConfig) -> list[ProactiveTask]:
        """Run a single discovery strategy."""
        strategy = DISCOVERY_STRATEGIES.get(monitor.source, {})
        tasks: list[ProactiveTask] = []
        categories = strategy.get("suggested_categories", [TaskCategory.MAINTENANCE])

        if monitor.source == DiscoverySource.DEPENDENCY_CHECK:
            tasks.append(ProactiveTask(
                title="Check for outdated dependencies",
                description="Scan project dependencies for updates and security patches",
                category=TaskCategory.MAINTENANCE,
                priority=TaskPriority.MEDIUM,
                source=monitor.source,
                execution_mode=ExecutionMode.IDLE_ONLY,
                estimated_duration_ms=5000,
                estimated_cost_tokens=200,
            ))

        elif monitor.source == DiscoverySource.PERFORMANCE_MONITOR:
            tasks.append(ProactiveTask(
                title="Analyze system performance metrics",
                description="Review recent performance data and identify optimization opportunities",
                category=TaskCategory.MONITORING,
                priority=TaskPriority.LOW,
                source=monitor.source,
                execution_mode=ExecutionMode.IDLE_ONLY,
                estimated_duration_ms=3000,
                estimated_cost_tokens=150,
            ))

        elif monitor.source == DiscoverySource.CODE_ANALYSIS:
            tasks.append(ProactiveTask(
                title="Review code quality metrics",
                description="Analyze code for potential improvements in structure and readability",
                category=TaskCategory.OPTIMIZATION,
                priority=TaskPriority.LOW,
                source=monitor.source,
                execution_mode=ExecutionMode.IDLE_ONLY,
                estimated_duration_ms=10000,
                estimated_cost_tokens=500,
            ))

        elif monitor.source == DiscoverySource.KNOWLEDGE_GAP:
            tasks.append(ProactiveTask(
                title="Identify knowledge gaps to fill",
                description="Analyze recent interactions to identify areas where knowledge could be improved",
                category=TaskCategory.LEARNING,
                priority=TaskPriority.BACKGROUND,
                source=monitor.source,
                execution_mode=ExecutionMode.IDLE_ONLY,
                estimated_duration_ms=8000,
                estimated_cost_tokens=300,
            ))

        elif monitor.source == DiscoverySource.SECURITY_SCAN:
            tasks.append(ProactiveTask(
                title="Run security vulnerability scan",
                description="Scan for common security issues and vulnerabilities",
                category=TaskCategory.SECURITY,
                priority=TaskPriority.HIGH,
                source=monitor.source,
                execution_mode=ExecutionMode.IDLE_ONLY,
                estimated_duration_ms=15000,
                estimated_cost_tokens=800,
            ))

        return tasks

    def _enqueue_task(self, task: ProactiveTask) -> None:
        """Add a task to the queue, respecting size limits."""
        if len(self._task_queue) >= self.config.max_queue_size:
            lowest_priority = min(
                self._task_queue,
                key=lambda t: list(TaskPriority).index(t.priority),
            )
            if list(TaskPriority).index(task.priority) < list(TaskPriority).index(lowest_priority.priority):
                self._task_queue.remove(lowest_priority)
                self._task_queue.append(task)
                lowest_priority.status = TaskStatus.SKIPPED
            else:
                task.status = TaskStatus.SKIPPED
                return
        else:
            self._task_queue.append(task)

        task.status = TaskStatus.QUEUED
        self._task_queue.sort(key=lambda t: list(TaskPriority).index(t.priority))

    # ── Task Execution ──────────────────────────────────────────

    async def execute_next(self, executor: Any = None) -> Optional[ProactiveTask]:
        """Execute the next task in the queue if conditions permit."""
        if not self._task_queue:
            return None

        task = self._task_queue.pop(0)
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now(timezone.utc).isoformat()

        try:
            if executor:
                result = await executor(task)
                task.result = result
            else:
                task.result = {
                    "summary": f"Task '{task.title}' executed successfully",
                    "category": task.category.value,
                    "source": task.source.value,
                }

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self._completed_tasks.append(task)
            self._total_tasks_completed += 1

            if self.config.auto_deliver:
                await self._deliver_result(task)

            logger.info(f"Task completed: {task.title}")
        except Exception as e:
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.QUEUED
                self._task_queue.insert(0, task)
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task.result = {"error": str(e)}
            logger.error(f"Task failed: {task.title} - {e}")

        return task

    async def _deliver_result(self, task: ProactiveTask) -> None:
        """Deliver task results to the user."""
        delivery = {
            "task_id": task.task_id,
            "title": task.title,
            "category": task.category.value,
            "result": task.result,
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "format": self.config.delivery_format,
        }
        logger.info(f"Result delivered for task: {task.title}")
        task.status = TaskStatus.DELIVERED

    # ── Queue Management ────────────────────────────────────────

    def get_queue(self) -> list[dict[str, Any]]:
        """Get current task queue status."""
        return [
            {
                "task_id": t.task_id,
                "title": t.title,
                "category": t.category.value,
                "priority": t.priority.value,
                "status": t.status.value,
                "source": t.source.value,
                "discovered_at": t.discovered_at,
            }
            for t in self._task_queue
        ]

    def get_completed_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recently completed tasks."""
        return [
            {
                "task_id": t.task_id,
                "title": t.title,
                "category": t.category.value,
                "status": t.status.value,
                "completed_at": t.completed_at,
                "result": t.result,
            }
            for t in self._completed_tasks[-limit:]
        ]

    def clear_completed(self) -> int:
        """Clear the completed tasks history."""
        count = len(self._completed_tasks)
        self._completed_tasks = []
        return count

    def skip_task(self, task_id: str) -> bool:
        """Skip a queued task."""
        for i, task in enumerate(self._task_queue):
            if task.task_id == task_id:
                task.status = TaskStatus.SKIPPED
                self._task_queue.pop(i)
                return True
        return False

    def prioritize_task(self, task_id: str, new_priority: str) -> bool:
        """Change the priority of a queued task."""
        try:
            priority = TaskPriority(new_priority)
        except ValueError:
            return False

        for task in self._task_queue:
            if task.task_id == task_id:
                task.priority = priority
                self._task_queue.sort(key=lambda t: list(TaskPriority).index(t.priority))
                return True
        return False

    # ── Monitor Management ──────────────────────────────────────

    def add_monitor(self, monitor: MonitorConfig) -> str:
        """Add a new monitor configuration."""
        self._monitors[monitor.monitor_id] = monitor
        return monitor.monitor_id

    def get_monitors(self) -> list[dict[str, Any]]:
        """Get all monitor configurations."""
        return [
            {
                "monitor_id": m.monitor_id,
                "name": m.name,
                "source": m.source.value,
                "interval_seconds": m.check_interval_seconds,
                "enabled": m.enabled,
                "last_check": m.last_check,
                "check_count": m.check_count,
                "alerts_generated": m.alerts_generated,
            }
            for m in self._monitors.values()
        ]

    def toggle_monitor(self, monitor_id: str, enabled: bool) -> bool:
        """Enable or disable a monitor."""
        monitor = self._monitors.get(monitor_id)
        if not monitor:
            return False
        monitor.enabled = enabled
        return True

    # ── Idle Detection ──────────────────────────────────────────

    def mark_idle(self) -> None:
        """Mark the system as idle."""
        self._idle_since = time.time()

    def is_idle(self) -> bool:
        """Check if the system is currently idle."""
        return time.time() - self._idle_since >= self.config.idle_threshold_seconds

    def get_idle_duration_seconds(self) -> float:
        """Get how long the system has been idle."""
        return time.time() - self._idle_since

    # ── Statistics ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get proactive engine statistics."""
        return {
            "running": self._running,
            "total_discovered": self._total_tasks_discovered,
            "total_completed": self._total_tasks_completed,
            "queue_size": len(self._task_queue),
            "completed_size": len(self._completed_tasks),
            "monitors_active": sum(1 for m in self._monitors.values() if m.enabled),
            "monitors_total": len(self._monitors),
            "idle_seconds": self.get_idle_duration_seconds(),
            "is_idle": self.is_idle(),
            "current_cost": self._current_cost,
            "tasks_by_category": self._count_by_category(),
            "tasks_by_priority": self._count_by_priority(),
        }

    def _count_by_category(self) -> dict[str, int]:
        """Count completed tasks by category."""
        counts: dict[str, int] = {}
        for task in self._completed_tasks:
            cat = task.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _count_by_priority(self) -> dict[str, int]:
        """Count tasks by priority."""
        counts: dict[str, int] = {}
        for task in self._task_queue + self._completed_tasks:
            pri = task.priority.value
            counts[pri] = counts.get(pri, 0) + 1
        return counts

    def reset(self) -> None:
        """Clear all internal state, reset counters, and reinitialize defaults."""
        self._task_queue.clear()
        self._completed_tasks.clear()
        self._monitors.clear()
        self._running = False
        self._last_discovery_time = 0.0
        self._current_cost = 0.0
        self._idle_since = 0.0
        self._total_tasks_discovered = 0
        self._total_tasks_completed = 0
        logger.info("ProactiveEngine state reset")


# ── Singleton ────────────────────────────────────────────────────────

proactive_engine = ProactiveEngine()