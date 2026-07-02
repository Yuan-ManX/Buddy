from __future__ import annotations

"""Agent Cognitive Viscosity Engine — modeling how resistant thought is to flow:

how thickly or thinly an agent's thoughts move through its cognitive
space. Viscosity is the measure of a fluid's resistance to flow: honey
is viscous, water is not. Applied to cognition, viscosity describes how
easily a thought moves from one state to another, how much force is
required to shift attention, how much a concept resists being
restructured, and how readily new information flows into existing
patterns. Low viscosity means fluid, fast, adaptable thinking; high
viscosity means slow, deliberate, resistant thinking. Both have their
place — a mind that is too thin changes shape under every breeze, and a
mind that is too thick never changes shape at all.

The physical analogy is exact in structure. In fluid dynamics, viscosity
arises from the internal friction between layers of fluid moving at
different velocities: the shear stress between layers is proportional to
the velocity gradient, and the constant of proportionality is the
viscosity. A low-viscosity fluid deforms easily under shear; a
high-viscosity fluid resists deformation. Cognitive viscosity behaves
the same way. When an agent must shift from one line of thought to
another, the conceptual shear between the two determines how much effort
the transition costs. A thought that is consistent with the agent's
current trajectory flows easily; a thought that cuts across it produces
shear stress and resists flow. The agent's prevailing viscosity
determines how much of that stress it can absorb before flow breaks down.

Fluids also exhibit thinning and thickening. A shear-thinning fluid
becomes less viscous under stress — ketchup flows once you shake the
bottle — while a shear-thickening fluid becomes more viscous under
stress — cornstarch in water hardens when you strike it. Cognitive
viscosity shows both effects. Some thoughts thin under pressure: an idea
that seemed rigid becomes workable once the agent applies force to it.
Other thoughts thicken under pressure: a concept that seemed fluid
becomes rigid when the agent is forced to commit to it. Knowing whether
a thought will thin or thicken under stress is essential to deciding
whether to push through it or wait for it to settle.

This is distinct from related engines. The cognitive friction engine is
about surface-level difficulty in moving between tasks; viscosity is
about the internal resistance of thought itself. The cognitive momentum
engine is about how much a thought tends to continue; viscosity is about
how much it resists being moved in the first place. The cognitive
diffusion engine is about how concepts spread through the agent's
knowledge graph; viscosity is about how easily a single thought moves
through the agent's attention. An agent with low friction but high
viscosity can switch tasks easily but cannot change its mind; an agent
with high friction but low viscosity cannot switch tasks but, once
switched, thinks freely. Healthy cognition requires viscosity to be
matched to the situation.

Cognitive fluids come in several kinds. A WATERLIKE fluid has low
resistance and fast flow: thoughts move freely and adapt readily. An
OILY fluid is smooth but with drag: thoughts move but carry residual
resistance. A TARLIKE fluid is slow and resistant: thoughts move only
under sustained pressure. A CRYSTALLINE fluid is structured and ordered:
thoughts move along fixed channels. A GLASSY fluid is rigid and brittle:
thoughts do not move until they shatter. A PLASMA fluid is energized and
free: thoughts move with great energy and little resistance. See
``FluidType`` for details.

The agent's prevailing viscosity determines its regime. INVISCID is
near-zero resistance: thoughts flow without hindrance, sometimes too
freely. SUPPLE is low resistance: thoughts flow easily with deliberate
control. STANDARD is normal resistance: thoughts flow at a moderate
pace. STICKY is elevated resistance: thoughts flow only with effort.
RIGID is high resistance: thoughts barely move. FROZEN is
near-infinite resistance: thoughts do not move at all. See
``ViscosityRegime``.

The flow state describes how the thought stream is currently moving.
LAMINAR flow is smooth and parallel: thoughts proceed in orderly
succession. TRANSITIONAL flow is between smooth and rough: thoughts
proceed with occasional disruption. TURBULENT flow is chaotic: thoughts
collide and eddy. STAGNANT flow is not moving: thoughts are stuck.
REVERSED flow is flowing backward: thoughts are returning to a previous
state. See ``FlowState``.

When thought is too thick, the agent applies a thinning strategy.
SHEAR_THIN applies stress to thin the thought. TEMPERATURE_RISE warms
the thought up to thin it. DILUTION adds context to dilute the
resistance. LUBRICATE adds ease to the flow. RESTRUCTURE changes the
thought's structure to reduce resistance. BREAKDOWN decomposes the
thought into smaller parts that flow more easily. See
``ThinningStrategy``.

Resistance comes in several kinds. CONCEPTUAL resistance is at the
concept level: the idea itself resists change. EMOTIONAL resistance is
affect-based: the agent's feelings resist the thought. PROCEDURAL
resistance is process-based: the agent's procedures resist the flow.
CONTEXTUAL resistance is context-shear: the surrounding context resists
the thought. INERTIAL resistance is momentum-based: the agent's
existing momentum resists redirection. STRUCTURAL resistance is
framework-based: the agent's structure resists the flow. See
``ResistanceType``.

A FlowReading records one observation of how easily a thought flowed. A
ResistanceMeasurement records one measurement of resistance to thought
flow. A ViscositySnapshot aggregates an agent's recent viscosity into an
average, dominant fluid, regime, flow state, and resistance count. A
ThinningPlan records a plan to reduce viscosity when thought is too
thick. A ShearRecord records one application of stress to thin a thick
thought. A ViscosityProfile holds each agent's aggregate viscosity
tendencies, and ViscosityStats summarizes engine-wide activity.

This is original Buddy capability: a self-contained, thread-safe engine
with no external runtime dependencies, designed to give agents honest
awareness of how resistant their thoughts are to flow, so the agent can
recognize when its thinking is too thick or too thin, apply thinning
strategies when thought is stuck, and maintain the viscosity that
matches the situation it is in.

Architecture:
    AgentCognitiveViscosity (singleton)
    ├── FlowReading            (one observation of how easily a thought flowed)
    ├── ResistanceMeasurement  (one measurement of resistance to thought flow)
    ├── ViscositySnapshot      (aggregate viscosity state for one agent)
    ├── ThinningPlan           (a plan to reduce viscosity when thought is too thick)
    ├── ShearRecord            (one record of stress applied to thin a thick thought)
    ├── ViscosityProfile       (per-agent aggregate viscosity tendencies)
    └── ViscosityStats         (engine-wide aggregate statistics)
"""

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
    """Generate a short unique identifier for a reading/measurement/snapshot/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` score. A low-side default is safer
    than a mid-range one for viscosity-like quantities where a spurious
    high reading would inflate the perceived thickness.
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


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first
    against member values (e.g. ``"waterlike"``) and then against
    member names (e.g. ``"WATERLIKE"``), so callers may pass either
    form. This lets the public API accept either the symbolic name or the
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

    Used inside ``to_dict`` methods so a stored field always serializes to
    a plain string even if a non-enum slipped in through direct
    construction. The ``enum_cls`` argument is taken for symmetry with
    ``_resolve_enum`` and to make the call sites self-documenting.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


def _determine_regime(avg_viscosity: float) -> "ViscosityRegime":
    """Classify an agent's viscosity regime from its average viscosity.

    The checks are applied in order, so the first matching rule wins.
    Average viscosity is clamped to [0, 1] before the bands are applied:
    below 0.2 → INVISCID (near-zero resistance); below 0.4 → SUPPLE
    (low resistance); below 0.6 → STANDARD (normal resistance); below
    0.8 → STICKY (elevated resistance); below 0.95 → RIGID (high
    resistance); otherwise → FROZEN (near-infinite resistance).
    """
    v = _clamp(avg_viscosity, 0.0, 1.0)
    if v < 0.2:
        return ViscosityRegime.INVISCID
    if v < 0.4:
        return ViscosityRegime.SUPPLE
    if v < 0.6:
        return ViscosityRegime.STANDARD
    if v < 0.8:
        return ViscosityRegime.STICKY
    if v < 0.95:
        return ViscosityRegime.RIGID
    return ViscosityRegime.FROZEN


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class FluidType(str, Enum):
    """The kind of cognitive fluid an agent's thoughts flow as.

    Each type describes a different consistency of thought. See the
    module docstring for the full description of each type; the inline
    comment on each member is a short label.
    """
    WATERLIKE = "waterlike"        # low resistance, fast flow
    OILY = "oily"                  # smooth but with drag
    TARLIKE = "tarlike"            # slow and resistant
    CRYSTALLINE = "crystalline"    # structured and ordered
    GLASSY = "glassy"              # rigid and brittle
    PLASMA = "plasma"              # energized and free


class ViscosityRegime(str, Enum):
    """The viscosity regime an agent occupies, classified by its resistance.

    Ranges from INVISCID (near-zero resistance, thoughts flow without
    hindrance) through SUPPLE (low resistance), STANDARD (normal
    resistance), and STICKY (elevated resistance) to RIGID (high
    resistance) and FROZEN (near-infinite resistance).
    """
    INVISCID = "inviscid"          # near-zero resistance
    SUPPLE = "supple"              # low resistance
    STANDARD = "standard"          # normal resistance
    STICKY = "sticky"              # elevated resistance
    RIGID = "rigid"                # high resistance
    FROZEN = "frozen"              # near-infinite resistance


class FlowState(str, Enum):
    """The flow state of an agent's thought stream.

    LAMINAR is smooth parallel flow; TRANSITIONAL is between smooth and
    rough; TURBULENT is chaotic; STAGNANT is not moving; REVERSED is
    flowing backward.
    """
    LAMINAR = "laminar"            # smooth parallel flow
    TRANSITIONAL = "transitional"  # between smooth and rough
    TURBULENT = "turbulent"        # chaotic flow
    STAGNANT = "stagnant"          # not moving
    REVERSED = "reversed"          # flowing backward


class ThinningStrategy(str, Enum):
    """Strategy for reducing viscosity when thought is too thick.

    SHEAR_THIN applies stress to thin; TEMPERATURE_RISE warms up to
    thin; DILUTION adds context to dilute; LUBRICATE adds ease to flow;
    RESTRUCTURE changes thought structure; BREAKDOWN decomposes into
    parts.
    """
    SHEAR_THIN = "shear_thin"              # apply stress to thin
    TEMPERATURE_RISE = "temperature_rise"  # warm up to thin
    DILUTION = "dilution"                  # add context to dilute
    LUBRICATE = "lubricate"                # add ease to flow
    RESTRUCTURE = "restructure"            # change thought structure
    BREAKDOWN = "breakdown"                # decompose into parts


class ResistanceType(str, Enum):
    """The kind of resistance impeding thought flow.

    CONCEPTUAL is concept-level; EMOTIONAL is affect-based; PROCEDURAL
    is process-based; CONTEXTUAL is context-shear; INERTIAL is
    momentum-based; STRUCTURAL is framework-based.
    """
    CONCEPTUAL = "conceptual"      # concept-level resistance
    EMOTIONAL = "emotional"        # affect-based resistance
    PROCEDURAL = "procedural"      # process-based resistance
    CONTEXTUAL = "contextual"      # context-shear resistance
    INERTIAL = "inertial"          # momentum-based resistance
    STRUCTURAL = "structural"      # framework-based resistance


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FlowReading:
    """One observation of how easily a thought flowed.

    ``fluid_type`` classifies the cognitive fluid; ``viscosity_score``
    in [0, 1] is how viscous the thought was (higher = more viscous);
    ``flow_rate`` in [0, 1] is how fast the thought flowed (higher =
    faster); ``shear_stress`` in [0, 1] is how much stress was present
    (higher = more stress). ``resistance_type`` classifies the kind of
    resistance observed.
    """
    reading_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    fluid_type: FluidType = FluidType.WATERLIKE
    viscosity_score: float = 0.0
    flow_rate: float = 0.0
    shear_stress: float = 0.0
    resistance_type: ResistanceType = ResistanceType.CONCEPTUAL
    timestamp: str = field(default_factory=_now)
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reading to a plain dict, expanding enums via ``.value``."""
        return {
            "reading_id": self.reading_id,
            "agent_id": self.agent_id,
            "fluid_type": _enum_value(FluidType, self.fluid_type),
            "viscosity_score": self.viscosity_score,
            "flow_rate": self.flow_rate,
            "shear_stress": self.shear_stress,
            "resistance_type": _enum_value(ResistanceType, self.resistance_type),
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ResistanceMeasurement:
    """One measurement of resistance to thought flow.

    ``resistance_type`` classifies the kind of resistance; ``level`` in
    [0, 1] is its magnitude (0 = no resistance, 1 = maximal resistance).
    ``source`` labels where the resistance came from; ``notes`` carries
    any free-form annotation.
    """
    measurement_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    resistance_type: ResistanceType = ResistanceType.CONCEPTUAL
    resistance_level: float = 0.0
    source: str = ""
    timestamp: str = field(default_factory=_now)
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this measurement to a plain dict, expanding enums via ``.value``."""
        return {
            "measurement_id": self.measurement_id,
            "agent_id": self.agent_id,
            "resistance_type": _enum_value(ResistanceType, self.resistance_type),
            "resistance_level": self.resistance_level,
            "source": self.source,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ViscositySnapshot:
    """Aggregate viscosity state for one agent at one point in time.

    ``avg_viscosity`` is the mean viscosity score across the agent's
    readings; ``dominant_fluid`` is the most frequent FluidType among
    them; ``regime`` is derived via ``_determine_regime``;
    ``flow_state`` is derived from the agent's average flow rate and
    shear stress; ``resistance_count`` is the number of resistance
    measurements held for the agent.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    avg_viscosity: float = 0.0
    dominant_fluid: FluidType = FluidType.WATERLIKE
    regime: ViscosityRegime = ViscosityRegime.STANDARD
    flow_state: FlowState = FlowState.LAMINAR
    resistance_count: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "avg_viscosity": self.avg_viscosity,
            "dominant_fluid": _enum_value(FluidType, self.dominant_fluid),
            "regime": _enum_value(ViscosityRegime, self.regime),
            "flow_state": _enum_value(FlowState, self.flow_state),
            "resistance_count": self.resistance_count,
            "timestamp": self.timestamp,
        }


