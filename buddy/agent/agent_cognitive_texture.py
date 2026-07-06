"""Agent Cognitive Texture Engine — qualitative grain of thought

Texture models how fine or coarse the weave of cognition is, from silken
to coarse, distinct from fluidity, viscosity, and solidity.

Core capabilities:
  - Per-axis readings, refinements, regimes, plans, polishes, profiles, stats

Architecture:
  AgentCognitiveTexture (singleton)
  ├── TextureReading     (one observation of texture on one axis)
  ├── RefinementRecord   (one refinement event that changed texture)
  ├── TextureSnapshot    (aggregate texture state for one agent)
  ├── RefinementPlan     (a plan to change texture with a strategy)
  ├── PolishRecord       (one stage transition in the texture lifecycle)
  ├── TextureProfile     (per-agent aggregate texture tendencies)
  └── TextureStats       (engine-wide aggregate statistics)
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
    trivially interchangeable for testing -- tests can monkey-patch
    ``_now`` to a deterministic function rather than reach into every
    record type.
    """
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a reading/refinement/etc.

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
    engine with a ``NaN`` or ``None`` score. A low-side default is
    safer than a mid-range one for texture-like quantities where a
    spurious high reading would inflate the perceived fineness and
    push the agent's regime toward SILKEN.
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

    Durations must be non-negative; negative values are coerced to 0
    rather than rejected so a misconfigured caller cannot crash the
    engine. The upper bound is left open because real intervals can
    legitimately exceed 1.0 -- a long-lived polished stage or a slow
    tempering pass can span arbitrarily many milliseconds before the
    next stage transition is recorded.
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
    against member values (e.g. ``"coarse"``) and then against member
    names (e.g. ``"COARSE"``), so callers may pass either form. This
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


def _determine_regime(avg_texture: float) -> "TextureRegime":
    """Classify a texture regime from the average texture score.

    The average texture is clamped to [0, 1] where higher means a
    finer, more polished grain. The bands are applied in order, so
    the first matching band wins: below 0.15 the texture is COARSE
    (large, irregular grains, rough surface); below 0.35 it is
    ROUGH (noticeable grain, uneven surface); below 0.55 it is
    GRAINY (visible but regular grain); below 0.75 it is SMOOTH
    (fine grain, even surface); below 0.9 it is FINE (very fine
    grain, near-polished surface); otherwise it is SILKEN (grain
    invisible, flawless surface).
    """
    avg = _clamp(avg_texture, 0.0, 1.0)
    if avg < 0.15:
        return TextureRegime.COARSE
    if avg < 0.35:
        return TextureRegime.ROUGH
    if avg < 0.55:
        return TextureRegime.GRAINY
    if avg < 0.75:
        return TextureRegime.SMOOTH
    if avg < 0.9:
        return TextureRegime.FINE
    return TextureRegime.SILKEN


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class TextureAxis(str, Enum):
    """The axis along which a texture reading is taken.

    Each axis names a different kind of cognitive material whose grain
    can be felt. THOUGHT is the raw flow of ideas -- the texture of a
    thought measures how finely or coarsely it is wrought. LANGUAGE
    is the verbal surface -- the texture of language measures how
    polished or rough the phrasing is. IMAGERY is the perceptual
    surface -- the texture of imagery measures how fine or coarse the
    mental picture is. EMOTION is the affective surface -- the texture
    of an emotion measures how refined or blunt its grain is.
    INTUITION is the pre-verbal hunch -- the texture of an intuition
    measures how finely attuned or rough-edged it is. MEMORY is the
    recalled content -- the texture of a memory measures how smooth
    or fragmentary its surface has become.
    """
    THOUGHT = "thought"      # the raw flow of ideas
    LANGUAGE = "language"    # the verbal surface
    IMAGERY = "imagery"      # the perceptual surface
    EMOTION = "emotion"      # the affective surface
    INTUITION = "intuition"  # the pre-verbal hunch
    MEMORY = "memory"        # the recalled content


