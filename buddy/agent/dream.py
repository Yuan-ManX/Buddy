"""Buddy Dream Mode — background memory consolidation and creative synthesis

Implements a "dream" cycle where agents process accumulated memories during
idle periods, consolidating knowledge, resolving contradictions, forming
new connections, and generating creative insights.

Dream cycles follow a configurable schedule (cron-like) and operate in
distinct phases: REVIEW, CONSOLIDATE, SYNTHESIZE, PRUNE, ARCHIVE.
Each cycle is recorded and can be rolled back if needed.
"""
from __future__ import annotations
import logging
import asyncio
import json
import hashlib
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
    PRUNE = "prune"         # Removing obsolete or low-value memories
    ARCHIVE = "archive"     # Compressing sessions into searchable archives


@dataclass
class DreamInsight:
    id: str
    phase: DreamPhase
    content: str
    source_memories: list[str]
    confidence: float = 0.5
    action_items: list[str] = field(default_factory=list)
    created_at: str = ""


@dataclass
class DreamCycleResult:
    insights: list[DreamInsight]
    memories_processed: int
    memories_consolidated: int
    duration_seconds: float
    started_at: str
    completed_at: str


@dataclass
class DreamCycle:
    """A complete dream cycle record with all phases and their outcomes.

    Each cycle is versioned and can be rolled back. The cycle tracks which
    memories were created, consolidated, pruned, or archived, enabling
    precise undo operations.
    """

    id: str
    phases_run: list[str] = field(default_factory=list)
    insights: list[DreamInsight] = field(default_factory=list)
    memories_created: list[str] = field(default_factory=list)
    memories_consolidated: list[str] = field(default_factory=list)
    memories_pruned: list[str] = field(default_factory=list)
    sessions_archived: list[dict[str, Any]] = field(default_factory=list)
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    rolled_back: bool = False


