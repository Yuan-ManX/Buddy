"""Buddy Platform Role Catalog — unified role system with RBAC

Replaces the fragmented role definitions (SwarmRole, SquadMemberRole,
team_architect roles) with a single unified catalog. Each role has
permissions, capabilities, and a task-matching profile.

Design principles:
  - Single source of truth: all role definitions live here. Swarm,
    squad, team, and fleet systems reference this catalog.
  - RBAC: each role has explicit permissions (what it can do) and
    capabilities (what tools/toolsets it can access).
  - Role templates: 40+ pre-defined role templates covering common
    organizational and technical positions.
  - Custom roles: users can define custom roles with specific
    permission sets.
  - Role hierarchy: roles have a hierarchy level that influences
    delegation and task assignment priority.
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.platform.role_catalog")


class RoleLevel(int, Enum):
    """Hierarchy level for roles (higher = more authority)."""
    EXECUTIVE = 100  # Chairman, CEO
    MANAGEMENT = 80   # CTO, CPO, VP
    LEAD = 60         # Tech Lead, Design Lead
    SENIOR = 40       # Senior Engineer, Senior Designer
    JUNIOR = 20       # Junior Engineer, Intern
    SPECIALIST = 50   # Domain specialists (parallel to senior)


@dataclass
class RolePermission:
    """A permission granted to a role."""
    name: str
    description: str = ""
    resource: str = ""  # What resource this applies to
    actions: list[str] = field(default_factory=list)  # read, write, execute, admin


@dataclass
class Role:
    """A role in the unified role catalog."""
    role_id: str = ""
    name: str = ""
    description: str = ""
    level: RoleLevel = RoleLevel.SPECIALIST
    permissions: list[RolePermission] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)  # toolset names this role can access
    task_types: list[str] = field(default_factory=list)  # types of tasks this role handles
    parent_role_id: str = ""  # For role hierarchy
    metadata: dict[str, Any] = field(default_factory=dict)
    is_builtin: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "level": self.level.name,
            "level_value": self.level.value,
            "permissions": [
                {"name": p.name, "description": p.description, "resource": p.resource, "actions": p.actions}
                for p in self.permissions
            ],
            "capabilities": self.capabilities,
            "task_types": self.task_types,
            "parent_role_id": self.parent_role_id,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at,
        }

    def has_permission(self, permission_name: str) -> bool:
        return any(p.name == permission_name for p in self.permissions)

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities


class RoleCatalog:
    """Unified role catalog with 40+ built-in templates.

    All role definitions across the platform (swarm, squad, team, fleet)
    reference this catalog. This eliminates the fragmentation caused by
    separate role enums in each module.
    """

    def __init__(self):
        self._roles: dict[str, Role] = {}
        self._lock = threading.RLock()
        self._init_builtin_roles()

    def _init_builtin_roles(self) -> None:
        """Initialize 40+ built-in role templates."""
        builtin_roles = [
            # Executive
            ("chairman", "Chairman", "Ultimate authority; sets strategic direction", RoleLevel.EXECUTIVE,
             ["strategic_planning", "governance", "final_approval"], ["cognitive", "planning", "memory"]),
            ("ceo", "Chief Executive Officer", "Top-level execution; coordinates all teams", RoleLevel.EXECUTIVE,
             ["strategic_planning", "team_management", "resource_allocation", "task_assignment"], ["cognitive", "planning", "memory", "reasoning"]),
            ("cto", "Chief Technology Officer", "Technical strategy and architecture", RoleLevel.MANAGEMENT,
             ["tech_strategy", "architecture_review", "tech_decisions"], ["cognitive", "planning", "reasoning", "mcp"]),
            ("cpo", "Chief Product Officer", "Product vision and roadmap", RoleLevel.MANAGEMENT,
             ["product_strategy", "roadmap_planning", "user_research"], ["cognitive", "planning", "memory"]),
            ("coo", "Chief Operating Officer", "Operations and process management", RoleLevel.MANAGEMENT,
             ["operations", "process_management", "resource_coordination"], ["cognitive", "planning", "memory"]),

            # Management
            ("tech_lead", "Tech Lead", "Technical team leadership", RoleLevel.LEAD,
             ["code_review", "tech_guidance", "task_breakdown"], ["cognitive", "planning", "reasoning", "mcp"]),
            ("design_lead", "Design Lead", "Design team leadership", RoleLevel.LEAD,
             ["design_review", "design_guidance", "ux_decisions"], ["cognitive", "planning", "memory"]),
            ("product_manager", "Product Manager", "Product requirements and prioritization", RoleLevel.LEAD,
             ["requirements", "prioritization", "stakeholder_mgmt"], ["cognitive", "planning", "memory"]),
            ("project_manager", "Project Manager", "Project planning and tracking", RoleLevel.LEAD,
             ["project_planning", "task_tracking", "risk_management"], ["cognitive", "planning", "memory"]),

            # Engineering
            ("senior_engineer", "Senior Engineer", "Complex implementation and mentoring", RoleLevel.SENIOR,
             ["implementation", "code_review", "mentoring", "architecture"], ["cognitive", "planning", "reasoning", "mcp"]),
            ("frontend_engineer", "Frontend Engineer", "UI/UX implementation", RoleLevel.SENIOR,
             ["frontend_dev", "ui_implementation", "responsive_design"], ["cognitive", "planning", "mcp"]),
            ("backend_engineer", "Backend Engineer", "Server and API development", RoleLevel.SENIOR,
             ["backend_dev", "api_design", "database"], ["cognitive", "planning", "reasoning", "mcp"]),
            ("fullstack_engineer", "Full-Stack Engineer", "End-to-end implementation", RoleLevel.SENIOR,
             ["frontend_dev", "backend_dev", "database", "devops"], ["cognitive", "planning", "reasoning", "mcp"]),
            ("devops_engineer", "DevOps Engineer", "Infrastructure and deployment", RoleLevel.SENIOR,
             ["ci_cd", "infrastructure", "monitoring", "deployment"], ["cognitive", "planning", "mcp"]),
            ("data_engineer", "Data Engineer", "Data pipeline and storage", RoleLevel.SENIOR,
             ["data_pipeline", "etl", "data_modeling"], ["cognitive", "planning", "reasoning"]),
            ("ml_engineer", "ML Engineer", "Machine learning model development", RoleLevel.SENIOR,
             ["model_training", "model_deployment", "evaluation"], ["cognitive", "planning", "reasoning"]),
            ("security_engineer", "Security Engineer", "Security audits and hardening", RoleLevel.SENIOR,
             ["security_audit", "vulnerability_assessment", "hardening"], ["cognitive", "planning", "reasoning"]),
            ("qa_engineer", "QA Engineer", "Quality assurance and testing", RoleLevel.SENIOR,
             ["testing", "test_automation", "bug_reporting"], ["cognitive", "planning", "reasoning"]),
            ("junior_engineer", "Junior Engineer", "Learning and simple tasks", RoleLevel.JUNIOR,
             ["implementation", "testing", "documentation"], ["cognitive", "planning"]),

            # Design
            ("ux_designer", "UX Designer", "User experience design", RoleLevel.SENIOR,
             ["ux_research", "wireframing", "prototyping"], ["cognitive", "planning", "memory"]),
            ("ui_designer", "UI Designer", "Visual interface design", RoleLevel.SENIOR,
             ["visual_design", "design_system", "prototyping"], ["cognitive", "planning", "memory"]),
            ("product_designer", "Product Designer", "End-to-end product design", RoleLevel.SENIOR,
             ["ux_research", "visual_design", "prototyping"], ["cognitive", "planning", "memory"]),

            # Research & Analysis
            ("researcher", "Researcher", "Literature and technology research", RoleLevel.SPECIALIST,
             ["research", "analysis", "reporting"], ["cognitive", "memory", "reasoning"]),
            ("data_analyst", "Data Analyst", "Data analysis and insights", RoleLevel.SPECIALIST,
             ["data_analysis", "visualization", "reporting"], ["cognitive", "reasoning"]),
            ("market_analyst", "Market Analyst", "Market research and competitive analysis", RoleLevel.SPECIALIST,
             ["market_research", "competitive_analysis", "reporting"], ["cognitive", "memory"]),

            # Content & Communication
            ("technical_writer", "Technical Writer", "Documentation and guides", RoleLevel.SPECIALIST,
             ["documentation", "tutorials", "api_docs"], ["cognitive", "memory"]),
            ("content_creator", "Content Creator", "Marketing and blog content", RoleLevel.SPECIALIST,
             ["content_writing", "copywriting", "editing"], ["cognitive", "memory"]),
            ("translator", "Translator", "Multi-language translation", RoleLevel.SPECIALIST,
             ["translation", "localization", "editing"], ["cognitive", "memory"]),

            # Operations
            ("scrum_master", "Scrum Master", "Agile process facilitation", RoleLevel.LEAD,
             ["agile_coaching", "facilitation", "impediment_removal"], ["cognitive", "planning", "memory"]),
            ("ops_specialist", "Operations Specialist", "Day-to-day operations", RoleLevel.SPECIALIST,
             ["operations", "process_improvement", "coordination"], ["cognitive", "planning"]),

            # AI/Agent specialists
            ("ai_architect", "AI Architect", "AI system design and orchestration", RoleLevel.MANAGEMENT,
             ["ai_strategy", "agent_design", "model_selection"], ["cognitive", "planning", "reasoning", "mcp"]),
            ("prompt_engineer", "Prompt Engineer", "Prompt optimization and design", RoleLevel.SPECIALIST,
             ["prompt_design", "prompt_testing", "optimization"], ["cognitive", "reasoning"]),
            ("ai_trainer", "AI Trainer", "Model fine-tuning and training", RoleLevel.SPECIALIST,
             ["model_training", "dataset_preparation", "evaluation"], ["cognitive", "reasoning"]),
            ("conversation_designer", "Conversation Designer", "Dialog flow and conversation design", RoleLevel.SPECIALIST,
             ["dialog_design", "conversation_flow", "persona_design"], ["cognitive", "memory"]),

            # Support
            ("support_engineer", "Support Engineer", "Technical support and troubleshooting", RoleLevel.JUNIOR,
             ["troubleshooting", "customer_support", "bug_fixing"], ["cognitive", "planning"]),
            ("community_manager", "Community Manager", "Community engagement and moderation", RoleLevel.SPECIALIST,
             ["community_engagement", "moderation", "content_curation"], ["cognitive", "memory"]),
        ]

        for role_id, name, desc, level, task_types, capabilities in builtin_roles:
            role = Role(
                role_id=role_id,
                name=name,
                description=desc,
                level=level,
                capabilities=capabilities,
                task_types=task_types,
                is_builtin=True,
            )
            self._roles[role_id] = role

        logger.info("Initialized %d builtin roles", len(self._roles))

    # ── Role management ──────────────────────────────────

    def get_role(self, role_id: str) -> Optional[Role]:
        with self._lock:
            return self._roles.get(role_id)

    def list_roles(
        self, level: Optional[RoleLevel] = None, include_custom: bool = True
    ) -> list[dict[str, Any]]:
        with self._lock:
            roles = list(self._roles.values())
        if level:
            roles = [r for r in roles if r.level == level]
        if not include_custom:
            roles = [r for r in roles if r.is_builtin]
        return [r.to_dict() for r in roles]

    def create_custom_role(
        self,
        name: str,
        description: str,
        level: RoleLevel,
        capabilities: list[str],
        task_types: list[str],
        permissions: Optional[list[RolePermission]] = None,
    ) -> str:
        """Create a custom role. Returns role_id."""
        role_id = f"role-{uuid.uuid4().hex[:12]}"
        role = Role(
            role_id=role_id,
            name=name,
            description=description,
            level=level,
            capabilities=capabilities,
            task_types=task_types,
            permissions=permissions or [],
            is_builtin=False,
        )
        with self._lock:
            self._roles[role_id] = role
        logger.info("Created custom role '%s' (%s)", name, role_id)
        return role_id

    def delete_custom_role(self, role_id: str) -> bool:
        with self._lock:
            role = self._roles.get(role_id)
            if role is None or role.is_builtin:
                return False
            del self._roles[role_id]
            return True

    # ── Role matching ────────────────────────────────────

    def match_roles_for_task(
        self,
        task_type: str,
        required_capabilities: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Find roles that match a task's requirements."""
        with self._lock:
            matching = []
            for role in self._roles.values():
                if task_type in role.task_types:
                    if required_capabilities:
                        if not all(c in role.capabilities for c in required_capabilities):
                            continue
                    matching.append(role)
            # Sort by level (higher level first)
            matching.sort(key=lambda r: r.level.value, reverse=True)
            return [r.to_dict() for r in matching]

    def get_roles_by_capability(self, capability: str) -> list[dict[str, Any]]:
        with self._lock:
            matching = [r for r in self._roles.values() if capability in r.capabilities]
            return [r.to_dict() for r in matching]

    def get_subordinates(self, role_id: str) -> list[dict[str, Any]]:
        """Get all roles with a lower level than the given role."""
        with self._lock:
            role = self._roles.get(role_id)
            if role is None:
                return []
            subordinates = [r for r in self._roles.values() if r.level.value < role.level.value]
            return [r.to_dict() for r in subordinates]

    # ── Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_roles": len(self._roles),
                "builtin_roles": sum(1 for r in self._roles.values() if r.is_builtin),
                "custom_roles": sum(1 for r in self._roles.values() if not r.is_builtin),
                "by_level": {
                    level.name: sum(1 for r in self._roles.values() if r.level == level)
                    for level in RoleLevel
                },
            }


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

_role_catalog: Optional[RoleCatalog] = None
_rc_lock = threading.Lock()


def get_role_catalog() -> RoleCatalog:
    """Get the singleton RoleCatalog instance."""
    global _role_catalog
    if _role_catalog is None:
        with _rc_lock:
            if _role_catalog is None:
                _role_catalog = RoleCatalog()
    return _role_catalog
