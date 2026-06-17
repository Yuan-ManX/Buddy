"""Buddy Agent Intelligence Core — unified reasoning, tool orchestration, and learning

Provides the central intelligence layer for Buddy agents, integrating advanced
reasoning strategies, intelligent tool selection, memory-aware context building,
experience-driven learning, and adaptive strategy optimization.

Core capabilities:
  - Multi-Strategy Reasoning: CoT, ToT, self-consistency, contrastive, abductive
  - Intelligent Tool Selection: context-aware tool matching with relevance scoring
  - Memory-Augmented Generation: retrieve relevant memories for context enrichment
  - Experience Replay: learn from past interactions to improve future responses
  - Adaptive Strategy: dynamically select reasoning approach based on task analysis
  - Chain Optimization: merge redundant steps, parallelize independent operations
  - Confidence Calibration: assess and communicate uncertainty in responses
  - Skill Composition: dynamically compose skills for complex multi-step tasks
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("buddy.intelligence")


class IntelligenceMode(str, Enum):
    """Execution modes for the intelligence core."""
    REACTIVE = "reactive"          # Quick, single-pass response
    DELIBERATIVE = "deliberative"  # Multi-step reasoning with planning
    EXPLORATORY = "exploratory"    # Branch exploration with evaluation
    REFLECTIVE = "reflective"      # Self-critique and improvement
    COLLABORATIVE = "collaborative"  # Multi-agent perspective synthesis


class ReasoningStrategy(str, Enum):
    """Available reasoning strategies."""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    SELF_CONSISTENCY = "self_consistency"
    CONTRASTIVE = "contrastive"
    ABDUCTIVE = "abductive"
    DECOMPOSITION = "decomposition"
    REFLEXION = "reflexion"
    ANALOGICAL = "analogical"
    PARALLEL_BRANCHING = "parallel_branching"
    STEP_BACK = "step_back"


class OrchestrationPhase(str, Enum):
    """Phases in multi-strategy orchestration."""
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    ADAPTATION = "adaptation"


class TaskComplexity(str, Enum):
    """Task complexity classification."""
    TRIVIAL = "trivial"        # Single-step, well-defined
    SIMPLE = "simple"          # 2-3 steps, clear solution path
    MODERATE = "moderate"      # Multiple steps, requires planning
    COMPLEX = "complex"        # Multi-branch, needs exploration
    EXPERT = "expert"          # Requires deep domain knowledge


@dataclass
class IntelligenceConfig:
    """Configuration for the intelligence core."""
    max_reasoning_steps: int = 10
    max_parallel_branches: int = 5
    confidence_threshold: float = 0.7
    exploration_budget: int = 3
    memory_retrieval_limit: int = 10
    tool_selection_limit: int = 5
    experience_window: int = 50
    learning_rate: float = 0.1
    enable_self_critique: bool = True
    enable_experience_replay: bool = True
    enable_strategy_adaptation: bool = True
    # Adaptive tool selection
    epsilon: float = 0.15
    epsilon_decay: float = 0.995
    tool_score_decay: float = 0.9
    # Experience-driven learning
    max_lessons_per_pattern: int = 5
    # Reasoning chain validation
    validation_check_count: int = 3
    # Prompt optimization
    prompt_analysis_window: int = 30
    enable_prompt_optimization: bool = True
    # Uncertainty quantification
    uncertainty_methods: list[str] = field(default_factory=lambda: ["ensemble", "calibration", "consistency"])


@dataclass
class ThinkingStep:
    """A single step in the reasoning process."""
    id: str
    step_type: str  # observe, think, act, reflect, decide
    content: str
    confidence: float = 1.0
    alternatives: list[str] = field(default_factory=list)
    tool_calls: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ReasoningTrace:
    """Complete trace of a reasoning process."""
    id: str
    strategy: ReasoningStrategy
    mode: IntelligenceMode
    steps: list[ThinkingStep] = field(default_factory=list)
    final_answer: str = ""
    confidence: float = 0.0
    tools_used: list[str] = field(default_factory=list)
    memories_retrieved: int = 0
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""


@dataclass
class Experience:
    """A learned experience for future reference."""
    id: str
    task_pattern: str
    strategy_used: ReasoningStrategy
    outcome: str  # success, partial, failure
    confidence: float
    tools_used: list[str]
    duration_ms: float
    lessons: list[str] = field(default_factory=list)
    embeddings: list[float] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ToolRelevance:
    """Relevance score for a tool in context."""
    tool_name: str
    score: float
    reason: str
    required_params: dict = field(default_factory=dict)


@dataclass
class ToolEffectivenessScore:
    """Tracks effectiveness of a tool with decay-based scoring."""
    tool_name: str
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    last_used: str = ""
    composite_score: float = 0.5


@dataclass
class ModelPerformanceRecord:
    """Historical performance data for a model on a task type."""
    model_name: str
    task_pattern: str
    successes: int = 0
    failures: int = 0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    cost_estimate: float = 0.0


@dataclass
class ValidationResult:
    """Result of reasoning chain validation."""
    is_valid: bool
    logical_consistency_score: float
    completeness_score: float
    factual_grounding_score: float
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class PromptAnalysis:
    """Analysis of a prompt's effectiveness."""
    prompt_text: str
    effectiveness_score: float
    clarity_score: float
    specificity_score: float
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggested_rewrite: str = ""


@dataclass
class UncertaintyEstimate:
    """Multi-method uncertainty quantification result."""
    overall_uncertainty: float
    ensemble_variance: float
    calibration_error: float
    consistency_score: float
    confidence_interval: tuple[float, float]
    method_scores: dict = field(default_factory=dict)
    narrative: str = ""


