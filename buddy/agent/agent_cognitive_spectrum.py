from __future__ import annotations

"""Agent Cognitive Spectrum Engine — range and distribution of cognitive frequencies

Tracks how broad, tuned, and coherent an agent’s cognitive operating range is
across frequency, wavelength, amplitude, phase, coherence, and bandwidth.

Core capabilities:
  - Spectrum Readings: per-axis observations with source and intensity
  - Tuning Records: events that changed spectrum with before/after scores
  - Spectrum Plans: tune, filter, expand, shift, mix, harmonize strategies
  - Stage Lifecycle: narrow through tuning, broadening, wide, full, omni
  - Regime Classification: monochromatic through white spectrum

Architecture:
  AgentCognitiveSpectrum (singleton)
  ├── SpectrumReading, TuningRecord, SpectrumSnapshot
  ├── SpectrumPlan, FullbandRecord, SpectrumProfile
  └── SpectrumStats
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
    """Generate a short unique identifier for a reading/tuning/etc.

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
    engine with a ``NaN`` or ``None`` spectrum. A low-side default is
    safer than a mid-range one for spectrum-like quantities where a
    spurious high reading would inflate the perceived breadth and
    push the agent's regime toward WHITE.
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
    real fullband intervals and tuning magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate expansion
    may apply a large effective tuning.
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
    against member values (e.g. ``"monochromatic"``) and then against
    member names (e.g. ``"MONOCHROMATIC"``), so callers may pass either
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


def _determine_regime(avg_spectrum: float) -> "SpectrumRegime":
    """Classify a spectrum regime from the average spectrum score.

    The average spectrum is clamped to [0, 1] where higher means a
    broader, more complete cognitive range. The bands are applied in
    order, so the first matching band wins: below 0.15 the agent is
    MONOCHROMATIC (a single frequency, sharp but limited); below 0.35
    it is NARROW (a small band, focused); below 0.55 it is BAND (a
    workable range, neither narrow nor wide); below 0.75 it is
    BROADBAND (a wide range, versatile); below 0.9 it is FULL (a
    near-complete range); otherwise it is WHITE (a full spectrum,
    operating across all frequencies).
    """
    avg = _clamp(avg_spectrum, 0.0, 1.0)
    if avg < 0.15:
        return SpectrumRegime.MONOCHROMATIC
    if avg < 0.35:
        return SpectrumRegime.NARROW
    if avg < 0.55:
        return SpectrumRegime.BAND
    if avg < 0.75:
        return SpectrumRegime.BROADBAND
    if avg < 0.9:
        return SpectrumRegime.FULL
    return SpectrumRegime.WHITE


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class SpectrumAxis(str, Enum):
    """The axis along which a spectrum reading is taken.

    Each axis names a different dimension of the agent's cognitive
    spectrum whose breadth can be measured. FREQUENCY is the rate of
    cognitive processing. WAVELENGTH is the scale of the patterns the
    agent engages with. AMPLITUDE is the intensity of cognitive
    engagement. PHASE is the alignment of cognitive cycles. COHERENCE
    is the internal consistency across the spectrum. BANDWIDTH is the
    capacity for simultaneous processing.
    """
    FREQUENCY = "frequency"    # rate of cognitive processing
    WAVELENGTH = "wavelength"  # scale of patterns engaged
    AMPLITUDE = "amplitude"    # intensity of engagement
    PHASE = "phase"            # alignment of cognitive cycles
    COHERENCE = "coherence"    # consistency across the spectrum
    BANDWIDTH = "bandwidth"    # capacity for simultaneous processing


class SpectrumRegime(str, Enum):
    """The regime an agent's spectrum occupies, classified by breadth.

    Ranges from MONOCHROMATIC (a single frequency) through NARROW (a
    small band), BAND (a workable range), BROADBAND (a wide range),
    and FULL (a near-complete range) to WHITE (a full spectrum,
    operating across all frequencies). The regime is derived from the
    average spectrum across the agent's readings via
    ``_determine_regime``.
    """
    MONOCHROMATIC = "monochromatic"  # single frequency
    NARROW = "narrow"                # small band
    BAND = "band"                    # workable range
    BROADBAND = "broadband"          # wide range
    FULL = "full"                    # near-complete range
    WHITE = "white"                  # full spectrum


