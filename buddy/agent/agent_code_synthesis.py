"""Agent Code Synthesis — autonomous code generation pipeline from natural language specifications.

Implements a complete code generation lifecycle: specification analysis,
architecture planning, code generation, testing, and refinement. Supports
multiple languages and generates production-ready code with documentation.
"""

from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SynthesisStage(Enum):
    """Stages of the code synthesis pipeline."""
    SPECIFICATION = "specification"
    ARCHITECTURE = "architecture"
    GENERATION = "generation"
    TESTING = "testing"
    REFINEMENT = "refinement"
    COMPLETE = "complete"


class LanguageTarget(Enum):
    """Target programming languages for code generation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    SHELL = "shell"


class TestStatus(Enum):
    """Status of generated tests."""
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    SKIPPED = "skipped"


@dataclass
class CodeComponent:
    """A generated code component."""
    component_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    language: LanguageTarget = LanguageTarget.PYTHON
    code: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    test_code: str = ""
    test_status: TestStatus = TestStatus.PENDING
    version: int = 1


@dataclass
class ArchitecturePlan:
    """Architecture plan for a code synthesis project."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    components: list[str] = field(default_factory=list)
    data_flow: str = ""
    entry_point: str = ""
    patterns: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class SynthesisProject:
    """A complete code synthesis project."""
    project_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    specification: str = ""
    language: LanguageTarget = LanguageTarget.PYTHON
    stage: SynthesisStage = SynthesisStage.SPECIFICATION
    architecture: ArchitecturePlan | None = None
    components: dict[str, CodeComponent] = field(default_factory=dict)
    changelog: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class AgentCodeSynthesis:
    """Autonomous code generation pipeline from natural language.

    Transforms natural language specifications into production-ready code
    through a structured pipeline: specification analysis → architecture
    planning → component generation → testing → refinement.

    The pipeline manages the full lifecycle and maintains component versioning
    to support iterative improvement cycles.
    """

    MAX_COMPONENTS: int = 50
    MAX_REFINEMENTS: int = 5

    def __init__(self) -> None:
        self._projects: dict[str, SynthesisProject] = {}
        self._total_projects: int = 0
        self._total_components: int = 0

    def create_project(
        self,
        name: str,
        specification: str,
        language: LanguageTarget = LanguageTarget.PYTHON,
    ) -> SynthesisProject:
        """Create a new code synthesis project.

        Args:
            name: Project name.
            specification: Natural language specification.
            language: Target programming language.

        Returns:
            A new SynthesisProject ready for the pipeline.
        """
        project = SynthesisProject(
            name=name,
            specification=specification,
            language=language,
        )
        self._projects[project.project_id] = project
        self._total_projects += 1
        project.changelog.append(f"Project created: {name}")
        return project

    def plan_architecture(
        self,
        project_id: str,
        components: list[str],
        data_flow: str = "",
        entry_point: str = "",
        patterns: list[str] | None = None,
        rationale: str = "",
    ) -> ArchitecturePlan | None:
        """Define the architecture plan for a project.

        Args:
            project_id: The project to plan.
            components: List of component names to generate.
            data_flow: How data flows between components.
            entry_point: The main entry point component.
            patterns: Architecture patterns used.
            rationale: Why this architecture was chosen.

        Returns:
            The ArchitecturePlan, or None if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        plan = ArchitecturePlan(
            components=components,
            data_flow=data_flow,
            entry_point=entry_point,
            patterns=patterns or [],
            rationale=rationale,
        )
        project.architecture = plan
        project.stage = SynthesisStage.ARCHITECTURE
        project.changelog.append(f"Architecture planned: {len(components)} components")
        return plan

    def generate_component(
        self,
        project_id: str,
        name: str,
        code: str,
        description: str = "",
        dependencies: list[str] | None = None,
        test_code: str = "",
    ) -> CodeComponent | None:
        """Generate a code component for a project.

        Args:
            project_id: The project to add the component to.
            name: Component name.
            code: The generated source code.
            description: What the component does.
            dependencies: Other components this depends on.
            test_code: Generated test code for this component.

        Returns:
            The created CodeComponent, or None if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        if len(project.components) >= self.MAX_COMPONENTS:
            return None

        # Check if component exists, increment version
        existing = next(
            (c for c in project.components.values() if c.name == name), None
        )
        version = existing.version + 1 if existing else 1

        component = CodeComponent(
            name=name,
            language=project.language,
            code=code,
            description=description,
            dependencies=dependencies or [],
            test_code=test_code,
            version=version,
        )
        project.components[component.component_id] = component
        self._total_components += 1

        if project.stage == SynthesisStage.ARCHITECTURE:
            project.stage = SynthesisStage.GENERATION

        project.changelog.append(
            f"Component '{name}' v{version} generated"
        )
        return component

    def test_component(
        self,
        project_id: str,
        component_id: str,
        test_result: TestStatus,
        output: str = "",
    ) -> CodeComponent | None:
        """Record test results for a component.

        Args:
            project_id: The project containing the component.
            component_id: The component that was tested.
            test_result: Result of the test.
            output: Test output or error message.

        Returns:
            The updated CodeComponent, or None if not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return None
        component = project.components.get(component_id)
        if not component:
            return None

        component.test_status = test_result
        project.changelog.append(
            f"Component '{component.name}' test: {test_result.value}"
        )

        if project.stage == SynthesisStage.GENERATION:
            project.stage = SynthesisStage.TESTING

        return component

    def refine_component(
        self,
        project_id: str,
        component_id: str,
        improved_code: str,
        description: str = "",
    ) -> CodeComponent | None:
        """Refine a component based on test results.

        Args:
            project_id: The project containing the component.
            component_id: The component to refine.
            improved_code: The improved source code.
            description: What was improved.

        Returns:
            The refined CodeComponent, or None if not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return None
        component = project.components.get(component_id)
        if not component:
            return None

        old_version = component.version
        component.code = improved_code
        component.version += 1
        component.test_status = TestStatus.PENDING
        if description:
            component.description = description

        project.stage = SynthesisStage.REFINEMENT
        project.changelog.append(
            f"Component '{component.name}' refined: v{old_version} → v{component.version}"
        )

        if component.version >= self.MAX_REFINEMENTS:
            project.changelog.append(
                f"Component '{component.name}' reached max refinements"
            )

        return component

    def finalize_project(self, project_id: str) -> SynthesisProject | None:
        """Mark a project as complete.

        Args:
            project_id: The project to finalize.

        Returns:
            The finalized SynthesisProject, or None if not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        project.stage = SynthesisStage.COMPLETE
        project.completed_at = time.time()
        project.changelog.append("Project finalized")
        return project

    def get_project_summary(self, project_id: str) -> dict[str, Any] | None:
        """Get a summary of a synthesis project.

        Args:
            project_id: The project to summarize.

        Returns:
            Project summary dict.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        return {
            "project_id": project.project_id,
            "name": project.name,
            "language": project.language.value,
            "stage": project.stage.value,
            "specification": project.specification[:200],
            "component_count": len(project.components),
            "components": [
                {
                    "component_id": c.component_id,
                    "name": c.name,
                    "version": c.version,
                    "test_status": c.test_status.value,
                    "code_length": len(c.code),
                }
                for c in project.components.values()
            ],
            "architecture": {
                "components": project.architecture.components,
                "entry_point": project.architecture.entry_point,
                "patterns": project.architecture.patterns,
            } if project.architecture else None,
            "changelog": project.changelog[-10:],
            "created_at": project.created_at,
            "completed_at": project.completed_at,
        }

    def get_component_code(
        self, project_id: str, component_id: str
    ) -> dict[str, Any] | None:
        """Get the full code and test code for a component.

        Args:
            project_id: The project containing the component.
            component_id: The component to retrieve.

        Returns:
            Dict with code, test_code, and metadata.
        """
        project = self._projects.get(project_id)
        if not project:
            return None
        component = project.components.get(component_id)
        if not component:
            return None

        return {
            "component_id": component.component_id,
            "name": component.name,
            "language": component.language.value,
            "version": component.version,
            "code": component.code,
            "test_code": component.test_code,
            "description": component.description,
            "dependencies": component.dependencies,
            "test_status": component.test_status.value,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get synthesis engine statistics."""
        stage_counts: dict[str, int] = {}
        lang_counts: dict[str, int] = {}
        for project in self._projects.values():
            stage_counts[project.stage.value] = (
                stage_counts.get(project.stage.value, 0) + 1
            )
            lang_counts[project.language.value] = (
                lang_counts.get(project.language.value, 0) + 1
            )

        return {
            "total_projects": self._total_projects,
            "total_components": self._total_components,
            "active_projects": sum(
                1 for p in self._projects.values()
                if p.stage != SynthesisStage.COMPLETE
            ),
            "completed_projects": sum(
                1 for p in self._projects.values()
                if p.stage == SynthesisStage.COMPLETE
            ),
            "stage_distribution": stage_counts,
            "language_distribution": lang_counts,
            "avg_components_per_project": round(
                self._total_components / max(self._total_projects, 1), 1
            ),
        }

    def reset(self) -> None:
        """Reset the engine to initial state."""
        self._projects.clear()
        self._total_projects = 0
        self._total_components = 0


# ── Singleton accessors ──

_code_synthesis: AgentCodeSynthesis | None = None


def get_code_synthesis() -> AgentCodeSynthesis:
    """Get or create the singleton code synthesis engine."""
    global _code_synthesis
    if _code_synthesis is None:
        _code_synthesis = AgentCodeSynthesis()
    return _code_synthesis


def reset_code_synthesis() -> None:
    """Reset the singleton code synthesis engine."""
    global _code_synthesis
    if _code_synthesis is not None:
        _code_synthesis.reset()
    _code_synthesis = None