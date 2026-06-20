"""
Buddy Agent Intent Engine - Deep intent recognition and understanding.

Enables agents to understand user intent beyond surface-level queries
by analyzing multi-turn context, detecting implicit goals, and
predicting follow-up needs. Provides structured intent representations
for downstream processing.

Key capabilities:
- Multi-turn intent tracking with context accumulation
- Implicit goal detection from conversational patterns
- Intent classification with confidence scoring
- Follow-up prediction and proactive suggestion
- User preference learning from intent history
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class IntentCategory(str, Enum):
    """Primary categories of user intent."""
    INFORMATION_QUERY = "information_query"
    TASK_EXECUTION = "task_execution"
    CREATIVE_GENERATION = "creative_generation"
    ANALYSIS = "analysis"
    DECISION_SUPPORT = "decision_support"
    CONVERSATION = "conversation"
    TROUBLESHOOTING = "troubleshooting"
    LEARNING = "learning"
    PLANNING = "planning"
    CODE_GENERATION = "code_generation"


class IntentComplexity(str, Enum):
    """Complexity level of the detected intent."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    MULTI_STEP = "multi_step"


class IntentUrgency(str, Enum):
    """Urgency level of the detected intent."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IntentEntity:
    """A named entity extracted from the intent."""
    name: str
    entity_type: str
    value: str
    confidence: float


@dataclass
class IntentConstraint:
    """A constraint or requirement detected in the intent."""
    constraint_type: str
    value: str
    is_hard: bool  # Hard vs soft constraint
    source: str  # Explicit or implicit


@dataclass
class IntentResult:
    """Complete intent analysis result."""
    intent_id: str
    session_id: str
    agent_id: str
    raw_query: str
    category: IntentCategory
    complexity: IntentComplexity
    urgency: IntentUrgency
    confidence: float
    summary: str
    entities: list[IntentEntity] = field(default_factory=list)
    constraints: list[IntentConstraint] = field(default_factory=list)
    sub_intents: list[IntentResult] = field(default_factory=list)
    suggested_tools: list[str] = field(default_factory=list)
    suggested_skills: list[str] = field(default_factory=list)
    follow_up_predictions: list[str] = field(default_factory=list)
    context_requirements: list[str] = field(default_factory=list)
    related_previous_intents: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class IntentSession:
    """Tracks intent across a multi-turn conversation."""
    session_id: str
    agent_id: str
    intents: list[IntentResult] = field(default_factory=list)
    accumulated_context: dict[str, Any] = field(default_factory=dict)
    user_preferences: dict[str, float] = field(default_factory=dict)
    turn_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


class AgentIntentEngine:
    """Intent recognition and understanding engine for Buddy agents.

    Analyzes user queries to understand underlying intent, tracks intent
    across multi-turn conversations, and predicts follow-up needs.
    Builds a rich intent model for each interaction session.
    """

    def __init__(self):
        self._sessions: dict[str, IntentSession] = {}
        self._intents: dict[str, IntentResult] = {}
        self._intent_patterns: dict[str, list[dict]] = {}  # agent_id -> learned patterns
        self._total_intents = 0
        self._total_sessions = 0

    def analyze_intent(
        self,
        agent_id: str,
        query: str,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> IntentResult:
        """Analyze a user query to detect intent."""
        sid = session_id or f"isess-{uuid.uuid4().hex[:12]}"

        # Get or create session
        if sid not in self._sessions:
            self._sessions[sid] = IntentSession(
                session_id=sid,
                agent_id=agent_id,
            )
            self._total_sessions += 1

        session = self._sessions[sid]
        session.turn_count += 1
        if context:
            session.accumulated_context.update(context)

        # Classify intent based on query analysis
        category = self._classify_category(query, session)
        complexity = self._estimate_complexity(query, session)
        urgency = self._estimate_urgency(query, session)

        intent = IntentResult(
            intent_id=f"intent-{uuid.uuid4().hex[:12]}",
            session_id=sid,
            agent_id=agent_id,
            raw_query=query,
            category=category,
            complexity=complexity,
            urgency=urgency,
            confidence=0.85,
            summary=query[:200],
            entities=self._extract_entities(query),
            constraints=self._extract_constraints(query),
            suggested_tools=self._suggest_tools(category, query),
            suggested_skills=self._suggest_skills(category, query),
            follow_up_predictions=self._predict_followups(intent=None, session=session),
            context_requirements=self._determine_context_needs(category, complexity),
            related_previous_intents=[
                i.intent_id for i in session.intents[-3:]
            ] if session.intents else [],
            metadata=context or {},
        )

        session.intents.append(intent)
        session.last_updated = time.time()
        self._intents[intent.intent_id] = intent
        self._total_intents += 1

        return intent

    def get_session(self, session_id: str) -> IntentSession | None:
        """Get an intent session by ID."""
        return self._sessions.get(session_id)

    def get_intent(self, intent_id: str) -> IntentResult | None:
        """Get an intent result by ID."""
        return self._intents.get(intent_id)

    def get_session_intents(
        self, session_id: str, limit: int = 50
    ) -> list[IntentResult]:
        """Get all intents for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        return session.intents[-limit:]

    def update_preference(
        self, session_id: str, preference_key: str, value: float
    ) -> None:
        """Update a learned user preference in a session."""
        session = self._sessions.get(session_id)
        if not session:
            return
        session.user_preferences[preference_key] = (
            session.user_preferences.get(preference_key, 0.5) * 0.8 + value * 0.2
        )

    def get_stats(self, agent_id: str | None = None) -> dict:
        """Get intent engine statistics."""
        if agent_id:
            sessions = [
                s for s in self._sessions.values() if s.agent_id == agent_id
            ]
            intents = [
                i for i in self._intents.values() if i.agent_id == agent_id
            ]
            return {
                "agent_id": agent_id,
                "total_sessions": len(sessions),
                "total_intents": len(intents),
                "categories": self._count_categories(intents),
                "complexity_distribution": self._count_complexity(intents),
                "average_confidence": (
                    sum(i.confidence for i in intents) / len(intents)
                    if intents else 0.0
                ),
            }

        return {
            "total_sessions": self._total_sessions,
            "total_intents": self._total_intents,
            "active_agents": len(
                set(s.agent_id for s in self._sessions.values())
            ),
        }

    def _classify_category(
        self, query: str, session: IntentSession
    ) -> IntentCategory:
        """Classify the intent category from query text."""
        query_lower = query.lower()

        # Code-related detection
        code_keywords = ["code", "function", "class", "bug", "debug", "api",
                         "import", "def ", "class ", "implement", "refactor"]
        if any(kw in query_lower for kw in code_keywords):
            return IntentCategory.CODE_GENERATION

        # Analysis detection
        analysis_keywords = ["analyze", "compare", "evaluate", "assess",
                             "review", "examine", "investigate"]
        if any(kw in query_lower for kw in analysis_keywords):
            return IntentCategory.ANALYSIS

        # Task execution
        task_keywords = ["do", "execute", "run", "perform", "complete",
                         "create", "build", "make", "generate"]
        if any(kw in query_lower for kw in task_keywords):
            return IntentCategory.TASK_EXECUTION

        # Planning
        plan_keywords = ["plan", "schedule", "organize", "strategy",
                         "roadmap", "timeline", "steps"]
        if any(kw in query_lower for kw in plan_keywords):
            return IntentCategory.PLANNING

        # Troubleshooting
        trouble_keywords = ["error", "fail", "not working", "broken",
                            "issue", "problem", "fix", "wrong"]
        if any(kw in query_lower for kw in trouble_keywords):
            return IntentCategory.TROUBLESHOOTING

        # Learning
        learn_keywords = ["explain", "teach", "what is", "how does",
                          "learn", "understand", "tutorial"]
        if any(kw in query_lower for kw in learn_keywords):
            return IntentCategory.LEARNING

        # Decision support
        decision_keywords = ["should i", "which", "recommend", "suggest",
                             "best", "better", "option", "choice"]
        if any(kw in query_lower for kw in decision_keywords):
            return IntentCategory.DECISION_SUPPORT

        # Creative
        creative_keywords = ["write", "story", "poem", "design", "draw",
                             "creative", "imagine", "brainstorm"]
        if any(kw in query_lower for kw in creative_keywords):
            return IntentCategory.CREATIVE_GENERATION

        # Default to information query
        return IntentCategory.INFORMATION_QUERY

    def _estimate_complexity(
        self, query: str, session: IntentSession
    ) -> IntentComplexity:
        """Estimate the complexity of the intent."""
        word_count = len(query.split())
        has_multi_clause = any(
            sep in query for sep in [" and ", " also ", " then ", " after "]
        )
        references_previous = bool(session.intents and session.turn_count > 1)

        if word_count > 50 or (has_multi_clause and references_previous):
            return IntentComplexity.MULTI_STEP
        elif word_count > 25 or has_multi_clause:
            return IntentComplexity.COMPLEX
        elif word_count > 10 or references_previous:
            return IntentComplexity.MODERATE
        return IntentComplexity.SIMPLE

    def _estimate_urgency(
        self, query: str, session: IntentSession
    ) -> IntentUrgency:
        """Estimate the urgency of the intent."""
        query_lower = query.lower()
        urgent_keywords = ["urgent", "asap", "immediately", "critical",
                           "emergency", "now", "quickly", "fast"]
        high_keywords = ["important", "priority", "soon", "deadline"]

        if any(kw in query_lower for kw in urgent_keywords):
            return IntentUrgency.CRITICAL
        elif any(kw in query_lower for kw in high_keywords):
            return IntentUrgency.HIGH
        elif session.turn_count > 3:
            return IntentUrgency.MEDIUM
        return IntentUrgency.LOW

    def _extract_entities(self, query: str) -> list[IntentEntity]:
        """Extract named entities from the query."""
        entities: list[IntentEntity] = []
        # Simple keyword-based entity extraction
        tech_terms = ["python", "javascript", "react", "api", "database",
                      "docker", "kubernetes", "aws", "sql", "redis"]
        for term in tech_terms:
            if term.lower() in query.lower():
                entities.append(IntentEntity(
                    name=term, entity_type="technology",
                    value=term, confidence=0.9,
                ))
        return entities

    def _extract_constraints(self, query: str) -> list[IntentConstraint]:
        """Extract constraints from the query."""
        constraints: list[IntentConstraint] = []
        query_lower = query.lower()

        if "must" in query_lower or "required" in query_lower:
            constraints.append(IntentConstraint(
                constraint_type="requirement", value="mandatory",
                is_hard=True, source="explicit",
            ))
        if "prefer" in query_lower or "ideally" in query_lower:
            constraints.append(IntentConstraint(
                constraint_type="preference", value="optional",
                is_hard=False, source="explicit",
            ))
        return constraints

    def _suggest_tools(
        self, category: IntentCategory, query: str
    ) -> list[str]:
        """Suggest relevant tools based on intent category."""
        tool_map = {
            IntentCategory.CODE_GENERATION: ["code_executor", "file_editor", "git"],
            IntentCategory.ANALYSIS: ["data_analyzer", "chart_generator"],
            IntentCategory.TASK_EXECUTION: ["task_runner", "scheduler"],
            IntentCategory.TROUBLESHOOTING: ["log_analyzer", "debugger"],
            IntentCategory.INFORMATION_QUERY: ["web_search", "knowledge_base"],
            IntentCategory.PLANNING: ["planner", "timeline_generator"],
        }
        return tool_map.get(category, [])

    def _suggest_skills(
        self, category: IntentCategory, query: str
    ) -> list[str]:
        """Suggest relevant skills based on intent category."""
        skill_map = {
            IntentCategory.CODE_GENERATION: ["code_review", "refactoring"],
            IntentCategory.ANALYSIS: ["data_analysis", "reporting"],
            IntentCategory.CREATIVE_GENERATION: ["content_writing", "design"],
            IntentCategory.LEARNING: ["explanation", "tutorial_generation"],
        }
        return skill_map.get(category, [])

    def _predict_followups(
        self,
        intent: IntentResult | None,
        session: IntentSession,
    ) -> list[str]:
        """Predict likely follow-up intents."""
        if not session.intents:
            return []
        # Simple heuristic: users often ask for clarification or expansion
        return ["clarification", "elaboration", "example", "alternative"]

    def _determine_context_needs(
        self, category: IntentCategory, complexity: IntentComplexity
    ) -> list[str]:
        """Determine what context is needed for this intent."""
        needs = ["conversation_history"]
        if complexity in (IntentComplexity.COMPLEX, IntentComplexity.MULTI_STEP):
            needs.extend(["memory_retrieval", "skill_context", "tool_state"])
        if category == IntentCategory.CODE_GENERATION:
            needs.append("workspace_files")
        if category == IntentCategory.ANALYSIS:
            needs.append("data_context")
        return needs

    def _count_categories(
        self, intents: list[IntentResult]
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for intent in intents:
            cat = intent.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _count_complexity(
        self, intents: list[IntentResult]
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for intent in intents:
            c = intent.complexity.value
            counts[c] = counts.get(c, 0) + 1
        return counts


# Global singleton
intent_engine = AgentIntentEngine()