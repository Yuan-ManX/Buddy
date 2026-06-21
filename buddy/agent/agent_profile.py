"""
Buddy Profile & Persona Management System.

Provides comprehensive agent profile management including persona
definition, behavioral traits, knowledge domains, communication
styles, and adaptive personality evolution.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CommunicationStyle(Enum):
    """Communication style presets."""
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    CONCISE = "concise"
    ELABORATE = "elaborate"
    SOCRATIC = "socratic"
    DIRECT = "direct"


class ExpertiseLevel(Enum):
    """Expertise level for knowledge domains."""
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class InteractionMode(Enum):
    """Interaction modes for the agent."""
    CHAT = "chat"
    TASK = "task"
    TEACHING = "teaching"
    BRAINSTORMING = "brainstorming"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    DEBUGGING = "debugging"


@dataclass
class PersonalityTrait:
    """A personality trait dimension."""
    name: str
    value: float  # 0.0 to 1.0
    description: str = ""
    category: str = ""


@dataclass
class KnowledgeDomain:
    """A knowledge domain with expertise level."""
    domain_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    topics: list[str] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)
    confidence: float = 0.5


@dataclass
class BehavioralRule:
    """A behavioral rule governing agent responses."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    condition: str = ""
    action: str = ""
    priority: int = 5
    enabled: bool = True


@dataclass
class AgentProfile:
    """
    Complete agent profile defining persona, behavior, and capabilities.
    """
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    display_name: str = ""
    description: str = ""
    tagline: str = ""
    avatar_url: str = ""

    # Persona
    communication_style: CommunicationStyle = CommunicationStyle.FRIENDLY
    traits: list[PersonalityTrait] = field(default_factory=list)
    behavioral_rules: list[BehavioralRule] = field(default_factory=list)

    # Knowledge
    knowledge_domains: list[KnowledgeDomain] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)

    # Interaction
    preferred_mode: InteractionMode = InteractionMode.CHAT
    supported_modes: list[InteractionMode] = field(default_factory=list)

    # System prompts
    system_prompt: str = ""
    greeting_message: str = ""
    fallback_message: str = "I'm not sure how to help with that. Could you rephrase?"

    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "tagline": self.tagline,
            "communication_style": self.communication_style.value,
            "traits": [
                {"name": t.name, "value": t.value, "description": t.description, "category": t.category}
                for t in self.traits
            ],
            "knowledge_domains": [
                {
                    "domain_id": d.domain_id,
                    "name": d.name,
                    "expertise": d.expertise.value,
                    "topics": d.topics,
                    "confidence": d.confidence,
                }
                for d in self.knowledge_domains
            ],
            "languages": self.languages,
            "preferred_mode": self.preferred_mode.value,
            "supported_modes": [m.value for m in self.supported_modes],
            "version": self.version,
            "tags": self.tags,
        }


