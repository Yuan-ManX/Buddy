"""Buddy API Routes — REST endpoints for agent, task, conversation, skill management

Complete API with agents, conversations, chat (streaming), tasks, skills,
memories, tools, routing, autopilot, workspace, sub-agents, plans, MCP,
nexus, forge, identity, trajectory, squads, and system.
"""
from __future__ import annotations
import asyncio
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
    nexus, forge, identity, trajectory, squads,
    guard_system, pulse_system,
    ws_manager, self_improvement, gateway_hub, daemon_manager,
    swarm_engine, platform_hub, PlatformSubsystem,
    cost_tracker, enterprise_hub, session_searcher,
)
from agent.cost import cost_tracker as cost_tracker_legacy
from agent.templates import template_registry
from agent.task import task_lifecycle, TaskStatus, TaskKind
from agent.autopilot import AutopilotTrigger, AutopilotStatus
from agent.workspace import AgentWorkspace
from agent.subagent import SubAgentOrchestrator, SubAgentStatus
from agent.mcp import MCPServerConfig, MCPTransport
from agent.tools import ToolCategory, ToolParameter, ToolDefinition
from agent.nexus import PlatformType as NexusPlatformType, RuntimeStatus as NexusRuntimeStatus
from agent.forge import SkillCategory as ForgeSkillCategory, SkillStatus as ForgeSkillStatus
from agent.identity import PersonaType as IdentityPersonaType
from agent.trajectory import TraceAction as TrajectoryTraceAction
from agent.squad import SquadStatus as SquadSquadStatus, MemberRole as SquadMemberRole
from agent.websocket import MessageType as WsMessageType, WebSocketMessage
from agent.protocol import acp, AgentMessage, MessageType as AcpMessageType, MessagePriority
from agent.provider import provider_registry, ProviderType, ProviderConfig
from agent.tool_chain import tool_chain_executor, ToolNode
from agent.discovery import agent_discovery, AgentRegistration, AgentCapability
from agent.resource import resource_manager, ResourceType as ResType, QuotaPeriod
from agent.workflow import WorkflowPriority, TaskState, BlockerType
from config.settings import settings

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


class ConvUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    agent_ids: list[str] | None = None


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


# ── Workspace Isolation Models ─────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="", max_length=512)
    owner_id: str = Field(default="")


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)


class WorkspaceImport(BaseModel):
    data: dict = Field(...)


# ── Soul Profile Models ────────────────────────────────────

class SoulProfileUpdate(BaseModel):
    identity: str | None = Field(default=None, max_length=1024)
    principles: list[str] | None = None
    communication_style: str | None = Field(default=None, max_length=512)
    boundaries: list[str] | None = None
    goals: list[str] | None = None


# ── Scheduled Task Models ──────────────────────────────────

class ScheduledTaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    prompt: str = Field(..., min_length=1, max_length=4096)
    cron_expression: str = Field(default="")
    interval_seconds: int = Field(default=0, ge=0)
    description: str = Field(default="", max_length=512)


# ── Skill Models ───────────────────────────────────────────

class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(default="", max_length=512)
    category: str = Field(default="general", max_length=32)
    parameters: dict = Field(default_factory=dict)


class SkillUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=512)
    category: str | None = Field(default=None, max_length=32)
    parameters: dict | None = None


# ── Context Models ─────────────────────────────────────────

class ContextPinRequest(BaseModel):
    entry_index: int = Field(..., ge=0)


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


class MemoryCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="event")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    conversation_id: str | None = None


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


@router.get("/agents/dashboard")
async def agent_dashboard(agent_id: str | None = None):
    """Get comprehensive agent dashboard data with real-time status for all agents or a specific agent."""
    from database.db import async_session as _async_session
    from database.models import Agent as AgentModel, Task as TaskModel, Memory as MemModel
    from sqlalchemy import select, func

    async with _async_session() as session:
        if agent_id:
            result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
            agents = result.scalars().all()
        else:
            result = await session.execute(select(AgentModel).where(AgentModel.is_active == True))
            agents = result.scalars().all()

        dashboard_agents = []
        for agent in agents:
            task_counts = await session.execute(
                select(TaskModel.status, func.count(TaskModel.id))
                .where(TaskModel.agent_id == agent.id)
                .group_by(TaskModel.status)
            )
            task_stats = {row[0]: row[1] for row in task_counts.all()}

            mem_count = await session.execute(
                select(func.count(MemModel.id)).where(MemModel.agent_id == agent.id)
            )

            engine = orchestrator.get_engine(
                agent_id=agent.id,
                agent_name=agent.name,
                instructions=agent.instructions or "",
            )

            dream_status = {
                "is_running": engine.dream.is_running,
                "interval_seconds": engine.dream.interval,
                "total_insights": engine.dream.insights_count,
            }

            tool_stats = {
                "total_executions": getattr(engine, 'tool_execution_count', 0),
                "successful": getattr(engine, 'tool_success_count', 0),
                "failed": getattr(engine, 'tool_failure_count', 0),
            }

            iteration_info = {
                "remaining": engine.iteration_budget.remaining,
                "is_exhausted": engine.iteration_budget.is_exhausted,
                "usage_ratio": engine.iteration_budget.usage_ratio,
                "total_tokens": engine.total_tokens,
            }

            try:
                agent_costs = cost_tracker.get_agent_costs(agent.id)
            except Exception:
                agent_costs = {"total_cost": 0, "total_tokens": 0, "request_count": 0}

            dashboard_agents.append({
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "personality": agent.personality,
                "avatar": agent.avatar,
                "is_active": agent.is_active,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "tasks": {
                    "total": sum(task_stats.values()),
                    "by_status": task_stats,
                },
                "memory": {
                    "total": mem_count.scalar() or 0,
                },
                "dream": dream_status,
                "iteration": iteration_info,
                "tools": tool_stats,
                "costs": {
                    "total_cost": agent_costs.get("total_cost", 0) if isinstance(agent_costs, dict) else 0,
                    "total_tokens": agent_costs.get("total_tokens", 0) if isinstance(agent_costs, dict) else 0,
                },
            })

    return {
        "agents": dashboard_agents,
        "total_agents": len(dashboard_agents),
        "system_summary": {
            "total_tasks": sum(a["tasks"]["total"] for a in dashboard_agents),
            "total_memories": sum(a["memory"]["total"] for a in dashboard_agents),
            "active_dream_engines": sum(1 for a in dashboard_agents if a["dream"]["is_running"]),
            "total_tokens_used": sum(a["costs"].get("total_tokens", 0) for a in dashboard_agents),
        },
    }


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


@router.put("/conversations/{conv_id}")
async def update_conversation(conv_id: str, data: ConvUpdate):
    async with async_session() as session:
        result = await session.execute(select(ConvModel).where(ConvModel.id == conv_id))
        conv = result.scalars().first()
        if not conv:
            raise HTTPException(404, "Conversation not found")

        if data.title is not None:
            conv.title = data.title
        if data.agent_ids is not None:
            conv.agent_ids = data.agent_ids

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
        tool_state: dict[int, dict] = {}  # Track tool calls by index
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

                # Detect tool call markers emitted by the engine
                if token.startswith("\n[Tool:") and token.endswith("]\n"):
                    # Extract tool name from marker like "\n[Tool: search]\n"
                    tool_name = token.strip()[6:-1].strip()
                    tc_id = f"tc-{uuid.uuid4().hex[:6]}"
                    yield f"data: {json.dumps({'type': 'tool_call', 'id': tc_id, 'name': tool_name})}\n\n"
                elif token.startswith("[Tool:") and token.endswith("]\n"):
                    tool_name = token[6:-1].strip()
                    tc_id = f"tc-{uuid.uuid4().hex[:6]}"
                    yield f"data: {json.dumps({'type': 'tool_call', 'id': tc_id, 'name': tool_name})}\n\n"
                elif token.startswith("Error:") and any(tc in full_response.split(token)[0] for tc in ["[Tool:"]):
                    # Tool error result
                    yield f"data: {json.dumps({'type': 'tool_result', 'error': True, 'content': token})}\n\n"
                elif full_response.count("[Tool:") > 0 and not token.startswith("\n") and not token.startswith("["):
                    # Likely a tool result - emit as tool_result
                    pass  # Yielding as regular token for now
                else:
                    # Regular content token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # If reasoning was enabled, get reasoning summary
            if data.enable_reasoning:
                try:
                    engine = orchestrator.get_engine(agent.id, agent.name, agent.instructions or "")
                    reasoning_stats = engine.get_reasoning_stats()
                    if reasoning_stats.get("total_traces", 0) > 0:
                        avg_time = reasoning_stats.get("avg_time_ms", 0)
                        success_rate = reasoning_stats.get("success_rate", "N/A")
                        yield f"data: {json.dumps({'type': 'reasoning', 'content': f'Reasoning completed: {success_rate} success rate, {avg_time:.0f}ms avg time'})}\n\n"
                except Exception:
                    pass

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


# SSE streaming endpoint with proper event types
@router.post("/agents/{agent_id}/chat/stream")
async def agent_chat_stream(agent_id: str, data: ChatRequest):
    """Stream chat response as Server-Sent Events for a specific agent.

    Emits structured SSE events:
    - thinking: Reasoning steps from the agent
    - tool_call: Tool invocation events
    - tool_result: Tool execution outputs
    - message: Partial text chunks
    - done: Final summary with conversation_id
    - error: Failure event
    """
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
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
            # Emit connected event
            yield f"data: {json.dumps({'type': 'connected', 'agent_id': agent_id})}\n\n"

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

                # Detect thinking/reasoning markers
                if token.startswith("\n[Thinking:") or token.startswith("[Thinking:"):
                    thinking_content = token.replace("\n[Thinking:", "").replace("[Thinking:", "").rstrip("]\n").rstrip("]")
                    yield f"data: {json.dumps({'type': 'thinking', 'content': thinking_content.strip()})}\n\n"
                # Detect tool call markers
                elif token.startswith("\n[Tool:") and token.endswith("]\n"):
                    tool_name = token.strip()[6:-1].strip()
                    tc_id = f"tc-{uuid.uuid4().hex[:6]}"
                    yield f"data: {json.dumps({'type': 'tool_call', 'id': tc_id, 'name': tool_name})}\n\n"
                elif token.startswith("[Tool:") and token.endswith("]\n"):
                    tool_name = token[6:-1].strip()
                    tc_id = f"tc-{uuid.uuid4().hex[:6]}"
                    yield f"data: {json.dumps({'type': 'tool_call', 'id': tc_id, 'name': tool_name})}\n\n"
                # Detect tool result (error)
                elif token.startswith("Error:") and "[Tool:" in full_response.split(token)[0] if token in full_response.split(token)[0] else False:
                    yield f"data: {json.dumps({'type': 'tool_result', 'error': True, 'content': token})}\n\n"
                else:
                    # Regular message chunk
                    yield f"data: {json.dumps({'type': 'message', 'content': token})}\n\n"

                # Send keepalive comment every 15 seconds
                yield ": keepalive\n\n"

            # If reasoning was enabled, add reasoning summary
            if data.enable_reasoning:
                try:
                    engine = orchestrator.get_engine(agent.id, agent.name, agent.instructions or "")
                    reasoning_stats = engine.get_reasoning_stats()
                    if reasoning_stats.get("total_traces", 0) > 0:
                        avg_time = reasoning_stats.get("avg_time_ms", 0)
                        success_rate = reasoning_stats.get("success_rate", "N/A")
                        yield f"data: {json.dumps({'type': 'thinking', 'content': f'Reasoning completed: {success_rate} success rate, {avg_time:.0f}ms avg time'})}\n\n"
                except Exception:
                    pass

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

            # Final summary
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'agent_id': agent_id, 'summary': full_response[:200]})}\n\n"
        except Exception as e:
            logger.error(f"SSE stream error for agent {agent_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

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


@router.post("/agents/{agent_id}/memories", status_code=201)
async def create_agent_memory(agent_id: str, data: MemoryCreateRequest):
    """Create a new memory entry for an agent."""
    engine = orchestrator.get_engine(agent_id, "", "")
    memory_id = await engine.memory.store(
        content=data.content,
        memory_type=data.memory_type,
        importance=data.importance,
        conversation_id=data.conversation_id,
    )
    if data.tags:
        await engine.memory.tag(memory_id, data.tags)
    return {"id": memory_id, "agent_id": agent_id, "content": data.content, "status": "stored"}


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


@router.post("/routing/analyze-deep")
async def analyze_complexity_deep(message: str = Query(..., min_length=1), context_summary: str = Query(default="")):
    """LLM-powered deep complexity analysis for accurate tier routing."""
    complexity = await model_router.analyze_complexity_deep(message, context_summary)
    routing = await model_router.deep_route(message, 0, context_summary)
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


@router.get("/routing/tiers")
async def get_routing_tiers():
    """Get current model tier configuration."""
    return {
        tier.value: {
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "cost_multiplier": config.cost_multiplier,
            "usage_count": model_router._usage_stats.get(tier, 0),
        }
        for tier, config in model_router.tiers.items()
    }


class RoutingTierUpdate(BaseModel):
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=256, le=32768)
    cost_multiplier: float | None = Field(default=None, ge=0.01, le=100.0)