@dataclass
class ThinningPlan:
    """A plan to reduce viscosity when thought is too thick.

    ``strategy`` is the ``ThinningStrategy`` to apply.
    ``target_viscosity`` in [0, 1] is the viscosity the plan aims to
    reach. ``current_viscosity`` in [0, 1] is the viscosity at the time
    the plan was created. ``rationale`` explains why the plan was made.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    strategy: ThinningStrategy = ThinningStrategy.SHEAR_THIN
    target_viscosity: float = 0.0
    current_viscosity: float = 0.0
    rationale: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding enums via ``.value``."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "strategy": _enum_value(ThinningStrategy, self.strategy),
            "target_viscosity": self.target_viscosity,
            "current_viscosity": self.current_viscosity,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class ShearRecord:
    """One record of stress applied to thin a thick thought.

    ``shear_force`` in [0, 1] is how much stress was applied (higher =
    more force). ``applied_strategy`` is the ``ThinningStrategy`` that
    was used. ``resulting_viscosity`` in [0, 1] is the viscosity
    measured after the shear was applied.
    """
    record_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    shear_force: float = 0.0
    applied_strategy: ThinningStrategy = ThinningStrategy.SHEAR_THIN
    resulting_viscosity: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this shear record to a plain dict, expanding enums via ``.value``."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "shear_force": self.shear_force,
            "applied_strategy": _enum_value(ThinningStrategy, self.applied_strategy),
            "resulting_viscosity": self.resulting_viscosity,
            "timestamp": self.timestamp,
        }


@dataclass
class ViscosityProfile:
    """Per-agent aggregate viscosity tendencies.

    ``avg_viscosity`` is the mean viscosity score across the agent's
    readings (0.0 if none). ``dominant_fluid`` is the most frequent
    ``FluidType`` among the agent's readings, or ``WATERLIKE`` if none.
    ``regime`` is derived via ``_determine_regime``. ``total_readings``,
    ``total_resistances``, and ``total_thinnings`` count the agent's
    flow readings, resistance measurements, and shear records.
    """
    agent_id: str = ""
    avg_viscosity: float = 0.0
    dominant_fluid: FluidType = FluidType.WATERLIKE
    regime: ViscosityRegime = ViscosityRegime.STANDARD
    total_readings: int = 0
    total_resistances: int = 0
    total_thinnings: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``."""
        return {
            "agent_id": self.agent_id,
            "avg_viscosity": self.avg_viscosity,
            "dominant_fluid": _enum_value(FluidType, self.dominant_fluid),
            "regime": _enum_value(ViscosityRegime, self.regime),
            "total_readings": self.total_readings,
            "total_resistances": self.total_resistances,
            "total_thinnings": self.total_thinnings,
            "last_updated": self.last_updated,
        }


