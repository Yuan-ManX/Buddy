"""Buddy Guardrails — Agent output safety filtering and content moderation

Provides a multi-layered safety system that filters agent outputs before
they reach users. Includes content classification, toxicity detection,
PII redaction, and configurable policy enforcement.
"""
from __future__ import annotations
import re
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.guardrails")


class ContentCategory(str, Enum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    WARNING = "warning"
    BLOCKED = "blocked"


class ViolationType(str, Enum):
    TOXICITY = "toxicity"
    PII = "pii"
    HATE_SPEECH = "hate_speech"
    SELF_HARM = "self_harm"
    VIOLENCE = "violence"
    MISINFORMATION = "misinformation"
    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    CUSTOM = "custom"


@dataclass
class GuardrailResult:
    """Result of a guardrail check on agent output."""
    passed: bool = True
    category: ContentCategory = ContentCategory.SAFE
    violations: list[dict] = field(default_factory=list)
    sanitized_content: str = ""
    original_content: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "category": self.category.value,
            "violations": [
                {
                    "type": v.get("type", ""),
                    "severity": v.get("severity", "low"),
                    "detail": v.get("detail", ""),
                    "span": v.get("span", ""),
                }
                for v in self.violations
            ],
            "confidence": self.confidence,
        }


class GuardrailsEngine:
    """Multi-layered safety filtering engine for agent outputs.

    Usage:
        guard = GuardrailsEngine()
        result = guard.check(agent_output)
        if not result.passed:
            safe_content = result.sanitized_content
    """

    # PII patterns for redaction
    PII_PATTERNS: list[tuple[str, str, str]] = [
        # Email addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', 'email'),
        # Phone numbers (various formats)
        (r'\b(\+\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', 'phone'),
        # SSN-like patterns
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', 'ssn'),
        # Credit card patterns
        (r'\b(?:\d{4}[- ]?){3}\d{4}\b', '[CREDIT_CARD]', 'credit_card'),
        # IP addresses
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDRESS]', 'ip'),
        # API keys (common patterns)
        (r'\b(sk-[a-zA-Z0-9]{20,})\b', '[API_KEY]', 'api_key'),
        (r'\b([a-zA-Z0-9]{32,})\b', '[TOKEN]', 'token'),
    ]

    # Toxic pattern keywords
    TOXICITY_PATTERNS: list[str] = [
        # Hate speech indicators
        r'\b(hate|kill|murder|terrorist|bomb|attack)\b',
        # Self-harm indicators
        r'\b(suicide|self-harm|cut myself|end my life)\b',
        # Violence indicators
        r'\b(torture|massacre|genocide|slaughter)\b',
    ]

    # Prompt injection patterns
    INJECTION_PATTERNS: list[str] = [
        r'(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions?|prompts?|messages?)',
        r'(you\s+are\s+now|you\s+must|you\s+will)\s+(act\s+as|pretend|roleplay)',
        r'(system\s*(prompt|message|instruction))',
        r'\[SYSTEM\]|\[INST\]|<\|system\|>|<\|im_start\|>',
        r'DAN\s+mode|developer\s+mode|jailbreak',
    ]

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.enable_pii_redaction = self.config.get("enable_pii_redaction", True)
        self.enable_toxicity_check = self.config.get("enable_toxicity_check", True)
        self.enable_injection_check = self.config.get("enable_injection_check", True)
        self.max_output_length = self.config.get("max_output_length", 50000)
        self._stats: dict[str, int] = {"passed": 0, "blocked": 0, "redacted": 0}

    def check(self, content: str, context: dict | None = None) -> GuardrailResult:
        """Run all guardrail checks on agent output content.

        Args:
            content: The agent's output text to check.
            context: Optional context about the conversation (agent_id, user_id, etc.).

        Returns:
            GuardrailResult with pass/fail status and sanitized content.
        """
        result = GuardrailResult(original_content=content)
        sanitized = content

        # Length check
        if len(content) > self.max_output_length:
            result.violations.append({
                "type": ViolationType.CUSTOM.value,
                "severity": "low",
                "detail": f"Output exceeds max length ({len(content)} > {self.max_output_length})",
            })
            sanitized = sanitized[:self.max_output_length] + "\n[Output truncated]"

        # PII redaction
        if self.enable_pii_redaction:
            pii_violations = self._check_pii(sanitized)
            if pii_violations:
                result.violations.extend(pii_violations)
                for pattern, replacement, _ in self.PII_PATTERNS:
                    sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        # Toxicity check
        if self.enable_toxicity_check:
            tox_violations = self._check_toxicity(sanitized)
            if tox_violations:
                result.violations.extend(tox_violations)

        # Prompt injection check
        if self.enable_injection_check:
            inj_violations = self._check_injection(content)
            if inj_violations:
                result.violations.extend(inj_violations)

        # Determine result
        if result.violations:
            high_severity = [v for v in result.violations if v.get("severity") == "high"]
            medium_severity = [v for v in result.violations if v.get("severity") == "medium"]

            if high_severity:
                result.passed = False
                result.category = ContentCategory.BLOCKED
                self._stats["blocked"] += 1
            elif medium_severity:
                result.passed = True
                result.category = ContentCategory.WARNING
                self._stats["redacted"] += 1
            else:
                result.passed = True
                result.category = ContentCategory.SENSITIVE
                self._stats["redacted"] += 1
        else:
            self._stats["passed"] += 1

        result.sanitized_content = sanitized
        result.confidence = self._calculate_confidence(result)

        return result

    def _check_pii(self, content: str) -> list[dict]:
        """Check for PII patterns and return violations."""
        violations = []
        for pattern, replacement, pii_type in self.PII_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                for match in matches[:3]:  # Limit to first 3 matches
                    violations.append({
                        "type": ViolationType.PII.value,
                        "severity": "medium",
                        "detail": f"Potential {pii_type} detected",
                        "span": str(match)[:50],
                    })
        return violations

    def _check_toxicity(self, content: str) -> list[dict]:
        """Check for toxic or harmful content patterns."""
        violations = []
        content_lower = content.lower()

        for pattern in self.TOXICITY_PATTERNS:
            matches = re.findall(pattern, content_lower)
            if matches:
                # Check for context — single match in a long text might be false positive
                if len(matches) >= 2 or len(content) < 500:
                    violations.append({
                        "type": ViolationType.TOXICITY.value,
                        "severity": "high" if len(matches) >= 3 else "medium",
                        "detail": f"Potentially harmful content detected ({len(matches)} matches)",
                        "span": matches[0][:50] if matches else "",
                    })

        return violations

    def _check_injection(self, content: str) -> list[dict]:
        """Check for prompt injection attempts."""
        violations = []
        content_lower = content.lower()

        for pattern in self.INJECTION_PATTERNS:
            matches = re.findall(pattern, content_lower)
            if matches:
                violations.append({
                    "type": ViolationType.PROMPT_INJECTION.value,
                    "severity": "high",
                    "detail": "Prompt injection pattern detected in output",
                    "span": matches[0][:80] if matches else "",
                })
                break  # One injection is enough

        return violations

    def _calculate_confidence(self, result: GuardrailResult) -> float:
        """Calculate confidence score based on violations."""
        if not result.violations:
            return 1.0
        high_count = sum(1 for v in result.violations if v.get("severity") == "high")
        medium_count = sum(1 for v in result.violations if v.get("severity") == "medium")
        low_count = sum(1 for v in result.violations if v.get("severity") == "low")

        return max(0.0, 1.0 - (high_count * 0.4 + medium_count * 0.2 + low_count * 0.05))

    def get_stats(self) -> dict:
        """Get guardrail engine statistics."""
        total = sum(self._stats.values())
        return {
            **self._stats,
            "total_checks": total,
            "pass_rate": f"{(self._stats['passed'] / max(total, 1) * 100):.1f}%",
        }

    def add_custom_pattern(self, pattern: str, violation_type: str, severity: str = "medium"):
        """Add a custom regex pattern to check against."""
        self.INJECTION_PATTERNS.append(pattern)
        logger.info(f"Custom guardrail pattern added: {violation_type}")


# Singleton instance
guardrails_engine = GuardrailsEngine()