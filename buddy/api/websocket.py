"""WebSocket endpoint for real-time Agent streaming"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from database.db import async_session
from database.models import Agent, Message, Conversation
from agent.orchestrator import get_or_create_agent
from agent.memory import get_memory
import json

router = APIRouter()


@router.websocket("/ws/chat/{agent_id}")
async def websocket_chat(websocket: WebSocket, agent_id: str):
    await websocket.accept()

    async with async_session() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            await websocket.send_json({"type": "error", "content": "Agent not found"})
            await websocket.close()
            return

        buddy = get_or_create_agent(agent.id, agent.name, agent.personality, agent.instructions)
        memory_manager = get_memory(agent.id)

        conv = Conversation(title=f"Live: {agent.name}", agent_ids=[agent.id])
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        conv_id = conv.id

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            user_content = request.get("content", "")

            if not user_content:
                await websocket.send_json({"type": "error", "content": "Empty message"})
                continue

            await websocket.send_json({"type": "thinking", "content": ""})

            full_response = ""
            async for delta in buddy.stream_chat(user_content, await memory_manager.recall_context()):
                full_response += delta
                await websocket.send_json({"type": "token", "content": delta})

            await websocket.send_json({"type": "done", "content": full_response})

            async with async_session() as db:
                db_user_msg = Message(agent_id=agent_id, conversation_id=conv_id, role="user", content=user_content)
                db_agent_msg = Message(agent_id=agent_id, conversation_id=conv_id, role="assistant", content=full_response)
                db.add_all([db_user_msg, db_agent_msg])
                await db.commit()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass