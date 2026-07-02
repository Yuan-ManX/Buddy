"""Agent Cognitive Horizon Engine — managing the epistemic frontier of an agent.

Every cognitive agent operates inside a finite envelope of competence. The
engine maps that envelope using a known/unknown matrix and a HorizonProximity
measure from INTERIOR through UNCHARTED. Competence is tracked per
KnowledgeDomain on a Dreyfus-style ladder, and boundary responses (PROCEED,
LEARN, DEFER, REFER, ABSTAIN, ESCALATE) are recommended when reasoning
approaches the edge of what the agent actually knows.

Architecture:
  AgentCognitiveHorizon (singleton)
  ├── DomainCompetence  (per-domain competence level and confidence)
  ├── HorizonProbe      (a reasoning attempt near the boundary)
  ├── BoundaryEvent     (a recorded encounter with the competence edge)
  ├── LearningRequest   (a request to expand the horizon in a domain)
  ├── DeferDecision     (a decision to defer beyond the boundary)
  ├── HorizonProfile    (per-agent map of the competence envelope)
  └── HorizonStats      (engine-wide aggregate statistics)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class KnowledgeDomain(str, Enum):
    """Cognitive domains over which an agent may hold competence.

    Each domain is an independent axis of capability: an agent can be expert in
    one and novice in another, and the horizon is mapped per domain.
    """
    REASONING = "reasoning"            # deductive, inductive, abductive inference
    PLANNING = "planning"              # goal decomposition and step sequencing
    MEMORY = "memory"                  # recall, consolidation, retrieval
    LANGUAGE = "language"              # comprehension and generation of text
    PERCEPTION = "perception"          # parsing signals into structured meaning
    TOOL_USE = "tool_use"              # selecting and operating external tools
    COLLABORATION = "collaboration"    # coordinating with other agents or humans
    CREATIVITY = "creativity"          # novel synthesis and divergence
    ANALYTICS = "analytics"            # quantitative reasoning and statistics
    CODING = "coding"                  # source code authoring and review


class EpistemicState(str, Enum):
    """Epistemic classification of a knowledge item relative to an agent."""
    KNOWN_KNOWN = "known_known"          # known and recognised as known
    KNOWN_UNKNOWN = "known_unknown"      # gap is acknowledged
    UNKNOWN_UNKNOWN = "unknown_unknown"  # blind spot, no awareness of the gap
    PARTIALLY_KNOWN = "partially_known"  # fragmentary hold with holes
    DISPUTED = "disputed"                # conflicting candidates held at once
    OBSOLETE = "obsolete"                # superseded or decayed knowledge


class HorizonProximity(str, Enum):
    """Where a reasoning attempt sits relative to the competence frontier."""
    INTERIOR = "interior"      # deep inside known territory
    NEAR = "near"              # close to the boundary, still reliable
    AT = "at"                  # on the horizon edge itself
    BEYOND = "beyond"          # just past the horizon, describable but uncertain
    UNCHARTED = "uncharted"    # no map exists for this region


class BoundaryResponse(str, Enum):
    """Recommended action when reasoning meets the horizon."""
    PROCEED = "proceed"                    # continue normally
    PROCEED_WITH_CAUTION = "proceed_with_caution"  # continue but verify
    LEARN = "learn"                        # acquire the missing competence
    DEFER = "defer"                        # hand off to a more capable agent
    REFER = "refer"                        # route to an external authority
    ABSTAIN = "abstain"                    # decline to act
    ESCALATE = "escalate"                  # raise to a human or supervisor


class CompetenceLevel(str, Enum):
    """Dreyfus-style ladder of skill acquisition within a domain."""
    NOVICE = "novice"                          # rule-bound, no context
    ADVANCED_BEGINNER = "advanced_beginner"    # recognises some context
    COMPETENT = "competent"                    # handles standard cases alone
    PROFICIENT = "proficient"                  # intuitive grasp of priorities
    EXPERT = "expert"                          # fluent, sees deep patterns
    MASTER = "master"                          # shapes the domain itself


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DomainCompetence:
    """An agent's mapped competence in a single knowledge domain.

    `boundary_distance` is the engine's estimate of how far the agent's reach
    extends into the domain on a [0, 1] scale. It is derived from the
    competence level (a ceiling on reach) modulated by confidence (how reliably
    that reach holds). A master with low confidence still has a short horizon;
    a competent agent with high confidence reaches further than one without.
    """
    competence_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    domain: KnowledgeDomain = KnowledgeDomain.REASONING
    level: CompetenceLevel = CompetenceLevel.NOVICE
    confidence: float = 0.5
    samples_seen: int = 0
    success_rate: float = 0.5
    last_exercised: str = ""
    boundary_distance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competence_id": self.competence_id,
            "agent_id": self.agent_id,
            "domain": self.domain.value
            if isinstance(self.domain, KnowledgeDomain)
            else str(self.domain),
            "level": self.level.value
            if isinstance(self.level, CompetenceLevel)
            else str(self.level),
            "confidence": self.confidence,
            "samples_seen": self.samples_seen,
            "success_rate": self.success_rate,
            "last_exercised": self.last_exercised,
            "boundary_distance": self.boundary_distance,
        }


@dataclass
class HorizonProbe:
    """A single probe of the horizon for a (agent, domain) pair.

    Probing asks: given what this agent currently maps in this domain, where
    does this query sit? The answer is a proximity, an epistemic state, and a
    confidence reading taken at the boundary. Evidence signals are the cues
    that informed the probe (e.g. hedging language, missing entities, tool
    failures) and are stored verbatim for later auditing.
    """
    probe_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    domain: KnowledgeDomain = KnowledgeDomain.REASONING
    probe_query: str = ""
    proximity: HorizonProximity = HorizonProximity.UNCHARTED
    detected_state: EpistemicState = EpistemicState.UNKNOWN_UNKNOWN
    confidence_at_boundary: float = 0.0
    evidence_signals: List[str] = field(default_factory=list)
    probed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "agent_id": self.agent_id,
            "domain": self.domain.value
            if isinstance(self.domain, KnowledgeDomain)
            else str(self.domain),
            "probe_query": self.probe_query,
            "proximity": self.proximity.value
            if isinstance(self.proximity, HorizonProximity)
            else str(self.proximity),
            "detected_state": self.detected_state.value
            if isinstance(self.detected_state, EpistemicState)
            else str(self.detected_state),
            "confidence_at_boundary": self.confidence_at_boundary,
            "evidence_signals": list(self.evidence_signals),
            "probed_at": self.probed_at,
        }


@dataclass
class BoundaryEvent:
    """A recorded encounter with the horizon and the response it triggered.

    Events are the audit trail of boundary behaviour: every time an agent
    approaches, reaches, or crosses its horizon, an event captures the
    proximity, the chosen response, the triggering context, and (later) the
    resolution. Unresolved events flag open epistemic risk.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    domain: KnowledgeDomain = KnowledgeDomain.REASONING
    proximity: HorizonProximity = HorizonProximity.UNCHARTED
    response: BoundaryResponse = BoundaryResponse.PROCEED
    trigger: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution: str = ""
    occurred_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "domain": self.domain.value
            if isinstance(self.domain, KnowledgeDomain)
            else str(self.domain),
            "proximity": self.proximity.value
            if isinstance(self.proximity, HorizonProximity)
            else str(self.proximity),
            "response": self.response.value
            if isinstance(self.response, BoundaryResponse)
            else str(self.response),
            "trigger": self.trigger,
            "context": dict(self.context),
            "resolved": self.resolved,
            "resolution": self.resolution,
            "occurred_at": self.occurred_at,
        }


