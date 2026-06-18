"""Buddy Agent Learning Loop — autonomous self-evolution and skill compounding

Implements a continuous improvement cycle where agents learn from every
interaction, extract reusable patterns, compound skills across the mesh,
and proactively suggest improvements. The loop operates across four phases:

  Observe    → Capture interaction data, outcomes, user feedback, and context
  Extract    → Identify patterns, distill lessons, generate reusable skills
  Compound   → Merge skills across agents, resolve conflicts, rank by utility
  Evolve     → Update agent behavior, persona, and system prompts with learnings

Architecture:
  LearningLoop
    ├── ObservationEngine   — captures and stores interaction data
    ├── ExtractionEngine    — distills patterns from raw observations
    ├── CompoundingEngine   — merges and ranks skills across agents
    ├── EvolutionEngine     — applies learnings to agent behavior
    └── NudgeEngine         — proactively suggests actions to the user
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
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.learning_loop")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class ObservationType(str, Enum):
    """Types of interactions that can be observed."""
    CHAT_MESSAGE = "chat_message"
    TOOL_EXECUTION = "tool_execution"
    TASK_COMPLETION = "task_completion"
    USER_FEEDBACK = "user_feedback"
    ERROR_OCCURRED = "error_occurred"
    SKILL_CREATED = "skill_created"
    SKILL_USED = "skill_used"
    AGENT_COLLABORATION = "agent_collaboration"
    STRATEGY_CHANGE = "strategy_change"
    PERSONA_ADAPTATION = "persona_adaptation"


class SkillSource(str, Enum):
    """How a skill was created."""
    EXTRACTED = "extracted"         # From observed patterns
    USER_CREATED = "user_created"   # Manually by user
    COMPOUNDED = "compounded"       # Merged from multiple agents
    EVOLVED = "evolved"            # Auto-improved over time
    TEMPLATE = "template"          # From system templates


class NudgePriority(str, Enum):
    """Priority levels for proactive nudges."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SUGGESTION = "suggestion"


class NudgeCategory(str, Enum):
    """Categories of proactive nudges."""
    SKILL_SUGGESTION = "skill_suggestion"
    MEMORY_REMINDER = "memory_reminder"
    TASK_FOLLOWUP = "task_followup"
    PATTERN_DETECTED = "pattern_detected"
    OPTIMIZATION_TIP = "optimization_tip"
    COLLABORATION_OPPORTUNITY = "collaboration_opportunity"
    LEARNING_INSIGHT = "learning_insight"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class Observation:
    """A single observed interaction."""
    observation_id: str
    observation_type: ObservationType
    agent_id: str
    session_id: str = ""
    content: dict = field(default_factory=dict)
    outcome: str = "unknown"
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExtractedPattern:
    """A pattern extracted from observations."""
    pattern_id: str
    pattern_type: str
    description: str
    conditions: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    confidence: float = 0.5
    frequency: int = 0
    source_observations: list[str] = field(default_factory=list)
    related_agents: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CompoundSkill:
    """A skill created by compounding patterns across agents."""
    skill_id: str
    name: str
    description: str
    triggers: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    source_patterns: list[str] = field(default_factory=list)
    source_agents: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    usage_count: int = 0
    confidence: float = 0.5
    skill_source: SkillSource = SkillSource.EXTRACTED
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UserModel:
    """Deepening model of the user built across sessions."""
    user_id: str = "default"
    preferences: dict = field(default_factory=dict)
    communication_style: str = ""
    domain_knowledge: dict = field(default_factory=dict)
    common_tasks: list[str] = field(default_factory=list)
    feedback_history: list[dict] = field(default_factory=list)
    interaction_count: int = 0
    last_active: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_count: int = 0
    top_interests: list[str] = field(default_factory=list)


@dataclass
class Nudge:
    """A proactive suggestion for the user."""
    nudge_id: str
    category: NudgeCategory
    priority: NudgePriority
    message: str
    suggested_action: str = ""
    context: dict = field(default_factory=dict)
    dismissed: bool = False
    acted_upon: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════
