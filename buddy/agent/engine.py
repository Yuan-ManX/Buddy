"""Buddy Agent Engine — Core LLM reasoning with tools, skills, and plan execution

Provides the central agent execution framework with iteration budget
management, provider fallback chains, tool approval gating, and
event-driven lifecycle notifications.
"""
from __future__ import annotations
import json
import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from config.settings import settings
from agent.memory import MemorySystem
from agent.skills import SkillsRegistry
from agent.context import ContextManager
from agent.routing import model_router
from agent.tools import tool_registry, ToolResult
from agent.reasoning import ReasoningLoop, ReasoningStyle
from agent.planning import planning_engine, ExecutionPlan, PlanStatus, StepStatus
from agent.workspace import AgentWorkspace
from agent.subagent import SubAgentOrchestrator
from agent.dream import DreamEngine, DreamCycleResult
from agent.approval import approval_engine
from agent.events import event_bus, Event, EventType

logger = logging.getLogger("buddy.engine")


class IterationBudget:
    """Thread-safe iteration counter that limits agent loop depth."""

    def __init__(self, max_iterations: int = 90):
        self.max_iterations = max_iterations
        self._used = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_iterations - self._used)

    @property
    def is_exhausted(self) -> bool:
        return self._used >= self.max_iterations

    def consume(self, count: int = 1) -> bool:
        """Consume iterations. Returns True if budget remains."""
        if self._used + count > self.max_iterations:
            return False
        self._used += count
        return True

    def refund(self, count: int = 1):
        """Refund iterations (e.g., for code execution that chains sub-calls)."""
        self._used = max(0, self._used - count)

    def reset(self):
        self._used = 0

    @property
    def usage_ratio(self) -> float:
        return self._used / max(self.max_iterations, 1)