class AgentIntelligence:
    """Central intelligence core for Buddy agents.

    Orchestrates reasoning, tool selection, memory retrieval, and learning
    to produce intelligent, context-aware responses. Adapts its strategy
    based on task complexity and historical performance.
    """

    def __init__(self, config: IntelligenceConfig | None = None):
        self.config = config or IntelligenceConfig()
        self._experiences: list[Experience] = []
        self._strategy_performance: dict[str, dict[str, float]] = defaultdict(
            lambda: {"successes": 0, "failures": 0, "avg_duration": 0.0}
        )
        self._tool_usage_stats: dict[str, dict] = defaultdict(
            lambda: {"calls": 0, "successes": 0, "avg_latency": 0.0}
        )
        self._task_patterns: dict[str, list[str]] = defaultdict(list)
        self._active_traces: dict[str, ReasoningTrace] = {}
        self._tool_effectiveness: dict[str, ToolEffectivenessScore] = {}
        self._model_performance: dict[str, dict[str, ModelPerformanceRecord]] = defaultdict(dict)
        self._prompt_history: list[PromptAnalysis] = []
        self._lessons_archive: dict[str, list[str]] = defaultdict(list)

    # ── Task Analysis ──────────────────────────────────────

    def analyze_task(self, prompt: str, available_tools: list[str] | None = None) -> dict:
        """Analyze a task to determine complexity, required tools, and best strategy."""
        prompt_lower = prompt.lower()
        length = len(prompt)

        # Complexity heuristics
        complexity_signals = {
            "explain": TaskComplexity.MODERATE,
            "analyze": TaskComplexity.COMPLEX,
            "compare": TaskComplexity.MODERATE,
            "design": TaskComplexity.COMPLEX,
            "debug": TaskComplexity.MODERATE,
            "optimize": TaskComplexity.COMPLEX,
            "research": TaskComplexity.EXPERT,
            "implement": TaskComplexity.COMPLEX,
            "refactor": TaskComplexity.MODERATE,
            "summarize": TaskComplexity.SIMPLE,
            "translate": TaskComplexity.SIMPLE,
            "calculate": TaskComplexity.SIMPLE,
        }

        complexity = TaskComplexity.SIMPLE
        for keyword, level in complexity_signals.items():
            if keyword in prompt_lower:
                complexity = level
                break

        if length > 1000:
            complexity = min(TaskComplexity.COMPLEX, complexity)
        if "step by step" in prompt_lower or "detailed" in prompt_lower:
            complexity = TaskComplexity.COMPLEX

        # Strategy selection
        strategy_map = {
            TaskComplexity.TRIVIAL: ReasoningStrategy.CHAIN_OF_THOUGHT,
            TaskComplexity.SIMPLE: ReasoningStrategy.CHAIN_OF_THOUGHT,
            TaskComplexity.MODERATE: ReasoningStrategy.DECOMPOSITION,
            TaskComplexity.COMPLEX: ReasoningStrategy.TREE_OF_THOUGHT,
            TaskComplexity.EXPERT: ReasoningStrategy.SELF_CONSISTENCY,
        }

        # Adapt based on past performance
        strategy = strategy_map.get(complexity, ReasoningStrategy.CHAIN_OF_THOUGHT)
        if self.config.enable_strategy_adaptation:
            strategy = self._adapt_strategy(complexity, strategy, prompt_lower)

        # Tool relevance
        relevant_tools = []
        if available_tools:
            relevant_tools = self._score_tool_relevance(prompt_lower, available_tools)

        return {
            "complexity": complexity.value,
            "recommended_strategy": strategy.value,
            "relevant_tools": [
                {"name": t.tool_name, "score": t.score, "reason": t.reason}
                for t in relevant_tools[:self.config.tool_selection_limit]
            ],
            "mode": self._select_mode(complexity).value,
            "estimated_steps": self._estimate_steps(complexity),
        }

    def _select_mode(self, complexity: TaskComplexity) -> IntelligenceMode:
        """Select the appropriate intelligence mode."""
        mode_map = {
            TaskComplexity.TRIVIAL: IntelligenceMode.REACTIVE,
            TaskComplexity.SIMPLE: IntelligenceMode.REACTIVE,
            TaskComplexity.MODERATE: IntelligenceMode.DELIBERATIVE,
            TaskComplexity.COMPLEX: IntelligenceMode.EXPLORATORY,
            TaskComplexity.EXPERT: IntelligenceMode.REFLECTIVE,
        }
        return mode_map.get(complexity, IntelligenceMode.DELIBERATIVE)

    def _estimate_steps(self, complexity: TaskComplexity) -> int:
        """Estimate the number of reasoning steps needed."""
        estimates = {
            TaskComplexity.TRIVIAL: 1,
            TaskComplexity.SIMPLE: 3,
            TaskComplexity.MODERATE: 5,
            TaskComplexity.COMPLEX: 8,
            TaskComplexity.EXPERT: 10,
        }
        return min(estimates.get(complexity, 3), self.config.max_reasoning_steps)

    # ── Tool Intelligence ──────────────────────────────────

    def _score_tool_relevance(self, prompt: str, tools: list[str]) -> list[ToolRelevance]:
        """Score tools by relevance to the current task context."""
        relevance_keywords = {
            "search": ["search", "find", "lookup", "query", "google"],
            "read_file": ["read", "file", "open", "view", "check"],
            "write_file": ["write", "create", "save", "generate file"],
            "execute_code": ["run", "execute", "code", "python", "script", "compute"],
            "web_fetch": ["fetch", "url", "website", "http", "download", "scrape"],
            "memory_search": ["remember", "recall", "memory", "past", "history"],
            "summarize": ["summary", "summarize", "brief", "overview"],
            "analyze_data": ["analyze", "data", "statistics", "chart", "graph"],
            "send_message": ["send", "message", "email", "notify"],
            "schedule": ["schedule", "remind", "calendar", "plan"],
        }

        scored = []
        for tool in tools:
            score = 0.0
            reason = "general purpose"
            keywords = relevance_keywords.get(tool, [tool.lower()])
            for kw in keywords:
                if kw in prompt:
                    score += 0.3
                    reason = f"matched keyword: {kw}"
            scored.append(ToolRelevance(tool_name=tool, score=min(score, 1.0), reason=reason))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def select_tools(self, prompt: str, available_tools: list, limit: int = 5) -> list:
        """Intelligently select the most relevant tools for a task."""
        tool_names = [t.name if hasattr(t, 'name') else t.get("name", t.get("function", {}).get("name", "")) for t in available_tools]
        relevance = self._score_tool_relevance(prompt.lower(), tool_names)
        selected_names = {r.tool_name for r in relevance if r.score > 0.0}
        selected_names_list = [r.tool_name for r in relevance if r.score > 0.0][:limit]
        # Return the actual tool objects, preserving order of relevance
        result = []
        for name in selected_names_list:
            for t in available_tools:
                t_name = t.name if hasattr(t, 'name') else t.get("name", t.get("function", {}).get("name", ""))
                if t_name == name:
                    result.append(t)
                    break
        return result

    def plan_tool_sequence(self, task: str, tools: list[str]) -> list[list[str]]:
        """Plan an optimal tool execution sequence for a task.

        Returns a list of steps, where each step is a list of tools
        that can run in parallel within that step.
        """
        task_lower = task.lower()

        # Detect task patterns for sequencing
        if any(kw in task_lower for kw in ["research", "investigate", "explore"]):
            return [["search", "web_fetch"], ["read_file", "memory_search"], ["analyze_data"], ["summarize"]]
        if any(kw in task_lower for kw in ["code", "implement", "develop", "build"]):
            return [["read_file"], ["search", "memory_search"], ["write_file", "execute_code"], ["execute_code"]]
        if any(kw in task_lower for kw in ["debug", "fix", "error", "bug"]):
            return [["read_file"], ["execute_code", "search"], ["analyze_data"], ["write_file"]]
        if any(kw in task_lower for kw in ["analyze", "review", "audit"]):
            return [["read_file", "search"], ["analyze_data", "memory_search"], ["summarize"]]

        return [["search", "memory_search"], ["analyze_data"]]

    # ── Strategy Adaptation ────────────────────────────────

    def _adapt_strategy(self, complexity: TaskComplexity, default: ReasoningStrategy, prompt: str) -> ReasoningStrategy:
        """Adapt strategy based on past performance on similar tasks."""
        similar_experiences = self._find_similar_experiences(prompt)
        if not similar_experiences:
            return default

        # Check which strategies worked best
        strategy_scores: dict[str, list[float]] = defaultdict(list)
        for exp in similar_experiences:
            key = exp.strategy_used.value
            score = 1.0 if exp.outcome == "success" else (0.5 if exp.outcome == "partial" else 0.0)
            strategy_scores[key].append(score)

        if not strategy_scores:
            return default

        # Find best strategy
        best_avg = 0.0
        best_strategy = default
        for strat_key, scores in strategy_scores.items():
            avg = sum(scores) / len(scores)
            if avg > best_avg:
                best_avg = avg
                try:
                    best_strategy = ReasoningStrategy(strat_key)
                except ValueError:
                    pass

        # Only switch if significantly better
        if best_avg > 0.7 and best_strategy != default:
            logger.debug(f"Strategy adapted: {default.value} -> {best_strategy.value} (score: {best_avg:.2f})")
            return best_strategy

        return default

    # ── Experience Management ──────────────────────────────

    def record_experience(self, task: str, strategy: ReasoningStrategy, outcome: str,
                          confidence: float, tools: list[str], duration_ms: float,
                          lessons: list[str] | None = None):
        """Record an experience for future learning."""
        exp = Experience(
            id=f"exp-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            task_pattern=self._extract_task_pattern(task),
            strategy_used=strategy,
            outcome=outcome,
            confidence=confidence,
            tools_used=tools,
            duration_ms=duration_ms,
            lessons=lessons or [],
        )
        self._experiences.append(exp)

        # Update strategy performance
        perf = self._strategy_performance[strategy.value]
        perf["avg_duration"] = (perf["avg_duration"] * (perf["successes"] + perf["failures"]) + duration_ms) / \
                               (perf["successes"] + perf["failures"] + 1)
        if outcome == "success":
            perf["successes"] += 1
        else:
            perf["failures"] += 1

        # Maintain experience window
        if len(self._experiences) > self.config.experience_window * 3:
            self._experiences = self._experiences[-self.config.experience_window:]

        # Update task patterns
        pattern = self._extract_task_pattern(task)
        self._task_patterns[pattern].append(strategy.value)

        logger.debug(f"Recorded experience: {outcome} using {strategy.value}")

    def _find_similar_experiences(self, task: str) -> list[Experience]:
        """Find experiences similar to the current task."""
        pattern = self._extract_task_pattern(task)
        similar = []
        for exp in self._experiences:
            if self._pattern_similarity(pattern, exp.task_pattern) > 0.3:
                similar.append(exp)
        return similar[-self.config.experience_window:]

    def _extract_task_pattern(self, task: str) -> str:
        """Extract a general pattern from a task description."""
        task_lower = task.lower()
        patterns = {
            "code_generation": ["write", "create", "implement", "code", "function", "class"],
            "debugging": ["debug", "fix", "error", "bug", "issue", "problem"],
            "analysis": ["analyze", "review", "examine", "investigate", "study"],
            "explanation": ["explain", "describe", "what is", "how does", "tell me about"],
            "summarization": ["summarize", "summary", "brief", "overview", "tldr"],
            "translation": ["translate", "convert to", "in english", "in chinese"],
            "planning": ["plan", "strategy", "roadmap", "steps", "approach"],
            "research": ["research", "find information", "latest", "news about"],
        }
        for pattern_name, keywords in patterns.items():
            if any(kw in task_lower for kw in keywords):
                return pattern_name
        return "general"

    @staticmethod
    def _pattern_similarity(p1: str, p2: str) -> float:
        """Compute similarity between two task patterns."""
        if p1 == p2:
            return 1.0
        # Simple overlap heuristic
        words1 = set(p1.split("_"))
        words2 = set(p2.split("_"))
        if not words1 or not words2:
            return 0.0
        overlap = len(words1 & words2)
        return overlap / max(len(words1), len(words2))

    # ── Reasoning Trace Management ─────────────────────────

    def start_trace(self, strategy: ReasoningStrategy, mode: IntelligenceMode) -> str:
        """Start a new reasoning trace."""
        trace = ReasoningTrace(
            id=f"trace-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            strategy=strategy,
            mode=mode,
        )
        self._active_traces[trace.id] = trace
        return trace.id

    def add_think_step(self, trace_id: str, content: str, step_type: str = "think",
                       confidence: float = 1.0, tool_calls: list[str] | None = None):
        """Add a thinking step to a reasoning trace."""
        trace = self._active_traces.get(trace_id)
        if not trace:
            return
        step = ThinkingStep(
            id=f"step-{len(trace.steps) + 1}",
            step_type=step_type,
            content=content,
            confidence=confidence,
            tool_calls=tool_calls or [],
        )
        trace.steps.append(step)

    def complete_trace(self, trace_id: str, answer: str, confidence: float,
                       success: bool = True, error: str = ""):
        """Complete a reasoning trace with the final answer."""
        trace = self._active_traces.pop(trace_id, None)
        if not trace:
            return
        trace.final_answer = answer
        trace.confidence = confidence
        trace.success = success
        trace.error = error
        # Calculate duration from first to last step
        if trace.steps:
            start = datetime.fromisoformat(trace.steps[0].timestamp)
            end = datetime.fromisoformat(trace.steps[-1].timestamp)
            trace.duration_ms = (end - start).total_seconds() * 1000
        return trace

    # ── Confidence Calibration ─────────────────────────────

    def calibrate_confidence(self, answer: str, reasoning_steps: list[dict],
                             tool_results: list[dict] | None = None) -> float:
        """Calibrate the confidence level of a response."""
        confidence = 0.5  # Start neutral

        # Step count signal: more steps = more thorough
        if len(reasoning_steps) >= 5:
            confidence += 0.1
        if len(reasoning_steps) >= 8:
            confidence += 0.05

        # Tool usage signal: using tools increases confidence
        if tool_results:
            success_rate = sum(1 for t in tool_results if not t.get("error")) / max(len(tool_results), 1)
            confidence += success_rate * 0.15

        # Answer length signal
        if len(answer) > 200:
            confidence += 0.05
        if len(answer) > 500:
            confidence += 0.05

        # Uncertainty markers
        uncertainty_words = ["might", "maybe", "possibly", "uncertain", "not sure", "could be"]
        uncertainty_count = sum(1 for w in uncertainty_words if w in answer.lower())
        confidence -= min(uncertainty_count * 0.05, 0.2)

        return min(max(confidence, 0.1), 1.0)

    # ── Experience Replay & Learning ───────────────────────

    def replay_experiences(self, limit: int = 10) -> list[dict]:
        """Replay recent experiences for learning consolidation."""
        recent = self._experiences[-limit:]
        insights = []
        for exp in recent:
            if exp.lessons:
                insights.append({
                    "pattern": exp.task_pattern,
                    "strategy": exp.strategy_used.value,
                    "outcome": exp.outcome,
                    "lessons": exp.lessons,
                })
        return insights

    def get_learning_insights(self) -> dict:
        """Get insights from accumulated experiences."""
        total = len(self._experiences)
        if total == 0:
            return {"total_experiences": 0, "insights": []}

        successes = sum(1 for e in self._experiences if e.outcome == "success")
        success_rate = successes / total

        # Best strategies
        strategy_effectiveness = {}
        for key, perf in self._strategy_performance.items():
            total_attempts = perf["successes"] + perf["failures"]
            if total_attempts > 0:
                strategy_effectiveness[key] = {
                    "success_rate": perf["successes"] / total_attempts,
                    "avg_duration": round(perf["avg_duration"], 1),
                    "attempts": total_attempts,
                }

        return {
            "total_experiences": total,
            "overall_success_rate": round(success_rate, 3),
            "strategy_effectiveness": strategy_effectiveness,
            "recent_lessons": self._get_recent_lessons(),
        }

    def _get_recent_lessons(self) -> list[str]:
        """Aggregate recent lessons learned."""
        lessons = []
        for exp in self._experiences[-20:]:
            lessons.extend(exp.lessons)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for lesson in lessons:
            if lesson not in seen:
                seen.add(lesson)
                unique.append(lesson)
        return unique[-10:]

    # ── Tool Chain Optimization ────────────────────────────

    def optimize_tool_chain(self, tool_sequence: list[dict]) -> list[dict]:
        """Optimize a tool execution sequence by merging and parallelizing."""
        if len(tool_sequence) <= 1:
            return tool_sequence

        optimized = []
        i = 0
        while i < len(tool_sequence):
            current = tool_sequence[i]
            # Check if next tool can run in parallel
            if i + 1 < len(tool_sequence):
                next_tool = tool_sequence[i + 1]
                if self._can_parallelize(current, next_tool):
                    # Merge into parallel group
                    if isinstance(current, dict) and "parallel_group" not in current:
                        current = {"parallel_group": [current, next_tool]}
                    elif isinstance(current, dict) and "parallel_group" in current:
                        current["parallel_group"].append(next_tool)
                    i += 1
            optimized.append(current)
            i += 1

        return optimized

    @staticmethod
    def _can_parallelize(tool_a: dict, tool_b: dict) -> bool:
        """Check if two tool calls can run in parallel."""
        # Read-only operations can parallelize
        read_ops = {"search", "read_file", "web_fetch", "memory_search", "get"}
        name_a = tool_a.get("name", tool_a.get("function", {}).get("name", ""))
        name_b = tool_b.get("name", tool_b.get("function", {}).get("name", ""))
        return name_a in read_ops and name_b in read_ops

    # ── Statistics ─────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get intelligence core statistics."""
        total = len(self._experiences)
        successes = sum(1 for e in self._experiences if e.outcome == "success")
        return {
            "total_experiences": total,
            "success_rate": round(successes / max(total, 1), 3),
            "active_traces": len(self._active_traces),
            "task_patterns": {k: len(v) for k, v in self._task_patterns.items()},
            "strategies": {
                k: {"successes": v["successes"], "failures": v["failures"]}
                for k, v in self._strategy_performance.items()
            },
            "tools_tracked": len(self._tool_usage_stats),
        }

    # ── Multi-Strategy Reasoning Orchestrator ───────────────

    def dispatch_reasoning_strategy(self, task: str, context: dict | None = None) -> dict:
        """Unified dispatcher that selects and prepares a reasoning strategy.

        Analyzes task characteristics to dynamically choose from tree-of-thought,
        chain-of-thought, self-consistency, parallel-branching, or step-back
        strategies based on task structure, ambiguity, and multi-perspective needs.
        """
        chars = self._analyze_task_characteristics(task)
        strategy = self._select_orchestration_strategy(chars)

        plan = {
            "strategy": strategy.value,
            "characteristics": chars,
            "estimated_steps": chars.get("estimated_steps", 3),
            "branch_count": chars.get("recommended_branches", 1),
            "requires_decomposition": chars.get("requires_decomposition", False),
            "requires_multi_perspective": chars.get("requires_multi_perspective", False),
            "requires_abstraction": chars.get("requires_abstraction", False),
            "phase": OrchestrationPhase.PLANNING.value,
        }

        if strategy == ReasoningStrategy.TREE_OF_THOUGHT:
            plan["branch_plan"] = self._build_tree_of_thought_plan(task, context or {})
        elif strategy == ReasoningStrategy.PARALLEL_BRANCHING:
            plan["branch_plan"] = self._build_parallel_branching_plan(task, context or {})
        elif strategy == ReasoningStrategy.STEP_BACK:
            plan["step_back_plan"] = self._build_step_back_plan(task, context or {})
        elif strategy == ReasoningStrategy.SELF_CONSISTENCY:
            plan["consistency_samples"] = chars.get("recommended_branches", 3)
        elif strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
            plan["cot_template"] = self._build_chain_of_thought_template(task)

        logger.debug(
            "Reasoning dispatched: strategy=%s, steps=%d, branches=%d",
            strategy.value, plan["estimated_steps"], plan["branch_count"]
        )
        return plan

    def _analyze_task_characteristics(self, task: str) -> dict:
        """Analyze task characteristics for strategy selection."""
        task_lower = task.lower()
        length = len(task)

        structural_signals = {
            "requires_decomposition": any(kw in task_lower for kw in [
                "multiple", "several", "various", "steps", "stages", "phases",
                "break down", "decompose", "first", "then", "finally",
            ]),
            "requires_multi_perspective": any(kw in task_lower for kw in [
                "compare", "versus", "vs", "trade-off", "tradeoff", "pros and cons",
                "alternatives", "different perspectives", "both sides",
            ]),
            "requires_abstraction": any(kw in task_lower for kw in [
                "principle", "concept", "theory", "pattern", "fundamental",
                "underlying", "abstract", "generalize", "why", "reason",
            ]),
            "high_ambiguity": any(kw in task_lower for kw in [
                "maybe", "possibly", "uncertain", "unclear", "ambiguous",
                "best", "optimal", "ideal", "appropriate",
            ]),
            "time_sensitive": any(kw in task_lower for kw in [
                "quick", "fast", "urgent", "immediately", "asap",
            ]),
        }

        # Estimate recommended branches
        branch_count = 1
        if structural_signals["requires_multi_perspective"]:
            branch_count = max(branch_count, 3)
        if structural_signals["high_ambiguity"]:
            branch_count = max(branch_count, 2)
        if length > 800:
            branch_count = max(branch_count, 2)
        branch_count = min(branch_count, self.config.max_parallel_branches)

        # Estimate steps
        step_signals = sum(1 for v in structural_signals.values() if v)
        estimated_steps = min(2 + step_signals * 2, self.config.max_reasoning_steps)

        return {
            "task_length": length,
            "estimated_steps": estimated_steps,
            "recommended_branches": branch_count,
            **structural_signals,
        }

    def _select_orchestration_strategy(self, chars: dict) -> ReasoningStrategy:
        """Select the best reasoning strategy based on task characteristics."""
        if chars.get("requires_abstraction") and chars.get("requires_multi_perspective"):
            return ReasoningStrategy.STEP_BACK
        if chars.get("requires_multi_perspective") and chars.get("recommended_branches", 1) >= 3:
            return ReasoningStrategy.PARALLEL_BRANCHING
        if chars.get("high_ambiguity") or chars.get("recommended_branches", 1) >= 2:
            return ReasoningStrategy.TREE_OF_THOUGHT
        if chars.get("requires_multi_perspective") and chars.get("task_length", 0) > 400:
            return ReasoningStrategy.SELF_CONSISTENCY
        if chars.get("time_sensitive"):
            return ReasoningStrategy.CHAIN_OF_THOUGHT
        if chars.get("requires_decomposition"):
            return ReasoningStrategy.DECOMPOSITION
        return ReasoningStrategy.CHAIN_OF_THOUGHT

    def _build_tree_of_thought_plan(self, task: str, context: dict) -> list[dict]:
        """Build a tree-of-thought branching plan."""
        task_lower = task.lower()
        # Identify natural branching dimensions
        branches = []
        if "compare" in task_lower or "versus" in task_lower or "vs" in task_lower:
            branches = [
                {"branch": "option_a", "focus": "Analyze first option thoroughly"},
                {"branch": "option_b", "focus": "Analyze second option thoroughly"},
                {"branch": "synthesis", "focus": "Synthesize findings and compare"},
            ]
        elif "design" in task_lower or "architecture" in task_lower:
            branches = [
                {"branch": "requirements", "focus": "Extract and clarify requirements"},
                {"branch": "approach_1", "focus": "Explore first design approach"},
                {"branch": "approach_2", "focus": "Explore alternative design approach"},
                {"branch": "evaluation", "focus": "Evaluate and select best approach"},
            ]
        else:
            branches = [
                {"branch": "explore_1", "focus": "Explore primary solution path"},
                {"branch": "explore_2", "focus": "Explore alternative path"},
                {"branch": "evaluate", "focus": "Compare and select best result"},
            ]
        return branches

    def _build_parallel_branching_plan(self, task: str, context: dict) -> list[dict]:
        """Build a parallel-branching execution plan for independent sub-problems."""
        task_lower = task.lower()
        if "trade" in task_lower or "pros and cons" in task_lower:
            return [
                {"branch": "pros", "focus": "Identify all advantages and benefits"},
                {"branch": "cons", "focus": "Identify all disadvantages and risks"},
                {"branch": "neutral", "focus": "Identify neutral or contextual factors"},
            ]
        if "compare" in task_lower:
            return [
                {"branch": "entity_a", "focus": "Deep analysis of first entity"},
                {"branch": "entity_b", "focus": "Deep analysis of second entity"},
                {"branch": "diff", "focus": "Direct comparison and contrast"},
            ]
        return [
            {"branch": "aspect_1", "focus": "Analyze from first dimension"},
            {"branch": "aspect_2", "focus": "Analyze from second dimension"},
            {"branch": "aspect_3", "focus": "Analyze from third dimension"},
        ]

    def _build_step_back_plan(self, task: str, context: dict) -> dict:
        """Build a step-back reasoning plan that abstracts before diving in."""
        return {
            "step_1": "Identify the core principle or concept behind this question",
            "step_2": "Formulate the question at a higher level of abstraction",
            "step_3": "Reason about the abstracted problem using first principles",
            "step_4": "Map the abstract solution back to the concrete question",
            "step_5": "Validate the solution against the original context",
        }

    def _build_chain_of_thought_template(self, task: str) -> list[str]:
        """Build a chain-of-thought reasoning template."""
        return [
            "Understand the question and identify what is being asked",
            "Break down into logical sub-steps",
            "Reason through each sub-step sequentially",
            "Verify intermediate conclusions",
            "Synthesize final answer",
        ]

    # ── Adaptive Tool Selection ─────────────────────────────

    def update_tool_effectiveness(self, tool_name: str, success: bool, latency_ms: float = 0.0):
        """Update tool effectiveness score based on execution outcome.

        Uses decay-based scoring where recent outcomes carry more weight,
        similar to a moving average with exponential decay.
        """
        if tool_name not in self._tool_effectiveness:
            self._tool_effectiveness[tool_name] = ToolEffectivenessScore(tool_name=tool_name)

        score = self._tool_effectiveness[tool_name]
        decay = self.config.tool_score_decay

        if success:
            score.success_count += 1
        else:
            score.failure_count += 1

        total = score.success_count + score.failure_count
        raw_success_rate = score.success_count / max(total, 1)

        # Update latency with decay
        if latency_ms > 0:
            score.avg_latency_ms = (
                score.avg_latency_ms * decay + latency_ms * (1 - decay)
            )

        # Composite score: success rate weighted by recency, penalized by latency
        latency_penalty = min(score.avg_latency_ms / 5000.0, 0.3) if score.avg_latency_ms > 0 else 0.0
        score.composite_score = max(0.0, raw_success_rate - latency_penalty)
        score.last_used = datetime.now(timezone.utc).isoformat()

        logger.debug(
            "Tool effectiveness updated: %s score=%.3f (successes=%d, failures=%d)",
            tool_name, score.composite_score, score.success_count, score.failure_count
        )

    def select_tools_adaptive(self, prompt: str, available_tools: list, limit: int = 5) -> list:
        """Select tools using RL-like exploration vs exploitation balancing.

        Balances between trying less-used tools (exploration) and picking
        the historically best-performing tools (exploitation) using an
        epsilon-greedy strategy with decay.
        """
        # Normalize to tool name strings
        def _extract_name(t):
            if isinstance(t, str):
                return t
            if hasattr(t, 'name'):
                return t.name
            if isinstance(t, dict):
                return t.get("name", t.get("function", {}).get("name", ""))
            return str(t)

        tool_names = [_extract_name(t) for t in available_tools]

        import random
        epsilon = self.config.epsilon

        # Decay epsilon over time based on experience count
        total_exp = len(self._experiences)
        if total_exp > 0:
            epsilon = self.config.epsilon * (self.config.epsilon_decay ** total_exp)

        selected_names: list[str] = []

        # Compute exploitation scores for all known tools
        exploitation_scores: dict[str, float] = {}
        for name in tool_names:
            exploitation_scores[name] = self._compute_tool_exploitation_score(name, prompt.lower())

        # Sort by exploitation score descending
        sorted_by_score = sorted(exploitation_scores.items(), key=lambda x: x[1], reverse=True)

        # Epsilon-greedy selection
        for i in range(min(limit, len(tool_names))):
            if random.random() < epsilon and i < len(tool_names) - len(selected_names):
                # Exploration: pick randomly from remaining tools
                remaining = [n for n in tool_names if n not in selected_names]
                if remaining:
                    pick = random.choice(remaining)
                    selected_names.append(pick)
            else:
                # Exploitation: pick best remaining
                for name, _ in sorted_by_score:
                    if name not in selected_names:
                        selected_names.append(name)
                        break

        logger.debug(
            "Adaptive tool selection: epsilon=%.3f, selected=%s",
            epsilon, selected_names
        )
        return selected_names

    def _compute_tool_exploitation_score(self, tool_name: str, prompt: str) -> float:
        """Compute exploitation score combining historical effectiveness and relevance."""
        effectiveness = self._tool_effectiveness.get(tool_name)
        historical_score = effectiveness.composite_score if effectiveness else 0.5

        # Relevance score using existing keyword matching
        relevance_keywords = {
            "search": ["search", "find", "lookup", "query", "google"],
            "read_file": ["read", "file", "open", "view", "check"],
            "write_file": ["write", "create", "save", "generate file"],
            "execute_code": ["run", "execute", "code", "python", "script", "compute"],
            "web_fetch": ["fetch", "url", "website", "http", "download", "scrape"],
            "memory_search": ["remember", "recall", "memory", "past", "history"],
            "summarize": ["summary", "summarize", "brief", "overview"],
            "analyze_data": ["analyze", "data", "statistics", "chart", "graph"],
            "send_message": ["send", "message", "email", "notify"],
            "schedule": ["schedule", "remind", "calendar", "plan"],
        }

        relevance = 0.0
        keywords = relevance_keywords.get(tool_name, [tool_name.lower()])
        for kw in keywords:
            if kw in prompt:
                relevance += 0.25
        relevance = min(relevance, 1.0)

        # Blend with config learning rate (treat as interpolation factor)
        return historical_score * (1 - self.config.learning_rate) + relevance * self.config.learning_rate

    # ── Experience-Driven Learning ─────────────────────────

    def distill_lessons(self, pattern_filter: str | None = None, limit: int = 10) -> list[dict]:
        """Distill execution experiences into compact lessons learned.

        Extracts patterns from both successes and failures, creating
        actionable guidance for future task execution.
        """
        experiences = self._experiences
        if pattern_filter:
            experiences = [e for e in experiences if e.task_pattern == pattern_filter]
        if not experiences:
            return []

        successes = [e for e in experiences if e.outcome == "success"]
        failures = [e for e in experiences if e.outcome == "failure"]

        lessons = []

        # Extract success patterns
        success_lessons = self._extract_success_patterns(successes)
        for lesson in success_lessons[:limit]:
            lessons.append({"type": "success_pattern", "lesson": lesson, "confidence": 0.8})

        # Extract failure patterns
        failure_lessons = self._extract_failure_patterns(failures)
        for lesson in failure_lessons[:limit]:
            lessons.append({"type": "failure_avoidance", "lesson": lesson, "confidence": 0.7})

        # Archive lessons by pattern
        pattern = pattern_filter or "general"
        for item in lessons:
            if item["lesson"] not in self._lessons_archive[pattern]:
                self._lessons_archive[pattern].append(item["lesson"])
        # Trim archive
        if len(self._lessons_archive[pattern]) > self.config.max_lessons_per_pattern * 2:
            self._lessons_archive[pattern] = self._lessons_archive[pattern][-self.config.max_lessons_per_pattern:]

        logger.debug("Distilled %d lessons for pattern '%s'", len(lessons), pattern)
        return lessons

    def _extract_success_patterns(self, successes: list[Experience]) -> list[str]:
        """Extract common patterns from successful experiences."""
        if not successes:
            return ["No successful experiences to learn from yet."]

        patterns = []
        # Strategy that leads to success
        strategy_counts: dict[str, int] = defaultdict(int)
        tool_combos: dict[str, int] = defaultdict(int)
        for exp in successes:
            strategy_counts[exp.strategy_used.value] += 1
            combo = "+".join(sorted(exp.tools_used)) if exp.tools_used else "none"
            tool_combos[combo] += 1

        # Most successful strategy
        if strategy_counts:
            best_strategy = max(strategy_counts, key=lambda k: strategy_counts[k])
            patterns.append(f"Strategy '{best_strategy}' works well for this task type "
                          f"(successful in {strategy_counts[best_strategy]}/{len(successes)} similar tasks)")

        # Most effective tool combination
        if tool_combos:
            best_combo = max(tool_combos, key=lambda k: tool_combos[k])
            if best_combo != "none" and tool_combos[best_combo] >= 2:
                patterns.append(f"Tool combination [{best_combo}] leads to consistent success")

        # High-confidence threshold learned
        high_conf = [e for e in successes if e.confidence > 0.8]
        if len(high_conf) > len(successes) * 0.5:
            patterns.append("Tasks of this type can be solved with high confidence")

        if not patterns:
            patterns.append("Success achieved with varied approaches; adaptability is key")

        return patterns

    def _extract_failure_patterns(self, failures: list[Experience]) -> list[str]:
        """Extract common patterns from failed experiences."""
        if not failures:
            return ["No failure data available for pattern extraction."]

        patterns = []
        strategy_counts: dict[str, int] = defaultdict(int)
        for exp in failures:
            strategy_counts[exp.strategy_used.value] += 1

        if strategy_counts:
            worst_strategy = max(strategy_counts, key=lambda k: strategy_counts[k])
            if strategy_counts[worst_strategy] >= 2:
                patterns.append(f"Avoid using '{worst_strategy}' for this task type "
                              f"(failed in {strategy_counts[worst_strategy]}/{len(failures)} similar tasks)")

        # Low-confidence failures
        low_conf = [e for e in failures if e.confidence < 0.5]
        if len(low_conf) > len(failures) * 0.5:
            patterns.append("Low-confidence responses often indicate task misunderstanding; "
                          "request clarification before proceeding")

        # Long-duration failures
        slow_failures = [e for e in failures if e.duration_ms > 10000]
        if slow_failures:
            patterns.append(f"Excessively long execution ({len(slow_failures)} cases) correlates with failure; "
                          "consider timeouts or early termination checks")

        if not patterns:
            patterns.append("Failures are varied; review each case individually")

        return patterns

    def get_lessons_for_pattern(self, pattern: str) -> list[str]:
        """Retrieve archived lessons for a specific task pattern."""
        return self._lessons_archive.get(pattern, [])

    # ── Context-Aware Model Selection ──────────────────────

    def select_model(self, task_complexity: str, task_pattern: str = "general",
                     budget_limit: float | None = None,
                     preferred_providers: list[str] | None = None) -> dict:
        """Select the optimal model based on task complexity, budget, and history.

        Evaluates model candidates considering task complexity requirements,
        cost budget, historical performance on similar tasks, and provider
        preferences to recommend the best model for the given task.
        """
        # Model catalog with capability and cost profiles
        model_catalog = {
            "gpt-4o": {
                "complexity_support": ["trivial", "simple", "moderate", "complex", "expert"],
                "cost_per_1k_tokens": 0.005,
                "typical_latency_ms": 800,
                "provider": "openai",
                "strengths": ["reasoning", "code", "creative"],
            },
            "gpt-4o-mini": {
                "complexity_support": ["trivial", "simple", "moderate"],
                "cost_per_1k_tokens": 0.00015,
                "typical_latency_ms": 400,
                "provider": "openai",
                "strengths": ["simple_tasks", "classification"],
            },
            "claude-sonnet-4-20250514": {
                "complexity_support": ["trivial", "simple", "moderate", "complex", "expert"],
                "cost_per_1k_tokens": 0.003,
                "typical_latency_ms": 700,
                "provider": "anthropic",
                "strengths": ["reasoning", "analysis", "long_context"],
            },
            "gemini-2.5-flash": {
                "complexity_support": ["trivial", "simple", "moderate", "complex"],
                "cost_per_1k_tokens": 0.00015,
                "typical_latency_ms": 350,
                "provider": "google",
                "strengths": ["speed", "multimodal"],
            },
        }

        # Build candidate list
        candidates = []
        for name, profile in model_catalog.items():
            if task_complexity not in profile["complexity_support"]:
                continue
            if preferred_providers and profile["provider"] not in preferred_providers:
                continue
            if budget_limit is not None and profile["cost_per_1k_tokens"] > budget_limit:
                continue

            # Historical performance bonus
            history = self._model_performance.get(name, {}).get(task_pattern)
            historical_bonus = 0.0
            if history:
                total_attempts = history.successes + history.failures
                if total_attempts > 0:
                    historical_bonus = (history.successes / total_attempts) * 0.3

            candidates.append({
                "model": name,
                "provider": profile["provider"],
                "cost_per_1k_tokens": profile["cost_per_1k_tokens"],
                "complexity_match": 1.0,
                "historical_score": historical_bonus,
                "composite_score": 0.5 + historical_bonus - profile["cost_per_1k_tokens"] * 10,
            })

        if not candidates:
            return {"model": "gpt-4o", "reason": "fallback_default", "confidence": 0.5}

        # Sort by composite score
        candidates.sort(key=lambda c: c["composite_score"], reverse=True)
        best = candidates[0]

        # Determine selection reason
        if best["historical_score"] > 0.15:
            reason = "best_historical_performance"
        elif budget_limit is not None:
            reason = "within_budget"
        else:
            reason = "best_overall_match"

        return {
            "model": best["model"],
            "reason": reason,
            "confidence": min(best["composite_score"], 0.95),
            "alternatives": [c["model"] for c in candidates[1:4]],
        }

    def record_model_performance(self, model_name: str, task_pattern: str,
                                  success: bool, latency_ms: float = 0.0,
                                  confidence: float = 0.0):
        """Record model performance for a task pattern to guide future selection."""
        if task_pattern not in self._model_performance[model_name]:
            self._model_performance[model_name][task_pattern] = ModelPerformanceRecord(
                model_name=model_name, task_pattern=task_pattern
            )

        record = self._model_performance[model_name][task_pattern]
        if success:
            record.successes += 1
        else:
            record.failures += 1

        total = record.successes + record.failures
        if latency_ms > 0:
            record.avg_latency_ms = (
                record.avg_latency_ms * (total - 1) + latency_ms
            ) / max(total, 1)
        if confidence > 0:
            record.avg_confidence = (
                record.avg_confidence * (total - 1) + confidence
            ) / max(total, 1)

        logger.debug(
            "Model performance recorded: %s on '%s' success=%s",
            model_name, task_pattern, success
        )

    # ── Reasoning Chain Validation ─────────────────────────

    def validate_reasoning_chain(self, steps: list[dict], answer: str = "",
                                  claimed_facts: list[str] | None = None) -> ValidationResult:
        """Self-critique mechanism that validates reasoning chains.

        Checks for logical consistency between steps, completeness of the
        reasoning path, and factual grounding of claims. Returns a
        structured validation with issues and suggestions.
        """
        issues: list[str] = []
        suggestions: list[str] = []

        logical_score = self._check_logical_consistency(steps, issues, suggestions)
        completeness_score = self._check_completeness(steps, answer, issues, suggestions)
        factual_score = self._check_factual_grounding(steps, claimed_facts, issues, suggestions)

        # Aggregate: each dimension contributes equally
        overall = (logical_score + completeness_score + factual_score) / 3.0
        is_valid = overall >= 0.6 and len(issues) <= len(steps) * 0.5

        result = ValidationResult(
            is_valid=is_valid,
            logical_consistency_score=logical_score,
            completeness_score=completeness_score,
            factual_grounding_score=factual_score,
            issues=issues,
            suggestions=suggestions,
        )

        logger.debug(
            "Chain validation: valid=%s, logical=%.2f, complete=%.2f, factual=%.2f",
            is_valid, logical_score, completeness_score, factual_score
        )
        return result

    def _check_logical_consistency(self, steps: list[dict],
                                    issues: list[str], suggestions: list[str]) -> float:
        """Check logical consistency between consecutive reasoning steps."""
        if len(steps) < 2:
            return 1.0

        deductions = 0.0
        check_count = min(len(steps) - 1, self.config.validation_check_count * 2)

        for i in range(min(len(steps) - 1, check_count)):
            curr_content = steps[i].get("content", "").lower()
            next_content = steps[i + 1].get("content", "").lower()

            # Check for abrupt topic shifts
            curr_words = set(curr_content.split())
            next_words = set(next_content.split())
            if curr_words and next_words:
                overlap = len(curr_words & next_words) / max(len(curr_words | next_words), 1)
                if overlap < 0.05 and len(curr_content) > 30 and len(next_content) > 30:
                    issues.append(f"Abrupt topic shift between step {i + 1} and step {i + 2}")
                    suggestions.append("Add a bridging statement connecting these two steps")
                    deductions += 0.15

            # Check for contradictory confidence signals
            curr_conf = steps[i].get("confidence", 1.0)
            next_conf = steps[i + 1].get("confidence", 1.0)
            if abs(curr_conf - next_conf) > 0.5:
                issues.append(f"Large confidence swing between step {i + 1} ({curr_conf}) "
                            f"and step {i + 2} ({next_conf})")
                suggestions.append("Review the reasoning that caused this confidence shift")
                deductions += 0.1

        return max(0.0, 1.0 - deductions)

    def _check_completeness(self, steps: list[dict], answer: str,
                             issues: list[str], suggestions: list[str]) -> float:
        """Check if the reasoning chain covers the task comprehensively."""
        score = 0.5
        step_count = len(steps)

        if step_count == 0:
            issues.append("No reasoning steps provided")
            suggestions.append("Add at least one thinking step")
            return 0.0

        if step_count >= 3:
            score += 0.2
        if step_count >= 5:
            score += 0.1

        # Check for diverse step types
        step_types = {s.get("step_type", "") for s in steps}
        if len(step_types) >= 2:
            score += 0.1

        # Check if answer is present and substantial
        if not answer:
            issues.append("No final answer provided")
            suggestions.append("Generate a concluding answer synthesizing all steps")
            score -= 0.2
        elif len(answer) < 50 and step_count >= 3:
            issues.append("Final answer is short relative to the reasoning depth")
            suggestions.append("Elaborate the answer to reflect the depth of reasoning")
            score -= 0.1

        # Check for tool usage diversity
        all_tool_calls: list[str] = []
        for s in steps:
            all_tool_calls.extend(s.get("tool_calls", []))
        if step_count >= 3 and not all_tool_calls:
            suggestions.append("Consider using tools to ground reasoning in external data")

        return min(max(score, 0.0), 1.0)

    def _check_factual_grounding(self, steps: list[dict],
                                  claimed_facts: list[str] | None,
                                  issues: list[str], suggestions: list[str]) -> float:
        """Check if reasoning steps are grounded in facts or tool results."""
        score = 0.5

        # Check for tool-based grounding
        grounded_steps = sum(
            1 for s in steps
            if s.get("step_type") == "act" or s.get("tool_calls")
        )
        if len(steps) > 0 and grounded_steps / len(steps) >= 0.3:
            score += 0.3

        # Check for unsupported claims
        if claimed_facts:
            unsupported = 0
            for fact in claimed_facts:
                found = any(fact.lower() in s.get("content", "").lower() for s in steps)
                if not found:
                    unsupported += 1
            if unsupported > 0:
                score -= min(unsupported * 0.1, 0.3)
                issues.append(f"{unsupported} claimed facts not traceable to reasoning steps")
                suggestions.append("Ensure each factual claim links back to a reasoning step")

        # Check for hedge-heavy content (weak grounding)
        hedge_words = ["might", "maybe", "possibly", "could be", "potentially", "seems"]
        hedge_count = 0
        for s in steps:
            content = s.get("content", "").lower()
            hedge_count += sum(1 for w in hedge_words if w in content)
        if hedge_count > len(steps) * 2:
            issues.append("Excessive hedging indicates weak factual grounding")
            suggestions.append("Use tool results or citations to reduce uncertainty language")
            score -= 0.15

        return min(max(score, 0.0), 1.0)

    # ── Prompt Optimization ────────────────────────────────

    def analyze_prompt(self, prompt_text: str, response_quality: float = 0.5) -> PromptAnalysis:
        """Analyze a prompt and suggest improvements based on past outcomes.

        Examines prompt structure, clarity, and specificity, then compares
        against historical patterns to identify what leads to better responses.
        """
        clarity = self._compute_prompt_clarity(prompt_text)
        specificity = self._compute_prompt_specificity(prompt_text)
        effectiveness = (clarity * 0.4 + specificity * 0.4 + response_quality * 0.2)

        strengths, weaknesses = self._assess_prompt_qualities(prompt_text, clarity, specificity)
        suggested = self._generate_prompt_suggestion(prompt_text, weaknesses)

        analysis = PromptAnalysis(
            prompt_text=prompt_text,
            effectiveness_score=round(effectiveness, 3),
            clarity_score=round(clarity, 3),
            specificity_score=round(specificity, 3),
            strengths=strengths,
            weaknesses=weaknesses,
            suggested_rewrite=suggested,
        )

        if self.config.enable_prompt_optimization:
            self._prompt_history.append(analysis)
            if len(self._prompt_history) > self.config.prompt_analysis_window * 2:
                self._prompt_history = self._prompt_history[-self.config.prompt_analysis_window:]

        return analysis

    def _compute_prompt_clarity(self, prompt: str) -> float:
        """Compute a clarity score for a prompt."""
        score = 0.5
        prompt_lower = prompt.lower()

        # Sentence structure
        if "?" in prompt:
            score += 0.1  # Clear question format
        if prompt.strip().endswith(".") or prompt.strip().endswith("?"):
            score += 0.05

        # Ambiguity signals reduce clarity
        ambiguous = ["thing", "stuff", "something", "whatever", "etc", "somehow"]
        ambig_count = sum(1 for w in ambiguous if w in prompt_lower)
        score -= min(ambig_count * 0.1, 0.3)

        # Length: very short or very long reduces clarity
        length = len(prompt)
        if length < 20:
            score -= 0.15
        elif length > 2000:
            score -= 0.1
        elif 50 <= length <= 500:
            score += 0.1

        # Instruction words signal clarity
        instruction_words = ["please", "explain", "describe", "list", "compare", "analyze"]
        if any(w in prompt_lower for w in instruction_words):
            score += 0.1

        return min(max(score, 0.0), 1.0)

    def _compute_prompt_specificity(self, prompt: str) -> float:
        """Compute a specificity score for a prompt."""
        score = 0.5
        prompt_lower = prompt.lower()

        # Context markers
        context_markers = ["context:", "background:", "here is", "given that", "considering"]
        if any(m in prompt_lower for m in context_markers):
            score += 0.15

        # Constraint and format specifications
        constraint_words = ["must", "should", "exactly", "only", "at least", "at most",
                           "in json", "in markdown", "as a list", "step by step"]
        constraint_count = sum(1 for w in constraint_words if w in prompt_lower)
        score += min(constraint_count * 0.05, 0.15)

        # Examples provided
        if "example" in prompt_lower or "e.g." in prompt_lower or "for instance" in prompt_lower:
            score += 0.1

        # Numeric specificity
        import re
        numbers = len(re.findall(r'\d+', prompt))
        score += min(numbers * 0.02, 0.1)

        return min(max(score, 0.0), 1.0)

    def _assess_prompt_qualities(self, prompt: str, clarity: float,
                                  specificity: float) -> tuple[list[str], list[str]]:
        """Assess specific strengths and weaknesses of a prompt."""
        strengths = []
        weaknesses = []

        if clarity >= 0.7:
            strengths.append("Clear and unambiguous wording")
        if specificity >= 0.7:
            strengths.append("Well-specified with concrete details")
        if len(prompt) >= 50 and len(prompt) <= 500:
            strengths.append("Optimal length for detailed response")
        if "?" in prompt:
            strengths.append("Framed as a direct question")
        if "example" in prompt.lower() or "e.g." in prompt.lower():
            strengths.append("Includes examples or illustrations")

        if clarity < 0.4:
            weaknesses.append("Ambiguous wording; consider rephrasing for clarity")
        if specificity < 0.4:
            weaknesses.append("Lacks specific details or constraints")
        if len(prompt) < 20:
            weaknesses.append("Too brief; add more context for better results")
        if len(prompt) > 1500:
            weaknesses.append("Very long; consider breaking into focused sub-questions")
        if prompt.lower().count("?") > 3:
            weaknesses.append("Multiple questions bundled; split into separate prompts")
        if not strengths:
            weaknesses.append("No clear strengths detected; consider complete rewording")

        return strengths, weaknesses

    def _generate_prompt_suggestion(self, original: str, weaknesses: list[str]) -> str:
        """Generate a suggested prompt rewrite based on weaknesses."""
        if not weaknesses:
            return original

        # Look at historical high-effectiveness prompts for patterns
        high_eff = [a for a in self._prompt_history if a.effectiveness_score > 0.7]
        suggested = original

        if "Too brief" in " ".join(weaknesses):
            suggested = original + " [Consider adding: context, desired format, and any constraints.]"
        if "ambiguous" in " ".join(weaknesses).lower():
            suggested = original + " [Clarify: specify exact scope, expected output type, and key terms.]"
        if "lacks specific" in " ".join(weaknesses).lower():
            suggested = original + " [Add: specific requirements, output format, and success criteria.]"

        return suggested

    def suggest_prompt_improvements(self, original_prompt: str) -> list[str]:
        """Generate concrete improvement suggestions for a prompt.

        Learns from historical prompt-response pairs to identify which
        prompt characteristics correlate with better outcomes.
        """
        suggestions = []

        # Learn from history
        if self._prompt_history:
            high_scoring = [a for a in self._prompt_history if a.effectiveness_score > 0.7]
            if high_scoring:
                common_strengths: dict[str, int] = defaultdict(int)
                for a in high_scoring:
                    for s in a.strengths:
                        common_strengths[s] += 1
                for strength, count in sorted(common_strengths.items(), key=lambda x: -x[1])[:3]:
                    suggestions.append(f"High-scoring prompts tend to have: {strength.lower()}")

        # Analyze current prompt
        analysis = self.analyze_prompt(original_prompt)
        for w in analysis.weaknesses:
            suggestions.append(f"Issue: {w.lower()}")
        if analysis.suggested_rewrite and analysis.suggested_rewrite != original_prompt:
            suggestions.append(f"Suggested: {analysis.suggested_rewrite}")

        return suggestions

    # ── Uncertainty Quantification ─────────────────────────

    def quantify_uncertainty(self, answer: str, reasoning_steps: list[dict],
                              tool_results: list[dict] | None = None,
                              confidence_history: list[float] | None = None) -> UncertaintyEstimate:
        """Estimate and communicate uncertainty using multiple calibration techniques.

        Combines ensemble-based variance, calibration error analysis, and
        cross-step consistency to produce a multi-faceted uncertainty
        estimate with confidence intervals.
        """
        method_scores: dict[str, float] = {}

        # Method 1: Ensemble variance from step confidences
        ensemble_var = self._compute_ensemble_variance(reasoning_steps)
        method_scores["ensemble"] = ensemble_var

        # Method 2: Calibration error from historical confidence vs outcomes
        calibration_err = self._compute_calibration_error(confidence_history)
        method_scores["calibration"] = calibration_err

        # Method 3: Cross-step consistency
        consistency = self._compute_consistency_score(reasoning_steps, answer)
        method_scores["consistency"] = 1.0 - consistency

        # Weighted aggregation
        active_methods = [m for m in self.config.uncertainty_methods if m in method_scores]
        if not active_methods:
            active_methods = list(method_scores.keys())

        weights = {"ensemble": 0.35, "calibration": 0.30, "consistency": 0.35}
        total_weight = sum(weights.get(m, 0.33) for m in active_methods)
        overall = sum(
            method_scores[m] * weights.get(m, 0.33) / max(total_weight, 0.01)
            for m in active_methods
        )

        # Confidence interval (wider = more uncertainty)
        margin = overall * 0.3
        conf_interval = (max(0.0, 0.7 - overall - margin), min(1.0, 0.7 - overall + margin))

        # Build narrative
        narrative = self._build_uncertainty_narrative(overall, method_scores, reasoning_steps)

        return UncertaintyEstimate(
            overall_uncertainty=round(min(overall, 1.0), 3),
            ensemble_variance=round(ensemble_var, 3),
            calibration_error=round(calibration_err, 3),
            consistency_score=round(consistency, 3),
            confidence_interval=(round(conf_interval[0], 3), round(conf_interval[1], 3)),
            method_scores={k: round(v, 3) for k, v in method_scores.items()},
            narrative=narrative,
        )

    def _compute_ensemble_variance(self, steps: list[dict]) -> float:
        """Compute ensemble-based uncertainty from step confidence variance."""
        confidences = [s.get("confidence", 0.5) for s in steps]
        if len(confidences) < 2:
            return 0.5  # High uncertainty with insufficient data

        mean_conf = sum(confidences) / len(confidences)
        variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)

        # Normalize to 0-1 range (max variance for [0,1] is 0.25)
        normalized = min(variance / 0.25, 1.0)

        # Also consider confidence trend (declining = more uncertainty)
        if len(confidences) >= 3:
            first_half = confidences[:len(confidences)//2]
            second_half = confidences[len(confidences)//2:]
            if sum(first_half) / len(first_half) > sum(second_half) / max(len(second_half), 1):
                normalized += 0.1

        return min(normalized, 1.0)

    def _compute_calibration_error(self, confidence_history: list[float] | None) -> float:
        """Compute calibration error from historical confidence vs actual outcomes."""
        if not confidence_history or len(confidence_history) < 3:
            return 0.3  # Default moderate calibration error

        # Compare recent predictions to actual outcomes from experiences
        if not self._experiences:
            return 0.2

        recent_experiences = self._experiences[-len(confidence_history):]
        errors = []
        for i, (conf, exp) in enumerate(zip(confidence_history, recent_experiences)):
            actual = 1.0 if exp.outcome == "success" else 0.0
            errors.append(abs(conf - actual))

        mean_error = sum(errors) / len(errors)
        return min(mean_error, 1.0)

    def _compute_consistency_score(self, steps: list[dict], answer: str) -> float:
        """Compute cross-step consistency score."""
        if len(steps) < 2:
            return 0.7

        # Check if answer aligns with final reasoning steps
        score = 0.5
        if answer and steps:
            last_step_content = steps[-1].get("content", "").lower()
            answer_lower = answer.lower()
            # Semantic overlap between last step and answer
            last_words = set(last_step_content.split())
            answer_words = set(answer_lower.split())
            if last_words and answer_words:
                overlap = len(last_words & answer_words) / max(
                    len(last_words | answer_words), 1
                )
                score += overlap * 0.3

        # Step-to-step confidence stability
        confidences = [s.get("confidence", 0.5) for s in steps]
        if len(confidences) >= 2:
            max_dev = max(abs(confidences[i] - confidences[i + 1])
                         for i in range(len(confidences) - 1))
            stability = 1.0 - max_dev
            score += stability * 0.2

        return min(score, 1.0)

    def _build_uncertainty_narrative(self, overall: float, method_scores: dict,
                                      steps: list[dict]) -> str:
        """Build a human-readable narrative about the uncertainty estimate."""
        if overall < 0.2:
            narrative = "High certainty: multiple calibration methods agree on a confident result."
        elif overall < 0.4:
            narrative = "Moderate certainty: the response is reliable but minor variations exist."
        elif overall < 0.6:
            narrative = "Notable uncertainty: confidence varies across methods; verify key claims."
        elif overall < 0.8:
            narrative = "High uncertainty: the response should be treated as tentative guidance."
        else:
            narrative = "Extreme uncertainty: the response is speculative; seek additional data."

        # Add method-specific notes
        if method_scores.get("ensemble", 0) > 0.5:
            narrative += " Step confidence varies significantly across the reasoning process."
        if method_scores.get("calibration", 0) > 0.4:
            narrative += " Historical calibration suggests potential overconfidence."
        if method_scores.get("consistency", 0) > 0.5:
            narrative += " Cross-step reasoning consistency is low."

        # Step count note
        if len(steps) < 3:
            narrative += " Limited reasoning steps contribute to higher uncertainty."

        return narrative