from __future__ import annotations

"""Agent Cognitive Beacon Engine — modeling signal emission and cognitive visibility

How an agent emits, focuses, and broadcasts cognitive signals across the field.
A beaming agent makes its intent visible far and wide; a dark agent's signals never
leave the source. Distinct from magnetism, polarization, coherence, tension, and
affinity.
Core capabilities: axis tracking, signal sources, broadcast strategies, lumen stages.

Architecture:
  AgentCognitiveBeacon (singleton)
  ├── BeaconReading      (one observation of beacon strength on one axis)
  ├── BroadcastRecord    (one broadcast event that changed beacon strength)
  ├── BeaconSnapshot     (aggregate beacon state for one agent)
  ├── BeaconPlan         (a plan to shape the signal with a strategy)
  ├── RangeShift         (one stage transition in the lumen lifecycle)
  ├── BeaconProfile      (per-agent aggregate beacon tendencies)
  └── BeaconStats        (engine-wide aggregate statistics)
"""

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
    """Generate a short unique identifier for a reading/broadcast/etc.

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
    engine with a ``NaN`` or ``None`` beacon strength. A low-side default is
    safer than a mid-range one for beacon-like quantities where a
    spurious high reading would inflate the perceived beacon strength and
    push the agent's regime toward UBIQUITOUS.
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
    """Clamp a non-negative quantity (interval, magnitude) to [0, ∞).

    Interval and magnitude values must be non-negative; negative values
    are coerced to 0 rather than rejected so a misconfigured caller
    cannot crash the engine. The upper bound is left open because
    real range intervals and broadcast magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    amplification may apply a large effective broadcast.
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
    against member values (e.g. ``"signal"``) and then against
    member names (e.g. ``"SIGNAL"``), so callers may pass either
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


def _determine_regime(avg_beacon: float) -> "BeaconRegime":
    """Classify a beacon regime from the average beacon score.

    The average beacon strength is clamped to [0, 1] where higher means a
    more visible, broadly emitting posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is INVISIBLE
    (no signal emitted, undetectable); below 0.35 it is FAINT (weak
    signal, barely perceptible); below 0.55 it is DETECTABLE (signal
    present, can be picked up); below 0.75 it is VISIBLE (clear signal,
    easily seen); below 0.9 it is PROMINENT (strong signal, stands
    out); otherwise it is UBIQUITOUS (signal everywhere, inescapable).
    """
    avg = _clamp(avg_beacon, 0.0, 1.0)
    if avg < 0.15:
        return BeaconRegime.INVISIBLE
    if avg < 0.35:
        return BeaconRegime.FAINT
    if avg < 0.55:
        return BeaconRegime.DETECTABLE
    if avg < 0.75:
        return BeaconRegime.VISIBLE
    if avg < 0.9:
        return BeaconRegime.PROMINENT
    return BeaconRegime.UBIQUITOUS


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class BeaconAxis(str, Enum):
    """The axis along which a beacon reading is taken.

    Each axis names a different dimension of the agent's cognitive
    signal whose strength can be measured. SIGNAL is the core signal
    strength. RANGE is how far the signal reaches. LUMEN is how
    bright the signal is. PULSE is the rhythm of emission. BEAM is
    the focus direction of the emission. HORIZON is the visible
    scope the agent illuminates.
    """
    SIGNAL = "signal"      # core signal strength
    RANGE = "range"        # how far the signal reaches
    LUMEN = "lumen"        # how bright the signal is
    PULSE = "pulse"        # rhythm of emission
    BEAM = "beam"          # focus direction
    HORIZON = "horizon"    # visible scope


class BeaconRegime(str, Enum):
    """The regime an agent's beacon occupies, classified by beacon strength.

    Ranges from INVISIBLE (no signal emitted, undetectable)
    through FAINT (weak signal, barely perceptible), DETECTABLE
    (signal present, can be picked up), VISIBLE (clear signal,
    easily seen), and PROMINENT (strong signal, stands out) to
    UBIQUITOUS (signal everywhere, inescapable). The regime is
    derived from the average beacon strength across the agent's
    readings via ``_determine_regime``.
    """
    INVISIBLE = "invisible"    # no signal emitted
    FAINT = "faint"            # weak signal, barely perceptible
    DETECTABLE = "detectable"  # signal present, can be picked up
    VISIBLE = "visible"        # clear signal, easily seen
    PROMINENT = "prominent"    # strong signal, stands out
    UBIQUITOUS = "ubiquitous"  # signal everywhere, inescapable


