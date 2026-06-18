"""
Buddy Identity Core

Hierarchical Memory Modeling (HMM) for agent identity preservation.
Models agent identity across multiple layers: episodic memory (raw experiences),
semantic memory (extracted knowledge), and procedural memory (learned behaviors).
Enables agents to build, maintain, and evolve a coherent self-model.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MemoryLayer(Enum):
    """Hierarchical memory layers for identity modeling."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    META = "meta"


class TraitCategory(Enum):
    """Categories of identity traits."""

    COGNITIVE = "cognitive"
    BEHAVIORAL = "behavioral"
    SOCIAL = "social"
    DOMAIN = "domain"
    PREFERENCE = "preference"


@dataclass
class IdentityTrait:
    """A single identity trait extracted from agent behavior."""

    trait_id: str
    name: str
    category: TraitCategory
    value: float = 0.5
    confidence: float = 0.0
    source_experiences: list[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stability: float = 0.0

    def to_dict(self) -> dict:
        return {
            "trait_id": self.trait_id,
            "name": self.name,
            "category": self.category.value,
            "value": self.value,
            "confidence": self.confidence,
            "source_experiences": self.source_experiences,
            "last_updated": self.last_updated,
            "stability": self.stability,
        }


@dataclass
class EpisodicEntry:
    """A raw experience captured by the agent."""

    entry_id: str
    content: str
    context: dict = field(default_factory=dict)
    emotional_valence: float = 0.0
    importance: float = 0.5
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "content": self.content[:500],
            "context": self.context,
            "emotional_valence": self.emotional_valence,
            "importance": self.importance,
            "timestamp": self.timestamp,
        }


@dataclass
class SemanticNode:
    """Extracted knowledge from episodic memories."""

    node_id: str
    concept: str
    relationships: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.5
    source_episodes: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "concept": self.concept,
            "relationships": self.relationships,
            "confidence": self.confidence,
            "source_episodes": self.source_episodes,
            "timestamp": self.timestamp,
        }


@dataclass
class ProceduralPattern:
    """Learned behavioral patterns from repeated experiences."""

    pattern_id: str
    pattern_type: str
    trigger_conditions: list[str] = field(default_factory=list)
    action_sequence: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    execution_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "trigger_conditions": self.trigger_conditions,
            "action_sequence": self.action_sequence,
            "success_rate": self.success_rate,
            "execution_count": self.execution_count,
            "timestamp": self.timestamp,
        }


