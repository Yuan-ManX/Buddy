"""
Buddy Agent Self Identity System

A self-evolving identity layer that enables each agent to build and refine
a persistent digital self through hierarchical memory modeling, trait extraction,
and continuous alignment with user interactions.

The Agent Self is a living representation that grows more accurate over time,
capturing behavioral patterns, decision preferences, communication style,
and domain expertise through observation rather than static configuration.
"""

import logging
import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("buddy.agent_self")


class SelfTraitCategory(str, Enum):
    """Categories of traits that define an agent's digital self."""
    BEHAVIOR = "behavior"
    PREFERENCE = "preference"
    KNOWLEDGE = "knowledge"
    DECISION = "decision"
    COMMUNICATION = "communication"
    EMOTIONAL = "emotional"
    SOCIAL = "social"
    CREATIVE = "creative"


class TraitOrigin(str, Enum):
    """How a trait was acquired."""
    OBSERVED = "observed"
    INFERRED = "inferred"
    STATED = "stated"
    LEARNED = "learned"
    EVOLVED = "evolved"


@dataclass
class SelfTrait:
    """A single trait that defines part of the agent's digital self."""
    id: str
    category: SelfTraitCategory
    name: str
    value: str
    confidence: float = 0.5
    origin: TraitOrigin = TraitOrigin.INFERRED
    evidence_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    first_observed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)

    def reinforce(self, confidence_delta: float = 0.05):
        """Strengthen this trait based on new confirming evidence."""
        self.confidence = min(1.0, self.confidence + confidence_delta)
        self.evidence_count += 1
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def weaken(self, confidence_delta: float = 0.03):
        """Reduce confidence when contradictory evidence is found."""
        self.confidence = max(0.0, self.confidence - confidence_delta)
        self.last_updated = datetime.now(timezone.utc).isoformat()


@dataclass
class BehavioralPattern:
    """A recurring behavioral pattern extracted from interaction history."""
    id: str
    pattern_type: str
    description: str
    frequency: int = 0
    contexts: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    co_occurring_traits: list[str] = field(default_factory=list)
    first_detected: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_detected: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def record_occurrence(self, context: str = ""):
        """Record a new occurrence of this pattern."""
        self.frequency += 1
        self.last_detected = datetime.now(timezone.utc).isoformat()
        if context and context not in self.contexts:
            self.contexts.append(context)


@dataclass
class SelfSnapshot:
    """A point-in-time snapshot of the agent's digital self for evolution tracking."""
    id: str
    timestamp: str
    trait_count: int
    pattern_count: int
    dominant_categories: list[str]
    confidence_distribution: dict[str, float]
    evolution_step: int


