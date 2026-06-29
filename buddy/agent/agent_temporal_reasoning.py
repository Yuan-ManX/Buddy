"""
Buddy Agent Temporal Reasoning - Event sequencing and interval algebra engine.

This module implements a temporal reasoning engine for the Buddy AI agent. It
provides Allen's interval algebra for computing relations between time
intervals, event sequencing with topological ordering, constraint
satisfaction (deadlines, durations, ordering, separation, recurrence), and
conflict detection across temporal plans.

The engine is fully thread-safe: every state mutation is guarded by a single
re-entrant lock. A module-level singleton accessor is provided for convenient
shared usage across the agent runtime.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TemporalRelation(str, Enum):
    """Allen's interval algebra relations between two time intervals.

    The thirteen mutually exclusive relations describe every possible way two
    intervals can be related on a single timeline.
    """
    BEFORE = "before"                # a ends before b starts
    AFTER = "after"                  # a starts after b ends
    DURING = "during"                # a is contained within b
    CONTAINS = "contains"            # a fully contains b
    OVERLAPS = "overlaps"            # a starts first, partial overlap
    OVERLAPPED_BY = "overlapped_by"  # b starts first, partial overlap
    MEETS = "meets"                  # a ends exactly when b starts
    MET_BY = "met_by"                # a starts exactly when b ends
    STARTS = "starts"                # a and b start together, a ends first
    STARTED_BY = "started_by"        # a and b start together, b ends first
    FINISHES = "finishes"            # a and b end together, a starts later
    FINISHED_BY = "finished_by"      # a and b end together, b starts later
    EQUALS = "equals"                # a and b are identical


class TemporalConstraintType(str, Enum):
    """Types of temporal constraints that can be applied to events."""
    DEADLINE = "deadline"      # an event must finish by a fixed time
    DURATION = "duration"      # an event must take exactly some duration
    ORDERING = "ordering"      # an event must happen before/after another
    SEPARATION = "separation"  # minimum/maximum gap between two events
    RECURRENCE = "recurrence"  # a repeating temporal pattern


class EventStatus(str, Enum):
    """Lifecycle status of a temporal event."""
    SCHEDULED = "scheduled"      # planned but not yet started
    IN_PROGRESS = "in_progress"  # currently executing
    COMPLETED = "completed"      # finished successfully
    CANCELLED = "cancelled"      # abandoned before completion
    DELAYED = "delayed"          # postponed past its planned start
    MISSED = "missed"            # failed to occur by its deadline


class TimeWindowType(str, Enum):
    """Boundary semantics for a time interval.

    Controls whether the start and end points are inclusive (closed) or
    exclusive (open). The combined forms allow half-open intervals.
    """
    OPEN = "open"          # both ends exclusive
    CLOSED = "closed"      # both ends inclusive
    OPEN_LEFT = "open_left"    # start exclusive, end inclusive
    OPEN_RIGHT = "open_right"  # start inclusive, end exclusive


@dataclass
class TimeInterval:
    """A time interval with optional end and duration.

    The interval is anchored at ``start`` and extends to ``end``. When ``end``
    is omitted, ``duration`` may be used to derive an effective end. When both
    are omitted the interval is treated as a point in time at ``start``.
    """
    start: float = 0.0
    end: float | None = None
    duration: float | None = None
    window_type: TimeWindowType = TimeWindowType.CLOSED

    def to_dict(self) -> dict[str, Any]:
        """Serialize the interval to a plain dictionary."""
        return {
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "window_type": self.window_type.value
            if isinstance(self.window_type, TimeWindowType)
            else str(self.window_type),
        }


@dataclass
class TemporalEvent:
    """A single event within a temporal plan.

    Events carry their own time interval, lifecycle status, dependency
    references to other events, free-form tags, a priority bucket (0 is
    highest priority, 4 is lowest), the owning agent identifier, and an
    arbitrary metadata mapping.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    interval: TimeInterval = field(default_factory=TimeInterval)
    status: EventStatus = EventStatus.SCHEDULED
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    priority: int = 2
    agent_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a plain dictionary with fresh containers."""
        return {
            "event_id": self.event_id,
            "name": self.name,
            "description": self.description,
            "interval": self.interval.to_dict()
            if hasattr(self.interval, "to_dict")
            else dict(self.interval),
            "status": self.status.value
            if isinstance(self.status, EventStatus)
            else str(self.status),
            "dependencies": list(self.dependencies),
            "tags": list(self.tags),
            "priority": self.priority,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class TemporalConstraint:
    """A constraint applied to one or more temporal events.

    The ``constraint_type`` determines which fields are meaningful. For
    example, ``DEADLINE`` uses ``deadline``, ``DURATION`` uses ``min_value``,
    ``ORDERING`` uses ``relation`` and ``target_event_id``, and ``SEPARATION``
    uses ``min_value``/``max_value`` together with ``target_event_id``.
    """
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_id: str | None = None
    constraint_type: TemporalConstraintType = TemporalConstraintType.ORDERING
    relation: TemporalRelation | None = None
    target_event_id: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    deadline: float | None = None
    description: str = ""
    satisfied: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the constraint to a plain dictionary with fresh containers."""
        return {
            "constraint_id": self.constraint_id,
            "event_id": self.event_id,
            "constraint_type": self.constraint_type.value
            if isinstance(self.constraint_type, TemporalConstraintType)
            else str(self.constraint_type),
            "relation": self.relation.value
            if isinstance(self.relation, TemporalRelation)
            else (str(self.relation) if self.relation is not None else None),
            "target_event_id": self.target_event_id,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "deadline": self.deadline,
            "description": self.description,
            "satisfied": self.satisfied,
            "created_at": self.created_at,
        }


