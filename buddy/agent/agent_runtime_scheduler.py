"""Buddy Agent Runtime Scheduler — priority-based scheduling with dependency graphs and resource management.

Provides a unified scheduling layer that coordinates task execution across agents
with four integrated subsystems:

1. Priority Queue Layer — schedule tasks by priority with aging and preemption.
2. Dependency Graph Layer — manage DAG-based task dependencies with cycle detection.
3. Resource Allocation Layer — enforce token, concurrency, memory, and rate limits.
4. Schedule Optimization Layer — optimize ordering for cost, deadlines, and load.

Architecture:
    RuntimeScheduler (singleton)
    ├── PriorityQueue (priority ordering + aging + preemption)
    ├── DependencyGraph (DAG resolution + cycle detection)
    ├── ResourceAllocator (quotas + rate limiting)
    └── ScheduleOptimizer (cost-aware + deadline-aware + batching)
"""

from __future__ import annotations

import heapq
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.runtime_scheduler")


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class TaskPriority(str, Enum):
    """Priority levels for scheduled tasks. Higher values run first."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"

    @property
    def weight(self) -> int:
        """Numeric weight for priority ordering (higher = more urgent)."""
        return {
            TaskPriority.CRITICAL: 50,
            TaskPriority.HIGH: 40,
            TaskPriority.MEDIUM: 30,
            TaskPriority.LOW: 20,
            TaskPriority.BACKGROUND: 10,
        }[self]


class TaskStatus(str, Enum):
    """Lifecycle states for scheduled tasks."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING = "waiting"  # blocked on dependencies


class DependencyType(str, Enum):
    """Type of dependency relationship between tasks."""
    HARD = "hard"  # task cannot start until dependency completes
    SOFT = "soft"  # task prefers dependency completion but can proceed


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ScheduledTask:
    """A task submitted to the runtime scheduler."""
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    deadline: str = ""  # ISO datetime, empty means no deadline
    status: TaskStatus = TaskStatus.QUEUED
    agent_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    enqueued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    completed_at: str = ""
    age_boost: int = 0  # priority aging counter

    def __lt__(self, other: ScheduledTask) -> bool:
        """Compare by priority weight + aging boost (descending)."""
        self_score = self.priority.weight + self.age_boost
        other_score = other.priority.weight + other.age_boost
        return self_score > other_score  # higher score = higher priority (popped first)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "estimated_cost": self.estimated_cost,
            "deadline": self.deadline,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "payload": self.payload,
            "enqueued_at": self.enqueued_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "age_boost": self.age_boost,
        }


@dataclass
class TaskDependency:
    """A dependency edge between two tasks in the DAG."""
    task_id: str = ""
    depends_on: str = ""
    dependency_type: DependencyType = DependencyType.HARD
    timeout_ms: int = 30000  # how long to wait before treating as failed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "depends_on": self.depends_on,
            "dependency_type": self.dependency_type.value,
            "timeout_ms": self.timeout_ms,
            "created_at": self.created_at,
        }


@dataclass
class ResourceQuota:
    """Resource limits for an agent."""
    agent_id: str = ""
    max_tokens_per_minute: int = 100000
    max_concurrent: int = 5
    max_memory_mb: int = 2048
    current_tokens: int = 0
    current_concurrent: int = 0
    current_memory_mb: int = 0
    last_token_reset: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "max_tokens_per_minute": self.max_tokens_per_minute,
            "max_concurrent": self.max_concurrent,
            "max_memory_mb": self.max_memory_mb,
            "current_tokens": self.current_tokens,
            "current_concurrent": self.current_concurrent,
            "current_memory_mb": self.current_memory_mb,
        }


@dataclass
class ScheduleSlot:
    """A time slot allocated for a task on a specific agent."""
    slot_id: str = field(default_factory=lambda: f"slot-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    start_time: float = 0.0  # monotonic time
    duration_ms: int = 0
    task_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "agent_id": self.agent_id,
            "start_time": self.start_time,
            "duration_ms": self.duration_ms,
            "task_id": self.task_id,
        }


@dataclass
class SchedulePlan:
    """A timeline of scheduled slots for an agent."""
    plan_id: str = field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:12]}")
    slots: list[ScheduleSlot] = field(default_factory=list)
    total_cost: float = 0.0
    estimated_completion: float = 0.0  # monotonic time

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "slots": [s.to_dict() for s in self.slots],
            "total_cost": round(self.total_cost, 4),
            "estimated_completion": self.estimated_completion,
        }


