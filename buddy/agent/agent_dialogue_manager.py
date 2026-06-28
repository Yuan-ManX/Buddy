"""Buddy Agent Dialogue Manager — multi-turn conversation strategy and state tracking.

The Dialogue Management system governs the agent's conversational behavior across
multi-turn interactions. It maintains a structured model of the dialogue state,
tracks turn-taking, manages topics, and applies strategy rules to guide the
conversation flow toward user goals.

Core capabilities:
  - Dialogue State Tracking: finite-state model of conversation progress
  - Turn Management: structured logging of user/agent/system/tool turns
  - Topic Management: introduction, activation, pausing, and completion of topics
  - Strategy Selection: pluggable conversational strategies (Socratic, guided, etc.)
  - Transition Rules: configurable state transitions driven by dialogue acts
  - Clarification Tracking: pending questions and their resolutions
  - Information Collection: structured key/value gathering during elicitation
  - Engagement and Confidence: continuous signals of conversation quality
  - Session Summaries: lightweight roll-ups of completed or active sessions
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.dialogue_manager")


# ═══════════════════════════════════════════════════════════
# Enums and Types
# ═══════════════════════════════════════════════════════════

class DialogueState(str, Enum):
    """High-level states of a managed dialogue."""
    GREETING = "greeting"
    INFORMATION_GATHERING = "information_gathering"
    CLARIFICATION = "clarification"
    PROBLEM_SOLVING = "problem_solving"
    EXECUTION = "execution"
    CONFIRMATION = "confirmation"
    FEEDBACK = "feedback"
    CLOSING = "closing"
    ERROR_RECOVERY = "error_recovery"


class DialogueAct(str, Enum):
    """Speech-act style labels for individual dialogue turns."""
    ASSERT = "assert"
    INFORM = "inform"
    REQUEST = "request"
    QUESTION = "question"
    CONFIRM = "confirm"
    ACKNOWLEDGE = "acknowledge"
    REJECT = "reject"
    PROMISE = "promise"
    APOLOGIZE = "apologize"
    SUGGEST = "suggest"
    CLARIFY = "clarify"
    SUMMARIZE = "summarize"
    PROBE = "probe"
    REDIRECT = "redirect"


class TurnType(str, Enum):
    """Who produced a given turn in the dialogue."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationPhase(str, Enum):
    """Coarse-grained phase of the conversation arc."""
    OPENING = "opening"
    EXPLORATION = "exploration"
    ELICITATION = "elicitation"
    DELIBERATION = "deliberation"
    RESOLUTION = "resolution"
    WRAP_UP = "wrap_up"


class StrategyType(str, Enum):
    """Conversational strategies the agent may follow."""
    DIRECT_ANSWER = "direct_answer"
    Socratic = "socratic"
    GUIDED_DISCOVERY = "guided_discovery"
    STEP_BY_STEP = "step_by_step"
    BRAINSTORM = "brainstorm"
    DEVILS_ADVOCATE = "devils_advocate"
    REFLECTIVE = "reflective"
    PROACTIVE = "proactive"


class TopicStatus(str, Enum):
    """Lifecycle status of a topic within a session."""
    INTRODUCED = "introduced"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    REVISITED = "revisited"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class Topic:
    """A conversational topic tracked within a dialogue session."""
    topic_id: str = field(default_factory=lambda: f"topic-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    status: TopicStatus = TopicStatus.INTRODUCED
    introduced_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    relevance_score: float = 0.5
    related_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "introduced_at": self.introduced_at,
            "last_active": self.last_active,
            "relevance_score": self.relevance_score,
            "related_topics": self.related_topics,
        }


@dataclass
class DialogueTurn:
    """A single turn recorded in the dialogue history."""
    turn_id: str = field(default_factory=lambda: f"turn-{uuid.uuid4().hex[:12]}")
    session_id: str = ""
    turn_type: TurnType = TurnType.USER
    dialogue_act: DialogueAct = DialogueAct.INFORM
    content: str = ""
    speaker: str = ""
    timestamp: float = field(default_factory=time.time)
    state_before: DialogueState = DialogueState.GREETING
    state_after: DialogueState = DialogueState.GREETING
    topics: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "turn_type": self.turn_type.value,
            "dialogue_act": self.dialogue_act.value,
            "content": self.content,
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "state_before": self.state_before.value,
            "state_after": self.state_after.value,
            "topics": self.topics,
            "metadata": self.metadata,
        }


