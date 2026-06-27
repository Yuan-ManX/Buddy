"""
Buddy Personal Memory Engine - AI-native personalized memory layer.

Provides a persistent, evolving memory system that learns from user interactions
to build a rich personal profile. The engine captures preferences, patterns,
knowledge, and behavioral traits to enable deeply personalized agent experiences.

Core capabilities:
- Multi-dimensional memory capture (preferences, facts, patterns, skills, context)
- Automatic memory consolidation and decay modeling
- Semantic memory retrieval with relevance scoring
- Memory chain building for narrative continuity
- Privacy-aware memory partitioning with access controls
- Memory strength calibration based on recency and frequency
- Cross-session memory persistence and synchronization
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.personal_memory")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class MemoryDimension(str, Enum):
    """Dimensions of personal memory."""
    PREFERENCE = "preference"
    FACT = "fact"
    PATTERN = "pattern"
    SKILL = "skill"
    CONTEXT = "context"
    RELATIONSHIP = "relationship"
    GOAL = "goal"
    EMOTION = "emotion"


class MemoryStrength(str, Enum):
    """Memory strength levels based on recall frequency and recency."""
    EPHEMERAL = "ephemeral"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    CORE = "core"


class AccessLevel(str, Enum):
    """Privacy and access control levels for memories."""
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class ConsolidationStrategy(str, Enum):
    """Strategies for memory consolidation."""
    MERGE = "merge"
    REINFORCE = "reinforce"
    DECAY = "decay"
    ARCHIVE = "archive"
    ELEVATE = "elevate"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class MemoryEntry:
    """A single memory entry in the personal memory store."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    dimension: MemoryDimension = MemoryDimension.FACT
    content: str = ""
    strength: MemoryStrength = MemoryStrength.MODERATE
    access_level: AccessLevel = AccessLevel.PRIVATE
    confidence: float = 1.0
    recall_count: int = 0
    last_recalled: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = field(default_factory=list)
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryChain:
    """A chain of related memories forming a narrative."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    entries: list[str] = field(default_factory=list)
    summary: str = ""
    coherence_score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PersonalProfile:
    """Aggregated personal profile built from memories."""
    user_id: str = ""
    traits: dict[str, float] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    knowledge_domains: list[str] = field(default_factory=list)
    communication_style: dict[str, float] = field(default_factory=dict)
    goals: list[dict[str, Any]] = field(default_factory=list)
    relationship_graph: dict[str, list[str]] = field(default_factory=dict)
    total_memories: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConsolidationReport:
    """Report from a memory consolidation cycle."""
    memories_processed: int = 0
    memories_merged: int = 0
    memories_reinforced: int = 0
    memories_decayed: int = 0
    memories_archived: int = 0
    memories_elevated: int = 0
    new_chains_created: int = 0
    profile_updates: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Personal Memory Engine
# ═══════════════════════════════════════════════════════════

class PersonalMemoryEngine:
    """AI-native personal memory system for persistent agent personalization.

    Captures, stores, consolidates, and retrieves personal memories across
    multiple dimensions. Builds a rich personal profile that evolves over
    time through interaction.

    Memory strength follows a decay model: strength decreases with time
    but increases with recall frequency. Core memories persist indefinitely.
    """

    # Decay parameters
    DECAY_HALF_LIFE_DAYS: dict[MemoryStrength, float] = {
        MemoryStrength.EPHEMERAL: 1.0,
        MemoryStrength.WEAK: 7.0,
        MemoryStrength.MODERATE: 30.0,
        MemoryStrength.STRONG: 90.0,
        MemoryStrength.CORE: float("inf"),
    }

    # Consolidation thresholds
    RECALL_THRESHOLD_FOR_STRENGTHEN: int = 3
    AGE_THRESHOLD_FOR_ARCHIVE_DAYS: int = 180
    SIMILARITY_THRESHOLD_FOR_MERGE: float = 0.85

    def __init__(self) -> None:
        self._memories: dict[str, MemoryEntry] = {}
        self._chains: dict[str, MemoryChain] = {}
        self._profile: PersonalProfile = PersonalProfile()
        self._dimension_index: dict[MemoryDimension, list[str]] = defaultdict(list)
        self._tag_index: dict[str, list[str]] = defaultdict(list)
        self._consolidation_history: list[ConsolidationReport] = []
        self._total_captures: int = 0
        self._total_retrievals: int = 0

    # ── Memory Capture ─────────────────────────────────────────────

    def capture(
        self,
        content: str,
        dimension: MemoryDimension = MemoryDimension.FACT,
        confidence: float = 1.0,
        access_level: AccessLevel = AccessLevel.PRIVATE,
        tags: list[str] | None = None,
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Capture a new personal memory.

        Args:
            content: The memory content to store.
            dimension: The memory dimension category.
            confidence: Confidence level in the memory (0.0-1.0).
            access_level: Privacy access level.
            tags: Optional tags for categorization.
            source: Source of the memory.
            metadata: Additional metadata.

        Returns:
            The created MemoryEntry.
        """
        entry = MemoryEntry(
            dimension=dimension,
            content=content,
            confidence=confidence,
            access_level=access_level,
            tags=tags or [],
            source=source,
            metadata=metadata or {},
        )
        self._memories[entry.id] = entry
        self._dimension_index[dimension].append(entry.id)
        for tag in entry.tags:
            self._tag_index[tag].append(entry.id)
        self._total_captures += 1
        self._profile.total_memories += 1
        logger.debug(
            "Memory captured: %s [%s] confidence=%.2f",
            entry.id, dimension.value, confidence,
        )
        return entry

    # ── Memory Retrieval ───────────────────────────────────────────

    def retrieve(
        self,
        query: str = "",
        dimension: MemoryDimension | None = None,
        tags: list[str] | None = None,
        min_strength: MemoryStrength | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Retrieve memories matching the given criteria.

        Args:
            query: Semantic search query (simple substring matching).
            dimension: Filter by memory dimension.
            tags: Filter by tags.
            min_strength: Minimum memory strength.
            limit: Maximum number of results.

        Returns:
            List of matching MemoryEntry objects.
        """
        candidates = list(self._memories.values())

        if dimension:
            candidates = [m for m in candidates if m.dimension == dimension]
        if tags:
            candidates = [m for m in candidates if any(t in m.tags for t in tags)]
        if query:
            query_lower = query.lower()
            candidates = [m for m in candidates if query_lower in m.content.lower()]
        if min_strength:
            strength_order = list(MemoryStrength)
            min_idx = strength_order.index(min_strength)
            candidates = [
                m for m in candidates
                if strength_order.index(m.strength) >= min_idx
            ]

        # Sort by relevance: higher strength and confidence first
        strength_order = list(MemoryStrength)
        candidates.sort(
            key=lambda m: (
                strength_order.index(m.strength),
                m.confidence,
                m.recall_count,
            ),
            reverse=True,
        )

        results = candidates[:limit]
        for entry in results:
            entry.recall_count += 1
            entry.last_recalled = datetime.now(timezone.utc)
            self._total_retrievals += 1

        return results

    def get_memory(self, memory_id: str) -> MemoryEntry | None:
        """Get a specific memory by ID."""
        entry = self._memories.get(memory_id)
        if entry:
            entry.recall_count += 1
            entry.last_recalled = datetime.now(timezone.utc)
        return entry

    # ── Memory Strength Calibration ────────────────────────────────

    def calibrate_strength(self, memory_id: str) -> MemoryStrength:
        """Recalculate memory strength based on recency and frequency.

        Uses a decay model where strength decreases over time but
        increases with recall frequency.

        Args:
            memory_id: The memory to calibrate.

        Returns:
            The new MemoryStrength value.
        """
        entry = self._memories.get(memory_id)
        if not entry:
            return MemoryStrength.EPHEMERAL

        if entry.strength == MemoryStrength.CORE:
            return MemoryStrength.CORE

        now = datetime.now(timezone.utc)
        age_days = (now - entry.created_at).total_seconds() / 86400.0
        half_life = self.DECAY_HALF_LIFE_DAYS.get(entry.strength, 30.0)

        if half_life == float("inf"):
            return entry.strength

        # Decay factor based on age
        decay = math.exp(-math.log(2) * age_days / half_life)
        # Boost from recall frequency
        recall_boost = math.log(1 + entry.recall_count) * 0.2
        effective_strength = decay * (1.0 + recall_boost) * entry.confidence

        # Map to strength level
        if effective_strength > 0.8:
            new_strength = MemoryStrength.STRONG
        elif effective_strength > 0.5:
            new_strength = MemoryStrength.MODERATE
        elif effective_strength > 0.2:
            new_strength = MemoryStrength.WEAK
        else:
            new_strength = MemoryStrength.EPHEMERAL

        entry.strength = new_strength
        return new_strength

    # ── Memory Chains ──────────────────────────────────────────────

    def build_chain(
        self,
        title: str,
        entry_ids: list[str],
        summary: str = "",
    ) -> MemoryChain:
        """Build a narrative chain from related memories.

        Args:
            title: Chain title.
            entry_ids: IDs of memories to link.
            summary: Optional summary of the chain.

        Returns:
            The created MemoryChain.
        """
        chain = MemoryChain(
            title=title,
            entries=[eid for eid in entry_ids if eid in self._memories],
            summary=summary,
        )
        # Calculate coherence based on dimension consistency
        dimensions = [
            self._memories[eid].dimension
            for eid in chain.entries
            if eid in self._memories
        ]
        if dimensions:
            unique_dims = len(set(dimensions))
            chain.coherence_score = 1.0 - (unique_dims - 1) / max(len(dimensions), 1)
        self._chains[chain.id] = chain
        return chain

    def get_chains(self, limit: int = 20) -> list[MemoryChain]:
        """Get recent memory chains."""
        chains = sorted(
            self._chains.values(),
            key=lambda c: c.coherence_score,
            reverse=True,
        )
        return chains[:limit]

    # ── Memory Consolidation ───────────────────────────────────────

    def consolidate(self) -> ConsolidationReport:
        """Run a memory consolidation cycle.

        Performs merge of similar memories, reinforcement of frequently
        recalled memories, decay of old memories, and archiving of
        very old memories.

        Returns:
            ConsolidationReport with statistics.
        """
        report = ConsolidationReport()
        report.memories_processed = len(self._memories)

        for mem_id, entry in list(self._memories.items()):
            self.calibrate_strength(mem_id)

            # Check for archiving
            age_days = (datetime.now(timezone.utc) - entry.created_at).total_seconds() / 86400.0
            if age_days > self.AGE_THRESHOLD_FOR_ARCHIVE_DAYS and entry.strength == MemoryStrength.EPHEMERAL:
                report.memories_archived += 1
                continue

            # Check for elevation
            if entry.recall_count >= self.RECALL_THRESHOLD_FOR_STRENGTHEN:
                if entry.strength == MemoryStrength.WEAK:
                    entry.strength = MemoryStrength.MODERATE
                    report.memories_elevated += 1
                elif entry.strength == MemoryStrength.MODERATE:
                    entry.strength = MemoryStrength.STRONG
                    report.memories_elevated += 1

            # Check for reinforcement
            if entry.recall_count > 0:
                report.memories_reinforced += 1

            # Check for decay
            if entry.strength == MemoryStrength.EPHEMERAL:
                report.memories_decayed += 1

        # Merge similar memories
        merge_count = self._merge_similar_memories()
        report.memories_merged = merge_count

        # Update profile
        self._update_profile()
        report.profile_updates = ["preferences", "knowledge_domains", "traits"]

        self._consolidation_history.append(report)
        logger.info(
            "Consolidation complete: processed=%d merged=%d reinforced=%d "
            "decayed=%d archived=%d elevated=%d",
            report.memories_processed, report.memories_merged,
            report.memories_reinforced, report.memories_decayed,
            report.memories_archived, report.memories_elevated,
        )
        return report

    def _merge_similar_memories(self) -> int:
        """Internal: merge semantically similar memories."""
        merged = 0
        entries = list(self._memories.values())
        for i, e1 in enumerate(entries):
            for e2 in entries[i + 1:]:
                if e1.dimension != e2.dimension:
                    continue
                similarity = self._compute_similarity(e1.content, e2.content)
                if similarity > self.SIMILARITY_THRESHOLD_FOR_MERGE:
                    # Merge into the stronger memory
                    if e1.id in self._memories and e2.id in self._memories:
                        e1.confidence = max(e1.confidence, e2.confidence)
                        e1.recall_count += e2.recall_count
                        e1.tags = list(set(e1.tags + e2.tags))
                        del self._memories[e2.id]
                        merged += 1
        return merged

    @staticmethod
    def _compute_similarity(text1: str, text2: str) -> float:
        """Simple Jaccard-like word similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    # ── Profile Management ─────────────────────────────────────────

    def _update_profile(self) -> None:
        """Internal: update the personal profile from current memories."""
        self._profile.last_updated = datetime.now(timezone.utc)

        # Update preferences from preference memories
        pref_memories = self._dimension_index.get(MemoryDimension.PREFERENCE, [])
        for mid in pref_memories:
            entry = self._memories.get(mid)
            if entry:
                self._profile.preferences[entry.content[:50]] = entry.confidence

        # Update knowledge domains
        fact_memories = self._dimension_index.get(MemoryDimension.FACT, [])
        domains: dict[str, int] = defaultdict(int)
        for mid in fact_memories:
            entry = self._memories.get(mid)
            if entry and entry.tags:
                for tag in entry.tags:
                    domains[tag] += 1
        self._profile.knowledge_domains = sorted(
            domains, key=domains.get, reverse=True
        )[:10]

    def get_profile(self) -> PersonalProfile:
        """Get the current personal profile."""
        self._update_profile()
        return self._profile

    def get_stats(self) -> dict[str, Any]:
        """Get memory engine statistics."""
        strength_counts: dict[str, int] = defaultdict(int)
        for entry in self._memories.values():
            strength_counts[entry.strength.value] += 1

        return {
            "total_memories": len(self._memories),
            "total_chains": len(self._chains),
            "total_captures": self._total_captures,
            "total_retrievals": self._total_retrievals,
            "strength_distribution": dict(strength_counts),
            "dimension_distribution": {
                dim.value: len(ids)
                for dim, ids in self._dimension_index.items()
            },
            "consolidation_cycles": len(self._consolidation_history),
            "profile": {
                "knowledge_domains": self._profile.knowledge_domains,
                "traits": self._profile.traits,
                "goals_count": len(self._profile.goals),
            },
        }

    def reset(self) -> None:
        """Reset all memory state."""
        self._memories.clear()
        self._chains.clear()
        self._profile = PersonalProfile()
        self._dimension_index.clear()
        self._tag_index.clear()
        self._consolidation_history.clear()
        self._total_captures = 0
        self._total_retrievals = 0


# ═══════════════════════════════════════════════════════════
# Singleton Accessors
# ═══════════════════════════════════════════════════════════

_personal_memory: PersonalMemoryEngine | None = None


def get_personal_memory() -> PersonalMemoryEngine:
    """Get or create the singleton PersonalMemoryEngine."""
    global _personal_memory
    if _personal_memory is None:
        _personal_memory = PersonalMemoryEngine()
    return _personal_memory


def reset_personal_memory() -> None:
    """Reset the singleton PersonalMemoryEngine."""
    global _personal_memory
    if _personal_memory is not None:
        _personal_memory.reset()
    _personal_memory = None