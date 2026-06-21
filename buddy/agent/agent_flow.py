"""Buddy AgentFlow — comprehensive self-correcting agent execution engine

AgentFlow is the unified execution runtime that orchestrates all agent capabilities
into a coherent, self-correcting pipeline. It deeply integrates:

- Structured Output: schema-enforced outputs with self-validation and retry
- Parallel Reasoning: multiple reasoning paths executed concurrently with synthesis
- Tool Chaining: intelligent tool sequencing with automatic error recovery
- Context Management: sliding window with intelligent summarization and pruning
- Self-Correction: iterative refinement loops with quality scoring
- Stream Processing: real-time streaming with tool call interleaving
- Decision Audit: full traceability of every decision with confidence scoring
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Callable

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.agent_flow")

# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class FlowPhase(str, Enum):
    INGEST = "ingest"
    UNDERSTAND = "understand"
    REASON = "reason"
    DECIDE = "decide"
    EXECUTE = "execute"
    VALIDATE = "validate"
    CORRECT = "correct"
    DELIVER = "deliver"


class CorrectionStrategy(str, Enum):
    RETRY_SAME = "retry_same"
    RETRY_ALTERNATE = "retry_alternate"
    SIMPLIFY = "simplify"
    DECOMPOSE = "decompose"
    ESCALATE = "escalate"


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    CODE = "code"
    MARKDOWN = "markdown"
    STRUCTURED = "structured"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class OutputSchema:
    """Schema definition for structured output validation."""
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    required_fields: list[str] = field(default_factory=list)
    schema_name: str = ""
    strict_mode: bool = False

    def validate(self, data: dict) -> tuple[bool, list[str]]:
        """Validate data against the schema. Returns (is_valid, errors)."""
        errors = []
        for field_name in self.required_fields:
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")
        if self.strict_mode:
            for field_name, field_spec in self.fields.items():
                if field_name in data:
                    expected_type = field_spec.get("type", "string")
                    actual = data[field_name]
                    if expected_type == "string" and not isinstance(actual, str):
                        errors.append(f"Field '{field_name}': expected string, got {type(actual).__name__}")
                    elif expected_type == "number" and not isinstance(actual, (int, float)):
                        errors.append(f"Field '{field_name}': expected number, got {type(actual).__name__}")
                    elif expected_type == "array" and not isinstance(actual, list):
                        errors.append(f"Field '{field_name}': expected array, got {type(actual).__name__}")
                    elif expected_type == "object" and not isinstance(actual, dict):
                        errors.append(f"Field '{field_name}': expected object, got {type(actual).__name__}")
                    elif expected_type == "boolean" and not isinstance(actual, bool):
                        errors.append(f"Field '{field_name}': expected boolean, got {type(actual).__name__}")
        return len(errors) == 0, errors


@dataclass
class ReasoningPath:
    """A single reasoning path with its result and confidence."""
    path_id: str = field(default_factory=lambda: f"rpath-{uuid.uuid4().hex[:8]}")
    strategy: str = "balanced"
    result: str = ""
    confidence: float = 0.0
    steps: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    tokens_used: int = 0


@dataclass
class ToolCallRecord:
    """Record of a tool invocation with its context and result."""
    call_id: str = field(default_factory=lambda: f"tcall-{uuid.uuid4().hex[:8]}")
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    result: str = ""
    success: bool = False
    error: str = ""
    duration_ms: float = 0.0
    retry_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SelfCorrection:
    """Record of a self-correction attempt."""
    correction_id: str = field(default_factory=lambda: f"corr-{uuid.uuid4().hex[:8]}")
    phase: FlowPhase = FlowPhase.VALIDATE
    issue: str = ""
    strategy: CorrectionStrategy = CorrectionStrategy.RETRY_SAME
    original_output: str = ""
    corrected_output: str = ""
    quality_before: float = 0.0
    quality_after: float = 0.0
    success: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FlowResult:
    """Complete result of an AgentFlow execution."""
    flow_id: str = field(default_factory=lambda: f"flow-{uuid.uuid4().hex[:12]}")
    phase: FlowPhase = FlowPhase.DELIVER
    final_output: str = ""
    structured_output: dict | None = None
    output_format: OutputFormat = OutputFormat.TEXT
    reasoning_paths: list[ReasoningPath] = field(default_factory=list)
    best_path: ReasoningPath | None = None
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    corrections: list[SelfCorrection] = field(default_factory=list)
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_tool_calls: int = 0
    total_corrections: int = 0
    quality_score: float = 0.0
    success: bool = True
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════
# AgentFlow Engine
# ═══════════════════════════════════════════════════════════

class AgentFlow:
    """Comprehensive self-correcting agent execution engine.

    Orchestrates the full agent execution lifecycle with structured output
    validation, parallel reasoning, intelligent tool chaining, automatic
    error recovery, context management, and decision auditing.
    """

    MAX_CORRECTION_ATTEMPTS = 3
    MAX_PARALLEL_PATHS = 5
    MAX_TOOL_RETRIES = 2
    QUALITY_THRESHOLD = 0.6

    def __init__(self, client: AsyncOpenAI | None = None):
        self.client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._execution_history: list[FlowResult] = []
        self._total_executions: int = 0
        self._total_tokens: int = 0
        self._correction_stats: dict[str, int] = defaultdict(int)

    # ── Structured Output Execution ───────────────────────

    async def execute_structured(
        self,
        prompt: str,
        output_schema: OutputSchema,
        system_prompt: str = "",
        conversation_history: list[dict] | None = None,
        max_retries: int = 3,
        temperature: float = 0.3,
    ) -> FlowResult:
        """Execute a task with structured output enforced by schema validation.

        The agent will attempt to produce valid structured output. If validation
        fails, it will self-correct up to max_retries times using progressively
        more explicit prompting.
        """
        flow_start = time.time()
        result = FlowResult(
            output_format=OutputFormat.STRUCTURED,
            structured_output={},
        )

        schema_desc = self._describe_schema(output_schema)
        base_messages = [{"role": "system", "content": (
            f"{system_prompt}\n\n"
            f"You MUST respond with a valid JSON object matching this schema:\n"
            f"{schema_desc}\n"
            f"Do NOT include markdown code fences. Output ONLY the JSON object."
        )}]
        if conversation_history:
            base_messages.extend(conversation_history[-20:])
        base_messages.append({"role": "user", "content": prompt})

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=base_messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                    max_tokens=4096,
                )
                content = response.choices[0].message.content or "{}"
                result.total_tokens += response.usage.total_tokens if response.usage else 0

                # Parse and validate
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    correction = SelfCorrection(
                        phase=FlowPhase.VALIDATE,
                        issue="JSON parse error",
                        strategy=CorrectionStrategy.RETRY_SAME,
                        original_output=content[:200],
                        quality_before=0.0,
                    )
                    result.corrections.append(correction)
                    base_messages.append({
                        "role": "assistant", "content": content[:500]
                    })
                    base_messages.append({
                        "role": "user",
                        "content": f"Your response was not valid JSON. Please output ONLY a valid JSON object. Error: invalid JSON syntax."
                    })
                    continue

                is_valid, errors = output_schema.validate(parsed)
                if is_valid:
                    result.structured_output = parsed
                    result.final_output = json.dumps(parsed, indent=2)
                    result.quality_score = 0.9
                    break
                else:
                    correction = SelfCorrection(
                        phase=FlowPhase.VALIDATE,
                        issue=f"Schema validation failed: {'; '.join(errors)}",
                        strategy=CorrectionStrategy.RETRY_ALTERNATE if attempt > 0 else CorrectionStrategy.RETRY_SAME,
                        original_output=content[:200],
                        quality_before=0.3,
                    )
                    result.corrections.append(correction)
                    base_messages.append({
                        "role": "assistant", "content": content[:500]
                    })
                    base_messages.append({
                        "role": "user",
                        "content": (
                            f"Your response failed schema validation. Issues:\n"
                            + "\n".join(f"- {e}" for e in errors)
                            + f"\n\nPlease fix these issues and output a valid JSON object."
                        )
                    })

            except Exception as e:
                logger.warning(f"Structured output attempt {attempt + 1} failed: {e}")
                correction = SelfCorrection(
                    phase=FlowPhase.EXECUTE,
                    issue=str(e),
                    strategy=CorrectionStrategy.RETRY_SAME,
                    quality_before=0.0,
                )
                result.corrections.append(correction)

        if not result.structured_output:
            result.success = False
            result.error = "Failed to produce valid structured output after all retries"
            result.quality_score = 0.0

        result.total_duration_ms = (time.time() - flow_start) * 1000
        result.total_corrections = len(result.corrections)
        self._record_execution(result)
        return result

    def _describe_schema(self, schema: OutputSchema) -> str:
        """Generate a human-readable schema description for the LLM."""
        lines = [f"Schema: {schema.schema_name or 'Output'}", "Fields:"]
        for field_name, field_spec in schema.fields.items():
            required = "REQUIRED" if field_name in schema.required_fields else "optional"
            field_type = field_spec.get("type", "string")
            description = field_spec.get("description", "")
            lines.append(f"  - {field_name} ({field_type}, {required}): {description}")
        if schema.strict_mode:
            lines.append("Strict mode: all types must match exactly.")
        return "\n".join(lines)

    # ── Parallel Reasoning ────────────────────────────────

    async def reason_parallel(
        self,
        prompt: str,
        system_prompt: str = "",
        strategies: list[str] | None = None,
        num_paths: int = 3,
        synthesize: bool = True,
    ) -> FlowResult:
        """Execute multiple reasoning strategies in parallel and synthesize results.

        Launches num_paths concurrent reasoning paths with different strategies
        (e.g., chain_of_thought, tree_of_thought, self_consistency). Each path
        produces an independent result, then a synthesis step combines them
        into a single coherent answer.
        """
        flow_start = time.time()
        result = FlowResult()

        if strategies is None:
            strategies = self._select_strategies(prompt, num_paths)

        strategies = strategies[: self.MAX_PARALLEL_PATHS]

        # Launch all reasoning paths in parallel
        path_tasks = []
        for i, strategy in enumerate(strategies):
            path_tasks.append(self._run_reasoning_path(
                prompt, system_prompt, strategy, f"path-{i}"
            ))

        paths = await asyncio.gather(*path_tasks, return_exceptions=True)
        reasoning_paths = []
        for i, path_result in enumerate(paths):
            if isinstance(path_result, Exception):
                logger.warning(f"Reasoning path {i} failed: {path_result}")
                reasoning_paths.append(ReasoningPath(
                    strategy=strategies[i],
                    result=f"Error: {str(path_result)}",
                    confidence=0.0,
                ))
            else:
                reasoning_paths.append(path_result)

        result.reasoning_paths = reasoning_paths

        if synthesize and len(reasoning_paths) > 1:
            synthesis = await self._synthesize_paths(prompt, reasoning_paths, system_prompt)
            result.final_output = synthesis.get("answer", "")
            result.best_path = reasoning_paths[0] if reasoning_paths else None
            for path in reasoning_paths:
                if path.confidence > (result.best_path.confidence if result.best_path else 0):
                    result.best_path = path
            result.quality_score = synthesis.get("quality", 0.7)
        elif reasoning_paths:
            result.final_output = reasoning_paths[0].result
            result.best_path = reasoning_paths[0]
            result.quality_score = reasoning_paths[0].confidence

        result.total_tokens = sum(p.tokens_used for p in reasoning_paths)
        result.total_duration_ms = (time.time() - flow_start) * 1000
        self._record_execution(result)
        return result

    async def _run_reasoning_path(
        self, prompt: str, system_prompt: str, strategy: str, path_id: str,
    ) -> ReasoningPath:
        """Execute a single reasoning path with a specific strategy."""
        path_start = time.time()
        path = ReasoningPath(strategy=strategy, path_id=path_id)

        strategy_prompts = {
            "chain_of_thought": "Think step by step. Break down the problem and solve each part sequentially.",
            "tree_of_thought": "Explore multiple possible approaches. Consider at least 3 different perspectives, evaluate each, then select the best.",
            "self_consistency": "Solve the problem independently 3 times using different approaches. Compare results and give the most consistent answer.",
            "reflexion": "Solve the problem, then review your own answer for errors. If you find any, correct them and provide the revised answer.",
            "decomposition": "Break the problem into independent sub-problems. Solve each sub-problem separately, then combine the results.",
            "first_principles": "Identify the fundamental principles underlying the problem. Reason from these principles to derive the solution.",
            "analogical": "Find an analogous problem you know how to solve. Map the solution pattern to the current problem.",
        }

        strategy_instruction = strategy_prompts.get(strategy, "Solve the problem thoroughly and provide a clear answer.")
        path.steps.append(f"Strategy: {strategy}")

        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n{strategy_instruction}"},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.5,
                max_tokens=2048,
            )
            path.result = response.choices[0].message.content or ""
            path.tokens_used = response.usage.total_tokens if response.usage else 0
            path.confidence = self._estimate_confidence(path.result)
            path.steps.append(f"Generated {len(path.result)} chars of reasoning")
        except Exception as e:
            path.result = f"Reasoning path failed: {str(e)}"
            path.confidence = 0.0
            path.steps.append(f"Error: {str(e)}")

        path.duration_ms = (time.time() - path_start) * 1000
        return path

    async def _synthesize_paths(
        self, prompt: str, paths: list[ReasoningPath], system_prompt: str,
    ) -> dict:
        """Synthesize multiple reasoning paths into a single coherent answer."""
        paths_text = ""
        for i, path in enumerate(paths):
            paths_text += (
                f"\n--- Path {i + 1} ({path.strategy}, confidence={path.confidence:.2f}) ---\n"
                f"{path.result[:800]}\n"
            )

        synthesis_prompt = (
            f"Original question: {prompt}\n\n"
            f"The following are {len(paths)} independent reasoning paths for this question:\n"
            f"{paths_text}\n\n"
            f"Synthesize these into a single, coherent answer. Identify areas of agreement "
            f"and disagreement. If paths disagree, explain the trade-offs and give your best "
            f"judgment. Return a JSON object with:\n"
            f'  - answer: the synthesized answer\n'
            f'  - agreements: key points all paths agree on\n'
            f'  - disagreements: points where paths differ\n'
            f'  - quality: 0.0-1.0 confidence in the synthesis\n'
            f'  - best_path_index: which path was most valuable (0-based)\n'
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt or "You are a synthesis engine. Combine multiple reasoning paths into a single coherent answer."},
                    {"role": "user", "content": synthesis_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2048,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Synthesis failed: {e}")
            return {
                "answer": paths[0].result if paths else "",
                "agreements": [],
                "disagreements": [],
                "quality": 0.5,
                "best_path_index": 0,
            }

    def _select_strategies(self, prompt: str, num_paths: int) -> list[str]:
        """Select appropriate reasoning strategies based on the prompt."""
        prompt_lower = prompt.lower()

        all_strategies = [
            "chain_of_thought", "tree_of_thought", "self_consistency",
            "reflexion", "decomposition", "first_principles", "analogical",
        ]

        # Prioritize strategies based on task characteristics
        if any(w in prompt_lower for w in ["design", "architecture", "system"]):
            priority = ["tree_of_thought", "first_principles", "decomposition"]
        elif any(w in prompt_lower for w in ["debug", "fix", "error", "bug"]):
            priority = ["reflexion", "chain_of_thought", "decomposition"]
        elif any(w in prompt_lower for w in ["analyze", "compare", "evaluate"]):
            priority = ["self_consistency", "analogical", "chain_of_thought"]
        elif any(w in prompt_lower for w in ["explain", "what", "why", "how"]):
            priority = ["chain_of_thought", "first_principles", "analogical"]
        else:
            priority = ["chain_of_thought", "tree_of_thought", "self_consistency"]

        selected = []
        for s in priority:
            if s not in selected:
                selected.append(s)
        for s in all_strategies:
            if s not in selected and len(selected) < num_paths:
                selected.append(s)

        return selected[:num_paths]

    def _estimate_confidence(self, text: str) -> float:
        """Estimate confidence based on response characteristics."""
        if not text:
            return 0.0
        score = 0.5
        if len(text) > 200:
            score += 0.1
        if len(text) > 500:
            score += 0.1
        if any(marker in text.lower() for marker in ["therefore", "in conclusion", "to summarize"]):
            score += 0.1
        if any(marker in text.lower() for marker in ["however", "on the other hand", "alternatively"]):
            score += 0.05  # showing nuance
        if "i'm not sure" in text.lower() or "i don't know" in text.lower():
            score -= 0.2
        return min(0.95, max(0.1, score))

    # ── Tool Chaining with Error Recovery ─────────────────

    async def execute_tool_chain(
        self,
        task: str,
        tools: list[dict],
        system_prompt: str = "",
        conversation_history: list[dict] | None = None,
        max_rounds: int = 8,
    ) -> FlowResult:
        """Execute a multi-step task with automatic tool selection and chaining.

        The agent decides which tools to call, in what order, and handles errors
        by retrying with alternative approaches. Tool results are fed back into
        the context for subsequent decisions.
        """
        flow_start = time.time()
        result = FlowResult()

        messages = [{"role": "system", "content": (
            f"{system_prompt}\n\n"
            f"You have access to tools. Use them to accomplish the task. "
            f"For each step, decide which tool to call with what arguments. "
            f"If a tool fails, try an alternative approach. "
            f"After gathering enough information, provide a final answer."
        )}]
        if conversation_history:
            messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": task})

        for round_num in range(max_rounds):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.4,
                    max_tokens=2048,
                )
                result.total_tokens += response.usage.total_tokens if response.usage else 0

                choice = response.choices[0]
                msg = choice.message

                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            arguments = {}

                        record = ToolCallRecord(
                            tool_name=tool_name,
                            arguments=arguments,
                        )

                        # Execute the tool (delegated to tool registry)
                        try:
                            tool_result = await self._execute_tool(tool_name, arguments)
                            record.result = tool_result
                            record.success = True
                        except Exception as e:
                            record.error = str(e)
                            record.success = False
                            if record.retry_count < self.MAX_TOOL_RETRIES:
                                record.retry_count += 1

                        result.tool_calls.append(record)
                        result.total_tool_calls += 1

                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call.model_dump()],
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": record.result if record.success else f"Error: {record.error}",
                        })

                else:
                    # No more tool calls — final answer
                    result.final_output = msg.content or ""
                    result.quality_score = 0.8
                    break

            except Exception as e:
                logger.warning(f"Tool chain round {round_num} failed: {e}")
                correction = SelfCorrection(
                    phase=FlowPhase.EXECUTE,
                    issue=str(e),
                    strategy=CorrectionStrategy.RETRY_ALTERNATE,
                )
                result.corrections.append(correction)

        if not result.final_output:
            result.success = False
            result.error = "Tool chain did not produce a final answer"
            result.final_output = "I was unable to complete the task with the available tools."

        result.total_duration_ms = (time.time() - flow_start) * 1000
        result.total_corrections = len(result.corrections)
        self._record_execution(result)
        return result

    async def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a named tool with the given arguments."""
        from agent.tools import tool_registry
        result = await tool_registry.execute(tool_name, arguments)
        if result.success:
            return result.output
        raise RuntimeError(result.error)

    # ── Self-Correction Loop ──────────────────────────────

    async def execute_with_correction(
        self,
        prompt: str,
        system_prompt: str = "",
        quality_threshold: float = 0.7,
        max_corrections: int = 3,
    ) -> FlowResult:
        """Execute a task with iterative self-correction.

        After generating an initial response, the agent evaluates its own output
        and attempts to improve it through iterative refinement. Each correction
        cycle identifies specific issues and addresses them.
        """
        flow_start = time.time()
        result = FlowResult()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        current_output = ""
        current_quality = 0.0

        for attempt in range(max_corrections + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0.5 if attempt == 0 else 0.3,
                    max_tokens=2048,
                )
                current_output = response.choices[0].message.content or ""
                result.total_tokens += response.usage.total_tokens if response.usage else 0

                # Self-evaluate quality
                current_quality = await self._evaluate_quality(prompt, current_output, system_prompt)

                if current_quality >= quality_threshold or attempt >= max_corrections:
                    break

                # Generate correction feedback
                feedback = await self._generate_feedback(prompt, current_output, current_quality)
                correction = SelfCorrection(
                    phase=FlowPhase.CORRECT,
                    issue=feedback.get("issue", "Quality below threshold"),
                    strategy=self._select_correction_strategy(attempt, feedback),
                    original_output=current_output[:200],
                    quality_before=current_quality,
                )
                result.corrections.append(correction)

                messages.append({"role": "assistant", "content": current_output})
                messages.append({"role": "user", "content": (
                    f"Your response quality score is {current_quality:.2f} (threshold: {quality_threshold}). "
                    f"Issues identified: {feedback.get('issue', '')}. "
                    f"Suggestions: {feedback.get('suggestion', '')}. "
                    f"Please improve your response."
                )})

            except Exception as e:
                logger.warning(f"Correction attempt {attempt} failed: {e}")
                correction = SelfCorrection(
                    phase=FlowPhase.CORRECT,
                    issue=str(e),
                    strategy=CorrectionStrategy.SIMPLIFY,
                )
                result.corrections.append(correction)
                break

        result.final_output = current_output
        result.quality_score = current_quality
        result.total_corrections = len(result.corrections)
        result.total_duration_ms = (time.time() - flow_start) * 1000
        self._record_execution(result)
        return result

    async def _evaluate_quality(
        self, prompt: str, output: str, system_prompt: str = "",
    ) -> float:
        """Evaluate the quality of an agent response on a 0.0-1.0 scale."""
        if not output:
            return 0.0

        eval_prompt = (
            f"Original task: {prompt[:500]}\n\n"
            f"Response to evaluate:\n{output[:1000]}\n\n"
            f"Rate the quality of this response on a scale of 0.0 to 1.0 considering:\n"
            f"- Relevance: Does it directly address the task?\n"
            f"- Completeness: Does it cover all aspects?\n"
            f"- Accuracy: Is the information correct?\n"
            f"- Clarity: Is it well-structured and easy to understand?\n"
            f"Return ONLY a JSON object with: {{'score': <float>, 'reason': '<brief>'}}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": eval_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=256,
            )
            content = response.choices[0].message.content or '{"score": 0.5}'
            eval_result = json.loads(content)
            return float(eval_result.get("score", 0.5))
        except Exception:
            return self._estimate_confidence(output)

    async def _generate_feedback(
        self, prompt: str, output: str, quality: float,
    ) -> dict:
        """Generate specific feedback for improving a response."""
        feedback_prompt = (
            f"Original task: {prompt[:400]}\n\n"
            f"Current response (quality: {quality:.2f}):\n{output[:800]}\n\n"
            f"Identify the main issue with this response and suggest one specific improvement. "
            f"Return JSON: {{'issue': '<specific issue>', 'suggestion': '<concrete improvement>'}}"
        )
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": feedback_prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=256,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception:
            return {"issue": "Response could be improved", "suggestion": "Add more detail and structure"}

    def _select_correction_strategy(
        self, attempt: int, feedback: dict,
    ) -> CorrectionStrategy:
        """Select the appropriate correction strategy based on attempt number and feedback."""
        if attempt == 0:
            return CorrectionStrategy.RETRY_SAME
        elif attempt == 1:
            return CorrectionStrategy.RETRY_ALTERNATE
        elif "decompose" in feedback.get("suggestion", "").lower():
            return CorrectionStrategy.DECOMPOSE
        else:
            return CorrectionStrategy.SIMPLIFY

    # ── Context Window Management ─────────────────────────

    def manage_context(
        self,
        messages: list[dict],
        max_tokens: int = 8000,
        preserve_system: bool = True,
    ) -> list[dict]:
        """Intelligently manage context window by pruning and summarizing.

        Preserves the system message and most recent messages while summarizing
        or removing older content to fit within the token budget.
        """
        if not messages:
            return messages

        # Estimate token count (rough: 4 chars ≈ 1 token)
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        estimated_tokens = total_chars // 4

        if estimated_tokens <= max_tokens:
            return messages

        result = []
        system_messages = []
        other_messages = []

        for m in messages:
            if m.get("role") == "system" and preserve_system:
                system_messages.append(m)
            else:
                other_messages.append(m)

        result.extend(system_messages)

        # Keep the most recent messages, summarize older ones
        system_chars = sum(len(str(m.get("content", ""))) for m in system_messages)
        budget_tokens = max_tokens - (system_chars // 4)

        # Always keep the last 4 messages intact
        keep_count = min(4, len(other_messages))
        recent = other_messages[-keep_count:]
        older = other_messages[:-keep_count]

        if older and budget_tokens > 500:
            summary = self._summarize_context(older)
            result.append({"role": "system", "content": f"[Previous context summary]: {summary}"})

        result.extend(recent)
        return result

    def _summarize_context(self, messages: list[dict]) -> str:
        """Create a compact summary of older context messages."""
        if not messages:
            return ""
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        return (
            f"Earlier conversation: {len(user_msgs)} user messages, "
            f"{len(assistant_msgs)} assistant responses. "
            f"Key topics: {', '.join(str(m.get('content', ''))[:50] for m in user_msgs[-3:])}"
        )

    # ── Streaming with Tool Interleaving ──────────────────

    async def stream_execute(
        self,
        prompt: str,
        system_prompt: str = "",
        conversation_history: list[dict] | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """Stream execution with real-time tool call announcements.

        Yields tokens as they arrive, and announces tool calls with their
        results inline in the stream.
        """
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": prompt})

        try:
            stream = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=0.7,
                max_tokens=2048,
                stream=True,
            )

            tool_calls_buffer: dict[int, dict] = {}
            async for chunk in stream:
                delta = chunk.choices[0].delta

                if delta.content:
                    yield delta.content

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": tc.id or "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_buffer[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_buffer[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[idx]["arguments"] += tc.function.arguments

                if chunk.choices[0].finish_reason == "tool_calls":
                    for idx, tc_data in tool_calls_buffer.items():
                        yield f"\n\n[Tool: {tc_data['name']}]\n"
                        try:
                            args = json.loads(tc_data["arguments"])
                            from agent.tools import tool_registry
                            tool_result = await tool_registry.execute(tc_data["name"], args)
                            yield f"[Result]: {tool_result.output[:500]}\n\n"
                        except Exception as e:
                            yield f"[Error]: {str(e)}\n\n"

        except Exception as e:
            yield f"\n[Stream error: {str(e)}]"

    # ── Decision Audit ────────────────────────────────────

    def audit_decision(
        self,
        result: FlowResult,
        include_tool_calls: bool = True,
        include_corrections: bool = True,
    ) -> dict[str, Any]:
        """Generate a comprehensive audit trail of an agent execution.

        Provides full traceability of every decision made during execution,
        including reasoning paths, tool calls, corrections, and quality scores.
        """
        audit = {
            "flow_id": result.flow_id,
            "timestamp": result.timestamp,
            "success": result.success,
            "quality_score": result.quality_score,
            "total_duration_ms": result.total_duration_ms,
            "total_tokens": result.total_tokens,
            "phases": {
                "reasoning_paths": len(result.reasoning_paths),
                "tool_calls": result.total_tool_calls,
                "corrections": result.total_corrections,
            },
        }

        if result.reasoning_paths:
            audit["reasoning"] = [
                {
                    "path_id": p.path_id,
                    "strategy": p.strategy,
                    "confidence": round(p.confidence, 3),
                    "duration_ms": p.duration_ms,
                    "result_preview": p.result[:200],
                }
                for p in result.reasoning_paths
            ]
            if result.best_path:
                audit["best_path"] = {
                    "path_id": result.best_path.path_id,
                    "strategy": result.best_path.strategy,
                    "confidence": round(result.best_path.confidence, 3),
                }

        if include_tool_calls and result.tool_calls:
            audit["tool_calls"] = [
                {
                    "call_id": tc.call_id,
                    "tool": tc.tool_name,
                    "success": tc.success,
                    "duration_ms": tc.duration_ms,
                    "retry_count": tc.retry_count,
                    "result_preview": tc.result[:200] if tc.success else tc.error[:200],
                }
                for tc in result.tool_calls
            ]

        if include_corrections and result.corrections:
            audit["corrections"] = [
                {
                    "correction_id": c.correction_id,
                    "phase": c.phase.value,
                    "issue": c.issue[:200],
                    "strategy": c.strategy.value,
                    "quality_before": round(c.quality_before, 3),
                    "quality_after": round(c.quality_after, 3),
                    "success": c.success,
                }
                for c in result.corrections
            ]

        audit["final_output_preview"] = result.final_output[:500]
        return audit

    # ── Execution Recording ───────────────────────────────

    def _record_execution(self, result: FlowResult):
        """Record an execution for history and statistics."""
        self._execution_history.append(result)
        if len(self._execution_history) > 200:
            self._execution_history = self._execution_history[-100:]
        self._total_executions += 1
        self._total_tokens += result.total_tokens
        for c in result.corrections:
            self._correction_stats[c.strategy.value] += 1

    # ── Statistics ────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive execution statistics."""
        recent = self._execution_history[-50:]
        success_count = sum(1 for r in recent if r.success)
        avg_quality = sum(r.quality_score for r in recent) / max(len(recent), 1)
        avg_duration = sum(r.total_duration_ms for r in recent) / max(len(recent), 1)

        return {
            "total_executions": self._total_executions,
            "total_tokens": self._total_tokens,
            "recent": {
                "count": len(recent),
                "success_rate": round(success_count / max(len(recent), 1), 3),
                "avg_quality": round(avg_quality, 3),
                "avg_duration_ms": round(avg_duration, 1),
            },
            "corrections": dict(self._correction_stats),
            "last_execution": (
                {
                    "flow_id": recent[-1].flow_id,
                    "success": recent[-1].success,
                    "quality": round(recent[-1].quality_score, 3),
                    "corrections": recent[-1].total_corrections,
                }
                if recent else None
            ),
        }

    def get_recent_executions(self, limit: int = 10) -> list[dict]:
        """Get recent execution summaries."""
        return [
            {
                "flow_id": r.flow_id,
                "success": r.success,
                "quality_score": round(r.quality_score, 3),
                "duration_ms": round(r.total_duration_ms, 1),
                "tokens": r.total_tokens,
                "tool_calls": r.total_tool_calls,
                "corrections": r.total_corrections,
                "output_preview": r.final_output[:200],
                "timestamp": r.timestamp,
            }
            for r in self._execution_history[-limit:]
        ]


# ── Singleton ─────────────────────────────────────────────

agent_flow = AgentFlow()