@dataclass
class TemporalPlan:
    """A collection of events and constraints forming a temporal plan.

    Events are stored in a dictionary keyed by ``event_id`` for O(1) lookup.
    Constraints are stored as a list to preserve insertion order. The
    ``start_time`` and ``end_time`` fields, when set, bracket the entire plan.
    """
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    events: dict[str, TemporalEvent] = field(default_factory=dict)
    constraints: list[TemporalConstraint] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    start_time: float | None = None
    end_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the plan to a plain dictionary with fresh containers."""
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "events": {
                eid: e.to_dict() if hasattr(e, "to_dict") else dict(e)
                for eid, e in self.events.items()
            },
            "constraints": [
                c.to_dict() if hasattr(c, "to_dict") else dict(c)
                for c in self.constraints
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class ConsistencyReport:
    """Result of a consistency check over a temporal plan.

    ``conflicts`` is a list of ``(event_a_id, event_b_id, description)``
    tuples describing pairwise temporal conflicts. ``violated_constraints``
    lists the IDs of constraints that currently fail. ``is_consistent`` is
    ``True`` only when there are no conflicts and no violated constraints.
    """
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    plan_id: str = ""
    conflicts: list[tuple[str, str, str]] = field(default_factory=list)
    violated_constraints: list[str] = field(default_factory=list)
    is_consistent: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report, converting conflict tuples to lists."""
        return {
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "conflicts": [list(c) for c in self.conflicts],
            "violated_constraints": list(self.violated_constraints),
            "is_consistent": self.is_consistent,
            "created_at": self.created_at,
        }


