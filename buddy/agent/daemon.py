"""Buddy Agent Daemon — Background agent runtime management

Manages agent lifecycle in background mode:
- Starting/stopping agent background processes
- Health monitoring and automatic restart
- Resource allocation (concurrency limits, memory limits)
- Idle detection and hibernation
- Runtime statistics collection

Inspired by daemon-based agent orchestration for always-on agents
that can execute tasks without an active user session.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.daemon")


class DaemonStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    HIBERNATING = "hibernating"
    ERROR = "error"
    STOPPING = "stopping"


class AgentRuntime:
    """Represents a single agent's daemon runtime with lifecycle management."""

    def __init__(self, agent_id: str, agent_name: str, config: dict | None = None):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.status = DaemonStatus.STOPPED
        self.config = config or {}
        self.max_concurrency: int = self.config.get("max_concurrency", 5)
        self.idle_timeout: int = self.config.get("idle_timeout", 300)  # seconds
        self.hibernate_timeout: int = self.config.get("hibernate_timeout", 3600)  # seconds
        self.auto_restart: bool = self.config.get("auto_restart", True)

        # Runtime statistics
        self._started_at: str = ""
        self._last_active: str = ""
        self._tasks_completed: int = 0
        self._tasks_failed: int = 0
        self._total_runtime: float = 0.0  # seconds
        self._restart_count: int = 0
        self._current_concurrency: int = 0

        # Background task
        self._monitor_task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self.status in {DaemonStatus.RUNNING, DaemonStatus.IDLE}

    async def start(self) -> bool:
        """Start the agent daemon runtime."""
        if self.is_running:
            logger.warning(f"Agent {self.agent_id} is already running")
            return False

        self.status = DaemonStatus.STARTING
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._last_active = self._started_at

        # Simulate startup
        await asyncio.sleep(0.1)
        self.status = DaemonStatus.RUNNING

        # Start health monitor
        self._monitor_task = asyncio.create_task(self._health_monitor())
        logger.info(f"Agent daemon started for {self.agent_name} ({self.agent_id})")
        return True

    async def stop(self) -> bool:
        """Stop the agent daemon runtime."""
        if self.status == DaemonStatus.STOPPED:
            return False

        self.status = DaemonStatus.STOPPING
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None

        # Calculate runtime
        if self._started_at:
            start = datetime.fromisoformat(self._started_at)
            self._total_runtime += (datetime.now(timezone.utc) - start).total_seconds()

        self.status = DaemonStatus.STOPPED
        logger.info(f"Agent daemon stopped for {self.agent_name} ({self.agent_id})")
        return True

    async def restart(self) -> bool:
        """Restart the agent daemon runtime."""
        self._restart_count += 1
        await self.stop()
        return await self.start()

    def mark_active(self):
        """Mark the agent as recently active (prevents hibernation)."""
        self._last_active = datetime.now(timezone.utc).isoformat()
        if self.status == DaemonStatus.IDLE:
            self.status = DaemonStatus.RUNNING

    def record_task_completion(self, success: bool = True):
        """Record a completed task execution."""
        if success:
            self._tasks_completed += 1
        else:
            self._tasks_failed += 1
        self.mark_active()

    def increment_concurrency(self) -> bool:
        """Try to increment concurrency. Returns False if at limit."""
        if self._current_concurrency >= self.max_concurrency:
            return False
        self._current_concurrency += 1
        return True

    def decrement_concurrency(self):
        """Decrement current concurrency."""
        self._current_concurrency = max(0, self._current_concurrency - 1)

    async def _health_monitor(self):
        """Background task that monitors agent health and manages state transitions."""
        while self.is_running:
            await asyncio.sleep(30)  # Check every 30 seconds

            if not self.is_running:
                break

            # Check for idle transition
            if self._last_active:
                last_active = datetime.fromisoformat(self._last_active)
                idle_seconds = (datetime.now(timezone.utc) - last_active).total_seconds()

                if idle_seconds > self.hibernate_timeout:
                    self.status = DaemonStatus.HIBERNATING
                    logger.info(f"Agent {self.agent_id} entering hibernation after {idle_seconds:.0f}s idle")
                elif idle_seconds > self.idle_timeout:
                    self.status = DaemonStatus.IDLE

    def get_stats(self) -> dict:
        """Get runtime statistics."""
        uptime = 0.0
        if self._started_at and self.is_running:
            start = datetime.fromisoformat(self._started_at)
            uptime = (datetime.now(timezone.utc) - start).total_seconds()

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "uptime_seconds": int(uptime),
            "total_runtime": int(self._total_runtime),
            "tasks_completed": self._tasks_completed,
            "tasks_failed": self._tasks_failed,
            "success_rate": (
                self._tasks_completed / max(self._tasks_completed + self._tasks_failed, 1)
            ),
            "restart_count": self._restart_count,
            "concurrency": {
                "current": self._current_concurrency,
                "max": self.max_concurrency,
            },
            "started_at": self._started_at,
            "last_active": self._last_active,
            "auto_restart": self.auto_restart,
        }


