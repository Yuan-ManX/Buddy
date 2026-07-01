from __future__ import annotations

# Agent Cognitive Scaffolding — structured, adaptive support that helps users
# (and the agent itself) accomplish tasks just beyond current capability, with
# support fading as competence grows.
#
# Scaffolding is the temporary support a more capable partner offers a learner
# so they can reach a goal they could not reach alone. This module captures
# that idea operationally: it models learners, assesses their competence in
# specific skill domains, opens scaffolding sessions around concrete tasks,
# proposes scaffolds of varying level and strategy, attaches fading plans that
# describe when and how support should be withdrawn, and records outcomes so
# the engine can adapt over time. As a learner demonstrates mastery, support
# is faded and finally withdrawn; if the learner struggles, support can be
# re-proposed at a different level or with a different strategy.
#
# Capabilities: learner registration, competence assessment, session
# management, scaffold proposal/activation/fading/withdrawal, fading-plan
# construction, outcome recording, and aggregate statistics.
#
# Architecture:
#     AgentCognitiveScaffolding (singleton)
#     ├── LearnerProfile (a registered learner)
#     │   └── CompetenceAssessment (a measured competence in a skill domain)
#     ├── ScaffoldingSession (a task-focused support episode)
#     │   └── Scaffold (a single support artifact with a lifecycle)
#     │       └── FadingPlan (milestones describing when to fade support)
#     └── ScaffoldingStats (aggregate engine statistics)

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ScaffoldingLevel(str, Enum):
    """The cognitive level at which a scaffold operates.

    A scaffold can act on different layers of cognition. CONCEPTUAL scaffolds
    address ideas, principles, and mental models (the "what" and "why").
    PROCEDURAL scaffolds address steps, methods, and how-to knowledge (the
    "how"). STRATEGIC scaffolds address planning, selection among
    alternatives, and resource allocation (the "when" and "which"). 
    METACOGNITIVE scaffolds address self-monitoring, reflection, and the
    learner's awareness of their own thinking (the "whether" and "check").
    """
    CONCEPTUAL = "conceptual"        # ideas, principles, mental models
    PROCEDURAL = "procedural"        # steps, methods, how-to knowledge
    STRATEGIC = "strategic"          # planning, selection, allocation
    METACOGNITIVE = "metacognitive"  # self-monitoring, reflection


class ScaffoldingStrategy(str, Enum):
    """The pedagogical strategy a scaffold uses to deliver support.

    Each strategy is a different way of lending assistance. A HINT is a small
    cue pointing toward the next step. An EXAMPLE is a worked sample to
    imitate. DECOMPOSE breaks the task into smaller, more approachable parts.
    MODEL demonstrates the target process for the learner to observe. PROMPT
    is a direct request to act. FEEDBACK gives corrective information about
    performance. QUESTION poses a question that elicits the learner's own
    reasoning.
    """
    HINT = "hint"            # a small cue pointing toward the next step
    EXAMPLE = "example"      # a worked example to imitate
    DECOMPOSE = "decompose"  # break the task into smaller parts
    MODEL = "model"          # demonstrate the target process
    PROMPT = "prompt"        # a direct prompt to act
    FEEDBACK = "feedback"    # corrective information about performance
    QUESTION = "question"    # a question that elicits reasoning


class CompetenceLevel(str, Enum):
    """A coarse ordinal scale of a learner's competence in a skill domain.

    The scale runs from NOVICE (essentially no prior exposure) through
    BEGINNER and INTERMEDIATE to a capable level and finally EXPERT (fluent,
    can teach others). It is used both to record the current state of a
    learner and to express the target level a session aims to reach. The
    ordering reflects increasing independence: a NOVICE needs heavy support,
    an EXPERT needs little or none.
    """
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class FadingTrigger(str, Enum):
    """The signal that initiates fading of a scaffold.

    Fading is the gradual removal of support as competence grows. Different
    triggers can start the process: MASTERY fires when the learner
    demonstrates command of the skill; TIME fires after a fixed duration of
    support; ERROR_RATE fires when observed errors fall below a threshold;
    CONFIDENCE fires when the learner's self-reported confidence exceeds a
    threshold; EXPLICIT fires on a direct request to withdraw support.
    """
    MASTERY = "mastery"          # learner demonstrates mastery
    TIME = "time"                # a fixed duration has elapsed
    ERROR_RATE = "error_rate"    # error rate falls below threshold
    CONFIDENCE = "confidence"    # learner confidence exceeds threshold
    EXPLICIT = "explicit"        # an explicit request to withdraw


