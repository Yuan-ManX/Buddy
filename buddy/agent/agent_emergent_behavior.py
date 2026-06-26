"""
Buddy Emergent Behavior Detector - Discovers and manages emergent agent behaviors.

Monitors agent actions across the platform to detect unexpected patterns that
arise from multi-agent interactions. Classifies emergent behaviors as beneficial,
neutral, or harmful, then automatically promotes useful patterns into reusable
capabilities and suppresses detrimental ones.

Core capabilities:
- Continuous observation of agent actions with context and outcome tracking
- Statistical pattern detection across temporal and behavioral dimensions
- Multi-faceted pattern classification (collaboration, optimization, creativity, etc.)
- Utility assessment with scoring across reliability, generalizability, and efficiency
- Auto-promotion of beneficial patterns into platform capabilities
- Auto-suppression of harmful or destabilizing patterns
- Full emergence reporting with timeline and contribution tracking
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.emergent_behavior")


# ═════════════════════════════════════════════════════════════════════════════
# Enums
# ═════════════════════════════════════════════════════════════════════════════

class PatternType(str, Enum):
    """Classification of an emergent pattern's impact."""
    BENEFICIAL = "beneficial"
    NEUTRAL = "neutral"
    HARMFUL = "harmful"


class PatternStatus(str, Enum):
    """Lifecycle status of an emergent pattern."""
    OBSERVED = "observed"
    ANALYZING = "analyzing"
    CLASSIFIED = "classified"
    PROMOTED = "promoted"
    SUPPRESSED = "suppressed"


class PatternCategory(str, Enum):
    """Category describing the nature of an emergent pattern."""
    COLLABORATION = "collaboration"
    OPTIMIZATION = "optimization"
    CREATIVITY = "creativity"
    PROBLEM_SOLVING = "problem_solving"
    COMMUNICATION = "communication"
    ANOMALY = "anomaly"


# ═════════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class Observation:
    """A single recorded agent action with its context and outcome."""
    id: str
    agent_id: str
    action: str
    context: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    timestamp: float = field(default_factory=time.time)
    success: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "action": self.action,
            "context": self.context,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass
class EmergentPattern:
    """A detected emergent pattern arising from agent interactions."""
    id: str
    name: str
    description: str
    agents_involved: list[str] = field(default_factory=list)
    frequency: int = 0
    first_observed: float = field(default_factory=time.time)
    last_observed: float = field(default_factory=time.time)
    confidence: float = 0.0
    pattern_type: PatternType = PatternType.NEUTRAL
    status: PatternStatus = PatternStatus.OBSERVED
    action_signatures: list[str] = field(default_factory=list)
    context_fingerprints: list[dict[str, Any]] = field(default_factory=list)
    observation_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agents_involved": self.agents_involved,
            "frequency": self.frequency,
            "first_observed": self.first_observed,
            "first_observed_datetime": datetime.fromtimestamp(
                self.first_observed, tz=timezone.utc
            ).isoformat(),
            "last_observed": self.last_observed,
            "last_observed_datetime": datetime.fromtimestamp(
                self.last_observed, tz=timezone.utc
            ).isoformat(),
            "confidence": self.confidence,
            "pattern_type": self.pattern_type.value,
            "status": self.status.value,
            "action_signatures": self.action_signatures,
            "observation_ids": self.observation_ids,
        }


@dataclass
class PatternClassification:
    """Detailed classification of a detected emergent pattern."""
    pattern_id: str
    category: PatternCategory
    confidence: float = 0.0
    characteristics: list[str] = field(default_factory=list)
    similar_known_patterns: list[str] = field(default_factory=list)
    classification_rationale: str = ""
    classified_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "category": self.category.value,
            "confidence": self.confidence,
            "characteristics": self.characteristics,
            "similar_known_patterns": self.similar_known_patterns,
            "classification_rationale": self.classification_rationale,
            "classified_at": self.classified_at,
            "classified_at_datetime": datetime.fromtimestamp(
                self.classified_at, tz=timezone.utc
            ).isoformat(),
        }


@dataclass
class UtilityAssessment:
    """Assessment of a pattern's usefulness and impact."""
    pattern_id: str
    utility_score: float = 0.0
    reliability: float = 0.0
    generalizability: float = 0.0
    efficiency_gain: float = 0.0
    risk_level: float = 0.0
    assessed_at: float = field(default_factory=time.time)
    assessment_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "utility_score": self.utility_score,
            "reliability": self.reliability,
            "generalizability": self.generalizability,
            "efficiency_gain": self.efficiency_gain,
            "risk_level": self.risk_level,
            "assessed_at": self.assessed_at,
            "assessment_notes": self.assessment_notes,
        }


