"""Buddy Federated Knowledge Exchange — Decentralized Agent Knowledge Sharing Network

The Federated Knowledge Exchange enables agents to share, discover, and merge
knowledge across a decentralized federation. It provides:
- Publish/subscribe knowledge distribution with topic-based routing
- Multi-source knowledge merging with automated conflict resolution
- Knowledge provenance tracking with confidence scoring
- TTL-based knowledge expiration and access-level controls
- Federation-wide statistics and observability
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.federated_knowledge")


# ═══════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════

class KnowledgeType(str, Enum):
    """Types of knowledge that can be shared across the federation."""
    FACT = "fact"               # Verified factual information
    PROCEDURE = "procedure"      # Step-by-step operational procedure
    PATTERN = "pattern"          # Recurring pattern or template
    INSIGHT = "insight"          # Derived analytical insight
    WARNING = "warning"          # Cautionary knowledge or risk alert
    PREFERENCE = "preference"    # Agent preference or configuration
    DISCOVERY = "discovery"      # Newly discovered knowledge


class AccessLevel(str, Enum):
    """Access levels for knowledge sharing within the federation."""
    PUBLIC = "public"             # Available to all agents
    FEDERATION = "federation"     # Available within the federation
    TEAM = "team"                 # Available to team members only
    PRIVATE = "private"           # Restricted to the originating agent
    PEER = "peer"                 # Available to directly connected peers


class MergeStrategy(str, Enum):
    """Strategies for merging knowledge from multiple sources."""
    UNION = "union"                  # Combine all unique content
    CONSENSUS = "consensus"          # Only keep content with majority agreement
    CONFIDENCE_WEIGHTED = "weighted" # Weight by confidence scores
    LATEST = "latest"                # Prefer most recent content
    HIGHEST_CONFIDENCE = "highest"   # Keep highest confidence content only
    VOTING = "voting"                # Democratic voting across sources


class ConflictResolutionMethod(str, Enum):
    """Methods for resolving conflicts in merged knowledge."""
    MAJORITY = "majority"              # Accept majority position
    CONFIDENCE_WEIGHTED = "weighted"   # Weight by source confidence
    SOURCE_PRIORITY = "source_priority" # Prefer specific sources
    RECENCY = "recency"                # Prefer newer entries
    HYBRID = "hybrid"                  # Combine multiple methods
    CUSTOM = "custom"                  # Custom resolution logic


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class KnowledgeShare:
    """A single knowledge entry shared by an agent in the federation."""
    id: str
    agent_id: str
    knowledge_type: KnowledgeType
    content: str
    confidence: float
    source_context: str
    tags: list[str]
    created_at: str
    ttl: int
    access_level: AccessLevel
    version: int

    def is_expired(self) -> bool:
        """Check if this knowledge share has exceeded its TTL."""
        if self.ttl <= 0:
            return False
        created = datetime.fromisoformat(self.created_at)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        return elapsed > self.ttl

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "knowledge_type": self.knowledge_type.value,
            "content": self.content,
            "confidence": self.confidence,
            "source_context": self.source_context,
            "tags": self.tags,
            "created_at": self.created_at,
            "ttl": self.ttl,
            "access_level": self.access_level.value,
            "version": self.version,
        }


@dataclass
class Subscription:
    """A subscription to one or more knowledge topics."""
    id: str
    agent_id: str
    topics: list[str]
    created_at: str
    active: bool

    def matches_topic(self, topic: str) -> bool:
        """Check if this subscription includes the given topic."""
        return self.active and topic in self.topics


@dataclass
class PublishedEntry:
    """A knowledge entry published to a specific topic."""
    id: str
    topic: str
    knowledge: KnowledgeShare
    publisher_id: str
    published_at: str


@dataclass
class MergedKnowledge:
    """Result of merging multiple knowledge shares."""
    sources: list[KnowledgeShare]
    unified_content: str
    conflicts: list[dict[str, Any]]
    confidence: float
    merge_strategy: MergeStrategy


@dataclass
class ResolvedKnowledge:
    """Result of resolving conflicts in merged knowledge."""
    merged: MergedKnowledge
    resolutions: list[dict[str, Any]]
    final_content: str
    confidence: float
    resolution_method: ConflictResolutionMethod


@dataclass
class FederationStats:
    """Statistics about the federated knowledge exchange."""
    total_shares: int
    total_subscriptions: int
    active_topics: int
    knowledge_exchange_rate: float


# ═══════════════════════════════════════════════════════════════
# Federated Knowledge Exchange Engine
# ═══════════════════════════════════════════════════════════════

class FederatedKnowledgeExchange:
    """Decentralized knowledge exchange for the Buddy agent federation.

    Manages knowledge sharing, subscription-based distribution, multi-source
    merging, and automated conflict resolution across all participating agents.
    """

    DEFAULT_TTL = 86400  # 24 hours in seconds
    DEFAULT_CONFIDENCE = 0.5

    def __init__(self):
        self._shares: dict[str, KnowledgeShare] = {}
        self._subscriptions: dict[str, Subscription] = {}
        self._topics: dict[str, list[PublishedEntry]] = {}
        self._share_count: int = 0
        self._exchange_timestamps: list[float] = []

    # ── Core Knowledge Operations ──────────────────────────────────

    def share_knowledge(
        self,
        agent_id: str,
        knowledge_type: KnowledgeType,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> KnowledgeShare:
        """Share a piece of knowledge from an agent into the federation.

        Args:
            agent_id: Identifier of the sharing agent.
            knowledge_type: The type of knowledge being shared.
            content: The knowledge content string.
            metadata: Optional metadata including tags, confidence, ttl,
                      access_level, source_context, and version.

        Returns:
            The created KnowledgeShare entry.
        """
        meta = metadata or {}

        share_id = uuid.uuid4().hex[:12]
        share = KnowledgeShare(
            id=share_id,
            agent_id=agent_id,
            knowledge_type=knowledge_type,
            content=content,
            confidence=meta.get("confidence", self.DEFAULT_CONFIDENCE),
            source_context=meta.get("source_context", ""),
            tags=meta.get("tags", []),
            created_at=meta.get("created_at", datetime.now(timezone.utc).isoformat()),
            ttl=meta.get("ttl", self.DEFAULT_TTL),
            access_level=meta.get("access_level", AccessLevel.FEDERATION),
            version=meta.get("version", 1),
        )

        self._shares[share_id] = share
        self._share_count += 1
        self._exchange_timestamps.append(datetime.now(timezone.utc).timestamp())

        logger.info(
            "Knowledge shared: agent=%s type=%s id=%s",
            agent_id, knowledge_type.value, share_id,
        )
        return share

    def request_knowledge(
        self,
        agent_id: str,
        query: str,
        knowledge_type: Optional[KnowledgeType] = None,
    ) -> list[KnowledgeShare]:
        """Request knowledge from the federation matching a query.

        Searches across all shared knowledge, filtering by type if specified,
        and respecting access levels and TTL expiration.

        Args:
            agent_id: Identifier of the requesting agent.
            query: Search query string to match against content and tags.
            knowledge_type: Optional filter for specific knowledge type.

        Returns:
            A list of matching KnowledgeShare entries.
        """
        results: list[KnowledgeShare] = []
        query_lower = query.lower()

        for share in self._shares.values():
            if share.is_expired():
                continue

            if not self._can_access(agent_id, share):
                continue

            if knowledge_type is not None and share.knowledge_type != knowledge_type:
                continue

            matches_content = query_lower in share.content.lower()
            matches_tags = any(query_lower in tag.lower() for tag in share.tags)
            if matches_content or matches_tags:
                results.append(share)

        results.sort(key=lambda s: s.confidence, reverse=True)
        logger.info(
            "Knowledge requested: agent=%s query='%s' results=%d",
            agent_id, query, len(results),
        )
        return results

    # ── Publish / Subscribe System ─────────────────────────────────

    def subscribe(self, agent_id: str, topics: list[str]) -> Subscription:
        """Subscribe an agent to one or more knowledge topics.

        If the agent already has an active subscription, it merges the new
        topics into the existing subscription.

        Args:
            agent_id: Identifier of the subscribing agent.
            topics: List of topic strings to subscribe to.

        Returns:
            The created or updated Subscription.
        """
        existing = self._find_active_subscription(agent_id)
        if existing is not None:
            merged_topics = list(set(existing.topics) | set(topics))
            existing.topics = merged_topics
            logger.info(
                "Subscription updated: agent=%s topics=%s",
                agent_id, topics,
            )
            return existing

        sub_id = uuid.uuid4().hex[:12]
        subscription = Subscription(
            id=sub_id,
            agent_id=agent_id,
            topics=topics,
            created_at=datetime.now(timezone.utc).isoformat(),
            active=True,
        )
        self._subscriptions[sub_id] = subscription

        logger.info(
            "Subscription created: agent=%s topics=%s id=%s",
            agent_id, topics, sub_id,
        )
        return subscription

    def publish(
        self,
        agent_id: str,
        topic: str,
        knowledge: KnowledgeShare,
    ) -> PublishedEntry:
        """Publish knowledge to a specific topic for subscribers.

        Args:
            agent_id: Identifier of the publishing agent.
            topic: The topic to publish to.
            knowledge: The KnowledgeShare entry to publish.

        Returns:
            The PublishedEntry with delivery metadata.
        """
        entry_id = uuid.uuid4().hex[:12]
        entry = PublishedEntry(
            id=entry_id,
            topic=topic,
            knowledge=knowledge,
            publisher_id=agent_id,
            published_at=datetime.now(timezone.utc).isoformat(),
        )

        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(entry)

        self._share_count += 1
        self._exchange_timestamps.append(datetime.now(timezone.utc).timestamp())

        logger.info(
            "Published to topic: agent=%s topic=%s entry=%s",
            agent_id, topic, entry_id,
        )
        return entry

    def get_topic_entries(
        self,
        agent_id: str,
        topic: str,
        limit: int = 50,
    ) -> list[PublishedEntry]:
        """Retrieve published entries for a topic that the agent can access.

        Args:
            agent_id: Identifier of the requesting agent.
            topic: The topic to retrieve entries for.
            limit: Maximum number of entries to return.

        Returns:
            A list of accessible PublishedEntry objects.
        """
        entries = self._topics.get(topic, [])
        accessible = [
            e for e in entries
            if not e.knowledge.is_expired()
            and self._can_access(agent_id, e.knowledge)
        ]
        return accessible[-limit:]

    # ── Knowledge Merging ──────────────────────────────────────────

    def merge_knowledge(
        self,
        shares: list[KnowledgeShare],
        strategy: MergeStrategy = MergeStrategy.CONFIDENCE_WEIGHTED,
    ) -> MergedKnowledge:
        """Merge multiple knowledge shares into a unified representation.

        Applies the specified merge strategy to combine content from multiple
        sources while detecting and recording conflicts.

        Args:
            shares: List of KnowledgeShare entries to merge.
            strategy: The merge strategy to apply.

        Returns:
            A MergedKnowledge object containing the unified result.
        """
        if not shares:
            return MergedKnowledge(
                sources=[],
                unified_content="",
                conflicts=[],
                confidence=0.0,
                merge_strategy=strategy,
            )

        active_shares = [s for s in shares if not s.is_expired()]
        if not active_shares:
            return MergedKnowledge(
                sources=shares,
                unified_content="",
                conflicts=[],
                confidence=0.0,
                merge_strategy=strategy,
            )

        conflicts = self._detect_conflicts(active_shares)

        if strategy == MergeStrategy.UNION:
            unified = self._merge_union(active_shares)
        elif strategy == MergeStrategy.CONSENSUS:
            unified = self._merge_consensus(active_shares)
        elif strategy == MergeStrategy.CONFIDENCE_WEIGHTED:
            unified = self._merge_confidence_weighted(active_shares)
        elif strategy == MergeStrategy.LATEST:
            unified = self._merge_latest(active_shares)
        elif strategy == MergeStrategy.HIGHEST_CONFIDENCE:
            unified = self._merge_highest_confidence(active_shares)
        elif strategy == MergeStrategy.VOTING:
            unified = self._merge_voting(active_shares)
        else:
            unified = self._merge_confidence_weighted(active_shares)

        avg_confidence = (
            sum(s.confidence for s in active_shares) / len(active_shares)
        )

        return MergedKnowledge(
            sources=active_shares,
            unified_content=unified,
            conflicts=conflicts,
            confidence=round(avg_confidence, 4),
            merge_strategy=strategy,
        )

    def resolve_conflicts(
        self,
        merged: MergedKnowledge,
        method: ConflictResolutionMethod = ConflictResolutionMethod.CONFIDENCE_WEIGHTED,
    ) -> ResolvedKnowledge:
        """Resolve conflicts in merged knowledge using the specified method.

        Args:
            merged: The MergedKnowledge containing conflicts to resolve.
            method: The conflict resolution method to apply.

        Returns:
            A ResolvedKnowledge object with resolved content and metadata.
        """
        if not merged.conflicts:
            return ResolvedKnowledge(
                merged=merged,
                resolutions=[],
                final_content=merged.unified_content,
                confidence=merged.confidence,
                resolution_method=method,
            )

        resolutions: list[dict[str, Any]] = []

        if method == ConflictResolutionMethod.MAJORITY:
            final_content = self._resolve_majority(merged, resolutions)
        elif method == ConflictResolutionMethod.CONFIDENCE_WEIGHTED:
            final_content = self._resolve_confidence_weighted(merged, resolutions)
        elif method == ConflictResolutionMethod.SOURCE_PRIORITY:
            final_content = self._resolve_source_priority(merged, resolutions)
        elif method == ConflictResolutionMethod.RECENCY:
            final_content = self._resolve_recency(merged, resolutions)
        elif method == ConflictResolutionMethod.HYBRID:
            final_content = self._resolve_hybrid(merged, resolutions)
        else:
            final_content = self._resolve_confidence_weighted(merged, resolutions)

        resolution_confidence = self._compute_resolution_confidence(
            merged, resolutions
        )

        return ResolvedKnowledge(
            merged=merged,
            resolutions=resolutions,
            final_content=final_content,
            confidence=round(resolution_confidence, 4),
            resolution_method=method,
        )

    # ── Statistics ─────────────────────────────────────────────────

    def get_federation_stats(self) -> FederationStats:
        """Compute federation-wide statistics.

        Returns:
            A FederationStats object with current federation metrics.
        """
        active_topics = {t for t, entries in self._topics.items() if entries}
        active_subs = [s for s in self._subscriptions.values() if s.active]

        now = datetime.now(timezone.utc).timestamp()
        recent_window = 3600  # 1 hour
        recent_exchanges = sum(
            1 for ts in self._exchange_timestamps
            if now - ts <= recent_window
        )
        exchange_rate = recent_exchanges / 3600.0 if recent_exchanges > 0 else 0.0

        return FederationStats(
            total_shares=self._share_count,
            total_subscriptions=len(active_subs),
            active_topics=len(active_topics),
            knowledge_exchange_rate=round(exchange_rate, 4),
        )

    def reset(self) -> None:
        """Clear all federation state including shares, subscriptions, and topics."""
        self._shares.clear()
        self._subscriptions.clear()
        self._topics.clear()
        self._share_count = 0
        self._exchange_timestamps.clear()
        logger.info("Federated knowledge exchange state has been reset.")

    # ── Internal Helpers ───────────────────────────────────────────

    def _can_access(self, agent_id: str, share: KnowledgeShare) -> bool:
        """Determine if an agent can access a knowledge share."""
        if share.access_level == AccessLevel.PUBLIC:
            return True
        if share.access_level == AccessLevel.FEDERATION:
            return True
        if share.access_level == AccessLevel.PRIVATE:
            return share.agent_id == agent_id
        if share.access_level == AccessLevel.TEAM:
            return True
        if share.access_level == AccessLevel.PEER:
            return True
        return True

    def _find_active_subscription(self, agent_id: str) -> Optional[Subscription]:
        """Find an active subscription for the given agent."""
        for sub in self._subscriptions.values():
            if sub.agent_id == agent_id and sub.active:
                return sub
        return None

    def _detect_conflicts(
        self, shares: list[KnowledgeShare]
    ) -> list[dict[str, Any]]:
        """Detect content conflicts across multiple knowledge shares."""
        conflicts: list[dict[str, Any]] = []
        seen: dict[str, list[KnowledgeShare]] = {}

        for share in shares:
            key = share.knowledge_type.value
            if key not in seen:
                seen[key] = []
            seen[key].append(share)

        for key, group in seen.items():
            if len(group) < 2:
                continue
            contents = {s.content for s in group}
            if len(contents) > 1:
                conflicts.append({
                    "type": "content_divergence",
                    "knowledge_type": key,
                    "source_count": len(group),
                    "unique_contents": len(contents),
                    "sources": [
                        {"agent_id": s.agent_id, "content": s.content[:100]}
                        for s in group
                    ],
                })

        return conflicts

    def _merge_union(self, shares: list[KnowledgeShare]) -> str:
        """Merge by concatenating all unique content."""
        seen = set()
        parts = []
        for share in shares:
            if share.content not in seen:
                seen.add(share.content)
                parts.append(f"[{share.agent_id}]: {share.content}")
        return "\n\n".join(parts)

    def _merge_consensus(self, shares: list[KnowledgeShare]) -> str:
        """Merge by selecting content that appears most frequently."""
        content_counts: dict[str, int] = {}
        for share in shares:
            content_counts[share.content] = content_counts.get(share.content, 0) + 1

        best_content = max(content_counts, key=content_counts.get)
        return best_content

    def _merge_confidence_weighted(self, shares: list[KnowledgeShare]) -> str:
        """Merge by selecting content from the highest confidence source."""
        if not shares:
            return ""
        best = max(shares, key=lambda s: s.confidence)
        return best.content

    def _merge_latest(self, shares: list[KnowledgeShare]) -> str:
        """Merge by selecting the most recently created content."""
        if not shares:
            return ""
        latest = max(shares, key=lambda s: s.created_at)
        return latest.content

    def _merge_highest_confidence(self, shares: list[KnowledgeShare]) -> str:
        """Merge by selecting the highest confidence content (same as weighted)."""
        return self._merge_confidence_weighted(shares)

    def _merge_voting(self, shares: list[KnowledgeShare]) -> str:
        """Merge by democratic voting across sources."""
        if not shares:
            return ""
        content_votes: dict[str, float] = {}
        for share in shares:
            content_votes[share.content] = (
                content_votes.get(share.content, 0.0) + share.confidence
            )
        best = max(content_votes, key=content_votes.get)
        return best

    def _resolve_majority(
        self,
        merged: MergedKnowledge,
        resolutions: list[dict[str, Any]],
    ) -> str:
        """Resolve conflicts by majority vote."""
        content = merged.unified_content
        for conflict in merged.conflicts:
            sources = conflict.get("sources", [])
            agent_votes: dict[str, int] = {}
            for src in sources:
                c = src.get("content", "")
                agent_votes[c] = agent_votes.get(c, 0) + 1

            if agent_votes:
                winner = max(agent_votes, key=agent_votes.get)
                resolutions.append({
                    "conflict": conflict["type"],
                    "method": "majority",
                    "selected": winner[:100],
                    "votes": agent_votes,
                })
                content = winner
        return content

    def _resolve_confidence_weighted(
        self,
        merged: MergedKnowledge,
        resolutions: list[dict[str, Any]],
    ) -> str:
        """Resolve conflicts by confidence-weighted selection."""
        if not merged.sources:
            return merged.unified_content

        best = max(merged.sources, key=lambda s: s.confidence)
        for conflict in merged.conflicts:
            resolutions.append({
                "conflict": conflict["type"],
                "method": "confidence_weighted",
                "selected_source": best.agent_id,
                "confidence": best.confidence,
            })
        return best.content

    def _resolve_source_priority(
        self,
        merged: MergedKnowledge,
        resolutions: list[dict[str, Any]],
    ) -> str:
        """Resolve by preferring the first source."""
        if not merged.sources:
            return merged.unified_content

        first = merged.sources[0]
        for conflict in merged.conflicts:
            resolutions.append({
                "conflict": conflict["type"],
                "method": "source_priority",
                "selected_source": first.agent_id,
            })
        return first.content

    def _resolve_recency(
        self,
        merged: MergedKnowledge,
        resolutions: list[dict[str, Any]],
    ) -> str:
        """Resolve by preferring the most recent source."""
        if not merged.sources:
            return merged.unified_content

        latest = max(merged.sources, key=lambda s: s.created_at)
        for conflict in merged.conflicts:
            resolutions.append({
                "conflict": conflict["type"],
                "method": "recency",
                "selected_source": latest.agent_id,
                "created_at": latest.created_at,
            })
        return latest.content

    def _resolve_hybrid(
        self,
        merged: MergedKnowledge,
        resolutions: list[dict[str, Any]],
    ) -> str:
        """Resolve by combining confidence-weighted and recency approaches."""
        if not merged.sources:
            return merged.unified_content

        now = datetime.now(timezone.utc)
        scored: list[tuple[KnowledgeShare, float]] = []

        for share in merged.sources:
            created = datetime.fromisoformat(share.created_at)
            age_seconds = (now - created).total_seconds()
            recency_score = max(0.0, 1.0 - (age_seconds / self.DEFAULT_TTL))
            combined_score = (share.confidence * 0.6) + (recency_score * 0.4)
            scored.append((share, combined_score))

        best = max(scored, key=lambda x: x[1])[0]

        for conflict in merged.conflicts:
            resolutions.append({
                "conflict": conflict["type"],
                "method": "hybrid",
                "selected_source": best.agent_id,
                "confidence": best.confidence,
            })
        return best.content

    def _compute_resolution_confidence(
        self,
        merged: MergedKnowledge,
        resolutions: list[dict[str, Any]],
    ) -> float:
        """Compute confidence after conflict resolution."""
        if not resolutions:
            return merged.confidence

        resolution_bonus = min(len(resolutions) * 0.02, 0.1)
        base = merged.confidence
        if len(merged.sources) > 1:
            base = base * 0.95

        return min(1.0, base + resolution_bonus)


# ═══════════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════════

_federated_knowledge_instance: FederatedKnowledgeExchange | None = None


def get_federated_knowledge() -> FederatedKnowledgeExchange:
    """Get the global FederatedKnowledgeExchange singleton.

    Creates a new instance on first call, returns the existing instance
    on subsequent calls.

    Returns:
        The global FederatedKnowledgeExchange singleton.
    """
    global _federated_knowledge_instance
    if _federated_knowledge_instance is None:
        _federated_knowledge_instance = FederatedKnowledgeExchange()
    return _federated_knowledge_instance


def reset_federated_knowledge() -> None:
    """Reset the global FederatedKnowledgeExchange singleton.

    Destroys the current instance and clears all internal state.
    A new instance will be created on the next call to get_federated_knowledge().
    """
    global _federated_knowledge_instance
    if _federated_knowledge_instance is not None:
        _federated_knowledge_instance.reset()
    _federated_knowledge_instance = None