# Observation Engine
# ═══════════════════════════════════════════════════════════

class ObservationEngine:
    """Captures and stores interaction data from all agent activities."""

    def __init__(self):
        self._observations: list[Observation] = []
        self._session_observations: dict[str, list[Observation]] = defaultdict(list)
        self._by_agent: dict[str, list[Observation]] = defaultdict(list)

    def record(self, observation_type: ObservationType, agent_id: str,
               session_id: str = "", content: dict | None = None,
               outcome: str = "unknown", metadata: dict | None = None) -> Observation:
        """Record a new observation."""
        if isinstance(observation_type, str):
            observation_type = ObservationType(observation_type)
        obs = Observation(
            observation_id=str(uuid.uuid4())[:12],
            observation_type=observation_type,
            agent_id=agent_id,
            session_id=session_id,
            content=content or {},
            outcome=outcome,
            metadata=metadata or {},
        )
        self._observations.append(obs)
        if session_id:
            self._session_observations[session_id].append(obs)
        self._by_agent[agent_id].append(obs)

        if len(self._observations) > 10000:
            self._observations = self._observations[-5000:]
        return obs

    def get_agent_observations(self, agent_id: str, limit: int = 100,
                               obs_type: ObservationType | None = None) -> list[Observation]:
        """Get observations for a specific agent."""
        obs_list = self._by_agent.get(agent_id, [])
        if obs_type:
            obs_list = [o for o in obs_list if o.observation_type == obs_type]
        return obs_list[-limit:]

    def get_session_observations(self, session_id: str) -> list[Observation]:
        """Get all observations for a session."""
        return self._session_observations.get(session_id, [])

    def get_recent(self, limit: int = 50) -> list[Observation]:
        """Get recent observations across all agents."""
        return self._observations[-limit:]

    def get_stats(self) -> dict:
        """Get observation statistics."""
        total = len(self._observations)
        by_type = defaultdict(int)
        for o in self._observations:
            obs_type = o.observation_type
            if hasattr(obs_type, 'value'):
                key = obs_type.value
            else:
                key = str(obs_type)
            by_type[key] += 1

        return {
            "total_observations": total,
            "by_type": dict(by_type),
            "unique_agents": len(self._by_agent),
            "unique_sessions": len(self._session_observations),
        }


# ═══════════════════════════════════════════════════════════
# Extraction Engine
# ═══════════════════════════════════════════════════════════

