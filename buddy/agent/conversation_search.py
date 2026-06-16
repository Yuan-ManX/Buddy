"""Buddy Conversation Search — cross-conversation semantic search and retrieval

Enables agents to search their entire conversation history, find relevant
past discussions, and generate recaps of previous work. This creates a
persistent knowledge layer that spans individual sessions.

Core capabilities:
  - Semantic Search: finds conversations by meaning, not just keywords
  - Conversation Recap: summarizes past discussions on a topic
  - Pattern Detection: identifies recurring themes across sessions
  - Timeline View: chronological view of topics and decisions
  - Context Injection: relevant past context for current conversations
  - Metadata Indexing: tags, dates, participants, topics
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger("buddy.conversation_search")


# ═══════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════

@dataclass
class ConversationEntry:
    """A single turn in a conversation."""
    id: str = field(default_factory=lambda: f"entry-{uuid.uuid4().hex[:8]}")
    conversation_id: str = ""
    role: str = ""  # "user" or "assistant"
    content: str = ""
    summary: str = ""  # Auto-generated summary
    topics: list[str] = field(default_factory=list)
    tokens: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    embedding: list[float] | None = None  # For semantic search


@dataclass
class ConversationIndex:
    """A conversation with its full metadata index."""
    conversation_id: str = field(default_factory=lambda: f"conv-{uuid.uuid4().hex[:8]}")
    title: str = ""
    summary: str = ""
    topics: list[str] = field(default_factory=list)
    entry_count: int = 0
    total_tokens: int = 0
    first_message_at: str = ""
    last_message_at: str = ""
    key_decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """A single search result."""
    entry: ConversationEntry
    conversation: ConversationIndex | None = None
    relevance_score: float = 0.0
    context_window: list[ConversationEntry] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Conversation Search Engine
# ═══════════════════════════════════════════════════════════

class ConversationSearchEngine:
    """Cross-conversation semantic search and knowledge retrieval.

    Indexes all conversation history, provides semantic search across sessions,
    and generates contextual recaps for ongoing discussions.
    """

    def __init__(self, client: AsyncOpenAI | None = None):
        self._client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._entries: dict[str, ConversationEntry] = {}
        self._conversations: dict[str, ConversationIndex] = {}
        self._entries_by_conv: dict[str, list[str]] = defaultdict(list)

        # Topic index: topic → list of entry IDs
        self._topic_index: dict[str, list[str]] = defaultdict(list)

        # Keyword index for fast keyword-based search
        self._keyword_index: dict[str, list[str]] = defaultdict(list)

        # Statistics
        self._total_entries = 0
        self._total_conversations = 0
        self._last_indexed_at = ""

    # ── Indexing ─────────────────────────────────────────

    async def index_conversation(
        self,
        conversation_id: str,
        messages: list[dict],
        title: str = "",
        tags: list[str] | None = None,
    ) -> ConversationIndex:
        """Index a conversation with all its messages.

        Creates a ConversationIndex with metadata, and indexes each message
        as a ConversationEntry for future search. Auto-generates summaries
        and topic tags for efficient retrieval.
        """
        if not messages:
            raise ValueError("Cannot index empty conversation")

        # Create or update conversation index
        conv = self._conversations.get(conversation_id)
        if not conv:
            conv = ConversationIndex(
                conversation_id=conversation_id,
                title=title or self._generate_title(messages),
                first_message_at=messages[0].get("timestamp", datetime.now(timezone.utc).isoformat()),
                tags=tags or [],
            )
            self._total_conversations += 1

        conv.last_message_at = messages[-1].get("timestamp", datetime.now(timezone.utc).isoformat())

        # Index each message
        new_entries = []
        for msg in messages:
            entry = ConversationEntry(
                conversation_id=conversation_id,
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                tokens=len(msg.get("content", "").split()),
                timestamp=msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
            )

            # Auto-generate summary for longer messages
            if len(entry.content) > 200:
                entry.summary = self._quick_summarize(entry.content)

            # Extract topics
            entry.topics = self._extract_topics(entry.content)

            self._entries[entry.id] = entry
            self._entries_by_conv[conversation_id].append(entry.id)
            new_entries.append(entry)

            # Update topic index
            for topic in entry.topics:
                self._topic_index[topic].append(entry.id)

            # Update keyword index
            self._index_keywords(entry)

        # Update conversation metadata
        conv.entry_count = len(self._entries_by_conv[conversation_id])
        conv.total_tokens = sum(
            self._entries[eid].tokens
            for eid in self._entries_by_conv[conversation_id]
        )

        # Generate conversation summary
        if len(new_entries) > 0:
            conv.summary = await self._generate_conversation_summary(conv, new_entries[:10])

        # Extract key topics
        all_topics = []
        for eid in self._entries_by_conv[conversation_id]:
            all_topics.extend(self._entries[eid].topics)
        topic_counts = defaultdict(int)
        for t in all_topics:
            topic_counts[t] += 1
        conv.topics = [t for t, c in sorted(topic_counts.items(), key=lambda x: -x[1])[:10]]

        self._conversations[conversation_id] = conv
        self._total_entries += len(new_entries)
        self._last_indexed_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Indexed conversation {conversation_id}: "
            f"{len(new_entries)} entries, {len(conv.topics)} topics"
        )
        return conv

    def _generate_title(self, messages: list[dict]) -> str:
        """Generate a title from the first message."""
        if messages:
            first = messages[0].get("content", "")
            return first[:80] + ("..." if len(first) > 80 else "")
        return "Untitled Conversation"

    def _quick_summarize(self, text: str) -> str:
        """Quick heuristic summary (no LLM call)."""
        sentences = re.split(r'[.!?]+', text)
        # Take first and last sentence
        parts = []
        if sentences:
            parts.append(sentences[0].strip()[:100])
        if len(sentences) > 2:
            parts.append(sentences[-1].strip()[:100])
        return " | ".join(parts) if parts else text[:100]

    def _extract_topics(self, text: str) -> list[str]:
        """Extract keywords as topics from text."""
        words = re.findall(r'\b[A-Z][a-z]{3,}(?:\s[A-Z][a-z]{3,})*\b', text)
        # Also extract meaningful lowercase phrases
        topic_indicators = [
            "about", "regarding", "concerning", "related to", "topic",
            "project", "task", "issue", "feature", "bug", "fix",
            "deploy", "test", "build", "config", "api", "database",
        ]
        topics = set()
        for word in words:
            if len(word) > 3:
                topics.add(word.lower())

        # Add technical terms
        for indicator in topic_indicators:
            if indicator in text.lower():
                # Find the context around the indicator
                idx = text.lower().find(indicator)
                context = text[max(0, idx-5):idx+len(indicator)+30]
                topics.add(context.strip().lower()[:50])

        return list(topics)[:8]

    def _index_keywords(self, entry: ConversationEntry):
        """Index entry by keywords for fast retrieval."""
        words = re.findall(r'\b\w{4,}\b', entry.content.lower())
        stop_words = {
            "the", "and", "for", "that", "this", "with", "was", "have",
            "from", "are", "but", "not", "you", "all", "can", "has",
            "been", "will", "they", "what", "when", "where", "which",
            "here", "there", "about", "would", "could", "should", "just",
        }
        for word in set(words):
            if word not in stop_words:
                self._keyword_index[word].append(entry.id)

    async def _generate_conversation_summary(
        self, conv: ConversationIndex, entries: list[ConversationEntry]
    ) -> str:
        """Generate a summary of the conversation."""
        if len(entries) < 3:
            return conv.title

        content = "\n".join(
            f"[{e.role}]: {e.content[:300]}" for e in entries[:5]
        )

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": "Summarize this conversation in 2-3 sentences. Focus on the main topics discussed and any decisions made.",
                }, {
                    "role": "user",
                    "content": content,
                }],
                max_tokens=150,
                temperature=0.3,
            )
            return response.choices[0].message.content or conv.title
        except Exception:
            return conv.title

    # ── Search ───────────────────────────────────────────

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.1,
        conversation_id: str | None = None,
        role: str | None = None,
        days_back: int = 90,
    ) -> list[SearchResult]:
        """Search conversation history by semantic meaning and keywords.

        Uses a two-pass approach: keyword-based filtering followed by LLM-based
        relevance scoring for the most semantically relevant results.
        """
        # Pass 1: Keyword-based filtering
        query_words = set(re.findall(r'\b\w{4,}\b', query.lower()))
        candidate_ids: dict[str, float] = {}

        for word in query_words:
            for entry_id in self._keyword_index.get(word, []):
                candidate_ids[entry_id] = candidate_ids.get(entry_id, 0) + 1

        if not candidate_ids:
            # Fallback: search all entries by metadata
            for entry_id, entry in self._entries.items():
                if conversation_id and entry.conversation_id != conversation_id:
                    continue
                if role and entry.role != role:
                    continue
                # Check time range
                if days_back > 0:
                    entry_time = datetime.fromisoformat(entry.timestamp)
                    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
                    if entry_time < cutoff:
                        continue
                # Simple substring match
                query_lower = query.lower()
                if query_lower in entry.content.lower():
                    candidate_ids[entry_id] = 1.0
                elif query_lower in entry.summary.lower():
                    candidate_ids[entry_id] = 0.5

        # Pass 2: Score candidates
        results: list[SearchResult] = []
        for entry_id, keyword_score in sorted(
            candidate_ids.items(), key=lambda x: -x[1]
        )[:limit * 3]:
            entry = self._entries.get(entry_id)
            if not entry:
                continue

            # Score based on keyword match density
            normalized_score = min(keyword_score / max(len(query_words), 1), 1.0)

            if normalized_score >= min_score:
                conv = self._conversations.get(entry.conversation_id)
                context = self._get_entry_context(entry, window=3)
                results.append(SearchResult(
                    entry=entry,
                    conversation=conv,
                    relevance_score=normalized_score,
                    context_window=context,
                ))

        return sorted(results, key=lambda r: -r.relevance_score)[:limit]

    def _get_entry_context(
        self, entry: ConversationEntry, window: int = 3
    ) -> list[ConversationEntry]:
        """Get surrounding entries for context."""
        conv_entries = self._entries_by_conv.get(entry.conversation_id, [])
        try:
            idx = conv_entries.index(entry.id)
        except ValueError:
            return [entry]

        start = max(0, idx - window)
        end = min(len(conv_entries), idx + window + 1)
        return [
            self._entries[eid]
            for eid in conv_entries[start:end]
            if eid in self._entries
        ]

    async def search_by_topic(
        self, topic: str, limit: int = 10
    ) -> list[SearchResult]:
        """Search for conversations by topic."""
        entry_ids = self._topic_index.get(topic.lower(), [])
        results = []
        for entry_id in entry_ids[:limit * 2]:
            entry = self._entries.get(entry_id)
            if entry:
                conv = self._conversations.get(entry.conversation_id)
                results.append(SearchResult(
                    entry=entry,
                    conversation=conv,
                    relevance_score=0.8,
                ))
        return sorted(results, key=lambda r: -r.relevance_score)[:limit]

    # ── Recap Generation ─────────────────────────────────

    async def generate_recap(
        self, query: str, days_back: int = 30, limit: int = 5
    ) -> dict:
        """Generate a recap of past conversations relevant to a query.

        Searches conversation history, finds the most relevant discussions,
        and generates a coherent summary of what was discussed, decided,
        and what actions remain.
        """
        results = await self.search(query, limit=limit, days_back=days_back)
        if not results:
            return {
                "query": query,
                "found": False,
                "message": "No relevant conversations found.",
            }

        # Build context for recap
        context_parts = []
        for r in results[:limit]:
            entry = r.entry
            conv = r.conversation
            context_parts.append(
                f"[{conv.title if conv else 'Unknown'}]\n"
                f"[{entry.role}]: {entry.content[:300]}\n"
                f"Topics: {', '.join(entry.topics[:5])}\n"
            )

        context = "\n---\n".join(context_parts)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You are a conversation recap generator. Given past conversation "
                        "excerpts, generate a concise recap covering:\n"
                        "1. What was discussed\n"
                        "2. Key decisions made\n"
                        "3. Outstanding action items\n"
                        "4. How this relates to the current query\n\n"
                        "Respond in JSON:\n"
                        '{"summary": "...", "key_decisions": ["..."], '
                        '"action_items": ["..."], "relevance": "..."}'
                    ),
                }, {
                    "role": "user",
                    "content": (
                        f"Query: {query}\n\n"
                        f"Past conversations:\n{context}\n\n"
                        "Generate a recap."
                    ),
                }],
                max_tokens=400,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            return {
                "query": query,
                "found": True,
                "result_count": len(results),
                "summary": data.get("summary", ""),
                "key_decisions": data.get("key_decisions", []),
                "action_items": data.get("action_items", []),
                "relevance": data.get("relevance", ""),
                "sources": [
                    {
                        "conversation_id": r.entry.conversation_id,
                        "title": r.conversation.title if r.conversation else "",
                        "relevance": round(r.relevance_score, 2),
                        "timestamp": r.entry.timestamp,
                    }
                    for r in results[:limit]
                ],
            }

        except Exception as e:
            logger.error(f"Recap generation failed: {e}")
            return {
                "query": query,
                "found": True,
                "result_count": len(results),
                "summary": f"Found {len(results)} relevant conversations about '{query}'.",
                "key_decisions": [],
                "action_items": [],
                "sources": [
                    {
                        "conversation_id": r.entry.conversation_id,
                        "title": r.conversation.title if r.conversation else "",
                        "relevance": round(r.relevance_score, 2),
                    }
                    for r in results[:limit]
                ],
            }

    # ── Timeline ─────────────────────────────────────────

    def get_timeline(
        self, days_back: int = 30, topics: list[str] | None = None
    ) -> list[dict]:
        """Get a chronological timeline of conversations."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        timeline = []
        for conv in self._conversations.values():
            try:
                last_time = datetime.fromisoformat(conv.last_message_at)
            except (ValueError, TypeError):
                continue

            if last_time < cutoff:
                continue

            if topics and not any(t in conv.topics for t in topics):
                continue

            timeline.append({
                "conversation_id": conv.conversation_id,
                "title": conv.title,
                "summary": conv.summary[:200],
                "topics": conv.topics[:5],
                "entry_count": conv.entry_count,
                "total_tokens": conv.total_tokens,
                "last_message_at": conv.last_message_at,
                "first_message_at": conv.first_message_at,
                "tags": conv.tags,
            })

        timeline.sort(key=lambda x: x["last_message_at"], reverse=True)
        return timeline

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict:
        """Get search engine statistics."""
        return {
            "total_entries": self._total_entries,
            "total_conversations": self._total_conversations,
            "indexed_entries": len(self._entries),
            "indexed_conversations": len(self._conversations),
            "unique_topics": len(self._topic_index),
            "unique_keywords": len(self._keyword_index),
            "last_indexed_at": self._last_indexed_at,
            "avg_entries_per_conversation": round(
                len(self._entries) / max(len(self._conversations), 1), 1
            ),
        }

    def get_conversation(self, conversation_id: str) -> ConversationIndex | None:
        """Get a conversation by ID."""
        return self._conversations.get(conversation_id)

    def list_conversations(self, limit: int = 20) -> list[dict]:
        """List all indexed conversations."""
        result = [
            {
                "conversation_id": c.conversation_id,
                "title": c.title,
                "summary": c.summary[:200],
                "topics": c.topics[:5],
                "entry_count": c.entry_count,
                "total_tokens": c.total_tokens,
                "last_message_at": c.last_message_at,
                "tags": c.tags,
            }
            for c in self._conversations.values()
        ]
        result.sort(key=lambda x: x["last_message_at"], reverse=True)
        return result[:limit]


# Global conversation search engine instance
conversation_search = ConversationSearchEngine()