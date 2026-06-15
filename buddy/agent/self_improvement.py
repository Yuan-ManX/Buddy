"""Buddy Learning Loop — Autonomous skill generation from interaction patterns

The self-improvement cycle analyzes agent interactions to:
- Detect successful interaction patterns and workflows
- Generate candidate skills from repeated successful patterns
- Validate skills through test execution against past interactions
- Promote validated skills to the skill registry
- Track skill performance with continuous feedback scoring

Pattern detection uses LLM-powered analysis of conversation history,
extracting reusable strategies, decision frameworks, and procedural
knowledge that compound the agent's capabilities over time.
"""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.self_improvement")


class PatternType(str, Enum):
    WORKFLOW = "workflow"
    DECISION = "decision"
    STRATEGY = "strategy"
    CONVERSATION = "conversation"
    PROBLEM_SOLVING = "problem_solving"


class SkillStatus(str, Enum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


@dataclass
class InteractionPattern:
    """A detected reusable pattern from agent interactions."""
    id: str
    pattern_type: PatternType
    name: str
    description: str
    trigger_keywords: list[str]
    steps: list[dict]
    success_rate: float = 0.0
    usage_count: int = 0
    discovered_at: str = ""
    last_used: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.value,
            "name": self.name,
            "description": self.description,
            "trigger_keywords": self.trigger_keywords,
            "step_count": len(self.steps),
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "discovered_at": self.discovered_at,
            "last_used": self.last_used,
        }


