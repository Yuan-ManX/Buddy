"""
Buddy Code Review Engine — AI-Native Multi-Perspective Code Analysis System.

Comprehensive automated code review that evaluates code from multiple dimensions
including security, performance, style, architecture, correctness, maintainability,
and testing. Supports single-file review, diff analysis, batch processing, version
comparison, and self-improvement through review pattern learning.

Key capabilities:
- Multi-perspective review across 7 quality dimensions
- Automated review generation from code diffs and patches
- Priority scoring with severity classification
- Review history tracking with version comparison
- Batch review for multiple files with parallel execution
- Self-improvement through review pattern learning
- Simulation mode with rule-based pattern matching when no LLM is available
- Integration with UnifiedAgentSystem for deep reasoning
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.code_review")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class ReviewDimension(str, Enum):
    """Dimensions along which code can be reviewed."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    ARCHITECTURE = "architecture"
    CORRECTNESS = "correctness"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"


class Severity(str, Enum):
    """Severity level of a review finding."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def weight(self) -> int:
        """Numeric weight for severity scoring."""
        return {
            Severity.CRITICAL: 100,
            Severity.HIGH: 50,
            Severity.MEDIUM: 25,
            Severity.LOW: 10,
            Severity.INFO: 0,
        }[self]


class ReviewStatus(str, Enum):
    """Status of a code review."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class ReviewFinding:
    """A single finding discovered during code review."""
    finding_id: str
    dimension: ReviewDimension
    severity: Severity
    line_start: int
    line_end: int
    file_path: str
    title: str
    description: str
    suggestion: str
    code_snippet: str = ""
    confidence: float = 0.8
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "file_path": self.file_path,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class CodeReview:
    """A complete code review with all findings and metadata."""
    review_id: str
    file_paths: list[str] = field(default_factory=list)
    diff_content: str = ""
    language: str = ""
    findings: list[ReviewFinding] = field(default_factory=list)
    summary: str = ""
    overall_score: float = 0.0
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_agents: list[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.LOW)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "file_paths": self.file_paths,
            "language": self.language,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "overall_score": self.overall_score,
            "status": self.status.value,
            "reviewer_agents": self.reviewer_agents,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "counts": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "info": self.info_count,
            },
        }


@dataclass
class ReviewPattern:
    """A learned review pattern for detecting common issues."""
    pattern_id: str
    pattern_type: str
    regex_pattern: str
    description: str
    severity: Severity
    dimension: ReviewDimension
    occurrence_count: int = 0
    suggestion: str = ""
    confidence: float = 0.7
    created_at: float = field(default_factory=time.time)
    last_matched_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "regex_pattern": self.regex_pattern,
            "description": self.description,
            "severity": self.severity.value,
            "dimension": self.dimension.value,
            "occurrence_count": self.occurrence_count,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "last_matched_at": self.last_matched_at,
        }


@dataclass
class ReviewStats:
    """Aggregated statistics for code review performance."""
    total_reviews: int = 0
    total_findings: int = 0
    by_severity: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_dimension: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_language: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    average_score: float = 0.0
    total_patterns_learned: int = 0
    total_version_comparisons: int = 0
    average_review_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_reviews": self.total_reviews,
            "total_findings": self.total_findings,
            "by_severity": dict(self.by_severity),
            "by_dimension": dict(self.by_dimension),
            "by_language": dict(self.by_language),
            "average_score": self.average_score,
            "total_patterns_learned": self.total_patterns_learned,
            "total_version_comparisons": self.total_version_comparisons,
            "average_review_time_ms": self.average_review_time_ms,
        }


# ═══════════════════════════════════════════════════════════
# Built-in Review Patterns
# ═══════════════════════════════════════════════════════════