@router.put("/routing/tiers/{tier_name}")
async def update_routing_tier(tier_name: str, data: RoutingTierUpdate):
    """Dynamically reconfigure a model tier."""
    from agent.routing import ModelTier, ModelTierConfig
    try:
        tier = ModelTier(tier_name)
    except ValueError:
        raise HTTPException(400, f"Invalid tier: {tier_name}. Valid: {[t.value for t in ModelTier]}")

    current = model_router.tiers[tier]
    model_router.configure_tier(tier, ModelTierConfig(
        tier=tier,
        model=data.model or current.model,
        temperature=data.temperature if data.temperature is not None else current.temperature,
        max_tokens=data.max_tokens if data.max_tokens is not None else current.max_tokens,
        cost_multiplier=data.cost_multiplier if data.cost_multiplier is not None else current.cost_multiplier,
    ))
    config = model_router.tiers[tier]
    return {
        "tier": tier.value,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "cost_multiplier": config.cost_multiplier,
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
# Workspace Isolation API
# ═══════════════════════════════════════════════════════════

from agent.workspace_isolation import workspace_isolation


@router.post("/workspaces", status_code=201)
async def create_workspace(data: WorkspaceCreate):
    """Create a new fully isolated workspace with sandbox, memory, skills, and context."""
    try:
        workspace_id = workspace_isolation.create_workspace(
            name=data.name,
            description=data.description,
            owner_id=data.owner_id,
        )
        ws = workspace_isolation.get_workspace(workspace_id)
        return {
            "id": workspace_id,
            "name": ws["name"],
            "description": ws["description"],
            "owner_id": ws["owner_id"],
            "created_at": ws["created_at"],
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/workspaces")
async def list_workspaces():
    """List all workspaces with summary information."""
    workspaces = workspace_isolation.list_workspaces()
    return {"workspaces": workspaces, "count": len(workspaces)}


# ── Workspace Hub Stats (must be before /workspaces/{workspace_id}) ─────────

@router.get("/workspaces/stats")
async def get_workspace_hub_stats():
    """Get aggregate workspace statistics from enterprise hub."""
    return enterprise_hub.get_hub_stats()


@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get detailed information about a specific workspace."""
    try:
        ws = workspace_isolation.get_workspace(workspace_id)
        return {
            "id": ws["id"],
            "name": ws["name"],
            "description": ws["description"],
            "owner_id": ws["owner_id"],
            "created_at": ws["created_at"],
            "updated_at": ws["updated_at"],
            "is_active": ws["id"] == workspace_isolation._active_workspace_id,
        }
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(workspace_id: str):
    """Permanently delete a workspace and all its isolated data."""
    try:
        workspace_isolation.delete_workspace(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.post("/workspaces/{workspace_id}/switch")
async def switch_workspace(workspace_id: str):
    """Switch the active workspace context."""
    try:
        workspace_isolation.switch_workspace(workspace_id)
        return {"active_workspace_id": workspace_id, "switched": True}
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.get("/workspaces/{workspace_id}/stats")
async def get_workspace_stats(workspace_id: str):
    """Get resource usage statistics for a workspace."""
    try:
        stats = workspace_isolation.get_workspace_stats(workspace_id)
        return stats
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.post("/workspaces/{workspace_id}/export")
async def export_workspace(workspace_id: str):
    """Export the entire workspace state as a serializable dictionary."""
    try:
        data = workspace_isolation.export_workspace(workspace_id)
        return data
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.post("/workspaces/import", status_code=201)
async def import_workspace(data: WorkspaceImport):
    """Import a workspace from an exported state dictionary."""
    try:
        workspace_id = workspace_isolation.import_workspace(data.data)
        return {"workspace_id": workspace_id, "imported": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/workspaces/{workspace_id}/skills")
async def list_workspace_skills(workspace_id: str):
    """List all skills registered in a workspace."""
    try:
        ws = workspace_isolation.get_workspace(workspace_id)
        skills = ws["skills"].list()
        return {"workspace_id": workspace_id, "skills": skills, "count": len(skills)}
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.post("/workspaces/{workspace_id}/skills", status_code=201)
async def add_workspace_skill(workspace_id: str, data: SkillCreate):
    """Add a new skill to a workspace."""
    try:
        ws = workspace_isolation.get_workspace(workspace_id)
        skill_id = ws["skills"].register(
            name=data.name,
            description=data.description,
            category=data.category,
            parameters=data.parameters,
        )
        return {"skill_id": skill_id, "name": data.name, "workspace_id": workspace_id}
    except KeyError:
        raise HTTPException(404, "Workspace not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/workspaces/{workspace_id}/skills/{skill_id}", status_code=204)
async def remove_workspace_skill(workspace_id: str, skill_id: str):
    """Remove a skill from a workspace by skill name."""
    try:
        ws = workspace_isolation.get_workspace(workspace_id)
        removed = ws["skills"].remove(skill_id)
        if not removed:
            raise HTTPException(404, "Skill not found in workspace")
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.get("/workspaces/{workspace_id}/memories")
async def list_workspace_memories(workspace_id: str):
    """List all memories stored in a workspace."""
    try:
        ws = workspace_isolation.get_workspace(workspace_id)
        recent = ws["memory"].recall_recent(limit=50)
        long_term = ws["memory"].recall_long_term(limit=50)
        return {
            "workspace_id": workspace_id,
            "recent": recent,
            "long_term": long_term,
            "stats": ws["memory"].get_stats(),
        }
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.get("/workspaces/{workspace_id}/context")
async def get_workspace_context(workspace_id: str):
    """Get the current context window state for a workspace."""
    try:
        ws = workspace_isolation.get_workspace(workspace_id)
        usage = ws["context"].get_usage()
        return usage
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.post("/workspaces/{workspace_id}/context/pin")
async def pin_context_entry(workspace_id: str, data: ContextPinRequest):
    """Pin a context entry so it cannot be evicted."""
    try:
        ws = workspace_isolation.get_workspace(workspace_id)
        ws["context"].pin_entry(data.entry_index)
        return {"workspace_id": workspace_id, "pinned_index": data.entry_index}
    except KeyError:
        raise HTTPException(404, "Workspace not found")
    except IndexError:
        raise HTTPException(400, "Invalid entry index")


@router.post("/workspaces/{workspace_id}/context/unpin")
async def unpin_context_entry(workspace_id: str, data: ContextPinRequest):
    """Unpin a previously pinned context entry."""
    try:
        ws = workspace_isolation.get_workspace(workspace_id)
        ws["context"].unpin_entry(data.entry_index)
        return {"workspace_id": workspace_id, "unpinned_index": data.entry_index}
    except KeyError:
        raise HTTPException(404, "Workspace not found")
    except IndexError:
        raise HTTPException(400, "Invalid entry index")


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
    result = planning_engine.get_stats()
    if isinstance(result, dict):
        result.setdefault("status", "active")
    return result


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


@router.get("/mcp/servers/{server_id}")
async def get_mcp_server(server_id: str):
    state = mcp_registry._servers.get(server_id)
    if not state:
        raise HTTPException(404, "MCP server not found")
    return {
        "id": state.config.id,
        "name": state.config.name,
        "transport": state.config.transport.value,
        "endpoint": state.config.endpoint,
        "command": state.config.command,
        "env": state.config.env,
        "status": state.status.value,
        "last_error": state.last_error,
        "tool_count": mcp_registry.get_tool_count(server_id),
        "resource_count": mcp_registry.get_resource_count(server_id),
    }


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
# Memory Nudge System
# ═══════════════════════════════════════════════════════════

_nudge_engines: dict[str, Any] = {}


def _get_nudge_engine(agent_id: str):
    if agent_id not in _nudge_engines:
        from agent.nudge import MemoryNudgeEngine
        engine = orchestrator.get_engine(agent_id, "", "")
        _nudge_engines[agent_id] = MemoryNudgeEngine(agent_id, engine.memory)
    return _nudge_engines[agent_id]


@router.post("/agents/{agent_id}/nudge/analyze")
async def analyze_nudges(agent_id: str):
    nudge = _get_nudge_engine(agent_id)
    suggestions = await nudge.analyze()
    return [s.__dict__ for s in suggestions]


@router.get("/agents/{agent_id}/nudge/suggestions")
async def get_nudge_suggestions(agent_id: str, status: str | None = None):
    nudge = _get_nudge_engine(agent_id)
    return nudge.get_suggestions(status)


@router.get("/agents/{agent_id}/nudge/stats")
async def get_nudge_stats(agent_id: str):
    nudge = _get_nudge_engine(agent_id)
    return nudge.get_stats()


@router.post("/agents/{agent_id}/nudge/{nudge_id}/apply")
async def apply_nudge(agent_id: str, nudge_id: str):
    nudge = _get_nudge_engine(agent_id)
    return await nudge.apply(nudge_id)


@router.post("/agents/{agent_id}/nudge/{nudge_id}/revert")
async def revert_nudge(agent_id: str, nudge_id: str):
    nudge = _get_nudge_engine(agent_id)
    return await nudge.revert(nudge_id)


@router.post("/agents/{agent_id}/nudge/{nudge_id}/dismiss")
async def dismiss_nudge(agent_id: str, nudge_id: str):
    nudge = _get_nudge_engine(agent_id)
    success = nudge.dismiss(nudge_id)
    if not success:
        raise HTTPException(400, "Cannot dismiss this nudge")
    return {"success": True}


# ═══════════════════════════════════════════════════════════
# Cost Tracking
# ═══════════════════════════════════════════════════════════

@router.get("/costs/system")
async def get_system_costs():
    return cost_tracker_legacy.get_system_summary()


@router.get("/costs/agents/{agent_id}")
async def get_agent_costs(agent_id: str):
    return cost_tracker_legacy.get_agent_summary(agent_id)


@router.get("/costs/tasks/{task_id}")
async def get_task_cost(task_id: str):
    cost = cost_tracker_legacy.get_task_cost(task_id)
    if not cost:
        raise HTTPException(404, "Task cost record not found")
    return cost


# ═══════════════════════════════════════════════════════════
# Workflow Templates
# ═══════════════════════════════════════════════════════════

@router.get("/templates")
async def list_templates(category: str | None = None):
    if category:
        return template_registry.list_by_category(category)
    return template_registry.list_all()


@router.get("/templates/categories")
async def list_template_categories():
    return template_registry.get_categories()


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    plan = template_registry.instantiate_as_plan(template_id)
    if not plan:
        raise HTTPException(404, "Template not found")
    return plan


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
        "version": settings.VERSION,
        "agents": {"total": agent_count, "active": orchestrator.active_agents},
        "tasks": {"total": task_count, "active": active_tasks},
        "conversations": {"total": conv_count},
        "memories": {"total": memory_count},
        "autopilots": {"total": len(autopilot_engine.list_all())},
        "plans": {"total": len(planning_engine.list_plans())},
        "mcp_servers": {"total": len(mcp_registry.get_server_states())},
        "templates": {"total": len(template_registry.list_all())},
        "costs": cost_tracker_legacy.get_system_summary(),
        "routing": model_router.get_usage_stats(),
        "tools": tool_registry.get_execution_stats(),
        "orchestrator": orchestrator.get_orchestrator_stats(),
        "nexus": nexus.get_summary(),
        "forge": forge.get_stats(),
        "squads": squads.get_stats(),
        "trajectory": trajectory.get_stats(),
        "compressor": trajectory_compressor.get_stats(),
        "issue_board": issue_board.get_stats(),
        "skill_compounding": skill_compounding.get_stats(),
        "whitebox_memory": whitebox_memory.get_stats(),
        "platform_health": platform_hub.get_health(),
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
# Buddy Nexus — Runtime & Platform Management
# ═══════════════════════════════════════════════════════════


@router.get("/nexus/summary")
async def get_nexus_summary():
    return nexus.get_summary()


@router.get("/nexus/runtimes")
async def list_runtimes(
    platform: str | None = None,
    status: str | None = None,
):
    p = NexusPlatformType(platform) if platform else None
    s = NexusRuntimeStatus(status) if status else None
    return [r.dict() for r in nexus.list_runtimes(platform=p, status=s)]


@router.get("/nexus/runtimes/{runtime_id}")
async def get_runtime(runtime_id: str):
    info = nexus.get_runtime(runtime_id)
    if not info:
        raise HTTPException(404, "Runtime not found")
    return info.dict()


@router.post("/nexus/runtimes/{runtime_id}/heartbeat")
async def nexus_heartbeat(runtime_id: str):
    ok = nexus.heartbeat(runtime_id)
    if not ok:
        raise HTTPException(404, "Runtime not found")
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════
# Buddy Forge — Skill Creation & Pattern Detection
# ═══════════════════════════════════════════════════════════

class ForgeSkillCreate(BaseModel):
    name: str
    description: str
    category: str = "utility"
    prompt_template: str
    parameters: list[dict] = []
    author_agent_id: str = ""
    tags: list[str] = []


@router.get("/forge/skills")
async def list_forged_skills(category: str | None = None, status: str | None = None):
    c = ForgeSkillCategory(category) if category else None
    s = ForgeSkillStatus(status) if status else None
    return [sk.dict() for sk in forge.list_skills(category=c, status=s)]


@router.get("/forge/skills/{skill_id}")
async def get_forged_skill(skill_id: str):
    skill = forge.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    return skill.dict()


@router.post("/forge/skills")
async def forge_new_skill(data: ForgeSkillCreate):
    from agent.forge import SkillParameter
    params = [
        SkillParameter(**p) for p in data.parameters
    ] if data.parameters else []
    skill = forge.forge_skill(
        name=data.name,
        description=data.description,
        category=ForgeSkillCategory(data.category),
        prompt_template=data.prompt_template,
        parameters=params,
        author_agent_id=data.author_agent_id,
        tags=data.tags,
    )
    return skill.dict()


@router.post("/forge/skills/{skill_id}/evolve")
async def evolve_forged_skill(
    skill_id: str,
    new_prompt_template: str = Query(...),
    reason: str = "",
):
    new_ver = forge.evolve_skill(skill_id, new_prompt_template, reason=reason)
    return new_ver.dict()


@router.post("/forge/skills/{skill_id}/deprecate")
async def deprecate_forged_skill(skill_id: str):
    ok = forge.deprecate_skill(skill_id)
    if not ok:
        raise HTTPException(404, "Skill not found")
    return {"success": True}


@router.post("/forge/skills/{skill_id}/archive")
async def archive_forged_skill(skill_id: str):
    ok = forge.archive_skill(skill_id)
    if not ok:
        raise HTTPException(404, "Skill not found")
    return {"success": True}


@router.get("/forge/patterns")
async def list_forge_patterns():
    return {
        "patterns": [p.dict() for p in forge._patterns.values()],
        "promotable": [p.dict() for p in forge.get_promotable_patterns()],
    }


@router.post("/forge/patterns/{pattern_id}/promote")
async def promote_pattern(
    pattern_id: str,
    name: str = Query(...),
    description: str = Query(""),
    prompt_template: str = Query(...),
):
    skill = forge.promote_to_skill(pattern_id, name, description, prompt_template)
    if not skill:
        raise HTTPException(404, "Pattern not found")
    return skill.dict()


@router.get("/forge/stats")
async def get_forge_stats():
    result = forge.get_stats()
    if isinstance(result, dict):
        result.setdefault("total_skills", 0)
    return result


@router.post("/forge/observe")
async def observe_interaction(
    user_message: str = Query(""),
    actions: str = Query(""),
    agent_id: str = Query(""),
):
    action_list = actions.split(",") if actions else []
    forge.observe_interaction(user_message, action_list, agent_id)
    return {"observed": True}


@router.post("/forge/skills/{skill_id}/record")
async def record_skill_execution(
    skill_id: str,
    version: int = Query(...),
    success: bool = Query(...),
    tokens: int = Query(0),
    latency_ms: float = Query(0.0),
):
    forge.record_execution(skill_id, version, success, tokens, latency_ms)
    return {"recorded": True}


# ═══════════════════════════════════════════════════════════
# Buddy Identity — Personal AI Identity Profiles
# ═══════════════════════════════════════════════════════════

class IdentityPersonaCreate(BaseModel):
    name: str
    persona_type: str = "companion"
    description: str = ""
    tone: str = "professional"
    verbosity: str = "moderate"
    expertise_areas: list[str] = []


@router.get("/identity/profiles/{agent_id}")
async def get_identity_profile(agent_id: str, user_id: str = "default"):
    profile = identity.get_or_create_profile(agent_id, user_id)
    return profile.dict()


@router.get("/identity/profiles/{agent_id}/summary")
async def get_identity_summary(agent_id: str, user_id: str = "default"):
    return identity.get_profile_summary(agent_id, user_id)


@router.post("/identity/profiles/{agent_id}/attributes")
async def set_identity_attribute(
    agent_id: str,
    key: str = Query(...),
    value: str = Query(...),
    category: str = Query("preference"),
    confidence: float = Query(0.7),
    user_id: str = Query("default"),
):
    from agent.identity import AttributeCategory
    identity.set_attribute(
        agent_id, key, value,
        AttributeCategory(category),
        confidence,
        user_id=user_id,
    )
    return {"success": True}


@router.get("/identity/profiles/{agent_id}/attributes/{key}")
async def get_identity_attribute(agent_id: str, key: str, user_id: str = "default"):
    attr = identity.get_attribute(agent_id, key, user_id)
    if not attr:
        raise HTTPException(404, "Attribute not found")
    return attr.dict()


@router.delete("/identity/profiles/{agent_id}/attributes/{key}")
async def delete_identity_attribute(agent_id: str, key: str, user_id: str = "default"):
    ok = identity.delete_attribute(agent_id, key, user_id)
    if not ok:
        raise HTTPException(404, "Attribute not found")
    return {"success": True}


@router.post("/identity/profiles/{agent_id}/attributes/{key}/lock")
async def lock_identity_attribute(agent_id: str, key: str, user_id: str = "default"):
    ok = identity.lock_attribute(agent_id, key, user_id)
    if not ok:
        raise HTTPException(404, "Attribute not found")
    return {"success": True}


@router.post("/identity/profiles/{agent_id}/attributes/{key}/unlock")
async def unlock_identity_attribute(agent_id: str, key: str, user_id: str = "default"):
    ok = identity.unlock_attribute(agent_id, key, user_id)
    if not ok:
        raise HTTPException(404, "Attribute not found")
    return {"success": True}


@router.post("/identity/profiles/{agent_id}/personas")
async def add_identity_persona(agent_id: str, data: IdentityPersonaCreate, user_id: str = "default"):
    from agent.identity import Persona
    persona = Persona(
        name=data.name,
        persona_type=IdentityPersonaType(data.persona_type),
        description=data.description,
        tone=data.tone,
        verbosity=data.verbosity,
        expertise_areas=data.expertise_areas,
    )
    identity.add_persona(agent_id, persona, user_id)
    return persona.dict()


@router.post("/identity/profiles/{agent_id}/personas/{persona_name}/activate")
async def activate_identity_persona(agent_id: str, persona_name: str, user_id: str = "default"):
    ok = identity.activate_persona(agent_id, persona_name, user_id)
    if not ok:
        raise HTTPException(404, "Profile or persona not found")
    return {"success": True, "active_persona": persona_name}


@router.post("/identity/profiles/{agent_id}/learn")
async def learn_from_interaction(
    agent_id: str,
    user_message: str = Query(""),
    insights: str = Query("[]"),
    user_id: str = Query("default"),
):
    import json
    try:
        insights_list = json.loads(insights)
    except json.JSONDecodeError:
        insights_list = []
    identity.learn_from_interaction(agent_id, user_message, insights_list, user_id)
    return {"success": True}


# ═══════════════════════════════════════════════════════════
# Buddy Trajectory — Execution Trace & Compression
# ═══════════════════════════════════════════════════════════


@router.post("/trajectory/start")
async def start_trajectory(agent_id: str = Query(...), task_id: str = Query("")):
    trace = trajectory.start_trace(agent_id, task_id)
    return trace.dict()


@router.post("/trajectory/{trace_id}/step")
async def record_trajectory_step(
    trace_id: str,
    action: str = Query(...),
    content: str = Query(""),
    tokens: int = Query(0),
    tool_name: str = Query(""),
):
    trajectory.record_step(
        trace_id,
        TrajectoryTraceAction(action),
        content,
        tokens=tokens,
        tool_name=tool_name,
    )
    return {"recorded": True}


@router.post("/trajectory/{trace_id}/complete")
async def complete_trajectory(
    trace_id: str,
    success: bool = Query(...),
    quality_score: float = Query(1.0),
):
    trace = trajectory.complete_trace(trace_id, success, quality_score)
    if not trace:
        raise HTTPException(404, "Trace not found")
    compressed = trajectory.compress_trace(trace)
    return compressed.dict()


@router.post("/trajectory/{trace_id}/cancel")
async def cancel_trajectory(trace_id: str):
    trajectory.cancel_trace(trace_id)
    return {"cancelled": True}


@router.get("/trajectory/stats")
async def get_trajectory_stats():
    return trajectory.get_stats()


@router.get("/trajectory/recent")
async def get_recent_trajectories(limit: int = 20):
    return [t.dict() for t in trajectory.get_recent_trajectories(limit)]


@router.get("/trajectory/successful")
async def get_successful_trajectories(limit: int = 50):
    return [t.dict() for t in trajectory.get_successful_trajectories(limit)]


@router.get("/trajectory/failed")
async def get_failed_trajectories(limit: int = 20):
    return [t.dict() for t in trajectory.get_failed_trajectories(limit)]


@router.get("/trajectory/by-agent/{agent_id}")
async def get_agent_trajectories(agent_id: str, limit: int = 50):
    return [t.dict() for t in trajectory.get_trajectories_by_agent(agent_id, limit)]


@router.get("/trajectory/{trace_id}")
async def get_trajectory(trace_id: str):
    trace = trajectory.get_active_trace(trace_id)
    if not trace:
        raise HTTPException(404, "Trace not found")
    return trace.dict()


# ═══════════════════════════════════════════════════════════
# Compressor — Execution History Compression & Pattern Detection
# ═══════════════════════════════════════════════════════════

from agent.compressor import trajectory_compressor


@router.post("/agents/{agent_id}/compressor/compress")
async def compress_agent_trajectory(
    agent_id: str,
    conversation_id: str = Query(default=""),
):
    """Compress the current execution trajectory for an agent."""
    engine = orchestrator.get_engine(agent_id, "", "")
    compressed = engine.compress_execution(session_id=conversation_id)
    return compressed.to_dict()


@router.get("/agents/{agent_id}/compressor/trajectories")
async def list_compressed_trajectories(
    agent_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    """List compressed trajectories for an agent."""
    engine = orchestrator.get_engine(agent_id, "", "")
    return {
        "agent_id": agent_id,
        "trajectories": engine.get_compressed_trajectories(limit),
    }


@router.get("/agents/{agent_id}/compressor/patterns")
async def get_agent_execution_patterns(
    agent_id: str,
    pattern_type: str | None = None,
):
    """Get detected execution patterns for an agent."""
    engine = orchestrator.get_engine(agent_id, "", "")
    patterns = engine.get_detected_patterns(pattern_type)
    return {"agent_id": agent_id, "patterns": patterns, "count": len(patterns)}


@router.get("/compressor/stats")
async def get_compressor_stats():
    """Get global compressor statistics."""
    return trajectory_compressor.get_stats()


@router.get("/compressor/export")
async def export_training_data(
    agent_id: str | None = None,
    format: str = Query(default="jsonl"),
):
    """Export compressed trajectories as training data."""
    data = trajectory_compressor.export_training_data(agent_id=agent_id, format=format)
    return {"format": format, "agent_id": agent_id, "data": data}


# ═══════════════════════════════════════════════════════════
# Checkpoint — Agent State Preservation & Rollback
# ═══════════════════════════════════════════════════════════


@router.post("/agents/{agent_id}/checkpoints")
async def save_agent_checkpoint(agent_id: str, name: str = Query(default="manual")):
    """Save a checkpoint of the agent's current state."""
    engine = orchestrator.get_engine(agent_id, "", "")
    checkpoint_id = engine.save_checkpoint(name)
    return {"agent_id": agent_id, "checkpoint_id": checkpoint_id, "name": name}


@router.get("/agents/{agent_id}/checkpoints")
async def list_agent_checkpoints(agent_id: str):
    """List all checkpoints for an agent."""
    engine = orchestrator.get_engine(agent_id, "", "")
    return {"agent_id": agent_id, "checkpoints": engine.list_checkpoints()}


@router.post("/agents/{agent_id}/checkpoints/{checkpoint_id}/restore")
async def restore_agent_checkpoint(agent_id: str, checkpoint_id: str):
    """Restore agent state from a checkpoint."""
    engine = orchestrator.get_engine(agent_id, "", "")
    success = engine.restore_checkpoint(checkpoint_id)
    if not success:
        raise HTTPException(404, "Checkpoint not found")
    return {"agent_id": agent_id, "restored": True, "checkpoint_id": checkpoint_id}


@router.delete("/agents/{agent_id}/checkpoints/{checkpoint_id}")
async def delete_agent_checkpoint(agent_id: str, checkpoint_id: str):
    """Delete an agent checkpoint."""
    engine = orchestrator.get_engine(agent_id, "", "")
    success = engine.delete_checkpoint(checkpoint_id)
    if not success:
        raise HTTPException(404, "Checkpoint not found")
    return {"agent_id": agent_id, "deleted": True}


@router.post("/agents/{agent_id}/trajectory/clear")
async def clear_agent_trajectory(agent_id: str):
    """Reset the agent's execution trajectory buffer."""
    engine = orchestrator.get_engine(agent_id, "", "")
    engine.clear_trajectory()
    return {"agent_id": agent_id, "cleared": True}


# ═══════════════════════════════════════════════════════════
# Buddy Squads — Collaborative Agent Teams
# ═══════════════════════════════════════════════════════════

class SquadForm(BaseModel):
    name: str
    description: str = ""
    leader_id: str = ""


@router.post("/squads")
async def form_squad(data: SquadForm):
    squad = squads.form_squad(data.name, data.description, data.leader_id)
    return squad.dict()


@router.get("/squads")
async def list_squads(status: str | None = None):
    s = SquadSquadStatus(status) if status else None
    return [sq.dict() for sq in squads.list_squads(status=s)]


@router.get("/squads/stats")
async def get_squad_stats():
    return squads.get_stats()


@router.get("/squads/by-agent/{agent_id}")
async def get_agent_squads(agent_id: str):
    return [s.dict() for s in squads.get_agent_squads(agent_id)]


@router.get("/squads/{squad_id}")
async def get_squad(squad_id: str):
    squad = squads.get_squad(squad_id)
    if not squad:
        raise HTTPException(404, "Squad not found")
    return squad.dict()


@router.post("/squads/{squad_id}/activate")
async def activate_squad(squad_id: str):
    ok = squads.activate_squad(squad_id)
    if not ok:
        raise HTTPException(404, "Squad not found")
    return {"success": True}


@router.post("/squads/{squad_id}/pause")
async def pause_squad(squad_id: str):
    ok = squads.pause_squad(squad_id)
    if not ok:
        raise HTTPException(404, "Squad not found")
    return {"success": True}


@router.post("/squads/{squad_id}/dissolve")
async def dissolve_squad(squad_id: str):
    ok = squads.dissolve_squad(squad_id)
    if not ok:
        raise HTTPException(404, "Squad not found")
    return {"success": True}


@router.post("/squads/{squad_id}/members")
async def add_squad_member(
    squad_id: str,
    agent_id: str = Query(...),
    agent_name: str = Query(""),
    role: str = Query("generalist"),
    expertise: str = Query(""),
):
    expertise_list = [e.strip() for e in expertise.split(",")] if expertise else []
    try:
        member_role = SquadMemberRole(role)
    except ValueError:
        raise HTTPException(400, f"Invalid role: {role}. Valid roles: {[r.value for r in SquadMemberRole]}")
    ok = squads.add_member(squad_id, agent_id, agent_name, member_role, expertise_list)
    if not ok:
        raise HTTPException(400, "Cannot add member")
    return {"success": True}


@router.delete("/squads/{squad_id}/members/{agent_id}")
async def remove_squad_member(squad_id: str, agent_id: str):
    ok = squads.remove_member(squad_id, agent_id)
    if not ok:
        raise HTTPException(404, "Member not found")
    return {"success": True}


@router.post("/squads/{squad_id}/leader/{agent_id}")
async def set_squad_leader(squad_id: str, agent_id: str):
    ok = squads.set_leader(squad_id, agent_id)
    if not ok:
        raise HTTPException(400, "Cannot set leader")
    return {"success": True}


@router.post("/squads/{squad_id}/delegate")
async def delegate_squad_task(
    squad_id: str,
    task_description: str = Query(...),
    expertise: str = Query(""),
):
    expertise_list = [e.strip() for e in expertise.split(",")] if expertise else None
    result = squads.delegate_task(squad_id, task_description, expertise_list)
    return result


@router.post("/squads/{squad_id}/record-outcome")
async def record_squad_task_outcome(
    squad_id: str,
    agent_id: str = Query(...),
    success: bool = Query(...),
):
    squads.record_task_outcome(squad_id, agent_id, success)
    return {"recorded": True}


@router.post("/squads/{squad_id}/discussions")
async def start_squad_discussion(
    squad_id: str,
    topic: str = Query(...),
    created_by: str = Query(...),
    task_id: str = Query(""),
):
    thread = squads.start_discussion(squad_id, topic, created_by, task_id)
    if not thread:
        raise HTTPException(404, "Squad not found")
    return thread.dict()


@router.post("/squads/{squad_id}/discussions/{thread_id}/post")
async def post_to_discussion(
    squad_id: str,
    thread_id: str,
    agent_id: str = Query(...),
    content: str = Query(...),
):
    ok = squads.post_to_discussion(squad_id, thread_id, agent_id, content)
    if not ok:
        raise HTTPException(404, "Discussion not found")
    return {"posted": True}


@router.post("/squads/{squad_id}/discussions/{thread_id}/resolve")
async def resolve_discussion(
    squad_id: str,
    thread_id: str,
    resolution: str = Query(""),
):
    ok = squads.resolve_discussion(squad_id, thread_id, resolution)
    if not ok:
        raise HTTPException(404, "Discussion not found")
    return {"resolved": True}


# ═══════════════════════════════════════════════════════════
# BuddyGuard — Safety & Security Monitoring
# ═══════════════════════════════════════════════════════════

@router.get("/guard/stats")
async def get_guard_stats():
    from dataclasses import asdict as dc_asdict
    result = guard_system.get_stats()
    if hasattr(result, '__dataclass_fields__'):
        result = dc_asdict(result)
    if isinstance(result, dict):
        result["total_alerts"] = result.get("alerts", 0)
    return result


@router.get("/guard/alerts")
async def get_guard_alerts(
    agent_id: str | None = None,
    min_severity: str | None = None,
):
    from agent.guard import Severity
    sev = Severity(min_severity) if min_severity else None
    alerts = guard_system.get_alerts(agent_id=agent_id, min_severity=sev)
    return [a.__dict__ for a in alerts]


@router.post("/guard/check/content")
async def check_guard_content(
    agent_id: str = Query(...),
    content: str = Query(...),
):
    result = guard_system.check_content(agent_id, content)
    return result.__dict__


@router.post("/guard/check/rate-limit")
async def check_guard_rate_limit(
    agent_id: str = Query(...),
    window_seconds: int = Query(60),
    max_requests: int = Query(100),
):
    result = guard_system.check_rate_limit(agent_id, window_seconds, max_requests)
    return result.__dict__


@router.post("/guard/check/quota")
async def check_guard_quota(
    agent_id: str = Query(...),
    tokens_used: int = Query(...),
    max_tokens: int = Query(1_000_000),
):
    result = guard_system.check_quota(agent_id, tokens_used, max_tokens)
    return result.__dict__


@router.post("/guard/audit")
async def audit_guard_action(
    agent_id: str = Query(...),
    action_name: str = Query(...),
    details: str = Query("{}"),
):
    import json
    try:
        detail_dict = json.loads(details)
    except json.JSONDecodeError:
        detail_dict = {"raw": details}
    guard_system.audit(agent_id, action_name, detail_dict)
    return {"audited": True}


@router.post("/guard/alerts/clear")
async def clear_guard_alerts(agent_id: str | None = None):
    count = guard_system.clear_alerts(agent_id)
    return {"cleared": count}


# ═══════════════════════════════════════════════════════════
# BuddyPulse — Health Monitoring & Metrics
# ═══════════════════════════════════════════════════════════

@router.get("/pulse/health")
async def get_system_health():
    health = pulse_system.get_system_health()
    return {
        "overall_status": health.overall_status.value,
        "total_uptime_seconds": health.total_uptime_seconds,
        "active_components": health.active_components,
        "degraded_components": health.degraded_components,
        "unhealthy_components": health.unhealthy_components,
        "components": [
            {
                "component_id": c.component_id,
                "name": c.name,
                "status": c.status.value,
                "last_heartbeat": c.last_heartbeat,
                "latency_p50_ms": c.latency_p50_ms,
                "latency_p99_ms": c.latency_p99_ms,
                "error_rate": c.error_rate,
                "uptime_seconds": c.uptime_seconds,
                "metadata": c.metadata,
            }
            for c in health.components
        ],
        "recent_alerts": health.recent_alerts,
    }


@router.get("/pulse/components/{component_id}")
async def get_component_health(component_id: str):
    health = pulse_system.get_component_health(component_id)
    if not health:
        raise HTTPException(404, "Component not found")
    return {
        "component_id": health.component_id,
        "name": health.name,
        "status": health.status.value,
        "last_heartbeat": health.last_heartbeat,
        "latency_p50_ms": health.latency_p50_ms,
        "latency_p99_ms": health.latency_p99_ms,
        "error_rate": health.error_rate,
        "uptime_seconds": health.uptime_seconds,
        "metadata": health.metadata,
    }


@router.post("/pulse/components/{component_id}/heartbeat")
async def pulse_heartbeat(component_id: str):
    ok = pulse_system.heartbeat(component_id)
    if not ok:
        raise HTTPException(404, "Component not registered")
    return {"status": "ok"}


@router.get("/pulse/components/{component_id}/latency")
async def get_component_latency(component_id: str):
    stats = pulse_system.get_latency_stats(component_id)
    return stats


@router.get("/pulse/components/{component_id}/errors")
async def get_component_errors(component_id: str):
    stats = pulse_system.get_error_stats(component_id)
    return stats


@router.post("/pulse/record")
async def record_pulse_metric(
    component_id: str = Query(...),
    name: str = Query(...),
    value: float = Query(...),
    unit: str = Query("count"),
):
    pulse_system.record_metric(name, value, unit, component_id)
    return {"recorded": True}


@router.get("/pulse/anomalies")
async def check_pulse_anomalies():
    alerts = pulse_system.check_anomalies()
    return {"alerts": alerts, "count": len(alerts)}


# ═══════════════════════════════════════════════════════════
# Persona Management — Agent identity & behavior control
# ═══════════════════════════════════════════════════════════

_persona_managers: dict[str, Any] = {}


def _get_persona_manager(agent_id: str):
    if agent_id not in _persona_managers:
        from agent.persona import PersonaManager
        _persona_managers[agent_id] = PersonaManager(agent_id)
    return _persona_managers[agent_id]


@router.get("/agents/{agent_id}/personas")
async def list_personas(agent_id: str):
    pm = _get_persona_manager(agent_id)
    return pm.list_personas()


@router.get("/agents/{agent_id}/personas/active")
async def get_active_persona(agent_id: str):
    pm = _get_persona_manager(agent_id)
    persona = pm.active_persona
    if not persona:
        raise HTTPException(404, "No active persona")
    return persona.to_dict()


@router.get("/agents/{agent_id}/personas/presets")
async def list_persona_presets():
    from agent.persona import PRESET_PERSONAS
    return [
        {"key": key, "name": val["name"], "description": val["description"], "tone": val["tone"].value}
        for key, val in PRESET_PERSONAS.items()
    ]


@router.post("/agents/{agent_id}/personas/activate/{persona_id}")
async def activate_persona(agent_id: str, persona_id: str):
    pm = _get_persona_manager(agent_id)
    success = pm.activate(persona_id)
    if not success:
        raise HTTPException(404, "Persona not found")
    return {"success": True, "active_persona_id": persona_id}


@router.post("/agents/{agent_id}/personas/create-from-preset")
async def create_persona_from_preset_endpoint(agent_id: str, preset_name: str = Query(...)):
    from agent.persona import create_persona_from_preset
    try:
        persona = create_persona_from_preset(agent_id, preset_name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    pm = _get_persona_manager(agent_id)
    pm.add_persona(persona)
    return persona.to_dict()


class PersonaCreate(BaseModel):
    name: str = Field(..., min_length=1)
    tone: str = Field(default="collaborator")
    verbosity: str = Field(default="moderate")
    description: str = Field(default="")
    expertise_areas: list[str] = Field(default_factory=list)
    communication_style: str = Field(default="")


@router.post("/agents/{agent_id}/personas", status_code=201)
async def create_custom_persona(agent_id: str, data: PersonaCreate):
    from agent.persona import Persona, ToneMode, VerbosityLevel
    try:
        tone = ToneMode(data.tone)
    except ValueError:
        raise HTTPException(400, f"Invalid tone: {data.tone}. Valid: {[t.value for t in ToneMode]}")
    try:
        verbosity = VerbosityLevel(data.verbosity)
    except ValueError:
        raise HTTPException(400, f"Invalid verbosity: {data.verbosity}. Valid: {[v.value for v in VerbosityLevel]}")

    persona = Persona(
        id=f"persona-{uuid.uuid4().hex[:8]}",
        name=data.name,
        tone=tone,
        verbosity=verbosity,
        description=data.description,
        expertise_areas=data.expertise_areas,
        communication_style=data.communication_style,
    )
    pm = _get_persona_manager(agent_id)
    pm.add_persona(persona)
    return persona.to_dict()


@router.delete("/agents/{agent_id}/personas/{persona_id}", status_code=204)
async def delete_persona(agent_id: str, persona_id: str):
    pm = _get_persona_manager(agent_id)
    success = pm.remove_persona(persona_id)
    if not success:
        raise HTTPException(404, "Persona not found or is default")


# ═══════════════════════════════════════════════════════════
# Gateway — Multi-platform messaging integration
# ═══════════════════════════════════════════════════════════

@router.get("/gateway/stats")
async def get_gateway_stats():
    return gateway_hub.get_stats()


@router.get("/gateway/sessions")
async def get_gateway_sessions():
    return gateway_hub.get_active_sessions()


@router.post("/gateway/platforms/connect")
async def connect_gateway_platform(platform: str = Query(...), config: str = Query(default="{}")):
    from agent.gateway import MessagePlatform
    try:
        p = MessagePlatform(platform)
    except ValueError:
        raise HTTPException(400, f"Invalid platform: {platform}. Valid: {[p.value for p in MessagePlatform]}")
    try:
        config_dict = json.loads(config)
    except json.JSONDecodeError:
        config_dict = {}
    success = await gateway_hub.connect_platform(p, config_dict)
    return {"success": success, "platform": platform}


@router.post("/gateway/send")
async def gateway_send_message(
    platform: str = Query(...),
    user_id: str = Query(...),
    content: str = Query(...),
):
    from agent.gateway import MessagePlatform
    try:
        p = MessagePlatform(platform)
    except ValueError:
        raise HTTPException(400, f"Invalid platform: {platform}")
    success = await gateway_hub.send_to_user(p, user_id, content)
    return {"success": success}


# ═══════════════════════════════════════════════════════════
# Daemon — Background agent runtime management
# ═══════════════════════════════════════════════════════════

@router.get("/daemon/stats")
async def get_daemon_stats():
    return daemon_manager.get_stats()


@router.get("/daemon/agents/{agent_id}")
async def get_agent_daemon(agent_id: str):
    runtime = daemon_manager._runtimes.get(agent_id)
    if not runtime:
        raise HTTPException(404, "Agent daemon not found")
    return runtime.get_stats()


@router.post("/daemon/agents/{agent_id}/start")
async def start_agent_daemon(agent_id: str, agent_name: str = Query(default="")):
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
        a = result.scalars().first()
        name = a.name if a and not agent_name else (agent_name or agent_id)
    success = await daemon_manager.start_agent(agent_id, name)
    return {"success": success, "agent_id": agent_id}


@router.post("/daemon/agents/{agent_id}/stop")
async def stop_agent_daemon(agent_id: str):
    success = await daemon_manager.stop_agent(agent_id)
    return {"success": success}


@router.post("/daemon/agents/{agent_id}/restart")
async def restart_agent_daemon(agent_id: str):
    success = await daemon_manager.restart_agent(agent_id)
    return {"success": success}


@router.post("/daemon/start-all")
async def start_all_daemons():
    await daemon_manager.start_all()
    return {"success": True}


@router.post("/daemon/stop-all")
async def stop_all_daemons():
    await daemon_manager.stop_all()
    return {"success": True}


# ═══════════════════════════════════════════════════════════
# Self-Improvement — Autonomous skill learning loop
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/learning/stats")
async def get_learning_stats(agent_id: str):
    return self_improvement.get_agent_stats(agent_id)


@router.get("/agents/{agent_id}/learning/patterns")
async def get_learning_patterns(agent_id: str):
    loop = self_improvement.get_loop(agent_id)
    return loop.get_patterns()


@router.get("/agents/{agent_id}/learning/candidates")
async def get_learning_candidates(agent_id: str):
    loop = self_improvement.get_loop(agent_id)
    return loop.get_candidates()


@router.get("/learning/history")
async def get_learning_history(limit: int = Query(20, ge=1, le=100)):
    return self_improvement.get_cycle_history(limit)


@router.post("/agents/{agent_id}/learning/record")
async def record_learning_interaction(
    agent_id: str,
    user_message: str = Query(...),
    assistant_response: str = Query(...),
    tools_used: str = Query(default=""),
    success: bool = Query(default=True),
):
    tools = [t.strip() for t in tools_used.split(",")] if tools_used else None
    self_improvement.record(agent_id, user_message, assistant_response, tools, success)
    return {"recorded": True}


@router.post("/agents/{agent_id}/learning/run-cycle")
async def run_learning_cycle(agent_id: str):
    result = await self_improvement.run_cycle(agent_id)
    return result


@router.post("/learning/run-all")
async def run_all_learning_cycles():
    results = await self_improvement.run_all_cycles()
    return {"results": results, "agents_processed": len(results)}


# ═══════════════════════════════════════════════════════════
# WebSocket — Real-time streaming & event broadcast
# ═══════════════════════════════════════════════════════════

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")

    # Register with the WebSocket manager for system-wide events
    client_id = await ws_manager.connect(websocket, rooms=["system", "broadcast"])

    # Subscribe to event bus for real-time forwarding
    async def ws_event_handler(event: Event):
        try:
            await ws_manager.send_to_client(
                client_id,
                WebSocketMessage(WsMessageType.SYSTEM_EVENT, event.to_dict()),
            )
        except Exception:
            pass

    event_bus.subscribe_all(ws_event_handler)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await ws_manager.send_to_client(
                        client_id,
                        WebSocketMessage(WsMessageType.PONG, {"ts": datetime.now(timezone.utc).isoformat()}),
                    )
                elif msg_type == "subscribe":
                    rooms = msg.get("rooms", [])
                    await ws_manager.subscribe(client_id, rooms)
                elif msg_type == "unsubscribe":
                    rooms = msg.get("rooms", [])
                    await ws_manager.unsubscribe(client_id, rooms)
            except json.JSONDecodeError:
                pass
    except Exception:
        logger.info("WebSocket client disconnected")
    finally:
        event_bus.unsubscribe(None, ws_event_handler)
        await ws_manager.disconnect(client_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    return ws_manager.get_stats()


@router.websocket("/ws/agent/{agent_id}")
async def agent_websocket_endpoint(websocket: WebSocket, agent_id: str):
    """Agent-specific WebSocket for chat streaming and task progress."""
    await websocket.accept()

    client_id = await ws_manager.connect(
        websocket,
        rooms=[f"agent:{agent_id}", "system", "broadcast"],
    )
    logger.info(f"Agent WebSocket connected: {client_id} for agent {agent_id}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await ws_manager.send_to_client(
                        client_id,
                        WebSocketMessage(WsMessageType.PONG, {"ts": datetime.now(timezone.utc).isoformat()}),
                    )
                elif msg_type == "chat":
                    # Handled by the existing /ws/chat/{agent_id} endpoint
                    pass
            except json.JSONDecodeError:
                pass
    except Exception:
        logger.info(f"Agent WebSocket disconnected: {client_id}")
    finally:
        await ws_manager.disconnect(client_id)


# ═══════════════════════════════════════════════════════════
# Workspace Project Isolation
# ═══════════════════════════════════════════════════════════

_project_workspaces: dict[str, Any] = {}


def _get_project_workspace(agent_id: str, project_id: str):
    from agent.workspace import AgentWorkspace
    key = f"{agent_id}:{project_id}"
    if key not in _project_workspaces:
        _project_workspaces[key] = AgentWorkspace(agent_id)
    return _project_workspaces[key]


@router.get("/agents/{agent_id}/projects")
async def list_workspace_projects(agent_id: str):
    """List all project workspaces for an agent."""
    projects = []
    seen = set()
    for key in _project_workspaces:
        if key.startswith(f"{agent_id}:"):
            pid = key.split(":", 1)[1]
            if pid not in seen:
                ws = _project_workspaces[key]
                stats = ws.get_stats()
                projects.append({
                    "project_id": pid,
                    "file_count": stats.get("file_count", 0),
                    "total_size": stats.get("total_size", 0),
                    "languages": stats.get("languages", []),
                })
                seen.add(pid)
    if not projects:
        return [{"project_id": "default", "file_count": 0, "total_size": 0, "languages": []}]
    return projects


@router.post("/agents/{agent_id}/projects/{project_id}")
async def create_workspace_project(agent_id: str, project_id: str):
    """Create or initialize a project workspace with memory scoping."""
    ws = _get_project_workspace(agent_id, project_id)
    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "workspace": ws.get_stats(),
    }


@router.get("/agents/{agent_id}/projects/{project_id}/files")
async def list_project_files(agent_id: str, project_id: str, subdir: str = ""):
    ws = _get_project_workspace(agent_id, project_id)
    files = ws.list_files(subdir)
    return [
        {
            "name": f.name, "path": f.path, "language": f.language,
            "size": f.size, "created_at": f.created_at, "updated_at": f.updated_at,
        }
        for f in files
    ]


@router.get("/agents/{agent_id}/projects/{project_id}/files/{path:path}")
async def get_project_file(agent_id: str, project_id: str, path: str):
    ws = _get_project_workspace(agent_id, project_id)
    wf = ws.read_file(path)
    if not wf:
        raise HTTPException(404, "File not found")
    return {
        "name": wf.name, "path": wf.path, "content": wf.content,
        "language": wf.language, "size": wf.size,
        "created_at": wf.created_at, "updated_at": wf.updated_at,
    }


@router.post("/agents/{agent_id}/projects/{project_id}/files", status_code=201)
async def create_project_file(agent_id: str, project_id: str, data: WorkspaceFileCreate):
    ws = _get_project_workspace(agent_id, project_id)
    try:
        wf = ws.create_file(data.name, data.content, data.subdir)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "name": wf.name, "path": wf.path, "content": wf.content,
        "language": wf.language, "size": wf.size,
        "created_at": wf.created_at, "updated_at": wf.updated_at,
    }


@router.delete("/agents/{agent_id}/projects/{project_id}/files/{path:path}", status_code=204)
async def delete_project_file(agent_id: str, project_id: str, path: str):
    ws = _get_project_workspace(agent_id, project_id)
    success = ws.delete_file(path)
    if not success:
        raise HTTPException(404, "File not found")


# ═══════════════════════════════════════════════════════════
# System Health — Comprehensive system-wide health check
# ═══════════════════════════════════════════════════════════

@router.get("/system/health")
async def system_health():
    """Returns comprehensive system health with all subsystem statuses."""
    async with async_session() as session:
        agent_count = (await session.execute(
            select(func.count()).select_from(AgentModel).where(AgentModel.is_active == True)
        )).scalar() or 0
        conv_count = (await session.execute(
            select(func.count()).select_from(ConvModel)
        )).scalar() or 0
        memory_count = (await session.execute(
            select(func.count()).select_from(MemModel)
        )).scalar() or 0

    def _subsystem_status(name: str, obj: Any, method: str = "get_stats") -> str:
        try:
            fn = getattr(obj, method, None)
            if callable(fn):
                fn()
            return "ok"
        except Exception:
            return "degraded"

    return {
        "status": "ok",
        "backend": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "agents": agent_count,
            "conversations": conv_count,
            "memories": memory_count,
        },
        "subsystems": {
            "orchestrator": _subsystem_status("orchestrator", orchestrator, "get_orchestrator_stats"),
            "tool_registry": _subsystem_status("tool_registry", tool_registry, "get_execution_stats"),
            "model_router": _subsystem_status("model_router", model_router, "get_usage_stats"),
            "planning_engine": _subsystem_status("planning_engine", planning_engine, "get_stats"),
            "autopilot_engine": _subsystem_status("autopilot_engine", autopilot_engine, "list_all"),
            "mcp_registry": _subsystem_status("mcp_registry", mcp_registry, "get_server_states"),
            "websocket": _subsystem_status("websocket", ws_manager, "get_stats"),
            "event_bus": _subsystem_status("event_bus", event_bus, "get_stats"),
            "skills_registry": _subsystem_status("skills_registry", skills_registry, "list"),
            "nexus": _subsystem_status("nexus", nexus, "get_summary"),
            "forge": _subsystem_status("forge", forge, "get_stats"),
            "identity": _subsystem_status("identity", identity, "get_stats"),
            "trajectory": _subsystem_status("trajectory", trajectory, "get_stats"),
            "squads": _subsystem_status("squads", squads, "get_stats"),
            "guard": _subsystem_status("guard", guard_system, "get_stats"),
            "pulse": _subsystem_status("pulse", pulse_system, "get_system_health"),
            "cost_tracker": _subsystem_status("cost_tracker", cost_tracker_legacy, "get_system_summary"),
            "self_improvement": _subsystem_status("self_improvement", self_improvement, "get_cycle_history"),
            "gateway": _subsystem_status("gateway", gateway_hub, "get_stats"),
            "daemon": _subsystem_status("daemon", daemon_manager, "get_stats"),
            "swarm": _subsystem_status("swarm", swarm_engine, "get_stats"),
            "compressor": _subsystem_status("compressor", trajectory_compressor, "get_stats"),
            "issue_board": _subsystem_status("issue_board", issue_board, "get_stats"),
            "skill_compounding": _subsystem_status("skill_compounding", skill_compounding, "get_stats"),
            "whitebox_memory": _subsystem_status("whitebox_memory", whitebox_memory, "get_stats"),
        },
    }


# ═══════════════════════════════════════════════════════════
# Memory Export / Import — Cross-agent memory portability
# ═══════════════════════════════════════════════════════════

class MemoryEntry(BaseModel):
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="episodic")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    meta: dict = Field(default_factory=dict)


