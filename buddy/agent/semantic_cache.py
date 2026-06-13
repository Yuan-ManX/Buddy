"""Buddy Semantic Cache — Intent-aware response caching

Provides a semantic caching layer that stores and retrieves LLM responses
based on semantic similarity rather than exact text matching. Includes
TTL-based expiration, LRU eviction, and hit-rate analytics.

Features:
- Embedding-based semantic similarity matching
- Configurable similarity threshold for cache hits
- TTL-based entry expiration with background cleanup
- LRU eviction when capacity is reached
- Per-agent cache isolation
- Hit-rate tracking and analytics
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.cache")


# ══════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════

@dataclass
class CacheEntry:
    id: str
    query: str
    response: str
    embedding: list[float] | None = None
    agent_id: str = ""
    tokens_used: int = 0
    hits: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    ttl_seconds: float = 3600.0


# ══════════════════════════════════════════════════════════════
# Semantic Cache Engine
# ══════════════════════════════════════════════════════════════

class SemanticCache:
    """Intent-aware caching layer using semantic similarity matching.

    Stores query-response pairs keyed by embedding vectors, allowing
    retrieval of semantically similar past responses for new queries
    that aren't exact matches but convey the same intent.
    """

    DEFAULT_SIMILARITY_THRESHOLD = 0.92
    DEFAULT_MAX_ENTRIES = 1000
    DEFAULT_TTL_SECONDS = 3600
    CLEANUP_INTERVAL_SECONDS = 300

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}
        self._agent_index: dict[str, list[str]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._total_tokens_saved: int = 0
        self._cleanup_task: asyncio.Task | None = None
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    async def start(self):
        """Start the background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def get(self, query: str, agent_id: str = "") -> CacheEntry | None:
        """Search for a semantically similar cached response.

        Returns the CacheEntry if a match is found above the similarity
        threshold, otherwise returns None.
        """
        # Check exact match first (fast path)
        exact_key = f"{agent_id}:{query}"
        if exact_key in self._entries:
            entry = self._entries[exact_key]
            if not self._is_expired(entry):
                entry.hits += 1
                entry.last_accessed = time.time()
                self._hits += 1
                self._total_tokens_saved += entry.tokens_used
                return entry

        # Semantic search (slow path)
        candidate_ids = self._agent_index.get(agent_id, [])
        if not candidate_ids:
            candidate_ids = list(self._entries.keys())

        if not candidate_ids:
            self._misses += 1
            return None

        try:
            query_embedding = await self._get_embedding(query)
            best_match: CacheEntry | None = None
            best_similarity = 0.0

            for cid in candidate_ids[:50]:  # Limit search scope
                entry = self._entries.get(cid)
                if not entry or self._is_expired(entry):
                    continue
                if entry.embedding is None:
                    continue

                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = entry

            if best_match:
                best_match.hits += 1
                best_match.last_accessed = time.time()
                self._hits += 1
                self._total_tokens_saved += best_match.tokens_used
                logger.debug(f"Semantic cache hit: similarity={best_similarity:.4f}")
                return best_match

        except Exception as e:
            logger.debug(f"Semantic cache search failed: {e}")

        self._misses += 1
        return None

    async def set(
        self,
        query: str,
        response: str,
        agent_id: str = "",
        tokens_used: int = 0,
    ):
        """Store a query-response pair in the semantic cache."""
        key = f"{agent_id}:{query}"

        # Evict if at capacity
        if len(self._entries) >= self.max_entries:
            self._evict_lru()

        embedding = None
        try:
            embedding = await self._get_embedding(query)
        except Exception as e:
            logger.debug(f"Failed to embed query for cache: {e}")

        entry = CacheEntry(
            id=f"cache-{uuid.uuid4().hex[:12]}",
            query=query,
            response=response,
            embedding=embedding,
            agent_id=agent_id,
            tokens_used=tokens_used,
        )
        self._entries[key] = entry

        if agent_id not in self._agent_index:
            self._agent_index[agent_id] = []
        if key not in self._agent_index[agent_id]:
            self._agent_index[agent_id].append(key)

    def invalidate(self, agent_id: str = ""):
        """Invalidate all cache entries for a given agent."""
        if agent_id:
            keys = self._agent_index.pop(agent_id, [])
            for key in keys:
                self._entries.pop(key, None)
        else:
            self._entries.clear()
            self._agent_index.clear()

    def _evict_lru(self):
        """Evict the least recently used entry."""
        if not self._entries:
            return
        lru_key = min(self._entries.keys(), key=lambda k: self._entries[k].last_accessed)
        entry = self._entries.pop(lru_key, None)
        if entry and entry.agent_id in self._agent_index:
            self._agent_index[entry.agent_id].remove(lru_key)

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired."""
        return (time.time() - entry.created_at) > entry.ttl_seconds

    async def _cleanup_loop(self):
        """Background task that periodically removes expired entries."""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                expired = [
                    k for k, e in self._entries.items()
                    if self._is_expired(e)
                ]
                for key in expired:
                    entry = self._entries.pop(key, None)
                    if entry and entry.agent_id in self._agent_index:
                        self._agent_index[entry.agent_id].remove(key)
                if expired:
                    logger.debug(f"Semantic cache cleanup: evicted {len(expired)} expired entries")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Semantic cache cleanup error: {e}")

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for a text query."""
        response = await self._client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],  # Truncate to embedding model limit
        )
        return response.data[0].embedding

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))

    # ── Statistics ─────────────────────────────────────

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / max(total, 1)

    @property
    def size(self) -> int:
        return len(self._entries)

    def get_stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "total_entries": len(self._entries),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{(self.hit_rate * 100):.1f}%",
            "total_requests": total,
            "tokens_saved": self._total_tokens_saved,
            "estimated_cost_saved": round(self._total_tokens_saved * 0.000002, 4),
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
            "similarity_threshold": self.similarity_threshold,
        }


# ── Singleton ────────────────────────────────────────────

semantic_cache = SemanticCache()