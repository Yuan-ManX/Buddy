"""
Buddy Agent Governance System

Policy-based action control, approval flows, budget management, and
three-tier governance (server, agent, session). Ensures agents operate
within defined boundaries while maintaining flexibility for complex tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class PolicyLevel(Enum):
    """Governance scope levels from broadest to most specific."""

    SERVER = "server"
    AGENT = "agent"
    SESSION = "session"


class PolicyAction(Enum):
    """Actions a policy can take when triggered."""

    ALLOW = "allow"
    BLOCK = "block"
    ASK = "ask"
    LOG = "log"
    THROTTLE = "throttle"


class PolicyCategory(Enum):
    """Categories of governance policies."""

    SAFETY = "safety"
    COST = "cost"
    SECURITY = "security"
    PRIVACY = "privacy"
    QUALITY = "quality"
    RESOURCE = "resource"
    CUSTOM = "custom"


@dataclass
class PolicyRule:
    """A single governance rule that controls agent behavior."""

    rule_id: str
    name: str
    description: str = ""
    category: PolicyCategory = PolicyCategory.CUSTOM
    level: PolicyLevel = PolicyLevel.SESSION
    action: PolicyAction = PolicyAction.ASK

    # Conditions for triggering
    tool_patterns: list[str] = field(default_factory=list)
    file_patterns: list[str] = field(default_factory=list)
    domain_patterns: list[str] = field(default_factory=list)
    max_tokens_per_call: int = 0
    max_tokens_per_session: int = 0
    max_cost_per_session: float = 0.0
    max_tool_calls_per_session: int = 0
    require_approval_above_cost: float = 0.0

    # Custom condition function (callable)
    condition_fn: Callable | None = None

    enabled: bool = True
    priority: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def evaluate(self, context: dict) -> tuple[PolicyAction, str]:
        """Evaluate this rule against the given context."""
        if not self.enabled:
            return PolicyAction.ALLOW, "Rule disabled"

        reason_parts = []

        # Check tool patterns
        if self.tool_patterns:
            tool_name = context.get("tool_name", "")
            if any(pattern in tool_name for pattern in self.tool_patterns):
                reason_parts.append(f"tool '{tool_name}' matches pattern")

        # Check file patterns
        if self.file_patterns:
            file_path = context.get("file_path", "")
            if any(pattern in file_path for pattern in self.file_patterns):
                reason_parts.append(f"file '{file_path}' matches pattern")

        # Check domain patterns
        if self.domain_patterns:
            domain = context.get("domain", "")
            if any(pattern in domain for pattern in self.domain_patterns):
                reason_parts.append(f"domain '{domain}' matches pattern")

        # Check token limits
        if self.max_tokens_per_call > 0:
            tokens = context.get("tokens", 0)
            if tokens > self.max_tokens_per_call:
                reason_parts.append(f"tokens {tokens} > max {self.max_tokens_per_call}")

        if self.max_tokens_per_session > 0:
            session_tokens = context.get("session_tokens", 0)
            if session_tokens > self.max_tokens_per_session:
                reason_parts.append(f"session tokens {session_tokens} > max {self.max_tokens_per_session}")

        # Check cost limits
        if self.max_cost_per_session > 0:
            cost = context.get("session_cost", 0.0)
            if cost > self.max_cost_per_session:
                reason_parts.append(f"session cost ${cost:.4f} > max ${self.max_cost_per_session:.2f}")

        if self.require_approval_above_cost > 0:
            call_cost = context.get("estimated_cost", 0.0)
            if call_cost > self.require_approval_above_cost:
                reason_parts.append(f"estimated cost ${call_cost:.4f} > approval threshold")
                return PolicyAction.ASK, "; ".join(reason_parts)

        # Check tool calls
        if self.max_tool_calls_per_session > 0:
            tool_calls = context.get("session_tool_calls", 0)
            if tool_calls > self.max_tool_calls_per_session:
                reason_parts.append(f"tool calls {tool_calls} > max {self.max_tool_calls_per_session}")

        # Custom condition
        if self.condition_fn:
            try:
                if not self.condition_fn(context):
                    reason_parts.append("custom condition failed")
            except Exception as e:
                logger.warning("Custom condition error: %s", e)

        if reason_parts:
            return self.action, "; ".join(reason_parts)

        return PolicyAction.ALLOW, "No rules matched"

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "level": self.level.value,
            "action": self.action.value,
            "tool_patterns": self.tool_patterns,
            "file_patterns": self.file_patterns,
            "domain_patterns": self.domain_patterns,
            "max_tokens_per_call": self.max_tokens_per_call,
            "max_tokens_per_session": self.max_tokens_per_session,
            "max_cost_per_session": self.max_cost_per_session,
            "max_tool_calls_per_session": self.max_tool_calls_per_session,
            "require_approval_above_cost": self.require_approval_above_cost,
            "enabled": self.enabled,
            "priority": self.priority,
            "created_at": self.created_at,
        }


@dataclass
class ApprovalRequest:
    """A pending approval that requires user action."""

    request_id: str
    rule_id: str
    agent_id: str
    session_id: str
    action_description: str
    context: dict
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None
    resolution: str | None = None

    def approve(self):
        self.status = "approved"
        self.resolved_at = datetime.now(timezone.utc).isoformat()
        self.resolution = "approved"

    def deny(self):
        self.status = "denied"
        self.resolved_at = datetime.now(timezone.utc).isoformat()
        self.resolution = "denied"

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "rule_id": self.rule_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "action_description": self.action_description,
            "context": self.context,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution,
        }


@dataclass
class BudgetTracker:
    """Tracks and enforces budget limits for agents and sessions."""

    agent_id: str
    budget_limit: float = 0.0
    warning_thresholds: list[float] = field(default_factory=list)
    total_spent: float = 0.0
    total_tokens: int = 0
    total_tool_calls: int = 0
    warnings_issued: int = 0
    budget_exceeded: bool = False

    def record_spend(self, cost: float, tokens: int, tool_calls: int = 0):
        """Record a spend event."""
        self.total_spent += cost
        self.total_tokens += tokens
        self.total_tool_calls += tool_calls

        if self.budget_limit > 0 and self.total_spent >= self.budget_limit:
            self.budget_exceeded = True

        for threshold in sorted(self.warning_thresholds):
            if self.total_spent >= threshold and self.total_spent - cost < threshold:
                self.warnings_issued += 1

    def can_spend(self, estimated_cost: float = 0.0) -> bool:
        """Check if more spending is allowed."""
        if self.budget_exceeded:
            return False
        if self.budget_limit > 0 and self.total_spent + estimated_cost > self.budget_limit:
            return False
        return True

    def get_status(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "budget_limit": self.budget_limit,
            "total_spent": self.total_spent,
            "remaining": self.budget_limit - self.total_spent if self.budget_limit > 0 else float("inf"),
            "total_tokens": self.total_tokens,
            "total_tool_calls": self.total_tool_calls,
            "warnings_issued": self.warnings_issued,
            "budget_exceeded": self.budget_exceeded,
        }


class GovernanceEngine:
    """Central governance engine managing policies, approvals, and budgets."""

    def __init__(self):
        # Three-tier policy storage
        self._server_policies: dict[str, PolicyRule] = {}
        self._agent_policies: dict[str, dict[str, PolicyRule]] = {}
        self._session_policies: dict[str, dict[str, PolicyRule]] = {}

        # Approval tracking
        self._pending_approvals: dict[str, ApprovalRequest] = {}
        self._approval_history: list[ApprovalRequest] = []

        # Budget tracking
        self._budgets: dict[str, BudgetTracker] = {}

        # Audit log
        self._audit_log: list[dict] = []

        # Default policies
        self._init_defaults()

    def _init_defaults(self):
        """Initialize default governance policies."""
        defaults = [
            PolicyRule(
                rule_id="safety_shell_commands",
                name="Review Shell Commands",
                description="Ask for approval before executing shell commands",
                category=PolicyCategory.SAFETY,
                level=PolicyLevel.SERVER,
                action=PolicyAction.ASK,
                tool_patterns=["execute_command", "shell", "bash", "terminal"],
                priority=10,
            ),
            PolicyRule(
                rule_id="safety_file_writes",
                name="Review File Writes",
                description="Ask for approval before writing to files outside workspace",
                category=PolicyCategory.SAFETY,
                level=PolicyLevel.SERVER,
                action=PolicyAction.ASK,
                tool_patterns=["write_file", "save_file", "create_file"],
                priority=9,
            ),
            PolicyRule(
                rule_id="safety_sensitive_reads",
                name="Review Sensitive File Reads",
                description="Block reading sensitive system files",
                category=PolicyCategory.SECURITY,
                level=PolicyLevel.SERVER,
                action=PolicyAction.BLOCK,
                tool_patterns=["read_file", "cat", "head", "tail"],
                file_patterns=[
                    "/etc/passwd", "/etc/shadow", "/etc/hosts",
                    "/etc/ssl/", "/etc/ssh/", "/etc/sudoers",
                    "/root/", "/var/log/", "/proc/", "/sys/",
                    ".env", ".aws/", ".ssh/", ".git/config",
                    "credentials", "secrets", "tokens",
                ],
                priority=10,
            ),
            PolicyRule(
                rule_id="cost_budget",
                name="Session Cost Budget",
                description="Cap total cost per session at $5.00",
                category=PolicyCategory.COST,
                level=PolicyLevel.SESSION,
                action=PolicyAction.BLOCK,
                max_cost_per_session=5.0,
                require_approval_above_cost=3.0,
                priority=5,
            ),
            PolicyRule(
                rule_id="cost_token_limit",
                name="Per-Call Token Limit",
                description="Limit tokens per API call to 100K",
                category=PolicyCategory.COST,
                level=PolicyLevel.SERVER,
                action=PolicyAction.THROTTLE,
                max_tokens_per_call=100000,
                priority=4,
            ),
            PolicyRule(
                rule_id="resource_tool_calls",
                name="Session Tool Call Limit",
                description="Limit total tool calls per session to 50",
                category=PolicyCategory.RESOURCE,
                level=PolicyLevel.SESSION,
                action=PolicyAction.THROTTLE,
                max_tool_calls_per_session=50,
                priority=3,
            ),
        ]
        for rule in defaults:
            self._server_policies[rule.rule_id] = rule

    def add_policy(self, rule: PolicyRule, agent_id: str | None = None,
                   session_id: str | None = None):
        """Add a policy at the appropriate level."""
        if session_id:
            if session_id not in self._session_policies:
                self._session_policies[session_id] = {}
            self._session_policies[session_id][rule.rule_id] = rule
        elif agent_id:
            if agent_id not in self._agent_policies:
                self._agent_policies[agent_id] = {}
            self._agent_policies[agent_id][rule.rule_id] = rule
        else:
            self._server_policies[rule.rule_id] = rule

        self._audit_log.append({
            "action": "policy_added",
            "rule_id": rule.rule_id,
            "level": rule.level.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def remove_policy(self, rule_id: str, agent_id: str | None = None,
                      session_id: str | None = None):
        """Remove a policy."""
        if session_id and session_id in self._session_policies:
            self._session_policies[session_id].pop(rule_id, None)
        elif agent_id and agent_id in self._agent_policies:
            self._agent_policies[agent_id].pop(rule_id, None)
        else:
            self._server_policies.pop(rule_id, None)

    def evaluate(self, context: dict, agent_id: str | None = None,
                 session_id: str | None = None) -> tuple[PolicyAction, str, list[PolicyRule]]:
        """Evaluate all applicable policies against a context."""
        triggered = []

        # Collect rules from all three levels
        all_rules: list[PolicyRule] = []

        # Server-level
        all_rules.extend(self._server_policies.values())

        # Agent-level
        if agent_id and agent_id in self._agent_policies:
            all_rules.extend(self._agent_policies[agent_id].values())

        # Session-level
        if session_id and session_id in self._session_policies:
            all_rules.extend(self._session_policies[session_id].values())

        # Sort by priority (higher = more important)
        all_rules.sort(key=lambda r: r.priority, reverse=True)

        # Evaluate each rule
        most_restrictive = PolicyAction.ALLOW
        reasons = []

        for rule in all_rules:
            action, reason = rule.evaluate(context)
            if action != PolicyAction.ALLOW:
                triggered.append(rule)
                reasons.append(f"[{rule.name}] {reason}")

                # Most restrictive wins
                action_order = {
                    PolicyAction.BLOCK: 4,
                    PolicyAction.ASK: 3,
                    PolicyAction.THROTTLE: 2,
                    PolicyAction.LOG: 1,
                    PolicyAction.ALLOW: 0,
                }
                if action_order.get(action, 0) > action_order.get(most_restrictive, 0):
                    most_restrictive = action

        return most_restrictive, "; ".join(reasons) if reasons else "All policies passed", triggered

    def create_approval(self, rule_id: str, agent_id: str, session_id: str,
                        description: str, context: dict) -> ApprovalRequest:
        """Create a pending approval request."""
        import uuid
        request_id = str(uuid.uuid4())[:8]
        approval = ApprovalRequest(
            request_id=request_id,
            rule_id=rule_id,
            agent_id=agent_id,
            session_id=session_id,
            action_description=description,
            context=context,
        )
        self._pending_approvals[request_id] = approval
        self._audit_log.append({
            "action": "approval_requested",
            "request_id": request_id,
            "rule_id": rule_id,
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return approval

    def resolve_approval(self, request_id: str, approved: bool) -> ApprovalRequest | None:
        """Resolve a pending approval."""
        approval = self._pending_approvals.pop(request_id, None)
        if approval:
            if approved:
                approval.approve()
            else:
                approval.deny()
            self._approval_history.append(approval)
            self._audit_log.append({
                "action": "approval_resolved",
                "request_id": request_id,
                "approved": approved,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return approval

    def get_budget(self, agent_id: str) -> BudgetTracker:
        """Get or create a budget tracker for an agent."""
        if agent_id not in self._budgets:
            self._budgets[agent_id] = BudgetTracker(
                agent_id=agent_id,
                budget_limit=5.0,
                warning_thresholds=[3.0],
            )
        return self._budgets[agent_id]

    def get_pending_approvals(self, agent_id: str | None = None) -> list[dict]:
        """Get all pending approvals, optionally filtered by agent."""
        approvals = list(self._pending_approvals.values())
        if agent_id:
            approvals = [a for a in approvals if a.agent_id == agent_id]
        return [a.to_dict() for a in approvals]

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]

    def get_stats(self) -> dict:
        """Get governance statistics."""
        return {
            "total_server_policies": len(self._server_policies),
            "total_agent_policies": sum(len(p) for p in self._agent_policies.values()),
            "total_session_policies": sum(len(p) for p in self._session_policies.values()),
            "pending_approvals": len(self._pending_approvals),
            "total_approvals_processed": len(self._approval_history),
            "active_budgets": len(self._budgets),
            "budgets": {aid: b.get_status() for aid, b in self._budgets.items()},
            "recent_audit": self.get_audit_log(10),
        }


# Global instance
governance_engine = GovernanceEngine()