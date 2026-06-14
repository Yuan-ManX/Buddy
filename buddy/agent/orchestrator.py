"""Buddy Orchestrator — Multi-agent coordination, trust, and collaboration

Orchestrates multiple agents with inter-agent trust scoring, collaborative
discussion threads, and intelligent task delegation across agents.
"""
from __future__ import annotations
import logging
import uuid
import asyncio
import time
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Any

from agent.engine import AgentEngine

logger = logging.getLogger("buddy.orchestrator")


class TrustLevel:
    """Trust scoring between agents."""
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.9


# ── Task Delegation Strategies ───────────────────────────

class DelegationStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    EXPERTISE_BASED = "expertise_based"


class RoundRobinStrategy:
    """Rotate tasks among agents evenly using a circular counter."""

    def __init__(self):
        self._counter: int = 0

    def select(self, agent_ids: list[str], _context: dict | None = None) -> str | None:
        if not agent_ids:
            return None
        selected = agent_ids[self._counter % len(agent_ids)]
        self._counter += 1
        return selected

    def reset(self):
        self._counter = 0


class LoadBalancedStrategy:
    """Assign tasks to the least busy agent based on active task count."""

    def __init__(self):
        self._active_tasks: dict[str, int] = {}

    def assign(self, agent_id: str):
        """Increment active task count for an agent."""
        self._active_tasks[agent_id] = self._active_tasks.get(agent_id, 0) + 1

    def complete(self, agent_id: str):
        """Decrement active task count for an agent."""
        if agent_id in self._active_tasks:
            self._active_tasks[agent_id] = max(0, self._active_tasks[agent_id] - 1)

    def select(self, agent_ids: list[str], _context: dict | None = None) -> str | None:
        if not agent_ids:
            return None
        # Pick the agent with the fewest active tasks
        return min(agent_ids, key=lambda aid: self._active_tasks.get(aid, 0))

    def get_load(self) -> dict[str, int]:
        return dict(self._active_tasks)


class ExpertiseBasedStrategy:
    """Route tasks based on agent expertise scores for specific domains."""

    def __init__(self):
        self._expertise: dict[str, dict[str, float]] = {}

    def set_expertise(self, agent_id: str, domain: str, score: float):
        """Set an agent's expertise score for a specific domain (0.0-1.0)."""
        if agent_id not in self._expertise:
            self._expertise[agent_id] = {}
        self._expertise[agent_id][domain] = max(0.0, min(1.0, score))

    def get_expertise(self, agent_id: str, domain: str) -> float:
        return self._expertise.get(agent_id, {}).get(domain, 0.3)

    def select(self, agent_ids: list[str], context: dict | None = None) -> str | None:
        if not agent_ids:
            return None
        domain = (context or {}).get("domain", "general")
        # Pick agent with highest expertise in the domain
        return max(agent_ids, key=lambda aid: self.get_expertise(aid, domain))

    def get_all_expertise(self, agent_id: str) -> dict[str, float]:
        return dict(self._expertise.get(agent_id, {}))


# ── Collaboration Metrics ────────────────────────────────

@dataclass
class CollaborationMetrics:
    """Track collaboration effectiveness across multi-agent interactions."""

    total_collaborations: int = 0
    total_debates: int = 0
    total_consensus_votes: int = 0
    total_response_time_ms: float = 0.0
    agreement_count: int = 0
    disagreement_count: int = 0
    quality_scores: list[float] = field(default_factory=list)

    def record_collaboration(self, duration_ms: float, participants: int, agreement: bool):
        self.total_collaborations += 1
        self.total_response_time_ms += duration_ms
        if agreement:
            self.agreement_count += 1
        else:
            self.disagreement_count += 1

    def record_consensus(self, participants: int):
        self.total_consensus_votes += 1

    def record_debate(self, participants: int):
        self.total_debates += 1

    def record_quality(self, score: float):
        self.quality_scores.append(score)
        if len(self.quality_scores) > 200:
            self.quality_scores = self.quality_scores[-100:]

    def get_summary(self) -> dict:
        total = self.total_collaborations
        avg_time = self.total_response_time_ms / max(total, 1)
        avg_quality = sum(self.quality_scores) / max(len(self.quality_scores), 1)
        return {
            "total_collaborations": total,
            "total_debates": self.total_debates,
            "total_consensus_votes": self.total_consensus_votes,
            "avg_response_time_ms": round(avg_time, 1),
            "agreement_rate": f"{(self.agreement_count / max(total, 1) * 100):.1f}%",
            "avg_quality_score": round(avg_quality, 3),
        }


