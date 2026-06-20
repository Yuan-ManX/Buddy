"""
Buddy Agent Reflection Engine - Self-reflection and self-correction loop.

Provides the agent with the ability to examine its own outputs, detect
inconsistencies and errors, and apply corrective measures. Implements
a continuous self-improvement cycle through structured reflection.

Key capabilities:
- Output quality assessment with multi-dimensional scoring
- Error detection and classification (factual, logical, stylistic)
- Self-correction pipeline with revision tracking
- Reflection history with learning extraction
- Confidence calibration based on past performance
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ReflectionDimension(str, Enum):
    """Dimensions along which output quality is assessed."""
    FACTUAL_ACCURACY = "factual_accuracy"
    LOGICAL_COHERENCE = "logical_coherence"
    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"
    CLARITY = "clarity"
    ACTIONABILITY = "actionability"
    SAFETY = "safety"
    CONCISENESS = "conciseness"


class ErrorCategory(str, Enum):
    """Categories of errors detected during reflection."""
    FACTUAL_ERROR = "factual_error"
    LOGICAL_FALLACY = "logical_fallacy"
    INCOMPLETE_ANSWER = "incomplete_answer"
    OFF_TOPIC = "off_topic"
    AMBIGUOUS = "ambiguous"
    UNSAFE = "unsafe"
    VERBOSE = "verbose"
    HALLUCINATION = "hallucination"


class ReflectionStatus(str, Enum):
    """Status of a reflection session."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    REFLECTING = "reflecting"
    CORRECTING = "correcting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QualityScore:
    """Multi-dimensional quality assessment of an output."""
    dimension: ReflectionDimension
    score: float  # 0.0 to 1.0
    reasoning: str
    suggestions: list[str] = field(default_factory=list)


@dataclass
class DetectedError:
    """An error detected during reflection."""
    error_id: str
    category: ErrorCategory
    description: str
    location: str  # Which part of the output
    severity: float  # 0.0 to 1.0
    suggested_fix: str
    corrected: bool = False


@dataclass
class ReflectionRecord:
    """A single reflection session record."""
    reflection_id: str
    session_id: str
    agent_id: str
    original_output: str
    status: ReflectionStatus = ReflectionStatus.PENDING
    quality_scores: list[QualityScore] = field(default_factory=list)
    detected_errors: list[DetectedError] = field(default_factory=list)
    corrected_output: str = ""
    improvement_summary: str = ""
    confidence_before: float = 1.0
    confidence_after: float = 1.0
    revision_count: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    @property
    def overall_score(self) -> float:
        if not self.quality_scores:
            return 0.0
        return sum(s.score for s in self.quality_scores) / len(self.quality_scores)

    @property
    def error_count(self) -> int:
        return len(self.detected_errors)


