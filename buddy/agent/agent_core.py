"""Buddy Agent Core — unified autonomous agent execution framework

Provides the central execution nucleus for all Buddy agents, deeply integrating
reasoning, metacognition, tool orchestration, memory, evolution, proactive discovery,
and reactive execution into a single cohesive system.

Core capabilities:
  - Deep Reasoning: multi-strategy reasoning with automatic strategy selection
  - Adaptive Tool Use: intelligent tool selection, chaining, and parallelization
  - Continuous Learning: experience replay, pattern recognition, self-optimization
  - Proactive Execution: always-on observation, task discovery, autopilot bridging
  - Memory Integration: three-tier memory with semantic retrieval and consolidation
  - Meta-Cognition: adaptive strategy selection based on task fingerprinting
  - Evolution Tracking: experience accumulation with outcome-based learning
  - Checkpoint Safety: execution state preservation and rollback capability
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger("buddy.agent_core")


# ═══════════════════════════════════════════════════════════
# Enums and Configuration
# ═══════════════════════════════════════════════════════════

class AgentState(str, Enum):
    """Lifecycle states for an autonomous agent."""
    IDLE = "idle"
    OBSERVING = "observing"
    REASONING = "reasoning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    LEARNING = "learning"
    PAUSED = "paused"
    ERROR = "error"


class ExecutionContext(str, Enum):
    """Execution context types for the agent."""
    CHAT = "chat"               # Direct user conversation
    TASK = "task"               # Structured task execution
    AUTOPILOT = "autopilot"     # Scheduled background task
    PROACTIVE = "proactive"     # Self-initiated discovery
    DELEGATED = "delegated"     # Task from another agent
    SWARM = "swarm"             # Collaborative swarm execution
    REACTIVE = "reactive"       # Reactive loop trigger
    DREAM = "dream"             # Background consolidation


class AgentCapability(str, Enum):
    """Registered capabilities of an agent."""
    CHAT = "chat"
    CODE = "code"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    CREATIVE = "creative"
    SUMMARIZATION = "summarization"
    SCHEDULING = "scheduling"
    MONITORING = "monitoring"
    DELEGATION = "delegation"


@dataclass
class AgentCoreConfig:
    """Configuration for the Agent Core."""
    max_reasoning_depth: int = 10
    max_tool_rounds: int = 8
    max_parallel_branches: int = 5
    experience_window: int = 100
    learning_rate: float = 0.1
    confidence_threshold: float = 0.7
    proactive_scan_interval_ms: int = 30000
    memory_retrieval_limit: int = 10
    context_prune_threshold: int = 8000
    enable_metacognition: bool = True
    enable_evolution: bool = True
    enable_proactive: bool = True
    enable_checkpoints: bool = True
    enable_streaming: bool = True


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class ExecutionStep:
    """A single step in the agent's execution trace."""
    id: str
    phase: str  # observe, think, act, reflect, decide
    content: str
    tool_calls: list[str] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    confidence: float = 0.5
    elapsed_ms: float = 0.0
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExecutionTrace:
    """Complete trace of an agent execution."""
    id: str
    context: ExecutionContext
    prompt: str
    steps: list[ExecutionStep] = field(default_factory=list)
    final_answer: str = ""
    tools_used: list[str] = field(default_factory=list)
    total_tokens: int = 0
    total_time_ms: float = 0.0
    confidence: float = 0.0
    success: bool = True
    error: str = ""
    insights: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentInsight:
    """A learned insight from past executions."""
    id: str
    category: str  # pattern, strategy, tool, memory, behavior
    content: str
    confidence: float = 0.5
    evidence_count: int = 0
    source_traces: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ProactiveSignal:
    """A signal detected by proactive scanning."""
    id: str
    signal_type: str  # memory_pattern, time_trigger, context_gap, opportunity
    description: str
    priority: float = 0.5
    suggested_action: str = ""
    evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════
# Agent Core
# ═══════════════════════════════════════════════════════════

