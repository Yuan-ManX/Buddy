"""
Buddy Skill Compounding Engine — Self-Improving Skill System
=============================================================
Automatically creates, refines, and curates reusable skills from successful
agent interactions. Skills compound over time, allowing the entire agent
team to benefit from each solved task.

Core Loop:
  1. Task Execution → Record successful patterns
  2. Pattern Analysis → Identify recurring solution strategies
  3. Skill Generation → Create reusable skill definitions
  4. Skill Refinement → Improve skills through usage feedback
  5. Skill Curation → Prune outdated or low-quality skills
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.skill_compounding")


# ── Data Models ────────────────────────────────────────────


@dataclass
class CompoundedSkill:
    """A skill that was automatically generated from successful agent patterns."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: str = "general"
    prompt_template: str = ""
    required_tools: list[str] = field(default_factory=list)
    required_context: dict[str, Any] = field(default_factory=dict)
    source_interactions: list[str] = field(default_factory=list)  # IDs of source interactions
    usage_count: int = 0
    success_rate: float = 1.0
    quality_score: float = 0.5
    version: int = 1
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used_at: str | None = None
    deprecated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "prompt_template": self.prompt_template,
            "required_tools": self.required_tools,
            "required_context": self.required_context,
            "source_interactions": self.source_interactions,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "quality_score": self.quality_score,
            "version": self.version,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_used_at": self.last_used_at,
            "deprecated": self.deprecated,
        }

    def record_usage(self, success: bool):
        """Update usage statistics."""
        self.usage_count += 1
        self.last_used_at = datetime.now(timezone.utc).isoformat()
        # Exponential moving average for success rate
        alpha = 0.1
        self.success_rate = self.success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
        self.updated_at = datetime.now(timezone.utc).isoformat()


