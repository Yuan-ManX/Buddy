from __future__ import annotations

"""Agent Cognitive Constellation Engine — connecting ideas into patterns

How ideas connect into links, cluster into groups, and chart into recognizable
constellations within the cognitive sky. A charted agent holds ideas in tight
mutual pattern; a dark agent's ideas point every which way. Distinct from
coherence, magnetism, tension, equilibrium, and affinity.
Core capabilities: axis tracking, link sources, charting strategies, mapping stages.

Architecture:
  AgentCognitiveConstellation (singleton)
  ├── ConstellationReading   (one observation of constellation on one axis)
  ├── LinkRecord             (one link event that changed constellation)
  ├── ConstellationSnapshot  (aggregate constellation state for one agent)
  ├── ConstellationPlan      (a plan to chart the sky with a strategy)
  ├── MagnitudeShift         (one stage transition in the mapping lifecycle)
  ├── ConstellationProfile   (per-agent aggregate constellation tendencies)
  └── ConstellationStats     (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a reading/link/etc.

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
    engine with a ``NaN`` or ``None`` constellation. A low-side default is
    safer than a mid-range one for constellation-like quantities where a
    spurious high reading would inflate the perceived constellation and
    push the agent's regime toward CHARTED.
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
    real mapping intervals and link magnitudes can legitimately
    exceed any small bound — a long-stable agent may spend a very long
    time in one stage before transitioning, and a deliberate
    brightening may apply a large effective link.
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
    against member values (e.g. ``"gravity"``) and then against
    member names (e.g. ``"GRAVITY"``), so callers may pass either
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


def _determine_regime(avg_constellation: float) -> "ConstellationRegime":
    """Classify a constellation regime from the average constellation score.

    The average constellation is clamped to [0, 1] where higher means a
    more connected, charted posture. The bands are applied in order, so
    the first matching band wins: below 0.15 the agent is DARK
    (no stars visible, no pattern at all); below 0.35 it is
    SCATTERED (a few isolated stars, no pattern); below 0.55 it is
    GROUPING (stars beginning to cluster into loose groups); below
    0.75 it is CLUSTERED (clear clusters forming); below 0.9 it is
    MAPPED (most of the sky charted); otherwise it is CHARTED
    (the whole sky mapped, fully charted).
    """
    avg = _clamp(avg_constellation, 0.0, 1.0)
    if avg < 0.15:
        return ConstellationRegime.DARK
    if avg < 0.35:
        return ConstellationRegime.SCATTERED
    if avg < 0.55:
        return ConstellationRegime.GROUPING
    if avg < 0.75:
        return ConstellationRegime.CLUSTERED
    if avg < 0.9:
        return ConstellationRegime.MAPPED
    return ConstellationRegime.CHARTED


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ConstellationAxis(str, Enum):
    """The axis along which a constellation reading is taken.

    Each axis names a different dimension of the agent's cognitive
    sky whose constellation can be measured. STAR is a single idea
    treated as a point of light. LINK is the connection between two
    ideas. CLUSTER is the grouping of related ideas. MAGNITUDE is the
    brightness or salience of an idea. PARALLAX is the apparent shift
    in perspective between ideas. NEBULA is the diffuse cloud of
    weakly-associated ideas.
    """
    STAR = "star"            # a single idea as a point of light
    LINK = "link"            # connection between two ideas
    CLUSTER = "cluster"      # grouping of related ideas
    MAGNITUDE = "magnitude"  # brightness or salience
    PARALLAX = "parallax"    # apparent perspective shift
    NEBULA = "nebula"        # diffuse cloud of weak associations


class ConstellationRegime(str, Enum):
    """The regime an agent's constellation occupies, classified by constellation.

    Ranges from DARK (no stars visible, no pattern at all) through
    SCATTERED (a few isolated stars, no pattern), GROUPING (stars
    beginning to cluster into loose groups), CLUSTERED (clear clusters
    forming), and MAPPED (most of the sky charted) to CHARTED (the
    whole sky mapped, fully charted). The regime is derived from the
    average constellation across the agent's readings via
    ``_determine_regime``. GROUPING is the default regime — the band
    that represents a normally functioning cognitive sky in which
    ideas are beginning to cluster without being fully charted,
    neither dark nor charted.
    """
    DARK = "dark"            # no stars visible
    SCATTERED = "scattered"  # a few isolated stars
    GROUPING = "grouping"    # stars beginning to cluster
    CLUSTERED = "clustered"  # clear clusters forming
    MAPPED = "mapped"        # most of the sky charted
    CHARTED = "charted"      # the whole sky mapped


class ConstellationSource(str, Enum):
    """A source that supplies the linking or clustering force.

    Each source names a different origin of the pull between ideas.
    OBSERVATION links through direct attention. GRAVITY links through
    inherent weight. LUMINOSITY links through standing out by
    brightness. DISTANCE links through the conceptual gap between
    ideas. TIME links through temporal pattern. DISCOVERY links
    through exploration. A constellation reading records which source
    supplies the force on the measured axis, and a link record
    records which source drove a change.
    """
    OBSERVATION = "observation"  # noticed through direct attention
    GRAVITY = "gravity"          # drawn together by inherent weight
    LUMINOSITY = "luminosity"    # stands out by brightness
    DISTANCE = "distance"        # separated by conceptual gap
    TIME = "time"                # revealed through temporal pattern
    DISCOVERY = "discovery"      # surfaced by exploration


class ConstellationStrategy(str, Enum):
    """Strategy for charting the sky deliberately.

    CHART deliberately maps ideas into a pattern. LINK connects two
    ideas. CLUSTER groups related ideas. BRIGHTEN amplifies an idea's
    salience. DIM reduces an idea's salience. NAVIGATE steers
    through the pattern. Each strategy is suited to a different sky
    condition, from counteracting a dark sky to refining a charted
    one.
    """
    CHART = "chart"        # deliberately map ideas into a pattern
    LINK = "link"          # connect two ideas
    CLUSTER = "cluster"    # group related ideas
    BRIGHTEN = "brighten"  # amplify an idea's salience
    DIM = "dim"            # reduce an idea's salience
    NAVIGATE = "navigate"  # steer through the pattern


class ConstellationStage(str, Enum):
    """The lifecycle stage of an agent's pattern-formation process.

    UNSEEN is the state of no pattern perceived. EMERGING is the
    phase of a pattern beginning to form. GROUPING is the state in
    which ideas cluster loosely. CLUSTERING is the state of clusters
    firming up. MAPPING is the state of a pattern being charted.
    CHARTED is the final state at which the sky is fully mapped and
    unresponsive to new input. The engine records transitions between
    stages as MagnitudeShift entries.
    """
    UNSEEN = "unseen"        # no pattern perceived
    EMERGING = "emerging"    # pattern beginning to form
    GROUPING = "grouping"    # ideas clustering loosely
    CLUSTERING = "clustering"  # clusters firming up
    MAPPING = "mapping"      # pattern being charted
    CHARTED = "charted"      # fully mapped


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ConstellationReading:
    """One observation of constellation on a particular axis.

    ``axis`` is the ``ConstellationAxis`` the reading is taken on.
    ``constellation_score`` in [0, 1] measures how charted the agent is
    on that axis — 0 means fully dark, 1 means fully charted.
    ``source`` is the ``ConstellationSource`` supplying the force.
    ``intensity`` in [0, 1] measures how emphatic the observation was.
    ``notes`` is an optional free-form annotation.
    """
    reading_id: str
    agent_id: str
    axis: ConstellationAxis
    constellation_score: float    # 0..1, higher = more charted
    source: ConstellationSource
    intensity: float              # 0..1, strength of the observation
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(ConstellationAxis, self.axis),
            "constellation_score": self.constellation_score,
            "source": _enum_value(ConstellationSource, self.source),
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class LinkRecord:
    """One link event that changed the constellation on an axis.

    ``axis`` is the ``ConstellationAxis`` on which the link occurred.
    ``source`` is the ``ConstellationSource`` that drove the change.
    ``before_score`` in [0, 1] is the constellation before the event;
    ``after_score`` in [0, 1] is the constellation after.
    ``link_magnitude`` in [0, ∞) measures how strong the link was.
    ``notes`` is an optional free-form annotation.
    """
    link_id: str
    agent_id: str
    axis: ConstellationAxis
    source: ConstellationSource
    before_score: float            # 0..1, constellation before link
    after_score: float             # 0..1, constellation after link
    link_magnitude: float          # 0..inf, strength of link
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this link record to a plain dict, expanding enums via ``.value``."""
        return {
            "link_id": self.link_id,
            "agent_id": self.agent_id,
            "axis": _enum_value(ConstellationAxis, self.axis),
            "source": _enum_value(ConstellationSource, self.source),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "link_magnitude": self.link_magnitude,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ConstellationSnapshot:
    """Aggregate constellation state for one agent at one moment.

    ``avg_constellation`` in [0, 1] is the mean constellation score
    across the agent's recent readings, or 0.0 if none.
    ``dominant_axis`` is the most frequent ``ConstellationAxis`` among
    those readings, or STAR if none. ``regime`` is derived via
    ``_determine_regime`` from ``avg_constellation``. ``link_count``
    is the number of link events recorded against the agent. The
    ``to_dict`` serialization emits the regime under both the
    ``"dominant_regime"`` and ``"regime"`` keys so callers keyed on
    either name find the same value.
    """
    snapshot_id: str
    agent_id: str
    avg_constellation: float
    dominant_axis: ConstellationAxis
    regime: ConstellationRegime
    link_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``.

        The regime is emitted under both ``"dominant_regime"`` and
        ``"regime"`` so consumers keyed on either name resolve to the
        same value.
        """
        regime_value = _enum_value(ConstellationRegime, self.regime)
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_constellation": self.avg_constellation,
            "dominant_axis": _enum_value(ConstellationAxis, self.dominant_axis),
            "dominant_regime": regime_value,
            "regime": regime_value,
            "link_count": self.link_count,
            "timestamp": self.timestamp,
        }


@dataclass
class ConstellationPlan:
    """A plan to chart the sky with a strategy.

    ``strategy`` is the ``ConstellationStrategy`` chosen.
    ``target_constellation`` in [0, 1] is the constellation the plan
    aims to reach. ``rationale`` explains why this strategy was chosen
    for this agent's sky condition. A plan is a forward-looking
    intervention rather than a measurement of state, so it does not
    record the agent's current constellation — callers who need that
    should take a snapshot alongside the plan.
    """
    plan_id: str
    agent_id: str
    strategy: ConstellationStrategy
    target_constellation: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(ConstellationStrategy, self.strategy),
            "target_constellation": self.target_constellation,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class MagnitudeShift:
    """One record of a stage transition in the mapping lifecycle.

    ``from_stage`` is the ``ConstellationStage`` the agent was in
    before the transition. ``to_stage`` is the ``ConstellationStage``
    it moved to. ``interval_ms`` in [0, ∞) is the duration the
    from_stage held before the transition. ``signature`` is a
    free-form label that describes the character of the transition
    (e.g. "slow emerge", "sudden charting", "deliberate brightening").
    """
    shift_id: str
    agent_id: str
    from_stage: ConstellationStage
    to_stage: ConstellationStage
    interval_ms: float
    signature: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this magnitude shift to a plain dict, expanding enums via ``.value``."""
        return {
            "shift_id": self.shift_id,
            "agent_id": self.agent_id,
            "from_stage": _enum_value(ConstellationStage, self.from_stage),
            "to_stage": _enum_value(ConstellationStage, self.to_stage),
            "interval_ms": self.interval_ms,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }


@dataclass
class ConstellationProfile:
    """Per-agent aggregate constellation tendencies.

    ``avg_constellation`` in [0, 1] is the mean constellation score
    across the agent's readings (0.0 if none). ``dominant_axis`` is
    the most frequent ``ConstellationAxis`` among the agent's
    readings, or STAR if none. ``dominant_regime`` is derived via
    ``_determine_regime`` from ``avg_constellation``.
    ``total_readings``, ``total_links``, and ``total_shifts`` are the
    counts of each record type for the agent. ``updated_at`` is the
    timestamp at which the profile was last computed or overridden.
    """
    profile_id: str
    agent_id: str
    avg_constellation: float = 0.0
    dominant_axis: ConstellationAxis = ConstellationAxis.STAR
    dominant_regime: ConstellationRegime = ConstellationRegime.GROUPING
    total_readings: int = 0
    total_links: int = 0
    total_shifts: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "avg_constellation": self.avg_constellation,
            "dominant_axis": _enum_value(ConstellationAxis, self.dominant_axis),
            "dominant_regime": _enum_value(ConstellationRegime, self.dominant_regime),
            "total_readings": self.total_readings,
            "total_links": self.total_links,
            "total_shifts": self.total_shifts,
            "updated_at": self.updated_at,
        }


