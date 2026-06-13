"""Buddy Agent Communication Protocol — inter-agent messaging and negotiation

Provides a structured communication layer for agents to exchange messages,
coordinate tasks, negotiate roles, and share context. Supports both direct
peer-to-peer messaging and broadcast patterns through the platform hub.

Core capabilities:
  - Direct Messaging: point-to-point communication between agents
  - Broadcast: one-to-many announcements to all agents
  - Task Delegation: formal handoff of tasks with acceptance/rejection
  - Context Sharing: structured exchange of memory and knowledge
  - Negotiation: multi-round proposal/counter-proposal for task assignment
  - Message Routing: intelligent delivery based on agent roles and capabilities
  - Priority Queuing: messages prioritized by urgency and importance
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.comm_protocol")


class MessageType(str, Enum):
    """Types of inter-agent messages."""
    DIRECT = "direct"          # Point-to-point message
    BROADCAST = "broadcast"    # Announcement to all agents
    DELEGATE = "delegate"      # Task delegation request
    ACCEPT = "accept"          # Delegation acceptance
    REJECT = "reject"          # Delegation rejection
    QUERY = "query"            # Information request
    RESPONSE = "response"      # Information response
    CONTEXT_SHARE = "context_share"  # Shared memory/knowledge
    NEGOTIATE = "negotiate"    # Multi-round negotiation
    HEARTBEAT = "heartbeat"    # Liveness check
    STATUS = "status"          # Status update


class MessagePriority(str, Enum):
    """Priority levels for inter-agent messages."""
    CRITICAL = "critical"  # Must be processed immediately
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class MessageStatus(str, Enum):
    """Delivery and processing status of a message."""
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    PROCESSED = "processed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class AgentMessage:
    """A structured message between agents."""
    id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    msg_type: MessageType = MessageType.DIRECT
    sender_id: str = ""
    recipient_id: str = ""  # Empty for broadcast
    subject: str = ""
    content: str = ""
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    parent_msg_id: str = ""  # For threaded conversations
    correlation_id: str = ""  # For tracking related messages
    metadata: dict[str, Any] = field(default_factory=dict)
    ttl_seconds: int = 300  # Time-to-live
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    delivered_at: str = ""
    processed_at: str = ""


@dataclass
class DelegationRequest:
    """A formal task delegation request from one agent to another."""
    id: str = field(default_factory=lambda: f"del-{uuid.uuid4().hex[:8]}")
    from_agent_id: str = ""
    to_agent_id: str = ""
    task_description: str = ""
    task_context: dict[str, Any] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    deadline: str = ""  # ISO datetime
    priority: MessagePriority = MessagePriority.NORMAL
    status: str = "pending"  # pending, accepted, rejected, expired
    response_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ContextShare:
    """A structured context sharing payload between agents."""
    id: str = field(default_factory=lambda: f"ctx-{uuid.uuid4().hex[:8]}")
    from_agent_id: str = ""
    to_agent_id: str = ""
    context_type: str = "memory"  # memory, knowledge, insight, preference
    content: str = ""
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)
    expires_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentCommProtocol:
    """Inter-agent communication protocol with message routing, delivery tracking,
    and negotiation support.

    Enables agents to communicate as peers, delegate tasks, share context,
    and coordinate complex workflows across the platform.
    """

    def __init__(self):
        self._message_handlers: dict[MessageType, list[Callable[[AgentMessage], Awaitable[None]]]] = {}
        self._delegation_handlers: list[Callable[[DelegationRequest], Awaitable[bool]]] = []
        self._context_handlers: list[Callable[[ContextShare], Awaitable[None]]] = []
        self._message_history: list[AgentMessage] = []
        self._max_history = 500
        self._pending_delegations: dict[str, DelegationRequest] = {}
        self._agent_online_status: dict[str, bool] = {}
        self._agent_capabilities: dict[str, list[str]] = {}

    # ── Message Handling ──────────────────────────────────

    def register_handler(
        self,
        msg_type: MessageType,
        handler: Callable[[AgentMessage], Awaitable[None]],
    ):
        """Register a handler for a specific message type."""
        if msg_type not in self._message_handlers:
            self._message_handlers[msg_type] = []
        self._message_handlers[msg_type].append(handler)

    def register_delegation_handler(
        self,
        handler: Callable[[DelegationRequest], Awaitable[bool]],
    ):
        """Register a handler for delegation requests. Returns True if accepted."""
        self._delegation_handlers.append(handler)

    def register_context_handler(
        self,
        handler: Callable[[ContextShare], Awaitable[None]],
    ):
        """Register a handler for context sharing."""
        self._context_handlers.append(handler)

    async def send_message(self, msg: AgentMessage) -> AgentMessage:
        """Send a message and deliver it to the appropriate handlers."""
        self._message_history.append(msg)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]

        msg.status = MessageStatus.DELIVERED
        msg.delivered_at = datetime.now(timezone.utc).isoformat()

        if msg.msg_type in self._message_handlers:
            for handler in self._message_handlers[msg.msg_type]:
                try:
                    await handler(msg)
                except Exception as e:
                    logger.error(f"Message handler error for {msg.id}: {e}")

        # Also route to direct message handlers for targeted messages
        if msg.msg_type == MessageType.DIRECT and MessageType.DIRECT in self._message_handlers:
            for handler in self._message_handlers[MessageType.DIRECT]:
                try:
                    await handler(msg)
                except Exception as e:
                    logger.error(f"Direct message handler error for {msg.id}: {e}")

        msg.status = MessageStatus.PROCESSED
        msg.processed_at = datetime.now(timezone.utc).isoformat()
        return msg

    async def broadcast(
        self,
        sender_id: str,
        subject: str,
        content: str,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> AgentMessage:
        """Broadcast a message to all registered agents."""
        msg = AgentMessage(
            msg_type=MessageType.BROADCAST,
            sender_id=sender_id,
            subject=subject,
            content=content,
            priority=priority,
        )
        return await self.send_message(msg)

    async def direct_message(
        self,
        sender_id: str,
        recipient_id: str,
        subject: str,
        content: str,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> AgentMessage:
        """Send a direct message to a specific agent."""
        msg = AgentMessage(
            msg_type=MessageType.DIRECT,
            sender_id=sender_id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            priority=priority,
        )
        return await self.send_message(msg)

    # ── Task Delegation ───────────────────────────────────

    async def delegate_task(self, request: DelegationRequest) -> DelegationRequest:
        """Send a task delegation request and wait for acceptance."""
        self._pending_delegations[request.id] = request

        for handler in self._delegation_handlers:
            try:
                accepted = await handler(request)
                if accepted:
                    request.status = "accepted"
                    break
            except Exception as e:
                logger.error(f"Delegation handler error for {request.id}: {e}")

        if request.status == "pending":
            request.status = "rejected"
            request.response_reason = "No agent accepted the delegation"

        return request

    async def accept_delegation(self, delegation_id: str, reason: str = "") -> bool:
        """Accept a pending delegation."""
        if delegation_id in self._pending_delegations:
            self._pending_delegations[delegation_id].status = "accepted"
            self._pending_delegations[delegation_id].response_reason = reason
            return True
        return False

    async def reject_delegation(self, delegation_id: str, reason: str = "") -> bool:
        """Reject a pending delegation."""
        if delegation_id in self._pending_delegations:
            self._pending_delegations[delegation_id].status = "rejected"
            self._pending_delegations[delegation_id].response_reason = reason
            return True
        return False

    def get_pending_delegations(self, agent_id: str) -> list[DelegationRequest]:
        """Get all pending delegations for a specific agent."""
        return [
            d for d in self._pending_delegations.values()
            if d.to_agent_id == agent_id and d.status == "pending"
        ]

    # ── Context Sharing ───────────────────────────────────

    async def share_context(self, ctx: ContextShare) -> ContextShare:
        """Share context between agents."""
        for handler in self._context_handlers:
            try:
                await handler(ctx)
            except Exception as e:
                logger.error(f"Context share handler error for {ctx.id}: {e}")
        return ctx

    # ── Agent Registration ────────────────────────────────

    def register_agent(self, agent_id: str, capabilities: list[str] | None = None):
        """Register an agent with the communication protocol."""
        self._agent_online_status[agent_id] = True
        if capabilities:
            self._agent_capabilities[agent_id] = capabilities

    def unregister_agent(self, agent_id: str):
        """Unregister an agent from the communication protocol."""
        self._agent_online_status[agent_id] = False

    def is_agent_online(self, agent_id: str) -> bool:
        """Check if an agent is online."""
        return self._agent_online_status.get(agent_id, False)

    def get_agent_capabilities(self, agent_id: str) -> list[str]:
        """Get the capabilities of a registered agent."""
        return self._agent_capabilities.get(agent_id, [])

    def find_agents_by_capability(self, capability: str) -> list[str]:
        """Find agents that have a specific capability."""
        return [
            agent_id for agent_id, caps in self._agent_capabilities.items()
            if capability in caps and self._agent_online_status.get(agent_id, False)
        ]

    # ── Query/Response ────────────────────────────────────

    async def query_agent(
        self,
        sender_id: str,
        recipient_id: str,
        query: str,
        timeout_seconds: float = 30.0,
    ) -> str | None:
        """Send a query to an agent and wait for a response."""
        msg = AgentMessage(
            msg_type=MessageType.QUERY,
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=query,
            priority=MessagePriority.HIGH,
        )

        response_future: asyncio.Future[str] = asyncio.Future()

        async def response_handler(resp_msg: AgentMessage):
            if resp_msg.correlation_id == msg.id and not response_future.done():
                response_future.set_result(resp_msg.content)

        self.register_handler(MessageType.RESPONSE, response_handler)
        await self.send_message(msg)

        try:
            result = await asyncio.wait_for(response_future, timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Query to {recipient_id} timed out after {timeout_seconds}s")
            return None

    # ── Statistics ────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get communication protocol statistics."""
        return {
            "total_messages": len(self._message_history),
            "pending_delegations": sum(
                1 for d in self._pending_delegations.values() if d.status == "pending"
            ),
            "online_agents": sum(1 for v in self._agent_online_status.values() if v),
            "total_agents": len(self._agent_online_status),
            "message_types": {
                mt.value: sum(1 for m in self._message_history if m.msg_type == mt)
                for mt in MessageType
            },
        }

    def get_recent_messages(self, limit: int = 50) -> list[dict]:
        """Get recent messages in the history."""
        return [
            {
                "id": m.id,
                "type": m.msg_type.value,
                "sender": m.sender_id,
                "recipient": m.recipient_id,
                "subject": m.subject,
                "content": m.content[:200],
                "priority": m.priority.value,
                "status": m.status.value,
                "created_at": m.created_at,
            }
            for m in self._message_history[-limit:]
        ]


# Global instance
agent_comm = AgentCommProtocol()