"""Buddy Gateway — Multi-platform messaging integration hub

Unifies agent communication across messaging platforms so agents can
interact wherever users are:
- Web (browser-based chat in the Buddy dashboard)
- CLI (terminal-based interaction)
- Messaging platforms (Telegram, Discord, Slack — plugin architecture)

The gateway routes incoming messages to the correct agent and delivers
responses back through the originating platform. Platforms are
registered as plugins, enabling easy extension to new messaging services.

Core design:
- Platform-agnostic message routing
- Session tracking across platforms
- Authentication and platform connection management
- Message transformation between platform formats and Buddy internal format
"""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("buddy.gateway")


class MessagePlatform(str, Enum):
    WEB = "web"
    CLI = "cli"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"


class GatewayMessageType(str, Enum):
    TEXT = "text"
    COMMAND = "command"
    MEDIA = "media"
    SYSTEM = "system"


@dataclass
class GatewayMessage:
    """Normalized message format for all platforms."""
    id: str
    platform: MessagePlatform
    platform_user_id: str
    agent_id: str | None = None
    content: str = ""
    message_type: GatewayMessageType = GatewayMessageType.TEXT
    conversation_id: str | None = None
    metadata: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"gw-msg-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class GatewaySession:
    """Tracks a conversation session across platforms."""
    id: str
    platform: MessagePlatform
    platform_user_id: str
    agent_id: str
    conversation_id: str | None = None
    created_at: str = ""
    last_active: str = ""
    message_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.id:
            self.id = f"gw-session-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = now
        if not self.last_active:
            self.last_active = now


class PlatformAdapter(ABC):
    """Abstract base class for messaging platform adapters.

    Each platform (Telegram, Discord, etc.) implements this interface
    to connect to the Buddy gateway.
    """

    @property
    @abstractmethod
    def platform(self) -> MessagePlatform:
        ...

    @abstractmethod
    async def connect(self, config: dict) -> bool:
        """Establish connection to the messaging platform."""
        ...

    @abstractmethod
    async def disconnect(self):
        """Tear down the platform connection."""
        ...

    @abstractmethod
    async def send_message(self, recipient_id: str, content: str, metadata: dict | None = None) -> bool:
        """Send a message to a platform user."""
        ...

    @abstractmethod
    async def listen(self, callback: Callable[[GatewayMessage], Any]):
        """Start listening for incoming messages."""
        ...

    def transform_incoming(self, raw_message: Any) -> GatewayMessage:
        """Transform a platform-specific message into GatewayMessage format."""
        raise NotImplementedError

    def transform_outgoing(self, content: str, metadata: dict | None = None) -> Any:
        """Transform Gateway content into platform-specific format."""
        return content


