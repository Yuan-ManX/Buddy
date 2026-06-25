"""Buddy Session Commander — session grouping, batching, and lifecycle management

Provides a command layer for operating on multiple sessions at once:
- Group sessions by topic, user, project, or time
- Batch operations (summarize, archive, merge, export, delete)
- Session lifecycle (pause, resume, branch, merge, snapshot, rollback)
- Session search with full-text and filter-based retrieval
"""
from __future__ import annotations

import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.agent_session_commander")


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

class BatchOpType(str, Enum):
    SUMMARIZE = "summarize"
    ARCHIVE = "archive"
    MERGE = "merge"
    EXPORT = "export"
    DELETE = "delete"


class BatchOpStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    COMPLETED = "completed"


# ══════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════

@dataclass
class SessionGroup:
    """A logical grouping of related sessions."""
    group_id: str = field(default_factory=lambda: f"grp-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    parent_id: str | None = None
    session_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id, "name": self.name,
            "description": self.description, "parent_id": self.parent_id,
            "session_ids": self.session_ids, "session_count": len(self.session_ids),
            "created_at": self.created_at,
        }


@dataclass
class BatchOperation:
    """A batch operation applied to multiple sessions."""
    op_id: str = field(default_factory=lambda: f"batch-{uuid.uuid4().hex[:8]}")
    op_type: BatchOpType = BatchOpType.SUMMARIZE
    target_sessions: list[str] = field(default_factory=list)
    status: BatchOpStatus = BatchOpStatus.PENDING
    progress: float = 0.0
    results: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "op_id": self.op_id, "op_type": self.op_type.value,
            "target_sessions": self.target_sessions,
            "session_count": len(self.target_sessions),
            "status": self.status.value, "progress": self.progress,
            "result_count": len(self.results),
            "created_at": self.created_at, "completed_at": self.completed_at,
        }


@dataclass
class SessionSnapshot:
    """A point-in-time capture of a session's state."""
    snapshot_id: str = field(default_factory=lambda: f"snap-{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id, "session_id": self.session_id,
            "description": self.description, "created_at": self.created_at,
        }


@dataclass
class SessionBranch:
    """A branch created from a session at a specific point."""
    branch_id: str = field(default_factory=lambda: f"branch-{uuid.uuid4().hex[:8]}")
    parent_session_id: str = ""
    branch_point: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id, "parent_session_id": self.parent_session_id,
            "branch_point": self.branch_point, "created_at": self.created_at,
        }


@dataclass
class SessionTemplate:
    """A reusable template for session creation."""
    template_id: str = field(default_factory=lambda: f"tmpl-{uuid.uuid4().hex[:8]}")
    name: str = ""
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id, "name": self.name,
            "system_prompt": self.system_prompt[:100],
            "tools": self.tools, "skills": self.skills,
            "created_at": self.created_at,
        }


@dataclass
class SessionCommanderStats:
    """Aggregate statistics for the session commander."""
    total_sessions: int = 0
    active_groups: int = 0
    batches_run: int = 0
    total_snapshots: int = 0
    total_branches: int = 0
    total_templates: int = 0
    active_sessions: int = 0
    paused_sessions: int = 0
    archived_sessions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "active_groups": self.active_groups,
            "batches_run": self.batches_run,
            "total_snapshots": self.total_snapshots,
            "total_branches": self.total_branches,
            "total_templates": self.total_templates,
            "active_sessions": self.active_sessions,
            "paused_sessions": self.paused_sessions,
            "archived_sessions": self.archived_sessions,
        }


# ══════════════════════════════════════════════════════════════
# Session Commander
# ══════════════════════════════════════════════════════════════

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "it", "its", "that", "this", "these", "those", "i", "me", "my",
    "we", "our", "you", "your", "he", "she", "they", "them", "not",
    "no", "nor", "so", "as", "if", "then", "than", "too", "very",
    "just", "about", "also", "into", "over", "under", "after",
    "before", "between", "through",
})


