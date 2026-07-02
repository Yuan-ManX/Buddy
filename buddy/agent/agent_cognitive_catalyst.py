from __future__ import annotations

"""Agent Cognitive Catalyst Engine — catalytic elements that accelerate cognition

A catalyst lowers the activation energy for a reasoning move and is regenerated
rather than consumed — distinct from scaffolding (structural support).

Core capabilities:
  - Catalyst Registry: elements with selectivity, potency, and state
  - Catalysis Events: outcome, speedup, and duration per application
  - Activation Plans: deliberate state transitions with rationale
  - Potency Decay: fatigue tracking over time with reasons
  - Regime Classification: inert through prolific activity

Architecture:
  AgentCognitiveCatalyst (singleton)
  ├── CatalystEntry, CatalysisEvent, CatalysisSnapshot
  ├── ActivationPlan, DecayRecord, CatalystProfile
  └── CatalystStats
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
    """Generate a short unique identifier for a catalyst/event/plan/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` reading. A low-side default is safer
    than a mid-range one for catalyst-like quantities where a spurious
    high reading would suggest a catalyst is more potent than it is.
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
    against member values (e.g. ``"contextual"``) and then against member
    names (e.g. ``"CONTEXTUAL"``), so callers may pass either form. This
    lets the public API accept either the symbolic name or the lower-case
    value string from JSON payloads. Raises ``ValueError`` if neither
    matches.
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


def _determine_regime(
    active_count: int,
    avg_speedup: float,
) -> "CatalysisRegime":
    """Classify an agent's catalysis regime from activity and speedup.

    The regime partitions catalytic behavior into five qualitative bands.
    An agent with no active catalysts is INERT — no catalytic pathway is
    currently lowering any threshold. Once at least one catalyst is
    active, the regime is governed by the average speedup those catalysts
    deliver: below 1.2x the catalysis is SPORADIC (present but weak);
    below 1.5x it is MODERATE; below 2.0x it is ACTIVE; at 2.0x or above
    it is PROLIFIC, meaning the agent's catalytic layer is doing heavy
    work to lower the energy of its reasoning.

    The active count is checked first so an agent with active catalysts
    that have not yet produced events (and thus have a default speedup of
    1.0) still classifies as SPORADIC rather than INERT.
    """
    try:
        count = int(active_count)
    except (TypeError, ValueError):
        count = 0
    if count <= 0:
        return CatalysisRegime.INERT
    speedup = float(avg_speedup) if avg_speedup is not None else 1.0
    if speedup < 1.2:
        return CatalysisRegime.SPORADIC
    if speedup < 1.5:
        return CatalysisRegime.MODERATE
    if speedup < 2.0:
        return CatalysisRegime.ACTIVE
    return CatalysisRegime.PROLIFIC


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class CatalystType(str, Enum):
    """The kind of catalytic element.

    Each type describes a different locus at which a catalyst can lower
    the activation energy for cognitive moves. CONTEXTUAL catalysts are
    environmental contexts that make a class of operations natural.
    CONCEPTUAL catalysts are ideas or concepts that, once active, make
    related ideas easier to reach. FRAMING catalysts are perspectives or
    frames that open a reasoning path by recasting the problem.
    EMOTIONAL catalysts are affective states that lower the threshold for
    moves that flourish under that affect. SOCIAL catalysts are social or
    collaborative conditions that lower the energy for cooperative moves.
    ENVIRONMENTAL catalysts are physical or digital environmental
    conditions that lower the energy for moves suited to that
    environment.
    """
    CONTEXTUAL = "contextual"        # environmental context
    CONCEPTUAL = "conceptual"        # idea or concept
    FRAMING = "framing"              # perspective or frame
    EMOTIONAL = "emotional"          # affective state
    SOCIAL = "social"                # social/collaborative
    ENVIRONMENTAL = "environmental"  # physical/digital environment


class CatalysisOutcome(str, Enum):
    """The outcome of applying a catalyst to a target process.

    Outcomes range from strongly positive to strongly negative, because a
    catalyst can misfire: an element introduced to accelerate a process
    may instead inhibit it (the wrong framing slows reasoning down) or
    block it outright (an incompatible affective state prevents the move
    entirely). ACCELERATED means the catalyst produced a significant
    speedup. FACILITATED means it helped moderately. NEUTRAL means it had
    no measurable effect. INHIBITED means it slowed the process down.
    BLOCKED means it prevented the process from completing.
    """
    ACCELERATED = "accelerated"  # significant speedup
    FACILITATED = "facilitated"  # moderate help
    NEUTRAL = "neutral"           # no effect
    INHIBITED = "inhibited"      # slowed down
    BLOCKED = "blocked"           # prevented


class ActivationState(str, Enum):
    """The activation state of a catalyst.

    A catalyst moves through a lifecycle. DORMANT means the catalyst is
    registered but not active — it is available but not currently
    catalyzing anything. PRIMED means the catalyst is ready to activate,
    pre-loaded but not yet firing. ACTIVE means the catalyst is currently
    catalyzing, lowering the activation energy for its target process.
    SPENT means the catalyst is temporarily exhausted — it has catalyzed
    heavily and needs to refresh before it can fire again. DEACTIVATED
    means the catalyst has been deliberately turned off and will not fire
    until reactivated.
    """
    DORMANT = "dormant"        # not active
    PRIMED = "primed"          # ready to activate
    ACTIVE = "active"          # currently catalyzing
    SPENT = "spent"            # temporarily exhausted
    DEACTIVATED = "deactivated"  # turned off


class SelectivityLevel(str, Enum):
    """The specificity of a catalyst, mirroring enzyme specificity.

    Selectivity describes how narrow a catalyst's target set is. A BROAD
    catalyst lowers the activation energy for many reasoning paths at
    once — versatile but diffuse. A MODERATE catalyst targets a class of
    paths. A SPECIFIC catalyst targets a single path. An ULTRA_SPECIFIC
    catalyst targets one specific instance of a path, like an enzyme that
    binds a single substrate. High selectivity means precision but a
    narrow scope; low selectivity means versatility but a weaker effect on
    any one path.
    """
    BROAD = "broad"                  # catalyzes many paths
    MODERATE = "moderate"            # catalyzes a class of paths
    SPECIFIC = "specific"            # catalyzes one path
    ULTRA_SPECIFIC = "ultra_specific"  # catalyzes one specific instance


class CatalysisRegime(str, Enum):
    """The catalysis regime an agent occupies, classified by activity.

    A regime characterizes how catalytic the agent's cognition currently
    is. INERT means there is no catalytic activity — no catalyst is
    active, so no thresholds are being lowered. SPORADIC means catalysis
    is occasional and weak (below 1.2x average speedup). MODERATE means
    catalysis is regular but modest (below 1.5x). ACTIVE means catalysis
    is frequent and effective (below 2.0x). PROLIFIC means the agent is
    highly catalytic (2.0x or above), with the catalytic layer doing
    heavy work to accelerate its reasoning.
    """
    INERT = "inert"        # no catalytic activity
    SPORADIC = "sporadic"  # occasional catalysis
    MODERATE = "moderate"  # regular catalysis
    ACTIVE = "active"      # frequent effective catalysis
    PROLIFIC = "prolific"  # highly catalytic


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CatalystEntry:
    """One registered catalytic element.

    A catalyst entry is a single condition, context, prompt, or framing
    element that the agent has identified as capable of lowering the
    activation energy for a class of cognitive moves. ``catalyst_id``
    uniquely identifies this catalyst. ``agent_id`` is the agent that
    registered it. ``label`` is a human-readable name. ``catalyst_type``
    is the ``CatalystType`` describing the locus of the catalytic effect.
    ``selectivity`` is the ``SelectivityLevel`` describing how narrow the
    catalyst's target set is. ``activation_energy_reduction`` in [0, 1] is
    the fraction by which the catalyst lowers the threshold for its
    target — 0 means no reduction, 1 means the threshold is eliminated.
    ``state`` is the ``ActivationState`` of the catalyst. ``timestamp`` is
    when the catalyst was registered.
    """
    catalyst_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    label: str = ""
    catalyst_type: CatalystType = CatalystType.CONTEXTUAL
    selectivity: SelectivityLevel = SelectivityLevel.MODERATE
    activation_energy_reduction: float = 0.0
    state: ActivationState = ActivationState.DORMANT
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this catalyst to a plain dict, expanding the enums.

        Enums are converted to their ``.value`` strings so the serialized
        form is JSON-clean and unambiguous.
        """
        return {
            "catalyst_id": self.catalyst_id,
            "agent_id": self.agent_id,
            "label": self.label,
            "catalyst_type": _enum_value(CatalystType, self.catalyst_type),
            "selectivity": _enum_value(SelectivityLevel, self.selectivity),
            "activation_energy_reduction": self.activation_energy_reduction,
            "state": _enum_value(ActivationState, self.state),
            "timestamp": self.timestamp,
        }


@dataclass
class CatalysisEvent:
    """One application of a catalyst to a target process.

    An event records that a specific catalyst was applied to a specific
    target process, and what happened. ``event_id`` uniquely identifies
    this event. ``agent_id`` is the agent that applied the catalyst.
    ``catalyst_id`` is the catalyst that was applied. ``target_process``
    is a human-readable label for the cognitive process that was
    catalyzed (e.g. ``"hypothesis-generation"``, ``"analogy-retrieval"``).
    ``outcome`` is the ``CatalysisOutcome``. ``speedup_factor`` is the
    ratio of the uncatalyzed duration to the catalyzed duration: 1.0
    means no change, 2.0 means twice as fast, 0.5 means twice as slow.
    ``duration`` is how long the catalyzed process took, in seconds.
    ``timestamp`` is when the event was recorded.
    """
    event_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    catalyst_id: str = ""
    target_process: str = ""
    outcome: CatalysisOutcome = CatalysisOutcome.NEUTRAL
    speedup_factor: float = 1.0
    duration: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a plain dict, expanding the enum."""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "catalyst_id": self.catalyst_id,
            "target_process": self.target_process,
            "outcome": _enum_value(CatalysisOutcome, self.outcome),
            "speedup_factor": self.speedup_factor,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }


@dataclass
class CatalysisSnapshot:
    """A point-in-time aggregate of an agent's catalytic activity.

    A snapshot summarizes the agent's recent catalytic activity at the
    moment it was taken. ``snapshot_id`` uniquely identifies this
    snapshot. ``agent_id`` is the agent the snapshot summarizes.
    ``regime`` is the ``CatalysisRegime`` derived from the active count
    and average speedup via ``_determine_regime``. ``active_count`` is the
    number of the agent's catalysts currently in the ACTIVE state.
    ``avg_speedup`` is the mean ``speedup_factor`` across the agent's
    recent catalysis events (the last 20), or 1.0 if there are none.
    ``dominant_type`` is the ``CatalystType`` that appears most often
    among the agent's catalysts, or ``None`` if the agent has no
    catalysts. ``total_events`` is the agent's total catalysis event count
    at snapshot time. ``timestamp`` is when the snapshot was taken.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    regime: CatalysisRegime = CatalysisRegime.INERT
    active_count: int = 0
    avg_speedup: float = 1.0
    dominant_type: Optional[CatalystType] = None
    total_events: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding the enums.

        The optional ``dominant_type`` is emitted as ``None`` when absent
        and as its enum ``.value`` otherwise, so the serialized form is
        JSON-clean and unambiguous.
        """
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "regime": _enum_value(CatalysisRegime, self.regime),
            "active_count": self.active_count,
            "avg_speedup": self.avg_speedup,
            "dominant_type": (
                _enum_value(CatalystType, self.dominant_type)
                if self.dominant_type is not None
                else None
            ),
            "total_events": self.total_events,
            "timestamp": self.timestamp,
        }


@dataclass
class ActivationPlan:
    """A plan to transition a catalyst to a target activation state.

    When the agent (or its orchestrator) decides to deliberately move a
    catalyst from one activation state to another — to prime a dormant
    catalyst, to activate a primed one, to refresh a spent one, or to
    deactivate an active one — an activation plan records that decision.
    ``plan_id`` uniquely identifies this plan. ``agent_id`` is the agent
    the plan is for. ``catalyst_id`` is the catalyst whose state is to
    change. ``target_state`` is the ``ActivationState`` the catalyst
    should move to. ``rationale`` is a free-form explanation of why the
    transition is being made. ``expected_effect`` in [0, 1] is the
    predicted magnitude of the transition's effect — a prediction, not a
    measurement, that can be compared against later outcomes to
    calibrate the plan's effectiveness. ``timestamp`` is when the plan was
    created.
    """
    plan_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    catalyst_id: str = ""
    target_state: ActivationState = ActivationState.ACTIVE
    rationale: str = ""
    expected_effect: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this plan to a plain dict, expanding the enum."""
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "catalyst_id": self.catalyst_id,
            "target_state": _enum_value(ActivationState, self.target_state),
            "rationale": self.rationale,
            "expected_effect": self.expected_effect,
            "timestamp": self.timestamp,
        }


@dataclass
class DecayRecord:
    """A recorded loss of a catalyst's potency.

    Catalysts are not consumed by catalyzing — the same catalyst can
    fire many times — but they can fatigue. A decay record captures a
    single drop in a catalyst's potency. ``record_id`` uniquely identifies
    this record. ``agent_id`` is the agent that owns the catalyst.
    ``catalyst_id`` is the catalyst whose potency changed.
    ``from_potency`` in [0, 1] is the potency before the decay.
    ``to_potency`` in [0, 1] is the potency after. ``delta`` is
    ``to_potency - from_potency`` and is zero or negative for a decay
    (a positive delta would indicate a recovery, not a decay, but the
    record stores the raw delta so the direction is always legible).
    ``reason`` is a human-readable explanation of why the potency
    dropped (e.g. ``"overuse"``, ``"context-shift"``, ``"saturation"``).
    ``timestamp`` is when the decay was recorded.
    """
    record_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    catalyst_id: str = ""
    from_potency: float = 0.0
    to_potency: float = 0.0
    delta: float = 0.0
    reason: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this decay record to a plain dict."""
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "catalyst_id": self.catalyst_id,
            "from_potency": self.from_potency,
            "to_potency": self.to_potency,
            "delta": self.delta,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class CatalystProfile:
    """Per-agent aggregate catalytic posture.

    A profile summarizes one agent's catalytic behavior. ``agent_id`` is
    the agent this profile describes. ``total_catalysts`` is the count of
    catalysts registered for the agent. ``active_catalysts`` is the count
    currently in the ACTIVE state. ``avg_speedup`` is the mean
    ``speedup_factor`` across the agent's catalysis events (1.0 when
    there are none). ``dominant_type`` is the ``CatalystType`` that
    appears most often among the agent's catalysts, or ``None`` when the
    agent has no catalysts. ``regime`` is the ``CatalysisRegime`` derived
    from the active count and average speedup. ``last_updated`` records
    when the profile was last refreshed.
    """
    agent_id: str = ""
    total_catalysts: int = 0
    active_catalysts: int = 0
    avg_speedup: float = 1.0
    dominant_type: Optional[CatalystType] = None
    regime: CatalysisRegime = CatalysisRegime.INERT
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding the enums.

        The optional ``dominant_type`` is emitted as ``None`` when absent
        and as its enum ``.value`` otherwise, so the serialized form is
        JSON-clean and unambiguous.
        """
        return {
            "agent_id": self.agent_id,
            "total_catalysts": self.total_catalysts,
            "active_catalysts": self.active_catalysts,
            "avg_speedup": self.avg_speedup,
            "dominant_type": (
                _enum_value(CatalystType, self.dominant_type)
                if self.dominant_type is not None
                else None
            ),
            "regime": _enum_value(CatalysisRegime, self.regime),
            "last_updated": self.last_updated,
        }


@dataclass
class CatalystStats:
    """Engine-wide aggregate statistics across all agents and catalysts.

    Scalar totals are the rolling counts of each record type the engine
    stores. ``regime_distribution`` tallies the currently held snapshots
    by regime. ``type_distribution`` tallies the currently held catalysts
    by type. ``outcome_distribution`` tallies the currently held events by
    outcome. ``avg_speedup`` is the mean ``speedup_factor`` across all
    catalysis events, or 1.0 when no events exist. The breakdown dicts
    are keyed by enum ``.value`` strings so the stats serialize cleanly
    to JSON.
    """
    total_catalysts: int = 0
    total_events: int = 0
    total_snapshots: int = 0
    total_plans: int = 0
    total_decays: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    type_distribution: Dict[str, int] = field(default_factory=dict)
    outcome_distribution: Dict[str, int] = field(default_factory=dict)
    avg_speedup: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict.

        The distribution dicts are already keyed by ``str`` (the
        ``.value`` of each enum), so they are copied verbatim; no further
        enum expansion is needed.
        """
        return {
            "total_catalysts": self.total_catalysts,
            "total_events": self.total_events,
            "total_snapshots": self.total_snapshots,
            "total_plans": self.total_plans,
            "total_decays": self.total_decays,
            "regime_distribution": dict(self.regime_distribution),
            "type_distribution": dict(self.type_distribution),
            "outcome_distribution": dict(self.outcome_distribution),
            "avg_speedup": self.avg_speedup,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveCatalyst:
    """Thread-safe engine that identifies, applies, and tracks cognitive catalysts.

    The engine holds seven stores keyed by identifier:

      * ``_catalysts``  — CatalystEntry by catalyst_id
      * ``_events``     — CatalysisEvent by event_id
      * ``_snapshots``  — CatalysisSnapshot by snapshot_id
      * ``_plans``      — ActivationPlan by plan_id
      * ``_decays``     — DecayRecord by record_id
      * ``_profiles``   — CatalystProfile by agent_id
      * ``_stats``      — rolling counters for fast aggregate reads

    All mutations are guarded by a single reentrant lock so that public
    methods may safely call one another without self-deadlock. The
    catalysis model is deliberately heuristic: activation energy
    reductions, speedup factors, and potency values are caller-supplied
    readings, regimes are banded from aggregate activity, and dominant
    types are computed by mode. These heuristics are transparent and
    auditable rather than learned, which keeps the engine deterministic
    and easy to reason about.

    The engine is intentionally agnostic about how speedup factors and
    activation energy reductions are produced. Callers may derive them
    from timing measurements, from self-reports, from observed behavioral
    changes, or from any other source. The engine's job is to record,
    aggregate, classify, and plan — not to measure catalysis itself.

    The engine treats catalysts as regenerative rather than consumable.
    A catalyst that fires is not destroyed; it can fire again. Catalysts
    can fatigue (tracked via decay records) and can be deliberately
    transitioned between activation states (tracked via activation plans),
    but the default expectation is that a catalyst remains available after
    use. This regenerative property is what makes catalysis distinct from
    resource consumption: the catalyst lowers the energy of a move without
    paying for the move itself.
    """

    # Number of most-recent catalysis events that contribute to a
    # snapshot's average speedup. The window is long enough to smooth out
    # a single noisy reading and short enough to reflect the agent's
    # current catalytic behavior.
    _SNAPSHOT_EVENT_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty catalyst engine with fresh stores and counters."""
        self._lock = threading.RLock()
        self._catalysts: Dict[str, CatalystEntry] = {}
        self._events: Dict[str, CatalysisEvent] = {}
        self._snapshots: Dict[str, CatalysisSnapshot] = {}
        self._plans: Dict[str, ActivationPlan] = {}
        self._decays: Dict[str, DecayRecord] = {}
        self._profiles: Dict[str, CatalystProfile] = {}
        # Rolling counters kept in sync with the stores above. They mirror
        # the lengths of the primary stores and let get_stats() avoid full
        # scans for the scalar totals; distributions are still computed by
        # scanning so they always reflect the current state even after
        # out-of-band mutations.
        self._stats: Dict[str, int] = {
            "total_catalysts": 0,
            "total_events": 0,
            "total_snapshots": 0,
            "total_plans": 0,
            "total_decays": 0,
        }
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_catalysts_locked(self, agent_id: str) -> List[CatalystEntry]:
        """Return one agent's catalysts in insertion order. Caller holds the lock."""
        return [c for c in self._catalysts.values() if c.agent_id == agent_id]

    def _agent_events_locked(self, agent_id: str) -> List[CatalysisEvent]:
        """Return one agent's catalysis events in insertion order. Caller holds the lock."""
        return [e for e in self._events.values() if e.agent_id == agent_id]

    def _mode_type_locked(
        self, catalysts: List[CatalystEntry]
    ) -> Optional[CatalystType]:
        """Return the most frequent catalyst type among the supplied catalysts.

        Ties are broken by insertion order (the first type to reach the
        winning count wins, because ``dict`` preserves insertion order and
        ``max`` returns the first maximal item). Returns ``None`` if the
        list is empty.
        """
        if not catalysts:
            return None
        counts: Dict[CatalystType, int] = {}
        for catalyst in catalysts:
            counts[catalyst.catalyst_type] = counts.get(catalyst.catalyst_type, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    # ── Catalysts ──────────────────────────────────────────────────

    def register_catalyst(
        self,
        agent_id: str,
        label: str,
        catalyst_type: Any,
        selectivity: Any,
        activation_energy_reduction: float,
        state: ActivationState = ActivationState.DORMANT,
    ) -> CatalystEntry:
        """Register a single catalytic element for ``agent_id`` and return it.

        A catalyst is a condition, context, prompt, or framing element
        that lowers the activation energy for a class of cognitive moves.
        ``catalyst_type`` may be passed as a ``CatalystType`` member or
        its string name/value (e.g. ``"CONTEXTUAL"`` or ``"contextual"``).
        ``selectivity`` may be passed as a ``SelectivityLevel`` member or
        its string name/value. ``activation_energy_reduction`` in [0, 1]
        is the fraction by which the catalyst lowers the threshold for its
        target, clamped to that range. ``state`` is the catalyst's initial
        ``ActivationState`` and defaults to DORMANT. The catalyst is
        timestamped, stored, counted, and returned.
        """
        with self._lock:
            entry = CatalystEntry(
                agent_id=agent_id,
                label=str(label),
                catalyst_type=_resolve_enum(CatalystType, catalyst_type),
                selectivity=_resolve_enum(SelectivityLevel, selectivity),
                activation_energy_reduction=_clamp(activation_energy_reduction, 0.0, 1.0),
                state=_resolve_enum(ActivationState, state),
                timestamp=_now(),
            )
            self._catalysts[entry.catalyst_id] = entry
            self._stats["total_catalysts"] += 1
            # A new catalyst changes the agent's catalytic picture, so
            # invalidate any cached profile so the next access recomputes
            # from the fresh catalyst set.
            self._profiles.pop(agent_id, None)
            return entry

    def list_catalysts(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CatalystEntry]:
        """Return catalysts, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all catalysts are considered;
        otherwise only catalysts for that agent are returned. The most
        recently registered ``limit`` catalysts are returned (insertion
        order is chronological, so the tail is the most recent). The
        returned list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            catalysts = list(self._catalysts.values())
        if agent_id is not None:
            catalysts = [c for c in catalysts if c.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return catalysts[-n:] if n else []

    def get_catalyst(self, catalyst_id: str) -> Optional[CatalystEntry]:
        """Retrieve a catalyst by id, or ``None`` if absent."""
        with self._lock:
            return self._catalysts.get(catalyst_id)

    # ── Catalysis Events ───────────────────────────────────────────

    def record_event(
        self,
        agent_id: str,
        catalyst_id: str,
        target_process: str,
        outcome: Any,
        speedup_factor: float,
        duration: float,
    ) -> CatalysisEvent:
        """Record a single catalysis event for an agent and return it.

        ``catalyst_id`` is the catalyst that was applied.
        ``target_process`` is a human-readable label for the cognitive
        process that was catalyzed. ``outcome`` may be passed as a
        ``CatalysisOutcome`` member or its string name/value.
        ``speedup_factor`` is the ratio of uncatalyzed to catalyzed
        duration: 1.0 means no change, 2.0 means twice as fast, 0.5 means
        twice as slow. ``duration`` is how long the catalyzed process
        took, in seconds, coerced to a non-negative float. The event is
        timestamped, stored, counted, and returned; the agent's cached
        profile is invalidated so the next access recomputes from fresh
        data.
        """
        with self._lock:
            try:
                dur = float(duration)
            except (TypeError, ValueError):
                dur = 0.0
            if dur < 0.0:
                dur = 0.0
            try:
                speedup = float(speedup_factor)
            except (TypeError, ValueError):
                speedup = 1.0
            event = CatalysisEvent(
                agent_id=agent_id,
                catalyst_id=str(catalyst_id),
                target_process=str(target_process),
                outcome=_resolve_enum(CatalysisOutcome, outcome),
                speedup_factor=speedup,
                duration=dur,
                timestamp=_now(),
            )
            self._events[event.event_id] = event
            self._stats["total_events"] += 1
            self._profiles.pop(agent_id, None)
            return event

    def list_events(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CatalysisEvent]:
        """Return catalysis events, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all events are considered; otherwise
        only events for that agent are returned. The most recently recorded
        ``limit`` events are returned. The returned list is a snapshot
        copy; mutating it does not affect the engine.
        """
        with self._lock:
            events = list(self._events.values())
        if agent_id is not None:
            events = [e for e in events if e.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return events[-n:] if n else []

    def get_event(self, event_id: str) -> Optional[CatalysisEvent]:
        """Retrieve a catalysis event by id, or ``None`` if absent."""
        with self._lock:
            return self._events.get(event_id)

    # ── Snapshots ──────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> CatalysisSnapshot:
        """Aggregate an agent's recent catalytic activity into a snapshot.

        Collects every catalyst and catalysis event currently registered
        for the agent. ``active_count`` is the number of the agent's
        catalysts currently in the ACTIVE state. ``avg_speedup`` is the
        mean ``speedup_factor`` across the agent's most recent catalysis
        events (the last ``_SNAPSHOT_EVENT_WINDOW`` = 20), or 1.0 if the
        agent has no events. ``dominant_type`` is the most frequent
        ``CatalystType`` among the agent's catalysts, or ``None`` if the
        agent has no catalysts. ``total_events`` is the agent's total
        catalysis event count at snapshot time. ``regime`` is derived from
        the active count and average speedup via ``_determine_regime``.
        The snapshot is stored, counted, and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            agent_catalysts = self._agent_catalysts_locked(agent_id)
            agent_events = self._agent_events_locked(agent_id)
            recent = agent_events[-self._SNAPSHOT_EVENT_WINDOW:]

            active_count = sum(
                1 for c in agent_catalysts if c.state == ActivationState.ACTIVE
            )
            if recent:
                avg_speedup = sum(e.speedup_factor for e in recent) / len(recent)
            else:
                avg_speedup = 1.0
            dominant_type = self._mode_type_locked(agent_catalysts)
            regime = _determine_regime(active_count, avg_speedup)

            snapshot = CatalysisSnapshot(
                agent_id=agent_id,
                regime=regime,
                active_count=active_count,
                avg_speedup=round(avg_speedup, 4),
                dominant_type=dominant_type,
                total_events=len(agent_events),
                timestamp=_now(),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._stats["total_snapshots"] += 1
            self._profiles.pop(agent_id, None)
            return snapshot

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[CatalysisSnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The most
        recently taken ``limit`` snapshots are returned. The returned list
        is a snapshot copy; mutating it does not affect the engine.
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

    def get_snapshot(self, snapshot_id: str) -> Optional[CatalysisSnapshot]:
        """Retrieve a snapshot by id, or ``None`` if absent."""
        with self._lock:
            return self._snapshots.get(snapshot_id)

    # ── Activation Plans ───────────────────────────────────────────

    def plan_activation(
        self,
        agent_id: str,
        catalyst_id: str,
        target_state: Any,
        rationale: str,
        expected_effect: float,
    ) -> ActivationPlan:
        """Create an activation plan for a catalyst and return it.

        ``catalyst_id`` is the catalyst whose activation state is to
        change. ``target_state`` may be passed as an ``ActivationState``
        member or its string name/value. ``rationale`` is a free-form
        explanation of why the transition is being made. ``expected_effect``
        in [0, 1] is the predicted magnitude of the transition's effect,
        clamped to that range. The plan is timestamped, stored, counted,
        and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            plan = ActivationPlan(
                agent_id=agent_id,
                catalyst_id=str(catalyst_id),
                target_state=_resolve_enum(ActivationState, target_state),
                rationale=str(rationale),
                expected_effect=_clamp(expected_effect, 0.0, 1.0),
                timestamp=_now(),
            )
            self._plans[plan.plan_id] = plan
            self._stats["total_plans"] += 1
            self._profiles.pop(agent_id, None)
            return plan

    def list_plans(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ActivationPlan]:
        """Return activation plans, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all plans are considered; otherwise
        only plans for that agent are returned. The most recently created
        ``limit`` plans are returned. The returned list is a snapshot
        copy; mutating it does not affect the engine.
        """
        with self._lock:
            plans = list(self._plans.values())
        if agent_id is not None:
            plans = [p for p in plans if p.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return plans[-n:] if n else []

    def get_plan(self, plan_id: str) -> Optional[ActivationPlan]:
        """Retrieve an activation plan by id, or ``None`` if absent."""
        with self._lock:
            return self._plans.get(plan_id)

    # ── Decay Records ──────────────────────────────────────────────

    def record_decay(
        self,
        agent_id: str,
        catalyst_id: str,
        from_potency: float,
        to_potency: float,
        reason: str,
    ) -> DecayRecord:
        """Record a single loss of a catalyst's potency and return it.

        ``catalyst_id`` is the catalyst whose potency changed.
        ``from_potency`` in [0, 1] is the potency before the decay.
        ``to_potency`` in [0, 1] is the potency after. Both are clamped
        to that range. ``delta`` is computed as
        ``to_potency - from_potency`` and is zero or negative for a decay
        (a positive delta would indicate a recovery, but the raw delta is
        stored so the direction is always legible). ``reason`` is a
        human-readable explanation of why the potency dropped. The record
        is timestamped, stored, counted, and returned; the agent's cached
        profile is invalidated.
        """
        with self._lock:
            from_p = _clamp(from_potency, 0.0, 1.0)
            to_p = _clamp(to_potency, 0.0, 1.0)
            delta = round(to_p - from_p, 4)
            record = DecayRecord(
                agent_id=agent_id,
                catalyst_id=str(catalyst_id),
                from_potency=from_p,
                to_potency=to_p,
                delta=delta,
                reason=str(reason),
                timestamp=_now(),
            )
            self._decays[record.record_id] = record
            self._stats["total_decays"] += 1
            self._profiles.pop(agent_id, None)
            return record

    def list_decays(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DecayRecord]:
        """Return decay records, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all records are considered;
        otherwise only records for that agent are returned. The most
        recently recorded ``limit`` records are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            decays = list(self._decays.values())
        if agent_id is not None:
            decays = [d for d in decays if d.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return decays[-n:] if n else []

    def get_decay(self, record_id: str) -> Optional[DecayRecord]:
        """Retrieve a decay record by id, or ``None`` if absent."""
        with self._lock:
            return self._decays.get(record_id)

    # ── Profiles ───────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> CatalystProfile:
        """Return the agent's catalyst profile, computing it if absent.

        The profile is a snapshot computed from the current stores. It is
        cached on the agent_id and invalidated whenever the agent's
        catalysts, events, snapshots, plans, or decays change. Call
        ``update_profile`` to force a refresh after out-of-band changes,
        or to override a computed field with a caller-supplied value.

        ``total_catalysts`` is the count of catalysts registered for the
        agent. ``active_catalysts`` is the count currently in the ACTIVE
        state. ``avg_speedup`` is the mean ``speedup_factor`` across the
        agent's catalysis events (1.0 when there are none).
        ``dominant_type`` is the most frequent ``CatalystType`` among the
        agent's catalysts, or ``None`` when the agent has no catalysts.
        ``regime`` is derived from the active count and average speedup
        via ``_determine_regime``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> CatalystProfile:
        """Refresh and optionally override fields of an agent's catalyst profile.

        The profile is first recomputed from the live stores, then any
        supplied keyword overrides (matching ``CatalystProfile`` field
        names) are applied, and finally ``last_updated`` is stamped. This
        is the supported way to force a profile refresh after out-of-band
        changes, and the supported way to override a computed field with a
        caller-supplied value.

        Accepted overrides: ``total_catalysts``, ``active_catalysts``
        (coerced to int), ``avg_speedup`` (coerced to float),
        ``dominant_type`` (a ``CatalystType`` or its string name/value, or
        ``None`` to clear), and ``regime`` (a ``CatalysisRegime`` or its
        string name/value). Unknown keys are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key in ("total_catalysts", "active_catalysts"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
                elif key == "avg_speedup":
                    try:
                        profile.avg_speedup = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_type":
                    if value is None:
                        profile.dominant_type = None
                    else:
                        try:
                            profile.dominant_type = _resolve_enum(CatalystType, value)
                        except ValueError:
                            pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(CatalysisRegime, value)
                    except ValueError:
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[CatalystProfile]:
        """Return all stored catalyst profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics & Maintenance ────────────────────────────────────

    def get_stats(self) -> CatalystStats:
        """Compute engine-wide aggregate statistics.

        Scalar totals are read from the rolling ``_stats`` counters (which
        stay in sync with the primary stores). ``regime_distribution``
        tallies the currently held snapshots by regime.
        ``type_distribution`` tallies the currently held catalysts by
        type. ``outcome_distribution`` tallies the currently held events
        by outcome. ``avg_speedup`` is the mean ``speedup_factor`` across
        all catalysis events, or 1.0 when no events exist. Distributions
        are keyed by the ``.value`` string of each enum so the result is
        JSON-serializable.
        """
        with self._lock:
            regime_dist: Dict[str, int] = {}
            for snap in self._snapshots.values():
                key = _enum_value(CatalysisRegime, snap.regime)
                regime_dist[key] = regime_dist.get(key, 0) + 1

            outcome_dist: Dict[str, int] = {}
            speedup_sum = 0.0
            for event in self._events.values():
                key = _enum_value(CatalysisOutcome, event.outcome)
                outcome_dist[key] = outcome_dist.get(key, 0) + 1
                speedup_sum += event.speedup_factor

            type_dist: Dict[str, int] = {}
            for catalyst in self._catalysts.values():
                key = _enum_value(CatalystType, catalyst.catalyst_type)
                type_dist[key] = type_dist.get(key, 0) + 1

            event_count = len(self._events)
            avg_speedup = (
                round(speedup_sum / event_count, 4) if event_count else 1.0
            )

            return CatalystStats(
                total_catalysts=self._stats["total_catalysts"],
                total_events=self._stats["total_events"],
                total_snapshots=self._stats["total_snapshots"],
                total_plans=self._stats["total_plans"],
                total_decays=self._stats["total_decays"],
                regime_distribution=regime_dist,
                type_distribution=type_dist,
                outcome_distribution=outcome_dist,
                avg_speedup=avg_speedup,
            )

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store and zeroes every rolling counter. The
        singleton reference is not touched; callers that want a fresh
        singleton should use ``reset_catalyst_engine`` instead.
        """
        with self._lock:
            self._catalysts.clear()
            self._events.clear()
            self._snapshots.clear()
            self._plans.clear()
            self._decays.clear()
            self._profiles.clear()
            self._stats["total_catalysts"] = 0
            self._stats["total_events"] = 0
            self._stats["total_snapshots"] = 0
            self._stats["total_plans"] = 0
            self._stats["total_decays"] = 0

    # ── Internal profile computation (caller must hold the lock) ────

    def _compute_profile_locked(self, agent_id: str) -> CatalystProfile:
        """Aggregate an agent's catalysts and events into a profile.

        ``total_catalysts`` is the count of catalysts registered for the
        agent. ``active_catalysts`` is the count currently in the ACTIVE
        state. ``avg_speedup`` is the mean ``speedup_factor`` across the
        agent's catalysis events (1.0 when there are none).
        ``dominant_type`` is the most frequent ``CatalystType`` among the
        agent's catalysts, or ``None`` when the agent has no catalysts.
        ``regime`` is derived from the active count and average speedup
        via ``_determine_regime``. Caller holds the lock.
        """
        agent_catalysts = self._agent_catalysts_locked(agent_id)
        agent_events = self._agent_events_locked(agent_id)

        total_catalysts = len(agent_catalysts)
        active_catalysts = sum(
            1 for c in agent_catalysts if c.state == ActivationState.ACTIVE
        )
        if agent_events:
            avg_speedup = sum(e.speedup_factor for e in agent_events) / len(agent_events)
        else:
            avg_speedup = 1.0
        dominant_type = self._mode_type_locked(agent_catalysts)
        regime = _determine_regime(active_catalysts, avg_speedup)

        return CatalystProfile(
            agent_id=agent_id,
            total_catalysts=total_catalysts,
            active_catalysts=active_catalysts,
            avg_speedup=round(avg_speedup, 4),
            dominant_type=dominant_type,
            regime=regime,
            last_updated=_now(),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveCatalyst] = None
_engine_lock = threading.Lock()


def get_catalyst_engine() -> AgentCognitiveCatalyst:
    """Get or create the singleton ``AgentCognitiveCatalyst`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveCatalyst()
        return _engine


def reset_catalyst_engine() -> None:
    """Reset the singleton ``AgentCognitiveCatalyst`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_catalyst_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
