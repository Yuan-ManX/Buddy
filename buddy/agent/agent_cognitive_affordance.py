from __future__ import annotations

# Agent Cognitive Affordance — perceiving action possibilities.
#
# An affordance is an action possibility that an environment, tool, artifact,
# context, or social setting offers to an agent. This module bridges
# perception and action: it lets the agent perceive candidate actions in a
# context, validate them against constraints, rank them by actionable
# metrics, and execute them. Affordances are decorated with signatures
# (perceptual/structural/functional/contextual patterns that signal the
# affordance is available) and constraints (preconditions that must hold
# before the affordance can be enacted).
#
# Capabilities: context registration, affordance perception, signature and
# constraint management, validation, ranking by multiple metrics, execution,
# affordance map construction, and aggregate statistics.
#
# Architecture:
#     AgentCognitiveAffordance (singleton)
#     ├── AffordanceContext (per-agent/per-environment perception scope)
#     │   └── Affordance (a perceived action possibility)
#     │       ├── AffordanceConstraint (precondition/resource/safety/etc.)
#     │       └── AffordanceSignature (perceptual/structural/functional/etc.)
#     ├── AffordanceMap (summary view of a context's affordances)
#     └── AffordanceStats (aggregate engine statistics)

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class AffordanceSource(str, Enum):
    """Where a perceived affordance originates.

    Tools expose operations, environments expose navigation/interaction
    possibilities, contexts expose situation-specific actions, social
    settings expose cooperative or communicative acts, artifacts expose
    manipulation possibilities, and interfaces expose control affordances.
    """
    TOOL = "tool"                # a tool exposes an operation
    ENVIRONMENT = "environment"  # the environment offers an action
    CONTEXT = "context"          # situational action possibility
    SOCIAL = "social"            # cooperative / communicative act
    ARTIFACT = "artifact"        # a physical or digital artifact
    INTERFACE = "interface"      # a UI / control surface element


class AffordanceStatus(str, Enum):
    """Lifecycle states of a perceived affordance.

    PERCEIVED is the initial state once the agent notices the action
    possibility. VALIDATED means the affordance passed constraint checks and
    is ready to enact; INVALIDATED means it failed those checks. EXECUTED
    means the action was carried out successfully; FAILED means execution
    was attempted but did not succeed.
    """
    PERCEIVED = "perceived"      # noticed, not yet checked
    VALIDATED = "validated"      # passed constraint checks
    INVALIDATED = "invalidated"  # failed constraint checks
    EXECUTED = "executed"        # action carried out successfully
    FAILED = "failed"            # execution attempted, did not succeed


class ConstraintType(str, Enum):
    """Categories of constraints gating an affordance.

    PRECONDITION constraints describe state that must hold before the
    affordance can be enacted. RESOURCE constraints describe consumable or
    limited inputs (memory, tokens, quota). SAFETY constraints describe
    bounds that protect the agent or its environment from harm. TEMPORAL
    constraints describe time windows or ordering. PERMISSION constraints
    describe authorization requirements.
    """
    PRECONDITION = "precondition"  # required prior state
    RESOURCE = "resource"          # limited input / quota
    SAFETY = "safety"              # protective bound
    TEMPORAL = "temporal"          # time window / ordering
    PERMISSION = "permission"      # authorization requirement


class SignatureType(str, Enum):
    """Kinds of perceptual signatures that signal an affordance is available.

    A single affordance may carry several signatures of different kinds.
    PERCEPTUAL signatures are surface cues (visible features, sounds).
    STRUCTURAL signatures describe shape or composition (layout, topology).
    FUNCTIONAL signatures describe behavior (what the affordance does when
    enacted). CONTEXTUAL signatures describe situational conditions under
    which the affordance becomes relevant.
    """
    PERCEPTUAL = "perceptual"    # surface cue
    STRUCTURAL = "structural"    # shape / composition
    FUNCTIONAL = "functional"    # behavior / effect
    CONTEXTUAL = "contextual"    # situational condition


