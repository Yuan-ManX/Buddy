"""
Buddy Autonomous Research Engine - Self-directed research and investigation.

An autonomous research system that plans, executes, and synthesizes research
tasks. Supports multi-source information gathering, hypothesis generation and
testing, evidence evaluation, and comprehensive report generation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResearchPhase(str, Enum):
    """Phases of the autonomous research process."""
    PLANNING = "planning"
    GATHERING = "gathering"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"
    REPORTING = "reporting"


class SourceType(str, Enum):
    """Types of research sources."""
    DOCUMENT = "document"
    WEB = "web"
    API = "api"
    DATABASE = "database"
    EXPERT = "expert"
    OBSERVATION = "observation"
    EXPERIMENT = "experiment"


class EvidenceQuality(str, Enum):
    """Quality assessment of research evidence."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"
    CONTRADICTORY = "contradictory"


@dataclass
class ResearchSource:
    """A source of information for research."""
    source_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    source_type: SourceType = SourceType.WEB
    content: str = ""
    url: str = ""
    relevance_score: float = 0.0
    credibility_score: float = 0.5
    quality: EvidenceQuality = EvidenceQuality.UNVERIFIED
    key_findings: list[str] = field(default_factory=list)
    retrieved_at: float = field(default_factory=time.time)


@dataclass
class ResearchHypothesis:
    """A hypothesis being tested during research."""
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    statement: str = ""
    confidence: float = 0.5
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    evaluated_at: float | None = None


