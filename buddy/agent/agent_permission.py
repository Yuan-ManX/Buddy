"""
Buddy Permission & Approval System.

Provides a comprehensive permission framework for agent tool execution,
ensuring safety and control through configurable policies, approval
workflows, and audit trails.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for tool execution."""
    ALWAYS_ALLOW = "always_allow"
    ALLOW_ONCE = "allow_once"
    ASK_EVERY_TIME = "ask_every_time"
    ALWAYS_DENY = "always_deny"
    REQUIRE_MFA = "require_mfa"


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


class PolicyScope(Enum):
    """Scope of a permission policy."""
    GLOBAL = "global"
    AGENT = "agent"
    WORKSPACE = "workspace"
    SESSION = "session"


@dataclass
class PermissionPolicy:
    """A permission policy defining tool access rules."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    scope: PolicyScope = PolicyScope.GLOBAL
    scope_id: str = ""
    tool_patterns: list[str] = field(default_factory=list)
    permission_level: PermissionLevel = PermissionLevel.ASK_EVERY_TIME
    max_daily_executions: Optional[int] = None
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    require_approval_above_args_size: Optional[int] = None
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class ApprovalRequest:
    """A pending approval request for tool execution."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    agent_id: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    reason: str = ""
    requested_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved_by: str = ""
    expires_at: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionAudit:
    """Audit record for a tool execution."""
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    agent_id: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    success: bool = False
    error: Optional[str] = None
    permission_level: PermissionLevel = PermissionLevel.ASK_EVERY_TIME
    approval_status: Optional[ApprovalStatus] = None
    executed_at: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    session_id: str = ""
    workspace_id: str = ""


