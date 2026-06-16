"""Buddy Agent Communication Protocol — structured inter-agent messaging system

Provides a standardized messaging layer for agent-to-agent communication with
message routing, priority queues, delivery guarantees, and protocol versioning.
Enables agents to coordinate tasks, share context, and negotiate workflows.

Core capabilities:
  - Structured Message Types: task_request, context_share, capability_query, negotiation
  - Priority-based Message Queuing with TTL and retry logic
  - Protocol Version Negotiation for backward compatibility
  - Delivery Acknowledgments and idempotency guarantees
  - Conversation Threading for multi-turn agent dialogues
  - Broadcast and Multicast messaging patterns
"""
from __future__ import annotations

import asyncio
import hashlib
import heapq
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.protocol")


class MessageType(str, Enum):
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    CONTEXT_SHARE = "context_share"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    NEGOTIATION_PROPOSAL = "negotiation_proposal"
    NEGOTIATION_ACCEPT = "negotiation_accept"
    NEGOTIATION_REJECT = "negotiation_reject"
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"
    BROADCAST = "broadcast"
    ERROR = "error"


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class AgentMessage:
    """A structured message in the Agent Communication Protocol."""
    id: str = field(default_factory=lambda: f"acp-{uuid.uuid4().hex[:12]}")
    msg_type: MessageType = MessageType.TASK_REQUEST
    sender_id: str = ""
    recipient_id: str = ""
    thread_id: str = ""
    priority: MessagePriority = MessagePriority.NORMAL
    payload: dict = field(default_factory=dict)
    ttl_seconds: int = 300
    requires_ack: bool = True
    protocol_version: str = "1.0"
    correlation_id: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    delivered_at: str = ""
    acknowledged_at: str = ""
    status: DeliveryStatus = DeliveryStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "msg_type": self.msg_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "thread_id": self.thread_id,
            "priority": self.priority.value,
            "payload": self.payload,
            "ttl_seconds": self.ttl_seconds,
            "requires_ack": self.requires_ack,
            "protocol_version": self.protocol_version,
            "correlation_id": self.correlation_id,
            "tags": self.tags,
            "created_at": self.created_at,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    def is_expired(self) -> bool:
        if not self.created_at:
            return False
        created = datetime.fromisoformat(self.created_at)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        return elapsed > self.ttl_seconds

    def fingerprint(self) -> str:
        """Generate a deterministic fingerprint for idempotency checks."""
        parts = f"{self.sender_id}:{self.msg_type.value}:{json.dumps(self.payload, sort_keys=True)}"
        return hashlib.sha256(parts.encode()).hexdigest()[:16]


@dataclass
class ProtocolSession:
    """An active communication session between two agents."""
    id: str
    agent_a: str
    agent_b: str
    messages: list[AgentMessage] = field(default_factory=list)
    protocol_version: str = "1.0"
    established_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True
    metadata: dict = field(default_factory=dict)

    def touch(self):
        self.last_activity = datetime.now(timezone.utc).isoformat()


class _PriorityQueue:
    """A priority queue backed by heapq and asyncio.Queue for async support.

    Compatible with Python 3.9+. Provides the same put/get/qsize interface
    as asyncio.PriorityQueue but uses heapq for priority ordering and
    asyncio.Queue as the async wakeup mechanism.
    """

    def __init__(self, maxsize: int = 0):
        self._heap: list[tuple[int, int, Any]] = []
        self._counter: int = 0
        self._ready: asyncio.Queue = asyncio.Queue(maxsize=maxsize)

    async def put(self, item: tuple[int, Any]) -> None:
        """Put an item into the queue. item is (priority, value)."""
        priority, value = item
        heapq.heappush(self._heap, (priority, self._counter, value))
        self._counter += 1
        await self._ready.put(None)

    async def get(self) -> tuple[int, Any]:
        """Get the highest-priority item, returning (priority, value)."""
        await self._ready.get()
        priority, _, value = heapq.heappop(self._heap)
        return (priority, value)

    def qsize(self) -> int:
        """Return the approximate number of items in the queue."""
        return len(self._heap)