_BUILTIN_PATTERNS: list[ReviewPattern] = [
    # ── Python Security Patterns ──
    ReviewPattern(
        pattern_id="py-sec-001",
        pattern_type="regex",
        regex_pattern=r"os\.system\(|subprocess\.call\(.*shell\s*=\s*True",
        description="Use of os.system() or subprocess with shell=True may allow command injection",
        severity=Severity.CRITICAL,
        dimension=ReviewDimension.SECURITY,
        suggestion="Use subprocess.run() with shell=False and a list of arguments instead",
        confidence=0.95,
    ),
    ReviewPattern(
        pattern_id="py-sec-002",
        pattern_type="regex",
        regex_pattern=r"eval\(|exec\(|__import__\(",
        description="Use of eval() or exec() can execute arbitrary code and is a security risk",
        severity=Severity.CRITICAL,
        dimension=ReviewDimension.SECURITY,
        suggestion="Use safer alternatives like ast.literal_eval(), getattr(), or importlib",
        confidence=0.95,
    ),
    ReviewPattern(
        pattern_id="py-sec-003",
        pattern_type="regex",
        regex_pattern=r"pickle\.loads?\(|yaml\.load\(.*Loader\s*=\s*yaml\.Loader",
        description="Unsafe deserialization using pickle or yaml.load without SafeLoader",
        severity=Severity.HIGH,
        dimension=ReviewDimension.SECURITY,
        suggestion="Use yaml.safe_load() or pickle with caution; prefer JSON for serialization",
        confidence=0.90,
    ),
    ReviewPattern(
        pattern_id="py-sec-004",
        pattern_type="regex",
        regex_pattern=r"password\s*=\s*['\"][^'\"]+['\"]",
        description="Hardcoded password or secret detected in source code",
        severity=Severity.CRITICAL,
        dimension=ReviewDimension.SECURITY,
        suggestion="Store secrets in environment variables or a secure vault; never hardcode credentials",
        confidence=0.90,
    ),
    ReviewPattern(
        pattern_id="py-sec-005",
        pattern_type="regex",
        regex_pattern=r"assert\s+.*\s*,\s*['\"].*['\"]\s*$",
        description="Assert statements with messages are removed in optimized mode (-O); use for debugging only",
        severity=Severity.LOW,
        dimension=ReviewDimension.SECURITY,
        suggestion="Use proper if/raise statements for runtime validation instead of assert",
        confidence=0.80,
    ),

    # ── Python Performance Patterns ──
    ReviewPattern(
        pattern_id="py-perf-001",
        pattern_type="regex",
        regex_pattern=r"for\s+\w+\s+in\s+range\(len\(.+\)\)",
        description="Using range(len()) for iteration is less Pythonic and slower than direct iteration",
        severity=Severity.LOW,
        dimension=ReviewDimension.PERFORMANCE,
        suggestion="Use enumerate() for index-value pairs, or iterate the collection directly",
        confidence=0.85,
    ),
    ReviewPattern(
        pattern_id="py-perf-002",
        pattern_type="regex",
        regex_pattern=r"\+=\s*['\"].*['\"]\s*\+\s*['\"]",
        description="String concatenation in a loop; consider using list comprehension with join()",
        severity=Severity.MEDIUM,
        dimension=ReviewDimension.PERFORMANCE,
        suggestion="Collect strings in a list and use ''.join() for better performance",
        confidence=0.85,
    ),
    ReviewPattern(
        pattern_id="py-perf-003",
        pattern_type="regex",
        regex_pattern=r"\.keys\(\)\s*in\s+for\b|if\s+\w+\s+in\s+\w+\.keys\(\)",
        description="Calling .keys() for membership testing is redundant and slower",
        severity=Severity.LOW,
        dimension=ReviewDimension.PERFORMANCE,
        suggestion="Use 'in dict' directly instead of 'in dict.keys()'",
        confidence=0.90,
    ),

    # ── Python Style Patterns ──
    ReviewPattern(
        pattern_id="py-style-001",
        pattern_type="regex",
        regex_pattern=r"except\s*:",
        description="Bare except clause catches all exceptions including KeyboardInterrupt and SystemExit",
        severity=Severity.MEDIUM,
        dimension=ReviewDimension.STYLE,
        suggestion="Specify the exception type(s) to catch; use 'except Exception:' as a minimum",
        confidence=0.90,
    ),
    ReviewPattern(
        pattern_id="py-style-002",
        pattern_type="regex",
        regex_pattern=r"def\s+\w+\([^)]*\)\s*:\s*pass\s*$",
        description="Function body contains only 'pass' - likely a stub that needs implementation",
        severity=Severity.INFO,
        dimension=ReviewDimension.STYLE,
        suggestion="Implement the function or raise NotImplementedError if intentionally deferred",
        confidence=0.75,
    ),
    ReviewPattern(
        pattern_id="py-style-003",
        pattern_type="regex",
        regex_pattern=r"^\s*import\s+\*",
        description="Wildcard import (import *) pollutes namespace and makes dependencies unclear",
        severity=Severity.MEDIUM,
        dimension=ReviewDimension.STYLE,
        suggestion="Import only the specific names needed, or use __all__ to control exports",
        confidence=0.85,
    ),

    # ── Python Correctness Patterns ──
    ReviewPattern(
        pattern_id="py-corr-001",
        pattern_type="regex",
        regex_pattern=r"^\s*return\s+None\s*$",
        description="Explicit 'return None' is redundant; Python returns None by default",
        severity=Severity.INFO,
        dimension=ReviewDimension.CORRECTNESS,
        suggestion="Remove the explicit 'return None' or use a bare 'return' for consistency",
        confidence=0.85,
    ),
    ReviewPattern(
        pattern_id="py-corr-002",
        pattern_type="regex",
        regex_pattern=r"if\s+\w+\s*==\s*None\s*or\s*\w+\s*==\s*None",
        description="Multiple None checks can be simplified using 'is None'",
        severity=Severity.LOW,
        dimension=ReviewDimension.CORRECTNESS,
        suggestion="Use 'is None' instead of '== None' for None comparisons",
        confidence=0.90,
    ),
    ReviewPattern(
        pattern_id="py-corr-003",
        pattern_type="regex",
        regex_pattern=r"^\s*if\s+\w+\s*==\s*True\s*:",
        description="Comparing to True/False with '==' is redundant",
        severity=Severity.INFO,
        dimension=ReviewDimension.CORRECTNESS,
        suggestion="Use 'if variable:' or 'if not variable:' instead of '== True'/'== False'",
        confidence=0.85,
    ),

    # ── Python Architecture Patterns ──
    ReviewPattern(
        pattern_id="py-arch-001",
        pattern_type="regex",
        regex_pattern=r"class\s+\w+\s*[^(]*\s*:\s*$",
        description="Class exceeds 300 lines may indicate single responsibility violation",
        severity=Severity.INFO,
        dimension=ReviewDimension.ARCHITECTURE,
        suggestion="Consider splitting large classes into smaller, focused components",
        confidence=0.60,
    ),

    # ── Python Testing Patterns ──
    ReviewPattern(
        pattern_id="py-test-001",
        pattern_type="regex",
        regex_pattern=r"^\s*def\s+test_\w+\s*\([^)]*\)\s*:\s*pass\s*$",
        description="Empty test function found - test is not actually testing anything",
        severity=Severity.MEDIUM,
        dimension=ReviewDimension.TESTING,
        suggestion="Implement the test body or remove the stub",
        confidence=0.85,
    ),

    # ── TypeScript / JavaScript Security Patterns ──
    ReviewPattern(
        pattern_id="ts-sec-001",
        pattern_type="regex",
        regex_pattern=r"eval\(|new\s+Function\(|setTimeout\(.*['\"]",
        description="Dynamic code execution using eval() or Function constructor is a security risk",
        severity=Severity.CRITICAL,
        dimension=ReviewDimension.SECURITY,
        suggestion="Avoid dynamic code evaluation; use safer alternatives or sanitize inputs",
        confidence=0.95,
    ),
    ReviewPattern(
        pattern_id="ts-sec-002",
        pattern_type="regex",
        regex_pattern=r"innerHTML\s*=|document\.write\(|dangerouslySetInnerHTML",
        description="Use of innerHTML or dangerouslySetInnerHTML can lead to XSS vulnerabilities",
        severity=Severity.HIGH,
        dimension=ReviewDimension.SECURITY,
        suggestion="Use textContent, createElement, or sanitize HTML with DOMPurify",
        confidence=0.90,
    ),
    ReviewPattern(
        pattern_id="ts-sec-003",
        pattern_type="regex",
        regex_pattern=r"api_key\s*=\s*['\"][^'\"]+['\"]|secret\s*=\s*['\"][^'\"]+['\"]",
        description="Hardcoded API key or secret found in source code",
        severity=Severity.CRITICAL,
        dimension=ReviewDimension.SECURITY,
        suggestion="Use environment variables (process.env) or a secrets manager",
        confidence=0.95,
    ),

    # ── TypeScript / JavaScript Performance Patterns ──
    ReviewPattern(
        pattern_id="ts-perf-001",
        pattern_type="regex",
        regex_pattern=r"console\.log\(.*\)",
        description="Console.log statements in production code may impact performance and leak information",
        severity=Severity.LOW,
        dimension=ReviewDimension.PERFORMANCE,
        suggestion="Remove console.log statements or use a logging library with level control",
        confidence=0.80,
    ),
    ReviewPattern(
        pattern_id="ts-perf-002",
        pattern_type="regex",
        regex_pattern=r"for\s*\(\s*.*\s+in\s+\w+\)",
        description="for...in iterates over enumerable properties including inherited ones; use for...of or Object.keys()",
        severity=Severity.LOW,
        dimension=ReviewDimension.PERFORMANCE,
        suggestion="Use for...of for arrays or Object.keys()/Object.entries() for objects",
        confidence=0.80,
    ),

    # ── TypeScript / JavaScript Style Patterns ──
    ReviewPattern(
        pattern_id="ts-style-001",
        pattern_type="regex",
        regex_pattern=r"^\s*var\s+\w+",
        description="Using 'var' instead of 'const' or 'let' - var has function scope and hoisting issues",
        severity=Severity.LOW,
        dimension=ReviewDimension.STYLE,
        suggestion="Use 'const' by default, 'let' only when reassignment is needed",
        confidence=0.90,
    ),
    ReviewPattern(
        pattern_id="ts-style-002",
        pattern_type="regex",
        regex_pattern=r"==(?!=)",
        description="Using loose equality (==) instead of strict equality (===)",
        severity=Severity.LOW,
        dimension=ReviewDimension.STYLE,
        suggestion="Use === and !== for strict equality comparisons",
        confidence=0.85,
    ),

    # ── TypeScript / JavaScript Correctness Patterns ──
    ReviewPattern(
        pattern_id="ts-corr-001",
        pattern_type="regex",
        regex_pattern=r"Promise\.all\(.*\.map\(async",
        description="Using async callback with .map() inside Promise.all() without proper error handling",
        severity=Severity.MEDIUM,
        dimension=ReviewDimension.CORRECTNESS,
        suggestion="Wrap in try/catch or use Promise.allSettled() for partial failure tolerance",
        confidence=0.80,
    ),
    ReviewPattern(
        pattern_id="ts-corr-002",
        pattern_type="regex",
        regex_pattern=r"^\s*const\s+\w+\s*=\s*\w+\.map\(.*=>\s*\w+\s*$",
        description="Array.map() used without return value or side effects; consider .forEach() or .filter()",
        severity=Severity.INFO,
        dimension=ReviewDimension.CORRECTNESS,
        suggestion="Use .forEach() for side effects, .map() for transformations, .filter() for filtering",
        confidence=0.75,
    ),
]


