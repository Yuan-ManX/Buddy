"""Buddy Platform Organization Layer — company/org/team primitives

Provides the organizational hierarchy that ties users, twins, squads,
and workspaces together. Enables multi-tenant isolation and
organizational structure for the platform.

Hierarchy:
  Organization → Department → Team → Member
                    ↓            ↓
              Workspaces    Squads/Task Wall

Each level has its own isolation boundary:
  - Organization: billing, API keys, global config
  - Department: shared resources, cross-team coordination
  - Team: workspace sharing, task wall, squad formation
  - Member: individual agent + twin + role assignment
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("buddy.platform.org_layer")


@dataclass
class Member:
    """A member of a team."""
    member_id: str = ""
    agent_id: str = ""
    twin_id: str = ""
    role_id: str = ""
    team_id: str = ""
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_id": self.member_id,
            "agent_id": self.agent_id,
            "twin_id": self.twin_id,
            "role_id": self.role_id,
            "team_id": self.team_id,
            "joined_at": self.joined_at,
            "is_active": self.is_active,
        }


@dataclass
class Team:
    """A team within a department."""
    team_id: str = ""
    name: str = ""
    department_id: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    members: list[Member] = field(default_factory=list)
    workspace_ids: list[str] = field(default_factory=list)
    task_wall_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "department_id": self.department_id,
            "description": self.description,
            "created_at": self.created_at,
            "member_count": len(self.members),
            "workspace_ids": self.workspace_ids,
            "task_wall_id": self.task_wall_id,
        }


@dataclass
class Department:
    """A department within an organization."""
    department_id: str = ""
    name: str = ""
    org_id: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    team_ids: list[str] = field(default_factory=list)
    head_member_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "department_id": self.department_id,
            "name": self.name,
            "org_id": self.org_id,
            "description": self.description,
            "created_at": self.created_at,
            "team_count": len(self.team_ids),
            "head_member_id": self.head_member_id,
        }


@dataclass
class Organization:
    """Top-level organizational entity with multi-tenant isolation."""
    org_id: str = ""
    name: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    department_ids: list[str] = field(default_factory=list)
    api_keys: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "department_count": len(self.department_ids),
            "is_active": self.is_active,
            "config": self.config,
        }


class OrganizationManager:
    """Manages the organizational hierarchy.

    Organizations contain departments, departments contain teams,
    teams contain members. Each level provides isolation boundaries
    and shared resources.
    """

    def __init__(self):
        self._orgs: dict[str, Organization] = {}
        self._departments: dict[str, Department] = {}
        self._teams: dict[str, Team] = {}
        self._members: dict[str, Member] = {}
        self._lock = threading.RLock()
        self._workspace_manager = None
        self._role_catalog = None

    def attach_workspace_manager(self, workspace_manager) -> None:
        """Link a workspace manager for org-scoped workspace provisioning."""
        self._workspace_manager = workspace_manager

    def attach_role_catalog(self, role_catalog) -> None:
        """Link a role catalog for member role assignment."""
        self._role_catalog = role_catalog

    # ── Organization lifecycle ───────────────────────────

    def create_organization(
        self,
        name: str,
        description: str = "",
        config: Optional[dict[str, Any]] = None,
    ) -> str:
        org_id = f"org-{uuid.uuid4().hex[:12]}"
        org = Organization(
            org_id=org_id,
            name=name,
            description=description,
            config=config or {},
        )
        with self._lock:
            self._orgs[org_id] = org
        logger.info("Created organization '%s' (%s)", name, org_id)
        return org_id

    def get_organization(self, org_id: str) -> Optional[Organization]:
        with self._lock:
            return self._orgs.get(org_id)

    def list_organizations(self) -> list[dict[str, Any]]:
        with self._lock:
            return [o.to_dict() for o in self._orgs.values()]

    # ── Department lifecycle ─────────────────────────────

    def create_department(
        self,
        org_id: str,
        name: str,
        description: str = "",
    ) -> Optional[str]:
        with self._lock:
            if org_id not in self._orgs:
                return None
        dept_id = f"dept-{uuid.uuid4().hex[:12]}"
        dept = Department(
            department_id=dept_id,
            name=name,
            org_id=org_id,
            description=description,
        )
        with self._lock:
            self._departments[dept_id] = dept
            self._orgs[org_id].department_ids.append(dept_id)
        return dept_id

    def get_department(self, dept_id: str) -> Optional[Department]:
        with self._lock:
            return self._departments.get(dept_id)

    def list_departments(self, org_id: str) -> list[dict[str, Any]]:
        with self._lock:
            org = self._orgs.get(org_id)
            if org is None:
                return []
            return [
                self._departments[did].to_dict()
                for did in org.department_ids
                if did in self._departments
            ]

    # ── Team lifecycle ───────────────────────────────────

    def create_team(
        self,
        department_id: str,
        name: str,
        description: str = "",
    ) -> Optional[str]:
        with self._lock:
            if department_id not in self._departments:
                return None
        team_id = f"team-{uuid.uuid4().hex[:12]}"
        team = Team(
            team_id=team_id,
            name=name,
            department_id=department_id,
            description=description,
        )
        with self._lock:
            self._teams[team_id] = team
            self._departments[department_id].team_ids.append(team_id)
        return team_id

    def get_team(self, team_id: str) -> Optional[Team]:
        with self._lock:
            return self._teams.get(team_id)

    def list_teams(self, department_id: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            teams = list(self._teams.values())
        if department_id:
            teams = [t for t in teams if t.department_id == department_id]
        return [t.to_dict() for t in teams]

    # ── Member management ────────────────────────────────

    def add_member(
        self,
        team_id: str,
        agent_id: str,
        role_id: str,
        twin_id: str = "",
    ) -> Optional[str]:
        """Add a member to a team with a specific role."""
        with self._lock:
            if team_id not in self._teams:
                return None
        member_id = f"member-{uuid.uuid4().hex[:12]}"
        member = Member(
            member_id=member_id,
            agent_id=agent_id,
            twin_id=twin_id,
            role_id=role_id,
            team_id=team_id,
        )
        with self._lock:
            self._members[member_id] = member
            self._teams[team_id].members.append(member)
        logger.info("Added member %s to team %s with role %s", agent_id, team_id, role_id)
        return member_id

    def remove_member(self, member_id: str) -> bool:
        with self._lock:
            member = self._members.get(member_id)
            if member is None:
                return False
            member.is_active = False
            team = self._teams.get(member.team_id)
            if team:
                team.members = [m for m in team.members if m.member_id != member_id]
            return True

    def get_team_members(self, team_id: str) -> list[dict[str, Any]]:
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                return []
            return [m.to_dict() for m in team.members if m.is_active]

    def get_member_role(self, member_id: str) -> Optional[str]:
        with self._lock:
            member = self._members.get(member_id)
            return member.role_id if member else None

    # ── Workspace association ────────────────────────────

    def assign_workspace(self, team_id: str, workspace_id: str) -> bool:
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                return False
            if workspace_id not in team.workspace_ids:
                team.workspace_ids.append(workspace_id)
            return True

    def get_team_workspaces(self, team_id: str) -> list[str]:
        with self._lock:
            team = self._teams.get(team_id)
            return team.workspace_ids if team else []

    # ── Hierarchy queries ────────────────────────────────

    def get_org_structure(self, org_id: str) -> dict[str, Any]:
        """Get the complete organizational structure."""
        with self._lock:
            org = self._orgs.get(org_id)
            if org is None:
                return {}

            structure = org.to_dict()
            structure["departments"] = []
            for dept_id in org.department_ids:
                dept = self._departments.get(dept_id)
                if dept is None:
                    continue
                dept_dict = dept.to_dict()
                dept_dict["teams"] = []
                for team_id in dept.team_ids:
                    team = self._teams.get(team_id)
                    if team is None:
                        continue
                    team_dict = team.to_dict()
                    team_dict["members"] = [m.to_dict() for m in team.members if m.is_active]
                    dept_dict["teams"].append(team_dict)
                structure["departments"].append(dept_dict)
            return structure

    def get_member_org(self, member_id: str) -> Optional[str]:
        """Get the organization ID for a member."""
        with self._lock:
            member = self._members.get(member_id)
            if member is None:
                return None
            team = self._teams.get(member.team_id)
            if team is None:
                return None
            dept = self._departments.get(team.department_id)
            if dept is None:
                return None
            return dept.org_id

    # ── Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_orgs": len(self._orgs),
                "total_departments": len(self._departments),
                "total_teams": len(self._teams),
                "total_members": sum(1 for m in self._members.values() if m.is_active),
                "active_orgs": sum(1 for o in self._orgs.values() if o.is_active),
            }


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

_org_manager: Optional[OrganizationManager] = None
_om_lock = threading.Lock()


def get_org_manager() -> OrganizationManager:
    """Get the singleton OrganizationManager instance."""
    global _org_manager
    if _org_manager is None:
        with _om_lock:
            if _org_manager is None:
                _org_manager = OrganizationManager()
    return _org_manager