class AgentCommunicationProtocol:
    """Central message router and protocol manager for inter-agent communication.

    Handles message routing, delivery guarantees, protocol versioning,
    and priority-based queue management. Supports both point-to-point
    and broadcast messaging patterns.
    """

    MAX_QUEUE_SIZE = 1000
    SESSION_TIMEOUT_SECONDS = 3600

    def __init__(self):
        self._message_handlers: dict[MessageType, list[Callable[[AgentMessage], Awaitable[None]]]] = {}
        self._message_queue: _PriorityQueue = _PriorityQueue()
        self._sessions: dict[str, ProtocolSession] = {}
        self._agent_handlers: dict[str, Callable[[AgentMessage], Awaitable[None]]] = {}
        self._processed_fingerprints: set[str] = set()
        self._delivery_stats: dict[str, dict] = {}
        self._is_running: bool = False
        self._processor_task: asyncio.Task | None = None

    def register_handler(self, msg_type: MessageType, handler: Callable[[AgentMessage], Awaitable[None]]):
        """Register a handler for a specific message type."""
        self._message_handlers.setdefault(msg_type, []).append(handler)
        logger.debug(f"Registered handler for message type: {msg_type.value}")

    def register_agent_handler(self, agent_id: str, handler: Callable[[AgentMessage], Awaitable[None]]):
        """Register a message handler for a specific agent."""
        self._agent_handlers[agent_id] = handler
        logger.debug(f"Registered agent handler for: {agent_id}")

    def unregister_agent_handler(self, agent_id: str):
        """Remove an agent's message handler."""
        self._agent_handlers.pop(agent_id, None)

    async def send(self, message: AgentMessage) -> bool:
        """Send a message to its recipient via the priority queue.

        Returns True if enqueued successfully, False if queue is full.
        """
        fingerprint = message.fingerprint()
        if fingerprint in self._processed_fingerprints:
            logger.debug(f"Duplicate message detected, skipping: {message.id}")
            return True

        if self._message_queue.qsize() >= self.MAX_QUEUE_SIZE:
            logger.warning(f"Message queue full ({self.MAX_QUEUE_SIZE}), dropping message {message.id}")
            return False

        priority_map = {
            MessagePriority.CRITICAL: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 3,
        }
        queue_priority = priority_map.get(message.priority, 2)

        await self._message_queue.put((queue_priority, message))
        self._processed_fingerprints.add(fingerprint)

        # Track delivery stats
        if message.sender_id not in self._delivery_stats:
            self._delivery_stats[message.sender_id] = {"sent": 0, "delivered": 0, "failed": 0}
        self._delivery_stats[message.sender_id]["sent"] += 1

        return True

    async def broadcast(self, message: AgentMessage, recipient_ids: list[str]) -> int:
        """Send a message to multiple recipients.

        Returns the number of recipients successfully enqueued.
        """
        delivered = 0
        for recipient_id in recipient_ids:
            msg_copy = AgentMessage(
                msg_type=message.msg_type,
                sender_id=message.sender_id,
                recipient_id=recipient_id,
                priority=message.priority,
                payload=message.payload.copy(),
                ttl_seconds=message.ttl_seconds,
                protocol_version=message.protocol_version,
                tags=message.tags.copy(),
            )
            msg_copy.thread_id = message.thread_id
            if await self.send(msg_copy):
                delivered += 1
        return delivered

    async def create_session(self, agent_a: str, agent_b: str) -> ProtocolSession:
        """Establish a communication session between two agents."""
        session_key = self._session_key(agent_a, agent_b)
        if session_key in self._sessions and self._sessions[session_key].is_active:
            return self._sessions[session_key]

        session = ProtocolSession(
            id=f"session-{uuid.uuid4().hex[:8]}",
            agent_a=agent_a,
            agent_b=agent_b,
        )
        self._sessions[session_key] = session
        logger.info(f"Protocol session established: {agent_a} <-> {agent_b} ({session.id})")
        return session

    def get_session(self, agent_a: str, agent_b: str) -> ProtocolSession | None:
        """Get an existing session between two agents."""
        return self._sessions.get(self._session_key(agent_a, agent_b))

    async def close_session(self, agent_a: str, agent_b: str):
        """Close a communication session."""
        session_key = self._session_key(agent_a, agent_b)
        session = self._sessions.get(session_key)
        if session:
            session.is_active = False
            logger.info(f"Protocol session closed: {agent_a} <-> {agent_b}")

    async def start_processing(self):
        """Start the background message processing loop."""
        if self._is_running:
            return
        self._is_running = True
        self._processor_task = asyncio.create_task(self._process_loop())
        logger.info("ACP message processor started")

    async def stop_processing(self):
        """Stop the background message processing loop."""
        self._is_running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("ACP message processor stopped")

    async def _process_loop(self):
        """Main message processing loop with priority queue consumption."""
        while self._is_running:
            try:
                _, message = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )

                # Check TTL
                if message.is_expired():
                    message.status = DeliveryStatus.EXPIRED
                    logger.debug(f"Message {message.id} expired")
                    continue

                # Route to recipient handler
                recipient_handler = self._agent_handlers.get(message.recipient_id)
                if recipient_handler:
                    try:
                        await recipient_handler(message)
                        message.status = DeliveryStatus.DELIVERED
                        message.delivered_at = datetime.now(timezone.utc).isoformat()
                    except Exception as e:
                        message.status = DeliveryStatus.FAILED
                        logger.error(f"Failed to deliver message {message.id}: {e}")

                        # Retry logic
                        if message.retry_count < message.max_retries:
                            message.retry_count += 1
                            await self._message_queue.put((message.retry_count, message))
                else:
                    # Route to type-based handlers
                    handlers = self._message_handlers.get(message.msg_type, [])
                    for handler in handlers:
                        try:
                            await handler(message)
                        except Exception as e:
                            logger.error(f"Handler failed for message {message.id}: {e}")
                    message.status = DeliveryStatus.DELIVERED

                # Update delivery stats
                if message.sender_id in self._delivery_stats:
                    self._delivery_stats[message.sender_id]["delivered"] += 1

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message processing error: {e}")

    def _session_key(self, agent_a: str, agent_b: str) -> str:
        """Generate a deterministic session key for two agents."""
        return ":".join(sorted([agent_a, agent_b]))

    async def cleanup_expired_sessions(self):
        """Remove sessions that have been inactive beyond the timeout."""
        now = datetime.now(timezone.utc)
        expired = []
        for key, session in self._sessions.items():
            last_activity = datetime.fromisoformat(session.last_activity)
            if (now - last_activity).total_seconds() > self.SESSION_TIMEOUT_SECONDS:
                expired.append(key)
        for key in expired:
            del self._sessions[key]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired protocol sessions")

    def get_stats(self) -> dict:
        return {
            "active_sessions": sum(1 for s in self._sessions.values() if s.is_active),
            "total_sessions": len(self._sessions),
            "queue_size": self._message_queue.qsize(),
            "registered_agents": len(self._agent_handlers),
            "registered_handlers": sum(len(v) for v in self._message_handlers.values()),
            "delivery_stats": self._delivery_stats,
            "is_processing": self._is_running,
        }

    def get_agent_stats(self, agent_id: str) -> dict:
        """Get communication stats for a specific agent."""
        sessions = sum(
            1 for s in self._sessions.values()
            if (s.agent_a == agent_id or s.agent_b == agent_id) and s.is_active
        )
        return {
            "agent_id": agent_id,
            "active_sessions": sessions,
            "delivery": self._delivery_stats.get(agent_id, {}),
        }


# Global protocol instance
acp = AgentCommunicationProtocol()