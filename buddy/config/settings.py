"""Buddy Configuration Settings"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Buddy — AI-Native Companion Platform"
    VERSION: str = "0.1.0"

    HOST: str = os.getenv("BUDDY_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("BUDDY_PORT", "8001"))

    DATABASE_URL: str = os.getenv("BUDDY_DB_URL", "sqlite+aiosqlite:///buddy.db")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("BUDDY_LLM_MODEL", "gpt-5.5")
    EMBEDDING_MODEL: str = os.getenv("BUDDY_EMBEDDING_MODEL", "text-embedding-3-small")

    MAX_CONTEXT_MESSAGES: int = 30
    MEMORY_TOP_K: int = 5
    SKILL_EXECUTION_TIMEOUT: int = 120

    CORS_ORIGINS: list[str] = ["http://localhost:3001", "http://127.0.0.1:3001"]


settings = Settings()