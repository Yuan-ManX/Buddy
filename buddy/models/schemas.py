"""Pydantic models for Buddy API"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

AgentRole = Literal["strategy", "engineering", "design", "research", "writing", "companion", "custom"]


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    role: AgentRole = "custom"
    personality: str = Field(default="friendly and helpful")
    instructions: str = Field(default="")
    avatar: str = Field(default="")


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    personality: str
    instructions: str
    avatar: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    agent_id: str
    content: str
    role: Literal["user", "assistant", "system"] = "user"


class MessageResponse(BaseModel):
    id: str
    agent_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: str = Field(default="New Conversation")
    agent_ids: list[str] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    id: str
    title: str
    agent_ids: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemoryEntry(BaseModel):
    id: str
    agent_id: str
    conversation_id: Optional[str] = None
    content: str
    memory_type: Literal["fact", "preference", "event", "decision"]
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    agent_id: str
    content: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    agent_id: str
    content: str
    conversation_id: str
    tool_calls: list[dict] = Field(default_factory=list)


class SkillDefinition(BaseModel):
    name: str
    description: str
    parameters: dict = Field(default_factory=dict)


class SkillExecute(BaseModel):
    skill_name: str
    agent_id: str
    parameters: dict = Field(default_factory=dict)