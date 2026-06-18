"""Buddy Skill Fabric — Complete Skill Lifecycle Management

Provides a unified system for creating, bundling, marketing, composing, and
analyzing skills across the Buddy AI-native platform. The Skill Fabric is the
central hub for all skill lifecycle operations.

Components:
  - SkillForge: Skill creation, validation, refinement, and versioning
  - SkillBundle: Bundle packaging, dependency resolution, import/export
  - SkillMarket: Internal marketplace with discovery, rating, and recommendations
  - SkillComposer: Workflow composition through skill chaining and mapping
  - SkillAnalytics: Performance tracking, trends, and improvement suggestions
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.skill_fabric")


# ═══════════════════════════════════════════════════════════
# Shared Enums
# ═══════════════════════════════════════════════════════════

class SkillType(str, Enum):
    """Classification of skill execution patterns."""
    TOOL_CHAIN = "tool_chain"
    WORKFLOW = "workflow"
    KNOWLEDGE = "knowledge"
    INTERACTION = "interaction"
    AUTOMATION = "automation"


class SkillLifecycleStatus(str, Enum):
    """Lifecycle states for a skill."""
    DRAFT = "draft"
    VALIDATING = "validating"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class BundleStatus(str, Enum):
    """Status of a skill bundle."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PricingModel(str, Enum):
    """Pricing models for skills in the marketplace."""
    FREE = "free"
    TOKEN_COST = "token_cost"
    SUBSCRIPTION = "subscription"


