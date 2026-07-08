"""Buddy Memory Provider — unified memory contract with hard-capped providers

Consolidates the 9 overlapping memory modules (memory.py, white_memory.py,
whitebox_memory.py, memory_sync.py, agent_memory_*.py) behind a single
MemoryProvider ABC. The MemoryManager enforces a hard cap: the builtin
provider is always-on, and at most ONE external provider may be registered.
A second external registration is rejected with a warning.

This prevents tool schema bloat and conflicting memory backends — the
exact pathology that fragmented the previous memory layer.

Lifecycle hooks:
  - initialize(): one-time setup (connect, load state)
  - system_prompt_block(): inject context into the agent's system prompt
  - prefetch(query): warm up before the LLM turn
  - sync_turn(messages, tool_results): persist outcomes after a turn
  - get_tool_schemas(): expose memory tools to the LLM
  - handle_tool_call(name, args): dispatch memory tool calls
  - shutdown(): cleanup on session end
  - on_turn_start(): hook called at the beginning of each turn
  - on_session_end(): hook called when a session terminates
  - on_pre_compress(): hook called before trajectory compression
  - on_memory_write(entry): hook called when a memory entry is written
  - on_delegation(target_agent): hook called when delegating to another agent
"""
from __future__ import annotations

import abc
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("buddy.memory_provider")


# ═══════════════════════════════════════════════════════════
# Memory entry data structure
# ═══════════════════════════════════════════════════════════

@dataclass
class MemoryEntry:
    """A single memory entry stored by a memory provider."""
    id: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    embedding: Optional[list[float]] = None
    relevance_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "relevance_score": self.relevance_score,
        }


@dataclass
class MemorySearchResult:
    """Result of a memory search query."""
    entries: list[MemoryEntry] = field(default_factory=list)
    total: int = 0
    provider: str = ""
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total": self.total,
            "provider": self.provider,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


# ═══════════════════════════════════════════════════════════
# Memory Provider ABC
# ═══════════════════════════════════════════════════════════

class MemoryProvider(abc.ABC):
    """Abstract base class for memory providers.

    All memory backends (builtin, vector DB, graph DB, external API)
    implement this contract. The MemoryManager coordinates between
    the builtin provider (always-on) and at most one external provider.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name for identification."""
        ...

    @property
    @abc.abstractmethod
    def is_builtin(self) -> bool:
        """Whether this is the builtin provider (always-on)."""
        ...

    # ── Lifecycle ────────────────────────────────────────

    @abc.abstractmethod
    async def initialize(self) -> None:
        """One-time setup: connect, load state, prepare resources."""
        ...

    @abc.abstractmethod
    async def shutdown(self) -> None:
        """Cleanup on session end: flush, disconnect, save state."""
        ...

    # ── Core operations ──────────────────────────────────

    @abc.abstractmethod
    async def system_prompt_block(self, agent_id: str) -> str:
        """Return a text block to inject into the agent's system prompt."""
        ...

    @abc.abstractmethod
    async def prefetch(self, query: str, agent_id: str = "default") -> None:
        """Warm up the provider before the LLM turn begins."""
        ...

    @abc.abstractmethod
    async def sync_turn(
        self,
        messages: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        agent_id: str = "default",
    ) -> None:
        """Persist outcomes after a turn completes."""
        ...

    @abc.abstractmethod
    async def search(
        self,
        query: str,
        agent_id: str = "default",
        limit: int = 5,
    ) -> MemorySearchResult:
        """Search memory for entries relevant to the query."""
        ...

    @abc.abstractmethod
    async def store(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        agent_id: str = "default",
    ) -> str:
        """Store a memory entry. Returns the entry ID."""
        ...

    # ── Tool interface ───────────────────────────────────

    @abc.abstractmethod
    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool schemas for memory operations."""
        ...

    @abc.abstractmethod
    async def handle_tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Handle a tool call dispatched to this provider."""
        ...

    # ── Optional lifecycle hooks (override if needed) ────

    async def on_turn_start(self, agent_id: str) -> None:
        """Hook called at the beginning of each turn."""
        pass

    async def on_session_end(self, agent_id: str) -> None:
        """Hook called when a session terminates."""
        pass

    async def on_pre_compress(self, agent_id: str) -> None:
        """Hook called before trajectory compression."""
        pass

    async def on_memory_write(self, entry: MemoryEntry) -> None:
        """Hook called when a memory entry is written."""
        pass

    async def on_delegation(self, target_agent: str, context: dict[str, Any]) -> None:
        """Hook called when delegating to another agent."""
        pass


# ═══════════════════════════════════════════════════════════
# Builtin Memory Provider — always-on, in-process memory
# ═══════════════════════════════════════════════════════════

