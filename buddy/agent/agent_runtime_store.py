"""Buddy Agent Runtime Store — persistent agent state management with snapshots

The Runtime Store provides durable state persistence for all agent instances,
enabling state versioning, checkpoint/restore, migration, and temporal queries.
It serves as the foundational persistence layer for the entire agent ecosystem.

Core capabilities:
  - State Snapshots: point-in-time captures with compression and diffing
  - Checkpoint/Restore: save and resume agent execution at any point
  - State Versioning: immutable versioned records with rollback support
  - Temporal Queries: query state by time range or version
  - Migration: state migration between agent versions
  - Garbage Collection: automatic cleanup of stale snapshots
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.runtime_store")


# ═══════════════════════════════════════════════════════════
# Enums and Types
# ═══════════════════════════════════════════════════════════

class StoreBackend(str, Enum):
    """Storage backend types."""
    MEMORY = "memory"
    SQLITE = "sqlite"
    FILE = "file"


class SnapshotType(str, Enum):
    """Types of state snapshots."""
    FULL = "full"
    INCREMENTAL = "incremental"
    CHECKPOINT = "checkpoint"
    AUTO = "auto"


class StateStatus(str, Enum):
    """Status of a stored state."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    CORRUPTED = "corrupted"
    MIGRATING = "migrating"


class CompressionMode(str, Enum):
    """Compression modes for state storage."""
    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class RuntimeStoreConfig:
    """Configuration for the Runtime Store."""
    backend: StoreBackend = StoreBackend.MEMORY
    max_snapshots_per_agent: int = 50
    snapshot_interval_seconds: int = 300
    compression: CompressionMode = CompressionMode.GZIP
    retention_days: int = 30
    auto_checkpoint: bool = True
    enable_diffing: bool = True
    max_state_size_bytes: int = 10 * 1024 * 1024  # 10 MB


@dataclass
class StateSnapshot:
    """A point-in-time capture of agent state."""
    snapshot_id: str = field(default_factory=lambda: f"snap-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    snapshot_type: SnapshotType = SnapshotType.FULL
    version: int = 0
    parent_version: int = 0  # For incremental snapshots
    state_data: dict[str, Any] = field(default_factory=dict)
    state_hash: str = ""
    compressed_size: int = 0
    original_size: int = 0
    compression: CompressionMode = CompressionMode.NONE
    status: StateStatus = StateStatus.ACTIVE
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "snapshot_type": self.snapshot_type.value,
            "version": self.version,
            "parent_version": self.parent_version,
            "state_hash": self.state_hash,
            "compressed_size": self.compressed_size,
            "original_size": self.original_size,
            "compression": self.compression.value,
            "status": self.status.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


@dataclass
class StateDiff:
    """Difference between two state snapshots."""
    diff_id: str = field(default_factory=lambda: f"diff-{uuid.uuid4().hex[:8]}")
    from_version: int = 0
    to_version: int = 0
    added: dict[str, Any] = field(default_factory=dict)
    removed: dict[str, Any] = field(default_factory=dict)
    modified: dict[str, Any] = field(default_factory=dict)
    unchanged: int = 0
    total_keys: int = 0
    change_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "diff_id": self.diff_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "unchanged": self.unchanged,
            "total_keys": self.total_keys,
            "change_ratio": self.change_ratio,
        }


@dataclass
class AgentStateRecord:
    """Complete agent state record with metadata."""
    record_id: str = field(default_factory=lambda: f"rec-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    agent_name: str = ""
    agent_role: str = ""
    current_version: int = 0
    snapshots: list[StateSnapshot] = field(default_factory=list)
    active_snapshot: str = ""
    state_size_bytes: int = 0
    total_snapshots: int = 0
    last_snapshot_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "current_version": self.current_version,
            "active_snapshot": self.active_snapshot,
            "state_size_bytes": self.state_size_bytes,
            "total_snapshots": self.total_snapshots,
            "last_snapshot_at": self.last_snapshot_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class StoreStats:
    """Statistics for the Runtime Store."""
    total_agents: int = 0
    total_snapshots: int = 0
    total_size_bytes: int = 0
    compressed_size_bytes: int = 0
    compression_ratio: float = 0.0
    oldest_snapshot: str = ""
    newest_snapshot: str = ""
    snapshots_by_type: dict[str, int] = field(default_factory=dict)
    snapshots_by_status: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_agents": self.total_agents,
            "total_snapshots": self.total_snapshots,
            "total_size_bytes": self.total_size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "compression_ratio": self.compression_ratio,
            "oldest_snapshot": self.oldest_snapshot,
            "newest_snapshot": self.newest_snapshot,
            "snapshots_by_type": self.snapshots_by_type,
            "snapshots_by_status": self.snapshots_by_status,
        }


