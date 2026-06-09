"""
Buddy Forge — Self-Improving Skill Creation System

An autonomous skill refinery that observes agent execution patterns, identifies
reusable capabilities, and crystallizes them into composable skills. Once forged,
skills improve through usage — tracking success rates, accepting refinements,
and evolving their parameters based on real-world performance.

The Forge is the engine behind Buddy's "closed learning loop" — every task
makes the entire system smarter for the next one.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("buddy.forge")


# ── Skill Models ──

class SkillCategory(str, Enum):
    ANALYSIS = "analysis"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    ORCHESTRATION = "orchestration"
    UTILITY = "utility"
    DOMAIN = "domain"


class SkillStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class SkillParameter:
    """A parameter definition for a forged skill."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    examples: list[str] = field(default_factory=list)

    def dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "examples": self.examples,
        }


@dataclass
class SkillVersion:
    """A specific version of a forged skill."""
    version: int
    prompt_template: str
    parameters: list[SkillParameter]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success_rate: float = 0.0
    execution_count: int = 0
    avg_tokens: int = 0
    avg_latency_ms: float = 0.0

    def dict(self) -> dict:
        return {
            "version": self.version,
            "prompt_template": self.prompt_template,
            "parameters": [p.dict() for p in self.parameters],
            "created_at": self.created_at,
            "success_rate": self.success_rate,
            "execution_count": self.execution_count,
            "avg_tokens": self.avg_tokens,
            "avg_latency_ms": self.avg_latency_ms,
        }


@dataclass
class ForgedSkill:
    """A complete forged skill with version history."""
    skill_id: str
    name: str
    description: str
    category: SkillCategory
    status: SkillStatus = SkillStatus.DRAFT
    tags: list[str] = field(default_factory=list)
    versions: list[SkillVersion] = field(default_factory=list)
    parent_skill_id: str = ""  # If evolved from another skill
    author_agent_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_executions: int = 0
    average_rating: float = 0.0
    failure_patterns: list[str] = field(default_factory=list)

    @property
    def current_version(self) -> SkillVersion | None:
        return self.versions[-1] if self.versions else None

    @property
    def latest_success_rate(self) -> float:
        v = self.current_version
        return v.success_rate if v else 0.0

    def dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "tags": self.tags,
            "versions": [v.dict() for v in self.versions],
            "parent_skill_id": self.parent_skill_id,
            "author_agent_id": self.author_agent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_executions": self.total_executions,
            "average_rating": self.average_rating,
            "latest_success_rate": self.latest_success_rate,
        }


# ── Pattern Recognition ──

@dataclass
class InteractionPattern:
    """A detected pattern in agent interactions that may become a skill."""
    pattern_id: str
    description: str
    trigger_phrases: list[str]
    action_sequence: list[str]
    frequency: int = 0
    confidence: float = 0.0
    suggested_category: SkillCategory = SkillCategory.UTILITY
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "description": self.description,
            "trigger_phrases": self.trigger_phrases,
            "action_sequence": self.action_sequence,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "suggested_category": self.suggested_category.value,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


# ── The Forge ──