class ChainMode(str, Enum):
    """Execution modes for skill composition."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class CompositionStatus(str, Enum):
    """Status of a skill composition."""
    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


# ═══════════════════════════════════════════════════════════
# Shared Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class SkillPrecondition:
    """A precondition that must be satisfied before skill execution."""
    name: str
    check_type: str = "field_exists"  # field_exists, value_match, custom
    field: str = ""
    expected_value: Any = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "check_type": self.check_type,
            "field": self.field,
            "expected_value": self.expected_value,
            "description": self.description,
        }


@dataclass
class SkillPostcondition:
    """A postcondition that must hold after skill execution."""
    name: str
    check_type: str = "field_exists"  # field_exists, value_match, custom
    field: str = ""
    expected_value: Any = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "check_type": self.check_type,
            "field": self.field,
            "expected_value": self.expected_value,
            "description": self.description,
        }


@dataclass
class SkillParameter:
    """A parameter definition for a skill."""
    name: str
    param_type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.param_type,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "examples": self.examples,
        }


@dataclass
class SkillVersion:
    """A specific version of a skill."""
    version: str
    prompt_template: str = ""
    parameters: list[SkillParameter] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    changelog: str = ""

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "prompt_template": self.prompt_template,
            "parameters": [p.to_dict() for p in self.parameters],
            "created_at": self.created_at,
            "changelog": self.changelog,
        }


# ═══════════════════════════════════════════════════════════
# 1. SkillForge — Skill Creation and Refinement
# ═══════════════════════════════════════════════════════════

@dataclass
class ForgedSkill:
    """A skill created and managed by the SkillForge."""
    id: str = field(default_factory=lambda: f"skill-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    skill_type: SkillType = SkillType.TOOL_CHAIN
    status: SkillLifecycleStatus = SkillLifecycleStatus.DRAFT
    versions: list[SkillVersion] = field(default_factory=list)
    preconditions: list[SkillPrecondition] = field(default_factory=list)
    postconditions: list[SkillPostcondition] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    author_agent_id: str = ""
    parent_skill_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    total_executions: int = 0
    success_count: int = 0
    failure_count: int = 0
    validation_errors: list[str] = field(default_factory=list)

    @property
    def current_version(self) -> SkillVersion | None:
        return self.versions[-1] if self.versions else None

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.success_count / self.total_executions

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skill_type": self.skill_type.value,
            "status": self.status.value,
            "versions": [v.to_dict() for v in self.versions],
            "preconditions": [p.to_dict() for p in self.preconditions],
            "postconditions": [p.to_dict() for p in self.postconditions],
            "tags": self.tags,
            "author_agent_id": self.author_agent_id,
            "parent_skill_id": self.parent_skill_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_executions": self.total_executions,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 3),
            "validation_errors": self.validation_errors,
        }


class SkillForge:
    """Creates and refines skills with validation and version management.

    Supports skill creation from templates, patterns, or manual definition.
    Validates preconditions, postconditions, and type correctness. Refines
    skills based on execution feedback and maintains version history.
    """

    def __init__(self):
        self._skills: dict[str, ForgedSkill] = {}
        self._template_library: dict[str, dict] = {}
        self._total_created = 0
        self._total_refined = 0
        self._total_validated = 0
        logger.info("SkillForge initialized")

    # ── Skill Creation ───────────────────────────────────

    def create_from_template(
        self,
        template_name: str,
        name: str,
        description: str = "",
        skill_type: SkillType | None = None,
        overrides: dict | None = None,
    ) -> ForgedSkill | None:
        """Create a skill from a named template with optional overrides."""
        template = self._template_library.get(template_name)
        if not template:
            logger.warning(f"Template not found: {template_name}")
            return None

        overrides = overrides or {}
        skill = ForgedSkill(
            name=name,
            description=description or template.get("description", ""),
            skill_type=skill_type or SkillType(template.get("skill_type", "tool_chain")),
            tags=overrides.get("tags", template.get("tags", [])),
            author_agent_id=overrides.get("author_agent_id", ""),
            versions=[
                SkillVersion(
                    version="1.0.0",
                    prompt_template=overrides.get("prompt_template", template.get("prompt_template", "")),
                    parameters=[
                        SkillParameter(
                            name=p.get("name", ""),
                            param_type=p.get("type", "string"),
                            description=p.get("description", ""),
                            required=p.get("required", False),
                            default=p.get("default"),
                            examples=p.get("examples", []),
                        )
                        for p in overrides.get("parameters", template.get("parameters", []))
                    ],
                )
            ],
            preconditions=[
                SkillPrecondition(
                    name=c.get("name", ""),
                    check_type=c.get("check_type", "field_exists"),
                    field=c.get("field", ""),
                    expected_value=c.get("expected_value"),
                    description=c.get("description", ""),
                )
                for c in overrides.get("preconditions", template.get("preconditions", []))
            ],
            postconditions=[
                SkillPostcondition(
                    name=c.get("name", ""),
                    check_type=c.get("check_type", "field_exists"),
                    field=c.get("field", ""),
                    expected_value=c.get("expected_value"),
                    description=c.get("description", ""),
                )
                for c in overrides.get("postconditions", template.get("postconditions", []))
            ],
        )
        self._skills[skill.id] = skill
        self._total_created += 1
        logger.info(f"Skill created from template '{template_name}': {skill.name}")
        return skill

    def create_manual(
        self,
        name: str,
        description: str,
        skill_type: SkillType,
        prompt_template: str,
        parameters: list[SkillParameter] | None = None,
        preconditions: list[SkillPrecondition] | None = None,
        postconditions: list[SkillPostcondition] | None = None,
        tags: list[str] | None = None,
        author_agent_id: str = "",
    ) -> ForgedSkill:
        """Create a skill from a manual definition."""
        skill = ForgedSkill(
            name=name,
            description=description,
            skill_type=skill_type,
            tags=tags or [],
            author_agent_id=author_agent_id,
            versions=[
                SkillVersion(
                    version="1.0.0",
                    prompt_template=prompt_template,
                    parameters=parameters or [],
                )
            ],
            preconditions=preconditions or [],
            postconditions=postconditions or [],
        )
        self._skills[skill.id] = skill
        self._total_created += 1
        logger.info(f"Skill created manually: {skill.name}")
        return skill

    def create_from_pattern(
        self,
        name: str,
        description: str,
        skill_type: SkillType,
        pattern_data: dict,
        author_agent_id: str = "",
    ) -> ForgedSkill:
        """Create a skill from a detected execution pattern."""
        prompt_template = pattern_data.get("prompt_template", "")
        raw_params = pattern_data.get("parameters", [])
        parameters = [
            SkillParameter(
                name=p.get("name", ""),
                param_type=p.get("type", "string"),
                description=p.get("description", ""),
                required=p.get("required", False),
                default=p.get("default"),
                examples=p.get("examples", []),
            )
            for p in raw_params
        ]

        skill = ForgedSkill(
            name=name,
            description=description,
            skill_type=skill_type,
            tags=pattern_data.get("tags", []),
            author_agent_id=author_agent_id,
            versions=[
                SkillVersion(
                    version="0.1.0",
                    prompt_template=prompt_template,
                    parameters=parameters,
                )
            ],
        )
        self._skills[skill.id] = skill
        self._total_created += 1
        logger.info(f"Skill created from pattern: {skill.name}")
        return skill

    def register_template(
        self,
        name: str,
        description: str,
        skill_type: SkillType,
        prompt_template: str,
        parameters: list[dict] | None = None,
        tags: list[str] | None = None,
        preconditions: list[dict] | None = None,
        postconditions: list[dict] | None = None,
    ):
        """Register a reusable skill template in the template library."""
        self._template_library[name] = {
            "description": description,
            "skill_type": skill_type.value,
            "prompt_template": prompt_template,
            "parameters": parameters or [],
            "tags": tags or [],
            "preconditions": preconditions or [],
            "postconditions": postconditions or [],
        }
        logger.info(f"Template registered: {name}")

    # ── Skill Validation ─────────────────────────────────

    def validate(self, skill_id: str) -> dict:
        """Validate a skill's preconditions, postconditions, and type correctness."""
        skill = self._skills.get(skill_id)
        if not skill:
            return {"valid": False, "errors": ["Skill not found"]}

        errors = []

        # Validate name and description
        if not skill.name or len(skill.name.strip()) < 2:
            errors.append("Skill name must be at least 2 characters")
        if not skill.description or len(skill.description.strip()) < 10:
            errors.append("Skill description must be at least 10 characters")

        # Validate skill type
        try:
            SkillType(skill.skill_type.value)
        except ValueError:
            errors.append(f"Invalid skill type: {skill.skill_type}")

        # Validate current version
        version = skill.current_version
        if not version:
            errors.append("Skill has no versions")
            return {"valid": False, "errors": errors}

        if not version.prompt_template:
            errors.append("Prompt template cannot be empty")

        # Validate parameters
        param_names = set()
        for param in version.parameters:
            if not param.name:
                errors.append("Parameter has no name")
            elif param.name in param_names:
                errors.append(f"Duplicate parameter name: {param.name}")
            else:
                param_names.add(param.name)
            if param.param_type not in ("string", "number", "boolean", "array", "object"):
                errors.append(f"Invalid parameter type '{param.param_type}' for '{param.name}'")

        # Validate preconditions
        for pre in skill.preconditions:
            if not pre.name:
                errors.append("Precondition has no name")
            if pre.check_type not in ("field_exists", "value_match", "custom"):
                errors.append(f"Invalid precondition check type: {pre.check_type}")

        # Validate postconditions
        for post in skill.postconditions:
            if not post.name:
                errors.append("Postcondition has no name")
            if post.check_type not in ("field_exists", "value_match", "custom"):
                errors.append(f"Invalid postcondition check type: {post.check_type}")

        skill.validation_errors = errors
        if not errors:
            skill.status = SkillLifecycleStatus.VALIDATING
            self._total_validated += 1

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "skill_id": skill_id,
        }

    def activate(self, skill_id: str) -> bool:
        """Activate a skill after validation passes."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        if skill.status != SkillLifecycleStatus.VALIDATING:
            return False
        skill.status = SkillLifecycleStatus.ACTIVE
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Skill activated: {skill.name}")
        return True

    # ── Skill Refinement ─────────────────────────────────

    def refine(
        self,
        skill_id: str,
        feedback: dict,
        version_bump: str = "patch",
    ) -> dict:
        """Refine a skill based on execution feedback.

        Creates a new version incorporating the feedback. The feedback dict
        should contain 'new_prompt_template' or 'parameter_updates'.
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return {"refined": False, "error": "Skill not found"}

        current = skill.current_version
        if not current:
            return {"refined": False, "error": "Skill has no versions"}

        # Determine new version number
        old_parts = [int(x) for x in current.version.split(".")]
        if version_bump == "major":
            new_version = f"{old_parts[0] + 1}.0.0"
        elif version_bump == "minor":
            new_version = f"{old_parts[0]}.{old_parts[1] + 1}.0"
        else:
            new_version = f"{old_parts[0]}.{old_parts[1]}.{old_parts[2] + 1}"

        new_template = feedback.get("new_prompt_template", current.prompt_template)

        # Merge parameter updates
        raw_params = feedback.get("parameter_updates")
        if raw_params:
            new_params = [
                SkillParameter(
                    name=p.get("name", ""),
                    param_type=p.get("type", "string"),
                    description=p.get("description", ""),
                    required=p.get("required", False),
                    default=p.get("default"),
                    examples=p.get("examples", []),
                )
                for p in raw_params
            ]
        else:
            new_params = current.parameters

        new_version_obj = SkillVersion(
            version=new_version,
            prompt_template=new_template,
            parameters=new_params,
            changelog=feedback.get("changelog", ""),
        )
        skill.versions.append(new_version_obj)
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        self._total_refined += 1

        logger.info(f"Skill refined: {skill.name} v{new_version}")
        return {
            "refined": True,
            "skill_id": skill_id,
            "old_version": current.version,
            "new_version": new_version,
            "changelog": feedback.get("changelog", ""),
        }

    def record_execution(
        self,
        skill_id: str,
        success: bool,
        tokens: int = 0,
        latency_ms: float = 0.0,
    ):
        """Record a skill execution for tracking."""
        skill = self._skills.get(skill_id)
        if not skill:
            return
        skill.total_executions += 1
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1

    # ── Version Management ───────────────────────────────

    def get_version(self, skill_id: str, version: str) -> SkillVersion | None:
        """Get a specific version of a skill."""
        skill = self._skills.get(skill_id)
        if not skill:
            return None
        for v in skill.versions:
            if v.version == version:
                return v
        return None

    def list_versions(self, skill_id: str) -> list[dict]:
        """List all versions of a skill."""
        skill = self._skills.get(skill_id)
        if not skill:
            return []
        return [v.to_dict() for v in skill.versions]

    # ── Skill Management ─────────────────────────────────

    def get_skill(self, skill_id: str) -> ForgedSkill | None:
        return self._skills.get(skill_id)

    def list_skills(
        self,
        skill_type: SkillType | None = None,
        status: SkillLifecycleStatus | None = None,
        tags: list[str] | None = None,
    ) -> list[ForgedSkill]:
        """List skills with optional filtering."""
        results = list(self._skills.values())
        if skill_type:
            results = [s for s in results if s.skill_type == skill_type]
        if status:
            results = [s for s in results if s.status == status]
        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]
        return sorted(results, key=lambda s: s.success_rate, reverse=True)

    def deprecate(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.status = SkillLifecycleStatus.DEPRECATED
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def archive(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.status = SkillLifecycleStatus.ARCHIVED
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def get_stats(self) -> dict:
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for s in self._skills.values():
            by_type[s.skill_type.value] = by_type.get(s.skill_type.value, 0) + 1
            by_status[s.status.value] = by_status.get(s.status.value, 0) + 1

        return {
            "total_skills": len(self._skills),
            "total_created": self._total_created,
            "total_refined": self._total_refined,
            "total_validated": self._total_validated,
            "total_templates": len(self._template_library),
            "by_type": by_type,
            "by_status": by_status,
            "total_executions": sum(s.total_executions for s in self._skills.values()),
            "avg_success_rate": round(
                sum(s.success_rate for s in self._skills.values()) / max(len(self._skills), 1), 3
            ),
        }


# ═══════════════════════════════════════════════════════════
# 2. SkillBundle — Skill Bundle/Package Management
# ═══════════════════════════════════════════════════════════

@dataclass
class SkillBundleEntry:
    """A skill entry within a bundle."""
    skill_id: str
    skill_name: str = ""
    version: str = "1.0.0"
    required: bool = True

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "version": self.version,
            "required": self.required,
        }


@dataclass
class SkillBundle:
    """A package of skills bundled together with dependency resolution."""
    id: str = field(default_factory=lambda: f"bundle-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    status: BundleStatus = BundleStatus.DRAFT
    skills: list[SkillBundleEntry] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    author_agent_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    shared_with: list[str] = field(default_factory=list)  # Agent IDs
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "skills": [s.to_dict() for s in self.skills],
            "tags": self.tags,
            "author_agent_id": self.author_agent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "shared_with": self.shared_with,
            "version": self.version,
            "skill_count": len(self.skills),
        }


class SkillBundleManager:
    """Manages skill bundles with dependency resolution, sharing, and import/export.

    Bundles group related skills together for distribution, sharing between
    agents, and coordinated activation/deactivation.
    """

    def __init__(self):
        self._bundles: dict[str, SkillBundle] = {}
        self._skill_index: dict[str, set[str]] = {}  # skill_id -> set of bundle_ids
        logger.info("SkillBundleManager initialized")

    # ── Bundle Creation ──────────────────────────────────

    def create_bundle(
        self,
        name: str,
        description: str,
        skill_ids: list[str],
        skill_names: list[str] | None = None,
        author_agent_id: str = "",
        tags: list[str] | None = None,
    ) -> SkillBundle:
        """Create a bundle from a set of skills."""
        skill_names = skill_names or ["" for _ in skill_ids]
        entries = []
        for i, sid in enumerate(skill_ids):
            entry = SkillBundleEntry(
                skill_id=sid,
                skill_name=skill_names[i] if i < len(skill_names) else "",
            )
            entries.append(entry)

        bundle = SkillBundle(
            name=name,
            description=description,
            skills=entries,
            author_agent_id=author_agent_id,
            tags=tags or [],
        )
        self._bundles[bundle.id] = bundle

        # Update index
        for entry in entries:
            if entry.skill_id not in self._skill_index:
                self._skill_index[entry.skill_id] = set()
            self._skill_index[entry.skill_id].add(bundle.id)

        logger.info(f"Bundle created: {bundle.name} ({len(entries)} skills)")
        return bundle

    def add_skill_to_bundle(
        self,
        bundle_id: str,
        skill_id: str,
        skill_name: str = "",
        required: bool = True,
    ) -> bool:
        """Add a skill to an existing bundle."""
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return False

        entry = SkillBundleEntry(
            skill_id=skill_id,
            skill_name=skill_name,
            required=required,
        )
        bundle.skills.append(entry)
        bundle.updated_at = datetime.now(timezone.utc).isoformat()

        if skill_id not in self._skill_index:
            self._skill_index[skill_id] = set()
        self._skill_index[skill_id].add(bundle_id)
        return True

    def remove_skill_from_bundle(self, bundle_id: str, skill_id: str) -> bool:
        """Remove a skill from a bundle."""
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return False

        before = len(bundle.skills)
        bundle.skills = [s for s in bundle.skills if s.skill_id != skill_id]
        if len(bundle.skills) < before:
            bundle.updated_at = datetime.now(timezone.utc).isoformat()
            if skill_id in self._skill_index:
                self._skill_index[skill_id].discard(bundle_id)
            return True
        return False

    # ── Dependency Resolution ────────────────────────────

    def resolve_dependencies(
        self,
        bundle_id: str,
        available_skills: dict[str, Any] | None = None,
    ) -> dict:
        """Resolve dependencies for all skills in a bundle.

        Checks that all required skills are available and reports any
        missing or version-mismatched dependencies.
        """
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return {"resolved": False, "error": "Bundle not found"}

        available_skills = available_skills or {}
        missing: list[str] = []
        version_mismatches: list[dict] = []
        resolved: list[str] = []

        for entry in bundle.skills:
            if entry.skill_id in available_skills:
                skill_data = available_skills[entry.skill_id]
                skill_version = skill_data.get("version", "0.0.0") if isinstance(skill_data, dict) else getattr(skill_data, "version", "0.0.0")
                if entry.version and entry.version != skill_version:
                    version_mismatches.append({
                        "skill_id": entry.skill_id,
                        "expected": entry.version,
                        "actual": skill_version,
                    })
                resolved.append(entry.skill_id)
            elif entry.required:
                missing.append(entry.skill_id)

        is_resolved = len(missing) == 0
        return {
            "resolved": is_resolved,
            "bundle_id": bundle_id,
            "missing": missing,
            "version_mismatches": version_mismatches,
            "resolved_skills": resolved,
            "total_skills": len(bundle.skills),
        }

    # ── Bundle Activation/Deactivation ───────────────────

    def activate(self, bundle_id: str) -> bool:
        """Activate a bundle."""
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return False
        bundle.status = BundleStatus.ACTIVE
        bundle.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def deactivate(self, bundle_id: str) -> bool:
        """Deactivate a bundle."""
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return False
        bundle.status = BundleStatus.INACTIVE
        bundle.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    # ── Bundle Sharing ───────────────────────────────────

    def share_with_agent(self, bundle_id: str, agent_id: str) -> bool:
        """Share a bundle with another agent."""
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return False
        if agent_id not in bundle.shared_with:
            bundle.shared_with.append(agent_id)
            bundle.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def unshare_from_agent(self, bundle_id: str, agent_id: str) -> bool:
        """Remove sharing access for an agent."""
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return False
        if agent_id in bundle.shared_with:
            bundle.shared_with.remove(agent_id)
            bundle.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def get_shared_agents(self, bundle_id: str) -> list[str]:
        """Get the list of agents a bundle is shared with."""
        bundle = self._bundles.get(bundle_id)
        return bundle.shared_with if bundle else []

    # ── Import/Export ────────────────────────────────────

    def export_bundle(self, bundle_id: str) -> str | None:
        """Export a bundle as a JSON string."""
        bundle = self._bundles.get(bundle_id)
        if not bundle:
            return None
        return json.dumps(bundle.to_dict(), indent=2, default=str)

    def import_bundle(self, data: str) -> SkillBundle | None:
        """Import a bundle from a JSON string."""
        try:
            raw = json.loads(data)
            bundle = SkillBundle(
                id=raw.get("id", f"bundle-{uuid.uuid4().hex[:8]}"),
                name=raw.get("name", ""),
                description=raw.get("description", ""),
                status=BundleStatus(raw.get("status", "draft")),
                skills=[
                    SkillBundleEntry(
                        skill_id=s.get("skill_id", ""),
                        skill_name=s.get("skill_name", ""),
                        version=s.get("version", "1.0.0"),
                        required=s.get("required", True),
                    )
                    for s in raw.get("skills", [])
                ],
                tags=raw.get("tags", []),
                author_agent_id=raw.get("author_agent_id", ""),
                version=raw.get("version", "1.0.0"),
            )
            self._bundles[bundle.id] = bundle

            # Update index
            for entry in bundle.skills:
                if entry.skill_id not in self._skill_index:
                    self._skill_index[entry.skill_id] = set()
                self._skill_index[entry.skill_id].add(bundle.id)

            logger.info(f"Bundle imported: {bundle.name}")
            return bundle
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Bundle import failed: {e}")
            return None

    # ── Bundle Management ────────────────────────────────

    def get_bundle(self, bundle_id: str) -> SkillBundle | None:
        return self._bundles.get(bundle_id)

    def list_bundles(
        self,
        status: BundleStatus | None = None,
        tags: list[str] | None = None,
        shared_with_agent: str | None = None,
    ) -> list[SkillBundle]:
        """List bundles with optional filtering."""
        results = list(self._bundles.values())
        if status:
            results = [b for b in results if b.status == status]
        if tags:
            results = [b for b in results if any(t in b.tags for t in tags)]
        if shared_with_agent:
            results = [b for b in results if shared_with_agent in b.shared_with]
        return results

    def find_bundles_with_skill(self, skill_id: str) -> list[SkillBundle]:
        """Find all bundles that contain a given skill."""
        bundle_ids = self._skill_index.get(skill_id, set())
        return [self._bundles[bid] for bid in bundle_ids if bid in self._bundles]

    def get_stats(self) -> dict:
        return {
            "total_bundles": len(self._bundles),
            "active_bundles": sum(1 for b in self._bundles.values() if b.status == BundleStatus.ACTIVE),
            "total_skills_in_bundles": sum(len(b.skills) for b in self._bundles.values()),
            "total_shared": sum(1 for b in self._bundles.values() if b.shared_with),
        }


# ═══════════════════════════════════════════════════════════
# 3. SkillMarket — Internal Skill Marketplace
# ═══════════════════════════════════════════════════════════

@dataclass
class MarketSkill:
    """A skill listing in the internal marketplace."""
    id: str
    name: str = ""
    description: str = ""
    skill_type: SkillType = SkillType.TOOL_CHAIN
    version: str = "1.0.0"
    author_agent_id: str = ""
    pricing: PricingModel = PricingModel.FREE
    token_cost: float = 0.0
    subscription_cost: float = 0.0
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    rating: float = 0.0
    rating_count: int = 0
    downloads: int = 0
    usage_count: int = 0
    published_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skill_type": self.skill_type.value,
            "version": self.version,
            "author_agent_id": self.author_agent_id,
            "pricing": self.pricing.value,
            "token_cost": self.token_cost,
            "subscription_cost": self.subscription_cost,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "rating": round(self.rating, 2),
            "rating_count": self.rating_count,
            "downloads": self.downloads,
            "usage_count": self.usage_count,
            "published_at": self.published_at,
            "updated_at": self.updated_at,
        }