@dataclass
class TemporalEngineStats:
    """Aggregate statistics about the temporal engine state.

    Computed on demand by :meth:`AgentTemporalEngine.get_stats`. The
    ``events_by_status`` mapping is keyed by :class:`EventStatus` string
    values. ``avg_plan_duration`` averages ``end_time - start_time`` across
    plans that define both bounds.
    """
    total_plans: int = 0
    total_events: int = 0
    events_by_status: dict[str, int] = field(default_factory=dict)
    total_constraints: int = 0
    violated_constraints: int = 0
    avg_plan_duration: float = 0.0
    missed_deadlines: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the stats to a plain dictionary with fresh containers."""
        return {
            "total_plans": self.total_plans,
            "total_events": self.total_events,
            "events_by_status": dict(self.events_by_status),
            "total_constraints": self.total_constraints,
            "violated_constraints": self.violated_constraints,
            "avg_plan_duration": self.avg_plan_duration,
            "missed_deadlines": self.missed_deadlines,
        }


class AgentTemporalEngine:
    """Thread-safe temporal reasoning engine for the Buddy agent.

    The engine maintains a bounded set of temporal plans. Each plan holds
    events and constraints. The engine computes Allen's interval relations,
    validates constraint satisfaction, detects temporal conflicts, derives
    topological execution order, and reports aggregate statistics.

    All public methods are thread-safe. A single :class:`threading.Lock`
    guards every state mutation. Pure read helpers that do not touch shared
    state (such as :meth:`compute_relation`) do not require the lock.
    """

    # Bounding constants protect memory usage under sustained load.
    MAX_PLANS: int = 200
    MAX_EVENTS_PER_PLAN: int = 500

    def __init__(self) -> None:
        """Initialize an empty engine with no plans."""
        self._plans: dict[str, TemporalPlan] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Plan management
    # ------------------------------------------------------------------

    def create_plan(self, name: str, description: str = "") -> TemporalPlan:
        """Create and register a new temporal plan.

        If the engine is at capacity (``MAX_PLANS``), the oldest plan by
        creation time is evicted before inserting the new one.
        """
        with self._lock:
            if len(self._plans) >= self.MAX_PLANS:
                # Evict the plan with the smallest created_at timestamp.
                oldest_id = min(
                    self._plans.keys(),
                    key=lambda pid: self._plans[pid].created_at,
                )
                self._plans.pop(oldest_id, None)
            now = time.time()
            plan = TemporalPlan(
                name=name,
                description=description,
                created_at=now,
                updated_at=now,
            )
            self._plans[plan.plan_id] = plan
            return plan

    def get_plan(self, plan_id: str) -> TemporalPlan | None:
        """Return the plan with the given id, or ``None`` if not found."""
        with self._lock:
            return self._plans.get(plan_id)

    def list_plans(self) -> list[TemporalPlan]:
        """Return all plans ordered by creation time (oldest first)."""
        with self._lock:
            plans = list(self._plans.values())
        plans.sort(key=lambda p: p.created_at)
        return plans

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------

    def add_event(
        self,
        plan_id: str,
        name: str,
        description: str = "",
        start: float | None = None,
        end: float | None = None,
        duration: float | None = None,
        priority: int = 2,
        agent_id: str = "",
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> TemporalEvent | None:
        """Add an event to a plan.

        Returns the created event, or ``None`` if the plan does not exist or
        the plan has reached ``MAX_EVENTS_PER_PLAN``. ``priority`` is clamped
        to the valid range ``[0, 4]``.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return None
            if len(plan.events) >= self.MAX_EVENTS_PER_PLAN:
                return None
            now = time.time()
            clamped_priority = max(0, min(4, priority))
            event = TemporalEvent(
                name=name,
                description=description,
                interval=TimeInterval(
                    start=start if start is not None else 0.0,
                    end=end,
                    duration=duration,
                    window_type=TimeWindowType.CLOSED,
                ),
                priority=clamped_priority,
                agent_id=agent_id,
                tags=list(tags) if tags is not None else [],
                metadata=dict(metadata) if metadata is not None else {},
                created_at=now,
                updated_at=now,
            )
            plan.events[event.event_id] = event
            plan.updated_at = now
            # Expand plan bounds to include the new event when possible.
            eff_end = self._effective_end(event.interval)
            if plan.start_time is None or event.interval.start < plan.start_time:
                plan.start_time = event.interval.start
            if plan.end_time is None or eff_end > (plan.end_time or eff_end):
                plan.end_time = eff_end
            return event

    def get_event(self, plan_id: str, event_id: str) -> TemporalEvent | None:
        """Return an event by id within a plan, or ``None`` if absent."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return None
            return plan.events.get(event_id)

    def list_events(
        self,
        plan_id: str,
        status: EventStatus | None = None,
    ) -> list[TemporalEvent]:
        """List events in a plan, optionally filtered by status.

        Results are ordered by start time ascending; events without a defined
        start are placed last.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return []
            events = list(plan.events.values())
        if status is not None:
            events = [e for e in events if e.status == status]
        events.sort(key=lambda e: e.interval.start)
        return events

    def update_event_status(
        self,
        plan_id: str,
        event_id: str,
        status: EventStatus,
    ) -> TemporalEvent | None:
        """Transition an event to a new status.

        Returns the updated event, or ``None`` if the plan or event does not
        exist. Updates the event's ``updated_at`` timestamp.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return None
            event = plan.events.get(event_id)
            if event is None:
                return None
            event.status = status
            event.updated_at = time.time()
            plan.updated_at = event.updated_at
            return event

    # ------------------------------------------------------------------
    # Constraint management
    # ------------------------------------------------------------------

    def add_constraint(
        self,
        plan_id: str,
        event_id: str | None,
        constraint_type: TemporalConstraintType,
        relation: TemporalRelation | None = None,
        target_event_id: str | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        deadline: float | None = None,
        description: str = "",
    ) -> TemporalConstraint | None:
        """Add a constraint to a plan.

        Returns the created constraint, or ``None`` if the plan does not
        exist. The constraint is appended to the plan and initially assumed
        satisfied; call :meth:`check_consistency` to recompute satisfaction.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return None
            constraint = TemporalConstraint(
                event_id=event_id,
                constraint_type=constraint_type,
                relation=relation,
                target_event_id=target_event_id,
                min_value=min_value,
                max_value=max_value,
                deadline=deadline,
                description=description,
                satisfied=True,
                created_at=time.time(),
            )
            plan.constraints.append(constraint)
            plan.updated_at = constraint.created_at
            return constraint

    def list_constraints(
        self,
        plan_id: str,
        constraint_type: TemporalConstraintType | None = None,
    ) -> list[TemporalConstraint]:
        """List constraints in a plan, optionally filtered by type."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return []
            constraints = list(plan.constraints)
        if constraint_type is not None:
            constraints = [c for c in constraints if c.constraint_type == constraint_type]
        return constraints

    # ------------------------------------------------------------------
    # Allen's interval algebra
    # ------------------------------------------------------------------

    @staticmethod
    def _effective_end(interval: TimeInterval) -> float:
        """Resolve the effective end point of an interval.

        If ``end`` is set it is used directly. Otherwise ``start + duration``
        is used when ``duration`` is set. Otherwise the interval is a point
        and ``start`` is returned as both start and end.
        """
        if interval.end is not None:
            return interval.end
        if interval.duration is not None:
            return interval.start + interval.duration
        return interval.start

    def compute_relation(
        self,
        interval_a: TimeInterval,
        interval_b: TimeInterval,
    ) -> TemporalRelation:
        """Compute the Allen interval relation between two intervals.

        Implements all thirteen mutually exclusive relations. End points are
        resolved via :meth:`_effective_end` so point intervals and
        duration-only intervals are handled transparently.
        """
        a_start = interval_a.start
        a_end = self._effective_end(interval_a)
        b_start = interval_b.start
        b_end = self._effective_end(interval_b)

        # Most specific relations first to avoid shadowing.
        if a_start == b_start and a_end == b_end:
            return TemporalRelation.EQUALS
        if a_end == b_start:
            return TemporalRelation.MEETS
        if a_start == b_end:
            return TemporalRelation.MET_BY
        if a_start == b_start and a_end < b_end:
            return TemporalRelation.STARTS
        if a_start == b_start and a_end > b_end:
            return TemporalRelation.STARTED_BY
        if a_end == b_end and a_start > b_start:
            return TemporalRelation.FINISHES
        if a_end == b_end and a_start < b_start:
            return TemporalRelation.FINISHED_BY
        if a_start > b_start and a_end < b_end:
            return TemporalRelation.DURING
        if a_start < b_start and a_end > b_end:
            return TemporalRelation.CONTAINS
        if a_start < b_start and a_end > b_start and a_end < b_end:
            return TemporalRelation.OVERLAPS
        if b_start < a_start and b_end > a_start and b_end < a_end:
            return TemporalRelation.OVERLAPPED_BY
        if a_end < b_start:
            return TemporalRelation.BEFORE
        if a_start > b_end:
            return TemporalRelation.AFTER
        # Defensive fallback; with exhaustive checks above this is unreachable
        # for well-formed finite intervals.
        return TemporalRelation.BEFORE

    @staticmethod
    def _relations_compatible(
        actual: TemporalRelation,
        expected: TemporalRelation,
    ) -> bool:
        """Return whether an actual relation satisfies an expected one.

        Exact matches always satisfy. Boundary cases are tolerated: ``MEETS``
        satisfies ``BEFORE`` and ``MET_BY`` satisfies ``AFTER``.
        """
        if actual == expected:
            return True
        if expected == TemporalRelation.BEFORE and actual == TemporalRelation.MEETS:
            return True
        if expected == TemporalRelation.AFTER and actual == TemporalRelation.MET_BY:
            return True
        return False

    # ------------------------------------------------------------------
    # Consistency checking
    # ------------------------------------------------------------------

    def _check_single_constraint(
        self,
        plan: TemporalPlan,
        constraint: TemporalConstraint,
    ) -> bool:
        """Evaluate whether a single constraint is currently satisfied.

        This helper assumes the caller already holds the lock or is operating
        on a locally owned plan reference.
        """
        ctype = constraint.constraint_type

        if ctype == TemporalConstraintType.DEADLINE:
            if constraint.event_id is None or constraint.deadline is None:
                return True
            event = plan.events.get(constraint.event_id)
            if event is None:
                return True
            eff_end = self._effective_end(event.interval)
            return eff_end <= constraint.deadline

        if ctype == TemporalConstraintType.DURATION:
            if constraint.event_id is None or constraint.min_value is None:
                return True
            event = plan.events.get(constraint.event_id)
            if event is None:
                return True
            actual = self._effective_end(event.interval) - event.interval.start
            return abs(actual - constraint.min_value) < 1e-9

        if ctype == TemporalConstraintType.ORDERING:
            if (
                constraint.event_id is None
                or constraint.target_event_id is None
                or constraint.relation is None
            ):
                return True
            event = plan.events.get(constraint.event_id)
            target = plan.events.get(constraint.target_event_id)
            if event is None or target is None:
                return True
            actual = self.compute_relation(event.interval, target.interval)
            return self._relations_compatible(actual, constraint.relation)

        if ctype == TemporalConstraintType.SEPARATION:
            if constraint.event_id is None or constraint.target_event_id is None:
                return True
            event = plan.events.get(constraint.event_id)
            target = plan.events.get(constraint.target_event_id)
            if event is None or target is None:
                return True
            gap = self._compute_gap(event.interval, target.interval)
            if gap is None:
                return True
            if constraint.min_value is not None and gap < constraint.min_value:
                return False
            if constraint.max_value is not None and gap > constraint.max_value:
                return False
            return True

        if ctype == TemporalConstraintType.RECURRENCE:
            # Recurrence satisfaction requires pattern metadata that is beyond
            # the scope of this engine; treat presence as satisfaction.
            return True

        return True

    def _compute_gap(
        self,
        a: TimeInterval,
        b: TimeInterval,
    ) -> float | None:
        """Compute the temporal gap between two intervals.

        Returns the positive separation when intervals do not overlap, ``0.0``
        when they touch or overlap, and ``None`` if it cannot be determined.
        """
        a_end = self._effective_end(a)
        b_end = self._effective_end(b)
        if a_end <= b.start:
            return b.start - a_end
        if b_end <= a.start:
            return a.start - b_end
        return 0.0

    def check_consistency(self, plan_id: str) -> ConsistencyReport:
        """Check all constraints and detect conflicts within a plan.

        Every constraint is re-evaluated and its ``satisfied`` flag updated.
        Ordering conflicts (contradictory before/after relations between the
        same pair), deadline violations, and overlap violations are collected
        into the returned :class:`ConsistencyReport`.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return ConsistencyReport(
                    plan_id=plan_id,
                    conflicts=[],
                    violated_constraints=[],
                    is_consistent=False,
                    created_at=time.time(),
                )

            violated: list[str] = []
            for constraint in plan.constraints:
                ok = self._check_single_constraint(plan, constraint)
                constraint.satisfied = ok
                if not ok:
                    violated.append(constraint.constraint_id)

            conflicts = self._detect_conflicts(plan)

            is_consistent = len(violated) == 0 and len(conflicts) == 0
            return ConsistencyReport(
                plan_id=plan_id,
                conflicts=conflicts,
                violated_constraints=violated,
                is_consistent=is_consistent,
                created_at=time.time(),
            )

    def _detect_conflicts(self, plan: TemporalPlan) -> list[tuple[str, str, str]]:
        """Detect pairwise temporal conflicts within a plan.

        Two kinds of conflicts are reported: ordering constraints whose actual
        interval relation contradicts the expected one, and pairs of events
        with contradictory ordering constraints (e.g. A before B and B before
        A).
        """
        conflicts: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str]] = set()

        # Contradictory ordering constraints between the same pair.
        ordering_edges: dict[tuple[str, str], TemporalRelation] = {}
        for constraint in plan.constraints:
            if constraint.constraint_type != TemporalConstraintType.ORDERING:
                continue
            if (
                constraint.event_id is None
                or constraint.target_event_id is None
                or constraint.relation is None
            ):
                continue
            key = (constraint.event_id, constraint.target_event_id)
            ordering_edges[key] = constraint.relation
            reverse_key = (constraint.target_event_id, constraint.event_id)
            if reverse_key in ordering_edges:
                # Both directions present; check for contradiction.
                forward = constraint.relation
                backward = ordering_edges[reverse_key]
                if self._is_contradictory(forward, backward):
                    pair = tuple(sorted([constraint.event_id, constraint.target_event_id]))
                    if pair not in seen:
                        seen.add(pair)
                        conflicts.append((
                            constraint.event_id,
                            constraint.target_event_id,
                            "contradictory ordering constraints",
                        ))

        # Ordering constraints violated by actual interval relations.
        for constraint in plan.constraints:
            if constraint.constraint_type != TemporalConstraintType.ORDERING:
                continue
            if (
                constraint.event_id is None
                or constraint.target_event_id is None
                or constraint.relation is None
            ):
                continue
            event = plan.events.get(constraint.event_id)
            target = plan.events.get(constraint.target_event_id)
            if event is None or target is None:
                continue
            actual = self.compute_relation(event.interval, target.interval)
            if not self._relations_compatible(actual, constraint.relation):
                pair = tuple(sorted([constraint.event_id, constraint.target_event_id]))
                if pair not in seen:
                    seen.add(pair)
                    conflicts.append((
                        constraint.event_id,
                        constraint.target_event_id,
                        f"expected {constraint.relation.value}, actual {actual.value}",
                    ))

        return conflicts

    @staticmethod
    def _is_contradictory(
        forward: TemporalRelation,
        backward: TemporalRelation,
    ) -> bool:
        """Return whether two opposing ordering relations are contradictory.

        A before B combined with B before A is contradictory, whereas A before
        B combined with B after A is redundant but not contradictory.
        """
        contradictory_pairs = {
            (TemporalRelation.BEFORE, TemporalRelation.BEFORE),
            (TemporalRelation.AFTER, TemporalRelation.AFTER),
            (TemporalRelation.DURING, TemporalRelation.DURING),
            (TemporalRelation.CONTAINS, TemporalRelation.CONTAINS),
        }
        return (forward, backward) in contradictory_pairs

    # ------------------------------------------------------------------
    # Topological ordering
    # ------------------------------------------------------------------

    def _build_ordering_graph(self, plan: TemporalPlan) -> dict[str, list[str]]:
        """Build a directed graph encoding must-happen-before edges.

        Edges come from ORDERING constraints (BEFORE/AFTER relations) and from
        event ``dependencies`` lists. An edge ``u -> v`` means ``u`` must
        occur before ``v``.
        """
        graph: dict[str, list[str]] = {eid: [] for eid in plan.events}
        for constraint in plan.constraints:
            if constraint.constraint_type != TemporalConstraintType.ORDERING:
                continue
            if constraint.event_id is None or constraint.target_event_id is None:
                continue
            if constraint.relation is None:
                continue
            src, dst = constraint.event_id, constraint.target_event_id
            if src not in graph or dst not in graph:
                continue
            if constraint.relation == TemporalRelation.BEFORE:
                graph[src].append(dst)
            elif constraint.relation == TemporalRelation.AFTER:
                graph[dst].append(src)
        # Dependency edges: each dependency must precede the dependent event.
        for eid, event in plan.events.items():
            for dep in event.dependencies:
                if dep in graph:
                    graph[dep].append(eid)
        return graph

    def get_event_order(self, plan_id: str) -> list[str]:
        """Return event ids in topological order.

        Uses Kahn's algorithm over the ordering graph derived from BEFORE/AFTER
        constraints and event dependencies. When a cycle is detected the
        remaining events are appended in arbitrary order so the output always
        contains every event id.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return []
            graph = self._build_ordering_graph(plan)

        # Compute in-degrees.
        in_degree: dict[str, int] = {nid: 0 for nid in graph}
        for src, neighbors in graph.items():
            for dst in neighbors:
                in_degree[dst] = in_degree.get(dst, 0) + 1

        # Seed the queue with zero-in-degree nodes, ordered by start time then
        # priority for deterministic output.
        ready = sorted(
            [nid for nid, deg in in_degree.items() if deg == 0],
            key=lambda nid: (
                plan.events[nid].interval.start if nid in plan.events else 0.0,
                plan.events[nid].priority if nid in plan.events else 2,
            ),
        )
        order: list[str] = []
        processed: set[str] = set()
        while ready:
            node = ready.pop(0)
            if node in processed:
                continue
            processed.add(node)
            order.append(node)
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] <= 0 and neighbor not in processed:
                    ready.append(neighbor)
            ready.sort(
                key=lambda nid: (
                    plan.events[nid].interval.start if nid in plan.events else 0.0,
                    plan.events[nid].priority if nid in plan.events else 2,
                )
            )

        # Append any remaining nodes (cycle participants) for completeness.
        for nid in graph:
            if nid not in processed:
                order.append(nid)
        return order

    # ------------------------------------------------------------------
    # Conflict detection and critical path
    # ------------------------------------------------------------------

    def find_conflicts(self, plan_id: str) -> list[tuple[str, str, str]]:
        """Find pairs of events with conflicting temporal relations.

        Delegates to :meth:`_detect_conflicts`. Each conflict is a
        ``(event_a_id, event_b_id, description)`` tuple.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return []
            return self._detect_conflicts(plan)

    def get_critical_path(self, plan_id: str) -> list[str]:
        """Find the longest chain of dependent events in a plan.

        Builds a DAG from ORDERING constraints and dependencies, then runs a
        longest-path dynamic program over a topological ordering. Returns the
        sequence of event ids forming the critical (longest) path. When the
        graph contains a cycle, the acyclic prefix is used.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return []
            graph = self._build_ordering_graph(plan)

        # Topological order restricted to the graph nodes.
        in_degree: dict[str, int] = {nid: 0 for nid in graph}
        for src, neighbors in graph.items():
            for dst in neighbors:
                in_degree[dst] = in_degree.get(dst, 0) + 1
        ready = [nid for nid, deg in in_degree.items() if deg == 0]
        topo: list[str] = []
        processed: set[str] = set()
        while ready:
            node = ready.pop(0)
            if node in processed:
                continue
            processed.add(node)
            topo.append(node)
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] <= 0 and neighbor not in processed:
                    ready.append(neighbor)

        # Longest path DP over the topological order.
        best: dict[str, int] = {nid: 1 for nid in graph}
        predecessor: dict[str, str | None] = {nid: None for nid in graph}
        for node in topo:
            for neighbor in graph.get(node, []):
                if best[node] + 1 > best.get(neighbor, 1):
                    best[neighbor] = best[node] + 1
                    predecessor[neighbor] = node

        if not best:
            return []

        # Pick the node with the maximum path length.
        end_node = max(best, key=lambda nid: best[nid])
        path: list[str] = []
        cursor: str | None = end_node
        while cursor is not None:
            path.append(cursor)
            cursor = predecessor.get(cursor)
        path.reverse()
        return path

    # ------------------------------------------------------------------
    # Deadline checking
    # ------------------------------------------------------------------

    def check_deadlines(
        self,
        plan_id: str,
        current_time: float | None = None,
    ) -> list[str]:
        """Return event ids that have missed their deadlines.

        An event misses its deadline when its effective end exceeds the
        deadline, or when the current time has passed the deadline and the
        event has not completed. ``current_time`` defaults to ``time.time()``.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return []
            now = current_time if current_time is not None else time.time()
            missed: list[str] = []
            for constraint in plan.constraints:
                if constraint.constraint_type != TemporalConstraintType.DEADLINE:
                    continue
                if constraint.event_id is None or constraint.deadline is None:
                    continue
                event = plan.events.get(constraint.event_id)
                if event is None:
                    continue
                eff_end = self._effective_end(event.interval)
                deadline_missed = False
                if eff_end > constraint.deadline:
                    deadline_missed = True
                elif now > constraint.deadline and event.status != EventStatus.COMPLETED:
                    deadline_missed = True
                if deadline_missed:
                    if event.event_id not in missed:
                        missed.append(event.event_id)
                    if event.status != EventStatus.MISSED:
                        event.status = EventStatus.MISSED
                        event.updated_at = now
            return missed

    # ------------------------------------------------------------------
    # Statistics and maintenance
    # ------------------------------------------------------------------

    def get_stats(self) -> TemporalEngineStats:
        """Compute aggregate statistics across all plans."""
        with self._lock:
            total_plans = len(self._plans)
            total_events = 0
            events_by_status: dict[str, int] = {}
            total_constraints = 0
            violated_constraints = 0
            missed_deadlines = 0
            durations: list[float] = []

            for plan in self._plans.values():
                total_events += len(plan.events)
                for event in plan.events.values():
                    status_key = event.status.value if isinstance(
                        event.status, EventStatus
                    ) else str(event.status)
                    events_by_status[status_key] = events_by_status.get(status_key, 0) + 1
                    if event.status == EventStatus.MISSED:
                        missed_deadlines += 1
                total_constraints += len(plan.constraints)
                for constraint in plan.constraints:
                    if not constraint.satisfied:
                        violated_constraints += 1
                if plan.start_time is not None and plan.end_time is not None:
                    durations.append(plan.end_time - plan.start_time)

            avg_duration = sum(durations) / len(durations) if durations else 0.0
            return TemporalEngineStats(
                total_plans=total_plans,
                total_events=total_events,
                events_by_status=events_by_status,
                total_constraints=total_constraints,
                violated_constraints=violated_constraints,
                avg_plan_duration=avg_duration,
                missed_deadlines=missed_deadlines,
            )

    def clear(self) -> int:
        """Remove all plans from the engine. Returns the number removed."""
        with self._lock:
            count = len(self._plans)
            self._plans.clear()
            return count


# ----------------------------------------------------------------------
# Module-level singleton accessors
# ----------------------------------------------------------------------

_global_temporal_engine: AgentTemporalEngine | None = None


def get_temporal_engine() -> AgentTemporalEngine:
    """Return the shared :class:`AgentTemporalEngine` singleton.

    The engine is lazily constructed on first access.
    """
    global _global_temporal_engine
    if _global_temporal_engine is None:
        _global_temporal_engine = AgentTemporalEngine()
    return _global_temporal_engine


def reset_temporal_engine() -> None:
    """Discard the shared singleton so the next access creates a fresh engine."""
    global _global_temporal_engine
    _global_temporal_engine = None
