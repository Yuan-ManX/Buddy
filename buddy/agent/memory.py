"""Buddy Memory System — Relational memory for agents"""
import json
import logging
from datetime import datetime
from database.db import async_session
from database.models import Memory as MemoryModel
from sqlalchemy import select, func, desc

logger = logging.getLogger("buddy.memory")


class MemorySystem:
    """Relational memory system for storing and retrieving agent memories."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def store(
        self,
        content: str,
        memory_type: str = "event",
        importance: float = 0.5,
        conversation_id: str | None = None,
    ) -> str:
        async with async_session() as session:
            memory = MemoryModel(
                agent_id=self.agent_id,
                conversation_id=conversation_id,
                content=content,
                memory_type=memory_type,
                importance=min(max(importance, 0.0), 1.0),
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory.id

    async def recall(
        self,
        query: str | None = None,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        async with async_session() as session:
            stmt = select(MemoryModel).where(
                MemoryModel.agent_id == self.agent_id
            )

            if memory_type:
                stmt = stmt.where(MemoryModel.memory_type == memory_type)

            if query:
                stmt = stmt.where(MemoryModel.content.contains(query))

            stmt = stmt.order_by(desc(MemoryModel.importance), desc(MemoryModel.created_at)).limit(limit)
            result = await session.execute(stmt)
            memories = result.scalars().all()

            return [
                {
                    "id": m.id,
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ]

    async def summarize(self) -> str:
        memories = await self.recall(limit=20)
        if not memories:
            return "No memories stored yet."

        summary_parts = ["## Agent Memory Summary\n"]
        for m in memories:
            dt = m.get("created_at", "unknown")
            content_preview = m["content"][:120]
            summary_parts.append(
                f"- [{m['memory_type']}] ({m['importance']:.2f}) {content_preview}..."
            )
        return "\n".join(summary_parts)

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

    async def clear(self) -> int:
        async with async_session() as session:
            result = await session.execute(
                select(MemoryModel).where(MemoryModel.agent_id == self.agent_id)
            )
            memories = result.scalars().all()
            count = len(memories)
            for m in memories:
                await session.delete(m)
            await session.commit()
            return count