class TextureRegime(str, Enum):
    """The regime an agent's texture occupies, classified by fineness.

    Ranges from COARSE (large, irregular grains, rough surface)
    through ROUGH (noticeable grain, uneven surface), GRAINY (visible
    but regular grain), SMOOTH (fine grain, even surface), and FINE
    (very fine grain, near-polished surface) to SILKEN (grain
    invisible, flawless surface). The regime is derived from the
    average texture score across the agent's readings via
    ``_determine_regime``.
    """
    COARSE = "coarse"        # large, irregular grains
    ROUGH = "rough"          # noticeable grain, uneven surface
    GRAINY = "grainy"        # visible but regular grain
    SMOOTH = "smooth"        # fine grain, even surface
    FINE = "fine"            # very fine grain, near-polished
    SILKEN = "silken"        # grain invisible, flawless surface


class TextureSource(str, Enum):
    """The source from which a texture is acquired.

    Each source names a different process that drives texture toward
    finer grain. PRACTICE is the most basic: an idea or skill worked
    over repeatedly takes on a finer grain. EXPOSURE is observational:
    sustained contact with well-wrought material transfers some of its
    texture to the agent. REFLECTION is introspective: turning an idea
    over in the mind reveals and refines its grain. IMITATION is
    mimetic: copying the texture of an admired model lends the agent
    its surface qualities. CREATION is generative: producing new
    material under the demand for coherence forces its grain to
    align. MASTERY is achievement: skill so thoroughly acquired that
    its texture is flawless and instantly available.
    """
    PRACTICE = "practice"    # repeated working over
    EXPOSURE = "exposure"    # sustained contact with fine material
    REFLECTION = "reflection"  # introspective inspection
    IMITATION = "imitation"  # mimetic copying of a model
    CREATION = "creation"    # generative production under demand
    MASTERY = "mastery"      # flawless, instantly available skill


class RefinementStrategy(str, Enum):
    """Strategy for changing the texture of cognitive material deliberately.

    POLISH rubs the surface smooth, reducing roughness without altering
    the underlying grain. SMOOTH aligns the grains with one another,
    reducing the variation that produces a coarse feel. COMPOSE
    arranges the grains into a deliberate pattern, trading randomness
    for rhythmic regularity. LAYER adds depth by stacking finer grains
    over coarser ones, producing richness rather than flatness.
    DISTILL removes the coarsest grains, leaving only the finest
    behind -- a reductive operation that raises fineness at the cost
    of volume. TEMPER hardens the texture against stress so a
    polished thought does not lose its grain under pressure. Each
    strategy is suited to a different goal, from softening a too-raw
    impression to distilling a too-rich weave down to its finest thread.
    """
    POLISH = "polish"        # rub the surface smooth
    SMOOTH = "smooth"        # align grains with one another
    COMPOSE = "compose"      # arrange grains into a pattern
    LAYER = "layer"          # stack finer over coarser grains
    DISTILL = "distill"      # remove the coarsest grains
    TEMPER = "temper"        # harden the texture against stress


