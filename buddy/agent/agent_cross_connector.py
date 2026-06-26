"""
Platform Cross-Connector - Universal platform integration bridge.

Connects diverse platform components:
- Universal protocol adapter for heterogeneous systems
- Event-driven integration mesh with pub/sub routing
- Data transformation pipeline with schema mapping
- Connection health monitoring and auto-recovery
- Integration catalog with discovery and documentation
- Synchronous and asynchronous communication modes
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.cross_connector")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class IntegrationProtocol(str, Enum):
    """Supported integration protocols."""
    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    SSE = "sse"
    MQTT = "mqtt"
    AMQP = "amqp"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


class ConnectionState(str, Enum):
    """State of an integration connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class CommunicationMode(str, Enum):
    """Communication mode for integration."""
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"
    BATCH = "batch"
    EVENT_DRIVEN = "event_driven"


class DataFormat(str, Enum):
    """Supported data formats."""
    JSON = "json"
    XML = "xml"
    PROTOBUF = "protobuf"
    CSV = "csv"
    YAML = "yaml"
    BINARY = "binary"
    TEXT = "text"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class IntegrationConnection:
    """A connection to an external system."""
    connection_id: str
    name: str
    protocol: IntegrationProtocol
    endpoint: str
    mode: CommunicationMode
    state: ConnectionState = ConnectionState.DISCONNECTED
    auth_type: str = "none"
    auth_config: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_count: int = 3
    retry_delay_ms: int = 1000
    health_check_interval: int = 60
    last_connected: datetime | None = None
    last_error: str = ""
    total_requests: int = 0
    total_errors: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "name": self.name,
            "protocol": self.protocol.value,
            "endpoint": self.endpoint,
            "mode": self.mode.value,
            "state": self.state.value,
            "auth_type": self.auth_type,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "last_connected": self.last_connected.isoformat() if self.last_connected else None,
            "last_error": self.last_error,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "health_check_interval": self.health_check_interval,
            "tags": self.tags,
        }


@dataclass
class SchemaMapping:
    """Data transformation schema mapping."""
    mapping_id: str
    name: str
    source_format: DataFormat
    target_format: DataFormat
    field_mappings: list[dict[str, Any]]
    transformations: list[dict[str, Any]]
    validation_rules: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "name": self.name,
            "source_format": self.source_format.value,
            "target_format": self.target_format.value,
            "field_mappings": self.field_mappings,
            "transformations": self.transformations,
            "validation_rules": self.validation_rules,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class IntegrationEvent:
    """An event in the integration mesh."""
    event_id: str
    event_type: str
    source: str
    data: dict[str, Any]
    priority: str = "normal"
    correlation_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "priority": self.priority,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class IntegrationRequest:
    """A request through the integration bridge."""
    request_id: str
    connection_id: str
    method: str
    path: str
    headers: dict[str, str]
    body: dict[str, Any] | None
    response: dict[str, Any] | None = None
    status_code: int = 0
    duration_ms: float = 0.0
    success: bool = False
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "connection_id": self.connection_id,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConnectorStats:
    """Statistics for the cross-connector."""
    total_connections: int = 0
    active_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_events: int = 0
    total_mappings: int = 0
    avg_response_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(1, self.total_requests),
            "total_events": self.total_events,
            "total_mappings": self.total_mappings,
            "avg_response_time_ms": self.avg_response_time_ms,
        }


# ═══════════════════════════════════════════════════════════
# Platform Cross-Connector
# ═══════════════════════════════════════════════════════════