class ScaffoldStatus(str, Enum):
    """Lifecycle states of a scaffold.

    PROPOSED means the scaffold has been created but not yet providing
    support. ACTIVE means it is currently in effect. FADING means support is
    being gradually withdrawn according to its fading plan. WITHDRAWN is the
    terminal state for a scaffold that was removed successfully; FAILED is
    the terminal state for a scaffold that was removed without achieving its
    goal (for example, the learner could not progress even with support).
    """
    PROPOSED = "proposed"    # created, not yet active
    ACTIVE = "active"        # currently providing support
    FADING = "fading"        # support being gradually withdrawn
    WITHDRAWN = "withdrawn"  # support removed (success)
    FAILED = "failed"        # support removed (did not succeed)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a learner/session/scaffold/etc."""
    return str(uuid.uuid4())[:8]


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"conceptual"``) and then against member names
    (e.g. ``"CONCEPTUAL"``), so callers may pass either form. Raises
    ``ValueError`` if neither matches.
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            pass
        try:
            return enum_cls[value]
        except KeyError:
            pass
    raise ValueError(f"{value!r} is not a valid {enum_cls.__name__}")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = low
    if f < low:
        return low
    if f > high:
        return high
    return f


def _enum_value(enum_cls: type, value: Any) -> str:
    """Return the ``.value`` of an enum member, or a string fallback.

    Used inside ``to_dict`` methods so a stored field always serializes to a
    plain string even if (through direct construction) a non-enum slipped in.
    """
    if isinstance(value, enum_cls):
        return value.value
    return str(value)


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CompetenceAssessment:
    """A measurement of a learner's competence in a skill domain.

    An assessment pairs a coarse ``level`` (NOVICE..EXPERT) with a numeric
    ``score`` in [0, 1] for finer resolution, plus free-form ``evidence``
    describing what the measurement is based on (observed behavior, a test
    result, self-report, etc.). Assessments are append-only: each new
    measurement creates a new record so the learner's history is preserved.
    """
    assessment_id: str = field(default_factory=_new_id)
    learner_id: str = ""
    skill_domain: str = ""
    level: CompetenceLevel = CompetenceLevel.BEGINNER
    score: float = 0.3
    evidence: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this assessment to a plain dict, expanding the enum."""
        return {
            "assessment_id": self.assessment_id,
            "learner_id": self.learner_id,
            "skill_domain": self.skill_domain,
            "level": _enum_value(CompetenceLevel, self.level),
            "score": self.score,
            "evidence": self.evidence,
            "created_at": self.created_at,
        }


@dataclass
class FadingPlan:
    """A sequence of milestones describing when and how to fade a scaffold.

    Each milestone is a dict with three keys: ``trigger`` (a FadingTrigger
    that fires the milestone), ``threshold`` (a numeric threshold the trigger
    is compared against, e.g. a mastery score or an error rate), and
    ``action`` (a free-form description of the fading action to take, e.g.
    "reduce hint frequency"). ``current_step`` records which milestone the
    plan is currently waiting on; it advances as milestones fire.
    """
    plan_id: str = field(default_factory=_new_id)
    scaffold_id: str = ""
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this fading plan to a plain dict.

        Each milestone's ``trigger`` is expanded via ``.value``; the other
        keys are copied as-is.
        """
        serialized: List[Dict[str, Any]] = []
        for milestone in self.milestones:
            trigger = milestone.get("trigger") if isinstance(milestone, dict) else None
            entry: Dict[str, Any] = {
                "trigger": _enum_value(FadingTrigger, trigger) if trigger is not None else None,
                "threshold": milestone.get("threshold") if isinstance(milestone, dict) else None,
                "action": milestone.get("action") if isinstance(milestone, dict) else None,
            }
            serialized.append(entry)
        return {
            "plan_id": self.plan_id,
            "scaffold_id": self.scaffold_id,
            "milestones": serialized,
            "current_step": self.current_step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Scaffold:
    """A single support artifact within a scaffolding session.

    A scaffold is the unit of support: it has a cognitive ``level``, a
    pedagogical ``strategy``, free-form ``content`` (the actual hint,
    example, model, etc.), and a ``fading_trigger`` that describes when
    fading should begin. The ``status`` field tracks the lifecycle from
    PROPOSED through ACTIVE and FADING to a terminal WITHDRAWN or FAILED.

    ``fading_plan_id`` optionally links the scaffold to a FadingPlan that
    details the fading milestones. ``activated_at`` and ``withdrawn_at``
    record lifecycle timestamps; ``outcome`` records the final outcome
    string (e.g. "success", "partial", "failed") when the scaffold is
    withdrawn.
    """
    scaffold_id: str = field(default_factory=_new_id)
    session_id: str = ""
    level: ScaffoldingLevel = ScaffoldingLevel.CONCEPTUAL
    strategy: ScaffoldingStrategy = ScaffoldingStrategy.HINT
    content: str = ""
    fading_trigger: FadingTrigger = FadingTrigger.MASTERY
    status: ScaffoldStatus = ScaffoldStatus.PROPOSED
    fading_plan_id: Optional[str] = None
    created_at: str = field(default_factory=_now)
    activated_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    outcome: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this scaffold to a plain dict.

        Enums are expanded via ``.value``.
        """
        return {
            "scaffold_id": self.scaffold_id,
            "session_id": self.session_id,
            "level": _enum_value(ScaffoldingLevel, self.level),
            "strategy": _enum_value(ScaffoldingStrategy, self.strategy),
            "content": self.content,
            "fading_trigger": _enum_value(FadingTrigger, self.fading_trigger),
            "status": _enum_value(ScaffoldStatus, self.status),
            "fading_plan_id": self.fading_plan_id,
            "created_at": self.created_at,
            "activated_at": self.activated_at,
            "withdrawn_at": self.withdrawn_at,
            "outcome": self.outcome,
        }


@dataclass
class ScaffoldingSession:
    """A task-focused scaffolding episode for one learner.

    A session ties a learner to a concrete ``task_description`` in a
    ``skill_domain`` and holds the scaffolds proposed during the episode.
    ``target_level`` is the competence level the session aims to bring the
    learner toward. ``status`` is a free-form string (e.g. "open",
    "in_progress", "completed", "abandoned") so callers can model their own
    session lifecycle. ``outcomes`` is an append-only list of outcome dicts
    recorded as the session progresses.
    """
    session_id: str = field(default_factory=_new_id)
    learner_id: str = ""
    task_description: str = ""
    skill_domain: str = ""
    target_level: CompetenceLevel = CompetenceLevel.INTERMEDIATE
    status: str = "open"
    scaffolds: List[str] = field(default_factory=list)
    outcomes: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this session to a plain dict.

        The ``target_level`` enum is expanded via ``.value``; scaffold ids
        and outcomes are copied as plain lists/dicts.
        """
        return {
            "session_id": self.session_id,
            "learner_id": self.learner_id,
            "task_description": self.task_description,
            "skill_domain": self.skill_domain,
            "target_level": _enum_value(CompetenceLevel, self.target_level),
            "status": self.status,
            "scaffolds": list(self.scaffolds),
            "outcomes": [dict(o) if isinstance(o, dict) else o for o in self.outcomes],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class LearnerProfile:
    """A registered learner known to the scaffolding engine.

    A learner is identified by ``learner_id`` (caller-supplied) and an
    optional display ``name``. The profile holds references (by id) to the
    learner's competence assessments and scaffolding sessions, so the full
    history can be reconstructed without duplicating state.
    """
    learner_id: str = ""
    name: str = ""
    assessments: List[str] = field(default_factory=list)
    sessions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this learner profile to a plain dict."""
        return {
            "learner_id": self.learner_id,
            "name": self.name,
            "assessments": list(self.assessments),
            "sessions": list(self.sessions),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ScaffoldingStats:
    """Aggregate statistics over the scaffolding engine's state.

    Counts of learners, sessions, and scaffolds; the number of currently
    active scaffolds and the number withdrawn; and three breakdown dicts
    (``by_level``, ``by_strategy``, ``by_status``) that tally scaffolds by
    their enum members. Breakdown keys are the enum ``.value`` strings so
    the stats serialize cleanly to JSON.
    """
    total_learners: int = 0
    total_sessions: int = 0
    total_scaffolds: int = 0
    active_scaffolds: int = 0
    withdrawn_scaffolds: int = 0
    by_level: Dict[str, int] = field(default_factory=dict)
    by_strategy: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict."""
        return {
            "total_learners": self.total_learners,
            "total_sessions": self.total_sessions,
            "total_scaffolds": self.total_scaffolds,
            "active_scaffolds": self.active_scaffolds,
            "withdrawn_scaffolds": self.withdrawn_scaffolds,
            "by_level": dict(self.by_level),
            "by_strategy": dict(self.by_strategy),
            "by_status": dict(self.by_status),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveScaffolding:
    """Cognitive scaffolding engine with learner, session, and scaffold state.

    The engine maintains registries of learners, competence assessments,
    scaffolding sessions, scaffolds, and fading plans. Each scaffold moves
    through a lifecycle (PROPOSED -> ACTIVE -> FADING -> WITHDRAWN/FAILED)
    driven by explicit calls; fading plans describe when fading should
    begin. All state mutations are guarded by a single lock so the engine
    is safe to call from multiple threads.

    The engine is intended to support both human learners and the agent
    itself: an agent that is learning a new capability can register as a
    learner and receive scaffolds the same way a human would. As competence
    grows, support fades and is withdrawn, leaving the learner (or agent)
    operating independently.
    """

    # Capacity limits to bound memory use per engine instance.
    MAX_LEARNERS: int = 10000
    MAX_SESSIONS_PER_LEARNER: int = 1000
    MAX_SCAFFOLDS_PER_SESSION: int = 500
    MAX_MILESTONES_PER_PLAN: int = 50

    def __init__(self) -> None:
        self._learners: Dict[str, LearnerProfile] = {}
        self._assessments: Dict[str, CompetenceAssessment] = {}
        self._sessions: Dict[str, ScaffoldingSession] = {}
        self._scaffolds: Dict[str, Scaffold] = {}
        self._fading_plans: Dict[str, FadingPlan] = {}
        # Index from scaffold_id to its fading plan_id for quick lookup.
        self._scaffold_plan_index: Dict[str, str] = {}
        self._lock = threading.Lock()
        # Engine creation time, kept as a float for easy comparison.
        self._created_at: float = time.time()

    # ── Learner Management ──────────────────────────────────────────

    def register_learner(
        self,
        learner_id: str,
        name: str = "",
        initial_competence: Optional[Dict[str, Any]] = None,
    ) -> LearnerProfile:
        """Register a new learner and return its profile.

        ``learner_id`` is caller-supplied and must be unique within the
        engine. ``name`` is an optional display name. ``initial_competence``
        is an optional mapping from skill domain to a competence value: each
        value may be a ``CompetenceLevel`` (or its string name/value), or a
        dict with ``level``/``score``/``evidence`` keys, in which case an
        initial CompetenceAssessment is created for that domain.

        Raises ``KeyError`` if the learner_id is already registered, or
        ``RuntimeError`` if the learner registry is full.
        """
        with self._lock:
            if learner_id in self._learners:
                raise KeyError(f"learner already registered: {learner_id}")
            if len(self._learners) >= self.MAX_LEARNERS:
                raise RuntimeError("learner registry is full")
            profile = LearnerProfile(learner_id=learner_id, name=name)
            self._learners[learner_id] = profile
            # Seed initial assessments when a competence mapping is supplied.
            if initial_competence and isinstance(initial_competence, dict):
                for skill_domain, value in initial_competence.items():
                    if isinstance(value, dict):
                        level = _resolve_enum(
                            CompetenceLevel,
                            value.get("level", CompetenceLevel.BEGINNER),
                        )
                        score = _clamp(float(value.get("score", 0.3)))
                        evidence = str(value.get("evidence", ""))
                    else:
                        level = _resolve_enum(CompetenceLevel, value)
                        score = 0.3
                        evidence = ""
                    assessment = CompetenceAssessment(
                        learner_id=learner_id,
                        skill_domain=skill_domain,
                        level=level,
                        score=score,
                        evidence=evidence,
                    )
                    self._assessments[assessment.assessment_id] = assessment
                    profile.assessments.append(assessment.assessment_id)
                    profile.updated_at = _now()
            return profile

    def get_learner(self, learner_id: str) -> Optional[LearnerProfile]:
        """Retrieve a learner profile by id, or ``None`` if absent."""
        with self._lock:
            return self._learners.get(learner_id)

    def list_learners(self) -> List[LearnerProfile]:
        """Return all registered learner profiles."""
        with self._lock:
            return list(self._learners.values())

    # ── Competence Assessment ──────────────────────────────────────

    def assess_competence(
        self,
        learner_id: str,
        skill_domain: str,
        level: CompetenceLevel = CompetenceLevel.BEGINNER,
        score: float = 0.3,
        evidence: str = "",
    ) -> CompetenceAssessment:
        """Record a competence assessment for a learner in a skill domain.

        ``level`` may be passed as a ``CompetenceLevel`` or its string
        name/value. ``score`` is clamped to [0, 1]. The new assessment id is
        appended to the learner's assessment history. Raises ``KeyError`` if
        the learner_id is not registered.
        """
        level = _resolve_enum(CompetenceLevel, level)
        score = _clamp(score)
        with self._lock:
            profile = self._learners.get(learner_id)
            if profile is None:
                raise KeyError(f"learner not found: {learner_id}")
            assessment = CompetenceAssessment(
                learner_id=learner_id,
                skill_domain=skill_domain,
                level=level,
                score=score,
                evidence=evidence,
            )
            self._assessments[assessment.assessment_id] = assessment
            profile.assessments.append(assessment.assessment_id)
            profile.updated_at = _now()
            return assessment

    def get_assessment(self, assessment_id: str) -> Optional[CompetenceAssessment]:
        """Retrieve an assessment by id, or ``None`` if absent."""
        with self._lock:
            return self._assessments.get(assessment_id)

    def list_assessments(
        self,
        learner_id: Optional[str] = None,
        skill_domain: Optional[str] = None,
    ) -> List[CompetenceAssessment]:
        """List assessments, optionally filtered by learner and/or domain.

        Returns an empty list if no assessments match the filters.
        """
        with self._lock:
            results: List[CompetenceAssessment] = []
            for assessment in self._assessments.values():
                if learner_id is not None and assessment.learner_id != learner_id:
                    continue
                if skill_domain is not None and assessment.skill_domain != skill_domain:
                    continue
                results.append(assessment)
            return results

    # ── Session Management ─────────────────────────────────────────

    def create_session(
        self,
        learner_id: str,
        task_description: str,
        skill_domain: str,
        target_level: CompetenceLevel = CompetenceLevel.INTERMEDIATE,
    ) -> ScaffoldingSession:
        """Open a scaffolding session for a learner around a concrete task.

        ``target_level`` may be passed as a ``CompetenceLevel`` or its string
        name/value; it describes the competence level the session aims to
        bring the learner toward. The new session id is appended to the
        learner's session history. Raises ``KeyError`` if the learner_id is
        not registered, or ``RuntimeError`` if the per-learner session cap is
        reached.
        """
        target_level = _resolve_enum(CompetenceLevel, target_level)
        with self._lock:
            profile = self._learners.get(learner_id)
            if profile is None:
                raise KeyError(f"learner not found: {learner_id}")
            if len(profile.sessions) >= self.MAX_SESSIONS_PER_LEARNER:
                raise RuntimeError(
                    f"session cap reached for learner: {learner_id}"
                )
            session = ScaffoldingSession(
                learner_id=learner_id,
                task_description=task_description,
                skill_domain=skill_domain,
                target_level=target_level,
                status="open",
            )
            self._sessions[session.session_id] = session
            profile.sessions.append(session.session_id)
            profile.updated_at = _now()
            return session

    def get_session(self, session_id: str) -> Optional[ScaffoldingSession]:
        """Retrieve a session by id, or ``None`` if absent."""
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(
        self,
        learner_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ScaffoldingSession]:
        """List sessions, optionally filtered by learner and/or status.

        ``status`` is matched against the session's free-form status string.
        Returns an empty list if no sessions match the filters.
        """
        with self._lock:
            results: List[ScaffoldingSession] = []
            for session in self._sessions.values():
                if learner_id is not None and session.learner_id != learner_id:
                    continue
                if status is not None and session.status != status:
                    continue
                results.append(session)
            return results

    # ── Scaffold Lifecycle ─────────────────────────────────────────

    def propose_scaffold(
        self,
        session_id: str,
        level: ScaffoldingLevel,
        strategy: ScaffoldingStrategy,
        content: str,
        fading_trigger: FadingTrigger = FadingTrigger.MASTERY,
    ) -> Scaffold:
        """Propose a new scaffold within a session.

        ``level``, ``strategy`` and ``fading_trigger`` may be passed as their
        enum members or their string names/values. The scaffold is created
        in the PROPOSED status and its id is appended to the session's
        scaffold list. Raises ``KeyError`` if the session_id is not
        registered, or ``RuntimeError`` if the per-session scaffold cap is
        reached.
        """
        level = _resolve_enum(ScaffoldingLevel, level)
        strategy = _resolve_enum(ScaffoldingStrategy, strategy)
        fading_trigger = _resolve_enum(FadingTrigger, fading_trigger)
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"session not found: {session_id}")
            if len(session.scaffolds) >= self.MAX_SCAFFOLDS_PER_SESSION:
                raise RuntimeError(
                    f"scaffold cap reached for session: {session_id}"
                )
            scaffold = Scaffold(
                session_id=session_id,
                level=level,
                strategy=strategy,
                content=content,
                fading_trigger=fading_trigger,
                status=ScaffoldStatus.PROPOSED,
            )
            self._scaffolds[scaffold.scaffold_id] = scaffold
            session.scaffolds.append(scaffold.scaffold_id)
            session.updated_at = _now()
            return scaffold

    def get_scaffold(self, scaffold_id: str) -> Optional[Scaffold]:
        """Retrieve a scaffold by id, or ``None`` if absent."""
        with self._lock:
            return self._scaffolds.get(scaffold_id)

    def list_scaffolds(
        self,
        session_id: Optional[str] = None,
        status: Optional[ScaffoldStatus] = None,
    ) -> List[Scaffold]:
        """List scaffolds, optionally filtered by session and/or status.

        ``status`` may be passed as a ``ScaffoldStatus`` or its string
        name/value. Returns an empty list if no scaffolds match the filters.
        """
        resolved_status: Optional[ScaffoldStatus] = None
        if status is not None:
            resolved_status = _resolve_enum(ScaffoldStatus, status)
        with self._lock:
            results: List[Scaffold] = []
            for scaffold in self._scaffolds.values():
                if session_id is not None and scaffold.session_id != session_id:
                    continue
                if resolved_status is not None and scaffold.status != resolved_status:
                    continue
                results.append(scaffold)
            return results

    def activate_scaffold(self, scaffold_id: str) -> Scaffold:
        """Activate a proposed scaffold.

        Transitions a PROPOSED scaffold to ACTIVE and records the activation
        timestamp. A scaffold already in ACTIVE state is returned unchanged.
        Raises ``KeyError`` if the scaffold_id is not registered, or
        ``RuntimeError`` if the scaffold is in a terminal (WITHDRAWN/FAILED)
        or non-activatable (FADING) state.
        """
        with self._lock:
            scaffold = self._scaffolds.get(scaffold_id)
            if scaffold is None:
                raise KeyError(f"scaffold not found: {scaffold_id}")
            if scaffold.status == ScaffoldStatus.ACTIVE:
                return scaffold
            if scaffold.status != ScaffoldStatus.PROPOSED:
                raise RuntimeError(
                    f"cannot activate scaffold in status {scaffold.status.value}"
                )
            scaffold.status = ScaffoldStatus.ACTIVE
            scaffold.activated_at = _now()
            return scaffold

    def fade_scaffold(self, scaffold_id: str, reason: str = "") -> Scaffold:
        """Begin fading an active scaffold.

        Transitions an ACTIVE scaffold to FADING. A scaffold already in
        FADING state is returned unchanged (the reason is still recorded in
        the scaffold's outcome field for diagnostics). Raises ``KeyError``
        if the scaffold_id is not registered, or ``RuntimeError`` if the
        scaffold is not in ACTIVE or FADING state.
        """
        with self._lock:
            scaffold = self._scaffolds.get(scaffold_id)
            if scaffold is None:
                raise KeyError(f"scaffold not found: {scaffold_id}")
            if scaffold.status == ScaffoldStatus.FADING:
                # Record the additional fading reason alongside any prior note.
                if reason:
                    prior = scaffold.outcome
                    scaffold.outcome = (
                        f"{prior}; fading: {reason}" if prior else f"fading: {reason}"
                    )
                return scaffold
            if scaffold.status != ScaffoldStatus.ACTIVE:
                raise RuntimeError(
                    f"cannot fade scaffold in status {scaffold.status.value}"
                )
            scaffold.status = ScaffoldStatus.FADING
            if reason:
                scaffold.outcome = f"fading: {reason}"
            return scaffold

    def withdraw_scaffold(self, scaffold_id: str, outcome: str = "success") -> Scaffold:
        """Withdraw a scaffold, marking it terminal.

        Transitions a non-terminal scaffold to WITHDRAWN when ``outcome``
        indicates success (the default), or to FAILED when it indicates
        failure. The outcome string is recorded on the scaffold and the
        withdrawal timestamp is set. Raises ``KeyError`` if the scaffold_id
        is not registered, or ``RuntimeError`` if the scaffold is already in
        a terminal state.
        """
        with self._lock:
            scaffold = self._scaffolds.get(scaffold_id)
            if scaffold is None:
                raise KeyError(f"scaffold not found: {scaffold_id}")
            if scaffold.status in (ScaffoldStatus.WITHDRAWN, ScaffoldStatus.FAILED):
                raise RuntimeError(
                    f"scaffold already terminal: {scaffold.status.value}"
                )
            lowered = (outcome or "").lower()
            # Treat any outcome mentioning "fail" as a failure withdrawal.
            is_failure = "fail" in lowered
            scaffold.status = ScaffoldStatus.FAILED if is_failure else ScaffoldStatus.WITHDRAWN
            scaffold.outcome = outcome
            scaffold.withdrawn_at = _now()
            return scaffold

    # ── Fading Plans ───────────────────────────────────────────────

    def create_fading_plan(
        self,
        scaffold_id: str,
        milestones: List[Dict[str, Any]],
    ) -> FadingPlan:
        """Attach a fading plan to a scaffold.

        ``milestones`` is a list of dicts, each with keys ``trigger``
        (a FadingTrigger or its string name/value), ``threshold`` (a numeric
        threshold for the trigger), and ``action`` (a free-form description
        of the fading action). Triggers are normalized to FadingTrigger
        members; thresholds are coerced to float when possible. The plan is
        linked to the scaffold via ``fading_plan_id``.

        Raises ``KeyError`` if the scaffold_id is not registered,
        ``ValueError`` if a milestone trigger cannot be resolved, or
        ``RuntimeError`` if the milestone count exceeds the per-plan cap.
        """
        if milestones is None:
            milestones = []
        if len(milestones) > self.MAX_MILESTONES_PER_PLAN:
            raise RuntimeError(
                f"milestone cap exceeded: {len(milestones)} > {self.MAX_MILESTONES_PER_PLAN}"
            )
        normalized: List[Dict[str, Any]] = []
        for milestone in milestones:
            if not isinstance(milestone, dict):
                raise ValueError("each milestone must be a dict")
            trigger = _resolve_enum(
                FadingTrigger, milestone.get("trigger", FadingTrigger.MASTERY)
            )
            threshold_raw = milestone.get("threshold")
            try:
                threshold = float(threshold_raw) if threshold_raw is not None else None
            except (TypeError, ValueError):
                threshold = threshold_raw
            action = str(milestone.get("action", ""))
            normalized.append(
                {"trigger": trigger, "threshold": threshold, "action": action}
            )
        with self._lock:
            scaffold = self._scaffolds.get(scaffold_id)
            if scaffold is None:
                raise KeyError(f"scaffold not found: {scaffold_id}")
            # Replace any existing plan for this scaffold.
            existing_plan_id = self._scaffold_plan_index.get(scaffold_id)
            if existing_plan_id is not None:
                self._fading_plans.pop(existing_plan_id, None)
            plan = FadingPlan(
                scaffold_id=scaffold_id,
                milestones=normalized,
                current_step=0,
            )
            self._fading_plans[plan.plan_id] = plan
            self._scaffold_plan_index[scaffold_id] = plan.plan_id
            scaffold.fading_plan_id = plan.plan_id
            return plan

    def get_fading_plan(self, scaffold_id: str) -> Optional[FadingPlan]:
        """Retrieve the fading plan attached to a scaffold, if any.

        Returns ``None`` if the scaffold has no fading plan or is not
        registered.
        """
        with self._lock:
            plan_id = self._scaffold_plan_index.get(scaffold_id)
            if plan_id is None:
                return None
            return self._fading_plans.get(plan_id)

    # ── Outcomes & Statistics ──────────────────────────────────────

    def record_outcome(
        self,
        session_id: str,
        success: bool = True,
        feedback: str = "",
    ) -> ScaffoldingSession:
        """Record an outcome for a scaffolding session.

        Appends an outcome dict (with ``success``, ``feedback``, and a
        timestamp) to the session's outcome history and updates the
        session's status string: "completed" on success, "struggling" on
        failure. Raises ``KeyError`` if the session_id is not registered.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"session not found: {session_id}")
            entry: Dict[str, Any] = {
                "success": bool(success),
                "feedback": feedback,
                "recorded_at": _now(),
            }
            session.outcomes.append(entry)
            session.status = "completed" if success else "struggling"
            session.updated_at = _now()
            return session

    def get_stats(self) -> ScaffoldingStats:
        """Compute aggregate statistics over the current engine state.

        Counts learners, sessions, scaffolds, active scaffolds, and
        withdrawn scaffolds; tallies scaffolds by level, strategy, and
        status. The breakdown dicts are keyed by the enum ``.value``
        strings.
        """
        with self._lock:
            total_learners = len(self._learners)
            total_sessions = len(self._sessions)
            total_scaffolds = len(self._scaffolds)
            active = 0
            withdrawn = 0
            by_level: Dict[str, int] = {}
            by_strategy: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            for scaffold in self._scaffolds.values():
                level_key = scaffold.level.value
                strategy_key = scaffold.strategy.value
                status_key = scaffold.status.value
                by_level[level_key] = by_level.get(level_key, 0) + 1
                by_strategy[strategy_key] = by_strategy.get(strategy_key, 0) + 1
                by_status[status_key] = by_status.get(status_key, 0) + 1
                if scaffold.status == ScaffoldStatus.ACTIVE:
                    active += 1
                elif scaffold.status == ScaffoldStatus.WITHDRAWN:
                    withdrawn += 1
            return ScaffoldingStats(
                total_learners=total_learners,
                total_sessions=total_sessions,
                total_scaffolds=total_scaffolds,
                active_scaffolds=active,
                withdrawn_scaffolds=withdrawn,
                by_level=by_level,
                by_strategy=by_strategy,
                by_status=by_status,
            )

    # ── Maintenance ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all engine state. Intended for tests."""
        with self._lock:
            self._learners.clear()
            self._assessments.clear()
            self._sessions.clear()
            self._scaffolds.clear()
            self._fading_plans.clear()
            self._scaffold_plan_index.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveScaffolding] = None
_engine_lock = threading.Lock()


def get_scaffolding_engine() -> AgentCognitiveScaffolding:
    """Get or create the singleton ``AgentCognitiveScaffolding`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveScaffolding()
        return _engine


def reset_scaffolding_engine() -> None:
    """Reset the singleton ``AgentCognitiveScaffolding`` instance to ``None``.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_scaffolding_engine`` call creates a
    fresh instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
