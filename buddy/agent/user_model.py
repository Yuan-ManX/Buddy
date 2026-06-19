"""Buddy User Model Engine — cross-session user profiling and dialectic understanding

Builds and maintains a deepening model of each user across sessions,
tracking preferences, behavioral patterns, domain expertise, and evolving
communication styles. Forms the foundation for personalized agent interactions.
"""
from __future__ import annotations
import logging
import uuid
import math
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from collections import defaultdict

logger = logging.getLogger("buddy.user_model")


# ---------------------------------------------------------------------------
# Core Types
# ---------------------------------------------------------------------------

class TraitDimension(str, Enum):
    """Dimensions of user profiling."""
    COMMUNICATION = "communication"       # Style, verbosity, formality
    DOMAIN = "domain"                     # Knowledge areas, expertise
    BEHAVIORAL = "behavioral"             # Interaction patterns, habits
    PREFERENCE = "preference"             # Likes, dislikes, tool preferences
    EMOTIONAL = "emotional"               # Emotional patterns, triggers
    GOAL = "goal"                         # Long-term objectives, projects
    SOCIAL = "social"                     # Collaboration style, team preferences
    LEARNING = "learning"                 # Learning style, knowledge absorption


class ConfidenceLevel(str, Enum):
    """Confidence in a trait observation."""
    SPECULATIVE = "speculative"    # Single observation, low confidence
    EMERGING = "emerging"          # 2-3 reinforcing observations
    CONFIRMED = "confirmed"        # 4-7 consistent observations
    ESTABLISHED = "established"    # 8+ consistent observations
    DEFINITIVE = "definitive"      # Long-term pattern, high confidence


@dataclass
class UserTrait:
    """A single inferred trait about the user."""
    trait_id: str
    dimension: TraitDimension
    key: str
    value: Any
    confidence: ConfidenceLevel = ConfidenceLevel.SPECULATIVE
    evidence_count: int = 1
    first_observed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_observed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supporting_sessions: list[str] = field(default_factory=list)
    contradicting_count: int = 0
    stability_score: float = 1.0  # 0.0-1.0, how stable is this trait


@dataclass
class InteractionSnapshot:
    """A single interaction observation used for trait inference."""
    snapshot_id: str
    session_id: str
    agent_id: str
    timestamp: str
    context_type: str  # "chat", "tool_use", "feedback", "preference_statement"
    raw_content: str
    extracted_signals: dict[str, Any] = field(default_factory=dict)
    emotional_valence: float = 0.0  # -1.0 to 1.0


@dataclass
class UserProfile:
    """Complete user profile across all dimensions."""
    user_id: str
    profiles: dict[TraitDimension, dict[str, UserTrait]] = field(default_factory=dict)
    interaction_count: int = 0
    total_sessions: int = 0
    first_interaction: str | None = None
    last_interaction: str | None = None
    dominant_dimensions: list[TraitDimension] = field(default_factory=list)
    profile_version: int = 1

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "interaction_count": self.interaction_count,
            "total_sessions": self.total_sessions,
            "first_interaction": self.first_interaction,
            "last_interaction": self.last_interaction,
            "dominant_dimensions": [d.value for d in self.dominant_dimensions],
            "profile_version": self.profile_version,
            "traits": {
                dim.value: {
                    key: {
                        "value": trait.value,
                        "confidence": trait.confidence.value,
                        "evidence_count": trait.evidence_count,
                        "stability": trait.stability_score,
                    }
                    for key, trait in traits.items()
                }
                for dim, traits in self.profiles.items()
            },
        }


# ---------------------------------------------------------------------------
# Signal Extractor
# ---------------------------------------------------------------------------

