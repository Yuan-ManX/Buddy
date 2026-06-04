"""Buddy Tool Approval System — safety gate for high-risk operations

Provides a multi-level approval framework for controlling tool execution
based on risk classification, user preferences, and operational context.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable

logger = logging.getLogger("buddy.approval")


class ApprovalLevel(str, Enum):
    """Approval requirement levels for tool execution."""
    ALWAYS_ALLOW = "always_allow"       # Never requires approval
    SESSION_ALLOW = "session_allow"     # Approved once per session
    ASK_ONCE = "ask_once"               # Ask once, remember for session
    ALWAYS_ASK = "always_ask"           # Always require approval
    ALWAYS_DENY = "always_deny"         # Never allow


class RiskLevel(str, Enum):
    """Risk classification for tool operations."""
    SAFE = "safe"               # Read-only, no side effects
    LOW = "low"                 # Minor side effects
    MEDIUM = "medium"           # Potentially destructive
    HIGH = "high"               # Destructive, irreversible
    CRITICAL = "critical"       # System-level, extreme caution


@dataclass
class ApprovalRule:
    """Rule for approving or denying tool execution."""
    tool_name: str
    level: ApprovalLevel = ApprovalLevel.ASK_ONCE
    risk: RiskLevel = RiskLevel.LOW
    description: str = ""


@dataclass
class ApprovalRequest:
    """A request for tool execution approval."""
    tool_name: str
    arguments: dict
    risk: RiskLevel
    reason: str = ""

    @property
    def summary(self) -> str:
        args_preview = ", ".join(
            f"{k}={str(v)[:40]}" for k, v in list(self.arguments.items())[:3]
        )
        return f"{self.tool_name}({args_preview}) [risk: {self.risk.value}]"


class ApprovalEngine:
    """Manages tool execution approval with configurable rules."""

    # Default risk classification for tool categories
    DEFAULT_RISK_MAP: dict[str, RiskLevel] = {
        "read_file": RiskLevel.SAFE,
        "get_datetime": RiskLevel.SAFE,
        "calculate": RiskLevel.SAFE,
        "summarize_text": RiskLevel.SAFE,
        "web_search": RiskLevel.SAFE,
        "write_file": RiskLevel.MEDIUM,
        "execute_python": RiskLevel.HIGH,
        "execute_shell": RiskLevel.CRITICAL,
        "delete_file": RiskLevel.HIGH,
        "install_package": RiskLevel.HIGH,
        "git_push": RiskLevel.CRITICAL,
        "git_reset": RiskLevel.CRITICAL,
        "send_email": RiskLevel.MEDIUM,
        "http_request": RiskLevel.MEDIUM,
    }

    # Dangerous command patterns for shell execution
    DANGEROUS_PATTERNS: list[str] = [
        r"\brm\s+-rf\b",
        r"\brm\s+-r\b",
        r"\bmv\s+.*\s+/",
        r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+push\s+--force\b",
        r"\bdd\s+if=",
        r"\bmkfs\.",
        r"\bchmod\s+777\b",
        r"\bchown\s+-R\b",
        r"\b>.*/dev/",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bkill\s+-9\b",
        r"\bdocker\s+rm\b",
        r"\bdocker\s+system\s+prune\b",
        r"\bcurl.*\|\s*(ba)?sh\b",
        r"\bwget.*\|\s*(ba)?sh\b",
    ]

    def __init__(self):
        self._rules: dict[str, ApprovalRule] = {}
        self._session_approvals: dict[str, bool] = {}
        self._approval_callback: Callable[[ApprovalRequest], Awaitable[bool]] | None = None
        self._denied_tools: set[str] = set()

    def set_approval_callback(self, callback: Callable[[ApprovalRequest], Awaitable[bool]]):
        """Set callback for interactive approval requests."""
        self._approval_callback = callback

    def add_rule(self, rule: ApprovalRule):
        """Add or update an approval rule."""
        self._rules[rule.tool_name] = rule
        logger.info(f"Approval rule set: {rule.tool_name} -> {rule.level.value}")

    def remove_rule(self, tool_name: str):
        """Remove an approval rule."""
        self._rules.pop(tool_name, None)

    def get_risk(self, tool_name: str) -> RiskLevel:
        """Get risk level for a tool."""
        rule = self._rules.get(tool_name)
        if rule:
            return rule.risk
        return self.DEFAULT_RISK_MAP.get(tool_name, RiskLevel.LOW)

    def get_level(self, tool_name: str) -> ApprovalLevel:
        """Get approval level for a tool."""
        rule = self._rules.get(tool_name)
        if rule:
            return rule.level

        risk = self.get_risk(tool_name)
        risk_to_level = {
            RiskLevel.SAFE: ApprovalLevel.ALWAYS_ALLOW,
            RiskLevel.LOW: ApprovalLevel.ALWAYS_ALLOW,
            RiskLevel.MEDIUM: ApprovalLevel.ASK_ONCE,
            RiskLevel.HIGH: ApprovalLevel.ALWAYS_ASK,
            RiskLevel.CRITICAL: ApprovalLevel.ALWAYS_ASK,
        }
        return risk_to_level.get(risk, ApprovalLevel.ASK_ONCE)

    def is_dangerous_command(self, command: str) -> bool:
        """Check if a shell command matches dangerous patterns."""
        import re
        cmd_lower = command.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_lower):
                return True
        return False

    async def check(self, tool_name: str, arguments: dict) -> bool:
        """Check if a tool execution should be allowed."""
        # Check if permanently denied
        if tool_name in self._denied_tools:
            logger.warning(f"Tool {tool_name} is permanently denied")
            return False

        level = self.get_level(tool_name)
        risk = self.get_risk(tool_name)

        # Always allow
        if level == ApprovalLevel.ALWAYS_ALLOW:
            return True

        # Always deny
        if level == ApprovalLevel.ALWAYS_DENY:
            logger.warning(f"Tool {tool_name} is always denied")
            return False

        # Session-level approval
        if level == ApprovalLevel.SESSION_ALLOW:
            if tool_name in self._session_approvals:
                return self._session_approvals[tool_name]
            return True

        # Ask once per session
        if level == ApprovalLevel.ASK_ONCE:
            if tool_name in self._session_approvals:
                return self._session_approvals[tool_name]

        # Extra check for shell commands
        if tool_name in ("execute_shell",) and "command" in arguments:
            if self.is_dangerous_command(arguments["command"]):
                risk = RiskLevel.CRITICAL

        # Build approval request
        request = ApprovalRequest(
            tool_name=tool_name,
            arguments=arguments,
            risk=risk,
            reason=f"Tool {tool_name} requires approval (risk: {risk.value})",
        )

        # Use callback if available, otherwise auto-approve non-critical
        if self._approval_callback:
            approved = await self._approval_callback(request)
        else:
            approved = risk in (RiskLevel.SAFE, RiskLevel.LOW)

        # Cache session-level result
        if level in (ApprovalLevel.SESSION_ALLOW, ApprovalLevel.ASK_ONCE):
            self._session_approvals[tool_name] = approved

        if not approved:
            logger.info(f"Tool execution denied: {tool_name} (risk: {risk.value})")

        return approved

    def deny_permanently(self, tool_name: str):
        """Permanently deny a tool."""
        self._denied_tools.add(tool_name)

    def allow_permanently(self, tool_name: str):
        """Remove permanent denial for a tool."""
        self._denied_tools.discard(tool_name)

    def clear_session(self):
        """Clear all session-level approvals."""
        self._session_approvals.clear()

    def get_rules(self) -> list[dict]:
        """Get all approval rules."""
        return [
            {
                "tool_name": r.tool_name,
                "level": r.level.value,
                "risk": r.risk.value,
                "description": r.description,
            }
            for r in self._rules.values()
        ]


approval_engine = ApprovalEngine()