class ExtractionEngine:
    """Distills reusable patterns from raw observations."""

    def __init__(self):
        self._patterns: list[ExtractedPattern] = []
        self._pattern_hashes: set[str] = set()

    def extract_from_observations(self, observations: list[Observation],
                                  min_confidence: float = 0.3) -> list[ExtractedPattern]:
        """Extract patterns from a batch of observations."""
        new_patterns = []

        # Extract from successful tool executions
        tool_obs = [o for o in observations if o.observation_type == ObservationType.TOOL_EXECUTION
                    and o.outcome == "success"]
        if len(tool_obs) >= 2:
            pattern = self._extract_tool_pattern(tool_obs)
            if pattern and pattern.confidence >= min_confidence:
                self._add_pattern(pattern)
                new_patterns.append(pattern)

        # Extract from completed tasks
        task_obs = [o for o in observations if o.observation_type == ObservationType.TASK_COMPLETION
                    and o.outcome == "success"]
        if len(task_obs) >= 2:
            pattern = self._extract_task_pattern(task_obs)
            if pattern and pattern.confidence >= min_confidence:
                self._add_pattern(pattern)
                new_patterns.append(pattern)

        # Extract from user feedback
        feedback_obs = [o for o in observations if o.observation_type == ObservationType.USER_FEEDBACK]
        if feedback_obs:
            pattern = self._extract_feedback_pattern(feedback_obs)
            if pattern and pattern.confidence >= min_confidence:
                self._add_pattern(pattern)
                new_patterns.append(pattern)

        return new_patterns

    def _extract_tool_pattern(self, observations: list[Observation]) -> ExtractedPattern | None:
        """Extract a pattern from tool execution observations."""
        tool_sequences = []
        for obs in observations:
            content = obs.content
            tool_name = content.get("tool_name", "")
            if tool_name:
                tool_sequences.append(tool_name)

        if len(tool_sequences) < 2:
            return None

        # Find common tool sequences
        sequence_str = " → ".join(tool_sequences[:5])
        pattern_hash = hashlib.md5(sequence_str.encode()).hexdigest()[:8]

        return ExtractedPattern(
            pattern_id=f"tool-{pattern_hash}",
            pattern_type="tool_sequence",
            description=f"Common tool sequence: {sequence_str}",
            conditions=[f"task_requires_{t}" for t in tool_sequences[:3]],
            actions=tool_sequences[:5],
            confidence=min(0.8, len(tool_sequences) * 0.15),
            frequency=len(observations),
            source_observations=[o.observation_id for o in observations[:5]],
            related_agents=list(set(o.agent_id for o in observations)),
        )

    def _extract_task_pattern(self, observations: list[Observation]) -> ExtractedPattern | None:
        """Extract a pattern from task completion observations."""
        task_types = []
        for obs in observations:
            content = obs.content
            task_type = content.get("task_type", content.get("title", ""))
            if task_type:
                task_types.append(task_type)

        if len(task_types) < 2:
            return None

        # Find common task types
        from collections import Counter
        common = Counter(task_types).most_common(3)

        return ExtractedPattern(
            pattern_id=f"task-{hashlib.md5(str(common).encode()).hexdigest()[:8]}",
            pattern_type="task_pattern",
            description=f"Common task pattern: {common[0][0]}",
            conditions=[f"task_type_is_{t}" for t, _ in common],
            actions=["plan", "execute", "verify"],
            confidence=min(0.9, len(observations) * 0.2),
            frequency=len(observations),
            source_observations=[o.observation_id for o in observations[:5]],
            related_agents=list(set(o.agent_id for o in observations)),
        )

    def _extract_feedback_pattern(self, observations: list[Observation]) -> ExtractedPattern | None:
        """Extract patterns from user feedback."""
        positive = [o for o in observations if o.outcome == "positive"]
        negative = [o for o in observations if o.outcome == "negative"]

        if not positive and not negative:
            return None

        return ExtractedPattern(
            pattern_id=f"feedback-{hashlib.md5(str(len(observations)).encode()).hexdigest()[:8]}",
            pattern_type="feedback_pattern",
            description=f"Feedback pattern: {len(positive)} positive, {len(negative)} negative",
            conditions=["user_feedback_received"],
            actions=["adjust_behavior" if negative else "reinforce_behavior"],
            confidence=min(0.85, (len(positive) / max(len(observations), 1)) + 0.3),
            frequency=len(observations),
            source_observations=[o.observation_id for o in observations[:5]],
            related_agents=list(set(o.agent_id for o in observations)),
        )

    def _add_pattern(self, pattern: ExtractedPattern):
        """Add a pattern, avoiding duplicates."""
        pattern_hash = hashlib.md5(pattern.description.encode()).hexdigest()
        if pattern_hash not in self._pattern_hashes:
            self._patterns.append(pattern)
            self._pattern_hashes.add(pattern_hash)
            if len(self._patterns) > 500:
                self._patterns = self._patterns[-500:]

    def get_patterns(self, pattern_type: str | None = None,
                     min_confidence: float = 0.0) -> list[ExtractedPattern]:
        """Get extracted patterns, optionally filtered."""
        patterns = self._patterns
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        if min_confidence > 0:
            patterns = [p for p in patterns if p.confidence >= min_confidence]
        return patterns

    def get_stats(self) -> dict:
        """Get extraction statistics."""
        by_type = defaultdict(int)
        for p in self._patterns:
            by_type[p.pattern_type] += 1
        return {
            "total_patterns": len(self._patterns),
            "by_type": dict(by_type),
            "avg_confidence": sum(p.confidence for p in self._patterns) / max(len(self._patterns), 1),
        }