class MemoryImportPayload(BaseModel):
    memories: list[MemoryEntry] = Field(..., min_length=1)


@router.post("/memory/export/{agent_id}")
async def export_agent_memories(agent_id: str):
    """Export all memories for an agent as downloadable JSON."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        if not result.scalars().first():
            raise HTTPException(404, "Agent not found")

        stmt = (
            select(MemModel)
            .where(MemModel.agent_id == agent_id)
            .order_by(MemModel.created_at)
        )
        mem_result = await session.execute(stmt)
        memories = [
            {
                "id": m.id,
                "content": m.content,
                "memory_type": m.memory_type,
                "importance": m.importance,
                "meta": m.meta or {},
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in mem_result.scalars().all()
        ]

    return {
        "agent_id": agent_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(memories),
        "memories": memories,
    }


@router.post("/memory/import/{agent_id}", status_code=201)
async def import_agent_memories(agent_id: str, data: MemoryImportPayload):
    """Import memories from JSON body for an agent."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        if not result.scalars().first():
            raise HTTPException(404, "Agent not found")

        imported = []
        for entry in data.memories:
            mem = MemModel(
                id=f"mem-{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                content=entry.content,
                memory_type=entry.memory_type,
                importance=entry.importance,
                meta=entry.meta,
            )
            session.add(mem)
            imported.append({
                "id": mem.id,
                "content": mem.content[:100],
                "memory_type": mem.memory_type,
                "importance": mem.importance,
            })
        await session.commit()

    return {
        "agent_id": agent_id,
        "imported_count": len(imported),
        "memories": imported,
    }


# ═══════════════════════════════════════════════════════════
# Agent Summarization — Conversation & memory summary
# ═══════════════════════════════════════════════════════════

@router.post("/agents/{agent_id}/summarize")
async def summarize_agent(agent_id: str, max_tokens: int = Query(default=500, ge=100, le=2000)):
    """Generate a summary of an agent's conversation history and memory."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(404, "Agent not found")

        # Gather recent conversation messages
        msgs_result = await session.execute(
            select(MsgModel)
            .where(MsgModel.agent_id == agent_id)
            .order_by(desc(MsgModel.created_at))
            .limit(50)
        )
        messages = msgs_result.scalars().all()
        conversation_text = "\n".join([
            f"[{m.role}] {m.content[:500]}"
            for m in reversed(messages)
        ]) if messages else "(no conversation history)"

        # Gather memories
        mems_result = await session.execute(
            select(MemModel)
            .where(MemModel.agent_id == agent_id)
            .order_by(desc(MemModel.importance))
            .limit(20)
        )
        memories = mems_result.scalars().all()
        memory_text = "\n".join([
            f"- [{m.memory_type}] {m.content[:300]}"
            for m in memories
        ]) if memories else "(no memories)"

    try:
        response = await orchestrator.chat(
            agent_id=agent.id,
            agent_name=agent.name,
            instructions=(
                f"You are a summarization assistant. Generate a concise, structured summary "
                f"of agent '{agent.name}' ({agent.role}) based on their conversation history "
                f"and memory entries. Highlight key topics, important facts, recurring themes, "
                f"and notable interactions. Limit to approximately {max_tokens} tokens."
            ),
            message=(
                f"# Conversation History\n{conversation_text}\n\n"
                f"# Memory Entries\n{memory_text}"
            ),
            history=None,
            enable_tools=False,
            enable_reasoning=False,
        )
    except Exception as e:
        logger.error(f"Summarization failed for agent {agent_id}: {e}")
        raise HTTPException(500, f"Summarization failed: {str(e)}")

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "agent_role": agent.role,
        "conversations_sampled": len(messages),
        "memories_sampled": len(memories),
        "summary": response,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════
# RAG — Retrieval-Augmented Generation Knowledge Base
# ═══════════════════════════════════════════════════════════

class RAGIngestTextRequest(BaseModel):
    content: str = Field(..., min_length=1)
    title: str = Field(default="")
    source: str = Field(default="direct")
    metadata: dict = Field(default_factory=dict)


@router.post("/agents/{agent_id}/rag/ingest-text", status_code=201)
async def rag_ingest_text(agent_id: str, data: RAGIngestTextRequest):
    """Ingest raw text into the agent's RAG knowledge base."""
    engine = orchestrator.get_engine(agent_id, "", "")
    doc = await engine.rag.ingest_text(
        content=data.content,
        title=data.title,
        source=data.source,
        metadata=data.metadata,
    )
    await engine.rag.generate_embeddings(doc.id)
    return engine.rag.get_document(doc.id)


@router.post("/agents/{agent_id}/rag/ingest-file", status_code=201)
async def rag_ingest_file(agent_id: str, file_path: str = Query(..., description="Absolute path to the file")):
    """Ingest a local file into the agent's RAG knowledge base."""
    engine = orchestrator.get_engine(agent_id, "", "")
    doc = await engine.rag.ingest_file(file_path)
    await engine.rag.generate_embeddings(doc.id)
    return engine.rag.get_document(doc.id)


@router.post("/agents/{agent_id}/rag/ingest-url", status_code=201)
async def rag_ingest_url(agent_id: str, url: str = Query(..., description="URL to ingest")):
    """Ingest content from a URL into the agent's RAG knowledge base."""
    engine = orchestrator.get_engine(agent_id, "", "")
    doc = await engine.rag.ingest_url(url)
    await engine.rag.generate_embeddings(doc.id)
    return engine.rag.get_document(doc.id)


@router.get("/agents/{agent_id}/rag/search")
async def rag_search(
    agent_id: str,
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    hybrid: bool = Query(default=True),
):
    """Semantic search across the agent's RAG knowledge base."""
    engine = orchestrator.get_engine(agent_id, "", "")
    results = await engine.rag.search(query, top_k=top_k, hybrid=hybrid)
    return {"agent_id": agent_id, "query": query, "results": results, "count": len(results)}


@router.get("/agents/{agent_id}/rag/documents")
async def rag_list_documents(agent_id: str):
    """List all documents in the agent's RAG knowledge base."""
    engine = orchestrator.get_engine(agent_id, "", "")
    return {"agent_id": agent_id, "documents": engine.rag.list_documents()}


@router.delete("/agents/{agent_id}/rag/documents/{doc_id}", status_code=204)
async def rag_delete_document(agent_id: str, doc_id: str):
    """Remove a document from the agent's RAG knowledge base."""
    engine = orchestrator.get_engine(agent_id, "", "")
    count = engine.rag.remove_document(doc_id)
    if count == 0:
        raise HTTPException(404, "Document not found")


@router.get("/agents/{agent_id}/rag/stats")
async def rag_stats(agent_id: str):
    """Get RAG knowledge base statistics."""
    engine = orchestrator.get_engine(agent_id, "", "")
    return engine.rag.get_stats()


# ═══════════════════════════════════════════════════════════
# Configuration — System settings & runtime config
# ═══════════════════════════════════════════════════════════

@router.get("/system/config")
async def get_system_config():
    """Get current system configuration (non-sensitive)."""
    return {
        "version": settings.VERSION,
        "host": settings.HOST,
        "port": settings.PORT,
        "max_iterations": settings.MAX_ITERATIONS,
        "max_context_messages": settings.MAX_CONTEXT_MESSAGES,
        "dream_interval": settings.DREAM_INTERVAL,
        "autopilot_enabled": settings.AUTOPILOT_ENABLED,
        "tool_approval_enabled": settings.TOOL_APPROVAL_ENABLED,
        "max_workers": settings.MAX_WORKERS,
        "llm_model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "fallback_models": settings.FALLBACK_MODELS,
    }


# ═══════════════════════════════════════════════════════════
# Swarm — Dynamic Agent Team Formation & Execution
# ═══════════════════════════════════════════════════════════

class FormSwarmRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    goal: str = Field(..., min_length=1)
    min_members: int = Field(default=2, ge=1, le=10)


@router.post("/swarm/form", status_code=201)
async def swarm_form(data: FormSwarmRequest):
    """Form a new agent swarm for collaborative task execution."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.is_active == True)
        )
        agents = result.scalars().all()
        available = [
            {"id": a.id, "name": a.name, "role": a.role}
            for a in agents
        ]

    if len(available) < data.min_members:
        raise HTTPException(400, f"Need at least {data.min_members} active agents, found {len(available)}")

    session = await swarm_engine.form_swarm(
        name=data.name,
        goal=data.goal,
        available_agents=available,
        min_members=data.min_members,
    )

    # Register chat executor for swarm execution
    async def swarm_chat_executor(aid: str, prompt: str, name: str) -> str:
        async with async_session() as db_sess:
            agent_result = await db_sess.execute(
                select(AgentModel).where(AgentModel.id == aid)
            )
            agent = agent_result.scalars().first()
            if not agent:
                return f"Agent {aid} not found"
            response = await orchestrator.chat(
                agent_id=aid,
                agent_name=agent.name,
                instructions=agent.instructions or f"You are {agent.name}, a {agent.role} agent.",
                message=prompt,
                enable_tools=True,
                enable_reasoning=True,
            )
            return response

    swarm_engine.register_chat_executor(session.id, swarm_chat_executor)

    return {
        "session_id": session.id,
        "name": session.name,
        "goal": session.goal,
        "members": [
            {"agent_id": m.agent_id, "agent_name": m.agent_name, "role": m.role.value}
            for m in session.members
        ],
        "status": session.status,
        "created_at": session.created_at,
    }


@router.post("/swarm/{session_id}/plan")
async def swarm_plan(session_id: str):
    """Generate an execution plan for a swarm session."""
    session = swarm_engine.get_session(session_id)
    if not session:
        raise HTTPException(404, "Swarm session not found")

    tasks = await swarm_engine.plan_tasks(session_id)
    return {
        "session_id": session_id,
        "tasks": [
            {
                "id": t.id,
                "description": t.description,
                "required_roles": [r.value for r in t.required_roles],
                "dependencies": t.dependencies,
                "priority": t.priority,
            }
            for t in tasks
        ],
        "count": len(tasks),
    }


@router.post("/swarm/{session_id}/execute")
async def swarm_execute(session_id: str):
    """Execute all tasks in a swarm session."""
    session = swarm_engine.get_session(session_id)
    if not session:
        raise HTTPException(404, "Swarm session not found")

    try:
        completed = await swarm_engine.execute(session_id)
        return {
            "session_id": completed.id,
            "name": completed.name,
            "status": completed.status,
            "task_count": len(completed.tasks),
            "results": [
                {
                    "task_id": r.get("task_id", ""),
                    "result": r.get("result", r.get("content", ""))[:500],
                }
                for r in completed.results
            ],
            "created_at": completed.created_at,
            "completed_at": completed.completed_at,
        }
    except Exception as e:
        logger.error(f"Swarm execution failed: {e}")
        raise HTTPException(500, f"Swarm execution failed: {str(e)}")


@router.get("/swarm/sessions")
async def swarm_list_sessions():
    """List all swarm sessions."""
    return {"sessions": swarm_engine.list_sessions()}


@router.get("/swarm/stats")
async def swarm_stats():
    """Get swarm engine statistics."""
    return swarm_engine.get_stats()


@router.get("/swarm/{session_id}")
async def swarm_session(session_id: str):
    """Get a swarm session's status and results."""
    session = swarm_engine.get_session(session_id)
    if not session:
        raise HTTPException(404, "Swarm session not found")

    return {
        "session_id": session.id,
        "name": session.name,
        "goal": session.goal,
        "status": session.status,
        "members": [
            {
                "agent_id": m.agent_id,
                "agent_name": m.agent_name,
                "role": m.role.value,
                "status": m.status,
            }
            for m in session.members
        ],
        "tasks": [
            {
                "id": t.id,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
            }
            for t in session.tasks
        ],
        "results": [
            {
                "task_id": r.get("task_id", ""),
                "result": r.get("result", r.get("content", ""))[:500],
            }
            for r in session.results
        ],
        "created_at": session.created_at,
        "completed_at": session.completed_at,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Runtime Hub — Universal Execution Environment Management
# ═══════════════════════════════════════════════════════════════════════════

from agent.shared import runtime_hub, RtStatus as RuntimeHubStatus


class CreateRuntimeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    backend: str = Field(default="local")
    workspace_dir: str = Field(default="")
    image: str = Field(default="")
    tags: list[str] = Field(default_factory=list)


class ExecuteRequest(BaseModel):
    runtime_id: str = Field(..., min_length=1)
    command: str = Field(default="")
    code: str = Field(default="")
    language: str = Field(default="python")
    timeout_sec: int = Field(default=300, ge=1, le=3600)


@router.post("/runtimes", status_code=201)
async def create_runtime(data: CreateRuntimeRequest):
    """Create and register a new execution runtime."""
    from agent.runtime_hub import RuntimeBackend
    backend = RuntimeBackend(data.backend)
    rt = runtime_hub.create_runtime(
        name=data.name,
        backend=backend,
        workspace_dir=data.workspace_dir,
        image=data.image,
        tags=data.tags,
    )
    return rt.to_dict()


@router.get("/runtimes")
async def list_runtimes():
    """List all registered runtimes."""
    return {"runtimes": runtime_hub.list_runtimes()}


@router.get("/runtimes/{runtime_id}")
async def get_runtime(runtime_id: str):
    """Get runtime details."""
    rt = runtime_hub.get_runtime(runtime_id)
    if not rt:
        raise HTTPException(404, "Runtime not found")
    return rt.to_dict()


@router.delete("/runtimes/{runtime_id}")
async def delete_runtime(runtime_id: str):
    """Remove a runtime."""
    if not runtime_hub.destroy_runtime(runtime_id):
        raise HTTPException(404, "Runtime not found")
    return {"success": True}


@router.post("/runtimes/execute")
async def execute_in_runtime(data: ExecuteRequest):
    """Execute a command or code in a runtime."""
    from agent.runtime_hub import ExecutionRequest as ExecReq
    request = ExecReq(
        runtime_id=data.runtime_id,
        command=data.command,
        code=data.code,
        language=data.language,
        timeout_sec=data.timeout_sec,
    )
    result = await runtime_hub.execute(request)
    return {
        "execution_id": result.execution_id,
        "exit_code": result.exit_code,
        "success": result.success,
        "stdout": result.stdout[:2000],
        "stderr": result.stderr[:1000],
        "duration_ms": result.duration_ms,
        "error_message": result.error_message,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }


@router.get("/runtimes/{runtime_id}/history")
async def runtime_execution_history(runtime_id: str):
    """Get execution history for a runtime."""
    return {"history": runtime_hub.get_execution_history(runtime_id)}


@router.post("/runtimes/discover")
async def discover_runtimes():
    """Auto-discover available runtimes on the host."""
    runtimes = await runtime_hub.auto_discover()
    return {"discovered": [rt.to_dict() for rt in runtimes]}


@router.get("/runtimes-stats")
async def runtime_hub_stats():
    """Get runtime hub statistics."""
    return runtime_hub.get_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Scheduler — Cron-based Task Scheduling
# ═══════════════════════════════════════════════════════════════════════════

from agent.shared import buddy_scheduler


class CreateScheduleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    prompt: str = Field(..., min_length=1)
    agent_id: str = Field(default="")
    description: str = Field(default="")
    cron_expression: str = Field(default="")
    interval_seconds: int = Field(default=3600, ge=10)
    schedule_type: str = Field(default="")
    natural_schedule: str = Field(default="")
    tags: list[str] = Field(default_factory=list)


@router.post("/schedules", status_code=201)
async def create_schedule(data: CreateScheduleRequest):
    """Create a new scheduled task."""
    from agent.scheduler import ScheduleType, DeliveryPlatform

    if data.natural_schedule:
        task = buddy_scheduler.schedule_natural(
            name=data.name,
            prompt=data.prompt,
            natural_schedule=data.natural_schedule,
            agent_id=data.agent_id,
            description=data.description,
            tags=data.tags,
        )
    else:
        sched_type = ScheduleType(data.schedule_type) if data.schedule_type else None
        task = buddy_scheduler.schedule(
            name=data.name,
            prompt=data.prompt,
            agent_id=data.agent_id,
            description=data.description,
            cron_expression=data.cron_expression,
            interval_seconds=data.interval_seconds,
            schedule_type=sched_type,
            tags=data.tags,
        )

    return task.to_dict()


@router.get("/schedules")
async def list_schedules():
    """List all scheduled tasks."""
    return {"schedules": buddy_scheduler.list_tasks()}


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: str):
    """Get a scheduled task."""
    task = buddy_scheduler.get_task(schedule_id)
    if not task:
        raise HTTPException(404, "Schedule not found")
    return task.to_dict()


@router.get("/schedules/{schedule_id}/history")
async def schedule_history(schedule_id: str):
    """Get execution history for a scheduled task."""
    return {"history": buddy_scheduler.get_history(schedule_id)}


@router.post("/schedules/{schedule_id}/pause")
async def pause_schedule(schedule_id: str):
    """Pause a scheduled task."""
    if not buddy_scheduler.pause_task(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"success": True}


@router.post("/schedules/{schedule_id}/resume")
async def resume_schedule(schedule_id: str):
    """Resume a paused scheduled task."""
    if not buddy_scheduler.resume_task(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"success": True}


@router.delete("/schedules/{schedule_id}")
async def cancel_schedule(schedule_id: str):
    """Cancel a scheduled task."""
    if not buddy_scheduler.cancel_task(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"success": True}


@router.post("/schedules/parse")
async def parse_natural_schedule(text: str = Query(..., min_length=1)):
    """Parse a natural language schedule description."""
    from agent.scheduler import NaturalScheduleParser
    sched_type, cron_expr, interval = NaturalScheduleParser.parse(text)
    return {
        "text": text,
        "schedule_type": sched_type.value,
        "cron_expression": cron_expr,
        "interval_seconds": interval,
    }


@router.get("/schedules-stats")
async def scheduler_stats():
    """Get scheduler statistics."""
    return buddy_scheduler.get_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Studio — Project Workspace System with White-Box Memory
# ═══════════════════════════════════════════════════════════════════════════

from agent.shared import buddy_studio


class CreateStudioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="")
    template_id: str = Field(default="")
    icon: str = Field(default="📁")
    tags: list[str] = Field(default_factory=list)


class MemoryEntryCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=256)
    value: str = Field(..., min_length=1)
    category: str = Field(default="fact")
    importance: str = Field(default="medium")
    source: str = Field(default="user")
    tags: list[str] = Field(default_factory=list)
    context: str = Field(default="")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class MemoryEntryUpdate(BaseModel):
    value: str | None = Field(default=None)
    category: str | None = Field(default=None)
    importance: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    is_pinned: bool | None = Field(default=None)


@router.get("/studios")
async def list_studios():
    """List all studio workspaces."""
    return {
        "studios": buddy_studio.list_studios(),
        "templates": buddy_studio.list_templates(),
    }


@router.post("/studios", status_code=201)
async def create_studio(data: CreateStudioRequest):
    """Create a new studio workspace."""
    studio = buddy_studio.create_studio(
        name=data.name,
        description=data.description,
        template_id=data.template_id,
        icon=data.icon,
        tags=data.tags,
    )
    return studio.to_dict()


@router.get("/studios/{studio_id}")
async def get_studio(studio_id: str):
    """Get studio details."""
    studio = buddy_studio.get_studio(studio_id)
    if not studio:
        raise HTTPException(404, "Studio not found")
    return studio.to_dict()


@router.get("/studios/{studio_id}/analyze")
async def analyze_studio(studio_id: str):
    """Get comprehensive studio analytics."""
    result = buddy_studio.analyze_studio(studio_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.delete("/studios/{studio_id}")
async def delete_studio(studio_id: str):
    """Destroy a studio workspace."""
    if not buddy_studio.registry.destroy_studio(studio_id):
        raise HTTPException(404, "Studio not found")
    return {"success": True}


# ── White-Box Memory ──

@router.get("/studios/{studio_id}/memory")
async def list_memory_entries(
    studio_id: str,
    category: str = Query(default=""),
    importance: str = Query(default=""),
    search: str = Query(default=""),
    include_archived: bool = Query(default=False),
):
    """List memory entries in a studio."""
    memory = buddy_studio.get_memory(studio_id)
    if not memory:
        raise HTTPException(404, "Studio not found")

    if search:
        entries = memory.search(search)
    elif category:
        entries = memory.list_by_category(MemoryCategory(category))
    elif importance:
        entries = memory.list_by_importance(MemoryImportance(importance))
    else:
        entries = memory.list_all(include_archived=include_archived)

    return {
        "entries": [
            {
                "id": e.id,
                "key": e.key,
                "value": e.value,
                "category": e.category.value,
                "importance": e.importance.value,
                "source": e.source,
                "tags": e.tags,
                "confidence": e.confidence,
                "version": e.version,
                "is_pinned": e.is_pinned,
                "created_at": e.created_at,
                "updated_at": e.updated_at,
            }
            for e in entries
        ],
        "stats": memory.get_stats(),
    }


@router.post("/studios/{studio_id}/memory", status_code=201)
async def create_memory_entry(studio_id: str, data: MemoryEntryCreate):
    """Add a new memory entry to a studio."""
    memory = buddy_studio.get_memory(studio_id)
    if not memory:
        raise HTTPException(404, "Studio not found")

    entry = MemoryEntry(
        studio_id=studio_id,
        key=data.key,
        value=data.value,
        category=MemoryCategory(data.category),
        importance=MemoryImportance(data.importance),
        source=data.source,
        tags=data.tags,
        context=data.context,
        confidence=data.confidence,
    )
    memory.add(entry)
    return {
        "id": entry.id,
        "key": entry.key,
        "value": entry.value,
        "category": entry.category.value,
        "importance": entry.importance.value,
        "created_at": entry.created_at,
    }


@router.put("/studios/{studio_id}/memory/{entry_id}")
async def update_memory_entry(studio_id: str, entry_id: str, data: MemoryEntryUpdate):
    """Update a memory entry (white-box editing)."""
    memory = buddy_studio.get_memory(studio_id)
    if not memory:
        raise HTTPException(404, "Studio not found")

    updates = {}
    if data.value is not None:
        updates["value"] = data.value
    if data.category is not None:
        updates["category"] = MemoryCategory(data.category)
    if data.importance is not None:
        updates["importance"] = MemoryImportance(data.importance)
    if data.tags is not None:
        updates["tags"] = data.tags
    if data.is_pinned is not None:
        updates["is_pinned"] = data.is_pinned

    updated = memory.update(entry_id, **updates)
    if not updated:
        raise HTTPException(404, "Memory entry not found")
    return {"success": True, "version": updated.version}


@router.delete("/studios/{studio_id}/memory/{entry_id}")
async def delete_memory_entry(studio_id: str, entry_id: str):
    """Delete a memory entry."""
    memory = buddy_studio.get_memory(studio_id)
    if not memory:
        raise HTTPException(404, "Studio not found")
    if not memory.delete(entry_id):
        raise HTTPException(404, "Memory entry not found")
    return {"success": True}


@router.post("/studios/{studio_id}/memory/{entry_id}/pin")
async def pin_memory_entry(studio_id: str, entry_id: str):
    """Pin a memory entry."""
    memory = buddy_studio.get_memory(studio_id)
    if not memory:
        raise HTTPException(404, "Studio not found")
    if not memory.pin(entry_id):
        raise HTTPException(404, "Memory entry not found")
    return {"success": True}


# ── Memory Snapshots ──

@router.post("/studios/{studio_id}/snapshots", status_code=201)
async def create_snapshot(
    studio_id: str,
    label: str = Query(default=""),
    description: str = Query(default=""),
):
    """Create a memory snapshot for rollback."""
    memory = buddy_studio.get_memory(studio_id)
    if not memory:
        raise HTTPException(404, "Studio not found")

    snap = buddy_studio.snapshotter.create_snapshot(
        memory,
        label=label or f"Snapshot {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        description=description,
    )
    return {
        "snapshot_id": snap.id,
        "label": snap.label,
        "entry_count": snap.entry_count,
        "created_at": snap.created_at,
    }


@router.post("/studios/{studio_id}/snapshots/rollback")
async def rollback_snapshot(studio_id: str, snapshot_id: str = Query(...)):
    """Roll back memory to a previous snapshot."""
    memory = buddy_studio.get_memory(studio_id)
    if not memory:
        raise HTTPException(404, "Studio not found")
    if not buddy_studio.snapshotter.rollback(memory, snapshot_id):
        raise HTTPException(404, "Snapshot not found")
    return {"success": True, "entry_count": len(memory._entries)}


@router.get("/studios/{studio_id}/snapshots")
async def list_snapshots(studio_id: str):
    """List all memory snapshots for a studio."""
    snaps = buddy_studio.snapshotter._snapshots.get(studio_id, [])
    return {
        "snapshots": [
            {
                "id": s.id,
                "label": s.label,
                "description": s.description,
                "entry_count": s.entry_count,
                "created_at": s.created_at,
                "is_auto": s.is_auto,
            }
            for s in snaps
        ]
    }


@router.get("/studios-stats")
async def studio_stats():
    """Get studio workspace statistics."""
    return buddy_studio.get_stats()


# ═══════════════════════════════════════════════════════════════════════════
# Workflow — Agentic Task Lifecycle Management
# ═══════════════════════════════════════════════════════════════════════════

from agent.shared import workflow_engine


class CreateWorkflowTaskRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="")
    priority: str = Field(default="medium")
    assigned_agent: str = Field(default="")
    created_by: str = Field(default="")
    dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    studio_id: str = Field(default="")


class ReportBlockerRequest(BaseModel):
    blocker_type: str = Field(default="dependency")
    description: str = Field(..., min_length=1)
    reported_by: str = Field(default="")


class TransitionRequest(BaseModel):
    state: str = Field(..., min_length=1)
    actor: str = Field(default="")


@router.post("/workflow/tasks", status_code=201)
async def create_workflow_task(data: CreateWorkflowTaskRequest):
    """Create a new workflow task."""
    task = workflow_engine.board.create_task(
        title=data.title,
        description=data.description,
        priority=WorkflowPriority(data.priority),
        assigned_agent=data.assigned_agent,
        created_by=data.created_by,
        dependencies=data.dependencies,
        tags=data.tags,
        studio_id=data.studio_id,
    )
    return task.to_dict()


@router.get("/workflow/tasks")
async def list_workflow_tasks(
    state: str = Query(default=""),
    agent_id: str = Query(default=""),
):
    """List workflow tasks, optionally filtered."""
    task_state = TaskState(state) if state else None
    tasks = workflow_engine.board.list_tasks(state=task_state, agent_id=agent_id)
    return {"tasks": [t.to_dict() for t in tasks]}


@router.get("/workflow/tasks/{task_id}")
async def get_workflow_task(task_id: str):
    """Get a workflow task with full timeline."""
    task = workflow_engine.board.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return {
        "task": task.to_dict(),
        "timeline": workflow_engine.board.get_timeline(task_id),
    }


@router.post("/workflow/tasks/{task_id}/transition")
async def transition_task(task_id: str, data: TransitionRequest):
    """Transition a task to a new state."""
    if not workflow_engine.board.transition(task_id, TaskState(data.state), data.actor):
        raise HTTPException(400, "Invalid state transition")
    return {"success": True, "state": data.state}


@router.post("/workflow/tasks/{task_id}/assign")
async def assign_task(
    task_id: str,
    agent_id: str = Query(..., min_length=1),
    actor: str = Query(default=""),
):
    """Assign a task to an agent."""
    if not workflow_engine.board.assign(task_id, agent_id, actor):
        raise HTTPException(404, "Task not found")
    return {"success": True, "assigned_agent": agent_id}


@router.post("/workflow/tasks/{task_id}/delegate")
async def delegate_task(
    task_id: str,
    from_agent: str = Query(..., min_length=1),
    to_agent: str = Query(..., min_length=1),
):
    """Delegate a task from one agent to another."""
    if not workflow_engine.board.delegate(task_id, from_agent, to_agent):
        raise HTTPException(400, "Delegation failed")
    return {"success": True, "assigned_agent": to_agent}


@router.post("/workflow/tasks/{task_id}/blockers", status_code=201)
async def report_blocker(task_id: str, data: ReportBlockerRequest):
    """Report a blocker on a task."""
    blocker = workflow_engine.board.report_blocker(
        task_id,
        BlockerType(data.blocker_type),
        data.description,
        data.reported_by,
    )
    if not blocker:
        raise HTTPException(404, "Task not found")
    return {
        "blocker_id": blocker.id,
        "type": blocker.type.value,
        "description": blocker.description,
        "created_at": blocker.created_at,
    }


@router.post("/workflow/tasks/{task_id}/blockers/{blocker_id}/resolve")
async def resolve_blocker(
    task_id: str,
    blocker_id: str,
    resolution: str = Query(default="Resolved"),
):
    """Resolve a blocker on a task."""
    if not workflow_engine.board.resolve_blocker(task_id, blocker_id, resolution):
        raise HTTPException(404, "Task or blocker not found")
    return {"success": True}


@router.get("/workflow/tasks/{task_id}/can-start")
async def can_start_task(task_id: str):
    """Check if a task's dependencies are met."""
    can_start, unmet = workflow_engine.board.can_start(task_id)
    if can_start is False and not unmet:
        raise HTTPException(404, "Task not found")
    return {"can_start": can_start, "unmet_dependencies": unmet}


@router.get("/workflow/recent")
async def workflow_recent_activity(limit: int = Query(default=20)):
    """Get recent activity across all tasks."""
    return {"activity": workflow_engine.board.get_recent_activity(limit)}


@router.get("/workflow-stats")
async def workflow_stats():
    """Get workflow board statistics."""
    return workflow_engine.get_stats()


