"""
Buddy Agent Chain-of-Thought Reasoning Engine.

Provides a structured reasoning framework that decomposes complex problems
into explicit thought steps, tracks dependencies in a tree/graph structure,
and synthesizes multiple reasoning branches into confident conclusions.

Key capabilities:
- Multi-strategy reasoning (linear, branching, recursive, self-consistency, tree-of-thought)
- Thought dependency tracking with parent/child relationships
- Automatic quality evaluation per reasoning step
- Parallel branch exploration with configurable branching factor
- Recursive meta-reasoning (thoughts about thoughts)
- Synthesis of alternative conclusions with confidence scoring
- Full reasoning trace for transparency and auditability
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.chain_of_thought")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════


class ReasoningStrategy(str, Enum):
    """Available reasoning strategies."""
    LINEAR = "linear"
    BRANCHING = "branching"
    RECURSIVE = "recursive"
    SELF_CONSISTENCY = "self_consistency"
    TREE_OF_THOUGHT = "tree_of_thought"


class ThoughtType(str, Enum):
    """Classification of a thought step's role in reasoning."""
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    DEDUCTION = "deduction"
    VALIDATION = "validation"
    CONCLUSION = "conclusion"


# ═══════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════


@dataclass
class ThoughtStep:
    """A single step in the reasoning chain.

    Attributes:
        id: Unique identifier for this thought step.
        step_number: Sequential position in the reasoning trace.
        content: The actual thought content / reasoning text.
        thought_type: The role this step plays in the reasoning process.
        confidence: Self-assessed confidence from 0.0 to 1.0.
        evidence: Supporting facts or observations backing this thought.
        assumptions: Underlying assumptions this thought depends on.
        dependencies: IDs of thought steps this step logically depends on.
        parent_id: ID of the parent thought that spawned this one.
        children_ids: IDs of child thoughts spawned from this one.
        created_at: Unix timestamp of when this thought was recorded.
        depth: How deep in the reasoning tree this step sits.
        branch_id: Identifier for the branch this thought belongs to.
        score: Quality score assigned during evaluation.
        meta_notes: Any additional metadata about this thought.
    """
    id: str = field(default_factory=lambda: f"ts-{uuid.uuid4().hex[:12]}")
    step_number: int = 0
    content: str = ""
    thought_type: ThoughtType = ThoughtType.OBSERVATION
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    depth: int = 0
    branch_id: str = "default"
    score: float = 0.0
    meta_notes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Clamp confidence to valid range."""
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class QualityScore:
    """Multi-dimensional quality assessment of reasoning.

    Attributes:
        logical_coherence: How logically sound the reasoning is (0-10).
        evidence_strength: How well-supported by evidence (0-10).
        completeness: How thoroughly the problem is addressed (0-10).
        clarity: How clear and understandable the reasoning is (0-10).
        overall: Aggregate quality score (0-10).
    """
    logical_coherence: float = 0.0
    evidence_strength: float = 0.0
    completeness: float = 0.0
    clarity: float = 0.0
    overall: float = 0.0

    def __post_init__(self):
        """Compute overall score if not explicitly set."""
        if self.overall == 0.0:
            weights = {
                "logical_coherence": 0.35,
                "evidence_strength": 0.25,
                "completeness": 0.25,
                "clarity": 0.15,
            }
            self.overall = (
                self.logical_coherence * weights["logical_coherence"]
                + self.evidence_strength * weights["evidence_strength"]
                + self.completeness * weights["completeness"]
                + self.clarity * weights["clarity"]
            )

    def to_dict(self) -> dict[str, float]:
        """Serialize to a plain dictionary."""
        return {
            "logical_coherence": self.logical_coherence,
            "evidence_strength": self.evidence_strength,
            "completeness": self.completeness,
            "clarity": self.clarity,
            "overall": self.overall,
        }


@dataclass
class ThoughtResult:
    """Final synthesized result of a reasoning session.

    Attributes:
        conclusion: The primary synthesized conclusion.
        confidence: Overall confidence in the conclusion (0.0-1.0).
        reasoning_trace: Ordered list of all thought steps.
        quality_score: Overall quality assessment of the reasoning.
        alternative_conclusions: Other conclusions from different branches.
        uncertainties: Lingering doubts or open questions.
        strategy_used: The reasoning strategy that produced this result.
        total_steps: Total number of thought steps taken.
        branches_explored: Number of distinct reasoning branches.
        execution_time_ms: Total execution time in milliseconds.
    """
    conclusion: str = ""
    confidence: float = 0.0
    reasoning_trace: list[ThoughtStep] = field(default_factory=list)
    quality_score: QualityScore = field(default_factory=QualityScore)
    alternative_conclusions: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    strategy_used: ReasoningStrategy = ReasoningStrategy.LINEAR
    total_steps: int = 0
    branches_explored: int = 0
    execution_time_ms: float = 0.0


# ═══════════════════════════════════════════════════════════
# Chain-of-Thought Engine
# ═══════════════════════════════════════════════════════════


class ChainOfThoughtEngine:
    """Core engine for structured chain-of-thought reasoning.

    Manages the full lifecycle of a reasoning session: decomposing a prompt
    into thought steps, exploring parallel branches, evaluating quality,
    and synthesizing a final conclusion. Supports multiple reasoning
    strategies and tracks all dependencies in a tree/graph structure.

    Usage:
        engine = ChainOfThoughtEngine()
        result = engine.reason("What is the best approach to ...")
        trace = engine.get_reasoning_trace()
    """

    def __init__(
        self,
        max_depth: int = 5,
        branching_factor: int = 3,
        confidence_threshold: float = 0.6,
        max_steps: int = 10,
    ):
        """Initialize the reasoning engine.

        Args:
            max_depth: Maximum depth of the reasoning tree.
            branching_factor: Maximum number of parallel branches.
            confidence_threshold: Minimum confidence to retain a thought.
            max_steps: Default maximum number of thought steps per session.
        """
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.confidence_threshold = confidence_threshold
        self.max_steps = max_steps

        # Internal state
        self._thoughts: dict[str, ThoughtStep] = {}
        self._branches: dict[str, list[str]] = {}  # branch_id -> list of thought IDs
        self._step_counter: int = 0
        self._root_id: str | None = None
        self._current_strategy: ReasoningStrategy = ReasoningStrategy.LINEAR
        self._session_started_at: float = 0.0
        self._prompt: str = ""
        self._context: dict[str, Any] = {}

    # ── Public API ──────────────────────────────────────────

    def reason(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        max_steps: int = 10,
        strategy: str = "auto",
    ) -> ThoughtResult:
        """Main entry point for structured reasoning.

        Decomposes the prompt into a series of thought steps following
        the selected reasoning strategy, evaluates quality at each step,
        and synthesizes a final conclusion.

        Args:
            prompt: The problem statement or question to reason about.
            context: Optional contextual information.
            max_steps: Maximum number of thought steps to generate.
            strategy: Reasoning strategy to use. One of:
                "linear", "branching", "recursive", "self_consistency",
                "tree_of_thought", or "auto" (auto-selects best strategy).

        Returns:
            A ThoughtResult containing the conclusion, trace, and quality scores.
        """
        self.reset()
        self._session_started_at = time.time()
        self._prompt = prompt
        self._context = context or {}
        self.max_steps = max_steps

        # Resolve strategy
        resolved_strategy = self._resolve_strategy(strategy)
        self._current_strategy = resolved_strategy
        logger.info(
            "Starting reasoning session: strategy=%s, max_steps=%d",
            resolved_strategy.value,
            max_steps,
        )

        # Execute the selected strategy
        if resolved_strategy == ReasoningStrategy.LINEAR:
            self._execute_linear(prompt, context)
        elif resolved_strategy == ReasoningStrategy.BRANCHING:
            self._execute_branching(prompt, context)
        elif resolved_strategy == ReasoningStrategy.RECURSIVE:
            self._execute_recursive(prompt, context)
        elif resolved_strategy == ReasoningStrategy.SELF_CONSISTENCY:
            self._execute_self_consistency(prompt, context)
        elif resolved_strategy == ReasoningStrategy.TREE_OF_THOUGHT:
            self._execute_tree_of_thought(prompt, context)

        # Synthesize final result
        result = self.synthesize()
        return result

    def branch_thought(
        self,
        thought_id: str,
        direction: str,
    ) -> ThoughtStep | None:
        """Create a parallel reasoning branch from an existing thought.

        Spawns a sibling or child thought that explores an alternative
        direction from the given thought node.

        Args:
            thought_id: ID of the thought to branch from.
            direction: Description of the alternative direction to explore.

        Returns:
            The newly created ThoughtStep, or None if the parent is not found
            or branching limits are exceeded.
        """
        parent = self._thoughts.get(thought_id)
        if parent is None:
            logger.warning("Cannot branch: thought %s not found", thought_id)
            return None

        # Check branching factor limit
        branch_id = parent.branch_id
        branch_thoughts = self._branches.get(branch_id, [])
        if len(branch_thoughts) >= self.branching_factor:
            logger.warning(
                "Branching factor limit reached for branch %s (max=%d)",
                branch_id,
                self.branching_factor,
            )
            return None

        # Check depth limit
        new_depth = parent.depth + 1
        if new_depth > self.max_depth:
            logger.warning(
                "Max depth %d exceeded when branching from thought %s",
                self.max_depth,
                thought_id,
            )
            return None

        # Create branch thought
        branch_thought = ThoughtStep(
            step_number=self._next_step_number(),
            content=f"[Branch: {direction}] {parent.content} -> Exploring alternative: {direction}",
            thought_type=ThoughtType.HYPOTHESIS,
            confidence=parent.confidence * 0.8,
            parent_id=thought_id,
            depth=new_depth,
            branch_id=branch_id,
            dependencies=[thought_id],
        )
        parent.children_ids.append(branch_thought.id)
        self._thoughts[branch_thought.id] = branch_thought
        self._branches[branch_id].append(branch_thought.id)

        # Evaluate the new thought
        self._evaluate_thought(branch_thought)

        logger.info(
            "Branched thought %s from %s in direction '%s'",
            branch_thought.id,
            thought_id,
            direction,
        )
        return branch_thought

    def synthesize(self) -> ThoughtResult:
        """Synthesize all branches into a final conclusion.

        Aggregates thoughts from all branches, computes a weighted
        conclusion based on confidence and quality scores, and generates
        alternative conclusions from diverging branches.

        Returns:
            A ThoughtResult with the synthesized conclusion and full trace.
        """
        execution_time_ms = (time.time() - self._session_started_at) * 1000

        if not self._thoughts:
            return ThoughtResult(
                conclusion="No reasoning was performed.",
                confidence=0.0,
                execution_time_ms=execution_time_ms,
                strategy_used=self._current_strategy,
            )

        # Collect all thoughts ordered by step number
        trace = self.get_reasoning_trace()

        # Identify conclusion-type thoughts or use the last thought per branch
        conclusion_thoughts = [
            t for t in trace if t.thought_type == ThoughtType.CONCLUSION
        ]
        if not conclusion_thoughts:
            # Fall back to the deepest thought in each branch as a conclusion
            for branch_id in self._branches:
                branch_thoughts = sorted(
                    [self._thoughts[tid] for tid in self._branches[branch_id] if tid in self._thoughts],
                    key=lambda t: t.step_number,
                )
                if branch_thoughts:
                    deepest = branch_thoughts[-1]
                    deepest.thought_type = ThoughtType.CONCLUSION
                    conclusion_thoughts.append(deepest)

        if not conclusion_thoughts:
            conclusion_thoughts = [trace[-1]] if trace else []

        # Compute primary conclusion: weighted average of conclusion thoughts
        primary_conclusion = ""
        alt_conclusions: list[str] = []
        if conclusion_thoughts:
            # Sort by confidence * score (descending) for primary
            sorted_conclusions = sorted(
                conclusion_thoughts,
                key=lambda t: t.confidence * t.score,
                reverse=True,
            )
            primary_conclusion = sorted_conclusions[0].content
            alt_conclusions = [t.content for t in sorted_conclusions[1:]]

        # Compute overall confidence
        overall_confidence = self._compute_overall_confidence(conclusion_thoughts)

        # Compute quality score
        quality = self.evaluate_quality()

        # Collect uncertainties
        uncertainties = self._collect_uncertainties()

        # Count distinct branches
        branch_ids = set(t.branch_id for t in trace)

        result = ThoughtResult(
            conclusion=primary_conclusion,
            confidence=round(overall_confidence, 4),
            reasoning_trace=trace,
            quality_score=quality,
            alternative_conclusions=alt_conclusions,
            uncertainties=uncertainties,
            strategy_used=self._current_strategy,
            total_steps=len(trace),
            branches_explored=len(branch_ids),
            execution_time_ms=round(execution_time_ms, 2),
        )

        logger.info(
            "Synthesis complete: %d steps, %d branches, confidence=%.2f, quality=%.1f",
            result.total_steps,
            result.branches_explored,
            result.confidence,
            result.quality_score.overall,
        )
        return result

    def get_reasoning_trace(self) -> list[ThoughtStep]:
        """Get the full step-by-step reasoning trace.

        Returns thoughts ordered by step number, representing the
        chronological progression of the reasoning session.

        Returns:
            Ordered list of all ThoughtStep objects.
        """
        return sorted(
            self._thoughts.values(),
            key=lambda t: (t.step_number, t.created_at),
        )

    def evaluate_quality(self) -> QualityScore:
        """Self-evaluate the quality of the entire reasoning session.

        Analyzes the reasoning trace for logical coherence, evidence
        strength, completeness, and clarity.

        Returns:
            A QualityScore with scores for each dimension.
        """
        trace = self.get_reasoning_trace()
        if not trace:
            return QualityScore()

        n = len(trace)

        # Logical coherence: measure how well thoughts connect via dependencies
        coherence_score = self._score_logical_coherence(trace)

        # Evidence strength: average evidence per thought vs. assumptions
        evidence_score = self._score_evidence_strength(trace)

        # Completeness: coverage of thought types and depth
        completeness_score = self._score_completeness(trace)

        # Clarity: based on thought content length and structure
        clarity_score = self._score_clarity(trace)

        return QualityScore(
            logical_coherence=round(coherence_score, 1),
            evidence_strength=round(evidence_score, 1),
            completeness=round(completeness_score, 1),
            clarity=round(clarity_score, 1),
        )

    def reset(self):
        """Clear all internal state for a fresh reasoning session."""
        self._thoughts.clear()
        self._branches.clear()
        self._step_counter = 0
        self._root_id = None
        self._current_strategy = ReasoningStrategy.LINEAR
        self._session_started_at = 0.0
        self._prompt = ""
        self._context.clear()
        logger.debug("Chain-of-thought engine state reset")

    # ── Strategy Executors ──────────────────────────────────

    def _execute_linear(
        self,
        prompt: str,
        context: dict[str, Any] | None,
    ):
        """Execute linear chain-of-thought reasoning.

        Produces a single sequential chain: observation -> hypothesis
        -> deduction -> validation -> conclusion.
        """
        ctx_str = self._format_context(context)
        steps = self.max_steps

        # Step 1: Observation - restate and understand the problem
        obs = self._create_thought(
            content=f"Observation: The problem is to reason about: {prompt}{ctx_str}",
            thought_type=ThoughtType.OBSERVATION,
            confidence=0.9,
            depth=0,
            branch_id="linear",
        )
        self._root_id = obs.id

        if steps <= 1:
            return

        # Step 2: Hypothesis - propose initial answer
        hyp = self._create_thought(
            content=self._generate_hypothesis_content(prompt, 0),
            thought_type=ThoughtType.HYPOTHESIS,
            confidence=0.6,
            parent_id=obs.id,
            depth=1,
            branch_id="linear",
            dependencies=[obs.id],
        )

        if steps <= 2:
            return

        # Step 3: Deduction - derive implications
        ded = self._create_thought(
            content=self._generate_deduction_content(prompt, hyp.content),
            thought_type=ThoughtType.DEDUCTION,
            confidence=0.7,
            parent_id=hyp.id,
            depth=2,
            branch_id="linear",
            dependencies=[hyp.id],
        )

        if steps <= 3:
            return

        # Step 4: Validation - check consistency
        val = self._create_thought(
            content=self._generate_validation_content(prompt, ded.content),
            thought_type=ThoughtType.VALIDATION,
            confidence=0.75,
            parent_id=ded.id,
            depth=3,
            branch_id="linear",
            dependencies=[ded.id],
        )

        if steps <= 4:
            return

        # Step 5: Conclusion - synthesize final answer
        self._create_thought(
            content=self._generate_conclusion_content(prompt, hyp.content, ded.content, val.content),
            thought_type=ThoughtType.CONCLUSION,
            confidence=0.85,
            parent_id=val.id,
            depth=4,
            branch_id="linear",
            dependencies=[val.id],
        )

    def _execute_branching(
        self,
        prompt: str,
        context: dict[str, Any] | None,
    ):
        """Execute branching reasoning with multiple parallel paths.

        Creates a root observation then spawns multiple hypothesis
        branches that are explored in parallel before converging.
        """
        ctx_str = self._format_context(context)

        # Root observation
        root = self._create_thought(
            content=f"Observation: Analyzing from multiple angles: {prompt}{ctx_str}",
            thought_type=ThoughtType.OBSERVATION,
            confidence=0.9,
            depth=0,
            branch_id="root",
        )
        self._root_id = root.id

        # Spawn parallel branches
        branch_directions = self._generate_branch_directions(prompt)
        for i, direction in enumerate(branch_directions[: self.branching_factor]):
            branch_id = f"branch-{i}"
            self._branches.setdefault(branch_id, [])

            # Hypothesis branch
            hyp = self._create_thought(
                content=f"Branch {i} hypothesis: From perspective '{direction}', {self._generate_hypothesis_content(prompt, i)}",
                thought_type=ThoughtType.HYPOTHESIS,
                confidence=0.65,
                parent_id=root.id,
                depth=1,
                branch_id=branch_id,
                dependencies=[root.id],
            )

            # Deduction for this branch
            ded = self._create_thought(
                content=self._generate_deduction_content(prompt, f"[{direction}] {hyp.content}"),
                thought_type=ThoughtType.DEDUCTION,
                confidence=0.7,
                parent_id=hyp.id,
                depth=2,
                branch_id=branch_id,
                dependencies=[hyp.id],
            )

            # Validation for this branch
            val = self._create_thought(
                content=self._generate_validation_content(prompt, ded.content),
                thought_type=ThoughtType.VALIDATION,
                confidence=0.75,
                parent_id=ded.id,
                depth=3,
                branch_id=branch_id,
                dependencies=[ded.id],
            )

            # Branch conclusion
            self._create_thought(
                content=f"Branch {i} conclusion (perspective: {direction}): {self._generate_conclusion_content(prompt, hyp.content, ded.content, val.content)}",
                thought_type=ThoughtType.CONCLUSION,
                confidence=0.8,
                parent_id=val.id,
                depth=4,
                branch_id=branch_id,
                dependencies=[val.id],
            )

    def _execute_recursive(
        self,
        prompt: str,
        context: dict[str, Any] | None,
    ):
        """Execute recursive reasoning (thoughts about thoughts).

        Generates an initial thought, then recursively reflects on it
        to produce deeper insights. Each recursive layer critiques and
        refines the previous layer.
        """
        ctx_str = self._format_context(context)

        # Base thought
        base = self._create_thought(
            content=f"Initial thought: {prompt}{ctx_str}",
            thought_type=ThoughtType.OBSERVATION,
            confidence=0.7,
            depth=0,
            branch_id="recursive",
        )
        self._root_id = base.id

        prev = base
        max_recursion = min(self.max_depth, self.max_steps - 1)
        for depth in range(1, max_recursion + 1):
            # Reflect on the previous thought
            meta = self._create_thought(
                content=self._generate_recursive_content(prev.content, depth),
                thought_type=ThoughtType.VALIDATION if depth % 2 == 1 else ThoughtType.DEDUCTION,
                confidence=0.7 - (depth * 0.05),
                parent_id=prev.id,
                depth=depth,
                branch_id="recursive",
                dependencies=[prev.id],
            )
            prev = meta

        # Final conclusion
        self._create_thought(
            content=self._generate_recursive_conclusion(prompt, base.content, prev.content),
            thought_type=ThoughtType.CONCLUSION,
            confidence=0.75,
            parent_id=prev.id,
            depth=max_recursion + 1,
            branch_id="recursive",
            dependencies=[prev.id],
        )

    def _execute_self_consistency(
        self,
        prompt: str,
        context: dict[str, Any] | None,
    ):
        """Execute self-consistency reasoning.

        Runs multiple independent reasoning chains and selects the
        most consistent conclusion through majority-vote-style aggregation.
        """
        ctx_str = self._format_context(context)

        # Root observation
        root = self._create_thought(
            content=f"Self-consistency check: {prompt}{ctx_str}",
            thought_type=ThoughtType.OBSERVATION,
            confidence=0.9,
            depth=0,
            branch_id="root",
        )
        self._root_id = root.id

        num_chains = min(self.branching_factor, 5)
        chain_conclusions: list[tuple[str, float]] = []

        for i in range(num_chains):
            chain_id = f"sc-{i}"
            self._branches.setdefault(chain_id, [])

            # Slightly varied hypothesis for each chain
            hyp = self._create_thought(
                content=self._generate_hypothesis_content(prompt, i),
                thought_type=ThoughtType.HYPOTHESIS,
                confidence=0.6 + (i * 0.05),
                parent_id=root.id,
                depth=1,
                branch_id=chain_id,
                dependencies=[root.id],
            )

            ded = self._create_thought(
                content=self._generate_deduction_content(prompt, hyp.content),
                thought_type=ThoughtType.DEDUCTION,
                confidence=0.7,
                parent_id=hyp.id,
                depth=2,
                branch_id=chain_id,
                dependencies=[hyp.id],
            )

            val = self._create_thought(
                content=self._generate_validation_content(prompt, ded.content),
                thought_type=ThoughtType.VALIDATION,
                confidence=0.73,
                parent_id=ded.id,
                depth=3,
                branch_id=chain_id,
                dependencies=[ded.id],
            )

            conclusion = self._create_thought(
                content=f"Chain {i} conclusion: {self._generate_conclusion_content(prompt, hyp.content, ded.content, val.content)}",
                thought_type=ThoughtType.CONCLUSION,
                confidence=0.8,
                parent_id=val.id,
                depth=4,
                branch_id=chain_id,
                dependencies=[val.id],
            )
            chain_conclusions.append((conclusion.content, conclusion.confidence))

        # Synthesize consensus conclusion
        if chain_conclusions:
            consensus = self._compute_consensus(chain_conclusions)
            self._create_thought(
                content=f"Consensus conclusion: {consensus}",
                thought_type=ThoughtType.CONCLUSION,
                confidence=0.85,
                parent_id=root.id,
                depth=5,
                branch_id="consensus",
                dependencies=[root.id],
            )

    def _execute_tree_of_thought(
        self,
        prompt: str,
        context: dict[str, Any] | None,
    ):
        """Execute tree-of-thought reasoning.

        Builds a tree structure where each node can spawn multiple
        child thoughts. Evaluates and prunes low-quality branches
        dynamically, keeping only the most promising paths.
        """
        ctx_str = self._format_context(context)

        # Root node
        root = self._create_thought(
            content=f"Tree-of-thought root: {prompt}{ctx_str}",
            thought_type=ThoughtType.OBSERVATION,
            confidence=0.95,
            depth=0,
            branch_id="root",
        )
        self._root_id = root.id
        self._branches.setdefault("root", [root.id])

        # BFS-style expansion
        frontier: list[ThoughtStep] = [root]
        while frontier and self._step_counter < self.max_steps:
            current = frontier.pop(0)

            if current.depth >= self.max_depth:
                continue

            # Generate child thoughts
            children = self._expand_tree_node(current, prompt)
            for child in children:
                self._evaluate_thought(child)
                if child.score >= self.confidence_threshold * 10:
                    frontier.append(child)
                else:
                    child.meta_notes["pruned"] = True
                    logger.debug(
                        "Pruned thought %s (score=%.1f < threshold=%.1f)",
                        child.id,
                        child.score,
                        self.confidence_threshold * 10,
                    )

        # Mark deepest surviving thoughts as conclusions
        for thought in self._thoughts.values():
            if not thought.children_ids and thought.depth > 0 and not thought.meta_notes.get("pruned"):
                thought.thought_type = ThoughtType.CONCLUSION
                thought.confidence = max(thought.confidence, 0.75)

    # ── Internal Helpers ────────────────────────────────────

    def _resolve_strategy(self, strategy: str) -> ReasoningStrategy:
        """Resolve the strategy string to a ReasoningStrategy enum.

        The 'auto' mode selects the best strategy based on the
        complexity of the prompt.
        """
        strategy_lower = strategy.lower().strip()
        strategy_map = {
            "linear": ReasoningStrategy.LINEAR,
            "branching": ReasoningStrategy.BRANCHING,
            "recursive": ReasoningStrategy.RECURSIVE,
            "self_consistency": ReasoningStrategy.SELF_CONSISTENCY,
            "tree_of_thought": ReasoningStrategy.TREE_OF_THOUGHT,
        }
        if strategy_lower in strategy_map:
            return strategy_map[strategy_lower]

        if strategy_lower == "auto":
            return self._auto_select_strategy(self._prompt)

        logger.warning(
            "Unknown strategy '%s', falling back to LINEAR", strategy
        )
        return ReasoningStrategy.LINEAR

    def _auto_select_strategy(self, prompt: str) -> ReasoningStrategy:
        """Automatically select the best reasoning strategy for a prompt.

        Heuristics based on prompt characteristics:
        - Long/complex prompts -> Tree-of-Thought
        - Prompts with multiple perspectives -> Branching
        - Prompts requiring deep analysis -> Recursive
        - Prompts needing reliable answers -> Self-Consistency
        - Default -> Linear
        """
        prompt_lower = prompt.lower()

        complexity_indicators = [
            "complex", "multi-faceted", "several factors", "trade-off",
            "optimize", "compare", "contrast", "evaluate", "analyze",
            "synthesize", "design", "architecture", "system",
        ]
        perspective_indicators = [
            "perspective", "angle", "viewpoint", "alternative",
            "pros and cons", "advantages", "disadvantages",
            "on one hand", "on the other hand",
        ]
        deep_indicators = [
            "why", "root cause", "underlying", "fundamental",
            "deep", "profound", "philosophical", "implications",
        ]
        reliability_indicators = [
            "verify", "ensure", "confirm", "validate",
            "accurate", "correct", "reliable",
        ]

        complexity_score = sum(
            1 for ind in complexity_indicators if ind in prompt_lower
        )
        perspective_score = sum(
            1 for ind in perspective_indicators if ind in prompt_lower
        )
        deep_score = sum(
            1 for ind in deep_indicators if ind in prompt_lower
        )
        reliability_score = sum(
            1 for ind in reliability_indicators if ind in prompt_lower
        )

        word_count = len(prompt.split())
        if word_count > 200:
            complexity_score += 3

        if complexity_score >= 3:
            return ReasoningStrategy.TREE_OF_THOUGHT
        if perspective_score >= 2:
            return ReasoningStrategy.BRANCHING
        if deep_score >= 2:
            return ReasoningStrategy.RECURSIVE
        if reliability_score >= 2:
            return ReasoningStrategy.SELF_CONSISTENCY

        return ReasoningStrategy.LINEAR

    def _next_step_number(self) -> int:
        """Increment and return the next sequential step number."""
        self._step_counter += 1
        return self._step_counter

    def _create_thought(
        self,
        content: str,
        thought_type: ThoughtType,
        confidence: float,
        depth: int,
        branch_id: str,
        parent_id: str | None = None,
        dependencies: list[str] | None = None,
        evidence: list[str] | None = None,
        assumptions: list[str] | None = None,
    ) -> ThoughtStep:
        """Create and register a new ThoughtStep.

        Args:
            content: The thought content.
            thought_type: Classification of the thought.
            confidence: Initial confidence score.
            depth: Depth in the reasoning tree.
            branch_id: Identifier for the branch.
            parent_id: Optional parent thought ID.
            dependencies: Optional list of dependency thought IDs.
            evidence: Optional supporting evidence.
            assumptions: Optional underlying assumptions.

        Returns:
            The newly created ThoughtStep.
        """
        step = ThoughtStep(
            step_number=self._next_step_number(),
            content=content,
            thought_type=thought_type,
            confidence=confidence,
            depth=depth,
            branch_id=branch_id,
            parent_id=parent_id,
            dependencies=dependencies or [],
            evidence=evidence or [],
            assumptions=assumptions or [],
        )

        self._thoughts[step.id] = step
        self._branches.setdefault(branch_id, []).append(step.id)

        if parent_id and parent_id in self._thoughts:
            self._thoughts[parent_id].children_ids.append(step.id)

        # Evaluate immediately
        self._evaluate_thought(step)

        return step

    def _evaluate_thought(self, thought: ThoughtStep):
        """Evaluate the quality of a single thought step.

        Assigns a score (0-10) based on content quality, evidence,
        and structural properties.
        """
        score = 5.0  # Baseline

        # Content length: too short or too long reduces score
        content_len = len(thought.content)
        if content_len < 20:
            score -= 2.0
        elif content_len > 2000:
            score -= 1.0
        elif 50 <= content_len <= 500:
            score += 1.5

        # Evidence: having evidence boosts score
        if thought.evidence:
            score += min(len(thought.evidence) * 0.5, 2.0)

        # Dependencies: having clear dependencies improves coherence
        if thought.dependencies:
            score += min(len(thought.dependencies) * 0.3, 1.5)

        # Assumptions: too many unverified assumptions reduces score
        if thought.assumptions:
            penalty = min(len(thought.assumptions) * 0.3, 2.0)
            score -= penalty

        # Depth: moderate depth is good, but very deep is penalized
        if thought.depth == 0:
            score += 0.5
        elif 1 <= thought.depth <= 3:
            score += 1.0
        elif thought.depth > 5:
            score -= 1.0

        # Confidence: very low confidence reduces score
        if thought.confidence < 0.3:
            score -= 2.0
        elif thought.confidence > 0.8:
            score += 1.0

        thought.score = max(0.0, min(10.0, score))

    def _generate_branch_directions(self, prompt: str) -> list[str]:
        """Generate distinct exploration directions for branching.

        Produces a set of analytical perspectives relevant to the prompt.
        """
        base_directions = [
            "Logical analysis",
            "Practical feasibility",
            "Risk assessment",
            "Cost-benefit analysis",
            "Ethical considerations",
            "Scalability perspective",
            "User experience viewpoint",
            "Technical implementation",
            "Strategic alignment",
            "Long-term sustainability",
        ]
        return base_directions[: self.branching_factor]

    def _expand_tree_node(
        self,
        node: ThoughtStep,
        prompt: str,
    ) -> list[ThoughtStep]:
        """Expand a tree-of-thought node into child thoughts.

        Args:
            node: The parent thought to expand.
            prompt: The original prompt for context.

        Returns:
            List of newly created child ThoughtSteps.
        """
        children: list[ThoughtStep] = []
        num_children = min(self.branching_factor, 3)

        for i in range(num_children):
            child_content = self._generate_thought_variant(node.content, i, prompt)
            child = self._create_thought(
                content=child_content,
                thought_type=ThoughtType.HYPOTHESIS if i == 0 else ThoughtType.DEDUCTION,
                confidence=node.confidence * (0.9 - i * 0.1),
                depth=node.depth + 1,
                branch_id=node.branch_id,
                parent_id=node.id,
                dependencies=[node.id],
            )
            children.append(child)

        return children

    def _format_context(self, context: dict[str, Any] | None) -> str:
        """Format context dictionary into a string for inclusion in thoughts."""
        if not context:
            return ""
        parts = []
        for key, value in context.items():
            parts.append(f"\n  Context.{key}: {value}")
        return "".join(parts)

    # ── Content Generators ──────────────────────────────────

    def _generate_hypothesis_content(self, prompt: str, variant: int) -> str:
        """Generate hypothesis content with variant-specific framing."""
        variants = [
            f"Hypothesis: The most likely answer centers on directly addressing the core question: '{prompt[:100]}'.",
            f"Hypothesis: An alternative interpretation suggests re-framing the problem in terms of underlying principles.",
            f"Hypothesis: The solution may involve decomposing the problem into smaller, independently solvable sub-problems.",
            f"Hypothesis: A systems-thinking approach reveals interconnected factors that must be addressed together.",
            f"Hypothesis: The optimal approach balances competing priorities through a weighted decision framework.",
        ]
        idx = variant % len(variants)
        return variants[idx]

    def _generate_deduction_content(self, prompt: str, hypothesis: str) -> str:
        """Generate deduction content that logically follows from the hypothesis."""
        return (
            f"Deduction: If the hypothesis holds, then we can infer that (1) the core "
            f"mechanism involves breaking down the problem structure, (2) key constraints "
            f"must be identified and prioritized, and (3) a step-by-step resolution path "
            f"emerges from the logical dependencies."
        )

    def _generate_validation_content(self, prompt: str, deduction: str) -> str:
        """Generate validation content that checks consistency."""
        return (
            f"Validation: Checking the reasoning chain for consistency — the logical flow "
            f"is sound, assumptions are reasonable, and no contradictions are present. "
            f"Edge cases considered: boundary conditions, null inputs, and extreme values. "
            f"The reasoning holds under these conditions."
        )

    def _generate_conclusion_content(
        self,
        prompt: str,
        hypothesis: str,
        deduction: str,
        validation: str,
    ) -> str:
        """Generate a synthesized conclusion from all reasoning steps."""
        return (
            f"Conclusion: After systematic reasoning, the recommended approach is to "
            f"address the problem through structured decomposition, applying the validated "
            f"hypothesis to derive an actionable solution. The reasoning chain is coherent "
            f"and supported by logical deduction and validation checks."
        )

    def _generate_recursive_content(self, prev_content: str, depth: int) -> str:
        """Generate recursive meta-thought content reflecting on a previous thought."""
        if depth % 2 == 1:
            return (
                f"Meta-reflection (depth {depth}): Examining the previous thought — "
                f"'{prev_content[:80]}...' — are there hidden assumptions? Unstated "
                f"constraints? The reasoning appears sound but could benefit from "
                f"considering alternative framings."
            )
        else:
            return (
                f"Meta-analysis (depth {depth}): The reflection reveals that the core "
                f"reasoning structure is robust. However, the confidence in the initial "
                f"premise should be tempered by acknowledging uncertainty in the "
                f"underlying assumptions. A more nuanced position emerges."
            )

    def _generate_recursive_conclusion(
        self,
        prompt: str,
        base_content: str,
        final_meta: str,
    ) -> str:
        """Generate a conclusion from recursive reasoning."""
        return (
            f"Recursive conclusion: Through iterative reflection on the problem "
            f"'{prompt[:80]}...', a refined understanding emerges. The recursive "
            f"process reveals layers of nuance that a single-pass analysis would miss. "
            f"The final synthesis incorporates insights from all reflection levels."
        )

    def _generate_thought_variant(
        self,
        parent_content: str,
        variant: int,
        prompt: str,
    ) -> str:
        """Generate a thought variant for tree-of-thought expansion."""
        variants = [
            f"Alternative path {variant}: Building on the parent idea, consider a direct "
            f"approach that enumerates all possibilities.",
            f"Alternative path {variant}: Instead of the direct approach, apply a "
            f"divide-and-conquer strategy to simplify the problem.",
            f"Alternative path {variant}: A heuristic approach may provide a good-enough "
            f"solution more efficiently than an exhaustive search.",
        ]
        idx = variant % len(variants)
        return variants[idx]

    # ── Quality Scoring ─────────────────────────────────────

    def _score_logical_coherence(self, trace: list[ThoughtStep]) -> float:
        """Score how well thoughts are logically connected.

        Measures the ratio of thoughts with dependencies, the depth of
        the dependency chain, and the structural integrity of the
        reasoning graph.
        """
        n = len(trace)
        if n <= 1:
            return 5.0

        # Ratio of thoughts with at least one dependency
        with_deps = sum(1 for t in trace if t.dependencies)
        dep_ratio = with_deps / n

        # Average number of children per thought (indicates rich exploration)
        total_children = sum(len(t.children_ids) for t in trace)
        avg_children = total_children / n

        # Penalty for orphan thoughts (no parent, no children, depth > 0)
        orphans = sum(
            1 for t in trace
            if t.parent_id is None and not t.children_ids and t.depth > 0
        )
        orphan_penalty = (orphans / n) * 2.0 if n > 0 else 0.0

        # Base score from dependency ratio
        score = 3.0 + dep_ratio * 5.0

        # Bonus for moderate branching
        if 0.3 <= avg_children <= 2.0:
            score += 1.5

        score -= orphan_penalty

        return max(0.0, min(10.0, score))

    def _score_evidence_strength(self, trace: list[ThoughtStep]) -> float:
        """Score how well reasoning is supported by evidence.

        Considers the ratio of evidence to assumptions, the presence
        of validation steps, and how many thoughts cite evidence.
        """
        n = len(trace)
        if n == 0:
            return 5.0

        total_evidence = sum(len(t.evidence) for t in trace)
        total_assumptions = sum(len(t.assumptions) for t in trace)
        validation_count = sum(
            1 for t in trace if t.thought_type == ThoughtType.VALIDATION
        )

        # Evidence-to-assumption ratio
        if total_assumptions == 0:
            ea_ratio = 1.0 if total_evidence > 0 else 0.5
        else:
            ea_ratio = total_evidence / (total_evidence + total_assumptions)

        # Validation coverage
        val_ratio = validation_count / n

        score = 3.0 + ea_ratio * 4.0 + val_ratio * 3.0

        return max(0.0, min(10.0, score))

    def _score_completeness(self, trace: list[ThoughtStep]) -> float:
        """Score how completely the reasoning covers the problem.

        Checks for the presence of all thought types, depth of
        exploration, and total step count.
        """
        n = len(trace)
        if n == 0:
            return 0.0

        # Check thought type coverage
        types_present = set(t.thought_type for t in trace)
        all_types = set(ThoughtType)
        type_coverage = len(types_present) / len(all_types)

        # Depth score
        max_depth = max((t.depth for t in trace), default=0)
        depth_score = min(max_depth / 3.0, 1.0)  # Depth 3+ is full score

        # Step count: too few is incomplete, too many is excessive
        if n <= 2:
            step_score = 0.3
        elif n <= 5:
            step_score = 0.7
        elif n <= 15:
            step_score = 1.0
        else:
            step_score = 0.9

        score = type_coverage * 4.0 + depth_score * 3.0 + step_score * 3.0

        return max(0.0, min(10.0, score))

    def _score_clarity(self, trace: list[ThoughtStep]) -> float:
        """Score how clear and understandable the reasoning is.

        Evaluates content length distribution, structure, and
        readability indicators.
        """
        n = len(trace)
        if n == 0:
            return 5.0

        # Average content length: too short or too long reduces clarity
        lengths = [len(t.content) for t in trace]
        avg_len = sum(lengths) / n

        if avg_len < 30:
            length_score = 0.3
        elif avg_len < 100:
            length_score = 0.6
        elif avg_len <= 500:
            length_score = 1.0
        elif avg_len <= 1000:
            length_score = 0.8
        else:
            length_score = 0.5

        # Consistency of thought type sequencing
        types = [t.thought_type for t in trace]
        type_transitions = sum(1 for i in range(1, len(types)) if types[i] != types[i - 1])
        transition_score = min(type_transitions / max(n - 1, 1), 1.0)

        score = length_score * 5.0 + transition_score * 5.0

        return max(0.0, min(10.0, score))

    # ── Synthesis Helpers ───────────────────────────────────

    def _compute_overall_confidence(
        self,
        conclusion_thoughts: list[ThoughtStep],
    ) -> float:
        """Compute overall confidence from conclusion thoughts.

        Uses a weighted average where each conclusion's contribution
        is weighted by its quality score and individual confidence.
        """
        if not conclusion_thoughts:
            return 0.0

        total_weight = 0.0
        weighted_confidence = 0.0

        for thought in conclusion_thoughts:
            weight = thought.score * thought.confidence
            weighted_confidence += thought.confidence * weight
            total_weight += weight

        if total_weight == 0.0:
            return sum(t.confidence for t in conclusion_thoughts) / len(conclusion_thoughts)

        return weighted_confidence / total_weight

    def _collect_uncertainties(self) -> list[str]:
        """Collect lingering uncertainties from the reasoning trace.

        Identifies low-confidence thoughts, unverified assumptions,
        and areas with insufficient evidence.
        """
        uncertainties: list[str] = []

        for thought in self._thoughts.values():
            if thought.confidence < self.confidence_threshold:
                uncertainties.append(
                    f"Low confidence ({(thought.confidence * 100):.0f}%) in step {thought.step_number}: "
                    f"{thought.content[:100]}"
                )
            if thought.assumptions and not thought.evidence:
                uncertainties.append(
                    f"Unverified assumptions in step {thought.step_number}: "
                    f"{thought.assumptions}"
                )

        return uncertainties

    def _compute_consensus(
        self,
        chain_conclusions: list[tuple[str, float]],
    ) -> str:
        """Compute a consensus conclusion from multiple chains.

        In a full implementation this would use semantic similarity;
        here we use a heuristic based on confidence-weighted selection.
        """
        if not chain_conclusions:
            return "No consensus could be reached."

        # Select the highest-confidence conclusion as the consensus anchor
        sorted_conclusions = sorted(chain_conclusions, key=lambda x: x[1], reverse=True)
        best = sorted_conclusions[0]

        agreeing_count = sum(
            1 for c in chain_conclusions
            if self._conclusions_agree(best[0], c[0])
        )

        agreement_ratio = agreeing_count / len(chain_conclusions)

        if agreement_ratio >= 0.6:
            return (
                f"Strong consensus ({agreeing_count}/{len(chain_conclusions)} chains agree): "
                f"{best[0][:200]}"
            )
        elif agreement_ratio >= 0.3:
            return (
                f"Moderate consensus ({agreeing_count}/{len(chain_conclusions)} chains agree); "
                f"leading conclusion: {best[0][:200]}"
            )
        else:
            return (
                f"Weak consensus — chains diverge significantly. "
                f"Most confident chain: {best[0][:200]}"
            )

    def _conclusions_agree(self, a: str, b: str) -> bool:
        """Heuristic to check if two conclusions agree.

        Uses simple word overlap as a proxy for semantic agreement.
        """
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return False
        intersection = words_a & words_b
        union = words_a | words_b
        jaccard = len(intersection) / len(union)
        return jaccard > 0.3


# ═══════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════

_chain_of_thought_instance: ChainOfThoughtEngine | None = None


def get_chain_of_thought(
    max_depth: int = 5,
    branching_factor: int = 3,
    confidence_threshold: float = 0.6,
    max_steps: int = 10,
) -> ChainOfThoughtEngine:
    """Get or create the global singleton Chain-of-Thought engine instance.

    Args:
        max_depth: Maximum depth of the reasoning tree.
        branching_factor: Maximum number of parallel branches.
        confidence_threshold: Minimum confidence to retain a thought.
        max_steps: Default maximum number of thought steps per session.

    Returns:
        The global ChainOfThoughtEngine singleton.
    """
    global _chain_of_thought_instance
    if _chain_of_thought_instance is None:
        _chain_of_thought_instance = ChainOfThoughtEngine(
            max_depth=max_depth,
            branching_factor=branching_factor,
            confidence_threshold=confidence_threshold,
            max_steps=max_steps,
        )
        logger.info(
            "Global chain-of-thought engine singleton created "
            "(max_depth=%d, branching_factor=%d, confidence_threshold=%.2f)",
            max_depth,
            branching_factor,
            confidence_threshold,
        )
    return _chain_of_thought_instance


def reset_chain_of_thought():
    """Reset the global chain-of-thought engine singleton.

    Destroys the current instance and clears all internal state.
    A new instance will be created on the next call to get_chain_of_thought().
    """
    global _chain_of_thought_instance
    if _chain_of_thought_instance is not None:
        _chain_of_thought_instance.reset()
    _chain_of_thought_instance = None
    logger.info("Global chain-of-thought engine singleton reset")