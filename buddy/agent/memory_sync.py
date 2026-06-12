"""Buddy Memory Sync System — cross-agent memory sharing and synchronization

Provides a central hub for sharing memories between agents, creating sync groups
that auto-share, and searching across multiple agents' memories semantically.

Key components:
- MemorySyncHub: Central coordinator for cross-agent memory operations
- SyncGroup: Represents a group of agents that auto-share memories
- SharedMemory: Represents a single shared memory entry with tracking metadata
"""
from __future__ import annotations
import logging
import uuid
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, desc, and_
from database.db import async_session
from database.models import Memory as MemoryModel, Agent as AgentModel
from agent.memory import HierarchicalMemory, MemoryLayer

logger = logging.getLogger("buddy.memory_sync")


# ── Dataclasses ─────────────────────────────────────────────

@dataclass
class SyncGroup:
    """Represents a group of agents that auto-share memories with each other."""
    id: str
    name: str
    agent_ids: list[str]
    sync_interval: int = 300  # Seconds between auto-sync cycles
    last_sync: str = ""       # ISO timestamp of last sync
    enabled: bool = True
    filters: dict[str, Any] = field(default_factory=dict)
    # Example filters: {"memory_type": "fact", "min_importance": 0.5}


@dataclass
class SharedMemory:
    """Represents a single shared memory entry with tracking metadata."""
    id: str
    source_agent_id: str
    target_agent_id: str
    content: str
    memory_type: str = "shared"
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)
    shared_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    access_count: int = 0


# ── Memory Sync Hub ────────────────────────────────────────

