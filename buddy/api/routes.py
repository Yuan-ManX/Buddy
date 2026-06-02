"""Buddy API Routes — REST endpoints for agent and conversation management"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.db import async_session
from database.models import Agent as AgentModel, Conversation as ConvModel, Message as MsgModel, Memory as MemModel
from sqlalchemy import select, desc, delete
from agent.orchestrator import Orchestrator
from agent.skills import SkillsRegistry

logger = logging.getLogger("buddy.api")
router = APIRouter(prefix="/api")

orchestrator = Orchestrator()
skills_registry = SkillsRegistry()


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    role: str = Field(default="custom", max_length=32)
    personality: str = Field(default="friendly and helpful", max_length=256)
    instructions: str = Field(default="", max_length=4096)


class ChatRequest(BaseModel):
    agent_id: str
    content: str = Field(..., min_length=1)
    conversation_id: str | None = None


class ConvCreate(BaseModel):
    title: str = Field(..., min_length=1)
    agent_ids: list[str] = Field(default_factory=list)


class SkillExecute(BaseModel):
    skill_name: str
    agent_id: str
    parameters: dict = Field(default_factory=dict)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Buddy Platform", "active_agents": orchestrator.active_agents}


@router.get("/agents")
async def list_agents():
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.is_active == True).order_by(desc(AgentModel.created_at))
        )
        return [
            {
                "id": a.id, "name": a.name, "role": a.role,
                "personality": a.personality, "instructions": a.instructions,
                "avatar": a.avatar or a.name[0].upper(), "is_active": a.is_active,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in result.scalars().all()
        ]


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
        a = result.scalars().first()
        if not a:
            raise HTTPException(404, "Agent not found")
        return {
            "id": a.id, "name": a.name, "role": a.role,
            "personality": a.personality, "instructions": a.instructions,
            "avatar": a.avatar or a.name[0].upper(), "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }


@router.post("/agents", status_code=201)
async def create_agent(data: AgentCreate):
    agent_id = f"agent-{uuid.uuid4().hex[:8]}"
    async with async_session() as session:
        agent = AgentModel(
            id=agent_id, name=data.name, role=data.role,
            personality=data.personality, instructions=data.instructions,
            avatar=data.name[0].upper(), is_active=True,
        )
        session.add(agent)
        await session.commit()
        return {
            "id": agent.id, "name": agent.name, "role": agent.role,
            "personality": agent.personality, "instructions": agent.instructions,
            "avatar": agent.avatar, "is_active": agent.is_active,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
        }


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str):
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(404, "Agent not found")
        await session.delete(agent)
        await session.commit()
        orchestrator.evict_engine(agent_id)


@router.get("/conversations")
async def list_conversations():
    async with async_session() as session:
        result = await session.execute(
            select(ConvModel).order_by(desc(ConvModel.updated_at))
        )
        return [
            {
                "id": c.id, "title": c.title, "agent_ids": c.agent_ids or [],
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in result.scalars().all()
        ]


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    async with async_session() as session:
        result = await session.execute(select(ConvModel).where(ConvModel.id == conv_id))
        c = result.scalars().first()
        if not c:
            raise HTTPException(404, "Conversation not found")
        return {
            "id": c.id, "title": c.title, "agent_ids": c.agent_ids or [],
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }


@router.post("/conversations", status_code=201)
async def create_conversation(data: ConvCreate):
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    async with async_session() as session:
        conv = ConvModel(id=conv_id, title=data.title, agent_ids=data.agent_ids)
        session.add(conv)
        await session.commit()
        return {
            "id": conv.id, "title": conv.title, "agent_ids": conv.agent_ids or [],
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        }


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(MsgModel).where(MsgModel.conversation_id == conv_id).order_by(MsgModel.created_at)
        )
        return [
            {
                "id": m.id, "agent_id": m.agent_id, "conversation_id": m.conversation_id,
                "role": m.role, "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in result.scalars().all()
        ]


@router.post("/chat")
async def chat(data: ChatRequest):
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == data.agent_id))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(404, "Agent not found")

        conv_id = data.conversation_id
        if not conv_id:
            conv_id = f"conv-{uuid.uuid4().hex[:8]}"
            conv = ConvModel(id=conv_id, title=f"Chat with {agent.name}", agent_ids=[agent.id])
            session.add(conv)
            await session.commit()
        elif data.conversation_id:
            session.expire_all()

    history_result = None
    if conv_id:
        async with async_session() as s2:
            msgs = await s2.execute(
                select(MsgModel).where(MsgModel.conversation_id == conv_id).order_by(MsgModel.created_at).limit(20)
            )
            history_result = [
                {"role": m.role, "content": m.content}
                for m in msgs.scalars().all()
            ]

    response = await orchestrator.chat(
        agent_id=agent.id,
        agent_name=agent.name,
        instructions=agent.instructions or f"You are {agent.name}, a {agent.role} agent.",
        message=data.content,
        history=history_result,
    )

    async with async_session() as s3:
        user_msg = MsgModel(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            agent_id=agent.id, conversation_id=conv_id,
            role="user", content=data.content,
        )
        assistant_msg = MsgModel(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            agent_id=agent.id, conversation_id=conv_id,
            role="assistant", content=response,
        )
        s3.add_all([user_msg, assistant_msg])
        conv = await s3.execute(select(ConvModel).where(ConvModel.id == conv_id))
        c = conv.scalars().first()
        if c:
            c.updated_at = datetime.now(timezone.utc)
        await s3.commit()

    return {
        "agent_id": agent.id,
        "content": response,
        "conversation_id": conv_id,
        "tool_calls": [],
    }


@router.get("/agents/{agent_id}/memories")
async def get_agent_memories(agent_id: str, query: str | None = None, limit: int = 20):
    async with async_session() as session:
        stmt = select(MemModel).where(MemModel.agent_id == agent_id)
        if query:
            stmt = stmt.where(MemModel.content.contains(query))
        stmt = stmt.order_by(desc(MemModel.created_at)).limit(limit)
        result = await session.execute(stmt)
        return [
            {
                "id": m.id, "agent_id": m.agent_id,
                "content": m.content, "memory_type": m.memory_type,
                "importance": m.importance,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in result.scalars().all()
        ]


@router.get("/skills")
async def list_skills():
    return skills_registry.list()


@router.post("/skills/execute")
async def execute_skill(data: SkillExecute):
    result = await skills_registry.execute(data.skill_name, data.parameters)
    return {"result": result}