class SignalExtractor:
    """Extracts behavioral signals from raw interaction text."""

    # Communication style indicators
    COMMUNICATION_MARKERS: dict[str, list[str]] = {
        "verbose": ["elaborate", "detailed", "in-depth", "thorough", "comprehensive"],
        "concise": ["brief", "short", "quick", "concise", "summary", "tldr"],
        "formal": ["dear", "sincerely", "regards", "kindly", "please advise"],
        "casual": ["hey", "cool", "awesome", "btw", "lol", "thx", "np"],
        "visual": ["diagram", "chart", "visual", "show me", "draw", "graph"],
        "textual": ["explain", "describe", "write", "text", "document"],
    }

    # Domain indicators
    DOMAIN_MARKERS: dict[str, list[str]] = {
        "programming": ["code", "function", "api", "debug", "deploy", "python", "javascript", "typescript", "react", "docker"],
        "data_science": ["data", "model", "train", "ml", "ai", "neural", "dataset", "pandas", "numpy", "statistics"],
        "devops": ["ci/cd", "pipeline", "kubernetes", "aws", "cloud", "terraform", "ansible", "monitoring"],
        "design": ["ui", "ux", "design", "css", "layout", "color", "typography", "figma", "sketch"],
        "business": ["strategy", "roi", "kpi", "revenue", "market", "customer", "sales", "product"],
        "writing": ["article", "blog", "content", "essay", "draft", "edit", "proofread", "tone"],
        "research": ["research", "study", "paper", "analysis", "literature", "hypothesis", "methodology"],
        "math": ["equation", "formula", "theorem", "proof", "algebra", "calculus", "statistics", "probability"],
    }

    # Preference indicators
    PREFERENCE_PATTERNS: list[tuple[str, str]] = [
        (r"i prefer (.*?)(?:\.|$|\,)", "explicit_preference"),
        (r"i like (.*?)(?:\.|$|\,)", "positive_affinity"),
        (r"i don't like (.*?)(?:\.|$|\,)", "negative_affinity"),
        (r"i use (.*?)(?:for|to|\.|$|\,)", "tool_usage"),
        (r"i usually (.*?)(?:\.|$|\,)", "habit_pattern"),
        (r"my workflow (.*?)(?:\.|$|\,)", "workflow_pattern"),
    ]

    def extract(self, text: str, context_type: str) -> dict[str, Any]:
        """Extract signals from a single interaction."""
        text_lower = text.lower()
        signals: dict[str, Any] = {
            "context_type": context_type,
            "communication_style": self._extract_communication_style(text_lower),
            "domains": self._extract_domains(text_lower),
            "preferences": self._extract_preferences(text_lower),
            "complexity": self._estimate_complexity(text),
        }
        return signals

    def _extract_communication_style(self, text: str) -> dict[str, float]:
        scores: dict[str, float] = {}
        for style, markers in self.COMMUNICATION_MARKERS.items():
            count = sum(1 for m in markers if m in text)
            scores[style] = min(count / 2.0, 1.0)
        return scores

    def _extract_domains(self, text: str) -> dict[str, float]:
        scores: dict[str, float] = {}
        for domain, markers in self.DOMAIN_MARKERS.items():
            count = sum(1 for m in markers if m in text)
            if count > 0:
                scores[domain] = min(count / 3.0, 1.0)
        return scores

    def _extract_preferences(self, text: str) -> list[dict[str, str]]:
        preferences = []
        import re
        for pattern, pref_type in self.PREFERENCE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                preferences.append({
                    "type": pref_type,
                    "content": match.strip()[:200],
                })
        return preferences

    def _estimate_complexity(self, text: str) -> float:
        """Estimate interaction complexity based on various signals."""
        words = text.split()
        if len(words) < 5:
            return 0.1
        avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
        unique_ratio = len(set(words)) / max(len(words), 1)
        complexity = (avg_word_len / 10.0 * 0.4 + unique_ratio * 0.3 + min(len(words) / 200.0, 1.0) * 0.3)
        return round(min(complexity, 1.0), 3)


# ---------------------------------------------------------------------------
# Trait Inference Engine
# ---------------------------------------------------------------------------

