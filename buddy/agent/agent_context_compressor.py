"""
Buddy Context Compressor - Intelligent Context Window Management.

Manages LLM context windows through summarization, pruning, prioritization,
and chunking. Ensures optimal context usage while preserving critical information.
Part of the AI-Native Buddy Agent system.
"""

from __future__ import annotations

import re
import time
import uuid
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import logging

logger = logging.getLogger("buddy.context_compressor")


class CompressionStrategy(str, Enum):
    """Strategies for compressing context."""
    SUMMARIZE = "summarize"         # Compress to summary
    TRUNCATE_OLDEST = "truncate_oldest"  # Remove oldest messages
    TRUNCATE_LEAST_IMPORTANT = "truncate_least"  # Remove least important
    SLIDING_WINDOW = "sliding_window"  # Keep recent + summaries
    HIERARCHICAL = "hierarchical"   # Multi-level compression
    TOKEN_BUDGET = "token_budget"   # Strict token budget allocation


class ContentPriority(str, Enum):
    """Priority levels for context content."""
    SYSTEM = "system"       # System prompts (highest)
    CRITICAL = "critical"   # Critical instructions
    CORE = "core"           # Core context
    RECENT = "recent"       # Recent messages
    RELEVANT = "relevant"   # Semantically relevant
    BACKGROUND = "background"  # Background context
    ARCHIVE = "archive"     # Archived (lowest)


@dataclass
class ContextChunk:
    """A chunk of context content."""
    chunk_id: str
    content: str
    role: str  # system, user, assistant, tool
    priority: ContentPriority = ContentPriority.BACKGROUND
    token_count: int = 0
    importance_score: float = 0.5
    timestamp: float = field(default_factory=time.time)
    summary: str | None = None
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompressionResult:
    """Result of a compression operation."""
    original_chunks: int
    compressed_chunks: int
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategy: CompressionStrategy
    removed_chunks: list[str]
    summary: str
    duration_ms: float = 0.0


