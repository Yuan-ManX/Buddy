"""
Buddy Streaming Engine - Real-time Agent Output

Provides SSE (Server-Sent Events) and WebSocket streaming for real-time
agent output delivery. Supports token-level streaming, progress updates,
and bidirectional communication channels.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable


class StreamEventType(str, Enum):
    """Types of streaming events."""
    TOKEN = "token"              # Incremental token output
    TOOL_CALL = "tool_call"      # Tool invocation event
    TOOL_RESULT = "tool_result"  # Tool execution result
    THOUGHT = "thought"          # Reasoning/thinking output
    PROGRESS = "progress"        # Task progress update
    ERROR = "error"              # Error event
    COMPLETE = "complete"        # Stream completion
    STATUS = "status"            # Status update
    MESSAGE = "message"          # General message
    HEARTBEAT = "heartbeat"      # Keep-alive signal


@dataclass
class StreamEvent:
    """A single streaming event."""
    event_id: str
    event_type: StreamEventType
    data: Any
    agent_id: str = ""
    session_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_sse(self) -> str:
        """Format as SSE message."""
        payload = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"event: {self.event_type.value}\ndata: {payload}\n\n"

    def to_dict(self) -> dict:
        return {
            "id": self.event_id,
            "type": self.event_type.value,
            "data": self.data,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }


class StreamSession:
    """A single streaming session for an agent interaction."""

    def __init__(self, session_id: str, agent_id: str):
        self.session_id = session_id
        self.agent_id = agent_id
        self._queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        self._active = True
        self._subscribers: list[asyncio.Queue[StreamEvent]] = []
        self._event_count = 0
        self._created_at = time.time()

    async def emit(self, event: StreamEvent):
        """Emit an event to all subscribers."""
        event.session_id = self.session_id
        event.agent_id = self.agent_id
        self._event_count += 1
        await self._queue.put(event)
        for sub in self._subscribers:
            await sub.put(event)

    async def emit_token(self, token: str):
        """Emit a single token."""
        await self.emit(StreamEvent(
            event_id=f"tok-{self._event_count}",
            event_type=StreamEventType.TOKEN,
            data={"token": token},
        ))

    async def emit_tool_call(self, tool_name: str, arguments: dict):
        """Emit a tool call event."""
        await self.emit(StreamEvent(
            event_id=f"tool-{self._event_count}",
            event_type=StreamEventType.TOOL_CALL,
            data={"tool": tool_name, "arguments": arguments},
        ))

    async def emit_tool_result(self, tool_name: str, result: Any):
        """Emit a tool execution result."""
        await self.emit(StreamEvent(
            event_id=f"tres-{self._event_count}",
            event_type=StreamEventType.TOOL_RESULT,
            data={"tool": tool_name, "result": result},
        ))

    async def emit_thought(self, thought: str):
        """Emit a reasoning thought."""
        await self.emit(StreamEvent(
            event_id=f"tht-{self._event_count}",
            event_type=StreamEventType.THOUGHT,
            data={"thought": thought},
        ))

    async def emit_error(self, error: str, code: str = ""):
        """Emit an error event."""
        await self.emit(StreamEvent(
            event_id=f"err-{self._event_count}",
            event_type=StreamEventType.ERROR,
            data={"error": error, "code": code},
        ))

    async def emit_complete(self, summary: dict | None = None):
        """Emit stream completion."""
        await self.emit(StreamEvent(
            event_id=f"done-{self._event_count}",
            event_type=StreamEventType.COMPLETE,
            data=summary or {},
        ))
        self._active = False

    async def subscribe(self) -> AsyncGenerator[StreamEvent, None]:
        """Subscribe to this session's events."""
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while self._active or not self._queue.empty():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield StreamEvent(
                        event_id=f"hb-{time.time()}",
                        event_type=StreamEventType.HEARTBEAT,
                        data={},
                    )
        finally:
            self._subscribers.remove(queue)

    def close(self):
        """Close the session."""
        self._active = False


class StreamingEngine:
    """Central streaming engine for real-time agent communication.

    Manages streaming sessions, event routing, and subscriber management.
    Supports SSE for unidirectional and WebSocket for bidirectional communication.
    """

    def __init__(self):
        self._sessions: dict[str, StreamSession] = {}
        self._total_events = 0
        self._total_sessions = 0

    def create_session(self, agent_id: str) -> StreamSession:
        """Create a new streaming session."""
        session_id = f"stream-{uuid.uuid4().hex[:12]}"
        session = StreamSession(session_id, agent_id)
        self._sessions[session_id] = session
        self._total_sessions += 1
        return session

    def get_session(self, session_id: str) -> StreamSession | None:
        """Get an existing streaming session."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str):
        """Close and remove a streaming session."""
        session = self._sessions.pop(session_id, None)
        if session:
            session.close()

    async def generate_sse(self, session_id: str) -> AsyncGenerator[str, None]:
        """Generate SSE output for a session."""
        session = self.get_session(session_id)
        if not session:
            yield StreamEvent(
                event_id="err",
                event_type=StreamEventType.ERROR,
                data={"error": "Session not found"},
            ).to_sse()
            return

        async for event in session.subscribe():
            self._total_events += 1
            yield event.to_sse()

    async def simulate_stream(
        self,
        agent_id: str,
        content: str,
        tool_calls: list[dict] | None = None,
        delay_ms: float = 50,
    ) -> str:
        """Simulate a streaming response for testing."""
        session = self.create_session(agent_id)

        # Stream tokens
        for i, char in enumerate(content):
            if char == " " or i % 3 == 0:
                await session.emit_token(content[max(0, i - 2):i + 1])
                await asyncio.sleep(delay_ms / 1000)

        # Simulate tool calls
        if tool_calls:
            for tc in tool_calls:
                await session.emit_tool_call(tc["name"], tc.get("arguments", {}))
                await asyncio.sleep(0.1)
                await session.emit_tool_result(tc["name"], tc.get("result", "done"))

        await session.emit_complete({"tokens": len(content)})
        return session.session_id

    def get_stats(self) -> dict:
        return {
            "active_sessions": len(self._sessions),
            "total_sessions": self._total_sessions,
            "total_events": self._total_events,
            "sessions": [
                {"id": s.session_id, "agent_id": s.agent_id, "active": s._active}
                for s in self._sessions.values()
            ],
        }


# Global streaming engine instance
_streaming_engine: StreamingEngine | None = None


def get_streaming_engine() -> StreamingEngine:
    """Get or create the global streaming engine."""
    global _streaming_engine
    if _streaming_engine is None:
        _streaming_engine = StreamingEngine()
    return _streaming_engine