# ═══════════════════════════════════════════════════════════
# Compounding Engine
# ═══════════════════════════════════════════════════════════

class CompoundingEngine:
    """Merges and ranks skills across agents, resolving conflicts."""

    def __init__(self):
        self._skills: dict[str, CompoundSkill] = {}
        self._skill_index: dict[str, list[str]] = defaultdict(list)  # tag → skill_ids

    def compound_from_patterns(self, patterns: list[ExtractedPattern],
                               agent_id: str) -> CompoundSkill | None:
        """Create a compound skill from related patterns."""
        if len(patterns) < 2:
            return None

        # Group patterns by type
        tool_patterns = [p for p in patterns if p.pattern_type == "tool_sequence"]
        task_patterns = [p for p in patterns if p.pattern_type == "task_pattern"]

        if not tool_patterns and not task_patterns:
            return None

        # Build compound skill
        all_actions = []
        for p in tool_patterns:
            all_actions.extend(p.actions)
        for p in task_patterns:
            all_actions.extend(p.actions)

        name = f"Compound: {patterns[0].description[:50]}"
        skill_id = f"cmp-{hashlib.md5(name.encode()).hexdigest()[:12]}"

        skill = CompoundSkill(
            skill_id=skill_id,
            name=name,
            description=f"Auto-compounded skill from {len(patterns)} patterns",
            triggers=[f"pattern_{p.pattern_id}" for p in patterns],
            steps=[{"action": a, "confidence": 0.7} for a in all_actions[:10]],
            tools_required=[a for a in all_actions if a in {"read_file", "write_file", "grep", "glob", "run_command"}],
            source_patterns=[p.pattern_id for p in patterns],
            source_agents=[agent_id],
            confidence=sum(p.confidence for p in patterns) / len(patterns),
            skill_source=SkillSource.COMPOUNDED,
        )

        self._skills[skill_id] = skill
        self._index_skill(skill)
        return skill

    def merge_skills(self, skill_id1: str, skill_id2: str) -> CompoundSkill | None:
        """Merge two skills into a new compound skill."""
        skill1 = self._skills.get(skill_id1)
        skill2 = self._skills.get(skill_id2)
        if not skill1 or not skill2:
            return None

        merged = CompoundSkill(
            skill_id=f"merged-{hashlib.md5((skill_id1 + skill_id2).encode()).hexdigest()[:12]}",
            name=f"{skill1.name} + {skill2.name}",
            description=f"Merged skill: {skill1.description} | {skill2.description}",
            triggers=list(set(skill1.triggers + skill2.triggers)),
            steps=skill1.steps + skill2.steps,
            tools_required=list(set(skill1.tools_required + skill2.tools_required)),
            source_patterns=list(set(skill1.source_patterns + skill2.source_patterns)),
            source_agents=list(set(skill1.source_agents + skill2.source_agents)),
            confidence=(skill1.confidence + skill2.confidence) / 2,
            skill_source=SkillSource.COMPOUNDED,
            version=max(skill1.version, skill2.version) + 1,
        )

        self._skills[merged.skill_id] = merged
        self._index_skill(merged)
        return merged

    def rank_skills(self, limit: int = 20) -> list[CompoundSkill]:
        """Rank skills by utility (confidence * usage_count)."""
        ranked = sorted(
            self._skills.values(),
            key=lambda s: (s.confidence * (1 + s.usage_count * 0.1), s.success_rate),
            reverse=True,
        )
        return ranked[:limit]

    def _index_skill(self, skill: CompoundSkill):
        """Index skill by its trigger tags."""
        for trigger in skill.triggers:
            self._skill_index[trigger].append(skill.skill_id)
        for tool in skill.tools_required:
            self._skill_index[f"tool:{tool}"].append(skill.skill_id)

    def get_skills_by_tag(self, tag: str) -> list[CompoundSkill]:
        """Get skills matching a tag."""
        skill_ids = self._skill_index.get(tag, [])
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def get_stats(self) -> dict:
        """Get compounding statistics."""
        by_source = defaultdict(int)
        for s in self._skills.values():
            by_source[s.skill_source.value] += 1

        return {
            "total_skills": len(self._skills),
            "by_source": dict(by_source),
            "avg_confidence": sum(s.confidence for s in self._skills.values()) / max(len(self._skills), 1),
            "most_used": self.rank_skills(5),
        }


