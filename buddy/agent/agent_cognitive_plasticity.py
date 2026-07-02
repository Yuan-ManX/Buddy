"""Agent Cognitive Plasticity Engine — malleability of thought patterns

Plasticity measures how easily cognitive structure yields to new information
and holds its new shape, distinct from momentum, viscosity, and inertia.

Core capabilities:
  - Per-axis readings, reshapes, regimes, plans, stages, profiles, stats

Architecture:
  AgentCognitivePlasticity (singleton)
  ├── PlasticityReading      (one observation of cognitive plasticity)
  ├── ReshapeRecord          (one recorded reshape event)
  ├── PlasticitySnapshot     (aggregate plasticity state for one agent)
  ├── ReshapePlan            (a plan to perform a reshape)
  ├── SettleRecord           (one stage transition in a reshape lifecycle)
  ├── PlasticityProfile      (per-agent aggregate plasticity tendencies)
  └── PlasticityStats        (engine-wide aggregate statistics)
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string.

    Used as the canonical timestamp for every record the engine creates.
    Centralizing it here keeps timestamps uniform across the engine and
    trivially interchangeable for testing. The format is the simple ISO
    representation that ``datetime.utcnow().isoformat()`` produces.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/reshape/snapshot/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine of this scale.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` score. A low-side default is safer
    than a mid-range one for plasticity-like quantities where a spurious
    high reading would inflate the perceived malleability and make an
    agent look more transformable than it actually is.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _clamp_positive_ms(value: float) -> float:
    """Clamp a millisecond interval to a non-negative value.

    Intervals must be non-negative; negative values are coerced to 0
    rather than rejected so a misconfigured caller cannot crash the
    engine. The upper bound is left open because real settle intervals
    can legitimately exceed many seconds for slow agents.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    if f < 0.0:
        return 0.0
    return f


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first
    against member values (e.g. ``"morphological"``) and then against
    member names (e.g. ``"MORPHOLOGICAL"``), so callers may pass either
    form. This lets the public API accept either the symbolic name or
    the lower-case value string from JSON payloads. Raises
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