@dataclass
class PromotedPattern:
    """A beneficial pattern that has been promoted to a platform capability."""
    pattern_id: str
    capability_name: str
    capability_description: str
    integration_notes: str = ""
    promoted_at: float = field(default_factory=time.time)
    source_pattern_name: str = ""
    utility_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "capability_name": self.capability_name,
            "capability_description": self.capability_description,
            "integration_notes": self.integration_notes,
            "promoted_at": self.promoted_at,
            "promoted_at_datetime": datetime.fromtimestamp(
                self.promoted_at, tz=timezone.utc
            ).isoformat(),
            "source_pattern_name": self.source_pattern_name,
            "utility_score": self.utility_score,
        }


@dataclass
class SuppressedPattern:
    """A harmful pattern that has been suppressed."""
    pattern_id: str
    suppression_reason: str = ""
    suppressed_at: float = field(default_factory=time.time)
    source_pattern_name: str = ""
    risk_level: float = 0.0
    mitigation_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "suppression_reason": self.suppression_reason,
            "suppressed_at": self.suppressed_at,
            "suppressed_at_datetime": datetime.fromtimestamp(
                self.suppressed_at, tz=timezone.utc
            ).isoformat(),
            "source_pattern_name": self.source_pattern_name,
            "risk_level": self.risk_level,
            "mitigation_actions": self.mitigation_actions,
        }


@dataclass
class EmergenceReport:
    """Comprehensive report on emergent behavior analysis."""
    total_observations: int = 0
    patterns_detected: int = 0
    promoted: int = 0
    suppressed: int = 0
    observation_rate: float = 0.0
    top_patterns: list[dict[str, Any]] = field(default_factory=list)
    agent_contributions: dict[str, int] = field(default_factory=dict)
    emergence_timeline: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_observations": self.total_observations,
            "patterns_detected": self.patterns_detected,
            "promoted": self.promoted,
            "suppressed": self.suppressed,
            "observation_rate": self.observation_rate,
            "top_patterns": self.top_patterns,
            "agent_contributions": self.agent_contributions,
            "emergence_timeline": self.emergence_timeline,
            "generated_at": self.generated_at,
            "generated_at_datetime": datetime.fromtimestamp(
                self.generated_at, tz=timezone.utc
            ).isoformat(),
        }


# ═════════════════════════════════════════════════════════════════════════════
# Emergent Behavior Detector
# ═════════════════════════════════════════════════════════════════════════════

