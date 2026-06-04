"""Buddy Skills Registry — LLM-powered composable agent capabilities

Skills are self-contained units that execute via LLM with structured prompts.
Each skill has a fallback heuristic for offline mode. Skills can be chained
into pipelines for complex multi-step operations.
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Awaitable

from openai import AsyncOpenAI

logger = logging.getLogger("buddy.skills")

SkillHandler = Callable[[dict[str, Any]], Awaitable[str]]

# ── Prompt Templates ─────────────────────────────────────

SUMMARIZE_PROMPT = """Summarize the following text concisely. Capture key points and main ideas.
Keep the summary under 200 words. Use bullet points if helpful.

TEXT:
{text}

SUMMARY:"""

SENTIMENT_PROMPT = """Analyze the emotional tone of the following text. Provide:
1. Overall sentiment (positive/negative/neutral/mixed)
2. Confidence score (0-100)
3. Key emotional indicators found
4. Brief explanation

TEXT:
{text}

ANALYSIS:"""

BRAINSTORM_PROMPT = """Generate {count} creative and practical ideas for the following topic.
Each idea should be unique, specific, and actionable. Output as a numbered list.

TOPIC: {topic}

IDEAS:"""

TRANSLATE_PROMPT = """Translate the following text to {target_language}.
Preserve the original meaning, tone, and formatting.
Output only the translation, no explanations.

TEXT:
{text}

TRANSLATION ({target_language}):"""

CODE_REVIEW_PROMPT = """Review the following code for:
1. Bugs and logic errors
2. Performance issues
3. Security concerns
4. Readability and style
5. Best practice violations

Provide specific line references where possible. Be constructive.

CODE:
{code}

REVIEW:"""

EXTRACT_KEYWORDS_PROMPT = """Extract {count} key terms and concepts from the following text.
Include both explicit terms and implied concepts. Output as a simple list.

TEXT:
{text}

KEY TERMS:"""

FORMAT_CODE_PROMPT = """Format and improve the following {language} code:
1. Fix indentation and spacing
2. Add proper line breaks
3. Improve variable names if needed
4. Add brief comments for complex logic
5. Keep the original logic unchanged

Output only the formatted code in a code block.

CODE:
{code}

FORMATTED ({language}):"""

GENERATE_TEST_PROMPT = """Generate comprehensive test cases for the following code using {framework}.
Include:
1. Happy path tests
2. Edge case tests
3. Error handling tests
4. Boundary value tests

Output the tests in proper {framework} syntax.

CODE:
{code}

TESTS:"""

EXPLAIN_CONCEPT_PROMPT = """Explain the following concept at a {level} level.
Use simple analogies and concrete examples. Keep it under 300 words.

CONCEPT: {concept}

EXPLANATION ({level} level):"""

COMPARE_OPTIONS_PROMPT = """Compare the following options based on the criteria provided.
For each option, list pros and cons. Provide a summary recommendation.

OPTIONS: {options}
CRITERIA: {criteria}