class SpectrumSource(str, Enum):
    """A source that contributes to the agent's spectrum.

    Each source names a different origin of spectral content.
    EXPERIENCE accumulates from lived episodes. LEARNING accumulates
    from study and instruction. ADAPTATION accumulates from adjusting
    to conditions. EVOLUTION accumulates from long-term development.
    DIVERSITY accumulates from engaging with varied inputs.
    EXPLORATION accumulates from seeking out the unknown. A spectrum
    reading records which source contributed to the measured axis, and
    a tuning record records which source drove a change.
    """
    EXPERIENCE = "experience"    # lived episodes
    LEARNING = "learning"        # study and instruction
    ADAPTATION = "adaptation"    # adjusting to conditions
    EVOLUTION = "evolution"      # long-term development
    DIVERSITY = "diversity"      # varied inputs
    EXPLORATION = "exploration"  # seeking the unknown


class SpectrumStrategy(str, Enum):
    """Strategy for tuning or broadening the spectrum deliberately.

    TUNE sharpens the dominant frequency. FILTER removes noise from
    the spectrum. EXPAND adds new frequencies to the range. SHIFT
    moves the center of the spectrum. MIX blends multiple
    frequencies. HARMONIZE aligns the spectrum's frequencies with
    each other. Each strategy is suited to a different spectral
    state, from sharpening a diffuse band to harmonizing a broad but
    incoherent range.
    """
    TUNE = "tune"          # sharpen dominant frequency
    FILTER = "filter"      # remove noise from spectrum
    EXPAND = "expand"      # add new frequencies to range
    SHIFT = "shift"        # move center of spectrum
    MIX = "mix"            # blend multiple frequencies
    HARMONIZE = "harmonize"  # align frequencies with each other