# ═══════════════════════════════════════════════════════════
# Issue Board — Kanban Task Management
# ═══════════════════════════════════════════════════════════

from agent.issue_board import issue_board, IssueState, IssuePriority


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", max_length=4096)
    priority: str = Field(default="medium")
    tags: list[str] = Field(default_factory=list)
    workspace_id: str = Field(default="")
    context: dict = Field(default_factory=dict)
    auto_assign: bool = Field(default=True)


class IssueUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    tags: list[str] | None = None
    assigned_agent: str | None = None
    workspace_id: str | None = None


class AutopilotRuleCreate(BaseModel):
    name: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    filters: dict = Field(default_factory=dict)
    max_concurrent: int = Field(default=3, ge=1, le=10)


@router.get("/board")
async def get_board():
    """Get the full Kanban board state."""
    return issue_board.get_board()


@router.get("/board/stats")
async def get_board_stats():
    """Get board statistics."""
    return issue_board.get_stats()


@router.post("/board/issues")
async def create_board_issue(data: IssueCreate):
    """Create a new issue on the board."""
    try:
        priority = IssuePriority(data.priority)
    except ValueError:
        raise HTTPException(400, f"Invalid priority. Valid: {[p.value for p in IssuePriority]}")
    issue = issue_board.create_issue(
        title=data.title,
        description=data.description,
        priority=priority,
        tags=data.tags,
        workspace_id=data.workspace_id,
        context=data.context,
        auto_assign=data.auto_assign,
    )
    return issue.to_dict()


@router.get("/board/issues")
async def list_board_issues(
    state: str | None = None,
    agent_id: str | None = None,
    workspace_id: str | None = None,
    priority: str | None = None,
):
    """List issues with optional filtering."""
    issue_state = IssueState(state) if state else None
    issue_priority = IssuePriority(priority) if priority else None
    issues = issue_board.list_issues(
        state=issue_state,
        agent_id=agent_id,
        workspace_id=workspace_id,
        priority=issue_priority,
    )
    return {"issues": [i.to_dict() for i in issues], "count": len(issues)}


@router.get("/board/issues/{issue_id}")
async def get_board_issue(issue_id: str):
    """Get a single issue by ID."""
    issue = issue_board.get_issue(issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found")
    return issue.to_dict()


@router.patch("/board/issues/{issue_id}")
async def update_board_issue(issue_id: str, data: IssueUpdate):
    """Update issue fields."""
    kwargs = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if "priority" in kwargs:
        try:
            kwargs["priority"] = IssuePriority(kwargs["priority"])
        except ValueError:
            raise HTTPException(400, "Invalid priority")
    issue = issue_board.update_issue(issue_id, **kwargs)
    if not issue:
        raise HTTPException(404, "Issue not found")
    return issue.to_dict()


@router.delete("/board/issues/{issue_id}")
async def delete_board_issue(issue_id: str):
    """Delete an issue."""
    if not issue_board.delete_issue(issue_id):
        raise HTTPException(404, "Issue not found")
    return {"deleted": True}


@router.post("/board/issues/{issue_id}/move")
async def move_board_issue(issue_id: str, state: str = Query(..., min_length=1)):
    """Move an issue to a new column."""
    try:
        new_state = IssueState(state)
    except ValueError:
        raise HTTPException(400, f"Invalid state. Valid: {[s.value for s in IssueState]}")
    if not issue_board.move_issue(issue_id, new_state):
        raise HTTPException(400, "Invalid state transition")
    issue = issue_board.get_issue(issue_id)
    return issue.to_dict() if issue else {}


@router.post("/board/issues/{issue_id}/assign")
async def assign_board_issue(issue_id: str, agent_id: str = Query(..., min_length=1)):
    """Assign an issue to an agent."""
    if not issue_board.assign_issue(issue_id, agent_id):
        raise HTTPException(404, "Issue not found")
    issue = issue_board.get_issue(issue_id)
    return issue.to_dict() if issue else {}


@router.post("/board/issues/{issue_id}/claim")
async def claim_board_issue(issue_id: str, agent_id: str = Query(..., min_length=1)):
    """Agent claims an issue."""
    if not issue_board.claim_issue(issue_id, agent_id):
        raise HTTPException(400, "Cannot claim issue")
    issue = issue_board.get_issue(issue_id)
    return issue.to_dict() if issue else {}


@router.post("/board/issues/{issue_id}/complete")
async def complete_board_issue(issue_id: str, result: dict | None = None):
    """Mark an issue as completed."""
    if not issue_board.complete_issue(issue_id, result):
        raise HTTPException(400, "Cannot complete issue")
    issue = issue_board.get_issue(issue_id)
    return issue.to_dict() if issue else {}


@router.post("/board/issues/{issue_id}/fail")
async def fail_board_issue(issue_id: str, error: str = Query(default="")):
    """Mark an issue as failed."""
    if not issue_board.fail_issue(issue_id, error):
        raise HTTPException(400, "Cannot fail issue")
    issue = issue_board.get_issue(issue_id)
    return issue.to_dict() if issue else {}


@router.get("/board/autopilot")
async def list_autopilot_rules():
    """List autopilot rules."""
    return {"rules": issue_board.list_autopilot_rules()}


@router.post("/board/autopilot")
async def create_autopilot_rule(data: AutopilotRuleCreate):
    """Create an autopilot rule."""
    rule = issue_board.add_autopilot_rule(
        name=data.name,
        agent_id=data.agent_id,
        filters=data.filters,
        max_concurrent=data.max_concurrent,
    )
    return rule.to_dict()


@router.delete("/board/autopilot/{rule_id}")
async def delete_autopilot_rule(rule_id: str):
    """Remove an autopilot rule."""
    if not issue_board.remove_autopilot_rule(rule_id):
        raise HTTPException(404, "Rule not found")
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════
# Skill Compounding — Self-Improving Skill System
# ═══════════════════════════════════════════════════════════

from agent.skill_compounding import skill_compounding, CompoundedSkill


class CompoundingInteraction(BaseModel):
    agent_id: str = Field(..., min_length=1)
    task_description: str = Field(default="")
    tool_calls: list[dict] = Field(default_factory=list)
    success: bool = Field(default=True)
    output_summary: str = Field(default="")
    metadata: dict = Field(default_factory=dict)


@router.get("/compounding/stats")
async def get_compounding_stats():
    """Get skill compounding engine statistics."""
    return skill_compounding.get_stats()


@router.get("/compounding/skills")
async def list_compounded_skills(
    category: str | None = None,
    min_quality: float = Query(default=0.0, ge=0.0, le=1.0),
):
    """List compounded skills."""
    skills = skill_compounding.list_skills(category=category, min_quality=min_quality)
    return {"skills": [s.to_dict() for s in skills], "count": len(skills)}


@router.get("/compounding/skills/{skill_id}")
async def get_compounded_skill(skill_id: str):
    """Get a single compounded skill."""
    skill = skill_compounding.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    return skill.to_dict()


@router.post("/compounding/skills/{skill_id}/feedback")
async def skill_feedback(
    skill_id: str,
    success: bool = Query(default=True),
    feedback: str = Query(default=""),
):
    """Update skill quality based on usage feedback."""
    skill_compounding.update_skill_quality(skill_id, success, feedback)
    skill = skill_compounding.get_skill(skill_id)
    return skill.to_dict() if skill else {}


@router.post("/compounding/skills/{skill_id}/deprecate")
async def deprecate_skill(skill_id: str):
    """Deprecate a skill."""
    if not skill_compounding.deprecate_skill(skill_id):
        raise HTTPException(404, "Skill not found")
    return {"deprecated": True}


@router.delete("/compounding/skills/{skill_id}")
async def delete_compounded_skill(skill_id: str):
    """Delete a skill."""
    if not skill_compounding.delete_skill(skill_id):
        raise HTTPException(404, "Skill not found")
    return {"deleted": True}


@router.post("/compounding/interactions")
async def record_compounding_interaction(data: CompoundingInteraction):
    """Record an agent interaction for pattern analysis."""
    interaction_id = skill_compounding.record_interaction(
        agent_id=data.agent_id,
        task_description=data.task_description,
        tool_calls=data.tool_calls,
        success=data.success,
        output_summary=data.output_summary,
        metadata=data.metadata,
    )
    return {"interaction_id": interaction_id}


@router.post("/compounding/generate")
async def generate_skills():
    """Generate skills from all qualified patterns."""
    new_skills = skill_compounding.generate_all_skills()
    return {"skills": [s.to_dict() for s in new_skills], "count": len(new_skills)}


@router.get("/compounding/patterns")
async def get_compounding_patterns():
    """Get detected interaction patterns."""
    return {"patterns": skill_compounding.get_patterns()}


@router.post("/compounding/search")
async def search_skills_for_task(
    task_description: str = Query(..., min_length=1),
    required_tools: str | None = None,
    limit: int = Query(default=5, ge=1, le=20),
):
    """Find relevant skills for a task."""
    tools_list = required_tools.split(",") if required_tools else None
    skills = skill_compounding.find_skills_for_task(
        task_description=task_description,
        required_tools=tools_list,
        limit=limit,
    )
    return {"skills": [s.to_dict() for s in skills], "count": len(skills)}


@router.get("/compounding/export")
async def export_skills(format: str = Query(default="json")):
    """Export all skills."""
    data = skill_compounding.export_skills(format)
    return {"format": format, "data": data}


@router.post("/compounding/import")
async def import_skills(data: str = Query(..., min_length=1), format: str = Query(default="json")):
    """Import skills from serialized data."""
    count = skill_compounding.import_skills(data, format)
    return {"imported": count}


# ═══════════════════════════════════════════════════════════
# White-box Memory — Transparent Memory Management
# ═══════════════════════════════════════════════════════════

from agent.whitebox_memory import whitebox_memory, MemoryType, MemoryImportance


class WhiteboxMemoryCreate(BaseModel):
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="episodic")
    importance: str = Field(default="medium")
    workspace_id: str = Field(default="")
    session_id: str = Field(default="")
    agent_id: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="api")
    source_detail: dict = Field(default_factory=dict)
    summary: str = Field(default="")
    expires_in_hours: int | None = None


class WhiteboxMemoryUpdate(BaseModel):
    content: str | None = None
    importance: str | None = None
    memory_type: str | None = None
    summary: str | None = None


@router.get("/whitebox-memory/stats")
async def get_whitebox_memory_stats():
    """Get white-box memory statistics."""
    return whitebox_memory.get_stats()


@router.get("/whitebox-memory/entries")
async def list_whitebox_memories(
    workspace_id: str | None = None,
    agent_id: str | None = None,
    memory_type: str | None = None,
    importance: str | None = None,
    tags: str | None = None,
    pinned_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List memory entries with filtering."""
    try:
        mtype = MemoryType(memory_type) if memory_type else None
    except ValueError:
        mtype = None
    try:
        mimportance = MemoryImportance(importance) if importance else None
    except ValueError:
        mimportance = None

    tag_list = tags.split(",") if tags else None
    entries = whitebox_memory.list_memories(
        workspace_id=workspace_id,
        agent_id=agent_id,
        memory_type=mtype,
        importance=mimportance,
        tags=tag_list,
        pinned_only=pinned_only,
        limit=limit,
        offset=offset,
    )
    return {
        "entries": [e.to_dict() for e in entries],
        "count": len(entries),
        "total": whitebox_memory.get_stats()["total"],
    }


@router.post("/whitebox-memory/entries")
async def create_whitebox_memory(data: WhiteboxMemoryCreate):
    """Store a new memory entry."""
    try:
        mtype = MemoryType(data.memory_type)
    except ValueError:
        raise HTTPException(400, f"Invalid memory type. Valid: {[t.value for t in MemoryType]}")
    try:
        mimportance = MemoryImportance(data.importance)
    except ValueError:
        raise HTTPException(400, f"Invalid importance. Valid: {[i.value for i in MemoryImportance]}")

    entry = whitebox_memory.store(
        content=data.content,
        memory_type=mtype,
        importance=mimportance,
        workspace_id=data.workspace_id,
        session_id=data.session_id,
        agent_id=data.agent_id,
        tags=data.tags,
        source=data.source,
        source_detail=data.source_detail,
        summary=data.summary,
        expires_in_hours=data.expires_in_hours,
    )
    return entry.to_dict()


@router.get("/whitebox-memory/entries/{memory_id}")
async def get_whitebox_memory_entry(memory_id: str):
    """Get a single memory entry."""
    entry = whitebox_memory.get(memory_id)
    if not entry:
        raise HTTPException(404, "Memory entry not found")
    return entry.to_dict()


@router.patch("/whitebox-memory/entries/{memory_id}")
async def update_whitebox_memory_entry(memory_id: str, data: WhiteboxMemoryUpdate):
    """Update a memory entry."""
    kwargs = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    entry = whitebox_memory.update(memory_id, **kwargs)
    if not entry:
        raise HTTPException(404, "Memory entry not found")
    return entry.to_dict()


@router.put("/whitebox-memory/entries/{memory_id}/edit")
async def edit_whitebox_memory_content(
    memory_id: str,
    new_content: str = Query(..., min_length=1),
    edited_by: str = Query(default="user"),
):
    """Edit memory content with audit trail."""
    if not whitebox_memory.edit_content(memory_id, new_content, edited_by):
        raise HTTPException(404, "Memory entry not found")
    entry = whitebox_memory.get(memory_id)
    return entry.to_dict() if entry else {}


@router.delete("/whitebox-memory/entries/{memory_id}")
async def delete_whitebox_memory_entry(memory_id: str):
    """Delete a memory entry."""
    if not whitebox_memory.delete(memory_id):
        raise HTTPException(404, "Memory entry not found")
    return {"deleted": True}


@router.post("/whitebox-memory/entries/{memory_id}/pin")
async def pin_whitebox_memory_entry(memory_id: str):
    """Pin a memory entry."""
    if not whitebox_memory.pin(memory_id):
        raise HTTPException(404, "Memory entry not found")
    return {"pinned": True}


@router.post("/whitebox-memory/entries/{memory_id}/unpin")
async def unpin_whitebox_memory_entry(memory_id: str):
    """Unpin a memory entry."""
    if not whitebox_memory.unpin(memory_id):
        raise HTTPException(404, "Memory entry not found")
    return {"unpinned": True}


@router.get("/whitebox-memory/search")
async def search_whitebox_memories(
    query: str = Query(..., min_length=1),
    workspace_id: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
):
    """Search memories by keyword."""
    results = whitebox_memory.search(query=query, workspace_id=workspace_id, limit=limit)
    return {"results": results, "count": len(results), "query": query}


@router.get("/whitebox-memory/entries/{memory_id}/audit")
async def get_memory_audit_trail(memory_id: str):
    """Get the full edit history for a memory entry."""
    trail = whitebox_memory.get_audit_trail(memory_id)
    if not trail:
        raise HTTPException(404, "Memory entry not found")
    return {"audit_trail": trail}


@router.post("/whitebox-memory/dream")
async def run_dream_mode(workspace_id: str | None = None):
    """Run Dream Mode memory consolidation."""
    result = whitebox_memory.dream_consolidate(workspace_id)
    return result


@router.post("/whitebox-memory/dream/rollback")
async def rollback_dream_mode(dream_id: str | None = None):
    """Rollback the last Dream Mode consolidation."""
    result = whitebox_memory.rollback_dream(dream_id or "")
    return result


@router.get("/whitebox-memory/export")
async def export_whitebox_memories(
    workspace_id: str | None = None,
    format: str = Query(default="json"),
):
    """Export memories for backup or transfer."""
    data = whitebox_memory.export_memories(workspace_id, format)
    return {"format": format, "data": data}


@router.post("/whitebox-memory/import")
async def import_whitebox_memories(
    data: str = Query(..., min_length=1),
    format: str = Query(default="json"),
):
    """Import memories from serialized data."""
    count = whitebox_memory.import_memories(data, format)
    return {"imported": count}


# ═══════════════════════════════════════════════════════════
# Pipeline Engine — Composable Agent Execution Pipelines
# ═══════════════════════════════════════════════════════════

from agent.pipeline import pipeline_engine, StepKind, ErrorPolicy


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="")
    steps: list[dict] = Field(..., min_length=1)


class PipelineExecute(BaseModel):
    pipeline_id: str = Field(..., min_length=1)
    initial_state: dict = Field(default_factory=dict)


@router.get("/pipelines")
async def list_pipelines():
    """List all defined pipelines."""
    return {"pipelines": pipeline_engine.list_pipelines()}


@router.post("/pipelines", status_code=201)
async def create_pipeline(data: PipelineCreate):
    """Define a new pipeline."""
    from agent.pipeline import PipelineDefinition, StepConfig
    steps = []
    for s in data.steps:
        steps.append(StepConfig(
            kind=StepKind(s.get("kind", "chat")),
            name=s.get("name", f"step_{len(steps)}"),
            config=s.get("config", {}),
            depends_on=s.get("depends_on", []),
            error_policy=ErrorPolicy(s.get("error_policy", "abort")),
            max_retries=s.get("max_retries", 2),
            timeout_seconds=s.get("timeout_seconds", 120.0),
            condition=s.get("condition", ""),
            fallback_step=s.get("fallback_step", ""),
        ))
    definition = PipelineDefinition(
        id=f"pipeline-{uuid.uuid4().hex[:12]}",
        name=data.name,
        description=data.description,
        steps=steps,
    )
    pipeline_id = pipeline_engine.define_pipeline(definition)
    return {"pipeline_id": pipeline_id, "name": data.name, "step_count": len(steps)}


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get pipeline definition."""
    pipeline = pipeline_engine.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "description": pipeline.description,
        "steps": [
            {"name": s.name, "kind": s.kind.value, "config": s.config,
             "depends_on": s.depends_on, "error_policy": s.error_policy.value}
            for s in pipeline.steps
        ],
        "created_at": pipeline.created_at,
    }


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """Delete a pipeline definition."""
    if not pipeline_engine.delete_pipeline(pipeline_id):
        raise HTTPException(404, "Pipeline not found")
    return {"deleted": True}


@router.post("/pipelines/run")
async def run_pipeline(data: PipelineExecute):
    """Execute a pipeline."""
    try:
        run = await pipeline_engine.run(data.pipeline_id, data.initial_state)
        return {
            "run_id": run.id,
            "pipeline_id": run.pipeline_id,
            "status": run.status.value,
            "progress": run.progress,
            "steps": {k: {"status": v.status.value, "output": str(v.output)[:500] if v.output else None, "error": v.error}
                      for k, v in run.steps.items()},
            "total_duration_ms": run.total_duration_ms,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Pipeline execution failed: {str(e)}")


@router.get("/pipelines/runs/{run_id}")
async def get_pipeline_run(run_id: str):
    """Get a pipeline run status."""
    run = pipeline_engine.get_run(run_id)
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    return {
        "run_id": run.id,
        "pipeline_id": run.pipeline_id,
        "status": run.status.value,
        "progress": run.progress,
        "state": run.state,
        "steps": {k: {"status": v.status.value, "output": str(v.output)[:500] if v.output else None,
                     "error": v.error, "duration_ms": v.duration_ms}
                  for k, v in run.steps.items()},
        "total_duration_ms": run.total_duration_ms,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


@router.get("/pipeline-runs")
async def list_pipeline_runs(pipeline_id: str | None = None, limit: int = 20):
    """List pipeline run history."""
    return {"runs": pipeline_engine.list_runs(pipeline_id, limit)}


@router.get("/pipeline-stats")
async def pipeline_stats():
    """Get pipeline engine statistics."""
    return pipeline_engine.get_stats()


# ═══════════════════════════════════════════════════════════
# Semantic Cache — Intent-Aware Response Caching
# ═══════════════════════════════════════════════════════════

from agent.semantic_cache import semantic_cache


@router.get("/cache/stats")
async def cache_stats():
    """Get semantic cache statistics."""
    return semantic_cache.get_stats()


@router.post("/cache/invalidate")
async def invalidate_cache(agent_id: str = Query(default="")):
    """Invalidate cache entries."""
    semantic_cache.invalidate(agent_id)
    return {"invalidated": True, "agent_id": agent_id or "all"}


# ═══════════════════════════════════════════════════════════
# Capability Registry — Agent Skill Profiling
# ═══════════════════════════════════════════════════════════

from agent.capability import capability_registry, ProficiencyLevel, CapabilityDomain


class CapabilityProfileUpdate(BaseModel):
    agent_name: str = Field(default="")


@router.get("/capabilities")
async def list_capabilities(domain: str | None = None):
    """List all capabilities, optionally filtered by domain."""
    cap_domain = CapabilityDomain(domain) if domain else None
    return {"capabilities": capability_registry.list_capabilities(cap_domain)}


@router.get("/capabilities/domains")
async def list_capability_domains():
    """List all capability domains."""
    return {"domains": capability_registry.list_domains()}


@router.get("/capabilities/profiles/{agent_id}")
async def get_capability_profile(agent_id: str):
    """Get an agent's capability profile."""
    summary = capability_registry.get_profile_summary(agent_id)
    if not summary:
        raise HTTPException(404, "Agent profile not found")
    return summary


@router.post("/capabilities/profiles/{agent_id}/update")
async def update_capability_profile(agent_id: str, data: CapabilityProfileUpdate):
    """Create or update agent capability profile."""
    profile = capability_registry.get_or_create_profile(agent_id, data.agent_name)
    summary = capability_registry.get_profile_summary(agent_id)
    return summary or {}


@router.post("/capabilities/profiles/{agent_id}/capabilities")
async def add_agent_capability(
    agent_id: str,
    capability_id: str = Query(..., min_length=1),
    score: float = Query(default=0.5, ge=0.0, le=1.0),
):
    """Add a capability to an agent."""
    proficiency = capability_registry._score_to_level(score)
    capability_registry.add_capability(agent_id, capability_id, proficiency, score)
    return {"added": True, "capability_id": capability_id, "score": score}


@router.post("/capabilities/profiles/{agent_id}/record-usage")
async def record_capability_usage(
    agent_id: str,
    capability_id: str = Query(..., min_length=1),
    success: bool = Query(default=True),
):
    """Record capability usage."""
    capability_registry.record_usage(agent_id, capability_id, success)
    return {"recorded": True}


@router.post("/capabilities/match")
async def match_agents_for_requirements(
    required_capabilities: str = Query(..., min_length=1),
    min_proficiency: str = Query(default="intermediate"),
):
    """Find agents matching capability requirements."""
    caps = [c.strip() for c in required_capabilities.split(",") if c.strip()]
    proficiency = ProficiencyLevel(min_proficiency)
    results = capability_registry.find_agents_for_requirements(caps, proficiency)
    return {"matches": results, "required": caps}


@router.get("/capabilities/profiles/{agent_id}/gaps")
async def get_capability_gaps(agent_id: str, domain: str | None = None):
    """Get capability gaps for an agent."""
    cap_domain = CapabilityDomain(domain) if domain else None
    gaps = capability_registry.find_capability_gaps(agent_id, cap_domain)
    return {"gaps": gaps, "agent_id": agent_id}


@router.post("/capabilities/decay")
async def apply_capability_decay():
    """Apply time-based decay to all capability profiles."""
    capability_registry.apply_decay()
    return {"decay_applied": True}


@router.get("/capability-stats")
async def capability_stats():
    """Get capability registry statistics."""
    return capability_registry.get_stats()


# ═══════════════════════════════════════════════════════════
# Knowledge Graph — Entity-Relationship Modeling
# ═══════════════════════════════════════════════════════════

from agent.shared import knowledge_graph, memory_sync_hub


class EntityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    entity_type: str = Field(default="concept", max_length=64)
    properties: dict = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="api")


class RelationshipCreate(BaseModel):
    source_id: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)
    relation_type: str = Field(default="related_to", max_length=64)
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    properties: dict = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class KnowledgeExtractRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = Field(default="api")


@router.get("/kg/stats")
async def kg_stats():
    """Get knowledge graph statistics."""
    return knowledge_graph.get_stats()


@router.get("/kg/entities")
async def list_kg_entities(
    entity_type: str | None = None,
    name_contains: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List entities in the knowledge graph."""
    entities = knowledge_graph.find_entities(
        entity_type=entity_type,
        name_contains=name_contains,
        limit=limit,
    )
    return {
        "entities": [
            {"id": e.id, "name": e.name, "type": e.entity_type,
             "properties": e.properties, "confidence": e.confidence}
            for e in entities
        ],
        "count": len(entities),
    }


@router.post("/kg/entities", status_code=201)
async def create_kg_entity(data: EntityCreate):
    """Add an entity to the knowledge graph."""
    from agent.knowledge_graph import Entity
    entity = Entity(
        id=f"ent-{uuid.uuid4().hex[:12]}",
        name=data.name,
        entity_type=data.entity_type,
        properties=data.properties,
        confidence=data.confidence,
        source=data.source,
    )
    entity_id = knowledge_graph.add_entity(entity)
    return {"entity_id": entity_id, "name": data.name, "type": data.entity_type}


@router.get("/kg/entities/{entity_id}")
async def get_kg_entity(entity_id: str):
    """Get an entity by ID."""
    entity = knowledge_graph.get_entity(entity_id)
    if not entity:
        raise HTTPException(404, "Entity not found")
    return {
        "id": entity.id,
        "name": entity.name,
        "type": entity.entity_type,
        "properties": entity.properties,
        "confidence": entity.confidence,
        "source": entity.source,
        "created_at": entity.created_at,
    }


class EntityUpdate(BaseModel):
    properties: dict = Field(default_factory=dict)


@router.patch("/kg/entities/{entity_id}")
async def update_kg_entity(entity_id: str, data: EntityUpdate):
    """Update entity properties."""
    if not knowledge_graph.update_entity(entity_id, **data.properties):
        raise HTTPException(404, "Entity not found")
    return {"updated": True}


@router.delete("/kg/entities/{entity_id}")
async def delete_kg_entity(entity_id: str):
    """Delete an entity and its relationships."""
    if not knowledge_graph.remove_entity(entity_id):
        raise HTTPException(404, "Entity not found")
    return {"deleted": True}


@router.post("/kg/relationships", status_code=201)
async def create_kg_relationship(data: RelationshipCreate):
    """Add a relationship between entities."""
    from agent.knowledge_graph import Relationship
    rel = Relationship(
        id=f"rel-{uuid.uuid4().hex[:12]}",
        source_id=data.source_id,
        target_id=data.target_id,
        relation_type=data.relation_type,
        weight=data.weight,
        properties=data.properties,
        confidence=data.confidence,
    )
    rel_id = knowledge_graph.add_relationship(rel)
    if not rel_id:
        raise HTTPException(400, "One or both entities not found")
    return {"relationship_id": rel_id, "type": data.relation_type}


@router.get("/kg/entities/{entity_id}/relationships")
async def get_entity_relationships(entity_id: str):
    """Get all relationships for an entity."""
    rels = knowledge_graph.get_relationships(entity_id)
    return {
        "relationships": [
            {"id": r.id, "source": r.source_id, "target": r.target_id,
             "type": r.relation_type, "weight": r.weight}
            for r in rels
        ],
        "count": len(rels),
    }


@router.delete("/kg/relationships/{rel_id}")
async def delete_kg_relationship(rel_id: str):
    """Delete a relationship."""
    if not knowledge_graph.remove_relationship(rel_id):
        raise HTTPException(404, "Relationship not found")
    return {"deleted": True}


@router.get("/kg/entities/{entity_id}/neighborhood")
async def get_kg_neighborhood(
    entity_id: str,
    depth: int = Query(default=1, ge=1, le=5),
    max_entities: int = Query(default=50, ge=1, le=200),
):
    """Get the neighborhood around an entity."""
    return knowledge_graph.get_neighborhood(entity_id, depth, max_entities)


@router.get("/kg/paths")
async def find_kg_paths(
    source_id: str = Query(..., min_length=1),
    target_id: str = Query(..., min_length=1),
    max_depth: int = Query(default=5, ge=1, le=10),
):
    """Find paths between two entities."""
    paths = knowledge_graph.find_paths(source_id, target_id, max_depth)
    return {
        "paths": [
            {
                "entities": [e.name for e in p.entities],
                "relationship_types": [r.relation_type for r in p.relationships],
                "path_length": p.path_length,
                "total_weight": p.total_weight,
            }
            for p in paths
        ],
        "count": len(paths),
    }


@router.get("/kg/search")
async def semantic_search_kg(
    query: str = Query(..., min_length=1),
    entity_type: str | None = None,
    top_k: int = Query(default=10, ge=1, le=50),
):
    """Search entities semantically."""
    results = await knowledge_graph.semantic_search(query, top_k, entity_type)
    return {"results": results, "count": len(results), "query": query}


@router.post("/kg/extract")
async def extract_knowledge(data: KnowledgeExtractRequest):
    """Extract entities and relationships from text."""
    result = await knowledge_graph.extract_from_text(data.text, data.source)
    return result


@router.get("/kg/export")
async def export_kg_subgraph(
    entity_ids: str = Query(default=""),
    include_neighbors: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Export subgraph or visualization data."""
    if entity_ids:
        ids = [e.strip() for e in entity_ids.split(",")]
        return knowledge_graph.export_subgraph(ids, include_neighbors)
    return knowledge_graph.get_visualization_data(limit)


@router.post("/kg/clear")
async def clear_knowledge_graph():
    """Clear the knowledge graph."""
    knowledge_graph.clear()
    return {"cleared": True}


# ═══════════════════════════════════════════════════════════
# Memory Sync — Cross-Agent Memory Synchronization
# ═══════════════════════════════════════════════════════════


class SyncGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    agent_ids: list[str] = Field(..., min_length=1)
    sync_interval: int = Field(default=600, ge=60, le=86400)
    filters: dict = Field(default_factory=dict)


class SyncGroupUpdate(BaseModel):
    name: str | None = None
    agent_ids: list[str] | None = None
    sync_interval: int | None = None
    enabled: bool | None = None


class ShareMemoryRequest(BaseModel):
    source_agent_id: str = Field(..., min_length=1)
    target_agent_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="event")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class BroadcastMemoryRequest(BaseModel):
    source_agent_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="event")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    target_role: str = Field(default="")


@router.get("/memory-sync/stats")
async def memory_sync_stats():
    """Get memory sync hub statistics."""
    result = memory_sync_hub.get_stats()
    if isinstance(result, dict):
        result.setdefault("total_groups", 0)
    return result


@router.get("/memory-sync/config")
async def memory_sync_config():
    """Get memory sync configuration."""
    return memory_sync_hub.get_config()


@router.post("/memory-sync/config")
async def update_memory_sync_config(
    max_shared_per_agent: int | None = None,
    max_broadcast_agents: int | None = None,
    default_sync_interval: int | None = None,
    auto_sync_enabled: bool | None = None,
):
    """Update memory sync configuration."""
    memory_sync_hub.update_config(
        max_shared_per_agent=max_shared_per_agent,
        max_broadcast_agents=max_broadcast_agents,
        default_sync_interval=default_sync_interval,
        auto_sync_enabled=auto_sync_enabled,
    )
    return memory_sync_hub.get_config()