class AgentReflectionEngine:
    """Self-reflection engine for Buddy agents.

    Enables agents to critically examine their own outputs, identify
    weaknesses, and apply corrections. Maintains a reflection history
    for continuous learning and confidence calibration.
    """

    def __init__(self):
        self._reflections: dict[str, ReflectionRecord] = {}
        self._history: dict[str, list[ReflectionRecord]] = {}  # agent_id -> records
        self._confidence_scores: dict[str, float] = {}  # agent_id -> calibrated confidence
        self._total_reflections = 0
        self._total_corrections = 0

    def start_reflection(
        self,
        agent_id: str,
        original_output: str,
        session_id: str | None = None,
    ) -> ReflectionRecord:
        """Begin a new reflection session on an agent output."""
        reflection_id = f"refl-{uuid.uuid4().hex[:12]}"
        record = ReflectionRecord(
            reflection_id=reflection_id,
            session_id=session_id or f"sess-{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            original_output=original_output,
            status=ReflectionStatus.ANALYZING,
        )
        self._reflections[reflection_id] = record

        if agent_id not in self._history:
            self._history[agent_id] = []
        self._history[agent_id].append(record)
        self._total_reflections += 1

        return record

    def assess_quality(
        self,
        reflection_id: str,
        scores: list[QualityScore],
    ) -> ReflectionRecord | None:
        """Record quality assessment scores for a reflection."""
        record = self._reflections.get(reflection_id)
        if not record:
            return None
        record.quality_scores = scores
        record.status = ReflectionStatus.REFLECTING
        return record

    def detect_error(
        self,
        reflection_id: str,
        category: ErrorCategory,
        description: str,
        location: str = "",
        severity: float = 0.5,
        suggested_fix: str = "",
    ) -> DetectedError | None:
        """Register a detected error in a reflection session."""
        record = self._reflections.get(reflection_id)
        if not record:
            return None

        error = DetectedError(
            error_id=f"err-{uuid.uuid4().hex[:12]}",
            category=category,
            description=description,
            location=location,
            severity=severity,
            suggested_fix=suggested_fix,
        )
        record.detected_errors.append(error)
        return error

    def apply_correction(
        self,
        reflection_id: str,
        corrected_output: str,
        improvement_summary: str = "",
        mark_errors_corrected: bool = True,
    ) -> ReflectionRecord | None:
        """Apply the corrected output and complete the reflection."""
        record = self._reflections.get(reflection_id)
        if not record:
            return None

        record.corrected_output = corrected_output
        record.improvement_summary = improvement_summary
        record.revision_count += 1
        record.status = ReflectionStatus.CORRECTING

        if mark_errors_corrected:
            for error in record.detected_errors:
                error.corrected = True

        # Update confidence calibration
        if record.error_count > 0:
            self._update_confidence(record.agent_id, record.overall_score)

        self._total_corrections += 1
        record.completed_at = time.time()
        record.status = ReflectionStatus.COMPLETED
        return record

    def get_reflection(self, reflection_id: str) -> ReflectionRecord | None:
        """Retrieve a reflection record by ID."""
        return self._reflections.get(reflection_id)

    def get_history(self, agent_id: str, limit: int = 20) -> list[ReflectionRecord]:
        """Get reflection history for an agent."""
        records = self._history.get(agent_id, [])
        return sorted(records, key=lambda r: r.created_at, reverse=True)[:limit]

    def get_confidence(self, agent_id: str) -> float:
        """Get calibrated confidence score for an agent."""
        return self._confidence_scores.get(agent_id, 1.0)

    def get_stats(self, agent_id: str | None = None) -> dict:
        """Get reflection statistics."""
        if agent_id:
            records = self._history.get(agent_id, [])
            total_errors = sum(r.error_count for r in records)
            avg_score = (
                sum(r.overall_score for r in records) / len(records)
                if records else 0.0
            )
            return {
                "agent_id": agent_id,
                "total_reflections": len(records),
                "total_errors": total_errors,
                "total_corrections": sum(1 for r in records if r.corrected_output),
                "average_quality_score": round(avg_score, 3),
                "confidence": self.get_confidence(agent_id),
                "error_categories": self._count_error_categories(records),
            }

        return {
            "total_reflections": self._total_reflections,
            "total_corrections": self._total_corrections,
            "active_agents": len(self._history),
            "agent_stats": {
                aid: self.get_stats(aid) for aid in self._history
            },
        }

    def _update_confidence(self, agent_id: str, quality_score: float) -> None:
        """Update confidence calibration using exponential moving average."""
        current = self._confidence_scores.get(agent_id, 1.0)
        alpha = 0.1  # Smoothing factor
        self._confidence_scores[agent_id] = alpha * quality_score + (1 - alpha) * current

    def _count_error_categories(
        self, records: list[ReflectionRecord]
    ) -> dict[str, int]:
        """Count errors by category across reflection records."""
        counts: dict[str, int] = {}
        for record in records:
            for error in record.detected_errors:
                cat = error.category.value
                counts[cat] = counts.get(cat, 0) + 1
        return counts


# Global singleton
reflection_engine = AgentReflectionEngine()