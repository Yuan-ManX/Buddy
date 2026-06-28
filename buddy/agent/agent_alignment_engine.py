"""Agent Alignment Engine — keeps agent behavior aligned with who the user is.

The Agent Alignment Engine maintains a living mapping between an AI agent's
behavior and a user's personal identity: values, communication style,
expertise, decision-making habits, risk tolerance, work style, goals, and
ethical boundaries. It continuously learns the user's identity from explicit
statements, observed behavior, and inferred signals, then evaluates every
proposed agent action against that identity before it is executed.

Core capabilities:
- Multi-dimensional alignment profiling across fourteen identity dimensions
- Trait confidence modeling with source-weighted evidence accumulation
- Signal capture and batch processing with weighted moving-average updates
- Pre-action alignment checks with graduated recommend / nudge / warn / block gating
- Calibration sessions that refine traits through explicit user feedback
- Drift detection that flags dimensions moving away from their baseline
- Conflict detection and resolution between explicit and inferred traits
- Alignment summaries exposing strong and weak areas for downstream agents

The engine is intentionally dependency-free so it can run in any Buddy
runtime without extra packages.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════


class AlignmentDimension(str, Enum):
    """Identity dimensions along which an agent can align to a user."""

    VALUES = "values"
    COMMUNICATION_STYLE = "communication_style"
    EXPERTISE_LEVEL = "expertise_level"
    DECISION_MAKING = "decision_making"
    RISK_TOLERANCE = "risk_tolerance"
    WORK_STYLE = "work_style"
    LEARNING_PREFERENCE = "learning_preference"
    FEEDBACK_STYLE = "feedback_style"
    PRIORITIES = "priorities"
    GOALS = "goals"
    BOUNDARIES = "boundaries"
    TONE = "tone"
    CULTURAL_CONTEXT = "cultural_context"
    ETHICAL_STANCE = "ethical_stance"


class AlignmentStrength(str, Enum):
    """Qualitative strength bands for an alignment score.

    Bounds are enforced in code, not by the enum value itself.
    """

    WEAK = "weak"            # 0.0 - 0.3
    MODERATE = "moderate"    # 0.3 - 0.6
    STRONG = "strong"        # 0.6 - 0.85
    EXCELLENT = "excellent"  # 0.85 - 1.0


class AlignmentSource(str, Enum):
    """How a trait value became known to the engine."""

    EXPLICIT = "explicit"        # user stated it directly
    INFERRED = "inferred"        # deduced from behavior
    OBSERVED = "observed"        # seen in interactions
    CALIBRATED = "calibrated"    # refined through feedback
    DEFAULT = "default"          # system default


class AlignmentChange(str, Enum):
    """Kind of change applied to a trait during an update."""

    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    SHIFTED = "shifted"
    CONFIRMED = "confirmed"
    ADDED = "added"
    REMOVED = "removed"
    CONFLICT_DETECTED = "conflict_detected"


class AlignmentAction(str, Enum):
    """Recommended action when a proposed action is checked for alignment."""

    ALIGNED = "aligned"
    NUDGE = "nudge"
    ADAPT = "adapt"
    WARN = "warn"
    BLOCK = "block"
    ESCALATE = "escalate"


class ConflictResolution(str, Enum):
    """Strategies for resolving a conflict on a trait."""

    PREFER_USER = "prefer_user"
    PREFER_SAFETY = "prefer_safety"
    PREFER_CONTEXT = "prefer_context"
    NEGOTIATE = "negotiate"
    DEFER = "defer"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════


@dataclass
class AlignmentTrait:
    """A single alignment dimension value for a user.

    Represents the engine's current belief about the user along one
    AlignmentDimension, together with how confident it is and where
    that belief came from.
    """

    trait_id: str
    dimension: AlignmentDimension
    value: str
    confidence: float = 0.0
    source: AlignmentSource = AlignmentSource.DEFAULT
    evidence_count: int = 0
    first_observed: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    is_locked: bool = False
    conflicts_with: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


@dataclass
class AlignmentProfile:
    """Full alignment profile for a user-agent pair."""

    profile_id: str
    user_id: str
    agent_id: str
    traits: dict[str, AlignmentTrait] = field(default_factory=dict)
    overall_alignment: float = 0.0
    last_calibrated: float = field(default_factory=time.time)
    total_interactions: int = 0
    explicit_traits: int = 0
    inferred_traits: int = 0
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AlignmentSignal:
    """An observed signal that informs alignment.

    Signals are raw observations queued for processing. Each signal
    targets one dimension and carries evidence plus a weight that
    influences how strongly it moves the corresponding trait.
    """

    signal_id: str
    profile_id: str
    dimension: AlignmentDimension
    observed_value: str
    evidence: str
    source: AlignmentSource
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)
    processed: bool = False


@dataclass
class AlignmentCheck:
    """Result of checking a proposed action against alignment."""

    check_id: str
    profile_id: str
    dimension: AlignmentDimension | None
    proposed_action: str
    action_description: str
    alignment_score: float
    recommended_action: AlignmentAction
    reasoning: str
    conflicts: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)


@dataclass
class AlignmentDriftReport:
    """Report on alignment drift over a period of time."""

    report_id: str
    profile_id: str
    period_start: float
    period_end: float
    dimensions_checked: int
    dimensions_drifted: int
    avg_drift: float
    max_drift: float
    drifted_dimensions: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)


@dataclass
class CalibrationSession:
    """A feedback session used to calibrate alignment traits."""

    session_id: str
    profile_id: str
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    questions_asked: int = 0
    answers_received: int = 0
    traits_updated: list[str] = field(default_factory=list)
    traits_added: list[str] = field(default_factory=list)
    traits_confirmed: list[str] = field(default_factory=list)
    notes: str = ""


# ═══════════════════════════════════════════════════════════
# Agent Alignment Engine
# ═══════════════════════════════════════════════════════════


class AgentAlignmentEngine:
    """Maintains alignment between agent behavior and user identity.

    The engine stores one AlignmentProfile per user-agent pair. Profiles
    accumulate AlignmentTraits that are set explicitly, observed, or
    inferred from queued AlignmentSignals. Before an agent performs an
    action, :meth:`check_alignment` scores the action against the relevant
    traits and returns a recommended AlignmentAction ranging from ALIGNED
    to BLOCK. Drift detection and calibration sessions keep the profile
    current as the user evolves.
    """

    # Capacity guards
    MAX_PROFILES = 10000
    MAX_SIGNALS_PER_PROFILE = 50000
    MAX_TRAITS_PER_PROFILE = 200

    # Decision thresholds
    MIN_CONFIDENCE_FOR_ACTION = 0.5
    DRIFT_THRESHOLD = 0.25
    CALIBRATION_INTERVAL = 86400  # 1 day in seconds

    # Base confidence contributed by each source before evidence boosting.
    _SOURCE_BASE_CONFIDENCE: dict[AlignmentSource, float] = {
        AlignmentSource.EXPLICIT: 0.8,
        AlignmentSource.CALIBRATED: 0.75,
        AlignmentSource.OBSERVED: 0.6,
        AlignmentSource.INFERRED: 0.5,
        AlignmentSource.DEFAULT: 0.3,
    }

    def __init__(self) -> None:
        """Initialize an empty alignment engine."""
        self._profiles: dict[str, AlignmentProfile] = {}
        self._signals: dict[str, list[AlignmentSignal]] = {}
        self._checks: dict[str, AlignmentCheck] = {}
        self._drift_reports: dict[str, AlignmentDriftReport] = {}
        self._calibrations: dict[str, CalibrationSession] = {}
        self._changes: list[dict[str, Any]] = []

    # ── Internal helpers ────────────────────────────────────────

    @staticmethod
    def _new_id() -> str:
        """Generate a short unique id for engine entities."""
        return uuid.uuid4().hex[:12]

    def _compute_confidence(
        self,
        source: AlignmentSource,
        evidence_count: int,
        provided: float | None,
    ) -> float:
        """Compute trait confidence from source, evidence, and optional override.

        When ``provided`` is given it is clamped to [0.0, 1.0] and used
        directly. Otherwise the base confidence for the source is boosted
        by evidence count with diminishing returns.
        """
        if provided is not None:
            return max(0.0, min(1.0, float(provided)))
        base = self._SOURCE_BASE_CONFIDENCE.get(source, 0.3)
        boost = 0.2 * (1.0 - math.exp(-max(0, evidence_count) / 5.0))
        return max(0.0, min(1.0, base + boost))

    @staticmethod
    def _categorize_strength(score: float) -> AlignmentStrength:
        """Map a numeric alignment score to a qualitative strength band."""
        if score < 0.3:
            return AlignmentStrength.WEAK
        if score < 0.6:
            return AlignmentStrength.MODERATE
        if score < 0.85:
            return AlignmentStrength.STRONG
        return AlignmentStrength.EXCELLENT

    def _recompute_profile_counts(self, profile: AlignmentProfile) -> None:
        """Recount explicit and inferred traits on a profile."""
        explicit = 0
        inferred = 0
        for trait in profile.traits.values():
            if trait.source == AlignmentSource.EXPLICIT:
                explicit += 1
            elif trait.source == AlignmentSource.INFERRED:
                inferred += 1
        profile.explicit_traits = explicit
        profile.inferred_traits = inferred

    # ── Profile management ──────────────────────────────────────

    def create_profile(self, user_id: str, agent_id: str) -> AlignmentProfile:
        """Create a new empty alignment profile for a user-agent pair.

        Args:
            user_id: The user the profile describes.
            agent_id: The agent the profile aligns to.

        Returns:
            The newly created AlignmentProfile.

        Raises:
            ValueError: If a profile already exists for this user+agent
                pair, or if the engine has reached MAX_PROFILES.
        """
        if self.get_profile_by_user_agent(user_id, agent_id) is not None:
            raise ValueError(
                f"Alignment profile already exists for user={user_id} agent={agent_id}"
            )
        if len(self._profiles) >= self.MAX_PROFILES:
            raise ValueError("Maximum number of alignment profiles reached")

        profile = AlignmentProfile(
            profile_id=self._new_id(),
            user_id=user_id,
            agent_id=agent_id,
        )
        self._profiles[profile.profile_id] = profile
        return profile

    def get_profile(self, profile_id: str) -> AlignmentProfile | None:
        """Return a profile by id, or None if it does not exist."""
        return self._profiles.get(profile_id)

    def get_profile_by_user_agent(
        self, user_id: str, agent_id: str
    ) -> AlignmentProfile | None:
        """Return the profile for a given user-agent pair, if any."""
        for profile in self._profiles.values():
            if profile.user_id == user_id and profile.agent_id == agent_id:
                return profile
        return None

    def list_profiles(
        self, user_id: str | None = None, agent_id: str | None = None
    ) -> list[AlignmentProfile]:
        """List profiles, optionally filtered by user and/or agent."""
        results: list[AlignmentProfile] = []
        for profile in self._profiles.values():
            if user_id is not None and profile.user_id != user_id:
                continue
            if agent_id is not None and profile.agent_id != agent_id:
                continue
            results.append(profile)
        return results

    # ── Trait management ────────────────────────────────────────

    def set_trait(
        self,
        profile_id: str,
        dimension: AlignmentDimension,
        value: str,
        source: AlignmentSource = AlignmentSource.EXPLICIT,
        evidence: str = "",
        confidence: float | None = None,
        lock: bool = False,
    ) -> AlignmentTrait | None:
        """Set or update a trait on a profile.

        If a trait already exists for the dimension and is locked, the
        update is refused and None is returned. When a trait is new it
        is added; when it already exists its change type is detected
        (CONFIRMED if unchanged, SHIFTED if the value changed). Confidence
        is auto-computed from the source and evidence count unless an
        explicit value is supplied. The profile's overall alignment is
        refreshed afterwards.

        Args:
            profile_id: Target profile.
            dimension: Dimension to set.
            value: Trait value.
            source: Where the value came from.
            evidence: Optional evidence string recorded on the trait.
            confidence: Optional explicit confidence override.
            lock: Whether to lock the trait after setting it.

        Returns:
            The resulting AlignmentTrait, or None if the trait was
            locked and refused.

        Raises:
            ValueError: If the profile does not exist or the trait
                count limit would be exceeded.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"Alignment profile not found: {profile_id}")

        existing = profile.traits.get(dimension.value)
        if existing is not None and existing.is_locked:
            return None

        if existing is None and len(profile.traits) >= self.MAX_TRAITS_PER_PROFILE:
            raise ValueError(
                f"Maximum traits per profile ({self.MAX_TRAITS_PER_PROFILE}) reached"
            )

        now = time.time()
        if existing is not None:
            evidence_count = existing.evidence_count + 1
            if existing.value == value:
                change_type = AlignmentChange.CONFIRMED
            else:
                change_type = AlignmentChange.SHIFTED
            trait_id = existing.trait_id
            first_observed = existing.first_observed
            conflicts_with = list(existing.conflicts_with)
            examples = list(existing.examples)
        else:
            evidence_count = 1
            change_type = AlignmentChange.ADDED
            trait_id = self._new_id()
            first_observed = now
            conflicts_with = []
            examples = []

        if evidence and evidence not in examples:
            examples.append(evidence)

        computed_confidence = self._compute_confidence(
            source, evidence_count, confidence
        )

        trait = AlignmentTrait(
            trait_id=trait_id,
            dimension=dimension,
            value=value,
            confidence=computed_confidence,
            source=source,
            evidence_count=evidence_count,
            first_observed=first_observed,
            last_updated=now,
            is_locked=lock,
            conflicts_with=conflicts_with,
            examples=examples,
        )
        profile.traits[dimension.value] = trait

        self._recompute_profile_counts(profile)
        profile.overall_alignment = self.compute_overall_alignment(profile_id)
        profile.updated_at = now

        self._changes.append(
            {
                "profile_id": profile_id,
                "dimension": dimension.value,
                "change_type": change_type.value,
                "value": value,
                "timestamp": now,
            }
        )
        return trait

    def get_trait(
        self, profile_id: str, dimension: AlignmentDimension
    ) -> AlignmentTrait | None:
        """Return a trait for a dimension, or None if missing."""
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        return profile.traits.get(dimension.value)

    def remove_trait(
        self, profile_id: str, dimension: AlignmentDimension
    ) -> bool:
        """Remove a trait from a profile.

        Locked traits cannot be removed.

        Returns:
            True if the trait was removed, False if it was missing or
            locked.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return False
        trait = profile.traits.get(dimension.value)
        if trait is None:
            return False
        if trait.is_locked:
            return False
        del profile.traits[dimension.value]
        self._recompute_profile_counts(profile)
        profile.overall_alignment = self.compute_overall_alignment(profile_id)
        profile.updated_at = time.time()
        self._changes.append(
            {
                "profile_id": profile_id,
                "dimension": dimension.value,
                "change_type": AlignmentChange.REMOVED.value,
                "value": trait.value,
                "timestamp": profile.updated_at,
            }
        )
        return True

    def lock_trait(
        self, profile_id: str, dimension: AlignmentDimension
    ) -> AlignmentTrait | None:
        """Lock a trait so it cannot be modified or removed."""
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        trait = profile.traits.get(dimension.value)
        if trait is None:
            return None
        trait.is_locked = True
        trait.last_updated = time.time()
        return trait

    def unlock_trait(
        self, profile_id: str, dimension: AlignmentDimension
    ) -> AlignmentTrait | None:
        """Unlock a previously locked trait."""
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        trait = profile.traits.get(dimension.value)
        if trait is None:
            return None
        trait.is_locked = False
        trait.last_updated = time.time()
        return trait

    # ── Signal capture and processing ───────────────────────────

    def record_signal(
        self,
        profile_id: str,
        dimension: AlignmentDimension,
        observed_value: str,
        evidence: str,
        source: AlignmentSource = AlignmentSource.OBSERVED,
        weight: float = 1.0,
    ) -> AlignmentSignal | None:
        """Record a signal for later processing.

        Signals are queued per profile and consumed by
        :meth:`process_signals`. Returns None if the profile does not
        exist or the signal queue is full.
        """
        if profile_id not in self._profiles:
            return None
        signals = self._signals.setdefault(profile_id, [])
        if len(signals) >= self.MAX_SIGNALS_PER_PROFILE:
            return None
        signal = AlignmentSignal(
            signal_id=self._new_id(),
            profile_id=profile_id,
            dimension=dimension,
            observed_value=observed_value,
            evidence=evidence,
            source=source,
            weight=weight,
        )
        signals.append(signal)
        return signal

    def process_signals(
        self, profile_id: str, max_signals: int = 100
    ) -> dict[str, Any]:
        """Process pending signals for a profile.

        Each pending signal either strengthens an existing trait or
        creates a new one. Confidence is updated with a weighted moving
        average that blends the trait's current confidence (weighted by
        its evidence count) with the signal's contribution (weighted by
        the signal weight). When an observed/inferred signal contradicts
        an explicit trait, a conflict is recorded instead of overwriting
        the explicit value.

        Returns:
            A dict with processed_count, traits_updated, traits_added,
            and conflicts_detected.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return {
                "processed_count": 0,
                "traits_updated": 0,
                "traits_added": 0,
                "conflicts_detected": 0,
            }

        signals = self._signals.get(profile_id, [])
        pending = [s for s in signals if not s.processed][:max_signals]

        processed_count = 0
        traits_updated = 0
        traits_added = 0
        conflicts_detected = 0
        now = time.time()

        for signal in pending:
            signal.processed = True
            processed_count += 1

            existing = profile.traits.get(signal.dimension.value)
            if existing is None:
                if len(profile.traits) >= self.MAX_TRAITS_PER_PROFILE:
                    continue
                confidence = self._compute_confidence(signal.source, 1, None)
                trait = AlignmentTrait(
                    trait_id=self._new_id(),
                    dimension=signal.dimension,
                    value=signal.observed_value,
                    confidence=confidence,
                    source=signal.source,
                    evidence_count=1,
                    first_observed=signal.timestamp,
                    last_updated=now,
                    is_locked=False,
                    conflicts_with=[],
                    examples=[signal.evidence] if signal.evidence else [],
                )
                profile.traits[signal.dimension.value] = trait
                traits_added += 1
                continue

            # Existing trait: detect conflicts before mutating.
            if existing.value != signal.observed_value:
                if (
                    existing.source == AlignmentSource.EXPLICIT
                    and signal.source != AlignmentSource.EXPLICIT
                ):
                    if signal.observed_value not in existing.conflicts_with:
                        existing.conflicts_with.append(signal.observed_value)
                        conflicts_detected += 1
                    self._changes.append(
                        {
                            "profile_id": profile_id,
                            "dimension": signal.dimension.value,
                            "change_type": AlignmentChange.CONFLICT_DETECTED.value,
                            "value": signal.observed_value,
                            "timestamp": now,
                        }
                    )
                    continue
                # Otherwise treat as a shift toward the new value.
                existing.value = signal.observed_value

            old_weight = max(1.0, float(existing.evidence_count))
            new_weight = max(0.0, float(signal.weight))
            signal_confidence = self._compute_confidence(signal.source, 1, None)
            blended = (
                existing.confidence * old_weight
                + signal_confidence * new_weight
            ) / (old_weight + new_weight)
            existing.confidence = max(0.0, min(1.0, blended))
            existing.evidence_count += 1
            existing.last_updated = now
            if signal.evidence and signal.evidence not in existing.examples:
                existing.examples.append(signal.evidence)
            traits_updated += 1

        self._recompute_profile_counts(profile)
        profile.overall_alignment = self.compute_overall_alignment(profile_id)
        profile.total_interactions += processed_count
        profile.updated_at = now

        return {
            "processed_count": processed_count,
            "traits_updated": traits_updated,
            "traits_added": traits_added,
            "conflicts_detected": conflicts_detected,
        }

    # ── Alignment checking ──────────────────────────────────────

    def check_alignment(
        self,
        profile_id: str,
        proposed_action: str,
        action_description: str = "",
        dimension: AlignmentDimension | None = None,
    ) -> AlignmentCheck | None:
        """Check whether a proposed action aligns with the user's profile.

        The action is scored from 0.0 to 1.0 based on the confidence of
        relevant traits. When ``dimension`` is supplied only that trait
        is considered; otherwise the engine matches trait values and
        examples against the action text, falling back to all traits.
        Traits with conflicts lower the score. The score maps to a
        recommended action:

        - >= 0.85  -> ALIGNED
        - >= 0.60  -> NUDGE
        - >= 0.40  -> ADAPT
        - >= 0.20  -> WARN
        - <  0.20  -> BLOCK

        Returns:
            The stored AlignmentCheck, or None if the profile is missing.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None

        relevant: list[AlignmentTrait] = []
        conflicts: list[str] = []

        if dimension is not None:
            trait = profile.traits.get(dimension.value)
            if trait is not None:
                relevant.append(trait)
        else:
            action_text = (proposed_action + " " + action_description).lower()
            for trait in profile.traits.values():
                if trait.value and trait.value.lower() in action_text:
                    relevant.append(trait)
                elif any(
                    ex.lower() in action_text for ex in trait.examples if ex
                ):
                    relevant.append(trait)
            if not relevant:
                relevant = list(profile.traits.values())

        if not relevant:
            score = 0.5
        else:
            score = sum(t.confidence for t in relevant) / len(relevant)
            for trait in relevant:
                if trait.conflicts_with:
                    conflicts.extend(trait.conflicts_with)
            conflict_penalty = 0.1 * sum(
                1 for t in relevant if t.conflicts_with
            )
            score = max(0.0, score - conflict_penalty)

        if score >= 0.85:
            recommended = AlignmentAction.ALIGNED
        elif score >= 0.6:
            recommended = AlignmentAction.NUDGE
        elif score >= 0.4:
            recommended = AlignmentAction.ADAPT
        elif score >= 0.2:
            recommended = AlignmentAction.WARN
        else:
            recommended = AlignmentAction.BLOCK

        reasoning = self._build_check_reasoning(
            recommended, score, relevant, dimension
        )
        suggestions = self._build_check_suggestions(
            recommended, relevant, conflicts
        )

        check = AlignmentCheck(
            check_id=self._new_id(),
            profile_id=profile_id,
            dimension=dimension,
            proposed_action=proposed_action,
            action_description=action_description,
            alignment_score=round(score, 4),
            recommended_action=recommended,
            reasoning=reasoning,
            conflicts=conflicts,
            suggestions=suggestions,
        )
        self._checks[check.check_id] = check
        return check

    def _build_check_reasoning(
        self,
        recommended: AlignmentAction,
        score: float,
        relevant: list[AlignmentTrait],
        dimension: AlignmentDimension | None,
    ) -> str:
        """Compose a human-readable reasoning string for a check."""
        dim_label = dimension.value if dimension is not None else "all dimensions"
        trait_count = len(relevant)
        return (
            f"Alignment score {score:.3f} across {dim_label} "
            f"({trait_count} trait(s) considered); "
            f"recommended action: {recommended.value}."
        )

    @staticmethod
    def _build_check_suggestions(
        recommended: AlignmentAction,
        relevant: list[AlignmentTrait],
        conflicts: list[str],
    ) -> list[str]:
        """Compose actionable suggestions for a check."""
        suggestions: list[str] = []
        if recommended == AlignmentAction.BLOCK:
            suggestions.append("Do not execute; the action conflicts with the user's alignment.")
        elif recommended == AlignmentAction.WARN:
            suggestions.append("Proceed only with explicit user confirmation.")
        elif recommended == AlignmentAction.ADAPT:
            suggestions.append("Adapt the action to better fit the user's profile before executing.")
        elif recommended == AlignmentAction.NUDGE:
            suggestions.append("Proceed, but nudge the action toward the user's preferences.")
        if conflicts:
            suggestions.append(
                f"Resolve conflicting values: {', '.join(conflicts[:3])}"
            )
        for trait in relevant:
            if trait.confidence < 0.5:
                suggestions.append(
                    f"Calibrate dimension '{trait.dimension.value}' to raise confidence."
                )
        return suggestions

    def get_check(self, check_id: str) -> AlignmentCheck | None:
        """Return a stored alignment check by id."""
        return self._checks.get(check_id)

    def list_checks(
        self, profile_id: str | None = None, limit: int = 100
    ) -> list[AlignmentCheck]:
        """List alignment checks, optionally filtered by profile."""
        results: list[AlignmentCheck] = []
        for check in self._checks.values():
            if profile_id is not None and check.profile_id != profile_id:
                continue
            results.append(check)
        results.sort(key=lambda c: c.checked_at, reverse=True)
        return results[:limit]

    # ── Calibration ─────────────────────────────────────────────

    def calibrate(
        self,
        profile_id: str,
        dimension_updates: dict[AlignmentDimension, str] | None = None,
    ) -> CalibrationSession:
        """Run a calibration session that refines traits via explicit feedback.

        Each entry in ``dimension_updates`` is applied as a CALIBRATED
        trait update. New traits are added; existing traits have their
        value replaced, source set to CALIBRATED, and confidence
        incremented. The session records what was changed.

        Args:
            profile_id: Target profile.
            dimension_updates: Mapping of dimension to new value.

        Returns:
            The completed CalibrationSession.

        Raises:
            ValueError: If the profile does not exist.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"Alignment profile not found: {profile_id}")

        session = CalibrationSession(
            session_id=self._new_id(),
            profile_id=profile_id,
        )

        if dimension_updates:
            session.questions_asked = len(dimension_updates)
            now = time.time()
            for dimension, value in dimension_updates.items():
                existing = profile.traits.get(dimension.value)
                if existing is None:
                    if len(profile.traits) >= self.MAX_TRAITS_PER_PROFILE:
                        continue
                    trait = AlignmentTrait(
                        trait_id=AgentAlignmentEngine._new_id(),
                        dimension=dimension,
                        value=value,
                        confidence=AgentAlignmentEngine._compute_confidence(
                            AlignmentSource.CALIBRATED, 1, None
                        ),
                        source=AlignmentSource.CALIBRATED,
                        evidence_count=1,
                        first_observed=now,
                        last_updated=now,
                        examples=["calibration"],
                    )
                    profile.traits[dimension.value] = trait
                    session.traits_added.append(dimension.value)
                else:
                    existing.value = value
                    existing.source = AlignmentSource.CALIBRATED
                    existing.evidence_count += 1
                    existing.confidence = max(
                        0.0, min(1.0, existing.confidence + 0.1)
                    )
                    existing.last_updated = now
                    if "calibration" not in existing.examples:
                        existing.examples.append("calibration")
                    session.traits_updated.append(dimension.value)
                    session.traits_confirmed.append(dimension.value)
                session.answers_received += 1

        now = time.time()
        profile.last_calibrated = now
        self._recompute_profile_counts(profile)
        profile.overall_alignment = self.compute_overall_alignment(profile_id)
        profile.updated_at = now

        session.completed_at = now
        session.notes = f"Calibrated {session.answers_received} trait(s)."
        self._calibrations[session.session_id] = session
        return session

    # ── Drift detection ─────────────────────────────────────────

    def detect_drift(
        self, profile_id: str, period_seconds: int = 604800
    ) -> AlignmentDriftReport | None:
        """Detect how much traits have drifted over a period.

        Examines each trait's last_updated time within the period and
        estimates drift from how stale and how uncertain the trait is.
        Traits whose estimated drift meets DRIFT_THRESHOLD are reported.

        Args:
            profile_id: Target profile.
            period_seconds: Lookback window in seconds (default 7 days).

        Returns:
            An AlignmentDriftReport, or None if the profile is missing.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None

        now = time.time()
        period_start = now - period_seconds
        drifted: list[dict[str, Any]] = []

        for trait in profile.traits.values():
            if trait.last_updated < period_start:
                continue
            age_ratio = min(1.0, (now - trait.last_updated) / max(1.0, period_seconds))
            drift = age_ratio * (1.0 - trait.confidence)
            if drift >= self.DRIFT_THRESHOLD:
                drifted.append(
                    {
                        "dimension": trait.dimension.value,
                        "trait_id": trait.trait_id,
                        "value": trait.value,
                        "drift": round(drift, 4),
                        "current_confidence": trait.confidence,
                        "last_updated": trait.last_updated,
                    }
                )

        dimensions_checked = len(profile.traits)
        dimensions_drifted = len(drifted)
        avg_drift = (
            sum(d["drift"] for d in drifted) / len(drifted) if drifted else 0.0
        )
        max_drift = max((d["drift"] for d in drifted), default=0.0)

        report = AlignmentDriftReport(
            report_id=self._new_id(),
            profile_id=profile_id,
            period_start=period_start,
            period_end=now,
            dimensions_checked=dimensions_checked,
            dimensions_drifted=dimensions_drifted,
            avg_drift=round(avg_drift, 4),
            max_drift=round(max_drift, 4),
            drifted_dimensions=drifted,
        )
        self._drift_reports[report.report_id] = report
        return report

    # ── Conflict resolution ─────────────────────────────────────

    def resolve_conflict(
        self,
        profile_id: str,
        dimension: AlignmentDimension,
        resolution: ConflictResolution = ConflictResolution.PREFER_USER,
        resolution_value: str | None = None,
    ) -> AlignmentTrait | None:
        """Resolve a conflict recorded on a trait.

        Depending on the strategy, the trait value may be replaced, its
        confidence adjusted, and its conflict list cleared. DEFER leaves
        the trait untouched.

        Returns:
            The updated trait, or None if the profile or trait is missing.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        trait = profile.traits.get(dimension.value)
        if trait is None:
            return None

        now = time.time()
        if resolution == ConflictResolution.PREFER_USER:
            if resolution_value is not None:
                trait.value = resolution_value
            trait.conflicts_with = []
            trait.confidence = max(0.0, min(1.0, trait.confidence + 0.1))
        elif resolution == ConflictResolution.PREFER_SAFETY:
            trait.confidence = max(0.0, trait.confidence - 0.2)
            trait.conflicts_with = []
        elif resolution == ConflictResolution.PREFER_CONTEXT:
            if resolution_value is not None:
                trait.value = resolution_value
            trait.conflicts_with = []
        elif resolution == ConflictResolution.NEGOTIATE:
            trait.confidence = max(0.0, min(1.0, trait.confidence + 0.05))
            trait.conflicts_with = []
        elif resolution == ConflictResolution.DEFER:
            pass

        trait.last_updated = now
        profile.overall_alignment = self.compute_overall_alignment(profile_id)
        profile.updated_at = now
        return trait

    # ── Aggregation and stats ───────────────────────────────────

    def compute_overall_alignment(self, profile_id: str) -> float:
        """Compute a weighted average of trait confidences.

        Each trait is weighted by its evidence count (minimum weight 1)
        so traits with more supporting evidence contribute more.
        """
        profile = self._profiles.get(profile_id)
        if profile is None or not profile.traits:
            return 0.0
        total_weight = 0.0
        weighted_sum = 0.0
        for trait in profile.traits.values():
            weight = max(1.0, float(trait.evidence_count))
            weighted_sum += trait.confidence * weight
            total_weight += weight
        if total_weight <= 0.0:
            return 0.0
        return max(0.0, min(1.0, weighted_sum / total_weight))

    def get_alignment_summary(self, profile_id: str) -> dict[str, Any]:
        """Return a summary of a profile's alignment state.

        Includes the overall score and strength, a per-dimension
        breakdown, the top traits by confidence, and weak areas below
        the action confidence threshold.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return {}

        dimension_breakdown: dict[str, Any] = {}
        for trait in profile.traits.values():
            dimension_breakdown[trait.dimension.value] = {
                "value": trait.value,
                "confidence": trait.confidence,
                "source": trait.source.value,
                "strength": self._categorize_strength(trait.confidence).value,
                "evidence_count": trait.evidence_count,
                "locked": trait.is_locked,
            }

        sorted_traits = sorted(
            profile.traits.values(), key=lambda t: t.confidence, reverse=True
        )
        top_traits = [
            {
                "dimension": t.dimension.value,
                "value": t.value,
                "confidence": t.confidence,
            }
            for t in sorted_traits[:5]
        ]
        weak_areas = [
            {
                "dimension": t.dimension.value,
                "value": t.value,
                "confidence": t.confidence,
            }
            for t in sorted_traits
            if t.confidence < self.MIN_CONFIDENCE_FOR_ACTION
        ][:3]

        return {
            "profile_id": profile_id,
            "overall_alignment": profile.overall_alignment,
            "overall_strength": self._categorize_strength(
                profile.overall_alignment
            ).value,
            "total_traits": len(profile.traits),
            "explicit_traits": profile.explicit_traits,
            "inferred_traits": profile.inferred_traits,
            "total_interactions": profile.total_interactions,
            "last_calibrated": profile.last_calibrated,
            "dimension_breakdown": dimension_breakdown,
            "top_traits": top_traits,
            "weak_areas": weak_areas,
        }

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across the whole engine."""
        total_profiles = len(self._profiles)
        total_traits = sum(len(p.traits) for p in self._profiles.values())
        total_signals = sum(len(sigs) for sigs in self._signals.values())
        total_checks = len(self._checks)

        if total_profiles > 0:
            avg_alignment = (
                sum(p.overall_alignment for p in self._profiles.values())
                / total_profiles
            )
        else:
            avg_alignment = 0.0

        dimension_distribution: dict[str, int] = {}
        source_distribution: dict[str, int] = {}
        for profile in self._profiles.values():
            for trait in profile.traits.values():
                dim = trait.dimension.value
                dimension_distribution[dim] = (
                    dimension_distribution.get(dim, 0) + 1
                )
                src = trait.source.value
                source_distribution[src] = source_distribution.get(src, 0) + 1

        return {
            "total_profiles": total_profiles,
            "total_traits": total_traits,
            "total_signals": total_signals,
            "total_checks": total_checks,
            "total_drift_reports": len(self._drift_reports),
            "total_calibrations": len(self._calibrations),
            "avg_alignment": round(avg_alignment, 4),
            "dimension_distribution": dimension_distribution,
            "source_distribution": source_distribution,
        }

    def reset(self) -> None:
        """Clear all profiles, signals, checks, reports, and sessions."""
        self._profiles.clear()
        self._signals.clear()
        self._checks.clear()
        self._drift_reports.clear()
        self._calibrations.clear()
        self._changes.clear()


# ═══════════════════════════════════════════════════════════
# Singleton accessors
# ═══════════════════════════════════════════════════════════


_alignment_engine: AgentAlignmentEngine | None = None


def get_alignment_engine() -> AgentAlignmentEngine:
    """Get or create the singleton alignment engine."""
    global _alignment_engine
    if _alignment_engine is None:
        _alignment_engine = AgentAlignmentEngine()
    return _alignment_engine


def reset_alignment_engine() -> None:
    """Reset the singleton alignment engine."""
    global _alignment_engine
    if _alignment_engine is not None:
        _alignment_engine.reset()
    _alignment_engine = None
