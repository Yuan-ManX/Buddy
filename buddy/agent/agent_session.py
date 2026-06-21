"""Buddy Multi-Agent Session Manager — real-time collaboration and shared context

Provides a collaborative session layer where multiple agents can:
- Share a live session with real-time message synchronization
- Collaborate on tasks with role-based participation
- Maintain shared context, artifacts, and conversation history
- Support session forking, handoff, and multi-device continuity
"""
from __future__ import annotations
import json
import logging
import uuid
import time
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from statistics import mean
from typing import Any, Callable

logger = logging.getLogger("buddy.agent_session")


class SessionRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    WORKER = "worker"
    REVIEWER = "reviewer"
    OBSERVER = "observer"


class SessionState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FORKED = "forked"


class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class VoteStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"


# Role weights for collaborative voting
_ROLE_WEIGHTS: dict[SessionRole, float] = {
    SessionRole.ORCHESTRATOR: 3.0,
    SessionRole.REVIEWER: 2.0,
    SessionRole.WORKER: 1.0,
    SessionRole.OBSERVER: 0.5,
}


@dataclass
class SessionMessage:
    """A message within a collaborative session."""
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    role: MessageRole = MessageRole.AGENT
    sender_id: str = ""
    sender_name: str = ""
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_message_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content[:500],
            "timestamp": self.timestamp,
            "parent_message_id": self.parent_message_id,
        }


@dataclass
class SessionArtifact:
    """A shared artifact produced during a session."""
    artifact_id: str = field(default_factory=lambda: f"art-{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    name: str = ""
    artifact_type: str = "file"
    content: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "artifact_type": self.artifact_type,
            "created_by": self.created_by,
            "version": self.version,
            "tags": self.tags,
        }


@dataclass
class SessionParticipant:
    """A participant in a collaborative session."""
    agent_id: str
    name: str = ""
    role: SessionRole = SessionRole.WORKER
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True
    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "joined_at": self.joined_at,
            "is_active": self.is_active,
            "capabilities": self.capabilities,
        }


@dataclass
class DelegatedTask:
    """A task delegated to a session participant with role-based routing."""
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    delegator_id: str = ""
    description: str = ""
    target_role: SessionRole = SessionRole.WORKER
    target_agent_id: str | None = None
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    result: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "delegator_id": self.delegator_id,
            "description": self.description,
            "target_role": self.target_role.value,
            "target_agent_id": self.target_agent_id,
            "priority": self.priority,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": self.result,
        }


@dataclass
class SessionVote:
    """A collaborative vote within a session."""
    vote_id: str = field(default_factory=lambda: f"vote-{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    topic: str = ""
    description: str = ""
    options: list[str] = field(default_factory=list)
    initiator_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: VoteStatus = VoteStatus.OPEN
    votes: dict[str, dict[str, Any]] = field(default_factory=dict)  # voter_id -> {option, weight, timestamp}
    resolved_at: str | None = None
    winning_option: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "vote_id": self.vote_id,
            "session_id": self.session_id,
            "topic": self.topic,
            "description": self.description,
            "options": self.options,
            "initiator_id": self.initiator_id,
            "status": self.status.value,
            "vote_count": len(self.votes),
            "created_at": self.created_at,
            "winning_option": self.winning_option,
        }


@dataclass
class SessionTemplate:
    """A reusable session template for common collaboration patterns."""
    template_id: str = field(default_factory=lambda: f"tmpl-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    pattern: str = ""  # e.g. "code_review", "brainstorming", "incident_response"
    required_roles: list[SessionRole] = field(default_factory=list)
    suggested_participants: int = 2
    tags: list[str] = field(default_factory=list)
    default_context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "pattern": self.pattern,
            "required_roles": [r.value for r in self.required_roles],
            "suggested_participants": self.suggested_participants,
            "tags": self.tags,
        }


@dataclass
class CollaborativeSession:
    """A collaborative session with multiple agents."""
    session_id: str = field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    state: SessionState = SessionState.ACTIVE
    participants: dict[str, SessionParticipant] = field(default_factory=dict)
    messages: list[SessionMessage] = field(default_factory=list)
    artifacts: dict[str, SessionArtifact] = field(default_factory=dict)
    shared_context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    parent_session_id: str | None = None
    tags: list[str] = field(default_factory=list)
    message_count: int = 0
    artifact_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "participants": [p.to_dict() for p in self.participants.values()],
            "participant_count": len(self.participants),
            "message_count": self.message_count,
            "artifact_count": self.artifact_count,
            "created_at": self.created_at,
            "tags": self.tags,
        }


