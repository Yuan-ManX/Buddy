"""Buddy Skills Registry — Reusable agent capabilities"""
import logging
from typing import Any

logger = logging.getLogger("buddy.skills")


class SkillsRegistry:
    """Registry of reusable skills that agents can execute."""

    def __init__(self):
        self._skills: dict[str, dict] = {
            "summarize": {
                "name": "summarize",
                "description": "Generate a concise summary of provided text",
                "parameters": {"text": "The text to summarize"},
                "handler": self._handle_summarize,
            },
            "analyze_sentiment": {
                "name": "analyze_sentiment",
                "description": "Analyze the emotional tone of text",
                "parameters": {"text": "The text to analyze"},
                "handler": self._handle_sentiment,
            },
            "brainstorm": {
                "name": "brainstorm",
                "description": "Generate creative ideas around a topic",
                "parameters": {"topic": "The topic to brainstorm", "count": "Number of ideas (default 5)"},
                "handler": self._handle_brainstorm,
            },
            "translate": {
                "name": "translate",
                "description": "Translate text between languages",
                "parameters": {"text": "Text to translate", "target_language": "Target language code (default zh)"},
                "handler": self._handle_translate,
            },
            "code_review": {
                "name": "code_review",
                "description": "Review code for issues and improvements",
                "parameters": {"code": "The code snippet to review"},
                "handler": self._handle_code_review,
            },
        }

    def list(self) -> list[dict]:
        return [
            {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["parameters"],
            }
            for s in self._skills.values()
        ]

    def get(self, name: str) -> dict | None:
        return self._skills.get(name)

    async def execute(self, skill_name: str, parameters: dict[str, Any]) -> str:
        skill = self._skills.get(skill_name)
        if not skill:
            return f"Unknown skill: {skill_name}. Available skills: {', '.join(self._skills.keys())}"

        try:
            handler = skill["handler"]
            result = await handler(parameters)
            return result
        except Exception as e:
            logger.error(f"Skill execution error ({skill_name}): {e}")
            return f"Error executing skill '{skill_name}': {str(e)}"

    async def _handle_summarize(self, params: dict) -> str:
        text = params.get("text", "")
        if not text:
            return "No text provided to summarize."
        words = text.split()
        if len(words) <= 50:
            return f"**Summary**:\n\n{text}\n\n_(Text is already concise — no summarization needed.)_"
        return (
            f"**Summary** (original: {len(words)} words):\n\n"
            f"The text discusses {words[0]}... covering {len(words)} words of content. "
            f"Key themes emerge around the central topic. The main points can be condensed "
            f"while preserving essential meaning.\n\n"
            f"_Note: Connect an LLM for semantic summarization._"
        )

    async def _handle_sentiment(self, params: dict) -> str:
        text = params.get("text", "")
        if not text:
            return "No text provided to analyze."
        return (
            f"**Sentiment Analysis**:\n\n"
            f"- Positive indicators: moderate\n"
            f"- Negative indicators: low\n"
            f"- Overall tone: neutral-to-positive\n\n"
            f"_Note: Connect an LLM for detailed sentiment analysis._"
        )

    async def _handle_brainstorm(self, params: dict) -> str:
        topic = params.get("topic", "")
        count = int(params.get("count", 5))
        if not topic:
            return "No topic provided for brainstorming."

        ideas = [
            f"{i+1}. Explore **{topic}** from the angle of {angle}"
            for i, angle in enumerate([
                "user experience and accessibility",
                "scalability and performance",
                "integration with existing ecosystems",
                "novel technological approaches",
                "community and ecosystem building",
                "monetization and sustainability",
                "privacy and data sovereignty",
                "cross-platform and mobile-first",
            ][:count])
        ]

        return (
            f"**Brainstorm: {topic}** ({count} ideas):\n\n" +
            "\n".join(ideas) +
            f"\n\n_Note: Connect an LLM for contextual brainstorming._"
        )

    async def _handle_translate(self, params: dict) -> str:
        text = params.get("text", "")
        lang = params.get("target_language", "zh")
        if not text:
            return "No text provided to translate."
        return (
            f"**Translation Request** (to {lang}):\n\n"
            f"Original: {text[:200]}\n\n"
            f"_Note: Connect an LLM for actual translation._"
        )

    async def _handle_code_review(self, params: dict) -> str:
        code = params.get("code", "")
        if not code:
            return "No code provided to review."
        lines = code.strip().split("\n")
        return (
            f"**Code Review** ({len(lines)} lines):\n\n"
            f"- Structure: {'well-organized' if len(lines) > 3 else 'simple'}\n"
            f"- Readability: generally clear\n"
            f"- Suggestions: consider adding docstrings/type hints\n"
            f"- Potential issues: review edge cases and error handling\n\n"
            f"_Note: Connect an LLM for in-depth code review._"
        )