"""Agent Cognitive Elasticity Engine — spring-back of mental patterns

Elasticity measures how strongly cognition returns to its baseline shape
after deformation, distinct from inertia, resilience, plasticity, drift.

Core capabilities:
  - Per-axis readings, deformations, regimes, plans, snap records, profiles, stats

Architecture:
  AgentCognitiveElasticity (singleton)
  ├── ElasticityReading     (one observation of strain on an axis)
  ├── DeformationRecord     (one deformation event for an axis)
  ├── ElasticitySnapshot    (aggregate elasticity state for one agent)
  ├── RecoveryPlan          (a plan to recover to baseline)
  ├── SnapRecord            (one lifecycle stage transition)
  ├── ElasticityProfile     (per-agent aggregate elasticity tendencies)
  └── ElasticityStats       (engine-wide aggregate statistics)
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
    trivially interchangeable for testing.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/deformation/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` magnitude. A low-side default is
    safer than a mid-range one for elasticity-like quantities where a
    spurious high reading would inflate the perceived strain.
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
    engine. The upper bound is left open because real intervals can
    legitimately exceed one second.
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
    against member values (e.g. ``"brittle"``) and then against member
    names (e.g. ``"BRITTLE"``), so callers may pass either form. This
    lets the public API accept either the symbolic name or the
    lower-case value string from JSON payloads. Raises ``ValueError``
    if neither matches.
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


def _determine_regime(avg_strain: float) -> "ElasticityRegime":
    """Classify an agent's elasticity regime from its average strain.

    The average is clamped to [0, 1] where higher means more strain
    (and, on the elasticity interpretation, more deformed / closer to
    the elastic limit). The checks are applied in order, so the first
    matching band wins: below 0.15 the structure is BRITTLE (very
    little room to deform); below 0.35 it is STIFF (rigid, resists
    deformation); below 0.55 it is SPRINGY (deforms under load and
    recovers quickly); below 0.75 it is RESILIENT (absorbs substantial
    deformation and returns cleanly); below 0.9 it is SUPPLE (bends
    with whatever load is applied); otherwise it is RUBBERY
    (near-maximum strain, visible distortion).
    """
    avg = _clamp(avg_strain, 0.0, 1.0)
    if avg < 0.15:
        return ElasticityRegime.BRITTLE
    if avg < 0.35:
        return ElasticityRegime.STIFF
    if avg < 0.55:
        return ElasticityRegime.SPRINGY
    if avg < 0.75:
        return ElasticityRegime.RESILIENT
    if avg < 0.9:
        return ElasticityRegime.SUPPLE
    return ElasticityRegime.RUBBERY


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ElasticityAxis(str, Enum):
    """The cognitive axis whose elasticity is being measured.

    Elasticity is not a single scalar; it is a property of an axis
    along which the structure of the agent can be deformed. BELIEF
    is the elasticity of belief revision — how beliefs stretch and
    recover. HABIT is the elasticity of habitual behavior — how
    routines bend under pressure and snap back. ATTENTION is the
    elasticity of attentional focus — how attention deforms and
    restores. AROUSAL is the elasticity of the agent's arousal
    baseline — how activation level shifts and rebounds. POSTURE
    is the elasticity of the agent's interactional posture — how
    its stance toward others deforms and restores. COMMITMENT is
    the elasticity of the agent's commitments — how its promises
    and bindings bend and return.
    """
    BELIEF = "belief"          # elasticity of belief revision
    HABIT = "habit"            # elasticity of habitual behavior
    ATTENTION = "attention"    # elasticity of attentional focus
    AROUSAL = "arousal"        # elasticity of activation baseline
    POSTURE = "posture"        # elasticity of interactional posture
    COMMITMENT = "commitment"  # elasticity of commitments


class ElasticityRegime(str, Enum):
    """The elasticity regime an agent's structure occupies.

    BRITTLE means near-zero strain — very little room to deform;
    small loads shatter the structure. STIFF means low strain —
    the structure is rigid; it deforms but resists. SPRINGY means
    moderate strain — the structure deforms under load and recovers
    quickly with a small overshoot. RESILIENT means high strain —
    the structure absorbs substantial deformation and returns
    cleanly. SUPPLE means very high strain — the structure bends
    with whatever load is applied and recovers gracefully. RUBBERY
    means near-maximum strain — the structure has been stretched
    almost to its elastic limit and is showing visible distortion.
    The regime is derived from the average strain across the
    agent's readings via ``_determine_regime``.
    """
    BRITTLE = "brittle"        # near-zero room to deform
    STIFF = "stiff"            # rigid, resists deformation
    SPRINGY = "springy"        # deforms and recovers with overshoot
    RESILIENT = "resilient"    # absorbs substantial deformation
    SUPPLE = "supple"          # bends with any load, recovers
    RUBBERY = "rubbery"        # near-maximum strain, distorted


class DeformationSource(str, Enum):
    """The source of a deformation event on an axis.

    PRESSURE is sustained external force — obligations, deadlines,
    demands. NOVELTY is the surprise of new information — a fact
    that does not fit prior beliefs. CONFLICT is contradiction
    between sources — evidence that argues with itself. REPETITION
    is repeated exposure to the same stimulus — the elasticity of
    a pattern that has been triggered again and again. FATIGUE is
    accumulated load — the cost of keeping a deformation sustained.
    REWARD is positive reinforcement that may either strengthen or
    distort the structure. The engine tracks the source of each
    deformation to find the dominant load on each axis.
    """
    PRESSURE = "pressure"      # sustained external force
    NOVELTY = "novelty"        # surprise of new information
    CONFLICT = "conflict"      # contradiction between sources
    REPETITION = "repetition"  # repeated exposure
    FATIGUE = "fatigue"        # accumulated load
    REWARD = "reward"          # positive reinforcement


class RecoveryStrategy(str, Enum):
    """The strategy the agent uses to return to baseline after deformation.

    HOLD means no active recovery — the structure rests in its
    current state. BEND means a deliberate incremental return to
    baseline. ABSORB means letting the deformation dissipate on its
    own, with no active pushing back. REBOUND means a forceful
    snap-back that overshoots slightly and oscillates a few times
    before settling. RECOIL means a sharp reverse movement that
    goes past baseline and ends up displaced in the opposite
    direction. SNAP means a brittle failure — the structure
    fractures under load and does not return to its original
    shape at all. Each strategy suits a different elasticity
    regime; the engine records which strategy the agent chose.
    """
    HOLD = "hold"              # no active recovery
    BEND = "bend"              # deliberate incremental return
    ABSORB = "absorb"          # let dissipation do the work
    REBOUND = "rebound"        # forceful snap-back with overshoot
    RECOIL = "recoil"          # sharp reverse past baseline
    SNAP = "snap"              # brittle fracture, no return


class ElasticityStage(str, Enum):
    """The lifecycle stage of a deformation on an axis.

    RESTING is the unstressed baseline — the structure is at its
    preferred shape. STRETCHING is the phase of active deformation
    — the load is being applied and the strain is increasing.
    MAX_STRAIN is the peak of the deformation — the load is
    holding the structure at its most stretched state. REBOUNDING
    is the active spring-back — the load is releasing and the
    structure is returning. RETURNING is the recovery phase — the
    structure is approaching baseline with diminishing oscillation.
    OVERSHOT is the state when the recovery has gone past baseline
    in the opposite direction — the elastic overshoot that, if
    not damped, will oscillate. Transitions between stages are
    recorded as SnapRecord entries.
    """
    RESTING = "resting"            # unstressed baseline
    STRETCHING = "stretching"      # active deformation
    MAX_STRAIN = "max_strain"      # peak of deformation
    REBOUNDING = "rebounding"      # active spring-back
    RETURNING = "returning"        # approaching baseline
    OVERSHOT = "overshot"          # past baseline in opposite direction


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ElasticityReading:
    """One observation of strain and recovery on an axis.

    ``axis`` is the ``ElasticityAxis`` of the reading. ``strain_score``
    in [0, 1] is the current strain on that axis — higher means
    more deformed. ``recovery_rate`` in [0, 1] is the rate at which
    the axis is currently returning to baseline (0 means not
    recovering at all, 1 means recovering as fast as possible).
    ``source`` is the ``DeformationSource`` of the load that
    produced the strain. ``notes`` is an optional free-form
    annotation.
    """
    reading_id: str
    agent_id: str
    axis: ElasticityAxis
    strain_score: float         # 0..1, current strain
    recovery_rate: float        # 0..1, rate of return to baseline
    source: DeformationSource
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(ElasticityAxis, self.axis),
            "strain_score": self.strain_score,
            "recovery_rate": self.recovery_rate,
            "source": _enum_value(DeformationSource, self.source),
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class DeformationRecord:
    """One specific deformation event for an axis.

    ``axis`` is the ``ElasticityAxis`` that was deformed. ``source``
    is the ``DeformationSource`` of the load. ``before_score`` and
    ``after_score`` in [0, 1] are the strain scores before and after
    the deformation. ``recovery_ms`` in [0, ∞) is how long the
    structure took to recover (or 0 if not yet recovered at the time
    of the record). ``notes`` is an optional free-form annotation.
    """
    deform_id: str
    agent_id: str
    axis: ElasticityAxis
    source: DeformationSource
    before_score: float         # 0..1, strain before
    after_score: float          # 0..1, strain after
    recovery_ms: float          # 0..inf, time to recover
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this deformation record to a plain dict, expanding enums via ``.value``."""
        return {
            "deform_id": self.deform_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(ElasticityAxis, self.axis),
            "source": _enum_value(DeformationSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "recovery_ms": self.recovery_ms,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ElasticitySnapshot:
    """Aggregate elasticity state for one agent at one moment.

    ``avg_strain`` in [0, 1] is the mean strain score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is
    the most frequent ``ElasticityAxis`` among those readings, or
    BELIEF if none. ``regime`` is derived via ``_determine_regime``
    from ``avg_strain``. ``deformation_count`` is the number of
    deformation records the agent currently has.
    """
    snapshot_id: str
    agent_id: str
    avg_strain: float
    dominant_axis: ElasticityAxis
    regime: ElasticityRegime
    deformation_count: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_strain": self.avg_strain,
            "dominant_axis": _enum_value(ElasticityAxis, self.dominant_axis),
            "regime": _enum_value(ElasticityRegime, self.regime),
            "deformation_count": self.deformation_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class RecoveryPlan:
    """A plan to return the agent's structure to baseline.

    ``strategy`` is the ``RecoveryStrategy`` chosen. ``target_strain``
    in [0, 1] is the strain the plan aims to reach (typically 0.0 for
    full recovery). ``current_strain`` in [0, 1] is the strain at the
    time the plan was made. ``rationale`` explains why this strategy
    was chosen for this deformation.
    """
    plan_id: str
    agent_id: str
    strategy: RecoveryStrategy
    target_strain: float
    current_strain: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(RecoveryStrategy, self.strategy),
            "target_strain": self.target_strain,
            "current_strain": self.current_strain,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class SnapRecord:
    """One record of a lifecycle stage transition on an axis.

    ``from_stage`` is the ``ElasticityStage`` the agent was in
    before the transition. ``to_stage`` is the ``ElasticityStage``
    it moved to. ``interval_ms`` in [0, ∞) is the duration the
    from_stage held before the transition. ``signature`` is a
    free-form label summarizing the transition (e.g. a compact
    string identifying the axis and source).
    """
    snap_id: str
    agent_id: str
    from_stage: ElasticityStage
    to_stage: ElasticityStage
    interval_ms: float
    signature: str
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snap record to a plain dict, expanding enums via ``.value``."""
        return {
            "snap_id": self.snap_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(ElasticityStage, self.from_stage),
            "to_stage": _enum_value(ElasticityStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ElasticityProfile:
    """Per-agent aggregate elasticity tendencies.

    ``avg_strain`` in [0, 1] is the mean strain score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``ElasticityAxis`` among the agent's readings, or BELIEF
    if none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_strain``. ``total_readings``, ``total_deformations``, and
    ``total_snaps`` count the records held for the agent.
    """
    agent_id: str
    avg_strain: float = 0.0
    dominant_axis: ElasticityAxis = ElasticityAxis.BELIEF
    regime: ElasticityRegime = ElasticityRegime.STIFF
    total_readings: int = 0
    total_deformations: int = 0
    total_snaps: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_strain": self.avg_strain,
            "dominant_axis": _enum_value(ElasticityAxis, self.dominant_axis),
            "regime": _enum_value(ElasticityRegime, self.regime),
            "total_readings": self.total_readings,
            "total_deformations": self.total_deformations,
            "total_snaps": self.total_snaps,
            "last_updated": self.last_updated,
        }


@dataclass
class ElasticityStats:
    """Engine-wide aggregate statistics across all agents and elasticity.

    ``total_agents`` is the number of distinct agent_ids that appear
    in any store. Scalar totals are the rolling counts of each record
    type. ``avg_strain`` is the mean strain score across all readings,
    or 0.0 when none exist. ``dominant_regime`` is the most frequent
    ``ElasticityRegime`` across all snapshots, or STIFF when none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_deformations: int = 0
    total_snapshots: int = 0
    total_snaps: int = 0
    avg_strain: float = 0.0
    dominant_regime: ElasticityRegime = ElasticityRegime.STIFF

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_deformations": self.total_deformations,
            "total_snapshots": self.total_snapshots,
            "total_snaps": self.total_snaps,
            "avg_strain": self.avg_strain,
            "dominant_regime": _enum_value(ElasticityRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveElasticity:
    """Thread-safe engine that models an agent's cognitive elasticity.

    The engine holds six stores: ``_readings`` (ElasticityReading
    lists keyed by agent_id), ``_deformations`` (DeformationRecord
    lists keyed by agent_id), ``_snapshots`` (ElasticitySnapshot
    lists keyed by agent_id), ``_plans`` (a flat list of
    RecoveryPlan), ``_snaps`` (SnapRecord lists keyed by agent_id),
    and ``_profiles`` (ElasticityProfile keyed by agent_id, cached
    and invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The elasticity model is deliberately heuristic: strain scores,
    recovery rates, and recovery milliseconds are caller-supplied
    observations; regimes are banded from average strain; dominant
    axes are computed by mode. These heuristics are transparent and
    auditable rather than learned, which keeps the engine
    deterministic.

    The engine is intentionally agnostic about how strain is
    measured and how deformations are detected — callers may derive
    them from any source. The engine's job is to record, aggregate,
    classify, and plan, not to measure elasticity itself. Profiles
    are cached per agent and invalidated whenever the agent's
    readings, deformations, snapshots, or snaps change, so
    ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose strain scores feed into a
    # snapshot's average strain. The window is long enough to smooth a
    # single noisy reading and short enough to reflect the agent's
    # current elasticity posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty elasticity engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[ElasticityReading]] = {}
        self._deformations: Dict[str, List[DeformationRecord]] = {}
        self._snapshots: Dict[str, List[ElasticitySnapshot]] = {}
        self._plans: List[RecoveryPlan] = []
        self._snaps: Dict[str, List[SnapRecord]] = {}
        self._profiles: Dict[str, ElasticityProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_elasticity_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._deformations.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._snaps.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[ElasticityReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_deformations_locked(
        self, agent_id: str
    ) -> List[DeformationRecord]:
        """Return one agent's deformation records in insertion order. Caller holds the lock."""
        return list(self._deformations.get(agent_id, []))

    def _agent_snaps_locked(self, agent_id: str) -> List[SnapRecord]:
        """Return one agent's snap records in insertion order. Caller holds the lock."""
        return list(self._snaps.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[ElasticityReading]
    ) -> ElasticityAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns BELIEF if the list is empty,
        since BELIEF is the canonical default axis. Caller holds the
        lock.
        """
        if not readings:
            return ElasticityAxis.BELIEF
        counts: Counter = Counter()
        first_seen_order: Dict[ElasticityAxis, int] = {}
        for index, reading in enumerate(readings):
            ax = reading.axis
            counts[ax] += 1
            if ax not in first_seen_order:
                first_seen_order[ax] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: ElasticityAxis = readings[0].axis
        best_count = -1
        for ax, count in counts.items():
            if (count > best_count) or (
                count == best_count
                and first_seen_order.get(ax, 0) < first_seen_order.get(best_axis, 0)
            ):
                best_axis = ax
                best_count = count
        return best_axis

    def _avg_strain_locked(self, agent_id: str) -> float:
        """Return the mean strain score across the agent's readings.

        Returns 0.0 when the agent has no readings. Caller holds the
        lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        return sum(r.strain_score for r in readings) / len(readings)

    def _current_strain_locked(self, agent_id: str) -> float:
        """Return the agent's most recent strain score, or the mean if none recent.

        Prefers the strain score of the most recent reading, falling
        back to the mean of all readings when there is no clear most
        recent one. Returns 0.0 when the agent has no readings.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        most_recent = readings[-1]
        if most_recent.strain_score is not None:
            return float(most_recent.strain_score)
        return self._avg_strain_locked(agent_id)

    def _mode_regime_locked(
        self, profiles: List[ElasticityProfile]
    ) -> ElasticityRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns STIFF if the list is empty, since STIFF is the
        neutral default regime. Caller holds the lock.
        """
        if not profiles:
            return ElasticityRegime.STIFF
        counts: Dict[ElasticityRegime, int] = {}
        for profile in profiles:
            counts[profile.regime] = counts.get(profile.regime, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> ElasticityProfile:
        """Aggregate an agent's readings, deformations, and snaps into a profile.

        See ``ElasticityProfile`` for field semantics. ``avg_strain``
        is the mean strain score across all the agent's readings,
        0.0 if none. ``dominant_axis`` is the most frequent
        ``ElasticityAxis`` among the readings, or BELIEF if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_strain``. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        deformations = self._agent_deformations_locked(agent_id)
        snaps = self._agent_snaps_locked(agent_id)

        avg_strain = self._avg_strain_locked(agent_id)
        regime = _determine_regime(avg_strain)
        dominant_axis = self._mode_axis_locked(readings)

        return ElasticityProfile(
            agent_id=agent_id,
            avg_strain=round(avg_strain, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=len(readings),
            total_deformations=len(deformations),
            total_snaps=len(snaps),
            last_updated=_now(),
        )

    # ── Elasticity Readings ──────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        strain_score: float,
        recovery_rate: float,
        source: Any,
        notes: Optional[str] = None,
    ) -> ElasticityReading:
        """Record an elasticity reading for an agent and return it.

        ``axis`` may be passed as an ``ElasticityAxis`` member or its
        string name/value. ``strain_score`` in [0, 1] is clamped to
        that range. ``recovery_rate`` in [0, 1] is clamped to that
        range. ``source`` may be passed as a ``DeformationSource``
        member or its string name/value. The reading is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            reading = ElasticityReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(ElasticityAxis, axis),
                strain_score=_clamp(strain_score, 0.0, 1.0),
                recovery_rate=_clamp(recovery_rate, 0.0, 1.0),
                source=_resolve_enum(DeformationSource, source),
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
    ) -> List[ElasticityReading]:
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

    def get_reading(self, reading_id: str) -> ElasticityReading:
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

    # ── Deformation Records ──────────────────────────────────────

    def record_deformation(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        recovery_ms: float,
        notes: Optional[str] = None,
    ) -> DeformationRecord:
        """Record a deformation event for an agent and return it.

        ``axis`` may be passed as an ``ElasticityAxis`` member or its
        string name/value. ``source`` may be passed as a
        ``DeformationSource`` member or its string name/value.
        ``before_score`` and ``after_score`` in [0, 1] are clamped to
        that range. ``recovery_ms`` in [0, ∞) is clamped to that
        range. The deformation is stored and returned; the agent's
        cached profile is invalidated.
        """
        with self._lock:
            deformation = DeformationRecord(
                deform_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(ElasticityAxis, axis),
                source=_resolve_enum(DeformationSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                recovery_ms=_clamp_positive_ms(recovery_ms),
                timestamp=_now(),
                notes=notes,
            )
            self._deformations.setdefault(agent_id, []).append(deformation)
            self._profiles.pop(agent_id, None)
            return deformation

    def list_deformations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DeformationRecord]:
        """Return deformation records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all deformations are considered;
        otherwise only deformations for that agent are returned. The
        most recently recorded ``limit`` deformations are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                deformations = self._agent_deformations_locked(agent_id)
            else:
                deformations = []
                for agent_deformations in self._deformations.values():
                    deformations.extend(agent_deformations)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return deformations[-n:] if n else []

    def get_deformation(self, deform_id: str) -> DeformationRecord:
        """Retrieve a deformation record by id.

        Raises ``ValueError`` if no deformation record exists with
        that id.
        """
        with self._lock:
            for agent_deformations in self._deformations.values():
                for deformation in agent_deformations:
                    if deformation.deform_id == deform_id:
                        return deformation
        raise ValueError(f"deformation {deform_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> ElasticitySnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_strain`` is the mean strain score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``ElasticityAxis`` among those readings, or BELIEF if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_strain``. ``deformation_count`` is the number of
        deformation records the agent currently has. The snapshot is
        stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_strain = sum(r.strain_score for r in recent) / len(recent)
            else:
                avg_strain = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_strain)
            deformation_count = len(self._agent_deformations_locked(agent_id))

            snapshot = ElasticitySnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_strain=round(avg_strain, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                deformation_count=deformation_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ElasticitySnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The most
        recently taken ``limit`` snapshots are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                snapshots = list(self._snapshots.get(agent_id, []))
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

    def get_snapshot(self, snapshot_id: str) -> ElasticitySnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Recovery Plans ────────────────────────────────────────────

    def plan_recovery(
        self,
        agent_id: str,
        strategy: Any,
        target_strain: float,
        rationale: str,
    ) -> RecoveryPlan:
        """Record a recovery plan for an agent and return it.

        ``strategy`` may be passed as a ``RecoveryStrategy`` member or
        its string name/value. ``target_strain`` in [0, 1] is clamped
        to that range. ``current_strain`` is derived from the agent's
        readings (most-recent strain or mean if none) and clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured strain.
        """
        with self._lock:
            current_strain = _clamp(
                self._current_strain_locked(agent_id), 0.0, 1.0
            )
            plan = RecoveryPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(RecoveryStrategy, strategy),
                target_strain=_clamp(target_strain, 0.0, 1.0),
                current_strain=current_strain,
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RecoveryPlan]:
        """Return recovery plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered;
        otherwise only plans for that agent are returned. The most
        recently recorded ``limit`` plans are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            plans = list(self._plans)
        if agent_id is not None:
            plans = [p for p in plans if p.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> RecoveryPlan:
        """Retrieve a recovery plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"recovery plan {plan_id!r} not found")

    # ── Snap Records ──────────────────────────────────────────────

    def record_snap(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
        notes: Optional[str] = None,
    ) -> SnapRecord:
        """Record a lifecycle stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as an
        ``ElasticityStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is clamped to that range.
        ``signature`` is a free-form label summarizing the transition
        (e.g. ``"belief:pressure:rebound"``). The snap is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            snap = SnapRecord(
                snap_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(ElasticityStage, from_stage),
                to_stage=_resolve_enum(ElasticityStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
                notes=notes,
            )
            self._snaps.setdefault(agent_id, []).append(snap)
            self._profiles.pop(agent_id, None)
            return snap

    def list_snaps(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SnapRecord]:
        """Return snap records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snaps are considered;
        otherwise only snaps for that agent are returned. The most
        recently recorded ``limit`` snaps are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                snaps = self._agent_snaps_locked(agent_id)
            else:
                snaps = []
                for agent_snaps in self._snaps.values():
                    snaps.extend(agent_snaps)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return snaps[-n:] if n else []

    def get_snap(self, snap_id: str) -> SnapRecord:
        """Retrieve a snap record by id.

        Raises ``ValueError`` if no snap record exists with that id.
        """
        with self._lock:
            for agent_snaps in self._snaps.values():
                for snap in agent_snaps:
                    if snap.snap_id == snap_id:
                        return snap
        raise ValueError(f"snap record {snap_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> ElasticityProfile:
        """Return the agent's elasticity profile, building it if missing.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, deformations, snapshots, or snaps
        change. If the agent has data but no profile yet, the profile
        is built from the live stores. Call ``update_profile`` to
        force a refresh or override a computed field. Field semantics
        are documented on ``ElasticityProfile`` and
        ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(
        self, agent_id: str, **kwargs: Any
    ) -> ElasticityProfile:
        """Refresh and optionally override fields of an agent's elasticity profile.

        The profile is first recomputed from the live stores, then
        any supplied keyword overrides (matching ``ElasticityProfile``
        field names) are applied, and ``last_updated`` is stamped.
        Accepted overrides: ``avg_strain`` (float), ``dominant_axis``
        (``ElasticityAxis``), ``regime`` (``ElasticityRegime``),
        ``total_readings``, ``total_deformations``, ``total_snaps``
        (int). Enum-valued overrides may be passed as the enum
        member or its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_strain":
                    try:
                        profile.avg_strain = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            ElasticityAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(
                            ElasticityRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_deformations",
                    "total_snaps",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[ElasticityProfile]:
        """Return all stored elasticity profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> ElasticityStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids that
        appear in any store. Scalar totals are the counts of each
        record type. ``avg_strain`` is the mean strain score across
        all readings, or 0.0 when none exist. ``dominant_regime`` is
        the most frequent ``ElasticityRegime`` across all cached
        profiles, or STIFF when none exist. When no profiles exist
        but readings do, the dominant regime is derived from the
        average strain via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            total_readings = 0
            strain_sum = 0.0
            for agent_id, readings in self._readings.items():
                agent_ids.add(agent_id)
                total_readings += len(readings)
                for reading in readings:
                    strain_sum += reading.strain_score

            total_deformations = 0
            for agent_id, deformations in self._deformations.items():
                agent_ids.add(agent_id)
                total_deformations += len(deformations)

            total_snapshots = 0
            for agent_id, snapshots in self._snapshots.items():
                agent_ids.add(agent_id)
                total_snapshots += len(snapshots)

            total_snaps = 0
            for agent_id, snaps in self._snaps.items():
                agent_ids.add(agent_id)
                total_snaps += len(snaps)

            for plan in self._plans:
                agent_ids.add(plan.agent_id)

            avg_strain = (
                round(strain_sum / total_readings, 4) if total_readings else 0.0
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive the
                # regime from the average strain so the stats reflect
                # real state rather than the default STIFF.
                dominant_regime = _determine_regime(avg_strain)
            else:
                dominant_regime = ElasticityRegime.STIFF

            return ElasticityStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_deformations=total_deformations,
                total_snapshots=total_snapshots,
                total_snaps=total_snaps,
                avg_strain=avg_strain,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveElasticity] = None
_engine_lock = threading.Lock()


def get_elasticity_engine() -> AgentCognitiveElasticity:
    """Get or create the singleton ``AgentCognitiveElasticity`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveElasticity()
    return _engine


def reset_elasticity_engine() -> None:
    """Reset the singleton ``AgentCognitiveElasticity`` instance.

    Drops the reference to the current engine so the next
    ``get_elasticity_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
