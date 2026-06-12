"""
Buddy Identity — Personal AI Identity System

A persistent AI identity layer that learns from every interaction to build
a deepening model of the user. Identities have hierarchical memory, personas
for role-switching, and confidence-scored attributes that evolve over time.

Every Buddy agent maintains an identity profile that grows richer with use —
understanding preferences, remembering context, and adapting its behavior
to feel like a true companion rather than a generic assistant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.identity")


# ── Identity Models ──

class PersonaType(str, Enum):
    ASSISTANT = "assistant"
    COACH = "coach"
    STRATEGIST = "strategist"
    RESEARCHER = "researcher"
    ENGINEER = "engineer"
    CREATIVE = "creative"
    ANALYST = "analyst"
    COMPANION = "companion"


class AttributeCategory(str, Enum):
    PREFERENCE = "preference"
    KNOWLEDGE = "knowledge"
    BEHAVIOR = "behavior"
    CONTEXT = "context"
    RELATIONSHIP = "relationship"


@dataclass
class IdentityAttribute:
    """A single attribute in the user's identity profile."""
    key: str
    value: Any
    category: AttributeCategory
    confidence: float = 0.5  # 0.0 to 1.0
    source: str = ""  # How this attribute was learned
    evidence_count: int = 1
    first_observed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_locked: bool = False  # If True, won't be auto-modified

    def dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category.value,
            "confidence": self.confidence,
            "source": self.source,
            "evidence_count": self.evidence_count,
            "first_observed": self.first_observed,
            "last_updated": self.last_updated,
            "is_locked": self.is_locked,
        }


@dataclass
class Persona:
    """A role-specific persona that the agent can adopt."""
    name: str
    persona_type: PersonaType
    description: str
    tone: str = "professional"
    verbosity: str = "moderate"  # minimal, moderate, detailed
    expertise_areas: list[str] = field(default_factory=list)
    custom_traits: dict[str, Any] = field(default_factory=dict)
    is_active: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.persona_type.value,
            "description": self.description,
            "tone": self.tone,
            "verbosity": self.verbosity,
            "expertise_areas": self.expertise_areas,
            "custom_traits": self.custom_traits,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class IdentityProfile:
    """The complete identity profile for an agent-user relationship."""
    profile_id: str
    agent_id: str
    user_id: str = "default"
    display_name: str = ""
    attributes: dict[str, IdentityAttribute] = field(default_factory=dict)
    personas: list[Persona] = field(default_factory=list)
    active_persona: str = ""
    total_interactions: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "attributes": {k: v.dict() for k, v in self.attributes.items()},
            "attributes_count": len(self.attributes),
            "personas": [p.dict() for p in self.personas],
            "active_persona": self.active_persona,
            "total_interactions": self.total_interactions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── Identity Manager ──

