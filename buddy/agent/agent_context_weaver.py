"""
Agent Context Weaver - Intelligent context assembly and prioritization.

Weaves together multiple context sources into optimized prompts:
- Multi-source context fusion (memory, knowledge, tools, conversation)
- Dynamic context window management with intelligent pruning
- Relevance-based prioritization and scoring
- Cross-reference resolution and deduplication
- Context compression with semantic preservation
- Adaptive context assembly based on task requirements
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.context_weaver")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class ContextSource(str, Enum):
    """Source of context information."""
    CONVERSATION_HISTORY = "conversation_history"
    AGENT_MEMORY = "agent_memory"
    KNOWLEDGE_BASE = "knowledge_base"
    TOOL_OUTPUT = "tool_output"
    SYSTEM_PROMPT = "system_prompt"
    USER_PROFILE = "user_profile"
    SKILL_DEFINITION = "skill_definition"
    EXTERNAL_API = "external_api"
    DOCUMENT = "document"
    CODE_CONTEXT = "code_context"


class ContextPriority(str, Enum):
    """Priority level for context items."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVAL = "archival"


class WeaveStrategy(str, Enum):
    """Strategy for weaving context together."""
    HIERARCHICAL = "hierarchical"
    TEMPORAL = "temporal"
    RELEVANCE_SCORED = "relevance_scored"
    TASK_SPECIFIC = "task_specific"
    FUSION = "fusion"
    COMPRESSED = "compressed"


class CompressionMethod(str, Enum):
    """Method for compressing context."""
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    TRUNCATION = "truncation"
    EMBEDDING = "embedding"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class ContextItem:
    """A single piece of context."""
    item_id: str
    source: ContextSource
    content: str
    priority: ContextPriority = ContextPriority.MEDIUM
    relevance_score: float = 0.5
    token_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = field(default_factory=list)
    expires_at: datetime | None = None
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source": self.source.value,
            "content_preview": self.content[:100],
            "priority": self.priority.value,
            "relevance_score": self.relevance_score,
            "token_count": self.token_count,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class ContextBundle:
    """A collection of context items assembled for a task."""
    bundle_id: str
    task_id: str
    items: list[ContextItem]
    strategy: WeaveStrategy
    total_tokens: int
    max_tokens: int
    compression_ratio: float
    assembled_text: str
    priority_distribution: dict[str, int]
    source_distribution: dict[str, int]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "task_id": self.task_id,
            "item_count": len(self.items),
            "strategy": self.strategy.value,
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "compression_ratio": self.compression_ratio,
            "assembled_text_preview": self.assembled_text[:200],
            "priority_distribution": self.priority_distribution,
            "source_distribution": self.source_distribution,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class WeaveConfig:
    """Configuration for a single weave operation."""
    max_total_tokens: int = 8000
    min_priority: ContextPriority = ContextPriority.LOW
    sources: list[ContextSource] | None = None
    strategy: WeaveStrategy = WeaveStrategy.RELEVANCE_SCORED
    compression: CompressionMethod = CompressionMethod.TRUNCATION
    deduplicate: bool = True
    sort_by: str = "relevance"
    max_items_per_source: int = 10


@dataclass
class WeaverStats:
    """Statistics for the context weaver."""
    total_weaves: int = 0
    total_items_processed: int = 0
    total_tokens_saved: int = 0
    avg_compression_ratio: float = 0.0
    avg_items_per_bundle: float = 0.0
    source_usage: dict[str, int] = field(default_factory=dict)
    strategy_usage: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_weaves": self.total_weaves,
            "total_items_processed": self.total_items_processed,
            "total_tokens_saved": self.total_tokens_saved,
            "avg_compression_ratio": self.avg_compression_ratio,
            "avg_items_per_bundle": self.avg_items_per_bundle,
            "source_usage": self.source_usage,
            "strategy_usage": self.strategy_usage,
        }


# ═══════════════════════════════════════════════════════════
# Context Weaver
# ═══════════════════════════════════════════════════════════

