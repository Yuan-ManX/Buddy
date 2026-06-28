"""
Buddy Agent Dream Consolidator - Idle-Window Memory Consolidation with Rollback.

During idle periods, the system consolidates memories, creates snapshots for
rollback safety, and applies tier-aware strategies (merge, summarize, archive,
prioritize, prune). Part of the AI-Native Buddy Agent system.
"""

from __future__ import annotations

import copy
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.agent_dream_consolidator")


# ── Enums ────────────────────────────────────────────────────────


class DreamPhase(str, Enum):
    """Phases of a single dream (idle consolidation) cycle."""

    IDLE_DETECTION = "idle_detection"   # Waiting for / detecting an idle window
    CONSOLIDATION = "consolidation"     # Applying the consolidation strategy
    SYNTHESIS = "synthesis"             # Synthesizing post-consolidation state
    ROLLBACK_PREP = "rollback_prep"     # Preparing rollback snapshots
    COMPLETE = "complete"               # Dream cycle finished


class ConsolidationStrategy(str, Enum):
    """Strategies that may be applied during a dream cycle."""

    MERGE = "merge"           # Merge entries that share tags
    SUMMARIZE = "summarize"   # Compress groups of entries into summaries
    ARCHIVE = "archive"       # Demote low-value entries to ARCHIVED tier
    PRIORITIZE = "prioritize" # Boost importance of frequently accessed entries
    PRUNE = "prune"           # Delete entries below the importance threshold


class MemoryTier(str, Enum):
    """Temperature tiers for memory entries."""

    HOT = "hot"           # Frequently accessed, kept readily available
    WARM = "warm"         # Normal working set
    COLD = "cold"         # Rarely accessed, candidate for archival
    ARCHIVED = "archived" # Persisted but not in the active working set


class SnapshotType(str, Enum):
    """Types of memory snapshots captured for rollback."""

    FULL = "full"                     # Complete snapshot of all entries
    INCREMENTAL = "incremental"       # Delta since the last snapshot
    PRE_CONSOLIDATION = "pre_consolidation"   # Captured before a dream runs
    POST_CONSOLIDATION = "post_consolidation" # Captured after a dream runs


# ── Dataclasses ──────────────────────────────────────────────────


@dataclass
class MemoryEntry:
    """A single memory entry managed by the dream consolidator."""

    entry_id: str
    content: str
    tier: MemoryTier
    importance: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class DreamSession:
    """Record of a single dream (idle consolidation) cycle."""

    session_id: str
    phase: DreamPhase
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    entries_processed: int = 0
    entries_consolidated: int = 0
    entries_archived: int = 0
    strategy: ConsolidationStrategy = ConsolidationStrategy.MERGE
    snapshot_before: str | None = None
    snapshot_after: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemorySnapshot:
    """An immutable snapshot of memory state for rollback."""

    snapshot_id: str
    session_id: str | None
    snapshot_type: SnapshotType
    entries: list[MemoryEntry] = field(default_factory=list)
    total_entries: int = 0
    created_at: float = field(default_factory=time.time)
    checksum: str = ""


@dataclass
class ConsolidationResult:
    """Outcome of applying a consolidation strategy during a dream."""

    result_id: str
    session_id: str
    original_count: int
    consolidated_count: int
    archived_count: int
    strategy: ConsolidationStrategy
    improvements: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


# ── Main Consolidator ────────────────────────────────────────────