class ContextCompressor:
    """Intelligent context window compression engine.

    Features:
    - Token-aware compression with configurable budgets
    - Priority-based content retention
    - Semantic summarization of background content
    - Sliding window with historical summaries
    - Hierarchical multi-level compression
    """

    DEFAULT_TOKEN_BUDGET = 8000
    SAFETY_MARGIN = 500  # Reserve tokens for response
    MIN_CHUNKS_TO_KEEP = 3

    def __init__(self, token_budget: int = DEFAULT_TOKEN_BUDGET) -> None:
        self._token_budget = token_budget
        self._chunks: OrderedDict[str, ContextChunk] = OrderedDict()
        self._summaries: list[str] = []
        self._total_compressions: int = 0
        self._total_tokens_saved: int = 0

    # ── Public API ────────────────────────────────────────────────

    def add_chunk(
        self,
        content: str,
        role: str = "user",
        priority: ContentPriority = ContentPriority.BACKGROUND,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> ContextChunk:
        """Add a content chunk to the context."""
        chunk = ContextChunk(
            chunk_id=f"ctx-{uuid.uuid4().hex[:8]}",
            content=content,
            role=role,
            priority=priority,
            token_count=self._estimate_tokens(content),
            importance_score=importance,
            metadata=metadata or {},
        )
        self._chunks[chunk.chunk_id] = chunk
        return chunk

    def add_system_message(self, content: str) -> ContextChunk:
        """Add a system-level message (highest priority)."""
        return self.add_chunk(content, role="system", priority=ContentPriority.SYSTEM, importance=1.0)

    def add_user_message(self, content: str) -> ContextChunk:
        return self.add_chunk(content, role="user", priority=ContentPriority.RECENT, importance=0.8)

    def add_assistant_message(self, content: str) -> ContextChunk:
        return self.add_chunk(content, role="assistant", priority=ContentPriority.RECENT, importance=0.7)

    def add_tool_result(self, content: str, importance: float = 0.6) -> ContextChunk:
        return self.add_chunk(content, role="tool", priority=ContentPriority.RELEVANT, importance=importance)

    def compress(
        self,
        strategy: CompressionStrategy = CompressionStrategy.HIERARCHICAL,
        target_tokens: int | None = None,
    ) -> CompressionResult:
        """Compress context to fit within token budget."""
        start = time.time()
        target = target_tokens or self._token_budget - self.SAFETY_MARGIN
        original_count = len(self._chunks)
        original_tokens = self._total_tokens()

        if original_tokens <= target and original_count <= self.MIN_CHUNKS_TO_KEEP * 2:
            return CompressionResult(
                original_chunks=original_count,
                compressed_chunks=original_count,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                strategy=strategy,
                removed_chunks=[],
                summary="No compression needed",
                duration_ms=(time.time() - start) * 1000,
            )

        if strategy == CompressionStrategy.SUMMARIZE:
            result = self._compress_summarize(target)
        elif strategy == CompressionStrategy.TRUNCATE_OLDEST:
            result = self._compress_truncate_oldest(target)
        elif strategy == CompressionStrategy.TRUNCATE_LEAST_IMPORTANT:
            result = self._compress_truncate_least(target)
        elif strategy == CompressionStrategy.SLIDING_WINDOW:
            result = self._compress_sliding_window(target)
        elif strategy == CompressionStrategy.HIERARCHICAL:
            result = self._compress_hierarchical(target)
        elif strategy == CompressionStrategy.TOKEN_BUDGET:
            result = self._compress_token_budget(target)
        else:
            result = self._compress_hierarchical(target)

        self._total_compressions += 1
        self._total_tokens_saved += original_tokens - result.compressed_tokens

        logger.info(
            f"Compression ({strategy.value}): {original_tokens} -> {result.compressed_tokens} tokens "
            f"({result.compression_ratio:.1%} ratio, {len(result.removed_chunks)} chunks removed)"
        )
        return result

    def get_context(
        self,
        max_tokens: int | None = None,
        include_summaries: bool = True,
    ) -> list[dict[str, Any]]:
        """Get the current context as a list of messages."""
        target = max_tokens or self._token_budget
        if self._total_tokens() > target:
            self.compress(target_tokens=target)

        chunks = self._get_ordered_chunks()
        messages: list[dict[str, Any]] = []

        # Add historical summaries as system context
        if include_summaries and self._summaries:
            summary_text = "\n".join(self._summaries[-3:])
            if summary_text:
                messages.append({
                    "role": "system",
                    "content": f"[Context Summary]\n{summary_text}",
                })

        for chunk in chunks:
            if chunk.role == "system":
                messages.append({"role": "system", "content": chunk.content})
            elif chunk.role == "user":
                messages.append({"role": "user", "content": chunk.content})
            elif chunk.role == "assistant":
                messages.append({"role": "assistant", "content": chunk.content})
            elif chunk.role == "tool":
                messages.append({"role": "tool", "content": chunk.content})
            else:
                messages.append({"role": "user", "content": chunk.content})

        return messages

    def get_context_text(self, max_tokens: int | None = None) -> str:
        """Get context as a single text string."""
        chunks = self._get_ordered_chunks()
        return "\n\n".join(c.content for c in chunks)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_chunks": len(self._chunks),
            "total_tokens": self._total_tokens(),
            "token_budget": self._token_budget,
            "total_compressions": self._total_compressions,
            "total_tokens_saved": self._total_tokens_saved,
            "summaries_count": len(self._summaries),
            "chunk_distribution": self._get_chunk_distribution(),
            "utilization": round(self._total_tokens() / self._token_budget, 3),
        }

    def set_token_budget(self, budget: int) -> None:
        self._token_budget = budget

    def clear(self) -> None:
        self._chunks.clear()
        self._summaries.clear()

    # ── Compression Strategies ───────────────────────────────────

    def _compress_summarize(self, target: int) -> CompressionResult:
        """Compress by summarizing background chunks."""
        removed: list[str] = []
        background = [c for c in self._chunks.values() if c.priority == ContentPriority.BACKGROUND]

        if background:
            combined = " ".join(c.content for c in background)
            summary = self._generate_summary(combined)
            self._summaries.append(summary)

            for c in background:
                removed.append(c.chunk_id)
                del self._chunks[c.chunk_id]

        return CompressionResult(
            original_chunks=len(self._chunks) + len(removed),
            compressed_chunks=len(self._chunks),
            original_tokens=self._total_tokens() + sum(self._estimate_tokens(c.content) for c in background),
            compressed_tokens=self._total_tokens(),
            compression_ratio=self._total_tokens() / max(self._total_tokens() + len(background), 1),
            strategy=CompressionStrategy.SUMMARIZE,
            removed_chunks=removed,
            summary=f"Summarized {len(removed)} background chunks",
        )

    def _compress_truncate_oldest(self, target: int) -> CompressionResult:
        """Remove oldest chunks until within budget."""
        removed: list[str] = []
        chunks = self._get_ordered_chunks()

        for chunk in chunks:
            if chunk.priority == ContentPriority.SYSTEM:
                continue
            if self._total_tokens() <= target:
                break
            removed.append(chunk.chunk_id)
            del self._chunks[chunk.chunk_id]

        return CompressionResult(
            original_chunks=len(self._chunks) + len(removed),
            compressed_chunks=len(self._chunks),
            original_tokens=self._total_tokens() + sum(self._estimate_tokens("") for _ in removed),
            compressed_tokens=self._total_tokens(),
            compression_ratio=len(self._chunks) / max(len(self._chunks) + len(removed), 1),
            strategy=CompressionStrategy.TRUNCATE_OLDEST,
            removed_chunks=removed,
            summary=f"Removed {len(removed)} oldest chunks",
        )

    def _compress_truncate_least(self, target: int) -> CompressionResult:
        """Remove least important chunks."""
        removed: list[str] = []
        chunks = sorted(
            self._chunks.values(),
            key=lambda c: (
                {
                    "system": 5, "critical": 4, "recent": 3, "relevant": 2, "background": 1, "archive": 0,
                }.get(c.priority.value, 1),
                c.importance_score,
                c.timestamp,
            ),
        )

        for chunk in chunks:
            if self._total_tokens() <= target:
                break
            if chunk.priority == ContentPriority.SYSTEM:
                continue
            removed.append(chunk.chunk_id)
            del self._chunks[chunk.chunk_id]

        return CompressionResult(
            original_chunks=len(self._chunks) + len(removed),
            compressed_chunks=len(self._chunks),
            original_tokens=self._total_tokens() + sum(self._estimate_tokens("") for _ in removed),
            compressed_tokens=self._total_tokens(),
            compression_ratio=len(self._chunks) / max(len(self._chunks) + len(removed), 1),
            strategy=CompressionStrategy.TRUNCATE_LEAST_IMPORTANT,
            removed_chunks=removed,
            summary=f"Removed {len(removed)} least important chunks",
        )

    def _compress_sliding_window(self, target: int) -> CompressionResult:
        """Keep recent chunks, summarize older ones."""
        removed: list[str] = []
        chunks = self._get_ordered_chunks()
        recent_count = min(len(chunks), self.MIN_CHUNKS_TO_KEEP * 2)

        # Summarize old chunks
        old = chunks[:-recent_count] if len(chunks) > recent_count else []
        if old:
            combined = " ".join(c.content for c in old)
            summary = self._generate_summary(combined)
            self._summaries.append(summary)
            for c in old:
                removed.append(c.chunk_id)
                del self._chunks[c.chunk_id]

        return CompressionResult(
            original_chunks=len(self._chunks) + len(removed),
            compressed_chunks=len(self._chunks),
            original_tokens=self._total_tokens() + sum(self._estimate_tokens(c.content) for c in old),
            compressed_tokens=self._total_tokens(),
            compression_ratio=len(self._chunks) / max(len(self._chunks) + len(removed), 1),
            strategy=CompressionStrategy.SLIDING_WINDOW,
            removed_chunks=removed,
            summary=f"Sliding window: kept {recent_count} recent, summarized {len(old)} older chunks",
        )

    def _compress_hierarchical(self, target: int) -> CompressionResult:
        """Multi-level compression: summarize background, truncate oldest, then least important."""
        # Level 1: Summarize background
        background = [c for c in self._chunks.values() if c.priority == ContentPriority.BACKGROUND]
        if background:
            combined = " ".join(c.content for c in background)
            self._summaries.append(self._generate_summary(combined))
            for c in background:
                del self._chunks[c.chunk_id]

        # Level 2: Truncate oldest non-system
        if self._total_tokens() > target:
            self._compress_truncate_oldest(target)

        # Level 3: Remove least important
        if self._total_tokens() > target:
            self._compress_truncate_least(target)

        return CompressionResult(
            original_chunks=len(self._chunks) + len(background),
            compressed_chunks=len(self._chunks),
            original_tokens=self._total_tokens() + sum(self._estimate_tokens(c.content) for c in background),
            compressed_tokens=self._total_tokens(),
            compression_ratio=self._total_tokens() / max(self._total_tokens() + len(background), 1),
            strategy=CompressionStrategy.HIERARCHICAL,
            removed_chunks=[c.chunk_id for c in background],
            summary=f"Hierarchical compression: summarized background, applied truncation",
        )

    def _compress_token_budget(self, target: int) -> CompressionResult:
        """Strict token budget allocation."""
        removed: list[str] = []
        chunks = self._get_ordered_chunks()

        # Allocate budget by priority
        budgets = {
            ContentPriority.SYSTEM: 0.30,
            ContentPriority.CRITICAL: 0.25,
            ContentPriority.RECENT: 0.25,
            ContentPriority.RELEVANT: 0.15,
            ContentPriority.BACKGROUND: 0.05,
            ContentPriority.ARCHIVE: 0.0,
        }

        for chunk in chunks:
            budget_share = budgets.get(chunk.priority, 0.05)
            chunk_budget = int(target * budget_share)
            if chunk.token_count > chunk_budget:
                # Truncate content
                chunk.content = self._truncate_to_tokens(chunk.content, chunk_budget)
                chunk.token_count = self._estimate_tokens(chunk.content)

        return CompressionResult(
            original_chunks=len(self._chunks),
            compressed_chunks=len(self._chunks),
            original_tokens=self._total_tokens(),
            compressed_tokens=self._total_tokens(),
            compression_ratio=self._total_tokens() / max(self._total_tokens(), 1),
            strategy=CompressionStrategy.TOKEN_BUDGET,
            removed_chunks=[],
            summary=f"Token budget applied across {len(chunks)} chunks",
        )

    # ── Internal Helpers ─────────────────────────────────────────

    def _total_tokens(self) -> int:
        return sum(c.token_count for c in self._chunks.values())

    def _get_ordered_chunks(self) -> list[ContextChunk]:
        """Get chunks ordered by priority then timestamp."""
        return sorted(
            self._chunks.values(),
            key=lambda c: (
                {
                    "system": 0, "critical": 1, "recent": 2, "relevant": 3, "background": 4, "archive": 5,
                }.get(c.priority.value, 3),
                -c.timestamp,
            ),
        )

    def _get_chunk_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = defaultdict(int)
        for c in self._chunks.values():
            dist[c.priority.value] += 1
        return dict(dist)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 1 token ≈ 4 chars)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _generate_summary(self, text: str, max_chars: int = 500) -> str:
        """Generate a concise summary of text."""
        if not text:
            return ""

        # Extract key sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) <= 3:
            return text[:max_chars]

        # Take first, middle, and last sentences
        key_sentences = []
        if sentences:
            key_sentences.append(sentences[0])
        if len(sentences) > 2:
            key_sentences.append(sentences[len(sentences) // 2])
        if len(sentences) > 1:
            key_sentences.append(sentences[-1])

        summary = " [...] ".join(key_sentences)
        return summary[:max_chars]

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget."""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 3] + "..."


# ── Global Singleton ─────────────────────────────────────────────

context_compressor = ContextCompressor()