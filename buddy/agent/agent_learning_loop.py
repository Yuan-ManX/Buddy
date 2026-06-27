"""
Buddy Interactive Learning Loop - Continuous learning and adaptation system.

An interactive learning system that captures user feedback, learns from
interactions, adapts agent behavior over time, and continuously improves
through reinforcement from real usage patterns.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeedbackType(str, Enum):
    """Types of learning feedback."""
    EXPLICIT = "explicit"       # Direct user feedback (thumbs up/down, ratings)
    IMPLICIT = "implicit"       # Inferred from user behavior
    CORRECTIVE = "corrective"   # User correction of agent output
    REINFORCEMENT = "reinforcement"  # Positive reinforcement signal
    PREFERENCE = "preference"   # User preference indication


class LearningSignal(str, Enum):
    """Learning signals extracted from interactions."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTION = "correction"
    ADAPTATION = "adaptation"


class AdaptationType(str, Enum):
    """Types of behavioral adaptations."""
    STYLE = "style"             # Communication style adjustment
    TONE = "tone"               # Tone adjustment
    DEPTH = "depth"             # Response depth/detail level
    FORMAT = "format"           # Output format preference
    DOMAIN = "domain"           # Domain-specific knowledge
    TOOL_USAGE = "tool_usage"   # Tool usage patterns
    PROACTIVITY = "proactivity" # Proactive behavior level