@dataclass
class MarketReview:
    """A rating and review for a marketplace skill."""
    id: str = field(default_factory=lambda: f"review-{uuid.uuid4().hex[:8]}")
    skill_id: str = ""
    reviewer_agent_id: str = ""
    rating: float = 0.0  # 1.0 to 5.0
    title: str = ""
    content: str = ""
    helpful_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "reviewer_agent_id": self.reviewer_agent_id,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "helpful_count": self.helpful_count,
            "created_at": self.created_at,
        }


@dataclass
class AgentProfile:
    """A profile for an agent used for skill recommendations."""
    agent_id: str
    skills_used: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)
    usage_history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "skills_used": self.skills_used,
            "capabilities": self.capabilities,
            "preferred_categories": self.preferred_categories,
        }


class SkillMarket:
    """Internal skill marketplace with discovery, rating, and recommendations.

    Provides a catalog of skills that agents can discover, rate, and install.
    Includes usage statistics, pricing models, and personalized recommendations
    based on agent profiles.
    """

    def __init__(self):
        self._skills: dict[str, MarketSkill] = {}
        self._reviews: dict[str, list[MarketReview]] = {}
        self._agent_profiles: dict[str, AgentProfile] = {}
        self._usage_stats: dict[str, dict] = {}
        self._featured: list[str] = []
        logger.info("SkillMarket initialized")

    # ── Listing Management ───────────────────────────────

    def list_skill(self, skill: MarketSkill) -> MarketSkill:
        """List a skill in the marketplace."""
        self._skills[skill.id] = skill
        self._reviews[skill.id] = []
        self._usage_stats[skill.id] = {
            "daily": [],
            "weekly": [],
            "monthly": [],
        }
        logger.info(f"Skill listed in market: {skill.name}")
        return skill

    def update_listing(self, skill_id: str, updates: dict) -> MarketSkill | None:
        """Update a marketplace listing."""
        skill = self._skills.get(skill_id)
        if not skill:
            return None
        for key, value in updates.items():
            if hasattr(skill, key):
                setattr(skill, key, value)
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        return skill

    def remove_listing(self, skill_id: str) -> bool:
        """Remove a skill from the marketplace."""
        if skill_id in self._skills:
            del self._skills[skill_id]
            self._reviews.pop(skill_id, None)
            return True
        return False

    # ── Discovery ────────────────────────────────────────

    def discover(
        self,
        query: str = "",
        skill_type: SkillType | None = None,
        tags: list[str] | None = None,
        capabilities: list[str] | None = None,
        pricing: PricingModel | None = None,
        sort_by: str = "rating",
        limit: int = 20,
    ) -> list[dict]:
        """Discover skills by capability, tag, or other criteria."""
        results = list(self._skills.values())

        if query:
            q = query.lower()
            results = [
                s for s in results
                if q in s.name.lower()
                or q in s.description.lower()
                or any(q in tag.lower() for tag in s.tags)
                or any(q in cap.lower() for cap in s.capabilities)
            ]

        if skill_type:
            results = [s for s in results if s.skill_type == skill_type]

        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]

        if capabilities:
            results = [s for s in results if any(c in s.capabilities for c in capabilities)]

        if pricing:
            results = [s for s in results if s.pricing == pricing]

        # Sort
        if sort_by == "rating":
            results.sort(key=lambda s: (s.rating, s.downloads), reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda s: s.downloads, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda s: s.published_at, reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda s: s.name.lower())

        return [s.to_dict() for s in results[:limit]]

    def discover_by_agent(self, agent_id: str, limit: int = 10) -> list[dict]:
        """Discover skills by agent — finds skills created by a specific agent."""
        results = [s for s in self._skills.values() if s.author_agent_id == agent_id]
        results.sort(key=lambda s: s.rating, reverse=True)
        return [s.to_dict() for s in results[:limit]]

    # ── Rating and Reviews ───────────────────────────────

    def add_review(self, review: MarketReview) -> MarketReview:
        """Add a review for a marketplace skill."""
        if review.skill_id not in self._skills:
            raise ValueError(f"Skill {review.skill_id} not found in market")

        if review.rating < 1.0 or review.rating > 5.0:
            raise ValueError("Rating must be between 1.0 and 5.0")

        self._reviews[review.skill_id].append(review)

        # Update skill rating
        skill = self._skills[review.skill_id]
        all_reviews = self._reviews[review.skill_id]
        skill.rating = sum(r.rating for r in all_reviews) / len(all_reviews)
        skill.rating_count = len(all_reviews)

        logger.info(f"Review added for {skill.name}: {review.rating}/5")
        return review

    def get_reviews(self, skill_id: str) -> list[dict]:
        """Get all reviews for a skill."""
        reviews = self._reviews.get(skill_id, [])
        return sorted(
            [r.to_dict() for r in reviews],
            key=lambda r: r["created_at"],
            reverse=True,
        )

    def mark_review_helpful(self, review_id: str):
        """Increment the helpful count for a review."""
        for reviews in self._reviews.values():
            for review in reviews:
                if review.id == review_id:
                    review.helpful_count += 1
                    return

    # ── Usage Statistics ─────────────────────────────────

    def record_usage(self, skill_id: str):
        """Record a usage event for a skill."""
        skill = self._skills.get(skill_id)
        if not skill:
            return
        skill.usage_count += 1
        skill.downloads += 1

        now = datetime.now(timezone.utc)
        stats = self._usage_stats.get(skill_id, {})
        stats.setdefault("daily", []).append({"timestamp": now.isoformat()})
        stats.setdefault("weekly", []).append({"timestamp": now.isoformat()})
        stats.setdefault("monthly", []).append({"timestamp": now.isoformat()})

    def get_usage_stats(self, skill_id: str) -> dict:
        """Get usage statistics for a skill."""
        skill = self._skills.get(skill_id)
        if not skill:
            return {}

        stats = self._usage_stats.get(skill_id, {})
        return {
            "skill_id": skill_id,
            "total_usage": skill.usage_count,
            "total_downloads": skill.downloads,
            "daily_usage": len(stats.get("daily", [])),
            "weekly_usage": len(stats.get("weekly", [])),
            "monthly_usage": len(stats.get("monthly", [])),
            "rating": round(skill.rating, 2),
            "rating_count": skill.rating_count,
        }

    # ── Recommendations ──────────────────────────────────

    def register_agent_profile(self, profile: AgentProfile):
        """Register or update an agent profile for recommendations."""
        self._agent_profiles[profile.agent_id] = profile

    def recommend(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Recommend skills based on an agent's profile and usage history."""
        profile = self._agent_profiles.get(agent_id)
        if not profile:
            # Return top-rated skills for unknown agents
            results = sorted(
                self._skills.values(),
                key=lambda s: (s.rating, s.downloads),
                reverse=True,
            )
            return [s.to_dict() for s in results[:limit]]

        scored: list[tuple[float, MarketSkill]] = []
        for skill in self._skills.values():
            # Skip skills the agent already uses
            if skill.id in profile.skills_used:
                continue

            score = 0.0

            # Match by capabilities
            cap_overlap = set(skill.capabilities) & set(profile.capabilities)
            if cap_overlap:
                score += len(cap_overlap) * 0.3

            # Match by preferred categories
            if skill.skill_type.value in profile.preferred_categories:
                score += 0.2

            # Match by tags in usage history
            for usage in profile.usage_history:
                used_tags = usage.get("tags", [])
                if any(t in skill.tags for t in used_tags):
                    score += 0.1

            # Rating bonus
            score += skill.rating * 0.1

            # Popularity bonus
            score += min(skill.downloads / 1000, 1.0) * 0.05

            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s.to_dict() for _, s in scored[:limit]]

    # ── Pricing ──────────────────────────────────────────

    def set_pricing(
        self,
        skill_id: str,
        pricing: PricingModel,
        token_cost: float = 0.0,
        subscription_cost: float = 0.0,
    ) -> bool:
        """Set pricing for a marketplace skill."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        skill.pricing = pricing
        skill.token_cost = token_cost
        skill.subscription_cost = subscription_cost
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    # ── Featured Skills ──────────────────────────────────

    def feature_skill(self, skill_id: str):
        """Feature a skill in the marketplace."""
        if skill_id in self._skills and skill_id not in self._featured:
            self._featured.append(skill_id)
            if len(self._featured) > 20:
                self._featured = self._featured[-20:]

    def unfeature_skill(self, skill_id: str):
        """Remove a skill from featured."""
        if skill_id in self._featured:
            self._featured.remove(skill_id)

    def get_featured(self) -> list[dict]:
        """Get featured skills."""
        return [
            self._skills[sid].to_dict()
            for sid in self._featured
            if sid in self._skills
        ]

    def get_stats(self) -> dict:
        by_type: dict[str, int] = {}
        by_pricing: dict[str, int] = {}
        for s in self._skills.values():
            by_type[s.skill_type.value] = by_type.get(s.skill_type.value, 0) + 1
            by_pricing[s.pricing.value] = by_pricing.get(s.pricing.value, 0) + 1

        return {
            "total_listings": len(self._skills),
            "total_reviews": sum(len(r) for r in self._reviews.values()),
            "total_downloads": sum(s.downloads for s in self._skills.values()),
            "total_usage": sum(s.usage_count for s in self._skills.values()),
            "by_type": by_type,
            "by_pricing": by_pricing,
            "featured_count": len(self._featured),
            "avg_rating": round(
                sum(s.rating for s in self._skills.values()) / max(len(self._skills), 1), 2
            ),
        }


# ═══════════════════════════════════════════════════════════
# 4. SkillComposer — Skill Composition into Workflows
# ═══════════════════════════════════════════════════════════

@dataclass
class SkillChainStep:
    """A single step in a skill composition."""
    skill_id: str
    step_id: str = field(default_factory=lambda: f"step-{uuid.uuid4().hex[:8]}")
    chain_mode: ChainMode = ChainMode.SEQUENTIAL
    depends_on: list[str] = field(default_factory=list)
    condition: str = ""  # Expression evaluated against previous step outputs
    input_mapping: dict[str, str] = field(default_factory=dict)  # source_step -> param
    output_mapping: dict[str, str] = field(default_factory=dict)  # output -> target_step
    error_policy: str = "abort"  # abort, skip, fallback
    fallback_skill_id: str = ""
    timeout_seconds: float = 60.0
    max_retries: int = 2

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "step_id": self.step_id,
            "chain_mode": self.chain_mode.value,
            "depends_on": self.depends_on,
            "condition": self.condition,
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "error_policy": self.error_policy,
            "fallback_skill_id": self.fallback_skill_id,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }


@dataclass
class SkillComposition:
    """A composed workflow of skills chained together."""
    id: str = field(default_factory=lambda: f"comp-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    status: CompositionStatus = CompositionStatus.DRAFT
    steps: list[SkillChainStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    author_agent_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    validation_errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "tags": self.tags,
            "author_agent_id": self.author_agent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 3),
            "validation_errors": self.validation_errors,
        }


@dataclass
class ExecutionPlan:
    """A generated execution plan for a skill composition."""
    composition_id: str
    execution_order: list[str]  # Ordered list of step_ids
    parallel_groups: list[list[str]]  # Groups of step_ids that can run in parallel
    estimated_duration_ms: float = 0.0
    total_steps: int = 0
    critical_path: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "composition_id": self.composition_id,
            "execution_order": self.execution_order,
            "parallel_groups": self.parallel_groups,
            "estimated_duration_ms": self.estimated_duration_ms,
            "total_steps": self.total_steps,
            "critical_path": self.critical_path,
            "warnings": self.warnings,
        }


class SkillComposer:
    """Composes skills into workflows with chaining, mapping, and validation.

    Supports sequential, parallel, and conditional skill chaining. Handles
    input/output mapping between skills, error handling with fallback chains,
    and generates optimized execution plans.
    """

    def __init__(self):
        self._compositions: dict[str, SkillComposition] = {}
        self._plans: dict[str, ExecutionPlan] = {}
        logger.info("SkillComposer initialized")

    # ── Composition Creation ─────────────────────────────

    def create_composition(
        self,
        name: str,
        description: str,
        author_agent_id: str = "",
        tags: list[str] | None = None,
    ) -> SkillComposition:
        """Create a new empty skill composition."""
        composition = SkillComposition(
            name=name,
            description=description,
            author_agent_id=author_agent_id,
            tags=tags or [],
        )
        self._compositions[composition.id] = composition
        logger.info(f"Composition created: {composition.name}")
        return composition

    def add_step(
        self,
        composition_id: str,
        skill_id: str,
        chain_mode: ChainMode = ChainMode.SEQUENTIAL,
        depends_on: list[str] | None = None,
        input_mapping: dict[str, str] | None = None,
        output_mapping: dict[str, str] | None = None,
        condition: str = "",
        error_policy: str = "abort",
        fallback_skill_id: str = "",
    ) -> SkillChainStep | None:
        """Add a step to a composition."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return None

        step = SkillChainStep(
            skill_id=skill_id,
            chain_mode=chain_mode,
            depends_on=depends_on or [],
            condition=condition,
            input_mapping=input_mapping or {},
            output_mapping=output_mapping or {},
            error_policy=error_policy,
            fallback_skill_id=fallback_skill_id,
        )
        composition.steps.append(step)
        composition.updated_at = datetime.now(timezone.utc).isoformat()
        return step

    def remove_step(self, composition_id: str, step_id: str) -> bool:
        """Remove a step from a composition."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return False

        before = len(composition.steps)
        composition.steps = [s for s in composition.steps if s.step_id != step_id]
        if len(composition.steps) < before:
            composition.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    # ── Skill Chaining ───────────────────────────────────

    def chain_sequential(
        self,
        composition_id: str,
        skill_ids: list[str],
        input_mappings: list[dict[str, str]] | None = None,
    ) -> list[SkillChainStep] | None:
        """Chain skills sequentially in a composition."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return None

        steps = []
        prev_step_id: str | None = None

        for i, sid in enumerate(skill_ids):
            step = SkillChainStep(
                skill_id=sid,
                chain_mode=ChainMode.SEQUENTIAL,
                depends_on=[prev_step_id] if prev_step_id else [],
                input_mapping=input_mappings[i] if input_mappings and i < len(input_mappings) else {},
            )
            composition.steps.append(step)
            steps.append(step)
            prev_step_id = step.step_id

        composition.updated_at = datetime.now(timezone.utc).isoformat()
        return steps

    def chain_parallel(
        self,
        composition_id: str,
        skill_ids: list[str],
        depends_on: list[str] | None = None,
    ) -> list[SkillChainStep] | None:
        """Chain skills in parallel within a composition."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return None

        steps = []
        for sid in skill_ids:
            step = SkillChainStep(
                skill_id=sid,
                chain_mode=ChainMode.PARALLEL,
                depends_on=depends_on or [],
            )
            composition.steps.append(step)
            steps.append(step)

        composition.updated_at = datetime.now(timezone.utc).isoformat()
        return steps

    def chain_conditional(
        self,
        composition_id: str,
        skill_id: str,
        condition: str,
        true_skill_id: str = "",
        false_skill_id: str = "",
        depends_on: list[str] | None = None,
    ) -> list[SkillChainStep] | None:
        """Create a conditional branching chain in a composition."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return None

        condition_step = SkillChainStep(
            skill_id=skill_id,
            chain_mode=ChainMode.CONDITIONAL,
            condition=condition,
            depends_on=depends_on or [],
        )
        composition.steps.append(condition_step)
        steps = [condition_step]

        if true_skill_id:
            true_step = SkillChainStep(
                skill_id=true_skill_id,
                chain_mode=ChainMode.SEQUENTIAL,
                depends_on=[condition_step.step_id],
            )
            composition.steps.append(true_step)
            steps.append(true_step)

        if false_skill_id:
            false_step = SkillChainStep(
                skill_id=false_skill_id,
                chain_mode=ChainMode.SEQUENTIAL,
                depends_on=[condition_step.step_id],
            )
            composition.steps.append(false_step)
            steps.append(false_step)

        composition.updated_at = datetime.now(timezone.utc).isoformat()
        return steps

    # ── Input/Output Mapping ─────────────────────────────

    def set_input_mapping(
        self,
        composition_id: str,
        step_id: str,
        source_step_id: str,
        source_output: str,
        target_param: str,
    ) -> bool:
        """Map an output from a source step to an input parameter of a target step."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return False

        for step in composition.steps:
            if step.step_id == step_id:
                step.input_mapping[f"{source_step_id}.{source_output}"] = target_param
                composition.updated_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def set_output_mapping(
        self,
        composition_id: str,
        step_id: str,
        output_name: str,
        target_step_id: str,
    ) -> bool:
        """Map an output from a step to a target step."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return False

        for step in composition.steps:
            if step.step_id == step_id:
                step.output_mapping[output_name] = target_step_id
                composition.updated_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    # ── Error Handling ───────────────────────────────────

    def set_error_policy(
        self,
        composition_id: str,
        step_id: str,
        error_policy: str,
        fallback_skill_id: str = "",
    ) -> bool:
        """Set the error handling policy for a step."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return False

        for step in composition.steps:
            if step.step_id == step_id:
                step.error_policy = error_policy
                step.fallback_skill_id = fallback_skill_id
                composition.updated_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    # ── Composition Validation ───────────────────────────

    def validate(self, composition_id: str) -> dict:
        """Validate a composition for correctness.

        Checks for circular dependencies, missing dependencies, and ensures
        all referenced skills are defined.
        """
        composition = self._compositions.get(composition_id)
        if not composition:
            return {"valid": False, "errors": ["Composition not found"]}

        errors = []

        if not composition.name or len(composition.name.strip()) < 2:
            errors.append("Composition name must be at least 2 characters")

        if not composition.steps:
            errors.append("Composition has no steps")

        step_ids = {s.step_id for s in composition.steps}

        # Check for duplicate step IDs
        seen_ids = set()
        for step in composition.steps:
            if step.step_id in seen_ids:
                errors.append(f"Duplicate step ID: {step.step_id}")
            seen_ids.add(step.step_id)

        # Check for missing dependencies
        for step in composition.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    errors.append(f"Step '{step.step_id}' depends on unknown step '{dep}'")

        # Check for circular dependencies
        circular = self._detect_circular_dependencies(composition)
        errors.extend(circular)

        # Check fallback references
        for step in composition.steps:
            if step.fallback_skill_id and step.fallback_skill_id not in step_ids:
                errors.append(f"Step '{step.step_id}' has unknown fallback '{step.fallback_skill_id}'")

        composition.validation_errors = errors
        if not errors:
            composition.status = CompositionStatus.VALIDATED

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "composition_id": composition_id,
        }

    def _detect_circular_dependencies(self, composition: SkillComposition) -> list[str]:
        """Detect circular dependencies in a composition."""
        errors = []
        step_map = {s.step_id: s for s in composition.steps}

        for step in composition.steps:
            visited = set()
            stack = [step.step_id]
            while stack:
                current = stack.pop()
                if current in visited:
                    if current == step.step_id:
                        errors.append(f"Circular dependency detected involving '{step.step_id}'")
                    break
                visited.add(current)
                if current in step_map:
                    for dep in step_map[current].depends_on:
                        stack.append(dep)

        return errors

    def activate(self, composition_id: str) -> bool:
        """Activate a validated composition."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return False
        if composition.status != CompositionStatus.VALIDATED:
            return False
        composition.status = CompositionStatus.ACTIVE
        composition.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    # ── Execution Plan Generation ────────────────────────

    def generate_plan(self, composition_id: str) -> ExecutionPlan | None:
        """Generate an optimized execution plan for a composition.

        Analyzes the skill chain to determine execution order, identify
        parallelizable groups, and estimate total duration.
        """
        composition = self._compositions.get(composition_id)
        if not composition:
            return None

        if not composition.steps:
            return None

        # Build dependency graph
        step_map = {s.step_id: s for s in composition.steps}
        in_degree: dict[str, int] = {s.step_id: 0 for s in composition.steps}
        dependents: dict[str, list[str]] = {s.step_id: [] for s in composition.steps}

        for step in composition.steps:
            for dep in step.depends_on:
                if dep in in_degree:
                    in_degree[step.step_id] += 1
                    if dep in dependents:
                        dependents[dep].append(step.step_id)

        # Topological sort with parallel group detection
        execution_order: list[str] = []
        parallel_groups: list[list[str]] = []
        critical_path: list[str] = []
        warnings: list[str] = []

        ready = [sid for sid, deg in in_degree.items() if deg == 0]
        if not ready:
            warnings.append("No entry point found — all steps have dependencies")
            return ExecutionPlan(
                composition_id=composition_id,
                execution_order=[],
                parallel_groups=[],
                warnings=warnings,
                total_steps=len(composition.steps),
            )

        while ready:
            parallel_groups.append(list(ready))
            next_ready = []
            for sid in ready:
                execution_order.append(sid)
                critical_path.append(sid)
                for dep_id in dependents.get(sid, []):
                    in_degree[dep_id] -= 1
                    if in_degree[dep_id] == 0:
                        next_ready.append(dep_id)
            ready = next_ready

        # Check for unreachable steps
        if len(execution_order) < len(composition.steps):
            warnings.append(f"Some steps could not be reached: {len(composition.steps) - len(execution_order)} unreachable")

        # Estimate duration
        estimated_ms = len(parallel_groups) * 1000  # Rough estimate: 1s per parallel group

        plan = ExecutionPlan(
            composition_id=composition_id,
            execution_order=execution_order,
            parallel_groups=parallel_groups,
            estimated_duration_ms=estimated_ms,
            total_steps=len(composition.steps),
            critical_path=critical_path,
            warnings=warnings,
        )
        self._plans[composition_id] = plan
        return plan

    # ── Composition Management ───────────────────────────

    def get_composition(self, composition_id: str) -> SkillComposition | None:
        return self._compositions.get(composition_id)

    def get_plan(self, composition_id: str) -> ExecutionPlan | None:
        return self._plans.get(composition_id)

    def list_compositions(
        self,
        status: CompositionStatus | None = None,
        tags: list[str] | None = None,
    ) -> list[SkillComposition]:
        """List compositions with optional filtering."""
        results = list(self._compositions.values())
        if status:
            results = [c for c in results if c.status == status]
        if tags:
            results = [c for c in results if any(t in c.tags for t in tags)]
        return sorted(results, key=lambda c: c.success_rate, reverse=True)

    def record_execution(
        self,
        composition_id: str,
        success: bool,
    ):
        """Record a composition execution for tracking."""
        composition = self._compositions.get(composition_id)
        if not composition:
            return
        composition.usage_count += 1
        if success:
            composition.success_count += 1
        else:
            composition.failure_count += 1

    def deprecate(self, composition_id: str) -> bool:
        composition = self._compositions.get(composition_id)
        if not composition:
            return False
        composition.status = CompositionStatus.DEPRECATED
        composition.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def get_stats(self) -> dict:
        by_status: dict[str, int] = {}
        for c in self._compositions.values():
            by_status[c.status.value] = by_status.get(c.status.value, 0) + 1

        return {
            "total_compositions": len(self._compositions),
            "total_plans": len(self._plans),
            "by_status": by_status,
            "total_usage": sum(c.usage_count for c in self._compositions.values()),
            "total_success": sum(c.success_count for c in self._compositions.values()),
            "avg_success_rate": round(
                sum(c.success_rate for c in self._compositions.values()) / max(len(self._compositions), 1), 3
            ),
            "total_steps": sum(len(c.steps) for c in self._compositions.values()),
        }


