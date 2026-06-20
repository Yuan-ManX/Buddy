"""
Buddy Knowledge Network - Cross-agent knowledge sharing system.

Enables agents to share insights, discoveries, and learnings across
the platform. Creates a distributed knowledge graph where agents can
publish findings, subscribe to topics, and collaboratively build a
shared knowledge base.

Key capabilities:
- Knowledge publishing with verification and confidence scoring
- Topic-based knowledge subscription and discovery
- Cross-agent insight synthesis and conflict resolution
- Knowledge provenance tracking with agent attribution
- Collaborative knowledge graph construction
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class KnowledgeType(str, Enum):
    """Types of knowledge entries in the network."""
    FACT = "fact"
    INSIGHT = "insight"
    PATTERN = "pattern"
    STRATEGY = "strategy"
    WARNING = "warning"
    DISCOVERY = "discovery"
    BEST_PRACTICE = "best_practice"


class KnowledgeStatus(str, Enum):
    """Status of a knowledge entry."""
    PROPOSED = "proposed"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class VerificationLevel(str, Enum):
    """Level of verification for a knowledge entry."""
    UNVERIFIED = "unverified"
    SELF_VERIFIED = "self_verified"
    PEER_VERIFIED = "peer_verified"
    CONSENSUS = "consensus"
    PROVEN = "proven"


@dataclass
class KnowledgeEntry:
    """A single knowledge entry in the network."""
    entry_id: str
    knowledge_type: KnowledgeType
    topic: str
    content: str
    source_agent_id: str
    source_agent_name: str
    confidence: float
    status: KnowledgeStatus = KnowledgeStatus.PROPOSED
    verification_level: VerificationLevel = VerificationLevel.UNVERIFIED
    verifications: list[dict] = field(default_factory=list)
    related_entries: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class KnowledgeTopic:
    """A topic hub for organizing knowledge."""
    topic_id: str
    name: str
    description: str
    parent_topic_id: str | None = None
    entry_count: int = 0
    subscriber_count: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class KnowledgeSubscription:
    """An agent's subscription to a knowledge topic."""
    subscription_id: str
    agent_id: str
    topic_id: str
    min_confidence: float = 0.5
    knowledge_types: list[KnowledgeType] | None = None
    notify_on_new: bool = True
    created_at: float = field(default_factory=time.time)


