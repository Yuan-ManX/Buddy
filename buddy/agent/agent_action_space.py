"""
Agent Action Space — Formal enumeration, feasibility checking, and constraint management for agent actions.

The Action Space provides a structured registry of every action an agent may
perform. Each action is described by a schema, a category, an estimated cost,
and an associated set of constraints. Before an action is executed the space
can be queried for *feasibility* (can it run given the current context?) and
*validity* (are the supplied parameters well-formed?). Executions are recorded
so that success rate, average duration, and other statistics can be derived.

Architecture:
  Layer 1: Registry — Action registration with schema, tags, and versioning
  Layer 2: Constraints — Precondition / resource / permission rule attachments
  Layer 3: Feasibility — Constraint evaluation producing a scored report
  Layer 4: Validation — Parameter type-checking against the declared schema
  Layer 5: Execution Log — Append-only history capped at MAX_EXECUTIONS_LOG
  Layer 6: Statistics — Per-action and aggregate metrics for observability
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.action_space")


# ═══════════════════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════════════════

class ActionCategory(Enum):
    """Functional categories that an action may belong to."""
    COGNITIVE = "cognitive"
    COMMUNICATIVE = "communicative"
    TOOL_BASED = "tool_based"
    NAVIGATIONAL = "navigational"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"


class ActionStatus(Enum):
    """Lifecycle / availability status of a registered action."""
    AVAILABLE = "available"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class FeasibilityLevel(Enum):
    """Granular feasibility verdict, ordered from best to worst."""
    FULLY_FEASIBLE = 0
    CONDITIONALLY_FEASIBLE = 1
    PARTIALLY_FEASIBLE = 2
    INFEASIBLE = 3


class ConstraintType(Enum):
    """Classification of an action constraint."""
    PRECONDITION = "precondition"
    RESOURCE_LIMIT = "resource_limit"
    PERMISSION = "permission"
    TEMPORAL = "temporal"
    CONTEXTUAL = "contextual"
    DEPENDENCY = "dependency"


class ValidationResult(Enum):
    """Outcome of validating action parameters and resources."""
    VALID = "valid"
    INVALID = "invalid"
    NEEDS_REFINEMENT = "needs_refinement"
    REQUIRES_APPROVAL = "requires_approval"
    OUT_OF_SCOPE = "out_of_scope"


class RiskLevel(Enum):
    """Risk severity, ordered from none to critical."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ActionConstraint:
    """A single constraint attached to an action.

    Constraints are evaluated during feasibility checks. The ``check_function_name``
    field names a (mock) evaluator that the runtime would resolve; the actual
    evaluation logic lives inside ``AgentActionSpace._evaluate_constraint``.
    """
    constraint_id: str
    constraint_type: ConstraintType
    description: str
    check_function_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    severity: RiskLevel = RiskLevel.LOW
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type.value,
            "description": self.description,
            "check_function_name": self.check_function_name,
            "parameters": dict(self.parameters),
            "severity": self.severity.value,
            "created_at": self.created_at,
        }


@dataclass
class ActionDefinition:
    """A registered action and its metadata."""
    action_id: str
    name: str
    description: str
    category: ActionCategory
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    required_resources: list[str] = field(default_factory=list)
    estimated_duration_ms: int = 0
    estimated_cost: float = 0.0
    risk_level: RiskLevel = RiskLevel.NONE
    status: ActionStatus = ActionStatus.AVAILABLE
    constraints: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    invocation_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters_schema": dict(self.parameters_schema),
            "required_resources": list(self.required_resources),
            "estimated_duration_ms": self.estimated_duration_ms,
            "estimated_cost": self.estimated_cost,
            "risk_level": self.risk_level.value,
            "status": self.status.value,
            "constraints": list(self.constraints),
            "tags": list(self.tags),
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "invocation_count": self.invocation_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


@dataclass
class FeasibilityReport:
    """Detailed output of a feasibility evaluation for one action."""
    action_id: str
    level: FeasibilityLevel
    score: float
    satisfied_constraints: list[str] = field(default_factory=list)
    violated_constraints: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "level": self.level.value,
            "score": round(self.score, 4),
            "satisfied_constraints": list(self.satisfied_constraints),
            "violated_constraints": list(self.violated_constraints),
            "warnings": list(self.warnings),
            "suggestions": list(self.suggestions),
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class ActionExecution:
    """A recorded execution of an action."""
    execution_id: str
    action_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    status: str = "started"
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "action_id": self.action_id,
            "parameters": dict(self.parameters),
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": dict(self.result) if self.result is not None else None,
            "error": self.error,
        }


