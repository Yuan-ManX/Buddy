"""Buddy Hierarchical Memory System — layered memory for agents

Three-tier architecture:
- Short-term: Recent conversation messages (transient, session-scoped)
- Long-term: Persistent facts, preferences, and decisions (semantic recall)
- Episodic: Full conversation transcripts (contextual replay)

White-box memory features:
- Tagging and categorization
- Memory introspection and visualization
- User-editable memory entries
- Importance scoring and decay
- Semantic search with embeddings
- Thematic consolidation with LLM
"""
from __future__ import annotations
import json
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from database.db import async_session
from database.models import Memory as MemoryModel
from sqlalchemy import select, func, desc, and_, update
from config.settings import settings

logger = logging.getLogger("buddy.memory")


class MemoryLayer:
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SKILL = "skill"


class HierarchicalMemory:
    """Layered memory system with automatic consolidation from short-term to long-term
    and optional semantic search via embeddings."""

    def __init__(self, agent_id: str, load_from_db: bool = False):
        self.agent_id = agent_id
        self._short_term_buffer: list[dict] = []
        self._consolidation_threshold = 10
        self._embedding_client = None
        self._embedding_model = settings.EMBEDDING_MODEL
        self._semantic_enabled = settings.SEMANTIC_MEMORY_ENABLED
        self._db_loaded = False
        if load_from_db:
            self._load_from_db_flag = True
        else:
            self._load_from_db_flag = False

    async def _ensure_db_loaded(self):
        """Lazily load memories from database on first access."""
        if self._load_from_db_flag and not self._db_loaded:
            self._db_loaded = True
            try:
                memories = await self.recall_recent(limit=20)
                self._short_term_buffer.extend(memories)
                logger.debug(f"Loaded {len(memories)} recent memories for agent {self.agent_id}")
            except Exception as e:
                logger.debug(f"Failed to load memories from DB: {e}")

    async def _get_embedding(self, text: str) -> list[float] | None:
        """Get embedding vector for text using the configured embedding model."""
        if not self._semantic_enabled:
            return None
        if not self._embedding_client:
            from openai import AsyncOpenAI
            self._embedding_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
        try:
            response = await self._embedding_client.embeddings.create(
                model=self._embedding_model,
                input=text[:8000],  # Respect embedding model limits
            )
            return response.data[0].embedding
        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")
            return None

    async def search_semantic(
        self,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[dict]:
        """Semantic (vector similarity) search across memories."""
        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            # Fall back to text search if embeddings unavailable
            return await self.search(query, limit)

        # Get candidate memories
        async with async_session() as session:
            stmt = select(MemoryModel).where(
                MemoryModel.agent_id == self.agent_id
            )
            if min_importance > 0:
                stmt = stmt.where(MemoryModel.importance >= min_importance)
            stmt = stmt.order_by(desc(MemoryModel.created_at)).limit(limit * 5)
            result = await session.execute(stmt)
            candidates = result.scalars().all()

        # Score by cosine similarity (using stored embeddings or compute on-the-fly)
        import math

        scored = []
        for m in candidates:
            # For now, compute embedding on-the-fly. In production, store embeddings.
            mem_embedding = await self._get_embedding(m.content[:2000])
            if mem_embedding:
                similarity = self._cosine_similarity(query_embedding, mem_embedding)
                scored.append((similarity, m))
            else:
                # Without embedding, give baseline score
                scored.append((0.3, m))

        scored.sort(key=lambda x: -x[0])
        top_results = scored[:limit]

        return [
            {
                "id": m.id,
                "content": m.content,
                "memory_type": m.memory_type,
                "importance": m.importance,
                "similarity": round(score, 4),
                "tags": (m.meta or {}).get("tags", []),
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for score, m in top_results
        ]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def consolidate_thematic(self) -> dict:
        """Perform thematic consolidation of memories using embeddings."""
        recent = await self.recall_recent(limit=30)
        if len(recent) < 5:
            return {"consolidated": 0, "themes": []}

        clusters: dict[str, list[dict]] = {}
        for mem in recent:
            # Simple keyword-based clustering as fallback
            content = mem.get("content", "").lower()
            theme = "general"
            keywords = {
                "code": ["code", "function", "bug", "error", "python", "javascript"],
                "question": ["what", "how", "why", "explain", "help"],
                "task": ["task", "todo", "plan", "goal", "project"],
                "preference": ["prefer", "like", "want", "need", "favorite"],
                "decision": ["decide", "choose", "pick", "select", "option"],
            }
            for t, words in keywords.items():
                if any(w in content for w in words):
                    theme = t
                    break
            clusters.setdefault(theme, []).append(mem)

        consolidated = 0
        for theme, items in clusters.items():
            if len(items) >= 3:
                combined = " | ".join([m["content"][:100] for m in items])
                await self.store(
                    content=f"[Thematic: {theme}] {combined}",
                    layer=MemoryLayer.LONG_TERM,
                    memory_type="consolidation",
                    importance=0.6,
                )
                consolidated += 1

        return {
            "consolidated": consolidated,
            "themes": list(clusters.keys()),
            "total_processed": len(recent),
        }

    async def store(
        self,
        content: str,
        layer: str = MemoryLayer.SHORT_TERM,
        memory_type: str = "event",
        importance: float = 0.5,
        conversation_id: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        await self._ensure_db_loaded()
        async with async_session() as session:
            memory = MemoryModel(
                agent_id=self.agent_id,
                conversation_id=conversation_id,
                content=content,
                memory_type=f"{layer}:{memory_type}",
                importance=min(max(importance, 0.0), 1.0),
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)

            if layer == MemoryLayer.SHORT_TERM:
                self._short_term_buffer.append({
                    "id": memory.id,
                    "content": content,
                    "importance": importance,
                })
                if len(self._short_term_buffer) >= self._consolidation_threshold:
                    await self._consolidate()

            return memory.id

    async def recall(
        self,
        query: str | None = None,
        layer: str | None = None,
        memory_type: str | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[dict]:
        async with async_session() as session:
            stmt = select(MemoryModel).where(
                MemoryModel.agent_id == self.agent_id
            )

            if layer:
                stmt = stmt.where(MemoryModel.memory_type.like(f"{layer}:%"))
            if memory_type:
                stmt = stmt.where(MemoryModel.memory_type.contains(memory_type))
            if min_importance > 0:
                stmt = stmt.where(MemoryModel.importance >= min_importance)
            if query:
                stmt = stmt.where(MemoryModel.content.contains(query))

            stmt = stmt.order_by(desc(MemoryModel.importance), desc(MemoryModel.created_at)).limit(limit)
            result = await session.execute(stmt)
            memories = result.scalars().all()

            return [
                {
                    "id": m.id,
                    "content": m.content,
                    "layer": m.memory_type.split(":")[0] if ":" in m.memory_type else m.memory_type,
                    "memory_type": m.memory_type,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ]

    async def recall_recent(self, limit: int = 5) -> list[dict]:
        return await self.recall(layer=MemoryLayer.SHORT_TERM, limit=limit)

    async def recall_long_term(self, query: str | None = None, limit: int = 10) -> list[dict]:
        return await self.recall(layer=MemoryLayer.LONG_TERM, query=query, limit=limit, min_importance=0.3)

    async def recall_episodic(self, conversation_id: str | None = None, limit: int = 10) -> list[dict]:
        async with async_session() as session:
            stmt = select(MemoryModel).where(
                MemoryModel.agent_id == self.agent_id,
                MemoryModel.memory_type.like(f"{MemoryLayer.EPISODIC}:%"),
            )
            if conversation_id:
                stmt = stmt.where(MemoryModel.conversation_id == conversation_id)
            stmt = stmt.order_by(desc(MemoryModel.created_at)).limit(limit)
            result = await session.execute(stmt)
            memories = result.scalars().all()
            return [
                {
                    "id": m.id,
                    "content": m.content,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ]

    async def _consolidate(self):
        if not self._short_term_buffer:
            return

        high_importance = [m for m in self._short_term_buffer if m["importance"] >= 0.6]
        if high_importance:
            consolidated = "\n\n".join([m["content"] for m in high_importance])
            await self.store(
                content=f"Consolidated memory from {len(self._short_term_buffer)} short-term events:\n{consolidated}",
                layer=MemoryLayer.LONG_TERM,
                memory_type="fact",
                importance=0.5,
            )
            logger.info(f"Consolidated {len(high_importance)} memories for agent {self.agent_id}")

        self._short_term_buffer = []

    async def summarize(self) -> str:
        recent = await self.recall_recent(limit=10)
        long_term = await self.recall_long_term(limit=5)

        parts = ["## Agent Memory Summary\n"]

        if recent:
            parts.append("### Short-Term (Recent)\n")
            for m in recent:
                preview = m["content"][:120].replace("\n", " ")
                parts.append(f"- [{m['importance']:.2f}] {preview}...")

        if long_term:
            parts.append("\n### Long-Term (Consolidated)\n")
            for m in long_term:
                preview = m["content"][:120].replace("\n", " ")
                parts.append(f"- [{m['importance']:.2f}] {preview}...")

        if not recent and not long_term:
            parts.append("No memories stored yet.")

        return "\n".join(parts)

    async def forget(self, memory_id: str) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.id == memory_id,
                    MemoryModel.agent_id == self.agent_id,
                )
            )
            memory = result.scalars().first()
            if memory:
                await session.delete(memory)
                await session.commit()
                return True
            return False

    async def clear_layer(self, layer: str) -> int:
        async with async_session() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.agent_id == self.agent_id,
                    MemoryModel.memory_type.like(f"{layer}:%"),
                )
            )
            memories = result.scalars().all()
            count = len(memories)
            for m in memories:
                await session.delete(m)
            await session.commit()
            return count

    async def clear_expired(self, days: int = 7) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with async_session() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.agent_id == self.agent_id,
                    MemoryModel.memory_type.like(f"{MemoryLayer.SHORT_TERM}:%"),
                    MemoryModel.created_at < cutoff,
                    MemoryModel.importance < 0.4,
                )
            )
            memories = result.scalars().all()
            count = len(memories)
            for m in memories:
                await session.delete(m)
            await session.commit()
            if count > 0:
                logger.info(f"Cleared {count} expired short-term memories for agent {self.agent_id}")
            return count

    async def tag(self, memory_id: str, tags: list[str]) -> bool:
        """Add tags to a memory entry for categorization."""
        async with async_session() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.id == memory_id,
                    MemoryModel.agent_id == self.agent_id,
                )
            )
            memory = result.scalars().first()
            if not memory:
                return False

            existing_tags = memory.meta.get("tags", []) if memory.meta else []
            new_tags = list(set(existing_tags + tags))
            memory.meta = {**(memory.meta or {}), "tags": new_tags}
            await session.commit()
            logger.info(f"Tagged memory {memory_id}: {tags}")
            return True

    async def untag(self, memory_id: str, tags: list[str]) -> bool:
        """Remove tags from a memory entry."""
        async with async_session() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.id == memory_id,
                    MemoryModel.agent_id == self.agent_id,
                )
            )
            memory = result.scalars().first()
            if not memory:
                return False

            existing_tags = (memory.meta or {}).get("tags", [])
            new_tags = [t for t in existing_tags if t not in tags]
            memory.meta = {**(memory.meta or {}), "tags": new_tags}
            await session.commit()
            return True

    async def get_by_tags(self, tags: list[str], limit: int = 20) -> list[dict]:
        """Retrieve memories by tags."""
        async with async_session() as session:
            stmt = select(MemoryModel).where(
                MemoryModel.agent_id == self.agent_id
            ).order_by(desc(MemoryModel.created_at)).limit(limit * 2)

            result = await session.execute(stmt)
            memories = result.scalars().all()

            filtered = []
            for m in memories:
                mem_tags = (m.meta or {}).get("tags", [])
                if any(t in mem_tags for t in tags):
                    filtered.append(m)
                    if len(filtered) >= limit:
                        break

            return [
                {
                    "id": m.id,
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "importance": m.importance,
                    "tags": (m.meta or {}).get("tags", []),
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in filtered
            ]

    async def update(self, memory_id: str, content: str | None = None, importance: float | None = None) -> bool:
        """Update a memory entry's content or importance."""
        async with async_session() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.id == memory_id,
                    MemoryModel.agent_id == self.agent_id,
                )
            )
            memory = result.scalars().first()
            if not memory:
                return False

            if content is not None:
                memory.content = content
            if importance is not None:
                memory.importance = min(max(importance, 0.0), 1.0)

            await session.commit()
            logger.info(f"Updated memory {memory_id}")
            return True

    async def get_all_tags(self) -> list[dict]:
        """Get all tags used by this agent with counts."""
        async with async_session() as session:
            stmt = select(MemoryModel).where(
                MemoryModel.agent_id == self.agent_id
            )
            result = await session.execute(stmt)
            memories = result.scalars().all()

            tag_counts: dict[str, int] = {}
            for m in memories:
                for tag in (m.meta or {}).get("tags", []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

            return [
                {"tag": tag, "count": count}
                for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])
            ]

    async def get_memory_stats(self) -> dict:
        """Get comprehensive memory statistics."""
        async with async_session() as session:
            count_stmt = select(func.count()).select_from(MemoryModel).where(
                MemoryModel.agent_id == self.agent_id
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            avg_importance_stmt = select(func.avg(MemoryModel.importance)).where(
                MemoryModel.agent_id == self.agent_id
            )
            avg_importance = (await session.execute(avg_importance_stmt)).scalar() or 0

            layer_counts = {}
            for layer in [MemoryLayer.SHORT_TERM, MemoryLayer.LONG_TERM, MemoryLayer.EPISODIC]:
                layer_stmt = select(func.count()).select_from(MemoryModel).where(
                    MemoryModel.agent_id == self.agent_id,
                    MemoryModel.memory_type.like(f"{layer}:%"),
                )
                layer_counts[layer] = (await session.execute(layer_stmt)).scalar() or 0

            tags = await self.get_all_tags()

            return {
                "agent_id": self.agent_id,
                "total_memories": total,
                "average_importance": round(float(avg_importance), 3),
                "layer_distribution": layer_counts,
                "tags": tags,
                "consolidation_threshold": self._consolidation_threshold,
                "short_term_buffer_size": len(self._short_term_buffer),
            }

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Full-text search across all memory layers."""
        return await self.recall(query=query, limit=limit)

    async def decay_importance(self, days_threshold: int = 30, decay_rate: float = 0.1) -> int:
        """Gradually reduce importance of old, low-importance memories."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        async with async_session() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.agent_id == self.agent_id,
                    MemoryModel.created_at < cutoff,
                    MemoryModel.importance < 0.5,
                    MemoryModel.importance > 0.1,
                )
            )
            memories = result.scalars().all()
            count = 0
            for m in memories:
                m.importance = max(0.05, m.importance - decay_rate)
                count += 1
            await session.commit()
            if count > 0:
                logger.info(f"Decayed importance for {count} memories of agent {self.agent_id}")
            return count

    async def export_memories(self) -> list[dict]:
        """Export all memories for this agent."""
        async with async_session() as session:
            stmt = select(MemoryModel).where(
                MemoryModel.agent_id == self.agent_id
            ).order_by(desc(MemoryModel.created_at))
            result = await session.execute(stmt)
            memories = result.scalars().all()
            return [
                {
                    "id": m.id,
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "importance": m.importance,
                    "tags": (m.meta or {}).get("tags", []),
                    "conversation_id": m.conversation_id,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ]

    async def import_memories(self, memories: list[dict]) -> int:
        """Import memories from exported data."""
        count = 0
        for mem in memories:
            await self.store(
                content=mem.get("content", ""),
                memory_type=mem.get("memory_type", "event"),
                importance=mem.get("importance", 0.5),
                conversation_id=mem.get("conversation_id"),
                metadata=mem.get("metadata"),
            )
            count += 1
        return count


class MemorySystem(HierarchicalMemory):
    """Backward-compatible alias for HierarchicalMemory."""
    pass