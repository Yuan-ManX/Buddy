"""Agent Cognitive Cadence Engine — the rhythm and tempo of thought

Every active mind has a cadence: the underlying beat against which reasoning
and narration are played. Borrowing from music, it tracks tempo (event rate)
and beat type (from SYLLABLE to EPOCH), complementing momentum and turbulence.

Core capabilities:
  - Tempo Regime: ARRESTED through ANDANTE and MODERATO to PRESTO
  - Beat Types: SYLLABLE, PHRASE, CLAUSE, ARGUMENT, NARRATIVE, EPOCH
  - Pulse States: SILENT, TICKING, STEADY, SURGING, STUTTERING, SYNCOPATED
  - Drift: LOCKED, DRIFTING, FRAYING, ENTRAINED, POLYRHYTHMIC, BROKEN
  - Strategies: SLOW, STEADY, QUICKEN, RESET, SYNC, DAMPEN

Architecture:
  AgentCognitiveCadence (singleton)
  ├── CadenceReading, BeatRecord, CadenceSnapshot, PulseRecord
  └── RhythmPlan, CadenceProfile, CadenceStats
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
    """Generate a short unique identifier for a reading/beat/snapshot/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` intensity. A low-side default is
    safer than a mid-range one for cadence-like quantities where a
    spurious high reading would inflate the perceived tempo.
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
    against member values (e.g. ``"andante"``) and then against member
    names (e.g. ``"ANDANTE"``), so callers may pass either form. This
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


def _determine_regime(avg_cadence: float) -> "TempoRegime":
    """Classify a tempo regime from the average cadence intensity.

    The average is clamped to [0, 1] where higher means a faster
    cognitive tempo. The checks are applied in order, so the first
    matching band wins: below 0.15 the cadence is ARRESTED (no
    activity); below 0.35 it is ADAGIO (very slow); below 0.55 it is
    ANDANTE (walking pace); below 0.75 it is MODERATO (moderate);
    below 0.9 it is ALLEGRO (fast); otherwise it is PRESTO (very
    fast). The bands mirror the musical progression from a held
    silence through a slow largo to a frenetic prestissimo.
    """
    avg = _clamp(avg_cadence, 0.0, 1.0)
    if avg < 0.15:
        return TempoRegime.ARRESTED
    if avg < 0.35:
        return TempoRegime.ADAGIO
    if avg < 0.55:
        return TempoRegime.ANDANTE
    if avg < 0.75:
        return TempoRegime.MODERATO
    if avg < 0.9:
        return TempoRegime.ALLEGRO
    return TempoRegime.PRESTO


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class BeatType(str, Enum):
    """The kind of cognitive beat observed in a reading or beat record.

    The taxonomy follows linguistic and rhetorical units, from the
    smallest unit of attention (SYLLABLE) up to the longest arc of
    change (EPOCH). PHRASE is a small group of syllables; CLAUSE is a
    self-contained logical unit; ARGUMENT is a multi-clause
    justification; NARRATIVE is an integrated story; EPOCH is a
    long-arc strategic shift. The engine tracks the distribution of
    beat types per agent to find the dominant beat type.
    """
    SYLLABLE = "syllable"        # single unit of attention
    PHRASE = "phrase"            # small group of syllables
    CLAUSE = "clause"            # self-contained logical unit
    ARGUMENT = "argument"        # multi-clause justification
    NARRATIVE = "narrative"      # integrated story
    EPOCH = "epoch"              # long-arc strategic change


class TempoRegime(str, Enum):
    """The tempo regime an agent's cognitive cadence occupies.

    Ranges from ARRESTED (no activity) through ADAGIO (very slow),
    ANDANTE (walking pace), MODERATO (moderate), and ALLEGRO (fast)
    to PRESTO (very fast). See ``_determine_regime`` for the band
    thresholds. The labels are borrowed from classical tempo markings
    to give the bands an intuitive feel.
    """
    ARRESTED = "arrested"        # no cognitive activity
    ADAGIO = "adagio"            # very slow tempo
    ANDANTE = "andante"          # walking pace tempo
    MODERATO = "moderato"        # moderate tempo
    ALLEGRO = "allegro"          # fast tempo
    PRESTO = "presto"            # very fast tempo


class PulseState(str, Enum):
    """The instantaneous state of the agent's cognitive pulse.

    SILENT means no beats are being produced. TICKING means a beat is
    being prepared but has not yet fired. STEADY means beats are
    arriving at the expected rate. SURGING means beats are arriving
    faster than expected. STUTTERING means beats are being dropped
    or doubled unevenly. SYNCOPATED means the agent is deliberately
    off-beat for a specific purpose. The engine records transitions
    between these states as PulseRecord entries.
    """
    SILENT = "silent"            # no beats being produced
    TICKING = "ticking"          # beat being prepared
    STEADY = "steady"            # beats at expected rate
    SURGING = "surging"          # beats faster than expected
    STUTTERING = "stuttering"    # beats dropped or doubled
    SYNCOPATED = "syncopated"    # deliberately off-beat


class RhythmStrategy(str, Enum):
    """Strategy for adjusting the agent's cognitive cadence.

    SLOW reduces the tempo deliberately. STEADY holds the tempo
    constant against drift. QUICKEN increases the tempo. RESET
    returns the cadence to a baseline state from any drift. SYNC
    aligns the cadence with an external rhythm. DAMPEN reduces the
    variability in the cadence without changing the average tempo.
    Each strategy suits a different drift indicator.
    """
    SLOW = "slow"                # reduce tempo deliberately
    STEADY = "steady"            # hold tempo constant
    QUICKEN = "quicken"          # increase tempo
    RESET = "reset"              # return to baseline
    SYNC = "sync"                # align with external rhythm
    DAMPEN = "dampen"            # reduce variability only


class DriftIndicator(str, Enum):
    """The relationship between actual and target cadence.

    LOCKED means the agent is producing beats at the expected tempo
    and type. DRIFTING means the agent's tempo is moving away from
    the target but has not yet lost coherence. FRAYING means the
    beat pattern is becoming irregular while the average tempo is
    still on target. ENTRAINED means the agent has synchronized with
    an external rhythm. POLYRHYTHMIC means the agent is running two
    or more beat patterns simultaneously. BROKEN means the cadence
    has lost coherence entirely.
    """
    LOCKED = "locked"            # tempo on target
    DRIFTING = "drifting"        # tempo moving away
    FRAYING = "fraying"          # pattern irregular
    ENTRAINED = "entrained"      # synced with external rhythm
    POLYRHYTHMIC = "polyrhythmic"  # multiple patterns at once
    BROKEN = "broken"            # cadence lost coherence


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CadenceReading:
    """One observation of a cognitive beat in the agent's thought stream.

    ``beat_type`` classifies the beat (SYLLABLE, PHRASE, CLAUSE,
    ARGUMENT, NARRATIVE, EPOCH). ``tempo_score`` in [0, 1] is the
    instantaneous tempo at the time of the reading — higher means
    faster. ``interval_ms`` in [0, ∞) is the time since the previous
    beat in milliseconds. ``pulse_state`` is the pulse state during
    the reading. ``intensity`` in [0, 1] is how strong the beat was,
    with higher meaning more emphatic.
    """
    reading_id: str
    agent_id: str
    beat_type: BeatType
    tempo_score: float           # 0..1, instantaneous tempo
    interval_ms: float           # 0..inf, time since previous beat
    pulse_state: PulseState
    intensity: float             # 0..1, strength of the beat
    timestamp: str
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "beat_type": _enum_value(BeatType, self.beat_type),
            "tempo_score": self.tempo_score,
            "interval_ms": self.interval_ms,
            "pulse_state": _enum_value(PulseState, self.pulse_state),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BeatRecord:
    """One detected beat in the agent's thought stream.

    ``beat_type`` classifies the beat. ``period_ms`` in [0, ∞) is the
    expected time between this beat and the next one. ``amplitude``
    in [0, 1] is how loud the beat was — a high-amplitude beat is
    one that produced a major change, a low-amplitude beat is one
    that produced a minor refinement. ``source`` is a free-form label
    for the subsystem that produced the beat (e.g. "reasoning",
    "memory", "dialogue").
    """
    beat_id: str
    agent_id: str
    beat_type: BeatType
    period_ms: float             # 0..inf, expected time to next beat
    amplitude: float             # 0..1, loudness of the beat
    source: str
    timestamp: str
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this beat record to a plain dict, expanding enums via ``.value``."""
        return {
            "beat_id": self.beat_id,
            "agent_id": self.agent_id,
            "beat_type": _enum_value(BeatType, self.beat_type),
            "period_ms": self.period_ms,
            "amplitude": self.amplitude,
            "source": self.source,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CadenceSnapshot:
    """Aggregate cadence state for one agent at one moment.

    ``avg_tempo`` in [0, 1] is the mean tempo score across the
    agent's recent readings, or 0.0 if none. ``dominant_beat`` is the
    most frequent beat type across the agent's readings, or SYLLABLE
    if none. ``tempo_regime`` is derived from ``avg_tempo`` via
    ``_determine_regime``. ``pulse_state`` is the most recent pulse
    state observed, or STEADY if none. ``beat_count`` is the number
    of beat records the agent currently has.
    """
    snapshot_id: str
    agent_id: str
    avg_tempo: float
    dominant_beat: BeatType
    tempo_regime: TempoRegime
    pulse_state: PulseState
    beat_count: int
    timestamp: str
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_tempo": self.avg_tempo,
            "dominant_beat": _enum_value(BeatType, self.dominant_beat),
            "tempo_regime": _enum_value(TempoRegime, self.tempo_regime),
            "pulse_state": _enum_value(PulseState, self.pulse_state),
            "beat_count": self.beat_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class RhythmPlan:
    """A plan to adjust the agent's cognitive cadence.

    ``strategy`` is the ``RhythmStrategy`` chosen. ``target_tempo`` in
    [0, 1] is the tempo the plan aims to reach; ``current_tempo`` in
    [0, 1] is the tempo at the time the plan was made. ``rationale``
    explains why this strategy was chosen for this drift.
    """
    plan_id: str
    agent_id: str
    strategy: RhythmStrategy
    target_tempo: float
    current_tempo: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(RhythmStrategy, self.strategy),
            "target_tempo": self.target_tempo,
            "current_tempo": self.current_tempo,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class PulseRecord:
    """One record of a pulse-state transition.

    ``from_state`` is the ``PulseState`` the agent was in before the
    transition; ``to_state`` is the ``PulseState`` it moved to.
    ``interval_ms`` in [0, ∞) is the duration the from_state held
    before the transition. ``drift_indicator`` describes the
    relationship between the actual and target cadence at the
    moment of the transition.
    """
    pulse_id: str
    agent_id: str
    from_state: PulseState
    to_state: PulseState
    interval_ms: float
    drift_indicator: DriftIndicator
    timestamp: str
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this pulse record to a plain dict, expanding enums via ``.value``."""
        return {
            "pulse_id": self.pulse_id,
            "agent_id": self.agent_id,
            "from_state": _enum_value(PulseState, self.from_state),
            "to_state": _enum_value(PulseState, self.to_state),
            "interval_ms": self.interval_ms,
            "drift_indicator": _enum_value(DriftIndicator, self.drift_indicator),
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class CadenceProfile:
    """Per-agent aggregate cadence tendencies.

    ``avg_tempo`` is the mean tempo score across the agent's readings
    (0.0 if none). ``dominant_beat`` is the most frequent beat type
    across the agent's readings, or SYLLABLE if none.
    ``tempo_regime`` is derived via ``_determine_regime``.
    ``total_readings``, ``total_beats``, and ``total_pulses`` count
    the records held for the agent.
    """
    agent_id: str
    avg_tempo: float = 0.0
    dominant_beat: BeatType = BeatType.SYLLABLE
    tempo_regime: TempoRegime = TempoRegime.ANDANTE
    total_readings: int = 0
    total_beats: int = 0
    total_pulses: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_tempo": self.avg_tempo,
            "dominant_beat": _enum_value(BeatType, self.dominant_beat),
            "tempo_regime": _enum_value(TempoRegime, self.tempo_regime),
            "total_readings": self.total_readings,
            "total_beats": self.total_beats,
            "total_pulses": self.total_pulses,
            "last_updated": self.last_updated,
        }


@dataclass
class CadenceStats:
    """Engine-wide aggregate statistics across all agents and cadences.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_tempo`` is the mean tempo score across all readings,
    or 0.0 when none exist. ``dominant_regime`` is the most frequent
    tempo regime across all snapshots, or ANDANTE when none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_beats: int = 0
    total_snapshots: int = 0
    total_pulses: int = 0
    avg_tempo: float = 0.0
    dominant_regime: TempoRegime = TempoRegime.ANDANTE

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_beats": self.total_beats,
            "total_snapshots": self.total_snapshots,
            "total_pulses": self.total_pulses,
            "avg_tempo": self.avg_tempo,
            "dominant_regime": _enum_value(TempoRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCadence:
    """Thread-safe engine that models an agent's cognitive cadence.

    The engine holds six stores: ``_readings`` (CadenceReading lists
    keyed by agent_id), ``_beats`` (BeatRecord lists keyed by
    agent_id), ``_snapshots`` (CadenceSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of RhythmPlan), ``_pulses``
    (PulseRecord lists keyed by agent_id), and ``_profiles``
    (CadenceProfile by agent_id, cached and invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that public
    methods may safely call one another without self-deadlock. The
    cadence model is deliberately heuristic: tempo scores, intervals,
    amplitudes, and intensities are caller-supplied observations;
    tempo regimes are banded from aggregate activity; dominant beat
    types are computed by mode; and pulse states are taken from the
    most recent reading. These heuristics are transparent and
    auditable rather than learned, which keeps the engine
    deterministic.

    The engine is intentionally agnostic about how cadence is
    measured and how beats are detected — callers may derive them from
    any source. The engine's job is to record, aggregate, classify,
    and profile, not to detect cadence itself. Profiles are cached
    per agent and invalidated whenever the agent's readings, beats,
    snapshots, or pulses change, so ``get_profile`` always reflects
    the current state unless an explicit override has been applied
    via ``update_profile``.
    """

    def __init__(self) -> None:
        """Initialize an empty cadence engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[CadenceReading]] = {}
        self._beats: Dict[str, List[BeatRecord]] = {}
        self._snapshots: Dict[str, List[CadenceSnapshot]] = {}
        self._plans: List[RhythmPlan] = []
        self._pulses: Dict[str, List[PulseRecord]] = {}
        self._profiles: Dict[str, CadenceProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_cadence_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._beats.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._pulses.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[CadenceReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_beats_locked(self, agent_id: str) -> List[BeatRecord]:
        """Return one agent's beat records in insertion order. Caller holds the lock."""
        return list(self._beats.get(agent_id, []))

    def _agent_pulses_locked(self, agent_id: str) -> List[PulseRecord]:
        """Return one agent's pulse records in insertion order. Caller holds the lock."""
        return list(self._pulses.get(agent_id, []))

    def _mode_beat_locked(self, readings: List[CadenceReading]) -> BeatType:
        """Return the most frequent beat type among the supplied readings.

        Ties are broken by insertion order, so the earliest beat type
        observed in a tie wins. Returns SYLLABLE if the list is empty,
        since SYLLABLE is the smallest and most neutral beat type.
        Caller holds the lock.
        """
        if not readings:
            return BeatType.SYLLABLE
        counts: Counter = Counter()
        first_seen_order: Dict[BeatType, int] = {}
        for index, reading in enumerate(readings):
            bt = reading.beat_type
            counts[bt] += 1
            if bt not in first_seen_order:
                first_seen_order[bt] = index
        # Find the beat type with the highest count; ties broken by
        # earliest insertion order.
        best_type: BeatType = readings[0].beat_type
        best_count = -1
        for bt, count in counts.items():
            if (count > best_count) or (
                count == best_count
                and first_seen_order.get(bt, 0) < first_seen_order.get(best_type, 0)
            ):
                best_type = bt
                best_count = count
        return best_type

    def _avg_tempo_locked(self, agent_id: str) -> float:
        """Return the mean tempo score across the agent's readings.

        Returns 0.0 when the agent has no readings. Caller holds the
        lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        return sum(r.tempo_score for r in readings) / len(readings)

    def _current_tempo_locked(self, agent_id: str) -> float:
        """Return the agent's most recent tempo score, or the mean if none recent.

        Prefers the tempo score of the most recent reading, falling
        back to the mean of all readings when there is no clear most
        recent one. Returns 0.0 when the agent has no readings.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        # Use the most recent reading's tempo score as the "current" tempo,
        # since that best reflects the present state. Fall back to the
        # mean only when the most recent reading's tempo is missing.
        most_recent = readings[-1]
        if most_recent.tempo_score is not None:
            return float(most_recent.tempo_score)
        return self._avg_tempo_locked(agent_id)

    def _most_recent_pulse_state_locked(self, agent_id: str) -> PulseState:
        """Return the most recent pulse state observed for the agent.

        Falls back to STEADY when the agent has no readings, since
        STEADY is the neutral pulse state. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return PulseState.STEADY
        return readings[-1].pulse_state

    def _compute_profile_locked(self, agent_id: str) -> CadenceProfile:
        """Aggregate an agent's readings, beats, and pulses into a profile.

        See ``CadenceProfile`` for field semantics. ``avg_tempo`` is
        the mean tempo score across the agent's readings (0.0 if
        none). ``dominant_beat`` is the most frequent beat type among
        the agent's readings, or SYLLABLE if none. ``tempo_regime``
        is derived via ``_determine_regime``. ``total_readings``,
        ``total_beats``, and ``total_pulses`` count the records held
        for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        beats = self._agent_beats_locked(agent_id)
        pulses = self._agent_pulses_locked(agent_id)

        avg_tempo = self._avg_tempo_locked(agent_id)
        tempo_regime = _determine_regime(avg_tempo)
        dominant_beat = self._mode_beat_locked(readings)

        return CadenceProfile(
            agent_id=agent_id,
            avg_tempo=round(avg_tempo, 4),
            dominant_beat=dominant_beat,
            tempo_regime=tempo_regime,
            total_readings=len(readings),
            total_beats=len(beats),
            total_pulses=len(pulses),
            last_updated=_now(),
        )

    # ── Cadence Readings ─────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        beat_type: Any,
        tempo_score: float,
        interval_ms: float,
        pulse_state: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> CadenceReading:
        """Record a cadence reading for an agent and return it.

        ``beat_type`` may be passed as a ``BeatType`` member or its
        string name/value. ``pulse_state`` may be passed as a
        ``PulseState`` member or its string name/value.
        ``tempo_score`` and ``intensity`` are clamped to [0, 1].
        ``interval_ms`` is clamped to [0, ∞). The reading is stored
        and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            reading = CadenceReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                beat_type=_resolve_enum(BeatType, beat_type),
                tempo_score=_clamp(tempo_score, 0.0, 1.0),
                interval_ms=_clamp_positive_ms(interval_ms),
                pulse_state=_resolve_enum(PulseState, pulse_state),
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
    ) -> List[CadenceReading]:
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

    def get_reading(self, reading_id: str) -> CadenceReading:
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

    # ── Beat Records ─────────────────────────────────────────────

    def record_beat(
        self,
        agent_id: str,
        beat_type: Any,
        period_ms: float,
        amplitude: float,
        source: str,
        notes: Optional[str] = None,
    ) -> BeatRecord:
        """Record a beat for an agent and return it.

        ``beat_type`` may be passed as a ``BeatType`` member or its
        string name/value. ``amplitude`` is clamped to [0, 1].
        ``period_ms`` is clamped to [0, ∞). ``source`` is a free-form
        string label for the subsystem that produced the beat. The
        beat is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            beat = BeatRecord(
                beat_id=_new_id(),
                agent_id=str(agent_id),
                beat_type=_resolve_enum(BeatType, beat_type),
                period_ms=_clamp_positive_ms(period_ms),
                amplitude=_clamp(amplitude, 0.0, 1.0),
                source=str(source),
                timestamp=_now(),
                notes=notes,
            )
            self._beats.setdefault(agent_id, []).append(beat)
            self._profiles.pop(agent_id, None)
            return beat

    def list_beats(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BeatRecord]:
        """Return beat records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all beats are considered;
        otherwise only beats for that agent are returned. The most
        recently recorded ``limit`` beats are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                beats = self._agent_beats_locked(agent_id)
            else:
                beats = []
                for agent_beats in self._beats.values():
                    beats.extend(agent_beats)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return beats[-n:] if n else []

    def get_beat(self, beat_id: str) -> BeatRecord:
        """Retrieve a beat record by id.

        Raises ``ValueError`` if no beat exists with that id.
        """
        with self._lock:
            for agent_beats in self._beats.values():
                for beat in agent_beats:
                    if beat.beat_id == beat_id:
                        return beat
        raise ValueError(f"beat {beat_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CadenceSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_tempo`` is the mean tempo score across the agent's
        readings, or 0.0 if none. ``dominant_beat`` is the most
        frequent beat type among the agent's readings, or SYLLABLE if
        none. ``tempo_regime`` is derived from ``avg_tempo`` via
        ``_determine_regime``. ``pulse_state`` is the most recent
        pulse state observed, or STEADY if none. ``beat_count`` is
        the number of beat records the agent currently has. The
        snapshot is stored and returned; the agent's cached profile
        is invalidated.
        """
        with self._lock:
            avg_tempo = self._avg_tempo_locked(agent_id)
            tempo_regime = _determine_regime(avg_tempo)
            agent_readings = self._agent_readings_locked(agent_id)
            dominant_beat = self._mode_beat_locked(agent_readings)
            pulse_state = self._most_recent_pulse_state_locked(agent_id)
            beat_count = len(self._agent_beats_locked(agent_id))
            snapshot = CadenceSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_tempo=round(avg_tempo, 4),
                dominant_beat=dominant_beat,
                tempo_regime=tempo_regime,
                pulse_state=pulse_state,
                beat_count=beat_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CadenceSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The
        most recently taken ``limit`` snapshots are returned. The
        returned list is a snapshot copy; mutating it does not
        affect the engine.
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

    def get_snapshot(self, snapshot_id: str) -> CadenceSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Rhythm Plans ─────────────────────────────────────────────

    def plan_rhythm(
        self,
        agent_id: str,
        strategy: Any,
        target_tempo: float,
        rationale: str,
    ) -> RhythmPlan:
        """Record a rhythm plan for an agent and return it.

        ``strategy`` may be passed as a ``RhythmStrategy`` member or
        its string name/value. ``target_tempo`` is clamped to [0, 1].
        ``current_tempo`` is derived from the agent's readings
        (most-recent tempo or mean if none) and clamped to [0, 1].
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured tempo.
        """
        with self._lock:
            current_tempo = _clamp(
                self._current_tempo_locked(agent_id), 0.0, 1.0
            )
            plan = RhythmPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(RhythmStrategy, strategy),
                target_tempo=_clamp(target_tempo, 0.0, 1.0),
                current_tempo=current_tempo,
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RhythmPlan]:
        """Return rhythm plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> RhythmPlan:
        """Retrieve a rhythm plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Pulse Records ────────────────────────────────────────────

    def record_pulse(
        self,
        agent_id: str,
        from_state: Any,
        to_state: Any,
        interval_ms: float,
        drift_indicator: Any,
        notes: Optional[str] = None,
    ) -> PulseRecord:
        """Record a pulse-state transition for an agent and return it.

        ``from_state`` and ``to_state`` may each be passed as a
        ``PulseState`` member or its string name/value.
        ``drift_indicator`` may be passed as a ``DriftIndicator``
        member or its string name/value. ``interval_ms`` is clamped
        to [0, ∞). The pulse is stored and returned; the agent's
        cached profile is invalidated.
        """
        with self._lock:
            pulse = PulseRecord(
                pulse_id=_new_id(),
                agent_id=str(agent_id),
                from_state=_resolve_enum(PulseState, from_state),
                to_state=_resolve_enum(PulseState, to_state),
                interval_ms=_clamp_positive_ms(interval_ms),
                drift_indicator=_resolve_enum(DriftIndicator, drift_indicator),
                timestamp=_now(),
                notes=notes,
            )
            self._pulses.setdefault(agent_id, []).append(pulse)
            self._profiles.pop(agent_id, None)
            return pulse

    def list_pulses(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PulseRecord]:
        """Return pulse records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all pulses are considered;
        otherwise only pulses for that agent are returned. The most
        recently recorded ``limit`` pulses are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                pulses = self._agent_pulses_locked(agent_id)
            else:
                pulses = []
                for agent_pulses in self._pulses.values():
                    pulses.extend(agent_pulses)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return pulses[-n:] if n else []

    def get_pulse(self, pulse_id: str) -> PulseRecord:
        """Retrieve a pulse record by id.

        Raises ``ValueError`` if no pulse exists with that id.
        """
        with self._lock:
            for agent_pulses in self._pulses.values():
                for pulse in agent_pulses:
                    if pulse.pulse_id == pulse_id:
                        return pulse
        raise ValueError(f"pulse {pulse_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CadenceProfile:
        """Return the agent's cadence profile, building it if missing.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, beats, snapshots, or pulses change. If
        the agent has data but no profile yet, the profile is built
        from the live stores. Call ``update_profile`` to force a
        refresh or override a computed field. Field semantics are
        documented on ``CadenceProfile`` and
        ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> CadenceProfile:
        """Refresh and optionally override fields of an agent's cadence profile.

        The profile is first recomputed from the live stores, then
        any supplied keyword overrides (matching ``CadenceProfile``
        field names) are applied, and ``last_updated`` is stamped.
        Accepted overrides: ``avg_tempo`` (float), ``dominant_beat``
        (``BeatType``), ``tempo_regime`` (``TempoRegime``),
        ``total_readings``, ``total_beats``, and ``total_pulses``
        (int). Enum-valued overrides may be passed as the enum
        member or its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_tempo":
                    try:
                        profile.avg_tempo = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_beat":
                    try:
                        profile.dominant_beat = _resolve_enum(BeatType, value)
                    except ValueError:
                        pass
                elif key == "tempo_regime":
                    try:
                        profile.tempo_regime = _resolve_enum(TempoRegime, value)
                    except ValueError:
                        pass
                elif key in ("total_readings", "total_beats", "total_pulses"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CadenceProfile]:
        """Return all stored cadence profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> CadenceStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, beats, snapshots, and pulses. Scalar
        totals are the counts of each record type. ``avg_tempo`` is
        the mean tempo score across all readings, or 0.0 when none
        exist. ``dominant_regime`` is the most frequent tempo regime
        across all snapshots, or ANDANTE when none exist. When no
        snapshots exist but readings do, the dominant regime is
        derived from the average tempo via ``_determine_regime`` so
        the stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._beats.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._pulses.keys())

            total_readings = 0
            tempo_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    tempo_sum += reading.tempo_score
            avg_tempo = (
                round(tempo_sum / total_readings, 4) if total_readings else 0.0
            )

            total_beats = sum(
                len(agent_beats) for agent_beats in self._beats.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_pulses = sum(
                len(agent_pulses) for agent_pulses in self._pulses.values()
            )

            regime_counts: Dict[TempoRegime, int] = {}
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    regime_counts[snapshot.tempo_regime] = (
                        regime_counts.get(snapshot.tempo_regime, 0) + 1
                    )
            if regime_counts:
                dominant_regime = max(
                    regime_counts.items(), key=lambda kv: kv[1]
                )[0]
            elif total_readings:
                # No snapshots yet, but readings exist: derive the regime
                # from the average tempo so the stats reflect real state.
                dominant_regime = _determine_regime(avg_tempo)
            else:
                dominant_regime = TempoRegime.ANDANTE

            return CadenceStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_beats=total_beats,
                total_snapshots=total_snapshots,
                total_pulses=total_pulses,
                avg_tempo=avg_tempo,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCadence] = None
_engine_lock = threading.Lock()


def get_cadence_engine() -> AgentCognitiveCadence:
    """Get or create the singleton ``AgentCognitiveCadence`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveCadence()
    return _engine


def reset_cadence_engine() -> None:
    """Reset the singleton ``AgentCognitiveCadence`` instance.

    Drops the reference to the current engine so the next
    ``get_cadence_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