@dataclass
class LearningRequest:
    """A request to expand the horizon by acquiring a missing concept.

    Spawned when the recommended response is LEARN (or when an agent
    proactively wants to push a boundary outward). The `trigger_probe_id`
    links the request back to the probe that exposed the gap, so the learning
    loop can close the loop on the exact epistemic hole.
    """
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    domain: KnowledgeDomain = KnowledgeDomain.REASONING
    trigger_probe_id: str = ""
    target_concept: str = ""
    urgency: float = 0.5
    estimated_effort: float = 1.0
    requested_at: str = ""
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "domain": self.domain.value
            if isinstance(self.domain, KnowledgeDomain)
            else str(self.domain),
            "trigger_probe_id": self.trigger_probe_id,
            "target_concept": self.target_concept,
            "urgency": self.urgency,
            "estimated_effort": self.estimated_effort,
            "requested_at": self.requested_at,
            "status": self.status,
        }


@dataclass
class DeferDecision:
    """A decision to hand a (agent, domain) task off to a more capable party.

    Recorded whenever DEFER is chosen. The gap between `original_confidence`
    and `confidence_threshold` quantifies how far below the bar the agent was;
    that delta is a useful signal for prioritising later learning.
    """
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    domain: KnowledgeDomain = KnowledgeDomain.REASONING
    deferred_to: str = ""
    reason: str = ""
    confidence_threshold: float = 0.7
    original_confidence: float = 0.0
    decided_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "domain": self.domain.value
            if isinstance(self.domain, KnowledgeDomain)
            else str(self.domain),
            "deferred_to": self.deferred_to,
            "reason": self.reason,
            "confidence_threshold": self.confidence_threshold,
            "original_confidence": self.original_confidence,
            "decided_at": self.decided_at,
        }