class TelegramAdapter(PlatformAdapter):
    """Telegram Bot API adapter for Buddy Gateway."""

    def __init__(self):
        self._bot_token: str = ""
        self._client: Any = None
        self._connected = False

    @property
    def platform(self) -> MessagePlatform:
        return MessagePlatform.TELEGRAM

    async def connect(self, config: dict) -> bool:
        self._bot_token = config.get("bot_token", "")
        if not self._bot_token:
            logger.warning("Telegram adapter requires bot_token in config")
            return False
        self._connected = True
        logger.info("Telegram adapter configured (async polling mode)")
        return True

    async def disconnect(self):
        self._connected = False
        self._client = None

    async def send_message(self, recipient_id: str, content: str, metadata: dict | None = None) -> bool:
        if not self._connected:
            logger.warning("Telegram adapter not connected")
            return False
        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
            payload = {
                "chat_id": recipient_id,
                "text": content[:4096],
                "parse_mode": "Markdown",
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"Telegram message sent to {recipient_id}")
                        return True
                    logger.warning(f"Telegram send failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def listen(self, callback: Callable[[GatewayMessage], Any]):
        """Poll Telegram for updates (simplified polling mode)."""
        if not self._connected:
            return
        logger.info("Telegram listener started (polling mode)")
        import aiohttp
        last_update_id = 0
        while self._connected:
            try:
                url = f"https://api.telegram.org/bot{self._bot_token}/getUpdates?offset={last_update_id + 1}&timeout=30"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for update in data.get("result", []):
                                last_update_id = update["update_id"]
                                msg = update.get("message", {})
                                if "text" in msg:
                                    gw_msg = GatewayMessage(
                                        id=f"tg-{msg['message_id']}",
                                        platform=MessagePlatform.TELEGRAM,
                                        platform_user_id=str(msg["from"]["id"]),
                                        content=msg["text"],
                                        metadata={
                                            "chat_id": msg["chat"]["id"],
                                            "username": msg["from"].get("username", ""),
                                            "first_name": msg["from"].get("first_name", ""),
                                        },
                                    )
                                    await callback(gw_msg)
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
            await asyncio.sleep(1)


class WebAdapter(PlatformAdapter):
    """Built-in web platform adapter (always connected)."""

    @property
    def platform(self) -> MessagePlatform:
        return MessagePlatform.WEB

    async def connect(self, config: dict) -> bool:
        logger.info("Web adapter connected")
        return True

    async def disconnect(self):
        pass

    async def send_message(self, recipient_id: str, content: str, metadata: dict | None = None) -> bool:
        # Web messages are handled directly via HTTP/WS
        return True

    async def listen(self, callback: Callable[[GatewayMessage], Any]):
        pass  # Web listens through FastAPI routes


class GatewayHub:
    """Central gateway hub that routes messages between platforms and agents.

    Manages platform adapter registration, session tracking, and
    bidirectional message routing.
    """

    def __init__(self):
        self._adapters: dict[MessagePlatform, PlatformAdapter] = {}
        self._sessions: dict[str, GatewaySession] = {}
        self._message_handler: Callable[[GatewayMessage], Any] | None = None
        self._running = False

        # Register built-in adapters
        self._adapters[MessagePlatform.WEB] = WebAdapter()

    def register_adapter(self, adapter: PlatformAdapter):
        """Register a new platform adapter."""
        self._adapters[adapter.platform] = adapter
        logger.info(f"Registered adapter: {adapter.platform.value}")

    def unregister_adapter(self, platform: MessagePlatform):
        """Remove a platform adapter."""
        if platform in self._adapters:
            self._adapters.pop(platform)
            logger.info(f"Unregistered adapter: {platform.value}")

    async def connect_platform(self, platform: MessagePlatform, config: dict) -> bool:
        """Connect a platform adapter with configuration."""
        adapter = self._adapters.get(platform)
        if not adapter:
            # Auto-register based on platform type
            if platform == MessagePlatform.TELEGRAM:
                adapter = TelegramAdapter()
                self.register_adapter(adapter)
            else:
                logger.warning(f"No adapter for platform: {platform.value}")
                return False
        return await adapter.connect(config)

    async def start(self, message_handler: Callable[[GatewayMessage], Any]):
        """Start the gateway and begin listening on all platforms."""
        self._message_handler = message_handler
        self._running = True

        for platform, adapter in self._adapters.items():
            if platform != MessagePlatform.WEB:
                asyncio.create_task(self._listen_platform(adapter))

        logger.info("Gateway hub started")

    async def stop(self):
        """Stop the gateway and disconnect all platforms."""
        self._running = False
        for adapter in self._adapters.values():
            await adapter.disconnect()
        logger.info("Gateway hub stopped")

    async def _listen_platform(self, adapter: PlatformAdapter):
        """Background listener for a platform adapter."""
        async def forward(msg: GatewayMessage):
            if self._message_handler:
                await self._message_handler(msg)
        await adapter.listen(forward)

    async def route_message(self, message: GatewayMessage) -> str:
        """Route an incoming message to the appropriate agent and get response.

        Returns the agent's response string.
        """
        # Track session
        session_key = f"{message.platform.value}:{message.platform_user_id}:{message.agent_id}"
        if session_key not in self._sessions:
            self._sessions[session_key] = GatewaySession(
                id=f"gw-session-{uuid.uuid4().hex[:8]}",
                platform=message.platform,
                platform_user_id=message.platform_user_id,
                agent_id=message.agent_id or "default",
            )
        session = self._sessions[session_key]
        session.message_count += 1
        session.last_active = datetime.now(timezone.utc).isoformat()

        # Note: Actual agent response is handled by the orchestrator.
        # The gateway only routes messages and tracks sessions.
        logger.info(
            f"Routing message from {message.platform.value} user {message.platform_user_id} "
            f"to agent {message.agent_id} (session: {session.id})"
        )
        return session.id

    async def send_to_user(
        self,
        platform: MessagePlatform,
        user_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> bool:
        """Send a message to a user on a specific platform."""
        adapter = self._adapters.get(platform)
        if not adapter:
            logger.warning(f"No adapter for platform: {platform.value}")
            return False
        return await adapter.send_message(user_id, content, metadata)

    def get_active_sessions(self) -> list[dict]:
        """Get all active gateway sessions."""
        return [
            {
                "id": s.id,
                "platform": s.platform.value,
                "platform_user_id": s.platform_user_id,
                "agent_id": s.agent_id,
                "conversation_id": s.conversation_id,
                "message_count": s.message_count,
                "created_at": s.created_at,
                "last_active": s.last_active,
            }
            for s in self._sessions.values()
        ]

    def get_stats(self) -> dict:
        """Get gateway hub statistics."""
        return {
            "platforms": {
                p.value: "connected" for p in self._adapters
            },
            "active_sessions": len(self._sessions),
            "total_messages": sum(s.message_count for s in self._sessions.values()),
            "running": self._running,
        }


# Global singleton
gateway_hub = GatewayHub()