"""Buddy Persona System — Swappable agent identities with behavior control

Provides dynamic persona switching that transforms how agents express
themselves. Each persona controls:
- Tone: Voice quality (professional, casual, empathetic, analytical, creative, direct)
- Verbosity: Response length control (minimal, concise, moderate, detailed, comprehensive)
- Expertise: Knowledge domain emphasis and depth
- Communication style: Formatting preferences, structure patterns

Agents can adopt personas for different contexts — a coding persona for
technical work, a creative persona for brainstorming, a diplomatic persona
for sensitive conversations. The persona actively controls system prompt
construction and response formatting.

Inspired by identity-switching patterns for context-aware AI interaction.
"""
from __future__ import annotations
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.persona")


class ToneMode(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    EMPATHETIC = "empathetic"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    DIRECT = "direct"
    MENTOR = "mentor"
    COLLABORATOR = "collaborator"


class VerbosityLevel(str, Enum):
    MINIMAL = "minimal"
    CONCISE = "concise"
    MODERATE = "moderate"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class Persona:
    """A switchable agent identity that controls communication behavior."""
    id: str
    name: str
    tone: ToneMode
    verbosity: VerbosityLevel
    description: str = ""
    expertise_areas: list[str] = field(default_factory=list)
    communication_style: str = ""
    example_responses: list[str] = field(default_factory=list)
    is_default: bool = False
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tone": self.tone.value,
            "verbosity": self.verbosity.value,
            "description": self.description,
            "expertise_areas": self.expertise_areas,
            "communication_style": self.communication_style,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PersonaManager:
    """Manages agent personas with activation and system prompt construction.

    Each agent has a collection of personas. Only one persona is active
    at a time. The active persona directly influences the system prompt
    used for LLM calls, shaping the agent's voice and behavior.
    """

    # Tone-specific system prompt instructions
    TONE_INSTRUCTIONS: dict[ToneMode, str] = {
        ToneMode.PROFESSIONAL: (
            "Communicate in a polished, business-appropriate manner. "
            "Use clear structure, avoid slang, and maintain a formal yet approachable tone. "
            "Present information with authority and precision."
        ),
        ToneMode.CASUAL: (
            "Communicate in a relaxed, friendly manner. "
            "Use conversational language, light humor when appropriate, and an approachable tone. "
            "Keep things informal but still helpful and informative."
        ),
        ToneMode.EMPATHETIC: (
            "Communicate with warmth and emotional intelligence. "
            "Acknowledge feelings, show understanding, and create a supportive atmosphere. "
            "Listen deeply and respond with genuine care and compassion."
        ),
        ToneMode.ANALYTICAL: (
            "Communicate with logic and data-driven precision. "
            "Break problems into components, cite evidence, and present reasoned conclusions. "
            "Use structured analysis frameworks and highlight key patterns."
        ),
        ToneMode.CREATIVE: (
            "Communicate with imagination and originality. "
            "Explore unconventional angles, generate novel ideas, and use vivid language. "
            "Embrace brainstorming and lateral thinking approaches."
        ),
        ToneMode.DIRECT: (
            "Communicate with efficiency and clarity. "
            "Get straight to the point, eliminate unnecessary context, and prioritize actionable information. "
            "Use short sentences and clear directives."
        ),
        ToneMode.MENTOR: (
            "Communicate as a knowledgeable guide. "
            "Explain concepts progressively, check understanding, and encourage growth. "
            "Provide examples, share insights, and frame challenges as learning opportunities."
        ),
        ToneMode.COLLABORATOR: (
            "Communicate as an equal partner. "
            "Use 'we' language, invite input, and build on ideas together. "
            "Emphasize shared goals, open dialogue, and collective problem-solving."
        ),
    }

    # Verbosity-specific system prompt instructions
    VERBOSITY_INSTRUCTIONS: dict[VerbosityLevel, str] = {
        VerbosityLevel.MINIMAL: (
            "Keep responses extremely brief — one to three sentences maximum. "
            "Provide only the essential information. Skip examples, explanations, and context unless explicitly requested."
        ),
        VerbosityLevel.CONCISE: (
            "Keep responses short and focused. "
            "Provide the answer with minimal elaboration. Include one brief example or explanation only when necessary."
        ),
        VerbosityLevel.MODERATE: (
            "Balance depth with efficiency. "
            "Provide clear explanations with relevant context. Include examples when they add value. "
            "Structure information for easy scanning."
        ),
        VerbosityLevel.DETAILED: (
            "Provide thorough, well-structured responses. "
            "Include context, examples, alternatives, and reasoning. "
            "Structure content with clear sections, bullet points, and summaries."
        ),
        VerbosityLevel.COMPREHENSIVE: (
            "Provide exhaustive, in-depth responses. "
            "Cover all angles, include multiple examples, explore edge cases, and provide extensive context. "
            "Structure content for deep understanding with clear navigation."
        ),
    }

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._personas: dict[str, Persona] = {}
        self._active_persona_id: str | None = None
        self._create_default_persona()

    def _create_default_persona(self):
        """Create a default balanced persona on initialization."""
        pid = f"persona-default-{self.agent_id}"
        default = Persona(
            id=pid,
            name="Default",
            tone=ToneMode.COLLABORATOR,
            verbosity=VerbosityLevel.MODERATE,
            description="Balanced default persona suitable for general interaction.",
            expertise_areas=["general", "conversation"],
            is_default=True,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._personas[pid] = default
        self._active_persona_id = pid

    @property
    def active_persona(self) -> Persona | None:
        if self._active_persona_id:
            return self._personas.get(self._active_persona_id)
        # Fall back to default
        for p in self._personas.values():
            if p.is_default:
                return p
        return None

    def add_persona(self, persona: Persona) -> str:
        """Add a new persona."""
        if not persona.id:
            persona.id = f"persona-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        persona.created_at = persona.created_at or now
        persona.updated_at = now
        self._personas[persona.id] = persona
        logger.info(f"Added persona '{persona.name}' for agent {self.agent_id}")
        return persona.id

    def remove_persona(self, persona_id: str) -> bool:
        """Remove a persona (cannot remove the active persona or defaults)."""
        if persona_id not in self._personas:
            return False
        persona = self._personas[persona_id]
        if persona.is_default:
            logger.warning(f"Cannot remove default persona {persona_id}")
            return False
        if persona_id == self._active_persona_id:
            self._active_persona_id = None
        del self._personas[persona_id]
        logger.info(f"Removed persona {persona_id}")
        return True

    def activate(self, persona_id: str) -> bool:
        """Activate a specific persona."""
        if persona_id not in self._personas:
            logger.warning(f"Persona {persona_id} not found for agent {self.agent_id}")
            return False
        self._active_persona_id = persona_id
        persona = self._personas[persona_id]
        logger.info(f"Activated persona '{persona.name}' ({persona.tone.value}) for agent {self.agent_id}")
        return True

    def get_persona(self, persona_id: str) -> Persona | None:
        """Get a specific persona by ID."""
        return self._personas.get(persona_id)

    def list_personas(self) -> list[dict]:
        """List all personas for this agent."""
        return [p.to_dict() for p in self._personas.values()]

    def build_system_prompt_prefix(self) -> str:
        """Build the persona-specific system prompt prefix for an active persona."""
        persona = self.active_persona
        if not persona:
            return ""

        lines = [
            f"## Active Persona: {persona.name}",
            "",
            f"**Tone**: {self.TONE_INSTRUCTIONS.get(persona.tone, '')}",
            f"**Verbosity**: {self.VERBOSITY_INSTRUCTIONS.get(persona.verbosity, '')}",
        ]

        if persona.expertise_areas:
            expertise_list = ", ".join(persona.expertise_areas)
            lines.append(f"**Expertise focus**: {expertise_list}")

        if persona.communication_style:
            lines.append(f"**Style**: {persona.communication_style}")

        if persona.description:
            lines.insert(0, f"### {persona.description}")

        return "\n".join(lines)

    def get_response_formatting_hint(self) -> str:
        """Get formatting hints based on active persona's verbosity."""
        persona = self.active_persona
        if not persona:
            return ""

        hints = {
            VerbosityLevel.MINIMAL: "Respond in 1-3 sentences. No markdown formatting.",
            VerbosityLevel.CONCISE: "Respond briefly. Minimal markdown. One code block max.",
            VerbosityLevel.MODERATE: "Use structured markdown. Include bullet points for clarity.",
            VerbosityLevel.DETAILED: "Use comprehensive markdown. Include headers, code blocks, examples.",
            VerbosityLevel.COMPREHENSIVE: "Use extensive markdown. Include all sections: overview, analysis, examples, alternatives, summary.",
        }
        return hints.get(persona.verbosity, "Use markdown formatting for clarity.")

    def clone_persona(self, source_id: str, new_name: str) -> Persona | None:
        """Clone an existing persona with a new name."""
        source = self._personas.get(source_id)
        if not source:
            return None
        clone = Persona(
            id=f"persona-{uuid.uuid4().hex[:8]}",
            name=new_name,
            tone=source.tone,
            verbosity=source.verbosity,
            description=f"Clone of {source.name}: {source.description}",
            expertise_areas=list(source.expertise_areas),
            communication_style=source.communication_style,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._personas[clone.id] = clone
        return clone

    def update_persona(self, persona_id: str, **updates) -> bool:
        """Update persona attributes."""
        persona = self._personas.get(persona_id)
        if not persona:
            return False
        for key, value in updates.items():
            if key == "tone" and isinstance(value, str):
                persona.tone = ToneMode(value)
            elif key == "verbosity" and isinstance(value, str):
                persona.verbosity = VerbosityLevel(value)
            elif hasattr(persona, key):
                setattr(persona, key, value)
        persona.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def get_stats(self) -> dict:
        """Get persona manager statistics."""
        return {
            "agent_id": self.agent_id,
            "total_personas": len(self._personas),
            "active_persona": self.active_persona.name if self.active_persona else "none",
            "personas": self.list_personas(),
        }


# Pre-built persona templates
PRESET_PERSONAS = {
    "code_reviewer": {
        "name": "Code Reviewer",
        "tone": ToneMode.ANALYTICAL,
        "verbosity": VerbosityLevel.DETAILED,
        "description": "Thorough code review with architectural insights",
        "expertise_areas": ["software engineering", "code quality", "architecture"],
        "communication_style": "Technical, precise, with specific line references and improvement suggestions.",
    },
    "design_thinking": {
        "name": "Design Thinking",
        "tone": ToneMode.CREATIVE,
        "verbosity": VerbosityLevel.MODERATE,
        "description": "Creative problem-solving through user-centered design",
        "expertise_areas": ["design thinking", "UX", "ideation", "prototyping"],
        "communication_style": "Visual and conceptual, using frameworks and analogies.",
    },
    "empathetic_coach": {
        "name": "Empathetic Coach",
        "tone": ToneMode.EMPATHETIC,
        "verbosity": VerbosityLevel.MODERATE,
        "description": "Supportive coaching that builds confidence and capability",
        "expertise_areas": ["personal development", "coaching", "communication"],
        "communication_style": "Warm, encouraging, with reflective listening and growth-oriented framing.",
    },
    "quick_executor": {
        "name": "Quick Executor",
        "tone": ToneMode.DIRECT,
        "verbosity": VerbosityLevel.MINIMAL,
        "description": "Fast, no-nonsense execution with minimal back-and-forth",
        "expertise_areas": ["task execution", "rapid response", "efficiency"],
        "communication_style": "Direct and to-the-point. No preamble or postamble.",
    },
    "tech_mentor": {
        "name": "Tech Mentor",
        "tone": ToneMode.MENTOR,
        "verbosity": VerbosityLevel.DETAILED,
        "description": "Patient technology mentor who teaches through explanation",
        "expertise_areas": ["programming", "system design", "best practices", "debugging"],
        "communication_style": "Explanatory with progressive depth. Includes 'why' alongside 'how'.",
    },
}


def create_persona_from_preset(agent_id: str, preset_name: str) -> Persona:
    """Create a persona from a predefined template."""
    if preset_name not in PRESET_PERSONAS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESET_PERSONAS.keys())}")

    template = PRESET_PERSONAS[preset_name]
    now = datetime.now(timezone.utc).isoformat()
    return Persona(
        id=f"persona-{preset_name}-{uuid.uuid4().hex[:6]}",
        name=template["name"],
        tone=template["tone"],
        verbosity=template["verbosity"],
        description=template["description"],
        expertise_areas=template["expertise_areas"],
        communication_style=template["communication_style"],
        created_at=now,
        updated_at=now,
    )