"""Buddy Evolution Loop — Self-Improving Agent Learning Engine

The Evolution Loop enables continuous self-improvement through a closed
feedback cycle: agents learn from experience, create skills from complex
tasks, improve skills during use, and build deepening models of user
behavior across sessions.

Core capabilities:
- Closed learning loop with automatic skill creation
- Skill self-improvement during execution
- Experience-based nudging for knowledge persistence
- Cross-session knowledge recall and synthesis
- User model building through interaction patterns
- Trajectory compression for efficient storage
- Autonomous skill curation and pruning
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.evolution_loop")


# ── Core Enums ──────────────────────────────────────────────────────

class SkillStatus(str, Enum):
    """Lifecycle status of a skill."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    MERGED = "merged"
    ARCHIVED = "archived"
    EXPERIMENTAL = "experimental"


class LearningTrigger(str, Enum):
    """Triggers that initiate the learning cycle."""
    TASK_COMPLETION = "task_completion"
    ERROR_ENCOUNTERED = "error_encountered"
    USER_CORRECTION = "user_correction"
    PERIODIC_NUDGE = "periodic_nudge"
    COMPLEXITY_THRESHOLD = "complexity_threshold"
    PATTERN_DETECTED = "pattern_detected"
    USER_FEEDBACK = "user_feedback"


class NudgeType(str, Enum):
    """Types of memory nudges for knowledge persistence."""
    SUMMARIZE = "summarize"
    CONSOLIDATE = "consolidate"
    PRUNE = "prune"
    SURFACE = "surface"
    CONNECT = "connect"


class ImprovementType(str, Enum):
    """Types of skill improvements."""
    REFINE = "refine"
    GENERALIZE = "generalize"
    SPECIALIZE = "specialize"
    COMBINE = "combine"
    SPLIT = "split"
    DEPRECATE = "deprecate"


# ── Data Classes ────────────────────────────────────────────────────