@dataclass
class HorizonProfile:
    """A snapshot of an agent's horizon across all domains.

    Aggregates the agent's mapped competences, the proximity distribution of
    those competences, and the volume of probes and events the agent has
    generated. `epistemic_coverage` is the fraction of all KnowledgeDomain
    values for which the agent holds at least some competence — a coarse
    measure of how much of the territory has been mapped at all.
    """
    agent_id: str = ""
    total_domains_mapped: int = 0
    avg_boundary_distance: float = 0.0
    competence_distribution: Dict[CompetenceLevel, int] = field(default_factory=dict)
    proximity_distribution: Dict[HorizonProximity, int] = field(default_factory=dict)
    epistemic_coverage: float = 0.0
    total_probes: int = 0
    total_events: int = 0
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "total_domains_mapped": self.total_domains_mapped,
            "avg_boundary_distance": self.avg_boundary_distance,
            "competence_distribution": {
                (k.value if isinstance(k, CompetenceLevel) else str(k)): v
                for k, v in self.competence_distribution.items()
            },
            "proximity_distribution": {
                (k.value if isinstance(k, HorizonProximity) else str(k)): v
                for k, v in self.proximity_distribution.items()
            },
            "epistemic_coverage": self.epistemic_coverage,
            "total_probes": self.total_probes,
            "total_events": self.total_events,
            "updated_at": self.updated_at,
        }


