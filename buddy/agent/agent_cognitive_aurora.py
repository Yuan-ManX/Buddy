from __future__ import annotations

"""Agent Cognitive Aurora Engine — modeling luminous flowing thought patterns

How thoughts ignite, stream, glow, and radiate across the cognitive sky like the
aurora borealis. A radiant agent's thoughts flow in luminous curtains; a dormant
agent's sky stays dark. Distinct from magnetism, coherence, tension, equilibrium,
and affinity.
Core capabilities: axis tracking, source tracing, flow strategies, stage lifecycle.

Architecture:
  AgentCognitiveAurora (singleton)
  ├── AuroraReading      (one observation of aurora on one axis)
  ├── StreamRecord       (one stream event that changed aurora)
  ├── AuroraSnapshot     (aggregate aurora state for one agent)
  ├── AuroraPlan         (a plan to shape the flow with a strategy)
  ├── CurtainShift       (one stage transition in the curtain lifecycle)
  ├── AuroraProfile      (per-agent aggregate aurora tendencies)
  └── AuroraStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/stream/etc.

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
    engine with a ``NaN`` or ``None`` aurora. A low-side default is
    safer than a mid-range one for aurora-like quantities where a
    spurious high reading would inflate the perceived aurora and
    push the agent's regime toward CORONAL.
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
    real curtain intervals and stream magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    amplification may apply a large effective stream.
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
    against member values (e.g. ``"solar_wind"``) and then against
    member names (e.g. ``"SOLAR_WIND"``), so callers may pass either
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


def _determine_regime(avg_aurora: float) -> "AuroraRegime":
    """Classify an aurora regime from the average aurora score.

    The average aurora is clamped to [0, 1] where higher means a
    brighter, more flowing posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is DORMANT
    (dark sky, no emission); below 0.35 it is FLICKERING (intermittent
    glow, only lights up under external excitation); below 0.55 it is
    GLOWING (steady soft light, retains emission); below 0.75 it is
    FLOWING (moving curtains, most of the sky alive); below 0.9 it is
    RADIANT (bright display, little room for more); otherwise it is
    CORONAL (full-sky corona, perfectly locked emission).
    """
    avg = _clamp(avg_aurora, 0.0, 1.0)
    if avg < 0.15:
        return AuroraRegime.DORMANT
    if avg < 0.35:
        return AuroraRegime.FLICKERING
    if avg < 0.55:
        return AuroraRegime.GLOWING
    if avg < 0.75:
        return AuroraRegime.FLOWING
    if avg < 0.9:
        return AuroraRegime.RADIANT
    return AuroraRegime.CORONAL


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class AuroraAxis(str, Enum):
    """The axis along which an aurora reading is taken.

    Each axis names a different dimension of the agent's cognitive
    sky whose aurora can be measured. STREAM is a flowing ribbon of
    thought. CURTAIN is a hanging sheet of thought. GLOW is a diffuse
    luminous patch. FLUX is the changing intensity. BOREALIS is the
    overall northern display. ZENITH is the overhead peak of
    brightness.
    """
    STREAM = "stream"        # flowing ribbon of thought
    CURTAIN = "curtain"      # hanging sheet of thought
    GLOW = "glow"            # diffuse luminous patch
    FLUX = "flux"            # changing intensity
    BOREALIS = "borealis"    # overall northern display
    ZENITH = "zenith"        # overhead peak of brightness


class AuroraRegime(str, Enum):
    """The regime an agent's aurora occupies, classified by aurora.

    Ranges from DORMANT (dark sky, no emission) through FLICKERING
    (intermittent glow, only lights up under external excitation),
    GLOWING (steady soft light, retains emission), FLOWING (moving
    curtains, most of the sky alive), and RADIANT (bright display,
    little room for more) to CORONAL (full-sky corona, perfectly
    locked emission). The regime is derived from the average aurora
    across the agent's readings via ``_determine_regime``.
    """
    DORMANT = "dormant"        # dark sky, no emission
    FLICKERING = "flickering"  # intermittent glow
    GLOWING = "glowing"        # steady soft light, retains emission
    FLOWING = "flowing"        # moving curtains, most of the sky alive
    RADIANT = "radiant"        # bright display
    CORONAL = "coronal"        # full-sky corona, perfectly locked emission


class AuroraSource(str, Enum):
    """A source that supplies the luminous or flowing force.

    Each source names a different origin of the light between
    thoughts. PARTICLE is the charged particle influx. FIELD is the
    magnetic field line. SOLAR_WIND is the solar wind stream.
    MAGNETIC is the magnetic disturbance. ATMOSPHERE is the
    atmospheric interaction. IONOSPHERE is the ionospheric
    excitation. An aurora reading records which source supplies the
    light on the measured axis, and a stream record records which
    source drove a change.
    """
    PARTICLE = "particle"        # charged particle influx
    FIELD = "field"              # magnetic field line
    SOLAR_WIND = "solar_wind"    # solar wind stream
    MAGNETIC = "magnetic"        # magnetic disturbance
    ATMOSPHERE = "atmosphere"    # atmospheric interaction
    IONOSPHERE = "ionosphere"    # ionospheric excitation


class AuroraStrategy(str, Enum):
    """Strategy for shaping the flow deliberately.

    IGNITE starts a glow. CHANNEL directs the flow. AMPLIFY
    strengthens the brightness. DISPERSE spreads the light.
    STABILIZE holds the pattern. DISSIPATE lets it fade. Each
    strategy is suited to a different sky condition, from
    counteracting a dark sky to releasing a saturated corona.
    """
    IGNITE = "ignite"        # start a glow
    CHANNEL = "channel"      # direct the flow
    AMPLIFY = "amplify"      # strengthen the brightness
    DISPERSE = "disperse"    # spread the light
    STABILIZE = "stabilize"  # hold the pattern
    DISSIPATE = "dissipate"  # let it fade


class AuroraStage(str, Enum):
    """The lifecycle stage of an agent's flow-formation process.

    DARK is the state of no emission. STIRRING is the phase of
    beginning to glow. FLICKERING is the state of intermittent
    light. FLOWING is the state of moving curtains. RADIATING is
    the state of bright emission. CORONAL is the final state at
    which the sky is fully locked and unresponsive to new input.
    The engine records transitions between stages as CurtainShift
    entries.
    """
    DARK = "dark"              # no emission
    STIRRING = "stirring"      # beginning to glow
    FLICKERING = "flickering"  # intermittent light
    FLOWING = "flowing"        # moving curtains
    RADIATING = "radiating"    # bright emission
    CORONAL = "coronal"        # fully locked corona


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AuroraReading:
    """One observation of aurora on a particular axis.

    ``axis`` is the ``AuroraAxis`` the reading is taken on.
    ``aurora_score`` in [0, 1] measures how luminous the agent is
    on that axis — 0 means fully dark, 1 means fully coronal.
    ``source`` is the ``AuroraSource`` supplying the light.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: AuroraAxis
    aurora_score: float    # 0..1, higher = more luminous
    source: AuroraSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(AuroraAxis, self.axis),
            "aurora_score": self.aurora_score,
            "source": _enum_value(AuroraSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class StreamRecord:
    """One stream event that changed the aurora on an axis.

    ``axis`` is the ``AuroraAxis`` on which the stream occurred.
    ``source`` is the ``AuroraSource`` that drove the change.
    ``before_score`` in [0, 1] is the aurora before the event;
    ``after_score`` in [0, 1] is the aurora after.
    ``stream_magnitude`` in [0, ∞) measures how strong the
    stream was. ``notes`` is an optional free-form annotation.
    """
    stream_id: str
    agent_id: str
    axis: AuroraAxis
    source: AuroraSource
    before_score: float            # 0..1, aurora before stream
    after_score: float             # 0..1, aurora after stream
    stream_magnitude: float        # 0..inf, strength of stream
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this stream record to a plain dict, expanding enums via ``.value``."""
        return {
            "stream_id": self.stream_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(AuroraAxis, self.axis),
            "source": _enum_value(AuroraSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "stream_magnitude": self.stream_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class AuroraSnapshot:
    """Aggregate aurora state for one agent at one moment.

    ``avg_aurora`` in [0, 1] is the mean aurora score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``AuroraAxis`` among those readings, or
    STREAM if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_aurora``. ``stream_count``
    is the number of stream events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_aurora: float
    dominant_axis: AuroraAxis
    regime: AuroraRegime
    stream_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Both ``dominant_regime`` and ``regime`` keys are emitted pointing
        to the same value so consumers may read either name.
        """
        regime_value = _enum_value(AuroraRegime, self.regime)
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_aurora": self.avg_aurora,
            "dominant_axis": _enum_value(AuroraAxis, self.dominant_axis),
            "dominant_regime": regime_value,
            "regime": regime_value,
            "stream_count": self.stream_count,
            "timestamp": self.timestamp,
        }


@dataclass
class AuroraPlan:
    """A plan to shape the flow with a strategy.

    ``strategy`` is the ``AuroraStrategy`` chosen.
    ``target_aurora`` in [0, 1] is the aurora the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's sky condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current aurora — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: AuroraStrategy
    target_aurora: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(AuroraStrategy, self.strategy),
            "target_aurora": self.target_aurora,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class CurtainShift:
    """One record of a stage transition in the curtain lifecycle.

    ``from_stage`` is the ``AuroraStage`` the agent was in before
    the transition. ``to_stage`` is the ``AuroraStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow stir",
    "sudden radiation", "deliberate amplification").
    """
    shift_id: str
    agent_id: str
    from_stage: AuroraStage
    to_stage: AuroraStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this curtain shift record to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(AuroraStage, self.from_stage),
            "to_stage": _enum_value(AuroraStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class AuroraProfile:
    """Per-agent aggregate aurora tendencies.

    ``avg_aurora`` in [0, 1] is the mean aurora score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``AuroraAxis`` among the agent's readings, or
    STREAM if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_aurora``. ``total_readings``,
    ``total_streams``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_aurora: float = 0.0
    dominant_axis: AuroraAxis = AuroraAxis.STREAM
    dominant_regime: AuroraRegime = AuroraRegime.GLOWING
    total_readings: int = 0
    total_streams: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_aurora": self.avg_aurora,
            "dominant_axis": _enum_value(AuroraAxis, self.dominant_axis),
            "dominant_regime": _enum_value(AuroraRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_streams": self.total_streams,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class AuroraStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_aurora`` is the mean aurora score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or GLOWING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_streams: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_aurora: float = 0.0
    dominant_regime: AuroraRegime = AuroraRegime.GLOWING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_streams": self.total_streams,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_aurora": self.avg_aurora,
            "dominant_regime": _enum_value(AuroraRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveAurora:
    """Thread-safe engine that models an agent's cognitive aurora.

    The engine holds six stores: ``_readings`` (AuroraReading lists
    keyed by agent_id), ``_streams`` (StreamRecord lists keyed by
    agent_id), ``_snapshots`` (AuroraSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of AuroraPlan),
    ``_curtain_shifts`` (CurtainShift lists keyed by agent_id), and
    ``_profiles`` (AuroraProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The aurora model is deliberately heuristic: aurora scores
    and intensities are caller-supplied observations; aurora
    regimes are banded from the average aurora; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how aurora is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure aurora itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, streams, snapshots, or curtain shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose aurora scores feed into
    # a snapshot's average aurora. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current aurora posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty aurora engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[AuroraReading]] = {}
        self._streams: Dict[str, List[StreamRecord]] = {}
        self._snapshots: Dict[str, List[AuroraSnapshot]] = {}
        self._plans: List[AuroraPlan] = []
        self._curtain_shifts: Dict[str, List[CurtainShift]] = {}
        self._profiles: Dict[str, AuroraProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_aurora_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._streams.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._curtain_shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[AuroraReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_streams_locked(
        self, agent_id: str
    ) -> List[StreamRecord]:
        """Return one agent's stream records in insertion order. Caller holds the lock."""
        return list(self._streams.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[AuroraSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[AuroraPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_curtain_shifts_locked(
        self, agent_id: str
    ) -> List[CurtainShift]:
        """Return one agent's curtain shift records in insertion order. Caller holds the lock."""
        return list(self._curtain_shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[AuroraReading]
    ) -> AuroraAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns STREAM if the list is
        empty, since STREAM is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return AuroraAxis.STREAM
        counts: Counter = Counter()
        first_seen_order: Dict[AuroraAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: AuroraAxis = readings[0].axis
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
        self, profiles: List[AuroraProfile]
    ) -> AuroraRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns GLOWING if the list is empty, since
        GLOWING is the default regime — the band that
        represents a normally functioning cognitive sky that
        retains emission without being saturated, neither
        dormant nor coronal. Caller holds the lock.
        """
        if not profiles:
            return AuroraRegime.GLOWING
        counts: Dict[AuroraRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> AuroraProfile:
        """Aggregate an agent's readings, streams, and shifts into a profile.

        See ``AuroraProfile`` for field semantics. ``avg_aurora``
        is the mean aurora score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``AuroraAxis`` among the agent's readings, or STREAM
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_aurora``.
        ``total_readings``, ``total_streams``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        streams = self._agent_streams_locked(agent_id)
        shifts = self._agent_curtain_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_aurora = sum(
                r.aurora_score for r in readings
            ) / len(readings)
        else:
            avg_aurora = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_aurora)

        return AuroraProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_aurora=round(avg_aurora, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_streams=len(streams),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Aurora Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        aurora_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> AuroraReading:
        """Record an aurora reading for an agent and return it.

        ``axis`` may be passed as a ``AuroraAxis`` member or its
        string name/value. ``aurora_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``AuroraSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = AuroraReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(AuroraAxis, axis),
                aurora_score=_clamp(aurora_score, 0.0, 1.0),
                source=_resolve_enum(AuroraSource, source),
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
    ) -> List[AuroraReading]:
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

    def get_reading(self, reading_id: str) -> AuroraReading:
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

    # ── Stream Records ────────────────────────────────────────

    def record_stream(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        stream_magnitude: float,
        notes: Optional[str] = None,
    ) -> StreamRecord:
        """Record a stream event for an agent and return it.

        ``axis`` may be passed as a ``AuroraAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``AuroraSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``stream_magnitude`` is clamped to [0, ∞). The stream
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = StreamRecord(
                stream_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(AuroraAxis, axis),
                source=_resolve_enum(AuroraSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                stream_magnitude=_clamp_positive_ms(
                    stream_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._streams.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_streams(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StreamRecord]:
        """Return stream records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all streams are considered;
        otherwise only streams for that agent are returned. The
        most recently recorded ``limit`` streams are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                streams = self._agent_streams_locked(agent_id)
            else:
                streams = []
                for agent_streams in self._streams.values():
                    streams.extend(agent_streams)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return streams[-n:] if n else []

    def get_stream(self, stream_id: str) -> StreamRecord:
        """Retrieve a stream record by id.

        Raises ``ValueError`` if no stream exists with that id.
        """
        with self._lock:
            for agent_streams in self._streams.values():
                for stream in agent_streams:
                    if stream.stream_id == stream_id:
                        return stream
        raise ValueError(f"stream {stream_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> AuroraSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_aurora`` is the mean aurora score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``AuroraAxis`` among
        those readings, or STREAM if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_aurora``.
        ``stream_count`` is the number of stream events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_aurora = sum(
                    r.aurora_score for r in recent
                ) / len(recent)
            else:
                avg_aurora = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_aurora)
            stream_count = len(
                self._agent_streams_locked(agent_id)
            )

            snapshot = AuroraSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_aurora=round(avg_aurora, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                stream_count=stream_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuroraSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> AuroraSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Aurora Plans ────────────────────────────────────────────

    def plan_stream(
        self,
        agent_id: str,
        strategy: Any,
        target_aurora: float,
        rationale: str,
    ) -> AuroraPlan:
        """Record an aurora plan for an agent and return it.

        ``strategy`` may be passed as a ``AuroraStrategy`` member
        or its string name/value. ``target_aurora`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured aurora.
        """
        with self._lock:
            plan = AuroraPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(AuroraStrategy, strategy),
                target_aurora=_clamp(target_aurora, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuroraPlan]:
        """Return aurora plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> AuroraPlan:
        """Retrieve an aurora plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Curtain Shift Records ────────────────────────────────────

    def record_curtain_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> CurtainShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``AuroraStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        stir", "sudden radiation", "deliberate amplification"). The
        curtain shift record is stored and returned; the agent's cached
        profile is invalidated.

        Curtain shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = CurtainShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(AuroraStage, from_stage),
                to_stage=_resolve_enum(AuroraStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._curtain_shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_curtain_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CurtainShift]:
        """Return curtain shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all curtain shifts are considered;
        otherwise only curtain shifts for that agent are returned. The
        most recently recorded ``limit`` curtain shift records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                shifts = self._agent_curtain_shifts_locked(agent_id)
            else:
                shifts = []
                for agent_shifts in self._curtain_shifts.values():
                    shifts.extend(agent_shifts)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return shifts[-n:] if n else []

    def get_curtain_shift(self, shift_id: str) -> CurtainShift:
        """Retrieve a curtain shift record by id.

        Raises ``ValueError`` if no curtain shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._curtain_shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"curtain shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> AuroraProfile:
        """Return the agent's aurora profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, streams, snapshots, or
        curtain shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``AuroraProfile``
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
    ) -> AuroraProfile:
        """Refresh and optionally override fields of an agent's aurora profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``AuroraProfile`` field names) are applied. Accepted
        overrides: ``avg_aurora`` (float), ``dominant_axis``
        (``AuroraAxis``), ``dominant_regime``
        (``AuroraRegime``), ``total_readings``,
        ``total_streams``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_aurora":
                    try:
                        profile.avg_aurora = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            AuroraAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            AuroraRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_streams",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[AuroraProfile]:
        """Return all stored aurora profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> AuroraStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, streams, snapshots, and curtain shifts.
        Scalar totals are the counts of each record type.
        ``avg_aurora`` is the mean aurora score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        GLOWING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        aurora via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._streams.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._curtain_shifts.keys())

            total_readings = 0
            aurora_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    aurora_sum += reading.aurora_score
            avg_aurora = (
                round(aurora_sum / total_readings, 4) if total_readings else 0.0
            )

            total_streams = sum(
                len(agent_streams)
                for agent_streams in self._streams.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_shifts = sum(
                len(agent_shifts)
                for agent_shifts in self._curtain_shifts.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average aurora so the stats
                # reflect real state rather than the default
                # GLOWING.
                dominant_regime = _determine_regime(avg_aurora)
            else:
                dominant_regime = AuroraRegime.GLOWING

            return AuroraStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_streams=total_streams,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_aurora=avg_aurora,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveAurora] = None
_engine_lock = threading.Lock()


def get_aurora_engine() -> AgentCognitiveAurora:
    """Get or create the singleton ``AgentCognitiveAurora`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveAurora()
    return _engine


def reset_aurora_engine() -> None:
    """Reset the singleton ``AgentCognitiveAurora`` instance.

    Drops the reference to the current engine so the next
    ``get_aurora_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
