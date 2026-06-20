"""
Experience Database - Structured Experience Tracking for Buddy Agents.

The Experience Database provides a structured repository for agent experiences,
enabling agents to learn from past executions, track outcomes, and build
knowledge over time. Each experience is a complete record of what was tried,
what worked, and what didn't, forming a foundation for continuous improvement.

Core capabilities:
- Structured experience recording with full execution context
- Outcome tracking and success/failure analysis
- Pattern extraction from experience clusters
- Experience replay for learning and verification
- Quality scoring and ranking of experiential knowledge
- Cross-agent experience sharing with provenance tracking
"""

import uuid
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.experience_db")


class ExperienceType(str, Enum):
    """Types of experiences that can be recorded."""
    TASK_EXECUTION = "task_execution"
    TOOL_USAGE = "tool_usage"
    CODE_GENERATION = "code_generation"
    DEBUG_SESSION = "debug_session"
    DECISION_MAKING = "decision_making"
    USER_INTERACTION = "user_interaction"
    ERROR_HANDLING = "error_handling"
    COLLABORATION = "collaboration"


class ExperienceOutcome(str, Enum):
    """Outcome of a recorded experience."""
    EXCELLENT = "excellent"      # Exceeded expectations
    SUCCESS = "success"          # Met expectations
    PARTIAL = "partial"           # Partially successful
    FAILURE = "failure"          # Did not meet expectations
    INCONCLUSIVE = "inconclusive"  # Outcome unclear


class ExperienceQuality(str, Enum):
    """Quality assessment of an experience."""
    VERIFIED = "verified"        # Independently verified
    PEER_REVIEWED = "peer_reviewed"  # Reviewed by another agent
    SELF_REPORTED = "self_reported"  # Reported by the executing agent
    UNCERTAIN = "uncertain"      # Quality uncertain


@dataclass
class ExperienceRecord:
    """A complete record of an agent experience."""
    experience_id: str
    agent_id: str
    experience_type: ExperienceType
    description: str
    outcome: ExperienceOutcome
    quality: ExperienceQuality = ExperienceQuality.SELF_REPORTED
    steps: list[dict] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    errors_encountered: list[str] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)
    key_decisions: list[dict] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    tags: list[str] = field(default_factory=list)
    parent_experience_id: str | None = None
    related_experiences: list[str] = field(default_factory=list)
    reusability_score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    share_count: int = 0
    usage_count: int = 0

    def record_usage(self) -> None:
        """Record when this experience is referenced."""
        self.usage_count += 1
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "experience_id": self.experience_id,
            "agent_id": self.agent_id,
            "experience_type": self.experience_type.value,
            "description": self.description,
            "outcome": self.outcome.value,
            "quality": self.quality.value,
            "steps": self.steps,
            "tools_used": self.tools_used,
            "errors_encountered": self.errors_encountered,
            "lessons_learned": self.lessons_learned,
            "key_decisions": self.key_decisions,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "parent_experience_id": self.parent_experience_id,
            "related_experiences": self.related_experiences,
            "reusability_score": self.reusability_score,
            "created_at": self.created_at.isoformat(),
            "share_count": self.share_count,
            "usage_count": self.usage_count,
        }


