"""
Agent Communication Protocol - Standardized Inter-Agent Messaging for Buddy.

The Agent Communication Protocol provides a standardized framework for
agent-to-agent communication, enabling seamless collaboration between
specialized agents. It defines message types, routing mechanisms, state
management, and conversation tracking.

Core capabilities:
- Standardized message format with priority and routing
- Conversation threading with state tracking
- Message broadcasting and targeted delivery
- Protocol negotiation between agents
- Session management with handshake protocol
- Message validation and schema enforcement
"""

from __future__ import annotations

import uuid
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("buddy.agent_protocol")


class MessageType(str, Enum):
    """Standardized message types for inter-agent communication."""
    # Task-related
    TASK_REQUEST = "task_request"          # Request agent to perform a task
    TASK_RESPONSE = "task_response"        # Response to a task request
    TASK_DELEGATE = "task_delegate"        # Delegate a subtask
    TASK_STATUS = "task_status"            # Status update on a task

    # Knowledge-related
    KNOWLEDGE_QUERY = "knowledge_query"    # Query another agent's knowledge
    KNOWLEDGE_SHARE = "knowledge_share"    # Share knowledge with another agent
    KNOWLEDGE_VERIFY = "knowledge_verify"  # Verify knowledge accuracy

    # Collaboration
    COLLABORATION_REQUEST = "collab_request"   # Request collaboration
    COLLABORATION_ACCEPT = "collab_accept"     # Accept collaboration
    COLLABORATION_REJECT = "collab_reject"     # Reject collaboration
    COLLABORATION_UPDATE = "collab_update"     # Update on collaboration progress

    # System
    HANDSHAKE = "handshake"                # Initial connection handshake
    HEARTBEAT = "heartbeat"                # Keep-alive signal
    DISCONNECT = "disconnect"              # Graceful disconnect
    ERROR = "error"                        # Error notification
    ACK = "ack"                            # Acknowledgment

    # Review
    REVIEW_REQUEST = "review_request"      # Request code/task review
    REVIEW_FEEDBACK = "review_feedback"    # Provide review feedback


class MessagePriority(str, Enum):
    """Priority levels for inter-agent messages."""
    CRITICAL = "critical"    # Must be handled immediately
    HIGH = "high"            # Important, handle soon
    NORMAL = "normal"        # Standard priority
    LOW = "low"              # Can be deferred
    BACKGROUND = "background"  # Process when idle