@dataclass
class InteractionPattern:
    """A detected pattern from agent interactions."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = ""  # "tool_sequence", "prompt_strategy", "error_recovery"
    description: str = ""
    source_interaction_ids: list[str] = field(default_factory=list)
    tool_sequence: list[str] = field(default_factory=list)
    prompt_fragments: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    occurrence_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "source_interaction_ids": self.source_interaction_ids,
            "tool_sequence": self.tool_sequence,
            "prompt_fragments": self.prompt_fragments,
            "success_rate": self.success_rate,
            "occurrence_count": self.occurrence_count,
            "created_at": self.created_at,
        }


# ── Skill Compounding Engine ───────────────────────────────


class SkillCompoundingEngine:
    """Self-improving skill system that generates skills from interaction patterns.

    The engine observes agent interactions, detects successful patterns,
    and automatically creates reusable skills that compound across the team.
    """

    def __init__(self):
        self._skills: dict[str, CompoundedSkill] = {}
        self._patterns: dict[str, InteractionPattern] = {}
        self._interaction_log: list[dict[str, Any]] = []
        self._max_interactions = 500
        self._min_occurrences_for_skill = 3
        self._min_success_rate_for_skill = 0.7

    # ── Interaction Recording ──────────────────────────

    def record_interaction(
        self,
        agent_id: str,
        task_description: str,
        tool_calls: list[dict[str, Any]],
        success: bool,
        output_summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Record an agent interaction for pattern analysis."""
        interaction_id = str(uuid.uuid4())
        entry = {
            "id": interaction_id,
            "agent_id": agent_id,
            "task_description": task_description,
            "tool_calls": tool_calls,
            "tool_names": [tc.get("name", "") for tc in tool_calls if tc.get("name")],
            "success": success,
            "output_summary": output_summary[:1000],
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._interaction_log.append(entry)

        # Prune old interactions
        if len(self._interaction_log) > self._max_interactions:
            self._interaction_log = self._interaction_log[-self._max_interactions:]

        # Analyze for patterns
        self._analyze_patterns()

        logger.debug(f"Recorded interaction {interaction_id} from {agent_id}")
        return interaction_id

    # ── Pattern Detection ──────────────────────────────

    def _analyze_patterns(self):
        """Analyze interaction log for recurring patterns."""
        # Extract tool sequences from successful interactions
        successful = [i for i in self._interaction_log if i["success"]]
        if len(successful) < self._min_occurrences_for_skill:
            return

        # Find recurring tool sequences
        tool_sequences = self._find_tool_sequences(successful)
        for seq, interactions in tool_sequences.items():
            if len(interactions) >= self._min_occurrences_for_skill:
                pattern_id = self._hash_pattern("tool_sequence", seq)
                if pattern_id not in self._patterns:
                    self._patterns[pattern_id] = InteractionPattern(
                        id=pattern_id,
                        pattern_type="tool_sequence",
                        description=f"Recurring tool sequence: {' → '.join(seq.split('|'))}",
                        tool_sequence=seq.split("|"),
                        source_interaction_ids=[i["id"] for i in interactions],
                        success_rate=sum(1 for i in interactions if i["success"]) / len(interactions),
                        occurrence_count=len(interactions),
                    )

    def _find_tool_sequences(
        self,
        interactions: list[dict[str, Any]],
        min_length: int = 2,
    ) -> dict[str, list[dict[str, Any]]]:
        """Find recurring tool call sequences."""
        sequences: dict[str, list[dict[str, Any]]] = {}
        for interaction in interactions:
            names = interaction.get("tool_names", [])
            # Find all subsequences of length >= min_length
            for start in range(len(names)):
                for end in range(start + min_length, min(start + 5, len(names) + 1)):
                    seq = "|".join(names[start:end])
                    if seq not in sequences:
                        sequences[seq] = []
                    sequences[seq].append(interaction)
        return sequences

    def _hash_pattern(self, pattern_type: str, content: str) -> str:
        return hashlib.sha256(f"{pattern_type}:{content}".encode()).hexdigest()[:16]

    # ── Skill Generation ───────────────────────────────

    def generate_skill_from_pattern(self, pattern_id: str) -> CompoundedSkill | None:
        """Generate a reusable skill from a detected pattern."""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return None

        if pattern.occurrence_count < self._min_occurrences_for_skill:
            return None
        if pattern.success_rate < self._min_success_rate_for_skill:
            return None

        # Build skill name from pattern
        name_parts = pattern.tool_sequence[:3]
        skill_name = "_".join(name_parts).replace("-", "_").lower()

        # Build prompt template
        relevant_interactions = [
            i for i in self._interaction_log
            if i["id"] in pattern.source_interaction_ids
        ]
        prompt_template = self._build_prompt_template(pattern, relevant_interactions)

        skill = CompoundedSkill(
            name=skill_name,
            description=pattern.description,
            category=self._infer_category(pattern.tool_sequence),
            prompt_template=prompt_template,
            required_tools=pattern.tool_sequence,
            required_context={"pattern_id": pattern_id},
            source_interactions=pattern.source_interaction_ids,
            quality_score=pattern.success_rate * 0.8,  # Initial quality estimate
            tags=[f"auto-{pattern.pattern_type}"],
        )

        self._skills[skill.id] = skill
        logger.info(f"Generated skill: {skill.name} (id={skill.id}, quality={skill.quality_score:.2f})")
        return skill

    def _build_prompt_template(
        self,
        pattern: InteractionPattern,
        interactions: list[dict[str, Any]],
    ) -> str:
        """Build a prompt template from successful interactions."""
        steps = []
        for i, tool_name in enumerate(pattern.tool_sequence):
            steps.append(f"Step {i + 1}: Use {tool_name} to complete the necessary operation.")
            # Try to extract reasoning from interactions
            for interaction in interactions:
                for tc in interaction.get("tool_calls", []):
                    if tc.get("name") == tool_name:
                        args = tc.get("args", {})
                        if args:
                            steps.append(f"  Typical parameters: {json.dumps(args, default=str)[:200]}")
                        break
                break

        template = f"""# Auto-generated Skill: {pattern.description}

## Objective
Complete the following tool sequence successfully.

## Steps
{chr(10).join(steps)}

## Notes
- This skill was auto-generated from {pattern.occurrence_count} successful interactions
- Success rate: {pattern.success_rate:.0%}
- If any step fails, check the tool output and retry with adjusted parameters.
"""
        return template

    def _infer_category(self, tool_sequence: list[str]) -> str:
        """Infer skill category from tool names."""
        category_keywords = {
            "file": "file_operations",
            "code": "code_generation",
            "search": "information_retrieval",
            "web": "web_operations",
            "data": "data_processing",
            "db": "database",
            "api": "api_integration",
            "test": "testing",
            "deploy": "deployment",
            "git": "version_control",
        }
        for tool in tool_sequence:
            for keyword, category in category_keywords.items():
                if keyword in tool.lower():
                    return category
        return "general"

    # ── Skill Management ───────────────────────────────

    def get_skill(self, skill_id: str) -> CompoundedSkill | None:
        return self._skills.get(skill_id)

    def list_skills(
        self,
        category: str | None = None,
        min_quality: float = 0.0,
        include_deprecated: bool = False,
    ) -> list[CompoundedSkill]:
        """List skills with optional filtering."""
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        if min_quality > 0:
            skills = [s for s in skills if s.quality_score >= min_quality]
        if not include_deprecated:
            skills = [s for s in skills if not s.deprecated]
        return sorted(skills, key=lambda s: s.quality_score, reverse=True)

    def find_skills_for_task(
        self,
        task_description: str,
        required_tools: list[str] | None = None,
        limit: int = 5,
    ) -> list[CompoundedSkill]:
        """Find relevant skills for a given task."""
        scored: list[tuple[float, CompoundedSkill]] = []
        task_lower = task_description.lower()

        for skill in self._skills.values():
            if skill.deprecated:
                continue
            score = 0.0

            # Match by keywords in description
            desc_words = set(skill.description.lower().split())
            task_words = set(task_lower.split())
            overlap = desc_words & task_words
            if overlap:
                score += len(overlap) / max(len(desc_words), 1) * 0.4

            # Match by tags
            for tag in skill.tags:
                if tag in task_lower:
                    score += 0.2

            # Match by required tools
            if required_tools:
                tool_overlap = set(required_tools) & set(skill.required_tools)
                if tool_overlap:
                    score += len(tool_overlap) / max(len(required_tools), 1) * 0.3

            # Quality bonus
            score += skill.quality_score * 0.1

            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    def update_skill_quality(
        self,
        skill_id: str,
        success: bool,
        feedback: str = "",
    ):
        """Update skill quality based on usage feedback."""
        skill = self._skills.get(skill_id)
        if not skill:
            return
        skill.record_usage(success)
        # Adjust quality based on feedback
        if success:
            skill.quality_score = min(1.0, skill.quality_score + 0.02)
        else:
            skill.quality_score = max(0.1, skill.quality_score - 0.05)
        if feedback:
            logger.info(f"Skill {skill.name} feedback: {feedback}")

    def deprecate_skill(self, skill_id: str) -> bool:
        """Mark a skill as deprecated."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.deprecated = True
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def delete_skill(self, skill_id: str) -> bool:
        return self._skills.pop(skill_id, None) is not None

    # ── Bulk Operations ────────────────────────────────

    def generate_all_skills(self) -> list[CompoundedSkill]:
        """Generate skills from all qualified patterns."""
        new_skills = []
        for pattern_id in self._patterns:
            # Check if skill already exists for this pattern
            existing = [
                s for s in self._skills.values()
                if s.required_context.get("pattern_id") == pattern_id
            ]
            if not existing:
                skill = self.generate_skill_from_pattern(pattern_id)
                if skill:
                    new_skills.append(skill)
        return new_skills

    def prune_low_quality_skills(self, threshold: float = 0.2):
        """Deprecate skills below quality threshold."""
        for skill in self._skills.values():
            if skill.quality_score < threshold and skill.usage_count > 5:
                skill.deprecated = True
                logger.info(f"Pruned low-quality skill: {skill.name}")

    # ── Export / Import ────────────────────────────────

    def export_skills(self, format: str = "json") -> str:
        """Export all skills in the specified format."""
        skills_data = [s.to_dict() for s in self._skills.values() if not s.deprecated]
        if format == "jsonl":
            return "\n".join(json.dumps(s) for s in skills_data)
        return json.dumps(skills_data, indent=2, default=str)

    def import_skills(self, data: str, format: str = "json") -> int:
        """Import skills from serialized data."""
        count = 0
        try:
            if format == "jsonl":
                for line in data.strip().split("\n"):
                    if line.strip():
                        skill_data = json.loads(line)
                        self._import_skill(skill_data)
                        count += 1
            else:
                skills_data = json.loads(data)
                for skill_data in skills_data:
                    self._import_skill(skill_data)
                    count += 1
        except Exception as e:
            logger.error(f"Skill import error: {e}")
        return count

    def _import_skill(self, data: dict[str, Any]):
        skill = CompoundedSkill(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            prompt_template=data.get("prompt_template", ""),
            required_tools=data.get("required_tools", []),
            required_context=data.get("required_context", {}),
            source_interactions=data.get("source_interactions", []),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 1.0),
            quality_score=data.get("quality_score", 0.5),
            version=data.get("version", 1),
            tags=data.get("tags", []),
            deprecated=data.get("deprecated", False),
        )
        self._skills[skill.id] = skill

    # ── Stats ──────────────────────────────────────────

    def get_patterns(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._patterns.values()]

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        by_category: dict[str, int] = {}
        for skill in self._skills.values():
            if not skill.deprecated:
                by_category[skill.category] = by_category.get(skill.category, 0) + 1

        return {
            "total_skills": len(self._skills),
            "active_skills": len([s for s in self._skills.values() if not s.deprecated]),
            "deprecated_skills": len([s for s in self._skills.values() if s.deprecated]),
            "total_patterns": len(self._patterns),
            "interactions_recorded": len(self._interaction_log),
            "by_category": by_category,
            "avg_quality": (
                sum(s.quality_score for s in self._skills.values() if not s.deprecated)
                / max(len([s for s in self._skills.values() if not s.deprecated]), 1)
            ),
            "total_usage": sum(s.usage_count for s in self._skills.values()),
        }


# ── Singleton ──────────────────────────────────────────────

skill_compounding = SkillCompoundingEngine()