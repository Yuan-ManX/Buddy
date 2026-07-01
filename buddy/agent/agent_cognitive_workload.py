# Agent Cognitive Workload — measurement and management of an agent's
# cognitive effort budget across the three load types of Cognitive Load
# Theory: intrinsic, extraneous, and germane.
#
# Cognitive effort is finite. Any agent that reasons, holds context, and
# pursues goals draws on a bounded pool of working-memory resources, and
# when the demand on that pool exceeds its capacity the agent's
# performance degrades: reasoning shallows, context is dropped, and
# errors compound. Cognitive Load Theory separates that demand into three
# components. Intrinsic load is the difficulty inherent in the material
# itself, driven by element complexity (how many distinct elements a task
# contains) and element interactivity (how tightly those elements must be
# processed together). Extraneous load is the overhead imposed by how
# the task is presented — redundant context, confusing structure,
# distracting side-channels — and is the most reducible form of load.
# Germane load is the productive effort devoted to building and
# automating schemas; it is the load the agent wants to keep. Total load
# is their sum, compared against a capacity envelope to classify the
# agent as underloaded, optimal, loaded, overloaded, or saturated.
#
# This engine models that process operationally. Each LoadMeasurement
# records one observed load value of one type for an agent, annotated
# with the source task and the element complexity and interactivity that
# drove it. A WorkloadSnapshot aggregates the most recent measurements
# into the agent's current intrinsic, extraneous, and germane loads,
# derives the total load, and classifies the workload state against the
# capacity envelope. When two tasks run concurrently they may compete for
# the same cognitive channel (language, memory, vision, spatial,
# reasoning, ...); an InterferenceAssessment estimates that dual-task
# interference from keyword and channel overlap. When the agent is
# overloaded, an AllocationDecision redistributes cognitive resources via
# strategies such as shedding, deferring, delegating, chunking,
# sequencing, or offloading work, each freeing a characteristic amount of
# capacity. A RecoveryPlan prescribes how an overloaded agent recovers —
# pausing, breathing, consolidating, simplifying, or archiving. A
# WorkloadProfile holds each agent's capacity envelope and adaptation
# parameters, and WorkloadStats summarizes engine activity. All state
# mutations are guarded by a reentrant lock so the engine is safe to call
# from multiple threads, including from within its own methods.
#
# Architecture:
#     AgentCognitiveWorkload (singleton)
#     ├── LoadMeasurement        (one observed load value of one type)
#     ├── WorkloadSnapshot       (aggregate state of an agent's workload)
#     ├── InterferenceAssessment (dual-task interference estimate)
#     ├── AllocationDecision     (a resource redistribution choice)
#     ├── RecoveryPlan           (a plan to recover from overload)
#     ├── WorkloadProfile        (per-agent capacity and adaptation)
#     └── WorkloadStats          (aggregate engine statistics)

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class LoadType(str, Enum):
    """The kind of cognitive load a measurement records.

    Cognitive Load Theory partitions mental effort into three components.
    INTRINSIC load is the difficulty inherent in the material, driven by
    element complexity and interactivity. EXTRANEOUS load is overhead
    imposed by how the task is presented and is, in principle, reducible.
    GERMANE load is the productive effort devoted to building and
    automating schemas — the load the agent wants to keep.
    """
    INTRINSIC = "intrinsic"    # difficulty inherent in the material
    EXTRANEOUS = "extraneous"  # overhead from presentation/structure
    GERMANE = "germane"        # productive schema-construction effort


class WorkloadState(str, Enum):
    """The workload state of an agent at a point in time.

    States are ordered by capacity usage. UNDERLOADED means the agent has
    too little demand and is likely disengaged or underutilized. OPTIMAL
    means demand is well-matched to capacity. LOADED means the agent is
    busy but still effective. OVERLOADED means demand exceeds the
    comfortable band and performance is beginning to degrade. SATURATED
    means demand has exhausted capacity and the agent cannot take on
    more without shedding. RECOVERING means the agent has been taken
    offline to consolidate after an overload event.
    """
    UNDERLOADED = "underloaded"  # demand below the useful band
    OPTIMAL = "optimal"          # demand well-matched to capacity
    LOADED = "loaded"            # busy but effective
    OVERLOADED = "overloaded"    # past the comfortable band
    SATURATED = "saturated"      # capacity exhausted
    RECOVERING = "recovering"    # offline for consolidation


class InterferenceType(str, Enum):
    """The severity of dual-task interference between two concurrent tasks.

    When two tasks compete for the same cognitive resource, performance
    on one or both degrades. NONE means the tasks draw on independent
    resources and can run in parallel without cost. WEAK means minor
    competition with negligible cost. MODERATE means measurable
    competition that begins to slow one or both tasks. STRONG means
    substantial competition requiring care to schedule. SEVERE means the
    tasks are effectively incompatible and should not run concurrently.
    """
    NONE = "none"            # independent resources
    WEAK = "weak"            # minor competition
    MODERATE = "moderate"    # measurable competition
    STRONG = "strong"        # substantial competition
    SEVERE = "severe"        # effectively incompatible


class AllocationStrategy(str, Enum):
    """How cognitive resources are redistributed to relieve overload.

    Each strategy frees a different characteristic amount of capacity.
    SHED drops a task entirely, freeing the most but losing the work.
    DEFER postpones a task to a later, less-loaded moment. DELEGATE hands
    a task to another agent or sub-agent. CHUNK breaks a large task into
    smaller steps that can be processed serially. SEQUENCE serializes
    concurrent tasks to remove dual-task interference. OFFLOAD moves task
    state out of working memory into an external store or tool.
    """
    SHED = "shed"            # drop a task entirely
    DEFER = "defer"          # postpone to a less-loaded moment
    DELEGATE = "delegate"    # hand off to another agent
    CHUNK = "chunk"          # break into smaller serial steps
    SEQUENCE = "sequence"    # serialize concurrent tasks
    OFFLOAD = "offload"      # move state to an external store