class DaemonManager:
    """Manages all agent daemons with global orchestration.

    Provides system-wide daemon lifecycle management, resource
    coordination, and health monitoring across all agents.
    """

    def __init__(self, max_total_concurrency: int = 50):
        self._runtimes: dict[str, AgentRuntime] = {}
        self.max_total_concurrency = max_total_concurrency

    def get_runtime(self, agent_id: str, agent_name: str = "", config: dict | None = None) -> AgentRuntime:
        """Get or create an agent runtime."""
        if agent_id not in self._runtimes:
            self._runtimes[agent_id] = AgentRuntime(agent_id, agent_name, config)
        return self._runtimes[agent_id]

    async def start_agent(self, agent_id: str, agent_name: str = "", config: dict | None = None) -> bool:
        """Start a specific agent daemon."""
        runtime = self.get_runtime(agent_id, agent_name, config)
        return await runtime.start()

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a specific agent daemon."""
        runtime = self._runtimes.get(agent_id)
        if not runtime:
            return False
        return await runtime.stop()

    async def restart_agent(self, agent_id: str) -> bool:
        """Restart a specific agent daemon."""
        runtime = self._runtimes.get(agent_id)
        if not runtime:
            return False
        return await runtime.restart()

    async def stop_all(self):
        """Stop all agent daemons."""
        for runtime in list(self._runtimes.values()):
            await runtime.stop()
        logger.info("All agent daemons stopped")

    async def start_all(self):
        """Start all registered agent daemons."""
        started = 0
        for runtime in self._runtimes.values():
            if await runtime.start():
                started += 1
        logger.info(f"Started {started} agent daemons")

    def mark_agent_active(self, agent_id: str):
        """Mark an agent as active to prevent hibernation."""
        runtime = self._runtimes.get(agent_id)
        if runtime:
            runtime.mark_active()

    def get_total_concurrency(self) -> int:
        """Get current total concurrency across all agents."""
        return sum(r._current_concurrency for r in self._runtimes.values())

    def can_accept_task(self, agent_id: str) -> bool:
        """Check if an agent can accept more tasks."""
        if self.get_total_concurrency() >= self.max_total_concurrency:
            return False
        runtime = self._runtimes.get(agent_id)
        if not runtime or not runtime.is_running:
            return False
        return runtime._current_concurrency < runtime.max_concurrency

    def get_stats(self) -> dict:
        """Get comprehensive daemon manager statistics."""
        runtimes = [r.get_stats() for r in self._runtimes.values()]
        status_counts = {
            s.value: sum(1 for r in runtimes if r["status"] == s.value)
            for s in DaemonStatus
        }
        return {
            "total_agents": len(self._runtimes),
            "active_agents": sum(1 for r in self._runtimes.values() if r.is_running),
            "status_distribution": status_counts,
            "total_concurrency": self.get_total_concurrency(),
            "max_total_concurrency": self.max_total_concurrency,
            "runtimes": runtimes,
        }


# Global singleton
daemon_manager = DaemonManager()