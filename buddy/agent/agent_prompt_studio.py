"""
Buddy Prompt Studio - Prompt engineering, optimization, and management.

Provides a comprehensive prompt engineering system for creating, testing,
optimizing, and managing prompts across the Buddy platform. The studio
supports prompt versioning, A/B testing, template management, and
performance analytics.

Core capabilities:
- Prompt creation and versioning with full history
- A/B testing with performance metrics comparison
- Prompt template management with variable substitution
- Automatic prompt optimization suggestions
- Performance analytics and scoring
- Prompt library with categorization and search
- Chain-of-prompts composition
- System prompt vs user prompt separation
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.prompt_studio")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class PromptType(str, Enum):
    """Types of prompts in the system."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    CHAIN = "chain"


class PromptCategory(str, Enum):
    """Categories for organizing prompts."""
    GENERAL = "general"
    CODING = "coding"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    REASONING = "reasoning"
    PLANNING = "planning"


class OptimizationStrategy(str, Enum):
    """Strategies for prompt optimization."""
    SIMPLIFY = "simplify"
    ELABORATE = "elaborate"
    RESTRUCTURE = "restructure"
    ADD_EXAMPLES = "add_examples"
    CLARIFY_INSTRUCTIONS = "clarify_instructions"
    REDUCE_AMBIGUITY = "reduce_ambiguity"
    IMPROVE_FORMAT = "improve_format"