# ═══════════════════════════════════════════════════════════
# 5. SkillAnalytics — Skill Performance Analytics
# ═══════════════════════════════════════════════════════════

@dataclass
class SkillMetrics:
    """Performance metrics for a single skill."""
    skill_id: str
    skill_name: str = ""
    total_executions: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    first_used: str = ""
    last_used: str = ""
    daily_usage: dict[str, int] = field(default_factory=dict)  # date -> count
    hourly_usage: dict[str, int] = field(default_factory=dict)  # hour -> count
    failure_reasons: dict[str, int] = field(default_factory=dict)  # reason -> count

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.success_count / self.total_executions

    @property
    def avg_execution_time_ms(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_latency_ms / self.total_executions

    @property
    def avg_cost_per_execution(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_cost / self.total_executions

    @property
    def avg_tokens_per_execution(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_tokens / self.total_executions

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "total_executions": self.total_executions,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 3),
            "avg_execution_time_ms": round(self.avg_execution_time_ms, 1),
            "avg_cost_per_execution": round(self.avg_cost_per_execution, 4),
            "avg_tokens_per_execution": round(self.avg_tokens_per_execution, 1),
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "first_used": self.first_used,
            "last_used": self.last_used,
            "daily_usage": self.daily_usage,
            "hourly_usage": self.hourly_usage,
            "top_failure_reasons": dict(
                sorted(self.failure_reasons.items(), key=lambda x: x[1], reverse=True)[:5]
            ),
        }


@dataclass
class ImprovementSuggestion:
    """A suggestion for improving a skill based on analytics."""
    skill_id: str
    suggestion: str
    category: str = ""  # performance, reliability, cost, usability
    priority: str = "medium"  # low, medium, high, critical
    based_on: str = ""  # What metric triggered this suggestion
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "suggestion": self.suggestion,
            "category": self.category,
            "priority": self.priority,
            "based_on": self.based_on,
            "created_at": self.created_at,
        }


