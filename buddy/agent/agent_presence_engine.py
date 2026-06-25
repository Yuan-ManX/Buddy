"""
Agent Presence Engine — Persistent Digital Identity and Continuous Presence.

The Presence Engine maintains the agent's continuous digital existence across
sessions, platforms, and interactions. It provides availability management,
activity tracking, and context continuity so the agent never loses its sense
of being — even between conversations or across different channels.

Architecture:
  Layer 1: Identity — Persistent agent profile with evolving traits
  Layer 2: Presence — Real-time availability and status management
  Layer 3: Activity — Continuous activity timeline with context threading
  Layer 4: Availability — Schedule-based and rule-based presence control
  Layer 5: Continuity — Cross-session context preservation and handoff
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.presence")


# ═══════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════

class PresenceState(str, Enum):
    """The agent's current presence state."""
    ONLINE = "online"          # Actively available
    AWAY = "away"              # Temporarily unavailable
    BUSY = "busy"              # Actively working, limited availability
    IDLE = "idle"              # Available but inactive
    OFFLINE = "offline"        # Not connected
    DO_NOT_DISTURB = "dnd"     # Explicitly unavailable
    INVISIBLE = "invisible"    # Connected but hidden


class ActivityType(str, Enum):
    """Types of activities the agent can perform."""
    CONVERSATION = "conversation"     # Engaging in chat
    TASK_EXECUTION = "task_execution" # Running a task
    LEARNING = "learning"             # Processing new information
    REFLECTION = "reflection"         # Self-analysis
    COLLABORATION = "collaboration"   # Working with other agents
    IDLE = "idle"                     # No active work
    MONITORING = "monitoring"         # Watching for triggers
    MAINTENANCE = "maintenance"       # System upkeep
    DREAMING = "dreaming"             # Background consolidation
    CUSTOM = "custom"                 # Custom activity


class AvailabilityMode(str, Enum):
    """Availability scheduling modes."""
    ALWAYS = "always"              # Always available
    SCHEDULED = "scheduled"        # Based on time schedule
    ON_DEMAND = "on_demand"        # Available when explicitly activated
    WORKLOAD_BASED = "workload"    # Based on current workload
    HYBRID = "hybrid"              # Combination of modes


class ContextCarryover(str, Enum):
    """Strategy for carrying context between sessions."""
    FULL = "full"                  # Carry all context
    SUMMARIZED = "summarized"      # Carry compressed summary
    KEY_POINTS = "key_points"      # Carry only key points
    NONE = "none"                  # Fresh start each session


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class AgentProfile:
    """Persistent digital identity profile for an agent."""
    agent_id: str
    display_name: str = ""
    avatar_url: str = ""
    bio: str = ""
    role: str = ""
    expertise: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    timezone: str = "UTC"
    traits: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "role": self.role,
            "expertise": self.expertise,
            "languages": self.languages,
            "timezone": self.timezone,
            "traits": self.traits,
            "preferences": self.preferences,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PresenceStatus:
    """Current presence status of an agent."""
    agent_id: str
    state: PresenceState = PresenceState.OFFLINE
    status_message: str = ""
    current_activity: ActivityType = ActivityType.IDLE
    activity_description: str = ""
    connected_since: str = ""
    last_active_at: str = ""
    active_sessions: int = 0
    platforms: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "status_message": self.status_message,
            "current_activity": self.current_activity.value,
            "activity_description": self.activity_description,
            "connected_since": self.connected_since,
            "last_active_at": self.last_active_at,
            "active_sessions": self.active_sessions,
            "platforms": self.platforms,
        }


@dataclass
class ActivityRecord:
    """A single activity entry in the agent's timeline."""
    record_id: str
    agent_id: str
    activity_type: ActivityType
    description: str
    session_id: str = ""
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    tokens_used: int = 0
    outcome: str = ""
    tags: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "activity_type": self.activity_type.value,
            "description": self.description,
            "session_id": self.session_id,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "outcome": self.outcome,
            "tags": self.tags,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


