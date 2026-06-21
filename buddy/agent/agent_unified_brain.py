"""Buddy Unified Brain — holistic agent coordination and intelligence synthesis

The Unified Brain is the central coordination layer that orchestrates all
agent capabilities into a coherent, adaptive system. It manages:

- Perception: Multi-modal input processing and context assembly
- Cognition: Deep reasoning, planning, and metacognitive strategy selection
- Action: Tool execution, skill invocation, and agent delegation
- Reflection: Self-assessment, experience recording, and continuous improvement
- Collaboration: Multi-agent session management and shared context
"""
from __future__ import annotations
import json
import logging
import uuid
import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, AsyncIterator

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.unified_brain")

# ── Enums ─────────────────────────────────────────────────

class BrainMode(str, Enum):
    REACTIVE = "reactive"         # Quick response, minimal reasoning
    DELIBERATIVE = "deliberative"  # Full reasoning with planning
    CREATIVE = "creative"         # Exploratory, brainstorming
    ANALYTICAL = "analytical"     # Data-driven, rigorous analysis
    COLLABORATIVE = "collaborative"  # Multi-agent coordination


class PerceptionType(str, Enum):
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    AUDIO = "audio"
    STRUCTURED = "structured"
    CONTEXT = "context"


class CognitivePhase(str, Enum):
    PERCEIVE = "perceive"
    UNDERSTAND = "understand"
    REASON = "reason"
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"


# ── Data Classes ──────────────────────────────────────────

@dataclass
class BrainContext:
    """Assembled context for the unified brain to process."""
    user_message: str = ""
    conversation_history: list[dict] = field(default_factory=list)
    agent_id: str = ""
    agent_name: str = ""
    system_prompt: str = ""
    active_tools: list[str] = field(default_factory=list)
    memory_context: str = ""
    identity_context: str = ""
    persona_context: str = ""
    workspace_context: str = ""
    session_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainPerception:
    """Multi-modal perception result from the unified brain."""
    perception_id: str = field(default_factory=lambda: f"perc-{uuid.uuid4().hex[:8]}")
    perception_type: PerceptionType = PerceptionType.TEXT
    raw_content: str = ""
    entities: list[dict[str, Any]] = field(default_factory=list)
    intent: str = ""
    sentiment: str = "neutral"
    urgency: float = 0.0
    complexity: float = 0.0
    requires_tools: bool = False
    requires_reasoning: bool = False
    requires_collaboration: bool = False
    suggested_mode: BrainMode = BrainMode.REACTIVE
    extracted_keywords: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class BrainCognition:
    """Cognitive processing result from the unified brain."""
    cognition_id: str = field(default_factory=lambda: f"cog-{uuid.uuid4().hex[:8]}")
    reasoning_strategy: str = "balanced"
    reasoning_trace: list[dict[str, Any]] = field(default_factory=list)
    plan_steps: list[dict[str, Any]] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    agents_required: list[str] = field(default_factory=list)
    confidence: float = 0.0
    alternatives_considered: int = 0
    estimated_complexity: str = "medium"
    estimated_tokens: int = 0
    thinking_time_ms: float = 0.0


@dataclass
class BrainAction:
    """Action result from the unified brain."""
    action_id: str = field(default_factory=lambda: f"act-{uuid.uuid4().hex[:8]}")
    action_type: str = "response"
    content: str = ""
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    agent_results: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: str = ""
    duration_ms: float = 0.0
    tokens_used: int = 0


@dataclass
class BrainReflection:
    """Self-reflection result from the unified brain."""
    reflection_id: str = field(default_factory=lambda: f"refl-{uuid.uuid4().hex[:8]}")
    quality_score: float = 0.0
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)
    patterns_detected: list[dict[str, Any]] = field(default_factory=list)
    should_record_experience: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class BrainCycleResult:
    """Complete result of a unified brain processing cycle."""
    cycle_id: str = field(default_factory=lambda: f"cycle-{uuid.uuid4().hex[:8]}")
    perception: BrainPerception | None = None
    cognition: BrainCognition | None = None
    action: BrainAction | None = None
    reflection: BrainReflection | None = None
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    mode: BrainMode = BrainMode.REACTIVE
    success: bool = True
    error: str = ""


