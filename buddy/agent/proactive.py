"""Buddy Proactive Discovery — always-on task and opportunity detection

Continuously monitors agent memory, conversation history, and contextual
signals to discover actionable tasks, insights, and improvement opportunities.
Integrates with autopilot for automated scheduling and execution.

Core capabilities:
  - Pattern Detection: identifies recurring themes and needs from memory
  - Opportunity Discovery: surfaces gaps, improvements, and optimizations
  - Contextual Awareness: leverages conversation history and agent context
  - Task Generation: creates structured, actionable task proposals
  - Always-On Mode: continuous background monitoring and discovery
  - Priority Ranking: scores and ranks discovered tasks by urgency and impact
"""
from __future__ import annotations

import logging
import uuid
import asyncio
import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.proactive")


class DiscoverySource(str, Enum):
    MEMORY_PATTERN = "memory_pattern"      # Recurring themes in memory
    CONVERSATION_GAP = "conversation_gap"  # Unanswered questions or incomplete topics
    BEHAVIORAL_SIGNAL = "behavioral_signal"  # User behavior patterns
    SYSTEM_OPTIMIZATION = "system_optimization"  # Performance or efficiency opportunities
    EXTERNAL_EVENT = "external_event"      # Webhook or external trigger
    SCHEDULED_SCAN = "scheduled_scan"     # Periodic proactive scan


class TaskUrgency(str, Enum):
    NOW = "now"          # Immediate action needed
    SOON = "soon"        # Within hours
    LATER = "later"      # Within days
    SOMEDAY = "someday"  # Nice to have


@dataclass
class ProactiveTask:
    """A proactively discovered task."""
    id: str = field(default_factory=lambda: f"ptask-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    source: DiscoverySource = DiscoverySource.SCHEDULED_SCAN
    urgency: TaskUrgency = TaskUrgency.LATER
    related_memory_ids: list[str] = field(default_factory=list)
    suggested_agent_role: str = "general"
    suggested_action: str = ""  # Natural language action description
    confidence: float = 0.5
    auto_schedulable: bool = False
    estimated_effort: str = "medium"  # low, medium, high
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending"  # pending, scheduled, running, completed, dismissed

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source": self.source.value,
            "urgency": self.urgency.value,
            "related_memory_ids": self.related_memory_ids,
            "suggested_agent_role": self.suggested_agent_role,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
            "auto_schedulable": self.auto_schedulable,
            "estimated_effort": self.estimated_effort,
            "created_at": self.created_at,
            "status": self.status,
        }


@dataclass
class DiscoveryScanResult:
    """Result of a proactive discovery scan."""
    tasks: list[ProactiveTask]
    insights: list[str]
    patterns_detected: int
    scan_duration_ms: float
    scanned_at: str