class TraitInferenceEngine:
    """Infers user traits from accumulated interaction signals."""

    def __init__(self):
        self.extractor = SignalExtractor()
        self._observation_weights: dict[str, float] = {
            "chat": 0.5,
            "tool_use": 0.7,
            "feedback": 1.0,
            "preference_statement": 1.2,
        }

    def infer_from_snapshot(
        self,
        snapshot: InteractionSnapshot,
        existing_traits: dict[TraitDimension, dict[str, UserTrait]],
    ) -> tuple[list[UserTrait], list[UserTrait]]:
        """Infer new and updated traits from an interaction snapshot.

        Returns (new_traits, updated_traits).
        """
        signals = snapshot.extracted_signals
        weight = self._observation_weights.get(snapshot.context_type, 0.5)
        new_traits: list[UserTrait] = []
        updated_traits: list[UserTrait] = []

        # Communication style traits
        comm = signals.get("communication_style", {})
        for style, score in comm.items():
            if score > 0.3:
                trait = self._upsert_trait(
                    existing_traits,
                    TraitDimension.COMMUNICATION,
                    f"style_{style}",
                    score,
                    snapshot,
                    weight,
                )
                if trait.trait_id not in [t.trait_id for t in existing_traits.get(TraitDimension.COMMUNICATION, {}).values()]:
                    new_traits.append(trait)
                else:
                    updated_traits.append(trait)

        # Domain expertise traits
        domains = signals.get("domains", {})
        for domain, score in domains.items():
            if score > 0.2:
                trait = self._upsert_trait(
                    existing_traits,
                    TraitDimension.DOMAIN,
                    f"domain_{domain}",
                    score,
                    snapshot,
                    weight,
                )
                if trait.trait_id not in [t.trait_id for t in existing_traits.get(TraitDimension.DOMAIN, {}).values()]:
                    new_traits.append(trait)
                else:
                    updated_traits.append(trait)

        # Preference traits
        preferences = signals.get("preferences", [])
        for pref in preferences:
            trait = self._upsert_trait(
                existing_traits,
                TraitDimension.PREFERENCE,
                f"pref_{pref['type']}_{hash(pref['content']) % 10000}",
                pref["content"],
                snapshot,
                weight * 1.5,
            )
            if trait.trait_id not in [t.trait_id for t in existing_traits.get(TraitDimension.PREFERENCE, {}).values()]:
                new_traits.append(trait)
            else:
                updated_traits.append(trait)

        return new_traits, updated_traits

    def _upsert_trait(
        self,
        existing: dict[TraitDimension, dict[str, UserTrait]],
        dimension: TraitDimension,
        key: str,
        value: Any,
        snapshot: InteractionSnapshot,
        weight: float,
    ) -> UserTrait:
        dim_traits = existing.get(dimension, {})
        existing_trait = dim_traits.get(key)

        if existing_trait:
            existing_trait.evidence_count += 1
            existing_trait.last_observed = snapshot.timestamp
            existing_trait.supporting_sessions.append(snapshot.session_id)
            existing_trait.stability_score = min(
                existing_trait.stability_score + weight * 0.05, 1.0
            )
            existing_trait.confidence = self._compute_confidence(existing_trait.evidence_count)
            return existing_trait

        return UserTrait(
            trait_id=f"trait-{uuid.uuid4().hex[:12]}",
            dimension=dimension,
            key=key,
            value=value,
            confidence=ConfidenceLevel.SPECULATIVE,
            evidence_count=1,
            supporting_sessions=[snapshot.session_id],
            stability_score=weight * 0.3,
        )

    def _compute_confidence(self, evidence_count: int) -> ConfidenceLevel:
        if evidence_count >= 12:
            return ConfidenceLevel.DEFINITIVE
        elif evidence_count >= 8:
            return ConfidenceLevel.ESTABLISHED
        elif evidence_count >= 4:
            return ConfidenceLevel.CONFIRMED
        elif evidence_count >= 2:
            return ConfidenceLevel.EMERGING
        return ConfidenceLevel.SPECULATIVE


# ---------------------------------------------------------------------------
# Profile Evolution
# ---------------------------------------------------------------------------

