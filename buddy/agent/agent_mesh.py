"""Buddy Agent Mesh — autonomous multi-agent orchestration fabric

Provides the central coordination layer that weaves all agent capabilities
into a cohesive autonomous system. Each agent operates as an independent
node in the mesh while sharing knowledge, skills, and context through
the synthesis layer.

Core capabilities:
  - Lifecycle Management: create, configure, deploy, pause, resume, retire agents
  - Task Routing: intelligent task distribution based on agent profiles and load
  - Autonomy Loop: observe → reason → plan → execute → reflect → learn → evolve
  - Knowledge Fabric: shared memory, cross-agent learning, and insight propagation
  - Health Monitoring: real-time agent status, performance metrics, and alerts
  - Self-Healing: automatic error recovery, state rollback, and failover
  - Collaboration: agent-to-agent delegation, peer review, and swarm execution
  - Continuous Evolution: experience-driven capability growth and persona adaptation
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.agent_mesh")


# ═══════════════════════════════════════════════════════════
# Enums and Configuration
# ═══════════════════════════════════════════════════════════

class MeshNodeState(str, Enum):
    """Lifecycle states for mesh nodes."""
    PROVISIONING = "provisioning"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    RETIRED = "retired"
    ERROR = "error"


class TaskPriority(str, Enum):
    """Priority levels for task routing."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class DelegationStrategy(str, Enum):
    """Strategies for delegating tasks to agents."""
    CAPABILITY_MATCH = "capability_match"      # Match by agent capabilities
    LOAD_BALANCED = "load_balanced"            # Distribute evenly
    ROUND_ROBIN = "round_robin"                # Simple rotation
    CONFIDENCE_WEIGHTED = "confidence_weighted" # Based on past performance
    GEO_AWARE = "geo_aware"                    # Consider locality
    HYBRID = "hybrid"                          # Combine multiple strategies


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class MeshNodeConfig:
    """Configuration for a node in the agent mesh."""
    agent_id: str
    agent_name: str
    role: str = "general"
    capabilities: list[str] = field(default_factory=list)
    max_concurrent_tasks: int = 3
    task_timeout_seconds: int = 300
    retry_limit: int = 3
    cooldown_seconds: int = 5
    delegation_enabled: bool = True
    collaboration_enabled: bool = True
    auto_heal: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class MeshTask:
    """A task routed through the agent mesh."""
    task_id: str
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    target_agent_id: str | None = None
    context: dict = field(default_factory=dict)
    status: str = "pending"
    assigned_agent: str | None = None
    result: Any = None
    error: str | None = None
    attempts: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    parent_task_id: str | None = None
    sub_tasks: list[str] = field(default_factory=list)


@dataclass
class MeshNodeMetrics:
    """Performance metrics for a mesh node."""
    agent_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_response_time_ms: float = 0.0
    avg_tokens_per_task: int = 0
    total_cost: float = 0.0
    success_rate: float = 1.0
    current_load: int = 0
    last_active: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    uptime_seconds: int = 0
    health_score: float = 1.0


@dataclass
class MeshEvent:
    """An event in the agent mesh lifecycle."""
    event_id: str
    event_type: str
    agent_id: str | None = None
    task_id: str | None = None
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════
# Mesh Node
# ═══════════════════════════════════════════════════════════