class ABTestStatus(str, Enum):
    """Status of an A/B test."""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class Prompt:
    """A single prompt with versioning support."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    content: str = ""
    version: int = 1
    type: PromptType = PromptType.USER
    category: PromptCategory = PromptCategory.GENERAL
    tags: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    description: str = ""
    usage_count: int = 0
    avg_quality_score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PromptVersion:
    """A historical version of a prompt."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    prompt_id: str = ""
    version: int = 1
    content: str = ""
    changelog: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ABTest:
    """An A/B test comparing two prompt variants."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    prompt_a_id: str = ""
    prompt_b_id: str = ""
    status: ABTestStatus = ABTestStatus.DRAFT
    metric: str = "quality"
    results_a: dict[str, float] = field(default_factory=dict)
    results_b: dict[str, float] = field(default_factory=dict)
    winner: str = ""
    trials: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OptimizationResult:
    """Result of a prompt optimization attempt."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    original_prompt_id: str = ""
    optimized_prompt_id: str = ""
    strategy: OptimizationStrategy = OptimizationStrategy.SIMPLIFY
    improvement_score: float = 0.0
    changes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PromptChain:
    """A chain of prompts executed in sequence."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════
# Prompt Studio Engine
# ═══════════════════════════════════════════════════════════

class PromptStudio:
    """Prompt engineering, optimization, and management system.

    Provides tools for creating, versioning, testing, and optimizing
    prompts. Supports A/B testing, template management, and performance
    analytics for data-driven prompt engineering.
    """

    def __init__(self) -> None:
        self._prompts: dict[str, Prompt] = {}
        self._versions: dict[str, list[PromptVersion]] = defaultdict(list)
        self._ab_tests: dict[str, ABTest] = {}
        self._optimizations: list[OptimizationResult] = []
        self._chains: dict[str, PromptChain] = {}
        self._total_prompts: int = 0
        self._total_versions: int = 0
        self._total_tests: int = 0

        # Initialize library prompts
        self._init_library()

    def _init_library(self) -> None:
        """Initialize the prompt library with default prompts."""
        library = [
            {
                "name": "code_generation",
                "content": "You are a skilled software engineer. Write clean, well-documented code for the following task. Include error handling and follow best practices.",
                "type": PromptType.SYSTEM,
                "category": PromptCategory.CODING,
                "tags": ["code", "generation", "engineering"],
            },
            {
                "name": "text_summarization",
                "content": "Summarize the following text concisely. Focus on the key points and main conclusions. Keep the summary under {max_length} words.",
                "type": PromptType.USER,
                "category": PromptCategory.SUMMARIZATION,
                "variables": ["max_length"],
                "tags": ["summary", "text", "condense"],
            },
            {
                "name": "data_analysis",
                "content": "Analyze the following data and provide insights. Identify trends, patterns, and anomalies. Present findings in a structured format.",
                "type": PromptType.USER,
                "category": PromptCategory.ANALYSIS,
                "tags": ["data", "analysis", "insights"],
            },
            {
                "name": "reasoning_chain",
                "content": "Let's approach this problem step by step:\n1. First, understand the problem clearly\n2. Break it down into components\n3. Analyze each component\n4. Synthesize a solution\n5. Verify the solution",
                "type": PromptType.SYSTEM,
                "category": PromptCategory.REASONING,
                "tags": ["reasoning", "chain-of-thought", "problem-solving"],
            },
            {
                "name": "creative_writing",
                "content": "You are a creative writer. Write engaging, original content that captures the reader's attention. Use vivid language and maintain a consistent tone.",
                "type": PromptType.SYSTEM,
                "category": PromptCategory.CREATIVE,
                "tags": ["writing", "creative", "content"],
            },
            {
                "name": "classification",
                "content": "Classify the following input into one of the categories: {categories}. Provide your classification with a confidence score.",
                "type": PromptType.USER,
                "category": PromptCategory.CLASSIFICATION,
                "variables": ["categories"],
                "tags": ["classification", "categorize"],
            },
        ]

        for item in library:
            prompt = Prompt(
                name=item["name"],
                content=item["content"],
                type=item["type"],
                category=item["category"],
                tags=item.get("tags", []),
                variables=item.get("variables", []),
                description=item.get("description", ""),
            )
            self._prompts[prompt.id] = prompt
            self._total_prompts += 1

            # Create initial version
            version = PromptVersion(
                prompt_id=prompt.id,
                version=1,
                content=prompt.content,
                changelog="Initial version",
            )
            self._versions[prompt.id].append(version)
            self._total_versions += 1

    # ── Prompt CRUD ────────────────────────────────────────────────

    def create_prompt(
        self,
        name: str,
        content: str,
        type: PromptType = PromptType.USER,
        category: PromptCategory = PromptCategory.GENERAL,
        tags: list[str] | None = None,
        description: str = "",
    ) -> Prompt:
        """Create a new prompt.

        Args:
            name: Prompt name.
            content: Prompt content text.
            type: Prompt type.
            category: Prompt category.
            tags: Optional tags.
            description: Optional description.

        Returns:
            The created Prompt.
        """
        prompt = Prompt(
            name=name,
            content=content,
            type=type,
            category=category,
            tags=tags or [],
            description=description,
        )
        self._prompts[prompt.id] = prompt
        self._total_prompts += 1

        version = PromptVersion(
            prompt_id=prompt.id,
            version=1,
            content=content,
            changelog="Initial version",
        )
        self._versions[prompt.id].append(version)
        self._total_versions += 1

        logger.info("Prompt created: %s [%s]", name, category.value)
        return prompt

    def update_prompt(
        self,
        prompt_id: str,
        content: str,
        changelog: str = "",
    ) -> Prompt | None:
        """Update an existing prompt, creating a new version.

        Args:
            prompt_id: Prompt ID to update.
            content: New prompt content.
            changelog: Description of changes.

        Returns:
            The updated Prompt, or None if not found.
        """
        prompt = self._prompts.get(prompt_id)
        if not prompt:
            return None

        prompt.content = content
        prompt.version += 1
        prompt.updated_at = datetime.now(timezone.utc)

        version = PromptVersion(
            prompt_id=prompt_id,
            version=prompt.version,
            content=content,
            changelog=changelog,
        )
        self._versions[prompt_id].append(version)
        self._total_versions += 1

        logger.info("Prompt updated: %s v%d", prompt.name, prompt.version)
        return prompt

    def get_prompt(self, prompt_id: str) -> Prompt | None:
        """Get a prompt by ID."""
        return self._prompts.get(prompt_id)

    def list_prompts(
        self,
        category: PromptCategory | None = None,
        type: PromptType | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[Prompt]:
        """List prompts with optional filters.

        Args:
            category: Filter by category.
            type: Filter by type.
            tags: Filter by tags.
            limit: Maximum results.

        Returns:
            List of matching Prompt objects.
        """
        prompts = list(self._prompts.values())
        if category:
            prompts = [p for p in prompts if p.category == category]
        if type:
            prompts = [p for p in prompts if p.type == type]
        if tags:
            prompts = [p for p in prompts if any(t in p.tags for t in tags)]
        prompts.sort(key=lambda p: p.usage_count, reverse=True)
        return prompts[:limit]

    def get_versions(self, prompt_id: str) -> list[PromptVersion]:
        """Get version history for a prompt."""
        return self._versions.get(prompt_id, [])

    # ── Prompt Rendering ───────────────────────────────────────────

    def render(
        self,
        prompt_id: str,
        variables: dict[str, str] | None = None,
    ) -> str:
        """Render a prompt with variable substitution.

        Args:
            prompt_id: Prompt ID to render.
            variables: Variable values to substitute.

        Returns:
            Rendered prompt string.
        """
        prompt = self._prompts.get(prompt_id)
        if not prompt:
            return ""

        content = prompt.content
        vars_dict = variables or {}
        for var, val in vars_dict.items():
            content = content.replace(f"{{{var}}}", val)

        prompt.usage_count += 1
        return content

    # ── A/B Testing ────────────────────────────────────────────────

    def create_ab_test(
        self,
        name: str,
        prompt_a_id: str,
        prompt_b_id: str,
        metric: str = "quality",
    ) -> ABTest:
        """Create an A/B test between two prompt variants.

        Args:
            name: Test name.
            prompt_a_id: First prompt variant ID.
            prompt_b_id: Second prompt variant ID.
            metric: Metric to compare.

        Returns:
            The created ABTest.
        """
        test = ABTest(
            name=name,
            prompt_a_id=prompt_a_id,
            prompt_b_id=prompt_b_id,
            metric=metric,
        )
        self._ab_tests[test.id] = test
        self._total_tests += 1

        logger.info("A/B test created: %s", name)
        return test

    def run_ab_test(
        self,
        test_id: str,
        score_a: float,
        score_b: float,
    ) -> ABTest | None:
        """Run a trial of an A/B test with scores.

        Args:
            test_id: A/B test ID.
            score_a: Score for prompt variant A.
            score_b: Score for prompt variant B.

        Returns:
            The updated ABTest.
        """
        test = self._ab_tests.get(test_id)
        if not test:
            return None

        test.status = ABTestStatus.RUNNING
        test.trials += 1

        # Update running averages
        n = test.trials
        test.results_a["avg_score"] = (
            (test.results_a.get("avg_score", 0) * (n - 1) + score_a) / n
        )
        test.results_b["avg_score"] = (
            (test.results_b.get("avg_score", 0) * (n - 1) + score_b) / n
        )

        # Determine winner after sufficient trials
        if n >= 5:
            test.status = ABTestStatus.COMPLETED
            test.winner = (
                test.prompt_a_id
                if test.results_a.get("avg_score", 0) > test.results_b.get("avg_score", 0)
                else test.prompt_b_id
            )

        return test

    def complete_ab_test(self, test_id: str) -> ABTest | None:
        """Complete an A/B test and determine the winner.

        Args:
            test_id: A/B test ID.

        Returns:
            The completed ABTest.
        """
        test = self._ab_tests.get(test_id)
        if not test:
            return None

        test.status = ABTestStatus.COMPLETED
        test.winner = (
            test.prompt_a_id
            if test.results_a.get("avg_score", 0) > test.results_b.get("avg_score", 0)
            else test.prompt_b_id
        )
        return test

    # ── Prompt Optimization ────────────────────────────────────────

    def optimize(
        self,
        prompt_id: str,
        strategy: OptimizationStrategy = OptimizationStrategy.SIMPLIFY,
    ) -> OptimizationResult | None:
        """Optimize a prompt using the specified strategy.

        Args:
            prompt_id: Prompt ID to optimize.
            strategy: Optimization strategy to apply.

        Returns:
            OptimizationResult with the optimized prompt.
        """
        original = self._prompts.get(prompt_id)
        if not original:
            return None

        optimized_content = self._apply_optimization(original.content, strategy)

        # Create a new prompt version with the optimized content
        optimized = self.create_prompt(
            name=f"{original.name}_optimized",
            content=optimized_content,
            type=original.type,
            category=original.category,
            tags=original.tags + ["optimized"],
            description=f"Optimized from {original.name} using {strategy.value}",
        )

        result = OptimizationResult(
            original_prompt_id=prompt_id,
            optimized_prompt_id=optimized.id,
            strategy=strategy,
            improvement_score=0.15,
            changes=[f"Applied {strategy.value} optimization"],
        )
        self._optimizations.append(result)

        logger.info(
            "Prompt optimized: %s -> %s [%s]",
            original.name, optimized.name, strategy.value,
        )
        return result

    def _apply_optimization(self, content: str, strategy: OptimizationStrategy) -> str:
        """Internal: apply an optimization strategy to prompt content."""
        if strategy == OptimizationStrategy.SIMPLIFY:
            # Remove redundant words and shorten
            lines = content.split("\n")
            simplified = [l.strip() for l in lines if len(l.strip()) > 3]
            return "\n".join(simplified)
        elif strategy == OptimizationStrategy.ELABORATE:
            # Add more detail and structure
            return content + "\n\nProvide detailed explanations and examples where appropriate."
        elif strategy == OptimizationStrategy.RESTRUCTURE:
            # Reorganize with numbered steps
            return f"Follow these steps:\n1. {content}\n2. Verify your output\n3. Provide a summary"
        elif strategy == OptimizationStrategy.ADD_EXAMPLES:
            return content + "\n\nExample:\nInput: [example input]\nOutput: [expected output]"
        elif strategy == OptimizationStrategy.CLARIFY_INSTRUCTIONS:
            return content + "\n\nImportant: Be precise and specific. Avoid vague statements."
        elif strategy == OptimizationStrategy.REDUCE_AMBIGUITY:
            return content + "\n\nProvide exactly one answer. If multiple are possible, choose the most likely."
        elif strategy == OptimizationStrategy.IMPROVE_FORMAT:
            return f"## Instructions\n\n{content}\n\n## Output Format\n\nProvide output in the following format:\n- Key findings:\n- Recommendations:"
        return content

    # ── Prompt Chains ──────────────────────────────────────────────

    def create_chain(
        self,
        name: str,
        step_prompt_ids: list[str],
        description: str = "",
    ) -> PromptChain:
        """Create a chain of prompts for sequential execution.

        Args:
            name: Chain name.
            step_prompt_ids: Ordered list of prompt IDs.
            description: Chain description.

        Returns:
            The created PromptChain.
        """
        steps = []
        for i, pid in enumerate(step_prompt_ids):
            prompt = self._prompts.get(pid)
            steps.append({
                "order": i + 1,
                "prompt_id": pid,
                "prompt_name": prompt.name if prompt else "unknown",
            })

        chain = PromptChain(
            name=name,
            steps=steps,
            description=description,
        )
        self._chains[chain.id] = chain
        return chain

    def execute_chain(
        self,
        chain_id: str,
        initial_input: str,
        variables: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a prompt chain sequentially.

        Args:
            chain_id: Chain ID to execute.
            initial_input: Initial input for the first step.
            variables: Variable values for substitution.

        Returns:
            List of step results.
        """
        chain = self._chains.get(chain_id)
        if not chain:
            return []

        results = []
        current_input = initial_input

        for step in chain.steps:
            rendered = self.render(step["prompt_id"], variables)
            # Simulate execution
            result = {
                "step": step["order"],
                "prompt_name": step["prompt_name"],
                "input": current_input[:100],
                "output": f"Simulated output for step {step['order']}",
            }
            results.append(result)
            current_input = result["output"]

        return results

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get prompt studio statistics."""
        category_counts: dict[str, int] = defaultdict(int)
        type_counts: dict[str, int] = defaultdict(int)
        for p in self._prompts.values():
            category_counts[p.category.value] += 1
            type_counts[p.type.value] += 1

        return {
            "total_prompts": self._total_prompts,
            "total_versions": self._total_versions,
            "total_ab_tests": self._total_tests,
            "total_optimizations": len(self._optimizations),
            "total_chains": len(self._chains),
            "category_distribution": dict(category_counts),
            "type_distribution": dict(type_counts),
            "optimization_strategies": [s.value for s in OptimizationStrategy],
            "categories": [c.value for c in PromptCategory],
            "most_used_prompts": [
                {"name": p.name, "usage": p.usage_count}
                for p in sorted(
                    self._prompts.values(),
                    key=lambda x: x.usage_count, reverse=True
                )[:5]
            ],
        }

    def reset(self) -> None:
        """Reset all prompt studio state."""
        self._prompts.clear()
        self._versions.clear()
        self._ab_tests.clear()
        self._optimizations.clear()
        self._chains.clear()
        self._total_prompts = 0
        self._total_versions = 0
        self._total_tests = 0
        self._init_library()


# ═══════════════════════════════════════════════════════════
# Singleton Accessors
# ═══════════════════════════════════════════════════════════

_prompt_studio: PromptStudio | None = None


def get_prompt_studio() -> PromptStudio:
    """Get or create the singleton PromptStudio."""
    global _prompt_studio
    if _prompt_studio is None:
        _prompt_studio = PromptStudio()
    return _prompt_studio


def reset_prompt_studio() -> None:
    """Reset the singleton PromptStudio."""
    global _prompt_studio
    if _prompt_studio is not None:
        _prompt_studio.reset()
    _prompt_studio = None