class RecoveryAction(str, Enum):
    """A recovery action an overloaded agent takes to return to capacity.

    PAUSE halts processing for a short interval to let transients settle.
    BREATH slows the reasoning cadence and reduces context churn.
    CONSOLIDATE compresses working memory and persists intermediate state.
    SIMPLIFY drops extraneous sub-goals and uses simpler heuristics.
    ARCHIVE offloads completed items to long-term storage and reclaims
    working-memory slots.
    """
    PAUSE = "pause"            # halt processing briefly
    BREATH = "breath"          # slow the reasoning cadence
    CONSOLIDATE = "consolidate"  # compress and persist working memory
    SIMPLIFY = "simplify"      # drop extraneous sub-goals
    ARCHIVE = "archive"        # offload completed items


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a measurement/snapshot/etc."""
    return str(uuid.uuid4())[:8]


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"intrinsic"``) and then against member names
    (e.g. ``"INTRINSIC"``), so callers may pass either form. Raises
    ``ValueError`` if neither matches.
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            pass
        try:
            return enum_cls[value]
        except KeyError:
            pass
    raise ValueError(f"{value!r} is not a valid {enum_cls.__name__}")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _enum_value(enum_cls: type, value: Any) -> str:
    """Return the ``.value`` of an enum member, or a string fallback.

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


# Cognitive channels used for dual-task interference estimation. Each
# channel maps to a set of keyword cues; if two tasks both touch the same
# channel they compete for the same cognitive resource and interference
# is at least MODERATE.
_COGNITIVE_CHANNELS: Dict[str, List[str]] = {
    "language": [
        "language", "text", "linguistic", "verbal", "word", "reading",
        "writing", "translation", "nlp", "prompt",
    ],
    "memory": [
        "memory", "recall", "retrieval", "storage", "remember",
        "retention", "cache", "context",
    ],
    "vision": [
        "vision", "visual", "image", "picture", "ocr", "render",
        "diagram",
    ],
    "spatial": [
        "spatial", "geometry", "location", "navigation", "map", "layout",
        "position",
    ],
    "motor": [
        "motor", "action", "movement", "tool", "manipulation",
        "execution", "typing",
    ],
    "attention": [
        "attention", "focus", "monitor", "search", "vigilance", "scan",
        "watch",
    ],
    "reasoning": [
        "reasoning", "logic", "inference", "deduction", "planning",
        "analysis", "proof",
    ],
    "numeric": [
        "numeric", "math", "arithmetic", "calculation", "number",
        "quantitative", "statistics",
    ],
    "auditory": [
        "auditory", "sound", "audio", "speech", "music", "voice",
        "transcription",
    ],
}

# Generic tokens that should not count toward keyword overlap.
_STOPWORDS = {
    "task", "tasks", "the", "a", "an", "of", "for", "and", "to", "in",
    "on", "with", "by", "is", "are", "this", "that",
}


def _channels_for(task: str) -> set:
    """Return the set of cognitive channels a task name touches."""
    tokens = (task or "").lower().split()
    channels: set = set()
    for channel, keywords in _COGNITIVE_CHANNELS.items():
        for kw in keywords:
            if kw in tokens or any(kw in t for t in tokens):
                channels.add(channel)
                break
    return channels


def _content_tokens(task: str) -> set:
    """Tokenize a task name into lowercase content tokens, dropping stopwords."""
    return {
        t for t in (task or "").lower().split()
        if t and t not in _STOPWORDS
    }


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LoadMeasurement:
    """One observed cognitive load value of one type for one agent.

    A load measurement records a single ``value`` in [0, 1] of one
    ``load_type`` (intrinsic, extraneous, or germane) attributed to a
    ``source_task``. ``element_complexity`` captures how many distinct
    elements the task comprises; ``element_interactivity`` captures how
    tightly those elements must be processed together. Together these two
    factors drive the intrinsic load a task imposes: high complexity with
    high interactivity is the most demanding combination. ``measured_at``
    is an ISO-8601 UTC timestamp set at creation.
    """
    measurement_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    load_type: LoadType = LoadType.INTRINSIC
    value: float = 0.0
    source_task: str = ""
    element_complexity: float = 0.5
    element_interactivity: float = 0.5
    measured_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this measurement to a plain dict, expanding the enum."""
        return {
            "measurement_id": self.measurement_id,
            "agent_id": self.agent_id,
            "load_type": _enum_value(LoadType, self.load_type),
            "value": self.value,
            "source_task": self.source_task,
            "element_complexity": self.element_complexity,
            "element_interactivity": self.element_interactivity,
            "measured_at": self.measured_at,
        }


@dataclass
class WorkloadSnapshot:
    """A point-in-time summary of an agent's cognitive workload.

    A snapshot aggregates the agent's most recent measurements into the
    three load components and the ``total_load`` (their sum). The
    ``state`` classifies the agent against its capacity envelope.
    ``capacity_used`` is the raw total load and may exceed
    ``capacity_total`` when the agent is saturated. ``interference`` is
    the dual-task interference level implied by ``active_tasks``.
    ``measured_at`` is an ISO-8601 UTC timestamp set at creation.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    intrinsic_load: float = 0.0
    extraneous_load: float = 0.0
    germane_load: float = 0.0
    total_load: float = 0.0
    state: WorkloadState = WorkloadState.OPTIMAL
    capacity_used: float = 0.0
    capacity_total: float = 1.0
    interference: InterferenceType = InterferenceType.NONE
    active_tasks: int = 1
    measured_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "intrinsic_load": self.intrinsic_load,
            "extraneous_load": self.extraneous_load,
            "germane_load": self.germane_load,
            "total_load": self.total_load,
            "state": _enum_value(WorkloadState, self.state),
            "capacity_used": self.capacity_used,
            "capacity_total": self.capacity_total,
            "interference": _enum_value(InterferenceType, self.interference),
            "active_tasks": self.active_tasks,
            "measured_at": self.measured_at,
        }


