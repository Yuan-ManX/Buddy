"""Agent Hypothesis Engine — structured reasoning with hypothesis generation, testing, and refinement.

Implements a scientific-method reasoning cycle: observe → hypothesize → test → validate → refine.
Supports multiple hypothesis strategies, evidence-based scoring, and iterative refinement loops.
"""

from __future__ import annotations
import uuid
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HypothesisStatus(Enum):
    """Lifecycle states of a hypothesis."""
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    REFINED = "refined"
    MERGED = "merged"


class EvidenceType(Enum):
    """Types of evidence collected during hypothesis testing."""
    OBSERVATION = "observation"
    DEDUCTION = "deduction"
    COUNTER_EXAMPLE = "counter_example"
    CORROBORATION = "corroboration"
    EXPERIMENTAL = "experimental"
    ANALOGICAL = "analogical"


class TestOutcome(Enum):
    """Outcome of a hypothesis test."""
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    PARTIAL = "partial"


@dataclass
class Evidence:
    """A piece of evidence supporting or refuting a hypothesis."""
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    description: str = ""
    weight: float = 0.5
    supports: bool = True
    source: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class HypothesisTest:
    """A test designed to evaluate a hypothesis."""
    test_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    expected_result: str = ""
    actual_result: str = ""
    outcome: TestOutcome = TestOutcome.INCONCLUSIVE
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class Hypothesis:
    """A structured hypothesis with evidence and test history."""
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    statement: str = ""
    rationale: str = ""
    confidence: float = 0.5
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    parent_id: str | None = None
    evidence: list[Evidence] = field(default_factory=list)
    tests: list[HypothesisTest] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    iteration: int = 0


