from __future__ import annotations

"""Agent Cognitive Echo Engine — thought reverberation and decay over time

Thoughts reverberate through an agent's mind like sound in a chamber,
propagating, reflecting, and decaying until they fade to silence.

Core capabilities:
  - Echo Readings: per-axis reverberation scores (source, wave, reflection, decay)
  - Reverberation Records: events that changed echo with before/after scores
  - Regime Classification: silent, faint, audible, reverberant, resonant, eternal
  - Decay Lifecycle: origin → propagating → reflecting → decaying → faded → silent
  - Echo Plans: strategies to amplify, dampen, reflect, absorb, sustain, or silence
Architecture:
  AgentCognitiveEcho (singleton)
  ├── EchoReading, ReverberationRecord   (readings, reverberation events)
  ├── EchoSnapshot, EchoPlan             (aggregate state, shaping strategy)
  ├── DecayMark, EchoProfile             (stage transitions, per-agent)
  └── EchoStats                          (engine-wide statistics)
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
    """Generate a short unique identifier for a reading/reverberation/etc.

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
    engine with a ``NaN`` or ``None`` echo. A low-side default is
    safer than a mid-range one for echo-like quantities where a
    spurious high reading would inflate the perceived reverberation and
    push the agent's regime toward ETERNAL.
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
    real decay intervals and reverberation magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    amplification may apply a large effective reverberation.
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
    against member values (e.g. ``"audible"``) and then against
    member names (e.g. ``"AUDIBLE"``), so callers may pass either
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


def _determine_regime(avg_echo: float) -> "EchoRegime":
    """Classify an echo regime from the average echo score.

    The average echo is clamped to [0, 1] where higher means a more
    resonant, persistent posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is SILENT (no
    reverberation, thoughts vanish instantly); below 0.35 it is
    FAINT (barely audible, only the loudest thoughts persist); below
    0.55 it is AUDIBLE (moderate reverberation, most thoughts briefly
    echo); below 0.75 it is REVERBERANT (strong reverberation,
    thoughts sustain and reflect); below 0.9 it is RESONANT (deep
    resonance, thoughts ring long and loud); otherwise it is ETERNAL
    (perfectly sustained, thoughts never decay).
    """
    avg = _clamp(avg_echo, 0.0, 1.0)
    if avg < 0.15:
        return EchoRegime.SILENT
    if avg < 0.35:
        return EchoRegime.FAINT
    if avg < 0.55:
        return EchoRegime.AUDIBLE
    if avg < 0.75:
        return EchoRegime.REVERBERANT
    if avg < 0.9:
        return EchoRegime.RESONANT
    return EchoRegime.ETERNAL


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class EchoAxis(str, Enum):
    """The axis along which an echo reading is taken.

    Each axis names a different dimension of the agent's cognitive
    chamber whose echo can be measured. SOURCE is the origin strength
    of a thought. WAVE is the propagation strength outward. REFLECTION
    is the bounce-back strength off memory and belief. AMPLITUDE is
    the peak intensity of the reverberation. FREQUENCY is the
    recurrence rate of the thought. DECAY is the rate at which the
    reverberation fades.
    """
    SOURCE = "source"        # origin strength
    WAVE = "wave"            # propagation strength
    REFLECTION = "reflection"  # bounce-back strength
    AMPLITUDE = "amplitude"  # peak intensity
    FREQUENCY = "frequency"  # recurrence rate
    DECAY = "decay"          # rate of fade


class EchoRegime(str, Enum):
    """The regime an agent's echo occupies, classified by echo score.

    Ranges from SILENT (no reverberation, thoughts vanish instantly)
    through FAINT (barely audible, only the loudest thoughts persist),
    AUDIBLE (moderate reverberation, most thoughts briefly echo),
    REVERBERANT (strong reverberation, thoughts sustain and reflect),
    and RESONANT (deep resonance, thoughts ring long and loud) to
    ETERNAL (perfectly sustained, thoughts never decay). The regime is
    derived from the average echo across the agent's readings via
    ``_determine_regime``.
    """
    SILENT = "silent"            # no reverberation
    FAINT = "faint"              # barely audible
    AUDIBLE = "audible"          # moderate reverberation
    REVERBERANT = "reverberant"  # strong reverberation
    RESONANT = "resonant"        # deep resonance
    ETERNAL = "eternal"          # perfectly sustained