class SkillAnalytics:
    """Tracks and analyzes skill performance with improvement suggestions.

    Collects usage frequency, success/failure rates, execution time, cost
    metrics, and generates actionable improvement suggestions based on
    observed patterns.
    """

    def __init__(self):
        self._metrics: dict[str, SkillMetrics] = {}
        self._suggestions: dict[str, list[ImprovementSuggestion]] = {}
        self._event_log: list[dict] = []
        self._max_event_log = 1000
        logger.info("SkillAnalytics initialized")

    # ── Event Recording ──────────────────────────────────

    def record_execution(
        self,
        skill_id: str,
        skill_name: str = "",
        success: bool = True,
        tokens: int = 0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        failure_reason: str = "",
    ):
        """Record a skill execution event for analytics."""
        now = datetime.now(timezone.utc)
        date_key = now.strftime("%Y-%m-%d")
        hour_key = now.strftime("%H")

        if skill_id not in self._metrics:
            self._metrics[skill_id] = SkillMetrics(
                skill_id=skill_id,
                skill_name=skill_name,
                first_used=now.isoformat(),
            )

        metrics = self._metrics[skill_id]
        metrics.skill_name = skill_name or metrics.skill_name
        metrics.total_executions += 1
        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
            if failure_reason:
                metrics.failure_reasons[failure_reason] = (
                    metrics.failure_reasons.get(failure_reason, 0) + 1
                )

        metrics.total_tokens += tokens
        metrics.total_latency_ms += latency_ms
        metrics.total_cost += cost
        metrics.last_used = now.isoformat()
        metrics.daily_usage[date_key] = metrics.daily_usage.get(date_key, 0) + 1
        metrics.hourly_usage[hour_key] = metrics.hourly_usage.get(hour_key, 0) + 1

        # Log event
        self._event_log.append({
            "skill_id": skill_id,
            "success": success,
            "tokens": tokens,
            "latency_ms": latency_ms,
            "cost": cost,
            "timestamp": now.isoformat(),
        })
        if len(self._event_log) > self._max_event_log:
            self._event_log = self._event_log[-self._max_event_log:]

        # Generate suggestions if needed
        self._check_suggestions(skill_id)

    # ── Usage Analytics ──────────────────────────────────

    def get_usage_frequency(self, skill_id: str) -> dict:
        """Get usage frequency and trends for a skill."""
        metrics = self._metrics.get(skill_id)
        if not metrics:
            return {"skill_id": skill_id, "total_executions": 0}

        # Sort daily usage by date
        sorted_daily = sorted(metrics.daily_usage.items())

        # Calculate trend: is usage increasing or decreasing?
        trend = "stable"
        if len(sorted_daily) >= 2:
            first_half = sum(v for _, v in sorted_daily[:len(sorted_daily)//2])
            second_half = sum(v for _, v in sorted_daily[len(sorted_daily)//2:])
            if second_half > first_half * 1.2:
                trend = "increasing"
            elif second_half < first_half * 0.8:
                trend = "decreasing"

        return {
            "skill_id": skill_id,
            "skill_name": metrics.skill_name,
            "total_executions": metrics.total_executions,
            "daily_usage": dict(sorted_daily),
            "hourly_usage": metrics.hourly_usage,
            "trend": trend,
            "first_used": metrics.first_used,
            "last_used": metrics.last_used,
        }

    def get_success_rate(self, skill_id: str) -> dict:
        """Get success/failure rate for a skill."""
        metrics = self._metrics.get(skill_id)
        if not metrics:
            return {"skill_id": skill_id, "total_executions": 0}

        return {
            "skill_id": skill_id,
            "skill_name": metrics.skill_name,
            "total_executions": metrics.total_executions,
            "success_count": metrics.success_count,
            "failure_count": metrics.failure_count,
            "success_rate": round(metrics.success_rate, 3),
            "top_failure_reasons": dict(
                sorted(metrics.failure_reasons.items(), key=lambda x: x[1], reverse=True)[:5]
            ),
        }

    def get_execution_time(self, skill_id: str) -> dict:
        """Get average execution time for a skill."""
        metrics = self._metrics.get(skill_id)
        if not metrics:
            return {"skill_id": skill_id, "total_executions": 0}

        return {
            "skill_id": skill_id,
            "skill_name": metrics.skill_name,
            "total_executions": metrics.total_executions,
            "avg_execution_time_ms": round(metrics.avg_execution_time_ms, 1),
            "total_latency_ms": round(metrics.total_latency_ms, 1),
        }

    def get_cost(self, skill_id: str) -> dict:
        """Get cost per execution for a skill."""
        metrics = self._metrics.get(skill_id)
        if not metrics:
            return {"skill_id": skill_id, "total_executions": 0}

        return {
            "skill_id": skill_id,
            "skill_name": metrics.skill_name,
            "total_executions": metrics.total_executions,
            "avg_cost_per_execution": round(metrics.avg_cost_per_execution, 4),
            "total_cost": round(metrics.total_cost, 4),
            "avg_tokens_per_execution": round(metrics.avg_tokens_per_execution, 1),
            "total_tokens": metrics.total_tokens,
        }

    def get_all_metrics(self, skill_id: str) -> dict:
        """Get all metrics for a skill in a single call."""
        metrics = self._metrics.get(skill_id)
        if not metrics:
            return {"skill_id": skill_id, "found": False}
        return {"found": True, **metrics.to_dict()}

    # ── Improvement Suggestions ──────────────────────────

    def _check_suggestions(self, skill_id: str):
        """Check if any improvement suggestions should be generated."""
        metrics = self._metrics.get(skill_id)
        if not metrics or metrics.total_executions < 5:
            return

        if skill_id not in self._suggestions:
            self._suggestions[skill_id] = []

        # Check for low success rate
        if metrics.total_executions >= 10 and metrics.success_rate < 0.7:
            self._suggestions[skill_id].append(ImprovementSuggestion(
                skill_id=skill_id,
                suggestion=f"Success rate is {metrics.success_rate:.0%}. Review failure patterns and refine the skill's prompt template.",
                category="reliability",
                priority="high" if metrics.success_rate < 0.5 else "medium",
                based_on=f"success_rate={metrics.success_rate:.2f}",
            ))

        # Check for high cost
        if metrics.total_executions >= 10 and metrics.avg_cost_per_execution > 0.01:
            self._suggestions[skill_id].append(ImprovementSuggestion(
                skill_id=skill_id,
                suggestion=f"Average cost is ${metrics.avg_cost_per_execution:.4f} per execution. Consider optimizing the prompt to reduce token usage.",
                category="cost",
                priority="medium",
                based_on=f"avg_cost={metrics.avg_cost_per_execution:.4f}",
            ))

        # Check for high latency
        if metrics.total_executions >= 10 and metrics.avg_execution_time_ms > 5000:
            self._suggestions[skill_id].append(ImprovementSuggestion(
                skill_id=skill_id,
                suggestion=f"Average execution time is {metrics.avg_execution_time_ms:.0f}ms. Consider breaking the skill into smaller sub-skills.",
                category="performance",
                priority="medium",
                based_on=f"avg_latency={metrics.avg_execution_time_ms:.0f}ms",
            ))

    def get_suggestions(self, skill_id: str) -> list[dict]:
        """Get improvement suggestions for a skill."""
        return [s.to_dict() for s in self._suggestions.get(skill_id, [])]

    def get_all_suggestions(
        self,
        priority: str | None = None,
        category: str | None = None,
    ) -> list[dict]:
        """Get all improvement suggestions with optional filtering."""
        all_suggestions = []
        for suggestions in self._suggestions.values():
            for s in suggestions:
                if priority and s.priority != priority:
                    continue
                if category and s.category != category:
                    continue
                all_suggestions.append(s.to_dict())

        return sorted(
            all_suggestions,
            key=lambda s: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(s["priority"], 4),
        )

    def clear_suggestions(self, skill_id: str):
        """Clear all suggestions for a skill."""
        self._suggestions.pop(skill_id, None)

    # ── Aggregate Analytics ──────────────────────────────

    def get_top_skills(
        self,
        metric: str = "success_rate",
        limit: int = 10,
    ) -> list[dict]:
        """Get top skills ranked by a given metric."""
        results = list(self._metrics.values())

        if metric == "success_rate":
            results = [m for m in results if m.total_executions >= 5]
            results.sort(key=lambda m: m.success_rate, reverse=True)
        elif metric == "usage":
            results.sort(key=lambda m: m.total_executions, reverse=True)
        elif metric == "cost":
            results.sort(key=lambda m: m.avg_cost_per_execution)
        elif metric == "speed":
            results = [m for m in results if m.total_executions >= 5]
            results.sort(key=lambda m: m.avg_execution_time_ms)

        return [m.to_dict() for m in results[:limit]]

    def get_global_stats(self) -> dict:
        """Get aggregate analytics across all skills."""
        total_executions = sum(m.total_executions for m in self._metrics.values())
        total_success = sum(m.success_count for m in self._metrics.values())
        total_failure = sum(m.failure_count for m in self._metrics.values())
        total_cost = sum(m.total_cost for m in self._metrics.values())
        total_tokens = sum(m.total_tokens for m in self._metrics.values())

        return {
            "total_skills_tracked": len(self._metrics),
            "total_executions": total_executions,
            "total_success": total_success,
            "total_failure": total_failure,
            "overall_success_rate": round(total_success / max(total_executions, 1), 3),
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens,
            "avg_cost_per_execution": round(total_cost / max(total_executions, 1), 4),
            "total_suggestions": sum(len(s) for s in self._suggestions.values()),
            "critical_suggestions": sum(
                1 for s_list in self._suggestions.values()
                for s in s_list if s.priority == "critical"
            ),
            "high_suggestions": sum(
                1 for s_list in self._suggestions.values()
                for s in s_list if s.priority == "high"
            ),
        }


# ═══════════════════════════════════════════════════════════
# SkillFabric — Unified Skill Lifecycle Manager
# ═══════════════════════════════════════════════════════════

class SkillFabric:
    """Unified skill lifecycle management for the Buddy platform.

    Integrates all five skill management components:
    - SkillForge: creation, validation, refinement, versioning
    - SkillBundle: bundling, dependencies, sharing, import/export
    - SkillMarket: discovery, rating, recommendations, pricing
    - SkillComposer: workflow composition, chaining, execution plans
    - SkillAnalytics: performance tracking, metrics, suggestions
    """

    def __init__(self):
        self.forge = SkillForge()
        self.bundles = SkillBundleManager()
        self.market = SkillMarket()
        self.composer = SkillComposer()
        self.analytics = SkillAnalytics()
        logger.info("SkillFabric initialized")

    def get_full_stats(self) -> dict:
        """Get comprehensive statistics across all components."""
        return {
            "forge": self.forge.get_stats(),
            "bundles": self.bundles.get_stats(),
            "market": self.market.get_stats(),
            "composer": self.composer.get_stats(),
            "analytics": self.analytics.get_global_stats(),
        }

    def publish_skill_to_market(
        self,
        skill_id: str,
        pricing: PricingModel = PricingModel.FREE,
        token_cost: float = 0.0,
        subscription_cost: float = 0.0,
    ) -> MarketSkill | None:
        """Publish a forged skill to the marketplace."""
        skill = self.forge.get_skill(skill_id)
        if not skill:
            return None

        current = skill.current_version
        market_skill = MarketSkill(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            skill_type=skill.skill_type,
            version=current.version if current else "1.0.0",
            author_agent_id=skill.author_agent_id,
            pricing=pricing,
            token_cost=token_cost,
            subscription_cost=subscription_cost,
            tags=skill.tags,
            capabilities=[t for t in skill.tags],
        )
        return self.market.list_skill(market_skill)

    def bundle_and_publish(
        self,
        bundle_name: str,
        description: str,
        skill_ids: list[str],
        skill_names: list[str] | None = None,
        author_agent_id: str = "",
    ) -> SkillBundle | None:
        """Create a bundle from skills and make it ready for sharing."""
        # Validate all skills exist in forge
        for sid in skill_ids:
            if not self.forge.get_skill(sid):
                return None

        bundle = self.bundles.create_bundle(
            name=bundle_name,
            description=description,
            skill_ids=skill_ids,
            skill_names=skill_names,
            author_agent_id=author_agent_id,
        )
        self.bundles.activate(bundle.id)
        return bundle

    def compose_from_market(
        self,
        name: str,
        description: str,
        skill_ids: list[str],
        chain_mode: ChainMode = ChainMode.SEQUENTIAL,
        author_agent_id: str = "",
    ) -> SkillComposition | None:
        """Create a composition from marketplace skills."""
        # Verify all skills exist in the market
        for sid in skill_ids:
            if sid not in self.market._skills:
                return None

        composition = self.composer.create_composition(
            name=name,
            description=description,
            author_agent_id=author_agent_id,
        )

        if chain_mode == ChainMode.SEQUENTIAL:
            self.composer.chain_sequential(composition.id, skill_ids)
        elif chain_mode == ChainMode.PARALLEL:
            self.composer.chain_parallel(composition.id, skill_ids)

        # Validate and generate plan
        validation = self.composer.validate(composition.id)
        if validation["valid"]:
            self.composer.generate_plan(composition.id)

        return composition

    def record_and_analyze(
        self,
        skill_id: str,
        success: bool,
        tokens: int = 0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        failure_reason: str = "",
    ):
        """Record execution across forge and analytics simultaneously."""
        self.forge.record_execution(skill_id, success, tokens, latency_ms)
        self.analytics.record_execution(
            skill_id=skill_id,
            success=success,
            tokens=tokens,
            latency_ms=latency_ms,
            cost=cost,
            failure_reason=failure_reason,
        )


# ── Global Singleton ────────────────────────────────────────

skill_fabric = SkillFabric()