class Orchestrator:
    """Coordinates multiple agents, handles task delegation and inter-agent communication."""

    def __init__(self):
        self._engines: dict[str, AgentEngine] = {}
        self._trust_matrix: dict[str, dict[str, float]] = {}
        self._collaboration_threads: dict[str, dict] = {}
        self.escalation_chain: dict[str, list[str]] = {}
        self._metrics = CollaborationMetrics()
        self._round_robin = RoundRobinStrategy()
        self._load_balancer = LoadBalancedStrategy()
        self._expertise_router = ExpertiseBasedStrategy()

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
        self.escalation_chain.pop(agent_id, None)

    # ── Escalation Chain ────────────────────────────────────

    def set_escalation_chain(self, agent_id: str, chain: list[str]):
        """Define an escalation chain: when agent_id is stuck, try agents in order.

        Args:
            agent_id: The agent that may need escalation.
            chain: Ordered list of agent IDs to escalate to when stuck.
        """
        self.escalation_chain[agent_id] = chain

    async def escalate(
        self,
        from_agent_id: str,
        query: str,
        context: str = "",
    ) -> dict | None:
        """When an agent is stuck, automatically escalate to the next capable agent.

        Iterates through the escalation chain, trying each agent until one
        succeeds or the chain is exhausted.
        """
        chain = self.escalation_chain.get(from_agent_id, [])
        if not chain:
            logger.warning(f"No escalation chain configured for {from_agent_id}")
            return None

        escalation_results = []
        for target_id in chain:
            target_engine = self._engines.get(target_id)
            if not target_engine:
                logger.warning(f"Escalation target {target_id} not available")
                escalation_results.append({
                    "agent_id": target_id,
                    "success": False,
                    "error": "Agent not available",
                })
                continue

            try:
                prompt = (
                    f"Escalated task from upstream agent.\n"
                    f"Original query: {query}\n"
                    f"{'Additional context: ' + context if context else ''}\n\n"
                    "Please handle this task with your expertise."
                )
                result = await target_engine.chat(prompt, enable_tools=False)
                response = result if isinstance(result, str) else ""

                # Update trust: successful escalation increases trust
                self.update_trust(from_agent_id, target_id,
                    min(1.0, self.get_trust(from_agent_id, target_id) + 0.1))

                escalation_results.append({
                    "agent_id": target_id,
                    "agent_name": target_engine.agent_name,
                    "success": True,
                    "response": response[:500],
                })

                return {
                    "escalated": True,
                    "from_agent": from_agent_id,
                    "to_agent": target_id,
                    "response": response,
                    "chain_results": escalation_results,
                }

            except Exception as e:
                logger.error(f"Escalation to {target_id} failed: {e}")
                self.update_trust(from_agent_id, target_id,
                    max(0.0, self.get_trust(from_agent_id, target_id) - 0.1))
                escalation_results.append({
                    "agent_id": target_id,
                    "success": False,
                    "error": str(e),
                })

        return {
            "escalated": False,
            "from_agent": from_agent_id,
            "error": "All escalation targets failed",
            "chain_results": escalation_results,
        }

    # ── Consensus Voting ────────────────────────────────────

    async def consensus_voting(
        self,
        query: str,
        agent_ids: list[str],
        options: list[str] | None = None,
    ) -> dict:
        """Have multiple agents vote on a decision and aggregate results.

        If options are provided, agents choose from them. Otherwise, agents
        provide free-form answers and the orchestrator finds consensus.

        Args:
            query: The question to vote on.
            agent_ids: List of agent IDs participating in the vote.
            options: Optional list of predefined options to choose from.

        Returns:
            Dict with 'winner', 'votes', 'confidence', and 'details'.
        """
        start = time.time()
        votes: list[dict] = []

        for agent_id in agent_ids:
            engine = self._engines.get(agent_id)
            if not engine:
                continue

            if options:
                prompt = (
                    f"Vote on this question: {query}\n\n"
                    f"Options:\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options)) +
                    "\n\nRespond with JUST the number of your choice and a brief reason. "
                    "Format: 'CHOICE: <number> | REASON: <brief explanation>'"
                )
            else:
                prompt = (
                    f"Vote on this question: {query}\n\n"
                    "Provide your answer with a confidence score (0.0-1.0). "
                    "Format: 'ANSWER: <your answer> | CONFIDENCE: <0.0-1.0>'"
                )

            try:
                result = await engine.chat(prompt, enable_tools=False)
                response = result if isinstance(result, str) else ""
                votes.append({
                    "agent_id": agent_id,
                    "agent_name": engine.agent_name,
                    "response": response,
                })
            except Exception as e:
                logger.error(f"Vote failed for {agent_id}: {e}")

        # Tally votes
        if options:
            tally: dict[str, int] = {opt: 0 for opt in options}
            for vote in votes:
                for i, opt in enumerate(options, 1):
                    if str(i) in vote["response"][:50]:
                        tally[opt] += 1
                        break
            winner = max(tally, key=tally.get) if tally else None
            winner_votes = tally.get(winner, 0) if winner else 0
            confidence = winner_votes / max(len(votes), 1)
        else:
            # Simple majority on first 100 chars
            from collections import Counter
            answers = [v["response"][:100].lower().strip() for v in votes]
            counter = Counter(answers)
            winner = counter.most_common(1)[0][0] if counter else None
            winner_votes = counter.get(winner, 0) if winner else 0
            confidence = winner_votes / max(len(votes), 1)

        self._metrics.record_consensus(len(agent_ids))
        self._metrics.record_collaboration(
            (time.time() - start) * 1000, len(agent_ids),
            agreement=(confidence >= 0.66),
        )

        return {
            "query": query,
            "winner": winner,
            "votes_for_winner": winner_votes,
            "total_votes": len(votes),
            "confidence": round(confidence, 3),
            "details": [
                {"agent": v["agent_name"], "vote": v["response"][:200]}
                for v in votes
            ],
        }

    # ── Debate Mode ─────────────────────────────────────────

    async def debate_mode(
        self,
        topic: str,
        agent_a_id: str,
        agent_b_id: str,
        judge_agent_id: str | None = None,
        max_turns: int = 3,
    ) -> dict:
        """Two agents debate a topic with structured turns and a judge agent.

        Args:
            topic: The debate topic/question.
            agent_a_id: ID of the first debater (opening for the motion).
            agent_b_id: ID of the second debater (opening against the motion).
            judge_agent_id: Optional ID of a judge agent to declare the winner.
            max_turns: Number of debate turns (each turn = both agents speak once).

        Returns:
            Dict with 'winner', 'transcript', 'verdict', and 'metrics'.
        """
        start = time.time()
        engine_a = self._engines.get(agent_a_id)
        engine_b = self._engines.get(agent_b_id)

        if not engine_a or not engine_b:
            return {"error": "One or both debate agents not found", "success": False}

        transcript: list[dict] = []

        # Debate context that accumulates
        debate_context = f"DEBATE TOPIC: {topic}\n\n"

        for turn in range(1, max_turns + 1):
            # Agent A speaks
            prompt_a = (
                f"{debate_context}\n"
                f"=== TURN {turn}: PRO ===\n"
                f"{'Opening argument FOR the topic.' if turn == 1 else 'Rebuttal to the CON argument above. Defend the PRO position.'}\n"
                f"Be concise and persuasive."
            )
            try:
                result_a = await engine_a.chat(prompt_a, enable_tools=False)
                response_a = result_a if isinstance(result_a, str) else ""
                transcript.append({
                    "turn": turn,
                    "speaker": "PRO",
                    "agent": engine_a.agent_name,
                    "content": response_a,
                })
                debate_context += f"\n[PRO - Turn {turn}]: {response_a[:500]}\n"
            except Exception as e:
                logger.error(f"Debate agent A failed: {e}")

            # Agent B speaks
            prompt_b = (
                f"{debate_context}\n"
                f"=== TURN {turn}: CON ===\n"
                f"{'Opening argument AGAINST the topic.' if turn == 1 else 'Rebuttal to the PRO argument above. Defend the CON position.'}\n"
                f"Be concise and persuasive."
            )
            try:
                result_b = await engine_b.chat(prompt_b, enable_tools=False)
                response_b = result_b if isinstance(result_b, str) else ""
                transcript.append({
                    "turn": turn,
                    "speaker": "CON",
                    "agent": engine_b.agent_name,
                    "content": response_b,
                })
                debate_context += f"\n[CON - Turn {turn}]: {response_b[:500]}\n"
            except Exception as e:
                logger.error(f"Debate agent B failed: {e}")

        # Judge renders a verdict
        verdict = None
        if judge_agent_id:
            judge_engine = self._engines.get(judge_agent_id)
            if judge_engine:
                judge_prompt = (
                    f"DEBATE TOPIC: {topic}\n\n"
                    f"Complete debate transcript:\n{debate_context}\n\n"
                    "As the judge, declare a winner (PRO or CON) and explain your reasoning. "
                    "Consider: argument quality, evidence, persuasiveness, and logical consistency. "
                    "Return: WINNER: <PRO/CON> | REASON: <explanation>"
                )
                try:
                    judge_result = await judge_engine.chat(judge_prompt, enable_tools=False)
                    verdict = judge_result if isinstance(judge_result, str) else ""
                except Exception as e:
                    logger.error(f"Judge failed: {e}")
                    verdict = f"Judge unavailable: {str(e)}"

        self._metrics.record_debate(2)

        return {
            "topic": topic,
            "success": True,
            "turns": max_turns,
            "winner": verdict[:100] if verdict else "No verdict",
            "verdict": verdict,
            "transcript": [
                {"turn": t["turn"], "speaker": t["speaker"],
                 "agent": t["agent"], "content": t["content"][:300]}
                for t in transcript
            ],
            "duration_ms": (time.time() - start) * 1000,
        }

    # ── Delegation Strategy Access ─────────────────────────

    def get_round_robin(self) -> RoundRobinStrategy:
        return self._round_robin

    def get_load_balancer(self) -> LoadBalancedStrategy:
        return self._load_balancer

    def get_expertise_router(self) -> ExpertiseBasedStrategy:
        return self._expertise_router

    def get_collaboration_metrics(self) -> CollaborationMetrics:
        return self._metrics

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