from __future__ import annotations
"""Buddy Agent Session Fork — branched conversation exploration for AI sessions.

This module implements a session forking system that lets conversations branch
like a version-control tree. Users can spawn parallel exploration paths, explore
alternative responses without losing the original thread, merge insights back
into a parent session, and maintain a full tree of conversational history.

Core capabilities:
- Fork a session using different strategies (shallow, deep, lazy, selective)
- Append messages with copy-on-write semantics for lazy forks
- Request and execute merges with multiple merge strategies
- Detect and resolve merge conflicts with configurable policies
- Inspect the full fork tree and gather statistics
"""

import copy
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ForkStrategy(Enum):
    """Strategy used when creating a fork of an existing session."""

    SHALLOW = "shallow"
    DEEP = "deep"
    LAZY = "lazy"
    SELECTIVE = "selective"


class ForkStatus(Enum):
    """Lifecycle status of a forked session node."""

    ACTIVE = "active"
    PAUSED = "paused"
    MERGED = "merged"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"


class MergeStrategy(Enum):
    """Strategy used when merging a fork back into a target session."""

    APPEND = "append"
    INTERLEAVE = "interleave"
    REPLACE = "replace"
    CHERRY_PICK = "cherry_pick"
    SQUASH = "squash"


class MergeConflictPolicy(Enum):
    """Policy describing how to resolve merge conflicts automatically."""

    PREFER_FORK = "prefer_fork"
    PREFER_ORIGINAL = "prefer_original"
    PREFER_NEWER = "prefer_newer"
    MANUAL_RESOLVE = "manual_resolve"
    FAIL_FAST = "fail_fast"


class SessionNodeRole(Enum):
    """Role describing a node's position within the fork tree."""

    ROOT = "root"
    FORK = "fork"
    MERGE_POINT = "merge_point"
    LEAF = "leaf"


class ForkRelation(Enum):
    """Relationship between two sessions in a fork tree."""

    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    MERGED_INTO = "merged_into"


@dataclass
class SessionMessage:
    """A single message stored within a session."""

    message_id: str
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    parent_message_id: str | None = None


@dataclass
class ForkPoint:
    """Record describing where and how a fork was created."""

    fork_point_id: str
    source_session_id: str
    source_message_index: int
    source_message_id: str | None
    created_at: float = field(default_factory=time.time)
    strategy: ForkStrategy = ForkStrategy.DEEP
    reason: str = ""
    forked_by: str = "user"


@dataclass
class SessionNode:
    """A node in the fork tree representing one session and its history."""

    session_id: str
    root_session_id: str = ""
    parent_session_id: str | None = None
    role: SessionNodeRole = SessionNodeRole.ROOT
    status: ForkStatus = ForkStatus.ACTIVE
    messages: list[SessionMessage] = field(default_factory=list)
    fork_point: ForkPoint | None = None
    children: list[str] = field(default_factory=list)
    depth: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    message_count: int = 0
    total_tokens: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MergeRequest:
    """A request to merge a fork back into a target session."""

    merge_id: str
    fork_session_id: str
    target_session_id: str
    strategy: MergeStrategy
    conflict_policy: MergeConflictPolicy
    message_range: tuple[int, int] | None = None
    cherry_pick_ids: list[str] = field(default_factory=list)
    squash_summary: str | None = None
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    merged_message_ids: list[str] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MergeConflict:
    """A conflict detected while executing a merge."""

    conflict_id: str
    merge_id: str
    message_index: int
    fork_message: SessionMessage | None
    original_message: SessionMessage | None
    resolution: str | None = None
    resolved_by: str | None = None


@dataclass
class ForkTree:
    """Overview of an entire fork tree rooted at a single session."""

    root_session_id: str
    total_sessions: int
    total_messages: int
    max_depth: int
    active_forks: int
    leaf_sessions: list[str] = field(default_factory=list)