@dataclass
class ResearchTask:
    """A single research task or sub-task."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    phase: ResearchPhase = ResearchPhase.GATHERING
    status: str = "pending"
    priority: int = 1
    assigned_agent: str = ""
    result: str = ""
    sources_used: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


@dataclass
class ResearchProject:
    """A complete autonomous research project."""
    project_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    research_question: str = ""
    description: str = ""
    hypotheses: list[ResearchHypothesis] = field(default_factory=list)
    tasks: list[ResearchTask] = field(default_factory=list)
    sources: list[ResearchSource] = field(default_factory=list)
    status: str = "created"
    current_phase: ResearchPhase = ResearchPhase.PLANNING
    findings: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


@dataclass
class ResearchReport:
    """The final research report generated from a project."""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    project_id: str = ""
    title: str = ""
    executive_summary: str = ""
    introduction: str = ""
    methodology: str = ""
    findings: list[str] = field(default_factory=list)
    analysis: str = ""
    conclusions: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    sources_count: int = 0
    hypotheses_tested: int = 0
    created_at: float = field(default_factory=time.time)


class AutonomousResearchEngine:
    """Self-directed research and investigation engine.

    Automates the full research lifecycle: planning, multi-source information
    gathering, hypothesis testing, evidence evaluation, and comprehensive
    report generation. Operates autonomously once a research question is defined.
    """

    def __init__(self) -> None:
        self._projects: dict[str, ResearchProject] = {}
        self._reports: list[ResearchReport] = []
        self._total_projects: int = 0
        self._total_reports: int = 0

    # ── Project Management ───────────────────────────────────────

    def create_project(
        self,
        title: str,
        research_question: str,
        description: str = "",
    ) -> ResearchProject:
        """Create a new autonomous research project.

        Args:
            title: Project title.
            research_question: The core research question.
            description: Detailed project description.

        Returns:
            The created ResearchProject.
        """
        project = ResearchProject(
            title=title,
            research_question=research_question,
            description=description,
        )
        self._projects[project.project_id] = project
        self._total_projects += 1
        return project

    def plan_research(self, project_id: str) -> list[ResearchTask]:
        """Generate a research plan with tasks for the project.

        Args:
            project_id: The project ID to plan for.

        Returns:
            List of planned ResearchTask objects.
        """
        project = self._projects.get(project_id)
        if not project:
            return []

        project.current_phase = ResearchPhase.PLANNING

        # Generate research tasks automatically
        tasks = [
            ResearchTask(
                description=f"Background research on: {project.research_question}",
                phase=ResearchPhase.GATHERING,
                priority=1,
            ),
            ResearchTask(
                description=f"Identify key sources for: {project.title}",
                phase=ResearchPhase.GATHERING,
                priority=1,
            ),
            ResearchTask(
                description=f"Analyze collected data for: {project.research_question}",
                phase=ResearchPhase.ANALYSIS,
                priority=2,
            ),
            ResearchTask(
                description=f"Form and test hypotheses for: {project.title}",
                phase=ResearchPhase.ANALYSIS,
                priority=2,
            ),
            ResearchTask(
                description=f"Synthesize findings for: {project.research_question}",
                phase=ResearchPhase.SYNTHESIS,
                priority=3,
            ),
            ResearchTask(
                description=f"Verify conclusions for: {project.title}",
                phase=ResearchPhase.VERIFICATION,
                priority=3,
            ),
            ResearchTask(
                description=f"Generate final report for: {project.research_question}",
                phase=ResearchPhase.REPORTING,
                priority=4,
            ),
        ]

        project.tasks = tasks
        project.status = "planned"
        return tasks

    def add_source(
        self,
        project_id: str,
        title: str,
        content: str,
        source_type: SourceType = SourceType.WEB,
        url: str = "",
        credibility: float = 0.5,
        key_findings: list[str] | None = None,
    ) -> ResearchSource | None:
        """Add a research source to a project.

        Args:
            project_id: The project ID.
            title: Source title.
            content: Source content or summary.
            source_type: Type of source.
            url: Optional URL.
            credibility: Credibility score (0.0-1.0).
            key_findings: Key findings from this source.

        Returns:
            The created ResearchSource or None.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        source = ResearchSource(
            title=title,
            source_type=source_type,
            content=content,
            url=url,
            credibility_score=credibility,
            relevance_score=0.7,
            key_findings=key_findings or [],
        )
        project.sources.append(source)
        project.current_phase = ResearchPhase.GATHERING
        return source

    def add_hypothesis(
        self,
        project_id: str,
        statement: str,
        confidence: float = 0.5,
    ) -> ResearchHypothesis | None:
        """Add a hypothesis to test in the research project.

        Args:
            project_id: The project ID.
            statement: The hypothesis statement.
            confidence: Initial confidence level.

        Returns:
            The created ResearchHypothesis or None.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        hypothesis = ResearchHypothesis(
            statement=statement,
            confidence=confidence,
        )
        project.hypotheses.append(hypothesis)
        return hypothesis

    def evaluate_hypothesis(
        self,
        project_id: str,
        hypothesis_id: str,
        supporting: list[str] | None = None,
        contradicting: list[str] | None = None,
        new_confidence: float | None = None,
        status: str = "evaluated",
    ) -> ResearchHypothesis | None:
        """Evaluate a hypothesis with supporting and contradicting evidence.

        Args:
            project_id: The project ID.
            hypothesis_id: The hypothesis ID.
            supporting: Supporting evidence.
            contradicting: Contradicting evidence.
            new_confidence: Updated confidence level.
            status: New hypothesis status.

        Returns:
            The updated ResearchHypothesis or None.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        for h in project.hypotheses:
            if h.hypothesis_id == hypothesis_id:
                if supporting:
                    h.supporting_evidence.extend(supporting)
                if contradicting:
                    h.contradicting_evidence.extend(contradicting)
                if new_confidence is not None:
                    h.confidence = new_confidence
                h.status = status
                h.evaluated_at = time.time()
                return h
        return None

    def complete_task(
        self,
        project_id: str,
        task_id: str,
        result: str = "",
        sources_used: list[str] | None = None,
    ) -> ResearchTask | None:
        """Mark a research task as completed.

        Args:
            project_id: The project ID.
            task_id: The task ID.
            result: The task result or findings.
            sources_used: Sources used for this task.

        Returns:
            The updated ResearchTask or None.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        for task in project.tasks:
            if task.task_id == task_id:
                task.status = "completed"
                task.result = result
                task.completed_at = time.time()
                if sources_used:
                    task.sources_used = sources_used
                if result:
                    project.findings.append(result)
                return task
        return None

    def add_finding(self, project_id: str, finding: str) -> bool:
        """Add a research finding to the project.

        Args:
            project_id: The project ID.
            finding: The finding to add.

        Returns:
            True if successful, False otherwise.
        """
        project = self._projects.get(project_id)
        if not project:
            return False
        project.findings.append(finding)
        return True

    def generate_report(self, project_id: str) -> ResearchReport | None:
        """Generate a comprehensive research report from the project.

        Args:
            project_id: The project ID.

        Returns:
            The generated ResearchReport or None.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        # Build executive summary
        summary = (
            f"Research on: {project.research_question}\n"
            f"Sources analyzed: {len(project.sources)}\n"
            f"Hypotheses tested: {len(project.hypotheses)}\n"
            f"Key findings: {len(project.findings)}"
        )

        # Build methodology
        methodology = (
            f"Autonomous research methodology:\n"
            f"- Multi-source information gathering ({len(project.sources)} sources)\n"
            f"- Hypothesis-driven analysis ({len(project.hypotheses)} hypotheses)\n"
            f"- Evidence-based evaluation\n"
            f"- Systematic synthesis of findings"
        )

        # Build conclusions
        conclusions: list[str] = []
        for h in project.hypotheses:
            if h.status == "evaluated":
                if h.confidence > 0.7:
                    conclusions.append(f"Supported: {h.statement} (confidence: {h.confidence:.2f})")
                elif h.confidence > 0.4:
                    conclusions.append(f"Partially supported: {h.statement} (confidence: {h.confidence:.2f})")
                else:
                    conclusions.append(f"Not supported: {h.statement} (confidence: {h.confidence:.2f})")

        # Build recommendations
        recommendations = [
            f"Further investigation recommended for: {project.research_question}",
            "Consider additional data sources to strengthen findings",
            "Validate conclusions through peer review",
        ]

        # Compute confidence
        confidences = [h.confidence for h in project.hypotheses if h.status == "evaluated"]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        report = ResearchReport(
            project_id=project_id,
            title=project.title,
            executive_summary=summary,
            introduction=f"Research question: {project.research_question}\n\n{project.description}",
            methodology=methodology,
            findings=project.findings,
            analysis=f"Analysis of {len(project.hypotheses)} hypotheses across {len(project.sources)} sources.",
            conclusions=conclusions,
            recommendations=recommendations,
            limitations=["Sample size limited by available sources", "Automated analysis may miss nuance"],
            confidence_score=avg_confidence,
            sources_count=len(project.sources),
            hypotheses_tested=len([h for h in project.hypotheses if h.status == "evaluated"]),
        )

        project.status = "completed"
        project.current_phase = ResearchPhase.REPORTING
        project.completed_at = time.time()
        self._reports.append(report)
        self._total_reports += 1
        return report

    # ── Query & Stats ────────────────────────────────────────────

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get a project by ID."""
        project = self._projects.get(project_id)
        if not project:
            return None
        return {
            "project_id": project.project_id,
            "title": project.title,
            "research_question": project.research_question,
            "description": project.description,
            "status": project.status,
            "current_phase": project.current_phase.value,
            "hypotheses_count": len(project.hypotheses),
            "tasks_count": len(project.tasks),
            "sources_count": len(project.sources),
            "findings_count": len(project.findings),
            "findings": project.findings,
            "hypotheses": [
                {
                    "hypothesis_id": h.hypothesis_id,
                    "statement": h.statement,
                    "confidence": h.confidence,
                    "status": h.status,
                    "supporting_count": len(h.supporting_evidence),
                    "contradicting_count": len(h.contradicting_evidence),
                }
                for h in project.hypotheses
            ],
            "tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "phase": t.phase.value,
                    "status": t.status,
                    "priority": t.priority,
                    "result": t.result,
                }
                for t in project.tasks
            ],
        }

    def get_stats(self) -> dict[str, Any]:
        """Get research engine statistics."""
        return {
            "total_projects": self._total_projects,
            "total_reports": self._total_reports,
            "active_projects": len([
                p for p in self._projects.values() if p.status not in ("completed",)
            ]),
            "total_sources": sum(len(p.sources) for p in self._projects.values()),
            "total_hypotheses": sum(len(p.hypotheses) for p in self._projects.values()),
            "total_findings": sum(len(p.findings) for p in self._projects.values()),
            "avg_confidence": round(
                sum(r.confidence_score for r in self._reports) / len(self._reports), 3
            ) if self._reports else 0.0,
        }

    def get_recent_reports(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent research reports."""
        return [
            {
                "report_id": r.report_id,
                "title": r.title,
                "executive_summary": r.executive_summary,
                "confidence_score": r.confidence_score,
                "sources_count": r.sources_count,
                "hypotheses_tested": r.hypotheses_tested,
                "conclusions": r.conclusions,
                "recommendations": r.recommendations,
            }
            for r in self._reports[-limit:]
        ]

    def reset(self) -> None:
        """Reset the research engine to initial state."""
        self._projects.clear()
        self._reports.clear()
        self._total_projects = 0
        self._total_reports = 0


# ── Singleton Access ───────────────────────────────────────────────

_research_engine: AutonomousResearchEngine | None = None


def get_research_engine() -> AutonomousResearchEngine:
    """Get or create the singleton research engine instance."""
    global _research_engine
    if _research_engine is None:
        _research_engine = AutonomousResearchEngine()
    return _research_engine


def reset_research_engine() -> None:
    """Reset the singleton research engine."""
    global _research_engine
    if _research_engine:
        _research_engine.reset()
    _research_engine = None