"""Agent Cognitive Cohesion Engine — binding attractive force between cognitive elements

Cognitive cohesion is how tightly an agent's ideas, beliefs, and patterns hold
together as a unified whole. It is the attractive inverse of tension and the
substrate on which coherence, solidity, and resonance do their work: without
binding, there is nothing to be consistent, dense, or resonant.

Core capabilities:
  - Regime: SCATTERED (no binding) through BOUND to UNIFIED (indivisible)
  - Binding Forces: ASSOCIATION, CAUSATION, SIMILARITY, COMPLEMENTARITY, IDENTITY, NARRATIVE
  - Integration: WEAVE, ANCHOR, BRIDGE, MERGE, SCAFFOLD, DISSOLVE
  - Stages: SEPARATED -> TOUCHING -> LINKING -> BINDING -> FUSING -> UNIFIED

Architecture:
  AgentCognitiveCohesion (singleton)
  ├── CohesionReading, BindingRecord, CohesionSnapshot, FusionRecord
  └── IntegrationPlan, CohesionProfile, CohesionStats
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
    trivially interchangeable for testing — tests can monkey-patch
    ``_now`` to a deterministic function rather than reach into every
    record type.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/binding/etc.

    The identifier is the first eight characters of a UUID4, short
    enough to be readable in logs and long enough that collisions are
    negligible for an in-memory engine. Shorter ids are easier to scan
    visually when many records are returned together; full UUIDs are
    unnecessary here.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` cohesion score. A low-side default
    is safer than a mid-range one for cohesion-like quantities where a
    spurious high reading would inflate the perceived binding and push
    the agent's regime toward UNIFIED.
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
    """Clamp a duration in milliseconds to a non-negative value.

    Durations must be non-negative; negative values are coerced to 0
    rather than rejected so a misconfigured caller cannot crash the
    engine. The upper bound is left open because real stage-hold
    intervals can legitimately be very large — a binding may sit in
    the BINDING stage for an arbitrarily long time before fusing.
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
    against member values (e.g. ``"scattered"``) and then against
    member names (e.g. ``"SCATTERED"``), so callers may pass either
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


def _determine_regime(avg_cohesion: float) -> "CohesionRegime":
    """Classify a cohesion regime from the average cohesion score.

    The average cohesion is clamped to [0, 1] where higher means a
    more tightly bound structure. The bands are applied in order, so
    the first matching band wins: below 0.15 the structure is SCATTERED
    (elements fly apart, no binding); below 0.35 it is LOOSE (present
    but barely connected); below 0.55 it is CLUSTERED (local clumps but
    no global binding); below 0.75 it is BOUND (held together as a
    body); below 0.9 it is INTEGRATED (interlocked and mutually
    supporting); otherwise it is UNIFIED (functions as a single
    piece, separation would require breaking).
    """
    avg = _clamp(avg_cohesion, 0.0, 1.0)
    if avg < 0.15:
        return CohesionRegime.SCATTERED
    if avg < 0.35:
        return CohesionRegime.LOOSE
    if avg < 0.55:
        return CohesionRegime.CLUSTERED
    if avg < 0.75:
        return CohesionRegime.BOUND
    if avg < 0.9:
        return CohesionRegime.INTEGRATED
    return CohesionRegime.UNIFIED


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CohesionAxis(str, Enum):
    """The axis along which a cohesion reading is taken.

    Each axis names a different kind of binding whose attractive force
    can be measured. CONCEPTUAL is the binding between ideas — how
    tightly concepts pull toward one another. EMOTIONAL is the binding
    between feelings — how tightly affects cling together and color
    one another. NARRATIVE is the binding across a story — how tightly
    the episodes of a thread hold together. BEHAVIORAL is the binding
    between actions — how tightly patterns of conduct reinforce one
    another. SOCIAL is the binding across roles and relations — how
    tightly the agent's interpersonal elements hold together.
    TEMPORAL is the binding across time — how tightly the agent's
    past, present, and anticipated selves hold together as one
    continuous thread.
    """
    CONCEPTUAL = "conceptual"    # binding between ideas
    EMOTIONAL = "emotional"      # binding between feelings
    NARRATIVE = "narrative"      # binding across a story
    BEHAVIORAL = "behavioral"    # binding between actions
    SOCIAL = "social"            # binding across roles and relations
    TEMPORAL = "temporal"        # binding across time