class AgentSessionFork:
    """Manages a registry of sessions and their fork/merge lifecycle.

    The registry tracks every session node, pending and completed merge
    requests, and unresolved conflicts. It enforces capacity limits and
    validates all fork and merge operations.
    """

    MAX_SESSIONS = 10000
    MAX_MESSAGES_PER_SESSION = 100000
    MAX_FORK_DEPTH = 50
    MAX_MERGE_REQUESTS = 5000

    def __init__(self) -> None:
        """Initialize empty registries for sessions, merges, and conflicts."""
        self._sessions: dict[str, SessionNode] = {}
        self._merge_requests: dict[str, MergeRequest] = {}
        self._conflicts: dict[str, MergeConflict] = {}
        # Tracks lazy forks that have already been materialized via copy-on-write.
        self._lazy_materialized: set[str] = set()

    def create_root_session(
        self,
        session_id: str,
        messages: list[SessionMessage] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionNode:
        """Create a new root session that anchors a fork tree.

        Raises:
            ValueError: if session_id is empty or already exists, or if the
                session capacity has been reached.
        """
        if not session_id:
            raise ValueError("session_id must be a non-empty string")
        if session_id in self._sessions:
            raise ValueError(f"session_id '{session_id}' already exists")
        if len(self._sessions) >= self.MAX_SESSIONS:
            raise ValueError("maximum number of sessions reached")

        node = SessionNode(
            session_id=session_id,
            parent_session_id=None,
            root_session_id=session_id,
            role=SessionNodeRole.ROOT,
            status=ForkStatus.ACTIVE,
            messages=list(messages) if messages else [],
            tags=list(tags) if tags else [],
            metadata=dict(metadata) if metadata else {},
        )
        node.message_count = len(node.messages)
        node.total_tokens = sum(m.tokens for m in node.messages)
        self._sessions[session_id] = node
        return node

    def fork_session(
        self,
        source_session_id: str,
        new_session_id: str,
        strategy: ForkStrategy = ForkStrategy.DEEP,
        source_message_index: int | None = None,
        message_range: tuple[int, int] | None = None,
        reason: str = "",
        forked_by: str = "user",
        tags: list[str] | None = None,
    ) -> SessionNode:
        """Create a fork of an existing session.

        The copy behavior depends on ``strategy``:

        - SHALLOW: copy only the last 10 messages by default.
        - DEEP: full deepcopy of all messages and state.
        - LAZY: share the message list reference until a write triggers
          copy-on-write (modifications are tracked separately).
        - SELECTIVE: copy only the messages within ``message_range``.

        Raises:
            ValueError: if the source session is missing, the new id exists,
                the fork depth exceeds MAX_FORK_DEPTH, or SELECTIVE is used
                without a message_range.
        """
        source = self._sessions.get(source_session_id)
        if source is None:
            raise ValueError(f"source session '{source_session_id}' not found")
        if not new_session_id:
            raise ValueError("new_session_id must be a non-empty string")
        if new_session_id in self._sessions:
            raise ValueError(f"session_id '{new_session_id}' already exists")
        if len(self._sessions) >= self.MAX_SESSIONS:
            raise ValueError("maximum number of sessions reached")

        new_depth = source.depth + 1
        if new_depth > self.MAX_FORK_DEPTH:
            raise ValueError(
                f"fork depth {new_depth} exceeds MAX_FORK_DEPTH of {self.MAX_FORK_DEPTH}"
            )

        # Determine the source message index to record on the fork point.
        if source_message_index is None:
            recorded_index = max(len(source.messages) - 1, 0)
        else:
            recorded_index = source_message_index

        source_message_id: str | None = None
        if 0 <= recorded_index < len(source.messages):
            source_message_id = source.messages[recorded_index].message_id

        # Build the forked message list according to the strategy.
        copied_messages: list[SessionMessage]
        if strategy == ForkStrategy.DEEP:
            copied_messages = copy.deepcopy(source.messages)
        elif strategy == ForkStrategy.SHALLOW:
            copied_messages = copy.deepcopy(source.messages[-10:])
        elif strategy == ForkStrategy.LAZY:
            # Share the reference until a write occurs.
            copied_messages = source.messages
        elif strategy == ForkStrategy.SELECTIVE:
            if message_range is None:
                raise ValueError("SELECTIVE fork requires a message_range")
            start, end = message_range
            copied_messages = copy.deepcopy(source.messages[start:end])
        else:  # pragma: no cover - defensive default
            copied_messages = copy.deepcopy(source.messages)

        fork_point = ForkPoint(
            fork_point_id=str(uuid.uuid4()),
            source_session_id=source_session_id,
            source_message_index=recorded_index,
            source_message_id=source_message_id,
            strategy=strategy,
            reason=reason,
            forked_by=forked_by,
        )

        node = SessionNode(
            session_id=new_session_id,
            parent_session_id=source_session_id,
            root_session_id=source.root_session_id,
            role=SessionNodeRole.FORK,
            status=ForkStatus.ACTIVE,
            messages=copied_messages,
            fork_point=fork_point,
            depth=new_depth,
            tags=list(tags) if tags else [],
        )
        node.message_count = len(node.messages)
        node.total_tokens = sum(m.tokens for m in node.messages)

        # Link the new fork as a child of the source session.
        source.children.append(new_session_id)
        source.updated_at = time.time()

        self._sessions[new_session_id] = node
        return node

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        tokens: int = 0,
        tool_calls: list[dict[str, Any]] | None = None,
        parent_message_id: str | None = None,
    ) -> SessionMessage:
        """Append a new message to an active session.

        For LAZY forks, copy-on-write is performed: the shared message list is
        copied before the new message is appended so the parent is unaffected.

        Raises:
            ValueError: if the session is not found, is not ACTIVE, or has
                reached the per-session message capacity.
        """
        node = self._sessions.get(session_id)
        if node is None:
            raise ValueError(f"session '{session_id}' not found")
        if node.status != ForkStatus.ACTIVE:
            raise ValueError(
                f"session '{session_id}' is not active (status={node.status.value})"
            )
        if len(node.messages) >= self.MAX_MESSAGES_PER_SESSION:
            raise ValueError("maximum messages per session reached")

        # Copy-on-write for lazy forks that have not yet been materialized.
        if (
            node.fork_point is not None
            and node.fork_point.strategy == ForkStrategy.LAZY
            and session_id not in self._lazy_materialized
        ):
            node.messages = list(node.messages)
            self._lazy_materialized.add(session_id)

        message = SessionMessage(
            message_id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=dict(metadata) if metadata else {},
            tokens=tokens,
            tool_calls=list(tool_calls) if tool_calls else [],
            parent_message_id=parent_message_id,
        )
        node.messages.append(message)
        node.message_count = len(node.messages)
        node.total_tokens += tokens
        node.updated_at = time.time()
        return message

    def get_session(self, session_id: str) -> SessionNode | None:
        """Return the session node for ``session_id`` or None if not found."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        status: ForkStatus | None = None,
        parent: str | None = None,
        root: str | None = None,
    ) -> list[SessionNode]:
        """List sessions, optionally filtered by status, parent, or root."""
        results: list[SessionNode] = []
        for node in self._sessions.values():
            if status is not None and node.status != status:
                continue
            if parent is not None and node.parent_session_id != parent:
                continue
            if root is not None and node.root_session_id != root:
                continue
            results.append(node)
        return results

    def get_children(self, session_id: str) -> list[SessionNode]:
        """Return the direct child sessions of ``session_id``."""
        node = self._sessions.get(session_id)
        if node is None:
            return []
        children: list[SessionNode] = []
        for child_id in node.children:
            child = self._sessions.get(child_id)
            if child is not None:
                children.append(child)
        return children

    def get_path_to_root(self, session_id: str) -> list[SessionNode]:
        """Return the path from ``session_id`` up to the root, inclusive."""
        path: list[SessionNode] = []
        current = self._sessions.get(session_id)
        visited: set[str] = set()
        while current is not None and current.session_id not in visited:
            visited.add(current.session_id)
            path.append(current)
            if current.parent_session_id is None:
                break
            current = self._sessions.get(current.parent_session_id)
        return path

    def get_fork_tree(self, root_session_id: str) -> ForkTree | None:
        """Build an overview of the entire fork tree under ``root_session_id``."""
        root = self._sessions.get(root_session_id)
        if root is None:
            return None

        total_sessions = 0
        total_messages = 0
        max_depth = 0
        active_forks = 0
        leaf_sessions: list[str] = []

        for node in self._sessions.values():
            if node.root_session_id != root_session_id:
                continue
            total_sessions += 1
            total_messages += node.message_count
            if node.depth > max_depth:
                max_depth = node.depth
            if node.role == SessionNodeRole.FORK and node.status == ForkStatus.ACTIVE:
                active_forks += 1
            if not node.children:
                leaf_sessions.append(node.session_id)

        return ForkTree(
            root_session_id=root_session_id,
            total_sessions=total_sessions,
            total_messages=total_messages,
            max_depth=max_depth,
            active_forks=active_forks,
            leaf_sessions=leaf_sessions,
        )

    def request_merge(
        self,
        fork_session_id: str,
        target_session_id: str,
        strategy: MergeStrategy = MergeStrategy.APPEND,
        conflict_policy: MergeConflictPolicy = MergeConflictPolicy.PREFER_FORK,
        message_range: tuple[int, int] | None = None,
        cherry_pick_ids: list[str] | None = None,
        squash_summary: str | None = None,
    ) -> MergeRequest:
        """Create a pending merge request from a fork into a target session.

        Raises:
            ValueError: if either session is missing, the sessions are the
                same, or the merge request capacity has been reached.
        """
        if fork_session_id == target_session_id:
            raise ValueError("fork_session_id and target_session_id must differ")
        if fork_session_id not in self._sessions:
            raise ValueError(f"fork session '{fork_session_id}' not found")
        if target_session_id not in self._sessions:
            raise ValueError(f"target session '{target_session_id}' not found")
        if len(self._merge_requests) >= self.MAX_MERGE_REQUESTS:
            raise ValueError("maximum number of merge requests reached")

        request = MergeRequest(
            merge_id=str(uuid.uuid4()),
            fork_session_id=fork_session_id,
            target_session_id=target_session_id,
            strategy=strategy,
            conflict_policy=conflict_policy,
            message_range=message_range,
            cherry_pick_ids=list(cherry_pick_ids) if cherry_pick_ids else [],
            squash_summary=squash_summary,
            status="pending",
        )
        self._merge_requests[request.merge_id] = request
        return request

    def execute_merge(self, merge_id: str) -> MergeRequest | None:
        """Execute a pending merge request according to its strategy.

        Supported strategies: APPEND, INTERLEAVE, REPLACE, CHERRY_PICK, SQUASH.
        Conflicts are detected for REPLACE operations and resolved using the
        request's conflict policy. On success the fork session is marked
        MERGED and the request is marked completed.

        Raises:
            ValueError: if the request is not pending.
        """
        request = self._merge_requests.get(merge_id)
        if request is None:
            return None
        if request.status != "pending":
            raise ValueError(
                f"merge request '{merge_id}' is not pending (status={request.status})"
            )

        fork = self._sessions.get(request.fork_session_id)
        target = self._sessions.get(request.target_session_id)
        if fork is None or target is None:
            request.status = "failed"
            return request

        strategy = request.strategy
        policy = request.conflict_policy

        # Resolve the fork messages that participate in the merge.
        if request.message_range is not None:
            start, end = request.message_range
            fork_msgs = list(fork.messages[start:end])
        else:
            fork_msgs = list(fork.messages)

        merged_ids: list[str] = []

        if strategy == MergeStrategy.APPEND:
            for m in fork_msgs:
                new_msg = copy.deepcopy(m)
                target.messages.append(new_msg)
                merged_ids.append(new_msg.message_id)

        elif strategy == MergeStrategy.INTERLEAVE:
            combined = list(target.messages) + [copy.deepcopy(m) for m in fork_msgs]
            combined.sort(key=lambda m: m.timestamp)
            target.messages = combined
            merged_ids = [m.message_id for m in fork_msgs]

        elif strategy == MergeStrategy.REPLACE:
            if request.message_range is None:
                request.status = "failed"
                return request
            start, end = request.message_range
            existing = list(target.messages[start:end])

            # Detect conflicts for the indices being replaced.
            for i, orig in enumerate(existing):
                conflict = MergeConflict(
                    conflict_id=str(uuid.uuid4()),
                    merge_id=merge_id,
                    message_index=start + i,
                    fork_message=fork_msgs[i] if i < len(fork_msgs) else None,
                    original_message=orig,
                )
                self._conflicts[conflict.conflict_id] = conflict
                request.conflicts.append(
                    {
                        "conflict_id": conflict.conflict_id,
                        "message_index": start + i,
                        "original_message_id": orig.message_id if orig else None,
                        "fork_message_id": (
                            fork_msgs[i].message_id if i < len(fork_msgs) else None
                        ),
                    }
                )

            if policy == MergeConflictPolicy.FAIL_FAST:
                request.status = "failed"
                return request
            if policy == MergeConflictPolicy.MANUAL_RESOLVE:
                request.status = "conflict"
                return request
            if policy == MergeConflictPolicy.PREFER_ORIGINAL:
                # Keep the original messages untouched in the replaced range.
                pass
            elif policy == MergeConflictPolicy.PREFER_FORK:
                new_msgs = [copy.deepcopy(m) for m in fork_msgs]
                target.messages[start:end] = new_msgs
                merged_ids = [m.message_id for m in new_msgs]
            elif policy == MergeConflictPolicy.PREFER_NEWER:
                result: list[SessionMessage] = []
                max_len = max(len(existing), len(fork_msgs))
                for i in range(max_len):
                    orig = existing[i] if i < len(existing) else None
                    fork_m = fork_msgs[i] if i < len(fork_msgs) else None
                    if orig is None and fork_m is not None:
                        result.append(copy.deepcopy(fork_m))
                    elif fork_m is None and orig is not None:
                        result.append(orig)
                    elif orig is not None and fork_m is not None:
                        if fork_m.timestamp >= orig.timestamp:
                            result.append(copy.deepcopy(fork_m))
                        else:
                            result.append(orig)
                target.messages[start:end] = result
                merged_ids = [m.message_id for m in result]

        elif strategy == MergeStrategy.CHERRY_PICK:
            pick_set = set(request.cherry_pick_ids)
            for m in fork_msgs:
                if m.message_id in pick_set:
                    new_msg = copy.deepcopy(m)
                    target.messages.append(new_msg)
                    merged_ids.append(new_msg.message_id)

        elif strategy == MergeStrategy.SQUASH:
            summary = request.squash_summary
            if not summary:
                summary = " ".join(m.content for m in fork_msgs if m.role == "assistant")
            squash_msg = SessionMessage(
                message_id=str(uuid.uuid4()),
                role="assistant",
                content=summary,
                timestamp=time.time(),
                metadata={
                    "squashed_from": [m.message_id for m in fork_msgs],
                    "merge_id": merge_id,
                },
                tokens=sum(m.tokens for m in fork_msgs),
            )
            target.messages.append(squash_msg)
            merged_ids.append(squash_msg.message_id)

        # Refresh target aggregates.
        target.message_count = len(target.messages)
        target.total_tokens = sum(m.tokens for m in target.messages)
        target.updated_at = time.time()
        target.role = SessionNodeRole.MERGE_POINT

        request.merged_message_ids = merged_ids
        request.status = "completed"
        request.resolved_at = time.time()

        # Mark the fork session as merged.
        fork.status = ForkStatus.MERGED
        fork.updated_at = time.time()
        return request

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        resolved_by: str = "user",
    ) -> MergeConflict | None:
        """Manually resolve a previously detected merge conflict."""
        conflict = self._conflicts.get(conflict_id)
        if conflict is None:
            return None
        conflict.resolution = resolution
        conflict.resolved_by = resolved_by
        return conflict

    def abandon_fork(self, session_id: str) -> SessionNode | None:
        """Mark a fork as ABANDONED. Returns the node or None if not found."""
        node = self._sessions.get(session_id)
        if node is None:
            return None
        node.status = ForkStatus.ABANDONED
        node.updated_at = time.time()
        return node

    def archive_session(self, session_id: str) -> SessionNode | None:
        """Mark a session as ARCHIVED. Returns the node or None if not found."""
        node = self._sessions.get(session_id)
        if node is None:
            return None
        node.status = ForkStatus.ARCHIVED
        node.updated_at = time.time()
        return node

    def get_merge_request(self, merge_id: str) -> MergeRequest | None:
        """Return the merge request for ``merge_id`` or None if not found."""
        return self._merge_requests.get(merge_id)

    def list_merge_requests(
        self,
        status: str | None = None,
        fork_session: str | None = None,
        target_session: str | None = None,
    ) -> list[MergeRequest]:
        """List merge requests, optionally filtered by status or session."""
        results: list[MergeRequest] = []
        for request in self._merge_requests.values():
            if status is not None and request.status != status:
                continue
            if fork_session is not None and request.fork_session_id != fork_session:
                continue
            if target_session is not None and request.target_session_id != target_session:
                continue
            results.append(request)
        return results

    def get_session_stats(self, session_id: str) -> dict[str, Any]:
        """Return per-session statistics for ``session_id``."""
        node = self._sessions.get(session_id)
        if node is None:
            return {}
        return {
            "message_count": node.message_count,
            "total_tokens": node.total_tokens,
            "depth": node.depth,
            "children_count": len(node.children),
            "status": node.status.value,
            "age_seconds": time.time() - node.created_at,
        }

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all sessions and merge requests."""
        total_sessions = len(self._sessions)
        total_messages = sum(n.message_count for n in self._sessions.values())
        total_merges = sum(
            1 for r in self._merge_requests.values() if r.status == "completed"
        )
        active_forks = sum(
            1
            for n in self._sessions.values()
            if n.role == SessionNodeRole.FORK and n.status == ForkStatus.ACTIVE
        )
        depths = [n.depth for n in self._sessions.values()]
        avg_depth = sum(depths) / total_sessions if total_sessions else 0.0

        strategy_distribution: dict[str, int] = {}
        for n in self._sessions.values():
            if n.fork_point is not None:
                key = n.fork_point.strategy.value
                strategy_distribution[key] = strategy_distribution.get(key, 0) + 1

        status_distribution: dict[str, int] = {}
        for n in self._sessions.values():
            key = n.status.value
            status_distribution[key] = status_distribution.get(key, 0) + 1

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_merges": total_merges,
            "active_forks": active_forks,
            "avg_depth": avg_depth,
            "strategy_distribution": strategy_distribution,
            "status_distribution": status_distribution,
        }

    def reset(self) -> None:
        """Clear all sessions, merge requests, conflicts, and lazy tracking."""
        self._sessions.clear()
        self._merge_requests.clear()
        self._conflicts.clear()
        self._lazy_materialized.clear()


_session_fork: AgentSessionFork | None = None


def get_session_fork() -> AgentSessionFork:
    """Return the module-level singleton AgentSessionFork instance."""
    global _session_fork
    if _session_fork is None:
        _session_fork = AgentSessionFork()
    return _session_fork


def reset_session_fork() -> None:
    """Reset and discard the module-level singleton AgentSessionFork instance."""
    global _session_fork
    if _session_fork is not None:
        _session_fork.reset()
    _session_fork = None
