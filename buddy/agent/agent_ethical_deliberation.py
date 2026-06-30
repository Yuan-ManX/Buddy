"""Agent Ethical Deliberation — structured multi-framework ethical reasoning.

The Agent Ethical Deliberation framework provides a structured way for the
Buddy AI agent to reason about the ethical dimensions of proposed actions.
It evaluates actions against multiple ethical frameworks (utilitarian,
deontological, virtue ethics, care ethics, justice-based, pragmatic),
resolves ethical dilemmas, and produces verdicts with justifications and
recommendations.

Core capabilities:
- Register and look up ethical principles organized by category and framework
- Submit dilemmas with stakeholders, consequences, and applicable principles
- Auto-select applicable principles based on dilemma description keywords
- Multi-framework assessment producing per-framework scores and reasoning
- Weighted overall score combining all framework assessments
- Verdict determination with graduated permitted / conditional / review / prohibited gating
- Justification generation summarizing the deliberation outcome
- Recommendation generation guiding follow-up actions
- Quick action assessment for one-shot ethical checks
- Aggregate statistics describing the deliberator's state

The deliberator is intentionally dependency-free so it can run in any Buddy
runtime without extra packages. All state mutations are guarded by a single
``threading.Lock`` and reads return fresh copies of mutable structures.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class EthicalFramework(str, Enum):
    """Ethical frameworks used to evaluate proposed actions."""

    UTILITARIAN = "utilitarian"            # greatest overall good
    DEONTOLOGICAL = "deontological"        # duty- and rule-based ethics
    VIRTUE_ETHICS = "virtue_ethics"        # character and virtues
    CARE_ETHICS = "care_ethics"            # relationships and vulnerability
    JUSTICE_BASED = "justice_based"        # fairness and distribution
    PRAGMATIC = "pragmatic"                # blended practical reasoning


class DeliberationStatus(str, Enum):
    """Lifecycle state of an ethical dilemma."""

    PENDING = "pending"            # submitted, not yet analyzed
    ANALYZING = "analyzing"        # gathering stakeholders and consequences
    DELIBERATING = "deliberating"  # running framework assessments
    RESOLVED = "resolved"          # verdict produced
    FAILED = "failed"              # could not be resolved


class VerdictType(str, Enum):
    """Outcome of an ethical deliberation."""

    PERMITTED = "permitted"                                  # action is ethical
    PROHIBITED = "prohibited"                                # action is unethical
    PERMITTED_WITH_CONDITIONS = "permitted_with_conditions"  # ethical if conditions met
    REQUIRES_REVIEW = "requires_review"                      # insufficient clarity
    INCONCLUSIVE = "inconclusive"                            # cannot be decided


class StakeholderImpact(str, Enum):
    """Direction of impact a consequence has on a stakeholder."""

    POSITIVE = "positive"    # benefits the stakeholder
    NEGATIVE = "negative"    # harms the stakeholder
    NEUTRAL = "neutral"      # no significant effect
    MIXED = "mixed"          # both positive and negative aspects


class PrincipleCategory(str, Enum):
    """Category of an ethical principle (bioethics + general ethics)."""

    BENEFICENCE = "beneficence"            # do good
    NON_MALEFICENCE = "non_maleficence"    # do no harm
    AUTONOMY = "autonomy"                  # respect self-determination
    JUSTICE = "justice"                    # fair distribution
    FIDELITY = "fidelity"                  # honor commitments
    HONESTY = "honesty"                    # tell the truth
    FAIRNESS = "fairness"                  # treat equals equally


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

def _copy_value(value: Any) -> Any:
    """Return a fresh copy of mutable containers, pass scalars through.

    Lists and dicts are shallow-copied so callers cannot mutate internal
    state by holding a reference to a returned value. Enum values are
    left untouched; callers convert them via ``to_dict``.
    """
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    """Clamp ``value`` into the inclusive range ``[low, high]``."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _clamp01(value: float) -> float:
    """Clamp ``value`` into the inclusive range ``[0, 1]``."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


# Keyword table mapping descriptive cues to principle categories. Used by
# ``_select_applicable_principles`` to auto-attach relevant principles to a
# newly submitted dilemma based on its description text.
_PRINCIPLE_KEYWORDS: dict[PrincipleCategory, tuple[str, ...]] = {
    PrincipleCategory.NON_MALEFICENCE: (
        "harm", "hurt", "damage", "injury", "suffer", "pain",
    ),
    PrincipleCategory.BENEFICENCE: (
        "help", "benefit", "assist", "improve", "aid", "well-being",
    ),
    PrincipleCategory.AUTONOMY: (
        "choice", "consent", "freedom", "self-determination", "decide",
    ),
    PrincipleCategory.JUSTICE: (
        "fair", "equal", "just", "equitable", "distribution",
    ),
    PrincipleCategory.FAIRNESS: (
        "fair", "equal", "biased", "discrimination", "impartial",
    ),
    PrincipleCategory.HONESTY: (
        "truth", "lie", "deceive", "honest", "deception", "mislead",
    ),
    PrincipleCategory.FIDELITY: (
        "promise", "commit", "pledge", "trust", "vow", "oath",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Stakeholder:
    """A party with an interest in the outcome of an ethical dilemma.

    ``vulnerability`` ranges from 0 to 1; higher values indicate a
    stakeholder who is more susceptible to harm and therefore deserves
    additional weight under care-ethics considerations.
    """

    stakeholder_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    role: str = ""
    interests: list[str] = field(default_factory=list)
    vulnerability: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stakeholder_id": self.stakeholder_id,
            "name": self.name,
            "role": self.role,
            "interests": list(self.interests),
            "vulnerability": self.vulnerability,
            "created_at": self.created_at,
        }


@dataclass
class EthicalPrinciple:
    """A named ethical principle belonging to a category and framework.

    ``weight`` expresses how much this principle matters relative to
    others when scores are combined; higher weights dominate the overall
    assessment.
    """

    principle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: PrincipleCategory = PrincipleCategory.BENEFICENCE
    description: str = ""
    weight: float = 1.0
    framework: EthicalFramework = EthicalFramework.DEONTOLOGICAL
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "principle_id": self.principle_id,
            "name": self.name,
            "category": self.category.value
            if isinstance(self.category, PrincipleCategory)
            else str(self.category),
            "description": self.description,
            "weight": self.weight,
            "framework": self.framework.value
            if isinstance(self.framework, EthicalFramework)
            else str(self.framework),
            "created_at": self.created_at,
        }


@dataclass
class ActionConsequence:
    """A predicted outcome of the proposed action for a single stakeholder.

    ``magnitude`` ranges from 0 to 1 and expresses how large the effect
    is; ``probability`` ranges from 0 to 1 and expresses how likely the
    consequence is to materialize.
    """

    consequence_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    stakeholder_id: str = ""
    stakeholder_name: str = ""
    impact: StakeholderImpact = StakeholderImpact.NEUTRAL
    magnitude: float = 0.5
    probability: float = 0.8
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consequence_id": self.consequence_id,
            "stakeholder_id": self.stakeholder_id,
            "stakeholder_name": self.stakeholder_name,
            "impact": self.impact.value
            if isinstance(self.impact, StakeholderImpact)
            else str(self.impact),
            "magnitude": self.magnitude,
            "probability": self.probability,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class EthicalDilemma:
    """A structured ethical dilemma awaiting or undergoing deliberation.

    A dilemma bundles a proposed action with the stakeholders it affects,
    the consequences predicted for each, and the principles deemed
    applicable. Its ``status`` tracks progress through deliberation.
    """

    dilemma_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    proposed_action: str = ""
    stakeholders: list[Stakeholder] = field(default_factory=list)
    consequences: list[ActionConsequence] = field(default_factory=list)
    applicable_principles: list[EthicalPrinciple] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: DeliberationStatus = DeliberationStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "dilemma_id": self.dilemma_id,
            "title": self.title,
            "description": self.description,
            "proposed_action": self.proposed_action,
            "stakeholders": [s.to_dict() for s in self.stakeholders],
            "consequences": [c.to_dict() for c in self.consequences],
            "applicable_principles": [p.to_dict() for p in self.applicable_principles],
            "created_at": self.created_at,
            "status": self.status.value
            if isinstance(self.status, DeliberationStatus)
            else str(self.status),
        }


@dataclass
class FrameworkAssessment:
    """A single ethical framework's evaluation of a dilemma.

    ``score`` ranges from -1.0 (unethical under this framework) to
    +1.0 (ethical under this framework). ``key_factors`` captures the
    salient considerations that drove the score.
    """

    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    framework: EthicalFramework = EthicalFramework.PRAGMATIC
    score: float = 0.0
    reasoning: str = ""
    key_factors: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "framework": self.framework.value
            if isinstance(self.framework, EthicalFramework)
            else str(self.framework),
            "score": self.score,
            "reasoning": self.reasoning,
            "key_factors": list(self.key_factors),
            "created_at": self.created_at,
        }


@dataclass
class EthicalVerdict:
    """The final verdict on an ethical dilemma.

    Combines per-framework assessments into an overall score and a
    graduated verdict. ``conditions`` lists requirements that must hold
    for the action to be considered ethical when the verdict is
    ``PERMITTED_WITH_CONDITIONS``. ``recommendations`` suggests follow-up
    actions regardless of verdict.
    """

    verdict_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dilemma_id: str = ""
    verdict: VerdictType = VerdictType.INCONCLUSIVE
    overall_score: float = 0.0
    framework_assessments: list[FrameworkAssessment] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    justification: str = ""
    recommendations: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    deliberation_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict_id": self.verdict_id,
            "dilemma_id": self.dilemma_id,
            "verdict": self.verdict.value
            if isinstance(self.verdict, VerdictType)
            else str(self.verdict),
            "overall_score": self.overall_score,
            "framework_assessments": [a.to_dict() for a in self.framework_assessments],
            "conditions": list(self.conditions),
            "justification": self.justification,
            "recommendations": list(self.recommendations),
            "created_at": self.created_at,
            "deliberation_time": self.deliberation_time,
        }


@dataclass
class DeliberatorStats:
    """Aggregate statistics describing the state of the deliberator."""

    total_dilemmas: int = 0
    total_verdicts: int = 0
    total_permitted: int = 0
    total_prohibited: int = 0
    total_conditional: int = 0
    avg_deliberation_time: float = 0.0
    verdicts_by_framework: dict[str, int] = field(default_factory=dict)
    dilemmas_by_status: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_dilemmas": self.total_dilemmas,
            "total_verdicts": self.total_verdicts,
            "total_permitted": self.total_permitted,
            "total_prohibited": self.total_prohibited,
            "total_conditional": self.total_conditional,
            "avg_deliberation_time": self.avg_deliberation_time,
            "verdicts_by_framework": dict(self.verdicts_by_framework),
            "dilemmas_by_status": dict(self.dilemmas_by_status),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Agent Ethical Deliberator
# ═══════════════════════════════════════════════════════════════════════════

class AgentEthicalDeliberator:
    """Multi-framework ethical reasoning engine for the Buddy agent.

    The deliberator accepts ethical dilemmas described in terms of a
    proposed action, the stakeholders involved, and the consequences
    predicted for each. It evaluates each dilemma under six ethical
    frameworks (utilitarian, deontological, virtue ethics, care ethics,
    justice-based, pragmatic), combines the per-framework scores into an
    overall score, and emits a graduated verdict with a human-readable
    justification and actionable recommendations.

    All state mutations are guarded by a single ``threading.Lock`` so the
    deliberator is safe to invoke from concurrent agent threads. Reads
    return fresh copies of mutable structures to prevent external
    mutation of internal state.

    Capabilities:
      - Register and look up ethical principles by category and framework.
      - Submit dilemmas with optional pre-supplied stakeholders/consequences.
      - Auto-select applicable principles from dilemma description keywords.
      - Incrementally add stakeholders and consequences to a dilemma.
      - Run multi-framework deliberation producing a graduated verdict.
      - Generate justifications and recommendations for each verdict.
      - Quick one-shot action assessment for inline ethical checks.
      - Aggregate statistics describing the deliberator's state.
    """

    # Capacity limits guarding unbounded growth.
    MAX_DILEMMAS: int = 5000
    MAX_VERDICTS: int = 5000

    def __init__(self) -> None:
        self._dilemmas: dict[str, EthicalDilemma] = {}
        self._verdicts: dict[str, EthicalVerdict] = {}
        self._principles: dict[str, EthicalPrinciple] = {}
        self._lock = threading.Lock()
        self._default_principles: dict[str, EthicalPrinciple] = (
            self._init_default_principles()
        )

    # ── Principle Management ────────────────────────────────────────────

    def register_principle(
        self,
        name: str,
        category: PrincipleCategory,
        description: str,
        weight: float = 1.0,
        framework: EthicalFramework = EthicalFramework.DEONTOLOGICAL,
    ) -> EthicalPrinciple:
        """Register a new ethical principle with the deliberator.

        Args:
            name: Human-readable name of the principle.
            category: The ``PrincipleCategory`` this principle belongs to.
            description: Longer description of what the principle requires.
            weight: Relative importance of the principle (default 1.0).
            framework: The ethical framework this principle aligns with.

        Returns:
            The newly created and registered ``EthicalPrinciple``.
        """
        with self._lock:
            principle = EthicalPrinciple(
                name=name,
                category=category,
                description=description,
                weight=weight,
                framework=framework,
            )
            self._principles[principle.principle_id] = principle
            return principle

    def get_principle(self, principle_id: str) -> EthicalPrinciple | None:
        """Retrieve a registered principle by id, or ``None`` if absent.

        Looks up user-registered principles first, then falls back to the
        built-in default principles.
        """
        with self._lock:
            principle = self._principles.get(principle_id)
            if principle is not None:
                return principle
            return self._default_principles.get(principle_id)

    def list_principles(
        self, framework: EthicalFramework | None = None
    ) -> list[EthicalPrinciple]:
        """List registered principles, optionally filtered by framework.

        Default principles are included in the listing. When ``framework``
        is provided, only principles whose ``framework`` matches are
        returned.
        """
        with self._lock:
            combined: dict[str, EthicalPrinciple] = {}
            combined.update(self._default_principles)
            combined.update(self._principles)
            principles = list(combined.values())
            if framework is not None:
                principles = [p for p in principles if p.framework == framework]
            return principles

    def _init_default_principles(self) -> dict[str, EthicalPrinciple]:
        """Create the built-in default principles for each category.

        Must be called while holding ``self._lock`` (or before the lock
        is shared, e.g. in ``__init__``).
        """
        defaults = [
            ("Do Good", PrincipleCategory.BENEFICENCE,
             "Act to promote the well-being and benefit of others.",
             1.0, EthicalFramework.VIRTUE_ETHICS),
            ("Do No Harm", PrincipleCategory.NON_MALEFICENCE,
             "Avoid inflicting harm or suffering on others.",
             1.2, EthicalFramework.DEONTOLOGICAL),
            ("Respect Autonomy", PrincipleCategory.AUTONOMY,
             "Honor the self-determination and informed consent of agents.",
             1.0, EthicalFramework.DEONTOLOGICAL),
            ("Distribute Justly", PrincipleCategory.JUSTICE,
             "Distribute benefits and burdens fairly across stakeholders.",
             1.0, EthicalFramework.JUSTICE_BASED),
            ("Honor Fidelity", PrincipleCategory.FIDELITY,
             "Keep promises and honor commitments and trust.",
             1.0, EthicalFramework.DEONTOLOGICAL),
            ("Tell the Truth", PrincipleCategory.HONESTY,
             "Be truthful and avoid deception and misrepresentation.",
             1.1, EthicalFramework.DEONTOLOGICAL),
            ("Treat Equally", PrincipleCategory.FAIRNESS,
             "Treat equal cases equally without bias or discrimination.",
             1.0, EthicalFramework.JUSTICE_BASED),
        ]
        result: dict[str, EthicalPrinciple] = {}
        for name, category, description, weight, framework in defaults:
            principle = EthicalPrinciple(
                name=name,
                category=category,
                description=description,
                weight=weight,
                framework=framework,
            )
            result[principle.principle_id] = principle
        return result

    def _select_applicable_principles(
        self, dilemma_description: str
    ) -> list[EthicalPrinciple]:
        """Select principles whose keyword cues appear in ``dilemma_description``.

        Must be called while holding ``self._lock``.
        """
        if not dilemma_description:
            return []
        text = dilemma_description.lower()
        matched_categories: set[PrincipleCategory] = set()
        for category, keywords in _PRINCIPLE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    matched_categories.add(category)
                    break

        combined: dict[str, EthicalPrinciple] = {}
        combined.update(self._default_principles)
        combined.update(self._principles)
        selected: list[EthicalPrinciple] = []
        for principle in combined.values():
            if principle.category in matched_categories:
                selected.append(principle)
        return selected

    # ── Dilemma Management ──────────────────────────────────────────────

    def submit_dilemma(
        self,
        title: str,
        description: str,
        proposed_action: str,
        stakeholders: list[Stakeholder] | None = None,
        consequences: list[ActionConsequence] | None = None,
    ) -> EthicalDilemma:
        """Submit a new ethical dilemma for deliberation.

        Args:
            title: Short human-readable title for the dilemma.
            description: Longer description of the ethical situation.
            proposed_action: The action whose ethical status is in question.
            stakeholders: Optional pre-populated list of stakeholders.
            consequences: Optional pre-populated list of consequences.

        Returns:
            The newly created ``EthicalDilemma`` with status ``PENDING``.
            Applicable principles are auto-selected from the combined text
            of ``title``, ``description`` and ``proposed_action``. If no
            stakeholders or consequences are provided, the caller may add
            them later via ``add_stakeholder`` and ``add_consequence``
            before invoking ``deliberate``.
        """
        with self._lock:
            if len(self._dilemmas) >= self.MAX_DILEMMAS:
                # Evict the oldest dilemma to make room for the new one.
                oldest_id = min(
                    self._dilemmas.keys(),
                    key=lambda did: self._dilemmas[did].created_at,
                )
                self._dilemmas.pop(oldest_id, None)
            dilemma = EthicalDilemma(
                title=title,
                description=description,
                proposed_action=proposed_action,
                stakeholders=list(stakeholders) if stakeholders else [],
                consequences=list(consequences) if consequences else [],
            )
            dilemma.applicable_principles = self._select_applicable_principles(
                f"{title} {description} {proposed_action}"
            )
            self._dilemmas[dilemma.dilemma_id] = dilemma
            return dilemma

    def get_dilemma(self, dilemma_id: str) -> EthicalDilemma | None:
        """Retrieve a dilemma by id, or ``None`` if absent."""
        with self._lock:
            return self._dilemmas.get(dilemma_id)

    def list_dilemmas(
        self, status: DeliberationStatus | None = None
    ) -> list[EthicalDilemma]:
        """List dilemmas, optionally filtered by status."""
        with self._lock:
            dilemmas = list(self._dilemmas.values())
            if status is not None:
                dilemmas = [d for d in dilemmas if d.status == status]
            return dilemmas

    def add_stakeholder(
        self,
        dilemma_id: str,
        name: str,
        role: str,
        interests: list[str] | None = None,
        vulnerability: float = 0.5,
    ) -> Stakeholder | None:
        """Add a stakeholder to an existing dilemma.

        Returns the created ``Stakeholder``, or ``None`` if the dilemma
        was not found or is no longer editable (status ``RESOLVED`` or
        ``FAILED``).
        """
        with self._lock:
            dilemma = self._dilemmas.get(dilemma_id)
            if dilemma is None:
                return None
            if dilemma.status in (
                DeliberationStatus.RESOLVED,
                DeliberationStatus.FAILED,
            ):
                return None
            stakeholder = Stakeholder(
                name=name,
                role=role,
                interests=list(interests) if interests else [],
                vulnerability=_clamp01(vulnerability),
            )
            dilemma.stakeholders.append(stakeholder)
            return stakeholder

    def add_consequence(
        self,
        dilemma_id: str,
        stakeholder_id: str,
        stakeholder_name: str,
        impact: StakeholderImpact,
        magnitude: float = 0.5,
        probability: float = 0.8,
        description: str = "",
    ) -> ActionConsequence | None:
        """Add a predicted consequence to an existing dilemma.

        Returns the created ``ActionConsequence``, or ``None`` if the
        dilemma was not found or is no longer editable.
        """
        with self._lock:
            dilemma = self._dilemmas.get(dilemma_id)
            if dilemma is None:
                return None
            if dilemma.status in (
                DeliberationStatus.RESOLVED,
                DeliberationStatus.FAILED,
            ):
                return None
            consequence = ActionConsequence(
                stakeholder_id=stakeholder_id,
                stakeholder_name=stakeholder_name,
                impact=impact,
                magnitude=_clamp01(magnitude),
                probability=_clamp01(probability),
                description=description,
            )
            dilemma.consequences.append(consequence)
            return consequence

    # ── Deliberation ────────────────────────────────────────────────────

    def deliberate(self, dilemma_id: str) -> EthicalVerdict | None:
        """Run multi-framework deliberation on a dilemma.

        Produces a per-framework ``FrameworkAssessment`` for each of the
        six ethical frameworks, combines them into an overall score,
        determines a graduated verdict, generates a justification and
        recommendations, and stores the resulting ``EthicalVerdict``.

        Returns the verdict, or ``None`` if the dilemma was not found.
        """
        start_time = time.time()
        with self._lock:
            dilemma = self._dilemmas.get(dilemma_id)
            if dilemma is None:
                return None
            # Transition through the analyzing state before deliberating.
            dilemma.status = DeliberationStatus.ANALYZING
            dilemma.status = DeliberationStatus.DELIBERATING

            principles = list(dilemma.applicable_principles)
            if not principles:
                # Fall back to defaults so deliberation can still proceed.
                principles = list(self._default_principles.values())
            stakeholders = list(dilemma.stakeholders)
            consequences = list(dilemma.consequences)

            assessments: list[FrameworkAssessment] = []
            assessments.append(self._assess_utilitarian(consequences))
            assessments.append(self._assess_deontological(dilemma, principles))
            assessments.append(self._assess_virtue(dilemma, principles))
            assessments.append(self._assess_care(stakeholders, consequences))
            assessments.append(self._assess_justice(consequences))
            assessments.append(self._assess_pragmatic(assessments))

            overall_score = self._compute_overall_score(assessments)
            verdict_type = self._determine_verdict(overall_score)
            justification = self._generate_justification(
                dilemma, assessments, verdict_type
            )
            recommendations = self._generate_recommendations(
                verdict_type, assessments
            )
            conditions = self._generate_conditions(
                verdict_type, assessments, stakeholders
            )

            deliberation_time = time.time() - start_time
            verdict = EthicalVerdict(
                dilemma_id=dilemma_id,
                verdict=verdict_type,
                overall_score=overall_score,
                framework_assessments=assessments,
                conditions=conditions,
                justification=justification,
                recommendations=recommendations,
                deliberation_time=deliberation_time,
            )
            if len(self._verdicts) >= self.MAX_VERDICTS:
                # Evict the oldest verdict to make room for the new one.
                oldest_id = min(
                    self._verdicts.keys(),
                    key=lambda vid: self._verdicts[vid].created_at,
                )
                self._verdicts.pop(oldest_id, None)
            self._verdicts[verdict.verdict_id] = verdict
            dilemma.status = DeliberationStatus.RESOLVED
            return verdict

    def _assess_utilitarian(
        self, consequences: list[ActionConsequence]
    ) -> FrameworkAssessment:
        """Compute the utilitarian assessment of overall good.

        Each consequence contributes ``magnitude * probability * direction``
        where direction is +1 for positive impacts, -1 for negative, and 0
        for neutral and mixed impacts (mixed is treated as cancelling
        out). The raw sum is normalized by the maximum possible weighted
        magnitude to land in ``[-1, 1]``.
        """
        if not consequences:
            return FrameworkAssessment(
                framework=EthicalFramework.UTILITARIAN,
                score=0.0,
                reasoning="No consequences were provided; utility is neutral.",
                key_factors=["no consequences"],
            )

        def direction(impact: StakeholderImpact) -> float:
            if impact == StakeholderImpact.POSITIVE:
                return 1.0
            if impact == StakeholderImpact.NEGATIVE:
                return -1.0
            return 0.0  # NEUTRAL and MIXED contribute nothing.

        raw = 0.0
        normalizer = 0.0
        positive_count = 0
        negative_count = 0
        mixed_count = 0
        for c in consequences:
            mag = _clamp01(c.magnitude)
            prob = _clamp01(c.probability)
            contribution = mag * prob * direction(c.impact)
            raw += contribution
            normalizer += mag * prob
            if c.impact == StakeholderImpact.POSITIVE:
                positive_count += 1
            elif c.impact == StakeholderImpact.NEGATIVE:
                negative_count += 1
            elif c.impact == StakeholderImpact.MIXED:
                mixed_count += 1

        if normalizer > 0:
            score = _clamp(raw / normalizer)
        else:
            score = 0.0

        factors: list[str] = []
        if positive_count:
            factors.append(f"{positive_count} beneficial consequence(s)")
        if negative_count:
            factors.append(f"{negative_count} harmful consequence(s)")
        if mixed_count:
            factors.append(f"{mixed_count} mixed consequence(s)")
        if not factors:
            factors.append("no significant impact detected")

        reasoning = (
            f"Aggregated utility = {raw:.3f} normalized to {score:.3f} "
            f"across {len(consequences)} consequence(s)."
        )
        return FrameworkAssessment(
            framework=EthicalFramework.UTILITARIAN,
            score=score,
            reasoning=reasoning,
            key_factors=factors,
        )

    def _assess_deontological(
        self,
        dilemma: EthicalDilemma,
        principles: list[EthicalPrinciple],
    ) -> FrameworkAssessment:
        """Compute the deontological assessment based on duty adherence.

        Scans the dilemma text for cues indicating violations of honesty,
        fidelity, or non-maleficence duties. If violations are detected,
        the score is ``-1``. Otherwise, the score reflects adherence to
        applicable duty-style principles weighted by their importance.
        """
        text = (
            f"{dilemma.title} {dilemma.description} {dilemma.proposed_action}"
        ).lower()

        violation_cues = (
            "lie", "deceive", "deception", "mislead", "break promise",
            "betray", "cheat", "steal", "abuse", "coerce", "manipulate",
        )
        detected_violations = [c for c in violation_cues if c in text]

        duty_principles = [
            p for p in principles
            if p.category in (
                PrincipleCategory.HONESTY,
                PrincipleCategory.FIDELITY,
                PrincipleCategory.NON_MALEFICENCE,
            )
        ]

        if detected_violations:
            return FrameworkAssessment(
                framework=EthicalFramework.DEONTOLOGICAL,
                score=-1.0,
                reasoning=(
                    "Action appears to violate categorical duties: "
                    + ", ".join(detected_violations)
                    + "."
                ),
                key_factors=[
                    f"violation cue: {v}" for v in detected_violations
                ],
            )

        if not duty_principles:
            return FrameworkAssessment(
                framework=EthicalFramework.DEONTOLOGICAL,
                score=0.3,
                reasoning=(
                    "No duty-relevant principles applicable; default mild "
                    "duty adherence with no detected violations."
                ),
                key_factors=[
                    "no duty violations detected",
                    "no duty principles applicable",
                ],
            )

        total_weight = sum(p.weight for p in duty_principles)
        avg_weight = total_weight / len(duty_principles)
        # No violations detected: positive adherence proportional to weights.
        score = _clamp(0.5 * min(avg_weight, 1.0))
        return FrameworkAssessment(
            framework=EthicalFramework.DEONTOLOGICAL,
            score=score,
            reasoning=(
                f"No duty violations detected across {len(duty_principles)} "
                f"duty-relevant principle(s); adherence score = {score:.3f}."
            ),
            key_factors=[
                f"duty principle: {p.name}" for p in duty_principles
            ][:5],
        )

    def _assess_virtue(
        self,
        dilemma: EthicalDilemma,
        principles: list[EthicalPrinciple],
    ) -> FrameworkAssessment:
        """Compute the virtue-ethics assessment.

        Score is the weighted average of applicable virtue-aligned
        principles (beneficence, honesty, fidelity), with direction
        inferred from the dilemma text: +1 when virtue-affirming cues
        are present, -1 when virtue-violating cues are present, and a
        small presumptive positive value otherwise.
        """
        text = (
            f"{dilemma.title} {dilemma.description} {dilemma.proposed_action}"
        ).lower()

        virtue_categories = {
            PrincipleCategory.BENEFICENCE,
            PrincipleCategory.HONESTY,
            PrincipleCategory.FIDELITY,
        }
        virtue_principles = [
            p for p in principles if p.category in virtue_categories
        ]

        if not virtue_principles:
            return FrameworkAssessment(
                framework=EthicalFramework.VIRTUE_ETHICS,
                score=0.0,
                reasoning="No virtue-relevant principles applicable.",
                key_factors=["no virtue principles applicable"],
            )

        virtue_cues: dict[PrincipleCategory, tuple[str, ...]] = {
            PrincipleCategory.BENEFICENCE: ("help", "benefit", "assist", "care", "support"),
            PrincipleCategory.HONESTY: ("truth", "honest", "transparent", "candid"),
            PrincipleCategory.FIDELITY: ("promise", "commit", "trust", "loyal"),
        }
        violation_cues: dict[PrincipleCategory, tuple[str, ...]] = {
            PrincipleCategory.BENEFICENCE: ("harm", "hurt", "neglect"),
            PrincipleCategory.HONESTY: ("lie", "deceive", "mislead"),
            PrincipleCategory.FIDELITY: ("betray", "break promise", "abandon"),
        }

        weighted_sum = 0.0
        weight_total = 0.0
        factors: list[str] = []
        for principle in virtue_principles:
            direction = 0.0
            cues_pos = virtue_cues.get(principle.category, ())
            cues_neg = violation_cues.get(principle.category, ())
            if any(cue in text for cue in cues_pos):
                direction = 1.0
                factors.append(f"expresses {principle.name.lower()}")
            elif any(cue in text for cue in cues_neg):
                direction = -1.0
                factors.append(f"violates {principle.name.lower()}")
            else:
                direction = 0.2  # mild presumptive virtue
                factors.append(f"neutral toward {principle.name.lower()}")
            weighted_sum += principle.weight * direction
            weight_total += principle.weight

        score = _clamp(weighted_sum / weight_total) if weight_total > 0 else 0.0
        return FrameworkAssessment(
            framework=EthicalFramework.VIRTUE_ETHICS,
            score=score,
            reasoning=(
                f"Weighted virtue alignment = {weighted_sum:.3f} / "
                f"{weight_total:.3f} -> score {score:.3f}."
            ),
            key_factors=factors[:5],
        )

    def _assess_care(
        self,
        stakeholders: list[Stakeholder],
        consequences: list[ActionConsequence],
    ) -> FrameworkAssessment:
        """Compute the care-ethics assessment focusing on the vulnerable.

        Considers stakeholders whose ``vulnerability`` is strictly above
        0.5. If any vulnerable stakeholder suffers a negative
        consequence, the score is driven negative proportional to the
        harm magnitude and vulnerability weight; positive consequences
        for the vulnerable raise the score.
        """
        if not stakeholders:
            return FrameworkAssessment(
                framework=EthicalFramework.CARE_ETHICS,
                score=0.0,
                reasoning="No stakeholders provided; cannot assess care obligations.",
                key_factors=["no stakeholders"],
            )

        vulnerable = [s for s in stakeholders if s.vulnerability > 0.5]
        if not vulnerable:
            return FrameworkAssessment(
                framework=EthicalFramework.CARE_ETHICS,
                score=0.2,
                reasoning=(
                    "No highly vulnerable stakeholders identified; default "
                    "mild care score."
                ),
                key_factors=["no vulnerable stakeholders"],
            )

        vulnerable_ids = {s.stakeholder_id for s in vulnerable}
        relevant = [
            c for c in consequences if c.stakeholder_id in vulnerable_ids
        ]
        if not relevant:
            return FrameworkAssessment(
                framework=EthicalFramework.CARE_ETHICS,
                score=0.1,
                reasoning=(
                    f"{len(vulnerable)} vulnerable stakeholder(s) but no "
                    f"consequences predicted for them."
                ),
                key_factors=[f"vulnerable: {s.name}" for s in vulnerable][:5],
            )

        weighted_sum = 0.0
        weight_total = 0.0
        factors: list[str] = []
        vuln_by_id = {s.stakeholder_id: s for s in vulnerable}
        for c in relevant:
            stakeholder = vuln_by_id.get(c.stakeholder_id)
            if stakeholder is None:
                continue
            weight = stakeholder.vulnerability
            if c.impact == StakeholderImpact.NEGATIVE:
                direction = -1.0
                factors.append(f"harm to vulnerable {stakeholder.name}")
            elif c.impact == StakeholderImpact.POSITIVE:
                direction = 1.0
                factors.append(f"benefit to vulnerable {stakeholder.name}")
            else:
                direction = 0.0
                factors.append(f"neutral effect on vulnerable {stakeholder.name}")
            contribution = direction * c.magnitude * c.probability * weight
            weighted_sum += contribution
            weight_total += weight

        score = _clamp(weighted_sum / weight_total) if weight_total > 0 else 0.0
        return FrameworkAssessment(
            framework=EthicalFramework.CARE_ETHICS,
            score=score,
            reasoning=(
                f"Vulnerability-weighted impact = {weighted_sum:.3f} / "
                f"{weight_total:.3f} -> score {score:.3f}."
            ),
            key_factors=factors[:5],
        )

    def _assess_justice(
        self, consequences: list[ActionConsequence]
    ) -> FrameworkAssessment:
        """Compute the justice-based assessment of fair distribution.

        Measures how evenly benefits and burdens are distributed across
        stakeholders. Highly uneven distributions lower the score. The
        mean net impact drives the sign of the score while the variance
        modulates its magnitude.
        """
        if not consequences:
            return FrameworkAssessment(
                framework=EthicalFramework.JUSTICE_BASED,
                score=0.0,
                reasoning="No consequences provided; fairness is undetermined.",
                key_factors=["no consequences"],
            )

        # Per-stakeholder net impact (positive - negative magnitudes).
        net_by_stakeholder: dict[str, float] = {}
        for c in consequences:
            mag = c.magnitude * c.probability
            if c.impact == StakeholderImpact.POSITIVE:
                net_by_stakeholder[c.stakeholder_id] = (
                    net_by_stakeholder.get(c.stakeholder_id, 0.0) + mag
                )
            elif c.impact == StakeholderImpact.NEGATIVE:
                net_by_stakeholder[c.stakeholder_id] = (
                    net_by_stakeholder.get(c.stakeholder_id, 0.0) - mag
                )

        if not net_by_stakeholder:
            return FrameworkAssessment(
                framework=EthicalFramework.JUSTICE_BASED,
                score=0.2,
                reasoning=(
                    "Consequences have no directional impact; mild positive "
                    "fairness by default."
                ),
                key_factors=["no directional impact"],
            )

        values = list(net_by_stakeholder.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        # Normalize variance to [0, 1] (max variance ~1 for {-1, +1} split).
        normalized_variance = min(variance, 1.0)
        # Score rewards positive mean and penalizes uneven distribution.
        fairness_component = 1.0 - normalized_variance
        if mean >= 0:
            score = _clamp(0.5 * mean + 0.5 * fairness_component)
        else:
            score = _clamp(0.5 * mean - 0.5 * fairness_component)

        beneficiaries = sum(1 for v in values if v > 0)
        harmed = sum(1 for v in values if v < 0)
        factors = [
            f"{beneficiaries} stakeholder(s) benefit",
            f"{harmed} stakeholder(s) harmed",
            f"distribution variance {variance:.3f}",
        ]
        return FrameworkAssessment(
            framework=EthicalFramework.JUSTICE_BASED,
            score=score,
            reasoning=(
                f"Mean net impact = {mean:.3f}, variance = {variance:.3f} "
                f"-> fairness score {score:.3f}."
            ),
            key_factors=factors,
        )

    def _assess_pragmatic(
        self, framework_scores: list[FrameworkAssessment]
    ) -> FrameworkAssessment:
        """Compute the pragmatic assessment as a blended average.

        Averages the other framework scores and adjusts the result by
        the average confidence implied by their absolute magnitudes
        (assessments near zero are treated as low-confidence).
        """
        # Exclude any prior pragmatic assessment to avoid self-reference.
        others = [
            a for a in framework_scores
            if a.framework != EthicalFramework.PRAGMATIC
        ]
        if not others:
            return FrameworkAssessment(
                framework=EthicalFramework.PRAGMATIC,
                score=0.0,
                reasoning="No other frameworks assessed; pragmatic score is neutral.",
                key_factors=["no other assessments"],
            )

        avg_score = sum(a.score for a in others) / len(others)
        # Confidence = average absolute score (how far from neutral).
        confidence = sum(abs(a.score) for a in others) / len(others)
        # Adjust toward zero when confidence is low (uncertain assessments).
        adjusted = avg_score * (0.5 + 0.5 * min(confidence, 1.0))
        score = _clamp(adjusted)
        factors = [f"{a.framework.value}: {a.score:.3f}" for a in others]
        return FrameworkAssessment(
            framework=EthicalFramework.PRAGMATIC,
            score=score,
            reasoning=(
                f"Pragmatic blend of {len(others)} framework(s): "
                f"average {avg_score:.3f} adjusted by confidence {confidence:.3f}."
            ),
            key_factors=factors,
        )

    def _compute_overall_score(
        self, assessments: list[FrameworkAssessment]
    ) -> float:
        """Compute the weighted average of all framework assessment scores.

        Each framework contributes with equal weight except pragmatic,
        which is down-weighted to 0.5 because it is derived from the
        others and would otherwise double-count their signals.
        """
        if not assessments:
            return 0.0
        weighted_sum = 0.0
        weight_total = 0.0
        for a in assessments:
            weight = 0.5 if a.framework == EthicalFramework.PRAGMATIC else 1.0
            weighted_sum += a.score * weight
            weight_total += weight
        if weight_total <= 0:
            return 0.0
        return _clamp(weighted_sum / weight_total)

    def _determine_verdict(self, score: float) -> VerdictType:
        """Map an overall score to a graduated verdict.

        Thresholds:
          score > 0.3  -> PERMITTED
          score > 0.0  -> PERMITTED_WITH_CONDITIONS
          score > -0.3 -> REQUIRES_REVIEW
          score > -1.0 -> PROHIBITED
          else         -> INCONCLUSIVE
        """
        if score > 0.3:
            return VerdictType.PERMITTED
        if score > 0.0:
            return VerdictType.PERMITTED_WITH_CONDITIONS
        if score > -0.3:
            return VerdictType.REQUIRES_REVIEW
        if score > -1.0:
            return VerdictType.PROHIBITED
        return VerdictType.INCONCLUSIVE

    def _generate_justification(
        self,
        dilemma: EthicalDilemma,
        assessments: list[FrameworkAssessment],
        verdict: VerdictType,
    ) -> str:
        """Produce a human-readable justification for the verdict."""
        verdict_phrasing = {
            VerdictType.PERMITTED: "is ethically permitted",
            VerdictType.PROHIBITED: "is ethically prohibited",
            VerdictType.PERMITTED_WITH_CONDITIONS: "is permitted only with conditions",
            VerdictType.REQUIRES_REVIEW: "requires further ethical review",
            VerdictType.INCONCLUSIVE: "cannot be conclusively evaluated",
        }.get(verdict, "requires further ethical review")

        overall = self._compute_overall_score(assessments)
        parts: list[str] = []
        action_label = dilemma.proposed_action or dilemma.title or "the proposed action"
        parts.append(f"The proposed action '{action_label}' {verdict_phrasing}.")
        parts.append(
            f"Overall ethical score: {overall:.3f} on a [-1, +1] scale."
        )
        # Highlight the most extreme framework assessments.
        if assessments:
            sorted_assessments = sorted(
                assessments, key=lambda a: abs(a.score), reverse=True
            )
            top = sorted_assessments[0]
            parts.append(
                f"Most decisive framework: {top.framework.value} "
                f"(score {top.score:.3f}) - {top.reasoning}"
            )
        # Note stakeholders and consequences considered.
        parts.append(
            f"Considered {len(dilemma.stakeholders)} stakeholder(s) and "
            f"{len(dilemma.consequences)} consequence(s) across "
            f"{len(assessments)} ethical framework(s)."
        )
        return " ".join(parts)

    def _generate_recommendations(
        self,
        verdict: VerdictType,
        assessments: list[FrameworkAssessment],
    ) -> list[str]:
        """Produce actionable recommendations based on the verdict."""
        recommendations: list[str] = []
        if verdict == VerdictType.PERMITTED:
            recommendations.append(
                "Proceed with the action; no ethical concerns flagged."
            )
        elif verdict == VerdictType.PERMITTED_WITH_CONDITIONS:
            recommendations.append(
                "Proceed only after the attached conditions are satisfied."
            )
        elif verdict == VerdictType.REQUIRES_REVIEW:
            recommendations.append(
                "Escalate to a human reviewer or ethics board before proceeding."
            )
            recommendations.append(
                "Gather additional context on stakeholder consent and probable outcomes."
            )
        elif verdict == VerdictType.PROHIBITED:
            recommendations.append("Do not proceed with the action as proposed.")
            recommendations.append(
                "Consider alternative actions that achieve the same goal ethically."
            )
        else:  # INCONCLUSIVE
            recommendations.append(
                "Re-frame the dilemma with more detail before re-evaluating."
            )
            recommendations.append(
                "Collect missing information about stakeholders or consequences."
            )

        # Surface any framework that strongly objected.
        for a in assessments:
            if a.score <= -0.7:
                recommendations.append(
                    f"Address concerns raised by the {a.framework.value} framework."
                )
        # Surface any framework that strongly endorsed.
        for a in assessments:
            if a.score >= 0.7:
                recommendations.append(
                    f"The {a.framework.value} framework strongly endorses the action."
                )
        # Suggest bolstering weak evidence when review is required.
        if verdict == VerdictType.REQUIRES_REVIEW:
            for a in assessments:
                if -0.3 <= a.score <= 0.3:
                    recommendations.append(
                        f"Strengthen evidence considered under the {a.framework.value} framework."
                    )
                    break

        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique: list[str] = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique.append(r)
        return unique

    def _generate_conditions(
        self,
        verdict: VerdictType,
        assessments: list[FrameworkAssessment],
        stakeholders: list[Stakeholder],
    ) -> list[str]:
        """Produce conditions attached to a ``PERMITTED_WITH_CONDITIONS`` verdict.

        For other verdicts this returns an empty list.
        """
        if verdict != VerdictType.PERMITTED_WITH_CONDITIONS:
            return []
        conditions: list[str] = []
        # If any framework is negative, require its concerns to be mitigated.
        for a in assessments:
            if a.score < 0.0:
                conditions.append(
                    f"Mitigate concerns from the {a.framework.value} framework "
                    f"(current score {a.score:.3f})."
                )
        # Require informed consent from vulnerable stakeholders.
        vulnerable = [s for s in stakeholders if s.vulnerability > 0.5]
        if vulnerable:
            names = ", ".join(s.name for s in vulnerable[:3])
            conditions.append(
                f"Obtain informed consent from vulnerable stakeholder(s): {names}."
            )
        conditions.append("Monitor outcomes and re-evaluate if conditions change.")
        return conditions

    # ── Verdict Access ──────────────────────────────────────────────────

    def get_verdict(self, verdict_id: str) -> EthicalVerdict | None:
        """Retrieve a verdict by id, or ``None`` if absent."""
        with self._lock:
            return self._verdicts.get(verdict_id)

    def get_verdict_for_dilemma(self, dilemma_id: str) -> EthicalVerdict | None:
        """Retrieve the verdict for a given dilemma, if one has been produced."""
        with self._lock:
            for verdict in self._verdicts.values():
                if verdict.dilemma_id == dilemma_id:
                    return verdict
            return None

    def list_verdicts(
        self, verdict_type: VerdictType | None = None
    ) -> list[EthicalVerdict]:
        """List verdicts, optionally filtered by verdict type."""
        with self._lock:
            verdicts = list(self._verdicts.values())
            if verdict_type is not None:
                verdicts = [v for v in verdicts if v.verdict == verdict_type]
            return verdicts

    # ── Quick Assessment ────────────────────────────────────────────────

    def assess_action(
        self,
        action_description: str,
        stakeholders: list[Stakeholder] | None = None,
        consequences: list[ActionConsequence] | None = None,
    ) -> EthicalVerdict:
        """Quickly assess an action in a single call.

        Creates a dilemma from the supplied action description, ensures
        at least the default principles are applicable, runs deliberation,
        and returns the resulting verdict. Convenience wrapper around
        ``submit_dilemma`` + ``deliberate`` for inline ethical checks.

        Args:
            action_description: The action whose ethical status to assess.
            stakeholders: Optional pre-populated list of stakeholders.
            consequences: Optional pre-populated list of consequences.

        Returns:
            The ``EthicalVerdict`` produced by deliberation.
        """
        dilemma = self.submit_dilemma(
            title=f"Quick assessment: {action_description[:60]}",
            description=action_description,
            proposed_action=action_description,
            stakeholders=stakeholders,
            consequences=consequences,
        )
        verdict = self.deliberate(dilemma.dilemma_id)
        if verdict is None:
            # Extremely unlikely: the dilemma was just created. Fail loudly.
            raise RuntimeError(
                f"deliberate() returned None for freshly created dilemma "
                f"{dilemma.dilemma_id}"
            )
        return verdict

    # ── Statistics ──────────────────────────────────────────────────────

    def get_stats(self) -> DeliberatorStats:
        """Compute aggregate statistics describing the deliberator's state."""
        with self._lock:
            total_dilemmas = len(self._dilemmas)
            total_verdicts = len(self._verdicts)
            total_permitted = 0
            total_prohibited = 0
            total_conditional = 0
            deliberation_times: list[float] = []
            verdicts_by_framework: dict[str, int] = {}
            dilemmas_by_status: dict[str, int] = {}

            for verdict in self._verdicts.values():
                if verdict.verdict == VerdictType.PERMITTED:
                    total_permitted += 1
                elif verdict.verdict == VerdictType.PROHIBITED:
                    total_prohibited += 1
                elif verdict.verdict == VerdictType.PERMITTED_WITH_CONDITIONS:
                    total_conditional += 1
                deliberation_times.append(verdict.deliberation_time)
                for assessment in verdict.framework_assessments:
                    key = assessment.framework.value
                    verdicts_by_framework[key] = (
                        verdicts_by_framework.get(key, 0) + 1
                    )

            for dilemma in self._dilemmas.values():
                key = dilemma.status.value
                dilemmas_by_status[key] = (
                    dilemmas_by_status.get(key, 0) + 1
                )

            avg_time = (
                sum(deliberation_times) / len(deliberation_times)
                if deliberation_times
                else 0.0
            )

            return DeliberatorStats(
                total_dilemmas=total_dilemmas,
                total_verdicts=total_verdicts,
                total_permitted=total_permitted,
                total_prohibited=total_prohibited,
                total_conditional=total_conditional,
                avg_deliberation_time=avg_time,
                verdicts_by_framework=dict(verdicts_by_framework),
                dilemmas_by_status=dict(dilemmas_by_status),
            )


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_global_deliberator: AgentEthicalDeliberator | None = None
_global_deliberator_lock = threading.Lock()


def get_ethical_deliberator() -> AgentEthicalDeliberator:
    """Get or create the singleton AgentEthicalDeliberator instance."""
    global _global_deliberator
    with _global_deliberator_lock:
        if _global_deliberator is None:
            _global_deliberator = AgentEthicalDeliberator()
        return _global_deliberator


def reset_ethical_deliberator() -> None:
    """Reset the singleton AgentEthicalDeliberator instance."""
    global _global_deliberator
    with _global_deliberator_lock:
        _global_deliberator = None
