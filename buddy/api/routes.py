"""REST API Routes for Buddy"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db
from database.models import Agent, Message, Conversation, Memory
from models.schemas import (
    AgentCreate, AgentResponse, MessageCreate, MessageResponse,
    ConversationCreate, ConversationResponse, ChatRequest,
    SkillExecute,
)
from agent.orchestrator import get_or_create_agent, remove_agent
from agent.memory import get_memory
from agent.skills import registry

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Buddy"}


# ─── Agents ───

@router.post("/agents", response_model=AgentResponse, status_code=201)
async def create_agent(body: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(name=body.name, role=body.role, personality=body.personality,
                  instructions=body.instructions, avatar=body.avatar)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    get_or_create_agent(agent.id, agent.name, agent.personality, agent.instructions)
    return agent


@router.get("/agents", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.is_active == True).order_by(Agent.created_at.desc()))
    return list(result.scalars().all())


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_active = False
    await db.commit()
    remove_agent(agent_id)


# ─── Conversations ───

@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(body: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conv = Conversation(title=body.title, agent_ids=body.agent_ids)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    return list(result.scalars().all())


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


# ─── Messages ───

@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
async def list_messages(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/messages", response_model=MessageResponse, status_code=201)
async def create_message(body: MessageCreate, db: AsyncSession = Depends(get_db)):
    msg = Message(agent_id=body.agent_id, conversation_id=None, role=body.role, content=body.content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


# ─── Chat ───

@router.post("/chat")
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == body.agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    conv_id = body.conversation_id
    if not conv_id:
        conv = Conversation(title=f"Chat with {agent.name}", agent_ids=[agent.id])
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        conv_id = conv.id

    buddy = get_or_create_agent(agent.id, agent.name, agent.personality, agent.instructions)
    memory_manager = get_memory(agent.id)
    memory_context = await memory_manager.recall_context()

    response = await buddy.chat(body.content, memory_context)

    user_msg = Message(agent_id=agent.id, conversation_id=conv_id, role="user", content=body.content)
    assistant_msg = Message(agent_id=agent.id, conversation_id=conv_id, role="assistant", content=response["content"])
    db.add_all([user_msg, assistant_msg])
    await db.commit()

    return {
        "agent_id": agent.id,
        "content": response["content"],
        "conversation_id": conv_id,
        "tool_calls": response.get("tool_calls", [])
    }


# ─── Memories ───

@router.get("/agents/{agent_id}/memories")
async def list_memories(agent_id: str, query: str = None, top_k: int = 20):
    memory_manager = get_memory(agent_id)
    memories = await memory_manager.recall(query=query, top_k=top_k)
    return [{"id": m.id, "content": m.content, "memory_type": m.memory_type, "importance": m.importance,
             "created_at": m.created_at.isoformat()} for m in memories]


# ─── Skills ───

@router.get("/skills")
async def list_skills():
    return registry.list_all()


@router.post("/skills/execute")
async def execute_skill(body: SkillExecute):
    result = await registry.execute(body.skill_name, **body.parameters)
    return {"result": result}