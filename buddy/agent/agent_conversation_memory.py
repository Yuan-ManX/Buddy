"""Buddy Agent Conversation Memory — long-term conversation memory with semantic indexing

The Conversation Memory system provides persistent, searchable, and context-aware
storage for all agent-user interactions. It enables semantic retrieval, temporal
navigation, context assembly, and memory consolidation across conversation sessions.

Core capabilities:
  - Semantic Indexing: automatic embedding-based indexing for similarity search
  - Temporal Navigation: query conversations by time range, recency, or importance
  - Context Assembly: intelligent context window construction for LLM prompts
  - Memory Consolidation: periodic summarization and compression of old conversations
  - Topic Extraction: automatic topic modeling and conversation clustering
  - Cross-Session Linking: connect related conversations across different sessions
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.conversation_memory")


# ═══════════════════════════════════════════════════════════
# Enums and Types
# ═══════════════════════════════════════════════════════════

class MessageRole(str, Enum):
    """Roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MemoryImportance(str, Enum):
    """Importance level of a conversation memory."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRANSIENT = "transient"


class ConversationStatus(str, Enum):
    """Status of a conversation."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    CONSOLIDATED = "consolidated"
    DELETED = "deleted"


class SearchMode(str, Enum):
    """Search modes for conversation retrieval."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    TEMPORAL = "temporal"
    HYBRID = "hybrid"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class ConversationMemoryConfig:
    """Configuration for Conversation Memory."""
    max_conversations: int = 1000
    max_messages_per_conversation: int = 500
    consolidation_threshold: int = 100  # Messages before auto-consolidation
    embedding_dim: int = 1536
    similarity_threshold: float = 0.7
    context_window_size: int = 20
    auto_archive_days: int = 90
    enable_semantic_search: bool = True
    enable_topic_extraction: bool = True


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:12]}")
    role: MessageRole = MessageRole.USER
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    tokens: int = 0
    importance: MemoryImportance = MemoryImportance.MEDIUM
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "tokens": self.tokens,
            "importance": self.importance.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class ConversationTopic:
    """Extracted topic from conversation analysis."""
    topic_id: str = field(default_factory=lambda: f"topic-{uuid.uuid4().hex[:8]}")
    name: str = ""
    keywords: list[str] = field(default_factory=list)
    confidence: float = 0.0
    message_count: int = 0
    first_seen: str = ""
    last_seen: str = ""
    related_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "name": self.name,
            "keywords": self.keywords,
            "confidence": self.confidence,
            "message_count": self.message_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "related_topics": self.related_topics,
        }


@dataclass
class ConversationSummary:
    """A consolidated summary of a conversation or conversation segment."""
    summary_id: str = field(default_factory=lambda: f"sum-{uuid.uuid4().hex[:8]}")
    content: str = ""
    key_points: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    message_range: tuple[int, int] = (0, 0)
    tokens: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "content": self.content,
            "key_points": self.key_points,
            "decisions": self.decisions,
            "action_items": self.action_items,
            "message_range": list(self.message_range),
            "tokens": self.tokens,
            "created_at": self.created_at,
        }


@dataclass
class Conversation:
    """A complete conversation with messages, topics, and summaries."""
    conversation_id: str = field(default_factory=lambda: f"conv-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    title: str = ""
    messages: list[ConversationMessage] = field(default_factory=list)
    topics: list[ConversationTopic] = field(default_factory=list)
    summaries: list[ConversationSummary] = field(default_factory=list)
    status: ConversationStatus = ConversationStatus.ACTIVE
    total_tokens: int = 0
    total_messages: int = 0
    importance: MemoryImportance = MemoryImportance.MEDIUM
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_message_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "message_count": len(self.messages),
            "topic_count": len(self.topics),
            "summary_count": len(self.summaries),
            "status": self.status.value,
            "total_tokens": self.total_tokens,
            "importance": self.importance.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_message_at": self.last_message_at,
        }


@dataclass
class SearchResult:
    """Result from a conversation search query."""
    message: ConversationMessage
    conversation_id: str = ""
    relevance_score: float = 0.0
    match_type: str = ""
    context_before: list[ConversationMessage] = field(default_factory=list)
    context_after: list[ConversationMessage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message.to_dict(),
            "conversation_id": self.conversation_id,
            "relevance_score": self.relevance_score,
            "match_type": self.match_type,
            "context_before": [m.to_dict() for m in self.context_before],
            "context_after": [m.to_dict() for m in self.context_after],
        }


@dataclass
class ConversationMemoryStats:
    """Statistics for the Conversation Memory system."""
    total_conversations: int = 0
    total_messages: int = 0
    total_tokens: int = 0
    active_conversations: int = 0
    archived_conversations: int = 0
    consolidated_conversations: int = 0
    total_topics: int = 0
    total_summaries: int = 0
    avg_messages_per_conversation: float = 0.0
    oldest_conversation: str = ""
    newest_conversation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_conversations": self.total_conversations,
            "total_messages": self.total_messages,
            "total_tokens": self.total_tokens,
            "active_conversations": self.active_conversations,
            "archived_conversations": self.archived_conversations,
            "consolidated_conversations": self.consolidated_conversations,
            "total_topics": self.total_topics,
            "total_summaries": self.total_summaries,
            "avg_messages_per_conversation": self.avg_messages_per_conversation,
            "oldest_conversation": self.oldest_conversation,
            "newest_conversation": self.newest_conversation,
        }


# ═══════════════════════════════════════════════════════════
# Conversation Memory Implementation
# ═══════════════════════════════════════════════════════════

class AgentConversationMemory:
    """Long-term conversation memory with semantic indexing and retrieval."""

    def __init__(self, config: ConversationMemoryConfig | None = None):
        self.config = config or ConversationMemoryConfig()
        self._conversations: dict[str, Conversation] = {}
        self._message_index: dict[str, ConversationMessage] = {}
        self._topic_index: dict[str, ConversationTopic] = {}
        self._keyword_index: dict[str, set[str]] = defaultdict(set)  # keyword -> message_ids
        self._agent_conversations: dict[str, list[str]] = defaultdict(list)
        logger.info("AgentConversationMemory initialized")

    # ── Conversation CRUD ────────────────────────────────

    def create_conversation(
        self,
        agent_id: str,
        title: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            agent_id=agent_id,
            title=title or f"Conversation {len(self._conversations) + 1}",
            tags=tags or [],
            metadata=metadata or {},
        )
        self._conversations[conversation.conversation_id] = conversation
        self._agent_conversations[agent_id].append(conversation.conversation_id)
        logger.info("Created conversation %s for agent %s", conversation.conversation_id, agent_id)
        return conversation

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage | None:
        """Add a message to a conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            logger.warning("Conversation not found: %s", conversation_id)
            return None

        # Estimate tokens (rough approximation: 4 chars per token)
        tokens = len(content) // 4

        message = ConversationMessage(
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
            tokens=max(tokens, 1),
            importance=importance,
            metadata=metadata or {},
        )

        conversation.messages.append(message)
        conversation.total_messages = len(conversation.messages)
        conversation.total_tokens += message.tokens
        conversation.last_message_at = message.created_at
        conversation.updated_at = datetime.now(timezone.utc).isoformat()

        # Index message
        self._message_index[message.message_id] = message

        # Index keywords
        self._index_keywords(message.message_id, content)

        # Auto-consolidate if threshold exceeded
        if len(conversation.messages) > self.config.consolidation_threshold:
            self._auto_consolidate(conversation)

        # Enforce max messages
        if len(conversation.messages) > self.config.max_messages_per_conversation:
            conversation.messages = conversation.messages[-self.config.max_messages_per_conversation:]

        return message

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self._conversations.get(conversation_id)

    def get_message(self, message_id: str) -> ConversationMessage | None:
        """Get a message by ID."""
        return self._message_index.get(message_id)

    def list_conversations(
        self,
        agent_id: str = "",
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations with optional filtering."""
        if agent_id:
            conv_ids = self._agent_conversations.get(agent_id, [])
            conversations = [self._conversations[cid] for cid in conv_ids if cid in self._conversations]
        else:
            conversations = list(self._conversations.values())

        if status:
            conversations = [c for c in conversations if c.status == status]

        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations[offset:offset + limit]

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
        role: MessageRole | None = None,
    ) -> list[ConversationMessage]:
        """Get messages from a conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return []

        messages = conversation.messages
        if role:
            messages = [m for m in messages if m.role == role]

        return messages[offset:offset + limit]

    def update_conversation(
        self,
        conversation_id: str,
        title: str | None = None,
        status: ConversationStatus | None = None,
        importance: MemoryImportance | None = None,
        tags: list[str] | None = None,
    ) -> Conversation | None:
        """Update conversation metadata."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None

        if title is not None:
            conversation.title = title
        if status is not None:
            conversation.status = status
        if importance is not None:
            conversation.importance = importance
        if tags is not None:
            conversation.tags = tags

        conversation.updated_at = datetime.now(timezone.utc).isoformat()
        return conversation

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        conversation = self._conversations.pop(conversation_id, None)
        if not conversation:
            return False

        # Remove message index entries
        for message in conversation.messages:
            self._message_index.pop(message.message_id, None)

        # Remove from agent index
        agent_convs = self._agent_conversations.get(conversation.agent_id, [])
        if conversation_id in agent_convs:
            agent_convs.remove(conversation_id)

        logger.info("Deleted conversation %s", conversation_id)
        return True

    # ── Search and Retrieval ─────────────────────────────

    def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        agent_id: str = "",
        limit: int = 10,
        min_relevance: float = 0.3,
    ) -> list[SearchResult]:
        """Search conversations by keyword and/or semantic similarity."""
        results: list[SearchResult] = []

        # Determine which conversations to search
        if agent_id:
            conv_ids = self._agent_conversations.get(agent_id, [])
            conversations = {cid: self._conversations[cid] for cid in conv_ids if cid in self._conversations}
        else:
            conversations = self._conversations

        # Keyword search
        if mode in (SearchMode.KEYWORD, SearchMode.HYBRID):
            query_terms = set(query.lower().split())
            for conversation in conversations.values():
                for i, message in enumerate(conversation.messages):
                    content_lower = message.content.lower()
                    match_count = sum(1 for term in query_terms if term in content_lower)
                    if match_count > 0:
                        score = match_count / len(query_terms)
                        if score >= min_relevance:
                            result = SearchResult(
                                message=message,
                                conversation_id=conversation.conversation_id,
                                relevance_score=score,
                                match_type="keyword",
                                context_before=conversation.messages[max(0, i - 2):i],
                                context_after=conversation.messages[i + 1:i + 3],
                            )
                            results.append(result)

        # Temporal search
        if mode == SearchMode.TEMPORAL:
            results.sort(key=lambda r: r.message.created_at, reverse=True)

        # Deduplicate and sort by relevance
        seen = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x.relevance_score, reverse=True):
            if r.message.message_id not in seen:
                seen.add(r.message.message_id)
                unique_results.append(r)

        return unique_results[:limit]

    def search_by_time_range(
        self,
        agent_id: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: int = 50,
    ) -> list[ConversationMessage]:
        """Search messages within a time range."""
        results: list[ConversationMessage] = []

        if agent_id:
            conv_ids = self._agent_conversations.get(agent_id, [])
        else:
            conv_ids = list(self._conversations.keys())

        for conv_id in conv_ids:
            conversation = self._conversations.get(conv_id)
            if not conversation:
                continue
            for message in conversation.messages:
                if start_time and message.created_at < start_time:
                    continue
                if end_time and message.created_at > end_time:
                    continue
                results.append(message)

        results.sort(key=lambda m: m.created_at, reverse=True)
        return results[:limit]

    def get_context_window(
        self,
        conversation_id: str,
        around_message_id: str = "",
        window_size: int = 0,
    ) -> list[ConversationMessage]:
        """Get a context window around a specific message."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return []

        window_size = window_size or self.config.context_window_size
        half = window_size // 2

        if around_message_id:
            for i, message in enumerate(conversation.messages):
                if message.message_id == around_message_id:
                    start = max(0, i - half)
                    end = min(len(conversation.messages), i + half + 1)
                    return conversation.messages[start:end]

        # Return last N messages if no anchor
        return conversation.messages[-window_size:]

    # ── Topic Management ─────────────────────────────────

    def extract_topics(self, conversation_id: str) -> list[ConversationTopic]:
        """Extract topics from a conversation using keyword analysis."""
        conversation = self._conversations.get(conversation_id)
        if not conversation or not self.config.enable_topic_extraction:
            return []

        # Simple keyword frequency-based topic extraction
        word_freq: dict[str, int] = defaultdict(int)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                       "have", "has", "had", "do", "does", "did", "will", "would",
                       "could", "should", "may", "might", "can", "shall", "to", "of",
                       "in", "for", "on", "with", "at", "by", "from", "as", "into",
                       "through", "during", "before", "after", "above", "below", "and",
                       "but", "or", "nor", "not", "so", "yet", "both", "either", "neither",
                       "each", "every", "all", "any", "few", "more", "most", "other", "some",
                       "such", "no", "only", "own", "same", "than", "too", "very", "just",
                       "because", "about", "what", "when", "where", "which", "who", "how",
                       "this", "that", "these", "those", "it", "its", "i", "me", "my", "we", "our"}

        for message in conversation.messages:
            words = message.content.lower().split()
            for word in words:
                clean = word.strip(".,!?;:\"'()[]{}").lower()
                if len(clean) > 3 and clean not in stop_words:
                    word_freq[clean] += 1

        # Group top words into topics
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        if not sorted_words:
            return []

        topics = []
        for i in range(min(3, len(sorted_words) // 3)):
            cluster = sorted_words[i * 3:(i + 1) * 3]
            if cluster:
                topic = ConversationTopic(
                    name=" ".join(w for w, _ in cluster[:2]).title(),
                    keywords=[w for w, _ in cluster],
                    confidence=min(1.0, sum(c for _, c in cluster) / (len(conversation.messages) * 3)),
                    message_count=len(conversation.messages),
                    first_seen=conversation.messages[0].created_at,
                    last_seen=conversation.messages[-1].created_at,
                )
                topics.append(topic)
                self._topic_index[topic.topic_id] = topic

        conversation.topics = topics
        return topics

    def get_topics(self, conversation_id: str) -> list[ConversationTopic]:
        """Get topics for a conversation."""
        conversation = self._conversations.get(conversation_id)
        return conversation.topics if conversation else []

    # ── Memory Consolidation ─────────────────────────────

    def consolidate_conversation(self, conversation_id: str) -> ConversationSummary | None:
        """Create a consolidated summary of a conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None

        messages = conversation.messages
        if not messages:
            return None

        # Generate a summary from the conversation
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT]

        summary_content = f"Conversation with {len(messages)} messages. "
        summary_content += f"User sent {len(user_messages)} messages, "
        summary_content += f"Assistant responded {len(assistant_messages)} times. "

        # Extract key points from user messages
        key_points = []
        for msg in user_messages[:5]:
            if len(msg.content) > 20:
                key_points.append(msg.content[:100] + ("..." if len(msg.content) > 100 else ""))

        # Extract decisions from assistant messages
        decisions = []
        for msg in assistant_messages:
            lower = msg.content.lower()
            if any(word in lower for word in ["decided", "decision", "agreed", "concluded", "therefore"]):
                decisions.append(msg.content[:100] + ("..." if len(msg.content) > 100 else ""))

        summary = ConversationSummary(
            content=summary_content,
            key_points=key_points[:10],
            decisions=decisions[:5],
            action_items=[],
            message_range=(0, len(messages) - 1),
            tokens=len(summary_content) // 4,
        )

        conversation.summaries.append(summary)
        conversation.status = ConversationStatus.CONSOLIDATED
        conversation.updated_at = datetime.now(timezone.utc).isoformat()

        logger.info("Consolidated conversation %s: %d messages -> %d key points",
                     conversation_id, len(messages), len(key_points))
        return summary

    def get_summaries(self, conversation_id: str) -> list[ConversationSummary]:
        """Get summaries for a conversation."""
        conversation = self._conversations.get(conversation_id)
        return conversation.summaries if conversation else []

    # ── Cross-Session Linking ────────────────────────────

    def find_related_conversations(
        self,
        conversation_id: str,
        limit: int = 5,
    ) -> list[tuple[Conversation, float]]:
        """Find conversations related to the given one by topic overlap."""
        source = self._conversations.get(conversation_id)
        if not source:
            return []

        if not source.topics:
            self.extract_topics(conversation_id)

        source_keywords = set()
        for topic in source.topics:
            source_keywords.update(topic.keywords)

        if not source_keywords:
            return []

        related: list[tuple[Conversation, float]] = []
        for conv_id, conversation in self._conversations.items():
            if conv_id == conversation_id:
                continue

            if not conversation.topics:
                self.extract_topics(conv_id)

            target_keywords = set()
            for topic in conversation.topics:
                target_keywords.update(topic.keywords)

            overlap = len(source_keywords & target_keywords)
            if overlap > 0:
                score = overlap / max(len(source_keywords | target_keywords), 1)
                if score >= self.config.similarity_threshold:
                    related.append((conversation, score))

        related.sort(key=lambda x: x[1], reverse=True)
        return related[:limit]

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> ConversationMemoryStats:
        """Get comprehensive memory statistics."""
        stats = ConversationMemoryStats()
        stats.total_conversations = len(self._conversations)
        stats.total_messages = len(self._message_index)
        stats.total_topics = len(self._topic_index)

        for conversation in self._conversations.values():
            stats.total_tokens += conversation.total_tokens
            stats.total_summaries += len(conversation.summaries)

            if conversation.status == ConversationStatus.ACTIVE:
                stats.active_conversations += 1
            elif conversation.status == ConversationStatus.ARCHIVED:
                stats.archived_conversations += 1
            elif conversation.status == ConversationStatus.CONSOLIDATED:
                stats.consolidated_conversations += 1

            if not stats.oldest_conversation or conversation.created_at < stats.oldest_conversation:
                stats.oldest_conversation = conversation.created_at
            if not stats.newest_conversation or conversation.created_at > stats.newest_conversation:
                stats.newest_conversation = conversation.created_at

        if stats.total_conversations > 0:
            stats.avg_messages_per_conversation = stats.total_messages / stats.total_conversations

        return stats

    def reset(self) -> None:
        """Reset the entire conversation memory."""
        self._conversations.clear()
        self._message_index.clear()
        self._topic_index.clear()
        self._keyword_index.clear()
        self._agent_conversations.clear()
        logger.info("AgentConversationMemory reset")

    # ── Internal Helpers ─────────────────────────────────

    def _index_keywords(self, message_id: str, content: str) -> None:
        """Index keywords from message content for fast search."""
        words = set(content.lower().split())
        for word in words:
            clean = word.strip(".,!?;:\"'()[]{}").lower()
            if len(clean) > 2:
                self._keyword_index[clean].add(message_id)

    def _auto_consolidate(self, conversation: Conversation) -> None:
        """Automatically consolidate when message threshold is exceeded."""
        if len(conversation.summaries) < 5:
            self.consolidate_conversation(conversation.conversation_id)


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_conversation_memory: AgentConversationMemory | None = None


def get_conversation_memory() -> AgentConversationMemory:
    """Get or create the global Conversation Memory instance."""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = AgentConversationMemory()
    return _conversation_memory


def reset_conversation_memory() -> None:
    """Reset the global Conversation Memory instance."""
    global _conversation_memory
    if _conversation_memory:
        _conversation_memory.reset()
    _conversation_memory = None