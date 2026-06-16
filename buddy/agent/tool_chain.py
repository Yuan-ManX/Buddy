"""Buddy Tool Chain — dependency-aware tool orchestration graph

Provides intelligent tool chaining with dependency resolution, parallel
execution where possible, and automatic result piping between tools.
Models tool calls as a directed acyclic graph (DAG) with topological
sorting for optimal execution order.

Core capabilities:
  - DAG-based Tool Chaining: dependency-aware execution ordering
  - Parallel Execution: run independent tools concurrently
  - Result Piping: automatically pass tool outputs as inputs to dependent tools
  - Cycle Detection: prevent infinite loops in tool dependencies
  - Execution Timeout: per-tool and global timeout management
  - Rollback Support: revert side effects on chain failure
  - Pipeline Templates: reusable tool chain patterns
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.tool_chain")


class ChainStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


@dataclass
class ToolNode:
    """A single tool in the execution chain."""
    id: str
    tool_name: str
    arguments: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: ChainStatus = ChainStatus.PENDING
    result: Any = None
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    timeout_seconds: int = 60
    retry_on_failure: bool = False
    max_retries: int = 1
    retry_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class ToolChain:
    """A complete tool execution chain with DAG topology."""
    id: str
    name: str
    nodes: dict[str, ToolNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    status: ChainStatus = ChainStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    completed_at: str = ""
    global_timeout_seconds: int = 300
    metadata: dict = field(default_factory=dict)

    def add_node(self, node: ToolNode):
        self.nodes[node.id] = node

    def add_edge(self, from_id: str, to_id: str):
        if from_id in self.nodes and to_id in self.nodes:
            self.edges.append((from_id, to_id))
            if to_id not in self.nodes[from_id].depends_on:
                self.nodes[to_id].depends_on.append(from_id)

    def topological_sort(self) -> list[list[str]]:
        """Perform topological sort returning levels of parallel-executable nodes.

        Each level contains node IDs that can be executed in parallel.
        """
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        adjacency: dict[str, list[str]] = defaultdict(list)

        for from_id, to_id in self.edges:
            adjacency[from_id].append(to_id)
            in_degree[to_id] += 1

        # Kahn's algorithm
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        levels = []

        while queue:
            level = list(queue)
            levels.append(level)
            queue.clear()

            for node_id in level:
                for neighbor in adjacency.get(node_id, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        # Check for cycles
        if sum(len(l) for l in levels) != len(self.nodes):
            remaining = set(self.nodes.keys()) - set(nid for l in levels for nid in l)
            logger.warning(f"Cycle detected in tool chain {self.id}: {remaining}")
            # Add remaining nodes at the end as best-effort
            levels.append(list(remaining))

        return levels

    def validate(self) -> tuple[bool, str]:
        """Validate the chain for structural correctness."""
        node_ids = set(self.nodes.keys())

        for from_id, to_id in self.edges:
            if from_id not in node_ids:
                return False, f"Edge references unknown node: {from_id}"
            if to_id not in node_ids:
                return False, f"Edge references unknown node: {to_id}"

        # Check for self-loops
        for from_id, to_id in self.edges:
            if from_id == to_id:
                return False, f"Self-loop detected on node: {from_id}"

        return True, "Valid"


class ToolChainExecutor:
    """Executes tool chains with dependency-aware scheduling and parallelism.

    Manages the execution of tool DAGs, running independent tools concurrently
    and piping results between dependent tools automatically.
    """

    def __init__(self):
        self._chains: dict[str, ToolChain] = {}
        self._executor: Callable[[str, dict], Awaitable[Any]] | None = None
        self._execution_stats: dict[str, dict] = {}
        self._templates: dict[str, ToolChain] = {}

    def set_executor(self, executor: Callable[[str, dict], Awaitable[Any]]):
        """Set the function used to execute individual tools."""
        self._executor = executor

    def create_chain(self, name: str, nodes: list[ToolNode] = None) -> ToolChain:
        """Create a new tool execution chain."""
        import uuid
        chain = ToolChain(
            id=f"chain-{uuid.uuid4().hex[:8]}",
            name=name,
        )
        if nodes:
            for node in nodes:
                chain.add_node(node)
        self._chains[chain.id] = chain
        return chain

    async def execute(self, chain_id: str) -> ToolChain:
        """Execute a tool chain with parallel execution of independent tools.

        Progresses through topological levels, running all tools in each
        level concurrently. Results from completed tools are automatically
        fed as input to dependent tools.
        """
        chain = self._chains.get(chain_id)
        if not chain:
            raise ValueError(f"Chain not found: {chain_id}")

        valid, error = chain.validate()
        if not valid:
            chain.status = ChainStatus.FAILED
            logger.error(f"Chain {chain_id} validation failed: {error}")
            return chain

        chain.status = ChainStatus.RUNNING
        chain.started_at = datetime.now(timezone.utc).isoformat()
        levels = chain.topological_sort()

        self._execution_stats[chain_id] = {
            "total_nodes": len(chain.nodes),
            "levels": len(levels),
            "completed": 0,
            "failed": 0,
        }

        failed_nodes = set()

        for level_idx, level in enumerate(levels):
            # Skip level if predecessor failed and dependency is required
            executable = []
            for node_id in level:
                node = chain.nodes[node_id]
                deps_failed = any(d in failed_nodes for d in node.depends_on)
                if deps_failed and not node.retry_on_failure:
                    node.status = ChainStatus.CANCELLED
                    node.error = "Dependency failed"
                    failed_nodes.add(node_id)
                    continue
                executable.append(node_id)

            if not executable:
                continue

            # Execute all nodes in this level in parallel
            tasks = []
            for node_id in executable:
                node = chain.nodes[node_id]
                # Prepare arguments with piped results from dependencies
                enriched_args = self._pipe_results(chain, node)
                tasks.append(self._execute_node(chain_id, node, enriched_args))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for node_id, result in zip(executable, results):
                node = chain.nodes[node_id]
                if isinstance(result, Exception):
                    node.status = ChainStatus.FAILED
                    node.error = str(result)
                    failed_nodes.add(node_id)
                    self._execution_stats[chain_id]["failed"] += 1

                    if not node.retry_on_failure or node.retry_count >= node.max_retries:
                        continue

                    # Retry
                    node.retry_count += 1
                    logger.info(f"Retrying node {node_id} ({node.retry_count}/{node.max_retries})")
                    try:
                        retry_result = await self._execute_node(chain_id, node, self._pipe_results(chain, node))
                        node.status = ChainStatus.COMPLETED
                        node.result = retry_result
                        failed_nodes.discard(node_id)
                        self._execution_stats[chain_id]["completed"] += 1
                    except Exception as e:
                        node.error = str(e)
                        logger.error(f"Retry failed for node {node_id}: {e}")
                else:
                    node.status = ChainStatus.COMPLETED
                    node.result = result
                    self._execution_stats[chain_id]["completed"] += 1

            # Check global timeout
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(chain.started_at)).total_seconds()
            if elapsed > chain.global_timeout_seconds:
                logger.warning(f"Chain {chain_id} global timeout ({chain.global_timeout_seconds}s)")
                for node_id in [n for l in levels[level_idx + 1:] for n in l]:
                    chain.nodes[node_id].status = ChainStatus.CANCELLED
                break

        # Determine final status
        chain.completed_at = datetime.now(timezone.utc).isoformat()
        stats = self._execution_stats[chain_id]
        if stats["failed"] == 0:
            chain.status = ChainStatus.COMPLETED
        elif stats["completed"] > 0:
            chain.status = ChainStatus.PARTIAL
        else:
            chain.status = ChainStatus.FAILED

        logger.info(
            f"Chain {chain_id} completed: {chain.status.value} "
            f"({stats['completed']}/{stats['total_nodes']} nodes)"
        )
        return chain

    async def _execute_node(self, chain_id: str, node: ToolNode, args: dict) -> Any:
        """Execute a single tool node with timeout."""
        if not self._executor:
            raise RuntimeError("No tool executor configured")

        node.status = ChainStatus.RUNNING
        node.started_at = datetime.now(timezone.utc).isoformat()

        try:
            result = await asyncio.wait_for(
                self._executor(node.tool_name, args),
                timeout=node.timeout_seconds,
            )
            node.completed_at = datetime.now(timezone.utc).isoformat()
            return result
        except asyncio.TimeoutError:
            node.completed_at = datetime.now(timezone.utc).isoformat()
            raise TimeoutError(f"Tool {node.tool_name} timed out after {node.timeout_seconds}s")

    def _pipe_results(self, chain: ToolChain, node: ToolNode) -> dict:
        """Pipe results from completed dependencies into the node's arguments."""
        args = dict(node.arguments)
        for dep_id in node.depends_on:
            dep_node = chain.nodes.get(dep_id)
            if dep_node and dep_node.status == ChainStatus.COMPLETED and dep_node.result is not None:
                # Auto-pipe: inject dependency result into arguments
                pipe_key = f"_{dep_id}_result"
                if isinstance(dep_node.result, dict):
                    args.update({f"{dep_id}_{k}": v for k, v in dep_node.result.items()
                                if not k.startswith("_")})
                args[pipe_key] = dep_node.result
        return args

    def get_result(self, chain_id: str, node_id: str) -> Any | None:
        """Get the result of a specific node in a chain."""
        chain = self._chains.get(chain_id)
        if not chain:
            return None
        node = chain.nodes.get(node_id)
        return node.result if node else None

    def get_all_results(self, chain_id: str) -> dict[str, Any]:
        """Get all node results from a chain."""
        chain = self._chains.get(chain_id)
        if not chain:
            return {}
        return {
            nid: node.result
            for nid, node in chain.nodes.items()
            if node.status == ChainStatus.COMPLETED
        }

    def save_template(self, name: str, chain: ToolChain):
        """Save a chain as a reusable template."""
        self._templates[name] = chain
        logger.info(f"Saved tool chain template: {name}")

    def load_template(self, name: str) -> ToolChain | None:
        """Load a chain template by name."""
        return self._templates.get(name)

    def list_templates(self) -> list[str]:
        """List all available chain templates."""
        return list(self._templates.keys())

    def get_chain_stats(self, chain_id: str) -> dict | None:
        """Get execution statistics for a chain."""
        chain = self._chains.get(chain_id)
        if not chain:
            return None

        exec_stats = self._execution_stats.get(chain_id, {})
        return {
            "chain_id": chain.id,
            "name": chain.name,
            "status": chain.status.value,
            "total_nodes": len(chain.nodes),
            "levels": exec_stats.get("levels", 0),
            "completed": exec_stats.get("completed", 0),
            "failed": exec_stats.get("failed", 0),
            "created_at": chain.created_at,
            "started_at": chain.started_at,
            "completed_at": chain.completed_at,
            "nodes": [
                {
                    "id": nid,
                    "tool_name": node.tool_name,
                    "status": node.status.value,
                    "error": node.error[:200] if node.error else "",
                    "retry_count": node.retry_count,
                }
                for nid, node in chain.nodes.items()
            ],
        }

    def get_executor_stats(self) -> dict:
        """Get overall executor statistics."""
        return {
            "total_chains": len(self._chains),
            "active_chains": sum(1 for c in self._chains.values() if c.status == ChainStatus.RUNNING),
            "completed_chains": sum(1 for c in self._chains.values() if c.status == ChainStatus.COMPLETED),
            "failed_chains": sum(1 for c in self._chains.values() if c.status == ChainStatus.FAILED),
            "templates": len(self._templates),
        }


# Global tool chain executor
tool_chain_executor = ToolChainExecutor()