class IdentityCore:
    """Hierarchical identity modeling system for agent self-awareness."""

    def __init__(self, agent_id: str, agent_name: str = "Buddy"):
        self.agent_id = agent_id
        self.agent_name = agent_name

        # Hierarchical memory layers
        self._episodic: list[EpisodicEntry] = []
        self._semantic: dict[str, SemanticNode] = {}
        self._procedural: dict[str, ProceduralPattern] = {}

        # Identity traits
        self._traits: dict[str, IdentityTrait] = {}

        # Meta-cognition
        self._self_awareness_level: float = 0.3
        self._identity_coherence: float = 0.5
        self._evolution_history: list[dict] = []

        # Statistics
        self._total_experiences: int = 0
        self._total_abstractions: int = 0

        # Initialize default traits
        self._init_default_traits()

    def _init_default_traits(self):
        """Initialize default identity traits."""
        defaults = [
            ("helpfulness", TraitCategory.BEHAVIORAL, 0.85),
            ("curiosity", TraitCategory.COGNITIVE, 0.7),
            ("precision", TraitCategory.COGNITIVE, 0.75),
            ("creativity", TraitCategory.COGNITIVE, 0.65),
            ("empathy", TraitCategory.SOCIAL, 0.6),
            ("autonomy", TraitCategory.BEHAVIORAL, 0.5),
            ("adaptability", TraitCategory.COGNITIVE, 0.7),
            ("consistency", TraitCategory.BEHAVIORAL, 0.8),
        ]
        for name, category, value in defaults:
            trait_id = f"trait_{name}"
            self._traits[trait_id] = IdentityTrait(
                trait_id=trait_id,
                name=name,
                category=category,
                value=value,
                confidence=0.5,
            )

    # ── Episodic Memory ──

    def record_experience(self, content: str, context: dict | None = None,
                          importance: float = 0.5, emotional_valence: float = 0.0) -> EpisodicEntry:
        """Record a raw experience."""
        import uuid
        entry = EpisodicEntry(
            entry_id=str(uuid.uuid4())[:8],
            content=content,
            context=context or {},
            importance=importance,
            emotional_valence=emotional_valence,
        )
        self._episodic.append(entry)
        self._total_experiences += 1

        # Keep memory manageable
        if len(self._episodic) > 1000:
            # Retain high-importance entries
            self._episodic.sort(key=lambda e: e.importance, reverse=True)
            self._episodic = self._episodic[:800]

        # Trigger consolidation if enough experiences
        if len(self._episodic) % 50 == 0:
            self._consolidate()

        return entry

    def query_episodic(self, keyword: str | None = None, limit: int = 20) -> list[dict]:
        """Query episodic memories."""
        entries = self._episodic
        if keyword:
            kw = keyword.lower()
            entries = [e for e in entries if kw in e.content.lower()]
        entries.sort(key=lambda e: e.importance, reverse=True)
        return [e.to_dict() for e in entries[:limit]]

    # ── Semantic Memory ──

    def _consolidate(self):
        """Consolidate episodic memories into semantic knowledge."""
        # Extract concepts from recent experiences
        recent = self._episodic[-50:]
        concepts = self._extract_concepts(recent)

        for concept, confidence in concepts.items():
            if concept not in self._semantic:
                self._semantic[concept] = SemanticNode(
                    node_id=f"node_{concept}",
                    concept=concept,
                    confidence=confidence,
                    source_episodes=[e.entry_id for e in recent[:3]],
                )
                self._total_abstractions += 1
            else:
                node = self._semantic[concept]
                node.confidence = min(1.0, node.confidence + confidence * 0.1)
                node.source_episodes = (node.source_episodes +
                                       [e.entry_id for e in recent[:2]])[-5:]

        self._update_identity_coherence()

    def _extract_concepts(self, entries: list[EpisodicEntry]) -> dict[str, float]:
        """Extract key concepts from episodic entries."""
        concepts: dict[str, float] = {}

        # Simple keyword-based concept extraction
        keyword_weights = {
            "code": 0.8, "build": 0.7, "create": 0.7, "analyze": 0.75,
            "learn": 0.6, "teach": 0.6, "help": 0.7, "solve": 0.8,
            "design": 0.7, "debug": 0.75, "test": 0.7, "deploy": 0.7,
            "write": 0.6, "read": 0.5, "review": 0.65, "plan": 0.7,
            "research": 0.7, "explain": 0.6, "improve": 0.7, "optimize": 0.8,
            "error": 0.6, "success": 0.7, "failure": 0.6,
        }

        for entry in entries:
            content_lower = entry.content.lower()
            for keyword, weight in keyword_weights.items():
                if keyword in content_lower:
                    concepts[keyword] = concepts.get(keyword, 0) + weight * entry.importance

        return concepts

    def query_semantic(self, concept: str | None = None) -> list[dict]:
        """Query semantic knowledge."""
        if concept:
            return [n.to_dict() for n in self._semantic.values()
                    if concept.lower() in n.concept.lower()]
        return [n.to_dict() for n in self._semantic.values()]

    # ── Procedural Memory ──

    def learn_pattern(self, pattern_type: str, trigger_conditions: list[str],
                      action_sequence: list[str]) -> ProceduralPattern:
        """Learn a new procedural pattern."""
        import uuid
        pattern_id = str(uuid.uuid4())[:8]
        pattern = ProceduralPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            trigger_conditions=trigger_conditions,
            action_sequence=action_sequence,
        )
        self._procedural[pattern_id] = pattern
        return pattern

    def update_pattern(self, pattern_id: str, success: bool):
        """Update a pattern's success rate."""
        pattern = self._procedural.get(pattern_id)
        if pattern:
            pattern.execution_count += 1
            if success:
                pattern.success_rate = (
                    (pattern.success_rate * (pattern.execution_count - 1) + 1) /
                    pattern.execution_count
                )

    # ── Identity Traits ──

    def update_trait(self, name: str, delta: float, confidence_delta: float = 0.01):
        """Update an identity trait value."""
        for trait in self._traits.values():
            if trait.name == name:
                trait.value = max(0.0, min(1.0, trait.value + delta))
                trait.confidence = min(1.0, trait.confidence + confidence_delta)
                trait.last_updated = datetime.now(timezone.utc).isoformat()
                trait.stability = min(1.0, trait.stability + 0.01)
                break

    def extract_traits_from_experience(self, content: str):
        """Extract and update traits from an experience."""
        content_lower = content.lower()

        trait_patterns = {
            "helpfulness": ["help", "assist", "guide", "support", "explain"],
            "curiosity": ["explore", "investigate", "research", "discover", "learn"],
            "precision": ["exact", "precise", "accurate", "correct", "specific"],
            "creativity": ["create", "design", "innovate", "imagine", "novel"],
            "empathy": ["understand", "feel", "emotion", "perspective", "care"],
            "autonomy": ["decide", "autonomous", "self", "independent", "initiative"],
            "adaptability": ["adapt", "adjust", "flexible", "change", "evolve"],
            "consistency": ["consistent", "reliable", "stable", "always", "pattern"],
        }

        for trait_name, patterns in trait_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    self.update_trait(trait_name, 0.02, 0.01)
                    break

    # ── Meta-Cognition ──

    def _update_identity_coherence(self):
        """Update the overall identity coherence score."""
        if self._traits:
            stabilities = [t.stability for t in self._traits.values()]
            self._identity_coherence = sum(stabilities) / len(stabilities)
        self._self_awareness_level = min(
            1.0,
            self._self_awareness_level + 0.001 * self._total_experiences
        )

    def get_identity_profile(self) -> dict:
        """Get the complete identity profile."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "self_awareness": self._self_awareness_level,
            "identity_coherence": self._identity_coherence,
            "traits": {t.name: t.to_dict() for t in self._traits.values()},
            "memory_stats": {
                "episodic_entries": len(self._episodic),
                "semantic_nodes": len(self._semantic),
                "procedural_patterns": len(self._procedural),
                "total_experiences": self._total_experiences,
                "total_abstractions": self._total_abstractions,
            },
            "evolution_history": self._evolution_history[-10:],
        }

    def get_stats(self) -> dict:
        """Get identity core statistics."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "self_awareness": self._self_awareness_level,
            "identity_coherence": self._identity_coherence,
            "total_traits": len(self._traits),
            "episodic_entries": len(self._episodic),
            "semantic_nodes": len(self._semantic),
            "procedural_patterns": len(self._procedural),
            "total_experiences": self._total_experiences,
            "total_abstractions": self._total_abstractions,
            "traits": {
                t.name: {
                    "value": t.value,
                    "confidence": t.confidence,
                    "stability": t.stability,
                    "category": t.category.value,
                }
                for t in self._traits.values()
            },
        }


class IdentityRegistry:
    """Registry for managing multiple agent identities."""

    def __init__(self):
        self._identities: dict[str, IdentityCore] = {}

    def get_or_create(self, agent_id: str, agent_name: str = "Buddy") -> IdentityCore:
        if agent_id not in self._identities:
            self._identities[agent_id] = IdentityCore(agent_id, agent_name)
        return self._identities[agent_id]

    def get(self, agent_id: str) -> IdentityCore | None:
        return self._identities.get(agent_id)

    def get_stats(self) -> dict:
        return {
            "total_identities": len(self._identities),
            "identities": {
                aid: identity.get_stats() for aid, identity in self._identities.items()
            },
        }


# Global instance
identity_registry = IdentityRegistry()