class CohesionRegime(str, Enum):
    """The regime an agent's cohesion occupies, classified by binding.

    Ranges from SCATTERED (elements fly apart, no binding) through
    LOOSE (present but barely connected), CLUSTERED (local clumps but
    no global binding), BOUND (held together as a body), and
    INTEGRATED (interlocked and mutually supporting) to UNIFIED
    (functions as a single piece, separation would require breaking).
    The regime is derived from the average cohesion across the
    agent's readings via ``_determine_regime``.
    """
    SCATTERED = "scattered"      # elements fly apart, no binding
    LOOSE = "loose"              # present but barely connected
    CLUSTERED = "clustered"      # local clumps, no global binding
    BOUND = "bound"              # held together as a body
    INTEGRATED = "integrated"    # interlocked and mutually supporting
    UNIFIED = "unified"          # functions as a single piece


class BindingForce(str, Enum):
    """The kind of attractive force that binds two elements together.

    Each force names a different way elements can attract one another,
    ordered roughly from weakest to strongest. ASSOCIATION is the
    loosest: two elements co-occur and so recall one another.
    CAUSATION links by cause and effect: one element follows from the
    other. SIMILARITY links by resemblance: two elements share enough
    features to attract. COMPLEMENTARITY links by fit: two elements
    differ in just the way that lets them complete one another.
    IDENTITY links by sameness: two elements are recognized as the
    same thing seen twice. NARRATIVE links by story: two elements
    belong to the same unfolding thread.
    """
    ASSOCIATION = "association"        # co-occurrence
    CAUSATION = "causation"            # cause and effect
    SIMILARITY = "similarity"         # resemblance
    COMPLEMENTARITY = "complementarity"  # fit / mutual completion
    IDENTITY = "identity"             # sameness
    NARRATIVE = "narrative"           # shared story


class IntegrationStrategy(str, Enum):
    """Strategy for changing the cohesion of a structure deliberately.

    WEAVE interleaves elements so their strands lock into one another.
    ANCHOR fixes one element as a stable point that others bind to.
    BRIDGE connects distant elements via an intermediary when they
    cannot bind directly. MERGE combines elements into a single whole,
    giving up their separate identities. SCAFFOLD provides temporary
    external structure to support a binding that cannot yet hold its
    own weight. DISSOLVE deliberately unbinds elements, releasing a
    cohesion that has grown too tight. Each strategy is suited to a
    different situation, from gathering scattered ideas to loosening
    a fusion that has locked the agent into rigidity.
    """
    WEAVE = "weave"          # interleave strands so they lock
    ANCHOR = "anchor"        # fix a stable point others bind to
    BRIDGE = "bridge"        # connect via an intermediary
    MERGE = "merge"          # combine into a single whole
    SCAFFOLD = "scaffold"    # temporary support for a weak binding
    DISSOLVE = "dissolve"    # deliberately unbind elements


