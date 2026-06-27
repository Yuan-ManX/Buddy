"""
Buddy Agent Uncertainty Quantifier - Quantifies and manages uncertainty in agent outputs.

Provides a comprehensive uncertainty quantification engine that:
- Detects hedging language and uncertainty indicators in agent-generated text
- Segments text and assigns per-segment confidence scores
- Calibrates raw confidence scores using multiple calibration methods
- Generates alternative interpretations with probability weights
- Flags high-risk or high-uncertainty outputs for human review
- Tracks uncertainty patterns over time with aggregate metrics
"""

from __future__ import annotations

import logging
import math
import re
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.uncertainty_quantifier")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class UncertaintySource(str, Enum):
    """Sources of uncertainty in agent outputs."""
    KNOWLEDGE_GAP = "knowledge_gap"
    AMBIGUITY = "ambiguity"
    CONTRADICTION = "contradiction"
    INCOMPLETE_INFO = "incomplete_info"
    SPECULATION = "speculation"
    EXTRAPOLATION = "extrapolation"
    LOW_CONFIDENCE_SOURCE = "low_confidence_source"
    MODEL_LIMITATION = "model_limitation"


class VerificationPriority(str, Enum):
    """Priority levels for verification of uncertain outputs."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    """Risk severity levels for queries and outputs."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CalibrationMethod(str, Enum):
    """Methods used to calibrate confidence scores."""
    HEDGING_DENSITY = "hedging_density"
    SEGMENT_VARIANCE = "segment_variance"
    SOURCE_WEIGHTING = "source_weighting"
    HISTORICAL_ADJUSTMENT = "historical_adjustment"
    CONSISTENCY_CHECK = "consistency_check"
    CROSS_VALIDATION = "cross_validation"


# ═══════════════════════════════════════════════════════════
# Hedging Language Detection
# ═══════════════════════════════════════════════════════════

HEDGING_PATTERNS: list[tuple[str, float]] = [
    # High-uncertainty hedges (weight >= 0.7)
    (r"\bI('?m|\s+am)\s+not\s+(entirely\s+)?sure\b", 0.85),
    (r"\bI\s+(can('?t|not)\s+)?(really\s+)?say\s+for\s+(sure|certain)\b", 0.80),
    (r"\b(this\s+is\s+)?(highly\s+)?speculative\b", 0.85),
    (r"\b(pure(ly)?\s+)?conjecture\b", 0.85),
    (r"\b(unclear|uncertain|unknown)\b", 0.75),
    (r"\bimpossible\s+to\s+(determine|know|say|verify)\b", 0.80),
    (r"\bbeyond\s+(my\s+)?(current\s+)?knowledge\b", 0.80),
    (r"\bno\s+(clear|definitive|conclusive)\s+(answer|evidence|data)\b", 0.80),

    # Medium-uncertainty hedges (weight 0.4-0.7)
    (r"\bI\s+(think|believe|suspect|guess|imagine|suppose|assume)\b", 0.50),
    (r"\b(in\s+my\s+opinion|IMHO|personally)\b", 0.45),
    (r"\b(it\s+)?(seems?|appears?)(\s+to\s+be)?\b", 0.40),
    (r"\b(suggests?|indicates?|implies?|hints?\s+at)\b", 0.40),
    (r"\bto\s+the\s+best\s+of\s+(my\s+)?knowledge\b", 0.45),
    (r"\bas\s+far\s+as\s+I\s+(know|can\s+tell)\b", 0.45),
    (r"\bpotentially\b", 0.35),
    (r"\b(presumably|allegedly|reportedly|supposedly)\b", 0.45),
    (r"\b(arguably|debatably|conceivably)\b", 0.40),

    # Low-uncertainty hedges (weight < 0.4)
    (r"\b(probably|likely|unlikely|possibly|maybe|perhaps)\b", 0.30),
    (r"\b(might|may|could|can|would|should)\b", 0.20),
    (r"\b(approximately|roughly|around|about|nearly|almost)\b", 0.25),
    (r"\b(generally|typically|usually|often|sometimes|occasionally)\b", 0.25),
    (r"\b(tends?\s+to|inclined\s+to|prone\s+to)\b", 0.30),
    (r"\b(in\s+most\s+cases|in\s+general|broadly\s+speaking)\b", 0.30),
    (r"\b(relatively|somewhat|fairly|rather|quite)\b", 0.20),
    (r"\b(estimates?|approximations?|ballpark)\b", 0.35),
    (r"\b(tentative(ly)?|provisional(ly)?)\b", 0.40),
    (r"\b(pending\s+(further\s+)?(verification|confirmation|review))\b", 0.40),
    (r"\b(subject\s+to\s+(change|revision|update))\b", 0.35),
    (r"\b(based\s+on\s+(limited|incomplete|partial)\s+(data|information))\b", 0.55),
    (r"\b(without\s+(further|more|additional)\s+(context|information|data))\b", 0.50),
]

# Words and phrases that reduce confidence in nearby text
LOW_CONFIDENCE_MODIFIERS: list[str] = [
    "however", "although", "but", "nevertheless", "nonetheless",
    "on the other hand", "that said", "having said that",
    "it should be noted", "it is worth noting", "note that",
    "caution", "warning", "disclaimer", "caveat",
]

# Contradiction detection patterns
CONTRADICTION_PATTERNS: list[str] = [
    r"\b(on\s+the\s+one\s+hand.*on\s+the\s+other\s+hand)\b",
    r"\b(however.* contradict)",
    r"\b(although.* actually)",
    r"\b(while.* at\s+the\s+same\s+time)",
    r"\b(despite.* still)",
    r"\b(but\s+in\s+(fact|reality|truth))",
    r"\b(contrary\s+to)",
    r"\b(in\s+contrast)",
]

# Knowledge gap indicators
KNOWLEDGE_GAP_PATTERNS: list[str] = [
    r"\b(I\s+(do\s+)?not\s+(have|possess)\s+(enough|sufficient|adequate)\s+(information|data|knowledge|context))",
    r"\b(beyond\s+the\s+scope\s+of)\b",
    r"\b(outside\s+(my\s+)?(training|knowledge)\s+(data|domain|scope))",
    r"\b(insufficient\s+(data|information|context|detail))",
    r"\b(lack(s)?\s+(of\s+)?(sufficient\s+)?(information|data|context|detail))",
    r"\b(more\s+(information|data|context|detail)\s+(is\s+)?(needed|required|necessary))",
    r"\b(cannot\s+(fully\s+)?(determine|assess|evaluate|verify|confirm))",
]

# High-risk domain terms
HIGH_RISK_TERMS: list[str] = [
    "medical", "diagnosis", "treatment", "symptom", "disease",
    "legal", "lawsuit", "liability", "compliance", "regulation",
    "financial", "investment", "trading", "tax", "mortgage",
    "security", "vulnerability", "exploit", "hack", "breach",
    "safety", "emergency", "crisis", "danger", "hazard",
    "personal", "identity", "password", "credential", "private",
    "ethical", "moral", "discrimination", "bias", "fairness",
    "political", "election", "policy", "government", "legislation",
]

