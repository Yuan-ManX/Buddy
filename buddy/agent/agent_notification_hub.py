"""
Buddy Notification Hub - Integrated notification and messaging system.

Provides a centralized notification engine for the Buddy platform, supporting
multi-channel delivery, priority-based routing, templating, and subscription
management. The hub enables agents to send notifications to users and other
agents across various channels.

Core capabilities:
- Multi-channel notification delivery (in-app, email, webhook, SMS, desktop)
- Priority-based message routing with urgency levels
- Notification templating with variable substitution
- Subscription management with topic-based filtering
- Delivery tracking and acknowledgment
- Notification batching and digest generation
- Scheduled and recurring notifications
- Read/unread status management
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.notification_hub")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    DESKTOP = "desktop"
    SLACK = "slack"
    DISCORD = "discord"


class NotificationPriority(str, Enum):
    """Priority levels for notification routing."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Status of a notification."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    DISMISSED = "dismissed"


class NotificationTopic(str, Enum):
    """Predefined notification topics for subscription."""
    SYSTEM = "system"
    AGENT = "agent"
    TASK = "task"
    ALERT = "alert"
    UPDATE = "update"
    MENTION = "mention"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    PERFORMANCE = "performance"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class Notification:
    """A single notification message."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    body: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.IN_APP
    topic: NotificationTopic = NotificationTopic.SYSTEM
    sender_id: str = ""
    recipient_id: str = ""
    status: NotificationStatus = NotificationStatus.PENDING
    action_url: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None
    read_at: datetime | None = None


@dataclass
class Subscription:
    """A user/agent subscription to notification topics."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    subscriber_id: str = ""
    topics: list[NotificationTopic] = field(default_factory=list)
    channels: list[NotificationChannel] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NotificationTemplate:
    """A reusable notification template."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    title_template: str = ""
    body_template: str = ""
    default_priority: NotificationPriority = NotificationPriority.NORMAL
    default_channel: NotificationChannel = NotificationChannel.IN_APP
    variables: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Digest:
    """A digest/batch of notifications."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    recipient_id: str = ""
    notifications: list[str] = field(default_factory=list)
    summary: str = ""
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════
# Notification Hub Engine
# ═══════════════════════════════════════════════════════════

class NotificationHub:
    """Centralized notification and messaging engine.

    Manages notification delivery across multiple channels, subscription
    management, templating, and digest generation. Supports priority-based
    routing and delivery tracking.
    """

    def __init__(self) -> None:
        self._notifications: dict[str, Notification] = {}
        self._subscriptions: dict[str, Subscription] = {}
        self._templates: dict[str, NotificationTemplate] = {}
        self._digests: list[Digest] = []
        self._delivery_log: list[dict[str, Any]] = []
        self._total_sent: int = 0
        self._total_failed: int = 0
        self._total_read: int = 0

        # Initialize default templates
        self._init_default_templates()

    def _init_default_templates(self) -> None:
        """Initialize default notification templates."""
        defaults = [
            NotificationTemplate(
                name="task_complete",
                title_template="Task Completed: {task_name}",
                body_template="The task '{task_name}' has been completed successfully. Duration: {duration}.",
                variables=["task_name", "duration"],
            ),
            NotificationTemplate(
                name="agent_alert",
                title_template="Agent Alert: {alert_type}",
                body_template="Agent '{agent_name}' reported: {message}",
                default_priority=NotificationPriority.HIGH,
                variables=["alert_type", "agent_name", "message"],
            ),
            NotificationTemplate(
                name="review_request",
                title_template="Review Request: {item_name}",
                body_template="{requester} has requested your review on '{item_name}'. Please review at your earliest convenience.",
                default_channel=NotificationChannel.EMAIL,
                variables=["item_name", "requester"],
            ),
            NotificationTemplate(
                name="system_update",
                title_template="System Update: {update_title}",
                body_template="A system update is available: {update_description}",
                variables=["update_title", "update_description"],
            ),
            NotificationTemplate(
                name="mention",
                title_template="You were mentioned in {context}",
                body_template="{sender} mentioned you: {message}",
                variables=["context", "sender", "message"],
            ),
        ]
        for tpl in defaults:
            self._templates[tpl.name] = tpl

    # ── Subscription Management ────────────────────────────────────

    def subscribe(
        self,
        subscriber_id: str,
        topics: list[NotificationTopic] | None = None,
        channels: list[NotificationChannel] | None = None,
    ) -> Subscription:
        """Subscribe to notification topics.

        Args:
            subscriber_id: ID of the subscriber (user or agent).
            topics: Topics to subscribe to.
            channels: Channels to receive notifications on.

        Returns:
            The created Subscription.
        """
        existing = self._subscriptions.get(subscriber_id)
        if existing:
            if topics:
                existing.topics = list(set(existing.topics + topics))
            if channels:
                existing.channels = list(set(existing.channels + channels))
            return existing

        sub = Subscription(
            subscriber_id=subscriber_id,
            topics=topics or [NotificationTopic.SYSTEM],
            channels=channels or [NotificationChannel.IN_APP],
        )
        self._subscriptions[subscriber_id] = sub
        logger.info("Subscriber registered: %s", subscriber_id)
        return sub

    def unsubscribe(self, subscriber_id: str, topics: list[NotificationTopic] | None = None) -> bool:
        """Unsubscribe from topics or all topics.

        Args:
            subscriber_id: Subscriber ID.
            topics: Topics to unsubscribe from (None = all).

        Returns:
            True if successful.
        """
        sub = self._subscriptions.get(subscriber_id)
        if not sub:
            return False

        if topics is None:
            del self._subscriptions[subscriber_id]
        else:
            sub.topics = [t for t in sub.topics if t not in topics]

        return True

    def get_subscription(self, subscriber_id: str) -> Subscription | None:
        """Get subscription for a subscriber."""
        return self._subscriptions.get(subscriber_id)

    # ── Notification Sending ───────────────────────────────────────

    def send(
        self,
        title: str,
        body: str,
        recipient_id: str = "",
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        topic: NotificationTopic = NotificationTopic.SYSTEM,
        sender_id: str = "",
        action_url: str = "",
        data: dict[str, Any] | None = None,
    ) -> Notification:
        """Send a notification to a recipient.

        Args:
            title: Notification title.
            body: Notification body text.
            recipient_id: Recipient ID.
            priority: Notification priority.
            channel: Delivery channel.
            topic: Notification topic.
            sender_id: Sender ID.
            action_url: Optional action URL.
            data: Additional data payload.

        Returns:
            The created Notification.
        """
        notification = Notification(
            title=title,
            body=body,
            priority=priority,
            channel=channel,
            topic=topic,
            sender_id=sender_id,
            recipient_id=recipient_id,
            action_url=action_url,
            data=data or {},
        )

        # Check subscription filtering
        if recipient_id:
            sub = self._subscriptions.get(recipient_id)
            if sub and topic not in sub.topics:
                notification.status = NotificationStatus.DISMISSED
                self._notifications[notification.id] = notification
                return notification

        # Simulate delivery
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
        self._notifications[notification.id] = notification
        self._total_sent += 1

        self._delivery_log.append({
            "notification_id": notification.id,
            "channel": channel.value,
            "status": "sent",
            "timestamp": notification.sent_at.isoformat(),
        })

        logger.debug(
            "Notification sent: %s [%s] -> %s",
            notification.id, priority.value, recipient_id or "broadcast",
        )
        return notification

    def send_from_template(
        self,
        template_name: str,
        recipient_id: str = "",
        variables: dict[str, str] | None = None,
        channel: NotificationChannel | None = None,
        priority: NotificationPriority | None = None,
    ) -> Notification:
        """Send a notification using a template.

        Args:
            template_name: Name of the template to use.
            recipient_id: Recipient ID.
            variables: Variable values for template substitution.
            channel: Override default channel.
            priority: Override default priority.

        Returns:
            The created Notification.
        """
        tpl = self._templates.get(template_name)
        if not tpl:
            return self.send(
                title=f"Template not found: {template_name}",
                body="The requested notification template could not be found.",
                recipient_id=recipient_id,
            )

        vars_dict = variables or {}
        title = tpl.title_template
        body = tpl.body_template
        for var, val in vars_dict.items():
            title = title.replace(f"{{{var}}}", val)
            body = body.replace(f"{{{var}}}", val)

        return self.send(
            title=title,
            body=body,
            recipient_id=recipient_id,
            priority=priority or tpl.default_priority,
            channel=channel or tpl.default_channel,
        )

    # ── Notification Management ────────────────────────────────────

    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notif = self._notifications.get(notification_id)
        if notif:
            notif.status = NotificationStatus.READ
            notif.read_at = datetime.now(timezone.utc)
            self._total_read += 1
            return True
        return False

    def mark_all_read(self, recipient_id: str) -> int:
        """Mark all notifications for a recipient as read."""
        count = 0
        for notif in self._notifications.values():
            if notif.recipient_id == recipient_id and notif.status == NotificationStatus.SENT:
                notif.status = NotificationStatus.READ
                notif.read_at = datetime.now(timezone.utc)
                count += 1
        self._total_read += count
        return count

    def get_notifications(
        self,
        recipient_id: str = "",
        status: NotificationStatus | None = None,
        topic: NotificationTopic | None = None,
        priority: NotificationPriority | None = None,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notifications with optional filters.

        Args:
            recipient_id: Filter by recipient.
            status: Filter by status.
            topic: Filter by topic.
            priority: Filter by priority.
            limit: Maximum results.

        Returns:
            List of matching Notification objects.
        """
        notifs = list(self._notifications.values())

        if recipient_id:
            notifs = [n for n in notifs if n.recipient_id == recipient_id]
        if status:
            notifs = [n for n in notifs if n.status == status]
        if topic:
            notifs = [n for n in notifs if n.topic == topic]
        if priority:
            notifs = [n for n in notifs if n.priority == priority]

        notifs.sort(key=lambda n: n.created_at, reverse=True)
        return notifs[:limit]

    def get_unread_count(self, recipient_id: str) -> int:
        """Get count of unread notifications for a recipient."""
        return sum(
            1 for n in self._notifications.values()
            if n.recipient_id == recipient_id
            and n.status in (NotificationStatus.SENT, NotificationStatus.PENDING)
        )

    # ── Digest Generation ──────────────────────────────────────────

    def create_digest(
        self,
        recipient_id: str,
        hours: int = 24,
    ) -> Digest:
        """Create a digest of recent notifications for a recipient.

        Args:
            recipient_id: Recipient ID.
            hours: Time window in hours.

        Returns:
            Digest with batched notifications.
        """
        now = datetime.now(timezone.utc)
        cutoff = now.replace(hour=now.hour - hours) if now.hour >= hours else now

        recent_ids = [
            n.id for n in self._notifications.values()
            if n.recipient_id == recipient_id
            and n.created_at >= cutoff
        ]

        # Generate summary
        topic_counts: dict[str, int] = defaultdict(int)
        for nid in recent_ids:
            notif = self._notifications.get(nid)
            if notif:
                topic_counts[notif.topic.value] += 1

        summary_parts = [f"{count} {topic}" for topic, count in topic_counts.items()]
        summary = f"Digest for {recipient_id}: " + ", ".join(summary_parts) if summary_parts else "No notifications"

        digest = Digest(
            recipient_id=recipient_id,
            notifications=recent_ids,
            summary=summary,
            period_start=cutoff,
            period_end=now,
        )
        self._digests.append(digest)
        return digest

    # ── Template Management ────────────────────────────────────────

    def create_template(
        self,
        name: str,
        title_template: str,
        body_template: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> NotificationTemplate:
        """Create a new notification template.

        Args:
            name: Template name.
            title_template: Title with {variable} placeholders.
            body_template: Body with {variable} placeholders.
            priority: Default priority.
            channel: Default channel.

        Returns:
            The created NotificationTemplate.
        """
        import re
        variables = re.findall(r'\{(\w+)\}', title_template + body_template)

        tpl = NotificationTemplate(
            name=name,
            title_template=title_template,
            body_template=body_template,
            default_priority=priority,
            default_channel=channel,
            variables=variables,
        )
        self._templates[name] = tpl
        return tpl

    def get_templates(self) -> list[NotificationTemplate]:
        """Get all notification templates."""
        return list(self._templates.values())

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get notification hub statistics."""
        status_counts: dict[str, int] = defaultdict(int)
        for n in self._notifications.values():
            status_counts[n.status.value] += 1

        channel_counts: dict[str, int] = defaultdict(int)
        for n in self._notifications.values():
            channel_counts[n.channel.value] += 1

        return {
            "total_notifications": len(self._notifications),
            "total_sent": self._total_sent,
            "total_failed": self._total_failed,
            "total_read": self._total_read,
            "total_subscriptions": len(self._subscriptions),
            "total_templates": len(self._templates),
            "total_digests": len(self._digests),
            "status_distribution": dict(status_counts),
            "channel_distribution": dict(channel_counts),
            "channels_available": [c.value for c in NotificationChannel],
            "topics_available": [t.value for t in NotificationTopic],
        }

    def reset(self) -> None:
        """Reset all notification hub state."""
        self._notifications.clear()
        self._subscriptions.clear()
        self._templates.clear()
        self._digests.clear()
        self._delivery_log.clear()
        self._total_sent = 0
        self._total_failed = 0
        self._total_read = 0
        self._init_default_templates()


# ═══════════════════════════════════════════════════════════
# Singleton Accessors
# ═══════════════════════════════════════════════════════════

_notification_hub: NotificationHub | None = None


def get_notification_hub() -> NotificationHub:
    """Get or create the singleton NotificationHub."""
    global _notification_hub
    if _notification_hub is None:
        _notification_hub = NotificationHub()
    return _notification_hub


def reset_notification_hub() -> None:
    """Reset the singleton NotificationHub."""
    global _notification_hub
    if _notification_hub is not None:
        _notification_hub.reset()
    _notification_hub = None