@dataclass
class SchedulerStats:
    """Aggregate statistics for the scheduler."""
    total_tasks: int = 0
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    avg_wait_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "queued": self.queued,
            "running": self.running,
            "completed": self.completed,
            "failed": self.failed,
            "avg_wait_ms": round(self.avg_wait_ms, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Priority Queue Layer
# ═══════════════════════════════════════════════════════════════════════════

class PriorityQueueLayer:
    """Priority-based task queue with aging and preemption support.

    Tasks are ordered by priority weight. Low-priority tasks accumulate
    an aging boost over time to prevent starvation. Higher-priority tasks
    can preempt lower-priority ones when preemption is enabled.
    """

    _AGING_INTERVAL = 5  # seconds between aging ticks
    _AGING_BOOST = 1      # priority points added per aging tick

    def __init__(self) -> None:
        self._heap: list[ScheduledTask] = []
        self._lock = threading.Lock()
        self._aging_counter: dict[str, int] = defaultdict(int)
        self._preempted: dict[str, ScheduledTask] = {}

    def push(self, task: ScheduledTask) -> None:
        """Push a task onto the priority queue."""
        with self._lock:
            heapq.heappush(self._heap, task)
            logger.debug(
                f"Task {task.task_id} enqueued (priority={task.priority.value}, agent={task.agent_id})"
            )

    def pop(self) -> ScheduledTask | None:
        """Pop the highest-priority task from the queue."""
        with self._lock:
            if not self._heap:
                return None
            return heapq.heappop(self._heap)

    def peek(self) -> ScheduledTask | None:
        """Peek at the highest-priority task without removing it."""
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0]

    def remove(self, task_id: str) -> bool:
        """Remove a task by ID from the queue."""
        with self._lock:
            for i, task in enumerate(self._heap):
                if task.task_id == task_id:
                    self._heap.pop(i)
                    heapq.heapify(self._heap)
                    return True
            return False

    def apply_aging(self) -> None:
        """Apply aging boost to all queued tasks to prevent starvation."""
        with self._lock:
            for task in self._heap:
                if task.priority in (TaskPriority.LOW, TaskPriority.BACKGROUND):
                    self._aging_counter[task.task_id] += 1
                    if self._aging_counter[task.task_id] >= self._AGING_INTERVAL:
                        task.age_boost += self._AGING_BOOST
                        self._aging_counter[task.task_id] = 0
            heapq.heapify(self._heap)

    def preempt(self, incoming_task: ScheduledTask) -> ScheduledTask | None:
        """Attempt to preempt a running task with a higher-priority one.

        Returns the preempted task if successful, or None if preemption
        is not possible (no lower-priority task running).
        """
        with self._lock:
            if incoming_task.priority in (TaskPriority.LOW, TaskPriority.BACKGROUND):
                return None
            # Store for potential preemption; actual preemption
            # logic is handled by the scheduler at the scheduling layer.
            self._preempted[incoming_task.task_id] = incoming_task
            return None

    def size(self) -> int:
        """Return the number of tasks in the queue."""
        with self._lock:
            return len(self._heap)

    def list_all(self) -> list[ScheduledTask]:
        """Return a snapshot of all tasks in the queue."""
        with self._lock:
            return sorted(self._heap, key=lambda t: (t.priority.weight + t.age_boost), reverse=True)

    def clear(self) -> None:
        """Remove all tasks from the queue."""
        with self._lock:
            self._heap.clear()
            self._aging_counter.clear()
            self._preempted.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Dependency Graph Layer
# ═══════════════════════════════════════════════════════════════════════════

