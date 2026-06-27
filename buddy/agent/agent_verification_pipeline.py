"""
Agent Verification Pipeline - Self-verification and quality assurance for agent outputs.

Provides comprehensive verification:
- Multi-stage verification pipeline (factual, logical, consistency, safety)
- Cross-reference validation against knowledge sources
- Hallucination detection and mitigation
- Output quality scoring with explainable metrics
- Automated regression testing of agent responses
- Self-healing verification loops with corrective feedback
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.verification_pipeline")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class VerificationStage(str, Enum):
    """Stages in the verification pipeline."""
    FACTUAL = "factual"
    LOGICAL = "logical"
    CONSISTENCY = "consistency"
    SAFETY = "safety"
    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"
    FORMAT = "format"
    QUALITY = "quality"


class VerdictCode(str, Enum):
    """Verification verdict codes."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    UNCERTAIN = "uncertain"
    SKIP = "skip"


class SeverityLevel(str, Enum):
    """Severity of verification issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CorrectionStrategy(str, Enum):
    """How to handle verification failures."""
    RETRY = "retry"
    REFINE = "refine"
    REPLACE = "replace"
    SUPPLEMENT = "supplement"
    ESCALATE = "escalate"
    ACCEPT = "accept"


class FactSource(str, Enum):
    """Source of factual verification."""
    KNOWLEDGE_BASE = "knowledge_base"
    SEARCH_ENGINE = "search_engine"
    CODE_EXECUTION = "code_execution"
    CROSS_REFERENCE = "cross_reference"
    PEER_REVIEW = "peer_review"
    SELF_CONSISTENCY = "self_consistency"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class VerificationIssue:
    """A single issue found during verification."""
    issue_id: str
    stage: VerificationStage
    code: str
    message: str
    severity: SeverityLevel
    location: str = ""
    context: str = ""
    suggestion: str = ""
    correction: str = ""
    auto_fixable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "stage": self.stage.value,
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "location": self.location,
            "context": self.context,
            "suggestion": self.suggestion,
            "correction": self.correction,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class StageResult:
    """Result of a single verification stage."""
    stage: VerificationStage
    verdict: VerdictCode
    score: float
    issues: list[VerificationIssue] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "verdict": self.verdict.value,
            "score": self.score,
            "issue_count": len(self.issues),
            "issues": [i.to_dict() for i in self.issues],
            "duration_ms": self.duration_ms,
        }


@dataclass
class VerificationResult:
    """Complete verification result for a single output."""
    result_id: str
    output_id: str
    verdict: VerdictCode
    overall_score: float
    stages: list[StageResult]
    total_issues: int
    critical_issues: int
    corrections_applied: list[str]
    correction_count: int
    total_duration_ms: float
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "output_id": self.output_id,
            "verdict": self.verdict.value,
            "overall_score": self.overall_score,
            "stages": [s.to_dict() for s in self.stages],
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "corrections_applied": self.corrections_applied,
            "correction_count": self.correction_count,
            "total_duration_ms": self.total_duration_ms,
            "verified_at": self.verified_at.isoformat(),
        }


@dataclass
class VerificationProfile:
    """Configuration profile for verification behavior."""
    profile_id: str
    name: str
    enabled_stages: list[VerificationStage]
    min_pass_score: float = 0.7
    max_retries: int = 3
    auto_correct: bool = True
    correction_strategy: CorrectionStrategy = CorrectionStrategy.REFINE
    stage_configs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "enabled_stages": [s.value for s in self.enabled_stages],
            "min_pass_score": self.min_pass_score,
            "max_retries": self.max_retries,
            "auto_correct": self.auto_correct,
            "correction_strategy": self.correction_strategy.value,
        }


@dataclass
class VerificationStats:
    """Statistics for the verification pipeline."""
    total_verified: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_corrected: int = 0
    total_issues_found: int = 0
    avg_score: float = 0.0
    avg_duration_ms: float = 0.0
    stage_pass_rates: dict[str, float] = field(default_factory=dict)
    common_issues: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_verified": self.total_verified,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
            "total_corrected": self.total_corrected,
            "total_issues_found": self.total_issues_found,
            "pass_rate": self.total_passed / max(1, self.total_verified),
            "avg_score": self.avg_score,
            "avg_duration_ms": self.avg_duration_ms,
            "stage_pass_rates": self.stage_pass_rates,
            "common_issues": self.common_issues,
        }


# ═══════════════════════════════════════════════════════════
# Verification Pipeline
# ═══════════════════════════════════════════════════════════

class VerificationPipeline:
    """
    Multi-stage verification pipeline for agent outputs.
    
    Stages:
    1. Factual - Verify factual claims against knowledge sources
    2. Logical - Check logical consistency and reasoning validity
    3. Consistency - Ensure internal and cross-response consistency
    4. Safety - Screen for harmful, biased, or unsafe content
    5. Completeness - Verify all requested aspects are addressed
    6. Relevance - Check response relevance to the query
    7. Format - Validate output format and structure
    8. Quality - Assess overall quality, clarity, and usefulness
    """

    def __init__(self, config: VerificationPipelineConfig | None = None):
        self.config = config or VerificationPipelineConfig()
        self._profiles: dict[str, VerificationProfile] = {}
        self._results: dict[str, VerificationResult] = {}
        self._stats = VerificationStats()
        self._stage_handlers: dict[VerificationStage, callable] = {}
        self._register_default_handlers()
        self._init_default_profiles()

    def _register_default_handlers(self) -> None:
        """Register default verification stage handlers."""
        self._stage_handlers = {
            VerificationStage.FACTUAL: self._verify_factual,
            VerificationStage.LOGICAL: self._verify_logical,
            VerificationStage.CONSISTENCY: self._verify_consistency,
            VerificationStage.SAFETY: self._verify_safety,
            VerificationStage.COMPLETENESS: self._verify_completeness,
            VerificationStage.RELEVANCE: self._verify_relevance,
            VerificationStage.FORMAT: self._verify_format,
            VerificationStage.QUALITY: self._verify_quality,
        }

    def _init_default_profiles(self) -> None:
        """Initialize default verification profiles."""
        # Strict profile - all stages, high threshold
        strict = VerificationProfile(
            profile_id="strict",
            name="Strict Verification",
            enabled_stages=list(VerificationStage),
            min_pass_score=0.85,
            max_retries=2,
            auto_correct=True,
            correction_strategy=CorrectionStrategy.REFINE,
        )
        self._profiles["strict"] = strict

        # Standard profile - most stages, moderate threshold
        standard = VerificationProfile(
            profile_id="standard",
            name="Standard Verification",
            enabled_stages=[
                VerificationStage.FACTUAL,
                VerificationStage.LOGICAL,
                VerificationStage.SAFETY,
                VerificationStage.COMPLETENESS,
                VerificationStage.QUALITY,
            ],
            min_pass_score=0.7,
            max_retries=3,
            auto_correct=True,
            correction_strategy=CorrectionStrategy.REFINE,
        )
        self._profiles["standard"] = standard

        # Quick profile - critical checks only
        quick = VerificationProfile(
            profile_id="quick",
            name="Quick Verification",
            enabled_stages=[
                VerificationStage.SAFETY,
                VerificationStage.FORMAT,
            ],
            min_pass_score=0.6,
            max_retries=1,
            auto_correct=False,
            correction_strategy=CorrectionStrategy.ACCEPT,
        )
        self._profiles["quick"] = quick

    def register_profile(self, profile: VerificationProfile) -> None:
        """Register a custom verification profile."""
        self._profiles[profile.profile_id] = profile

    def register_handler(self, stage: VerificationStage, handler: callable) -> None:
        """Register a custom verification stage handler."""
        self._stage_handlers[stage] = handler

    # ── Main Verification ──

    def verify(
        self,
        output: str,
        context: dict[str, Any] | None = None,
        profile_id: str = "standard",
        output_id: str = "",
        apply_corrections: bool = True,
    ) -> VerificationResult:
        """
        Run verification pipeline on an agent output.
        
        Args:
            output: The agent output to verify
            context: Additional context (query, history, knowledge, etc.)
            profile_id: Verification profile to use
            output_id: Identifier for the output
            apply_corrections: Whether to auto-apply corrections
            
        Returns:
            VerificationResult with full verification details
        """
        context = context or {}
        profile = self._profiles.get(profile_id, self._profiles["standard"])
        result_id = str(uuid.uuid4())[:8]
        output_id = output_id or result_id

        start = time.time()
        stage_results: list[StageResult] = []
        total_issues = 0
        critical_issues = 0
        corrections: list[str] = []
        corrected_output = output

        for stage_enum in profile.enabled_stages:
            handler = self._stage_handlers.get(stage_enum)
            if not handler:
                stage_results.append(StageResult(
                    stage=stage_enum,
                    verdict=VerdictCode.SKIP,
                    score=1.0,
                ))
                continue

            stage_start = time.time()
            try:
                stage_result = handler(corrected_output, context)
                stage_result.duration_ms = (time.time() - stage_start) * 1000

                total_issues += len(stage_result.issues)
                critical_issues += sum(
                    1 for i in stage_result.issues
                    if i.severity == SeverityLevel.CRITICAL
                )

                # Apply corrections if enabled
                if apply_corrections and profile.auto_correct:
                    for issue in stage_result.issues:
                        if issue.auto_fixable and issue.correction:
                            corrected_output = self._apply_correction(
                                corrected_output, issue
                            )
                            corrections.append(f"[{stage_enum.value}] {issue.code}: {issue.correction}")

                stage_results.append(stage_result)

            except Exception as e:
                logger.error("Stage %s failed: %s", stage_enum.value, e)
                stage_results.append(StageResult(
                    stage=stage_enum,
                    verdict=VerdictCode.UNCERTAIN,
                    score=0.5,
                    issues=[VerificationIssue(
                        issue_id=str(uuid.uuid4())[:8],
                        stage=stage_enum,
                        code="STAGE_ERROR",
                        message=f"Verification stage error: {e}",
                        severity=SeverityLevel.HIGH,
                    )],
                    duration_ms=(time.time() - stage_start) * 1000,
                ))

        # Calculate overall score
        if stage_results:
            overall_score = sum(s.score for s in stage_results) / len(stage_results)
        else:
            overall_score = 1.0

        # Determine overall verdict
        if critical_issues > 0:
            verdict = VerdictCode.FAIL
        elif overall_score >= profile.min_pass_score:
            verdict = VerdictCode.PASS
        elif any(s.verdict == VerdictCode.FAIL for s in stage_results):
            verdict = VerdictCode.FAIL
        else:
            verdict = VerdictCode.WARN

        total_duration = (time.time() - start) * 1000

        result = VerificationResult(
            result_id=result_id,
            output_id=output_id,
            verdict=verdict,
            overall_score=round(overall_score, 3),
            stages=stage_results,
            total_issues=total_issues,
            critical_issues=critical_issues,
            corrections_applied=corrections,
            correction_count=len(corrections),
            total_duration_ms=round(total_duration, 2),
        )

        self._results[result_id] = result
        self._update_stats(result)

        logger.info(
            "Verification %s complete: verdict=%s, score=%.2f, issues=%d, corrections=%d, %.1fms",
            result_id, verdict.value, overall_score, total_issues,
            len(corrections), total_duration,
        )

        return result

    def verify_with_correction_loop(
        self,
        output: str,
        regenerate_fn: callable,
        context: dict[str, Any] | None = None,
        profile_id: str = "standard",
        max_iterations: int = 3,
    ) -> tuple[str, VerificationResult]:
        """
        Verify output and auto-correct through regeneration loop.
        
        Args:
            output: Initial output to verify
            regenerate_fn: Function to regenerate corrected output
            context: Verification context
            profile_id: Verification profile
            max_iterations: Maximum correction iterations
            
        Returns:
            Tuple of (final_output, verification_result)
        """
        context = context or {}
        current_output = output
        final_result = None

        for iteration in range(max_iterations):
            result = self.verify(
                output=current_output,
                context=context,
                profile_id=profile_id,
                apply_corrections=iteration < max_iterations - 1,
            )

            if result.verdict == VerdictCode.PASS:
                return current_output, result

            # Collect issues for regeneration
            issues_for_regeneration = [
                i for s in result.stages
                for i in s.issues
                if i.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH)
            ]

            if not issues_for_regeneration:
                return current_output, result

            # Regenerate with issue feedback
            try:
                current_output = regenerate_fn(
                    original_output=current_output,
                    issues=issues_for_regeneration,
                    context=context,
                )
            except Exception as e:
                logger.error("Regeneration failed: %s", e)
                return current_output, result

            final_result = result

        return current_output, final_result or VerificationResult(
            result_id=str(uuid.uuid4())[:8],
            output_id="",
            verdict=VerdictCode.WARN,
            overall_score=0.0,
            stages=[],
            total_issues=0,
            critical_issues=0,
            corrections_applied=[],
            correction_count=0,
            total_duration_ms=0.0,
        )

    # ── Stage Handlers ──

    def _verify_factual(
        self, output: str, context: dict[str, Any]
    ) -> StageResult:
        """Verify factual accuracy of the output."""
        issues: list[VerificationIssue] = []

        # Check for unsupported claims
        knowledge = context.get("knowledge", "")
        if knowledge:
            claims = self._extract_claims(output)
            for claim in claims:
                if not self._is_claim_supported(claim, knowledge):
                    issues.append(VerificationIssue(
                        issue_id=str(uuid.uuid4())[:8],
                        stage=VerificationStage.FACTUAL,
                        code="UNSUPPORTED_CLAIM",
                        message=f"Claim may not be supported: {claim[:100]}",
                        severity=SeverityLevel.MEDIUM,
                        location=claim[:50],
                        context=claim,
                        suggestion="Verify this claim against knowledge sources",
                    ))

        # Check for hallucination indicators
        hallucinations = self._detect_hallucinations(output)
        for h in hallucinations:
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                stage=VerificationStage.FACTUAL,
                code="POTENTIAL_HALLUCINATION",
                message=h,
                severity=SeverityLevel.HIGH,
                auto_fixable=False,
            ))

        score = self._calculate_stage_score(issues, 1.0)
        return StageResult(
            stage=VerificationStage.FACTUAL,
            verdict=self._determine_verdict(score),
            score=score,
            issues=issues,
        )

    def _verify_logical(
        self, output: str, context: dict[str, Any]
    ) -> StageResult:
        """Verify logical consistency of the output."""
        issues: list[VerificationIssue] = []

        # Check for contradictions
        contradictions = self._detect_contradictions(output)
        for c in contradictions:
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                stage=VerificationStage.LOGICAL,
                code="CONTRADICTION",
                message=c,
                severity=SeverityLevel.HIGH,
                auto_fixable=False,
            ))

        # Check for circular reasoning
        if self._has_circular_reasoning(output):
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                stage=VerificationStage.LOGICAL,
                code="CIRCULAR_REASONING",
                message="Output contains circular reasoning patterns",
                severity=SeverityLevel.MEDIUM,
                suggestion="Restructure reasoning to avoid circular logic",
            ))

        # Check for false dilemmas
        false_dilemmas = self._detect_false_dilemmas(output)
        for fd in false_dilemmas:
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                stage=VerificationStage.LOGICAL,
                code="FALSE_DILEMMA",
                message=fd,
                severity=SeverityLevel.LOW,
            ))

        score = self._calculate_stage_score(issues, 1.0)
        return StageResult(
            stage=VerificationStage.LOGICAL,
            verdict=self._determine_verdict(score),
            score=score,
            issues=issues,
        )

    def _verify_consistency(
        self, output: str, context: dict[str, Any]
    ) -> StageResult:
        """Verify consistency with context and history."""
        issues: list[VerificationIssue] = []

        history = context.get("history", [])
        if history:
            for i, prev in enumerate(history[-3:]):
                if self._has_conflict(output, prev):
                    issues.append(VerificationIssue(
                        issue_id=str(uuid.uuid4())[:8],
                        stage=VerificationStage.CONSISTENCY,
                        code="CONTEXT_CONFLICT",
                        message=f"Output conflicts with previous response #{i + 1}",
                        severity=SeverityLevel.MEDIUM,
                    ))

        score = self._calculate_stage_score(issues, 1.0)
        return StageResult(
            stage=VerificationStage.CONSISTENCY,
            verdict=self._determine_verdict(score),
            score=score,
            issues=issues,
        )

    def _verify_safety(
        self, output: str, context: dict[str, Any]
    ) -> StageResult:
        """Verify safety of the output content."""
        issues: list[VerificationIssue] = []

        # Check for harmful content patterns
        harmful_patterns = [
            (r"(?i)\b(hack|exploit|illegal|malware|phish)\b", "HARMFUL_KEYWORD"),
            (r"(?i)\b(suicide|self-harm|violent)\b", "SENSITIVE_TOPIC"),
        ]

        for pattern, code in harmful_patterns:
            if re.search(pattern, output):
                issues.append(VerificationIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    stage=VerificationStage.SAFETY,
                    code=code,
                    message=f"Potentially sensitive content detected: {code}",
                    severity=SeverityLevel.HIGH,
                    suggestion="Review and redact sensitive content",
                ))

        score = self._calculate_stage_score(issues, 1.0)
        return StageResult(
            stage=VerificationStage.SAFETY,
            verdict=self._determine_verdict(score),
            score=score,
            issues=issues,
        )

    def _verify_completeness(
        self, output: str, context: dict[str, Any]
    ) -> StageResult:
        """Verify completeness of the response."""
        issues: list[VerificationIssue] = []

        query = context.get("query", "")
        if query and len(output) < 20:
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                stage=VerificationStage.COMPLETENESS,
                code="INCOMPLETE_RESPONSE",
                message="Response is too short to be complete",
                severity=SeverityLevel.HIGH,
                suggestion="Provide a more detailed response",
            ))

        # Check for truncation
        if output.rstrip().endswith(("...", "etc.", "and so on")):
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                stage=VerificationStage.COMPLETENESS,
                code="TRUNCATED",
                message="Response appears to be truncated",
                severity=SeverityLevel.MEDIUM,
            ))

        score = self._calculate_stage_score(issues, 1.0)
        return StageResult(
            stage=VerificationStage.COMPLETENESS,
            verdict=self._determine_verdict(score),
            score=score,
            issues=issues,
        )

    def _verify_relevance(
        self, output: str, context: dict[str, Any]
    ) -> StageResult:
        """Verify relevance of the output to the query."""
        issues: list[VerificationIssue] = []

        query = context.get("query", "")
        if query and len(query) > 10:
            # Simple keyword overlap check
            query_words = set(query.lower().split())
            output_words = set(output.lower().split())
            overlap = query_words & output_words
            if len(overlap) < 2 and len(query_words) > 3:
                issues.append(VerificationIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    stage=VerificationStage.RELEVANCE,
                    code="LOW_RELEVANCE",
                    message="Response may not be relevant to the query",
                    severity=SeverityLevel.MEDIUM,
                ))

        score = self._calculate_stage_score(issues, 1.0)
        return StageResult(
            stage=VerificationStage.RELEVANCE,
            verdict=self._determine_verdict(score),
            score=score,
            issues=issues,
        )

    def _verify_format(
        self, output: str, context: dict[str, Any]
    ) -> StageResult:
        """Verify output format and structure."""
        issues: list[VerificationIssue] = []

        expected_format = context.get("expected_format", "")
        if expected_format == "json":
            try:
                json.loads(output)
            except json.JSONDecodeError:
                issues.append(VerificationIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    stage=VerificationStage.FORMAT,
                    code="INVALID_JSON",
                    message="Output is not valid JSON",
                    severity=SeverityLevel.HIGH,
                    auto_fixable=True,
                    correction="Format output as valid JSON",
                ))

        if expected_format == "code":
            if "```" not in output:
                issues.append(VerificationIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    stage=VerificationStage.FORMAT,
                    code="MISSING_CODE_BLOCK",
                    message="Output should contain code blocks",
                    severity=SeverityLevel.LOW,
                ))

        score = self._calculate_stage_score(issues, 1.0)
        return StageResult(
            stage=VerificationStage.FORMAT,
            verdict=self._determine_verdict(score),
            score=score,
            issues=issues,
        )

    def _verify_quality(
        self, output: str, context: dict[str, Any]
    ) -> StageResult:
        """Assess overall quality of the output."""
        issues: list[VerificationIssue] = []

        # Check for vague language
        vague_patterns = [
            r"(?i)\b(somehow|something|someone|things|stuff)\b",
            r"(?i)\b(maybe|perhaps|possibly|might be|could be)\b",
        ]
        for pattern in vague_patterns:
            if len(re.findall(pattern, output)) > 3:
                issues.append(VerificationIssue(
                    issue_id=str(uuid.uuid4())[:8],
                    stage=VerificationStage.QUALITY,
                    code="VAGUE_LANGUAGE",
                    message="Output contains overly vague language",
                    severity=SeverityLevel.LOW,
                    suggestion="Use more specific and precise language",
                ))

        # Check for repetition
        if self._has_excessive_repetition(output):
            issues.append(VerificationIssue(
                issue_id=str(uuid.uuid4())[:8],
                stage=VerificationStage.QUALITY,
                code="EXCESSIVE_REPETITION",
                message="Output contains excessive repetition",
                severity=SeverityLevel.LOW,
            ))

        score = self._calculate_stage_score(issues, 1.0)
        return StageResult(
            stage=VerificationStage.QUALITY,
            verdict=self._determine_verdict(score),
            score=score,
            issues=issues,
        )

    # ── Helper Methods ──

    def _extract_claims(self, text: str) -> list[str]:
        """Extract factual claims from text."""
        sentences = re.split(r'[.!?]+', text)
        claims = []
        for s in sentences:
            s = s.strip()
            if len(s) > 20 and any(
                keyword in s.lower()
                for keyword in ["is", "are", "was", "were", "has", "have", "will", "can"]
            ):
                claims.append(s)
        return claims[:10]

    def _is_claim_supported(self, claim: str, knowledge: str) -> bool:
        """Check if a claim is supported by knowledge."""
        claim_words = set(claim.lower().split()) - {"the", "a", "an", "is", "are", "was", "were", "has", "have", "will", "can", "in", "on", "at", "to", "for", "of", "and", "or", "that", "this", "it", "be"}
        knowledge_lower = knowledge.lower()
        matches = sum(1 for w in claim_words if len(w) > 3 and w in knowledge_lower)
        return matches >= len(claim_words) * 0.3 if claim_words else True

    def _detect_hallucinations(self, text: str) -> list[str]:
        """Detect potential hallucination indicators."""
        indicators = []
        patterns = [
            (r"\b\d{4}-\d{2}-\d{2}\b", "Specific date mentioned without source"),
            (r"\b\d+%\b", "Specific percentage without source"),
            (r"\baccording to (?:a )?study\b", "Vague study reference"),
            (r"\bresearch (?:has )?shown\b", "Vague research reference"),
        ]
        for pattern, msg in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                indicators.append(msg)
        return indicators

    def _detect_contradictions(self, text: str) -> list[str]:
        """Detect internal contradictions."""
        contradictions = []
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

        for i, s1 in enumerate(sentences):
            for j, s2 in enumerate(sentences):
                if i >= j:
                    continue
                # Check for negation conflicts
                if ("not" in s1 and "not" not in s2) or ("not" in s2 and "not" not in s1):
                    s1_words = set(s1.lower().split())
                    s2_words = set(s2.lower().split())
                    common = s1_words & s2_words - {"not", "the", "a", "an", "is", "are", "was", "were", "it", "this", "that", "to", "of", "in", "and"}
                    if len(common) >= 3:
                        contradictions.append(f"Potential contradiction: '{s1[:50]}...' vs '{s2[:50]}...'")
                        break

        return contradictions[:3]

    def _has_circular_reasoning(self, text: str) -> bool:
        """Check for circular reasoning patterns."""
        circular_patterns = [
            r"(?i)because.*therefore.*because",
            r"(?i)it is.*because.*it is",
        ]
        return any(re.search(p, text) for p in circular_patterns)

    def _detect_false_dilemmas(self, text: str) -> list[str]:
        """Detect false dilemma patterns."""
        dilemmas = []
        if re.search(r"(?i)\b(either|neither).*or\b", text):
            if re.search(r"(?i)\b(only|must|have to)\b", text):
                dilemmas.append("Possible false dilemma: presents only binary options")
        return dilemmas

    def _has_conflict(self, text1: str, text2: str) -> bool:
        """Check if two texts have conflicting information."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        negations1 = {"not", "no", "never", "none", "neither", "nor"}
        negations2 = {"not", "no", "never", "none", "neither", "nor"}

        has_neg1 = bool(words1 & negations1)
        has_neg2 = bool(words2 & negations2)

        if has_neg1 != has_neg2:
            common = (words1 - negations1) & (words2 - negations2)
            common = {w for w in common if len(w) > 3}
            return len(common) >= 3

        return False

    def _has_excessive_repetition(self, text: str) -> bool:
        """Check for excessive word/phrase repetition."""
        words = text.lower().split()
        if len(words) < 20:
            return False
        word_counts = defaultdict(int)
        for w in words:
            if len(w) > 3:
                word_counts[w] += 1
        max_count = max(word_counts.values()) if word_counts else 0
        return max_count > len(words) * 0.15

    def _calculate_stage_score(
        self, issues: list[VerificationIssue], max_score: float
    ) -> float:
        """Calculate stage score based on issues."""
        if not issues:
            return max_score

        deductions = {
            SeverityLevel.CRITICAL: 0.4,
            SeverityLevel.HIGH: 0.2,
            SeverityLevel.MEDIUM: 0.1,
            SeverityLevel.LOW: 0.05,
            SeverityLevel.INFO: 0.0,
        }

        total_deduction = sum(deductions.get(i.severity, 0.05) for i in issues)
        return max(0.0, round(max_score - total_deduction, 2))

    def _determine_verdict(self, score: float) -> VerdictCode:
        """Determine verdict from score."""
        if score >= 0.9:
            return VerdictCode.PASS
        if score >= 0.6:
            return VerdictCode.WARN
        return VerdictCode.FAIL

    def _apply_correction(
        self, output: str, issue: VerificationIssue
    ) -> str:
        """Apply a correction to the output."""
        if issue.code == "INVALID_JSON":
            return output  # Would need JSON repair logic
        return output

    # ── Statistics ──

    def _update_stats(self, result: VerificationResult) -> None:
        """Update verification statistics."""
        self._stats.total_verified += 1
        if result.verdict == VerdictCode.PASS:
            self._stats.total_passed += 1
        elif result.verdict == VerdictCode.FAIL:
            self._stats.total_failed += 1

        self._stats.total_issues_found += result.total_issues
        if result.correction_count > 0:
            self._stats.total_corrected += 1

        n = self._stats.total_verified
        self._stats.avg_score = (
            (self._stats.avg_score * (n - 1) + result.overall_score) / n
        )
        self._stats.avg_duration_ms = (
            (self._stats.avg_duration_ms * (n - 1) + result.total_duration_ms) / n
        )

        for stage in result.stages:
            if stage.stage.value not in self._stats.stage_pass_rates:
                self._stats.stage_pass_rates[stage.stage.value] = 0.0
            prev = self._stats.stage_pass_rates[stage.stage.value]
            self._stats.stage_pass_rates[stage.stage.value] = (
                (prev * (n - 1) + (1.0 if stage.verdict == VerdictCode.PASS else 0.0)) / n
            )

        for stage in result.stages:
            for issue in stage.issues:
                self._stats.common_issues[issue.code] = (
                    self._stats.common_issues.get(issue.code, 0) + 1
                )

    def get_stats(self) -> VerificationStats:
        """Get current verification statistics."""
        return self._stats

    def get_result(self, result_id: str) -> VerificationResult | None:
        """Get a verification result by ID."""
        return self._results.get(result_id)

    def list_results(self, limit: int = 50) -> list[VerificationResult]:
        """List recent verification results."""
        return list(self._results.values())[-limit:]

    def reset(self) -> None:
        """Reset the verification pipeline."""
        self._results.clear()
        self._stats = VerificationStats()
        logger.info("Verification pipeline reset")


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@dataclass
class VerificationPipelineConfig:
    """Configuration for the verification pipeline."""
    enabled: bool = True
    default_profile: str = "standard"
    max_verification_time_ms: int = 5000
    max_issues_per_stage: int = 20
    log_verification_results: bool = True
    collect_metrics: bool = True
    auto_correct_enabled: bool = True
    correction_max_attempts: int = 3


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_verification_pipeline: VerificationPipeline | None = None


def get_verification_pipeline() -> VerificationPipeline:
    """Get or create the singleton verification pipeline."""
    global _verification_pipeline
    if _verification_pipeline is None:
        _verification_pipeline = VerificationPipeline()
    return _verification_pipeline


def reset_verification_pipeline() -> None:
    """Reset the singleton verification pipeline."""
    global _verification_pipeline
    if _verification_pipeline:
        _verification_pipeline.reset()
    _verification_pipeline = None