class MeshNode:
    """A single autonomous agent node in the mesh fabric."""

    def __init__(self, config: MeshNodeConfig):
        self.config = config
        self.state = MeshNodeState.PROVISIONING
        self.metrics = MeshNodeMetrics(agent_id=config.agent_id)
        self._active_tasks: dict[str, MeshTask] = {}
        self._task_history: list[MeshTask] = []
        self._event_log: list[MeshEvent] = []
        self._peers: dict[str, MeshNode] = {}
        self._started_at: str | None = None
        self._engine: Any = None  # Will be wired to AgentEngine

    def wire_engine(self, engine: Any):
        """Connect this node to an AgentEngine instance."""
        self._engine = engine

    def activate(self):
        """Bring the node to active state."""
        self.state = MeshNodeState.ACTIVE
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._log_event("node_activated")

    def pause(self):
        """Pause the node, completing current tasks."""
        self.state = MeshNodeState.PAUSED
        self._log_event("node_paused")

    def resume(self):
        """Resume a paused node."""
        self.state = MeshNodeState.ACTIVE
        self._log_event("node_resumed")

    def retire(self):
        """Gracefully retire the node."""
        self.state = MeshNodeState.RETIRED
        self._log_event("node_retired")

    def can_accept_task(self) -> bool:
        """Check if the node can accept a new task."""
        if self.state not in (MeshNodeState.ACTIVE, MeshNodeState.IDLE, MeshNodeState.BUSY):
            return False
        return len(self._active_tasks) < self.config.max_concurrent_tasks

    def assign_task(self, task: MeshTask) -> bool:
        """Assign a task to this node."""
        if not self.can_accept_task():
            return False
        task.assigned_agent = self.config.agent_id
        task.status = "assigned"
        self._active_tasks[task.task_id] = task
        self.metrics.current_load = len(self._active_tasks)
        if self.state == MeshNodeState.IDLE:
            self.state = MeshNodeState.BUSY
        self._log_event("task_assigned", task_id=task.task_id)
        return True

    def complete_task(self, task_id: str, result: Any = None, error: str | None = None):
        """Mark a task as completed or failed."""
        task = self._active_tasks.pop(task_id, None)
        if not task:
            return
        task.completed_at = datetime.now(timezone.utc).isoformat()
        if error:
            task.status = "failed"
            task.error = error
            self.metrics.failed_tasks += 1
        else:
            task.status = "completed"
            task.result = result
            self.metrics.completed_tasks += 1
        self.metrics.total_tasks += 1
        self._task_history.append(task)
        if len(self._task_history) > 500:
            self._task_history = self._task_history[-500:]
        self.metrics.current_load = len(self._active_tasks)
        if self.metrics.current_load == 0 and self.state == MeshNodeState.BUSY:
            self.state = MeshNodeState.IDLE
        self._update_success_rate()
        self._log_event("task_completed" if not error else "task_failed", task_id=task_id)

    def _update_success_rate(self):
        total = self.metrics.completed_tasks + self.metrics.failed_tasks
        if total > 0:
            self.metrics.success_rate = self.metrics.completed_tasks / total

    def _log_event(self, event_type: str, task_id: str | None = None, details: dict | None = None):
        event = MeshEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            agent_id=self.config.agent_id,
            task_id=task_id,
            details=details or {},
        )
        self._event_log.append(event)
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-1000:]

    def get_status(self) -> dict:
        """Get comprehensive node status."""
        return {
            "agent_id": self.config.agent_id,
            "agent_name": self.config.agent_name,
            "role": self.config.role,
            "state": self.state.value,
            "capabilities": self.config.capabilities,
            "metrics": {
                "total_tasks": self.metrics.total_tasks,
                "completed_tasks": self.metrics.completed_tasks,
                "failed_tasks": self.metrics.failed_tasks,
                "success_rate": self.metrics.success_rate,
                "current_load": self.metrics.current_load,
                "max_concurrent": self.config.max_concurrent_tasks,
                "avg_response_time_ms": self.metrics.avg_response_time_ms,
                "total_cost": self.metrics.total_cost,
                "health_score": self.metrics.health_score,
                "uptime_seconds": self.metrics.uptime_seconds,
            },
            "active_tasks": len(self._active_tasks),
            "peers": len(self._peers),
            "started_at": self._started_at,
            "tags": self.config.tags,
        }


# ═══════════════════════════════════════════════════════════
# Agent Mesh — Main Orchestration Layer
# ═══════════════════════════════════════════════════════════