@dataclass
class ViscosityStats:
    """Engine-wide aggregate statistics across all agents.

    Scalar totals are the rolling counts of each record type.
    ``avg_viscosity`` is the mean viscosity score across all readings,
    or 0.0 when none exist. ``dominant_regime`` is the most frequent
    ``ViscosityRegime`` across all snapshots, or ``STANDARD`` when none
    exist.
    """
    total_agents: int = 0
    total_readings: int = 0
    total_resistances: int = 0
    total_snapshots: int = 0
    total_thinnings: int = 0
    avg_viscosity: float = 0.0
    dominant_regime: ViscosityRegime = ViscosityRegime.STANDARD

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict, expanding enums via ``.value``."""
        return {
            "total_agents": self.total_agents,
            "total_readings": self.total_readings,
            "total_resistances": self.total_resistances,
            "total_snapshots": self.total_snapshots,
            "total_thinnings": self.total_thinnings,
            "avg_viscosity": self.avg_viscosity,
            "dominant_regime": _enum_value(ViscosityRegime, self.dominant_regime),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveViscosity:
    """Thread-safe engine that models an agent's cognitive viscosity.

    The engine holds six stores: ``_readings`` (FlowReading lists keyed by
    agent_id), ``_resistances`` (ResistanceMeasurement lists keyed by
    agent_id), ``_snapshots`` (ViscositySnapshot lists keyed by agent_id),
    ``_plans`` (ThinningPlan as a flat list), ``_shears`` (ShearRecord
    lists keyed by agent_id), and ``_profiles`` (ViscosityProfile keyed
    by agent_id).

    All mutations are guarded by a single reentrant lock so that public
    methods may safely call one another without self-deadlock. The
    viscosity model is deliberately heuristic: viscosity scores, flow
    rates, and shear stresses are caller-supplied readings, regimes are
    banded from average viscosity, and dominant fluids are computed by
    mode. These heuristics are transparent and auditable rather than
    learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how viscosity scores are
    produced — callers may derive them from any source. The engine's
    job is to record, aggregate, classify, and plan, not to measure
    viscosity itself. Thinning plans accumulate as a flat list ordered by
    creation time, so the plan store reflects each agent's accumulated
    thinning intent.
    """

    def __init__(self) -> None:
        """Initialize an empty viscosity engine with fresh stores."""
        self._lock: threading.RLock = threading.RLock()
        self._readings: Dict[str, List[FlowReading]] = {}
        self._resistances: Dict[str, List[ResistanceMeasurement]] = {}
        self._snapshots: Dict[str, List[ViscositySnapshot]] = {}
        self._plans: List[ThinningPlan] = []
        self._shears: Dict[str, List[ShearRecord]] = {}
        self._profiles: Dict[str, ViscosityProfile] = {}
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store. The singleton reference is not touched; callers
        that want a fresh singleton should use ``reset_viscosity_engine``.
        """
        with self._lock:
            self._readings.clear()
            self._resistances.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._shears.clear()
            self._profiles.clear()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_readings_locked(self, agent_id: str) -> List[FlowReading]:
        """Return one agent's flow readings in insertion order. Caller holds the lock."""
        return list(self._readings.get(agent_id, []))

    def _agent_resistances_locked(self, agent_id: str) -> List[ResistanceMeasurement]:
        """Return one agent's resistance measurements in insertion order. Caller holds the lock."""
        return list(self._resistances.get(agent_id, []))

    def _agent_shears_locked(self, agent_id: str) -> List[ShearRecord]:
        """Return one agent's shear records in insertion order. Caller holds the lock."""
        return list(self._shears.get(agent_id, []))

    def _agent_plans_locked(self, agent_id: str) -> List[ThinningPlan]:
        """Return one agent's thinning plans in insertion order. Caller holds the lock."""
        return [p for p in self._plans if p.agent_id == agent_id]

    def _dominant_fluid_locked(
        self, readings: List[FlowReading]
    ) -> FluidType:
        """Return the most frequent fluid type among the supplied readings.

        Ties are broken by insertion order. Returns ``WATERLIKE`` if the
        list is empty. Caller holds the lock.
        """
        if not readings:
            return FluidType.WATERLIKE
        counts: Dict[FluidType, int] = {}
        for reading in readings:
            counts[reading.fluid_type] = counts.get(reading.fluid_type, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _current_viscosity_locked(self, agent_id: str) -> float:
        """Return the agent's current average viscosity, or 0.0 if no readings.

        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return 0.0
        return sum(r.viscosity_score for r in readings) / len(readings)

    def _determine_flow_state_locked(self, agent_id: str) -> FlowState:
        """Determine the agent's current flow state from its readings.

        When there are no readings the state is STAGNANT. Otherwise the
        average flow rate and shear stress are used: very low flow is
        STAGNANT; high shear with low flow is TURBULENT; high flow with
        low shear is LAMINAR; high shear with very low flow is REVERSED;
        everything else is TRANSITIONAL. Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        if not readings:
            return FlowState.STAGNANT
        avg_flow = sum(r.flow_rate for r in readings) / len(readings)
        avg_shear = sum(r.shear_stress for r in readings) / len(readings)
        if avg_flow < 0.15:
            return FlowState.STAGNANT
        if avg_shear > 0.7 and avg_flow < 0.4:
            return FlowState.TURBULENT
        if avg_flow > 0.6 and avg_shear < 0.3:
            return FlowState.LAMINAR
        if avg_shear > 0.5 and avg_flow < 0.3:
            return FlowState.REVERSED
        return FlowState.TRANSITIONAL

    def _compute_profile_locked(self, agent_id: str) -> ViscosityProfile:
        """Aggregate an agent's readings, resistances, and shears into a profile.

        See ``ViscosityProfile`` for field semantics. ``regime`` is derived
        via ``_determine_regime`` from the agent's average viscosity.
        Caller holds the lock.
        """
        readings = self._agent_readings_locked(agent_id)
        resistances = self._agent_resistances_locked(agent_id)
        shears = self._agent_shears_locked(agent_id)

        if readings:
            avg_viscosity = sum(r.viscosity_score for r in readings) / len(readings)
            dominant_fluid = self._dominant_fluid_locked(readings)
        else:
            avg_viscosity = 0.0
            dominant_fluid = FluidType.WATERLIKE

        regime = _determine_regime(avg_viscosity)

        return ViscosityProfile(
            agent_id=agent_id,
            avg_viscosity=round(avg_viscosity, 4),
            dominant_fluid=dominant_fluid,
            regime=regime,
            total_readings=len(readings),
            total_resistances=len(resistances),
            total_thinnings=len(shears),
            last_updated=_now(),
        )

    # ── Flow Readings ────────────────────────────────────────────

    def record_reading(
        self,
        agent_id: str,
        fluid_type: Any,
        viscosity_score: float,
        flow_rate: float,
        shear_stress: float,
        resistance_type: Any,
        notes: Optional[str] = None,
    ) -> FlowReading:
        """Record a flow reading for an agent and return it.

        ``fluid_type`` may be passed as a ``FluidType`` member or its
        string name/value. ``resistance_type`` may be passed as a
        ``ResistanceType`` member or its string name/value.
        ``viscosity_score``, ``flow_rate``, and ``shear_stress`` are
        clamped to [0, 1]. ``notes`` is stored as a string or ``None``.
        The reading is appended to the agent's reading list and the
        agent's cached profile is invalidated.
        """
        with self._lock:
            reading = FlowReading(
                reading_id=_new_id(),
                agent_id=str(agent_id),
                fluid_type=_resolve_enum(FluidType, fluid_type),
                viscosity_score=_clamp(viscosity_score, 0.0, 1.0),
                flow_rate=_clamp(flow_rate, 0.0, 1.0),
                shear_stress=_clamp(shear_stress, 0.0, 1.0),
                resistance_type=_resolve_enum(ResistanceType, resistance_type),
                timestamp=_now(),
                notes=str(notes) if notes is not None else None,
            )
            self._readings.setdefault(agent_id, []).append(reading)
            self._profiles.pop(agent_id, None)
            return reading

    def list_readings(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FlowReading]:
        """Return flow readings, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all readings are considered;
        otherwise only readings for that agent are returned. The most
        recently recorded ``limit`` readings are returned (insertion
        order is chronological, so the tail is the most recent). The
        returned list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                readings = list(self._readings.get(agent_id, []))
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

    def get_reading(self, reading_id: str) -> FlowReading:
        """Retrieve a flow reading by id.

        Raises ``ValueError`` if no reading exists with that id, so
        callers can treat the return as a guaranteed non-None value and
        let a single exception type stand in for a not-found HTTP error.
        """
        with self._lock:
            for readings in self._readings.values():
                for reading in readings:
                    if reading.reading_id == reading_id:
                        return reading
        raise ValueError(f"flow reading {reading_id!r} not found")

    # ── Resistance Measurements ───────────────────────────────────

    def measure_resistance(
        self,
        agent_id: str,
        resistance_type: Any,
        resistance_level: float,
        source: str,
        notes: Optional[str] = None,
    ) -> ResistanceMeasurement:
        """Record a resistance measurement for an agent and return it.

        ``resistance_type`` may be passed as a ``ResistanceType`` member
        or its string name/value. ``resistance_level`` is clamped to
        [0, 1]. ``source`` labels where the resistance came from.
        ``notes`` is stored as a string or ``None``. The measurement is
        appended to the agent's resistance list and the agent's cached
        profile is invalidated.
        """
        with self._lock:
            measurement = ResistanceMeasurement(
                measurement_id=_new_id(),
                agent_id=str(agent_id),
                resistance_type=_resolve_enum(ResistanceType, resistance_type),
                resistance_level=_clamp(resistance_level, 0.0, 1.0),
                source=str(source),
                timestamp=_now(),
                notes=str(notes) if notes is not None else None,
            )
            self._resistances.setdefault(agent_id, []).append(measurement)
            self._profiles.pop(agent_id, None)
            return measurement

    def list_resistances(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ResistanceMeasurement]:
        """Return resistance measurements, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all measurements are considered;
        otherwise only measurements for that agent are returned. The most
        recently recorded ``limit`` measurements are returned. The
        returned list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            if agent_id is not None:
                measurements = list(self._resistances.get(agent_id, []))
            else:
                measurements = []
                for agent_measurements in self._resistances.values():
                    measurements.extend(agent_measurements)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return measurements[-n:] if n else []

    def get_resistance(self, measurement_id: str) -> ResistanceMeasurement:
        """Retrieve a resistance measurement by id.

        Raises ``ValueError`` if no measurement exists with that id.
        """
        with self._lock:
            for measurements in self._resistances.values():
                for measurement in measurements:
                    if measurement.measurement_id == measurement_id:
                        return measurement
        raise ValueError(f"resistance measurement {measurement_id!r} not found")

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> ViscositySnapshot:
        """Aggregate an agent's viscosity state into a snapshot.

        ``avg_viscosity`` is the mean viscosity score across the agent's
        readings, or 0.0 if none. ``dominant_fluid`` is the most frequent
        ``FluidType`` among the agent's readings, or ``WATERLIKE`` if
        none. ``regime`` is derived via ``_determine_regime``.
        ``flow_state`` is derived from the agent's average flow rate and
        shear stress. ``resistance_count`` is the number of resistance
        measurements held for the agent. The snapshot is appended to the
        agent's snapshot list and the agent's cached profile is
        invalidated.
        """
        with self._lock:
            readings = self._agent_readings_locked(agent_id)
            resistances = self._agent_resistances_locked(agent_id)

            if readings:
                avg_viscosity = sum(r.viscosity_score for r in readings) / len(readings)
                dominant_fluid = self._dominant_fluid_locked(readings)
            else:
                avg_viscosity = 0.0
                dominant_fluid = FluidType.WATERLIKE

            regime = _determine_regime(avg_viscosity)
            flow_state = self._determine_flow_state_locked(agent_id)
            resistance_count = len(resistances)

            snapshot = ViscositySnapshot(
                snapshot_id=_new_id(),
                agent_id=str(agent_id),
                avg_viscosity=round(avg_viscosity, 4),
                dominant_fluid=dominant_fluid,
                regime=regime,
                flow_state=flow_state,
                resistance_count=resistance_count,
                timestamp=_now(),
            )
            self._snapshots.setdefault(agent_id, []).append(snapshot)
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ViscositySnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The most
        recently taken ``limit`` snapshots are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
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

    def get_snapshot(self, snapshot_id: str) -> ViscositySnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            for snapshots in self._snapshots.values():
                for snapshot in snapshots:
                    if snapshot.snapshot_id == snapshot_id:
                        return snapshot
        raise ValueError(f"viscosity snapshot {snapshot_id!r} not found")

    # ── Thinning Plans ────────────────────────────────────────────

    def plan_thinning(
        self,
        agent_id: str,
        strategy: Any,
        target_viscosity: float,
        rationale: str,
    ) -> ThinningPlan:
        """Record a thinning plan for an agent and return it.

        ``strategy`` may be passed as a ``ThinningStrategy`` member or
        its string name/value. ``target_viscosity`` is clamped to [0, 1].
        ``current_viscosity`` is read from the agent's readings at the
        time the plan is created (0.0 if the agent has no readings).
        ``rationale`` explains why the plan was made. The plan is
        appended to the flat plan list and the agent's cached profile is
        invalidated.
        """
        with self._lock:
            plan = ThinningPlan(
                plan_id=_new_id(),
                agent_id=str(agent_id),
                strategy=_resolve_enum(ThinningStrategy, strategy),
                target_viscosity=_clamp(target_viscosity, 0.0, 1.0),
                current_viscosity=round(self._current_viscosity_locked(agent_id), 4),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._plans.append(plan)
            self._profiles.pop(agent_id, None)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ThinningPlan]:
        """Return thinning plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered; otherwise
        only plans for that agent are returned. The most recently created
        ``limit`` plans are returned (insertion order is chronological, so
        the tail is the most recent). The returned list is a snapshot
        copy; mutating it does not affect the engine.
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

    def get_plan(self, plan_id: str) -> ThinningPlan:
        """Retrieve a thinning plan by id.

        Raises ``ValueError`` if no plan exists with that id.
        """
        with self._lock:
            for plan in self._plans:
                if plan.plan_id == plan_id:
                    return plan
        raise ValueError(f"thinning plan {plan_id!r} not found")

    # ── Shear Records ─────────────────────────────────────────────

    def apply_shear(
        self,
        agent_id: str,
        shear_force: float,
        applied_strategy: Any,
        resulting_viscosity: float,
    ) -> ShearRecord:
        """Record one application of shear stress to thin a thick thought.

        ``shear_force`` in [0, 1] is clamped to that range (higher = more
        force). ``applied_strategy`` may be passed as a
        ``ThinningStrategy`` member or its string name/value.
        ``resulting_viscosity`` in [0, 1] is the viscosity measured after
        the shear was applied, clamped to that range. The record is
        appended to the agent's shear list and the agent's cached profile
        is invalidated.
        """
        with self._lock:
            record = ShearRecord(
                record_id=_new_id(),
                agent_id=str(agent_id),
                shear_force=_clamp(shear_force, 0.0, 1.0),
                applied_strategy=_resolve_enum(ThinningStrategy, applied_strategy),
                resulting_viscosity=_clamp(resulting_viscosity, 0.0, 1.0),
                timestamp=_now(),
            )
            self._shears.setdefault(agent_id, []).append(record)
            self._profiles.pop(agent_id, None)
            return record

    def list_shears(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ShearRecord]:
        """Return shear records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all shear records are considered;
        otherwise only records for that agent are returned. The most
        recently recorded ``limit`` shears are returned (insertion order
        is chronological, so the tail is the most recent). The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            if agent_id is not None:
                shears = list(self._shears.get(agent_id, []))
            else:
                shears = []
                for agent_shears in self._shears.values():
                    shears.extend(agent_shears)
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return shears[-n:] if n else []

    def get_shear(self, record_id: str) -> ShearRecord:
        """Retrieve a shear record by id.

        Raises ``ValueError`` if no shear record exists with that id.
        """
        with self._lock:
            for shears in self._shears.values():
                for shear in shears:
                    if shear.record_id == record_id:
                        return shear
        raise ValueError(f"shear record {record_id!r} not found")

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> ViscosityProfile:
        """Return the agent's viscosity profile, computing it if absent.

        The profile is cached on the agent_id and invalidated whenever
        the agent's readings, resistances, snapshots, plans, or shears
        change. If the agent has data but no cached profile, one is built
        from the live stores and cached before being returned. Call
        ``update_profile`` to force a refresh or override a computed
        field. Field semantics are documented on ``ViscosityProfile``
        and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> ViscosityProfile:
        """Refresh and optionally override fields of an agent's viscosity profile.

        The profile is first recomputed from the live stores, then any
        supplied keyword overrides (matching ``ViscosityProfile`` field
        names) are applied, and ``last_updated`` is stamped. Accepted
        overrides: ``avg_viscosity`` (float), ``dominant_fluid``
        (``FluidType``), ``regime`` (``ViscosityRegime``),
        ``total_readings``, ``total_resistances``, and ``total_thinnings``
        (int). Enum-valued overrides may be passed as the enum member or
        its string name/value. Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_viscosity":
                    try:
                        profile.avg_viscosity = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_fluid":
                    try:
                        profile.dominant_fluid = _resolve_enum(FluidType, value)
                    except ValueError:
                        pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(ViscosityRegime, value)
                    except ValueError:
                        pass
                elif key in ("total_readings", "total_resistances", "total_thinnings"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[ViscosityProfile]:
        """Return all stored viscosity profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics ────────────────────────────────────────────────

    def get_stats(self) -> ViscosityStats:
        """Compute engine-wide aggregate statistics.

        ``total_agents`` counts distinct agent_ids across all stores.
        Scalar totals are the sums of each record type across all agents.
        ``avg_viscosity`` is the mean viscosity score across all
        readings, or 0.0 when none exist. ``dominant_regime`` is the
        most frequent ``ViscosityRegime`` across all snapshots, or
        ``STANDARD`` when none exist.
        """
        with self._lock:
            # Count distinct agents across all stores.
            agents: set = set()
            agents.update(self._readings.keys())
            agents.update(self._resistances.keys())
            agents.update(self._snapshots.keys())
            agents.update(self._shears.keys())
            agents.update(p.agent_id for p in self._plans)
            agents.update(self._profiles.keys())
            total_agents = len(agents)

            # Sum record counts across all agents.
            total_readings = sum(len(r) for r in self._readings.values())
            total_resistances = sum(len(r) for r in self._resistances.values())
            total_snapshots = sum(len(s) for s in self._snapshots.values())
            total_thinnings = sum(len(s) for s in self._shears.values())

            # Average viscosity across all readings.
            viscosity_sum = 0.0
            reading_count = 0
            for readings in self._readings.values():
                for reading in readings:
                    viscosity_sum += reading.viscosity_score
                    reading_count += 1
            avg_viscosity = (
                round(viscosity_sum / reading_count, 4) if reading_count else 0.0
            )

            # Dominant regime across all snapshots.
            regime_counts: Dict[ViscosityRegime, int] = {}
            for snapshots in self._snapshots.values():
                for snapshot in snapshots:
                    regime_counts[snapshot.regime] = (
                        regime_counts.get(snapshot.regime, 0) + 1
                    )
            if regime_counts:
                dominant_regime = max(
                    regime_counts.items(), key=lambda kv: kv[1]
                )[0]
            elif reading_count:
                # No snapshots yet, but readings exist: derive the regime
                # from the average viscosity so the stats reflect real state.
                dominant_regime = _determine_regime(avg_viscosity)
            else:
                dominant_regime = ViscosityRegime.STANDARD

            return ViscosityStats(
                total_agents=total_agents,
                total_readings=total_readings,
                total_resistances=total_resistances,
                total_snapshots=total_snapshots,
                total_thinnings=total_thinnings,
                avg_viscosity=avg_viscosity,
                dominant_regime=dominant_regime,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_viscosity_engine: Optional[AgentCognitiveViscosity] = None
_viscosity_lock = threading.Lock()


def get_viscosity_engine() -> AgentCognitiveViscosity:
    """Get or create the singleton ``AgentCognitiveViscosity`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _viscosity_engine
    if _viscosity_engine is None:
        with _viscosity_lock:
            if _viscosity_engine is None:
                _viscosity_engine = AgentCognitiveViscosity()
    return _viscosity_engine


def reset_viscosity_engine() -> None:
    """Reset the singleton ``AgentCognitiveViscosity`` instance.

    Drops the reference so the next ``get_viscosity_engine`` call
    creates a fresh instance with empty stores. Useful for tests that
    need a clean engine state.
    """
    global _viscosity_engine
    with _viscosity_lock:
        _viscosity_engine = None