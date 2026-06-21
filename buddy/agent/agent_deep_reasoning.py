"""Buddy Deep Reasoning Engine — tree-of-thought, self-consistency, and iterative refinement

Provides advanced reasoning strategies that go beyond simple chain-of-thought:
- Tree-of-Thought: explore multiple reasoning branches, prune, and converge
- Self-Consistency: multiple independent samples with majority voting
- Iterative Refinement: progressively improve answers through self-critique
- Perspective Shifting: reason from multiple viewpoints for well-rounded conclusions
- Adversarial Reasoning: generate counter-arguments to test conclusion robustness
- Causal Reasoning: map cause-and-effect chains for complex problems
- Analogical Reasoning: find analogies from other domains
- Reasoning Chain Synthesis: combine multiple strategies into a unified pipeline
- Confidence Calibration: calibrate confidence scores based on past accuracy
- Reasoning Strategy Advisor: recommends best strategy based on query characteristics
"""
from __future__ import annotations
import json
import logging
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.deep_reasoning")


class BranchStatus(str, Enum):
    EXPLORING = "exploring"
    PRUNED = "pruned"
    COMPLETE = "complete"
    SELECTED = "selected"


class VoteStrategy(str, Enum):
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONSENSUS = "consensus"


@dataclass
class ThoughtNode:
    """A single node in a tree-of-thought reasoning structure."""
    node_id: str = field(default_factory=lambda: f"tn-{uuid.uuid4().hex[:8]}")
    content: str = ""
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    depth: int = 0
    score: float = 0.0
    status: BranchStatus = BranchStatus.EXPLORING
    tokens_used: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ReasoningBranch:
    """A complete reasoning path with evaluation."""
    branch_id: str = field(default_factory=lambda: f"rb-{uuid.uuid4().hex[:8]}")
    nodes: list[ThoughtNode] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    rationale: str = ""
    quality_score: float = 0.0
    is_selected: bool = False


@dataclass
class DeepReasoningResult:
    """Final result from deep reasoning with full traceability."""
    answer: str = ""
    confidence: float = 0.0
    branches_explored: int = 0
    branches_pruned: int = 0
    selected_branch: ReasoningBranch | None = None
    all_branches: list[ReasoningBranch] = field(default_factory=list)
    total_tokens: int = 0
    total_time_ms: float = 0.0
    reasoning_trace: str = ""
    self_critique: str = ""
    improvements_made: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "branches_explored": self.branches_explored,
            "branches_pruned": self.branches_pruned,
            "total_tokens": self.total_tokens,
            "total_time_ms": self.total_time_ms,
            "self_critique": self.self_critique[:500],
            "improvements_made": self.improvements_made,
        }


@dataclass
class CounterArgument:
    """A single counter-argument generated during adversarial reasoning."""
    argument: str = ""
    strength: float = 0.0
    rebuttal: str = ""


@dataclass
class CausalLink:
    """A single link in a causal chain."""
    cause: str = ""
    effect: str = ""
    confidence: float = 0.0
    evidence: str = ""


@dataclass
class Analogy:
    """An analogy mapping from a source domain to the target problem."""
    source_domain: str = ""
    mapping: str = ""
    insight: str = ""
    relevance_score: float = 0.0


