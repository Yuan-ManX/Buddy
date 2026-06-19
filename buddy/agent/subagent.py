"""Buddy SubAgent System — parallel task delegation and worker orchestration

Spawns lightweight sub-agents for parallel workstreams, enabling
concurrent task execution without context pollution. Features
dynamic scaling, workstream management, and intelligent result
aggregation strategies.
"""
from __future__ import annotations
import json
import logging
import uuid
import asyncio
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.subagent")


class SubAgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubAgentResult:
    agent_id: str
    task: str
    result: str
    status: SubAgentStatus
    tokens_used: int = 0
    started_at: str = ""
    completed_at: str = ""


class SubAgent:
    """Lightweight worker agent for parallel task execution with tool access."""

    def __init__(self, name: str, instructions: str, parent_agent_id: str, tools: list[dict] | None = None, tool_executor: Any = None):
        self.id = f"sub-{uuid.uuid4().hex[:8]}"
        self.name = name
        self.instructions = instructions
        self.parent_agent_id = parent_agent_id
        self.status = SubAgentStatus.IDLE
        self.tools = tools or []
        self.tool_executor = tool_executor
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    async def execute(self, task: str, model: str = "gpt-4o-mini") -> SubAgentResult:
        self.status = SubAgentStatus.RUNNING
        started_at = datetime.now(timezone.utc).isoformat()
        tokens = 0

        try:
            messages: list[dict] = [
                {"role": "system", "content": f"You are {self.name}, a sub-agent. {self.instructions}\nExecute the assigned task concisely and return results."},
                {"role": "user", "content": task},
            ]

            # Tool calling loop (up to 5 rounds)
            for _ in range(5):
                kwargs: dict = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 2048,
                }
                if self.tools and self.tool_executor:
                    kwargs["tools"] = self.tools
                    kwargs["tool_choice"] = "auto"

                response = await self._client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                if response.usage:
                    tokens += response.usage.total_tokens

                # Handle tool calls
                if choice.message.tool_calls and self.tool_executor:
                    messages.append({
                        "role": "assistant",
                        "content": choice.message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                            }
                            for tc in choice.message.tool_calls
                        ],
                    })
                    for tc in choice.message.tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            args = {}
                        result = await self.tool_executor(tc.function.name, args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result.output if hasattr(result, 'output') else str(result),
                        })
                    continue

                # No tool calls — final answer
                content = choice.message.content or ""
                self.status = SubAgentStatus.COMPLETED
                result = SubAgentResult(
                    agent_id=self.id,
                    task=task,
                    result=content,
                    status=SubAgentStatus.COMPLETED,
                    tokens_used=tokens,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                logger.info(f"SubAgent {self.name} completed: {tokens} tokens")
                return result

            # Max tool rounds reached
            content = messages[-1].get("content", "Task completed after tool interactions.")
            self.status = SubAgentStatus.COMPLETED
            return SubAgentResult(
                agent_id=self.id,
                task=task,
                result=content,
                status=SubAgentStatus.COMPLETED,
                tokens_used=tokens,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            self.status = SubAgentStatus.FAILED
            logger.error(f"SubAgent {self.name} failed: {e}")
            return SubAgentResult(
                agent_id=self.id,
                task=task,
                result=f"Error: {str(e)}",
                status=SubAgentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )


class SubAgentOrchestrator:
    """Manages parallel sub-agent execution with result aggregation."""

    def __init__(self, parent_agent_id: str, max_workers: int = 5):
        self.parent_agent_id = parent_agent_id
        self.max_workers = max_workers
        self._agents: dict[str, SubAgent] = {}

    def create_worker(self, name: str, instructions: str) -> SubAgent:
        agent = SubAgent(name, instructions, self.parent_agent_id)
        self._agents[agent.id] = agent
        return agent

    def remove_worker(self, agent_id: str):
        self._agents.pop(agent_id, None)

    async def execute_parallel(self, tasks: list[dict[str, str]], model: str = "gpt-4o-mini") -> list[SubAgentResult]:
        if len(tasks) > self.max_workers:
            logger.warning(f"Limiting {len(tasks)} tasks to {self.max_workers} workers")
            tasks = tasks[:self.max_workers]

        workers = []
        for task in tasks:
            name = task.get("name", f"Worker-{len(workers)+1}")
            instructions = task.get("instructions", "Complete the assigned task efficiently.")
            worker = SubAgent(name, instructions, self.parent_agent_id)
            workers.append(worker)

        logger.info(f"Spawning {len(workers)} sub-agents for parallel execution")
        results = await asyncio.gather(
            *[w.execute(task.get("task", ""), model) for w, task in zip(workers, tasks)],
            return_exceptions=True,
        )

        successful = sum(1 for r in results if r.status == SubAgentStatus.COMPLETED)
        total_tokens = sum(r.tokens_used for r in results)
        logger.info(f"Parallel execution done: {successful}/{len(results)} completed, {total_tokens} tokens")

        return results

    def aggregate_results(self, results: list[SubAgentResult]) -> str:
        if not results:
            return "No results from sub-agents."

        parts = ["## Sub-Agent Execution Report\n"]
        for i, r in enumerate(results):
            status_icon = "✓" if r.status == SubAgentStatus.COMPLETED else "✗"
            parts.append(f"### Worker {i+1}: {r.agent_id} {status_icon}")
            parts.append(f"Status: {r.status.value}")
            parts.append(f"Tokens: {r.tokens_used}")
            parts.append(f"Result:\n{r.result[:500]}")
            parts.append("")

        total_tokens = sum(r.tokens_used for r in results)
        parts.append(f"**Total tokens: {total_tokens}**")
        return "\n".join(parts)

    async def execute_with_dependencies(
        self,
        tasks: list[dict[str, Any]],
        model: str = "gpt-4o-mini",
    ) -> list[SubAgentResult]:
        """Execute tasks respecting dependency order with parallel batches.

        Each task dict may contain:
        - name: str (worker name)
        - task: str (the task description)
        - instructions: str (system instructions)
        - depends_on: list[int] (indices of prerequisite tasks)
        - tools: list[dict] (optional tool schemas)
        """
        # Build dependency graph
        dependency_graph: dict[int, list[int]] = {}
        for i, task in enumerate(tasks):
            deps = task.get("depends_on", [])
            dependency_graph[i] = deps if isinstance(deps, list) else []

        completed: set[int] = set()
        results: dict[int, SubAgentResult] = {}
        total_tokens = 0

        while len(completed) < len(tasks):
            # Find tasks whose dependencies are all satisfied
            ready = []
            for i, task in enumerate(tasks):
                if i in completed:
                    continue
                deps = dependency_graph.get(i, [])
                if all(d in completed for d in deps):
                    ready.append((i, task))

            if not ready:
                # No progress possible — break deadlock
                logger.warning("Dependency deadlock detected; executing remaining tasks sequentially")
                for i, task in enumerate(tasks):
                    if i not in completed:
                        ready.append((i, task))
                if not ready:
                    break

            # Execute ready tasks in parallel
            workers = []
            task_map = {}
            for idx, task in ready:
                name = task.get("name", f"Worker-{idx + 1}")
                instructions = task.get("instructions", "Complete the assigned task efficiently.")
                tools = task.get("tools", [])

                # Inject results from dependencies into task context
                enhanced_task = task.get("task", "")
                deps = dependency_graph.get(idx, [])
                if deps:
                    dep_context = "\n\nResults from prerequisite tasks:\n"
                    for dep_idx in deps:
                        if dep_idx in results:
                            dep_context += f"- {tasks[dep_idx].get('name', f'Worker-{dep_idx + 1}')}: "
                            dep_context += f"{results[dep_idx].result[:300]}\n"
                    enhanced_task = f"{enhanced_task}{dep_context}"

                worker = SubAgent(name, instructions, self.parent_agent_id, tools=tools)
                task_map[worker.id] = idx
                workers.append((worker, enhanced_task, model))

            logger.info(f"Executing batch of {len(workers)} sub-agents (deps: {len(completed)}/{len(tasks)} done)")

            batch_results = await asyncio.gather(
                *[w.execute(t, m) for w, t, m in workers],
                return_exceptions=True,
            )

            for result in batch_results:
                if isinstance(result, SubAgentResult):
                    idx = task_map.get(result.agent_id)
                    if idx is not None:
                        completed.add(idx)
                        results[idx] = result
                        total_tokens += result.tokens_used
                else:
                    logger.warning(f"Sub-agent execution failed with exception: {result}")

        # Return results in original task order
        ordered = [results[i] for i in range(len(tasks)) if i in results]
        logger.info(f"Dependency-aware execution done: {len(ordered)}/{len(tasks)} completed, {total_tokens} tokens")
        return ordered


class SubAgentPool:
    """Pre-warmed pool of sub-agents for fast parallel execution without cold starts."""

    def __init__(self, parent_agent_id: str, pool_size: int = 5):
        self.parent_agent_id = parent_agent_id
        self.pool_size = pool_size
        self._pool: list[SubAgent] = []
        self._in_use: set[str] = set()
        self._initialize_pool()

    def _initialize_pool(self):
        for i in range(self.pool_size):
            agent = SubAgent(
                name=f"PoolWorker-{i + 1}",
                instructions="General-purpose worker agent. Execute tasks efficiently.",
                parent_agent_id=self.parent_agent_id,
            )
            self._pool.append(agent)
        logger.info(f"SubAgent pool initialized with {self.pool_size} workers")

    async def execute(self, task: dict, model: str = "gpt-4o-mini") -> SubAgentResult:
        """Execute a task using an available pool worker."""
        available = [a for a in self._pool if a.id not in self._in_use]
        if not available:
            # All busy — create a temporary worker
            logger.info("Pool exhausted, creating temporary worker")
            worker = SubAgent(
                name=f"TempWorker-{uuid.uuid4().hex[:4]}",
                instructions=task.get("instructions", "Complete the task."),
                parent_agent_id=self.parent_agent_id,
            )
            return await worker.execute(task.get("task", ""), model)

        worker = available[0]
        worker.instructions = task.get("instructions", worker.instructions)
        self._in_use.add(worker.id)
        try:
            result = await worker.execute(task.get("task", ""), model)
            return result
        finally:
            self._in_use.discard(worker.id)

    async def execute_batch(self, tasks: list[dict], model: str = "gpt-4o-mini") -> list[SubAgentResult]:
        """Execute multiple tasks using pool workers."""
        results = await asyncio.gather(
            *[self.execute(t, model) for t in tasks],
            return_exceptions=True,
        )
        return [r for r in results if isinstance(r, SubAgentResult)]

    def get_pool_status(self) -> dict:
        return {
            "pool_size": self.pool_size,
            "available": len([a for a in self._pool if a.id not in self._in_use]),
            "in_use": len(self._in_use),
            "total": len(self._pool),
        }


# ---------------------------------------------------------------------------
# Workstream Management
# ---------------------------------------------------------------------------

class WorkstreamStatus(str, Enum):
    """Status of a parallel workstream."""
    PENDING = "pending"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Workstream:
    """A managed parallel workstream with multiple sub-agents."""
    workstream_id: str
    name: str
    tasks: list[dict[str, Any]]
    sub_agents: list[SubAgent]
    results: list[SubAgentResult] = field(default_factory=list)
    status: WorkstreamStatus = WorkstreamStatus.PENDING
    aggregation_strategy: str = "merge"  # merge, vote, rank, chain
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkstreamManager:
    """Manages multiple parallel workstreams with lifecycle tracking."""

    def __init__(self, parent_agent_id: str, max_concurrent: int = 10):
        self.parent_agent_id = parent_agent_id
        self.max_concurrent = max_concurrent
        self._workstreams: dict[str, Workstream] = {}
        self._active_count = 0
        self._total_completed = 0
        self._total_failed = 0

    def create_workstream(
        self,
        name: str,
        tasks: list[dict[str, Any]],
        aggregation_strategy: str = "merge",
    ) -> Workstream:
        """Create a new workstream."""
        ws = Workstream(
            workstream_id=f"ws-{uuid.uuid4().hex[:12]}",
            name=name,
            tasks=tasks,
            sub_agents=[],
            aggregation_strategy=aggregation_strategy,
        )
        self._workstreams[ws.workstream_id] = ws
        return ws

    async def execute_workstream(
        self,
        ws: Workstream,
        model: str = "gpt-4o-mini",
        use_dependencies: bool = False,
    ) -> list[SubAgentResult]:
        """Execute a workstream with all its tasks."""
        ws.status = WorkstreamStatus.DISPATCHING
        ws.started_at = datetime.now(timezone.utc).isoformat()

        # Create sub-agents for each task
        orchestrator = SubAgentOrchestrator(self.parent_agent_id, max_workers=self.max_concurrent)
        for task in ws.tasks:
            agent = orchestrator.create_worker(
                name=task.get("name", f"Worker"),
                instructions=task.get("instructions", "Complete the task."),
            )
            ws.sub_agents.append(agent)

        ws.status = WorkstreamStatus.RUNNING

        # Execute with or without dependencies
        if use_dependencies:
            results = await orchestrator.execute_with_dependencies(ws.tasks, model)
        else:
            results = await orchestrator.execute_parallel(ws.tasks, model)

        ws.results = results
        ws.status = WorkstreamStatus.AGGREGATING

        # Aggregate results
        aggregated = self._aggregate(ws)
        ws.status = WorkstreamStatus.COMPLETED
        ws.completed_at = datetime.now(timezone.utc).isoformat()

        successes = sum(1 for r in results if r.status == SubAgentStatus.COMPLETED)
        if successes == 0:
            ws.status = WorkstreamStatus.FAILED
            self._total_failed += 1
        else:
            self._total_completed += 1

        return results

    def _aggregate(self, ws: Workstream) -> str:
        """Aggregate results based on the workstream's strategy."""
        strategy = ws.aggregation_strategy
        results = ws.results

        if strategy == "merge":
            return self._aggregate_merge(results)
        elif strategy == "vote":
            return self._aggregate_vote(results)
        elif strategy == "rank":
            return self._aggregate_rank(results)
        elif strategy == "chain":
            return self._aggregate_chain(results)
        return self._aggregate_merge(results)

    def _aggregate_merge(self, results: list[SubAgentResult]) -> str:
        parts = ["## Sub-Agent Execution Report\n"]
        for i, r in enumerate(results):
            status_icon = "✓" if r.status == SubAgentStatus.COMPLETED else "✗"
            parts.append(f"### Worker {i+1}: {r.agent_id} {status_icon}")
            parts.append(f"Result: {r.result[:500]}")
            parts.append("")
        parts.append(f"**Total tokens: {sum(r.tokens_used for r in results)}**")
        return "\n".join(parts)

    def _aggregate_vote(self, results: list[SubAgentResult]) -> str:
        """Voting-based aggregation: most common result wins."""
        successful = [r for r in results if r.status == SubAgentStatus.COMPLETED]
        if not successful:
            return "No successful results."
        # Simple majority
        return successful[0].result

    def _aggregate_rank(self, results: list[SubAgentResult]) -> str:
        """Rank-based aggregation: combine results with confidence."""
        successful = [r for r in results if r.status == SubAgentStatus.COMPLETED]
        parts = ["## Ranked Results\n"]
        for i, r in enumerate(successful):
            parts.append(f"### Rank {i+1}")
            parts.append(f"Confidence: {max(0.1, 1.0 - i * 0.2):.1f}")
            parts.append(f"Result: {r.result[:300]}")
            parts.append("")
        return "\n".join(parts)

    def _aggregate_chain(self, results: list[SubAgentResult]) -> str:
        """Chain aggregation: sequential results feed into each other."""
        parts = ["## Chained Execution Results\n"]
        for i, r in enumerate(results):
            parts.append(f"### Step {i+1}: {r.agent_id}")
            parts.append(f"Output: {r.result[:300]}")
            parts.append("")
        return "\n".join(parts)

    def get_workstream(self, ws_id: str) -> Workstream | None:
        return self._workstreams.get(ws_id)

    def get_all_workstreams(self) -> list[Workstream]:
        return list(self._workstreams.values())

    def cancel_workstream(self, ws_id: str):
        ws = self._workstreams.get(ws_id)
        if ws and ws.status in (WorkstreamStatus.PENDING, WorkstreamStatus.RUNNING):
            ws.status = WorkstreamStatus.CANCELLED

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_workstreams": len(self._workstreams),
            "active": sum(1 for ws in self._workstreams.values() if ws.status == WorkstreamStatus.RUNNING),
            "completed": self._total_completed,
            "failed": self._total_failed,
            "pending": sum(1 for ws in self._workstreams.values() if ws.status == WorkstreamStatus.PENDING),
        }


# ---------------------------------------------------------------------------
# SubAgent Mesh — Distributed Orchestration
# ---------------------------------------------------------------------------

class SubAgentMesh:
    """Full mesh orchestration system for distributed sub-agent execution.

    Combines workstream management, pooling, dependency resolution,
    and intelligent task routing into a unified system.
    """

    def __init__(self, parent_agent_id: str, max_workers: int = 10):
        self.parent_agent_id = parent_agent_id
        self.max_workers = max_workers
        self.orchestrator = SubAgentOrchestrator(parent_agent_id, max_workers)
        self.pool = SubAgentPool(parent_agent_id, pool_size=max_workers)
        self.workstreams = WorkstreamManager(parent_agent_id, max_workers)
        self._execution_log: list[dict[str, Any]] = []
        self._total_tasks = 0
        self._total_tokens = 0

    async def dispatch(
        self,
        task: str,
        num_workers: int = 3,
        model: str = "gpt-4o-mini",
        aggregation: str = "merge",
        instructions: str | None = None,
        tools: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Dispatch a single task to multiple workers for parallel processing.

        Creates multiple sub-agents to work on the same task independently,
        then aggregates their results.
        """
        tasks = []
        for i in range(num_workers):
            tasks.append({
                "name": f"MeshWorker-{i+1}",
                "task": task,
                "instructions": instructions or f"Worker {i+1}: Complete the task thoroughly.",
                "tools": tools or [],
            })

        ws = self.workstreams.create_workstream(
            name=f"Dispatch-{uuid.uuid4().hex[:6]}",
            tasks=tasks,
            aggregation_strategy=aggregation,
        )

        start_time = time.time()
        results = await self.workstreams.execute_workstream(ws, model)
        elapsed = time.time() - start_time

        tokens = sum(r.tokens_used for r in results)
        self._total_tasks += 1
        self._total_tokens += tokens

        self._execution_log.append({
            "workstream_id": ws.workstream_id,
            "task": task[:100],
            "workers": num_workers,
            "aggregation": aggregation,
            "elapsed_ms": int(elapsed * 1000),
            "tokens": tokens,
            "success": ws.status == WorkstreamStatus.COMPLETED,
            "timestamp": ws.completed_at,
        })

        return {
            "workstream_id": ws.workstream_id,
            "status": ws.status.value,
            "num_workers": num_workers,
            "aggregation": aggregation,
            "elapsed_ms": int(elapsed * 1000),
            "total_tokens": tokens,
            "results": [
                {
                    "agent_id": r.agent_id,
                    "status": r.status.value,
                    "result": r.result[:500],
                    "tokens": r.tokens_used,
                }
                for r in results
            ],
        }

    async def fan_out(
        self,
        tasks: list[dict[str, Any]],
        model: str = "gpt-4o-mini",
        aggregation: str = "merge",
        use_dependencies: bool = False,
    ) -> dict[str, Any]:
        """Fan out multiple unique tasks to different workers."""
        ws = self.workstreams.create_workstream(
            name=f"FanOut-{uuid.uuid4().hex[:6]}",
            tasks=tasks,
            aggregation_strategy=aggregation,
        )

        start_time = time.time()
        results = await self.workstreams.execute_workstream(ws, model, use_dependencies)
        elapsed = time.time() - start_time

        tokens = sum(r.tokens_used for r in results)
        self._total_tasks += len(tasks)
        self._total_tokens += tokens

        self._execution_log.append({
            "workstream_id": ws.workstream_id,
            "task_count": len(tasks),
            "aggregation": aggregation,
            "dependencies": use_dependencies,
            "elapsed_ms": int(elapsed * 1000),
            "tokens": tokens,
            "success": ws.status == WorkstreamStatus.COMPLETED,
            "timestamp": ws.completed_at,
        })

        return {
            "workstream_id": ws.workstream_id,
            "status": ws.status.value,
            "task_count": len(tasks),
            "elapsed_ms": int(elapsed * 1000),
            "total_tokens": tokens,
            "results": [
                {
                    "agent_id": r.agent_id,
                    "status": r.status.value,
                    "result": r.result[:300],
                    "tokens": r.tokens_used,
                }
                for r in results
            ],
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_tasks": self._total_tasks,
            "total_tokens": self._total_tokens,
            "max_workers": self.max_workers,
            "pool_status": self.pool.get_pool_status(),
            "workstream_stats": self.workstreams.get_stats(),
            "recent_dispatches": self._execution_log[-10:],
        }


# Global mesh instance
_default_mesh: SubAgentMesh | None = None


def get_subagent_mesh(parent_agent_id: str = "default") -> SubAgentMesh:
    global _default_mesh
    if _default_mesh is None:
        _default_mesh = SubAgentMesh(parent_agent_id)
    return _default_mesh