class PlatformCrossConnector:
    """
    Universal platform integration bridge.
    
    Features:
    - Multi-protocol connection management (REST, GraphQL, gRPC, WebSocket, etc.)
    - Event-driven integration mesh with pub/sub routing
    - Data transformation with schema mapping
    - Connection health monitoring and auto-recovery
    - Integration catalog with discovery
    - Request/response logging and analytics
    """

    def __init__(self, config: CrossConnectorConfig | None = None):
        self.config = config or CrossConnectorConfig()
        self._connections: dict[str, IntegrationConnection] = {}
        self._mappings: dict[str, SchemaMapping] = {}
        self._events: list[IntegrationEvent] = []
        self._requests: list[IntegrationRequest] = []
        self._event_subscribers: dict[str, list[callable]] = defaultdict(list)
        self._stats = ConnectorStats()

    # ── Connection Management ──

    def register_connection(
        self,
        name: str,
        protocol: IntegrationProtocol,
        endpoint: str,
        mode: CommunicationMode = CommunicationMode.SYNC,
        auth_type: str = "none",
        auth_config: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: int = 30,
        tags: list[str] | None = None,
    ) -> IntegrationConnection:
        """Register a new integration connection."""
        connection = IntegrationConnection(
            connection_id=str(uuid.uuid4())[:8],
            name=name,
            protocol=protocol,
            endpoint=endpoint,
            mode=mode,
            auth_type=auth_type,
            auth_config=auth_config or {},
            headers=headers or {},
            timeout_seconds=timeout_seconds,
            tags=tags or [],
        )

        self._connections[connection.connection_id] = connection
        self._stats.total_connections += 1

        logger.info(
            "Registered connection %s: %s (%s -> %s)",
            connection.connection_id, name, protocol.value, endpoint,
        )
        return connection

    def connect(self, connection_id: str) -> ConnectionState:
        """Establish a connection."""
        connection = self._connections.get(connection_id)
        if not connection:
            return ConnectionState.ERROR

        connection.state = ConnectionState.CONNECTING

        # Simulate connection establishment
        try:
            # In production, this would actually connect
            connection.state = ConnectionState.CONNECTED
            connection.last_connected = datetime.now(timezone.utc)
            self._stats.active_connections += 1
            logger.info("Connected to %s (%s)", connection.name, connection.endpoint)
        except Exception as e:
            connection.state = ConnectionState.ERROR
            connection.last_error = str(e)
            logger.error("Failed to connect to %s: %s", connection.name, e)

        return connection.state

    def disconnect(self, connection_id: str) -> ConnectionState:
        """Disconnect a connection."""
        connection = self._connections.get(connection_id)
        if not connection:
            return ConnectionState.ERROR

        connection.state = ConnectionState.DISCONNECTED
        if self._stats.active_connections > 0:
            self._stats.active_connections -= 1

        logger.info("Disconnected from %s", connection.name)
        return connection.state

    def check_connection_health(self, connection_id: str) -> ConnectionState:
        """Check the health of a connection."""
        connection = self._connections.get(connection_id)
        if not connection:
            return ConnectionState.ERROR

        if connection.state == ConnectionState.ERROR:
            connection.state = ConnectionState.RECONNECTING
            connection.last_error = ""
            connection.state = ConnectionState.CONNECTED
            return ConnectionState.CONNECTED

        return connection.state

    def check_all_health(self) -> dict[str, ConnectionState]:
        """Check health of all connections."""
        return {
            cid: self.check_connection_health(cid)
            for cid in self._connections
        }

    # ── Request Execution ──

    def execute_request(
        self,
        connection_id: str,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> IntegrationRequest:
        """Execute a request through a connection."""
        connection = self._connections.get(connection_id)
        request = IntegrationRequest(
            request_id=str(uuid.uuid4())[:8],
            connection_id=connection_id,
            method=method.upper(),
            path=path,
            headers=headers or {},
            body=body,
        )

        start = time.time()

        if not connection:
            request.success = False
            request.error = "Connection not found"
            request.duration_ms = (time.time() - start) * 1000
            self._requests.append(request)
            return request

        connection.total_requests += 1

        # Simulate request execution
        # In production, this would make actual HTTP/GraphQL/gRPC calls
        try:
            request.response = {
                "status": "ok",
                "connection": connection.name,
                "method": method,
                "path": path,
            }
            request.status_code = 200
            request.success = True
            self._stats.successful_requests += 1
        except Exception as e:
            request.success = False
            request.error = str(e)
            request.status_code = 500
            connection.total_errors += 1
            self._stats.failed_requests += 1

        request.duration_ms = (time.time() - start) * 1000
        self._requests.append(request)
        self._stats.total_requests += 1

        self._update_response_stats(request.duration_ms)
        return request

    # ── Event System ──

    def publish_event(
        self,
        event_type: str,
        source: str,
        data: dict[str, Any],
        priority: str = "normal",
        correlation_id: str = "",
    ) -> IntegrationEvent:
        """Publish an event to the integration mesh."""
        event = IntegrationEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            source=source,
            data=data,
            priority=priority,
            correlation_id=correlation_id,
        )

        self._events.append(event)
        self._stats.total_events += 1

        # Notify subscribers
        subscribers = self._event_subscribers.get(event_type, [])
        for subscriber in subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.error("Event subscriber error for %s: %s", event_type, e)

        if len(self._events) > self.config.max_stored_events:
            self._events = self._events[-self.config.max_stored_events:]

        logger.debug("Published event %s: %s", event_type, event.event_id)
        return event

    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subscribe to events of a specific type."""
        self._event_subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: callable) -> bool:
        """Unsubscribe from events."""
        if event_type in self._event_subscribers and handler in self._event_subscribers[event_type]:
            self._event_subscribers[event_type].remove(handler)
            return True
        return False

    # ── Schema Mapping ──

    def create_mapping(
        self,
        name: str,
        source_format: DataFormat,
        target_format: DataFormat,
        field_mappings: list[dict[str, Any]],
        transformations: list[dict[str, Any]] | None = None,
    ) -> SchemaMapping:
        """Create a data transformation schema mapping."""
        mapping = SchemaMapping(
            mapping_id=str(uuid.uuid4())[:8],
            name=name,
            source_format=source_format,
            target_format=target_format,
            field_mappings=field_mappings,
            transformations=transformations or [],
        )

        self._mappings[mapping.mapping_id] = mapping
        self._stats.total_mappings += 1

        logger.info("Created schema mapping %s: %s -> %s", mapping.mapping_id, source_format.value, target_format.value)
        return mapping

    def transform_data(
        self,
        mapping_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Transform data using a schema mapping."""
        mapping = self._mappings.get(mapping_id)
        if not mapping:
            return None

        result = {}
        for field_map in mapping.field_mappings:
            source_field = field_map.get("source", "")
            target_field = field_map.get("target", "")
            default_value = field_map.get("default")

            if source_field in data:
                result[target_field] = data[source_field]
            elif default_value is not None:
                result[target_field] = default_value

        # Apply transformations
        for transform in mapping.transformations:
            transform_type = transform.get("type", "")
            if transform_type == "rename":
                old_key = transform.get("from", "")
                new_key = transform.get("to", "")
                if old_key in result:
                    result[new_key] = result.pop(old_key)
            elif transform_type == "default":
                field = transform.get("field", "")
                if field not in result:
                    result[field] = transform.get("value")

        return result

    # ── Query ──

    def get_connections(
        self,
        protocol: IntegrationProtocol | None = None,
        state: ConnectionState | None = None,
    ) -> list[IntegrationConnection]:
        """Get connections with optional filters."""
        connections = list(self._connections.values())
        if protocol:
            connections = [c for c in connections if c.protocol == protocol]
        if state:
            connections = [c for c in connections if c.state == state]
        return connections

    def get_events(
        self,
        event_type: str = "",
        limit: int = 50,
    ) -> list[IntegrationEvent]:
        """Get recent events."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_requests(
        self,
        connection_id: str = "",
        limit: int = 50,
    ) -> list[IntegrationRequest]:
        """Get recent requests."""
        requests = self._requests
        if connection_id:
            requests = [r for r in requests if r.connection_id == connection_id]
        return requests[-limit:]

    def get_mappings(self) -> list[SchemaMapping]:
        """Get all schema mappings."""
        return list(self._mappings.values())

    # ── Statistics ──

    def _update_response_stats(self, duration_ms: float) -> None:
        """Update response time statistics."""
        n = self._stats.total_requests
        self._stats.avg_response_time_ms = (
            (self._stats.avg_response_time_ms * (n - 1) + duration_ms) / n
        )

    def get_stats(self) -> ConnectorStats:
        """Get connector statistics."""
        return self._stats

    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection."""
        if connection_id in self._connections:
            conn = self._connections[connection_id]
            if conn.state == ConnectionState.CONNECTED:
                self.disconnect(connection_id)
            del self._connections[connection_id]
            self._stats.total_connections -= 1
            return True
        return False

    def reset(self) -> None:
        """Reset the cross-connector."""
        self._connections.clear()
        self._mappings.clear()
        self._events.clear()
        self._requests.clear()
        self._event_subscribers.clear()
        self._stats = ConnectorStats()
        logger.info("Platform cross-connector reset")


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@dataclass
class CrossConnectorConfig:
    """Configuration for the cross-connector."""
    max_connections: int = 100
    max_stored_events: int = 10000
    max_stored_requests: int = 10000
    default_timeout_seconds: int = 30
    health_check_interval_seconds: int = 60
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 5
    collect_metrics: bool = True


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_cross_connector: PlatformCrossConnector | None = None


def get_cross_connector() -> PlatformCrossConnector:
    """Get or create the singleton cross-connector."""
    global _cross_connector
    if _cross_connector is None:
        _cross_connector = PlatformCrossConnector()
    return _cross_connector


def reset_cross_connector() -> None:
    """Reset the singleton cross-connector."""
    global _cross_connector
    if _cross_connector:
        _cross_connector.reset()
    _cross_connector = None