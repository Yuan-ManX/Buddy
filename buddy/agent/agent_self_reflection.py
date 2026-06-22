"""
Buddy Self-Reflection Engine - Multi-Perspective Action Analysis.

Evaluates past actions from multiple perspectives, identifies improvement
opportunities, and generates actionable feedback for continuous agent evolution.
Part of the AI-Native Buddy Agent system.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import logging

logger = logging.getLogger(__name__)


class ReflectionDepth(str, Enum):
    """Depth of reflection analysis."""
    SURFACE = "surface"
    STRUCTURAL = "structural"
    ROOT_CAUSE = "root_cause"
    META = "meta"


class ReflectionPerspective(str, Enum):
    """Lens through which to analyze actions."""
    EFFICIENCY = "efficiency"
    QUALITY = "quality"
    CORRECTNESS = "correctness"
    CREATIVITY = "creativity"
    COMMUNICATION = "communication"
    ETHICS = "ethics"
    USER_SATISFACTION = "user_satisfaction"
    RESOURCE_USAGE = "resource_usage"


class InsightType(str, Enum):
    """Type of insight generated from reflection."""
    PATTERN = "pattern"
    HEURISTIC = "heuristic"
    WARNING = "warning"
    OPPORTUNITY = "opportunity"
    RULE = "rule"
    PREFERENCE = "preference"


class ImprovementPriority(str, Enum):
    """Priority level for improvement actions."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OBSERVATION = "observation"


@dataclass
class ActionRecord:
    """A single action to be reflected upon."""
    action_id: str
    action_type: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    outcome: str = "unknown"
    confidence: float = 0.5
    duration_ms: float = 0.0
    tokens_used: int = 0
    tools_called: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfReflectionInsight:
    """An insight generated from self-reflection."""
    insight_id: str
    insight_type: InsightType
    content: str
    perspective: ReflectionPerspective
    priority: ImprovementPriority = ImprovementPriority.MEDIUM
    confidence: float = 0.5
    source_actions: list[str] = field(default_factory=list)
    suggested_action: str | None = None
    created_at: float = field(default_factory=time.time)
    applied: bool = False
    impact_score: float = 0.0


