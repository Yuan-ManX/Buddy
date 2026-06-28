"""Agent Skill Forge — autonomous skill creation, testing, and evolution system.

The forge allows an agent to crystallize reusable skills from experience,
validate them against baselines through structured tests, and evolve them
over time as more evidence is gathered. Each skill progresses through a
lifecycle: draft -> testing -> active -> (deprecated|retired), while its
evolution stage tracks maturity: created -> tested -> refined -> validated
-> deployed.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enums ──


class SkillOrigin(Enum):
    """How a skill came into existence."""
    EXPERIENCE = "experience"
    OBSERVATION = "observation"
    SYNTHESIS = "synthesis"
    USER_DEFINED = "user_defined"


class SkillStatus(Enum):
    """Lifecycle status of a skill candidate."""
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class TestStatus(Enum):
    """Outcome state of a skill test."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EvolutionStage(Enum):
    """Maturity stage of a skill within the evolution pipeline."""
    CREATED = "created"
    TESTED = "tested"
    REFINED = "refined"
    VALIDATED = "validated"
    DEPLOYED = "deployed"


# ── Data Classes ──


@dataclass
class SkillCandidate:
    """A skill proposal created by the agent.

    Attributes:
        skill_id: Unique identifier for the skill.
        name: Human-readable name.
        description: What the skill does and when to use it.
        trigger_conditions: Conditions that should activate the skill.
        procedure: Ordered steps the skill performs.
        pitfalls: Known failure modes to avoid.
        verification: How to verify the skill succeeded.
        origin: How the skill was created.
        status: Current lifecycle status.
        evolution_stage: Current maturity stage.
        created_at: Creation timestamp (unix seconds).
        updated_at: Last update timestamp (unix seconds).
        version: Monotonically increasing version number.
        test_results: Tests executed against this skill.
        success_count: Number of passing test executions.
        failure_count: Number of failing test executions.
        confidence_score: Confidence in the skill (0.0 to 1.0).
    """
    skill_id: str
    name: str
    description: str
    trigger_conditions: list[str]
    procedure: list[str]
    pitfalls: list[str]
    verification: str
    origin: SkillOrigin
    status: SkillStatus = SkillStatus.DRAFT
    evolution_stage: EvolutionStage = EvolutionStage.CREATED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    test_results: list[SkillTest] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    confidence_score: float = 0.0


@dataclass
class SkillTest:
    """A single test designed to validate a skill against a baseline.

    Attributes:
        test_id: Unique identifier for the test.
        skill_id: The skill being tested.
        test_prompt: The prompt that triggers the skill under test.
        expected_behavior: What the skill should do.
        actual_behavior: What the skill actually did (filled after running).
        baseline_score: Reference score to compare against.
        skill_score: Score achieved by the skill.
        status: Current state of the test.
        duration_ms: Execution duration in milliseconds.
        created_at: Creation timestamp (unix seconds).
        notes: Free-form notes about the test run.
    """
    test_id: str
    skill_id: str
    test_prompt: str
    expected_behavior: str
    actual_behavior: str = ""
    baseline_score: float = 0.0
    skill_score: float = 0.0
    status: TestStatus = TestStatus.PENDING
    duration_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    notes: str = ""


@dataclass
class SkillEvolution:
    """A record of one evolution step applied to a skill.

    Attributes:
        evolution_id: Unique identifier for the evolution event.
        skill_id: The skill that was evolved.
        from_version: Version before the evolution.
        to_version: Version after the evolution.
        change_description: What changed and why.
        improvement_delta: Change in confidence score (after - before).
        created_at: When the evolution occurred (unix seconds).
    """
    evolution_id: str
    skill_id: str
    from_version: int
    to_version: int
    change_description: str
    improvement_delta: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class SkillDependency:
    """A dependency edge between two skills.

    Attributes:
        skill_id: The skill that depends on another.
        depends_on_skill_id: The skill being depended upon.
        dependency_type: Nature of the dependency (e.g. "requires").
        created_at: When the dependency was recorded (unix seconds).
    """
    skill_id: str
    depends_on_skill_id: str
    dependency_type: str = "requires"
    created_at: float = field(default_factory=time.time)


# ── Skill Forge ──