class AgentSelf:
    """Core self-identity engine for a Buddy agent.

    Builds and maintains a persistent digital self through:
    - Hierarchical trait modeling across multiple personality dimensions
    - Behavioral pattern extraction from interaction streams
    - Continuous alignment based on observation and feedback
    - Self-snapshotting for evolution tracking and rollback
    """

    def __init__(self, agent_id: str, agent_name: str = ""):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self._traits: dict[str, SelfTrait] = {}
        self._patterns: dict[str, BehavioralPattern] = {}
        self._snapshots: list[SelfSnapshot] = []
        self._evolution_step = 0
        self._interaction_count = 0
        self._alignment_score = 0.5
        logger.info(f"AgentSelf initialized for {agent_id}")

    def add_trait(
        self,
        name: str,
        value: str,
        category: SelfTraitCategory,
        confidence: float = 0.5,
        origin: TraitOrigin = TraitOrigin.INFERRED,
    ) -> SelfTrait:
        """Add or update a trait in the agent's digital self."""
        trait_id = hashlib.md5(f"{name}:{category.value}".encode()).hexdigest()[:12]

        if trait_id in self._traits:
            existing = self._traits[trait_id]
            if existing.value != value:
                existing.weaken()
                if existing.confidence < 0.2:
                    existing.value = value
                    existing.origin = origin
                    existing.confidence = confidence
            else:
                existing.reinforce()
            return existing

        trait = SelfTrait(
            id=trait_id,
            category=category,
            name=name,
            value=value,
            confidence=confidence,
            origin=origin,
        )
        self._traits[trait_id] = trait
        logger.debug(f"Trait added: {name}={value} [{category.value}] confidence={confidence}")
        return trait

    def observe_interaction(self, user_message: str, agent_response: str, context: dict = None):
        """Observe an interaction and extract behavioral patterns and traits."""
        self._interaction_count += 1

        # Extract implicit traits from the interaction
        if context:
            self._extract_contextual_traits(context)

        # Detect behavioral patterns
        self._detect_patterns(user_message, agent_response)

        # Update alignment score
        self._recalculate_alignment()

        # Periodic self-snapshot
        if self._interaction_count % 50 == 0:
            self.create_snapshot()

    def _extract_contextual_traits(self, context: dict):
        """Extract traits from interaction context metadata."""
        topic = context.get("topic", "")
        sentiment = context.get("sentiment", "")
        complexity = context.get("complexity", "")

        if topic:
            self.add_trait(
                "discussed_topic",
                topic,
                SelfTraitCategory.KNOWLEDGE,
                confidence=0.3,
                origin=TraitOrigin.OBSERVED,
            )

        if sentiment in ("positive", "appreciative", "grateful"):
            self.add_trait(
                "user_satisfaction",
                "high",
                SelfTraitCategory.SOCIAL,
                confidence=0.4,
                origin=TraitOrigin.OBSERVED,
            )

        if complexity == "high":
            self.add_trait(
                "handles_complexity",
                "expert",
                SelfTraitCategory.BEHAVIOR,
                confidence=0.35,
                origin=TraitOrigin.INFERRED,
            )

    def _detect_patterns(self, user_message: str, agent_response: str):
        """Detect recurring behavioral patterns from interactions."""
        msg_lower = user_message.lower()
        resp_lower = agent_response.lower() if agent_response else ""

        pattern_signals = {
            "code_help": ["code", "python", "javascript", "function", "bug", "error", "debug"],
            "explanation": ["explain", "how does", "what is", "why", "tell me about"],
            "creative_writing": ["write", "story", "poem", "creative", "imagine"],
            "planning": ["plan", "strategy", "steps", "organize", "schedule"],
            "analysis": ["analyze", "compare", "evaluate", "assess", "review"],
            "emotional_support": ["feel", "sad", "worried", "anxious", "stressed", "happy"],
        }

        for pattern_type, keywords in pattern_signals.items():
            if any(kw in msg_lower for kw in keywords):
                if pattern_type not in self._patterns:
                    self._patterns[pattern_type] = BehavioralPattern(
                        id=hashlib.md5(pattern_type.encode()).hexdigest()[:12],
                        pattern_type=pattern_type,
                        description=f"Agent frequently handles {pattern_type.replace('_', ' ')} requests",
                    )
                self._patterns[pattern_type].record_occurrence(
                    context=pattern_type
                )

    def _recalculate_alignment(self):
        """Recalculate the overall alignment score based on trait consistency."""
        if not self._traits:
            self._alignment_score = 0.5
            return

        total_confidence = sum(t.confidence for t in self._traits.values())
        avg_confidence = total_confidence / len(self._traits)
        evidence_ratio = sum(
            1 for t in self._traits.values() if t.evidence_count > 0
        ) / max(len(self._traits), 1)

        self._alignment_score = (avg_confidence * 0.6) + (evidence_ratio * 0.4)

    def create_snapshot(self) -> SelfSnapshot:
        """Create a point-in-time snapshot of the current self for evolution tracking."""
        self._evolution_step += 1

        category_counts = {}
        for trait in self._traits.values():
            category_counts[trait.category.value] = category_counts.get(trait.category.value, 0) + 1

        snapshot = SelfSnapshot(
            id=hashlib.md5(
                f"{self.agent_id}:{self._evolution_step}:{datetime.now(timezone.utc).isoformat()}".encode()
            ).hexdigest()[:12],
            timestamp=datetime.now(timezone.utc).isoformat(),
            trait_count=len(self._traits),
            pattern_count=len(self._patterns),
            dominant_categories=sorted(
                category_counts, key=category_counts.get, reverse=True
            )[:3],
            confidence_distribution={
                "high": sum(1 for t in self._traits.values() if t.confidence > 0.7),
                "medium": sum(
                    1 for t in self._traits.values() if 0.3 <= t.confidence <= 0.7
                ),
                "low": sum(1 for t in self._traits.values() if t.confidence < 0.3),
            },
            evolution_step=self._evolution_step,
        )
        self._snapshots.append(snapshot)
        logger.info(
            f"Self snapshot created: step={self._evolution_step}, "
            f"traits={snapshot.trait_count}, patterns={snapshot.pattern_count}"
        )
        return snapshot

    def get_self_profile(self) -> dict:
        """Generate a comprehensive self profile for prompt construction."""
        high_confidence = [t for t in self._traits.values() if t.confidence > 0.6]
        top_patterns = sorted(
            self._patterns.values(), key=lambda p: p.frequency, reverse=True
        )[:5]

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "interaction_count": self._interaction_count,
            "alignment_score": round(self._alignment_score, 3),
            "evolution_step": self._evolution_step,
            "core_traits": [
                {
                    "name": t.name,
                    "value": t.value,
                    "category": t.category.value,
                    "confidence": round(t.confidence, 3),
                    "origin": t.origin.value,
                }
                for t in sorted(high_confidence, key=lambda t: t.confidence, reverse=True)[:10]
            ],
            "behavioral_patterns": [
                {
                    "type": p.pattern_type,
                    "description": p.description,
                    "frequency": p.frequency,
                }
                for p in top_patterns
            ],
            "trait_summary": {
                "total": len(self._traits),
                "high_confidence": len(high_confidence),
                "by_category": {
                    cat.value: sum(
                        1 for t in self._traits.values() if t.category == cat
                    )
                    for cat in SelfTraitCategory
                },
            },
        }

    def get_system_prompt_segment(self) -> str:
        """Generate a system prompt segment describing the agent's self."""
        profile = self.get_self_profile()
        core = profile["core_traits"]

        if not core:
            return ""

        lines = ["\n## Agent Self Profile", f"You are {self.agent_name}. "]
        lines.append("Your core traits based on interaction history:")

        for trait in core[:5]:
            lines.append(f"- {trait['name']}: {trait['value']} (confidence: {trait['confidence']:.0%})")

        if profile["behavioral_patterns"]:
            pattern_names = [p["type"].replace("_", " ") for p in profile["behavioral_patterns"][:3]]
            lines.append(f"\nYou frequently handle: {', '.join(pattern_names)}")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Get statistics about the agent's self model."""
        return {
            "agent_id": self.agent_id,
            "total_traits": len(self._traits),
            "total_patterns": len(self._patterns),
            "total_snapshots": len(self._snapshots),
            "interaction_count": self._interaction_count,
            "alignment_score": round(self._alignment_score, 3),
            "evolution_step": self._evolution_step,
            "trait_categories": {
                cat.value: sum(1 for t in self._traits.values() if t.category == cat)
                for cat in SelfTraitCategory
            },
            "top_patterns": sorted(
                [
                    {"type": p.pattern_type, "frequency": p.frequency}
                    for p in self._patterns.values()
                ],
                key=lambda x: x["frequency"],
                reverse=True,
            )[:5],
        }

    def export_self(self) -> dict:
        """Export the full agent self model for backup or migration."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "evolution_step": self._evolution_step,
            "interaction_count": self._interaction_count,
            "alignment_score": self._alignment_score,
            "traits": [
                {
                    "id": t.id,
                    "category": t.category.value,
                    "name": t.name,
                    "value": t.value,
                    "confidence": t.confidence,
                    "origin": t.origin.value,
                    "evidence_count": t.evidence_count,
                    "last_updated": t.last_updated,
                    "first_observed": t.first_observed,
                }
                for t in self._traits.values()
            ],
            "patterns": [
                {
                    "id": p.id,
                    "pattern_type": p.pattern_type,
                    "description": p.description,
                    "frequency": p.frequency,
                    "contexts": p.contexts,
                    "triggers": p.triggers,
                    "first_detected": p.first_detected,
                    "last_detected": p.last_detected,
                }
                for p in self._patterns.values()
            ],
            "snapshots": [
                {
                    "id": s.id,
                    "timestamp": s.timestamp,
                    "trait_count": s.trait_count,
                    "pattern_count": s.pattern_count,
                    "dominant_categories": s.dominant_categories,
                    "evolution_step": s.evolution_step,
                }
                for s in self._snapshots[-10:]
            ],
        }

    def import_self(self, data: dict):
        """Import an agent self model from exported data."""
        self.agent_name = data.get("agent_name", self.agent_name)
        self._evolution_step = data.get("evolution_step", 0)
        self._interaction_count = data.get("interaction_count", 0)
        self._alignment_score = data.get("alignment_score", 0.5)

        for trait_data in data.get("traits", []):
            trait = SelfTrait(
                id=trait_data["id"],
                category=SelfTraitCategory(trait_data["category"]),
                name=trait_data["name"],
                value=trait_data["value"],
                confidence=trait_data["confidence"],
                origin=TraitOrigin(trait_data["origin"]),
                evidence_count=trait_data.get("evidence_count", 0),
                last_updated=trait_data.get("last_updated", ""),
                first_observed=trait_data.get("first_observed", ""),
            )
            self._traits[trait.id] = trait

        for pattern_data in data.get("patterns", []):
            pattern = BehavioralPattern(
                id=pattern_data["id"],
                pattern_type=pattern_data["pattern_type"],
                description=pattern_data["description"],
                frequency=pattern_data["frequency"],
                contexts=pattern_data.get("contexts", []),
                triggers=pattern_data.get("triggers", []),
                first_detected=pattern_data.get("first_detected", ""),
                last_detected=pattern_data.get("last_detected", ""),
            )
            self._patterns[pattern.id] = pattern

        logger.info(
            f"Agent self imported for {self.agent_id}: "
            f"{len(self._traits)} traits, {len(self._patterns)} patterns"
        )


# Global registry of agent selves
class AgentSelfRegistry:
    """Registry managing AgentSelf instances for all agents."""

    def __init__(self):
        self._selves: dict[str, AgentSelf] = {}

    def get_or_create(self, agent_id: str, agent_name: str = "") -> AgentSelf:
        """Get or create an AgentSelf for the given agent."""
        if agent_id not in self._selves:
            self._selves[agent_id] = AgentSelf(agent_id, agent_name)
        return self._selves[agent_id]

    def get(self, agent_id: str) -> Optional[AgentSelf]:
        """Get an AgentSelf if it exists."""
        return self._selves.get(agent_id)

    def list_all(self) -> list[dict]:
        """List all agent selves with their stats."""
        return [
            {"agent_id": aid, **self._selves[aid].get_stats()}
            for aid in self._selves
        ]

    def remove(self, agent_id: str):
        """Remove an agent self."""
        self._selves.pop(agent_id, None)


# Global singleton
agent_self_registry = AgentSelfRegistry()