class ContextWeaver:
    """
    Intelligent context assembly and prioritization engine.
    
    Features:
    - Multi-source context fusion with configurable strategies
    - Dynamic token budget management with smart pruning
    - Relevance scoring and priority-based selection
    - Cross-reference resolution and deduplication
    - Context compression with semantic preservation
    - Adaptive assembly based on task requirements
    """

    def __init__(self, config: ContextWeaverConfig | None = None):
        self.config = config or ContextWeaverConfig()
        self._context_store: dict[str, ContextItem] = {}
        self._bundles: dict[str, ContextBundle] = {}
        self._stats = WeaverStats()

    # ── Context Management ──

    def add_context(self, item: ContextItem) -> str:
        """Add a context item to the store."""
        if not item.token_count:
            item.token_count = self._estimate_tokens(item.content)
        self._context_store[item.item_id] = item
        return item.item_id

    def add_contexts(self, items: list[ContextItem]) -> list[str]:
        """Add multiple context items."""
        return [self.add_context(item) for item in items]

    def remove_context(self, item_id: str) -> bool:
        """Remove a context item."""
        if item_id in self._context_store:
            del self._context_store[item_id]
            return True
        return False

    def clear_expired(self) -> int:
        """Remove expired context items."""
        now = datetime.now(timezone.utc)
        expired = [
            iid for iid, item in self._context_store.items()
            if item.expires_at and item.expires_at < now
        ]
        for iid in expired:
            del self._context_store[iid]
        return len(expired)

    # ── Weaving ──

    def weave(
        self,
        task_id: str,
        query: str = "",
        config: WeaveConfig | None = None,
    ) -> ContextBundle:
        """
        Weave context items into an optimized context bundle.
        
        Args:
            task_id: Task identifier for the bundle
            query: Current query for relevance scoring
            config: Weave configuration
            
        Returns:
            ContextBundle with assembled and optimized context
        """
        config = config or WeaveConfig()
        start = time.time()

        # Filter by source
        items = list(self._context_store.values())
        if config.sources:
            items = [i for i in items if i.source in config.sources]

        # Filter by minimum priority
        priority_order = {
            ContextPriority.CRITICAL: 0,
            ContextPriority.HIGH: 1,
            ContextPriority.MEDIUM: 2,
            ContextPriority.LOW: 3,
            ContextPriority.ARCHIVAL: 4,
        }
        min_priority_value = priority_order.get(config.min_priority, 3)
        items = [i for i in items if priority_order.get(i.priority, 3) <= min_priority_value]

        # Score relevance
        if query:
            items = self._score_relevance(items, query)

        # Deduplicate
        if config.deduplicate:
            items = self._deduplicate(items)

        # Sort by configured method
        if config.sort_by == "relevance":
            items.sort(key=lambda i: i.relevance_score, reverse=True)
        elif config.sort_by == "priority":
            items.sort(key=lambda i: priority_order.get(i.priority, 3))
        elif config.sort_by == "temporal":
            items.sort(key=lambda i: i.timestamp, reverse=True)

        # Limit per source
        if config.max_items_per_source > 0:
            source_counts: dict[str, int] = defaultdict(int)
            limited_items = []
            for item in items:
                source_key = item.source.value
                if source_counts[source_key] < config.max_items_per_source:
                    limited_items.append(item)
                    source_counts[source_key] += 1
            items = limited_items

        # Apply token budget
        selected_items, total_tokens = self._apply_token_budget(
            items, config.max_total_tokens
        )

        # Apply compression if needed
        original_tokens = sum(i.token_count for i in selected_items)
        if original_tokens > config.max_total_tokens:
            selected_items = self._compress_items(
                selected_items, config.max_total_tokens, config.compression
            )
            total_tokens = sum(i.token_count for i in selected_items)

        compression_ratio = (
            total_tokens / max(1, original_tokens)
        )

        # Assemble final text
        assembled_text = self._assemble_text(selected_items, config.strategy)

        # Calculate distributions
        priority_dist = defaultdict(int)
        source_dist = defaultdict(int)
        for item in selected_items:
            priority_dist[item.priority.value] += 1
            source_dist[item.source.value] += 1

        bundle = ContextBundle(
            bundle_id=str(uuid.uuid4())[:8],
            task_id=task_id,
            items=selected_items,
            strategy=config.strategy,
            total_tokens=total_tokens,
            max_tokens=config.max_total_tokens,
            compression_ratio=round(compression_ratio, 3),
            assembled_text=assembled_text,
            priority_distribution=dict(priority_dist),
            source_distribution=dict(source_dist),
        )

        self._bundles[bundle.bundle_id] = bundle
        self._update_stats(bundle, len(items), original_tokens - total_tokens)

        logger.info(
            "Weave %s: %d items, %d tokens, ratio=%.2f, strategy=%s",
            bundle.bundle_id, len(selected_items), total_tokens,
            compression_ratio, config.strategy.value,
        )

        return bundle

    def _score_relevance(
        self, items: list[ContextItem], query: str
    ) -> list[ContextItem]:
        """Score items by relevance to the query."""
        query_terms = set(query.lower().split())
        query_terms = {t for t in query_terms if len(t) > 2}

        for item in items:
            if not query_terms:
                item.relevance_score = 0.5
                continue

            content_lower = item.content.lower()
            term_matches = sum(1 for t in query_terms if t in content_lower)
            tag_matches = sum(1 for t in query_terms if any(t in tag.lower() for tag in item.tags))

            base_score = (term_matches / max(1, len(query_terms))) * 0.7
            tag_bonus = (tag_matches / max(1, len(query_terms))) * 0.3
            priority_bonus = {
                ContextPriority.CRITICAL: 0.3,
                ContextPriority.HIGH: 0.2,
                ContextPriority.MEDIUM: 0.1,
                ContextPriority.LOW: 0.0,
                ContextPriority.ARCHIVAL: -0.2,
            }.get(item.priority, 0.0)

            recency_bonus = 0.0
            age_seconds = (datetime.now(timezone.utc) - item.timestamp).total_seconds()
            if age_seconds < 3600:
                recency_bonus = 0.1
            elif age_seconds < 86400:
                recency_bonus = 0.05

            item.relevance_score = min(1.0, max(0.0, base_score + tag_bonus + priority_bonus + recency_bonus))

        return items

    def _deduplicate(self, items: list[ContextItem]) -> list[ContextItem]:
        """Remove duplicate or near-duplicate context items."""
        seen_hashes: set[str] = set()
        unique: list[ContextItem] = []

        for item in items:
            content_hash = hashlib.md5(item.content[:200].encode()).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(item)

        return unique

    def _apply_token_budget(
        self, items: list[ContextItem], max_tokens: int
    ) -> tuple[list[ContextItem], int]:
        """Apply token budget, prioritizing higher relevance/priority items."""
        selected = []
        total_tokens = 0

        for item in items:
            if total_tokens + item.token_count <= max_tokens:
                selected.append(item)
                total_tokens += item.token_count
            else:
                break

        return selected, total_tokens

    def _compress_items(
        self,
        items: list[ContextItem],
        max_tokens: int,
        method: CompressionMethod,
    ) -> list[ContextItem]:
        """Compress context items to fit token budget."""
        current_tokens = sum(i.token_count for i in items)
        if current_tokens <= max_tokens:
            return items

        if method == CompressionMethod.TRUNCATION:
            return self._truncate_items(items, max_tokens)
        elif method == CompressionMethod.KEYWORD:
            return self._keyword_compress(items, max_tokens)
        elif method == CompressionMethod.SUMMARIZATION:
            return self._summarize_items(items, max_tokens)
        else:
            return self._truncate_items(items, max_tokens)

    def _truncate_items(
        self, items: list[ContextItem], max_tokens: int
    ) -> list[ContextItem]:
        """Truncate items to fit token budget."""
        ratio = max_tokens / max(1, sum(i.token_count for i in items))
        for item in items:
            new_length = max(50, int(len(item.content) * ratio))
            item.content = item.content[:new_length] + "..."
            item.token_count = self._estimate_tokens(item.content)
        return items

    def _keyword_compress(
        self, items: list[ContextItem], max_tokens: int
    ) -> list[ContextItem]:
        """Compress by extracting key sentences."""
        for item in items:
            sentences = re.split(r'[.!?]+', item.content)
            if len(sentences) > 3:
                item.content = ". ".join(sentences[:3]) + "."
                item.token_count = self._estimate_tokens(item.content)
        return items

    def _summarize_items(
        self, items: list[ContextItem], max_tokens: int
    ) -> list[ContextItem]:
        """Summarize items (placeholder for LLM-based summarization)."""
        for item in items:
            if len(item.content) > 500:
                item.content = item.content[:200] + " [summarized]"
                item.token_count = self._estimate_tokens(item.content)
        return items

    def _assemble_text(
        self, items: list[ContextItem], strategy: WeaveStrategy
    ) -> str:
        """Assemble context items into formatted text."""
        if strategy == WeaveStrategy.HIERARCHICAL:
            return self._assemble_hierarchical(items)
        elif strategy == WeaveStrategy.TEMPORAL:
            return self._assemble_temporal(items)
        elif strategy == WeaveStrategy.FUSION:
            return self._assemble_fusion(items)
        elif strategy == WeaveStrategy.COMPRESSED:
            return self._assemble_compressed(items)
        else:
            return self._assemble_relevance_scored(items)

    def _assemble_hierarchical(self, items: list[ContextItem]) -> str:
        """Assemble in hierarchical order (critical first)."""
        parts = []
        current_priority = None

        for item in items:
            if item.priority != current_priority:
                current_priority = item.priority
                parts.append(f"\n[{current_priority.value.upper()} CONTEXT]\n")
            parts.append(f"[{item.source.value}] {item.content}")

        return "\n".join(parts)

    def _assemble_temporal(self, items: list[ContextItem]) -> str:
        """Assemble in temporal order."""
        items.sort(key=lambda i: i.timestamp)
        parts = []
        for item in items:
            ts = item.timestamp.strftime("%H:%M:%S")
            parts.append(f"[{ts}] [{item.source.value}] {item.content}")
        return "\n".join(parts)

    def _assemble_relevance_scored(self, items: list[ContextItem]) -> str:
        """Assemble by relevance score."""
        items.sort(key=lambda i: i.relevance_score, reverse=True)
        parts = []
        for item in items:
            parts.append(f"[{item.source.value}|{item.relevance_score:.2f}] {item.content}")
        return "\n\n".join(parts)

    def _assemble_fusion(self, items: list[ContextItem]) -> str:
        """Fuse context items into a unified narrative."""
        parts = ["Context Fusion:\n"]
        for item in items:
            parts.append(f"- {item.content}")
        return "\n".join(parts)

    def _assemble_compressed(self, items: list[ContextItem]) -> str:
        """Assemble in compressed format."""
        parts = []
        for item in items:
            parts.append(f"[{item.source.value}] {item.content[:100]}")
        return " | ".join(parts)

    # ── Helpers ──

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 4 chars ≈ 1 token)."""
        return max(1, len(text) // 4)

    def _update_stats(
        self, bundle: ContextBundle, total_candidates: int, tokens_saved: int
    ) -> None:
        """Update weaver statistics."""
        self._stats.total_weaves += 1
        self._stats.total_items_processed += len(bundle.items)
        self._stats.total_tokens_saved += tokens_saved

        n = self._stats.total_weaves
        self._stats.avg_compression_ratio = (
            (self._stats.avg_compression_ratio * (n - 1) + bundle.compression_ratio) / n
        )
        self._stats.avg_items_per_bundle = (
            (self._stats.avg_items_per_bundle * (n - 1) + len(bundle.items)) / n
        )

        for source, count in bundle.source_distribution.items():
            self._stats.source_usage[source] = (
                self._stats.source_usage.get(source, 0) + count
            )
        self._stats.strategy_usage[bundle.strategy.value] = (
            self._stats.strategy_usage.get(bundle.strategy.value, 0) + 1
        )

    def get_stats(self) -> WeaverStats:
        """Get current weaver statistics."""
        return self._stats

    def get_bundle(self, bundle_id: str) -> ContextBundle | None:
        """Get a context bundle by ID."""
        return self._bundles.get(bundle_id)

    def get_context_count(self) -> int:
        """Get total context items in store."""
        return len(self._context_store)

    def list_bundles(self, limit: int = 50) -> list[ContextBundle]:
        """List recent context bundles."""
        return list(self._bundles.values())[-limit:]

    def reset(self) -> None:
        """Reset the context weaver."""
        self._context_store.clear()
        self._bundles.clear()
        self._stats = WeaverStats()
        logger.info("Context weaver reset")


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@dataclass
class ContextWeaverConfig:
    """Configuration for the context weaver."""
    default_max_tokens: int = 8000
    default_strategy: WeaveStrategy = WeaveStrategy.RELEVANCE_SCORED
    default_compression: CompressionMethod = CompressionMethod.TRUNCATION
    auto_deduplicate: bool = True
    auto_expire_seconds: int = 3600
    max_stored_items: int = 1000
    collect_metrics: bool = True


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_context_weaver: ContextWeaver | None = None


def get_context_weaver() -> ContextWeaver:
    """Get or create the singleton context weaver."""
    global _context_weaver
    if _context_weaver is None:
        _context_weaver = ContextWeaver()
    return _context_weaver


def reset_context_weaver() -> None:
    """Reset the singleton context weaver."""
    global _context_weaver
    if _context_weaver:
        _context_weaver.reset()
    _context_weaver = None