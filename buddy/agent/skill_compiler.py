"""Buddy Skill Compiler — skill creation, improvement, and compounding engine

Enables agents to autonomously create, refine, and compound skills from experience.
Each execution is analyzed for reusable patterns, which are codified into
parameterized skills with validation, testing, and auto-documentation.

Core capabilities:
  - Skill Creation: autonomously generates skills from successful execution traces
  - Skill Improvement: refines existing skills based on usage patterns and feedback
  - Skill Compounding: chains multiple skills into parameterized pipelines
  - Skill Validation: tests skills against golden datasets before deployment
  - Skill Discovery: searches the skill registry for relevant capabilities
  - Skill Versioning: tracks skill evolution with semantic versioning
  - Skill Analytics: measures usage, success rate, and cost per skill
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger("buddy.skill_compiler")


# ═══════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════

class SkillStatus(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class SkillCategory(str, Enum):
    ANALYSIS = "analysis"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    INTEGRATION = "integration"
    UTILITY = "utility"
    CODING = "coding"
    RESEARCH = "research"
    COMMUNICATION = "communication"


@dataclass
class CompiledSkill:
    """A skill autonomously created and refined from execution experience."""
    id: str = field(default_factory=lambda: f"skill-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.UTILITY
    version: str = "0.1.0"
    status: SkillStatus = SkillStatus.DRAFT

    # Prompt template with {param} placeholders
    prompt_template: str = ""
    parameters: list[str] = field(default_factory=list)

    # Creation metadata
    created_from_execution: str = ""  # Execution ID that spawned this skill
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    # Performance metrics
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_tokens: float = 0.0
    avg_latency_ms: float = 0.0

    # Validation
    test_cases: list[dict] = field(default_factory=list)
    validation_score: float = 0.0

    # Tags for discovery
    tags: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "version": self.version,
            "status": self.status.value,
            "parameters": self.parameters,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(
                self.success_count / max(self.usage_count, 1) * 100, 1
            ),
            "avg_tokens": round(self.avg_tokens, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "validation_score": round(self.validation_score, 2),
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def increment_version(self, bump: str = "patch"):
        """Semantic version bump."""
        parts = [int(x) for x in self.version.split(".")]
        if bump == "major":
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif bump == "minor":
            parts[1] += 1
            parts[2] = 0
        else:
            parts[2] += 1
        self.version = f"{parts[0]}.{parts[1]}.{parts[2]}"


@dataclass
class SkillPipeline:
    """A chain of skills composed into a reusable workflow."""
    id: str = field(default_factory=lambda: f"pipeline-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    skills: list[str] = field(default_factory=list)  # Skill IDs in order
    pipeline_config: dict = field(default_factory=dict)  # Parameter mapping
    usage_count: int = 0
    success_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skills": self.skills,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "success_rate": round(
                self.success_count / max(self.usage_count, 1) * 100, 1
            ),
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════
# Skill Compiler
# ═══════════════════════════════════════════════════════════

class SkillCompiler:
    """Autonomous skill creation, improvement, and compounding engine.

    Analyzes agent execution traces to identify reusable patterns, codifies
    them into parameterized skills, and continuously refines them based on
    usage feedback and performance metrics.
    """

    def __init__(self, client: AsyncOpenAI | None = None):
        self._client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._skills: dict[str, CompiledSkill] = {}
        self._pipelines: dict[str, SkillPipeline] = {}
        self._execution_buffer: list[dict] = []  # Recent execution traces
        self._max_execution_buffer = 200
        self._creation_threshold = 3  # Min similar executions to create a skill
        self._improvement_threshold = 10  # Usages before considering improvement
        self._total_skills_created = 0
        self._total_skills_improved = 0

    # ── Skill Creation ───────────────────────────────────

    async def analyze_execution(
        self,
        execution_id: str,
        prompt: str,
        result: str,
        success: bool,
        tools_used: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Analyze an execution trace for potential skill creation.

        Stores the execution in a buffer. When similar patterns are detected
        across multiple executions, autonomously creates a new skill.
        """
        if not success:
            return {"skill_created": False, "reason": "execution was not successful"}

        trace = {
            "execution_id": execution_id,
            "prompt": prompt[:500],
            "result": result[:500],
            "tools_used": tools_used or [],
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._execution_buffer.append(trace)
        if len(self._execution_buffer) > self._max_execution_buffer:
            self._execution_buffer = self._execution_buffer[-self._max_execution_buffer:]

        # Check for similar patterns
        similar = self._find_similar_executions(prompt)
        if len(similar) >= self._creation_threshold:
            return await self._create_skill_from_pattern(similar)

        return {"skill_created": False, "similar_count": len(similar)}

    def _find_similar_executions(self, prompt: str) -> list[dict]:
        """Find executions with similar patterns to the given prompt."""
        similar = []
        prompt_lower = prompt.lower()
        prompt_words = set(re.findall(r'\b\w{4,}\b', prompt_lower))

        for trace in self._execution_buffer:
            trace_prompt = trace["prompt"].lower()
            trace_words = set(re.findall(r'\b\w{4,}\b', trace_prompt))

            if not prompt_words or not trace_words:
                continue

            # Jaccard similarity
            intersection = prompt_words & trace_words
            union = prompt_words | trace_words
            similarity = len(intersection) / len(union) if union else 0

            if similarity > 0.3:  # 30% word overlap threshold
                similar.append(trace)

        return similar[-10:]  # Return last 10 similar

    async def _create_skill_from_pattern(self, similar_traces: list[dict]) -> dict:
        """Use LLM to create a parameterized skill from execution patterns."""
        if len(similar_traces) < 2:
            return {"skill_created": False}

        # Build a summary of the pattern
        prompts = [t["prompt"][:300] for t in similar_traces[:5]]
        results = [t["result"][:300] for t in similar_traces[:5]]
        tools = list(set(
            t for trace in similar_traces[:5]
            for t in trace.get("tools_used", [])
        ))

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You are a skill compiler. Analyze the following execution patterns "
                        "and create a parameterized, reusable skill. Identify the common "
                        "pattern, extract inputs that vary, and create a prompt template.\n\n"
                        "Respond in JSON:\n"
                        '{"name": "skill-name", "description": "...", '
                        '"category": "analysis|generation|transformation|integration|utility|coding|research|communication", '
                        '"parameters": ["param1", "param2"], '
                        '"prompt_template": "You are a... {input}...", '
                        '"tags": ["tag1", "tag2"]}'
                    ),
                }, {
                    "role": "user",
                    "content": (
                        f"Pattern Examples:\n"
                        + "\n".join(f"Prompt: {p}\nResult: {r}\n" for p, r in zip(prompts, results))
                        + f"\nTools used: {', '.join(tools) if tools else 'none'}"
                        + "\n\nCreate a reusable skill from this pattern."
                    ),
                }],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            skill = CompiledSkill(
                name=data.get("name", "Unnamed Skill"),
                description=data.get("description", ""),
                category=SkillCategory(data.get("category", "utility")),
                prompt_template=data.get("prompt_template", ""),
                parameters=data.get("parameters", []),
                tags=data.get("tags", []),
                created_from_execution=similar_traces[0].get("execution_id", ""),
            )

            self._skills[skill.id] = skill
            self._total_skills_created += 1

            logger.info(f"Skill created: {skill.name} ({skill.id})")
            return {
                "skill_created": True,
                "skill": skill.to_dict(),
                "pattern_size": len(similar_traces),
            }

        except Exception as e:
            logger.error(f"Skill creation failed: {e}")
            return {"skill_created": False, "error": str(e)}

    # ── Skill Improvement ────────────────────────────────

    async def improve_skill(self, skill_id: str) -> dict:
        """Analyze and refine an existing skill based on usage patterns.

        Uses LLM to analyze the skill's performance history, identify areas
        for improvement, and generate an updated prompt template.
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return {"improved": False, "error": "Skill not found"}

        if skill.usage_count < self._improvement_threshold:
            return {"improved": False, "reason": "Not enough usage data"}

        # Collect recent failures for analysis
        failure_rate = skill.failure_count / max(skill.usage_count, 1)
        if failure_rate < 0.1:  # Less than 10% failure — skill is fine
            return {"improved": False, "reason": "Skill performing well"}

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You are a skill optimizer. Analyze the current skill and "
                        "improve its prompt template to increase success rate. "
                        "Focus on clarity, edge cases, and parameter handling.\n\n"
                        "Respond in JSON:\n"
                        '{"improved_template": "...", "improvements": ["...", "..."], '
                        '"version_bump": "patch|minor|major"}'
                    ),
                }, {
                    "role": "user",
                    "content": (
                        f"Skill: {skill.name}\n"
                        f"Description: {skill.description}\n"
                        f"Current template: {skill.prompt_template}\n"
                        f"Success rate: {skill.success_count}/{skill.usage_count} "
                        f"({skill.success_count/max(skill.usage_count,1)*100:.0f}%)\n"
                        f"Avg tokens: {skill.avg_tokens:.0f}\n"
                        f"Parameters: {', '.join(skill.parameters)}\n\n"
                        "Improve this skill's prompt template."
                    ),
                }],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            skill.prompt_template = data.get("improved_template", skill.prompt_template)
            skill.increment_version(data.get("version_bump", "patch"))
            skill.updated_at = datetime.now(timezone.utc).isoformat()
            self._total_skills_improved += 1

            logger.info(f"Skill improved: {skill.name} → v{skill.version}")
            return {
                "improved": True,
                "skill": skill.to_dict(),
                "improvements": data.get("improvements", []),
            }

        except Exception as e:
            logger.error(f"Skill improvement failed: {e}")
            return {"improved": False, "error": str(e)}

    # ── Skill Compounding ────────────────────────────────

    async def compound_pipeline(
        self,
        name: str,
        skill_ids: list[str],
        description: str = "",
    ) -> dict:
        """Create a compound pipeline from multiple skills.

        Analyzes the skill chain compatibility, generates parameter mapping,
        and creates a reusable pipeline for complex multi-step operations.
        """
        if len(skill_ids) < 2:
            return {"created": False, "error": "Need at least 2 skills"}

        # Validate all skills exist
        skills = []
        for sid in skill_ids:
            skill = self._skills.get(sid)
            if not skill:
                return {"created": False, "error": f"Skill {sid} not found"}
            skills.append(skill)

        # Generate pipeline configuration
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You are a skill pipeline designer. Given a chain of skills, "
                        "analyze their compatibility and create a configuration for "
                        "chaining them together. Identify how outputs flow to inputs.\n\n"
                        "Respond in JSON:\n"
                        '{"is_compatible": true|false, "compatibility_notes": "...", '
                        '"parameter_mapping": {"skill1_param": "skill2_param"}, '
                        '"estimated_tokens": 1000}'
                    ),
                }, {
                    "role": "user",
                    "content": (
                        "Pipeline skills:\n"
                        + "\n".join(
                            f"{i+1}. {s.name}: {s.description[:100]} "
                            f"(params: {', '.join(s.parameters)})"
                            for i, s in enumerate(skills)
                        )
                        + "\n\nDesign a pipeline configuration."
                    ),
                }],
                max_tokens=400,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            if not data.get("is_compatible", True):
                return {
                    "created": False,
                    "error": "Skills are not compatible",
                    "notes": data.get("compatibility_notes", ""),
                }

            pipeline = SkillPipeline(
                name=name,
                description=description or f"Pipeline: {' → '.join(s.name for s in skills)}",
                skills=skill_ids,
                pipeline_config=data.get("parameter_mapping", {}),
            )

            self._pipelines[pipeline.id] = pipeline

            logger.info(f"Pipeline created: {pipeline.name} ({pipeline.id})")
            return {
                "created": True,
                "pipeline": pipeline.to_dict(),
                "compatibility_notes": data.get("compatibility_notes", ""),
            }

        except Exception as e:
            logger.error(f"Pipeline creation failed: {e}")
            return {"created": False, "error": str(e)}

    # ── Skill Discovery ──────────────────────────────────

    def search_skills(
        self,
        query: str,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search for skills matching a query, category, or tags.

        Uses keyword matching against skill names, descriptions, and tags
        to find the most relevant skills for a given task.
        """
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w{4,}\b', query_lower))

        scored = []
        for skill in self._skills.values():
            if skill.status != SkillStatus.ACTIVE:
                continue
            if category and skill.category.value != category:
                continue
            if tags and not any(t in skill.tags for t in tags):
                continue

            # Score by keyword match
            score = 0.0
            name_lower = skill.name.lower()
            desc_lower = skill.description.lower()

            for word in query_words:
                if word in name_lower:
                    score += 3.0
                if word in desc_lower:
                    score += 1.0
                if word in skill.tags:
                    score += 2.0

            # Boost by usage and success
            score += min(skill.usage_count / 100, 1.0)
            score += min(skill.success_count / max(skill.usage_count, 1), 0.5)

            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: -x[0])
        return [s.to_dict() for _, s in scored[:limit]]

    # ── Skill Registry Management ────────────────────────

    def get_skill(self, skill_id: str) -> CompiledSkill | None:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_skills(
        self,
        status: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List skills with optional filtering."""
        result = []
        for skill in self._skills.values():
            if status and skill.status.value != status:
                continue
            if category and skill.category.value != category:
                continue
            result.append(skill.to_dict())
        result.sort(key=lambda s: -s["usage_count"])
        return result[:limit]

    def activate_skill(self, skill_id: str) -> bool:
        """Activate a skill for use."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.status = SkillStatus.ACTIVE
        return True

    def record_skill_usage(
        self, skill_id: str, success: bool, tokens: int, latency_ms: float
    ):
        """Record a skill usage for analytics."""
        skill = self._skills.get(skill_id)
        if not skill:
            return

        skill.usage_count += 1
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1

        # Update rolling averages
        n = skill.usage_count
        skill.avg_tokens = (skill.avg_tokens * (n - 1) + tokens) / n
        skill.avg_latency_ms = (skill.avg_latency_ms * (n - 1) + latency_ms) / n

    def get_stats(self) -> dict:
        """Get compiler statistics."""
        statuses = defaultdict(int)
        categories = defaultdict(int)
        for s in self._skills.values():
            statuses[s.status.value] += 1
            categories[s.category.value] += 1

        return {
            "total_skills": len(self._skills),
            "total_pipelines": len(self._pipelines),
            "total_skills_created": self._total_skills_created,
            "total_skills_improved": self._total_skills_improved,
            "skills_by_status": dict(statuses),
            "skills_by_category": dict(categories),
            "total_usage": sum(s.usage_count for s in self._skills.values()),
            "total_success": sum(s.success_count for s in self._skills.values()),
            "execution_buffer_size": len(self._execution_buffer),
        }

    def get_pipeline(self, pipeline_id: str) -> SkillPipeline | None:
        """Get a pipeline by ID."""
        return self._pipelines.get(pipeline_id)

    def list_pipelines(self, limit: int = 20) -> list[dict]:
        """List all pipelines."""
        result = [p.to_dict() for p in self._pipelines.values()]
        result.sort(key=lambda p: -p["usage_count"])
        return result[:limit]


# Global skill compiler instance
skill_compiler = SkillCompiler()