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
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

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
    parent_experience_id: Optional[str] = None
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
        self._version_history: dict[str, list[dict]] = {}

    # ── Experience Recording ────────────────────────────────────────

    def record(
        self,
        agent_id: str,
        experience_type: ExperienceType,
        description: str,
        outcome: ExperienceOutcome,
        steps: Optional[list[dict]] = None,
        tools_used: Optional[list[str]] = None,
        errors: Optional[list[str]] = None,
        lessons: Optional[list[str]] = None,
        decisions: Optional[list[dict]] = None,
        context: Optional[dict[str, Any]] = None,
        duration_ms: float = 0.0,
        tags: Optional[list[str]] = None,
        parent_id: Optional[str] = None,
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
    ) -> Optional[ExperienceRecord]:
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

    def get_experience(self, experience_id: str) -> Optional[ExperienceRecord]:
        """Get an experience by ID."""
        exp = self._experiences.get(experience_id)
        if exp:
            exp.record_usage()
        return exp

    def search(
        self,
        agent_id: Optional[str] = None,
        experience_type: Optional[ExperienceType] = None,
        outcome: Optional[ExperienceOutcome] = None,
        min_reusability: float = 0.0,
        tags: Optional[list[str]] = None,
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
        self, agent_id: Optional[str] = None, limit: int = 20
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
        self, agent_id: Optional[str] = None, limit: int = 20
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

    def get_cluster(self, cluster_id: str) -> Optional[ExperienceCluster]:
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


# ── Trend Analysis ──────────────────────────────────────────────

    def analyze_trends(
        self,
        days: int = 30,
        agent_id: Optional[str] = None,
    ) -> dict:
        """Analyze experience trends over time.

        Computes success rate trends, identifies common failure patterns,
        and surfaces improvement areas from the experience database.

        Args:
            days: Number of days to look back for trend analysis.
            agent_id: Optionally filter trends to a specific agent.

        Returns:
            A dictionary with daily success/failure rates, common failure
            patterns, improvement areas, and per-tool effectiveness scores.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        exps = [e for e in self._experiences.values() if e.created_at >= cutoff]
        if agent_id:
            exps = [e for e in exps if e.agent_id == agent_id]

        if not exps:
            return {
                "period_days": days,
                "total_experiences": 0,
                "overall_success_rate": 0.0,
                "daily_trends": [],
                "common_failure_patterns": [],
                "improvement_areas": [],
                "tool_effectiveness": [],
            }

        # Group experiences by day
        by_day: dict[str, list[ExperienceRecord]] = {}
        for exp in exps:
            day_key = exp.created_at.strftime("%Y-%m-%d")
            by_day.setdefault(day_key, []).append(exp)

        daily_trends: list[dict] = []
        for day_key in sorted(by_day.keys()):
            day_exps = by_day[day_key]
            total = len(day_exps)
            successes = sum(
                1 for e in day_exps
                if e.outcome in (ExperienceOutcome.EXCELLENT, ExperienceOutcome.SUCCESS)
            )
            failures = sum(
                1 for e in day_exps if e.outcome == ExperienceOutcome.FAILURE
            )
            daily_trends.append({
                "date": day_key,
                "total": total,
                "success_rate": successes / total,
                "failure_rate": failures / total,
            })

        # Overall success rate
        overall_successes = sum(
            1 for e in exps
            if e.outcome in (ExperienceOutcome.EXCELLENT, ExperienceOutcome.SUCCESS)
        )
        overall_success_rate = overall_successes / len(exps)

        # Common failure patterns: most frequent errors in failed experiences
        failure_exps = [e for e in exps if e.outcome == ExperienceOutcome.FAILURE]
        failure_errors = Counter()
        for e in failure_exps:
            for err in e.errors_encountered:
                failure_errors[err] += 1

        # Improvement areas: lessons from partial / failure experiences
        improvement_exps = [
            e for e in exps
            if e.outcome in (ExperienceOutcome.PARTIAL, ExperienceOutcome.FAILURE)
        ]
        improvement_lessons = Counter()
        for e in improvement_exps:
            for lesson in e.lessons_learned:
                improvement_lessons[lesson] += 1

        # Per-tool effectiveness: success rate when each tool was used
        tool_results: dict[str, list[bool]] = {}
        for e in exps:
            is_success = e.outcome in (
                ExperienceOutcome.EXCELLENT, ExperienceOutcome.SUCCESS
            )
            for tool in e.tools_used:
                tool_results.setdefault(tool, []).append(is_success)

        tool_effectiveness = [
            {"tool": tool, "success_rate": sum(results) / len(results)}
            for tool, results in tool_results.items()
        ]
        tool_effectiveness.sort(key=lambda x: x["success_rate"], reverse=True)

        return {
            "period_days": days,
            "total_experiences": len(exps),
            "overall_success_rate": overall_success_rate,
            "daily_trends": daily_trends,
            "common_failure_patterns": failure_errors.most_common(10),
            "improvement_areas": improvement_lessons.most_common(10),
            "tool_effectiveness": tool_effectiveness,
        }

    # ── Predictive Insights ─────────────────────────────────────────

    def predict_outcome(
        self,
        description: str,
        experience_type: Optional[ExperienceType] = None,
        tools_used: Optional[list[str]] = None,
        top_k: int = 5,
    ) -> dict:
        """Generate predictive insights about likely outcomes.

        Finds past experiences most similar to the given task description
        and uses their outcomes to predict the likely result.

        Args:
            description: Natural-language description of the upcoming task.
            experience_type: Optionally restrict to a specific experience type.
            tools_used: Tools expected to be used in the upcoming task.
            top_k: Number of most-similar past experiences to consider.

        Returns:
            A dictionary with predicted outcome distribution, confidence,
            and the most-similar past experiences used for the prediction.
        """
        # Build candidate pool
        candidates = list(self._experiences.values())
        if experience_type is not None:
            candidates = [
                e for e in candidates if e.experience_type == experience_type
            ]
        if not candidates:
            return {
                "predicted_outcome": "unknown",
                "confidence": 0.0,
                "outcome_distribution": {},
                "similar_experiences": [],
            }

        # Score each candidate by similarity to the description
        scored: list[tuple[float, ExperienceRecord]] = []
        for exp in candidates:
            desc_sim = self._compute_similarity(description, exp.description)
            # Bonus for tag overlap with tools
            tag_bonus = 0.0
            if tools_used:
                tool_set = set(tools_used)
                exp_tool_set = set(exp.tools_used)
                if tool_set and exp_tool_set:
                    tag_bonus = len(tool_set & exp_tool_set) / len(tool_set | exp_tool_set)
            score = 0.7 * desc_sim + 0.3 * tag_bonus
            if score > 0:
                scored.append((score, exp))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        if not top:
            return {
                "predicted_outcome": "unknown",
                "confidence": 0.0,
                "outcome_distribution": {},
                "similar_experiences": [],
            }

        # Weighted outcome distribution
        outcome_weights: dict[str, float] = {}
        for score, exp in top:
            key = exp.outcome.value
            outcome_weights[key] = outcome_weights.get(key, 0.0) + score

        total_weight = sum(outcome_weights.values())
        outcome_distribution = {
            k: v / total_weight for k, v in outcome_weights.items()
        }

        predicted_outcome = max(outcome_distribution, key=outcome_distribution.get)
        confidence = outcome_distribution[predicted_outcome]

        similar = [
            {
                "experience_id": exp.experience_id,
                "description": exp.description,
                "outcome": exp.outcome.value,
                "similarity_score": round(score, 3),
            }
            for score, exp in top
        ]

        return {
            "predicted_outcome": predicted_outcome,
            "confidence": round(confidence, 3),
            "outcome_distribution": {
                k: round(v, 3) for k, v in outcome_distribution.items()
            },
            "similar_experiences": similar,
        }

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute Jaccard similarity between two text strings."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    # ── Experience Recommendation ───────────────────────────────────

    def recommend_experiences(
        self,
        description: str,
        experience_type: Optional[ExperienceType] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Recommend relevant past experiences for a new task.

        Ranks past experiences by similarity to the given task description,
        considering both textual similarity and tag overlap.

        Args:
            description: Natural-language description of the new task.
            experience_type: Optionally restrict to a specific experience type.
            limit: Maximum number of recommendations to return.

        Returns:
            A list of recommended experiences ranked by relevance, each
            containing the experience metadata and a relevance score.
        """
        candidates = list(self._experiences.values())
        if experience_type is not None:
            candidates = [
                e for e in candidates if e.experience_type == experience_type
            ]

        scored: list[tuple[float, ExperienceRecord]] = []
        for exp in candidates:
            desc_sim = self._compute_similarity(description, exp.description)
            # Boost successful experiences
            outcome_bonus = 0.0
            if exp.outcome in (ExperienceOutcome.EXCELLENT, ExperienceOutcome.SUCCESS):
                outcome_bonus = 0.15
            # Boost verified experiences
            quality_bonus = 0.0
            if exp.quality == ExperienceQuality.VERIFIED:
                quality_bonus = 0.1
            score = desc_sim + outcome_bonus + quality_bonus
            if score > 0:
                scored.append((score, exp))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        return [
            {
                "experience_id": exp.experience_id,
                "description": exp.description,
                "experience_type": exp.experience_type.value,
                "outcome": exp.outcome.value,
                "relevance_score": round(score, 3),
                "lessons_learned": exp.lessons_learned,
                "tools_used": exp.tools_used,
                "tags": exp.tags,
            }
            for score, exp in top
        ]

    # ── Experience Versioning ───────────────────────────────────────

    def update_experience(
        self,
        experience_id: str,
        **updates: Any,
    ) -> Optional[ExperienceRecord]:
        """Update an experience record with version tracking.

        Saves a snapshot of the current state before applying updates,
        enabling version history tracking for each experience.

        Acceptable update keys match ExperienceRecord fields:
        description, outcome, quality, steps, tools_used,
        errors_encountered, lessons_learned, key_decisions, context,
        duration_ms, tags, reusability_score.

        Args:
            experience_id: The ID of the experience to update.
            **updates: Keyword arguments for fields to update.

        Returns:
            The updated ExperienceRecord, or None if not found.
        """
        exp = self._experiences.get(experience_id)
        if exp is None:
            return None

        # Save a snapshot of the current state before applying changes
        snapshot = exp.to_dict()
        snapshot["version_saved_at"] = datetime.now(timezone.utc).isoformat()
        self._version_history.setdefault(experience_id, []).append(snapshot)

        # Apply updates to allowed fields
        allowed_fields = (
            "description", "outcome", "quality", "steps", "tools_used",
            "errors_encountered", "lessons_learned", "key_decisions",
            "context", "duration_ms", "tags", "reusability_score",
        )
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(exp, key, value)

        exp.updated_at = datetime.now(timezone.utc)

        # Recalculate reusability if outcome or lessons changed
        if "outcome" in updates or "lessons_learned" in updates:
            if exp.outcome in (ExperienceOutcome.EXCELLENT, ExperienceOutcome.SUCCESS):
                exp.reusability_score = 0.5 + (0.1 * len(exp.lessons_learned))
                if exp.quality == ExperienceQuality.VERIFIED:
                    exp.reusability_score += 0.2
            elif exp.outcome == ExperienceOutcome.PARTIAL:
                exp.reusability_score = 0.3 + (0.05 * len(exp.lessons_learned))
            else:
                exp.reusability_score = 0.1 * len(exp.lessons_learned)
            exp.reusability_score = min(1.0, exp.reusability_score)

        return exp

    def get_experience_versions(
        self, experience_id: str
    ) -> list[dict]:
        """Get the version history of an experience.

        Args:
            experience_id: The ID of the experience.

        Returns:
            A list of previous version snapshots, oldest first.
        """
        return self._version_history.get(experience_id, [])

    def get_version_count(self, experience_id: str) -> int:
        """Get the number of previous versions for an experience.

        Args:
            experience_id: The ID of the experience.

        Returns:
            The number of saved version snapshots.
        """
        return len(self._version_history.get(experience_id, []))

    # ── Cross-Domain Transfer ───────────────────────────────────────

    def cross_domain_transfer(
        self,
        source_type: ExperienceType,
        target_type: ExperienceType,
        min_reusability: float = 0.3,
        limit: int = 10,
    ) -> list[dict]:
        """Identify experiences from one domain applicable to another.

        Finds high-quality experiences from a source domain that share
        tools, patterns, or lessons with the target domain, suggesting
        knowledge that can transfer across domains.

        Args:
            source_type: The source experience type to draw from.
            target_type: The target experience type to apply to.
            min_reusability: Minimum reusability score for source experiences.
            limit: Maximum number of transfer candidates to return.

        Returns:
            A list of cross-domain transfer candidates with transfer
            relevance scores.
        """
        source_exps = [
            e for e in self._experiences.values()
            if e.experience_type == source_type
            and e.reusability_score >= min_reusability
        ]
        target_exps = [
            e for e in self._experiences.values()
            if e.experience_type == target_type
        ]

        if not source_exps:
            return []

        # Build a profile of tools and tags used in the target domain
        target_tools = set()
        target_tags = set()
        target_lessons = set()
        for e in target_exps:
            target_tools.update(e.tools_used)
            target_tags.update(e.tags)
            target_lessons.update(e.lessons_learned)

        # Score each source experience by how well it overlaps with target patterns
        scored: list[tuple[float, ExperienceRecord]] = []
        for exp in source_exps:
            tool_overlap = len(set(exp.tools_used) & target_tools)
            tag_overlap = len(set(exp.tags) & target_tags)
            lesson_overlap = len(set(exp.lessons_learned) & target_lessons)

            # Normalize and combine scores
            tool_score = tool_overlap / max(1, len(set(exp.tools_used)))
            tag_score = tag_overlap / max(1, len(set(exp.tags)))
            lesson_score = lesson_overlap / max(1, len(set(exp.lessons_learned)))

            transfer_score = (
                0.35 * tool_score + 0.25 * tag_score + 0.25 * lesson_score
                + 0.15 * exp.reusability_score
            )

            if transfer_score > 0:
                scored.append((transfer_score, exp))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        return [
            {
                "experience_id": exp.experience_id,
                "description": exp.description,
                "source_domain": source_type.value,
                "target_domain": target_type.value,
                "transfer_score": round(score, 3),
                "shared_tools": [
                    t for t in exp.tools_used if t in target_tools
                ],
                "shared_tags": [
                    t for t in exp.tags if t in target_tags
                ],
                "outcome": exp.outcome.value,
                "lessons_learned": exp.lessons_learned,
            }
            for score, exp in top
        ]

    # ── Experience Summarization ────────────────────────────────────

    def summarize_cluster(self, cluster_id: str) -> Optional[dict]:
        """Generate a concise summary of an experience cluster.

        Produces a human-readable summary with key takeaways, aggregated
        statistics, and actionable recommendations based on the cluster's
        member experiences.

        Args:
            cluster_id: The ID of the cluster to summarize.

        Returns:
            A dictionary with cluster summary information, or None if
            the cluster is not found.
        """
        cluster = self._clusters.get(cluster_id)
        if cluster is None:
            return None

        # Gather all member experiences
        members = [
            self._experiences[eid]
            for eid in cluster.experience_ids
            if eid in self._experiences
        ]

        if not members:
            return {
                "cluster_id": cluster_id,
                "topic": cluster.topic,
                "description": cluster.description,
                "member_count": 0,
                "success_rate": 0.0,
                "key_takeaways": [],
                "summary": "No member experiences found for this cluster.",
            }

        # Aggregate outcomes
        outcome_counts = Counter(e.outcome.value for e in members)
        success_rate = (
            outcome_counts.get("excellent", 0) + outcome_counts.get("success", 0)
        ) / len(members)

        # Aggregate all lessons and rank by frequency
        all_lessons = Counter()
        for e in members:
            for lesson in e.lessons_learned:
                all_lessons[lesson] += 1
        top_lessons = all_lessons.most_common(5)

        # Aggregate all errors and rank by frequency
        all_errors = Counter()
        for e in members:
            for err in e.errors_encountered:
                all_errors[err] += 1
        top_errors = all_errors.most_common(5)

        # Compute average duration
        durations = [e.duration_ms for e in members if e.duration_ms > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Most-used tools
        tool_counts = Counter()
        for e in members:
            for tool in e.tools_used:
                tool_counts[tool] += 1

        # Build key takeaways
        key_takeaways: list[str] = []
        if top_lessons:
            key_takeaways.append(
                f"Top lesson: {top_lessons[0][0]} "
                f"(seen in {top_lessons[0][1]} of {len(members)} experiences)"
            )
        if top_errors:
            key_takeaways.append(
                f"Most common error: {top_errors[0][0]} "
                f"(seen in {top_errors[0][1]} of {len(members)} experiences)"
            )
        if success_rate >= 0.8:
            key_takeaways.append(
                "High success rate — this approach is well-proven."
            )
        elif success_rate < 0.5:
            key_takeaways.append(
                "Low success rate — consider alternative approaches."
            )

        # Build a human-readable summary paragraph
        summary_parts = [
            f"This cluster contains {len(members)} experiences about "
            f"{cluster.topic}.",
            f"The overall success rate is {success_rate:.0%}.",
        ]
        if top_lessons:
            summary_parts.append(
                f"The most valuable lesson is: \"{top_lessons[0][0]}\"."
            )
        if top_errors:
            summary_parts.append(
                f"The most frequent error is: \"{top_errors[0][0]}\"."
            )
        summary = " ".join(summary_parts)

        return {
            "cluster_id": cluster_id,
            "topic": cluster.topic,
            "description": cluster.description,
            "member_count": len(members),
            "success_rate": round(success_rate, 3),
            "outcome_distribution": dict(outcome_counts),
            "average_duration_ms": round(avg_duration, 1),
            "most_used_tools": tool_counts.most_common(5),
            "top_lessons": top_lessons,
            "top_errors": top_errors,
            "key_takeaways": key_takeaways,
            "summary": summary,
        }


# Singleton instance
experience_db = ExperienceDatabase()