@dataclass
class InterferenceAssessment:
    """An estimate of dual-task interference between two concurrent tasks.

    When two tasks run at once they may compete for the same cognitive
    resource. ``interference_type`` is the severity band;
    ``interference_score`` in [0, 1] is the underlying continuous estimate.
    ``mutual_channel`` is True when both tasks touch the same cognitive
    channel (e.g. both are language tasks), which forces interference to
    at least MODERATE. ``resource_conflict`` names the shared channel(s),
    or ``"none"`` when the tasks draw on independent resources.
    """
    assessment_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    primary_task: str = ""
    secondary_task: str = ""
    interference_type: InterferenceType = InterferenceType.NONE
    interference_score: float = 0.0
    mutual_channel: bool = False
    resource_conflict: str = "none"
    assessed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this assessment to a plain dict, expanding the enum."""
        return {
            "assessment_id": self.assessment_id,
            "agent_id": self.agent_id,
            "primary_task": self.primary_task,
            "secondary_task": self.secondary_task,
            "interference_type": _enum_value(InterferenceType, self.interference_type),
            "interference_score": self.interference_score,
            "mutual_channel": self.mutual_channel,
            "resource_conflict": self.resource_conflict,
            "assessed_at": self.assessed_at,
        }


@dataclass
class AllocationDecision:
    """A choice to redistribute cognitive resources to relieve overload.

    ``strategy`` is the allocation strategy applied to ``target_task``.
    ``freed_capacity`` is the amount of capacity the strategy is expected
    to free, bounded by the load the task actually contributed.
    ``rationale`` is a free-form explanation of why the strategy was
    chosen. ``applied_at`` is an ISO-8601 UTC timestamp set at creation.
    """
    decision_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    strategy: AllocationStrategy = AllocationStrategy.SHED
    target_task: str = ""
    rationale: str = ""
    freed_capacity: float = 0.0
    applied_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this decision to a plain dict, expanding the enum."""
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(AllocationStrategy, self.strategy),
            "target_task": self.target_task,
            "rationale": self.rationale,
            "freed_capacity": self.freed_capacity,
            "applied_at": self.applied_at,
        }


@dataclass
class RecoveryPlan:
    """A plan for an overloaded agent to recover back to capacity.

    ``action`` is the recovery action to take; ``duration_estimate`` is
    the expected recovery time in seconds; ``expected_relief`` in [0, 1]
    is the amount of load the action is expected to shed; ``steps`` is an
    ordered list of concrete recovery steps. ``created_at`` is an
    ISO-8601 UTC timestamp set at creation.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    action: RecoveryAction = RecoveryAction.PAUSE
    duration_estimate: float = 60.0
    expected_relief: float = 0.3
    steps: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, copying the steps list."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "action": _enum_value(RecoveryAction, self.action),
            "duration_estimate": self.duration_estimate,
            "expected_relief": self.expected_relief,
            "steps": list(self.steps),
            "created_at": self.created_at,
        }


@dataclass
class WorkloadProfile:
    """Per-agent capacity envelope and adaptation parameters.

    ``baseline_capacity`` is the agent's normal working-memory envelope;
    ``peak_capacity`` is the short-burst maximum it can sustain.
    ``adaptation_rate`` controls how quickly the envelope adjusts to
    observed demand. ``overload_threshold`` is the capacity-used fraction
    above which proactive load shedding is warranted;
    ``underload_threshold`` is the fraction below which the agent is
    considered underutilized. The aggregate fields (``total_measurements``,
    ``avg_intrinsic``, ``avg_extraneous``, ``avg_germane``,
    ``state_distribution``) are recomputed from the engine's records and
    describe the agent's recent workload history.
    """
    agent_id: str = ""
    baseline_capacity: float = 1.0
    peak_capacity: float = 1.2
    adaptation_rate: float = 0.1
    overload_threshold: float = 0.85
    underload_threshold: float = 0.3
    total_measurements: int = 0
    avg_intrinsic: float = 0.0
    avg_extraneous: float = 0.0
    avg_germane: float = 0.0
    state_distribution: Dict[WorkloadState, int] = field(default_factory=dict)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict.

        The ``state_distribution`` dict is rebuilt with enum ``.value``
        string keys so the serialized form is JSON-clean and independent
        of the live profile.
        """
        state_out: Dict[str, int] = {}
        for key, val in self.state_distribution.items():
            key_str = key.value if isinstance(key, WorkloadState) else str(key)
            state_out[key_str] = val
        return {
            "agent_id": self.agent_id,
            "baseline_capacity": self.baseline_capacity,
            "peak_capacity": self.peak_capacity,
            "adaptation_rate": self.adaptation_rate,
            "overload_threshold": self.overload_threshold,
            "underload_threshold": self.underload_threshold,
            "total_measurements": self.total_measurements,
            "avg_intrinsic": self.avg_intrinsic,
            "avg_extraneous": self.avg_extraneous,
            "avg_germane": self.avg_germane,
            "state_distribution": state_out,
            "updated_at": self.updated_at,
        }