class AgentCore:
    """Unified autonomous agent execution core.

    Deeply integrates reasoning, metacognition, tool orchestration, memory,
    evolution, proactive discovery, and reactive execution into a single
    cohesive system. Each agent instance operates as a self-contained
    intelligence unit with its own memory, learning trajectory, and
    capability profile.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str = "Buddy",
        config: AgentCoreConfig | None = None,
        client: AsyncOpenAI | None = None,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.config = config or AgentCoreConfig()
        self.client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        # State
        self._state = AgentState.IDLE
        self._capabilities: set[AgentCapability] = set()
        self._execution_history: list[ExecutionTrace] = []
        self._insights: list[AgentInsight] = []
        self._proactive_signals: list[ProactiveSignal] = []
        self._checkpoints: dict[str, dict] = {}
        self._active_traces: dict[str, ExecutionTrace] = {}

        # Performance tracking
        self._total_executions: int = 0
        self._successful_executions: int = 0
        self._total_tokens_used: int = 0
        self._total_tool_calls: int = 0
        self._avg_response_time_ms: float = 0.0

        # Strategy effectiveness
        self._strategy_scores: dict[str, dict[str, float]] = defaultdict(
            lambda: {"successes": 0, "failures": 0, "avg_tokens": 0.0, "avg_time": 0.0}
        )

        # Tool usage patterns
        self._tool_patterns: dict[str, list[str]] = defaultdict(list)

        # Task fingerprint → best strategy mapping
        self._task_strategy_map: dict[str, str] = {}

    # ── Properties ───────────────────────────────────────

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def total_executions(self) -> int:
        return self._total_executions

    @property
    def success_rate(self) -> float:
        if self._total_executions == 0:
            return 0.0
        return self._successful_executions / self._total_executions

    @property
    def total_tokens(self) -> int:
        return self._total_tokens_used

    @property
    def capabilities(self) -> list[str]:
        return [c.value for c in self._capabilities]

    # ── State Management ─────────────────────────────────

    def set_state(self, state: AgentState):
        """Transition the agent to a new state."""
        old_state = self._state
        self._state = state
        logger.debug(f"Agent {self.agent_id}: {old_state.value} → {state.value}")

    def register_capability(self, capability: AgentCapability):
        """Register a capability for this agent."""
        self._capabilities.add(capability)

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if the agent has a specific capability."""
        return capability in self._capabilities

    # ── Task Fingerprinting ──────────────────────────────

    def fingerprint_task(self, prompt: str) -> str:
        """Generate a stable fingerprint for a task to enable pattern matching."""
        # Normalize the prompt
        normalized = prompt.lower().strip()
        # Extract key structural features
        words = normalized.split()
        key_verbs = [w for w in words[:20] if w in {
            "explain", "analyze", "create", "debug", "fix", "implement",
            "design", "review", "optimize", "research", "summarize", "translate",
            "compare", "calculate", "generate", "refactor", "test", "deploy",
            "monitor", "schedule", "search", "find", "write", "read",
        }]
        features = "|".join(key_verbs[:5]) if key_verbs else "general"
        features += f"|len:{min(len(normalized) // 100, 20)}"
        features += f"|qs:{'?' in normalized}"
        features += f"|mult:{normalized.count('?') > 1 or ';' in normalized}"
        return hashlib.md5(features.encode()).hexdigest()[:12]

    # ── Strategy Selection ───────────────────────────────

    def select_strategy(self, prompt: str, available_tools: list[str] | None = None) -> dict:
        """Select the optimal execution strategy for a task.

        Uses task fingerprinting to match against historical outcomes,
        combined with heuristic analysis of task complexity and required tools.
        """
        fingerprint = self.fingerprint_task(prompt)

        # Check if we have a learned strategy for this task pattern
        if fingerprint in self._task_strategy_map:
            learned_strategy = self._task_strategy_map[fingerprint]
            strategy_score = self._strategy_scores.get(learned_strategy, {})
            if strategy_score.get("successes", 0) > 0:
                return {
                    "fingerprint": fingerprint,
                    "strategy": learned_strategy,
                    "source": "learned",
                    "confidence": min(
                        strategy_score["successes"] / max(strategy_score["successes"] + strategy_score["failures"], 1),
                        0.95,
                    ),
                }

        # Heuristic-based strategy selection
        prompt_lower = prompt.lower()
        strategy = "balanced"

        # Complexity heuristics
        complex_signals = ["design", "implement", "optimize", "research", "refactor"]
        simple_signals = ["summarize", "translate", "calculate", "hello", "hi"]
        expert_signals = ["architecture", "system design", "security audit", "performance"]

        if any(s in prompt_lower for s in expert_signals):
            strategy = "tree_of_thought"
        elif any(s in prompt_lower for s in complex_signals):
            strategy = "decomposition"
        elif len(prompt) > 500:
            strategy = "thorough"
        elif any(s in prompt_lower for s in simple_signals):
            strategy = "concise"

        return {
            "fingerprint": fingerprint,
            "strategy": strategy,
            "source": "heuristic",
            "confidence": 0.7,
        }

    # ── Tool Intelligence ────────────────────────────────

    def score_tools(self, prompt: str, tools: list[str]) -> list[dict]:
        """Score tools by relevance to the current task."""
        relevance_map = {
            "search": ["search", "find", "lookup", "query", "google", "research"],
            "web_search": ["search", "find", "lookup", "query", "google", "research"],
            "web_fetch": ["fetch", "url", "website", "http", "download", "scrape", "read online"],
            "read_file": ["read", "file", "open", "view", "check", "examine"],
            "write_file": ["write", "create", "save", "generate file", "output"],
            "execute_code": ["run", "execute", "code", "python", "script", "compute", "debug", "test"],
            "memory_search": ["remember", "recall", "memory", "past", "history", "previous"],
            "calculate": ["calculate", "compute", "math", "formula", "equation"],
            "summarize": ["summary", "summarize", "brief", "overview", "tldr"],
            "analyze_data": ["analyze", "data", "statistics", "chart", "graph", "metrics"],
            "send_message": ["send", "message", "email", "notify", "alert"],
            "schedule_task": ["schedule", "remind", "calendar", "plan", "set timer"],
            "image_generate": ["image", "picture", "draw", "generate image", "visual"],
        }

        prompt_lower = prompt.lower()
        scored = []
        for tool in tools:
            score = 0.0
            reason = "general purpose"
            keywords = relevance_map.get(tool, [tool])
            for kw in keywords:
                if kw in prompt_lower:
                    score += 0.25
                    reason = f"matched: {kw}"

            # Boost from usage patterns
            if tool in self._tool_patterns:
                pattern_score = min(len(self._tool_patterns[tool]) * 0.05, 0.3)
                score += pattern_score

            scored.append({
                "tool": tool,
                "score": min(score, 1.0),
                "reason": reason,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def plan_tool_sequence(self, task: str, available_tools: list[str]) -> list[list[str]]:
        """Plan an optimal tool execution sequence with parallelization."""
        task_lower = task.lower()

        # Pattern-based sequencing
        patterns = {
            "research": [["web_search", "web_fetch"], ["read_file", "memory_search"], ["analyze_data"], ["summarize"]],
            "coding": [["read_file"], ["web_search", "memory_search"], ["write_file", "execute_code"], ["execute_code"]],
            "debugging": [["read_file"], ["execute_code", "web_search"], ["analyze_data"], ["write_file"]],
            "analysis": [["read_file", "web_search"], ["analyze_data", "memory_search"], ["summarize"]],
            "creation": [["web_search", "memory_search"], ["write_file"], ["execute_code"], ["read_file"]],
        }

        for pattern_key, sequence in patterns.items():
            if pattern_key in task_lower:
                # Filter to only available tools
                return [
                    [t for t in step if t in available_tools] or step
                    for step in sequence
                ]

        return [["web_search", "memory_search"], ["analyze_data"]]

    # ── Execution Recording ──────────────────────────────

    def start_execution(self, context: ExecutionContext, prompt: str) -> ExecutionTrace:
        """Start recording a new execution trace."""
        trace = ExecutionTrace(
            id=f"exec-{uuid.uuid4().hex[:12]}",
            context=context,
            prompt=prompt,
        )
        self._active_traces[trace.id] = trace
        self.set_state(AgentState.REASONING)
        return trace

    def add_step(self, trace_id: str, step: ExecutionStep):
        """Add a step to an execution trace."""
        trace = self._active_traces.get(trace_id)
        if trace:
            trace.steps.append(step)

    def complete_execution(
        self,
        trace_id: str,
        answer: str,
        success: bool = True,
        error: str = "",
        insights: list[str] | None = None,
    ) -> ExecutionTrace | None:
        """Complete an execution trace."""
        trace = self._active_traces.pop(trace_id, None)
        if not trace:
            return None

        trace.final_answer = answer
        trace.success = success
        trace.error = error
        trace.insights = insights or []

        if trace.steps:
            trace.total_time_ms = sum(s.elapsed_ms for s in trace.steps)
            trace.confidence = sum(s.confidence for s in trace.steps) / max(len(trace.steps), 1)

        # Record in history
        self._execution_history.append(trace)
        if len(self._execution_history) > self.config.experience_window * 2:
            self._execution_history = self._execution_history[-self.config.experience_window:]

        # Update stats
        self._total_executions += 1
        if success:
            self._successful_executions += 1

        # Update strategy scores
        if trace.steps:
            strategy = self._task_strategy_map.get(
                self.fingerprint_task(trace.prompt), "unknown"
            )
            scores = self._strategy_scores[strategy]
            if success:
                scores["successes"] += 1
            else:
                scores["failures"] += 1
            scores["avg_tokens"] = (scores["avg_tokens"] * (self._total_executions - 1) + trace.total_tokens) / max(self._total_executions, 1)
            scores["avg_time"] = (scores["avg_time"] * (self._total_executions - 1) + trace.total_time_ms) / max(self._total_executions, 1)

        # Update average response time
        self._avg_response_time_ms = (
            (self._avg_response_time_ms * (self._total_executions - 1) + trace.total_time_ms)
            / max(self._total_executions, 1)
        )

        self.set_state(AgentState.IDLE)
        return trace

    # ── Insight Generation ───────────────────────────────

    def generate_insights(self) -> list[AgentInsight]:
        """Generate insights from accumulated execution history."""
        if len(self._execution_history) < 5:
            return []

        new_insights = []

        # Pattern insight: detect recurring successful strategies
        strategy_outcomes = defaultdict(list)
        for trace in self._execution_history[-50:]:
            fingerprint = self.fingerprint_task(trace.prompt)
            strategy_outcomes[fingerprint].append(trace.success)

        for fingerprint, outcomes in strategy_outcomes.items():
            if len(outcomes) >= 3:
                success_rate = sum(1 for o in outcomes if o) / len(outcomes)
                if success_rate > 0.8:
                    # This task pattern consistently succeeds
                    existing = [i for i in self._insights if fingerprint in str(i.source_traces)]
                    if not existing:
                        insight = AgentInsight(
                            id=f"insight-{uuid.uuid4().hex[:8]}",
                            category="pattern",
                            content=f"Task pattern {fingerprint} has high success rate ({success_rate:.0%})",
                            confidence=success_rate,
                            evidence_count=len(outcomes),
                        )
                        new_insights.append(insight)
                        self._insights.append(insight)

        # Tool insight: detect most effective tool combinations
        tool_combos = defaultdict(lambda: {"successes": 0, "failures": 0})
        for trace in self._execution_history[-30:]:
            if trace.tools_used:
                combo_key = "→".join(sorted(trace.tools_used))
                if trace.success:
                    tool_combos[combo_key]["successes"] += 1
                else:
                    tool_combos[combo_key]["failures"] += 1

        for combo, stats in tool_combos.items():
            total = stats["successes"] + stats["failures"]
            if total >= 3:
                rate = stats["successes"] / total
                if rate > 0.8:
                    new_insights.append(AgentInsight(
                        id=f"insight-{uuid.uuid4().hex[:8]}",
                        category="tool",
                        content=f"Tool chain [{combo}] is highly effective ({rate:.0%})",
                        confidence=rate,
                        evidence_count=total,
                    ))

        # Prune old insights
        if len(self._insights) > 100:
            self._insights = self._insights[-50:]

        return new_insights

    # ── Proactive Signal Detection ───────────────────────

    def scan_proactive_signals(self) -> list[ProactiveSignal]:
        """Scan for proactive signals based on execution patterns and memory."""
        if not self.config.enable_proactive:
            return []

        signals = []

        # Signal: repeated task patterns suggest automation opportunity
        recent_traces = self._execution_history[-20:]
        task_patterns = defaultdict(int)
        for trace in recent_traces:
            fingerprint = self.fingerprint_task(trace.prompt)
            task_patterns[fingerprint] += 1

        for fingerprint, count in task_patterns.items():
            if count >= 3:
                signals.append(ProactiveSignal(
                    id=f"sig-{uuid.uuid4().hex[:8]}",
                    signal_type="opportunity",
                    description=f"Repeated task pattern detected ({count}x) — consider automation",
                    priority=min(0.3 + count * 0.1, 0.9),
                    suggested_action="Create autopilot schedule for this task pattern",
                    evidence={"fingerprint": fingerprint, "occurrences": count},
                ))

        # Signal: low success rate on certain strategy suggests adaptation
        for strategy, scores in self._strategy_scores.items():
            total = scores["successes"] + scores["failures"]
            if total >= 5:
                rate = scores["successes"] / total
                if rate < 0.5:
                    signals.append(ProactiveSignal(
                        id=f"sig-{uuid.uuid4().hex[:8]}",
                        signal_type="strategy_gap",
                        description=f"Strategy '{strategy}' has low success rate ({rate:.0%}) — consider adapting",
                        priority=0.6,
                        suggested_action=f"Explore alternative strategies for tasks using '{strategy}'",
                        evidence={"strategy": strategy, "rate": rate, "total": total},
                    ))

        # Signal: idle period suggests dream/consolidation
        if self._state == AgentState.IDLE and len(self._execution_history) > 10:
            last_exec = self._execution_history[-1]
            idle_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(last_exec.timestamp)).total_seconds()
            if idle_seconds > 300:  # 5 minutes idle
                signals.append(ProactiveSignal(
                    id=f"sig-{uuid.uuid4().hex[:8]}",
                    signal_type="context_gap",
                    description=f"Agent idle for {idle_seconds:.0f}s — opportunity for memory consolidation",
                    priority=0.3,
                    suggested_action="Run dream consolidation cycle",
                ))

        self._proactive_signals = signals[-20:]
        return signals

    # ── Checkpoint Management ────────────────────────────

    def save_checkpoint(self, name: str, state_data: dict) -> str:
        """Save an execution checkpoint."""
        checkpoint_id = f"cp-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{name}"
        self._checkpoints[checkpoint_id] = {
            "name": name,
            "state": state_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_state": self._state.value,
        }
        if len(self._checkpoints) > 50:
            oldest = sorted(self._checkpoints.keys())[0]
            del self._checkpoints[oldest]
        return checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> dict | None:
        """Restore from a checkpoint."""
        cp = self._checkpoints.get(checkpoint_id)
        return cp["state"].copy() if cp else None

    # ── Learning & Adaptation ────────────────────────────

    def learn_from_execution(self, trace: ExecutionTrace):
        """Learn from a completed execution to improve future performance."""
        fingerprint = self.fingerprint_task(trace.prompt)

        # Update task-strategy mapping
        if trace.success:
            # Find which strategy was used
            strategy = "balanced"  # default
            for step in trace.steps:
                if hasattr(step, 'metadata') and 'strategy' in step.metadata:
                    strategy = step.metadata['strategy']
                    break
            self._task_strategy_map[fingerprint] = strategy

        # Update tool patterns
        for tool in trace.tools_used:
            self._tool_patterns[tool].append("success" if trace.success else "failure")
            if len(self._tool_patterns[tool]) > 100:
                self._tool_patterns[tool] = self._tool_patterns[tool][-50:]

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict:
        """Get comprehensive agent core statistics."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "state": self._state.value,
            "capabilities": self.capabilities,
            "executions": {
                "total": self._total_executions,
                "successful": self._successful_executions,
                "success_rate": round(self.success_rate, 3),
            },
            "performance": {
                "total_tokens": self._total_tokens_used,
                "total_tool_calls": self._total_tool_calls,
                "avg_response_time_ms": round(self._avg_response_time_ms, 1),
            },
            "learning": {
                "insights": len(self._insights),
                "task_patterns": len(self._task_strategy_map),
                "tool_patterns": len(self._tool_patterns),
            },
            "strategies": {
                k: {
                    "successes": v["successes"],
                    "failures": v["failures"],
                    "avg_tokens": round(v["avg_tokens"], 1),
                    "avg_time_ms": round(v["avg_time"], 1),
                }
                for k, v in self._strategy_scores.items()
            },
            "checkpoints": len(self._checkpoints),
            "proactive_signals": len(self._proactive_signals),
        }

    def get_recent_traces(self, limit: int = 10) -> list[dict]:
        """Get recent execution traces."""
        return [
            {
                "id": t.id,
                "context": t.context.value,
                "prompt": t.prompt[:200],
                "steps": len(t.steps),
                "success": t.success,
                "confidence": round(t.confidence, 3),
                "total_time_ms": round(t.total_time_ms, 1),
                "tools_used": t.tools_used,
                "insights": t.insights,
                "timestamp": t.timestamp,
            }
            for t in self._execution_history[-limit:]
        ]

    def get_insights(self, limit: int = 20) -> list[dict]:
        """Get learned insights."""
        return [
            {
                "id": i.id,
                "category": i.category,
                "content": i.content,
                "confidence": round(i.confidence, 3),
                "evidence_count": i.evidence_count,
                "timestamp": i.timestamp,
            }
            for i in self._insights[-limit:]
        ]

    def get_proactive_signals(self, limit: int = 10) -> list[dict]:
        """Get recent proactive signals."""
        return [
            {
                "id": s.id,
                "type": s.signal_type,
                "description": s.description,
                "priority": s.priority,
                "suggested_action": s.suggested_action,
                "timestamp": s.timestamp,
            }
            for s in self._proactive_signals[-limit:]
        ]