@dataclass
class SkillDefinition:
    """Definition of an agent skill."""
    skill_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    category: str = "general"
    triggers: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    status: SkillStatus = SkillStatus.ACTIVE
    version: int = 1
    usage_count: int = 0
    success_rate: float = 1.0
    avg_duration_ms: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningEvent:
    """A single learning event captured from agent execution."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    trigger: LearningTrigger = LearningTrigger.TASK_COMPLETION
    session_id: str = ""
    agent_id: str = ""
    description: str = ""
    context: str = ""
    outcome: str = "success"
    complexity_score: float = 0.0
    novel_patterns: list[str] = field(default_factory=list)
    skills_used: list[str] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0
    user_feedback: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SkillImprovement:
    """A proposed or applied skill improvement."""
    improvement_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    skill_id: str = ""
    improvement_type: ImprovementType = ImprovementType.REFINE
    description: str = ""
    before_snapshot: dict[str, Any] = field(default_factory=dict)
    after_snapshot: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    applied: bool = False
    applied_at: str = ""
    performance_impact: float = 0.0


@dataclass
class UserModel:
    """Accumulated user behavior model across sessions."""
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: str = "default"
    preferences: dict[str, Any] = field(default_factory=dict)
    interaction_patterns: list[dict[str, Any]] = field(default_factory=list)
    domain_expertise: dict[str, float] = field(default_factory=dict)
    communication_style: str = ""
    frequent_topics: list[str] = field(default_factory=list)
    common_workflows: list[dict[str, Any]] = field(default_factory=list)
    total_sessions: int = 0
    total_interactions: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EvolutionConfig:
    """Configuration for the evolution loop."""
    auto_skill_creation: bool = True
    auto_skill_improvement: bool = True
    periodic_nudge_interval: int = 3600
    min_complexity_for_skill: float = 0.6
    min_usage_for_improvement: int = 3
    max_skill_versions: int = 10
    user_model_update_frequency: int = 5
    trajectory_compression_enabled: bool = True
    pruning_threshold_days: int = 30


# ── Evolution Loop Engine ───────────────────────────────────────────

class EvolutionLoop:
    """Closed-loop self-improvement engine for AI agents.

    Implements a continuous learning cycle: capture → analyze → create/improve
    → validate → deploy. Agents learn from every interaction, creating skills
    from complex tasks, improving skills during use, and building user models
    across sessions.
    """

    def __init__(self, config: EvolutionConfig | None = None):
        self.config = config or EvolutionConfig()
        self._skills: dict[str, SkillDefinition] = {}
        self._learning_events: list[LearningEvent] = []
        self._improvements: list[SkillImprovement] = []
        self._user_models: dict[str, UserModel] = {}
        self._nudge_queue: list[dict[str, Any]] = []
        self._last_nudge_time: float = 0.0
        self._total_skills_created: int = 0
        self._total_improvements_applied: int = 0

    # ── Learning Event Capture ──────────────────────────────────

    def capture_event(self, event: LearningEvent) -> str:
        """Capture a learning event from agent execution."""
        self._learning_events.append(event)

        if self.config.auto_skill_creation:
            if event.complexity_score >= self.config.min_complexity_for_skill:
                self._maybe_create_skill(event)

        if self.config.auto_skill_improvement:
            for skill_id in event.skills_used:
                skill = self._skills.get(skill_id)
                if skill and skill.usage_count >= self.config.min_usage_for_improvement:
                    self._maybe_improve_skill(skill, event)

        self._update_user_model(event)

        logger.debug(f"Learning event captured: {event.event_id} ({event.trigger.value})")
        return event.event_id

    def _maybe_create_skill(self, event: LearningEvent) -> Optional[SkillDefinition]:
        """Create a new skill from a complex task if patterns are novel."""
        if not event.novel_patterns:
            return None

        skill_name = event.description[:50].lower().replace(" ", "_")
        skill = SkillDefinition(
            name=skill_name,
            description=event.description[:200],
            category=self._infer_category(event),
            triggers=[event.trigger.value],
            steps=event.novel_patterns,
            status=SkillStatus.EXPERIMENTAL,
            metadata={
                "source_event": event.event_id,
                "agent_id": event.agent_id,
                "complexity": event.complexity_score,
            },
        )

        self._skills[skill.skill_id] = skill
        self._total_skills_created += 1
        logger.info(f"New skill created: {skill.name} (v{skill.version})")
        return skill

    def _maybe_improve_skill(
        self, skill: SkillDefinition, event: LearningEvent
    ) -> Optional[SkillImprovement]:
        """Propose a skill improvement based on execution data."""
        if skill.usage_count < self.config.min_usage_for_improvement:
            return None

        if event.outcome != "success" and skill.success_rate > 0.5:
            improvement = SkillImprovement(
                skill_id=skill.skill_id,
                improvement_type=ImprovementType.REFINE,
                description=f"Refine {skill.name} based on failure pattern",
                before_snapshot={"steps": list(skill.steps), "triggers": list(skill.triggers)},
                rationale=f"Execution failed with outcome: {event.outcome}",
            )
            self._improvements.append(improvement)
            return improvement

        if event.complexity_score > 0.8 and len(skill.steps) < 5:
            improvement = SkillImprovement(
                skill_id=skill.skill_id,
                improvement_type=ImprovementType.GENERALIZE,
                description=f"Generalize {skill.name} for broader applicability",
                before_snapshot={"steps": list(skill.steps)},
                rationale="High complexity suggests broader applicability",
            )
            self._improvements.append(improvement)
            return improvement

        return None

    def _infer_category(self, event: LearningEvent) -> str:
        """Infer skill category from event context."""
        context_lower = event.context.lower()
        if any(kw in context_lower for kw in ["code", "program", "develop", "api"]):
            return "development"
        if any(kw in context_lower for kw in ["data", "analysis", "query", "report"]):
            return "data"
        if any(kw in context_lower for kw in ["content", "write", "document", "blog"]):
            return "content"
        if any(kw in context_lower for kw in ["research", "study", "learn", "explore"]):
            return "research"
        return "general"

    def _update_user_model(self, event: LearningEvent) -> None:
        """Update the user model with interaction data."""
        user_id = event.agent_id or "default"
        model = self._user_models.get(user_id)
        if not model:
            model = UserModel(user_id=user_id, total_sessions=1, total_interactions=1)
            self._user_models[user_id] = model
        else:
            model.total_interactions += 1

        model.last_updated = datetime.now(timezone.utc).isoformat()

        if event.context:
            words = event.context.lower().split()
            for word in words[:10]:
                if len(word) > 3:
                    model.frequent_topics.append(word)

        model.frequent_topics = list(set(model.frequent_topics))[:50]

    # ── Skill Management ────────────────────────────────────────

    def register_skill(self, skill: SkillDefinition) -> str:
        """Register a new or updated skill."""
        self._skills[skill.skill_id] = skill
        return skill.skill_id

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_skills(
        self, category: str = "", status: str = ""
    ) -> list[SkillDefinition]:
        """List skills, optionally filtered by category and status."""
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        if status:
            skills = [s for s in skills if s.status.value == status]
        return sorted(skills, key=lambda s: s.usage_count, reverse=True)

    def apply_improvement(self, improvement_id: str) -> bool:
        """Apply a pending skill improvement."""
        improvement = next(
            (i for i in self._improvements if i.improvement_id == improvement_id), None
        )
        if not improvement or improvement.applied:
            return False

        skill = self._skills.get(improvement.skill_id)
        if not skill:
            return False

        if improvement.improvement_type == ImprovementType.REFINE:
            if improvement.before_snapshot.get("steps"):
                skill.steps = list(set(skill.steps + improvement.before_snapshot["steps"]))
        elif improvement.improvement_type == ImprovementType.GENERALIZE:
            skill.description = f"[Generalized] {skill.description}"
        elif improvement.improvement_type == ImprovementType.DEPRECATE:
            skill.status = SkillStatus.DEPRECATED

        skill.version += 1
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        improvement.applied = True
        improvement.applied_at = datetime.now(timezone.utc).isoformat()
        self._total_improvements_applied += 1
        logger.info(f"Improvement applied to skill {skill.name} (v{skill.version})")
        return True

    # ── Nudge System ────────────────────────────────────────────

    def check_nudges(self) -> list[dict[str, Any]]:
        """Check if any memory nudges are due."""
        now = time.time()
        nudges_due: list[dict[str, Any]] = []

        if now - self._last_nudge_time < self.config.periodic_nudge_interval:
            return nudges_due

        unused_skills = [
            s for s in self._skills.values()
            if s.status == SkillStatus.ACTIVE and s.usage_count == 0
        ]
        if unused_skills:
            nudges_due.append({
                "type": NudgeType.PRUNE.value,
                "message": f"{len(unused_skills)} unused skills could be pruned",
                "targets": [s.skill_id for s in unused_skills[:5]],
                "priority": "low",
            })

        low_success_skills = [
            s for s in self._skills.values()
            if s.success_rate < 0.5 and s.usage_count >= 3
        ]
        if low_success_skills:
            nudges_due.append({
                "type": NudgeType.SURFACE.value,
                "message": f"{len(low_success_skills)} skills have low success rates",
                "targets": [s.skill_id for s in low_success_skills[:5]],
                "priority": "medium",
            })

        if nudges_due:
            self._last_nudge_time = now
            self._nudge_queue.extend(nudges_due)

        return nudges_due

    def process_nudge(self, nudge_index: int, action: str) -> dict[str, Any]:
        """Process a user response to a nudge."""
        if nudge_index >= len(self._nudge_queue):
            return {"error": "Nudge not found"}

        nudge = self._nudge_queue.pop(nudge_index)
        if action == "prune" and nudge["type"] == NudgeType.PRUNE.value:
            for skill_id in nudge.get("targets", []):
                skill = self._skills.get(skill_id)
                if skill:
                    skill.status = SkillStatus.ARCHIVED
            return {"action": "pruned", "count": len(nudge.get("targets", []))}

        return {"action": "acknowledged", "nudge": nudge["message"]}

    # ── User Model ──────────────────────────────────────────────

    def get_user_model(self, user_id: str = "default") -> Optional[dict[str, Any]]:
        """Get the accumulated user model."""
        model = self._user_models.get(user_id)
        if not model:
            return None
        return {
            "user_id": model.user_id,
            "preferences": model.preferences,
            "communication_style": model.communication_style,
            "frequent_topics": model.frequent_topics[:10],
            "domain_expertise": model.domain_expertise,
            "total_sessions": model.total_sessions,
            "total_interactions": model.total_interactions,
            "common_workflows": model.common_workflows[:5],
            "last_updated": model.last_updated,
        }

    def update_user_preference(
        self, key: str, value: Any, user_id: str = "default"
    ) -> None:
        """Update a specific user preference."""
        model = self._user_models.get(user_id)
        if not model:
            model = UserModel(user_id=user_id)
            self._user_models[user_id] = model
        model.preferences[key] = value
        model.last_updated = datetime.now(timezone.utc).isoformat()

    # ── Trajectory Compression ──────────────────────────────────

    def compress_trajectories(self, max_events: int = 100) -> dict[str, Any]:
        """Compress older learning events into summaries."""
        if len(self._learning_events) <= max_events:
            return {"compressed": 0, "remaining": len(self._learning_events)}

        to_compress = self._learning_events[:-max_events]
        summary = {
            "total_events": len(to_compress),
            "success_rate": sum(1 for e in to_compress if e.outcome == "success") / max(len(to_compress), 1),
            "avg_complexity": sum(e.complexity_score for e in to_compress) / max(len(to_compress), 1),
            "top_triggers": self._count_triggers(to_compress),
            "skills_created": sum(1 for e in to_compress if e.novel_patterns),
            "compressed_at": datetime.now(timezone.utc).isoformat(),
        }

        self._learning_events = self._learning_events[-max_events:]
        logger.info(f"Compressed {len(to_compress)} events into summary")
        return {"compressed": len(to_compress), "remaining": len(self._learning_events), "summary": summary}

    def _count_triggers(self, events: list[LearningEvent]) -> dict[str, int]:
        """Count events by trigger type."""
        counts: dict[str, int] = {}
        for event in events:
            trigger = event.trigger.value
            counts[trigger] = counts.get(trigger, 0) + 1
        return counts

    # ── Statistics ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get evolution loop statistics."""
        total_skills = len(self._skills)
        active_skills = len([s for s in self._skills.values() if s.status == SkillStatus.ACTIVE])
        return {
            "total_skills": total_skills,
            "active_skills": active_skills,
            "total_skills_created": self._total_skills_created,
            "total_improvements": len(self._improvements),
            "improvements_applied": self._total_improvements_applied,
            "learning_events": len(self._learning_events),
            "user_models": len(self._user_models),
            "pending_nudges": len(self._nudge_queue),
            "skills_by_category": self._count_by_category(),
            "skills_by_status": self._count_by_status(),
            "average_success_rate": self._average_success_rate(),
        }

    def _count_by_category(self) -> dict[str, int]:
        """Count skills by category."""
        counts: dict[str, int] = {}
        for skill in self._skills.values():
            counts[skill.category] = counts.get(skill.category, 0) + 1
        return counts

    def _count_by_status(self) -> dict[str, int]:
        """Count skills by status."""
        counts: dict[str, int] = {}
        for skill in self._skills.values():
            counts[skill.status.value] = counts.get(skill.status.value, 0) + 1
        return counts

    def _average_success_rate(self) -> float:
        """Calculate average success rate across all skills."""
        if not self._skills:
            return 1.0
        return sum(s.success_rate for s in self._skills.values()) / len(self._skills)

    def reset(self) -> None:
        """Clear all internal state, reset counters, and reinitialize defaults."""
        self._skills.clear()
        self._learning_events.clear()
        self._improvements.clear()
        self._user_models.clear()
        self._nudge_queue.clear()
        self._last_nudge_time = 0.0
        self._total_skills_created = 0
        self._total_improvements_applied = 0
        logger.info("EvolutionLoop state reset")


# ── Singleton ────────────────────────────────────────────────────────

evolution_loop = EvolutionLoop()