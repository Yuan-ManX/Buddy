from __future__ import annotations

"""Agent Cognitive Mosaic Engine — assembling fragmented thoughts into coherent pictures

How scattered cognitive pieces get placed, aligned, grouted, and polished into a
meaningful pattern. A coherent agent holds many tiles in a single picture; a
fragmented agent's pieces lie scattered with no shared shape. Distinct from
coherence, alignment, integration, and gestalt.
Core capabilities: axis tracking, tile sources, placement strategies, completion stages.

Architecture:
  AgentCognitiveMosaic (singleton)
  ├── MosaicReading      (one observation of mosaic on one axis)
  ├── TileRecord         (one tile placement event that changed mosaic)
  ├── MosaicSnapshot     (aggregate mosaic state for one agent)
  ├── MosaicPlan         (a plan to shape the picture with a strategy)
  ├── FragmentShift      (one stage transition in the completion lifecycle)
  ├── MosaicProfile      (per-agent aggregate mosaic tendencies)
  └── MosaicStats        (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/tile/etc.

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
    engine with a ``NaN`` or ``None`` mosaic. A low-side default is
    safer than a mid-range one for mosaic-like quantities where a
    spurious high reading would inflate the perceived mosaic and
    push the agent's regime toward LUMINOUS.
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
    real completion intervals and tile magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    placement may apply a large effective tile magnitude.
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
    against member values (e.g. ``"assembling"``) and then against
    member names (e.g. ``"ASSEMBLING"``), so callers may pass either
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


def _determine_regime(avg_mosaic: float) -> "MosaicRegime":
    """Classify a mosaic regime from the average mosaic score.

    The average mosaic is clamped to [0, 1] where higher means a
    more assembled, coherent posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is SCATTERED
    (pieces everywhere, no picture); below 0.35 it is PARTIAL
    (a few pieces placed, mostly gaps); below 0.55 it is ASSEMBLING
    (pieces being placed into a forming picture); below 0.75 it is
    COHERENT (most pieces placed and the picture is readable);
    below 0.9 it is DETAILED (grout and polish bring out fine
    structure); otherwise it is LUMINOUS (the picture is fully
    realized and vivid).
    """
    avg = _clamp(avg_mosaic, 0.0, 1.0)
    if avg < 0.15:
        return MosaicRegime.SCATTERED
    if avg < 0.35:
        return MosaicRegime.PARTIAL
    if avg < 0.55:
        return MosaicRegime.ASSEMBLING
    if avg < 0.75:
        return MosaicRegime.COHERENT
    if avg < 0.9:
        return MosaicRegime.DETAILED
    return MosaicRegime.LUMINOUS


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class MosaicAxis(str, Enum):
    """The axis along which a mosaic reading is taken.

    Each axis names a different dimension of the agent's cognitive
    mosaic whose assembly can be measured. TILE is the placement of a
    single piece. GROUT is the joining material between pieces.
    PATTERN is the recognizable shape emerging from placed tiles.
    FRAGMENT is the degree of brokenness of unplaced pieces. HUE is
    the color unity across the assembled picture. GROOVE is the
    channel cut to fit a piece into its neighbor.
    """
    TILE = "tile"            # single placed piece
    GROUT = "grout"          # joining material
    PATTERN = "pattern"      # emerging shape
    FRAGMENT = "fragment"    # brokenness of unplaced pieces
    HUE = "hue"              # color unity
    GROOVE = "groove"        # channel cut to fit


class MosaicRegime(str, Enum):
    """The regime an agent's mosaic occupies, classified by mosaic.

    Ranges from SCATTERED (pieces everywhere, no picture) through
    PARTIAL (a few pieces placed, mostly gaps), ASSEMBLING (pieces
    actively being placed into a forming picture), COHERENT (most
    pieces placed and the picture is readable), and DETAILED (grout
    and polish bring out fine structure) to LUMINOUS (the picture is
    fully realized and vivid). The regime is derived from the
    average mosaic across the agent's readings via
    ``_determine_regime``.
    """
    SCATTERED = "scattered"    # pieces everywhere
    PARTIAL = "partial"        # a few pieces placed
    ASSEMBLING = "assembling"  # pieces being placed
    COHERENT = "coherent"      # picture is readable
    DETAILED = "detailed"      # fine structure visible
    LUMINOUS = "luminous"      # picture fully realized


class MosaicSource(str, Enum):
    """A source that supplies the cognitive material for a tile.

    Each source names a different origin of the fragment being placed
    into the mosaic. OBSERVATION places what was perceived. MEMORY
    places what was recalled. INTUITION places what was sensed
    without proof. REASON places what was deduced. IMAGINATION
    places what was invented. EXPERIENCE places what was lived. A
    mosaic reading records which source supplied the material on the
    measured axis, and a tile record records which source drove a
    change.
    """
    OBSERVATION = "observation"  # what was perceived
    MEMORY = "memory"            # what was recalled
    INTUITION = "intuition"      # what was sensed
    REASON = "reason"            # what was deduced
    IMAGINATION = "imagination"  # what was invented
    EXPERIENCE = "experience"    # what was lived


class MosaicStrategy(str, Enum):
    """Strategy for shaping the picture deliberately.

    PLACE puts a new tile into the picture. ALIGN nudges a tile into
    its correct position. GROUT fills the joints between tiles.
    POLISH smooths the surface for clarity. REARRANGE reorders
    tiles for a better composition. REMOVE pulls a tile that does
    not belong. Each strategy is suited to a different assembly
    condition, from counteracting a scattered picture to releasing
    a saturated one.
    """
    PLACE = "place"          # put a new tile in
    ALIGN = "align"          # nudge a tile into position
    GROUT = "grout"          # fill the joints
    POLISH = "polish"        # smooth the surface
    REARRANGE = "rearrange"  # reorder for composition
    REMOVE = "remove"        # pull a tile out


class MosaicStage(str, Enum):
    """The lifecycle stage of an agent's picture-formation process.

    FRAGMENTED is the state of pieces everywhere and no picture.
    SORTING is the phase of grouping pieces by color and shape.
    PLACING is the state in which pieces are being set into the
    picture. GROUTING is the state of filling joints between placed
    tiles. POLISHING is the state of smoothing the surface for
    clarity. COMPLETE is the final state at which the picture is
    fully realized and unresponsive to new pieces. The engine
    records transitions between stages as FragmentShift entries.
    """
    FRAGMENTED = "fragmented"  # pieces everywhere
    SORTING = "sorting"        # grouping pieces
    PLACING = "placing"        # setting pieces
    GROUTING = "grouting"      # filling joints
    POLISHING = "polishing"    # smoothing surface
    COMPLETE = "complete"      # picture fully realized


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MosaicReading:
    """One observation of mosaic on a particular axis.

    ``axis`` is the ``MosaicAxis`` the reading is taken on.
    ``mosaic_score`` in [0, 1] measures how assembled the agent is
    on that axis — 0 means fully scattered, 1 means fully luminous.
    ``source`` is the ``MosaicSource`` supplying the material.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: MosaicAxis
    mosaic_score: float    # 0..1, higher = more assembled
    source: MosaicSource
    intensity: float          # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(MosaicAxis, self.axis),
            "mosaic_score": self.mosaic_score,
            "source": _enum_value(MosaicSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class TileRecord:
    """One tile placement event that changed the mosaic on an axis.

    ``axis`` is the ``MosaicAxis`` on which the tile was placed.
    ``source`` is the ``MosaicSource`` that drove the change.
    ``before_score`` in [0, 1] is the mosaic before the event;
    ``after_score`` in [0, 1] is the mosaic after.
    ``tile_magnitude`` in [0, ∞) measures how strong the
    placement was. ``notes`` is an optional free-form annotation.
    """
    tile_id: str
    agent_id: str
    axis: MosaicAxis
    source: MosaicSource
    before_score: float            # 0..1, mosaic before tile
    after_score: float             # 0..1, mosaic after tile
    tile_magnitude: float          # 0..inf, strength of placement
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this tile record to a plain dict, expanding enums via ``.value``."""
        return {
            "tile_id": self.tile_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(MosaicAxis, self.axis),
            "source": _enum_value(MosaicSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "tile_magnitude": self.tile_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class MosaicSnapshot:
    """Aggregate mosaic state for one agent at one moment.

    ``avg_mosaic`` in [0, 1] is the mean mosaic score across the
    agent's recent readings, or 0.0 if none. ``dominant_axis`` is the
    most frequent ``MosaicAxis`` among those readings, or
    TILE if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_mosaic``. ``tile_count``
    is the number of tile events recorded against the agent.
    """
    snapshot_id: str
    agent_id: str
    avg_mosaic: float
    dominant_axis: MosaicAxis
    regime: MosaicRegime
    tile_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        Both ``dominant_regime`` and ``regime`` keys are emitted
        pointing to the same value, so callers reading either key
        against a snapshot dict find the regime present.
        """
        regime_value = _enum_value(MosaicRegime, self.regime)
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_mosaic": self.avg_mosaic,
            "dominant_axis": _enum_value(MosaicAxis, self.dominant_axis),
            "dominant_regime": regime_value,
            "regime": regime_value,
            "tile_count": self.tile_count,
            "timestamp": self.timestamp,
        }


