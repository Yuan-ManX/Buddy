"""Buddy Memory Nudge System — proactive memory consolidation suggestions

Provides intelligent nudges that suggest memory consolidation, cleanup,
and reorganization based on usage patterns. Supports rollback of any
consolidation action for safety.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Any

from agent.memory import HierarchicalMemory

logger = logging.getLogger("buddy.nudge")


@dataclass
class NudgeSuggestion:
    """A single memory nudge suggestion."""
    id: str
    agent_id: str
    type: str  # "consolidate", "cleanup", "reorganize", "summarize"
    title: str
    description: str
    affected_memory_ids: list[str]
    priority: float  # 0.0-1.0
    auto_apply: bool
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    applied_at: str | None = None
    reverted_at: str | None = None
    status: str = "pending"  # "pending", "applied", "reverted", "dismissed"


@dataclass
class ConsolidationSnapshot:
    """Snapshot taken before a consolidation, enabling rollback."""
    id: str
    agent_id: str
    nudge_id: str
    original_memory_ids: list[str]
    consolidated_memory_id: str | None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MemoryNudgeEngine:
    """Proactive memory management with intelligent suggestions and rollback support."""

    def __init__(self, agent_id: str, memory: HierarchicalMemory):
        self.agent_id = agent_id
        self.memory = memory
        self._suggestions: dict[str, NudgeSuggestion] = {}
        self._snapshots: dict[str, ConsolidationSnapshot] = {}
        self._nudge_interval = 1800  # 30 minutes
        self._min_cluster_size = 3
        self._similarity_threshold = 0.6

    async def analyze(self) -> list[NudgeSuggestion]:
        """Analyze memory state and generate nudge suggestions."""
        suggestions = []

        # Check for similar memories that could be consolidated
        consolidate_nudges = await self._detect_consolidation_opportunities()
        suggestions.extend(consolidate_nudges)

        # Check for stale/low-importance memories to clean up
        cleanup_nudges = await self._detect_cleanup_opportunities()
        suggestions.extend(cleanup_nudges)

        # Check for tag reorganization opportunities
        reorganize_nudges = await self._detect_reorganization_opportunities()
        suggestions.extend(reorganize_nudges)

        # Check for summarization opportunities
        summarize_nudges = await self._detect_summarization_opportunities()
        suggestions.extend(summarize_nudges)

        # Store suggestions
        for s in suggestions:
            self._suggestions[s.id] = s

        if suggestions:
            logger.info(
                f"Nudge engine generated {len(suggestions)} suggestions for agent {self.agent_id}"
            )

        return suggestions

    async def _detect_consolidation_opportunities(self) -> list[NudgeSuggestion]:
        """Detect memory clusters that could be consolidated into a single entry."""
        suggestions = []

        # Get recent short-term memories
        recent = await self.memory.recall_recent(limit=50)
        if len(recent) < self._min_cluster_size:
            return suggestions

        # Simple keyword-based clustering for similar content
        clusters = self._cluster_by_similarity(recent)

        for topic, cluster in clusters.items():
            if len(cluster) >= self._min_cluster_size:
                ids = [m["id"] for m in cluster]
                suggestion = NudgeSuggestion(
                    id=f"nudge-{uuid.uuid4().hex[:8]}",
                    agent_id=self.agent_id,
                    type="consolidate",
                    title=f"Consolidate {len(cluster)} memories about '{topic}'",
                    description=(
                        f"Found {len(cluster)} memories related to '{topic}'. "
                        f"These could be consolidated into a single long-term memory entry "
                        f"for better organization and recall."
                    ),
                    affected_memory_ids=ids,
                    priority=min(0.5 + len(cluster) * 0.05, 0.95),
                    auto_apply=len(cluster) >= 8,
                )
                suggestions.append(suggestion)

        return suggestions

    def _cluster_by_similarity(self, memories: list[dict]) -> dict[str, list[dict]]:
        """Cluster memories by keyword overlap."""
        import re

        clusters: dict[str, list[dict]] = {}

        for mem in memories:
            content = (mem.get("content", "") or "").lower()
            # Extract significant words (3+ chars, filter common words)
            words = set(
                w for w in re.findall(r'\w{3,}', content)
                if w not in {"the", "and", "for", "that", "this", "with", "was", "have", "from"}
            )

            best_cluster = None
            best_overlap = 0

            for topic, cluster in clusters.items():
                topic_words = set(topic.split())
                overlap = len(words & topic_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_cluster = topic

            if best_cluster and best_overlap >= 2:
                clusters[best_cluster].append(mem)
            else:
                # Find dominant theme
                meaningful = [w for w in words if len(w) > 3]
                topic = meaningful[0] if meaningful else "general"
                if topic not in clusters:
                    clusters[topic] = []
                clusters[topic].append(mem)

        return clusters

    async def _detect_cleanup_opportunities(self) -> list[NudgeSuggestion]:
        """Detect stale or very low-importance memories for cleanup."""
        suggestions = []
        try:
            stats = await self.memory.get_memory_stats()
        except Exception:
            return suggestions

        # Check for expired short-term memories
        if stats.get("short_term_buffer_size", 0) > 20:
            suggestion = NudgeSuggestion(
                id=f"nudge-{uuid.uuid4().hex[:8]}",
                agent_id=self.agent_id,
                type="cleanup",
                title="Clean up short-term memory buffer",
                description=(
                    f"Short-term buffer has {stats['short_term_buffer_size']} entries "
                    f"(threshold: {stats.get('consolidation_threshold', 10)}). "
                    f"Consider consolidating to long-term memory."
                ),
                affected_memory_ids=[],
                priority=0.4,
                auto_apply=False,
            )
            suggestions.append(suggestion)

        return suggestions

    async def _detect_reorganization_opportunities(self) -> list[NudgeSuggestion]:
        """Detect opportunities to reorganize memory tags."""
        suggestions = []
        try:
            tags = await self.memory.get_all_tags()
        except Exception:
            return suggestions

        # Suggest merging similar tags
        tag_names = [t["tag"] for t in tags]
        for i, t1 in enumerate(tag_names):
            for t2 in tag_names[i + 1:]:
                # Simple similarity check
                if t1.lower() == t2.lower() or (
                    len(t1) > 3 and len(t2) > 3 and
                    (t1.lower() in t2.lower() or t2.lower() in t1.lower())
                ):
                    suggestion = NudgeSuggestion(
                        id=f"nudge-{uuid.uuid4().hex[:8]}",
                        agent_id=self.agent_id,
                        type="reorganize",
                        title=f"Merge similar tags: '{t1}' and '{t2}'",
                        description=(
                            f"Tags '{t1}' and '{t2}' appear to be similar. "
                            f"Consider merging them for cleaner organization."
                        ),
                        affected_memory_ids=[],
                        priority=0.3,
                        auto_apply=False,
                    )
                    suggestions.append(suggestion)

        return suggestions

    async def _detect_summarization_opportunities(self) -> list[NudgeSuggestion]:
        """Detect conversation threads that could benefit from summarization."""
        suggestions = []

        # Get long-term memories that could be summarized
        long_term = await self.memory.recall_long_term(limit=30)

        if len(long_term) > 10:
            suggestion = NudgeSuggestion(
                id=f"nudge-{uuid.uuid4().hex[:8]}",
                agent_id=self.agent_id,
                type="summarize",
                title=f"Summarize {len(long_term)} long-term memories",
                description=(
                    f"Found {len(long_term)} long-term memories. "
                    f"Running thematic consolidation could create a more concise summary."
                ),
                affected_memory_ids=[],
                priority=0.35,
                auto_apply=False,
            )
            suggestions.append(suggestion)

        return suggestions

    async def apply(self, nudge_id: str) -> dict:
        """Apply a nudge suggestion."""
        nudge = self._suggestions.get(nudge_id)
        if not nudge:
            return {"success": False, "error": "Nudge not found"}
        if nudge.status != "pending":
            return {"success": False, "error": f"Nudge already {nudge.status}"}

        result = {"success": True, "nudge_id": nudge_id, "type": nudge.type, "actions": []}

        try:
            if nudge.type == "consolidate":
                result = await self._apply_consolidation(nudge)
            elif nudge.type == "summarize":
                result = await self._apply_summarization(nudge)
            elif nudge.type == "cleanup":
                result = await self._apply_cleanup(nudge)
            elif nudge.type == "reorganize":
                result = await self._apply_reorganize(nudge)

            nudge.status = "applied"
            nudge.applied_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            logger.error(f"Failed to apply nudge {nudge_id}: {e}")
            result = {"success": False, "error": str(e)}

        return result

    async def _apply_consolidation(self, nudge: NudgeSuggestion) -> dict:
        """Consolidate a cluster of similar memories."""
        # Take snapshot before consolidation
        snapshot = ConsolidationSnapshot(
            id=f"snap-{uuid.uuid4().hex[:8]}",
            agent_id=self.agent_id,
            nudge_id=nudge.id,
            original_memory_ids=list(nudge.affected_memory_ids),
            consolidated_memory_id=None,
        )

        # Collect content from all affected memories
        contents = []
        async with __import__("database.db", fromlist=["async_session"]).async_session() as session:
            from database.models import Memory as MemoryModel
            from sqlalchemy import select

            for mid in nudge.affected_memory_ids:
                result = await session.execute(
                    select(MemoryModel).where(MemoryModel.id == mid)
                )
                mem = result.scalars().first()
                if mem:
                    contents.append(mem.content)

        if not contents:
            return {"success": False, "error": "No memory contents found"}

        # Store consolidated memory
        combined = "\n\n---\n\n".join(contents)
        consolidated_id = await self.memory.store(
            content=f"[Consolidated via Nudge] {combined}",
            layer="long_term",
            memory_type="consolidation",
            importance=0.5,
        )

        snapshot.consolidated_memory_id = consolidated_id
        self._snapshots[snapshot.id] = snapshot

        return {
            "success": True,
            "nudge_id": nudge.id,
            "type": "consolidate",
            "actions": [
                {
                    "action": "consolidated",
                    "source_count": len(nudge.affected_memory_ids),
                    "result_memory_id": consolidated_id,
                    "snapshot_id": snapshot.id,
                }
            ],
        }

    async def _apply_summarization(self, nudge: NudgeSuggestion) -> dict:
        """Run thematic consolidation."""
        result = await self.memory.consolidate_thematic()
        return {
            "success": True,
            "nudge_id": nudge.id,
            "type": "summarize",
            "actions": [{"action": "thematic_consolidation", **result}],
        }

    async def _apply_cleanup(self, nudge: NudgeSuggestion) -> dict:
        """Clean up expired memories."""
        count = await self.memory.clear_expired(days=7)
        return {
            "success": True,
            "nudge_id": nudge.id,
            "type": "cleanup",
            "actions": [{"action": "cleared_expired", "count": count}],
        }

    async def _apply_reorganize(self, nudge: NudgeSuggestion) -> dict:
        """Reorganize memory tags (placeholder - actual merge requires tag rewrite)."""
        return {
            "success": True,
            "nudge_id": nudge.id,
            "type": "reorganize",
            "actions": [{"action": "tag_review_suggested", "note": "Manual merge recommended"}],
        }

    async def revert(self, nudge_id: str) -> dict:
        """Revert an applied nudge using its snapshot."""
        nudge = self._suggestions.get(nudge_id)
        if not nudge:
            return {"success": False, "error": "Nudge not found"}
        if nudge.status != "applied":
            return {"success": False, "error": "Nudge not in applied state"}

        # Find the snapshot
        snapshot = None
        for snap in self._snapshots.values():
            if snap.nudge_id == nudge_id:
                snapshot = snap
                break

        if not snapshot:
            return {"success": False, "error": "No snapshot found for rollback"}

        try:
            # Delete consolidated memory
            if snapshot.consolidated_memory_id:
                await self.memory.forget(snapshot.consolidated_memory_id)

            nudge.status = "reverted"
            nudge.reverted_at = datetime.now(timezone.utc).isoformat()

            return {
                "success": True,
                "nudge_id": nudge_id,
                "action": "reverted",
                "restored_memory_ids": snapshot.original_memory_ids,
                "removed_consolidated_id": snapshot.consolidated_memory_id,
            }
        except Exception as e:
            logger.error(f"Failed to revert nudge {nudge_id}: {e}")
            return {"success": False, "error": str(e)}

    def dismiss(self, nudge_id: str) -> bool:
        """Dismiss a nudge suggestion without applying."""
        nudge = self._suggestions.get(nudge_id)
        if not nudge or nudge.status != "pending":
            return False
        nudge.status = "dismissed"
        return True

    def get_suggestions(self, status: str | None = None) -> list[dict]:
        """Get nudge suggestions, optionally filtered by status."""
        result = []
        for s in self._suggestions.values():
            if status and s.status != status:
                continue
            result.append({
                "id": s.id,
                "agent_id": s.agent_id,
                "type": s.type,
                "title": s.title,
                "description": s.description,
                "affected_memory_ids": s.affected_memory_ids,
                "priority": s.priority,
                "auto_apply": s.auto_apply,
                "status": s.status,
                "created_at": s.created_at,
                "applied_at": s.applied_at,
                "reverted_at": s.reverted_at,
            })
        return sorted(result, key=lambda x: -x["priority"])

    def get_stats(self) -> dict:
        """Get nudge engine statistics."""
        statuses = {"pending": 0, "applied": 0, "reverted": 0, "dismissed": 0}
        for s in self._suggestions.values():
            statuses[s.status] = statuses.get(s.status, 0) + 1

        return {
            "agent_id": self.agent_id,
            "total_suggestions": len(self._suggestions),
            "by_status": statuses,
            "active_snapshots": len(self._snapshots),
            "last_analysis": max(
                (s.created_at for s in self._suggestions.values()),
                default=None,
            ),
        }