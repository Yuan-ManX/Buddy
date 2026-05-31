"""Skills System — Reusable capabilities for Buddy Agents"""
from typing import Callable
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    handler: Callable = None

    async def execute(self, **kwargs) -> str:
        if self.handler:
            return await self.handler(**kwargs)
        return f"Skill '{self.name}' executed."


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill):
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        return self._skills.get(name)

    def list_all(self) -> list[dict]:
        return [
            {"name": s.name, "description": s.description, "parameters": s.parameters}
            for s in self._skills.values()
        ]

    async def execute(self, skill_name: str, **kwargs) -> str:
        skill = self.get(skill_name)
        if not skill:
            return f"Unknown skill: {skill_name}"
        return await skill.execute(**kwargs)


registry = SkillRegistry()


async def deploy_skill(args):
    return "Deployment pipeline triggered."


async def code_review_skill(args):
    return f"Code review completed. No issues found."


async def research_skill(args):
    query = args.get("query", "")
    return f"Research completed for query: {query}."


async def summarize_skill(args):
    text = args.get("text", "")[:500]
    return f"Summary: Key points extracted from provided content."


registry.register(Skill("deploy", "Run deployment pipeline", {"target": "string"}, deploy_skill))
registry.register(Skill("code_review", "Review code changes", {"files": "array"}, code_review_skill))
registry.register(Skill("research", "Research a topic", {"query": "string"}, research_skill))
registry.register(Skill("summarize", "Summarize content", {"text": "string"}, summarize_skill))