@router.post("/memory-sync/share")
async def share_memory_between_agents(data: ShareMemoryRequest):
    """Share a memory from one agent to another."""
    memory_id = await memory_sync_hub.share_memory(
        source_agent_id=data.source_agent_id,
        target_agent_id=data.target_agent_id,
        content=data.content,
        memory_type=data.memory_type,
        importance=data.importance,
        tags=data.tags,
    )
    if not memory_id:
        raise HTTPException(500, "Failed to share memory")
    return {
        "shared": True,
        "memory_id": memory_id,
        "source": data.source_agent_id,
        "target": data.target_agent_id,
    }


@router.post("/memory-sync/broadcast")
async def broadcast_memory(data: BroadcastMemoryRequest):
    """Broadcast a memory to multiple agents."""
    result = await memory_sync_hub.broadcast_memory(
        source_agent_id=data.source_agent_id,
        content=data.content,
        memory_type=data.memory_type,
        importance=data.importance,
        tags=data.tags,
        target_role=data.target_role,
    )
    return result


@router.get("/memory-sync/search")
async def search_across_agents(
    query: str = Query(..., min_length=1),
    agent_ids: str = Query(default=""),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Search across multiple agents' memories."""
    id_list = [a.strip() for a in agent_ids.split(",") if a.strip()] if agent_ids else None
    results = await memory_sync_hub.search_across_agents(
        query=query,
        agent_ids=id_list,
        limit=limit,
    )
    return {"results": results, "count": len(results), "query": query}


@router.get("/memory-sync/context")
async def get_shared_context(
    agent_id: str = Query(..., min_length=1),
    topic: str = Query(..., min_length=1),
    max_memories: int = Query(default=10, ge=1, le=50),
):
    """Get relevant shared memories for a topic."""
    context = await memory_sync_hub.get_shared_context(
        agent_id=agent_id,
        topic=topic,
        max_memories=max_memories,
    )
    return {"context": context, "agent_id": agent_id, "topic": topic}


@router.get("/memory-sync/groups")
async def list_sync_groups():
    """List all memory sync groups."""
    return {"groups": memory_sync_hub.list_sync_groups()}


@router.post("/memory-sync/groups", status_code=201)
async def create_sync_group(data: SyncGroupCreate):
    """Create a new memory sync group."""
    group_id = memory_sync_hub.create_sync_group(
        name=data.name,
        agent_ids=data.agent_ids,
        sync_interval=data.sync_interval,
        filters=data.filters,
    )
    return {"group_id": group_id, "name": data.name, "agent_count": len(data.agent_ids)}


@router.get("/memory-sync/groups/{group_id}")
async def get_sync_group(group_id: str):
    """Get a sync group by ID."""
    group = memory_sync_hub.get_sync_group(group_id)
    if not group:
        raise HTTPException(404, "Sync group not found")
    return {
        "id": group.id,
        "name": group.name,
        "agent_ids": group.agent_ids,
        "sync_interval": group.sync_interval,
        "last_sync": group.last_sync,
        "enabled": group.enabled,
        "filters": group.filters,
    }


@router.put("/memory-sync/groups/{group_id}")
async def update_sync_group(group_id: str, data: SyncGroupUpdate):
    """Update a sync group."""
    success = memory_sync_hub.update_sync_group(
        group_id=group_id,
        name=data.name,
        agent_ids=data.agent_ids,
        sync_interval=data.sync_interval,
        enabled=data.enabled,
    )
    if not success:
        raise HTTPException(404, "Sync group not found")
    return {"updated": True, "group_id": group_id}


@router.delete("/memory-sync/groups/{group_id}")
async def delete_sync_group(group_id: str):
    """Delete a sync group."""
    if not memory_sync_hub.remove_sync_group(group_id):
        raise HTTPException(404, "Sync group not found")
    return {"deleted": True}


@router.post("/memory-sync/groups/{group_id}/sync")
async def trigger_group_sync(group_id: str):
    """Manually trigger sync for a group."""
    result = await memory_sync_hub.sync_group_memories(group_id)
    return result


@router.get("/memory-sync/records")
async def list_shared_records(
    source_agent_id: str | None = None,
    target_agent_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """List shared memory records."""
    records = memory_sync_hub.list_shared_memories(
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        limit=limit,
    )
    return {
        "records": [
            {
                "id": r.id,
                "source_agent_id": r.source_agent_id,
                "target_agent_id": r.target_agent_id,
                "content": r.content[:200],
                "memory_type": r.memory_type,
                "importance": r.importance,
                "tags": r.tags,
                "shared_at": r.shared_at,
                "access_count": r.access_count,
            }
            for r in records
        ],
        "count": len(records),
    }


# ═══════════════════════════════════════════════════════════════════
# Agent Communication Protocol (ACP) Endpoints
# ═══════════════════════════════════════════════════════════════════

class AgentMessageCreate(BaseModel):
    msg_type: str = "task_request"
    sender_id: str
    recipient_id: str
    priority: str = "normal"
    payload: dict = Field(default_factory=dict)
    ttl_seconds: int = 300
    tags: list[str] = Field(default_factory=list)


@router.get("/protocol/stats")
async def get_protocol_stats():
    """Get ACP communication statistics."""
    return acp.get_stats()


@router.get("/protocol/agent/{agent_id}/stats")
async def get_agent_protocol_stats(agent_id: str):
    """Get ACP stats for a specific agent."""
    return acp.get_agent_stats(agent_id)


@router.post("/protocol/send", status_code=201)
async def send_acp_message(data: AgentMessageCreate):
    """Send a message via the Agent Communication Protocol."""
    try:
        msg_type = AcpMessageType(data.msg_type)
    except ValueError:
        raise HTTPException(400, f"Invalid message type: {data.msg_type}")
    try:
        priority = MessagePriority(data.priority)
    except ValueError:
        priority = MessagePriority.NORMAL

    msg = AgentMessage(
        msg_type=msg_type,
        sender_id=data.sender_id,
        recipient_id=data.recipient_id,
        priority=priority,
        payload=data.payload,
        ttl_seconds=data.ttl_seconds,
        tags=data.tags,
    )
    success = await acp.send(msg)
    return {"sent": success, "message_id": msg.id, "status": msg.status.value}


@router.post("/protocol/session")
async def create_protocol_session(agent_a: str = Query(...), agent_b: str = Query(...)):
    """Create a communication session between two agents."""
    session = await acp.create_session(agent_a, agent_b)
    return {
        "session_id": session.id,
        "agent_a": session.agent_a,
        "agent_b": session.agent_b,
        "is_active": session.is_active,
    }


@router.delete("/protocol/session")
async def close_protocol_session(agent_a: str = Query(...), agent_b: str = Query(...)):
    """Close a communication session."""
    await acp.close_session(agent_a, agent_b)
    return {"closed": True}


# ═══════════════════════════════════════════════════════════════════
# Provider Registry Endpoints
# ═══════════════════════════════════════════════════════════════════

class ProviderRegisterRequest(BaseModel):
    provider_type: str
    api_key: str = ""
    base_url: str = ""
    models: list[str] = Field(default_factory=list)
    default_model: str = ""
    max_concurrency: int = 10


@router.get("/providers/stats")
async def get_provider_stats():
    """Get comprehensive provider statistics."""
    return provider_registry.get_stats()


@router.get("/providers/costs")
async def get_provider_costs():
    """Get cost breakdown by provider."""
    return provider_registry.get_cost_summary()


@router.get("/providers/models")
async def get_available_models():
    """Get all available models across providers."""
    return {"models": provider_registry.get_available_models()}


@router.get("/providers/health")
async def get_provider_health():
    """Get health status of all providers."""
    healthy = provider_registry.get_healthy_providers()
    return {
        "healthy": [h.value for h in healthy],
        "total": len(provider_registry._providers),
    }


@router.post("/providers/health/{provider_type}/check")
async def check_provider_health(provider_type: str):
    """Run a health check on a specific provider."""
    try:
        pt = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(400, f"Invalid provider type: {provider_type}")
    health = await provider_registry.health_check(pt)
    return {
        "provider": pt.value,
        "status": health.status.value,
        "latency_ms": health.latency_ms,
        "consecutive_failures": health.consecutive_failures,
    }


@router.post("/providers/register", status_code=201)
async def register_provider(data: ProviderRegisterRequest):
    """Register a new LLM provider."""
    try:
        pt = ProviderType(data.provider_type)
    except ValueError:
        raise HTTPException(400, f"Invalid provider type: {data.provider_type}")
    config = ProviderConfig(
        provider_type=pt,
        api_key=data.api_key,
        base_url=data.base_url,
        models=data.models,
        default_model=data.default_model or (data.models[0] if data.models else ""),
        max_concurrency=data.max_concurrency,
    )
    provider_registry.register(config)
    return {"registered": True, "provider": pt.value, "models": data.models}


@router.delete("/providers/{provider_type}")
async def unregister_provider(provider_type: str):
    """Remove a provider from the registry."""
    try:
        pt = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(400, f"Invalid provider type: {provider_type}")
    provider_registry.unregister(pt)
    return {"unregistered": True}


@router.post("/providers/cache/clear")
async def clear_provider_cache():
    """Clear the provider response cache."""
    provider_registry.clear_cache()
    return {"cleared": True}


# ═══════════════════════════════════════════════════════════════════
# Tool Chain Endpoints
# ═══════════════════════════════════════════════════════════════════

class ToolNodeCreate(BaseModel):
    id: str
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    timeout_seconds: int = 60
    retry_on_failure: bool = False


class ToolChainCreate(BaseModel):
    name: str
    nodes: list[ToolNodeCreate]
    edges: list[dict] = Field(default_factory=list)  # [{from, to}]
    global_timeout_seconds: int = 300


@router.get("/tool-chains/stats")
async def get_tool_chain_stats():
    """Get tool chain executor statistics."""
    return tool_chain_executor.get_executor_stats()


@router.get("/tool-chains/templates")
async def list_tool_chain_templates():
    """List all saved tool chain templates."""
    return {"templates": tool_chain_executor.list_templates()}


@router.post("/tool-chains", status_code=201)
async def create_tool_chain(data: ToolChainCreate):
    """Create and optionally execute a tool chain."""
    nodes = [
        ToolNode(
            id=n.id,
            tool_name=n.tool_name,
            arguments=n.arguments,
            depends_on=n.depends_on,
            timeout_seconds=n.timeout_seconds,
            retry_on_failure=n.retry_on_failure,
        )
        for n in data.nodes
    ]
    chain = tool_chain_executor.create_chain(data.name, nodes)
    for edge in data.edges:
        chain.add_edge(edge["from"], edge["to"])
    chain.global_timeout_seconds = data.global_timeout_seconds
    return {"chain_id": chain.id, "name": chain.name, "node_count": len(nodes)}


@router.get("/tool-chains/{chain_id}")
async def get_tool_chain(chain_id: str):
    """Get tool chain details and execution stats."""
    stats = tool_chain_executor.get_chain_stats(chain_id)
    if not stats:
        raise HTTPException(404, "Tool chain not found")
    return stats


@router.post("/tool-chains/{chain_id}/execute")
async def execute_tool_chain(chain_id: str):
    """Execute a tool chain."""
    chain = await tool_chain_executor.execute(chain_id)
    results = tool_chain_executor.get_all_results(chain_id)
    return {
        "chain_id": chain.id,
        "status": chain.status.value,
        "results": {k: str(v)[:500] for k, v in results.items()},
        "node_count": len(chain.nodes),
    }


@router.post("/tool-chains/templates/{name}")
async def save_tool_chain_template(name: str, data: ToolChainCreate):
    """Save a tool chain as a reusable template."""
    nodes = [
        ToolNode(
            id=n.id,
            tool_name=n.tool_name,
            arguments=n.arguments,
            depends_on=n.depends_on,
            timeout_seconds=n.timeout_seconds,
            retry_on_failure=n.retry_on_failure,
        )
        for n in data.nodes
    ]
    chain = tool_chain_executor.create_chain(data.name, nodes)
    for edge in data.edges:
        chain.add_edge(edge["from"], edge["to"])
    tool_chain_executor.save_template(name, chain)
    return {"saved": True, "template": name, "node_count": len(nodes)}


# ═══════════════════════════════════════════════════════════════════
# Agent Discovery Endpoints
# ═══════════════════════════════════════════════════════════════════

class AgentRegisterRequest(BaseModel):
    agent_id: str
    agent_name: str
    capabilities: list[str] = Field(default_factory=list)
    expertise_domains: list[str] = Field(default_factory=list)
    model: str = ""
    max_concurrency: int = 5


@router.get("/discovery/stats")
async def get_discovery_stats():
    """Get agent discovery service statistics."""
    return agent_discovery.get_stats()


@router.get("/discovery/capabilities")
async def list_discovery_capabilities():
    """List all registered capabilities."""
    return {"capabilities": agent_discovery.list_capabilities()}


@router.get("/discovery/agents")
async def list_discovered_agents():
    """List all registered agents."""
    agents = agent_discovery.list_all_agents()
    return {
        "agents": [
            {
                "agent_id": a.agent_id,
                "agent_name": a.agent_name,
                "capabilities": a.capabilities,
                "status": a.status,
                "score": a.score,
                "availability": a.availability(),
            }
            for a in agents
        ],
        "count": len(agents),
    }


@router.post("/discovery/register", status_code=201)
async def register_agent_discovery(data: AgentRegisterRequest):
    """Register an agent in the discovery service."""
    registration = AgentRegistration(
        agent_id=data.agent_id,
        agent_name=data.agent_name,
        capabilities=data.capabilities,
        expertise_domains=data.expertise_domains,
        model=data.model,
        max_concurrency=data.max_concurrency,
    )
    agent_id = agent_discovery.register(registration)
    return {"registered": True, "agent_id": agent_id}


@router.post("/discovery/heartbeat/{agent_id}")
async def agent_heartbeat(agent_id: str):
    """Send a heartbeat for an agent."""
    success = agent_discovery.heartbeat(agent_id)
    return {"heartbeat": success, "agent_id": agent_id}


@router.get("/discovery/find/{capability}")
async def discover_by_capability(
    capability: str,
    min_score: float = Query(default=0.3, ge=0.0, le=1.0),
    strategy: str = Query(default="balanced"),
):
    """Find agents by capability."""
    if strategy == "best":
        agent = agent_discovery.discover_best_agent(capability, strategy)
        if agent:
            return {"found": True, "agent": agent.agent_name, "agent_id": agent.agent_id, "score": agent.score}
        return {"found": False, "capability": capability}

    agents = agent_discovery.discover_by_capability(capability, min_score=min_score)
    return {
        "agents": [
            {"agent_id": a.agent_id, "agent_name": a.agent_name, "score": a.score, "load": a.current_load}
            for a in agents
        ],
        "count": len(agents),
    }


@router.get("/discovery/agent/{agent_id}")
async def get_discovery_agent_info(agent_id: str):
    """Get detailed agent discovery info."""
    info = agent_discovery.get_agent_info(agent_id)
    if not info:
        raise HTTPException(404, "Agent not found in discovery service")
    return info


@router.delete("/discovery/agent/{agent_id}")
async def unregister_discovery_agent(agent_id: str):
    """Remove an agent from discovery."""
    agent_discovery.unregister(agent_id)
    return {"unregistered": True}


# ═══════════════════════════════════════════════════════════════════
# Resource Manager Endpoints
# ═══════════════════════════════════════════════════════════════════

class ResourceQuotaSet(BaseModel):
    resource_type: str
    limit: float
    period: str = "per_day"


@router.get("/resources/stats")
async def get_resource_stats():
    """Get resource management statistics."""
    return resource_manager.get_stats()


@router.get("/resources/global")
async def get_global_resource_report():
    """Get global resource usage report."""
    return resource_manager.get_global_report()


@router.get("/resources/agent/{agent_id}")
async def get_agent_resource_report(agent_id: str):
    """Get resource usage report for an agent."""
    return resource_manager.get_usage_report(agent_id)


@router.post("/resources/agent/{agent_id}/quota")
async def set_agent_resource_quota(agent_id: str, data: ResourceQuotaSet):
    """Set a resource quota for an agent."""
    try:
        res_type = ResType(data.resource_type)
    except ValueError:
        raise HTTPException(400, f"Invalid resource type: {data.resource_type}")
    try:
        period = QuotaPeriod(data.period)
    except ValueError:
        period = QuotaPeriod.PER_DAY

    resource_manager.set_agent_quota(agent_id, res_type, data.limit, period)
    return {"set": True, "agent_id": agent_id, "resource_type": res_type.value, "limit": data.limit}


@router.post("/resources/agent/{agent_id}/acquire")
async def acquire_resource(agent_id: str, resource_type: str = Query(...), amount: float = Query(default=1.0, gt=0)):
    """Try to acquire resources for an agent."""
    try:
        res_type = ResType(resource_type)
    except ValueError:
        raise HTTPException(400, f"Invalid resource type: {resource_type}")
    success = await resource_manager.acquire(agent_id, res_type, amount)
    return {"acquired": success, "agent_id": agent_id, "resource_type": res_type.value, "amount": amount}


@router.post("/resources/agent/{agent_id}/release")
async def release_resource(agent_id: str, resource_type: str = Query(...), amount: float = Query(default=1.0, gt=0)):
    """Release previously acquired resources."""
    try:
        res_type = ResType(resource_type)
    except ValueError:
        raise HTTPException(400, f"Invalid resource type: {resource_type}")
    resource_manager.release(agent_id, res_type, amount)
    return {"released": True}


@router.get("/resources/alerts")
async def get_resource_alerts(limit: int = Query(default=10, ge=1, le=100)):
    """Get recent resource usage alerts."""
    return {"alerts": resource_manager.get_alerts(limit)}


@router.post("/resources/agent/{agent_id}/reset")
async def reset_agent_quotas(agent_id: str):
    """Reset all quotas for an agent."""
    resource_manager.reset_agent_quotas(agent_id)
    return {"reset": True}


@router.get("/resources/agent/{agent_id}/check")
async def check_resource_availability(
    agent_id: str,
    resource_type: str = Query(...),
    amount: float = Query(default=1.0, gt=0),
):
    """Check if resources are available without acquiring."""
    try:
        res_type = ResType(resource_type)
    except ValueError:
        raise HTTPException(400, f"Invalid resource type: {resource_type}")
    available, message = resource_manager.check_availability(agent_id, res_type, amount)
    return {"available": available, "message": message}


# ── Reactive Loop APIs ──────────────────────────────────

class ReactiveLoopStartRequest(BaseModel):
    agent_id: str
    mode: str = Field(default="reactive")
    cycle_interval_ms: int = Field(default=5000, ge=1000, le=60000)


class ReactiveLoopObserveRequest(BaseModel):
    source: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    data: dict = Field(default_factory=dict)


class ReactiveLoopEnqueueRequest(BaseModel):
    description: str = Field(..., min_length=1)
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    handler: str = Field(default="")
    payload: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


@router.get("/reactive-loop/{agent_id}/stats")
async def get_reactive_loop_stats(agent_id: str):
    """Get reactive loop statistics for an agent."""
    engine = orchestrator._engines.get(agent_id)
    if not engine or not hasattr(engine, '_reactive_loop'):
        raise HTTPException(404, "Reactive loop not found for this agent")

    loop = engine._reactive_loop
    if not loop:
        raise HTTPException(404, "Reactive loop not initialized")

    return loop.get_stats()


@router.post("/reactive-loop/{agent_id}/start")
async def start_reactive_loop(agent_id: str, data: ReactiveLoopStartRequest):
    """Start the reactive loop for an agent."""
    engine = orchestrator._engines.get(agent_id)
    if not engine:
        raise HTTPException(404, "Agent engine not found")

    from agent.reactive_loop import ReactiveLoop, LoopMode
    if not hasattr(engine, '_reactive_loop') or engine._reactive_loop is None:
        engine._reactive_loop = ReactiveLoop(
            agent_id=agent_id,
            mode=LoopMode(data.mode) if data.mode in [m.value for m in LoopMode] else LoopMode.REACTIVE,
            cycle_interval_ms=data.cycle_interval_ms,
        )

    if not engine._reactive_loop.is_running:
        await engine._reactive_loop.start()

    return {
        "agent_id": agent_id,
        "started": True,
        "mode": engine._reactive_loop.mode.value,
    }


@router.post("/reactive-loop/{agent_id}/stop")
async def stop_reactive_loop(agent_id: str):
    """Stop the reactive loop for an agent."""
    engine = orchestrator._engines.get(agent_id)
    if not engine or not hasattr(engine, '_reactive_loop'):
        raise HTTPException(404, "Reactive loop not found")

    loop = engine._reactive_loop
    if loop and loop.is_running:
        await loop.stop()

    return {"agent_id": agent_id, "stopped": True}


@router.post("/reactive-loop/{agent_id}/observe")
async def reactive_loop_observe(agent_id: str, data: ReactiveLoopObserveRequest):
    """Feed an observation into the reactive loop."""
    engine = orchestrator._engines.get(agent_id)
    if not engine or not hasattr(engine, '_reactive_loop'):
        raise HTTPException(404, "Reactive loop not found")

    loop = engine._reactive_loop
    if not loop:
        raise HTTPException(404, "Reactive loop not initialized")

    loop.observe(
        source=data.source,
        summary=data.summary,
        priority=data.priority,
        data=data.data,
    )

    return {"agent_id": agent_id, "observed": True}


@router.post("/reactive-loop/{agent_id}/enqueue")
async def reactive_loop_enqueue(agent_id: str, data: ReactiveLoopEnqueueRequest):
    """Enqueue an action into the reactive loop."""
    engine = orchestrator._engines.get(agent_id)
    if not engine or not hasattr(engine, '_reactive_loop'):
        raise HTTPException(404, "Reactive loop not found")

    loop = engine._reactive_loop
    if not loop:
        raise HTTPException(404, "Reactive loop not initialized")

    action_id = loop.enqueue_action(
        description=data.description,
        priority=data.priority,
        handler=data.handler,
        payload=data.payload,
        depends_on=data.depends_on,
    )

    return {"agent_id": agent_id, "action_id": action_id, "enqueued": True}


@router.get("/reactive-loop/{agent_id}/actions")
async def reactive_loop_actions(agent_id: str, limit: int = Query(default=20, ge=1, le=100)):
    """Get pending/recent actions from the reactive loop."""
    engine = orchestrator._engines.get(agent_id)
    if not engine or not hasattr(engine, '_reactive_loop'):
        raise HTTPException(404, "Reactive loop not found")

    loop = engine._reactive_loop
    if not loop:
        raise HTTPException(404, "Reactive loop not initialized")

    return {
        "agent_id": agent_id,
        "actions": loop.get_pending_actions(limit),
    }


@router.get("/reactive-loop/{agent_id}/cycles")
async def reactive_loop_cycles(agent_id: str, limit: int = Query(default=10, ge=1, le=100)):
    """Get recent cycle history from the reactive loop."""
    engine = orchestrator._engines.get(agent_id)
    if not engine or not hasattr(engine, '_reactive_loop'):
        raise HTTPException(404, "Reactive loop not found")

    loop = engine._reactive_loop
    if not loop:
        raise HTTPException(404, "Reactive loop not initialized")

    return {
        "agent_id": agent_id,
        "cycles": loop.get_recent_cycles(limit),
    }


@router.post("/reactive-loop/{agent_id}/mode")
async def set_reactive_loop_mode(agent_id: str, mode: str = Query(..., description="Operating mode: passive, reactive, proactive, autonomous")):
    """Change the operating mode of the reactive loop."""
    from agent.reactive_loop import LoopMode

    engine = orchestrator._engines.get(agent_id)
    if not engine or not hasattr(engine, '_reactive_loop'):
        raise HTTPException(404, "Reactive loop not found")

    loop = engine._reactive_loop
    if not loop:
        raise HTTPException(404, "Reactive loop not initialized")

    valid_modes = [m.value for m in LoopMode]
    if mode not in valid_modes:
        raise HTTPException(400, f"Invalid mode. Must be one of: {', '.join(valid_modes)}")

    loop.set_mode(LoopMode(mode))

    return {"agent_id": agent_id, "mode": mode}


# ── Platform Hub APIs ──────────────────────────────────

class PlatformConfigUpdate(BaseModel):
    auto_restart_subsystems: bool | None = None
    health_check_interval_ms: int | None = Field(default=None, ge=5000, le=300000)
    max_subsystem_restarts: int | None = Field(default=None, ge=1, le=20)


@router.get("/platform/hub/health")
async def get_platform_health():
    """Get comprehensive platform health status."""
    return platform_hub.get_health()


@router.get("/platform/hub/stats")
async def get_platform_stats():
    """Get platform hub statistics."""
    return platform_hub.get_stats()


@router.get("/platform/hub/config")
async def get_platform_config():
    """Get platform hub configuration."""
    return platform_hub.get_config()


@router.post("/platform/hub/config")
async def update_platform_config(data: PlatformConfigUpdate):
    """Update platform hub configuration."""
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    platform_hub.update_config(updates)
    return {"updated": True, "config": platform_hub.get_config()}


@router.get("/platform/hub/subsystems")
async def list_platform_subsystems():
    """List all platform subsystems and their status."""
    subsystems = {}
    for name in PlatformSubsystem.__members__.values():
        subsystems[name.value] = platform_hub.get_subsystem_info(name.value)
    return {"subsystems": subsystems}


@router.get("/platform/hub/subsystems/{subsystem_name}")
async def get_platform_subsystem(subsystem_name: str):
    """Get detailed info for a specific subsystem."""
    info = platform_hub.get_subsystem_info(subsystem_name)
    if not info:
        raise HTTPException(404, f"Subsystem not found: {subsystem_name}")
    return info


@router.get("/platform/hub/events")
async def get_platform_events(
    limit: int = Query(default=50, ge=1, le=200),
    event_type: str | None = None,
):
    """Get recent platform events."""
    return {
        "events": platform_hub.get_recent_events(limit=limit, event_type=event_type),
    }


@router.post("/platform/hub/start")
async def start_platform_hub():
    """Start the platform hub and all subsystems."""
    if platform_hub.is_running:
        return {"started": False, "message": "Platform hub is already running"}

    await platform_hub.start()
    return {
        "started": True,
        "health": platform_hub.get_health(),
    }


@router.post("/platform/hub/stop")
async def stop_platform_hub():
    """Stop the platform hub and all subsystems."""
    if not platform_hub.is_running:
        return {"stopped": False, "message": "Platform hub is not running"}

    await platform_hub.stop()
    return {"stopped": True}


# ── Platform Hub SSE Event Stream ─────────────────────────

@router.get("/platform/hub/stream")
async def platform_event_stream():
    """SSE stream for real-time platform events."""
    import asyncio

    async def event_generator():
        # Send initial health status
        health = platform_hub.get_health()
        yield f"data: {json.dumps({'type': 'health', 'data': health})}\n\n"

        stats = platform_hub.get_stats()
        yield f"data: {json.dumps({'type': 'stats', 'data': stats})}\n\n"

        recent_events = platform_hub.get_recent_events(limit=20)
        yield f"data: {json.dumps({'type': 'events', 'data': recent_events})}\n\n"

        # Stream new events every 2 seconds
        last_event_idx = len(platform_hub._event_history)
        while True:
            await asyncio.sleep(2)
            current_events = platform_hub._event_history
            if len(current_events) > last_event_idx:
                new_events = current_events[last_event_idx:]
                last_event_idx = len(current_events)
                for event in new_events:
                    yield f"data: {json.dumps({'type': 'event', 'data': {'id': event.id, 'source': event.source, 'event_type': event.event_type, 'severity': event.severity, 'data': event.data, 'timestamp': event.timestamp}})}\n\n"

            # Send heartbeat to keep connection alive
            yield f": heartbeat\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Platform Hub Agent Routing ───────────────────────────

@router.post("/platform/hub/routing/register")
async def register_agent_route(task_type: str = Query(..., min_length=1), agent_id: str = Query(..., min_length=1)):
    """Register an agent as the handler for a specific task type."""
    platform_hub.register_agent_route(task_type, agent_id)
    return {"task_type": task_type, "agent_id": agent_id, "registered": True}


@router.get("/platform/hub/routing/table")
async def get_agent_routing_table():
    """Get the complete agent routing table."""
    return platform_hub.get_routing_table()


@router.get("/platform/hub/routing/resolve")
async def resolve_agent_route(task_type: str = Query(..., min_length=1)):
    """Resolve which agent should handle a given task type."""
    agent_id = platform_hub.resolve_agent_route(task_type)
    return {"task_type": task_type, "agent_id": agent_id}


# ── Platform Hub Performance Metrics ──────────────────────

@router.get("/platform/hub/metrics")
async def get_platform_metrics():
    """Get aggregated performance metrics for all subsystems."""
    return platform_hub.get_performance_metrics()


@router.post("/platform/hub/metrics/record")
async def record_platform_metric(subsystem: str = Query(..., min_length=1), latency_ms: float = Query(..., ge=0)):
    """Record a performance metric for a subsystem."""
    platform_hub.record_metric(subsystem, latency_ms)
    return {"subsystem": subsystem, "latency_ms": latency_ms, "recorded": True}


@router.get("/platform/hub/dependencies")
async def get_subsystem_dependencies():
    """Get the subsystem dependency graph."""
    return platform_hub.get_dependency_graph()


# ── Cost Analytics APIs ──────────────────────────────────

@router.get("/costs/overview")
async def get_cost_overview():
    """Get overall cost summary across all agents."""
    return cost_tracker.get_system_overview()


@router.get("/costs/breakdown")
async def get_cost_breakdown(period: str = "daily"):
    """Get cost breakdown by period (daily, weekly, monthly)."""
    return cost_tracker.get_cost_breakdown(period)


@router.get("/costs/by-tier")
async def get_cost_by_tier():
    """Get cost breakdown by model tier (light/standard/premium)."""
    return cost_tracker.get_cost_by_tier()


@router.get("/costs/suggestions")
async def get_cost_suggestions():
    """Get optimization suggestions for cost reduction."""
    return cost_tracker.get_optimization_suggestions()


@router.get("/costs/budgets")
async def get_cost_budgets():
    """Get current budget status and alerts."""
    return cost_tracker.get_budget_status()


@router.get("/costs/projections")
async def get_cost_projections(days: int = 30):
    """Get cost projections for the specified number of days."""
    return cost_tracker.project_costs(days)


# ═══════════════════════════════════════════════════════════
# Proactive Discovery
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/proactive/status")
async def get_proactive_status(agent_id: str):
    """Get proactive discovery engine status."""
    engine = orchestrator.get_engine(agent_id, "", "")
    return engine.proactive.get_stats()


@router.get("/agents/{agent_id}/proactive/tasks")
async def get_proactive_tasks(
    agent_id: str,
    status: str | None = None,
    source: str | None = None,
    urgency: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get proactively discovered tasks with optional filtering."""
    engine = orchestrator.get_engine(agent_id, "", "")
    tasks = engine.proactive.get_tasks(
        status=status,
        source=source,
        urgency=urgency,
        limit=limit,
    )
    return {"tasks": tasks, "total": len(tasks)}


@router.get("/agents/{agent_id}/proactive/insights")
async def get_proactive_insights(agent_id: str, limit: int = Query(20, ge=1, le=100)):
    """Get discovery insights."""
    engine = orchestrator.get_engine(agent_id, "", "")
    insights = engine.proactive.get_insights(limit=limit)
    return {"insights": insights, "total": len(insights)}


@router.post("/agents/{agent_id}/proactive/scan")
async def run_proactive_scan(agent_id: str):
    """Run an immediate proactive discovery scan."""
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(404, "Agent not found")

    engine = orchestrator.get_engine(
        agent_id=agent.id,
        agent_name=agent.name,
        instructions=agent.instructions or "",
    )

    scan_result = await engine.proactive.scan(
        memory_system=engine.memory,
    )

    return {
        "tasks_discovered": len(scan_result.tasks),
        "insights": scan_result.insights,
        "patterns_detected": scan_result.patterns_detected,
        "scan_duration_ms": scan_result.scan_duration_ms,
        "scanned_at": scan_result.scanned_at,
        "tasks": [t.to_dict() for t in scan_result.tasks],
    }


@router.post("/agents/{agent_id}/proactive/start")
async def start_proactive_discovery(agent_id: str, interval: int = Query(600, ge=60, le=86400)):
    """Start the always-on proactive discovery loop."""
    engine = orchestrator.get_engine(agent_id, "", "")
    await engine.proactive.start(interval=interval)
    return {"status": "started", "agent_id": agent_id, "interval": interval}


@router.post("/agents/{agent_id}/proactive/stop")
async def stop_proactive_discovery(agent_id: str):
    """Stop the proactive discovery loop."""
    engine = orchestrator.get_engine(agent_id, "", "")
    await engine.proactive.stop()
    return {"status": "stopped", "agent_id": agent_id}


@router.post("/agents/{agent_id}/proactive/tasks/{task_id}/schedule")
async def schedule_proactive_task(agent_id: str, task_id: str):
    """Schedule a discovered task for execution."""
    engine = orchestrator.get_engine(agent_id, "", "")
    success = engine.proactive.schedule_task(task_id)
    if not success:
        raise HTTPException(400, "Task cannot be scheduled")
    return {"status": "scheduled", "task_id": task_id}


@router.post("/agents/{agent_id}/proactive/tasks/{task_id}/dismiss")
async def dismiss_proactive_task(agent_id: str, task_id: str):
    """Dismiss a discovered task."""
    engine = orchestrator.get_engine(agent_id, "", "")
    success = engine.proactive.dismiss_task(task_id)
    if not success:
        raise HTTPException(404, "Task not found")
    return {"status": "dismissed", "task_id": task_id}


@router.post("/agents/{agent_id}/proactive/tasks/{task_id}/complete")
async def complete_proactive_task(agent_id: str, task_id: str):
    """Mark a discovered task as completed."""
    engine = orchestrator.get_engine(agent_id, "", "")
    success = engine.proactive.complete_task(task_id)
    if not success:
        raise HTTPException(404, "Task not found")
    return {"status": "completed", "task_id": task_id}


# ═══════════════════════════════════════════════════════════
# Meta-Cognition
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/metacognition/stats")
async def get_metacognition_stats(agent_id: str):
    """Get meta-cognition strategy statistics."""
    engine = orchestrator.get_engine(agent_id, "", "")
    return engine.get_metacognition_stats()


@router.get("/agents/{agent_id}/metacognition/insights")
async def get_metacognition_insights(agent_id: str):
    """Get actionable insights from metacognition learning."""
    engine = orchestrator.get_engine(agent_id, "", "")
    insights = engine.get_metacognition_insights()
    return {"agent_id": agent_id, "insights": insights, "count": len(insights)}


@router.get("/agents/{agent_id}/metacognition/decisions")
async def get_metacognition_decisions(agent_id: str, limit: int = Query(20, ge=1, le=100)):
    """Get recent strategy decisions with their outcomes."""
    engine = orchestrator.get_engine(agent_id, "", "")
    decisions = engine.metacognition.get_recent_decisions(limit=limit)
    return {"agent_id": agent_id, "decisions": decisions, "count": len(decisions)}


# ═══════════════════════════════════════════════════════════
# Proactive-Autopilot Bridge
# ═══════════════════════════════════════════════════════════

@router.post("/agents/{agent_id}/bridge/proactive-to-autopilot")
async def bridge_proactive_to_autopilot(agent_id: str, max_tasks: int = Query(5, ge=1, le=50)):
    """Bridge proactively discovered tasks to the autopilot scheduler."""
    engine = orchestrator.get_engine(agent_id, "", "")
    result = await engine.bridge_proactive_to_autopilot(max_tasks=max_tasks)
    return result


# ═══════════════════════════════════════════════════════════
# Agent Evolution
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/evolution/stats")
async def get_evolution_stats(agent_id: str):
    """Get agent evolution optimization statistics."""
    engine = orchestrator.get_engine(agent_id, "", "")
    return engine.get_evolution_stats()


@router.get("/agents/{agent_id}/evolution/pathways")
async def get_evolution_pathways(agent_id: str):
    """Get discovered optimization pathways."""
    engine = orchestrator.get_engine(agent_id, "", "")
    pathways = engine.get_evolution_pathways()
    return {"agent_id": agent_id, "pathways": pathways, "count": len(pathways)}


@router.get("/agents/{agent_id}/evolution/insights")
async def get_evolution_insights(agent_id: str):
    """Get evolution optimization insights."""
    engine = orchestrator.get_engine(agent_id, "", "")
    insights = engine.get_evolution_insights()
    return {"agent_id": agent_id, "insights": insights, "count": len(insights)}


@router.post("/agents/{agent_id}/evolution/run")
async def run_evolution_cycle(agent_id: str):
    """Run an evolution analysis cycle."""
    engine = orchestrator.get_engine(agent_id, "", "")
    result = await engine.run_evolution_cycle()
    return result


# ═══════════════════════════════════════════════════════════
# Proactive Interactions
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/proactive/interactions")
async def get_proactive_interactions(agent_id: str, limit: int = Query(20, ge=1, le=100)):
    """Get recent interactions observed by the proactive discovery engine."""
    engine = orchestrator.get_engine(agent_id, "", "")
    interactions = engine.proactive.get_recent_interactions(limit=limit)
    return {"agent_id": agent_id, "interactions": interactions, "count": len(interactions)}


# ═══════════════════════════════════════════════════════════
# Agent Communication Protocol
# ═══════════════════════════════════════════════════════════

from agent.comm_protocol import agent_comm, DelegationRequest, ContextShare
from agent.comm_protocol import MessageType as CommMsgType, MessagePriority as CommMsgPriority


@router.get("/comm/stats")
async def get_comm_stats():
    """Get agent communication protocol statistics."""
    return agent_comm.get_stats()


@router.get("/comm/messages")
async def get_recent_messages(limit: int = Query(50, ge=1, le=200)):
    """Get recent inter-agent messages."""
    messages = agent_comm.get_recent_messages(limit=limit)
    return {"messages": messages, "count": len(messages)}


@router.post("/comm/send")
async def send_agent_message(
    sender_id: str = Query(..., min_length=1),
    recipient_id: str = Query(default=""),
    subject: str = Query(default=""),
    content: str = Query(..., min_length=1),
    msg_type: str = Query(default="direct"),
    priority: str = Query(default="normal"),
):
    """Send a message between agents."""
    if msg_type == "broadcast":
        msg = await agent_comm.broadcast(
            sender_id=sender_id,
            subject=subject,
            content=content,
            priority=CommMsgPriority(priority) if priority in [p.value for p in CommMsgPriority] else CommMsgPriority.NORMAL,
        )
    else:
        msg = await agent_comm.direct_message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            priority=CommMsgPriority(priority) if priority in [p.value for p in CommMsgPriority] else CommMsgPriority.NORMAL,
        )
    return {
        "id": msg.id,
        "type": msg.msg_type.value,
        "status": msg.status.value,
        "sender": msg.sender_id,
        "recipient": msg.recipient_id,
        "subject": msg.subject,
        "created_at": msg.created_at,
    }


@router.post("/comm/delegate")
async def delegate_task(request: dict):
    """Delegate a task from one agent to another."""
    delegation = DelegationRequest(
        from_agent_id=request.get("from_agent_id", ""),
        to_agent_id=request.get("to_agent_id", ""),
        task_description=request.get("task_description", ""),
        task_context=request.get("task_context", {}),
        required_capabilities=request.get("required_capabilities", []),
        priority=CommMsgPriority(request.get("priority", "normal")),
    )
    result = await agent_comm.delegate_task(delegation)
    return {
        "id": result.id,
        "status": result.status,
        "from_agent_id": result.from_agent_id,
        "to_agent_id": result.to_agent_id,
        "response_reason": result.response_reason,
    }


@router.get("/comm/delegations/pending")
async def get_pending_delegations(agent_id: str = Query(..., min_length=1)):
    """Get pending delegations for an agent."""
    delegations = agent_comm.get_pending_delegations(agent_id)
    return {
        "agent_id": agent_id,
        "delegations": [
            {
                "id": d.id,
                "from_agent_id": d.from_agent_id,
                "task_description": d.task_description,
                "priority": d.priority.value,
                "status": d.status,
                "created_at": d.created_at,
            }
            for d in delegations
        ],
        "count": len(delegations),
    }


@router.post("/comm/agents/register")
async def register_comm_agent(
    agent_id: str = Query(..., min_length=1),
    capabilities: str = Query(default=""),
):
    """Register an agent with the communication protocol."""
    caps = [c.strip() for c in capabilities.split(",") if c.strip()] if capabilities else None
    agent_comm.register_agent(agent_id, caps)
    return {"agent_id": agent_id, "registered": True, "capabilities": caps or []}


@router.post("/comm/agents/unregister")
async def unregister_comm_agent(agent_id: str = Query(..., min_length=1)):
    """Unregister an agent from the communication protocol."""
    agent_comm.unregister_agent(agent_id)
    return {"agent_id": agent_id, "unregistered": True}


@router.get("/comm/agents/online")
async def get_online_agents():
    """Get all online agents."""
    online = [
        {"agent_id": aid, "capabilities": agent_comm.get_agent_capabilities(aid)}
        for aid, is_online in agent_comm._agent_online_status.items()
        if is_online
    ]
    return {"agents": online, "count": len(online)}


# ═══════════════════════════════════════════════════════════
# System Stats
# ═══════════════════════════════════════════════════════════

@router.get("/system/stats")
async def get_system_stats():
    """Get comprehensive system statistics."""
    return {
        "platform": platform_hub.get_stats() if hasattr(platform_hub, 'get_stats') else {"status": "active"},
        "agents": {"total": len(orchestrator._engines)},
        "services": {
            "swarm": swarm_engine.get_stats() if hasattr(swarm_engine, 'get_stats') else {},
            "forge": forge.get_stats() if hasattr(forge, 'get_stats') else {},
            "pipeline": pipeline_engine.get_stats() if hasattr(pipeline_engine, 'get_stats') else {},
            "capability": capability_registry.get_stats() if hasattr(capability_registry, 'get_stats') else {},
            "task_queue": task_queue.get_stats() if hasattr(task_queue, 'get_stats') else {},
            "im_hub": im_hub.get_stats() if hasattr(im_hub, 'get_stats') else {},
        },
        "status": "operational",
    }


# ═══════════════════════════════════════════════════════════
# Platform Hub Stats
# ═══════════════════════════════════════════════════════════

@router.get("/platform-hub/status")
async def get_platform_hub_status():
    """Get platform hub status and statistics."""
    return platform_hub.get_stats() if hasattr(platform_hub, 'get_stats') else {"status": "active"}


# ═══════════════════════════════════════════════════════════
# Session Search Stats
# ═══════════════════════════════════════════════════════════

@router.get("/session-search/stats")
async def get_session_search_stats():
    """Get session search statistics."""
    try:
        sessions = session_searcher.get_recent_sessions(limit=1) if hasattr(session_searcher, 'get_recent_sessions') else []
        return {"total_sessions": len(sessions), "indexed_sessions": len(sessions), "status": "active"}
    except Exception:
        return {"total_sessions": 0, "indexed_sessions": 0, "status": "active"}


# ═══════════════════════════════════════════════════════════
# Cost Analytics
# ═══════════════════════════════════════════════════════════

@router.get("/costs/report")
async def get_cost_report():
    """Get cost analytics report."""
    if hasattr(cost_tracker, 'get_system_overview'):
        return cost_tracker.get_system_overview()
    return {"total_cost": 0, "total_tokens": 0, "status": "active"}


# ═══════════════════════════════════════════════════════════
# Workflow Stats
# ═══════════════════════════════════════════════════════════

@router.get("/workflows/stats")
async def get_workflow_stats():
    """Get workflow engine statistics."""
    return workflow_engine.get_stats() if hasattr(workflow_engine, 'get_stats') else {}


# ═══════════════════════════════════════════════════════════
# Studio Stats
# ═══════════════════════════════════════════════════════════

@router.get("/studio/stats")
async def get_studio_stats():
    """Get studio statistics."""
    return buddy_studio.get_stats() if hasattr(buddy_studio, 'get_stats') else {}


# ═══════════════════════════════════════════════════════════
# Scheduler Stats
# ═══════════════════════════════════════════════════════════

@router.get("/scheduler/stats")
async def get_scheduler_stats():
    """Get scheduler statistics."""
    return buddy_scheduler.get_stats() if hasattr(buddy_scheduler, 'get_stats') else {}


# ═══════════════════════════════════════════════════════════
# Nexus Stats
# ═══════════════════════════════════════════════════════════

@router.get("/nexus/stats")
async def get_nexus_stats():
    """Get nexus statistics."""
    result = nexus.get_summary() if hasattr(nexus, 'get_summary') else {}
    if isinstance(result, dict):
        result.setdefault("nexus_id", "nexus-001")
    return result


# ═══════════════════════════════════════════════════════════
# Identity Stats
# ═══════════════════════════════════════════════════════════

@router.get("/identity/stats")
async def get_identity_stats():
    """Get identity statistics."""
    try:
        agent_id = next(iter(orchestrator._engines), None)
        if agent_id and hasattr(identity, 'get_profile_summary'):
            return identity.get_profile_summary(agent_id)
        return {"profiles": 0, "status": "active"}
    except Exception:
        return {"profiles": 0, "status": "active"}


# ═══════════════════════════════════════════════════════════
# Pulse Stats
# ═══════════════════════════════════════════════════════════

@router.get("/pulse/stats")
async def get_pulse_stats():
    """Get system pulse health statistics."""
    from dataclasses import asdict as dc_asdict
    result = pulse_system.get_system_health() if hasattr(pulse_system, 'get_system_health') else {}
    if hasattr(result, '__dataclass_fields__'):
        result = dc_asdict(result)
    if isinstance(result, dict):
        result["overall_health"] = result.get("overall_status", result.get("overall_health", "healthy"))
    return result


# ═══════════════════════════════════════════════════════════
# Agent Self Stats
# ═══════════════════════════════════════════════════════════

@router.get("/agent-self/stats")
async def get_agent_self_stats():
    """Get agent self registry statistics."""
    result = agent_self_registry.get_stats() if hasattr(agent_self_registry, 'get_stats') else {}
    if isinstance(result, dict):
        result.setdefault("agent_id", "default")
    return result


# ═══════════════════════════════════════════════════════════
# IM Hub Stats
# ═══════════════════════════════════════════════════════════

@router.get("/im-hub/stats")
async def get_im_hub_stats():
    """Get IM hub statistics."""
    result = im_hub.get_stats() if hasattr(im_hub, 'get_stats') else {}
    if isinstance(result, dict):
        result.setdefault("total_channels", 0)
    return result


# ═══════════════════════════════════════════════════════════
# Task Queue Stats
# ═══════════════════════════════════════════════════════════

@router.get("/task-queue/stats")
async def get_task_queue_stats():
    """Get task queue statistics."""
    return task_queue.get_stats() if hasattr(task_queue, 'get_stats') else {}


# ═══════════════════════════════════════════════════════════
# Enterprise Stats
# ═══════════════════════════════════════════════════════════

@router.get("/enterprise/stats")
async def get_enterprise_stats():
    """Get enterprise hub statistics."""
    return enterprise_hub.get_hub_stats() if hasattr(enterprise_hub, 'get_hub_stats') else {}


# ═══════════════════════════════════════════════════════════
# Pipeline Stats
# ═══════════════════════════════════════════════════════════

@router.get("/pipeline/stats")
async def get_pipeline_stats():
    """Get pipeline engine statistics."""
    return pipeline_engine.get_stats() if hasattr(pipeline_engine, 'get_stats') else {}


# ═══════════════════════════════════════════════════════════
# Capability Stats
# ═══════════════════════════════════════════════════════════

@router.get("/capability/stats")
async def get_capability_stats():
    """Get capability registry statistics."""
    result = capability_registry.get_stats() if hasattr(capability_registry, 'get_stats') else {}
    if isinstance(result, dict):
        result.setdefault("total_domains", 0)
    return result


# ═══════════════════════════════════════════════════════════
# Knowledge Graph Stats
# ═══════════════════════════════════════════════════════════

@router.get("/knowledge/stats")
async def get_knowledge_stats():
    """Get knowledge graph statistics."""
    return knowledge_graph.get_stats() if hasattr(knowledge_graph, 'get_stats') else {"status": "active"}


# ═══════════════════════════════════════════════════════════
# MCP Stats
# ═══════════════════════════════════════════════════════════

@router.get("/mcp/stats")
async def get_mcp_stats():
    """Get MCP registry statistics."""
    servers = mcp_registry.get_server_states() if hasattr(mcp_registry, 'get_server_states') else []
    return {"servers": len(servers), "server_states": servers, "status": "active"}


# ═══════════════════════════════════════════════════════════
# Proactive Discovery Stats
# ═══════════════════════════════════════════════════════════

@router.get("/proactive/stats")
async def get_proactive_stats():
    """Get proactive discovery engine statistics."""
    from agent.proactive import ProactiveDiscoveryEngine
    # Get engine for a default agent
    agent_id = next(iter(orchestrator._engines), None)
    if agent_id:
        engine = orchestrator.get_engine(agent_id=agent_id, agent_name="Default", instructions="")
        if hasattr(engine, 'proactive') and hasattr(engine.proactive, 'get_stats'):
            return engine.proactive.get_stats()
    return {"status": "active", "tasks_detected": 0}


# ═══════════════════════════════════════════════════════════
# Evolution Stats
# ═══════════════════════════════════════════════════════════

@router.get("/evolution/stats")
async def get_evolution_stats():
    """Get agent evolution statistics."""
    from agent.agent_evolution import AgentEvolution
    agent_id = next(iter(orchestrator._engines), None)
    if agent_id:
        engine = orchestrator.get_engine(agent_id=agent_id, agent_name="Default", instructions="")
        if hasattr(engine, 'evolution') and hasattr(engine.evolution, 'get_stats'):
            return engine.evolution.get_stats()
    return {"status": "active", "experiences": 0}


# ═══════════════════════════════════════════════════════════
# Metacognition Stats
# ═══════════════════════════════════════════════════════════

@router.get("/metacognition/stats")
async def get_metacognition_stats():
    """Get metacognition engine statistics."""
    from agent.metacognition import MetaCognition
    agent_id = next(iter(orchestrator._engines), None)
    if agent_id:
        engine = orchestrator.get_engine(agent_id=agent_id, agent_name="Default", instructions="")
        if hasattr(engine, 'metacognition') and hasattr(engine.metacognition, 'get_stats'):
            return engine.metacognition.get_stats()
    return {"status": "active", "decisions": 0}


from agent.shared import intelligence, ReasoningStrategy


# ═══════════════════════════════════════════════════════════
# Agent Intelligence Core API
# ═══════════════════════════════════════════════════════════

@router.get("/intelligence/stats")
async def get_intelligence_stats():
    """Get agent intelligence core statistics."""
    return intelligence.get_stats()


@router.post("/intelligence/analyze")
async def analyze_task_intelligence(prompt: str = Query(..., min_length=1)):
    """Analyze a task for complexity, strategy, and tool recommendations."""
    tools = [t.name for t in tool_registry.list_tools()]
    return intelligence.analyze_task(prompt, tools)


@router.get("/intelligence/insights")
async def get_learning_insights():
    """Get learning insights from accumulated experiences."""
    return intelligence.get_learning_insights()


@router.get("/intelligence/experiences")
async def get_recent_experiences(limit: int = Query(10, ge=1, le=100)):
    """Replay recent learning experiences."""
    return {"experiences": intelligence.replay_experiences(limit)}


@router.post("/intelligence/plan-tools")
async def plan_tool_sequence(task: str = Query(..., min_length=1)):
    """Plan an optimal tool execution sequence for a task."""
    tools = [t.name for t in tool_registry.list_tools()]
    return {"sequence": intelligence.plan_tool_sequence(task, tools)}


@router.post("/intelligence/select-tools")
async def select_relevant_tools(prompt: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=20)):
    """Intelligently select the most relevant tools for a task."""
    available = tool_registry.list_tools()
    selected = intelligence.select_tools(prompt, available, limit)
    return {"tools": [{"name": t.name, "description": t.description} for t in selected]}


# ═══════════════════════════════════════════════════════════
# Activity Events API
# ═══════════════════════════════════════════════════════════

@router.get("/events")
async def get_recent_events(
    agent_id: str | None = None,
    type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    since: str | None = None,
):
    """Get recent events with optional filtering by agent_id, type, and time range.

    Args:
        agent_id: Filter events by agent ID.
        type: Filter by event type (e.g., 'agent.created', 'task.completed').
        limit: Maximum number of events to return.
        since: ISO 8601 timestamp to filter events after.
    """
    events = event_bus.get_history(limit=limit * 2)  # Get more to allow client-side filtering

    # Apply filters
    if agent_id:
        events = [e for e in events if e.get("source", "") == agent_id]
    if type:
        events = [e for e in events if e.get("type", "") == type]
    if since:
        events = [e for e in events if e.get("timestamp", "") >= since]

    events = events[:limit]

    return {"events": events, "count": len(events), "limit": limit}


@router.get("/events/stream")
async def stream_events(
    agent_id: str | None = None,
    type: str | None = None,
):
    """SSE stream of live events from the event bus.

    Clients connect to this endpoint to receive real-time event notifications
    as they occur in the system. Events are filtered by agent_id and type
    if provided.

    Args:
        agent_id: Only stream events for this agent.
        type: Only stream events of this type.
    """
    async def event_generator():
        event_queue: asyncio.Queue = asyncio.Queue()

        async def event_handler(event: Event):
            data = event.to_dict()
            # Apply filters
            if agent_id and data.get("source", "") != agent_id:
                return
            if type and data.get("type", "") != type:
                return
            await event_queue.put(data)

        event_bus.subscribe_all(event_handler)

        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Event stream started'})}\n\n"

            while True:
                try:
                    event_data = await asyncio.wait_for(event_queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            event_bus.unsubscribe(None, event_handler)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/events/stats")
async def get_event_stats():
    """Get event statistics by type and agent."""
    bus_stats = event_bus.get_stats()
    return {
        "total_events": bus_stats["total_events"],
        "type_counts": bus_stats["type_counts"],
        "listener_count": bus_stats["listener_count"],
        "pending_tasks": bus_stats["pending_tasks"],
    }


# ═══════════════════════════════════════════════════════════
# Runtime Status API
# ═══════════════════════════════════════════════════════════

@router.get("/runtime/status")
async def get_runtime_status():
    """Get status of all running agents and system components."""
    agents_status = []
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.is_active == True)
        )
        agents = result.scalars().all()
        for a in agents:
            try:
                engine = orchestrator.get_engine(
                    agent_id=a.id,
                    agent_name=a.name,
                    instructions=a.instructions or "",
                )
                agents_status.append({
                    "agent_id": a.id,
                    "name": a.name,
                    "role": a.role,
                    "is_active": a.is_active,
                    "dream_running": engine.dream.is_running,
                    "iteration_remaining": engine.iteration_budget.remaining,
                    "total_tokens": engine.total_tokens,
                    "tool_executions": getattr(engine, 'tool_execution_count', 0),
                })
            except Exception:
                agents_status.append({
                    "agent_id": a.id,
                    "name": a.name,
                    "role": a.role,
                    "is_active": a.is_active,
                    "error": "Failed to get engine status",
                })

    ws_stats = ws_manager.get_stats()

    return {
        "agents": agents_status,
        "total_agents": len(agents_status),
        "websocket": {
            "active_connections": ws_stats["active_connections"],
            "total_rooms": ws_stats["total_rooms"],
            "max_connections": ws_stats["max_connections"],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/runtime/agents/{agent_id}/status")
async def get_agent_runtime_status(agent_id: str):
    """Get specific agent runtime status."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        a = result.scalars().first()
        if not a:
            raise HTTPException(404, "Agent not found")

    try:
        engine = orchestrator.get_engine(
            agent_id=a.id,
            agent_name=a.name,
            instructions=a.instructions or "",
        )
        return {
            "agent_id": a.id,
            "name": a.name,
            "role": a.role,
            "is_active": a.is_active,
            "dream": {
                "is_running": engine.dream.is_running,
                "interval_seconds": engine.dream.interval,
                "total_insights": engine.dream.insights_count,
            },
            "iteration": {
                "remaining": engine.iteration_budget.remaining,
                "is_exhausted": engine.iteration_budget.is_exhausted,
                "usage_ratio": engine.iteration_budget.usage_ratio,
            },
            "tokens": {
                "total": engine.total_tokens,
            },
            "tools": {
                "executions": getattr(engine, 'tool_execution_count', 0),
                "successful": getattr(engine, 'tool_success_count', 0),
                "failed": getattr(engine, 'tool_failure_count', 0),
            },
            "soul_profile": {
                "identity": engine.soul_profile.identity,
                "principles": engine.soul_profile.principles,
                "communication_style": engine.soul_profile.communication_style,
                "boundaries": engine.soul_profile.boundaries,
                "goals": engine.soul_profile.goals,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "agent_id": a.id,
            "name": a.name,
            "error": f"Failed to get engine status: {str(e)}",
        }


@router.post("/runtime/agents/{agent_id}/restart")
async def restart_agent(agent_id: str):
    """Restart an agent's runtime engine."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        a = result.scalars().first()
        if not a:
            raise HTTPException(404, "Agent not found")

    try:
        engine = orchestrator.get_engine(
            agent_id=a.id,
            agent_name=a.name,
            instructions=a.instructions or "",
        )
        # Reset iteration budget and clear state
        engine.iteration_budget.reset()
        engine.total_tokens = 0
        engine.tool_execution_count = 0
        engine.tool_success_count = 0
        engine.tool_failure_count = 0

        # Broadcast status change
        await ws_manager.broadcast_agent_status(agent_id, "restarted")

        return {
            "agent_id": agent_id,
            "restarted": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to restart agent: {str(e)}")


@router.post("/runtime/agents/{agent_id}/pause")
async def pause_agent(agent_id: str):
    """Pause an agent's background processes (dream, autopilot)."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        a = result.scalars().first()
        if not a:
            raise HTTPException(404, "Agent not found")

    try:
        engine = orchestrator.get_engine(
            agent_id=a.id,
            agent_name=a.name,
            instructions=a.instructions or "",
        )
        if engine.dream.is_running:
            await engine.dream.stop()
        await ws_manager.broadcast_agent_status(agent_id, "paused")

        return {
            "agent_id": agent_id,
            "paused": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to pause agent: {str(e)}")


@router.post("/runtime/agents/{agent_id}/resume")
async def resume_agent(agent_id: str):
    """Resume an agent's background processes."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        a = result.scalars().first()
        if not a:
            raise HTTPException(404, "Agent not found")

    try:
        engine = orchestrator.get_engine(
            agent_id=a.id,
            agent_name=a.name,
            instructions=a.instructions or "",
        )
        if not engine.dream.is_running:
            await engine.dream.start()
        await ws_manager.broadcast_agent_status(agent_id, "resumed")

        return {
            "agent_id": agent_id,
            "resumed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to resume agent: {str(e)}")


# ═══════════════════════════════════════════════════════════
# Soul Profile API
# ═══════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/soul")
async def get_agent_soul(agent_id: str):
    """Get agent's soul profile."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        a = result.scalars().first()
        if not a:
            raise HTTPException(404, "Agent not found")

    engine = orchestrator.get_engine(
        agent_id=a.id,
        agent_name=a.name,
        instructions=a.instructions or "",
    )

    return {
        "agent_id": agent_id,
        "soul": {
            "identity": engine.soul_profile.identity,
            "principles": engine.soul_profile.principles,
            "communication_style": engine.soul_profile.communication_style,
            "boundaries": engine.soul_profile.boundaries,
            "goals": engine.soul_profile.goals,
        },
    }


@router.put("/agents/{agent_id}/soul")
async def update_agent_soul(agent_id: str, data: SoulProfileUpdate):
    """Update agent's soul profile."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        a = result.scalars().first()
        if not a:
            raise HTTPException(404, "Agent not found")

    engine = orchestrator.get_engine(
        agent_id=a.id,
        agent_name=a.name,
        instructions=a.instructions or "",
    )

    update_kwargs = {}
    if data.identity is not None:
        update_kwargs["identity"] = data.identity
    if data.principles is not None:
        update_kwargs["principles"] = data.principles
    if data.communication_style is not None:
        update_kwargs["communication_style"] = data.communication_style
    if data.boundaries is not None:
        update_kwargs["boundaries"] = data.boundaries
    if data.goals is not None:
        update_kwargs["goals"] = data.goals

    if update_kwargs:
        engine.update_soul_profile(**update_kwargs)

    return {
        "agent_id": agent_id,
        "soul": {
            "identity": engine.soul_profile.identity,
            "principles": engine.soul_profile.principles,
            "communication_style": engine.soul_profile.communication_style,
            "boundaries": engine.soul_profile.boundaries,
            "goals": engine.soul_profile.goals,
        },
    }


@router.get("/agents/{agent_id}/scheduled-tasks")
async def list_scheduled_tasks(agent_id: str):
    """List scheduled tasks for an agent."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        if not result.scalars().first():
            raise HTTPException(404, "Agent not found")

    all_tasks = buddy_scheduler.list_tasks()
    agent_tasks = [t for t in all_tasks if t.get("agent_id", "") == agent_id]

    return {
        "agent_id": agent_id,
        "tasks": agent_tasks,
        "count": len(agent_tasks),
    }


@router.post("/agents/{agent_id}/scheduled-tasks", status_code=201)
async def create_scheduled_task(agent_id: str, data: ScheduledTaskCreate):
    """Create a new scheduled task for an agent."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        if not result.scalars().first():
            raise HTTPException(404, "Agent not found")

    try:
        task = buddy_scheduler.schedule(
            name=data.name,
            prompt=data.prompt,
            agent_id=agent_id,
            cron_expression=data.cron_expression,
            interval_seconds=data.interval_seconds,
            description=data.description,
        )
        return task.to_dict()
    except Exception as e:
        raise HTTPException(400, f"Failed to create scheduled task: {str(e)}")


@router.delete("/agents/{agent_id}/scheduled-tasks/{task_id}", status_code=204)
async def delete_scheduled_task(agent_id: str, task_id: str):
    """Delete a scheduled task."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        if not result.scalars().first():
            raise HTTPException(404, "Agent not found")

    task = buddy_scheduler.get_task(task_id)
    if not task:
        raise HTTPException(404, "Scheduled task not found")

    removed = buddy_scheduler.registry.remove_task(task_id)
    if not removed:
        raise HTTPException(404, "Failed to remove scheduled task")


@router.post("/agents/{agent_id}/scheduled-tasks/{task_id}/run")
async def run_scheduled_task_now(agent_id: str, task_id: str):
    """Run a scheduled task immediately."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        if not result.scalars().first():
            raise HTTPException(404, "Agent not found")

    task = buddy_scheduler.get_task(task_id)
    if not task:
        raise HTTPException(404, "Scheduled task not found")

    try:
        # Trigger immediate execution via the engine
        await buddy_scheduler.engine._execute_task(task)
        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "executed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to execute task: {str(e)}")


# ═══════════════════════════════════════════════════════════
# Agent Self Identity
# ═══════════════════════════════════════════════════════════

from agent.agent_self import agent_self_registry, SelfTraitCategory, TraitOrigin


@router.get("/agents/{agent_id}/self/profile")
async def get_agent_self_profile(agent_id: str):
    """Get the self identity profile for an agent."""
    agent_self = agent_self_registry.get_or_create(agent_id)
    return agent_self.get_self_profile()


@router.get("/agents/{agent_id}/self/stats")
async def get_agent_self_stats(agent_id: str):
    """Get self identity statistics for an agent."""
    agent_self = agent_self_registry.get_or_create(agent_id)
    return agent_self.get_stats()


@router.post("/agents/{agent_id}/self/snapshot")
async def create_agent_self_snapshot(agent_id: str):
    """Create a self identity snapshot for an agent."""
    agent_self = agent_self_registry.get_or_create(agent_id)
    snapshot = agent_self.create_snapshot()
    return {
        "id": snapshot.id,
        "timestamp": snapshot.timestamp,
        "trait_count": snapshot.trait_count,
        "pattern_count": snapshot.pattern_count,
        "dominant_categories": snapshot.dominant_categories,
        "evolution_step": snapshot.evolution_step,
    }


@router.post("/agents/{agent_id}/self/observe")
async def observe_agent_interaction(
    agent_id: str,
    user_message: str = Query(..., min_length=1),
    agent_response: str = Query(default=""),
    topic: str = Query(default=""),
    sentiment: str = Query(default=""),
    complexity: str = Query(default=""),
):
    """Record an observed interaction for self identity learning."""
    agent_self = agent_self_registry.get_or_create(agent_id)
    context = {}
    if topic:
        context["topic"] = topic
    if sentiment:
        context["sentiment"] = sentiment
    if complexity:
        context["complexity"] = complexity
    agent_self.observe_interaction(user_message, agent_response, context)
    return {"agent_id": agent_id, "observed": True}


@router.get("/agents/{agent_id}/self/export")
async def export_agent_self(agent_id: str):
    """Export the full agent self model."""
    agent_self = agent_self_registry.get_or_create(agent_id)
    return agent_self.export_self()


@router.post("/agents/{agent_id}/self/import")
async def import_agent_self(agent_id: str, data: dict):
    """Import an agent self model."""
    agent_self = agent_self_registry.get_or_create(agent_id)
    agent_self.import_self(data)
    return agent_self.get_stats()


@router.get("/agent-self/registry")
async def list_agent_selves():
    """List all agent selves in the registry."""
    return {"agents": agent_self_registry.list_all()}


# ═══════════════════════════════════════════════════════════
# Plugin System
# ═══════════════════════════════════════════════════════════

from agent.plugin_system import plugin_system, PluginManifest, PluginPermission, PluginStatus


@router.get("/plugins")
async def list_plugins(
    status: str = Query(default=""),
):
    """List all registered plugins."""
    status_filter = PluginStatus(status) if status else None
    return {"plugins": plugin_system.list_plugins(status_filter)}


@router.get("/plugins/stats")
async def get_plugin_stats():
    """Get plugin system statistics."""
    return plugin_system.get_stats()


@router.post("/plugins/register")
async def register_plugin(data: dict):
    """Register a new plugin manifest."""
    manifest = PluginManifest(
        id=data["id"],
        name=data["name"],
        version=data.get("version", "1.0.0"),
        description=data.get("description", ""),
        author=data.get("author", ""),
        homepage=data.get("homepage", ""),
        permissions=[PluginPermission(p) for p in data.get("permissions", [])],
        capabilities=data.get("capabilities", []),
        entry_point=data.get("entry_point", ""),
        tags=data.get("tags", []),
    )
    instance = plugin_system.register_manifest(manifest)
    return {"id": instance.manifest.id, "status": instance.status.value}


@router.post("/plugins/{plugin_id}/install")
async def install_plugin(plugin_id: str):
    """Install a registered plugin."""
    success = await plugin_system.install(plugin_id)
    return {"plugin_id": plugin_id, "installed": success}


@router.post("/plugins/{plugin_id}/activate")
async def activate_plugin(plugin_id: str):
    """Activate an installed plugin."""
    success = await plugin_system.activate(plugin_id)
    return {"plugin_id": plugin_id, "activated": success}


@router.post("/plugins/{plugin_id}/deactivate")
async def deactivate_plugin(plugin_id: str):
    """Deactivate an active plugin."""
    success = await plugin_system.deactivate(plugin_id)
    return {"plugin_id": plugin_id, "deactivated": success}


@router.delete("/plugins/{plugin_id}")
async def uninstall_plugin(plugin_id: str):
    """Uninstall a plugin."""
    await plugin_system.uninstall(plugin_id)
    return {"plugin_id": plugin_id, "uninstalled": True}


# ═══════════════════════════════════════════════════════════
# IM Integration Hub
# ═══════════════════════════════════════════════════════════

from agent.im_hub import im_hub, IMPlatform, IMChannelConfig


@router.get("/im/stats")
async def get_im_hub_stats():
    """Get IM Hub statistics."""
    return im_hub.get_stats()


@router.get("/im/platforms")
async def list_im_platforms():
    """List all IM platforms and their statuses."""
    return {
        "platforms": [
            im_hub.get_platform_status(p) for p in IMPlatform
        ]
    }


@router.get("/im/messages")
async def get_im_messages(
    platform: str = Query(default=""),
    limit: int = Query(50, ge=1, le=200),
):
    """Get recent IM messages."""
    plat = IMPlatform(platform) if platform else None
    return {"messages": im_hub.get_recent_messages(plat, limit)}


@router.post("/im/platforms/configure")
async def configure_im_platform(data: dict):
    """Configure an IM platform for connection."""
    config = IMChannelConfig(
        platform=IMPlatform(data["platform"]),
        enabled=data.get("enabled", False),
        bot_token=data.get("bot_token", ""),
        app_id=data.get("app_id", ""),
        app_secret=data.get("app_secret", ""),
        webhook_url=data.get("webhook_url", ""),
        allowed_chat_ids=data.get("allowed_chat_ids", []),
        auto_reply=data.get("auto_reply", True),
    )
    im_hub.configure_platform(config)
    return {"platform": config.platform.value, "configured": True}


@router.post("/im/platforms/{platform}/connect")
async def connect_im_platform(platform: str):
    """Connect to an IM platform."""
    success = await im_hub.connect_platform(IMPlatform(platform))
    return {"platform": platform, "connected": success}


@router.post("/im/platforms/{platform}/disconnect")
async def disconnect_im_platform(platform: str):
    """Disconnect from an IM platform."""
    await im_hub.disconnect_platform(IMPlatform(platform))
    return {"platform": platform, "disconnected": True}


@router.post("/im/send")
async def send_im_message(
    platform: str = Query(...),
    chat_id: str = Query(...),
    text: str = Query(..., min_length=1),
):
    """Send a message through an IM platform."""
    success = await im_hub.send_to_chat(IMPlatform(platform), chat_id, text)
    return {"sent": success}


@router.post("/im/chats/assign")
async def assign_agent_to_im_chat(
    chat_id: str = Query(...),
    agent_id: str = Query(...),
):
    """Assign a Buddy agent to handle messages from an IM chat."""
    im_hub.assign_agent_to_chat(chat_id, agent_id)
    return {"chat_id": chat_id, "agent_id": agent_id, "assigned": True}


# ═══════════════════════════════════════════════════════════
# Skills Marketplace
# ═══════════════════════════════════════════════════════════

from agent.skills_marketplace import skills_marketplace, MarketplaceSkill, SkillCategory, SkillPricing, SkillReview


@router.get("/marketplace/stats")
async def get_marketplace_stats():
    """Get skills marketplace statistics."""
    return skills_marketplace.get_stats()


@router.get("/marketplace/skills")
async def search_marketplace_skills(
    query: str = Query(default=""),
    category: str = Query(default=""),
    tags: str = Query(default=""),
    pricing: str = Query(default=""),
    sort_by: str = Query(default="rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Search and browse marketplace skills."""
    cat = SkillCategory(category) if category else None
    tag_list = tags.split(",") if tags else None
    price = SkillPricing(pricing) if pricing else None
    return skills_marketplace.search_skills(
        query=query, category=cat, tags=tag_list,
        pricing=price, sort_by=sort_by, page=page, page_size=page_size
    )


@router.get("/marketplace/skills/featured")
async def get_featured_skills():
    """Get featured marketplace skills."""
    return {"skills": skills_marketplace.get_featured_skills()}


@router.get("/marketplace/skills/{skill_id}")
async def get_marketplace_skill(skill_id: str):
    """Get a specific marketplace skill."""
    skill = skills_marketplace.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, f"Skill {skill_id} not found")
    return skills_marketplace._skill_to_dict(skill)


@router.post("/marketplace/skills/publish")
async def publish_marketplace_skill(data: dict):
    """Publish a new skill to the marketplace."""
    skill = MarketplaceSkill(
        id="",
        name=data["name"],
        description=data.get("description", ""),
        category=SkillCategory(data.get("category", "utility")),
        version=data.get("version", "1.0.0"),
        author=data.get("author", ""),
        author_id=data.get("author_id", ""),
        tags=data.get("tags", []),
        dependencies=data.get("dependencies", []),
        prompt_template=data.get("prompt_template", ""),
        tool_requirements=data.get("tool_requirements", []),
    )
    published = skills_marketplace.publish_skill(skill)
    return skills_marketplace._skill_to_dict(published)


@router.post("/marketplace/skills/{skill_id}/review")
async def review_marketplace_skill(skill_id: str, data: dict):
    """Add a review for a marketplace skill."""
    if skill_id not in skills_marketplace._skills:
        raise HTTPException(404, f"Skill {skill_id} not found")
    review = SkillReview(
        id="",
        skill_id=skill_id,
        reviewer_id=data.get("reviewer_id", ""),
        reviewer_name=data.get("reviewer_name", "Anonymous"),
        rating=float(data["rating"]),
        title=data.get("title", ""),
        content=data.get("content", ""),
    )
    result = skills_marketplace.add_review(review)
    return {"id": result.id, "rating": result.rating, "created_at": result.created_at}


@router.get("/marketplace/skills/{skill_id}/reviews")
async def get_marketplace_reviews(
    skill_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    """Get reviews for a marketplace skill."""
    return skills_marketplace.get_reviews(skill_id, page, page_size)


@router.get("/marketplace/publishers/{publisher_id}")
async def get_marketplace_publisher(publisher_id: str):
    """Get a publisher profile."""
    pub = skills_marketplace.get_publisher(publisher_id)
    if not pub:
        raise HTTPException(404, f"Publisher {publisher_id} not found")
    return pub


@router.get("/marketplace/categories")
async def get_marketplace_categories():
    """Get marketplace category statistics."""
    return {"categories": skills_marketplace.get_categories()}


@router.post("/marketplace/skills/{skill_id}/download")
async def record_skill_download(skill_id: str):
    """Record a download of a marketplace skill."""
    skills_marketplace.record_download(skill_id)
    return {"skill_id": skill_id, "recorded": True}


# ═══════════════════════════════════════════════════════════
# Task Queue
# ═══════════════════════════════════════════════════════════

from agent.task_queue import task_queue, JobType, JobPriority, JobStatus as TQJobStatus


@router.get("/queue/stats")
async def get_task_queue_stats():
    """Get task queue statistics."""
    return task_queue.get_stats()


@router.get("/queue/jobs")
async def list_queued_jobs(
    status: str = Query(default=""),
    job_type: str = Query(default=""),
    priority: str = Query(default=""),
    agent_id: str = Query(default=""),
    limit: int = Query(50, ge=1, le=200),
):
    """List queued jobs with optional filtering."""
    s = TQJobStatus(status) if status else None
    t = JobType(job_type) if job_type else None
    p = JobPriority(priority) if priority else None
    return {"jobs": task_queue.list_jobs(status=s, job_type=t, priority=p, agent_id=agent_id, limit=limit)}


@router.get("/queue/jobs/{job_id}")
async def get_queued_job(job_id: str):
    """Get a specific queued job."""
    job = task_queue.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return task_queue._job_to_dict(job)


@router.post("/queue/jobs/submit")
async def submit_job(data: dict):
    """Submit a new job to the queue."""
    job = task_queue.submit(
        name=data["name"],
        job_type=JobType(data.get("job_type", "custom")),
        payload=data.get("payload", {}),
        priority=JobPriority(data.get("priority", "normal")),
        agent_id=data.get("agent_id", ""),
        max_retries=data.get("max_retries", 3),
        timeout_seconds=data.get("timeout_seconds", 300),
        tags=data.get("tags", []),
    )
    return task_queue._job_to_dict(job)


@router.post("/queue/jobs/batch")
async def submit_batch_jobs(data: dict):
    """Submit a batch of related jobs."""
    batch = task_queue.submit_batch(
        name=data["name"],
        jobs=data.get("jobs", []),
        priority=JobPriority(data.get("priority", "normal")),
        agent_id=data.get("agent_id", ""),
    )
    return {
        "id": batch.id,
        "name": batch.name,
        "total_jobs": batch.total_jobs,
        "status": batch.status,
    }


@router.get("/queue/batches")
async def list_batches(limit: int = Query(20, ge=1, le=100)):
    """List batch jobs."""
    return {"batches": task_queue.list_batches(limit)}


@router.get("/queue/batches/{batch_id}")
async def get_batch(batch_id: str):
    """Get a batch by ID."""
    batch = task_queue.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, f"Batch {batch_id} not found")
    return {
        "id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "progress": round(batch.progress, 2),
        "total_jobs": batch.total_jobs,
        "completed_jobs": batch.completed_jobs,
        "failed_jobs": batch.failed_jobs,
        "job_ids": batch.job_ids,
    }


@router.post("/queue/jobs/{job_id}/cancel")
async def cancel_queued_job(job_id: str):
    """Cancel a pending or queued job."""
    success = task_queue.cancel_job(job_id)
    return {"job_id": job_id, "cancelled": success}


@router.put("/queue/jobs/{job_id}/progress")
async def update_job_progress(
    job_id: str,
    progress: float = Query(..., ge=0.0, le=1.0),
    message: str = Query(default=""),
):
    """Update the progress of a running job."""
    task_queue.update_progress(job_id, progress, message)
    return {"job_id": job_id, "progress": progress, "updated": True}


# ═══════════════════════════════════════════════════════════
# Agent Runtime Backend
# ═══════════════════════════════════════════════════════════

from agent.runtime_backend import runtime_backend_hub, RuntimeBackendKind, RuntimeConfig


@router.get("/runtime-backend/stats")
async def get_runtime_backend_stats():
    """Get runtime backend hub statistics."""
    result = runtime_backend_hub.get_stats()
    if isinstance(result, dict):
        result.setdefault("total_backends", 0)
    return result


@router.get("/runtime-backend/backends")
async def list_runtime_backends():
    """List available runtime backends."""
    return {"backends": runtime_backend_hub.list_backends()}


@router.get("/runtime-backend/instances")
async def list_runtime_instances(agent_id: str = Query(default="")):
    """List runtime instances."""
    return {"instances": runtime_backend_hub.list_instances(agent_id)}


@router.get("/runtime-backend/instances/{instance_id}")
async def get_runtime_instance(instance_id: str):
    """Get a specific runtime instance."""
    instance = runtime_backend_hub.get_instance(instance_id)
    if not instance:
        raise HTTPException(404, f"Instance {instance_id} not found")
    return {
        "id": instance.id,
        "backend": instance.backend.value,
        "status": instance.status.value,
        "agent_id": instance.agent_id,
        "created_at": instance.created_at,
        "started_at": instance.started_at,
        "error": instance.error_message,
    }


@router.post("/runtime-backend/instances/create")
async def create_runtime_instance(data: dict):
    """Create a new runtime instance."""
    config = RuntimeConfig(
        backend=RuntimeBackendKind(data.get("backend", "buddy_native")),
        workspace_dir=data.get("workspace_dir", ""),
        environment_vars=data.get("environment_vars", {}),
        installed_packages=data.get("installed_packages", []),
        max_memory_mb=data.get("max_memory_mb", 512),
        max_cpu_cores=data.get("max_cpu_cores", 2),
        timeout_seconds=data.get("timeout_seconds", 3600),
    )
    instance = await runtime_backend_hub.create_instance(
        agent_id=data.get("agent_id", ""),
        backend=RuntimeBackendKind(data.get("backend", "buddy_native")),
        config=config,
    )
    return {
        "id": instance.id,
        "backend": instance.backend.value,
        "status": instance.status.value,
        "agent_id": instance.agent_id,
    }


@router.post("/runtime-backend/instances/{instance_id}/execute")
async def execute_in_runtime(instance_id: str, data: dict):
    """Execute an agent operation in a runtime instance."""
    result = await runtime_backend_hub.execute(
        instance_id,
        agent_config=data.get("agent_config", {}),
        input_data=data.get("input_data", {}),
    )
    return result


@router.get("/runtime-backend/instances/{instance_id}/metrics")
async def get_runtime_metrics(instance_id: str):
    """Get runtime instance metrics."""
    return await runtime_backend_hub.get_metrics(instance_id)


@router.delete("/runtime-backend/instances/{instance_id}")
async def terminate_runtime_instance(instance_id: str):
    """Terminate a runtime instance."""
    await runtime_backend_hub.terminate_instance(instance_id)
    return {"instance_id": instance_id, "terminated": True}


# ═══════════════════════════════════════════════════════════
# Agent Core API
# ═══════════════════════════════════════════════════════════

from agent.shared import AgentCore, AgentCoreConfig, AgentState, ExecutionContext, AgentCapability, agent_synthesis

# Global agent core instances
_agent_cores: dict[str, AgentCore] = {}


def _get_or_create_core(agent_id: str, agent_name: str = "Buddy") -> AgentCore:
    """Get or create an agent core instance."""
    if agent_id not in _agent_cores:
        _agent_cores[agent_id] = AgentCore(
            agent_id=agent_id,
            agent_name=agent_name,
            config=AgentCoreConfig(
                enable_metacognition=True,
                enable_evolution=True,
                enable_proactive=True,
                enable_checkpoints=True,
            ),
        )
    return _agent_cores[agent_id]


@router.get("/agent-core/stats")
async def get_agent_core_stats(agent_id: str = Query("default", min_length=1)):
    """Get comprehensive agent core statistics."""
    core = _get_or_create_core(agent_id)
    return core.get_stats()


@router.get("/agent-core/traces")
async def get_agent_core_traces(
    agent_id: str = Query("default", min_length=1),
    limit: int = Query(10, ge=1, le=100),
):
    """Get recent execution traces from the agent core."""
    core = _get_or_create_core(agent_id)
    return {"traces": core.get_recent_traces(limit)}


@router.get("/agent-core/insights")
async def get_agent_core_insights(
    agent_id: str = Query("default", min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get learned insights from the agent core."""
    core = _get_or_create_core(agent_id)
    return {"insights": core.get_insights(limit)}


@router.post("/agent-core/generate-insights")
async def generate_agent_core_insights(agent_id: str = Query("default", min_length=1)):
    """Generate new insights from accumulated execution history."""
    core = _get_or_create_core(agent_id)
    insights = core.generate_insights()
    return {"generated": len(insights), "insights": [
        {"id": i.id, "category": i.category, "content": i.content, "confidence": round(i.confidence, 3)}
        for i in insights
    ]}


@router.get("/agent-core/proactive-signals")
async def get_proactive_signals(
    agent_id: str = Query("default", min_length=1),
    limit: int = Query(10, ge=1, le=50),
):
    """Get proactive signals detected by the agent core."""
    core = _get_or_create_core(agent_id)
    core.scan_proactive_signals()
    return {"signals": core.get_proactive_signals(limit)}


@router.post("/agent-core/analyze")
async def analyze_with_core(prompt: str = Query(..., min_length=1), agent_id: str = Query("default", min_length=1)):
    """Analyze a task using the agent core's strategy selection."""
    core = _get_or_create_core(agent_id)
    result = await core.select_strategy(prompt)
    tools = core.score_tools(prompt, [t.name for t in tool_registry.list_tools()])
    return {
        "fingerprint": result["fingerprint"],
        "strategy": result["strategy"],
        "source": result["source"],
        "confidence": result["confidence"],
        "relevant_tools": tools[:5],
    }


@router.post("/agent-core/plan-sequence")
async def plan_with_core(task: str = Query(..., min_length=1), agent_id: str = Query("default", min_length=1)):
    """Plan a tool execution sequence using the agent core."""
    core = _get_or_create_core(agent_id)
    tools = [t.name for t in tool_registry.list_tools()]
    return {"sequence": core.plan_tool_sequence(task, tools)}


@router.post("/agent-core/learn")
async def record_agent_learning(
    agent_id: str = Query(..., min_length=1),
    prompt: str = Query(..., min_length=1),
    success: bool = Query(True),
    tools_used: str = Query(""),
):
    """Record a learning event for the agent core."""
    core = _get_or_create_core(agent_id)
    trace = core.start_execution(ExecutionContext.CHAT, prompt)
    trace.success = success
    if tools_used:
        trace.tools_used = tools_used.split(",")
    core.learn_from_execution(trace)
    return {"agent_id": agent_id, "recorded": True}


@router.post("/agent-core/checkpoint")
async def save_agent_checkpoint(
    agent_id: str = Query("default", min_length=1),
    name: str = Query("manual", min_length=1),
):
    """Save a checkpoint of the agent core's state."""
    core = _get_or_create_core(agent_id)
    checkpoint_id = core.save_checkpoint(name, {"state": core.get_stats()})
    return {"checkpoint_id": checkpoint_id, "agent_id": agent_id}


# ═══════════════════════════════════════════════════════════
# Agent Synthesis API
# ═══════════════════════════════════════════════════════════

@router.get("/synthesis/stats")
async def get_synthesis_stats():
    """Get agent synthesis engine statistics."""
    return agent_synthesis.get_stats()


@router.get("/synthesis/reports")
async def get_synthesis_reports(limit: int = Query(5, ge=1, le=50)):
    """Get recent synthesis reports."""
    return {"reports": agent_synthesis.get_recent_reports(limit)}


@router.post("/synthesis/contribute")
async def contribute_to_synthesis(
    agent_id: str = Query(..., min_length=1),
    agent_name: str = Query("Buddy", min_length=1),
    insight_type: str = Query("strategy", min_length=1),
    content: str = Query(..., min_length=1),
    confidence: float = Query(0.5, ge=0.0, le=1.0),
):
    """Submit an agent's insight for cross-agent synthesis."""
    from agent.agent_synthesis import InsightType
    try:
        it = InsightType(insight_type)
    except ValueError:
        it = InsightType.STRATEGY
    contrib = agent_synthesis.contribute(agent_id, agent_name, it, content, confidence)
    return {
        "contribution_id": contrib.agent_id,
        "insight_type": contrib.insight_type.value,
        "confidence": contrib.confidence,
    }


@router.post("/synthesis/synthesize")
async def run_synthesis(mode: str = Query("aggregate", min_length=1)):
    """Run a synthesis cycle across all agent contributions."""
    from agent.agent_synthesis import SynthesisMode
    try:
        sm = SynthesisMode(mode)
    except ValueError:
        sm = SynthesisMode.AGGREGATE
    report = agent_synthesis.synthesize(sm)
    return {
        "report_id": report.id,
        "total_agents": report.total_agents,
        "insights": len(report.insights),
        "conflicts": len(report.conflicts),
        "emergent_patterns": report.emergent_patterns,
    }


@router.get("/synthesis/recommendations/{agent_id}")
async def get_agent_recommendations(agent_id: str):
    """Get cross-agent learning recommendations for a specific agent."""
    return {"recommendations": agent_synthesis.get_agent_recommendations(agent_id)}


@router.get("/synthesis/conflicts")
async def get_synthesis_conflicts(limit: int = Query(20, ge=1, le=100)):
    """Get detected knowledge conflicts between agents."""
    conflicts = agent_synthesis._conflicts[-limit:]
    return {
        "conflicts": [
            {
                "id": c.id,
                "topic": c.topic,
                "agent_a": c.agent_a,
                "agent_b": c.agent_b,
                "resolved": c.resolved,
                "resolution": c.resolution,
                "timestamp": c.timestamp,
            }
            for c in conflicts
        ]
    }


# ═══════════════════════════════════════════════════════════
# Agent Runtime API — unified lifecycle and execution management
# ═══════════════════════════════════════════════════════════

from agent.agent_runtime import (
    runtime_registry, AgentRuntime, RuntimeConfig, RuntimeState as RtState,
    ExecutionMode as RtExecMode, RuntimeEventType,
)


@router.get("/runtime/registry")
async def get_runtime_registry():
    """Get all active runtime instances."""
    return {
        "runtimes": runtime_registry.list_all(),
        "active_count": runtime_registry.active_count,
        "total_executions": runtime_registry.total_executions,
    }


@router.get("/runtime/{agent_id}/stats")
async def get_runtime_stats(agent_id: str):
    """Get comprehensive runtime statistics for an agent."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    return runtime.get_stats()


@router.get("/runtime/{agent_id}/executions")
async def get_runtime_executions(agent_id: str, limit: int = Query(10, ge=1, le=100)):
    """Get recent execution history for an agent runtime."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    return {"executions": runtime.get_recent_executions(limit)}


@router.get("/runtime/{agent_id}/checkpoints")
async def get_runtime_checkpoints(agent_id: str):
    """List all checkpoints for an agent runtime."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    return {"checkpoints": runtime.list_checkpoints()}


@router.post("/runtime/{agent_id}/checkpoint")
async def save_runtime_checkpoint(agent_id: str, name: str = Query("manual", min_length=1)):
    """Save a runtime checkpoint."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    checkpoint_id = await runtime.save_checkpoint(name)
    return {"checkpoint_id": checkpoint_id, "agent_id": agent_id, "saved": True}


@router.post("/runtime/{agent_id}/pause")
async def pause_runtime(agent_id: str):
    """Pause an agent runtime."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    runtime.pause()
    return {"agent_id": agent_id, "state": runtime.state.value}


@router.post("/runtime/{agent_id}/resume")
async def resume_runtime(agent_id: str):
    """Resume a paused agent runtime."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    runtime.resume()
    return {"agent_id": agent_id, "state": runtime.state.value}


@router.post("/runtime/{agent_id}/refill-tokens")
async def refill_runtime_tokens(agent_id: str, count: int = Query(10000, ge=1)):
    """Refill the token budget for an agent runtime."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    runtime.refill_tokens(count)
    return {"agent_id": agent_id, "token_budget_remaining": runtime.token_budget_remaining}


@router.post("/runtime/{agent_id}/shutdown")
async def shutdown_runtime(agent_id: str):
    """Shutdown an agent runtime."""
    await runtime_registry.remove(agent_id)
    return {"agent_id": agent_id, "shutdown": True}


@router.get("/runtime/{agent_id}/events")
async def get_runtime_events(agent_id: str, limit: int = Query(20, ge=1, le=100)):
    """Get recent events from an agent runtime (non-destructive peek)."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    events = []
    # Peek at events without consuming them
    for _ in range(min(limit, runtime._event_queue.qsize())):
        try:
            event = runtime._event_queue.get_nowait()
            events.append({
                "id": event.id,
                "type": event.event_type.value,
                "data": event.data,
                "timestamp": event.timestamp,
            })
            runtime._event_queue.put_nowait(event)  # Put back
        except asyncio.QueueEmpty:
            break
    return {"events": events, "agent_id": agent_id}


@router.get("/runtime/{agent_id}/intelligence")
async def get_runtime_intelligence(agent_id: str):
    """Get intelligence core statistics for an agent runtime."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    intelligence = runtime.get_intelligence()
    return intelligence.get_stats()


@router.get("/runtime/{agent_id}/agent-core")
async def get_runtime_agent_core(agent_id: str):
    """Get agent core statistics for an agent runtime."""
    runtime = runtime_registry.get(agent_id)
    if not runtime:
        raise HTTPException(404, f"Runtime not found for agent {agent_id}")
    core = runtime.get_agent_core()
    return core.get_stats()


# ═══════════════════════════════════════════════════════════
# System Dashboard API — unified platform monitoring
# ═══════════════════════════════════════════════════════════

@router.get("/system/dashboard")
async def get_system_dashboard():
    """Get unified system dashboard with all platform metrics."""
    from agent.shared import (
        platform_hub, cost_tracker, enterprise_hub, session_searcher,
        memory_sync_hub, guard_system, pulse_system,
        daemon_manager, gateway_hub, nexus,
    )

    # Collect all subsystem stats
    dashboard = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "active_runtimes": runtime_registry.active_count,
            "total_executions": runtime_registry.total_executions,
            "runtimes": runtime_registry.list_all(),
        },
        "platform": platform_hub.get_stats() if hasattr(platform_hub, 'get_stats') else {"status": "active"},
        "costs": cost_tracker.get_summary() if hasattr(cost_tracker, 'get_summary') else {},
        "enterprise": {
            "workspaces": enterprise_hub.get_stats() if hasattr(enterprise_hub, 'get_stats') else {},
        },
        "guard": guard_system.get_stats() if hasattr(guard_system, 'get_stats') else {},
        "pulse": pulse_system.get_health() if hasattr(pulse_system, 'get_health') else {},
        "daemon": daemon_manager.get_status() if hasattr(daemon_manager, 'get_status') else {},
        "gateway": gateway_hub.get_stats() if hasattr(gateway_hub, 'get_stats') else {},
        "nexus": nexus.get_stats() if hasattr(nexus, 'get_stats') else {},
    }

    # Add synthesis stats
    try:
        dashboard["synthesis"] = agent_synthesis.get_stats()
    except Exception:
        dashboard["synthesis"] = {"status": "active"}

    return dashboard


@router.get("/system/health")
async def get_system_health():
    """Get comprehensive system health check."""
    health = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "api": "ok",
            "database": "ok",
            "runtime_registry": f"ok ({runtime_registry.active_count} active)",
            "orchestrator": f"ok ({orchestrator.active_agents} agents)",
        },
    }

    # Check pulse system
    try:
        pulse = pulse_system.get_health()
        health["components"]["pulse"] = pulse.get("status", "ok") if isinstance(pulse, dict) else "ok"
    except Exception as e:
        health["components"]["pulse"] = f"error: {e}"

    return health


# ═══════════════════════════════════════════════════════════
# Skill Compiler API
# ═══════════════════════════════════════════════════════════

from agent.skill_compiler import skill_compiler


@router.get("/skill-compiler/skills")
async def list_compiled_skills(category: str = Query("", max_length=50), status: str = Query("", max_length=50)):
    """List compiled skills with optional filtering."""
    skills = skill_compiler.list_skills(
        status=status or None,
        category=category or None,
    )
    return {"skills": skills}


@router.get("/skill-compiler/pipelines")
async def list_skill_pipelines():
    """List all skill pipelines."""
    pipelines = skill_compiler.list_pipelines()
    return {"pipelines": pipelines}


@router.get("/skill-compiler/stats")
async def get_skill_compiler_stats():
    """Get skill compiler statistics."""
    result = skill_compiler.get_stats()
    if isinstance(result, dict):
        result.setdefault("total_patterns", 0)
    return result


@router.get("/skill-compiler/search")
async def search_skills(query: str = Query(min_length=1, max_length=200)):
    """Search for skills by query."""
    skills = skill_compiler.search_skills(query)
    return {"skills": skills}


@router.post("/skill-compiler/skills/{skill_id}/activate")
async def activate_skill(skill_id: str):
    """Activate a compiled skill."""
    success = skill_compiler.activate_skill(skill_id)
    if not success:
        raise HTTPException(404, "Skill not found")
    return {"success": True}


@router.post("/skill-compiler/skills/{skill_id}/improve")
async def improve_skill(skill_id: str):
    """Improve a compiled skill based on usage data."""
    result = await skill_compiler.improve_skill(skill_id)
    if result.get("error"):
        raise HTTPException(400, result["error"])
    return result


@router.post("/skill-compiler/pipelines")
async def create_skill_pipeline(
    name: str = Query(min_length=1, max_length=100),
    skill_ids: str = Query(min_length=1, max_length=500),
):
    """Create a skill pipeline from multiple skills."""
    ids = [s.strip() for s in skill_ids.split(",") if s.strip()]
    result = await skill_compiler.compound_pipeline(name=name, skill_ids=ids)
    if result.get("error"):
        raise HTTPException(400, result["error"])
    return result


# ═══════════════════════════════════════════════════════════
# Conversation Search API
# ═══════════════════════════════════════════════════════════

from agent.conversation_search import conversation_search


@router.get("/conversation-search/list")
async def list_conversations(limit: int = Query(20, ge=1, le=100)):
    """List indexed conversations."""
    conversations = conversation_search.list_conversations(limit)
    return {"conversations": conversations}


@router.get("/conversation-search/search")
async def search_conversations(
    query: str = Query(min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50),
):
    """Search conversation history."""
    results = await conversation_search.search(query, limit=limit)
    return {
        "results": [
            {
                "conversation_id": r.entry.conversation_id,
                "role": r.entry.role,
                "content": r.entry.content[:500],
                "summary": r.entry.summary,
                "topics": r.entry.topics,
                "relevance_score": r.relevance_score,
                "timestamp": r.entry.timestamp,
                "conversation_title": r.conversation.title if r.conversation else "",
            }
            for r in results
        ]
    }


@router.get("/conversation-search/search-by-topic")
async def search_by_topic(
    topic: str = Query(min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
):
    """Search conversations by topic."""
    results = await conversation_search.search_by_topic(topic, limit=limit)
    return {
        "results": [
            {
                "conversation_id": r.entry.conversation_id,
                "role": r.entry.role,
                "content": r.entry.content[:500],
                "summary": r.entry.summary,
                "topics": r.entry.topics,
                "relevance_score": r.relevance_score,
                "timestamp": r.entry.timestamp,
                "conversation_title": r.conversation.title if r.conversation else "",
            }
            for r in results
        ]
    }


@router.get("/conversation-search/recap")
async def generate_conversation_recap(
    query: str = Query(min_length=1, max_length=500),
    days_back: int = Query(30, ge=1, le=365),
):
    """Generate a recap of past conversations relevant to a query."""
    recap = await conversation_search.generate_recap(query, days_back=days_back)
    return recap


@router.get("/conversation-search/timeline")
async def get_conversation_timeline(days_back: int = Query(30, ge=1, le=365)):
    """Get a chronological timeline of conversations."""
    timeline = conversation_search.get_timeline(days_back=days_back)
    return {"timeline": timeline}


@router.get("/conversation-search/stats")
async def get_conversation_search_stats():
    """Get conversation search engine statistics."""
    return conversation_search.get_stats()


# ═══════════════════════════════════════════════════════════
# MCP Bridge API
# ═══════════════════════════════════════════════════════════

from agent.mcp_bridge import mcp_bridge, MCPServerConfig, MCPTransport


@router.get("/mcp-bridge/stats")
async def get_mcp_bridge_stats():
    """Get MCP bridge statistics."""
    result = mcp_bridge.get_stats()
    if isinstance(result, dict):
        result.setdefault("total_servers", 0)
    return result


@router.get("/mcp-bridge/tools")
async def list_mcp_tools(server_name: str = Query("", max_length=100)):
    """List MCP tools, optionally filtered by server."""
    tools = mcp_bridge.get_tools(server_name=server_name or None)
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "server_name": t.server_name,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]
    }


@router.post("/mcp-bridge/servers")
async def register_mcp_server(config: MCPServerConfig):
    """Register a new MCP server."""
    server_name = mcp_bridge.register_server(config)
    return {"server_name": server_name, "registered": True}


@router.post("/mcp-bridge/servers/{server_name}/connect")
async def connect_mcp_server(server_name: str):
    """Connect to a registered MCP server."""
    success = await mcp_bridge.connect_server(server_name)
    return {"server_name": server_name, "connected": success}


@router.post("/mcp-bridge/servers/{server_name}/disconnect")
async def disconnect_mcp_server(server_name: str):
    """Disconnect from an MCP server."""
    await mcp_bridge.disconnect_server(server_name)
    return {"server_name": server_name, "disconnected": True}


# ═══════════════════════════════════════════════════════════
# Learning Orchestrator API
# ═══════════════════════════════════════════════════════════

from agent.learning_orchestrator import learning_orchestrator


@router.get("/learning/stats")
async def get_learning_stats():
    """Get learning orchestrator statistics."""
    result = learning_orchestrator.get_stats()
    if isinstance(result, dict):
        result.setdefault("total_insights", 0)
    return result


@router.get("/learning/insights")
async def get_learning_insights(
    category: str = Query("", max_length=50),
    limit: int = Query(20, ge=1, le=100),
):
    """Get learning insights with optional category filter."""
    insights = learning_orchestrator.get_insights(
        category=category or None,
        limit=limit,
    )
    return {"insights": insights}


@router.get("/learning/strategies")
async def get_learning_strategies(limit: int = Query(10, ge=1, le=50)):
    """Get top-performing strategy profiles."""
    strategies = learning_orchestrator.get_best_strategies(limit)
    return {"strategies": strategies}


@router.post("/learning/consolidate")
async def trigger_learning_consolidation():
    """Trigger a learning consolidation cycle."""
    result = await learning_orchestrator.consolidate()
    return result


@router.get("/learning/best-strategy")
async def get_best_strategy(prompt: str = Query(min_length=1, max_length=500)):
    """Get the best known strategy for a given prompt."""
    strategy = learning_orchestrator.get_best_strategy(prompt)
    if strategy:
        return {"found": True, "strategy": strategy}
    return {"found": False, "message": "No strategy profile found for this task pattern"}


# ═══════════════════════════════════════════════════════════
# Agent Core Pipeline API — full analyze→plan→execute→reflect
# ═══════════════════════════════════════════════════════════


class PipelineRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    agent_id: str = Field(default="default", min_length=1)
    tools: list[str] | None = None
    context: str = Field(default="task")


class AnalyzeRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    agent_id: str = Field(default="default", min_length=1)


class PlanSequenceRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=4096)
    agent_id: str = Field(default="default", min_length=1)
    tools: list[str] | None = None


class ReflectRequest(BaseModel):
    agent_id: str = Field(default="default", min_length=1)
    trace_ids: list[str] | None = None
    limit: int = Field(default=10, ge=1, le=100)


class CrossTraceRequest(BaseModel):
    agent_id: str = Field(default="default", min_length=1)
    trace_ids: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=100)


class CalibrateRequest(BaseModel):
    raw_confidence: float = Field(..., ge=0.0, le=1.0)
    strategy: str = Field(default="balanced")
    agent_id: str = Field(default="default", min_length=1)


@router.post("/agent-core/pipeline")
async def run_agent_core_pipeline(data: PipelineRequest):
    """Run the full observe→analyze→plan→execute→reflect pipeline."""
    try:
        core = _get_or_create_core(data.agent_id)
        result = await core.run_pipeline(
            prompt=data.prompt,
            available_tools=data.tools,
            context=ExecutionContext(data.context) if data.context in [e.value for e in ExecutionContext] else ExecutionContext.TASK,
        )
        return {"status": "completed", "agent_id": data.agent_id, "pipeline_id": str(uuid.uuid4()), "pipeline": result}
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(500, f"Pipeline execution failed: {str(e)}")


@router.post("/agent-core/analyze/deep")
async def analyze_with_core_deep(data: AnalyzeRequest):
    """Deep analysis of a prompt using the agent core's LLM-backed analyzer."""
    try:
        core = _get_or_create_core(data.agent_id)
        analysis = await core.analyze(data.prompt)
        return {"agent_id": data.agent_id, "task_type": analysis.get("task_type", "general") if isinstance(analysis, dict) else "general", "analysis": analysis}
    except Exception as e:
        logger.error(f"Deep analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/agent-core/plan-sequence/deep")
async def plan_sequence_with_core_deep(data: PlanSequenceRequest):
    """Decompose a task into a structured execution plan with dependencies."""
    try:
        core = _get_or_create_core(data.agent_id)
        tools = data.tools or [t.name for t in tool_registry.list_tools()]
        plan = await core.plan_sequence(data.task, tools)
        return {"agent_id": data.agent_id, "sequence": plan, "plan": plan}
    except Exception as e:
        logger.error(f"Plan sequence failed: {e}")
        raise HTTPException(500, f"Planning failed: {str(e)}")


@router.post("/agent-core/reflect")
async def reflect_on_execution(data: ReflectRequest):
    """Generate improvement suggestions from execution history."""
    try:
        core = _get_or_create_core(data.agent_id)
        traces = None
        if data.trace_ids:
            all_traces = core.get_recent_traces(100)
            traces = [t for t in core._execution_history if t.id in data.trace_ids]
        result = await core.reflect(traces=traces, limit=data.limit)
        return {"agent_id": data.agent_id, "suggestions": result.get("suggestions", result) if isinstance(result, dict) else result, "reflection": result}
    except Exception as e:
        logger.error(f"Reflection failed: {e}")
        raise HTTPException(500, f"Reflection failed: {str(e)}")


@router.post("/agent-core/cross-trace")
async def cross_trace_analysis(data: CrossTraceRequest):
    """Cross-trace meta-analysis across multiple execution traces."""
    try:
        core = _get_or_create_core(data.agent_id)
        result = await core.analyze_cross_trace(
            trace_ids=data.trace_ids,
            limit=data.limit,
        )
        return {"agent_id": data.agent_id, "patterns": result.get("patterns", result) if isinstance(result, dict) else result, "cross_trace": result}
    except Exception as e:
        logger.error(f"Cross-trace analysis failed: {e}")
        raise HTTPException(500, f"Cross-trace analysis failed: {str(e)}")


@router.get("/agent-core/calibrate")
async def calibrate_confidence(
    raw_confidence: float = Query(..., ge=0.0, le=1.0),
    strategy: str = Query("balanced", min_length=1),
    agent_id: str = Query("default", min_length=1),
):
    """Get calibrated confidence for a task based on historical strategy performance."""
    try:
        core = _get_or_create_core(agent_id)
        result = core.calibrate_confidence(raw_confidence, strategy)
        return {"agent_id": agent_id, "calibrated_confidence": result.get("calibrated", result) if isinstance(result, dict) else result, "calibration": result}
    except Exception as e:
        logger.error(f"Confidence calibration failed: {e}")
        raise HTTPException(500, f"Calibration failed: {str(e)}")


# ═══════════════════════════════════════════════════════════
# Agent Synthesis API — cross-agent knowledge fusion
# ═══════════════════════════════════════════════════════════


class FuseRequest(BaseModel):
    min_contributors: int = Field(default=2, ge=1, le=20)


class CollaborateRequest(BaseModel):
    agent_id: str = Field(default="", min_length=0)
    agent_ids: list[str] = Field(default_factory=list)
    focus_areas: list[str] | None = None


class DecideRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    options: list[str] = Field(..., min_length=2)
    agent_ids: list[str] = Field(default_factory=list)
    agent_votes: list[dict] | None = None


class ResolveConflictsRequest(BaseModel):
    topic_filter: str | None = Field(default=None, max_length=200)


@router.post("/synthesis/fuse")
async def fuse_knowledge(data: FuseRequest):
    """Fuse knowledge across agents using confidence-weighted aggregation."""
    try:
        fused = agent_synthesis.fuse_knowledge(min_contributors=data.min_contributors)
        return {
            "fused_count": len(fused),
            "topic": fused[0].topic if fused else "unknown",
            "results": [
                {
                    "id": f.id,
                    "topic": f.topic,
                    "content": f.fused_content[:300],
                    "confidence": f.confidence,
                    "contributing_agents": f.contributing_agents,
                    "dissenting_views": f.dissenting_views,
                    "timestamp": f.timestamp,
                }
                for f in fused
            ],
        }
    except Exception as e:
        logger.error(f"Knowledge fusion failed: {e}")
        raise HTTPException(500, f"Fusion failed: {str(e)}")


@router.post("/synthesis/collaborate")
async def collaborative_learning(data: CollaborateRequest):
    """Collaborative learning protocol across agents."""
    try:
        patterns = agent_synthesis.collaborative_learn_protocol()
        if data.agent_id:
            for pattern in patterns:
                agent_synthesis.adopt_pattern(data.agent_id, pattern.id)
        return {
            "shared_patterns": [
                {
                    "id": p.id,
                    "pattern": p.pattern,
                    "source_agents": p.source_agents,
                    "adoption_count": p.adoption_count,
                    "effectiveness": p.effectiveness,
                }
                for p in patterns
            ],
            "agent_id": data.agent_id,
        }
    except Exception as e:
        logger.error(f"Collaborative learning failed: {e}")
        raise HTTPException(500, f"Collaboration failed: {str(e)}")


@router.post("/synthesis/decide")
async def collective_decision(data: DecideRequest):
    """Collective decision making with trust-weighted voting."""
    try:
        # Convert agent_ids to agent_votes if provided
        agent_votes = data.agent_votes
        if data.agent_ids and not agent_votes:
            agent_votes = [
                {"agent_id": aid, "agent_name": f"Agent-{aid[:8]}", "option": "", "confidence": 0.5, "rationale": ""}
                for aid in data.agent_ids
            ]
        decision = agent_synthesis.make_collective_decision(
            question=data.question,
            options=data.options,
            agent_votes=agent_votes,
        )
        return {
            "question": data.question,
            "decision": decision.winner,
            "consensus_level": decision.consensus_level,
            "option_scores": decision.options,
            "votes": [
                {
                    "agent_id": v.agent_id,
                    "agent_name": v.agent_name,
                    "option": v.option,
                    "confidence": v.confidence,
                    "rationale": v.rationale[:200],
                }
                for v in decision.votes
            ],
            "dissenting_views": decision.dissenting_minority,
            "timestamp": decision.timestamp,
        }
    except Exception as e:
        logger.error(f"Collective decision failed: {e}")
        raise HTTPException(500, f"Decision failed: {str(e)}")


@router.get("/synthesis/distill")
async def query_distilled_knowledge(query: str = Query(min_length=1, max_length=500)):
    """Query distilled knowledge from the synthesis engine."""
    try:
        agent_synthesis.distill_knowledge()
        results = agent_synthesis.query_distilled_knowledge(query)
        return {"query": query, "found": len(results) > 0, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Knowledge distillation query failed: {e}")
        raise HTTPException(500, f"Distillation query failed: {str(e)}")


@router.get("/synthesis/trust-network")
async def get_trust_network(agent_id: str = Query("", max_length=64)):
    """Get trust network graph for all agents or a specific agent."""
    try:
        if agent_id:
            edges = agent_synthesis.get_trust_edges(agent_id)
            return {
                "agent_id": agent_id,
                "edges": [
                    {
                        "source": e.source_agent,
                        "target": e.target_agent,
                        "trust_score": e.trust_score,
                        "interaction_count": e.interaction_count,
                        "successful_exchanges": e.successful_exchanges,
                        "last_interaction": e.last_interaction,
                    }
                    for e in edges
                ],
            }
        # Return full network
        all_edges = []
        for aid in agent_synthesis._trust_edges:
            for edge in agent_synthesis.get_trust_edges(aid):
                all_edges.append({
                    "source": edge.source_agent,
                    "target": edge.target_agent,
                    "trust_score": edge.trust_score,
                    "interaction_count": edge.interaction_count,
                })
        return {"network": all_edges, "total_edges": len(all_edges), "agent_count": len(agent_synthesis._agent_trust_scores)}
    except Exception as e:
        logger.error(f"Trust network query failed: {e}")
        raise HTTPException(500, f"Trust network query failed: {str(e)}")


@router.post("/synthesis/resolve-conflicts")
async def resolve_knowledge_conflicts(data: ResolveConflictsRequest):
    """Resolve knowledge conflicts between agents."""
    try:
        conflicts = agent_synthesis.resolve_conflicts_with_provenance()
        if data.topic_filter:
            conflicts = [c for c in conflicts if data.topic_filter.lower() in c.topic.lower()]
        return {
            "resolved": sum(1 for c in conflicts if c.resolved),
            "conflicts": [
                {
                    "id": c.id,
                    "topic": c.topic,
                    "agent_a": c.agent_a,
                    "agent_b": c.agent_b,
                    "resolved": c.resolved,
                    "resolution": c.resolution,
                    "timestamp": c.timestamp,
                }
                for c in conflicts
            ],
            "total": len(conflicts),
        }
    except Exception as e:
        logger.error(f"Conflict resolution failed: {e}")
        raise HTTPException(500, f"Conflict resolution failed: {str(e)}")


# ═══════════════════════════════════════════════════════════
# Agent Intelligence API — reasoning strategy and validation
# ═══════════════════════════════════════════════════════════

from agent.shared import intelligence


class DispatchStrategyRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=4096)
    context: str | dict | None = None


class AdaptiveToolsRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    tools: list[str] | None = None
    limit: int = Field(default=5, ge=1, le=20)


class ValidateRequest(BaseModel):
    steps: list[dict] = Field(..., min_length=1)
    answer: str = Field(default="", max_length=4096)
    claimed_facts: list[str] = Field(default_factory=list, max_length=50)


class AnalyzePromptRequest(BaseModel):
    prompt_text: str = Field(default="", max_length=4096)
    prompt: str = Field(default="", max_length=4096)
    response_quality: float = Field(default=0.5, ge=0.0, le=1.0)


class QuantifyRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=4096)
    reasoning_steps: list[dict] = Field(default_factory=list)
    tool_results: list[dict] | None = None
    confidence_history: list[float] | None = None


@router.post("/intelligence/dispatch-strategy")
async def dispatch_reasoning(data: DispatchStrategyRequest):
    """Dispatch reasoning strategy based on task characteristics."""
    try:
        result = intelligence.dispatch_reasoning_strategy(
            task=data.task,
            context=data.context,
        )
        return {"strategy": result}
    except Exception as e:
        logger.error(f"Strategy dispatch failed: {e}")
        raise HTTPException(500, f"Strategy dispatch failed: {str(e)}")


@router.post("/intelligence/adaptive-tools")
async def adaptive_tool_selection(data: AdaptiveToolsRequest):
    """Adaptive tool selection based on task and tool effectiveness history."""
    try:
        available = data.tools or [t.name for t in tool_registry.list_tools()]
        selected = intelligence.select_tools_adaptive(
            prompt=data.prompt,
            available_tools=available,
            limit=data.limit,
        )
        return {
            "prompt": data.prompt[:200],
            "selected_tools": [
                {"name": t, "score": intelligence._compute_tool_exploitation_score(t, data.prompt.lower())}
                for t in selected
            ],
        }
    except Exception as e:
        logger.error(f"Adaptive tool selection failed: {e}")
        raise HTTPException(500, f"Tool selection failed: {str(e)}")


@router.get("/intelligence/lessons")
async def get_distilled_lessons(
    pattern_filter: str | None = Query(None, max_length=100),
    limit: int = Query(10, ge=1, le=50),
):
    """Get distilled lessons from execution experience."""
    try:
        lessons = intelligence.distill_lessons(
            pattern_filter=pattern_filter,
            limit=limit,
        )
        return {"lessons": lessons, "count": len(lessons)}
    except Exception as e:
        logger.error(f"Lesson distillation failed: {e}")
        raise HTTPException(500, f"Lesson retrieval failed: {str(e)}")


@router.post("/intelligence/validate")
async def validate_reasoning_chain(data: ValidateRequest):
    """Validate a reasoning chain for logical consistency and completeness."""
    try:
        result = intelligence.validate_reasoning_chain(
            steps=data.steps,
            answer=data.answer,
            claimed_facts=data.claimed_facts,
        )
        return {"valid": result.get("valid", True) if isinstance(result, dict) else True, "validation": result}
    except Exception as e:
        logger.error(f"Reasoning validation failed: {e}")
        raise HTTPException(500, f"Validation failed: {str(e)}")


@router.post("/intelligence/analyze-prompt")
async def analyze_prompt_quality(data: AnalyzePromptRequest):
    """Analyze and optimize prompt for better reasoning outcomes."""
    try:
        prompt_text = data.prompt_text or data.prompt
        analysis = intelligence.analyze_prompt(
            prompt_text=prompt_text,
            response_quality=data.response_quality,
        )
        suggestions = intelligence.suggest_prompt_improvements(prompt_text)
        return {
            "clarity_score": analysis.clarity_score,
            "analysis": {
                "clarity_score": analysis.clarity_score,
                "specificity_score": analysis.specificity_score,
                "effectiveness_score": analysis.effectiveness_score,
                "strengths": analysis.strengths,
                "weaknesses": analysis.weaknesses,
                "suggested_rewrite": analysis.suggested_rewrite,
            },
            "improvement_suggestions": suggestions,
        }
    except Exception as e:
        logger.error(f"Prompt analysis failed: {e}")
        raise HTTPException(500, f"Prompt analysis failed: {str(e)}")


@router.post("/intelligence/quantify")
async def quantify_uncertainty(data: QuantifyRequest):
    """Quantify response uncertainty using multiple calibration techniques."""
    try:
        estimate = intelligence.quantify_uncertainty(
            answer=data.answer,
            reasoning_steps=data.reasoning_steps,
            tool_results=data.tool_results,
            confidence_history=data.confidence_history,
        )
        return {
            "uncertainty_level": estimate.overall_uncertainty,
            "uncertainty": {
                "overall": estimate.overall_uncertainty,
                "ensemble_variance": estimate.ensemble_variance,
                "calibration_error": estimate.calibration_error,
                "consistency_score": estimate.consistency_score,
                "confidence_interval": estimate.confidence_interval,
                "narrative": estimate.narrative,
            }
        }
    except Exception as e:
        logger.error(f"Uncertainty quantification failed: {e}")
        raise HTTPException(500, f"Quantification failed: {str(e)}")


# ═══════════════════════════════════════════════════════════
# Platform API — event routing, health, and configuration
# ═══════════════════════════════════════════════════════════


class EventRouteRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=100)
    event_type: str = Field(..., min_length=1, max_length=100)
    data: dict | None = None
    severity: str = Field(default="info", max_length=20)


class ServiceRegisterRequest(BaseModel):
    subsystem: str = Field(..., min_length=1, max_length=50)
    status: str = Field(default="running", max_length=20)
    metadata: dict | None = None


class ConfigReloadRequest(BaseModel):
    updates: dict = Field(default_factory=dict)


@router.post("/platform/event-route")
async def route_platform_event(data: EventRouteRequest):
    """Route events across platform subsystems."""
    try:
        event = platform_hub.emit_event(
            source=data.source,
            event_type=data.event_type,
            data=data.data,
            severity=data.severity,
        )
        return {
            "event_id": event.id,
            "source": event.source,
            "event_type": event.event_type,
            "routed": True,
            "timestamp": event.timestamp,
        }
    except Exception as e:
        logger.error(f"Event routing failed: {e}")
        raise HTTPException(500, f"Event routing failed: {str(e)}")


@router.get("/platform/health-aggregate")
async def get_platform_health_aggregate():
    """Aggregated health across all platform subsystems."""
    try:
        health = platform_hub.get_health()
        performance = platform_hub.get_performance_metrics()
        deps = platform_hub.get_dependency_graph()
        return {
            "overall_status": health.get("status", "healthy") if isinstance(health, dict) else "healthy",
            "health": health,
            "performance": performance,
            "dependencies": deps,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Health aggregate failed: {e}")
        raise HTTPException(500, f"Health aggregate failed: {str(e)}")


@router.post("/platform/service-register")
async def register_service(data: ServiceRegisterRequest):
    """Dynamic service registration for platform subsystems."""
    try:
        subsystem = PlatformSubsystem(data.subsystem) if data.subsystem in [s.value for s in PlatformSubsystem] else None
        if subsystem:
            platform_hub.update_subsystem_status(
                subsystem_name=data.subsystem,
                status=data.status,
                details=data.metadata,
            )
            return {
                "subsystem": data.subsystem,
                "registered": True,
                "status": data.status,
            }
        return {
            "subsystem": data.subsystem,
            "registered": False,
            "message": "Unknown subsystem type",
        }
    except Exception as e:
        logger.error(f"Service registration failed: {e}")
        raise HTTPException(500, f"Service registration failed: {str(e)}")


@router.post("/platform/config-reload")
async def reload_platform_config(data: ConfigReloadRequest):
    """Hot-reload platform configuration."""
    try:
        platform_hub.update_config(data.updates)
        current_config = platform_hub.get_config()
        return {
            "reloaded": True,
            "config_reloaded": True,
            "current_config": current_config,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Config reload failed: {e}")
        raise HTTPException(500, f"Config reload failed: {str(e)}")


@router.get("/platform/audit-log")
async def get_platform_audit_log(
    limit: int = Query(50, ge=1, le=500),
    event_type: str | None = Query(None, max_length=100),
):
    """Platform audit log with event history."""
    try:
        events = platform_hub.get_recent_events(limit=limit, event_type=event_type)
        return {
            "entries": events,
            "events": events,
            "total": len(events),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Audit log retrieval failed: {e}")
        raise HTTPException(500, f"Audit log retrieval failed: {str(e)}")


# ═══════════════════════════════════════════════════════════
# Real-time Streaming API — SSE for pipeline and chat
# ═══════════════════════════════════════════════════════════


class StreamPipelineRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    agent_id: str = Field(default="default", min_length=1)
    tools: list[str] | None = None


class StreamChatRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    conversation_id: str | None = None
    enable_tools: bool = Field(default=True)
    enable_reasoning: bool = Field(default=False)


@router.get("/agent-core/stream-pipeline")
async def stream_pipeline_execution(
    prompt: str = Query(..., min_length=1, max_length=4096),
    agent_id: str = Query("default", min_length=1),
):
    """SSE stream for pipeline execution with real-time stage updates."""
    async def event_stream():
        try:
            core = _get_or_create_core(agent_id)
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'observe', 'message': 'Starting pipeline observation...'})}\n\n"

            # Run analysis
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'analyze', 'message': 'Analyzing task...'})}\n\n"
            analysis = await core.analyze(prompt)
            yield f"data: {json.dumps({'type': 'analysis', 'data': analysis})}\n\n"

            # Run planning
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'plan', 'message': 'Planning execution sequence...'})}\n\n"
            tools = [t.name for t in tool_registry.list_tools()]
            plan = await core.plan_sequence(prompt, tools)
            yield f"data: {json.dumps({'type': 'plan', 'data': plan})}\n\n"

            # Run strategy selection
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'execute', 'message': 'Selecting execution strategy...'})}\n\n"
            strategy = await core.select_strategy(prompt, tools)
            yield f"data: {json.dumps({'type': 'strategy', 'data': strategy})}\n\n"

            # Run reflection
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'reflect', 'message': 'Generating reflections...'})}\n\n"
            reflection = await core.reflect(limit=5)
            yield f"data: {json.dumps({'type': 'reflection', 'data': reflection})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'agent_id': agent_id, 'pipeline': 'complete'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/stream")