class BuiltinMemoryProvider(MemoryProvider):
    """The always-on builtin memory provider.

    Provides in-process memory with keyword search. This is the baseline
    memory that every agent has access to, regardless of external
    configuration. Wraps the existing memory.py MemorySystem when
    available, falling back to a simple in-memory store.
    """

    def __init__(self):
        self._entries: dict[str, list[MemoryEntry]] = {}  # agent_id -> entries
        self._lock = threading.RLock()
        self._initialized = False
        self._wrapped_system: Optional[Any] = None

    @property
    def name(self) -> str:
        return "builtin"

    @property
    def is_builtin(self) -> bool:
        return True

    async def initialize(self) -> None:
        if self._initialized:
            return
        # Try to wrap the existing MemorySystem
        try:
            from agent.memory import MemorySystem
            self._wrapped_system = MemorySystem()
            logger.info("BuiltinMemoryProvider wrapped existing MemorySystem")
        except Exception as exc:
            logger.debug("BuiltinMemoryProvider using standalone store: %s", exc)
        self._initialized = True

    async def shutdown(self) -> None:
        self._initialized = False

    async def system_prompt_block(self, agent_id: str) -> str:
        entries = self._entries.get(agent_id, [])
        if not entries:
            return ""
        recent = entries[-5:]
        lines = [f"- [{e.timestamp}] {e.content[:100]}" for e in recent]
        return f"\n\nRecent memory ({len(entries)} entries):\n" + "\n".join(lines)

    async def prefetch(self, query: str, agent_id: str = "default") -> None:
        # Builtin provider doesn't need prefetching
        pass

    async def sync_turn(
        self,
        messages: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        agent_id: str = "default",
    ) -> None:
        # Extract user messages and store them
        for msg in messages:
            if msg.get("role") == "user" and msg.get("content"):
                await self.store(
                    content=msg["content"],
                    metadata={"source": "conversation", "role": "user"},
                    agent_id=agent_id,
                )

    async def search(
        self,
        query: str,
        agent_id: str = "default",
        limit: int = 5,
    ) -> MemorySearchResult:
        start = time.time()
        with self._lock:
            entries = self._entries.get(agent_id, [])

        # Simple keyword search
        query_lower = query.lower()
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in entries:
            content_lower = entry.content.lower()
            if query_lower in content_lower:
                score = 1.0
            else:
                # Partial match scoring
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                score = overlap / max(1, len(query_words))
            if score > 0:
                entry.relevance_score = score
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        result_entries = [e for _, e in scored[:limit]]

        return MemorySearchResult(
            entries=result_entries,
            total=len(scored),
            provider=self.name,
            elapsed_ms=(time.time() - start) * 1000,
        )

    async def store(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        agent_id: str = "default",
    ) -> str:
        import uuid
        entry_id = f"mem-{uuid.uuid4().hex[:12]}"
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            metadata=metadata or {},
        )
        with self._lock:
            if agent_id not in self._entries:
                self._entries[agent_id] = []
            self._entries[agent_id].append(entry)

        await self.on_memory_write(entry)
        return entry_id

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "memory_search",
                    "description": "Search the agent's memory for relevant past experiences",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "default": 5, "description": "Max results"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_store",
                    "description": "Store a memory entry for future retrieval",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Content to remember"},
                            "metadata": {"type": "object", "description": "Optional metadata"},
                        },
                        "required": ["content"],
                    },
                },
            },
        ]

    async def handle_tool_call(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "memory_search":
            query = arguments.get("query", "")
            limit = int(arguments.get("limit", 5))
            result = await self.search(query, limit=limit)
            return json.dumps(result.to_dict(), default=str)
        elif name == "memory_store":
            content = arguments.get("content", "")
            metadata = arguments.get("metadata", {})
            entry_id = await self.store(content, metadata=metadata)
            return json.dumps({"ok": True, "entry_id": entry_id})
        return f"ERROR: unknown memory tool '{name}'"


# ═══════════════════════════════════════════════════════════
# Memory Manager — coordinates builtin + at most 1 external provider
# ═══════════════════════════════════════════════════════════

class MemoryManager:
    """Coordinates memory providers with a hard cap.

    Enforces: builtin provider always-on + at most ONE external provider.
    A second external registration is rejected with a warning. This
    prevents tool schema bloat and conflicting memory backends.

    All memory operations route through the manager, which delegates to
    the appropriate provider. Search results merge across providers;
    writes go to all active providers.
    """

    def __init__(self):
        self._builtin = BuiltinMemoryProvider()
        self._external: Optional[MemoryProvider] = None
        self._lock = threading.RLock()
        self._initialized = False

    @property
    def builtin(self) -> MemoryProvider:
        return self._builtin

    @property
    def external(self) -> Optional[MemoryProvider]:
        return self._external

    @property
    def active_providers(self) -> list[MemoryProvider]:
        providers = [self._builtin]
        if self._external is not None:
            providers.append(self._external)
        return providers

    def register_external(self, provider: MemoryProvider) -> bool:
        """Register an external memory provider.

        Returns True if accepted, False if rejected (hard cap exceeded).
        Only ONE external provider may be active at a time.
        """
        with self._lock:
            if self._external is not None:
                logger.warning(
                    "Rejected external memory provider '%s': hard cap exceeded. "
                    "Only one external provider allowed (current: '%s').",
                    provider.name,
                    self._external.name,
                )
                return False
            self._external = provider
            logger.info("Registered external memory provider: %s", provider.name)
            return True

    def unregister_external(self) -> bool:
        """Remove the external memory provider."""
        with self._lock:
            if self._external is None:
                return False
            logger.info("Unregistered external memory provider: %s", self._external.name)
            self._external = None
            return True

    async def initialize(self) -> None:
        """Initialize all active providers."""
        if self._initialized:
            return
        await self._builtin.initialize()
        if self._external is not None:
            await self._external.initialize()
        self._initialized = True
        logger.info("MemoryManager initialized (builtin + %s)", "1 external" if self._external else "0 external")

    async def shutdown(self) -> None:
        """Shutdown all providers."""
        await self._builtin.shutdown()
        if self._external is not None:
            await self._external.shutdown()
        self._initialized = False

    # ── Delegated operations ─────────────────────────────

    async def system_prompt_block(self, agent_id: str) -> str:
        """Merge system prompt blocks from all active providers."""
        blocks: list[str] = []
        for provider in self.active_providers:
            block = await provider.system_prompt_block(agent_id)
            if block:
                blocks.append(block)
        return "\n".join(blocks)

    async def prefetch(self, query: str, agent_id: str = "default") -> None:
        """Prefetch across all active providers."""
        for provider in self.active_providers:
            try:
                await provider.prefetch(query, agent_id)
            except Exception as exc:
                logger.debug("Prefetch failed for %s: %s", provider.name, exc)

    async def sync_turn(
        self,
        messages: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        agent_id: str = "default",
    ) -> None:
        """Sync turn across all active providers."""
        for provider in self.active_providers:
            try:
                await provider.sync_turn(messages, tool_results, agent_id)
            except Exception as exc:
                logger.debug("Sync turn failed for %s: %s", provider.name, exc)

    async def search(
        self,
        query: str,
        agent_id: str = "default",
        limit: int = 5,
    ) -> MemorySearchResult:
        """Search across all active providers and merge results."""
        all_entries: list[MemoryEntry] = []
        total = 0
        start = time.time()

        for provider in self.active_providers:
            try:
                result = await provider.search(query, agent_id, limit)
                all_entries.extend(result.entries)
                total += result.total
            except Exception as exc:
                logger.debug("Search failed for %s: %s", provider.name, exc)

        # Sort by relevance and limit
        all_entries.sort(key=lambda e: e.relevance_score, reverse=True)
        return MemorySearchResult(
            entries=all_entries[:limit],
            total=total,
            provider="merged",
            elapsed_ms=(time.time() - start) * 1000,
        )

    async def store(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        agent_id: str = "default",
    ) -> str:
        """Store across all active providers. Returns builtin entry ID."""
        entry_id = await self._builtin.store(content, metadata, agent_id)
        if self._external is not None:
            try:
                await self._external.store(content, metadata, agent_id)
            except Exception as exc:
                logger.debug("External store failed: %s", exc)
        return entry_id

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return tool schemas from all active providers (deduplicated)."""
        seen_names: set[str] = set()
        schemas: list[dict[str, Any]] = []
        for provider in self.active_providers:
            for schema in provider.get_tool_schemas():
                name = schema.get("function", {}).get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    schemas.append(schema)
        return schemas

    async def handle_tool_call(self, name: str, arguments: dict[str, Any]) -> str:
        """Route a tool call to the provider that handles it."""
        for provider in self.active_providers:
            schema_names = {
                s.get("function", {}).get("name", "")
                for s in provider.get_tool_schemas()
            }
            if name in schema_names:
                return await provider.handle_tool_call(name, arguments)
        return f"ERROR: no provider handles tool '{name}'"

    # ── Lifecycle hook dispatch ──────────────────────────

    async def on_turn_start(self, agent_id: str) -> None:
        for provider in self.active_providers:
            await provider.on_turn_start(agent_id)

    async def on_session_end(self, agent_id: str) -> None:
        for provider in self.active_providers:
            await provider.on_session_end(agent_id)

    async def on_pre_compress(self, agent_id: str) -> None:
        for provider in self.active_providers:
            await provider.on_pre_compress(agent_id)

    async def on_delegation(self, target_agent: str, context: dict[str, Any]) -> None:
        for provider in self.active_providers:
            await provider.on_delegation(target_agent, context)

    def get_stats(self) -> dict[str, Any]:
        return {
            "builtin_provider": self._builtin.name,
            "external_provider": self._external.name if self._external else None,
            "active_providers": [p.name for p in self.active_providers],
            "initialized": self._initialized,
        }


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

_memory_manager: Optional[MemoryManager] = None
_manager_lock = threading.Lock()


def get_memory_manager() -> MemoryManager:
    """Get the singleton MemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        with _manager_lock:
            if _memory_manager is None:
                _memory_manager = MemoryManager()
    return _memory_manager