def _enum_value(enum_cls: type, value: Any) -> str:
    """Return the ``.value`` of an enum member, or a string fallback.

    Used inside ``to_dict`` methods so a stored field always serializes
    to a plain string even if a non-enum slipped in through direct
    construction. The ``enum_cls`` argument is taken for symmetry with
    ``_resolve_enum`` and to make the call sites self-documenting.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_regime(avg_score: float) -> "PlasticityRegime":
    """Classify an agent's plasticity regime from its average score.

    The average plasticity score is clamped to [0, 1] where higher means
    more plastic. The bands are applied in order: below 0.15 the agent
    is RIGID (near-zero plasticity, structure fully hardened); below
    0.35 it is SET (low plasticity, yields only under substantial
    force); below 0.55 it is YIELDING (moderate plasticity, bends under
    ordinary pressure); below 0.75 it is MALLEABLE (high plasticity,
    reshapes readily); below 0.9 it is ADAPTIVE (very high plasticity,
    restructures proactively); otherwise it is TRANSFORMABLE (extreme
    plasticity, can be remade by a single decisive input).
    """
    s = _clamp(avg_score, 0.0, 1.0)
    if s < 0.15:
        return PlasticityRegime.RIGID
    if s < 0.35:
        return PlasticityRegime.SET
    if s < 0.55:
        return PlasticityRegime.YIELDING
    if s < 0.75:
        return PlasticityRegime.MALLEABLE
    if s < 0.9:
        return PlasticityRegime.ADAPTIVE
    return PlasticityRegime.TRANSFORMABLE


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class PlasticityAxis(str, Enum):
    """The axis along which cognitive plasticity is being measured.

    Each axis is a different dimension of the agent's structure whose
    malleability can vary independently. MORPHOLOGICAL plasticity is
    the plasticity of form (categories, shapes). ASSOCIATIVE plasticity
    is the plasticity of linkage (connections between ideas).
    PROCEDURAL plasticity is the plasticity of process (routines,
    procedures). EPISTEMIC plasticity is the plasticity of belief
    (knowledge claims). AFFECTIVE plasticity is the plasticity of
    feeling (emotional responses). NORMATIVE plasticity is the
    plasticity of value (standards, preferences). See the module
    docstring for the full description of each axis.
    """
    MORPHOLOGICAL = "morphological"  # form / category plasticity
    ASSOCIATIVE = "associative"      # linkage plasticity
    PROCEDURAL = "procedural"        # process plasticity
    EPISTEMIC = "epistemic"          # belief plasticity
    AFFECTIVE = "affective"          # affect plasticity
    NORMATIVE = "normative"          # value plasticity


class PlasticityRegime(str, Enum):
    """The plasticity regime an agent occupies, classified by its score.

    Ranges from RIGID (near-zero plasticity, structure fully hardened)
    through SET (low plasticity), YIELDING (moderate plasticity), and
    MALLEABLE (high plasticity) to ADAPTIVE (very high plasticity) and
    TRANSFORMABLE (extreme plasticity). The regime is derived from the
    average plasticity score across the agent's readings via
    ``_determine_regime``.
    """
    RIGID = "rigid"                # near-zero plasticity
    SET = "set"                    # low plasticity
    YIELDING = "yielding"          # moderate plasticity
    MALLEABLE = "malleable"        # high plasticity
    ADAPTIVE = "adaptive"          # very high plasticity
    TRANSFORMABLE = "transformable"  # extreme plasticity


class ReshapeTrigger(str, Enum):
    """What initiated a reshape.

    EXPERIENCE means empirical input drove the reshape. INSTRUCTION
    means external direction drove it. REFLECTION means the agent's
    own reconsideration drove it. SURPRISE means an unexpected event
    drove it. FATIGUE means exhaustion weakened the structure enough
    that a reshape could occur. INSIGHT means a sudden reorganization
    drove it. The trigger names the proximate cause; the reshape
    strategy names the operation actually performed.
    """
    EXPERIENCE = "experience"      # empirical input
    INSTRUCTION = "instruction"    # external direction
    REFLECTION = "reflection"      # agent's reconsideration
    SURPRISE = "surprise"          # unexpected event
    FATIGUE = "fatigue"            # structural exhaustion
    INSIGHT = "insight"            # sudden reorganization


class ReshapeStrategy(str, Enum):
    """The strategy used to perform a reshape.

    REINFORCE strengthens an existing pattern. EXTEND grows an existing
    pattern. RECOMBINE merges existing patterns into new configurations.
    PRUNE removes weak or obsolete structure. RECONFIGURE rewires the
    relationships between patterns. OVERWRITE replaces existing
    structure wholesale. The strategy names the operation actually
    performed; the trigger names what initiated it.
    """
    REINFORCE = "reinforce"        # strengthen existing pattern
    EXTEND = "extend"              # grow existing pattern
    RECOMBINE = "recombine"        # merge existing patterns
    PRUNE = "prune"                # remove weak structure
    RECONFIGURE = "reconfigure"    # rewire relationships
    OVERWRITE = "overwrite"        # replace structure wholesale


class PlasticityStage(str, Enum):
    """The lifecycle stage of a reshape.

    FROZEN means no reshape is occurring. CRACKED means the structure
    has begun to fail under pressure but is not yet moving. BENDING
    means parts of the structure are yielding. REFORMING means the
    structure is settling into a new configuration. SETTLING means the
    new configuration is hardening into place. STABLE means the
    reshape is complete and the new structure is the working state.
    """
    FROZEN = "frozen"        # no reshape occurring
    CRACKED = "cracked"      # fractures but no movement
    BENDING = "bending"      # yielding under pressure
    REFORMING = "reforming"  # settling into new config
    SETTLING = "settling"    # hardening into place
    STABLE = "stable"        # reshape complete


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PlasticityReading:
    """One observation of cognitive plasticity for an agent.

    ``axis`` classifies which dimension of plasticity the reading
    applies to. ``score`` in [0, 1] is the plasticity score: 0 means
    fully rigid, 1 means fully transformable. ``trigger`` is the
    ``ReshapeTrigger`` that motivated the reading. ``intensity`` in
    [0, 1] is how strongly the trigger is acting on the agent — a
    mild surprise is a low-intensity reading, a structural breakdown
    is a high-intensity reading. ``notes`` is an optional free-form
    annotation.
    """
    reading_id: str
    agent_id: str
    axis: PlasticityAxis
    score: float                  # 0..1, higher = more plastic
    trigger: ReshapeTrigger
    intensity: float              # 0..1, higher = stronger trigger
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(PlasticityAxis, self.axis),
            "score": self.score,
            "trigger": _enum_value(ReshapeTrigger, self.trigger),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ReshapeRecord:
    """One recorded reshape event for an agent.

    ``axis`` is the dimension being reshaped. ``trigger`` is the
    ``ReshapeTrigger`` that initiated the reshape. ``strategy`` is the
    ``ReshapeStrategy`` used to perform the reshape. ``before_score``
    in [0, 1] is the agent's plasticity on that axis before the
    reshape; ``after_score`` in [0, 1] is the score after. The
    difference is the change in plasticity that the reshape produced
    on that axis (positive means the agent became more plastic on
    that axis, negative means it became less so). ``notes`` is an
    optional free-form annotation.
    """
    reshape_id: str
    agent_id: str
    axis: PlasticityAxis
    trigger: ReshapeTrigger
    strategy: ReshapeStrategy
    before_score: float           # 0..1
    after_score: float            # 0..1
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reshape to a plain dict, expanding enums via ``.value``."""
        return {
            "reshape_id": self.reshape_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(PlasticityAxis, self.axis),
            "trigger": _enum_value(ReshapeTrigger, self.trigger),
            "strategy": _enum_value(ReshapeStrategy, self.strategy),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class PlasticitySnapshot:
    """Aggregate plasticity state for one agent.

    ``avg_score`` in [0, 1] is the mean plasticity score across the
    agent's most recent readings (the last ``_SNAPSHOT_READING_WINDOW``
    = 20), or 0.0 if none. ``dominant_axis`` is the most frequent
    ``PlasticityAxis`` among those readings, or MORPHOLOGICAL if none.
    ``regime`` is derived via ``_determine_regime`` from ``avg_score``.
    ``reshape_count`` is the number of reshape records the agent has
    accumulated. ``stage`` is the latest settle record's ``to_stage``,
    or FROZEN if no settle records exist. ``notes`` is an optional
    free-form annotation.
    """
    snapshot_id: str
    agent_id: str
    avg_score: float
    dominant_axis: PlasticityAxis
    regime: PlasticityRegime
    reshape_count: int
    stage: PlasticityStage
    timestamp: str
    notes: Optional[str] = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_score": self.avg_score,
            "dominant_axis": _enum_value(PlasticityAxis, self.dominant_axis),
            "regime": _enum_value(PlasticityRegime, self.regime),
            "reshape_count": self.reshape_count,
            "stage": _enum_value(PlasticityStage, self.stage),
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ReshapePlan:
    """A plan to perform a reshape on an agent.

    ``strategy`` is the ``ReshapeStrategy`` to use. ``target_score``
    in [0, 1] is the score the plan aims to reach. ``current_score``
    in [0, 1] is the agent's current plasticity on the targeted axis.
    ``rationale`` explains why this plan was chosen — what the agent
    hopes to achieve by moving to ``target_score`` from
    ``current_score``.
    """
    plan_id: str
    agent_id: str
    strategy: ReshapeStrategy
    target_score: float           # 0..1
    current_score: float          # 0..1
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(ReshapeStrategy, self.strategy),
            "target_score": self.target_score,
            "current_score": self.current_score,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class SettleRecord:
    """One stage transition in a reshape's lifecycle.

    ``from_stage`` is the ``PlasticityStage`` the reshape was in
    before the transition. ``to_stage`` is the ``PlasticityStage`` it
    moved to. ``interval_ms`` is the time elapsed during the
    transition in milliseconds (clamped to non-negative). ``signature``
    is a free-form string identifying the reshape (e.g. a reshape_id
    or a descriptive label) so settle records can be tied back to
    their parent reshape. ``notes`` is an optional free-form
    annotation.
    """
    settle_id: str
    agent_id: str
    from_stage: PlasticityStage
    to_stage: PlasticityStage
    interval_ms: float
    signature: str
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this settle to a plain dict, expanding enums via ``.value``."""
        return {
            "settle_id": self.settle_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(PlasticityStage, self.from_stage),
            "to_stage": _enum_value(PlasticityStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class PlasticityProfile:
    """Per-agent aggregate plasticity tendencies.

    ``avg_score`` in [0, 1] is the mean plasticity score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``PlasticityAxis`` among the agent's readings, or
    MORPHOLOGICAL if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_score``. ``total_readings``,
    ``total_reshapes``, and ``total_settles`` are the counts of each
    record type for the agent. ``last_updated`` is the ISO-8601
    timestamp of the last profile computation.
    """
    agent_id: str
    avg_score: float = 0.0
    dominant_axis: PlasticityAxis = PlasticityAxis.MORPHOLOGICAL
    regime: PlasticityRegime = PlasticityRegime.SET
    total_readings: int = 0
    total_reshapes: int = 0
    total_settles: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_score": self.avg_score,
            "dominant_axis": _enum_value(PlasticityAxis, self.dominant_axis),
            "regime": _enum_value(PlasticityRegime, self.regime),
            "total_readings": self.total_readings,
            "total_reshapes": self.total_reshapes,
            "total_settles": self.total_settles,
            "last_updated": self.last_updated,
        }


@dataclass
class PlasticityStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids that have at
    least one record. ``avg_score`` is the mean plasticity score across
    all readings, or 0.0 when none exist. ``dominant_regime`` is the
    most frequent regime across all cached profiles, or SET when none
    exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_reshapes: int = 0
    total_snapshots: int = 0
    total_settles: int = 0
    avg_score: float = 0.0
    dominant_regime: PlasticityRegime = PlasticityRegime.SET

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_reshapes": self.total_reshapes,
            "total_snapshots": self.total_snapshots,
            "total_settles": self.total_settles,
            "avg_score": self.avg_score,
            "dominant_regime": _enum_value(PlasticityRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitivePlasticity:
    """Thread-safe engine that models an agent's cognitive plasticity.

    The engine holds six stores: ``_readings`` (PlasticityReading lists
    keyed by agent_id), ``_reshapes`` (ReshapeRecord lists keyed by
    agent_id), ``_snapshots`` (PlasticitySnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of ReshapePlan), ``_settles``
    (SettleRecord lists keyed by agent_id), and ``_profiles``
    (PlasticityProfile keyed by agent_id).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The plasticity model is deliberately heuristic: scores, triggers,
    and intensities are caller-supplied observations, regimes are
    banded from average score, and dominant axes are computed by
    mode. These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how plasticity scores
    and intensities are produced — callers may derive them from any
    source. The engine's job is to record, aggregate, classify, and
    plan, not to measure plasticity itself. Profiles are cached per
    agent and invalidated whenever the agent's readings, reshapes,
    snapshots, or settles change, so ``get_profile`` returns a fresh
    aggregate only when the underlying data has changed.
    """

    # Number of most-recent readings whose scores feed into a snapshot's
    # average plasticity. The window is long enough to smooth a single
    # noisy reading and short enough to reflect the agent's current
    # plasticity posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty plasticity engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[PlasticityReading]] = {}
        self._reshapes: Dict[str, List[ReshapeRecord]] = {}
        self._snapshots: Dict[str, List[PlasticitySnapshot]] = {}
        self._plans: List[ReshapePlan] = []
        self._settles: Dict[str, List[SettleRecord]] = {}
        self._profiles: Dict[str, PlasticityProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_plasticity_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._reshapes.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._settles.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[PlasticityReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_reshapes_locked(self, agent_id: str) -> List[ReshapeRecord]:
        """Return one agent's reshape records in insertion order. Caller holds the lock."""
        return list(self._reshapes.get(agent_id, []))

    def _agent_snapshots_locked(self, agent_id: str) -> List[PlasticitySnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_settles_locked(self, agent_id: str) -> List[SettleRecord]:
        """Return one agent's settle records in insertion order. Caller holds the lock."""
        return list(self._settles.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[PlasticityReading]
    ) -> Optional[PlasticityAxis]:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order (the first axis to reach
        the maximum count wins). Returns ``None`` if the list is
        empty. Caller holds the lock.
        """
        if not readings:
            return None
        counts: Counter = Counter()
        for reading in readings:
            counts[reading.axis] += 1
        # ``most_common`` breaks ties by insertion order in Python 3.7+.
        return counts.most_common(1)[0][0]

    def _latest_stage_locked(self, agent_id: str) -> PlasticityStage:
        """Return the agent's most recent settle stage, or FROZEN.

        FROZEN is the default when the agent has no settle records —
        a stable steady state is treated as "no reshape currently in
        progress". Caller holds the lock.
        """
        settles = self._agent_settles_locked(agent_id)
        if not settles:
            return PlasticityStage.FROZEN
        # Settles are stored in insertion order, so the last one is
        # the most recent.
        return settles[-1].to_stage

    def _mode_regime_locked(
        self, profiles: List[PlasticityProfile]
    ) -> PlasticityRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns SET if the list is empty. Ties are broken by insertion
        order. Caller holds the lock.
        """
        if not profiles:
            return PlasticityRegime.SET
        counts: Counter = Counter()
        for profile in profiles:
            counts[profile.regime] += 1
        return counts.most_common(1)[0][0]

    # ── Plasticity Readings ─────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        score: float,
        trigger: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> PlasticityReading:
        """Record a plasticity reading for an agent and return it.

        ``axis`` may be passed as a ``PlasticityAxis`` member or its
        string name/value. ``score`` in [0, 1] is clamped to that
        range. ``trigger`` may be passed as a ``ReshapeTrigger``
        member or its string name/value. ``intensity`` in [0, 1] is
        clamped to that range. The reading is stored and returned;
        the agent's cached profile is invalidated.
        """
        with self._lock:
            reading = PlasticityReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(PlasticityAxis, axis),
                score=_clamp(score, 0.0, 1.0),
                trigger=_resolve_enum(ReshapeTrigger, trigger),
                intensity=_clamp(intensity, 0.0, 1.0),
                timestamp=_now(),
                notes=notes,
            )
            self._readings.setdefault(agent_id, []).append(reading)
            self._profiles.pop(agent_id, None)
            return reading

    def list_readings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PlasticityReading]:
        """Return readings, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all readings are considered;
        otherwise only readings for that agent are returned. The most
        recently recorded ``limit`` readings are returned (insertion
        order is chronological, so the tail is the most recent). The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                readings = self._agent_readings_locked(agent_id)
            else:
                readings = []
                for agent_readings in self._readings.values():
                    readings.extend(agent_readings)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return readings[-n:] if n else []

    def get_reading(self, reading_id: str) -> PlasticityReading:
        """Retrieve a reading by id.

        Raises ``ValueError`` if no reading exists with that id, so
        callers can treat the return as a guaranteed non-None value
        and let a single exception type stand in for a not-found
        error.
        """
        with self._lock:
            for agent_readings in self._readings.values():
                for reading in agent_readings:
                    if reading.reading_id == reading_id:
                        return reading
        raise ValueError(f"reading {reading_id!r} not found")

    # ── Reshape Records ─────────────────────────────────────────────

    def record_reshape(
        self,
        agent_id: str,
        axis: Any,
        trigger: Any,
        strategy: Any,
        before_score: float,
        after_score: float,
        notes: Optional[str] = None,
    ) -> ReshapeRecord:
        """Record a reshape event for an agent and return it.

        ``axis`` may be passed as a ``PlasticityAxis`` member or its
        string name/value. ``trigger`` may be passed as a
        ``ReshapeTrigger`` member or its string name/value.
        ``strategy`` may be passed as a ``ReshapeStrategy`` member or
        its string name/value. ``before_score`` and ``after_score`` in
        [0, 1] are each clamped to that range. The reshape is stored
        and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            record = ReshapeRecord(
                reshape_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(PlasticityAxis, axis),
                trigger=_resolve_enum(ReshapeTrigger, trigger),
                strategy=_resolve_enum(ReshapeStrategy, strategy),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                timestamp=_now(),
                notes=notes,
            )
            self._reshapes.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_reshapes(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReshapeRecord]:
        """Return reshape records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all reshapes are considered;
        otherwise only reshapes for that agent are returned. The most
        recently recorded ``limit`` reshapes are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                reshapes = self._agent_reshapes_locked(agent_id)
            else:
                reshapes = []
                for agent_reshapes in self._reshapes.values():
                    reshapes.extend(agent_reshapes)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return reshapes[-n:] if n else []

    def get_reshape(self, reshape_id: str) -> ReshapeRecord:
        """Retrieve a reshape record by id.

        Raises ``ValueError`` if no reshape record exists with that id.
        """
        with self._lock:
            for agent_reshapes in self._reshapes.values():
                for reshape in agent_reshapes:
                    if reshape.reshape_id == reshape_id:
                        return reshape
        raise ValueError(f"reshape {reshape_id!r} not found")

    # ── Snapshots ───────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> PlasticitySnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_score`` is the mean plasticity score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW``
        = 20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``PlasticityAxis`` among those readings, or MORPHOLOGICAL if
        none. ``regime`` is derived via ``_determine_regime`` from
        ``avg_score``. ``reshape_count`` is the number of reshape
        records the agent has accumulated. ``stage`` is the latest
        settle record's ``to_stage``, or FROZEN if no settle records
        exist. The snapshot is stored and returned; the agent's
        cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_score = sum(r.score for r in recent) / len(recent)
            else:
                avg_score = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            if dominant_axis is None:
                dominant_axis = PlasticityAxis.MORPHOLOGICAL

            regime = _determine_regime(avg_score)
            reshape_count = len(self._agent_reshapes_locked(agent_id))
            stage = self._latest_stage_locked(agent_id)

            snapshot = PlasticitySnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_score=round(avg_score, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                reshape_count=reshape_count,
                stage=stage,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PlasticitySnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The
        most recently taken ``limit`` snapshots are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                snapshots = self._agent_snapshots_locked(agent_id)
            else:
                snapshots = []
                for agent_snapshots in self._snapshots.values():
                    snapshots.extend(agent_snapshots)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return snapshots[-n:] if n else []

    def get_snapshot(self, snapshot_id: str) -> PlasticitySnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Reshape Plans ───────────────────────────────────────────────

    def plan_reshape(
        self,
        agent_id: str,
        strategy: Any,
        target_score: float,
        current_score: float,
        rationale: str,
    ) -> ReshapePlan:
        """Record a reshape plan for an agent and return it.

        ``strategy`` may be passed as a ``ReshapeStrategy`` member or
        its string name/value. ``target_score`` in [0, 1] is the
        plasticity score the plan aims to reach. ``current_score`` in
        [0, 1] is the agent's current plasticity score. ``rationale``
        explains why this plan was chosen — what the agent hopes to
        achieve by moving to ``target_score`` from ``current_score``.
        The plan is stored and returned.
        """
        with self._lock:
            plan = ReshapePlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(ReshapeStrategy, strategy),
                target_score=_clamp(target_score, 0.0, 1.0),
                current_score=_clamp(current_score, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReshapePlan]:
        """Return reshape plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered;
        otherwise only plans for that agent are returned. The most
        recently recorded ``limit`` plans are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                plans = [p for p in self._plans if p.agent_id == agent_id]
            else:
                plans = list(self._plans)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> ReshapePlan:
        """Retrieve a reshape plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"reshape plan {plan_id!r} not found")

    # ── Settle Records ──────────────────────────────────────────────

    def record_settle(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
        notes: Optional[str] = None,
    ) -> SettleRecord:
        """Record a stage transition in a reshape's lifecycle and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``PlasticityStage`` member or its string name/value.
        ``interval_ms`` is the time elapsed during the transition in
        milliseconds; it is clamped to non-negative so a misconfigured
        caller cannot crash the engine with a negative interval.
        ``signature`` is a free-form string identifying the reshape
        (e.g. a ``reshape_id`` or a descriptive label) so settle
        records can be tied back to their parent reshape. The settle
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = SettleRecord(
                settle_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(PlasticityStage, from_stage),
                to_stage=_resolve_enum(PlasticityStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
                notes=notes,
            )
            self._settles.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_settles(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SettleRecord]:
        """Return settle records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all settles are considered;
        otherwise only settles for that agent are returned. The most
        recently recorded ``limit`` settles are returned. The
        returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                settles = self._agent_settles_locked(agent_id)
            else:
                settles = []
                for agent_settles in self._settles.values():
                    settles.extend(agent_settles)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return settles[-n:] if n else []

    def get_settle(self, settle_id: str) -> SettleRecord:
        """Retrieve a settle record by id.

        Raises ``ValueError`` if no settle record exists with that id.
        """
        with self._lock:
            for agent_settles in self._settles.values():
                for settle in agent_settles:
                    if settle.settle_id == settle_id:
                        return settle
        raise ValueError(f"settle record {settle_id!r} not found")

    # ── Profiles ────────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> PlasticityProfile:
        """Return the agent's plasticity profile, computing it if absent.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, reshapes, snapshots, or settles change.
        If the agent has data but no profile yet, one is built from
        the existing data. Call ``update_profile`` to force a refresh
        or override a computed field. Field semantics are documented
        on ``PlasticityProfile`` and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> PlasticityProfile:
        """Refresh and optionally override fields of an agent's plasticity profile.

        The profile is first recomputed from the live stores, then any
        supplied keyword overrides (matching ``PlasticityProfile``
        field names) are applied, and ``last_updated`` is stamped.
        Accepted overrides: ``avg_score`` (float), ``dominant_axis``
        (``PlasticityAxis``), ``regime`` (``PlasticityRegime``),
        ``total_readings``, ``total_reshapes``, ``total_settles``
        (int). Enum-valued overrides may be passed as the enum
        member or its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_score":
                    try:
                        profile.avg_score = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(PlasticityAxis, value)
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(PlasticityRegime, value)
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_reshapes",
                    "total_settles",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[PlasticityProfile]:
        """Return all stored plasticity profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ──────────────────────────────────────────────────

    def get_stats(self) -> PlasticityStats:
        """Compute engine-wide aggregate statistics.

        Scalar totals are computed by scanning the stores.
        ``total_agents`` is the number of distinct agent_ids that
        appear in any store. ``avg_score`` is the mean plasticity
        score across all readings, or 0.0 when none exist.
        ``dominant_regime`` is the most frequent regime across all
        cached profiles, or SET when none exist.
        """
        with self._lock:
            agent_ids: set = set()
            total_readings = 0
            score_sum = 0.0
            for agent_id, readings in self._readings.items():
                agent_ids.add(agent_id)
                total_readings += len(readings)
                for reading in readings:
                    score_sum += reading.score

            total_reshapes = 0
            for agent_id, reshapes in self._reshapes.items():
                agent_ids.add(agent_id)
                total_reshapes += len(reshapes)

            total_snapshots = 0
            for agent_id, snapshots in self._snapshots.items():
                agent_ids.add(agent_id)
                total_snapshots += len(snapshots)

            total_settles = 0
            for agent_id, settles in self._settles.items():
                agent_ids.add(agent_id)
                total_settles += len(settles)

            for plan in self._plans:
                agent_ids.add(plan.agent_id)

            avg_score = (
                round(score_sum / total_readings, 4) if total_readings else 0.0
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average score so the stats
                # reflect real state rather than the default SET.
                dominant_regime = _determine_regime(avg_score)
            else:
                dominant_regime = PlasticityRegime.SET

            return PlasticityStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_reshapes=total_reshapes,
                total_snapshots=total_snapshots,
                total_settles=total_settles,
                avg_score=avg_score,
                dominant_regime=dominant_regime,
            )

    # ── Internal profile computation (caller must hold the lock) ────

    def _compute_profile_locked(self, agent_id: str) -> PlasticityProfile:
        """Aggregate an agent's readings, reshapes, and settles into a profile.

        See ``PlasticityProfile`` for field semantics. ``avg_score``
        is the mean plasticity score across all the agent's readings,
        or 0.0 if none. ``dominant_axis`` is the most frequent
        ``PlasticityAxis`` among the readings, or MORPHOLOGICAL if
        none. ``regime`` is derived via ``_determine_regime`` from
        ``avg_score``. Caller holds the lock.
        """
        agent_readings = self._agent_readings_locked(agent_id)
        agent_reshapes = self._agent_reshapes_locked(agent_id)
        agent_settles = self._agent_settles_locked(agent_id)

        total_readings = len(agent_readings)
        if agent_readings:
            avg_score = sum(r.score for r in agent_readings) / len(agent_readings)
        else:
            avg_score = 0.0

        dominant_axis = self._mode_axis_locked(agent_readings)
        if dominant_axis is None:
            dominant_axis = PlasticityAxis.MORPHOLOGICAL

        regime = _determine_regime(avg_score)

        return PlasticityProfile(
            agent_id=str(agent_id),
            avg_score=round(avg_score, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=total_readings,
            total_reshapes=len(agent_reshapes),
            total_settles=len(agent_settles),
            last_updated=_now(),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitivePlasticity] = None
_engine_lock = threading.Lock()


def get_plasticity_engine() -> AgentCognitivePlasticity:
    """Get or create the singleton ``AgentCognitivePlasticity`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitivePlasticity()
    return _engine


def reset_plasticity_engine() -> None:
    """Reset the singleton ``AgentCognitivePlasticity`` instance.

    Drops the reference so the next ``get_plasticity_engine`` call
    creates a fresh instance. Useful for tests that need a clean
    engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
