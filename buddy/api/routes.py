"""Buddy API Routes — REST endpoints for agent, task, conversation, skill management

Complete API with agents, conversations, chat (streaming), tasks, skills,
memories, tools, routing, autopilot, workspace, sub-agents, plans, MCP, and system.
"""
from __future__ import annotations
import logging
import uuid
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, WebSocket
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from database.db import async_session
from database.models import (
    Agent as AgentModel,
    Conversation as ConvModel,
    Message as MsgModel,
    Memory as MemModel,
    Task as TaskModel,
)
from sqlalchemy import select, desc, delete, func
from agent.shared import (
    orchestrator, skills_registry, model_router, autopilot_engine,
    tool_registry, planning_engine, mcp_registry,
    approval_engine, event_bus, EventType, Event,
)
from agent.task import task_lifecycle, TaskStatus, TaskKind
from agent.autopilot import AutopilotTrigger, AutopilotStatus
from agent.workspace import AgentWorkspace
from agent.subagent import SubAgentOrchestrator, SubAgentStatus
from agent.mcp import MCPServerConfig, MCPTransport
from agent.tools import ToolCategory, ToolParameter, ToolDefinition

logger = logging.getLogger("buddy.api")
router = APIRouter(prefix="/api")


# ── Request Models ─────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    role: str = Field(default="custom", max_length=32)
    personality: str = Field(default="friendly and helpful", max_length=256)
    instructions: str = Field(default="", max_length=4096)


class ChatRequest(BaseModel):
    agent_id: str
    content: str = Field(..., min_length=1)
    conversation_id: str | None = None
    enable_tools: bool = Field(default=True)
    enable_reasoning: bool = Field(default=False)


class PlanChatRequest(BaseModel):
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


class SkillPipelineExecute(BaseModel):
    steps: list[dict] = Field(..., min_length=1)
    agent_id: str


class TaskCreate(BaseModel):
    agent_id: str
    title: str = Field(..., min_length=1, max_length=256)
    kind: str = Field(default="direct")
    payload: dict = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=10)


class TaskTransition(BaseModel):
    status: str
    result: dict | None = None
    error: str | None = None


class AutopilotCreate(BaseModel):
    agent_id: str
    name: str = Field(..., min_length=1, max_length=128)
    task_template: str = Field(..., min_length=1)
    trigger: str = Field(default="interval")
    schedule: str = Field(default="3600")
    max_runs: int = Field(default=0, ge=0)
    description: str = Field(default="", max_length=512)


class WorkspaceFileCreate(BaseModel):
    name: str = Field(..., min_length=1)
    content: str = Field(default="")
    subdir: str = Field(default="")


class WorkspaceFileUpdate(BaseModel):
    content: str = Field(..., min_length=0)


class CodeExecute(BaseModel):
    code: str = Field(..., min_length=1)
    timeout: int = Field(default=30, ge=1, le=120)


class ShellExecute(BaseModel):
    command: str = Field(..., min_length=1)
    timeout: int = Field(default=30, ge=1, le=120)


class SubAgentTask(BaseModel):
    name: str = Field(default="Worker")
    instructions: str = Field(default="Complete the assigned task efficiently.")
    task: str = Field(..., min_length=1)


class SubAgentBatch(BaseModel):
    agent_id: str
    tasks: list[SubAgentTask]
    model: str = Field(default="gpt-4o-mini")


class MemoryTagRequest(BaseModel):
    tags: list[str] = Field(..., min_length=1)


class MemoryUpdateRequest(BaseModel):
    content: str | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)


class ToolExecuteRequest(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)


class ToolRegisterRequest(BaseModel):
    name: str
    description: str = ""
    category: str = "system"
    parameter_definitions: dict = Field(default_factory=dict)


class PlanGenerateRequest(BaseModel):
    agent_id: str
    goal: str = Field(..., min_length=1)


class PlanExecuteRequest(BaseModel):
    plan_id: str
    agent_id: str


class MCPServerRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    transport: str = Field(default="http")
    endpoint: str = Field(default="")
    command: str = Field(default="")
    env: dict[str, str] = Field(default_factory=dict)


class CollaborationRequest(BaseModel):
    query: str = Field(..., min_length=1)
    agent_ids: list[str] = Field(..., min_length=2)
    max_rounds: int = Field(default=3, ge=1, le=10)


class TransferRequest(BaseModel):
    from_agent_id: str
    to_agent_id: str
    context: str = Field(..., min_length=1)


class VerifyRequest(BaseModel):
    verification_agent_id: str
    original_response: str = Field(..., min_length=1)
    original_query: str = Field(..., min_length=1)