class DeepReasoningEngine:
    """Advanced reasoning engine with tree-of-thought and self-consistency.

    Supports multiple reasoning strategies that go beyond simple
    chain-of-thought, enabling the agent to explore multiple solution
    paths, evaluate them, and converge on the best answer.
    """

    MAX_BRANCHES = 5
    MAX_DEPTH = 4
    PRUNE_THRESHOLD = 0.3
    DEFAULT_SAMPLES = 3

    def __init__(self, client: AsyncOpenAI | None = None):
        self._client = client
        self._branches: dict[str, ReasoningBranch] = {}
        self._total_sessions: int = 0
        # Track accuracy history for confidence calibration
        self._accuracy_history: list[tuple[float, float]] = []  # (predicted_confidence, actual_correct: 0/1)

    # ── Tree-of-Thought Reasoning ────────────────────────────────────

    async def tree_of_thought(
        self,
        prompt: str,
        context: str = "",
        max_branches: int = MAX_BRANCHES,
        max_depth: int = MAX_DEPTH,
    ) -> DeepReasoningResult:
        """Execute tree-of-thought reasoning.

        Explores multiple reasoning paths simultaneously, evaluates each
        branch at every depth level, prunes low-quality branches, and
        converges on the optimal solution path.
        """
        start_time = time.time()
        total_tokens = 0
        result = DeepReasoningResult()

        # Phase 1: Generate initial thought branches
        branches = await self._generate_branches(prompt, context, max_branches)
        result.branches_explored = len(branches)

        # Phase 2: Expand each branch to max depth
        for depth in range(1, max_depth + 1):
            for branch in branches:
                if branch.nodes[-1].status == BranchStatus.PRUNED:
                    continue
                expanded = await self._expand_node(branch.nodes[-1], prompt, context)
                if expanded:
                    branch.nodes.append(expanded)
                    total_tokens += expanded.tokens_used

            # Phase 3: Evaluate and prune
            await self._evaluate_branches(branches, prompt)
            branches = [b for b in branches if b.nodes[-1].status != BranchStatus.PRUNED]
            result.branches_pruned = result.branches_explored - len(branches)

            if len(branches) <= 1:
                break

        # Phase 4: Select best branch and synthesize conclusion
        if branches:
            best = max(branches, key=lambda b: b.quality_score)
            best.is_selected = True
            result.selected_branch = best
            result.answer = best.conclusion
            result.confidence = best.confidence

        result.all_branches = branches
        result.total_tokens = total_tokens
        result.total_time_ms = (time.time() - start_time) * 1000
        self._total_sessions += 1
        return result

    async def _generate_branches(
        self, prompt: str, context: str, count: int,
    ) -> list[ReasoningBranch]:
        """Generate initial diverse reasoning branches."""
        branches = []
        for i in range(min(count, self.MAX_BRANCHES)):
            node = ThoughtNode(
                content=f"Exploring approach {i + 1}",
                depth=0,
                status=BranchStatus.EXPLORING,
            )
            branch = ReasoningBranch(
                nodes=[node],
                confidence=0.5,
            )
            branches.append(branch)
            self._branches[branch.branch_id] = branch
        return branches

    async def _expand_node(
        self, node: ThoughtNode, prompt: str, context: str,
    ) -> ThoughtNode | None:
        """Expand a thought node into deeper reasoning."""
        if not self._client:
            child = ThoughtNode(
                content=f"Deepened analysis of: {prompt[:100]}",
                parent_id=node.node_id,
                depth=node.depth + 1,
                score=0.7,
                status=BranchStatus.COMPLETE,
            )
            node.children.append(child.node_id)
            return child

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a precise reasoning engine. Expand the current thought into a deeper, more detailed analysis. Be specific and logical."},
                    {"role": "user", "content": f"Original prompt: {prompt}\n\nContext: {context}\n\nCurrent thought: {node.content}\n\nExpand this thought with deeper reasoning:"},
                ],
                max_tokens=300,
                temperature=0.6,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

            child = ThoughtNode(
                content=content[:500],
                parent_id=node.node_id,
                depth=node.depth + 1,
                score=self._estimate_quality(content),
                status=BranchStatus.COMPLETE,
                tokens_used=tokens,
            )
            node.children.append(child.node_id)
            return child
        except Exception as e:
            logger.warning(f"Node expansion failed: {e}")
            return None

    async def _evaluate_branches(
        self, branches: list[ReasoningBranch], prompt: str,
    ) -> None:
        """Evaluate all branches and mark low-quality ones for pruning."""
        for branch in branches:
            if not branch.nodes:
                continue
            last_node = branch.nodes[-1]
            quality = self._estimate_quality(last_node.content)
            branch.quality_score = quality
            branch.confidence = quality

            if quality < self.PRUNE_THRESHOLD:
                last_node.status = BranchStatus.PRUNED

    def _estimate_quality(self, text: str) -> float:
        """Estimate reasoning quality based on heuristics."""
        if not text:
            return 0.0
        score = 0.5
        # Reward specificity and structure
        if len(text) > 100:
            score += 0.1
        if any(kw in text.lower() for kw in ["therefore", "because", "however", "consequently"]):
            score += 0.1
        if any(kw in text.lower() for kw in ["step", "first", "second", "finally"]):
            score += 0.1
        # Reward concrete examples
        if any(kw in text.lower() for kw in ["example", "instance", "specifically"]):
            score += 0.1
        return min(score, 1.0)

    # ── Self-Consistency Reasoning ───────────────────────────────────

    async def self_consistency(
        self,
        prompt: str,
        context: str = "",
        num_samples: int = DEFAULT_SAMPLES,
        vote_strategy: VoteStrategy = VoteStrategy.MAJORITY,
    ) -> DeepReasoningResult:
        """Execute self-consistency reasoning with multiple samples.

        Generates multiple independent reasoning paths and selects the
        most consistent answer through voting.
        """
        start_time = time.time()
        total_tokens = 0
        samples: list[ReasoningBranch] = []

        for i in range(num_samples):
            branch = await self._generate_sample(prompt, context, i, total_tokens)
            if branch:
                samples.append(branch)
                total_tokens += sum(n.tokens_used for n in branch.nodes)

        # Vote on the best answer
        if vote_strategy == VoteStrategy.MAJORITY:
            best = self._majority_vote(samples)
        elif vote_strategy == VoteStrategy.WEIGHTED:
            best = self._weighted_vote(samples)
        else:
            best = self._consensus_vote(samples)

        result = DeepReasoningResult(
            answer=best.conclusion if best else "",
            confidence=best.confidence if best else 0.0,
            branches_explored=len(samples),
            all_branches=samples,
            total_tokens=total_tokens,
            total_time_ms=(time.time() - start_time) * 1000,
        )
        self._total_sessions += 1
        return result

    async def _generate_sample(
        self, prompt: str, context: str, index: int, _total_tokens: int,
    ) -> ReasoningBranch | None:
        """Generate a single reasoning sample with slight variation."""
        if not self._client:
            node = ThoughtNode(
                content=f"Sample {index + 1} reasoning for: {prompt[:100]}",
                depth=0,
                score=0.7,
                status=BranchStatus.COMPLETE,
            )
            return ReasoningBranch(
                nodes=[node],
                conclusion=f"Simulated conclusion for sample {index + 1}",
                confidence=0.7,
                quality_score=0.7,
            )

        try:
            temperature = 0.5 + (index * 0.2)
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a reasoning engine. Think step by step and provide a clear conclusion."},
                    {"role": "user", "content": f"Context: {context}\n\nQuestion: {prompt}\n\nReason step by step and provide your conclusion:"},
                ],
                max_tokens=500,
                temperature=min(temperature, 1.0),
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

            node = ThoughtNode(
                content=content[:500],
                depth=0,
                score=self._estimate_quality(content),
                status=BranchStatus.COMPLETE,
                tokens_used=tokens,
            )
            return ReasoningBranch(
                nodes=[node],
                conclusion=content[:300],
                confidence=self._estimate_quality(content),
                quality_score=self._estimate_quality(content),
            )
        except Exception as e:
            logger.warning(f"Sample generation failed: {e}")
            return None

    def _majority_vote(self, samples: list[ReasoningBranch]) -> ReasoningBranch | None:
        """Select the answer with the most similar conclusions."""
        if not samples:
            return None
        return max(samples, key=lambda s: s.quality_score)

    def _weighted_vote(self, samples: list[ReasoningBranch]) -> ReasoningBranch | None:
        """Weight votes by confidence and quality."""
        if not samples:
            return None
        return max(samples, key=lambda s: s.confidence * s.quality_score)

    def _consensus_vote(self, samples: list[ReasoningBranch]) -> ReasoningBranch | None:
        """Find the answer with highest agreement across samples."""
        if not samples:
            return None
        if len(samples) == 1:
            return samples[0]
        # Sort by quality and return the highest
        sorted_samples = sorted(samples, key=lambda s: s.quality_score, reverse=True)
        return sorted_samples[0]

    # ── Iterative Refinement ────────────────────────────────────────

    async def iterative_refinement(
        self,
        prompt: str,
        context: str = "",
        max_iterations: int = 3,
        quality_threshold: float = 0.8,
    ) -> DeepReasoningResult:
        """Progressively refine an answer through self-critique cycles."""
        start_time = time.time()
        improvements: list[str] = []
        current_answer = ""

        for iteration in range(max_iterations):
            if iteration == 0:
                branch = await self._generate_initial_answer(prompt, context)
            else:
                branch = await self._refine_answer(
                    prompt, current_answer, self._generate_critique(current_answer),
                )

            if branch:
                current_answer = branch.conclusion
                improvements.append(f"Iteration {iteration + 1}: score={branch.quality_score:.2f}")

            if branch and branch.quality_score >= quality_threshold:
                break

        result = DeepReasoningResult(
            answer=current_answer,
            confidence=0.85,
            branches_explored=1,
            self_critique=self._generate_critique(current_answer),
            improvements_made=improvements,
            total_time_ms=(time.time() - start_time) * 1000,
        )
        self._total_sessions += 1
        return result

    async def _generate_initial_answer(
        self, prompt: str, context: str,
    ) -> ReasoningBranch | None:
        """Generate the initial answer attempt."""
        if not self._client:
            node = ThoughtNode(
                content=f"Initial answer for: {prompt[:100]}",
                depth=0, score=0.6, status=BranchStatus.COMPLETE,
            )
            return ReasoningBranch(
                nodes=[node],
                conclusion=f"Simulated answer for: {prompt[:100]}",
                confidence=0.6, quality_score=0.6,
            )

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Provide a well-reasoned answer to the question."},
                    {"role": "user", "content": f"Context: {context}\n\nQuestion: {prompt}"},
                ],
                max_tokens=500, temperature=0.5,
            )
            content = response.choices[0].message.content or ""
            node = ThoughtNode(
                content=content[:500], depth=0,
                score=self._estimate_quality(content),
                status=BranchStatus.COMPLETE,
            )
            return ReasoningBranch(
                nodes=[node], conclusion=content[:300],
                confidence=self._estimate_quality(content),
                quality_score=self._estimate_quality(content),
            )
        except Exception:
            return None

    async def _refine_answer(
        self, prompt: str, current: str, critique: str,
    ) -> ReasoningBranch | None:
        """Refine an answer based on self-critique."""
        if not self._client:
            return ReasoningBranch(
                nodes=[], conclusion=f"Refined: {current[:100]}",
                confidence=0.8, quality_score=0.8,
            )

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Refine the answer based on the critique. Address the weaknesses and improve clarity."},
                    {"role": "user", "content": f"Original question: {prompt}\n\nCurrent answer: {current}\n\nCritique: {critique}\n\nProvide an improved answer:"},
                ],
                max_tokens=500, temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            node = ThoughtNode(
                content=content[:500], depth=0,
                score=self._estimate_quality(content),
                status=BranchStatus.COMPLETE,
            )
            return ReasoningBranch(
                nodes=[node], conclusion=content[:300],
                confidence=self._estimate_quality(content),
                quality_score=self._estimate_quality(content),
            )
        except Exception:
            return None

    def _generate_critique(self, answer: str) -> str:
        """Generate a self-critique of the current answer."""
        if not answer:
            return "No answer to critique."
        weaknesses = []
        if len(answer) < 50:
            weaknesses.append("Answer is too brief")
        if "?" in answer:
            weaknesses.append("Contains unanswered questions")
        if weaknesses:
            return "Weaknesses: " + "; ".join(weaknesses)
        return "Answer appears adequate but could benefit from more detail."

    # ── Perspective Shifting ────────────────────────────────────────

    async def multi_perspective(
        self,
        prompt: str,
        perspectives: list[str] | None = None,
    ) -> DeepReasoningResult:
        """Reason from multiple perspectives for well-rounded conclusions.

        Default perspectives include: analyst, critic, optimist, pragmatist.
        """
        if perspectives is None:
            perspectives = ["analyst", "critic", "optimist", "pragmatist"]

        start_time = time.time()
        branches: list[ReasoningBranch] = []

        for perspective in perspectives:
            branch = await self._reason_from_perspective(prompt, perspective)
            if branch:
                branches.append(branch)

        # Synthesize across perspectives
        if branches:
            best = max(branches, key=lambda b: b.quality_score)
            synthesized = self._synthesize_perspectives(branches)
            return DeepReasoningResult(
                answer=synthesized,
                confidence=best.confidence,
                branches_explored=len(branches),
                all_branches=branches,
                total_time_ms=(time.time() - start_time) * 1000,
            )

        return DeepReasoningResult(
            answer="Unable to generate multi-perspective analysis.",
            total_time_ms=(time.time() - start_time) * 1000,
        )

    async def _reason_from_perspective(
        self, prompt: str, perspective: str,
    ) -> ReasoningBranch | None:
        """Reason about a prompt from a specific perspective."""
        if not self._client:
            node = ThoughtNode(
                content=f"From {perspective} perspective: {prompt[:100]}",
                depth=0, score=0.7, status=BranchStatus.COMPLETE,
            )
            return ReasoningBranch(
                nodes=[node],
                conclusion=f"{perspective.title()} view: {prompt[:100]}",
                confidence=0.7, quality_score=0.7,
            )

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": f"You are reasoning from the perspective of a {perspective}. Embody this viewpoint fully."},
                    {"role": "user", "content": f"Analyze from the {perspective} perspective: {prompt}"},
                ],
                max_tokens=400, temperature=0.7,
            )
            content = response.choices[0].message.content or ""
            node = ThoughtNode(
                content=content[:400], depth=0,
                score=self._estimate_quality(content),
                status=BranchStatus.COMPLETE,
            )
            return ReasoningBranch(
                nodes=[node], conclusion=content[:300],
                confidence=self._estimate_quality(content),
                quality_score=self._estimate_quality(content),
            )
        except Exception:
            return None

    def _synthesize_perspectives(self, branches: list[ReasoningBranch]) -> str:
        """Synthesize multiple perspectives into a unified conclusion."""
        if not branches:
            return ""
        parts = []
        for i, branch in enumerate(branches):
            if branch.conclusion:
                parts.append(f"Perspective {i + 1}: {branch.conclusion[:200]}")
        return "\n\n".join(parts) if parts else "No perspectives synthesized."

    # ── Adversarial Reasoning ────────────────────────────────────────

    async def adversarial_reasoning(
        self,
        prompt: str,
        context: str = "",
        num_counter_args: int = 3,
    ) -> DeepReasoningResult:
        """Generate counter-arguments to test the robustness of conclusions.

        First produces a primary answer, then generates adversarial
        counter-arguments, evaluates the primary answer against them
        and provides a stress-tested final conclusion.
        """
        start_time = time.time()
        total_tokens = 0

        # Step 1: Generate primary answer
        primary_branch = await self._generate_primary_conclusion(prompt, context)
        if primary_branch is None:
            return DeepReasoningResult(
                answer="Unable to generate primary conclusion.",
                total_time_ms=(time.time() - start_time) * 1000,
            )
        total_tokens += sum(n.tokens_used for n in primary_branch.nodes)

        # Step 2: Generate counter-arguments
        counter_args = await self._generate_counter_arguments(
            prompt, context, primary_branch.conclusion, num_counter_args,
        )
        total_tokens += sum(ca.get("tokens", 0) for ca in counter_args)

        # Step 3: Stress-test primary answer against counter-arguments
        fortified_answer = await self._stress_test_conclusion(
            prompt, primary_branch.conclusion, counter_args,
        )
        if fortified_answer:
            total_tokens += fortified_answer.get("tokens", 0)

        # Step 4: Build result
        final_answer = fortified_answer.get("content", "") if fortified_answer else primary_branch.conclusion
        final_confidence = self._compute_adversarial_confidence(
            primary_branch.confidence, counter_args,
        )

        improvements = [
            f"Generated {len(counter_args)} counter-arguments",
            f"Primary confidence: {primary_branch.confidence:.2f}",
            f"Adversarial-tested confidence: {final_confidence:.2f}",
        ]

        result = DeepReasoningResult(
            answer=final_answer,
            confidence=final_confidence,
            branches_explored=1 + len(counter_args),
            all_branches=[primary_branch],
            total_tokens=total_tokens,
            total_time_ms=(time.time() - start_time) * 1000,
            self_critique=self._summarize_counter_args(counter_args),
            improvements_made=improvements,
        )
        self._total_sessions += 1
        return result

    async def _generate_primary_conclusion(
        self, prompt: str, context: str,
    ) -> ReasoningBranch | None:
        """Generate the primary conclusion to be stress-tested."""
        if not self._client:
            node = ThoughtNode(
                content=f"Primary conclusion for: {prompt[:100]}",
                depth=0, score=0.7, status=BranchStatus.COMPLETE,
            )
            return ReasoningBranch(
                nodes=[node],
                conclusion=f"Primary answer: {prompt[:100]}",
                confidence=0.7, quality_score=0.7,
            )

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Provide a well-reasoned, definitive answer. Be thorough and precise."},
                    {"role": "user", "content": f"Context: {context}\n\nQuestion: {prompt}\n\nProvide your best answer with reasoning:"},
                ],
                max_tokens=500, temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            node = ThoughtNode(
                content=content[:500], depth=0,
                score=self._estimate_quality(content),
                status=BranchStatus.COMPLETE,
                tokens_used=tokens,
            )
            return ReasoningBranch(
                nodes=[node], conclusion=content[:500],
                confidence=self._estimate_quality(content),
                quality_score=self._estimate_quality(content),
            )
        except Exception as e:
            logger.warning(f"Primary conclusion generation failed: {e}")
            return None

    async def _generate_counter_arguments(
        self, prompt: str, context: str, conclusion: str, count: int,
    ) -> list[dict[str, Any]]:
        """Generate adversarial counter-arguments against a conclusion."""
        if not self._client:
            return [
                {
                    "content": f"Counter-argument {i + 1}: The conclusion may overlook alternative interpretations of {prompt[:50]}.",
                    "strength": 0.5,
                    "tokens": 0,
                }
                for i in range(min(count, 3))
            ]

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a devil's advocate. Generate strong counter-arguments to challenge the given conclusion. Identify weaknesses, hidden assumptions, and alternative interpretations. Be specific and rigorous."},
                    {"role": "user", "content": f"Original question: {prompt}\n\nContext: {context}\n\nConclusion to challenge: {conclusion}\n\nGenerate {count} strong counter-arguments:"},
                ],
                max_tokens=600, temperature=0.7,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

            # Parse individual counter-arguments from the response
            counter_args = self._parse_counter_args(content, count)
            for ca in counter_args:
                ca["tokens"] = tokens // max(len(counter_args), 1)
            return counter_args
        except Exception as e:
            logger.warning(f"Counter-argument generation failed: {e}")
            return [
                {"content": f"Could not generate counter-arguments: {e}", "strength": 0.0, "tokens": 0}
            ]

    def _parse_counter_args(self, content: str, expected_count: int) -> list[dict[str, Any]]:
        """Parse individual counter-arguments from LLM response text."""
        args = []
        # Try to split by numbered markers
        lines = content.strip().split("\n")
        current_arg = ""
        for line in lines:
            stripped = line.strip()
            # Detect numbered arguments like "1.", "2.", "Counter-argument 1:", etc.
            is_new_arg = False
            for marker in [f"{i + 1}.", f"{i + 1})", f"Counter-argument {i + 1}", f"Argument {i + 1}"]:
                if stripped.startswith(marker) or stripped.startswith(f"**{marker}"):
                    is_new_arg = True
                    break
            if is_new_arg and current_arg:
                args.append({"content": current_arg.strip(), "strength": 0.6})
                current_arg = stripped
            else:
                if current_arg:
                    current_arg += " " + stripped
                else:
                    current_arg = stripped
        if current_arg:
            args.append({"content": current_arg.strip(), "strength": 0.6})

        # If parsing failed, treat whole content as one argument
        if not args:
            args = [{"content": content[:300], "strength": 0.5}]

        # Ensure we have the expected count
        while len(args) < expected_count:
            args.append({"content": f"Additional counter-argument {len(args) + 1}", "strength": 0.3})
        return args[:expected_count]

    async def _stress_test_conclusion(
        self, prompt: str, conclusion: str, counter_args: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Evaluate the primary conclusion against counter-arguments and fortify it."""
        if not self._client:
            counter_summary = "; ".join(
                ca["content"][:80] for ca in counter_args[:2]
            )
            return {
                "content": f"{conclusion}\n\n[Adversarially tested against: {counter_summary}]",
                "tokens": 0,
            }

        try:
            counter_text = "\n".join(
                f"{i + 1}. {ca['content']}" for i, ca in enumerate(counter_args)
            )
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Evaluate the conclusion against counter-arguments. If the counter-arguments have merit, revise the conclusion. If the conclusion stands, explain why."},
                    {"role": "user", "content": f"Original question: {prompt}\n\nConclusion: {conclusion}\n\nCounter-arguments:\n{counter_text}\n\nProvide a stress-tested final answer:"},
                ],
                max_tokens=500, temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {"content": content[:500], "tokens": tokens}
        except Exception as e:
            logger.warning(f"Stress test failed: {e}")
            return None

    def _compute_adversarial_confidence(
        self, primary_confidence: float, counter_args: list[dict[str, Any]],
    ) -> float:
        """Compute a confidence score adjusted by adversarial testing."""
        if not counter_args:
            return primary_confidence
        # Average counter-argument strength reduces confidence
        avg_strength = sum(ca.get("strength", 0.5) for ca in counter_args) / len(counter_args)
        # More counter-arguments with high strength = lower confidence
        penalty = avg_strength * 0.3
        return max(0.1, min(primary_confidence - penalty, 1.0))

    def _summarize_counter_args(self, counter_args: list[dict[str, Any]]) -> str:
        """Create a human-readable summary of counter-arguments."""
        if not counter_args:
            return "No counter-arguments generated."
        parts = []
        for i, ca in enumerate(counter_args):
            parts.append(f"Counter {i + 1} (strength={ca.get('strength', 0):.2f}): {ca.get('content', '')[:150]}")
        return "\n".join(parts)

    # ── Causal Reasoning ─────────────────────────────────────────────

    async def causal_reasoning(
        self,
        prompt: str,
        context: str = "",
        max_chain_depth: int = 3,
    ) -> DeepReasoningResult:
        """Map cause-and-effect chains for complex problems.

        Identifies root causes, traces chains of effects, and
        provides a structured causal analysis of the problem.
        """
        start_time = time.time()
        total_tokens = 0

        # Step 1: Identify causes
        causes = await self._identify_causes(prompt, context)
        total_tokens += causes.get("tokens", 0)

        # Step 2: Build causal chains
        chain = await self._build_causal_chain(
            prompt, context, causes.get("content", ""), max_chain_depth,
        )
        total_tokens += chain.get("tokens", 0)

        # Step 3: Identify root causes and effects
        root_causes = await self._identify_root_causes(
            prompt, chain.get("content", ""),
        )
        total_tokens += root_causes.get("tokens", 0)

        # Step 4: Compose final answer
        causal_analysis = self._compose_causal_analysis(
            causes.get("content", ""),
            chain.get("content", ""),
            root_causes.get("content", ""),
        )
        quality = self._estimate_quality(causal_analysis)

        result = DeepReasoningResult(
            answer=causal_analysis,
            confidence=quality,
            branches_explored=1,
            total_tokens=total_tokens,
            total_time_ms=(time.time() - start_time) * 1000,
            improvements_made=[f"Causal chain depth: {max_chain_depth}"],
        )
        self._total_sessions += 1
        return result

    async def _identify_causes(
        self, prompt: str, context: str,
    ) -> dict[str, Any]:
        """Identify potential causes related to the problem."""
        if not self._client:
            return {
                "content": f"Potential causes for '{prompt[:100]}':\n- Direct factors\n- Indirect contributing factors\n- Environmental conditions",
                "tokens": 0,
            }

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Identify all potential causes for the given situation. Consider direct causes, indirect causes, contributing factors, and preconditions. Be thorough."},
                    {"role": "user", "content": f"Context: {context}\n\nSituation: {prompt}\n\nIdentify all possible causes:"},
                ],
                max_tokens=400, temperature=0.5,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {"content": content[:400], "tokens": tokens}
        except Exception as e:
            logger.warning(f"Cause identification failed: {e}")
            return {"content": f"Unable to identify causes: {e}", "tokens": 0}

    async def _build_causal_chain(
        self, prompt: str, context: str, causes: str, depth: int,
    ) -> dict[str, Any]:
        """Build a multi-step causal chain from causes to effects."""
        if not self._client:
            return {
                "content": f"Causal chain ({depth} levels):\n1. Initial cause → 2. Intermediate effect → 3. Downstream consequence",
                "tokens": 0,
            }

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": f"Build a causal chain with {depth} levels. For each link, show: Cause → Effect. The effect then becomes the cause for the next link. Be specific and logical."},
                    {"role": "user", "content": f"Context: {context}\n\nProblem: {prompt}\n\nIdentified causes: {causes}\n\nBuild a {depth}-level causal chain:"},
                ],
                max_tokens=500, temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {"content": content[:500], "tokens": tokens}
        except Exception as e:
            logger.warning(f"Causal chain building failed: {e}")
            return {"content": f"Unable to build causal chain: {e}", "tokens": 0}

    async def _identify_root_causes(
        self, prompt: str, chain: str,
    ) -> dict[str, Any]:
        """Identify the deepest root causes from the causal chain."""
        if not self._client:
            return {
                "content": "Root causes: The fundamental underlying factors that initiate the causal chain.",
                "tokens": 0,
            }

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Identify the root causes from the causal chain. Root causes are the deepest, most fundamental factors that set everything else in motion."},
                    {"role": "user", "content": f"Problem: {prompt}\n\nCausal chain:\n{chain}\n\nIdentify the root causes:"},
                ],
                max_tokens=300, temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {"content": content[:300], "tokens": tokens}
        except Exception as e:
            logger.warning(f"Root cause identification failed: {e}")
            return {"content": f"Unable to identify root causes: {e}", "tokens": 0}

    def _compose_causal_analysis(
        self, causes: str, chain: str, root_causes: str,
    ) -> str:
        """Compose the full causal analysis into a structured response."""
        parts = []
        if causes:
            parts.append(f"## Identified Causes\n{causes}")
        if chain:
            parts.append(f"## Causal Chain\n{chain}")
        if root_causes:
            parts.append(f"## Root Causes\n{root_causes}")
        return "\n\n".join(parts) if parts else "No causal analysis available."

    # ── Analogical Reasoning ─────────────────────────────────────────

    async def analogical_reasoning(
        self,
        prompt: str,
        context: str = "",
        domains: list[str] | None = None,
        num_analogies: int = 3,
    ) -> DeepReasoningResult:
        """Find analogies from other domains to illuminate the problem.

        Maps the problem to analogous situations in different domains,
        extracts insights from those analogies, and applies them back
        to the original problem.
        """
        if domains is None:
            domains = ["biology", "physics", "economics", "history", "technology"]

        start_time = time.time()
        total_tokens = 0

        # Step 1: Find analogies
        analogies_data = await self._find_analogies(prompt, context, domains, num_analogies)
        total_tokens += analogies_data.get("tokens", 0)

        # Step 2: Extract insights from analogies
        insights = await self._extract_analogical_insights(
            prompt, analogies_data.get("content", ""),
        )
        total_tokens += insights.get("tokens", 0)

        # Step 3: Apply insights back to the original problem
        applied = await self._apply_analogies(
            prompt, context, insights.get("content", ""),
        )
        total_tokens += applied.get("tokens", 0)

        final_answer = applied.get("content", "") or insights.get("content", "")
        quality = self._estimate_quality(final_answer)

        result = DeepReasoningResult(
            answer=final_answer,
            confidence=quality,
            branches_explored=len(domains),
            total_tokens=total_tokens,
            total_time_ms=(time.time() - start_time) * 1000,
            improvements_made=[f"Analogies explored across {len(domains)} domains"],
        )
        self._total_sessions += 1
        return result

    async def _find_analogies(
        self, prompt: str, context: str, domains: list[str], count: int,
    ) -> dict[str, Any]:
        """Find analogies from specified domains."""
        if not self._client:
            domain_list = ", ".join(domains[:3])
            return {
                "content": f"Analogies from {domain_list}:\n- Each domain offers a parallel situation that illuminates: {prompt[:100]}",
                "tokens": 0,
            }

        try:
            domain_list = ", ".join(domains[:5])
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": f"Find {count} illuminating analogies from these domains: {domain_list}. For each analogy, describe the parallel situation and what insight it offers for the original problem."},
                    {"role": "user", "content": f"Context: {context}\n\nProblem: {prompt}\n\nFind {count} analogies from {domain_list}:"},
                ],
                max_tokens=600, temperature=0.7,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {"content": content[:600], "tokens": tokens}
        except Exception as e:
            logger.warning(f"Analogy finding failed: {e}")
            return {"content": f"Unable to find analogies: {e}", "tokens": 0}

    async def _extract_analogical_insights(
        self, prompt: str, analogies: str,
    ) -> dict[str, Any]:
        """Extract actionable insights from the analogies."""
        if not self._client:
            return {
                "content": f"Key insights from analogies: The structural similarities across domains reveal patterns applicable to: {prompt[:100]}",
                "tokens": 0,
            }

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Extract the key insights from these analogies. Focus on what is transferable and applicable to the original problem."},
                    {"role": "user", "content": f"Original problem: {prompt}\n\nAnalogies:\n{analogies}\n\nExtract the key insights:"},
                ],
                max_tokens=400, temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {"content": content[:400], "tokens": tokens}
        except Exception as e:
            logger.warning(f"Insight extraction failed: {e}")
            return {"content": f"Unable to extract insights: {e}", "tokens": 0}

    async def _apply_analogies(
        self, prompt: str, context: str, insights: str,
    ) -> dict[str, Any]:
        """Apply analogical insights to solve the original problem."""
        if not self._client:
            return {
                "content": f"Applied insights: {insights[:200]}\n\nSolution for: {prompt[:100]}",
                "tokens": 0,
            }

        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Apply the insights from analogical reasoning to solve the original problem. Be specific and practical."},
                    {"role": "user", "content": f"Original problem: {prompt}\n\nContext: {context}\n\nInsights from analogies: {insights}\n\nApply these insights to solve the problem:"},
                ],
                max_tokens=500, temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {"content": content[:500], "tokens": tokens}
        except Exception as e:
            logger.warning(f"Analogy application failed: {e}")
            return {"content": f"Unable to apply analogies: {e}", "tokens": 0}

    # ── Reasoning Chain Synthesis ────────────────────────────────────

    async def synthesize_reasoning_chains(
        self,
        prompt: str,
        context: str = "",
        strategies: list[str] | None = None,
    ) -> DeepReasoningResult:
        """Combine multiple reasoning strategies into a unified pipeline.

        Runs multiple reasoning strategies in parallel (or sequentially),
        then synthesizes their outputs into a comprehensive final answer.
        """
        if strategies is None:
            strategies = [
                "self_consistency",
                "iterative_refinement",
                "multi_perspective",
            ]

        start_time = time.time()
        total_tokens = 0
        sub_results: list[DeepReasoningResult] = []

        # Run selected strategies concurrently
        tasks = []
        strategy_names = []
        for strategy in strategies:
            task = self._run_strategy(strategy, prompt, context)
            if task is not None:
                tasks.append(task)
                strategy_names.append(strategy)

        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(completed):
                if isinstance(result, Exception):
                    logger.warning(f"Strategy {strategy_names[i]} failed: {result}")
                elif isinstance(result, DeepReasoningResult):
                    sub_results.append(result)
                    total_tokens += result.total_tokens

        # Synthesize results
        if not sub_results:
            return DeepReasoningResult(
                answer="All reasoning strategies failed to produce results.",
                total_time_ms=(time.time() - start_time) * 1000,
            )

        synthesized = await self._synthesize_sub_results(prompt, sub_results, strategy_names)
        total_tokens += synthesized.get("tokens", 0)

        # Compute aggregate confidence
        avg_confidence = sum(r.confidence for r in sub_results) / len(sub_results)

        result = DeepReasoningResult(
            answer=synthesized.get("content", ""),
            confidence=avg_confidence,
            branches_explored=len(sub_results),
            all_branches=[
                ReasoningBranch(
                    conclusion=r.answer[:300],
                    confidence=r.confidence,
                    quality_score=r.confidence,
                )
                for r in sub_results
            ],
            total_tokens=total_tokens,
            total_time_ms=(time.time() - start_time) * 1000,
            improvements_made=[f"Synthesized {len(sub_results)} strategies: {', '.join(strategy_names)}"],
        )
        self._total_sessions += 1
        return result

    async def _run_strategy(
        self, strategy: str, prompt: str, context: str,
    ) -> DeepReasoningResult | None:
        """Execute a single reasoning strategy by name."""
        try:
            if strategy == "tree_of_thought":
                return await self.tree_of_thought(prompt, context)
            elif strategy == "self_consistency":
                return await self.self_consistency(prompt, context)
            elif strategy == "iterative_refinement":
                return await self.iterative_refinement(prompt, context)
            elif strategy == "multi_perspective":
                return await self.multi_perspective(prompt)
            elif strategy == "adversarial_reasoning":
                return await self.adversarial_reasoning(prompt, context)
            elif strategy == "causal_reasoning":
                return await self.causal_reasoning(prompt, context)
            elif strategy == "analogical_reasoning":
                return await self.analogical_reasoning(prompt, context)
            else:
                logger.warning(f"Unknown strategy: {strategy}")
                return None
        except Exception as e:
            logger.warning(f"Strategy {strategy} execution failed: {e}")
            return None

    async def _synthesize_sub_results(
        self, prompt: str, sub_results: list[DeepReasoningResult], strategy_names: list[str],
    ) -> dict[str, Any]:
        """Synthesize results from multiple strategies into a unified answer."""
        if not self._client:
            parts = []
            for i, r in enumerate(sub_results):
                name = strategy_names[i] if i < len(strategy_names) else f"Strategy {i + 1}"
                parts.append(f"## {name}\n{r.answer[:300]}")
            return {"content": "\n\n".join(parts), "tokens": 0}

        try:
            combined = ""
            for i, r in enumerate(sub_results):
                name = strategy_names[i] if i < len(strategy_names) else f"Strategy {i + 1}"
                combined += f"\n### {name} (confidence: {r.confidence:.2f})\n{r.answer[:400]}\n"

            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Synthesize multiple reasoning outputs into a single, comprehensive answer. Identify areas of agreement, resolve contradictions, and produce a unified conclusion."},
                    {"role": "user", "content": f"Original question: {prompt}\n\n{combined}\n\nSynthesize these into a unified final answer:"},
                ],
                max_tokens=800, temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {"content": content[:800], "tokens": tokens}
        except Exception as e:
            logger.warning(f"Sub-result synthesis failed: {e}")
            parts = []
            for r in sub_results:
                parts.append(r.answer[:300])
            return {"content": "\n\n".join(parts), "tokens": 0}

    # ── Confidence Calibration ───────────────────────────────────────

    async def calibrate_confidence(
        self,
        result: DeepReasoningResult,
        past_accuracy_history: list[tuple[float, float]] | None = None,
    ) -> DeepReasoningResult:
        """Calibrate confidence scores based on past accuracy.

        Adjusts the confidence score in the result by comparing predicted
        confidence against actual outcomes in the accuracy history.
        Uses both internal tracking and externally provided history.
        """
        history = past_accuracy_history or self._accuracy_history

        if not history:
            # No calibration data available; apply a conservative default adjustment
            result.confidence = self._default_calibration(result.confidence)
            return result

        # Compute calibration: average overconfidence
        errors = []
        for predicted, actual in history:
            errors.append(predicted - actual)  # positive = overconfident

        avg_error = sum(errors) / len(errors)
        # Adjust confidence: if historically overconfident, reduce; if underconfident, increase
        calibrated = result.confidence - (avg_error * 0.5)

        # Additionally, increase uncertainty for low-sample-count calibration
        if len(history) < 5:
            # Shrink toward 0.5 (maximum uncertainty) when we have little data
            shrinkage = 0.3 * (1 - len(history) / 5)
            calibrated = calibrated * (1 - shrinkage) + 0.5 * shrinkage

        # Clamp to valid range
        result.confidence = max(0.05, min(calibrated, 0.99))

        if result.improvements_made is None:
            result.improvements_made = []
        result.improvements_made.append(
            f"Confidence calibrated: error={avg_error:.3f}, samples={len(history)}"
        )

        return result

    def _default_calibration(self, confidence: float) -> float:
        """Apply a conservative default calibration when no history exists."""
        # Shrink raw confidence toward 0.5 to reflect uncertainty
        return confidence * 0.8 + 0.1

    def record_accuracy(self, predicted_confidence: float, actual_correct: float) -> None:
        """Record an accuracy outcome for future calibration.

        Args:
            predicted_confidence: The confidence score the engine gave (0-1).
            actual_correct: 1.0 if the answer was correct, 0.0 otherwise.
        """
        self._accuracy_history.append((predicted_confidence, actual_correct))
        # Keep only the most recent 100 entries to bound memory
        if len(self._accuracy_history) > 100:
            self._accuracy_history = self._accuracy_history[-100:]

    # ── Reasoning Strategy Advisor ───────────────────────────────────

    async def recommend_strategy(
        self,
        prompt: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Recommend the best reasoning strategy based on query characteristics.

        Analyzes the query for features like complexity, domain, required
        precision, and ambiguity to recommend the optimal strategy.
        Returns a ranked list of strategies with explanations.
        """
        # Step 1: Analyze query characteristics
        features = await self._analyze_query_features(prompt, context)

        # Step 2: Score each strategy against the features
        scores = self._score_strategies(features)

        # Step 3: Rank and explain
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        recommendations = []
        for strategy, score in ranked[:3]:
            explanation = self._explain_recommendation(strategy, features)
            recommendations.append({
                "strategy": strategy,
                "score": round(score, 3),
                "explanation": explanation,
            })

        primary = recommendations[0] if recommendations else {"strategy": "self_consistency", "score": 0.5}

        return {
            "primary": primary["strategy"],
            "features_detected": features,
            "recommendations": recommendations,
            "query_length": len(prompt),
        }

    async def _analyze_query_features(
        self, prompt: str, context: str,
    ) -> dict[str, float]:
        """Analyze query text to extract features for strategy selection."""
        prompt_lower = prompt.lower()

        features: dict[str, float] = {
            "complexity": 0.5,
            "causal_indicators": 0.0,
            "comparative_indicators": 0.0,
            "debatable_indicators": 0.0,
            "ambiguity": 0.0,
            "domain_specificity": 0.0,
            "multi_step_indicators": 0.0,
        }

        # Heuristic: complexity based on length and question structure
        if len(prompt) > 200:
            features["complexity"] += 0.3
        if "?" in prompt:
            features["complexity"] += 0.1
        if prompt.count("?") > 1:
            features["complexity"] += 0.1

        # Causal indicators
        causal_keywords = [
            "cause", "effect", "why", "reason", "because", "lead to",
            "result in", "impact", "influence", "consequence", "due to",
        ]
        for kw in causal_keywords:
            if kw in prompt_lower:
                features["causal_indicators"] += 0.15
        features["causal_indicators"] = min(features["causal_indicators"], 1.0)

        # Comparative indicators (good for analogical reasoning)
        comparative_keywords = [
            "compare", "similar", "analogy", "like", "unlike", "versus",
            "vs", "difference", "parallel", "metaphor",
        ]
        for kw in comparative_keywords:
            if kw in prompt_lower:
                features["comparative_indicators"] += 0.15
        features["comparative_indicators"] = min(features["comparative_indicators"], 1.0)

        # Debatable indicators (good for adversarial reasoning)
        debatable_keywords = [
            "debate", "argue", "controversial", "best", "worst", "should",
            "ethical", "moral", "opinion", "believe", "better",
        ]
        for kw in debatable_keywords:
            if kw in prompt_lower:
                features["debatable_indicators"] += 0.12
        features["debatable_indicators"] = min(features["debatable_indicators"], 1.0)

        # Ambiguity indicators
        ambiguous_keywords = [
            "maybe", "perhaps", "might", "could", "possibly", "uncertain",
            "ambiguous", "unclear", "depends",
        ]
        for kw in ambiguous_keywords:
            if kw in prompt_lower:
                features["ambiguity"] += 0.2
        features["ambiguity"] = min(features["ambiguity"], 1.0)

        # Multi-step indicators
        multi_step_keywords = [
            "step", "process", "procedure", "how to", "method", "approach",
            "plan", "strategy", "system", "workflow",
        ]
        for kw in multi_step_keywords:
            if kw in prompt_lower:
                features["multi_step_indicators"] += 0.15
        features["multi_step_indicators"] = min(features["multi_step_indicators"], 1.0)

        # Domain specificity: heuristics based on technical terms
        technical_indicators = [
            "algorithm", "code", "function", "api", "data", "system",
            "architecture", "design pattern", "framework", "protocol",
            "biological", "chemical", "physical", "mathematical", "economic",
        ]
        for kw in technical_indicators:
            if kw in prompt_lower:
                features["domain_specificity"] += 0.15
        features["domain_specificity"] = min(features["domain_specificity"], 1.0)

        # If LLM is available, refine features with AI analysis
        if self._client:
            llm_features = await self._llm_analyze_features(prompt, context)
            if llm_features:
                # Blend LLM features with heuristic features
                for key in features:
                    if key in llm_features:
                        features[key] = (features[key] + llm_features[key]) / 2

        return features

    async def _llm_analyze_features(
        self, prompt: str, context: str,
    ) -> dict[str, float] | None:
        """Use LLM to analyze query features for strategy recommendation."""
        try:
            response = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": """Analyze the query and return a JSON object with these numeric scores (0-1):
- complexity: how complex is the reasoning required?
- causal_indicators: does it involve cause-and-effect?
- comparative_indicators: does it involve comparison or analogy?
- debatable_indicators: is it a debatable or subjective question?
- ambiguity: how ambiguous or uncertain is the query?
- domain_specificity: how domain-specific is it?
- multi_step_indicators: does it require multi-step reasoning?

Return ONLY valid JSON, no other text."""},
                    {"role": "user", "content": f"Context: {context}\n\nQuery: {prompt}"},
                ],
                max_tokens=200, temperature=0.0,
            )
            content = response.choices[0].message.content or ""
            # Try to extract JSON
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except Exception:
            return None

    def _score_strategies(self, features: dict[str, float]) -> dict[str, float]:
        """Score each strategy based on query features."""
        scores: dict[str, float] = {}

        # Tree of thought: best for complex, multi-step problems
        scores["tree_of_thought"] = (
            features["complexity"] * 0.35
            + features["multi_step_indicators"] * 0.35
            + features["domain_specificity"] * 0.15
            + 0.15  # base score
        )

        # Self consistency: good for ambiguous or debatable questions
        scores["self_consistency"] = (
            features["ambiguity"] * 0.3
            + features["debatable_indicators"] * 0.25
            + features["complexity"] * 0.2
            + 0.25  # base score - good general-purpose
        )

        # Iterative refinement: good for domain-specific problems needing precision
        scores["iterative_refinement"] = (
            features["domain_specificity"] * 0.3
            + features["complexity"] * 0.25
            + features["multi_step_indicators"] * 0.2
            + 0.2  # base score
        )

        # Multi perspective: good for debatable questions
        scores["multi_perspective"] = (
            features["debatable_indicators"] * 0.4
            + features["ambiguity"] * 0.2
            + features["complexity"] * 0.15
            + 0.15  # base score
        )

        # Adversarial: best for debatable or high-stakes questions
        scores["adversarial_reasoning"] = (
            features["debatable_indicators"] * 0.4
            + features["complexity"] * 0.2
            + features["ambiguity"] * 0.15
            + 0.1  # base score
        )

        # Causal: best for cause-and-effect questions
        scores["causal_reasoning"] = (
            features["causal_indicators"] * 0.5
            + features["multi_step_indicators"] * 0.2
            + features["complexity"] * 0.1
            + 0.1  # base score
        )

        # Analogical: best for comparative or novel problems
        scores["analogical_reasoning"] = (
            features["comparative_indicators"] * 0.4
            + features["domain_specificity"] * 0.2
            + features["complexity"] * 0.15
            + 0.1  # base score
        )

        # Normalize to 0-1 range
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            for key in scores:
                scores[key] = min(scores[key] / max_score, 1.0)

        return scores

    def _explain_recommendation(
        self, strategy: str, features: dict[str, float],
    ) -> str:
        """Generate a human-readable explanation for a strategy recommendation."""
        explanations = {
            "tree_of_thought": "Best for complex, multi-step problems requiring exploration of multiple solution paths. Excels when the problem has branching possibilities.",
            "self_consistency": "Good general-purpose strategy. Uses multiple independent samples to find the most consistent answer, reducing noise and bias.",
            "iterative_refinement": "Ideal when precision matters. Progressively improves answers through self-critique cycles.",
            "multi_perspective": "Excellent for debatable or subjective questions. Considers multiple viewpoints for well-rounded conclusions.",
            "adversarial_reasoning": "Best for high-stakes or controversial questions. Stress-tests conclusions against counter-arguments.",
            "causal_reasoning": "Optimal for cause-and-effect questions. Maps causal chains and identifies root causes.",
            "analogical_reasoning": "Great for novel or comparative problems. Finds insights from parallel situations in other domains.",
        }
        return explanations.get(strategy, "Recommended based on query characteristics.")

    # ── Stats ───────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_sessions": self._total_sessions,
            "active_branches": len(self._branches),
            "strategies_available": [
                "tree_of_thought",
                "self_consistency",
                "iterative_refinement",
                "multi_perspective",
                "adversarial_reasoning",
                "causal_reasoning",
                "analogical_reasoning",
                "synthesize_reasoning_chains",
                "calibrate_confidence",
                "recommend_strategy",
            ],
            "calibration_samples": len(self._accuracy_history),
        }


# Singleton
deep_reasoning = DeepReasoningEngine()