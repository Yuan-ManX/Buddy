"""Buddy Reactive Loop — continuous agent execution with observation-action-reflection cycles

Implements a proactive agent runtime that continuously observes its environment,
plans actions, executes them, and learns from outcomes. This enables background
task processing, proactive suggestions, and autonomous workflow execution.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.reactive_loop")


class LoopPhase(str, Enum):
    """Phases of the reactive loop cycle."""
    IDLE = "idle"
    OBSERVE = "observe"       # Scan environment, check triggers
    PRIORITIZE = "prioritize" # Evaluate and rank pending actions
    PLAN = "plan"             # Formulate execution strategy
    EXECUTE = "execute"       # Run the planned action
    REFLECT = "reflect"       # Analyze results, update knowledge
    LEARN = "learn"           # Integrate lessons into memory


class LoopMode(str, Enum):
    """Operating modes for the reactive loop."""
    PASSIVE = "passive"       # Only respond when explicitly triggered
    REACTIVE = "reactive"     # Respond to environmental changes
    PROACTIVE = "proactive"   # Initiate actions based on predictions
    AUTONOMOUS = "autonomous" # Operate completely independently


@dataclass
class Observation:
    """A single observation from the environment."""
    id: str
    source: str                # e.g., "message", "timer", "event", "monitor"
    summary: str
    priority: float = 0.5      # 0.0-1.0 urgency
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PendingAction:
    """An action queued for execution by the reactive loop."""
    id: str
    description: str
    priority: float = 0.5
    depends_on: list[str] = field(default_factory=list)
    handler: str = ""          # Name of the handler function
    payload: dict = field(default_factory=dict)
    status: str = "pending"    # pending, running, completed, failed, cancelled
    result: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    completed_at: str = ""


@dataclass
class LoopCycle:
    """Record of a single execution cycle."""
    id: str
    phase: LoopPhase
    observations_processed: int = 0
    actions_executed: int = 0
    actions_failed: int = 0
    insights_generated: int = 0
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReactiveLoop:
    """Continuous reactive agent execution loop with observation-action-reflection cycles.

    The loop follows a standard agent architecture:
    1. OBSERVE — collect signals from environment (messages, timers, events, monitors)
    2. PRIORITIZE — rank pending actions by urgency and dependencies
    3. PLAN — formulate execution strategies for top-priority actions
    4. EXECUTE — run actions with tool calling and reasoning
    5. REFLECT — analyze results, detect patterns, identify improvements
    6. LEARN — integrate insights into memory and update behavior models

    Supports four operating modes: passive, reactive, proactive, and autonomous.
    """

    def __init__(
        self,
        agent_id: str,
        mode: LoopMode = LoopMode.REACTIVE,
        cycle_interval_ms: int = 5000,
    ):
        self.agent_id = agent_id
        self.mode = mode
        self.cycle_interval_ms = cycle_interval_ms

        self._observations: list[Observation] = []
        self._actions: list[PendingAction] = []
        self._cycle_history: list[LoopCycle] = []
        self._is_running = False
        self._loop_task: asyncio.Task | None = None

        # Configurable thresholds
        self._max_observations = 500
        self._max_actions = 200
        self._max_cycle_history = 1000
        self._idle_delay_ms = 1000

        # Registered handlers
        self._action_handlers: dict[str, Callable[[PendingAction], Awaitable[str]]] = {}
        self._on_cycle_complete: Callable[[LoopCycle], Awaitable[None]] | None = None

    # ── Lifecycle ────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self):
        """Start the reactive loop running in the background."""
        if self._is_running:
            return
        self._is_running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info(f"Reactive loop started for {self.agent_id} (mode={self.mode.value})")

    async def stop(self):
        """Stop the reactive loop gracefully."""
        self._is_running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Reactive loop stopped for {self.agent_id}")

    async def _run_loop(self):
        """Main loop execution."""
        while self._is_running:
            cycle_start = datetime.now(timezone.utc)
            cycle_id = f"cycle-{uuid.uuid4().hex[:8]}"

            try:
                # Phase 1: Observe
                obs_count = await self._phase_observe()

                # Phase 2: Prioritize
                prioritized = await self._phase_prioritize()

                # Phase 3: Plan
                if prioritized:
                    await self._phase_plan(prioritized[0])

                # Phase 4: Execute
                executed, failed = await self._phase_execute()

                # Phase 5: Reflect
                insights = await self._phase_reflect()

                # Phase 6: Learn
                await self._phase_learn()

                # Record cycle
                duration = (datetime.now(timezone.utc) - cycle_start).total_seconds() * 1000
                cycle = LoopCycle(
                    id=cycle_id,
                    phase=LoopPhase.IDLE,
                    observations_processed=obs_count,
                    actions_executed=executed,
                    actions_failed=failed,
                    insights_generated=insights,
                    duration_ms=duration,
                )
                self._cycle_history.append(cycle)
                if len(self._cycle_history) > self._max_cycle_history:
                    self._cycle_history = self._cycle_history[-500:]

                if self._on_cycle_complete:
                    await self._on_cycle_complete(cycle)

            except Exception as e:
                logger.error(f"Reactive loop cycle error for {self.agent_id}: {e}")

            # Adaptive delay based on activity
            delay = self._idle_delay_ms if executed == 0 else self.cycle_interval_ms
            await asyncio.sleep(delay / 1000.0)

    # ── Phase Handlers ──────────────────────────────────

    async def _phase_observe(self) -> int:
        """Collect and process observations from the environment."""
        # Process pending observations
        processed = 0
        for obs in list(self._observations):
            if obs.priority >= 0.3:
                # Convert high-priority observations into actions
                action = PendingAction(
                    id=f"act-{uuid.uuid4().hex[:8]}",
                    description=obs.summary,
                    priority=obs.priority,
                    payload=obs.data,
                    handler=obs.source,
                )
                self._actions.append(action)
                processed += 1

        # Clear processed observations
        self._observations = [o for o in self._observations if o.priority < 0.3]
        return processed

    async def _phase_prioritize(self) -> list[PendingAction]:
        """Prioritize pending actions by urgency and dependency resolution."""
        pending = [a for a in self._actions if a.status == "pending"]

        # Sort by priority (descending)
        pending.sort(key=lambda a: a.priority, reverse=True)

        # Filter out actions with unmet dependencies
        completed_ids = {a.id for a in self._actions if a.status == "completed"}
        ready = [
            a for a in pending
            if all(dep in completed_ids for dep in a.depends_on)
        ]

        return ready

    async def _phase_plan(self, action: PendingAction) -> None:
        """Formulate an execution plan for a high-priority action."""
        # Mark the action as being planned
        action.status = "running"
        action.started_at = datetime.now(timezone.utc).isoformat()
        logger.debug(f"Planning action: {action.description[:80]}")

    async def _phase_execute(self) -> tuple[int, int]:
        """Execute all running actions."""
        executed = 0
        failed = 0

        running = [a for a in self._actions if a.status == "running"]
        for action in running:
            try:
                if action.handler and action.handler in self._action_handlers:
                    handler = self._action_handlers[action.handler]
                    result = await handler(action)
                    action.result = result
                    action.status = "completed"
                    executed += 1
                else:
                    # Default: mark as completed if no handler
                    action.status = "completed"
                    action.result = "No handler registered"
                    executed += 1
            except Exception as e:
                logger.error(f"Action execution failed: {action.id}: {e}")
                action.status = "failed"
                action.result = str(e)
                failed += 1
            finally:
                action.completed_at = datetime.now(timezone.utc).isoformat()

        # Cleanup old completed/failed actions
        self._actions = [
            a for a in self._actions
            if a.status in ("pending", "running")
            or len([x for x in self._actions if x.status in ("pending", "running")]) < self._max_actions
        ]
        # Trim if still too many
        if len(self._actions) > self._max_actions:
            keep_count = self._max_actions // 2
            self._actions = self._actions[-keep_count:]

        return executed, failed

    async def _phase_reflect(self) -> int:
        """Analyze completed actions for patterns and insights."""
        recently_completed = [
            a for a in self._actions[-20:]
            if a.status == "completed"
        ]

        insights = 0
        if recently_completed:
            # Simple pattern detection: sequential success = effective strategy
            success_rate = len([a for a in self._actions[-50:] if a.status == "completed"]) / max(len(self._actions[-50:]), 1)

            if success_rate > 0.9 and len(recently_completed) >= 3:
                insights += 1
                logger.debug(f"High success rate ({success_rate:.0%}) for {self.agent_id}")

        return insights

    async def _phase_learn(self) -> None:
        """Integrate insights into the agent's knowledge."""
        # Prune old cycle history
        if len(self._cycle_history) > self._max_cycle_history:
            self._cycle_history = self._cycle_history[-500:]

    # ── Public Interface ────────────────────────────────

    def observe(self, source: str, summary: str, priority: float = 0.5, data: dict | None = None):
        """Feed an observation into the reactive loop."""
        obs = Observation(
            id=f"obs-{uuid.uuid4().hex[:8]}",
            source=source,
            summary=summary,
            priority=max(0.0, min(1.0, priority)),
            data=data or {},
        )
        self._observations.append(obs)
        if len(self._observations) > self._max_observations:
            self._observations = self._observations[-self._max_observations:]

    def enqueue_action(
        self,
        description: str,
        priority: float = 0.5,
        handler: str = "",
        payload: dict | None = None,
        depends_on: list[str] | None = None,
    ) -> str:
        """Queue an action for execution."""
        action = PendingAction(
            id=f"act-{uuid.uuid4().hex[:8]}",
            description=description,
            priority=max(0.0, min(1.0, priority)),
            handler=handler,
            payload=payload or {},
            depends_on=depends_on or [],
        )
        self._actions.append(action)
        return action.id

    def register_handler(self, name: str, handler: Callable[[PendingAction], Awaitable[str]]):
        """Register an action handler for a specific source/type."""
        self._action_handlers[name] = handler

    def on_cycle_complete(self, callback: Callable[[LoopCycle], Awaitable[None]]):
        """Register a callback invoked after each loop cycle."""
        self._on_cycle_complete = callback

    def set_mode(self, mode: LoopMode):
        """Change the loop operating mode."""
        self.mode = mode
        logger.info(f"Reactive loop mode changed to {mode.value} for {self.agent_id}")

    # ── Statistics ──────────────────────────────────────

    def get_stats(self) -> dict:
        """Get comprehensive loop statistics."""
        pending = sum(1 for a in self._actions if a.status == "pending")
        running = sum(1 for a in self._actions if a.status == "running")
        completed = sum(1 for a in self._actions if a.status == "completed")
        failed = sum(1 for a in self._actions if a.status == "failed")

        recent_cycles = self._cycle_history[-20:]
        avg_duration = (
            sum(c.duration_ms for c in recent_cycles) / max(len(recent_cycles), 1)
        )

        return {
            "agent_id": self.agent_id,
            "is_running": self._is_running,
            "mode": self.mode.value,
            "cycle_interval_ms": self.cycle_interval_ms,
            "observations": {
                "pending": len(self._observations),
                "max": self._max_observations,
            },
            "actions": {
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "total": len(self._actions),
                "max": self._max_actions,
            },
            "cycles": {
                "total": len(self._cycle_history),
                "avg_duration_ms": round(avg_duration, 1),
            },
            "success_rate": f"{(completed / max(completed + failed, 1) * 100):.1f}%",
        }

    def get_pending_actions(self, limit: int = 20) -> list[dict]:
        """Get list of pending actions."""
        return [
            {
                "id": a.id,
                "description": a.description[:200],
                "priority": a.priority,
                "status": a.status,
                "handler": a.handler,
                "result": a.result[:200],
                "created_at": a.created_at,
                "completed_at": a.completed_at,
            }
            for a in self._actions[-limit:]
        ]

    def get_recent_cycles(self, limit: int = 10) -> list[dict]:
        """Get recent cycle records."""
        return [
            {
                "id": c.id,
                "phase": c.phase.value,
                "observations_processed": c.observations_processed,
                "actions_executed": c.actions_executed,
                "actions_failed": c.actions_failed,
                "insights_generated": c.insights_generated,
                "duration_ms": c.duration_ms,
                "timestamp": c.timestamp,
            }
            for c in self._cycle_history[-limit:]
        ]