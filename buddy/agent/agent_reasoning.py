"""
Buddy Agent Reasoning Engine - Structured chain-of-thought reasoning.

Provides the agent with a systematic reasoning framework inspired by
cognitive science principles. Supports multiple reasoning strategies
including chain-of-thought, tree-of-thought, and step-back reasoning.
Tracks the full reasoning trace for transparency and auditability.

Key capabilities:
- Chain-of-thought decomposition with explicit intermediate steps
- Tree-of-thought exploration with branching and backtracking
- Hypothesis generation, testing, and refinement
- Step-back reasoning for high-level abstraction
- Reasoning trace with confidence scoring per step
- Self-consistency verification across reasoning paths
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ReasoningStrategy(str, Enum):
    """Available reasoning strategies."""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    STEP_BACK = "step_back"
    ANALOGICAL = "analogical"
    DECOMPOSITION = "decomposition"
    SELF_CONSISTENCY = "self_consistency"
    CONTRASTIVE = "contrastive"


class StepStatus(str, Enum):
    """Status of a reasoning step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    REVISED = "revised"


class HypothesisStatus(str, Enum):
    """Status of a hypothesis in the reasoning process."""
    PROPOSED = "proposed"
    TESTING = "testing"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    REFINED = "refined"


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_id: str
    step_number: int
    content: str
    status: StepStatus = StepStatus.PENDING
    confidence: float = 0.5
    parent_step_id: str | None = None
    alternative_steps: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


@dataclass
class Hypothesis:
    """A hypothesis generated during reasoning."""
    hypothesis_id: str
    statement: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = 0.5
    supporting_steps: list[str] = field(default_factory=list)
    contradicting_steps: list[str] = field(default_factory=list)
    test_results: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class ReasoningTrace:
    """Complete trace of a reasoning session."""
    trace_id: str
    agent_id: str
    query: str
    strategy: ReasoningStrategy
    steps: list[ReasoningStep] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    conclusion: str = ""
    overall_confidence: float = 0.0
    alternative_conclusions: list[str] = field(default_factory=list)
    total_steps: int = 0
    rejected_steps: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    @property
    def average_confidence(self) -> float:
        completed = [s for s in self.steps if s.status == StepStatus.COMPLETED]
        if not completed:
            return 0.0
        return sum(s.confidence for s in completed) / len(completed)