class DependencyGraphLayer:
    """DAG-based dependency manager for task execution ordering.

    Maintains a directed acyclic graph of task dependencies. Provides
    cycle detection, resolution of ready tasks, and timeout handling
    for soft dependencies.
    """

    def __init__(self) -> None:
        # adjacency: task_id -> list of dependent task_ids
        self._dependents: dict[str, list[str]] = defaultdict(list)
        # in_degree: task_id -> number of unmet dependencies
        self._in_degree: dict[str, int] = {}
        # dependency details
        self._edges: dict[str, TaskDependency] = {}  # key: "task_id:depends_on"
        # completion status
        self._completed: set[str] = set()
        self._lock = threading.Lock()

    def add_dependency(self, task_id: str, depends_on: str, dep_type: DependencyType) -> TaskDependency:
        """Add a dependency edge from depends_on -> task_id."""
        with self._lock:
            edge_key = f"{task_id}:{depends_on}"
            dep = TaskDependency(
                task_id=task_id,
                depends_on=depends_on,
                dependency_type=dep_type,
            )
            self._edges[edge_key] = dep
            self._dependents[depends_on].append(task_id)
            self._in_degree[task_id] = self._in_degree.get(task_id, 0) + 1
            self._in_degree.setdefault(depends_on, 0)
            logger.debug(f"Dependency added: {task_id} depends on {depends_on} ({dep_type.value})")
            return dep

    def remove_dependency(self, task_id: str, depends_on: str) -> bool:
        """Remove a dependency edge."""
        with self._lock:
            edge_key = f"{task_id}:{depends_on}"
            if edge_key not in self._edges:
                return False
            del self._edges[edge_key]
            if task_id in self._dependents.get(depends_on, []):
                self._dependents[depends_on].remove(task_id)
            self._in_degree[task_id] = max(0, self._in_degree.get(task_id, 1) - 1)
            logger.debug(f"Dependency removed: {task_id} no longer depends on {depends_on}")
            return True

    def mark_completed(self, task_id: str) -> list[str]:
        """Mark a task as completed and return newly ready task IDs."""
        with self._lock:
            self._completed.add(task_id)
            ready: list[str] = []
            for dependent in self._dependents.get(task_id, []):
                self._in_degree[dependent] = max(0, self._in_degree.get(dependent, 1) - 1)
                if self._in_degree[dependent] == 0:
                    ready.append(dependent)
            return ready

    def get_ready_tasks(self, task_ids: list[str]) -> list[str]:
        """From a list of task IDs, return those with all dependencies met."""
        with self._lock:
            return [tid for tid in task_ids if self._in_degree.get(tid, 0) == 0]

    def resolve_dependencies(self, task_id: str) -> list[str]:
        """Return the list of task IDs that are ready after resolution.

        This includes the task itself if its dependencies are met, plus
        any other tasks that become unblocked as a side effect.
        """
        with self._lock:
            ready: list[str] = []
            if self._in_degree.get(task_id, 0) == 0:
                ready.append(task_id)
            # Also check dependents that might be ready
            for dependent in self._dependents.get(task_id, []):
                if self._in_degree.get(dependent, 0) == 0:
                    ready.append(dependent)
            return ready

    def has_cycle(self) -> bool:
        """Detect if the dependency graph contains a cycle using DFS."""
        with self._lock:
            all_tasks = set(self._in_degree.keys()) | set(self._dependents.keys())
            for dep in self._edges.values():
                all_tasks.add(dep.task_id)
                all_tasks.add(dep.depends_on)

            WHITE, GRAY, BLACK = 0, 1, 2
            color: dict[str, int] = {t: WHITE for t in all_tasks}

            def dfs(node: str) -> bool:
                color[node] = GRAY
                for neighbor in self._dependents.get(node, []):
                    if color.get(neighbor, WHITE) == GRAY:
                        return True
                    if color.get(neighbor, WHITE) == WHITE and dfs(neighbor):
                        return True
                color[node] = BLACK
                return False

            for node in all_tasks:
                if color.get(node, WHITE) == WHITE:
                    if dfs(node):
                        logger.warning(f"Cycle detected in dependency graph (node={node})")
                        return True
            return False

    def get_dependency_timeout(self, task_id: str) -> list[str]:
        """Return dependencies that have exceeded their timeout."""
        with self._lock:
            now = time.monotonic() * 1000
            timed_out: list[str] = []
            for edge_key, dep in self._edges.items():
                if dep.task_id == task_id:
                    dep_time = datetime.fromisoformat(dep.created_at).timestamp() * 1000
                    if now - dep_time > dep.timeout_ms:
                        timed_out.append(dep.depends_on)
            return timed_out

    def clear(self) -> None:
        """Remove all dependencies from the graph."""
        with self._lock:
            self._dependents.clear()
            self._in_degree.clear()
            self._edges.clear()
            self._completed.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Resource Allocation Layer