class BuddyForge:
    """Autonomous skill creation and refinement engine.

    The Forge observes agent execution traces, detects recurring patterns,
    and crystallizes them into reusable skills. Skills are versioned, tracked,
    and refined through real usage data — creating a compounding knowledge
    base that grows smarter with every interaction.
    """

    def __init__(self, storage_dir: str = ""):
        self._skills: dict[str, ForgedSkill] = {}
        self._patterns: dict[str, InteractionPattern] = {}
        self._pattern_threshold = 3  # Min frequency to promote to skill
        self._min_confidence = 0.6
        self._storage_dir = Path(storage_dir) if storage_dir else None

    # ── Skill Management ──

    def forge_skill(
        self,
        name: str,
        description: str,
        category: SkillCategory,
        prompt_template: str,
        parameters: list[SkillParameter] | None = None,
        author_agent_id: str = "",
        tags: list[str] | None = None,
    ) -> ForgedSkill:
        """Forge a new skill from a template."""
        skill_id = self._generate_id(name)
        if skill_id in self._skills:
            raise ValueError(f"Skill already exists: {skill_id}")

        skill = ForgedSkill(
            skill_id=skill_id,
            name=name,
            description=description,
            category=category,
            author_agent_id=author_agent_id,
            tags=tags or [],
            versions=[
                SkillVersion(
                    version=1,
                    prompt_template=prompt_template,
                    parameters=parameters or [],
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            ],
        )
        self._skills[skill_id] = skill
        logger.info(f"Forge created skill: {skill_id} ({category.value})")
        return skill

    def evolve_skill(
        self,
        skill_id: str,
        new_prompt_template: str,
        new_parameters: list[SkillParameter] | None = None,
        reason: str = "",
    ) -> SkillVersion:
        """Evolve an existing skill to a new version."""
        if skill_id not in self._skills:
            raise ValueError(f"Unknown skill: {skill_id}")

        skill = self._skills[skill_id]
        new_version_num = len(skill.versions) + 1
        new_version = SkillVersion(
            version=new_version_num,
            prompt_template=new_prompt_template,
            parameters=new_parameters or (
                [p for p in skill.current_version.parameters]
                if skill.current_version else []
            ),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        skill.versions.append(new_version)
        skill.updated_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Skill evolved: {skill_id} → v{new_version_num}"
            + (f" ({reason})" if reason else "")
        )
        return new_version

    def get_skill(self, skill_id: str) -> ForgedSkill | None:
        return self._skills.get(skill_id)

    def list_skills(
        self,
        category: SkillCategory | None = None,
        status: SkillStatus | None = None,
        tags: list[str] | None = None,
    ) -> list[ForgedSkill]:
        results = list(self._skills.values())
        if category:
            results = [s for s in results if s.category == category]
        if status:
            results = [s for s in results if s.status == status]
        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]
        return sorted(results, key=lambda s: s.latest_success_rate, reverse=True)

    def deprecate_skill(self, skill_id: str) -> bool:
        """Mark a skill as deprecated."""
        if skill_id not in self._skills:
            return False
        self._skills[skill_id].status = SkillStatus.DEPRECATED
        self._skills[skill_id].updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Skill deprecated: {skill_id}")
        return True

    def archive_skill(self, skill_id: str) -> bool:
        """Archive a skill (soft delete)."""
        if skill_id not in self._skills:
            return False
        self._skills[skill_id].status = SkillStatus.ARCHIVED
        self._skills[skill_id].updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Skill archived: {skill_id}")
        return True

    # ── Execution Tracking ──

    def record_execution(
        self,
        skill_id: str,
        version: int,
        success: bool,
        tokens: int = 0,
        latency_ms: float = 0.0,
        failure_reason: str = "",
    ):
        """Record a skill execution for performance tracking."""
        skill = self._skills.get(skill_id)
        if not skill:
            return

        skill.total_executions += 1
        if len(skill.versions) >= version:
            ver = skill.versions[version - 1]
            ver.execution_count += 1
            old_total = ver.success_rate * (ver.execution_count - 1)
            ver.success_rate = (old_total + (1.0 if success else 0.0)) / ver.execution_count
            if tokens > 0:
                ver.avg_tokens = int(
                    (ver.avg_tokens * (ver.execution_count - 1) + tokens) / ver.execution_count
                )
            if latency_ms > 0:
                ver.avg_latency_ms = (
                    ver.avg_latency_ms * (ver.execution_count - 1) + latency_ms
                ) / ver.execution_count

        if not success and failure_reason:
            skill.failure_patterns.append(failure_reason)
            if len(skill.failure_patterns) > 20:
                skill.failure_patterns = skill.failure_patterns[-20:]

    # ── Pattern Detection ──

    def observe_interaction(
        self,
        user_message: str,
        actions_taken: list[str],
        agent_id: str = "",
    ):
        """Observe an interaction to detect reusable patterns."""
        pattern_hash = self._hash_interaction(actions_taken)

        if pattern_hash in self._patterns:
            pattern = self._patterns[pattern_hash]
            pattern.frequency += 1
            pattern.last_seen = datetime.now(timezone.utc).isoformat()
            pattern.confidence = min(1.0, pattern.confidence + 0.05)

            # Extract trigger phrases
            if user_message and user_message not in pattern.trigger_phrases:
                pattern.trigger_phrases.append(user_message)
                if len(pattern.trigger_phrases) > 10:
                    pattern.trigger_phrases = pattern.trigger_phrases[-10:]
        else:
            pattern = InteractionPattern(
                pattern_id=pattern_hash,
                description=f"Auto-detected pattern from {agent_id or 'unknown'}",
                trigger_phrases=[user_message] if user_message else [],
                action_sequence=actions_taken,
                frequency=1,
                confidence=0.3,
            )
            self._patterns[pattern_hash] = pattern

    def get_promotable_patterns(self) -> list[InteractionPattern]:
        """Get patterns that are ready to be forged into skills."""
        return [
            p for p in self._patterns.values()
            if p.frequency >= self._pattern_threshold
            and p.confidence >= self._min_confidence
        ]

    def promote_to_skill(
        self,
        pattern_id: str,
        name: str,
        description: str,
        prompt_template: str,
        parameters: list[SkillParameter] | None = None,
    ) -> ForgedSkill | None:
        """Promote a detected pattern into a full skill."""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return None

        skill = self.forge_skill(
            name=name,
            description=description or pattern.description,
            category=pattern.suggested_category,
            prompt_template=prompt_template,
            parameters=parameters,
        )
        logger.info(f"Pattern {pattern_id} promoted to skill: {skill.skill_id}")
        return skill

    # ── Statistics ──

    def get_stats(self) -> dict:
        by_category: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for s in self._skills.values():
            c = s.category.value
            by_category[c] = by_category.get(c, 0) + 1
            st = s.status.value
            by_status[st] = by_status.get(st, 0) + 1

        patterns_promotable = len(self.get_promotable_patterns())

        return {
            "total_skills": len(self._skills),
            "total_patterns": len(self._patterns),
            "patterns_ready_for_promotion": patterns_promotable,
            "by_category": by_category,
            "by_status": by_status,
            "total_executions": sum(s.total_executions for s in self._skills.values()),
            "avg_success_rate": (
                sum(s.latest_success_rate for s in self._skills.values()) / max(len(self._skills), 1)
            ),
        }

    # ── Helpers ──

    @staticmethod
    def _generate_id(name: str) -> str:
        slug = name.lower().replace(" ", "-")[:40]
        suffix = hashlib.md5(name.encode()).hexdigest()[:6]
        return f"skill-{slug}-{suffix}"

    @staticmethod
    def _hash_interaction(actions: list[str]) -> str:
        content = "|".join(actions)
        return f"pattern-{hashlib.md5(content.encode()).hexdigest()[:10]}"