class MemorySyncHub:
    """Central hub for cross-agent memory sharing, sync groups, and federated search.

    Manages:
    - Point-to-point memory sharing between agents
    - Broadcast memory to all agents (with optional role filtering)
    - Sync groups that periodically auto-share memories among members
    - Federated semantic search across multiple agents' memory stores
    - Usage statistics for shared memories
    """

    def __init__(self, orchestrator=None):
        # Lazy import to avoid circular dependency at module level
        self._orchestrator = orchestrator

        # Per-agent HierarchicalMemory instances (lazily created)
        self._memory_instances: dict[str, HierarchicalMemory] = {}

        # Active sync groups keyed by group ID
        self._sync_groups: dict[str, SyncGroup] = {}

        # Shared memory records keyed by shared memory ID
        self._shared_memories: dict[str, SharedMemory] = {}

        # Background sync tasks keyed by group ID
        self._sync_tasks: dict[str, asyncio.Task] = {}

        # Configuration
        self._config: dict[str, Any] = {
            "auto_sync_enabled": True,
            "default_sync_interval": 300,
            "max_shared_memories_per_sync": 10,
            "min_importance_for_sync": 0.3,
        }

        # Statistics
        self._stats: dict[str, Any] = {
            "total_shares": 0,
            "total_broadcasts": 0,
            "total_syncs": 0,
            "total_search_queries": 0,
            "active_groups": 0,
            "total_shared_memories": 0,
        }

    # ── Internal Helpers ────────────────────────────────────

    def _get_memory(self, agent_id: str) -> HierarchicalMemory:
        """Get or create a HierarchicalMemory instance for the given agent."""
        if agent_id not in self._memory_instances:
            self._memory_instances[agent_id] = HierarchicalMemory(agent_id)
        return self._memory_instances[agent_id]

    def _build_memory_type(self, memory_type: str) -> str:
        """Build a memory type string that includes the shared prefix."""
        return f"{MemoryLayer.LONG_TERM}:shared:{memory_type}"

    async def _get_agents_by_role(self, role: str) -> list[str]:
        """Query the database for agent IDs matching a given role."""
        async with async_session() as session:
            stmt = select(AgentModel.id).where(
                and_(
                    AgentModel.role == role,
                    AgentModel.is_active == True,
                )
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.fetchall()]

    async def _get_all_active_agent_ids(self) -> list[str]:
        """Get all active agent IDs from the database."""
        async with async_session() as session:
            stmt = select(AgentModel.id).where(AgentModel.is_active == True)
            result = await session.execute(stmt)
            return [row[0] for row in result.fetchall()]

    # ── Memory Sharing ──────────────────────────────────────

    async def share_memory(
        self,
        source_agent_id: str,
        target_agent_id: str,
        content: str,
        memory_type: str = "shared",
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> SharedMemory | None:
        """Share a specific memory from one agent to another.

        Stores the memory in the target agent's HierarchicalMemory and
        creates a SharedMemory record for tracking.

        Args:
            source_agent_id: ID of the agent sharing the memory
            target_agent_id: ID of the agent receiving the memory
            content: The memory content to share
            memory_type: Type of memory (e.g., "fact", "decision", "insight")
            importance: Importance score (0.0 - 1.0)
            tags: Optional list of tags for categorization

        Returns:
            SharedMemory record if successful, None on failure
        """
        if source_agent_id == target_agent_id:
            logger.warning("Cannot share memory to the same agent")
            return None

        tags = tags or []
        shared_id = f"shared-{uuid.uuid4().hex[:12]}"
        shared_at = datetime.now(timezone.utc).isoformat()

        try:
            # Store in source agent's memory as a sent record
            source_memory = self._get_memory(source_agent_id)
            await source_memory.store(
                content=content,
                layer=MemoryLayer.LONG_TERM,
                memory_type=f"shared_out:{memory_type}",
                importance=importance,
                metadata={
                    "shared_to": target_agent_id,
                    "shared_id": shared_id,
                    "tags": tags,
                },
            )

            # Store in target agent's memory as a received record
            target_memory = self._get_memory(target_agent_id)
            await target_memory.store(
                content=content,
                layer=MemoryLayer.LONG_TERM,
                memory_type=f"shared_in:{memory_type}",
                importance=importance,
                metadata={
                    "shared_from": source_agent_id,
                    "shared_id": shared_id,
                    "tags": tags,
                },
            )

            # Create tracking record
            shared_memory = SharedMemory(
                id=shared_id,
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                tags=tags,
                shared_at=shared_at,
            )
            self._shared_memories[shared_id] = shared_memory

            self._stats["total_shares"] += 1
            self._stats["total_shared_memories"] += 1

            logger.info(
                f"Memory shared: {source_agent_id} -> {target_agent_id} "
                f"(type={memory_type}, importance={importance})"
            )
            return shared_memory

        except Exception as e:
            logger.error(f"Failed to share memory from {source_agent_id} to {target_agent_id}: {e}")
            return None

    async def broadcast_memory(
        self,
        source_agent_id: str,
        content: str,
        memory_type: str = "broadcast",
        importance: float = 0.5,
        tags: list[str] | None = None,
        target_role: str | None = None,
    ) -> list[SharedMemory]:
        """Broadcast a memory from one agent to all active agents.

        Optionally filter target agents by their role.

        Args:
            source_agent_id: ID of the agent broadcasting the memory
            content: The memory content to broadcast
            memory_type: Type of memory
            importance: Importance score (0.0 - 1.0)
            tags: Optional list of tags
            target_role: If set, only broadcast to agents with this role

        Returns:
            List of successfully created SharedMemory records
        """
        if target_role:
            target_ids = await self._get_agents_by_role(target_role)
        else:
            target_ids = await self._get_all_active_agent_ids()

        # Remove source agent from targets
        target_ids = [aid for aid in target_ids if aid != source_agent_id]

        if not target_ids:
            logger.info(f"No target agents found for broadcast from {source_agent_id}")
            return []

        results: list[SharedMemory] = []
        for target_id in target_ids:
            result = await self.share_memory(
                source_agent_id=source_agent_id,
                target_agent_id=target_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                tags=tags,
            )
            if result:
                results.append(result)

        self._stats["total_broadcasts"] += 1

        logger.info(
            f"Broadcast from {source_agent_id} to {len(results)} agents "
            f"(role_filter={target_role or 'none'})"
        )
        return results

    # ── Federated Search ────────────────────────────────────

    async def search_across_agents(
        self,
        query: str,
        agent_ids: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Semantically search across multiple agents' memories.

        Performs a semantic search on each agent's memory store and
        aggregates results sorted by relevance.

        Args:
            query: The search query string
            agent_ids: List of agent IDs to search. If None, searches all agents
                       that have memory instances.
            limit: Maximum number of total results to return

        Returns:
            List of memory entries with agent_id, content, similarity score, etc.
        """
        if agent_ids is None:
            agent_ids = list(self._memory_instances.keys())
            if not agent_ids:
                agent_ids = await self._get_all_active_agent_ids()

        if not agent_ids:
            return []

        all_results: list[dict[str, Any]] = []

        for agent_id in agent_ids:
            try:
                memory = self._get_memory(agent_id)
                agent_results = await memory.search_semantic(
                    query=query,
                    limit=limit,
                )
                # Tag results with agent_id and source info
                for result in agent_results:
                    result["agent_id"] = agent_id
                    # Check if this is a shared memory
                    is_shared = any(
                        sm.target_agent_id == agent_id
                        for sm in self._shared_memories.values()
                    )
                    result["is_shared"] = is_shared
                all_results.extend(agent_results)
            except Exception as e:
                logger.error(f"Search failed for agent {agent_id}: {e}")
                continue

        # Sort by similarity (if available) then by importance
        all_results.sort(
            key=lambda x: (x.get("similarity", 0), x.get("importance", 0)),
            reverse=True,
        )

        self._stats["total_search_queries"] += 1

        return all_results[:limit]

    async def get_shared_context(
        self,
        agent_id: str,
        topic: str,
        max_memories: int = 5,
    ) -> list[dict[str, Any]]:
        """Get relevant shared memories for a given topic across all agents.

        Searches for memories related to the topic that have been shared
        with the specified agent, providing cross-agent context.

        Args:
            agent_id: The agent requesting context
            topic: The topic to search for
            max_memories: Maximum number of memories to return

        Returns:
            List of relevant shared memory entries sorted by relevance
        """
        # Find memories shared to this agent
        relevant_shared: list[str] = []
        for sm in self._shared_memories.values():
            if sm.target_agent_id == agent_id:
                relevant_shared.append(sm.id)

        if not relevant_shared:
            return []

        try:
            memory = self._get_memory(agent_id)
            # Search the agent's own memory for the topic, focusing on shared-in memories
            all_memories = await memory.recall(
                query=topic,
                memory_type="shared_in",
                limit=max_memories * 3,
            )

            # Also do a semantic search for better relevance
            semantic_results = await memory.search_semantic(
                query=topic,
                limit=max_memories * 2,
            )

            # Merge and deduplicate results
            seen_ids: set[str] = set()
            merged: list[dict[str, Any]] = []

            for result in all_memories:
                if result["id"] not in seen_ids:
                    result["source"] = "recall"
                    merged.append(result)
                    seen_ids.add(result["id"])

            for result in semantic_results:
                if result["id"] not in seen_ids:
                    # Check if this is a shared-in memory
                    result["source"] = "semantic"
                    merged.append(result)
                    seen_ids.add(result["id"])

            # Sort by importance
            merged.sort(key=lambda x: x.get("importance", 0), reverse=True)

            # Track access counts
            for m in merged[:max_memories]:
                for sm in self._shared_memories.values():
                    if sm.target_agent_id == agent_id and sm.content[:50] in m.get("content", ""):
                        sm.access_count += 1

            return merged[:max_memories]

        except Exception as e:
            logger.error(f"Failed to get shared context for agent {agent_id}: {e}")
            return []

    # ── Sync Groups ─────────────────────────────────────────

    async def create_sync_group(
        self,
        name: str,
        agent_ids: list[str],
        sync_interval: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SyncGroup:
        """Create a sync group of agents that auto-share memories.

        Once created, agents in the group will periodically share their
        recent high-importance memories with each other.

        Args:
            name: Human-readable name for the group
            agent_ids: List of agent IDs to include in the group
            sync_interval: Seconds between auto-sync cycles (default from config)
            filters: Optional filters for what memories to sync (e.g., min_importance)

        Returns:
            The created SyncGroup
        """
        group_id = f"syncgrp-{uuid.uuid4().hex[:8]}"
        interval = sync_interval or self._config["default_sync_interval"]

        group = SyncGroup(
            id=group_id,
            name=name,
            agent_ids=agent_ids,
            sync_interval=interval,
            filters=filters or {},
            enabled=True,
        )

        self._sync_groups[group_id] = group
        self._stats["active_groups"] = len(self._sync_groups)

        logger.info(f"Sync group created: {name} ({group_id}) with {len(agent_ids)} agents")

        # Start background auto-sync if enabled
        if self._config["auto_sync_enabled"] and len(agent_ids) > 1:
            await self._start_group_auto_sync(group_id)

        return group

    async def sync_group_memories(self, group_id: str) -> dict[str, Any]:
        """Trigger a manual sync for all agents in a sync group.

        Each agent shares its recent high-importance memories with all
        other agents in the group.

        Args:
            group_id: The sync group ID to synchronize

        Returns:
            Dict with sync results including count of shared memories and errors
        """
        group = self._sync_groups.get(group_id)
        if not group:
            logger.warning(f"Sync group {group_id} not found")
            return {"success": False, "error": "Group not found"}

        if not group.enabled:
            return {"success": False, "error": "Group is disabled"}

        min_importance = group.filters.get("min_importance", self._config["min_importance_for_sync"])
        memory_type_filter = group.filters.get("memory_type", None)
        max_per_agent = group.filters.get("max_memories", self._config["max_shared_memories_per_sync"])

        total_shared = 0
        errors: list[str] = []

        for source_id in group.agent_ids:
            try:
                memory = self._get_memory(source_id)
                # Recall recent long-term memories above the importance threshold
                recent_memories = await memory.recall_long_term(
                    query=memory_type_filter,
                    limit=max_per_agent,
                )

                for mem in recent_memories:
                    if mem.get("importance", 0) < min_importance:
                        continue

                    for target_id in group.agent_ids:
                        if target_id == source_id:
                            continue

                        result = await self.share_memory(
                            source_agent_id=source_id,
                            target_agent_id=target_id,
                            content=mem["content"],
                            memory_type=mem.get("memory_type", "shared"),
                            importance=mem.get("importance", 0.5),
                        )
                        if result:
                            total_shared += 1
                        else:
                            errors.append(f"Failed to share from {source_id} to {target_id}")

            except Exception as e:
                error_msg = f"Sync error for agent {source_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Update last sync time
        group.last_sync = datetime.now(timezone.utc).isoformat()
        self._stats["total_syncs"] += 1

        logger.info(
            f"Sync group '{group.name}' completed: {total_shared} memories shared, "
            f"{len(errors)} errors"
        )

        return {
            "success": True,
            "group_id": group_id,
            "group_name": group.name,
            "memories_shared": total_shared,
            "errors": errors,
            "synced_at": group.last_sync,
        }

    async def _start_group_auto_sync(self, group_id: str):
        """Start a background task that periodically auto-syncs a group."""
        group = self._sync_groups.get(group_id)
        if not group:
            return

        # Cancel existing task if any
        if group_id in self._sync_tasks:
            self._sync_tasks[group_id].cancel()
            try:
                await self._sync_tasks[group_id]
            except asyncio.CancelledError:
                pass

        async def _auto_sync_loop():
            while True:
                try:
                    await asyncio.sleep(group.sync_interval)
                    current_group = self._sync_groups.get(group_id)
                    if not current_group or not current_group.enabled:
                        break
                    await self.sync_group_memories(group_id)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto-sync error for group {group_id}: {e}")

        task = asyncio.create_task(_auto_sync_loop())
        self._sync_tasks[group_id] = task
        logger.info(f"Auto-sync started for group '{group.name}' (interval={group.sync_interval}s)")

    async def stop_group_auto_sync(self, group_id: str):
        """Stop the background auto-sync for a specific group."""
        if group_id in self._sync_tasks:
            self._sync_tasks[group_id].cancel()
            try:
                await self._sync_tasks[group_id]
            except asyncio.CancelledError:
                pass
            del self._sync_tasks[group_id]
            logger.info(f"Auto-sync stopped for group {group_id}")

    def get_sync_group(self, group_id: str) -> SyncGroup | None:
        """Get a sync group by ID."""
        return self._sync_groups.get(group_id)

    def list_sync_groups(self) -> list[SyncGroup]:
        """List all registered sync groups."""
        return list(self._sync_groups.values())

    def remove_sync_group(self, group_id: str) -> bool:
        """Remove a sync group and stop its auto-sync."""
        if group_id not in self._sync_groups:
            return False
        # Stop auto-sync
        if group_id in self._sync_tasks:
            self._sync_tasks[group_id].cancel()
            del self._sync_tasks[group_id]
        del self._sync_groups[group_id]
        self._stats["active_groups"] = len(self._sync_groups)
        logger.info(f"Sync group {group_id} removed")
        return True

    def update_sync_group(
        self,
        group_id: str,
        name: str | None = None,
        agent_ids: list[str] | None = None,
        sync_interval: int | None = None,
        enabled: bool | None = None,
        filters: dict[str, Any] | None = None,
    ) -> SyncGroup | None:
        """Update a sync group's configuration.

        If agent_ids or sync_interval change, the auto-sync task is restarted.
        """
        group = self._sync_groups.get(group_id)
        if not group:
            return None

        needs_restart = False

        if name is not None:
            group.name = name
        if agent_ids is not None:
            group.agent_ids = agent_ids
            needs_restart = True
        if sync_interval is not None:
            group.sync_interval = sync_interval
            needs_restart = True
        if enabled is not None:
            group.enabled = enabled
            needs_restart = True
        if filters is not None:
            group.filters = filters

        if needs_restart and group.enabled and len(group.agent_ids) > 1:
            # Restart the auto-sync loop with new config
            async def _restart():
                await self._start_group_auto_sync(group_id)

            # Schedule restart; we can't await in a sync method, so we use the event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(_restart())
            except RuntimeError:
                pass

        return group

    # ── Stats & Config ──────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get current memory sync statistics."""
        return {
            **self._stats,
            "shared_memory_count": len(self._shared_memories),
            "sync_group_count": len(self._sync_groups),
            "memory_instance_count": len(self._memory_instances),
            "active_auto_sync_tasks": len(self._sync_tasks),
        }

    def get_config(self) -> dict[str, Any]:
        """Get current sync hub configuration."""
        return dict(self._config)

    def update_config(self, **kwargs: Any) -> None:
        """Update sync hub configuration parameters.

        Valid keys: auto_sync_enabled, default_sync_interval,
        max_shared_memories_per_sync, min_importance_for_sync
        """
        for key, value in kwargs.items():
            if key in self._config:
                self._config[key] = value
                logger.info(f"MemorySyncHub config updated: {key} = {value}")
            else:
                logger.warning(f"Ignored unknown config key: {key}")

    def get_shared_memory_record(self, shared_id: str) -> SharedMemory | None:
        """Get a SharedMemory record by its ID."""
        return self._shared_memories.get(shared_id)

    def list_shared_memories(
        self,
        source_agent_id: str | None = None,
        target_agent_id: str | None = None,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[SharedMemory]:
        """List shared memory records with optional filtering."""
        results = list(self._shared_memories.values())

        if source_agent_id:
            results = [sm for sm in results if sm.source_agent_id == source_agent_id]
        if target_agent_id:
            results = [sm for sm in results if sm.target_agent_id == target_agent_id]
        if memory_type:
            results = [sm for sm in results if sm.memory_type == memory_type]

        # Sort by shared_at descending
        results.sort(key=lambda sm: sm.shared_at, reverse=True)
        return results[:limit]

    async def shutdown(self):
        """Gracefully shutdown all background sync tasks."""
        for group_id in list(self._sync_tasks.keys()):
            await self.stop_group_auto_sync(group_id)

        self._memory_instances.clear()
        self._sync_groups.clear()
        self._shared_memories.clear()

        logger.info("MemorySyncHub shut down gracefully")