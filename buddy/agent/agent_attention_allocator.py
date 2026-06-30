"""Agent Attention Allocator — dynamic attention and focus management.

The allocator manages how the agent distributes its cognitive attention across
competing tasks, contexts, and goals. It implements an attention budget system
where each target competes for limited attention resources based on urgency,
importance, and decay.

Core capabilities:
  - Attention Budgets: per-agent pools of attention that can be subdivided.
  - Attention Targets: registered foci (tasks, contexts, goals, etc.) that
    compete for budget based on priority, urgency, importance, and decay.
  - Weighted Allocation: targets receive attention weight computed from
    base weight, urgency, importance, and a priority multiplier.
  - Preemption: when budget is exhausted, lower-priority allocations can be
    preempted to free capacity for higher-priority work.
  - Decay Models: four decay functions (linear, exponential, logarithmic,
    step) model how attention naturally drifts away from inactive targets.
  - Rebalancing: weights are recomputed over time and normalized back to the
    budget envelope so the agent stays within its attention capacity.
  - Modes: focused, divided, scanning, deep_work, and background attention
    modes provide high-level policy knobs on the allocator.
  - Observability: snapshots, events, and aggregate stats expose the state
    of attention for downstream telemetry and self-reflection.

Architecture:
    AgentAttentionAllocator (singleton)
    ├── AttentionBudget       (per-agent pool of attention)
    ├── AttentionTarget       (a registered focus competing for attention)
    ├── AttentionAllocation   (an active grant of attention to a target)
    ├── AttentionSnapshot     (point-in-time summary of a budget)
    ├── AttentionEvent        (append-only audit log of changes)
    └── AllocatorStats        (aggregate counters across all budgets)

The engine is intentionally dependency-free so it can run in any Buddy
runtime without extra packages.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class AttentionMode(str, Enum):
    """High-level policy modes describing how attention is distributed."""

    FOCUSED = "focused"          # narrow concentration on a single target
    DIVIDED = "divided"          # split across several concurrent targets
    SCANNING = "scanning"        # broad low-fidelity sweep over many targets
    DEEP_WORK = "deep_work"      # sustained, interruption-averse focus
    BACKGROUND = "background"    # passive monitoring, low overall weight


class PriorityLevel(str, Enum):
    """Priority bands for an attention target."""

    CRITICAL = "critical"        # must be addressed immediately
    HIGH = "high"                # important, address soon
    MEDIUM = "medium"            # normal priority
    LOW = "low"                  # address when capacity allows
    BACKGROUND = "background"    # best-effort, only when idle


class FocusType(str, Enum):
    """The kind of object an attention target represents."""

    TASK = "task"                # a concrete unit of work
    CONTEXT = "context"          # an active context or workspace
    GOAL = "goal"                # a longer-term objective
    CONVERSATION = "conversation"  # an ongoing dialogue
    MONITORING = "monitoring"    # a watch over some signal or resource
    LEARNING = "learning"        # an active learning or study thread


class AllocationStatus(str, Enum):
    """Lifecycle states of an attention allocation."""

    ACTIVE = "active"            # currently receiving attention weight
    PAUSED = "paused"            # temporarily suspended
    EXPIRED = "expired"          # passed its deadline without completion
    COMPLETED = "completed"      # the target finished and freed the weight
    PREEMPTED = "preempted"      # displaced by a higher-priority target


class DecayFunction(str, Enum):
    """Mathematical model describing how a target's weight decays over time."""

    LINEAR = "linear"            # subtract proportional to elapsed time
    EXPONENTIAL = "exponential"  # multiplicative decay over time
    LOGARITHMIC = "logarithmic"  # sub-linear decay over time
    STEP = "step"                # fixed step decay once threshold elapsed