class PermissionManager:
    """
    Central permission management system for Buddy agents.

    Enforces tool execution policies, manages approval workflows,
    and maintains comprehensive audit trails.
    """

    def __init__(self):
        self._policies: dict[str, PermissionPolicy] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._audit_log: list[ExecutionAudit] = []
        self._execution_counts: dict[str, dict[str, int]] = {}  # agent_id -> tool_name -> count
        self._yolo_mode: bool = False

    # ── Policy Management ──────────────────────────────────────────

    def create_policy(
        self,
        name: str,
        tool_patterns: list[str],
        permission_level: PermissionLevel,
        scope: PolicyScope = PolicyScope.GLOBAL,
        scope_id: str = "",
        description: str = "",
        **kwargs,
    ) -> PermissionPolicy:
        """Create a new permission policy."""
        policy = PermissionPolicy(
            name=name,
            description=description,
            scope=scope,
            scope_id=scope_id,
            tool_patterns=tool_patterns,
            permission_level=permission_level,
            **kwargs,
        )
        self._policies[policy.policy_id] = policy
        logger.info("Permission policy created: %s (level=%s)", name, permission_level.value)
        return policy

    def update_policy(self, policy_id: str, **kwargs) -> Optional[PermissionPolicy]:
        """Update an existing policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        policy.updated_at = time.time()
        return policy

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a permission policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    def get_policy(self, policy_id: str) -> Optional[PermissionPolicy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def list_policies(
        self,
        scope: Optional[PolicyScope] = None,
        enabled_only: bool = True,
    ) -> list[PermissionPolicy]:
        """List policies with optional filtering."""
        policies = list(self._policies.values())
        if scope:
            policies = [p for p in policies if p.scope == scope]
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        return policies

    # ── Permission Checking ────────────────────────────────────────

    def check_permission(
        self,
        agent_id: str,
        tool_name: str,
        arguments: Optional[dict[str, Any]] = None,
    ) -> tuple[PermissionLevel, Optional[str]]:
        """
        Check if an agent has permission to execute a tool.

        Returns (permission_level, reason_if_denied).
        """
        if self._yolo_mode:
            return PermissionLevel.ALWAYS_ALLOW, "YOLO mode enabled"

        # Find applicable policies
        applicable = self._find_applicable_policies(agent_id, tool_name)

        if not applicable:
            return PermissionLevel.ASK_EVERY_TIME, "No matching policy"

        # Use the most restrictive policy
        policy = applicable[0]

        # Check execution limits
        if policy.max_daily_executions:
            agent_counts = self._execution_counts.get(agent_id, {})
            daily_count = agent_counts.get(tool_name, 0)
            if daily_count >= policy.max_daily_executions:
                return PermissionLevel.ALWAYS_DENY, f"Daily execution limit ({policy.max_daily_executions}) reached"

        # Check time window
        if policy.time_window_start and policy.time_window_end:
            from datetime import datetime
            now = datetime.now().strftime("%H:%M")
            if not (policy.time_window_start <= now <= policy.time_window_end):
                return PermissionLevel.ALWAYS_DENY, f"Outside allowed time window ({policy.time_window_start}-{policy.time_window_end})"

        # Check argument size
        if policy.require_approval_above_args_size and arguments:
            import json
            args_size = len(json.dumps(arguments))
            if args_size > policy.require_approval_above_args_size:
                return PermissionLevel.REQUIRE_MFA, f"Arguments size ({args_size}) exceeds threshold"

        return policy.permission_level, None

    # ── Approval Workflow ──────────────────────────────────────────

    def create_approval_request(
        self,
        agent_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str = "",
        ttl_seconds: float = 300.0,
    ) -> ApprovalRequest:
        """Create a new approval request for tool execution."""
        request = ApprovalRequest(
            agent_id=agent_id,
            tool_name=tool_name,
            arguments=arguments,
            reason=reason,
            expires_at=time.time() + ttl_seconds,
        )
        self._approvals[request.request_id] = request
        logger.info("Approval request created: %s for %s", request.request_id, tool_name)
        return request

    def approve_request(self, request_id: str, approved_by: str = "user") -> Optional[ApprovalRequest]:
        """Approve a pending approval request."""
        request = self._approvals.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        if request.expires_at and time.time() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            return None

        request.status = ApprovalStatus.APPROVED
        request.resolved_at = time.time()
        request.resolved_by = approved_by
        return request

    def deny_request(self, request_id: str, denied_by: str = "user") -> Optional[ApprovalRequest]:
        """Deny a pending approval request."""
        request = self._approvals.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.DENIED
        request.resolved_at = time.time()
        request.resolved_by = denied_by
        return request

    def get_pending_approvals(self, agent_id: Optional[str] = None) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        pending = [
            r for r in self._approvals.values()
            if r.status == ApprovalStatus.PENDING
        ]
        if agent_id:
            pending = [r for r in pending if r.agent_id == agent_id]
        return pending

    def cleanup_expired(self) -> int:
        """Clean up expired approval requests."""
        now = time.time()
        expired = [
            rid for rid, r in self._approvals.items()
            if r.status == ApprovalStatus.PENDING and r.expires_at and r.expires_at < now
        ]
        for rid in expired:
            self._approvals[rid].status = ApprovalStatus.EXPIRED
        return len(expired)

    # ── Audit Logging ──────────────────────────────────────────────

    def record_execution(
        self,
        agent_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        success: bool,
        permission_level: PermissionLevel,
        approval_status: Optional[ApprovalStatus] = None,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
        session_id: str = "",
        workspace_id: str = "",
    ) -> ExecutionAudit:
        """Record a tool execution in the audit log."""
        audit = ExecutionAudit(
            agent_id=agent_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            error=error,
            permission_level=permission_level,
            approval_status=approval_status,
            duration_ms=duration_ms,
            session_id=session_id,
            workspace_id=workspace_id,
        )
        self._audit_log.append(audit)

        # Update execution counts
        if agent_id not in self._execution_counts:
            self._execution_counts[agent_id] = {}
        self._execution_counts[agent_id][tool_name] = (
            self._execution_counts[agent_id].get(tool_name, 0) + 1
        )

        return audit

    def get_audit_log(
        self,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        limit: int = 50,
    ) -> list[ExecutionAudit]:
        """Get filtered audit log entries."""
        entries = list(self._audit_log)
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        if tool_name:
            entries = [e for e in entries if e.tool_name == tool_name]
        return entries[-limit:]

    def clear_audit_log(self) -> None:
        """Clear the audit log."""
        self._audit_log.clear()

    # ── YOLO Mode ──────────────────────────────────────────────────

    def enable_yolo_mode(self) -> None:
        """Enable YOLO mode - bypass all permission checks."""
        self._yolo_mode = True
        logger.warning("YOLO mode enabled - all permission checks bypassed")

    def disable_yolo_mode(self) -> None:
        """Disable YOLO mode."""
        self._yolo_mode = False
        logger.info("YOLO mode disabled")

    # ── Internal Methods ───────────────────────────────────────────

    def _find_applicable_policies(
        self, agent_id: str, tool_name: str
    ) -> list[PermissionPolicy]:
        """Find all policies applicable to a tool execution."""
        import fnmatch

        applicable = []
        for policy in self._policies.values():
            if not policy.enabled:
                continue
            # Check if any pattern matches the tool name
            if any(fnmatch.fnmatch(tool_name, pattern) for pattern in policy.tool_patterns):
                # Check scope
                if policy.scope == PolicyScope.GLOBAL:
                    applicable.append(policy)
                elif policy.scope == PolicyScope.AGENT and policy.scope_id == agent_id:
                    applicable.append(policy)

        # Sort by most restrictive first
        level_order = {
            PermissionLevel.ALWAYS_DENY: 0,
            PermissionLevel.REQUIRE_MFA: 1,
            PermissionLevel.ASK_EVERY_TIME: 2,
            PermissionLevel.ALLOW_ONCE: 3,
            PermissionLevel.ALWAYS_ALLOW: 4,
        }
        applicable.sort(key=lambda p: level_order.get(p.permission_level, 2))
        return applicable

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get permission system statistics."""
        return {
            "total_policies": len(self._policies),
            "policies_by_scope": {
                scope.value: len(self.list_policies(scope=scope))
                for scope in PolicyScope
            },
            "pending_approvals": len(self.get_pending_approvals()),
            "total_audit_entries": len(self._audit_log),
            "yolo_mode": self._yolo_mode,
            "execution_counts": {
                agent_id: dict(counts)
                for agent_id, counts in self._execution_counts.items()
            },
        }


# Global permission manager instance
permission_manager = PermissionManager()