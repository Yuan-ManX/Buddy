"""Buddy Capability System — Agent skill profiling and dynamic matching

Provides a capability-based agent system where each agent has a dynamic
profile of skills, tools, and domain expertise. The system enables:
- Capability registration and discovery
- Skill-requirement matching for task routing
- Proficiency tracking with decay over time
- Cross-agent capability gap analysis
- Automatic capability suggestion based on task history

Architecture:
    CapabilityRegistry (singleton)
    ├── CapabilityProfile (per-agent capability snapshot)
    ├── CapabilityMatcher (requirement-to-agent matching)
    └── ProficiencyTracker (skill decay and growth tracking)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.capability")


# ══════════════════════════════════════════════════════════════
# Enums & Data Classes
# ══════════════════════════════════════════════════════════════

class CapabilityDomain(str, Enum):
    REASONING = "reasoning"
    CODING = "coding"
    WRITING = "writing"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    RESEARCH = "research"
    PLANNING = "planning"
    COMMUNICATION = "communication"
    TOOL_USE = "tool_use"
    DOMAIN_KNOWLEDGE = "domain_knowledge"


class ProficiencyLevel(str, Enum):
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


@dataclass
class Capability:
    id: str
    name: str
    domain: CapabilityDomain
    description: str = ""
    tags: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    prerequisite_capabilities: list[str] = field(default_factory=list)


@dataclass
class AgentCapability:
    capability_id: str
    proficiency: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE
    score: float = 0.5  # 0.0 - 1.0 numerical proficiency
    usage_count: int = 0
    last_used: str = ""
    first_acquired: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decay_rate: float = 0.01  # Score decay per day when unused


@dataclass
class CapabilityProfile:
    agent_id: str
    agent_name: str
    capabilities: dict[str, AgentCapability] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    overall_score: float = 0.0
    last_updated: str = ""


# ══════════════════════════════════════════════════════════════
# Capability Registry
# ══════════════════════════════════════════════════════════════

class CapabilityRegistry:
    """Manages capability definitions, agent profiles, and requirement matching."""

    NOVICE_THRESHOLD = 0.2
    BEGINNER_THRESHOLD = 0.4
    INTERMEDIATE_THRESHOLD = 0.6
    ADVANCED_THRESHOLD = 0.8
    EXPERT_THRESHOLD = 0.9

    def __init__(self):
        self._capabilities: dict[str, Capability] = {}
        self._profiles: dict[str, CapabilityProfile] = {}
        self._domain_capabilities: dict[CapabilityDomain, list[str]] = {}

    # ── Capability Definitions ──────────────────────────

    def define_capability(self, capability: Capability) -> str:
        """Register a new capability definition."""
        self._capabilities[capability.id] = capability
        if capability.domain not in self._domain_capabilities:
            self._domain_capabilities[capability.domain] = []
        if capability.id not in self._domain_capabilities[capability.domain]:
            self._domain_capabilities[capability.domain].append(capability.id)
        logger.debug(f"Capability defined: {capability.name} ({capability.domain.value})")
        return capability.id

    def get_capability(self, cap_id: str) -> Capability | None:
        return self._capabilities.get(cap_id)

    def list_capabilities(self, domain: CapabilityDomain | None = None) -> list[dict]:
        caps = self._capabilities.values()
        if domain:
            caps = [c for c in caps if c.domain == domain]
        return [
            {
                "id": c.id,
                "name": c.name,
                "domain": c.domain.value,
                "description": c.description,
                "tags": c.tags,
                "required_tools": c.required_tools,
            }
            for c in caps
        ]

    def list_domains(self) -> list[dict]:
        return [
            {
                "domain": d.value,
                "capability_count": len(ids),
            }
            for d, ids in self._domain_capabilities.items()
        ]

    # ── Agent Profile Management ────────────────────────

    def get_or_create_profile(self, agent_id: str, agent_name: str = "") -> CapabilityProfile:
        """Get or create an agent's capability profile."""
        if agent_id not in self._profiles:
            self._profiles[agent_id] = CapabilityProfile(
                agent_id=agent_id,
                agent_name=agent_name,
            )
        return self._profiles[agent_id]

    def add_capability(
        self,
        agent_id: str,
        capability_id: str,
        proficiency: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE,
        score: float = 0.5,
    ):
        """Add or update a capability for an agent."""
        profile = self.get_or_create_profile(agent_id)
        if capability_id not in self._capabilities:
            raise ValueError(f"Unknown capability: {capability_id}")

        if capability_id in profile.capabilities:
            existing = profile.capabilities[capability_id]
            existing.score = max(existing.score, score)
            existing.proficiency = self._score_to_level(score)
            existing.usage_count += 1
            existing.last_used = datetime.now(timezone.utc).isoformat()
        else:
            profile.capabilities[capability_id] = AgentCapability(
                capability_id=capability_id,
                proficiency=proficiency,
                score=score,
                usage_count=1,
                last_used=datetime.now(timezone.utc).isoformat(),
            )

        self._recalculate_profile(profile)

    def record_usage(self, agent_id: str, capability_id: str, success: bool = True):
        """Record usage of a capability, boosting its score."""
        profile = self._profiles.get(agent_id)
        if not profile or capability_id not in profile.capabilities:
            return

        ac = profile.capabilities[capability_id]
        ac.usage_count += 1
        ac.last_used = datetime.now(timezone.utc).isoformat()

        # Boost score on success, slight penalty on failure
        if success:
            ac.score = min(1.0, ac.score + 0.02)
        else:
            ac.score = max(0.0, ac.score - 0.01)

        ac.proficiency = self._score_to_level(ac.score)
        self._recalculate_profile(profile)

    def apply_decay(self):
        """Apply time-based decay to all agent capability scores."""
        now = datetime.now(timezone.utc)
        for profile in self._profiles.values():
            for ac in profile.capabilities.values():
                if ac.last_used:
                    last = datetime.fromisoformat(ac.last_used)
                    days_since = (now - last).days
                    if days_since > 0:
                        ac.score = max(0.0, ac.score - ac.decay_rate * days_since)
                        ac.proficiency = self._score_to_level(ac.score)
            self._recalculate_profile(profile)

    # ── Matching ────────────────────────────────────────

    def find_agents_for_requirements(
        self,
        required_capabilities: list[str],
        min_proficiency: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE,
        min_score: float = 0.5,
    ) -> list[dict]:
        """Find agents that match a set of capability requirements.

        Returns agents ranked by overall match score, with detailed
        capability coverage analysis.
        """
        min_threshold = self._level_to_threshold(min_proficiency)
        results = []

        for agent_id, profile in self._profiles.items():
            match_count = 0
            total_score = 0.0
            missing = []
            matched_caps = []

            for req_cap in required_capabilities:
                ac = profile.capabilities.get(req_cap)
                if ac and ac.score >= max(min_threshold, min_score):
                    match_count += 1
                    total_score += ac.score
                    matched_caps.append({
                        "capability_id": req_cap,
                        "name": self._capabilities.get(req_cap, Capability(id=req_cap, name=req_cap, domain=CapabilityDomain.REASONING)).name,
                        "score": ac.score,
                        "proficiency": ac.proficiency.value,
                    })
                else:
                    missing.append(req_cap)

            coverage = match_count / max(len(required_capabilities), 1)
            avg_score = total_score / max(match_count, 1)

            results.append({
                "agent_id": agent_id,
                "agent_name": profile.agent_name,
                "match_score": coverage * avg_score,
                "coverage": coverage,
                "avg_capability_score": avg_score,
                "matched_count": match_count,
                "total_required": len(required_capabilities),
                "matched_capabilities": matched_caps,
                "missing_capabilities": missing,
                "overall_profile_score": profile.overall_score,
            })

        results.sort(key=lambda r: -r["match_score"])
        return results

    def find_capability_gaps(self, agent_id: str, domain: CapabilityDomain | None = None) -> list[dict]:
        """Identify capability gaps for an agent.

        Returns capabilities the agent doesn't have but could benefit from,
        based on their existing profile and domain patterns.
        """
        profile = self._profiles.get(agent_id)
        if not profile:
            return []

        agent_caps = set(profile.capabilities.keys())
        gaps = []

        for cap_id, cap in self._capabilities.items():
            if cap_id in agent_caps:
                continue
            if domain and cap.domain != domain:
                continue

            # Check prerequisites
            prereqs_met = all(
                p in agent_caps and profile.capabilities[p].score >= 0.4
                for p in cap.prerequisite_capabilities
            )
            if not prereqs_met and cap.prerequisite_capabilities:
                continue

            # Score the gap based on related capabilities
            related_score = 0.0
            if cap.domain in self._domain_capabilities:
                domain_caps = self._domain_capabilities[cap.domain]
                for dc in domain_caps:
                    if dc in agent_caps:
                        related_score += profile.capabilities[dc].score

            gaps.append({
                "capability_id": cap_id,
                "name": cap.name,
                "domain": cap.domain.value,
                "description": cap.description,
                "relevance_score": min(1.0, related_score / max(len(agent_caps), 1)),
                "prerequisites_met": prereqs_met,
            })

        gaps.sort(key=lambda g: -g["relevance_score"])
        return gaps[:20]

    # ── Profile Analysis ────────────────────────────────

    def get_profile(self, agent_id: str) -> CapabilityProfile | None:
        return self._profiles.get(agent_id)

    def get_profile_summary(self, agent_id: str) -> dict | None:
        profile = self._profiles.get(agent_id)
        if not profile:
            return None

        by_domain: dict[str, list[dict]] = {}
        for cap_id, ac in profile.capabilities.items():
            cap = self._capabilities.get(cap_id)
            domain = cap.domain.value if cap else "unknown"
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append({
                "capability_id": cap_id,
                "name": cap.name if cap else cap_id,
                "score": ac.score,
                "proficiency": ac.proficiency.value,
                "usage_count": ac.usage_count,
            })

        return {
            "agent_id": profile.agent_id,
            "agent_name": profile.agent_name,
            "overall_score": profile.overall_score,
            "strengths": profile.strengths,
            "weaknesses": profile.weaknesses,
            "total_capabilities": len(profile.capabilities),
            "capabilities_by_domain": by_domain,
            "last_updated": profile.last_updated,
        }

    # ── Internal ────────────────────────────────────────

    def _score_to_level(self, score: float) -> ProficiencyLevel:
        if score >= self.EXPERT_THRESHOLD:
            return ProficiencyLevel.EXPERT
        if score >= self.ADVANCED_THRESHOLD:
            return ProficiencyLevel.ADVANCED
        if score >= self.INTERMEDIATE_THRESHOLD:
            return ProficiencyLevel.INTERMEDIATE
        if score >= self.BEGINNER_THRESHOLD:
            return ProficiencyLevel.BEGINNER
        return ProficiencyLevel.NOVICE

    def _level_to_threshold(self, level: ProficiencyLevel) -> float:
        thresholds = {
            ProficiencyLevel.NOVICE: self.NOVICE_THRESHOLD,
            ProficiencyLevel.BEGINNER: self.BEGINNER_THRESHOLD,
            ProficiencyLevel.INTERMEDIATE: self.INTERMEDIATE_THRESHOLD,
            ProficiencyLevel.ADVANCED: self.ADVANCED_THRESHOLD,
            ProficiencyLevel.EXPERT: self.EXPERT_THRESHOLD,
            ProficiencyLevel.MASTER: 0.95,
        }
        return thresholds.get(level, self.INTERMEDIATE_THRESHOLD)

    def _recalculate_profile(self, profile: CapabilityProfile):
        """Recalculate aggregate profile metrics."""
        if not profile.capabilities:
            profile.overall_score = 0.0
            profile.strengths = []
            profile.weaknesses = []
            return

        scores = [ac.score for ac in profile.capabilities.values()]
        profile.overall_score = sum(scores) / len(scores)

        # Identify strengths (top 30%) and weaknesses (bottom 30%)
        sorted_caps = sorted(
            profile.capabilities.items(),
            key=lambda x: -x[1].score,
        )
        strength_count = max(1, len(sorted_caps) // 3)
        profile.strengths = [cid for cid, _ in sorted_caps[:strength_count]]
        profile.weaknesses = [cid for cid, _ in sorted_caps[-strength_count:]]

        profile.last_updated = datetime.now(timezone.utc).isoformat()

    # ── Statistics ──────────────────────────────────────

    def get_stats(self) -> dict:
        total_caps = len(self._capabilities)
        total_profiles = len(self._profiles)
        avg_overall = (
            sum(p.overall_score for p in self._profiles.values()) / max(total_profiles, 1)
        )

        domain_counts = {
            d.value: len(ids) for d, ids in self._domain_capabilities.items()
        }

        return {
            "total_capabilities": total_caps,
            "total_profiles": total_profiles,
            "domains": domain_counts,
            "average_profile_score": round(avg_overall, 3),
            "most_common_domain": max(domain_counts, key=domain_counts.get) if domain_counts else "none",
        }


# ── Singleton & Built-in Capabilities ────────────────────

capability_registry = CapabilityRegistry()

# Register foundational capabilities
_builtin_capabilities = [
    Capability(id="cap-reasoning", name="Logical Reasoning", domain=CapabilityDomain.REASONING,
               description="Analyze problems logically, identify patterns, and draw valid conclusions.",
               tags=["logic", "deduction", "induction"]),
    Capability(id="cap-planning", name="Strategic Planning", domain=CapabilityDomain.PLANNING,
               description="Break down complex goals into actionable steps with timelines.",
               tags=["strategy", "roadmap", "milestones"]),
    Capability(id="cap-code-gen", name="Code Generation", domain=CapabilityDomain.CODING,
               description="Write clean, efficient code across multiple programming languages.",
               tags=["python", "javascript", "typescript", "programming"],
               required_tools=["execute_python", "execute_shell"]),
    Capability(id="cap-code-review", name="Code Review", domain=CapabilityDomain.CODING,
               description="Review code for bugs, performance issues, and best practices.",
               tags=["review", "debugging", "optimization"],
               prerequisite_capabilities=["cap-code-gen"]),
    Capability(id="cap-writing", name="Content Writing", domain=CapabilityDomain.WRITING,
               description="Create clear, engaging written content for various formats.",
               tags=["writing", "editing", "documentation"]),
    Capability(id="cap-analysis", name="Data Analysis", domain=CapabilityDomain.ANALYSIS,
               description="Analyze data sets, extract insights, and create visualizations.",
               tags=["data", "statistics", "visualization"],
               required_tools=["execute_python"]),
    Capability(id="cap-research", name="Information Research", domain=CapabilityDomain.RESEARCH,
               description="Gather, evaluate, and synthesize information from multiple sources.",
               tags=["search", "synthesis", "fact-checking"]),
    Capability(id="cap-creative", name="Creative Ideation", domain=CapabilityDomain.CREATIVE,
               description="Generate novel ideas, brainstorm solutions, and think outside the box.",
               tags=["brainstorming", "innovation", "design"]),
    Capability(id="cap-tool-mastery", name="Tool Mastery", domain=CapabilityDomain.TOOL_USE,
               description="Expertly leverage available tools to accomplish complex tasks.",
               tags=["tools", "automation", "orchestration"]),
    Capability(id="cap-domain-expert", name="Domain Expertise", domain=CapabilityDomain.DOMAIN_KNOWLEDGE,
               description="Deep knowledge in specific subject matter domains.",
               tags=["expertise", "specialization"]),
]

for cap in _builtin_capabilities:
    capability_registry.define_capability(cap)