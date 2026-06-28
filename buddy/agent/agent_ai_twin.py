"""Platform AI Twin — personal digital identity with continuous mirroring and learning.

Creates a persistent digital twin that mirrors a user's preferences, knowledge,
behavioral patterns, and decision-making style. The twin continuously learns
from interactions and evolves to become a more accurate representation over time.
"""

from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MirrorDimension(Enum):
    """Dimensions of the digital twin mirroring."""
    PREFERENCES = "preferences"
    KNOWLEDGE = "knowledge"
    BEHAVIOR = "behavior"
    DECISION_STYLE = "decision_style"
    COMMUNICATION = "communication"
    VALUES = "values"
    GOALS = "goals"
    ROUTINES = "routines"


class SyncFrequency(Enum):
    """How often the twin syncs with the user."""
    CONTINUOUS = "continuous"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"


class MirrorAccuracy(Enum):
    """Accuracy level of the mirror in a dimension."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class MirrorSnapshot:
    """A snapshot of a mirror dimension at a point in time."""
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dimension: MirrorDimension = MirrorDimension.PREFERENCES
    data: dict[str, Any] = field(default_factory=dict)
    accuracy: MirrorAccuracy = MirrorAccuracy.MEDIUM
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class LearningSignal:
    """A signal captured from user interaction for twin learning."""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dimension: MirrorDimension = MirrorDimension.PREFERENCES
    action: str = ""
    context: str = ""
    outcome: str = ""
    weight: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class TwinProfile:
    """The complete digital twin profile."""
    twin_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    mirrors: dict[str, MirrorSnapshot] = field(default_factory=dict)
    learning_history: list[LearningSignal] = field(default_factory=list)
    sync_frequency: SyncFrequency = SyncFrequency.CONTINUOUS
    total_interactions: int = 0
    created_at: float = field(default_factory=time.time)
    last_synced: float = field(default_factory=time.time)


class PlatformAITwin:
    """Personal AI digital twin with continuous identity mirroring.

    Builds and maintains a persistent digital representation of a user across
    multiple dimensions: preferences, knowledge, behavioral patterns, decision
    style, communication patterns, values, goals, and routines.

    The twin continuously learns from interaction signals, updating its mirror
    snapshots to improve accuracy. It can predict user preferences, simulate
    decision-making, and act as a proxy for the user in automated scenarios.
    """

    MAX_SIGNALS_PER_DIMENSION: int = 1000
    CONFIDENCE_DECAY: float = 0.95
    LEARNING_RATE: float = 0.1

    def __init__(self) -> None:
        self._profiles: dict[str, TwinProfile] = {}
        self._total_profiles: int = 0
        self._total_signals: int = 0

    def create_profile(
        self,
        name: str = "",
        sync_frequency: SyncFrequency = SyncFrequency.CONTINUOUS,
    ) -> TwinProfile:
        """Create a new digital twin profile.

        Args:
            name: Name for the twin.
            sync_frequency: How often to sync.

        Returns:
            A new TwinProfile with initialized mirrors.
        """
        profile = TwinProfile(
            name=name,
            sync_frequency=sync_frequency,
        )
        # Initialize all mirror dimensions
        for dim in MirrorDimension:
            profile.mirrors[dim.value] = MirrorSnapshot(
                dimension=dim,
                accuracy=MirrorAccuracy.LOW,
            )
        self._profiles[profile.twin_id] = profile
        self._total_profiles += 1
        return profile

    def learn(
        self,
        twin_id: str,
        dimension: MirrorDimension,
        action: str,
        context: str = "",
        outcome: str = "",
        weight: float = 0.5,
    ) -> LearningSignal | None:
        """Record a learning signal from user interaction.

        Args:
            twin_id: The twin to update.
            dimension: The dimension being learned.
            action: What the user did.
            context: Context of the action.
            outcome: Result of the action.
            weight: Importance of this signal.

        Returns:
            The recorded LearningSignal, or None if profile not found.
        """
        profile = self._profiles.get(twin_id)
        if not profile:
            return None

        signal = LearningSignal(
            dimension=dimension,
            action=action,
            context=context,
            outcome=outcome,
            weight=weight,
        )
        profile.learning_history.append(signal)
        profile.total_interactions += 1
        self._total_signals += 1

        # Trim history if too large
        dim_signals = [
            s for s in profile.learning_history if s.dimension == dimension
        ]
        if len(dim_signals) > self.MAX_SIGNALS_PER_DIMENSION:
            profile.learning_history = [
                s for s in profile.learning_history
                if not (s.dimension == dimension and s in dim_signals[:len(dim_signals) - self.MAX_SIGNALS_PER_DIMENSION])
            ]

        # Update the mirror
        self._update_mirror(profile, dimension)

        return signal

    def _update_mirror(
        self, profile: TwinProfile, dimension: MirrorDimension
    ) -> None:
        """Update a mirror dimension based on learning signals."""
        mirror = profile.mirrors.get(dimension.value)
        if not mirror:
            return

        dim_signals = [
            s for s in profile.learning_history if s.dimension == dimension
        ]

        if not dim_signals:
            return

        # Aggregate signals into mirror data
        action_counts: dict[str, int] = {}
        outcome_counts: dict[str, int] = {}
        context_counts: dict[str, int] = {}

        for sig in dim_signals:
            action_counts[sig.action] = action_counts.get(sig.action, 0) + 1
            if sig.outcome:
                outcome_counts[sig.outcome] = outcome_counts.get(sig.outcome, 0) + 1
            if sig.context:
                context_counts[sig.context] = context_counts.get(sig.context, 0) + 1

        total = len(dim_signals)
        mirror.data = {
            "total_signals": total,
            "top_actions": sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_outcomes": sorted(outcome_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_contexts": sorted(context_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "last_signal": dim_signals[-1].action if dim_signals else "",
        }

        # Update accuracy based on signal volume
        if total < 5:
            mirror.accuracy = MirrorAccuracy.LOW
        elif total < 20:
            mirror.accuracy = MirrorAccuracy.MEDIUM
        elif total < 50:
            mirror.accuracy = MirrorAccuracy.HIGH
        else:
            mirror.accuracy = MirrorAccuracy.VERY_HIGH

        mirror.confidence = min(1.0, total * self.LEARNING_RATE)
        mirror.timestamp = time.time()
        profile.last_synced = time.time()

    def predict(
        self,
        twin_id: str,
        dimension: MirrorDimension,
        context: str = "",
    ) -> dict[str, Any] | None:
        """Predict user behavior or preference based on the twin.

        Args:
            twin_id: The twin to predict from.
            dimension: The dimension to predict in.
            context: Context for the prediction.

        Returns:
            Prediction dict with actions and confidence.
        """
        profile = self._profiles.get(twin_id)
        if not profile:
            return None

        mirror = profile.mirrors.get(dimension.value)
        if not mirror:
            return None

        dim_signals = [
            s for s in profile.learning_history
            if s.dimension == dimension
            and (not context or context.lower() in s.context.lower())
        ]

        if not dim_signals:
            dim_signals = [
                s for s in profile.learning_history
                if s.dimension == dimension
            ]

        if not dim_signals:
            return {
                "dimension": dimension.value,
                "prediction": "insufficient_data",
                "confidence": 0.0,
                "accuracy": mirror.accuracy.value,
            }

        # Find most common action
        action_counts: dict[str, int] = {}
        for sig in dim_signals:
            action_counts[sig.action] = action_counts.get(sig.action, 0) + 1

        best_action = max(action_counts, key=action_counts.get)
        confidence = action_counts[best_action] / len(dim_signals)

        return {
            "dimension": dimension.value,
            "prediction": best_action,
            "confidence": round(confidence, 3),
            "accuracy": mirror.accuracy.value,
            "total_signals": len(dim_signals),
            "alternatives": sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:3],
        }

    def get_mirror_snapshot(
        self, twin_id: str, dimension: MirrorDimension
    ) -> dict[str, Any] | None:
        """Get the current mirror snapshot for a dimension.

        Args:
            twin_id: The twin to query.
            dimension: The dimension to snapshot.

        Returns:
            Mirror data dict.
        """
        profile = self._profiles.get(twin_id)
        if not profile:
            return None

        mirror = profile.mirrors.get(dimension.value)
        if not mirror:
            return None

        return {
            "dimension": dimension.value,
            "accuracy": mirror.accuracy.value,
            "confidence": mirror.confidence,
            "data": mirror.data,
            "last_updated": mirror.timestamp,
        }

    def get_profile_summary(self, twin_id: str) -> dict[str, Any] | None:
        """Get a complete summary of a twin profile.

        Args:
            twin_id: The twin to summarize.

        Returns:
            Profile summary dict.
        """
        profile = self._profiles.get(twin_id)
        if not profile:
            return None

        return {
            "twin_id": profile.twin_id,
            "name": profile.name,
            "sync_frequency": profile.sync_frequency.value,
            "total_interactions": profile.total_interactions,
            "total_signals": len(profile.learning_history),
            "mirrors": {
                dim.value: {
                    "accuracy": profile.mirrors[dim.value].accuracy.value,
                    "confidence": profile.mirrors[dim.value].confidence,
                    "signal_count": sum(
                        1 for s in profile.learning_history if s.dimension == dim
                    ),
                }
                for dim in MirrorDimension
            },
            "created_at": profile.created_at,
            "last_synced": profile.last_synced,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get platform statistics."""
        accuracy_counts: dict[str, int] = {}
        for profile in self._profiles.values():
            for mirror in profile.mirrors.values():
                accuracy_counts[mirror.accuracy.value] = (
                    accuracy_counts.get(mirror.accuracy.value, 0) + 1
                )

        return {
            "total_profiles": self._total_profiles,
            "total_signals": self._total_signals,
            "total_interactions": sum(
                p.total_interactions for p in self._profiles.values()
            ),
            "active_twins": len(self._profiles),
            "accuracy_distribution": accuracy_counts,
            "avg_signals_per_twin": round(
                self._total_signals / max(self._total_profiles, 1), 1
            ),
        }

    def reset(self) -> None:
        """Reset the platform to initial state."""
        self._profiles.clear()
        self._total_profiles = 0
        self._total_signals = 0


# ── Singleton accessors ──

_ai_twin: PlatformAITwin | None = None


def get_ai_twin() -> PlatformAITwin:
    """Get or create the singleton AI twin platform."""
    global _ai_twin
    if _ai_twin is None:
        _ai_twin = PlatformAITwin()
    return _ai_twin


def reset_ai_twin() -> None:
    """Reset the singleton AI twin platform."""
    global _ai_twin
    if _ai_twin is not None:
        _ai_twin.reset()
    _ai_twin = None