# ═══════════════════════════════════════════════════════════
# Evolution Engine
# ═══════════════════════════════════════════════════════════

class EvolutionEngine:
    """Applies learnings to update agent behavior and system prompts."""

    def __init__(self):
        self._evolution_log: list[dict] = []
        self._behavior_updates: dict[str, list[dict]] = defaultdict(list)

    def evolve_agent_prompt(self, agent_id: str, patterns: list[ExtractedPattern],
                            skills: list[CompoundSkill]) -> dict:
        """Generate prompt improvements based on learnings."""
        improvements = []

        # Add successful patterns as guidance
        successful_patterns = [p for p in patterns if p.frequency >= 3]
        if successful_patterns:
            improvements.append({
                "type": "pattern_guidance",
                "content": f"Apply {len(successful_patterns)} learned patterns for better results",
                "patterns": [p.pattern_id for p in successful_patterns],
            })

        # Add compound skills
        if skills:
            improvements.append({
                "type": "skill_integration",
                "content": f"Integrate {len(skills)} compound skills",
                "skills": [s.skill_id for s in skills],
            })

        # Record evolution
        entry = {
            "agent_id": agent_id,
            "improvements": improvements,
            "patterns_applied": len(patterns),
            "skills_integrated": len(skills),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._evolution_log.append(entry)
        self._behavior_updates[agent_id].append(entry)

        if len(self._evolution_log) > 1000:
            self._evolution_log = self._evolution_log[-1000:]

        return {"improvements": improvements, "agent_id": agent_id}

    def get_agent_evolution(self, agent_id: str) -> list[dict]:
        """Get evolution history for an agent."""
        return self._behavior_updates.get(agent_id, [])

    def get_stats(self) -> dict:
        """Get evolution statistics."""
        return {
            "total_evolutions": len(self._evolution_log),
            "agents_evolved": len(self._behavior_updates),
            "recent": self._evolution_log[-5:] if self._evolution_log else [],
        }


# ═══════════════════════════════════════════════════════════
# Nudge Engine
# ═══════════════════════════════════════════════════════════

class NudgeEngine:
    """Proactively suggests actions to the user based on learnings."""

    def __init__(self):
        self._nudges: list[Nudge] = []
        self._dismissed_nudges: set[str] = set()

    def generate_nudges(self, patterns: list[ExtractedPattern],
                        user_model: UserModel,
                        recent_observations: list[Observation]) -> list[Nudge]:
        """Generate proactive nudges based on learnings and user context."""
        nudges = []

        # Skill suggestion nudges
        high_confidence_patterns = [p for p in patterns if p.confidence >= 0.6 and p.frequency >= 3]
        for p in high_confidence_patterns[:3]:
            nudge = Nudge(
                nudge_id=str(uuid.uuid4())[:8],
                category=NudgeCategory.SKILL_SUGGESTION,
                priority=NudgePriority.MEDIUM,
                message=f"I noticed a pattern in your workflow: {p.description}. Would you like me to create a reusable skill for this?",
                suggested_action="create_skill",
                context={"pattern_id": p.pattern_id, "pattern_type": p.pattern_type},
            )
            nudges.append(nudge)

        # Memory reminder nudges
        if user_model.interaction_count > 10 and len(user_model.feedback_history) > 0:
            nudge = Nudge(
                nudge_id=str(uuid.uuid4())[:8],
                category=NudgeCategory.MEMORY_REMINDER,
                priority=NudgePriority.LOW,
                message=f"I've learned from {user_model.interaction_count} interactions. Review your preferences?",
                suggested_action="review_preferences",
                context={"interaction_count": user_model.interaction_count},
            )
            nudges.append(nudge)

        # Task followup nudges
        incomplete_tasks = [o for o in recent_observations
                           if o.observation_type == ObservationType.TASK_COMPLETION
                           and o.outcome == "partial"]
        if incomplete_tasks:
            nudge = Nudge(
                nudge_id=str(uuid.uuid4())[:8],
                category=NudgeCategory.TASK_FOLLOWUP,
                priority=NudgePriority.HIGH,
                message=f"You have {len(incomplete_tasks)} incomplete tasks. Would you like me to pick them up?",
                suggested_action="resume_tasks",
                context={"task_count": len(incomplete_tasks)},
            )
            nudges.append(nudge)

        # Optimization tip nudges
        if len(recent_observations) > 20:
            tool_obs = [o for o in recent_observations
                       if o.observation_type == ObservationType.TOOL_EXECUTION]
            if len(tool_obs) >= 5:
                nudge = Nudge(
                    nudge_id=str(uuid.uuid4())[:8],
                    category=NudgeCategory.OPTIMIZATION_TIP,
                    priority=NudgePriority.SUGGESTION,
                    message="I've observed your tool usage patterns. I can optimize the workflow for better efficiency.",
                    suggested_action="optimize_workflow",
                    context={"tool_count": len(tool_obs)},
                )
                nudges.append(nudge)

        for n in nudges:
            if n.nudge_id not in self._dismissed_nudges:
                self._nudges.append(n)

        if len(self._nudges) > 200:
            self._nudges = self._nudges[-200:]

        return nudges

    def dismiss_nudge(self, nudge_id: str):
        """Dismiss a nudge so it won't be shown again."""
        self._dismissed_nudges.add(nudge_id)
        for n in self._nudges:
            if n.nudge_id == nudge_id:
                n.dismissed = True

    def act_on_nudge(self, nudge_id: str):
        """Mark a nudge as acted upon."""
        for n in self._nudges:
            if n.nudge_id == nudge_id:
                n.acted_upon = True

    def get_active_nudges(self, limit: int = 10) -> list[Nudge]:
        """Get active (non-dismissed) nudges."""
        active = [n for n in self._nudges if not n.dismissed and not n.acted_upon]
        return sorted(active, key=lambda n: {
            NudgePriority.CRITICAL: 0,
            NudgePriority.HIGH: 1,
            NudgePriority.MEDIUM: 2,
            NudgePriority.LOW: 3,
            NudgePriority.SUGGESTION: 4,
        }[n.priority])[:limit]

    def get_stats(self) -> dict:
        """Get nudge statistics."""
        active = self.get_active_nudges()
        return {
            "total_nudges": len(self._nudges),
            "active_nudges": len(active),
            "dismissed": len(self._dismissed_nudges),
            "acted_upon": len([n for n in self._nudges if n.acted_upon]),
        }


# ═══════════════════════════════════════════════════════════
# Learning Loop — Main Orchestrator
# ═══════════════════════════════════════════════════════════

class LearningLoop:
    """Main orchestrator for the autonomous agent learning cycle.

    Coordinates observation, extraction, compounding, and evolution in a
    continuous loop that improves agent performance over time.
    """

    def __init__(self):
        self.observation_engine = ObservationEngine()
        self.extraction_engine = ExtractionEngine()
        self.compounding_engine = CompoundingEngine()
        self.evolution_engine = EvolutionEngine()
        self.nudge_engine = NudgeEngine()
        self._user_model = UserModel()
        self._running = False
        self._loop_task: asyncio.Task | None = None

    # ── Observation ──

    def observe(self, observation_type: ObservationType, agent_id: str,
                session_id: str = "", content: dict | None = None,
                outcome: str = "unknown", metadata: dict | None = None) -> Observation:
        """Record an observation and update the user model."""
        if isinstance(observation_type, str):
            observation_type = ObservationType(observation_type)
        obs = self.observation_engine.record(
            observation_type, agent_id, session_id, content, outcome, metadata
        )
        self._update_user_model(obs)
        return obs

    def _update_user_model(self, observation: Observation):
        """Update the user model based on new observations."""
        self._user_model.interaction_count += 1
        if observation.session_id:
            self._user_model.session_count = max(
                self._user_model.session_count,
                len(self.observation_engine._session_observations)
            )
        if observation.observation_type == ObservationType.USER_FEEDBACK:
            self._user_model.feedback_history.append({
                "outcome": observation.outcome,
                "timestamp": observation.timestamp,
                "content": observation.content,
            })
            if len(self._user_model.feedback_history) > 100:
                self._user_model.feedback_history = self._user_model.feedback_history[-100:]

    # ── Extract ──

    def extract(self, agent_id: str | None = None,
                session_id: str | None = None) -> list[ExtractedPattern]:
        """Extract patterns from recent observations."""
        if agent_id:
            observations = self.observation_engine.get_agent_observations(agent_id, limit=100)
        elif session_id:
            observations = self.observation_engine.get_session_observations(session_id)
        else:
            observations = self.observation_engine.get_recent(limit=100)

        return self.extraction_engine.extract_from_observations(observations)

    # ── Compound ──

    def compound(self, patterns: list[ExtractedPattern],
                 agent_id: str) -> CompoundSkill | None:
        """Create compound skills from extracted patterns."""
        return self.compounding_engine.compound_from_patterns(patterns, agent_id)

    # ── Evolve ──

    def evolve(self, agent_id: str) -> dict:
        """Apply all learnings to evolve the agent."""
        patterns = self.extraction_engine.get_patterns(min_confidence=0.5)
        skills = self.compounding_engine.rank_skills(limit=10)
        return self.evolution_engine.evolve_agent_prompt(agent_id, patterns, skills)

    # ── Nudge ──

    def generate_nudges(self) -> list[Nudge]:
        """Generate proactive nudges for the user."""
        patterns = self.extraction_engine.get_patterns(min_confidence=0.4)
        observations = self.observation_engine.get_recent(limit=50)
        return self.nudge_engine.generate_nudges(patterns, self._user_model, observations)

    # ── Full Cycle ──

    async def run_cycle(self, agent_id: str, session_id: str = "") -> dict:
        """Run a complete learning cycle: observe → extract → compound → evolve → nudge."""
        result = {
            "agent_id": agent_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Extract
        patterns = self.extract(agent_id=agent_id)
        result["patterns_extracted"] = len(patterns)

        # Compound
        if patterns:
            skill = self.compound(patterns, agent_id)
            if skill:
                result["skill_compounded"] = skill.skill_id

        # Evolve
        evolution = self.evolve(agent_id)
        result["evolution"] = evolution

        # Nudge
        nudges = self.generate_nudges()
        result["nudges_generated"] = len(nudges)

        return result

    async def start_loop(self, interval_seconds: float = 60.0):
        """Start the continuous learning loop."""
        self._running = True
        self._loop_task = asyncio.create_task(self._loop(interval_seconds))
        logger.info("Learning loop started (interval: %.1fs)", interval_seconds)

    async def stop_loop(self):
        """Stop the learning loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Learning loop stopped")

    async def _loop(self, interval_seconds: float):
        """Background loop for continuous learning."""
        while self._running:
            try:
                observations = self.observation_engine.get_recent(limit=50)
                if observations:
                    patterns = self.extraction_engine.extract_from_observations(observations)
                    if patterns:
                        for agent_id in set(o.agent_id for o in observations):
                            self.compound(patterns, agent_id)
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Learning loop error: %s", e)
                await asyncio.sleep(interval_seconds)

    def get_status(self) -> dict:
        """Get comprehensive learning loop status."""
        return {
            "observation": self.observation_engine.get_stats(),
            "extraction": self.extraction_engine.get_stats(),
            "compounding": self.compounding_engine.get_stats(),
            "evolution": self.evolution_engine.get_stats(),
            "nudge": self.nudge_engine.get_stats(),
            "user_model": {
                "interaction_count": self._user_model.interaction_count,
                "session_count": self._user_model.session_count,
                "feedback_count": len(self._user_model.feedback_history),
                "last_active": self._user_model.last_active,
            },
            "running": self._running,
        }


# Global learning loop instance
learning_loop = LearningLoop()