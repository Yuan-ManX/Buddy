"""Buddy — AI-Native Companion Platform

Backend API Entry Point (port 8001)
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from database.db import init_db
from api.routes import router as api_router
from api.websocket import router as ws_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("buddy")


async def seed_agents():
    from database.db import async_session
    from database.models import Agent as AgentModel
    from sqlalchemy import select

    async with async_session() as session:
        existing = await session.execute(select(AgentModel).limit(1))
        if existing.scalars().first():
            return

        agents = [
            AgentModel(
                id="agent-strategy-001",
                name="Strategy Buddy",
                role="strategy",
                personality="analytical and decisive",
                instructions="You are Strategy Buddy, a strategic planning expert. Help users analyze situations, plan projects, identify risks, and make data-driven decisions. Be concise but thorough.",
                avatar="S",
                is_active=True,
            ),
            AgentModel(
                id="agent-engineering-001",
                name="Code Buddy",
                role="engineering",
                personality="precise and solution-oriented",
                instructions="You are Code Buddy, a software engineering expert. Help users write, debug, and optimize code. Explain concepts clearly and provide working examples.",
                avatar="C",
                is_active=True,
            ),
            AgentModel(
                id="agent-research-001",
                name="Research Buddy",
                role="research",
                personality="curious and thorough",
                instructions="You are Research Buddy, a research assistant. Help users explore topics, find information, synthesize knowledge, and stay updated on the latest developments.",
                avatar="R",
                is_active=True,
            ),
            AgentModel(
                id="agent-companion-001",
                name="Life Buddy",
                role="companion",
                personality="warm and supportive",
                instructions="You are Life Buddy, a personal companion. Help users with daily life, wellness, habits, personal growth, and general advice. Be empathetic and encouraging.",
                avatar="L",
                is_active=True,
            ),
        ]
        session.add_all(agents)
        await session.commit()
        logger.info("Seeded 4 Buddy agents")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_agents()
    logger.info(f"Buddy backend started on port {settings.PORT}")
    yield
    logger.info("Buddy backend shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)