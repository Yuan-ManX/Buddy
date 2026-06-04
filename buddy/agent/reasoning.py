"""Buddy Reasoning Loop — chain-of-thought execution with self-reflection

Implements a structured reasoning pipeline: Observe → Think → Act → Reflect.
The agent cycles through this loop, using tool calls and self-critique to
arrive at accurate, well-reasoned responses.
"""
from __future__ import annotations
import json
import logging
import asyncio
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.reasoning")


class ReasoningPhase(str, Enum):
    OBSERVE = "observe"     # Gather context, understand the task
    THINK = "think"         # Analyze, break down, plan approach
    ACT = "act"             # Execute tools, generate response
    REFLECT = "reflect"     # Self-critique, verify correctness


class ReasoningStyle(str, Enum):
    CONCISE = "concise"           # Minimal reasoning, direct answers
    BALANCED = "balanced"         # Standard reasoning with key steps
    THOROUGH = "thorough"         # Detailed step-by-step with verification


@dataclass
class ReasoningStep:
    phase: ReasoningPhase
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    confidence: float = 0.5
    elapsed_ms: float = 0.0


@dataclass
class ReasoningTrace:
    """Complete trace of a reasoning cycle."""
    steps: list[ReasoningStep] = field(default_factory=list)
    final_answer: str = ""
    total_tokens: int = 0
    total_time_ms: float = 0.0
    success: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "steps": [
                {
                    "phase": s.phase.value,
                    "content": s.content[:500],
                    "tool_calls": [tc.get("function", {}).get("name", "") for tc in s.tool_calls],
                    "confidence": s.confidence,
                    "elapsed_ms": s.elapsed_ms,
                }
                for s in self.steps
            ],
            "final_answer": self.final_answer[:500],
            "total_tokens": self.total_tokens,
            "total_time_ms": self.total_time_ms,
            "success": self.success,
        }


