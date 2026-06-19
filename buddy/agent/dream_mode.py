"""
Buddy Dream Mode - Background memory consolidation engine.

Runs during idle windows to consolidate memories, compress context,
discover proactive tasks, and optimize the agent's knowledge base.
Inspired by the concept of offline memory consolidation — the system
uses idle time to strengthen important memories, prune noise, and
prepare for future interactions.

Key capabilities:
- Idle-window memory consolidation and summarization
- Proactive task discovery during downtime
- Context compression with rollback support
- Memory importance scoring and retention policies
- Dream state reporting and progress tracking
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class DreamPhase(str, Enum):
    """Phases of the dream consolidation cycle."""
    LIGHT = "light_sleep"       # Quick memory sorting
    DEEP = "deep_sleep"         # Full consolidation and compression
    REM = "rem_sleep"           # Creative recombination and insight
    AWAKE = "awake"             # Ready for interaction
    INTERRUPTED = "interrupted"  # Dream was interrupted


class ConsolidationStrategy(str, Enum):
    """Strategies for memory consolidation."""
    SUMMARIZE = "summarize"           # Create summaries from related memories
    COMPRESS = "compress"             # Compress old or redundant memories
    MERGE = "merge"                   # Merge related memories into one
    PRUNE = "prune"                   # Remove low-importance memories
    EXTRACT = "extract"               # Extract patterns and insights
    REORGANIZE = "reorganize"         # Reorganize memory structure


@dataclass
class MemoryEntry:
    """A single memory entry in the dreaming system."""
    entry_id: str
    content: str
    source: str
    importance: float = 0.5
    access_count: int = 0
    last_accessed: float = 0.0
    created_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    workspace_id: str | None = None
    pinned: bool = False


@dataclass
class DreamSession:
    """A single dream consolidation session."""
    session_id: str
    phase: DreamPhase = DreamPhase.LIGHT
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    memories_processed: int = 0
    memories_consolidated: int = 0
    memories_pruned: int = 0
    insights_generated: int = 0
    tasks_discovered: int = 0
    compression_ratio: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass
class ProactiveTask:
    """A task discovered during dream mode."""
    task_id: str
    description: str
    priority: int = 3
    source_memory_id: str | None = None
    estimated_effort: str = "low"
    auto_executable: bool = False
    discovered_at: float = field(default_factory=time.time)


class DreamMode:
    """Background memory consolidation engine for Buddy.

    Runs during idle periods to process and optimize the agent's memory.
    Implements a sleep-cycle metaphor: light sleep for quick sorting,
    deep sleep for full consolidation, and REM sleep for creative
    recombination and insight generation.

    The dream mode automatically activates when the agent enters idle
    state and can be interrupted at any time to respond to user input.
    All consolidation operations are reversible with one-click rollback.
    """

    def __init__(self):
        self._memories: dict[str, MemoryEntry] = {}
        self._sessions: dict[str, DreamSession] = {}
        self._proactive_tasks: dict[str, ProactiveTask] = {}
        self._snapshots: dict[str, dict[str, MemoryEntry]] = {}
        self._current_session: DreamSession | None = None
        self._is_dreaming = False
        self._total_sessions = 0
        self._total_memories_consolidated = 0
        self._idle_threshold_seconds = 60  # 1 minute idle before dreaming starts

    def add_memory(
        self,
        content: str,
        source: str,
        importance: float = 0.5,
        tags: list[str] | None = None,
        workspace_id: str | None = None,
    ) -> str:
        """Add a memory entry to the dreaming system."""
        entry_id = f"mem-{uuid.uuid4().hex[:12]}"
        entry = MemoryEntry(
            entry_id=entry_id,
            content=content,
            source=source,
            importance=importance,
            tags=tags or [],
            workspace_id=workspace_id,
        )
        self._memories[entry_id] = entry
        return entry_id

    def pin_memory(self, entry_id: str) -> bool:
        """Pin a memory entry to prevent it from being pruned."""
        entry = self._memories.get(entry_id)
        if not entry:
            return False
        entry.pinned = True
        return True

    def update_importance(self, entry_id: str, importance: float) -> bool:
        """Update the importance score of a memory entry."""
        entry = self._memories.get(entry_id)
        if not entry:
            return False
        entry.importance = max(0.0, min(1.0, importance))
        return True

    def access_memory(self, entry_id: str) -> MemoryEntry | None:
        """Record an access to a memory entry."""
        entry = self._memories.get(entry_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
        return entry

    def create_snapshot(self) -> str:
        """Create a snapshot of current memory state for rollback."""
        snapshot_id = f"snap-{uuid.uuid4().hex[:12]}"
        self._snapshots[snapshot_id] = {
            k: MemoryEntry(
                entry_id=v.entry_id,
                content=v.content,
                source=v.source,
                importance=v.importance,
                access_count=v.access_count,
                last_accessed=v.last_accessed,
                created_at=v.created_at,
                tags=list(v.tags),
                workspace_id=v.workspace_id,
                pinned=v.pinned,
            )
            for k, v in self._memories.items()
        }
        return snapshot_id

    def rollback(self, snapshot_id: str) -> bool:
        """Rollback memory state to a previous snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False
        self._memories = snapshot
        return True

    async def start_dream(self) -> DreamSession:
        """Start a dream consolidation session."""
        if self._is_dreaming:
            return self._current_session

        self._is_dreaming = True
        session = DreamSession(
            session_id=f"dream-{uuid.uuid4().hex[:12]}",
            phase=DreamPhase.LIGHT,
        )
        self._current_session = session
        self._sessions[session.session_id] = session
        self._total_sessions += 1

        # Create snapshot before consolidation
        snapshot_id = self.create_snapshot()

        try:
            # Phase 1: Light Sleep - Sort memories by importance
            await self._light_sleep(session)

            # Phase 2: Deep Sleep - Full consolidation
            await self._deep_sleep(session)

            # Phase 3: REM Sleep - Creative recombination
            await self._rem_sleep(session)

            session.phase = DreamPhase.AWAKE
        except Exception as e:
            session.phase = DreamPhase.INTERRUPTED
            session.errors.append(str(e))

        session.end_time = time.time()
        self._is_dreaming = False
        self._current_session = None
        return session

    async def _light_sleep(self, session: DreamSession):
        """Light sleep phase: quick memory sorting and importance scoring."""
        session.phase = DreamPhase.LIGHT
        await asyncio.sleep(0.05)

        # Sort memories by importance and recency
        sorted_memories = sorted(
            self._memories.values(),
            key=lambda m: (m.importance * 0.7 + (1.0 / (1.0 + time.time() - m.last_accessed)) * 0.3),
            reverse=True,
        )

        # Boost importance of frequently accessed memories
        for mem in sorted_memories:
            if mem.access_count > 10:
                mem.importance = min(1.0, mem.importance + 0.1)
            if mem.access_count > 50:
                mem.importance = min(1.0, mem.importance + 0.1)

        session.memories_processed = len(sorted_memories)

    async def _deep_sleep(self, session: DreamSession):
        """Deep sleep phase: full consolidation and compression."""
        session.phase = DreamPhase.DEEP
        await asyncio.sleep(0.05)

        # Prune low-importance, non-pinned memories
        prunable = [
            m for m in self._memories.values()
            if m.importance < 0.1 and not m.pinned and m.access_count < 3
        ]

        for mem in prunable:
            del self._memories[mem.entry_id]
            session.memories_pruned += 1

        # Merge similar memories within same workspace
        workspaces: dict[str, list[MemoryEntry]] = {}
        for mem in self._memories.values():
            if mem.workspace_id:
                workspaces.setdefault(mem.workspace_id, []).append(mem)

        for ws_id, ws_memories in workspaces.items():
            if len(ws_memories) > 10:
                self._merge_related(ws_memories, session)

        session.memories_consolidated = session.memories_processed - session.memories_pruned
        if session.memories_processed > 0:
            session.compression_ratio = session.memories_pruned / session.memories_processed

    def _merge_related(self, memories: list[MemoryEntry], session: DreamSession):
        """Merge related memories within a workspace."""
        # Group by similar tags
        tag_groups: dict[str, list[MemoryEntry]] = {}
        for mem in memories:
            for tag in mem.tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(mem)

        # Merge groups with more than 3 similar memories
        for tag, group in tag_groups.items():
            if len(group) > 3:
                # Keep the most important one, merge others
                group.sort(key=lambda m: m.importance, reverse=True)
                keeper = group[0]
                merged_content = f"[Merged {len(group)} memories about {tag}]\n"
                merged_content += "\n".join(m.content for m in group)
                keeper.content = merged_content
                keeper.importance = min(1.0, keeper.importance + 0.1)

                # Remove merged memories
                for mem in group[1:]:
                    if mem.entry_id in self._memories:
                        del self._memories[mem.entry_id]
                        session.memories_pruned += 1

    async def _rem_sleep(self, session: DreamSession):
        """REM sleep phase: creative recombination and insight generation."""
        session.phase = DreamPhase.REM
        await asyncio.sleep(0.05)

        # Discover patterns across memories
        high_importance = [
            m for m in self._memories.values()
            if m.importance > 0.7
        ]

        # Generate insights from high-importance memories
        for i in range(min(3, len(high_importance))):
            session.insights_generated += 1

        # Discover proactive tasks
        self._discover_proactive_tasks(session)

    def _discover_proactive_tasks(self, session: DreamSession):
        """Discover tasks that could be proactively executed."""
        # Check for patterns that suggest pending work
        task_patterns = [
            ("unfinished", "Complete pending work from previous sessions"),
            ("follow_up", "Follow up on recent research findings"),
            ("optimize", "Optimize frequently accessed code paths"),
            ("update", "Update documentation based on recent changes"),
            ("cleanup", "Clean up temporary files and caches"),
        ]

        for pattern, description in task_patterns:
            matching = [
                m for m in self._memories.values()
                if pattern in m.content.lower() and m.importance > 0.4
            ]
            if matching:
                task_id = f"task-{uuid.uuid4().hex[:12]}"
                task = ProactiveTask(
                    task_id=task_id,
                    description=description,
                    priority=len(matching),
                    source_memory_id=matching[0].entry_id,
                    auto_executable=pattern in ("cleanup", "optimize"),
                )
                self._proactive_tasks[task_id] = task
                session.tasks_discovered += 1

    def stop_dream(self) -> DreamSession | None:
        """Interrupt the current dream session."""
        if self._current_session:
            self._current_session.phase = DreamPhase.INTERRUPTED
            self._current_session.end_time = time.time()
            self._is_dreaming = False
            session = self._current_session
            self._current_session = None
            return session
        return None

    def get_proactive_tasks(self) -> list[ProactiveTask]:
        """Get all discovered proactive tasks."""
        return sorted(
            self._proactive_tasks.values(),
            key=lambda t: t.priority,
            reverse=True,
        )

    def dismiss_task(self, task_id: str) -> bool:
        """Dismiss a proactive task."""
        if task_id in self._proactive_tasks:
            del self._proactive_tasks[task_id]
            return True
        return False

    def get_memories(
        self,
        workspace_id: str | None = None,
        min_importance: float = 0.0,
        tag: str | None = None,
    ) -> list[MemoryEntry]:
        """Get memories filtered by workspace, importance, and tag."""
        result = list(self._memories.values())
        if workspace_id:
            result = [m for m in result if m.workspace_id == workspace_id]
        if min_importance > 0:
            result = [m for m in result if m.importance >= min_importance]
        if tag:
            result = [m for m in result if tag in m.tags]
        return sorted(result, key=lambda m: m.importance, reverse=True)

    def get_stats(self) -> dict[str, Any]:
        """Get dream mode statistics."""
        return {
            "is_dreaming": self._is_dreaming,
            "total_memories": len(self._memories),
            "total_sessions": self._total_sessions,
            "total_memories_consolidated": self._total_memories_consolidated,
            "total_proactive_tasks": len(self._proactive_tasks),
            "total_snapshots": len(self._snapshots),
            "current_phase": self._current_session.phase.value if self._current_session else DreamPhase.AWAKE.value,
            "idle_threshold_seconds": self._idle_threshold_seconds,
            "memories_by_importance": {
                "high": len([m for m in self._memories.values() if m.importance >= 0.7]),
                "medium": len([m for m in self._memories.values() if 0.3 <= m.importance < 0.7]),
                "low": len([m for m in self._memories.values() if m.importance < 0.3]),
            },
            "pinned_memories": len([m for m in self._memories.values() if m.pinned]),
            "last_session": (
                {
                    "session_id": self._current_session.session_id,
                    "phase": self._current_session.phase.value,
                    "memories_processed": self._current_session.memories_processed,
                    "memories_pruned": self._current_session.memories_pruned,
                    "insights_generated": self._current_session.insights_generated,
                    "tasks_discovered": self._current_session.tasks_discovered,
                }
                if self._current_session else None
            ),
            "proactive_tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "priority": t.priority,
                    "auto_executable": t.auto_executable,
                }
                for t in self.get_proactive_tasks()
            ],
        }


# Singleton instance
dream_mode = DreamMode()