@dataclass
class HypothesisSession:
    """A reasoning session containing multiple hypotheses."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    description: str = ""
    hypotheses: dict[str, Hypothesis] = field(default_factory=dict)
    exploration_log: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class AgentHypothesisEngine:
    """Hypothesis-driven reasoning engine with scientific-method cycle.

    Generates hypotheses from observations, designs tests, collects evidence,
    and iteratively refines conclusions. Implements a structured reasoning
    loop that mirrors the scientific method: observe, hypothesize, test, refine.

    The engine maintains exploration sessions that group related hypotheses
    and tracks the full lifecycle from proposal through validation to refinement.
    """

    # Configuration
    MAX_ITERATIONS: int = 5
    CONFIDENCE_THRESHOLD: float = 0.7
    MIN_EVIDENCE_WEIGHT: float = 0.1
    MAX_ALTERNATIVES: int = 5

    def __init__(self) -> None:
        self._sessions: dict[str, HypothesisSession] = {}
        self._total_sessions: int = 0
        self._total_hypotheses: int = 0
        self._total_tests: int = 0

    def create_session(
        self,
        topic: str,
        description: str = "",
    ) -> HypothesisSession:
        """Create a new hypothesis exploration session.

        Args:
            topic: The topic or question to explore.
            description: Additional context about the exploration.

        Returns:
            A new HypothesisSession ready for hypothesis generation.
        """
        session = HypothesisSession(
            topic=topic,
            description=description,
        )
        self._sessions[session.session_id] = session
        self._total_sessions += 1
        session.exploration_log.append(
            f"Session created: {topic}"
        )
        return session

    def propose(
        self,
        session_id: str,
        statement: str,
        rationale: str = "",
        confidence: float = 0.5,
        parent_id: str | None = None,
    ) -> Hypothesis | None:
        """Propose a new hypothesis in a session.

        Args:
            session_id: The session to add the hypothesis to.
            statement: The hypothesis statement.
            rationale: Reasoning behind the hypothesis.
            confidence: Initial confidence in the hypothesis.
            parent_id: Optional parent hypothesis this refines.

        Returns:
            The created Hypothesis, or None if session not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        hypothesis = Hypothesis(
            statement=statement,
            rationale=rationale,
            confidence=confidence,
            parent_id=parent_id,
        )
        session.hypotheses[hypothesis.hypothesis_id] = hypothesis
        self._total_hypotheses += 1
        session.exploration_log.append(
            f"Hypothesis proposed: {statement[:80]}"
        )
        return hypothesis

    def add_evidence(
        self,
        session_id: str,
        hypothesis_id: str,
        description: str,
        evidence_type: EvidenceType = EvidenceType.OBSERVATION,
        weight: float = 0.5,
        supports: bool = True,
        source: str = "",
    ) -> Evidence | None:
        """Add evidence to a hypothesis.

        Args:
            session_id: The session containing the hypothesis.
            hypothesis_id: The hypothesis to add evidence to.
            description: Description of the evidence.
            evidence_type: Type of evidence.
            weight: Weight/importance of this evidence.
            supports: Whether this evidence supports the hypothesis.
            source: Source of the evidence.

        Returns:
            The created Evidence, or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        hypothesis = session.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None

        evidence = Evidence(
            evidence_type=evidence_type,
            description=description,
            weight=max(self.MIN_EVIDENCE_WEIGHT, min(1.0, weight)),
            supports=supports,
            source=source,
        )
        hypothesis.evidence.append(evidence)
        hypothesis.updated_at = time.time()

        # Update confidence based on evidence
        self._update_confidence(hypothesis)

        session.exploration_log.append(
            f"Evidence added to {hypothesis_id}: {description[:60]}"
        )
        return evidence

    def design_test(
        self,
        session_id: str,
        hypothesis_id: str,
        description: str,
        expected_result: str,
    ) -> HypothesisTest | None:
        """Design a test for a hypothesis.

        Args:
            session_id: The session containing the hypothesis.
            hypothesis_id: The hypothesis to test.
            description: Test description.
            expected_result: Expected outcome if hypothesis is correct.

        Returns:
            The created HypothesisTest, or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        hypothesis = session.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None

        test = HypothesisTest(
            description=description,
            expected_result=expected_result,
        )
        hypothesis.tests.append(test)
        hypothesis.status = HypothesisStatus.TESTING
        hypothesis.updated_at = time.time()
        self._total_tests += 1

        session.exploration_log.append(
            f"Test designed for {hypothesis_id}: {description[:60]}"
        )
        return test

    def run_test(
        self,
        session_id: str,
        hypothesis_id: str,
        test_id: str,
        actual_result: str,
        outcome: TestOutcome = TestOutcome.PASS,
        confidence: float = 0.5,
    ) -> HypothesisTest | None:
        """Record the result of running a test.

        Args:
            session_id: The session containing the hypothesis.
            hypothesis_id: The hypothesis being tested.
            test_id: The test to record results for.
            actual_result: What actually happened.
            outcome: The test outcome.
            confidence: Confidence in the test result.

        Returns:
            The updated HypothesisTest, or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        hypothesis = session.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None

        for test in hypothesis.tests:
            if test.test_id == test_id:
                test.actual_result = actual_result
                test.outcome = outcome
                test.confidence = confidence
                test.timestamp = time.time()

                # Update hypothesis status based on test outcome
                self._evaluate_hypothesis(hypothesis)
                hypothesis.updated_at = time.time()

                session.exploration_log.append(
                    f"Test {test_id} for {hypothesis_id}: {outcome.value}"
                )
                return test
        return None

    def refine(
        self,
        session_id: str,
        hypothesis_id: str,
        new_statement: str,
        new_rationale: str = "",
    ) -> Hypothesis | None:
        """Refine a hypothesis based on evidence and test results.

        Creates a refined version of the hypothesis, marking the original
        as refined and linking the new one as its successor.

        Args:
            session_id: The session containing the hypothesis.
            hypothesis_id: The hypothesis to refine.
            new_statement: The refined statement.
            new_rationale: Updated rationale.

        Returns:
            The new refined Hypothesis, or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        original = session.hypotheses.get(hypothesis_id)
        if not original:
            return None

        original.status = HypothesisStatus.REFINED
        original.updated_at = time.time()

        refined = Hypothesis(
            statement=new_statement,
            rationale=new_rationale,
            confidence=self._compute_confidence(original) * 0.9,
            parent_id=hypothesis_id,
            iteration=original.iteration + 1,
        )
        session.hypotheses[refined.hypothesis_id] = refined
        self._total_hypotheses += 1

        original.alternatives.append(refined.hypothesis_id)
        session.exploration_log.append(
            f"Hypothesis {hypothesis_id} refined to {refined.hypothesis_id}"
        )
        return refined

    def evaluate(
        self,
        session_id: str,
        hypothesis_id: str,
    ) -> dict[str, Any] | None:
        """Evaluate a hypothesis and return its current status.

        Args:
            session_id: The session containing the hypothesis.
            hypothesis_id: The hypothesis to evaluate.

        Returns:
            Evaluation summary dict, or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        hypothesis = session.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None

        supporting = [e for e in hypothesis.evidence if e.supports]
        refuting = [e for e in hypothesis.evidence if not e.supports]
        passed_tests = [t for t in hypothesis.tests if t.outcome == TestOutcome.PASS]
        failed_tests = [t for t in hypothesis.tests if t.outcome == TestOutcome.FAIL]

        return {
            "hypothesis_id": hypothesis.hypothesis_id,
            "statement": hypothesis.statement,
            "status": hypothesis.status.value,
            "confidence": hypothesis.confidence,
            "iteration": hypothesis.iteration,
            "evidence_count": len(hypothesis.evidence),
            "supporting_evidence": len(supporting),
            "refuting_evidence": len(refuting),
            "tests_run": len(hypothesis.tests),
            "tests_passed": len(passed_tests),
            "tests_failed": len(failed_tests),
            "evidence_score": self._compute_evidence_score(hypothesis),
            "test_score": self._compute_test_score(hypothesis),
            "overall_score": self._compute_confidence(hypothesis),
        }

    def compare(
        self,
        session_id: str,
        hypothesis_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Compare multiple hypotheses in a session.

        Args:
            session_id: The session to compare hypotheses in.
            hypothesis_ids: Specific hypotheses to compare. All if None.

        Returns:
            List of evaluation summaries sorted by overall score.
        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        ids = hypothesis_ids or list(session.hypotheses.keys())
        evaluations = []
        for hid in ids:
            eval_result = self.evaluate(session_id, hid)
            if eval_result:
                evaluations.append(eval_result)

        evaluations.sort(key=lambda x: x["overall_score"], reverse=True)
        return evaluations

    def get_session(self, session_id: str) -> HypothesisSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        status_counts: dict[str, int] = {}
        for session in self._sessions.values():
            for h in session.hypotheses.values():
                status_counts[h.status.value] = status_counts.get(h.status.value, 0) + 1

        return {
            "total_sessions": self._total_sessions,
            "total_hypotheses": self._total_hypotheses,
            "total_tests": self._total_tests,
            "active_sessions": len(self._sessions),
            "status_distribution": status_counts,
            "avg_confidence": round(
                sum(
                    h.confidence
                    for s in self._sessions.values()
                    for h in s.hypotheses.values()
                ) / max(self._total_hypotheses, 1),
                3,
            ),
            "avg_iterations": round(
                sum(
                    h.iteration
                    for s in self._sessions.values()
                    for h in s.hypotheses.values()
                ) / max(self._total_hypotheses, 1),
                3,
            ),
        }

    def reset(self) -> None:
        """Reset the engine to initial state."""
        self._sessions.clear()
        self._total_sessions = 0
        self._total_hypotheses = 0
        self._total_tests = 0

    # ── Private helpers ──

    def _update_confidence(self, hypothesis: Hypothesis) -> None:
        """Update hypothesis confidence based on accumulated evidence."""
        hypothesis.confidence = self._compute_confidence(hypothesis)

    def _compute_evidence_score(self, hypothesis: Hypothesis) -> float:
        """Compute a score from evidence."""
        if not hypothesis.evidence:
            return 0.5
        total_weight = sum(e.weight for e in hypothesis.evidence)
        if total_weight == 0:
            return 0.5
        support_weight = sum(e.weight for e in hypothesis.evidence if e.supports)
        return support_weight / total_weight

    def _compute_test_score(self, hypothesis: Hypothesis) -> float:
        """Compute a score from test results."""
        if not hypothesis.tests:
            return 0.5
        passed = sum(1 for t in hypothesis.tests if t.outcome == TestOutcome.PASS)
        return passed / len(hypothesis.tests)

    def _compute_confidence(self, hypothesis: Hypothesis) -> float:
        """Compute overall confidence combining evidence and tests."""
        evidence_score = self._compute_evidence_score(hypothesis)
        test_score = self._compute_test_score(hypothesis)

        if not hypothesis.evidence and not hypothesis.tests:
            return hypothesis.confidence

        if hypothesis.evidence and hypothesis.tests:
            return round((evidence_score * 0.6 + test_score * 0.4), 3)

        if hypothesis.evidence:
            return round(evidence_score, 3)

        return round(test_score, 3)

    def _evaluate_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Evaluate hypothesis status based on evidence and tests."""
        score = self._compute_confidence(hypothesis)
        hypothesis.confidence = score

        if score >= self.CONFIDENCE_THRESHOLD:
            hypothesis.status = HypothesisStatus.SUPPORTED
        elif score <= 0.3:
            if any(t.outcome == TestOutcome.FAIL for t in hypothesis.tests):
                hypothesis.status = HypothesisStatus.REFUTED
            else:
                hypothesis.status = HypothesisStatus.PROPOSED


# ── Singleton accessors ──

_hypothesis_engine: AgentHypothesisEngine | None = None


def get_hypothesis_engine() -> AgentHypothesisEngine:
    """Get or create the singleton hypothesis engine."""
    global _hypothesis_engine
    if _hypothesis_engine is None:
        _hypothesis_engine = AgentHypothesisEngine()
    return _hypothesis_engine


def reset_hypothesis_engine() -> None:
    """Reset the singleton hypothesis engine."""
    global _hypothesis_engine
    if _hypothesis_engine is not None:
        _hypothesis_engine.reset()
    _hypothesis_engine = None