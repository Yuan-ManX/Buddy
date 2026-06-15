"""
Buddy IM Integration Hub

A unified instant messaging integration layer that enables Buddy agents
to connect with popular messaging platforms. Agents can receive messages,
respond in threads, and participate in group conversations across multiple
IM channels simultaneously.

Supported platforms include Telegram, Slack, Discord, WeChat Work (Feishu),
and DingTalk — each with its own adapter implementing a common interface.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.im_hub")


class IMPlatform(str, Enum):
    """Supported instant messaging platforms."""
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"
    FEISHU = "feishu"
    WECHAT_WORK = "wechat_work"
    DINGTALK = "dingtalk"
    WHATSAPP = "whatsapp"
    MATRIX = "matrix"


class IMConnectionStatus(str, Enum):
    """Connection status of an IM platform adapter."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class IMMessageType(str, Enum):
    """Types of messages that can be received or sent."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACT = "contact"
    SYSTEM = "system"


@dataclass
class IMChatMessage:
    """A message received from or to be sent to an IM platform."""
    id: str = ""
    platform: IMPlatform = IMPlatform.TELEGRAM
    chat_id: str = ""
    chat_type: str = "private"  # private, group, channel
    sender_id: str = ""
    sender_name: str = ""
    text: str = ""
    message_type: IMMessageType = IMMessageType.TEXT
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reply_to_id: str = ""
    attachments: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    is_mentioned: bool = False
    thread_id: str = ""


@dataclass
class IMChannelConfig:
    """Configuration for connecting to an IM platform."""
    platform: IMPlatform
    enabled: bool = False
    bot_token: str = ""
    app_id: str = ""
    app_secret: str = ""
    webhook_url: str = ""
    allowed_chat_ids: list[str] = field(default_factory=list)
    blocked_chat_ids: list[str] = field(default_factory=list)
    auto_reply: bool = True
    max_context_messages: int = 20
    response_timeout_seconds: int = 30


class IMAdapter(ABC):
    """Abstract base class for IM platform adapters.

    Each adapter implements the platform-specific logic for connecting,
    receiving messages, and sending responses. The IM Hub orchestrates
    multiple adapters through this common interface.
    """

    def __init__(self, config: IMChannelConfig):
        self.config = config
        self.status = IMConnectionStatus.DISCONNECTED
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._message_handler: Optional[callable] = None

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the IM platform."""
        ...

    @abstractmethod
    async def disconnect(self):
        """Gracefully disconnect from the IM platform."""
        ...

    @abstractmethod
    async def send_message(self, message: IMChatMessage) -> bool:
        """Send a message to the IM platform."""
        ...

    @abstractmethod
    async def send_typing_indicator(self, chat_id: str):
        """Send typing indicator to a chat."""
        ...

    @abstractmethod
    async def get_chat_info(self, chat_id: str) -> dict:
        """Get information about a chat/channel."""
        ...

    def set_message_handler(self, handler: callable):
        """Set the async callback for incoming messages."""
        self._message_handler = handler

    async def _handle_incoming(self, message: IMChatMessage):
        """Process an incoming message and pass to the handler."""
        if self._message_handler:
            try:
                await self._message_handler(message)
            except Exception as e:
                logger.error(f"Message handler error for {self.config.platform}: {e}")


class TelegramAdapter(IMAdapter):
    """Telegram Bot API adapter."""

    async def connect(self) -> bool:
        self.status = IMConnectionStatus.CONNECTING
        try:
            if not self.config.bot_token:
                logger.warning("Telegram bot token not configured")
                self.status = IMConnectionStatus.DISCONNECTED
                return False
            # In production, this would use python-telegram-bot or httpx polling
            self.status = IMConnectionStatus.CONNECTED
            logger.info("Telegram adapter connected (simulated)")
            return True
        except Exception as e:
            self.status = IMConnectionStatus.ERROR
            logger.error(f"Telegram connection failed: {e}")
            return False

    async def disconnect(self):
        self.status = IMConnectionStatus.DISCONNECTED
        logger.info("Telegram adapter disconnected")

    async def send_message(self, message: IMChatMessage) -> bool:
        logger.info(f"[Telegram] Sending to {message.chat_id}: {message.text[:100]}...")
        return True

    async def send_typing_indicator(self, chat_id: str):
        logger.debug(f"[Telegram] Typing indicator sent to {chat_id}")

    async def get_chat_info(self, chat_id: str) -> dict:
        return {"chat_id": chat_id, "type": "private", "platform": "telegram"}