class AgentDreamConsolidator:
    """Idle-window memory consolidation engine with rollback support.

    The consolidator maintains an in-memory store of :class:`MemoryEntry`
    instances. During idle windows it runs a "dream" cycle that captures
    pre/post snapshots (enabling rollback), applies a consolidation strategy,
    and records the outcome in a :class:`DreamSession`.
    """

    MAX_ENTRIES = 10000             # Hard cap on stored entries
    IDLE_THRESHOLD = 300            # Seconds of inactivity before a dream may start
    MAX_SNAPSHOTS = 50              # Maximum number of retained snapshots
    IMPORTANCE_THRESHOLD = 0.5      # Entries below this are candidates for pruning

    def __init__(self) -> None:
        # Primary storage: entry_id -> MemoryEntry
        self._entries: dict[str, MemoryEntry] = {}
        # Snapshot storage: snapshot_id -> MemorySnapshot (insertion-ordered)
        self._snapshots: dict[str, MemorySnapshot] = {}
        # Dream session storage: session_id -> DreamSession (insertion-ordered)
        self._sessions: dict[str, DreamSession] = {}
        # Counters / state
        self._total_dreams: int = 0
        self._last_dream_at: float | None = None
        self._last_snapshot_id: str | None = None

    # ── Entry CRUD ───────────────────────────────────────────────

    def add_entry(
        self,
        content: str,
        tier: MemoryTier = MemoryTier.WARM,
        importance: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Create and store a new memory entry.

        Args:
            content: The textual content of the memory.
            tier: Initial memory tier. Defaults to :attr:`MemoryTier.WARM`.
            importance: Initial importance score in ``[0.0, 1.0]``.
            tags: Optional list of tags for grouping and lookup.
            metadata: Optional arbitrary metadata payload.

        Returns:
            The newly created :class:`MemoryEntry`.
        """
        now = time.time()
        entry = MemoryEntry(
            entry_id=f"entry-{uuid.uuid4().hex[:12]}",
            content=content,
            tier=tier,
            importance=max(0.0, min(1.0, importance)),
            access_count=0,
            last_accessed=now,
            tags=list(tags) if tags else [],
            metadata=dict(metadata) if metadata else {},
            created_at=now,
            updated_at=now,
        )
        self._entries[entry.entry_id] = entry

        # Enforce capacity by dropping the least-important cold entries first.
        if len(self._entries) > self.MAX_ENTRIES:
            self._evict_to_capacity()

        return entry

    def update_entry(
        self,
        entry_id: str,
        content: str | None = None,
        tier: MemoryTier | None = None,
        importance: float | None = None,
        tags: list[str] | None = None,
    ) -> MemoryEntry | None:
        """Update fields of an existing entry.

        Only fields that are not ``None`` are modified. Returns ``None`` if the
        entry does not exist.
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            return None

        if content is not None:
            entry.content = content
        if tier is not None:
            entry.tier = tier
        if importance is not None:
            entry.importance = max(0.0, min(1.0, importance))
        if tags is not None:
            entry.tags = list(tags)
        entry.updated_at = time.time()
        return entry

    def access_entry(self, entry_id: str) -> MemoryEntry | None:
        """Record an access of an entry, bumping its access counters.

        Returns the entry, or ``None`` if it does not exist.
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            return None
        entry.access_count += 1
        entry.last_accessed = time.time()
        # Promote to HOT when accessed frequently.
        if entry.access_count >= 5 and entry.tier != MemoryTier.HOT:
            entry.tier = MemoryTier.HOT
            entry.updated_at = entry.last_accessed
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID. Returns ``True`` if an entry was removed."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def get_entry(self, entry_id: str) -> MemoryEntry | None:
        """Return the entry with the given ID, or ``None``."""
        return self._entries.get(entry_id)

    def list_entries(
        self,
        tier: MemoryTier | None = None,
        min_importance: float | None = None,
        tags: list[str] | None = None,
        limit: int | None = None,
    ) -> list[MemoryEntry]:
        """List entries, optionally filtered by tier, importance, and tags.

        Results are ordered by ``created_at`` ascending (oldest first). When a
        ``limit`` is provided, only the first ``limit`` entries are returned
        after filtering.
        """
        tag_set = set(tags) if tags else None
        results: list[MemoryEntry] = []
        for entry in self._entries.values():
            if tier is not None and entry.tier != tier:
                continue
            if min_importance is not None and entry.importance < min_importance:
                continue
            if tag_set is not None and not tag_set.intersection(entry.tags):
                continue
            results.append(entry)
        results.sort(key=lambda e: e.created_at)
        if limit is not None and limit >= 0:
            results = results[:limit]
        return results

    # ── Snapshots & Rollback ─────────────────────────────────────

    def create_snapshot(
        self,
        snapshot_type: SnapshotType = SnapshotType.FULL,
        session_id: str | None = None,
    ) -> MemorySnapshot:
        """Capture a deep-copy snapshot of all current entries.

        Args:
            snapshot_type: The :class:`SnapshotType` to record.
            session_id: Optional owning dream session ID.

        Returns:
            The newly created :class:`MemorySnapshot`.
        """
        # Deep copy so later mutations do not affect the snapshot.
        entries = [copy.deepcopy(e) for e in self._entries.values()]
        snapshot = MemorySnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            snapshot_type=snapshot_type,
            entries=entries,
            total_entries=len(entries),
            created_at=time.time(),
            checksum=self._compute_checksum(entries),
        )
        self._snapshots[snapshot.snapshot_id] = snapshot
        self._last_snapshot_id = snapshot.snapshot_id

        # Enforce snapshot retention cap (drop oldest).
        if len(self._snapshots) > self.MAX_SNAPSHOTS:
            oldest_id = next(iter(self._snapshots))
            del self._snapshots[oldest_id]
            if self._last_snapshot_id == oldest_id:
                self._last_snapshot_id = (
                    next(reversed(self._snapshots)) if self._snapshots else None
                )
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore the entry store from a snapshot.

        Replaces all current entries with deep copies of the snapshot's
        entries. Returns ``True`` if the snapshot existed and was restored.
        """
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            return False
        self._entries = {
            e.entry_id: copy.deepcopy(e) for e in snapshot.entries
        }
        logger.info(
            "Restored snapshot %s with %d entries", snapshot_id, len(self._entries)
        )
        return True

    def get_snapshot(self, snapshot_id: str) -> MemorySnapshot | None:
        """Return the snapshot with the given ID, or ``None``."""
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self, limit: int = 20) -> list[MemorySnapshot]:
        """List snapshots, most recent first."""
        snapshots = list(self._snapshots.values())
        snapshots.sort(key=lambda s: s.created_at, reverse=True)
        return snapshots[:limit] if limit >= 0 else snapshots

    # ── Dream Cycle ──────────────────────────────────────────────

    def start_dream(
        self,
        strategy: ConsolidationStrategy = ConsolidationStrategy.MERGE,
    ) -> DreamSession:
        """Run a full dream (idle consolidation) cycle.

        Steps:
            1. Open a :class:`DreamSession` (IDLE_DETECTION -> CONSOLIDATION).
            2. Capture a PRE_CONSOLIDATION snapshot for rollback.
            3. Apply the consolidation strategy via :meth:`_consolidate`.
            4. Capture a POST_CONSOLIDATION snapshot.
            5. Mark the session COMPLETE and return it.
        """
        session = DreamSession(
            session_id=f"dream-{uuid.uuid4().hex[:12]}",
            phase=DreamPhase.IDLE_DETECTION,
            strategy=strategy,
            started_at=time.time(),
        )
        self._sessions[session.session_id] = session
        self._total_dreams += 1
        self._last_dream_at = session.started_at

        # Transition into consolidation and capture the pre-snapshot.
        session.phase = DreamPhase.CONSOLIDATION
        pre_snapshot = self.create_snapshot(
            snapshot_type=SnapshotType.PRE_CONSOLIDATION,
            session_id=session.session_id,
        )
        session.snapshot_before = pre_snapshot.snapshot_id
        session.entries_processed = len(self._entries)

        # Apply the strategy.
        result = self._consolidate(session, strategy)
        session.entries_consolidated = result.consolidated_count
        session.entries_archived = result.archived_count

        # Synthesis phase: capture post-snapshot.
        session.phase = DreamPhase.SYNTHESIS
        post_snapshot = self.create_snapshot(
            snapshot_type=SnapshotType.POST_CONSOLIDATION,
            session_id=session.session_id,
        )
        session.snapshot_after = post_snapshot.snapshot_id

        # Rollback prep is satisfied by the captured snapshots.
        session.phase = DreamPhase.ROLLBACK_PREP
        session.metrics = {
            "original_count": result.original_count,
            "remaining_count": len(self._entries),
            "improvements": list(result.improvements),
            "pre_snapshot": pre_snapshot.snapshot_id,
            "post_snapshot": post_snapshot.snapshot_id,
            "pre_checksum": pre_snapshot.checksum,
            "post_checksum": post_snapshot.checksum,
        }

        session.phase = DreamPhase.COMPLETE
        session.completed_at = time.time()
        logger.info(
            "Dream %s complete: processed=%d consolidated=%d archived=%d",
            session.session_id,
            session.entries_processed,
            session.entries_consolidated,
            session.entries_archived,
        )
        return session

    def _consolidate(
        self,
        session: DreamSession,
        strategy: ConsolidationStrategy,
    ) -> ConsolidationResult:
        """Apply a consolidation strategy to the current entry store.

        This is the internal strategy dispatcher invoked by
        :meth:`start_dream`. It returns a :class:`ConsolidationResult`
        describing the outcome.
        """
        original_count = len(self._entries)
        improvements: list[str] = []
        consolidated = 0
        archived = 0

        if strategy == ConsolidationStrategy.MERGE:
            consolidated = self._strategy_merge(improvements)
        elif strategy == ConsolidationStrategy.SUMMARIZE:
            consolidated = self._strategy_summarize(improvements)
        elif strategy == ConsolidationStrategy.ARCHIVE:
            archived = self._strategy_archive(improvements)
        elif strategy == ConsolidationStrategy.PRIORITIZE:
            consolidated = self._strategy_prioritize(improvements)
        elif strategy == ConsolidationStrategy.PRUNE:
            consolidated = self._strategy_prune(improvements)

        result = ConsolidationResult(
            result_id=f"result-{uuid.uuid4().hex[:12]}",
            session_id=session.session_id,
            original_count=original_count,
            consolidated_count=consolidated,
            archived_count=archived,
            strategy=strategy,
            improvements=improvements,
            created_at=time.time(),
        )
        return result

    # ── Consolidation Strategies ─────────────────────────────────

    def _strategy_merge(self, improvements: list[str]) -> int:
        """Merge entries that share tags into single combined entries.

        Returns the number of entries that were merged away (i.e. the
        reduction in entry count).
        """
        # Group entry IDs by each of their tags.
        groups: dict[str, list[MemoryEntry]] = {}
        for entry in list(self._entries.values()):
            for tag in entry.tags:
                groups.setdefault(tag, []).append(entry)

        merged_away = 0
        consumed_ids: set[str] = set()
        for tag, group in groups.items():
            # Only merge groups with at least two entries that have not been
            # consumed by a prior merge in this pass.
            candidates = [e for e in group if e.entry_id not in consumed_ids]
            if len(candidates) < 2:
                continue

            merged = self._merge_entries(candidates, tag)
            if merged is None:
                continue
            for e in candidates:
                consumed_ids.add(e.entry_id)
                self._entries.pop(e.entry_id, None)
            self._entries[merged.entry_id] = merged
            merged_away += len(candidates) - 1

        if merged_away > 0:
            improvements.append(
                f"Merged {merged_away} entries by shared tags"
            )
            logger.info("Merge strategy: removed %d entries", merged_away)
        return merged_away

    def _strategy_summarize(self, improvements: list[str]) -> int:
        """Compress groups of entries into single summary entries.

        Entries sharing the same primary tag are collapsed into one entry
        whose content is a delimited summary of the originals. Returns the
        number of entries removed.
        """
        groups: dict[str, list[MemoryEntry]] = {}
        for entry in list(self._entries.values()):
            primary = entry.tags[0] if entry.tags else "untagged"
            groups.setdefault(primary, []).append(entry)

        removed = 0
        for primary, group in groups.items():
            if len(group) < 2:
                continue
            contents = [e.content for e in group]
            summary = " | ".join(c[:120] for c in contents if c)
            summary = summary[:500]
            max_importance = max(e.importance for e in group)
            total_access = sum(e.access_count for e in group)
            union_tags = sorted({t for e in group for t in e.tags})
            merged_metadata: dict[str, Any] = {"source_count": len(group)}

            summary_entry = MemoryEntry(
                entry_id=f"entry-{uuid.uuid4().hex[:12]}",
                content=summary,
                tier=MemoryTier.WARM,
                importance=max_importance,
                access_count=total_access,
                last_accessed=max(e.last_accessed for e in group),
                tags=union_tags,
                metadata=merged_metadata,
                created_at=min(e.created_at for e in group),
                updated_at=time.time(),
            )
            for e in group:
                self._entries.pop(e.entry_id, None)
            self._entries[summary_entry.entry_id] = summary_entry
            removed += len(group) - 1

        if removed > 0:
            improvements.append(
                f"Summarized entries, reduced count by {removed}"
            )
            logger.info("Summarize strategy: removed %d entries", removed)
        return removed

    def _strategy_archive(self, improvements: list[str]) -> int:
        """Demote low-value entries to the ARCHIVED tier.

        Entries that are COLD or below the importance threshold, or that have
        not been accessed recently, are archived. Returns the number of
        entries archived.
        """
        now = time.time()
        archived = 0
        for entry in self._entries.values():
            if entry.tier == MemoryTier.ARCHIVED:
                continue
            should_archive = (
                entry.tier == MemoryTier.COLD
                or entry.importance < self.IMPORTANCE_THRESHOLD
                or (entry.access_count == 0 and (now - entry.created_at) > self.IDLE_THRESHOLD)
            )
            if should_archive:
                entry.tier = MemoryTier.ARCHIVED
                entry.updated_at = now
                archived += 1
        if archived > 0:
            improvements.append(
                f"Archived {archived} low-value entries"
            )
            logger.info("Archive strategy: archived %d entries", archived)
        return archived

    def _strategy_prioritize(self, improvements: list[str]) -> int:
        """Boost importance of frequently accessed entries.

        Entries accessed at least three times have their importance raised
        (capped at 1.0) and are promoted toward HOT. Returns the number of
        entries that were adjusted.
        """
        prioritized = 0
        for entry in self._entries.values():
            if entry.access_count >= 3:
                entry.importance = min(1.0, entry.importance + 0.1)
                if entry.tier == MemoryTier.WARM:
                    entry.tier = MemoryTier.HOT
                elif entry.tier == MemoryTier.COLD:
                    entry.tier = MemoryTier.WARM
                entry.updated_at = time.time()
                prioritized += 1
        if prioritized > 0:
            improvements.append(
                f"Prioritized {prioritized} frequently-accessed entries"
            )
            logger.info(
                "Prioritize strategy: boosted %d entries", prioritized
            )
        return prioritized

    def _strategy_prune(self, improvements: list[str]) -> int:
        """Delete entries below the importance threshold that are unused.

        Entries with importance below :attr:`IMPORTANCE_THRESHOLD` and zero
        access count are removed entirely. Returns the number of entries
        pruned.
        """
        to_remove = [
            entry_id
            for entry_id, entry in self._entries.items()
            if entry.importance < self.IMPORTANCE_THRESHOLD
            and entry.access_count == 0
        ]
        for entry_id in to_remove:
            del self._entries[entry_id]
        if to_remove:
            improvements.append(
                f"Pruned {len(to_remove)} low-value entries"
            )
            logger.info("Prune strategy: removed %d entries", len(to_remove))
        return len(to_remove)

    # ── Session Accessors ────────────────────────────────────────

    def get_dream_session(self, session_id: str) -> DreamSession | None:
        """Return the dream session with the given ID, or ``None``."""
        return self._sessions.get(session_id)

    def list_dream_sessions(self, limit: int = 20) -> list[DreamSession]:
        """List dream sessions, most recent first."""
        sessions = list(self._sessions.values())
        sessions.sort(key=lambda s: s.started_at, reverse=True)
        return sessions[:limit] if limit >= 0 else sessions

    # ── Stats & Maintenance ──────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics about the consolidator's state."""
        tier_distribution: dict[str, int] = {tier.value: 0 for tier in MemoryTier}
        importance_sum = 0.0
        for entry in self._entries.values():
            tier_distribution[entry.tier.value] = (
                tier_distribution.get(entry.tier.value, 0) + 1
            )
            importance_sum += entry.importance
        total_entries = len(self._entries)
        avg_importance = (
            importance_sum / total_entries if total_entries > 0 else 0.0
        )
        return {
            "total_entries": total_entries,
            "total_snapshots": len(self._snapshots),
            "total_dreams": self._total_dreams,
            "tier_distribution": tier_distribution,
            "avg_importance": avg_importance,
            "last_dream_at": self._last_dream_at,
        }

    def reset(self) -> None:
        """Clear all entries, snapshots, sessions, and counters."""
        self._entries.clear()
        self._snapshots.clear()
        self._sessions.clear()
        self._total_dreams = 0
        self._last_dream_at = None
        self._last_snapshot_id = None

    # ── Internal Helpers ─────────────────────────────────────────

    def _compute_checksum(self, entries: list[MemoryEntry]) -> str:
        """Compute a stable SHA-256 checksum over a list of entries."""
        digest = hashlib.sha256()
        for entry in sorted(entries, key=lambda e: e.entry_id):
            payload = "|".join(
                [
                    entry.entry_id,
                    entry.content,
                    entry.tier.value,
                    f"{entry.importance:.6f}",
                    ",".join(sorted(entry.tags)),
                ]
            )
            digest.update(payload.encode("utf-8"))
            digest.update(b"\n")
        return digest.hexdigest()

    def _merge_entries(
        self, entries: list[MemoryEntry], tag: str
    ) -> MemoryEntry | None:
        """Merge a list of entries into a single combined entry.

        The combined entry concatenates content (truncated), takes the max
        importance, sums access counts, unions tags, and selects the hottest
        tier among the inputs.
        """
        if not entries:
            return None
        combined_content = " | ".join(e.content for e in entries if e.content)
        combined_content = combined_content[:500]
        max_importance = max(e.importance for e in entries)
        total_access = sum(e.access_count for e in entries)
        union_tags = sorted({t for e in entries for t in e.tags})
        # Hottest tier wins: HOT > WARM > COLD > ARCHIVED.
        tier_rank = {
            MemoryTier.HOT: 0,
            MemoryTier.WARM: 1,
            MemoryTier.COLD: 2,
            MemoryTier.ARCHIVED: 3,
        }
        hottest_tier = min(entries, key=lambda e: tier_rank.get(e.tier, 3)).tier
        merged_metadata: dict[str, Any] = {
            "merged_from": [e.entry_id for e in entries],
            "merge_tag": tag,
        }
        return MemoryEntry(
            entry_id=f"entry-{uuid.uuid4().hex[:12]}",
            content=combined_content,
            tier=hottest_tier,
            importance=max_importance,
            access_count=total_access,
            last_accessed=max(e.last_accessed for e in entries),
            tags=union_tags,
            metadata=merged_metadata,
            created_at=min(e.created_at for e in entries),
            updated_at=time.time(),
        )

    def _evict_to_capacity(self) -> None:
        """Drop the least-important, least-recently-accessed entries."""
        if len(self._entries) <= self.MAX_ENTRIES:
            return
        # Rank by (importance asc, access_count asc, last_accessed asc).
        ranked = sorted(
            self._entries.values(),
            key=lambda e: (e.importance, e.access_count, e.last_accessed),
        )
        overflow = len(self._entries) - self.MAX_ENTRIES
        for entry in ranked[:overflow]:
            self._entries.pop(entry.entry_id, None)
        logger.info("Evicted %d entries to restore capacity", overflow)


# ── Singleton accessors ──────────────────────────────────────────

_dream_consolidator: AgentDreamConsolidator | None = None


def get_dream_consolidator() -> AgentDreamConsolidator:
    """Get or create the singleton dream consolidator instance."""
    global _dream_consolidator
    if _dream_consolidator is None:
        _dream_consolidator = AgentDreamConsolidator()
    return _dream_consolidator


def reset_dream_consolidator() -> None:
    """Reset the singleton dream consolidator instance."""
    global _dream_consolidator
    if _dream_consolidator is not None:
        _dream_consolidator.reset()
    _dream_consolidator = None