class EmergentBehaviorDetector:
    """Detects, classifies, and manages emergent behaviors in agent systems.

    Accumulates observations from agent actions over time, applies statistical
    analysis to discover recurring patterns, classifies them by type and impact,
    and automatically promotes beneficial patterns while suppressing harmful ones.

    The detector uses action-signature hashing to group similar observations,
    temporal clustering to identify emerging trends, and multi-dimensional
    scoring to assess utility and risk.
    """

    # ── Configuration constants ─────────────────────────────────────────

    # Minimum number of observations sharing a signature before a pattern is
    # considered emergent.
    _MIN_OBSERVATIONS_FOR_PATTERN = 3

    # Minimum confidence threshold for a pattern to be classified.
    _MIN_CONFIDENCE_FOR_CLASSIFICATION = 0.4

    # Utility score threshold above which patterns are auto-promoted.
    _AUTO_PROMOTE_UTILITY_THRESHOLD = 7.0

    # Risk level threshold above which patterns are auto-suppressed.
    _AUTO_SUPPRESS_RISK_THRESHOLD = 7.0

    # Maximum number of recent observations to keep in the sliding window.
    _MAX_OBSERVATION_WINDOW = 10000

    def __init__(self) -> None:
        self._observations: dict[str, Observation] = {}
        self._patterns: dict[str, EmergentPattern] = {}
        self._classifications: dict[str, PatternClassification] = {}
        self._utilities: dict[str, UtilityAssessment] = {}
        self._promoted: dict[str, PromotedPattern] = {}
        self._suppressed: dict[str, SuppressedPattern] = {}

        # Action signature -> list of observation IDs for pattern detection
        self._signature_index: dict[str, list[str]] = defaultdict(list)
        # Agent ID -> list of observation IDs for contribution tracking
        self._agent_index: dict[str, list[str]] = defaultdict(list)

        # Timeline entries: list of (timestamp, event_type, description) dicts
        self._timeline: list[dict[str, Any]] = []

        self._total_observations: int = 0
        self._start_time: float = time.time()

    # ── Observation ─────────────────────────────────────────────────────

    def observe(
        self,
        agent_id: str,
        action: str,
        context: dict[str, Any] | None = None,
        outcome: str = "",
    ) -> Observation:
        """Record an agent action for emergent behavior analysis.

        Args:
            agent_id: Identifier of the agent performing the action.
            action: Description or name of the action performed.
            context: Additional contextual information about the action.
            outcome: The result or outcome of the action.

        Returns:
            The recorded Observation object.
        """
        obs_id = f"obs-{uuid.uuid4().hex[:12]}"
        observation = Observation(
            id=obs_id,
            agent_id=agent_id,
            action=action,
            context=context or {},
            outcome=outcome,
            timestamp=time.time(),
            success=self._infer_success(outcome),
            metadata={},
        )

        # Store observation
        self._observations[obs_id] = observation
        self._total_observations += 1

        # Build signature and index
        signature = self._build_action_signature(agent_id, action, context)
        self._signature_index[signature].append(obs_id)
        self._agent_index[agent_id].append(obs_id)

        # Enforce observation window
        if len(self._observations) > self._MAX_OBSERVATION_WINDOW:
            self._prune_oldest_observations()

        # Record timeline event
        self._timeline.append({
            "timestamp": observation.timestamp,
            "event_type": "observation",
            "agent_id": agent_id,
            "action": action[:120],
            "observation_id": obs_id,
        })

        logger.debug(
            "Recorded observation %s for agent %s: %s", obs_id, agent_id, action[:80]
        )

        return observation

    # ── Pattern Detection ────────────────────────────────────────────────

    def detect_patterns(self) -> list[EmergentPattern]:
        """Detect emergent patterns across all recorded observations.

        Uses action-signature clustering to group similar observations,
        then applies frequency and temporal analysis to identify patterns
        that exceed the minimum emergence threshold.

        Returns:
            List of newly detected or updated EmergentPattern instances.
        """
        detected: list[EmergentPattern] = []

        for signature, obs_ids in self._signature_index.items():
            if len(obs_ids) < self._MIN_OBSERVATIONS_FOR_PATTERN:
                continue

            existing_id = self._find_pattern_by_signature(signature)
            if existing_id:
                pattern = self._update_existing_pattern(existing_id, obs_ids, signature)
                detected.append(pattern)
            else:
                pattern = self._create_new_pattern(signature, obs_ids)
                if pattern is not None:
                    detected.append(pattern)

        # Update timeline
        if detected:
            self._timeline.append({
                "timestamp": time.time(),
                "event_type": "pattern_detection",
                "patterns_found": len(detected),
                "pattern_ids": [p.id for p in detected],
            })

        logger.info("Pattern detection complete: %d patterns found", len(detected))
        return detected

    # ── Pattern Classification ───────────────────────────────────────────

    def classify_pattern(self, pattern_id: str) -> PatternClassification:
        """Classify a detected pattern by its category and characteristics.

        Analyzes the pattern's action signatures, agent involvement, and
        outcomes to determine the most likely category (collaboration,
        optimization, creativity, problem-solving, communication, anomaly).

        Args:
            pattern_id: The identifier of the pattern to classify.

        Returns:
            A PatternClassification with the determined category and metadata.

        Raises:
            ValueError: If the pattern_id is not found.
        """
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            raise ValueError(f"Pattern not found: {pattern_id}")

        # Gather observation data for analysis
        observations = [
            self._observations[oid]
            for oid in pattern.observation_ids
            if oid in self._observations
        ]

        if not observations:
            raise ValueError(f"No observations found for pattern: {pattern_id}")

        # Determine category based on behavioral analysis
        category, characteristics, confidence = self._analyze_pattern_category(
            pattern, observations
        )

        # Find similar known patterns
        similar = self._find_similar_patterns(pattern, category)

        classification = PatternClassification(
            pattern_id=pattern_id,
            category=category,
            confidence=confidence,
            characteristics=characteristics,
            similar_known_patterns=similar,
            classification_rationale=self._build_classification_rationale(
                pattern, category, characteristics
            ),
        )

        self._classifications[pattern_id] = classification
        pattern.status = PatternStatus.CLASSIFIED

        # Determine pattern type based on category and characteristics
        pattern.pattern_type = self._infer_pattern_type(category, classification)

        self._timeline.append({
            "timestamp": classification.classified_at,
            "event_type": "classification",
            "pattern_id": pattern_id,
            "category": category.value,
            "confidence": confidence,
        })

        logger.info(
            "Classified pattern %s as %s (confidence: %.2f)",
            pattern_id, category.value, confidence,
        )

        return classification

    # ── Utility Evaluation ───────────────────────────────────────────────

    def evaluate_utility(self, pattern_id: str) -> UtilityAssessment:
        """Evaluate the usefulness and impact of a detected pattern.

        Scores the pattern across multiple dimensions: reliability (based
        on success rate of constituent observations), generalizability
        (based on agent and context diversity), efficiency gain (based on
        action patterns), and risk level (based on anomaly indicators).

        Args:
            pattern_id: The identifier of the pattern to evaluate.

        Returns:
            A UtilityAssessment with scores across all dimensions.

        Raises:
            ValueError: If the pattern_id is not found.
        """
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            raise ValueError(f"Pattern not found: {pattern_id}")

        observations = [
            self._observations[oid]
            for oid in pattern.observation_ids
            if oid in self._observations
        ]

        if not observations:
            raise ValueError(f"No observations found for pattern: {pattern_id}")

        # Compute reliability: proportion of successful observations
        success_count = sum(1 for o in observations if o.success)
        reliability = success_count / len(observations) if observations else 0.0

        # Compute generalizability: based on diversity of agents and contexts
        unique_agents = len(set(o.agent_id for o in observations))
        unique_contexts = len(set(
            frozenset(o.context.items()) if o.context else ()
            for o in observations
        ))
        generalizability = min(
            (unique_agents / max(len(pattern.agents_involved), 1)) * 0.5
            + min(unique_contexts / max(len(observations), 1), 1.0) * 0.5,
            1.0,
        )

        # Compute efficiency gain: based on pattern frequency and success rate
        time_span = pattern.last_observed - pattern.first_observed
        if time_span > 0:
            frequency_rate = pattern.frequency / max(time_span / 3600.0, 0.001)
            efficiency_gain = min(
                (frequency_rate / 10.0) * 0.4 + reliability * 0.6, 1.0
            )
        else:
            efficiency_gain = reliability * 0.5

        # Compute risk level: based on anomaly indicators and failure patterns
        failure_rate = 1.0 - reliability
        classification = self._classifications.get(pattern_id)
        is_anomaly = (
            classification is not None
            and classification.category == PatternCategory.ANOMALY
        )
        risk_level = min(
            failure_rate * 0.6
            + (0.3 if is_anomaly else 0.0)
            + (0.1 if pattern.pattern_type == PatternType.HARMFUL else 0.0),
            1.0,
        )

        # Compute overall utility score
        utility_score = round(
            (reliability * 3.0
             + generalizability * 2.5
             + efficiency_gain * 3.0
             - risk_level * 2.5),
            1,
        )
        utility_score = max(0.0, min(10.0, utility_score + 2.5))

        assessment = UtilityAssessment(
            pattern_id=pattern_id,
            utility_score=utility_score,
            reliability=round(reliability, 3),
            generalizability=round(generalizability, 3),
            efficiency_gain=round(efficiency_gain, 3),
            risk_level=round(risk_level, 3),
            assessment_notes=self._build_assessment_notes(
                reliability, generalizability, efficiency_gain, risk_level, utility_score
            ),
        )

        self._utilities[pattern_id] = assessment

        # Auto-promote or auto-suppress based on scores
        if utility_score >= self._AUTO_PROMOTE_UTILITY_THRESHOLD and risk_level < 0.5:
            self._auto_promote(pattern, assessment)
        elif risk_level >= self._AUTO_SUPPRESS_RISK_THRESHOLD:
            self._auto_suppress(pattern, assessment)

        self._timeline.append({
            "timestamp": assessment.assessed_at,
            "event_type": "utility_assessment",
            "pattern_id": pattern_id,
            "utility_score": utility_score,
            "risk_level": round(risk_level, 3),
        })

        logger.info(
            "Utility assessment for pattern %s: score=%.1f, risk=%.2f",
            pattern_id, utility_score, risk_level,
        )

        return assessment

    # ── Pattern Promotion ────────────────────────────────────────────────

    def promote_pattern(self, pattern_id: str) -> PromotedPattern:
        """Promote a useful emergent pattern to a platform capability.

        Generates a capability name and description from the pattern's
        characteristics, along with integration guidance.

        Args:
            pattern_id: The identifier of the pattern to promote.

        Returns:
            A PromotedPattern with capability details and integration notes.

        Raises:
            ValueError: If the pattern_id is not found or already suppressed.
        """
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            raise ValueError(f"Pattern not found: {pattern_id}")

        if pattern.status == PatternStatus.SUPPRESSED:
            raise ValueError(f"Cannot promote a suppressed pattern: {pattern_id}")

        # Generate capability name from pattern characteristics
        capability_name = self._generate_capability_name(pattern)
        capability_description = self._generate_capability_description(pattern)

        utility = self._utilities.get(pattern_id)
        utility_score = utility.utility_score if utility else 0.0

        promoted = PromotedPattern(
            pattern_id=pattern_id,
            capability_name=capability_name,
            capability_description=capability_description,
            integration_notes=self._generate_integration_notes(pattern),
            source_pattern_name=pattern.name,
            utility_score=utility_score,
        )

        self._promoted[pattern_id] = promoted
        pattern.status = PatternStatus.PROMOTED

        self._timeline.append({
            "timestamp": promoted.promoted_at,
            "event_type": "promotion",
            "pattern_id": pattern_id,
            "capability_name": capability_name,
        })

        logger.info(
            "Promoted pattern %s to capability '%s'", pattern_id, capability_name
        )

        return promoted

    # ── Pattern Suppression ──────────────────────────────────────────────

    def suppress_pattern(self, pattern_id: str) -> SuppressedPattern:
        """Suppress a harmful or destabilizing emergent pattern.

        Records the suppression reason, risk level, and recommended
        mitigation actions.

        Args:
            pattern_id: The identifier of the pattern to suppress.

        Returns:
            A SuppressedPattern with suppression details.

        Raises:
            ValueError: If the pattern_id is not found.
        """
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            raise ValueError(f"Pattern not found: {pattern_id}")

        utility = self._utilities.get(pattern_id)
        risk_level = utility.risk_level if utility else 0.5

        reason = self._build_suppression_reason(pattern, risk_level)
        mitigation = self._generate_mitigation_actions(pattern)

        suppressed = SuppressedPattern(
            pattern_id=pattern_id,
            suppression_reason=reason,
            source_pattern_name=pattern.name,
            risk_level=risk_level,
            mitigation_actions=mitigation,
        )

        self._suppressed[pattern_id] = suppressed
        pattern.status = PatternStatus.SUPPRESSED

        self._timeline.append({
            "timestamp": suppressed.suppressed_at,
            "event_type": "suppression",
            "pattern_id": pattern_id,
            "risk_level": risk_level,
        })

        logger.info(
            "Suppressed pattern %s (risk: %.2f)", pattern_id, risk_level
        )

        return suppressed

    # ── Emergence Report ─────────────────────────────────────────────────

    def get_emergence_report(self) -> EmergenceReport:
        """Generate a comprehensive report on emergent behavior analysis.

        Aggregates all observations, patterns, promotions, and suppressions
        into a single report with timeline and contribution data.

        Returns:
            An EmergenceReport with full analysis results.
        """
        now = time.time()
        elapsed = now - self._start_time
        observation_rate = (
            self._total_observations / (elapsed / 3600.0) if elapsed > 0 else 0.0
        )

        # Top patterns ranked by confidence
        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: (p.confidence, p.frequency),
            reverse=True,
        )
        top_patterns = [
            {
                "id": p.id,
                "name": p.name,
                "confidence": p.confidence,
                "frequency": p.frequency,
                "type": p.pattern_type.value,
                "status": p.status.value,
            }
            for p in sorted_patterns[:10]
        ]

        # Agent contribution counts
        agent_contributions = {
            agent_id: len(obs_ids)
            for agent_id, obs_ids in self._agent_index.items()
        }

        # Timeline sorted by timestamp
        timeline = sorted(self._timeline, key=lambda e: e["timestamp"])

        return EmergenceReport(
            total_observations=self._total_observations,
            patterns_detected=len(self._patterns),
            promoted=len(self._promoted),
            suppressed=len(self._suppressed),
            observation_rate=round(observation_rate, 2),
            top_patterns=top_patterns,
            agent_contributions=agent_contributions,
            emergence_timeline=timeline,
        )

    # ── Reset ────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all accumulated state in the detector."""
        self._observations.clear()
        self._patterns.clear()
        self._classifications.clear()
        self._utilities.clear()
        self._promoted.clear()
        self._suppressed.clear()
        self._signature_index.clear()
        self._agent_index.clear()
        self._timeline.clear()
        self._total_observations = 0
        self._start_time = time.time()
        logger.info("EmergentBehaviorDetector has been reset")

    # ── Internal Helpers ─────────────────────────────────────────────────

    def _build_action_signature(
        self, agent_id: str, action: str, context: dict[str, Any] | None
    ) -> str:
        """Build a normalized signature for grouping similar actions."""
        # Normalize action by extracting key verb-noun patterns
        action_lower = action.lower().strip()
        # Use first 3 words as the core signature component
        words = action_lower.split()
        core = " ".join(words[:3]) if len(words) >= 3 else action_lower

        # Include context keys (sorted for determinism) as part of the signature
        ctx_keys = sorted(context.keys()) if context else []
        ctx_part = ",".join(ctx_keys[:5]) if ctx_keys else ""

        return f"{core}|{ctx_part}"

    def _infer_success(self, outcome: str) -> bool:
        """Infer success from the outcome string."""
        if not outcome:
            return False
        outcome_lower = outcome.lower()
        positive_indicators = [
            "success", "completed", "ok", "done", "resolved",
            "achieved", "passed", "finished", "correct",
        ]
        negative_indicators = [
            "fail", "error", "timeout", "rejected", "aborted",
            "cancelled", "denied", "invalid", "exception",
        ]
        for neg in negative_indicators:
            if neg in outcome_lower:
                return False
        for pos in positive_indicators:
            if pos in outcome_lower:
                return True
        return False

    def _find_pattern_by_signature(self, signature: str) -> str | None:
        """Find an existing pattern ID that matches the given signature."""
        for pid, pattern in self._patterns.items():
            if pattern.action_signatures and pattern.action_signatures[0] == signature:
                return pid
        return None

    def _update_existing_pattern(
        self, pattern_id: str, obs_ids: list[str], signature: str
    ) -> EmergentPattern:
        """Update an existing pattern with new observation data."""
        pattern = self._patterns[pattern_id]
        pattern.frequency = len(obs_ids)
        pattern.last_observed = max(
            self._observations[oid].timestamp
            for oid in obs_ids
            if oid in self._observations
        )
        pattern.observation_ids = obs_ids
        agents = set()
        for oid in obs_ids:
            if oid in self._observations:
                agents.add(self._observations[oid].agent_id)
        pattern.agents_involved = list(agents)
        pattern.confidence = min(
            1.0, pattern.confidence + 0.05 * (len(obs_ids) - pattern.frequency + 1)
        )
        return pattern

    def _create_new_pattern(
        self, signature: str, obs_ids: list[str]
    ) -> EmergentPattern | None:
        """Create a new pattern from a signature cluster."""
        if len(obs_ids) < self._MIN_OBSERVATIONS_FOR_PATTERN:
            return None

        observations = [
            self._observations[oid]
            for oid in obs_ids
            if oid in self._observations
        ]
        if not observations:
            return None

        timestamps = [o.timestamp for o in observations]
        agents = list(set(o.agent_id for o in observations))
        actions = list(set(o.action for o in observations))

        # Generate a descriptive name
        name = self._generate_pattern_name(actions, agents)

        # Generate description
        description = self._generate_pattern_description(
            actions, agents, len(observations)
        )

        # Compute initial confidence based on observation consistency
        success_rate = sum(1 for o in observations if o.success) / len(observations)
        context_similarity = self._compute_context_similarity(observations)
        confidence = min(1.0, (success_rate * 0.4 + context_similarity * 0.3 + 0.3))

        pattern_id = f"pat-{uuid.uuid4().hex[:12]}"
        pattern = EmergentPattern(
            id=pattern_id,
            name=name,
            description=description,
            agents_involved=agents,
            frequency=len(obs_ids),
            first_observed=min(timestamps),
            last_observed=max(timestamps),
            confidence=round(confidence, 3),
            pattern_type=PatternType.NEUTRAL,
            status=PatternStatus.OBSERVED,
            action_signatures=[signature],
            observation_ids=obs_ids,
        )

        self._patterns[pattern_id] = pattern
        return pattern

    def _generate_pattern_name(
        self, actions: list[str], agents: list[str]
    ) -> str:
        """Generate a descriptive name for a pattern."""
        if not actions:
            return "Emergent Pattern"
        # Use the most common action as basis
        action = max(set(actions), key=actions.count) if actions else actions[0]
        words = action.lower().split()[:4]
        base = " ".join(words).title()
        return f"{base} Pattern"

    def _generate_pattern_description(
        self, actions: list[str], agents: list[str], count: int
    ) -> str:
        """Generate a description for a detected pattern."""
        unique_actions = len(set(actions))
        return (
            f"Recurring pattern observed {count} times across {len(agents)} agent(s) "
            f"involving {unique_actions} distinct action type(s). "
            f"Detected through statistical clustering of action signatures."
        )

    def _compute_context_similarity(self, observations: list[Observation]) -> float:
        """Compute how similar the contexts are across observations."""
        if len(observations) < 2:
            return 0.5
        # Compare context key overlap
        ctx_sets = [set(o.context.keys()) if o.context else set() for o in observations]
        if not ctx_sets or all(len(c) == 0 for c in ctx_sets):
            return 0.5
        # Jaccard similarity averaged across all pairs (sample)
        similarities = []
        for i in range(min(len(ctx_sets), 10)):
            for j in range(i + 1, min(len(ctx_sets), 10)):
                union = ctx_sets[i] | ctx_sets[j]
                intersection = ctx_sets[i] & ctx_sets[j]
                if union:
                    similarities.append(len(intersection) / len(union))
        return sum(similarities) / len(similarities) if similarities else 0.5

    def _analyze_pattern_category(
        self,
        pattern: EmergentPattern,
        observations: list[Observation],
    ) -> tuple[PatternCategory, list[str], float]:
        """Analyze and determine the category of a pattern."""
        scores: dict[PatternCategory, float] = defaultdict(float)
        characteristics: list[str] = []

        all_actions = " ".join(o.action.lower() for o in observations)
        all_outcomes = " ".join(o.outcome.lower() for o in observations)
        agent_count = len(pattern.agents_involved)

        # Collaboration indicators
        collaboration_keywords = [
            "collaborate", "share", "delegate", "coordinate", "team",
            "together", "joint", "peer", "partner", "assist",
        ]
        collab_hits = sum(1 for kw in collaboration_keywords if kw in all_actions)
        if agent_count >= 3 or collab_hits >= 2:
            scores[PatternCategory.COLLABORATION] += 0.3 + min(collab_hits * 0.15, 0.4)
            characteristics.append("multi-agent coordination")

        # Optimization indicators
        optimization_keywords = [
            "optimize", "reduce", "faster", "efficient", "speed",
            "cache", "batch", "parallel", "shortcut", "streamline",
        ]
        opt_hits = sum(1 for kw in optimization_keywords if kw in all_actions)
        if opt_hits >= 2:
            scores[PatternCategory.OPTIMIZATION] += 0.3 + min(opt_hits * 0.15, 0.4)
            characteristics.append("performance optimization")

        # Creativity indicators
        creativity_keywords = [
            "create", "generate", "novel", "innovative", "design",
            "compose", "invent", "imagine", "synthesize", "craft",
        ]
        creative_hits = sum(1 for kw in creativity_keywords if kw in all_actions)
        if creative_hits >= 2:
            scores[PatternCategory.CREATIVITY] += 0.3 + min(creative_hits * 0.15, 0.4)
            characteristics.append("novel solution generation")

        # Problem-solving indicators
        ps_keywords = [
            "solve", "resolve", "fix", "debug", "troubleshoot",
            "diagnose", "repair", "recover", "handle", "mitigate",
        ]
        ps_hits = sum(1 for kw in ps_keywords if kw in all_actions)
        if ps_hits >= 2:
            scores[PatternCategory.PROBLEM_SOLVING] += 0.3 + min(ps_hits * 0.15, 0.4)
            characteristics.append("problem resolution")

        # Communication indicators
        comm_keywords = [
            "message", "notify", "alert", "report", "inform",
            "communicate", "broadcast", "announce", "relay", "signal",
        ]
        comm_hits = sum(1 for kw in comm_keywords if kw in all_actions)
        if comm_hits >= 2:
            scores[PatternCategory.COMMUNICATION] += 0.3 + min(comm_hits * 0.15, 0.4)
            characteristics.append("information exchange")

        # Anomaly indicators
        anomaly_keywords = [
            "unexpected", "anomaly", "unusual", "strange", "abnormal",
            "deviation", "irregular", "odd", "surprising", "unknown",
        ]
        anomaly_hits = sum(1 for kw in anomaly_keywords if kw in all_actions)
        failure_rate = (
            1.0 - sum(1 for o in observations if o.success) / len(observations)
        )
        if anomaly_hits >= 1 or failure_rate > 0.5:
            scores[PatternCategory.ANOMALY] += 0.2 + min(anomaly_hits * 0.2, 0.3)
            if failure_rate > 0.5:
                scores[PatternCategory.ANOMALY] += 0.3
            characteristics.append("unusual behavior pattern")

        # If no strong category signal, default to problem_solving or anomaly
        if not scores:
            if failure_rate > 0.4:
                scores[PatternCategory.ANOMALY] = 0.4
                characteristics.append("low-confidence anomalous pattern")
            else:
                scores[PatternCategory.PROBLEM_SOLVING] = 0.35
                characteristics.append("general action pattern")

        # Pick the highest-scoring category
        best_category = max(scores, key=lambda k: scores[k])
        confidence = min(1.0, scores[best_category])

        return best_category, characteristics, round(confidence, 3)

    def _find_similar_patterns(
        self, pattern: EmergentPattern, category: PatternCategory
    ) -> list[str]:
        """Find similar patterns among already-classified patterns."""
        similar: list[str] = []
        for pid, existing in self._patterns.items():
            if pid == pattern.id:
                continue
            if pid not in self._classifications:
                continue
            cls = self._classifications[pid]
            if cls.category == category:
                similar.append(existing.name)
        return similar[:5]

    def _build_classification_rationale(
        self,
        pattern: EmergentPattern,
        category: PatternCategory,
        characteristics: list[str],
    ) -> str:
        """Build a human-readable rationale for the classification."""
        return (
            f"Pattern classified as {category.value} based on "
            f"{len(characteristics)} characteristic(s): {', '.join(characteristics)}. "
            f"Observed {pattern.frequency} times across {len(pattern.agents_involved)} "
            f"agent(s) with confidence {pattern.confidence:.2f}."
        )

    def _infer_pattern_type(
        self,
        category: PatternCategory,
        classification: PatternClassification,
    ) -> PatternType:
        """Infer whether a pattern is beneficial, neutral, or harmful."""
        if category == PatternCategory.ANOMALY:
            return PatternType.HARMFUL if classification.confidence > 0.7 else PatternType.NEUTRAL
        if category in (PatternCategory.COLLABORATION, PatternCategory.OPTIMIZATION):
            return PatternType.BENEFICIAL
        if category == PatternCategory.CREATIVITY:
            return PatternType.BENEFICIAL
        return PatternType.NEUTRAL

    def _build_assessment_notes(
        self,
        reliability: float,
        generalizability: float,
        efficiency_gain: float,
        risk_level: float,
        utility_score: float,
    ) -> str:
        """Build human-readable assessment notes."""
        notes = []
        if reliability >= 0.8:
            notes.append("highly reliable")
        elif reliability < 0.5:
            notes.append("low reliability")

        if generalizability >= 0.7:
            notes.append("broadly generalizable")
        elif generalizability < 0.3:
            notes.append("narrowly applicable")

        if efficiency_gain >= 0.7:
            notes.append("significant efficiency gain")
        elif efficiency_gain < 0.3:
            notes.append("minimal efficiency impact")

        if risk_level >= 0.6:
            notes.append("elevated risk level")
        elif risk_level < 0.2:
            notes.append("low risk")

        notes.append(f"overall utility score: {utility_score}/10")
        return "; ".join(notes)

    def _auto_promote(
        self, pattern: EmergentPattern, assessment: UtilityAssessment
    ) -> PromotedPattern | None:
        """Automatically promote a pattern that meets the promotion threshold."""
        if pattern.status == PatternStatus.PROMOTED:
            return self._promoted.get(pattern.id)
        if pattern.status == PatternStatus.SUPPRESSED:
            return None
        return self.promote_pattern(pattern.id)

    def _auto_suppress(
        self, pattern: EmergentPattern, assessment: UtilityAssessment
    ) -> SuppressedPattern | None:
        """Automatically suppress a pattern that exceeds the risk threshold."""
        if pattern.status == PatternStatus.SUPPRESSED:
            return self._suppressed.get(pattern.id)
        return self.suppress_pattern(pattern.id)

    def _generate_capability_name(self, pattern: EmergentPattern) -> str:
        """Generate a capability name from a pattern."""
        base = pattern.name.replace(" Pattern", "").strip()
        return f"EmergentCapability.{base.replace(' ', '')}"

    def _generate_capability_description(self, pattern: EmergentPattern) -> str:
        """Generate a capability description from a pattern."""
        return (
            f"Auto-generated capability derived from emergent pattern '{pattern.name}'. "
            f"Observed across {len(pattern.agents_involved)} agent(s) with "
            f"{pattern.frequency} occurrences. Confidence: {pattern.confidence:.2f}."
        )

    def _generate_integration_notes(self, pattern: EmergentPattern) -> str:
        """Generate integration guidance for a promoted pattern."""
        return (
            f"To integrate this capability, register it in the capability mesh "
            f"with agents {', '.join(pattern.agents_involved[:5])}. "
            f"Monitor for {pattern.frequency // 2 + 1} additional occurrences "
            f"to validate stability."
        )

    def _build_suppression_reason(
        self, pattern: EmergentPattern, risk_level: float
    ) -> str:
        """Build a reason string for suppressing a pattern."""
        reasons = []
        if risk_level >= 0.7:
            reasons.append("high risk level")
        if pattern.pattern_type == PatternType.HARMFUL:
            reasons.append("classified as harmful")
        if pattern.frequency >= 10:
            reasons.append("high frequency of recurrence")
        if not reasons:
            reasons.append("elevated risk indicators")
        return f"Pattern suppressed due to: {'; '.join(reasons)}."

    def _generate_mitigation_actions(
        self, pattern: EmergentPattern
    ) -> list[str]:
        """Generate mitigation actions for a suppressed pattern."""
        actions = [
            f"Block action signatures matching pattern {pattern.id}",
            f"Notify affected agents: {', '.join(pattern.agents_involved[:3])}",
        ]
        if pattern.frequency >= 5:
            actions.append(
                "Add monitoring rule to alert on recurrence of this pattern"
            )
        actions.append("Log all future occurrences for audit trail")
        return actions

    def _prune_oldest_observations(self) -> None:
        """Remove the oldest observations to stay within the window limit."""
        if len(self._observations) <= self._MAX_OBSERVATION_WINDOW:
            return

        # Sort by timestamp and remove the oldest excess entries
        sorted_ids = sorted(
            self._observations.keys(),
            key=lambda oid: self._observations[oid].timestamp,
        )
        excess = len(self._observations) - self._MAX_OBSERVATION_WINDOW
        to_remove = sorted_ids[:excess]

        for oid in to_remove:
            obs = self._observations.pop(oid, None)
            if obs is None:
                continue
            # Clean up signature index
            signature = self._build_action_signature(
                obs.agent_id, obs.action, obs.context
            )
            if signature in self._signature_index:
                self._signature_index[signature] = [
                    x for x in self._signature_index[signature] if x != oid
                ]
                if not self._signature_index[signature]:
                    del self._signature_index[signature]
            # Clean up agent index
            if obs.agent_id in self._agent_index:
                self._agent_index[obs.agent_id] = [
                    x for x in self._agent_index[obs.agent_id] if x != oid
                ]
                if not self._agent_index[obs.agent_id]:
                    del self._agent_index[obs.agent_id]

        logger.debug("Pruned %d oldest observations", len(to_remove))


# ═════════════════════════════════════════════════════════════════════════════
# Singleton
# ═════════════════════════════════════════════════════════════════════════════

_emergent_behavior: EmergentBehaviorDetector | None = None


def get_emergent_behavior() -> EmergentBehaviorDetector:
    """Get or create the global EmergentBehaviorDetector singleton instance."""
    global _emergent_behavior
    if _emergent_behavior is None:
        _emergent_behavior = EmergentBehaviorDetector()
        logger.info("Global EmergentBehaviorDetector singleton created")
    return _emergent_behavior


def reset_emergent_behavior() -> None:
    """Reset the global EmergentBehaviorDetector singleton instance."""
    global _emergent_behavior
    if _emergent_behavior is not None:
        _emergent_behavior.reset()
    _emergent_behavior = None
    logger.info("Global EmergentBehaviorDetector singleton reset")