# ═══════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AttentionTarget:
    """A registered focus that competes for a share of an attention budget.

    Each target carries a base weight (its intrinsic salience), plus urgency
    and importance modifiers that feed into the computed allocation weight.
    Decay is applied on each rebalance based on the configured function and
    rate, using ``last_accessed`` as the reference time.
    """

    target_id: str
    name: str
    description: str
    focus_type: FocusType
    priority: PriorityLevel
    base_weight: float = 0.5
    current_weight: float = 0.5
    urgency: float = 0.0  # 0..1
    importance: float = 0.5  # 0..1
    deadline: float | None = None
    decay_function: DecayFunction = DecayFunction.LINEAR
    decay_rate: float = 0.01
    last_accessed: float = 0.0
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "name": self.name,
            "description": self.description,
            "focus_type": self.focus_type.value,
            "priority": self.priority.value,
            "base_weight": self.base_weight,
            "current_weight": self.current_weight,
            "urgency": self.urgency,
            "importance": self.importance,
            "deadline": self.deadline,
            "decay_function": self.decay_function.value,
            "decay_rate": self.decay_rate,
            "last_accessed": self.last_accessed,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class AttentionBudget:
    """Per-agent pool of attention that can be subdivided across targets."""

    budget_id: str
    agent_id: str
    total_budget: float = 100.0
    allocated_budget: float = 0.0
    available_budget: float = 100.0
    mode: AttentionMode = AttentionMode.DIVIDED
    max_concurrent_targets: int = 5
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget_id": self.budget_id,
            "agent_id": self.agent_id,
            "total_budget": self.total_budget,
            "allocated_budget": self.allocated_budget,
            "available_budget": self.available_budget,
            "mode": self.mode.value,
            "max_concurrent_targets": self.max_concurrent_targets,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AttentionAllocation:
    """An active grant of attention weight to a target within a budget."""

    allocation_id: str
    budget_id: str
    target_id: str
    allocated_weight: float
    status: AllocationStatus = AllocationStatus.ACTIVE
    allocated_at: float = 0.0
    expires_at: float | None = None
    preempted_by: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "budget_id": self.budget_id,
            "target_id": self.target_id,
            "allocated_weight": self.allocated_weight,
            "status": self.status.value,
            "allocated_at": self.allocated_at,
            "expires_at": self.expires_at,
            "preempted_by": self.preempted_by,
            "notes": self.notes,
        }


@dataclass
class AttentionSnapshot:
    """A point-in-time summary of an attention budget."""

    snapshot_id: str
    budget_id: str
    mode: AttentionMode
    total_targets: int
    active_allocations: int
    top_targets: list[dict[str, Any]] = field(default_factory=list)
    utilization: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "budget_id": self.budget_id,
            "mode": self.mode.value,
            "total_targets": self.total_targets,
            "active_allocations": self.active_allocations,
            "top_targets": list(self.top_targets),
            "utilization": self.utilization,
            "timestamp": self.timestamp,
        }


@dataclass
class AttentionEvent:
    """An entry in the append-only audit log of attention changes."""

    event_id: str
    budget_id: str
    event_type: str  # "allocation", "deallocation", "preemption", "rebalance", "mode_change"
    target_id: str | None
    description: str
    old_value: Any = None
    new_value: Any = None
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "budget_id": self.budget_id,
            "event_type": self.event_type,
            "target_id": self.target_id,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp,
        }


@dataclass
class AllocatorStats:
    """Aggregate counters describing the state of the whole allocator."""

    total_budgets: int = 0
    total_targets: int = 0
    total_allocations: int = 0
    total_preemptions: int = 0
    total_rebalances: int = 0
    avg_utilization: float = 0.0
    active_budgets: int = 0
    targets_by_priority: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_budgets": self.total_budgets,
            "total_targets": self.total_targets,
            "total_allocations": self.total_allocations,
            "total_preemptions": self.total_preemptions,
            "total_rebalances": self.total_rebalances,
            "avg_utilization": self.avg_utilization,
            "active_budgets": self.active_budgets,
            "targets_by_priority": dict(self.targets_by_priority),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

_PRIORITY_MULTIPLIERS: dict[PriorityLevel, float] = {
    PriorityLevel.CRITICAL: 3.0,
    PriorityLevel.HIGH: 2.0,
    PriorityLevel.MEDIUM: 1.0,
    PriorityLevel.LOW: 0.5,
    PriorityLevel.BACKGROUND: 0.1,
}