class AgentSessionManager:
    """Manages collaborative multi-agent sessions.

    Provides real-time session management with message synchronization,
    shared context, artifact management, and session lifecycle control.
    Supports forking, handoff, and multi-device session continuity.
    """

    MAX_MESSAGES_PER_SESSION = 1000
    MAX_ARTIFACTS_PER_SESSION = 500
    MAX_TASKS_PER_SESSION = 200

    def __init__(self):
        self._sessions: dict[str, CollaborativeSession] = {}
        self._message_subscribers: dict[str, list[Callable]] = {}
        self._total_sessions_created: int = 0
        self._total_messages_sent: int = 0

        # Task delegation storage
        self._tasks: dict[str, dict[str, DelegatedTask]] = defaultdict(dict)  # session_id -> {task_id -> task}

        # Voting storage
        self._votes: dict[str, dict[str, SessionVote]] = defaultdict(dict)  # session_id -> {vote_id -> vote}

        # Session templates
        self._templates: dict[str, SessionTemplate] = {}

        # Participant activity tracking for health checks
        self._participant_activity: dict[str, dict[str, str]] = defaultdict(dict)  # session_id -> {agent_id -> last_active_iso}

        # Handoff log
        self._handoff_log: dict[str, list[dict[str, Any]]] = defaultdict(list)  # session_id -> [handoff records]

        # Seed built-in templates
        self._seed_templates()

    # ── Session Lifecycle ───────────────────────────────────────────

    def create_session(
        self,
        name: str,
        description: str = "",
        orchestrator_id: str = "",
        tags: list[str] | None = None,
    ) -> CollaborativeSession:
        """Create a new collaborative session."""
        session = CollaborativeSession(
            name=name,
            description=description,
            tags=tags or [],
        )

        if orchestrator_id:
            session.participants[orchestrator_id] = SessionParticipant(
                agent_id=orchestrator_id,
                name="Orchestrator",
                role=SessionRole.ORCHESTRATOR,
            )

        self._sessions[session.session_id] = session
        self._total_sessions_created += 1
        logger.info(f"Session created: {session.session_id} ({name})")
        return session

    def add_participant(
        self,
        session_id: str,
        agent_id: str,
        name: str = "",
        role: SessionRole = SessionRole.WORKER,
        capabilities: list[str] | None = None,
    ) -> SessionParticipant | None:
        """Add a participant to a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        participant = SessionParticipant(
            agent_id=agent_id,
            name=name,
            role=role,
            capabilities=capabilities or [],
        )
        session.participants[agent_id] = participant
        session.updated_at = datetime.now(timezone.utc).isoformat()
        self._record_activity(session_id, agent_id)
        return participant

    def remove_participant(self, session_id: str, agent_id: str) -> bool:
        """Remove a participant from a session."""
        session = self._sessions.get(session_id)
        if not session or agent_id not in session.participants:
            return False
        session.participants[agent_id].is_active = False
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def set_leader(self, session_id: str, agent_id: str) -> bool:
        """Set a participant as the session leader/orchestrator."""
        session = self._sessions.get(session_id)
        if not session or agent_id not in session.participants:
            return False
        # Demote current orchestrator
        for p in session.participants.values():
            if p.role == SessionRole.ORCHESTRATOR:
                p.role = SessionRole.WORKER
        session.participants[agent_id].role = SessionRole.ORCHESTRATOR
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def pause_session(self, session_id: str) -> bool:
        """Pause a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.state = SessionState.PAUSED
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.state = SessionState.ACTIVE
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def complete_session(self, session_id: str) -> bool:
        """Mark a session as completed."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.state = SessionState.COMPLETED
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def fork_session(
        self, session_id: str, new_name: str,
    ) -> CollaborativeSession | None:
        """Fork a session for parallel exploration."""
        original = self._sessions.get(session_id)
        if not original:
            return None

        forked = CollaborativeSession(
            name=new_name,
            description=f"Forked from: {original.name}",
            parent_session_id=session_id,
            participants={
                pid: SessionParticipant(
                    agent_id=p.agent_id,
                    name=p.name,
                    role=p.role,
                    capabilities=p.capabilities.copy(),
                )
                for pid, p in original.participants.items()
            },
            shared_context=original.shared_context.copy(),
        )

        original.state = SessionState.FORKED
        self._sessions[forked.session_id] = forked
        self._total_sessions_created += 1
        return forked

    # ── Messaging ───────────────────────────────────────────────────

    def send_message(
        self,
        session_id: str,
        sender_id: str,
        content: str,
        role: MessageRole = MessageRole.AGENT,
        parent_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionMessage | None:
        """Send a message in a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        if session.state != SessionState.ACTIVE:
            return None

        sender_name = sender_id
        if sender_id in session.participants:
            sender_name = session.participants[sender_id].name or sender_id

        message = SessionMessage(
            session_id=session_id,
            role=role,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            parent_message_id=parent_message_id,
            metadata=metadata or {},
        )

        session.messages.append(message)
        session.message_count += 1
        session.updated_at = datetime.now(timezone.utc).isoformat()
        self._total_messages_sent += 1

        # Track participant activity
        self._record_activity(session_id, sender_id)

        # Prune old messages if over limit
        if len(session.messages) > self.MAX_MESSAGES_PER_SESSION:
            session.messages = session.messages[-self.MAX_MESSAGES_PER_SESSION:]

        # Notify subscribers
        self._notify_subscribers(session_id, message)

        return message

    def get_messages(
        self, session_id: str, limit: int = 100, before: str | None = None,
    ) -> list[SessionMessage]:
        """Get messages from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        messages = session.messages
        if before:
            messages = [m for m in messages if m.timestamp < before]
        return messages[-limit:]

    def subscribe(self, session_id: str, callback: Callable) -> None:
        """Subscribe to real-time message updates for a session."""
        if session_id not in self._message_subscribers:
            self._message_subscribers[session_id] = []
        self._message_subscribers[session_id].append(callback)

    def unsubscribe(self, session_id: str, callback: Callable) -> None:
        """Unsubscribe from session updates."""
        if session_id in self._message_subscribers:
            self._message_subscribers[session_id] = [
                cb for cb in self._message_subscribers[session_id] if cb != callback
            ]

    def _notify_subscribers(
        self, session_id: str, message: SessionMessage,
    ) -> None:
        """Notify all subscribers of a new message."""
        if session_id in self._message_subscribers:
            for callback in self._message_subscribers[session_id]:
                try:
                    callback(message.to_dict())
                except Exception as e:
                    logger.warning(f"Subscriber notification failed: {e}")

    # ── Artifacts ───────────────────────────────────────────────────

    def create_artifact(
        self,
        session_id: str,
        name: str,
        content: str,
        artifact_type: str = "file",
        created_by: str = "",
        tags: list[str] | None = None,
    ) -> SessionArtifact | None:
        """Create a shared artifact in a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        artifact = SessionArtifact(
            session_id=session_id,
            name=name,
            artifact_type=artifact_type,
            content=content,
            created_by=created_by,
            tags=tags or [],
        )
        session.artifacts[artifact.artifact_id] = artifact
        session.artifact_count += 1
        session.updated_at = datetime.now(timezone.utc).isoformat()

        # Prune old artifacts if over limit
        if len(session.artifacts) > self.MAX_ARTIFACTS_PER_SESSION:
            oldest = sorted(
                session.artifacts.items(),
                key=lambda x: x[1].created_at,
            )[: len(session.artifacts) - self.MAX_ARTIFACTS_PER_SESSION]
            for aid, _ in oldest:
                del session.artifacts[aid]

        return artifact

    def update_artifact(
        self, session_id: str, artifact_id: str, content: str,
    ) -> SessionArtifact | None:
        """Update an existing artifact."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        artifact = session.artifacts.get(artifact_id)
        if not artifact:
            return None
        artifact.content = content
        artifact.version += 1
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return artifact

    def get_artifacts(
        self, session_id: str, artifact_type: str | None = None,
    ) -> list[SessionArtifact]:
        """Get artifacts from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        artifacts = list(session.artifacts.values())
        if artifact_type:
            artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
        return sorted(artifacts, key=lambda a: a.created_at, reverse=True)

    # ── Shared Context ──────────────────────────────────────────────

    def set_context(
        self, session_id: str, key: str, value: Any,
    ) -> bool:
        """Set a shared context value."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.shared_context[key] = value
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def get_context(
        self, session_id: str, key: str | None = None,
    ) -> Any:
        """Get shared context values."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        if key:
            return session.shared_context.get(key)
        return session.shared_context.copy()

    # ── Query Methods ───────────────────────────────────────────────

    def get_session(self, session_id: str) -> CollaborativeSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        state: SessionState | None = None,
        agent_id: str | None = None,
    ) -> list[CollaborativeSession]:
        """List sessions, optionally filtered."""
        sessions = list(self._sessions.values())
        if state:
            sessions = [s for s in sessions if s.state == state]
        if agent_id:
            sessions = [
                s for s in sessions
                if agent_id in s.participants
            ]
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

    def get_sessions_by_agent(self, agent_id: str) -> list[CollaborativeSession]:
        """Get all sessions a specific agent participates in."""
        return [
            s for s in self._sessions.values()
            if agent_id in s.participants
        ]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data."""
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        self._message_subscribers.pop(session_id, None)
        self._tasks.pop(session_id, None)
        self._votes.pop(session_id, None)
        self._participant_activity.pop(session_id, None)
        self._handoff_log.pop(session_id, None)
        return True

    # ── Stats ───────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get session manager statistics."""
        active = sum(
            1 for s in self._sessions.values()
            if s.state == SessionState.ACTIVE
        )
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active,
            "total_sessions_created": self._total_sessions_created,
            "total_messages_sent": self._total_messages_sent,
            "total_participants": sum(
                len(s.participants) for s in self._sessions.values()
            ),
            "total_artifacts": sum(
                s.artifact_count for s in self._sessions.values()
            ),
            "states": {
                state.value: sum(
                    1 for s in self._sessions.values()
                    if s.state == state
                )
                for state in SessionState
            },
        }

    # ═══════════════════════════════════════════════════════════════════
    # ── Task Delegation ───────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════

    def delegate_task(
        self,
        session_id: str,
        delegator_id: str,
        description: str,
        target_role: SessionRole = SessionRole.WORKER,
        target_agent_id: str | None = None,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> DelegatedTask | None:
        """Delegate a task to session participants with role-based routing.

        Tasks are routed based on the target_role. If target_agent_id is specified,
        the task is assigned directly to that agent. Otherwise, the first available
        participant matching the target_role is assigned. If no matching participant
        is found, the task remains in pending status.

        Args:
            session_id: The session to delegate within.
            delegator_id: The agent delegating the task.
            description: A description of the task to perform.
            target_role: The role required to execute the task.
            target_agent_id: A specific agent to assign the task to (optional).
            priority: Task priority (higher = more urgent).
            metadata: Additional task metadata.

        Returns:
            The created DelegatedTask, or None if the session is invalid.
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"delegate_task: session {session_id} not found")
            return None

        if session.state != SessionState.ACTIVE:
            logger.warning(f"delegate_task: session {session_id} is not active")
            return None

        task = DelegatedTask(
            session_id=session_id,
            delegator_id=delegator_id,
            description=description,
            target_role=target_role,
            target_agent_id=target_agent_id,
            priority=priority,
            metadata=metadata or {},
        )

        # Route the task to a matching participant
        assigned = self._route_task(session, task)
        if assigned:
            task.status = TaskStatus.ASSIGNED
            task.assigned_to = assigned
            logger.info(
                f"Task {task.task_id} delegated to {assigned} "
                f"(role={target_role.value}) in session {session_id}"
            )
        else:
            logger.info(
                f"Task {task.task_id} created but no matching participant "
                f"for role={target_role.value} in session {session_id}"
            )

        self._tasks[session_id][task.task_id] = task

        # Prune old tasks if over limit
        if len(self._tasks[session_id]) > self.MAX_TASKS_PER_SESSION:
            oldest = sorted(
                self._tasks[session_id].items(),
                key=lambda x: x[1].created_at,
            )[: len(self._tasks[session_id]) - self.MAX_TASKS_PER_SESSION]
            for tid, _ in oldest:
                del self._tasks[session_id][tid]

        session.updated_at = datetime.now(timezone.utc).isoformat()
        return task

    def _route_task(
        self, session: CollaborativeSession, task: DelegatedTask,
    ) -> str | None:
        """Route a task to the best available participant by role."""
        if task.target_agent_id and task.target_agent_id in session.participants:
            participant = session.participants[task.target_agent_id]
            if participant.is_active:
                return task.target_agent_id

        # Find the first active participant with the matching role
        for agent_id, participant in session.participants.items():
            if participant.role == task.target_role and participant.is_active:
                return agent_id

        return None

    def update_task_status(
        self,
        session_id: str,
        task_id: str,
        status: TaskStatus,
        result: str | None = None,
    ) -> DelegatedTask | None:
        """Update the status of a delegated task."""
        session_tasks = self._tasks.get(session_id, {})
        task = session_tasks.get(task_id)
        if not task:
            return None
        task.status = status
        if result is not None:
            task.result = result
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task.completed_at = datetime.now(timezone.utc).isoformat()
        session = self._sessions.get(session_id)
        if session:
            session.updated_at = datetime.now(timezone.utc).isoformat()
        return task

    def get_tasks(
        self,
        session_id: str,
        status: TaskStatus | None = None,
        assigned_to: str | None = None,
    ) -> list[DelegatedTask]:
        """Get delegated tasks for a session, optionally filtered."""
        session_tasks = list(self._tasks.get(session_id, {}).values())
        if status:
            session_tasks = [t for t in session_tasks if t.status == status]
        if assigned_to:
            session_tasks = [t for t in session_tasks if t.assigned_to == assigned_to]
        return sorted(session_tasks, key=lambda t: (-t.priority, t.created_at))

    def get_pending_tasks_by_role(
        self, session_id: str, role: SessionRole,
    ) -> list[DelegatedTask]:
        """Get all pending tasks for a specific role in a session."""
        return [
            t for t in self._tasks.get(session_id, {}).values()
            if t.status == TaskStatus.PENDING and t.target_role == role
        ]

    # ═══════════════════════════════════════════════════════════════════
    # ── Collaborative Voting ──────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════

    def start_vote(
        self,
        session_id: str,
        topic: str,
        options: list[str],
        initiator_id: str,
        description: str = "",
    ) -> SessionVote | None:
        """Start a collaborative vote with weighted voting.

        Each participant's vote is weighted by their session role:
        Orchestrator = 3.0, Reviewer = 2.0, Worker = 1.0, Observer = 0.5.

        Args:
            session_id: The session to vote in.
            topic: The topic being voted on.
            options: The list of options to vote for.
            initiator_id: The agent starting the vote.
            description: Optional description of the vote.

        Returns:
            The created SessionVote, or None if the session is invalid.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        if len(options) < 2:
            logger.warning("start_vote: at least 2 options required")
            return None

        vote = SessionVote(
            session_id=session_id,
            topic=topic,
            description=description,
            options=options,
            initiator_id=initiator_id,
        )
        self._votes[session_id][vote.vote_id] = vote
        session.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Vote started: {vote.vote_id} on '{topic}' in session {session_id}")
        return vote

    def cast_vote(
        self,
        session_id: str,
        vote_id: str,
        voter_id: str,
        option: str,
    ) -> bool:
        """Cast a weighted vote from a participant.

        The voter's weight is determined by their role in the session.
        Each voter can only vote once; recasting overwrites the previous vote.

        Returns:
            True if the vote was cast successfully, False otherwise.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        if voter_id not in session.participants:
            logger.warning(f"cast_vote: {voter_id} is not a participant of session {session_id}")
            return False

        session_votes = self._votes.get(session_id, {})
        vote = session_votes.get(vote_id)
        if not vote:
            return False
        if vote.status != VoteStatus.OPEN:
            logger.warning(f"cast_vote: vote {vote_id} is not open")
            return False
        if option not in vote.options:
            logger.warning(f"cast_vote: '{option}' is not a valid option")
            return False

        participant = session.participants[voter_id]
        weight = _ROLE_WEIGHTS.get(participant.role, 1.0)

        vote.votes[voter_id] = {
            "option": option,
            "weight": weight,
            "role": participant.role.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        session.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Vote cast: {voter_id} voted '{option}' (weight={weight}) on {vote_id}")
        return True

    def get_vote_result(
        self, session_id: str, vote_id: str,
    ) -> dict[str, Any] | None:
        """Tally the results of a vote with weighted scoring.

        Returns:
            A dict with per-option tallies and the winning option, or None.
        """
        session_votes = self._votes.get(session_id, {})
        vote = session_votes.get(vote_id)
        if not vote:
            return None

        tally: dict[str, float] = {opt: 0.0 for opt in vote.options}
        for voter_id, cast in vote.votes.items():
            option = cast["option"]
            weight = cast["weight"]
            if option in tally:
                tally[option] += weight

        winning_option = max(tally, key=tally.get) if tally else None
        total_weight = sum(tally.values())

        return {
            "vote_id": vote.vote_id,
            "topic": vote.topic,
            "status": vote.status.value,
            "total_voters": len(vote.votes),
            "total_weight": total_weight,
            "tally": tally,
            "winning_option": winning_option,
            "winning_weight": tally.get(winning_option, 0) if winning_option else 0,
            "percentage": (
                {opt: round((w / total_weight) * 100, 1) for opt, w in tally.items()}
                if total_weight > 0
                else {}
            ),
            "voter_details": {
                vid: {
                    "option": cast["option"],
                    "weight": cast["weight"],
                    "role": cast.get("role", ""),
                }
                for vid, cast in vote.votes.items()
            },
        }

    def close_vote(self, session_id: str, vote_id: str) -> dict[str, Any] | None:
        """Close a vote and compute the final result."""
        session_votes = self._votes.get(session_id, {})
        vote = session_votes.get(vote_id)
        if not vote:
            return None
        if vote.status != VoteStatus.OPEN:
            return None

        vote.status = VoteStatus.CLOSED
        vote.resolved_at = datetime.now(timezone.utc).isoformat()

        result = self.get_vote_result(session_id, vote_id)
        if result:
            vote.winning_option = result["winning_option"]
            vote.status = VoteStatus.RESOLVED
            result["status"] = VoteStatus.RESOLVED.value

        session = self._sessions.get(session_id)
        if session:
            session.updated_at = datetime.now(timezone.utc).isoformat()

        logger.info(f"Vote {vote_id} resolved: winner='{vote.winning_option}'")
        return result

    def get_open_votes(self, session_id: str) -> list[SessionVote]:
        """Get all open votes in a session."""
        return [
            v for v in self._votes.get(session_id, {}).values()
            if v.status == VoteStatus.OPEN
        ]

    # ═══════════════════════════════════════════════════════════════════
    # ── Session Templates ─────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════

    def _seed_templates(self) -> None:
        """Create built-in session templates for common collaboration patterns."""
        builtins = [
            SessionTemplate(
                name="Code Review",
                description="Collaborative code review session with reviewer and author roles.",
                pattern="code_review",
                required_roles=[SessionRole.ORCHESTRATOR, SessionRole.REVIEWER, SessionRole.WORKER],
                suggested_participants=3,
                tags=["code_review", "quality"],
                default_context={
                    "workflow": "review",
                    "approval_required": True,
                    "review_rounds": 1,
                },
            ),
            SessionTemplate(
                name="Brainstorming",
                description="Open brainstorming session for creative problem solving.",
                pattern="brainstorming",
                required_roles=[SessionRole.ORCHESTRATOR, SessionRole.WORKER],
                suggested_participants=4,
                tags=["ideation", "creative"],
                default_context={
                    "workflow": "brainstorm",
                    "voting_enabled": True,
                    "timebox_minutes": 30,
                },
            ),
            SessionTemplate(
                name="Incident Response",
                description="Structured incident response with orchestrator-led coordination.",
                pattern="incident_response",
                required_roles=[SessionRole.ORCHESTRATOR, SessionRole.WORKER, SessionRole.OBSERVER],
                suggested_participants=5,
                tags=["incident", "urgent"],
                default_context={
                    "workflow": "incident_response",
                    "severity": "unknown",
                    "status_page_update": True,
                },
            ),
            SessionTemplate(
                name="Pair Programming",
                description="Two-agent pair programming session with driver and navigator.",
                pattern="pair_programming",
                required_roles=[SessionRole.WORKER, SessionRole.REVIEWER],
                suggested_participants=2,
                tags=["development", "pairing"],
                default_context={
                    "workflow": "pair",
                    "driver_rotation_minutes": 20,
                },
            ),
            SessionTemplate(
                name="Daily Standup",
                description="Quick daily standup for status updates and blocker identification.",
                pattern="daily_standup",
                required_roles=[SessionRole.ORCHESTRATOR, SessionRole.WORKER],
                suggested_participants=3,
                tags=["standup", "planning"],
                default_context={
                    "workflow": "standup",
                    "timebox_minutes": 15,
                    "format": "yesterday_today_blockers",
                },
            ),
        ]
        for tmpl in builtins:
            self._templates[tmpl.template_id] = tmpl

    def create_template(
        self,
        name: str,
        description: str,
        pattern: str,
        required_roles: list[SessionRole],
        suggested_participants: int = 2,
        tags: list[str] | None = None,
        default_context: dict[str, Any] | None = None,
    ) -> SessionTemplate:
        """Create a custom session template for reusable collaboration patterns.

        Args:
            name: Human-readable template name.
            description: What this template is for.
            pattern: A unique pattern identifier (e.g. "code_review", "brainstorming").
            required_roles: The roles that should be filled in a session using this template.
            suggested_participants: Recommended number of participants.
            tags: Categorization tags.
            default_context: Default shared context for sessions created from this template.

        Returns:
            The created SessionTemplate.
        """
        template = SessionTemplate(
            name=name,
            description=description,
            pattern=pattern,
            required_roles=required_roles,
            suggested_participants=suggested_participants,
            tags=tags or [],
            default_context=default_context or {},
        )
        self._templates[template.template_id] = template
        logger.info(f"Template created: {template.template_id} ({name})")
        return template

    def load_template(
        self,
        session_id: str,
        template_id: str,
        overwrite_context: bool = False,
    ) -> bool:
        """Apply a session template to an existing session.

        This sets the session's shared context and tags based on the template.
        If overwrite_context is True, existing context keys are replaced.

        Args:
            session_id: The session to apply the template to.
            template_id: The template to load.
            overwrite_context: Whether to overwrite existing context keys.

        Returns:
            True if the template was applied, False otherwise.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        template = self._templates.get(template_id)
        if not template:
            return False

        # Merge tags
        for tag in template.tags:
            if tag not in session.tags:
                session.tags.append(tag)

        # Merge default context
        if overwrite_context:
            session.shared_context.update(template.default_context)
        else:
            for key, value in template.default_context.items():
                if key not in session.shared_context:
                    session.shared_context[key] = value

        # Set a template reference in context
        session.shared_context["_template_id"] = template_id
        session.shared_context["_template_pattern"] = template.pattern

        session.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Template {template.name} loaded into session {session_id}"
        )
        return True

    def create_session_from_template(
        self,
        template_id: str,
        name: str,
        orchestrator_id: str = "",
        description: str = "",
    ) -> CollaborativeSession | None:
        """Create a new session pre-configured with a template.

        Args:
            template_id: The template to base the session on.
            name: Name for the new session.
            orchestrator_id: Initial orchestrator agent.
            description: Optional session description (overrides template description).

        Returns:
            The created CollaborativeSession, or None if the template is not found.
        """
        template = self._templates.get(template_id)
        if not template:
            return None

        session = self.create_session(
            name=name,
            description=description or template.description,
            orchestrator_id=orchestrator_id,
            tags=template.tags.copy(),
        )
        session.shared_context.update(template.default_context)
        session.shared_context["_template_id"] = template_id
        session.shared_context["_template_pattern"] = template.pattern
        logger.info(
            f"Session {session.session_id} created from template '{template.name}'"
        )
        return session

    def list_templates(
        self, pattern: str | None = None, tag: str | None = None,
    ) -> list[SessionTemplate]:
        """List available session templates, optionally filtered."""
        templates = list(self._templates.values())
        if pattern:
            templates = [t for t in templates if t.pattern == pattern]
        if tag:
            templates = [t for t in templates if tag in t.tags]
        return sorted(templates, key=lambda t: t.name)

    def get_template(self, template_id: str) -> SessionTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    # ═══════════════════════════════════════════════════════════════════
    # ── Session Summarization ─────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════

    def summarize_session(self, session_id: str) -> dict[str, Any] | None:
        """Generate a comprehensive summary of session activity and outcomes.

        The summary includes:
        - Session metadata (name, duration, state)
        - Participant list with roles and activity status
        - Message statistics (total, by role, by sender)
        - Artifact summary
        - Delegated task status breakdown
        - Voting outcomes (resolved and open votes)
        - Handoff history
        - Key context keys

        Args:
            session_id: The session to summarize.

        Returns:
            A dict with the full summary, or None if the session is not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        now = datetime.now(timezone.utc)
        created = datetime.fromisoformat(session.created_at)
        duration = now - created

        # Message breakdown by sender
        messages_by_sender: dict[str, int] = defaultdict(int)
        messages_by_role: dict[str, int] = defaultdict(int)
        for msg in session.messages:
            messages_by_sender[msg.sender_name or msg.sender_id] += 1
            messages_by_role[msg.role.value] += 1

        # Task breakdown
        session_tasks = self._tasks.get(session_id, {})
        task_breakdown: dict[str, int] = defaultdict(int)
        completed_tasks: list[dict[str, Any]] = []
        for task in session_tasks.values():
            task_breakdown[task.status.value] += 1
            if task.status == TaskStatus.COMPLETED:
                completed_tasks.append({
                    "task_id": task.task_id,
                    "description": task.description,
                    "assigned_to": task.assigned_to,
                    "result": task.result,
                })

        # Vote outcomes
        session_votes = self._votes.get(session_id, {})
        resolved_votes: list[dict[str, Any]] = []
        open_votes: list[dict[str, Any]] = []
        for vote in session_votes.values():
            if vote.status == VoteStatus.RESOLVED:
                resolved_votes.append({
                    "vote_id": vote.vote_id,
                    "topic": vote.topic,
                    "winning_option": vote.winning_option,
                    "voter_count": len(vote.votes),
                })
            elif vote.status == VoteStatus.OPEN:
                open_votes.append({
                    "vote_id": vote.vote_id,
                    "topic": vote.topic,
                    "voter_count": len(vote.votes),
                })

        # Handoff history
        handoffs = self._handoff_log.get(session_id, [])

        # Activity summary
        activity = self._participant_activity.get(session_id, {})

        # Key context (filter out internal template keys)
        key_context = {
            k: v for k, v in session.shared_context.items()
            if not k.startswith("_template_")
        }

        return {
            "session_id": session.session_id,
            "name": session.name,
            "description": session.description,
            "state": session.state.value,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "duration_seconds": int(duration.total_seconds()),
            "duration_human": str(duration).split(".")[0],
            "participants": [
                {
                    "agent_id": p.agent_id,
                    "name": p.name,
                    "role": p.role.value,
                    "is_active": p.is_active,
                    "last_active": activity.get(p.agent_id),
                }
                for p in session.participants.values()
            ],
            "messages": {
                "total": session.message_count,
                "by_role": dict(messages_by_role),
                "by_sender": dict(messages_by_sender),
            },
            "artifacts": {
                "total": session.artifact_count,
                "by_type": {
                    atype: len([a for a in session.artifacts.values() if a.artifact_type == atype])
                    for atype in set(a.artifact_type for a in session.artifacts.values())
                },
            },
            "tasks": {
                "total": len(session_tasks),
                "breakdown": dict(task_breakdown),
                "completed": completed_tasks,
            },
            "votes": {
                "total": len(session_votes),
                "resolved": resolved_votes,
                "open": open_votes,
            },
            "handoffs": handoffs,
            "tags": session.tags,
            "key_context": key_context,
            "parent_session_id": session.parent_session_id,
        }

    # ═══════════════════════════════════════════════════════════════════
    # ── Handoff Protocol ──────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════

    def handoff_session(
        self,
        session_id: str,
        from_agent_id: str,
        to_agent_id: str,
        context_notes: str = "",
        preserve_role: bool = True,
    ) -> dict[str, Any] | None:
        """Hand off a session from one agent to another with full context preservation.

        The handoff protocol:
        1. Transfers orchestrator/leadership role to the target agent.
        2. Adds the target agent as a participant if not already present.
        3. Records the handoff in the session log with context notes.
        4. Preserves all shared context, artifacts, and message history.
        5. Optionally preserves the departing agent's role (demotes to worker).

        Args:
            session_id: The session to hand off.
            from_agent_id: The agent handing off the session.
            to_agent_id: The agent receiving the session.
            context_notes: Optional notes about the handoff context.
            preserve_role: If True, the departing agent is demoted to worker
                           rather than being removed.

        Returns:
            A dict with the handoff record, or None if the session is invalid.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        if from_agent_id not in session.participants:
            logger.warning(f"handoff_session: {from_agent_id} is not a participant")
            return None

        # Ensure the target agent is a participant
        if to_agent_id not in session.participants:
            self.add_participant(
                session_id=session_id,
                agent_id=to_agent_id,
                name=to_agent_id,
                role=SessionRole.ORCHESTRATOR,
            )
        else:
            # Transfer orchestrator role to target
            self.set_leader(session_id, to_agent_id)

        # Preserve departing agent as worker or deactivate
        if preserve_role and from_agent_id != to_agent_id:
            departing = session.participants[from_agent_id]
            if departing.role == SessionRole.ORCHESTRATOR:
                departing.role = SessionRole.WORKER
        elif from_agent_id != to_agent_id:
            session.participants[from_agent_id].is_active = False

        # Create a handoff message in the session
        handoff_message = (
            f"Session handed off from {from_agent_id} to {to_agent_id}."
        )
        if context_notes:
            handoff_message += f" Context: {context_notes}"

        self.send_message(
            session_id=session_id,
            sender_id="system",
            content=handoff_message,
            role=MessageRole.SYSTEM,
        )

        # Record the handoff
        handoff_record = {
            "handoff_id": f"handoff-{uuid.uuid4().hex[:8]}",
            "session_id": session_id,
            "from_agent": from_agent_id,
            "to_agent": to_agent_id,
            "context_notes": context_notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_count_at_handoff": session.message_count,
            "artifact_count_at_handoff": session.artifact_count,
            "task_count_at_handoff": len(self._tasks.get(session_id, {})),
        }
        self._handoff_log[session_id].append(handoff_record)

        # Store handoff state in shared context
        session.shared_context["_last_handoff"] = handoff_record
        session.updated_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Session {session_id} handed off from {from_agent_id} "
            f"to {to_agent_id}"
        )
        return handoff_record

    def get_handoff_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get the complete handoff history for a session."""
        return list(self._handoff_log.get(session_id, []))

    # ═══════════════════════════════════════════════════════════════════
    # ── Session Health Check ──────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════

    def check_session_health(self, session_id: str) -> dict[str, Any] | None:
        """Monitor session health including participant responsiveness and message rate.

        Checks the following health metrics:
        - Overall session status (active/paused/completed)
        - Participant responsiveness (last activity per participant)
        - Stale participants (no activity beyond a threshold)
        - Message rate (messages per minute over the session lifetime)
        - Recent activity (messages in the last 5 minutes)
        - Task completion ratio
        - Open votes that may need attention
        - Session age

        Args:
            session_id: The session to check.

        Returns:
            A dict with health metrics and status, or None if the session is not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        now = datetime.now(timezone.utc)
        created = datetime.fromisoformat(session.created_at)
        updated = datetime.fromisoformat(session.updated_at)
        session_age_seconds = (now - created).total_seconds()
        idle_seconds = (now - updated).total_seconds()

        # Per-participant responsiveness
        activity = self._participant_activity.get(session_id, {})
        participant_health: list[dict[str, Any]] = []
        stale_participants: list[str] = []
        responsive_participants: list[str] = []

        # Thresholds (in seconds)
        stale_threshold = 600  # 10 minutes
        warning_threshold = 300  # 5 minutes

        for agent_id, participant in session.participants.items():
            last_active_str = activity.get(agent_id)
            if last_active_str:
                last_active = datetime.fromisoformat(last_active_str)
                inactive_seconds = (now - last_active).total_seconds()
            else:
                # Never recorded activity; use joined_at if available
                joined = datetime.fromisoformat(participant.joined_at)
                inactive_seconds = (now - joined).total_seconds()

            health_status = "healthy"
            if inactive_seconds > stale_threshold:
                health_status = "stale"
                stale_participants.append(agent_id)
            elif inactive_seconds > warning_threshold:
                health_status = "warning"
            else:
                responsive_participants.append(agent_id)

            participant_health.append({
                "agent_id": agent_id,
                "name": participant.name,
                "role": participant.role.value,
                "is_active": participant.is_active,
                "inactive_seconds": int(inactive_seconds),
                "inactive_human": str(timedelta(seconds=int(inactive_seconds))),
                "health_status": health_status,
            })

        # Message rate (messages per minute)
        messages_per_minute = 0.0
        if session_age_seconds > 0:
            messages_per_minute = round(
                (session.message_count / session_age_seconds) * 60, 2
            )

        # Recent messages (last 5 minutes)
        five_min_ago = now - timedelta(minutes=5)
        recent_messages = [
            m for m in session.messages
            if datetime.fromisoformat(m.timestamp) > five_min_ago
        ]

        # Task completion ratio
        session_tasks = self._tasks.get(session_id, {})
        total_tasks = len(session_tasks)
        completed_tasks = sum(
            1 for t in session_tasks.values()
            if t.status == TaskStatus.COMPLETED
        )
        failed_tasks = sum(
            1 for t in session_tasks.values()
            if t.status == TaskStatus.FAILED
        )
        task_completion_ratio = (
            round(completed_tasks / total_tasks, 2) if total_tasks > 0 else 1.0
        )

        # Open votes
        open_votes = self.get_open_votes(session_id)

        # Overall health assessment
        total_participants = len(session.participants)
        if total_participants == 0:
            overall_health = "empty"
        elif len(stale_participants) == total_participants:
            overall_health = "critical"
        elif len(stale_participants) > 0:
            overall_health = "degraded"
        elif session.state == SessionState.PAUSED:
            overall_health = "paused"
        elif session.state == SessionState.COMPLETED:
            overall_health = "completed"
        elif idle_seconds > stale_threshold:
            overall_health = "idle"
        else:
            overall_health = "healthy"

        return {
            "session_id": session.session_id,
            "session_name": session.name,
            "session_state": session.state.value,
            "overall_health": overall_health,
            "checked_at": now.isoformat(),
            "session_age": {
                "seconds": int(session_age_seconds),
                "human": str(timedelta(seconds=int(session_age_seconds))),
            },
            "idle_time": {
                "seconds": int(idle_seconds),
                "human": str(timedelta(seconds=int(idle_seconds))),
            },
            "participants": {
                "total": total_participants,
                "healthy": len(responsive_participants),
                "stale": len(stale_participants),
                "details": participant_health,
            },
            "message_rate": {
                "total_messages": session.message_count,
                "messages_per_minute": messages_per_minute,
                "recent_messages_5min": len(recent_messages),
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks,
                "pending": total_tasks - completed_tasks - failed_tasks,
                "completion_ratio": task_completion_ratio,
            },
            "votes": {
                "open": len(open_votes),
                "open_vote_ids": [v.vote_id for v in open_votes],
            },
            "artifacts": {
                "total": session.artifact_count,
            },
            "participant_count": total_participants,
        }

    def _record_activity(self, session_id: str, agent_id: str) -> None:
        """Record a participant's activity timestamp for health tracking."""
        self._participant_activity[session_id][agent_id] = (
            datetime.now(timezone.utc).isoformat()
        )

    def record_participant_heartbeat(
        self, session_id: str, agent_id: str,
    ) -> bool:
        """Explicitly record a heartbeat from a participant to indicate liveness.

        Use this for agents that are listening but not actively sending messages.
        """
        session = self._sessions.get(session_id)
        if not session or agent_id not in session.participants:
            return False
        self._record_activity(session_id, agent_id)
        return True

    def get_participant_activity(
        self, session_id: str, agent_id: str,
    ) -> str | None:
        """Get the last activity timestamp for a participant."""
        return self._participant_activity.get(session_id, {}).get(agent_id)


# Singleton
agent_session_manager = AgentSessionManager()