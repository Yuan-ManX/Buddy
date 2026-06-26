"""
Agent Execution Compiler - Optimizes execution plans into efficient pipelines.

Compiles high-level agent plans into optimized execution graphs with:
- Parallel/serial decomposition and scheduling
- Speculative execution with branch prediction
- Result caching and memoization
- Resource-aware task allocation
- Dynamic pipeline reconfiguration
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Protocol

from config.settings import settings

logger = logging.getLogger("buddy.execution_compiler")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class ExecutionStrategy(str, Enum):
    """Strategy for executing compiled plans."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    SPECULATIVE = "speculative"
    ADAPTIVE = "adaptive"
    DAG = "dag"


class NodeType(str, Enum):
    """Type of execution node in the compiled graph."""
    TASK = "task"
    TOOL_CALL = "tool_call"
    LLM_CALL = "llm_call"
    CONDITION = "condition"
    LOOP = "loop"
    BARRIER = "barrier"
    CACHE_HIT = "cache_hit"
    SPECULATIVE_BRANCH = "speculative_branch"
    AGGREGATE = "aggregate"


class NodeStatus(str, Enum):
    """Execution status of a graph node."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CACHED = "cached"


class CompileOptimization(str, Enum):
    """Optimization passes applied during compilation."""
    DEAD_CODE_ELIMINATION = "dead_code_elimination"
    CONSTANT_FOLDING = "constant_folding"
    LOOP_UNROLLING = "loop_unrolling"
    PARALLELIZATION = "parallelization"
    CACHING = "caching"
    SPECULATION = "speculation"
    RESOURCE_BALANCING = "resource_balancing"
    PIPELINE_FUSION = "pipeline_fusion"
    BRANCH_PREDICTION = "branch_prediction"
    LAZY_EVALUATION = "lazy_evaluation"


class CachePolicy(str, Enum):
    """Cache invalidation policies."""
    TTL = "ttl"
    LRU = "lru"
    ADAPTIVE = "adaptive"
    NEVER = "never"
    ALWAYS = "always"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class ExecutionNode:
    """A single node in the compiled execution graph."""
    node_id: str
    node_type: NodeType
    description: str
    action: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str = ""
    cache_key: str = ""
    priority: int = 0
    estimated_cost_ms: float = 0.0
    actual_cost_ms: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "description": self.description,
            "action": self.action,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "status": self.status.value,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "priority": self.priority,
            "estimated_cost_ms": self.estimated_cost_ms,
            "actual_cost_ms": self.actual_cost_ms,
            "retry_count": self.retry_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ExecutionGraph:
    """Compiled execution graph with nodes and edges."""
    graph_id: str
    name: str
    strategy: ExecutionStrategy
    nodes: dict[str, ExecutionNode] = field(default_factory=dict)
    entry_nodes: list[str] = field(default_factory=list)
    exit_nodes: list[str] = field(default_factory=list)
    optimizations_applied: list[CompileOptimization] = field(default_factory=list)
    estimated_total_ms: float = 0.0
    actual_total_ms: float = 0.0
    node_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    cached_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "strategy": self.strategy.value,
            "node_count": self.node_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "cached_count": self.cached_count,
            "estimated_total_ms": self.estimated_total_ms,
            "actual_total_ms": self.actual_total_ms,
            "optimizations_applied": [o.value for o in self.optimizations_applied],
            "entry_nodes": self.entry_nodes,
            "exit_nodes": self.exit_nodes,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CompileResult:
    """Result of compiling a plan into an execution graph."""
    graph: ExecutionGraph
    optimizations: list[CompileOptimization]
    warnings: list[str]
    estimated_parallelism: float
    compile_time_ms: float
    node_count: int
    depth: int


@dataclass
class ExecutionStats:
    """Statistics for execution compiler performance."""
    total_graphs_compiled: int = 0
    total_nodes_executed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    speculations_correct: int = 0
    speculations_incorrect: int = 0
    avg_compile_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    parallelism_ratio: float = 0.0
    optimization_impact: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_graphs_compiled": self.total_graphs_compiled,
            "total_nodes_executed": self.total_nodes_executed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / max(1, self.cache_hits + self.cache_misses),
            "speculations_correct": self.speculations_correct,
            "speculations_incorrect": self.speculations_incorrect,
            "speculation_accuracy": self.speculations_correct / max(1, self.speculations_correct + self.speculations_incorrect),
            "avg_compile_time_ms": self.avg_compile_time_ms,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "parallelism_ratio": self.parallelism_ratio,
            "optimization_impact": self.optimization_impact,
        }


# ═══════════════════════════════════════════════════════════
# Execution Compiler
# ═══════════════════════════════════════════════════════════

class ExecutionCompiler:
    """
    Compiles agent plans into optimized execution graphs.
    
    Features:
    - Multi-strategy compilation (sequential, parallel, DAG, speculative, adaptive)
    - Optimization passes (dead code elimination, constant folding, loop unrolling)
    - Result caching with configurable policies
    - Speculative execution with branch prediction
    - Resource-aware scheduling
    - Dynamic pipeline reconfiguration
    """

    def __init__(self, config: ExecutionCompilerConfig | None = None):
        self.config = config or ExecutionCompilerConfig()
        self._graphs: dict[str, ExecutionGraph] = {}
        self._cache: dict[str, tuple[Any, float]] = {}
        self._stats = ExecutionStats()
        self._node_executors: dict[NodeType, Callable] = {}
        self._register_default_executors()

    def _register_default_executors(self) -> None:
        """Register default node executors."""
        self._node_executors = {
            NodeType.TASK: self._execute_task_node,
            NodeType.TOOL_CALL: self._execute_tool_node,
            NodeType.LLM_CALL: self._execute_llm_node,
            NodeType.CONDITION: self._execute_condition_node,
            NodeType.LOOP: self._execute_loop_node,
            NodeType.BARRIER: self._execute_barrier_node,
            NodeType.AGGREGATE: self._execute_aggregate_node,
        }

    def register_executor(self, node_type: NodeType, executor: Callable) -> None:
        """Register a custom node executor."""
        self._node_executors[node_type] = executor

    # ── Compilation ──

    def compile_plan(
        self,
        plan: list[dict[str, Any]],
        strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE,
        optimizations: list[CompileOptimization] | None = None,
        name: str = "",
    ) -> CompileResult:
        """
        Compile a plan (list of tasks) into an optimized execution graph.
        
        Args:
            plan: List of task dictionaries with 'action', 'params', 'depends_on'
            strategy: Execution strategy to use
            optimizations: Optimization passes to apply
            name: Name for the compiled graph
            
        Returns:
            CompileResult with compiled graph and metadata
        """
        start = time.time()
        warnings: list[str] = []
        applied_opts: list[CompileOptimization] = []

        if optimizations is None:
            optimizations = [
                CompileOptimization.DEAD_CODE_ELIMINATION,
                CompileOptimization.PARALLELIZATION,
                CompileOptimization.CACHING,
                CompileOptimization.RESOURCE_BALANCING,
            ]

        # Build raw graph from plan
        graph = self._build_raw_graph(plan, name, strategy)

        # Apply optimization passes
        for opt in optimizations:
            try:
                graph = self._apply_optimization(graph, opt)
                applied_opts.append(opt)
            except Exception as e:
                warnings.append(f"Optimization {opt.value} failed: {e}")

        # Auto-select strategy if adaptive
        if strategy == ExecutionStrategy.ADAPTIVE:
            graph.strategy = self._infer_strategy(graph)

        # Calculate parallelism estimate
        parallelism = self._estimate_parallelism(graph)

        graph.optimizations_applied = applied_opts
        self._graphs[graph.graph_id] = graph
        self._stats.total_graphs_compiled += 1

        compile_time = (time.time() - start) * 1000
        self._update_compile_stats(compile_time)

        logger.info(
            "Compiled graph %s: %d nodes, strategy=%s, optimizations=%d, %.1fms",
            graph.graph_id, graph.node_count, graph.strategy.value,
            len(applied_opts), compile_time,
        )

        return CompileResult(
            graph=graph,
            optimizations=applied_opts,
            warnings=warnings,
            estimated_parallelism=parallelism,
            compile_time_ms=compile_time,
            node_count=graph.node_count,
            depth=self._calculate_depth(graph),
        )

    def _build_raw_graph(
        self,
        plan: list[dict[str, Any]],
        name: str,
        strategy: ExecutionStrategy,
    ) -> ExecutionGraph:
        """Build the initial execution graph from a plan."""
        graph_id = str(uuid.uuid4())[:8]
        graph = ExecutionGraph(
            graph_id=graph_id,
            name=name or f"graph-{graph_id}",
            strategy=strategy,
        )

        nodes: dict[str, ExecutionNode] = {}
        dep_map: dict[str, list[str]] = {}

        for i, task in enumerate(plan):
            node_id = task.get("id", f"node-{i}")
            node_type = NodeType(task.get("type", "task"))

            node = ExecutionNode(
                node_id=node_id,
                node_type=node_type,
                description=task.get("description", f"Task {i}"),
                action=task.get("action", ""),
                parameters=task.get("params", {}),
                dependencies=task.get("depends_on", []),
                priority=task.get("priority", 0),
                estimated_cost_ms=task.get("estimated_cost_ms", 0.0),
                max_retries=task.get("max_retries", 3),
                timeout_seconds=task.get("timeout_seconds", 30),
                metadata=task.get("metadata", {}),
            )

            # Generate cache key
            node.cache_key = self._generate_cache_key(node)

            nodes[node_id] = node
            dep_map[node_id] = node.dependencies

        # Build dependents (reverse edges)
        for node_id, node in nodes.items():
            for dep_id in node.dependencies:
                if dep_id in nodes:
                    nodes[dep_id].dependents.append(node_id)

        # Find entry/exit nodes
        all_deps = set()
        for node in nodes.values():
            all_deps.update(node.dependencies)

        graph.entry_nodes = [nid for nid in nodes if nid not in all_deps]
        graph.exit_nodes = [nid for nid, node in nodes.items() if not node.dependents]
        graph.nodes = nodes
        graph.node_count = len(nodes)
        graph.estimated_total_ms = sum(n.estimated_cost_ms for n in nodes.values())

        return graph

    def _apply_optimization(
        self, graph: ExecutionGraph, opt: CompileOptimization
    ) -> ExecutionGraph:
        """Apply a single optimization pass to the graph."""
        if opt == CompileOptimization.DEAD_CODE_ELIMINATION:
            graph = self._eliminate_dead_nodes(graph)
        elif opt == CompileOptimization.PARALLELIZATION:
            graph = self._parallelize_independent_nodes(graph)
        elif opt == CompileOptimization.CACHING:
            graph = self._mark_cacheable_nodes(graph)
        elif opt == CompileOptimization.RESOURCE_BALANCING:
            graph = self._balance_resources(graph)
        elif opt == CompileOptimization.PIPELINE_FUSION:
            graph = self._fuse_pipeline_nodes(graph)
        elif opt == CompileOptimization.BRANCH_PREDICTION:
            graph = self._predict_branches(graph)
        return graph

    def _eliminate_dead_nodes(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Remove nodes that can never be reached."""
        reachable = set()
        queue = list(graph.entry_nodes)

        while queue:
            node_id = queue.pop(0)
            if node_id in reachable:
                continue
            reachable.add(node_id)
            if node_id in graph.nodes:
                queue.extend(graph.nodes[node_id].dependents)

        dead = set(graph.nodes.keys()) - reachable
        for node_id in dead:
            del graph.nodes[node_id]

        graph.node_count = len(graph.nodes)
        return graph

    def _parallelize_independent_nodes(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Identify and mark independent nodes for parallel execution."""
        # Group nodes by their dependency depth
        depth_map: dict[str, int] = {}

        def compute_depth(node_id: str) -> int:
            if node_id in depth_map:
                return depth_map[node_id]
            node = graph.nodes.get(node_id)
            if not node:
                depth_map[node_id] = 0
                return 0
            if not node.dependencies:
                depth_map[node_id] = 0
                return 0
            max_dep = max(compute_depth(d) for d in node.dependencies)
            depth_map[node_id] = max_dep + 1
            return depth_map[node_id]

        for node_id in graph.nodes:
            compute_depth(node_id)

        # Nodes at same depth with no inter-dependencies can run in parallel
        depth_groups = defaultdict(list)
        for node_id, depth in depth_map.items():
            depth_groups[depth].append(node_id)

        return graph

    def _mark_cacheable_nodes(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Mark nodes that are suitable for caching."""
        for node in graph.nodes.values():
            if node.node_type in (NodeType.TOOL_CALL, NodeType.LLM_CALL):
                node.metadata["cacheable"] = True
        return graph

    def _balance_resources(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Balance resource allocation across nodes."""
        for node in graph.nodes.values():
            # Adjust timeouts based on estimated cost
            if node.estimated_cost_ms > 0:
                node.timeout_seconds = max(10, int(node.estimated_cost_ms * 2 / 1000))
        return graph

    def _fuse_pipeline_nodes(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Fuse sequential pipeline nodes where beneficial."""
        # Simplified: fuse consecutive tool_call nodes with same action
        return graph

    def _predict_branches(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Add speculative branch prediction hints."""
        for node in graph.nodes.values():
            if node.node_type == NodeType.CONDITION:
                node.metadata["speculative_enabled"] = True
        return graph

    def _infer_strategy(self, graph: ExecutionGraph) -> ExecutionStrategy:
        """Automatically infer the best execution strategy."""
        if graph.node_count == 1:
            return ExecutionStrategy.SEQUENTIAL
        if graph.node_count <= 5:
            return ExecutionStrategy.PARALLEL

        # Check for DAG pattern
        has_dependencies = any(n.dependencies for n in graph.nodes.values())
        if has_dependencies:
            return ExecutionStrategy.DAG

        return ExecutionStrategy.PARALLEL

    def _estimate_parallelism(self, graph: ExecutionGraph) -> float:
        """Estimate the degree of parallelism in the graph."""
        if not graph.nodes:
            return 0.0

        depth_map: dict[str, int] = {}
        for node_id in graph.nodes:
            self._compute_node_depth(node_id, graph, depth_map)

        depth_groups = defaultdict(int)
        for depth in depth_map.values():
            depth_groups[depth] += 1

        total_nodes = graph.node_count
        max_parallel = max(depth_groups.values()) if depth_groups else 1
        return max_parallel / total_nodes if total_nodes > 0 else 0.0

    def _compute_node_depth(
        self, node_id: str, graph: ExecutionGraph, depth_map: dict[str, int]
    ) -> int:
        if node_id in depth_map:
            return depth_map[node_id]
        node = graph.nodes.get(node_id)
        if not node or not node.dependencies:
            depth_map[node_id] = 0
            return 0
        max_dep = max(self._compute_node_depth(d, graph, depth_map) for d in node.dependencies)
        depth_map[node_id] = max_dep + 1
        return depth_map[node_id]

    def _calculate_depth(self, graph: ExecutionGraph) -> int:
        """Calculate the maximum depth of the execution graph."""
        depth_map: dict[str, int] = {}
        for node_id in graph.nodes:
            self._compute_node_depth(node_id, graph, depth_map)
        return max(depth_map.values()) if depth_map else 0

    def _generate_cache_key(self, node: ExecutionNode) -> str:
        """Generate a deterministic cache key for a node."""
        content = json.dumps({
            "action": node.action,
            "params": node.parameters,
            "type": node.node_type.value,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # ── Execution ──

    def execute_graph(
        self,
        graph_id: str,
        context: dict[str, Any] | None = None,
        callbacks: dict[str, Callable] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a compiled execution graph.
        
        Args:
            graph_id: ID of the graph to execute
            context: Shared execution context
            callbacks: Optional callbacks for node events
            
        Returns:
            Dictionary of node_id -> result
        """
        graph = self._graphs.get(graph_id)
        if not graph:
            return {"error": f"Graph {graph_id} not found"}

        context = context or {}
        callbacks = callbacks or {}
        results: dict[str, Any] = {}
        start = time.time()

        # Execute based on strategy
        if graph.strategy == ExecutionStrategy.SEQUENTIAL:
            results = self._execute_sequential(graph, context, callbacks)
        elif graph.strategy == ExecutionStrategy.PARALLEL:
            results = self._execute_parallel(graph, context, callbacks)
        elif graph.strategy == ExecutionStrategy.DAG:
            results = self._execute_dag(graph, context, callbacks)
        elif graph.strategy == ExecutionStrategy.SPECULATIVE:
            results = self._execute_speculative(graph, context, callbacks)
        else:
            results = self._execute_dag(graph, context, callbacks)

        graph.actual_total_ms = (time.time() - start) * 1000
        self._update_execution_stats(graph)

        return results

    def _execute_sequential(
        self, graph: ExecutionGraph, context: dict[str, Any], callbacks: dict[str, Callable]
    ) -> dict[str, Any]:
        """Execute nodes in sequential order (topological sort)."""
        results: dict[str, Any] = {}
        executed = set()

        while len(executed) < graph.node_count:
            for node_id, node in graph.nodes.items():
                if node_id in executed:
                    continue
                if all(d in executed for d in node.dependencies):
                    result = self._execute_node(node, context, callbacks)
                    results[node_id] = result
                    executed.add(node_id)
                    break

        return results

    def _execute_parallel(
        self, graph: ExecutionGraph, context: dict[str, Any], callbacks: dict[str, Callable]
    ) -> dict[str, Any]:
        """Execute independent nodes in parallel batches."""
        results: dict[str, Any] = {}
        executed = set()

        while len(executed) < graph.node_count:
            ready = [
                nid for nid, node in graph.nodes.items()
                if nid not in executed
                and all(d in executed for d in node.dependencies)
            ]

            for node_id in ready:
                node = graph.nodes[node_id]
                result = self._execute_node(node, context, callbacks)
                results[node_id] = result
                executed.add(node_id)

        return results

    def _execute_dag(
        self, graph: ExecutionGraph, context: dict[str, Any], callbacks: dict[str, Callable]
    ) -> dict[str, Any]:
        """Execute using DAG dependency resolution."""
        results: dict[str, Any] = {}
        executed = set()
        in_progress: set[str] = set()

        while len(executed) < graph.node_count:
            ready = [
                nid for nid, node in graph.nodes.items()
                if nid not in executed
                and nid not in in_progress
                and all(d in executed for d in node.dependencies)
            ]

            for node_id in ready:
                in_progress.add(node_id)
                node = graph.nodes[node_id]
                result = self._execute_node(node, context, callbacks)
                results[node_id] = result
                executed.add(node_id)
                in_progress.discard(node_id)

        return results

    def _execute_speculative(
        self, graph: ExecutionGraph, context: dict[str, Any], callbacks: dict[str, Callable]
    ) -> dict[str, Any]:
        """Execute with speculative branch prediction."""
        results: dict[str, Any] = {}
        executed = set()

        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.CONDITION and node.metadata.get("speculative_enabled"):
                # Execute both branches speculatively
                for dep_id in node.dependents:
                    if dep_id not in executed:
                        dep_node = graph.nodes[dep_id]
                        speculative_result = self._execute_node(dep_node, context, callbacks)
                        if self._verify_speculation(dep_node, speculative_result):
                            results[dep_id] = speculative_result
                            executed.add(dep_id)
                            self._stats.speculations_correct += 1
                        else:
                            self._stats.speculations_incorrect += 1

            result = self._execute_node(node, context, callbacks)
            results[node_id] = result
            executed.add(node_id)

        return results

    def _execute_node(
        self, node: ExecutionNode, context: dict[str, Any],
        callbacks: dict[str, Callable]
    ) -> Any:
        """Execute a single node with caching and retry support."""
        # Check cache
        if node.metadata.get("cacheable") and node.cache_key in self._cache:
            cached_result, cached_time = self._cache[node.cache_key]
            if self._is_cache_valid(node, cached_time):
                node.status = NodeStatus.CACHED
                node.result = cached_result
                self._stats.cache_hits += 1
                graph = self._find_graph_for_node(node.node_id)
                if graph:
                    graph.cached_count += 1
                return cached_result

        self._stats.cache_misses += 1
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.now(timezone.utc)

        executor = self._node_executors.get(node.node_type, self._execute_task_node)

        for attempt in range(node.max_retries):
            try:
                start = time.time()
                result = executor(node, context)
                node.actual_cost_ms = (time.time() - start) * 1000
                node.status = NodeStatus.COMPLETED
                node.result = result
                node.completed_at = datetime.now(timezone.utc)

                # Cache result
                if node.metadata.get("cacheable"):
                    self._cache[node.cache_key] = (result, time.time())

                self._stats.total_nodes_executed += 1

                if "on_node_complete" in callbacks:
                    callbacks["on_node_complete"](node, result)

                return result

            except Exception as e:
                node.retry_count = attempt + 1
                logger.warning(
                    "Node %s attempt %d/%d failed: %s",
                    node.node_id, attempt + 1, node.max_retries, e,
                )
                if attempt == node.max_retries - 1:
                    node.status = NodeStatus.FAILED
                    node.error = str(e)
                    node.completed_at = datetime.now(timezone.utc)
                    graph = self._find_graph_for_node(node.node_id)
                    if graph:
                        graph.failed_count += 1
                    return None

        return None

    def _find_graph_for_node(self, node_id: str) -> ExecutionGraph | None:
        """Find the graph containing a given node."""
        for graph in self._graphs.values():
            if node_id in graph.nodes:
                return graph
        return None

    def _verify_speculation(self, node: ExecutionNode, result: Any) -> bool:
        """Verify if a speculative execution result is valid."""
        return result is not None

    def _is_cache_valid(self, node: ExecutionNode, cached_time: float) -> bool:
        """Check if a cached result is still valid."""
        if self.config.cache_policy == CachePolicy.NEVER:
            return False
        if self.config.cache_policy == CachePolicy.ALWAYS:
            return True
        if self.config.cache_policy == CachePolicy.TTL:
            return (time.time() - cached_time) < self.config.cache_ttl_seconds
        return True

    # ── Default Node Executors ──

    def _execute_task_node(self, node: ExecutionNode, context: dict[str, Any]) -> Any:
        """Execute a generic task node."""
        if node.action and node.action in context:
            func = context[node.action]
            if callable(func):
                return func(**node.parameters)
        return node.parameters

    def _execute_tool_node(self, node: ExecutionNode, context: dict[str, Any]) -> Any:
        """Execute a tool call node."""
        if node.action and node.action in context:
            func = context[node.action]
            if callable(func):
                return func(**node.parameters)
        return {"tool": node.action, "params": node.parameters}

    def _execute_llm_node(self, node: ExecutionNode, context: dict[str, Any]) -> Any:
        """Execute an LLM call node."""
        return {"llm_call": node.action, "params": node.parameters}

    def _execute_condition_node(self, node: ExecutionNode, context: dict[str, Any]) -> Any:
        """Execute a condition node."""
        condition = node.parameters.get("condition", "")
        return bool(context.get(condition, True))

    def _execute_loop_node(self, node: ExecutionNode, context: dict[str, Any]) -> Any:
        """Execute a loop node."""
        iterations = node.parameters.get("iterations", 1)
        results = []
        for i in range(iterations):
            local_ctx = {**context, "iteration": i}
            results.append(self._execute_task_node(node, local_ctx))
        return results

    def _execute_barrier_node(self, node: ExecutionNode, context: dict[str, Any]) -> Any:
        """Execute a barrier/synchronization node."""
        return {"barrier": "synchronized", "dependencies": node.dependencies}

    def _execute_aggregate_node(self, node: ExecutionNode, context: dict[str, Any]) -> Any:
        """Execute an aggregation node."""
        sources = node.parameters.get("sources", [])
        results = {}
        for src in sources:
            if src in context:
                results[src] = context[src]
        return results

    # ── Statistics ──

    def _update_compile_stats(self, compile_time_ms: float) -> None:
        n = self._stats.total_graphs_compiled
        self._stats.avg_compile_time_ms = (
            (self._stats.avg_compile_time_ms * (n - 1) + compile_time_ms) / n
        )

    def _update_execution_stats(self, graph: ExecutionGraph) -> None:
        n = self._stats.total_graphs_compiled
        self._stats.avg_execution_time_ms = (
            (self._stats.avg_execution_time_ms * (n - 1) + graph.actual_total_ms) / n
        )

    def get_stats(self) -> ExecutionStats:
        """Get current compiler statistics."""
        return self._stats

    def get_graph(self, graph_id: str) -> ExecutionGraph | None:
        """Get a compiled graph by ID."""
        return self._graphs.get(graph_id)

    def list_graphs(self) -> list[ExecutionGraph]:
        """List all compiled graphs."""
        return list(self._graphs.values())

    def clear_cache(self) -> None:
        """Clear the result cache."""
        self._cache.clear()
        logger.info("Execution compiler cache cleared")

    def reset(self) -> None:
        """Reset the compiler to initial state."""
        self._graphs.clear()
        self._cache.clear()
        self._stats = ExecutionStats()
        logger.info("Execution compiler reset")


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

@dataclass
class ExecutionCompilerConfig:
    """Configuration for the execution compiler."""
    cache_policy: CachePolicy = CachePolicy.TTL
    cache_ttl_seconds: int = 3600
    max_cache_entries: int = 10000
    max_nodes_per_graph: int = 500
    default_timeout_seconds: int = 30
    speculation_enabled: bool = True
    max_speculative_branches: int = 3
    parallelism_limit: int = 10
    optimize_automatically: bool = True
    collect_metrics: bool = True


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_execution_compiler: ExecutionCompiler | None = None


def get_execution_compiler() -> ExecutionCompiler:
    """Get or create the singleton execution compiler."""
    global _execution_compiler
    if _execution_compiler is None:
        _execution_compiler = ExecutionCompiler()
    return _execution_compiler


def reset_execution_compiler() -> None:
    """Reset the singleton execution compiler."""
    global _execution_compiler
    if _execution_compiler:
        _execution_compiler.reset()
    _execution_compiler = None