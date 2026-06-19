"""Buddy Agent Protocol — standardized communication layer for all agent components

Defines a unified protocol for inter-component communication, message
routing, event streaming, and state synchronization. Every component
in the Buddy ecosystem communicates through this protocol layer.
"""
from __future__ import annotations
import logging
import uuid
import json
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Optional
from collections import defaultdict

logger = logging.getLogger("buddy.protocol_layer")


# ---------------------------------------------------------------------------
# Protocol Types
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    """Types of messages in the protocol."""
    COMMAND = "command"           # Action requests
    EVENT = "event"               # State change notifications
    QUERY = "query"               # Information requests
    RESPONSE = "response"         # Query/command results
    STREAM = "stream"             # Streaming data chunks
    ERROR = "error"               # Error notifications
    HEARTBEAT = "heartbeat"       # Liveness checks
    SYNC = "sync"                 # State synchronization


class MessagePriority(str, Enum):
    """Message priority levels."""
    CRITICAL = "critical"    # Must be processed immediately
    HIGH = "high"            # Process before normal
    NORMAL = "normal"        # Standard processing
    LOW = "low"              # Background processing
    BATCH = "batch"          # Can be batched with others


class ComponentState(str, Enum):
    """States of a protocol component."""
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    DEGRADED = "degraded"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class ProtocolMessage:
    """Standard message format for all inter-component communication."""
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:12]}")
    message_type: MessageType = MessageType.EVENT
    source: str = ""          # Source component ID
    target: str = ""          # Target component ID (empty = broadcast)
    correlation_id: str | None = None  # For request-response pairing
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    ttl: int = 300  # Time-to-live in seconds

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "source": self.source,
            "target": self.target,
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "metadata": self.metadata,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProtocolMessage:
        return cls(
            message_id=data.get("message_id", ""),
            message_type=MessageType(data.get("message_type", "event")),
            source=data.get("source", ""),
            target=data.get("target", ""),
            correlation_id=data.get("correlation_id"),
            priority=MessagePriority(data.get("priority", "normal")),
            timestamp=data.get("timestamp", ""),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
            ttl=data.get("ttl", 300),
        )


# ---------------------------------------------------------------------------
# Message Router
# ---------------------------------------------------------------------------

HandlerType = Callable[[ProtocolMessage], Awaitable[Optional[dict[str, Any]]]]


class MessageRouter:
    """Routes messages between components based on type and target."""

    def __init__(self):
        self._handlers: dict[MessageType, list[HandlerType]] = defaultdict(list)
        self._target_handlers: dict[str, list[HandlerType]] = defaultdict(list)
        self._wildcard_handlers: list[HandlerType] = []
        self._message_queue: asyncio.Queue[ProtocolMessage] = asyncio.Queue(maxsize=10000)
        self._message_history: list[ProtocolMessage] = []
        self._max_history = 1000
        self._processed_count = 0
        self._error_count = 0
        self._is_running = False
        self._router_task: asyncio.Task | None = None

    def register(self, message_type: MessageType | None = None, target: str | None = None) -> Callable:
        """Decorator to register a message handler."""
        def decorator(func: HandlerType) -> HandlerType:
            if target:
                self._target_handlers[target].append(func)
            elif message_type:
                self._handlers[message_type].append(func)
            else:
                self._wildcard_handlers.append(func)
            return func
        return decorator

    def add_handler(self, handler: HandlerType, message_type: MessageType | None = None, target: str | None = None):
        """Add a handler function directly."""
        if target:
            self._target_handlers[target].append(handler)
        elif message_type:
            self._handlers[message_type].append(handler)
        else:
            self._wildcard_handlers.append(handler)

    async def route(self, message: ProtocolMessage) -> list[dict[str, Any]]:
        """Route a message to all matching handlers."""
        results = []

        # Route to type-specific handlers
        handlers = self._handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                result = await handler(message)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Handler error for {message.message_type}: {e}")
                self._error_count += 1

        # Route to target-specific handlers
        if message.target:
            target_handlers = self._target_handlers.get(message.target, [])
            for handler in target_handlers:
                try:
                    result = await handler(message)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Target handler error for {message.target}: {e}")
                    self._error_count += 1

        # Route to wildcard handlers
        for handler in self._wildcard_handlers:
            try:
                result = await handler(message)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Wildcard handler error: {e}")
                self._error_count += 1

        self._processed_count += 1
        self._record_message(message)
        return results

    async def publish(self, message: ProtocolMessage):
        """Publish a message to the queue for async processing."""
        await self._message_queue.put(message)

    async def start_router(self):
        """Start the background message processing loop."""
        self._is_running = True
        self._router_task = asyncio.create_task(self._process_loop())

    async def stop_router(self):
        """Stop the background message processing loop."""
        self._is_running = False
        if self._router_task:
            self._router_task.cancel()
            try:
                await self._router_task
            except asyncio.CancelledError:
                pass

    async def _process_loop(self):
        """Background loop for processing queued messages."""
        while self._is_running:
            try:
                message = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                await self.route(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Process loop error: {e}")

    def _record_message(self, message: ProtocolMessage):
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "queue_size": self._message_queue.qsize(),
            "registered_handlers": {
                mt.value: len(handlers) for mt, handlers in self._handlers.items()
            },
            "target_handlers": {
                target: len(handlers) for target, handlers in self._target_handlers.items()
            },
            "wildcard_handlers": len(self._wildcard_handlers),
            "is_running": self._is_running,
        }


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

EventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class EventBus:
    """Publish-subscribe event system for component communication."""

    def __init__(self):
        self._subscribers: dict[str, list[EventCallback]] = defaultdict(list)
        self._event_history: list[dict[str, Any]] = []
        self._max_history = 500
        self._total_events = 0

    def subscribe(self, event_type: str, callback: EventCallback):
        """Subscribe to an event type."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: EventCallback):
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    async def emit(self, event_type: str, data: dict[str, Any], source: str = ""):
        """Emit an event to all subscribers."""
        event = {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        self._total_events += 1

        # Notify subscribers
        callbacks = self._subscribers.get(event_type, [])
        for callback in callbacks:
            try:
                await callback(event_type, data)
            except Exception as e:
                logger.error(f"Event callback error for {event_type}: {e}")

        # Also notify wildcard subscribers
        wildcard_callbacks = self._subscribers.get("*", [])
        for callback in wildcard_callbacks:
            try:
                await callback(event_type, data)
            except Exception as e:
                logger.error(f"Wildcard event callback error: {e}")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": self._total_events,
            "subscriber_count": sum(len(subs) for subs in self._subscribers.values()),
            "event_types": list(self._subscribers.keys()),
            "recent_events": self._event_history[-10:],
        }


# ---------------------------------------------------------------------------
# Component Registry
# ---------------------------------------------------------------------------

@dataclass
class ComponentInfo:
    """Information about a registered component."""
    component_id: str
    component_type: str
    state: ComponentState = ComponentState.INITIALIZING
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    health_score: float = 1.0


class ComponentRegistry:
    """Registry of all agent components with health monitoring."""

    def __init__(self):
        self._components: dict[str, ComponentInfo] = {}
        self._health_check_interval = 30  # seconds

    def register(self, component_id: str, component_type: str, capabilities: list[str] | None = None, dependencies: list[str] | None = None, metadata: dict | None = None) -> ComponentInfo:
        """Register a new component."""
        info = ComponentInfo(
            component_id=component_id,
            component_type=component_type,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            metadata=metadata or {},
        )
        self._components[component_id] = info
        logger.info(f"Component registered: {component_id} ({component_type})")
        return info

    def unregister(self, component_id: str):
        """Remove a component from the registry."""
        self._components.pop(component_id, None)

    def update_state(self, component_id: str, state: ComponentState):
        """Update component state."""
        if component_id in self._components:
            self._components[component_id].state = state

    def heartbeat(self, component_id: str):
        """Record a heartbeat from a component."""
        if component_id in self._components:
            self._components[component_id].last_heartbeat = datetime.now(timezone.utc).isoformat()
            self._components[component_id].health_score = min(1.0, self._components[component_id].health_score + 0.05)

    def get_component(self, component_id: str) -> ComponentInfo | None:
        return self._components.get(component_id)

    def get_all_components(self) -> dict[str, ComponentInfo]:
        return dict(self._components)

    def get_by_type(self, component_type: str) -> list[ComponentInfo]:
        return [c for c in self._components.values() if c.component_type == component_type]

    def get_by_capability(self, capability: str) -> list[ComponentInfo]:
        return [c for c in self._components.values() if capability in c.capabilities]

    def check_health(self) -> dict[str, Any]:
        """Check health of all components."""
        now = datetime.now(timezone.utc)
        unhealthy = []
        degraded = []

        for cid, info in self._components.items():
            last_hb = datetime.fromisoformat(info.last_heartbeat)
            seconds_since_hb = (now - last_hb).total_seconds()

            if seconds_since_hb > self._health_check_interval * 2:
                info.health_score = max(0.0, info.health_score - 0.2)
                if info.health_score < 0.3:
                    unhealthy.append(cid)
                else:
                    degraded.append(cid)

        return {
            "total_components": len(self._components),
            "healthy": len(self._components) - len(unhealthy) - len(degraded),
            "degraded": degraded,
            "unhealthy": unhealthy,
            "components": {
                cid: {
                    "type": info.component_type,
                    "state": info.state.value,
                    "health": round(info.health_score, 2),
                }
                for cid, info in self._components.items()
            },
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_components": len(self._components),
            "components_by_type": self._count_by_type(),
            "health_summary": self.check_health(),
        }

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for info in self._components.values():
            counts[info.component_type] = counts.get(info.component_type, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# State Synchronizer
# ---------------------------------------------------------------------------

class StateSynchronizer:
    """Synchronizes state across distributed components."""

    def __init__(self):
        self._state_store: dict[str, dict[str, Any]] = {}
        self._version_counter: dict[str, int] = defaultdict(int)
        self._conflict_resolvers: dict[str, Callable] = {}

    def set_state(self, component_id: str, key: str, value: Any):
        """Set state for a component."""
        if component_id not in self._state_store:
            self._state_store[component_id] = {}
        self._state_store[component_id][key] = value
        self._version_counter[component_id] += 1

    def get_state(self, component_id: str, key: str, default: Any = None) -> Any:
        """Get state for a component."""
        return self._state_store.get(component_id, {}).get(key, default)

    def get_all_state(self, component_id: str) -> dict[str, Any]:
        """Get all state for a component."""
        return dict(self._state_store.get(component_id, {}))

    def sync_state(self, source_id: str, target_id: str, keys: list[str] | None = None):
        """Sync state from source to target component."""
        source_state = self._state_store.get(source_id, {})
        if keys:
            source_state = {k: v for k, v in source_state.items() if k in keys}

        if target_id not in self._state_store:
            self._state_store[target_id] = {}
        self._state_store[target_id].update(source_state)

    def get_version(self, component_id: str) -> int:
        return self._version_counter.get(component_id, 0)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_components": len(self._state_store),
            "total_keys": sum(len(state) for state in self._state_store.values()),
            "versions": dict(self._version_counter),
        }


# ---------------------------------------------------------------------------
# Protocol Engine — Main Coordinator
# ---------------------------------------------------------------------------

class ProtocolEngine:
    """Central protocol engine for the Buddy agent ecosystem.

    Manages all inter-component communication through a unified protocol
    layer, providing message routing, event publishing, component
    registration, and state synchronization.
    """

    def __init__(self):
        self.router = MessageRouter()
        self.events = EventBus()
        self.registry = ComponentRegistry()
        self.sync = StateSynchronizer()

    def register_component(self, component_id: str, component_type: str, capabilities: list[str] | None = None, dependencies: list[str] | None = None, metadata: dict | None = None) -> ComponentInfo:
        """Register a component and wire it into the protocol."""
        info = self.registry.register(
            component_id=component_id,
            component_type=component_type,
            capabilities=capabilities,
            dependencies=dependencies,
            metadata=metadata,
        )
        return info

    async def send_message(self, source: str, target: str, message_type: MessageType, payload: dict, priority: MessagePriority = MessagePriority.NORMAL, correlation_id: str | None = None) -> list[dict[str, Any]]:
        """Send a message through the protocol."""
        message = ProtocolMessage(
            message_type=message_type,
            source=source,
            target=target,
            priority=priority,
            payload=payload,
            correlation_id=correlation_id,
        )
        return await self.router.route(message)

    async def publish_message(self, source: str, target: str, message_type: MessageType, payload: dict, priority: MessagePriority = MessagePriority.NORMAL):
        """Publish a message async to the queue."""
        message = ProtocolMessage(
            message_type=message_type,
            source=source,
            target=target,
            priority=priority,
            payload=payload,
        )
        await self.router.publish(message)

    async def emit_event(self, event_type: str, data: dict, source: str = ""):
        """Emit an event to all subscribers."""
        await self.events.emit(event_type, data, source)

    def subscribe_to_event(self, event_type: str, callback: EventCallback):
        """Subscribe to an event type."""
        self.events.subscribe(event_type, callback)

    def get_global_stats(self) -> dict[str, Any]:
        return {
            "router": self.router.get_stats(),
            "events": self.events.get_stats(),
            "registry": self.registry.get_stats(),
            "synchronizer": self.sync.get_stats(),
        }


# Global instance
protocol_engine = ProtocolEngine()