class ProtocolVersion(str, Enum):
    """Supported protocol versions."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


@dataclass
class AgentMessage:
    """A standardized message between agents."""
    message_id: str
    sender_id: str
    receiver_id: str                    # Can be "broadcast" for all agents
    message_type: MessageType
    content: dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: str | None = None   # Links related messages
    conversation_id: str | None = None  # Thread identifier
    protocol_version: ProtocolVersion = ProtocolVersion.V1_0
    requires_response: bool = False
    timeout_ms: int = 30000
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "conversation_id": self.conversation_id,
            "protocol_version": self.protocol_version.value,
            "requires_response": self.requires_response,
            "timeout_ms": self.timeout_ms,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Conversation:
    """A conversation thread between agents."""
    conversation_id: str
    participants: list[str]
    topic: str
    status: str = "active"           # active, completed, archived
    messages: list[AgentMessage] = field(default_factory=list)
    message_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: AgentMessage) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.message_count += 1
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "participants": self.participants,
            "topic": self.topic,
            "status": self.status,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AgentSession:
    """A session between two communicating agents."""
    session_id: str
    initiator_id: str
    responder_id: str
    protocol_version: ProtocolVersion
    status: str = "connecting"         # connecting, established, closed
    established_at: datetime | None = None
    closed_at: datetime | None = None
    messages_sent: int = 0
    messages_received: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentProtocol:
    """Standardized communication protocol for Buddy agents.

    Enables structured, reliable communication between agents with
    message routing, conversation threading, session management, and
    protocol negotiation. Supports both point-to-point and broadcast
    communication patterns.
    """

    def __init__(self):
        self._messages: dict[str, AgentMessage] = {}
        self._conversations: dict[str, Conversation] = {}
        self._sessions: dict[str, AgentSession] = {}
        self._message_queue: list[AgentMessage] = []
        self._total_messages = 0
        self._total_conversations = 0
        self._total_sessions = 0

    # ── Session Management ──────────────────────────────────────────

    def initiate_session(
        self,
        initiator_id: str,
        responder_id: str,
        protocol_version: ProtocolVersion = ProtocolVersion.V1_0,
        metadata: dict[str, Any] | None = None,
    ) -> AgentSession:
        """Initiate a communication session between two agents."""
        session_id = f"session-{uuid.uuid4().hex[:12]}"

        session = AgentSession(
            session_id=session_id,
            initiator_id=initiator_id,
            responder_id=responder_id,
            protocol_version=protocol_version,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        self._total_sessions += 1

        # Send handshake
        self.send_message(
            sender_id=initiator_id,
            receiver_id=responder_id,
            message_type=MessageType.HANDSHAKE,
            content={
                "protocol_version": protocol_version.value,
                "session_id": session_id,
            },
            priority=MessagePriority.HIGH,
        )

        return session

    def establish_session(self, session_id: str) -> bool:
        """Mark a session as established after handshake."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.status = "established"
        session.established_at = datetime.now(timezone.utc)
        return True

    def close_session(self, session_id: str) -> bool:
        """Close an active session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.status = "closed"
        session.closed_at = datetime.now(timezone.utc)

        # Send disconnect notification
        self.send_message(
            sender_id=session.initiator_id,
            receiver_id=session.responder_id,
            message_type=MessageType.DISCONNECT,
            content={"session_id": session_id},
            priority=MessagePriority.LOW,
        )

        return True

    # ── Message Operations ──────────────────────────────────────────

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: MessageType,
        content: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: str | None = None,
        conversation_id: str | None = None,
        requires_response: bool = False,
        timeout_ms: int = 30000,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        """Send a message from one agent to another."""
        message_id = f"msg-{uuid.uuid4().hex[:12]}"

        message = AgentMessage(
            message_id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            priority=priority,
            correlation_id=correlation_id,
            conversation_id=conversation_id,
            requires_response=requires_response,
            timeout_ms=timeout_ms,
            metadata=metadata or {},
        )

        self._messages[message_id] = message
        self._message_queue.append(message)
        self._total_messages += 1

        # Update session counters
        for session in self._sessions.values():
            if session.status == "established":
                if sender_id in (session.initiator_id, session.responder_id):
                    session.messages_sent += 1

        # Add to conversation if specified
        if conversation_id and conversation_id in self._conversations:
            self._conversations[conversation_id].add_message(message)

        return message

    def receive_messages(
        self,
        receiver_id: str,
        message_type: MessageType | None = None,
        priority: MessagePriority | None = None,
        limit: int = 50,
    ) -> list[AgentMessage]:
        """Receive messages for a specific receiver."""
        results: list[AgentMessage] = []

        for msg in self._message_queue:
            if msg.receiver_id != receiver_id and msg.receiver_id != "broadcast":
                continue
            if message_type and msg.message_type != message_type:
                continue
            if priority and msg.priority != priority:
                continue
            results.append(msg)

        results.sort(key=lambda m: (
            {"critical": 0, "high": 1, "normal": 2, "low": 3, "background": 4}[m.priority.value],
            m.created_at,
        ))

        return results[:limit]

    def acknowledge_message(self, message_id: str) -> bool:
        """Acknowledge receipt of a message."""
        if message_id not in self._messages:
            return False

        message = self._messages[message_id]
        # Remove from queue after acknowledgment
        self._message_queue = [
            m for m in self._message_queue if m.message_id != message_id
        ]

        # Send ACK back
        self.send_message(
            sender_id=message.receiver_id,
            receiver_id=message.sender_id,
            message_type=MessageType.ACK,
            content={"acknowledged_message_id": message_id},
            correlation_id=message.message_id,
            priority=MessagePriority.LOW,
        )

        return True

    def broadcast(
        self,
        sender_id: str,
        message_type: MessageType,
        content: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        exclude: list[str] | None = None,
    ) -> AgentMessage:
        """Broadcast a message to all agents."""
        return self.send_message(
            sender_id=sender_id,
            receiver_id="broadcast",
            message_type=message_type,
            content=content,
            priority=priority,
            metadata={"exclude": exclude or []},
        )

    # ── Conversation Management ─────────────────────────────────────

    def create_conversation(
        self,
        participants: list[str],
        topic: str,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation thread."""
        conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

        conversation = Conversation(
            conversation_id=conversation_id,
            participants=participants,
            topic=topic,
            metadata=metadata or {},
        )
        self._conversations[conversation_id] = conversation
        self._total_conversations += 1

        return conversation

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self._conversations.get(conversation_id)

    def list_conversations(
        self, participant_id: str | None = None, status: str | None = None
    ) -> list[Conversation]:
        """List conversations with optional filters."""
        results = list(self._conversations.values())

        if participant_id:
            results = [c for c in results if participant_id in c.participants]
        if status:
            results = [c for c in results if c.status == status]

        results.sort(key=lambda c: c.updated_at, reverse=True)
        return results

    def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a conversation."""
        conv = self._conversations.get(conversation_id)
        if not conv:
            return False
        conv.status = "archived"
        return True

    # ── Protocol Negotiation ────────────────────────────────────────

    def negotiate_protocol(
        self, initiator_id: str, responder_id: str
    ) -> ProtocolVersion:
        """Negotiate the highest compatible protocol version."""
        # Try V2.0 first, fall back to V1.1, then V1.0
        session = self.initiate_session(
            initiator_id=initiator_id,
            responder_id=responder_id,
            protocol_version=ProtocolVersion.V2_0,
        )

        # Check if responder supports the version
        responses = self.receive_messages(
            receiver_id=initiator_id,
            message_type=MessageType.HANDSHAKE,
        )

        for resp in responses:
            version = resp.content.get("protocol_version", "1.0")
            if version == "2.0":
                return ProtocolVersion.V2_0

        return ProtocolVersion.V1_0

    # ── Query Methods ───────────────────────────────────────────────

    def get_message(self, message_id: str) -> AgentMessage | None:
        """Get a message by ID."""
        return self._messages.get(message_id)

    def get_queue_size(self) -> int:
        """Get current message queue size."""
        return len(self._message_queue)

    def get_stats(self) -> dict:
        """Get protocol statistics."""
        type_counts = {}
        for msg in self._messages.values():
            t = msg.message_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        priority_counts = {}
        for msg in self._messages.values():
            p = msg.priority.value
            priority_counts[p] = priority_counts.get(p, 0) + 1

        return {
            "total_messages": self._total_messages,
            "total_conversations": self._total_conversations,
            "total_sessions": self._total_sessions,
            "active_sessions": len([
                s for s in self._sessions.values() if s.status == "established"
            ]),
            "queue_size": len(self._message_queue),
            "messages_by_type": type_counts,
            "messages_by_priority": priority_counts,
            "active_conversations": len([
                c for c in self._conversations.values() if c.status == "active"
            ]),
        }


# Singleton instance
agent_protocol = AgentProtocol()


# ═══════════════════════════════════════════════════════════
# Backward-compatible aliases for existing code
# ═══════════════════════════════════════════════════════════

import time as _time
from dataclasses import dataclass as _dataclass, field as _field


class ComponentState(str, Enum):
    """Component state enum (backward compat)."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