class CohesionStage(str, Enum):
    """The lifecycle stage of a binding between elements.

    SEPARATED is the starting state: elements are apart, with no
    attraction. TOUCHING is the state at which elements are adjacent
    but not yet bound. LINKING is the phase in which connections
    begin to form between elements. BINDING is the phase in which
    those connections strengthen into load-bearing bonds. FUSING is
    the phase in which the bonds grow so tight that the elements
    begin to lose their separate identities. UNIFIED is the final
    state at which the elements function as a single piece and
    separation would require breaking. The engine records transitions
    between stages as FusionRecord entries.
    """
    SEPARATED = "separated"    # apart, no attraction
    TOUCHING = "touching"      # adjacent but not bound
    LINKING = "linking"        # connections forming
    BINDING = "binding"        # bonds strengthening
    FUSING = "fusing"          # identities beginning to merge
    UNIFIED = "unified"        # function as a single piece


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CohesionReading:
    """One observation of cohesion on a particular axis.

    ``axis`` is the ``CohesionAxis`` the reading is taken on.
    ``cohesion_score`` in [0, 1] measures how tightly the elements
    bind — 0 means fully scattered, 1 means fully unified.
    ``binding_force`` is the ``BindingForce`` observed holding the
    elements together. ``intensity`` in [0, 1] measures how emphatic
    the observation was. ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: CohesionAxis
    cohesion_score: float          # 0..1, higher = more tightly bound
    binding_force: BindingForce
    intensity: float               # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CohesionAxis, self.axis),
            "cohesion_score": self.cohesion_score,
            "binding_force": _enum_value(BindingForce, self.binding_force),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BindingRecord:
    """One binding event that changed the cohesion of a structure.

    ``axis`` is the ``CohesionAxis`` on which the binding occurred.
    ``binding_force`` is the ``BindingForce`` that drove the change.
    ``before_score`` in [0, 1] is the cohesion before the event;
    ``after_score`` in [0, 1] is the cohesion after. ``binding_strength``
    in [0, ∞) measures how strong the binding force was. ``notes`` is
    an optional free-form annotation.
    """
    binding_id: str
    agent_id: str
    axis: CohesionAxis
    binding_force: BindingForce
    before_score: float            # 0..1, cohesion before binding
    after_score: float             # 0..1, cohesion after binding
    binding_strength: float        # 0..inf, strength of the binding force
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this binding record to a plain dict, expanding enums via ``.value``."""
        return {
            "binding_id": self.binding_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(CohesionAxis, self.axis),
            "binding_force": _enum_value(BindingForce, self.binding_force),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "binding_strength": self.binding_strength,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CohesionSnapshot:
    """Aggregate cohesion state for one agent at one moment.

    ``avg_cohesion`` in [0, 1] is the mean cohesion score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is
    the most frequent ``CohesionAxis`` among those readings, or
    CONCEPTUAL if none. ``regime`` is derived via ``_determine_regime``
    from ``avg_cohesion``. ``binding_count`` is the number of binding
    events recorded against the agent. ``notes`` is an optional
    free-form annotation.
    """
    snapshot_id: str
    agent_id: str
    avg_cohesion: float
    dominant_axis: CohesionAxis
    regime: CohesionRegime
    binding_count: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_cohesion": self.avg_cohesion,
            "dominant_axis": _enum_value(CohesionAxis, self.dominant_axis),
            "regime": _enum_value(CohesionRegime, self.regime),
            "binding_count": self.binding_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class IntegrationPlan:
    """A plan to change the cohesion of a structure with a strategy.

    ``strategy`` is the ``IntegrationStrategy`` chosen. ``target_cohesion``
    in [0, 1] is the cohesion the plan aims to reach. ``rationale``
    explains why this strategy was chosen for this structure.
    """
    plan_id: str
    agent_id: str
    strategy: IntegrationStrategy
    target_cohesion: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(IntegrationStrategy, self.strategy),
            "target_cohesion": self.target_cohesion,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class FusionRecord:
    """One record of a stage transition in the cohesion lifecycle.

    ``from_stage`` is the ``CohesionStage`` the agent's binding was in
    before the transition. ``to_stage`` is the ``CohesionStage`` it
    moved to. ``interval_ms`` in [0, ∞) is the duration the
    from_stage held before the transition. ``signature`` is a
    free-form label that describes the character of the transition
    (e.g. "slow link", "sudden fuse", "deliberate dissolve").
    """
    fusion_id: str
    agent_id: str
    from_stage: CohesionStage
    to_stage: CohesionStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this fusion record to a plain dict, expanding enums via ``.value``."""
        return {
            "fusion_id": self.fusion_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(CohesionStage, self.from_stage),
            "to_stage": _enum_value(CohesionStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class CohesionProfile:
    """Per-agent aggregate cohesion tendencies.

    ``avg_cohesion`` in [0, 1] is the mean cohesion score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``CohesionAxis`` among the agent's readings, or CONCEPTUAL
    if none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_cohesion``. ``total_readings``, ``total_bindings``, and
    ``total_fusions`` are the counts of each record type for the
    agent.
    """
    agent_id: str
    avg_cohesion: float = 0.0
    dominant_axis: CohesionAxis = CohesionAxis.CONCEPTUAL
    regime: CohesionRegime = CohesionRegime.CLUSTERED
    total_readings: int = 0
    total_bindings: int = 0
    total_fusions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_cohesion": self.avg_cohesion,
            "dominant_axis": _enum_value(CohesionAxis, self.dominant_axis),
            "regime": _enum_value(CohesionRegime, self.regime),
            "total_readings": self.total_readings,
            "total_bindings": self.total_bindings,
            "total_fusions": self.total_fusions,
        }


@dataclass
class CohesionStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_cohesion`` is the mean cohesion score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the
    most frequent regime across all cached profiles, or CLUSTERED when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_bindings: int = 0
    total_snapshots: int = 0
    total_fusions: int = 0
    avg_cohesion: float = 0.0
    dominant_regime: CohesionRegime = CohesionRegime.CLUSTERED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_bindings": self.total_bindings,
            "total_snapshots": self.total_snapshots,
            "total_fusions": self.total_fusions,
            "avg_cohesion": self.avg_cohesion,
            "dominant_regime": _enum_value(CohesionRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCohesion:
    """Thread-safe engine that models an agent's cognitive cohesion.

    The engine holds six stores: ``_readings`` (CohesionReading lists
    keyed by agent_id), ``_bindings`` (BindingRecord lists keyed by
    agent_id), ``_snapshots`` (CohesionSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of IntegrationPlan),
    ``_fusions`` (FusionRecord lists keyed by agent_id), and
    ``_profiles`` (CohesionProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The cohesion model is deliberately heuristic: cohesion scores and
    intensities are caller-supplied observations; cohesion regimes
    are banded from the average cohesion; dominant axes are computed
    by mode; stage transitions are recorded as observed. These
    heuristics are transparent and auditable rather than learned,
    which keeps the engine deterministic.

    The engine is intentionally agnostic about how cohesion is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure cohesion itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, bindings, snapshots, or fusions change, so
    ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose cohesion scores feed into a
    # snapshot's average cohesion. The window is long enough to smooth
    # a single noisy reading and short enough to reflect the agent's
    # current cohesion posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty cohesion engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[CohesionReading]] = {}
        self._bindings: Dict[str, List[BindingRecord]] = {}
        self._snapshots: Dict[str, List[CohesionSnapshot]] = {}
        self._plans: List[IntegrationPlan] = []
        self._fusions: Dict[str, List[FusionRecord]] = {}
        self._profiles: Dict[str, CohesionProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_cohesion_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._bindings.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._fusions.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[CohesionReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_bindings_locked(
        self, agent_id: str
    ) -> List[BindingRecord]:
        """Return one agent's binding records in insertion order. Caller holds the lock."""
        return list(self._bindings.get(agent_id, []))

    def _agent_fusions_locked(
        self, agent_id: str
    ) -> List[FusionRecord]:
        """Return one agent's fusion records in insertion order. Caller holds the lock."""
        return list(self._fusions.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[CohesionReading]
    ) -> CohesionAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns CONCEPTUAL if the list is
        empty, since CONCEPTUAL is the smallest and most neutral
        axis. Caller holds the lock.
        """
        if not readings:
            return CohesionAxis.CONCEPTUAL
        counts: Counter = Counter()
        first_seen_order: Dict[CohesionAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: CohesionAxis = readings[0].axis
        best_count = -1
        for axis, count in counts.items():
            if (count > best_count) or (
                count == best_count
                and first_seen_order.get(axis, 0)
                < first_seen_order.get(best_axis, 0)
            ):
                best_axis = axis
                best_count = count
        return best_axis

    def _mode_regime_locked(
        self, profiles: List[CohesionProfile]
    ) -> CohesionRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns CLUSTERED if the list is empty, since CLUSTERED is the
        neutral mid-range regime — neither too scattered nor too
        unified. Caller holds the lock.
        """
        if not profiles:
            return CohesionRegime.CLUSTERED
        counts: Dict[CohesionRegime, int] = {}
        for profile in profiles:
            counts[profile.regime] = counts.get(profile.regime, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _current_cohesion_locked(self, agent_id: str) -> float:
        """Return the agent's most recent cohesion score, or the mean if none recent.

        Prefers the cohesion score of the most recent reading, falling
        back to the mean of all readings when there is no clear
        most-recent one. Returns 0.0 when the agent has no readings.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        most_recent = readings[-1]
        return float(most_recent.cohesion_score)

    def _compute_profile_locked(self, agent_id: str) -> CohesionProfile:
        """Aggregate an agent's readings, bindings, and fusions into a profile.

        See ``CohesionProfile`` for field semantics. ``avg_cohesion`` is
        the mean cohesion score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent ``CohesionAxis``
        among the agent's readings, or CONCEPTUAL if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_cohesion``.
        ``total_readings``, ``total_bindings``, and ``total_fusions``
        count the records held for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        bindings = self._agent_bindings_locked(agent_id)
        fusions = self._agent_fusions_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_cohesion = sum(r.cohesion_score for r in readings) / len(
                readings
            )
        else:
            avg_cohesion = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        regime = _determine_regime(avg_cohesion)

        return CohesionProfile(
            agent_id=str(agent_id),
            avg_cohesion=round(avg_cohesion, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=total_readings,
            total_bindings=len(bindings),
            total_fusions=len(fusions),
        )

    # ── Cohesion Readings ─────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        cohesion_score: float,
        binding_force: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> CohesionReading:
        """Record a cohesion reading for an agent and return it.

        ``axis`` may be passed as a ``CohesionAxis`` member or its
        string name/value. ``cohesion_score`` and ``intensity`` are
        clamped to [0, 1]. ``binding_force`` may be passed as a
        ``BindingForce`` member or its string name/value. The reading
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = CohesionReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CohesionAxis, axis),
                cohesion_score=_clamp(cohesion_score, 0.0, 1.0),
                binding_force=_resolve_enum(BindingForce, binding_force),
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
    ) -> List[CohesionReading]:
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

    def get_reading(self, reading_id: str) -> CohesionReading:
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

    # ── Binding Records ──────────────────────────────────────────

    def record_binding(
        self,
        agent_id: str,
        axis: Any,
        binding_force: Any,
        before_score: float,
        after_score: float,
        binding_strength: float,
        notes: Optional[str] = None,
    ) -> BindingRecord:
        """Record a binding event for an agent and return it.

        ``axis`` may be passed as a ``CohesionAxis`` member or its
        string name/value. ``binding_force`` may be passed as a
        ``BindingForce`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``binding_strength`` is clamped to [0, ∞). The binding is
        stored and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            record = BindingRecord(
                binding_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(CohesionAxis, axis),
                binding_force=_resolve_enum(BindingForce, binding_force),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                binding_strength=_clamp_positive_ms(binding_strength),
                timestamp=_now(),
                notes=notes,
            )
            self._bindings.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_bindings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BindingRecord]:
        """Return binding records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all bindings are considered;
        otherwise only bindings for that agent are returned. The most
        recently recorded ``limit`` bindings are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                bindings = self._agent_bindings_locked(agent_id)
            else:
                bindings = []
                for agent_bindings in self._bindings.values():
                    bindings.extend(agent_bindings)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return bindings[-n:] if n else []

    def get_binding(self, binding_id: str) -> BindingRecord:
        """Retrieve a binding record by id.

        Raises ``ValueError`` if no binding exists with that id.
        """
        with self._lock:
            for agent_bindings in self._bindings.values():
                for binding in agent_bindings:
                    if binding.binding_id == binding_id:
                        return binding
        raise ValueError(f"binding {binding_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CohesionSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_cohesion`` is the mean cohesion score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``CohesionAxis`` among those readings, or CONCEPTUAL if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_cohesion``. ``binding_count`` is the number of binding
        events recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_cohesion = sum(
                    r.cohesion_score for r in recent
                ) / len(recent)
            else:
                avg_cohesion = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_cohesion)
            binding_count = len(self._agent_bindings_locked(agent_id))

            snapshot = CohesionSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_cohesion=round(avg_cohesion, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                binding_count=binding_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CohesionSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> CohesionSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Integration Plans ──────────────────────────────────────────

    def plan_integration(
        self,
        agent_id: str,
        strategy: Any,
        target_cohesion: float,
        rationale: str,
    ) -> IntegrationPlan:
        """Record an integration plan for an agent and return it.

        ``strategy`` may be passed as an ``IntegrationStrategy`` member
        or its string name/value. ``target_cohesion`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured cohesion.
        """
        with self._lock:
            plan = IntegrationPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(IntegrationStrategy, strategy),
                target_cohesion=_clamp(target_cohesion, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[IntegrationPlan]:
        """Return integration plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> IntegrationPlan:
        """Retrieve an integration plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Fusion Records ───────────────────────────────────────────

    def record_fusion(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> FusionRecord:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``CohesionStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label that
        describes the character of the transition (e.g. "slow link",
        "sudden fuse", "deliberate dissolve"). The fusion record is
        stored and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            record = FusionRecord(
                fusion_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(CohesionStage, from_stage),
                to_stage=_resolve_enum(CohesionStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._fusions.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_fusions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FusionRecord]:
        """Return fusion records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all fusions are considered;
        otherwise only fusions for that agent are returned. The most
        recently recorded ``limit`` fusion records are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                fusions = self._agent_fusions_locked(agent_id)
            else:
                fusions = []
                for agent_fusions in self._fusions.values():
                    fusions.extend(agent_fusions)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return fusions[-n:] if n else []

    def get_fusion(self, fusion_id: str) -> FusionRecord:
        """Retrieve a fusion record by id.

        Raises ``ValueError`` if no fusion record exists with that id.
        """
        with self._lock:
            for agent_fusions in self._fusions.values():
                for record in agent_fusions:
                    if record.fusion_id == fusion_id:
                        return record
        raise ValueError(f"fusion record {fusion_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CohesionProfile:
        """Return the agent's cohesion profile, building it if missing.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, bindings, snapshots, or fusions change.
        If the agent has data but no profile yet, the profile is built
        from the live stores. Call ``update_profile`` to force a
        refresh or override a computed field. Field semantics are
        documented on ``CohesionProfile`` and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> CohesionProfile:
        """Refresh and optionally override fields of an agent's cohesion profile.

        The profile is first recomputed from the live stores, then
        any supplied keyword overrides (matching ``CohesionProfile``
        field names) are applied. Accepted overrides: ``avg_cohesion``
        (float), ``dominant_axis`` (``CohesionAxis``), ``regime``
        (``CohesionRegime``), ``total_readings``, ``total_bindings``,
        ``total_fusions`` (int). Enum-valued overrides may be passed
        as the enum member or its string name/value. Unknown keys are
        ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_cohesion":
                    try:
                        profile.avg_cohesion = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            CohesionAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(
                            CohesionRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_bindings",
                    "total_fusions",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CohesionProfile]:
        """Return all stored cohesion profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> CohesionStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, bindings, snapshots, and fusions. Scalar
        totals are the counts of each record type. ``avg_cohesion`` is
        the mean cohesion score across all readings, or 0.0 when none
        exist. ``dominant_regime`` is the most frequent regime across
        all cached profiles, or CLUSTERED when none exist. When no
        profiles exist but readings do, the dominant regime is derived
        from the average cohesion via ``_determine_regime`` so the
        stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._bindings.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._fusions.keys())

            total_readings = 0
            cohesion_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    cohesion_sum += reading.cohesion_score
            avg_cohesion = (
                round(cohesion_sum / total_readings, 4) if total_readings else 0.0
            )

            total_bindings = sum(
                len(agent_bindings)
                for agent_bindings in self._bindings.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_fusions = sum(
                len(agent_fusions) for agent_fusions in self._fusions.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average cohesion so the stats
                # reflect real state rather than the default CLUSTERED.
                dominant_regime = _determine_regime(avg_cohesion)
            else:
                dominant_regime = CohesionRegime.CLUSTERED

            return CohesionStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_bindings=total_bindings,
                total_snapshots=total_snapshots,
                total_fusions=total_fusions,
                avg_cohesion=avg_cohesion,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCohesion] = None
_engine_lock = threading.Lock()


def get_cohesion_engine() -> AgentCognitiveCohesion:
    """Get or create the singleton ``AgentCognitiveCohesion`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveCohesion()
    return _engine


def reset_cohesion_engine() -> None:
    """Reset the singleton ``AgentCognitiveCohesion`` instance.

    Drops the reference to the current engine so the next
    ``get_cohesion_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
