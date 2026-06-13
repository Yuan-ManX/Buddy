"""Buddy Session Search — Cross-session recall and recap system

Enables agents to search their own past conversations, summarize findings,
and bring relevant context into current conversations. Combines FTS5-style
keyword matching with LLM-powered semantic search for robust recall.

Features:
- Conversation-level indexing with timestamps, summaries, topics, and embeddings
- FTS5-style full-text search across session transcripts
- LLM-powered semantic search using embedding similarity
- Automatic session summarization when sessions end
- Contextual recap generation for search queries
- Export/import of the session index for persistence

Architecture:
- SessionIndex: In-memory index of all indexed sessions with keyword + vector stores
- SessionSearcher: Orchestrates text search, semantic search, and recap generation
- SessionEntry / SessionRecap: Immutable data classes for session metadata and results
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

from config.settings import settings
from database.db import async_session
from database.models import Conversation, Message

logger = logging.getLogger("buddy.session_search")


# ══════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════

@dataclass
class SessionEntry:
    """Represents a single indexed conversation session.

    Attributes:
        id: Unique session identifier.
        title: Human-readable session title.
        agent_ids: List of agent IDs that participated.
        summary: LLM-generated summary of the session content.
        key_topics: List of extracted topic strings.
        embedding: Vector embedding of the combined summary + topics.
        message_count: Number of messages in the session.
        importance: Heuristic importance score (0.0 - 1.0).
        created_at: ISO-8601 timestamp of session creation.
        updated_at: ISO-8601 timestamp of last modification.
        metadata: Arbitrary additional metadata.
    """
    id: str
    title: str
    agent_ids: list[str]
    summary: str = ""
    key_topics: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    message_count: int = 0
    importance: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionRecap:
    """Summarized search result bundling matched sessions with a narrative recap.

    Attributes:
        query: The original search query.
        recap_text: LLM-generated narrative summary across matched sessions.
        sessions: List of matched SessionEntry objects.
        relevance_scores: Mapping of session_id to relevance score (0.0 - 1.0).
        generated_at: ISO-8601 timestamp of recap generation.
        total_matches: Total number of sessions considered.
    """
    query: str
    recap_text: str
    sessions: list[SessionEntry]
    relevance_scores: dict[str, float] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_matches: int = 0


# ══════════════════════════════════════════════════════════════
# Session Index
# ══════════════════════════════════════════════════════════════

class SessionIndex:
    """In-memory index of all indexed conversation sessions.

    Maintains a keyword-based inverted index for fast text lookup and
    an embedding store for semantic similarity search. Supports sessions
    being added, removed, updated, and searched.

    Thread-compatible but not thread-safe; intended for use within an
    async event loop.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionEntry] = {}
        # Inverted keyword index: lowercase token -> set of session ids
        self._keyword_index: dict[str, set[str]] = {}
        # Pre-computed embeddings: session_id -> embedding vector
        self._embedding_store: dict[str, list[float]] = {}
        # Common English stop words to exclude from keyword indexing
        self._stop_words: frozenset[str] = frozenset({
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "shall", "can",
            "need", "dare", "ought", "used", "it", "its", "that", "this",
            "these", "those", "i", "me", "my", "we", "our", "you", "your",
            "he", "she", "they", "them", "not", "no", "nor", "so", "as",
            "if", "then", "than", "too", "very", "just", "about", "also",
            "into", "over", "under", "after", "before", "between", "through",
        })

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def add_session(self, entry: SessionEntry) -> None:
        """Add or update a session entry and rebuild its keyword index entries."""
        self._sessions[entry.id] = entry
        self._rebuild_keywords_for(entry)
        if entry.embedding:
            self._embedding_store[entry.id] = entry.embedding
        logger.debug("Indexed session %s (%d messages)", entry.id, entry.message_count)

    def remove_session(self, session_id: str) -> bool:
        """Remove a session from all indexes. Returns True if it existed."""
        entry = self._sessions.pop(session_id, None)
        if entry is None:
            return False
        self._remove_keywords_for(entry)
        self._embedding_store.pop(session_id, None)
        logger.debug("Removed session %s from index", session_id)
        return True

    def get_session(self, session_id: str) -> SessionEntry | None:
        """Return the SessionEntry for the given id, or None."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        agent_id: str | None = None,
        min_importance: float = 0.0,
        limit: int = 50,
    ) -> list[SessionEntry]:
        """List sessions, optionally filtered by agent and importance."""
        results: list[SessionEntry] = []
        for entry in self._sessions.values():
            if agent_id and agent_id not in entry.agent_ids:
                continue
            if entry.importance < min_importance:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def get_recent_sessions(self, limit: int = 10) -> list[SessionEntry]:
        """Return the most recently updated sessions."""
        sorted_entries = sorted(
            self._sessions.values(),
            key=lambda e: e.updated_at,
            reverse=True,
        )
        return sorted_entries[:limit]

    @property
    def session_count(self) -> int:
        """Total number of indexed sessions."""
        return len(self._sessions)

    # ------------------------------------------------------------------
    # Keyword (FTS5-style) search
    # ------------------------------------------------------------------

    def keyword_search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[tuple[SessionEntry, float]]:
        """Perform FTS5-style keyword search across indexed sessions.

        Tokenizes the query, matches against the inverted keyword index,
        and scores sessions by term frequency (TF) relative to session size.

        Args:
            query: Free-text search query.
            limit: Maximum number of results.
            min_score: Minimum relevance score threshold.

        Returns:
            List of (SessionEntry, score) tuples ordered by descending score.
        """
        if not self._sessions:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Gather candidate sessions that match any query token
        candidate_ids: set[str] = set()
        for token in query_tokens:
            if token in self._keyword_index:
                candidate_ids.update(self._keyword_index[token])

        if not candidate_ids:
            return []

        # Score candidates: number of matching tokens / total tokens in session
        scored: list[tuple[SessionEntry, float]] = []
        for sid in candidate_ids:
            entry = self._sessions[sid]
            session_text = self._build_searchable_text(entry)
            session_tokens = self._tokenize(session_text)
            if not session_tokens:
                continue
            matches = sum(1 for t in query_tokens if t in session_tokens)
            # TF-like score normalised by total tokens to avoid long-session bias
            score = matches / max(len(query_tokens), 1)
            if score >= min_score:
                scored.append((entry, round(score, 4)))

        scored.sort(key=lambda x: -x[1])
        return scored[:limit]

    # ------------------------------------------------------------------
    # Keyword index helpers
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase, split on non-alphanumeric, and remove stop words."""
        import re
        tokens: list[str] = []
        for raw in re.split(r"[^a-zA-Z0-9]+", text.lower()):
            token = raw.strip()
            if not token:
                continue
            if len(token) < 2:
                continue
            if token in self._stop_words:
                continue
            tokens.append(token)
        return tokens

    def _build_searchable_text(self, entry: SessionEntry) -> str:
        """Create the full text block used for keyword indexing and search."""
        parts = [
            entry.title,
            entry.summary,
            " ".join(entry.key_topics),
        ]
        return " ".join(part for part in parts if part)

    def _rebuild_keywords_for(self, entry: SessionEntry) -> None:
        """Extract tokens from a session and add them to the inverted index."""
        self._remove_keywords_for(entry)
        text = self._build_searchable_text(entry)
        tokens = self._tokenize(text)
        for token in tokens:
            self._keyword_index.setdefault(token, set()).add(entry.id)

    def _remove_keywords_for(self, entry: SessionEntry) -> None:
        """Remove a session's tokens from the inverted index."""
        text = self._build_searchable_text(entry)
        tokens = self._tokenize(text)
        for token in tokens:
            if token in self._keyword_index:
                self._keyword_index[token].discard(entry.id)
                if not self._keyword_index[token]:
                    del self._keyword_index[token]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_index(self) -> dict[str, Any]:
        """Export the entire session index as a serializable dictionary.

        Embeddings are included so the index can be fully restored.
        """
        sessions_data: list[dict[str, Any]] = []
        for entry in self._sessions.values():
            sessions_data.append({
                "id": entry.id,
                "title": entry.title,
                "agent_ids": entry.agent_ids,
                "summary": entry.summary,
                "key_topics": entry.key_topics,
                "embedding": entry.embedding,
                "message_count": entry.message_count,
                "importance": entry.importance,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
                "metadata": entry.metadata,
            })

        return {
            "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "session_count": len(sessions_data),
            "sessions": sessions_data,
        }

    def import_index(self, data: dict[str, Any]) -> int:
        """Import sessions from a previously exported index dictionary.

        Existing sessions with the same id are overwritten.
        Returns the number of sessions imported.
        """
        sessions_data = data.get("sessions", [])
        count = 0
        for raw in sessions_data:
            entry = SessionEntry(
                id=raw.get("id", str(uuid.uuid4())),
                title=raw.get("title", "Untitled"),
                agent_ids=raw.get("agent_ids", []),
                summary=raw.get("summary", ""),
                key_topics=raw.get("key_topics", []),
                embedding=raw.get("embedding"),
                message_count=raw.get("message_count", 0),
                importance=raw.get("importance", 0.5),
                created_at=raw.get("created_at", ""),
                updated_at=raw.get("updated_at", ""),
                metadata=raw.get("metadata", {}),
            )
            self.add_session(entry)
            count += 1

        logger.info("Imported %d sessions into index (total: %d)", count, self.session_count)
        return count

    def save_to_file(self, filepath: str) -> None:
        """Persist the full index to a JSON file on disk."""
        data = self.export_index()
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Session index saved to %s (%d sessions)", filepath, data["session_count"])

    def load_from_file(self, filepath: str) -> int:
        """Load the index from a JSON file on disk. Returns imported count."""
        if not os.path.exists(filepath):
            logger.warning("Session index file not found: %s", filepath)
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.import_index(data)


