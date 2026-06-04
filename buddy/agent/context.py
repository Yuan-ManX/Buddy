"""Buddy Context Window Manager — intelligent context pruning and summarization

Manages agent context windows by automatically pruning, summarizing, and
compacting conversation history to stay within token limits while preserving
critical information. Supports LLM-powered summarization for high-quality
context compression.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI
from config.settings import settings

logger = logging.getLogger("buddy.context")


@dataclass
class ContextConfig:
    max_tokens: int = 8192
    max_messages: int = 50
    preserve_system: bool = True
    preserve_recent: int = 10
    summarize_threshold: int = 30
    summary_compression_ratio: float = 0.3


# LLM summarization prompt template
CONTEXT_SUMMARIZE_PROMPT = """Summarize the following conversation history. Include:
1. Key topics discussed
2. Important decisions made
3. Open questions or pending tasks
4. User preferences mentioned
5. Any critical context needed to continue

Be concise. Preserve facts, not conversational filler.

CONVERSATION:
{messages}

SUMMARY:"""


class ContextManager:
    """Intelligent context window manager with LLM-powered summarization."""

    def __init__(self, config: ContextConfig | None = None, client: AsyncOpenAI | None = None):
        self.config = config or ContextConfig()
        self._summary_cache: str = ""
        self._client = client

    def set_client(self, client: AsyncOpenAI):
        """Set the LLM client for summarization."""
        self._client = client

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token."""
        return max(1, len(text) // 4)

    def estimate_tokens_for_messages(self, messages: list[dict]) -> int:
        total = 0
        for m in messages:
            total += self.estimate_tokens(str(m.get("content", "")))
            total += 4  # role overhead
        return total

    async def compact(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> list[dict]:
        """Compact messages to fit within token budget, using LLM summarization when available."""
        if not messages:
            return []

        result: list[dict] = []
        token_budget = self.config.max_tokens

        # Always include system message
        if system_prompt and self.config.preserve_system:
            result.append({"role": "system", "content": system_prompt})
            token_budget -= self.estimate_tokens(system_prompt)

        if self._summary_cache:
            result.append({"role": "system", "content": f"[Previous context summary]: {self._summary_cache}"})
            token_budget -= self.estimate_tokens(self._summary_cache)

        # Separate recent messages from older ones
        non_system = [m for m in messages if m.get("role") != "system"]

        if len(non_system) <= self.config.max_messages:
            recent = non_system
            older = []
        else:
            recent = non_system[-self.config.preserve_recent:]
            older = non_system[:-self.config.preserve_recent]

        # Summarize older messages if needed
        if older and len(non_system) > self.config.summarize_threshold:
            summary = await self._generate_summary(older)
            self._summary_cache = summary[:500]
            token_budget -= self.estimate_tokens(summary)

        # Add recent messages, respecting token budget
        for msg in reversed(recent):
            msg_tokens = self.estimate_tokens(str(msg.get("content", "")))
            if token_budget - msg_tokens < 500:
                break
            token_budget -= msg_tokens
            result.append(msg)

        # Ensure correct ordering
        system_msgs = [m for m in result if m.get("role") == "system"]
        other_msgs = [m for m in result if m.get("role") != "system"]
        return system_msgs + other_msgs

    async def _generate_summary(self, messages: list[dict]) -> str:
        """Generate a summary using LLM when available, with heuristic fallback."""
        if not messages:
            return ""
        # Try LLM summarization first
        if self._client:
            llm_summary = await self._generate_summary_llm(messages)
            if llm_summary:
                return llm_summary
        return self._generate_summary_heuristic(messages)

    async def _generate_summary_llm(self, messages: list[dict]) -> str:
        """Use LLM to generate a high-quality summary."""
        if not self._client:
            return ""

        # Format messages for the summary prompt
        message_texts = []
        for m in messages[-20:]:  # Limit to last 20 older messages
            role = m.get("role", "unknown")
            content = str(m.get("content", ""))[:200]
            message_texts.append(f"[{role}]: {content}")

        combined = "\n".join(message_texts)

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": CONTEXT_SUMMARIZE_PROMPT.format(messages=combined[:4000]),
                }],
                max_tokens=400,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.debug(f"LLM summary failed: {e}")
            return ""

    def _generate_summary_heuristic(self, messages: list[dict]) -> str:
        """Fallback keyword-based summary generation."""

        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        assistant_msgs = [m["content"] for m in messages if m.get("role") == "assistant"]

        topics = set()
        for msg in user_msgs:
            words = msg.lower().split()[:5]
            for w in words:
                if len(w) > 3:
                    topics.add(w)

        parts = [f"Conversation history ({len(messages)} messages):"]
        if topics:
            parts.append(f"Topics discussed: {', '.join(list(topics)[:10])}")
        parts.append(f"User messages: {len(user_msgs)}, Assistant messages: {len(assistant_msgs)}")
        parts.append("Key exchanges preserved in recent context.")

        return " ".join(parts)

    def clear_summary(self):
        self._summary_cache = ""

    def get_stats(self) -> dict:
        return {
            "config": {
                "max_tokens": self.config.max_tokens,
                "max_messages": self.config.max_messages,
                "preserve_recent": self.config.preserve_recent,
            },
            "summary_cache_size": len(self._summary_cache),
            "has_cached_summary": bool(self._summary_cache),
        }


context_manager = ContextManager()