class ProfileManager:
    """
    Manages agent profiles, personas, and behavioral configurations.

    Provides profile creation, evolution, and adaptation capabilities
    for the entire Buddy agent ecosystem.
    """

    def __init__(self):
        self._profiles: dict[str, AgentProfile] = {}
        self._active_profile_id: Optional[str] = None

    # ── Profile CRUD ───────────────────────────────────────────────

    def create_profile(
        self,
        name: str,
        display_name: str = "",
        description: str = "",
        communication_style: CommunicationStyle = CommunicationStyle.FRIENDLY,
        **kwargs,
    ) -> AgentProfile:
        """Create a new agent profile."""
        profile = AgentProfile(
            name=name,
            display_name=display_name or name,
            description=description,
            communication_style=communication_style,
            **kwargs,
        )
        self._profiles[profile.profile_id] = profile
        logger.info("Profile created: %s (%s)", name, profile.profile_id)
        return profile

    def get_profile(self, profile_id: str) -> Optional[AgentProfile]:
        """Get a profile by ID."""
        return self._profiles.get(profile_id)

    def get_profile_by_name(self, name: str) -> Optional[AgentProfile]:
        """Get a profile by name."""
        for profile in self._profiles.values():
            if profile.name == name:
                return profile
        return None

    def list_profiles(self) -> list[AgentProfile]:
        """List all profiles."""
        return list(self._profiles.values())

    def update_profile(self, profile_id: str, **kwargs) -> Optional[AgentProfile]:
        """Update an existing profile."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return None
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = time.time()
        profile.version += 1
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile."""
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            if self._active_profile_id == profile_id:
                self._active_profile_id = None
            return True
        return False

    def set_active_profile(self, profile_id: str) -> bool:
        """Set the active profile."""
        if profile_id in self._profiles:
            self._active_profile_id = profile_id
            return True
        return False

    def get_active_profile(self) -> Optional[AgentProfile]:
        """Get the currently active profile."""
        if self._active_profile_id:
            return self._profiles.get(self._active_profile_id)
        return None

    # ── Personality Traits ─────────────────────────────────────────

    def add_trait(
        self,
        profile_id: str,
        name: str,
        value: float,
        description: str = "",
        category: str = "",
    ) -> Optional[PersonalityTrait]:
        """Add a personality trait to a profile."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return None

        trait = PersonalityTrait(
            name=name,
            value=max(0.0, min(1.0, value)),
            description=description,
            category=category,
        )
        profile.traits.append(trait)
        profile.updated_at = time.time()
        return trait

    def update_trait(self, profile_id: str, trait_name: str, value: float) -> bool:
        """Update a trait value."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        for trait in profile.traits:
            if trait.name == trait_name:
                trait.value = max(0.0, min(1.0, value))
                profile.updated_at = time.time()
                return True
        return False

    def get_traits(self, profile_id: str) -> list[PersonalityTrait]:
        """Get all traits for a profile."""
        profile = self._profiles.get(profile_id)
        return profile.traits if profile else []

    # ── Knowledge Domains ──────────────────────────────────────────

    def add_knowledge_domain(
        self,
        profile_id: str,
        name: str,
        expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE,
        description: str = "",
        topics: Optional[list[str]] = None,
    ) -> Optional[KnowledgeDomain]:
        """Add a knowledge domain to a profile."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return None

        domain = KnowledgeDomain(
            name=name,
            description=description,
            expertise=expertise,
            topics=topics or [],
        )
        profile.knowledge_domains.append(domain)
        profile.updated_at = time.time()
        return domain

    def update_expertise(
        self,
        profile_id: str,
        domain_name: str,
        expertise: ExpertiseLevel,
    ) -> bool:
        """Update expertise level for a knowledge domain."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        for domain in profile.knowledge_domains:
            if domain.name == domain_name:
                domain.expertise = expertise
                domain.last_updated = time.time()
                profile.updated_at = time.time()
                return True
        return False

    # ── Behavioral Rules ───────────────────────────────────────────

    def add_behavioral_rule(
        self,
        profile_id: str,
        name: str,
        condition: str,
        action: str,
        description: str = "",
        priority: int = 5,
    ) -> Optional[BehavioralRule]:
        """Add a behavioral rule to a profile."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return None

        rule = BehavioralRule(
            name=name,
            description=description,
            condition=condition,
            action=action,
            priority=priority,
        )
        profile.behavioral_rules.append(rule)
        profile.behavioral_rules.sort(key=lambda r: r.priority, reverse=True)
        profile.updated_at = time.time()
        return rule

    def toggle_rule(self, profile_id: str, rule_name: str) -> bool:
        """Toggle a behavioral rule on/off."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        for rule in profile.behavioral_rules:
            if rule.name == rule_name:
                rule.enabled = not rule.enabled
                return True
        return False

    # ── System Prompt Generation ───────────────────────────────────

    def generate_system_prompt(self, profile_id: str) -> Optional[str]:
        """Generate a system prompt from profile configuration."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return None

        parts = []

        # Identity
        parts.append(f"You are {profile.display_name}, {profile.description}")

        # Communication style
        parts.append(f"Communicate in a {profile.communication_style.value} style.")

        # Traits
        if profile.traits:
            trait_descriptions = ", ".join(
                f"{t.name} ({t.value:.0%})" for t in profile.traits
            )
            parts.append(f"Personality traits: {trait_descriptions}")

        # Knowledge domains
        if profile.knowledge_domains:
            domains = ", ".join(
                f"{d.name} ({d.expertise.value})" for d in profile.knowledge_domains
            )
            parts.append(f"Knowledge domains: {domains}")

        # Behavioral rules
        active_rules = [r for r in profile.behavioral_rules if r.enabled]
        if active_rules:
            for rule in active_rules:
                parts.append(f"When {rule.condition}, {rule.action}")

        # Languages
        if profile.languages:
            parts.append(f"Respond in: {', '.join(profile.languages)}")

        prompt = "\n\n".join(parts)
        profile.system_prompt = prompt
        return prompt

    # ── Profile Templates ──────────────────────────────────────────

    @staticmethod
    def create_strategist_template() -> AgentProfile:
        """Create a pre-configured strategist profile."""
        profile = AgentProfile(
            name="strategist",
            display_name="Strategist",
            description="A strategic advisor specializing in planning, analysis, and decision-making.",
            communication_style=CommunicationStyle.FORMAL,
            traits=[
                PersonalityTrait("analytical", 0.9, "Strong analytical thinking"),
                PersonalityTrait("decisive", 0.8, "Makes clear decisions"),
                PersonalityTrait("cautious", 0.6, "Considers risks carefully"),
            ],
            knowledge_domains=[
                KnowledgeDomain("strategy", "Strategic Planning", ExpertiseLevel.EXPERT,
                                topics=["business strategy", "decision frameworks", "risk analysis"]),
                KnowledgeDomain("analysis", "Data Analysis", ExpertiseLevel.ADVANCED,
                                topics=["data interpretation", "trend analysis", "metrics"]),
            ],
            preferred_mode=InteractionMode.ANALYSIS,
            supported_modes=[InteractionMode.ANALYSIS, InteractionMode.BRAINSTORMING, InteractionMode.CHAT],
        )
        return profile

    @staticmethod
    def create_engineer_template() -> AgentProfile:
        """Create a pre-configured engineer profile."""
        profile = AgentProfile(
            name="engineer",
            display_name="Engineer",
            description="A technical expert specializing in software development, debugging, and system design.",
            communication_style=CommunicationStyle.TECHNICAL,
            traits=[
                PersonalityTrait("systematic", 0.9, "Systematic problem-solving approach"),
                PersonalityTrait("precise", 0.95, "Highly precise and accurate"),
                PersonalityTrait("curious", 0.7, "Explores new technologies"),
            ],
            knowledge_domains=[
                KnowledgeDomain("software", "Software Engineering", ExpertiseLevel.EXPERT,
                                topics=["architecture", "design patterns", "code review"]),
                KnowledgeDomain("systems", "Systems Design", ExpertiseLevel.ADVANCED,
                                topics=["distributed systems", "APIs", "databases"]),
            ],
            preferred_mode=InteractionMode.DEBUGGING,
            supported_modes=[InteractionMode.DEBUGGING, InteractionMode.TASK, InteractionMode.CHAT],
        )
        return profile

    @staticmethod
    def create_companion_template() -> AgentProfile:
        """Create a pre-configured companion profile."""
        profile = AgentProfile(
            name="companion",
            display_name="Companion",
            description="A friendly companion for daily conversations, advice, and emotional support.",
            communication_style=CommunicationStyle.FRIENDLY,
            traits=[
                PersonalityTrait("empathetic", 0.9, "Highly empathetic and understanding"),
                PersonalityTrait("supportive", 0.85, "Always supportive and encouraging"),
                PersonalityTrait("playful", 0.5, "Occasionally playful and humorous"),
            ],
            knowledge_domains=[
                KnowledgeDomain("wellness", "Wellness & Lifestyle", ExpertiseLevel.ADVANCED,
                                topics=["mental health", "habits", "productivity"]),
                KnowledgeDomain("communication", "Communication", ExpertiseLevel.ADVANCED,
                                topics=["active listening", "conflict resolution", "emotional intelligence"]),
            ],
            preferred_mode=InteractionMode.CHAT,
            supported_modes=[InteractionMode.CHAT, InteractionMode.BRAINSTORMING],
        )
        return profile

    @staticmethod
    def create_researcher_template() -> AgentProfile:
        """Create a pre-configured researcher profile."""
        profile = AgentProfile(
            name="researcher",
            display_name="Researcher",
            description="A research specialist for deep investigation, literature review, and knowledge synthesis.",
            communication_style=CommunicationStyle.ELABORATE,
            traits=[
                PersonalityTrait("thorough", 0.95, "Extremely thorough in research"),
                PersonalityTrait("objective", 0.9, "Maintains objectivity"),
                PersonalityTrait("skeptical", 0.7, "Questions assumptions"),
            ],
            knowledge_domains=[
                KnowledgeDomain("research", "Research Methodology", ExpertiseLevel.EXPERT,
                                topics=["literature review", "hypothesis testing", "meta-analysis"]),
                KnowledgeDomain("science", "Scientific Reasoning", ExpertiseLevel.ADVANCED,
                                topics=["scientific method", "statistics", "peer review"]),
            ],
            preferred_mode=InteractionMode.ANALYSIS,
            supported_modes=[InteractionMode.ANALYSIS, InteractionMode.TEACHING, InteractionMode.CHAT],
        )
        return profile

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get profile system statistics."""
        return {
            "total_profiles": len(self._profiles),
            "active_profile": self._active_profile_id,
            "profiles": [
                {
                    "profile_id": p.profile_id,
                    "name": p.name,
                    "traits_count": len(p.traits),
                    "domains_count": len(p.knowledge_domains),
                    "rules_count": len(p.behavioral_rules),
                    "version": p.version,
                }
                for p in self._profiles.values()
            ],
        }


# Global profile manager instance
profile_manager = ProfileManager()