class AgentEngine:
    """Core agent execution engine with LLM integration, tool calling,
    reasoning pipeline, skill execution, plan orchestration, and
    iteration budget management."""

    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 30.0

    def __init__(self, agent_id: str, agent_name: str, instructions: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.instructions = instructions
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.memory = MemorySystem(agent_id, load_from_db=True)
        self.skills = SkillsRegistry(client=self.client)
        self.context = ContextManager(client=self.client)
        self.reasoning = ReasoningLoop(
            style=ReasoningStyle.BALANCED,
            client=self.client,
        )
        self.workspace = AgentWorkspace(agent_id)
        self.subagent_orchestrator = SubAgentOrchestrator(agent_id)
        self.dream = DreamEngine(agent_id=self.agent_id, memory_system=self.memory, client=self.client)
        self._conversation_id: str | None = None
        self._iteration_budget = IterationBudget(settings.MAX_ITERATIONS)
        self._fallback_models = settings.FALLBACK_MODELS.copy()
        self._total_tokens_used = 0

    @property
    def iteration_budget(self) -> IterationBudget:
        return self._iteration_budget

    @property
    def total_tokens(self) -> int:
        return self._total_tokens_used

    def _track_tokens(self, usage: Any):
        """Track token usage from an LLM response."""
        if hasattr(usage, 'total_tokens'):
            self._total_tokens_used += usage.total_tokens

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute an async function with exponential backoff retry."""
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{self.MAX_RETRIES}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
        raise last_error

    # ── Primary Chat Interface ──────────────────────────────

    async def chat(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        stream: bool = False,
        enable_tools: bool = True,
        enable_reasoning: bool = False,
    ) -> str | AsyncIterator[str]:
        """Primary chat entry point with optional tool and reasoning support."""
        system_prompt = await self._build_system_prompt(enable_tools)

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend([
                {"role": m["role"], "content": m["content"]}
                for m in conversation_history[-settings.MAX_CONTEXT_MESSAGES:]
            ])

        messages.append({"role": "user", "content": message})

        try:
            if stream:
                return self._stream_chat(messages, enable_tools, enable_reasoning)
            else:
                return await self._chat(messages, enable_tools, enable_reasoning)
        except Exception as e:
            logger.error(f"Agent engine error: {e}")
            await self.memory.store(
                content=f"Error during conversation: {str(e)}",
                memory_type="event",
                importance=0.3,
            )
            raise

    async def chat_with_plan(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """Chat with automatic plan generation and step-by-step execution."""
        # Generate execution plan
        plan = await planning_engine.generate_plan(message, self.agent_id)

        if stream:

            async def plan_stream():
                yield f"**Plan: {plan.title}** ({len(plan.steps)} steps)\n\n"
                for i, step in enumerate(plan.steps):
                    yield f"### Step {i+1}: {step.title}\n"
                    planning_engine.update_step_status(plan.id, step.id, StepStatus.IN_PROGRESS)

                    # Execute this step
                    result = await self.chat(
                        f"Goal: {plan.goal}\nCurrent step: {step.title}\n{step.description}",
                        conversation_history=conversation_history,
                        enable_tools=True,
                        enable_reasoning=True,
                    )
                    if isinstance(result, str):
                        yield f"{result}\n\n"
                        planning_engine.update_step_status(plan.id, step.id, StepStatus.COMPLETED, result)
                    else:
                        async for chunk in result:
                            yield chunk

                yield f"\n---\n**Plan completed.** Progress: {plan.progress['percentage']}%"

            return plan_stream()
        else:
            results = []
            for step in plan.steps:
                planning_engine.update_step_status(plan.id, step.id, StepStatus.IN_PROGRESS)
                result = await self.chat(
                    f"Goal: {plan.goal}\nCurrent step: {step.title}\n{step.description}",
                    conversation_history=conversation_history,
                    enable_tools=True,
                    enable_reasoning=True,
                )
                step_result = result if isinstance(result, str) else ""
                results.append(f"### {step.title}\n{step_result}")
                planning_engine.update_step_status(plan.id, step.id, StepStatus.COMPLETED, step_result)

            return f"**Plan: {plan.title}**\n\n" + "\n\n".join(results)

    # ── Internal Chat Methods ───────────────────────────────

    async def _chat(
        self,
        messages: list[dict],
        enable_tools: bool = True,
        enable_reasoning: bool = False,
    ) -> str:
        user_message = messages[-1]["content"]
        context_depth = len(messages) - 2

        # Context compaction
        if context_depth > self.context.config.max_messages:
            system_prompt = messages[0]["content"] if messages[0]["role"] == "system" else ""
            messages = await self.context.compact(messages, system_prompt)

        # Model routing
        routing = model_router.route(user_message, context_depth)
        logger.info(f"Routing: {routing.reasoning}")

        # Reasoning loop if enabled
        if enable_reasoning:
            try:
                trace = await self.reasoning.execute(
                    system_prompt=messages[0]["content"] if messages[0]["role"] == "system" else "",
                    user_message=user_message,
                    tool_schemas=tool_registry.get_openai_schemas() if enable_tools else None,
                    tool_executor=self._execute_tool if enable_tools else None,
                    model=routing.model,
                )
                content = trace.final_answer
            except Exception as e:
                logger.warning(f"Reasoning loop failed, falling back to direct: {e}")
                content = await self._direct_chat(messages, routing, enable_tools)
        else:
            content = await self._direct_chat(messages, routing, enable_tools)

        # Store in memory
        await self.memory.store(
            content=f"User: {user_message}\nAssistant: {content}",
            memory_type="event",
            importance=0.5,
        )

        # Publish events
        event_bus.publish(Event(
            type=EventType.MESSAGE_SENT,
            source=self.agent_id,
            data={"agent_id": self.agent_id, "content": user_message[:200], "role": "user"},
        ))
        event_bus.publish(Event(
            type=EventType.MESSAGE_RECEIVED,
            source=self.agent_id,
            data={"agent_id": self.agent_id, "content": content[:200], "role": "assistant"},
        ))

        return content

    async def _direct_chat(self, messages: list[dict], routing, enable_tools: bool) -> str:
        """Direct LLM chat with optional tool calling and provider fallback."""
        models_to_try = [routing.model] + [
            m for m in self._fallback_models if m != routing.model
        ]

        last_error = None
        for model in models_to_try:
            try:
                kwargs: dict = {
                    "model": model,
                    "messages": messages,
                    "temperature": routing.temperature,
                    "max_tokens": routing.max_tokens,
                }

                if enable_tools:
                    kwargs["tools"] = tool_registry.get_openai_schemas()
                    kwargs["tool_choice"] = "auto"

                response = await self._retry_with_backoff(
                    self.client.chat.completions.create, **kwargs
                )
                choice = response.choices[0]
                self._track_tokens(response.usage)

                # Handle tool calls
                if choice.message.tool_calls and enable_tools:
                    return await self._handle_tool_calls(messages, choice, routing)

                return choice.message.content or ""

            except Exception as e:
                last_error = e
                if model != models_to_try[-1]:
                    logger.warning(f"Model {model} failed, trying next in fallback chain: {e}")
                continue

        logger.error(f"All models in fallback chain failed. Last error: {last_error}")
        return self._fallback_response(messages[-1]["content"])

    async def _stream_chat(
        self,
        messages: list[dict],
        enable_tools: bool = True,
        enable_reasoning: bool = False,
    ) -> AsyncIterator[str]:
        full_content = ""
        user_message = messages[-1]["content"]
        context_depth = len(messages) - 2

        if context_depth > self.context.config.max_messages:
            system_prompt = messages[0]["content"] if messages[0]["role"] == "system" else ""
            messages = await self.context.compact(messages, system_prompt)

        routing = model_router.route(user_message, context_depth)

        try:
            create_kwargs: dict = {
                "model": routing.model,
                "messages": messages,
                "temperature": routing.temperature,
                "max_tokens": routing.max_tokens,
                "stream": True,
            }
            if enable_tools:
                create_kwargs["tools"] = tool_registry.get_openai_schemas()
                create_kwargs["tool_choice"] = "auto"

            stream = await self._retry_with_backoff(
                self.client.chat.completions.create, **create_kwargs
            )

            # Collect tool call deltas while streaming text content
            tool_call_deltas: dict[int, dict] = {}
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    token = delta.content
                    full_content += token
                    yield token
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_call_deltas:
                            tool_call_deltas[idx] = {
                                "id": tc_delta.id or "",
                                "name": tc_delta.function.name if tc_delta.function else "",
                                "arguments": "",
                            }
                        if tc_delta.id:
                            tool_call_deltas[idx]["id"] = tc_delta.id
                        if tc_delta.function and tc_delta.function.name:
                            tool_call_deltas[idx]["name"] = tc_delta.function.name
                        if tc_delta.function and tc_delta.function.arguments:
                            tool_call_deltas[idx]["arguments"] += tc_delta.function.arguments

            # If tool calls were requested, execute them and get final response
            if tool_call_deltas:
                self._iteration_budget.consume()
                yield "\n\n"  # visual separator

                # Build assistant tool call message for context
                tool_call_entries = []
                for idx in sorted(tool_call_deltas.keys()):
                    tc = tool_call_deltas[idx]
                    try:
                        args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    tool_call_entries.append({"id": tc["id"], "name": tc["name"], "arguments": args})

                # Append assistant message with tool calls to message history
                messages.append({
                    "role": "assistant",
                    "content": full_content or "",
                    "tool_calls": [
                        {
                            "id": e["id"],
                            "type": "function",
                            "function": {"name": e["name"], "arguments": json.dumps(e["arguments"])},
                        }
                        for e in tool_call_entries
                    ],
                })

                # Execute tools and yield results, appending to message history
                for entry in tool_call_entries:
                    result = await self._execute_tool_safe(entry["name"], entry["arguments"])
                    yield f"\n[Tool: {entry['name']}]\n"
                    yield result.output if result.success else f"Error: {result.error}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": entry["id"],
                        "content": result.output if result.success else f"Error: {result.error}",
                    })

                # Get final response with tool results in context
                final_text = ""
                final_stream = await self._retry_with_backoff(
                    self.client.chat.completions.create,
                    model=routing.model,
                    messages=messages,
                    temperature=routing.temperature,
                    max_tokens=routing.max_tokens,
                    stream=True,
                )
                async for chunk in final_stream:
                    if chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        final_text += token
                        yield token
                full_content = final_text

            self._total_tokens_used += 1  # approximate

        except Exception as e:
            logger.warning(f"Streaming LLM call failed, using fallback: {e}")
            fallback = self._fallback_response(user_message)
            yield fallback

        await self.memory.store(
            content=f"User: {user_message}\nAssistant: {full_content}",
            memory_type="event",
            importance=0.5,
        )
        event_bus.publish(Event(
            type=EventType.MESSAGE_RECEIVED,
            source=self.agent_id,
            data={"agent_id": self.agent_id, "content": full_content[:200], "role": "assistant"},
        ))

    # ── Tool Calling ────────────────────────────────────────

    async def _execute_tool(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool from the registry with unified approval check."""
        event_bus.publish(Event(
            type=EventType.TOOL_CALLED,
            source=self.agent_id,
            data={"agent_id": self.agent_id, "tool_name": name, "args": {k: str(v)[:80] for k, v in arguments.items()}},
        ))

        # Unified approval check for all tool execution paths
        if settings.TOOL_APPROVAL_ENABLED:
            approved = await approval_engine.check(name, arguments)
            if not approved:
                event_bus.publish(Event(
                    type=EventType.TOOL_DENIED,
                    source=self.agent_id,
                    data={"agent_id": self.agent_id, "tool_name": name},
                ))
                return ToolResult(name=name, success=False, error="Tool execution denied by safety policy")

        # Check if it's a skill
        skill = self.skills.get(name)
        if skill:
            try:
                handler = skill["handler"]
                result = await handler(arguments)
                return ToolResult(name=name, success=True, output=result)
            except Exception as e:
                return ToolResult(name=name, success=False, error=str(e))

        return await tool_registry.execute(name, arguments)

    async def _execute_tool_safe(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool with safety check (delegates to unified _execute_tool)."""
        return await self._execute_tool(name, arguments)

    async def _handle_tool_calls(self, messages: list[dict], choice, routing) -> str:
        """Process tool calls from LLM response with approval gating."""
        # Append assistant message with tool calls
        tool_call_messages = []
        for tc in choice.message.tool_calls:
            tool_call_messages.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            })

        messages.append({
            "role": "assistant",
            "content": choice.message.content or "",
            "tool_calls": tool_call_messages,
        })

        # Execute each tool call (approval is handled by _execute_tool)
        for tc in choice.message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            result = await self._execute_tool(tc.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result.output if result.success else f"Error: {result.error}",
            })

        # Get final response after tool calls
        try:
            final_response = await self.client.chat.completions.create(
                model=routing.model,
                messages=messages,
                temperature=routing.temperature,
                max_tokens=routing.max_tokens,
            )
            return final_response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"Final response after tool calls failed: {e}")
            return "I completed the requested actions but encountered an issue summarizing the results."

    # ── Skill Execution ────────────────────────────────────

    async def execute_skill(self, skill_name: str, parameters: dict[str, Any]) -> str:
        """Execute a skill by name."""
        return await self.skills.execute(skill_name, parameters)

    async def execute_skill_pipeline(self, steps: list[tuple[str, dict]]) -> str:
        """Execute a pipeline of skills."""
        return await self.skills.execute_pipeline(steps)

    # ── Workspace Operations ──────────────────────────────

    async def execute_code(self, code: str, language: str = "python", timeout: int = 30) -> dict:
        """Execute code in the agent's workspace."""
        if language == "python":
            result = await self.workspace.execute_python(code, timeout)
        else:
            result = await self.workspace.execute_shell(code, timeout)

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "exit_code": result.exit_code,
            "execution_time": result.execution_time,
        }

    # ── Plan Operations ────────────────────────────────────

    async def generate_plan(self, goal: str) -> dict:
        """Generate an execution plan."""
        plan = await planning_engine.generate_plan(goal, self.agent_id)
        return plan.to_dict()

    async def execute_plan(self, plan_id: str) -> dict:
        """Execute a plan step by step."""

        async def step_executor(prompt: str, model: str) -> str:
            result = await self.chat(prompt, enable_tools=True, enable_reasoning=True)
            return result if isinstance(result, str) else ""

        plan = await planning_engine.execute_plan(plan_id, step_executor)
        return plan.to_dict()

    # ── System Prompt Building ─────────────────────────────

    async def _build_system_prompt(self, include_tools: bool = False) -> str:
        memory_context = ""
        recent_memories = await self.memory.recall(limit=5)

        if recent_memories:
            memory_lines = ["\n## Context from Past Interactions\n"]
            for m in recent_memories:
                preview = m["content"][:200].replace("\n", " ")
                memory_lines.append(f"- {preview}")
            memory_context = "\n".join(memory_lines)

        tools_section = ""
        if include_tools:
            tool_names = [t.name for t in tool_registry.list_tools()]
            skill_names = [s["name"] for s in self.skills.list()]
            all_capabilities = tool_names + skill_names
            if all_capabilities:
                tools_section = (
                    "\n## Available Capabilities\n"
                    f"You can use function calling to invoke these: {', '.join(all_capabilities)}.\n"
                    "Use tools proactively when they help answer the user's question.\n"
                )

        return f"""You are {self.agent_name}, an AI agent in the Buddy platform.

{self.instructions}

Buddy is an AI-native platform where humans and agents collaborate as peers.
You are a dedicated agent with your own identity, personality, and capabilities.

Guidelines:
- Be authentic to your role and personality
- Use markdown formatting for clarity when helpful
- Be proactive and thoughtful in your responses
- Stay in character as {self.agent_name}
- If you don't know something, say so honestly
- Be concise but thorough — respect the user's time
- Use available tools and skills to provide the best answer
{tools_section}
Current date: {datetime.now().strftime('%Y-%m-%d')}
{memory_context}"""

    # ── Fallback Responses ──────────────────────────────────

    def _fallback_response(self, user_message: str) -> str:
        msg_lower = user_message.lower().strip()

        if any(g in msg_lower for g in ["hello", "hi", "hey", "greetings"]):
            return (
                f"Hello! I'm {self.agent_name}. Great to meet you!\n\n"
                f"I'm currently running in offline mode (no LLM API key configured).\n"
                f"To unlock my full conversational abilities, add your `OPENAI_API_KEY` to the `.env` file.\n\n"
                f"In the meantime, I can still help with basic tasks. What would you like to talk about?"
            )

        if any(g in msg_lower for g in ["who are you", "what are you", "your name", "introduce"]):
            return (
                f"I'm **{self.agent_name}**, your AI agent on the Buddy platform.\n\n"
                f"{self.instructions}\n\n"
                f"I'm designed to collaborate with you as a peer — think of me as a digital teammate "
                f"with my own perspective and capabilities."
            )

        if any(g in msg_lower for g in ["help", "can you", "what can"]):
            return (
                f"Great question! Here's what I can help with:\n\n"
                f"- **Conversations** — discuss ideas, get advice, brainstorm\n"
                f"- **Code** — review, debug, explain, and execute programming concepts\n"
                f"- **Analysis** — break down problems, evaluate options\n"
                f"- **Research** — explore topics, synthesize information\n"
                f"- **Planning** — decompose complex goals into executable steps\n"
                f"- **Tools** — calculate, search, read/write files, and more\n"
                f"- **Memory** — I remember past conversations for continuity\n\n"
                f"To unlock my full LLM-powered capabilities, configure an `OPENAI_API_KEY` in your `.env` file.\n"
                f"Once connected, I can handle much more complex tasks!"
            )

        return (
            f"Hi! I'm **{self.agent_name}**, your AI agent.\n\n"
            f"I received your message but I'm currently in offline mode without an LLM API key.\n\n"
            f"**To enable full AI capabilities:**\n"
            f"1. Copy `buddy/.env.example` to `buddy/.env`\n"
            f"2. Set your `OPENAI_API_KEY`\n"
            f"3. Restart the backend server\n\n"
            f"I can still help with basic interactions powered by my internal skill and tool systems.\n"
            f"Feel free to ask me anything — I'll do my best!\n\n"
            f"> Your message: _{user_message[:200]}{'...' if len(user_message) > 200 else ''}_"
        )

    # ── Dream Operations ───────────────────────────────────

    async def start_dream_cycle(self, interval_seconds: int = 3600) -> bool:
        """Start the background dream processing loop."""
        if self.dream.is_running:
            return False
        self.dream.start(interval_seconds)
        logger.info(f"Dream cycle started for {self.agent_id} (interval: {interval_seconds}s)")
        return True

    async def stop_dream_cycle(self) -> bool:
        """Stop the background dream processing loop."""
        if not self.dream.is_running:
            return False
        await self.dream.stop()
        logger.info(f"Dream cycle stopped for {self.agent_id}")
        return True

    async def run_dream_cycle_once(self) -> DreamCycleResult:
        """Manually trigger a single dream cycle and return results."""
        return await self.dream.run_dream_cycle()

    def get_dream_insights(self, limit: int = 20) -> list[dict]:
        """Get stored dream insights."""
        return self.dream.get_insights(limit)

    def get_dream_status(self) -> dict:
        """Get dream engine status."""
        return self.dream.get_status()

    # ── Statistics and Introspection ───────────────────────

    def get_routing_stats(self) -> dict:
        return model_router.get_usage_stats()

    def get_context_stats(self) -> dict:
        return self.context.get_stats()

    def get_tool_stats(self) -> dict:
        return tool_registry.get_execution_stats()

    def get_reasoning_stats(self) -> dict:
        return self.reasoning.get_stats()

    def get_plan_stats(self) -> dict:
        return planning_engine.get_stats()

    def get_engine_stats(self) -> dict:
        """Get comprehensive engine statistics."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "iteration_budget": {
                "max": self._iteration_budget.max_iterations,
                "used": self._iteration_budget._used,
                "remaining": self._iteration_budget.remaining,
                "exhausted": self._iteration_budget.is_exhausted,
            },
            "tokens": {
                "total_used": self._total_tokens_used,
            },
            "routing": self.get_routing_stats(),
            "context": self.get_context_stats(),
            "tools": self.get_tool_stats(),
            "reasoning": self.get_reasoning_stats(),
            "memory": {
                "total": len(self.memory._short_term_buffer),
            },
            "workspace": self.workspace.get_stats(),
            "dream": self.dream.get_status(),
        }