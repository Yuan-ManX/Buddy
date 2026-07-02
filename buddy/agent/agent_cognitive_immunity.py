from __future__ import annotations

"""Agent Cognitive Immunity Engine — modeling the cognitive immune system

How an agent identifies, neutralizes, and rejects harmful or contradictory
information. Like biological immunity, it recognizes threats, mounts responses,
remembers past encounters, and maintains tolerance to avoid auto-immunity.
Distinct from alignment, belief-state, and coherence.
Core capabilities: threat detection, immune response, tolerance, memory.

Architecture:
  AgentCognitiveImmunity (singleton)
  ├── ThreatDetection       (one identified cognitive threat)
  ├── ImmuneAction          (one response to a detection)
  ├── ImmunitySnapshot      (aggregate immune activity for one agent)
  ├── ToleranceAssessment   (a measurement of tolerance posture)
  ├── MemoryEntry           (immune memory for one threat type)
  ├── ImmunityProfile       (per-agent aggregate immune tendencies)
  └── ImmunityStats         (engine-wide aggregate statistics)
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
    """Generate a short unique identifier for a detection/action/snapshot/etc.

    The identifier is the first eight characters of a UUID4, short enough
    to be readable in logs and long enough that collisions are negligible
    for an in-memory engine.
    """
    return str(uuid.uuid4())[:8]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high].

    Non-numeric input is coerced to ``low`` so callers cannot poison the
    engine with a ``NaN`` or ``None`` severity. A low-side default is safer
    than a mid-range one for threat-like quantities where a spurious high
    reading would inflate the perceived threat.
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
    against member values (e.g. ``"contradiction"``) and then against
    member names (e.g. ``"CONTRADICTION"``), so callers may pass either
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


def _determine_regime(
    active_threats: int,
    neutralized_ratio: float,
    false_positive_rate: float,
) -> "ImmunityRegime":
    """Classify an agent's immune regime from threat and response data.

    The checks are applied in order, so the first matching rule wins:
    false-positive rate above 0.5 → HYPERACTIVE (over-reacting);
    neutralized ratio below 0.3 → COMPROMISED (weak defense); below 0.5
    → SLUGGISH (slow response); active threats above 10 → HYPERACTIVE
    (overwhelmed); neutralized ratio above 0.8 → ROBUST; otherwise
    VIGILANT. False-positive rate is checked first because over-reaction
    is the most acute failure mode.
    """
    fpr = _clamp(false_positive_rate, 0.0, 1.0)
    nr = _clamp(neutralized_ratio, 0.0, 1.0)
    try:
        at = int(active_threats)
    except (TypeError, ValueError):
        at = 0
    if fpr > 0.5:
        return ImmunityRegime.HYPERACTIVE
    if nr < 0.3:
        return ImmunityRegime.COMPROMISED
    if nr < 0.5:
        return ImmunityRegime.SLUGGISH
    if at > 10:
        return ImmunityRegime.HYPERACTIVE
    if nr > 0.8:
        return ImmunityRegime.ROBUST
    return ImmunityRegime.VIGILANT


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ThreatType(str, Enum):
    """The kind of cognitive threat an input poses.

    Each type describes a different way an input can be harmful to the
    agent's cognition. See the module docstring for the full description
    of each type; the inline comment on each member is a short label.
    """
    CONTRADICTION = "contradiction"        # contradicts core beliefs
    MANIPULATION = "manipulation"          # attempts to manipulate
    MISINFORMATION = "misinformation"      # false information
    COGNITIVE_OVERLOAD = "cognitive_overload"  # overwhelming input
    PARASITIC = "parasitic"                # exploits cognitive resources
    CORRUPTION = "corruption"              # degrades cognitive integrity
    ALIEN = "alien"                        # incompatible framework


class ImmuneResponse(str, Enum):
    """The response the immune system mounts to a detected threat.

    Responses range from passive dismissal (IGNORE) through review
    (FLAG), isolation (QUARANTINE), and active counteraction
    (NEUTRALIZE) to outright blocking (REJECT). ASSIMILATE incorporates
    the input after processing when an apparent threat turns out to be
    beneficial.
    """
    IGNORE = "ignore"          # dismissed as harmless
    FLAG = "flag"              # marked for review
    QUARANTINE = "quarantine"  # isolated for analysis
    NEUTRALIZE = "neutralize"  # actively counteracted
    REJECT = "reject"          # blocked entirely
    ASSIMILATE = "assimilate"  # incorporated after processing


class ImmunityRegime(str, Enum):
    """The immune regime an agent occupies, classified by its defenses.

    Ranges from COMPROMISED (weak defense, threats rarely neutralized)
    through SLUGGISH (slow response), VIGILANT (healthy monitoring),
    and HYPERACTIVE (over-reacting, too many false positives) to ROBUST
    (strong and balanced).
    """
    COMPROMISED = "compromised"  # weak defense
    SLUGGISH = "sluggish"        # slow response
    VIGILANT = "vigilant"        # healthy monitoring
    HYPERACTIVE = "hyperactive"  # over-reacting
    ROBUST = "robust"            # strong and balanced


class ToleranceLevel(str, Enum):
    """The tolerance posture of an agent's immune system.

    Tolerance is the complement of vigilance: too little attacks
    everything (including self, via AUTO_IMMUNE); too much attacks
    nothing, leaving the agent undefended. NONE through HIGH range from
    strict to permissive; MODERATE is the balanced default.
    """
    NONE = "none"                # no tolerance
    LOW = "low"                  # strict
    MODERATE = "moderate"        # balanced
    HIGH = "high"                # permissive
    AUTO_IMMUNE = "auto_immune"  # attacking self


class MemoryState(str, Enum):
    """The state of an agent's immune memory for one threat type.

    Immune memory moves through a lifecycle: NAIVE (never encountered),
    PRIMED (seen once, sensitized), ACTIVE (recently responded,
    mobilized), MEMORY (long-term protection from repeated encounters),
    and EXHAUSTED (temporarily depleted from over-use).
    """
    NAIVE = "naive"        # never encountered
    PRIMED = "primed"      # seen once
    ACTIVE = "active"      # recently responded
    MEMORY = "memory"      # long-term protection
    EXHAUSTED = "exhausted"  # temporarily depleted


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ThreatDetection:
    """One identified cognitive threat.

    ``threat_type`` classifies the threat; ``severity`` in [0, 1] is its
    magnitude (0 harmless, 1 maximally dangerous). ``source`` labels
    where the threat came from; ``evidence`` explains why the input was
    flagged.
    """
    detection_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    threat_type: ThreatType = ThreatType.MISINFORMATION
    source: str = ""
    severity: float = 0.0
    evidence: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this detection to a plain dict, expanding enums via ``.value``."""
        return {
            "detection_id": self.detection_id,
            "agent_id": self.agent_id,
            "threat_type": _enum_value(ThreatType, self.threat_type),
            "source": self.source,
            "severity": self.severity,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class ImmuneAction:
    """One immune response to a detected threat.

    ``detection_id`` links the action to its triggering
    ``ThreatDetection``. ``response`` is the ``ImmuneResponse`` mounted.
    ``neutralization_method`` describes how the threat was neutralized
    (empty for passive responses like IGNORE). ``success`` is whether the
    response achieved its goal.
    """
    action_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    detection_id: str = ""
    response: ImmuneResponse = ImmuneResponse.IGNORE
    rationale: str = ""
    neutralization_method: str = ""
    success: bool = False
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this action to a plain dict, expanding enums via ``.value``."""
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "detection_id": self.detection_id,
            "response": _enum_value(ImmuneResponse, self.response),
            "rationale": self.rationale,
            "neutralization_method": self.neutralization_method,
            "success": self.success,
            "timestamp": self.timestamp,
        }


@dataclass
class ImmunitySnapshot:
    """A point-in-time aggregate of an agent's immune activity.

    ``regime`` is derived via ``_determine_regime`` from the active
    threat count, neutralized ratio, and false-positive rate.
    ``tolerance`` is from the agent's most recent tolerance assessment,
    or MODERATE if none exists. ``avg_severity`` is the mean severity
    across the agent's detections, or 0.0 if none.
    """
    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    regime: ImmunityRegime = ImmunityRegime.VIGILANT
    tolerance: ToleranceLevel = ToleranceLevel.MODERATE
    active_threats: int = 0
    neutralized_count: int = 0
    memory_count: int = 0
    avg_severity: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a plain dict, expanding enums via ``.value``."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "regime": _enum_value(ImmunityRegime, self.regime),
            "tolerance": _enum_value(ToleranceLevel, self.tolerance),
            "active_threats": self.active_threats,
            "neutralized_count": self.neutralized_count,
            "memory_count": self.memory_count,
            "avg_severity": self.avg_severity,
            "timestamp": self.timestamp,
        }


@dataclass
class ToleranceAssessment:
    """A measurement of an agent's tolerance posture.

    ``level`` is the assigned ``ToleranceLevel``. ``false_positive_rate``
    in [0, 1] is the fraction of responses that dismissed inputs as
    harmless (IGNORE) — high values mean over-flagging.
    ``self_attack_rate`` in [0, 1] is the fraction of responses that
    targeted the agent's own reasoning — any non-zero value signals
    auto-immune tendency.
    """
    assessment_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    level: ToleranceLevel = ToleranceLevel.MODERATE
    false_positive_rate: float = 0.0
    self_attack_rate: float = 0.0
    rationale: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this assessment to a plain dict, expanding enums via ``.value``."""
        return {
            "assessment_id": self.assessment_id,
            "agent_id": self.agent_id,
            "level": _enum_value(ToleranceLevel, self.level),
            "false_positive_rate": self.false_positive_rate,
            "self_attack_rate": self.self_attack_rate,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class MemoryEntry:
    """Immune memory for one threat type held by one agent.

    ``encounter_count`` is how many times the agent has encountered this
    threat type. ``state`` is the ``MemoryState`` of the memory.
    ``last_response`` is the ``ImmuneResponse`` most recently mounted
    against this threat type, or ``None`` if the agent has not yet
    responded.
    """
    memory_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    threat_type: ThreatType = ThreatType.MISINFORMATION
    encounter_count: int = 0
    state: MemoryState = MemoryState.NAIVE
    last_response: Optional[ImmuneResponse] = None
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this memory entry to a plain dict, expanding enums via ``.value``.

        ``last_response`` is emitted as ``None`` when absent, else its
        enum ``.value``.
        """
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "threat_type": _enum_value(ThreatType, self.threat_type),
            "encounter_count": self.encounter_count,
            "state": _enum_value(MemoryState, self.state),
            "last_response": (
                _enum_value(ImmuneResponse, self.last_response)
                if self.last_response is not None
                else None
            ),
            "timestamp": self.timestamp,
        }


@dataclass
class ImmunityProfile:
    """Per-agent aggregate immune tendencies.

    ``avg_severity`` is the mean severity across the agent's detections
    (0.0 if none). ``dominant_threat`` is the most frequent
    ``ThreatType`` among the agent's detections, or ``None`` if none.
    ``regime`` is derived via ``_determine_regime``. ``tolerance_level``
    is from the most recent tolerance assessment, or MODERATE.
    ``total_neutralizations`` counts actions whose ``success`` flag is
    True.
    """
    agent_id: str = ""
    avg_severity: float = 0.0
    dominant_threat: Optional[ThreatType] = None
    regime: ImmunityRegime = ImmunityRegime.VIGILANT
    tolerance_level: ToleranceLevel = ToleranceLevel.MODERATE
    total_detections: int = 0
    total_neutralizations: int = 0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this profile to a plain dict, expanding enums via ``.value``.

        ``dominant_threat`` is emitted as ``None`` when absent, else its
        enum ``.value``.
        """
        return {
            "agent_id": self.agent_id,
            "avg_severity": self.avg_severity,
            "dominant_threat": (
                _enum_value(ThreatType, self.dominant_threat)
                if self.dominant_threat is not None
                else None
            ),
            "regime": _enum_value(ImmunityRegime, self.regime),
            "tolerance_level": _enum_value(ToleranceLevel, self.tolerance_level),
            "total_detections": self.total_detections,
            "total_neutralizations": self.total_neutralizations,
            "last_updated": self.last_updated,
        }


@dataclass
class ImmunityStats:
    """Engine-wide aggregate statistics across all agents and threats.

    Scalar totals are the rolling counts of each record type.
    ``regime_distribution``, ``threat_distribution``, and
    ``response_distribution`` tally the currently held snapshots,
    detections, and actions by their enum ``.value`` strings.
    ``avg_severity`` is the mean severity across all detections, or 0.0
    when none exist.
    """
    total_detections: int = 0
    total_actions: int = 0
    total_snapshots: int = 0
    total_tolerances: int = 0
    total_memories: int = 0
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    threat_distribution: Dict[str, int] = field(default_factory=dict)
    response_distribution: Dict[str, int] = field(default_factory=dict)
    avg_severity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict. Distributions are already keyed by ``str``."""
        return {
            "total_detections": self.total_detections,
            "total_actions": self.total_actions,
            "total_snapshots": self.total_snapshots,
            "total_tolerances": self.total_tolerances,
            "total_memories": self.total_memories,
            "regime_distribution": dict(self.regime_distribution),
            "threat_distribution": dict(self.threat_distribution),
            "response_distribution": dict(self.response_distribution),
            "avg_severity": self.avg_severity,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveImmunity:
    """Thread-safe engine that models an agent's cognitive immune system.

    The engine holds seven stores keyed by identifier: ``_detections``
    (ThreatDetection), ``_actions`` (ImmuneAction), ``_snapshots``
    (ImmunitySnapshot), ``_tolerances`` (ToleranceAssessment),
    ``_memories`` (MemoryEntry), ``_profiles`` (ImmunityProfile by
    agent_id), and ``_stats`` (rolling counters for fast aggregate reads).

    All mutations are guarded by a single reentrant lock so that public
    methods may safely call one another without self-deadlock. The
    immunity model is deliberately heuristic: severities, false-positive
    rates, and self-attack rates are caller-supplied readings, regimes
    are banded from aggregate activity, and dominant threats are
    computed by mode. These heuristics are transparent and auditable
    rather than learned, which keeps the engine deterministic.

    The engine is intentionally agnostic about how threats are detected
    and how severities are produced — callers may derive them from any
    source. The engine's job is to record, aggregate, classify, and
    remember, not to detect threats itself. Immune memory accumulates
    per agent+threat_type pair: recording a memory for a threat type
    the agent has already seen increments the encounter count and
    refreshes the state rather than creating a duplicate, so the memory
    store reflects the agent's accumulated exposure to each threat type.
    """

    # Number of most-recent detections whose severities feed into a
    # snapshot's average severity. The window is long enough to smooth a
    # single noisy reading and short enough to reflect the agent's
    # current threat exposure.
    _SNAPSHOT_DETECTION_WINDOW: int = 20

    def __init__(self) -> None:
        """Initialize an empty immunity engine with fresh stores and counters."""
        self._lock: threading.RLock = threading.RLock()
        self._detections: Dict[str, ThreatDetection] = {}
        self._actions: Dict[str, ImmuneAction] = {}
        self._snapshots: Dict[str, ImmunitySnapshot] = {}
        self._tolerances: Dict[str, ToleranceAssessment] = {}
        self._memories: Dict[str, MemoryEntry] = {}
        self._profiles: Dict[str, ImmunityProfile] = {}
        # Rolling counters kept in sync with the stores above. They mirror
        # the lengths of the primary stores and let get_stats() avoid full
        # scans for the scalar totals; distributions are still computed by
        # scanning so they always reflect the current state even after
        # out-of-band mutations.
        self._stats: Dict[str, int] = {
            "total_detections": 0,
            "total_actions": 0,
            "total_snapshots": 0,
            "total_tolerances": 0,
            "total_memories": 0,
        }
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Internal helpers (callers must already hold the lock) ───────

    def _agent_detections_locked(self, agent_id: str) -> List[ThreatDetection]:
        """Return one agent's detections in insertion order. Caller holds the lock."""
        return [d for d in self._detections.values() if d.agent_id == agent_id]

    def _agent_actions_locked(self, agent_id: str) -> List[ImmuneAction]:
        """Return one agent's actions in insertion order. Caller holds the lock."""
        return [a for a in self._actions.values() if a.agent_id == agent_id]

    def _agent_memories_locked(self, agent_id: str) -> List[MemoryEntry]:
        """Return one agent's memory entries in insertion order. Caller holds the lock."""
        return [m for m in self._memories.values() if m.agent_id == agent_id]

    def _agent_tolerances_locked(self, agent_id: str) -> List[ToleranceAssessment]:
        """Return one agent's tolerance assessments in insertion order. Caller holds the lock."""
        return [t for t in self._tolerances.values() if t.agent_id == agent_id]

    def _mode_threat_locked(
        self, detections: List[ThreatDetection]
    ) -> Optional[ThreatType]:
        """Return the most frequent threat type among the supplied detections.

        Ties are broken by insertion order. Returns ``None`` if the list
        is empty. Caller holds the lock.
        """
        if not detections:
            return None
        counts: Dict[ThreatType, int] = {}
        for detection in detections:
            counts[detection.threat_type] = counts.get(detection.threat_type, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def _latest_tolerance_locked(self, agent_id: str) -> ToleranceLevel:
        """Return the agent's most recent tolerance level, or MODERATE.

        MODERATE is the balanced default when the agent has no
        assessments. Caller holds the lock.
        """
        assessments = self._agent_tolerances_locked(agent_id)
        if not assessments:
            return ToleranceLevel.MODERATE
        # Assessments are stored in insertion order, so the last one is
        # the most recent.
        return assessments[-1].level

    def _neutralized_ratio_locked(self, agent_id: str) -> float:
        """Return the fraction of the agent's actions that neutralized a threat.

        A neutralizing action is one whose ``success`` flag is True.
        Returns 0.0 when the agent has no actions. Caller holds the lock.
        """
        actions = self._agent_actions_locked(agent_id)
        if not actions:
            return 0.0
        neutralized = sum(1 for a in actions if a.success)
        return neutralized / len(actions)

    def _false_positive_rate_locked(self, agent_id: str) -> float:
        """Return the fraction of the agent's actions that dismissed inputs as harmless.

        A false positive is an action whose response was IGNORE. Returns
        0.0 when the agent has no actions. Caller holds the lock.
        """
        actions = self._agent_actions_locked(agent_id)
        if not actions:
            return 0.0
        ignored = sum(1 for a in actions if a.response == ImmuneResponse.IGNORE)
        return ignored / len(actions)

    def _active_threat_count_locked(self, agent_id: str) -> int:
        """Return the number of the agent's detections that have no response yet.

        A threat is active when it has been detected but no action
        references its ``detection_id``. Caller holds the lock.
        """
        detections = self._agent_detections_locked(agent_id)
        if not detections:
            return 0
        responded_ids = {
            a.detection_id for a in self._agent_actions_locked(agent_id)
        }
        return sum(1 for d in detections if d.detection_id not in responded_ids)

    # ── Threat Detections ─────────────────────────────────────────

    def detect_threat(
        self,
        agent_id: str,
        threat_type: Any,
        source: str,
        severity: float,
        evidence: str,
    ) -> ThreatDetection:
        """Record a threat detection for an agent and return it.

        ``threat_type`` may be passed as a ``ThreatType`` member or its
        string name/value. ``severity`` in [0, 1] is clamped to that
        range. The detection is stored, counted, and returned; the
        agent's cached profile is invalidated.
        """
        with self._lock:
            detection = ThreatDetection(
                agent_id=agent_id,
                threat_type=_resolve_enum(ThreatType, threat_type),
                source=str(source),
                severity=_clamp(severity, 0.0, 1.0),
                evidence=str(evidence),
                timestamp=_now(),
            )
            self._detections[detection.detection_id] = detection
            self._stats["total_detections"] += 1
            self._profiles.pop(agent_id, None)
            return detection

    def list_detections(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ThreatDetection]:
        """Return detections, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all detections are considered;
        otherwise only detections for that agent are returned. The most
        recently recorded ``limit`` detections are returned (insertion
        order is chronological, so the tail is the most recent). The
        returned list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            detections = list(self._detections.values())
        if agent_id is not None:
            detections = [d for d in detections if d.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return detections[-n:] if n else []

    def get_detection(self, detection_id: str) -> ThreatDetection:
        """Retrieve a detection by id.

        Raises ``ValueError`` if no detection exists with that id, so
        callers can treat the return as a guaranteed non-None value and
        let a single exception type stand in for a not-found HTTP error.
        """
        with self._lock:
            detection = self._detections.get(detection_id)
        if detection is None:
            raise ValueError(f"detection {detection_id!r} not found")
        return detection

    # ── Immune Actions ────────────────────────────────────────────

    def respond(
        self,
        agent_id: str,
        detection_id: str,
        response: Any,
        rationale: str,
        neutralization_method: str,
        success: bool,
    ) -> ImmuneAction:
        """Record an immune response to a detection and return it.

        ``detection_id`` links the action to its triggering
        ``ThreatDetection``. ``response`` may be passed as an
        ``ImmuneResponse`` member or its string name/value. The action
        is stored, counted, and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            action = ImmuneAction(
                agent_id=agent_id,
                detection_id=str(detection_id),
                response=_resolve_enum(ImmuneResponse, response),
                rationale=str(rationale),
                neutralization_method=str(neutralization_method),
                success=bool(success),
                timestamp=_now(),
            )
            self._actions[action.action_id] = action
            self._stats["total_actions"] += 1
            self._profiles.pop(agent_id, None)
            return action

    def list_responses(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ImmuneAction]:
        """Return immune actions, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all actions are considered;
        otherwise only actions for that agent are returned. The most
        recently recorded ``limit`` actions are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            actions = list(self._actions.values())
        if agent_id is not None:
            actions = [a for a in actions if a.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return actions[-n:] if n else []

    def get_response(self, action_id: str) -> ImmuneAction:
        """Retrieve an immune action by id.

        Raises ``ValueError`` if no action exists with that id.
        """
        with self._lock:
            action = self._actions.get(action_id)
        if action is None:
            raise ValueError(f"immune action {action_id!r} not found")
        return action

    # ── Snapshots ─────────────────────────────────────────────────

    def take_snapshot(self, agent_id: str) -> ImmunitySnapshot:
        """Aggregate an agent's recent immune activity into a snapshot.

        ``active_threats`` is the count of detections with no response
        yet. ``neutralized_count`` is the count of successful actions.
        ``memory_count`` is the count of immune memory entries.
        ``avg_severity`` is the mean severity across the agent's most
        recent detections (the last ``_SNAPSHOT_DETECTION_WINDOW`` = 20),
        or 0.0 if none. ``regime`` is derived via ``_determine_regime``.
        ``tolerance`` is from the agent's most recent tolerance
        assessment, or MODERATE if none exists. The snapshot is stored,
        counted, and returned; the agent's cached profile is invalidated.
        """
        with self._lock:
            agent_detections = self._agent_detections_locked(agent_id)
            recent = agent_detections[-self._SNAPSHOT_DETECTION_WINDOW:]

            active_threats = self._active_threat_count_locked(agent_id)
            neutralized_count = sum(
                1 for a in self._agent_actions_locked(agent_id) if a.success
            )
            memory_count = len(self._agent_memories_locked(agent_id))
            if recent:
                avg_severity = sum(d.severity for d in recent) / len(recent)
            else:
                avg_severity = 0.0

            neutralized_ratio = self._neutralized_ratio_locked(agent_id)
            false_positive_rate = self._false_positive_rate_locked(agent_id)
            regime = _determine_regime(
                active_threats, neutralized_ratio, false_positive_rate
            )
            tolerance = self._latest_tolerance_locked(agent_id)

            snapshot = ImmunitySnapshot(
                agent_id=agent_id,
                regime=regime,
                tolerance=tolerance,
                active_threats=active_threats,
                neutralized_count=neutralized_count,
                memory_count=memory_count,
                avg_severity=round(avg_severity, 4),
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
    ) -> List[ImmunitySnapshot]:
        """Return snapshots, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all snapshots are considered;
        otherwise only snapshots for that agent are returned. The most
        recently taken ``limit`` snapshots are returned. The returned
        list is a snapshot copy; mutating it does not affect the engine.
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

    def get_snapshot(self, snapshot_id: str) -> ImmunitySnapshot:
        """Retrieve a snapshot by id.

        Raises ``ValueError`` if no snapshot exists with that id.
        """
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise ValueError(f"snapshot {snapshot_id!r} not found")
        return snapshot

    # ── Tolerance Assessments ─────────────────────────────────────

    def assess_tolerance(
        self,
        agent_id: str,
        level: Any,
        false_positive_rate: float,
        self_attack_rate: float,
        rationale: str,
    ) -> ToleranceAssessment:
        """Record a tolerance assessment for an agent and return it.

        ``level`` may be passed as a ``ToleranceLevel`` member or its
        string name/value. Both ``false_positive_rate`` and
        ``self_attack_rate`` are clamped to [0, 1]. The assessment is
        stored, counted, and returned; the agent's cached profile is
        invalidated.
        """
        with self._lock:
            assessment = ToleranceAssessment(
                agent_id=agent_id,
                level=_resolve_enum(ToleranceLevel, level),
                false_positive_rate=_clamp(false_positive_rate, 0.0, 1.0),
                self_attack_rate=_clamp(self_attack_rate, 0.0, 1.0),
                rationale=str(rationale),
                timestamp=_now(),
            )
            self._tolerances[assessment.assessment_id] = assessment
            self._stats["total_tolerances"] += 1
            self._profiles.pop(agent_id, None)
            return assessment

    def list_tolerances(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ToleranceAssessment]:
        """Return tolerance assessments, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all assessments are considered;
        otherwise only assessments for that agent are returned. The most
        recently recorded ``limit`` assessments are returned. The
        returned list is a snapshot copy; mutating it does not affect the
        engine.
        """
        with self._lock:
            tolerances = list(self._tolerances.values())
        if agent_id is not None:
            tolerances = [t for t in tolerances if t.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return tolerances[-n:] if n else []

    def get_tolerance(self, assessment_id: str) -> ToleranceAssessment:
        """Retrieve a tolerance assessment by id.

        Raises ``ValueError`` if no assessment exists with that id.
        """
        with self._lock:
            assessment = self._tolerances.get(assessment_id)
        if assessment is None:
            raise ValueError(f"tolerance assessment {assessment_id!r} not found")
        return assessment

    # ── Immune Memory ─────────────────────────────────────────────

    def record_memory(
        self,
        agent_id: str,
        threat_type: Any,
        state: Any = MemoryState.PRIMED,
        encounter_count: int = 1,
        last_response: Optional[Any] = None,
    ) -> MemoryEntry:
        """Record or update an immune memory entry for an agent+threat_type.

        Immune memory accumulates per agent+threat_type pair. If a memory
        for the pair already exists, its ``encounter_count`` is
        incremented by the provided ``encounter_count`` (default 1), its
        ``state`` and ``last_response`` are updated, and its timestamp is
        refreshed. Otherwise a new memory is created. ``threat_type``,
        ``state``, and ``last_response`` may each be passed as an enum
        member or its string name/value. ``encounter_count`` is coerced
        to a non-negative int. ``last_response`` may be ``None`` to clear
        it. The agent's cached profile is invalidated.
        """
        with self._lock:
            member_threat = _resolve_enum(ThreatType, threat_type)
            member_state = _resolve_enum(MemoryState, state)
            try:
                inc = int(encounter_count)
            except (TypeError, ValueError):
                inc = 1
            if inc < 0:
                inc = 0
            if last_response is None:
                resolved_response: Optional[ImmuneResponse] = None
            else:
                resolved_response = _resolve_enum(ImmuneResponse, last_response)

            # Find an existing memory for this agent+threat_type pair.
            existing: Optional[MemoryEntry] = None
            for memory in self._agent_memories_locked(agent_id):
                if memory.threat_type == member_threat:
                    existing = memory
                    break

            if existing is not None:
                existing.encounter_count += inc
                existing.state = member_state
                existing.last_response = resolved_response
                existing.timestamp = _now()
                memory_entry = existing
            else:
                memory_entry = MemoryEntry(
                    agent_id=agent_id,
                    threat_type=member_threat,
                    encounter_count=inc,
                    state=member_state,
                    last_response=resolved_response,
                    timestamp=_now(),
                )
                self._memories[memory_entry.memory_id] = memory_entry
                self._stats["total_memories"] += 1

            self._profiles.pop(agent_id, None)
            return memory_entry

    def list_memories(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """Return immune memory entries, optionally filtered by agent, capped to ``limit``.

        When ``agent_id`` is ``None`` all memory entries are considered;
        otherwise only entries for that agent are returned. The most
        recently updated ``limit`` entries are returned (insertion order
        is chronological, so the tail is the most recent). The returned
        list is a snapshot copy; mutating it does not affect the engine.
        """
        with self._lock:
            memories = list(self._memories.values())
        if agent_id is not None:
            memories = [m for m in memories if m.agent_id == agent_id]
        try:
            n = int(limit)
        except (TypeError, ValueError):
            n = 50
        if n < 0:
            n = 0
        return memories[-n:] if n else []

    def get_memory(self, memory_id: str) -> MemoryEntry:
        """Retrieve an immune memory entry by id.

        Raises ``ValueError`` if no memory entry exists with that id.
        """
        with self._lock:
            memory = self._memories.get(memory_id)
        if memory is None:
            raise ValueError(f"memory entry {memory_id!r} not found")
        return memory

    # ── Profiles ──────────────────────────────────────────────────

    def get_profile(self, agent_id: str) -> ImmunityProfile:
        """Return the agent's immunity profile, computing it if absent.

        The profile is cached on the agent_id and invalidated whenever
        the agent's detections, actions, snapshots, tolerances, or
        memories change. Call ``update_profile`` to force a refresh or
        override a computed field. Field semantics are documented on
        ``ImmunityProfile`` and ``_compute_profile_locked``.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> ImmunityProfile:
        """Refresh and optionally override fields of an agent's immunity profile.

        The profile is first recomputed from the live stores, then any
        supplied keyword overrides (matching ``ImmunityProfile`` field
        names) are applied, and ``last_updated`` is stamped. Accepted
        overrides: ``avg_severity`` (float), ``dominant_threat``
        (``ThreatType`` or ``None``), ``regime`` (``ImmunityRegime``),
        ``tolerance_level`` (``ToleranceLevel``), ``total_detections``
        and ``total_neutralizations`` (int). Enum-valued overrides may be
        passed as the enum member or its string name/value. Unknown keys
        are ignored.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            for key, value in kwargs.items():
                if key == "avg_severity":
                    try:
                        profile.avg_severity = float(value)
                    except (TypeError, ValueError):
                        pass
                elif key == "dominant_threat":
                    if value is None:
                        profile.dominant_threat = None
                    else:
                        try:
                            profile.dominant_threat = _resolve_enum(ThreatType, value)
                        except ValueError:
                            pass
                elif key == "regime":
                    try:
                        profile.regime = _resolve_enum(ImmunityRegime, value)
                    except ValueError:
                        pass
                elif key == "tolerance_level":
                    try:
                        profile.tolerance_level = _resolve_enum(ToleranceLevel, value)
                    except ValueError:
                        pass
                elif key in ("total_detections", "total_neutralizations"):
                    try:
                        setattr(profile, key, int(value))
                    except (TypeError, ValueError):
                        pass
            profile.last_updated = _now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[ImmunityProfile]:
        """Return all stored immunity profiles as a snapshot list.

        The returned list is a snapshot copy; mutating it does not affect
        the engine.
        """
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics & Maintenance ────────────────────────────────────

    def get_stats(self) -> ImmunityStats:
        """Compute engine-wide aggregate statistics.

        Scalar totals are read from the rolling ``_stats`` counters.
        Distributions are tallied from the currently held snapshots,
        detections, and actions, keyed by each enum's ``.value`` string
        so the result is JSON-serializable.
        """
        with self._lock:
            regime_dist: Dict[str, int] = {}
            for snap in self._snapshots.values():
                key = _enum_value(ImmunityRegime, snap.regime)
                regime_dist[key] = regime_dist.get(key, 0) + 1

            threat_dist: Dict[str, int] = {}
            severity_sum = 0.0
            for detection in self._detections.values():
                key = _enum_value(ThreatType, detection.threat_type)
                threat_dist[key] = threat_dist.get(key, 0) + 1
                severity_sum += detection.severity

            response_dist: Dict[str, int] = {}
            for action in self._actions.values():
                key = _enum_value(ImmuneResponse, action.response)
                response_dist[key] = response_dist.get(key, 0) + 1

            detection_count = len(self._detections)
            avg_severity = (
                round(severity_sum / detection_count, 4) if detection_count else 0.0
            )

            return ImmunityStats(
                total_detections=self._stats["total_detections"],
                total_actions=self._stats["total_actions"],
                total_snapshots=self._stats["total_snapshots"],
                total_tolerances=self._stats["total_tolerances"],
                total_memories=self._stats["total_memories"],
                regime_distribution=regime_dist,
                threat_distribution=threat_dist,
                response_distribution=response_dist,
                avg_severity=avg_severity,
            )

    def reset(self) -> None:
        """Reset the engine to its initial empty state.

        Clears every store and zeroes every rolling counter. The
        singleton reference is not touched; callers that want a fresh
        singleton should use ``reset_immunity_engine`` instead.
        """
        with self._lock:
            self._detections.clear()
            self._actions.clear()
            self._snapshots.clear()
            self._tolerances.clear()
            self._memories.clear()
            self._profiles.clear()
            self._stats["total_detections"] = 0
            self._stats["total_actions"] = 0
            self._stats["total_snapshots"] = 0
            self._stats["total_tolerances"] = 0
            self._stats["total_memories"] = 0

    # ── Internal profile computation (caller must hold the lock) ────

    def _compute_profile_locked(self, agent_id: str) -> ImmunityProfile:
        """Aggregate an agent's detections and actions into a profile.

        See ``ImmunityProfile`` for field semantics. ``regime`` is derived
        via ``_determine_regime``; ``tolerance_level`` is from the agent's
        most recent tolerance assessment, or MODERATE if none exists.
        Caller holds the lock.
        """
        agent_detections = self._agent_detections_locked(agent_id)
        agent_actions = self._agent_actions_locked(agent_id)

        total_detections = len(agent_detections)
        if agent_detections:
            avg_severity = sum(d.severity for d in agent_detections) / len(
                agent_detections
            )
        else:
            avg_severity = 0.0
        dominant_threat = self._mode_threat_locked(agent_detections)

        total_neutralizations = sum(1 for a in agent_actions if a.success)
        active_threats = self._active_threat_count_locked(agent_id)
        if agent_actions:
            neutralized_ratio = total_neutralizations / len(agent_actions)
        else:
            neutralized_ratio = 0.0
        false_positive_rate = self._false_positive_rate_locked(agent_id)
        regime = _determine_regime(
            active_threats, neutralized_ratio, false_positive_rate
        )
        tolerance_level = self._latest_tolerance_locked(agent_id)

        return ImmunityProfile(
            agent_id=agent_id,
            avg_severity=round(avg_severity, 4),
            dominant_threat=dominant_threat,
            regime=regime,
            tolerance_level=tolerance_level,
            total_detections=total_detections,
            total_neutralizations=total_neutralizations,
            last_updated=_now(),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveImmunity] = None
_engine_lock = threading.Lock()


def get_immunity_engine() -> AgentCognitiveImmunity:
    """Get or create the singleton ``AgentCognitiveImmunity`` instance.

    The first call constructs the engine; subsequent calls return the
    same instance. Access is guarded by a module-level lock so the
    singleton is safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveImmunity()
        return _engine


def reset_immunity_engine() -> None:
    """Reset the singleton ``AgentCognitiveImmunity`` instance.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_immunity_engine`` call creates a fresh
    instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
