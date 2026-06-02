"""Buddy WebSocket — Real-time streaming chat"""
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from database.db import async_session
from database.models import Agent as AgentModel, Message as MsgModel, Conversation as ConvModel
from sqlalchemy import select
from agent.orchestrator import Orchestrator

logger = logging.getLogger("buddy.ws")
router = APIRouter()

orchestrator = Orchestrator()


@router.websocket("/ws/chat/{agent_id}")
async def ws_chat(websocket: WebSocket, agent_id: str):
    await websocket.accept()

    try:
        async with async_session() as session:
            result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
            agent = result.scalars().first()
            if not agent:
                await websocket.send_json({"type": "error", "content": "Agent not found"})
                await websocket.close()
                return

            agent_name = agent.name
            instructions = agent.instructions or f"You are {agent.name}, a {agent.role} agent."

        history: list[dict] = []
        conv_id = None

        while True:
            data = await websocket.receive_json()
            message = data.get("content", "").strip()
            if not message:
                continue

            history.append({"role": "user", "content": message})

            await websocket.send_json({"type": "thinking"})

            full_response = ""
            try:
                async for token in orchestrator.chat_stream(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    instructions=instructions,
                    message=message,
                    history=history[:-1],
                ):
                    full_response += token
                    await websocket.send_json({"type": "token", "content": token})
            except Exception as e:
                logger.error(f"Stream error: {e}")
                full_response = f"Error: {str(e)}"
                await websocket.send_json({"type": "error", "content": str(e)})
                await websocket.close()
                return

            history.append({"role": "assistant", "content": full_response})

            await websocket.send_json({"type": "done", "content": full_response})

            if not conv_id:
                conv_id = f"conv-{uuid.uuid4().hex[:8]}"
                async with async_session() as s:
                    conv = ConvModel(id=conv_id, title=f"Chat with {agent_name}", agent_ids=[agent_id])
                    s.add(conv)
                    await s.commit()

            async with async_session() as s:
                user_msg = MsgModel(
                    id=f"msg-{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id, conversation_id=conv_id,
                    role="user", content=message,
                )
                assistant_msg = MsgModel(
                    id=f"msg-{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id, conversation_id=conv_id,
                    role="assistant", content=full_response,
                )
                s.add_all([user_msg, assistant_msg])
                conv = await s.execute(select(ConvModel).where(ConvModel.id == conv_id))
                c = conv.scalars().first()
                if c:
                    c.updated_at = datetime.now(timezone.utc)
                await s.commit()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for agent {agent_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass