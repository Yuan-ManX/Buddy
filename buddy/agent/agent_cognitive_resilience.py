"""Agent Cognitive Resilience Engine — absorbing shocks and recovering

Resilience measures the capacity to take a hit, recover function, and grow,
distinct from inertia, momentum, turbulence, and immunity.

Core capabilities:
  - Readings, stress events, regimes, plans, recoveries, profiles, stats

Architecture:
  AgentCognitiveResilience (singleton)
  ├── ResilienceReading     (one observation of an agent's capacity)
  ├── StressEvent           (one shock applied to an agent)
  ├── ResilienceSnapshot    (aggregate resilience state for one agent)
  ├── AdaptationPlan        (a plan to grow the agent's resilience)
  ├── RecoveryRecord        (one record of a recovery transition)
  ├── ResilienceProfile     (per-agent aggregate resilience tendencies)
  └── ResilienceStats       (engine-wide aggregate statistics)
"""

from __future__ import annotations

import threading
import time
import uuid
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
    """Generate a short unique identifier for a reading/event/snapshot/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` magnitude. A low-side default is
    safer than a mid-range one for capacity-like quantities where a
    spurious high reading would inflate the perceived resilience.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return low
    if f < low:
        return low
    if f > high:
        return f
    return f


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first
    against member values (e.g. ``"supple"``) and then against member
    names (e.g. ``"SUPPLE"``), so callers may pass either form. This
    lets the public API accept either the symbolic name or the
    lower-case value string from JSON payloads. Raises ``ValueError`` if
    neither matches.
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


def _determine_regime(avg_resilience: float) -> "ResilienceRegime":
    """Classify a resilience regime from the average capacity.

    The average is clamped to [0, 1] where higher means more resilient.
    The bands are applied in order: below 0.15 the agent is BRITTLE
    (shatters on impact); below 0.35 it is FRAGILE (cracks before it
    breaks); below 0.55 it is SUPPLE (bends under load, returns to
    form); below 0.75 it is TOUGH (absorbs significant energy before
    yielding); below 0.92 it is HARDY (takes heavy shocks in stride);
    otherwise it is ANTIFRAGILE (grows stronger from shocks). The
    progression mirrors the materials-science scale from brittle to
    antifragile.
    """
    ar = _clamp(avg_resilience, 0.0, 1.0)
    if ar < 0.15:
        return ResilienceRegime.BRITTLE
    if ar < 0.35:
        return ResilienceRegime.FRAGILE
    if ar < 0.55:
        return ResilienceRegime.SUPPLE
    if ar < 0.75:
        return ResilienceRegime.TOUGH
    if ar < 0.92:
        return ResilienceRegime.HARDY
    return ResilienceRegime.ANTIFRAGILE


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CapacityType(str, Enum):
    """The kind of capacity an agent's resilience rests on.

    Each type describes a different substrate of resilience. See the
    module docstring for the full description; the inline comment on
    each member is a short label.
    """
    EMOTIONAL = "emotional"      # affect-based capacity
    EPISTEMIC = "epistemic"      # belief-based capacity
    PROCEDURAL = "procedural"    # process-based capacity
    CONTEXTUAL = "contextual"    # context-based capacity
    STRUCTURAL = "structural"    # framework-based capacity
    RELATIONAL = "relational"    # relationship-based capacity


class ResilienceRegime(str, Enum):
    """The resilience regime an agent occupies.

    Ranges from BRITTLE (shatters on impact) through FRAGILE (cracks
    before breaking), SUPPLE (bends and returns), and TOUGH (absorbs
    significant energy) to HARDY (takes heavy shocks in stride) and
    ANTIFRAGILE (grows stronger from shocks). The regime is derived
    from the average capacity across the agent's readings via
    ``_determine_regime``.
    """
    BRITTLE = "brittle"          # shatters on impact
    FRAGILE = "fragile"          # cracks before it breaks
    SUPPLE = "supple"            # bends under load, returns to form
    TOUGH = "tough"              # absorbs significant energy
    HARDY = "hardy"              # takes heavy shocks in stride
    ANTIFRAGILE = "antifragile"  # grows stronger from shocks


class RecoveryState(str, Enum):
    """The stage of an agent's recovery from stress.

    BROKEN means the agent has failed to recover. STRESSED means
    acute load but still functioning. STRAINED means function is
    degraded. RECOVERING means actively returning to baseline.
    STABLE means at baseline, functioning normally. FLOURISHING
    means the agent has emerged from recovery stronger than before.
    Each state represents a different point on the recovery curve.
    """
    BROKEN = "broken"            # failed to recover
    STRESSED = "stressed"        # acute load, still functioning
    STRAINED = "strained"        # function degraded
    RECOVERING = "recovering"    # actively returning to baseline
    STABLE = "stable"            # at baseline
    FLOURISHING = "flourishing"  # emerged stronger


class AdaptationStrategy(str, Enum):
    """Strategy for growing an agent's resilience.

    ABSORB takes the hit and returns to form. REDISTRIBUTE spreads
    load across multiple capacities. TRANSFORM converts the shock
    into useful work. RENEW deliberately cycles capacity, allowing
    controlled degradation to come back stronger. GROW exposes the
    agent to calibrated shocks to build capacity. ANTICIPATE builds
    capacity for shocks before they arrive. Each strategy suits a
    different position on the brittle-to-antifragile axis.
    """
    ABSORB = "absorb"            # take the hit, return to form
    REDISTRIBUTE = "redistribute"  # spread the load
    TRANSFORM = "transform"      # convert shock to work
    RENEW = "renew"              # cycle capacity, rebuild
    GROW = "grow"                # build capacity through exposure
    ANTICIPATE = "anticipate"    # prepare capacity in advance


class StressSignature(str, Enum):
    """The temporal shape of a stress event.

    IMPULSE is a single, brief hit. SUSTAINED is prolonged pressure.
    CYCLIC recurs periodically. ESCALATING grows over time. COMPOUND
    is multiple distinct sources hitting simultaneously. CASCADING is
    one shock triggering another, propagating through the system. The
    signature tells the agent what shape of recovery to plan for.
    """
    IMPULSE = "impulse"          # single brief hit
    SUSTAINED = "sustained"      # prolonged pressure
    CYCLIC = "cyclic"            # recurring periodically
    ESCALATING = "escalating"    # growing over time
    COMPOUND = "compound"        # multiple sources at once
    CASCADING = "cascading"      # one shock triggering another


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ResilienceReading:
    """One observation of an agent's resilience capacity.

    ``capacity_type`` classifies the substrate of capacity. ``capacity_score``
    in [0, 1] is the magnitude of that capacity. ``recovery_rate`` in
    [0, 1] is how fast the agent bounces back from shock. ``recovery_state``
    is the ``RecoveryState`` the agent is in. ``intensity`` in [0, 1] is
    the magnitude of the stress being applied when the reading was
    taken. ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    capacity_type: CapacityType
    capacity_score: float        # 0..1, higher = more capacity
    recovery_rate: float         # 0..1, how fast it bounces back
    recovery_state: RecoveryState
    intensity: float             # 0..1, current stress intensity
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "capacity_type": _enum_value(CapacityType, self.capacity_type),
            "capacity_score": self.capacity_score,
            "recovery_rate": self.recovery_rate,
            "recovery_state": _enum_value(RecoveryState, self.recovery_state),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class StressEvent:
    """One stress event (shock) applied to an agent.

    ``source`` is a free-form string naming where the shock came from
    (e.g. ``"user-criticism"``, ``"contradictory-evidence"``).
    ``magnitude`` in [0, 1] is how strong the shock is. ``signature``
    is the ``StressSignature`` describing its temporal shape.
    ``duration_ms`` is the duration of the shock in milliseconds.
    ``notes`` is an optional free-form annotation.
    """
    event_id: str
    agent_id: str
    source: str
    magnitude: float             # 0..1
    signature: StressSignature
    duration_ms: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict, expanding enums via ``.value``."""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "source": self.source,
            "magnitude": self.magnitude,
            "signature": _enum_value(StressSignature, self.signature),
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ResilienceSnapshot:
    """Aggregate resilience state for one agent.

    ``avg_capacity`` in [0, 1] is the mean capacity across the agent's
    recent readings. ``dominant_type`` is the most frequent
    ``CapacityType`` among those readings. ``regime`` is derived via
    ``_determine_regime`` from ``avg_capacity``. ``recovery_state`` is
    the latest reading's recovery state, or STABLE if no readings
    exist. ``event_count`` is the number of stress events recorded
    against the agent. ``notes`` is an optional free-form annotation.
    """
    snapshot_id: str
    agent_id: str
    avg_capacity: float
    dominant_type: CapacityType
    regime: ResilienceRegime
    recovery_state: RecoveryState
    event_count: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_capacity": self.avg_capacity,
            "dominant_type": _enum_value(CapacityType, self.dominant_type),
            "regime": _enum_value(ResilienceRegime, self.regime),
            "recovery_state": _enum_value(RecoveryState, self.recovery_state),
            "event_count": self.event_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class AdaptationPlan:
    """A plan to grow an agent's resilience.

    ``strategy`` is the ``AdaptationStrategy`` chosen. ``target_capacity``
    in [0, 1] is the capacity the plan aims to reach. ``rationale``
    explains why this strategy was chosen for this regime. The plan is
    stored in a flat list (not keyed by agent) since plans are
    forward-looking interventions rather than measurements of state.
    """
    plan_id: str
    agent_id: str
    strategy: AdaptationStrategy
    target_capacity: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(AdaptationStrategy, self.strategy),
            "target_capacity": self.target_capacity,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class RecoveryRecord:
    """One record of a recovery transition.

    ``from_state`` is the ``RecoveryState`` the agent was in before the
    transition. ``to_state`` is the ``RecoveryState`` it moved to.
    ``recovery_ms`` is the time the transition took in milliseconds.
    ``residual_stress`` in [0, 1] is the stress still present after
    the transition (0.0 means fully recovered). ``notes`` is an
    optional free-form annotation.
    """
    recovery_id: str
    agent_id: str
    from_state: RecoveryState
    to_state: RecoveryState
    recovery_ms: int
    residual_stress: float       # 0..1
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this record to a plain dict, expanding enums via ``.value``."""
        return {
            "recovery_id": self.recovery_id,
            "agent_id": self.agent_id,
            "from_state": _enum_value(RecoveryState, self.from_state),
            "to_state": _enum_value(RecoveryState, self.to_state),
            "recovery_ms": self.recovery_ms,
            "residual_stress": self.residual_stress,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ResilienceProfile:
    """Per-agent aggregate resilience tendencies.

    ``avg_capacity`` in [0, 1] is the mean capacity across the agent's
    readings (0.0 if none). ``dominant_type`` is the most frequent
    ``CapacityType`` among the agent's readings, or EMOTIONAL if none.
    ``regime`` is derived via ``_determine_regime`` from
    ``avg_capacity``. ``total_readings``, ``total_events``, and
    ``total_recoveries`` are the counts of each record type for the
    agent.
    """
    agent_id: str
    avg_capacity: float = 0.0
    dominant_type: CapacityType = CapacityType.EMOTIONAL
    regime: ResilienceRegime = ResilienceRegime.SUPPLE
    total_readings: int = 0
    total_events: int = 0
    total_recoveries: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_capacity": self.avg_capacity,
            "dominant_type": _enum_value(CapacityType, self.dominant_type),
            "regime": _enum_value(ResilienceRegime, self.regime),
            "total_readings": self.total_readings,
            "total_events": self.total_events,
            "total_recoveries": self.total_recoveries,
            "last_updated": self.last_updated,
        }