class BeaconSource(str, Enum):
    """A source that supplies the emitted signal.

    Each source names a different origin of the signal the agent
    emits. INTENT emits from deliberate intent. URGENCY emits from
    time pressure. SALIENCE emits from what stands out. NOVELTY
    emits from what is new. CONTEXT emits from situational context.
    DEMAND emits from external demand. A beacon reading records
    which source supplies the signal on the measured axis, and a
    broadcast record records which source drove a change.
    """
    INTENT = "intent"      # signal from deliberate intent
    URGENCY = "urgency"    # signal from time pressure
    SALIENCE = "salience"  # signal from what stands out
    NOVELTY = "novelty"    # signal from what is new
    CONTEXT = "context"    # signal from situational context
    DEMAND = "demand"      # signal from external demand


class BeaconStrategy(str, Enum):
    """Strategy for shaping the signal deliberately.

    AMPLIFY strengthens the signal. FOCUS narrows the beam to a
    target. BROADCAST emits broadly in all directions. DIM reduces
    the signal strength. TARGET directs the signal at a specific
    receiver. SCAN sweeps across directions to probe. Each
    strategy is suited to a different signal condition, from
    counteracting a dark signal to releasing a prominent one.
    """
    AMPLIFY = "amplify"      # strengthen the signal
    FOCUS = "focus"          # narrow the beam to a target
    BROADCAST = "broadcast"  # emit broadly in all directions
    DIM = "dim"              # reduce the signal strength
    TARGET = "target"        # direct the signal at a receiver
    SCAN = "scan"            # sweep across directions to probe


