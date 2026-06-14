"""SQLAlchemy ORM models for Buddy"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.db import Base


def gen_id():
    return str(uuid.uuid4())


class TimestampMixin:
    """Mixin providing created_at and updated_at timestamps for all models."""
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="custom")
    personality: Mapped[str] = mapped_column(Text, default="friendly and helpful")
    instructions: Mapped[str] = mapped_column(Text, default="")
    avatar: Mapped[str] = mapped_column(String(256), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    messages = relationship("Message", back_populates="agent", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="agent", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="agent", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="agent", cascade="all, delete-orphan")
    autopilots = relationship("AutopilotConfig", back_populates="agent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_agents_active_role", "is_active", "role"),
    )


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default="user")
    content: Mapped[str] = mapped_column(Text, nullable=False)

    agent = relationship("Agent", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conv", "conversation_id", "created_at"),
    )


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    title: Mapped[str] = mapped_column(String(256), default="New Conversation")
    agent_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), default="fact")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    agent = relationship("Agent", back_populates="memories")

    __table_args__ = (
        Index("idx_memories_agent_time", "agent_id", "created_at"),
        Index("idx_memories_type_importance", "memory_type", "importance"),
    )


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    kind: Mapped[str] = mapped_column(String(32), default="direct")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    parent_task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    agent = relationship("Agent", back_populates="tasks")

    __table_args__ = (
        Index("idx_tasks_agent_status", "agent_id", "status"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_parent", "parent_task_id"),
    )


class Plan(TimestampMixin, Base):
    """Persistent execution plan for multi-step agent workflows."""
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    agent = relationship("Agent", back_populates="plans")

    __table_args__ = (
        Index("idx_plans_agent_status", "agent_id", "status"),
    )


class AutopilotConfig(TimestampMixin, Base):
    """Persistent autopilot configuration for scheduled agent tasks."""
    __tablename__ = "autopilots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_template: Mapped[str] = mapped_column(Text, nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), default="interval")
    schedule: Mapped[str] = mapped_column(String(64), default="3600")
    status: Mapped[str] = mapped_column(String(32), default="active")
    max_runs: Mapped[int] = mapped_column(Integer, default=0)
    runs_completed: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(512), default="")
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    agent = relationship("Agent", back_populates="autopilots")

    __table_args__ = (
        Index("idx_autopilots_agent_status", "agent_id", "status"),
    )


class MCPServer(TimestampMixin, Base):
    """Persistent MCP server configuration for external tool integration."""
    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    transport: Mapped[str] = mapped_column(String(32), default="http")
    endpoint: Mapped[str] = mapped_column(String(512), default="")
    command: Mapped[str] = mapped_column(Text, default="")
    env: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="disconnected")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_mcp_servers_status", "status"),
    )