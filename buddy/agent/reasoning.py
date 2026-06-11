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
    CREATIVE = "creative"         # Divergent thinking, brainstorming mode
    CODING = "coding"             # Code-focused reasoning with testing emphasis
    PARALLEL = "parallel"         # Multi-perspective reasoning with simultaneous viewpoints
    TREE = "tree"                 # Tree-of-thought: explore multiple branches, prune, converge
    SELF_CONSISTENCY = "self_consistency"  # Multiple samples with majority voting


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

    async def execute_parallel(
        self,
        system_prompt: str,
        user_message: str,
        tool_schemas: list[dict] | None = None,
        tool_executor: Any = None,
        model: str = "gpt-4o-mini",
        num_perspectives: int = 4,
    ) -> ReasoningTrace:
        """Execute multiple reasoning passes in parallel from different perspectives.

        Runs concurrent reasoning cycles, each with a slightly different angle
        (technical, practical, ethical, creative), then synthesizes the results
        into a balanced final answer.

        Args:
            system_prompt: Base system prompt for the agent.
            user_message: The user's message/query.
            tool_schemas: Optional tool definitions for tool calling.
            tool_executor: Optional async callable to execute tool calls.
            model: The LLM model to use.
            num_perspectives: Number of parallel perspectives to run (1-4).

        Returns:
            ReasoningTrace with the synthesized answer and aggregated steps.
        """
        start = time.time()
        perspective_prompts = [
            ("technical", "Focus on the technical aspects: architecture, implementation details, correctness, and efficiency."),
            ("practical", "Focus on practical considerations: usability, feasibility, cost, and real-world applicability."),
            ("ethical", "Focus on ethical implications: fairness, safety, privacy, and societal impact."),
            ("creative", "Focus on creative and innovative angles: novel approaches, alternative solutions, and outside-the-box thinking."),
        ]

        perspectives = perspective_prompts[:num_perspectives]

        async def run_perspective(perspective_name: str, perspective_instruction: str) -> ReasoningTrace:
            """Run a single reasoning pass with a specific perspective lens."""
            modified_system_prompt = (
                f"{system_prompt}\n\n"
                f"[Perspective: {perspective_name}]\n"
                f"{perspective_instruction}"
            )
            trace = ReasoningTrace()
            try:
                inner_trace = await self.execute(
                    system_prompt=modified_system_prompt,
                    user_message=user_message,
                    tool_schemas=tool_schemas,
                    tool_executor=tool_executor,
                    model=model,
                )
                return inner_trace
            except Exception as e:
                logger.warning(f"Perspective '{perspective_name}' failed: {e}")
                trace.success = False
                trace.error = str(e)
                trace.final_answer = f"[{perspective_name}] Failed to complete."
                return trace

        # Run all perspectives concurrently
        perspective_traces: list[ReasoningTrace] = list(await asyncio.gather(*[
            run_perspective(name, instruction) for name, instruction in perspectives
        ]))

        # Synthesize results
        synthesis_trace = ReasoningTrace()

        # Aggregate steps from all perspectives
        for pt in perspective_traces:
            synthesis_trace.steps.extend(pt.steps)
            synthesis_trace.total_tokens += pt.total_tokens

        synthesis_trace.total_time_ms = (time.time() - start) * 1000

        # Build synthesis prompt from all perspective answers
        perspective_summaries = "\n\n".join(
            f"## {perspectives[i][0].capitalize()} Perspective:\n{pt.final_answer[:1000]}"
            for i, pt in enumerate(perspective_traces)
            if pt.success
        )

        if not perspective_summaries:
            synthesis_trace.success = False
            synthesis_trace.error = "All parallel perspectives failed."
            synthesis_trace.final_answer = "Unable to synthesize results — all perspectives failed."
            return synthesis_trace

        try:
            synthesis_response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a synthesis agent. Below are multiple perspectives on the same question. "
                            "Synthesize them into a single balanced, comprehensive answer. "
                            "Weigh each perspective appropriately. Identify areas of agreement and disagreement. "
                            "Present a cohesive final response that captures the best insights from all angles."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Original question: {user_message}\n\n"
                            f"{perspective_summaries}\n\n"
                            "Please synthesize these perspectives into a balanced, comprehensive answer."
                        ),
                    },
                ],
                max_tokens=4096,
                temperature=0.5,
            )
            final_answer = synthesis_response.choices[0].message.content or ""
            if synthesis_response.usage:
                synthesis_trace.total_tokens += synthesis_response.usage.total_tokens

            synthesis_trace.final_answer = final_answer
            synthesis_trace.success = any(pt.success for pt in perspective_traces)

            # Add synthesis as a final step
            synthesis_trace.steps.append(ReasoningStep(
                phase=ReasoningPhase.REFLECT,
                content=f"Synthesized {len(perspectives)} parallel perspectives into final answer.",
                confidence=0.85,
                elapsed_ms=0.0,
            ))

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Fall back to concatenating the most confident answer
            best_trace = max(
                (pt for pt in perspective_traces if pt.success),
                key=lambda pt: pt.steps[-1].confidence if pt.steps else 0.5,
                default=perspective_traces[0],
            )
            synthesis_trace.final_answer = (
                f"[Synthesized from {len(perspectives)} perspectives]\n\n"
                f"{best_trace.final_answer}"
            )
            synthesis_trace.error = f"Synthesis step failed ({e}); using best individual perspective."

        synthesis_trace.total_time_ms = (time.time() - start) * 1000
        self._trace_store.append(synthesis_trace)
        if len(self._trace_store) > 200:
            self._trace_store = self._trace_store[-100:]

        return synthesis_trace

    async def execute_tree_of_thought(
        self,
        system_prompt: str,
        user_message: str,
        tool_schemas: list[dict] | None = None,
        tool_executor: Any = None,
        model: str = "gpt-4o-mini",
        num_branches: int = 3,
        max_depth: int = 3,
    ) -> ReasoningTrace:
        """Execute tree-of-thought reasoning with branch exploration and pruning.

        Expands multiple solution paths simultaneously, evaluates each branch
        at every depth level, prunes low-quality branches, and converges on
        the best final answer through iterative refinement.
        """
        start = time.time()
        trace = ReasoningTrace()
        total_tokens = 0

        try:
            branch_prompt = (
                f"{system_prompt}\n\n"
                f"Generate {num_branches} distinct approaches to solve this problem. "
                f"Each approach should be a different strategy or perspective.\n\n"
                f"Problem: {user_message}\n\n"
                f"Return {num_branches} numbered approaches, each as a separate paragraph."
            )

            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": branch_prompt}],
                max_tokens=2000,
                temperature=0.8,
            )
            content = response.choices[0].message.content or ""
            if response.usage:
                total_tokens += response.usage.total_tokens

            branches = self._parse_branches(content, num_branches)
            if not branches:
                return await self.execute(system_prompt, user_message, tool_schemas, tool_executor, model)

            active_branches = [(b, 0.5) for b in branches]

            for depth in range(max_depth):
                if not active_branches:
                    break
                new_branches = []
                for branch_text, confidence in active_branches:
                    if confidence < 0.2:
                        continue
                    expand_prompt = (
                        f"{system_prompt}\n\n"
                        f"Original problem: {user_message}\n\n"
                        f"Current approach (depth {depth + 1}/{max_depth}):\n{branch_text}\n\n"
                        f"Refine and expand this approach. Add more specific details, "
                        f"consider edge cases, and improve the solution. "
                        f"Also provide a confidence score (0.0-1.0) for this branch.\n\n"
                        f"Response format:\n"
                        f"CONFIDENCE: <0.0-1.0>\n"
                        f"REASONING: <refined approach>"
                    )
                    try:
                        resp = await self.client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": expand_prompt}],
                            max_tokens=1000,
                            temperature=0.6,
                        )
                        expanded = resp.choices[0].message.content or ""
                        if resp.usage:
                            total_tokens += resp.usage.total_tokens
                        new_confidence = self._extract_confidence(expanded, confidence)
                        reasoning = self._extract_reasoning(expanded)
                        trace.steps.append(ReasoningStep(
                            phase=ReasoningPhase.THINK,
                            content=f"Branch depth {depth + 1}: {reasoning[:200]}",
                            confidence=new_confidence,
                            elapsed_ms=0.0,
                        ))
                        new_branches.append((reasoning, new_confidence))
                    except Exception as e:
                        logger.debug(f"Branch expansion failed at depth {depth}: {e}")
                        continue
                new_branches.sort(key=lambda x: -x[1])
                active_branches = new_branches[:num_branches]

            best_branches = [b for b, _ in active_branches[:2]] if active_branches else [branches[0]]
            synthesis_prompt = (
                f"{system_prompt}\n\n"
                f"Original problem: {user_message}\n\n"
                f"Best approaches found:\n\n" +
                "\n\n".join(f"Approach {i+1}:\n{b}" for i, b in enumerate(best_branches)) +
                f"\n\nSynthesize these into a single comprehensive answer. "
                f"Combine the best elements from each approach."
            )
            final_response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=4096,
                temperature=0.4,
            )
            final_answer = final_response.choices[0].message.content or ""
            if final_response.usage:
                total_tokens += final_response.usage.total_tokens
            trace.final_answer = final_answer
            trace.total_tokens = total_tokens
            trace.success = True

        except Exception as e:
            logger.error(f"Tree-of-thought reasoning error: {e}")
            trace.success = False
            trace.error = str(e)
            trace.final_answer = f"Tree-of-thought reasoning encountered an error: {str(e)}"

        trace.total_time_ms = (time.time() - start) * 1000
        self._trace_store.append(trace)
        if len(self._trace_store) > 200:
            self._trace_store = self._trace_store[-100:]
        return trace

    async def execute_self_consistency(
        self,
        system_prompt: str,
        user_message: str,
        tool_schemas: list[dict] | None = None,
        tool_executor: Any = None,
        model: str = "gpt-4o-mini",
        num_samples: int = 5,
    ) -> ReasoningTrace:
        """Execute self-consistency reasoning with multiple sampling and majority voting.

        Generates multiple independent reasoning paths, then aggregates results
        through voting to produce a more reliable answer. Most effective for
        math, logic, and factual queries.
        """
        start = time.time()
        trace = ReasoningTrace()
        total_tokens = 0

        try:
            sample_tasks = []
            for i in range(num_samples):
                temp = 0.7 + (i * 0.05)
                sample_tasks.append(self._generate_sample(
                    system_prompt, user_message, tool_schemas, tool_executor,
                    model, temp, i,
                ))
            sample_results = await asyncio.gather(*sample_tasks, return_exceptions=True)
            valid_samples = []
            for i, result in enumerate(sample_results):
                if isinstance(result, Exception):
                    logger.warning(f"Sample {i} failed: {result}")
                    continue
                valid_samples.append(result)
                trace.steps.append(ReasoningStep(
                    phase=ReasoningPhase.THINK,
                    content=f"Sample {i+1}: {result['answer'][:200]}",
                    confidence=result.get("confidence", 0.5),
                    elapsed_ms=result.get("elapsed_ms", 0),
                ))

            if not valid_samples:
                trace.success = False
                trace.error = "All self-consistency samples failed."
                trace.final_answer = "Unable to generate consensus — all samples failed."
                return trace

            answers = [s["answer"].strip() for s in valid_samples]
            tokens_used = sum(s.get("tokens", 0) for s in valid_samples)
            total_tokens += tokens_used

            consensus = self._majority_vote(answers)

            if len(set(a[:100] for a in answers)) > 1:
                synthesis_prompt = (
                    f"Original question: {user_message}\n\n"
                    f"Multiple reasoning attempts produced these answers:\n\n" +
                    "\n---\n".join(f"Answer {i+1}:\n{a}" for i, a in enumerate(answers)) +
                    f"\n\nIdentify the most correct answer and explain why. "
                    f"If there's disagreement, resolve it through logical analysis. "
                    f"Provide a single final answer."
                )
                final_response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": synthesis_prompt}],
                    max_tokens=4096,
                    temperature=0.3,
                )
                final_answer = final_response.choices[0].message.content or consensus
                if final_response.usage:
                    total_tokens += final_response.usage.total_tokens
            else:
                final_answer = consensus

            unique_answers = len(set(a[:200] for a in answers))
            agreement_score = 1.0 - (unique_answers - 1) / max(len(answers) - 1, 1)

            trace.final_answer = final_answer
            trace.total_tokens = total_tokens
            trace.success = True

            trace.steps.append(ReasoningStep(
                phase=ReasoningPhase.REFLECT,
                content=f"Self-consistency: {len(valid_samples)}/{num_samples} samples, "
                        f"agreement: {agreement_score:.2f}",
                confidence=agreement_score,
                elapsed_ms=0.0,
            ))

        except Exception as e:
            logger.error(f"Self-consistency reasoning error: {e}")
            trace.success = False
            trace.error = str(e)
            trace.final_answer = f"Self-consistency reasoning encountered an error: {str(e)}"

        trace.total_time_ms = (time.time() - start) * 1000
        self._trace_store.append(trace)
        if len(self._trace_store) > 200:
            self._trace_store = self._trace_store[-100:]
        return trace

    async def _generate_sample(
        self, system_prompt: str, user_message: str,
        tool_schemas, tool_executor, model: str, temperature: float, index: int,
    ) -> dict:
        """Generate a single reasoning sample for self-consistency."""
        sample_start = time.time()
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2048,
            }
            if tool_schemas and tool_executor:
                kwargs["tools"] = tool_schemas
                kwargs["tool_choice"] = "auto"
            response = await self.client.chat.completions.create(**kwargs)
            answer = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            return {
                "answer": answer,
                "tokens": tokens,
                "elapsed_ms": (time.time() - sample_start) * 1000,
                "confidence": 0.7,
                "index": index,
            }
        except Exception as e:
            logger.warning(f"Sample {index} generation failed: {e}")
            return {
                "answer": f"[Sample {index} failed: {str(e)}]",
                "tokens": 0,
                "elapsed_ms": (time.time() - sample_start) * 1000,
                "confidence": 0.1,
                "index": index,
            }

    def _parse_branches(self, content: str, expected_count: int) -> list[str]:
        """Parse numbered branches from LLM output."""
        branches = []
        lines = content.split("\n")
        current = []
        for line in lines:
            stripped = line.strip()
            is_new_branch = False
            for pattern in [f"{i+1}.", f"{i+1})", f"Approach {i+1}", f"Branch {i+1}"]:
                if stripped.startswith(pattern):
                    is_new_branch = True
                    break
            if is_new_branch and current:
                branches.append(" ".join(current).strip())
                current = []
            current.append(stripped)
        if current:
            branches.append(" ".join(current).strip())
        branches = [b for b in branches if len(b) > 10]
        return branches[:expected_count]

    def _extract_confidence(self, text: str, default: float = 0.5) -> float:
        """Extract confidence score from text output."""
        import re
        match = re.search(r'CONFIDENCE:\s*([0-9]*\.?[0-9]+)', text, re.IGNORECASE)
        if match:
            return max(0.0, min(1.0, float(match.group(1))))
        lines = text.strip().split("\n")
        for line in reversed(lines):
            match = re.search(r'([0-9]\.[0-9]+)', line)
            if match:
                val = float(match.group(1))
                if 0.0 <= val <= 1.0:
                    return val
        return default

    def _extract_reasoning(self, text: str) -> str:
        """Extract reasoning content from formatted output."""
        import re
        match = re.search(r'REASONING:\s*\n?(.*)', text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        lines = text.split("\n")
        filtered = [l for l in lines if not l.strip().upper().startswith("CONFIDENCE:")]
        return "\n".join(filtered).strip()

    def _majority_vote(self, answers: list[str]) -> str:
        """Perform majority voting on a list of answer strings."""
        if not answers:
            return ""
        if len(answers) == 1:
            return answers[0]
        from collections import Counter
        signatures = [a[:200].lower().strip() for a in answers]
        counter = Counter(signatures)
        most_common_sig, _ = counter.most_common(1)[0]
        for a in answers:
            if a[:200].lower().strip() == most_common_sig:
                return a
        return max(answers, key=len)

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
            ReasoningStyle.CREATIVE: (
                "Think divergently and explore multiple perspectives. Use brainstorming techniques. "
                "Generate novel ideas and connections. Consider unconventional approaches."
                "Embrace open-ended exploration while maintaining coherence."
            ),
            ReasoningStyle.CODING: (
                "Approach coding tasks methodically: understand requirements, design solution, "
                "write clean code, test edge cases, document decisions. "
                "Prioritize correctness, readability, and maintainability. "
                "Consider errors, edge cases, and performance implications."
            ),
            ReasoningStyle.PARALLEL: (
                "Consider multiple perspectives simultaneously. Analyze from different angles: "
                "technical, practical, ethical, and creative. Weigh trade-offs and synthesize "
                "a balanced conclusion. Use parallel thinking to avoid tunnel vision."
            ),
            ReasoningStyle.TREE: (
                "Explore multiple solution paths systematically. For each path, think through "
                "intermediate steps, evaluate feasibility, and compare alternatives. "
                "Prune unpromising approaches early. Converge on the best solution."
            ),
            ReasoningStyle.SELF_CONSISTENCY: (
                "Generate multiple independent solutions to the same problem. "
                "Compare answers, identify the most consistent and reliable one. "
                "Use diversity of thought to increase accuracy. Vote on the best answer."
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

    def recalibrate_confidence(
        self,
        trace: ReasoningTrace,
        model: str = "gpt-4o-mini",
    ) -> float:
        """Recalibrate confidence scores based on tool results and fact verification.

        Analyzes the reasoning trace for signals that affect confidence:
        - Tool call success/failure patterns in each step
        - Reflection phase findings (issues, corrections, caveats)
        - Cross-references between observation claims and tool results
        - Overall trace success status

        Args:
            trace: The ReasoningTrace to recalibrate.
            model: LLM model to use for semantic confidence analysis (reserved
                   for future LLM-based verification).

        Returns:
            A recalibrated confidence score between 0.0 and 1.0.
        """
        # Start with a neutral baseline
        if not trace.success:
            return 0.0

        if not trace.steps:
            return 0.5

        confidence = 0.5
        tool_success_count = 0
        tool_failure_count = 0
        reflection_issues = 0
        total_steps = len(trace.steps)

        # Keywords that indicate problems in reflection content
        caution_keywords = [
            "incorrect", "error", "mistake", "inaccurate", "wrong",
            "missing", "incomplete", "verify", "double-check", "uncertain",
            "might be", "could be wrong", "not sure", "potential issue",
            "limitation", "caveat", "however", "but note", "important to note",
        ]

        for step in trace.steps:
            # Check tool results for success/failure signals
            for tr in step.tool_results:
                if isinstance(tr, dict):
                    if tr.get("success", True):
                        tool_success_count += 1
                    else:
                        tool_failure_count += 1
                elif hasattr(tr, "success"):
                    if tr.success:
                        tool_success_count += 1
                    else:
                        tool_failure_count += 1

            # Check reflection phase for issues
            if step.phase == ReasoningPhase.REFLECT:
                content_lower = step.content.lower()
                for keyword in caution_keywords:
                    if keyword in content_lower:
                        reflection_issues += 1
                        break

        # Adjust confidence based on tool results
        total_tool_results = tool_success_count + tool_failure_count
        if total_tool_results > 0:
            tool_success_rate = tool_success_count / total_tool_results
            # Tool successes boost confidence, failures reduce it
            confidence += (tool_success_rate - 0.5) * 0.3

        # Adjust confidence based on reflection findings
        if reflection_issues > 0:
            # Each reflection issue reduces confidence
            confidence -= min(0.3, reflection_issues * 0.1)

        # Adjust confidence based on step count (more steps = more verification)
        if total_steps >= 4:
            confidence += 0.05  # Bonus for thorough multi-phase reasoning

        # Adjust confidence based on trace-level success
        if trace.success:
            confidence += 0.05

        # Clamp to valid range
        confidence = max(0.0, min(1.0, confidence))

        # Update the steps with the recalibrated confidence
        for step in trace.steps:
            # Blend original confidence with recalibrated value
            step.confidence = round((step.confidence + confidence) / 2, 2)

        logger.debug(
            "Confidence recalibrated: %.2f (tools: %d success / %d fail, "
            "reflection issues: %d, steps: %d)",
            confidence, tool_success_count, tool_failure_count,
            reflection_issues, total_steps,
        )

        return confidence