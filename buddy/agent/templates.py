"""Buddy Workflow Templates — pre-built task workflows for rapid agent deployment

Provides a catalog of reusable task templates that agents can instantiate
immediately, covering common workflows across research, engineering, strategy,
content creation, and analysis domains.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowStep:
    """A single step in a workflow template."""
    id: str
    title: str
    description: str
    skill: str | None = None
    depends_on: list[str] = field(default_factory=list)
    timeout_seconds: int = 300


@dataclass
class WorkflowTemplate:
    """A reusable workflow template."""
    id: str
    name: str
    category: str
    description: str
    icon: str
    steps: list[WorkflowStep]
    estimated_tokens: int = 0
    tags: list[str] = field(default_factory=list)


class TemplateRegistry:
    """Registry of pre-built workflow templates."""

    def __init__(self):
        self._templates: dict[str, WorkflowTemplate] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register the default workflow templates."""
        # Research Deep Dive
        self._register(WorkflowTemplate(
            id="research-deep-dive",
            name="Deep Research",
            category="research",
            description="Comprehensive research on any topic with multi-source analysis",
            icon="search",
            tags=["research", "analysis", "writing"],
            estimated_tokens=8000,
            steps=[
                WorkflowStep("rd-1", "Topic Decomposition", "Break down the research topic into sub-topics", skill="brainstorm"),
                WorkflowStep("rd-2", "Source Gathering", "Gather relevant information and sources", depends_on=["rd-1"]),
                WorkflowStep("rd-3", "Analysis & Synthesis", "Analyze findings and synthesize insights", depends_on=["rd-2"]),
                WorkflowStep("rd-4", "Report Generation", "Generate comprehensive research report", depends_on=["rd-3"], skill="summarize"),
            ],
        ))

        # Code Review Pipeline
        self._register(WorkflowTemplate(
            id="code-review-pipeline",
            name="Code Review Pipeline",
            category="engineering",
            description="Automated code review with style, security, and architecture analysis",
            icon="code",
            tags=["engineering", "code", "security"],
            estimated_tokens=5000,
            steps=[
                WorkflowStep("cr-1", "Style Check", "Check code style and formatting", skill="code-review"),
                WorkflowStep("cr-2", "Security Scan", "Scan for security vulnerabilities", depends_on=["cr-1"]),
                WorkflowStep("cr-3", "Architecture Review", "Review architecture and design patterns", depends_on=["cr-2"]),
                WorkflowStep("cr-4", "Summary Report", "Generate review summary with recommendations", depends_on=["cr-1", "cr-2", "cr-3"], skill="summarize"),
            ],
        ))

        # Content Strategy
        self._register(WorkflowTemplate(
            id="content-strategy",
            name="Content Strategy",
            category="strategy",
            description="Develop a complete content strategy for any platform",
            icon="strategy",
            tags=["strategy", "content", "marketing"],
            estimated_tokens=6000,
            steps=[
                WorkflowStep("cs-1", "Audience Analysis", "Analyze target audience and personas"),
                WorkflowStep("cs-2", "Competitor Research", "Research competitor content strategies", depends_on=["cs-1"]),
                WorkflowStep("cs-3", "Content Pillars", "Define content pillars and themes", depends_on=["cs-1"]),
                WorkflowStep("cs-4", "Calendar Planning", "Create content calendar", depends_on=["cs-2", "cs-3"]),
                WorkflowStep("cs-5", "Distribution Plan", "Plan distribution channels and schedule", depends_on=["cs-4"]),
            ],
        ))

        # Data Analysis Report
        self._register(WorkflowTemplate(
            id="data-analysis",
            name="Data Analysis Report",
            category="research",
            description="Analyze data and generate insights with visualizations",
            icon="chart",
            tags=["data", "analysis", "reporting"],
            estimated_tokens=7000,
            steps=[
                WorkflowStep("da-1", "Data Understanding", "Explore and understand data structure"),
                WorkflowStep("da-2", "Statistical Analysis", "Perform statistical analysis", depends_on=["da-1"]),
                WorkflowStep("da-3", "Pattern Discovery", "Discover patterns and trends", depends_on=["da-2"]),
                WorkflowStep("da-4", "Insight Generation", "Generate actionable insights", depends_on=["da-3"]),
                WorkflowStep("da-5", "Report Drafting", "Draft analysis report with visualizations", depends_on=["da-4"], skill="summarize"),
            ],
        ))

        # Project Planning
        self._register(WorkflowTemplate(
            id="project-planning",
            name="Project Planning",
            category="strategy",
            description="Create comprehensive project plan with milestones and timelines",
            icon="plan",
            tags=["project", "planning", "management"],
            estimated_tokens=4500,
            steps=[
                WorkflowStep("pp-1", "Requirements Gathering", "Define project requirements and scope"),
                WorkflowStep("pp-2", "Task Decomposition", "Break down into tasks and subtasks", depends_on=["pp-1"]),
                WorkflowStep("pp-3", "Timeline Estimation", "Estimate timelines for each task", depends_on=["pp-2"]),
                WorkflowStep("pp-4", "Risk Assessment", "Identify risks and mitigation plans", depends_on=["pp-2"]),
                WorkflowStep("pp-5", "Plan Compilation", "Compile final project plan document", depends_on=["pp-3", "pp-4"], skill="summarize"),
            ],
        ))

        # Translation Pipeline
        self._register(WorkflowTemplate(
            id="translation-pipeline",
            name="Multi-language Translation",
            category="content",
            description="Translate content into multiple languages with quality review",
            icon="translate",
            tags=["content", "translation", "localization"],
            estimated_tokens=3000,
            steps=[
                WorkflowStep("tp-1", "Source Preparation", "Prepare source content for translation"),
                WorkflowStep("tp-2", "Primary Translation", "Translate content using best-fit models"),
                WorkflowStep("tp-3", "Quality Review", "Review translation quality and accuracy", depends_on=["tp-2"]),
                WorkflowStep("tp-4", "Final Polish", "Polish and format final translations", depends_on=["tp-3"]),
            ],
        ))

        # Sentiment & Feedback Analysis
        self._register(WorkflowTemplate(
            id="sentiment-analysis",
            name="Sentiment & Feedback Analysis",
            category="analysis",
            description="Analyze user feedback and sentiment from multiple channels",
            icon="feedback",
            tags=["analysis", "sentiment", "feedback"],
            estimated_tokens=4000,
            steps=[
                WorkflowStep("sa-1", "Data Collection", "Collect feedback from various sources"),
                WorkflowStep("sa-2", "Sentiment Scoring", "Score sentiment for each feedback item", depends_on=["sa-1"], skill="sentiment"),
                WorkflowStep("sa-3", "Theme Extraction", "Extract common themes and concerns", depends_on=["sa-2"]),
                WorkflowStep("sa-4", "Report Generation", "Generate sentiment analysis report", depends_on=["sa-3"], skill="summarize"),
            ],
        ))

        # Document Generation
        self._register(WorkflowTemplate(
            id="document-generation",
            name="Formal Document Generation",
            category="content",
            description="Generate formal documents: reports, proposals, whitepapers",
            icon="document",
            tags=["content", "writing", "document"],
            estimated_tokens=5500,
            steps=[
                WorkflowStep("dg-1", "Outline Creation", "Create document outline and structure"),
                WorkflowStep("dg-2", "Section Drafting", "Draft each section with content", depends_on=["dg-1"]),
                WorkflowStep("dg-3", "Data Integration", "Integrate data, charts and references", depends_on=["dg-2"]),
                WorkflowStep("dg-4", "Review & Polish", "Review for consistency and polish", depends_on=["dg-3"], skill="code-review"),
            ],
        ))

        # SEO Optimization
        self._register(WorkflowTemplate(
            id="seo-optimization",
            name="SEO Content Optimization",
            category="marketing",
            description="Optimize content for search engines with keyword analysis",
            icon="seo",
            tags=["marketing", "seo", "content"],
            estimated_tokens=3500,
            steps=[
                WorkflowStep("so-1", "Keyword Research", "Research relevant keywords and phrases", skill="keyword-extract"),
                WorkflowStep("so-2", "Content Audit", "Audit existing content for SEO gaps", depends_on=["so-1"]),
                WorkflowStep("so-3", "Optimization Plan", "Create optimization recommendations", depends_on=["so-2"]),
                WorkflowStep("so-4", "Final Report", "Compile SEO optimization report", depends_on=["so-3"], skill="summarize"),
            ],
        ))

    def _register(self, template: WorkflowTemplate):
        self._templates[template.id] = template

    def get(self, template_id: str) -> WorkflowTemplate | None:
        return self._templates.get(template_id)

    def list_by_category(self, category: str) -> list[dict]:
        return [
            {
                "id": t.id, "name": t.name, "category": t.category,
                "description": t.description, "icon": t.icon,
                "estimated_tokens": t.estimated_tokens, "steps_count": len(t.steps),
                "tags": t.tags,
            }
            for t in self._templates.values() if t.category == category
        ]

    def list_all(self) -> list[dict]:
        return [
            {
                "id": t.id, "name": t.name, "category": t.category,
                "description": t.description, "icon": t.icon,
                "estimated_tokens": t.estimated_tokens, "steps_count": len(t.steps),
                "tags": t.tags,
            }
            for t in self._templates.values()
        ]

    def get_categories(self) -> list[str]:
        return sorted(set(t.category for t in self._templates.values()))

    def instantiate_as_plan(self, template_id: str) -> dict | None:
        """Convert a template into an executable plan definition."""
        template = self._templates.get(template_id)
        if not template:
            return None
        return {
            "template_id": template.id,
            "name": template.name,
            "category": template.category,
            "description": template.description,
            "estimated_tokens": template.estimated_tokens,
            "steps": [
                {
                    "id": s.id, "title": s.title, "description": s.description,
                    "skill": s.skill, "depends_on": s.depends_on,
                    "timeout_seconds": s.timeout_seconds,
                }
                for s in template.steps
            ],
        }


# Global template registry
template_registry = TemplateRegistry()