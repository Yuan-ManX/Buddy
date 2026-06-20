"""
Agent Evolution Engine - Self-Learning Loop for Buddy Agents.

The Evolution Engine enables agents to automatically create reusable skills
from successful task completions, refine them during use, and persist
user-specific knowledge across sessions. Implements a continuous learning
cycle where the agent grows more capable with each interaction.

Core capabilities:
- Operation tracking with success/failure analysis
- Pattern recognition across successful operations
- Automatic skill creation from proven patterns
- Skill refinement through iterative improvement
- Version management with rollback support
- Effectiveness scoring and ranking
"""

import uuid
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("buddy.agent_evolution")


class EvolutionStage(str, Enum):
    """Stages in the evolution lifecycle."""
    OBSERVATION = "observation"      # Watching and recording operations
    ANALYSIS = "analysis"            # Analyzing patterns in successes
    SYNTHESIS = "synthesis"          # Creating new skills from patterns
    VERIFICATION = "verification"    # Testing synthesized skills
    PUBLICATION = "publication"      # Publishing verified skills
    REFINEMENT = "refinement"        # Improving existing skills
    DEPRECATION = "deprecation"      # Marking obsolete skills


class OperationOutcome(str, Enum):
    """Outcome of an agent operation."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    UNCERTAIN = "uncertain"


@dataclass
class OperationRecord:
    """Record of a single agent operation."""
    operation_id: str
    agent_id: str
    task_description: str
    outcome: OperationOutcome
    steps_taken: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    error_message: str | None = None
    user_feedback: str | None = None
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "operation_id": self.operation_id,
            "agent_id": self.agent_id,
            "task_description": self.task_description,
            "outcome": self.outcome.value,
            "steps_taken": self.steps_taken,
            "tools_used": self.tools_used,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "user_feedback": self.user_feedback,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EvolutionSkill:
    """A skill created through the evolution process."""
    skill_id: str
    name: str
    description: str
    source_operations: list[str] = field(default_factory=list)
    execution_pattern: list[str] = field(default_factory=list)
    recommended_tools: list[str] = field(default_factory=list)
    version: int = 1
    effectiveness_score: float = 0.0
    usage_count: int = 0
    success_count: int = 0
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: EvolutionStage = EvolutionStage.SYNTHESIS
    versions: list[dict] = field(default_factory=list)

    def record_usage(self, success: bool) -> None:
        """Record a usage of this skill."""
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.effectiveness_score = (
            self.success_count / self.usage_count if self.usage_count > 0 else 0.0
        )
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "source_operations": self.source_operations,
            "execution_pattern": self.execution_pattern,
            "recommended_tools": self.recommended_tools,
            "version": self.version,
            "effectiveness_score": round(self.effectiveness_score, 3),
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
        }


@dataclass
class EvolutionPattern:
    """A recognized pattern from successful operations."""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int = 0
    associated_operations: list[str] = field(default_factory=list)
    common_tools: list[str] = field(default_factory=list)
    common_steps: list[str] = field(default_factory=list)
    confidence: float = 0.0
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentEvolutionEngine:
    """Self-learning evolution engine for Buddy agents.

    Implements a continuous learning cycle where agents observe their own
    operations, identify successful patterns, synthesize new skills, and
    refine existing ones through iterative improvement.

    The engine maintains an operation history, pattern database, and a
    registry of evolution-created skills with full version management.
    """

    def __init__(self):
        self._operations: dict[str, OperationRecord] = {}
        self._skills: dict[str, EvolutionSkill] = {}
        self._patterns: dict[str, EvolutionPattern] = {}
        self._total_operations = 0
        self._total_skills_created = 0
        self._total_patterns_discovered = 0
        self._evolution_log: list[dict] = []

    # ── Operation Recording ─────────────────────────────────────────

    def record_operation(
        self,
        agent_id: str,
        task_description: str,
        outcome: OperationOutcome,
        steps_taken: list[str] | None = None,
        tools_used: list[str] | None = None,
        duration_ms: float = 0.0,
        error_message: str | None = None,
        user_feedback: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> OperationRecord:
        """Record an agent operation for evolution analysis."""
        op_id = f"op-{uuid.uuid4().hex[:12]}"
        record = OperationRecord(
            operation_id=op_id,
            agent_id=agent_id,
            task_description=task_description,
            outcome=outcome,
            steps_taken=steps_taken or [],
            tools_used=tools_used or [],
            duration_ms=duration_ms,
            error_message=error_message,
            user_feedback=user_feedback,
            context_snapshot=context or {},
        )
        self._operations[op_id] = record
        self._total_operations += 1

        # Log evolution event
        self._evolution_log.append({
            "event": "operation_recorded",
            "operation_id": op_id,
            "agent_id": agent_id,
            "outcome": outcome.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Trigger pattern analysis on success
        if outcome == OperationOutcome.SUCCESS:
            self._analyze_patterns(agent_id)

        return record

    def record_experience(
        self,
        agent_id: str = "",
        experience_type: Any = None,
        task_signature: str = "",
        strategy_used: dict[str, Any] | None = None,
        outcome: Any = None,
        quality_score: float = 0.0,
        tokens_consumed: int = 0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> OperationRecord:
        """Record a high-level experience for evolution learning.

        Maps to record_operation internally, converting the experience
        parameters into an operation record with full context.
        """
        op_outcome = OperationOutcome.SUCCESS
        if outcome is not None:
            try:
                op_outcome = OperationOutcome(outcome.value if hasattr(outcome, 'value') else str(outcome))
            except ValueError:
                op_outcome = OperationOutcome.SUCCESS

        context_data = {
            "quality_score": quality_score,
            "tokens_consumed": tokens_consumed,
            "latency_ms": latency_ms,
            "cost": cost,
            **(metadata or {}),
        }
        if strategy_used:
            context_data["strategy"] = strategy_used

        return self.record_operation(
            agent_id=agent_id,
            task_description=task_signature,
            outcome=op_outcome,
            duration_ms=latency_ms,
            context=context_data,
        )

    # ── Pattern Analysis ────────────────────────────────────────────

    def _analyze_patterns(self, agent_id: str) -> list[EvolutionPattern]:
        """Analyze successful operations to discover patterns."""
        successful_ops = [
            op for op in self._operations.values()
            if op.agent_id == agent_id and op.outcome == OperationOutcome.SUCCESS
        ]

        new_patterns: list[EvolutionPattern] = []

        # Pattern: tool combinations
        tool_sets: dict[str, list[str]] = {}
        for op in successful_ops:
            if op.tools_used:
                key = "|".join(sorted(op.tools_used))
                if key not in tool_sets:
                    tool_sets[key] = []
                tool_sets[key].append(op.operation_id)

        for tools_key, op_ids in tool_sets.items():
            if len(op_ids) >= 2:
                pattern_id = f"pat-{uuid.uuid4().hex[:12]}"
                tools = tools_key.split("|")
                pattern = EvolutionPattern(
                    pattern_id=pattern_id,
                    pattern_type="tool_combination",
                    description=f"Effective tool combination: {', '.join(tools)}",
                    frequency=len(op_ids),
                    associated_operations=op_ids,
                    common_tools=tools,
                    confidence=min(1.0, len(op_ids) / 5.0),
                )
                self._patterns[pattern_id] = pattern
                self._total_patterns_discovered += 1
                new_patterns.append(pattern)

        # Pattern: step sequences
        step_sequences: dict[str, list[str]] = {}
        for op in successful_ops:
            if len(op.steps_taken) >= 2:
                # Create n-grams of step sequences
                for i in range(len(op.steps_taken) - 1):
                    bigram = f"{op.steps_taken[i]} -> {op.steps_taken[i + 1]}"
                    if bigram not in step_sequences:
                        step_sequences[bigram] = []
                    step_sequences[bigram].append(op.operation_id)

        for seq_key, op_ids in step_sequences.items():
            if len(op_ids) >= 3:
                pattern_id = f"pat-{uuid.uuid4().hex[:12]}"
                pattern = EvolutionPattern(
                    pattern_id=pattern_id,
                    pattern_type="step_sequence",
                    description=f"Common step sequence: {seq_key}",
                    frequency=len(op_ids),
                    associated_operations=op_ids,
                    common_steps=seq_key.split(" -> "),
                    confidence=min(1.0, len(op_ids) / 10.0),
                )
                self._patterns[pattern_id] = pattern
                self._total_patterns_discovered += 1
                new_patterns.append(pattern)

        return new_patterns

    # ── Skill Synthesis ─────────────────────────────────────────────

    def synthesize_skill(
        self,
        name: str,
        description: str,
        source_operations: list[str] | None = None,
        execution_pattern: list[str] | None = None,
        tools: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> EvolutionSkill:
        """Synthesize a new skill from successful operation patterns."""
        skill_id = f"evskill-{uuid.uuid4().hex[:12]}"

        # Gather source operations if not specified
        if source_operations is None:
            source_operations = []
            for op in self._operations.values():
                if op.outcome == OperationOutcome.SUCCESS:
                    source_operations.append(op.operation_id)

        # Infer execution pattern from successful operations
        if execution_pattern is None and source_operations:
            all_steps: list[str] = []
            for op_id in source_operations:
                if op_id in self._operations:
                    all_steps.extend(self._operations[op_id].steps_taken)
            # Deduplicate while preserving order
            seen: set[str] = set()
            execution_pattern = []
            for step in all_steps:
                if step not in seen:
                    seen.add(step)
                    execution_pattern.append(step)

        # Infer tools from successful operations
        if tools is None and source_operations:
            all_tools: set[str] = set()
            for op_id in source_operations:
                if op_id in self._operations:
                    all_tools.update(self._operations[op_id].tools_used)
            tools = list(all_tools)

        skill = EvolutionSkill(
            skill_id=skill_id,
            name=name,
            description=description,
            source_operations=source_operations or [],
            execution_pattern=execution_pattern or [],
            recommended_tools=tools or [],
            tags=tags or [],
            status=EvolutionStage.SYNTHESIS,
        )
        self._skills[skill_id] = skill
        self._total_skills_created += 1

        self._evolution_log.append({
            "event": "skill_synthesized",
            "skill_id": skill_id,
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return skill

    def auto_synthesize_from_patterns(
        self,
        agent_id: str,
        min_confidence: float = 0.5,
    ) -> list[EvolutionSkill]:
        """Automatically create skills from discovered patterns."""
        new_skills: list[EvolutionSkill] = []

        for pattern in self._patterns.values():
            if pattern.confidence < min_confidence:
                continue

            # Check if a similar skill already exists
            existing = False
            for skill in self._skills.values():
                if set(pattern.common_tools) == set(skill.recommended_tools):
                    existing = True
                    break

            if existing:
                continue

            skill = self.synthesize_skill(
                name=f"auto-skill-{pattern.pattern_type}",
                description=pattern.description,
                source_operations=pattern.associated_operations,
                tools=pattern.common_tools,
                execution_pattern=pattern.common_steps,
                tags=[pattern.pattern_type, "auto-generated"],
            )
            skill.status = EvolutionStage.VERIFICATION
            new_skills.append(skill)

        return new_skills

    # ── Skill Refinement ────────────────────────────────────────────

    def refine_skill(
        self,
        skill_id: str,
        new_execution_pattern: list[str] | None = None,
        new_tools: list[str] | None = None,
        new_description: str | None = None,
    ) -> EvolutionSkill | None:
        """Refine an existing evolution skill with improvements."""
        if skill_id not in self._skills:
            return None

        skill = self._skills[skill_id]

        # Save current version
        skill.versions.append({
            "version": skill.version,
            "execution_pattern": list(skill.execution_pattern),
            "recommended_tools": list(skill.recommended_tools),
            "description": skill.description,
            "effectiveness_score": skill.effectiveness_score,
        })

        # Apply refinements
        if new_execution_pattern:
            skill.execution_pattern = new_execution_pattern
        if new_tools:
            skill.recommended_tools = new_tools
        if new_description:
            skill.description = new_description

        skill.version += 1
        skill.status = EvolutionStage.REFINEMENT
        skill.updated_at = datetime.now(timezone.utc)

        self._evolution_log.append({
            "event": "skill_refined",
            "skill_id": skill_id,
            "new_version": skill.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return skill

    def rollback_skill(self, skill_id: str, target_version: int) -> EvolutionSkill | None:
        """Rollback a skill to a previous version."""
        if skill_id not in self._skills:
            return None

        skill = self._skills[skill_id]
        for version_data in skill.versions:
            if version_data["version"] == target_version:
                skill.execution_pattern = version_data["execution_pattern"]
                skill.recommended_tools = version_data["recommended_tools"]
                skill.description = version_data["description"]
                skill.version = target_version + 1
                skill.updated_at = datetime.now(timezone.utc)
                return skill

        return None

    def mark_deprecated(self, skill_id: str) -> bool:
        """Mark a skill as deprecated."""
        if skill_id not in self._skills:
            return False
        self._skills[skill_id].status = EvolutionStage.DEPRECATION
        return True

    # ── Query Methods ───────────────────────────────────────────────

    def get_skill(self, skill_id: str) -> EvolutionSkill | None:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_skills(
        self,
        min_effectiveness: float = 0.0,
        status: EvolutionStage | None = None,
        tags: list[str] | None = None,
    ) -> list[EvolutionSkill]:
        """List skills with optional filters."""
        result = list(self._skills.values())

        if min_effectiveness > 0:
            result = [s for s in result if s.effectiveness_score >= min_effectiveness]
        if status:
            result = [s for s in result if s.status == status]
        if tags:
            result = [s for s in result if any(t in s.tags for t in tags)]

        return sorted(result, key=lambda s: s.effectiveness_score, reverse=True)

    def get_operations(
        self,
        agent_id: str | None = None,
        outcome: OperationOutcome | None = None,
        limit: int = 50,
    ) -> list[OperationRecord]:
        """Get operation records with filters."""
        result = list(self._operations.values())

        if agent_id:
            result = [op for op in result if op.agent_id == agent_id]
        if outcome:
            result = [op for op in result if op.outcome == outcome]

        result.sort(key=lambda op: op.timestamp, reverse=True)
        return result[:limit]

    def get_patterns(
        self,
        min_confidence: float = 0.0,
        pattern_type: str | None = None,
    ) -> list[EvolutionPattern]:
        """Get discovered patterns with filters."""
        result = list(self._patterns.values())

        if min_confidence > 0:
            result = [p for p in result if p.confidence >= min_confidence]
        if pattern_type:
            result = [p for p in result if p.pattern_type == pattern_type]

        return sorted(result, key=lambda p: p.confidence, reverse=True)

    def get_evolution_log(self, limit: int = 100) -> list[dict]:
        """Get the evolution event log."""
        return self._evolution_log[-limit:]

    def get_stats(self) -> dict:
        """Get evolution engine statistics."""
        return {
            "total_operations": self._total_operations,
            "total_skills_created": self._total_skills_created,
            "total_patterns_discovered": self._total_patterns_discovered,
            "active_skills": len([
                s for s in self._skills.values()
                if s.status not in (EvolutionStage.DEPRECATION,)
            ]),
            "deprecated_skills": len([
                s for s in self._skills.values()
                if s.status == EvolutionStage.DEPRECATION
            ]),
            "success_rate": (
                len([op for op in self._operations.values()
                     if op.outcome == OperationOutcome.SUCCESS]) /
                max(1, self._total_operations)
            ),
            "top_skills": [
                {"name": s.name, "effectiveness": round(s.effectiveness_score, 3)}
                for s in sorted(
                    self._skills.values(),
                    key=lambda x: x.effectiveness_score,
                    reverse=True,
                )[:5]
            ],
            "top_patterns": [
                {"type": p.pattern_type, "confidence": round(p.confidence, 3)}
                for p in sorted(
                    self._patterns.values(),
                    key=lambda x: x.confidence,
                    reverse=True,
                )[:5]
            ],
        }


# Singleton instance
evolution_engine = AgentEvolutionEngine()


# ═══════════════════════════════════════════════════════════
# Backward-compatible aliases for existing code
# ═══════════════════════════════════════════════════════════

class ExperienceType(str, Enum):
    """Experience types for agent evolution tracking (backward compat)."""
    CHAT = "chat"
    TASK = "task"
    TOOL = "tool"
    CODE = "code"
    REASONING = "reasoning"
    PLAN = "plan"
    COLLABORATION = "collaboration"
    USER_INTERACTION = "user_interaction"
    ERROR = "error"


ExperienceOutcome = OperationOutcome  # Backward-compatible alias


class AgentEvolution:
    """Backward-compatible wrapper for AgentEvolutionEngine.

    Accepts agent_id and client parameters for compatibility with
    existing engine.py initialization, while delegating all
    functionality to the singleton AgentEvolutionEngine.
    """

    def __init__(self, agent_id: str = "", client: Any = None):
        self.agent_id = agent_id
        self.client = client
        self._engine = evolution_engine

    def get_stats(self) -> dict:
        return self._engine.get_stats()

    def record_operation(self, **kwargs) -> OperationRecord:
        kwargs.setdefault("agent_id", self.agent_id)
        return self._engine.record_operation(**kwargs)

    def synthesize_skill(self, **kwargs) -> EvolutionSkill:
        return self._engine.synthesize_skill(**kwargs)

    def get_skills(self) -> list[EvolutionSkill]:
        return self._engine.list_skills()

    def get_patterns(self) -> list[EvolutionPattern]:
        return self._engine.get_patterns()

    def get_evolution_log(self, limit: int = 100) -> list[dict]:
        return self._engine.get_evolution_log(limit)

    def record_experience(self, **kwargs) -> OperationRecord:
        kwargs.setdefault("agent_id", self.agent_id)
        return self._engine.record_experience(**kwargs)