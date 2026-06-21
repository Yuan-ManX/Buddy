"""Buddy Self-Improvement Engine — autonomous skill synthesis and nudge system

Implements a continuous improvement loop where the agent:
- Synthesizes reusable skills from successful operations
- Detects patterns and creates composite workflows
- Self-nudges to persist knowledge, improve responses, and adapt behavior
- Manages a skill lifecycle: creation, refinement, deprecation, archival
- Tracks improvement metrics and generates optimization insights
- Compounds skills with dependency tracking
- Synthesizes cross-category bridging skills
- Benchmarks skill performance and tracks improvement velocity
- Recommends optimal skills for given tasks
- Adaptively tunes synthesis thresholds based on performance data
- Analyzes improvement trends over time
"""
from __future__ import annotations

import json
import logging
import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.self_improve")


class SkillOrigin(str, Enum):
    AUTO_SYNTHESIZED = "auto_synthesized"
    PATTERN_DETECTED = "pattern_detected"
    USER_DEFINED = "user_defined"
    IMPORTED = "imported"


class SkillLifecycle(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    REFINING = "refining"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class NudgeType(str, Enum):
    KNOWLEDGE_PERSIST = "knowledge_persist"
    RESPONSE_IMPROVE = "response_improve"
    BEHAVIOR_ADAPT = "behavior_adapt"
    SKILL_SUGGEST = "skill_suggest"
    EFFICIENCY_OPTIMIZE = "efficiency_optimize"


class NudgePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SynthesizedSkill:
    """A skill automatically created from successful operations."""
    skill_id: str = field(default_factory=lambda: f"skill-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    category: str = "general"
    steps: list[dict[str, Any]] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    success_rate: float = 0.0
    usage_count: int = 0
    origin: SkillOrigin = SkillOrigin.AUTO_SYNTHESIZED
    lifecycle: SkillLifecycle = SkillLifecycle.DRAFT
    source_patterns: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "steps_count": len(self.steps),
            "tools_required": self.tools_required,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "origin": self.origin.value,
            "lifecycle": self.lifecycle.value,
            "quality_score": self.quality_score,
            "version": self.version,
            "tags": self.tags,
        }


@dataclass
class AgentNudge:
    """A self-generated suggestion for agent improvement."""
    nudge_id: str = field(default_factory=lambda: f"nudge-{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    nudge_type: NudgeType = NudgeType.KNOWLEDGE_PERSIST
    priority: NudgePriority = NudgePriority.MEDIUM
    title: str = ""
    description: str = ""
    suggested_action: str = ""
    evidence: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    applied: bool = False
    applied_at: str | None = None
    impact_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "nudge_id": self.nudge_id,
            "agent_id": self.agent_id,
            "nudge_type": self.nudge_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "suggested_action": self.suggested_action,
            "applied": self.applied,
            "impact_score": self.impact_score,
        }


@dataclass
class ImprovementMetrics:
    """Tracked metrics for measuring agent improvement over time."""
    total_skills_synthesized: int = 0
    total_nudges_generated: int = 0
    total_nudges_applied: int = 0
    average_skill_success_rate: float = 0.0
    skills_active: int = 0
    skills_deprecated: int = 0
    improvement_cycles_run: int = 0
    last_cycle_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_skills_synthesized": self.total_skills_synthesized,
            "total_nudges_generated": self.total_nudges_generated,
            "total_nudges_applied": self.total_nudges_applied,
            "average_skill_success_rate": round(self.average_skill_success_rate, 3),
            "skills_active": self.skills_active,
            "skills_deprecated": self.skills_deprecated,
            "improvement_cycles_run": self.improvement_cycles_run,
            "last_cycle_at": self.last_cycle_at,
        }


@dataclass
class CompositeSkill:
    """A skill created by compounding multiple existing skills with dependency tracking."""
    composite_id: str = field(default_factory=lambda: f"composite-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    source_skill_ids: list[str] = field(default_factory=list)
    # Maps each skill_id to the list of skill_ids it depends on (must execute first)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    combined_steps: list[dict[str, Any]] = field(default_factory=list)
    combined_tools: list[str] = field(default_factory=list)
    category: str = "composite"
    success_rate: float = 0.0
    usage_count: int = 0
    quality_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite_id": self.composite_id,
            "name": self.name,
            "description": self.description,
            "source_skill_ids": self.source_skill_ids,
            "dependencies": self.dependencies,
            "steps_count": len(self.combined_steps),
            "tools_required": self.combined_tools,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "category": self.category,
            "quality_score": self.quality_score,
            "version": self.version,
        }

    def get_execution_order(self) -> list[str]:
        """Return skill_ids in topological order based on dependencies."""
        in_degree: dict[str, int] = {sid: 0 for sid in self.source_skill_ids}
        adjacency: dict[str, list[str]] = {sid: [] for sid in self.source_skill_ids}

        for sid, deps in self.dependencies.items():
            for dep in deps:
                if dep in adjacency and sid in in_degree:
                    adjacency[dep].append(sid)
                    in_degree[sid] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        order: list[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for neighbor in adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order


@dataclass
class SkillBenchmark:
    """Benchmark result comparing skill performance and tracking improvement velocity."""
    skill_id: str = ""
    skill_name: str = ""
    category: str = ""
    success_rate: float = 0.0
    usage_count: int = 0
    quality_score: float = 0.0
    improvement_velocity: float = 0.0
    # The compound score for ranking (higher is better)
    composite_score: float = 0.0
    benchmarked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "category": self.category,
            "success_rate": round(self.success_rate, 4),
            "usage_count": self.usage_count,
            "quality_score": round(self.quality_score, 4),
            "improvement_velocity": round(self.improvement_velocity, 4),
            "composite_score": round(self.composite_score, 4),
            "benchmarked_at": self.benchmarked_at,
        }