@dataclass
class ActionSpaceStats:
    """Aggregate statistics for the entire action space."""
    total_actions: int = 0
    actions_by_category: dict[str, int] = field(default_factory=dict)
    actions_by_status: dict[str, int] = field(default_factory=dict)
    total_executions: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    constraint_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_actions": self.total_actions,
            "actions_by_category": dict(self.actions_by_category),
            "actions_by_status": dict(self.actions_by_status),
            "total_executions": self.total_executions,
            "success_rate": round(self.success_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "constraint_count": self.constraint_count,
        }


# ═══════════════════════════════════════════════════════════════════════════
# AgentActionSpace
# ═══════════════════════════════════════════════════════════════════════════

# Mapping from a schema-declared type name to a Python type used for validation.
_SCHEMA_TYPE_MAP: dict[str, type] = {
    "string": str,
    "str": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": bool,
    "boolean": bool,
    "list": list,
    "dict": dict,
    "object": dict,
}

# Statuses that block feasibility entirely.
_BLOCKING_STATUSES = {ActionStatus.BLOCKED, ActionStatus.DEPRECATED}


class AgentActionSpace:
    """Thread-safe registry and feasibility engine for agent actions.

    The action space is the single source of truth for what an agent *can* do.
    It owns four stores:

    * ``_actions`` — registered :class:`ActionDefinition` instances keyed by ID.
    * ``_constraints`` — :class:`ActionConstraint` instances keyed by constraint ID.
    * ``_executions`` — ordered :class:`ActionExecution` log keyed by execution ID.
    * ``_execution_order`` — list of execution IDs preserving insertion order.

    All mutations are guarded by ``self._lock``.
    """

    MAX_ACTIONS: int = 1000
    MAX_EXECUTIONS_LOG: int = 5000

    def __init__(self) -> None:
        """Initialize empty storage and a re-entrant lock."""
        self._actions: dict[str, ActionDefinition] = {}
        self._constraints: dict[str, ActionConstraint] = {}
        self._executions: dict[str, ActionExecution] = {}
        self._execution_order: list[str] = []
        self._lock = threading.Lock()

    # ── Action registry ──────────────────────────────────────────

    def register_action(
        self,
        name: str,
        description: str,
        category: ActionCategory,
        parameters_schema: dict[str, Any] | None = None,
        required_resources: list[str] | None = None,
        estimated_duration_ms: int = 0,
        estimated_cost: float = 0.0,
        risk_level: RiskLevel = RiskLevel.NONE,
        tags: list[str] | None = None,
    ) -> ActionDefinition:
        """Register a new action and return its definition.

        Raises:
            RuntimeError: If the action registry is at capacity.
            ValueError: If ``name`` is empty.
        """
        if not name or not name.strip():
            raise ValueError("Action name must not be empty")

        with self._lock:
            if len(self._actions) >= self.MAX_ACTIONS:
                raise RuntimeError(
                    f"Cannot register action: registry at capacity ({self.MAX_ACTIONS})"
                )

            action_id = f"action-{uuid.uuid4().hex[:12]}"
            now = time.time()
            action = ActionDefinition(
                action_id=action_id,
                name=name.strip(),
                description=description,
                category=category,
                parameters_schema=dict(parameters_schema) if parameters_schema else {},
                required_resources=list(required_resources) if required_resources else [],
                estimated_duration_ms=estimated_duration_ms,
                estimated_cost=estimated_cost,
                risk_level=risk_level,
                status=ActionStatus.AVAILABLE,
                constraints=[],
                tags=list(tags) if tags else [],
                version=1,
                created_at=now,
                updated_at=now,
                invocation_count=0,
                success_count=0,
                failure_count=0,
            )
            self._actions[action_id] = action
            logger.debug(
                f"Action registered (id={action_id}, name={name}, category={category.value})"
            )
            return action

    def unregister_action(self, action_id: str) -> bool:
        """Remove an action and any constraints attached to it.

        Returns:
            True if the action was removed, False if it was not found.
        """
        with self._lock:
            action = self._actions.pop(action_id, None)
            if action is None:
                return False
            # Cascade: drop every constraint owned by this action.
            for constraint_id in list(action.constraints):
                self._constraints.pop(constraint_id, None)
            logger.debug(f"Action unregistered (id={action_id})")
            return True

    def get_action(self, action_id: str) -> ActionDefinition | None:
        """Retrieve an action by ID."""
        with self._lock:
            return self._actions.get(action_id)

    def update_action(self, action_id: str, **kwargs: Any) -> ActionDefinition | None:
        """Update mutable fields of a registered action.

        Only the following fields may be updated: ``name``, ``description``,
        ``parameters_schema``, ``required_resources``, ``estimated_duration_ms``,
        ``estimated_cost``, ``risk_level``, ``tags``. The ``version`` is
        incremented and ``updated_at`` is refreshed on every successful update.

        Returns:
            The updated action, or None if ``action_id`` was not found.
        """
        allowed = {
            "name", "description", "parameters_schema", "required_resources",
            "estimated_duration_ms", "estimated_cost", "risk_level", "tags",
        }
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return None
            for key, value in kwargs.items():
                if key not in allowed:
                    continue
                if key == "parameters_schema" and value is not None:
                    setattr(action, key, dict(value))
                elif key == "required_resources" and value is not None:
                    setattr(action, key, list(value))
                elif key == "tags" and value is not None:
                    setattr(action, key, list(value))
                else:
                    setattr(action, key, value)
            action.version += 1
            action.updated_at = time.time()
            return action

    def set_action_status(
        self, action_id: str, status: ActionStatus
    ) -> ActionDefinition | None:
        """Set the availability status of an action.

        Returns:
            The updated action, or None if ``action_id`` was not found.
        """
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return None
            action.status = status
            action.updated_at = time.time()
            logger.debug(
                f"Action status set (id={action_id}, status={status.value})"
            )
            return action

    def list_actions(
        self,
        category: ActionCategory | None = None,
        status: ActionStatus | None = None,
        tag: str | None = None,
    ) -> list[ActionDefinition]:
        """List registered actions, optionally filtered.

        Filters are AND-combined: an action is included only if it matches
        every non-None filter.
        """
        with self._lock:
            result: list[ActionDefinition] = []
            for action in self._actions.values():
                if category is not None and action.category is not category:
                    continue
                if status is not None and action.status is not status:
                    continue
                if tag is not None and tag not in action.tags:
                    continue
                result.append(action)
            return result

    # ── Constraints ──────────────────────────────────────────────

    def register_constraint(
        self,
        action_id: str,
        constraint_type: ConstraintType,
        description: str,
        check_function_name: str,
        parameters: dict[str, Any] | None = None,
        severity: RiskLevel = RiskLevel.LOW,
    ) -> ActionConstraint:
        """Attach a new constraint to an action.

        Raises:
            KeyError: If ``action_id`` is not registered.
        """
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                raise KeyError(f"Unknown action_id: {action_id}")

            constraint_id = f"constraint-{uuid.uuid4().hex[:12]}"
            constraint = ActionConstraint(
                constraint_id=constraint_id,
                constraint_type=constraint_type,
                description=description,
                check_function_name=check_function_name,
                parameters=dict(parameters) if parameters else {},
                severity=severity,
                created_at=time.time(),
            )
            self._constraints[constraint_id] = constraint
            action.constraints.append(constraint_id)
            action.updated_at = time.time()
            logger.debug(
                f"Constraint registered (id={constraint_id}, action={action_id}, "
                f"type={constraint_type.value})"
            )
            return constraint

    def remove_constraint(self, action_id: str, constraint_id: str) -> bool:
        """Remove a constraint from an action.

        Returns:
            True if the constraint was removed, False if either the action or
            the constraint was not found.
        """
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return False
            if constraint_id not in action.constraints:
                return False
            action.constraints.remove(constraint_id)
            self._constraints.pop(constraint_id, None)
            action.updated_at = time.time()
            return True

    # ── Feasibility ──────────────────────────────────────────────

    def check_feasibility(
        self,
        action_id: str,
        parameters: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> FeasibilityReport:
        """Evaluate whether an action may run in the current context.

        The evaluation proceeds in three stages:

        1. Existence and status — the action must exist and not be in a
           blocking status (BLOCKED / DEPRECATED).
        2. Constraint evaluation — every attached constraint is evaluated by
           :meth:`_evaluate_constraint`. Satisfied constraints raise the
           feasibility score; violated constraints lower it and contribute
           warnings.
        3. Score aggregation — the score starts at 1.0 and is reduced for each
           violated constraint proportional to its severity.

        Returns:
            A :class:`FeasibilityReport` with the level, score, and lists of
            satisfied / violated constraint IDs plus actionable suggestions.
        """
        params = parameters or {}
        ctx = context or {}

        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return FeasibilityReport(
                    action_id=action_id,
                    level=FeasibilityLevel.INFEASIBLE,
                    score=0.0,
                    violated_constraints=[],
                    warnings=["Action not found"],
                    suggestions=["Register the action before checking feasibility"],
                )

            if action.status in _BLOCKING_STATUSES:
                return FeasibilityReport(
                    action_id=action_id,
                    level=FeasibilityLevel.INFEASIBLE,
                    score=0.0,
                    warnings=[f"Action is {action.status.value}"],
                    suggestions=[f"Change the action status from {action.status.value}"],
                )

            satisfied: list[str] = []
            violated: list[str] = []
            warnings: list[str] = []
            suggestions: list[str] = []

            score = 1.0
            for constraint_id in action.constraints:
                constraint = self._constraints.get(constraint_id)
                if constraint is None:
                    continue
                ok, message = self._evaluate_constraint(constraint, params, ctx)
                if ok:
                    satisfied.append(constraint_id)
                else:
                    violated.append(constraint_id)
                    if message:
                        warnings.append(message)
                    # Severity-weighted penalty.
                    penalty = constraint.severity.value / RiskLevel.CRITICAL.value
                    score -= penalty

            # Status-based soft penalties (non-blocking statuses still count).
            if action.status == ActionStatus.RESTRICTED:
                score -= 0.15
                warnings.append("Action is restricted; additional approval may be required")
                suggestions.append("Request explicit approval before execution")
            elif action.status == ActionStatus.EXPERIMENTAL:
                score -= 0.10
                warnings.append("Action is experimental; behavior may be unstable")

            # Risk level contributes a small penalty.
            risk_penalty = action.risk_level.value / RiskLevel.CRITICAL.value * 0.2
            score -= risk_penalty
            if action.risk_level.value >= RiskLevel.HIGH.value:
                warnings.append(
                    f"High risk action (risk={action.risk_level.name.lower()})"
                )
                suggestions.append("Apply additional review for high-risk actions")

            score = max(0.0, min(1.0, score))

            if not violated and action.status == ActionStatus.AVAILABLE:
                level = FeasibilityLevel.FULLY_FEASIBLE
            elif score >= 0.5:
                level = FeasibilityLevel.CONDITIONALLY_FEASIBLE
            elif score > 0.0:
                level = FeasibilityLevel.PARTIALLY_FEASIBLE
                suggestions.append("Resolve violated constraints before executing")
            else:
                level = FeasibilityLevel.INFEASIBLE
                suggestions.append("Action cannot be executed under current constraints")

            return FeasibilityReport(
                action_id=action_id,
                level=level,
                score=score,
                satisfied_constraints=satisfied,
                violated_constraints=violated,
                warnings=warnings,
                suggestions=suggestions,
            )

    @staticmethod
    def _evaluate_constraint(
        constraint: ActionConstraint,
        parameters: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Mock constraint evaluator keyed on :class:`ConstraintType`.

        Real deployments would resolve ``constraint.check_function_name`` to a
        callable. Here we derive a deterministic verdict from the constraint
        type and its declared parameters so the feasibility report is stable
        across runs.

        Returns:
            A tuple of (satisfied, warning_message). ``warning_message`` is
            None when the constraint is satisfied.
        """
        ctype = constraint.constraint_type
        params = constraint.parameters

        if ctype == ConstraintType.PRECONDITION:
            required_keys = params.get("required_keys", [])
            missing = [k for k in required_keys if k not in parameters]
            if missing:
                return False, f"Missing required parameter(s): {', '.join(missing)}"
            return True, None

        if ctype == ConstraintType.RESOURCE_LIMIT:
            resource = params.get("resource", "")
            limit = params.get("limit", 0)
            available = context.get("resources", {}).get(resource, limit)
            if available < limit:
                return False, f"Resource '{resource}' below limit ({available} < {limit})"
            return True, None

        if ctype == ConstraintType.PERMISSION:
            required_role = params.get("role", "")
            roles = context.get("roles", [])
            if required_role and required_role not in roles:
                return False, f"Missing required role: {required_role}"
            return True, None

        if ctype == ConstraintType.TEMPORAL:
            start = params.get("start_hour", 0)
            end = params.get("end_hour", 24)
            current_hour = context.get("current_hour", time.localtime().tm_hour)
            if not (start <= current_hour < end):
                return False, f"Outside allowed time window [{start}, {end})"
            return True, None

        if ctype == ConstraintType.CONTEXTUAL:
            required_context = params.get("required_context_key", "")
            if required_context and required_context not in context:
                return False, f"Missing context key: {required_context}"
            return True, None

        if ctype == ConstraintType.DEPENDENCY:
            dependency = params.get("depends_on", "")
            completed = context.get("completed_actions", [])
            if dependency and dependency not in completed:
                return False, f"Dependency '{dependency}' has not completed"
            return True, None

        # Unknown constraint types are treated as satisfied.
        return True, None

    # ── Validation ───────────────────────────────────────────────

    def validate_action(
        self, action_id: str, parameters: dict[str, Any] | None = None
    ) -> ValidationResult:
        """Validate action parameters against the declared schema.

        Performs two checks:

        1. Schema type-checking — every declared parameter is compared against
           the type named in ``parameters_schema``. Unknown schema type names
           are ignored. Missing required parameters (``required: True``) yield
           an INVALID verdict.
        2. Required resources — if the action declares ``required_resources``
           they are expected to appear in ``parameters`` under the ``resources``
           key. Missing resources return NEEDS_REFINEMENT.

        Returns:
            A :class:`ValidationResult` describing the outcome.
        """
        params = parameters or {}

        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return ValidationResult.OUT_OF_SCOPE

            # ── Schema type checking ──
            schema = action.parameters_schema
            if schema:
                properties = schema.get("properties", schema)
                for key, spec in properties.items():
                    if not isinstance(spec, dict):
                        continue
                    required = spec.get("required", False)
                    declared_type = spec.get("type", "")
                    if required and key not in params:
                        return ValidationResult.INVALID
                    if key not in params:
                        continue
                    expected = _SCHEMA_TYPE_MAP.get(declared_type)
                    if expected is None:
                        continue
                    value = params[key]
                    # bool is a subclass of int; reject when a strict int is
                    # declared but a bool is supplied.
                    if expected is int and isinstance(value, bool):
                        return ValidationResult.INVALID
                    if not isinstance(value, expected):
                        return ValidationResult.INVALID

            # ── Required resources availability ──
            if action.required_resources:
                provided_resources = params.get("resources", {})
                if isinstance(provided_resources, dict):
                    missing = [
                        r for r in action.required_resources
                        if r not in provided_resources
                    ]
                else:
                    missing = list(action.required_resources)
                if missing:
                    return ValidationResult.NEEDS_REFINEMENT

            # High-risk actions require explicit approval.
            if action.risk_level.value >= RiskLevel.HIGH.value:
                return ValidationResult.REQUIRES_APPROVAL

            return ValidationResult.VALID

    # ── Execution log ────────────────────────────────────────────

    def record_execution(
        self,
        action_id: str,
        parameters: dict[str, Any] | None = None,
        status: str = "completed",
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> ActionExecution:
        """Record an execution and update the parent action's counters.

        The execution log is capped at :attr:`MAX_EXECUTIONS_LOG`; when full,
        the oldest entry is evicted.

        Returns:
            The created :class:`ActionExecution`.
        """
        with self._lock:
            execution_id = f"exec-{uuid.uuid4().hex[:12]}"
            now = time.time()
            execution = ActionExecution(
                execution_id=execution_id,
                action_id=action_id,
                parameters=dict(parameters) if parameters else {},
                status=status,
                started_at=now,
                completed_at=now,
                result=dict(result) if result else None,
                error=error,
            )
            self._executions[execution_id] = execution
            self._execution_order.append(execution_id)

            # Enforce the log cap by dropping the oldest entries.
            while len(self._execution_order) > self.MAX_EXECUTIONS_LOG:
                oldest_id = self._execution_order.pop(0)
                self._executions.pop(oldest_id, None)

            # Update the parent action's counters (if it still exists).
            action = self._actions.get(action_id)
            if action is not None:
                action.invocation_count += 1
                if status in ("completed", "success", "ok"):
                    action.success_count += 1
                elif status in ("failed", "error", "cancelled"):
                    action.failure_count += 1

            logger.debug(
                f"Execution recorded (id={execution_id}, action={action_id}, status={status})"
            )
            return execution

    def get_execution(self, execution_id: str) -> ActionExecution | None:
        """Retrieve an execution by ID."""
        with self._lock:
            return self._executions.get(execution_id)

    def list_executions(
        self, action_id: str | None = None, limit: int = 100
    ) -> list[ActionExecution]:
        """List executions, optionally filtered by action ID.

        Results are returned in reverse-chronological order (newest first).
        """
        if limit <= 0:
            return []
        with self._lock:
            if action_id is None:
                ids = list(reversed(self._execution_order))
            else:
                ids = [
                    eid for eid in reversed(self._execution_order)
                    if self._executions[eid].action_id == action_id
                ]
            return [self._executions[eid] for eid in ids[:limit]]

    # ── Statistics ───────────────────────────────────────────────

    def get_action_stats(self, action_id: str) -> dict[str, Any]:
        """Return per-action statistics.

        Returns an empty dict if the action is not found.
        """
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return {}
            total = action.success_count + action.failure_count
            success_rate = (action.success_count / total) if total else 0.0
            return {
                "action_id": action.action_id,
                "name": action.name,
                "category": action.category.value,
                "status": action.status.value,
                "invocation_count": action.invocation_count,
                "success_count": action.success_count,
                "failure_count": action.failure_count,
                "success_rate": round(success_rate, 4),
                "constraint_count": len(action.constraints),
                "version": action.version,
                "estimated_duration_ms": action.estimated_duration_ms,
                "estimated_cost": action.estimated_cost,
                "risk_level": action.risk_level.value,
            }

    def get_stats(self) -> ActionSpaceStats:
        """Compute aggregate statistics across the entire action space."""
        with self._lock:
            total_actions = len(self._actions)
            actions_by_category: dict[str, int] = {}
            actions_by_status: dict[str, int] = {}
            for action in self._actions.values():
                cat = action.category.value
                actions_by_category[cat] = actions_by_category.get(cat, 0) + 1
                st = action.status.value
                actions_by_status[st] = actions_by_status.get(st, 0) + 1

            total_executions = len(self._executions)
            total_success = 0
            total_fail = 0
            total_duration_ms = 0.0
            duration_samples = 0
            for execution in self._executions.values():
                if execution.status in ("completed", "success", "ok"):
                    total_success += 1
                elif execution.status in ("failed", "error", "cancelled"):
                    total_fail += 1
                if execution.completed_at is not None:
                    duration_ms = (execution.completed_at - execution.started_at) * 1000.0
                    total_duration_ms += duration_ms
                    duration_samples += 1

            success_rate = (
                total_success / (total_success + total_fail)
                if (total_success + total_fail) else 0.0
            )
            avg_duration_ms = (
                total_duration_ms / duration_samples if duration_samples else 0.0
            )

            return ActionSpaceStats(
                total_actions=total_actions,
                actions_by_category=actions_by_category,
                actions_by_status=actions_by_status,
                total_executions=total_executions,
                success_rate=success_rate,
                avg_duration_ms=avg_duration_ms,
                constraint_count=len(self._constraints),
            )

    # ── Lifecycle ────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear every store so the space returns to its initial state."""
        with self._lock:
            self._actions.clear()
            self._constraints.clear()
            self._executions.clear()
            self._execution_order.clear()
            logger.debug("Action space reset")


# ═══════════════════════════════════════════════════════════════════════════
# Singleton accessors
# ═══════════════════════════════════════════════════════════════════════════

_action_space: AgentActionSpace | None = None


def get_action_space() -> AgentActionSpace:
    """Get or create the singleton action space instance.

    Returns:
        The shared :class:`AgentActionSpace` instance.
    """
    global _action_space
    if _action_space is None:
        _action_space = AgentActionSpace()
    return _action_space


def reset_action_space() -> None:
    """Reset the singleton action space instance.

    Clears any existing instance so the next call to :func:`get_action_space`
    creates a fresh action space.
    """
    global _action_space
    if _action_space is not None:
        _action_space.reset()
    _action_space = None