class SessionCommander:
    """Manages session groups, batch operations, lifecycle, and search.

    Provides grouping of sessions into hierarchical collections, batch
    operations across multiple sessions, lifecycle controls including
    snapshot/rollback and branching/merging, and session search.
    """

    def __init__(self) -> None:
        self._groups: dict[str, SessionGroup] = {}
        self._batches: dict[str, BatchOperation] = {}
        self._session_states: dict[str, SessionState] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._snapshots: dict[str, list[SessionSnapshot]] = defaultdict(list)
        self._branches: dict[str, list[SessionBranch]] = defaultdict(list)
        self._templates: dict[str, SessionTemplate] = {}
        self._text_index: dict[str, set[str]] = defaultdict(set)
        self._batches_run: int = 0
        self._total_sessions_registered: int = 0
        self._seed_templates()

    # ── Session Registration ──────────────────────────────────────

    def register_session(self, session_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Register a session with the commander for tracking."""
        if session_id not in self._session_states:
            self._session_states[session_id] = SessionState.ACTIVE
            self._sessions[session_id] = metadata or {}
            self._total_sessions_registered += 1
        elif metadata:
            self._sessions[session_id].update(metadata)

    def unregister_session(self, session_id: str) -> bool:
        """Remove a session from tracking."""
        if session_id not in self._session_states:
            return False
        del self._session_states[session_id]
        self._sessions.pop(session_id, None)
        for group in self._groups.values():
            if session_id in group.session_ids:
                group.session_ids.remove(session_id)
        self._remove_from_text_index(session_id)
        return True

    # ── Session Grouping ──────────────────────────────────────────

    def create_group(
        self, name: str, description: str = "",
        session_ids: list[str] | None = None, parent_id: str | None = None,
    ) -> SessionGroup:
        """Create a group of related sessions with optional parent for hierarchy."""
        group = SessionGroup(
            name=name, description=description,
            parent_id=parent_id, session_ids=list(session_ids or []),
        )
        self._groups[group.group_id] = group
        logger.info("Group created: %s (%s) with %d sessions", group.group_id, name, len(group.session_ids))
        return group

    def get_groups(self) -> list[SessionGroup]:
        """Return all session groups."""
        return list(self._groups.values())

    def get_group(self, group_id: str) -> SessionGroup | None:
        """Get a group by ID."""
        return self._groups.get(group_id)

    def get_group_children(self, parent_id: str) -> list[SessionGroup]:
        """Get all child groups of a parent group."""
        return [g for g in self._groups.values() if g.parent_id == parent_id]

    def delete_group(self, group_id: str) -> bool:
        """Delete a group without deleting its sessions."""
        if group_id not in self._groups:
            return False
        del self._groups[group_id]
        return True

    def auto_group_by_topic(self, topic_keyword: str) -> SessionGroup:
        """Create a group of sessions matching a topic keyword via text index."""
        matching: set[str] = set()
        for token in self._tokenize(topic_keyword):
            matching.update(self._text_index.get(token, set()))
        return self.create_group(
            name=f"Topic: {topic_keyword}",
            description=f"Auto-grouped sessions matching '{topic_keyword}'",
            session_ids=list(matching),
        )

    # ── Batch Operations ──────────────────────────────────────────

    def _execute_batch(self, op_type: BatchOpType, session_ids: list[str], processor: Any) -> BatchOperation:
        batch = BatchOperation(op_type=op_type, target_sessions=list(session_ids), status=BatchOpStatus.IN_PROGRESS)
        self._batches[batch.op_id] = batch
        total = len(session_ids)
        for i, sid in enumerate(session_ids):
            try:
                result = processor(sid)
                batch.results.append({"session_id": sid, "status": "success", "data": result})
            except Exception as exc:
                batch.results.append({"session_id": sid, "status": "error", "error": str(exc)})
            batch.progress = round((i + 1) / max(total, 1), 2)
        batch.status = BatchOpStatus.COMPLETED
        batch.completed_at = datetime.now(timezone.utc).isoformat()
        self._batches_run += 1
        return batch

    def batch_summarize(self, session_ids: list[str]) -> BatchOperation:
        """Generate summaries for multiple sessions in a batch."""
        def _summarize(sid: str) -> dict[str, Any]:
            state = self._session_states.get(sid)
            return {"session_id": sid, "state": state.value if state else "unknown", "metadata": self._sessions.get(sid, {})}
        logger.info("Batch summarize: %d sessions", len(session_ids))
        return self._execute_batch(BatchOpType.SUMMARIZE, session_ids, _summarize)

    def batch_archive(self, session_ids: list[str]) -> BatchOperation:
        """Archive multiple sessions in a batch."""
        def _archive(sid: str) -> dict[str, Any]:
            self._session_states[sid] = SessionState.ARCHIVED
            return {"session_id": sid, "new_state": "archived"}
        logger.info("Batch archive: %d sessions", len(session_ids))
        return self._execute_batch(BatchOpType.ARCHIVE, session_ids, _archive)

    def batch_merge(self, session_ids: list[str]) -> BatchOperation:
        """Merge related sessions into one in a batch."""
        merged_id = self.merge_sessions(session_ids)
        batch = BatchOperation(
            op_type=BatchOpType.MERGE, target_sessions=list(session_ids),
            status=BatchOpStatus.COMPLETED, progress=1.0,
            results=[{"session_ids": session_ids, "merged_session_id": merged_id, "status": "success"}],
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._batches[batch.op_id] = batch
        self._batches_run += 1
        logger.info("Batch merge: %d sessions -> %s", len(session_ids), merged_id)
        return batch

    def batch_export(self, session_ids: list[str]) -> BatchOperation:
        """Export session data for multiple sessions in a batch."""
        def _export(sid: str) -> dict[str, Any]:
            state = self._session_states.get(sid)
            snapshots = [s.to_dict() for s in self._snapshots.get(sid, [])]
            return {
                "session_id": sid, "state": state.value if state else "unknown",
                "metadata": self._sessions.get(sid, {}), "snapshot_count": len(snapshots), "snapshots": snapshots,
            }
        logger.info("Batch export: %d sessions", len(session_ids))
        return self._execute_batch(BatchOpType.EXPORT, session_ids, _export)

    def batch_delete(self, session_ids: list[str]) -> BatchOperation:
        """Delete multiple sessions in a batch."""
        def _delete(sid: str) -> dict[str, Any]:
            self.unregister_session(sid)
            return {"session_id": sid, "status": "deleted"}
        logger.info("Batch delete: %d sessions", len(session_ids))
        return self._execute_batch(BatchOpType.DELETE, session_ids, _delete)

    def get_batch(self, op_id: str) -> BatchOperation | None:
        """Get a batch operation by ID."""
        return self._batches.get(op_id)

    # ── Session Lifecycle ─────────────────────────────────────────

    def pause_session(self, session_id: str) -> bool:
        """Pause an active session."""
        if session_id not in self._session_states:
            return False
        self._session_states[session_id] = SessionState.PAUSED
        return True

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session."""
        if self._session_states.get(session_id) != SessionState.PAUSED:
            return False
        self._session_states[session_id] = SessionState.ACTIVE
        return True

    def create_snapshot(self, session_id: str, description: str = "") -> SessionSnapshot | None:
        """Create a point-in-time snapshot of a session's state."""
        if session_id not in self._session_states:
            return None
        snapshot = SessionSnapshot(
            session_id=session_id,
            state={"state": self._session_states[session_id].value, "metadata": self._sessions.get(session_id, {}).copy()},
            description=description,
        )
        self._snapshots[session_id].append(snapshot)
        logger.info("Snapshot %s created for session %s", snapshot.snapshot_id, session_id)
        return snapshot

    def restore_snapshot(self, session_id: str, snapshot_id: str) -> bool:
        """Restore a session's state from a snapshot."""
        for snap in self._snapshots.get(session_id, []):
            if snap.snapshot_id == snapshot_id:
                state_value = snap.state.get("state", SessionState.ACTIVE.value)
                self._session_states[session_id] = SessionState(state_value)
                self._sessions[session_id] = snap.state.get("metadata", {}).copy()
                logger.info("Session %s restored from snapshot %s", session_id, snapshot_id)
                return True
        return False

    def get_snapshots(self, session_id: str) -> list[SessionSnapshot]:
        """Get all snapshots for a session."""
        return list(self._snapshots.get(session_id, []))

    def branch_session(self, session_id: str, branch_point: str = "") -> SessionBranch | None:
        """Create a branch from a session at a given point."""
        if session_id not in self._session_states:
            return None
        branch = SessionBranch(
            parent_session_id=session_id, branch_point=branch_point,
            state={"state": self._session_states[session_id].value, "metadata": self._sessions.get(session_id, {}).copy()},
        )
        self._branches[session_id].append(branch)
        logger.info("Branch %s created from session %s at '%s'", branch.branch_id, session_id, branch_point)
        return branch

    def get_branches(self, session_id: str) -> list[SessionBranch]:
        """Get all branches created from a session."""
        return list(self._branches.get(session_id, []))

    def merge_sessions(self, session_ids: list[str]) -> str:
        """Merge multiple sessions into a single combined session.

        Creates a new session that combines metadata from the source sessions.
        Source sessions are archived.
        """
        merged_id = f"merged-{uuid.uuid4().hex[:8]}"
        merged_metadata: dict[str, Any] = {
            "source_sessions": list(session_ids),
            "merged_at": datetime.now(timezone.utc).isoformat(),
        }
        for sid in session_ids:
            if sid in self._sessions:
                merged_metadata.setdefault("collected_metadata", {})[sid] = self._sessions[sid].copy()
            self._session_states[sid] = SessionState.ARCHIVED
        self._session_states[merged_id] = SessionState.ACTIVE
        self._sessions[merged_id] = merged_metadata
        self._total_sessions_registered += 1
        logger.info("Merged %d sessions into %s", len(session_ids), merged_id)
        return merged_id

    # ── Session Search ────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens: list[str] = []
        for raw in re.split(r"[^a-zA-Z0-9]+", text.lower()):
            token = raw.strip()
            if not token or len(token) < 2 or token in _STOP_WORDS:
                continue
            tokens.append(token)
        return tokens

    def _remove_from_text_index(self, session_id: str) -> None:
        for token_set in self._text_index.values():
            token_set.discard(session_id)
        empty = [t for t, s in self._text_index.items() if not s]
        for t in empty:
            del self._text_index[t]

    def index_session_for_search(self, session_id: str, text: str) -> None:
        """Index session content for full-text search."""
        self._remove_from_text_index(session_id)
        for token in self._tokenize(text):
            self._text_index[token].add(session_id)

    def search_sessions(self, query: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Search sessions by full-text query with optional filters.

        Filters may include: date_from, date_to, agent_id, user_id, state,
        tags, sort_by (relevance/recency/duration), limit.
        """
        filters = filters or {}
        limit = filters.get("limit", 20)
        query_tokens = self._tokenize(query)
        candidate_ids: set[str] = set()
        if query_tokens:
            for token in query_tokens:
                candidate_ids.update(self._text_index.get(token, set()))
            if not candidate_ids:
                candidate_ids = set(self._session_states.keys())
        else:
            candidate_ids = set(self._session_states.keys())

        results: list[dict[str, Any]] = []
        for sid in candidate_ids:
            state = self._session_states.get(sid)
            if state is None:
                continue
            meta = self._sessions.get(sid, {})
            entry = {
                "session_id": sid, "state": state.value, "metadata": meta,
                "snapshot_count": len(self._snapshots.get(sid, [])),
                "branch_count": len(self._branches.get(sid, [])),
                "created_at": meta.get("created_at", ""),
                "message_count": meta.get("message_count", 0),
            }
            if not self._matches_filters(entry, filters):
                continue
            matches = sum(1 for t in query_tokens if t in self._text_index and sid in self._text_index[t])
            entry["relevance"] = round(matches / max(len(query_tokens), 1), 4) if query_tokens else 0.5
            results.append(entry)

        sort_by = filters.get("sort_by", "relevance")
        if sort_by == "relevance":
            results.sort(key=lambda r: r["relevance"], reverse=True)
        elif sort_by == "recency":
            results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        elif sort_by == "duration":
            results.sort(key=lambda r: r.get("message_count", 0), reverse=True)
        return results[:limit]

    @staticmethod
    def _matches_filters(entry: dict[str, Any], filters: dict[str, Any]) -> bool:
        state_filter = filters.get("state")
        if state_filter and entry.get("state") != state_filter:
            return False
        agent_id = filters.get("agent_id")
        if agent_id:
            agent_ids = entry.get("metadata", {}).get("agent_ids", [])
            if agent_id not in agent_ids:
                return False
        user_id = filters.get("user_id")
        if user_id and entry.get("metadata", {}).get("user_id") != user_id:
            return False
        tags_filter = filters.get("tags")
        if tags_filter:
            session_tags = set(entry.get("metadata", {}).get("tags", []))
            if not session_tags.intersection(tags_filter):
                return False
        date_from = filters.get("date_from")
        if date_from:
            created = entry.get("created_at", "")
            if created and created < date_from:
                return False
        date_to = filters.get("date_to")
        if date_to:
            created = entry.get("created_at", "")
            if created and created > date_to:
                return False
        return True

    # ── Session Templates ─────────────────────────────────────────

    def _seed_templates(self) -> None:
        """Create built-in session templates."""
        builtins = [
            SessionTemplate(name="Default Agent", system_prompt="You are a helpful AI assistant.",
                            tools=["web_search", "code_execution", "file_ops"], skills=["general"],
                            settings={"temperature": 0.7, "max_tokens": 4096}),
            SessionTemplate(name="Code Review", system_prompt="You are a code review specialist. Analyze code for bugs, style, and best practices.",
                            tools=["code_execution", "file_ops"], skills=["code_review", "security_scan"],
                            settings={"temperature": 0.3, "max_tokens": 8192}),
            SessionTemplate(name="Research Analyst", system_prompt="You are a research analyst. Conduct thorough research and synthesize findings.",
                            tools=["web_search", "file_ops"], skills=["research", "summarization"],
                            settings={"temperature": 0.5, "max_tokens": 8192}),
            SessionTemplate(name="Creative Writer", system_prompt="You are a creative writer. Generate engaging and original content.",
                            tools=["web_search", "file_ops"], skills=["writing", "brainstorming"],
                            settings={"temperature": 0.9, "max_tokens": 4096}),
            SessionTemplate(name="Data Analyst", system_prompt="You are a data analyst. Analyze data and generate insights.",
                            tools=["code_execution", "file_ops"], skills=["data_analysis", "visualization"],
                            settings={"temperature": 0.2, "max_tokens": 8192}),
        ]
        for tmpl in builtins:
            self._templates[tmpl.template_id] = tmpl
        logger.info("Seeded %d built-in session templates", len(builtins))

    def create_template(self, template_data: dict[str, Any]) -> SessionTemplate:
        """Create a custom session template.

        template_data keys: name, system_prompt, tools, skills, settings.
        """
        template = SessionTemplate(
            name=template_data.get("name", "Custom Template"),
            system_prompt=template_data.get("system_prompt", ""),
            tools=template_data.get("tools", []),
            skills=template_data.get("skills", []),
            settings=template_data.get("settings", {}),
        )
        self._templates[template.template_id] = template
        logger.info("Template created: %s (%s)", template.template_id, template.name)
        return template

    def get_template(self, template_id: str) -> SessionTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> list[SessionTemplate]:
        """List all session templates."""
        return list(self._templates.values())

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> SessionCommanderStats:
        """Get aggregate statistics for the session commander."""
        return SessionCommanderStats(
            total_sessions=len(self._session_states),
            active_groups=len(self._groups),
            batches_run=self._batches_run,
            total_snapshots=sum(len(s) for s in self._snapshots.values()),
            total_branches=sum(len(b) for b in self._branches.values()),
            total_templates=len(self._templates),
            active_sessions=sum(1 for s in self._session_states.values() if s == SessionState.ACTIVE),
            paused_sessions=sum(1 for s in self._session_states.values() if s == SessionState.PAUSED),
            archived_sessions=sum(1 for s in self._session_states.values() if s == SessionState.ARCHIVED),
        )

    # ── Reset ─────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all state in the session commander."""
        self._groups.clear()
        self._batches.clear()
        self._session_states.clear()
        self._sessions.clear()
        self._snapshots.clear()
        self._branches.clear()
        self._templates.clear()
        self._text_index.clear()
        self._batches_run = 0
        self._total_sessions_registered = 0
        self._seed_templates()
        logger.info("Session commander reset")


# ══════════════════════════════════════════════════════════════
# Global Instance
# ══════════════════════════════════════════════════════════════

session_commander = SessionCommander()