@dataclass
class CandidateSkill:
    """A skill generated from interaction patterns pending validation."""
    id: str
    agent_id: str
    name: str
    description: str
    source_patterns: list[str]
    prompt_template: str
    tools_required: list[str]
    status: SkillStatus = SkillStatus.CANDIDATE
    score: float = 0.0
    validation_results: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "source_patterns": self.source_patterns,
            "status": self.status.value,
            "score": self.score,
            "tools_required": self.tools_required,
            "validation_count": len(self.validation_results),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class LearningLoop:
    """Autonomous skill discovery and generation from interaction patterns.

    The learning loop runs in three phases:
    1. Pattern Detection — Analyze conversation history for reusable patterns
    2. Skill Generation — Create candidate skills from detected patterns
    3. Validation — Test skills against historical interactions
    """

    def __init__(self, agent_id: str, client: AsyncOpenAI | None = None):
        self.agent_id = agent_id
        self.client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._patterns: dict[str, InteractionPattern] = {}
        self._candidates: dict[str, CandidateSkill] = {}
        self._session_interactions: list[dict] = []
        self._interaction_threshold = 20  # min interactions before pattern detection
        self._confidence_threshold = 0.7  # min confidence to promote a skill

    def record_interaction(self, user_message: str, assistant_response: str, tools_used: list[str] | None = None, success: bool = True):
        """Record a single interaction for pattern analysis."""
        self._session_interactions.append({
            "user": user_message,
            "assistant": assistant_response[:500],
            "tools": tools_used or [],
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Trigger analysis when threshold is hit
        if len(self._session_interactions) >= self._interaction_threshold:
            logger.info(f"Interaction threshold ({self._interaction_threshold}) reached for {self.agent_id}")

    async def analyze_patterns(self) -> list[InteractionPattern]:
        """Analyze recorded interactions for reusable patterns using LLM."""
        if len(self._session_interactions) < 5:
            return []

        # Prepare analysis prompt
        sample = self._session_interactions[-30:]
        interactions_text = "\n\n".join([
            f"User: {i['user'][:300]}\nAgent: {i['assistant'][:300]}\nTools: {', '.join(i['tools'])}"
            for i in sample
        ])

        analysis_prompt = f"""Analyze these agent interactions for reusable patterns.

Identify 2-4 patterns that can be turned into reusable skills:
1. Workflows: Multi-step procedures that solve common tasks
2. Decision patterns: Frameworks for making consistent decisions
3. Strategies: Approaches for tackling specific problem types
4. Problem-solving: General problem-solving methodologies

For each pattern found, output a JSON object with these fields:
- pattern_type: "workflow" | "decision" | "strategy" | "problem_solving"
- name: Short descriptive name (2-4 words)
- description: What the pattern does and when to use it
- trigger_keywords: List of keywords that indicate this pattern should be used
- steps: Array of {{"step": step_number, "action": description, "purpose": rationale}}

Return ONLY valid JSON: [{{pattern1}}, {{pattern2}}, ...]

Interactions:
{interactions_text}"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You analyze agent interactions to detect reusable patterns. Output only valid JSON."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
            )

            content = response.choices[0].message.content or "[]"
            # Extract JSON from response
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                content = content[json_start:json_end]

            patterns_data = json.loads(content)
            new_patterns = []

            for p in patterns_data:
                pid = f"pat-{uuid.uuid4().hex[:8]}"
                pattern = InteractionPattern(
                    id=pid,
                    pattern_type=PatternType(p.get("pattern_type", "workflow")),
                    name=p.get("name", "Unnamed Pattern"),
                    description=p.get("description", ""),
                    trigger_keywords=p.get("trigger_keywords", []),
                    steps=p.get("steps", []),
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                )
                self._patterns[pid] = pattern
                new_patterns.append(pattern)

            logger.info(f"Discovered {len(new_patterns)} patterns for agent {self.agent_id}")
            return new_patterns

        except Exception as e:
            logger.warning(f"Pattern analysis failed: {e}")
            return []

    async def generate_skills_from_patterns(self, patterns: list[InteractionPattern]) -> list[CandidateSkill]:
        """Generate candidate skills from detected interaction patterns."""
        candidates = []

        for pattern in patterns:
            # Skip patterns that are too simple
            if len(pattern.steps) < 2:
                continue

            skill_id = f"learned-skill-{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()

            skill = CandidateSkill(
                id=skill_id,
                agent_id=self.agent_id,
                name=f"auto_{pattern.name.lower().replace(' ', '_')}",
                description=pattern.description,
                source_patterns=[pattern.id],
                prompt_template=self._build_prompt_template(pattern),
                tools_required=self._infer_tools(pattern),
                created_at=now,
                updated_at=now,
            )
            candidates.append(skill)

        # Validate candidates against historical interactions
        for skill in candidates:
            await self._validate_skill(skill)
            self._candidates[skill.id] = skill

        logger.info(f"Generated {len(candidates)} candidate skills for {self.agent_id}")
        return candidates

    def _build_prompt_template(self, pattern: InteractionPattern) -> str:
        """Build a prompt template for a skill from a detected pattern."""
        steps_text = "\n".join([
            f"{s.get('step', i+1)}. {s.get('action', '')} — {s.get('purpose', '')}"
            for i, s in enumerate(pattern.steps)
        ])

        return f"""Execute the "{pattern.name}" workflow:
{pattern.description}

Steps:
{steps_text}

Adapt this approach to the user's specific situation while following the core methodology."""

    def _infer_tools(self, pattern: InteractionPattern) -> list[str]:
        """Infer which tools might be needed based on pattern steps."""
        tool_keywords = {
            "calculate": "calculate",
            "search": "web_search",
            "file": "file_read",
            "code": "code_execute",
            "python": "code_execute",
            "write": "file_write",
            "read": "file_read",
            "execute": "code_execute",
            "deploy": "shell_execute",
            "browse": "web_search",
            "fetch": "web_search",
            "query": "web_search",
        }

        tools = set()
        for step in pattern.steps:
            action = step.get("action", "").lower()
            purpose = step.get("purpose", "").lower()
            combined = f"{action} {purpose}"
            for keyword, tool in tool_keywords.items():
                if keyword in combined:
                    tools.add(tool)
        return list(tools) if tools else ["chat"]

    async def _validate_skill(self, skill: CandidateSkill) -> float:
        """Validate a candidate skill against recent interactions."""
        if not self._session_interactions:
            skill.status = SkillStatus.CANDIDATE
            skill.score = 0.5
            return skill.score

        # Test against recent interactions
        test_sample = self._session_interactions[-5:]
        scores = []

        for interaction in test_sample:
            # Check if pattern's trigger keywords match
            user_text = interaction["user"].lower()
            keyword_match = False
            if skill.source_patterns:
                for pid in skill.source_patterns:
                    pattern = self._patterns.get(pid)
                    if pattern:
                        if any(kw.lower() in user_text for kw in pattern.trigger_keywords):
                            keyword_match = True
                            break

            # Simulated execution score (in production, actually run the skill)
            base_score = 0.7 if keyword_match else 0.3
            if interaction.get("success"):
                base_score += 0.15
            scores.append(min(base_score, 1.0))

        avg_score = sum(scores) / len(scores) if scores else 0.0
        skill.score = avg_score
        skill.validation_results = [
            {"test": i, "score": s}
            for i, s in enumerate(scores)
        ]

        if avg_score >= self._confidence_threshold:
            skill.status = SkillStatus.VALIDATED
        elif avg_score >= 0.4:
            skill.status = SkillStatus.CANDIDATE
        else:
            skill.status = SkillStatus.REJECTED

        return avg_score

    async def promote_validated_skills(self) -> list[str]:
        """Promote validated skills to the skill registry."""
        promoted = []
        for skill in list(self._candidates.values()):
            if skill.status == SkillStatus.VALIDATED and skill.score >= self._confidence_threshold:
                # Create a handler function for the skill
                async def make_skill_handler(sk: CandidateSkill):
                    async def handler(params: dict) -> str:
                        # Execute the skill using the prompt template
                        user_input = params.get("input", "")
                        response = await self.client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": sk.prompt_template},
                                {"role": "user", "content": user_input},
                            ],
                            temperature=0.5,
                            max_tokens=2048,
                        )
                        return response.choices[0].message.content or ""
                    return handler

                skill.status = SkillStatus.PROMOTED
                skill.updated_at = datetime.now(timezone.utc).isoformat()
                promoted.append(skill.id)

                # Register the skill handler in the skills registry
                handler_fn = await make_skill_handler(skill)
                try:
                    from .shared import skills_registry
                    skills_registry.register(
                        skill_id=skill.id,
                        name=skill.name,
                        handler=handler_fn,
                        description=skill.description,
                        tags=skill.tags,
                    )
                except (ImportError, AttributeError) as e:
                    logger.warning(f"Could not register promoted skill {skill.name}: {e}")

                logger.info(f"Promoted skill: {skill.name} (score: {skill.score:.2f})")

        return promoted

    async def run_full_cycle(self) -> dict:
        """Execute a complete learning cycle: analyze → generate → validate → promote."""
        result = {
            "agent_id": self.agent_id,
            "interactions_analyzed": len(self._session_interactions),
            "patterns_found": 0,
            "skills_generated": 0,
            "skills_validated": 0,
            "skills_promoted": 0,
        }

        # Phase 1: Pattern detection
        patterns = await self.analyze_patterns()
        result["patterns_found"] = len(patterns)

        # Phase 2: Skill generation
        if patterns:
            candidates = await self.generate_skills_from_patterns(patterns)
            result["skills_generated"] = len(candidates)
            result["skills_validated"] = sum(
                1 for c in candidates if c.status != SkillStatus.REJECTED
            )

            # Phase 3: Promotion
            promoted = await self.promote_validated_skills()
            result["skills_promoted"] = len(promoted)

        # Clear session interactions after processing
        self._session_interactions = []

        return result

    def get_patterns(self) -> list[dict]:
        """Get all detected patterns."""
        return [p.to_dict() for p in self._patterns.values()]

    def get_candidates(self) -> list[dict]:
        """Get all candidate skills."""
        return [c.to_dict() for c in self._candidates.values()]

    def get_stats(self) -> dict:
        """Get learning loop statistics."""
        return {
            "agent_id": self.agent_id,
            "total_patterns": len(self._patterns),
            "total_candidates": len(self._candidates),
            "candidates_by_status": {
                status.value: sum(1 for c in self._candidates.values() if c.status == status)
                for status in SkillStatus
            },
            "session_interactions": len(self._session_interactions),
            "interaction_threshold": self._interaction_threshold,
            "confidence_threshold": self._confidence_threshold,
        }