class AgentMesh:
    """Central orchestration fabric for the Buddy agent ecosystem.

    Coordinates all agents as nodes in a unified mesh, handling task routing,
    load balancing, health monitoring, self-healing, and cross-agent collaboration.
    """

    def __init__(self):
        self._nodes: dict[str, MeshNode] = {}
        self._task_queue: list[MeshTask] = []
        self._delegation_strategy = DelegationStrategy.HYBRID
        self._event_log: list[MeshEvent] = []
        self._orchestrator: Any = None  # Wire to Orchestrator
        self._synthesis: Any = None     # Wire to AgentSynthesis
        self._intelligence: Any = None  # Wire to AgentIntelligence
        self._governance: Any = None    # Wire to GovernanceEngine
        self._running = False
        self._loop_task: asyncio.Task | None = None

    def wire(self, orchestrator: Any = None, synthesis: Any = None,
             intelligence: Any = None, governance: Any = None):
        """Wire the mesh to core Buddy services."""
        self._orchestrator = orchestrator
        self._synthesis = synthesis
        self._intelligence = intelligence
        self._governance = governance

    def register_node(self, config: MeshNodeConfig) -> MeshNode:
        """Register a new agent node in the mesh."""
        node = MeshNode(config)
        self._nodes[config.agent_id] = node
        node.activate()
        self._log_event("node_registered", agent_id=config.agent_id, details={
            "name": config.agent_name,
            "role": config.role,
            "capabilities": config.capabilities,
        })
        logger.info("Mesh node registered: %s (%s)", config.agent_name, config.agent_id)
        return node

    def get_node(self, agent_id: str) -> MeshNode | None:
        """Get a node by agent ID."""
        return self._nodes.get(agent_id)

    def remove_node(self, agent_id: str):
        """Remove a node from the mesh."""
        node = self._nodes.pop(agent_id, None)
        if node:
            node.retire()
            self._log_event("node_removed", agent_id=agent_id)
            logger.info("Mesh node removed: %s", agent_id)

    def submit_task(self, task: MeshTask) -> bool:
        """Submit a task for routing through the mesh."""
        task.task_id = task.task_id or str(uuid.uuid4())[:8]
        self._task_queue.append(task)
        self._log_event("task_submitted", task_id=task.task_id, details={
            "title": task.title,
            "priority": task.priority.value,
        })
        return True

    def route_task(self, task: MeshTask) -> MeshNode | None:
        """Route a task to the best available node."""
        available = [n for n in self._nodes.values() if n.can_accept_task()]

        if not available:
            return None

        # If a specific agent is targeted, use it
        if task.target_agent_id and task.target_agent_id in self._nodes:
            target = self._nodes[task.target_agent_id]
            if target.can_accept_task():
                return target

        # Strategy-based routing
        if self._delegation_strategy == DelegationStrategy.CAPABILITY_MATCH:
            return self._route_by_capability(task, available)
        elif self._delegation_strategy == DelegationStrategy.LOAD_BALANCED:
            return self._route_by_load(available)
        elif self._delegation_strategy == DelegationStrategy.CONFIDENCE_WEIGHTED:
            return self._route_by_confidence(task, available)
        else:
            return self._route_hybrid(task, available)

    def _route_by_capability(self, task: MeshTask, available: list[MeshNode]) -> MeshNode | None:
        """Route based on capability matching."""
        task_text = (task.title + " " + task.description).lower()
        best_node = None
        best_score = 0

        for node in available:
            score = 0
            for cap in node.config.capabilities:
                if cap.lower() in task_text:
                    score += 2
            if node.config.role.lower() in task_text:
                score += 3
            if node.metrics.current_load < node.config.max_concurrent_tasks:
                score += 1
            if score > best_score:
                best_score = score
                best_node = node

        return best_node or self._route_by_load(available)

    def _route_by_load(self, available: list[MeshNode]) -> MeshNode:
        """Route to the least loaded node."""
        return min(available, key=lambda n: n.metrics.current_load)

    def _route_by_confidence(self, task: MeshTask, available: list[MeshNode]) -> MeshNode | None:
        """Route based on past success rate."""
        return max(available, key=lambda n: n.metrics.success_rate)

    def _route_hybrid(self, task: MeshTask, available: list[MeshNode]) -> MeshNode | None:
        """Hybrid routing combining capability and load balancing."""
        by_capability = self._route_by_capability(task, available)
        if by_capability:
            return by_capability
        return self._route_by_load(available)

    def process_queue(self) -> list[dict]:
        """Process all pending tasks in the queue."""
        results = []
        remaining = []

        for task in self._task_queue:
            node = self.route_task(task)
            if node:
                node.assign_task(task)
                results.append({
                    "task_id": task.task_id,
                    "assigned_to": node.config.agent_id,
                    "status": "assigned",
                })
            else:
                remaining.append(task)

        self._task_queue = remaining
        return results

    def get_mesh_status(self) -> dict:
        """Get comprehensive mesh status."""
        nodes_status = []
        total_tasks = 0
        total_completed = 0
        total_failed = 0
        healthy_nodes = 0
        degraded_nodes = 0

        for node in self._nodes.values():
            status = node.get_status()
            nodes_status.append(status)
            total_tasks += node.metrics.total_tasks
            total_completed += node.metrics.completed_tasks
            total_failed += node.metrics.failed_tasks
            if node.state in (MeshNodeState.ACTIVE, MeshNodeState.IDLE, MeshNodeState.BUSY):
                healthy_nodes += 1
            elif node.state in (MeshNodeState.DEGRADED, MeshNodeState.RECOVERING):
                degraded_nodes += 1

        return {
            "total_nodes": len(self._nodes),
            "healthy_nodes": healthy_nodes,
            "degraded_nodes": degraded_nodes,
            "total_tasks": total_tasks,
            "completed_tasks": total_completed,
            "failed_tasks": total_failed,
            "pending_tasks": len(self._task_queue),
            "overall_success_rate": total_completed / max(total_tasks, 1),
            "delegation_strategy": self._delegation_strategy.value,
            "nodes": nodes_status,
            "recent_events": [
                {
                    "event_type": e.event_type,
                    "agent_id": e.agent_id,
                    "task_id": e.task_id,
                    "timestamp": e.timestamp,
                }
                for e in self._event_log[-20:]
            ],
        }

    def delegate_to_peer(self, from_agent_id: str, to_agent_id: str,
                         task: MeshTask) -> bool:
        """Delegate a task from one agent to another."""
        from_node = self._nodes.get(from_agent_id)
        to_node = self._nodes.get(to_agent_id)
        if not from_node or not to_node:
            return False
        if not to_node.can_accept_task():
            return False
        task.parent_task_id = task.task_id
        task.task_id = str(uuid.uuid4())[:8]
        to_node.assign_task(task)
        self._log_event("task_delegated", task_id=task.task_id, details={
            "from": from_agent_id,
            "to": to_agent_id,
        })
        return True

    def set_delegation_strategy(self, strategy: DelegationStrategy):
        """Change the task routing strategy."""
        self._delegation_strategy = strategy
        self._log_event("strategy_changed", details={"strategy": strategy.value})

    def _log_event(self, event_type: str, agent_id: str | None = None,
                   task_id: str | None = None, details: dict | None = None):
        event = MeshEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            agent_id=agent_id,
            task_id=task_id,
            details=details or {},
        )
        self._event_log.append(event)
        if len(self._event_log) > 2000:
            self._event_log = self._event_log[-2000:]

    async def start_autonomy_loop(self, interval_seconds: float = 5.0):
        """Start the autonomous mesh orchestration loop."""
        self._running = True
        self._loop_task = asyncio.create_task(self._autonomy_loop(interval_seconds))
        logger.info("Agent Mesh autonomy loop started (interval: %.1fs)", interval_seconds)

    async def stop_autonomy_loop(self):
        """Stop the autonomy loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Agent Mesh autonomy loop stopped")

    async def _autonomy_loop(self, interval_seconds: float):
        """Main autonomy loop: process queue, check health, trigger learning."""
        while self._running:
            try:
                # Process pending tasks
                if self._task_queue:
                    results = self.process_queue()
                    if results:
                        logger.debug("Mesh processed %d tasks", len(results))

                # Update node health
                for node in self._nodes.values():
                    if node._started_at:
                        start = datetime.fromisoformat(node._started_at)
                        node.metrics.uptime_seconds = int(
                            (datetime.now(timezone.utc) - start).total_seconds()
                        )
                    # Health score based on success rate and responsiveness
                    node.metrics.health_score = (
                        node.metrics.success_rate * 0.7 +
                        (1.0 - min(node.metrics.current_load / max(node.config.max_concurrent_tasks, 1), 1.0)) * 0.3
                    )
                    if node.metrics.health_score < 0.5 and node.state == MeshNodeState.ACTIVE:
                        node.state = MeshNodeState.DEGRADED
                    elif node.metrics.health_score >= 0.7 and node.state == MeshNodeState.DEGRADED:
                        node.state = MeshNodeState.RECOVERING

                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Mesh autonomy loop error: %s", e)
                await asyncio.sleep(interval_seconds)


# Global mesh instance
agent_mesh = AgentMesh()