class PaginationParams:
    def __init__(self, page: int = 1, page_size: int = 20):
        self.page = max(page, 1)
        self.page_size = min(max(page_size, 1), 100)
        self.offset = (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    def response(self, total: int, items: list) -> dict:
        return {
            "items": items,
            "total": total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": max((total + self.page_size - 1) // self.page_size, 1),
        }


# ═══════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Buddy Platform",
        "active_agents": orchestrator.active_agents,
    }


# ═══════════════════════════════════════════════════════════
# Agents
# ═══════════════════════════════════════════════════════════

@router.get("/agents")
async def list_agents(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    pagination = PaginationParams(page, page_size)
    async with async_session() as session:
        count_stmt = select(func.count()).select_from(AgentModel).where(AgentModel.is_active == True)
        total = (await session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AgentModel)
            .where(AgentModel.is_active == True)
            .order_by(desc(AgentModel.created_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await session.execute(stmt)
        items = [
            {
                "id": a.id, "name": a.name, "role": a.role,
                "personality": a.personality, "instructions": a.instructions,
                "avatar": a.avatar or a.name[0].upper(), "is_active": a.is_active,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in result.scalars().all()
        ]
        return pagination.response(total, items)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    personality: str | None = Field(default=None, max_length=256)
    instructions: str | None = Field(default=None, max_length=4096)


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


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, data: AgentUpdate):
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(404, "Agent not found")

        if data.name is not None:
            agent.name = data.name
        if data.personality is not None:
            agent.personality = data.personality
        if data.instructions is not None:
            agent.instructions = data.instructions

        await session.commit()
        return {
            "id": agent.id, "name": agent.name, "role": agent.role,
            "personality": agent.personality, "instructions": agent.instructions,
            "avatar": agent.avatar, "is_active": agent.is_active,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
        }


@router.get("/agents/{agent_id}/engine-stats")
async def get_agent_engine_stats(agent_id: str):
    """Get comprehensive engine statistics for an agent."""
    engine = orchestrator.get_engine(agent_id, "", "")
    return engine.get_engine_stats()


# ═══════════════════════════════════════════════════════════
# Conversations
# ═══════════════════════════════════════════════════════════

@router.get("/conversations")
async def list_conversations(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    pagination = PaginationParams(page, page_size)
    async with async_session() as session:
        count_stmt = select(func.count()).select_from(ConvModel)
        total = (await session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(ConvModel)
            .order_by(desc(ConvModel.updated_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await session.execute(stmt)
        items = [
            {
                "id": c.id, "title": c.title, "agent_ids": c.agent_ids or [],
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in result.scalars().all()
        ]
        return pagination.response(total, items)


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


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(conv_id: str):
    async with async_session() as session:
        result = await session.execute(select(ConvModel).where(ConvModel.id == conv_id))
        conv = result.scalars().first()
        if not conv:
            raise HTTPException(404, "Conversation not found")
        await session.delete(conv)
        await session.commit()


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    pagination = PaginationParams(page, page_size)
    async with async_session() as session:
        count_stmt = select(func.count()).select_from(MsgModel).where(MsgModel.conversation_id == conv_id)
        total = (await session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(MsgModel)
            .where(MsgModel.conversation_id == conv_id)
            .order_by(MsgModel.created_at)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await session.execute(stmt)
        items = [
            {
                "id": m.id, "agent_id": m.agent_id, "conversation_id": m.conversation_id,
                "role": m.role, "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in result.scalars().all()
        ]
        return pagination.response(total, items)


# ═══════════════════════════════════════════════════════════
# Chat
# ═══════════════════════════════════════════════════════════

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

    history_result = None
    if conv_id:
        async with async_session() as s2:
            msgs = await s2.execute(
                select(MsgModel)
                .where(MsgModel.conversation_id == conv_id)
                .order_by(MsgModel.created_at)
                .limit(30)
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
        enable_tools=data.enable_tools,
        enable_reasoning=data.enable_reasoning,
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


@router.post("/chat/stream")
async def chat_stream(data: ChatRequest):
    """Stream chat response as Server-Sent Events."""
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

    history_result = None
    if conv_id:
        async with async_session() as s2:
            msgs = await s2.execute(
                select(MsgModel)
                .where(MsgModel.conversation_id == conv_id)
                .order_by(MsgModel.created_at)
                .limit(30)
            )
            history_result = [
                {"role": m.role, "content": m.content}
                for m in msgs.scalars().all()
            ]

    async def event_stream():
        full_response = ""
        try:
            async for token in orchestrator.chat_stream(
                agent_id=agent.id,
                agent_name=agent.name,
                instructions=agent.instructions or f"You are {agent.name}, a {agent.role} agent.",
                message=data.content,
                history=history_result,
                enable_tools=data.enable_tools,
                enable_reasoning=data.enable_reasoning,
            ):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # Save messages
            async with async_session() as s3:
                user_msg = MsgModel(
                    id=f"msg-{uuid.uuid4().hex[:8]}",
                    agent_id=agent.id, conversation_id=conv_id,
                    role="user", content=data.content,
                )
                assistant_msg = MsgModel(
                    id=f"msg-{uuid.uuid4().hex[:8]}",
                    agent_id=agent.id, conversation_id=conv_id,
                    role="assistant", content=full_response,
                )
                s3.add_all([user_msg, assistant_msg])
                conv = await s3.execute(select(ConvModel).where(ConvModel.id == conv_id))
                c = conv.scalars().first()
                if c:
                    c.updated_at = datetime.now(timezone.utc)
                await s3.commit()

            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/plan")
async def chat_with_plan(data: PlanChatRequest):
    """Chat with automatic plan generation and execution."""
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == data.agent_id))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(404, "Agent not found")

    response = await orchestrator.chat_with_plan(
        agent_id=agent.id,
        agent_name=agent.name,
        instructions=agent.instructions or f"You are {agent.name}, a {agent.role} agent.",
        message=data.content,
        stream=False,
    )

    return {
        "agent_id": agent.id,
        "content": response if isinstance(response, str) else "Plan execution completed.",
        "conversation_id": data.conversation_id,
    }


# ═══════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════

@router.get("/tasks")
async def list_tasks(
    agent_id: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    pagination = PaginationParams(page, page_size)
    async with async_session() as session:
        stmt = select(func.count()).select_from(TaskModel)
        if agent_id:
            stmt = stmt.where(TaskModel.agent_id == agent_id)
        if status:
            stmt = stmt.where(TaskModel.status == status)
        if kind:
            stmt = stmt.where(TaskModel.kind == kind)
        total = (await session.execute(stmt)).scalar() or 0

        stmt = select(TaskModel)
        if agent_id:
            stmt = stmt.where(TaskModel.agent_id == agent_id)
        if status:
            stmt = stmt.where(TaskModel.status == status)
        if kind:
            stmt = stmt.where(TaskModel.kind == kind)
        stmt = stmt.order_by(desc(TaskModel.created_at)).offset(pagination.offset).limit(pagination.limit)
        result = await session.execute(stmt)

        items = []
        for t in result.scalars().all():
            items.append({
                "id": t.id, "agent_id": t.agent_id, "title": t.title,
                "status": t.status, "kind": t.kind, "payload": t.payload,
                "result": t.result, "error": t.error,
                "conversation_id": t.conversation_id,
                "attempt": t.attempt, "max_attempts": t.max_attempts,
                "parent_task_id": t.parent_task_id,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            })
        return pagination.response(total, items)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = await task_lifecycle.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return {
        "id": task.id, "agent_id": task.agent_id, "title": task.title,
        "status": task.status, "kind": task.kind, "payload": task.payload,
        "result": task.result, "error": task.error,
        "conversation_id": task.conversation_id,
        "attempt": task.attempt, "max_attempts": task.max_attempts,
        "parent_task_id": task.parent_task_id,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.post("/tasks", status_code=201)
async def create_task(data: TaskCreate):
    try:
        kind = TaskKind(data.kind)
    except ValueError:
        raise HTTPException(400, f"Invalid task kind: {data.kind}. Valid: {[k.value for k in TaskKind]}")

    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == data.agent_id))
        if not result.scalars().first():
            raise HTTPException(404, "Agent not found")

    task = await task_lifecycle.enqueue(
        agent_id=data.agent_id,
        title=data.title,
        kind=kind,
        payload=data.payload,
        max_attempts=data.max_attempts,
    )
    return {
        "id": task.id, "agent_id": task.agent_id, "title": task.title,
        "status": task.status, "kind": task.kind, "payload": task.payload,
        "attempt": task.attempt, "max_attempts": task.max_attempts,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.post("/tasks/{task_id}/transition")
async def transition_task(task_id: str, data: TaskTransition):
    try:
        status = TaskStatus(data.status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {data.status}")

    task = await task_lifecycle.transition(task_id, status, data.result, data.error)
    if not task:
        raise HTTPException(404, "Task not found or invalid transition")
    return {
        "id": task.id, "agent_id": task.agent_id, "title": task.title,
        "status": task.status, "kind": task.kind,
        "result": task.result, "error": task.error,
        "attempt": task.attempt,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    task = await task_lifecycle.cancel(task_id)
    if not task:
        raise HTTPException(404, "Task not found or cannot be cancelled")
    return {"id": task.id, "status": task.status}


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str):
    task = await task_lifecycle.retry(task_id)
    if not task:
        raise HTTPException(400, "Task cannot be retried")
    return {"id": task.id, "status": task.status, "attempt": task.attempt}


@router.post("/agents/{agent_id}/claim")
async def claim_task(agent_id: str):
    task = await task_lifecycle.claim(agent_id)
    if not task:
        raise HTTPException(404, "No queued tasks available for this agent")
    return {
        "id": task.id, "agent_id": task.agent_id, "title": task.title,
        "status": task.status, "kind": task.kind, "payload": task.payload,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


# ═══════════════════════════════════════════════════════════
# Skills
# ═══════════════════════════════════════════════════════════

@router.get("/skills")
async def list_skills(category: str | None = None):
    return skills_registry.list(category=category)


@router.get("/skills/categories")
async def list_skill_categories():
    return skills_registry.categories()


@router.post("/skills/execute")
async def execute_skill(data: SkillExecute):
    result = await skills_registry.execute(data.skill_name, data.parameters)
    return {"result": result}


@router.post("/skills/pipeline")
async def execute_skill_pipeline(data: SkillPipelineExecute):
    if not data.steps:
        raise HTTPException(400, "Pipeline must contain at least one step")
    steps = [(s["name"], s.get("params", {})) for s in data.steps]
    result = await skills_registry.execute_pipeline(steps)
    return {"result": result}


# ═══════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════

@router.get("/tools")
async def list_tools(category: str | None = None):
    cat = ToolCategory(category) if category else None
    tools = tool_registry.list_tools(cat)
    return [
        {
            "name": t.name,
            "description": t.description,
            "category": t.category.value,
            "parameters": [
                {"name": p.name, "type": p.type, "description": p.description, "required": p.required}
                for p in t.parameters
            ],
        }
        for t in tools
    ]


@router.get("/tools/categories")
async def list_tool_categories():
    return [c.value for c in ToolCategory]


@router.post("/tools/execute")
async def execute_tool(data: ToolExecuteRequest):
    result = await tool_registry.execute(data.name, data.arguments)
    return {
        "name": result.name,
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@router.post("/tools/execute/batch")
async def execute_tools_batch(calls: list[ToolExecuteRequest]):
    results = await tool_registry.execute_batch(
        [(c.name, c.arguments) for c in calls]
    )
    return [
        {
            "name": r.name, "success": r.success,
            "output": r.output[:500], "error": r.error,
            "duration_ms": r.duration_ms,
        }
        for r in results
    ]


@router.get("/tools/stats")
async def get_tool_stats():
    return tool_registry.get_execution_stats()


# ═══════════════════════════════════════════════════════════
# Agent Memories
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/memories")
async def get_agent_memories(
    agent_id: str,
    query: str | None = None,
    limit: int = Query(20, ge=1, le=100),
):
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
                "tags": (m.meta or {}).get("tags", []),
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in result.scalars().all()
        ]


@router.get("/agents/{agent_id}/memories/stats")
async def get_memory_stats(agent_id: str):
    engine = orchestrator.get_engine(agent_id, "", "")
    stats = await engine.memory.get_memory_stats()
    return stats


@router.get("/agents/{agent_id}/memories/tags")
async def get_memory_tags(agent_id: str):
    engine = orchestrator.get_engine(agent_id, "", "")
    return await engine.memory.get_all_tags()


@router.get("/agents/{agent_id}/memories/search")
async def search_memories(agent_id: str, q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    engine = orchestrator.get_engine(agent_id, "", "")
    return await engine.memory.search(q, limit)


@router.post("/agents/{agent_id}/memories/{memory_id}/tag")
async def tag_memory(agent_id: str, memory_id: str, data: MemoryTagRequest):
    engine = orchestrator.get_engine(agent_id, "", "")
    success = await engine.memory.tag(memory_id, data.tags)
    if not success:
        raise HTTPException(404, "Memory not found")
    return {"success": True}


@router.delete("/agents/{agent_id}/memories/{memory_id}/tag")
async def untag_memory(agent_id: str, memory_id: str, data: MemoryTagRequest):
    engine = orchestrator.get_engine(agent_id, "", "")
    success = await engine.memory.untag(memory_id, data.tags)
    if not success:
        raise HTTPException(404, "Memory not found")
    return {"success": True}


@router.put("/agents/{agent_id}/memories/{memory_id}")
async def update_memory(agent_id: str, memory_id: str, data: MemoryUpdateRequest):
    engine = orchestrator.get_engine(agent_id, "", "")
    success = await engine.memory.update(memory_id, data.content, data.importance)
    if not success:
        raise HTTPException(404, "Memory not found")
    return {"success": True}


@router.delete("/agents/{agent_id}/memories/{memory_id}", status_code=204)
async def delete_memory(agent_id: str, memory_id: str):
    engine = orchestrator.get_engine(agent_id, "", "")
    success = await engine.memory.forget(memory_id)
    if not success:
        raise HTTPException(404, "Memory not found")


@router.post("/agents/{agent_id}/memories/export")
async def export_memories(agent_id: str):
    engine = orchestrator.get_engine(agent_id, "", "")
    return await engine.memory.export_memories()


@router.post("/agents/{agent_id}/memories/decay")
async def decay_memories(agent_id: str, days: int = Query(30, ge=1), rate: float = Query(0.1, ge=0.01, le=0.5)):
    engine = orchestrator.get_engine(agent_id, "", "")
    count = await engine.memory.decay_importance(days, rate)
    return {"decayed": count}


# ═══════════════════════════════════════════════════════════
# Model Routing
# ═══════════════════════════════════════════════════════════

@router.get("/routing/stats")
async def get_routing_stats():
    return model_router.get_usage_stats()


@router.post("/routing/analyze")
async def analyze_complexity(message: str = Query(..., min_length=1)):
    complexity = model_router.analyze_complexity(message)
    routing = model_router.route(message)
    return {
        "message": message[:200],
        "complexity": complexity.value,
        "routing": {
            "tier": routing.tier.value,
            "model": routing.model,
            "temperature": routing.temperature,
            "max_tokens": routing.max_tokens,
            "reasoning": routing.reasoning,
        },
    }


# ═══════════════════════════════════════════════════════════
# Autopilot / Scheduled Tasks
# ═══════════════════════════════════════════════════════════

@router.get("/autopilots")
async def list_autopilots(agent_id: str | None = None):
    if agent_id:
        return autopilot_engine.list_by_agent(agent_id)
    return autopilot_engine.list_all()


@router.get("/autopilots/{autopilot_id}")
async def get_autopilot(autopilot_id: str):
    config = autopilot_engine.get(autopilot_id)
    if not config:
        raise HTTPException(404, "Autopilot not found")
    return config.to_dict()


@router.post("/autopilots", status_code=201)
async def create_autopilot(data: AutopilotCreate):
    try:
        trigger = AutopilotTrigger(data.trigger)
    except ValueError:
        raise HTTPException(400, f"Invalid trigger: {data.trigger}")

    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == data.agent_id))
        if not result.scalars().first():
            raise HTTPException(404, "Agent not found")

    config = autopilot_engine.create(
        agent_id=data.agent_id,
        name=data.name,
        task_template=data.task_template,
        trigger=trigger,
        schedule=data.schedule,
        max_runs=data.max_runs,
        description=data.description,
    )
    return config.to_dict()


@router.post("/autopilots/{autopilot_id}/pause")
async def pause_autopilot(autopilot_id: str):
    success = autopilot_engine.pause(autopilot_id)
    if not success:
        raise HTTPException(404, "Autopilot not found")
    return {"success": True}


@router.post("/autopilots/{autopilot_id}/resume")
async def resume_autopilot(autopilot_id: str):
    success = autopilot_engine.resume(autopilot_id)
    if not success:
        raise HTTPException(404, "Autopilot not found")
    return {"success": True}


@router.delete("/autopilots/{autopilot_id}", status_code=204)
async def delete_autopilot(autopilot_id: str):
    success = autopilot_engine.delete(autopilot_id)
    if not success:
        raise HTTPException(404, "Autopilot not found")


# ═══════════════════════════════════════════════════════════
# Workspace
# ═══════════════════════════════════════════════════════════

_workspaces: dict[str, AgentWorkspace] = {}


def _get_workspace(agent_id: str) -> AgentWorkspace:
    if agent_id not in _workspaces:
        _workspaces[agent_id] = AgentWorkspace(agent_id)
    return _workspaces[agent_id]


@router.get("/agents/{agent_id}/workspace")
async def get_workspace_stats(agent_id: str):
    ws = _get_workspace(agent_id)
    return ws.get_stats()


@router.get("/agents/{agent_id}/workspace/files")
async def list_workspace_files(agent_id: str, subdir: str = ""):
    ws = _get_workspace(agent_id)
    files = ws.list_files(subdir)
    return [
        {
            "name": f.name, "path": f.path, "language": f.language,
            "size": f.size, "created_at": f.created_at, "updated_at": f.updated_at,
        }
        for f in files
    ]


@router.get("/agents/{agent_id}/workspace/files/{path:path}")
async def get_workspace_file(agent_id: str, path: str):
    ws = _get_workspace(agent_id)
    wf = ws.read_file(path)
    if not wf:
        raise HTTPException(404, "File not found")
    return {
        "name": wf.name, "path": wf.path, "content": wf.content,
        "language": wf.language, "size": wf.size,
        "created_at": wf.created_at, "updated_at": wf.updated_at,
    }


@router.post("/agents/{agent_id}/workspace/files", status_code=201)
async def create_workspace_file(agent_id: str, data: WorkspaceFileCreate):
    ws = _get_workspace(agent_id)
    try:
        wf = ws.create_file(data.name, data.content, data.subdir)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "name": wf.name, "path": wf.path, "content": wf.content,
        "language": wf.language, "size": wf.size,
        "created_at": wf.created_at, "updated_at": wf.updated_at,
    }


@router.put("/agents/{agent_id}/workspace/files/{path:path}")
async def update_workspace_file(agent_id: str, path: str, data: WorkspaceFileUpdate):
    ws = _get_workspace(agent_id)
    wf = ws.update_file(path, data.content)
    if not wf:
        raise HTTPException(404, "File not found")
    return {
        "name": wf.name, "path": wf.path, "content": wf.content,
        "language": wf.language, "size": wf.size,
        "updated_at": wf.updated_at,
    }


@router.delete("/agents/{agent_id}/workspace/files/{path:path}", status_code=204)
async def delete_workspace_file(agent_id: str, path: str):
    ws = _get_workspace(agent_id)
    success = ws.delete_file(path)
    if not success:
        raise HTTPException(404, "File not found")


@router.post("/agents/{agent_id}/workspace/execute/python")
async def execute_python(agent_id: str, data: CodeExecute):
    ws = _get_workspace(agent_id)
    result = await ws.execute_python(data.code, data.timeout)
    return {
        "success": result.success, "output": result.output,
        "error": result.error, "exit_code": result.exit_code,
        "execution_time": result.execution_time,
    }


@router.post("/agents/{agent_id}/workspace/execute/shell")
async def execute_shell(agent_id: str, data: ShellExecute):
    ws = _get_workspace(agent_id)
    result = await ws.execute_shell(data.command, data.timeout)
    return {
        "success": result.success, "output": result.output,
        "error": result.error, "exit_code": result.exit_code,
        "execution_time": result.execution_time,
    }


# ═══════════════════════════════════════════════════════════
# Sub-Agent Parallel Execution
# ═══════════════════════════════════════════════════════════

_subagent_orchestrators: dict[str, SubAgentOrchestrator] = {}


def _get_subagent_orchestrator(agent_id: str) -> SubAgentOrchestrator:
    if agent_id not in _subagent_orchestrators:
        _subagent_orchestrators[agent_id] = SubAgentOrchestrator(agent_id)
    return _subagent_orchestrators[agent_id]


@router.post("/agents/{agent_id}/subagents/execute")
async def execute_subagents(agent_id: str, data: SubAgentBatch):
    o = _get_subagent_orchestrator(agent_id)
    tasks = [
        {"name": t.name, "instructions": t.instructions, "task": t.task}
        for t in data.tasks
    ]
    results = await o.execute_parallel(tasks, data.model)
    return [
        {
            "agent_id": r.agent_id, "task": r.task[:200],
            "result": r.result[:500], "status": r.status.value,
            "tokens_used": r.tokens_used,
            "started_at": r.started_at, "completed_at": r.completed_at,
        }
        for r in results
    ]


@router.post("/agents/{agent_id}/subagents/aggregate")
async def aggregate_subagent_results(agent_id: str, data: SubAgentBatch):
    o = _get_subagent_orchestrator(agent_id)
    tasks = [
        {"name": t.name, "instructions": t.instructions, "task": t.task}
        for t in data.tasks
    ]
    results = await o.execute_parallel(tasks, data.model)
    aggregated = o.aggregate_results(results)
    return {
        "aggregated": aggregated,
        "results": [
            {
                "agent_id": r.agent_id, "status": r.status.value,
                "tokens_used": r.tokens_used,
            }
            for r in results
        ],
    }


# ═══════════════════════════════════════════════════════════
# Plans
# ═══════════════════════════════════════════════════════════

@router.get("/plans")
async def list_plans(agent_id: str | None = None):
    plans = planning_engine.list_plans(agent_id)
    return [p.to_dict() for p in plans]


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan.to_dict()


@router.post("/plans/generate", status_code=201)
async def generate_plan(data: PlanGenerateRequest):
    plan = await planning_engine.generate_plan(data.goal, data.agent_id)
    return plan.to_dict()


@router.post("/plans/{plan_id}/execute")
async def execute_plan(plan_id: str, data: PlanExecuteRequest):
    plan = planning_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")

    engine = orchestrator.get_engine(data.agent_id, "", "")

    async def step_executor(prompt: str, model: str) -> str:
        result = await engine.chat(prompt, enable_tools=True, enable_reasoning=True)
        return result if isinstance(result, str) else ""

    plan = await planning_engine.execute_plan(plan_id, step_executor)
    return plan.to_dict()


@router.post("/plans/{plan_id}/cancel")
async def cancel_plan(plan_id: str):
    success = planning_engine.cancel_plan(plan_id)
    if not success:
        raise HTTPException(404, "Plan not found")
    return {"success": True}


@router.delete("/plans/{plan_id}", status_code=204)
async def delete_plan(plan_id: str):
    success = planning_engine.delete_plan(plan_id)
    if not success:
        raise HTTPException(404, "Plan not found")


@router.get("/plans/stats/overview")
async def get_plan_stats():
    return planning_engine.get_stats()


# ═══════════════════════════════════════════════════════════
# Multi-Agent Collaboration
# ═══════════════════════════════════════════════════════════

@router.post("/collaborate")
async def collaborate_agents(data: CollaborationRequest):
    result = await orchestrator.collaborate(
        query=data.query,
        agent_ids=data.agent_ids,
        max_rounds=data.max_rounds,
    )
    return result


@router.post("/transfer")
async def transfer_task(data: TransferRequest):
    result = await orchestrator.transfer(
        from_agent_id=data.from_agent_id,
        to_agent_id=data.to_agent_id,
        context=data.context,
    )
    return result


@router.post("/verify")
async def verify_response(data: VerifyRequest):
    result = await orchestrator.verify_response(
        verification_agent_id=data.verification_agent_id,
        original_response=data.original_response,
        original_query=data.original_query,
    )
    return result


@router.get("/agents/{agent_id}/trust")
async def get_agent_trust(agent_id: str):
    trusted = orchestrator.get_trusted_agents(agent_id)
    return {
        "agent_id": agent_id,
        "trusted_agents": trusted,
        "count": len(trusted),
    }


# ═══════════════════════════════════════════════════════════
# MCP Servers
# ═══════════════════════════════════════════════════════════

@router.get("/mcp/servers")
async def list_mcp_servers():
    return mcp_registry.get_server_states()


@router.get("/mcp/tools")
async def list_mcp_tools(server_id: str | None = None):
    tools = mcp_registry.get_tools(server_id)
    return [t.to_dict() for t in tools]


@router.get("/mcp/resources")
async def list_mcp_resources(server_id: str | None = None):
    resources = mcp_registry.get_resources(server_id)
    return [
        {"uri": r.uri, "name": r.name, "description": r.description,
         "mime_type": r.mime_type, "server_id": r.server_id}
        for r in resources
    ]


@router.post("/mcp/servers", status_code=201)
async def register_mcp_server(data: MCPServerRegisterRequest):
    try:
        transport = MCPTransport(data.transport)
    except ValueError:
        raise HTTPException(400, f"Invalid transport: {data.transport}")

    config = MCPServerConfig(
        id=f"mcp-{uuid.uuid4().hex[:8]}",
        name=data.name,
        transport=transport,
        endpoint=data.endpoint,
        command=data.command,
        env=data.env,
    )
    state = mcp_registry.register_server(config)
    return {
        "id": state.config.id,
        "name": state.config.name,
        "transport": state.config.transport.value,
        "status": state.status.value,
    }


@router.post("/mcp/servers/{server_id}/connect")
async def connect_mcp_server(server_id: str):
    success = await mcp_registry.connect_server(server_id)
    if not success:
        state = mcp_registry._servers.get(server_id)
        error = state.last_error if state else "Server not found"
        raise HTTPException(400, f"Connection failed: {error}")
    return {"success": True, "server_id": server_id}


@router.post("/mcp/servers/{server_id}/disconnect")
async def disconnect_mcp_server(server_id: str):
    success = mcp_registry.disconnect_server(server_id)
    if not success:
        raise HTTPException(404, "Server not found")
    return {"success": True}


@router.delete("/mcp/servers/{server_id}", status_code=204)
async def unregister_mcp_server(server_id: str):
    success = mcp_registry.unregister_server(server_id)
    if not success:
        raise HTTPException(404, "Server not found")


class MCPToolCallRequest(BaseModel):
    arguments: dict = Field(default_factory=dict)


@router.post("/mcp/tools/{tool_name}/call")
async def call_mcp_tool(tool_name: str, data: MCPToolCallRequest):
    result = await mcp_registry.call_tool(tool_name, data.arguments)
    return result


# ═══════════════════════════════════════════════════════════
# Dream Engine
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/dream/status")
async def get_dream_status(agent_id: str):
    engine = orchestrator.get_engine(agent_id, "", "")
    return engine.get_dream_status()


@router.get("/agents/{agent_id}/dream/insights")
async def get_dream_insights(agent_id: str, limit: int = Query(20, ge=1, le=100)):
    engine = orchestrator.get_engine(agent_id, "", "")
    return engine.get_dream_insights(limit)


@router.post("/agents/{agent_id}/dream/start")
async def start_dream_cycle(agent_id: str, interval: int = Query(3600, ge=60, le=86400)):
    engine = orchestrator.get_engine(agent_id, "", "")
    success = await engine.start_dream_cycle(interval)
    if not success:
        raise HTTPException(400, "Dream cycle already running")
    return {"success": True, "agent_id": agent_id, "interval": interval}


@router.post("/agents/{agent_id}/dream/stop")
async def stop_dream_cycle(agent_id: str):
    engine = orchestrator.get_engine(agent_id, "", "")
    success = await engine.stop_dream_cycle()
    if not success:
        raise HTTPException(400, "Dream cycle not running")
    return {"success": True, "agent_id": agent_id}


@router.post("/agents/{agent_id}/dream/run")
async def run_dream_cycle_once(agent_id: str):
    engine = orchestrator.get_engine(agent_id, "", "")
    result = await engine.run_dream_cycle_once()
    return {
        "agent_id": agent_id,
        "insights": [
            {
                "id": i.id,
                "phase": i.phase.value,
                "content": i.content[:300],
                "confidence": i.confidence,
                "created_at": i.created_at,
            }
            for i in result.insights
        ],
        "memories_processed": result.memories_processed,
        "memories_consolidated": result.memories_consolidated,
        "duration_seconds": result.duration_seconds,
    }


# ═══════════════════════════════════════════════════════════
# System Overview
# ═══════════════════════════════════════════════════════════

@router.get("/system/overview")
async def system_overview():
    async with async_session() as session:
        agent_count = (await session.execute(
            select(func.count()).select_from(AgentModel).where(AgentModel.is_active == True)
        )).scalar() or 0
        task_count = (await session.execute(
            select(func.count()).select_from(TaskModel)
        )).scalar() or 0
        active_tasks = (await session.execute(
            select(func.count()).select_from(TaskModel).where(
                TaskModel.status.in_(["queued", "dispatched", "running"])
            )
        )).scalar() or 0
        conv_count = (await session.execute(
            select(func.count()).select_from(ConvModel)
        )).scalar() or 0
        memory_count = (await session.execute(
            select(func.count()).select_from(MemModel)
        )).scalar() or 0

    return {
        "service": "Buddy Platform",
        "version": "0.2.0",
        "agents": {"total": agent_count, "active": orchestrator.active_agents},
        "tasks": {"total": task_count, "active": active_tasks},
        "conversations": {"total": conv_count},
        "memories": {"total": memory_count},
        "autopilots": {"total": len(autopilot_engine.list_all())},
        "plans": {"total": len(planning_engine.list_plans())},
        "mcp_servers": {"total": len(mcp_registry.get_server_states())},
        "routing": model_router.get_usage_stats(),
        "tools": tool_registry.get_execution_stats(),
        "orchestrator": orchestrator.get_orchestrator_stats(),
    }


# ═══════════════════════════════════════════════════════════
# Semantic Memory & Thematic Consolidation
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/memories/semantic")
async def semantic_memory_search(
    agent_id: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
):
    engine = orchestrator.get_engine(agent_id, "", "")
    return await engine.memory.search_semantic(q, limit, min_importance)


@router.post("/agents/{agent_id}/memories/consolidate")
async def consolidate_memories(agent_id: str):
    engine = orchestrator.get_engine(agent_id, "", "")
    return await engine.memory.consolidate_thematic()


# ═══════════════════════════════════════════════════════════
# Tool Approval
# ═══════════════════════════════════════════════════════════

@router.get("/approval/rules")
async def get_approval_rules():
    return approval_engine.get_rules()


@router.post("/approval/check")
async def check_approval(data: ToolExecuteRequest):
    approved = await approval_engine.check(data.name, data.arguments)
    return {"approved": approved, "tool_name": data.name}


@router.post("/approval/session/clear")
async def clear_approval_session():
    approval_engine.clear_session()
    return {"success": True}


# ═══════════════════════════════════════════════════════════
# Event Bus
# ═══════════════════════════════════════════════════════════

@router.get("/events/stats")
async def get_event_stats():
    return event_bus.get_stats()


@router.get("/events/history")
async def get_event_history(
    event_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    et = EventType(event_type) if event_type else None
    return event_bus.get_history(et, limit)


# ═══════════════════════════════════════════════════════════
# WebSocket
# ═══════════════════════════════════════════════════════════

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")

    async def ws_event_handler(event: Event):
        try:
            await websocket.send_json(event.to_dict())
        except Exception:
            pass

    event_bus.subscribe_all(ws_event_handler)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
            except json.JSONDecodeError:
                pass
    except Exception:
        logger.info("WebSocket client disconnected")
    finally:
        event_bus.unsubscribe(None, ws_event_handler)