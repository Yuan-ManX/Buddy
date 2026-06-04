"""SQLAlchemy ORM models for Buddy"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.db import Base


def gen_id():
    return str(uuid.uuid4())


class TimestampMixin:
    """Mixin providing created_at and updated_at timestamps for all models."""
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)


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
    agent_ids: Mapped[dict] = mapped_column(JSON, default=list)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), default="fact")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

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
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    parent_task_id: Mapped[str] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    agent = relationship("Agent", back_populates="tasks")

    __table_args__ = (
        Index("idx_tasks_agent_status", "agent_id", "status"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_parent", "parent_task_id"),
    )