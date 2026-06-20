"""
Buddy Agent Context Manager - Intelligent context window optimization.

Manages the agent's context window by intelligently pruning, summarizing,
and prioritizing content. Ensures critical information is preserved while
maximizing the effective use of limited context space.

Key capabilities:
- Token-aware content budgeting and allocation
- Priority-based content retention with aging
- Automatic summarization of low-priority content
- Context snapshot and restoration
- Cross-session context preservation
- Context compression with semantic summarization
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ContextPriority(str, Enum):
    """Priority levels for context items."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVABLE = "archivable"


class ContextType(str, Enum):
    """Types of context items."""
    SYSTEM_PROMPT = "system_prompt"
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_RESULT = "tool_result"
    MEMORY_ENTRY = "memory_entry"
    KNOWLEDGE_FACT = "knowledge_fact"
    SKILL_CONTEXT = "skill_context"
    REFLECTION = "reflection"
    METADATA = "metadata"


@dataclass
class ContextItem:
    """A single item in the context window."""
    item_id: str
    content: str
    context_type: ContextType
    priority: ContextPriority = ContextPriority.MEDIUM
    token_count: int = 0
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    pinned: bool = False
    summary: str = ""
    related_items: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    @property
    def relevance_score(self) -> float:
        """Calculate relevance based on recency, access, and priority."""
        priority_weight = {
            ContextPriority.CRITICAL: 1.0,
            ContextPriority.HIGH: 0.8,
            ContextPriority.MEDIUM: 0.5,
            ContextPriority.LOW: 0.2,
            ContextPriority.ARCHIVABLE: 0.05,
        }[self.priority]

        recency_factor = max(0.1, 1.0 - self.age_seconds / 3600)
        access_factor = min(1.0, self.access_count / 10)

        return (priority_weight * 0.5 + recency_factor * 0.3 + access_factor * 0.2)


@dataclass
class ContextSnapshot:
    """A snapshot of the context window at a point in time."""
    snapshot_id: str
    agent_id: str
    items: list[ContextItem] = field(default_factory=list)
    total_tokens: int = 0
    created_at: float = field(default_factory=time.time)
    label: str = ""