@dataclass
class DialogueContext:
    """Live state for a single dialogue session."""
    session_id: str = ""
    current_state: DialogueState = DialogueState.GREETING
    phase: ConversationPhase = ConversationPhase.OPENING
    strategy: StrategyType = StrategyType.DIRECT_ANSWER
    active_topics: list[str] = field(default_factory=list)
    turn_count: int = 0
    user_engagement: float = 0.5
    agent_confidence: float = 0.5
    pending_clarifications: list[str] = field(default_factory=list)
    collected_info: dict[str, Any] = field(default_factory=dict)
    session_goals: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.value,
            "phase": self.phase.value,
            "strategy": self.strategy.value,
            "active_topics": self.active_topics,
            "turn_count": self.turn_count,
            "user_engagement": self.user_engagement,
            "agent_confidence": self.agent_confidence,
            "pending_clarifications": self.pending_clarifications,
            "collected_info": self.collected_info,
            "session_goals": self.session_goals,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class TransitionRule:
    """A rule describing when and where the dialogue may transition."""
    rule_id: str = field(default_factory=lambda: f"rule-{uuid.uuid4().hex[:8]}")
    from_state: DialogueState = DialogueState.GREETING
    to_state: DialogueState = DialogueState.GREETING
    trigger_act: DialogueAct = DialogueAct.INFORM
    condition: str = ""
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "trigger_act": self.trigger_act.value,
            "condition": self.condition,
            "priority": self.priority,
        }


@dataclass
class DialogueManagerStats:
    """Aggregate statistics across the dialogue manager."""
    total_sessions: int = 0
    active_sessions: int = 0
    total_turns: int = 0
    avg_session_length: float = 0.0
    state_distribution: dict[str, int] = field(default_factory=dict)
    strategy_distribution: dict[str, int] = field(default_factory=dict)
    avg_engagement: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "total_turns": self.total_turns,
            "avg_session_length": self.avg_session_length,
            "state_distribution": self.state_distribution,
            "strategy_distribution": self.strategy_distribution,
            "avg_engagement": self.avg_engagement,
        }


# ═══════════════════════════════════════════════════════════
# Dialogue Manager Implementation
# ═══════════════════════════════════════════════════════════