class EchoSource(str, Enum):
    """A source that supplies the original impulse setting a thought reverberating.

    Each source names a different origin of the impulse behind a
    thought. MEMORY re-sounds what was experienced before. THOUGHT
    re-sounds what is being considered. EMOTION re-sounds what is
    felt. SPEECH re-sounds what is said aloud. ACTION re-sounds what
    is done. REFLECTION re-sounds what is examined inward. An echo
    reading records which source supplied the impulse on the measured
    axis, and a reverberation record records which source drove a
    change.
    """
    MEMORY = "memory"        # re-sound of past experience
    THOUGHT = "thought"      # re-sound of consideration
    EMOTION = "emotion"      # re-sound of feeling
    SPEECH = "speech"        # re-sound of spoken words
    ACTION = "action"        # re-sound of deeds
    REFLECTION = "reflection"  # re-sound of inward examination


class EchoStrategy(str, Enum):
    """Strategy for shaping the chamber deliberately.

    AMPLIFY strengthens the reverberation. DAMPEN weakens the
    reverberation. REFLECT bounces the thought back into the chamber.
    ABSORB soaks up the reverberation. SUSTAIN prolongs the decay.
    SILENCE cuts the reverberation short. Each strategy is suited to
    a different chamber condition, from counteracting a silent chamber
    to releasing an eternal one.
    """
    AMPLIFY = "amplify"    # strengthen the reverberation
    DAMPEN = "dampen"      # weaken the reverberation
    REFLECT = "reflect"    # bounce the thought back
    ABSORB = "absorb"      # soak up the reverberation
    SUSTAIN = "sustain"    # prolong the decay
    SILENCE = "silence"    # cut the reverberation short


