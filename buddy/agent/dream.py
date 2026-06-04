"""Buddy Dream Mode — background memory consolidation and creative synthesis

Implements a "dream" cycle where agents process accumulated memories during
idle periods, consolidating knowledge, resolving contradictions, forming
new connections, and generating creative insights.
"""
from __future__ import annotations
import logging
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.dream")


class DreamPhase(str, Enum):
    REVIEW = "review"       # Scanning recent memories
    CONSOLIDATE = "consolidate"  # Merging related memories
    SYNTHESIZE = "synthesize"   # Creating new connections
    RESOLVE = "resolve"     # Handling contradictions
    REFLECT = "reflect"     # Self-analysis and growth


@dataclass
class DreamInsight:
    id: str
    phase: DreamPhase
    content: str
    source_memories: list[str]
    confidence: float = 0.5
    created_at: str = ""


@dataclass
class DreamCycleResult:
    insights: list[DreamInsight]
    memories_processed: int
    memories_consolidated: int
    duration_seconds: float
    started_at: str
    completed_at: str


class DreamEngine:
    """Background memory processing engine for agents."""

    def __init__(self, agent_id: str, memory_system: Any, client: AsyncOpenAI | None = None):
        self.agent_id = agent_id
        self.memory = memory_system
        self._insights: list[DreamInsight] = []
        self._is_running = False
        self._client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._dream_interval = 3600  # 1 hour default
        self._dream_task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self, interval: int = 3600):
        """Start periodic dream cycles (synchronous wrapper)."""
        self._dream_interval = interval
        self._is_running = True
        if self._dream_task:
            self._dream_task.cancel()
        self._dream_task = asyncio.create_task(self._dream_loop())
        logger.info(f"Dream engine started for agent {self.agent_id} (interval: {interval}s)")

    def get_insights(self, limit: int = 20) -> list[dict]:
        """Get stored dream insights."""
        return [
            {
                "id": i.id,
                "phase": i.phase.value,
                "content": i.content,
                "source_memories": i.source_memories,
                "confidence": i.confidence,
                "created_at": i.created_at,
            }
            for i in self._insights[-limit:]
        ]

    def get_status(self) -> dict:
        """Get dream engine status."""
        return {
            "agent_id": self.agent_id,
            "is_running": self._is_running,
            "interval_seconds": self._dream_interval,
            "total_insights": len(self._insights),
            "latest_insight": self._insights[-1].content[:200] if self._insights else "",
        }

    async def start_cycle(self, interval: int = 3600):
        """Start periodic dream cycles."""
        self._dream_interval = interval
        if self._dream_task:
            self._dream_task.cancel()

        self._dream_task = asyncio.create_task(self._dream_loop())
        logger.info(f"Dream engine started for agent {self.agent_id}")

    async def stop(self):
        """Stop dream cycles."""
        if self._dream_task:
            self._dream_task.cancel()
            self._dream_task = None
        self._is_running = False
        logger.info(f"Dream engine stopped for agent {self.agent_id}")

    async def _dream_loop(self):
        """Main dream cycle loop."""
        await asyncio.sleep(10)  # Initial delay
        self._is_running = True

        while self._is_running:
            try:
                await self.run_dream_cycle()
            except Exception as e:
                logger.error(f"Dream cycle error for {self.agent_id}: {e}")
            await asyncio.sleep(self._dream_interval)

    async def run_dream_cycle(self) -> DreamCycleResult:
        """Execute a complete dream cycle."""
        started_at = datetime.now(timezone.utc).isoformat()
        import time
        start = time.time()

        insights = []
        memories_processed = 0
        memories_consolidated = 0

        try:
            # Phase 1: Review recent memories
            recent = await self.memory.recall_recent(limit=20)
            memories_processed += len(recent)

            if recent:
                review_insight = await self._phase_review(recent)
                if review_insight:
                    insights.append(review_insight)

            # Phase 2: Consolidate high-importance memories
            long_term = await self.memory.recall_long_term(limit=15)
            if long_term and len(long_term) > 5:
                consolidate_insight = await self._phase_consolidate(long_term)
                if consolidate_insight:
                    insights.append(consolidate_insight)
                    memories_consolidated += len(long_term)

            # Phase 3: Synthesize new connections
            if len(recent) + len(long_term) > 10:
                all_memories = recent + long_term
                synthesis_insight = await self._phase_synthesize(all_memories)
                if synthesis_insight:
                    insights.append(synthesis_insight)

            # Phase 4: Resolve contradictions
            if len(long_term) > 3:
                resolve_insight = await self._phase_resolve(long_term)
                if resolve_insight:
                    insights.append(resolve_insight)

            # Phase 5: Reflect and self-improve
            reflect_insight = await self._phase_reflect()
            if reflect_insight:
                insights.append(reflect_insight)

            # Store insights
            for insight in insights:
                self._insights.append(insight)
                await self.memory.store(
                    content=f"[Dream Insight] {insight.content}",
                    memory_type="insight",
                    importance=0.7,
                )

        except Exception as e:
            logger.error(f"Dream cycle error: {e}")

        elapsed = time.time() - start
        completed_at = datetime.now(timezone.utc).isoformat()

        result = DreamCycleResult(
            insights=insights,
            memories_processed=memories_processed,
            memories_consolidated=memories_consolidated,
            duration_seconds=elapsed,
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(
            f"Dream cycle complete: {len(insights)} insights, "
            f"{memories_processed} processed, {elapsed:.1f}s"
        )
        return result

    async def _phase_review(self, memories: list[dict]) -> DreamInsight | None:
        """Review recent memories for patterns."""
        memory_texts = [m["content"][:200] for m in memories[:5]]
        combined = "\n".join(f"- {t}" for t in memory_texts)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": "You are a memory review system. Summarize key themes from recent interactions in one concise sentence."
                }, {
                    "role": "user",
                    "content": f"Recent interactions:\n{combined}\n\nSummarize the key themes:"
                }],
                max_tokens=200,
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                return DreamInsight(
                    id=f"di-{len(self._insights)}",
                    phase=DreamPhase.REVIEW,
                    content=content.strip(),
                    source_memories=[m.get("id", "") for m in memories[:5]],
                    confidence=0.7,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            logger.debug(f"Review phase skipped (no LLM): {e}")

        return None

    async def _phase_consolidate(self, memories: list[dict]) -> DreamInsight | None:
        """Consolidate related long-term memories."""
        memory_texts = [m["content"][:150] for m in memories[:8]]
        combined = "\n".join(f"- {t}" for t in memory_texts)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": "You consolidate memories. Identify the most important recurring theme or fact in one sentence."
                }, {
                    "role": "user",
                    "content": f"Memories to consolidate:\n{combined}\n\nKey consolidated insight:"
                }],
                max_tokens=200,
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                return DreamInsight(
                    id=f"di-{len(self._insights)}",
                    phase=DreamPhase.CONSOLIDATE,
                    content=content.strip(),
                    source_memories=[m.get("id", "") for m in memories[:8]],
                    confidence=0.6,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            logger.debug(f"Consolidate phase skipped (no LLM): {e}")

        return None

    async def _phase_synthesize(self, memories: list[dict]) -> DreamInsight | None:
        """Synthesize new connections between disparate memories."""
        memory_texts = [m["content"][:100] for m in memories[:10]]
        combined = "\n".join(f"- {t}" for t in memory_texts)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": "You find creative connections between seemingly unrelated topics. Identify one novel connection in one sentence."
                }, {
                    "role": "user",
                    "content": f"Topics:\n{combined}\n\nNovel connection between these:"
                }],
                max_tokens=200,
                temperature=0.7,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                return DreamInsight(
                    id=f"di-{len(self._insights)}",
                    phase=DreamPhase.SYNTHESIZE,
                    content=content.strip(),
                    source_memories=[m.get("id", "") for m in memories[:10]],
                    confidence=0.4,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            logger.debug(f"Synthesize phase skipped (no LLM): {e}")

        return None

    async def _phase_resolve(self, memories: list[dict]) -> DreamInsight | None:
        """Resolve potential contradictions in memories."""
        memory_texts = [m["content"][:150] for m in memories[:5]]
        combined = "\n".join(f"- {t}" for t in memory_texts)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": "You identify contradictions. If there are conflicting facts, note them. Otherwise state 'no contradictions found'."
                }, {
                    "role": "user",
                    "content": f"Check for contradictions:\n{combined}"
                }],
                max_tokens=200,
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            if content.strip() and "no contradiction" not in content.lower():
                return DreamInsight(
                    id=f"di-{len(self._insights)}",
                    phase=DreamPhase.RESOLVE,
                    content=content.strip(),
                    source_memories=[m.get("id", "") for m in memories[:5]],
                    confidence=0.5,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            logger.debug(f"Resolve phase skipped (no LLM): {e}")

        return None

    async def _phase_reflect(self) -> DreamInsight | None:
        """Self-reflection on agent effectiveness."""
        if len(self._insights) < 5:
            return None

        recent_insights = [i.content for i in self._insights[-5:]]
        combined = "\n".join(f"- {t}" for t in recent_insights)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": "You are a self-reflection system. Summarize what the agent has learned and how it could improve in one sentence."
                }, {
                    "role": "user",
                    "content": f"Recent insights:\n{combined}\n\nSelf-reflection:"
                }],
                max_tokens=200,
                temperature=0.5,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                return DreamInsight(
                    id=f"di-{len(self._insights)}",
                    phase=DreamPhase.REFLECT,
                    content=content.strip(),
                    source_memories=[],
                    confidence=0.5,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            logger.debug(f"Reflect phase skipped (no LLM): {e}")

        return None

    def get_insights(self, limit: int = 20) -> list[dict]:
        """Get recent dream insights."""
        return [
            {
                "id": i.id,
                "phase": i.phase.value,
                "content": i.content,
                "confidence": i.confidence,
                "created_at": i.created_at,
            }
            for i in self._insights[-limit:]
        ]

    def get_stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "is_running": self._is_running,
            "total_insights": len(self._insights),
            "dream_interval": self._dream_interval,
            "phases": {
                phase.value: sum(1 for i in self._insights if i.phase == phase)
                for phase in DreamPhase
            },
        }