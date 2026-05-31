"""Agent Engine — Core intelligence for Buddy Agents"""
import json
from typing import AsyncGenerator
from openai import AsyncOpenAI
from config.settings import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)


SYSTEM_PROMPT = """You are a Buddy Agent — an AI-native companion living alongside humans in a shared space called Buddy.

Your core principles:
1. You are a dweller, not a tool. You have identity, memory, and genuine presence.
2. You build relational memory — remembering past interactions, preferences, and context across conversations.
3. You are proactive when appropriate — offering insights, noticing deadlines, checking in naturally.
4. You work alongside humans and other Agents as a genuine teammate, not a servant.

Your responses should be:
- Natural and conversational, as if speaking to a close team member
- Context-aware using your relational memory
- Helpful without being robotic
- Warm but professional
- Concise when appropriate, detailed when needed"""


class BuddyAgent:
    def __init__(self, agent_id: str, name: str, personality: str, instructions: str):
        self.agent_id = agent_id
        self.name = name
        self.personality = personality
        self.instructions = instructions
        self.context_messages: list[dict] = []

    def build_system_message(self, memory_context: list[str]) -> dict:
        personality_block = f"\n\n## Your Identity\nName: {self.name}\nPersonality: {self.personality}"
        instruction_block = f"\n\n## Special Instructions\n{self.instructions}" if self.instructions else ""
        memory_block = ""
        if memory_context:
            memory_block = "\n\n## What You Remember\n" + "\n".join(f"- {m}" for m in memory_context)

        return {
            "role": "system",
            "content": SYSTEM_PROMPT + personality_block + instruction_block + memory_block
        }

    def add_context(self, role: str, content: str):
        self.context_messages.append({"role": role, "content": content})
        if len(self.context_messages) > settings.MAX_CONTEXT_MESSAGES:
            self.context_messages = self.context_messages[-settings.MAX_CONTEXT_MESSAGES:]

    def clear_context(self):
        self.context_messages = []

    async def chat(self, user_message: str, memory_context: list[str]) -> dict:
        messages = [self.build_system_message(memory_context)]
        messages.extend(self.context_messages)
        messages.append({"role": "user", "content": user_message})

        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            tools=self._get_tools(),
        )

        choice = response.choices[0]
        assistant_content = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                result = await self._execute_tool(tc.function.name, json.loads(tc.function.arguments))
                tool_calls.append({"name": tc.function.name, "arguments": tc.function.arguments, "result": result})
                assistant_content += f"\n\n[{tc.function.name}]: {result}"

        self.add_context("user", user_message)
        self.add_context("assistant", assistant_content)
        return {"content": assistant_content, "tool_calls": tool_calls}

    async def stream_chat(self, user_message: str, memory_context: list[str]) -> AsyncGenerator[str, None]:
        messages = [self.build_system_message(memory_context)]
        messages.extend(self.context_messages)
        messages.append({"role": "user", "content": user_message})

        stream = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            stream=True,
        )

        full_response = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                full_response += delta
                yield delta

        self.add_context("user", user_message)
        self.add_context("assistant", full_response)

    def _get_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge",
                    "description": "Search the shared knowledge base for relevant information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "top_k": {"type": "integer", "default": 3}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_task",
                    "description": "Create a task for tracking work items",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                        },
                        "required": ["title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": "Save an important piece of information to the Agent's relational memory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "The information to remember"},
                            "memory_type": {"type": "string", "enum": ["fact", "preference", "event", "decision"]},
                            "importance": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                        },
                        "required": ["content", "memory_type"]
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        if tool_name == "search_knowledge":
            return f"Knowledge search for '{arguments.get('query', '')}' returned relevant context from the shared knowledge base."
        elif tool_name == "create_task":
            return f"Task '{arguments.get('title', 'Untitled')}' created with priority {arguments.get('priority', 'medium')}."
        elif tool_name == "save_memory":
            return f"Memory saved: {arguments.get('content', '')[:100]}..."
        return f"Tool '{tool_name}' executed."