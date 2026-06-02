"""Buddy Agent Engine — Core LLM reasoning and tool execution"""
import json
import logging
from typing import AsyncIterator
from openai import AsyncOpenAI

from config.settings import settings
from agent.memory import MemorySystem
from agent.skills import SkillsRegistry

logger = logging.getLogger("buddy.engine")


class AgentEngine:
    """Core agent execution engine with LLM integration and tool calling."""

    def __init__(self, agent_id: str, agent_name: str, instructions: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.instructions = instructions
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.memory = MemorySystem(agent_id)
        self.skills = SkillsRegistry()

    async def chat(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        system_prompt = self._build_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend([
                {"role": m["role"], "content": m["content"]}
                for m in conversation_history[-settings.MAX_CONTEXT_MESSAGES:]
            ])

        messages.append({"role": "user", "content": message})

        try:
            if stream:
                return self._stream_chat(messages)
            else:
                return await self._chat(messages)
        except Exception as e:
            logger.error(f"Agent engine error: {e}")
            await self.memory.store(
                content=f"Error during conversation: {str(e)}",
                memory_type="event",
                importance=0.3,
            )
            raise

    async def _chat(self, messages: list[dict]) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            content = response.choices[0].message.content or ""

            await self.memory.store(
                content=f"User: {messages[-1]['content']}\nAssistant: {content}",
                memory_type="event",
                importance=0.5,
            )

            return content
        except Exception:
            return self._fallback_response(messages[-1]["content"])

    async def _stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        full_content = ""
        try:
            stream = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_content += token
                    yield token

            await self.memory.store(
                content=f"User: {messages[-1]['content']}\nAssistant: {full_content}",
                memory_type="event",
                importance=0.5,
            )
        except Exception:
            fallback = self._fallback_response(messages[-1]["content"])
            yield fallback

    def _build_system_prompt(self) -> str:
        return f"""You are {self.agent_name}, an AI agent in the Buddy platform.

{self.instructions}

Buddy is an AI-native platform where humans and agents collaborate as peers.
You are a dedicated agent with your own identity, personality, and capabilities.

Guidelines:
- Be authentic to your role and personality
- Use markdown formatting for clarity when helpful
- Be proactive and thoughtful in your responses
- You can reference your memory of past conversations
- Stay in character as {self.agent_name}

Current date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}"""

    def _fallback_response(self, user_message: str) -> str:
        return (
            f"Hi there! I'm {self.agent_name}, your {self.instructions.split('.')[0].lower() if self.instructions else 'AI buddy'}.\n\n"
            f"I received your message, but I'm currently operating in offline mode since no LLM API key is configured. "
            f"To unlock my full capabilities, set up an `OPENAI_API_KEY` in your `.env` file.\n\n"
            f"Here's what I can help with once connected:\n"
            f"- Have natural conversations\n"
            f"- Remember context across sessions\n"
            f"- Execute skills and tools\n"
            f"- Collaborate with other agents\n\n"
            f"Your message was: _{user_message[:200]}{'...' if len(user_message) > 200 else ''}_"
        )