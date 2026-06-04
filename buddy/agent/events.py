"""Buddy Event Bus — decoupled event-driven communication

Provides a lightweight publish-subscribe event system for internal
decoupling between agent subsystems, API layers, and background workers.
"""
from __future__ import annotations
import logging
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.events")


class EventType(str, Enum):
    """Standard event types in the Buddy platform."""
    # Agent lifecycle
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    AGENT_ONLINE = "agent.online"
    AGENT_OFFLINE = "agent.offline"

    # Conversation
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_DELETED = "conversation.deleted"
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"

    # Task
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Memory
    MEMORY_STORED = "memory.stored"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_CONSOLIDATED = "memory.consolidated"

    # Dream
    DREAM_CYCLE_STARTED = "dream.cycle_started"
    DREAM_CYCLE_COMPLETED = "dream.cycle_completed"
    DREAM_INSIGHT_GENERATED = "dream.insight_generated"

    # Autopilot
    AUTOPILOT_RUN_STARTED = "autopilot.run_started"
    AUTOPILOT_RUN_COMPLETED = "autopilot.run_completed"
    AUTOPILOT_RUN_FAILED = "autopilot.run_failed"

    # SubAgent
    SUBAGENT_SPAWNED = "subagent.spawned"
    SUBAGENT_COMPLETED = "subagent.completed"
    SUBAGENT_FAILED = "subagent.failed"

    # Collaboration
    COLLABORATION_STARTED = "collaboration.started"
    COLLABORATION_COMPLETED = "collaboration.completed"

    # Tool
    TOOL_CALLED = "tool.called"
    TOOL_APPROVED = "tool.approved"
    TOOL_DENIED = "tool.denied"

    # System
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class Event:
    """An event in the Buddy platform."""
    type: EventType
    source: str = ""
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = ""

    def __post_init__(self):
        import uuid
        if not self.id:
            self.id = f"evt-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Lightweight publish-subscribe event bus for internal decoupling."""

    def __init__(self):
        self._listeners: dict[EventType, list[EventHandler]] = {}
        self._global_listeners: list[EventHandler] = []
        self._event_history: list[Event] = []
        self._max_history = 500
        self._publish_tasks: set[asyncio.Task] = set()

    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe to a specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)
        logger.debug(f"Event listener added for {event_type.value}")

    def subscribe_all(self, handler: EventHandler):
        """Subscribe to all event types."""
        self._global_listeners.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """Remove a subscription."""
        if event_type in self._listeners:
            self._listeners[event_type] = [
                h for h in self._listeners[event_type] if h != handler
            ]

    def publish(self, event: Event):
        """Publish an event synchronously (fire and forget)."""
        task = asyncio.create_task(self._publish_async(event))
        self._publish_tasks.add(task)
        task.add_done_callback(self._publish_tasks.discard)

    async def publish_and_wait(self, event: Event):
        """Publish an event and wait for all listeners to complete."""
        await self._publish_async(event)

    async def _publish_async(self, event: Event):
        """Internal async publish implementation."""
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        # Notify type-specific listeners
        listeners = self._listeners.get(event.type, [])
        tasks = []

        for handler in listeners:
            tasks.append(self._safe_invoke(handler, event))

        for handler in self._global_listeners:
            tasks.append(self._safe_invoke(handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_invoke(self, handler: EventHandler, event: Event):
        """Safely invoke a handler, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Event handler error for {event.type.value}: {e}")

    def get_history(self, event_type: EventType | None = None, limit: int = 50) -> list[dict]:
        """Get recent event history."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return [e.to_dict() for e in events[-limit:]]

    def get_stats(self) -> dict:
        """Get event bus statistics."""
        type_counts: dict[str, int] = {}
        for event in self._event_history:
            key = event.type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        return {
            "total_events": len(self._event_history),
            "listener_count": sum(len(v) for v in self._listeners.values()) + len(self._global_listeners),
            "type_counts": type_counts,
            "pending_tasks": len(self._publish_tasks),
        }

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()


event_bus = EventBus()