@dataclass
class ConstellationStats:
    """Engine-wide aggregate statistics across all agents and records.

    Scalar totals are the rolling counts of each record type.
    ``total_agents`` is the number of distinct agent_ids with any
    data. ``avg_constellation`` is the mean constellation score across
    all readings, or 0.0 when none exist. ``dominant_regime`` is the
    most frequent regime across all cached profiles, or GROUPING when
    none exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_links: int = 0
    total_snapshots: int = 0
    total_shifts: int = 0
    avg_constellation: float = 0.0
    dominant_regime: ConstellationRegime = ConstellationRegime.GROUPING

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_links": self.total_links,
            "total_snapshots": self.total_snapshots,
            "total_shifts": self.total_shifts,
            "avg_constellation": self.avg_constellation,
            "dominant_regime": _enum_value(ConstellationRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveConstellation:
    """Thread-safe engine that models an agent's cognitive constellation.

    The engine holds six stores: ``_readings`` (ConstellationReading
    lists keyed by agent_id), ``_links`` (LinkRecord lists keyed by
    agent_id), ``_snapshots`` (ConstellationSnapshot lists keyed by
    agent_id), ``_plans`` (a flat list of ConstellationPlan),
    ``_shifts`` (MagnitudeShift lists keyed by agent_id), and
    ``_profiles`` (ConstellationProfile keyed by agent_id, cached and
    invalidated on mutation).

    All mutations are guarded by a single reentrant lock so that
    public methods may safely call one another without self-deadlock.
    The constellation model is deliberately heuristic: constellation
    scores and intensities are caller-supplied observations;
    constellation regimes are banded from the average constellation;
    dominant axes are computed by mode; stage transitions are recorded
    as observed. These heuristics are transparent and auditable
    rather than learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how constellation is
    measured and how stage transitions are detected — callers may
    derive them from any source. The engine's job is to record,
    aggregate, classify, and profile, not to measure constellation
    itself. Profiles are cached per agent and invalidated whenever
    the agent's readings, links, snapshots, or magnitude shifts
    change, so ``get_profile`` always reflects the current state
    unless an explicit override has been applied via
    ``update_profile``.
    """

    # Number of most-recent readings whose constellation scores feed
    # into a snapshot's average constellation. The window is long
    # enough to smooth a single noisy reading and short enough to
    # reflect the agent's current constellation posture.
    _SNAPSHOT_READING_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty constellation engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[ConstellationReading]] = {}
        self._links: Dict[str, List[LinkRecord]] = {}
        self._snapshots: Dict[str, List[ConstellationSnapshot]] = {}
        self._plans: List[ConstellationPlan] = []
        self._shifts: Dict[str, List[MagnitudeShift]] = {}
        self._profiles: Dict[str, ConstellationProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched;
        callers that want a fresh singleton should use
        ``reset_constellation_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._links.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shifts.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[ConstellationReading]:
        """Return one agent's readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_links_locked(
        self, agent_id: str
    ) -> List[LinkRecord]:
        """Return one agent's link records in insertion order. Caller holds the lock."""
        return list(self._links.get(agent_id, []))

    def _agent_snapshots_locked(
        self, agent_id: str
    ) -> List[ConstellationSnapshot]:
        """Return one agent's snapshots in insertion order. Caller holds the lock."""
        return list(self._snapshots.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[ConstellationPlan]:
        """Return one agent's plans in insertion order. Caller holds the lock.

        Plans are stored in a flat list rather than keyed by agent, so
        this helper filters the flat list by ``agent_id`` to give
        callers the same per-agent view the other helpers provide.
        """
        return [p for p in self._plans if p.agent_id == agent_id]

    def _agent_shifts_locked(
        self, agent_id: str
    ) -> List[MagnitudeShift]:
        """Return one agent's magnitude shift records in insertion order. Caller holds the lock."""
        return list(self._shifts.get(agent_id, []))

    def _mode_axis_locked(
        self, readings: List[ConstellationReading]
    ) -> ConstellationAxis:
        """Return the most frequent axis among the supplied readings.

        Ties are broken by insertion order, so the earliest axis
        observed in a tie wins. Returns STAR if the list is empty,
        since STAR is the smallest and most neutral axis. Caller
        holds the lock.
        """
        if not readings:
            return ConstellationAxis.STAR
        counts: Counter = Counter()
        first_seen_order: Dict[ConstellationAxis, int] = {}
        for index, reading in enumerate(readings):
            axis = reading.axis
            counts[axis] += 1
            if axis not in first_seen_order:
                first_seen_order[axis] = index
        # Find the axis with the highest count; ties broken by
        # earliest insertion order.
        best_axis: ConstellationAxis = readings[0].axis
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
        self, profiles: List[ConstellationProfile]
    ) -> ConstellationRegime:
        """Return the most frequent regime among the supplied profiles.

        Returns GROUPING if the list is empty, since GROUPING is the
        default regime — the band that represents a normally
        functioning cognitive sky in which ideas are beginning to
        cluster without being fully charted, neither dark nor
        charted. Caller holds the lock.
        """
        if not profiles:
            return ConstellationRegime.GROUPING
        counts: Dict[ConstellationRegime, int] = {}
        for profile in profiles:
            counts[profile.dominant_regime] = counts.get(
                profile.dominant_regime, 0
            ) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _compute_profile_locked(self, agent_id: str) -> ConstellationProfile:
        """Aggregate an agent's readings, links, and shifts into a profile.

        See ``ConstellationProfile`` for field semantics.
        ``avg_constellation`` is the mean constellation score across
        the agent's readings (0.0 if none). ``dominant_axis`` is the
        most frequent ``ConstellationAxis`` among the agent's
        readings, or STAR if none. ``dominant_regime`` is derived via
        ``_determine_regime`` from ``avg_constellation``.
        ``total_readings``, ``total_links``, and ``total_shifts``
        count the records held for the agent. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        links = self._agent_links_locked(agent_id)
        shifts = self._agent_shifts_locked(agent_id)

        total_readings = len(readings)
        if readings:
            avg_constellation = sum(
                r.constellation_score for r in readings
            ) / len(readings)
        else:
            avg_constellation = 0.0

        dominant_axis = self._mode_axis_locked(readings)
        dominant_regime = _determine_regime(avg_constellation)

        return ConstellationProfile(
            profile_id=_new_id(),
            agent_id=str(agent_id),
            avg_constellation=round(avg_constellation, 4),
            dominant_axis=dominant_axis,
            dominant_regime=dominant_regime,
            total_readings=total_readings,
            total_links=len(links),
            total_shifts=len(shifts),
            updated_at=_now(),
        )

    # ── Constellation Readings ───────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        axis: Any,
        constellation_score: float,
        source: Any,
        intensity: float,
        notes: Optional[str] = None,
    ) -> ConstellationReading:
        """Record a constellation reading for an agent and return it.

        ``axis`` may be passed as a ``ConstellationAxis`` member or
        its string name/value. ``constellation_score`` and
        ``intensity`` are clamped to [0, 1]. ``source`` may be passed
        as a ``ConstellationSource`` member or its string name/value.
        The reading is stored and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            reading = ConstellationReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(ConstellationAxis, axis),
                constellation_score=_clamp(constellation_score, 0.0, 1.0),
                source=_resolve_enum(ConstellationSource, source),
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
    ) -> List[ConstellationReading]:
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

    def get_reading(self, reading_id: str) -> ConstellationReading:
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

    # ── Link Records ────────────────────────────────────────────

    def record_link(
        self,
        agent_id: str,
        axis: Any,
        source: Any,
        before_score: float,
        after_score: float,
        link_magnitude: float,
        notes: Optional[str] = None,
    ) -> LinkRecord:
        """Record a link event for an agent and return it.

        ``axis`` may be passed as a ``ConstellationAxis`` member or
        its string name/value. ``source`` may be passed as a
        ``ConstellationSource`` member or its string name/value.
        ``before_score`` and ``after_score`` are clamped to [0, 1].
        ``link_magnitude`` is clamped to [0, ∞). The link is stored
        and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            record = LinkRecord(
                link_id=_new_id(),
                agent_id=str(agent_id),
                axis=_resolve_enum(ConstellationAxis, axis),
                source=_resolve_enum(ConstellationSource, source),
                before_score=_clamp(before_score, 0.0, 1.0),
                after_score=_clamp(after_score, 0.0, 1.0),
                link_magnitude=_clamp_positive_ms(
                    link_magnitude
                ),
                timestamp=_now(),
                notes=notes,
            )
            self._links.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_links(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LinkRecord]:
        """Return link records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all links are considered;
        otherwise only links for that agent are returned. The most
        recently recorded ``limit`` links are returned. The returned
        list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                links = self._agent_links_locked(agent_id)
            else:
                links = []
                for agent_links in self._links.values():
                    links.extend(agent_links)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return links[-n:] if n else []

    def get_link(self, link_id: str) -> LinkRecord:
        """Retrieve a link record by id.

        Raises ``ValueError`` if no link exists with that id.
        """
        with self._lock:
            for agent_links in self._links.values():
                for link in agent_links:
                    if link.link_id == link_id:
                        return link
        raise ValueError(f"link {link_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> ConstellationSnapshot:
        """Aggregate an agent's recent readings into a snapshot.

        ``avg_constellation`` is the mean constellation score across
        the agent's most recent readings (the last
        ``_SNAPSHOT_READING_WINDOW`` = 20), or 0.0 if none.
        ``dominant_axis`` is the most frequent ``ConstellationAxis``
        among those readings, or STAR if none. ``regime`` is derived
        via ``_determine_regime`` from ``avg_constellation``.
        ``link_count`` is the number of link events recorded against
        the agent. The snapshot is stored and returned; the agent's
        cached profile is invalidated.
        """
        with self._lock:
            agent_readings = self._agent_readings_locked(agent_id)
            recent = agent_readings[-self._SNAPSHOT_READING_WINDOW:]

            if recent:
                avg_constellation = sum(
                    r.constellation_score for r in recent
                ) / len(recent)
            else:
                avg_constellation = 0.0

            dominant_axis = self._mode_axis_locked(recent)
            regime = _determine_regime(avg_constellation)
            link_count = len(
                self._agent_links_locked(agent_id)
            )

            snapshot = ConstellationSnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_constellation=round(avg_constellation, 4),
                dominant_axis=dominant_axis,
                regime=regime,
                link_count=link_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ConstellationSnapshot]:
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

    def get_snapshot(self, snapshot_id: str) -> ConstellationSnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for agent_snapshots in self._snapshots.values():
                for snapshot in agent_snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"snapshot {snapshot_id!r} not found")

    # ── Constellation Plans ────────────────────────────────────────

    def plan_link(
        self,
        agent_id: str,
        strategy: Any,
        target_constellation: float,
        rationale: str,
    ) -> ConstellationPlan:
        """Record a constellation plan for an agent and return it.

        ``strategy`` may be passed as a ``ConstellationStrategy``
        member or its string name/value. ``target_constellation`` is
        clamped to [0, 1]. ``rationale`` explains why this strategy
        was chosen. The plan is stored in a flat list (not keyed by
        agent, since plans are forward-looking interventions rather
        than measurements of state) and returned. The agent's cached
        profile is not invalidated, since a plan does not change the
        agent's measured constellation.
        """
        with self._lock:
            plan = ConstellationPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(ConstellationStrategy, strategy),
                target_constellation=_clamp(target_constellation, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ConstellationPlan]:
        """Return constellation plans, optionally filtered by agent, capped to ``limit``.

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

    def get_plan(self, plan_id: str) -> ConstellationPlan:
        """Retrieve a constellation plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"plan {plan_id!r} not found")

    # ── Magnitude Shift Records ────────────────────────────────────

    def record_magnitude_shift(
        self,
        agent_id: str,
        from_stage: Any,
        to_stage: Any,
        interval_ms: float,
        signature: str,
    ) -> MagnitudeShift:
        """Record a stage transition for an agent and return it.

        ``from_stage`` and ``to_stage`` may each be passed as a
        ``ConstellationStage`` member or its string name/value.
        ``interval_ms`` in [0, ∞) is the duration the from_stage held
        before the transition. ``signature`` is a free-form label
        that describes the character of the transition (e.g. "slow
        emerge", "sudden charting", "deliberate brightening"). The
        magnitude shift record is stored and returned; the agent's
        cached profile is invalidated.

        Magnitude shift records carry no ``notes`` field, since the
        ``signature`` already captures the free-form character of the
        transition and a second free-form field would be redundant.
        """
        with self._lock:
            record = MagnitudeShift(
                shift_id=_new_id(),
                agent_id=str(agent_id),
                from_stage=_resolve_enum(ConstellationStage, from_stage),
                to_stage=_resolve_enum(ConstellationStage, to_stage),
                interval_ms=_clamp_positive_ms(interval_ms),
                signature=str(signature),
                timestamp=_now(),
            )
            self._shifts.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_magnitude_shifts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MagnitudeShift]:
        """Return magnitude shift records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all shifts are considered;
        otherwise only shifts for that agent are returned. The most
        recently recorded ``limit`` magnitude shift records are
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

    def get_magnitude_shift(self, shift_id: str) -> MagnitudeShift:
        """Retrieve a magnitude shift record by id.

        Raises ``ValueError`` if no magnitude shift record exists
        with that id.
        """
        with self._lock:
            for agent_shifts in self._shifts.values():
                for record in agent_shifts:
                    if record.shift_id == shift_id:
                        return record
        raise ValueError(
            f"magnitude shift record {shift_id!r} not found"
        )

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> ConstellationProfile:
        """Return the agent's constellation profile, building it if missing.

        The profile is cached on the agent_id and invalidated
        whenever the agent's readings, links, snapshots, or magnitude
        shifts change. If the agent has data but no profile yet, the
        profile is built from the live stores. Call ``update_profile``
        to force a refresh or override a computed field. Field
        semantics are documented on ``ConstellationProfile`` and
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
    ) -> ConstellationProfile:
        """Refresh and optionally override fields of an agent's constellation profile.

        The profile is first recomputed from the live stores, then
        any supplied overrides in ``kwargs`` (matching
        ``ConstellationProfile`` field names) are applied. Accepted
        overrides: ``avg_constellation`` (float), ``dominant_axis``
        (``ConstellationAxis``), ``dominant_regime``
        (``ConstellationRegime``), ``total_readings``,
        ``total_links``, ``total_shifts`` (int). Enum-valued
        overrides may be passed as the enum member or its string
        name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_constellation":
                    try:
                        profile.avg_constellation = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_axis":
                    try:
                        profile.dominant_axis = _resolve_enum(
                            ConstellationAxis, value
                        )
                    except ValueError:
                        pass
                elif key == "dominant_regime":
                    try:
                        profile.dominant_regime = _resolve_enum(
                            ConstellationRegime, value
                        )
                    except ValueError:
                        pass
                elif key in (
                    "total_readings",
                    "total_links",
                    "total_shifts",
                ):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.updated_at = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[ConstellationProfile]:
        """Return all stored constellation profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not
        affect the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> ConstellationStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` is the number of distinct agent_ids with any
        data across readings, links, snapshots, and shifts. Scalar
        totals are the counts of each record type.
        ``avg_constellation`` is the mean constellation score across
        all readings, or 0.0 when none exist. ``dominant_regime`` is
        the most frequent regime across all cached profiles, or
        GROUPING when none exist. When no profiles exist but readings
        do, the dominant regime is derived from the average
        constellation via ``_determine_regime`` so the stats always
        reflect real state.
        """
        with self._lock:
            agent_ids: set = set()
            agent_ids.update(self._readings.keys())
            agent_ids.update(self._links.keys())
            agent_ids.update(self._snapshots.keys())
            agent_ids.update(self._shifts.keys())

            total_readings = 0
            constellation_sum = 0.0
            for agent_readings in self._readings.values():
                total_readings += len(agent_readings)
                for reading in agent_readings:
                    constellation_sum += reading.constellation_score
            avg_constellation = (
                round(constellation_sum / total_readings, 4) if total_readings else 0.0
            )

            total_links = sum(
                len(agent_links)
                for agent_links in self._links.values()
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
                # the regime from the average constellation so the
                # stats reflect real state rather than the default
                # GROUPING.
                dominant_regime = _determine_regime(avg_constellation)
            else:
                dominant_regime = ConstellationRegime.GROUPING

            return ConstellationStats(
                total_agents=len(agent_ids),
                total_readings=total_readings,
                total_links=total_links,
                total_snapshots=total_snapshots,
                total_shifts=total_shifts,
                avg_constellation=avg_constellation,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveConstellation] = None
_engine_lock = threading.Lock()


def get_constellation_engine() -> AgentCognitiveConstellation:
    """Get or create the singleton ``AgentCognitiveConstellation`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveConstellation()
    return _engine


def reset_constellation_engine() -> None:
    """Reset the singleton ``AgentCognitiveConstellation`` instance.

    Drops the reference to the current engine so the next
    ``get_constellation_engine`` call creates a fresh instance.
    Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        _engine = None
