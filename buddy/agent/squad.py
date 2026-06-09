"""
Buddy Squads — Collaborative Agent Teams

A multi-agent collaboration framework that groups agents into squads
with leader-based delegation. Squads enable parallel work distribution,
specialized role assignment, and trust-scored coordination.

Key concepts:
  - Squad: A named team of agents with a designated leader
  - Leadership: The leader receives tasks and delegates to members
  - Trust scoring: Agents earn trust through successful collaboration
  - Task transfer: Work can be reassigned between squad members
  - Team discussion: Members can discuss and coordinate on shared tasks
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.squad")


# ── Squad Models ──

class SquadStatus(str, Enum):
    FORMING = "forming"
    ACTIVE = "active"
    PAUSED = "paused"
    DISSOLVED = "dissolved"


class MemberRole(str, Enum):
    LEADER = "leader"
    SPECIALIST = "specialist"
    GENERALIST = "generalist"
    OBSERVER = "observer"


class DiscussionStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


@dataclass
class SquadMember:
    """A member of a squad with role and trust information."""
    agent_id: str
    agent_name: str = ""
    role: MemberRole = MemberRole.GENERALIST
    trust_score: float = 0.5
    tasks_completed: int = 0
    tasks_failed: int = 0
    expertise: list[str] = field(default_factory=list)
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / max(total, 1)

    def dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "role": self.role.value,
            "trust_score": self.trust_score,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "success_rate": self.success_rate,
            "expertise": self.expertise,
            "joined_at": self.joined_at,
        }


@dataclass
class DiscussionThread:
    """A discussion thread among squad members about a task."""
    thread_id: str
    squad_id: str
    task_id: str = ""
    topic: str = ""
    status: DiscussionStatus = DiscussionStatus.OPEN
    messages: list[dict] = field(default_factory=list)
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str = ""
    resolution: str = ""

    def add_message(self, agent_id: str, content: str):
        self.messages.append({
            "agent_id": agent_id,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "squad_id": self.squad_id,
            "task_id": self.task_id,
            "topic": self.topic,
            "status": self.status.value,
            "message_count": len(self.messages),
            "created_by": self.created_by,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution,
        }


@dataclass
class Squad:
    """A collaborative team of agents with leader-based delegation."""
    squad_id: str
    name: str
    description: str = ""
    status: SquadStatus = SquadStatus.FORMING
    members: dict[str, SquadMember] = field(default_factory=dict)
    leader_id: str = ""
    discussions: list[DiscussionThread] = field(default_factory=list)
    total_tasks: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def active_members(self) -> list[SquadMember]:
        return [m for m in self.members.values()]

    @property
    def member_count(self) -> int:
        return len(self.members)

    def get_leader(self) -> SquadMember | None:
        return self.members.get(self.leader_id)

    def dict(self) -> dict:
        return {
            "squad_id": self.squad_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "member_count": self.member_count,
            "members": [m.dict() for m in self.members.values()],
            "leader_id": self.leader_id,
            "discussions": [d.dict() for d in self.discussions],
            "total_tasks": self.total_tasks,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── Squad Manager ──

class BuddySquads:
    """Manages collaborative agent squads with trust-based delegation.

    Squads enable agents to work together as teams. A squad leader
    receives incoming tasks and delegates them to the most appropriate
    member based on expertise and trust scores. Members can discuss
    tasks in threads, transfer work between each other, and build
    trust through successful collaboration.

    The squad system enables:
      - Parallel work distribution across specialized agents
      - Leader-based routing for stable task assignment
      - Trust scoring that improves delegation quality over time
      - Discussion threads for team coordination
      - Status tracking across all squad activities
    """

    def __init__(self):
        self._squads: dict[str, Squad] = {}

    # ── Squad Management ──

    def form_squad(
        self,
        name: str,
        description: str = "",
        leader_id: str = "",
    ) -> Squad:
        """Form a new squad."""
        squad_id = f"squad-{uuid.uuid4().hex[:10]}"
        squad = Squad(
            squad_id=squad_id,
            name=name,
            description=description,
            leader_id=leader_id,
        )
        self._squads[squad_id] = squad
        logger.info(f"Squad formed: {name} ({squad_id})")
        return squad

    def dissolve_squad(self, squad_id: str) -> bool:
        """Dissolve a squad."""
        squad = self._squads.get(squad_id)
        if not squad:
            return False
        squad.status = SquadStatus.DISSOLVED
        squad.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Squad dissolved: {squad.name} ({squad_id})")
        return True

    def get_squad(self, squad_id: str) -> Squad | None:
        return self._squads.get(squad_id)

    def list_squads(self, status: SquadStatus | None = None) -> list[Squad]:
        results = list(self._squads.values())
        if status:
            results = [s for s in results if s.status == status]
        return results

    def activate_squad(self, squad_id: str) -> bool:
        squad = self._squads.get(squad_id)
        if not squad:
            return False
        squad.status = SquadStatus.ACTIVE
        squad.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def pause_squad(self, squad_id: str) -> bool:
        squad = self._squads.get(squad_id)
        if not squad:
            return False
        squad.status = SquadStatus.PAUSED
        squad.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    # ── Member Management ──

    def add_member(
        self,
        squad_id: str,
        agent_id: str,
        agent_name: str = "",
        role: MemberRole = MemberRole.GENERALIST,
        expertise: list[str] | None = None,
    ) -> bool:
        """Add an agent to a squad."""
        squad = self._squads.get(squad_id)
        if not squad or agent_id in squad.members:
            return False

        member = SquadMember(
            agent_id=agent_id,
            agent_name=agent_name,
            role=role,
            expertise=expertise or [],
        )
        squad.members[agent_id] = member

        # First member becomes leader if none set
        if not squad.leader_id:
            squad.leader_id = agent_id
            member.role = MemberRole.LEADER

        squad.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Member {agent_id} added to squad {squad_id} as {role.value}")
        return True

    def remove_member(self, squad_id: str, agent_id: str) -> bool:
        """Remove an agent from a squad."""
        squad = self._squads.get(squad_id)
        if not squad or agent_id not in squad.members:
            return False

        del squad.members[agent_id]

        # If leader removed, assign new leader
        if squad.leader_id == agent_id:
            remaining = list(squad.members.keys())
            if remaining:
                squad.leader_id = remaining[0]
                squad.members[remaining[0]].role = MemberRole.LEADER
            else:
                squad.leader_id = ""

        squad.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def set_leader(self, squad_id: str, agent_id: str) -> bool:
        """Designate a new squad leader."""
        squad = self._squads.get(squad_id)
        if not squad or agent_id not in squad.members:
            return False

        # Demote old leader
        if squad.leader_id and squad.leader_id in squad.members:
            squad.members[squad.leader_id].role = MemberRole.GENERALIST

        # Promote new leader
        squad.leader_id = agent_id
        squad.members[agent_id].role = MemberRole.LEADER
        squad.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"New leader {agent_id} for squad {squad_id}")
        return True

    # ── Trust Scoring ──

    def record_task_outcome(
        self,
        squad_id: str,
        agent_id: str,
        success: bool,
    ):
        """Update trust scores based on task outcomes."""
        squad = self._squads.get(squad_id)
        if not squad or agent_id not in squad.members:
            return

        member = squad.members[agent_id]
        if success:
            member.tasks_completed += 1
            member.trust_score = min(1.0, member.trust_score + 0.05)
        else:
            member.tasks_failed += 1
            member.trust_score = max(0.0, member.trust_score - 0.1)

        squad.total_tasks += 1
        squad.updated_at = datetime.now(timezone.utc).isoformat()

    def get_best_member_for_task(
        self,
        squad_id: str,
        required_expertise: list[str] | None = None,
    ) -> SquadMember | None:
        """Find the best squad member for a given task."""
        squad = self._squads.get(squad_id)
        if not squad or not squad.members:
            return None

        candidates = list(squad.members.values())

        if required_expertise:
            # Score candidates by expertise match
            def expertise_score(m: SquadMember) -> float:
                matched = len(set(m.expertise) & set(required_expertise))
                return matched + m.trust_score
            candidates.sort(key=expertise_score, reverse=True)
        else:
            # Sort by trust score
            candidates.sort(key=lambda m: m.trust_score, reverse=True)

        return candidates[0] if candidates else None

    # ── Delegation ──

    def delegate_task(
        self,
        squad_id: str,
        task_description: str,
        required_expertise: list[str] | None = None,
    ) -> dict:
        """Delegate a task to the best available squad member."""
        squad = self._squads.get(squad_id)
        if not squad:
            return {"success": False, "error": "Squad not found"}

        best_member = self.get_best_member_for_task(squad_id, required_expertise)
        if not best_member:
            return {"success": False, "error": "No suitable member found"}

        return {
            "success": True,
            "squad_id": squad_id,
            "assigned_to": best_member.agent_id,
            "agent_name": best_member.agent_name,
            "trust_score": best_member.trust_score,
            "task": task_description,
        }

    # ── Discussions ──

    def start_discussion(
        self,
        squad_id: str,
        topic: str,
        created_by: str,
        task_id: str = "",
    ) -> DiscussionThread | None:
        """Start a discussion thread within a squad."""
        squad = self._squads.get(squad_id)
        if not squad:
            return None

        thread = DiscussionThread(
            thread_id=f"disc-{uuid.uuid4().hex[:8]}",
            squad_id=squad_id,
            topic=topic,
            created_by=created_by,
            task_id=task_id,
        )
        squad.discussions.append(thread)
        squad.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Discussion started in squad {squad_id}: {topic}")
        return thread

    def post_to_discussion(
        self,
        squad_id: str,
        thread_id: str,
        agent_id: str,
        content: str,
    ) -> bool:
        """Post a message to a discussion thread."""
        squad = self._squads.get(squad_id)
        if not squad:
            return False

        for thread in squad.discussions:
            if thread.thread_id == thread_id:
                thread.add_message(agent_id, content)
                squad.updated_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def resolve_discussion(
        self,
        squad_id: str,
        thread_id: str,
        resolution: str,
    ) -> bool:
        """Resolve a discussion thread."""
        squad = self._squads.get(squad_id)
        if not squad:
            return False

        for thread in squad.discussions:
            if thread.thread_id == thread_id:
                thread.status = DiscussionStatus.RESOLVED
                thread.resolution = resolution
                thread.resolved_at = datetime.now(timezone.utc).isoformat()
                squad.updated_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    # ── Statistics ──

    def get_stats(self) -> dict:
        by_status: dict[str, int] = {}
        total_members = 0
        total_tasks = 0

        for s in self._squads.values():
            st = s.status.value
            by_status[st] = by_status.get(st, 0) + 1
            total_members += s.member_count
            total_tasks += s.total_tasks

        return {
            "total_squads": len(self._squads),
            "by_status": by_status,
            "total_members": total_members,
            "total_tasks_processed": total_tasks,
            "avg_trust_score": self._compute_avg_trust(),
        }

    def _compute_avg_trust(self) -> float:
        scores = []
        for s in self._squads.values():
            for m in s.members.values():
                scores.append(m.trust_score)
        return sum(scores) / max(len(scores), 1)

    # ── Agents in Squads ──

    def get_agent_squads(self, agent_id: str) -> list[Squad]:
        """Get all squads an agent belongs to."""
        return [
            s for s in self._squads.values()
            if agent_id in s.members
        ]