@dataclass
class HorizonStats:
    """Engine-wide aggregate statistics across all agents and domains."""
    total_competences: int = 0
    total_probes: int = 0
    total_events: int = 0
    total_learning_requests: int = 0
    total_defers: int = 0
    proximity_distribution: Dict[HorizonProximity, int] = field(default_factory=dict)
    response_distribution: Dict[BoundaryResponse, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_competences": self.total_competences,
            "total_probes": self.total_probes,
            "total_events": self.total_events,
            "total_learning_requests": self.total_learning_requests,
            "total_defers": self.total_defers,
            "proximity_distribution": {
                (k.value if isinstance(k, HorizonProximity) else str(k)): v
                for k, v in self.proximity_distribution.items()
            },
            "response_distribution": {
                (k.value if isinstance(k, BoundaryResponse) else str(k)): v
                for k, v in self.response_distribution.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# Agent Cognitive Horizon Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveHorizon:
    """Thread-safe engine that maps and manages each agent's epistemic horizon.

    The engine holds seven stores keyed by identifier:

      * ``_competences``        — DomainCompetence by competence_id
      * ``_probes``             — HorizonProbe by probe_id
      * ``_events``             — BoundaryEvent by event_id
      * ``_learning_requests``  — LearningRequest by request_id
      * ``_defer_decisions``    — DeferDecision by decision_id
      * ``_profiles``           — HorizonProfile by agent_id
      * ``_stats``              — rolling counters for fast aggregate reads

    All mutations are guarded by a single reentrant lock so that public methods
    may safely call one another without self-deadlock. The horizon model is
    deliberately heuristic: boundary distance is a function of competence level
    and confidence, proximity is banded from that distance, and recommended
    responses are look-ups over (proximity, confidence). These heuristics are
    transparent and auditable rather than learned, which keeps the engine
    deterministic and easy to reason about.
    """

    # Boundary-distance ceiling per competence level. The product of this base
    # and the agent's confidence yields boundary_distance in [0, 1].
    _LEVEL_BASE_DISTANCE: Dict[CompetenceLevel, float] = {
        CompetenceLevel.NOVICE: 0.10,
        CompetenceLevel.ADVANCED_BEGINNER: 0.25,
        CompetenceLevel.COMPETENT: 0.45,
        CompetenceLevel.PROFICIENT: 0.65,
        CompetenceLevel.EXPERT: 0.85,
        CompetenceLevel.MASTER: 0.95,
    }

    # Bands that turn a continuous boundary_distance into a discrete proximity.
    _INTERIOR_THRESHOLD: float = 0.70
    _NEAR_THRESHOLD: float = 0.40
    _AT_THRESHOLD: float = 0.15

    # Confidence gates that pick between adjacent responses at a proximity.
    _AT_LEARN_CONFIDENCE: float = 0.40    # below this at the horizon -> LEARN
    _BEYOND_DEFER_CONFIDENCE: float = 0.30  # below this beyond horizon -> DEFER

    # Default confidence bar above which a task is deferred rather than owned.
    _DEFAULT_DEFER_THRESHOLD: float = 0.70

    # Mapping from proximity to the epistemic state it implies.
    _STATE_FROM_PROXIMITY: Dict[HorizonProximity, EpistemicState] = {
        HorizonProximity.INTERIOR: EpistemicState.KNOWN_KNOWN,
        HorizonProximity.NEAR: EpistemicState.PARTIALLY_KNOWN,
        HorizonProximity.AT: EpistemicState.KNOWN_UNKNOWN,
        HorizonProximity.BEYOND: EpistemicState.KNOWN_UNKNOWN,
        HorizonProximity.UNCHARTED: EpistemicState.UNKNOWN_UNKNOWN,
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._competences: Dict[str, DomainCompetence] = {}
        self._probes: Dict[str, HorizonProbe] = {}
        self._events: Dict[str, BoundaryEvent] = {}
        self._learning_requests: Dict[str, LearningRequest] = {}
        self._defer_decisions: Dict[str, DeferDecision] = {}
        self._profiles: Dict[str, HorizonProfile] = {}
        # Rolling counters kept in sync with the stores above. They mirror the
        # lengths of the primary stores and let get_stats() avoid full scans for
        # the scalar totals; distributions are still computed by scanning.
        self._stats: Dict[str, int] = {
            "total_competences": 0,
            "total_probes": 0,
            "total_events": 0,
            "total_learning_requests": 0,
            "total_defers": 0,
        }

    # ── Competence Management ─────────────────────────────────────────

    def register_competence(
        self,
        agent_id: str,
        domain: KnowledgeDomain,
        level: CompetenceLevel,
        confidence: float = 0.5,
        success_rate: float = 0.5,
        samples_seen: int = 0,
    ) -> DomainCompetence:
        """Register (or refresh) an agent's competence in a domain.

        ``boundary_distance`` is computed as ``level_base * confidence`` where
        ``level_base`` is the ceiling for the given CompetenceLevel. Both
        confidence and success_rate are clamped to [0, 1] and samples_seen is
        clamped to a non-negative integer. A new competence_id is always
        allocated; callers wishing to "update" should re-register, and the
        most recent registration wins when probing or recommending.
        """
        with self._lock:
            confidence = max(0.0, min(1.0, float(confidence)))
            success_rate = max(0.0, min(1.0, float(success_rate)))
            samples_seen = max(0, int(samples_seen))
            base = self._LEVEL_BASE_DISTANCE.get(level, self._LEVEL_BASE_DISTANCE[CompetenceLevel.NOVICE])
            boundary_distance = max(0.0, min(1.0, base * confidence))

            competence = DomainCompetence(
                competence_id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
                domain=domain,
                level=level,
                confidence=confidence,
                samples_seen=samples_seen,
                success_rate=success_rate,
                last_exercised=self._iso_now(),
                boundary_distance=boundary_distance,
            )
            self._competences[competence.competence_id] = competence
            self._stats["total_competences"] += 1
            # A re-registration changes the agent's horizon, so invalidate any
            # cached profile so the next access recomputes from fresh data.
            self._profiles.pop(agent_id, None)
            return competence

    def get_competence(self, competence_id: str) -> Optional[DomainCompetence]:
        """Retrieve a competence record by its identifier."""
        with self._lock:
            return self._competences.get(competence_id)

    def list_competences(
        self,
        agent_id: Optional[str] = None,
        domain: Optional[KnowledgeDomain] = None,
    ) -> List[DomainCompetence]:
        """List competence records, optionally filtered by agent and/or domain."""
        with self._lock:
            results: List[DomainCompetence] = []
            for competence in self._competences.values():
                if agent_id is not None and competence.agent_id != agent_id:
                    continue
                if domain is not None and competence.domain != domain:
                    continue
                results.append(competence)
            return results

    # ── Horizon Probing ───────────────────────────────────────────────

    def probe_horizon(
        self,
        agent_id: str,
        domain: KnowledgeDomain,
        probe_query: str,
        evidence_signals: Optional[List[str]] = None,
    ) -> HorizonProbe:
        """Probe where a query sits relative to the agent's horizon in a domain.

        If the agent has no mapped competence in the domain, the probe returns
        UNCHARTED / UNKNOWN_UNKNOWN with zero boundary confidence. Otherwise the
        competence's boundary_distance is banded into a proximity, the
        epistemic state is derived from that proximity, and the confidence at
        the boundary is taken from the competence's current confidence.
        """
        with self._lock:
            competence = self._find_competence_locked(agent_id, domain)
            if competence is None:
                proximity = HorizonProximity.UNCHARTED
                confidence_at_boundary = 0.0
            else:
                proximity = self._proximity_from_boundary(competence.boundary_distance)
                confidence_at_boundary = competence.confidence
                # Touching the competence at probe time counts as exercise.
                competence.last_exercised = self._iso_now()

            detected_state = self._state_from_proximity(proximity)
            probe = HorizonProbe(
                probe_id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
                domain=domain,
                probe_query=probe_query,
                proximity=proximity,
                detected_state=detected_state,
                confidence_at_boundary=confidence_at_boundary,
                evidence_signals=list(evidence_signals) if evidence_signals else [],
                probed_at=self._iso_now(),
            )
            self._probes[probe.probe_id] = probe
            self._stats["total_probes"] += 1
            self._profiles.pop(agent_id, None)
            return probe

    def get_probe(self, probe_id: str) -> Optional[HorizonProbe]:
        """Retrieve a horizon probe by its identifier."""
        with self._lock:
            return self._probes.get(probe_id)

    def list_probes(
        self,
        agent_id: Optional[str] = None,
        domain: Optional[KnowledgeDomain] = None,
        proximity: Optional[HorizonProximity] = None,
    ) -> List[HorizonProbe]:
        """List probes, optionally filtered by agent, domain, and/or proximity."""
        with self._lock:
            results: List[HorizonProbe] = []
            for probe in self._probes.values():
                if agent_id is not None and probe.agent_id != agent_id:
                    continue
                if domain is not None and probe.domain != domain:
                    continue
                if proximity is not None and probe.proximity != proximity:
                    continue
                results.append(probe)
            return results

    # ── Boundary Events ───────────────────────────────────────────────

    def record_event(
        self,
        agent_id: str,
        domain: KnowledgeDomain,
        proximity: HorizonProximity,
        response: BoundaryResponse,
        trigger: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> BoundaryEvent:
        """Record an encounter with the horizon and the response it triggered."""
        with self._lock:
            event = BoundaryEvent(
                event_id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
                domain=domain,
                proximity=proximity,
                response=response,
                trigger=trigger,
                context=dict(context) if context else {},
                resolved=False,
                resolution="",
                occurred_at=self._iso_now(),
            )
            self._events[event.event_id] = event
            self._stats["total_events"] += 1
            self._profiles.pop(agent_id, None)
            return event

    def get_event(self, event_id: str) -> Optional[BoundaryEvent]:
        """Retrieve a boundary event by its identifier."""
        with self._lock:
            return self._events.get(event_id)

    def list_events(
        self,
        agent_id: Optional[str] = None,
        response: Optional[BoundaryResponse] = None,
    ) -> List[BoundaryEvent]:
        """List boundary events, optionally filtered by agent and/or response."""
        with self._lock:
            results: List[BoundaryEvent] = []
            for event in self._events.values():
                if agent_id is not None and event.agent_id != agent_id:
                    continue
                if response is not None and event.response != response:
                    continue
                results.append(event)
            return results

    def resolve_event(self, event_id: str, resolution: str) -> Optional[BoundaryEvent]:
        """Mark a boundary event as resolved with a free-text resolution note.

        Returns the updated event, or None if the event cannot be found.
        """
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            event.resolved = True
            event.resolution = resolution
            return event

    # ── Learning Requests ─────────────────────────────────────────────

    def request_learning(
        self,
        agent_id: str,
        domain: KnowledgeDomain,
        trigger_probe_id: str,
        target_concept: str,
        urgency: float = 0.5,
        estimated_effort: float = 1.0,
    ) -> LearningRequest:
        """Create a learning request to close an identified epistemic gap.

        ``urgency`` is clamped to [0, 1] and ``estimated_effort`` is clamped to
        a non-negative float. The request starts in the "pending" status.
        """
        with self._lock:
            urgency = max(0.0, min(1.0, float(urgency)))
            estimated_effort = max(0.0, float(estimated_effort))
            request = LearningRequest(
                request_id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
                domain=domain,
                trigger_probe_id=trigger_probe_id,
                target_concept=target_concept,
                urgency=urgency,
                estimated_effort=estimated_effort,
                requested_at=self._iso_now(),
                status="pending",
            )
            self._learning_requests[request.request_id] = request
            self._stats["total_learning_requests"] += 1
            self._profiles.pop(agent_id, None)
            return request

    def get_learning_request(self, request_id: str) -> Optional[LearningRequest]:
        """Retrieve a learning request by its identifier."""
        with self._lock:
            return self._learning_requests.get(request_id)

    def list_learning_requests(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[LearningRequest]:
        """List learning requests, optionally filtered by agent and/or status."""
        with self._lock:
            results: List[LearningRequest] = []
            for request in self._learning_requests.values():
                if agent_id is not None and request.agent_id != agent_id:
                    continue
                if status is not None and request.status != status:
                    continue
                results.append(request)
            return results

    # ── Defer Decisions ───────────────────────────────────────────────

    def defer_decision(
        self,
        agent_id: str,
        domain: KnowledgeDomain,
        deferred_to: str,
        reason: str,
        original_confidence: float,
        confidence_threshold: float = 0.7,
    ) -> DeferDecision:
        """Record a decision to defer a task to a more capable party.

        ``original_confidence`` is clamped to [0, 1] and represents the
        confidence the agent had in its own ability to handle the task; the
        ``confidence_threshold`` is the bar it failed to clear. The delta
        between the two is the size of the competence shortfall.
        """
        with self._lock:
            original_confidence = max(0.0, min(1.0, float(original_confidence)))
            confidence_threshold = max(0.0, min(1.0, float(confidence_threshold)))
            decision = DeferDecision(
                decision_id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
                domain=domain,
                deferred_to=deferred_to,
                reason=reason,
                confidence_threshold=confidence_threshold,
                original_confidence=original_confidence,
                decided_at=self._iso_now(),
            )
            self._defer_decisions[decision.decision_id] = decision
            self._stats["total_defers"] += 1
            self._profiles.pop(agent_id, None)
            return decision

    def get_defer_decision(self, decision_id: str) -> Optional[DeferDecision]:
        """Retrieve a defer decision by its identifier."""
        with self._lock:
            return self._defer_decisions.get(decision_id)

    def list_defer_decisions(self, agent_id: Optional[str] = None) -> List[DeferDecision]:
        """List defer decisions, optionally filtered by agent."""
        with self._lock:
            if agent_id is None:
                return list(self._defer_decisions.values())
            return [
                d for d in self._defer_decisions.values() if d.agent_id == agent_id
            ]

    # ── Response Recommendation ───────────────────────────────────────

    def recommend_response(
        self,
        agent_id: str,
        domain: KnowledgeDomain,
    ) -> BoundaryResponse:
        """Recommend how the agent should respond at its current horizon.

        The recommendation is a pure function of the agent's proximity and
        confidence in the domain:

          * INTERIOR  -> PROCEED
          * NEAR      -> PROCEED_WITH_CAUTION
          * AT        -> LEARN if confidence < 0.4 else DEFER
          * BEYOND    -> DEFER if confidence < 0.3 else ABSTAIN
          * UNCHARTED -> ABSTAIN

        An agent with no mapped competence is treated as UNCHARTED and advised
        to ABSTAIN rather than fabricate.
        """
        with self._lock:
            competence = self._find_competence_locked(agent_id, domain)
            if competence is None:
                return BoundaryResponse.ABSTAIN

            proximity = self._proximity_from_boundary(competence.boundary_distance)
            confidence = competence.confidence

            if proximity == HorizonProximity.INTERIOR:
                return BoundaryResponse.PROCEED
            if proximity == HorizonProximity.NEAR:
                return BoundaryResponse.PROCEED_WITH_CAUTION
            if proximity == HorizonProximity.AT:
                if confidence < self._AT_LEARN_CONFIDENCE:
                    return BoundaryResponse.LEARN
                return BoundaryResponse.DEFER
            if proximity == HorizonProximity.BEYOND:
                # High confidence past the horizon is treated as overconfidence:
                # the agent should abstain rather than act on an unmapped claim.
                if confidence < self._BEYOND_DEFER_CONFIDENCE:
                    return BoundaryResponse.DEFER
                return BoundaryResponse.ABSTAIN
            return BoundaryResponse.ABSTAIN

    # ── Profiles ──────────────────────────────────────────────────────

    def get_or_create_profile(self, agent_id: str) -> HorizonProfile:
        """Return the agent's cached horizon profile, computing it if absent.

        The profile is a snapshot computed from the current stores. It is
        cached on the agent_id and invalidated whenever the agent's competences,
        probes, or events change. Call ``update_profile`` to force a refresh.
        """
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                profile = self._compute_profile_locked(agent_id)
                self._profiles[agent_id] = profile
            return profile

    def update_profile(self, agent_id: str, **kwargs: Any) -> HorizonProfile:
        """Refresh and optionally override fields of an agent's horizon profile.

        The profile is first recomputed from the live stores, then any supplied
        keyword overrides (matching HorizonProfile field names) are applied,
        and finally ``updated_at`` is stamped. This is the supported way to
        force a profile refresh after out-of-band changes.
        """
        with self._lock:
            profile = self._compute_profile_locked(agent_id)
            allowed = {
                "total_domains_mapped",
                "avg_boundary_distance",
                "competence_distribution",
                "proximity_distribution",
                "epistemic_coverage",
                "total_probes",
                "total_events",
            }
            for key, value in kwargs.items():
                if key in allowed:
                    setattr(profile, key, value)
            profile.updated_at = self._iso_now()
            self._profiles[agent_id] = profile
            return profile

    def list_profiles(self) -> List[HorizonProfile]:
        """List all cached horizon profiles."""
        with self._lock:
            return list(self._profiles.values())

    # ── Statistics & Reset ────────────────────────────────────────────

    def get_stats(self) -> HorizonStats:
        """Compute engine-wide aggregate statistics.

        Scalar totals are read from the rolling ``_stats`` counters (which stay
        in sync with the primary stores), while the proximity and response
        distributions are computed by scanning the probe and event stores so
        they always reflect the current state even after resolves or updates.
        """
        with self._lock:
            proximity_distribution: Dict[HorizonProximity, int] = {}
            for probe in self._probes.values():
                proximity_distribution[probe.proximity] = (
                    proximity_distribution.get(probe.proximity, 0) + 1
                )
            response_distribution: Dict[BoundaryResponse, int] = {}
            for event in self._events.values():
                response_distribution[event.response] = (
                    response_distribution.get(event.response, 0) + 1
                )
            return HorizonStats(
                total_competences=self._stats["total_competences"],
                total_probes=self._stats["total_probes"],
                total_events=self._stats["total_events"],
                total_learning_requests=self._stats["total_learning_requests"],
                total_defers=self._stats["total_defers"],
                proximity_distribution=proximity_distribution,
                response_distribution=response_distribution,
            )

    def reset(self) -> None:
        """Reset the engine to its initial empty state."""
        with self._lock:
            self._competences.clear()
            self._probes.clear()
            self._events.clear()
            self._learning_requests.clear()
            self._defer_decisions.clear()
            self._profiles.clear()
            self._stats["total_competences"] = 0
            self._stats["total_probes"] = 0
            self._stats["total_events"] = 0
            self._stats["total_learning_requests"] = 0
            self._stats["total_defers"] = 0

    # ── Internal Helpers (callers must already hold the lock) ─────────

    def _find_competence_locked(
        self,
        agent_id: str,
        domain: KnowledgeDomain,
    ) -> Optional[DomainCompetence]:
        """Return the most recently registered competence for (agent, domain).

        Iteration is over insertion order, so the last matching record wins;
        this makes re-registration a natural "update" semantic.
        """
        latest: Optional[DomainCompetence] = None
        for competence in self._competences.values():
            if competence.agent_id == agent_id and competence.domain == domain:
                latest = competence
        return latest

    def _proximity_from_boundary(self, boundary_distance: float) -> HorizonProximity:
        """Band a continuous boundary_distance into a discrete proximity."""
        if boundary_distance > self._INTERIOR_THRESHOLD:
            return HorizonProximity.INTERIOR
        if boundary_distance > self._NEAR_THRESHOLD:
            return HorizonProximity.NEAR
        if boundary_distance > self._AT_THRESHOLD:
            return HorizonProximity.AT
        return HorizonProximity.BEYOND

    def _state_from_proximity(self, proximity: HorizonProximity) -> EpistemicState:
        """Map a proximity to its implied epistemic state."""
        return self._STATE_FROM_PROXIMITY.get(
            proximity, EpistemicState.UNKNOWN_UNKNOWN
        )

    def _compute_profile_locked(self, agent_id: str) -> HorizonProfile:
        """Aggregate an agent's competences, probes, and events into a profile."""
        competences = [
            c for c in self._competences.values() if c.agent_id == agent_id
        ]
        domains_mapped = {c.domain for c in competences}
        total_domains_mapped = len(domains_mapped)

        if competences:
            avg_boundary = sum(c.boundary_distance for c in competences) / len(competences)
        else:
            avg_boundary = 0.0

        competence_distribution: Dict[CompetenceLevel, int] = {}
        proximity_distribution: Dict[HorizonProximity, int] = {}
        for competence in competences:
            competence_distribution[competence.level] = (
                competence_distribution.get(competence.level, 0) + 1
            )
            prox = self._proximity_from_boundary(competence.boundary_distance)
            proximity_distribution[prox] = proximity_distribution.get(prox, 0) + 1

        total_probes = sum(1 for p in self._probes.values() if p.agent_id == agent_id)
        total_events = sum(1 for ev in self._events.values() if ev.agent_id == agent_id)

        domain_count = len(KnowledgeDomain) if KnowledgeDomain else 1
        epistemic_coverage = total_domains_mapped / domain_count if domain_count else 0.0

        return HorizonProfile(
            agent_id=agent_id,
            total_domains_mapped=total_domains_mapped,
            avg_boundary_distance=round(avg_boundary, 4),
            competence_distribution=competence_distribution,
            proximity_distribution=proximity_distribution,
            epistemic_coverage=round(epistemic_coverage, 4),
            total_probes=total_probes,
            total_events=total_events,
            updated_at=self._iso_now(),
        )

    @staticmethod
    def _iso_now() -> str:
        """Return an ISO-8601 UTC timestamp for record fields."""
        return datetime.now().isoformat()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveHorizon] = None
_engine_lock = threading.Lock()


def get_horizon_engine() -> AgentCognitiveHorizon:
    """Get or create the singleton AgentCognitiveHorizon instance."""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveHorizon()
        return _engine


def reset_horizon_engine() -> None:
    """Reset the singleton AgentCognitiveHorizon instance to a fresh state."""
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