# Bias indicator terms
BIAS_INDICATORS: list[str] = [
    "always", "never", "everyone", "nobody", "obviously",
    "clearly", "undoubtedly", "absolutely", "definitely",
    "without question", "without a doubt", "certainly",
    "all", "none", "best", "worst", "only",
]

# Ethical concern indicators
ETHICAL_CONCERN_TERMS: list[str] = [
    "exploit", "manipulate", "deceive", "trick", "cheat",
    "bypass", "circumvent", "evade", "illegal", "unethical",
    "harmful", "dangerous", "malicious", "fraudulent",
    "discriminate", "stereotype", "offensive",
]


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class UncertaintySegment:
    """A text segment with an associated confidence score."""
    text: str
    confidence: float  # 0.0 to 1.0
    start_index: int
    end_index: int
    source: UncertaintySource
    hedging_phrases: list[str] = field(default_factory=list)


@dataclass
class UncertaintyAssessment:
    """Complete uncertainty assessment of a text output."""
    id: str
    overall_confidence: float  # 0.0 to 1.0
    sources: list[UncertaintySource]
    uncertainty_segments: list[UncertaintySegment] = field(default_factory=list)
    factuality_score: float = 1.0
    precision_score: float = 1.0
    requires_verification: bool = False
    verification_priority: VerificationPriority = VerificationPriority.LOW
    hedging_phrases_detected: list[str] = field(default_factory=list)
    suggested_caveats: list[str] = field(default_factory=list)
    text_length: int = 0
    segment_count: int = 0
    assessed_at: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def high_uncertainty_segments(self) -> list[UncertaintySegment]:
        """Return segments with confidence below 0.5."""
        return [s for s in self.uncertainty_segments if s.confidence < 0.5]

    @property
    def hedging_density(self) -> float:
        """Ratio of hedging phrases to text length (0.0 to 1.0)."""
        if self.text_length == 0:
            return 0.0
        return min(len(self.hedging_phrases_detected) / (self.text_length / 100), 1.0)


@dataclass
class CalibrationFactor:
    """A single factor that contributed to confidence calibration."""
    method: CalibrationMethod
    description: str
    adjustment: float  # Positive or negative adjustment
    weight: float = 1.0  # How much this factor influenced the result


@dataclass
class CalibratedAssessment:
    """A calibrated version of an uncertainty assessment."""
    original_assessment: UncertaintyAssessment
    calibrated_confidence: float  # 0.0 to 1.0
    calibration_method: str  # Composite method description
    calibration_factors: list[CalibrationFactor] = field(default_factory=list)
    reliability_score: float = 1.0  # 0.0 to 1.0 - how reliable the calibration is
    calibrated_at: float = field(default_factory=time.time)

    @property
    def confidence_shift(self) -> float:
        """How much the confidence changed after calibration."""
        return self.calibrated_confidence - self.original_assessment.overall_confidence


@dataclass
class Alternative:
    """An alternative interpretation of uncertain text."""
    id: str
    text: str
    confidence: float  # 0.0 to 1.0
    probability: float  # 0.0 to 1.0 - relative likelihood
    rationale: str


@dataclass
class RiskProfile:
    """Risk assessment profile for a query or output."""
    risk_level: RiskLevel
    risk_factors: list[str] = field(default_factory=list)
    mitigation_suggestions: list[str] = field(default_factory=list)
    safe_handling_required: bool = False
    content_warnings: list[str] = field(default_factory=list)
    ethical_concerns: list[str] = field(default_factory=list)
    bias_indicators: list[str] = field(default_factory=list)
    domain_risk_score: float = 0.0  # 0.0 to 1.0
    assessed_at: float = field(default_factory=time.time)


@dataclass
class ReviewFlag:
    """A flag indicating an output requires human review."""
    flag_id: str
    assessment_id: str
    reason: str
    priority: VerificationPriority
    flagged_at: float = field(default_factory=time.time)
    recommended_action: str = ""
    assessment_snapshot: UncertaintyAssessment | None = None


@dataclass
class UncertaintyMetrics:
    """Aggregate uncertainty statistics across all assessments."""
    total_assessments: int = 0
    avg_confidence: float = 0.0
    high_uncertainty_rate: float = 0.0  # Proportion with confidence < 0.5
    most_common_sources: list[tuple[UncertaintySource, int]] = field(default_factory=list)
    calibration_effectiveness: float = 0.0  # 0.0 to 1.0
    avg_hedging_density: float = 0.0
    total_flags: int = 0
    avg_factuality_score: float = 0.0
    avg_precision_score: float = 0.0
    assessment_velocity: float = 0.0  # Assessments per minute
    computed_at: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════
# Uncertainty Quantifier Engine
# ═══════════════════════════════════════════════════════════

