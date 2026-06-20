"""
Buddy Event Pipeline - Unified event-driven architecture.

Provides a centralized event pipeline that connects all Buddy modules
through a publish-subscribe pattern. Enables loose coupling between
components while maintaining real-time event propagation with filtering,
transformation, and persistence.

Key capabilities:
- Topic-based publish-subscribe with wildcard matching
- Event filtering and transformation middleware
- Event persistence and replay
- Dead letter queue for failed event processing
- Event correlation and tracing
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class EventSource(str, Enum):
    """Source components that generate events."""
    AGENT_CORE = "agent_core"
    ORCHESTRATOR = "orchestrator"
    TOOL_EXECUTOR = "tool_executor"
    MEMORY_SYSTEM = "memory_system"
    SKILL_ENGINE = "skill_engine"
    WEB_FRONTEND = "web_frontend"
    API_GATEWAY = "api_gateway"
    MCP_CONNECTOR = "mcp_connector"
    FLEET_MANAGER = "fleet_manager"
    REFLECTION_ENGINE = "reflection_engine"
    INTENT_ENGINE = "intent_engine"
    SANDBOX = "sandbox"
    DEPLOYMENT = "deployment"


class EventPriority(str, Enum):
    """Priority levels for events."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PipelineEvent:
    """An event flowing through the pipeline."""
    event_id: str
    topic: str
    source: EventSource
    priority: EventPriority
    payload: dict[str, Any]
    correlation_id: str | None = None
    parent_event_id: str | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class EventSubscription:
    """A subscription to an event topic."""
    subscription_id: str
    topic_pattern: str
    handler: Callable
    priority: EventPriority = EventPriority.NORMAL
    filter_fn: Callable | None = None
    is_async: bool = False
    created_at: float = field(default_factory=time.time)


@dataclass
class DeadLetterEntry:
    """An event that failed processing and was moved to dead letter queue."""
    entry_id: str
    event: PipelineEvent
    error: str
    subscription_id: str
    failed_at: float = field(default_factory=time.time)
    retry_count: int = 0