@dataclass
class ResilienceStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids that appear in
    any store. ``avg_capacity`` is the mean capacity across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or SUPPLE when none
    exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_events: int = 0
    total_snapshots: int = 0
    total_recoveries: int = 0
    avg_capacity: float = 0.0
    dominant_regime: ResilienceRegime = ResilienceRegime.SUPPLE

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_events": self.total_events,
            "total_snapshots": self.total_snapshots,
            "total_recoveries": self.total_recoveries,
            "avg_capacity": self.avg_capacity,
            "dominant_regime": _enum_value(ResilienceRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveResilience:
    """Thread-safe engine that models an agent's cognitive resilience.

    The engine holds six stores: ``_readings`` (ResilienceReading lists
    keyed by agent_id), ``_events`` (StressEvent lists keyed by
    agent_id), ``_snapshots`` (ResilienceSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of AdaptationPlan), ``_recoveries``
    (RecoveryRecord lists keyed by agent_id), and ``_profiles``
    (ResilienceProfile keyed by agent_id).

    All mutations are guarded by a single reentrant lock so that public
    methods may safely call one another without self-deadlock. The
    resilience model is deliberately heuristic: capacity scores,
    recovery rates, magnitudes, and durations are caller-supplied
    readings; regimes are banded from average capacity; dominant types
    are computed by mode. These heuristics are transparent and
    auditable rather than learned, which keeps the engine
    deterministic.

    The engine is intentionally agnostic about how capacity is
    measured and how stress is detected — callers may derive them from
    any source. The engine's job is to record, aggregate, classify,
    and plan, not to measure resilience itself. Profiles are cached per
    agent and invalidated whenever the agent's readings, events,
    snapshots, or recoveries change, so ``get_profile`` returns a
    fresh aggregate only when the underlying data has changed.
    """

    # Number of most-recent readings whose capacity scores feed into a
    # snapshot's average capacity. The window is long enough to smooth
    # a single noisy reading and short enough to reflect the agent's
    # current capacity posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty resilience engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[ResilienceReading]] = {}
        self._events: Dict[str, List[StressEvent]] = {}
        self._snapshots: Dict[str, List[ResilienceSnapshot]] = {}
        self._plans: List[AdaptationPlan] = []
        self._recoveries: Dict[str, List[RecoveryRecord]] = {}
        self._profiles: Dict[str, ResilienceProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_resilience_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._events.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._recoveries.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[ResilienceReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_events_locked(self, agent_id: str) -> List[StressEvent]:
        """Return one agent's stress events in insertion order. Caller holds the lock."""
        return list(self._events.get(agent_id, []))

    def _agent_snapshots_locked(self, agent_id: str) -> List[ResilienceSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_recoveries_locked(self, agent_id: str) -> List[RecoveryRecord]:
        """Return one agent's recovery records in insertion order. Caller holds the lock."""
        return list(self._recoveries.get(agent_id, []))

    def _mode_type_locked(
        self, readings: List[ResilienceReading]
    ) -> Optional[CapacityType]:
        """Return the most frequent capacity type among the supplied readings.

        Ties are broken by insertion order. Returns ``None`` if the list
        is empty. Caller holds the lock.
        """
        if not readings:
            return None
        counts: Dict[CapacityType, int] = {}
        for reading in readings:
            counts[reading.capacity_type] = (
                counts.get(reading.capacity_type, 0) + 1
            )
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _latest_recovery_state_locked(self, agent_id: str) -> RecoveryState:
        """Return the agent's most recent recovery state, or STABLE.

        STABLE is the default when the agent has no readings, since a
        non-loaded agent is at baseline. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return RecoveryState.STABLE
        # Readings are stored in insertion order, so the last one is
        # the most recent.
        return readings[-1].recovery_state

    def _mode_regime_locked(
        self, profiles: List[ResilienceProfile]
    ) -> ResilienceRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns SUPPLE if the list is empty. SUPPLE is the balanced
        default — neither brittle nor antifragile. Caller holds the
        lock.
        """
        if not profiles:
            return ResilienceRegime.SUPPLE
        counts: Dict[ResilienceRegime, int] = {}
        for profile in profiles:
            counts[profile.regime] = counts.get(profile.regime, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _current_capacity_locked(self, agent_id: str) -> float:
        """Return the mean capacity across the agent's readings.

        Returns 0.0 when the agent has no readings. Caller holds the
        lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        return sum(r.capacity_score for r in readings) / len(readings)

    # ── Resilience Readings ────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        capacity_type: Any,
        capacity_score: float,
        recovery_rate: float,
        recovery_state: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> ResilienceReading:
        """Record a resilience reading for an agent and return it.

        ``capacity_type`` may be passed as a ``CapacityType`` member or
        its string name/value. ``capacity_score`` in [0, 1] is clamped to
        that range. ``recovery_rate`` in [0, 1] is clamped to that
        range. ``recovery_state`` may be passed as a ``RecoveryState``
        member or its string name/value. ``intensity`` in [0, 1] is
        clamped to that range. The reading is stored and returned; the
        agent's cached profile is invalidated.
        """
        with self._lock:
            reading = ResilienceReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                capacity_type=_resolve_enum(CapacityType, capacity_type),
                capacity_score=_clamp(capacity_score, 0.0, 1.0),
                recovery_rate=_clamp(recovery_rate, 0.0, 1.0),
                recovery_state=_resolve_enum(RecoveryState, recovery_state),
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
    ) -> List[ResilienceReading]:
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

    def get_reading(self, reading_id: str) -> ResilienceReading:
        """Retrieve a reading by id.

        Raises ``ValueError`` if no reading exists with that id, so
        callers can treat the return as a guaranteed non-None value and
        let a single exception type stand in for a not-found error.
        """
        with self._lock:
            for agent_readings in self._readings.values():
                for reading in agent_readings:
                    if reading.reading_id == reading_id:
                        return reading
        raise ValueError(f"reading {reading_id!r} not found")

    # ── Stress Events ───────────────────────────────────────────────

    def record_event(
        self,
        agent_id: str,
        source: str,
        magnitude: float,
        signature: Any,
        duration_ms: int,
        notes: Optional[str] = None,
    ) -> StressEvent:
        """Record a stress event for an agent and return it.

        ``source`` is a free-form string naming where the shock came
        from. ``magnitude`` in [0, 1] is clamped to that range.
        ``signature`` may be passed as a ``StressSignature`` member or
        its string name/value. ``duration_ms`` is the duration in
        milliseconds (clamped to non-negative integers). The event is
        stored and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            try:
                ms = int(duration_ms)
            except (TypeError, ValueError):
                ms = 0
            if ms < 0:
                ms = 0
            event = StressEvent(
                event_id=_new_id(),
                agent_id=str(agent_id),
                source=str(source),
                magnitude=_clamp(magnitude, 0.0, 1.0),
                signature=_resolve_enum(StressSignature, signature),
                duration_ms=ms,
                timestamp=_now(),
                notes=notes,
            )
            self._events.setdefault(agent_id, []).append(event)
            self._profiles.pop(agent_id, None)
            return event

    def list_events(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StressEvent]:
        """Return stress events, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all events are considered;
        otherwise only events for that agent are returned. The most
        recently recorded ``limit`` events are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                events = self._agent_events_locked(agent_id)
            else:
                events = []
                for agent_events in self._events.values():
                    events.extend(agent_events)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return events[-n:] if n else []

    def get_event(self, event_id: str) -> StressEvent:
        """Retrieve a stress event by id.

        Raises ``ValueError`` if no event exists with that id.
        """
        with self._lock:
            for agent_events in self._events.values():
                for event in agent_events:
                    if event.event_id == event_id:
                        return event
        raise ValueError(f"stress event {event_id!r} not found")

    # ── Snapshots ───────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> ResilienceSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_capacity`` is the mean capacity across the agent's most
        recent readings (the last ``_SNAPSHOT_READING_WINDOW`` = 20),
        or 0.0 if none. ``dominant_type`` is the most frequent
        ``CapacityType`` among those readings, or EMOTIONAL if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_capacity``. ``recovery_state`` is the latest reading's
        recovery state, or STABLE if no readings exist.
        ``event_count`` is the number of stress events recorded against
        the agent. The snapshot is stored and returned; the agent's
        cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_capacity = sum(
                    r.capacity_score for r in recent
                ) / len(recent)
            else:
                avg_capacity = 0.0

            dominant_type = self._mode_type_locked(recent)
            if dominant_type is None:
                dominant_type = CapacityType.EMOTIONAL

            regime = _determine_regime(avg_capacity)
            recovery_state = self._latest_recovery_state_locked(agent_id)
            event_count = len(self._agent_events_locked(agent_id))

            snapshot = ResilienceSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_capacity=round(avg_capacity, 4),
                dominant_type=dominant_type,
                regime=regime,
                recovery_state=recovery_state,
                event_count=event_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ResilienceSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The most
        recently taken ``limit`` snapshots are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
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

    def get_snapshot(self, snapshot_id: str) -> ResilienceSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Adaptation Plans ────────────────────────────────────────────

    def plan_adaptation(
        self,
        agent_id: str,
        strategy: Any,
        target_capacity: float,
        rationale: str,
    ) -> AdaptationPlan:
        """Record an adaptation plan for an agent and return it.

        ``strategy`` may be passed as an ``AdaptationStrategy`` member
        or its string name/value. ``target_capacity`` in [0, 1] is
        clamped to that range. ``rationale`` explains why this strategy
        was chosen. The plan is stored in a flat list (not keyed by
        agent, since plans are forward-looking interventions rather
        than measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured capacity.
        """
        with self._lock:
            plan = AdaptationPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(AdaptationStrategy, strategy),
                target_capacity=_clamp(target_capacity, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AdaptationPlan]:
        """Return adaptation plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> AdaptationPlan:
        """Retrieve an adaptation plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"adaptation plan {plan_id!r} not found")

    # ── Recovery Records ────────────────────────────────────────────

    def record_recovery(
        self,
        agent_id: str,
        from_state: Any,
        to_state: Any,
        recovery_ms: int,
        residual_stress: float,
        notes: Optional[str] = None,
    ) -> RecoveryRecord:
        """Record a recovery transition for an agent and return it.

        ``from_state`` and ``to_state`` may each be passed as a
        ``RecoveryState`` member or its string name/value.
        ``recovery_ms`` is the time the transition took in milliseconds
        (clamped to non-negative integers). ``residual_stress`` in
        [0, 1] is the stress still present after the transition
        (0.0 means fully recovered). The record is stored and returned;
        the agent's cached profile is invalidated.
        """
        with self._lock:
            try:
                ms = int(recovery_ms)
            except (TypeError, ValueError):
                ms = 0
            if ms < 0:
                ms = 0
            record = RecoveryRecord(
                recovery_id=_new_id(),
                agent_id=str(agent_id),
                from_state=_resolve_enum(RecoveryState, from_state),
                to_state=_resolve_enum(RecoveryState, to_state),
                recovery_ms=ms,
                residual_stress=_clamp(residual_stress, 0.0, 1.0),
                timestamp=_now(),
                notes=notes,
            )
            self._recoveries.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_recoveries(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RecoveryRecord]:
        """Return recovery records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all recoveries are considered;
        otherwise only recoveries for that agent are returned. The most
        recently recorded ``limit`` recoveries are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                recoveries = self._agent_recoveries_locked(agent_id)
            else:
                recoveries = []
                for agent_recoveries in self._recoveries.values():
                    recoveries.extend(agent_recoveries)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return recoveries[-n:] if n else []

    def get_recovery(self, recovery_id: str) -> RecoveryRecord:
        """Retrieve a recovery record by id.

        Raises ``ValueError`` if no recovery record exists with that id.
        """
        with self._lock:
            for agent_recoveries in self._recoveries.values():
                for recovery in agent_recoveries:
                    if recovery.recovery_id == recovery_id:
                        return recovery
        raise ValueError(f"recovery record {recovery_id!r} not found")

    # ── Profiles ────────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> ResilienceProfile:
        """Return the agent's resilience profile, computing it if absent.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, events, snapshots, or recoveries change.
        If the agent has data but no profile yet, one is built from the
        existing data. Call ``update_profile`` to force a refresh or
        override a computed field. Field semantics are documented on
        ``ResilienceProfile`` and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> ResilienceProfile:
        """Refresh and optionally override fields of an agent's resilience profile.

        The profile is first recomputed from the live stores, then any
        supplied keyword overrides (matching ``ResilienceProfile`` field
        names) are applied, and ``last_updated`` is stamped. Accepted
        overrides: ``avg_capacity`` (float), ``dominant_type``
        (``CapacityType``), ``regime`` (``ResilienceRegime``),
        ``total_readings``, ``total_events``, ``total_recoveries``
        (int). Enum-valued overrides may be passed as the enum member
        or its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_capacity":
                    try:
                        profile.avg_capacity = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_type":
                    try:
                        profile.dominant_type = _resolve_enum(
                            CapacityType, value
                        )
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(
                            ResilienceRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_events",
                    "total_recoveries",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[ResilienceProfile]:
        """Return all stored resilience profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ──────────────────────────────────────────────────

    def get_stats(self) -> ResilienceStats:
        """Compute engine-wide aggregate statistics.

        Scalar totals are computed by scanning the stores.
        ``total_agents`` is the number of distinct agent_ids that
        appear in any store. ``avg_capacity`` is the mean capacity
        across all readings, or 0.0 when none exist. ``dominant_regime``
        is the most frequent regime across all cached profiles, or
        SUPPLE when none exist. When profiles have not been computed
        yet but readings exist, the dominant regime is derived from the
        average capacity so the stats reflect real state rather than
        the default SUPPLE.
        """
        with self._lock:
            agent_ids: set = set()
            total_readings = 0
            capacity_sum = 0.0
            for agent_id, readings in self._readings.items():
                agent_ids.add(agent_id)
                total_readings += len(readings)
                for reading in readings:
                    capacity_sum += reading.capacity_score

            total_events = 0
            for agent_id, events in self._events.items():
                agent_ids.add(agent_id)
                total_events += len(events)

            total_snapshots = 0
            for agent_id, snapshots in self._snapshots.items():
                agent_ids.add(agent_id)
                total_snapshots += len(snapshots)

            total_recoveries = 0
            for agent_id, recoveries in self._recoveries.items():
                agent_ids.add(agent_id)
                total_recoveries += len(recoveries)

            for plan in self._plans:
                agent_ids.add(plan.agent_id)

            avg_capacity = (
                round(capacity_sum / total_readings, 4)
                if total_readings
                else 0.0
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average capacity so the stats
                # reflect real state rather than the default SUPPLE.
                dominant_regime = _determine_regime(avg_capacity)
            else:
                dominant_regime = ResilienceRegime.SUPPLE

            return ResilienceStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_events=total_events,
                total_snapshots=total_snapshots,
                total_recoveries=total_recoveries,
                avg_capacity=avg_capacity,
                dominant_regime=dominant_regime,
            )

    # ── Internal profile computation (caller must hold the lock) ────

    def _compute_profile_locked(self, agent_id: str) -> ResilienceProfile:
        """Aggregate an agent's readings, events, and recoveries into a profile.

        See ``ResilienceProfile`` for field semantics. ``avg_capacity``
        is the mean capacity across all the agent's readings, or 0.0
        if none. ``dominant_type`` is the most frequent ``CapacityType``
        among the readings, or EMOTIONAL if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_capacity``.
        ``total_readings``, ``total_events``, and ``total_recoveries``
        count the records held for the agent. Caller holds the lock.
        """
        agent_readings = self._agent_readings_locked(agent_id)
        agent_events = self._agent_events_locked(agent_id)
        agent_recoveries = self._agent_recoveries_locked(agent_id)

        total_readings = len(agent_readings)
        if agent_readings:
            avg_capacity = sum(
                r.capacity_score for r in agent_readings
            ) / len(agent_readings)
        else:
            avg_capacity = 0.0

        dominant_type = self._mode_type_locked(agent_readings)
        if dominant_type is None:
            dominant_type = CapacityType.EMOTIONAL

        regime = _determine_regime(avg_capacity)

        return ResilienceProfile(
            agent_id=str(agent_id),
            avg_capacity=round(avg_capacity, 4),
            dominant_type=dominant_type,
            regime=regime,
            total_readings=total_readings,
            total_events=len(agent_events),
            total_recoveries=len(agent_recoveries),
            last_updated=_now(),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveResilience] = None
_engine_lock = threading.Lock()


def get_resilience_engine() -> AgentCognitiveResilience:
    """Get or create the singleton ``AgentCognitiveResilience`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveResilience()
    return _engine


def reset_resilience_engine() -> None:
    """Reset the singleton ``AgentCognitiveResilience`` instance.

    Drops the reference so the next ``get_resilience_engine`` call
    creates a fresh instance. Useful for tests that need a clean
    engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
