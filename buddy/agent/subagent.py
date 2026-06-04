"""Buddy SubAgent System — parallel task delegation and worker orchestration

Spawns lightweight sub-agents for parallel workstreams, enabling
concurrent task execution without context pollution.
"""
from __future__ import annotations
import logging
import uuid
import asyncio
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
    """Lightweight worker agent for parallel task execution."""

    def __init__(self, name: str, instructions: str, parent_agent_id: str):
        self.id = f"sub-{uuid.uuid4().hex[:8]}"
        self.name = name
        self.instructions = instructions
        self.parent_agent_id = parent_agent_id
        self.status = SubAgentStatus.IDLE
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    async def execute(self, task: str, model: str = "gpt-4o-mini") -> SubAgentResult:
        self.status = SubAgentStatus.RUNNING
        started_at = datetime.now(timezone.utc).isoformat()

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are {self.name}, a sub-agent. {self.instructions}\nExecute the assigned task concisely and return results."},
                    {"role": "user", "content": task},
                ],
                temperature=0.5,
                max_tokens=2048,
            )

            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

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
            return_exceptions=False,
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