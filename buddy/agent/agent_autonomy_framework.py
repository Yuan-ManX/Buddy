"""
Agent Autonomy Framework - Comprehensive autonomy levels with guardrails.

Provides graduated autonomy capabilities:
- Five autonomy levels from supervised to fully autonomous
- Configurable guardrails and safety boundaries
- Approval workflows with escalation chains
- Trust scoring and behavioral reputation
- Action audit trails and decision logging
- Dynamic autonomy adjustment based on performance
- Risk assessment and mitigation strategies
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.autonomy_framework")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class AutonomyLevel(str, Enum):
    """Autonomy levels from fully supervised to fully autonomous."""
    SUPERVISED = "supervised"
    ASSISTED = "assisted"
    SEMI_AUTONOMOUS = "semi_autonomous"
    AUTONOMOUS = "autonomous"
    FULLY_AUTONOMOUS = "fully_autonomous"


class ActionCategory(str, Enum):
    """Categories of actions an agent can perform."""
    READ = "read"
    ANALYZE = "analyze"
    SUGGEST = "suggest"
    EXECUTE_SAFE = "execute_safe"
    EXECUTE_MODIFY = "execute_modify"
    EXECUTE_DESTRUCTIVE = "execute_destructive"
    EXTERNAL_API = "external_api"
    DEPLOY = "deploy"
    FINANCIAL = "financial"
    SYSTEM = "system"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"
    ESCALATED = "escalated"


class RiskLevel(str, Enum):
    """Risk level of an action."""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GuardrailType(str, Enum):
    """Type of guardrail constraint."""
    HARD_BLOCK = "hard_block"
    SOFT_WARNING = "soft_warning"
    APPROVAL_REQUIRED = "approval_required"
    RATE_LIMIT = "rate_limit"
    SCOPE_LIMIT = "scope_limit"
    TIME_WINDOW = "time_window"
    BUDGET_LIMIT = "budget_limit"


class EscalationReason(str, Enum):
    """Reason for escalating an approval."""
    TIMEOUT = "timeout"
    HIGH_RISK = "high_risk"
    POLICY_VIOLATION = "policy_violation"
    UNCERTAINTY = "uncertainty"
    MANUAL_REQUEST = "manual_request"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class AutonomyPolicy:
    """Policy defining autonomy boundaries for an agent."""
    policy_id: str
    agent_id: str
    level: AutonomyLevel
    allowed_categories: list[ActionCategory]
    blocked_categories: list[ActionCategory]
    require_approval_categories: list[ActionCategory]
    max_actions_per_hour: int = 100
    max_cost_per_action: float = 1.0
    max_daily_cost: float = 50.0
    allowed_time_windows: list[tuple[int, int]] = field(default_factory=list)
    escalation_chain: list[str] = field(default_factory=list)
    auto_approve_threshold: RiskLevel = RiskLevel.LOW
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "agent_id": self.agent_id,
            "level": self.level.value,
            "allowed_categories": [c.value for c in self.allowed_categories],
            "blocked_categories": [c.value for c in self.blocked_categories],
            "require_approval_categories": [c.value for c in self.require_approval_categories],
            "max_actions_per_hour": self.max_actions_per_hour,
            "max_cost_per_action": self.max_cost_per_action,
            "max_daily_cost": self.max_daily_cost,
            "auto_approve_threshold": self.auto_approve_threshold.value,
        }


@dataclass
class Guardrail:
    """A single guardrail constraint."""
    guardrail_id: str
    guardrail_type: GuardrailType
    description: str
    condition: str
    action_on_violation: str
    enabled: bool = True
    violation_count: int = 0
    max_violations: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "guardrail_id": self.guardrail_id,
            "guardrail_type": self.guardrail_type.value,
            "description": self.description,
            "condition": self.condition,
            "enabled": self.enabled,
            "violation_count": self.violation_count,
        }


@dataclass
class ApprovalRequest:
    """An approval request for an action."""
    request_id: str
    agent_id: str
    action_category: ActionCategory
    action_description: str
    risk_level: RiskLevel
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str = ""
    approved_by: str = ""
    denial_reason: str = ""
    escalation_level: int = 0
    max_escalation: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=30)
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "action_category": self.action_category.value,
            "action_description": self.action_description,
            "risk_level": self.risk_level.value,
            "status": self.status.value,
            "approved_by": self.approved_by,
            "denial_reason": self.denial_reason,
            "escalation_level": self.escalation_level,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "expires_at": self.expires_at.isoformat(),
        }


@dataclass
class ActionAuditEntry:
    """Audit trail entry for an agent action."""
    entry_id: str
    agent_id: str
    action_category: ActionCategory
    action_description: str
    risk_level: RiskLevel
    autonomy_level: AutonomyLevel
    approved: bool
    approval_id: str = ""
    result: str = ""
    cost: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "agent_id": self.agent_id,
            "action_category": self.action_category.value,
            "action_description": self.action_description,
            "risk_level": self.risk_level.value,
            "autonomy_level": self.autonomy_level.value,
            "approved": self.approved,
            "result": self.result[:200],
            "cost": self.cost,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TrustScore:
    """Trust score for an agent."""
    agent_id: str
    overall_score: float
    reliability: float
    safety: float
    accuracy: float
    consistency: float
    total_actions: int
    successful_actions: int
    policy_violations: int
    approval_rate: float
    trend: str
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "overall_score": self.overall_score,
            "reliability": self.reliability,
            "safety": self.safety,
            "accuracy": self.accuracy,
            "consistency": self.consistency,
            "total_actions": self.total_actions,
            "successful_actions": self.successful_actions,
            "policy_violations": self.policy_violations,
            "approval_rate": self.approval_rate,
            "trend": self.trend,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class AutonomyStats:
    """Statistics for the autonomy framework."""
    total_actions: int = 0
    total_approved: int = 0
    total_denied: int = 0
    total_auto_approved: int = 0
    total_escalated: int = 0
    total_violations: int = 0
    approvals_by_level: dict[str, int] = field(default_factory=dict)
    actions_by_category: dict[str, int] = field(default_factory=dict)
    avg_trust_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_actions": self.total_actions,
            "total_approved": self.total_approved,
            "total_denied": self.total_denied,
            "total_auto_approved": self.total_auto_approved,
            "total_escalated": self.total_escalated,
            "total_violations": self.total_violations,
            "approval_rate": self.total_approved / max(1, self.total_actions),
            "approvals_by_level": self.approvals_by_level,
            "actions_by_category": self.actions_by_category,
            "avg_trust_score": self.avg_trust_score,
        }


# ═══════════════════════════════════════════════════════════
# Autonomy Framework
# ═══════════════════════════════════════════════════════════

class AutonomyFramework:
    """
    Comprehensive autonomy management with graduated levels and guardrails.
    
    Features:
    - Five graduated autonomy levels with configurable boundaries
    - Multi-layer guardrail system with hard/soft constraints
    - Approval workflows with escalation chains
    - Trust scoring with behavioral reputation
    - Complete action audit trails
    - Dynamic autonomy adjustment based on performance
    - Risk assessment and mitigation
    """

    def __init__(self, config: AutonomyConfig | None = None):
        self.config = config or AutonomyConfig()
        self._policies: dict[str, AutonomyPolicy] = {}
        self._guardrails: dict[str, Guardrail] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._audit_trail: list[ActionAuditEntry] = []
        self._trust_scores: dict[str, TrustScore] = {}
        self._action_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._stats = AutonomyStats()
        self._init_default_guardrails()

    def _init_default_guardrails(self) -> None:
        """Initialize default guardrails."""
        defaults = [
            Guardrail(
                guardrail_id="gr-destructive-block",
                guardrail_type=GuardrailType.HARD_BLOCK,
                description="Block destructive actions without explicit approval",
                condition="action_category in [EXECUTE_DESTRUCTIVE, DEPLOY, FINANCIAL]",
                action_on_violation="Block action and require approval",
            ),
            Guardrail(
                guardrail_id="gr-rate-limit",
                guardrail_type=GuardrailType.RATE_LIMIT,
                description="Rate limit actions to prevent abuse",
                condition="actions_per_hour > max_actions_per_hour",
                action_on_violation="Throttle actions for remainder of hour",
            ),
            Guardrail(
                guardrail_id="gr-cost-limit",
                guardrail_type=GuardrailType.BUDGET_LIMIT,
                description="Limit cost per action and daily total",
                condition="cost > max_cost_per_action or daily_cost > max_daily_cost",
                action_on_violation="Block action and notify",
            ),
            Guardrail(
                guardrail_id="gr-scope-limit",
                guardrail_type=GuardrailType.SCOPE_LIMIT,
                description="Restrict actions to allowed categories",
                condition="action_category not in allowed_categories",
                action_on_violation="Block action",
            ),
            Guardrail(
                guardrail_id="gr-system-protection",
                guardrail_type=GuardrailType.HARD_BLOCK,
                description="Protect system-level operations",
                condition="action_category == SYSTEM and autonomy_level < AUTONOMOUS",
                action_on_violation="Block and require manual approval",
            ),
        ]
        for gr in defaults:
            self._guardrails[gr.guardrail_id] = gr

    # ── Policy Management ──

    def create_policy(
        self,
        agent_id: str,
        level: AutonomyLevel = AutonomyLevel.ASSISTED,
        allowed_categories: list[ActionCategory] | None = None,
        blocked_categories: list[ActionCategory] | None = None,
        require_approval_categories: list[ActionCategory] | None = None,
    ) -> AutonomyPolicy:
        """Create an autonomy policy for an agent."""
        # Default category assignments based on autonomy level
        default_categories = self._get_default_categories(level)

        policy = AutonomyPolicy(
            policy_id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            level=level,
            allowed_categories=allowed_categories or default_categories["allowed"],
            blocked_categories=blocked_categories or default_categories["blocked"],
            require_approval_categories=require_approval_categories or default_categories["approval"],
        )

        self._policies[agent_id] = policy
        logger.info(
            "Created autonomy policy for agent %s: level=%s, allowed=%d, blocked=%d",
            agent_id, level.value, len(policy.allowed_categories),
            len(policy.blocked_categories),
        )
        return policy

    def update_policy_level(self, agent_id: str, new_level: AutonomyLevel) -> AutonomyPolicy | None:
        """Update an agent's autonomy level."""
        policy = self._policies.get(agent_id)
        if not policy:
            return None

        old_level = policy.level
        policy.level = new_level
        policy.updated_at = datetime.now(timezone.utc)

        logger.info(
            "Agent %s autonomy level changed: %s -> %s",
            agent_id, old_level.value, new_level.value,
        )
        return policy

    def _get_default_categories(self, level: AutonomyLevel) -> dict[str, list[ActionCategory]]:
        """Get default category assignments for an autonomy level."""
        defaults = {
            AutonomyLevel.SUPERVISED: {
                "allowed": [ActionCategory.READ, ActionCategory.ANALYZE, ActionCategory.SUGGEST],
                "blocked": [ActionCategory.EXECUTE_DESTRUCTIVE, ActionCategory.DEPLOY, ActionCategory.FINANCIAL, ActionCategory.SYSTEM],
                "approval": [ActionCategory.EXECUTE_SAFE, ActionCategory.EXECUTE_MODIFY, ActionCategory.EXTERNAL_API],
            },
            AutonomyLevel.ASSISTED: {
                "allowed": [ActionCategory.READ, ActionCategory.ANALYZE, ActionCategory.SUGGEST, ActionCategory.EXECUTE_SAFE],
                "blocked": [ActionCategory.EXECUTE_DESTRUCTIVE, ActionCategory.DEPLOY, ActionCategory.FINANCIAL],
                "approval": [ActionCategory.EXECUTE_MODIFY, ActionCategory.EXTERNAL_API, ActionCategory.SYSTEM],
            },
            AutonomyLevel.SEMI_AUTONOMOUS: {
                "allowed": [ActionCategory.READ, ActionCategory.ANALYZE, ActionCategory.SUGGEST, ActionCategory.EXECUTE_SAFE, ActionCategory.EXECUTE_MODIFY, ActionCategory.EXTERNAL_API],
                "blocked": [ActionCategory.EXECUTE_DESTRUCTIVE, ActionCategory.DEPLOY],
                "approval": [ActionCategory.FINANCIAL, ActionCategory.SYSTEM],
            },
            AutonomyLevel.AUTONOMOUS: {
                "allowed": [ActionCategory.READ, ActionCategory.ANALYZE, ActionCategory.SUGGEST, ActionCategory.EXECUTE_SAFE, ActionCategory.EXECUTE_MODIFY, ActionCategory.EXTERNAL_API, ActionCategory.DEPLOY, ActionCategory.SYSTEM],
                "blocked": [],
                "approval": [ActionCategory.EXECUTE_DESTRUCTIVE, ActionCategory.FINANCIAL],
            },
            AutonomyLevel.FULLY_AUTONOMOUS: {
                "allowed": list(ActionCategory),
                "blocked": [],
                "approval": [ActionCategory.FINANCIAL],
            },
        }
        return defaults.get(level, defaults[AutonomyLevel.ASSISTED])

    # ── Action Authorization ──

    def authorize_action(
        self,
        agent_id: str,
        action_category: ActionCategory,
        action_description: str,
        estimated_cost: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str, str]:
        """
        Authorize an action based on autonomy policy and guardrails.
        
        Returns:
            Tuple of (authorized, status, reason)
        """
        policy = self._policies.get(agent_id)
        if not policy:
            policy = self.create_policy(agent_id)

        # Check if action is blocked
        if action_category in policy.blocked_categories:
            return False, "blocked", f"Action category {action_category.value} is blocked"

        # Check guardrails
        for gr in self._guardrails.values():
            if not gr.enabled:
                continue
            if gr.guardrail_type == GuardrailType.HARD_BLOCK:
                if action_category in [ActionCategory.EXECUTE_DESTRUCTIVE, ActionCategory.DEPLOY]:
                    if policy.level in [AutonomyLevel.SUPERVISED, AutonomyLevel.ASSISTED]:
                        gr.violation_count += 1
                        return False, "blocked", f"Guardrail blocked: {gr.description}"

        # Assess risk
        risk_level = self._assess_risk(action_category, estimated_cost, policy.level)

        # Check if action requires approval
        if action_category in policy.require_approval_categories:
            # Auto-approve if risk is below threshold
            if self._risk_order(risk_level) <= self._risk_order(policy.auto_approve_threshold):
                return True, "auto_approved", f"Auto-approved: risk {risk_level.value} below threshold"

            # Create approval request
            request = ApprovalRequest(
                request_id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
                action_category=action_category,
                action_description=action_description,
                risk_level=risk_level,
                metadata=metadata or {},
            )
            self._approvals[request.request_id] = request
            return False, "pending_approval", request.request_id

        # Check rate limits
        hour_key = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
        current_count = self._action_counts[agent_id].get(hour_key, 0)
        if current_count >= policy.max_actions_per_hour:
            return False, "rate_limited", "Hourly action limit reached"

        # Check cost limits
        if estimated_cost > policy.max_cost_per_action:
            return False, "cost_exceeded", f"Cost {estimated_cost} exceeds limit {policy.max_cost_per_action}"

        # Allowed
        self._action_counts[agent_id][hour_key] = current_count + 1
        return True, "authorized", "Action authorized"

    def _assess_risk(
        self,
        action_category: ActionCategory,
        estimated_cost: float,
        autonomy_level: AutonomyLevel,
    ) -> RiskLevel:
        """Assess the risk level of an action."""
        category_risk = {
            ActionCategory.READ: RiskLevel.NEGLIGIBLE,
            ActionCategory.ANALYZE: RiskLevel.NEGLIGIBLE,
            ActionCategory.SUGGEST: RiskLevel.NEGLIGIBLE,
            ActionCategory.EXECUTE_SAFE: RiskLevel.LOW,
            ActionCategory.EXECUTE_MODIFY: RiskLevel.MEDIUM,
            ActionCategory.EXTERNAL_API: RiskLevel.MEDIUM,
            ActionCategory.EXECUTE_DESTRUCTIVE: RiskLevel.HIGH,
            ActionCategory.DEPLOY: RiskLevel.HIGH,
            ActionCategory.FINANCIAL: RiskLevel.CRITICAL,
            ActionCategory.SYSTEM: RiskLevel.HIGH,
        }

        risk = category_risk.get(action_category, RiskLevel.MEDIUM)

        # Adjust for cost
        if estimated_cost > 10.0:
            risk = self._increase_risk(risk, 2)
        elif estimated_cost > 1.0:
            risk = self._increase_risk(risk, 1)

        # Adjust for autonomy level
        if autonomy_level in [AutonomyLevel.SUPERVISED, AutonomyLevel.ASSISTED]:
            risk = self._increase_risk(risk, 1)

        return risk

    def _risk_order(self, risk: RiskLevel) -> int:
        """Get numeric order of risk level."""
        order = {
            RiskLevel.NEGLIGIBLE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        return order.get(risk, 2)

    def _increase_risk(self, risk: RiskLevel, steps: int) -> RiskLevel:
        """Increase risk level by steps."""
        levels = [
            RiskLevel.NEGLIGIBLE,
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        current = levels.index(risk)
        new_index = min(len(levels) - 1, current + steps)
        return levels[new_index]

    # ── Approval Management ──

    def approve_action(self, request_id: str, approved_by: str = "system") -> ApprovalRequest | None:
        """Approve a pending action."""
        request = self._approvals.get(request_id)
        if not request:
            return None

        if request.status != ApprovalStatus.PENDING:
            return request

        request.status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.resolved_at = datetime.now(timezone.utc)

        self._stats.total_approved += 1
        logger.info("Approval %s approved by %s", request_id, approved_by)
        return request

    def deny_action(self, request_id: str, reason: str = "") -> ApprovalRequest | None:
        """Deny a pending action."""
        request = self._approvals.get(request_id)
        if not request:
            return None

        request.status = ApprovalStatus.DENIED
        request.denial_reason = reason
        request.resolved_at = datetime.now(timezone.utc)

        self._stats.total_denied += 1
        logger.info("Approval %s denied: %s", request_id, reason)
        return request

    def escalate_approval(self, request_id: str) -> ApprovalRequest | None:
        """Escalate an approval request."""
        request = self._approvals.get(request_id)
        if not request:
            return None

        if request.escalation_level >= request.max_escalation:
            request.status = ApprovalStatus.ESCALATED
            return request

        request.escalation_level += 1
        self._stats.total_escalated += 1
        logger.info("Approval %s escalated to level %d", request_id, request.escalation_level)
        return request

    def get_pending_approvals(self, agent_id: str = "") -> list[ApprovalRequest]:
        """Get pending approval requests."""
        pending = [
            req for req in self._approvals.values()
            if req.status == ApprovalStatus.PENDING
        ]
        if agent_id:
            pending = [req for req in pending if req.agent_id == agent_id]
        return pending

    # ── Audit Trail ──

    def record_action(
        self,
        agent_id: str,
        action_category: ActionCategory,
        action_description: str,
        risk_level: RiskLevel,
        approved: bool,
        approval_id: str = "",
        result: str = "",
        cost: float = 0.0,
        duration_ms: float = 0.0,
        success: bool = True,
        error: str = "",
    ) -> ActionAuditEntry:
        """Record an action in the audit trail."""
        policy = self._policies.get(agent_id)
        autonomy_level = policy.level if policy else AutonomyLevel.ASSISTED

        entry = ActionAuditEntry(
            entry_id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            action_category=action_category,
            action_description=action_description,
            risk_level=risk_level,
            autonomy_level=autonomy_level,
            approved=approved,
            approval_id=approval_id,
            result=result,
            cost=cost,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )

        self._audit_trail.append(entry)
        self._update_action_stats(entry)

        # Trim audit trail if too large
        if len(self._audit_trail) > self.config.max_audit_entries:
            self._audit_trail = self._audit_trail[-self.config.max_audit_entries:]

        return entry

    def get_audit_trail(
        self,
        agent_id: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[ActionAuditEntry]:
        """Get audit trail entries."""
        entries = self._audit_trail
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        return entries[offset:offset + limit]

    # ── Trust Scoring ──

    def calculate_trust_score(self, agent_id: str) -> TrustScore:
        """Calculate trust score for an agent."""
        agent_entries = [e for e in self._audit_trail if e.agent_id == agent_id]
        total = len(agent_entries)

        if total == 0:
            score = TrustScore(
                agent_id=agent_id,
                overall_score=0.5,
                reliability=0.5,
                safety=0.5,
                accuracy=0.5,
                consistency=0.5,
                total_actions=0,
                successful_actions=0,
                policy_violations=0,
                approval_rate=0.0,
                trend="stable",
            )
            self._trust_scores[agent_id] = score
            return score

        successful = sum(1 for e in agent_entries if e.success)
        violations = sum(
            1 for e in agent_entries
            if e.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] and not e.approved
        )

        reliability = successful / total
        safety = 1.0 - (violations / max(1, total))
        accuracy = successful / max(1, total)
        consistency = self._calculate_consistency(agent_entries)

        approval_count = sum(1 for e in agent_entries if e.approved)
        approval_rate = approval_count / total

        overall = (reliability * 0.3 + safety * 0.3 + accuracy * 0.2 + consistency * 0.2)

        # Determine trend
        recent = agent_entries[-20:]
        if recent:
            recent_success = sum(1 for e in recent if e.success) / len(recent)
            if recent_success > reliability + 0.1:
                trend = "improving"
            elif recent_success < reliability - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        score = TrustScore(
            agent_id=agent_id,
            overall_score=round(overall, 3),
            reliability=round(reliability, 3),
            safety=round(safety, 3),
            accuracy=round(accuracy, 3),
            consistency=round(consistency, 3),
            total_actions=total,
            successful_actions=successful,
            policy_violations=violations,
            approval_rate=round(approval_rate, 3),
            trend=trend,
        )

        self._trust_scores[agent_id] = score
        return score

    def _calculate_consistency(self, entries: list[ActionAuditEntry]) -> float:
        """Calculate action consistency score."""
        if len(entries) < 3:
            return 0.5

        # Check if success rate is stable across windows
        window_size = max(5, len(entries) // 5)
        success_rates = []
        for i in range(0, len(entries), window_size):
            window = entries[i:i + window_size]
            if window:
                success_rates.append(sum(1 for e in window if e.success) / len(window))

        if len(success_rates) < 2:
            return 0.5

        avg = sum(success_rates) / len(success_rates)
        variance = sum((r - avg) ** 2 for r in success_rates) / len(success_rates)
        return max(0.0, 1.0 - variance)

    def recommend_autonomy_level(self, agent_id: str) -> AutonomyLevel:
        """Recommend autonomy level based on trust score."""
        score = self._trust_scores.get(agent_id)
        if not score:
            score = self.calculate_trust_score(agent_id)

        if score.overall_score >= 0.95:
            return AutonomyLevel.FULLY_AUTONOMOUS
        if score.overall_score >= 0.85:
            return AutonomyLevel.AUTONOMOUS
        if score.overall_score >= 0.7:
            return AutonomyLevel.SEMI_AUTONOMOUS
        if score.overall_score >= 0.5:
            return AutonomyLevel.ASSISTED
        return AutonomyLevel.SUPERVISED

    # ── Guardrail Management ──

    def add_guardrail(self, guardrail: Guardrail) -> None:
        """Add a custom guardrail."""
        self._guardrails[guardrail.guardrail_id] = guardrail

    def remove_guardrail(self, guardrail_id: str) -> bool:
        """Remove a guardrail."""
        if guardrail_id in self._guardrails:
            del self._guardrails[guardrail_id]
            return True
        return False

    def get_guardrails(self) -> list[Guardrail]:
        """Get all guardrails."""
        return list(self._guardrails.values())

    # ── Statistics ──

    def _update_action_stats(self, entry: ActionAuditEntry) -> None:
        """Update autonomy statistics."""
        self._stats.total_actions += 1
        self._stats.actions_by_category[entry.action_category.value] = (
            self._stats.actions_by_category.get(entry.action_category.value, 0) + 1
        )

        if entry.approved:
            self._stats.total_approved += 1
        self._stats.approvals_by_level[entry.autonomy_level.value] = (
            self._stats.approvals_by_level.get(entry.autonomy_level.value, 0) + 1
        )

    def get_stats(self) -> AutonomyStats:
        """Get current autonomy statistics."""
        if self._trust_scores:
            self._stats.avg_trust_score = sum(
                s.overall_score for s in self._trust_scores.values()
            ) / len(self._trust_scores)
        return self._stats

    def get_policy(self, agent_id: str) -> AutonomyPolicy | None:
        """Get autonomy policy for an agent."""
        return self._policies.get(agent_id)

    def get_trust_score(self, agent_id: str) -> TrustScore | None:
        """Get trust score for an agent."""
        return self._trust_scores.get(agent_id)

    def reset(self) -> None:
        """Reset the autonomy framework."""
        self._policies.clear()
        self._approvals.clear()
        self._audit_trail.clear()
        self._trust_scores.clear()
        self._action_counts.clear()
        self._stats = AutonomyStats()
        self._init_default_guardrails()
        logger.info("Autonomy framework reset")


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@dataclass
class AutonomyConfig:
    """Configuration for the autonomy framework."""
    default_level: AutonomyLevel = AutonomyLevel.ASSISTED
    max_audit_entries: int = 10000
    auto_escalation_timeout_minutes: int = 30
    trust_score_decay_days: int = 30
    require_approval_for_high_risk: bool = True
    auto_approve_low_risk: bool = True
    collect_metrics: bool = True


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_autonomy_framework: AutonomyFramework | None = None


def get_autonomy_framework() -> AutonomyFramework:
    """Get or create the singleton autonomy framework."""
    global _autonomy_framework
    if _autonomy_framework is None:
        _autonomy_framework = AutonomyFramework()
    return _autonomy_framework


def reset_autonomy_framework() -> None:
    """Reset the singleton autonomy framework."""
    global _autonomy_framework
    if _autonomy_framework:
        _autonomy_framework.reset()
    _autonomy_framework = None