@dataclass
class SelfReflectionSession:
    """A complete self-reflection session with all findings."""
    session_id: str
    agent_id: str
    depth: ReflectionDepth
    perspectives: list[ReflectionPerspective]
    actions: list[ActionRecord] = field(default_factory=list)
    insights: list[SelfReflectionInsight] = field(default_factory=list)
    summary: str = ""
    improvement_plan: list[dict[str, Any]] = field(default_factory=list)
    overall_score: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class SelfReflectionEngine:
    """Multi-perspective self-reflection engine for agent improvement.

    Analyzes past actions from multiple perspectives, identifies patterns,
    generates actionable insights, and produces improvement plans.
    """

    MAX_ACTIONS_PER_SESSION = 50
    MAX_INSIGHTS_PER_SESSION = 20

    def __init__(self) -> None:
        self._sessions: dict[str, SelfReflectionSession] = {}
        self._insight_library: dict[str, SelfReflectionInsight] = {}
        self._action_history: list[ActionRecord] = []
        self._pattern_counts: dict[str, int] = defaultdict(int)
        self._total_sessions: int = 0
        self._total_insights: int = 0

    def start_session(
        self,
        agent_id: str,
        depth: ReflectionDepth = ReflectionDepth.STRUCTURAL,
        perspectives: list[ReflectionPerspective] | None = None,
    ) -> SelfReflectionSession:
        """Start a new self-reflection session."""
        session = SelfReflectionSession(
            session_id=f"ref-{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            depth=depth,
            perspectives=perspectives or list(ReflectionPerspective),
        )
        self._sessions[session.session_id] = session
        self._total_sessions += 1
        logger.info(f"Self-reflection session '{session.session_id}' started for agent '{agent_id}'")
        return session

    def record_action(
        self,
        session_id: str,
        action_type: str,
        description: str,
        outcome: str = "unknown",
        confidence: float = 0.5,
        duration_ms: float = 0.0,
        tokens_used: int = 0,
        tools_called: list[str] | None = None,
        errors: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ActionRecord | None:
        """Record an action for reflection."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        action = ActionRecord(
            action_id=f"act-{uuid.uuid4().hex[:8]}",
            action_type=action_type,
            description=description,
            outcome=outcome,
            confidence=confidence,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            tools_called=tools_called or [],
            errors=errors or [],
            context=context or {},
        )
        session.actions.append(action)
        self._action_history.append(action)

        if len(session.actions) > self.MAX_ACTIONS_PER_SESSION:
            session.actions.pop(0)

        self._pattern_counts[f"{action_type}:{outcome}"] += 1
        return action

    def reflect(
        self,
        session_id: str,
        depth: ReflectionDepth | None = None,
    ) -> list[SelfReflectionInsight]:
        """Execute reflection on recorded actions."""
        session = self._sessions.get(session_id)
        if not session:
            return []

        if depth:
            session.depth = depth

        if not session.actions:
            logger.warning("No actions to reflect on")
            return []

        insights: list[SelfReflectionInsight] = []

        for perspective in session.perspectives:
            perspective_insights = self._reflect_from_perspective(session, perspective)
            insights.extend(perspective_insights)

        insights = self._deduplicate_insights(insights)

        for insight in insights:
            self._insight_library[insight.insight_id] = insight
            self._total_insights += 1

        session.insights = insights
        session.overall_score = self._compute_overall_score(session)
        session.summary = self._generate_summary(session)
        session.improvement_plan = self._generate_improvement_plan(session)

        logger.info(
            f"Self-reflection complete: {len(insights)} insights, "
            f"overall score {session.overall_score:.2f}"
        )
        return insights

    def get_session(self, session_id: str) -> SelfReflectionSession | None:
        return self._sessions.get(session_id)

    def apply_insight(self, insight_id: str) -> bool:
        """Mark an insight as applied."""
        insight = self._insight_library.get(insight_id)
        if not insight:
            return False
        insight.applied = True
        insight.impact_score = min(1.0, insight.impact_score + 0.2)
        return True

    def get_improvement_history(self, agent_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get improvement history for an agent."""
        sessions = [
            {
                "session_id": s.session_id,
                "depth": s.depth.value,
                "actions_count": len(s.actions),
                "insights_count": len(s.insights),
                "overall_score": s.overall_score,
                "summary": s.summary,
                "created_at": s.created_at,
            }
            for s in self._sessions.values()
            if s.agent_id == agent_id
        ]
        sessions.sort(key=lambda s: s["created_at"], reverse=True)
        return sessions[:limit]

    def get_top_insights(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most impactful unapplied insights."""
        unapplied = [i for i in self._insight_library.values() if not i.applied]
        unapplied.sort(key=lambda i: (i.priority == "critical", i.impact_score), reverse=True)
        return [
            {
                "insight_id": i.insight_id,
                "type": i.insight_type.value,
                "content": i.content,
                "priority": i.priority.value,
                "confidence": i.confidence,
                "suggested_action": i.suggested_action,
                "impact_score": i.impact_score,
            }
            for i in unapplied[:limit]
        ]

    def get_stats(self) -> dict[str, Any]:
        total_actions = len(self._action_history)
        success_rate = sum(
            1 for a in self._action_history if a.outcome == "success"
        ) / max(total_actions, 1)

        return {
            "total_sessions": self._total_sessions,
            "total_insights": self._total_insights,
            "total_actions_recorded": total_actions,
            "insights_applied": sum(1 for i in self._insight_library.values() if i.applied),
            "insights_pending": sum(1 for i in self._insight_library.values() if not i.applied),
            "action_success_rate": round(success_rate, 3),
            "top_patterns": dict(
                sorted(self._pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }

    def _reflect_from_perspective(
        self,
        session: SelfReflectionSession,
        perspective: ReflectionPerspective,
    ) -> list[SelfReflectionInsight]:
        """Generate insights from a specific perspective."""
        insights: list[SelfReflectionInsight] = []

        if perspective == ReflectionPerspective.EFFICIENCY:
            insights = self._analyze_efficiency(session)
        elif perspective == ReflectionPerspective.QUALITY:
            insights = self._analyze_quality(session)
        elif perspective == ReflectionPerspective.CORRECTNESS:
            insights = self._analyze_correctness(session)
        elif perspective == ReflectionPerspective.CREATIVITY:
            insights = self._analyze_creativity(session)
        elif perspective == ReflectionPerspective.COMMUNICATION:
            insights = self._analyze_communication(session)
        elif perspective == ReflectionPerspective.ETHICS:
            insights = self._analyze_ethics(session)
        elif perspective == ReflectionPerspective.USER_SATISFACTION:
            insights = self._analyze_user_satisfaction(session)
        elif perspective == ReflectionPerspective.RESOURCE_USAGE:
            insights = self._analyze_resource_usage(session)

        return insights

    def _analyze_efficiency(self, session: SelfReflectionSession) -> list[SelfReflectionInsight]:
        insights: list[SelfReflectionInsight] = []
        if not session.actions:
            return insights

        durations = [a.duration_ms for a in session.actions if a.duration_ms > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
            slow_actions = [a for a in session.actions if a.duration_ms > avg_duration * 2]
            if slow_actions:
                insights.append(SelfReflectionInsight(
                    insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                    insight_type=InsightType.PATTERN,
                    content=f"Slow execution detected: {len(slow_actions)} actions exceed 2x average duration",
                    perspective=ReflectionPerspective.EFFICIENCY,
                    priority=ImprovementPriority.MEDIUM,
                    confidence=0.8,
                    source_actions=[a.action_id for a in slow_actions],
                    suggested_action="Consider caching, batching, or optimizing slow operations",
                ))

        tokens = [a.tokens_used for a in session.actions if a.tokens_used > 0]
        if tokens:
            avg_tokens = sum(tokens) / len(tokens)
            high_token = [a for a in session.actions if a.tokens_used > avg_tokens * 1.5]
            if high_token:
                insights.append(SelfReflectionInsight(
                    insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                    insight_type=InsightType.HEURISTIC,
                    content=f"High token usage: {len(high_token)} actions use 1.5x+ average tokens",
                    perspective=ReflectionPerspective.EFFICIENCY,
                    priority=ImprovementPriority.LOW,
                    confidence=0.7,
                    source_actions=[a.action_id for a in high_token],
                    suggested_action="Review prompt templates for conciseness",
                ))

        return insights

    def _analyze_quality(self, session: SelfReflectionSession) -> list[SelfReflectionInsight]:
        insights: list[SelfReflectionInsight] = []
        if not session.actions:
            return insights

        failures = [a for a in session.actions if a.outcome == "failure"]
        if failures:
            error_types = defaultdict(int)
            for a in failures:
                for e in a.errors:
                    error_types[e[:50]] += 1

            top_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:3]
            for error_msg, count in top_errors:
                insights.append(SelfReflectionInsight(
                    insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                    insight_type=InsightType.WARNING,
                    content=f"Recurring error ({count}x): '{error_msg}'",
                    perspective=ReflectionPerspective.QUALITY,
                    priority=ImprovementPriority.HIGH,
                    confidence=0.9,
                    source_actions=[a.action_id for a in failures],
                    suggested_action="Add error handling or validation for this case",
                ))

        return insights

    def _analyze_correctness(self, session: SelfReflectionSession) -> list[SelfReflectionInsight]:
        insights: list[SelfReflectionInsight] = []
        if not session.actions:
            return insights

        low_confidence = [a for a in session.actions if a.confidence < 0.4]
        if low_confidence:
            insights.append(SelfReflectionInsight(
                insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                insight_type=InsightType.WARNING,
                content=f"Low confidence in {len(low_confidence)} actions",
                perspective=ReflectionPerspective.CORRECTNESS,
                priority=ImprovementPriority.MEDIUM,
                confidence=0.8,
                source_actions=[a.action_id for a in low_confidence],
                suggested_action="Request clarification or gather more context before acting",
            ))

        return insights

    def _analyze_creativity(self, session: SelfReflectionSession) -> list[SelfReflectionInsight]:
        insights: list[SelfReflectionInsight] = []
        tool_variety = len(set(
            tool for a in session.actions for tool in a.tools_called
        ))
        if tool_variety <= 1 and session.actions:
            insights.append(SelfReflectionInsight(
                insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                insight_type=InsightType.OPPORTUNITY,
                content="Limited tool variety detected - consider exploring alternative approaches",
                perspective=ReflectionPerspective.CREATIVITY,
                priority=ImprovementPriority.LOW,
                confidence=0.6,
                suggested_action="Experiment with different tools and methods",
            ))
        return insights

    def _analyze_communication(self, session: SelfReflectionSession) -> list[SelfReflectionInsight]:
        return []

    def _analyze_ethics(self, session: SelfReflectionSession) -> list[SelfReflectionInsight]:
        return []

    def _analyze_user_satisfaction(self, session: SelfReflectionSession) -> list[SelfReflectionInsight]:
        return []

    def _analyze_resource_usage(self, session: SelfReflectionSession) -> list[SelfReflectionInsight]:
        insights: list[SelfReflectionInsight] = []
        if not session.actions:
            return insights

        total_tokens = sum(a.tokens_used for a in session.actions)
        if total_tokens > 10000:
            insights.append(SelfReflectionInsight(
                insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                insight_type=InsightType.HEURISTIC,
                content=f"High total token usage: {total_tokens} tokens across {len(session.actions)} actions",
                perspective=ReflectionPerspective.RESOURCE_USAGE,
                priority=ImprovementPriority.MEDIUM,
                confidence=0.8,
                suggested_action="Consider implementing response caching",
            ))

        return insights

    def _deduplicate_insights(self, insights: list[SelfReflectionInsight]) -> list[SelfReflectionInsight]:
        seen: set[str] = set()
        unique: list[SelfReflectionInsight] = []

        for ins in insights:
            key = f"{ins.insight_type.value}:{ins.content[:80]}"
            if key not in seen:
                seen.add(key)
                unique.append(ins)
            else:
                for existing in unique:
                    existing_key = f"{existing.insight_type.value}:{existing.content[:80]}"
                    if existing_key == key:
                        existing.source_actions.extend(ins.source_actions)
                        existing.confidence = max(existing.confidence, ins.confidence)
                        break

        return unique[:self.MAX_INSIGHTS_PER_SESSION]

    def _compute_overall_score(self, session: SelfReflectionSession) -> float:
        if not session.actions:
            return 0.5

        scores: list[float] = []
        success_count = sum(1 for a in session.actions if a.outcome == "success")
        scores.append(success_count / len(session.actions))

        confidences = [a.confidence for a in session.actions if a.confidence > 0]
        if confidences:
            scores.append(sum(confidences) / len(confidences))

        return round(sum(scores) / len(scores), 3) if scores else 0.5

    def _generate_summary(self, session: SelfReflectionSession) -> str:
        total = len(session.actions)
        success = sum(1 for a in session.actions if a.outcome == "success")
        parts = [f"Analyzed {total} actions ({success}/{total} successful)"]

        if session.insights:
            critical = sum(1 for i in session.insights if i.priority == ImprovementPriority.CRITICAL)
            high = sum(1 for i in session.insights if i.priority == ImprovementPriority.HIGH)
            parts.append(f"Generated {len(session.insights)} insights ({critical} critical, {high} high priority)")

        parts.append(f"Overall score: {session.overall_score:.2%}")
        return " | ".join(parts)

    def _generate_improvement_plan(self, session: SelfReflectionSession) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = []

        sorted_insights = sorted(
            session.insights,
            key=lambda i: (
                ["critical", "high", "medium", "low", "observation"].index(
                    i.priority.value if i.priority.value in ["critical", "high", "medium", "low", "observation"] else "low"
                ),
                i.confidence,
            ),
        )

        for ins in sorted_insights[:10]:
            if ins.suggested_action:
                plan.append({
                    "insight_id": ins.insight_id,
                    "action": ins.suggested_action,
                    "priority": ins.priority.value,
                    "confidence": ins.confidence,
                })

        return plan


# ── Global Singleton ─────────────────────────────────────────────

self_reflection_engine = SelfReflectionEngine()