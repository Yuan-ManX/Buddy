"""Agent Explanation Synthesizer.

An explainable AI (XAI) layer that generates structured, audience-appropriate
explanations for agent decisions. The synthesizer supports multiple explanation
types (decision, reasoning, causal, contrastive, counterfactual) and produces
narrative text together with supporting evidence and contributing factors.

The module is designed to be thread-safe. All mutable state is guarded by a
single ``threading.Lock`` and every accessor returns fresh copies so callers
cannot mutate internal state by reference.

Public API:
    - ``AgentExplanationSynthesizer``: main class implementing the XAI layer.
    - ``get_explanation_synthesizer()``: process-wide singleton accessor.
    - ``reset_explanation_synthesizer()``: clears the singleton (useful in tests).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExplanationType(str, Enum):
    """The kind of explanation being requested / generated."""

    DECISION = "decision"
    REASONING = "reasoning"
    CAUSAL = "causal"
    CONTRASTIVE = "contrastive"
    COUNTERFACTUAL = "counterfactual"


class AudienceLevel(str, Enum):
    """The intended audience for an explanation.

    Different audiences get different narrative styles: technical depth for
    engineers, simplified framing for business stakeholders, plain language
    for end users, and implementation-level detail for developers.
    """

    TECHNICAL = "technical"
    BUSINESS = "business"
    END_USER = "end_user"
    DEVELOPER = "developer"


class ConfidenceLevel(str, Enum):
    """Qualitative confidence in an explanation."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class ExplanationStatus(str, Enum):
    """Lifecycle status for an explanation."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceType(str, Enum):
    """The nature of a piece of supporting evidence."""

    DATA = "data"
    RULE = "rule"
    PRECEDENT = "precedent"
    INTUITION = "intuition"
    STATISTICAL = "statistical"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Evidence:
    """A single piece of supporting evidence attached to an explanation.

    Attributes:
        evidence_id: Unique identifier for this evidence record.
        evidence_type: The nature of the evidence (data, rule, precedent, ...).
        content: Human-readable description of the evidence.
        source: Where the evidence came from (e.g. a sensor, a rule name, a
            precedent identifier).
        weight: How strongly this evidence supports the explanation, in [0, 1].
        timestamp: Unix timestamp (seconds) when the evidence was recorded.
    """

    evidence_id: str
    evidence_type: EvidenceType
    content: str
    source: str
    weight: float = 0.5
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "content": self.content,
            "source": self.source,
            "weight": self.weight,
            "timestamp": self.timestamp,
        }


@dataclass
class ExplanationFactor:
    """A factor that contributed to an agent decision.

    Attributes:
        factor_id: Unique identifier for this factor.
        name: Short name / label for the factor.
        description: Longer human-readable description.
        contribution: How much this factor influenced the decision, in [0, 1].
        direction: ``"positive"`` if the factor pushed toward the decision,
            ``"negative"`` if it pushed against.
        timestamp: Unix timestamp (seconds) when the factor was recorded.
    """

    factor_id: str
    name: str
    description: str
    contribution: float
    direction: str
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "description": self.description,
            "contribution": self.contribution,
            "direction": self.direction,
            "timestamp": self.timestamp,
        }


@dataclass
class Explanation:
    """A complete, generated explanation for an agent decision.

    Attributes:
        explanation_id: Unique identifier.
        request_id: The id of the ``ExplanationRequest`` that produced this.
        decision_id: The decision being explained.
        explanation_type: The kind of explanation.
        audience: The intended audience.
        title: Short human-readable title.
        summary: One- or two-sentence summary.
        narrative: Full human-readable narrative.
        factors: Contributing factors.
        evidence: Supporting evidence.
        confidence: Qualitative confidence in the explanation.
        alternatives_considered: Other options that were considered.
        created_at: Unix timestamp (seconds) when the explanation was created.
        status: Lifecycle status.
    """

    explanation_id: str
    request_id: str
    decision_id: str
    explanation_type: ExplanationType
    audience: AudienceLevel
    title: str
    summary: str
    narrative: str
    factors: list[ExplanationFactor] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.UNCERTAIN
    alternatives_considered: list[str] = field(default_factory=list)
    created_at: float = 0.0
    status: ExplanationStatus = ExplanationStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "explanation_type": self.explanation_type.value,
            "audience": self.audience.value,
            "title": self.title,
            "summary": self.summary,
            "narrative": self.narrative,
            "factors": [f.to_dict() for f in self.factors],
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence.value,
            "alternatives_considered": list(self.alternatives_considered),
            "created_at": self.created_at,
            "status": self.status.value,
        }


@dataclass
class ExplanationRequest:
    """A request to generate an explanation for a decision.

    Attributes:
        request_id: Unique identifier.
        decision_id: The decision to explain.
        explanation_type: The kind of explanation requested.
        audience: The intended audience.
        context: Free-form context dict (e.g. inputs, options, metadata).
        question: Optional natural-language question the explanation should
            answer.
        created_at: Unix timestamp (seconds) when the request was created.
    """

    request_id: str
    decision_id: str
    explanation_type: ExplanationType
    audience: AudienceLevel
    context: dict[str, Any] = field(default_factory=dict)
    question: str = ""
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "explanation_type": self.explanation_type.value,
            "audience": self.audience.value,
            "context": dict(self.context),
            "question": self.question,
            "created_at": self.created_at,
        }


@dataclass
class DecisionTrace:
    """A trace of how an agent reached a decision.

    Attributes:
        trace_id: Unique identifier.
        decision_id: The decision that was traced.
        agent_id: The agent that made the decision.
        action_taken: The action that was ultimately taken.
        inputs: The inputs the agent acted on.
        reasoning_steps: Ordered list of reasoning steps the agent followed.
        alternatives: Other actions the agent considered.
        timestamp: Unix timestamp (seconds) when the trace was recorded.
    """

    trace_id: str
    decision_id: str
    agent_id: str
    action_taken: str
    inputs: dict[str, Any] = field(default_factory=dict)
    reasoning_steps: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "action_taken": self.action_taken,
            "inputs": dict(self.inputs),
            "reasoning_steps": list(self.reasoning_steps),
            "alternatives": list(self.alternatives),
            "timestamp": self.timestamp,
        }


@dataclass
class SynthesizerStats:
    """Aggregate statistics about the synthesizer's activity.

    Attributes:
        total_requests: Number of explanation requests received.
        total_explanations: Number of explanations generated.
        total_traces: Number of decision traces recorded.
        avg_confidence_score: Average numeric confidence score across all
            generated explanations, in [0, 1].
        avg_factors_per_explanation: Average number of factors per explanation.
        explanations_by_type: Count of explanations per ``ExplanationType``.
    """

    total_requests: int = 0
    total_explanations: int = 0
    total_traces: int = 0
    avg_confidence_score: float = 0.0
    avg_factors_per_explanation: float = 0.0
    explanations_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_explanations": self.total_explanations,
            "total_traces": self.total_traces,
            "avg_confidence_score": self.avg_confidence_score,
            "avg_factors_per_explanation": self.avg_factors_per_explanation,
            "explanations_by_type": dict(self.explanations_by_type),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> float:
    """Return the current Unix timestamp in seconds."""
    return time.time()


def _new_id(prefix: str) -> str:
    """Generate a new unique id with the given prefix.

    Uses ``uuid.uuid4`` for global uniqueness and prepends a human-readable
    prefix so ids are easy to spot in logs.
    """
    return f"{prefix}_{uuid.uuid4().hex}"


def _confidence_to_score(level: ConfidenceLevel) -> float:
    """Map a qualitative ``ConfidenceLevel`` to a numeric score in [0, 1]."""
    mapping = {
        ConfidenceLevel.HIGH: 1.0,
        ConfidenceLevel.MEDIUM: 0.66,
        ConfidenceLevel.LOW: 0.33,
        ConfidenceLevel.UNCERTAIN: 0.1,
    }
    return mapping.get(level, 0.0)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class AgentExplanationSynthesizer:
    """Generates structured, audience-appropriate explanations for agent decisions.

    The synthesizer is the central XAI component. It accepts explanation
    requests, builds contributing factors from request context, composes a
    narrative tuned to the requested audience, and records supporting evidence
    and decision traces.

    All public methods are thread-safe. Internal dicts (``_requests``,
    ``_explanations``, ``_traces``) are guarded by ``self._lock`` and accessors
    return fresh copies so callers cannot mutate internal state.
    """

    MAX_EXPLANATIONS = 5000
    MAX_TRACES = 5000

    def __init__(self) -> None:
        self._requests: dict[str, ExplanationRequest] = {}
        self._explanations: dict[str, Explanation] = {}
        self._traces: dict[str, DecisionTrace] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Explanation requests
    # ------------------------------------------------------------------

    def request_explanation(
        self,
        decision_id: str,
        explanation_type: ExplanationType,
        audience: AudienceLevel = AudienceLevel.TECHNICAL,
        context: dict[str, Any] | None = None,
        question: str = "",
    ) -> ExplanationRequest:
        """Register a new request to explain ``decision_id``.

        Args:
            decision_id: The decision to explain.
            explanation_type: The kind of explanation to generate.
            audience: The intended audience. Defaults to ``TECHNICAL``.
            context: Optional context dict. Keys become contributing factors
                during explanation generation. ``None`` is treated as empty.
            question: Optional natural-language question to answer.

        Returns:
            The newly created ``ExplanationRequest``.
        """
        request = ExplanationRequest(
            request_id=_new_id("req"),
            decision_id=decision_id,
            explanation_type=explanation_type,
            audience=audience,
            context=dict(context) if context else {},
            question=question,
            created_at=_now(),
        )
        with self._lock:
            self._requests[request.request_id] = request
        return request

    def get_request(self, request_id: str) -> ExplanationRequest | None:
        """Return the request with ``request_id``, or ``None`` if not found."""
        with self._lock:
            request = self._requests.get(request_id)
            if request is None:
                return None
            # Return a shallow copy so callers cannot mutate internal state.
            return ExplanationRequest(
                request_id=request.request_id,
                decision_id=request.decision_id,
                explanation_type=request.explanation_type,
                audience=request.audience,
                context=dict(request.context),
                question=request.question,
                created_at=request.created_at,
            )

    def list_requests(self) -> list[ExplanationRequest]:
        """Return a list of all requests, ordered by creation time."""
        with self._lock:
            requests = list(self._requests.values())
        requests.sort(key=lambda r: r.created_at)
        return requests

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def generate_explanation(self, request_id: str) -> Explanation:
        """Generate a structured explanation for the given request.

        The method:
            1. Looks up the request (raises ``KeyError`` if missing).
            2. Builds contributing factors from the request context — each
               context key becomes a factor whose contribution is derived from
               the magnitude of its value.
            3. Composes an audience-appropriate narrative from the factors.
            4. Computes a qualitative confidence level.
            5. Extracts any alternatives listed in the context.
            6. Persists the explanation (evicting the oldest if at capacity)
               and returns it.

        Args:
            request_id: The id of the ``ExplanationRequest`` to fulfill.

        Returns:
            The generated ``Explanation``.

        Raises:
            KeyError: If no request with ``request_id`` exists.
        """
        with self._lock:
            request = self._requests.get(request_id)
            if request is None:
                raise KeyError(f"No explanation request with id {request_id!r}")
            # Snapshot the fields we need while holding the lock.
            decision_id = request.decision_id
            explanation_type = request.explanation_type
            audience = request.audience
            context = dict(request.context)

        factors = self._build_factors(context)
        narrative = self._generate_narrative(
            factors=factors,
            explanation_type=explanation_type,
            audience=audience,
            decision_id=decision_id,
        )
        confidence = self._compute_confidence(factors)
        alternatives = self._extract_alternatives(context)
        title = self._generate_title(explanation_type, decision_id)
        summary = self._generate_summary(narrative, factors)

        explanation = Explanation(
            explanation_id=_new_id("exp"),
            request_id=request_id,
            decision_id=decision_id,
            explanation_type=explanation_type,
            audience=audience,
            title=title,
            summary=summary,
            narrative=narrative,
            factors=factors,
            evidence=[],
            confidence=confidence,
            alternatives_considered=alternatives,
            created_at=_now(),
            status=ExplanationStatus.COMPLETED,
        )

        with self._lock:
            # Evict the oldest explanation if we are at capacity.
            if len(self._explanations) >= self.MAX_EXPLANATIONS:
                oldest_id = min(
                    self._explanations.keys(),
                    key=lambda eid: self._explanations[eid].created_at,
                )
                self._explanations.pop(oldest_id, None)
            self._explanations[explanation.explanation_id] = explanation

        return explanation

    def get_explanation(self, explanation_id: str) -> Explanation | None:
        """Return the explanation with ``explanation_id``, or ``None``."""
        with self._lock:
            explanation = self._explanations.get(explanation_id)
            if explanation is None:
                return None
            return self._clone_explanation(explanation)

    def list_explanations(self, decision_id: str | None = None) -> list[Explanation]:
        """Return all explanations, optionally filtered by ``decision_id``.

        Results are ordered by creation time (oldest first).
        """
        with self._lock:
            explanations = list(self._explanations.values())
        if decision_id is not None:
            explanations = [e for e in explanations if e.decision_id == decision_id]
        explanations.sort(key=lambda e: e.created_at)
        return [self._clone_explanation(e) for e in explanations]

    # ------------------------------------------------------------------
    # Decision tracing
    # ------------------------------------------------------------------

    def trace_decision(
        self,
        agent_id: str,
        decision_id: str,
        action_taken: str,
        inputs: dict[str, Any] | None = None,
        reasoning_steps: list[str] | None = None,
        alternatives: list[str] | None = None,
    ) -> DecisionTrace:
        """Record a trace of how ``agent_id`` reached ``decision_id``.

        Args:
            agent_id: The agent that made the decision.
            decision_id: The decision being traced.
            action_taken: The action the agent ultimately took.
            inputs: The inputs the agent acted on. ``None`` is treated as empty.
            reasoning_steps: Ordered reasoning steps. ``None`` is treated as
                empty.
            alternatives: Other actions the agent considered. ``None`` is
                treated as empty.

        Returns:
            The newly created ``DecisionTrace``.
        """
        trace = DecisionTrace(
            trace_id=_new_id("trace"),
            decision_id=decision_id,
            agent_id=agent_id,
            action_taken=action_taken,
            inputs=dict(inputs) if inputs else {},
            reasoning_steps=list(reasoning_steps) if reasoning_steps else [],
            alternatives=list(alternatives) if alternatives else [],
            timestamp=_now(),
        )
        with self._lock:
            if len(self._traces) >= self.MAX_TRACES:
                oldest_id = min(
                    self._traces.keys(),
                    key=lambda tid: self._traces[tid].timestamp,
                )
                self._traces.pop(oldest_id, None)
            self._traces[trace.trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> DecisionTrace | None:
        """Return the trace with ``trace_id``, or ``None`` if not found."""
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return None
            return DecisionTrace(
                trace_id=trace.trace_id,
                decision_id=trace.decision_id,
                agent_id=trace.agent_id,
                action_taken=trace.action_taken,
                inputs=dict(trace.inputs),
                reasoning_steps=list(trace.reasoning_steps),
                alternatives=list(trace.alternatives),
                timestamp=trace.timestamp,
            )

    def list_traces(self, agent_id: str | None = None) -> list[DecisionTrace]:
        """Return all traces, optionally filtered by ``agent_id``.

        Results are ordered by timestamp (oldest first).
        """
        with self._lock:
            traces = list(self._traces.values())
        if agent_id is not None:
            traces = [t for t in traces if t.agent_id == agent_id]
        traces.sort(key=lambda t: t.timestamp)
        return [
            DecisionTrace(
                trace_id=t.trace_id,
                decision_id=t.decision_id,
                agent_id=t.agent_id,
                action_taken=t.action_taken,
                inputs=dict(t.inputs),
                reasoning_steps=list(t.reasoning_steps),
                alternatives=list(t.alternatives),
                timestamp=t.timestamp,
            )
            for t in traces
        ]

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def add_evidence(
        self,
        explanation_id: str,
        evidence_type: EvidenceType,
        content: str,
        source: str,
        weight: float = 0.5,
    ) -> Evidence:
        """Attach a piece of supporting evidence to an explanation.

        Args:
            explanation_id: The explanation to attach evidence to.
            evidence_type: The nature of the evidence.
            content: Human-readable description of the evidence.
            source: Where the evidence came from.
            weight: How strongly the evidence supports the explanation, in
                [0, 1]. Defaults to 0.5.

        Returns:
            The newly created ``Evidence``.

        Raises:
            KeyError: If no explanation with ``explanation_id`` exists.
        """
        # Clamp weight into [0, 1].
        if weight < 0.0:
            weight = 0.0
        elif weight > 1.0:
            weight = 1.0

        evidence = Evidence(
            evidence_id=_new_id("ev"),
            evidence_type=evidence_type,
            content=content,
            source=source,
            weight=weight,
            timestamp=_now(),
        )

        with self._lock:
            explanation = self._explanations.get(explanation_id)
            if explanation is None:
                raise KeyError(
                    f"No explanation with id {explanation_id!r}"
                )
            # Mutate the stored explanation in place. Because ``explanation``
            # here is the actual stored object (not a clone), appending is
            # safe and visible to subsequent reads.
            explanation.evidence.append(evidence)

        return evidence

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> SynthesizerStats:
        """Return aggregate statistics about synthesizer activity."""
        with self._lock:
            total_requests = len(self._requests)
            total_explanations = len(self._explanations)
            total_traces = len(self._traces)

            explanations = list(self._explanations.values())
            by_type: dict[str, int] = {}
            confidence_sum = 0.0
            factor_sum = 0
            for explanation in explanations:
                key = explanation.explanation_type.value
                by_type[key] = by_type.get(key, 0) + 1
                confidence_sum += _confidence_to_score(explanation.confidence)
                factor_sum += len(explanation.factors)

            if total_explanations > 0:
                avg_confidence = confidence_sum / total_explanations
                avg_factors = factor_sum / total_explanations
            else:
                avg_confidence = 0.0
                avg_factors = 0.0

        return SynthesizerStats(
            total_requests=total_requests,
            total_explanations=total_explanations,
            total_traces=total_traces,
            avg_confidence_score=avg_confidence,
            avg_factors_per_explanation=avg_factors,
            explanations_by_type=dict(by_type),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clone_explanation(self, explanation: Explanation) -> Explanation:
        """Return a deep-enough copy of ``explanation`` for safe return to callers.

        Nested lists (factors, evidence, alternatives) are copied so that
        callers cannot mutate the stored explanation through returned
        references.
        """
        return Explanation(
            explanation_id=explanation.explanation_id,
            request_id=explanation.request_id,
            decision_id=explanation.decision_id,
            explanation_type=explanation.explanation_type,
            audience=explanation.audience,
            title=explanation.title,
            summary=explanation.summary,
            narrative=explanation.narrative,
            factors=list(explanation.factors),
            evidence=list(explanation.evidence),
            confidence=explanation.confidence,
            alternatives_considered=list(explanation.alternatives_considered),
            created_at=explanation.created_at,
            status=explanation.status,
        )

    def _build_factors(self, context: dict[str, Any]) -> list[ExplanationFactor]:
        """Build contributing factors from a request's context dict.

        Each top-level key in ``context`` becomes a factor. The contribution
        value is derived from the magnitude of the value:

            - Numeric values use the value directly, clamped to [0, 1].
            - Boolean ``True`` -> 1.0, ``False`` -> 0.0.
            - Strings / other: contribution is derived from length, capped at
              1.0 (``min(len(str(value)) / 100.0, 1.0)``).
            - Lists / dicts: contribution is derived from size, capped at 1.0.

        Direction is ``"positive"`` when contribution >= 0.5, else
        ``"negative"``. Special keys ``"alternatives"`` and ``"question"`` are
        skipped since they are not factors.
        """
        now = _now()
        factors: list[ExplanationFactor] = []
        for key, value in context.items():
            # Skip non-factor metadata.
            if key in ("alternatives", "question"):
                continue

            contribution = self._derive_contribution(value)
            direction = "positive" if contribution >= 0.5 else "negative"
            factors.append(
                ExplanationFactor(
                    factor_id=_new_id("factor"),
                    name=str(key),
                    description=f"Context factor '{key}' with value {value!r}.",
                    contribution=contribution,
                    direction=direction,
                    timestamp=now,
                )
            )
        return factors

    def _derive_contribution(self, value: Any) -> float:
        """Derive a contribution score in [0, 1] from a context value."""
        if isinstance(value, bool):
            # ``bool`` is a subclass of ``int`` so check it first.
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            score = float(abs(value))
            if score > 1.0:
                # Map values > 1 into (0, 1] via a saturating transform so
                # that large numeric inputs still produce a valid score.
                score = 1.0 - (1.0 / (1.0 + score))
            return max(0.0, min(1.0, score))
        if isinstance(value, (list, tuple, set)):
            return min(len(value) / 10.0, 1.0)
        if isinstance(value, dict):
            return min(len(value) / 10.0, 1.0)
        # Strings and anything else: derive from string length.
        text = str(value)
        return min(len(text) / 100.0, 1.0)

    def _generate_narrative(
        self,
        factors: list[ExplanationFactor],
        explanation_type: ExplanationType,
        audience: AudienceLevel,
        decision_id: str,
    ) -> str:
        """Compose a human-readable narrative tuned to ``audience``.

        The narrative structure varies by audience:

            - ``TECHNICAL``: lists factor count, top contributors, and their
              contribution values.
            - ``DEVELOPER``: similar to technical but emphasizes that the
              factors were derived programmatically from request context.
            - ``BUSINESS``: simplifies to plain language focused on the top
              contributors by name.
            - ``END_USER``: uses plain, non-technical language without any
              numeric detail.
        """
        n = len(factors)
        # Sort by contribution descending so we can talk about "top" factors.
        sorted_factors = sorted(
            factors, key=lambda f: f.contribution, reverse=True
        )
        top_factors = sorted_factors[:3]
        type_label = explanation_type.value

        if audience == AudienceLevel.TECHNICAL:
            return self._narrative_technical(
                decision_id, n, top_factors, type_label
            )
        if audience == AudienceLevel.DEVELOPER:
            return self._narrative_developer(
                decision_id, n, top_factors, type_label
            )
        if audience == AudienceLevel.BUSINESS:
            return self._narrative_business(decision_id, n, top_factors, type_label)
        # END_USER
        return self._narrative_end_user(decision_id, n, top_factors, type_label)

    def _narrative_technical(
        self,
        decision_id: str,
        n: int,
        top_factors: list[ExplanationFactor],
        type_label: str,
    ) -> str:
        """Technical narrative: factor count + named contributors with weights."""
        parts: list[str] = []
        parts.append(
            f"Decision {decision_id} was reached by evaluating {n} factor(s) "
            f"as part of a {type_label} analysis."
        )
        if top_factors:
            parts.append("Primary contributors:")
            for f in top_factors:
                parts.append(
                    f"  - {f.name} (contribution={f.contribution:.3f}, "
                    f"direction={f.direction})"
                )
        else:
            parts.append("No contributing factors were identified.")
        return " ".join(parts)

    def _narrative_developer(
        self,
        decision_id: str,
        n: int,
        top_factors: list[ExplanationFactor],
        type_label: str,
    ) -> str:
        """Developer narrative: emphasizes programmatic factor derivation."""
        parts: list[str] = []
        parts.append(
            f"[{type_label}] Decision {decision_id}: synthesizer derived {n} "
            f"factor(s) from the request context."
        )
        if top_factors:
            parts.append("Top contributing factors (derived from context keys):")
            for f in top_factors:
                parts.append(
                    f"  - factor_id={f.factor_id} name={f.name} "
                    f"contribution={f.contribution:.3f} direction={f.direction}"
                )
        else:
            parts.append(
                "Context yielded no factors; explanation is based on default "
                "reasoning."
            )
        return " ".join(parts)

    def _narrative_business(
        self,
        decision_id: str,
        n: int,
        top_factors: list[ExplanationFactor],
        type_label: str,
    ) -> str:
        """Business narrative: plain language focused on top factor names."""
        parts: list[str] = []
        parts.append(
            f"Decision {decision_id} was made after considering {n} factor(s)."
        )
        if top_factors:
            names = ", ".join(f.name for f in top_factors)
            parts.append(f"The most important considerations were: {names}.")
        else:
            parts.append("No specific considerations were recorded.")
        return " ".join(parts)

    def _narrative_end_user(
        self,
        decision_id: str,
        n: int,
        top_factors: list[ExplanationFactor],
        type_label: str,
    ) -> str:
        """End-user narrative: plain language, no numeric detail."""
        parts: list[str] = []
        if n == 0:
            parts.append(
                f"We made decision {decision_id} based on our standard process."
            )
        else:
            parts.append(
                f"We made decision {decision_id} after looking at {n} thing(s)."
            )
            if top_factors:
                names = ", ".join(f.name for f in top_factors)
                parts.append(f"The main things we thought about were: {names}.")
        return " ".join(parts)

    def _compute_confidence(self, factors: list[ExplanationFactor]) -> ConfidenceLevel:
        """Compute a qualitative confidence level from factor contributions.

        Rules:
            - sum(contributions) > 2.0 AND len(factors) >= 3 -> ``HIGH``
            - sum(contributions) > 1.0 -> ``MEDIUM``
            - sum(contributions) > 0.5 -> ``LOW``
            - otherwise -> ``UNCERTAIN``
        """
        total = sum(f.contribution for f in factors)
        n = len(factors)
        if total > 2.0 and n >= 3:
            return ConfidenceLevel.HIGH
        if total > 1.0:
            return ConfidenceLevel.MEDIUM
        if total > 0.5:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNCERTAIN

    def _extract_alternatives(self, context: dict[str, Any]) -> list[str]:
        """Extract the list of alternatives from ``context`` if present.

        The conventions are:
            - ``context["alternatives"]`` may be a list of strings.
            - Each element is coerced to ``str`` so non-string entries do not
              break callers.
        """
        raw = context.get("alternatives")
        if raw is None:
            return []
        if isinstance(raw, (list, tuple)):
            return [str(item) for item in raw]
        if isinstance(raw, str):
            # A single alternative given as a string.
            return [raw]
        return []

    def _generate_title(
        self, explanation_type: ExplanationType, decision_id: str
    ) -> str:
        """Generate a short human-readable title for the explanation.

        Examples:
            ``Causal Explanation for Decision d_123``
            ``Decision Explanation for Decision d_123``
        """
        label = explanation_type.value.replace("_", " ").title()
        return f"{label} Explanation for Decision {decision_id}"

    def _generate_summary(
        self, narrative: str, factors: list[ExplanationFactor]
    ) -> str:
        """Generate a one-line summary from the narrative.

        The summary is the first 200 characters of the narrative, followed by
        a parenthetical note giving the number of contributing factors.
        """
        snippet = narrative[:200]
        return f"{snippet} ({len(factors)} contributing factors)"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


_global_synthesizer: AgentExplanationSynthesizer | None = None
_global_synthesizer_lock = threading.Lock()


def get_explanation_synthesizer() -> AgentExplanationSynthesizer:
    """Return the process-wide ``AgentExplanationSynthesizer`` singleton.

    The singleton is created lazily on first access and shared thereafter.
    """
    global _global_synthesizer
    with _global_synthesizer_lock:
        if _global_synthesizer is None:
            _global_synthesizer = AgentExplanationSynthesizer()
        return _global_synthesizer


def reset_explanation_synthesizer() -> None:
    """Reset the process-wide singleton.

    Primarily useful in tests where a fresh synthesizer is needed between
    cases.
    """
    global _global_synthesizer
    with _global_synthesizer_lock:
        _global_synthesizer = None