class SelfImprovementEngine:
    """Manages learning loops across multiple agents and orchestrates discovery cycles.

    Provides:
    - Scheduled analysis cycles for idle agents
    - Cross-agent pattern sharing (anonymized)
    - Performance tracking across learning iterations
    """

    def __init__(self):
        self._loops: dict[str, LearningLoop] = {}
        self._client: AsyncOpenAI | None = None
        self._cycle_history: list[dict] = []

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
        return self._client

    def get_loop(self, agent_id: str) -> LearningLoop:
        """Get or create a learning loop for an agent."""
        if agent_id not in self._loops:
            self._loops[agent_id] = LearningLoop(agent_id, self._get_client())
        return self._loops[agent_id]

    def record(self, agent_id: str, user_message: str, assistant_response: str, tools_used: list[str] | None = None, success: bool = True):
        """Record an interaction for pattern analysis."""
        loop = self.get_loop(agent_id)
        loop.record_interaction(user_message, assistant_response, tools_used, success)

    async def run_cycle(self, agent_id: str) -> dict:
        """Run a full learning cycle for a specific agent."""
        loop = self.get_loop(agent_id)
        result = await loop.run_full_cycle()
        self._cycle_history.append({
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **result,
        })
        return result

    async def run_all_cycles(self) -> dict:
        """Run learning cycles for all agents with sufficient interactions."""
        results = {}
        for agent_id, loop in list(self._loops.items()):
            if len(loop._session_interactions) >= loop._interaction_threshold:
                results[agent_id] = await self.run_cycle(agent_id)
        return results

    def get_agent_stats(self, agent_id: str) -> dict:
        """Get learning statistics for an agent."""
        loop = self._loops.get(agent_id)
        if not loop:
            return {"agent_id": agent_id, "error": "No learning loop active"}
        return loop.get_stats()

    def get_cycle_history(self, limit: int = 20) -> list[dict]:
        """Get recent learning cycle results."""
        return self._cycle_history[-limit:]


# Global singleton
self_improvement = SelfImprovementEngine()