from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Dict, List
import threading
import uuid
import time
import re
from datetime import datetime


# =========================================================
# Enums
# =========================================================

class BiasType(str, Enum):
    """Categories of cognitive biases that may affect agent reasoning."""
    CONFIRMATION = "confirmation"
    ANCHORING = "anchoring"
    AVAILABILITY = "availability"
    RECENCY = "recency"
    SUNK_COST = "sunk_cost"
    FRAMING = "framing"
    REPRESENTATIVENESS = "representativeness"
    OVERCONFIDENCE = "overconfidence"


class BiasSeverity(str, Enum):
    """Severity scale used when reporting a detected bias."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DebiasingStrategy(str, Enum):
    """Strategies available for mitigating a detected bias."""
    COUNTERFACTUAL_PROBING = "counterfactual_probing"
    PERSPECTIVE_SHIFTING = "perspective_shifting"
    EVIDENCE_DIVERSIFICATION = "evidence_diversification"
    BASE_RATE_RECALIBRATION = "base_rate_recalibration"
    BLIND_REVIEW = "blind_review"
    DELAYED_JUDGMENT = "delayed_judgment"


class AuditStatus(str, Enum):
    """Lifecycle status of a reasoning audit."""
    PENDING = "pending"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    RESOLVED = "resolved"


class EvidenceRole(str, Enum):
    """Role that a piece of evidence plays relative to a hypothesis."""
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    NEUTRAL = "neutral"


# =========================================================
# Keyword tables used by the heuristic detectors
# =========================================================
#
# The detector is intentionally lightweight: it scans the free-form
# reasoning trace and the structured context supplied by the caller and
# matches against these keyword tables to produce BiasDetection records.
# Keyword matching is case-insensitive because every scanned text is
# lowercased before the comparison is performed.

_CONFIRMATION_KEYWORDS: List[str] = [
    "supports", "support", "confirms", "confirm", "proves", "prove",
    "evidence for", "in favor of", "consistent with", "agrees with",
    "backs up", "corroborates", "validates", "aligns with",
]

_CONTRADICTION_KEYWORDS: List[str] = [
    "contradicts", "contradict", "refutes", "refute", "disproves",
    "evidence against", "inconsistent with", "disagrees with", "opposes",
    "undermines", "challenges", "counters",
]

_NEUTRAL_KEYWORDS: List[str] = [
    "mentions", "notes", "states", "reports", "describes", "observes",
    "records", "indicates", "mentions that", "says",
]

_ANCHORING_KEYWORDS: List[str] = [
    "first", "initial", "anchor", "starting point", "baseline",
    "originally", "previously assumed", "default", "initial impression",
]

_RECENCY_KEYWORDS: List[str] = [
    "recently", "latest", "last", "most recent", "just now",
    "newest", "current", "updated", "fresh",
]

_OVERCONFIDENCE_KEYWORDS: List[str] = [
    "certain", "definitely", "absolutely", "without a doubt",
    "guaranteed", "100%", "clearly", "obviously", "must be",
    "undoubtedly", "surely", "no question", "certainly",
]

_AVAILABILITY_KEYWORDS: List[str] = [
    "recall", "remember", "memorable", "salient", "striking",
    "stands out", "comes to mind", "vivid", "easily remembered",
]

_SUNK_COST_KEYWORDS: List[str] = [
    "invested", "spent", "committed", "already paid", "sunk",
    "cannot lose", "too much to abandon", "in too deep",
    "already spent", "heavily invested",
]

_FRAMING_KEYWORDS: List[str] = [
    "gain", "loss", "save", "risk", "benefit", "cost",
    "avoid", "secure", "protect", "forfeit", "preserve", "lose",
]

_REPRESENTATIVENESS_KEYWORDS: List[str] = [
    "similar", "like", "resembles", "reminds me of", "typical of",
    "matches the pattern", "looks like", "consistent with the stereotype",
    "fits the profile", "pattern matches",
]


# =========================================================
# Dataclasses
# =========================================================

@dataclass
class BiasEvidence:
    """A single piece of evidence considered during bias analysis.

    Evidence objects are derived either from the structured context
    supplied by the caller or from a shallow parse of the reasoning
    trace itself. The weight field expresses how much the evidence
    influenced the overall judgement and is used by the anchoring and
    recency heuristics.
    """
    evidence_id: str
    description: str
    role: EvidenceRole
    weight: float
    source: str = "reasoning_trace"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "description": self.description,
            "role": self.role.value,
            "weight": self.weight,
            "source": self.source,
        }


@dataclass
class BiasDetection:
    """A single detected cognitive bias tied to a reasoning audit.

    Each detection carries the evidence that triggered it, a confidence
    score in the range [0.0, 1.0], and a resolution flag that is set
    when a human or downstream consumer has reviewed the finding.
    """
    detection_id: str
    audit_id: str
    bias_type: BiasType
    severity: BiasSeverity
    description: str
    evidence: List[BiasEvidence] = field(default_factory=list)
    confidence: float = 0.0
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved: bool = False
    resolution_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": self.detection_id,
            "audit_id": self.audit_id,
            "bias_type": self.bias_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence,
            "detected_at": self.detected_at,
            "resolved": self.resolved,
            "resolution_note": self.resolution_note,
        }


@dataclass
class DebiasingAction:
    """A mitigating action applied to a specific bias detection."""
    action_id: str
    detection_id: str
    strategy: DebiasingStrategy
    description: str
    applied_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    outcome: str = "applied"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "detection_id": self.detection_id,
            "strategy": self.strategy.value,
            "description": self.description,
            "applied_at": self.applied_at,
            "outcome": self.outcome,
        }


@dataclass
class BiasProfile:
    """Per-agent tendency profile aggregated across audits.

    The tendency_scores map expresses, for each BiasType, a value in
    the range [0.0, 1.0] where higher values indicate a stronger
    historical tendency for the agent to exhibit that bias.
    """
    agent_id: str
    tendency_scores: Dict[BiasType, float] = field(default_factory=dict)
    total_audits: int = 0
    total_detections: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "tendency_scores": {k.value: v for k, v in self.tendency_scores.items()},
            "total_audits": self.total_audits,
            "total_detections": self.total_detections,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ReasoningAudit:
    """A captured reasoning trace together with its bias audit results.

    Audits move through the PENDING -> COMPLETED lifecycle when
    detect_biases is invoked. They may transition to DISPUTED or
    RESOLVED by downstream consumers that disagree with or accept the
    findings.
    """
    audit_id: str
    agent_id: str
    reasoning_trace: str
    context: Dict[str, Any] = field(default_factory=dict)
    status: AuditStatus = AuditStatus.PENDING
    detections: List[BiasDetection] = field(default_factory=list)
    debiasing_actions: List[DebiasingAction] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "agent_id": self.agent_id,
            "reasoning_trace": self.reasoning_trace,
            "context": dict(self.context),
            "status": self.status.value,
            "detections": [d.to_dict() for d in self.detections],
            "debiasing_actions": [a.to_dict() for a in self.debiasing_actions],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class DetectorStats:
    """Aggregate counters describing detector activity.

    detections_by_type and detections_by_severity are keyed by the
    corresponding enum so that callers can inspect the distribution of
    findings across bias categories and severity bands.
    """
    total_audits: int = 0
    completed_audits: int = 0
    total_detections: int = 0
    resolved_detections: int = 0
    total_debiasing_actions: int = 0
    detections_by_type: Dict[BiasType, int] = field(default_factory=dict)
    detections_by_severity: Dict[BiasSeverity, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_audits": self.total_audits,
            "completed_audits": self.completed_audits,
            "total_detections": self.total_detections,
            "resolved_detections": self.resolved_detections,
            "total_debiasing_actions": self.total_debiasing_actions,
            "detections_by_type": {k.value: v for k, v in self.detections_by_type.items()},
            "detections_by_severity": {k.value: v for k, v in self.detections_by_severity.items()},
        }


# =========================================================
# Detector
# =========================================================

class AgentCognitiveBiasDetector:
    """Detects, quantifies, and mitigates cognitive biases in agent reasoning.

    The detector is intentionally heuristic-based: it scans the free-form
    reasoning trace and the structured context supplied by the caller and
    produces BiasDetection records that downstream consumers can act on.
    All mutable state is guarded by an internal reentrant lock so the
    detector is safe to share across threads within a single process.

    Typical usage:

        detector = get_bias_detector()
        audit = detector.submit_reasoning("agent_1", trace, context)
        detections = detector.detect_biases(audit.audit_id)
        for d in detections:
            detector.apply_debiasing(d.detection_id, strategy)
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._audits: Dict[str, ReasoningAudit] = {}
        self._detections: Dict[str, BiasDetection] = {}
        self._debiasing_actions: Dict[str, DebiasingAction] = {}
        self._profiles: Dict[str, BiasProfile] = {}
        self._stats: DetectorStats = DetectorStats()

    # -----------------------------------------------------
    # Audit lifecycle
    # -----------------------------------------------------

    def submit_reasoning(
        self,
        agent_id: str,
        reasoning_trace: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReasoningAudit:
        """Register a new reasoning trace for bias analysis.

        The audit is created in PENDING status. Call detect_biases to
        perform the heuristic scan and populate detections. The audit
        is returned by reference so the caller can immediately inspect
        its audit_id and other identifying fields.
        """
        audit_id = f"audit_{uuid.uuid4().hex}"
        audit = ReasoningAudit(
            audit_id=audit_id,
            agent_id=agent_id,
            reasoning_trace=reasoning_trace or "",
            context=dict(context) if context else {},
        )
        with self._lock:
            self._audits[audit_id] = audit
            profile = self._get_or_create_profile(agent_id)
            profile.total_audits += 1
            profile.updated_at = datetime.utcnow().isoformat()
            self._stats.total_audits += 1
        return audit

    def get_audit(self, audit_id: str) -> Optional[ReasoningAudit]:
        """Return the audit with the given id, or None if it does not exist."""
        with self._lock:
            return self._audits.get(audit_id)

    def list_audits(
        self,
        agent_id: Optional[str] = None,
        status: Optional[AuditStatus] = None,
    ) -> List[ReasoningAudit]:
        """List audits, optionally filtered by agent_id and/or status."""
        with self._lock:
            audits = list(self._audits.values())
        if agent_id is not None:
            audits = [a for a in audits if a.agent_id == agent_id]
        if status is not None:
            audits = [a for a in audits if a.status == status]
        return audits

    # -----------------------------------------------------
    # Detection
    # -----------------------------------------------------

    def detect_biases(self, audit_id: str) -> List[BiasDetection]:
        """Run heuristic bias detection against a stored audit.

        Resets audit.detections to a freshly computed list and marks the
        audit as COMPLETED. Re-running detect_biases on the same audit
        will recompute detections from scratch and keep the aggregate
        statistics consistent. Returns the new list of detections.
        """
        start = time.monotonic()
        with self._lock:
            audit = self._audits.get(audit_id)
            if audit is None:
                return []

            # Roll back any previously recorded detections so stats stay
            # consistent when detect_biases is invoked more than once.
            for prev in audit.detections:
                self._detections.pop(prev.detection_id, None)
                self._decrement_detection_stats(prev)
            audit.detections = []
            # Note: previously applied debiasing actions are preserved on
            # the audit for historical traceability even though their
            # target detections have been cleared and recomputed.

            trace = audit.reasoning_trace or ""
            context = audit.context or {}
            text = trace.lower()

            evidence_items = self._extract_evidence(trace, context)
            evidence_stats = self._evidence_stats(evidence_items)

            new_detections: List[BiasDetection] = []
            new_detections.extend(self._detect_confirmation(audit, text, evidence_stats, evidence_items))
            new_detections.extend(self._detect_anchoring(audit, text, evidence_items))
            new_detections.extend(self._detect_recency(audit, text, evidence_items))
            new_detections.extend(self._detect_overconfidence(audit, text, evidence_stats, evidence_items))
            new_detections.extend(self._detect_availability(audit, text, evidence_items))
            new_detections.extend(self._detect_sunk_cost(audit, text, context, evidence_items))
            new_detections.extend(self._detect_framing(audit, text, context, evidence_items))
            new_detections.extend(self._detect_representativeness(audit, text, evidence_items))

            for detection in new_detections:
                audit.detections.append(detection)
                self._detections[detection.detection_id] = detection
                self._increment_detection_stats(detection)

            profile = self._get_or_create_profile(audit.agent_id)
            profile.total_detections += len(new_detections)
            for detection in new_detections:
                current = profile.tendency_scores.get(detection.bias_type, 0.0)
                # Blend the new signal with the running tendency score so
                # that long-running agents do not spike on a single audit.
                profile.tendency_scores[detection.bias_type] = round(
                    current * 0.7 + detection.confidence * 0.3, 4
                )
            profile.updated_at = datetime.utcnow().isoformat()

            # Only flip PENDING audits to COMPLETED to avoid clobbering
            # DISPUTED or RESOLVED statuses set by downstream consumers.
            if audit.status == AuditStatus.PENDING:
                audit.status = AuditStatus.COMPLETED
                self._stats.completed_audits += 1
            audit.completed_at = datetime.utcnow().isoformat()

            # Elapsed time is computed for instrumentation only; the
            # result is intentionally discarded to keep the API surface
            # focused on the bias detection contract.
            _elapsed = (time.monotonic() - start) * 1000.0
            return list(audit.detections)

    def get_detection(self, detection_id: str) -> Optional[BiasDetection]:
        """Return the detection with the given id, or None if missing."""
        with self._lock:
            return self._detections.get(detection_id)

    def list_detections(self, audit_id: str) -> List[BiasDetection]:
        """Return all detections currently attached to the given audit."""
        with self._lock:
            audit = self._audits.get(audit_id)
            if audit is None:
                return []
            return list(audit.detections)

    # -----------------------------------------------------
    # Debiasing actions
    # -----------------------------------------------------

    def apply_debiasing(
        self,
        detection_id: str,
        strategy: DebiasingStrategy,
    ) -> DebiasingAction:
        """Apply a debiasing strategy to a detection and record the action.

        Raises KeyError if the detection_id is unknown to the detector.
        """
        with self._lock:
            detection = self._detections.get(detection_id)
            if detection is None:
                raise KeyError(f"Unknown detection_id: {detection_id}")
            audit = self._audits.get(detection.audit_id)

            action_id = f"action_{uuid.uuid4().hex}"
            action = DebiasingAction(
                action_id=action_id,
                detection_id=detection_id,
                strategy=strategy,
                description=self._describe_strategy(strategy, detection),
                outcome="applied",
            )
            self._debiasing_actions[action_id] = action
            if audit is not None:
                audit.debiasing_actions.append(action)
            self._stats.total_debiasing_actions += 1
            return action

    def list_debiasing_actions(
        self,
        audit_id: Optional[str] = None,
    ) -> List[DebiasingAction]:
        """List debiasing actions, optionally filtered by audit_id.

        When audit_id is provided, only actions tied to detections on
        that audit are returned. Otherwise every recorded action is
        returned.
        """
        with self._lock:
            if audit_id is None:
                return list(self._debiasing_actions.values())
            audit = self._audits.get(audit_id)
            if audit is None:
                return []
            return list(audit.debiasing_actions)

    # -----------------------------------------------------
    # Resolution
    # -----------------------------------------------------

    def resolve_detection(
        self,
        detection_id: str,
        resolution_note: str = "",
    ) -> BiasDetection:
        """Mark a detection as resolved and attach an optional note.

        Raises KeyError if the detection_id is unknown. Re-resolving an
        already-resolved detection simply updates the note and leaves
        the resolved counter unchanged.
        """
        with self._lock:
            detection = self._detections.get(detection_id)
            if detection is None:
                raise KeyError(f"Unknown detection_id: {detection_id}")
            if not detection.resolved:
                detection.resolved = True
                self._stats.resolved_detections += 1
            detection.resolution_note = resolution_note
            return detection

    # -----------------------------------------------------
    # Profiles
    # -----------------------------------------------------

    def get_profile(self, agent_id: str) -> BiasProfile:
        """Return the bias profile for the given agent, creating one if needed."""
        with self._lock:
            return self._get_or_create_profile(agent_id)

    def list_profiles(self) -> List[BiasProfile]:
        """Return all known per-agent bias profiles."""
        with self._lock:
            return list(self._profiles.values())

    def update_profile(
        self,
        agent_id: str,
        bias_type: BiasType,
        tendency_delta: float,
    ) -> BiasProfile:
        """Adjust an agent's tendency score for a specific bias type.

        The resulting score is clamped to the range [0.0, 1.0] so that
        downstream consumers can treat it as a probability-like value.
        """
        with self._lock:
            profile = self._get_or_create_profile(agent_id)
            current = profile.tendency_scores.get(bias_type, 0.0)
            profile.tendency_scores[bias_type] = max(
                0.0, min(1.0, round(current + tendency_delta, 4))
            )
            profile.updated_at = datetime.utcnow().isoformat()
            return profile

    # -----------------------------------------------------
    # Evidence analysis
    # -----------------------------------------------------

    def analyze_evidence(self, evidence_items: List[Any]) -> Dict[str, Any]:
        """Return symmetry statistics for a list of evidence items.

        Each item may be a BiasEvidence instance or a dict containing at
        least a "role" key whose value is one of EvidenceRole. The
        returned dict includes raw counts, ratios, total weight, and a
        boolean flag indicating whether the evidence set is symmetric.
        """
        normalized: List[BiasEvidence] = []
        for item in evidence_items or []:
            if isinstance(item, BiasEvidence):
                normalized.append(item)
            elif isinstance(item, dict):
                role = self._coerce_role(item.get("role"))
                normalized.append(BiasEvidence(
                    evidence_id=str(item.get("evidence_id", f"ev_{uuid.uuid4().hex[:8]}")),
                    description=str(item.get("description", "")),
                    role=role,
                    weight=float(item.get("weight", 1.0)),
                    source=str(item.get("source", "external")),
                ))
            else:
                continue
        stats = self._evidence_stats(normalized)
        return {
            "total": stats["total"],
            "supporting": stats["supporting"],
            "contradicting": stats["contradicting"],
            "neutral": stats["neutral"],
            "supporting_ratio": stats["supporting_ratio"],
            "contradicting_ratio": stats["contradicting_ratio"],
            "neutral_ratio": stats["neutral_ratio"],
            "total_weight": stats["total_weight"],
            "is_symmetric": stats["is_symmetric"],
        }

    # -----------------------------------------------------
    # Stats and instrumentation
    # -----------------------------------------------------

    def get_stats(self) -> DetectorStats:
        """Return the aggregate detector statistics snapshot."""
        with self._lock:
            return self._stats

    # -----------------------------------------------------
    # Internal helpers - profile and stats bookkeeping
    # -----------------------------------------------------

    def _get_or_create_profile(self, agent_id: str) -> BiasProfile:
        """Fetch or create the BiasProfile for the given agent.

        Caller is expected to already hold self._lock.
        """
        if agent_id not in self._profiles:
            self._profiles[agent_id] = BiasProfile(agent_id=agent_id)
        return self._profiles[agent_id]

    def _increment_detection_stats(self, detection: BiasDetection) -> None:
        """Update aggregate counters for a newly stored detection."""
        self._stats.total_detections += 1
        self._stats.detections_by_type[detection.bias_type] = (
            self._stats.detections_by_type.get(detection.bias_type, 0) + 1
        )
        self._stats.detections_by_severity[detection.severity] = (
            self._stats.detections_by_severity.get(detection.severity, 0) + 1
        )

    def _decrement_detection_stats(self, detection: BiasDetection) -> None:
        """Reverse the aggregate counter updates for a detection.

        Used when detect_biases is re-run on an audit and the previous
        detections need to be discarded without double counting.
        """
        self._stats.total_detections = max(0, self._stats.total_detections - 1)
        if detection.resolved:
            self._stats.resolved_detections = max(0, self._stats.resolved_detections - 1)
        cur_type = self._stats.detections_by_type.get(detection.bias_type, 0)
        if cur_type <= 1:
            self._stats.detections_by_type.pop(detection.bias_type, None)
        else:
            self._stats.detections_by_type[detection.bias_type] = cur_type - 1
        cur_sev = self._stats.detections_by_severity.get(detection.severity, 0)
        if cur_sev <= 1:
            self._stats.detections_by_severity.pop(detection.severity, None)
        else:
            self._stats.detections_by_severity[detection.severity] = cur_sev - 1

    # -----------------------------------------------------
    # Internal helpers - evidence extraction
    # -----------------------------------------------------

    def _coerce_role(self, value: Any) -> EvidenceRole:
        """Best-effort conversion of an arbitrary value into an EvidenceRole."""
        if isinstance(value, EvidenceRole):
            return value
        if isinstance(value, str):
            try:
                return EvidenceRole(value.lower())
            except ValueError:
                low = value.lower()
                if low in ("support", "supporting", "for", "pro"):
                    return EvidenceRole.SUPPORTING
                if low in ("contradict", "contradicting", "against", "con"):
                    return EvidenceRole.CONTRADICTING
        return EvidenceRole.NEUTRAL

    def _evidence_stats(self, evidence_items: List[BiasEvidence]) -> Dict[str, Any]:
        """Compute summary statistics for a list of evidence items."""
        total = len(evidence_items)
        supporting = sum(1 for e in evidence_items if e.role == EvidenceRole.SUPPORTING)
        contradicting = sum(1 for e in evidence_items if e.role == EvidenceRole.CONTRADICTING)
        neutral = sum(1 for e in evidence_items if e.role == EvidenceRole.NEUTRAL)
        supporting_ratio = (supporting / total) if total else 0.0
        contradicting_ratio = (contradicting / total) if total else 0.0
        neutral_ratio = (neutral / total) if total else 0.0
        total_weight = sum(e.weight for e in evidence_items)
        # Symmetric when supporting and contradicting counts are within
        # one item of each other, or within 10% of the total.
        symmetry_threshold = max(1, int(0.1 * total)) if total else 0
        is_symmetric = abs(supporting - contradicting) <= symmetry_threshold
        return {
            "total": total,
            "supporting": supporting,
            "contradicting": contradicting,
            "neutral": neutral,
            "supporting_ratio": round(supporting_ratio, 4),
            "contradicting_ratio": round(contradicting_ratio, 4),
            "neutral_ratio": round(neutral_ratio, 4),
            "total_weight": round(total_weight, 4),
            "is_symmetric": is_symmetric,
            "items": evidence_items,
        }

    def _extract_evidence(
        self,
        trace: str,
        context: Dict[str, Any],
    ) -> List[BiasEvidence]:
        """Build a list of BiasEvidence objects from context or trace text.

        If context supplies an "evidence" list it is normalized and used
        verbatim. Otherwise the reasoning trace is split into clauses on
        common connectives and each clause is classified by role.
        """
        raw = context.get("evidence") if context else None
        if raw and isinstance(raw, list):
            items: List[BiasEvidence] = []
            for idx, entry in enumerate(raw):
                if isinstance(entry, BiasEvidence):
                    items.append(entry)
                elif isinstance(entry, dict):
                    description = str(entry.get("description", ""))
                    role = self._coerce_role(entry.get("role"))
                    weight = float(entry.get("weight", 1.0))
                    source = str(entry.get("source", "context"))
                    items.append(BiasEvidence(
                        evidence_id=str(entry.get(
                            "evidence_id", f"ev_{idx}_{uuid.uuid4().hex[:8]}"
                        )),
                        description=description,
                        role=role,
                        weight=weight,
                        source=source,
                    ))
            if items:
                return items

        # Fallback: derive evidence from the reasoning trace itself.
        clauses = self._split_clauses(trace)
        items = []
        for idx, clause in enumerate(clauses):
            role = self._classify_clause(clause)
            weight = self._clause_weight(clause, idx, len(clauses))
            items.append(BiasEvidence(
                evidence_id=f"ev_{idx}_{uuid.uuid4().hex[:8]}",
                description=clause.strip(),
                role=role,
                weight=weight,
                source="reasoning_trace",
            ))
        return items

    def _split_clauses(self, trace: str) -> List[str]:
        """Split a reasoning trace into clauses on common connectives."""
        if not trace:
            return []
        # Split on connectives and punctuation while keeping clause text.
        parts = re.split(
            r"(?:\bbecause\b|\bsince\b|\btherefore\b|\bso\b|\bthus\b|\bhence\b|,|;|\.)",
            trace,
            flags=re.IGNORECASE,
        )
        return [p.strip() for p in parts if p and p.strip()]

    def _classify_clause(self, clause: str) -> EvidenceRole:
        """Classify a single clause into a supporting/contradicting/neutral role."""
        low = clause.lower()
        if any(k in low for k in _CONTRADICTION_KEYWORDS):
            return EvidenceRole.CONTRADICTING
        if any(k in low for k in _CONFIRMATION_KEYWORDS):
            return EvidenceRole.SUPPORTING
        if any(k in low for k in _NEUTRAL_KEYWORDS):
            return EvidenceRole.NEUTRAL
        return EvidenceRole.NEUTRAL

    def _clause_weight(self, clause: str, idx: int, total: int) -> float:
        """Assign a weight to a clause based on its position.

        Earlier clauses carry more weight to mirror the anchoring effect
        that the detector is trying to surface. Weights decay linearly
        from 1.0 (first clause) down toward 0.5 (last clause).
        """
        base = 1.0
        if total <= 1:
            return base
        decay = 0.5 * (1.0 - (idx / max(total - 1, 1)))
        return round(base * (0.5 + decay), 4)

    # -----------------------------------------------------
    # Per-bias detectors
    # -----------------------------------------------------

    def _detect_confirmation(
        self,
        audit: ReasoningAudit,
        text: str,
        evidence_stats: Dict[str, Any],
        evidence_items: List[BiasEvidence],
    ) -> List[BiasDetection]:
        """Confirmation bias: evidence is heavily skewed toward supporting."""
        detections: List[BiasDetection] = []
        supporting_ratio = evidence_stats.get("supporting_ratio", 0.0)
        contradicting_ratio = evidence_stats.get("contradicting_ratio", 0.0)
        total = evidence_stats.get("total", 0)
        if total and supporting_ratio > 0.7 and contradicting_ratio < 0.2:
            if supporting_ratio > 0.9:
                severity = BiasSeverity.HIGH
            else:
                severity = BiasSeverity.MODERATE
            supporting_evidence = [
                e for e in evidence_items if e.role == EvidenceRole.SUPPORTING
            ]
            detections.append(BiasDetection(
                detection_id=f"det_{uuid.uuid4().hex}",
                audit_id=audit.audit_id,
                bias_type=BiasType.CONFIRMATION,
                severity=severity,
                description=(
                    f"Evidence is heavily skewed toward supporting hypotheses "
                    f"({supporting_ratio:.0%} supporting, "
                    f"{contradicting_ratio:.0%} contradicting)."
                ),
                evidence=supporting_evidence,
                confidence=round(min(0.99, supporting_ratio), 4),
            ))
        return detections

    def _detect_anchoring(
        self,
        audit: ReasoningAudit,
        text: str,
        evidence_items: List[BiasEvidence],
    ) -> List[BiasDetection]:
        """Anchoring bias: first piece of evidence carries disproportionate weight."""
        detections: List[BiasDetection] = []
        if len(evidence_items) < 2:
            return detections
        first = evidence_items[0]
        total_weight = sum(e.weight for e in evidence_items)
        if total_weight <= 0:
            return detections
        first_share = first.weight / total_weight
        if first_share > 0.5:
            if first_share > 0.7:
                severity = BiasSeverity.HIGH
            else:
                severity = BiasSeverity.MODERATE
            anchor_hit = any(k in text for k in _ANCHORING_KEYWORDS)
            confidence = round(
                min(0.95, first_share + (0.1 if anchor_hit else 0.0)), 4
            )
            detections.append(BiasDetection(
                detection_id=f"det_{uuid.uuid4().hex}",
                audit_id=audit.audit_id,
                bias_type=BiasType.ANCHORING,
                severity=severity,
                description=(
                    f"First piece of evidence carries {first_share:.0%} of "
                    f"total weight, indicating anchoring on initial information."
                ),
                evidence=[first],
                confidence=confidence,
            ))
        return detections

    def _detect_recency(
        self,
        audit: ReasoningAudit,
        text: str,
        evidence_items: List[BiasEvidence],
    ) -> List[BiasDetection]:
        """Recency bias: most recent evidence dominates the reasoning."""
        detections: List[BiasDetection] = []
        if not evidence_items:
            return detections
        last = evidence_items[-1]
        total_weight = sum(e.weight for e in evidence_items)
        if total_weight <= 0:
            return detections
        last_share = last.weight / total_weight
        recency_hit = any(k in text for k in _RECENCY_KEYWORDS)
        if recency_hit and last_share >= 0.3:
            if last_share < 0.5:
                severity = BiasSeverity.MODERATE
            else:
                severity = BiasSeverity.HIGH
            detections.append(BiasDetection(
                detection_id=f"det_{uuid.uuid4().hex}",
                audit_id=audit.audit_id,
                bias_type=BiasType.RECENCY,
                severity=severity,
                description=(
                    "Most recent evidence appears to dominate the reasoning; "
                    "earlier evidence may be under-weighted."
                ),
                evidence=[last],
                confidence=round(min(0.9, last_share + 0.1), 4),
            ))
        return detections

    def _detect_overconfidence(
        self,
        audit: ReasoningAudit,
        text: str,
        evidence_stats: Dict[str, Any],
        evidence_items: List[BiasEvidence],
    ) -> List[BiasDetection]:
        """Overconfidence bias: high-confidence claims without sufficient evidence."""
        detections: List[BiasDetection] = []
        total = evidence_stats.get("total", 0)
        hits = [k for k in _OVERCONFIDENCE_KEYWORDS if k in text]
        # Respect an explicit confidence supplied by the caller.
        declared = audit.context.get("confidence") if audit.context else None
        try:
            declared_val = float(declared) if declared is not None else None
        except (TypeError, ValueError):
            declared_val = None
        triggered = bool(hits) or (declared_val is not None and declared_val > 0.9)
        if triggered and total < 3:
            if (declared_val or 0.0) > 0.95:
                severity = BiasSeverity.HIGH
            else:
                severity = BiasSeverity.MODERATE
            evidence = evidence_items[:1] if evidence_items else []
            confidence = round(min(0.95, 0.6 + 0.05 * len(hits)), 4)
            keyword_summary = ", ".join(hits) if hits else "none"
            detections.append(BiasDetection(
                detection_id=f"det_{uuid.uuid4().hex}",
                audit_id=audit.audit_id,
                bias_type=BiasType.OVERCONFIDENCE,
                severity=severity,
                description=(
                    "High-confidence claim made without sufficient supporting "
                    f"evidence ({total} item(s), keywords: {keyword_summary})."
                ),
                evidence=evidence,
                confidence=confidence,
            ))
        return detections

    def _detect_availability(
        self,
        audit: ReasoningAudit,
        text: str,
        evidence_items: List[BiasEvidence],
    ) -> List[BiasDetection]:
        """Availability bias: similar evidence types cluster in the reasoning."""
        detections: List[BiasDetection] = []
        if not evidence_items:
            return detections
        # Cluster evidence by significant tokens to detect availability.
        token_buckets: Dict[str, List[BiasEvidence]] = {}
        for e in evidence_items:
            tokens = [t for t in e.description.lower().split() if len(t) > 3]
            for token in tokens:
                token_buckets.setdefault(token, []).append(e)
        dominant_token = None
        dominant_count = 0
        for token, items in token_buckets.items():
            if len(items) > dominant_count:
                dominant_count = len(items)
                dominant_token = token
        availability_hit = any(k in text for k in _AVAILABILITY_KEYWORDS)
        if dominant_token and dominant_count >= 2 and availability_hit:
            clustered = token_buckets[dominant_token]
            if dominant_count < 3:
                severity = BiasSeverity.LOW
            else:
                severity = BiasSeverity.MODERATE
            detections.append(BiasDetection(
                detection_id=f"det_{uuid.uuid4().hex}",
                audit_id=audit.audit_id,
                bias_type=BiasType.AVAILABILITY,
                severity=severity,
                description=(
                    f"Evidence clusters around the term '{dominant_token}' "
                    f"({dominant_count} mentions), suggesting availability-driven recall."
                ),
                evidence=list(clustered),
                confidence=round(min(0.85, 0.4 + 0.15 * dominant_count), 4),
            ))
        return detections

    def _detect_sunk_cost(
        self,
        audit: ReasoningAudit,
        text: str,
        context: Dict[str, Any],
        evidence_items: List[BiasEvidence],
    ) -> List[BiasDetection]:
        """Sunk-cost bias: reasoning references prior investment or commitment."""
        detections: List[BiasDetection] = []
        ctx_text = " ".join(str(v) for v in (context or {}).values()).lower()
        combined = f"{text} {ctx_text}"
        hits = [k for k in _SUNK_COST_KEYWORDS if k in combined]
        if hits:
            if len(hits) >= 3:
                severity = BiasSeverity.HIGH
            else:
                severity = BiasSeverity.MODERATE
            detections.append(BiasDetection(
                detection_id=f"det_{uuid.uuid4().hex}",
                audit_id=audit.audit_id,
                bias_type=BiasType.SUNK_COST,
                severity=severity,
                description=(
                    "Reasoning references prior investment or commitment "
                    f"(keywords: {', '.join(hits)}), indicating sunk-cost influence."
                ),
                evidence=evidence_items[:1] if evidence_items else [],
                confidence=round(min(0.9, 0.5 + 0.1 * len(hits)), 4),
            ))
        return detections

    def _detect_framing(
        self,
        audit: ReasoningAudit,
        text: str,
        context: Dict[str, Any],
        evidence_items: List[BiasEvidence],
    ) -> List[BiasDetection]:
        """Framing bias: reasoning uses gain/loss framing language."""
        detections: List[BiasDetection] = []
        ctx_text = " ".join(str(v) for v in (context or {}).values()).lower()
        combined = f"{text} {ctx_text}"
        hits = [k for k in _FRAMING_KEYWORDS if k in combined]
        if hits:
            if len(hits) < 3:
                severity = BiasSeverity.LOW
            else:
                severity = BiasSeverity.MODERATE
            # Detect gain/loss asymmetry to escalate severity.
            loss_hits = [
                k for k in ("loss", "risk", "cost", "forfeit", "avoid", "lose")
                if k in combined
            ]
            gain_hits = [
                k for k in ("gain", "save", "benefit", "secure", "protect", "preserve")
                if k in combined
            ]
            if loss_hits and not gain_hits:
                severity = BiasSeverity.HIGH
            detections.append(BiasDetection(
                detection_id=f"det_{uuid.uuid4().hex}",
                audit_id=audit.audit_id,
                bias_type=BiasType.FRAMING,
                severity=severity,
                description=(
                    "Reasoning uses framing language that may steer the "
                    f"decision (keywords: {', '.join(hits)})."
                ),
                evidence=evidence_items[:1] if evidence_items else [],
                confidence=round(min(0.85, 0.45 + 0.08 * len(hits)), 4),
            ))
        return detections

    def _detect_representativeness(
        self,
        audit: ReasoningAudit,
        text: str,
        evidence_items: List[BiasEvidence],
    ) -> List[BiasDetection]:
        """Representativeness bias: reasoning relies on similarity rather than base rates."""
        detections: List[BiasDetection] = []
        hits = [k for k in _REPRESENTATIVENESS_KEYWORDS if k in text]
        base_rate_mentioned = (
            "base rate" in text or "base-rate" in text or "prevalence" in text
        )
        if hits and not base_rate_mentioned:
            if len(hits) >= 2:
                severity = BiasSeverity.MODERATE
            else:
                severity = BiasSeverity.LOW
            detections.append(BiasDetection(
                detection_id=f"det_{uuid.uuid4().hex}",
                audit_id=audit.audit_id,
                bias_type=BiasType.REPRESENTATIVENESS,
                severity=severity,
                description=(
                    "Reasoning relies on similarity judgements without "
                    f"reference to base rates (keywords: {', '.join(hits)})."
                ),
                evidence=evidence_items[:1] if evidence_items else [],
                confidence=round(min(0.85, 0.5 + 0.1 * len(hits)), 4),
            ))
        return detections

    # -----------------------------------------------------
    # Strategy descriptions
    # -----------------------------------------------------

    def _describe_strategy(
        self,
        strategy: DebiasingStrategy,
        detection: BiasDetection,
    ) -> str:
        """Render a human-readable description for a debiasing action."""
        templates = {
            DebiasingStrategy.COUNTERFACTUAL_PROBING: (
                "Probe alternative scenarios that would falsify the "
                "{bias} hypothesis for detection {detection_id}."
            ),
            DebiasingStrategy.PERSPECTIVE_SHIFTING: (
                "Re-evaluate the reasoning from an independent reviewer "
                "perspective to counteract {bias} (detection {detection_id})."
            ),
            DebiasingStrategy.EVIDENCE_DIVERSIFICATION: (
                "Actively gather contradicting evidence to balance the "
                "{bias} tendency flagged in detection {detection_id}."
            ),
            DebiasingStrategy.BASE_RATE_RECALIBRATION: (
                "Re-anchor the {bias} judgement for detection "
                "{detection_id} against base-rate statistics."
            ),
            DebiasingStrategy.BLIND_REVIEW: (
                "Re-assess detection {detection_id} with identifying "
                "details masked to mitigate {bias}."
            ),
            DebiasingStrategy.DELAYED_JUDGMENT: (
                "Defer the {bias}-sensitive conclusion in detection "
                "{detection_id} to allow for cooler reasoning."
            ),
        }
        template = templates.get(strategy, "Apply {bias} mitigation to {detection_id}.")
        return template.format(
            bias=detection.bias_type.value,
            detection_id=detection.detection_id,
        )

    # -----------------------------------------------------
    # Maintenance
    # -----------------------------------------------------

    def reset(self) -> None:
        """Clear all stored state. Intended for tests and resets."""
        with self._lock:
            self._audits.clear()
            self._detections.clear()
            self._debiasing_actions.clear()
            self._profiles.clear()
            self._stats = DetectorStats()


# =========================================================
# Module-level singleton
# =========================================================

_engine: Optional[AgentCognitiveBiasDetector] = None
_engine_lock = threading.Lock()


def get_bias_detector() -> AgentCognitiveBiasDetector:
    """Return the process-wide AgentCognitiveBiasDetector singleton.

    The singleton is created lazily on first access and is safe to call
    from multiple threads. Subsequent calls return the same instance.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = AgentCognitiveBiasDetector()
    return _engine


def reset_bias_detector() -> None:
    """Reset the process-wide AgentCognitiveBiasDetector singleton.

    Clears any in-memory state on the existing instance (if any) and
    drops the singleton reference so the next get_bias_detector() call
    creates a fresh detector.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