@dataclass
class AvailabilitySchedule:
    """Time-based availability schedule."""
    schedule_id: str
    agent_id: str
    mode: AvailabilityMode = AvailabilityMode.ALWAYS
    timezone: str = "UTC"
    active_days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    active_hours_start: str = "00:00"
    active_hours_end: str = "23:59"
    max_concurrent_sessions: int = 10
    auto_away_after_ms: int = 300000  # 5 minutes
    auto_offline_after_ms: int = 1800000  # 30 minutes
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "agent_id": self.agent_id,
            "mode": self.mode.value,
            "timezone": self.timezone,
            "active_days": self.active_days,
            "active_hours_start": self.active_hours_start,
            "active_hours_end": self.active_hours_end,
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "auto_away_after_ms": self.auto_away_after_ms,
            "auto_offline_after_ms": self.auto_offline_after_ms,
        }


@dataclass
class SessionContext:
    """Context carried across sessions for continuity."""
    context_id: str
    agent_id: str
    previous_session_id: str = ""
    carryover_strategy: ContextCarryover = ContextCarryover.SUMMARIZED
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    active_topics: list[str] = field(default_factory=list)
    pending_items: list[dict[str, Any]] = field(default_factory=list)
    user_preferences_learned: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "agent_id": self.agent_id,
            "previous_session_id": self.previous_session_id,
            "carryover_strategy": self.carryover_strategy.value,
            "summary": self.summary,
            "key_points": self.key_points,
            "active_topics": self.active_topics,
            "pending_items": self.pending_items,
            "created_at": self.created_at,
        }


@dataclass
class PresenceEvent:
    """An event in the presence system."""
    event_id: str
    agent_id: str
    event_type: str  # "state_change", "activity_start", "activity_end", "session_join", "session_leave"
    previous_state: str = ""
    new_state: str = ""
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "event_type": self.event_type,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "description": self.description,
            "timestamp": self.timestamp,
        }


@dataclass
class PresenceStats:
    """Statistics for the presence engine."""
    total_sessions: int = 0
    total_activities: int = 0
    total_uptime_ms: float = 0.0
    current_state: str = "offline"
    active_sessions: int = 0
    activities_today: int = 0
    tokens_used_today: int = 0
    average_session_duration_ms: float = 0.0
    presence_changes_today: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "total_activities": self.total_activities,
            "total_uptime_ms": round(self.total_uptime_ms, 0),
            "current_state": self.current_state,
            "active_sessions": self.active_sessions,
            "activities_today": self.activities_today,
            "tokens_used_today": self.tokens_used_today,
            "average_session_duration_ms": round(self.average_session_duration_ms, 0),
            "presence_changes_today": self.presence_changes_today,
        }


# ═══════════════════════════════════════════════════════════════
# Presence Engine
# ═══════════════════════════════════════════════════════════════