class SpectrumStage(str, Enum):
    """The lifecycle stage of an agent's spectrum broadening process.

    NARROW is the state of operating on a single band. TUNING is the
    phase of deliberately sharpening or softening the band. BROADENING
    is the phase of actively widening the range. WIDE is the state of
    operating across a wide band. FULL is the state of operating
    across nearly all frequencies. OMNI is the final state at which
    the agent operates across the full spectrum with coherence. The
    engine records transitions between stages as FullbandRecord
    entries.
    """
    NARROW = "narrow"        # single band
    TUNING = "tuning"        # sharpening or softening the band
    BROADENING = "broadening"  # actively widening the range
    WIDE = "wide"            # wide band
    FULL = "full"            # nearly all frequencies
    OMNI = "omni"            # full spectrum with coherence


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SpectrumReading:
    """One observation of the spectrum on a particular axis.

    ``axis`` is the ``SpectrumAxis`` the reading is taken on.
    ``spectrum_score`` in [0, 1] measures how broad the agent's
    spectrum is on that axis — 0 means monochromatic, 1 means full
    spectrum. ``source`` is the ``SpectrumSource`` contributing to the
    reading. ``intensity`` in [0, 1] measures how emphatic the
    observation was. ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: SpectrumAxis
    spectrum_score: float    # 0..1, higher = broader spectrum
    source: SpectrumSource
    intensity: float         # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(SpectrumAxis, self.axis),
            "spectrum_score": self.spectrum_score,
            "source": _enum_value(SpectrumSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class TuningRecord:
    """One tuning event that changed the spectrum on an axis.

    ``axis`` is the ``SpectrumAxis`` on which the tuning occurred.
    ``source`` is the ``SpectrumSource`` that drove the change.
    ``before_score`` in [0, 1] is the spectrum before the event;
    ``after_score`` in [0, 1] is the spectrum after.
    ``tuning_magnitude`` in [0, ∞) measures how strong the tuning
    was. ``notes`` is an optional free-form annotation.
    """
    tuning_id: str
    agent_id: str
    axis: SpectrumAxis
    source: SpectrumSource
    before_score: float          # 0..1, spectrum before tuning
    after_score: float           # 0..1, spectrum after tuning
    tuning_magnitude: float      # 0..inf, strength of tuning
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this tuning record to a plain dict, expanding enums via ``.value``."""
        return {
            "tuning_id": self.tuning_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(SpectrumAxis, self.axis),
            "source": _enum_value(SpectrumSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "tuning_magnitude": self.tuning_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class SpectrumSnapshot:
    """Aggregate spectrum state for one agent at one moment.

    ``avg_spectrum`` in [0, 1] is the mean spectrum score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is
    the most frequent ``SpectrumAxis`` among those readings, or
    FREQUENCY if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_spectrum``. ``tuning_count`` is
    the number of tuning events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_spectrum: float
    dominant_axis: SpectrumAxis
    dominant_regime: SpectrumRegime
    tuning_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_spectrum": self.avg_spectrum,
            "dominant_axis": _enum_value(SpectrumAxis, self.dominant_axis),
            "dominant_regime": _enum_value(SpectrumRegime, self.dominant_regime),
            "regime": _enum_value(SpectrumRegime, self.dominant_regime),
            "tuning_count": self.tuning_count,
            "timestamp": self.timestamp,
        }


@dataclass
class SpectrumPlan:
    """A plan to tune or broaden the spectrum with a strategy.

    ``strategy`` is the ``SpectrumStrategy`` chosen.
    ``target_spectrum`` in [0, 1] is the spectrum breadth the plan
    aims to reach. ``rationale`` explains why this strategy was chosen
    for this agent's spectral state. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current spectrum — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: SpectrumStrategy
    target_spectrum: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(SpectrumStrategy, self.strategy),
            "target_spectrum": self.target_spectrum,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class FullbandRecord:
    """One record of a stage transition in the broadening lifecycle.

    ``from_stage`` is the ``SpectrumStage`` the agent was in before
    the transition. ``to_stage`` is the ``SpectrumStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow broaden",
    "sudden fullband", "deliberate expansion").
    """
    fullband_id: str
    agent_id: str
    from_stage: SpectrumStage
    to_stage: SpectrumStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this fullband record to a plain dict, expanding enums via ``.value``."""
        return {
            "fullband_id": self.fullband_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(SpectrumStage, self.from_stage),
            "to_stage": _enum_value(SpectrumStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class SpectrumProfile:
    """Per-agent aggregate spectrum tendencies.

    ``avg_spectrum`` in [0, 1] is the mean spectrum score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``SpectrumAxis`` among the agent's readings, or
    FREQUENCY if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_spectrum``. ``total_readings``,
    ``total_tunings``, and ``total_fullbands`` are the counts of each
    record type for the agent. ``last_updated`` is the timestamp of
    the most recent profile computation.
    """
    profile_id: str
    agent_id: str
    avg_spectrum: float = 0.0
    dominant_axis: SpectrumAxis = SpectrumAxis.FREQUENCY
    dominant_regime: SpectrumRegime = SpectrumRegime.BAND
    total_readings: int = 0
    total_tunings: int = 0
    total_fullbands: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_spectrum": self.avg_spectrum,
            "dominant_axis": _enum_value(SpectrumAxis, self.dominant_axis),
            "dominant_regime": _enum_value(SpectrumRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_tunings": self.total_tunings,
            "total_fullbands": self.total_fullbands,
            "last_updated": self.last_updated,
        }


@dataclass
class SpectrumStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_spectrum`` is the mean spectrum score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the
    most frequent regime across all cached profiles, or BAND when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_tunings: int = 0
    total_snapshots: int = 0
    total_fullbands: int = 0
    avg_spectrum: float = 0.0
    dominant_regime: SpectrumRegime = SpectrumRegime.BAND

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_tunings": self.total_tunings,
            "total_snapshots": self.total_snapshots,
            "total_fullbands": self.total_fullbands,
            "avg_spectrum": self.avg_spectrum,
            "dominant_regime": _enum_value(SpectrumRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveSpectrum:
    """Thread-safe engine that models an agent's cognitive spectrum.

    The engine holds six stores: ``_readings`` (SpectrumReading lists
    keyed by agent_id), ``_tunings`` (TuningRecord lists keyed by
    agent_id), ``_snapshots`` (SpectrumSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of SpectrumPlan), ``_fullbands``
    (FullbandRecord lists keyed by agent_id), and ``_profiles``
    (SpectrumProfile keyed by agent_id, cached and invalidated on
    mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The spectrum model is deliberately heuristic: spectrum scores
    and intensities are caller-supplied observations; spectrum
    regimes are banded from the average spectrum; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how spectrum breadth
    is measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure spectrum itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, tunings, snapshots, or fullbands change, so
    ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose spectrum scores feed into
    # a snapshot's average spectrum. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current spectrum posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty spectrum engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[SpectrumReading]] = {}
        self._tunings: Dict[str, List[TuningRecord]] = {}
        self._snapshots: Dict[str, List[SpectrumSnapshot]] = {}
        self._plans: List[SpectrumPlan] = []
        self._fullbands: Dict[str, List[FullbandRecord]] = {}
        self._profiles: Dict[str, SpectrumProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_spectrum_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._tunings.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._fullbands.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[SpectrumReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_tunings_locked(
        self, agent_id: str
    ) -> List[TuningRecord]:
        """Return one agent's tuning records in insertion order. Caller holds the lock."""
        return list(self._tunings.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[SpectrumSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(
        self, agent_id: str
    ) -> List[SpectrumPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock."""
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_fullbands_locked(
        self, agent_id: str
    ) -> List[FullbandRecord]:
        """Return one agent's fullband records in insertion order. Caller holds the lock."""
        return list(self._fullbands.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[SpectrumReading]
    ) -> SpectrumAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns FREQUENCY if the list is
        empty, since FREQUENCY is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return SpectrumAxis.FREQUENCY
        counts: Counter = Counter()
        first_seen_order: Dict[SpectrumAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: SpectrumAxis = readings[0].axis
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
        self, profiles: List[SpectrumProfile]
    ) -> SpectrumRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns BAND if the list is empty, since BAND is the neutral
        mid-range regime — the band that contains the midpoint of the
        spectrum scale, neither monochromatic nor white. Caller holds
        the lock.
        """
        if not profiles:
            return SpectrumRegime.BAND
        counts: Dict[SpectrumRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> SpectrumProfile:
        """Aggregate an agent's readings, tunings, and fullbands into a profile.

        See ``SpectrumProfile`` for field semantics. ``avg_spectrum``
        is the mean spectrum score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent ``SpectrumAxis``
        among the agent's readings, or FREQUENCY if none.
        ``dominant_regime`` is derived via ``_determine_regime`` from
        ``avg_spectrum``. ``total_readings``, ``total_tunings``, and
        ``total_fullbands`` count the records held for the agent.
        ``last_updated`` is the timestamp of this computation. Caller
        holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        tunings = self._agent_tunings_locked(agent_id)
        fullbands = self._agent_fullbands_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_spectrum = sum(r.spectrum_score for r in readings) / len(
                readings
            )
        else:
            avg_spectrum = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_spectrum)

        return SpectrumProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_spectrum=round(avg_spectrum, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_tunings=len(tunings),
            total_fullbands=len(fullbands),
            last_updated=_now(),
        )

    # ── Spectrum Readings ─────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        spectrum_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> SpectrumReading:
        """Record a spectrum reading for an agent and return it.

        ``axis`` may be passed as a ``SpectrumAxis`` member or its
        string name/value. ``spectrum_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``SpectrumSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = SpectrumReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(SpectrumAxis, axis),
                spectrum_score=_clamp(spectrum_score, 0.0, 1.0),
                source=_resolve_enum(SpectrumSource, source),
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
    ) -> List[SpectrumReading]:
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

    def get_reading(self, reading_id: str) -> SpectrumReading:
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

    # ── Tuning Records ────────────────────────────────────────────

    def record_tuning(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        tuning_magnitude: float,
        notes: Optional[str] = None,
    ) -> TuningRecord:
        """Record a tuning event for an agent and return it.

        ``axis`` may be passed as a ``SpectrumAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``SpectrumSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``tuning_magnitude`` is clamped to [0, ∞). The tuning
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = TuningRecord(
                tuning_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(SpectrumAxis, axis),
                source=_resolve_enum(SpectrumSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                tuning_magnitude=_clamp_positive_ms(
                    tuning_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._tunings.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_tunings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TuningRecord]:
        """Return tuning records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all tunings are considered;
        otherwise only tunings for that agent are returned. The
        most recently recorded ``limit`` tunings are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                tunings = self._agent_tunings_locked(agent_id)
            else:
                tunings = []
                for agent_tunings in self._tunings.values():
                    tunings.extend(agent_tunings)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return tunings[-n:] if n else []

    def get_tuning(self, tuning_id: str) -> TuningRecord:
        """Retrieve a tuning record by id.

        Raises ``ValueError`` if no tuning exists with that id.
        """
        with self._lock:
            for agent_tunings in self._tunings.values():
                for tuning in agent_tunings:
                    if tuning.tuning_id == tuning_id:
                        return tuning
        raise ValueError(f"tuning {tuning_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> SpectrumSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_spectrum`` is the mean spectrum score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``SpectrumAxis`` among those readings, or FREQUENCY if none.
        ``dominant_regime`` is derived via ``_determine_regime`` from
        ``avg_spectrum``. ``tuning_count`` is the number of tuning
        events recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_spectrum = sum(
                    r.spectrum_score for r in recent
                ) / len(recent)
            else:
                avg_spectrum = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            dominant_regime = _determine_regime(avg_spectrum)
            tuning_count = len(
                self._agent_tunings_locked(agent_id)
            )

            snapshot = SpectrumSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_spectrum=round(avg_spectrum, 4),
                dominant_axis=dominant_axis,
                dominant_regime=dominant_regime,
                tuning_count=tuning_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SpectrumSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The
        most recently taken ``limit`` snapshots are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
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

    def get_snapshot(self, snapshot_id: str) -> SpectrumSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Spectrum Plans ────────────────────────────────────────────

    def plan_spectrum(
        self,
        agent_id: str,
        strategy: Any,
        target_spectrum: float,
        rationale: str,
    ) -> SpectrumPlan:
        """Record a spectrum plan for an agent and return it.

        ``strategy`` may be passed as a ``SpectrumStrategy`` member
        or its string name/value. ``target_spectrum`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured spectrum.
        """
        with self._lock:
            plan = SpectrumPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(SpectrumStrategy, strategy),
                target_spectrum=_clamp(target_spectrum, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SpectrumPlan]:
        """Return spectrum plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> SpectrumPlan:
        """Retrieve a spectrum plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Fullband Records ─────────────────────────────────────────

    def record_fullband(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> FullbandRecord:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``SpectrumStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        broaden", "sudden fullband", "deliberate expansion"). The
        fullband record is stored and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            record = FullbandRecord(
                fullband_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(SpectrumStage, from_stage),
                to_stage=_resolve_enum(SpectrumStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._fullbands.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_fullbands(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FullbandRecord]:
        """Return fullband records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all fullbands are considered;
        otherwise only fullbands for that agent are returned. The
        most recently recorded ``limit`` fullband records are
        returned. The returned list is a snapshot copy; mutating it
        does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                fullbands = self._agent_fullbands_locked(agent_id)
            else:
                fullbands = []
                for agent_fullbands in self._fullbands.values():
                    fullbands.extend(agent_fullbands)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return fullbands[-n:] if n else []

    def get_fullband(self, fullband_id: str) -> FullbandRecord:
        """Retrieve a fullband record by id.

        Raises ``ValueError`` if no fullband record exists with that
        id.
        """
        with self._lock:
            for agent_fullbands in self._fullbands.values():
                for record in agent_fullbands:
                    if record.fullband_id == fullband_id:
                        return record
        raise ValueError(f"fullband record {fullband_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> SpectrumProfile:
        """Return the agent's spectrum profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, tunings, snapshots, or
        fullbands change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on
        ``SpectrumProfile`` and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(
        self, agent_id: str, **kwargs: Any
    ) -> SpectrumProfile:
        """Refresh and optionally override fields of an agent's spectrum profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``SpectrumProfile`` field names) are applied. Accepted
        overrides: ``avg_spectrum`` (float), ``dominant_axis``
        (``SpectrumAxis``), ``dominant_regime``
        (``SpectrumRegime``), ``total_readings``, ``total_tunings``,
        ``total_fullbands`` (int). Enum-valued overrides may be
        passed as the enum member or its string name/value. Unknown
        keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_spectrum":
                    try:
                        profile.avg_spectrum = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            SpectrumAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            SpectrumRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_tunings",
                    "total_fullbands",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[SpectrumProfile]:
        """Return all stored spectrum profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> SpectrumStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, tunings, snapshots, and fullbands.
        Scalar totals are the counts of each record type.
        ``avg_spectrum`` is the mean spectrum score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or BAND when
        none exist. When no profiles exist but readings do, the
        dominant regime is derived from the average spectrum via
        ``_determine_regime`` so the stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._tunings.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._fullbands.keys())

            total_readings = 0
            spectrum_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    spectrum_sum += reading.spectrum_score
            avg_spectrum = (
                round(spectrum_sum / total_readings, 4) if total_readings else 0.0
            )

            total_tunings = sum(
                len(agent_tunings)
                for agent_tunings in self._tunings.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_fullbands = sum(
                len(agent_fullbands)
                for agent_fullbands in self._fullbands.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average spectrum so the stats
                # reflect real state rather than the default BAND.
                dominant_regime = _determine_regime(avg_spectrum)
            else:
                dominant_regime = SpectrumRegime.BAND

            return SpectrumStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_tunings=total_tunings,
                total_snapshots=total_snapshots,
                total_fullbands=total_fullbands,
                avg_spectrum=avg_spectrum,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveSpectrum] = None
_engine_lock = threading.Lock()


def get_spectrum_engine() -> AgentCognitiveSpectrum:
    """Get or create the singleton ``AgentCognitiveSpectrum`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveSpectrum()
    return _engine


def reset_spectrum_engine() -> None:
    """Reset the singleton ``AgentCognitiveSpectrum`` instance.

    Drops the reference to the current engine so the next
    ``get_spectrum_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