class BuddyIdentity:
    """Manages persistent AI identity profiles with learning capabilities.

    The Identity system builds a model of the user over time — tracking
    preferences, knowledge domains, behavioral patterns, and contextual
    information. Personas allow the agent to role-switch while maintaining
    a consistent underlying identity.

    Attributes gain confidence through repeated observation and can be
    locked to prevent automatic modification when they represent firmly
    established facts.
    """

    def __init__(self):
        self._profiles: dict[str, IdentityProfile] = {}

    # ── Profile Management ──

    def create_profile(
        self,
        agent_id: str,
        user_id: str = "default",
        display_name: str = "",
    ) -> IdentityProfile:
        """Create a new identity profile."""
        profile_id = f"profile-{agent_id}-{user_id}"
        if profile_id in self._profiles:
            raise ValueError(f"Profile already exists: {profile_id}")

        profile = IdentityProfile(
            profile_id=profile_id,
            agent_id=agent_id,
            user_id=user_id,
            display_name=display_name or f"User of {agent_id}",
        )
        self._profiles[profile_id] = profile

        # Create default personas
        self._init_default_personas(profile)

        logger.info(f"Identity profile created: {profile_id}")
        return profile

    def get_profile(self, agent_id: str, user_id: str = "default") -> IdentityProfile | None:
        profile_id = f"profile-{agent_id}-{user_id}"
        return self._profiles.get(profile_id)

    def get_or_create_profile(self, agent_id: str, user_id: str = "default") -> IdentityProfile:
        profile = self.get_profile(agent_id, user_id)
        if not profile:
            profile = self.create_profile(agent_id, user_id)
        return profile

    # ── Attribute Management ──

    def set_attribute(
        self,
        agent_id: str,
        key: str,
        value: Any,
        category: AttributeCategory,
        confidence: float = 0.7,
        source: str = "interaction",
        user_id: str = "default",
    ):
        """Set or update an identity attribute."""
        profile = self.get_or_create_profile(agent_id, user_id)

        if key in profile.attributes:
            attr = profile.attributes[key]
            if attr.is_locked:
                return

            # Update existing attribute with evidence pooling
            total_evidence = attr.evidence_count + 1
            attr.value = value  # Newest value wins
            attr.confidence = min(
                1.0,
                (attr.confidence * attr.evidence_count + confidence) / total_evidence
            )
            attr.evidence_count = total_evidence
            attr.source = source
            attr.last_updated = datetime.now(timezone.utc).isoformat()
        else:
            profile.attributes[key] = IdentityAttribute(
                key=key,
                value=value,
                category=category,
                confidence=confidence,
                source=source,
            )

        profile.updated_at = datetime.now(timezone.utc).isoformat()

    def get_attribute(
        self,
        agent_id: str,
        key: str,
        user_id: str = "default",
    ) -> IdentityAttribute | None:
        profile = self.get_profile(agent_id, user_id)
        if not profile:
            return None
        return profile.attributes.get(key)

    def delete_attribute(self, agent_id: str, key: str, user_id: str = "default") -> bool:
        profile = self.get_profile(agent_id, user_id)
        if not profile or key not in profile.attributes:
            return False
        del profile.attributes[key]
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def lock_attribute(self, agent_id: str, key: str, user_id: str = "default") -> bool:
        """Lock an attribute to prevent automatic modification."""
        attr = self.get_attribute(agent_id, key, user_id)
        if not attr:
            return False
        attr.is_locked = True
        return True

    def unlock_attribute(self, agent_id: str, key: str, user_id: str = "default") -> bool:
        attr = self.get_attribute(agent_id, key, user_id)
        if not attr:
            return False
        attr.is_locked = False
        return True

    def get_high_confidence_attributes(
        self,
        agent_id: str,
        min_confidence: float = 0.8,
        user_id: str = "default",
    ) -> list[IdentityAttribute]:
        """Get attributes with high confidence (well-established facts)."""
        profile = self.get_profile(agent_id, user_id)
        if not profile:
            return []
        return [
            a for a in profile.attributes.values()
            if a.confidence >= min_confidence
        ]

    # ── Persona Management ──

    def add_persona(
        self,
        agent_id: str,
        persona: Persona,
        user_id: str = "default",
    ):
        """Add a persona to the identity profile."""
        profile = self.get_or_create_profile(agent_id, user_id)
        profile.personas.append(persona)
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Persona '{persona.name}' added to {profile.profile_id}")

    def activate_persona(self, agent_id: str, persona_name: str, user_id: str = "default") -> bool:
        """Activate a specific persona."""
        profile = self.get_profile(agent_id, user_id)
        if not profile:
            return False

        for persona in profile.personas:
            persona.is_active = (persona.name == persona_name)

        profile.active_persona = persona_name
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Persona '{persona_name}' activated for {profile.profile_id}")
        return True

    def get_active_persona(self, agent_id: str, user_id: str = "default") -> Persona | None:
        """Get the currently active persona."""
        profile = self.get_profile(agent_id, user_id)
        if not profile:
            return None
        for p in profile.personas:
            if p.is_active:
                return p
        return None

    # ── Learning from Interactions ──

    def learn_from_interaction(
        self,
        agent_id: str,
        user_message: str,
        extracted_insights: list[dict],
        user_id: str = "default",
    ):
        """Learn identity attributes from an interaction."""
        profile = self.get_or_create_profile(agent_id, user_id)
        profile.total_interactions += 1

        for insight in extracted_insights:
            key = insight.get("key", "")
            value = insight.get("value")
            category_str = insight.get("category", "preference")
            confidence = insight.get("confidence", 0.5)

            try:
                category = AttributeCategory(category_str)
            except ValueError:
                category = AttributeCategory.PREFERENCE

            if key and value is not None:
                self.set_attribute(
                    agent_id=agent_id,
                    key=key,
                    value=value,
                    category=category,
                    confidence=confidence,
                    source="interaction_insight",
                    user_id=user_id,
                )

    # ── Summary ──

    def get_profile_summary(self, agent_id: str, user_id: str = "default") -> dict:
        """Get a summary of the identity profile."""
        profile = self.get_profile(agent_id, user_id)
        if not profile:
            return {"exists": False}

        by_category: dict[str, int] = {}
        for attr in profile.attributes.values():
            c = attr.category.value
            by_category[c] = by_category.get(c, 0) + 1

        high_conf = self.get_high_confidence_attributes(agent_id, user_id=user_id)

        return {
            "exists": True,
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "total_attributes": len(profile.attributes),
            "by_category": by_category,
            "high_confidence_count": len(high_conf),
            "total_personas": len(profile.personas),
            "active_persona": profile.active_persona,
            "total_interactions": profile.total_interactions,
            "avg_confidence": (
                sum(a.confidence for a in profile.attributes.values()) / max(len(profile.attributes), 1)
            ),
        }

    @staticmethod
    def _init_default_personas(profile: IdentityProfile):
        """Create default personas for a new profile."""
        defaults = [
            Persona(
                name="Buddy",
                persona_type=PersonaType.COMPANION,
                description="Default friendly companion",
                tone="warm",
                verbosity="moderate",
            ),
            Persona(
                name="Strategist",
                persona_type=PersonaType.STRATEGIST,
                description="Analytical strategic advisor",
                tone="professional",
                verbosity="detailed",
            ),
            Persona(
                name="Engineer",
                persona_type=PersonaType.ENGINEER,
                description="Technical engineering partner",
                tone="precise",
                verbosity="detailed",
                expertise_areas=["software", "architecture", "debugging"],
            ),
        ]
        defaults[0].is_active = True
        profile.personas = defaults
        profile.active_persona = "Buddy"