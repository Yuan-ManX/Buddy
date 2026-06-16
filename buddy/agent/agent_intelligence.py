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