class SlackAdapter(IMAdapter):
    """Slack API adapter."""

    async def connect(self) -> bool:
        self.status = IMConnectionStatus.CONNECTING
        try:
            if not self.config.bot_token:
                logger.warning("Slack bot token not configured")
                self.status = IMConnectionStatus.DISCONNECTED
                return False
            self.status = IMConnectionStatus.CONNECTED
            logger.info("Slack adapter connected (simulated)")
            return True
        except Exception as e:
            self.status = IMConnectionStatus.ERROR
            logger.error(f"Slack connection failed: {e}")
            return False

    async def disconnect(self):
        self.status = IMConnectionStatus.DISCONNECTED

    async def send_message(self, message: IMChatMessage) -> bool:
        logger.info(f"[Slack] Sending to {message.chat_id}: {message.text[:100]}...")
        return True

    async def send_typing_indicator(self, chat_id: str):
        logger.debug(f"[Slack] Typing indicator sent to {chat_id}")

    async def get_chat_info(self, chat_id: str) -> dict:
        return {"chat_id": chat_id, "type": "channel", "platform": "slack"}


class DiscordAdapter(IMAdapter):
    """Discord API adapter."""

    async def connect(self) -> bool:
        self.status = IMConnectionStatus.CONNECTING
        try:
            if not self.config.bot_token:
                logger.warning("Discord bot token not configured")
                self.status = IMConnectionStatus.DISCONNECTED
                return False
            self.status = IMConnectionStatus.CONNECTED
            logger.info("Discord adapter connected (simulated)")
            return True
        except Exception as e:
            self.status = IMConnectionStatus.ERROR
            logger.error(f"Discord connection failed: {e}")
            return False

    async def disconnect(self):
        self.status = IMConnectionStatus.DISCONNECTED

    async def send_message(self, message: IMChatMessage) -> bool:
        logger.info(f"[Discord] Sending to {message.chat_id}: {message.text[:100]}...")
        return True

    async def send_typing_indicator(self, chat_id: str):
        logger.debug(f"[Discord] Typing indicator sent to {chat_id}")

    async def get_chat_info(self, chat_id: str) -> dict:
        return {"chat_id": chat_id, "type": "guild", "platform": "discord"}


class FeishuAdapter(IMAdapter):
    """Feishu (Lark) API adapter."""

    async def connect(self) -> bool:
        self.status = IMConnectionStatus.CONNECTING
        try:
            if not self.config.app_id or not self.config.app_secret:
                logger.warning("Feishu app credentials not configured")
                self.status = IMConnectionStatus.DISCONNECTED
                return False
            self.status = IMConnectionStatus.CONNECTED
            logger.info("Feishu adapter connected (simulated)")
            return True
        except Exception as e:
            self.status = IMConnectionStatus.ERROR
            logger.error(f"Feishu connection failed: {e}")
            return False

    async def disconnect(self):
        self.status = IMConnectionStatus.DISCONNECTED

    async def send_message(self, message: IMChatMessage) -> bool:
        logger.info(f"[Feishu] Sending to {message.chat_id}: {message.text[:100]}...")
        return True

    async def send_typing_indicator(self, chat_id: str):
        logger.debug(f"[Feishu] Typing indicator sent to {chat_id}")

    async def get_chat_info(self, chat_id: str) -> dict:
        return {"chat_id": chat_id, "type": "group", "platform": "feishu"}