# ═══════════════════════════════════════════════════════════════════════════

class ResourceAllocationLayer:
    """Resource allocation manager for agent compute budgets.

    Tracks and enforces token budgets, concurrency limits, memory usage,
    and rate limits per agent and per API provider.
    """

    _TOKEN_WINDOW_SECONDS = 60.0

    def __init__(self) -> None:
        self._quotas: dict[str, ResourceQuota] = {}
        self._rate_limiters: dict[str, float] = {}  # provider -> last request monotonic time
        self._min_request_interval: dict[str, float] = {}  # provider -> min seconds between requests
        self._lock = threading.Lock()

    def set_quota(self, agent_id: str, quota: ResourceQuota) -> ResourceQuota:
        """Set or update the resource quota for an agent."""
        with self._lock:
            quota.agent_id = agent_id
            self._quotas[agent_id] = quota
            logger.info(
                f"Quota set for agent {agent_id}: "
                f"tokens={quota.max_tokens_per_minute}/min, "
                f"concurrent={quota.max_concurrent}, "
                f"memory={quota.max_memory_mb}MB"
            )
            return quota

    def get_quota(self, agent_id: str) -> ResourceQuota | None:
        """Get the resource quota for an agent."""
        with self._lock:
            return self._quotas.get(agent_id)

    def check_quota(self, agent_id: str) -> bool:
        """Check if an agent has available resources to run a task.

        Returns True if the agent is within all resource limits:
        - Token budget not exceeded
        - Concurrent execution slots available
        - Memory budget not exceeded
        """
        with self._lock:
            quota = self._quotas.get(agent_id)
            if quota is None:
                return True  # no quota set = no restrictions

            # Reset token counter if window has elapsed
            now = time.monotonic()
            if now - quota.last_token_reset >= self._TOKEN_WINDOW_SECONDS:
                quota.current_tokens = 0
                quota.last_token_reset = now

            if quota.current_tokens >= quota.max_tokens_per_minute:
                return False
            if quota.current_concurrent >= quota.max_concurrent:
                return False
            if quota.current_memory_mb >= quota.max_memory_mb:
                return False
            return True

    def allocate(self, agent_id: str, tokens: int = 0, memory_mb: int = 0) -> bool:
        """Allocate resources for a task. Returns True if successful."""
        with self._lock:
            quota = self._quotas.get(agent_id)
            if quota is None:
                return True

            now = time.monotonic()
            if now - quota.last_token_reset >= self._TOKEN_WINDOW_SECONDS:
                quota.current_tokens = 0
                quota.last_token_reset = now

            if quota.current_tokens + tokens > quota.max_tokens_per_minute:
                return False
            if quota.current_concurrent >= quota.max_concurrent:
                return False
            if quota.current_memory_mb + memory_mb > quota.max_memory_mb:
                return False

            quota.current_tokens += tokens
            quota.current_concurrent += 1
            quota.current_memory_mb += memory_mb
            return True

    def release(self, agent_id: str, tokens: int = 0, memory_mb: int = 0) -> None:
        """Release resources back to an agent's quota."""
        with self._lock:
            quota = self._quotas.get(agent_id)
            if quota is None:
                return
            quota.current_concurrent = max(0, quota.current_concurrent - 1)
            quota.current_memory_mb = max(0, quota.current_memory_mb - memory_mb)

    def set_rate_limit(self, provider: str, min_interval_seconds: float) -> None:
        """Set the minimum interval between requests for a provider."""
        with self._lock:
            self._min_request_interval[provider] = min_interval_seconds
            self._rate_limiters.setdefault(provider, 0.0)

    def check_rate_limit(self, provider: str) -> bool:
        """Check if a request to a provider is within rate limits."""
        with self._lock:
            if provider not in self._min_request_interval:
                return True
            now = time.monotonic()
            last = self._rate_limiters.get(provider, 0.0)
            return (now - last) >= self._min_request_interval[provider]

    def record_request(self, provider: str) -> None:
        """Record a request timestamp for rate limiting."""
        with self._lock:
            self._rate_limiters[provider] = time.monotonic()

    def clear(self) -> None:
        """Reset all resource quotas and rate limiters."""
        with self._lock:
            self._quotas.clear()
            self._rate_limiters.clear()
            self._min_request_interval.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Schedule Optimization Layer