@dataclass
class LearningEvent:
    """A single learning event from an interaction."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    interaction_id: str = ""
    feedback_type: FeedbackType = FeedbackType.IMPLICIT
    signal: LearningSignal = LearningSignal.NEUTRAL
    description: str = ""
    context: str = ""
    agent_response: str = ""
    user_reaction: str = ""
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class AdaptationRule:
    """A learned adaptation rule for agent behavior."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    adaptation_type: AdaptationType = AdaptationType.STYLE
    condition: str = ""
    action: str = ""
    confidence: float = 0.5
    success_count: int = 0
    failure_count: int = 0
    last_applied: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class LearningSession:
    """A continuous learning session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str = ""
    events: list[LearningEvent] = field(default_factory=list)
    adaptations: list[AdaptationRule] = field(default_factory=list)
    status: str = "active"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class UserPreferenceProfile:
    """Aggregated user preference profile learned over time."""
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str = ""
    preferred_style: str = "balanced"
    preferred_tone: str = "neutral"
    preferred_depth: str = "moderate"
    preferred_format: str = "paragraph"
    domain_interests: list[str] = field(default_factory=list)
    common_topics: list[str] = field(default_factory=list)
    engagement_patterns: dict[str, float] = field(default_factory=dict)
    total_interactions: int = 0
    positive_rate: float = 0.0
    updated_at: float = field(default_factory=time.time)


class InteractiveLearningLoop:
    """Continuous learning and adaptation system.

    Captures feedback from every interaction, learns behavioral patterns,
    and continuously adapts agent behavior to optimize user satisfaction.
    Implements a closed learning loop: Interact -> Observe -> Learn -> Adapt.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, LearningSession] = {}
        self._events: list[LearningEvent] = []
        self._rules: list[AdaptationRule] = []
        self._profiles: dict[str, UserPreferenceProfile] = {}
        self._total_events: int = 0
        self._total_adaptations: int = 0

    # ── Session Management ───────────────────────────────────────

    def create_session(self, user_id: str = "") -> LearningSession:
        """Create a new learning session.

        Args:
            user_id: Identifier for the user.

        Returns:
            The created LearningSession.
        """
        session = LearningSession(user_id=user_id)
        self._sessions[session.session_id] = session
        return session

    def record_event(
        self,
        session_id: str,
        feedback_type: FeedbackType,
        signal: LearningSignal,
        description: str = "",
        context: str = "",
        agent_response: str = "",
        user_reaction: str = "",
        confidence: float = 0.5,
        tags: list[str] | None = None,
    ) -> LearningEvent | None:
        """Record a learning event from an interaction.

        Args:
            session_id: The learning session ID.
            feedback_type: Type of feedback received.
            signal: The learning signal extracted.
            description: Description of the event.
            context: Context of the interaction.
            agent_response: What the agent said/did.
            user_reaction: How the user reacted.
            confidence: Confidence in the learning signal.
            tags: Categorization tags.

        Returns:
            The created LearningEvent or None.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        event = LearningEvent(
            interaction_id=session_id,
            feedback_type=feedback_type,
            signal=signal,
            description=description,
            context=context,
            agent_response=agent_response,
            user_reaction=user_reaction,
            confidence=confidence,
            tags=tags or [],
        )
        session.events.append(event)
        session.updated_at = time.time()
        self._events.append(event)
        self._total_events += 1

        # Update user profile
        if session.user_id:
            self._update_profile(session.user_id, event)

        return event

    def create_adaptation(
        self,
        adaptation_type: AdaptationType,
        condition: str,
        action: str,
        confidence: float = 0.5,
    ) -> AdaptationRule:
        """Create a new adaptation rule based on learned patterns.

        Args:
            adaptation_type: What aspect of behavior to adapt.
            condition: When to apply this adaptation.
            action: What action to take.
            confidence: Confidence in this adaptation.

        Returns:
            The created AdaptationRule.
        """
        rule = AdaptationRule(
            adaptation_type=adaptation_type,
            condition=condition,
            action=action,
            confidence=confidence,
        )
        self._rules.append(rule)
        self._total_adaptations += 1
        return rule

    def apply_adaptation(
        self, rule_id: str, success: bool = True
    ) -> AdaptationRule | None:
        """Record the outcome of applying an adaptation rule.

        Args:
            rule_id: The rule ID.
            success: Whether the adaptation was successful.

        Returns:
            The updated AdaptationRule or None.
        """
        for rule in self._rules:
            if rule.rule_id == rule_id:
                if success:
                    rule.success_count += 1
                    rule.confidence = min(1.0, rule.confidence + 0.05)
                else:
                    rule.failure_count += 1
                    rule.confidence = max(0.1, rule.confidence - 0.1)
                rule.last_applied = time.time()
                return rule
        return None

    def learn_from_session(self, session_id: str) -> list[AdaptationRule]:
        """Analyze a session and generate adaptation rules.

        Args:
            session_id: The session to learn from.

        Returns:
            List of newly created AdaptationRule objects.
        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        new_rules: list[AdaptationRule] = []

        # Analyze positive events
        positive_events = [
            e for e in session.events
            if e.signal == LearningSignal.POSITIVE
        ]

        # Analyze negative events
        negative_events = [
            e for e in session.events
            if e.signal == LearningSignal.NEGATIVE
        ]

        # Analyze corrections
        corrections = [
            e for e in session.events
            if e.signal == LearningSignal.CORRECTION
        ]

        # Generate rules from patterns
        if positive_events:
            # Reinforce what works
            common_tags = self._find_common_tags(positive_events)
            for tag in common_tags:
                rule = self.create_adaptation(
                    adaptation_type=AdaptationType.STYLE,
                    condition=f"context_contains:{tag}",
                    action="reinforce_current_approach",
                    confidence=0.7,
                )
                new_rules.append(rule)

        if corrections:
            # Adapt based on corrections
            for correction in corrections[:3]:
                rule = self.create_adaptation(
                    adaptation_type=AdaptationType.FORMAT,
                    condition=f"correction_pattern:{correction.description[:50]}",
                    action="adjust_output_format",
                    confidence=0.6,
                )
                new_rules.append(rule)

        if negative_events:
            # Avoid what doesn't work
            for event in negative_events[:3]:
                rule = self.create_adaptation(
                    adaptation_type=AdaptationType.DEPTH,
                    condition=f"negative_pattern:{event.description[:50]}",
                    action="reduce_depth_or_change_approach",
                    confidence=0.5,
                )
                new_rules.append(rule)

        return new_rules

    def _find_common_tags(self, events: list[LearningEvent]) -> list[str]:
        """Find common tags across events."""
        tag_counts: dict[str, int] = defaultdict(int)
        for event in events:
            for tag in event.tags:
                tag_counts[tag] += 1
        threshold = max(1, len(events) // 2)
        return [tag for tag, count in tag_counts.items() if count >= threshold]

    def _update_profile(
        self, user_id: str, event: LearningEvent
    ) -> None:
        """Update a user's preference profile based on new events."""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserPreferenceProfile(user_id=user_id)

        profile = self._profiles[user_id]
        profile.total_interactions += 1

        # Update engagement patterns
        signal_key = event.signal.value
        profile.engagement_patterns[signal_key] = (
            profile.engagement_patterns.get(signal_key, 0) + 1
        )

        # Update positive rate
        total = sum(profile.engagement_patterns.values())
        positive = profile.engagement_patterns.get("positive", 0)
        profile.positive_rate = positive / total if total > 0 else 0.0

        # Update topics from tags
        for tag in event.tags:
            if tag not in profile.common_topics:
                profile.common_topics.append(tag)

        profile.updated_at = time.time()

    # ── Query & Stats ────────────────────────────────────────────

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        """Get a user's preference profile."""
        profile = self._profiles.get(user_id)
        if not profile:
            return None
        return {
            "profile_id": profile.profile_id,
            "user_id": profile.user_id,
            "preferred_style": profile.preferred_style,
            "preferred_tone": profile.preferred_tone,
            "preferred_depth": profile.preferred_depth,
            "preferred_format": profile.preferred_format,
            "domain_interests": profile.domain_interests,
            "common_topics": profile.common_topics[-10:],
            "engagement_patterns": profile.engagement_patterns,
            "total_interactions": profile.total_interactions,
            "positive_rate": round(profile.positive_rate, 3),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get learning loop statistics."""
        return {
            "total_events": self._total_events,
            "total_adaptations": self._total_adaptations,
            "active_sessions": len(self._sessions),
            "active_rules": len(self._rules),
            "user_profiles": len(self._profiles),
            "rules_by_type": {
                t.value: len([r for r in self._rules if r.adaptation_type == t])
                for t in AdaptationType
            },
            "avg_rule_confidence": round(
                sum(r.confidence for r in self._rules) / len(self._rules), 3
            ) if self._rules else 0.0,
            "signal_distribution": self._compute_signal_distribution(),
        }

    def _compute_signal_distribution(self) -> dict[str, int]:
        """Compute the distribution of learning signals."""
        dist: dict[str, int] = defaultdict(int)
        for event in self._events:
            dist[event.signal.value] += 1
        return dict(dist)

    def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent learning events."""
        return [
            {
                "event_id": e.event_id,
                "feedback_type": e.feedback_type.value,
                "signal": e.signal.value,
                "description": e.description,
                "context": e.context[:200],
                "confidence": e.confidence,
                "tags": e.tags,
            }
            for e in self._events[-limit:]
        ]

    def get_top_rules(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top-performing adaptation rules."""
        sorted_rules = sorted(
            self._rules,
            key=lambda r: r.confidence * (r.success_count + 1),
            reverse=True,
        )
        return [
            {
                "rule_id": r.rule_id,
                "adaptation_type": r.adaptation_type.value,
                "condition": r.condition,
                "action": r.action,
                "confidence": r.confidence,
                "success_count": r.success_count,
                "failure_count": r.failure_count,
            }
            for r in sorted_rules[:limit]
        ]

    def reset(self) -> None:
        """Reset the learning loop to initial state."""
        self._sessions.clear()
        self._events.clear()
        self._rules.clear()
        self._profiles.clear()
        self._total_events = 0
        self._total_adaptations = 0


# ── Singleton Access ───────────────────────────────────────────────

_learning_loop: InteractiveLearningLoop | None = None


def get_learning_loop() -> InteractiveLearningLoop:
    """Get or create the singleton learning loop instance."""
    global _learning_loop
    if _learning_loop is None:
        _learning_loop = InteractiveLearningLoop()
    return _learning_loop


def reset_learning_loop() -> None:
    """Reset the singleton learning loop."""
    global _learning_loop
    if _learning_loop:
        _learning_loop.reset()
    _learning_loop = None