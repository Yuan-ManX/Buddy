"""Buddy Agent Orchestrator — Multi-agent coordination and delegation"""
import logging
from typing import AsyncIterator

from agent.engine import AgentEngine

logger = logging.getLogger("buddy.orchestrator")


class Orchestrator:
    """Coordinates multiple agents, handles task delegation and inter-agent communication."""

    def __init__(self):
        self._engines: dict[str, AgentEngine] = {}

    def get_engine(self, agent_id: str, agent_name: str, instructions: str) -> AgentEngine:
        if agent_id not in self._engines:
            self._engines[agent_id] = AgentEngine(agent_id, agent_name, instructions)
        return self._engines[agent_id]

    async def chat(
        self,
        agent_id: str,
        agent_name: str,
        instructions: str,
        message: str,
        history: list[dict] | None = None,
    ) -> str:
        engine = self.get_engine(agent_id, agent_name, instructions)
        return await engine.chat(message, conversation_history=history)

    async def chat_stream(
        self,
        agent_id: str,
        agent_name: str,
        instructions: str,
        message: str,
        history: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        engine = self.get_engine(agent_id, agent_name, instructions)
        result = await engine.chat(message, conversation_history=history, stream=True)
        async for token in result:
            yield token

    async def transfer(
        self,
        from_agent_id: str,
        to_agent_id: str,
        context: str,
    ) -> str:
        return (
            f"## Task Transfer\n\n"
            f"From: Agent {from_agent_id}\n"
            f"To: Agent {to_agent_id}\n\n"
            f"**Context**:\n\n{context}\n\n"
            f"_Multi-agent task transfer initialized._"
        )

    def evict_engine(self, agent_id: str):
        self._engines.pop(agent_id, None)

    @property
    def active_agents(self) -> int:
        return len(self._engines)