# ═══════════════════════════════════════════════════════════════════════════

class ScheduleOptimizationLayer:
    """Optimizes task ordering for cost, deadlines, and load balancing.

    Strategies:
    - Cost-aware: prefer cheaper tasks when cost information is available.
    - Deadline-aware: prioritize tasks with approaching deadlines.
    - Batch optimization: group similar tasks for execution efficiency.
    - Load balancing: distribute tasks evenly across available agents.
    """

    _DEFAULT_DURATION_MS = 5000  # estimated duration for unknown tasks

    def __init__(self) -> None:
        self._task_history: dict[str, list[float]] = defaultdict(list)  # agent_id -> recent durations

    def optimize_schedule(
        self,
        tasks: list[ScheduledTask],
        agents: list[str],
        quotas: dict[str, ResourceQuota],
        deadline_bias: float = 0.3,
        cost_bias: float = 0.2,
    ) -> SchedulePlan:
        """Generate an optimized schedule plan for a set of tasks.

        Returns a SchedulePlan with time slots assigned to agents,
        optimized for deadlines, cost, and load distribution.
        """
        if not tasks or not agents:
            return SchedulePlan()

        # Sort tasks: deadline-aware first, then cost-aware, then priority
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                self._deadline_urgency(t, deadline_bias),
                -t.estimated_cost * cost_bias,
                -(t.priority.weight + t.age_boost),
            ),
            reverse=True,
        )

        # Track per-agent load
        agent_load: dict[str, float] = {a: 0.0 for a in agents}
        agent_slots: dict[str, list[ScheduleSlot]] = {a: [] for a in agents}
        now = time.monotonic()

        for task in sorted_tasks:
            # Pick the agent with the least load that can run the task
            best_agent = self._pick_agent(task, agents, agent_load, quotas)
            if best_agent is None:
                continue

            duration = self._estimate_duration(task, best_agent)
            start_time = agent_load[best_agent]

            slot = ScheduleSlot(
                agent_id=best_agent,
                start_time=start_time,
                duration_ms=duration,
                task_id=task.task_id,
            )
            agent_slots[best_agent].append(slot)
            agent_load[best_agent] = start_time + (duration / 1000.0)

        # Flatten slots into a single plan
        all_slots: list[ScheduleSlot] = []
        total_cost = 0.0
        max_completion = 0.0

        for agent_id in agents:
            for slot in agent_slots[agent_id]:
                all_slots.append(slot)
                task = next((t for t in sorted_tasks if t.task_id == slot.task_id), None)
                if task:
                    total_cost += task.estimated_cost
                completion = slot.start_time + slot.duration_ms / 1000.0
                if completion > max_completion:
                    max_completion = completion

        plan = SchedulePlan(
            slots=all_slots,
            total_cost=total_cost,
            estimated_completion=max_completion,
        )
        logger.debug(
            f"Optimized schedule: {len(all_slots)} slots, "
            f"cost={total_cost:.2f}, completion={max_completion:.1f}s"
        )
        return plan

    def _deadline_urgency(self, task: ScheduledTask, bias: float) -> float:
        """Calculate urgency based on deadline proximity (0-1)."""
        if not task.deadline:
            return 0.3  # neutral urgency for tasks without deadlines
        try:
            deadline_dt = datetime.fromisoformat(task.deadline)
            now_dt = datetime.now(timezone.utc)
            remaining = (deadline_dt - now_dt).total_seconds()
            if remaining <= 0:
                return 1.0
            # Urgency increases as deadline approaches
            urgency = 1.0 / (1.0 + remaining / 60.0)  # decay over minutes
            return urgency * bias
        except (ValueError, TypeError):
            return 0.3

    def _pick_agent(
        self,
        task: ScheduledTask,
        agents: list[str],
        agent_load: dict[str, float],
        quotas: dict[str, ResourceQuota],
    ) -> str | None:
        """Pick the best agent for a task based on load and quota availability."""
        # If task specifies an agent, prefer it
        if task.agent_id and task.agent_id in agents:
            quota = quotas.get(task.agent_id)
            if quota is None or quota.current_concurrent < quota.max_concurrent:
                return task.agent_id

        # Otherwise, pick the least loaded agent with capacity
        candidates = []
        for agent_id in agents:
            quota = quotas.get(agent_id)
            if quota and quota.current_concurrent >= quota.max_concurrent:
                continue
            candidates.append((agent_load[agent_id], agent_id))

        if not candidates:
            return None

        candidates.sort()
        return candidates[0][1]

    def _estimate_duration(self, task: ScheduledTask, agent_id: str) -> int:
        """Estimate task duration in milliseconds based on history."""
        history = self._task_history.get(agent_id, [])
        if history:
            return int(sum(history) / len(history))
        return self._DEFAULT_DURATION_MS

    def record_duration(self, agent_id: str, duration_ms: float) -> None:
        """Record a task's actual duration for future estimates."""
        self._task_history[agent_id].append(duration_ms)
        if len(self._task_history[agent_id]) > 50:
            self._task_history[agent_id] = self._task_history[agent_id][-50:]

    def batch_tasks(self, tasks: list[ScheduledTask], max_batch_size: int = 5) -> list[list[ScheduledTask]]:
        """Group similar tasks into batches for execution efficiency.

        Tasks are grouped by agent_id and payload similarity.
        """
        if not tasks:
            return []

        # Group by agent_id
        by_agent: dict[str, list[ScheduledTask]] = defaultdict(list)
        for task in tasks:
            by_agent[task.agent_id or "__default__"].append(task)

        batches: list[list[ScheduledTask]] = []
        for agent_tasks in by_agent.values():
            # Sort by priority within each agent group
            agent_tasks.sort(key=lambda t: -(t.priority.weight + t.age_boost))
            for i in range(0, len(agent_tasks), max_batch_size):
                batches.append(agent_tasks[i:i + max_batch_size])

        return batches

    def clear(self) -> None:
        """Clear task history for optimization."""
        self._task_history.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Runtime Scheduler
