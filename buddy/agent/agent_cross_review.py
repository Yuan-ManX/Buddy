"""
Buddy Agent Cross-Review - Cross-Model Review System for Quality Assurance.

Implements a cross-model review system where one agent reviews another agent's
work for quality assurance. Different review strategies can be selected to tune
the depth and tone of the review, and review quality is tracked over time via
reviewer profiles, scores, and confidence metrics.

Key capabilities:
- Multiple review strategies (peer, adversarial, checklist, rubric, diff analysis)
- Reviewer registration with specialties and trust scoring
- Review session lifecycle (pending -> in progress -> completed / disputed / resolved)
- Structured review reports with verdicts, items, scores, and confidence
- Dispute and resolution workflow with multi-round support
- Aggregate statistics for monitoring review quality over time
- Singleton accessor for shared access across the agent runtime
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("buddy.cross_review")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class ReviewStrategy(str, Enum):
    """Strategy guiding how a cross-model review is conducted."""
    PEER_REVIEW = "peer_review"
    ADVERSARIAL = "adversarial"
    CHECKLIST = "checklist"
    RUBRIC_BASED = "rubric_based"
    DIFF_ANALYSIS = "diff_analysis"


class ReviewStatus(str, Enum):
    """Lifecycle status of a review session."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    RESOLVED = "resolved"


class SeverityLevel(str, Enum):
    """Severity level assigned to an individual review item."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def weight(self) -> int:
        """Numeric weight used for severity-based scoring."""
        return {
            SeverityLevel.CRITICAL: 100,
            SeverityLevel.HIGH: 50,
            SeverityLevel.MEDIUM: 25,
            SeverityLevel.LOW: 10,
            SeverityLevel.INFO: 0,
        }[self]


class ReviewVerdict(str, Enum):
    """Overall verdict issued by a reviewer for an artifact."""
    APPROVE = "approve"
    APPROVE_WITH_CHANGES = "approve_with_changes"
    REJECT = "reject"
    NEEDS_DISCUSSION = "needs_discussion"


# ═══════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════

@dataclass
class ReviewItem:
    """A single finding produced during a review."""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    severity: SeverityLevel = SeverityLevel.INFO
    category: str = "general"
    line_reference: str | None = None
    suggestion: str | None = None
    resolved: bool = False


@dataclass
class ReviewReport:
    """The structured report produced by a reviewer for a review session."""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    review_id: str = ""
    reviewer_id: str = ""
    reviewee_id: str = ""
    verdict: ReviewVerdict = ReviewVerdict.NEEDS_DISCUSSION
    summary: str = ""
    items: list[ReviewItem] = field(default_factory=list)
    score: float = 0.5
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)


@dataclass
class ReviewSession:
    """A single cross-model review session over an artifact."""
    review_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reviewer_id: str = ""
    reviewee_id: str = ""
    artifact_type: str = ""
    artifact_content: str = ""
    artifact_metadata: dict = field(default_factory=dict)
    strategy: ReviewStrategy = ReviewStrategy.PEER_REVIEW
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    report: ReviewReport | None = None
    round_number: int = 1


@dataclass
class ReviewerProfile:
    """Profile tracking a reviewer's history and trustworthiness."""
    reviewer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    specialties: list[str] = field(default_factory=list)
    total_reviews: int = 0
    avg_score_given: float = 0.5
    trust_score: float = 0.5
    created_at: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════
# Main class
# ═══════════════════════════════════════════════════════════