# ═══════════════════════════════════════════════════════════
# Language Detection
# ═══════════════════════════════════════════════════════════

_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".pyx": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "c++",
    ".cc": "c++",
    ".cxx": "c++",
    ".h": "c",
    ".hpp": "c++",
    ".cs": "csharp",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
}


def _detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    if not file_path:
        return "unknown"
    for ext, lang in _LANGUAGE_MAP.items():
        if file_path.endswith(ext):
            return lang
    return "unknown"


# ═══════════════════════════════════════════════════════════
# CodeReviewEngine
# ═══════════════════════════════════════════════════════════

class CodeReviewEngine:
    """AI-native multi-perspective code review engine.

    Performs comprehensive code review across seven dimensions, using either
    LLM-based reasoning (via UnifiedAgentSystem) or rule-based pattern matching
    as a fallback simulation mode. Tracks review history, learns from successful
    reviews, and supports version comparison.
    """

    MAX_FINDINGS_PER_REVIEW = 100
    MAX_REVIEW_HISTORY = 500

    def __init__(self) -> None:
        self._reviews: dict[str, CodeReview] = {}
        self._patterns: dict[str, ReviewPattern] = {}
        self._finding_library: dict[str, ReviewFinding] = {}
        self._review_history: list[CodeReview] = []
        self._pattern_match_counts: dict[str, int] = defaultdict(int)
        self._stats = ReviewStats()
        self._unified_system = None  # Lazy-loaded UnifiedAgentSystem reference

        # Initialize built-in patterns
        for pattern in _BUILTIN_PATTERNS:
            self._patterns[pattern.pattern_id] = pattern
        self._stats.total_patterns_learned = len(self._patterns)

        logger.info(
            f"CodeReviewEngine initialized with {len(self._patterns)} built-in patterns"
        )

    # ── Public API: Single-File Review ──────────────────────────

    async def review_code(
        self,
        content: str,
        file_path: str,
        language: str = "",
        use_llm: bool = True,
    ) -> CodeReview:
        """Review a single code file.

        Args:
            content: The source code content to review.
            file_path: Path to the file being reviewed.
            language: Programming language (auto-detected if empty).
            use_llm: Whether to use LLM reasoning (falls back to pattern matching).

        Returns:
            CodeReview with all findings and summary.
        """
        if not language:
            language = _detect_language(file_path)

        review_id = f"cr-{uuid.uuid4().hex[:12]}"
        review = CodeReview(
            review_id=review_id,
            file_paths=[file_path],
            language=language,
            status=ReviewStatus.IN_PROGRESS,
        )

        logger.info(f"Starting review '{review_id}' for {file_path} ({language})")

        findings: list[ReviewFinding] = []

        # Always run pattern-based review for deterministic coverage
        pattern_findings = self._review_with_patterns(content, file_path, language)
        findings.extend(pattern_findings)

        # Attempt LLM-based review if available and requested
        if use_llm and self._unified_system is not None:
            try:
                llm_findings = await self._review_with_llm(content, file_path, language)
                findings.extend(llm_findings)
            except Exception as e:
                logger.warning(f"LLM review failed for {file_path}: {e}")

        # Deduplicate and score
        findings = self._deduplicate_findings(findings)
        findings = findings[:self.MAX_FINDINGS_PER_REVIEW]
        review.findings = findings
        review.overall_score = self._compute_overall_score(findings)
        review.summary = self._generate_summary(review)
        review.completed_at = time.time()
        review.status = ReviewStatus.COMPLETED

        # Store
        self._reviews[review_id] = review
        self._review_history.append(review)
        self._update_stats(review)

        if len(self._review_history) > self.MAX_REVIEW_HISTORY:
            self._review_history.pop(0)

        elapsed = review.completed_at - review.started_at
        logger.info(
            f"Review '{review_id}' completed: {len(findings)} findings, "
            f"score {review.overall_score:.1f}, {elapsed:.2f}s"
        )
        return review

    # ── Public API: Diff Review ─────────────────────────────────

    async def review_diff(
        self,
        diff_content: str,
        file_paths: list[str],
        language: str = "",
        use_llm: bool = True,
    ) -> CodeReview:
        """Review a diff/patch.

        Args:
            diff_content: The unified diff content to review.
            file_paths: List of files affected by the diff.
            language: Primary programming language.
            use_llm: Whether to use LLM reasoning.

        Returns:
            CodeReview with findings specific to the changed lines.
        """
        if not language and file_paths:
            language = _detect_language(file_paths[0])

        review_id = f"cr-{uuid.uuid4().hex[:12]}"
        review = CodeReview(
            review_id=review_id,
            file_paths=file_paths,
            diff_content=diff_content,
            language=language,
            status=ReviewStatus.IN_PROGRESS,
        )

        logger.info(
            f"Starting diff review '{review_id}' for {len(file_paths)} files"
        )

        findings: list[ReviewFinding] = []

        # Extract added/modified lines from diff for pattern matching
        changed_lines = self._extract_changed_lines(diff_content)
        for file_path in file_paths:
            for line_info in changed_lines:
                if line_info["file"] == file_path or not line_info["file"]:
                    pattern_findings = self._review_with_patterns(
                        line_info["content"], file_path, language
                    )
                    for f in pattern_findings:
                        f.line_start = line_info.get("line_number", f.line_start)
                        f.line_end = line_info.get("line_number", f.line_end)
                    findings.extend(pattern_findings)

        # LLM-based diff review
        if use_llm and self._unified_system is not None:
            try:
                llm_findings = await self._review_diff_with_llm(
                    diff_content, file_paths, language
                )
                findings.extend(llm_findings)
            except Exception as e:
                logger.warning(f"LLM diff review failed: {e}")

        findings = self._deduplicate_findings(findings)
        findings = findings[:self.MAX_FINDINGS_PER_REVIEW]
        review.findings = findings
        review.overall_score = self._compute_overall_score(findings)
        review.summary = self._generate_summary(review)
        review.completed_at = time.time()
        review.status = ReviewStatus.COMPLETED

        self._reviews[review_id] = review
        self._review_history.append(review)
        self._update_stats(review)

        if len(self._review_history) > self.MAX_REVIEW_HISTORY:
            self._review_history.pop(0)

        logger.info(
            f"Diff review '{review_id}' completed: {len(findings)} findings"
        )
        return review

    # ── Public API: Batch Review ────────────────────────────────

    async def batch_review(
        self,
        files: list[dict[str, str]],
        use_llm: bool = True,
    ) -> list[CodeReview]:
        """Review multiple files in parallel.

        Args:
            files: List of dicts with 'content' and 'file_path' keys.
            use_llm: Whether to use LLM reasoning.

        Returns:
            List of CodeReview results, one per file.
        """
        if not files:
            return []

        logger.info(f"Starting batch review of {len(files)} files")

        tasks = [
            self.review_code(
                content=f.get("content", ""),
                file_path=f.get("file_path", "unknown"),
                language=f.get("language", ""),
                use_llm=use_llm,
            )
            for f in files
        ]

        reviews = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[CodeReview] = []
        for i, result in enumerate(reviews):
            if isinstance(result, Exception):
                logger.error(f"Batch review failed for {files[i].get('file_path', 'unknown')}: {result}")
                continue
            results.append(result)

        logger.info(
            f"Batch review complete: {len(results)}/{len(files)} succeeded, "
            f"total findings: {sum(len(r.findings) for r in results)}"
        )
        return results

    # ── Public API: Commentary Generation ───────────────────────

    async def generate_review_commentary(
        self,
        findings: list[ReviewFinding],
    ) -> str:
        """Generate human-readable commentary from review findings.

        Args:
            findings: List of review findings to synthesize.

        Returns:
            A formatted commentary string suitable for PR comments.
        """
        if not findings:
            return "No issues found. Code looks good!"

        # Group findings by severity
        by_severity: dict[Severity, list[ReviewFinding]] = defaultdict(list)
        for f in findings:
            by_severity[f.severity].append(f)

        lines: list[str] = []
        lines.append("## Code Review Commentary\n")

        # Summary header
        critical = len(by_severity.get(Severity.CRITICAL, []))
        high = len(by_severity.get(Severity.HIGH, []))
        medium = len(by_severity.get(Severity.MEDIUM, []))
        low = len(by_severity.get(Severity.LOW, []))
        info = len(by_severity.get(Severity.INFO, []))

        lines.append(
            f"**Summary:** {len(findings)} findings — "
            f"{critical} critical, {high} high, {medium} medium, "
            f"{low} low, {info} info\n"
        )

        # Group by dimension for organized output
        by_dimension: dict[ReviewDimension, list[ReviewFinding]] = defaultdict(list)
        for f in findings:
            by_dimension[f.dimension].append(f)

        for dimension in ReviewDimension:
            dim_findings = by_dimension.get(dimension, [])
            if not dim_findings:
                continue

            lines.append(f"### {dimension.value.title()}\n")
            for f in sorted(dim_findings, key=lambda x: x.severity.weight, reverse=True):
                severity_icon = {
                    Severity.CRITICAL: "🔴",
                    Severity.HIGH: "🟠",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🟢",
                    Severity.INFO: "🔵",
                }.get(f.severity, "⚪")

                lines.append(
                    f"- {severity_icon} **[{f.severity.value.upper()}]** "
                    f"`{f.file_path}:{f.line_start}-{f.line_end}`: "
                    f"{f.title}"
                )
                lines.append(f"  - {f.description}")
                if f.suggestion:
                    lines.append(f"  - **Suggestion:** {f.suggestion}")
                if f.code_snippet:
                    lines.append(f"  - ```\n{f.code_snippet.strip()}\n    ```")
                lines.append("")

        # LLM-enhanced commentary if available
        if self._unified_system is not None:
            try:
                enhanced = await self._generate_llm_commentary(findings)
                if enhanced:
                    lines.append("\n---\n")
                    lines.append("### AI-Enhanced Analysis\n")
                    lines.append(enhanced)
            except Exception as e:
                logger.warning(f"LLM commentary generation failed: {e}")

        return "\n".join(lines)

    # ── Public API: Version Comparison ──────────────────────────

    async def compare_versions(
        self,
        old_code: str,
        new_code: str,
        file_path: str,
        language: str = "",
    ) -> CodeReview:
        """Compare two versions of code and generate a review of changes.

        Args:
            old_code: The previous version of the code.
            new_code: The new version of the code.
            file_path: Path to the file being compared.
            language: Programming language (auto-detected if empty).

        Returns:
            CodeReview with findings specific to the changes between versions.
        """
        if not language:
            language = _detect_language(file_path)

        review_id = f"cr-{uuid.uuid4().hex[:12]}"
        review = CodeReview(
            review_id=review_id,
            file_paths=[file_path],
            language=language,
            status=ReviewStatus.IN_PROGRESS,
        )

        logger.info(f"Starting version comparison '{review_id}' for {file_path}")

        # Generate a simple diff
        diff_lines = self._generate_simple_diff(old_code, new_code)
        diff_content = "\n".join(diff_lines)

        findings: list[ReviewFinding] = []

        # Review the new code
        new_findings = self._review_with_patterns(new_code, file_path, language)
        findings.extend(new_findings)

        # Review only changed sections
        added_lines = self._extract_added_lines(diff_lines)
        if added_lines:
            added_content = "\n".join(added_lines)
            added_findings = self._review_with_patterns(added_content, file_path, language)
            for f in added_findings:
                f.title = f"[Changed Code] {f.title}"
            findings.extend(added_findings)

        # LLM-based comparison if available
        if self._unified_system is not None:
            try:
                llm_findings = await self._compare_with_llm(
                    old_code, new_code, file_path, language
                )
                findings.extend(llm_findings)
            except Exception as e:
                logger.warning(f"LLM version comparison failed: {e}")

        findings = self._deduplicate_findings(findings)
        findings = findings[:self.MAX_FINDINGS_PER_REVIEW]
        review.findings = findings
        review.diff_content = diff_content
        review.overall_score = self._compute_overall_score(findings)
        review.summary = self._generate_summary(review)
        review.completed_at = time.time()
        review.status = ReviewStatus.COMPLETED

        self._reviews[review_id] = review
        self._review_history.append(review)
        self._stats.total_version_comparisons += 1
        self._update_stats(review)

        logger.info(
            f"Version comparison '{review_id}': {len(findings)} findings"
        )
        return review

    # ── Public API: Pattern Learning ────────────────────────────

    def learn_from_patterns(
        self,
        successful_reviews: list[CodeReview],
    ) -> int:
        """Learn review patterns from history of successful reviews.

        Analyzes findings from reviews that were approved or had high scores,
        extracts recurring patterns, and adds them to the pattern library.

        Args:
            successful_reviews: Reviews that were approved or scored well.

        Returns:
            Number of new patterns learned.
        """
        if not successful_reviews:
            return 0

        new_patterns = 0
        finding_snippets: dict[str, int] = defaultdict(int)

        # Collect code snippets from findings
        for review in successful_reviews:
            for finding in review.findings:
                if finding.code_snippet and finding.confidence > 0.7:
                    key = finding.code_snippet.strip()[:120]
                    finding_snippets[key] += 1

        # Promote recurring snippets to patterns
        for snippet, count in finding_snippets.items():
            if count >= 2:
                # Check if a similar pattern already exists
                pattern_key = f"learned-{uuid.uuid4().hex[:8]}"
                if not self._pattern_exists_for_snippet(snippet):
                    escaped = re.escape(snippet.strip())
                    pattern = ReviewPattern(
                        pattern_id=pattern_key,
                        pattern_type="regex",
                        regex_pattern=escaped,
                        description=f"Learned pattern (seen {count}x): {snippet[:80]}",
                        severity=Severity.MEDIUM,
                        dimension=ReviewDimension.MAINTAINABILITY,
                        occurrence_count=count,
                        suggestion="Review this pattern for potential issues",
                        confidence=0.6,
                    )
                    self._patterns[pattern_key] = pattern
                    new_patterns += 1

        self._stats.total_patterns_learned += new_patterns
        logger.info(
            f"Pattern learning: {new_patterns} new patterns from "
            f"{len(successful_reviews)} reviews"
        )
        return new_patterns

    # ── Public API: Statistics ──────────────────────────────────

    def get_review_stats(self) -> dict[str, Any]:
        """Get comprehensive review statistics.

        Returns:
            Dictionary with review statistics and trend data.
        """
        # Update average score
        if self._review_history:
            scores = [r.overall_score for r in self._review_history]
            self._stats.average_score = sum(scores) / len(scores)

        # Update average review time
        completed = [
            r for r in self._review_history
            if r.completed_at > 0 and r.started_at > 0
        ]
        if completed:
            avg_time = sum(
                (r.completed_at - r.started_at) * 1000 for r in completed
            ) / len(completed)
            self._stats.average_review_time_ms = avg_time

        # Recent trend
        recent = self._review_history[-20:]
        trend = {
            "recent_reviews": len(recent),
            "recent_findings_avg": sum(len(r.findings) for r in recent) / max(len(recent), 1),
            "recent_score_avg": sum(r.overall_score for r in recent) / max(len(recent), 1),
        }

        return {
            **self._stats.to_dict(),
            "active_patterns": len(self._patterns),
            "trend": trend,
            "top_patterns": sorted(
                [
                    {
                        "pattern_id": p.pattern_id,
                        "description": p.description,
                        "occurrences": p.occurrence_count,
                        "dimension": p.dimension.value,
                        "severity": p.severity.value,
                    }
                    for p in self._patterns.values()
                    if p.occurrence_count > 0
                ],
                key=lambda x: x["occurrences"],
                reverse=True,
            )[:10],
        }

    # ── Public API: Review Management ───────────────────────────

    def get_review(self, review_id: str) -> CodeReview | None:
        """Retrieve a specific review by ID."""
        return self._reviews.get(review_id)

    def update_review_status(self, review_id: str, status: ReviewStatus) -> bool:
        """Update the status of a review (e.g., approve/reject)."""
        review = self._reviews.get(review_id)
        if not review:
            return False
        review.status = status
        logger.info(f"Review '{review_id}' status updated to {status.value}")
        return True

    def get_reviews_by_file(self, file_path: str, limit: int = 20) -> list[CodeReview]:
        """Get review history for a specific file."""
        matches = [
            r for r in self._review_history
            if file_path in r.file_paths
        ]
        return sorted(matches, key=lambda r: r.started_at, reverse=True)[:limit]

    def set_unified_system(self, unified_system: Any) -> None:
        """Inject the UnifiedAgentSystem for LLM-based reasoning."""
        self._unified_system = unified_system
        logger.info("UnifiedAgentSystem linked to CodeReviewEngine")

    # ── Internal: Pattern-Based Review ──────────────────────────

    def _review_with_patterns(
        self,
        content: str,
        file_path: str,
        language: str,
    ) -> list[ReviewFinding]:
        """Apply all relevant patterns to code content and generate findings."""
        findings: list[ReviewFinding] = []

        for pattern in self._patterns.values():
            if not self._pattern_applies_to(pattern, language):
                continue

            try:
                matches = list(re.finditer(pattern.regex_pattern, content, re.MULTILINE))
            except re.error:
                logger.debug(f"Invalid regex in pattern {pattern.pattern_id}")
                continue

            for match in matches:
                line_start = content[:match.start()].count("\n") + 1
                line_end = content[:match.end()].count("\n") + 1

                snippet = content[
                    max(0, match.start() - 20):min(len(content), match.end() + 20)
                ]

                finding = ReviewFinding(
                    finding_id=f"f-{uuid.uuid4().hex[:8]}",
                    dimension=pattern.dimension,
                    severity=pattern.severity,
                    line_start=line_start,
                    line_end=line_end,
                    file_path=file_path,
                    title=pattern.description,
                    description=pattern.description,
                    suggestion=pattern.suggestion,
                    code_snippet=snippet.strip(),
                    confidence=pattern.confidence,
                )
                findings.append(finding)

                # Update pattern stats
                pattern.occurrence_count += 1
                pattern.last_matched_at = time.time()
                self._pattern_match_counts[pattern.pattern_id] = (
                    self._pattern_match_counts[pattern.pattern_id] + 1
                )

        return findings

    def _pattern_applies_to(self, pattern: ReviewPattern, language: str) -> bool:
        """Check if a pattern is relevant for the given language."""
        pattern_lang = pattern.pattern_id.split("-")[0] if "-" in pattern.pattern_id else ""
        language_map = {
            "py": "python",
            "ts": "typescript",
            "js": "javascript",
        }
        target_lang = language_map.get(pattern_lang, pattern_lang)
        # ts patterns apply to both typescript and javascript
        if pattern_lang == "ts" and language in ("typescript", "javascript"):
            return True
        return (
            not pattern_lang
            or target_lang == language
            or language == "unknown"
        )

    # ── Internal: LLM-Based Review ──────────────────────────────

    async def _review_with_llm(
        self,
        content: str,
        file_path: str,
        language: str,
    ) -> list[ReviewFinding]:
        """Use the UnifiedAgentSystem to perform deep reasoning review."""
        if self._unified_system is None:
            return []

        prompt = self._build_review_prompt(content, file_path, language)
        try:
            result = await self._unified_system.run(
                content=prompt,
                source="code_review",
                context={"file_path": file_path, "language": language},
            )
            return self._parse_llm_findings(result, file_path)
        except Exception as e:
            logger.error(f"LLM review failed: {e}")
            return []

    async def _review_diff_with_llm(
        self,
        diff_content: str,
        file_paths: list[str],
        language: str,
    ) -> list[ReviewFinding]:
        """Use LLM to review a diff."""
        if self._unified_system is None:
            return []

        prompt = (
            f"Review the following code diff for {language} code. "
            f"Analyze for security issues, bugs, performance problems, "
            f"style violations, and architectural concerns.\n\n"
            f"Files: {', '.join(file_paths)}\n\n"
            f"```diff\n{diff_content[:8000]}\n```\n\n"
            f"Provide findings as a JSON list with fields: "
            f"dimension, severity, line_start, title, description, suggestion."
        )

        try:
            result = await self._unified_system.run(
                content=prompt,
                source="code_review_diff",
                context={"file_paths": file_paths, "language": language},
            )
            return self._parse_llm_findings(result, file_paths[0] if file_paths else "unknown")
        except Exception as e:
            logger.error(f"LLM diff review failed: {e}")
            return []

    async def _compare_with_llm(
        self,
        old_code: str,
        new_code: str,
        file_path: str,
        language: str,
    ) -> list[ReviewFinding]:
        """Use LLM to compare two code versions."""
        if self._unified_system is None:
            return []

        prompt = (
            f"Compare the following two versions of {language} code and identify "
            f"improvements, regressions, and issues introduced in the new version.\n\n"
            f"### Old Version:\n```{language}\n{old_code[:4000]}\n```\n\n"
            f"### New Version:\n```{language}\n{new_code[:4000]}\n```\n\n"
            f"Provide findings as a JSON list with fields: "
            f"dimension, severity, title, description, suggestion."
        )

        try:
            result = await self._unified_system.run(
                content=prompt,
                source="code_review_compare",
                context={"file_path": file_path, "language": language},
            )
            return self._parse_llm_findings(result, file_path)
        except Exception as e:
            logger.error(f"LLM version comparison failed: {e}")
            return []

    async def _generate_llm_commentary(
        self,
        findings: list[ReviewFinding],
    ) -> str:
        """Generate enhanced commentary using LLM."""
        if self._unified_system is None:
            return ""

        findings_text = "\n".join(
            f"- [{f.severity.value}] {f.dimension.value}: {f.title} — {f.suggestion}"
            for f in findings[:20]
        )

        prompt = (
            f"Based on these code review findings, provide a concise, actionable "
            f"summary in 2-3 paragraphs that prioritizes the most critical issues "
            f"and suggests an overall improvement strategy:\n\n{findings_text}"
        )

        try:
            result = await self._unified_system.run(
                content=prompt,
                source="code_review_commentary",
            )
            return result.get("output", "") if isinstance(result, dict) else str(result)
        except Exception:
            return ""

    def _build_review_prompt(
        self,
        content: str,
        file_path: str,
        language: str,
    ) -> str:
        """Build a structured prompt for LLM code review."""
        return (
            f"Perform a comprehensive code review of the following {language} code "
            f"from file '{file_path}'. Analyze across these dimensions:\n"
            f"- Security: vulnerabilities, unsafe practices, data exposure\n"
            f"- Performance: inefficient algorithms, resource leaks, N+1 queries\n"
            f"- Style: naming conventions, formatting, idiomatic usage\n"
            f"- Architecture: design patterns, SOLID principles, coupling/cohesion\n"
            f"- Correctness: bugs, edge cases, error handling, type safety\n"
            f"- Maintainability: readability, documentation, complexity\n"
            f"- Testing: test coverage gaps, untestable code, missing assertions\n\n"
            f"```{language}\n{content[:12000]}\n```\n\n"
            f"Provide findings as a JSON array with fields: "
            f"dimension, severity, line_start, title, description, suggestion."
        )

    def _parse_llm_findings(
        self,
        result: Any,
        file_path: str,
    ) -> list[ReviewFinding]:
        """Parse LLM response into ReviewFinding objects."""
        findings: list[ReviewFinding] = []

        output = ""
        if isinstance(result, dict):
            output = result.get("output", "")
            if isinstance(output, str):
                pass
            elif isinstance(output, list):
                items = output
            else:
                return findings
        else:
            output = str(result)

        # Try to extract JSON from the response
        import json
        try:
            # Find JSON array in the output
            json_match = re.search(r"\[.*\]", output, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group())
            elif isinstance(result, dict) and isinstance(result.get("output"), list):
                items = result["output"]
            else:
                return findings
        except (json.JSONDecodeError, TypeError):
            return findings

        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                finding = ReviewFinding(
                    finding_id=f"f-{uuid.uuid4().hex[:8]}",
                    dimension=ReviewDimension(item.get("dimension", "maintainability")),
                    severity=Severity(item.get("severity", "low")),
                    line_start=item.get("line_start", 1),
                    line_end=item.get("line_end", item.get("line_start", 1)),
                    file_path=file_path,
                    title=item.get("title", "Untitled finding"),
                    description=item.get("description", ""),
                    suggestion=item.get("suggestion", ""),
                    code_snippet=item.get("code_snippet", ""),
                    confidence=item.get("confidence", 0.7),
                )
                findings.append(finding)
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping malformed finding: {e}")
                continue

        return findings

    # ── Internal: Diff Utilities ────────────────────────────────

    def _extract_changed_lines(self, diff_content: str) -> list[dict[str, Any]]:
        """Extract added/modified lines from unified diff."""
        changed: list[dict[str, Any]] = []
        current_file = ""
        current_line = 0

        for line in diff_content.split("\n"):
            if line.startswith("+++ "):
                current_file = line[4:].strip()
                continue
            if line.startswith("@@ "):
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                m = re.search(r"\+(\d+)(?:,(\d+))?", line)
                if m:
                    current_line = int(m.group(1))
                continue
            if line.startswith("+") and not line.startswith("+++"):
                changed.append({
                    "file": current_file,
                    "content": line[1:],
                    "line_number": current_line,
                })
                current_line += 1
            elif not line.startswith("-") and not line.startswith("---"):
                current_line += 1

        return changed

    def _extract_added_lines(self, diff_lines: list[str]) -> list[str]:
        """Extract added lines from a simple diff."""
        added: list[str] = []
        for line in diff_lines:
            if line.startswith("+ ") or line.startswith("+") and not line.startswith("+++"):
                added.append(line[1:].lstrip() if line.startswith("+ ") else line[1:])
        return added

    def _generate_simple_diff(self, old_code: str, new_code: str) -> list[str]:
        """Generate a simple line-by-line diff between two code versions."""
        old_lines = old_code.split("\n")
        new_lines = new_code.split("\n")

        diff_lines: list[str] = []
        max_len = max(len(old_lines), len(new_lines))
        i = 0

        while i < max_len:
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None

            if old_line == new_line:
                if old_line is not None:
                    diff_lines.append(f"  {old_line}")
            else:
                if old_line is not None:
                    diff_lines.append(f"- {old_line}")
                if new_line is not None:
                    diff_lines.append(f"+ {new_line}")
            i += 1

        return diff_lines

    # ── Internal: Scoring & Summarization ───────────────────────

    def _compute_overall_score(self, findings: list[ReviewFinding]) -> float:
        """Compute an overall quality score (0-100) based on findings.

        Lower severity/quantity of findings → higher score.
        """
        if not findings:
            return 100.0

        penalty = sum(
            f.severity.weight * f.confidence
            for f in findings
        )
        # Normalize: cap at 100 base penalty, then scale to 0-100
        normalized = min(penalty, 100.0)
        return round(100.0 - normalized, 1)

    def _generate_summary(self, review: CodeReview) -> str:
        """Generate a human-readable summary of the review."""
        if not review.findings:
            return "No issues found. Code appears clean and well-structured."

        parts: list[str] = []

        by_severity = {
            s: len([f for f in review.findings if f.severity == s])
            for s in Severity
        }
        parts.append(
            f"Found {len(review.findings)} issues: "
            f"{by_severity[Severity.CRITICAL]} critical, "
            f"{by_severity[Severity.HIGH]} high, "
            f"{by_severity[Severity.MEDIUM]} medium, "
            f"{by_severity[Severity.LOW]} low, "
            f"{by_severity[Severity.INFO]} informational."
        )

        # Top dimension
        by_dim: dict[ReviewDimension, int] = defaultdict(int)
        for f in review.findings:
            by_dim[f.dimension] += 1
        top_dim = max(by_dim, key=by_dim.get) if by_dim else None
        if top_dim:
            parts.append(
                f"Most findings in {top_dim.value} ({by_dim[top_dim]} issues)."
            )

        parts.append(f"Overall score: {review.overall_score:.1f}/100")
        return " ".join(parts)

    def _deduplicate_findings(
        self,
        findings: list[ReviewFinding],
    ) -> list[ReviewFinding]:
        """Remove duplicate or near-duplicate findings."""
        seen: set[str] = set()
        unique: list[ReviewFinding] = []

        for f in findings:
            key = (
                f"{f.dimension.value}:{f.severity.value}:"
                f"{f.line_start}:{f.title[:60]}"
            )
            if key not in seen:
                seen.add(key)
                unique.append(f)
            else:
                # Boost confidence of existing finding
                for existing in unique:
                    existing_key = (
                        f"{existing.dimension.value}:{existing.severity.value}:"
                        f"{existing.line_start}:{existing.title[:60]}"
                    )
                    if existing_key == key:
                        existing.confidence = max(existing.confidence, f.confidence)
                        break

        return unique

    def _pattern_exists_for_snippet(self, snippet: str) -> bool:
        """Check if a similar pattern already exists for the given snippet."""
        try:
            for pattern in self._patterns.values():
                if re.search(pattern.regex_pattern, snippet, re.MULTILINE | re.IGNORECASE):
                    return True
        except re.error:
            pass
        return False

    # ── Internal: Statistics Tracking ───────────────────────────

    def _update_stats(self, review: CodeReview) -> None:
        """Update internal statistics with a completed review."""
        self._stats.total_reviews += 1
        self._stats.total_findings += len(review.findings)

        for f in review.findings:
            self._stats.by_severity[f.severity.value] += 1
            self._stats.by_dimension[f.dimension.value] += 1

        if review.language:
            self._stats.by_language[review.language] += 1


# ═══════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════

code_review_engine = CodeReviewEngine()