# ═══════════════════════════════════════════════════════════════════════════

class RuntimeScheduler:
    """Central scheduler for agent task execution.

    Orchestrates four layers — priority queue, dependency graph, resource
    allocation, and schedule optimization — to manage task execution
    across multiple agents with fairness, efficiency, and constraint
    enforcement.
    """

    def __init__(self) -> None:
        self._priority_queue = PriorityQueueLayer()
        self._dependency_graph = DependencyGraphLayer()
        self._resource_allocator = ResourceAllocationLayer()
        self._optimizer = ScheduleOptimizationLayer()

        # Task registry
        self._tasks: dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()

        # Statistics
        self._completed_count = 0
        self._failed_count = 0
        self._wait_times: list[float] = []  # milliseconds
        self._max_wait_samples = 500

        # Aging thread
        self._aging_thread: threading.Thread | None = None
        self._aging_running = False

        logger.info("RuntimeScheduler initialized")

    # ── Task Management ──────────────────────────────────────

    def enqueue(self, task_data: dict[str, Any]) -> ScheduledTask:
        """Create and enqueue a new task from a data dictionary.

        Args:
            task_data: Dict with keys matching ScheduledTask fields.
                Required: none (defaults are used).
                Optional: priority, dependencies, estimated_cost, deadline,
                         agent_id, payload.

        Returns:
            The created ScheduledTask.
        """
        task = ScheduledTask(
            priority=TaskPriority(task_data.get("priority", "medium")),
            dependencies=task_data.get("dependencies", []),
            estimated_cost=task_data.get("estimated_cost", 0.0),
            deadline=task_data.get("deadline", ""),
            agent_id=task_data.get("agent_id", ""),
            payload=task_data.get("payload", {}),
        )

        with self._lock:
            self._tasks[task.task_id] = task

        self._priority_queue.push(task)
        logger.info(
            f"Task enqueued: {task.task_id} "
            f"(priority={task.priority.value}, agent={task.agent_id}, "
            f"deps={len(task.dependencies)})"
        )
        return task

    def dequeue(self, task_id: str) -> bool:
        """Remove a task from the queue by ID.

        Returns True if the task was found and removed.
        """
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status in (TaskStatus.QUEUED, TaskStatus.WAITING):
                    task.status = TaskStatus.CANCELLED
                    self._priority_queue.remove(task_id)
                    logger.info(f"Task dequeued: {task_id}")
                    return True
            return False

    def get_next(self, agent_id: str) -> ScheduledTask | None:
        """Get the next task ready for execution by an agent.

        Considers resource availability, dependency resolution, and
        priority ordering. Returns None if no task is ready.
        """
        # Check resource availability first
        if not self._resource_allocator.check_quota(agent_id):
            return None

        with self._lock:
            # Try to pop tasks from the priority queue until we find one
            # that is ready (dependencies met, resources available)
            temp: list[ScheduledTask] = []
            result: ScheduledTask | None = None

            while True:
                task = self._priority_queue.pop()
                if task is None:
                    break

                if task.status == TaskStatus.CANCELLED:
                    continue

                # Check dependencies
                ready = self._dependency_graph.resolve_dependencies(task.task_id)
                if task.task_id not in ready:
                    temp.append(task)
                    continue

                # Allocate resources
                if self._resource_allocator.allocate(agent_id):
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now(timezone.utc).isoformat()
                    # Calculate wait time
                    try:
                        enqueued = datetime.fromisoformat(task.enqueued_at)
                        wait_ms = (datetime.now(timezone.utc) - enqueued).total_seconds() * 1000
                        self._wait_times.append(wait_ms)
                        if len(self._wait_times) > self._max_wait_samples:
                            self._wait_times = self._wait_times[-self._max_wait_samples:]
                    except (ValueError, TypeError):
                        pass
                    result = task
                    break

                temp.append(task)

            # Push back tasks that weren't selected
            for t in temp:
                self._priority_queue.push(t)

            if result:
                logger.info(f"Task dispatched: {result.task_id} -> agent {agent_id}")
            return result

    def complete_task(self, task_id: str, agent_id: str, tokens: int = 0, memory_mb: int = 0) -> None:
        """Mark a task as completed and release resources."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc).isoformat()
                self._completed_count += 1

                # Record duration for optimization
                if task.started_at:
                    try:
                        started = datetime.fromisoformat(task.started_at)
                        duration_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000
                        self._optimizer.record_duration(agent_id, duration_ms)
                    except (ValueError, TypeError):
                        pass

            # Release resources
            self._resource_allocator.release(agent_id, tokens, memory_mb)

            # Mark dependency completed and unblock dependents
            ready = self._dependency_graph.mark_completed(task_id)
            for ready_id in ready:
                if ready_id in self._tasks and self._tasks[ready_id].status == TaskStatus.WAITING:
                    self._tasks[ready_id].status = TaskStatus.QUEUED
                    self._priority_queue.push(self._tasks[ready_id])
                    logger.debug(f"Task unblocked: {ready_id} (dependency {task_id} completed)")

    def fail_task(self, task_id: str, agent_id: str, tokens: int = 0, memory_mb: int = 0) -> None:
        """Mark a task as failed and release resources."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc).isoformat()
                self._failed_count += 1

            self._resource_allocator.release(agent_id, tokens, memory_mb)

    # ── Dependency Management ─────────────────────────────────

    def add_dependency(
        self, task_id: str, depends_on: str, dep_type: str = "hard"
    ) -> TaskDependency | None:
        """Add a dependency between two tasks.

        Args:
            task_id: The task that depends on another.
            depends_on: The task that must complete first.
            dep_type: 'hard' or 'soft'.

        Returns:
            The created TaskDependency, or None if it would create a cycle.
        """
        dep = self._dependency_graph.add_dependency(
            task_id, depends_on, DependencyType(dep_type)
        )

        # Check for cycles
        if self._dependency_graph.has_cycle():
            self._dependency_graph.remove_dependency(task_id, depends_on)
            logger.warning(f"Cycle detected: {task_id} -> {depends_on}. Dependency rejected.")
            return None

        # Mark task as waiting if it was queued
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.QUEUED:
                task.status = TaskStatus.WAITING
                self._priority_queue.remove(task_id)

        return dep

    def resolve_dependencies(self, task_id: str) -> list[str]:
        """Return task IDs that are ready to execute after dependency resolution."""
        return self._dependency_graph.resolve_dependencies(task_id)

    # ── Resource Management ───────────────────────────────────

    def set_quota(self, agent_id: str, quota: ResourceQuota) -> ResourceQuota:
        """Set resource quota for an agent."""
        return self._resource_allocator.set_quota(agent_id, quota)

    def check_quota(self, agent_id: str) -> bool:
        """Check if an agent has available resources."""
        return self._resource_allocator.check_quota(agent_id)

    def set_rate_limit(self, provider: str, min_interval_seconds: float) -> None:
        """Set rate limit for an API provider."""
        self._resource_allocator.set_rate_limit(provider, min_interval_seconds)

    # ── Schedule Planning ─────────────────────────────────────

    def get_schedule(self, agent_id: str) -> SchedulePlan:
        """Get the current schedule plan for an agent.

        Returns a SchedulePlan with all pending and running tasks
        organized into time slots.
        """
        with self._lock:
            agent_tasks = [
                t for t in self._tasks.values()
                if t.agent_id == agent_id and t.status in (TaskStatus.QUEUED, TaskStatus.WAITING)
            ]

        quotas = {}
        q = self._resource_allocator.get_quota(agent_id)
        if q:
            quotas[agent_id] = q

        return self._optimizer.optimize_schedule(
            agent_tasks, [agent_id], quotas
        )

    def optimize_schedule(self, agent_id: str) -> SchedulePlan:
        """Run full schedule optimization for an agent.

        This is the primary entry point for schedule optimization,
        returning a cost- and deadline-aware plan.
        """
        return self.get_schedule(agent_id)

    def batch_optimize(self, agent_id: str, max_batch_size: int = 5) -> list[list[ScheduledTask]]:
        """Group pending tasks for an agent into optimized batches."""
        with self._lock:
            agent_tasks = [
                t for t in self._tasks.values()
                if t.agent_id == agent_id and t.status in (TaskStatus.QUEUED, TaskStatus.WAITING)
            ]
        return self._optimizer.batch_tasks(agent_tasks, max_batch_size)

    # ── Statistics ────────────────────────────────────────────

    def get_stats(self) -> SchedulerStats:
        """Return aggregate scheduler statistics."""
        with self._lock:
            queued = sum(
                1 for t in self._tasks.values()
                if t.status in (TaskStatus.QUEUED, TaskStatus.WAITING)
            )
            running = sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.RUNNING
            )

            avg_wait = 0.0
            if self._wait_times:
                avg_wait = sum(self._wait_times) / len(self._wait_times)

            return SchedulerStats(
                total_tasks=len(self._tasks),
                queued=queued,
                running=running,
                completed=self._completed_count,
                failed=self._failed_count,
                avg_wait_ms=round(avg_wait, 2),
            )

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(
        self,
        agent_id: str = "",
        status: TaskStatus | None = None,
    ) -> list[ScheduledTask]:
        """List tasks with optional filtering."""
        with self._lock:
            tasks = list(self._tasks.values())
            if agent_id:
                tasks = [t for t in tasks if t.agent_id == agent_id]
            if status:
                tasks = [t for t in tasks if t.status == status]
            return sorted(tasks, key=lambda t: t.enqueued_at, reverse=True)

    # ── Aging Loop ────────────────────────────────────────────

    def start_aging(self, interval: float = 5.0) -> None:
        """Start a background thread that applies priority aging."""
        if self._aging_running:
            return
        self._aging_running = True
        self._aging_thread = threading.Thread(
            target=self._aging_loop, args=(interval,), daemon=True
        )
        self._aging_thread.start()
        logger.info("Priority aging loop started")

    def stop_aging(self) -> None:
        """Stop the priority aging background thread."""
        self._aging_running = False
        if self._aging_thread:
            self._aging_thread.join(timeout=2.0)
            self._aging_thread = None
        logger.info("Priority aging loop stopped")

    def _aging_loop(self, interval: float) -> None:
        """Background loop that applies aging to queued tasks."""
        while self._aging_running:
            time.sleep(interval)
            self._priority_queue.apply_aging()

    # ── Reset ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset the entire scheduler to its initial state."""
        self.stop_aging()
        with self._lock:
            self._tasks.clear()
            self._completed_count = 0
            self._failed_count = 0
            self._wait_times.clear()
        self._priority_queue.clear()
        self._dependency_graph.clear()
        self._resource_allocator.clear()
        self._optimizer.clear()
        logger.info("RuntimeScheduler reset")


# ═══════════════════════════════════════════════════════════════════════════
# Global Instance
# ═══════════════════════════════════════════════════════════════════════════

runtime_scheduler = RuntimeScheduler()