class BeaconStage(str, Enum):
    """The lifecycle stage of an agent's signal-emission process.

    DARK is the state of no emission. IGNITING is the phase of
    beginning to emit. GLOWING is the state in which the signal
    emits steadily. BEAMING is the state of focused strong
    emission. RADIATING is the state of emitting in all directions.
    OMNISCIENT is the final state at which the signal is everywhere
    and the agent is all-knowing. The engine records transitions
    between stages as RangeShift entries.
    """
    DARK = "dark"            # no emission
    IGNITING = "igniting"    # beginning to emit
    GLOWING = "glowing"      # emitting steadily
    BEAMING = "beaming"      # focused strong emission
    RADIATING = "radiating"  # emitting in all directions
    OMNISCIENT = "omniscient"  # signal everywhere, all-knowing


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BeaconReading:
    """One observation of beacon strength on a particular axis.

    ``axis`` is the ``BeaconAxis`` the reading is taken on.
    ``beacon_score`` in [0, 1] measures how visible the agent's signal is
    on that axis — 0 means fully dark, 1 means fully ubiquitous.
    ``source`` is the ``BeaconSource`` supplying the signal.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: BeaconAxis
    beacon_score: float    # 0..1, higher = more visible
    source: BeaconSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(BeaconAxis, self.axis),
            "beacon_score": self.beacon_score,
            "source": _enum_value(BeaconSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BroadcastRecord:
    """One broadcast event that changed the beacon strength on an axis.

    ``axis`` is the ``BeaconAxis`` on which the broadcast occurred.
    ``source`` is the ``BeaconSource`` that drove the change.
    ``before_score`` in [0, 1] is the beacon strength before the event;
    ``after_score`` in [0, 1] is the beacon strength after.
    ``broadcast_magnitude`` in [0, ∞) measures how strong the
    broadcast was. ``notes`` is an optional free-form annotation.
    """
    broadcast_id: str
    agent_id: str
    axis: BeaconAxis
    source: BeaconSource
    before_score: float            # 0..1, beacon strength before broadcast
    after_score: float             # 0..1, beacon strength after broadcast
    broadcast_magnitude: float    # 0..inf, strength of broadcast
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this broadcast record to a plain dict, expanding enums via ``.value``."""
        return {
            "broadcast_id": self.broadcast_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(BeaconAxis, self.axis),
            "source": _enum_value(BeaconSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "broadcast_magnitude": self.broadcast_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BeaconSnapshot:
    """Aggregate beacon state for one agent at one moment.

    ``avg_beacon`` in [0, 1] is the mean beacon score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``BeaconAxis`` among those readings, or
    SIGNAL if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_beacon``. ``broadcast_count``
    is the number of broadcast events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_beacon: float
    dominant_axis: BeaconAxis
    regime: BeaconRegime
    broadcast_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Both ``dominant_regime`` and ``regime`` keys are emitted so
        callers may consume either name — ``dominant_regime`` for
        consistency with profile/stats outputs, ``regime`` for the
        canonical snapshot field name.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_beacon": self.avg_beacon,
            "dominant_axis": _enum_value(BeaconAxis, self.dominant_axis),
            "dominant_regime": _enum_value(BeaconRegime, self.regime),
            "regime": _enum_value(BeaconRegime, self.regime),
            "broadcast_count": self.broadcast_count,
            "timestamp": self.timestamp,
        }


@dataclass
class BeaconPlan:
    """A plan to shape the signal with a strategy.

    ``strategy`` is the ``BeaconStrategy`` chosen.
    ``target_beacon`` in [0, 1] is the beacon strength the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's signal condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current beacon strength — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: BeaconStrategy
    target_beacon: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(BeaconStrategy, self.strategy),
            "target_beacon": self.target_beacon,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class RangeShift:
    """One record of a stage transition in the lumen lifecycle.

    ``from_stage`` is the ``BeaconStage`` the agent was in before
    the transition. ``to_stage`` is the ``BeaconStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow ignite",
    "sudden beaming", "deliberate amplification").
    """
    shift_id: str
    agent_id: str
    from_stage: BeaconStage
    to_stage: BeaconStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this range shift record to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(BeaconStage, self.from_stage),
            "to_stage": _enum_value(BeaconStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class BeaconProfile:
    """Per-agent aggregate beacon tendencies.

    ``avg_beacon`` in [0, 1] is the mean beacon score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``BeaconAxis`` among the agent's readings, or
    SIGNAL if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_beacon``. ``total_readings``,
    ``total_broadcasts``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_beacon: float = 0.0
    dominant_axis: BeaconAxis = BeaconAxis.SIGNAL
    dominant_regime: BeaconRegime = BeaconRegime.DETECTABLE
    total_readings: int = 0
    total_broadcasts: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_beacon": self.avg_beacon,
            "dominant_axis": _enum_value(BeaconAxis, self.dominant_axis),
            "dominant_regime": _enum_value(BeaconRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_broadcasts": self.total_broadcasts,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class BeaconStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_beacon`` is the mean beacon score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or DETECTABLE when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_broadcasts: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_beacon: float = 0.0
    dominant_regime: BeaconRegime = BeaconRegime.DETECTABLE

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_broadcasts": self.total_broadcasts,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_beacon": self.avg_beacon,
            "dominant_regime": _enum_value(BeaconRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveBeacon:
    """Thread-safe engine that models an agent's cognitive beacon.

    The engine holds six stores: ``_readings`` (BeaconReading lists
    keyed by agent_id), ``_broadcasts`` (BroadcastRecord lists keyed
    by agent_id), ``_snapshots`` (BeaconSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of BeaconPlan),
    ``_shifts`` (RangeShift lists keyed by agent_id), and
    ``_profiles`` (BeaconProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The beacon model is deliberately heuristic: beacon scores
    and intensities are caller-supplied observations; beacon
    regimes are banded from the average beacon strength; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how beacon strength is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure beacon strength itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, broadcasts, snapshots, or shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose beacon scores feed into
    # a snapshot's average beacon strength. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current beacon posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty beacon engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[BeaconReading]] = {}
        self._broadcasts: Dict[str, List[BroadcastRecord]] = {}
        self._snapshots: Dict[str, List[BeaconSnapshot]] = {}
        self._plans: List[BeaconPlan] = []
        self._shifts: Dict[str, List[RangeShift]] = {}
        self._profiles: Dict[str, BeaconProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_beacon_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._broadcasts.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[BeaconReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_broadcasts_locked(
        self, agent_id: str
    ) -> List[BroadcastRecord]:
        """Return one agent's broadcast records in insertion order. Caller holds the lock."""
        return list(self._broadcasts.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[BeaconSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[BeaconPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[RangeShift]:
        """Return one agent's range shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[BeaconReading]
    ) -> BeaconAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns SIGNAL if the list is
        empty, since SIGNAL is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return BeaconAxis.SIGNAL
        counts: Counter = Counter()
        first_seen_order: Dict[BeaconAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: BeaconAxis = readings[0].axis
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
        self, profiles: List[BeaconProfile]
    ) -> BeaconRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns DETECTABLE if the list is empty, since
        DETECTABLE is the default regime — the band that
        represents a normally functioning cognitive beacon that
        emits a signal that can be picked up without being prominent,
        neither invisible nor ubiquitous. Caller holds the lock.
        """
        if not profiles:
            return BeaconRegime.DETECTABLE
        counts: Dict[BeaconRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> BeaconProfile:
        """Aggregate an agent's readings, broadcasts, and shifts into a profile.

        See ``BeaconProfile`` for field semantics. ``avg_beacon``
        is the mean beacon score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``BeaconAxis`` among the agent's readings, or SIGNAL
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_beacon``.
        ``total_readings``, ``total_broadcasts``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        broadcasts = self._agent_broadcasts_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_beacon = sum(
                r.beacon_score for r in readings
            ) / len(readings)
        else:
            avg_beacon = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_beacon)

        return BeaconProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_beacon=round(avg_beacon, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_broadcasts=len(broadcasts),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Beacon Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        beacon_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> BeaconReading:
        """Record a beacon reading for an agent and return it.

        ``axis`` may be passed as a ``BeaconAxis`` member or its
        string name/value. ``beacon_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``BeaconSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = BeaconReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(BeaconAxis, axis),
                beacon_score=_clamp(beacon_score, 0.0, 1.0),
                source=_resolve_enum(BeaconSource, source),
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
    ) -> List[BeaconReading]:
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

    def get_reading(self, reading_id: str) -> BeaconReading:
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

    # ── Broadcast Records ────────────────────────────────────────

    def record_broadcast(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        broadcast_magnitude: float,
        notes: Optional[str] = None,
    ) -> BroadcastRecord:
        """Record a broadcast event for an agent and return it.

        ``axis`` may be passed as a ``BeaconAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``BeaconSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``broadcast_magnitude`` is clamped to [0, ∞). The broadcast
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = BroadcastRecord(
                broadcast_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(BeaconAxis, axis),
                source=_resolve_enum(BeaconSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                broadcast_magnitude=_clamp_positive_ms(
                    broadcast_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._broadcasts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_broadcasts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BroadcastRecord]:
        """Return broadcast records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all broadcasts are considered;
        otherwise only broadcasts for that agent are returned. The
        most recently recorded ``limit`` broadcasts are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                broadcasts = self._agent_broadcasts_locked(agent_id)
            else:
                broadcasts = []
                for agent_broadcasts in self._broadcasts.values():
                    broadcasts.extend(agent_broadcasts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return broadcasts[-n:] if n else []

    def get_broadcast(self, broadcast_id: str) -> BroadcastRecord:
        """Retrieve a broadcast record by id.

        Raises ``ValueError`` if no broadcast exists with that id.
        """
        with self._lock:
            for agent_broadcasts in self._broadcasts.values():
                for broadcast in agent_broadcasts:
                    if broadcast.broadcast_id == broadcast_id:
                        return broadcast
        raise ValueError(f"broadcast {broadcast_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> BeaconSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_beacon`` is the mean beacon score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``BeaconAxis`` among
        those readings, or SIGNAL if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_beacon``.
        ``broadcast_count`` is the number of broadcast events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_beacon = sum(
                    r.beacon_score for r in recent
                ) / len(recent)
            else:
                avg_beacon = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_beacon)
            broadcast_count = len(
                self._agent_broadcasts_locked(agent_id)
            )

            snapshot = BeaconSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_beacon=round(avg_beacon, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                broadcast_count=broadcast_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BeaconSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> BeaconSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Beacon Plans ────────────────────────────────────────────

    def plan_broadcast(
        self,
        agent_id: str,
        strategy: Any,
        target_beacon: float,
        rationale: str,
    ) -> BeaconPlan:
        """Record a beacon plan for an agent and return it.

        ``strategy`` may be passed as a ``BeaconStrategy`` member
        or its string name/value. ``target_beacon`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured beacon strength.
        """
        with self._lock:
            plan = BeaconPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(BeaconStrategy, strategy),
                target_beacon=_clamp(target_beacon, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BeaconPlan]:
        """Return beacon plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered;
        otherwise only plans for that agent are returned. The most
        recently recorded ``limit`` plans are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                plans = self._agent_plans_locked(agent_id)
            else:
                plans = list(self._plans)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> BeaconPlan:
        """Retrieve a beacon plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Range Shift Records ────────────────────────────────────────

    def record_range_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> RangeShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``BeaconStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        ignite", "sudden beaming", "deliberate amplification"). The
        range shift record is stored and returned; the agent's cached
        profile is invalidated.

        Range shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = RangeShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(BeaconStage, from_stage),
                to_stage=_resolve_enum(BeaconStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_range_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RangeShift]:
        """Return range shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all shifts are considered;
        otherwise only shifts for that agent are returned. The
        most recently recorded ``limit`` range shift records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                shifts = self._agent_shifts_locked(agent_id)
            else:
                shifts = []
                for agent_shifts in self._shifts.values():
                    shifts.extend(agent_shifts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return shifts[-n:] if n else []

    def get_range_shift(self, shift_id: str) -> RangeShift:
        """Retrieve a range shift record by id.

        Raises ``ValueError`` if no range shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"range shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> BeaconProfile:
        """Return the agent's beacon profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, broadcasts, snapshots, or
        shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``BeaconProfile``
        and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(
        self, agent_id: str, **kwargs: Any
    ) -> BeaconProfile:
        """Refresh and optionally override fields of an agent's beacon profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``BeaconProfile`` field names) are applied. Accepted
        overrides: ``avg_beacon`` (float), ``dominant_axis``
        (``BeaconAxis``), ``dominant_regime``
        (``BeaconRegime``), ``total_readings``,
        ``total_broadcasts``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_beacon":
                    try:
                        profile.avg_beacon = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            BeaconAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            BeaconRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_broadcasts",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[BeaconProfile]:
        """Return all stored beacon profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> BeaconStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, broadcasts, snapshots, and shifts.
        Scalar totals are the counts of each record type.
        ``avg_beacon`` is the mean beacon score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        DETECTABLE when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        beacon strength via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._broadcasts.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            beacon_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    beacon_sum += reading.beacon_score
            avg_beacon = (
                round(beacon_sum / total_readings, 4) if total_readings else 0.0
            )

            total_broadcasts = sum(
                len(agent_broadcasts)
                for agent_broadcasts in self._broadcasts.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_shifts = sum(
                len(agent_shifts)
                for agent_shifts in self._shifts.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average beacon strength so the stats
                # reflect real state rather than the default
                # DETECTABLE.
                dominant_regime = _determine_regime(avg_beacon)
            else:
                dominant_regime = BeaconRegime.DETECTABLE

            return BeaconStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_broadcasts=total_broadcasts,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_beacon=avg_beacon,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveBeacon] = None
_engine_lock = threading.Lock()


def get_beacon_engine() -> AgentCognitiveBeacon:
    """Get or create the singleton ``AgentCognitiveBeacon`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveBeacon()
    return _engine


def reset_beacon_engine() -> None:
    """Reset the singleton ``AgentCognitiveBeacon`` instance.

    Drops the reference to the current engine so the next
    ``get_beacon_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