class AgentDialogueManager:
    """Manages multi-turn dialogue state, turn-taking, and conversation strategy.

    The manager is thread-safe and intended to be used as a process-wide singleton
    via `get_dialogue_manager()`. Each session maintains its own `DialogueContext`
    and turn history; transition rules are shared across sessions so that dialogue
    policy can be defined once and applied uniformly.
    """

    MAX_SESSIONS = 200
    MAX_TURNS_PER_SESSION = 500
    MAX_TURNS_LOG = 10000

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, DialogueContext] = {}
        self._turns: dict[str, list[DialogueTurn]] = {}
        self._topics: dict[str, dict[str, Topic]] = {}
        self._rules: list[TransitionRule] = []
        self._session_meta: dict[str, dict[str, Any]] = {}
        self._init_default_rules()
        logger.info("AgentDialogueManager initialized")

    # ── Session Lifecycle ────────────────────────────────

    def create_session(
        self,
        session_id: str,
        agent_id: str = "",
        user_id: str = "",
        strategy: StrategyType = StrategyType.DIRECT_ANSWER,
        session_goals: list[str] | None = None,
    ) -> DialogueContext:
        """Create a new dialogue session with the given strategy and goals."""
        with self._lock:
            if session_id in self._sessions:
                logger.warning("Session %s already exists; returning existing", session_id)
                return self._sessions[session_id]

            # Evict oldest session if at capacity
            if len(self._sessions) >= self.MAX_SESSIONS:
                self._evict_oldest_session()

            now = time.time()
            context = DialogueContext(
                session_id=session_id,
                current_state=DialogueState.GREETING,
                phase=ConversationPhase.OPENING,
                strategy=strategy,
                session_goals=list(session_goals) if session_goals else [],
                created_at=now,
                updated_at=now,
            )
            self._sessions[session_id] = context
            self._turns[session_id] = []
            self._topics[session_id] = {}
            self._session_meta[session_id] = {
                "agent_id": agent_id,
                "user_id": user_id,
                "ended": False,
            }
            logger.info(
                "Created dialogue session %s (strategy=%s, goals=%d)",
                session_id,
                strategy.value,
                len(context.session_goals),
            )
            return context

    def get_session(self, session_id: str) -> DialogueContext | None:
        """Retrieve a dialogue session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> bool:
        """Mark a session as ended. Returns True if the session existed."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return False
            context.current_state = DialogueState.CLOSING
            context.phase = ConversationPhase.WRAP_UP
            context.updated_at = time.time()
            meta = self._session_meta.get(session_id, {})
            meta["ended"] = True
            meta["ended_at"] = context.updated_at
            self._session_meta[session_id] = meta
            logger.info("Ended dialogue session %s", session_id)
            return True

    def list_sessions(self, active_only: bool = False) -> list[DialogueContext]:
        """List dialogue sessions, optionally filtered to active ones."""
        with self._lock:
            contexts = list(self._sessions.values())
        if active_only:
            contexts = [
                c for c in contexts
                if not self._session_meta.get(c.session_id, {}).get("ended", False)
            ]
        contexts.sort(key=lambda c: c.updated_at, reverse=True)
        return contexts

    # ── Turn Management ──────────────────────────────────

    def record_turn(
        self,
        session_id: str,
        turn_type: TurnType,
        dialogue_act: DialogueAct,
        content: str,
        speaker: str = "",
        topics: list[str] | None = None,
    ) -> DialogueTurn:
        """Record a single turn in the dialogue history.

        The turn captures the state before and after it was recorded, providing
        an audit trail of how the dialogue evolved. Returns the created turn.
        Raises ValueError if the session does not exist.
        """
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                raise ValueError(f"Session not found: {session_id}")

            state_before = context.current_state
            turn = DialogueTurn(
                session_id=session_id,
                turn_type=turn_type,
                dialogue_act=dialogue_act,
                content=content,
                speaker=speaker or turn_type.value,
                timestamp=time.time(),
                state_before=state_before,
                state_after=state_before,
                topics=list(topics) if topics else [],
            )

            turns = self._turns.setdefault(session_id, [])
            turns.append(turn)

            # Enforce per-session turn cap by trimming oldest entries
            if len(turns) > self.MAX_TURNS_PER_SESSION:
                self._turns[session_id] = turns[-self.MAX_TURNS_PER_SESSION:]

            # Enforce global turn log cap
            total_turns = sum(len(t) for t in self._turns.values())
            if total_turns > self.MAX_TURNS_LOG:
                self._trim_oldest_turns_globally(total_turns - self.MAX_TURNS_LOG)

            context.turn_count = len(self._turns[session_id])
            context.updated_at = turn.timestamp

            # Refresh topic activity timestamps
            topic_map = self._topics.setdefault(session_id, {})
            for topic_id in turn.topics:
                topic = topic_map.get(topic_id)
                if topic:
                    topic.last_active = turn.timestamp
                    if topic.status == TopicStatus.INTRODUCED:
                        topic.status = TopicStatus.ACTIVE

            logger.debug(
                "Recorded turn %s in session %s (act=%s, type=%s)",
                turn.turn_id,
                session_id,
                dialogue_act.value,
                turn_type.value,
            )
            return turn

    def get_turns(self, session_id: str, limit: int = 50) -> list[DialogueTurn]:
        """Return the most recent turns for a session, newest last."""
        with self._lock:
            turns = self._turns.get(session_id, [])
            if limit <= 0:
                return list(turns)
            return list(turns[-limit:])

    # ── State Transitions ────────────────────────────────

    def get_current_state(self, session_id: str) -> DialogueState | None:
        """Return the current dialogue state for a session, or None."""
        with self._lock:
            context = self._sessions.get(session_id)
            return context.current_state if context else None

    def transition_state(
        self,
        session_id: str,
        trigger_act: DialogueAct,
        context_info: str = "",
    ) -> DialogueState:
        """Advance the dialogue state based on a trigger act.

        Looks up matching transition rules for the current state and the supplied
        dialogue act, sorts candidates by priority (descending), and applies the
        highest-priority rule. If no rule matches, the current state is retained.
        Returns the resulting (possibly unchanged) dialogue state.
        """
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                logger.warning("transition_state: session not found: %s", session_id)
                return DialogueState.GREETING

            current = context.current_state

            # Collect matching rules
            candidates = [
                rule for rule in self._rules
                if rule.from_state == current and rule.trigger_act == trigger_act
            ]

            # Sort by priority descending; ties broken by rule_id for stability
            candidates.sort(key=lambda r: (-r.priority, r.rule_id))

            if candidates:
                target = candidates[0].to_state
                logger.debug(
                    "State transition %s -> %s (act=%s, info=%r, rule=%s)",
                    current.value,
                    target.value,
                    trigger_act.value,
                    context_info,
                    candidates[0].rule_id,
                )
                context.current_state = target
            else:
                logger.debug(
                    "No transition rule for state=%s act=%s; retaining state",
                    current.value,
                    trigger_act.value,
                )

            context.updated_at = time.time()
            return context.current_state

    def register_transition_rule(
        self,
        from_state: DialogueState,
        to_state: DialogueState,
        trigger_act: DialogueAct,
        condition: str = "",
        priority: int = 0,
    ) -> TransitionRule:
        """Register a new transition rule. Higher priority rules win ties."""
        with self._lock:
            rule = TransitionRule(
                from_state=from_state,
                to_state=to_state,
                trigger_act=trigger_act,
                condition=condition,
                priority=priority,
            )
            self._rules.append(rule)
            logger.debug(
                "Registered transition rule %s: %s -> %s on %s (priority=%d)",
                rule.rule_id,
                from_state.value,
                to_state.value,
                trigger_act.value,
                priority,
            )
            return rule

    # ── Strategy Management ──────────────────────────────

    def set_strategy(self, session_id: str, strategy: StrategyType) -> DialogueContext | None:
        """Set the conversational strategy for a session."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return None
            context.strategy = strategy
            context.updated_at = time.time()
            logger.info("Session %s strategy set to %s", session_id, strategy.value)
            return context

    def get_strategy(self, session_id: str) -> StrategyType | None:
        """Return the current strategy for a session, or None."""
        with self._lock:
            context = self._sessions.get(session_id)
            return context.strategy if context else None

    # ── Topic Management ─────────────────────────────────

    def introduce_topic(
        self,
        session_id: str,
        name: str,
        description: str = "",
        relevance_score: float = 0.5,
    ) -> Topic:
        """Introduce a new topic into the session's topic map.

        Returns the created Topic. Raises ValueError if the session is unknown.
        """
        with self._lock:
            if session_id not in self._sessions:
                raise ValueError(f"Session not found: {session_id}")

            topic = Topic(
                name=name,
                description=description,
                status=TopicStatus.INTRODUCED,
                relevance_score=max(0.0, min(1.0, relevance_score)),
            )
            topic_map = self._topics.setdefault(session_id, {})
            topic_map[topic.topic_id] = topic

            context = self._sessions[session_id]
            if topic.topic_id not in context.active_topics:
                context.active_topics.append(topic.topic_id)
            context.updated_at = time.time()

            logger.debug(
                "Introduced topic %s (%s) in session %s",
                topic.topic_id,
                name,
                session_id,
            )
            return topic

    def update_topic_status(
        self,
        session_id: str,
        topic_id: str,
        status: TopicStatus,
    ) -> Topic | None:
        """Update the status of a tracked topic. Returns the updated topic."""
        with self._lock:
            topic_map = self._topics.get(session_id)
            if not topic_map:
                return None
            topic = topic_map.get(topic_id)
            if not topic:
                return None

            topic.status = status
            topic.last_active = time.time()
            context = self._sessions.get(session_id)
            if context:
                if status in (TopicStatus.ACTIVE, TopicStatus.REVISITED, TopicStatus.INTRODUCED):
                    if topic_id not in context.active_topics:
                        context.active_topics.append(topic_id)
                elif status in (TopicStatus.COMPLETED, TopicStatus.ABANDONED):
                    if topic_id in context.active_topics:
                        context.active_topics.remove(topic_id)
                context.updated_at = topic.last_active
            return topic

    def get_active_topics(self, session_id: str) -> list[Topic]:
        """Return all topics currently marked active for a session."""
        with self._lock:
            topic_map = self._topics.get(session_id, {})
            return [
                topic for topic in topic_map.values()
                if topic.status in (TopicStatus.ACTIVE, TopicStatus.REVISITED, TopicStatus.INTRODUCED)
            ]

    # ── Clarification Tracking ───────────────────────────

    def add_pending_clarification(self, session_id: str, question: str) -> DialogueContext | None:
        """Record an open clarification question for a session."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return None
            if question and question not in context.pending_clarifications:
                context.pending_clarifications.append(question)
            context.updated_at = time.time()
            logger.debug(
                "Added pending clarification to %s (%d pending)",
                session_id,
                len(context.pending_clarifications),
            )
            return context

    def resolve_clarification(
        self,
        session_id: str,
        question: str,
        answer: str,
    ) -> DialogueContext | None:
        """Resolve a pending clarification, recording the answer in collected_info."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return None
            if question in context.pending_clarifications:
                context.pending_clarifications.remove(question)
            context.collected_info[f"clarification::{question}"] = answer
            context.updated_at = time.time()
            logger.debug(
                "Resolved clarification in %s (%d remaining)",
                session_id,
                len(context.pending_clarifications),
            )
            return context

    # ── Information Collection ───────────────────────────

    def collect_info(self, session_id: str, key: str, value: Any) -> DialogueContext | None:
        """Store a piece of information gathered during the dialogue."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return None
            context.collected_info[key] = value
            context.updated_at = time.time()
            return context

    def get_collected_info(self, session_id: str) -> dict:
        """Return a copy of all collected information for a session."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return {}
            return dict(context.collected_info)

    # ── Engagement and Confidence ────────────────────────

    def update_engagement(self, session_id: str, engagement_level: float) -> DialogueContext | None:
        """Update the user engagement signal (clamped to [0.0, 1.0])."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return None
            context.user_engagement = max(0.0, min(1.0, float(engagement_level)))
            context.updated_at = time.time()
            return context

    def update_confidence(self, session_id: str, confidence_level: float) -> DialogueContext | None:
        """Update the agent confidence signal (clamped to [0.0, 1.0])."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return None
            context.agent_confidence = max(0.0, min(1.0, float(confidence_level)))
            context.updated_at = time.time()
            return context

    # ── Next-Act Suggestion ──────────────────────────────

    def suggest_next_act(self, session_id: str) -> DialogueAct:
        """Suggest the next dialogue act the agent should produce.

        The suggestion is a heuristic mapping from the current dialogue state to
        an appropriate act. If the session is unknown, a safe default (INFORM)
        is returned. When clarifications are pending, QUESTION always wins.
        """
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return DialogueAct.INFORM

            # Pending clarifications always take precedence
            if context.pending_clarifications:
                return DialogueAct.QUESTION

            state = context.current_state

            # Map state to a sensible next act
            state_to_act: dict[DialogueState, DialogueAct] = {
                DialogueState.GREETING: DialogueAct.INFORM,
                DialogueState.INFORMATION_GATHERING: DialogueAct.QUESTION,
                DialogueState.CLARIFICATION: DialogueAct.QUESTION,
                DialogueState.PROBLEM_SOLVING: DialogueAct.SUGGEST,
                DialogueState.EXECUTION: DialogueAct.INFORM,
                DialogueState.CONFIRMATION: DialogueAct.CONFIRM,
                DialogueState.FEEDBACK: DialogueAct.ACKNOWLEDGE,
                DialogueState.CLOSING: DialogueAct.SUMMARIZE,
                DialogueState.ERROR_RECOVERY: DialogueAct.APOLOGIZE,
            }

            suggested = state_to_act.get(state, DialogueAct.INFORM)

            # Strategy-level refinements
            if context.strategy == StrategyType.Socratic and state == DialogueState.PROBLEM_SOLVING:
                suggested = DialogueAct.QUESTION
            elif context.strategy == StrategyType.STEP_BY_STEP and state == DialogueState.PROBLEM_SOLVING:
                suggested = DialogueAct.ASSERT
            elif context.strategy == StrategyType.REFLECTIVE and state == DialogueState.FEEDBACK:
                suggested = DialogueAct.CLARIFY
            elif context.strategy == StrategyType.PROACTIVE and state == DialogueState.GREETING:
                suggested = DialogueAct.SUGGEST

            return suggested

    # ── Summaries and Statistics ─────────────────────────

    def get_session_summary(self, session_id: str) -> dict:
        """Build a lightweight summary of a session's state and history."""
        with self._lock:
            context = self._sessions.get(session_id)
            if not context:
                return {}

            turns = self._turns.get(session_id, [])
            topic_map = self._topics.get(session_id, {})
            meta = self._session_meta.get(session_id, {})

            # Tally dialogue acts seen in this session
            act_counts: dict[str, int] = {}
            for turn in turns:
                act_counts[turn.dialogue_act.value] = act_counts.get(turn.dialogue_act.value, 0) + 1

            # Tally turn types
            type_counts: dict[str, int] = {}
            for turn in turns:
                type_counts[turn.turn_type.value] = type_counts.get(turn.turn_type.value, 0) + 1

            return {
                "session_id": session_id,
                "state": context.current_state.value,
                "phase": context.phase.value,
                "strategy": context.strategy.value,
                "turn_count": context.turn_count,
                "topic_count": len(topic_map),
                "pending_clarifications": len(context.pending_clarifications),
                "collected_info_keys": list(context.collected_info.keys()),
                "session_goals": list(context.session_goals),
                "user_engagement": context.user_engagement,
                "agent_confidence": context.agent_confidence,
                "ended": meta.get("ended", False),
                "agent_id": meta.get("agent_id", ""),
                "user_id": meta.get("user_id", ""),
                "act_counts": act_counts,
                "turn_type_counts": type_counts,
                "created_at": context.created_at,
                "updated_at": context.updated_at,
            }

    def get_stats(self) -> DialogueManagerStats:
        """Aggregate statistics across all known sessions."""
        with self._lock:
            stats = DialogueManagerStats()
            stats.total_sessions = len(self._sessions)

            state_distribution: dict[str, int] = {}
            strategy_distribution: dict[str, int] = {}
            engagement_sum = 0.0
            active_count = 0
            turn_total = 0

            for session_id, context in self._sessions.items():
                state_distribution[context.current_state.value] = (
                    state_distribution.get(context.current_state.value, 0) + 1
                )
                strategy_distribution[context.strategy.value] = (
                    strategy_distribution.get(context.strategy.value, 0) + 1
                )
                engagement_sum += context.user_engagement
                turn_total += context.turn_count

                if not self._session_meta.get(session_id, {}).get("ended", False):
                    active_count += 1

            stats.active_sessions = active_count
            stats.total_turns = turn_total
            stats.state_distribution = state_distribution
            stats.strategy_distribution = strategy_distribution

            if stats.total_sessions > 0:
                stats.avg_session_length = turn_total / stats.total_sessions
                stats.avg_engagement = engagement_sum / stats.total_sessions

            return stats

    # ── Reset ────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all sessions, turns, topics, and rules, then reseed defaults."""
        with self._lock:
            self._sessions.clear()
            self._turns.clear()
            self._topics.clear()
            self._rules.clear()
            self._session_meta.clear()
            self._init_default_rules_locked()
            logger.info("AgentDialogueManager reset")

    # ── Internal Helpers ─────────────────────────────────

    def _init_default_rules(self) -> None:
        """Seed the rule set with sensible defaults (called from __init__)."""
        # Lock already held during __init__ is not guaranteed, so acquire once.
        with self._lock:
            self._init_default_rules_locked()

    def _init_default_rules_locked(self) -> None:
        """Populate default transition rules. Caller must hold self._lock."""
        defaults = [
            # Greeting flows
            (DialogueState.GREETING, DialogueState.INFORMATION_GATHERING, DialogueAct.INFORM, "user states need", 10),
            (DialogueState.GREETING, DialogueState.PROBLEM_SOLVING, DialogueAct.REQUEST, "user asks directly", 20),
            (DialogueState.GREETING, DialogueState.CLARIFICATION, DialogueAct.QUESTION, "user is vague", 15),

            # Information gathering
            (DialogueState.INFORMATION_GATHERING, DialogueState.CLARIFICATION, DialogueAct.QUESTION, "info missing", 10),
            (DialogueState.INFORMATION_GATHERING, DialogueState.PROBLEM_SOLVING, DialogueAct.INFORM, "info complete", 20),
            (DialogueState.INFORMATION_GATHERING, DialogueState.EXECUTION, DialogueAct.REQUEST, "ready to act", 15),

            # Clarification
            (DialogueState.CLARIFICATION, DialogueState.INFORMATION_GATHERING, DialogueAct.ACKNOWLEDGE, "user answers", 10),
            (DialogueState.CLARIFICATION, DialogueState.PROBLEM_SOLVING, DialogueAct.INFORM, "clarified", 15),
            (DialogueState.CLARIFICATION, DialogueState.ERROR_RECOVERY, DialogueAct.APOLOGIZE, "user confused", 5),

            # Problem solving
            (DialogueState.PROBLEM_SOLVING, DialogueState.EXECUTION, DialogueAct.PROMISE, "plan agreed", 20),
            (DialogueState.PROBLEM_SOLVING, DialogueState.CLARIFICATION, DialogueAct.QUESTION, "ambiguity", 10),
            (DialogueState.PROBLEM_SOLVING, DialogueState.CONFIRMATION, DialogueAct.SUGGEST, "solution proposed", 15),

            # Execution
            (DialogueState.EXECUTION, DialogueState.CONFIRMATION, DialogueAct.INFORM, "action done", 20),
            (DialogueState.EXECUTION, DialogueState.ERROR_RECOVERY, DialogueAct.APOLOGIZE, "action failed", 25),

            # Confirmation
            (DialogueState.CONFIRMATION, DialogueState.FEEDBACK, DialogueAct.ACKNOWLEDGE, "user confirms", 20),
            (DialogueState.CONFIRMATION, DialogueState.PROBLEM_SOLVING, DialogueAct.REJECT, "user rejects", 15),

            # Feedback
            (DialogueState.FEEDBACK, DialogueState.CLOSING, DialogueAct.SUMMARIZE, "session winding down", 20),
            (DialogueState.FEEDBACK, DialogueState.PROBLEM_SOLVING, DialogueAct.SUGGEST, "iterate", 10),

            # Closing
            (DialogueState.CLOSING, DialogueState.GREETING, DialogueAct.ACKNOWLEDGE, "new topic", 5),

            # Error recovery returns to a sensible prior state
            (DialogueState.ERROR_RECOVERY, DialogueState.CLARIFICATION, DialogueAct.APOLOGIZE, "recover", 10),
            (DialogueState.ERROR_RECOVERY, DialogueState.INFORMATION_GATHERING, DialogueAct.QUESTION, "restart", 5),
        ]
        for from_state, to_state, trigger_act, condition, priority in defaults:
            self._rules.append(TransitionRule(
                from_state=from_state,
                to_state=to_state,
                trigger_act=trigger_act,
                condition=condition,
                priority=priority,
            ))

    def _evict_oldest_session(self) -> None:
        """Evict the least-recently-updated session. Caller must hold self._lock."""
        if not self._sessions:
            return
        oldest_id = min(self._sessions.keys(), key=lambda sid: self._sessions[sid].updated_at)
        self._sessions.pop(oldest_id, None)
        self._turns.pop(oldest_id, None)
        self._topics.pop(oldest_id, None)
        self._session_meta.pop(oldest_id, None)
        logger.info("Evicted oldest dialogue session %s (capacity)", oldest_id)

    def _trim_oldest_turns_globally(self, count: int) -> None:
        """Trim the oldest `count` turns across all sessions. Caller must hold self._lock."""
        if count <= 0:
            return
        # Build a list of (timestamp, session_id, index) and remove oldest first.
        candidates: list[tuple[float, str, int]] = []
        for session_id, turns in self._turns.items():
            for idx, turn in enumerate(turns):
                candidates.append((turn.timestamp, session_id, idx))
        candidates.sort(key=lambda c: (c[0], c[1], c[2]))
        to_remove_by_session: dict[str, set[int]] = {}
        for _, session_id, idx in candidates[:count]:
            to_remove_by_session.setdefault(session_id, set()).add(idx)
        for session_id, indices in to_remove_by_session.items():
            turns = self._turns.get(session_id)
            if not turns:
                continue
            self._turns[session_id] = [t for i, t in enumerate(turns) if i not in indices]
            context = self._sessions.get(session_id)
            if context:
                context.turn_count = len(self._turns[session_id])


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_dialogue_manager: AgentDialogueManager | None = None
_singleton_lock = threading.Lock()


def get_dialogue_manager() -> AgentDialogueManager:
    """Get or create the global AgentDialogueManager instance."""
    global _dialogue_manager
    if _dialogue_manager is None:
        with _singleton_lock:
            if _dialogue_manager is None:
                _dialogue_manager = AgentDialogueManager()
    return _dialogue_manager


def reset_dialogue_manager() -> None:
    """Reset the global AgentDialogueManager instance."""
    global _dialogue_manager
    with _singleton_lock:
        if _dialogue_manager is not None:
            _dialogue_manager.reset()
        _dialogue_manager = None
