"""
Buddy Agent Policy Gateway.

Multi-tier governance system that inspects every agent action and decides
whether to allow, block, or pause for human approval. Policies stack across
global, agent, and session scopes so broad guardrails can be refined by more
specific rules closer to the action being performed.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PolicyLevel(Enum):
    """Governance tiers, ordered from broadest to most specific scope."""

    GLOBAL = "global"
    AGENT = "agent"
    SESSION = "session"


class PolicyAction(Enum):
    """Decision a policy rule can return when it matches an action."""

    ALLOW = "allow"
    BLOCK = "block"
    APPROVE = "approve"
    LOG = "log"


class PolicyCategory(Enum):
    """Categories of agent actions governed by policies."""

    TOOL_EXECUTION = "tool_execution"
    FILE_ACCESS = "file_access"
    NETWORK_ACCESS = "network_access"
    CODE_EXECUTION = "code_execution"
    DATA_ACCESS = "data_access"
    SYSTEM_OPERATION = "system_operation"


class PolicyStatus(Enum):
    """Lifecycle status of a policy rule."""

    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"


# Evaluation order: most specific scope first so session rules override
# agent-level rules, which in turn override global rules.
_LEVEL_EVALUATION_ORDER: tuple[PolicyLevel, ...] = (
    PolicyLevel.SESSION,
    PolicyLevel.AGENT,
    PolicyLevel.GLOBAL,
)


@dataclass
class PolicyRule:
    """A single governance rule controlling a category of agent actions."""

    rule_id: str
    name: str
    description: str
    level: PolicyLevel
    category: PolicyCategory
    action: PolicyAction
    conditions: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    status: PolicyStatus = PolicyStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    hit_count: int = 0


@dataclass
class ApprovalRequest:
    """A request that pauses an agent action pending human approval."""

    request_id: str
    rule_id: str
    agent_id: str
    action_description: str
    context: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    requested_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved_by: str = ""
    notes: str = ""


@dataclass
class PolicyEvaluation:
    """The outcome of evaluating an action against the rule set."""

    evaluation_id: str
    rule_id: str
    action: PolicyAction
    reason: str
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PolicyAuditEntry:
    """An immutable record of a governance decision for audit purposes."""

    entry_id: str
    agent_id: str
    action_type: str
    category: PolicyCategory
    rule_id: str
    decision: str
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)


def _match_conditions(conditions: dict[str, Any], context: dict[str, Any]) -> bool:
    """Return True when every condition key matches the supplied context.

    An empty conditions dict acts as a wildcard and matches any context.
    If a condition value is a list, the corresponding context value must be
    a member of that list. Otherwise an exact equality comparison is used.
    Missing context keys cause the match to fail.
    """
    if not conditions:
        return True
    for key, expected in conditions.items():
        if key not in context:
            return False
        actual = context[key]
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


class AgentPolicyGateway:
    """Multi-tier policy gateway that governs every agent action.

    Rules are stored in-memory and evaluated in scope-priority order
    (session > agent > global) so that more specific scopes take
    precedence. The gateway also tracks approval workflows and an
    append-only audit log of governance decisions.
    """

    MAX_RULES: int = 500
    MAX_AUDIT_ENTRIES: int = 10000
    APPROVAL_TIMEOUT: int = 3600

    def __init__(self) -> None:
        """Initialize empty storage and counters for the gateway."""
        self._rules: dict[str, PolicyRule] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._audit_entries: list[PolicyAuditEntry] = []
        self._total_evaluations: int = 0

    # -- Rule management --------------------------------------------

    def add_rule(
        self,
        name: str,
        description: str,
        level: PolicyLevel,
        category: PolicyCategory,
        action: PolicyAction,
        conditions: Optional[dict[str, Any]] = None,
        priority: int = 0,
    ) -> PolicyRule:
        """Create and register a new policy rule.

        Args:
            name: Human-readable rule name.
            description: Short description of the rule's intent.
            level: Governance tier the rule belongs to.
            category: Action category the rule applies to.
            action: Decision returned when the rule matches.
            conditions: Optional context matchers. An empty dict acts as
                a wildcard.
            priority: Higher values are evaluated earlier within a tier.

        Returns:
            The newly created PolicyRule.

        Raises:
            ValueError: If the rule cap has been reached.
        """
        if len(self._rules) >= self.MAX_RULES:
            raise ValueError(
                f"Cannot add rule: maximum of {self.MAX_RULES} rules reached"
            )
        now = time.time()
        rule = PolicyRule(
            rule_id=str(uuid.uuid4()),
            name=name,
            description=description,
            level=level,
            category=category,
            action=action,
            conditions=dict(conditions) if conditions else {},
            priority=priority,
            status=PolicyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            hit_count=0,
        )
        self._rules[rule.rule_id] = rule
        logger.info("Policy rule added: %s (%s)", rule.name, rule.rule_id)
        return rule

    def update_rule(
        self,
        rule_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        action: Optional[PolicyAction] = None,
        conditions: Optional[dict[str, Any]] = None,
        priority: Optional[int] = None,
        status: Optional[PolicyStatus] = None,
    ) -> Optional[PolicyRule]:
        """Update fields of an existing rule by ID.

        Only the supplied arguments are modified; all others are left
        unchanged. The ``updated_at`` timestamp is refreshed on success.

        Args:
            rule_id: ID of the rule to update.
            name: Optional new name.
            description: Optional new description.
            action: Optional new action.
            conditions: Optional replacement conditions dict.
            priority: Optional new priority.
            status: Optional new status.

        Returns:
            The updated PolicyRule, or None if the rule was not found.
        """
        rule = self._rules.get(rule_id)
        if rule is None:
            return None
        if name is not None:
            rule.name = name
        if description is not None:
            rule.description = description
        if action is not None:
            rule.action = action
        if conditions is not None:
            rule.conditions = dict(conditions)
        if priority is not None:
            rule.priority = priority
        if status is not None:
            rule.status = status
        rule.updated_at = time.time()
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the gateway.

        Args:
            rule_id: ID of the rule to remove.

        Returns:
            True if the rule was removed, False if it was not found.
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Return the rule with the given ID, or None if missing."""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        level: Optional[PolicyLevel] = None,
        category: Optional[PolicyCategory] = None,
        status: Optional[PolicyStatus] = None,
    ) -> list[PolicyRule]:
        """List rules, optionally filtered by level, category, and status.

        Args:
            level: Optional level filter.
            category: Optional category filter.
            status: Optional status filter.

        Returns:
            A list of matching rules sorted by priority descending.
        """
        results: list[PolicyRule] = []
        for rule in self._rules.values():
            if level is not None and rule.level != level:
                continue
            if category is not None and rule.category != category:
                continue
            if status is not None and rule.status != status:
                continue
            results.append(rule)
        results.sort(key=lambda r: r.priority, reverse=True)
        return results

    # -- Evaluation -------------------------------------------------

    def evaluate(
        self,
        agent_id: str,
        action_type: str,
        category: PolicyCategory,
        context: Optional[dict[str, Any]] = None,
    ) -> PolicyEvaluation:
        """Evaluate an action against the rule set.

        Rules are checked in scope-priority order (session > agent >
        global). Within each scope, higher-priority rules are checked
        first. The first matching active rule determines the returned
        action. If no rule matches, the action is allowed by default.

        Args:
            agent_id: ID of the agent requesting the action.
            action_type: A short identifier for the action being taken.
            category: The category the action falls under.
            context: Optional context dict used for condition matching.

        Returns:
            A PolicyEvaluation describing the decision and reason.
        """
        self._total_evaluations += 1
        ctx = dict(context) if context else {}
        # Always expose the action_type and agent_id to condition matchers
        # so rules can reference them without callers having to duplicate
        # the values inside context.
        ctx.setdefault("action_type", action_type)
        ctx.setdefault("agent_id", agent_id)

        for level in _LEVEL_EVALUATION_ORDER:
            # Collect active rules for this level and category, then sort
            # by priority descending so the strongest rule wins.
            tier_rules = [
                rule
                for rule in self._rules.values()
                if rule.level == level
                and rule.category == category
                and rule.status == PolicyStatus.ACTIVE
            ]
            tier_rules.sort(key=lambda r: r.priority, reverse=True)

            for rule in tier_rules:
                if _match_conditions(rule.conditions, ctx):
                    rule.hit_count += 1
                    evaluation = PolicyEvaluation(
                        evaluation_id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        action=rule.action,
                        reason=f"Matched rule '{rule.name}' at {rule.level.value} level",
                        context_snapshot=dict(ctx),
                        timestamp=time.time(),
                    )
                    logger.debug(
                        "Action %s for agent %s evaluated as %s by rule %s",
                        action_type,
                        agent_id,
                        rule.action.value,
                        rule.rule_id,
                    )
                    return evaluation

        # No matching rule: default to allow so the gateway fails open.
        evaluation = PolicyEvaluation(
            evaluation_id=str(uuid.uuid4()),
            rule_id="",
            action=PolicyAction.ALLOW,
            reason="No matching rule found; defaulting to ALLOW",
            context_snapshot=dict(ctx),
            timestamp=time.time(),
        )
        return evaluation

    # -- Approval workflow ------------------------------------------

    def request_approval(
        self,
        rule_id: str,
        agent_id: str,
        action_description: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """Create a pending approval request for an agent action.

        Args:
            rule_id: ID of the rule that triggered the approval.
            agent_id: ID of the agent requesting approval.
            action_description: Human-readable description of the action.
            context: Optional context dict captured for reviewers.

        Returns:
            The newly created ApprovalRequest in the pending state.
        """
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            rule_id=rule_id,
            agent_id=agent_id,
            action_description=action_description,
            context=dict(context) if context else {},
            status="pending",
            requested_at=time.time(),
            resolved_at=None,
            resolved_by="",
            notes="",
        )
        self._approvals[request.request_id] = request
        logger.info(
            "Approval request %s created for agent %s",
            request.request_id,
            agent_id,
        )
        return request

    def resolve_approval(
        self,
        request_id: str,
        approved: bool,
        resolved_by: str = "",
        notes: str = "",
    ) -> Optional[ApprovalRequest]:
        """Resolve a pending approval request.

        Pending requests older than APPROVAL_TIMEOUT seconds are
        automatically marked as expired.

        Args:
            request_id: ID of the approval request to resolve.
            approved: True to approve, False to deny.
            resolved_by: Identifier of the resolver.
            notes: Optional notes explaining the decision.

        Returns:
            The updated ApprovalRequest, or None if not found or already
            resolved.
        """
        request = self._approvals.get(request_id)
        if request is None:
            return None
        if request.status != "pending":
            return None
        # Auto-expire stale requests before resolving.
        if time.time() - request.requested_at > self.APPROVAL_TIMEOUT:
            request.status = "expired"
            request.resolved_at = time.time()
            request.resolved_by = resolved_by
            request.notes = notes or "auto-expired due to timeout"
            return request
        request.status = "approved" if approved else "denied"
        request.resolved_at = time.time()
        request.resolved_by = resolved_by
        request.notes = notes
        logger.info(
            "Approval %s resolved as %s by %s",
            request_id,
            request.status,
            resolved_by,
        )
        return request

    def get_pending_approvals(
        self, agent_id: Optional[str] = None
    ) -> list[ApprovalRequest]:
        """Return pending approval requests, optionally for one agent.

        Args:
            agent_id: Optional agent filter. If None, all pending
                requests are returned.

        Returns:
            A list of pending ApprovalRequest objects ordered by
            requested_at ascending.
        """
        results = [
            request
            for request in self._approvals.values()
            if request.status == "pending"
            and (agent_id is None or request.agent_id == agent_id)
        ]
        results.sort(key=lambda r: r.requested_at)
        return results

    # -- Audit log --------------------------------------------------

    def audit_log(
        self,
        agent_id: str,
        action_type: str,
        category: PolicyCategory,
        rule_id: str,
        decision: str,
        details: Optional[dict[str, Any]] = None,
    ) -> PolicyAuditEntry:
        """Append an audit entry describing a governance decision.

        Args:
            agent_id: ID of the agent that performed the action.
            action_type: The action type that was evaluated.
            category: The category of the action.
            rule_id: ID of the rule that drove the decision (may be empty).
            decision: Short label for the decision (e.g. "allow").
            details: Optional extra context for the audit entry.

        Returns:
            The created PolicyAuditEntry.
        """
        entry = PolicyAuditEntry(
            entry_id=str(uuid.uuid4()),
            agent_id=agent_id,
            action_type=action_type,
            category=category,
            rule_id=rule_id,
            decision=decision,
            timestamp=time.time(),
            details=dict(details) if details else {},
        )
        self._audit_entries.append(entry)
        # Trim the audit log to the configured maximum to bound memory use.
        if len(self._audit_entries) > self.MAX_AUDIT_ENTRIES:
            overflow = len(self._audit_entries) - self.MAX_AUDIT_ENTRIES
            del self._audit_entries[:overflow]
        return entry

    def get_audit_entries(
        self, agent_id: Optional[str] = None, limit: int = 100
    ) -> list[PolicyAuditEntry]:
        """Return recent audit entries, optionally filtered by agent.

        Args:
            agent_id: Optional agent filter. If None, entries for all
                agents are returned.
            limit: Maximum number of entries to return.

        Returns:
            A list of PolicyAuditEntry objects ordered newest first.
        """
        if agent_id is not None:
            filtered = [
                entry for entry in self._audit_entries if entry.agent_id == agent_id
            ]
        else:
            filtered = list(self._audit_entries)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)
        if limit > 0:
            return filtered[:limit]
        return filtered

    # -- Stats & maintenance ----------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return a summary of the gateway's current state.

        The returned dict includes rule counts, evaluation/approval
        counters, and distributions of rules by action and category.
        """
        action_distribution: dict[str, int] = {}
        category_distribution: dict[str, int] = {}
        active_rules = 0
        for rule in self._rules.values():
            action_distribution[rule.action.value] = (
                action_distribution.get(rule.action.value, 0) + 1
            )
            category_distribution[rule.category.value] = (
                category_distribution.get(rule.category.value, 0) + 1
            )
            if rule.status == PolicyStatus.ACTIVE:
                active_rules += 1
        pending_count = sum(
            1 for r in self._approvals.values() if r.status == "pending"
        )
        return {
            "total_rules": len(self._rules),
            "active_rules": active_rules,
            "total_evaluations": self._total_evaluations,
            "total_approvals": len(self._approvals),
            "pending_approvals": pending_count,
            "action_distribution": action_distribution,
            "category_distribution": category_distribution,
        }

    def reset(self) -> None:
        """Clear all rules, approvals, audit entries, and counters."""
        self._rules.clear()
        self._approvals.clear()
        self._audit_entries.clear()
        self._total_evaluations = 0
        logger.info("AgentPolicyGateway state has been reset.")


# -- Singleton Access ---------------------------------------------------

_policy_gateway_instance: Optional[AgentPolicyGateway] = None


def get_policy_gateway() -> AgentPolicyGateway:
    """Get the singleton AgentPolicyGateway instance.

    Creates the gateway on first call. Subsequent calls return the same
    instance, providing a single point of governance across the platform.

    Returns:
        The singleton AgentPolicyGateway instance.
    """
    global _policy_gateway_instance
    if _policy_gateway_instance is None:
        _policy_gateway_instance = AgentPolicyGateway()
        logger.info("Agent Policy Gateway singleton initialized.")
    return _policy_gateway_instance


def reset_policy_gateway() -> None:
    """Reset the singleton AgentPolicyGateway instance.

    Destroys the current singleton and clears all state. The next call
    to get_policy_gateway() will create a fresh instance.
    """
    global _policy_gateway_instance
    if _policy_gateway_instance is not None:
        _policy_gateway_instance.reset()
    _policy_gateway_instance = None
    logger.info("Agent Policy Gateway singleton has been reset.")
