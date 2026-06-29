"""Buddy — AI-Native Companion Platform

Backend API Entry Point (port 8001)
"""
import sys
import os
import time
import logging
from contextlib import asynccontextmanager

# Ensure the buddy package directory is on sys.path for imports
_buddy_dir = os.path.dirname(os.path.abspath(__file__))
if _buddy_dir not in sys.path:
    sys.path.insert(0, _buddy_dir)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from database.db import init_db
from api.routes import router as api_router
from api.websocket import router as ws_router
from api.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, rate_limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
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


async def init_autopilot_executor():
    """Wire the autopilot engine with a real executor function."""
    from agent.shared import orchestrator, autopilot_engine
    from database.db import async_session
    from database.models import Agent as AgentModel
    from sqlalchemy import select

    async def execute_autopilot_task(agent_id: str, task_template: str, config_name: str):
        async with async_session() as session:
            result = await session.execute(select(AgentModel).where(AgentModel.id == agent_id))
            agent = result.scalars().first()
            if not agent:
                logger.warning(f"Autopilot: agent {agent_id} not found")
                return

        engine = orchestrator.get_engine(
            agent_id=agent.id,
            agent_name=agent.name,
            instructions=agent.instructions or f"You are {agent.name}, a {agent.role} agent.",
        )

        try:
            response = await engine.chat(
                f"[Autopilot Task: {config_name}]\n{task_template}",
                enable_tools=True,
                enable_reasoning=True,
            )
            result_text = response if isinstance(response, str) else ""
            logger.info(f"Autopilot [{config_name}] completed for {agent.name}: {result_text[:100]}")
        except Exception as e:
            logger.error(f"Autopilot [{config_name}] failed for {agent.name}: {e}")

    autopilot_engine.set_executor(execute_autopilot_task)
    logger.info("Autopilot executor wired")


async def init_dream_engines():
    """Start dream cycles for all active agents."""
    from agent.shared import orchestrator
    from database.db import async_session
    from database.models import Agent as AgentModel
    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(
            select(AgentModel).where(AgentModel.is_active == True)
        )
        agents = result.scalars().all()

    for agent in agents:
        engine = orchestrator.get_engine(
            agent_id=agent.id,
            agent_name=agent.name,
            instructions=agent.instructions or "",
        )
        engine.dream.start(interval=settings.DREAM_INTERVAL)
        logger.info(f"Dream engine started for {agent.name} (interval: {settings.DREAM_INTERVAL}s)")

    logger.info(f"Dream engines initialized for {len(agents)} agents")


async def init_mcp_connections():
    """Auto-connect to registered MCP servers."""
    from agent.shared import mcp_registry
    results = await mcp_registry.connect_all()
    connected = sum(1 for v in results.values() if v)
    logger.info(f"MCP auto-connect: {connected}/{len(results)} servers connected")


async def shutdown_engines():
    """Gracefully stop all dream engines and autopilot tasks."""
    from agent.shared import orchestrator, autopilot_engine

    for agent_id in list(orchestrator._engines.keys()):
        engine = orchestrator._engines.get(agent_id)
        if engine and engine.dream.is_running:
            await engine.dream.stop()
            logger.info(f"Dream engine stopped for {agent_id}")

    autopilot_engine.shutdown()
    logger.info("All engines shut down")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_agents()
    await init_autopilot_executor()
    await init_dream_engines()

    # Wire WebSocket manager to Platform Hub for real-time event broadcasting
    from agent.shared import ws_manager, platform_hub
    platform_hub.set_ws_manager(ws_manager)

    # MCP auto-connect runs in background, don't block startup
    import asyncio
    asyncio.create_task(init_mcp_connections())
    logger.info(f"Buddy backend started on http://{settings.HOST}:{settings.PORT}")
    logger.info(f"API docs: http://{settings.HOST}:{settings.PORT}/docs")
    yield
    await shutdown_engines()
    logger.info("Buddy backend shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")
    return response


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Return 400 Bad Request for invalid enum values or coercion failures.

    Route handlers that convert request strings into Enums (e.g. ScoreScale,
    GoalStatus, BeliefCategory) raise ValueError when the supplied value is
    not a valid member. Without this handler those would surface as opaque
    500 errors; surfacing them as 400 with the underlying message makes the
    API contract clearer for clients.
    """
    logger.warning(f"Invalid value on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": f"Invalid value: {exc}"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security and rate limiting middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

app.include_router(api_router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)