class PresenceEngine:
    """Persistent digital identity and continuous presence management.

    The Presence Engine maintains the agent's continuous existence across
    sessions and platforms. It tracks availability, activity history, and
    carries context between interactions to provide a seamless experience.

    Design Principles:
    - Persistent: Agent identity and state survive across sessions
    - Continuous: Context seamlessly carries between interactions
    - Aware: The agent knows its own state and availability
    - Transparent: State changes are broadcast to interested parties
    - Adaptive: Behavior adjusts based on availability mode
    """

    def __init__(self, engine_id: str = "buddy-global"):
        self.engine_id = engine_id

        # Agent profiles
        self._profiles: dict[str, AgentProfile] = {}

        # Presence states
        self._presence: dict[str, PresenceStatus] = {}

        # Activity timelines
        self._activities: dict[str, list[ActivityRecord]] = {}
        self._active_activities: dict[str, ActivityRecord | None] = {}

        # Availability schedules
        self._schedules: dict[str, AvailabilitySchedule] = {}

        # Session contexts
        self._session_contexts: dict[str, SessionContext] = {}

        # Presence events
        self._events: list[PresenceEvent] = []

        # Statistics
        self._stats: dict[str, PresenceStats] = {}

        # Callbacks
        self._state_change_hooks: list[Callable] = []
        self._activity_hooks: list[Callable] = []

        # Background task
        self._idle_check_task: asyncio.Task | None = None

        logger.info(f"Presence engine initialized: {engine_id}")

    # ═════════════════════════════════════════════════════════
    # Profile Management
    # ═════════════════════════════════════════════════════════

    def create_profile(
        self,
        agent_id: str,
        display_name: str = "",
        bio: str = "",
        role: str = "",
        expertise: list[str] | None = None,
        traits: dict[str, Any] | None = None,
    ) -> AgentProfile:
        """Create a persistent agent profile."""
        profile = AgentProfile(
            agent_id=agent_id,
            display_name=display_name or agent_id,
            bio=bio,
            role=role,
            expertise=expertise or [],
            traits=traits or {},
        )
        self._profiles[agent_id] = profile

        # Initialize presence
        self._presence[agent_id] = PresenceStatus(agent_id=agent_id)

        # Initialize stats
        self._stats[agent_id] = PresenceStats()

        logger.info(f"Agent profile created: {agent_id}")
        return profile

    def get_profile(self, agent_id: str) -> AgentProfile | None:
        """Get an agent's profile."""
        return self._profiles.get(agent_id)

    def update_profile(self, agent_id: str, **kwargs) -> AgentProfile | None:
        """Update profile fields."""
        profile = self._profiles.get(agent_id)
        if not profile:
            return None

        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.updated_at = datetime.now(timezone.utc).isoformat()
        return profile

    # ═════════════════════════════════════════════════════════
    # Presence Management
    # ═════════════════════════════════════════════════════════

    def set_presence(
        self,
        agent_id: str,
        state: PresenceState,
        status_message: str = "",
        platforms: list[str] | None = None,
    ) -> PresenceStatus | None:
        """Set the agent's presence state."""
        if agent_id not in self._presence:
            self._presence[agent_id] = PresenceStatus(agent_id=agent_id)

        presence = self._presence[agent_id]
        previous_state = presence.state.value

        presence.state = state
        presence.status_message = status_message
        if platforms is not None:
            presence.platforms = platforms
        presence.last_active_at = datetime.now(timezone.utc).isoformat()

        if state == PresenceState.ONLINE and previous_state != "online":
            presence.connected_since = presence.last_active_at

        # Record event
        self._record_event(agent_id, "state_change", previous_state, state.value,
                          f"Presence changed: {previous_state} -> {state.value}")

        # Fire hooks
        for hook in self._state_change_hooks:
            try:
                hook(agent_id, state, previous_state)
            except Exception as e:
                logger.debug(f"State change hook error: {e}")

        # Update stats
        if agent_id in self._stats:
            self._stats[agent_id].current_state = state.value
            self._stats[agent_id].presence_changes_today += 1

        logger.info(f"Agent {agent_id} presence: {state.value}")
        return presence

    def get_presence(self, agent_id: str) -> PresenceStatus | None:
        """Get current presence status."""
        return self._presence.get(agent_id)

    def connect(self, agent_id: str, platform: str = "web") -> PresenceStatus | None:
        """Mark agent as connected on a platform."""
        presence = self._presence.get(agent_id)
        if not presence:
            presence = PresenceStatus(agent_id=agent_id)
            self._presence[agent_id] = presence

        if platform not in presence.platforms:
            presence.platforms.append(platform)

        presence.active_sessions += 1
        if presence.state == PresenceState.OFFLINE:
            presence.state = PresenceState.ONLINE
            presence.connected_since = datetime.now(timezone.utc).isoformat()

        presence.last_active_at = datetime.now(timezone.utc).isoformat()

        if agent_id in self._stats:
            self._stats[agent_id].active_sessions = presence.active_sessions

        self._record_event(agent_id, "session_join", "", "",
                          f"Connected on {platform}")
        return presence

    def disconnect(self, agent_id: str, platform: str = "web") -> PresenceStatus | None:
        """Mark agent as disconnected from a platform."""
        presence = self._presence.get(agent_id)
        if not presence:
            return None

        if platform in presence.platforms:
            presence.platforms.remove(platform)

        presence.active_sessions = max(0, presence.active_sessions - 1)

        if presence.active_sessions == 0:
            presence.state = PresenceState.OFFLINE

        presence.last_active_at = datetime.now(timezone.utc).isoformat()

        if agent_id in self._stats:
            self._stats[agent_id].active_sessions = presence.active_sessions

        self._record_event(agent_id, "session_leave", "", "",
                          f"Disconnected from {platform}")
        return presence

    def heartbeat(self, agent_id: str) -> bool:
        """Update last active timestamp."""
        presence = self._presence.get(agent_id)
        if presence:
            presence.last_active_at = datetime.now(timezone.utc).isoformat()

            # Auto-transition from AWAY to ONLINE
            if presence.state == PresenceState.AWAY:
                presence.state = PresenceState.ONLINE

            return True
        return False

    # ═════════════════════════════════════════════════════════
    # Activity Tracking
    # ═════════════════════════════════════════════════════════

    def start_activity(
        self,
        agent_id: str,
        activity_type: ActivityType,
        description: str = "",
        session_id: str = "",
        tags: list[str] | None = None,
    ) -> ActivityRecord:
        """Start tracking a new activity."""
        record = ActivityRecord(
            record_id=f"act-{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            activity_type=activity_type,
            description=description,
            session_id=session_id,
            tags=tags or [],
        )

        if agent_id not in self._activities:
            self._activities[agent_id] = []

        self._activities[agent_id].append(record)
        self._active_activities[agent_id] = record

        # Update presence
        if agent_id in self._presence:
            self._presence[agent_id].current_activity = activity_type
            self._presence[agent_id].activity_description = description

        # Update stats
        if agent_id in self._stats:
            self._stats[agent_id].total_activities += 1
            self._stats[agent_id].activities_today += 1

        self._record_event(agent_id, "activity_start", "", "",
                          f"Started: {activity_type.value} - {description}")

        for hook in self._activity_hooks:
            try:
                hook(agent_id, record, "started")
            except Exception as e:
                logger.debug(f"Activity hook error: {e}")

        return record

    def end_activity(
        self,
        agent_id: str,
        outcome: str = "",
        tokens_used: int = 0,
        context_snapshot: dict[str, Any] | None = None,
    ) -> ActivityRecord | None:
        """End the current activity."""
        record = self._active_activities.get(agent_id)
        if not record:
            return None

        record.ended_at = datetime.now(timezone.utc).isoformat()
        record.outcome = outcome
        record.tokens_used = tokens_used
        if context_snapshot:
            record.context_snapshot = context_snapshot

        # Calculate duration
        start = datetime.fromisoformat(record.started_at)
        end = datetime.fromisoformat(record.ended_at)
        record.duration_ms = (end - start).total_seconds() * 1000

        self._active_activities[agent_id] = None

        # Update presence
        if agent_id in self._presence:
            self._presence[agent_id].current_activity = ActivityType.IDLE
            self._presence[agent_id].activity_description = ""

        # Update stats
        if agent_id in self._stats:
            self._stats[agent_id].tokens_used_today += tokens_used

        self._record_event(agent_id, "activity_end", "", "",
                          f"Ended: {record.activity_type.value} ({record.duration_ms:.0f}ms)")

        for hook in self._activity_hooks:
            try:
                hook(agent_id, record, "ended")
            except Exception as e:
                logger.debug(f"Activity hook error: {e}")

        return record

    def get_current_activity(self, agent_id: str) -> ActivityRecord | None:
        """Get the currently running activity."""
        return self._active_activities.get(agent_id)

    def get_activity_timeline(
        self, agent_id: str, limit: int = 50, activity_type: str | None = None,
    ) -> list[ActivityRecord]:
        """Get recent activity timeline."""
        activities = self._activities.get(agent_id, [])
        if activity_type:
            activities = [a for a in activities if a.activity_type.value == activity_type]
        return activities[-limit:]

    # ═════════════════════════════════════════════════════════
    # Availability Management
    # ═════════════════════════════════════════════════════════

    def set_schedule(
        self,
        agent_id: str,
        mode: AvailabilityMode = AvailabilityMode.ALWAYS,
        active_days: list[int] | None = None,
        active_hours_start: str = "00:00",
        active_hours_end: str = "23:59",
        max_concurrent_sessions: int = 10,
        auto_away_after_ms: int = 300000,
        auto_offline_after_ms: int = 1800000,
    ) -> AvailabilitySchedule:
        """Set availability schedule for an agent."""
        schedule = AvailabilitySchedule(
            schedule_id=f"sch-{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            mode=mode,
            active_days=active_days or [0, 1, 2, 3, 4, 5, 6],
            active_hours_start=active_hours_start,
            active_hours_end=active_hours_end,
            max_concurrent_sessions=max_concurrent_sessions,
            auto_away_after_ms=auto_away_after_ms,
            auto_offline_after_ms=auto_offline_after_ms,
        )
        self._schedules[agent_id] = schedule
        return schedule

    def get_schedule(self, agent_id: str) -> AvailabilitySchedule | None:
        """Get availability schedule."""
        return self._schedules.get(agent_id)

    def is_available(self, agent_id: str) -> bool:
        """Check if agent is currently available."""
        presence = self._presence.get(agent_id)
        if not presence:
            return False

        if presence.state in (PresenceState.OFFLINE, PresenceState.DO_NOT_DISTURB):
            return False

        schedule = self._schedules.get(agent_id)
        if schedule and schedule.mode == AvailabilityMode.SCHEDULED:
            now = datetime.now(timezone.utc)
            if now.weekday() not in schedule.active_days:
                return False
            # Simple hour check
            current_hour = now.hour
            start_hour = int(schedule.active_hours_start.split(":")[0])
            end_hour = int(schedule.active_hours_end.split(":")[0])
            if not (start_hour <= current_hour < end_hour):
                return False

        if schedule and presence.active_sessions >= schedule.max_concurrent_sessions:
            return False

        return True

    # ═════════════════════════════════════════════════════════
    # Context Continuity
    # ═════════════════════════════════════════════════════════

    def save_session_context(
        self,
        agent_id: str,
        previous_session_id: str,
        summary: str = "",
        key_points: list[str] | None = None,
        active_topics: list[str] | None = None,
        pending_items: list[dict[str, Any]] | None = None,
        user_preferences: dict[str, Any] | None = None,
    ) -> SessionContext:
        """Save context for continuity between sessions."""
        context = SessionContext(
            context_id=f"ctx-{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            previous_session_id=previous_session_id,
            carryover_strategy=ContextCarryover.SUMMARIZED,
            summary=summary,
            key_points=key_points or [],
            active_topics=active_topics or [],
            pending_items=pending_items or [],
            user_preferences_learned=user_preferences or {},
        )
        self._session_contexts[agent_id] = context
        logger.info(f"Session context saved for {agent_id}: {len(key_points or [])} key points")
        return context

    def get_session_context(self, agent_id: str) -> SessionContext | None:
        """Get the most recent session context."""
        return self._session_contexts.get(agent_id)

    def build_continuity_prompt(self, agent_id: str) -> str:
        """Build a continuity prompt from saved context."""
        context = self._session_contexts.get(agent_id)
        if not context:
            return ""

        parts = []
        if context.summary:
            parts.append(f"Previous session summary: {context.summary}")
        if context.key_points:
            parts.append("Key points from last session:")
            for kp in context.key_points[:5]:
                parts.append(f"  - {kp}")
        if context.active_topics:
            parts.append(f"Ongoing topics: {', '.join(context.active_topics[:5])}")
        if context.pending_items:
            parts.append("Pending items:")
            for item in context.pending_items[:3]:
                parts.append(f"  - {item.get('description', str(item))}")

        return "\n".join(parts)

    # ═════════════════════════════════════════════════════════
    # Presence Events
    # ═════════════════════════════════════════════════════════

    def _record_event(
        self, agent_id: str, event_type: str, previous_state: str,
        new_state: str, description: str,
    ):
        """Record a presence event."""
        event = PresenceEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            event_type=event_type,
            previous_state=previous_state,
            new_state=new_state,
            description=description,
        )
        self._events.append(event)

        # Keep only last 1000 events
        if len(self._events) > 1000:
            self._events = self._events[-1000:]

    def get_events(self, agent_id: str | None = None, limit: int = 50) -> list[PresenceEvent]:
        """Get presence events, optionally filtered by agent."""
        events = self._events
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        return events[-limit:]

    def add_state_change_hook(self, hook: Callable):
        """Register a hook for state changes."""
        self._state_change_hooks.append(hook)

    def add_activity_hook(self, hook: Callable):
        """Register a hook for activity changes."""
        self._activity_hooks.append(hook)

    # ═════════════════════════════════════════════════════════
    # Idle Detection
    # ═════════════════════════════════════════════════════════

    async def start_idle_detection(self, check_interval_ms: int = 30000):
        """Start background idle detection."""
        if self._idle_check_task and not self._idle_check_task.done():
            return

        async def _check_idle():
            while True:
                await asyncio.sleep(check_interval_ms / 1000)
                await self._check_idle_agents()

        self._idle_check_task = asyncio.create_task(_check_idle())
        logger.info("Idle detection started")

    async def stop_idle_detection(self):
        """Stop background idle detection."""
        if self._idle_check_task and not self._idle_check_task.done():
            self._idle_check_task.cancel()
            try:
                await self._idle_check_task
            except asyncio.CancelledError:
                pass
            self._idle_check_task = None

    async def _check_idle_agents(self):
        """Check for idle agents and transition their state."""
        now = datetime.now(timezone.utc)
        for agent_id, presence in list(self._presence.items()):
            if presence.state not in (PresenceState.ONLINE, PresenceState.AWAY):
                continue

            schedule = self._schedules.get(agent_id)
            if not schedule:
                continue

            if not presence.last_active_at:
                continue

            last_active = datetime.fromisoformat(presence.last_active_at)
            idle_ms = (now - last_active).total_seconds() * 1000

            if presence.state == PresenceState.ONLINE and idle_ms > schedule.auto_away_after_ms:
                self.set_presence(agent_id, PresenceState.AWAY, "Auto-away due to inactivity")
            elif presence.state == PresenceState.AWAY and idle_ms > schedule.auto_offline_after_ms:
                self.set_presence(agent_id, PresenceState.OFFLINE, "Auto-offline due to inactivity")

    # ═════════════════════════════════════════════════════════
    # Statistics & Introspection
    # ═════════════════════════════════════════════════════════

    def get_stats(self, agent_id: str | None = None) -> dict[str, Any]:
        """Get presence statistics."""
        if agent_id:
            stats = self._stats.get(agent_id, PresenceStats())
            presence = self._presence.get(agent_id)
            if presence:
                stats.current_state = presence.state.value
                stats.active_sessions = presence.active_sessions
            return stats.to_dict()

        # Aggregate stats
        aggregate = {
            "total_agents": len(self._profiles),
            "online_agents": sum(
                1 for p in self._presence.values()
                if p.state not in (PresenceState.OFFLINE,)
            ),
            "total_activities": sum(
                s.total_activities for s in self._stats.values()
            ),
            "total_events": len(self._events),
            "agents": {
                agent_id: {
                    "state": self._presence.get(agent_id, PresenceStatus(agent_id=agent_id)).state.value,
                    "activities": self._stats.get(agent_id, PresenceStats()).total_activities,
                }
                for agent_id in self._profiles
            },
        }
        return aggregate

    def get_all_presence(self) -> list[PresenceStatus]:
        """Get all agent presence states."""
        return list(self._presence.values())

    def reset(self, agent_id: str | None = None):
        """Reset presence data."""
        if agent_id:
            self._profiles.pop(agent_id, None)
            self._presence.pop(agent_id, None)
            self._activities.pop(agent_id, None)
            self._active_activities.pop(agent_id, None)
            self._schedules.pop(agent_id, None)
            self._session_contexts.pop(agent_id, None)
            self._stats.pop(agent_id, None)
        else:
            self._profiles.clear()
            self._presence.clear()
            self._activities.clear()
            self._active_activities.clear()
            self._schedules.clear()
            self._session_contexts.clear()
            self._events.clear()
            self._stats.clear()

        logger.info(f"Presence engine reset: {agent_id or 'all'}")


# ═══════════════════════════════════════════════════════════════
# Global Instance
# ═══════════════════════════════════════════════════════════════

presence_engine = PresenceEngine()