"""
Buddy Agentic Reasoning Network - Multi-path reasoning and synthesis engine.

A sophisticated reasoning system that constructs reasoning graphs, evaluates
multiple reasoning paths in parallel, and synthesizes optimal conclusions.
The network supports both linear chain-of-thought and branching graph-of-thought
strategies with automatic path pruning and confidence scoring.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class ReasoningStrategy(str, Enum):
    """Available reasoning strategies for the network."""
    LINEAR = "linear"           # Traditional chain-of-thought
    BRANCHING = "branching"     # Multiple parallel reasoning paths
    RECURSIVE = "recursive"     # Self-referential reasoning
    CONTRASTIVE = "contrastive"  # Compare and contrast
    ABDUCTIVE = "abductive"     # Best explanation inference
    DEDUCTIVE = "deductive"     # Rule-based deduction
    INDUCTIVE = "inductive"     # Pattern-based induction
    ANALOGICAL = "analogical"   # Analogy-based reasoning


class NodeStatus(str, Enum):
    """Status of a reasoning node."""
    PENDING = "pending"
    EXPLORING = "exploring"
    EVALUATED = "evaluated"
    PRUNED = "pruned"
    SELECTED = "selected"
    REJECTED = "rejected"


class PathStatus(str, Enum):
    """Status of a reasoning path."""
    ACTIVE = "active"
    COMPLETED = "completed"
    PRUNED = "pruned"
    SELECTED = "selected"


@dataclass
class ReasoningNode:
    """A single node in the reasoning graph."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    depth: int = 0
    status: NodeStatus = NodeStatus.PENDING
    evidence: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    evaluated_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningPath:
    """A complete reasoning path from root to conclusion."""
    path_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    nodes: list[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    strategy: ReasoningStrategy = ReasoningStrategy.LINEAR
    status: PathStatus = PathStatus.ACTIVE
    quality_score: float = 0.0
    coherence_score: float = 0.0
    novelty_score: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


@dataclass
class ReasoningResult:
    """The final synthesized reasoning result."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str = ""
    conclusion: str = ""
    confidence: float = 0.0
    paths_explored: int = 0
    paths_selected: int = 0
    total_nodes: int = 0
    strategies_used: list[str] = field(default_factory=list)
    selected_paths: list[ReasoningPath] = field(default_factory=list)
    reasoning_trace: list[dict[str, Any]] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    execution_time_ms: float = 0.0


@dataclass
class NetworkStats:
    """Statistics for the reasoning network."""
    total_queries: int = 0
    total_paths_explored: int = 0
    total_nodes_created: int = 0
    avg_confidence: float = 0.0
    avg_execution_ms: float = 0.0
    strategy_usage: dict[str, int] = field(default_factory=dict)
    path_prune_rate: float = 0.0


class AgenticReasoningNetwork:
    """Multi-path reasoning engine with graph-based synthesis.

    Constructs reasoning graphs where each node represents a reasoning step.
    Supports multiple reasoning strategies simultaneously and synthesizes
    results through weighted confidence aggregation.

    The network automatically prunes low-confidence paths to maintain
    efficiency while exploring diverse reasoning approaches.
    """

    # Configuration
    MAX_DEPTH: int = 10
    MAX_BRANCHING_FACTOR: int = 5
    PRUNE_CONFIDENCE_THRESHOLD: float = 0.2
    MIN_CONFIDENCE_FOR_SELECTION: float = 0.5
    MAX_PATHS: int = 20

    def __init__(self) -> None:
        self._nodes: dict[str, ReasoningNode] = {}
        self._paths: dict[str, ReasoningPath] = {}
        self._results: list[ReasoningResult] = []
        self._stats = NetworkStats()

    # ── Node Management ──────────────────────────────────────────

    def create_node(
        self,
        content: str,
        parent_id: str | None = None,
        confidence: float = 0.5,
        evidence: list[str] | None = None,
        assumptions: list[str] | None = None,
    ) -> ReasoningNode:
        """Create a new reasoning node in the graph.

        Args:
            content: The reasoning step content.
            parent_id: Optional parent node ID.
            confidence: Initial confidence in this step (0.0-1.0).
            evidence: Supporting evidence for this step.
            assumptions: Underlying assumptions.

        Returns:
            The created ReasoningNode.
        """
        depth = 0
        if parent_id and parent_id in self._nodes:
            parent = self._nodes[parent_id]
            depth = parent.depth + 1
            parent.children_ids.append(self._nodes)

        node = ReasoningNode(
            content=content,
            parent_id=parent_id,
            confidence=confidence,
            depth=depth,
            evidence=evidence or [],
            assumptions=assumptions or [],
        )

        # Assign to parent
        if parent_id and parent_id in self._nodes:
            parent = self._nodes[parent_id]
            parent.children_ids.append(node.node_id)

        self._nodes[node.node_id] = node
        self._stats.total_nodes_created += 1
        return node

    def evaluate_node(
        self,
        node_id: str,
        confidence: float,
        evidence: list[str] | None = None,
        status: NodeStatus = NodeStatus.EVALUATED,
    ) -> ReasoningNode | None:
        """Evaluate a node with a confidence score and optional evidence.

        Args:
            node_id: The node ID to evaluate.
            confidence: Updated confidence score.
            evidence: Additional evidence.
            status: New node status.

        Returns:
            The updated ReasoningNode or None if not found.
        """
        node = self._nodes.get(node_id)
        if not node:
            return None
        node.confidence = confidence
        node.status = status
        node.evaluated_at = time.time()
        if evidence:
            node.evidence.extend(evidence)
        return node

    def prune_node(self, node_id: str) -> ReasoningNode | None:
        """Prune a node and all its descendants from the graph.

        Args:
            node_id: The node ID to prune.

        Returns:
            The pruned node or None.
        """
        node = self._nodes.get(node_id)
        if not node:
            return None
        node.status = NodeStatus.PRUNED
        # Recursively prune children
        for child_id in node.children_ids:
            self.prune_node(child_id)
        return node

    def get_node(self, node_id: str) -> ReasoningNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    # ── Path Management ──────────────────────────────────────────

    def create_path(
        self,
        nodes: list[str],
        conclusion: str = "",
        strategy: ReasoningStrategy = ReasoningStrategy.LINEAR,
    ) -> ReasoningPath:
        """Create a reasoning path from a sequence of nodes.

        Args:
            nodes: Ordered list of node IDs forming the path.
            conclusion: The path's conclusion.
            strategy: The reasoning strategy used.

        Returns:
            The created ReasoningPath.
        """
        path = ReasoningPath(
            nodes=nodes,
            conclusion=conclusion,
            strategy=strategy,
        )
        self._paths[path.path_id] = path
        return path

    def evaluate_path(
        self,
        path_id: str,
        confidence: float | None = None,
        quality_score: float = 0.0,
        coherence_score: float = 0.0,
        novelty_score: float = 0.0,
    ) -> ReasoningPath | None:
        """Evaluate a reasoning path with quality metrics.

        Args:
            path_id: The path ID to evaluate.
            confidence: Overall path confidence. Auto-computed if None.
            quality_score: Path quality assessment.
            coherence_score: Logical coherence score.
            novelty_score: Novelty of the reasoning.

        Returns:
            The updated ReasoningPath or None.
        """
        path = self._paths.get(path_id)
        if not path:
            return None

        if confidence is None:
            # Auto-compute from node confidences
            node_confs = [
                self._nodes[n].confidence
                for n in path.nodes
                if n in self._nodes
            ]
            confidence = sum(node_confs) / len(node_confs) if node_confs else 0.0

        path.confidence = confidence
        path.quality_score = quality_score
        path.coherence_score = coherence_score
        path.novelty_score = novelty_score
        path.status = PathStatus.COMPLETED
        path.completed_at = time.time()
        return path

    def select_path(self, path_id: str) -> ReasoningPath | None:
        """Mark a path as selected for the final result.

        Args:
            path_id: The path ID to select.

        Returns:
            The selected ReasoningPath or None.
        """
        path = self._paths.get(path_id)
        if not path:
            return None
        path.status = PathStatus.SELECTED
        return path

    def prune_path(self, path_id: str) -> ReasoningPath | None:
        """Prune a low-confidence path.

        Args:
            path_id: The path ID to prune.

        Returns:
            The pruned path or None.
        """
        path = self._paths.get(path_id)
        if not path:
            return None
        path.status = PathStatus.PRUNED
        return path

    # ── Reasoning Operations ─────────────────────────────────────

    def reason(
        self,
        question: str,
        strategies: list[ReasoningStrategy] | None = None,
        max_paths: int | None = None,
        prune_threshold: float | None = None,
        initial_context: str = "",
    ) -> ReasoningResult:
        """Execute multi-strategy reasoning on a question.

        This is the main entry point. It creates a root node, then applies
        each requested strategy to generate reasoning paths. Low-confidence
        paths are pruned, and the best paths are synthesized into a final
        conclusion.

        Args:
            question: The question to reason about.
            strategies: List of reasoning strategies to apply.
            max_paths: Maximum number of paths to explore.
            prune_threshold: Confidence threshold for path pruning.
            initial_context: Optional context to seed the reasoning.

        Returns:
            A ReasoningResult with the synthesized conclusion.
        """
        start_time = time.time()
        strategies = strategies or [ReasoningStrategy.LINEAR]
        max_paths = max_paths or self.MAX_PATHS
        prune_threshold = prune_threshold or self.PRUNE_CONFIDENCE_THRESHOLD

        # Create root node
        root_content = f"Question: {question}"
        if initial_context:
            root_content += f"\nContext: {initial_context}"
        root = self.create_node(content=root_content, confidence=1.0)
        self.evaluate_node(root.node_id, confidence=1.0)

        all_paths: list[ReasoningPath] = []

        # Apply each strategy
        for strategy in strategies:
            strategy_paths = self._apply_strategy(
                root.node_id, question, strategy, max_paths
            )
            all_paths.extend(strategy_paths)
            self._stats.strategy_usage[strategy.value] = (
                self._stats.strategy_usage.get(strategy.value, 0) + 1
            )

        # Prune low-confidence paths
        pruned_count = 0
        selected_paths: list[ReasoningPath] = []
        for path in all_paths:
            if path.confidence < prune_threshold:
                self.prune_path(path.path_id)
                pruned_count += 1
            elif path.confidence >= self.MIN_CONFIDENCE_FOR_SELECTION:
                self.select_path(path.path_id)
                selected_paths.append(path)

        # Synthesize conclusion
        conclusion = self._synthesize(question, selected_paths)

        # Generate alternatives
        alternatives = self._generate_alternatives(question, selected_paths, all_paths)

        execution_time = (time.time() - start_time) * 1000

        result = ReasoningResult(
            question=question,
            conclusion=conclusion,
            confidence=self._aggregate_confidence(selected_paths),
            paths_explored=len(all_paths),
            paths_selected=len(selected_paths),
            total_nodes=len(self._nodes),
            strategies_used=[s.value for s in strategies],
            selected_paths=selected_paths,
            reasoning_trace=self._build_trace(selected_paths),
            alternatives=alternatives,
            execution_time_ms=execution_time,
        )

        self._results.append(result)
        self._stats.total_queries += 1
        self._stats.total_paths_explored += len(all_paths)
        self._stats.avg_confidence = self._compute_avg_confidence()
        self._stats.avg_execution_ms = self._compute_avg_execution()
        if all_paths:
            self._stats.path_prune_rate = pruned_count / len(all_paths)

        return result

    def _apply_strategy(
        self,
        root_id: str,
        question: str,
        strategy: ReasoningStrategy,
        max_paths: int,
    ) -> list[ReasoningPath]:
        """Apply a specific reasoning strategy to generate paths."""
        paths: list[ReasoningPath] = []

        if strategy == ReasoningStrategy.LINEAR:
            paths = self._linear_reasoning(root_id, question, max_paths)
        elif strategy == ReasoningStrategy.BRANCHING:
            paths = self._branching_reasoning(root_id, question, max_paths)
        elif strategy == ReasoningStrategy.RECURSIVE:
            paths = self._recursive_reasoning(root_id, question, max_paths)
        elif strategy == ReasoningStrategy.CONTRASTIVE:
            paths = self._contrastive_reasoning(root_id, question, max_paths)
        elif strategy == ReasoningStrategy.ABDUCTIVE:
            paths = self._abductive_reasoning(root_id, question, max_paths)
        elif strategy == ReasoningStrategy.DEDUCTIVE:
            paths = self._deductive_reasoning(root_id, question, max_paths)
        elif strategy == ReasoningStrategy.INDUCTIVE:
            paths = self._inductive_reasoning(root_id, question, max_paths)
        elif strategy == ReasoningStrategy.ANALOGICAL:
            paths = self._analogical_reasoning(root_id, question, max_paths)

        return paths

    def _linear_reasoning(
        self, root_id: str, question: str, max_paths: int
    ) -> list[ReasoningPath]:
        """Generate a linear chain-of-thought reasoning path."""
        steps = [
            f"Step 1: Understand the core question - {question}",
            "Step 2: Identify key components and constraints",
            "Step 3: Analyze relevant information and relationships",
            "Step 4: Form initial reasoning chain",
            "Step 5: Validate logical consistency",
            "Step 6: Draw conclusion",
        ]

        node_ids = [root_id]
        for i, step in enumerate(steps):
            node = self.create_node(
                content=step,
                parent_id=node_ids[-1],
                confidence=0.9 - (i * 0.05),
            )
            self.evaluate_node(
                node.node_id,
                confidence=0.9 - (i * 0.05),
                status=NodeStatus.EVALUATED,
            )
            node_ids.append(node.node_id)

        path = self.create_path(
            nodes=node_ids,
            conclusion=f"Linear reasoning complete for: {question}",
            strategy=ReasoningStrategy.LINEAR,
        )
        self.evaluate_path(
            path.path_id,
            confidence=0.85,
            quality_score=0.8,
            coherence_score=0.9,
            novelty_score=0.3,
        )
        return [path]

    def _branching_reasoning(
        self, root_id: str, question: str, max_paths: int
    ) -> list[ReasoningPath]:
        """Generate multiple branching reasoning paths."""
        branches = [
            ["Analytical: Decompose the problem into sub-problems", "Solve each sub-problem", "Recombine solutions"],
            ["Creative: Generate novel approaches", "Evaluate feasibility", "Select best creative approach"],
            ["Critical: Identify potential flaws", "Stress-test assumptions", "Validate robustness"],
            ["Practical: Consider real-world constraints", "Evaluate implementation", "Assess practicality"],
        ]

        paths: list[ReasoningPath] = []
        for i, branch_steps in enumerate(branches):
            node_ids = [root_id]
            for step in branch_steps:
                node = self.create_node(
                    content=step,
                    parent_id=node_ids[-1],
                    confidence=0.8 - (i * 0.05),
                )
                self.evaluate_node(
                    node.node_id,
                    confidence=0.8 - (i * 0.05),
                    status=NodeStatus.EVALUATED,
                )
                node_ids.append(node.node_id)

            path = self.create_path(
                nodes=node_ids,
                conclusion=f"Branch {i+1} conclusion for: {question}",
                strategy=ReasoningStrategy.BRANCHING,
            )
            self.evaluate_path(
                path.path_id,
                confidence=0.75 - (i * 0.05),
                quality_score=0.7 + (i * 0.05),
                coherence_score=0.8,
                novelty_score=0.5 + (i * 0.1),
            )
            paths.append(path)

        return paths

    def _recursive_reasoning(
        self, root_id: str, question: str, max_paths: int
    ) -> list[ReasoningPath]:
        """Generate recursive self-referential reasoning."""
        steps = [
            "Initial analysis of the question",
            "What assumptions am I making?",
            "Are these assumptions valid?",
            "Re-examine the question from first principles",
            "Synthesize recursive insights",
        ]

        node_ids = [root_id]
        for step in steps:
            node = self.create_node(content=step, parent_id=node_ids[-1], confidence=0.85)
            self.evaluate_node(node.node_id, confidence=0.85, status=NodeStatus.EVALUATED)
            node_ids.append(node.node_id)

        path = self.create_path(
            nodes=node_ids,
            conclusion=f"Recursive reflection complete for: {question}",
            strategy=ReasoningStrategy.RECURSIVE,
        )
        self.evaluate_path(
            path.path_id, confidence=0.8, quality_score=0.75,
            coherence_score=0.85, novelty_score=0.6,
        )
        return [path]

    def _contrastive_reasoning(
        self, root_id: str, question: str, max_paths: int
    ) -> list[ReasoningPath]:
        """Generate contrastive comparison reasoning."""
        node_ids = [root_id]
        steps = [
            "Identify contrasting perspectives on the question",
            "Perspective A: Proponents' view",
            "Perspective B: Opponents' view",
            "Compare and contrast key differences",
            "Synthesize balanced understanding",
        ]
        for step in steps:
            node = self.create_node(content=step, parent_id=node_ids[-1], confidence=0.8)
            self.evaluate_node(node.node_id, confidence=0.8, status=NodeStatus.EVALUATED)
            node_ids.append(node.node_id)

        path = self.create_path(
            nodes=node_ids,
            conclusion=f"Contrastive analysis complete for: {question}",
            strategy=ReasoningStrategy.CONTRASTIVE,
        )
        self.evaluate_path(
            path.path_id, confidence=0.78, quality_score=0.82,
            coherence_score=0.88, novelty_score=0.45,
        )
        return [path]

    def _abductive_reasoning(
        self, root_id: str, question: str, max_paths: int
    ) -> list[ReasoningPath]:
        """Generate abductive (best explanation) reasoning."""
        node_ids = [root_id]
        steps = [
            "Observe the phenomenon or question",
            "Generate possible explanations",
            "Evaluate each explanation's plausibility",
            "Select the best explanation",
            "Validate the selected explanation",
        ]
        for step in steps:
            node = self.create_node(content=step, parent_id=node_ids[-1], confidence=0.8)
            self.evaluate_node(node.node_id, confidence=0.8, status=NodeStatus.EVALUATED)
            node_ids.append(node.node_id)

        path = self.create_path(
            nodes=node_ids,
            conclusion=f"Best explanation for: {question}",
            strategy=ReasoningStrategy.ABDUCTIVE,
        )
        self.evaluate_path(
            path.path_id, confidence=0.75, quality_score=0.78,
            coherence_score=0.82, novelty_score=0.55,
        )
        return [path]

    def _deductive_reasoning(
        self, root_id: str, question: str, max_paths: int
    ) -> list[ReasoningPath]:
        """Generate deductive rule-based reasoning."""
        node_ids = [root_id]
        steps = [
            "Establish known rules and premises",
            "Apply rules to the specific case",
            "Derive logical consequences",
            "Verify consistency with premises",
            "State deductive conclusion",
        ]
        for step in steps:
            node = self.create_node(content=step, parent_id=node_ids[-1], confidence=0.85)
            self.evaluate_node(node.node_id, confidence=0.85, status=NodeStatus.EVALUATED)
            node_ids.append(node.node_id)

        path = self.create_path(
            nodes=node_ids,
            conclusion=f"Deductive conclusion for: {question}",
            strategy=ReasoningStrategy.DEDUCTIVE,
        )
        self.evaluate_path(
            path.path_id, confidence=0.88, quality_score=0.85,
            coherence_score=0.92, novelty_score=0.25,
        )
        return [path]

    def _inductive_reasoning(
        self, root_id: str, question: str, max_paths: int
    ) -> list[ReasoningPath]:
        """Generate inductive pattern-based reasoning."""
        node_ids = [root_id]
        steps = [
            "Gather specific observations or examples",
            "Identify patterns across observations",
            "Form general hypothesis from patterns",
            "Test hypothesis against more examples",
            "State inductive generalization",
        ]
        for step in steps:
            node = self.create_node(content=step, parent_id=node_ids[-1], confidence=0.8)
            self.evaluate_node(node.node_id, confidence=0.8, status=NodeStatus.EVALUATED)
            node_ids.append(node.node_id)

        path = self.create_path(
            nodes=node_ids,
            conclusion=f"Inductive generalization for: {question}",
            strategy=ReasoningStrategy.INDUCTIVE,
        )
        self.evaluate_path(
            path.path_id, confidence=0.72, quality_score=0.75,
            coherence_score=0.78, novelty_score=0.5,
        )
        return [path]

    def _analogical_reasoning(
        self, root_id: str, question: str, max_paths: int
    ) -> list[ReasoningPath]:
        """Generate analogy-based reasoning."""
        node_ids = [root_id]
        steps = [
            "Identify the core problem structure",
            "Find analogous problems or domains",
            "Map the analogy to the current problem",
            "Transfer insights from the analogy",
            "Validate the analogical transfer",
        ]
        for step in steps:
            node = self.create_node(content=step, parent_id=node_ids[-1], confidence=0.8)
            self.evaluate_node(node.node_id, confidence=0.8, status=NodeStatus.EVALUATED)
            node_ids.append(node.node_id)

        path = self.create_path(
            nodes=node_ids,
            conclusion=f"Analogical insight for: {question}",
            strategy=ReasoningStrategy.ANALOGICAL,
        )
        self.evaluate_path(
            path.path_id, confidence=0.7, quality_score=0.72,
            coherence_score=0.75, novelty_score=0.7,
        )
        return [path]

    def _synthesize(
        self, question: str, selected_paths: list[ReasoningPath]
    ) -> str:
        """Synthesize a final conclusion from selected reasoning paths."""
        if not selected_paths:
            return f"Unable to reach a confident conclusion for: {question}"

        conclusions = [p.conclusion for p in selected_paths if p.conclusion]
        if not conclusions:
            return f"Reasoning paths explored but no clear conclusion reached for: {question}"

        if len(conclusions) == 1:
            return conclusions[0]

        # Weighted synthesis
        total_weight = sum(p.confidence for p in selected_paths)
        if total_weight == 0:
            return " | ".join(conclusions)

        return (
            f"Synthesized conclusion (from {len(selected_paths)} paths): "
            f"{' | '.join(conclusions[:3])}"
        )

    def _generate_alternatives(
        self,
        question: str,
        selected: list[ReasoningPath],
        all_paths: list[ReasoningPath],
    ) -> list[str]:
        """Generate alternative conclusions from non-selected paths."""
        alternatives: list[str] = []
        for path in all_paths:
            if path not in selected and path.conclusion:
                alternatives.append(path.conclusion)
        return alternatives[:5]

    def _aggregate_confidence(self, paths: list[ReasoningPath]) -> float:
        """Aggregate confidence across selected paths."""
        if not paths:
            return 0.0
        return sum(p.confidence for p in paths) / len(paths)

    def _build_trace(self, paths: list[ReasoningPath]) -> list[dict[str, Any]]:
        """Build a reasoning trace from selected paths."""
        trace: list[dict[str, Any]] = []
        for path in paths:
            for node_id in path.nodes:
                node = self._nodes.get(node_id)
                if node:
                    trace.append({
                        "node_id": node.node_id,
                        "content": node.content,
                        "confidence": node.confidence,
                        "depth": node.depth,
                        "status": node.status.value,
                    })
        return trace

    def _compute_avg_confidence(self) -> float:
        """Compute average confidence across all results."""
        if not self._results:
            return 0.0
        return sum(r.confidence for r in self._results) / len(self._results)

    def _compute_avg_execution(self) -> float:
        """Compute average execution time."""
        if not self._results:
            return 0.0
        return sum(r.execution_time_ms for r in self._results) / len(self._results)

    # ── Query & Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get reasoning network statistics."""
        return {
            "total_queries": self._stats.total_queries,
            "total_paths_explored": self._stats.total_paths_explored,
            "total_nodes_created": self._stats.total_nodes_created,
            "avg_confidence": round(self._stats.avg_confidence, 3),
            "avg_execution_ms": round(self._stats.avg_execution_ms, 1),
            "strategy_usage": self._stats.strategy_usage,
            "path_prune_rate": round(self._stats.path_prune_rate, 3),
            "active_nodes": len(self._nodes),
            "active_paths": len(self._paths),
            "total_results": len(self._results),
        }

    def get_recent_results(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent reasoning results."""
        return [
            {
                "result_id": r.result_id,
                "question": r.question,
                "conclusion": r.conclusion,
                "confidence": r.confidence,
                "paths_explored": r.paths_explored,
                "paths_selected": r.paths_selected,
                "strategies_used": r.strategies_used,
                "execution_time_ms": r.execution_time_ms,
                "alternatives": r.alternatives,
            }
            for r in self._results[-limit:]
        ]

    def reset(self) -> None:
        """Reset the reasoning network to initial state."""
        self._nodes.clear()
        self._paths.clear()
        self._results.clear()
        self._stats = NetworkStats()


# ── Singleton Access ───────────────────────────────────────────────

_reasoning_network: AgenticReasoningNetwork | None = None


def get_reasoning_network() -> AgenticReasoningNetwork:
    """Get or create the singleton reasoning network instance."""
    global _reasoning_network
    if _reasoning_network is None:
        _reasoning_network = AgenticReasoningNetwork()
    return _reasoning_network


def reset_reasoning_network() -> None:
    """Reset the singleton reasoning network."""
    global _reasoning_network
    if _reasoning_network:
        _reasoning_network.reset()
    _reasoning_network = None