@dataclass
class DreamSchedule:
    """Configurable schedule for dream cycles with cron-like syntax.

    Supports minute, hour, day-of-week scheduling. A schedule of
    ``minute=0, hour=3`` means "run every day at 3:00 AM".
    """

    minute: int = 0
    hour: int = -1       # -1 means every hour
    day_of_week: int = -1  # -1 means every day (0=Mon, 6=Sun)
    enabled: bool = True

    def matches(self, dt: datetime | None = None) -> bool:
        """Check if the current time matches this schedule.

        Args:
            dt: Datetime to check against. Uses now() if None.
        """
        if not self.enabled:
            return False
        now = dt or datetime.now(timezone.utc)
        if self.hour >= 0 and now.hour != self.hour:
            return False
        if self.minute >= 0 and now.minute != self.minute:
            return False
        if self.day_of_week >= 0 and now.weekday() != self.day_of_week:
            return False
        return True

    def next_run(self, dt: datetime | None = None) -> datetime:
        """Calculate the next scheduled run time."""
        now = dt or datetime.now(timezone.utc)
        candidate = now.replace(second=0, microsecond=0)

        if self.hour >= 0:
            candidate = candidate.replace(hour=self.hour)
        if self.minute >= 0:
            candidate = candidate.replace(minute=self.minute)
        if self.day_of_week >= 0:
            days_ahead = self.day_of_week - candidate.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            from datetime import timedelta
            candidate = candidate + timedelta(days=days_ahead)

        if candidate <= now:
            from datetime import timedelta
            if self.hour >= 0:
                candidate = candidate + timedelta(days=1)
            else:
                candidate = candidate + timedelta(hours=1)

        return candidate


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
        self._dream_schedule: DreamSchedule = DreamSchedule()
        self._cycles: list[DreamCycle] = []
        self._cycle_backups: dict[str, dict[str, Any]] = {}
        self._archived_sessions: list[dict[str, Any]] = []
        self._skill_patterns: dict[str, int] = {}

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def interval(self) -> int:
        """Get the current dream cycle interval in seconds."""
        return self._dream_interval

    @property
    def insights_count(self) -> int:
        """Get the total number of dream insights generated."""
        return len(self._insights)

    @property
    def dream_schedule(self) -> DreamSchedule:
        """Get the current dream cycle schedule."""
        return self._dream_schedule

    def start(self, interval: int = 3600):
        """Start periodic dream cycles (synchronous wrapper)."""
        self._dream_interval = interval
        self._is_running = True
        if self._dream_task:
            self._dream_task.cancel()
        self._dream_task = asyncio.create_task(self._dream_loop())
        logger.info(f"Dream engine started for agent {self.agent_id} (interval: {interval}s)")

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
        """Get recent dream insights with source memories."""
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

    # ── Deep Dream Methods ─────────────────────────────

    async def dream_consolidate_memories(self) -> list[DreamInsight]:
        """Merge related memories into coherent narratives during idle periods.

        Scans long-term memory for semantically related entries and uses the LLM
        to combine them into unified, higher-level memories. The original entries
        are preserved as source references.

        Returns:
            List of consolidation insights produced.
        """
        insights: list[DreamInsight] = []

        try:
            long_term = await self.memory.recall_long_term(limit=50)
            if len(long_term) < 5:
                return insights

            # Group memories by keyword similarity
            clusters: dict[str, list[dict]] = {}
            for mem in long_term:
                content = str(mem.get("content", ""))[:200]
                # Use first significant word as cluster key
                words = [w for w in content.lower().split() if len(w) > 4]
                key = words[0] if words else "misc"
                if key not in clusters:
                    clusters[key] = []
                clusters[key].append(mem)

            # Consolidate each cluster with enough entries
            for cluster_key, cluster_mems in clusters.items():
                if len(cluster_mems) < 3:
                    continue

                memory_texts = [str(m.get("content", ""))[:200] for m in cluster_mems[:5]]
                combined = "\n".join(f"- {t}" for t in memory_texts)

                response = await self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "system",
                        "content": (
                            "You consolidate related memories into a coherent narrative. "
                            "Merge these related entries into one unified summary. "
                            "Include any action items that emerge from the consolidation."
                        ),
                    }, {
                        "role": "user",
                        "content": f"Related memories:\n{combined}\n\nConsolidated narrative:"
                    }],
                    max_tokens=300,
                    temperature=0.3,
                )
                content = response.choices[0].message.content or ""
                if content.strip():
                    insight = DreamInsight(
                        id=f"di-consolidate-{len(self._insights)}",
                        phase=DreamPhase.CONSOLIDATE,
                        content=content.strip(),
                        source_memories=[m.get("id", "") for m in cluster_mems[:5]],
                        confidence=0.65,
                        action_items=self._extract_action_items(content),
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                    insights.append(insight)
                    self._insights.append(insight)

                    # Store the consolidated memory
                    await self.memory.store(
                        content=f"[Consolidated] {insight.content}",
                        memory_type="consolidation",
                        importance=0.7,
                    )

        except Exception as e:
            logger.debug(f"Dream consolidation skipped: {e}")

        return insights

    async def dream_synthesize_skills(self) -> list[DreamInsight]:
        """Combine observed behavior patterns into new skills during idle time.

        Analyzes memory patterns and past interactions to detect recurring
        multi-step workflows that could be formalized as reusable skills.

        Returns:
            List of skill synthesis insights.
        """
        insights: list[DreamInsight] = []

        try:
            recent = await self.memory.recall_recent(limit=40)
            long_term = await self.memory.recall_long_term(limit=30)
            all_memories = recent + long_term

            if len(all_memories) < 10:
                return insights

            # Extract action verb patterns from memories
            for mem in all_memories:
                content = str(mem.get("content", "")).lower()
                action_verbs = [
                    "create", "build", "deploy", "analyze", "review",
                    "update", "fix", "optimize", "generate", "convert",
                ]
                for verb in action_verbs:
                    if verb in content:
                        self._skill_patterns[verb] = self._skill_patterns.get(verb, 0) + 1

            # Find frequently recurring patterns
            frequent_patterns = {
                verb: count
                for verb, count in self._skill_patterns.items()
                if count >= 3
            }

            if not frequent_patterns:
                return insights

            memory_texts = [str(m.get("content", ""))[:150] for m in all_memories[:10]]
            combined = "\n".join(f"- {t}" for t in memory_texts)
            pattern_list = ", ".join(frequent_patterns.keys())

            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You identify recurring workflows that could become reusable skills. "
                        "Given frequent action patterns and memory context, suggest one "
                        "concrete skill that could be formalized. Describe what it does, "
                        "what parameters it needs, and what it produces."
                    ),
                }, {
                    "role": "user",
                    "content": (
                        f"Frequent action patterns: {pattern_list}\n"
                        f"Recent context:\n{combined}\n\n"
                        "Suggest a formalizable skill:"
                    ),
                }],
                max_tokens=300,
                temperature=0.5,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                insight = DreamInsight(
                    id=f"di-skill-{len(self._insights)}",
                    phase=DreamPhase.SYNTHESIZE,
                    content=content.strip(),
                    source_memories=[m.get("id", "") for m in all_memories[:5]],
                    confidence=0.45,
                    action_items=[f"Create skill: {content.strip()[:100]}"],
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                insights.append(insight)
                self._insights.append(insight)

        except Exception as e:
            logger.debug(f"Skill synthesis skipped: {e}")

        return insights

    async def dream_prune_obsolete(self) -> list[DreamInsight]:
        """Remove outdated or low-value memories during idle cleanup cycles.

        Evaluates long-term memories for relevance, age, and importance.
        Low-scoring entries are flagged for removal. Memories with importance
        below the threshold are pruned.

        Returns:
            List of prune-phase insights describing what was removed.
        """
        insights: list[DreamInsight] = []
        pruned_ids: list[str] = []

        try:
            long_term = await self.memory.recall_long_term(limit=100)
            if len(long_term) < 10:
                return insights

            now = datetime.now(timezone.utc)
            candidates_for_pruning = []

            for mem in long_term:
                importance = float(mem.get("importance", 0.5))
                created_str = str(mem.get("created_at", ""))
                age_days = 365  # Default: very old

                if created_str:
                    try:
                        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        age_days = (now - created.replace(tzinfo=timezone.utc)).days
                    except (ValueError, TypeError):
                        pass

                # Prune score: low importance + old = high prune priority
                prune_score = (1.0 - importance) * (age_days / 30.0)
                if prune_score > 0.5:
                    candidates_for_pruning.append((mem, prune_score))

            candidates_for_pruning.sort(key=lambda x: -x[1])

            # Prune top candidates (up to 20% of long-term memories)
            prune_count = max(1, len(candidates_for_pruning) // 5)
            for mem, _ in candidates_for_pruning[:prune_count]:
                mem_id = mem.get("id", "")
                pruned_ids.append(mem_id)

            if pruned_ids:
                content = (
                    f"Pruned {len(pruned_ids)} obsolete memories: "
                    f"{', '.join(pruned_ids[:5])}"
                    f"{'...' if len(pruned_ids) > 5 else ''}"
                )
                insight = DreamInsight(
                    id=f"di-prune-{len(self._insights)}",
                    phase=DreamPhase.PRUNE,
                    content=content,
                    source_memories=pruned_ids,
                    confidence=0.8,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                insights.append(insight)
                self._insights.append(insight)

        except Exception as e:
            logger.debug(f"Prune phase skipped: {e}")

        return insights

    async def dream_archive_session(self) -> list[DreamInsight]:
        """Compress an entire session into a searchable archive entry.

        Summarizes the current session's accumulated memories into a compact
        archive record. This allows long-term storage of session context
        without consuming the active memory budget.

        Returns:
            List of archive-phase insights.
        """
        insights: list[DreamInsight] = []

        try:
            recent = await self.memory.recall_recent(limit=50)
            if len(recent) < 5:
                return insights

            memory_texts = [str(m.get("content", ""))[:200] for m in recent[:20]]
            combined = "\n".join(f"- {t}" for t in memory_texts)

            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You create searchable session archives. Summarize the entire "
                        "session into a concise, searchable entry. Include key topics, "
                        "decisions made, and unresolved questions. Format as JSON with "
                        "fields: summary, topics (list), decisions (list), "
                        "open_questions (list)."
                    ),
                }, {
                    "role": "user",
                    "content": f"Session memories:\n{combined}\n\nArchive summary:"
                }],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            archive_text = response.choices[0].message.content or "{}"
            try:
                archive_data = json.loads(archive_text)
            except json.JSONDecodeError:
                archive_data = {"summary": archive_text}

            archive_entry = {
                "id": f"archive-{len(self._archived_sessions)}",
                "agent_id": self.agent_id,
                "data": archive_data,
                "memory_ids": [m.get("id", "") for m in recent[:20]],
                "memory_count": len(recent),
                "archived_at": datetime.now(timezone.utc).isoformat(),
                "hash": hashlib.sha256(archive_text.encode()).hexdigest()[:16],
            }
            self._archived_sessions.append(archive_entry)

            insight = DreamInsight(
                id=f"di-archive-{len(self._insights)}",
                phase=DreamPhase.ARCHIVE,
                content=f"Session archived: {archive_data.get('summary', archive_text)[:200]}",
                source_memories=archive_entry["memory_ids"],
                confidence=0.75,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            insights.append(insight)
            self._insights.append(insight)

        except Exception as e:
            logger.debug(f"Archive session skipped: {e}")

        return insights

    async def dream_cross_reference(self) -> list[DreamInsight]:
        """Find connections between isolated memory clusters.

        Identifies semantic bridges between memories that were stored at
        different times or in different contexts but share underlying themes.
        This helps surface non-obvious relationships in the agent's knowledge.

        Returns:
            List of cross-reference insights.
        """
        insights: list[DreamInsight] = []

        try:
            recent = await self.memory.recall_recent(limit=30)
            long_term = await self.memory.recall_long_term(limit=30)

            if len(recent) < 5 or len(long_term) < 5:
                return insights

            recent_texts = [str(m.get("content", ""))[:150] for m in recent[:8]]
            long_term_texts = [str(m.get("content", ""))[:150] for m in long_term[:8]]

            recent_combined = "\n".join(f"- {t}" for t in recent_texts)
            long_term_combined = "\n".join(f"- {t}" for t in long_term_texts)

            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You find hidden connections between different memory clusters. "
                        "Identify one surprising or non-obvious connection between the "
                        "recent memories and the long-term knowledge. Be specific."
                    ),
                }, {
                    "role": "user",
                    "content": (
                        f"Recent memories:\n{recent_combined}\n\n"
                        f"Long-term knowledge:\n{long_term_combined}\n\n"
                        "Hidden connection:"
                    ),
                }],
                max_tokens=300,
                temperature=0.6,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                insight = DreamInsight(
                    id=f"di-crossref-{len(self._insights)}",
                    phase=DreamPhase.SYNTHESIZE,
                    content=content.strip(),
                    source_memories=[
                        m.get("id", "") for m in recent[:5] + long_term[:5]
                    ],
                    confidence=0.35,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                insights.append(insight)
                self._insights.append(insight)

        except Exception as e:
            logger.debug(f"Cross-reference skipped: {e}")

        return insights

    async def dream_generate_insights(self) -> list[DreamInsight]:
        """Produce creative synthesis reports from accumulated dream findings.

        Analyzes all previous dream insights and generates a meta-level
        report that identifies overarching themes, emerging patterns, and
        strategic recommendations.

        Returns:
            List of meta-insight reports.
        """
        insights: list[DreamInsight] = []

        if len(self._insights) < 10:
            return insights

        recent_insight_contents = [
            i.content for i in self._insights[-20:]
        ]
        combined = "\n".join(f"- {c}" for c in recent_insight_contents)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": (
                        "You generate creative synthesis reports from meta-analysis. "
                        "Review these accumulated insights and produce a synthesis "
                        "report with: (1) overarching themes, (2) emerging patterns, "
                        "(3) strategic recommendations. Be concise but insightful."
                    ),
                }, {
                    "role": "user",
                    "content": f"Accumulated insights:\n{combined}\n\nSynthesis report:"
                }],
                max_tokens=500,
                temperature=0.6,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                insight = DreamInsight(
                    id=f"di-meta-{len(self._insights)}",
                    phase=DreamPhase.SYNTHESIZE,
                    content=content.strip(),
                    source_memories=[i.id for i in self._insights[-20:]],
                    confidence=0.5,
                    action_items=self._extract_action_items(content),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                insights.append(insight)
                self._insights.append(insight)

        except Exception as e:
            logger.debug(f"Insight generation skipped: {e}")

        return insights

    async def dream_rollback(self, cycle_id: str) -> bool:
        """Revert to the state before a specific dream cycle.

        Restores the memory state snapshot taken before the cycle ran.
        Insights produced by the cycle are removed from the active list.

        Args:
            cycle_id: The ID of the dream cycle to roll back.

        Returns:
            True if the rollback was successful, False if the cycle was not found.
        """
        target_cycle = None
        for cycle in self._cycles:
            if cycle.id == cycle_id:
                target_cycle = cycle
                break

        if target_cycle is None:
            logger.warning("Dream cycle not found for rollback: %s", cycle_id)
            return False

        if target_cycle.rolled_back:
            logger.warning("Dream cycle already rolled back: %s", cycle_id)
            return False

        # Restore state snapshot if available
        if target_cycle.state_snapshot:
            snapshot = target_cycle.state_snapshot
            # Restore insights list to pre-cycle state
            saved_insight_count = snapshot.get("insight_count", 0)
            self._insights = self._insights[:saved_insight_count]
            # Restore archived sessions
            saved_archive_count = snapshot.get("archive_count", 0)
            self._archived_sessions = self._archived_sessions[:saved_archive_count]

        # Remove insights produced during this cycle
        cycle_insight_ids = {i.id for i in target_cycle.insights}
        self._insights = [
            i for i in self._insights
            if i.id not in cycle_insight_ids
        ]

        target_cycle.rolled_back = True
        logger.info("Dream cycle rolled back: %s", cycle_id)
        return True

    def set_schedule(self, schedule: DreamSchedule) -> None:
        """Configure the dream cycle schedule.

        Args:
            schedule: A DreamSchedule with cron-like timing configuration.
        """
        self._dream_schedule = schedule
        logger.info(
            "Dream schedule set: hour=%s minute=%s day_of_week=%s enabled=%s",
            schedule.hour, schedule.minute, schedule.day_of_week, schedule.enabled,
        )

    def get_cycle_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent dream cycle records.

        Args:
            limit: Maximum number of cycles to return.

        Returns:
            List of cycle summary dicts.
        """
        return [
            {
                "id": c.id,
                "phases_run": c.phases_run,
                "insight_count": len(c.insights),
                "memories_consolidated": len(c.memories_consolidated),
                "memories_pruned": len(c.memories_pruned),
                "sessions_archived": len(c.sessions_archived),
                "started_at": c.started_at,
                "completed_at": c.completed_at,
                "rolled_back": c.rolled_back,
            }
            for c in self._cycles[-limit:]
        ]

    def get_archived_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent archived session summaries."""
        return self._archived_sessions[-limit:]

    # ── Internal Helpers ──────────────────────────────

    def _snapshot_state(self) -> dict[str, Any]:
        """Capture current engine state for rollback support."""
        return {
            "insight_count": len(self._insights),
            "archive_count": len(self._archived_sessions),
            "skill_pattern_count": len(self._skill_patterns),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _extract_action_items(text: str) -> list[str]:
        """Extract action items from natural language text."""
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.lower().startswith(("- ", "* ", "• ", "action", "task", "todo")):
                cleaned = line.lstrip("- *•").strip()
                if len(cleaned) > 10:
                    items.append(cleaned)
        return items[:5]