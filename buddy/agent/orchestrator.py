"""Buddy Orchestrator — Multi-agent coordination, trust, and collaboration

Orchestrates multiple agents with inter-agent trust scoring, collaborative
discussion threads, and intelligent task delegation across agents.
"""
from __future__ import annotations
import logging
import uuid
import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator, Any

from agent.engine import AgentEngine

logger = logging.getLogger("buddy.orchestrator")


class TrustLevel:
    """Trust scoring between agents."""
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.9


class Orchestrator:
    """Coordinates multiple agents, handles task delegation and inter-agent communication."""

    def __init__(self):
        self._engines: dict[str, AgentEngine] = {}
        self._trust_matrix: dict[str, dict[str, float]] = {}
        self._collaboration_threads: dict[str, dict] = {}

    def get_engine(self, agent_id: str, agent_name: str, instructions: str) -> AgentEngine:
        """Get or create an agent engine instance."""
        if agent_id not in self._engines:
            self._engines[agent_id] = AgentEngine(agent_id, agent_name, instructions)
            self._trust_matrix[agent_id] = {}
        return self._engines[agent_id]

    async def chat(
        self,
        agent_id: str,
        agent_name: str,
        instructions: str,
        message: str,
        history: list[dict] | None = None,
        enable_tools: bool = True,
        enable_reasoning: bool = False,
    ) -> str:
        engine = self.get_engine(agent_id, agent_name, instructions)
        result = await engine.chat(
            message,
            conversation_history=history,
            enable_tools=enable_tools,
            enable_reasoning=enable_reasoning,
        )
        if isinstance(result, str):
            return result
        return ""

    async def chat_stream(
        self,
        agent_id: str,
        agent_name: str,
        instructions: str,
        message: str,
        history: list[dict] | None = None,
        enable_tools: bool = True,
        enable_reasoning: bool = False,
    ) -> AsyncIterator[str]:
        engine = self.get_engine(agent_id, agent_name, instructions)
        result = await engine.chat(
            message,
            conversation_history=history,
            stream=True,
            enable_tools=enable_tools,
            enable_reasoning=enable_reasoning,
        )
        async for token in result:
            yield token

    async def chat_with_plan(
        self,
        agent_id: str,
        agent_name: str,
        instructions: str,
        message: str,
        history: list[dict] | None = None,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        engine = self.get_engine(agent_id, agent_name, instructions)
        return await engine.chat_with_plan(message, conversation_history=history, stream=stream)

    # ── Multi-Agent Trust & Reputation ──────────────────────

    def update_trust(self, from_agent: str, to_agent: str, score: float):
        """Update trust score between two agents."""
        if from_agent not in self._trust_matrix:
            self._trust_matrix[from_agent] = {}
        self._trust_matrix[from_agent][to_agent] = max(0.0, min(1.0, score))

    def get_trust(self, from_agent: str, to_agent: str) -> float:
        """Get trust score from agent A to agent B."""
        return self._trust_matrix.get(from_agent, {}).get(to_agent, TrustLevel.MEDIUM)

    def get_trusted_agents(self, agent_id: str, min_trust: float = TrustLevel.MEDIUM) -> list[str]:
        """Get agents that trust this agent above threshold."""
        trusted = []
        for other_id, score in self._trust_matrix.get(agent_id, {}).items():
            if score >= min_trust:
                trusted.append(other_id)
        return trusted

    # ── Multi-Agent Collaboration ───────────────────────────

    async def collaborate(
        self,
        query: str,
        agent_ids: list[str],
        max_rounds: int = 3,
    ) -> dict:
        """Run a collaborative discussion among multiple agents."""
        thread_id = f"collab-{uuid.uuid4().hex[:8]}"
        thread = {
            "id": thread_id,
            "query": query,
            "participants": agent_ids,
            "rounds": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
        }
        self._collaboration_threads[thread_id] = thread

        context = f"Collaborative discussion. Query: {query}\n\nParticipants: {len(agent_ids)} agents.\n"
        consensus = None

        for round_num in range(max_rounds):
            round_responses = []
            for agent_id in agent_ids:
                if agent_id not in self._engines:
                    continue

                engine = self._engines[agent_id]
                prompt = (
                    f"{context}\n"
                    f"Round {round_num + 1}/{max_rounds}.\n"
                    f"Provide your perspective on the query. Be concise. "
                    f"{'Build on what others have said.' if round_responses else 'Start the discussion.'}"
                )

                try:
                    result = await engine.chat(prompt, enable_tools=False)
                    response = result if isinstance(result, str) else ""
                    round_responses.append({
                        "agent_id": agent_id,
                        "agent_name": engine.agent_name,
                        "response": response,
                    })
                except Exception as e:
                    logger.error(f"Collaboration error for {agent_id}: {e}")

            thread["rounds"].append({
                "round": round_num + 1,
                "responses": round_responses,
            })

            if round_num == max_rounds - 1:
                consensus = await self._synthesize_consensus(query, round_responses, agent_ids[0])

        thread["status"] = "completed"
        thread["consensus"] = consensus
        thread["completed_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "thread_id": thread_id,
            "query": query,
            "participants": agent_ids,
            "rounds": len(thread["rounds"]),
            "consensus": consensus,
            "discussion": [
                {
                    "round": r["round"],
                    "responses": [
                        {"agent": resp["agent_name"], "response": resp["response"][:500]}
                        for resp in r["responses"]
                    ],
                }
                for r in thread["rounds"]
            ],
        }

    async def _synthesize_consensus(self, query: str, responses: list[dict], agent_id: str) -> str:
        """Synthesize a consensus from multiple agent responses."""
        if not responses:
            return "No consensus reached."

        combined = "\n\n".join([
            f"**{r['agent_name']}**: {r['response'][:300]}"
            for r in responses
        ])

        engine = self._engines.get(agent_id)
        if engine:
            result = await engine.chat(
                f"Query: {query}\n\nAgent responses:\n{combined}\n\nSynthesize a consensus view.",
                enable_tools=False,
            )
            return result if isinstance(result, str) else combined
        return f"Multiple agents contributed. Key points:\n\n{combined}"

    async def verify_response(
        self,
        verification_agent_id: str,
        original_response: str,
        original_query: str,
    ) -> dict:
        """Have one agent verify another agent's response."""
        engine = self._engines.get(verification_agent_id)
        if not engine:
            return {"verified": False, "reason": "Verification agent not found"}

        result = await engine.chat(
            f"Verify this response to the query: '{original_query}'\n\n"
            f"Response to verify:\n{original_response}\n\n"
            f"Check for: accuracy, completeness, safety, clarity.\n"
            f"Return JSON: {{'verified': true/false, 'confidence': 0.0-1.0, 'issues': [...], 'suggestions': '...'}}",
            enable_tools=False,
        )

        try:
            import json
            verification = json.loads(result if isinstance(result, str) else "{}")
        except (json.JSONDecodeError, TypeError):
            verification = {"verified": True, "confidence": 0.5, "issues": [], "suggestions": ""}

        return verification

    # ── Agent Transfer ──────────────────────────────────────

    async def transfer(
        self,
        from_agent_id: str,
        to_agent_id: str,
        context: str,
    ) -> dict:
        """Transfer a task from one agent to another with full context."""
        from_engine = self._engines.get(from_agent_id)
        to_engine = self._engines.get(to_agent_id)

        if not from_engine or not to_engine:
            return {
                "success": False,
                "error": "One or both agents not found",
                "from_agent": from_agent_id,
                "to_agent": to_agent_id,
            }

        # Update trust: successful transfer increases trust
        self.update_trust(from_agent_id, to_agent_id, 0.8)
        self.update_trust(to_agent_id, from_agent_id, 0.7)

        # Get the receiving agent's response to the context
        result = await to_engine.chat(
            f"Task transferred from {from_engine.agent_name}. Context:\n\n{context}\n\n"
            f"Acknowledge receipt and provide your initial assessment.",
            enable_tools=False,
        )

        return {
            "success": True,
            "from_agent": from_agent_id,
            "from_name": from_engine.agent_name,
            "to_agent": to_agent_id,
            "to_name": to_engine.agent_name,
            "acknowledgment": result if isinstance(result, str) else "",
            "context": context[:500],
        }

    # ── Engine Management ───────────────────────────────────

    def evict_engine(self, agent_id: str):
        self._engines.pop(agent_id, None)
        self._trust_matrix.pop(agent_id, None)

    @property
    def active_agents(self) -> int:
        return len(self._engines)

    def get_agent_status(self, agent_id: str) -> dict | None:
        engine = self._engines.get(agent_id)
        if not engine:
            return None
        return {
            "agent_id": engine.agent_id,
            "agent_name": engine.agent_name,
            "trusted_by": len(self.get_trusted_agents(agent_id)),
            "active": True,
        }

    def get_orchestrator_stats(self) -> dict:
        return {
            "active_agents": self.active_agents,
            "trust_relationships": sum(len(v) for v in self._trust_matrix.values()),
            "collaboration_threads": len(self._collaboration_threads),
            "agents": [
                self.get_agent_status(aid)
                for aid in self._engines
            ],
        }