@dataclass
class ExperienceCluster:
    """A cluster of related experiences forming a knowledge pattern."""
    cluster_id: str
    topic: str
    description: str
    experience_ids: list[str] = field(default_factory=list)
    common_tools: list[str] = field(default_factory=list)
    common_errors: list[str] = field(default_factory=list)
    best_practices: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    member_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExperienceDatabase:
    """Structured experience repository for Buddy agents.

    Provides a complete system for recording, analyzing, and learning from
    agent experiences. Enables agents to build on past successes, avoid
    repeated failures, and share knowledge across the agent network.
    """

    def __init__(self):
        self._experiences: dict[str, ExperienceRecord] = {}
        self._clusters: dict[str, ExperienceCluster] = {}
        self._total_experiences = 0
        self._total_clusters = 0
        self._shared_experiences = 0

    # ── Experience Recording ────────────────────────────────────────

    def record(
        self,
        agent_id: str,
        experience_type: ExperienceType,
        description: str,
        outcome: ExperienceOutcome,
        steps: list[dict] | None = None,
        tools_used: list[str] | None = None,
        errors: list[str] | None = None,
        lessons: list[str] | None = None,
        decisions: list[dict] | None = None,
        context: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
        tags: list[str] | None = None,
        parent_id: str | None = None,
        quality: ExperienceQuality = ExperienceQuality.SELF_REPORTED,
    ) -> ExperienceRecord:
        """Record a new experience in the database."""
        exp_id = f"exp-{uuid.uuid4().hex[:12]}"

        record = ExperienceRecord(
            experience_id=exp_id,
            agent_id=agent_id,
            experience_type=experience_type,
            description=description,
            outcome=outcome,
            quality=quality,
            steps=steps or [],
            tools_used=tools_used or [],
            errors_encountered=errors or [],
            lessons_learned=lessons or [],
            key_decisions=decisions or [],
            context=context or {},
            duration_ms=duration_ms,
            tags=tags or [],
            parent_experience_id=parent_id,
        )

        # Calculate reusability score based on outcome and lessons
        if outcome in (ExperienceOutcome.EXCELLENT, ExperienceOutcome.SUCCESS):
            record.reusability_score = 0.5 + (0.1 * len(lessons or []))
            if quality == ExperienceQuality.VERIFIED:
                record.reusability_score += 0.2
        elif outcome == ExperienceOutcome.PARTIAL:
            record.reusability_score = 0.3 + (0.05 * len(lessons or []))
        else:
            record.reusability_score = 0.1 * len(lessons or [])

        record.reusability_score = min(1.0, record.reusability_score)

        self._experiences[exp_id] = record
        self._total_experiences += 1

        # Trigger clustering
        self._cluster_experiences(experience_type)

        return record

    # ── Experience Clustering ───────────────────────────────────────

    def _cluster_experiences(self, experience_type: ExperienceType) -> None:
        """Cluster similar experiences to identify patterns."""
        type_experiences = [
            e for e in self._experiences.values()
            if e.experience_type == experience_type
        ]

        if len(type_experiences) < 3:
            return

        # Group by tool usage patterns
        tool_groups: dict[str, list[ExperienceRecord]] = {}
        for exp in type_experiences:
            if exp.tools_used:
                key = "|".join(sorted(exp.tools_used))
                if key not in tool_groups:
                    tool_groups[key] = []
                tool_groups[key].append(exp)

        for tool_key, exps in tool_groups.items():
            if len(exps) >= 2:
                self._create_cluster(tool_key, exps, experience_type)

    def _create_cluster(
        self,
        tool_key: str,
        experiences: list[ExperienceRecord],
        exp_type: ExperienceType,
    ) -> ExperienceCluster:
        """Create a new experience cluster."""
        cluster_id = f"clu-{uuid.uuid4().hex[:12]}"
        tools = tool_key.split("|")

        # Collect common patterns
        all_errors: list[str] = []
        all_lessons: list[str] = []
        successes = 0

        for exp in experiences:
            all_errors.extend(exp.errors_encountered)
            all_lessons.extend(exp.lessons_learned)
            if exp.outcome in (ExperienceOutcome.EXCELLENT, ExperienceOutcome.SUCCESS):
                successes += 1

        # Deduplicate
        common_errors = list(set(all_errors))
        best_practices = list(set(all_lessons))

        cluster = ExperienceCluster(
            cluster_id=cluster_id,
            topic=f"{exp_type.value} with {', '.join(tools)}",
            description=f"Experiences using {', '.join(tools)} for {exp_type.value}",
            experience_ids=[e.experience_id for e in experiences],
            common_tools=tools,
            common_errors=common_errors,
            best_practices=best_practices,
            success_rate=successes / len(experiences),
            member_count=len(experiences),
        )
        self._clusters[cluster_id] = cluster
        self._total_clusters += 1

        return cluster

    # ── Experience Sharing ──────────────────────────────────────────

    def share_experience(
        self, experience_id: str, target_agent_id: str
    ) -> ExperienceRecord | None:
        """Share an experience with another agent."""
        source = self._experiences.get(experience_id)
        if not source:
            return None

        # Create a copy for the target agent
        shared = self.record(
            agent_id=target_agent_id,
            experience_type=source.experience_type,
            description=f"[Shared] {source.description}",
            outcome=source.outcome,
            steps=source.steps,
            tools_used=source.tools_used,
            errors=source.errors_encountered,
            lessons=source.lessons_learned,
            decisions=source.key_decisions,
            context={"shared_from": source.agent_id, "original_id": experience_id},
            tags=source.tags + ["shared"],
            quality=ExperienceQuality.PEER_REVIEWED,
        )

        source.share_count += 1
        self._shared_experiences += 1

        return shared

    # ── Query Methods ───────────────────────────────────────────────

    def get_experience(self, experience_id: str) -> ExperienceRecord | None:
        """Get an experience by ID."""
        exp = self._experiences.get(experience_id)
        if exp:
            exp.record_usage()
        return exp

    def search(
        self,
        agent_id: str | None = None,
        experience_type: ExperienceType | None = None,
        outcome: ExperienceOutcome | None = None,
        min_reusability: float = 0.0,
        tags: list[str] | None = None,
        query: str = "",
        limit: int = 50,
    ) -> list[ExperienceRecord]:
        """Search experiences with multiple filters."""
        results: list[ExperienceRecord] = []

        query_lower = query.lower()
        for exp in self._experiences.values():
            if agent_id and exp.agent_id != agent_id:
                continue
            if experience_type and exp.experience_type != experience_type:
                continue
            if outcome and exp.outcome != outcome:
                continue
            if exp.reusability_score < min_reusability:
                continue
            if tags and not any(t in exp.tags for t in tags):
                continue
            if query_lower and query_lower not in exp.description.lower():
                continue

            results.append(exp)

        results.sort(key=lambda e: e.reusability_score, reverse=True)
        return results[:limit]

    def get_successful_experiences(
        self, agent_id: str | None = None, limit: int = 20
    ) -> list[ExperienceRecord]:
        """Get the most successful experiences for learning."""
        return self.search(
            agent_id=agent_id,
            outcome=ExperienceOutcome.EXCELLENT,
            min_reusability=0.5,
            limit=limit,
        ) + self.search(
            agent_id=agent_id,
            outcome=ExperienceOutcome.SUCCESS,
            min_reusability=0.5,
            limit=limit,
        )

    def get_failure_lessons(
        self, agent_id: str | None = None, limit: int = 20
    ) -> list[ExperienceRecord]:
        """Get failure experiences to learn what to avoid."""
        return self.search(
            agent_id=agent_id,
            outcome=ExperienceOutcome.FAILURE,
            limit=limit,
        )

    def get_clusters(
        self, min_success_rate: float = 0.0, limit: int = 50
    ) -> list[ExperienceCluster]:
        """Get experience clusters."""
        clusters = list(self._clusters.values())
        if min_success_rate > 0:
            clusters = [c for c in clusters if c.success_rate >= min_success_rate]
        clusters.sort(key=lambda c: c.success_rate, reverse=True)
        return clusters[:limit]

    def get_cluster(self, cluster_id: str) -> ExperienceCluster | None:
        """Get a cluster by ID."""
        return self._clusters.get(cluster_id)

    def get_stats(self) -> dict:
        """Get experience database statistics."""
        type_counts = {}
        for exp in self._experiences.values():
            t = exp.experience_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        outcome_counts = {}
        for exp in self._experiences.values():
            o = exp.outcome.value
            outcome_counts[o] = outcome_counts.get(o, 0) + 1

        return {
            "total_experiences": self._total_experiences,
            "total_clusters": self._total_clusters,
            "shared_experiences": self._shared_experiences,
            "by_type": type_counts,
            "by_outcome": outcome_counts,
            "average_reusability": (
                sum(e.reusability_score for e in self._experiences.values()) /
                max(1, len(self._experiences))
            ),
            "top_lessons": self._get_top_lessons(5),
            "top_errors": self._get_top_errors(5),
        }

    def _get_top_lessons(self, n: int) -> list[str]:
        """Get the most common lessons learned."""
        lesson_counts: dict[str, int] = {}
        for exp in self._experiences.values():
            for lesson in exp.lessons_learned:
                lesson_counts[lesson] = lesson_counts.get(lesson, 0) + 1
        return sorted(lesson_counts, key=lesson_counts.get, reverse=True)[:n]

    def _get_top_errors(self, n: int) -> list[str]:
        """Get the most common errors encountered."""
        error_counts: dict[str, int] = {}
        for exp in self._experiences.values():
            for error in exp.errors_encountered:
                error_counts[error] = error_counts.get(error, 0) + 1
        return sorted(error_counts, key=error_counts.get, reverse=True)[:n]


# Singleton instance
experience_db = ExperienceDatabase()