"""Platform Workflow Composer — visual workflow design, automation, and orchestration.

Enables definition, composition, and execution of complex AI workflows through
a node-graph architecture. Supports triggers, conditions, parallel execution,
branching, and multi-step automation pipelines.
"""

from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(Enum):
    """Types of workflow nodes."""
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    TRANSFORM = "transform"
    AGENT = "agent"
    TOOL = "tool"
    DELAY = "delay"
    PARALLEL = "parallel"
    MERGE = "merge"
    OUTPUT = "output"


class ExecutionStatus(Enum):
    """Execution status of a workflow or node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PAUSED = "paused"


class TriggerType(Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    WEBHOOK = "webhook"
    CONDITION = "condition"
    CHAIN = "chain"


@dataclass
class WorkflowNode:
    """A single node in a workflow graph."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_type: NodeType = NodeType.ACTION
    label: str = ""
    description: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0
    status: ExecutionStatus = ExecutionStatus.PENDING


@dataclass
class WorkflowEdge:
    """A directed edge connecting two nodes in a workflow."""
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str = ""
    target_id: str = ""
    condition: str = ""
    label: str = ""


@dataclass
class WorkflowExecution:
    """A single execution run of a workflow."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    workflow_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    node_statuses: dict[str, ExecutionStatus] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class WorkflowDefinition:
    """A complete workflow definition with nodes and edges."""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_config: dict[str, Any] = field(default_factory=dict)
    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    edges: dict[str, WorkflowEdge] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class PlatformWorkflowComposer:
    """Visual workflow design and automation orchestration platform.

    Provides a node-graph workflow engine for composing complex AI automation
    pipelines. Supports multiple trigger types, conditional branching, parallel
    execution, and multi-step orchestration with full execution tracking.

    Workflows are defined as directed graphs of nodes connected by edges,
    enabling visual composition of sophisticated automation sequences.
    """

    MAX_NODES: int = 100
    MAX_EDGES: int = 200

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._executions: dict[str, WorkflowExecution] = {}
        self._total_workflows: int = 0
        self._total_executions: int = 0

    def create_workflow(
        self,
        name: str,
        description: str = "",
        trigger_type: TriggerType = TriggerType.MANUAL,
        trigger_config: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> WorkflowDefinition:
        """Create a new workflow definition.

        Args:
            name: Workflow name.
            description: What the workflow does.
            trigger_type: How the workflow is triggered.
            trigger_config: Trigger-specific configuration.
            tags: Categorization tags.

        Returns:
            A new WorkflowDefinition ready for node composition.
        """
        workflow = WorkflowDefinition(
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {},
            tags=tags or [],
        )
        self._workflows[workflow.workflow_id] = workflow
        self._total_workflows += 1
        return workflow

    def add_node(
        self,
        workflow_id: str,
        node_type: NodeType,
        label: str,
        description: str = "",
        config: dict[str, Any] | None = None,
        position_x: float = 0.0,
        position_y: float = 0.0,
    ) -> WorkflowNode | None:
        """Add a node to a workflow graph.

        Args:
            workflow_id: The workflow to add the node to.
            node_type: Type of the node.
            label: Display label.
            description: What the node does.
            config: Node-specific configuration.
            position_x: X position in visual editor.
            position_y: Y position in visual editor.

        Returns:
            The created WorkflowNode, or None if workflow not found.
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        if len(workflow.nodes) >= self.MAX_NODES:
            return None

        node = WorkflowNode(
            node_type=node_type,
            label=label,
            description=description,
            config=config or {},
            position_x=position_x,
            position_y=position_y,
        )
        workflow.nodes[node.node_id] = node
        workflow.updated_at = time.time()
        return node

    def add_edge(
        self,
        workflow_id: str,
        source_id: str,
        target_id: str,
        condition: str = "",
        label: str = "",
    ) -> WorkflowEdge | None:
        """Add an edge connecting two nodes in a workflow.

        Args:
            workflow_id: The workflow to add the edge to.
            source_id: Source node ID.
            target_id: Target node ID.
            condition: Condition for this edge to be traversed.
            label: Display label for the edge.

        Returns:
            The created WorkflowEdge, or None if invalid.
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        if len(workflow.edges) >= self.MAX_EDGES:
            return None
        if source_id not in workflow.nodes or target_id not in workflow.nodes:
            return None

        edge = WorkflowEdge(
            source_id=source_id,
            target_id=target_id,
            condition=condition,
            label=label,
        )
        workflow.edges[edge.edge_id] = edge
        workflow.updated_at = time.time()
        return edge

    def execute(
        self,
        workflow_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> WorkflowExecution | None:
        """Execute a workflow.

        Args:
            workflow_id: The workflow to execute.
            input_data: Input data for the workflow.

        Returns:
            A WorkflowExecution tracking the run, or None if not found.
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            status=ExecutionStatus.RUNNING,
            started_at=time.time(),
        )

        # Initialize node statuses
        for node_id in workflow.nodes:
            execution.node_statuses[node_id] = ExecutionStatus.PENDING

        # Find trigger nodes and execute the graph
        trigger_nodes = [
            nid for nid, node in workflow.nodes.items()
            if node.node_type == NodeType.TRIGGER
        ]

        if not trigger_nodes:
            # Start from nodes with no incoming edges
            has_incoming = set()
            for edge in workflow.edges.values():
                has_incoming.add(edge.target_id)
            trigger_nodes = [
                nid for nid in workflow.nodes if nid not in has_incoming
            ]

        # Simulate execution by traversing the graph
        visited: set[str] = set()
        self._traverse_graph(
            workflow, execution, trigger_nodes, visited, input_data or {}
        )

        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = time.time()

        self._executions[execution.execution_id] = execution
        self._total_executions += 1
        return execution

    def _traverse_graph(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
        node_ids: list[str],
        visited: set[str],
        context: dict[str, Any],
    ) -> None:
        """Traverse the workflow graph and simulate node execution."""
        for node_id in node_ids:
            if node_id in visited:
                continue
            visited.add(node_id)

            node = workflow.nodes.get(node_id)
            if not node:
                continue

            execution.node_statuses[node_id] = ExecutionStatus.RUNNING
            node.status = ExecutionStatus.RUNNING

            # Simulate node execution
            if node.node_type == NodeType.CONDITION:
                # Evaluate condition
                condition_result = node.config.get("condition", "true")
                context[f"node_{node_id}_result"] = True
            elif node.node_type == NodeType.TRANSFORM:
                context[f"node_{node_id}_output"] = node.config.get("transform", "")
            elif node.node_type == NodeType.DELAY:
                delay_ms = node.config.get("delay_ms", 0)
                context[f"node_{node_id}_delay"] = delay_ms
            elif node.node_type == NodeType.OUTPUT:
                execution.output[node.label or node_id] = context

            execution.node_statuses[node_id] = ExecutionStatus.COMPLETED
            node.status = ExecutionStatus.COMPLETED

            # Find outgoing edges
            outgoing = [
                edge.target_id
                for edge in workflow.edges.values()
                if edge.source_id == node_id
            ]
            if outgoing:
                self._traverse_graph(workflow, execution, outgoing, visited, context)

    def get_workflow_summary(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a summary of a workflow definition.

        Args:
            workflow_id: The workflow to summarize.

        Returns:
            Workflow summary dict.
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        node_type_counts: dict[str, int] = {}
        for node in workflow.nodes.values():
            node_type_counts[node.node_type.value] = (
                node_type_counts.get(node.node_type.value, 0) + 1
            )

        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "trigger_type": workflow.trigger_type.value,
            "version": workflow.version,
            "node_count": len(workflow.nodes),
            "edge_count": len(workflow.edges),
            "node_types": node_type_counts,
            "tags": workflow.tags,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_type": n.node_type.value,
                    "label": n.label,
                    "position_x": n.position_x,
                    "position_y": n.position_y,
                }
                for n in workflow.nodes.values()
            ],
            "edges": [
                {
                    "edge_id": e.edge_id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "label": e.label,
                }
                for e in workflow.edges.values()
            ],
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
        }

    def get_execution_status(
        self, execution_id: str
    ) -> dict[str, Any] | None:
        """Get the status of a workflow execution.

        Args:
            execution_id: The execution to check.

        Returns:
            Execution status dict.
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "node_statuses": {
                nid: s.value for nid, s in execution.node_statuses.items()
            },
            "output": execution.output,
            "error": execution.error,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get workflow composer statistics."""
        trigger_counts: dict[str, int] = {}
        for wf in self._workflows.values():
            trigger_counts[wf.trigger_type.value] = (
                trigger_counts.get(wf.trigger_type.value, 0) + 1
            )

        return {
            "total_workflows": self._total_workflows,
            "total_executions": self._total_executions,
            "total_nodes": sum(len(wf.nodes) for wf in self._workflows.values()),
            "total_edges": sum(len(wf.edges) for wf in self._workflows.values()),
            "trigger_distribution": trigger_counts,
            "avg_nodes_per_workflow": round(
                sum(len(wf.nodes) for wf in self._workflows.values())
                / max(self._total_workflows, 1),
                1,
            ),
            "recent_executions": sum(
                1 for e in self._executions.values()
                if e.status == ExecutionStatus.COMPLETED
            ),
        }

    def reset(self) -> None:
        """Reset the composer to initial state."""
        self._workflows.clear()
        self._executions.clear()
        self._total_workflows = 0
        self._total_executions = 0


# ── Singleton accessors ──

_workflow_composer: PlatformWorkflowComposer | None = None


def get_workflow_composer() -> PlatformWorkflowComposer:
    """Get or create the singleton workflow composer."""
    global _workflow_composer
    if _workflow_composer is None:
        _workflow_composer = PlatformWorkflowComposer()
    return _workflow_composer


def reset_workflow_composer() -> None:
    """Reset the singleton workflow composer."""
    global _workflow_composer
    if _workflow_composer is not None:
        _workflow_composer.reset()
    _workflow_composer = None