class ProfileEvolutionEngine:
    """Manages profile evolution, decay, and contradiction resolution."""

    def __init__(self):
        self.decay_rate = 0.01  # Per-day stability decay for inactive traits
        self.contradiction_threshold = 3  # Contradictions before trait re-evaluation

    def apply_temporal_decay(self, profile: UserProfile) -> list[UserTrait]:
        """Apply time-based decay to trait stability scores."""
        now = datetime.now(timezone.utc)
        decayed: list[UserTrait] = []

        for dim, traits in profile.profiles.items():
            for key, trait in list(traits.items()):
                last_obs = datetime.fromisoformat(trait.last_observed)
                days_inactive = (now - last_obs).days

                if days_inactive > 7:
                    decay = self.decay_rate * (days_inactive - 7)
                    trait.stability_score = max(0.1, trait.stability_score - decay)

                    if trait.stability_score < 0.2:
                        trait.confidence = ConfidenceLevel.SPECULATIVE
                        decayed.append(trait)
                    elif trait.stability_score < 0.4:
                        if trait.confidence in (ConfidenceLevel.ESTABLISHED, ConfidenceLevel.DEFINITIVE):
                            trait.confidence = ConfidenceLevel.CONFIRMED
                            decayed.append(trait)

        return decayed

    def resolve_contradiction(
        self,
        trait: UserTrait,
        evidence: dict[str, Any],
    ) -> UserTrait | None:
        """Resolve contradictions in trait evidence."""
        trait.contradicting_count += 1

        if trait.contradicting_count >= self.contradiction_threshold:
            trait.stability_score = max(0.1, trait.stability_score - 0.3)
            trait.confidence = self._downgrade_confidence(trait.confidence)

            if trait.stability_score < 0.15:
                return None  # Trait should be removed

        return trait

    def _downgrade_confidence(self, level: ConfidenceLevel) -> ConfidenceLevel:
        order = [
            ConfidenceLevel.DEFINITIVE,
            ConfidenceLevel.ESTABLISHED,
            ConfidenceLevel.CONFIRMED,
            ConfidenceLevel.EMERGING,
            ConfidenceLevel.SPECULATIVE,
        ]
        try:
            idx = order.index(level)
            return order[min(idx + 1, len(order) - 1)]
        except ValueError:
            return ConfidenceLevel.SPECULATIVE

    def compute_dominant_dimensions(self, profile: UserProfile) -> list[TraitDimension]:
        """Compute the most significant trait dimensions."""
        scores: dict[TraitDimension, float] = {}

        for dim, traits in profile.profiles.items():
            score = sum(
                t.stability_score * t.evidence_count
                for t in traits.values()
            )
            if traits:
                score /= len(traits)
            scores[dim] = score

        sorted_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [dim for dim, score in sorted_dims[:3] if score > 0.3]


# ---------------------------------------------------------------------------
# User Model Engine — Main Coordinator
# ---------------------------------------------------------------------------