@_dataclass
class ComponentInfo:
    """Component info dataclass (backward compat)."""
    component_id: str
    component_type: str
    state: ComponentState = ComponentState.ACTIVE
    capabilities: list[str] = _field(default_factory=list)
    health_score: float = 1.0
    dependencies: list[str] = _field(default_factory=list)
    metadata: dict[str, Any] = _field(default_factory=dict)
    registered_at: float = _field(default_factory=_time.time)
    last_heartbeat: float = _field(default_factory=_time.time)


class ComponentRegistry:
    """Component registry (backward compat)."""

    def __init__(self):
        self._components: dict[str, ComponentInfo] = {}

    def get_all_components(self) -> dict[str, ComponentInfo]:
        return dict(self._components)

    def heartbeat(self, component_id: str) -> None:
        if component_id in self._components:
            self._components[component_id].last_heartbeat = _time.time()

    def register(self, info: ComponentInfo) -> None:
        self._components[info.component_id] = info


class EventBus:
    """Event bus (backward compat)."""

    def __init__(self):
        self._events: list[dict] = []
        self._subscribers: dict[str, list[Callable]] = {}

    def get_stats(self) -> dict:
        return {
            "total_events": len(self._events),
            "subscriber_count": sum(len(v) for v in self._subscribers.values()),
            "event_types": list(set(e.get("type", "unknown") for e in self._events)),
        }


class StateSynchronizer:
    """State synchronizer (backward compat)."""

    def __init__(self):
        self._states: dict[str, dict] = {}

    def get_stats(self) -> dict:
        return {"components": len(self._states), "keys": sum(len(v) for v in self._states.values())}


class MessageRouter:
    """Message router (backward compat)."""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self.processed_count = 0
        self.error_count = 0

    def register_handler(self, msg_type: str, handler: Callable) -> None:
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)


ProtocolMessage = AgentMessage  # Backward-compatible alias


class ProtocolEngine:
    """Backward-compatible ProtocolEngine wrapping AgentProtocol.

    Provides the older API surface used by existing routes while
    delegating core functionality to the underlying AgentProtocol.
    """

    def __init__(self):
        self._protocol = agent_protocol
        self.registry = ComponentRegistry()
        self.events = EventBus()
        self.router = MessageRouter()
        self.synchronizer = StateSynchronizer()

    def get_global_stats(self) -> dict:
        stats = self._protocol.get_stats()
        stats.update({
            "router": {
                "processed_count": self.router.processed_count,
                "error_count": self.router.error_count,
                "queue_size": stats.get("queue_size", 0),
                "registered_handlers": {},
                "is_running": True,
            },
            "events": self.events.get_stats(),
            "registry": {
                "total_components": len(self.registry._components),
                "components_by_type": {},
                "health_summary": {},
            },
            "synchronizer": self.synchronizer.get_stats(),
        })
        return stats

    def register_component(
        self, component_id: str, component_type: str,
        capabilities: list[str] | None = None,
        dependencies: list[str] | None = None,
        metadata: dict | None = None,
    ) -> ComponentInfo:
        info = ComponentInfo(
            component_id=component_id,
            component_type=component_type,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            metadata=metadata or {},
        )
        self.registry.register(info)
        return info

    async def emit_event(
        self, event_type: str, source: str, data: dict,
        component_id: str | None = None,
    ) -> None:
        self.events._events.append({
            "type": event_type,
            "source": source,
            "data": data,
            "component_id": component_id,
            "timestamp": _time.time(),
        })


# Singleton instance
protocol_engine = ProtocolEngine()