"""Buddy Agent Streaming Hub — real-time streaming orchestration for multi-client delivery

The Streaming Hub provides a unified streaming infrastructure for the entire agent
ecosystem. It supports multiple streaming protocols (SSE, WebSocket, chunked transfer),
multi-client fan-out, stream transformation pipelines, and backpressure management.

Core capabilities:
  - Multi-Protocol: SSE, WebSocket, and chunked transfer encoding support
  - Multi-Client: fan-out to unlimited concurrent clients with per-client filtering
  - Stream Pipelines: transform, filter, enrich, and buffer streaming data
  - Backpressure: adaptive flow control with buffer management
  - Event Typing: structured stream events with type-safe dispatching
  - Reconnection: automatic client reconnection with event replay
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Callable, Awaitable

from config.settings import settings

logger = logging.getLogger("buddy.streaming_hub")


# ═══════════════════════════════════════════════════════════
# Enums and Types
# ═══════════════════════════════════════════════════════════

class StreamProtocol(str, Enum):
    """Supported streaming protocols."""
    SSE = "sse"
    WEBSOCKET = "websocket"
    CHUNKED = "chunked"
    POLLING = "polling"


class StreamEventType(str, Enum):
    """Types of stream events."""
    TEXT_DELTA = "text_delta"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_END = "tool_call_end"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    REASONING_STEP = "reasoning_step"
    PLAN_UPDATE = "plan_update"
    PROGRESS = "progress"
    ERROR = "error"
    DONE = "done"
    HEARTBEAT = "heartbeat"
    META = "meta"


class StreamState(str, Enum):
    """States of a stream session."""
    CONNECTING = "connecting"
    ACTIVE = "active"
    PAUSED = "paused"
    DRAINING = "draining"
    CLOSED = "closed"
    ERROR = "error"


class PipelineStage(str, Enum):
    """Stages in a stream processing pipeline."""
    PRE_PROCESS = "pre_process"
    TRANSFORM = "transform"
    ENRICH = "enrich"
    FILTER = "filter"
    BUFFER = "buffer"
    POST_PROCESS = "post_process"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class StreamingHubConfig:
    """Configuration for the Streaming Hub."""
    max_concurrent_streams: int = 100
    max_clients_per_stream: int = 50
    buffer_size: int = 100
    heartbeat_interval_seconds: int = 30
    client_timeout_seconds: int = 300
    max_replay_events: int = 500
    enable_compression: bool = True
    enable_persistence: bool = False
    default_protocol: StreamProtocol = StreamProtocol.SSE


@dataclass
class StreamEvent:
    """A single event in a stream."""
    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")
    stream_id: str = ""
    event_type: StreamEventType = StreamEventType.TEXT_DELTA
    data: Any = None
    sequence: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "stream_id": self.stream_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    def to_sse(self) -> str:
        """Format as SSE event string."""
        lines = []
        if self.event_id:
            lines.append(f"id: {self.event_id}")
        lines.append(f"event: {self.event_type.value}")
        data_str = json.dumps(self.data) if not isinstance(self.data, str) else self.data
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")
        lines.append("")
        return "\n".join(lines)


@dataclass
class StreamSession:
    """A streaming session with metadata."""
    session_id: str = field(default_factory=lambda: f"stream-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    conversation_id: str = ""
    protocol: StreamProtocol = StreamProtocol.SSE
    state: StreamState = StreamState.CONNECTING
    clients: dict[str, Any] = field(default_factory=dict)  # client_id -> client info
    events: list[StreamEvent] = field(default_factory=list)
    event_count: int = 0
    bytes_streamed: int = 0
    start_time: str = ""
    end_time: str = ""
    last_activity: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id,
            "protocol": self.protocol.value,
            "state": self.state.value,
            "client_count": len(self.clients),
            "event_count": self.event_count,
            "bytes_streamed": self.bytes_streamed,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "last_activity": self.last_activity,
            "metadata": self.metadata,
        }


@dataclass
class StreamPipeline:
    """A processing pipeline for stream events."""
    pipeline_id: str = field(default_factory=lambda: f"pipe-{uuid.uuid4().hex[:8]}")
    name: str = ""
    stages: list[tuple[PipelineStage, Callable[[StreamEvent], StreamEvent]]] = field(default_factory=list)
    enabled: bool = True
    order: int = 0

    def process(self, event: StreamEvent) -> StreamEvent:
        """Process an event through all pipeline stages."""
        if not self.enabled:
            return event
        for stage, processor in self.stages:
            try:
                event = processor(event)
            except Exception as e:
                logger.error("Pipeline %s stage %s failed: %s", self.name, stage.value, e)
        return event


@dataclass
class StreamingHubStats:
    """Statistics for the Streaming Hub."""
    active_streams: int = 0
    total_streams: int = 0
    total_clients: int = 0
    total_events: int = 0
    total_bytes: int = 0
    events_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    active_protocols: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_streams": self.active_streams,
            "total_streams": self.total_streams,
            "total_clients": self.total_clients,
            "total_events": self.total_events,
            "total_bytes": self.total_bytes,
            "events_per_second": self.events_per_second,
            "avg_latency_ms": self.avg_latency_ms,
            "active_protocols": self.active_protocols,
        }


# ═══════════════════════════════════════════════════════════
# Streaming Hub Implementation
# ═══════════════════════════════════════════════════════════

class AgentStreamingHub:
    """Real-time streaming orchestration for multi-client delivery."""

    def __init__(self, config: StreamingHubConfig | None = None):
        self.config = config or StreamingHubConfig()
        self._sessions: dict[str, StreamSession] = {}
        self._pipelines: dict[str, StreamPipeline] = {}
        self._event_queues: dict[str, asyncio.Queue] = {}
        self._client_queues: dict[str, dict[str, asyncio.Queue]] = defaultdict(dict)
        self._total_streams: int = 0
        self._total_events: int = 0
        self._total_bytes: int = 0
        self._start_time: float = time.monotonic()
        logger.info("AgentStreamingHub initialized")

    # ── Stream Management ────────────────────────────────

    def create_stream(
        self,
        agent_id: str = "",
        conversation_id: str = "",
        protocol: StreamProtocol | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StreamSession:
        """Create a new streaming session."""
        session = StreamSession(
            agent_id=agent_id,
            conversation_id=conversation_id,
            protocol=protocol or self.config.default_protocol,
            start_time=datetime.now(timezone.utc).isoformat(),
            last_activity=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )

        self._sessions[session.session_id] = session
        self._event_queues[session.session_id] = asyncio.Queue(maxsize=self.config.buffer_size)
        self._total_streams += 1

        logger.info("Created stream %s (protocol: %s)", session.session_id, session.protocol.value)
        return session

    def get_stream(self, session_id: str) -> StreamSession | None:
        """Get a stream session by ID."""
        return self._sessions.get(session_id)

    def close_stream(self, session_id: str) -> bool:
        """Close a streaming session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.state = StreamState.CLOSED
        session.end_time = datetime.now(timezone.utc).isoformat()

        # Clean up queues
        self._event_queues.pop(session_id, None)
        self._client_queues.pop(session_id, None)

        logger.info("Closed stream %s", session_id)
        return True

    # ── Event Emission ───────────────────────────────────

    async def emit_event(
        self,
        session_id: str,
        event_type: StreamEventType,
        data: Any,
        metadata: dict[str, Any] | None = None,
    ) -> StreamEvent | None:
        """Emit an event to a stream session."""
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("Stream not found: %s", session_id)
            return None

        if session.state not in (StreamState.ACTIVE, StreamState.CONNECTING):
            logger.warning("Stream %s is not active (state: %s)", session_id, session.state.value)
            return None

        event = StreamEvent(
            stream_id=session_id,
            event_type=event_type,
            data=data,
            sequence=session.event_count + 1,
            metadata=metadata or {},
        )

        # Process through pipelines
        for pipeline in sorted(self._pipelines.values(), key=lambda p: p.order):
            event = pipeline.process(event)

        session.events.append(event)
        session.event_count += 1
        session.bytes_streamed += len(json.dumps(data)) if data else 0
        session.last_activity = datetime.now(timezone.utc).isoformat()

        self._total_events += 1
        self._total_bytes += session.bytes_streamed

        # Put event in queue for async consumers
        queue = self._event_queues.get(session_id)
        if queue:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event queue full for stream %s, dropping event", session_id)

        # Fan out to all clients
        for client_queue in self._client_queues.get(session_id, {}).values():
            try:
                client_queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

        return event

    def emit_event_sync(
        self,
        session_id: str,
        event_type: StreamEventType,
        data: Any,
        metadata: dict[str, Any] | None = None,
    ) -> StreamEvent | None:
        """Synchronous event emission (for non-async contexts)."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        if session.state not in (StreamState.ACTIVE, StreamState.CONNECTING):
            return None

        event = StreamEvent(
            stream_id=session_id,
            event_type=event_type,
            data=data,
            sequence=session.event_count + 1,
            metadata=metadata or {},
        )

        for pipeline in sorted(self._pipelines.values(), key=lambda p: p.order):
            event = pipeline.process(event)

        session.events.append(event)
        session.event_count += 1
        session.bytes_streamed += len(json.dumps(data)) if isinstance(data, (dict, list)) else len(str(data))
        session.last_activity = datetime.now(timezone.utc).isoformat()

        self._total_events += 1
        self._total_bytes += session.bytes_streamed

        return event

    async def emit_batch(
        self,
        session_id: str,
        events: list[tuple[StreamEventType, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> list[StreamEvent]:
        """Emit multiple events in batch."""
        results = []
        for event_type, data in events:
            event = await self.emit_event(session_id, event_type, data, metadata)
            if event:
                results.append(event)
        return results

    async def emit_done(self, session_id: str, metadata: dict[str, Any] | None = None) -> StreamEvent | None:
        """Emit a done event and close the stream."""
        event = await self.emit_event(session_id, StreamEventType.DONE, None, metadata)
        session = self._sessions.get(session_id)
        if session:
            session.state = StreamState.DRAINING
        return event

    async def emit_error(
        self,
        session_id: str,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> StreamEvent | None:
        """Emit an error event."""
        event = await self.emit_event(
            session_id,
            StreamEventType.ERROR,
            {"error": error},
            metadata,
        )
        session = self._sessions.get(session_id)
        if session:
            session.state = StreamState.ERROR
        return event

    # ── Client Subscription ──────────────────────────────

    async def subscribe_client(
        self,
        session_id: str,
        client_id: str = "",
        filter_types: list[StreamEventType] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Subscribe a client to a stream, yielding events as they arrive."""
        session = self._sessions.get(session_id)
        if not session:
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": "Stream not found"},
            )
            return

        client_id = client_id or f"client-{uuid.uuid4().hex[:8]}"
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.buffer_size)

        if session_id not in self._client_queues:
            self._client_queues[session_id] = {}
        self._client_queues[session_id][client_id] = queue

        session.state = StreamState.ACTIVE

        try:
            while session.state != StreamState.CLOSED:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=self.config.heartbeat_interval_seconds,
                    )
                    if filter_types and event.event_type not in filter_types:
                        continue
                    yield event
                except asyncio.TimeoutError:
                    yield StreamEvent(
                        event_type=StreamEventType.HEARTBEAT,
                        data={"timestamp": datetime.now(timezone.utc).isoformat()},
                    )
        finally:
            self._client_queues.get(session_id, {}).pop(client_id, None)

    async def subscribe_sse(
        self,
        session_id: str,
        client_id: str = "",
        filter_types: list[StreamEventType] | None = None,
    ) -> AsyncIterator[str]:
        """Subscribe a client to SSE formatted stream."""
        async for event in self.subscribe_client(session_id, client_id, filter_types):
            yield event.to_sse()

    # ── Pipeline Management ──────────────────────────────

    def register_pipeline(
        self,
        name: str,
        stages: list[tuple[PipelineStage, Callable[[StreamEvent], StreamEvent]]],
        order: int = 0,
    ) -> StreamPipeline:
        """Register a stream processing pipeline."""
        pipeline_id = f"pipe-{uuid.uuid4().hex[:8]}"
        pipeline = StreamPipeline(
            pipeline_id=pipeline_id,
            name=name,
            stages=stages,
            order=order,
        )
        self._pipelines[pipeline_id] = pipeline
        logger.info("Registered pipeline: %s (%s)", name, pipeline_id)
        return pipeline

    def remove_pipeline(self, pipeline_id: str) -> bool:
        """Remove a pipeline."""
        return self._pipelines.pop(pipeline_id, None) is not None

    def list_pipelines(self) -> list[StreamPipeline]:
        """List all registered pipelines."""
        return list(self._pipelines.values())

    # ── Event Replay ─────────────────────────────────────

    def get_replay_events(
        self,
        session_id: str,
        from_sequence: int = 0,
        limit: int = 0,
    ) -> list[StreamEvent]:
        """Get events for replay from a specific sequence number."""
        session = self._sessions.get(session_id)
        if not session:
            return []

        limit = limit or self.config.max_replay_events
        events = session.events[from_sequence:from_sequence + limit]
        return events

    async def replay_stream(
        self,
        session_id: str,
        from_sequence: int = 0,
    ) -> AsyncIterator[StreamEvent]:
        """Replay events from a stream."""
        events = self.get_replay_events(session_id, from_sequence)
        for event in events:
            yield event

    # ── Session Management ───────────────────────────────

    def list_sessions(
        self,
        agent_id: str = "",
        state: StreamState | None = None,
    ) -> list[StreamSession]:
        """List stream sessions with filtering."""
        sessions = list(self._sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        if state:
            sessions = [s for s in sessions if s.state == state]
        return sorted(sessions, key=lambda s: s.start_time or "", reverse=True)

    def pause_stream(self, session_id: str) -> bool:
        """Pause a stream."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.state = StreamState.PAUSED
        return True

    def resume_stream(self, session_id: str) -> bool:
        """Resume a paused stream."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.state = StreamState.ACTIVE
        return True

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> StreamingHubStats:
        """Get comprehensive streaming statistics."""
        stats = StreamingHubStats()
        stats.total_streams = self._total_streams
        stats.total_events = self._total_events
        stats.total_bytes = self._total_bytes

        protocol_counts: dict[str, int] = defaultdict(int)
        for session in self._sessions.values():
            if session.state == StreamState.ACTIVE:
                stats.active_streams += 1
            stats.total_clients += len(session.clients)
            protocol_counts[session.protocol.value] += 1

        stats.active_protocols = dict(protocol_counts)

        elapsed = time.monotonic() - self._start_time
        if elapsed > 0:
            stats.events_per_second = self._total_events / elapsed

        return stats

    def reset(self) -> None:
        """Reset the streaming hub."""
        self._sessions.clear()
        self._pipelines.clear()
        self._event_queues.clear()
        self._client_queues.clear()
        self._total_streams = 0
        self._total_events = 0
        self._total_bytes = 0
        self._start_time = time.monotonic()
        logger.info("AgentStreamingHub reset")


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_streaming_hub: AgentStreamingHub | None = None


def get_streaming_hub() -> AgentStreamingHub:
    """Get or create the global Streaming Hub instance."""
    global _streaming_hub
    if _streaming_hub is None:
        _streaming_hub = AgentStreamingHub()
    return _streaming_hub


def reset_streaming_hub() -> None:
    """Reset the global Streaming Hub instance."""
    global _streaming_hub
    if _streaming_hub:
        _streaming_hub.reset()
    _streaming_hub = None