class UncertaintyQuantifier:
    """Quantifies and manages uncertainty in agent-generated text.

    Performs multi-dimensional uncertainty assessment including hedging
    detection, confidence segmentation, calibration, alternative generation,
    risk profiling, and review flagging. Tracks patterns over time for
    continuous improvement of agent reliability.
    """

    def __init__(self):
        self._assessments: dict[str, UncertaintyAssessment] = {}
        self._calibrated: dict[str, CalibratedAssessment] = {}
        self._alternatives: dict[str, list[Alternative]] = {}
        self._risk_profiles: dict[str, RiskProfile] = {}
        self._review_flags: dict[str, list[ReviewFlag]] = {}
        self._calibration_history: list[tuple[float, float]] = []  # (raw, calibrated)
        self._source_counts: Counter[UncertaintySource] = Counter()
        self._first_assessment_time: float | None = None
        self._compiled_patterns: dict[str, list[tuple[re.Pattern, float]]] | None = None

    # ── Public API ──────────────────────────────────────────

    def assess(self, text: str, context: dict[str, Any] | None = None) -> UncertaintyAssessment:
        """Assess uncertainty in a given text.

        Analyzes the text for hedging language, uncertainty indicators,
        knowledge gaps, and other uncertainty sources. Segments the text
        and assigns per-segment confidence scores.

        Args:
            text: The text to assess for uncertainty.
            context: Optional context about the generation (domain, intent, etc.).

        Returns:
            An UncertaintyAssessment with confidence scores and uncertainty details.
        """
        if not text or not text.strip():
            return self._create_empty_assessment(text)

        assessment_id = f"ua-{uuid.uuid4().hex[:12]}"
        patterns = self._get_compiled_patterns()

        # Detect hedging phrases
        hedging_phrases, hedging_scores = self._detect_hedging(text, patterns)

        # Segment text into sentences
        segments = self._segment_text(text, hedging_phrases, hedging_scores)

        # Detect uncertainty sources
        sources = self._detect_uncertainty_sources(text, segments, patterns)

        # Compute overall confidence from segment scores
        raw_confidence = self._compute_overall_confidence(segments)

        # Compute factuality and precision scores
        factuality = self._compute_factuality_score(text, segments, hedging_phrases)
        precision = self._compute_precision_score(text, hedging_phrases)

        # Determine verification requirements
        requires_verification, verification_priority = self._determine_verification(
            raw_confidence, sources, segments, factuality
        )

        # Generate suggested caveats
        suggested_caveats = self._generate_caveats(sources, hedging_phrases, raw_confidence)

        # Build uncertainty segments
        uncertainty_segments = [
            UncertaintySegment(
                text=seg["text"],
                confidence=seg["confidence"],
                start_index=seg["start"],
                end_index=seg["end"],
                source=seg["source"],
                hedging_phrases=seg["hedging_phrases"],
            )
            for seg in segments
            if seg["confidence"] < 1.0 or seg["hedging_phrases"]
        ]

        assessment = UncertaintyAssessment(
            id=assessment_id,
            overall_confidence=raw_confidence,
            sources=sources,
            uncertainty_segments=uncertainty_segments,
            factuality_score=factuality,
            precision_score=precision,
            requires_verification=requires_verification,
            verification_priority=verification_priority,
            hedging_phrases_detected=list(set(hedging_phrases)),
            suggested_caveats=suggested_caveats,
            text_length=len(text),
            segment_count=len(segments),
            context=context or {},
        )

        self._assessments[assessment_id] = assessment
        for source in sources:
            self._source_counts[source] += 1
        if self._first_assessment_time is None:
            self._first_assessment_time = time.time()

        logger.debug(
            "Assessment %s: confidence=%.3f, sources=%s, hedging=%d, verification=%s",
            assessment_id,
            raw_confidence,
            [s.value for s in sources],
            len(hedging_phrases),
            verification_priority.value,
        )

        return assessment

    def calibrate_confidence(self, assessment_id: str) -> CalibratedAssessment | None:
        """Calibrate the confidence scores of an existing assessment.

        Applies multiple calibration methods including hedging density
        adjustment, segment variance analysis, and historical calibration
        to produce a more reliable confidence estimate.

        Args:
            assessment_id: The ID of the assessment to calibrate.

        Returns:
            A CalibratedAssessment, or None if the assessment is not found.
        """
        assessment = self._assessments.get(assessment_id)
        if assessment is None:
            logger.warning("Calibration requested for unknown assessment: %s", assessment_id)
            return None

        factors: list[CalibrationFactor] = []

        # Factor 1: Hedging density calibration
        hedging_adj = self._calibrate_hedging_density(assessment)
        if abs(hedging_adj) > 0.001:
            factors.append(CalibrationFactor(
                method=CalibrationMethod.HEDGING_DENSITY,
                description=f"Hedging density of {assessment.hedging_density:.3f} "
                            f"with {len(assessment.hedging_phrases_detected)} phrases detected",
                adjustment=hedging_adj,
                weight=0.40,
            ))

        # Factor 2: Segment variance calibration
        variance_adj = self._calibrate_segment_variance(assessment)
        if abs(variance_adj) > 0.001:
            factors.append(CalibrationFactor(
                method=CalibrationMethod.SEGMENT_VARIANCE,
                description=f"Confidence variance across {assessment.segment_count} segments",
                adjustment=variance_adj,
                weight=0.25,
            ))

        # Factor 3: Source weighting calibration
        source_adj = self._calibrate_source_weighting(assessment)
        if abs(source_adj) > 0.001:
            factors.append(CalibrationFactor(
                method=CalibrationMethod.SOURCE_WEIGHTING,
                description=f"Adjustment based on {len(assessment.sources)} uncertainty sources",
                adjustment=source_adj,
                weight=0.20,
            ))

        # Factor 4: Historical calibration
        historical_adj = self._calibrate_historical(assessment)
        if abs(historical_adj) > 0.001:
            factors.append(CalibrationFactor(
                method=CalibrationMethod.HISTORICAL_ADJUSTMENT,
                description=f"Historical calibration from {len(self._calibration_history)} prior assessments",
                adjustment=historical_adj,
                weight=0.15,
            ))

        # Compute calibrated confidence
        total_weight = sum(f.weight for f in factors)
        if total_weight > 0:
            weighted_adjustment = sum(f.adjustment * f.weight for f in factors) / total_weight
        else:
            weighted_adjustment = 0.0

        calibrated_confidence = max(0.0, min(1.0, assessment.overall_confidence + weighted_adjustment))

        # Compute reliability score
        reliability_score = self._compute_reliability_score(assessment, factors, calibrated_confidence)

        # Build method description
        method_names = [f.method.value for f in factors]
        method_desc = f"composite:{'+'.join(method_names)}" if method_names else "passthrough"

        calibrated = CalibratedAssessment(
            original_assessment=assessment,
            calibrated_confidence=round(calibrated_confidence, 4),
            calibration_method=method_desc,
            calibration_factors=factors,
            reliability_score=round(reliability_score, 4),
        )

        self._calibrated[assessment_id] = calibrated
        self._calibration_history.append((assessment.overall_confidence, calibrated_confidence))

        logger.info(
            "Calibrated %s: %.3f -> %.3f (shift=%.3f, reliability=%.3f)",
            assessment_id,
            assessment.overall_confidence,
            calibrated_confidence,
            calibrated.confidence_shift,
            reliability_score,
        )

        return calibrated

    def generate_alternatives(
        self, assessment_id: str, count: int = 3
    ) -> list[Alternative]:
        """Generate alternative interpretations for an uncertain assessment.

        Creates alternative versions of the text with different confidence
        levels and probability weights, based on the uncertainty sources
        and segments identified in the assessment.

        Args:
            assessment_id: The ID of the assessment to generate alternatives for.
            count: Maximum number of alternatives to generate.

        Returns:
            A list of Alternative objects with varied interpretations.
        """
        assessment = self._assessments.get(assessment_id)
        if assessment is None:
            logger.warning("Alternatives requested for unknown assessment: %s", assessment_id)
            return []

        alternatives: list[Alternative] = []

        uncertainty_segments = assessment.uncertainty_segments
        if not uncertainty_segments:
            # No uncertain segments; generate a single high-confidence alternative
            alt = Alternative(
                id=f"alt-{uuid.uuid4().hex[:8]}",
                text="[Confirmed interpretation]",
                confidence=assessment.overall_confidence,
                probability=1.0,
                rationale="No uncertainty segments detected; interpretation is consistent.",
            )
            alternatives.append(alt)
            self._store_alternatives(assessment_id, alternatives)
            return alternatives

        # Generate alternatives based on uncertainty sources
        source_alternatives = self._generate_source_based_alternatives(
            assessment, uncertainty_segments, count
        )
        alternatives.extend(source_alternatives)

        # If we still need more alternatives, generate variance-based ones
        if len(alternatives) < count:
            variance_alternatives = self._generate_variance_alternatives(
                assessment, uncertainty_segments, count - len(alternatives)
            )
            alternatives.extend(variance_alternatives)

        # Normalize probabilities
        total_prob = sum(a.probability for a in alternatives)
        if total_prob > 0:
            for alt in alternatives:
                alt.probability = round(alt.probability / total_prob, 4)

        # Limit to requested count
        alternatives = alternatives[:count]

        self._store_alternatives(assessment_id, alternatives)
        return alternatives

    def create_risk_profile(self, query: str) -> RiskProfile:
        """Assess the risks associated with a query.

        Analyzes the query for high-risk domain terms, ethical concerns,
        bias indicators, and content warnings to produce a risk profile.

        Args:
            query: The query text to analyze for risks.

        Returns:
            A RiskProfile with risk level, factors, and mitigation suggestions.
        """
        query_lower = query.lower()
        risk_factors: list[str] = []
        content_warnings: list[str] = []
        ethical_concerns: list[str] = []
        bias_indicators: list[str] = []
        risk_score = 0.0

        # Check for high-risk domain terms
        matched_risk_terms = []
        for term in HIGH_RISK_TERMS:
            if term in query_lower:
                matched_risk_terms.append(term)
        if matched_risk_terms:
            risk_factors.append(f"High-risk domain terms detected: {', '.join(matched_risk_terms)}")
            risk_score += min(len(matched_risk_terms) * 0.15, 0.5)
            content_warnings.append(
                f"This query involves potentially sensitive domains: {', '.join(matched_risk_terms[:3])}"
            )

        # Check for ethical concerns
        matched_ethical = []
        for term in ETHICAL_CONCERN_TERMS:
            if term in query_lower:
                matched_ethical.append(term)
        if matched_ethical:
            ethical_concerns.append(f"Ethically sensitive terms: {', '.join(matched_ethical)}")
            risk_score += min(len(matched_ethical) * 0.2, 0.6)

        # Check for bias indicators
        matched_bias = []
        for term in BIAS_INDICATORS:
            pattern = re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE)
            if pattern.search(query):
                matched_bias.append(term)
        if matched_bias:
            bias_indicators.append(f"Absolutist language detected: {', '.join(matched_bias)}")
            risk_score += min(len(matched_bias) * 0.1, 0.3)

        # Determine risk level
        risk_level = self._classify_risk_level(risk_score)

        # Determine if safe handling is required
        safe_handling = risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

        # Generate mitigation suggestions
        mitigation = self._generate_mitigation_suggestions(
            risk_level, matched_risk_terms, matched_ethical, matched_bias
        )

        profile = RiskProfile(
            risk_level=risk_level,
            risk_factors=risk_factors,
            mitigation_suggestions=mitigation,
            safe_handling_required=safe_handling,
            content_warnings=content_warnings,
            ethical_concerns=ethical_concerns,
            bias_indicators=bias_indicators,
            domain_risk_score=round(risk_score, 4),
        )

        self._risk_profiles[query] = profile

        logger.info(
            "Risk profile created: level=%s, score=%.3f, factors=%d",
            risk_level.value, risk_score, len(risk_factors),
        )

        return profile

    def get_uncertainty_metrics(self) -> UncertaintyMetrics:
        """Compute aggregate uncertainty statistics across all assessments.

        Returns:
            An UncertaintyMetrics object with comprehensive statistics.
        """
        total = len(self._assessments)
        if total == 0:
            return UncertaintyMetrics()

        confidences = [a.overall_confidence for a in self._assessments.values()]
        avg_conf = sum(confidences) / total
        high_uncertainty = sum(1 for c in confidences if c < 0.5) / total

        # Most common sources
        most_common = self._source_counts.most_common(5)

        # Calibration effectiveness
        cal_effectiveness = self._compute_calibration_effectiveness()

        # Average hedging density
        avg_hedging = (
            sum(a.hedging_density for a in self._assessments.values()) / total
            if total > 0 else 0.0
        )

        # Total flags
        total_flags = sum(len(flags) for flags in self._review_flags.values())

        # Average factuality and precision
        avg_factuality = (
            sum(a.factuality_score for a in self._assessments.values()) / total
            if total > 0 else 0.0
        )
        avg_precision = (
            sum(a.precision_score for a in self._assessments.values()) / total
            if total > 0 else 0.0
        )

        # Assessment velocity
        if self._first_assessment_time is not None:
            elapsed = time.time() - self._first_assessment_time
            velocity = (total / (elapsed / 60)) if elapsed > 0 else 0.0
        else:
            velocity = 0.0

        return UncertaintyMetrics(
            total_assessments=total,
            avg_confidence=round(avg_conf, 4),
            high_uncertainty_rate=round(high_uncertainty, 4),
            most_common_sources=[(s, c) for s, c in most_common],
            calibration_effectiveness=round(cal_effectiveness, 4),
            avg_hedging_density=round(avg_hedging, 4),
            total_flags=total_flags,
            avg_factuality_score=round(avg_factuality, 4),
            avg_precision_score=round(avg_precision, 4),
            assessment_velocity=round(velocity, 4),
        )

    def flag_for_review(self, assessment_id: str) -> ReviewFlag | None:
        """Flag a high-uncertainty assessment for human review.

        Creates a review flag with priority and recommended actions based
        on the assessment's uncertainty level and sources.

        Args:
            assessment_id: The ID of the assessment to flag.

        Returns:
            A ReviewFlag, or None if the assessment is not found.
        """
        assessment = self._assessments.get(assessment_id)
        if assessment is None:
            logger.warning("Review flag requested for unknown assessment: %s", assessment_id)
            return None

        # Determine flag reason and priority
        reason_parts = []
        priority = assessment.verification_priority

        if assessment.overall_confidence < 0.3:
            reason_parts.append("critically low confidence")
            priority = max(priority, VerificationPriority.CRITICAL, key=self._priority_rank)
        elif assessment.overall_confidence < 0.5:
            reason_parts.append("low confidence")
            priority = max(priority, VerificationPriority.HIGH, key=self._priority_rank)
        elif assessment.overall_confidence < 0.7:
            reason_parts.append("moderate uncertainty")
            priority = max(priority, VerificationPriority.MEDIUM, key=self._priority_rank)

        if assessment.hedging_phrases_detected:
            reason_parts.append(
                f"{len(assessment.hedging_phrases_detected)} hedging phrases detected"
            )

        if assessment.sources:
            source_names = [s.value for s in assessment.sources]
            reason_parts.append(f"sources: {', '.join(source_names[:3])}")

        if assessment.factuality_score < 0.5:
            reason_parts.append(f"low factuality score ({assessment.factuality_score:.2f})")

        reason = "; ".join(reason_parts) if reason_parts else "flagged for review"

        # Generate recommended action
        recommended_action = self._generate_recommended_action(assessment, priority)

        flag = ReviewFlag(
            flag_id=f"rf-{uuid.uuid4().hex[:12]}",
            assessment_id=assessment_id,
            reason=reason,
            priority=priority,
            recommended_action=recommended_action,
            assessment_snapshot=assessment,
        )

        if assessment_id not in self._review_flags:
            self._review_flags[assessment_id] = []
        self._review_flags[assessment_id].append(flag)

        logger.warning(
            "Review flag created: %s (priority=%s, assessment=%s)",
            flag.flag_id, priority.value, assessment_id,
        )

        return flag

    def reset(self) -> None:
        """Clear all state including assessments, calibrations, and history."""
        self._assessments.clear()
        self._calibrated.clear()
        self._alternatives.clear()
        self._risk_profiles.clear()
        self._review_flags.clear()
        self._calibration_history.clear()
        self._source_counts.clear()
        self._first_assessment_time = None
        logger.info("UncertaintyQuantifier state reset")

    # ── Internal: Hedging Detection ─────────────────────────

    def _get_compiled_patterns(self) -> dict[str, list[tuple[re.Pattern, float]]]:
        """Compile regex patterns once and cache them."""
        if self._compiled_patterns is not None:
            return self._compiled_patterns

        self._compiled_patterns = {
            "hedging": [(re.compile(p, re.IGNORECASE), w) for p, w in HEDGING_PATTERNS],
            "contradiction": [(re.compile(p, re.IGNORECASE), 0.0) for p in CONTRADICTION_PATTERNS],
            "knowledge_gap": [(re.compile(p, re.IGNORECASE), 0.0) for p in KNOWLEDGE_GAP_PATTERNS],
        }
        return self._compiled_patterns

    def _detect_hedging(
        self, text: str, patterns: dict[str, list[tuple[re.Pattern, float]]]
    ) -> tuple[list[str], dict[int, float]]:
        """Detect hedging phrases and their positions with scores."""
        hedging_phrases: list[str] = []
        position_scores: dict[int, float] = {}

        for pattern, weight in patterns["hedging"]:
            for match in pattern.finditer(text):
                phrase = match.group(0)
                hedging_phrases.append(phrase)
                # Record position-based score
                pos = match.start()
                if pos not in position_scores or weight > position_scores[pos]:
                    position_scores[pos] = weight

        return hedging_phrases, position_scores

    # ── Internal: Text Segmentation ─────────────────────────

    def _segment_text(
        self,
        text: str,
        hedging_phrases: list[str],
        hedging_scores: dict[int, float],
    ) -> list[dict[str, Any]]:
        """Split text into sentences and assign per-segment confidence."""
        # Split into sentences using regex
        sentence_pattern = re.compile(r'(?<=[.!?])\s+')
        raw_sentences = sentence_pattern.split(text)

        segments: list[dict[str, Any]] = []
        current_pos = 0

        for sentence in raw_sentences:
            if not sentence.strip():
                continue

            start = text.find(sentence, current_pos) if sentence in text[current_pos:] else current_pos
            if start == -1:
                start = current_pos
            end = start + len(sentence)
            current_pos = end

            # Compute segment confidence
            confidence = self._compute_segment_confidence(
                sentence, hedging_phrases, hedging_scores, start, end
            )

            # Determine uncertainty source for this segment
            source = self._determine_segment_source(sentence)

            # Find hedging phrases within this segment
            seg_hedging = [
                h for h in hedging_phrases
                if h.lower() in sentence.lower()
            ]

            segments.append({
                "text": sentence,
                "confidence": confidence,
                "start": start,
                "end": end,
                "source": source,
                "hedging_phrases": seg_hedging,
            })

        # If no segments were created (empty or single sentence), create one
        if not segments and text.strip():
            segments.append({
                "text": text,
                "confidence": 1.0,
                "start": 0,
                "end": len(text),
                "source": UncertaintySource.AMBIGUITY,
                "hedging_phrases": [],
            })

        return segments

    def _compute_segment_confidence(
        self,
        sentence: str,
        hedging_phrases: list[str],
        hedging_scores: dict[int, float],
        seg_start: int,
        seg_end: int,
    ) -> float:
        """Compute confidence for a single text segment."""
        sentence_lower = sentence.lower()

        # Start at 1.0 and reduce based on hedging
        confidence = 1.0

        # Count hedging phrases in this segment
        hedge_count = 0
        for phrase in hedging_phrases:
            if phrase.lower() in sentence_lower:
                hedge_count += 1

        # Apply hedging penalties
        if hedge_count > 0:
            # More hedges = lower confidence, but with diminishing returns
            hedge_penalty = min(hedge_count * 0.12, 0.60)
            confidence -= hedge_penalty

        # Check for position-based hedging scores within this segment
        for pos, score in hedging_scores.items():
            if seg_start <= pos < seg_end:
                # Stronger hedges reduce confidence more
                confidence -= score * 0.5

        # Check for low-confidence modifiers
        for modifier in LOW_CONFIDENCE_MODIFIERS:
            if modifier in sentence_lower:
                confidence -= 0.05

        # Apply contradiction penalty
        for pattern, _ in self._get_compiled_patterns()["contradiction"]:
            if pattern.search(sentence):
                confidence -= 0.15
                break

        # Apply knowledge gap penalty
        for pattern, _ in self._get_compiled_patterns()["knowledge_gap"]:
            if pattern.search(sentence):
                confidence -= 0.20
                break

        # Clamp to valid range
        return max(0.0, min(1.0, round(confidence, 4)))

    # ── Internal: Source Detection ──────────────────────────

    def _detect_uncertainty_sources(
        self,
        text: str,
        segments: list[dict[str, Any]],
        patterns: dict[str, list[tuple[re.Pattern, float]]],
    ) -> list[UncertaintySource]:
        """Detect all uncertainty sources in the text."""
        sources: list[UncertaintySource] = []
        text_lower = text.lower()

        # Check for knowledge gaps
        for pattern, _ in patterns["knowledge_gap"]:
            if pattern.search(text):
                if UncertaintySource.KNOWLEDGE_GAP not in sources:
                    sources.append(UncertaintySource.KNOWLEDGE_GAP)
                break

        # Check for contradictions
        for pattern, _ in patterns["contradiction"]:
            if pattern.search(text):
                if UncertaintySource.CONTRADICTION not in sources:
                    sources.append(UncertaintySource.CONTRADICTION)
                break

        # Check for ambiguity (multiple uncertain segments)
        uncertain_count = sum(1 for s in segments if s["confidence"] < 0.7)
        if uncertain_count >= 2:
            if UncertaintySource.AMBIGUITY not in sources:
                sources.append(UncertaintySource.AMBIGUITY)

        # Check for incomplete information
        if any(s["confidence"] < 0.3 for s in segments):
            if UncertaintySource.INCOMPLETE_INFO not in sources:
                sources.append(UncertaintySource.INCOMPLETE_INFO)

        # Check for speculation
        speculation_indicators = ["might", "could", "possibly", "perhaps", "speculate"]
        if any(ind in text_lower for ind in speculation_indicators):
            if any(s["confidence"] < 0.6 for s in segments):
                if UncertaintySource.SPECULATION not in sources:
                    sources.append(UncertaintySource.SPECULATION)

        # Check for extrapolation (going beyond known data)
        extrapolation_indicators = [
            "extrapolate", "project forward", "based on trends",
            "if this continues", "predict", "forecast", "estimate",
        ]
        if any(ind in text_lower for ind in extrapolation_indicators):
            if UncertaintySource.EXTRAPOLATION not in sources:
                sources.append(UncertaintySource.EXTRAPOLATION)

        # Check for low-confidence source indicators
        low_conf_indicators = [
            "according to", "reportedly", "allegedly", "sources say",
            "unverified", "unconfirmed", "rumor",
        ]
        if any(ind in text_lower for ind in low_conf_indicators):
            if UncertaintySource.LOW_CONFIDENCE_SOURCE not in sources:
                sources.append(UncertaintySource.LOW_CONFIDENCE_SOURCE)

        # Always add model limitation if overall confidence is very low
        avg_confidence = sum(s["confidence"] for s in segments) / max(len(segments), 1)
        if avg_confidence < 0.4:
            if UncertaintySource.MODEL_LIMITATION not in sources:
                sources.append(UncertaintySource.MODEL_LIMITATION)

        # If no specific sources found but confidence is not perfect
        if not sources and avg_confidence < 0.9:
            sources.append(UncertaintySource.AMBIGUITY)

        return sources

    def _determine_segment_source(self, sentence: str) -> UncertaintySource:
        """Determine the primary uncertainty source for a segment."""
        sentence_lower = sentence.lower()
        patterns = self._get_compiled_patterns()

        for pattern, _ in patterns["knowledge_gap"]:
            if pattern.search(sentence):
                return UncertaintySource.KNOWLEDGE_GAP

        for pattern, _ in patterns["contradiction"]:
            if pattern.search(sentence):
                return UncertaintySource.CONTRADICTION

        spec_indicators = ["might", "could", "possibly", "perhaps", "speculate", "guess"]
        if any(ind in sentence_lower for ind in spec_indicators):
            return UncertaintySource.SPECULATION

        extrap_indicators = ["extrapolate", "predict", "forecast", "project", "trend"]
        if any(ind in sentence_lower for ind in extrap_indicators):
            return UncertaintySource.EXTRAPOLATION

        low_src = ["according to", "reportedly", "allegedly", "unverified"]
        if any(ind in sentence_lower for ind in low_src):
            return UncertaintySource.LOW_CONFIDENCE_SOURCE

        return UncertaintySource.AMBIGUITY

    # ── Internal: Confidence Computation ────────────────────

    def _compute_overall_confidence(self, segments: list[dict[str, Any]]) -> float:
        """Compute overall confidence as weighted average of segment scores."""
        if not segments:
            return 0.0

        total_len = sum(len(s["text"]) for s in segments)
        if total_len == 0:
            return 0.0

        weighted_sum = sum(
            s["confidence"] * len(s["text"]) for s in segments
        )
        return round(weighted_sum / total_len, 4)

    def _compute_factuality_score(
        self,
        text: str,
        segments: list[dict[str, Any]],
        hedging_phrases: list[str],
    ) -> float:
        """Estimate a factuality score based on hedging and segment patterns."""
        if not segments:
            return 1.0

        base_score = 1.0

        # Hedging reduces factuality
        if len(hedging_phrases) > 0:
            hedge_ratio = len(hedging_phrases) / max(len(text.split()), 1)
            base_score -= min(hedge_ratio * 5, 0.5)

        # High-confidence segments boost factuality
        high_conf_count = sum(1 for s in segments if s["confidence"] > 0.8)
        if len(segments) > 0:
            high_conf_ratio = high_conf_count / len(segments)
            base_score = base_score * 0.6 + high_conf_ratio * 0.4

        return max(0.0, min(1.0, round(base_score, 4)))

    def _compute_precision_score(
        self, text: str, hedging_phrases: list[str]
    ) -> float:
        """Estimate a precision score based on specificity of language."""
        if not text.strip():
            return 1.0

        text_lower = text.lower()
        score = 1.0

        # Vague quantifiers reduce precision
        vague_quantifiers = [
            "some", "many", "several", "a few", "a lot", "various",
            "numerous", "a number of", "a couple of", "multiple",
            "around", "about", "approximately", "roughly",
        ]
        for vq in vague_quantifiers:
            count = len(re.findall(rf'\b{re.escape(vq)}\b', text_lower))
            if count > 0:
                score -= min(count * 0.03, 0.3)

        # Hedging density reduces precision
        if len(text.split()) > 0:
            hedge_density = len(hedging_phrases) / len(text.split())
            score -= min(hedge_density * 3, 0.4)

        return max(0.0, min(1.0, round(score, 4)))

    # ── Internal: Verification ──────────────────────────────

    def _determine_verification(
        self,
        confidence: float,
        sources: list[UncertaintySource],
        segments: list[dict[str, Any]],
        factuality: float,
    ) -> tuple[bool, VerificationPriority]:
        """Determine if verification is required and at what priority."""
        requires_verification = False
        priority = VerificationPriority.LOW

        # Low confidence triggers verification
        if confidence < 0.7:
            requires_verification = True
            if confidence < 0.3:
                priority = VerificationPriority.CRITICAL
            elif confidence < 0.5:
                priority = VerificationPriority.HIGH
            else:
                priority = VerificationPriority.MEDIUM

        # Critical sources trigger verification
        critical_sources = {
            UncertaintySource.KNOWLEDGE_GAP,
            UncertaintySource.CONTRADICTION,
            UncertaintySource.MODEL_LIMITATION,
        }
        if any(s in critical_sources for s in sources):
            requires_verification = True
            priority = max(priority, VerificationPriority.HIGH, key=self._priority_rank)

        # Low factuality triggers verification
        if factuality < 0.5:
            requires_verification = True
            priority = max(priority, VerificationPriority.HIGH, key=self._priority_rank)

        # Many uncertain segments trigger verification
        uncertain_ratio = sum(1 for s in segments if s["confidence"] < 0.6) / max(len(segments), 1)
        if uncertain_ratio > 0.5:
            requires_verification = True
            priority = max(priority, VerificationPriority.MEDIUM, key=self._priority_rank)

        return requires_verification, priority

    def _priority_rank(self, priority: VerificationPriority) -> int:
        """Return numeric rank for priority comparison."""
        return {
            VerificationPriority.LOW: 0,
            VerificationPriority.MEDIUM: 1,
            VerificationPriority.HIGH: 2,
            VerificationPriority.CRITICAL: 3,
        }[priority]

    # ── Internal: Caveats ──────────────────────────────────

    def _generate_caveats(
        self,
        sources: list[UncertaintySource],
        hedging_phrases: list[str],
        confidence: float,
    ) -> list[str]:
        """Generate suggested caveats based on uncertainty analysis."""
        caveats: list[str] = []

        if UncertaintySource.KNOWLEDGE_GAP in sources:
            caveats.append(
                "This response may be incomplete due to knowledge gaps; "
                "consider consulting additional authoritative sources."
            )

        if UncertaintySource.CONTRADICTION in sources:
            caveats.append(
                "Potential contradictions detected in this response; "
                "cross-reference individual claims before relying on them."
            )

        if UncertaintySource.SPECULATION in sources:
            caveats.append(
                "Portions of this response are speculative; "
                "treat conclusions as hypotheses rather than established facts."
            )

        if UncertaintySource.EXTRAPOLATION in sources:
            caveats.append(
                "This response includes extrapolations beyond known data; "
                "projections may not account for all variables."
            )

        if UncertaintySource.LOW_CONFIDENCE_SOURCE in sources:
            caveats.append(
                "Some information may come from low-confidence sources; "
                "verify key claims independently."
            )

        if UncertaintySource.MODEL_LIMITATION in sources:
            caveats.append(
                "This response may be affected by inherent model limitations; "
                "apply human judgment for critical decisions."
            )

        if len(hedging_phrases) > 5:
            caveats.append(
                f"High hedging density detected ({len(hedging_phrases)} phrases); "
                "the response expresses significant uncertainty."
            )

        if confidence < 0.5:
            caveats.append(
                "Overall confidence is low; this response should be treated "
                "as a preliminary assessment only."
            )

        if not caveats and confidence < 0.8:
            caveats.append(
                "Moderate uncertainty present; consider validating key points."
            )

        return caveats

    # ── Internal: Calibration ───────────────────────────────

    def _calibrate_hedging_density(self, assessment: UncertaintyAssessment) -> float:
        """Calibrate based on the density of hedging phrases."""
        density = assessment.hedging_density
        if density < 0.02:
            return 0.0
        # Higher density = more downward adjustment
        adjustment = -min(density * 0.8, 0.35)
        return round(adjustment, 4)

    def _calibrate_segment_variance(self, assessment: UncertaintyAssessment) -> float:
        """Calibrate based on variance in per-segment confidence."""
        segments = assessment.uncertainty_segments
        if not segments:
            return 0.0

        confidence_values = [s.confidence for s in segments]
        if len(confidence_values) < 2:
            return 0.0

        mean = sum(confidence_values) / len(confidence_values)
        variance = sum((c - mean) ** 2 for c in confidence_values) / len(confidence_values)
        std_dev = math.sqrt(variance)

        # High variance = the assessment is inconsistent, reduce confidence
        if std_dev > 0.3:
            return -0.15
        elif std_dev > 0.2:
            return -0.10
        elif std_dev > 0.1:
            return -0.05
        return 0.0

    def _calibrate_source_weighting(self, assessment: UncertaintyAssessment) -> float:
        """Calibrate based on the types and number of uncertainty sources."""
        source_weights = {
            UncertaintySource.KNOWLEDGE_GAP: -0.12,
            UncertaintySource.CONTRADICTION: -0.10,
            UncertaintySource.MODEL_LIMITATION: -0.10,
            UncertaintySource.INCOMPLETE_INFO: -0.08,
            UncertaintySource.SPECULATION: -0.06,
            UncertaintySource.EXTRAPOLATION: -0.05,
            UncertaintySource.LOW_CONFIDENCE_SOURCE: -0.04,
            UncertaintySource.AMBIGUITY: -0.03,
        }

        total_adjustment = sum(
            source_weights.get(s, 0.0) for s in assessment.sources
        )
        return max(-0.30, round(total_adjustment, 4))

    def _calibrate_historical(self, assessment: UncertaintyAssessment) -> float:
        """Calibrate based on historical calibration patterns."""
        if len(self._calibration_history) < 3:
            return 0.0

        # Average historical shift
        avg_shift = sum(cal - raw for raw, cal in self._calibration_history) / len(
            self._calibration_history
        )

        # Apply a fraction of the historical bias
        return round(avg_shift * 0.3, 4)

    def _compute_reliability_score(
        self,
        assessment: UncertaintyAssessment,
        factors: list[CalibrationFactor],
        calibrated_confidence: float,
    ) -> float:
        """Compute how reliable the calibration is."""
        if not factors:
            return 1.0

        score = 1.0

        # More factors = potentially less reliable
        if len(factors) > 3:
            score -= 0.05

        # Large adjustments reduce reliability
        shift = abs(calibrated_confidence - assessment.overall_confidence)
        if shift > 0.3:
            score -= 0.15
        elif shift > 0.2:
            score -= 0.10
        elif shift > 0.1:
            score -= 0.05

        # Few calibration history points reduce reliability
        if len(self._calibration_history) < 5:
            score -= 0.10

        # High segment variance reduces reliability
        if assessment.uncertainty_segments:
            conf_values = [s.confidence for s in assessment.uncertainty_segments]
            if len(conf_values) > 1:
                mean = sum(conf_values) / len(conf_values)
                variance = sum((c - mean) ** 2 for c in conf_values) / len(conf_values)
                if variance > 0.15:
                    score -= 0.10

        return max(0.0, min(1.0, round(score, 4)))

    # ── Internal: Alternatives ──────────────────────────────

    def _generate_source_based_alternatives(
        self,
        assessment: UncertaintyAssessment,
        uncertainty_segments: list[UncertaintySegment],
        count: int,
    ) -> list[Alternative]:
        """Generate alternatives based on detected uncertainty sources."""
        alternatives: list[Alternative] = []

        source_map: dict[UncertaintySource, list[UncertaintySegment]] = defaultdict(list)
        for seg in uncertainty_segments:
            source_map[seg.source].append(seg)

        gen_count = 0

        for source, segments in source_map.items():
            if gen_count >= count:
                break

            affected_text = " ".join(s.text for s in segments[:3])

            alt_id = f"alt-{uuid.uuid4().hex[:8]}"

            if source == UncertaintySource.KNOWLEDGE_GAP:
                alt = Alternative(
                    id=alt_id,
                    text=f"[Refined: {affected_text[:80]}...]",
                    confidence=assessment.overall_confidence + 0.10,
                    probability=0.25,
                    rationale="Knowledge gap addressed by narrowing scope to confirmed information.",
                )
            elif source == UncertaintySource.CONTRADICTION:
                alt = Alternative(
                    id=alt_id,
                    text=f"[Resolved: {affected_text[:80]}...]",
                    confidence=assessment.overall_confidence + 0.08,
                    probability=0.20,
                    rationale="Contradiction resolved by selecting the most consistent interpretation.",
                )
            elif source == UncertaintySource.SPECULATION:
                alt = Alternative(
                    id=alt_id,
                    text=f"[Conservative: {affected_text[:80]}...]",
                    confidence=assessment.overall_confidence + 0.05,
                    probability=0.30,
                    rationale="Speculation removed; only well-supported claims retained.",
                )
            elif source == UncertaintySource.EXTRAPOLATION:
                alt = Alternative(
                    id=alt_id,
                    text=f"[Bounded: {affected_text[:80]}...]",
                    confidence=assessment.overall_confidence + 0.06,
                    probability=0.22,
                    rationale="Extrapolation bounded to the range supported by available data.",
                )
            elif source == UncertaintySource.LOW_CONFIDENCE_SOURCE:
                alt = Alternative(
                    id=alt_id,
                    text=f"[Verified: {affected_text[:80]}...]",
                    confidence=assessment.overall_confidence + 0.12,
                    probability=0.18,
                    rationale="Low-confidence sources replaced with more reliable references.",
                )
            elif source == UncertaintySource.MODEL_LIMITATION:
                alt = Alternative(
                    id=alt_id,
                    text=f"[Constrained: {affected_text[:80]}...]",
                    confidence=assessment.overall_confidence + 0.04,
                    probability=0.18,
                    rationale="Response constrained to model's known capability boundaries.",
                )
            else:
                alt = Alternative(
                    id=alt_id,
                    text=f"[Clarified: {affected_text[:80]}...]",
                    confidence=assessment.overall_confidence + 0.07,
                    probability=0.25,
                    rationale="Ambiguity reduced through clearer, more precise language.",
                )

            alt.confidence = min(1.0, round(alt.confidence, 4))
            alternatives.append(alt)
            gen_count += 1

        return alternatives

    def _generate_variance_alternatives(
        self,
        assessment: UncertaintyAssessment,
        uncertainty_segments: list[UncertaintySegment],
        remaining: int,
    ) -> list[Alternative]:
        """Generate alternatives based on confidence variance."""
        alternatives: list[Alternative] = []

        if not uncertainty_segments:
            return alternatives

        # Sort by confidence
        sorted_segs = sorted(uncertainty_segments, key=lambda s: s.confidence)

        # Generate a pessimistic alternative
        if remaining > 0 and sorted_segs:
            lowest = sorted_segs[0]
            alt = Alternative(
                id=f"alt-{uuid.uuid4().hex[:8]}",
                text=f"[Pessimistic view on: {lowest.text[:80]}...]",
                confidence=assessment.overall_confidence - 0.15,
                probability=0.15,
                rationale="Worst-case interpretation assuming lowest-confidence segments are incorrect.",
            )
            alt.confidence = max(0.0, round(alt.confidence, 4))
            alternatives.append(alt)
            remaining -= 1

        # Generate an optimistic alternative
        if remaining > 0 and sorted_segs:
            highest = sorted_segs[-1]
            alt = Alternative(
                id=f"alt-{uuid.uuid4().hex[:8]}",
                text=f"[Optimistic view on: {highest.text[:80]}...]",
                confidence=assessment.overall_confidence + 0.10,
                probability=0.20,
                rationale="Best-case interpretation assuming highest-confidence segments are correct.",
            )
            alt.confidence = min(1.0, round(alt.confidence, 4))
            alternatives.append(alt)
            remaining -= 1

        # Generate a balanced alternative
        if remaining > 0 and len(sorted_segs) >= 2:
            mid = sorted_segs[len(sorted_segs) // 2]
            alt = Alternative(
                id=f"alt-{uuid.uuid4().hex[:8]}",
                text=f"[Balanced view on: {mid.text[:80]}...]",
                confidence=assessment.overall_confidence,
                probability=0.25,
                rationale="Balanced interpretation using median-confidence segments as anchor.",
            )
            alternatives.append(alt)

        return alternatives

    def _store_alternatives(
        self, assessment_id: str, alternatives: list[Alternative]
    ) -> None:
        """Store generated alternatives for later retrieval."""
        self._alternatives[assessment_id] = alternatives

    # ── Internal: Risk Profiling ────────────────────────────

    def _classify_risk_level(self, risk_score: float) -> RiskLevel:
        """Classify risk score into a risk level."""
        if risk_score >= 0.7:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.5:
            return RiskLevel.HIGH
        elif risk_score >= 0.25:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _generate_mitigation_suggestions(
        self,
        risk_level: RiskLevel,
        risk_terms: list[str],
        ethical_terms: list[str],
        bias_terms: list[str],
    ) -> list[str]:
        """Generate mitigation suggestions based on risk factors."""
        suggestions: list[str] = []

        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            suggestions.append(
                "Human review is strongly recommended before acting on the response."
            )
            suggestions.append(
                "Include explicit disclaimers about the limitations of AI-generated content."
            )

        if risk_terms:
            suggestions.append(
                "Verify any domain-specific claims against authoritative sources "
                "before taking action."
            )

        if ethical_terms:
            suggestions.append(
                "Review the response for ethical compliance and ensure it aligns "
                "with organizational values and policies."
            )

        if bias_terms:
            suggestions.append(
                "Check for potential bias in the response and consider whether "
                "alternative perspectives should be presented."
            )

        if risk_level == RiskLevel.MEDIUM:
            suggestions.append(
                "Consider a light review of the response for accuracy and completeness."
            )

        if not suggestions:
            suggestions.append("Standard quality checks are sufficient for this query.")

        return suggestions

    # ── Internal: Review Flags ──────────────────────────────

    def _generate_recommended_action(
        self,
        assessment: UncertaintyAssessment,
        priority: VerificationPriority,
    ) -> str:
        """Generate recommended action for a review flag."""
        if priority == VerificationPriority.CRITICAL:
            return (
                "Immediate human review required. Do not use this output "
                "without expert verification. Consider re-querying with "
                "more specific constraints."
            )
        elif priority == VerificationPriority.HIGH:
            return (
                "Human review recommended before use. Cross-reference key "
                "claims and consider providing additional context to the "
                "model for improved confidence."
            )
        elif priority == VerificationPriority.MEDIUM:
            return (
                "Light review suggested. Verify the most uncertain claims "
                "and consider whether the overall response meets quality "
                "expectations."
            )
        else:
            return "Standard review. The output is generally reliable but may benefit from spot-checking."

    # ── Internal: Metrics ───────────────────────────────────

    def _compute_calibration_effectiveness(self) -> float:
        """Compute how effective calibration has been historically."""
        if len(self._calibration_history) < 3:
            return 0.5  # Neutral default

        # Measure how much calibration reduces the spread of confidence scores
        raw_confidences = [raw for raw, _ in self._calibration_history]
        cal_confidences = [cal for _, cal in self._calibration_history]

        raw_mean = sum(raw_confidences) / len(raw_confidences)
        cal_mean = sum(cal_confidences) / len(cal_confidences)

        # Ideal calibration: confidence scores should reflect actual reliability
        # Effectiveness is measured by how well calibrated scores distribute
        # around the expected value (less extreme values)
        raw_variance = sum((c - raw_mean) ** 2 for c in raw_confidences) / len(raw_confidences)
        cal_variance = sum((c - cal_mean) ** 2 for c in cal_confidences) / len(cal_confidences)

        if raw_variance > 0:
            # Reduction in variance = better calibration
            variance_reduction = max(0.0, (raw_variance - cal_variance) / raw_variance)
            return min(1.0, round(variance_reduction, 4))

        return 0.5

    def _create_empty_assessment(self, text: str) -> UncertaintyAssessment:
        """Create an assessment for empty or whitespace-only text."""
        return UncertaintyAssessment(
            id=f"ua-{uuid.uuid4().hex[:12]}",
            overall_confidence=1.0,
            sources=[],
            text_length=len(text),
        )


# ═══════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════

_uncertainty_quantifier: UncertaintyQuantifier | None = None


def get_uncertainty_quantifier() -> UncertaintyQuantifier:
    """Get or create the global UncertaintyQuantifier singleton instance."""
    global _uncertainty_quantifier
    if _uncertainty_quantifier is None:
        _uncertainty_quantifier = UncertaintyQuantifier()
        logger.info("Global UncertaintyQuantifier singleton created")
    return _uncertainty_quantifier


def reset_uncertainty_quantifier() -> None:
    """Reset the global UncertaintyQuantifier singleton instance."""
    global _uncertainty_quantifier
    if _uncertainty_quantifier is not None:
        _uncertainty_quantifier.reset()
    _uncertainty_quantifier = None
    logger.info("Global UncertaintyQuantifier singleton reset")