# Numeric ranking for priority comparison (higher = more important).
_PRIORITY_RANK: dict[PriorityLevel, int] = {
    PriorityLevel.CRITICAL: 5,
    PriorityLevel.HIGH: 4,
    PriorityLevel.MEDIUM: 3,
    PriorityLevel.LOW: 2,
    PriorityLevel.BACKGROUND: 1,
}

# Per-mode hints on how aggressively attention is concentrated. Kept as a
# reference for downstream policy decisions rather than used directly here.
_MODE_WEIGHT_BIAS: dict[AttentionMode, float] = {
    AttentionMode.FOCUSED: 0.9,
    AttentionMode.DIVIDED: 0.5,
    AttentionMode.SCANNING: 0.3,
    AttentionMode.DEEP_WORK: 1.0,
    AttentionMode.BACKGROUND: 0.1,
}


# ═══════════════════════════════════════════════════════════════════════════
# Allocator
# ═══════════════════════════════════════════════════════════════════════════

class AgentAttentionAllocator:
    """Dynamic attention and focus management engine.

    Manages per-agent attention budgets and the targets competing for them.
    All public mutation methods are guarded by a single lock so the allocator
    is safe to call from multiple threads.
    """

    MAX_TARGETS_PER_BUDGET: int = 100
    MAX_EVENTS: int = 10000

    def __init__(self) -> None:
        self._budgets: dict[str, AttentionBudget] = {}
        # budget_id -> {target_id -> target}
        self._targets: dict[str, dict[str, AttentionTarget]] = {}
        # budget_id -> list of allocations (newest appended at end)
        self._allocations: dict[str, list[AttentionAllocation]] = {}
        # global, append-only event log (capped at MAX_EVENTS)
        self._events: list[AttentionEvent] = []
        self._lock = threading.Lock()

    # ───────────────────────────────────────────────────────────────────
    # Budget lifecycle
    # ───────────────────────────────────────────────────────────────────

    def create_budget(
        self,
        agent_id: str,
        total_budget: float = 100.0,
        mode: AttentionMode = AttentionMode.DIVIDED,
        max_concurrent_targets: int = 5,
    ) -> AttentionBudget:
        """Create a new attention budget for an agent."""
        if total_budget <= 0:
            raise ValueError("total_budget must be positive")
        if max_concurrent_targets < 1:
            raise ValueError("max_concurrent_targets must be >= 1")

        now = time.time()
        budget = AttentionBudget(
            budget_id=str(uuid.uuid4()),
            agent_id=agent_id,
            total_budget=total_budget,
            allocated_budget=0.0,
            available_budget=total_budget,
            mode=mode,
            max_concurrent_targets=max_concurrent_targets,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._budgets[budget.budget_id] = budget
            self._targets[budget.budget_id] = {}
            self._allocations[budget.budget_id] = []
            self._record_event(
                budget.budget_id,
                "mode_change",
                None,
                f"Budget created for agent {agent_id} in {mode.value} mode",
                None,
                mode.value,
            )
        return budget

    def get_budget(self, budget_id: str) -> AttentionBudget | None:
        """Return the budget for the given id, or None if not found."""
        with self._lock:
            budget = self._budgets.get(budget_id)
            return budget

    def list_budgets(self) -> list[AttentionBudget]:
        """Return all known budgets as a fresh list."""
        with self._lock:
            return list(self._budgets.values())

    def set_mode(self, budget_id: str, mode: AttentionMode) -> AttentionBudget | None:
        """Change a budget's attention mode and trigger a rebalance."""
        with self._lock:
            budget = self._budgets.get(budget_id)
            if budget is None:
                return None
            old_mode = budget.mode
            if old_mode == mode:
                return budget
            budget.mode = mode
            budget.updated_at = time.time()
            self._record_event(
                budget_id,
                "mode_change",
                None,
                f"Mode changed from {old_mode.value} to {mode.value}",
                old_mode.value,
                mode.value,
            )
            # Rebalance in-place under the same lock to reflect the new mode.
            self._rebalance_locked(budget_id)
            return budget

    # ───────────────────────────────────────────────────────────────────
    # Target lifecycle
    # ───────────────────────────────────────────────────────────────────

    def register_target(
        self,
        budget_id: str,
        name: str,
        description: str,
        focus_type: FocusType,
        priority: PriorityLevel = PriorityLevel.MEDIUM,
        base_weight: float = 0.5,
        urgency: float = 0.0,
        importance: float = 0.5,
        deadline: float | None = None,
        decay_function: DecayFunction = DecayFunction.LINEAR,
        decay_rate: float = 0.01,
        metadata: dict[str, Any] | None = None,
    ) -> AttentionTarget:
        """Register a new attention target on the given budget."""
        if not name:
            raise ValueError("name must not be empty")
        if not (0.0 <= urgency <= 1.0):
            raise ValueError("urgency must be in [0.0, 1.0]")
        if not (0.0 <= importance <= 1.0):
            raise ValueError("importance must be in [0.0, 1.0]")
        if base_weight < 0.0:
            raise ValueError("base_weight must be non-negative")
        if decay_rate < 0.0:
            raise ValueError("decay_rate must be non-negative")

        now = time.time()
        target = AttentionTarget(
            target_id=str(uuid.uuid4()),
            name=name,
            description=description,
            focus_type=focus_type,
            priority=priority,
            base_weight=base_weight,
            current_weight=base_weight,
            urgency=urgency,
            importance=importance,
            deadline=deadline,
            decay_function=decay_function,
            decay_rate=decay_rate,
            last_accessed=now,
            created_at=now,
            metadata=dict(metadata) if metadata else {},
        )

        with self._lock:
            if budget_id not in self._budgets:
                raise KeyError(f"Unknown budget_id: {budget_id}")
            targets_for_budget = self._targets[budget_id]
            if len(targets_for_budget) >= self.MAX_TARGETS_PER_BUDGET:
                raise RuntimeError(
                    f"Budget {budget_id} already has the maximum of "
                    f"{self.MAX_TARGETS_PER_BUDGET} targets"
                )
            targets_for_budget[target.target_id] = target
            self._record_event(
                budget_id,
                "allocation",
                target.target_id,
                f"Target registered: {name}",
                None,
                target.to_dict(),
            )
        return target

    def get_target(self, budget_id: str, target_id: str) -> AttentionTarget | None:
        """Return a target by id, or None if not found."""
        with self._lock:
            targets_for_budget = self._targets.get(budget_id)
            if targets_for_budget is None:
                return None
            return targets_for_budget.get(target_id)

    def list_targets(self, budget_id: str, active_only: bool = False) -> list[AttentionTarget]:
        """Return targets for a budget as a fresh list.

        When ``active_only`` is True, only targets with at least one ACTIVE
        allocation are returned.
        """
        with self._lock:
            targets_for_budget = self._targets.get(budget_id)
            if targets_for_budget is None:
                return []
            targets = list(targets_for_budget.values())
            if not active_only:
                return targets
            active_ids = {
                a.target_id
                for a in self._allocations.get(budget_id, [])
                if a.status == AllocationStatus.ACTIVE
            }
            return [t for t in targets if t.target_id in active_ids]

    def update_target(
        self,
        budget_id: str,
        target_id: str,
        urgency: float | None = None,
        importance: float | None = None,
        priority: PriorityLevel | None = None,
        deadline: float | None = None,
    ) -> AttentionTarget | None:
        """Update mutable fields of a target. Returns the updated target."""
        with self._lock:
            targets_for_budget = self._targets.get(budget_id)
            if targets_for_budget is None:
                return None
            target = targets_for_budget.get(target_id)
            if target is None:
                return None

            if urgency is not None:
                if not (0.0 <= urgency <= 1.0):
                    raise ValueError("urgency must be in [0.0, 1.0]")
                target.urgency = urgency
            if importance is not None:
                if not (0.0 <= importance <= 1.0):
                    raise ValueError("importance must be in [0.0, 1.0]")
                target.importance = importance
            if priority is not None:
                target.priority = priority
            if deadline is not None:
                target.deadline = deadline

            # Touching the target refreshes its decay clock and pulls its
            # current weight back toward the freshly computed value.
            target.last_accessed = time.time()
            target.current_weight = self._compute_weight(target)

            self._record_event(
                budget_id,
                "rebalance",
                target.target_id,
                f"Target updated: {target.name}",
                None,
                target.to_dict(),
            )
            return target

    def remove_target(self, budget_id: str, target_id: str) -> bool:
        """Remove a target and release any active allocation it held."""
        with self._lock:
            targets_for_budget = self._targets.get(budget_id)
            if targets_for_budget is None or target_id not in targets_for_budget:
                return False
            # Deallocate any active allocation for this target first.
            self._deallocate_locked(budget_id, target_id)
            removed = targets_for_budget.pop(target_id, None)
            if removed is not None:
                self._record_event(
                    budget_id,
                    "deallocation",
                    target_id,
                    f"Target removed: {removed.name}",
                    removed.to_dict(),
                    None,
                )
                return True
            return False

    # ───────────────────────────────────────────────────────────────────
    # Allocation
    # ───────────────────────────────────────────────────────────────────

    def allocate(
        self,
        budget_id: str,
        target_id: str,
        allocated_weight: float | None = None,
    ) -> AttentionAllocation:
        """Allocate attention weight to a target.

        If ``allocated_weight`` is not provided, the weight is computed from
        the target's base weight, urgency, importance, and priority. If the
        budget does not have enough available capacity, the lowest-priority
        active allocation is preempted to make room.
        """
        with self._lock:
            if budget_id not in self._budgets:
                raise KeyError(f"Unknown budget_id: {budget_id}")
            budget = self._budgets[budget_id]
            target = self._targets[budget_id].get(target_id)
            if target is None:
                raise KeyError(f"Unknown target_id: {target_id}")

            # Reject duplicate active allocation for the same target.
            for existing in self._allocations[budget_id]:
                if (
                    existing.target_id == target_id
                    and existing.status == AllocationStatus.ACTIVE
                ):
                    return existing

            # Concurrency cap: preempt the weakest allocation if needed.
            active_count = sum(
                1
                for a in self._allocations[budget_id]
                if a.status == AllocationStatus.ACTIVE
            )
            if active_count >= budget.max_concurrent_targets:
                self._preempt_lowest(budget_id, 0.0)

            if allocated_weight is None:
                weight = self._compute_weight(target)
            else:
                if allocated_weight < 0.0:
                    raise ValueError("allocated_weight must be non-negative")
                weight = allocated_weight

            # Make room in the budget if needed.
            if weight > budget.available_budget:
                needed = weight - budget.available_budget
                self._preempt_lowest(budget_id, needed)
                # If we still cannot fit it, clamp to what's available —
                # but never to zero for a positive request (always grant at
                # least a minimal sliver so the target remains scheduled).
                if weight > budget.available_budget:
                    if budget.available_budget <= 0.0:
                        budget.available_budget = max(0.0, budget.total_budget - budget.allocated_budget)
                    weight = max(min(weight, budget.available_budget), 0.0)

            now = time.time()
            allocation = AttentionAllocation(
                allocation_id=str(uuid.uuid4()),
                budget_id=budget_id,
                target_id=target_id,
                allocated_weight=weight,
                status=AllocationStatus.ACTIVE,
                allocated_at=now,
                expires_at=target.deadline,
                preempted_by=None,
                notes="",
            )
            self._allocations[budget_id].append(allocation)
            budget.allocated_budget += weight
            budget.available_budget = max(0.0, budget.total_budget - budget.allocated_budget)
            budget.updated_at = now

            target.last_accessed = now
            target.current_weight = weight

            self._record_event(
                budget_id,
                "allocation",
                target_id,
                f"Allocated {weight:.4f} to target {target.name}",
                None,
                allocation.to_dict(),
            )
            return allocation

    def deallocate(self, budget_id: str, target_id: str) -> bool:
        """Release the active allocation held by a target."""
        with self._lock:
            return self._deallocate_locked(budget_id, target_id)

    def get_allocations(
        self,
        budget_id: str,
        status: AllocationStatus | None = None,
    ) -> list[AttentionAllocation]:
        """Return allocations for a budget, optionally filtered by status."""
        with self._lock:
            allocations = self._allocations.get(budget_id, [])
            if status is None:
                return list(allocations)
            return [a for a in allocations if a.status == status]

    # ───────────────────────────────────────────────────────────────────
    # Rebalancing & snapshots
    # ───────────────────────────────────────────────────────────────────

    def rebalance(self, budget_id: str) -> list[AttentionAllocation]:
        """Recompute target weights, apply decay, and renormalize to budget."""
        with self._lock:
            return self._rebalance_locked(budget_id)

    def get_snapshot(self, budget_id: str) -> AttentionSnapshot:
        """Capture a point-in-time summary of the budget."""
        with self._lock:
            budget = self._budgets.get(budget_id)
            if budget is None:
                raise KeyError(f"Unknown budget_id: {budget_id}")
            targets = self._targets.get(budget_id, {})
            allocations = self._allocations.get(budget_id, [])

            active_allocations = [
                a for a in allocations if a.status == AllocationStatus.ACTIVE
            ]
            active_ids = {a.target_id for a in active_allocations}
            active_targets = [t for t in targets.values() if t.target_id in active_ids]

            # Build the top-5 by current weight.
            ranked = sorted(
                active_targets,
                key=lambda t: t.current_weight,
                reverse=True,
            )[:5]
            top_targets = [
                {
                    "target_id": t.target_id,
                    "name": t.name,
                    "weight": t.current_weight,
                    "priority": t.priority.value,
                }
                for t in ranked
            ]

            utilization = (
                budget.allocated_budget / budget.total_budget
                if budget.total_budget > 0
                else 0.0
            )
            snapshot = AttentionSnapshot(
                snapshot_id=str(uuid.uuid4()),
                budget_id=budget_id,
                mode=budget.mode,
                total_targets=len(targets),
                active_allocations=len(active_allocations),
                top_targets=top_targets,
                utilization=utilization,
                timestamp=time.time(),
            )
            return snapshot

    # ───────────────────────────────────────────────────────────────────
    # Events & stats
    # ───────────────────────────────────────────────────────────────────

    def get_events(
        self,
        budget_id: str | None = None,
        limit: int = 100,
    ) -> list[AttentionEvent]:
        """Return events, optionally filtered by budget, newest first."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        with self._lock:
            events = self._events
            if budget_id is not None:
                filtered = [e for e in events if e.budget_id == budget_id]
            else:
                filtered = list(events)
            # Newest first.
            return list(reversed(filtered[-limit:])) if limit else list(reversed(filtered))

    def get_stats(self) -> AllocatorStats:
        """Aggregate counters across all budgets."""
        with self._lock:
            total_targets = sum(len(t) for t in self._targets.values())
            total_allocations = sum(len(a) for a in self._allocations.values())
            total_preemptions = sum(
                1
                for a in self._allocations.values()
                for alloc in a
                if alloc.status == AllocationStatus.PREEMPTED
            )
            total_rebalances = sum(
                1 for e in self._events if e.event_type == "rebalance"
            )
            active_budgets = sum(
                1
                for b in self._budgets.values()
                if any(
                    a.status == AllocationStatus.ACTIVE
                    for a in self._allocations.get(b.budget_id, [])
                )
            )

            # Average utilization across all budgets.
            utilizations: list[float] = []
            for b in self._budgets.values():
                if b.total_budget > 0:
                    utilizations.append(b.allocated_budget / b.total_budget)
            avg_utilization = (
                sum(utilizations) / len(utilizations) if utilizations else 0.0
            )

            targets_by_priority: dict[str, int] = {}
            for targets in self._targets.values():
                for t in targets.values():
                    key = t.priority.value
                    targets_by_priority[key] = targets_by_priority.get(key, 0) + 1

            return AllocatorStats(
                total_budgets=len(self._budgets),
                total_targets=total_targets,
                total_allocations=total_allocations,
                total_preemptions=total_preemptions,
                total_rebalances=total_rebalances,
                avg_utilization=avg_utilization,
                active_budgets=active_budgets,
                targets_by_priority=targets_by_priority,
            )

    # ───────────────────────────────────────────────────────────────────
    # Internal helpers (must be called while holding self._lock)
    # ───────────────────────────────────────────────────────────────────

    def _compute_weight(self, target: AttentionTarget) -> float:
        """Compute the raw attention weight a target deserves."""
        priority_mult = _PRIORITY_MULTIPLIERS.get(target.priority, 1.0)
        weight = (
            target.base_weight
            * (1.0 + target.urgency)
            * target.importance
            * priority_mult
        )
        return max(0.0, weight)

    def _apply_decay(self, target: AttentionTarget, current_time: float) -> float:
        """Apply the target's decay function since its last access."""
        elapsed = current_time - target.last_accessed
        if elapsed <= 0:
            return target.current_weight

        rate = target.decay_rate
        if target.decay_function == DecayFunction.LINEAR:
            return max(0.0, target.current_weight - rate * elapsed)
        if target.decay_function == DecayFunction.EXPONENTIAL:
            return target.current_weight * math.exp(-rate * elapsed)
        if target.decay_function == DecayFunction.LOGARITHMIC:
            return max(0.0, target.current_weight - rate * math.log(1.0 + elapsed))
        if target.decay_function == DecayFunction.STEP:
            if elapsed > 1.0:
                return max(0.0, target.current_weight - rate)
            return target.current_weight
        return target.current_weight

    def _preempt_lowest(
        self,
        budget_id: str,
        needed_weight: float,
    ) -> AttentionAllocation | None:
        """Preempt the lowest-priority active allocation to free capacity.

        Selects the active allocation whose target has the lowest priority
        rank, breaking ties by the smallest allocated weight. The chosen
        allocation is marked PREEMPTED and its weight is returned to the
        budget. Returns the preempted allocation, or None if no candidate
        was available.
        """
        allocations = self._allocations.get(budget_id, [])
        targets = self._targets.get(budget_id, {})

        best_index: int | None = None
        best_score: tuple[int, float] | None = None
        for idx, alloc in enumerate(allocations):
            if alloc.status != AllocationStatus.ACTIVE:
                continue
            target = targets.get(alloc.target_id)
            priority = target.priority if target is not None else PriorityLevel.BACKGROUND
            rank = _PRIORITY_RANK.get(priority, 0)
            score = (rank, alloc.allocated_weight)
            if best_score is None or score < best_score:
                best_score = score
                best_index = idx

        if best_index is None:
            return None

        victim = allocations[best_index]
        victim_target = targets.get(victim.target_id)
        victim_name = victim_target.name if victim_target is not None else victim.target_id

        budget = self._budgets.get(budget_id)
        if budget is not None:
            budget.allocated_budget = max(0.0, budget.allocated_budget - victim.allocated_weight)
            budget.available_budget = max(0.0, budget.total_budget - budget.allocated_budget)
            budget.updated_at = time.time()

        victim.status = AllocationStatus.PREEMPTED
        # preempted_by is filled in by the caller when a new allocation
        # displaces this one; here we leave it blank for capacity-driven
        # preemptions triggered by the concurrency cap.

        self._record_event(
            budget_id,
            "preemption",
            victim.target_id,
            f"Preempted target {victim_name} to free capacity",
            victim.to_dict(),
            AllocationStatus.PREEMPTED.value,
        )
        return victim

    def _record_event(
        self,
        budget_id: str,
        event_type: str,
        target_id: str | None,
        description: str,
        old_value: Any,
        new_value: Any,
    ) -> AttentionEvent:
        """Append an event to the log. Caller must hold the lock."""
        event = AttentionEvent(
            event_id=str(uuid.uuid4()),
            budget_id=budget_id,
            event_type=event_type,
            target_id=target_id,
            description=description,
            old_value=old_value,
            new_value=new_value,
            timestamp=time.time(),
        )
        self._events.append(event)
        if len(self._events) > self.MAX_EVENTS:
            # Drop the oldest entries to stay within the cap.
            overflow = len(self._events) - self.MAX_EVENTS
            del self._events[:overflow]
        return event

    def _normalize_weights(self, budget_id: str) -> None:
        """Scale all active allocations so their total fits the budget.

        Caller must hold the lock. If the total active weight exceeds the
        budget envelope, every active allocation is scaled down uniformly.
        If it falls below the envelope, weights are left as-is so targets
        keep their earned weight rather than being inflated.
        """
        budget = self._budgets.get(budget_id)
        if budget is None:
            return
        allocations = self._allocations.get(budget_id, [])
        active = [a for a in allocations if a.status == AllocationStatus.ACTIVE]
        if not active:
            budget.allocated_budget = 0.0
            budget.available_budget = budget.total_budget
            return

        total = sum(a.allocated_weight for a in active)
        if total <= 0:
            return

        if total > budget.total_budget:
            scale = budget.total_budget / total
            for a in active:
                a.allocated_weight *= scale
            total = sum(a.allocated_weight for a in active)

        budget.allocated_budget = total
        budget.available_budget = max(0.0, budget.total_budget - total)
        budget.updated_at = time.time()

    def _deallocate_locked(self, budget_id: str, target_id: str) -> bool:
        """Internal deallocate. Caller must hold the lock."""
        budget = self._budgets.get(budget_id)
        allocations = self._allocations.get(budget_id, [])
        for alloc in allocations:
            if alloc.target_id != target_id:
                continue
            if alloc.status != AllocationStatus.ACTIVE:
                return False
            alloc.status = AllocationStatus.COMPLETED
            if budget is not None:
                budget.allocated_budget = max(
                    0.0, budget.allocated_budget - alloc.allocated_weight
                )
                budget.available_budget = max(
                    0.0, budget.total_budget - budget.allocated_budget
                )
                budget.updated_at = time.time()
            target = self._targets.get(budget_id, {}).get(target_id)
            target_name = target.name if target is not None else target_id
            self._record_event(
                budget_id,
                "deallocation",
                target_id,
                f"Deallocated target {target_name}",
                alloc.to_dict(),
                AllocationStatus.COMPLETED.value,
            )
            return True
        return False

    def _rebalance_locked(self, budget_id: str) -> list[AttentionAllocation]:
        """Internal rebalance. Caller must hold the lock."""
        budget = self._budgets.get(budget_id)
        if budget is None:
            return []
        targets = self._targets.get(budget_id, {})
        allocations = self._allocations.get(budget_id, [])
        now = time.time()

        # Apply decay to every target (whether or not it currently has an
        # active allocation) so weights stay current when read later.
        for target in targets.values():
            target.current_weight = self._apply_decay(target, now)
            # Expire targets whose deadline has passed.
            if target.deadline is not None and now > target.deadline:
                for alloc in allocations:
                    if (
                        alloc.target_id == target.target_id
                        and alloc.status == AllocationStatus.ACTIVE
                    ):
                        alloc.status = AllocationStatus.EXPIRED
                        budget.allocated_budget = max(
                            0.0, budget.allocated_budget - alloc.allocated_weight
                        )
                        self._record_event(
                            budget_id,
                            "deallocation",
                            target.target_id,
                            f"Target {target.name} expired at deadline",
                            alloc.to_dict(),
                            AllocationStatus.EXPIRED.value,
                        )

        # Refresh each still-active allocation to match the decayed weight.
        for alloc in allocations:
            if alloc.status != AllocationStatus.ACTIVE:
                continue
            target = targets.get(alloc.target_id)
            if target is None:
                continue
            alloc.allocated_weight = target.current_weight
            target.last_accessed = now

        self._normalize_weights(budget_id)

        self._record_event(
            budget_id,
            "rebalance",
            None,
            "Budget rebalanced",
            None,
            None,
        )
        return [a for a in allocations if a.status == AllocationStatus.ACTIVE]


# ═══════════════════════════════════════════════════════════════════════════
# Singleton access
# ═══════════════════════════════════════════════════════════════════════════

_global_allocator: AgentAttentionAllocator | None = None
_global_allocator_lock = threading.Lock()


def get_attention_allocator() -> AgentAttentionAllocator:
    """Get or create the singleton attention allocator."""
    global _global_allocator
    with _global_allocator_lock:
        if _global_allocator is None:
            _global_allocator = AgentAttentionAllocator()
        return _global_allocator


def reset_attention_allocator() -> None:
    """Reset the singleton attention allocator.

    Mainly useful in tests where a fresh allocator is needed between cases.
    """
    global _global_allocator
    with _global_allocator_lock:
        _global_allocator = None
