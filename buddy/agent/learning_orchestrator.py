"""Buddy Learning Orchestrator — unified self-improvement coordination layer

Coordinates all learning subsystems — metacognition, evolution, skill compilation,
and proactive discovery — into a cohesive self-improvement pipeline. This is the
brain's executive function: it decides what to learn, when to consolidate, and
how to apply past experience to future decisions.

Architecture:
    LearningOrchestrator
    ├── StrategyOptimizer (refines reasoning strategies from outcomes)
    ├── ExperienceSynthesizer (distills patterns from execution history)
    ├── ConsolidationScheduler (triggers periodic learning cycles)
    ├── InsightPropagator (shares learnings across agent instances)
    └── LearningMetrics (tracks self-improvement effectiveness over time)

The orchestrator operates on three timescales:
  - Real-time: immediate strategy adjustments during execution
  - Periodic: scheduled consolidation runs (every N executions)
  - Background: continuous pattern detection from idle compute
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger("buddy.learning_orchestrator")


# ═══════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════

class LearningPhase(str, Enum):
    """Phases of the learning cycle."""
    COLLECT = "collect"          # Gather execution traces and outcomes
    ANALYZE = "analyze"          # Identify patterns and extract insights
    CONSOLIDATE = "consolidate"  # Integrate into strategies and heuristics
    PROPAGATE = "propagate"      # Share learnings across the system
    VERIFY = "verify"            # Test that new strategies improve outcomes


class InsightCategory(str, Enum):
    """Categories of learned insights."""
    STRATEGY = "strategy"              # Which reasoning strategy works best
    MODEL = "model"                    # Which model tier is optimal
    TOOL = "tool"                      # Which tools work well together
    PROMPT = "prompt"                  # Prompt patterns that improve results
    ERROR = "error"                    # Common failure patterns to avoid
    EFFICIENCY = "efficiency"         # Token/latency optimization
    COLLABORATION = "collaboration"   # Inter-agent coordination patterns


@dataclass
class LearningInsight:
    """A distilled insight from execution experience."""
    id: str = field(default_factory=lambda: f"insight-{uuid.uuid4().hex[:8]}")
    category: InsightCategory = InsightCategory.STRATEGY
    summary: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    impact_score: float = 0.0  # Estimated improvement from applying this
    applied_count: int = 0
    success_rate_after: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = ""  # Insights can expire if no longer relevant

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "summary": self.summary,
            "confidence": round(self.confidence, 2),
            "impact_score": round(self.impact_score, 3),
            "applied_count": self.applied_count,
            "success_rate_after": round(self.success_rate_after, 3),
            "created_at": self.created_at,
        }


@dataclass
class StrategyProfile:
    """A learned strategy profile mapping task patterns to optimal approaches."""
    id: str = field(default_factory=lambda: f"profile-{uuid.uuid4().hex[:8]}")
    task_pattern: str = ""              # Hash or description of task type
    preferred_style: str = "balanced"   # Best reasoning style
    preferred_model: str = "default"    # Best model tier
    preferred_tools: list[str] = field(default_factory=list)
    preferred_mode: str = "reasoned"    # Best execution mode
    success_count: int = 0
    total_attempts: int = 0
    avg_tokens: float = 0.0
    avg_latency_ms: float = 0.0
    last_used: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.total_attempts, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_pattern": self.task_pattern[:50],
            "preferred_style": self.preferred_style,
            "preferred_model": self.preferred_model,
            "preferred_mode": self.preferred_mode,
            "success_rate": round(self.success_rate, 3),
            "total_attempts": self.total_attempts,
            "avg_tokens": round(self.avg_tokens, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
        }


# ═══════════════════════════════════════════════════════════
# Learning Orchestrator
# ═══════════════════════════════════════════════════════════

class LearningOrchestrator:
    """Central coordination layer for all agent self-improvement.

    Integrates strategy optimization, experience synthesis, consolidation
    scheduling, and insight propagation into a unified learning pipeline.
    """

    def __init__(self, agent_id: str = "default", client: AsyncOpenAI | None = None):
        self.agent_id = agent_id
        self._client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        # Learning state
        self._insights: list[LearningInsight] = []
        self._profiles: dict[str, StrategyProfile] = {}
        self._execution_log: list[dict] = []
        self._error_patterns: dict[str, int] = defaultdict(int)

        # Configuration
        self._max_insights = 100
        self._max_profiles = 50
        self._max_execution_log = 500
        self._consolidation_interval = 20  # executions between consolidation
        self._executions_since_consolidation = 0
        self._min_confidence_for_application = 0.6

        # Metrics
        self._total_executions_tracked = 0
        self._total_insights_generated = 0
        self._total_insights_applied = 0
        self._baseline_success_rate = 0.0
        self._current_success_rate = 0.0

        # Background tasks
        self._consolidation_task: asyncio.Task | None = None
        self._is_running = False

        logger.info(f"LearningOrchestrator initialized for {agent_id}")

    # ── Execution Tracking ───────────────────────────────

    def track_execution(
        self,
        prompt: str,
        success: bool,
        strategy: dict | None = None,
        tokens_used: int = 0,
        latency_ms: float = 0.0,
        tools_used: list[str] | None = None,
        error: str = "",
    ):
        """Record an execution for learning analysis."""
        self._total_executions_tracked += 1

        # Generate task signature
        task_sig = self._compute_task_signature(prompt)

        # Log the execution
        entry = {
            "task_signature": task_sig,
            "prompt": prompt[:300],
            "success": success,
            "strategy": strategy or {},
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "tools_used": tools_used or [],
            "error": error[:200],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._execution_log.append(entry)
        if len(self._execution_log) > self._max_execution_log:
            self._execution_log = self._execution_log[-self._max_execution_log:]

        # Update strategy profile
        self._update_profile(task_sig, success, strategy or {}, tokens_used, latency_ms)

        # Track error patterns
        if not success and error:
            error_type = self._classify_error(error)
            self._error_patterns[error_type] += 1

        # Update success rate
        recent = [e for e in self._execution_log[-100:]]
        if recent:
            self._current_success_rate = sum(1 for e in recent if e["success"]) / len(recent)
            if self._baseline_success_rate == 0:
                self._baseline_success_rate = self._current_success_rate

        self._executions_since_consolidation += 1

    def _compute_task_signature(self, prompt: str) -> str:
        """Generate a stable task signature from prompt text."""
        import re
        # Normalize: lowercase, remove punctuation, take key words
        words = re.findall(r'\b\w{4,}\b', prompt.lower())
        key_words = sorted(set(words))[:10]
        sig = "|".join(key_words)
        return hashlib.md5(sig.encode()).hexdigest()[:12] if sig else "unknown"

    def _classify_error(self, error: str) -> str:
        """Classify an error into a pattern category."""
        error_lower = error.lower()
        if "timeout" in error_lower:
            return "timeout"
        elif "token" in error_lower or "budget" in error_lower:
            return "token_exhausted"
        elif "tool" in error_lower:
            return "tool_error"
        elif "model" in error_lower or "api" in error_lower:
            return "api_error"
        elif "parse" in error_lower or "json" in error_lower:
            return "parse_error"
        else:
            return "unknown_error"

    def _update_profile(
        self,
        task_sig: str,
        success: bool,
        strategy: dict,
        tokens_used: int,
        latency_ms: float,
    ):
        """Update or create a strategy profile for a task pattern."""
        if task_sig not in self._profiles:
            self._profiles[task_sig] = StrategyProfile(task_pattern=task_sig)

        profile = self._profiles[task_sig]
        if success:
            profile.success_count += 1
        profile.total_attempts += 1

        # Update preferred strategy based on success
        style = strategy.get("reasoning_style", "")
        if style and success:
            profile.preferred_style = style
        model = strategy.get("model", "")
        if model:
            profile.preferred_model = model
        mode = strategy.get("execution_mode", "")
        if mode:
            profile.preferred_mode = mode

        # Update averages
        n = profile.total_attempts
        profile.avg_tokens = (profile.avg_tokens * (n - 1) + tokens_used) / n
        profile.avg_latency_ms = (profile.avg_latency_ms * (n - 1) + latency_ms) / n
        profile.last_used = datetime.now(timezone.utc).isoformat()

        # Prune old profiles
        if len(self._profiles) > self._max_profiles:
            sorted_profiles = sorted(
                self._profiles.items(),
                key=lambda x: x[1].last_used,
            )
            for old_sig, _ in sorted_profiles[:len(self._profiles) - self._max_profiles]:
                del self._profiles[old_sig]

    # ── Strategy Optimization ────────────────────────────

    def get_best_strategy(self, prompt: str) -> dict | None:
        """Get the best known strategy for a task pattern."""
        task_sig = self._compute_task_signature(prompt)
        profile = self._profiles.get(task_sig)

        if profile and profile.total_attempts >= 3 and profile.success_rate >= 0.6:
            return {
                "reasoning_style": profile.preferred_style,
                "model": profile.preferred_model,
                "execution_mode": profile.preferred_mode,
                "tools": profile.preferred_tools,
                "confidence": profile.success_rate,
                "total_attempts": profile.total_attempts,
            }

        # Fallback: find similar profiles
        similar = self._find_similar_profiles(task_sig)
        if similar:
            best = similar[0]
            return {
                "reasoning_style": best.preferred_style,
                "model": best.preferred_model,
                "execution_mode": best.preferred_mode,
                "tools": best.preferred_tools,
                "confidence": best.success_rate * 0.8,  # Discounted for similarity
                "total_attempts": best.total_attempts,
            }

        return None

    def _find_similar_profiles(self, task_sig: str, limit: int = 3) -> list[StrategyProfile]:
        """Find profiles similar to the given task signature."""
        if not task_sig or len(task_sig) < 4:
            return []

        scored = []
        for sig, profile in self._profiles.items():
            if sig == task_sig:
                continue
            # Simple character-level similarity
            common = sum(1 for a, b in zip(sig, task_sig) if a == b)
            similarity = common / max(len(sig), len(task_sig))
            if similarity > 0.4:
                scored.append((similarity * profile.success_rate, profile))

        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored[:limit]]

    # ── Insight Generation ───────────────────────────────

    async def generate_insights(self) -> list[LearningInsight]:
        """Analyze execution history and generate learning insights.

        Uses LLM to identify patterns in successful and failed executions,
        then codifies these as actionable insights for future decisions.
        """
        if len(self._execution_log) < 10:
            return []

        recent = self._execution_log[-50:]
        successes = [e for e in recent if e["success"]]
        failures = [e for e in recent if not e["success"]]

        if len(successes) < 3 and len(failures) < 3:
            return []

        new_insights: list[LearningInsight] = []

        # Generate strategy insights from LLM analysis
        if successes:
            try:
                summary = "\n".join(
                    f"- {'SUCCESS' if e['success'] else 'FAIL'}: {e['prompt'][:150]} "
                    f"(strategy: {e['strategy'].get('reasoning_style', 'unknown')}, "
                    f"tokens: {e['tokens_used']})"
                    for e in recent[-15:]
                )

                response = await self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "system",
                        "content": (
                            "You are a learning analyst for an AI agent. Analyze execution patterns "
                            "and identify actionable insights for improving performance. "
                            "Respond in JSON:\n"
                            '{"insights": [{"category": "strategy|model|tool|prompt|error|efficiency", '
                            '"summary": "...", "confidence": 0.0-1.0, "impact": 0.0-1.0}]}'
                        ),
                    }, {
                        "role": "user",
                        "content": (
                            f"Recent execution history:\n{summary}\n\n"
                            f"Success rate: {len(successes)}/{(len(successes)+len(failures))} "
                            f"({len(successes)/max(len(successes)+len(failures),1)*100:.0f}%)\n"
                            f"Common errors: {dict(self._error_patterns.most_common(3)) if hasattr(self._error_patterns, 'most_common') else dict(self._error_patterns)}\n\n"
                            "Generate 2-4 actionable insights."
                        ),
                    }],
                    max_tokens=400,
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content or "{}"
                data = json.loads(content)

                for item in data.get("insights", []):
                    insight = LearningInsight(
                        category=InsightCategory(item.get("category", "strategy")),
                        summary=item.get("summary", ""),
                        confidence=float(item.get("confidence", 0.5)),
                        impact_score=float(item.get("impact", 0.0)),
                    )
                    self._insights.append(insight)
                    new_insights.append(insight)
                    self._total_insights_generated += 1

            except Exception as e:
                logger.debug(f"Insight generation via LLM skipped: {e}")

        # Also generate simple heuristic insights
        self._generate_heuristic_insights(new_insights)

        # Prune old insights
        if len(self._insights) > self._max_insights:
            self._insights = sorted(
                self._insights,
                key=lambda i: i.confidence * i.impact_score,
                reverse=True,
            )[:self._max_insights]

        return new_insights

    def _generate_heuristic_insights(self, existing: list[LearningInsight]):
        """Generate simple heuristic-based insights without LLM."""
        # Check error patterns
        for error_type, count in self._error_patterns.items():
            if count >= 3 and not any(
                error_type in i.summary for i in existing
            ):
                insight = LearningInsight(
                    category=InsightCategory.ERROR,
                    summary=f"Recurring error pattern '{error_type}' detected ({count} occurrences). Consider adjusting strategy when this pattern appears.",
                    confidence=0.7,
                    impact_score=0.3,
                )
                self._insights.append(insight)
                existing.append(insight)
                self._total_insights_generated += 1

        # Check success rate trend
        if self._current_success_rate < self._baseline_success_rate * 0.8:
            if not any("success rate declining" in i.summary for i in existing):
                insight = LearningInsight(
                    category=InsightCategory.STRATEGY,
                    summary=(
                        f"Success rate declining: {self._current_success_rate:.0%} vs "
                        f"baseline {self._baseline_success_rate:.0%}. Consider strategy recalibration."
                    ),
                    confidence=0.65,
                    impact_score=0.5,
                )
                self._insights.append(insight)
                existing.append(insight)
                self._total_insights_generated += 1

    # ── Consolidation ────────────────────────────────────

    async def consolidate(self) -> dict:
        """Run a consolidation cycle: analyze, generate insights, update profiles.

        This is the periodic "learning moment" where the orchestrator
        pauses to reflect on recent experience and codify improvements.
        """
        self._executions_since_consolidation = 0

        # Generate insights from recent executions
        new_insights = await self.generate_insights()

        # Update baseline
        self._baseline_success_rate = self._current_success_rate

        # Prune old profiles with low success
        stale_profiles = [
            sig for sig, profile in self._profiles.items()
            if profile.total_attempts >= 5 and profile.success_rate < 0.3
        ]
        for sig in stale_profiles:
            del self._profiles[sig]

        result = {
            "insights_generated": len(new_insights),
            "total_insights": len(self._insights),
            "total_profiles": len(self._profiles),
            "profiles_pruned": len(stale_profiles),
            "current_success_rate": round(self._current_success_rate, 3),
            "error_patterns": dict(self._error_patterns),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Consolidation complete for {self.agent_id}: "
            f"{len(new_insights)} new insights, {len(self._profiles)} profiles"
        )
        return result

    # ── Background Learning ──────────────────────────────

    async def start_background_learning(self):
        """Start periodic background consolidation."""
        self._is_running = True
        self._consolidation_task = asyncio.create_task(self._background_loop())
        logger.info(f"Background learning started for {self.agent_id}")

    async def stop_background_learning(self):
        """Stop background consolidation."""
        self._is_running = False
        if self._consolidation_task:
            self._consolidation_task.cancel()
            try:
                await self._consolidation_task
            except asyncio.CancelledError:
                pass

    async def _background_loop(self):
        """Periodic background consolidation loop."""
        while self._is_running:
            await asyncio.sleep(300)  # Every 5 minutes
            if self._executions_since_consolidation >= self._consolidation_interval:
                try:
                    await self.consolidate()
                except Exception as e:
                    logger.error(f"Background consolidation error: {e}")

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict:
        """Get comprehensive learning statistics."""
        return {
            "agent_id": self.agent_id,
            "tracked_executions": self._total_executions_tracked,
            "insights": {
                "total": len(self._insights),
                "generated": self._total_insights_generated,
                "applied": self._total_insights_applied,
                "by_category": {
                    cat.value: sum(1 for i in self._insights if i.category == cat)
                    for cat in InsightCategory
                },
            },
            "profiles": {
                "total": len(self._profiles),
                "avg_success_rate": round(
                    sum(p.success_rate for p in self._profiles.values()) / max(len(self._profiles), 1), 3
                ),
                "top_profiles": [
                    p.to_dict()
                    for p in sorted(
                        self._profiles.values(),
                        key=lambda x: x.success_rate,
                        reverse=True,
                    )[:5]
                ],
            },
            "performance": {
                "baseline_success_rate": round(self._baseline_success_rate, 3),
                "current_success_rate": round(self._current_success_rate, 3),
                "improvement": round(
                    self._current_success_rate - self._baseline_success_rate, 3
                ),
            },
            "error_patterns": dict(self._error_patterns),
            "consolidation": {
                "interval": self._consolidation_interval,
                "since_last": self._executions_since_consolidation,
                "is_running": self._is_running,
            },
        }

    def get_insights(
        self, category: str | None = None, limit: int = 20
    ) -> list[dict]:
        """Get learning insights with optional category filter."""
        insights = self._insights
        if category:
            insights = [i for i in insights if i.category.value == category]
        return [
            i.to_dict()
            for i in sorted(
                insights,
                key=lambda x: x.confidence * x.impact_score,
                reverse=True,
            )[:limit]
        ]

    def get_best_strategies(self, limit: int = 10) -> list[dict]:
        """Get the top-performing strategy profiles."""
        return [
            p.to_dict()
            for p in sorted(
                self._profiles.values(),
                key=lambda x: x.success_rate * x.total_attempts,
                reverse=True,
            )[:limit]
        ]


# Global learning orchestrator instance
learning_orchestrator = LearningOrchestrator()