class ReasoningLoop:
    """Structured reasoning loop with chain-of-thought and self-critique."""

    MAX_TOOL_ROUNDS = 8
    REFLECTION_PROMPT = """Review your response for:
1. Factual accuracy — are all claims verifiable?
2. Completeness — did you address all parts of the question?
3. Clarity — is the response easy to understand?
4. Safety — are there any potential issues to flag?

If issues found, provide a corrected response. Otherwise, confirm the answer."""

    def __init__(
        self,
        style: ReasoningStyle = ReasoningStyle.BALANCED,
        client: AsyncOpenAI | None = None,
    ):
        self.style = style
        self.client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._trace_store: list[ReasoningTrace] = []

    async def execute(
        self,
        system_prompt: str,
        user_message: str,
        tool_schemas: list[dict] | None = None,
        tool_executor: Any = None,
        model: str = "gpt-4o-mini",
    ) -> ReasoningTrace:
        """Execute a complete reasoning cycle."""
        start = time.time()
        trace = ReasoningTrace()
        total_tokens = 0

        messages: list[dict] = [
            {"role": "system", "content": self._build_reasoning_prompt(system_prompt)},
            {"role": "user", "content": user_message},
        ]

        try:
            # ── Phase 1: OBSERVE ──
            phase_start = time.time()
            observe_step = await self._observe(messages, model)
            observe_step.elapsed_ms = (time.time() - phase_start) * 1000
            trace.steps.append(observe_step)
            if observe_step.content:
                messages.append({"role": "assistant", "content": f"[Observation] {observe_step.content}"})

            # ── Phase 2: THINK ──
            phase_start = time.time()
            think_step = await self._think(messages, model)
            think_step.elapsed_ms = (time.time() - phase_start) * 1000
            trace.steps.append(think_step)

            # ── Phase 3: ACT (with tool-calling loop) ──
            phase_start = time.time()
            act_result, act_tokens = await self._act_with_tools(
                messages, tool_schemas, tool_executor, model
            )
            total_tokens += act_tokens
            trace.steps.append(ReasoningStep(
                phase=ReasoningPhase.ACT,
                content=act_result,
                elapsed_ms=(time.time() - phase_start) * 1000,
            ))

            # ── Phase 4: REFLECT ──
            if self.style == ReasoningStyle.THOROUGH:
                phase_start = time.time()
                reflect_step = await self._reflect(messages, act_result, model)
                reflect_step.elapsed_ms = (time.time() - phase_start) * 1000
                trace.steps.append(reflect_step)
                trace.final_answer = reflect_step.content or act_result
            else:
                trace.final_answer = act_result

        except Exception as e:
            logger.error(f"Reasoning loop error: {e}")
            trace.success = False
            trace.error = str(e)
            trace.final_answer = f"I encountered an error while reasoning: {str(e)}"

        trace.total_time_ms = (time.time() - start) * 1000
        trace.total_tokens = total_tokens
        self._trace_store.append(trace)
        if len(self._trace_store) > 200:
            self._trace_store = self._trace_store[-100:]

        return trace

    async def execute_streaming(
        self,
        system_prompt: str,
        user_message: str,
        tool_schemas: list[dict] | None = None,
        tool_executor: Any = None,
        model: str = "gpt-4o-mini",
    ) -> AsyncIterator[dict]:
        """Execute reasoning with streaming phase output."""
        start = time.time()

        # Yield phase markers before executing
        yield {"type": "phase", "phase": "observe", "content": "Analyzing request..."}
        yield {"type": "phase", "phase": "think", "content": "Planning approach..."}

        # Execute full reasoning cycle
        trace = await self.execute(system_prompt, user_message, tool_schemas, tool_executor, model)

        # Yield intermediate steps
        for step in trace.steps:
            yield {
                "type": "step",
                "phase": step.phase.value,
                "content": step.content,
                "confidence": step.confidence,
                "elapsed_ms": step.elapsed_ms,
            }

        # Yield final answer as tokens
        yield {"type": "phase", "phase": "act", "content": "Generating response..."}
        for char in trace.final_answer:
            yield {
                "type": "token",
                "content": char,
                "step": "final",
            }

        yield {
            "type": "trace",
            "trace": trace.to_dict(),
        }

        yield {"type": "done"}

    async def _observe(self, messages: list[dict], model: str) -> ReasoningStep:
        """Phase 1: Observe and understand the task."""
        if self.style == ReasoningStyle.CONCISE:
            return ReasoningStep(phase=ReasoningPhase.OBSERVE, content="")

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages + [{
                    "role": "system",
                    "content": "Analyze the user's request. Identify: 1) Core intent 2) Required information 3) Constraints. Be brief."
                }],
                max_tokens=300,
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            return ReasoningStep(
                phase=ReasoningPhase.OBSERVE,
                content=content.strip(),
                confidence=0.9,
            )
        except Exception as e:
            logger.debug(f"Observe phase skipped: {e}")
            return ReasoningStep(phase=ReasoningPhase.OBSERVE, content="")

    async def _think(self, messages: list[dict], model: str) -> ReasoningStep:
        """Phase 2: Think through the problem."""
        if self.style == ReasoningStyle.CONCISE:
            return ReasoningStep(phase=ReasoningPhase.THINK, content="")

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages + [{
                    "role": "system",
                    "content": (
                        "Think step by step. Outline your approach:\n"
                        "1. What do I know?\n"
                        "2. What do I need to find out?\n"
                        "3. What tools might help?\n"
                        "4. What's my plan?\n\n"
                        "Be concise but thorough."
                    ),
                }],
                max_tokens=500,
                temperature=0.5,
            )
            content = response.choices[0].message.content or ""
            return ReasoningStep(
                phase=ReasoningPhase.THINK,
                content=content.strip(),
                confidence=0.8,
            )
        except Exception as e:
            logger.debug(f"Think phase skipped: {e}")
            return ReasoningStep(phase=ReasoningPhase.THINK, content="")

    async def _act_with_tools(
        self,
        messages: list[dict],
        tool_schemas: list[dict] | None,
        tool_executor: Any,
        model: str,
    ) -> tuple[str, int]:
        """Phase 3: Act — generate response, potentially using tools."""
        total_tokens = 0
        current_messages = list(messages)
        tool_rounds = 0

        while tool_rounds < self.MAX_TOOL_ROUNDS:
            kwargs: dict = {
                "model": model,
                "messages": current_messages,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
            if tool_schemas and tool_executor:
                kwargs["tools"] = tool_schemas
                kwargs["tool_choice"] = "auto"

            try:
                response = await self.client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                if response.usage:
                    total_tokens += response.usage.total_tokens

                # Check for tool calls
                if choice.message.tool_calls and tool_executor:
                    current_messages.append({
                        "role": "assistant",
                        "content": choice.message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in choice.message.tool_calls
                        ],
                    })

                    for tc in choice.message.tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            args = {}

                        result = await tool_executor(tc.function.name, args)
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result.output if hasattr(result, 'output') else str(result),
                        })
                        logger.info(f"Tool call: {tc.function.name} -> {'OK' if result.success else 'ERR' if hasattr(result, 'success') else 'done'}")

                    tool_rounds += 1
                    continue

                # No tool calls — final answer
                return choice.message.content or "", total_tokens

            except Exception as e:
                logger.warning(f"LLM call in act phase: {e}")
                return f"I encountered an issue generating a response: {str(e)}", total_tokens

        return "I've completed multiple tool interactions. Please review the findings above.", total_tokens

    async def _reflect(
        self,
        messages: list[dict],
        answer: str,
        model: str,
    ) -> ReasoningStep:
        """Phase 4: Self-reflect on the answer."""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages + [
                    {"role": "assistant", "content": answer},
                    {"role": "user", "content": self.REFLECTION_PROMPT},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            return ReasoningStep(
                phase=ReasoningPhase.REFLECT,
                content=content.strip(),
                confidence=0.7,
            )
        except Exception as e:
            logger.debug(f"Reflect phase skipped: {e}")
            return ReasoningStep(phase=ReasoningPhase.REFLECT, content="Self-reflection not available.")

    def _build_reasoning_prompt(self, base_prompt: str) -> str:
        """Build the system prompt with reasoning instructions."""
        style_instructions = {
            ReasoningStyle.CONCISE: "Provide direct, concise answers. Skip explanation unless asked.",
            ReasoningStyle.BALANCED: (
                "Think through problems carefully. Use tools when helpful. "
                "Explain your reasoning in key steps, but be concise."
            ),
            ReasoningStyle.THOROUGH: (
                "Reason step by step through every problem. Break complex tasks into subtasks. "
                "Verify your work. Use tools proactively. Explain your full reasoning."
            ),
        }

        return f"""{base_prompt}

## Reasoning Protocol
{style_instructions[self.style]}

When responding:
- If uncertain, say so rather than guessing
- Use available tools to gather information before answering
- Structure complex responses with clear sections
- Quote sources when using external information"""

    def get_recent_traces(self, limit: int = 10) -> list[dict]:
        return [t.to_dict() for t in self._trace_store[-limit:]]

    def get_stats(self) -> dict:
        total = len(self._trace_store)
        successful = sum(1 for t in self._trace_store if t.success)
        avg_time = sum(t.total_time_ms for t in self._trace_store) / max(total, 1)
        return {
            "total_traces": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": f"{(successful / max(total, 1) * 100):.1f}%",
            "avg_time_ms": round(avg_time, 0),
            "style": self.style.value,
        }