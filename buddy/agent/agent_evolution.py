"""Buddy Agent Evolution — self-optimization through experience replay and adaptive learning

The evolution system continuously refines the agent's behavior by:
- Recording execution experiences with outcomes and context
- Replaying past experiences to identify successful strategies
- Adapting learning pathways based on performance metrics
- Generating optimization insights for metacognition and routing
- Maintaining a feedback loop between strategy selection and outcomes
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

logger = logging.getLogger("buddy.evolution")


class ExperienceType(str, Enum):
    CHAT = "chat"
    TOOL_CALL = "tool_call"
    REASONING = "reasoning"
    PLAN_EXECUTION = "plan_execution"
    SKILL_EXECUTION = "skill_execution"
    COLLABORATION = "collaboration"
    SUBAGENT = "subagent"


class ExperienceOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"


@dataclass
class Experience:
    """A single execution experience for learning."""
    id: str
    agent_id: str
    experience_type: ExperienceType
    task_signature: str
    strategy_used: dict
    outcome: ExperienceOutcome
    quality_score: float
    tokens_consumed: int
    latency_ms: float
    context: dict = field(default_factory=dict)
    insights: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "experience_type": self.experience_type.value,
            "task_signature": self.task_signature[:100],
            "strategy_used": self.strategy_used,
            "outcome": self.outcome.value,
            "quality_score": self.quality_score,
            "tokens_consumed": self.tokens_consumed,
            "latency_ms": self.latency_ms,
            "insights": self.insights,
            "created_at": self.created_at,
        }


@dataclass
class EvolutionPathway:
    """A learned optimization pathway connecting task patterns to strategies."""
    id: str
    name: str
    task_pattern: str
    recommended_strategy: str
    success_rate: float
    sample_count: int
    avg_tokens: int
    avg_latency_ms: float
    confidence: float
    last_updated: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "task_pattern": self.task_pattern[:100],
            "recommended_strategy": self.recommended_strategy,
            "success_rate": self.success_rate,
            "sample_count": self.sample_count,
            "avg_tokens": self.avg_tokens,
            "avg_latency_ms": self.avg_latency_ms,
            "confidence": self.confidence,
            "last_updated": self.last_updated,
        }


class AgentEvolution:
    """Self-optimization engine that learns from execution experiences.

    Maintains a replay buffer of past experiences, periodically analyzes
    them to discover optimization pathways, and feeds insights back into
    the metacognition and routing systems.
    """

    def __init__(self, agent_id: str, client: AsyncOpenAI | None = None):
        self.agent_id = agent_id
        self._client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._experiences: list[Experience] = []
        self._pathways: dict[str, EvolutionPathway] = {}
        self._max_experiences = 200
        self._analysis_threshold = 30
        self._insights: list[str] = []
        self._total_experiences = 0
        self._success_count = 0
        self._failure_count = 0
        self._last_analysis_at: str = ""

    def record_experience(
        self,
        experience_type: ExperienceType,
        task_signature: str,
        strategy_used: dict,
        outcome: ExperienceOutcome,
        quality_score: float,
        tokens_consumed: int,
        latency_ms: float,
        context: dict | None = None,
    ) -> Experience:
        """Record an execution experience in the replay buffer."""
        exp = Experience(
            id=f"exp-{uuid.uuid4().hex[:8]}",
            agent_id=self.agent_id,
            experience_type=experience_type,
            task_signature=task_signature,
            strategy_used=strategy_used,
            outcome=outcome,
            quality_score=quality_score,
            tokens_consumed=tokens_consumed,
            latency_ms=latency_ms,
            context=context or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._experiences.append(exp)
        self._total_experiences += 1

        if outcome == ExperienceOutcome.SUCCESS:
            self._success_count += 1
        elif outcome == ExperienceOutcome.FAILURE:
            self._failure_count += 1

        # Prune old experiences if over limit
        if len(self._experiences) > self._max_experiences:
            self._experiences = self._experiences[-self._max_experiences:]

        logger.debug(
            f"Recorded experience {exp.id}: type={experience_type.value}, "
            f"outcome={outcome.value}, quality={quality_score:.2f}"
        )
        return exp

    async def analyze_experiences(self) -> list[EvolutionPathway]:
        """Analyze recent experiences to discover optimization pathways.

        Groups experiences by task patterns, identifies which strategies
        perform best for each pattern, and generates or updates pathways.
        """
        if len(self._experiences) < 10:
            return []

        self._last_analysis_at = datetime.now(timezone.utc).isoformat()

        # Group experiences by task signature patterns
        pattern_groups: dict[str, list[Experience]] = {}
        for exp in self._experiences:
            pattern = self._extract_pattern(exp.task_signature)
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(exp)

        new_pathways = []
        for pattern, experiences in pattern_groups.items():
            if len(experiences) < 3:
                continue

            # Calculate success rate for each strategy used with this pattern
            strategy_outcomes: dict[str, dict] = {}
            for exp in experiences:
                strategy_key = exp.strategy_used.get("execution_mode", "direct")
                if strategy_key not in strategy_outcomes:
                    strategy_outcomes[strategy_key] = {
                        "successes": 0,
                        "failures": 0,
                        "total_tokens": 0,
                        "total_latency": 0,
                        "count": 0,
                    }
                stats = strategy_outcomes[strategy_key]
                stats["count"] += 1
                stats["total_tokens"] += exp.tokens_consumed
                stats["total_latency"] += exp.latency_ms
                if exp.outcome == ExperienceOutcome.SUCCESS:
                    stats["successes"] += 1
                elif exp.outcome == ExperienceOutcome.FAILURE:
                    stats["failures"] += 1

            # Find the best strategy for this pattern
            best_strategy = None
            best_score = -1.0
            for strategy_key, stats in strategy_outcomes.items():
                success_rate = stats["successes"] / max(stats["count"], 1)
                # Weight by success rate and sample count
                score = success_rate * 0.7 + min(stats["count"] / 10, 1.0) * 0.3
                if score > best_score:
                    best_score = score
                    best_strategy = strategy_key

            if best_strategy:
                best_stats = strategy_outcomes[best_strategy]
                success_rate = best_stats["successes"] / max(best_stats["count"], 1)
                avg_tokens = best_stats["total_tokens"] // max(best_stats["count"], 1)
                avg_latency = best_stats["total_latency"] / max(best_stats["count"], 1)

                pathway_id = f"pw-{uuid.uuid4().hex[:8]}"
                pathway = EvolutionPathway(
                    id=pathway_id,
                    name=f"Optimize {pattern[:30]}",
                    task_pattern=pattern,
                    recommended_strategy=best_strategy,
                    success_rate=success_rate,
                    sample_count=best_stats["count"],
                    avg_tokens=avg_tokens,
                    avg_latency_ms=avg_latency,
                    confidence=best_score,
                    last_updated=datetime.now(timezone.utc).isoformat(),
                )
                self._pathways[pathway_id] = pathway
                new_pathways.append(pathway)

        # Generate insights from analysis
        await self._generate_insights(new_pathways)

        logger.info(
            f"Evolution analysis complete: {len(new_pathways)} pathways "
            f"from {len(self._experiences)} experiences"
        )
        return new_pathways

    async def _generate_insights(self, pathways: list[EvolutionPathway]):
        """Generate actionable insights from pathway analysis."""
        if not pathways:
            return

        # Synthesize insights from pathways
        high_confidence = [p for p in pathways if p.confidence > 0.7]
        if high_confidence:
            self._insights.append(
                f"High-confidence optimization: {len(high_confidence)} task patterns "
                f"have clear winning strategies with >70% confidence"
            )

        # Look for strategy dominance patterns
        strategy_counts: dict[str, int] = {}
        for p in pathways:
            strategy_counts[p.recommended_strategy] = strategy_counts.get(p.recommended_strategy, 0) + 1

        dominant = max(strategy_counts, key=strategy_counts.get)
        if strategy_counts[dominant] >= 3:
            self._insights.append(
                f"Strategy '{dominant}' dominates across {strategy_counts[dominant]} "
                f"task patterns — consider as default for similar tasks"
            )

        # Cost efficiency insights
        avg_tokens = sum(p.avg_tokens for p in pathways) / len(pathways)
        if avg_tokens > 2000:
            self._insights.append(
                f"Average token usage ({avg_tokens:.0f}) is elevated — "
                f"consider enabling context compaction for complex patterns"
            )

        # Keep only the most recent 20 insights
        if len(self._insights) > 20:
            self._insights = self._insights[-20:]

    def _extract_pattern(self, task_signature: str) -> str:
        """Extract a generalized pattern from a task signature.

        Collapses specific details to create reusable pattern categories
        that can group similar tasks together.
        """
        sig = task_signature.lower().strip()

        # Pattern-based categorization
        if any(kw in sig for kw in ["code", "function", "bug", "debug", "implement"]):
            return "coding_implementation"
        if any(kw in sig for kw in ["explain", "what is", "how does", "define"]):
            return "explanation_query"
        if any(kw in sig for kw in ["compare", "vs", "difference", "pros and cons"]):
            return "comparative_analysis"
        if any(kw in sig for kw in ["create", "build", "generate", "design"]):
            return "creation_generation"
        if any(kw in sig for kw in ["fix", "error", "issue", "problem", "broken"]):
            return "troubleshooting"
        if any(kw in sig for kw in ["summarize", "summary", "tl;dr", "key points"]):
            return "summarization"
        if any(kw in sig for kw in ["plan", "strategy", "roadmap", "approach"]):
            return "planning_strategy"
        if any(kw in sig for kw in ["optimize", "improve", "better", "faster"]):
            return "optimization"
        if any(kw in sig for kw in ["hello", "hi", "hey", "greetings"]):
            return "greeting_social"
        if any(kw in sig for kw in ["search", "find", "lookup", "research"]):
            return "research_lookup"

        # Fallback: use first 30 chars as pattern
        return sig[:30] if len(sig) > 30 else sig

    async def replay_experiences(self, limit: int = 20) -> dict:
        """Replay recent experiences to validate current pathways.

        Simulates replay by checking if current pathways would have
        recommended the correct strategy for past experiences.
        """
        recent = self._experiences[-limit:]
        if not recent:
            return {"validated": 0, "total": 0, "accuracy": 0.0}

        correct = 0
        for exp in recent:
            pattern = self._extract_pattern(exp.task_signature)
            # Find best matching pathway
            best_pathway = None
            for pathway in self._pathways.values():
                if pathway.task_pattern == pattern:
                    if best_pathway is None or pathway.confidence > best_pathway.confidence:
                        best_pathway = pathway

            if best_pathway and best_pathway.recommended_strategy == exp.strategy_used.get("execution_mode", ""):
                correct += 1

        accuracy = correct / len(recent) if recent else 0.0
        return {
            "validated": correct,
            "total": len(recent),
            "accuracy": accuracy,
            "message": f"Pathway validation: {correct}/{len(recent)} correct ({accuracy:.1%})",
        }

    async def run_evolution_cycle(self) -> dict:
        """Execute a complete evolution cycle: analyze → validate → generate insights."""
        if len(self._experiences) < self._analysis_threshold:
            return {
                "agent_id": self.agent_id,
                "status": "skipped",
                "reason": f"Need {self._analysis_threshold} experiences, have {len(self._experiences)}",
                "experiences_total": len(self._experiences),
            }

        pathways = await self.analyze_experiences()
        replay_result = await self.replay_experiences()

        return {
            "agent_id": self.agent_id,
            "status": "completed",
            "pathways_discovered": len(pathways),
            "pathways_total": len(self._pathways),
            "experiences_analyzed": len(self._experiences),
            "replay_accuracy": replay_result["accuracy"],
            "insights_generated": len(self._insights),
            "last_analysis": self._last_analysis_at,
        }

    def get_pathway(self, task_pattern: str) -> EvolutionPathway | None:
        """Get the best optimization pathway for a task pattern."""
        pattern = self._extract_pattern(task_pattern)
        best = None
        for pathway in self._pathways.values():
            if pathway.task_pattern == pattern:
                if best is None or pathway.confidence > best.confidence:
                    best = pathway
        return best

    def get_pathways(self) -> list[dict]:
        """Get all discovered optimization pathways."""
        return [p.to_dict() for p in self._pathways.values()]

    def get_insights(self, limit: int = 20) -> list[str]:
        """Get recent evolution insights."""
        return self._insights[-limit:]

    def get_experiences(self, limit: int = 50) -> list[dict]:
        """Get recent experiences."""
        return [e.to_dict() for e in self._experiences[-limit:]]

    def get_stats(self) -> dict:
        """Get evolution engine statistics."""
        return {
            "agent_id": self.agent_id,
            "total_experiences": self._total_experiences,
            "buffer_size": len(self._experiences),
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": (
                self._success_count / max(self._total_experiences, 1)
            ),
            "pathways_count": len(self._pathways),
            "insights_count": len(self._insights),
            "last_analysis_at": self._last_analysis_at,
            "analysis_threshold": self._analysis_threshold,
        }