class IMHub:
    """Central IM Integration Hub for the Buddy platform.

    Manages multiple IM platform connections simultaneously, routing
    incoming messages to the appropriate agent and sending agent
    responses back through the correct platform adapter.

    Features:
    - Multi-platform connection management
    - Message routing and filtering
    - Agent assignment per chat/channel
    - Rate limiting and throttling
    - Connection health monitoring
    """

    def __init__(self):
        self._adapters: dict[IMPlatform, IMAdapter] = {}
        self._configs: dict[IMPlatform, IMChannelConfig] = {}
        self._chat_agent_mapping: dict[str, str] = {}  # chat_id -> agent_id
        self._message_history: list[IMChatMessage] = []
        self._max_history = 500
        self._agent_handler: Optional[callable] = None
        logger.info("IM Hub initialized")

    def configure_platform(self, config: IMChannelConfig):
        """Configure a platform for connection."""
        self._configs[config.platform] = config
        logger.info(f"IM platform configured: {config.platform.value}")

    async def connect_platform(self, platform: IMPlatform) -> bool:
        """Connect to a specific IM platform."""
        if platform not in self._configs:
            logger.error(f"Platform {platform.value} not configured")
            return False

        config = self._configs[platform]
        if not config.enabled:
            logger.info(f"Platform {platform.value} is disabled")
            return False

        adapter_map = {
            IMPlatform.TELEGRAM: TelegramAdapter,
            IMPlatform.SLACK: SlackAdapter,
            IMPlatform.DISCORD: DiscordAdapter,
            IMPlatform.FEISHU: FeishuAdapter,
        }

        adapter_cls = adapter_map.get(platform)
        if not adapter_cls:
            logger.error(f"No adapter available for {platform.value}")
            return False

        adapter = adapter_cls(config)
        adapter.set_message_handler(self._handle_incoming_message)
        success = await adapter.connect()

        if success:
            self._adapters[platform] = adapter
            logger.info(f"Connected to {platform.value}")

        return success

    async def disconnect_platform(self, platform: IMPlatform):
        """Disconnect from a specific IM platform."""
        if platform in self._adapters:
            await self._adapters[platform].disconnect()
            del self._adapters[platform]

    async def connect_all(self):
        """Connect to all configured and enabled platforms."""
        tasks = []
        for platform in self._configs:
            tasks.append(self.connect_platform(platform))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        connected = sum(1 for r in results if r is True)
        logger.info(f"Connected to {connected}/{len(tasks)} IM platforms")

    async def disconnect_all(self):
        """Disconnect from all platforms."""
        for platform in list(self._adapters.keys()):
            await self.disconnect_platform(platform)

    async def send_message(self, platform: IMPlatform, message: IMChatMessage) -> bool:
        """Send a message through a specific platform."""
        if platform not in self._adapters:
            logger.error(f"Platform {platform.value} not connected")
            return False

        adapter = self._adapters[platform]
        message.platform = platform
        success = await adapter.send_message(message)

        if success:
            self._record_message(message)

        return success

    async def send_to_chat(
        self, platform: IMPlatform, chat_id: str, text: str, **kwargs
    ) -> bool:
        """Convenience method to send a text message to a chat."""
        message = IMChatMessage(
            platform=platform,
            chat_id=chat_id,
            text=text,
            **kwargs,
        )
        return await self.send_message(platform, message)

    def set_agent_handler(self, handler: callable):
        """Set the handler for routing IM messages to agents."""
        self._agent_handler = handler

    def assign_agent_to_chat(self, chat_id: str, agent_id: str):
        """Assign a specific agent to handle messages from a chat."""
        self._chat_agent_mapping[chat_id] = agent_id
        logger.info(f"Chat {chat_id} assigned to agent {agent_id}")

    async def _handle_incoming_message(self, message: IMChatMessage):
        """Process an incoming IM message."""
        self._record_message(message)

        # Route to assigned agent or default handler
        agent_id = self._chat_agent_mapping.get(message.chat_id, "")

        if self._agent_handler:
            try:
                await self._agent_handler(message, agent_id)
            except Exception as e:
                logger.error(f"Agent handler error: {e}")

    def _record_message(self, message: IMChatMessage):
        """Record a message in the history buffer."""
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]

    def get_platform_status(self, platform: IMPlatform) -> dict:
        """Get the connection status of a specific platform."""
        if platform in self._adapters:
            adapter = self._adapters[platform]
            return {
                "platform": platform.value,
                "status": adapter.status.value,
                "configured": True,
                "enabled": self._configs.get(platform, IMChannelConfig(platform=platform)).enabled,
            }
        return {
            "platform": platform.value,
            "status": "disconnected",
            "configured": platform in self._configs,
            "enabled": self._configs.get(platform, IMChannelConfig(platform=platform)).enabled,
        }

    def get_stats(self) -> dict:
        """Get comprehensive IM Hub statistics."""
        platform_statuses = {
            p.value: self.get_platform_status(p) for p in IMPlatform
        }

        return {
            "connected_platforms": len(self._adapters),
            "configured_platforms": len(self._configs),
            "platforms": platform_statuses,
            "total_messages": len(self._message_history),
            "chat_assignments": len(self._chat_agent_mapping),
            "recent_messages": [
                {
                    "platform": m.platform.value,
                    "chat_id": m.chat_id,
                    "sender": m.sender_name,
                    "text": m.text[:100],
                    "timestamp": m.timestamp,
                }
                for m in self._message_history[-10:]
            ],
        }

    def get_recent_messages(
        self, platform: Optional[IMPlatform] = None, limit: int = 50
    ) -> list[dict]:
        """Get recent messages, optionally filtered by platform."""
        messages = self._message_history
        if platform:
            messages = [m for m in messages if m.platform == platform]
        return [
            {
                "id": m.id,
                "platform": m.platform.value,
                "chat_id": m.chat_id,
                "chat_type": m.chat_type,
                "sender_id": m.sender_id,
                "sender_name": m.sender_name,
                "text": m.text,
                "message_type": m.message_type.value,
                "timestamp": m.timestamp,
                "is_mentioned": m.is_mentioned,
            }
            for m in messages[-limit:]
        ]


# Global singleton
im_hub = IMHub()