class EventPipeline:
    """Central event pipeline for the Buddy platform.

    Routes events between all system components using a pub-sub model.
    Supports topic-based routing with wildcard patterns, event filtering,
    transformation middleware, and dead letter queuing for reliability.
    """

    def __init__(self):
        self._subscriptions: dict[str, list[EventSubscription]] = defaultdict(list)
        self._event_history: list[PipelineEvent] = []
        self._dead_letter_queue: list[DeadLetterEntry] = []
        self._middleware: list[Callable] = []
        self._correlation_map: dict[str, list[str]] = defaultdict(list)
        self._total_events = 0
        self._total_published = 0
        self._total_delivered = 0
        self._total_failed = 0
        self._max_history = 10000

    def subscribe(
        self,
        topic_pattern: str,
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        filter_fn: Callable | None = None,
        is_async: bool = False,
    ) -> str:
        """Subscribe to events matching a topic pattern.

        Topic patterns support wildcards:
        - 'agent.*' matches all agent events
        - 'agent.core.output' matches exact topic
        - '*.error' matches all error events
        """
        subscription_id = f"sub-{uuid.uuid4().hex[:12]}"
        subscription = EventSubscription(
            subscription_id=subscription_id,
            topic_pattern=topic_pattern,
            handler=handler,
            priority=priority,
            filter_fn=filter_fn,
            is_async=is_async,
        )
        self._subscriptions[topic_pattern].append(subscription)
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by ID."""
        for pattern, subs in list(self._subscriptions.items()):
            self._subscriptions[pattern] = [
                s for s in subs if s.subscription_id != subscription_id
            ]
            if not self._subscriptions[pattern]:
                del self._subscriptions[pattern]
        return True

    def add_middleware(self, middleware_fn: Callable) -> None:
        """Add a middleware function to process events before delivery."""
        self._middleware.append(middleware_fn)

    async def publish(
        self,
        topic: str,
        source: EventSource,
        payload: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: str | None = None,
        parent_event_id: str | None = None,
    ) -> PipelineEvent:
        """Publish an event to the pipeline."""
        event = PipelineEvent(
            event_id=f"evt-{uuid.uuid4().hex[:12]}",
            topic=topic,
            source=source,
            priority=priority,
            payload=payload,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id,
        )

        self._total_published += 1

        # Run middleware
        for mw in self._middleware:
            try:
                event = mw(event) or event
            except Exception:
                pass

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        # Track correlation
        if correlation_id:
            self._correlation_map[correlation_id].append(event.event_id)

        # Deliver to matching subscribers
        await self._deliver(event)

        self._total_events += 1
        return event

    async def publish_and_wait(
        self,
        topic: str,
        source: EventSource,
        payload: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        timeout: float = 30.0,
    ) -> list[Any]:
        """Publish an event and collect responses from all subscribers."""
        event = await self.publish(topic, source, payload, priority)
        matching = self._find_matching_subscriptions(topic)

        results = []
        for sub in matching:
            try:
                if sub.is_async:
                    result = await asyncio.wait_for(
                        sub.handler(event) if asyncio.iscoroutinefunction(sub.handler)
                        else asyncio.to_thread(sub.handler, event),
                        timeout=timeout,
                    )
                else:
                    result = sub.handler(event)
                results.append(result)
            except asyncio.TimeoutError:
                results.append(None)
            except Exception as e:
                self._handle_failure(event, sub, str(e))

        return results

    def get_history(
        self,
        topic: str | None = None,
        source: EventSource | None = None,
        limit: int = 100,
    ) -> list[PipelineEvent]:
        """Get event history with optional filtering."""
        events = self._event_history
        if topic:
            events = [e for e in events if self._topic_matches(e.topic, topic)]
        if source:
            events = [e for e in events if e.source == source]
        return events[-limit:]

    def get_correlated_events(self, correlation_id: str) -> list[PipelineEvent]:
        """Get all events correlated by correlation ID."""
        event_ids = self._correlation_map.get(correlation_id, [])
        return [e for e in self._event_history if e.event_id in event_ids]

    def get_dead_letter(self, limit: int = 50) -> list[DeadLetterEntry]:
        """Get dead letter queue entries."""
        return self._dead_letter_queue[-limit:]

    def replay_dead_letter(self, entry_id: str) -> bool:
        """Replay a dead letter event."""
        for entry in self._dead_letter_queue:
            if entry.entry_id == entry_id:
                entry.event.retry_count += 1
                if entry.event.retry_count <= entry.event.max_retries:
                    asyncio.create_task(self._deliver(entry.event))
                    self._dead_letter_queue.remove(entry)
                    return True
        return False

    def get_stats(self) -> dict:
        """Get event pipeline statistics."""
        return {
            "total_events": self._total_events,
            "total_published": self._total_published,
            "total_delivered": self._total_delivered,
            "total_failed": self._total_failed,
            "dead_letter_count": len(self._dead_letter_queue),
            "active_subscriptions": sum(
                len(subs) for subs in self._subscriptions.values()
            ),
            "topic_count": len(self._subscriptions),
            "history_size": len(self._event_history),
            "topics": list(self._subscriptions.keys()),
            "recent_events": [
                {
                    "event_id": e.event_id,
                    "topic": e.topic,
                    "source": e.source.value,
                    "priority": e.priority.value,
                    "timestamp": e.timestamp,
                }
                for e in self._event_history[-10:]
            ],
        }

    async def _deliver(self, event: PipelineEvent) -> None:
        """Deliver an event to all matching subscribers."""
        matching = self._find_matching_subscriptions(event.topic)
        matching.sort(key=lambda s: {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }[s.priority])

        for sub in matching:
            if sub.filter_fn and not sub.filter_fn(event):
                continue
            try:
                if sub.is_async and asyncio.iscoroutinefunction(sub.handler):
                    await sub.handler(event)
                elif sub.is_async:
                    await asyncio.to_thread(sub.handler, event)
                else:
                    sub.handler(event)
                self._total_delivered += 1
            except Exception as e:
                self._handle_failure(event, sub, str(e))

    def _find_matching_subscriptions(
        self, topic: str
    ) -> list[EventSubscription]:
        """Find all subscriptions matching a topic."""
        matching: list[EventSubscription] = []
        for pattern, subs in self._subscriptions.items():
            if self._topic_matches(topic, pattern):
                matching.extend(subs)
        return matching

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if a topic matches a pattern with wildcard support."""
        if pattern == "*":
            return True
        if pattern == topic:
            return True

        topic_parts = topic.split(".")
        pattern_parts = pattern.split(".")

        if len(pattern_parts) > len(topic_parts):
            return False

        for i, pp in enumerate(pattern_parts):
            if i >= len(topic_parts):
                return False
            if pp == "*":
                continue
            if pp == "**":
                return True
            if pp != topic_parts[i]:
                return False

        return len(pattern_parts) == len(topic_parts)

    def _handle_failure(
        self, event: PipelineEvent, sub: EventSubscription, error: str
    ) -> None:
        """Handle a failed event delivery."""
        self._total_failed += 1
        entry = DeadLetterEntry(
            entry_id=f"dlq-{uuid.uuid4().hex[:12]}",
            event=event,
            error=error,
            subscription_id=sub.subscription_id,
        )
        self._dead_letter_queue.append(entry)


# Global singleton
event_pipeline = EventPipeline()