class TextureStage(str, Enum):
    """The lifecycle stage of a texture as it is worked.

    RAW is the starting state: the material is present but unworked,
    its grain unrefined. SHAPING is the phase in which the material
    is being given a preliminary form -- coarse grains are being
    aligned, the surface is being leveled. REFINING is the phase in
    which the shaped material is being polished -- the grain is being
    made finer, the surface smoother. POLISHED is the stable state at
    which the texture holds its fineness under normal handling.
    LUSTERED is the phase in which the polished surface is being
    given its final depth, the grain receding further from perception.
    FLAWLESS is the final state at which the texture is so fine that
    no grain can be detected and the surface is unbroken. The engine
    records transitions between stages as PolishRecord entries.
    """
    RAW = "raw"              # present but unworked
    SHAPING = "shaping"      # being given a preliminary form
    REFINING = "refining"    # being polished finer
    POLISHED = "polished"    # holds fineness under normal handling
    LUSTERED = "lustered"    # being given final depth
    FLAWLESS = "flawless"    # no grain can be detected


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TextureReading:
    """One observation of texture on a particular axis.

    ``axis`` is the ``TextureAxis`` the reading is taken on.
    ``texture_score`` in [0, 1] measures how fine the grain is -- 0
    means fully coarse, 1 means fully silken. ``texture_source`` is
    the ``TextureSource`` that produced the texture. ``intensity`` in
    [0, 1] measures how emphatic the observation was. ``notes`` is an
    optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: TextureAxis
    texture_score: float          # 0..1, higher = finer grain
    texture_source: TextureSource
    intensity: float              # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(TextureAxis, self.axis),
            "texture_score": self.texture_score,
            "texture_source": _enum_value(TextureSource, self.texture_source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class RefinementRecord:
    """One refinement event that changed the texture of a structure.

    ``axis`` is the ``TextureAxis`` on which the refinement occurred.
    ``texture_source`` is the ``TextureSource`` that drove the change.
    ``before_score`` in [0, 1] is the texture before the event;
    ``after_score`` in [0, 1] is the texture after. ``refinement_magnitude``
    in [0, infty) measures how large the refinement change was.
    ``notes`` is an optional free-form annotation.
    """
    refinement_id: str
    agent_id: str
    axis: TextureAxis
    texture_source: TextureSource
    before_score: float           # 0..1, texture before refinement
    after_score: float            # 0..1, texture after refinement
    refinement_magnitude: float   # 0..inf, size of the change
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this refinement record to a plain dict, expanding enums via ``.value``."""
        return {
            "refinement_id": self.refinement_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(TextureAxis, self.axis),
            "texture_source": _enum_value(TextureSource, self.texture_source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "refinement_magnitude": self.refinement_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class TextureSnapshot:
    """Aggregate texture state for one agent at one moment.

    ``avg_texture`` in [0, 1] is the mean texture score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is
    the most frequent ``TextureAxis`` among those readings, or
    THOUGHT if none. ``regime`` is derived via ``_determine_regime``
    from ``avg_texture``. ``refinement_count`` is the number of
    refinement events recorded against the agent. ``notes`` is an
    optional free-form annotation.
    """
    snapshot_id: str
    agent_id: str
    avg_texture: float
    dominant_axis: TextureAxis
    regime: TextureRegime
    refinement_count: int
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_texture": self.avg_texture,
            "dominant_axis": _enum_value(TextureAxis, self.dominant_axis),
            "regime": _enum_value(TextureRegime, self.regime),
            "refinement_count": self.refinement_count,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class RefinementPlan:
    """A plan to change the texture of a structure with a strategy.

    ``strategy`` is the ``RefinementStrategy`` chosen. ``target_texture``
    in [0, 1] is the texture the plan aims to reach. ``rationale``
    explains why this strategy was chosen for this structure.
    """
    plan_id: str
    agent_id: str
    strategy: RefinementStrategy
    target_texture: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(RefinementStrategy, self.strategy),
            "target_texture": self.target_texture,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class PolishRecord:
    """One record of a stage transition in the texture lifecycle.

    ``from_stage`` is the ``TextureStage`` the agent's texture was in
    before the transition. ``to_stage`` is the ``TextureStage`` it
    moved to. ``interval_ms`` in [0, infty) is the duration the
    from_stage held before the transition. ``signature`` is a
    free-form label that describes the character of the transition
    (e.g. "slow polish", "sudden luster", "practice-driven shaping").
    """
    polish_id: str
    agent_id: str
    from_stage: TextureStage
    to_stage: TextureStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this polish record to a plain dict, expanding enums via ``.value``."""
        return {
            "polish_id": self.polish_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(TextureStage, self.from_stage),
            "to_stage": _enum_value(TextureStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class TextureProfile:
    """Per-agent aggregate texture tendencies.

    ``avg_texture`` in [0, 1] is the mean texture score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``TextureAxis`` among the agent's readings, or THOUGHT
    if none. ``regime`` is derived via ``_determine_regime`` from
    ``avg_texture``. ``total_readings``, ``total_refinements``, and
    ``total_polishes`` are the counts of each record type for the
    agent.
    """
    agent_id: str
    avg_texture: float = 0.0
    dominant_axis: TextureAxis = TextureAxis.THOUGHT
    regime: TextureRegime = TextureRegime.GRAINY
    total_readings: int = 0
    total_refinements: int = 0
    total_polishes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_texture": self.avg_texture,
            "dominant_axis": _enum_value(TextureAxis, self.dominant_axis),
            "regime": _enum_value(TextureRegime, self.regime),
            "total_readings": self.total_readings,
            "total_refinements": self.total_refinements,
            "total_polishes": self.total_polishes,
        }


@dataclass
class TextureStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_texture`` is the mean texture score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or GRAINY when none
    exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_refinements: int = 0
    total_snapshots: int = 0
    total_polishes: int = 0
    avg_texture: float = 0.0
    dominant_regime: TextureRegime = TextureRegime.GRAINY

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_refinements": self.total_refinements,
            "total_snapshots": self.total_snapshots,
            "total_polishes": self.total_polishes,
            "avg_texture": self.avg_texture,
            "dominant_regime": _enum_value(TextureRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveTexture:
    """Thread-safe engine that models an agent's cognitive texture.

    The engine holds six stores: ``_readings`` (TextureReading lists
    keyed by agent_id), ``_refinements`` (RefinementRecord lists
    keyed by agent_id), ``_snapshots`` (TextureSnapshot lists keyed
    by agent_id), ``_plans`` (a flat list of RefinementPlan),
    ``_polishes`` (PolishRecord lists keyed by agent_id), and
    ``_profiles`` (TextureProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The texture model is deliberately heuristic: texture scores and
    intensities are caller-supplied observations; texture regimes
    are banded from the average texture; dominant axes are computed
    by mode; stage transitions are recorded as observed. These
    heuristics are transparent and auditable rather than learned,
    which keeps the engine deterministic.

    The engine is intentionally agnostic about how texture is measured
    and how stage transitions are detected -- callers may derive them
    from any source. The engine's job is to record, aggregate,
    classify, and profile, not to measure texture itself. Profiles
    are cached per agent and invalidated whenever the agent's
    readings, refinements, snapshots, or polishes change, so
    ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose texture scores feed into a
    # snapshot's average texture. The window is long enough to smooth
    # a single noisy reading and short enough to reflect the agent's
    # current texture posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty texture engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[TextureReading]] = {}
        self._refinements: Dict[str, List[RefinementRecord]] = {}
        self._snapshots: Dict[str, List[TextureSnapshot]] = {}
        self._plans: List[RefinementPlan] = []
        self._polishes: Dict[str, List[PolishRecord]] = {}
        self._profiles: Dict[str, TextureProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_texture_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._refinements.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._polishes.clear()
            self._profiles.clear()

    # -- Internal helpers (callers must already hold the lock) -------

    def _agent_readings_locked(self, agent_id: str) -> List[TextureReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_refinements_locked(
        self, agent_id: str
    ) -> List[RefinementRecord]:
        """Return one agent's refinement records in insertion order. Caller holds the lock."""
        return list(self._refinements.get(agent_id, []))

    def _agent_polishes_locked(
        self, agent_id: str
    ) -> List[PolishRecord]:
        """Return one agent's polish records in insertion order. Caller holds the lock."""
        return list(self._polishes.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[TextureReading]
    ) -> TextureAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns THOUGHT if the list is empty,
        since THOUGHT is the smallest and most neutral axis. Caller
        holds the lock.
        """
        if not readings:
            return TextureAxis.THOUGHT
        counts: Counter = Counter()
        first_seen_order: Dict[TextureAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: TextureAxis = readings[0].axis
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
        self, profiles: List[TextureProfile]
    ) -> TextureRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns GRAINY if the list is empty, since GRAINY is the
        neutral mid-range regime -- neither too coarse nor too fine.
        Caller holds the lock.
        """
        if not profiles:
            return TextureRegime.GRAINY
        counts: Dict[TextureRegime, int] = {}
        for profile in profiles:
            counts[profile.regime] = counts.get(profile.regime, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _current_texture_locked(self, agent_id: str) -> float:
        """Return the agent's most recent texture score, or the mean if none recent.

        Prefers the texture score of the most recent reading, falling
        back to the mean of all readings when there is no clear
        most-recent one. Returns 0.0 when the agent has no readings.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        most_recent = readings[-1]
        return float(most_recent.texture_score)

    def _compute_profile_locked(self, agent_id: str) -> TextureProfile:
        """Aggregate an agent's readings, refinements, and polishes into a profile.

        See ``TextureProfile`` for field semantics. ``avg_texture`` is
        the mean texture score across the agent's readings (0.0 if
        none). ``dominant_axis`` is the most frequent ``TextureAxis``
        among the agent's readings, or THOUGHT if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_texture``.
        ``total_readings``, ``total_refinements``, and ``total_polishes``
        count the records held for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        refinements = self._agent_refinements_locked(agent_id)
        polishes = self._agent_polishes_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_texture = sum(r.texture_score for r in readings) / len(
                readings
            )
        else:
            avg_texture = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        regime = _determine_regime(avg_texture)

        return TextureProfile(
            agent_id=str(agent_id),
            avg_texture=round(avg_texture, 4),
            dominant_axis=dominant_axis,
            regime=regime,
            total_readings=total_readings,
            total_refinements=len(refinements),
            total_polishes=len(polishes),
        )

    # -- Texture Readings --------------------------------------------

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        texture_score: float,
        texture_source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> TextureReading:
        """Record a texture reading for an agent and return it.

        ``axis`` may be passed as a ``TextureAxis`` member or its
        string name/value. ``texture_score`` and ``intensity`` are
        clamped to [0, 1]. ``texture_source`` may be passed as a
        ``TextureSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = TextureReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(TextureAxis, axis),
                texture_score=_clamp(texture_score, 0.0, 1.0),
                texture_source=_resolve_enum(TextureSource, texture_source),
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
    ) -> List[TextureReading]:
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

    def get_reading(self, reading_id: str) -> TextureReading:
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

    # -- Refinement Records ------------------------------------------

    def record_refinement(
        self,
        agent_id: str,
        axis: Any,
        texture_source: Any,
        before_score: float,
        after_score: float,
        refinement_magnitude: float,
        notes: Optional[str] = None,
    ) -> RefinementRecord:
        """Record a refinement event for an agent and return it.

        ``axis`` may be passed as a ``TextureAxis`` member or its
        string name/value. ``texture_source`` may be passed as a
        ``TextureSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``refinement_magnitude`` is clamped to [0, infty). The
        refinement is stored and returned; the agent's cached profile
        is invalidated.
        """
        with self._lock:
            record = RefinementRecord(
                refinement_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(TextureAxis, axis),
                texture_source=_resolve_enum(TextureSource, texture_source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                refinement_magnitude=_clamp_positive_ms(refinement_magnitude),
                timestamp=_now(),
                notes=notes,
            )
            self._refinements.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_refinements(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RefinementRecord]:
        """Return refinement records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all refinements are considered;
        otherwise only refinements for that agent are returned. The
        most recently recorded ``limit`` refinements are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                refinements = self._agent_refinements_locked(agent_id)
            else:
                refinements = []
                for agent_refinements in self._refinements.values():
                    refinements.extend(agent_refinements)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return refinements[-n:] if n else []

    def get_refinement(self, refinement_id: str) -> RefinementRecord:
        """Retrieve a refinement record by id.

        Raises ``ValueError`` if no refinement exists with that id.
        """
        with self._lock:
            for agent_refinements in self._refinements.values():
                for refinement in agent_refinements:
                    if refinement.refinement_id == refinement_id:
                        return refinement
        raise ValueError(f"refinement {refinement_id!r} not found")

    # -- Snapshots ---------------------------------------------------

    def take_snapshot(self, agent_id: str) -> TextureSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_texture`` is the mean texture score across the agent's
        most recent readings (the last ``_SNAPSHOT_READING_WINDOW`` =
        20), or 0.0 if none. ``dominant_axis`` is the most frequent
        ``TextureAxis`` among those readings, or THOUGHT if none.
        ``regime`` is derived via ``_determine_regime`` from
        ``avg_texture``. ``refinement_count`` is the number of
        refinement events recorded against the agent. The snapshot
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_texture = sum(r.texture_score for r in recent) / len(
                    recent
                )
            else:
                avg_texture = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_texture)
            refinement_count = len(self._agent_refinements_locked(agent_id))

            snapshot = TextureSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_texture=round(avg_texture, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                refinement_count=refinement_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TextureSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> TextureSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # -- Refinement Plans --------------------------------------------

    def plan_refinement(
        self,
        agent_id: str,
        strategy: Any,
        target_texture: float,
        rationale: str,
    ) -> RefinementPlan:
        """Record a refinement plan for an agent and return it.

        ``strategy`` may be passed as a ``RefinementStrategy`` member
        or its string name/value. ``target_texture`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured texture.
        """
        with self._lock:
            plan = RefinementPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(RefinementStrategy, strategy),
                target_texture=_clamp(target_texture, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RefinementPlan]:
        """Return refinement plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> RefinementPlan:
        """Retrieve a refinement plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # -- Polish Records ----------------------------------------------

    def record_polish(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> PolishRecord:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``TextureStage`` member or its string name/value.
        ``interval_ms`` in [0, infty) is the duration the from_stage
        held before the transition. ``signature`` is a free-form
        label that describes the character of the transition (e.g.
        "slow polish", "sudden luster", "practice-driven shaping").
        The polish record is stored and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            record = PolishRecord(
                polish_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(TextureStage, from_stage),
                to_stage=_resolve_enum(TextureStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._polishes.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_polishes(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PolishRecord]:
        """Return polish records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all polishes are considered;
        otherwise only polishes for that agent are returned. The most
        recently recorded ``limit`` polish records are returned. The
        returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            if agent_id is not None:
                polishes = self._agent_polishes_locked(agent_id)
            else:
                polishes = []
                for agent_polishes in self._polishes.values():
                    polishes.extend(agent_polishes)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return polishes[-n:] if n else []

    def get_polish(self, polish_id: str) -> PolishRecord:
        """Retrieve a polish record by id.

        Raises ``ValueError`` if no polish record exists with that id.
        """
        with self._lock:
            for agent_polishes in self._polishes.values():
                for record in agent_polishes:
                    if record.polish_id == polish_id:
                        return record
        raise ValueError(f"polish record {polish_id!r} not found")

    # -- Profiles ----------------------------------------------------

    def get_profile(self, agent_id: str) -> TextureProfile:
        """Return the agent's texture profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, refinements, snapshots, or
        polishes change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``TextureProfile``
        and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> TextureProfile:
        """Refresh and optionally override fields of an agent's texture profile.

        The profile is first recomputed from the live stores, then
        any supplied keyword overrides (matching ``TextureProfile``
        field names) are applied. Accepted overrides: ``avg_texture``
        (float), ``dominant_axis`` (``TextureAxis``), ``regime``
        (``TextureRegime``), ``total_readings``, ``total_refinements``,
        ``total_polishes`` (int). Enum-valued overrides may be passed
        as the enum member or its string name/value. Unknown keys
        are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_texture":
                    try:
                        profile.avg_texture = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            TextureAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(
                            TextureRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_refinements",
                    "total_polishes",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[TextureProfile]:
        """Return all stored texture profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # -- Statistics --------------------------------------------------

    def get_stats(self) -> TextureStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with
        any data across readings, refinements, snapshots, and
        polishes. Scalar totals are the counts of each record type.
        ``avg_texture`` is the mean texture score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or GRAINY
        when none exist. When no profiles exist but readings do, the
        dominant regime is derived from the average texture via
        ``_determine_regime`` so the stats always reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._refinements.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._polishes.keys())

            total_readings = 0
            texture_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    texture_sum += reading.texture_score
            avg_texture = (
                round(texture_sum / total_readings, 4) if total_readings else 0.0
            )

            total_refinements = sum(
                len(agent_refinements)
                for agent_refinements in self._refinements.values()
            )
            total_snapshots = sum(
                len(agent_snapshots)
                for agent_snapshots in self._snapshots.values()
            )
            total_polishes = sum(
                len(agent_polishes) for agent_polishes in self._polishes.values()
            )

            profiles = list(self._profiles.values())
            if profiles:
                dominant_regime = self._mode_regime_locked(profiles)
            elif total_readings:
                # No profiles cached yet, but readings exist: derive
                # the regime from the average texture so the stats
                # reflect real state rather than the default GRAINY.
                dominant_regime = _determine_regime(avg_texture)
            else:
                dominant_regime = TextureRegime.GRAINY

            return TextureStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_refinements=total_refinements,
                total_snapshots=total_snapshots,
                total_polishes=total_polishes,
                avg_texture=avg_texture,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveTexture] = None
_engine_lock = threading.Lock()


def get_texture_engine() -> AgentCognitiveTexture:
    """Get or create the singleton ``AgentCognitiveTexture`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveTexture()
    return _engine


def reset_texture_engine() -> None:
    """Reset the singleton ``AgentCognitiveTexture`` instance.

    Drops the reference to the current engine so the next
    ``get_texture_engine`` call creates a fresh instance. Useful for
    tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