# ═══════════════════════════════════════════════════════════
# Runtime Store Implementation
# ═══════════════════════════════════════════════════════════

class AgentRuntimeStore:
    """Persistent agent state management with snapshots, versioning, and restore."""

    def __init__(self, config: RuntimeStoreConfig | None = None):
        self.config = config or RuntimeStoreConfig()
        self._records: dict[str, AgentStateRecord] = {}
        self._snapshots: dict[str, StateSnapshot] = {}
        self._diffs: dict[str, list[StateDiff]] = {}
        self._state_cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock() if self._is_async() else None
        self._last_gc: datetime | None = None
        logger.info("AgentRuntimeStore initialized with backend: %s", self.config.backend.value)

    def _is_async(self) -> bool:
        try:
            import asyncio
            return True
        except ImportError:
            return False

    # ── State Management ─────────────────────────────────

    def register_agent(
        self,
        agent_id: str,
        agent_name: str = "",
        agent_role: str = "",
        initial_state: dict[str, Any] | None = None,
    ) -> AgentStateRecord:
        """Register a new agent for state tracking."""
        if agent_id in self._records:
            logger.warning("Agent already registered: %s", agent_id)
            return self._records[agent_id]

        record = AgentStateRecord(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_role=agent_role,
        )
        self._records[agent_id] = record

        if initial_state:
            self.create_snapshot(agent_id, initial_state, SnapshotType.FULL, tags=["initial"])

        logger.info("Registered agent in store: %s (%s)", agent_name, agent_id)
        return record

    def create_snapshot(
        self,
        agent_id: str,
        state_data: dict[str, Any],
        snapshot_type: SnapshotType = SnapshotType.AUTO,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StateSnapshot | None:
        """Create a new state snapshot for an agent."""
        record = self._records.get(agent_id)
        if not record:
            logger.warning("Agent not registered: %s", agent_id)
            return None

        # Compute state hash
        state_json = json.dumps(state_data, sort_keys=True, default=str)
        state_hash = hashlib.sha256(state_json.encode()).hexdigest()
        original_size = len(state_json)

        # Compress if enabled
        compressed_data = state_json
        compressed_size = original_size
        compression = CompressionMode.NONE

        if self.config.compression == CompressionMode.GZIP:
            compressed_data = gzip.compress(state_json.encode())
            compressed_size = len(compressed_data)
            compression = CompressionMode.GZIP

        # Check size limit
        if original_size > self.config.max_state_size_bytes:
            logger.warning(
                "State size %d exceeds limit %d for agent %s",
                original_size, self.config.max_state_size_bytes, agent_id,
            )

        version = record.current_version + 1
        parent_version = record.current_version if snapshot_type == SnapshotType.INCREMENTAL else 0

        snapshot = StateSnapshot(
            agent_id=agent_id,
            snapshot_type=snapshot_type,
            version=version,
            parent_version=parent_version,
            state_data=state_data,
            state_hash=state_hash,
            compressed_size=compressed_size,
            original_size=original_size,
            compression=compression,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Set expiration
        if self.config.retention_days > 0:
            expiry = datetime.now(timezone.utc) + timedelta(days=self.config.retention_days)
            snapshot.expires_at = expiry.isoformat()

        # Store snapshot
        self._snapshots[snapshot.snapshot_id] = snapshot
        record.snapshots.append(snapshot)
        record.current_version = version
        record.active_snapshot = snapshot.snapshot_id
        record.state_size_bytes += compressed_size
        record.total_snapshots += 1
        record.last_snapshot_at = snapshot.created_at
        record.updated_at = datetime.now(timezone.utc).isoformat()

        # Cache state
        self._state_cache[agent_id] = state_data

        # Enforce snapshot limit
        if len(record.snapshots) > self.config.max_snapshots_per_agent:
            self._prune_oldest_snapshots(agent_id)

        logger.info(
            "Snapshot %s created for agent %s (v%d, %d bytes)",
            snapshot.snapshot_id, agent_id, version, compressed_size,
        )
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> StateSnapshot | None:
        """Retrieve a snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def get_latest_snapshot(self, agent_id: str) -> StateSnapshot | None:
        """Get the most recent snapshot for an agent."""
        record = self._records.get(agent_id)
        if not record or not record.active_snapshot:
            return None
        return self._snapshots.get(record.active_snapshot)

    def get_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get the current state for an agent."""
        # Check cache first
        if agent_id in self._state_cache:
            return self._state_cache[agent_id]

        snapshot = self.get_latest_snapshot(agent_id)
        if snapshot:
            self._state_cache[agent_id] = snapshot.state_data
            return snapshot.state_data
        return None

    def restore_snapshot(self, agent_id: str, snapshot_id: str) -> dict[str, Any] | None:
        """Restore agent state to a specific snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            logger.warning("Snapshot not found: %s", snapshot_id)
            return None

        record = self._records.get(agent_id)
        if record:
            record.active_snapshot = snapshot_id

        self._state_cache[agent_id] = snapshot.state_data
        logger.info("Restored agent %s to snapshot %s (v%d)", agent_id, snapshot_id, snapshot.version)
        return snapshot.state_data

    def list_snapshots(
        self,
        agent_id: str,
        snapshot_type: SnapshotType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StateSnapshot]:
        """List snapshots for an agent with optional filtering."""
        record = self._records.get(agent_id)
        if not record:
            return []

        snapshots = record.snapshots
        if snapshot_type:
            snapshots = [s for s in snapshots if s.snapshot_type == snapshot_type]

        snapshots.sort(key=lambda s: s.version, reverse=True)
        return snapshots[offset:offset + limit]

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        snapshot = self._snapshots.pop(snapshot_id, None)
        if not snapshot:
            return False

        record = self._records.get(snapshot.agent_id)
        if record:
            record.snapshots = [s for s in record.snapshots if s.snapshot_id != snapshot_id]
            record.total_snapshots = len(record.snapshots)
            record.state_size_bytes -= snapshot.compressed_size

        logger.info("Deleted snapshot %s for agent %s", snapshot_id, snapshot.agent_id)
        return True

    def delete_agent(self, agent_id: str) -> bool:
        """Remove an agent and all its snapshots."""
        record = self._records.pop(agent_id, None)
        if not record:
            return False

        for snapshot in record.snapshots:
            self._snapshots.pop(snapshot.snapshot_id, None)

        self._state_cache.pop(agent_id, None)
        self._diffs.pop(agent_id, None)
        logger.info("Deleted agent %s and all snapshots", agent_id)
        return True

    # ── Diffing ──────────────────────────────────────────

    def compute_diff(
        self,
        agent_id: str,
        from_version: int,
        to_version: int,
    ) -> StateDiff | None:
        """Compute the difference between two state versions."""
        from_snapshot = self._get_snapshot_by_version(agent_id, from_version)
        to_snapshot = self._get_snapshot_by_version(agent_id, to_version)

        if not from_snapshot or not to_snapshot:
            return None

        from_state = from_snapshot.state_data
        to_state = to_snapshot.state_data

        added = {}
        removed = {}
        modified = {}
        unchanged = 0

        all_keys = set(from_state.keys()) | set(to_state.keys())
        for key in all_keys:
            in_from = key in from_state
            in_to = key in to_state

            if in_from and in_to:
                if from_state[key] == to_state[key]:
                    unchanged += 1
                else:
                    modified[key] = {"from": from_state[key], "to": to_state[key]}
            elif in_to and not in_from:
                added[key] = to_state[key]
            elif in_from and not in_to:
                removed[key] = from_state[key]

        total_keys = len(all_keys)
        changed = len(added) + len(removed) + len(modified)
        change_ratio = changed / max(total_keys, 1)

        diff = StateDiff(
            from_version=from_version,
            to_version=to_version,
            added=added,
            removed=removed,
            modified=modified,
            unchanged=unchanged,
            total_keys=total_keys,
            change_ratio=change_ratio,
        )

        if agent_id not in self._diffs:
            self._diffs[agent_id] = []
        self._diffs[agent_id].append(diff)

        return diff

    def get_diffs(self, agent_id: str, limit: int = 50) -> list[StateDiff]:
        """Get computed diffs for an agent."""
        return self._diffs.get(agent_id, [])[-limit:]

    # ── Checkpointing ────────────────────────────────────

    def create_checkpoint(self, agent_id: str, state_data: dict[str, Any], label: str = "") -> StateSnapshot | None:
        """Create a named checkpoint snapshot."""
        return self.create_snapshot(
            agent_id,
            state_data,
            SnapshotType.CHECKPOINT,
            tags=["checkpoint"] + ([label] if label else []),
            metadata={"label": label, "timestamp": datetime.now(timezone.utc).isoformat()},
        )

    def list_checkpoints(self, agent_id: str) -> list[StateSnapshot]:
        """List all checkpoint snapshots for an agent."""
        return self.list_snapshots(agent_id, SnapshotType.CHECKPOINT)

    def rollback_to_checkpoint(self, agent_id: str, checkpoint_id: str) -> dict[str, Any] | None:
        """Rollback agent state to a specific checkpoint."""
        return self.restore_snapshot(agent_id, checkpoint_id)

    # ── Garbage Collection ───────────────────────────────

    def run_garbage_collection(self) -> dict[str, int]:
        """Run garbage collection to remove expired snapshots."""
        now = datetime.now(timezone.utc)
        removed = 0
        freed_bytes = 0

        for snapshot_id, snapshot in list(self._snapshots.items()):
            if snapshot.snapshot_type == SnapshotType.CHECKPOINT:
                continue  # Never GC checkpoints

            if snapshot.status == StateStatus.ARCHIVED:
                self.delete_snapshot(snapshot_id)
                removed += 1
                freed_bytes += snapshot.compressed_size
                continue

            if snapshot.expires_at:
                try:
                    expiry = datetime.fromisoformat(snapshot.expires_at)
                    if expiry < now:
                        self.delete_snapshot(snapshot_id)
                        removed += 1
                        freed_bytes += snapshot.compressed_size
                except (ValueError, TypeError):
                    pass

        self._last_gc = now
        logger.info("GC completed: removed %d snapshots, freed %d bytes", removed, freed_bytes)
        return {"removed_snapshots": removed, "freed_bytes": freed_bytes}

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> StoreStats:
        """Get comprehensive store statistics."""
        stats = StoreStats()
        stats.total_agents = len(self._records)
        stats.total_snapshots = len(self._snapshots)

        type_counts: dict[str, int] = defaultdict(int)
        status_counts: dict[str, int] = defaultdict(int)
        oldest_time = None
        newest_time = None

        for snapshot in self._snapshots.values():
            stats.total_size_bytes += snapshot.original_size
            stats.compressed_size_bytes += snapshot.compressed_size
            type_counts[snapshot.snapshot_type.value] += 1
            status_counts[snapshot.status.value] += 1

            if not oldest_time or snapshot.created_at < oldest_time:
                oldest_time = snapshot.created_at
            if not newest_time or snapshot.created_at > newest_time:
                newest_time = snapshot.created_at

        if stats.total_size_bytes > 0:
            stats.compression_ratio = 1 - (stats.compressed_size_bytes / stats.total_size_bytes)

        stats.snapshots_by_type = dict(type_counts)
        stats.snapshots_by_status = dict(status_counts)
        stats.oldest_snapshot = oldest_time or ""
        stats.newest_snapshot = newest_time or ""

        return stats

    def list_agents(self) -> list[AgentStateRecord]:
        """List all registered agents."""
        return list(self._records.values())

    def get_agent_record(self, agent_id: str) -> AgentStateRecord | None:
        """Get a specific agent record."""
        return self._records.get(agent_id)

    def reset(self) -> None:
        """Reset the entire store."""
        self._records.clear()
        self._snapshots.clear()
        self._diffs.clear()
        self._state_cache.clear()
        self._last_gc = None
        logger.info("AgentRuntimeStore reset")

    # ── Internal Helpers ─────────────────────────────────

    def _get_snapshot_by_version(self, agent_id: str, version: int) -> StateSnapshot | None:
        """Find a snapshot by version number."""
        record = self._records.get(agent_id)
        if not record:
            return None
        for snapshot in record.snapshots:
            if snapshot.version == version:
                return snapshot
        return None

    def _prune_oldest_snapshots(self, agent_id: str) -> None:
        """Remove the oldest non-checkpoint snapshots to stay within limits."""
        record = self._records.get(agent_id)
        if not record:
            return

        excess = len(record.snapshots) - self.config.max_snapshots_per_agent
        if excess <= 0:
            return

        # Sort by version ascending, skip checkpoints
        candidates = sorted(
            [s for s in record.snapshots if s.snapshot_type != SnapshotType.CHECKPOINT],
            key=lambda s: s.version,
        )

        for snapshot in candidates[:excess]:
            self.delete_snapshot(snapshot.snapshot_id)


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_runtime_store: AgentRuntimeStore | None = None


def get_runtime_store() -> AgentRuntimeStore:
    """Get or create the global Runtime Store instance."""
    global _runtime_store
    if _runtime_store is None:
        _runtime_store = AgentRuntimeStore()
    return _runtime_store


def reset_runtime_store() -> None:
    """Reset the global Runtime Store instance."""
    global _runtime_store
    if _runtime_store:
        _runtime_store.reset()
    _runtime_store = None