class AgentCrossReview:
    """Coordinates cross-model reviews and tracks review quality over time."""

    MAX_SESSIONS: int = 1000
    MAX_ROUNDS: int = 5
    MIN_TRUST_SCORE: float = 0.5

    def __init__(self) -> None:
        self._reviewers: dict[str, ReviewerProfile] = {}
        self._sessions: dict[str, ReviewSession] = {}
        self._dispute_reasons: dict[str, list[str]] = {}
        self._resolution_notes: dict[str, str] = {}
        self._total_sessions: int = 0
        self._total_reports: int = 0

    # ── Reviewer management ──

    def register_reviewer(
        self,
        name: str,
        specialties: list[str] | None = None,
    ) -> ReviewerProfile:
        """Register a new reviewer and return its profile.

        Args:
            name: Human-readable name of the reviewer.
            specialties: Optional list of specialty tags for the reviewer.

        Returns:
            The newly created ReviewerProfile.
        """
        profile = ReviewerProfile(
            name=name,
            specialties=list(specialties) if specialties else [],
            trust_score=self.MIN_TRUST_SCORE,
        )
        self._reviewers[profile.reviewer_id] = profile
        logger.info("Registered reviewer %s (%s)", profile.reviewer_id, name)
        return profile

    def update_reviewer(
        self,
        reviewer_id: str,
        name: str | None = None,
        specialties: list[str] | None = None,
        trust_score: float | None = None,
    ) -> ReviewerProfile | None:
        """Update an existing reviewer profile.

        Args:
            reviewer_id: Identifier of the reviewer to update.
            name: Optional new name.
            specialties: Optional replacement list of specialties.
            trust_score: Optional new trust score (clamped to [0, 1]).

        Returns:
            The updated ReviewerProfile, or None if the reviewer was not found.
        """
        profile = self._reviewers.get(reviewer_id)
        if profile is None:
            return None
        if name is not None:
            profile.name = name
        if specialties is not None:
            profile.specialties = list(specialties)
        if trust_score is not None:
            profile.trust_score = max(0.0, min(1.0, float(trust_score)))
        return profile

    def get_reviewer(self, reviewer_id: str) -> ReviewerProfile | None:
        """Return a reviewer profile by id, or None if not found."""
        return self._reviewers.get(reviewer_id)

    def list_reviewers(self, specialty: str | None = None) -> list[ReviewerProfile]:
        """List reviewer profiles, optionally filtered by specialty.

        Args:
            specialty: Optional specialty tag to filter by.

        Returns:
            List of matching ReviewerProfile objects.
        """
        if specialty is None:
            return list(self._reviewers.values())
        return [
            p for p in self._reviewers.values()
            if specialty in p.specialties
        ]

    # ── Review session lifecycle ──

    def create_review(
        self,
        reviewer_id: str,
        reviewee_id: str,
        artifact_type: str,
        artifact_content: str,
        strategy: ReviewStrategy = ReviewStrategy.PEER_REVIEW,
        artifact_metadata: dict | None = None,
    ) -> ReviewSession:
        """Create a new cross-model review session.

        Args:
            reviewer_id: Identifier of the reviewing agent.
            reviewee_id: Identifier of the agent whose work is being reviewed.
            artifact_type: Type label for the artifact (e.g. "code", "plan").
            artifact_content: The content of the artifact under review.
            strategy: Review strategy to apply.
            artifact_metadata: Optional metadata dict for the artifact.

        Returns:
            The newly created ReviewSession.

        Raises:
            ValueError: If the reviewer is not registered or capacity is exceeded.
        """
        if reviewer_id not in self._reviewers:
            raise ValueError(f"Reviewer not registered: {reviewer_id}")
        if len(self._sessions) >= self.MAX_SESSIONS:
            raise RuntimeError("Maximum number of review sessions reached")

        session = ReviewSession(
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            artifact_type=artifact_type,
            artifact_content=artifact_content,
            artifact_metadata=dict(artifact_metadata) if artifact_metadata else {},
            strategy=strategy,
            status=ReviewStatus.IN_PROGRESS,
        )
        self._sessions[session.review_id] = session
        self._total_sessions += 1
        logger.info(
            "Created review %s (reviewer=%s reviewee=%s strategy=%s)",
            session.review_id, reviewer_id, reviewee_id, strategy.value,
        )
        return session

    def submit_report(
        self,
        review_id: str,
        verdict: ReviewVerdict,
        summary: str,
        items: list[ReviewItem] | None = None,
        score: float = 0.5,
        confidence: float = 0.5,
    ) -> ReviewReport:
        """Submit a review report for an active review session.

        Args:
            review_id: Identifier of the review session.
            verdict: Overall verdict issued by the reviewer.
            summary: Human-readable summary of the review.
            items: Optional list of structured review findings.
            score: Quality score in [0, 1] given by the reviewer.
            confidence: Reviewer confidence in [0, 1].

        Returns:
            The created ReviewReport.

        Raises:
            ValueError: If the review session does not exist.
        """
        session = self._sessions.get(review_id)
        if session is None:
            raise ValueError(f"Review not found: {review_id}")

        report = ReviewReport(
            review_id=review_id,
            reviewer_id=session.reviewer_id,
            reviewee_id=session.reviewee_id,
            verdict=verdict,
            summary=summary,
            items=list(items) if items else [],
            score=max(0.0, min(1.0, float(score))),
            confidence=max(0.0, min(1.0, float(confidence))),
        )
        session.report = report
        session.status = ReviewStatus.COMPLETED
        session.completed_at = time.time()
        self._total_reports += 1

        # Update reviewer profile statistics.
        profile = self._reviewers.get(session.reviewer_id)
        if profile is not None:
            profile.total_reviews += 1
            profile.avg_score_given = (
                (profile.avg_score_given * (profile.total_reviews - 1) + report.score)
                / profile.total_reviews
            )

        logger.info(
            "Submitted report %s for review %s (verdict=%s score=%.2f)",
            report.report_id, review_id, verdict.value, report.score,
        )
        return report

    def dispute_review(self, review_id: str, reason: str) -> ReviewSession:
        """Mark a completed review as disputed.

        Args:
            review_id: Identifier of the review session.
            reason: Human-readable reason for the dispute.

        Returns:
            The updated ReviewSession.

        Raises:
            ValueError: If the review session does not exist or the round
                limit has been reached.
        """
        session = self._sessions.get(review_id)
        if session is None:
            raise ValueError(f"Review not found: {review_id}")
        if session.round_number >= self.MAX_ROUNDS:
            raise ValueError(
                f"Maximum review rounds ({self.MAX_ROUNDS}) reached for {review_id}"
            )

        session.status = ReviewStatus.DISPUTED
        session.round_number += 1
        self._dispute_reasons.setdefault(review_id, []).append(reason)
        logger.info(
            "Review %s disputed (round=%d): %s",
            review_id, session.round_number, reason,
        )
        return session

    def resolve_review(
        self,
        review_id: str,
        resolution_notes: str,
    ) -> ReviewSession:
        """Mark a disputed review as resolved.

        Args:
            review_id: Identifier of the review session.
            resolution_notes: Human-readable notes describing the resolution.

        Returns:
            The updated ReviewSession.

        Raises:
            ValueError: If the review session does not exist.
        """
        session = self._sessions.get(review_id)
        if session is None:
            raise ValueError(f"Review not found: {review_id}")

        session.status = ReviewStatus.RESOLVED
        session.completed_at = time.time()
        self._resolution_notes[review_id] = resolution_notes
        logger.info("Review %s resolved: %s", review_id, resolution_notes)
        return session

    def get_review(self, review_id: str) -> ReviewSession | None:
        """Return a review session by id, or None if not found."""
        return self._sessions.get(review_id)

    def list_reviews(
        self,
        reviewer_id: str | None = None,
        status: ReviewStatus | None = None,
        limit: int = 50,
    ) -> list[ReviewSession]:
        """List review sessions with optional filters.

        Args:
            reviewer_id: Optional reviewer id to filter by.
            status: Optional review status to filter by.
            limit: Maximum number of sessions to return.

        Returns:
            List of matching ReviewSession objects, most recent first.
        """
        sessions = list(self._sessions.values())
        if reviewer_id is not None:
            sessions = [s for s in sessions if s.reviewer_id == reviewer_id]
        if status is not None:
            sessions = [s for s in sessions if s.status == status]
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions[:limit]

    # ── Statistics ──

    def get_stats(self) -> dict:
        """Return aggregate statistics about reviews and reviewers.

        Returns:
            A dict containing total_reviews, completed_reviews, avg_score,
            avg_confidence, verdict_distribution, strategy_usage,
            total_reviewers, and avg_trust_score.
        """
        reports = [s.report for s in self._sessions.values() if s.report is not None]
        completed = [
            s for s in self._sessions.values()
            if s.status in (ReviewStatus.COMPLETED, ReviewStatus.RESOLVED)
        ]

        verdict_distribution: dict[str, int] = {v.value: 0 for v in ReviewVerdict}
        for r in reports:
            verdict_distribution[r.verdict.value] += 1

        strategy_usage: dict[str, int] = {s.value: 0 for s in ReviewStrategy}
        for s in self._sessions.values():
            strategy_usage[s.strategy.value] += 1

        avg_score = (
            sum(r.score for r in reports) / len(reports) if reports else 0.0
        )
        avg_confidence = (
            sum(r.confidence for r in reports) / len(reports) if reports else 0.0
        )
        avg_trust = (
            sum(p.trust_score for p in self._reviewers.values())
            / len(self._reviewers)
            if self._reviewers else 0.0
        )

        return {
            "total_reviews": len(self._sessions),
            "completed_reviews": len(completed),
            "avg_score": avg_score,
            "avg_confidence": avg_confidence,
            "verdict_distribution": verdict_distribution,
            "strategy_usage": strategy_usage,
            "total_reviewers": len(self._reviewers),
            "avg_trust_score": avg_trust,
        }

    # ── Maintenance ──

    def reset(self) -> None:
        """Reset the cross-review system to its initial state."""
        self._reviewers.clear()
        self._sessions.clear()
        self._dispute_reasons.clear()
        self._resolution_notes.clear()
        self._total_sessions = 0
        self._total_reports = 0


# ═══════════════════════════════════════════════════════════
# Singleton accessors
# ═══════════════════════════════════════════════════════════

_cross_review: AgentCrossReview | None = None


def get_cross_review() -> AgentCrossReview:
    """Get or create the singleton AgentCrossReview instance."""
    global _cross_review
    if _cross_review is None:
        _cross_review = AgentCrossReview()
    return _cross_review


def reset_cross_review() -> None:
    """Reset the singleton AgentCrossReview instance."""
    global _cross_review
    if _cross_review is not None:
        _cross_review.reset()
    _cross_review = None