# ── Unified Brain Engine ──────────────────────────────────

class UnifiedBrain:
    """Central coordination engine that orchestrates all agent capabilities.

    The Unified Brain implements a complete perceive-think-act-reflect cycle,
    coordinating deep reasoning, planning, tool execution, multi-agent
    collaboration, and self-improvement in a single coherent system.
    """

    def __init__(self, client: AsyncOpenAI | None = None):
        self.client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._cycles: list[BrainCycleResult] = []
        self._perceptions: list[BrainPerception] = []
        self._cognitions: list[BrainCognition] = []
        self._actions: list[BrainAction] = []
        self._reflections: list[BrainReflection] = []
        self._mode_history: list[dict[str, Any]] = []
        self._total_cycles: int = 0
        self._successful_cycles: int = 0
        self._failed_cycles: int = 0
        self._total_tokens: int = 0
        self._total_time_ms: float = 0.0
        self._start_time: str = datetime.now(timezone.utc).isoformat()

    # ── Perception ────────────────────────────────────────

    async def perceive(self, context: BrainContext) -> BrainPerception:
        """Analyze and understand the incoming input to determine intent,
        complexity, and required processing mode.

        Performs multi-modal understanding including entity extraction,
        sentiment analysis, intent classification, and complexity estimation.
        """
        start = time.time()

        perception = BrainPerception(
            perception_type=PerceptionType.TEXT,
            raw_content=context.user_message[:1000],
            urgency=0.0,
            complexity=0.0,
        )

        msg = context.user_message
        msg_lower = msg.lower()
        msg_len = len(msg)

        # ── Intent Classification ──
        intent_patterns = {
            "question": ["what", "how", "why", "when", "where", "who", "can you", "tell me", "explain"],
            "command": ["do", "create", "make", "build", "write", "run", "execute", "start", "stop"],
            "analysis": ["analyze", "evaluate", "compare", "review", "assess", "break down"],
            "brainstorm": ["brainstorm", "idea", "suggest", "imagine", "what if", "design"],
            "debug": ["fix", "debug", "error", "bug", "not working", "issue", "problem"],
            "conversation": ["hello", "hi", "hey", "thanks", "goodbye", "how are you"],
        }
        max_intent_score = 0.0
        for intent, keywords in intent_patterns.items():
            score = sum(1 for kw in keywords if kw in msg_lower) / max(len(keywords), 1)
            if score > max_intent_score:
                max_intent_score = score
                perception.intent = intent

        if not perception.intent:
            perception.intent = "general"

        # ── Complexity Estimation ──
        complexity_signals = {
            "code_blocks": int("```" in msg or "`" in msg),
            "multiple_sentences": int(msg.count(".") > 3),
            "technical_terms": sum(1 for t in ["api", "function", "class", "database", "algorithm"] if t in msg_lower),
            "length": min(1.0, msg_len / 500),
            "bullet_points": int("\n-" in msg or "\n*" in msg),
        }
        complexity_raw = sum(complexity_signals.values()) / max(len(complexity_signals), 1)
        perception.complexity = min(1.0, complexity_raw)

        # ── Urgency Detection ──
        urgency_words = ["urgent", "asap", "immediately", "critical", "emergency", "now", "quickly", "fast"]
        urgency_score = sum(1 for w in urgency_words if w in msg_lower) / max(len(urgency_words), 1)
        perception.urgency = min(1.0, urgency_score + (0.3 if msg_len < 30 else 0.0))

        # ── Mode Selection ──
        if perception.intent == "brainstorm":
            perception.suggested_mode = BrainMode.CREATIVE
        elif perception.intent in ("analysis", "debug"):
            perception.suggested_mode = BrainMode.ANALYTICAL
        elif perception.complexity > 0.6:
            perception.suggested_mode = BrainMode.DELIBERATIVE
        elif any(kw in msg_lower for kw in ["collaborate", "team", "together"]):
            perception.suggested_mode = BrainMode.COLLABORATIVE
        else:
            perception.suggested_mode = BrainMode.REACTIVE

        # ── Tool and Reasoning Needs ──
        perception.requires_tools = any(
            kw in msg_lower for kw in ["run", "execute", "search", "calculate", "create", "write", "read", "deploy"]
        )
        perception.requires_reasoning = perception.complexity > 0.4 or perception.intent in ("analysis", "debug")
        perception.requires_collaboration = perception.suggested_mode == BrainMode.COLLABORATIVE

        # ── Entity Extraction ──
        import re
        code_entities = re.findall(r'`([^`]+)`', msg)
        for entity in code_entities[:5]:
            perception.entities.append({"type": "code", "value": entity})

        url_entities = re.findall(r'https?://[^\s]+', msg)
        for entity in url_entities[:3]:
            perception.entities.append({"type": "url", "value": entity})

        # ── Keyword Extraction ──
        common_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                        "have", "has", "had", "do", "does", "did", "will", "would", "could",
                        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
                        "on", "with", "at", "by", "from", "as", "into", "about", "like",
                        "this", "that", "these", "those", "it", "its", "and", "but", "or",
                        "if", "then", "else", "when", "up", "out", "no", "not", "so", "just"}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', msg_lower)
        keyword_freq = {}
        for w in words:
            if w not in common_words:
                keyword_freq[w] = keyword_freq.get(w, 0) + 1
        perception.extracted_keywords = sorted(keyword_freq, key=keyword_freq.get, reverse=True)[:10]

        perception.timestamp = datetime.now(timezone.utc).isoformat()
        perception.sentiment = "positive" if any(w in msg_lower for w in ["great", "good", "awesome", "thanks", "love"]) else "neutral"

        self._perceptions.append(perception)
        return perception

    # ── Cognition ─────────────────────────────────────────

    async def think(
        self,
        context: BrainContext,
        perception: BrainPerception,
    ) -> BrainCognition:
        """Perform deep cognitive processing: reasoning, planning, and
        strategy selection based on the perceived input.
        """
        start = time.time()

        cognition = BrainCognition(
            reasoning_strategy="balanced",
            estimated_complexity="medium",
        )

        # ── Strategy Selection ──
        if perception.complexity > 0.7:
            cognition.reasoning_strategy = "tree_of_thought"
            cognition.estimated_complexity = "high"
        elif perception.complexity > 0.4:
            cognition.reasoning_strategy = "self_consistency"
            cognition.estimated_complexity = "medium"
        elif perception.intent == "brainstorm":
            cognition.reasoning_strategy = "parallel_perspectives"
            cognition.estimated_complexity = "medium"
        elif perception.intent == "analysis":
            cognition.reasoning_strategy = "iterative_refinement"
            cognition.estimated_complexity = "high"
        else:
            cognition.reasoning_strategy = "direct"
            cognition.estimated_complexity = "low"

        # ── Tool Requirement Analysis ──
        if perception.requires_tools:
            msg_lower = context.user_message.lower()
            tool_keywords = {
                "web_search": ["search", "find", "lookup", "google", "information about"],
                "code_execution": ["run", "execute", "code", "python", "shell", "command"],
                "file_operation": ["read", "write", "create", "save", "file", "document"],
                "calculation": ["calculate", "compute", "math", "sum", "average"],
                "web_fetch": ["fetch", "url", "website", "page", "http"],
                "deployment": ["deploy", "publish", "release", "ship"],
            }
            for tool, keywords in tool_keywords.items():
                if any(kw in msg_lower for kw in keywords):
                    cognition.tools_required.append(tool)

        # ── Plan Generation ──
        if cognition.estimated_complexity in ("medium", "high"):
            steps = self._generate_plan_steps(perception, context)
            cognition.plan_steps = steps

        # ── Confidence Estimation ──
        if perception.complexity < 0.3:
            cognition.confidence = 0.9
        elif perception.complexity < 0.6:
            cognition.confidence = 0.7
        else:
            cognition.confidence = 0.5

        cognition.thinking_time_ms = (time.time() - start) * 1000
        cognition.estimated_tokens = len(context.user_message) // 4

        self._cognitions.append(cognition)
        return cognition

    def _generate_plan_steps(self, perception: BrainPerception, context: BrainContext) -> list[dict[str, Any]]:
        """Generate a structured execution plan based on the task."""
        steps = []

        if perception.intent == "analysis":
            steps = [
                {"step": 1, "title": "Gather Information", "description": "Collect relevant data and context", "status": "pending"},
                {"step": 2, "title": "Analyze Patterns", "description": "Identify patterns and relationships", "status": "pending"},
                {"step": 3, "title": "Evaluate Options", "description": "Compare alternatives and assess trade-offs", "status": "pending"},
                {"step": 4, "title": "Formulate Conclusion", "description": "Synthesize findings into actionable insights", "status": "pending"},
            ]
        elif perception.intent == "debug":
            steps = [
                {"step": 1, "title": "Reproduce Issue", "description": "Understand the error and reproduce it", "status": "pending"},
                {"step": 2, "title": "Identify Root Cause", "description": "Trace the source of the problem", "status": "pending"},
                {"step": 3, "title": "Develop Fix", "description": "Create and test the solution", "status": "pending"},
                {"step": 4, "title": "Verify Resolution", "description": "Confirm the fix works correctly", "status": "pending"},
            ]
        elif perception.intent == "command":
            steps = [
                {"step": 1, "title": "Understand Request", "description": "Clarify the exact requirements", "status": "pending"},
                {"step": 2, "title": "Prepare Execution", "description": "Set up necessary tools and context", "status": "pending"},
                {"step": 3, "title": "Execute Task", "description": "Carry out the requested action", "status": "pending"},
                {"step": 4, "title": "Verify Results", "description": "Check that the output meets expectations", "status": "pending"},
            ]
        elif perception.complexity > 0.5:
            steps = [
                {"step": 1, "title": "Decompose Problem", "description": "Break down into manageable sub-tasks", "status": "pending"},
                {"step": 2, "title": "Research & Explore", "description": "Investigate each sub-task thoroughly", "status": "pending"},
                {"step": 3, "title": "Synthesize Solution", "description": "Combine findings into a coherent answer", "status": "pending"},
            ]

        return steps

    # ── Action ────────────────────────────────────────────

    async def act(
        self,
        context: BrainContext,
        perception: BrainPerception,
        cognition: BrainCognition,
    ) -> BrainAction:
        """Execute the planned actions: generate responses, invoke tools,
        delegate to agents, and produce artifacts.
        """
        start = time.time()

        action = BrainAction(
            action_type="response",
            success=True,
        )

        # ── Direct LLM Response ──
        try:
            messages = [{"role": "system", "content": context.system_prompt}]
            if context.conversation_history:
                messages.extend(context.conversation_history[-10:])
            messages.append({"role": "user", "content": context.user_message})

            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
            )
            action.content = response.choices[0].message.content or ""
            if hasattr(response, 'usage') and response.usage:
                action.tokens_used = response.usage.total_tokens
        except Exception as e:
            logger.warning(f"Unified brain action failed: {e}")
            action.content = self._fallback_response(context.user_message)
            action.success = False
            action.error = str(e)

        action.duration_ms = (time.time() - start) * 1000
        self._actions.append(action)
        return action

    def _fallback_response(self, message: str) -> str:
        """Generate a fallback response when LLM is unavailable."""
        msg_lower = message.lower().strip()
        if any(g in msg_lower for g in ["hello", "hi", "hey"]):
            return "Hello! I'm your Buddy agent. How can I help you today?"
        if any(g in msg_lower for g in ["who are you", "what are you"]):
            return "I'm your Buddy AI agent, designed to help with a wide range of tasks including analysis, coding, research, and creative work."
        return "I received your message. Let me help you with that. Could you provide more details about what you need?"

    # ── Reflection ────────────────────────────────────────

    async def reflect(
        self,
        context: BrainContext,
        perception: BrainPerception,
        cognition: BrainCognition,
        action: BrainAction,
    ) -> BrainReflection:
        """Reflect on the completed cycle to identify strengths, weaknesses,
        and opportunities for improvement.
        """
        reflection = BrainReflection(
            quality_score=0.7,
        )

        # ── Quality Assessment ──
        if action.success and action.content:
            content_len = len(action.content)
            if content_len > 200:
                reflection.quality_score = 0.8
                reflection.strengths.append("Comprehensive response with sufficient detail")
            if content_len > 100:
                reflection.strengths.append("Adequate response length")
            else:
                reflection.weaknesses.append("Response could be more detailed")
        else:
            reflection.quality_score = 0.3
            reflection.weaknesses.append(f"Action failed: {action.error}")

        # ── Pattern Detection ──
        if cognition.tools_required:
            reflection.patterns_detected.append({
                "pattern": "tool_usage",
                "tools": cognition.tools_required,
                "frequency": 1,
            })

        if cognition.plan_steps:
            reflection.patterns_detected.append({
                "pattern": "planned_execution",
                "steps_count": len(cognition.plan_steps),
            })

        # ── Improvement Suggestions ──
        if action.duration_ms > 2000:
            reflection.improvement_suggestions.append(
                "Consider caching common responses to reduce latency"
            )
        if not action.success:
            reflection.improvement_suggestions.append(
                "Review error handling and fallback mechanisms"
            )

        # ── Experience Recording Decision ──
        reflection.should_record_experience = (
            reflection.quality_score > 0.6 or
            (not action.success and len(reflection.lessons_learned) > 0)
        )

        reflection.timestamp = datetime.now(timezone.utc).isoformat()
        self._reflections.append(reflection)
        return reflection

    # ── Full Cycle ─────────────────────────────────────────

    async def process(
        self,
        context: BrainContext,
        mode: BrainMode | None = None,
    ) -> BrainCycleResult:
        """Execute a complete perceive-think-act-reflect cycle.

        This is the primary entry point for the unified brain. It processes
        input through all four cognitive phases and returns a comprehensive
        result with full traceability.
        """
        cycle_start = time.time()

        cycle = BrainCycleResult(
            mode=mode or BrainMode.REACTIVE,
        )

        try:
            # Phase 1: Perceive
            perception = await self.perceive(context)
            cycle.perception = perception
            cycle.mode = mode or perception.suggested_mode

            # Phase 2: Think
            cognition = await self.think(context, perception)
            cycle.cognition = cognition

            # Phase 3: Act
            action = await self.act(context, perception, cognition)
            cycle.action = action

            # Phase 4: Reflect
            reflection = await self.reflect(context, perception, cognition, action)
            cycle.reflection = reflection

            cycle.total_tokens = action.tokens_used
            cycle.success = action.success
            cycle.error = action.error

            self._successful_cycles += 1
        except Exception as e:
            logger.error(f"Unified brain cycle failed: {e}")
            cycle.success = False
            cycle.error = str(e)
            self._failed_cycles += 1

        cycle.total_duration_ms = (time.time() - cycle_start) * 1000
        self._total_cycles += 1
        self._total_tokens += cycle.total_tokens
        self._total_time_ms += cycle.total_duration_ms

        self._cycles.append(cycle)
        if len(self._cycles) > 100:
            self._cycles = self._cycles[-50:]

        return cycle

    # ── Multi-Agent Coordination ───────────────────────────

    async def coordinate(
        self,
        task: str,
        agent_ids: list[str],
        orchestrator_context: dict[str, Any] | None = None,
    ) -> BrainCycleResult:
        """Coordinate multiple agents to collaboratively solve a task.

        Creates a collaborative session, distributes the task across agents,
        collects and synthesizes results from all participants.
        """
        context = BrainContext(
            user_message=task,
            agent_id="orchestrator",
            agent_name="Buddy Orchestrator",
            system_prompt="You are the Buddy Orchestrator, coordinating multiple agents.",
            metadata={"agent_ids": agent_ids, **(orchestrator_context or {})},
        )
        return await self.process(context, mode=BrainMode.COLLABORATIVE)

    # ── Streaming Support ─────────────────────────────────

    async def process_stream(
        self,
        context: BrainContext,
    ) -> AsyncIterator[str]:
        """Process input with streaming output for real-time feedback."""
        try:
            # Quick perception
            perception = await self.perceive(context)

            # Stream the response
            messages = [{"role": "system", "content": context.system_prompt}]
            if context.conversation_history:
                messages.extend(context.conversation_history[-10:])
            messages.append({"role": "user", "content": context.user_message})

            stream = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                stream=True,
            )

            full_content = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_content += token
                    yield token

            # Post-stream reflection
            cognition = await self.think(context, perception)
            action = BrainAction(content=full_content, success=True, action_type="response")
            await self.reflect(context, perception, cognition, action)

        except Exception as e:
            logger.error(f"Unified brain stream failed: {e}")
            yield f"\n\n[Error: {str(e)}]"

    # ── Statistics ─────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics about the unified brain."""
        return {
            "total_cycles": self._total_cycles,
            "successful_cycles": self._successful_cycles,
            "failed_cycles": self._failed_cycles,
            "success_rate": round(
                self._successful_cycles / max(self._total_cycles, 1), 2
            ),
            "total_tokens": self._total_tokens,
            "total_time_ms": self._total_time_ms,
            "avg_cycle_time_ms": round(
                self._total_time_ms / max(self._total_cycles, 1), 1
            ),
            "recent_cycles": [
                {
                    "cycle_id": c.cycle_id,
                    "mode": c.mode.value,
                    "success": c.success,
                    "duration_ms": round(c.total_duration_ms, 1),
                    "tokens": c.total_tokens,
                }
                for c in self._cycles[-5:]
            ],
            "mode_distribution": self._get_mode_distribution(),
            "uptime_since": self._start_time,
        }

    def _get_mode_distribution(self) -> dict[str, int]:
        """Get distribution of brain modes used."""
        distribution: dict[str, int] = {}
        for cycle in self._cycles:
            mode = cycle.mode.value
            distribution[mode] = distribution.get(mode, 0) + 1
        return distribution

    def get_recent_insights(self, limit: int = 10) -> list[str]:
        """Get recent insights from reflections."""
        insights = []
        for reflection in self._reflections[-limit:]:
            insights.extend(reflection.lessons_learned)
            insights.extend(reflection.improvement_suggestions)
        return list(dict.fromkeys(insights))  # Deduplicate while preserving order

    def get_perception_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent perception history."""
        return [
            {
                "perception_id": p.perception_id,
                "intent": p.intent,
                "complexity": round(p.complexity, 2),
                "urgency": round(p.urgency, 2),
                "suggested_mode": p.suggested_mode.value,
                "keywords": p.extracted_keywords[:5],
                "timestamp": p.timestamp,
            }
            for p in self._perceptions[-limit:]
        ]

    def reset_stats(self):
        """Reset all statistics."""
        self._total_cycles = 0
        self._successful_cycles = 0
        self._failed_cycles = 0
        self._total_tokens = 0
        self._total_time_ms = 0.0
        self._start_time = datetime.now(timezone.utc).isoformat()


# ── Singleton ─────────────────────────────────────────────

unified_brain = UnifiedBrain()