async def chat_stream_sse(
    agent_id: str = Query(..., min_length=1),
    content: str = Query(..., min_length=1),
    conversation_id: str | None = Query(None),
    enable_tools: bool = Query(True),
    enable_reasoning: bool = Query(False),
):
    """SSE stream for chat with tool call visualization."""
    async with async_session() as session:
        result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(404, "Agent not found")

        conv_id = conversation_id
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
                message=content,
                history=history_result,
                enable_tools=enable_tools,
                enable_reasoning=enable_reasoning,
            ):
                full_response += token

                # Tool call visualization markers
                if token.startswith("\n[Tool:") and token.endswith("]\n"):
                    tool_name = token.strip()[6:-1].strip()
                    tc_id = f"tc-{uuid.uuid4().hex[:6]}"
                    yield f"data: {json.dumps({'type': 'tool_call', 'id': tc_id, 'name': tool_name})}\n\n"
                elif token.startswith("[Tool:") and token.endswith("]\n"):
                    tool_name = token[6:-1].strip()
                    tc_id = f"tc-{uuid.uuid4().hex[:6]}"
                    yield f"data: {json.dumps({'type': 'tool_call', 'id': tc_id, 'name': tool_name})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            if enable_reasoning:
                try:
                    engine = orchestrator.get_engine(agent.id, agent.name, agent.instructions or "")
                    reasoning_stats = engine.get_reasoning_stats()
                    if reasoning_stats.get("total_traces", 0) > 0:
                        avg_time = reasoning_stats.get("avg_time_ms", 0)
                        success_rate = reasoning_stats.get("success_rate", "N/A")
                        yield f"data: {json.dumps({'type': 'reasoning', 'content': f'Reasoning completed: {success_rate} success rate, {avg_time:.0f}ms avg time'})}\n\n"
                except Exception:
                    pass

            async with async_session() as s3:
                user_msg = MsgModel(
                    id=f"msg-{uuid.uuid4().hex[:8]}",
                    agent_id=agent.id, conversation_id=conv_id,
                    role="user", content=content,
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

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ═══════════════════════════════════════════════════════════
# Convenience Aliases — compatibility routes for dashboard panels
# ═══════════════════════════════════════════════════════════


@router.get("/platform-hub/stats")
async def get_platform_hub_stats_alias():
    """Platform hub stats convenience alias."""
    result = platform_hub.get_stats() if hasattr(platform_hub, 'get_stats') else {"status": "active"}
    if isinstance(result, dict):
        result["total_subsystems"] = result.get("subsystem_count", result.get("total_subsystems", 0))
    return result


@router.get("/costs/stats")
async def get_costs_stats():
    """Cost tracker statistics."""
    if hasattr(cost_tracker, 'get_summary'):
        return cost_tracker.get_summary()
    if hasattr(cost_tracker, 'get_stats'):
        return cost_tracker.get_stats()
    return {"total_entries": 0, "total_cost": 0.0}


@router.get("/agent-dashboard")
async def get_agent_dashboard_alias(agent_id: str | None = None):
    """Agent dashboard convenience alias."""
    return await agent_dashboard(agent_id)


@router.get("/enterprise")
async def get_enterprise_alias():
    """Enterprise hub convenience alias."""
    result = enterprise_hub.get_hub_stats() if hasattr(enterprise_hub, 'get_hub_stats') else {}
    result.setdefault("total_workspaces", 0)
    return result