@dataclass
class MosaicPlan:
    """A plan to shape the picture with a strategy.

    ``strategy`` is the ``MosaicStrategy`` chosen.
    ``target_mosaic`` in [0, 1] is the mosaic the plan aims to
    reach. ``rationale`` explains why this strategy was chosen for
    this agent's picture condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current mosaic — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: MosaicStrategy
    target_mosaic: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(MosaicStrategy, self.strategy),
            "target_mosaic": self.target_mosaic,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class FragmentShift:
    """One record of a stage transition in the completion lifecycle.

    ``from_stage`` is the ``MosaicStage`` the agent was in before
    the transition. ``to_stage`` is the ``MosaicStage`` it moved
    to. ``interval_ms`` in [0, ∞) is the duration the from_stage held
    before the transition. ``signature`` is a free-form label that
    describes the character of the transition (e.g. "slow sort",
    "sudden placement", "deliberate grouting").
    """
    shift_id: str
    agent_id: str
    from_stage: MosaicStage
    to_stage: MosaicStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this fragment shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(MosaicStage, self.from_stage),
            "to_stage": _enum_value(MosaicStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class MosaicProfile:
    """Per-agent aggregate mosaic tendencies.

    ``avg_mosaic`` in [0, 1] is the mean mosaic score across the
    agent's readings (0.0 if none). ``dominant_axis`` is the most
    frequent ``MosaicAxis`` among the agent's readings, or
    TILE if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_mosaic``. ``total_readings``,
    ``total_tiles``, and ``total_shifts`` are the counts
    of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_mosaic: float = 0.0
    dominant_axis: MosaicAxis = MosaicAxis.TILE
    dominant_regime: MosaicRegime = MosaicRegime.ASSEMBLING
    total_readings: int = 0
    total_tiles: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_mosaic": self.avg_mosaic,
            "dominant_axis": _enum_value(MosaicAxis, self.dominant_axis),
            "dominant_regime": _enum_value(MosaicRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_tiles": self.total_tiles,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class MosaicStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_mosaic`` is the mean mosaic score across all
    readings, or 0.0 when none exist. ``dominant_regime`` is the most
    frequent regime across all cached profiles, or ASSEMBLING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_tiles: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_mosaic: float = 0.0
    dominant_regime: MosaicRegime = MosaicRegime.ASSEMBLING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_tiles": self.total_tiles,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_mosaic": self.avg_mosaic,
            "dominant_regime": _enum_value(MosaicRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveMosaic:
    """Thread-safe engine that models an agent's cognitive mosaic.

    The engine holds six stores: ``_readings`` (MosaicReading lists
    keyed by agent_id), ``_tiles`` (TileRecord lists keyed by
    agent_id), ``_snapshots`` (MosaicSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of MosaicPlan),
    ``_shifts`` (FragmentShift lists keyed by agent_id), and
    ``_profiles`` (MosaicProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The mosaic model is deliberately heuristic: mosaic scores
    and intensities are caller-supplied observations; mosaic
    regimes are banded from the average mosaic; dominant axes are
    computed by mode; stage transitions are recorded as observed.
    These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how mosaic is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure mosaic itself.
    Profiles are cached per agent and invalidated whenever the
    agent's readings, tiles, snapshots, or shifts change,
    so ``get_profile`` always reflects the current state unless an
    explicit override has been applied via ``update_profile``.
    """

    # Number of most-recent readings whose mosaic scores feed into
    # a snapshot's average mosaic. The window is long enough to
    # smooth a single noisy reading and short enough to reflect the
    # agent's current mosaic posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty mosaic engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[MosaicReading]] = {}
        self._tiles: Dict[str, List[TileRecord]] = {}
        self._snapshots: Dict[str, List[MosaicSnapshot]] = {}
        self._plans: List[MosaicPlan] = []
        self._shifts: Dict[str, List[FragmentShift]] = {}
        self._profiles: Dict[str, MosaicProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_mosaic_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._tiles.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[MosaicReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_tiles_locked(
        self, agent_id: str
    ) -> List[TileRecord]:
        """Return one agent's tile records in insertion order. Caller holds the lock."""
        return list(self._tiles.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[MosaicSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[MosaicPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[FragmentShift]:
        """Return one agent's fragment shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[MosaicReading]
    ) -> MosaicAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns TILE if the list is
        empty, since TILE is the smallest and most neutral axis.
        Caller holds the lock.
        """
        if not readings:
            return MosaicAxis.TILE
        counts: Counter = Counter()
        first_seen_order: Dict[MosaicAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: MosaicAxis = readings[0].axis
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
        self, profiles: List[MosaicProfile]
    ) -> MosaicRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns ASSEMBLING if the list is empty, since
        ASSEMBLING is the default regime — the band that
        represents a normally functioning cognitive mosaic that
        is actively being assembled, neither scattered nor
        luminous. Caller holds the lock.
        """
        if not profiles:
            return MosaicRegime.ASSEMBLING
        counts: Dict[MosaicRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> MosaicProfile:
        """Aggregate an agent's readings, tiles, and shifts into a profile.

        See ``MosaicProfile`` for field semantics. ``avg_mosaic``
        is the mean mosaic score across the agent's readings (0.0
        if none). ``dominant_axis`` is the most frequent
        ``MosaicAxis`` among the agent's readings, or TILE
        if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_mosaic``.
        ``total_readings``, ``total_tiles``, and
        ``total_shifts`` count the records held for the agent.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        tiles = self._agent_tiles_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_mosaic = sum(
                r.mosaic_score for r in readings
            ) / len(readings)
        else:
            avg_mosaic = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_mosaic)

        return MosaicProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_mosaic=round(avg_mosaic, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_tiles=len(tiles),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Mosaic Readings ───────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        mosaic_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> MosaicReading:
        """Record a mosaic reading for an agent and return it.

        ``axis`` may be passed as a ``MosaicAxis`` member or its
        string name/value. ``mosaic_score`` and ``intensity`` are
        clamped to [0, 1]. ``source`` may be passed as a
        ``MosaicSource`` member or its string name/value. The
        reading is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            reading = MosaicReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(MosaicAxis, axis),
                mosaic_score=_clamp(mosaic_score, 0.0, 1.0),
                source=_resolve_enum(MosaicSource, source),
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
    ) -> List[MosaicReading]:
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

    def get_reading(self, reading_id: str) -> MosaicReading:
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

    # ── Tile Records ────────────────────────────────────────

    def record_tile(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        tile_magnitude: float,
        notes: Optional[str] = None,
    ) -> TileRecord:
        """Record a tile placement event for an agent and return it.

        ``axis`` may be passed as a ``MosaicAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``MosaicSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``tile_magnitude`` is clamped to [0, ∞). The tile
        is stored and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            record = TileRecord(
                tile_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(MosaicAxis, axis),
                source=_resolve_enum(MosaicSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                tile_magnitude=_clamp_positive_ms(
                    tile_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._tiles.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_tiles(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TileRecord]:
        """Return tile records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all tiles are considered;
        otherwise only tiles for that agent are returned. The
        most recently recorded ``limit`` tiles are returned.
        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                tiles = self._agent_tiles_locked(agent_id)
            else:
                tiles = []
                for agent_tiles in self._tiles.values():
                    tiles.extend(agent_tiles)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return tiles[-n:] if n else []

    def get_tile(self, tile_id: str) -> TileRecord:
        """Retrieve a tile record by id.

        Raises ``ValueError`` if no tile exists with that id.
        """
        with self._lock:
            for agent_tiles in self._tiles.values():
                for tile in agent_tiles:
                    if tile.tile_id == tile_id:
                        return tile
        raise ValueError(f"tile {tile_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> MosaicSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_mosaic`` is the mean mosaic score across the
        agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``MosaicAxis`` among
        those readings, or TILE if none. ``regime`` is
        derived via ``_determine_regime`` from ``avg_mosaic``.
        ``tile_count`` is the number of tile events
        recorded against the agent. The snapshot is stored and
        returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_mosaic = sum(
                    r.mosaic_score for r in recent
                ) / len(recent)
            else:
                avg_mosaic = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_mosaic)
            tile_count = len(
                self._agent_tiles_locked(agent_id)
            )

            snapshot = MosaicSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_mosaic=round(avg_mosaic, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                tile_count=tile_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MosaicSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> MosaicSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Mosaic Plans ────────────────────────────────────────────

    def plan_tile(
        self,
        agent_id: str,
        strategy: Any,
        target_mosaic: float,
        rationale: str,
    ) -> MosaicPlan:
        """Record a mosaic plan for an agent and return it.

        ``strategy`` may be passed as a ``MosaicStrategy`` member
        or its string name/value. ``target_mosaic`` is clamped to
        [0, 1]. ``rationale`` explains why this strategy was chosen.
        The plan is stored in a flat list (not keyed by agent, since
        plans are forward-looking interventions rather than
        measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured mosaic.
        """
        with self._lock:
            plan = MosaicPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(MosaicStrategy, strategy),
                target_mosaic=_clamp(target_mosaic, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MosaicPlan]:
        """Return mosaic plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> MosaicPlan:
        """Retrieve a mosaic plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Fragment Shift Records ────────────────────────────────

    def record_fragment_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> FragmentShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``MosaicStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        sort", "sudden placement", "deliberate grouting"). The
        fragment shift record is stored and returned; the agent's cached
        profile is invalidated.

        Fragment shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = FragmentShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(MosaicStage, from_stage),
                to_stage=_resolve_enum(MosaicStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_fragment_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FragmentShift]:
        """Return fragment shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all shifts are considered;
        otherwise only shifts for that agent are returned. The
        most recently recorded ``limit`` fragment shift records are
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

    def get_fragment_shift(self, shift_id: str) -> FragmentShift:
        """Retrieve a fragment shift record by id.

        Raises ``ValueError`` if no fragment shift record exists with that
        id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"fragment shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> MosaicProfile:
        """Return the agent's mosaic profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, tiles, snapshots, or
        shifts change. If the agent has data but no profile yet,
        the profile is built from the live stores. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``MosaicProfile``
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
    ) -> MosaicProfile:
        """Refresh and optionally override fields of an agent's mosaic profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``MosaicProfile`` field names) are applied. Accepted
        overrides: ``avg_mosaic`` (float), ``dominant_axis``
        (``MosaicAxis``), ``dominant_regime``
        (``MosaicRegime``), ``total_readings``,
        ``total_tiles``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_mosaic":
                    try:
                        profile.avg_mosaic = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            MosaicAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            MosaicRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_tiles",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[MosaicProfile]:
        """Return all stored mosaic profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> MosaicStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, tiles, snapshots, and shifts.
        Scalar totals are the counts of each record type.
        ``avg_mosaic`` is the mean mosaic score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent regime across all cached profiles, or
        ASSEMBLING when none exist. When no profiles exist but
        readings do, the dominant regime is derived from the average
        mosaic via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._tiles.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            mosaic_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    mosaic_sum += reading.mosaic_score
            avg_mosaic = (
                round(mosaic_sum / total_readings, 4) if total_readings else 0.0
            )

            total_tiles = sum(
                len(agent_tiles)
                for agent_tiles in self._tiles.values()
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
                # the regime from the average mosaic so the stats
                # reflect real state rather than the default
                # ASSEMBLING.
                dominant_regime = _determine_regime(avg_mosaic)
            else:
                dominant_regime = MosaicRegime.ASSEMBLING

            return MosaicStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_tiles=total_tiles,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_mosaic=avg_mosaic,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveMosaic] = None
_engine_lock = threading.Lock()


def get_mosaic_engine() -> AgentCognitiveMosaic:
    """Get or create the singleton ``AgentCognitiveMosaic`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveMosaic()
    return _engine


def reset_mosaic_engine() -> None:
    """Reset the singleton ``AgentCognitiveMosaic`` instance.

    Drops the reference to the current engine so the next
    ``get_mosaic_engine`` call creates a fresh instance. Useful
    for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