class ProactiveDiscoveryEngine:
    """Always-on proactive task and opportunity discovery engine.

    Continuously monitors agent state, memory, and context to discover
    actionable tasks and surface them to the user or schedule them
    automatically via the autopilot system.
    """

    def __init__(self, agent_id: str, client: AsyncOpenAI | None = None):
        self.agent_id = agent_id
        self._client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._discovered_tasks: dict[str, ProactiveTask] = {}
        self._insights: list[str] = []
        self._is_running = False
        self._scan_interval = 600  # 10 minutes default
        self._scan_task: asyncio.Task | None = None
        self._last_scan_at: str = ""
        self._total_scans = 0
        self._total_discoveries = 0
        self._recent_interactions: list[dict] = []  # Buffer for interaction-based discovery

    def observe_interaction(self, user_message: str, assistant_response: str):
        """Feed an interaction into the discovery engine for pattern detection.

        Stores recent interactions in a rolling buffer. When the buffer reaches
        threshold, triggers a lightweight inline analysis for immediate insights.
        """
        self._recent_interactions.append({
            "user_message": user_message[:500],
            "assistant_response": assistant_response[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep last 100 interactions
        if len(self._recent_interactions) > 100:
            self._recent_interactions = self._recent_interactions[-100:]

    def get_recent_interactions(self, limit: int = 20) -> list[dict]:
        """Get recent interactions observed by the discovery engine."""
        return self._recent_interactions[-limit:]

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def scan_interval(self) -> int:
        return self._scan_interval

    @property
    def last_scan_at(self) -> str:
        return self._last_scan_at

    @property
    def total_discoveries(self) -> int:
        return self._total_discoveries

    async def start(self, interval: int = 600):
        """Start the always-on proactive discovery loop."""
        self._scan_interval = interval
        self._is_running = True
        if self._scan_task:
            self._scan_task.cancel()
        self._scan_task = asyncio.create_task(self._discovery_loop())
        logger.info(f"Proactive discovery started for {self.agent_id} (interval: {interval}s)")

    async def stop(self):
        """Stop the proactive discovery loop."""
        self._is_running = False
        if self._scan_task:
            self._scan_task.cancel()
            self._scan_task = None
        logger.info(f"Proactive discovery stopped for {self.agent_id}")

    async def _discovery_loop(self):
        """Main discovery loop."""
        await asyncio.sleep(30)  # Initial delay before first scan
        while self._is_running:
            try:
                await self.scan()
            except Exception as e:
                logger.error(f"Discovery scan error for {self.agent_id}: {e}")
            await asyncio.sleep(self._scan_interval)

    async def scan(
        self,
        memory_system: Any = None,
        conversation_history: list[dict] | None = None,
        agent_context: dict | None = None,
    ) -> DiscoveryScanResult:
        """Execute a complete proactive discovery scan across all sources."""
        import time
        start = time.time()

        tasks: list[ProactiveTask] = []
        insights: list[str] = []
        patterns_detected = 0

        # Source 1: Memory pattern detection
        if memory_system:
            try:
                memory_tasks, memory_insights = await self._scan_memory_patterns(memory_system)
                tasks.extend(memory_tasks)
                insights.extend(memory_insights)
                patterns_detected += len(memory_tasks)
            except Exception as e:
                logger.debug(f"Memory pattern scan skipped: {e}")

        # Source 2: Conversation gap detection
        if conversation_history:
            try:
                conv_tasks, conv_insights = await self._scan_conversation_gaps(conversation_history)
                tasks.extend(conv_tasks)
                insights.extend(conv_insights)
                patterns_detected += len(conv_tasks)
            except Exception as e:
                logger.debug(f"Conversation gap scan skipped: {e}")

        # Source 3: Behavioral signal detection
        if agent_context:
            try:
                behavior_tasks = await self._scan_behavioral_signals(agent_context)
                tasks.extend(behavior_tasks)
                patterns_detected += len(behavior_tasks)
            except Exception as e:
                logger.debug(f"Behavioral scan skipped: {e}")

        # Source 4: System optimization recommendations
        try:
            opt_tasks = await self._scan_system_optimizations()
            tasks.extend(opt_tasks)
            patterns_detected += len(opt_tasks)
        except Exception as e:
            logger.debug(f"System optimization scan skipped: {e}")

        # Store discovered tasks
        for task in tasks:
            self._discovered_tasks[task.id] = task

        self._insights.extend(insights)
        self._total_scans += 1
        self._total_discoveries += len(tasks)
        self._last_scan_at = datetime.now(timezone.utc).isoformat()

        elapsed = (time.time() - start) * 1000

        result = DiscoveryScanResult(
            tasks=tasks,
            insights=insights,
            patterns_detected=patterns_detected,
            scan_duration_ms=elapsed,
            scanned_at=self._last_scan_at,
        )

        if tasks:
            logger.info(
                f"Proactive scan: {len(tasks)} tasks discovered for {self.agent_id} "
                f"({elapsed:.0f}ms)"
            )

        return result

    async def _scan_memory_patterns(
        self, memory_system: Any
    ) -> tuple[list[ProactiveTask], list[str]]:
        """Detect recurring themes and needs from memory patterns."""
        tasks: list[ProactiveTask] = []
        insights: list[str] = []

        try:
            recent = await memory_system.recall_recent(limit=30)
            long_term = await memory_system.recall_long_term(limit=20)

            if not recent and not long_term:
                return tasks, insights

            # Build a summary of recent and long-term memories
            memory_summaries = []
            for m in recent[:10]:
                content = str(m.get("content", ""))[:200]
                if content:
                    memory_summaries.append(content)

            if not memory_summaries:
                return tasks, insights

            combined = "\n".join(f"- {s}" for s in memory_summaries[:8])

            # Use LLM to identify patterns and suggest tasks
            try:
                response = await self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "system",
                        "content": (
                            "You are a proactive task discovery system. Analyze recent memory entries "
                            "and identify actionable tasks, recurring themes, or unmet needs. "
                            "Respond in JSON format with a list of tasks.\n"
                            'Format: {"tasks": [{"title": "...", "description": "...", '
                            '"urgency": "now|soon|later|someday", "confidence": 0.0-1.0, '
                            '"auto_schedulable": true|false}]}'
                        ),
                    }, {
                        "role": "user",
                        "content": (
                            f"Recent memory entries:\n{combined}\n\n"
                            "Identify tasks that should be proactively addressed. "
                            "Focus on recurring themes, incomplete items, and opportunities."
                        ),
                    }],
                    max_tokens=500,
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content or "{}"
                import json
                data = json.loads(content)
                llm_tasks = data.get("tasks", [])

                for t in llm_tasks:
                    task = ProactiveTask(
                        title=t.get("title", "Untitled Task"),
                        description=t.get("description", ""),
                        source=DiscoverySource.MEMORY_PATTERN,
                        urgency=TaskUrgency(t.get("urgency", "later")),
                        confidence=float(t.get("confidence", 0.5)),
                        auto_schedulable=bool(t.get("auto_schedulable", False)),
                    )
                    tasks.append(task)

            except Exception as e:
                logger.debug(f"LLM memory pattern analysis skipped: {e}")

            # Also detect simple keyword frequency patterns
            import re
            word_freq: dict[str, int] = {}
            stop_words = {"the", "and", "for", "that", "this", "with", "was", "have", "from", "are", "but", "not", "you", "all", "can", "has", "been", "will"}

            for m in recent + long_term:
                content = str(m.get("content", ""))
                words = re.findall(r'\b\w{4,}\b', content.lower())
                for w in words:
                    if w not in stop_words:
                        word_freq[w] = word_freq.get(w, 0) + 1

            # Find frequently mentioned topics
            frequent_topics = sorted(
                [(w, c) for w, c in word_freq.items() if c >= 3],
                key=lambda x: -x[1],
            )[:5]

            for topic, count in frequent_topics:
                insights.append(
                    f"Recurring theme '{topic}' appears {count} times in recent memories"
                )

        except Exception as e:
            logger.debug(f"Memory pattern scan error: {e}")

        return tasks, insights

    async def _scan_conversation_gaps(
        self, conversation_history: list[dict]
    ) -> tuple[list[ProactiveTask], list[str]]:
        """Detect unanswered questions and incomplete conversation topics."""
        tasks: list[ProactiveTask] = []
        insights: list[str] = []

        if len(conversation_history) < 3:
            return tasks, insights

        # Look for user questions that were asked but may need follow-up
        user_questions = []
        for msg in conversation_history[-20:]:
            if msg.get("role") == "user":
                content = str(msg.get("content", ""))
                if "?" in content or content.lower().startswith(("how", "what", "why", "can", "could", "would")):
                    user_questions.append(content)

        if user_questions and len(user_questions) > 3:
            task = ProactiveTask(
                title="Review recent conversation questions",
                description=(
                    f"Found {len(user_questions)} questions in recent conversations. "
                    "Review these to ensure all were adequately addressed."
                ),
                source=DiscoverySource.CONVERSATION_GAP,
                urgency=TaskUrgency.SOON,
                confidence=0.6,
                auto_schedulable=False,
            )
            tasks.append(task)

        # Check for conversation threads that ended abruptly
        if len(conversation_history) > 10:
            insights.append(
                f"Conversation history has {len(conversation_history)} messages; "
                "consider summarizing long threads into memory"
            )

        return tasks, insights

    async def _scan_behavioral_signals(
        self, agent_context: dict
    ) -> list[ProactiveTask]:
        """Detect patterns from agent behavioral signals."""
        tasks: list[ProactiveTask] = []

        # Check for agent role-specific opportunities
        role = agent_context.get("role", "")

        if role == "engineering":
            tasks.append(ProactiveTask(
                title="Review code quality metrics",
                description="Periodic code review of recent changes to maintain quality standards.",
                source=DiscoverySource.BEHAVIORAL_SIGNAL,
                urgency=TaskUrgency.LATER,
                suggested_agent_role="engineering",
                confidence=0.4,
                auto_schedulable=True,
                estimated_effort="medium",
            ))
        elif role == "strategy":
            tasks.append(ProactiveTask(
                title="Weekly strategy review",
                description="Review recent decisions and update strategic priorities.",
                source=DiscoverySource.BEHAVIORAL_SIGNAL,
                urgency=TaskUrgency.LATER,
                suggested_agent_role="strategy",
                confidence=0.4,
                auto_schedulable=True,
                estimated_effort="low",
            ))
        elif role == "research":
            tasks.append(ProactiveTask(
                title="Research trend analysis",
                description="Analyze recent research topics for emerging trends and patterns.",
                source=DiscoverySource.BEHAVIORAL_SIGNAL,
                urgency=TaskUrgency.SOMEDAY,
                suggested_agent_role="research",
                confidence=0.35,
                auto_schedulable=True,
                estimated_effort="medium",
            ))

        return tasks

    async def _scan_system_optimizations(self) -> list[ProactiveTask]:
        """Detect system-level optimization opportunities."""
        tasks: list[ProactiveTask] = []

        # Check for old/unused items that could be cleaned up
        if len(self._discovered_tasks) > 50:
            tasks.append(ProactiveTask(
                title="Clean up stale discovered tasks",
                description=(
                    f"Found {len(self._discovered_tasks)} discovered tasks. "
                    "Review and dismiss outdated ones."
                ),
                source=DiscoverySource.SYSTEM_OPTIMIZATION,
                urgency=TaskUrgency.LATER,
                confidence=0.5,
                auto_schedulable=False,
            ))

        if len(self._insights) > 100:
            tasks.append(ProactiveTask(
                title="Consolidate discovery insights",
                description="Summarize accumulated insights into actionable themes.",
                source=DiscoverySource.SYSTEM_OPTIMIZATION,
                urgency=TaskUrgency.SOMEDAY,
                confidence=0.4,
                auto_schedulable=False,
            ))

        return tasks

    def get_tasks(
        self,
        status: str | None = None,
        source: str | None = None,
        urgency: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get discovered tasks with optional filtering."""
        result = []
        for task in self._discovered_tasks.values():
            if status and task.status != status:
                continue
            if source and task.source.value != source:
                continue
            if urgency and task.urgency.value != urgency:
                continue
            result.append(task.to_dict())

        # Sort by urgency then confidence
        urgency_order = {"now": 0, "soon": 1, "later": 2, "someday": 3}
        result.sort(key=lambda t: (urgency_order.get(t["urgency"], 999), -t["confidence"]))
        return result[:limit]

    def get_insights(self, limit: int = 20) -> list[str]:
        """Get recent discovery insights."""
        return self._insights[-limit:]

    def schedule_task(self, task_id: str) -> bool:
        """Mark a task as scheduled."""
        task = self._discovered_tasks.get(task_id)
        if not task or task.status != "pending":
            return False
        task.status = "scheduled"
        return True

    def dismiss_task(self, task_id: str) -> bool:
        """Dismiss a discovered task."""
        task = self._discovered_tasks.get(task_id)
        if not task:
            return False
        task.status = "dismissed"
        return True

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        task = self._discovered_tasks.get(task_id)
        if not task:
            return False
        task.status = "completed"
        return True

    def get_stats(self) -> dict:
        """Get discovery engine statistics."""
        statuses: dict[str, int] = {}
        for task in self._discovered_tasks.values():
            statuses[task.status] = statuses.get(task.status, 0) + 1

        source_counts: dict[str, int] = {}
        for task in self._discovered_tasks.values():
            source_counts[task.source.value] = source_counts.get(task.source.value, 0) + 1

        return {
            "agent_id": self.agent_id,
            "is_running": self._is_running,
            "scan_interval": self._scan_interval,
            "total_scans": self._total_scans,
            "total_discoveries": self._total_discoveries,
            "last_scan_at": self._last_scan_at,
            "tasks_by_status": statuses,
            "tasks_by_source": source_counts,
            "total_insights": len(self._insights),
        }


# ── Proactive Bridge ─────────────────────────────────


@dataclass
class NotificationRecord:
    """A record of a proactive notification sent to the user."""
    id: str
    task_id: str
    title: str
    message: str
    sent_at: str
    acknowledged: bool = False


class ProactiveBridge:
    """Connects proactive discovery to autopilot scheduling and user notification.

    This bridge serves as the integration layer between the ProactiveDiscoveryEngine
    and the rest of the Buddy system. When tasks are discovered, it evaluates
    them against confidence thresholds, schedules them automatically when
    appropriate, and notifies the user. It also supports a learning loop
    that improves discovery accuracy based on user feedback.
    """

    def __init__(self, discovery_engine: ProactiveDiscoveryEngine):
        self._engine = discovery_engine
        self._confidence_threshold: float = 0.7  # Minimum confidence for auto-schedule
        self._priority_queue: list[tuple[float, ProactiveTask]] = []
        self._notifications: list[NotificationRecord] = []
        self._quiet_hours_start: int = 22  # 10 PM
        self._quiet_hours_end: int = 7     # 7 AM
        self._quiet_hours_enabled: bool = True
        self._learning_feedback: list[dict[str, Any]] = []
        self._auto_scheduled_count: int = 0
        self._user_dismissed_count: int = 0
        self._daily_digest_enabled: bool = True
        self._digest_last_sent: str = ""
        self._notification_queue: list[ProactiveTask] = []

    # ── Confidence Threshold ──────────────────────────

    @property
    def confidence_threshold(self) -> float:
        """Get the current confidence threshold for auto-scheduling."""
        return self._confidence_threshold

    def set_confidence_threshold(self, threshold: float) -> None:
        """Set the minimum confidence required to auto-schedule a task.

        Args:
            threshold: Float between 0.0 and 1.0. Higher values mean only
                       very confident discoveries are auto-scheduled.
        """
        self._confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info("Proactive confidence threshold set to %.2f", self._confidence_threshold)

    # ── Auto-Scheduling ───────────────────────────────

    def auto_schedule_discovered_task(self, task: ProactiveTask) -> bool:
        """Automatically schedule a discovered task if it meets the criteria.

        A task is auto-scheduled when:
        - Its confidence exceeds the threshold
        - It is marked as auto_schedulable
        - It is not within quiet hours (if enabled)

        Args:
            task: The ProactiveTask to potentially auto-schedule.

        Returns:
            True if the task was auto-scheduled, False otherwise.
        """
        if not task.auto_schedulable:
            return False

        if task.confidence < self._confidence_threshold:
            return False

        if self._is_quiet_hours():
            # Queue for later scheduling
            self._notification_queue.append(task)
            return False

        # Auto-schedule the task
        task.status = "scheduled"
        self._auto_scheduled_count += 1
        logger.info(
            "Auto-scheduled task: %s (confidence: %.2f)",
            task.title, task.confidence,
        )
        return True

    def process_scan_results(self, result: DiscoveryScanResult) -> dict[str, Any]:
        """Process a discovery scan result: auto-schedule, notify, and queue.

        Args:
            result: The DiscoveryScanResult from a completed scan.

        Returns:
            Summary of actions taken.
        """
        auto_scheduled = 0
        notifications_sent = 0

        for task in result.tasks:
            # Add to priority queue
            self._priority_queue.append((task.confidence, task))

            # Try auto-scheduling
            if self.auto_schedule_discovered_task(task):
                auto_scheduled += 1

            # Notify user
            if self._should_notify(task):
                self._send_notification(task)
                notifications_sent += 1

        # Keep priority queue sorted (highest confidence first)
        self._priority_queue.sort(key=lambda x: -x[0])
        # Keep top 1000
        if len(self._priority_queue) > 1000:
            self._priority_queue = self._priority_queue[:1000]

        return {
            "tasks_discovered": len(result.tasks),
            "auto_scheduled": auto_scheduled,
            "notifications_sent": notifications_sent,
            "priority_queue_size": len(self._priority_queue),
        }

    # ── Priority Queue ────────────────────────────────

    def get_priority_queue(
        self, limit: int = 20, include_scheduled: bool = False
    ) -> list[dict[str, Any]]:
        """Get the ranked list of discovered tasks from the priority queue.

        Args:
            limit: Maximum number of tasks to return.
            include_scheduled: Whether to include already-scheduled tasks.

        Returns:
            List of task dicts sorted by priority (confidence + urgency).
        """
        urgency_weights = {
            TaskUrgency.NOW: 1.0,
            TaskUrgency.SOON: 0.7,
            TaskUrgency.LATER: 0.3,
            TaskUrgency.SOMEDAY: 0.1,
        }

        scored = []
        for confidence, task in self._priority_queue:
            if not include_scheduled and task.status in ("scheduled", "dismissed", "completed"):
                continue
            urgency_weight = urgency_weights.get(task.urgency, 0.1)
            combined_score = (confidence * 0.6) + (urgency_weight * 0.4)
            scored.append((combined_score, task))

        scored.sort(key=lambda x: -x[0])
        return [task.to_dict() for _, task in scored[:limit]]

    # ── User Notifications ────────────────────────────

    def _should_notify(self, task: ProactiveTask) -> bool:
        """Determine whether to notify the user about a discovered task."""
        if self._is_quiet_hours():
            return False
        if task.urgency in (TaskUrgency.NOW, TaskUrgency.SOON):
            return True
        if task.confidence >= 0.8:
            return True
        return False

    def _send_notification(self, task: ProactiveTask) -> None:
        """Send a notification to the user about a discovered task.

        In production, this would integrate with email, Slack, or push
        notification services. Currently stores the notification in memory.
        """
        notification = NotificationRecord(
            id=f"notif-{uuid.uuid4().hex[:8]}",
            task_id=task.id,
            title=task.title,
            message=(
                f"Discovered: {task.title}\n"
                f"Urgency: {task.urgency.value}\n"
                f"Confidence: {task.confidence:.0%}\n"
                f"Source: {task.source.value}"
            ),
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
        self._notifications.append(notification)

        # Keep last 500 notifications
        if len(self._notifications) > 500:
            self._notifications = self._notifications[-500:]

        logger.info("Notification sent: %s (task: %s)", notification.id, task.title)

    def get_notifications(
        self, limit: int = 20, unacknowledged_only: bool = False
    ) -> list[dict[str, Any]]:
        """Get recent notification records.

        Args:
            limit: Maximum number of notifications to return.
            unacknowledged_only: If True, only return unacknowledged notifications.

        Returns:
            List of notification dicts.
        """
        results = self._notifications
        if unacknowledged_only:
            results = [n for n in results if not n.acknowledged]
        return [
            {
                "id": n.id,
                "task_id": n.task_id,
                "title": n.title,
                "message": n.message,
                "sent_at": n.sent_at,
                "acknowledged": n.acknowledged,
            }
            for n in results[-limit:]
        ]

    def acknowledge_notification(self, notification_id: str) -> bool:
        """Mark a notification as acknowledged by the user."""
        for notif in self._notifications:
            if notif.id == notification_id:
                notif.acknowledged = True
                return True
        return False

    # ── Daily Digest ──────────────────────────────────

    def generate_daily_digest(self) -> dict[str, Any]:
        """Generate a daily summary of discovered tasks and actions taken.

        Summarizes the last 24 hours of proactive activity: tasks discovered,
        auto-scheduled, completed, dismissed, and pending. Designed to be
        sent to the user at a configurable time each day.

        Returns:
            Digest dict with daily statistics and task summaries.
        """
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(hours=24)).isoformat()

        # Count tasks from last 24 hours
        discovered_today = 0
        scheduled_today = 0
        completed_today = 0
        dismissed_today = 0
        pending_tasks: list[dict] = []

        for task in self._engine._discovered_tasks.values():
            if task.created_at >= cutoff:
                discovered_today += 1
                if task.status == "scheduled":
                    scheduled_today += 1
                elif task.status == "completed":
                    completed_today += 1
                elif task.status == "dismissed":
                    dismissed_today += 1
                elif task.status == "pending":
                    pending_tasks.append(task.to_dict())

        # Top pending tasks
        pending_tasks.sort(key=lambda t: -t["confidence"])
        top_pending = pending_tasks[:5]

        # Notifications count
        notifications_today = sum(
            1 for n in self._notifications
            if n.sent_at >= cutoff
        )

        self._digest_last_sent = now.isoformat()

        return {
            "date": now.strftime("%Y-%m-%d"),
            "generated_at": now.isoformat(),
            "summary": {
                "tasks_discovered": discovered_today,
                "tasks_auto_scheduled": scheduled_today,
                "tasks_completed": completed_today,
                "tasks_dismissed": dismissed_today,
                "tasks_pending": len(pending_tasks),
                "notifications_sent": notifications_today,
            },
            "top_pending_tasks": top_pending,
            "learning_stats": {
                "total_feedback": len(self._learning_feedback),
                "auto_schedule_accuracy": self._calculate_accuracy(),
            },
        }

    def get_daily_digest_status(self) -> dict[str, Any]:
        """Check if a daily digest is due and when it was last sent."""
        return {
            "enabled": self._daily_digest_enabled,
            "last_sent": self._digest_last_sent,
            "pending_notifications": len(self._notification_queue),
        }

    # ── Learning Loop ─────────────────────────────────

    def record_feedback(
        self, task_id: str, was_useful: bool, user_comment: str = ""
    ) -> None:
        """Record user feedback on a discovered task to improve accuracy.

        Feedback is used to adjust the confidence threshold and refine
        future discovery patterns. Positive feedback on auto-scheduled
        tasks reinforces the current threshold; negative feedback
        suggests raising it.

        Args:
            task_id: The ID of the task being rated.
            was_useful: Whether the user found the task useful.
            user_comment: Optional free-text comment from the user.
        """
        feedback = {
            "task_id": task_id,
            "was_useful": was_useful,
            "user_comment": user_comment,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._learning_feedback.append(feedback)

        # Adaptive threshold adjustment
        if was_useful:
            # Slightly lower threshold — we're being too conservative
            self._confidence_threshold = max(0.3, self._confidence_threshold - 0.01)
        else:
            # Slightly raise threshold — we're being too aggressive
            self._confidence_threshold = min(0.95, self._confidence_threshold + 0.02)

        logger.info(
            "Feedback recorded for task %s: useful=%s (new threshold: %.2f)",
            task_id, was_useful, self._confidence_threshold,
        )

    def get_learning_stats(self) -> dict[str, Any]:
        """Return statistics about the learning loop."""
        total = len(self._learning_feedback)
        if total == 0:
            return {"total_feedback": 0, "useful_rate": 0.0, "current_threshold": self._confidence_threshold}

        useful_count = sum(1 for f in self._learning_feedback if f["was_useful"])
        return {
            "total_feedback": total,
            "useful_count": useful_count,
            "not_useful_count": total - useful_count,
            "useful_rate": round(useful_count / total * 100, 1),
            "current_threshold": self._confidence_threshold,
        }

    def _calculate_accuracy(self) -> float:
        """Calculate the accuracy of auto-scheduling decisions."""
        total = len(self._learning_feedback)
        if total == 0:
            return 0.0
        return sum(1 for f in self._learning_feedback if f["was_useful"]) / total

    # ── Quiet Hours ───────────────────────────────────

    def set_quiet_hours(self, start_hour: int, end_hour: int, enabled: bool = True) -> None:
        """Configure quiet hours during which proactive actions are suppressed.

        Args:
            start_hour: Hour (0-23) when quiet hours begin.
            end_hour: Hour (0-23) when quiet hours end.
            enabled: Whether quiet hours are active.
        """
        self._quiet_hours_start = start_hour % 24
        self._quiet_hours_end = end_hour % 24
        self._quiet_hours_enabled = enabled
        logger.info(
            "Quiet hours set: %02d:00 - %02d:00 (enabled=%s)",
            self._quiet_hours_start, self._quiet_hours_end, enabled,
        )

    def get_quiet_hours(self) -> dict[str, Any]:
        """Return current quiet hours configuration."""
        return {
            "enabled": self._quiet_hours_enabled,
            "start_hour": self._quiet_hours_start,
            "end_hour": self._quiet_hours_end,
            "is_active": self._is_quiet_hours(),
        }

    def _is_quiet_hours(self) -> bool:
        """Check if the current time falls within quiet hours."""
        if not self._quiet_hours_enabled:
            return False

        now = datetime.now(timezone.utc)
        current_hour = now.hour

        if self._quiet_hours_start <= self._quiet_hours_end:
            # Normal range: e.g., 22:00 - 07:00
            return current_hour >= self._quiet_hours_start or current_hour < self._quiet_hours_end
        else:
            # Wraps around midnight: e.g., 22:00 - 07:00
            return self._quiet_hours_start <= current_hour < self._quiet_hours_end

    # ── Bridge Statistics ─────────────────────────────

    def get_bridge_stats(self) -> dict[str, Any]:
        """Return comprehensive bridge statistics."""
        return {
            "confidence_threshold": self._confidence_threshold,
            "priority_queue_size": len(self._priority_queue),
            "auto_scheduled_total": self._auto_scheduled_count,
            "user_dismissed_total": self._user_dismissed_count,
            "notifications_total": len(self._notifications),
            "unacknowledged_notifications": sum(
                1 for n in self._notifications if not n.acknowledged
            ),
            "quiet_hours": self.get_quiet_hours(),
            "learning": self.get_learning_stats(),
            "daily_digest": self.get_daily_digest_status(),
        }

    # ── Queue Processing ──────────────────────────────

    def process_queued_notifications(self) -> int:
        """Process any notifications queued during quiet hours.

        Returns:
            Number of notifications sent.
        """
        if self._is_quiet_hours():
            return 0

        sent = 0
        for task in list(self._notification_queue):
            self._send_notification(task)
            sent += 1
        self._notification_queue.clear()
        return sent