class AgentContextManager:
    """Intelligent context window manager for Buddy agents.

    Manages the limited context window by prioritizing, pruning, and
    summarizing content. Ensures critical information is preserved
    while maximizing effective use of available context space.
    """

    def __init__(self, max_tokens: int = 128000, reserve_tokens: int = 4096):
        self._items: dict[str, ContextItem] = {}
        self._snapshots: dict[str, ContextSnapshot] = {}
        self._max_tokens = max_tokens
        self._reserve_tokens = reserve_tokens
        self._total_tokens = 0
        self._total_items = 0
        self._total_pruned = 0
        self._total_summarized = 0

    @property
    def available_tokens(self) -> int:
        return self._max_tokens - self._total_tokens - self._reserve_tokens

    def add(
        self,
        content: str,
        context_type: ContextType,
        priority: ContextPriority = ContextPriority.MEDIUM,
        pin: bool = False,
        token_count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ContextItem:
        """Add an item to the context window."""
        if token_count is None:
            token_count = self._estimate_tokens(content)

        item_id = f"ctx-{uuid.uuid4().hex[:12]}"
        item = ContextItem(
            item_id=item_id,
            content=content,
            context_type=context_type,
            priority=priority,
            token_count=token_count,
            pinned=pin,
            metadata=metadata or {},
        )

        self._items[item_id] = item
        self._total_tokens += token_count
        self._total_items += 1

        # Auto-prune if over budget
        if self._total_tokens > self._max_tokens:
            self._auto_prune()

        return item

    def access(self, item_id: str) -> ContextItem | None:
        """Record an access to a context item."""
        item = self._items.get(item_id)
        if item:
            item.access_count += 1
            item.last_accessed = time.time()
        return item

    def get(self, item_id: str) -> ContextItem | None:
        """Get a context item by ID."""
        item = self._items.get(item_id)
        if item:
            item.access_count += 1
            item.last_accessed = time.time()
        return item

    def update(
        self,
        item_id: str,
        content: str | None = None,
        priority: ContextPriority | None = None,
        pin: bool | None = None,
    ) -> ContextItem | None:
        """Update a context item."""
        item = self._items.get(item_id)
        if not item:
            return None

        if content is not None:
            old_tokens = item.token_count
            item.content = content
            item.token_count = self._estimate_tokens(content)
            self._total_tokens += item.token_count - old_tokens

        if priority is not None:
            item.priority = priority
        if pin is not None:
            item.pinned = pin

        return item

    def summarize(self, item_id: str, summary: str) -> ContextItem | None:
        """Replace an item's content with a summary to save tokens."""
        item = self._items.get(item_id)
        if not item:
            return None

        old_tokens = item.token_count
        item.summary = item.content[:500]  # Keep original prefix
        item.content = summary
        item.token_count = self._estimate_tokens(summary)
        item.priority = ContextPriority.LOW
        self._total_tokens += item.token_count - old_tokens
        self._total_summarized += 1

        return item

    def remove(self, item_id: str) -> bool:
        """Remove an item from the context window."""
        item = self._items.get(item_id)
        if not item:
            return False

        if item.pinned:
            return False

        self._total_tokens -= item.token_count
        del self._items[item_id]
        self._total_pruned += 1
        return True

    def query(
        self,
        context_type: ContextType | None = None,
        priority: ContextPriority | None = None,
        min_relevance: float = 0.0,
        limit: int = 50,
        include_summarized: bool = True,
    ) -> list[ContextItem]:
        """Query context items with filters."""
        results = list(self._items.values())

        if context_type:
            results = [r for r in results if r.context_type == context_type]
        if priority:
            results = [r for r in results if r.priority == priority]
        if min_relevance > 0:
            results = [r for r in results if r.relevance_score >= min_relevance]

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def build_context_window(
        self, max_tokens: int | None = None
    ) -> list[ContextItem]:
        """Build the optimal context window within token budget."""
        budget = max_tokens or self.available_tokens
        items = sorted(
            self._items.values(),
            key=lambda i: (i.pinned, i.relevance_score),
            reverse=True,
        )

        window: list[ContextItem] = []
        used_tokens = 0

        for item in items:
            if used_tokens + item.token_count <= budget:
                window.append(item)
                used_tokens += item.token_count
            else:
                break

        return window

    def create_snapshot(self, agent_id: str, label: str = "") -> ContextSnapshot:
        """Create a snapshot of the current context."""
        snapshot = ContextSnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            items=list(self._items.values()),
            total_tokens=self._total_tokens,
            label=label,
        )
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore context from a snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False

        self._items = {item.item_id: item for item in snapshot.items}
        self._total_tokens = snapshot.total_tokens
        return True

    def get_stats(self) -> dict:
        """Get context manager statistics."""
        type_counts = {}
        priority_counts = {}
        for item in self._items.values():
            t = item.context_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
            p = item.priority.value
            priority_counts[p] = priority_counts.get(p, 0) + 1

        return {
            "total_items": self._total_items,
            "active_items": len(self._items),
            "total_tokens": self._total_tokens,
            "max_tokens": self._max_tokens,
            "available_tokens": self.available_tokens,
            "utilization": round(self._total_tokens / self._max_tokens * 100, 1),
            "total_pruned": self._total_pruned,
            "total_summarized": self._total_summarized,
            "total_snapshots": len(self._snapshots),
            "pinned_items": sum(1 for i in self._items.values() if i.pinned),
            "by_type": type_counts,
            "by_priority": priority_counts,
        }

    def _auto_prune(self) -> None:
        """Automatically prune low-priority items to stay within budget."""
        if self._total_tokens <= self._max_tokens:
            return

        # Sort by relevance (lowest first), excluding pinned and critical
        candidates = sorted(
            [
                i for i in self._items.values()
                if not i.pinned and i.priority != ContextPriority.CRITICAL
            ],
            key=lambda i: i.relevance_score,
        )

        for item in candidates:
            if self._total_tokens <= self._max_tokens * 0.85:
                break
            if item.priority == ContextPriority.ARCHIVABLE:
                self.remove(item.item_id)
            elif item.priority == ContextPriority.LOW:
                # Summarize instead of removing
                self.summarize(item.item_id, f"[Summary of: {item.content[:100]}...]")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: ~4 chars per token)."""
        return max(1, len(text) // 4)


# Global singleton
context_manager = AgentContextManager()