@dataclass
class WorkloadStats:
    """Aggregate statistics over the workload engine's state.

    Counts of snapshots, assessments, decisions, and recovery plans, plus
    two breakdown dicts (``state_distribution`` and
    ``interference_distribution``) that tally snapshots by state and
    assessments by interference type. ``avg_total_load`` is the mean total
    load over the currently held snapshots (0.0 when none exist).
    ``overload_events`` counts every snapshot whose state was OVERLOADED
    or SATURATED, cumulatively across the engine's lifetime.
    """
    total_snapshots: int = 0
    total_assessments: int = 0
    total_decisions: int = 0
    total_recoveries: int = 0
    state_distribution: Dict[WorkloadState, int] = field(default_factory=dict)
    avg_total_load: float = 0.0
    overload_events: int = 0
    interference_distribution: Dict[InterferenceType, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict with JSON-clean keys."""
        state_out: Dict[str, int] = {}
        for key, val in self.state_distribution.items():
            key_str = key.value if isinstance(key, WorkloadState) else str(key)
            state_out[key_str] = val
        interference_out: Dict[str, int] = {}
        for key, val in self.interference_distribution.items():
            key_str = key.value if isinstance(key, InterferenceType) else str(key)
            interference_out[key_str] = val
        return {
            "total_snapshots": self.total_snapshots,
            "total_assessments": self.total_assessments,
            "total_decisions": self.total_decisions,
            "total_recoveries": self.total_recoveries,
            "state_distribution": state_out,
            "avg_total_load": self.avg_total_load,
            "overload_events": self.overload_events,
            "interference_distribution": interference_out,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveWorkload:
    """Cognitive workload engine with measurements, snapshots, and plans.

    The engine maintains registries of load measurements, workload
    snapshots, interference assessments, allocation decisions, recovery
    plans, and per-agent workload profiles. Load measurements are
    aggregated into snapshots that classify the agent's state against its
    capacity envelope. Dual-task interference is estimated from keyword
    and cognitive-channel overlap. Allocation decisions redistribute
    cognitive resources to relieve overload, and recovery plans prescribe
    how an overloaded agent returns to capacity. Cumulative counters in
    ``_stats`` survive trimming of the bounded registries so lifetime
    telemetry is preserved. All state mutations are guarded by a single
    reentrant lock so the engine is safe to call from multiple threads,
    including from within its own locked methods.
    """

    # Capacity limits to bound memory use per engine instance.
    MAX_MEASUREMENTS: int = 5000
    MAX_SNAPSHOTS: int = 5000
    MAX_ASSESSMENTS: int = 2000
    MAX_DECISIONS: int = 2000
    MAX_PLANS: int = 1000
    MAX_PROFILES: int = 1000
    # Number of recent measurements aggregated into a snapshot.
    SNAPSHOT_WINDOW: int = 10
    # Fixed band boundaries for state classification (the OPTIMAL/LOADED/
    # SATURATED breakpoints; the underload boundary comes from the profile).
    OPTIMAL_BOUND: float = 0.6
    LOADED_BOUND: float = 0.8
    SATURATED_BOUND: float = 0.95
    # Nominal capacity freed by each allocation strategy.
    STRATEGY_RELIEF: Dict[AllocationStrategy, float] = {
        AllocationStrategy.SHED: 0.3,
        AllocationStrategy.DEFER: 0.2,
        AllocationStrategy.DELEGATE: 0.4,
        AllocationStrategy.CHUNK: 0.15,
        AllocationStrategy.SEQUENCE: 0.25,
        AllocationStrategy.OFFLOAD: 0.5,
    }
    # Default recovery steps for each recovery action.
    RECOVERY_STEPS: Dict[RecoveryAction, List[str]] = {
        RecoveryAction.PAUSE: [
            "Halt active task processing",
            "Wait for the specified duration",
            "Resume with reduced concurrency",
        ],
        RecoveryAction.BREATH: [
            "Slow the reasoning cadence",
            "Reduce context window churn",
            "Allow a short idle cycle before resuming",
        ],
        RecoveryAction.CONSOLIDATE: [
            "Compress working memory entries",
            "Persist intermediate state to long-term store",
            "Collapse redundant context windows",
        ],
        RecoveryAction.SIMPLIFY: [
            "Drop extraneous sub-goals",
            "Reduce task decomposition depth",
            "Fall back to simpler heuristics",
        ],
        RecoveryAction.ARCHIVE: [
            "Offload completed items to long-term storage",
            "Close inactive contexts",
            "Reclaim working-memory slots",
        ],
    }

    def __init__(self) -> None:
        self._measurements: Dict[str, LoadMeasurement] = {}
        self._snapshots: Dict[str, WorkloadSnapshot] = {}
        self._assessments: Dict[str, InterferenceAssessment] = {}
        self._decisions: Dict[str, AllocationDecision] = {}
        self._plans: Dict[str, RecoveryPlan] = {}
        self._profiles: Dict[str, WorkloadProfile] = {}
        # Cumulative telemetry counters that survive registry trimming.
        self._stats: Dict[str, int] = {}
        # Agents currently in recovery; snapshots report RECOVERING while
        # an agent is in this set.
        self._recovering: set = set()
        self._lock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal helpers ───────────────────────────────────────────

    def _bump(self, key: str, amount: int = 1) -> None:
        """Increment a cumulative telemetry counter. Caller holds the lock."""
        self._stats[key] = self._stats.get(key, 0) + amount

    def _trim(self, registry: Dict[str, Any], limit: int) -> None:
        """Drop the oldest entry from a registry if it exceeds ``limit``.

        Caller holds the lock. Uses dict insertion order (Python 3.7+) to
        identify the oldest entry in O(1).
        """
        if len(registry) > limit:
            oldest = next(iter(registry))
            del registry[oldest]

    def _classify_state(
        self, capacity_used: float, profile: WorkloadProfile
    ) -> WorkloadState:
        """Classify a workload state from capacity used and the profile.

        The underload boundary comes from the profile's
        ``underload_threshold``; the OPTIMAL/LOADED/SATURATED boundaries
        are the engine's fixed band breakpoints. ``capacity_used`` may
        exceed 1.0, in which case the state is SATURATED.
        """
        if capacity_used < profile.underload_threshold:
            return WorkloadState.UNDERLOADED
        if capacity_used < self.OPTIMAL_BOUND:
            return WorkloadState.OPTIMAL
        if capacity_used < self.LOADED_BOUND:
            return WorkloadState.LOADED
        if capacity_used < self.SATURATED_BOUND:
            return WorkloadState.OVERLOADED
        return WorkloadState.SATURATED

    def _interference_for_task_count(self, active_tasks: int) -> InterferenceType:
        """Estimate dual-task interference from the number of active tasks.

        A single task cannot interfere with itself. Each additional
        concurrent task raises the interference band, since more tasks
        compete for the agent's finite cognitive resources.
        """
        try:
            n = int(active_tasks)
        except (TypeError, ValueError):
            n = 1
        if n <= 1:
            return InterferenceType.NONE
        if n == 2:
            return InterferenceType.WEAK
        if n == 3:
            return InterferenceType.MODERATE
        if n == 4:
            return InterferenceType.STRONG
        return InterferenceType.SEVERE

    def _refresh_profile(self, profile: WorkloadProfile, agent_id: str) -> None:
        """Recompute the aggregate fields of ``profile`` from engine state.

        Recomputes ``total_measurements``, the per-type load averages, and
        ``state_distribution`` from the currently held measurements and
        snapshots for ``agent_id``. Caller holds the lock.
        """
        measurements = [m for m in self._measurements.values() if m.agent_id == agent_id]
        snapshots = [s for s in self._snapshots.values() if s.agent_id == agent_id]
        intrinsic_vals = [m.value for m in measurements if m.load_type == LoadType.INTRINSIC]
        extraneous_vals = [m.value for m in measurements if m.load_type == LoadType.EXTRANEOUS]
        germane_vals = [m.value for m in measurements if m.load_type == LoadType.GERMANE]
        profile.total_measurements = len(measurements)
        profile.avg_intrinsic = (
            sum(intrinsic_vals) / len(intrinsic_vals) if intrinsic_vals else 0.0
        )
        profile.avg_extraneous = (
            sum(extraneous_vals) / len(extraneous_vals) if extraneous_vals else 0.0
        )
        profile.avg_germane = (
            sum(germane_vals) / len(germane_vals) if germane_vals else 0.0
        )
        state_dist: Dict[WorkloadState, int] = {}
        for snap in snapshots:
            state_dist[snap.state] = state_dist.get(snap.state, 0) + 1
        profile.state_distribution = state_dist
        profile.updated_at = _now()

    # ── Load Measurement ───────────────────────────────────────────

    def record_measurement(
        self,
        agent_id: str,
        load_type: LoadType,
        value: float,
        source_task: str = "",
        element_complexity: float = 0.5,
        element_interactivity: float = 0.5,
    ) -> LoadMeasurement:
        """Record a single cognitive load measurement and return it.

        ``load_type`` may be passed as a ``LoadType`` member or as its
        string value/name. ``value`` is clamped to [0, 1].
        ``element_complexity`` and ``element_interactivity`` are clamped
        to [0, 1] and annotate the measurement for downstream analysis of
        intrinsic load. Raises ``RuntimeError`` if the measurement
        registry is full and cannot be trimmed (it trims automatically).
        """
        resolved_type = _resolve_enum(LoadType, load_type)
        measurement = LoadMeasurement(
            agent_id=agent_id,
            load_type=resolved_type,
            value=_clamp(value),
            source_task=str(source_task),
            element_complexity=_clamp(element_complexity),
            element_interactivity=_clamp(element_interactivity),
        )
        with self._lock:
            self._measurements[measurement.measurement_id] = measurement
            self._trim(self._measurements, self.MAX_MEASUREMENTS)
            self._bump("total_measurements")
            return measurement

    def get_measurement(self, measurement_id: str) -> Optional[LoadMeasurement]:
        """Retrieve a measurement by id, or ``None`` if absent."""
        with self._lock:
            return self._measurements.get(measurement_id)

    def list_measurements(
        self,
        agent_id: Optional[str] = None,
        load_type: Optional[LoadType] = None,
    ) -> List[LoadMeasurement]:
        """Return measurements, optionally filtered by agent and load type.

        When ``agent_id`` is ``None`` all measurements are returned;
        otherwise only measurements for that agent are returned. When
        ``load_type`` is given (as a member or string) the result is
        further filtered to that load type. The returned list is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            measurements = list(self._measurements.values())
        if agent_id is not None:
            measurements = [m for m in measurements if m.agent_id == agent_id]
        if load_type is not None:
            resolved = _resolve_enum(LoadType, load_type)
            measurements = [m for m in measurements if m.load_type == resolved]
        return measurements

    # ── Workload Snapshot ──────────────────────────────────────────

    def take_snapshot(self, agent_id: str, active_tasks: int = 1) -> WorkloadSnapshot:
        """Aggregate recent measurements into a workload snapshot.

        Collects the last ``SNAPSHOT_WINDOW`` measurements for the agent,
        averages them per load type, and sums the per-type averages into
        ``total_load``. The state is classified against the agent's
        capacity envelope: UNDERLOADED below the profile's
        ``underload_threshold``, then OPTIMAL, LOADED, OVERLOADED, and
        SATURATED at the engine's fixed band breakpoints. If the agent is
        currently in recovery, the state is RECOVERING; the recovery flag
        clears automatically once load drops below the underload
        threshold. ``interference`` is estimated from ``active_tasks``.
        """
        with self._lock:
            agent_measurements = [
                m for m in self._measurements.values() if m.agent_id == agent_id
            ]
            recent = agent_measurements[-self.SNAPSHOT_WINDOW:]
            intrinsic_vals = [m.value for m in recent if m.load_type == LoadType.INTRINSIC]
            extraneous_vals = [m.value for m in recent if m.load_type == LoadType.EXTRANEOUS]
            germane_vals = [m.value for m in recent if m.load_type == LoadType.GERMANE]
            intrinsic_load = (
                sum(intrinsic_vals) / len(intrinsic_vals) if intrinsic_vals else 0.0
            )
            extraneous_load = (
                sum(extraneous_vals) / len(extraneous_vals) if extraneous_vals else 0.0
            )
            germane_load = (
                sum(germane_vals) / len(germane_vals) if germane_vals else 0.0
            )
            total_load = intrinsic_load + extraneous_load + germane_load

            # Refresh the profile so its thresholds and aggregates are current.
            profile = self.get_or_create_profile(agent_id)
            capacity_total = profile.baseline_capacity
            capacity_used = total_load

            if agent_id in self._recovering:
                if capacity_used < profile.underload_threshold:
                    self._recovering.discard(agent_id)
                    state = self._classify_state(capacity_used, profile)
                else:
                    state = WorkloadState.RECOVERING
            else:
                state = self._classify_state(capacity_used, profile)

            interference = self._interference_for_task_count(active_tasks)
            snapshot = WorkloadSnapshot(
                agent_id=agent_id,
                intrinsic_load=intrinsic_load,
                extraneous_load=extraneous_load,
                germane_load=germane_load,
                total_load=total_load,
                state=state,
                capacity_used=capacity_used,
                capacity_total=capacity_total,
                interference=interference,
                active_tasks=max(0, int(active_tasks)),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._trim(self._snapshots, self.MAX_SNAPSHOTS)
            self._bump("total_snapshots")
            if state in (WorkloadState.OVERLOADED, WorkloadState.SATURATED):
                self._bump("overload_events")
            # Count this snapshot's state in the profile. The averages were
            # refreshed by get_or_create_profile above; the new snapshot is
            # accounted for incrementally here.
            profile.state_distribution[state] = (
                profile.state_distribution.get(state, 0) + 1
            )
            profile.updated_at = _now()
            return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[WorkloadSnapshot]:
        """Retrieve a snapshot by id, or ``None`` if absent."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        state: Optional[WorkloadState] = None,
    ) -> List[WorkloadSnapshot]:
        """Return snapshots, optionally filtered by agent and state.

        When ``agent_id`` is ``None`` all snapshots are returned;
        otherwise only snapshots for that agent are returned. When
        ``state`` is given (as a member or string) the result is further
        filtered to that workload state. The returned list is a snapshot
        copy; mutating it does not affect the engine.
        """
        with self._lock:
            snapshots = list(self._snapshots.values())
        if agent_id is not None:
            snapshots = [s for s in snapshots if s.agent_id == agent_id]
        if state is not None:
            resolved = _resolve_enum(WorkloadState, state)
            snapshots = [s for s in snapshots if s.state == resolved]
        return snapshots

    # ── Interference Assessment ────────────────────────────────────

    def assess_interference(
        self,
        agent_id: str,
        primary_task: str,
        secondary_task: str,
    ) -> InterferenceAssessment:
        """Estimate dual-task interference between two concurrent tasks.

        Two signals drive the estimate. First, each task is mapped to the
        cognitive channels it touches (language, memory, vision, ...);
        if both tasks share a channel, ``mutual_channel`` is True and
        interference is forced to at least MODERATE, because the tasks
        compete for the same cognitive resource. Second, the Jaccard
        overlap of the tasks' content tokens gives a continuous overlap
        ratio; the interference score is ``0.3 + 0.5 * overlap_ratio``,
        bumped to at least 0.6 when a channel is shared, then clamped to
        [0, 1]. The score is mapped onto an ``InterferenceType`` band.
        ``resource_conflict`` names the shared channel(s), or ``"none"``.
        """
        with self._lock:
            channels_a = _channels_for(primary_task)
            channels_b = _channels_for(secondary_task)
            shared_channels = channels_a & channels_b
            mutual_channel = len(shared_channels) > 0

            tokens_a = _content_tokens(primary_task)
            tokens_b = _content_tokens(secondary_task)
            union = tokens_a | tokens_b
            if union:
                overlap_ratio = len(tokens_a & tokens_b) / len(union)
            else:
                overlap_ratio = 0.0

            interference_score = 0.3 + 0.5 * overlap_ratio
            if mutual_channel:
                interference_score = max(interference_score, 0.6)
            interference_score = _clamp(interference_score, 0.0, 1.0)

            if interference_score < 0.4:
                itype = InterferenceType.NONE
            elif interference_score < 0.6:
                itype = InterferenceType.WEAK
            elif interference_score < 0.75:
                itype = InterferenceType.MODERATE
            elif interference_score < 0.9:
                itype = InterferenceType.STRONG
            else:
                itype = InterferenceType.SEVERE
            # A shared cognitive channel forces at least MODERATE
            # interference regardless of the keyword-derived score.
            if mutual_channel and itype in (InterferenceType.NONE, InterferenceType.WEAK):
                itype = InterferenceType.MODERATE

            resource_conflict = (
                ", ".join(sorted(shared_channels)) if shared_channels else "none"
            )
            assessment = InterferenceAssessment(
                agent_id=agent_id,
                primary_task=primary_task,
                secondary_task=secondary_task,
                interference_type=itype,
                interference_score=interference_score,
                mutual_channel=mutual_channel,
                resource_conflict=resource_conflict,
            )
            self._assessments[assessment.assessment_id] = assessment
            self._trim(self._assessments, self.MAX_ASSESSMENTS)
            self._bump("total_assessments")
            return assessment

    def get_assessment(self, assessment_id: str) -> Optional[InterferenceAssessment]:
        """Retrieve an interference assessment by id, or ``None`` if absent."""
        with self._lock:
            return self._assessments.get(assessment_id)

    def list_assessments(
        self, agent_id: Optional[str] = None
    ) -> List[InterferenceAssessment]:
        """Return assessments, optionally filtered by ``agent_id``.

        When ``agent_id`` is ``None`` all assessments are returned;
        otherwise only assessments for that agent are returned. The
        returned list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            assessments = list(self._assessments.values())
        if agent_id is None:
            return assessments
        return [a for a in assessments if a.agent_id == agent_id]

    # ── Allocation Decision ────────────────────────────────────────

    def decide_allocation(
        self,
        agent_id: str,
        target_task: str,
        current_load: float,
        strategy: AllocationStrategy,
        rationale: str = "",
    ) -> AllocationDecision:
        """Record a decision to redistribute cognitive resources.

        ``strategy`` may be passed as an ``AllocationStrategy`` member or
        as its string value/name. ``freed_capacity`` is the nominal
        capacity the strategy frees (from ``STRATEGY_RELIEF``), bounded by
        the load the task actually contributes: a strategy cannot free
        more than the agent is currently using. If ``rationale`` is empty
        a default rationale describing the strategy and load is generated.
        """
        resolved_strategy = _resolve_enum(AllocationStrategy, strategy)
        base = self.STRATEGY_RELIEF.get(resolved_strategy, 0.2)
        try:
            load = float(current_load)
        except (TypeError, ValueError):
            load = 0.0
        if load < 0.0:
            load = 0.0
        freed = min(base, load)
        with self._lock:
            if not rationale:
                rationale = (
                    f"{resolved_strategy.value} applied to "
                    f"'{target_task}' at load {load:.2f}"
                )
            decision = AllocationDecision(
                agent_id=agent_id,
                strategy=resolved_strategy,
                target_task=str(target_task),
                rationale=rationale,
                freed_capacity=freed,
            )
            self._decisions[decision.decision_id] = decision
            self._trim(self._decisions, self.MAX_DECISIONS)
            self._bump("total_decisions")
            return decision

    def get_decision(self, decision_id: str) -> Optional[AllocationDecision]:
        """Retrieve an allocation decision by id, or ``None`` if absent."""
        with self._lock:
            return self._decisions.get(decision_id)

    def list_decisions(
        self,
        agent_id: Optional[str] = None,
        strategy: Optional[AllocationStrategy] = None,
    ) -> List[AllocationDecision]:
        """Return decisions, optionally filtered by agent and strategy.

        When ``agent_id`` is ``None`` all decisions are returned;
        otherwise only decisions for that agent are returned. When
        ``strategy`` is given (as a member or string) the result is
        further filtered to that strategy. The returned list is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            decisions = list(self._decisions.values())
        if agent_id is not None:
            decisions = [d for d in decisions if d.agent_id == agent_id]
        if strategy is not None:
            resolved = _resolve_enum(AllocationStrategy, strategy)
            decisions = [d for d in decisions if d.strategy == resolved]
        return decisions

    # ── Recovery Plan ──────────────────────────────────────────────

    def create_recovery_plan(
        self,
        agent_id: str,
        action: RecoveryAction,
        duration_estimate: float = 60.0,
        expected_relief: float = 0.3,
        steps: Optional[List[str]] = None,
    ) -> RecoveryPlan:
        """Create a recovery plan for an overloaded agent and return it.

        ``action`` may be passed as a ``RecoveryAction`` member or as its
        string value/name. ``duration_estimate`` (seconds) and
        ``expected_relief`` in [0, 1] are clamped to non-negative values.
        If ``steps`` is ``None`` the engine supplies a default ordered
        step list for the chosen action. Creating a plan marks the agent
        as recovering, so subsequent snapshots report RECOVERING until
        the agent's load falls back below its underload threshold.
        """
        resolved_action = _resolve_enum(RecoveryAction, action)
        try:
            duration = float(duration_estimate)
        except (TypeError, ValueError):
            duration = 60.0
        if duration < 0.0:
            duration = 0.0
        relief = _clamp(expected_relief, 0.0, 1.0)
        if steps is None:
            plan_steps = list(self.RECOVERY_STEPS.get(resolved_action, []))
        else:
            plan_steps = [str(s) for s in steps]
        with self._lock:
            plan = RecoveryPlan(
                agent_id=agent_id,
                action=resolved_action,
                duration_estimate=duration,
                expected_relief=relief,
                steps=plan_steps,
            )
            self._plans[plan.plan_id] = plan
            self._trim(self._plans, self.MAX_PLANS)
            self._bump("total_recoveries")
            # Entering a recovery plan puts the agent into the RECOVERING
            # state for subsequent snapshots until load drops back down.
            self._recovering.add(agent_id)
            return plan

    def get_recovery_plan(self, plan_id: str) -> Optional[RecoveryPlan]:
        """Retrieve a recovery plan by id, or ``None`` if absent."""
        with self._lock:
            return self._plans.get(plan_id)

    def list_recovery_plans(
        self,
        agent_id: Optional[str] = None,
        action: Optional[RecoveryAction] = None,
    ) -> List[RecoveryPlan]:
        """Return recovery plans, optionally filtered by agent and action.

        When ``agent_id`` is ``None`` all plans are returned; otherwise
        only plans for that agent are returned. When ``action`` is given
        (as a member or string) the result is further filtered to that
        recovery action. The returned list is a snapshot copy; mutating
        it does not affect the engine.
        """
        with self._lock:
            plans = list(self._plans.values())
        if agent_id is not None:
            plans = [p for p in plans if p.agent_id == agent_id]
        if action is not None:
            resolved = _resolve_enum(RecoveryAction, action)
            plans = [p for p in plans if p.action == resolved]
        return plans

    # ── Workload Profile ───────────────────────────────────────────

    def get_or_create_profile(self, agent_id: str) -> WorkloadProfile:
        """Get the workload profile for ``agent_id``, creating it if needed.

        A new profile is created with the default capacity envelope
        (baseline 1.0, peak 1.2, overload threshold 0.85, underload
        threshold 0.3). The profile's aggregate fields are refreshed from
        the engine's current measurements and snapshots before returning,
        so callers always see up-to-date averages and state distribution.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                if len(self._profiles) >= self.MAX_PROFILES:
                    # Drop the oldest profile to make room for a new agent.
                    oldest = next(iter(self._profiles))
                    del self._profiles[oldest]
                profile = WorkloadProfile(
                    agent_id=agent_id,
                    baseline_capacity=1.0,
                    peak_capacity=1.2,
                    adaptation_rate=0.1,
                    overload_threshold=0.85,
                    underload_threshold=0.3,
                )
                self._profiles[agent_id] = profile
            self._refresh_profile(profile, agent_id)
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> WorkloadProfile:
        """Update tunable fields of an agent's workload profile.

        Accepted keyword arguments are ``baseline_capacity``,
        ``peak_capacity``, ``adaptation_rate``, ``overload_threshold``,
        and ``underload_threshold``; all are coerced to float. Unknown
        keys are ignored. The profile is created if it does not yet exist,
        and its aggregate fields are refreshed after the update.
        """
        with self._lock:
            profile = self.get_or_create_profile(agent_id)
            allowed = {
                "baseline_capacity",
                "peak_capacity",
                "adaptation_rate",
                "overload_threshold",
                "underload_threshold",
            }
            for key, val in kwargs.items():
                if key in allowed:
                    try:
                        setattr(profile, key, float(val))
                    except (TypeError, ValueError):
                        continue
            self._refresh_profile(profile, agent_id)
            return profile

    def list_profiles(self) -> List[WorkloadProfile]:
        """Return all workload profiles.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics & Maintenance ────────────────────────────────────

    def get_stats(self) -> WorkloadStats:
        """Compute aggregate statistics over the current engine state.

        Counts of snapshots, assessments, decisions, and recovery plans
        are taken from the cumulative telemetry counters (which survive
        registry trimming). ``state_distribution`` tallies the currently
        held snapshots by state; ``interference_distribution`` tallies the
        currently held assessments by interference type.
        ``avg_total_load`` is the mean total load over the currently held
        snapshots (0.0 when none exist). ``overload_events`` counts every
        snapshot whose state was OVERLOADED or SATURATED, cumulatively.
        """
        with self._lock:
            state_dist: Dict[WorkloadState, int] = {}
            interference_dist: Dict[InterferenceType, int] = {}
            load_sum = 0.0
            snapshot_count = len(self._snapshots)
            for snap in self._snapshots.values():
                state_dist[snap.state] = state_dist.get(snap.state, 0) + 1
                load_sum += snap.total_load
            for assessment in self._assessments.values():
                interference_dist[assessment.interference_type] = (
                    interference_dist.get(assessment.interference_type, 0) + 1
                )
            avg_total_load = load_sum / snapshot_count if snapshot_count else 0.0
            return WorkloadStats(
                total_snapshots=self._stats.get("total_snapshots", 0),
                total_assessments=self._stats.get("total_assessments", 0),
                total_decisions=self._stats.get("total_decisions", 0),
                total_recoveries=self._stats.get("total_recoveries", 0),
                state_distribution=state_dist,
                avg_total_load=avg_total_load,
                overload_events=self._stats.get("overload_events", 0),
                interference_distribution=interference_dist,
            )

    # ── Maintenance ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Drops every measurement, snapshot, assessment, decision, plan,
        profile, cumulative counter, and recovering flag. The engine
        returns to its initial empty state.
        """
        with self._lock:
            self._measurements.clear()
            self._snapshots.clear()
            self._assessments.clear()
            self._decisions.clear()
            self._plans.clear()
            self._profiles.clear()
            self._stats.clear()
            self._recovering.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine = None
_engine_lock = threading.Lock()


def get_workload_engine() -> AgentCognitiveWorkload:
    """Get or create the singleton ``AgentCognitiveWorkload`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveWorkload()
        return _engine


def reset_workload_engine() -> None:
    """Reset the singleton ``AgentCognitiveWorkload`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_workload_engine`` call creates a
    fresh instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None