class EchoStage(str, Enum):
    """The lifecycle stage of an agent's reverberation process.

    ORIGIN is the state in which a thought has arisen. PROPAGATING is
    the phase of spreading outward. REFLECTING is the state of
    bouncing off the chamber walls. DECAYING is the state of fading.
    FADED is the state in which the thought is barely audible. SILENT
    is the final state at which the thought has vanished. The engine
    records transitions between stages as DecayMark entries.
    """
    ORIGIN = "origin"            # thought has arisen
    PROPAGATING = "propagating"  # spreading outward
    REFLECTING = "reflecting"    # bouncing off walls
    DECAYING = "decaying"        # fading
    FADED = "faded"              # barely audible
    SILENT = "silent"            # vanished


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class EchoReading:
    """One observation of echo on a particular axis.

    ``axis`` is the ``EchoAxis`` the reading is taken on.
    ``echo_score`` in [0, 1] measures how strongly the thought is
    reverberating on that axis — 0 means silent, 1 means eternal.
    ``source`` is the ``EchoSource`` supplying the impulse.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: EchoAxis
    echo_score: float        # 0..1, higher = more resonant
    source: EchoSource
    intensity: float         # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(EchoAxis, self.axis),
            "echo_score": self.echo_score,
            "source": _enum_value(EchoSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ReverberationRecord:
    """One reverberation event that changed the echo on an axis.

    ``axis`` is the ``EchoAxis`` on which the reverberation occurred.
    ``source`` is the ``EchoSource`` that drove the change.
    ``before_score`` in [0, 1] is the echo before the event;
    ``after_score`` in [0, 1] is the echo after.
    ``reverberation_magnitude`` in [0, ∞) measures how strong the
    reverberation was. ``notes`` is an optional free-form annotation.
    """
    reverberation_id: str
    agent_id: str
    axis: EchoAxis
    source: EchoSource
    before_score: float                # 0..1, echo before reverberation
    after_score: float                 # 0..1, echo after reverberation
    reverberation_magnitude: float     # 0..inf, strength of reverberation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reverberation record to a plain dict, expanding enums via ``.value``."""
        return {
            "reverberation_id": self.reverberation_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(EchoAxis, self.axis),
            "source": _enum_value(EchoSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "reverberation_magnitude": self.reverberation_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class EchoSnapshot:
    """Aggregate echo state for one agent at one moment.

    ``avg_echo`` in [0, 1] is the mean echo score across the agent's
    recent readings, or 0.0 if none. ``dominant_axis`` is the most
    frequent ``EchoAxis`` among those readings, or SOURCE if none.
    ``dominant_regime`` is derived via ``_determine_regime`` from
    ``avg_echo``. ``reverberation_count`` is the number of
    reverberation events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_echo: float
    dominant_axis: EchoAxis
    dominant_regime: EchoRegime
    reverberation_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Both ``dominant_regime`` and ``regime`` keys are emitted and
        point to the same value, so callers reading either key see a
        consistent regime. ``dominant_regime`` is the canonical name
        matching the field; ``regime`` is kept for backward
        compatibility with consumers that expect the shorter key.
        """
        regime_value = _enum_value(EchoRegime, self.dominant_regime)
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_echo": self.avg_echo,
            "dominant_axis": _enum_value(EchoAxis, self.dominant_axis),
            "dominant_regime": regime_value,
            "regime": regime_value,
            "reverberation_count": self.reverberation_count,
            "timestamp": self.timestamp,
        }


@dataclass
class EchoPlan:
    """A plan to shape the chamber with a strategy.

    ``strategy`` is the ``EchoStrategy`` chosen.
    ``target_echo`` in [0, 1] is the echo the plan aims to reach.
    ``rationale`` explains why this strategy was chosen for this
    agent's chamber condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current echo — callers who need that should
    take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: EchoStrategy
    target_echo: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(EchoStrategy, self.strategy),
            "target_echo": self.target_echo,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class DecayMark:
    """One record of a stage transition in the decay lifecycle.

    ``from_stage`` is the ``EchoStage`` the agent was in before the
    transition. ``to_stage`` is the ``EchoStage`` it moved to.
    ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow propagate",
    "sudden decay", "deliberate sustain").
    """
    decay_id: str
    agent_id: str
    from_stage: EchoStage
    to_stage: EchoStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this decay mark to a plain dict, expanding enums via ``.value``."""
        return {
            "decay_id": self.decay_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(EchoStage, self.from_stage),
            "to_stage": _enum_value(EchoStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class EchoProfile:
    """Per-agent aggregate echo tendencies.

    ``avg_echo`` in [0, 1] is the mean echo score across the agent's
    readings (0.0 if none). ``dominant_axis`` is the most frequent
    ``EchoAxis`` among the agent's readings, or SOURCE if none.
    ``dominant_regime`` is derived via ``_determine_regime`` from
    ``avg_echo``. ``total_readings``, ``total_reverberations``, and
    ``total_decays`` are the counts of each record type for the agent.
    ``updated_at`` is the timestamp at which the profile was last
    computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_echo: float = 0.0
    dominant_axis: EchoAxis = EchoAxis.SOURCE
    dominant_regime: EchoRegime = EchoRegime.AUDIBLE
    total_readings: int = 0
    total_reverberations: int = 0
    total_decays: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_echo": self.avg_echo,
            "dominant_axis": _enum_value(EchoAxis, self.dominant_axis),
            "dominant_regime": _enum_value(EchoRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_reverberations": self.total_reverberations,
            "total_decays": self.total_decays,
            "updated_at": self.updated_at,
        }


@dataclass
class EchoStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_echo`` is the mean echo score across all readings, or
    0.0 when none exist. ``dominant_regime`` is the most frequent
    regime across all cached profiles, or AUDIBLE when none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_reverberations: int = 0
    total_snapshots: int = 0
    total_decays: int = 0
    avg_echo: float = 0.0
    dominant_regime: EchoRegime = EchoRegime.AUDIBLE

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_reverberations": self.total_reverberations,
            "total_snapshots": self.total_snapshots,
            "total_decays": self.total_decays,
            "avg_echo": self.avg_echo,
            "dominant_regime": _enum_value(EchoRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveEcho:
    """Thread-safe engine that models an agent's cognitive echo.

    The engine holds six stores: ``_readings`` (EchoReading lists keyed
    by agent_id), ``_reverberations`` (ReverberationRecord lists keyed
    by agent_id), ``_snapshots`` (EchoSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of EchoPlan), ``_decays``
    (DecayMark lists keyed by agent_id), and ``_profiles``
    (EchoProfile keyed by agent_id, cached and invalidated on
    mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The echo model is deliberately heuristic: echo scores and
    intensities are caller-supplied observations; echo regimes are
    banded from the average echo; dominant axes are computed by mode;
    stage transitions are recorded as observed. These heuristics are
    transparent and auditable rather than learned, which keeps the
    engine deterministic.

    The engine is intentionally agnostic about how echo is measured
    and how stage transitions are detected — callers may derive them
    from any source. The engine's job is to record, aggregate,
    classify, and profile, not to measure echo itself. Profiles are
    cached per agent and invalidated whenever the agent's readings,
    reverberations, snapshots, or decays change, so ``get_profile``
    always reflects the current state unless an explicit override has
    been applied via ``update_profile``.
    """

    # Number of most-recent readings whose echo scores feed into a
    # snapshot's average echo. The window is long enough to smooth a
    # single noisy reading and short enough to reflect the agent's
    # current reverberation posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty echo engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[EchoReading]] = {}
        self._reverberations: Dict[str, List[ReverberationRecord]] = {}
        self._snapshots: Dict[str, List[EchoSnapshot]] = {}
        self._plans: List[EchoPlan] = []
        self._decays: Dict[str, List[DecayMark]] = {}
        self._profiles: Dict[str, EchoProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_echo_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._reverberations.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._decays.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[EchoReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_reverberations_locked(
        self, agent_id: str
    ) -> List[ReverberationRecord]:
        """Return one agent's reverberation records in insertion order. Caller holds the lock."""
        return list(self._reverberations.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[EchoSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[EchoPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_decays_locked(
        self, agent_id: str
    ) -> List[DecayMark]:
        """Return one agent's decay marks in insertion order. Caller holds the lock."""
        return list(self._decays.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[EchoReading]
    ) -> EchoAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns SOURCE if the list is empty,
        since SOURCE is the smallest and most neutral axis. Caller
        holds the lock.
        """
        if not readings:
            return EchoAxis.SOURCE
        counts: Counter = Counter()
        first_seen_order: Dict[EchoAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: EchoAxis = readings[0].axis
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
        self, profiles: List[EchoProfile]
    ) -> EchoRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns AUDIBLE if the list is empty, since AUDIBLE is the
        default regime — the band that represents a normally
        functioning cognitive chamber where thoughts briefly
        reverberate before fading, neither silent nor eternal. Caller
        holds the lock.
        """
        if not profiles:
            return EchoRegime.AUDIBLE
        counts: Dict[EchoRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> EchoProfile:
        """Aggregate an agent's readings, reverberations, and decays into a profile.

        See ``EchoProfile`` for field semantics. ``avg_echo`` is the
        mean echo score across the agent's readings (0.0 if none).
        ``dominant_axis`` is the most frequent ``EchoAxis`` among the
        agent's readings, or SOURCE if none. ``dominant_regime`` is
        derived via ``_determine_regime`` from ``avg_echo``.
        ``total_readings``, ``total_reverberations``, and
        ``total_decays`` count the records held for the agent. Caller
        holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        reverberations = self._agent_reverberations_locked(agent_id)
        decays = self._agent_decays_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_echo = sum(
                r.echo_score for r in readings
            ) / len(readings)
        else:
            avg_echo = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_echo)

        return EchoProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_echo=round(avg_echo, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_reverberations=len(reverberations),
            total_decays=len(decays),
            updated_at=_now(),
        )

    # ── Echo Readings ───────────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        echo_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> EchoReading:
        """Record an echo reading for an agent and return it.

        ``axis`` may be passed as an ``EchoAxis`` member or its string
        name/value. ``echo_score`` and ``intensity`` are clamped to
        [0, 1]. ``source`` may be passed as an ``EchoSource`` member
        or its string name/value. The reading is stored and returned;
        the agent's cached profile is invalidated.
        """
        with self._lock:
            reading = EchoReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(EchoAxis, axis),
                echo_score=_clamp(echo_score, 0.0, 1.0),
                source=_resolve_enum(EchoSource, source),
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
    ) -> List[EchoReading]:
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

    def get_reading(self, reading_id: str) -> EchoReading:
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

    # ── Reverberation Records ──────────────────────────────────────

    def record_reverberation(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        reverberation_magnitude: float,
        notes: Optional[str] = None,
    ) -> ReverberationRecord:
        """Record a reverberation event for an agent and return it.

        ``axis`` may be passed as an ``EchoAxis`` member or its
        string name/value. ``source`` may be passed as an
        ``EchoSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``reverberation_magnitude`` is clamped to [0, ∞). The
        reverberation is stored and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            record = ReverberationRecord(
                reverberation_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(EchoAxis, axis),
                source=_resolve_enum(EchoSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                reverberation_magnitude=_clamp_positive_ms(
                    reverberation_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._reverberations.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_reverberations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReverberationRecord]:
        """Return reverberation records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all reverberations are
        considered; otherwise only reverberations for that agent are
        returned. The most recently recorded ``limit`` reverberations
        are returned. The returned list is a snapshot copy; mutating
        it does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                reverberations = self._agent_reverberations_locked(agent_id)
            else:
                reverberations = []
                for agent_reverberations in self._reverberations.values():
                    reverberations.extend(agent_reverberations)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return reverberations[-n:] if n else []

    def get_reverberation(self, reverberation_id: str) -> ReverberationRecord:
        """Retrieve a reverberation record by id.

        Raises ``ValueError`` if no reverberation exists with that id.
        """
        with self._lock:
            for agent_reverberations in self._reverberations.values():
                for reverberation in agent_reverberations:
                    if reverberation.reverberation_id == reverberation_id:
                        return reverberation
        raise ValueError(f"reverberation {reverberation_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> EchoSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_echo`` is the mean echo score across the agent's most
        recent readings (the last ``_SNAPSHOT_READING_WINDOW`` = 20),
        or 0.0 if none. ``dominant_axis`` is the most frequent
        ``EchoAxis`` among those readings, or SOURCE if none.
        ``dominant_regime`` is derived via ``_determine_regime`` from
        ``avg_echo``. ``reverberation_count`` is the number of
        reverberation events recorded against the agent. The snapshot
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_echo = sum(
                    r.echo_score for r in recent
                ) / len(recent)
            else:
                avg_echo = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            dominant_regime = _determine_regime(avg_echo)
            reverberation_count = len(
                self._agent_reverberations_locked(agent_id)
            )

            snapshot = EchoSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_echo=round(avg_echo, 4),
                dominant_axis=dominant_axis,
                dominant_regime=dominant_regime,
                reverberation_count=reverberation_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EchoSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> EchoSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Echo Plans ──────────────────────────────────────────────────

    def plan_reverberation(
        self,
        agent_id: str,
        strategy: Any,
        target_echo: float,
        rationale: str,
    ) -> EchoPlan:
        """Record a reverberation plan for an agent and return it.

        ``strategy`` may be passed as an ``EchoStrategy`` member or
        its string name/value. ``target_echo`` is clamped to [0, 1].
        ``rationale`` explains why this strategy was chosen. The plan
        is stored in a flat list (not keyed by agent, since plans are
        forward-looking interventions rather than measurements of
        state) and returned. The agent's cached profile is not
        invalidated, since a plan does not change the agent's measured
        echo.
        """
        with self._lock:
            plan = EchoPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(EchoStrategy, strategy),
                target_echo=_clamp(target_echo, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EchoPlan]:
        """Return echo plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> EchoPlan:
        """Retrieve an echo plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Decay Marks ────────────────────────────────────────────────

    def record_decay(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> DecayMark:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as an
        ``EchoStage`` member or its string name/value. ``interval_ms``
        in [0, ∞) is the duration the from_stage held before the
        transition. ``signature`` is a free-form label that describes
        the character of the transition (e.g. "slow propagate",
        "sudden decay", "deliberate sustain"). The decay mark is
        stored and returned; the agent's cached profile is
        invalidated.

        Decay marks carry no ``notes`` field, since the ``signature``
        already captures the free-form character of the transition and
        a second free-form field would be redundant.
        """
        with self._lock:
            record = DecayMark(
                decay_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(EchoStage, from_stage),
                to_stage=_resolve_enum(EchoStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._decays.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_decays(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DecayMark]:
        """Return decay marks, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all decays are considered;
        otherwise only decays for that agent are returned. The most
        recently recorded ``limit`` decay marks are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                decays = self._agent_decays_locked(agent_id)
            else:
                decays = []
                for agent_decays in self._decays.values():
                    decays.extend(agent_decays)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return decays[-n:] if n else []

    def get_decay(self, decay_id: str) -> DecayMark:
        """Retrieve a decay mark by id.

        Raises ``ValueError`` if no decay mark exists with that id.
        """
        with self._lock:
            for agent_decays in self._decays.values():
                for record in agent_decays:
                    if record.decay_id == decay_id:
                        return record
        raise ValueError(f"decay mark {decay_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> EchoProfile:
        """Return the agent's echo profile, building it if missing.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, reverberations, snapshots, or decays
        change. If the agent has data but no profile yet, the profile
        is built from the live stores. Call ``update_profile`` to
        force a refresh or override a computed field. Field semantics
        are documented on ``EchoProfile`` and
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
    ) -> EchoProfile:
        """Refresh and optionally override fields of an agent's echo profile.

        The profile is first recomputed from the live stores, then any
        supplied overrides in ``kwargs`` (matching ``EchoProfile``
        field names) are applied. Accepted overrides: ``avg_echo``
        (float), ``dominant_axis`` (``EchoAxis``),
        ``dominant_regime`` (``EchoRegime``), ``total_readings``,
        ``total_reverberations``, ``total_decays`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_echo":
                    try:
                        profile.avg_echo = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            EchoAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            EchoRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_reverberations",
                    "total_decays",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[EchoProfile]:
        """Return all stored echo profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> EchoStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, reverberations, snapshots, and decays.
        Scalar totals are the counts of each record type. ``avg_echo``
        is the mean echo score across all readings, or 0.0 when none
        exist. ``dominant_regime`` is the most frequent regime across
        all cached profiles, or AUDIBLE when none exist. When no
        profiles exist but readings do, the dominant regime is derived
        from the average echo via ``_determine_regime`` so the stats
        always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._reverberations.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._decays.keys())

            total_readings = 0
            echo_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    echo_sum += reading.echo_score
            avg_echo = (
                round(echo_sum / total_readings, 4) if total_readings else 0.0
            )

            total_reverberations = sum(
                len(agent_reverberations)
                for agent_reverberations in self._reverberations.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_decays = sum(
                len(agent_decays)
                for agent_decays in self._decays.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average echo so the stats
                # reflect real state rather than the default AUDIBLE.
                dominant_regime = _determine_regime(avg_echo)
            else:
                dominant_regime = EchoRegime.AUDIBLE

            return EchoStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_reverberations=total_reverberations,
                total_snapshots=total_snapshots,
                total_decays=total_decays,
                avg_echo=avg_echo,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveEcho] = None
_engine_lock = threading.Lock()


def get_echo_engine() -> AgentCognitiveEcho:
    """Get or create the singleton ``AgentCognitiveEcho`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveEcho()
    return _engine


def reset_echo_engine() -> None:
    """Reset the singleton ``AgentCognitiveEcho`` instance.

    Drops the reference to the current engine so the next
    ``get_echo_engine`` call creates a fresh instance. Useful for tests
    that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