@dataclass
class TrendSnapshot:
    """A point-in-time snapshot of improvement metrics for trend analysis."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_skills: int = 0
    active_skills: int = 0
    avg_success_rate: float = 0.0
    improvement_cycles: int = 0
    nudges_applied: int = 0
    skills_synthesized: int = 0
    composite_skills: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_skills": self.total_skills,
            "active_skills": self.active_skills,
            "avg_success_rate": round(self.avg_success_rate, 4),
            "improvement_cycles": self.improvement_cycles,
            "nudges_applied": self.nudges_applied,
            "skills_synthesized": self.skills_synthesized,
            "composite_skills": self.composite_skills,
        }


class SelfImprovementEngine:
    """Autonomous self-improvement system for Buddy agents.

    Continuously analyzes agent operations to synthesize reusable skills,
    generate improvement nudges, and optimize behavior patterns. Implements
    a full skill lifecycle from creation through refinement to archival.
    Supports skill compounding, cross-skill synthesis, benchmarking,
    recommendation, adaptive threshold tuning, and trend analysis.
    """

    MIN_PATTERN_SUPPORT = 3
    SYNTHESIS_QUALITY_THRESHOLD = 0.6

    def __init__(self):
        self._skills: dict[str, SynthesizedSkill] = {}
        self._nudges: dict[str, AgentNudge] = {}
        self._operation_patterns: dict[str, list[dict[str, Any]]] = {}
        self._metrics = ImprovementMetrics()
        # Storage for composite skills created via skill compounding
        self._composite_skills: dict[str, CompositeSkill] = {}
        # History of benchmark snapshots for velocity tracking
        self._benchmark_history: list[dict[str, SkillBenchmark]] = []
        # Trend snapshots for improvement trend analysis
        self._trend_snapshots: list[TrendSnapshot] = []

    # ── Skill Synthesis ─────────────────────────────────────────────

    def synthesize_skill(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        tools_required: list[str] | None = None,
        category: str = "general",
        tags: list[str] | None = None,
    ) -> SynthesizedSkill:
        """Create a new skill from successful operation patterns."""
        skill = SynthesizedSkill(
            name=name,
            description=description,
            category=category,
            steps=steps,
            tools_required=tools_required or [],
            tags=tags or [],
            origin=SkillOrigin.AUTO_SYNTHESIZED,
            lifecycle=SkillLifecycle.DRAFT,
            quality_score=self._estimate_skill_quality(steps, tools_required or []),
        )
        self._skills[skill.skill_id] = skill
        self._metrics.total_skills_synthesized += 1
        self._metrics.skills_active += 1
        logger.info(f"Skill synthesized: {name} ({skill.skill_id})")
        return skill

    def synthesize_from_pattern(
        self,
        pattern_name: str,
        operations: list[dict[str, Any]],
    ) -> SynthesizedSkill | None:
        """Synthesize a skill from a detected operation pattern."""
        if len(operations) < self.MIN_PATTERN_SUPPORT:
            return None

        # Extract common steps and tools
        all_steps = []
        all_tools: set[str] = set()
        for op in operations:
            if "steps" in op:
                all_steps.extend(op["steps"])
            if "tools_used" in op:
                all_tools.update(op["tools_used"])

        # Deduplicate and order steps
        unique_steps = self._deduplicate_steps(all_steps)

        if not unique_steps:
            return None

        skill = self.synthesize_skill(
            name=pattern_name.replace("_", " ").title(),
            description=f"Auto-synthesized skill from pattern: {pattern_name}",
            steps=unique_steps,
            tools_required=list(all_tools),
            category="pattern_detected",
            tags=[pattern_name],
        )
        skill.origin = SkillOrigin.PATTERN_DETECTED
        skill.source_patterns = [pattern_name]
        return skill

    def _deduplicate_steps(
        self, steps: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Remove duplicate steps while preserving order."""
        seen = set()
        unique = []
        for step in steps:
            key = json.dumps(step, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                unique.append(step)
        return unique

    def _estimate_skill_quality(
        self, steps: list[dict[str, Any]], tools: list[str],
    ) -> float:
        """Estimate the quality of a synthesized skill."""
        score = 0.5
        if len(steps) >= 3:
            score += 0.15
        if len(tools) > 0:
            score += 0.1
        if len(steps) >= 5:
            score += 0.1
        # Check for structured steps
        has_descriptions = any(
            s.get("description") or s.get("action") for s in steps
        )
        if has_descriptions:
            score += 0.1
        return min(score, 1.0)

    # ── Skill Lifecycle ─────────────────────────────────────────────

    def activate_skill(self, skill_id: str) -> bool:
        """Activate a draft skill for use."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.lifecycle = SkillLifecycle.ACTIVE
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def refine_skill(
        self, skill_id: str, updates: dict[str, Any],
    ) -> SynthesizedSkill | None:
        """Refine an existing skill with improvements."""
        skill = self._skills.get(skill_id)
        if not skill:
            return None
        skill.lifecycle = SkillLifecycle.REFINING

        if "steps" in updates:
            skill.steps = updates["steps"]
        if "description" in updates:
            skill.description = updates["description"]
        if "tools_required" in updates:
            skill.tools_required = updates["tools_required"]

        skill.version += 1
        skill.quality_score = self._estimate_skill_quality(
            skill.steps, skill.tools_required,
        )
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        skill.lifecycle = SkillLifecycle.ACTIVE
        return skill

    def deprecate_skill(self, skill_id: str) -> bool:
        """Mark a skill as deprecated."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.lifecycle = SkillLifecycle.DEPRECATED
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        self._metrics.skills_active -= 1
        self._metrics.skills_deprecated += 1
        return True

    def archive_skill(self, skill_id: str) -> bool:
        """Archive a deprecated skill."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.lifecycle = SkillLifecycle.ARCHIVED
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def record_skill_usage(self, skill_id: str, success: bool) -> None:
        """Record a skill usage for success rate tracking."""
        skill = self._skills.get(skill_id)
        if not skill:
            return
        skill.usage_count += 1
        if skill.usage_count > 0:
            skill.success_rate = (
                (skill.success_rate * (skill.usage_count - 1) + (1.0 if success else 0.0))
                / skill.usage_count
            )
        skill.updated_at = datetime.now(timezone.utc).isoformat()

    def rollback_skill(self, skill_id: str) -> SynthesizedSkill | None:
        """Rollback a skill to its previous version."""
        skill = self._skills.get(skill_id)
        if not skill or skill.version <= 1:
            return None
        skill.version -= 1
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        return skill

    # ── Nudge System ────────────────────────────────────────────────

    def generate_nudge(
        self,
        agent_id: str,
        nudge_type: NudgeType,
        title: str,
        description: str,
        suggested_action: str = "",
        evidence: list[str] | None = None,
        priority: NudgePriority = NudgePriority.MEDIUM,
    ) -> AgentNudge:
        """Generate a self-improvement nudge for the agent."""
        nudge = AgentNudge(
            agent_id=agent_id,
            nudge_type=nudge_type,
            priority=priority,
            title=title,
            description=description,
            suggested_action=suggested_action,
            evidence=evidence or [],
        )
        self._nudges[nudge.nudge_id] = nudge
        self._metrics.total_nudges_generated += 1
        return nudge

    def apply_nudge(self, nudge_id: str) -> bool:
        """Mark a nudge as applied."""
        nudge = self._nudges.get(nudge_id)
        if not nudge:
            return False
        nudge.applied = True
        nudge.applied_at = datetime.now(timezone.utc).isoformat()
        self._metrics.total_nudges_applied += 1
        return True

    def revert_nudge(self, nudge_id: str) -> bool:
        """Revert an applied nudge."""
        nudge = self._nudges.get(nudge_id)
        if not nudge:
            return False
        nudge.applied = False
        nudge.applied_at = None
        self._metrics.total_nudges_applied -= 1
        return True

    def dismiss_nudge(self, nudge_id: str) -> bool:
        """Dismiss a nudge without applying."""
        nudge = self._nudges.get(nudge_id)
        if not nudge:
            return False
        nudge.applied = False
        return True

    def analyze_and_nudge(self, agent_id: str) -> list[AgentNudge]:
        """Analyze agent state and generate improvement nudges."""
        nudges: list[AgentNudge] = []

        # Check for skill synthesis opportunities
        pending_patterns = sum(
            1 for p in self._operation_patterns.values()
            if len(p) >= self.MIN_PATTERN_SUPPORT
        )
        if pending_patterns > 0:
            nudges.append(self.generate_nudge(
                agent_id=agent_id,
                nudge_type=NudgeType.SKILL_SUGGEST,
                title="Skill Synthesis Opportunity",
                description=f"Found {pending_patterns} patterns with enough support for skill synthesis.",
                suggested_action="Run auto-synthesize to create new skills from detected patterns.",
                priority=NudgePriority.HIGH,
            ))

        # Check for deprecated skills
        deprecated = [
            s for s in self._skills.values()
            if s.lifecycle == SkillLifecycle.DEPRECATED
        ]
        if deprecated:
            nudges.append(self.generate_nudge(
                agent_id=agent_id,
                nudge_type=NudgeType.BEHAVIOR_ADAPT,
                title="Archive Deprecated Skills",
                description=f"Found {len(deprecated)} deprecated skills that should be archived.",
                suggested_action="Review and archive deprecated skills to keep the skill library clean.",
                priority=NudgePriority.LOW,
            ))

        return nudges

    # ── Pattern Detection ───────────────────────────────────────────

    def record_operation_pattern(
        self,
        pattern_name: str,
        operation: dict[str, Any],
    ) -> None:
        """Record an operation for pattern detection."""
        if pattern_name not in self._operation_patterns:
            self._operation_patterns[pattern_name] = []
        self._operation_patterns[pattern_name].append(operation)

    def detect_patterns(self) -> list[dict[str, Any]]:
        """Detect recurring operation patterns ready for synthesis."""
        patterns = []
        for name, ops in self._operation_patterns.items():
            if len(ops) >= self.MIN_PATTERN_SUPPORT:
                patterns.append({
                    "pattern_name": name,
                    "occurrence_count": len(ops),
                    "ready_for_synthesis": True,
                    "sample_operations": ops[:3],
                })
        return patterns

    def auto_synthesize_from_patterns(self) -> list[SynthesizedSkill]:
        """Automatically synthesize skills from all detected patterns."""
        new_skills = []
        for name, ops in self._operation_patterns.items():
            if len(ops) >= self.MIN_PATTERN_SUPPORT:
                skill = self.synthesize_from_pattern(name, ops)
                if skill:
                    self.activate_skill(skill.skill_id)
                    new_skills.append(skill)
        return new_skills

    # ── Improvement Cycle ───────────────────────────────────────────

    async def run_improvement_cycle(self, agent_id: str) -> dict[str, Any]:
        """Run a full improvement cycle: analyze, nudge, synthesize."""
        start_time = time.time()

        # Detect patterns
        patterns = self.detect_patterns()

        # Auto-synthesize skills from patterns
        new_skills = self.auto_synthesize_from_patterns()

        # Generate nudges
        nudges = self.analyze_and_nudge(agent_id)

        self._metrics.improvement_cycles_run += 1
        self._metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()

        # Update average success rate
        active_skills = [s for s in self._skills.values() if s.lifecycle == SkillLifecycle.ACTIVE]
        if active_skills:
            self._metrics.average_skill_success_rate = sum(
                s.success_rate for s in active_skills
            ) / len(active_skills)

        return {
            "agent_id": agent_id,
            "patterns_detected": len(patterns),
            "skills_synthesized": len(new_skills),
            "nudges_generated": len(nudges),
            "duration_ms": (time.time() - start_time) * 1000,
            "new_skill_ids": [s.skill_id for s in new_skills],
            "nudge_ids": [n.nudge_id for n in nudges],
        }

    # ── Query Methods ───────────────────────────────────────────────

    def get_skills(
        self,
        lifecycle: SkillLifecycle | None = None,
        category: str | None = None,
    ) -> list[SynthesizedSkill]:
        """Get skills, optionally filtered by lifecycle or category."""
        skills = list(self._skills.values())
        if lifecycle:
            skills = [s for s in skills if s.lifecycle == lifecycle]
        if category:
            skills = [s for s in skills if s.category == category]
        return sorted(skills, key=lambda s: s.quality_score, reverse=True)

    def get_skill(self, skill_id: str) -> SynthesizedSkill | None:
        """Get a specific skill by ID."""
        return self._skills.get(skill_id)

    def get_nudges(
        self,
        agent_id: str | None = None,
        applied: bool | None = None,
    ) -> list[AgentNudge]:
        """Get nudges, optionally filtered."""
        nudges = list(self._nudges.values())
        if agent_id:
            nudges = [n for n in nudges if n.agent_id == agent_id]
        if applied is not None:
            nudges = [n for n in nudges if n.applied == applied]
        return sorted(nudges, key=lambda n: n.created_at, reverse=True)

    def get_metrics(self) -> dict[str, Any]:
        """Get current improvement metrics."""
        return self._metrics.to_dict()

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "metrics": self._metrics.to_dict(),
            "total_skills": len(self._skills),
            "active_skills": self._metrics.skills_active,
            "total_nudges": len(self._nudges),
            "patterns_detected": len(self._operation_patterns),
            "patterns_ready": sum(
                1 for ops in self._operation_patterns.values()
                if len(ops) >= self.MIN_PATTERN_SUPPORT
            ),
        }

    # ── Skill Compounding ───────────────────────────────────────────

    def compound_skills(
        self,
        skill_ids: list[str],
        name: str,
        description: str = "",
        dependencies: dict[str, list[str]] | None = None,
    ) -> CompositeSkill | None:
        """Combine multiple existing skills into a composite skill with dependency tracking.

        Args:
            skill_ids: List of existing skill IDs to compound together.
            name: Name for the new composite skill.
            description: Human-readable description of the composite skill.
            dependencies: Mapping of skill_id -> [dependent_skill_ids] indicating
                which skills must execute before others. If not provided, skills
                are assumed to have no ordering constraints.

        Returns:
            A new CompositeSkill if at least two valid skills are provided, else None.
        """
        if len(skill_ids) < 2:
            logger.warning("Skill compounding requires at least 2 skills.")
            return None

        # Resolve and validate all source skills
        resolved: list[SynthesizedSkill] = []
        for sid in skill_ids:
            skill = self._skills.get(sid)
            if skill is None:
                logger.warning(f"Skill not found for compounding: {sid}")
                continue
            resolved.append(skill)

        if len(resolved) < 2:
            logger.warning("Not enough valid skills for compounding.")
            return None

        # Build combined steps and tools, respecting dependency ordering
        dep_map = dependencies or {}
        # Validate that all referenced skills in dependencies exist in resolved
        all_resolved_ids = {s.skill_id for s in resolved}
        validated_deps: dict[str, list[str]] = {}
        for sid, deps in dep_map.items():
            if sid in all_resolved_ids:
                validated_deps[sid] = [d for d in deps if d in all_resolved_ids]

        combined_steps: list[dict[str, Any]] = []
        combined_tools: list[str] = []
        seen_tools: set[str] = set()

        # Order skills: those with no dependencies first, then dependents
        ordered_ids = self._topological_order(resolved, validated_deps)
        ordered_skills = {s.skill_id: s for s in resolved}

        for sid in ordered_ids:
            if sid in ordered_skills:
                sk = ordered_skills[sid]
                combined_steps.extend(sk.steps)
                for tool in sk.tools_required:
                    if tool not in seen_tools:
                        seen_tools.add(tool)
                        combined_tools.append(tool)

        # Compute quality as weighted average of source skill qualities
        total_quality = sum(s.quality_score for s in resolved)
        avg_quality = total_quality / len(resolved) if resolved else 0.0

        composite = CompositeSkill(
            name=name,
            description=description or f"Composite of: {', '.join(s.name for s in resolved)}",
            source_skill_ids=[s.skill_id for s in resolved],
            dependencies=validated_deps,
            combined_steps=combined_steps,
            combined_tools=combined_tools,
            category="composite",
            quality_score=round(avg_quality, 4),
        )
        self._composite_skills[composite.composite_id] = composite
        logger.info(
            "Composite skill created: %s (%s) from %d source skills",
            name, composite.composite_id, len(resolved),
        )
        return composite

    def get_composite_skill(self, composite_id: str) -> CompositeSkill | None:
        """Retrieve a composite skill by its ID."""
        return self._composite_skills.get(composite_id)

    def get_all_composite_skills(self) -> list[CompositeSkill]:
        """Return all registered composite skills."""
        return list(self._composite_skills.values())

    def _topological_order(
        self,
        skills: list[SynthesizedSkill],
        dependencies: dict[str, list[str]],
    ) -> list[str]:
        """Compute a topological ordering of skill IDs based on dependencies."""
        skill_ids = {s.skill_id for s in skills}
        in_degree: dict[str, int] = {sid: 0 for sid in skill_ids}
        adjacency: dict[str, list[str]] = {sid: [] for sid in skill_ids}

        for sid, deps in dependencies.items():
            for dep in deps:
                if dep in adjacency and sid in in_degree:
                    adjacency[dep].append(sid)
                    in_degree[sid] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        order: list[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for neighbor in adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Append any remaining skills not covered by dependency edges
        for sid in skill_ids:
            if sid not in order:
                order.append(sid)

        return order

    # ── Cross-Skill Synthesis ───────────────────────────────────────

    def cross_skill_synthesize(
        self,
        category_a: str,
        category_b: str,
    ) -> list[SynthesizedSkill]:
        """Identify and create skills that bridge gaps between two different skill categories.

        Analyzes skills in two categories, finds complementary tool/steps patterns,
        and synthesizes bridging skills that combine capabilities from both categories.

        Args:
            category_a: First skill category to bridge from.
            category_b: Second skill category to bridge to.

        Returns:
            List of newly synthesized bridging skills.
        """
        skills_a = self.get_skills(category=category_a)
        skills_b = self.get_skills(category=category_b)

        if not skills_a or not skills_b:
            logger.info(
                "Cross-skill synthesis requires skills in both categories. "
                "Found %d in '%s' and %d in '%s'.",
                len(skills_a), category_a, len(skills_b), category_b,
            )
            return []

        new_bridge_skills: list[SynthesizedSkill] = []

        # Collect all tools from each category
        tools_a: set[str] = set()
        tools_b: set[str] = set()
        for sk in skills_a:
            tools_a.update(sk.tools_required)
        for sk in skills_b:
            tools_b.update(sk.tools_required)

        # Find complementary tools: tools in B that are not in A (gap to bridge)
        bridging_tools = tools_b - tools_a

        # Find complementary tools the other way
        bridging_tools_reverse = tools_a - tools_b

        # Synthesize bridging skills for each direction
        if bridging_tools:
            # Combine steps from category A with tools from category B
            bridge_steps = self._merge_category_steps(skills_a, skills_b)
            bridge_skill = self.synthesize_skill(
                name=f"Bridge: {category_a.title()} → {category_b.title()}",
                description=(
                    f"Bridging skill that combines {category_a} patterns with "
                    f"{category_b} tools: {', '.join(sorted(bridging_tools)[:5])}"
                ),
                steps=bridge_steps,
                tools_required=list(tools_a | bridging_tools),
                category="cross_synthesis",
                tags=[category_a, category_b, "bridge"],
            )
            bridge_skill.origin = SkillOrigin.AUTO_SYNTHESIZED
            self.activate_skill(bridge_skill.skill_id)
            new_bridge_skills.append(bridge_skill)

        if bridging_tools_reverse and bridging_tools_reverse != bridging_tools:
            bridge_steps_rev = self._merge_category_steps(skills_b, skills_a)
            bridge_skill_rev = self.synthesize_skill(
                name=f"Bridge: {category_b.title()} → {category_a.title()}",
                description=(
                    f"Bridging skill that combines {category_b} patterns with "
                    f"{category_a} tools: {', '.join(sorted(bridging_tools_reverse)[:5])}"
                ),
                steps=bridge_steps_rev,
                tools_required=list(tools_b | bridging_tools_reverse),
                category="cross_synthesis",
                tags=[category_a, category_b, "bridge"],
            )
            bridge_skill_rev.origin = SkillOrigin.AUTO_SYNTHESIZED
            self.activate_skill(bridge_skill_rev.skill_id)
            new_bridge_skills.append(bridge_skill_rev)

        logger.info(
            "Cross-skill synthesis between '%s' and '%s' produced %d bridging skills.",
            category_a, category_b, len(new_bridge_skills),
        )
        return new_bridge_skills

    def _merge_category_steps(
        self,
        primary_skills: list[SynthesizedSkill],
        secondary_skills: list[SynthesizedSkill],
    ) -> list[dict[str, Any]]:
        """Merge steps from two skill groups, prioritizing primary category steps."""
        merged: list[dict[str, Any]] = []
        seen_step_keys: set[str] = set()

        for sk in primary_skills:
            for step in sk.steps:
                key = json.dumps(step, sort_keys=True, default=str)
                if key not in seen_step_keys:
                    seen_step_keys.add(key)
                    merged.append(step)

        for sk in secondary_skills:
            for step in sk.steps:
                key = json.dumps(step, sort_keys=True, default=str)
                if key not in seen_step_keys:
                    seen_step_keys.add(key)
                    merged.append(step)

        return merged

    # ── Performance Benchmarking ────────────────────────────────────

    def benchmark_skills(self) -> list[SkillBenchmark]:
        """Benchmark all active skills against each other and track improvement velocity.

        Computes a composite score for each skill based on success rate, usage count,
        and quality score. Compares against the previous benchmark snapshot to
        calculate improvement velocity (rate of change per cycle).

        Returns:
            List of SkillBenchmark results sorted by composite score descending.
        """
        active_skills = self.get_skills(lifecycle=SkillLifecycle.ACTIVE)
        if not active_skills:
            return []

        # Build previous benchmark lookup for velocity calculation
        prev_benchmarks: dict[str, SkillBenchmark] = {}
        if self._benchmark_history:
            prev_benchmarks = self._benchmark_history[-1]

        current_benchmarks: dict[str, SkillBenchmark] = {}
        max_usage = max((s.usage_count for s in active_skills), default=1)

        for skill in active_skills:
            # Normalize usage count to a 0-1 scale for composite scoring
            usage_score = skill.usage_count / max_usage if max_usage > 0 else 0.0

            # Composite score: weighted combination of success_rate, usage, and quality
            composite_score = (
                0.40 * skill.success_rate
                + 0.30 * usage_score
                + 0.30 * skill.quality_score
            )

            # Calculate improvement velocity relative to previous benchmark
            prev = prev_benchmarks.get(skill.skill_id)
            if prev and prev.composite_score > 0:
                improvement_velocity = (
                    (composite_score - prev.composite_score) / prev.composite_score
                )
            else:
                improvement_velocity = 0.0

            benchmark = SkillBenchmark(
                skill_id=skill.skill_id,
                skill_name=skill.name,
                category=skill.category,
                success_rate=skill.success_rate,
                usage_count=skill.usage_count,
                quality_score=skill.quality_score,
                improvement_velocity=round(improvement_velocity, 4),
                composite_score=round(composite_score, 4),
            )
            current_benchmarks[skill.skill_id] = benchmark

        # Store this benchmark snapshot for future velocity calculations
        self._benchmark_history.append(current_benchmarks)

        # Return sorted by composite score (best first)
        return sorted(
            current_benchmarks.values(),
            key=lambda b: b.composite_score,
            reverse=True,
        )

    def get_benchmark_history(self) -> list[dict[str, Any]]:
        """Return the full benchmark history as a list of snapshots."""
        return [
            {sid: b.to_dict() for sid, b in snapshot.items()}
            for snapshot in self._benchmark_history
        ]

    # ── Skill Recommendation Engine ─────────────────────────────────

    def recommend_skill(
        self,
        task_description: str,
        required_tools: list[str] | None = None,
        preferred_category: str | None = None,
        min_success_rate: float = 0.0,
        top_k: int = 3,
    ) -> list[SynthesizedSkill]:
        """Recommend the best skill(s) for a given task based on success rates and context.

        Scores each active skill by matching the task description against skill name,
        description, tags, and category. Skills that match required tools get a boost.
        Results are filtered by minimum success rate and ranked by relevance.

        Args:
            task_description: Natural language description of the task.
            required_tools: Tools that the task is expected to use.
            preferred_category: Preferred skill category for the task.
            min_success_rate: Minimum required success rate (0.0-1.0).
            top_k: Maximum number of recommendations to return.

        Returns:
            Ranked list of recommended skills, up to top_k entries.
        """
        active_skills = self.get_skills(lifecycle=SkillLifecycle.ACTIVE)
        if not active_skills:
            return []

        # Normalize task description for matching
        task_lower = task_description.lower()
        task_tokens = set(task_lower.split())
        required_tools_set = set(required_tools or [])

        scored: list[tuple[float, SynthesizedSkill]] = []

        for skill in active_skills:
            # Apply minimum success rate filter
            if skill.success_rate < min_success_rate:
                continue

            score = 0.0

            # Token overlap with skill name and description
            name_lower = skill.name.lower()
            desc_lower = skill.description.lower()
            skill_text = f"{name_lower} {desc_lower}"

            # Count matching tokens
            matching_tokens = sum(1 for t in task_tokens if t in skill_text)
            if task_tokens:
                score += 0.35 * (matching_tokens / len(task_tokens))

            # Tag matching
            tag_matches = sum(1 for tag in skill.tags if tag.lower() in task_lower)
            if tag_matches > 0:
                score += 0.15 * min(tag_matches / max(len(skill.tags), 1), 1.0)

            # Category matching
            if preferred_category and skill.category == preferred_category:
                score += 0.20

            # Tool overlap
            if required_tools_set:
                skill_tools = set(skill.tools_required)
                tool_overlap = len(required_tools_set & skill_tools)
                score += 0.15 * (tool_overlap / len(required_tools_set))

            # Success rate bonus
            score += 0.10 * skill.success_rate

            # Quality score bonus
            score += 0.05 * skill.quality_score

            scored.append((score, skill))

        # Sort by score descending and return top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored[:top_k]]

    # ── Adaptive Threshold Tuning ───────────────────────────────────

    def tune_synthesis_thresholds(self) -> dict[str, Any]:
        """Automatically adjust synthesis thresholds based on performance data.

        Analyzes the current skill library's quality distribution, success rates,
        and pattern density to adaptively tune MIN_PATTERN_SUPPORT and
        SYNTHESIS_QUALITY_THRESHOLD for optimal synthesis behavior.

        - If average skill quality is high, lower thresholds to encourage more synthesis.
        - If many low-quality or deprecated skills exist, raise thresholds to be stricter.
        - Adjusts MIN_PATTERN_SUPPORT based on pattern volume and diversity.

        Returns:
            Dictionary with old values, new values, and the rationale for changes.
        """
        old_min_pattern = self.MIN_PATTERN_SUPPORT
        old_quality_threshold = self.SYNTHESIS_QUALITY_THRESHOLD

        active_skills = [s for s in self._skills.values() if s.lifecycle == SkillLifecycle.ACTIVE]
        deprecated_skills = [s for s in self._skills.values() if s.lifecycle == SkillLifecycle.DEPRECATED]
        total_skills = len(self._skills)

        # Calculate quality distribution
        avg_quality = (
            sum(s.quality_score for s in active_skills) / len(active_skills)
            if active_skills else 0.5
        )
        avg_success = (
            sum(s.success_rate for s in active_skills) / len(active_skills)
            if active_skills else 0.0
        )

        # Calculate deprecation ratio
        deprecation_ratio = len(deprecated_skills) / max(total_skills, 1)

        # Calculate pattern density
        total_patterns = sum(len(ops) for ops in self._operation_patterns.values())
        pattern_count = len(self._operation_patterns)
        avg_pattern_size = total_patterns / max(pattern_count, 1)

        # Tune MIN_PATTERN_SUPPORT based on pattern density
        if avg_pattern_size > 10 and avg_success > 0.7:
            # Many patterns with high success: relax support to synthesize more
            new_min_pattern = max(2, old_min_pattern - 1)
            pattern_rationale = "High pattern density and success rate; lowering to encourage more synthesis."
        elif deprecation_ratio > 0.3:
            # Too many deprecated skills: raise support to be more selective
            new_min_pattern = min(10, old_min_pattern + 1)
            pattern_rationale = "High deprecation ratio; raising to be more selective."
        elif avg_pattern_size < 3:
            # Sparse patterns: lower support to allow synthesis from fewer samples
            new_min_pattern = max(2, old_min_pattern - 1)
            pattern_rationale = "Low pattern density; lowering to capture emerging patterns."
        else:
            new_min_pattern = old_min_pattern
            pattern_rationale = "Pattern density is stable; no change needed."

        # Tune SYNTHESIS_QUALITY_THRESHOLD based on skill quality distribution
        if avg_quality > 0.8 and deprecation_ratio < 0.15:
            # High quality, low deprecation: relax threshold
            new_quality_threshold = max(0.4, round(old_quality_threshold - 0.05, 2))
            quality_rationale = "High average quality and low deprecation; relaxing threshold."
        elif avg_quality < 0.5 or deprecation_ratio > 0.3:
            # Low quality or high deprecation: tighten threshold
            new_quality_threshold = min(0.9, round(old_quality_threshold + 0.05, 2))
            quality_rationale = "Low quality or high deprecation; tightening threshold."
        else:
            new_quality_threshold = old_quality_threshold
            quality_rationale = "Quality distribution is healthy; no change needed."

        # Apply the new thresholds
        self.MIN_PATTERN_SUPPORT = new_min_pattern
        self.SYNTHESIS_QUALITY_THRESHOLD = new_quality_threshold

        result = {
            "min_pattern_support": {
                "old": old_min_pattern,
                "new": new_min_pattern,
                "rationale": pattern_rationale,
            },
            "synthesis_quality_threshold": {
                "old": old_quality_threshold,
                "new": new_quality_threshold,
                "rationale": quality_rationale,
            },
            "context": {
                "avg_quality": round(avg_quality, 4),
                "avg_success": round(avg_success, 4),
                "deprecation_ratio": round(deprecation_ratio, 4),
                "avg_pattern_size": round(avg_pattern_size, 2),
                "total_skills": total_skills,
                "active_skills": len(active_skills),
            },
        }

        logger.info(
            "Adaptive threshold tuning: MIN_PATTERN_SUPPORT %d→%d, "
            "QUALITY_THRESHOLD %.2f→%.2f",
            old_min_pattern, new_min_pattern,
            old_quality_threshold, new_quality_threshold,
        )
        return result

    # ── Improvement Trend Analysis ──────────────────────────────────

    def snapshot_trends(self) -> TrendSnapshot:
        """Capture a point-in-time snapshot of current improvement metrics.

        Call this periodically (e.g., after each improvement cycle) to build
        a history of trend data for analysis.

        Returns:
            The newly created TrendSnapshot.
        """
        active_skills = [s for s in self._skills.values() if s.lifecycle == SkillLifecycle.ACTIVE]
        avg_success = (
            sum(s.success_rate for s in active_skills) / len(active_skills)
            if active_skills else 0.0
        )

        snapshot = TrendSnapshot(
            total_skills=len(self._skills),
            active_skills=len(active_skills),
            avg_success_rate=avg_success,
            improvement_cycles=self._metrics.improvement_cycles_run,
            nudges_applied=self._metrics.total_nudges_applied,
            skills_synthesized=self._metrics.total_skills_synthesized,
            composite_skills=len(self._composite_skills),
        )
        self._trend_snapshots.append(snapshot)
        logger.debug("Trend snapshot captured: %d total snapshots", len(self._trend_snapshots))
        return snapshot

    def analyze_improvement_trends(self) -> dict[str, Any]:
        """Analyze improvement trends over time and generate actionable insights.

        Uses the collected trend snapshots to compute growth rates, detect
        plateaus, and generate recommendations for continued improvement.

        Returns:
            Dictionary with trend metrics, growth rates, and generated insights.
        """
        if not self._trend_snapshots:
            return {
                "status": "insufficient_data",
                "message": "No trend snapshots available. Run snapshot_trends() first.",
                "snapshots_count": 0,
                "insights": [],
            }

        snapshots = self._trend_snapshots
        latest = snapshots[-1]
        first = snapshots[0]
        n = len(snapshots)

        # Compute growth rates (compound per-snapshot growth)
        def _growth_rate(current: float, initial: float, periods: int) -> float:
            if periods <= 0 or initial <= 0:
                return 0.0
            return (current / initial) ** (1.0 / periods) - 1.0

        periods = max(n - 1, 1)

        skill_growth_rate = _growth_rate(latest.total_skills, first.total_skills, periods)
        success_growth_rate = _growth_rate(
            max(latest.avg_success_rate, 0.001), max(first.avg_success_rate, 0.001), periods,
        )

        # Compute velocity: rate of change in last few snapshots
        recent_window = min(5, n)
        recent_snapshots = snapshots[-recent_window:]
        if len(recent_snapshots) >= 2:
            success_deltas = [
                recent_snapshots[i].avg_success_rate - recent_snapshots[i - 1].avg_success_rate
                for i in range(1, len(recent_snapshots))
            ]
            avg_success_velocity = sum(success_deltas) / len(success_deltas)
        else:
            avg_success_velocity = 0.0

        # Detect plateau: success rate has not improved meaningfully
        plateau_detected = (
            abs(avg_success_velocity) < 0.01
            and latest.avg_success_rate > 0
            and n >= 3
        )

        # Generate insights
        insights: list[str] = []

        if skill_growth_rate > 0.1:
            insights.append(
                f"Strong skill growth rate ({skill_growth_rate:.1%} per snapshot). "
                "Continue current synthesis strategy."
            )
        elif skill_growth_rate < 0.01 and n > 3:
            insights.append(
                f"Low skill growth rate ({skill_growth_rate:.1%} per snapshot). "
                "Consider lowering synthesis thresholds or exploring new categories."
            )

        if success_growth_rate > 0.05:
            insights.append(
                f"Success rate is trending upward ({success_growth_rate:.1%} per snapshot). "
                "Skill quality is improving."
            )
        elif success_growth_rate < -0.02:
            insights.append(
                f"Success rate is declining ({success_growth_rate:.1%} per snapshot). "
                "Review recently synthesized skills for quality issues."
            )

        if plateau_detected:
            insights.append(
                "Improvement plateau detected. Consider cross-skill synthesis or "
                "adaptive threshold tuning to break through stagnation."
            )

        if latest.composite_skills > 0 and latest.composite_skills > first.composite_skills:
            insights.append(
                f"Composite skills growing ({first.composite_skills} → {latest.composite_skills}). "
                "Skill compounding is producing reusable workflows."
            )

        if latest.nudges_applied > first.nudges_applied * 1.5 and n >= 3:
            insights.append(
                "Nudge application rate is accelerating. The self-improvement loop is active."
            )

        if not insights:
            insights.append(
                "Steady state. Continue monitoring and consider running cross-skill synthesis "
                "to discover new bridging opportunities."
            )

        # Compute trend direction summaries
        trend_direction = {
            "skills": "growing" if skill_growth_rate > 0.02 else ("declining" if skill_growth_rate < -0.02 else "stable"),
            "success_rate": "improving" if avg_success_velocity > 0.005 else ("declining" if avg_success_velocity < -0.005 else "stable"),
        }

        return {
            "status": "ok",
            "snapshots_count": n,
            "time_range": {
                "first": first.timestamp,
                "latest": latest.timestamp,
            },
            "current_metrics": latest.to_dict(),
            "growth_rates": {
                "skill_growth_rate": round(skill_growth_rate, 4),
                "success_growth_rate": round(success_growth_rate, 4),
            },
            "velocity": {
                "avg_success_velocity": round(avg_success_velocity, 4),
                "plateau_detected": plateau_detected,
            },
            "trend_direction": trend_direction,
            "insights": insights,
        }


# Singleton
self_improvement = SelfImprovementEngine()