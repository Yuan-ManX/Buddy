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

    # ── LLM-Powered Task Analysis ───────────────────────

    async def analyze(self, prompt: str) -> dict:
        """Use the LLM to deeply analyze a prompt and produce structured analysis.

        Returns a dict with:
          - task_type: primary task category
          - complexity: low | medium | high | very_high
          - required_capabilities: list of needed capabilities
          - required_tools: list of likely needed tools
          - risk_assessment: risk level and potential pitfalls
          - recommended_approach: suggested execution strategy
          - estimated_tokens: rough token estimate
          - prerequisite_knowledge: domains the agent should understand
          - ambiguity_flags: any detected ambiguities in the prompt
        """
        system_prompt = (
            "You are a task analysis engine. Analyze the user's prompt and produce "
            "a structured JSON assessment. Be precise and conservative in estimates. "
            "Output ONLY valid JSON, no markdown wrapping."
        )
        user_prompt = (
            f"Analyze the following task prompt and produce a JSON object with these fields:\n"
            f'  - task_type: one of [chat, code, research, analysis, planning, creative, '
            f'summarization, scheduling, monitoring, delegation]\n'
            f'  - complexity: one of [low, medium, high, very_high]\n'
            f'  - required_capabilities: list of strings from [chat, code, research, analysis, '
            f'planning, creative, summarization, scheduling, monitoring, delegation]\n'
            f'  - required_tools: list of tool names likely needed\n'
            f'  - risk_assessment: {{"level": "low|medium|high", "concerns": [string, ...]}}\n'
            f'  - recommended_approach: one-line summary of the best execution approach\n'
            f'  - estimated_tokens: integer estimate of response tokens needed\n'
            f'  - prerequisite_knowledge: list of knowledge domains required\n'
            f'  - ambiguity_flags: list of any ambiguous or unclear aspects\n'
            f'\nTask Prompt:\n"""\n{prompt}\n"""'
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1024,
            )
            content = response.choices[0].message.content or "{}"
            analysis = json.loads(content)
            self._total_tokens_used += response.usage.total_tokens if response.usage else 0
            logger.debug(f"Agent {self.agent_id}: LLM analysis complete for task, "
                         f"complexity={analysis.get('complexity', 'unknown')}")
            return analysis
        except Exception as e:
            logger.warning(f"Agent {self.agent_id}: LLM analysis failed ({e}), "
                           f"using heuristic fallback.")
            return self._analyze_heuristic(prompt)

    def _analyze_heuristic(self, prompt: str) -> dict:
        """Fallback heuristic analysis when LLM is unavailable."""
        prompt_lower = prompt.lower()

        # Task type detection
        task_type_map = {
            "chat": ["hello", "hi", "hey", "thanks", "how are you"],
            "code": ["implement", "code", "function", "class", "debug", "fix bug",
                     "refactor", "write a", "script", "program"],
            "research": ["research", "find information", "look up", "what is",
                         "how does", "explain"],
            "analysis": ["analyze", "compare", "evaluate", "assess", "review"],
            "planning": ["plan", "schedule", "organize", "roadmap", "strategy"],
            "creative": ["write a story", "poem", "creative", "design idea",
                         "brainstorm"],
            "summarization": ["summarize", "summary", "tldr", "brief"],
            "scheduling": ["remind", "calendar", "set a time", "schedule"],
            "monitoring": ["monitor", "track", "watch", "alert"],
        }
        task_type = "chat"
        for ttype, keywords in task_type_map.items():
            if any(kw in prompt_lower for kw in keywords):
                task_type = ttype
                break

        # Complexity estimation
        word_count = len(prompt.split())
        if word_count < 10:
            complexity = "low"
        elif word_count < 50:
            complexity = "medium"
        elif word_count < 200:
            complexity = "high"
        else:
            complexity = "very_high"

        # Required tools estimation
        tool_map = {
            "search": ["search", "find", "look up", "google"],
            "read_file": ["read", "file", "check", "examine"],
            "write_file": ["write", "create file", "save", "generate file"],
            "execute_code": ["run", "execute", "code", "compile"],
            "memory_search": ["remember", "recall", "past", "previous"],
        }
        required_tools = [
            tool for tool, keywords in tool_map.items()
            if any(kw in prompt_lower for kw in keywords)
        ] or ["web_search"]

        return {
            "task_type": task_type,
            "complexity": complexity,
            "required_capabilities": [task_type],
            "required_tools": required_tools,
            "risk_assessment": {"level": "low", "concerns": []},
            "recommended_approach": f"Standard {task_type} execution",
            "estimated_tokens": max(word_count * 3, 100),
            "prerequisite_knowledge": [],
            "ambiguity_flags": [],
        }

    # ── LLM-Powered Plan Sequencing ─────────────────────

    async def plan_sequence(
        self,
        task: str,
        available_tools: list[str] | None = None,
        context: str = "",
    ) -> dict:
        """Use the LLM to decompose a complex task into a structured sequence of
        sub-tasks with dependencies, parallelization opportunities, and effort
        estimates.

        Returns a dict with:
          - goal: the original task
          - sub_tasks: list of {{id, title, description, depends_on, tools, estimated_effort}}
          - parallel_groups: list of groups where sub-tasks can run concurrently
          - total_estimated_effort: aggregate effort across all sub-tasks
          - critical_path: list of sub-task ids on the critical path
        """
        tools_list = ", ".join(available_tools) if available_tools else "general purpose tools"
        context_block = f"\nAdditional Context:\n{context}" if context else ""

        system_prompt = (
            "You are a task decomposition engine. Given a task description and "
            "available tools, decompose the task into an ordered sequence of sub-tasks. "
            "Identify which sub-tasks depend on others and which can run in parallel. "
            "Output ONLY valid JSON, no markdown wrapping."
        )
        user_prompt = (
            f"Decompose the following task into sub-tasks.\n\n"
            f"Task Goal:\n\"\"\"\n{task}\n\"\"\"\n"
            f"Available Tools: {tools_list}{context_block}\n\n"
            f"Return a JSON object with:\n"
            f'  - sub_tasks: list of {{"id": "s1", "title": "...", '
            f'"description": "...", "depends_on": ["s0"], '
            f'"tools": ["tool_name"], "estimated_effort": "low|medium|high"}}\n'
            f'  - parallel_groups: list of lists of sub-task ids that can run concurrently\n'
            f'  - total_estimated_effort: "low|medium|high"\n'
            f'  - critical_path: ordered list of sub-task ids forming the critical path\n'
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2048,
            )
            content = response.choices[0].message.content or "{}"
            plan = json.loads(content)
            self._total_tokens_used += response.usage.total_tokens if response.usage else 0
            plan.setdefault("goal", task)
            plan.setdefault("sub_tasks", [])
            plan.setdefault("parallel_groups", [])
            plan.setdefault("total_estimated_effort", "medium")
            plan.setdefault("critical_path", [])
            logger.debug(f"Agent {self.agent_id}: LLM plan sequence generated "
                         f"{len(plan.get('sub_tasks', []))} sub-tasks.")
            return plan
        except Exception as e:
            logger.warning(f"Agent {self.agent_id}: LLM plan_sequence failed ({e}), "
                           f"using fallback.")
            return self._plan_sequence_fallback(task, available_tools or [])

    def _plan_sequence_fallback(
        self, task: str, available_tools: list[str],
    ) -> dict:
        """Fallback plan sequence using heuristic decomposition."""
        task_lower = task.lower()
        tools = available_tools or ["web_search", "read_file", "execute_code"]

        # Simple keyword-based decomposition
        sub_tasks = []
        patterns = {
            "research": [
                ("Search for information", tools[0] if tools else "web_search"),
                ("Fetch relevant sources", "web_fetch"),
                ("Analyze findings", "analyze_data"),
                ("Summarize results", "summarize"),
            ],
            "implement": [
                ("Review existing code", "read_file"),
                ("Plan implementation approach", None),
                ("Write implementation", "write_file"),
                ("Test the solution", "execute_code"),
            ],
            "debug": [
                ("Read the relevant code", "read_file"),
                ("Identify root cause", "execute_code"),
                ("Implement fix", "write_file"),
                ("Verify the fix", "execute_code"),
            ],
        }

        for key, steps in patterns.items():
            if key in task_lower:
                for i, (title, tool) in enumerate(steps):
                    sub_tasks.append({
                        "id": f"s{i}",
                        "title": title,
                        "description": f"{title} for: {task[:100]}",
                        "depends_on": [f"s{i-1}"] if i > 0 else [],
                        "tools": [tool] if tool else [],
                        "estimated_effort": "medium",
                    })
                break

        if not sub_tasks:
            sub_tasks = [
                {"id": "s0", "title": "Understand task", "description": task[:100],
                 "depends_on": [], "tools": [], "estimated_effort": "low"},
                {"id": "s1", "title": "Execute task", "description": task[:100],
                 "depends_on": ["s0"], "tools": available_tools[:2] if available_tools else [],
                 "estimated_effort": "medium"},
                {"id": "s2", "title": "Verify completion", "description": "Verify the result",
                 "depends_on": ["s1"], "tools": [], "estimated_effort": "low"},
            ]

        return {
            "goal": task,
            "sub_tasks": sub_tasks,
            "parallel_groups": [],
            "total_estimated_effort": "medium",
            "critical_path": [s["id"] for s in sub_tasks],
        }

    # ── LLM-Powered Reflection ──────────────────────────

    async def reflect(
        self,
        traces: list[ExecutionTrace] | None = None,
        limit: int = 10,
    ) -> dict:
        """Use the LLM to analyze past execution traces and generate actionable
        improvement suggestions.

        Args:
            traces: Specific traces to reflect on. If None, uses recent history.
            limit: Max number of traces to include from history.

        Returns a dict with:
          - patterns_identified: list of recurring patterns (good and bad)
          - improvement_suggestions: list of concrete action items
          - strategy_recommendations: suggestions for strategy adjustments
          - tool_usage_insights: observations about tool effectiveness
          - overall_assessment: high-level summary of agent performance
        """
        if traces is None:
            traces = self._execution_history[-limit:]

        if not traces:
            return {
                "patterns_identified": [],
                "improvement_suggestions": [],
                "strategy_recommendations": [],
                "tool_usage_insights": [],
                "overall_assessment": "No execution history available for reflection.",
            }

        # Build a compact trace summary for the LLM
        trace_summaries = []
        for t in traces:
            trace_summaries.append({
                "id": t.id,
                "context": t.context.value,
                "prompt": t.prompt[:200],
                "success": t.success,
                "confidence": round(t.confidence, 2),
                "tools_used": t.tools_used,
                "step_count": len(t.steps),
                "error": t.error[:150] if t.error else "",
            })

        traces_json = json.dumps(trace_summaries, indent=2)

        system_prompt = (
            "You are an agent performance analyst. Review execution traces and "
            "identify patterns, suggest improvements, and assess overall performance. "
            "Output ONLY valid JSON, no markdown wrapping."
        )
        user_prompt = (
            f"Analyze the following agent execution traces and provide a structured "
            f"assessment.\n\nExecution Traces:\n{traces_json}\n\n"
            f"Return a JSON object with:\n"
            f'  - patterns_identified: list of strings describing recurring patterns\n'
            f'  - improvement_suggestions: list of concrete, actionable suggestions\n'
            f'  - strategy_recommendations: list of strategy adjustments\n'
            f'  - tool_usage_insights: list of observations about tool effectiveness\n'
            f'  - overall_assessment: one-paragraph summary of agent performance\n'
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1536,
            )
            content = response.choices[0].message.content or "{}"
            reflection = json.loads(content)
            self._total_tokens_used += response.usage.total_tokens if response.usage else 0
            logger.debug(f"Agent {self.agent_id}: Reflection complete, "
                         f"{len(reflection.get('improvement_suggestions', []))} suggestions.")
            return reflection
        except Exception as e:
            logger.warning(f"Agent {self.agent_id}: LLM reflection failed ({e}).")
            return self._reflect_heuristic(traces)

    def _reflect_heuristic(self, traces: list[ExecutionTrace]) -> dict:
        """Heuristic fallback for trace reflection."""
        if not traces:
            return {
                "patterns_identified": [],
                "improvement_suggestions": [],
                "strategy_recommendations": [],
                "tool_usage_insights": [],
                "overall_assessment": "No data available.",
            }

        success_rate = sum(1 for t in traces if t.success) / max(len(traces), 1)
        patterns = []
        suggestions = []
        strategy_recs = []

        if success_rate < 0.5:
            patterns.append("High failure rate detected in recent executions")
            suggestions.append("Review recent failing traces for common error patterns")
            strategy_recs.append("Consider switching to a more thorough strategy")

        if success_rate > 0.8:
            patterns.append("Consistently high success rate in recent executions")

        # Tool usage analysis
        tool_counts = defaultdict(int)
        for t in traces:
            for tool in t.tools_used:
                tool_counts[tool] += 1
        most_used = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        tool_insights = [
            f"Tool '{tool}' used in {count}/{len(traces)} recent traces"
            for tool, count in most_used
        ]

        return {
            "patterns_identified": patterns,
            "improvement_suggestions": suggestions,
            "strategy_recommendations": strategy_recs,
            "tool_usage_insights": tool_insights,
            "overall_assessment": (
                f"Agent {self.agent_name} has a {success_rate:.0%} success rate "
                f"across {len(traces)} recent executions."
            ),
        }

    # ── Full Execution Pipeline ─────────────────────────

    async def run_pipeline(
        self,
        prompt: str,
        available_tools: list[str] | None = None,
        context: ExecutionContext = ExecutionContext.TASK,
    ) -> dict:
        """Orchestrate the full observe→analyze→plan→execute→reflect loop with
        LLM integration at each stage.

        This runs the complete agent execution lifecycle:
        1. Observe: Capture the task context
        2. Analyze: Deep LLM analysis of the prompt
        3. Plan: Decompose into sub-tasks with dependencies
        4. Execute: Record a structured execution plan
        5. Reflect: Generate insights from the execution

        Returns a comprehensive pipeline result dict.
        """
        tools = available_tools or ["web_search", "web_fetch", "read_file",
                                     "execute_code", "memory_search"]
        pipeline_start = time.time()

        # Stage 1: Observe
        self.set_state(AgentState.OBSERVING)
        trace = self.start_execution(context, prompt)
        observe_step = ExecutionStep(
            id=f"step-{uuid.uuid4().hex[:8]}",
            phase="observe",
            content=f"Observing task: {prompt[:200]}",
            elapsed_ms=0.0,
        )
        self.add_step(trace.id, observe_step)

        # Stage 2: Analyze
        self.set_state(AgentState.REASONING)
        analyze_start = time.time()
        analysis = await self.analyze(prompt)
        analyze_elapsed = (time.time() - analyze_start) * 1000
        analyze_step = ExecutionStep(
            id=f"step-{uuid.uuid4().hex[:8]}",
            phase="analyze",
            content=f"Task analysis: {analysis.get('task_type', 'unknown')} "
                    f"({analysis.get('complexity', 'unknown')} complexity)",
            confidence=0.8,
            elapsed_ms=analyze_elapsed,
            metadata={"analysis": analysis},
        )
        self.add_step(trace.id, analyze_step)

        # Stage 3: Plan
        plan_start = time.time()
        plan = await self.plan_sequence(prompt, tools)
        plan_elapsed = (time.time() - plan_start) * 1000
        plan_step = ExecutionStep(
            id=f"step-{uuid.uuid4().hex[:8]}",
            phase="plan",
            content=f"Plan: {len(plan.get('sub_tasks', []))} sub-tasks, "
                    f"{len(plan.get('parallel_groups', []))} parallel groups",
            confidence=0.75,
            elapsed_ms=plan_elapsed,
            metadata={"plan": plan},
        )
        self.add_step(trace.id, plan_step)

        # Stage 4: Execute (record strategy and tool plan)
        self.set_state(AgentState.EXECUTING)
        strategy = await self.select_strategy(prompt, tools)
        tool_sequence = self.plan_tool_sequence(prompt, tools)
        execute_step = ExecutionStep(
            id=f"step-{uuid.uuid4().hex[:8]}",
            phase="execute",
            content=f"Strategy: {strategy.get('strategy', 'balanced')}, "
                    f"Tool rounds: {len(tool_sequence)}",
            tool_calls=[t for round_tools in tool_sequence for t in round_tools],
            confidence=strategy.get("confidence", 0.7),
            elapsed_ms=0.0,
            metadata={
                "strategy": strategy,
                "tool_sequence": tool_sequence,
            },
        )
        self.add_step(trace.id, execute_step)

        # Update tool patterns and trace tracking
        trace.tools_used = execute_step.tool_calls
        self._total_tool_calls += len(execute_step.tool_calls)

        # Stage 5: Reflect
        self.set_state(AgentState.REFLECTING)
        reflection = await self.reflect([trace])
        reflect_step = ExecutionStep(
            id=f"step-{uuid.uuid4().hex[:8]}",
            phase="reflect",
            content=f"Reflection: {len(reflection.get('improvement_suggestions', []))} "
                    f"suggestions generated",
            confidence=0.6,
            elapsed_ms=0.0,
            metadata={"reflection": reflection},
        )
        self.add_step(trace.id, reflect_step)

        # Complete the trace
        self.complete_execution(
            trace.id,
            answer=f"Pipeline completed for: {prompt[:200]}",
            success=True,
            insights=reflection.get("improvement_suggestions", []),
        )

        # Update strategy mapping
        fingerprint = self.fingerprint_task(prompt)
        self._task_strategy_map[fingerprint] = strategy.get("strategy", "balanced")

        # Generate insights
        self.generate_insights()

        total_elapsed = (time.time() - pipeline_start) * 1000
        self.set_state(AgentState.IDLE)

        return {
            "trace_id": trace.id,
            "analysis": analysis,
            "plan": plan,
            "strategy": strategy,
            "tool_sequence": tool_sequence,
            "reflection": reflection,
            "total_elapsed_ms": round(total_elapsed, 1),
            "success": True,
        }

    # ── Confidence Calibration ──────────────────────────

    def calibrate_confidence(
        self,
        raw_confidence: float,
        strategy: str = "balanced",
    ) -> dict:
        """Calibrate a raw confidence score using Bayesian-like updating based on
        historical accuracy of the selected strategy.

        Returns a dict with:
          - raw_confidence: the original confidence value
          - calibrated_confidence: adjusted confidence after calibration
          - prior_success_rate: historical success rate for this strategy
          - calibration_factor: the multiplier applied
          - sample_size: number of historical samples used
          - is_reliable: whether the calibration is based on enough data
        """
        strategy_scores = self._strategy_scores.get(strategy, {
            "successes": 0, "failures": 0,
        })
        successes = strategy_scores["successes"]
        failures = strategy_scores["failures"]
        total = successes + failures

        if total < 3:
            # Not enough data for meaningful calibration
            return {
                "raw_confidence": raw_confidence,
                "calibrated_confidence": raw_confidence,
                "prior_success_rate": 0.5,
                "calibration_factor": 1.0,
                "sample_size": total,
                "is_reliable": False,
            }

        prior_rate = successes / max(total, 1)

        # Bayesian-like calibration: weighted blend of prior and raw confidence
        # As sample size grows, prior becomes more influential
        weight = min(total / 20.0, 0.5)  # cap at 0.5 so raw still has influence
        calibrated = raw_confidence * (1 - weight) + prior_rate * weight

        # Adjust: if historical rate is very different from raw, we pull harder
        delta = abs(raw_confidence - prior_rate)
        if delta > 0.3:
            calibrated = raw_confidence * 0.4 + prior_rate * 0.6

        calibration_factor = calibrated / max(raw_confidence, 0.01)

        return {
            "raw_confidence": raw_confidence,
            "calibrated_confidence": round(min(calibrated, 0.99), 3),
            "prior_success_rate": round(prior_rate, 3),
            "calibration_factor": round(calibration_factor, 3),
            "sample_size": total,
            "is_reliable": total >= 5,
        }

    # ── Strategy Selection with LLM Fallback ────────────

    async def select_strategy(
        self,
        prompt: str,
        available_tools: list[str] | None = None,
    ) -> dict:
        """Select the optimal execution strategy for a task.

        Uses task fingerprinting to match against historical outcomes first.
        For complex or unfamiliar tasks, delegates to the LLM for strategy
        recommendation. Falls back to heuristics for simple cases.
        """
        fingerprint = self.fingerprint_task(prompt)

        # Check if we have a learned strategy for this task pattern
        if fingerprint in self._task_strategy_map:
            learned_strategy = self._task_strategy_map[fingerprint]
            strategy_score = self._strategy_scores.get(learned_strategy, {})
            if strategy_score.get("successes", 0) > 0:
                calibrated = self.calibrate_confidence(
                    0.85, learned_strategy,
                )
                return {
                    "fingerprint": fingerprint,
                    "strategy": learned_strategy,
                    "source": "learned",
                    "confidence": calibrated["calibrated_confidence"],
                }

        # Heuristic-based strategy selection for simple cases
        prompt_lower = prompt.lower()
        word_count = len(prompt.split())

        # Determine if this warrants LLM-based strategy selection
        complex_signals = ["design", "implement", "optimize", "research", "refactor",
                           "architecture", "system", "debug complex", "migrate"]
        is_complex = (
            word_count > 100
            or any(s in prompt_lower for s in complex_signals)
            or "?" in prompt and word_count > 50
        )

        if is_complex:
            # Use LLM for complex strategy decisions
            return await self._select_strategy_llm(prompt, fingerprint)

        # Simple heuristic path
        strategy = "balanced"
        expert_signals = ["architecture", "system design", "security audit",
                          "performance optimization"]
        simple_signals = ["summarize", "translate", "calculate", "hello", "hi",
                          "thanks", "what is"]

        if any(s in prompt_lower for s in expert_signals):
            strategy = "tree_of_thought"
        elif any(s in prompt_lower for s in complex_signals):
            strategy = "decomposition"
        elif word_count > 500:
            strategy = "thorough"
        elif any(s in prompt_lower for s in simple_signals):
            strategy = "concise"

        calibrated = self.calibrate_confidence(0.7, strategy)

        return {
            "fingerprint": fingerprint,
            "strategy": strategy,
            "source": "heuristic",
            "confidence": calibrated["calibrated_confidence"],
        }

    async def _select_strategy_llm(
        self, prompt: str, fingerprint: str,
    ) -> dict:
        """Use the LLM to recommend a strategy for a complex task."""
        strategy_options = [
            "balanced — general-purpose step-by-step execution",
            "decomposition — break into sub-problems and solve independently",
            "tree_of_thought — explore multiple reasoning paths in parallel",
            "thorough — exhaustive analysis with multiple validation passes",
            "concise — minimal steps, direct answer",
            "reflexion — iterative self-correction with reflection at each step",
            "chain_of_thought — sequential reasoning with intermediate steps",
        ]
        strategies_text = "\n".join(f"  - {s}" for s in strategy_options)

        system_prompt = (
            "You are a strategy selection engine. Given a task, recommend the most "
            "appropriate execution strategy from the available options. Consider task "
            "complexity, domain, and required depth. Output ONLY valid JSON."
        )
        user_prompt = (
            f"Task:\n\"\"\"\n{prompt[:1000]}\n\"\"\"\n\n"
            f"Available strategies:\n{strategies_text}\n\n"
            f"Return JSON with:\n"
            f'  - strategy: the recommended strategy name (use the short form '
            f'before "—")\n'
            f'  - rationale: brief explanation of why this strategy fits\n'
            f'  - confidence: 0.0-1.0 estimate of this being the right choice\n'
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=512,
            )
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            self._total_tokens_used += response.usage.total_tokens if response.usage else 0

            strategy = result.get("strategy", "balanced")
            raw_conf = float(result.get("confidence", 0.75))
            calibrated = self.calibrate_confidence(raw_conf, strategy)

            logger.debug(f"Agent {self.agent_id}: LLM selected strategy '{strategy}' "
                         f"for {fingerprint} (rationale: {result.get('rationale', 'N/A')})")
            return {
                "fingerprint": fingerprint,
                "strategy": strategy,
                "source": "llm",
                "confidence": calibrated["calibrated_confidence"],
                "rationale": result.get("rationale", ""),
            }
        except Exception as e:
            logger.warning(f"Agent {self.agent_id}: LLM strategy selection failed "
                           f"({e}), falling back to heuristic.")
            return {
                "fingerprint": fingerprint,
                "strategy": "balanced",
                "source": "heuristic_fallback",
                "confidence": 0.6,
            }

    # ── Cross-Trace Analysis ────────────────────────────

    async def analyze_cross_trace(
        self,
        trace_ids: list[str] | None = None,
        limit: int = 20,
    ) -> dict:
        """Analyze patterns across multiple execution traces and generate
        meta-insights using the LLM.

        Args:
            trace_ids: Specific trace IDs to analyze. If None, uses recent history.
            limit: Max traces to include from history when trace_ids not provided.

        Returns a dict with:
          - meta_patterns: cross-trace patterns detected
          - emergent_behaviors: behaviors that emerge across multiple traces
          - failure_clusters: groupings of related failure modes
          - optimization_opportunities: areas for systematic improvement
          - trend_analysis: directional trends in performance over time
          - summary: human-readable synthesis of findings
        """
        if trace_ids:
            traces = [t for t in self._execution_history if t.id in trace_ids]
        else:
            traces = self._execution_history[-limit:]

        if len(traces) < 3:
            return {
                "meta_patterns": [],
                "emergent_behaviors": [],
                "failure_clusters": [],
                "optimization_opportunities": [],
                "trend_analysis": "Insufficient data for cross-trace analysis.",
                "summary": f"Only {len(traces)} traces available; need at least 3.",
            }

        # Build compact trace representations
        trace_data = []
        for t in traces:
            trace_data.append({
                "id": t.id,
                "context": t.context.value,
                "prompt": t.prompt[:150],
                "success": t.success,
                "confidence": round(t.confidence, 3),
                "tools_used": t.tools_used,
                "steps": len(t.steps),
                "time_ms": round(t.total_time_ms, 1),
                "error": t.error[:100] if t.error else "",
                "timestamp": t.timestamp,
            })

        traces_json = json.dumps(trace_data, indent=2)

        # Gather strategy statistics
        strategy_stats = {}
        for s_name, scores in self._strategy_scores.items():
            total = scores["successes"] + scores["failures"]
            if total > 0:
                strategy_stats[s_name] = {
                    "success_rate": round(scores["successes"] / max(total, 1), 2),
                    "total_uses": int(total),
                    "avg_time_ms": round(scores["avg_time"], 1),
                }

        system_prompt = (
            "You are a meta-analysis engine for agent execution traces. Identify "
            "cross-cutting patterns, emergent behaviors, failure clusters, and "
            "optimization opportunities across multiple executions. Output ONLY "
            "valid JSON, no markdown wrapping."
        )
        user_prompt = (
            f"Analyze the following set of {len(traces)} agent execution traces "
            f"for cross-trace patterns.\n\n"
            f"Strategy Performance:\n{json.dumps(strategy_stats, indent=2)}\n\n"
            f"Execution Traces:\n{traces_json}\n\n"
            f"Return a JSON object with:\n"
            f'  - meta_patterns: list of strings describing cross-trace patterns\n'
            f'  - emergent_behaviors: list of behaviors that appear across traces\n'
            f'  - failure_clusters: list of common failure groupings with descriptions\n'
            f'  - optimization_opportunities: list of systematic improvement areas\n'
            f'  - trend_analysis: description of performance trends over time\n'
            f'  - summary: concise one-paragraph synthesis of all findings\n'
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2048,
            )
            content = response.choices[0].message.content or "{}"
            cross_analysis = json.loads(content)
            self._total_tokens_used += response.usage.total_tokens if response.usage else 0

            # Store key findings as insights
            for pattern in cross_analysis.get("meta_patterns", []):
                if not any(i.content == pattern for i in self._insights):
                    self._insights.append(AgentInsight(
                        id=f"insight-{uuid.uuid4().hex[:8]}",
                        category="meta",
                        content=pattern,
                        confidence=0.7,
                        source_traces=[t["id"] for t in trace_data[:5]],
                    ))

            logger.debug(f"Agent {self.agent_id}: Cross-trace analysis complete, "
                         f"{len(cross_analysis.get('meta_patterns', []))} patterns found.")
            return cross_analysis
        except Exception as e:
            logger.warning(f"Agent {self.agent_id}: LLM cross-trace analysis "
                           f"failed ({e}).")
            return self._cross_trace_heuristic(traces, strategy_stats)

    def _cross_trace_heuristic(
        self,
        traces: list[ExecutionTrace],
        strategy_stats: dict,
    ) -> dict:
        """Heuristic fallback for cross-trace analysis."""
        success_rate = sum(1 for t in traces if t.success) / max(len(traces), 1)
        meta_patterns = []
        optimization_opportunities = []
        failure_clusters = []

        # Strategy-based patterns
        for s_name, stats in strategy_stats.items():
            if stats["total_uses"] >= 3:
                if stats["success_rate"] < 0.5:
                    meta_patterns.append(
                        f"Strategy '{s_name}' underperforming at "
                        f"{stats['success_rate']:.0%} success rate"
                    )
                    optimization_opportunities.append(
                        f"Review and tune strategy '{s_name}' or consider deprecation"
                    )
                elif stats["success_rate"] > 0.85:
                    meta_patterns.append(
                        f"Strategy '{s_name}' highly effective at "
                        f"{stats['success_rate']:.0%} success rate"
                    )

        # Time-based trend
        if len(traces) >= 5:
            first_half = traces[:len(traces) // 2]
            second_half = traces[len(traces) // 2:]
            first_rate = sum(1 for t in first_half if t.success) / max(len(first_half), 1)
            second_rate = sum(1 for t in second_half if t.success) / max(len(second_half), 1)
            if second_rate > first_rate + 0.1:
                meta_patterns.append("Success rate trending upward over time")
            elif second_rate < first_rate - 0.1:
                meta_patterns.append("Success rate trending downward — investigate")

        # Failure clustering
        failures = [t for t in traces if not t.success]
        if failures:
            error_messages = [t.error for t in failures if t.error]
            common_errors = set(error_messages)
            if len(common_errors) <= 3 and common_errors:
                failure_clusters.append(
                    f"{len(failures)} failures with {len(common_errors)} distinct "
                    f"error types"
                )

        return {
            "meta_patterns": meta_patterns,
            "emergent_behaviors": [],
            "failure_clusters": failure_clusters,
            "optimization_opportunities": optimization_opportunities,
            "trend_analysis": (
                f"Agent {self.agent_name} shows {success_rate:.0%} success rate "
                f"across {len(traces)} recent traces."
            ),
            "summary": (
                f"Cross-trace analysis of {len(traces)} executions: "
                f"{success_rate:.0%} success rate. "
                f"{len(meta_patterns)} meta-patterns identified. "
                f"{len(optimization_opportunities)} optimization areas found."
            ),
        }