COMPARISON:"""


class SkillPipeline:
    """Chain multiple skills together, passing output of one as input to the next."""

    def __init__(self, registry: "SkillsRegistry"):
        self.registry = registry
        self._steps: list[tuple[str, dict[str, Any]]] = []

    def add(self, skill_name: str, parameters: dict[str, Any] | None = None) -> "SkillPipeline":
        self._steps.append((skill_name, parameters or {}))
        return self

    async def execute(self, initial_input: dict[str, Any] | None = None) -> str:
        results: list[str] = []
        context = initial_input or {}

        for i, (skill_name, params) in enumerate(self._steps):
            merged_params = {**context, **params}
            result = await self.registry.execute(skill_name, merged_params)
            results.append(f"[Step {i+1}: {skill_name}]\n{result}")
            context["_previous_result"] = result

        return "\n\n".join(results)


class SkillsRegistry:
    """Registry of LLM-powered composable skills with pipeline support."""

    def __init__(self, client: AsyncOpenAI | None = None):
        self._client = client
        self._skills: dict[str, dict] = {
            "summarize": {
                "name": "summarize",
                "description": "Generate a concise summary of provided text",
                "category": "text",
                "parameters": {"text": "The text to summarize"},
                "handler": self._handle_summarize,
            },
            "analyze_sentiment": {
                "name": "analyze_sentiment",
                "description": "Analyze the emotional tone of text",
                "category": "analysis",
                "parameters": {"text": "The text to analyze"},
                "handler": self._handle_sentiment,
            },
            "brainstorm": {
                "name": "brainstorm",
                "description": "Generate creative ideas around a topic",
                "category": "creative",
                "parameters": {"topic": "The topic to brainstorm", "count": "Number of ideas (default 5)"},
                "handler": self._handle_brainstorm,
            },
            "translate": {
                "name": "translate",
                "description": "Translate text between languages",
                "category": "text",
                "parameters": {"text": "Text to translate", "target_language": "Target language code"},
                "handler": self._handle_translate,
            },
            "code_review": {
                "name": "code_review",
                "description": "Review code for issues and improvements",
                "category": "engineering",
                "parameters": {"code": "The code snippet to review"},
                "handler": self._handle_code_review,
            },
            "extract_keywords": {
                "name": "extract_keywords",
                "description": "Extract key terms and concepts from text",
                "category": "analysis",
                "parameters": {"text": "The text to analyze", "count": "Number of keywords (default 5)"},
                "handler": self._handle_extract_keywords,
            },
            "format_code": {
                "name": "format_code",
                "description": "Format and organize code structure",
                "category": "engineering",
                "parameters": {"code": "The code to format", "language": "Programming language"},
                "handler": self._handle_format_code,
            },
            "generate_test": {
                "name": "generate_test",
                "description": "Generate test cases for code",
                "category": "engineering",
                "parameters": {"code": "The code to test", "framework": "Test framework"},
                "handler": self._handle_generate_test,
            },
            "explain_concept": {
                "name": "explain_concept",
                "description": "Explain a technical concept in simple terms",
                "category": "education",
                "parameters": {"concept": "The concept to explain", "level": "Expertise level (beginner/intermediate/expert)"},
                "handler": self._handle_explain_concept,
            },
            "compare_options": {
                "name": "compare_options",
                "description": "Compare multiple options with pros and cons",
                "category": "analysis",
                "parameters": {"options": "Options to compare (comma-separated)", "criteria": "Comparison criteria"},
                "handler": self._handle_compare_options,
            },
        }

    def set_client(self, client: AsyncOpenAI):
        """Set the LLM client after initialization."""
        self._client = client

    @property
    def has_llm(self) -> bool:
        return self._client is not None

    def list(self, category: str | None = None) -> list[dict]:
        skills = [
            {
                "name": s["name"],
                "description": s["description"],
                "category": s["category"],
                "parameters": s["parameters"],
            }
            for s in self._skills.values()
        ]
        if category:
            skills = [s for s in skills if s["category"] == category]
        return skills

    def categories(self) -> list[str]:
        return list({s["category"] for s in self._skills.values()})

    def get(self, name: str) -> dict | None:
        return self._skills.get(name)

    def register(self, name: str, description: str, category: str, parameters: dict, handler: SkillHandler):
        self._skills[name] = {
            "name": name,
            "description": description,
            "category": category,
            "parameters": parameters,
            "handler": handler,
        }
        logger.info(f"Registered skill: {name} ({category})")

    def pipeline(self) -> SkillPipeline:
        return SkillPipeline(self)

    async def execute(self, skill_name: str, parameters: dict[str, Any]) -> str:
        skill = self._skills.get(skill_name)
        if not skill:
            available = ", ".join(sorted(self._skills.keys()))
            return f"Unknown skill: `{skill_name}`. Available: {available}"

        try:
            handler = skill["handler"]
            result = await handler(parameters)
            logger.info(f"Skill executed: {skill_name}")
            return result
        except Exception as e:
            logger.error(f"Skill execution error ({skill_name}): {e}")
            return f"Error executing skill `{skill_name}`: {str(e)}"

    async def execute_pipeline(self, steps: list[tuple[str, dict]]) -> str:
        pipeline = self.pipeline()
        for name, params in steps:
            pipeline.add(name, params)
        return await pipeline.execute()

    async def _llm_call(self, prompt: str, max_tokens: int = 800, temperature: float = 0.5) -> str | None:
        """Execute an LLM call. Returns None if LLM is unavailable."""
        if not self._client:
            return None
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"LLM call failed for skill: {e}")
            return None

    # ── Skill Handlers ────────────────────────────────────

    async def _handle_summarize(self, params: dict) -> str:
        text = params.get("text", "")
        if not text:
            return "No text provided to summarize."

        result = await self._llm_call(SUMMARIZE_PROMPT.format(text=text[:4000]), max_tokens=400)
        if result:
            return f"**Summary**:\n\n{result.strip()}"

        # Fallback
        words = text.split()
        if len(words) <= 50:
            return f"**Summary**:\n\n{text}\n\n_(Text is already concise.)_"
        return f"**Summary** ({len(words)} words):\n\n{text[:200]}...\n\n_(LLM unavailable — showing preview.)_"

    async def _handle_sentiment(self, params: dict) -> str:
        text = params.get("text", "")
        if not text:
            return "No text provided to analyze."

        result = await self._llm_call(SENTIMENT_PROMPT.format(text=text[:3000]), max_tokens=300)
        if result:
            return f"**Sentiment Analysis**:\n\n{result.strip()}"

        return (
            f"**Sentiment Analysis**:\n\n"
            f"- Overall tone: neutral-to-positive\n"
            f"- Text length: {len(text.split())} words\n"
            f"_(LLM unavailable — heuristic only.)_"
        )

    async def _handle_brainstorm(self, params: dict) -> str:
        topic = params.get("topic", "")
        count = min(int(params.get("count", 5)), 10)
        if not topic:
            return "No topic provided for brainstorming."

        result = await self._llm_call(BRAINSTORM_PROMPT.format(topic=topic, count=count), max_tokens=600)
        if result:
            return f"**Brainstorm: {topic}**:\n\n{result.strip()}"

        angles = [
            "user experience and accessibility",
            "scalability and performance",
            "integration with existing systems",
            "novel technical approaches",
            "community building",
            "monetization and sustainability",
            "privacy and data security",
            "cross-platform capability",
            "developer experience",
            "AI-assisted features",
        ]
        ideas = [f"{i+1}. Explore **{topic}** via {angles[i]}" for i in range(min(count, len(angles)))]
        return f"**Brainstorm: {topic}** ({count} ideas):\n\n" + "\n".join(ideas) + "\n\n_(LLM unavailable — template ideas.)_"

    async def _handle_translate(self, params: dict) -> str:
        text = params.get("text", "")
        lang = params.get("target_language", "zh")
        if not text:
            return "No text provided to translate."

        result = await self._llm_call(TRANSLATE_PROMPT.format(text=text[:3000], target_language=lang), max_tokens=800)
        if result:
            return f"**Translation** (→ {lang}):\n\n{result.strip()}"

        return f"**Translation Request** (→ {lang}):\n\nOriginal: {text[:200]}\n\n_(LLM unavailable.)_"

    async def _handle_code_review(self, params: dict) -> str:
        code = params.get("code", "")
        if not code:
            return "No code provided to review."

        result = await self._llm_call(CODE_REVIEW_PROMPT.format(code=code[:5000]), max_tokens=800)
        if result:
            return f"**Code Review**:\n\n{result.strip()}"

        lines = code.strip().split("\n")
        return (
            f"**Code Review** ({len(lines)} lines):\n\n"
            f"- Structure: {'well-organized' if len(lines) > 3 else 'simple'}\n"
            f"- Check: edge cases, error handling, type safety, documentation\n"
            f"_(LLM unavailable — heuristic review.)_"
        )

    async def _handle_extract_keywords(self, params: dict) -> str:
        text = params.get("text", "")
        count = min(int(params.get("count", 5)), 20)
        if not text:
            return "No text provided."

        result = await self._llm_call(EXTRACT_KEYWORDS_PROMPT.format(text=text[:3000], count=count), max_tokens=300)
        if result:
            return f"**Keywords** ({count}):\n\n{result.strip()}"

        words = [w.strip(".,!?;:\"'()[]") for w in text.split() if len(w.strip(".,!?;:\"'()[]")) > 3]
        return f"**Keywords** ({min(count, len(words))}):\n\n- " + "\n- ".join(words[:count]) + "\n\n_(LLM unavailable — word extraction.)_"

    async def _handle_format_code(self, params: dict) -> str:
        code = params.get("code", "")
        language = params.get("language", "unknown")
        if not code:
            return "No code provided."

        result = await self._llm_call(FORMAT_CODE_PROMPT.format(code=code, language=language), max_tokens=1000)
        if result:
            return f"**Formatted Code** ({language}):\n\n{result.strip()}"

        return f"**Formatted Code** ({language}):\n\n```{language}\n{code.strip()}\n```\n\n_(LLM unavailable — no formatting applied.)_"

    async def _handle_generate_test(self, params: dict) -> str:
        code = params.get("code", "")
        framework = params.get("framework", "pytest")
        if not code:
            return "No code provided."

        result = await self._llm_call(GENERATE_TEST_PROMPT.format(code=code[:4000], framework=framework), max_tokens=1000)
        if result:
            return f"**Test Cases** ({framework}):\n\n{result.strip()}"

        return (
            f"**Test Cases** ({framework}):\n\n"
            f"```python\ndef test_happy_path():\n    pass\n\ndef test_edge_case():\n    pass\n```\n\n"
            f"_(LLM unavailable — template only.)_"
        )

    async def _handle_explain_concept(self, params: dict) -> str:
        concept = params.get("concept", "")
        level = params.get("level", "intermediate")
        if not concept:
            return "No concept provided."

        result = await self._llm_call(EXPLAIN_CONCEPT_PROMPT.format(concept=concept, level=level), max_tokens=500)
        if result:
            return f"**Explaining: {concept}** ({level}):\n\n{result.strip()}"

        return (
            f"**Explaining: {concept}** ({level}):\n\n"
            f"This concept is fundamental to its domain. At the {level} level, "
            f"understanding its principles and practical application is essential.\n\n"
            f"_(LLM unavailable — generic explanation.)_"
        )

    async def _handle_compare_options(self, params: dict) -> str:
        options = params.get("options", "")
        criteria = params.get("criteria", "general comparison")
        if not options:
            return "No options provided."

        result = await self._llm_call(COMPARE_OPTIONS_PROMPT.format(options=options, criteria=criteria), max_tokens=800)
        if result:
            return f"**Comparison**:\n\n{result.strip()}"

        option_list = [o.strip() for o in options.split(",")]
        comparison = f"**Comparison** (criteria: {criteria}):\n\n"
        for opt in option_list:
            comparison += f"### {opt}\n- Pros: context-dependent\n- Cons: requires evaluation\n\n"
        comparison += "_(LLM unavailable — template comparison.)_"
        return comparison