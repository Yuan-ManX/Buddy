"""Buddy WebSocket — Real-time streaming and event broadcast

Provides WebSocket-based communication for:
- Real-time chat token streaming to frontend clients
- Task progress and lifecycle events
- Agent status change notifications
- System event broadcasting (Guard alerts, Pulse health, Squad activity)
- Sub-agent execution progress tracking

The WebSocket manager maintains per-client connections and supports
room-based broadcasting for targeted message delivery.
"""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("buddy.websocket")


class MessageType(str, Enum):
    CHAT_STREAM = "chat_stream"
    CHAT_TOKEN = "chat_token"
    CHAT_DONE = "chat_done"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    AGENT_STATUS = "agent_status"
    SYSTEM_EVENT = "system_event"
    GUARD_ALERT = "guard_alert"
    PULSE_HEALTH = "pulse_health"
    SQUAD_UPDATE = "squad_update"
    SUBAGENT_PROGRESS = "subagent_progress"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WebSocketMessage:
    """Structured WebSocket message with type and payload."""

    def __init__(self, msg_type: MessageType, payload: Any, room: str | None = None, sender: str = "system"):
        self.id = f"ws-{uuid.uuid4().hex[:8]}"
        self.type = msg_type
        self.payload = payload
        self.room = room
        self.sender = sender
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "type": self.type.value,
            "payload": self.payload,
            "room": self.room,
            "sender": self.sender,
            "timestamp": self.timestamp,
        }, ensure_ascii=False)


class Connection:
    """A single WebSocket client connection with metadata."""

    def __init__(self, ws: WebSocket, client_id: str, subscribed_rooms: list[str] | None = None):
        self.ws = ws
        self.client_id = client_id
        self.subscribed_rooms: set[str] = set(subscribed_rooms or [])
        self.connected_at = datetime.now(timezone.utc)
        self.last_ping = datetime.now(timezone.utc)
        self.messages_sent = 0
        self.messages_received = 0

    async def send(self, msg: WebSocketMessage):
        """Send a message to this client. Silently drops if disconnected."""
        try:
            await self.ws.send_text(msg.to_json())
            self.messages_sent += 1
        except Exception:
            pass

    async def send_json(self, data: dict):
        """Send raw JSON to this client."""
        try:
            await self.ws.send_json(data)
            self.messages_sent += 1
        except Exception:
            pass