class AgentSkillForge:
    """Autonomous skill creation, testing, and evolution engine.

    The forge lets an agent propose skills from experience, design tests
    that compare skill performance against a baseline, and iteratively
    evolve skills as evidence accumulates. Skills move through a lifecycle
    (draft -> testing -> active -> retired) and a maturity pipeline
    (created -> tested -> refined -> validated -> deployed).
    """

    # Configuration
    MAX_SKILLS: int = 200
    MAX_TESTS_PER_SKILL: int = 10
    MIN_CONFIDENCE: float = 0.6
    EVOLUTION_THRESHOLD: float = 0.7

    def __init__(self) -> None:
        self._skills: dict[str, SkillCandidate] = {}
        self._tests: dict[str, SkillTest] = {}
        self._evolutions: dict[str, SkillEvolution] = {}
        self._dependencies: list[SkillDependency] = []
        self._total_tests: int = 0
        self._total_evolutions: int = 0

    # ── Skill lifecycle ──

    def create_skill(
        self,
        name: str,
        description: str,
        trigger_conditions: list[str],
        procedure: list[str],
        pitfalls: list[str] | None = None,
        verification: str = "",
        origin: SkillOrigin = SkillOrigin.EXPERIENCE,
    ) -> SkillCandidate:
        """Create a new skill candidate in draft state.

        Args:
            name: Human-readable skill name.
            description: What the skill does and when to use it.
            trigger_conditions: Conditions that should activate the skill.
            procedure: Ordered steps the skill performs.
            pitfalls: Known failure modes to avoid.
            verification: How to verify the skill succeeded.
            origin: How the skill was created.

        Returns:
            The newly created SkillCandidate.
        """
        if len(self._skills) >= self.MAX_SKILLS:
            raise RuntimeError(
                f"Maximum number of skills reached ({self.MAX_SKILLS})"
            )

        now = time.time()
        skill = SkillCandidate(
            skill_id=f"skill-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            trigger_conditions=list(trigger_conditions),
            procedure=list(procedure),
            pitfalls=list(pitfalls) if pitfalls else [],
            verification=verification,
            origin=origin,
            status=SkillStatus.DRAFT,
            evolution_stage=EvolutionStage.CREATED,
            created_at=now,
            updated_at=now,
            version=1,
        )
        self._skills[skill.skill_id] = skill
        return skill

    def update_skill(
        self,
        skill_id: str,
        name: str | None = None,
        description: str | None = None,
        trigger_conditions: list[str] | None = None,
        procedure: list[str] | None = None,
        pitfalls: list[str] | None = None,
        verification: str | None = None,
    ) -> SkillCandidate | None:
        """Update mutable fields of an existing skill.

        Only provided (non-None) fields are updated. Bumps the updated_at
        timestamp.

        Args:
            skill_id: The skill to update.
            name: New name, if provided.
            description: New description, if provided.
            trigger_conditions: New trigger conditions, if provided.
            procedure: New procedure, if provided.
            pitfalls: New pitfalls, if provided.
            verification: New verification, if provided.

        Returns:
            The updated SkillCandidate, or None if the skill was not found.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        if name is not None:
            skill.name = name
        if description is not None:
            skill.description = description
        if trigger_conditions is not None:
            skill.trigger_conditions = list(trigger_conditions)
        if procedure is not None:
            skill.procedure = list(procedure)
        if pitfalls is not None:
            skill.pitfalls = list(pitfalls)
        if verification is not None:
            skill.verification = verification

        skill.updated_at = time.time()
        return skill

    # ── Testing ──

    def design_test(
        self,
        skill_id: str,
        test_prompt: str,
        expected_behavior: str,
    ) -> SkillTest | None:
        """Design a new test for a skill.

        The test starts in the PENDING state and is attached to the skill's
        test_results. A skill still in DRAFT is moved into the TESTING
        status; skills already active or otherwise advanced keep their
        current status while the new test is added.

        Args:
            skill_id: The skill to design a test for.
            test_prompt: The prompt that triggers the skill under test.
            expected_behavior: What the skill should do.

        Returns:
            The created SkillTest, or None if the skill was not found or
            the per-skill test limit has been reached.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        if len(skill.test_results) >= self.MAX_TESTS_PER_SKILL:
            return None

        test = SkillTest(
            test_id=f"test-{uuid.uuid4().hex[:8]}",
            skill_id=skill_id,
            test_prompt=test_prompt,
            expected_behavior=expected_behavior,
        )
        skill.test_results.append(test)
        self._tests[test.test_id] = test
        self._total_tests += 1

        # Only draft skills enter testing; already-active skills stay active
        # while additional tests are designed against them.
        if skill.status == SkillStatus.DRAFT:
            skill.status = SkillStatus.TESTING
        skill.updated_at = time.time()
        return test

    def run_test(
        self,
        skill_id: str,
        test_id: str,
        actual_behavior: str,
        baseline_score: float = 0.5,
        skill_score: float = 0.7,
        notes: str = "",
    ) -> SkillTest | None:
        """Record the result of running a test against a skill.

        Updates the test with the actual behavior, scores, and outcome
        (PASSED when skill_score >= baseline_score, FAILED otherwise).
        Also updates the owning skill's success/failure counters,
        confidence score, and evolution stage.

        Args:
            skill_id: The skill the test belongs to.
            test_id: The test to record results for.
            actual_behavior: What the skill actually did.
            baseline_score: Reference score to compare against.
            skill_score: Score achieved by the skill.
            notes: Free-form notes about the test run.

        Returns:
            The updated SkillTest, or None if the skill or test was not
            found.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        test = self._tests.get(test_id)
        if test is None or test.skill_id != skill_id:
            return None

        passed = skill_score >= baseline_score
        test.actual_behavior = actual_behavior
        test.baseline_score = baseline_score
        test.skill_score = skill_score
        test.status = TestStatus.PASSED if passed else TestStatus.FAILED
        test.duration_ms = 0.0
        test.notes = notes

        if passed:
            skill.success_count += 1
        else:
            skill.failure_count += 1

        skill.confidence_score = self._compute_confidence(skill)
        skill.evolution_stage = EvolutionStage.TESTED
        skill.updated_at = time.time()

        # Promote to active once enough confidence is established.
        if skill.confidence_score >= self.MIN_CONFIDENCE:
            skill.status = SkillStatus.ACTIVE

        return test

    # ── Evolution ──

    def evolve_skill(
        self,
        skill_id: str,
        change_description: str,
        new_procedure: list[str] | None = None,
        new_pitfalls: list[str] | None = None,
        new_verification: str | None = None,
    ) -> SkillCandidate | None:
        """Evolve a skill to a new version.

        Bumps the skill version, applies any provided procedure/pitfalls/
        verification updates, and records a SkillEvolution entry capturing
        the improvement delta relative to the previous confidence score.
        Skills below the EVOLUTION_THRESHOLD are refined but not validated.

        Args:
            skill_id: The skill to evolve.
            change_description: What changed and why.
            new_procedure: Replacement procedure, if provided.
            new_pitfalls: Replacement pitfalls, if provided.
            new_verification: Replacement verification, if provided.

        Returns:
            The evolved SkillCandidate, or None if the skill was not found.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        previous_confidence = skill.confidence_score
        from_version = skill.version

        if new_procedure is not None:
            skill.procedure = list(new_procedure)
        if new_pitfalls is not None:
            skill.pitfalls = list(new_pitfalls)
        if new_verification is not None:
            skill.verification = new_verification

        skill.version += 1
        skill.evolution_stage = EvolutionStage.REFINED
        if skill.confidence_score >= self.EVOLUTION_THRESHOLD:
            skill.evolution_stage = EvolutionStage.VALIDATED
        skill.updated_at = time.time()

        improvement_delta = round(skill.confidence_score - previous_confidence, 4)
        evolution = SkillEvolution(
            evolution_id=f"evo-{uuid.uuid4().hex[:8]}",
            skill_id=skill_id,
            from_version=from_version,
            to_version=skill.version,
            change_description=change_description,
            improvement_delta=improvement_delta,
        )
        self._evolutions[evolution.evolution_id] = evolution
        self._total_evolutions += 1

        return skill

    # ── Querying ──

    def get_skill(self, skill_id: str) -> SkillCandidate | None:
        """Retrieve a skill by ID.

        Args:
            skill_id: The unique skill identifier.

        Returns:
            The SkillCandidate, or None if not found.
        """
        return self._skills.get(skill_id)

    def list_skills(
        self,
        status: SkillStatus | None = None,
        origin: SkillOrigin | None = None,
    ) -> list[SkillCandidate]:
        """List skills, optionally filtered by status and/or origin.

        Args:
            status: Only return skills with this status, if provided.
            origin: Only return skills with this origin, if provided.

        Returns:
            A list of matching SkillCandidate objects.
        """
        results = list(self._skills.values())
        if status is not None:
            results = [s for s in results if s.status == status]
        if origin is not None:
            results = [s for s in results if s.origin == origin]
        return results

    def get_active_skills(self) -> list[SkillCandidate]:
        """Return all skills currently in the ACTIVE status.

        Returns:
            A list of active SkillCandidate objects.
        """
        return self.list_skills(status=SkillStatus.ACTIVE)

    def retire_skill(self, skill_id: str) -> SkillCandidate | None:
        """Retire a skill, marking it as no longer in use.

        Args:
            skill_id: The skill to retire.

        Returns:
            The retired SkillCandidate, or None if not found.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return None
        skill.status = SkillStatus.RETIRED
        skill.evolution_stage = EvolutionStage.DEPLOYED
        skill.updated_at = time.time()
        return skill

    # ── Dependencies ──

    def add_dependency(
        self,
        skill_id: str,
        depends_on_skill_id: str,
        dependency_type: str = "requires",
    ) -> SkillDependency | None:
        """Record a dependency between two skills.

        Args:
            skill_id: The skill that depends on another.
            depends_on_skill_id: The skill being depended upon.
            dependency_type: Nature of the dependency (e.g. "requires").

        Returns:
            The created SkillDependency, or None if either skill was not
            found or a self-dependency was requested.
        """
        if skill_id not in self._skills:
            return None
        if depends_on_skill_id not in self._skills:
            return None
        if skill_id == depends_on_skill_id:
            return None

        dependency = SkillDependency(
            skill_id=skill_id,
            depends_on_skill_id=depends_on_skill_id,
            dependency_type=dependency_type,
        )
        self._dependencies.append(dependency)
        return dependency

    # ── Statistics ──

    def get_stats(self) -> dict[str, Any]:
        """Compute aggregate statistics about the forge.

        Returns:
            A dictionary with total_skills, active_skills, total_tests,
            total_evolutions, avg_confidence, status_distribution, and
            origin_distribution.
        """
        status_distribution: dict[str, int] = {}
        origin_distribution: dict[str, int] = {}
        confidence_sum = 0.0

        for skill in self._skills.values():
            status_key = skill.status.value
            status_distribution[status_key] = status_distribution.get(status_key, 0) + 1

            origin_key = skill.origin.value
            origin_distribution[origin_key] = origin_distribution.get(origin_key, 0) + 1

            confidence_sum += skill.confidence_score

        total_skills = len(self._skills)
        return {
            "total_skills": total_skills,
            "active_skills": status_distribution.get(SkillStatus.ACTIVE.value, 0),
            "total_tests": self._total_tests,
            "total_evolutions": self._total_evolutions,
            "avg_confidence": round(confidence_sum / total_skills, 3) if total_skills else 0.0,
            "status_distribution": status_distribution,
            "origin_distribution": origin_distribution,
        }

    # ── Reset ──

    def reset(self) -> None:
        """Reset the forge to its initial empty state."""
        self._skills.clear()
        self._tests.clear()
        self._evolutions.clear()
        self._dependencies.clear()
        self._total_tests = 0
        self._total_evolutions = 0

    # ── Private helpers ──

    @staticmethod
    def _compute_confidence(skill: SkillCandidate) -> float:
        """Compute a skill's confidence from its test history.

        Confidence is the fraction of passing tests. A skill with no tests
        retains its existing confidence score.

        Args:
            skill: The skill to score.

        Returns:
            A confidence value between 0.0 and 1.0.
        """
        total = skill.success_count + skill.failure_count
        if total == 0:
            return skill.confidence_score
        return round(skill.success_count / total, 4)


# ── Singleton accessors ──

_skill_forge: AgentSkillForge | None = None


def get_skill_forge() -> AgentSkillForge:
    """Get or create the global skill forge singleton.

    Returns:
        The shared AgentSkillForge instance.
    """
    global _skill_forge
    if _skill_forge is None:
        _skill_forge = AgentSkillForge()
    return _skill_forge


def reset_skill_forge() -> None:
    """Reset the global skill forge singleton.

    Clears any existing instance so the next call to get_skill_forge()
    creates a fresh forge.
    """
    global _skill_forge
    if _skill_forge is not None:
        _skill_forge.reset()
    _skill_forge = None
