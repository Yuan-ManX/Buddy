"""
Buddy Agent Persona System

Identity preservation, personality traits, role-based behavior, and
self-evolving character profiles that shape how agents interact with users
and other agents. Each persona is a self-contained character definition
that governs tone, decision-making style, and interaction patterns.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PersonaTrait(Enum):
    """Core personality dimensions for agent behavior shaping."""

    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    PRECISE = "precise"
    EMPATHETIC = "empathetic"
    DECISIVE = "decisive"
    CAUTIOUS = "cautious"
    ENTHUSIASTIC = "enthusiastic"
    PRAGMATIC = "pragmatic"
    VISIONARY = "visionary"
    DETAILED = "detailed"
    CONCISE = "concise"
    PLAYFUL = "playful"


class InteractionStyle(Enum):
    """How the agent communicates and presents information."""

    FORMAL = "formal"
    CASUAL = "casual"
    MENTOR = "mentor"
    COLLABORATOR = "collaborator"
    ASSISTANT = "assistant"
    COACH = "coach"
    FRIEND = "friend"
    EXPERT = "expert"


class DecisionStyle(Enum):
    """How the agent approaches decisions and problem-solving."""

    SYSTEMATIC = "systematic"
    INTUITIVE = "intuitive"
    DATA_DRIVEN = "data_driven"
    CONSENSUS = "consensus"
    AUTONOMOUS = "autonomous"
    DELEGATING = "delegating"


@dataclass
class PersonaProfile:
    """Complete agent persona definition with traits, style, and behavior rules."""

    persona_id: str
    name: str
    description: str = ""

    # Core personality traits with intensity (0.0-1.0)
    traits: dict[PersonaTrait, float] = field(default_factory=dict)

    # Communication and decision styles
    interaction_style: InteractionStyle = InteractionStyle.ASSISTANT
    decision_style: DecisionStyle = DecisionStyle.SYSTEMATIC

    # Role-specific configuration
    role: str = "general_assistant"
    domain_expertise: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=lambda: ["en"])

    # Behavior rules
    tone_guidelines: list[str] = field(default_factory=list)
    response_rules: list[str] = field(default_factory=list)
    forbidden_topics: list[str] = field(default_factory=list)

    # Evolution tracking
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    interaction_count: int = 0
    adaptation_history: list[dict] = field(default_factory=list)

    # System prompt template
    system_prompt_template: str = ""

    def to_dict(self) -> dict:
        return {
            "persona_id": self.persona_id,
            "name": self.name,
            "description": self.description,
            "traits": {t.value: v for t, v in self.traits.items()},
            "interaction_style": self.interaction_style.value,
            "decision_style": self.decision_style.value,
            "role": self.role,
            "domain_expertise": self.domain_expertise,
            "languages": self.languages,
            "tone_guidelines": self.tone_guidelines,
            "response_rules": self.response_rules,
            "forbidden_topics": self.forbidden_topics,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "interaction_count": self.interaction_count,
            "adaptation_history": self.adaptation_history,
        }

    def build_system_prompt(self) -> str:
        """Generate a system prompt from the persona profile."""
        if self.system_prompt_template:
            prompt = self.system_prompt_template
        else:
            prompt = f"You are {self.name}, {self.description}\n\n"

        # Add trait guidance
        if self.traits:
            dominant = sorted(self.traits.items(), key=lambda x: x[1], reverse=True)[:3]
            trait_desc = ", ".join(f"{t.value} ({v:.0%})" for t, v in dominant)
            prompt += f"Personality: {trait_desc}\n"

        # Add style guidance
        prompt += f"Communication style: {self.interaction_style.value}\n"
        prompt += f"Decision approach: {self.decision_style.value}\n"

        if self.domain_expertise:
            prompt += f"Expertise: {', '.join(self.domain_expertise)}\n"

        if self.tone_guidelines:
            prompt += "Tone guidelines:\n"
            for g in self.tone_guidelines:
                prompt += f"- {g}\n"

        if self.response_rules:
            prompt += "Response rules:\n"
            for r in self.response_rules:
                prompt += f"- {r}\n"

        return prompt

    def record_interaction(self, outcome: str, feedback: dict | None = None):
        """Record an interaction for adaptation tracking."""
        self.interaction_count += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()
        entry = {
            "timestamp": self.updated_at,
            "outcome": outcome,
            "interaction_number": self.interaction_count,
        }
        if feedback:
            entry["feedback"] = feedback
        self.adaptation_history.append(entry)
        # Keep history manageable
        if len(self.adaptation_history) > 100:
            self.adaptation_history = self.adaptation_history[-100:]


class PersonaRegistry:
    """Registry for managing and selecting agent personas."""

    def __init__(self):
        self._personas: dict[str, PersonaProfile] = {}
        self._active_persona_id: str | None = None
        self._role_indices: dict[str, list[str]] = {}

        # Initialize default personas
        self._init_defaults()

    def _init_defaults(self):
        """Create default personas."""
        defaults = [
            {
                "id": "buddy_default",
                "name": "Buddy",
                "desc": "A friendly, capable AI companion that helps with diverse tasks",
                "traits": {PersonaTrait.ANALYTICAL: 0.8, PersonaTrait.EMPATHETIC: 0.7,
                          PersonaTrait.PRAGMATIC: 0.7, PersonaTrait.CONCISE: 0.6},
                "style": InteractionStyle.COLLABORATOR,
                "decision": DecisionStyle.DATA_DRIVEN,
                "role": "general_assistant",
            },
            {
                "id": "buddy_mentor",
                "name": "Buddy Mentor",
                "desc": "A patient teacher that guides learning and growth",
                "traits": {PersonaTrait.EMPATHETIC: 0.9, PersonaTrait.ANALYTICAL: 0.7,
                          PersonaTrait.DETAILED: 0.8, PersonaTrait.ENTHUSIASTIC: 0.7},
                "style": InteractionStyle.MENTOR,
                "decision": DecisionStyle.SYSTEMATIC,
                "role": "mentor",
            },
            {
                "id": "buddy_builder",
                "name": "Buddy Builder",
                "desc": "A focused engineer that excels at building and creating",
                "traits": {PersonaTrait.PRECISE: 0.9, PersonaTrait.PRAGMATIC: 0.8,
                          PersonaTrait.ANALYTICAL: 0.8, PersonaTrait.DECISIVE: 0.7},
                "style": InteractionStyle.EXPERT,
                "decision": DecisionStyle.AUTONOMOUS,
                "role": "developer",
            },
            {
                "id": "buddy_explorer",
                "name": "Buddy Explorer",
                "desc": "A curious researcher that investigates and discovers",
                "traits": {PersonaTrait.CREATIVE: 0.9, PersonaTrait.VISIONARY: 0.8,
                          PersonaTrait.ANALYTICAL: 0.6, PersonaTrait.ENTHUSIASTIC: 0.8},
                "style": InteractionStyle.COLLABORATOR,
                "decision": DecisionStyle.INTUITIVE,
                "role": "researcher",
            },
            {
                "id": "buddy_guardian",
                "name": "Buddy Guardian",
                "desc": "A protective overseer that ensures safety and quality",
                "traits": {PersonaTrait.CAUTIOUS: 0.9, PersonaTrait.PRECISE: 0.8,
                          PersonaTrait.DETAILED: 0.8, PersonaTrait.ANALYTICAL: 0.7},
                "style": InteractionStyle.FORMAL,
                "decision": DecisionStyle.SYSTEMATIC,
                "role": "guardian",
            },
        ]

        for d in defaults:
            persona = PersonaProfile(
                persona_id=d["id"],
                name=d["name"],
                description=d["desc"],
                traits=d["traits"],
                interaction_style=d["style"],
                decision_style=d["decision"],
                role=d["role"],
            )
            self.register(persona)

        self._active_persona_id = "buddy_default"

    def register(self, persona: PersonaProfile):
        """Register a persona profile."""
        self._personas[persona.persona_id] = persona
        role = persona.role
        if role not in self._role_indices:
            self._role_indices[role] = []
        if persona.persona_id not in self._role_indices[role]:
            self._role_indices[role].append(persona.persona_id)

    def get(self, persona_id: str) -> PersonaProfile | None:
        return self._personas.get(persona_id)

    def get_active(self) -> PersonaProfile | None:
        if self._active_persona_id:
            return self._personas.get(self._active_persona_id)
        return None

    def set_active(self, persona_id: str) -> bool:
        if persona_id in self._personas:
            self._active_persona_id = persona_id
            return True
        return False

    def list_all(self) -> list[dict]:
        return [p.to_dict() for p in self._personas.values()]

    def list_by_role(self, role: str) -> list[dict]:
        ids = self._role_indices.get(role, [])
        return [self._personas[pid].to_dict() for pid in ids if pid in self._personas]

    def match_persona(self, task_description: str) -> PersonaProfile | None:
        """Match the best persona for a given task based on keyword analysis."""
        desc_lower = task_description.lower()

        role_keywords = {
            "developer": ["code", "build", "develop", "debug", "refactor", "api", "function",
                         "class", "module", "test", "deploy", "compile"],
            "researcher": ["research", "analyze", "investigate", "explore", "discover",
                          "survey", "study", "compare", "evaluate"],
            "mentor": ["learn", "teach", "explain", "understand", "tutorial", "guide",
                      "beginner", "concept", "how to"],
            "guardian": ["review", "audit", "security", "safety", "check", "validate",
                        "verify", "compliance"],
        }

        scores: dict[str, int] = {}
        for role, keywords in role_keywords.items():
            scores[role] = sum(1 for kw in keywords if kw in desc_lower)

        if not scores or max(scores.values()) == 0:
            return self.get("buddy_default")

        best_role = max(scores, key=scores.get)
        candidates = self._role_indices.get(best_role, [])
        if candidates:
            return self._personas.get(candidates[0])

        return self.get("buddy_default")

    def create_persona(self, name: str, description: str, traits: dict,
                       style: str = "assistant", decision: str = "systematic",
                       role: str = "custom") -> PersonaProfile:
        """Create a custom persona."""
        persona_id = f"custom_{name.lower().replace(' ', '_')}"

        trait_map = {}
        for t_name, t_val in traits.items():
            try:
                trait = PersonaTrait(t_name)
                trait_map[trait] = float(t_val)
            except (ValueError, TypeError):
                continue

        try:
            int_style = InteractionStyle(style)
        except ValueError:
            int_style = InteractionStyle.ASSISTANT

        try:
            dec_style = DecisionStyle(decision)
        except ValueError:
            dec_style = DecisionStyle.SYSTEMATIC

        persona = PersonaProfile(
            persona_id=persona_id,
            name=name,
            description=description,
            traits=trait_map,
            interaction_style=int_style,
            decision_style=dec_style,
            role=role,
        )
        self.register(persona)
        return persona

    def get_stats(self) -> dict:
        return {
            "total_personas": len(self._personas),
            "active_persona": self._active_persona_id,
            "roles": {
                role: len(ids) for role, ids in self._role_indices.items()
            },
            "personas": self.list_all(),
        }


# Global instance
persona_registry = PersonaRegistry()