# ══════════════════════════════════════════════════════════════
# Session Searcher
# ══════════════════════════════════════════════════════════════

class SessionSearcher:
    """Orchestrates text search, semantic search, and recap generation.

    Combines the SessionIndex (keyword matching) with embedding-based
    semantic search and an optional LLM for generating narrative recaps
    and automatic session summaries.

    Typical usage::

        searcher = SessionSearcher()
        await searcher.index_session(conversation_id="abc123")
        results = await searcher.search("what did we decide about deployment?")
        recap = await searcher.generate_recap("deployment decisions")

    Parameters:
        embedding_model: Model name for generating embeddings.
        semantic_enabled: Whether semantic search via embeddings is active.
        llm_model: Model used for recap generation and auto-summarization.
    """

    def __init__(
        self,
        embedding_model: str | None = None,
        semantic_enabled: bool = True,
        llm_model: str | None = None,
    ) -> None:
        self.index = SessionIndex()
        self._embedding_model = embedding_model or settings.EMBEDDING_MODEL
        self._semantic_enabled = semantic_enabled
        self._llm_model = llm_model or settings.LLM_MODEL

        self._embedding_client: AsyncOpenAI | None = None
        self._llm_client: AsyncOpenAI | None = None

    # ------------------------------------------------------------------
    # Lazy client initialization
    # ------------------------------------------------------------------

    def _get_embedding_client(self) -> AsyncOpenAI:
        if self._embedding_client is None:
            self._embedding_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
        return self._embedding_client

    def _get_llm_client(self) -> AsyncOpenAI:
        if self._llm_client is None:
            self._llm_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
        return self._llm_client

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    async def _compute_embedding(self, text: str) -> list[float] | None:
        """Generate an embedding vector for the given text."""
        if not self._semantic_enabled or not text.strip():
            return None
        try:
            client = self._get_embedding_client()
            response = await client.embeddings.create(
                model=self._embedding_model,
                input=text[:8000],
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.debug("Embedding generation failed: %s", exc)
            return None

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute the cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------
    # Session indexing
    # ------------------------------------------------------------------

    async def index_session(
        self,
        conversation_id: str,
        agent_ids: list[str] | None = None,
        auto_summarize: bool = True,
    ) -> SessionEntry | None:
        """Index a conversation session by pulling messages from the database.

        Reads all messages for the given conversation from the DB, optionally
        generates an LLM summary and extracts key topics, computes an embedding,
        and adds the resulting SessionEntry to the SessionIndex.

        Args:
            conversation_id: Database conversation ID to index.
            agent_ids: Optional list of participating agent IDs.
            auto_summarize: Whether to call the LLM for summary generation.

        Returns:
            The new or updated SessionEntry, or None if the conversation was empty.
        """
        try:
            async with async_session() as session:
                from sqlalchemy import select

                # Fetch conversation metadata
                conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
                conv_result = await session.execute(conv_stmt)
                conversation = conv_result.scalars().first()

                if conversation is None:
                    logger.warning("Conversation %s not found in database", conversation_id)
                    return None

                # Fetch all messages ordered by creation time
                msg_stmt = (
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at.asc())
                )
                msg_result = await session.execute(msg_stmt)
                messages = msg_result.scalars().all()

                if not messages:
                    logger.debug("Conversation %s has no messages, skipping indexing", conversation_id)
                    return None

                # Build transcript text
                transcript_parts: list[str] = []
                resolved_agent_ids = set(agent_ids or [])
                for msg in messages:
                    role = msg.role or "unknown"
                    content = msg.content or ""
                    transcript_parts.append(f"[{role}]: {content}")
                    if msg.agent_id:
                        resolved_agent_ids.add(msg.agent_id)

                full_transcript = "\n".join(transcript_parts)

                title = conversation.title or "Untitled Session"
                summary = ""
                key_topics: list[str] = []
                embedding: list[float] | None = None

                if auto_summarize:
                    summary, key_topics = await self._summarize_session(
                        title=title,
                        transcript=full_transcript,
                        message_count=len(messages),
                    )
                    combined_text = f"{title}\n{summary}\n{' '.join(key_topics)}"
                    embedding = await self._compute_embedding(combined_text)

                # Compute heuristic importance based on message count and recency
                importance = self._compute_importance(
                    message_count=len(messages),
                    created_at=conversation.created_at,
                )

                entry = SessionEntry(
                    id=conversation_id,
                    title=title,
                    agent_ids=sorted(resolved_agent_ids),
                    summary=summary,
                    key_topics=key_topics,
                    embedding=embedding,
                    message_count=len(messages),
                    importance=importance,
                    created_at=conversation.created_at.isoformat() if conversation.created_at else "",
                    updated_at=conversation.updated_at.isoformat() if conversation.updated_at else "",
                )

                self.index.add_session(entry)
                logger.info(
                    "Indexed session %s: %d messages, %d topics, importance=%.2f",
                    conversation_id, entry.message_count, len(key_topics), importance,
                )
                return entry

        except Exception as exc:
            logger.error("Failed to index session %s: %s", conversation_id, exc)
            return None

    async def index_session_manual(
        self,
        session_id: str,
        title: str,
        transcript: str,
        agent_ids: list[str] | None = None,
        auto_summarize: bool = True,
        message_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> SessionEntry:
        """Index a session from a manually provided transcript (no DB read).

        Useful for indexing sessions that are not (or not yet) persisted
        in the database, such as in-flight or external conversations.

        Args:
            session_id: Unique identifier for the session.
            title: Human-readable session title.
            transcript: Full conversation transcript text.
            agent_ids: Participating agent IDs.
            auto_summarize: Whether to call the LLM for summary generation.
            message_count: Number of messages (if known).
            metadata: Arbitrary additional metadata.

        Returns:
            The newly created SessionEntry.
        """
        summary = ""
        key_topics: list[str] = []
        embedding: list[float] | None = None

        if auto_summarize and transcript.strip():
            summary, key_topics = await self._summarize_session(
                title=title,
                transcript=transcript,
                message_count=message_count,
            )
            combined_text = f"{title}\n{summary}\n{' '.join(key_topics)}"
            embedding = await self._compute_embedding(combined_text)

        importance = self._compute_importance(
            message_count=message_count,
            created_at=datetime.now(timezone.utc),
        )

        entry = SessionEntry(
            id=session_id,
            title=title,
            agent_ids=sorted(agent_ids or []),
            summary=summary,
            key_topics=key_topics,
            embedding=embedding,
            message_count=message_count,
            importance=importance,
            metadata=metadata or {},
        )

        self.index.add_session(entry)
        logger.info(
            "Manually indexed session %s: %d messages, %d topics",
            session_id, message_count, len(key_topics),
        )
        return entry

    # ------------------------------------------------------------------
    # Search methods
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        limit: int = 10,
        fusion_weight: float = 0.5,
    ) -> list[tuple[SessionEntry, float]]:
        """Combine keyword and semantic search for robust session retrieval.

        Uses a simple reciprocal-rank fusion approach: keyword results and
        semantic results are combined with configurable weighting.

        Args:
            query: Search query string.
            limit: Maximum number of results.
            fusion_weight: Weight for semantic vs keyword (0.0 = all keyword,
                           1.0 = all semantic, 0.5 = equal).

        Returns:
            List of (SessionEntry, score) tuples ordered by descending score.
        """
        # Run keyword and semantic searches concurrently
        kw_results, sem_results = await asyncio.gather(
            self._keyword_search_async(query, limit * 2),
            self.semantic_search(query, limit * 2) if self._semantic_enabled else asyncio.sleep(0, result=[]),
        )

        # Combine results with weighted fusion
        fused: dict[str, float] = {}

        # Keyword scores (rank-based: 1/(rank+1) scaling)
        for rank, (entry, kw_score) in enumerate(kw_results):
            rank_score = 1.0 / (rank + 1)
            fused[entry.id] = fused.get(entry.id, 0.0) + (1.0 - fusion_weight) * rank_score

        # Semantic scores
        for rank, (entry, sem_score) in enumerate(sem_results):
            rank_score = 1.0 / (rank + 1)
            fused[entry.id] = fused.get(entry.id, 0.0) + fusion_weight * rank_score

        # Build final ranked list
        scored: list[tuple[SessionEntry, float]] = []
        for sid, score in fused.items():
            entry = self.index.get_session(sid)
            if entry:
                scored.append((entry, round(score, 4)))

        scored.sort(key=lambda x: -x[1])
        return scored[:limit]

    async def _keyword_search_async(
        self, query: str, limit: int
    ) -> list[tuple[SessionEntry, float]]:
        """Thin async wrapper around the synchronous keyword search."""
        return self.index.keyword_search(query, limit=limit)

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> list[tuple[SessionEntry, float]]:
        """Perform embedding-based semantic search across indexed sessions.

        Computes the query embedding and compares it against all stored
        session embeddings using cosine similarity.

        Args:
            query: Natural language query.
            limit: Maximum number of results.
            min_similarity: Minimum cosine similarity threshold.

        Returns:
            List of (SessionEntry, similarity) tuples ordered by highest similarity.
        """
        if not self._semantic_enabled:
            return []

        query_embedding = await self._compute_embedding(query)
        if query_embedding is None:
            # Fall back to keyword search if embeddings unavailable
            return self.index.keyword_search(query, limit=limit)

        scored: list[tuple[SessionEntry, float]] = []
        for entry in self.index._sessions.values():
            stored_emb = self.index._embedding_store.get(entry.id)
            if stored_emb is None:
                # Compute on the fly for sessions without pre-computed embeddings
                combined = f"{entry.title}\n{entry.summary}\n{' '.join(entry.key_topics)}"
                stored_emb = await self._compute_embedding(combined)
                if stored_emb is not None:
                    self.index._embedding_store[entry.id] = stored_emb

            if stored_emb is None:
                # Give a small baseline for sessions without embeddings
                scored.append((entry, 0.15))
                continue

            similarity = self._cosine_similarity(query_embedding, stored_emb)
            if similarity >= min_similarity:
                scored.append((entry, round(similarity, 4)))

        scored.sort(key=lambda x: -x[1])
        return scored[:limit]

    # ------------------------------------------------------------------
    # Recap generation
    # ------------------------------------------------------------------

    async def generate_recap(
        self,
        query: str,
        limit: int = 5,
        use_llm: bool = True,
    ) -> SessionRecap:
        """Generate a contextual recap by searching and summarizing matched sessions.

        First searches for relevant sessions using fused keyword + semantic
        search, then optionally calls the LLM to produce a narrative summary
        that bridges the matched sessions into a coherent overview.

        Args:
            query: The search/recap query.
            limit: Number of top sessions to include in the recap.
            use_llm: Whether to use the LLM for narrative recap generation.
                     If False, a simple concatenation of session summaries is
                     returned as the recap text.

        Returns:
            A SessionRecap containing the recap text and matched sessions.
        """
        results = await self.search(query, limit=limit)

        relevance_scores: dict[str, float] = {}
        for entry, score in results:
            relevance_scores[entry.id] = score

        sessions = [entry for entry, _ in results]

        if use_llm and sessions:
            recap_text = await self._generate_llm_recap(query, sessions)
        else:
            # Simple concatenation fallback
            parts = [f"# Recap for: {query}\n"]
            for i, entry in enumerate(sessions, 1):
                parts.append(f"## {i}. {entry.title}")
                if entry.summary:
                    parts.append(entry.summary)
                if entry.key_topics:
                    parts.append(f"Topics: {', '.join(entry.key_topics)}")
                parts.append("")
            recap_text = "\n".join(parts)

        return SessionRecap(
            query=query,
            recap_text=recap_text,
            sessions=sessions,
            relevance_scores=relevance_scores,
            total_matches=len(results),
        )

    async def _generate_llm_recap(
        self,
        query: str,
        sessions: list[SessionEntry],
    ) -> str:
        """Use the LLM to produce a narrative recap across matched sessions."""
        if not sessions:
            return f"No sessions found matching: {query}"

        # Build context for the LLM
        session_contexts: list[str] = []
        for i, entry in enumerate(sessions, 1):
            ctx = (
                f"Session {i}: \"{entry.title}\"\n"
                f"Summary: {entry.summary or '(no summary)'}\n"
                f"Topics: {', '.join(entry.key_topics) if entry.key_topics else '(none)'}\n"
                f"Messages: {entry.message_count}, Importance: {entry.importance:.2f}"
            )
            session_contexts.append(ctx)

        prompt = (
            "You are a session search assistant. Given a user query and a list of "
            "matched past conversation sessions, produce a concise, narrative recap "
            "that synthesises the relevant information into a coherent summary. "
            "Highlight connections between sessions, key decisions, and actionable "
            "context that would be useful in a current conversation.\n\n"
            f"User query: {query}\n\n"
            "Matched sessions:\n"
            + "\n\n".join(session_contexts)
            + "\n\nProvide your recap below:"
        )

        try:
            client = self._get_llm_client()
            response = await client.chat.completions.create(
                model=self._llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("LLM recap generation failed: %s", exc)
            # Fallback
            parts = [f"Recap for: {query}\n"]
            for entry in sessions:
                parts.append(f"- {entry.title}: {entry.summary[:200] if entry.summary else 'No summary'}")
            return "\n".join(parts)

    # ------------------------------------------------------------------
    # Automatic session summarization
    # ------------------------------------------------------------------

    async def _summarize_session(
        self,
        title: str,
        transcript: str,
        message_count: int,
    ) -> tuple[str, list[str]]:
        """Generate an LLM summary and extract key topics from a transcript.

        Returns a (summary, key_topics) tuple. If the LLM call fails or the
        transcript is too small, returns a heuristic summary.
        """
        if not transcript.strip() or message_count < 2:
            return transcript[:500].strip(), []

        # Truncate transcript to avoid excessive token usage
        truncated = transcript[:12000] if len(transcript) > 12000 else transcript

        prompt = (
            "You are a session summarizer. Analyze the following conversation "
            "transcript and produce:\n"
            "1. A concise summary (2-5 sentences) capturing the main purpose, "
            "key decisions, and outcomes.\n"
            "2. A list of 3-8 key topics as comma-separated keywords or short phrases.\n\n"
            f"Session title: {title}\n"
            f"Message count: {message_count}\n\n"
            "Transcript:\n"
            f"{truncated}\n\n"
            "Respond in the following format:\n"
            "SUMMARY: <your summary here>\n"
            "TOPICS: <topic1>, <topic2>, <topic3>, ..."
        )

        try:
            client = self._get_llm_client()
            response = await client.chat.completions.create(
                model=self._llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
            )
            raw_output = response.choices[0].message.content or ""

            # Parse structured response
            summary = ""
            topics: list[str] = []

            summary_match_start = raw_output.find("SUMMARY:")
            topics_match_start = raw_output.find("TOPICS:")

            if summary_match_start != -1:
                if topics_match_start != -1:
                    summary = raw_output[summary_match_start + 8:topics_match_start].strip()
                else:
                    summary = raw_output[summary_match_start + 8:].strip()

            if topics_match_start != -1:
                topics_raw = raw_output[topics_match_start + 7:].strip()
                topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

            # Ensure we have at least a basic summary
            if not summary:
                summary = transcript[:300].strip()

            return summary, topics[:8]

        except Exception as exc:
            logger.error("Session summarization failed: %s", exc)
            # Heuristic fallback
            lines = transcript.strip().split("\n")
            fallback_summary = " ".join(line[:120] for line in lines[:5])
            return fallback_summary[:500], []

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    async def get_recent_sessions(
        self,
        limit: int = 10,
        agent_id: str | None = None,
    ) -> list[SessionEntry]:
        """Return recently updated sessions, optionally filtered by agent."""
        recent = self.index.get_recent_sessions(limit=limit * 2)
        if agent_id:
            recent = [e for e in recent if agent_id in e.agent_ids]
        return recent[:limit]

    async def reindex_session(self, conversation_id: str) -> SessionEntry | None:
        """Re-index a session (removes old entry, reads fresh from DB)."""
        self.index.remove_session(conversation_id)
        return await self.index_session(conversation_id, auto_summarize=True)

    async def remove_session(self, session_id: str) -> bool:
        """Remove a session from the index."""
        return self.index.remove_session(session_id)

    async def export_index(self) -> dict[str, Any]:
        """Export the full session index as a serializable dictionary."""
        return self.index.export_index()

    async def import_index(self, data: dict[str, Any]) -> int:
        """Import sessions from a previously exported index."""
        return self.index.import_index(data)

    async def save_index_to_file(self, filepath: str) -> None:
        """Persist the session index to a JSON file."""
        self.index.save_to_file(filepath)

    async def load_index_from_file(self, filepath: str) -> int:
        """Load the session index from a JSON file."""
        return self.index.load_from_file(filepath)

    @property
    def session_count(self) -> int:
        """Total number of indexed sessions."""
        return self.index.session_count

    # ------------------------------------------------------------------
    # Importance heuristic
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_importance(
        message_count: int,
        created_at: datetime | None = None,
    ) -> float:
        """Compute a heuristic importance score for a session.

        Based on message volume (log-scaled) and recency bonus.
        """
        # Base score from message count (log scale, max ~1.0 at 200+ messages)
        base = min(math.log(max(message_count, 1) + 1) / math.log(201), 1.0) * 0.7

        # Recency bonus: sessions from the last 7 days get up to 0.3 extra
        if created_at is not None:
            age_days = (datetime.now(timezone.utc) - created_at.replace(tzinfo=timezone.utc)).days
            recency = max(0.0, 0.3 * (1.0 - min(age_days, 30) / 30.0))
        else:
            recency = 0.0

        return round(min(base + recency, 1.0), 4)


# ══════════════════════════════════════════════════════════════
# Module-level convenience instance
# ══════════════════════════════════════════════════════════════

#: Shared SessionSearcher instance for cross-module use.
session_searcher = SessionSearcher()