class UserModelEngine:
    """Central engine for cross-session user understanding.

    Builds and maintains comprehensive user profiles by observing
    interactions across all agents and sessions, extracting behavioral
    signals, inferring traits, and evolving the user model over time.

    This enables every Buddy agent to understand the user deeply,
    providing personalized, context-aware interactions.
    """

    def __init__(self):
        self.extractor = SignalExtractor()
        self.inference = TraitInferenceEngine()
        self.evolution = ProfileEvolutionEngine()
        self._profiles: dict[str, UserProfile] = {}
        self._snapshots: dict[str, list[InteractionSnapshot]] = {}
        self._total_observations = 0
        self._total_inferences = 0

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create a new one."""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(
                user_id=user_id,
                profiles={dim: {} for dim in TraitDimension},
            )
        return self._profiles[user_id]

    def get_profile(self, user_id: str) -> UserProfile | None:
        """Get a user profile if it exists."""
        return self._profiles.get(user_id)

    # ------------------------------------------------------------------
    # Interaction Recording
    # ------------------------------------------------------------------

    def record_interaction(
        self,
        user_id: str,
        session_id: str,
        agent_id: str,
        text: str,
        context_type: str = "chat",
        emotional_valence: float = 0.0,
    ) -> InteractionSnapshot:
        """Record a user interaction and extract signals."""
        signals = self.extractor.extract(text, context_type)

        snapshot = InteractionSnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            agent_id=agent_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            context_type=context_type,
            raw_content=text,
            extracted_signals=signals,
            emotional_valence=emotional_valence,
        )

        if user_id not in self._snapshots:
            self._snapshots[user_id] = []
        self._snapshots[user_id].append(snapshot)
        self._total_observations += 1

        # Update profile
        profile = self.get_or_create_profile(user_id)
        profile.interaction_count += 1
        if profile.first_interaction is None:
            profile.first_interaction = snapshot.timestamp
        profile.last_interaction = snapshot.timestamp

        return snapshot

    # ------------------------------------------------------------------
    # Trait Inference
    # ------------------------------------------------------------------

    def infer_traits(self, user_id: str) -> dict[str, Any]:
        """Run trait inference on recent interactions."""
        profile = self.get_or_create_profile(user_id)
        snapshots = self._snapshots.get(user_id, [])

        if not snapshots:
            return {"new_traits": [], "updated_traits": [], "total_inferred": 0}

        all_new: list[dict] = []
        all_updated: list[dict] = []

        for snapshot in snapshots[-50:]:  # Process last 50 interactions
            new_traits, updated_traits = self.inference.infer_from_snapshot(
                snapshot, profile.profiles
            )

            for trait in new_traits:
                if trait.dimension not in profile.profiles:
                    profile.profiles[trait.dimension] = {}
                profile.profiles[trait.dimension][trait.key] = trait
                all_new.append(self._trait_to_dict(trait))

            for trait in updated_traits:
                all_updated.append(self._trait_to_dict(trait))

            self._total_inferences += len(new_traits) + len(updated_traits)

        profile.total_sessions = len(set(s.session_id for s in snapshots))
        profile.dominant_dimensions = self.evolution.compute_dominant_dimensions(profile)
        profile.profile_version += 1

        return {
            "new_traits": all_new,
            "updated_traits": all_updated,
            "total_inferred": len(all_new) + len(all_updated),
            "profile_version": profile.profile_version,
        }

    # ------------------------------------------------------------------
    # Profile Maintenance
    # ------------------------------------------------------------------

    def run_maintenance(self):
        """Run periodic profile maintenance tasks."""
        for profile in self._profiles.values():
            self.evolution.apply_temporal_decay(profile)

    def get_profile_summary(self, user_id: str) -> dict[str, Any]:
        """Get a human-readable profile summary."""
        profile = self.get_profile(user_id)
        if not profile:
            return {"user_id": user_id, "status": "no_profile"}

        summary = {
            "user_id": user_id,
            "interaction_count": profile.interaction_count,
            "total_sessions": profile.total_sessions,
            "first_interaction": profile.first_interaction,
            "last_interaction": profile.last_interaction,
            "dominant_dimensions": [d.value for d in profile.dominant_dimensions],
            "profile_version": profile.profile_version,
            "traits_by_dimension": {},
        }

        for dim, traits in profile.profiles.items():
            dim_summary = []
            for key, trait in sorted(traits.items(), key=lambda x: x[1].stability_score, reverse=True)[:10]:
                dim_summary.append({
                    "key": key,
                    "value": trait.value if isinstance(trait.value, (str, int, float, bool)) else str(trait.value)[:100],
                    "confidence": trait.confidence.value,
                    "evidence": trait.evidence_count,
                    "stability": round(trait.stability_score, 3),
                })
            if dim_summary:
                summary["traits_by_dimension"][dim.value] = dim_summary

        return summary

    def get_global_stats(self) -> dict[str, Any]:
        """Get global user model engine statistics."""
        total_profiles = len(self._profiles)
        total_traits = sum(
            sum(len(traits) for traits in p.profiles.values())
            for p in self._profiles.values()
        )

        return {
            "total_profiles": total_profiles,
            "total_observations": self._total_observations,
            "total_inferences": self._total_inferences,
            "total_traits": total_traits,
            "avg_traits_per_user": round(total_traits / max(total_profiles, 1), 1),
            "users_by_activity": {
                uid: p.interaction_count
                for uid, p in sorted(
                    self._profiles.items(),
                    key=lambda x: x[1].interaction_count,
                    reverse=True,
                )[:10]
            },
        }

    def _trait_to_dict(self, trait: UserTrait) -> dict[str, Any]:
        return {
            "trait_id": trait.trait_id,
            "dimension": trait.dimension.value,
            "key": trait.key,
            "value": trait.value if isinstance(trait.value, (str, int, float, bool)) else str(trait.value)[:100],
            "confidence": trait.confidence.value,
            "evidence_count": trait.evidence_count,
            "stability_score": round(trait.stability_score, 3),
            "last_observed": trait.last_observed,
        }


# Global instance
user_model_engine = UserModelEngine()