class KnowledgeNetwork:
    """Cross-agent knowledge sharing network for the Buddy platform.

    Enables agents to publish, discover, verify, and synthesize knowledge
    across the platform. Maintains a distributed knowledge graph with
    provenance tracking and collaborative verification.
    """

    def __init__(self):
        self._entries: dict[str, KnowledgeEntry] = {}
        self._topics: dict[str, KnowledgeTopic] = {}
        self._subscriptions: dict[str, KnowledgeSubscription] = {}
        self._topic_index: dict[str, list[str]] = {}  # topic_id -> entry_ids
        self._agent_contributions: dict[str, list[str]] = {}  # agent_id -> entry_ids
        self._total_entries = 0
        self._total_verifications = 0

    def create_topic(
        self,
        name: str,
        description: str = "",
        parent_topic_id: str | None = None,
    ) -> KnowledgeTopic:
        """Create a new knowledge topic."""
        topic_id = f"ktopic-{uuid.uuid4().hex[:12]}"
        topic = KnowledgeTopic(
            topic_id=topic_id,
            name=name,
            description=description,
            parent_topic_id=parent_topic_id,
        )
        self._topics[topic_id] = topic
        self._topic_index[topic_id] = []
        return topic

    def publish(
        self,
        knowledge_type: KnowledgeType,
        topic: str,
        content: str,
        source_agent_id: str,
        source_agent_name: str,
        confidence: float = 0.5,
        tags: list[str] | None = None,
        evidence: list[str] | None = None,
    ) -> KnowledgeEntry:
        """Publish a knowledge entry to the network."""
        entry_id = f"kentry-{uuid.uuid4().hex[:12]}"
        entry = KnowledgeEntry(
            entry_id=entry_id,
            knowledge_type=knowledge_type,
            topic=topic,
            content=content,
            source_agent_id=source_agent_id,
            source_agent_name=source_agent_name,
            confidence=confidence,
            tags=tags or [],
            evidence=evidence or [],
        )
        self._entries[entry_id] = entry
        self._total_entries += 1

        # Index by topic
        if topic not in self._topic_index:
            self._topic_index[topic] = []
        self._topic_index[topic].append(entry_id)

        # Track agent contributions
        if source_agent_id not in self._agent_contributions:
            self._agent_contributions[source_agent_id] = []
        self._agent_contributions[source_agent_id].append(entry_id)

        # Update topic counts
        for tid, topic_obj in self._topics.items():
            if topic_obj.name == topic:
                topic_obj.entry_count += 1

        return entry

    def verify(
        self,
        entry_id: str,
        verifying_agent_id: str,
        verifying_agent_name: str,
        agreement: bool,
        confidence: float = 0.5,
        comment: str = "",
    ) -> KnowledgeEntry | None:
        """Submit a verification for a knowledge entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            return None

        entry.verifications.append({
            "agent_id": verifying_agent_id,
            "agent_name": verifying_agent_name,
            "agreement": agreement,
            "confidence": confidence,
            "comment": comment,
            "timestamp": time.time(),
        })
        self._total_verifications += 1

        # Update verification level based on number of verifications
        verify_count = len(entry.verifications)
        agree_count = sum(1 for v in entry.verifications if v["agreement"])
        disagree_count = verify_count - agree_count

        if verify_count >= 5 and agree_count / verify_count >= 0.8:
            entry.verification_level = VerificationLevel.CONSENSUS
            entry.status = KnowledgeStatus.ACCEPTED
        elif verify_count >= 2 and agree_count / verify_count >= 0.8:
            entry.verification_level = VerificationLevel.PEER_VERIFIED
            entry.status = KnowledgeStatus.VERIFIED
        elif verify_count >= 1:
            entry.verification_level = VerificationLevel.SELF_VERIFIED

        if disagree_count > agree_count:
            entry.status = KnowledgeStatus.DISPUTED

        entry.updated_at = time.time()
        return entry

    def supersede(
        self, old_entry_id: str, new_entry_id: str
    ) -> bool:
        """Mark an entry as superseded by a newer entry."""
        old_entry = self._entries.get(old_entry_id)
        new_entry = self._entries.get(new_entry_id)
        if not old_entry or not new_entry:
            return False

        old_entry.status = KnowledgeStatus.SUPERSEDED
        old_entry.superseded_by = new_entry_id
        old_entry.updated_at = time.time()
        new_entry.related_entries.append(old_entry_id)
        return True

    def subscribe(
        self,
        agent_id: str,
        topic_id: str,
        min_confidence: float = 0.5,
        knowledge_types: list[KnowledgeType] | None = None,
    ) -> KnowledgeSubscription:
        """Subscribe an agent to a knowledge topic."""
        sub_id = f"ksub-{uuid.uuid4().hex[:12]}"
        subscription = KnowledgeSubscription(
            subscription_id=sub_id,
            agent_id=agent_id,
            topic_id=topic_id,
            min_confidence=min_confidence,
            knowledge_types=knowledge_types,
        )
        self._subscriptions[sub_id] = subscription

        # Update topic subscriber count
        topic = self._topics.get(topic_id)
        if topic:
            topic.subscriber_count += 1

        return subscription

    def query(
        self,
        topic: str | None = None,
        knowledge_type: KnowledgeType | None = None,
        min_confidence: float = 0.0,
        status: KnowledgeStatus | None = None,
        source_agent_id: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[KnowledgeEntry]:
        """Query knowledge entries with filters."""
        results = list(self._entries.values())

        if topic:
            results = [e for e in results if e.topic == topic]
        if knowledge_type:
            results = [e for e in results if e.knowledge_type == knowledge_type]
        if min_confidence > 0:
            results = [e for e in results if e.confidence >= min_confidence]
        if status:
            results = [e for e in results if e.status == status]
        if source_agent_id:
            results = [e for e in results if e.source_agent_id == source_agent_id]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]

        results.sort(key=lambda e: e.confidence * (1 + e.access_count * 0.01), reverse=True)

        # Track access
        for entry in results[:limit]:
            entry.access_count += 1

        return results[:limit]

    def get_agent_contributions(
        self, agent_id: str, limit: int = 50
    ) -> list[KnowledgeEntry]:
        """Get all knowledge contributions from an agent."""
        entry_ids = self._agent_contributions.get(agent_id, [])
        entries = [
            self._entries[eid] for eid in entry_ids
            if eid in self._entries
        ]
        return sorted(entries, key=lambda e: e.created_at, reverse=True)[:limit]

    def get_topic_entries(
        self, topic_name: str, limit: int = 50
    ) -> list[KnowledgeEntry]:
        """Get all entries for a topic."""
        entry_ids = self._topic_index.get(topic_name, [])
        entries = [
            self._entries[eid] for eid in entry_ids
            if eid in self._entries
        ]
        return sorted(entries, key=lambda e: e.created_at, reverse=True)[:limit]

    def get_stats(self) -> dict:
        """Get knowledge network statistics."""
        return {
            "total_entries": self._total_entries,
            "total_verifications": self._total_verifications,
            "total_topics": len(self._topics),
            "total_subscriptions": len(self._subscriptions),
            "active_contributors": len(self._agent_contributions),
            "entries_by_type": self._count_by_type(),
            "entries_by_status": self._count_by_status(),
            "entries_by_verification": self._count_by_verification(),
            "top_contributors": self._get_top_contributors(10),
            "topics": [
                {
                    "topic_id": t.topic_id,
                    "name": t.name,
                    "entry_count": t.entry_count,
                    "subscriber_count": t.subscriber_count,
                }
                for t in self._topics.values()
            ],
        }

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self._entries.values():
            t = entry.knowledge_type.value
            counts[t] = counts.get(t, 0) + 1
        return counts

    def _count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self._entries.values():
            s = entry.status.value
            counts[s] = counts.get(s, 0) + 1
        return counts

    def _count_by_verification(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self._entries.values():
            v = entry.verification_level.value
            counts[v] = counts.get(v, 0) + 1
        return counts

    def _get_top_contributors(self, limit: int) -> list[dict]:
        contributors = [
            (aid, len(entries))
            for aid, entries in self._agent_contributions.items()
        ]
        contributors.sort(key=lambda x: x[1], reverse=True)
        return [
            {"agent_id": aid, "contributions": count}
            for aid, count in contributors[:limit]
        ]


# Global singleton
knowledge_network = KnowledgeNetwork()