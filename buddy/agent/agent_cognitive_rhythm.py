from __future__ import annotations

"""Agent Cognitive Rhythm Engine — temporal oscillation patterns of cognitive

activity. Just as biological systems exhibit circadian rhythms (daily
cycles of wakefulness and sleep, of alertness and recovery), cognition
itself oscillates. An agent's cognitive activity is not a flat, constant
stream of equal-effort output. It has rhythms: periods of high focus
where sustained concentration is cheap, creative bursts where generative
flow comes easily, consolidation phases where the agent integrates what
it has produced, and rest cycles where recovery happens. The rhythm is
the substrate on which every cognitive act is performed. Two identical
tasks done at different points in the rhythm cost different amounts of
effort and produce different quality of result.

This is genuinely distinct from temporal_reasoning, which reasons about
time as a concept — ordering events, reasoning about durations, modelling
deadlines. The rhythm engine is not reasoning about time at all. It is
modelling the RHYTHM of cognition itself: the periodic return of the
same cognitive phases, the amplitude with which intensity varies across
a cycle, the alignment between a task's demands and the phase the agent
currently occupies. Temporal reasoning asks "when did this happen?";
cognitive rhythm asks "where in its cycle is the agent's cognition, and
what does that mean for the work it is about to do?"

The engine tracks four quantities, each analogous to a property of a
physical oscillation:

  * Periodicity (period)   — the length of one complete cognitive cycle,
                              measured in seconds. An ultradian cycle
                              might be minutes long; a circadian cycle
                              a full day; a per-task cycle only as long
                              as the task itself.
  * Amplitude              — how much the agent's intensity varies
                              between the trough and the peak of the
                              cycle, in [0, 1]. High amplitude means
                              sharp swings between focused and spent;
                              low amplitude means a relatively flat
                              output.
  * Phase                  — the agent's current position within the
                              cycle, in [0, 1). A phase of 0.0 is the
                              start of a focus phase; 0.5 is roughly
                              the opposite pole.
  * Alignment             — how well the type of task the agent is
                              about to perform matches the phase it is
                              currently in. A generative task started
                              at the trough of a focus phase is
                              misaligned; the same task started at the
                              peak is aligned.

This engine instruments that picture operationally. A RhythmPulse is a
single point sample of the agent's cognitive activity at one moment —
its current phase and intensity. A CycleMeasurement records one
observed cognitive cycle: its type (ultradian, circadian, per-session,
per-task, infradian), its period, its amplitude, and its phase offset.
A RhythmSnapshot aggregates an agent's recent pulses into a current
phase, an average intensity, and a regime classification running from
ARRHYTHMIC (no detectable pattern) through IRREGULAR and REGULAR to
HARMONIC (multiple aligned rhythms) and SYNCOPATED (complex but
coherent). An AlignmentDecision records a choice about how to fit a
task to the current phase — match it, defer it, force a phase,
alternate task types, or batch similar tasks into one phase. A
TrendRecord tracks how the rhythm itself is changing over time
(accelerating, decelerating, stable, drifting, disrupting). A
RhythmProfile holds each agent's aggregate rhythm tendencies, and
RhythmStats summarizes engine activity.

This is original Buddy capability: a self-contained, thread-safe
engine with no external runtime dependencies, designed to give agents
honest awareness of their own cognitive rhythm so that work can be
timed to the rhythm rather than fought against it.

Architecture:
    AgentCognitiveRhythm (singleton)
    ├── RhythmPulse          (one point sample of cognitive activity)
    ├── CycleMeasurement    (one observed cognitive cycle)
    ├── RhythmSnapshot      (aggregate of recent pulses into a regime)
    ├── AlignmentDecision   (one decision fitting a task to a phase)
    ├── TrendRecord         (one record of how the rhythm is changing)
    ├── RhythmProfile       (per-agent aggregate tendencies)
    └── RhythmStats         (engine-wide aggregate statistics)
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a pulse/cycle/snapshot/etc."""
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` intensity value.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"focus"``) and then against member names
    (e.g. ``"FOCUS"``), so callers may pass either form. Raises
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

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_regime(consistency_score: float, cycle_count: int) -> "RhythmRegime":
    """Classify a rhythm regime from a consistency score and cycle count.

    The regime describes how detectable the agent's cognitive rhythm is.
    With no cycles observed there is nothing to detect, so the regime is
    ARRHYTHMIC regardless of the consistency score. With cycles in hand,
    the consistency score (a value in [0, 1] derived from how regular the
    observed periods are) partitions the remaining regimes: a low score
    means the rhythm is IRREGULAR (a weak pattern is present but noisy),
    a middling score means REGULAR (a consistent single pattern), a high
    score with several cycles means HARMONIC (multiple rhythms aligned),
    and the top band means SYNCOPATED (complex but coherent, like a
    polyrhythm whose beats land together).
    """
    score = _clamp(consistency_score, 0.0, 1.0)
    if cycle_count == 0:
        return RhythmRegime.ARRHYTHMIC
    if score < 0.3:
        return RhythmRegime.IRREGULAR
    if score < 0.6:
        return RhythmRegime.REGULAR
    if score < 0.85:
        if cycle_count > 2:
            return RhythmRegime.HARMONIC
        return RhythmRegime.REGULAR
    return RhythmRegime.SYNCOPATED


def _consistency_from_periods(periods: List[float]) -> float:
    """Compute a consistency score in [0, 1] from a list of cycle periods.

    The score is one minus the coefficient of variation of the periods
    (standard deviation divided by the mean), clamped to [0, 1]. A list of
    identical periods yields 1.0 (perfectly consistent); a list whose
    periods vary wildly yields a low score. With fewer than two periods
    the rhythm is not yet measurable, so the score is 0.0 (which combined
    with a non-zero cycle count yields IRREGULAR). A degenerate mean of
    zero (all periods zero) also yields 0.0 to avoid division by zero.
    """
    if len(periods) < 2:
        return 0.0
    mean = sum(periods) / len(periods)
    if mean <= 0:
        return 0.0
    variance = sum((p - mean) ** 2 for p in periods) / len(periods)
    std = variance ** 0.5
    cv = std / mean
    return _clamp(1.0 - cv, 0.0, 1.0)


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class RhythmPhase(str, Enum):
    """A position within one cycle of cognitive activity.

    A cognitive cycle is not a featureless oscillation between "on" and
    "off". It passes through qualitatively distinct phases, each of which
    favours a different kind of work. FOCUS is the high-concentration
    phase where sustained, effortful reasoning is cheap and the agent can
    hold a complex structure in mind. CREATIVE_BURST is the generative
    flow phase where novel connections come easily, where the agent
    produces rather than evaluates. CONSOLIDATION is the integrating
    phase where the agent knits together what focus and burst produced,
    turning scattered output into a coherent whole. REST is the recovery
    phase where the agent rebuilds the capacity that focus and burst
    consumed. TRANSITION is the liminal phase between any two of the
    above, where the agent is neither fully in the old phase nor fully in
    the new one.
    """
    FOCUS = "focus"                      # high concentration
    CREATIVE_BURST = "creative_burst"    # generative flow
    CONSOLIDATION = "consolidation"      # integrating
    REST = "rest"                        # recovery
    TRANSITION = "transition"            # between phases


class RhythmRegime(str, Enum):
    """The regime an agent occupies, classified by its rhythm profile.

    A regime is a qualitative characterization of how detectable and how
    coherent the agent's cognitive rhythm is, more informative than the
    raw consistency score alone. ARRHYTHMIC means no rhythm has been
    detected at all — there are no cycles on record, so the agent's
    activity is treated as uniform noise. IRREGULAR means a weak pattern
    is present but noisy: cycles exist but their periods vary too much
    to rely on. REGULAR means a single consistent rhythm is present: the
    agent's cycles repeat with a stable period. HARMONIC means several
    rhythms are present and aligned, like two oscillations whose peaks
    coincide — the agent benefits from multiple coordinated cycles at
    once. SYNCOPATED means the rhythm is complex but coherent, like a
    polyrhythm whose beats land together despite their different
    periods — the agent's activity is richly patterned rather than
    simple.
    """
    ARRHYTHMIC = "arrhythmic"    # no detectable pattern
    IRREGULAR = "irregular"      # weak pattern
    REGULAR = "regular"          # consistent pattern
    HARMONIC = "harmonic"        # multiple aligned rhythms
    SYNCOPATED = "syncopated"    # complex but coherent


class CycleType(str, Enum):
    """The timescale on which a cognitive cycle runs.

    Biological rhythms are classified by their period, and cognitive
    rhythms inherit the same vocabulary. ULTRADIAN cycles are shorter
    than a day — sub-hour swings between focus and fatigue, the basic
    oscillation of attention. CIRCADIAN cycles run across a full day,
    following the wake/sleep and light/dark structure that shapes all
    biological activity. INFRADIAN cycles run longer than a day —
    multi-day rhythms of motivation and energy. SESSION cycles run for
    the length of one working session and reset between sessions. TASK
    cycles run for the length of a single task and reset when the task
    completes. The cycle type determines how the period is interpreted
    and how the rhythm should be matched to task timing.
    """
    ULTRADIAN = "ultradian"    # sub-hour cycles
    CIRCADIAN = "circadian"    # daily
    INFRADIAN = "infradian"    # multi-day
    SESSION = "session"        # per-session
    TASK = "task"              # per-task


class AlignmentStrategy(str, Enum):
    """Strategies for fitting a task to the current rhythm phase.

    Alignment is the art of timing work to the rhythm. MATCH_PHASE
    accepts the current phase and chooses a task that fits it, rather
    than fighting the phase the agent is in. DEFER_TASK waits for the
    optimal phase to arrive before starting the task, accepting a delay
    in exchange for a better fit. FORCE_PHASE deliberately induces the
    phase the task needs, paying the cost of shifting the rhythm so the
    task can run in its preferred phase. ALTERNATE rotates task types so
    that each task lands in a phase suited to it, exploiting the
    natural progression of the cycle. BATCH groups similar tasks together
    into a single phase, so that the one-time cost of entering the phase
    is amortised across many tasks of the same kind.
    """
    MATCH_PHASE = "match_phase"    # align task to current phase
    DEFER_TASK = "defer_task"      # wait for optimal phase
    FORCE_PHASE = "force_phase"    # induce desired phase
    ALTERNATE = "alternate"        # alternate task types
    BATCH = "batch"                # batch similar tasks in same phase


class RhythmTrend(str, Enum):
    """How the rhythm itself is changing over time.

    The rhythm is not static; it evolves. ACCELERATING means the cycles
    are speeding up — the period is shrinking, the agent is moving
    through phases faster than before, which can signal rising energy or
    rising agitation. DECELERATING means the cycles are slowing down —
    the period is lengthening, the agent is lingering in each phase
    longer, which can signal deepening focus or mounting fatigue.
    STABLE means the period is consistent across observations, the
    rhythm holding its shape. DRIFTING means the phase is shifting
    relative to the clock — the same rhythm is present but its peaks and
    troughs are arriving at different times, the way a circadian rhythm
    drifts under jet lag. DISRUPTING means the pattern is breaking down
    — the rhythm is losing coherence, the cycles no longer repeating
    reliably, which can signal overload or the approach of an arrhythmic
    state.
    """
    ACCELERATING = "accelerating"  # cycle speeding up
    DECELERATING = "decelerating"  # cycle slowing down
    STABLE = "stable"              # consistent
    DRIFTING = "drifting"          # phase shifting
    DISRUPTING = "disrupting"      # pattern breaking down


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RhythmPulse:
    """One point sample of an agent's cognitive activity at one moment.

    ``pulse_id`` uniquely identifies this pulse. ``agent_id`` is the agent
    whose activity was sampled. ``phase`` is the ``RhythmPhase`` the agent
    occupied at the moment of sampling. ``intensity`` in [0, 1] is how
    active the agent's cognition was at that moment, where 0 means no
    detectable activity and 1 means peak output. ``timestamp`` is when the
    pulse was recorded. ``context`` is an optional free-form string
    carrying any additional detail the caller wants to preserve (e.g. the
    task that was in progress when the pulse was taken).
    """
    pulse_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    phase: RhythmPhase = RhythmPhase.FOCUS
    intensity: float = 0.0
    timestamp: str = field(default_factory=_now)
    context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this pulse to a plain dict, expanding the enum."""
        return {
            "pulse_id": self.pulse_id,
            "agent_id": self.agent_id,
            "phase": _enum_value(RhythmPhase, self.phase),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class CycleMeasurement:
    """One observed cognitive cycle for an agent.

    ``measurement_id`` uniquely identifies this measurement. ``agent_id``
    is the agent whose cycle was measured. ``cycle_type`` is the
    ``CycleType`` describing the timescale of the cycle. ``period`` in
    seconds is the length of one complete oscillation — the time from one
    peak of a phase to the next peak of the same phase. ``amplitude`` in
    [0, 1] is how much the agent's intensity varied between the trough and
    the peak across the cycle, where 0 means a flat output and 1 means the
    sharpest possible swing. ``phase_offset`` in [0, 1] is where in the
    cycle the measurement was taken, where 0.0 is the start of the focus
    phase and 0.5 is roughly the opposite pole. ``timestamp`` is when the
    measurement was recorded.
    """
    measurement_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    cycle_type: CycleType = CycleType.ULTRADIAN
    period: float = 0.0
    amplitude: float = 0.0
    phase_offset: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this measurement to a plain dict, expanding the enum."""
        return {
            "measurement_id": self.measurement_id,
            "agent_id": self.agent_id,
            "cycle_type": _enum_value(CycleType, self.cycle_type),
            "period": self.period,
            "amplitude": self.amplitude,
            "phase_offset": self.phase_offset,
            "timestamp": self.timestamp,
        }


@dataclass
class RhythmSnapshot:
    """An aggregate view of an agent's rhythm at a point in time.

    ``snapshot_id`` uniquely identifies this snapshot. ``agent_id`` is the
    agent the snapshot summarizes. ``current_phase`` is the ``RhythmPhase``
    of the agent's most recent pulse, or TRANSITION if the agent has no
    pulses yet. ``regime`` is the ``RhythmRegime`` derived from the
    consistency of the agent's observed cycles via ``_determine_regime``.
    ``avg_intensity`` in [0, 1] is the mean intensity across the agent's
    recent pulses (the last 20, or fewer if fewer exist). ``cycle_count``
    is how many cycle measurements the agent has on record at snapshot
    time. ``dominant_cycle`` is the ``CycleType`` that appears most often
    across the agent's cycles, or ``None`` if the agent has none.
    ``timestamp`` is when the snapshot was taken.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    current_phase: RhythmPhase = RhythmPhase.TRANSITION
    regime: RhythmRegime = RhythmRegime.ARRHYTHMIC
    avg_intensity: float = 0.0
    cycle_count: int = 0
    dominant_cycle: Optional[CycleType] = None
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums.

        ``dominant_cycle`` may be ``None``; it is serialized as ``None``
        in that case rather than as a string.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "current_phase": _enum_value(RhythmPhase, self.current_phase),
            "regime": _enum_value(RhythmRegime, self.regime),
            "avg_intensity": self.avg_intensity,
            "cycle_count": self.cycle_count,
            "dominant_cycle": (
                _enum_value(CycleType, self.dominant_cycle)
                if self.dominant_cycle is not None
                else None
            ),
            "timestamp": self.timestamp,
        }


@dataclass
class AlignmentDecision:
    """A decision fitting a task to the current rhythm phase.

    ``decision_id`` uniquely identifies this decision. ``agent_id`` is the
    agent the decision is for. ``task_type`` is a human-readable label for
    the kind of task being fit to the rhythm (e.g. ``"deep_analysis"`` or
    ``"brainstorm"``). ``current_phase`` is the ``RhythmPhase`` the agent
    occupied when the decision was made. ``strategy`` is the
    ``AlignmentStrategy`` selected to fit the task to that phase.
    ``rationale`` is a human-readable explanation of why this strategy
    was chosen for this task in this phase. ``expected_fit`` in [0, 1] is
    how well the task is expected to land given the strategy, where 0 means
    the task is expected to land badly and 1 means it is expected to land
    perfectly. ``timestamp`` is when the decision was made.
    """
    decision_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    task_type: str = ""
    current_phase: RhythmPhase = RhythmPhase.FOCUS
    strategy: AlignmentStrategy = AlignmentStrategy.MATCH_PHASE
    rationale: str = ""
    expected_fit: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this decision to a plain dict, expanding the enums."""
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "current_phase": _enum_value(RhythmPhase, self.current_phase),
            "strategy": _enum_value(AlignmentStrategy, self.strategy),
            "rationale": self.rationale,
            "expected_fit": self.expected_fit,
            "timestamp": self.timestamp,
        }


@dataclass
class TrendRecord:
    """A record of how the agent's rhythm is changing over time.

    ``record_id`` uniquely identifies this record. ``agent_id`` is the
    agent whose rhythm trend is being recorded. ``trend`` is the
    ``RhythmTrend`` describing the direction of change. ``from_period`` in
    seconds is the cycle period before the change. ``to_period`` in
    seconds is the cycle period after the change. ``delta`` is
    ``to_period`` minus ``from_period``, so a positive delta means the
    cycle has lengthened (decelerated) and a negative delta means it has
    shortened (accelerated). ``timestamp`` is when the record was made.
    """
    record_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    trend: RhythmTrend = RhythmTrend.STABLE
    from_period: float = 0.0
    to_period: float = 0.0
    delta: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this record to a plain dict, expanding the enum."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "trend": _enum_value(RhythmTrend, self.trend),
            "from_period": self.from_period,
            "to_period": self.to_period,
            "delta": self.delta,
            "timestamp": self.timestamp,
        }


@dataclass
class RhythmProfile:
    """Per-agent aggregate rhythm tendencies.

    ``agent_id`` is the agent this profile describes. ``dominant_phase`` is
    the ``RhythmPhase`` the agent occupies most often, or TRANSITION if the
    agent has no pulses. ``regime`` is the ``RhythmRegime`` derived from the
    consistency of the agent's observed cycles. ``avg_period`` in seconds is
    the mean period across the agent's cycle measurements, or 0.0 if the
    agent has none. ``avg_amplitude`` in [0, 1] is the mean amplitude
    across the agent's cycle measurements, or 0.0 if the agent has none.
    ``total_pulses`` is how many pulses the agent has on record.
    ``total_cycles`` is how many cycle measurements the agent has on
    record. ``last_updated`` is the timestamp of the most recent profile
    change.
    """
    agent_id: str = ""
    dominant_phase: RhythmPhase = RhythmPhase.TRANSITION
    regime: RhythmRegime = RhythmRegime.ARRHYTHMIC
    avg_period: float = 0.0
    avg_amplitude: float = 0.0
    total_pulses: int = 0
    total_cycles: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enums."""
        return {
            "agent_id": self.agent_id,
            "dominant_phase": _enum_value(RhythmPhase, self.dominant_phase),
            "regime": _enum_value(RhythmRegime, self.regime),
            "avg_period": self.avg_period,
            "avg_amplitude": self.avg_amplitude,
            "total_pulses": self.total_pulses,
            "total_cycles": self.total_cycles,
            "last_updated": self.last_updated,
        }


@dataclass
class RhythmStats:
    """Aggregate statistics over the current engine state.

    ``total_pulses`` counts all recorded ``RhythmPulse`` records.
    ``total_cycles`` counts all recorded ``CycleMeasurement`` records.
    ``total_snapshots`` counts all recorded ``RhythmSnapshot`` records.
    ``total_alignments`` counts all recorded ``AlignmentDecision`` records.
    ``total_trends`` counts all recorded ``TrendRecord`` records.
    ``phase_distribution`` tallies pulses by their phase, keyed by the
    phase's ``.value`` string. ``regime_distribution`` tallies snapshots by
    their diagnosed regime, keyed by the regime's ``.value`` string. Both
    distribution dicts are plain ``Dict[str, int]`` so they are already
    JSON-serializable. ``avg_intensity`` is the mean intensity across all
    recorded pulses, or 0.0 if there are none.
    """
    total_pulses: int = 0
    total_cycles: int = 0
    total_snapshots: int = 0
    total_alignments: int = 0
    total_trends: int = 0
    phase_distribution: Dict[str, int] = field(default_factory=dict)
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    avg_intensity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The distribution dicts are already keyed by ``.value`` strings, so
        they are copied as-is. This keeps the output JSON-serializable
        without further conversion.
        """
        return {
            "total_pulses": self.total_pulses,
            "total_cycles": self.total_cycles,
            "total_snapshots": self.total_snapshots,
            "total_alignments": self.total_alignments,
            "total_trends": self.total_trends,
            "phase_distribution": dict(self.phase_distribution),
            "regime_distribution": dict(self.regime_distribution),
            "avg_intensity": self.avg_intensity,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveRhythm:
    """Singleton engine tracking the temporal rhythm of cognitive activity.

    Holds rhythm pulses, cycle measurements, snapshots, alignment
    decisions, trend records, and per-agent profiles. All state mutations
    are guarded by a single reentrant lock so the engine is safe to call
    from multiple threads, including from within its own methods. The
    engine is intentionally dependency-free so it can run in any Buddy
    runtime without extra packages.

    The engine is a measurement instrument first and a timing advisor
    second. It records what the agent's cognitive activity actually did at
    each sampled moment, aggregates those samples into a rhythm regime
    classification, and — when a task needs to be timed — prescribes an
    alignment strategy that fits the task to the current phase. It does
    not itself force phases or shift the rhythm; it makes the rhythm
    legible so that the agent (or its orchestrator) can decide whether a
    task should be done now, deferred, batched, or run after a deliberate
    phase shift.
    """

    # Caps to keep the in-memory engine bounded under runaway callers.
    MAX_PULSES: int = 5000
    MAX_CYCLES: int = 5000
    MAX_SNAPSHOTS: int = 5000
    MAX_ALIGNMENTS: int = 5000
    MAX_TRENDS: int = 5000
    MAX_RECENT_FOR_SNAPSHOT: int = 20

    def __init__(self) -> None:
        self._pulses: Dict[str, RhythmPulse] = {}
        self._cycles: Dict[str, CycleMeasurement] = {}
        self._snapshots: Dict[str, RhythmSnapshot] = {}
        self._alignments: Dict[str, AlignmentDecision] = {}
        self._trends: Dict[str, TrendRecord] = {}
        self._profiles: Dict[str, RhythmProfile] = {}
        self._stats: Dict[str, float] = self._init_stats()
        self._lock: threading.RLock = threading.RLock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _init_stats() -> Dict[str, float]:
        """Return a fresh running-counter dict for engine statistics."""
        return {
            "total_pulses": 0,
            "total_cycles": 0,
            "total_snapshots": 0,
            "total_alignments": 0,
            "total_trends": 0,
            "intensity_sum": 0.0,
        }

    def _agent_pulses(self, agent_id: str) -> List[RhythmPulse]:
        """Return this agent's pulses in insertion order (no lock)."""
        return [p for p in self._pulses.values() if p.agent_id == agent_id]

    def _agent_cycles(self, agent_id: str) -> List[CycleMeasurement]:
        """Return this agent's cycle measurements in insertion order (no lock)."""
        return [c for c in self._cycles.values() if c.agent_id == agent_id]

    # ── Rhythm Pulses ─────────────────────────────────────────────

    def record_pulse(
        self,
        agent_id: str,
        phase: Any,
        intensity: float,
        context: Optional[str] = None,
    ) -> RhythmPulse:
        """Record a rhythm pulse for an agent and return it.

        ``phase`` accepts a ``RhythmPhase`` member or its value/name string.
        ``intensity`` in [0, 1] is clamped to that range. ``context`` is an
        optional free-form string preserved verbatim on the stored record.
        Raises ``RuntimeError`` if the pulse registry is full.
        """
        with self._lock:
            if len(self._pulses) >= self.MAX_PULSES:
                raise RuntimeError("pulse registry is full")
            pulse = RhythmPulse(
                agent_id=agent_id,
                phase=_resolve_enum(RhythmPhase, phase),
                intensity=_clamp(intensity, 0.0, 1.0),
                timestamp=_now(),
                context=context,
            )
            self._pulses[pulse.pulse_id] = pulse
            self._stats["total_pulses"] += 1
            self._stats["intensity_sum"] += pulse.intensity
            return pulse

    def list_pulses(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RhythmPulse]:
        """Return pulses, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to pulses recorded for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            pulses = list(self._pulses.values())
        if agent_id is not None:
            pulses = [p for p in pulses if p.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return pulses[-n:] if n else []

    def get_pulse(self, pulse_id: str) -> Optional[RhythmPulse]:
        """Retrieve a pulse by id.

        Returns ``None`` if no pulse with the given id exists.
        """
        with self._lock:
            return self._pulses.get(pulse_id)

    # ── Cycle Measurements ────────────────────────────────────────

    def measure_cycle(
        self,
        agent_id: str,
        cycle_type: Any,
        period: float,
        amplitude: float,
        phase_offset: float,
    ) -> CycleMeasurement:
        """Record a cycle measurement for an agent and return it.

        ``cycle_type`` accepts a ``CycleType`` member or its value/name
        string. ``period`` in seconds is the length of one complete
        oscillation; negative values are coerced to 0. ``amplitude`` in
        [0, 1] is clamped to that range. ``phase_offset`` in [0, 1] is
        clamped to that range, expressing where in the cycle the
        measurement was taken. Raises ``RuntimeError`` if the cycle
        registry is full.
        """
        with self._lock:
            if len(self._cycles) >= self.MAX_CYCLES:
                raise RuntimeError("cycle registry is full")
            measurement = CycleMeasurement(
                agent_id=agent_id,
                cycle_type=_resolve_enum(CycleType, cycle_type),
                period=max(0.0, float(period)),
                amplitude=_clamp(amplitude, 0.0, 1.0),
                phase_offset=_clamp(phase_offset, 0.0, 1.0),
                timestamp=_now(),
            )
            self._cycles[measurement.measurement_id] = measurement
            self._stats["total_cycles"] += 1
            return measurement

    def list_cycles(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CycleMeasurement]:
        """Return cycle measurements, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to measurements recorded for that agent.
        ``limit`` caps the number of results, applied after filtering. The
        returned list is ordered most-recent-last (insertion order) and is
        a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            cycles = list(self._cycles.values())
        if agent_id is not None:
            cycles = [c for c in cycles if c.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return cycles[-n:] if n else []

    def get_cycle(self, measurement_id: str) -> Optional[CycleMeasurement]:
        """Retrieve a cycle measurement by id.

        Returns ``None`` if no measurement with the given id exists.
        """
        with self._lock:
            return self._cycles.get(measurement_id)

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> RhythmSnapshot:
        """Aggregate an agent's recent pulses into a rhythm snapshot.

        ``current_phase`` is the ``RhythmPhase`` of the agent's most recent
        pulse, or TRANSITION if the agent has no pulses. ``avg_intensity``
        is the mean ``intensity`` of the agent's most recent pulses, capped
        at the last ``MAX_RECENT_FOR_SNAPSHOT`` (20). ``cycle_count`` is the
        total number of cycle measurements the agent has on record.
        ``dominant_cycle`` is the ``CycleType`` that appears most often
        across the agent's cycles, or ``None`` if the agent has none.
        ``regime`` is derived from the consistency of the agent's observed
        cycle periods via ``_determine_regime``. The snapshot is stored and
        reflected in the engine stats. If the agent has no pulses and no
        cycles, ``current_phase`` is TRANSITION, ``avg_intensity`` is 0.0,
        ``regime`` is ARRHYTHMIC, and ``dominant_cycle`` is ``None``.
        """
        with self._lock:
            agent_pulses = self._agent_pulses(agent_id)
            agent_cycles = self._agent_cycles(agent_id)

            if agent_pulses:
                current_phase = agent_pulses[-1].phase
            else:
                current_phase = RhythmPhase.TRANSITION

            recent = agent_pulses[-self.MAX_RECENT_FOR_SNAPSHOT:]
            if recent:
                avg_intensity = sum(p.intensity for p in recent) / len(recent)
            else:
                avg_intensity = 0.0

            cycle_count = len(agent_cycles)
            periods = [c.period for c in agent_cycles if c.period > 0]
            consistency = _consistency_from_periods(periods)
            regime = _determine_regime(consistency, cycle_count)

            # Dominant cycle is the mode across ALL of the agent's cycles,
            # so a single recent outlier cannot dominate the picture.
            cycle_counts: Dict[CycleType, int] = {}
            for c in agent_cycles:
                cycle_counts[c.cycle_type] = cycle_counts.get(c.cycle_type, 0) + 1
            if cycle_counts:
                dominant_cycle = max(
                    cycle_counts.items(), key=lambda kv: kv[1]
                )[0]
            else:
                dominant_cycle = None

            snapshot = RhythmSnapshot(
                agent_id=agent_id,
                current_phase=current_phase,
                regime=regime,
                avg_intensity=avg_intensity,
                cycle_count=cycle_count,
                dominant_cycle=dominant_cycle,
                timestamp=_now(),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._stats["total_snapshots"] += 1
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RhythmSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to snapshots taken for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a snapshot
        copy; mutating it does not affect the engine.
        """
        with self._lock:
            snapshots = list(self._snapshots.values())
        if agent_id is not None:
            snapshots = [s for s in snapshots if s.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return snapshots[-n:] if n else []

    def get_snapshot(self, snapshot_id: str) -> Optional[RhythmSnapshot]:
        """Retrieve a snapshot by id.

        Returns ``None`` if no snapshot with the given id exists.
        """
        with self._lock:
            return self._snapshots.get(snapshot_id)

    # ── Alignment Decisions ──────────────────────────────────────

    def decide_alignment(
        self,
        agent_id: str,
        task_type: str,
        current_phase: Any,
        strategy: Any,
        rationale: str,
        expected_fit: float,
    ) -> AlignmentDecision:
        """Create an alignment decision for a task and return it.

        ``task_type`` is a human-readable label for the kind of task being
        fit to the rhythm. ``current_phase`` accepts a ``RhythmPhase``
        member or its value/name string and records the phase the agent
        occupied when the decision was made. ``strategy`` accepts an
        ``AlignmentStrategy`` member or its value/name string.
        ``rationale`` is a human-readable explanation of the choice.
        ``expected_fit`` in [0, 1] is clamped to that range. Raises
        ``RuntimeError`` if the alignment registry is full.
        """
        with self._lock:
            if len(self._alignments) >= self.MAX_ALIGNMENTS:
                raise RuntimeError("alignment registry is full")
            decision = AlignmentDecision(
                agent_id=agent_id,
                task_type=str(task_type),
                current_phase=_resolve_enum(RhythmPhase, current_phase),
                strategy=_resolve_enum(AlignmentStrategy, strategy),
                rationale=str(rationale),
                expected_fit=_clamp(expected_fit, 0.0, 1.0),
                timestamp=_now(),
            )
            self._alignments[decision.decision_id] = decision
            self._stats["total_alignments"] += 1
            return decision

    def list_alignments(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AlignmentDecision]:
        """Return alignment decisions, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to decisions recorded for that agent.
        ``limit`` caps the number of results, applied after filtering. The
        returned list is ordered most-recent-last (insertion order) and is
        a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            alignments = list(self._alignments.values())
        if agent_id is not None:
            alignments = [a for a in alignments if a.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return alignments[-n:] if n else []

    def get_alignment(self, decision_id: str) -> Optional[AlignmentDecision]:
        """Retrieve an alignment decision by id.

        Returns ``None`` if no decision with the given id exists.
        """
        with self._lock:
            return self._alignments.get(decision_id)

    # ── Trend Records ────────────────────────────────────────────

    def record_trend(
        self,
        agent_id: str,
        trend: Any,
        from_period: float,
        to_period: float,
    ) -> TrendRecord:
        """Record a rhythm trend for an agent and return it.

        ``trend`` accepts a ``RhythmTrend`` member or its value/name string.
        ``from_period`` in seconds is the cycle period before the change.
        ``to_period`` in seconds is the cycle period after the change.
        ``delta`` is computed as ``to_period - from_period`` so callers do
        not need to supply it. Both periods are coerced to non-negative
        floats. Raises ``RuntimeError`` if the trend registry is full.
        """
        with self._lock:
            if len(self._trends) >= self.MAX_TRENDS:
                raise RuntimeError("trend registry is full")
            from_p = max(0.0, float(from_period))
            to_p = max(0.0, float(to_period))
            record = TrendRecord(
                agent_id=agent_id,
                trend=_resolve_enum(RhythmTrend, trend),
                from_period=from_p,
                to_period=to_p,
                delta=to_p - from_p,
                timestamp=_now(),
            )
            self._trends[record.record_id] = record
            self._stats["total_trends"] += 1
            return record

    def list_trends(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TrendRecord]:
        """Return trend records, optionally filtered by agent, capped to ``limit``.

        ``agent_id`` filters to records recorded for that agent. ``limit``
        caps the number of results, applied after filtering. The returned
        list is ordered most-recent-last (insertion order) and is a
        snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            trends = list(self._trends.values())
        if agent_id is not None:
            trends = [t for t in trends if t.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return trends[-n:] if n else []

    def get_trend(self, record_id: str) -> Optional[TrendRecord]:
        """Retrieve a trend record by id.

        Returns ``None`` if no record with the given id exists.
        """
        with self._lock:
            return self._trends.get(record_id)

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> RhythmProfile:
        """Return the agent's rhythm profile, creating it if absent.

        When a profile does not yet exist for the agent, a fresh one is
        computed from the agent's currently recorded pulses and cycles:
        ``dominant_phase`` is the modal phase across the agent's pulses
        (or TRANSITION if the agent has none), ``regime`` is derived from
        the consistency of the agent's observed cycle periods,
        ``avg_period`` is the mean period across the agent's cycles (or
        0.0 if none), ``avg_amplitude`` is the mean amplitude across the
        agent's cycles (or 0.0 if none), ``total_pulses`` is the agent's
        pulse count, and ``total_cycles`` is the agent's cycle count. The
        profile is then stored so subsequent record calls can update it
        incrementally.
        """
        with self._lock:
            existing = self._profiles.get(agent_id)
            if existing is not None:
                return existing

            agent_pulses = self._agent_pulses(agent_id)
            agent_cycles = self._agent_cycles(agent_id)

            if agent_pulses:
                phase_counts: Dict[RhythmPhase, int] = {}
                for p in agent_pulses:
                    phase_counts[p.phase] = phase_counts.get(p.phase, 0) + 1
                dominant_phase = max(
                    phase_counts.items(), key=lambda kv: kv[1]
                )[0]
            else:
                dominant_phase = RhythmPhase.TRANSITION

            periods = [c.period for c in agent_cycles if c.period > 0]
            consistency = _consistency_from_periods(periods)
            regime = _determine_regime(consistency, len(agent_cycles))

            if agent_cycles:
                avg_period = sum(c.period for c in agent_cycles) / len(agent_cycles)
                avg_amplitude = sum(c.amplitude for c in agent_cycles) / len(agent_cycles)
            else:
                avg_period = 0.0
                avg_amplitude = 0.0

            profile = RhythmProfile(
                agent_id=agent_id,
                dominant_phase=dominant_phase,
                regime=regime,
                avg_period=avg_period,
                avg_amplitude=avg_amplitude,
                total_pulses=len(agent_pulses),
                total_cycles=len(agent_cycles),
                last_updated=_now(),
            )
            self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> RhythmProfile:
        """Update fields on an agent's rhythm profile and return it.

        The profile is fetched (or created) first, then each keyword in
        ``kwargs`` is applied to the matching attribute. ``dominant_phase``
        and ``regime`` may be supplied as enum members or their value/name
        strings; they are normalized to enum members. Numeric fields
        (``avg_period``, ``avg_amplitude``) are coerced to floats. Integer
        fields (``total_pulses``, ``total_cycles``) are coerced to ints.
        Unknown keys are ignored so callers can pass through generic update
        payloads safely.
        """
        with self._lock:
            profile = self.get_profile(agent_id)
            for key, value in kwargs.items():
                if key == "dominant_phase" and value is not None:
                    profile.dominant_phase = _resolve_enum(RhythmPhase, value)
                elif key == "regime":
                    profile.regime = _resolve_enum(RhythmRegime, value)
                elif key in ("avg_period", "avg_amplitude"):
                    try:
                        setattr(profile, key, float(value))
                    except (TypeError, ValueError):
                        pass
                elif key in ("total_pulses", "total_cycles"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
                elif hasattr(profile, key):
                    setattr(profile, key, value)
            profile.last_updated = _now()
            return profile

    def list_profiles(self) -> List[RhythmProfile]:
        """Return all stored rhythm profiles as a snapshot list."""
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> RhythmStats:
        """Compute aggregate statistics over the current engine state.

        Totals are read from the running counter dict maintained by the
        record methods. ``phase_distribution`` is tallied from stored
        pulses and keyed by the phase ``.value`` string.
        ``regime_distribution`` is tallied from stored snapshots and keyed
        by the regime ``.value`` string. Both dicts are plain
        ``Dict[str, int]`` so the result is JSON-serializable directly.
        ``avg_intensity`` is the mean intensity across all recorded
        pulses, or 0.0 if there are none.
        """
        with self._lock:
            s = self._stats
            phase_dist: Dict[str, int] = {}
            for p in self._pulses.values():
                key = _enum_value(RhythmPhase, p.phase)
                phase_dist[key] = phase_dist.get(key, 0) + 1
            regime_dist: Dict[str, int] = {}
            for snap in self._snapshots.values():
                key = _enum_value(RhythmRegime, snap.regime)
                regime_dist[key] = regime_dist.get(key, 0) + 1
            total_pulses = int(s["total_pulses"])
            if total_pulses > 0:
                avg_intensity = float(s["intensity_sum"]) / total_pulses
            else:
                avg_intensity = 0.0
            return RhythmStats(
                total_pulses=total_pulses,
                total_cycles=int(s["total_cycles"]),
                total_snapshots=int(s["total_snapshots"]),
                total_alignments=int(s["total_alignments"]),
                total_trends=int(s["total_trends"]),
                phase_distribution=phase_dist,
                regime_distribution=regime_dist,
                avg_intensity=avg_intensity,
            )

    # ── Maintenance ───────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests.

        Drops every pulse, cycle, snapshot, alignment decision, trend
        record, and profile, and re-initializes the running counters. The
        lock itself is not replaced.
        """
        with self._lock:
            self._pulses.clear()
            self._cycles.clear()
            self._snapshots.clear()
            self._alignments.clear()
            self._trends.clear()
            self._profiles.clear()
            self._stats = self._init_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional["AgentCognitiveRhythm"] = None
_engine_lock = threading.Lock()


def get_rhythm_engine() -> AgentCognitiveRhythm:
    """Get or create the singleton ``AgentCognitiveRhythm`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveRhythm()
    return _engine


def reset_rhythm_engine() -> None:
    """Reset the singleton ``AgentCognitiveRhythm`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_rhythm_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
