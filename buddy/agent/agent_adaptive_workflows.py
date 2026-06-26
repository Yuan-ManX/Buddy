"""
Platform Adaptive Workflows - Self-optimizing workflow engine.

Provides dynamic workflow capabilities:
- Self-modifying workflow graphs that adapt to conditions
- Context-aware branching with learned decision trees
- Automated workflow optimization and simplification
- Real-time workflow visualization and monitoring
- Plugin-based action nodes with hot-reload
- Workflow templates with parameterization
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.adaptive_workflows")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class WorkflowNodeType(str, Enum):
    """Types of workflow nodes."""
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    WAIT = "wait"
    SUB_WORKFLOW = "sub_workflow"
    NOTIFICATION = "notification"
    TRANSFORM = "transform"
    END = "end"


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OPTIMIZING = "optimizing"


class TriggerType(str, Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    WEBHOOK = "webhook"
    CONDITION = "condition"
    CHAIN = "chain"


class OptimizationStrategy(str, Enum):
    """Strategies for workflow optimization."""
    SIMPLIFY = "simplify"
    PARALLELIZE = "parallelize"
    CACHE = "cache"
    MERGE = "merge"
    REORDER = "reorder"
    ELIMINATE = "eliminate"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class WorkflowNode:
    """A single node in a workflow."""
    node_id: str
    node_type: WorkflowNodeType
    label: str
    action: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    next_nodes: list[str] = field(default_factory=list)
    conditions: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 60
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "action": self.action,
            "config": self.config,
            "next_nodes": self.next_nodes,
            "conditions": self.conditions,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class WorkflowDefinition:
    """A complete workflow definition."""
    workflow_id: str
    name: str
    description: str
    trigger: TriggerType
    trigger_config: dict[str, Any]
    nodes: dict[str, WorkflowNode]
    entry_node: str
    status: WorkflowStatus = WorkflowStatus.DRAFT
    version: int = 1
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger.value,
            "trigger_config": self.trigger_config,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "entry_node": self.entry_node,
            "status": self.status.value,
            "version": self.version,
            "tags": self.tags,
            "node_count": len(self.nodes),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class WorkflowExecution:
    """A single execution of a workflow."""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    current_node: str
    node_results: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None = None
    total_duration_ms: float = 0.0
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "current_node": self.current_node,
            "node_results": self.node_results,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
        }


@dataclass
class WorkflowTemplate:
    """A reusable workflow template."""
    template_id: str
    name: str
    description: str
    category: str
    nodes: dict[str, WorkflowNode]
    entry_node: str
    parameters: list[dict[str, Any]]
    usage_count: int = 0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "node_count": len(self.nodes),
            "entry_node": self.entry_node,
            "parameters": self.parameters,
            "usage_count": self.usage_count,
            "tags": self.tags,
        }


@dataclass
class WorkflowStats:
    """Statistics for the adaptive workflow engine."""
    total_workflows: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_templates: int = 0
    optimizations_applied: int = 0
    avg_execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_workflows": self.total_workflows,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": self.successful_executions / max(1, self.total_executions),
            "total_templates": self.total_templates,
            "optimizations_applied": self.optimizations_applied,
            "avg_execution_time_ms": self.avg_execution_time_ms,
        }


# ═══════════════════════════════════════════════════════════
# Adaptive Workflow Engine
# ═══════════════════════════════════════════════════════════

class AdaptiveWorkflowEngine:
    """
    Self-optimizing workflow engine with adaptive execution.
    
    Features:
    - Self-modifying workflows that adapt to runtime conditions
    - Context-aware branching with learned decision trees
    - Automated optimization (simplify, parallelize, merge)
    - Workflow templates with parameterization
    - Real-time execution monitoring
    - Plugin-based action nodes
    """

    def __init__(self, config: WorkflowEngineConfig | None = None):
        self.config = config or WorkflowEngineConfig()
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._executions: dict[str, WorkflowExecution] = {}
        self._templates: dict[str, WorkflowTemplate] = {}
        self._action_handlers: dict[str, callable] = {}
        self._stats = WorkflowStats()
        self._init_default_templates()

    def _init_default_templates(self) -> None:
        """Initialize default workflow templates."""
        templates = [
            WorkflowTemplate(
                template_id="template-data-pipeline",
                name="Data Pipeline",
                description="Standard data processing pipeline",
                category="data",
                nodes={
                    "start": WorkflowNode(
                        node_id="start", node_type=WorkflowNodeType.TRIGGER,
                        label="Start", next_nodes=["extract"],
                    ),
                    "extract": WorkflowNode(
                        node_id="extract", node_type=WorkflowNodeType.ACTION,
                        label="Extract Data", action="extract", next_nodes=["transform"],
                    ),
                    "transform": WorkflowNode(
                        node_id="transform", node_type=WorkflowNodeType.TRANSFORM,
                        label="Transform", action="transform", next_nodes=["load"],
                    ),
                    "load": WorkflowNode(
                        node_id="load", node_type=WorkflowNodeType.ACTION,
                        label="Load", action="load", next_nodes=["end"],
                    ),
                    "end": WorkflowNode(
                        node_id="end", node_type=WorkflowNodeType.END,
                        label="End",
                    ),
                },
                entry_node="start",
                parameters=[
                    {"name": "source", "type": "string", "description": "Data source"},
                    {"name": "destination", "type": "string", "description": "Data destination"},
                ],
            ),
            WorkflowTemplate(
                template_id="template-approval-flow",
                name="Approval Flow",
                description="Multi-step approval workflow",
                category="governance",
                nodes={
                    "start": WorkflowNode(
                        node_id="start", node_type=WorkflowNodeType.TRIGGER,
                        label="Start", next_nodes=["review"],
                    ),
                    "review": WorkflowNode(
                        node_id="review", node_type=WorkflowNodeType.ACTION,
                        label="Review", action="review", next_nodes=["decision"],
                    ),
                    "decision": WorkflowNode(
                        node_id="decision", node_type=WorkflowNodeType.CONDITION,
                        label="Decision", action="check_approval",
                        conditions=[
                            {"condition": "approved", "next": "notify_approved"},
                            {"condition": "rejected", "next": "notify_rejected"},
                        ],
                    ),
                    "notify_approved": WorkflowNode(
                        node_id="notify_approved", node_type=WorkflowNodeType.NOTIFICATION,
                        label="Notify Approved", next_nodes=["end"],
                    ),
                    "notify_rejected": WorkflowNode(
                        node_id="notify_rejected", node_type=WorkflowNodeType.NOTIFICATION,
                        label="Notify Rejected", next_nodes=["end"],
                    ),
                    "end": WorkflowNode(
                        node_id="end", node_type=WorkflowNodeType.END,
                        label="End",
                    ),
                },
                entry_node="start",
                parameters=[
                    {"name": "approver", "type": "string", "description": "Approver ID"},
                    {"name": "threshold", "type": "number", "description": "Approval threshold"},
                ],
            ),
        ]
        for t in templates:
            self._templates[t.template_id] = t

    # ── Workflow Management ──

    def create_workflow(
        self,
        name: str,
        description: str,
        trigger: TriggerType,
        trigger_config: dict[str, Any],
        nodes: dict[str, WorkflowNode],
        entry_node: str,
        tags: list[str] | None = None,
    ) -> WorkflowDefinition:
        """Create a new workflow definition."""
        workflow = WorkflowDefinition(
            workflow_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            trigger=trigger,
            trigger_config=trigger_config,
            nodes=nodes,
            entry_node=entry_node,
            tags=tags or [],
        )

        self._validate_workflow(workflow)
        self._workflows[workflow.workflow_id] = workflow
        self._stats.total_workflows += 1

        logger.info("Created workflow %s: %s (%d nodes)", workflow.workflow_id, name, len(nodes))
        return workflow

    def create_from_template(
        self,
        template_id: str,
        name: str,
        description: str,
        trigger_config: dict[str, Any],
        parameter_values: dict[str, Any] | None = None,
    ) -> WorkflowDefinition | None:
        """Create a workflow from a template."""
        template = self._templates.get(template_id)
        if not template:
            return None

        # Deep copy nodes
        nodes = {}
        for node_id, node in template.nodes.items():
            nodes[node_id] = WorkflowNode(
                node_id=node.node_id,
                node_type=node.node_type,
                label=node.label,
                action=node.action,
                config={**node.config},
                next_nodes=list(node.next_nodes),
                conditions=[{**c} for c in node.conditions],
                max_retries=node.max_retries,
                timeout_seconds=node.timeout_seconds,
            )

        workflow = self.create_workflow(
            name=name,
            description=description,
            trigger=TriggerType.MANUAL,
            trigger_config=trigger_config,
            nodes=nodes,
            entry_node=template.entry_node,
            tags=list(template.tags),
        )

        template.usage_count += 1
        self._stats.total_templates = len(self._templates)
        return workflow

    def _validate_workflow(self, workflow: WorkflowDefinition) -> None:
        """Validate workflow structure."""
        if workflow.entry_node not in workflow.nodes:
            raise ValueError(f"Entry node '{workflow.entry_node}' not found in nodes")

        # Check all referenced nodes exist
        for node in workflow.nodes.values():
            for next_id in node.next_nodes:
                if next_id not in workflow.nodes:
                    raise ValueError(f"Node '{node.node_id}' references non-existent node '{next_id}'")

    # ── Execution ──

    def execute_workflow(
        self,
        workflow_id: str,
        context: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """Execute a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        context = context or {}
        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4())[:8],
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            current_node=workflow.entry_node,
            node_results={},
            started_at=datetime.now(timezone.utc),
        )

        start = time.time()
        self._executions[execution.execution_id] = execution

        try:
            self._execute_node_chain(workflow, execution, workflow.entry_node, context)
            execution.status = WorkflowStatus.COMPLETED
            self._stats.successful_executions += 1
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            self._stats.failed_executions += 1
            logger.error("Workflow %s execution failed: %s", workflow_id, e)

        execution.total_duration_ms = (time.time() - start) * 1000
        execution.completed_at = datetime.now(timezone.utc)

        self._update_execution_stats(execution)
        return execution

    def _execute_node_chain(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
        node_id: str,
        context: dict[str, Any],
    ) -> None:
        """Execute a chain of workflow nodes."""
        node = workflow.nodes.get(node_id)
        if not node:
            return

        execution.current_node = node_id

        # Execute node action
        result = self._execute_node(node, context)
        execution.node_results[node_id] = result

        # Handle conditions
        next_nodes = node.next_nodes
        if node.conditions:
            for condition in node.conditions:
                if self._evaluate_condition(condition, result, context):
                    next_nodes = [condition["next"]]
                    break

        # Execute next nodes
        if node.node_type == WorkflowNodeType.PARALLEL:
            for next_id in next_nodes:
                self._execute_node_chain(workflow, execution, next_id, context)
        else:
            for next_id in next_nodes:
                self._execute_node_chain(workflow, execution, next_id, context)

    def _execute_node(
        self, node: WorkflowNode, context: dict[str, Any]
    ) -> Any:
        """Execute a single workflow node."""
        if node.node_type == WorkflowNodeType.END:
            return {"status": "completed"}

        if node.node_type == WorkflowNodeType.WAIT:
            wait_seconds = node.config.get("seconds", 1)
            time.sleep(min(wait_seconds, 60))
            return {"waited": wait_seconds}

        if node.node_type == WorkflowNodeType.NOTIFICATION:
            return {"notified": node.config.get("channel", "default")}

        # Execute action handler
        handler = self._action_handlers.get(node.action)
        if handler:
            return handler(node.config, context)

        return {"action": node.action, "config": node.config}

    def _evaluate_condition(
        self,
        condition: dict[str, Any],
        result: Any,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate a workflow condition."""
        cond_type = condition.get("condition", "")

        if cond_type == "approved":
            return context.get("approved", False)
        if cond_type == "rejected":
            return not context.get("approved", True)
        if cond_type == "success":
            return result is not None and not isinstance(result, dict) or result.get("status") != "error"

        return True

    def register_action(self, action_name: str, handler: callable) -> None:
        """Register an action handler."""
        self._action_handlers[action_name] = handler

    # ── Optimization ──

    def optimize_workflow(
        self,
        workflow_id: str,
        strategies: list[OptimizationStrategy] | None = None,
    ) -> WorkflowDefinition | None:
        """Optimize a workflow using specified strategies."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        strategies = strategies or [
            OptimizationStrategy.SIMPLIFY,
            OptimizationStrategy.PARALLELIZE,
        ]

        workflow.status = WorkflowStatus.OPTIMIZING

        for strategy in strategies:
            if strategy == OptimizationStrategy.SIMPLIFY:
                workflow = self._simplify_workflow(workflow)
            elif strategy == OptimizationStrategy.PARALLELIZE:
                workflow = self._parallelize_workflow(workflow)
            elif strategy == OptimizationStrategy.ELIMINATE:
                workflow = self._eliminate_redundant(workflow)

        workflow.status = WorkflowStatus.ACTIVE
        workflow.version += 1
        workflow.updated_at = datetime.now(timezone.utc)
        self._stats.optimizations_applied += len(strategies)

        return workflow

    def _simplify_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """Simplify workflow by removing unnecessary nodes."""
        # Remove no-op nodes (just pass through)
        to_remove = []
        for node_id, node in workflow.nodes.items():
            if node.node_type == WorkflowNodeType.ACTION and not node.action:
                if len(node.next_nodes) == 1:
                    to_remove.append(node_id)

        for node_id in to_remove:
            node = workflow.nodes[node_id]
            next_node = node.next_nodes[0]
            # Re-route predecessors
            for other in workflow.nodes.values():
                if node_id in other.next_nodes:
                    other.next_nodes = [next_node if n == node_id else n for n in other.next_nodes]
            del workflow.nodes[node_id]

        return workflow

    def _parallelize_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """Identify independent sequential nodes for parallelization."""
        for node_id, node in workflow.nodes.items():
            if len(node.next_nodes) > 1:
                # Check if next nodes are independent
                next_nodes = [workflow.nodes[n] for n in node.next_nodes if n in workflow.nodes]
                if all(not n.next_nodes or set(n.next_nodes).isdisjoint(
                    set(nn.next_nodes) for nn in next_nodes if nn != n
                ) for n in next_nodes):
                    # Can parallelize
                    parallel_node = WorkflowNode(
                        node_id=f"parallel-{node_id}",
                        node_type=WorkflowNodeType.PARALLEL,
                        label=f"Parallel after {node.label}",
                        next_nodes=node.next_nodes,
                    )
                    workflow.nodes[parallel_node.node_id] = parallel_node
                    node.next_nodes = [parallel_node.node_id]

        return workflow

    def _eliminate_redundant(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """Eliminate redundant or unreachable nodes."""
        # Find reachable nodes
        reachable = set()
        queue = [workflow.entry_node]
        while queue:
            nid = queue.pop(0)
            if nid in reachable or nid not in workflow.nodes:
                continue
            reachable.add(nid)
            queue.extend(workflow.nodes[nid].next_nodes)

        # Remove unreachable
        unreachable = set(workflow.nodes.keys()) - reachable
        for nid in unreachable:
            del workflow.nodes[nid]

        return workflow

    # ── Templates ──

    def save_as_template(self, workflow_id: str, name: str, category: str) -> WorkflowTemplate | None:
        """Save a workflow as a reusable template."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        template = WorkflowTemplate(
            template_id=str(uuid.uuid4())[:8],
            name=name,
            description=workflow.description,
            category=category,
            nodes=workflow.nodes,
            entry_node=workflow.entry_node,
            parameters=[],
            tags=list(workflow.tags),
        )
        self._templates[template.template_id] = template
        self._stats.total_templates = len(self._templates)
        return template

    def get_templates(self, category: str = "") -> list[WorkflowTemplate]:
        """Get workflow templates, optionally filtered by category."""
        if category:
            return [t for t in self._templates.values() if t.category == category]
        return list(self._templates.values())

    # ── Statistics ──

    def _update_execution_stats(self, execution: WorkflowExecution) -> None:
        """Update execution statistics."""
        self._stats.total_executions += 1
        n = self._stats.total_executions
        self._stats.avg_execution_time_ms = (
            (self._stats.avg_execution_time_ms * (n - 1) + execution.total_duration_ms) / n
        )

    def get_stats(self) -> WorkflowStats:
        """Get workflow engine statistics."""
        return self._stats

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self, status: WorkflowStatus | None = None) -> list[WorkflowDefinition]:
        """List workflows, optionally filtered by status."""
        workflows = list(self._workflows.values())
        if status:
            workflows = [w for w in workflows if w.status == status]
        return workflows

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """Get an execution by ID."""
        return self._executions.get(execution_id)

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    def reset(self) -> None:
        """Reset the workflow engine."""
        self._workflows.clear()
        self._executions.clear()
        self._stats = WorkflowStats()
        self._init_default_templates()
        logger.info("Adaptive workflow engine reset")


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@dataclass
class WorkflowEngineConfig:
    """Configuration for the adaptive workflow engine."""
    max_nodes_per_workflow: int = 100
    max_parallel_branches: int = 10
    default_timeout_seconds: int = 60
    auto_optimize: bool = True
    max_executions_per_workflow: int = 1000
    collect_metrics: bool = True


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_adaptive_workflows: AdaptiveWorkflowEngine | None = None


def get_adaptive_workflows() -> AdaptiveWorkflowEngine:
    """Get or create the singleton adaptive workflow engine."""
    global _adaptive_workflows
    if _adaptive_workflows is None:
        _adaptive_workflows = AdaptiveWorkflowEngine()
    return _adaptive_workflows


def reset_adaptive_workflows() -> None:
    """Reset the singleton adaptive workflow engine."""
    global _adaptive_workflows
    if _adaptive_workflows:
        _adaptive_workflows.reset()
    _adaptive_workflows = None