class WebSocketManager:
    """Manages all WebSocket connections with room-based broadcasting.

    Rooms provide targeted delivery:
    - "agent:{agent_id}" — Agent-specific events (chat, status, task progress)
    - "system" — Global system events (health, alerts)
    - "squad:{squad_id}" — Squad collaboration events
    - "broadcast" — All connected clients
    """

    MAX_CONNECTIONS = 1000
    PING_INTERVAL = 30  # seconds
    PING_TIMEOUT = 90   # seconds

    def __init__(self):
        self._connections: dict[str, Connection] = {}
        self._rooms: dict[str, set[str]] = {}  # room_name -> set of client_ids
        self._ping_task: asyncio.Task | None = None
        self._started = False

    async def start(self):
        """Start the WebSocket manager background tasks."""
        if self._started:
            return
        self._started = True
        self._ping_task = asyncio.create_task(self._ping_loop())
        logger.info("WebSocket manager started")

    async def stop(self):
        """Stop the WebSocket manager and disconnect all clients."""
        self._started = False
        if self._ping_task:
            self._ping_task.cancel()
        for client_id in list(self._connections.keys()):
            await self.disconnect(client_id)
        logger.info("WebSocket manager stopped")

    async def connect(self, ws: WebSocket, client_id: str | None = None, rooms: list[str] | None = None) -> str:
        """Accept a new WebSocket connection and register it."""
        if len(self._connections) >= self.MAX_CONNECTIONS:
            await ws.close(code=1013, reason="Max connections reached")
            raise ValueError("Max connections reached")

        cid = client_id or f"client-{uuid.uuid4().hex[:8]}"

        # Close existing connection for this client_id if present
        if cid in self._connections:
            await self.disconnect(cid)

        # Default rooms: client-specific + broadcast + system
        default_rooms = [f"client:{cid}", "broadcast", "system"]
        all_rooms = list(set(default_rooms + (rooms or [])))

        conn = Connection(ws, cid, all_rooms)
        self._connections[cid] = conn

        for room in all_rooms:
            self._add_to_room(cid, room)

        logger.info(f"WebSocket connected: {cid} in rooms: {all_rooms}")
        await conn.send(WebSocketMessage(
            MessageType.SYSTEM_EVENT,
            {"event": "connected", "client_id": cid, "rooms": all_rooms},
        ))
        return cid

    async def disconnect(self, client_id: str):
        """Remove a client connection and clean up room memberships."""
        conn = self._connections.pop(client_id, None)
        if conn is None:
            return

        for room in list(conn.subscribed_rooms):
            self._remove_from_room(client_id, room)

        try:
            await conn.ws.close()
        except Exception:
            pass
        logger.info(f"WebSocket disconnected: {client_id}")

    async def handle_client(self, ws: WebSocket, client_id: str | None = None, rooms: list[str] | None = None):
        """Full client lifecycle handler — accept, listen, cleanup."""
        cid = await self.connect(ws, client_id, rooms)
        try:
            while True:
                raw = await ws.receive_text()
                conn = self._connections.get(cid)
                if conn:
                    conn.messages_received += 1
                    conn.last_ping = datetime.now(timezone.utc)
                await self._handle_client_message(cid, raw)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket error for {cid}: {e}")
        finally:
            await self.disconnect(cid)

    async def _handle_client_message(self, client_id: str, raw: str):
        """Process incoming client messages."""
        try:
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "ping":
                conn = self._connections.get(client_id)
                if conn:
                    await conn.send(WebSocketMessage(MessageType.PONG, {"echo": data.get("payload", {})}))

            elif msg_type == "subscribe":
                rooms = data.get("rooms", [])
                await self.subscribe(client_id, rooms)

            elif msg_type == "unsubscribe":
                rooms = data.get("rooms", [])
                await self.unsubscribe(client_id, rooms)

        except json.JSONDecodeError:
            logger.debug(f"Invalid JSON from client {client_id}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")

    # ── Room Management ────────────────────────────────────

    def _add_to_room(self, client_id: str, room: str):
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(client_id)

    def _remove_from_room(self, client_id: str, room: str):
        if room in self._rooms:
            self._rooms[room].discard(client_id)
            if not self._rooms[room]:
                del self._rooms[room]

    async def subscribe(self, client_id: str, rooms: list[str]):
        """Subscribe a client to additional rooms."""
        conn = self._connections.get(client_id)
        if not conn:
            return
        for room in rooms:
            conn.subscribed_rooms.add(room)
            self._add_to_room(client_id, room)
        await conn.send(WebSocketMessage(
            MessageType.SYSTEM_EVENT,
            {"event": "subscribed", "rooms": rooms},
        ))

    async def unsubscribe(self, client_id: str, rooms: list[str]):
        """Unsubscribe a client from rooms."""
        conn = self._connections.get(client_id)
        if not conn:
            return
        for room in rooms:
            conn.subscribed_rooms.discard(room)
            self._remove_from_room(client_id, room)
        await conn.send(WebSocketMessage(
            MessageType.SYSTEM_EVENT,
            {"event": "unsubscribed", "rooms": rooms},
        ))

    # ── Broadcasting ───────────────────────────────────────

    async def broadcast(self, msg: WebSocketMessage):
        """Send to all connected clients."""
        tasks = []
        for cid in list(self._connections.keys()):
            conn = self._connections.get(cid)
            if conn:
                tasks.append(conn.send(msg))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_room(self, room: str, msg: WebSocketMessage):
        """Send a message to all clients in a specific room."""
        client_ids = self._rooms.get(room, set())
        if not client_ids:
            return
        msg.room = room
        tasks = []
        for cid in list(client_ids):
            conn = self._connections.get(cid)
            if conn:
                tasks.append(conn.send(msg))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_client(self, client_id: str, msg: WebSocketMessage):
        """Send a message to a specific client."""
        conn = self._connections.get(client_id)
        if conn:
            await conn.send(msg)

    # ── Specialized Broadcast Methods ──────────────────────

    async def stream_chat_token(self, agent_id: str, token: str, done: bool = False):
        """Stream a single chat token to agent's subscribers."""
        msg_type = MessageType.CHAT_DONE if done else MessageType.CHAT_TOKEN
        await self.send_to_room(
            f"agent:{agent_id}",
            WebSocketMessage(msg_type, {"agent_id": agent_id, "token": token}),
        )

    async def notify_task_progress(self, agent_id: str, task_id: str, status: str, progress: float = 0.0, detail: str = ""):
        """Notify about task progress."""
        await self.send_to_room(
            f"agent:{agent_id}",
            WebSocketMessage(MessageType.TASK_PROGRESS, {
                "agent_id": agent_id,
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "detail": detail,
            }),
        )

    async def notify_agent_status(self, agent_id: str, status: str, detail: str = ""):
        """Notify about agent status change."""
        await self.send_to_room(
            f"agent:{agent_id}",
            WebSocketMessage(MessageType.AGENT_STATUS, {
                "agent_id": agent_id,
                "status": status,
                "detail": detail,
            }),
        )
        await self.send_to_room(
            "system",
            WebSocketMessage(MessageType.AGENT_STATUS, {
                "agent_id": agent_id,
                "status": status,
                "detail": detail,
            }),
        )

    async def notify_guard_alert(self, alert: dict):
        """Broadcast a security/safety alert."""
        await self.send_to_room(
            "system",
            WebSocketMessage(MessageType.GUARD_ALERT, alert),
        )

    async def notify_pulse_health(self, health_data: dict):
        """Broadcast system health status."""
        await self.send_to_room(
            "system",
            WebSocketMessage(MessageType.PULSE_HEALTH, health_data),
        )

    async def notify_squad_update(self, squad_id: str, update: dict):
        """Notify squad members about changes."""
        await self.send_to_room(
            f"squad:{squad_id}",
            WebSocketMessage(MessageType.SQUAD_UPDATE, update),
        )

    async def notify_subagent_progress(self, parent_agent_id: str, subagent_id: str, status: str, detail: str = ""):
        """Notify about sub-agent execution progress."""
        await self.send_to_room(
            f"agent:{parent_agent_id}",
            WebSocketMessage(MessageType.SUBAGENT_PROGRESS, {
                "parent_agent_id": parent_agent_id,
                "subagent_id": subagent_id,
                "status": status,
                "detail": detail,
            }),
        )

    # ── Heartbeat / Ping ────────────────────────────────────

    async def _ping_loop(self):
        """Periodically ping clients and clean up dead connections."""
        while self._started:
            await asyncio.sleep(self.PING_INTERVAL)
            now = datetime.now(timezone.utc)
            dead_clients = []

            for cid, conn in list(self._connections.items()):
                # Check for stale connections
                if (now - conn.last_ping).total_seconds() > self.PING_TIMEOUT:
                    dead_clients.append(cid)
                else:
                    try:
                        await conn.send(WebSocketMessage(MessageType.PING, {"ts": now.isoformat()}))
                    except Exception:
                        dead_clients.append(cid)

            for cid in dead_clients:
                logger.info(f"Cleaning up dead connection: {cid}")
                await self.disconnect(cid)

    # ── Stats ──────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get WebSocket manager statistics."""
        return {
            "active_connections": len(self._connections),
            "rooms": {room: len(members) for room, members in self._rooms.items()},
            "total_rooms": len(self._rooms),
            "max_connections": self.MAX_CONNECTIONS,
            "clients": [
                {
                    "client_id": c.client_id,
                    "rooms": list(c.subscribed_rooms),
                    "connected_since": c.connected_at.isoformat(),
                    "messages_sent": c.messages_sent,
                    "messages_received": c.messages_received,
                }
                for c in self._connections.values()
            ],
        }


# Global singleton
ws_manager = WebSocketManager()