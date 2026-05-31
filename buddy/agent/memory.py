"""Relational Memory System for Buddy Agents"""
from sqlalchemy import select, delete, text
from database.db import get_db
from database.models import Memory


class MemoryManager:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def store(self, content: str, memory_type: str = "fact",
                    importance: float = 0.5, conversation_id: str = None) -> Memory:
        async for session in get_db():
            memory = Memory(
                agent_id=self.agent_id,
                conversation_id=conversation_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def recall(self, query: str = None, top_k: int = 5,
                     memory_type: str = None, min_importance: float = 0.0) -> list[Memory]:
        async for session in get_db():
            stmt = select(Memory).where(
                Memory.agent_id == self.agent_id,
                Memory.importance >= min_importance
            )
            if memory_type:
                stmt = stmt.where(Memory.memory_type == memory_type)

            if query:
                stmt = stmt.where(Memory.content.ilike(f"%{query}%"))

            stmt = stmt.order_by(Memory.importance.desc(), Memory.created_at.desc()).limit(top_k)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def recall_context(self, top_k: int = 5) -> list[str]:
        memories = await self.recall(top_k=top_k, min_importance=0.3)
        return [m.content for m in memories]

    async def forget(self, memory_id: str):
        async for session in get_db():
            stmt = delete(Memory).where(Memory.id == memory_id, Memory.agent_id == self.agent_id)
            await session.execute(stmt)
            await session.commit()

    async def consolidate(self, conversation_id: str, summary: str):
        await self.store(
            content=summary,
            memory_type="event",
            importance=0.7,
            conversation_id=conversation_id
        )


AGENT_MEMORIES: dict[str, MemoryManager] = {}


def get_memory(agent_id: str) -> MemoryManager:
    if agent_id not in AGENT_MEMORIES:
        AGENT_MEMORIES[agent_id] = MemoryManager(agent_id)
    return AGENT_MEMORIES[agent_id]