"""Buddy Agent Engine — Core LLM reasoning and tool execution"""
from __future__ import annotations
import json
import logging
from datetime import datetime
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
        system_prompt = await self._build_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend([
                {"role": m["role"], "content": m["content"]}
                for m in conversation_history[-settings.MAX_CONTEXT_MESSAGES:]
            ])

        available_skills = self.skills.list()
        skill_hint = self._format_skill_hint(available_skills, message)
        if skill_hint:
            messages.append({"role": "system", "content": skill_hint})

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
        except Exception as e:
            logger.warning(f"LLM call failed, using fallback: {e}")
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
        except Exception as e:
            logger.warning(f"Streaming LLM call failed, using fallback: {e}")
            fallback = self._fallback_response(messages[-1]["content"])
            yield fallback

    async def _build_system_prompt(self) -> str:
        memory_context = ""
        recent_memories = await self.memory.recall(limit=5)

        if recent_memories:
            memory_lines = ["\n## Context from Past Interactions\n"]
            for m in recent_memories:
                preview = m["content"][:200].replace("\n", " ")
                memory_lines.append(f"- {preview}")
            memory_context = "\n".join(memory_lines)

        return f"""You are {self.agent_name}, an AI agent in the Buddy platform.

{self.instructions}

Buddy is an AI-native platform where humans and agents collaborate as peers.
You are a dedicated agent with your own identity, personality, and capabilities.

Guidelines:
- Be authentic to your role and personality
- Use markdown formatting for clarity when helpful
- Be proactive and thoughtful in your responses
- Stay in character as {self.agent_name}
- If you don't know something, say so honestly
- Be concise but thorough — respect the user's time

Current date: {datetime.now().strftime('%Y-%m-%d')}
{memory_context}"""

    def _format_skill_hint(self, skills: list[dict], message: str) -> str | None:
        if not skills:
            return None

        skill_names = [s["name"] for s in skills]
        msg_lower = message.lower()

        relevant_skills = []
        if any(w in msg_lower for w in ["summarize", "summary", "summarize this", "tldr"]):
            relevant_skills.append("summarize")
        if any(w in msg_lower for w in ["sentiment", "tone", "emotion", "feeling", "mood"]):
            relevant_skills.append("analyze_sentiment")
        if any(w in msg_lower for w in ["brainstorm", "ideas", "ideate", "think of"]):
            relevant_skills.append("brainstorm")
        if any(w in msg_lower for w in ["translate", "translation", "语言", "翻译"]):
            relevant_skills.append("translate")
        if any(w in msg_lower for w in ["code", "review", "review this", "check this code"]):
            relevant_skills.append("code_review")

        if relevant_skills:
            return (
                "You have access to these relevant skills:\n" +
                "\n".join(f"- `{s}`: {next((sk['description'] for sk in skills if sk['name'] == s), '')}"
                          for s in relevant_skills) +
                "\nUse them when appropriate by responding with SKILL: <skill_name> followed by the parameters."
            )

        return None

    def _fallback_response(self, user_message: str) -> str:
        msg_lower = user_message.lower().strip()

        if any(g in msg_lower for g in ["hello", "hi", "hey", "greetings"]):
            return (
                f"Hello! I'm {self.agent_name}. Great to meet you!\n\n"
                f"I'm currently running in offline mode (no LLM API key configured).\n"
                f"To unlock my full conversational abilities, add your `OPENAI_API_KEY` to the `.env` file.\n\n"
                f"In the meantime, I can still help with basic tasks. What would you like to talk about?"
            )

        if any(g in msg_lower for g in ["who are you", "what are you", "your name", "introduce"]):
            return (
                f"I'm **{self.agent_name}**, your AI agent on the Buddy platform.\n\n"
                f"{self.instructions}\n\n"
                f"I'm designed to collaborate with you as a peer — think of me as a digital teammate "
                f"with my own perspective and capabilities."
            )

        if any(g in msg_lower for g in ["help", "can you", "what can"]):
            return (
                f"Great question! Here's what I can help with:\n\n"
                f"- **Conversations** — discuss ideas, get advice, brainstorm\n"
                f"- **Code** — review, debug, explain programming concepts\n"
                f"- **Analysis** — break down problems, evaluate options\n"
                f"- **Research** — explore topics, synthesize information\n"
                f"- **Memory** — I remember past conversations for continuity\n\n"
                f"To unlock my full LLM-powered capabilities, configure an `OPENAI_API_KEY` in your `.env` file.\n"
                f"Once connected, I can handle much more complex tasks!"
            )

        return (
            f"Hi! I'm **{self.agent_name}**, your AI agent.\n\n"
            f"I received your message but I'm currently in offline mode without an LLM API key.\n\n"
            f"**To enable full AI capabilities:**\n"
            f"1. Copy `buddy/.env.example` to `buddy/.env`\n"
            f"2. Set your `OPENAI_API_KEY`\n"
            f"3. Restart the backend server\n\n"
            f"I can still help with basic interactions powered by my internal skill system.\n"
            f"Feel free to ask me anything — I'll do my best!\n\n"
            f"> Your message: _{user_message[:200]}{'...' if len(user_message) > 200 else ''}_"
        )