class AgentReasoningEngine:
    """Structured reasoning engine for Buddy agents.

    Implements multiple reasoning strategies inspired by cognitive
    science. Agents can decompose complex problems, explore branching
    solutions, generate and test hypotheses, and verify conclusions
    through self-consistency checks.
    """

    def __init__(self):
        self._traces: dict[str, ReasoningTrace] = {}
        self._history: dict[str, list[ReasoningTrace]] = {}
        self._total_traces = 0
        self._total_steps = 0

    def start_reasoning(
        self,
        agent_id: str,
        query: str,
        strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT,
    ) -> ReasoningTrace:
        """Begin a new reasoning session."""
        trace_id = f"reason-{uuid.uuid4().hex[:12]}"
        trace = ReasoningTrace(
            trace_id=trace_id,
            agent_id=agent_id,
            query=query,
            strategy=strategy,
        )
        self._traces[trace_id] = trace

        if agent_id not in self._history:
            self._history[agent_id] = []
        self._history[agent_id].append(trace)
        self._total_traces += 1

        return trace

    def add_step(
        self,
        trace_id: str,
        content: str,
        confidence: float = 0.5,
        parent_step_id: str | None = None,
        evidence: list[str] | None = None,
        assumptions: list[str] | None = None,
    ) -> ReasoningStep | None:
        """Add a reasoning step to the trace."""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        step = ReasoningStep(
            step_id=f"step-{uuid.uuid4().hex[:12]}",
            step_number=len(trace.steps) + 1,
            content=content,
            confidence=confidence,
            parent_step_id=parent_step_id,
            evidence=evidence or [],
            assumptions=assumptions or [],
            status=StepStatus.IN_PROGRESS,
        )
        trace.steps.append(step)
        trace.total_steps += 1
        self._total_steps += 1

        if parent_step_id:
            parent = self._find_step(trace, parent_step_id)
            if parent:
                parent.alternative_steps.append(step.step_id)

        return step

    def complete_step(
        self,
        trace_id: str,
        step_id: str,
        confidence: float | None = None,
        tools_used: list[str] | None = None,
    ) -> ReasoningStep | None:
        """Mark a reasoning step as completed."""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        step = self._find_step(trace, step_id)
        if not step:
            return None

        step.status = StepStatus.COMPLETED
        step.completed_at = time.time()
        if confidence is not None:
            step.confidence = confidence
        if tools_used:
            step.tools_used = tools_used

        return step

    def reject_step(
        self, trace_id: str, step_id: str, reason: str = ""
    ) -> ReasoningStep | None:
        """Reject a reasoning step."""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        step = self._find_step(trace, step_id)
        if not step:
            return None

        step.status = StepStatus.REJECTED
        step.completed_at = time.time()
        trace.rejected_steps += 1

        return step

    def propose_hypothesis(
        self,
        trace_id: str,
        statement: str,
        confidence: float = 0.5,
        supporting_steps: list[str] | None = None,
    ) -> Hypothesis | None:
        """Propose a hypothesis during reasoning."""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        hypothesis = Hypothesis(
            hypothesis_id=f"hyp-{uuid.uuid4().hex[:12]}",
            statement=statement,
            confidence=confidence,
            supporting_steps=supporting_steps or [],
        )
        trace.hypotheses.append(hypothesis)
        return hypothesis

    def test_hypothesis(
        self,
        trace_id: str,
        hypothesis_id: str,
        result: dict,
        confirmed: bool = False,
    ) -> Hypothesis | None:
        """Record a test result for a hypothesis."""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        hyp = self._find_hypothesis(trace, hypothesis_id)
        if not hyp:
            return None

        hyp.status = HypothesisStatus.TESTING
        hyp.test_results.append(result)

        if confirmed:
            hyp.status = HypothesisStatus.CONFIRMED
            hyp.confidence = min(1.0, hyp.confidence + 0.2)
        elif len(hyp.test_results) >= 3:
            # Auto-refute after multiple failed tests
            all_negative = all(
                r.get("passed", True) is False for r in hyp.test_results
            )
            if all_negative:
                hyp.status = HypothesisStatus.REFUTED

        return hyp

    def set_conclusion(
        self,
        trace_id: str,
        conclusion: str,
        confidence: float = 0.5,
        alternatives: list[str] | None = None,
    ) -> ReasoningTrace | None:
        """Set the final conclusion for a reasoning trace."""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        trace.conclusion = conclusion
        trace.overall_confidence = confidence
        trace.alternative_conclusions = alternatives or []
        trace.completed_at = time.time()

        return trace

    def get_trace(self, trace_id: str) -> ReasoningTrace | None:
        """Get a reasoning trace by ID."""
        return self._traces.get(trace_id)

    def get_history(
        self, agent_id: str, limit: int = 20
    ) -> list[ReasoningTrace]:
        """Get reasoning history for an agent."""
        traces = self._history.get(agent_id, [])
        return sorted(traces, key=lambda t: t.created_at, reverse=True)[:limit]

    def reflect_on_trace(
        self,
        trace_id: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Run a reflection session on the reasoning trace.

        Integrates with the Reflection Engine to analyze the reasoning
        process and generate improvement insights.
        """
        trace = self.get_trace(trace_id)
        if not trace:
            return {"error": "Trace not found"}

        from agent.agent_self_reflection import self_reflection_engine, ReflectionDepth

        session = self_reflection_engine.start_session(
            agent_id=agent_id,
            depth=ReflectionDepth.STRUCTURAL,
        )

        for step in trace.steps:
            outcome = "success" if step.status == StepStatus.COMPLETED else "partial"
            self_reflection_engine.record_action(
                session_id=session.session_id,
                action_type="reasoning_step",
                description=step.content[:100],
                outcome=outcome,
                confidence=step.confidence,
                context={"strategy": trace.strategy.value, "step_number": step.step_number},
            )

        insights = self_reflection_engine.reflect(session.session_id)
        plan = session.improvement_plan

        return {
            "trace_id": trace_id,
            "steps_analyzed": len(trace.steps),
            "insights": [
                {
                    "type": i.insight_type.value,
                    "content": i.content,
                    "priority": i.priority.value,
                    "suggested_action": i.suggested_action,
                }
                for i in insights
            ],
            "improvement_plan": plan,
            "overall_score": session.overall_score,
            "summary": session.summary,
        }

    def get_stats(self, agent_id: str | None = None) -> dict:
        """Get reasoning engine statistics."""
        if agent_id:
            traces = self._history.get(agent_id, [])
            strategies = {}
            for t in traces:
                s = t.strategy.value
                strategies[s] = strategies.get(s, 0) + 1
            return {
                "agent_id": agent_id,
                "total_traces": len(traces),
                "total_steps": sum(t.total_steps for t in traces),
                "total_hypotheses": sum(len(t.hypotheses) for t in traces),
                "average_confidence": (
                    sum(t.overall_confidence for t in traces if t.overall_confidence > 0)
                    / max(1, sum(1 for t in traces if t.overall_confidence > 0))
                ),
                "strategies_used": strategies,
            }

        return {
            "total_traces": self._total_traces,
            "total_steps": self._total_steps,
            "active_agents": len(self._history),
        }

    def _find_step(
        self, trace: ReasoningTrace, step_id: str
    ) -> ReasoningStep | None:
        for step in trace.steps:
            if step.step_id == step_id:
                return step
        return None

    def _find_hypothesis(
        self, trace: ReasoningTrace, hypothesis_id: str
    ) -> Hypothesis | None:
        for hyp in trace.hypotheses:
            if hyp.hypothesis_id == hypothesis_id:
                return hyp
        return None


# Global singleton
reasoning_engine = AgentReasoningEngine()