class RankingMetric(str, Enum):
    """Metrics used to rank affordances within a context.

    UTILITY ranks by expected usefulness (descending). EFFORT ranks by the
    cost to enact (ascending, lower effort first). RISK ranks by the chance
    or severity of negative outcomes (ascending, lower risk first).
    GOAL_ALIGNMENT ranks by how well the affordance serves current goals
    (descending); when no explicit goal model is available, utility is used
    as a proxy.
    """
    UTILITY = "utility"                  # expected usefulness (desc)
    EFFORT = "effort"                    # cost to enact (asc)
    RISK = "risk"                        # negative outcome potential (asc)
    GOAL_ALIGNMENT = "goal_alignment"    # goal fit (desc; utility proxy)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a context/affordance/etc."""
    return str(uuid.uuid4())[:8]


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"tool"``) and then against member names
    (e.g. ``"TOOL"``), so callers may pass either form. Raises ``ValueError``
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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = low
    if f < low:
        return low
    if f > high:
        return high
    return f


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AffordanceConstraint:
    """A constraint gating the enactment of an affordance.

    Constraints describe conditions that must hold before an affordance can
    be enacted. The ``satisfied`` flag records whether the constraint is
    currently met; an affordance is considered validatable only when all of
    its constraints are satisfied.
    """
    constraint_id: str = field(default_factory=_new_id)
    affordance_id: str = ""
    constraint_type: ConstraintType = ConstraintType.PRECONDITION
    description: str = ""
    satisfied: bool = False
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this constraint to a plain dict, expanding the enum."""
        return {
            "constraint_id": self.constraint_id,
            "affordance_id": self.affordance_id,
            "constraint_type": self.constraint_type.value
            if isinstance(self.constraint_type, ConstraintType)
            else str(self.constraint_type),
            "description": self.description,
            "satisfied": self.satisfied,
            "created_at": self.created_at,
        }


@dataclass
class AffordanceSignature:
    """A perceptual signature signaling an affordance is available.

    Signatures are the cues by which the agent recognizes that an affordance
    exists. ``pattern`` is a free-form description of the cue (a literal
    string, a regex, a feature vector serialized as a string, etc.). The
    ``confidence`` value in [0, 1] records how reliably the pattern predicts
    the affordance.
    """
    signature_id: str = field(default_factory=_new_id)
    affordance_id: str = ""
    signature_type: SignatureType = SignatureType.PERCEPTUAL
    pattern: str = ""
    confidence: float = 0.5
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this signature to a plain dict, expanding the enum."""
        return {
            "signature_id": self.signature_id,
            "affordance_id": self.affordance_id,
            "signature_type": self.signature_type.value
            if isinstance(self.signature_type, SignatureType)
            else str(self.signature_type),
            "pattern": self.pattern,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class Affordance:
    """A perceived action possibility within a context.

    An affordance is the central object of this module: an action the agent
    could take, perceived against a context. It carries a source (where the
    action possibility comes from), descriptive text, a list of constraints
    that gate enactment, a list of signatures that signal its availability,
    and a list of free-form effect descriptions. The effort/utility/risk
    floats in [0, 1] drive ranking; status tracks the affordance lifecycle.

    ``execution_data`` holds an optional payload recorded when the
    affordance is executed (inputs, outputs, timing, references).
    """
    affordance_id: str = field(default_factory=_new_id)
    context_id: str = ""
    name: str = ""
    source: AffordanceSource = AffordanceSource.TOOL
    description: str = ""
    constraints: List[AffordanceConstraint] = field(default_factory=list)
    signatures: List[AffordanceSignature] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    effort: float = 0.5
    utility: float = 0.5
    risk: float = 0.0
    status: AffordanceStatus = AffordanceStatus.PERCEIVED
    execution_data: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this affordance to a plain dict.

        Enums are expanded via ``.value`` and nested dataclasses via their
        own ``to_dict`` methods.
        """
        return {
            "affordance_id": self.affordance_id,
            "context_id": self.context_id,
            "name": self.name,
            "source": self.source.value
            if isinstance(self.source, AffordanceSource)
            else str(self.source),
            "description": self.description,
            "constraints": [
                c.to_dict() if hasattr(c, "to_dict") else dict(c)
                for c in self.constraints
            ],
            "signatures": [
                s.to_dict() if hasattr(s, "to_dict") else dict(s)
                for s in self.signatures
            ],
            "effects": list(self.effects),
            "effort": self.effort,
            "utility": self.utility,
            "risk": self.risk,
            "status": self.status.value
            if isinstance(self.status, AffordanceStatus)
            else str(self.status),
            "execution_data": dict(self.execution_data)
            if self.execution_data is not None
            else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AffordanceContext:
    """A perception scope tying one agent to one environment.

    A context is the frame within which affordances are perceived. It
    belongs to a single agent and describes a single environment. Cues are
    free-form strings describing salient features of the situation that
    helped surface the affordances within it. ``affordance_ids`` lists the
    affordances perceived within this context.
    """
    context_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    environment_id: str = ""
    description: str = ""
    cues: List[str] = field(default_factory=list)
    affordance_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this context to a plain dict."""
        return {
            "context_id": self.context_id,
            "agent_id": self.agent_id,
            "environment_id": self.environment_id,
            "description": self.description,
            "cues": list(self.cues),
            "affordance_ids": list(self.affordance_ids),
            "created_at": self.created_at,
        }


@dataclass
class AffordanceMap:
    """A summary view of all affordances within a context.

    Computed on demand by ``AgentCognitiveAffordance.build_map``. The
    ``by_source`` and ``by_status`` dicts map source/status values to counts.
    The averages are computed over all affordances in the context.
    ``ranked_by_utility`` lists affordance ids sorted by utility descending.
    """
    context_id: str = ""
    total_affordances: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    avg_utility: float = 0.0
    avg_effort: float = 0.0
    avg_risk: float = 0.0
    ranked_by_utility: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this map to a plain dict."""
        return {
            "context_id": self.context_id,
            "total_affordances": self.total_affordances,
            "by_source": dict(self.by_source),
            "by_status": dict(self.by_status),
            "avg_utility": self.avg_utility,
            "avg_effort": self.avg_effort,
            "avg_risk": self.avg_risk,
            "ranked_by_utility": list(self.ranked_by_utility),
        }


@dataclass
class AffordanceStats:
    """Aggregate statistics across the entire affordance engine.

    Computed on demand by ``AgentCognitiveAffordance.get_stats``. The
    ``by_source`` and ``by_status`` dicts map source/status values to counts
    across all registered affordances.
    """
    total_contexts: int = 0
    total_affordances: int = 0
    validated_affordances: int = 0
    executed_affordances: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict."""
        return {
            "total_contexts": self.total_contexts,
            "total_affordances": self.total_affordances,
            "validated_affordances": self.validated_affordances,
            "executed_affordances": self.executed_affordances,
            "by_source": dict(self.by_source),
            "by_status": dict(self.by_status),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveAffordance:
    """Affordance perception engine with context/affordance management.

    Maintains a registry of contexts (each tying one agent to one
    environment) and a registry of affordances perceived within those
    contexts. Each affordance may carry constraints (gating enactment) and
    signatures (signaling availability). All state mutations are guarded by
    a single lock to ensure thread safety.

    The engine supports a full affordance lifecycle: affordances are
    perceived, validated against their constraints, ranked by a chosen
    metric, and finally executed (or marked failed). Aggregation methods
    build per-context maps and engine-wide statistics on demand.
    """

    # Capacity limits to bound memory use per engine instance.
    MAX_CONTEXTS: int = 1000
    MAX_AFFORDANCES_PER_CONTEXT: int = 500
    MAX_CONSTRAINTS_PER_AFFORDANCE: int = 50
    MAX_SIGNATURES_PER_AFFORDANCE: int = 50

    def __init__(self) -> None:
        self._contexts: Dict[str, AffordanceContext] = {}
        self._affordances: Dict[str, Affordance] = {}
        self._lock = threading.Lock()
        # Internal engine creation time, used for diagnostics. Stored as a
        # monotonic-ish float rather than an ISO string for easy comparison.
        self._created_at: float = time.time()

    # ── Context Management ──────────────────────────────────────────

    def register_context(
        self,
        agent_id: str,
        environment_id: str,
        description: str = "",
        cues: Optional[List[str]] = None,
    ) -> AffordanceContext:
        """Register a new perception context and return it.

        A context ties one agent to one environment and serves as the
        container for affordances perceived within that pairing. ``cues`` is
        an optional list of free-form strings describing situational
        features. Raises ``RuntimeError`` if the context registry is full
        and no empty context can be evicted.
        """
        with self._lock:
            if len(self._contexts) >= self.MAX_CONTEXTS:
                # Evict the oldest context with no perceived affordances.
                evicted = False
                for candidate_id, candidate in list(self._contexts.items()):
                    if not candidate.affordance_ids:
                        del self._contexts[candidate_id]
                        evicted = True
                        break
                if not evicted:
                    raise RuntimeError("affordance context registry is full")
            context = AffordanceContext(
                agent_id=agent_id,
                environment_id=environment_id,
                description=description,
                cues=list(cues) if cues else [],
            )
            self._contexts[context.context_id] = context
            return context

    def get_context(self, context_id: str) -> Optional[AffordanceContext]:
        """Retrieve a context by its identifier, or ``None`` if absent."""
        with self._lock:
            return self._contexts.get(context_id)

    def list_contexts(
        self,
        agent_id: Optional[str] = None,
    ) -> List[AffordanceContext]:
        """List contexts, optionally filtered by ``agent_id``.

        Returns an empty list if no contexts match the filter.
        """
        with self._lock:
            results: List[AffordanceContext] = []
            for context in self._contexts.values():
                if agent_id is not None and context.agent_id != agent_id:
                    continue
                results.append(context)
            return results

    # ── Affordance Perception ──────────────────────────────────────

    def perceive_affordance(
        self,
        context_id: str,
        name: str,
        source: AffordanceSource,
        description: str = "",
        constraints: Optional[List[Dict[str, Any]]] = None,
        signatures: Optional[List[Dict[str, Any]]] = None,
        effects: Optional[List[str]] = None,
        effort: float = 0.5,
        utility: float = 0.5,
        risk: float = 0.0,
    ) -> Affordance:
        """Perceive a new affordance within a context.

        ``source`` may be passed as an ``AffordanceSource`` or its string
        name/value. ``constraints`` and ``signatures`` are optional lists of
        dicts whose keys populate the corresponding dataclasses; each dict
        may omit generated fields (ids, affordance_id, timestamps). The
        ``effort``, ``utility``, and ``risk`` floats are clamped to [0, 1].

        Raises ``KeyError`` if the context_id is not registered, or
        ``RuntimeError`` if the per-context affordance cap is reached.
        """
        source = _resolve_enum(AffordanceSource, source)
        effort = _clamp(effort)
        utility = _clamp(utility)
        risk = _clamp(risk)
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                raise KeyError(f"context not found: {context_id}")
            if len(context.affordance_ids) >= self.MAX_AFFORDANCES_PER_CONTEXT:
                raise RuntimeError(
                    f"affordance cap reached for context: {context_id}"
                )
            affordance = Affordance(
                context_id=context_id,
                name=name,
                source=source,
                description=description,
                effects=list(effects) if effects else [],
                effort=effort,
                utility=utility,
                risk=risk,
                status=AffordanceStatus.PERCEIVED,
            )
            # Attach any constraints supplied inline.
            if constraints:
                for raw in constraints:
                    if not isinstance(raw, dict):
                        continue
                    if len(affordance.constraints) >= self.MAX_CONSTRAINTS_PER_AFFORDANCE:
                        break
                    ctype = _resolve_enum(
                        ConstraintType,
                        raw.get("constraint_type", ConstraintType.PRECONDITION),
                    )
                    affordance.constraints.append(
                        AffordanceConstraint(
                            affordance_id=affordance.affordance_id,
                            constraint_type=ctype,
                            description=str(raw.get("description", "")),
                            satisfied=bool(raw.get("satisfied", False)),
                        )
                    )
            # Attach any signatures supplied inline.
            if signatures:
                for raw in signatures:
                    if not isinstance(raw, dict):
                        continue
                    if len(affordance.signatures) >= self.MAX_SIGNATURES_PER_AFFORDANCE:
                        break
                    stype = _resolve_enum(
                        SignatureType,
                        raw.get("signature_type", SignatureType.PERCEPTUAL),
                    )
                    affordance.signatures.append(
                        AffordanceSignature(
                            affordance_id=affordance.affordance_id,
                            signature_type=stype,
                            pattern=str(raw.get("pattern", "")),
                            confidence=_clamp(raw.get("confidence", 0.5)),
                        )
                    )
            self._affordances[affordance.affordance_id] = affordance
            context.affordance_ids.append(affordance.affordance_id)
            return affordance

    def get_affordance(self, affordance_id: str) -> Optional[Affordance]:
        """Retrieve an affordance by id, or ``None`` if absent."""
        with self._lock:
            return self._affordances.get(affordance_id)

    def list_affordances(
        self,
        context_id: Optional[str] = None,
        source: Optional[AffordanceSource] = None,
        status: Optional[AffordanceStatus] = None,
    ) -> List[Affordance]:
        """List affordances, optionally filtered by context/source/status.

        Any of ``context_id``, ``source``, and ``status`` may be passed to
        narrow the result set; ``None`` (the default) leaves a filter
        inactive. ``source`` and ``status`` may be passed as enum members or
        their string name/value. Returns an empty list if nothing matches.
        """
        source = (
            _resolve_enum(AffordanceSource, source)
            if source is not None
            else None
        )
        status = (
            _resolve_enum(AffordanceStatus, status)
            if status is not None
            else None
        )
        with self._lock:
            results: List[Affordance] = []
            for affordance in self._affordances.values():
                if context_id is not None and affordance.context_id != context_id:
                    continue
                if source is not None and affordance.source != source:
                    continue
                if status is not None and affordance.status != status:
                    continue
                results.append(affordance)
            return results

    def validate_affordance(
        self,
        affordance_id: str,
        validation_result: bool = True,
        notes: str = "",
    ) -> Affordance:
        """Validate an affordance against its constraints.

        When ``validation_result`` is ``True`` the affordance transitions to
        VALIDATED (or stays EXECUTED if it was already executed); otherwise
        it transitions to INVALIDATED. The ``notes`` string is recorded in
        the affordance's execution_data under the ``validation_notes`` key
        for later inspection. Raises ``KeyError`` if the affordance_id is
        not registered.
        """
        with self._lock:
            affordance = self._affordances.get(affordance_id)
            if affordance is None:
                raise KeyError(f"affordance not found: {affordance_id}")
            if validation_result:
                # Preserve terminal EXECUTED state; otherwise mark validated.
                if affordance.status != AffordanceStatus.EXECUTED:
                    affordance.status = AffordanceStatus.VALIDATED
            else:
                affordance.status = AffordanceStatus.INVALIDATED
            if affordance.execution_data is None:
                affordance.execution_data = {}
            affordance.execution_data["validation_notes"] = notes
            affordance.updated_at = _now()
            return affordance

    def rank_affordances(
        self,
        context_id: str,
        metric: RankingMetric = RankingMetric.UTILITY,
        top_k: int = 10,
    ) -> List[Affordance]:
        """Rank affordances within a context by the selected metric.

        Ranking directions:

          * UTILITY — descending (higher utility first).
          * EFFORT — ascending (lower effort first).
          * RISK — ascending (lower risk first).
          * GOAL_ALIGNMENT — descending (utility used as a proxy).

        Ties are broken by ``affordance_id`` for deterministic output. The
        result is truncated to ``top_k`` entries. Returns an empty list if
        the context has no affordances or does not exist.
        """
        metric = _resolve_enum(RankingMetric, metric)
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return []
            candidates: List[Affordance] = []
            for aid in context.affordance_ids:
                aff = self._affordances.get(aid)
                if aff is not None:
                    candidates.append(aff)
            if not candidates:
                return []

            # Select the sort key and direction for the chosen metric. The
            # GOAL_ALIGNMENT metric falls back to utility as a proxy when no
            # explicit goal model is available.
            if metric == RankingMetric.UTILITY:
                candidates.sort(
                    key=lambda a: (-a.utility, a.affordance_id)
                )
            elif metric == RankingMetric.GOAL_ALIGNMENT:
                candidates.sort(
                    key=lambda a: (-a.utility, a.affordance_id)
                )
            elif metric == RankingMetric.EFFORT:
                candidates.sort(
                    key=lambda a: (a.effort, a.affordance_id)
                )
            elif metric == RankingMetric.RISK:
                candidates.sort(
                    key=lambda a: (a.risk, a.affordance_id)
                )

            if top_k is not None and top_k >= 0:
                candidates = candidates[:top_k]
            return candidates

    def execute_affordance(
        self,
        affordance_id: str,
        execution_data: Optional[Dict[str, Any]] = None,
    ) -> Affordance:
        """Mark an affordance as executed, recording optional payload data.

        ``execution_data`` is merged into the affordance's execution_data
        dict alongside a timestamp. The affordance transitions to EXECUTED
        on success; if the caller signals failure by including a
        ``"success": False`` entry in ``execution_data``, the affordance
        transitions to FAILED instead. Raises ``KeyError`` if the
        affordance_id is not registered.
        """
        with self._lock:
            affordance = self._affordances.get(affordance_id)
            if affordance is None:
                raise KeyError(f"affordance not found: {affordance_id}")
            if affordance.execution_data is None:
                affordance.execution_data = {}
            if execution_data:
                for k, v in execution_data.items():
                    affordance.execution_data[k] = v
            affordance.execution_data["executed_at"] = _now()
            success = affordance.execution_data.get("success", True)
            if success is False:
                affordance.status = AffordanceStatus.FAILED
            else:
                affordance.status = AffordanceStatus.EXECUTED
            affordance.updated_at = _now()
            return affordance

    # ── Constraint Management ──────────────────────────────────────

    def add_constraint(
        self,
        affordance_id: str,
        constraint_type: ConstraintType,
        description: str,
        satisfied: bool = False,
    ) -> AffordanceConstraint:
        """Attach a new constraint to an affordance.

        ``constraint_type`` may be passed as a ``ConstraintType`` or its
        string name/value. Raises ``KeyError`` if the affordance_id is not
        registered, or ``RuntimeError`` if the per-affordance constraint cap
        is reached.
        """
        constraint_type = _resolve_enum(ConstraintType, constraint_type)
        with self._lock:
            affordance = self._affordances.get(affordance_id)
            if affordance is None:
                raise KeyError(f"affordance not found: {affordance_id}")
            if len(affordance.constraints) >= self.MAX_CONSTRAINTS_PER_AFFORDANCE:
                raise RuntimeError(
                    f"constraint cap reached for affordance: {affordance_id}"
                )
            constraint = AffordanceConstraint(
                affordance_id=affordance_id,
                constraint_type=constraint_type,
                description=description,
                satisfied=satisfied,
            )
            affordance.constraints.append(constraint)
            affordance.updated_at = _now()
            return constraint

    def list_constraints(self, affordance_id: str) -> List[AffordanceConstraint]:
        """List the constraints attached to an affordance.

        Returns an empty list if the affordance has no constraints or does
        not exist.
        """
        with self._lock:
            affordance = self._affordances.get(affordance_id)
            if affordance is None:
                return []
            return list(affordance.constraints)

    # ── Signature Management ───────────────────────────────────────

    def add_signature(
        self,
        affordance_id: str,
        signature_type: SignatureType,
        pattern: str,
        confidence: float = 0.5,
    ) -> AffordanceSignature:
        """Attach a new perceptual signature to an affordance.

        ``signature_type`` may be passed as a ``SignatureType`` or its
        string name/value. ``confidence`` is clamped to [0, 1]. Raises
        ``KeyError`` if the affordance_id is not registered, or
        ``RuntimeError`` if the per-affordance signature cap is reached.
        """
        signature_type = _resolve_enum(SignatureType, signature_type)
        confidence = _clamp(confidence)
        with self._lock:
            affordance = self._affordances.get(affordance_id)
            if affordance is None:
                raise KeyError(f"affordance not found: {affordance_id}")
            if len(affordance.signatures) >= self.MAX_SIGNATURES_PER_AFFORDANCE:
                raise RuntimeError(
                    f"signature cap reached for affordance: {affordance_id}"
                )
            signature = AffordanceSignature(
                affordance_id=affordance_id,
                signature_type=signature_type,
                pattern=pattern,
                confidence=confidence,
            )
            affordance.signatures.append(signature)
            affordance.updated_at = _now()
            return signature

    def list_signatures(self, affordance_id: str) -> List[AffordanceSignature]:
        """List the signatures attached to an affordance.

        Returns an empty list if the affordance has no signatures or does
        not exist.
        """
        with self._lock:
            affordance = self._affordances.get(affordance_id)
            if affordance is None:
                return []
            return list(affordance.signatures)

    # ── Aggregation ────────────────────────────────────────────────

    def build_map(self, context_id: str) -> AffordanceMap:
        """Build a summary map of all affordances in a context.

        The map aggregates counts by source and status, computes average
        effort/utility/risk, and lists affordance ids ranked by utility
        descending. Returns an empty map (zero totals) if the context does
        not exist.
        """
        with self._lock:
            context = self._contexts.get(context_id)
            if context is None:
                return AffordanceMap(context_id=context_id)
            affordances: List[Affordance] = []
            for aid in context.affordance_ids:
                aff = self._affordances.get(aid)
                if aff is not None:
                    affordances.append(aff)
            total = len(affordances)
            by_source: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            sum_utility = 0.0
            sum_effort = 0.0
            sum_risk = 0.0
            for aff in affordances:
                src = aff.source.value if isinstance(aff.source, AffordanceSource) else str(aff.source)
                st = aff.status.value if isinstance(aff.status, AffordanceStatus) else str(aff.status)
                by_source[src] = by_source.get(src, 0) + 1
                by_status[st] = by_status.get(st, 0) + 1
                sum_utility += aff.utility
                sum_effort += aff.effort
                sum_risk += aff.risk
            ranked = sorted(
                affordances,
                key=lambda a: (-a.utility, a.affordance_id),
            )
            return AffordanceMap(
                context_id=context_id,
                total_affordances=total,
                by_source=by_source,
                by_status=by_status,
                avg_utility=(sum_utility / total) if total else 0.0,
                avg_effort=(sum_effort / total) if total else 0.0,
                avg_risk=(sum_risk / total) if total else 0.0,
                ranked_by_utility=[a.affordance_id for a in ranked],
            )

    def get_stats(self) -> AffordanceStats:
        """Compute aggregate statistics across the entire engine.

        Counts contexts, affordances, validated affordances, and executed
        affordances, and breaks affordances down by source and status.
        """
        with self._lock:
            total_contexts = len(self._contexts)
            total_affordances = len(self._affordances)
            validated = 0
            executed = 0
            by_source: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            for aff in self._affordances.values():
                src = aff.source.value if isinstance(aff.source, AffordanceSource) else str(aff.source)
                st = aff.status.value if isinstance(aff.status, AffordanceStatus) else str(aff.status)
                by_source[src] = by_source.get(src, 0) + 1
                by_status[st] = by_status.get(st, 0) + 1
                if aff.status == AffordanceStatus.VALIDATED:
                    validated += 1
                elif aff.status == AffordanceStatus.EXECUTED:
                    executed += 1
            return AffordanceStats(
                total_contexts=total_contexts,
                total_affordances=total_affordances,
                validated_affordances=validated,
                executed_affordances=executed,
                by_source=by_source,
                by_status=by_status,
            )

    # ── Maintenance ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all registered contexts and affordances. Intended for tests."""
        with self._lock:
            self._contexts.clear()
            self._affordances.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveAffordance] = None
_engine_lock = threading.Lock()


def get_affordance_engine() -> AgentCognitiveAffordance:
    """Get or create the singleton ``AgentCognitiveAffordance`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveAffordance()
        return _engine


def reset_affordance_engine() -> None:
    """Reset the singleton ``AgentCognitiveAffordance`` instance to ``None``.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_affordance_engine`` call creates a
    fresh instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
