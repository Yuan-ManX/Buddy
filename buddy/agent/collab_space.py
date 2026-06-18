"""Buddy Collaboration Space — shared persistent workspace for multi-agent collaboration.

Provides a collaborative environment where multiple agents can work together
in shared rooms, inspired by the "AI Space" concept. Includes session management,
artifact sharing, consensus building, and collaboration analytics.

Architecture:
    CollaborationSpace (singleton)
    ├── CollaborationRoom (shared workspace with configurable capacity)
    │   ├── CollaborationSession (session lifecycle and participant management)
    │   ├── ArtifactBoard (shared artifact management with versioning)
    │   └── ConsensusEngine (group decision-making and voting)
    └── CollaborationAnalytics (insights about collaboration)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.collab_space")


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class RoomType(str, Enum):
    """Types of collaboration rooms for different purposes."""
    BRAINSTORM = "brainstorm"
    CODE_REVIEW = "code_review"
    PROBLEM_SOLVING = "problem_solving"
    RESEARCH = "research"
    GENERAL = "general"


class RoomState(str, Enum):
    """Lifecycle states for a collaboration room."""
    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"
    LOCKED = "locked"


class SessionStatus(str, Enum):
    """Lifecycle states for a collaboration session."""
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class MessageRole(str, Enum):
    """Roles for messages in a collaboration session thread."""
    PROPOSAL = "proposal"
    QUESTION = "question"
    ANSWER = "answer"
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    COMMENT = "comment"


class VoteOption(str, Enum):
    """Voting options for proposals."""
    AGREE = "agree"
    DISAGREE = "disagree"
    ABSTAIN = "abstain"
    BLOCK = "block"


class ConsensusType(str, Enum):
    """Types of consensus required for decision-making."""
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    SUPERMAJORITY = "supermajority"


class ProposalStatus(str, Enum):
    """Lifecycle states for a proposal in the consensus engine."""
    PENDING = "pending"
    VOTING = "voting"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEADLOCKED = "deadlocked"
    WITHDRAWN = "withdrawn"


class ArtifactType(str, Enum):
    """Types of artifacts that can be shared in a collaboration room."""
    CODE = "code"
    DOCUMENT = "document"
    DIAGRAM = "diagram"
    DATA = "data"
    LINK = "link"
    NOTE = "note"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes — Collaboration Room
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CollaborationRoom:
    """A shared persistent workspace for agent collaboration.

    Rooms provide a configurable environment where agents can join,
    create sessions, share artifacts, and make group decisions.
    Context and artifacts persist across sessions.
    """

    id: str = field(default_factory=lambda: f"room-{uuid.uuid4().hex[:12]}")
    name: str = "New Room"
    description: str = ""
    room_type: RoomType = RoomType.GENERAL
    state: RoomState = RoomState.ACTIVE
    max_agents: int = 10
    max_sessions: int = 5
    created_by: str = ""
    tags: list[str] = field(default_factory=list)
    persistent_context: dict[str, Any] = field(default_factory=dict)
    active_agents: list[str] = field(default_factory=list)
    session_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def agent_count(self) -> int:
        return len(self.active_agents)

    @property
    def session_count(self) -> int:
        return len(self.session_ids)

    @property
    def is_full(self) -> bool:
        return self.agent_count >= self.max_agents

    @property
    def can_create_session(self) -> bool:
        return self.session_count < self.max_sessions

    def add_agent(self, agent_id: str) -> bool:
        if agent_id in self.active_agents:
            return False
        if self.agent_count >= self.max_agents:
            return False
        self.active_agents.append(agent_id)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def remove_agent(self, agent_id: str) -> bool:
        if agent_id not in self.active_agents:
            return False
        self.active_agents.remove(agent_id)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def add_session(self, session_id: str) -> bool:
        if self.session_count >= self.max_sessions:
            return False
        self.session_ids.append(session_id)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def remove_session(self, session_id: str) -> bool:
        if session_id not in self.session_ids:
            return False
        self.session_ids.remove(session_id)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def update_context(self, key: str, value: Any) -> None:
        self.persistent_context[key] = value
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def get_context(self, key: str, default: Any = None) -> Any:
        return self.persistent_context.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "room_type": self.room_type.value,
            "state": self.state.value,
            "max_agents": self.max_agents,
            "max_sessions": self.max_sessions,
            "created_by": self.created_by,
            "tags": self.tags,
            "agent_count": self.agent_count,
            "session_count": self.session_count,
            "active_agents": self.active_agents,
            "session_ids": self.session_ids,
            "persistent_context_keys": list(self.persistent_context.keys()),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes — Collaboration Session
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SessionMessage:
    """A single message in a collaboration session thread."""

    id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:12]}")
    sender_id: str = ""
    sender_name: str = ""
    role: MessageRole = MessageRole.COMMENT
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reply_to: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "metadata": self.metadata,
        }


@dataclass
class Vote:
    """A vote cast by a participant on a proposal."""

    voter_id: str = ""
    voter_name: str = ""
    option: VoteOption = VoteOption.ABSTAIN
    reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "voter_id": self.voter_id,
            "voter_name": self.voter_name,
            "option": self.option.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class Poll:
    """A poll created within a collaboration session for group decisions."""

    id: str = field(default_factory=lambda: f"poll-{uuid.uuid4().hex[:12]}")
    question: str = ""
    options: list[str] = field(default_factory=list)
    created_by: str = ""
    is_open: bool = True
    votes: dict[str, str] = field(default_factory=dict)  # voter_id -> option
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: str = ""

    def cast_vote(self, voter_id: str, option: str) -> bool:
        if not self.is_open:
            return False
        if option not in self.options:
            return False
        self.votes[voter_id] = option
        return True

    def close(self) -> dict[str, int]:
        self.is_open = False
        self.closed_at = datetime.now(timezone.utc).isoformat()
        tally: dict[str, int] = {opt: 0 for opt in self.options}
        for opt in self.votes.values():
            if opt in tally:
                tally[opt] += 1
        return tally

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "options": self.options,
            "created_by": self.created_by,
            "is_open": self.is_open,
            "vote_count": len(self.votes),
            "votes": self.votes,
            "created_at": self.created_at,
            "closed_at": self.closed_at,
        }


@dataclass
class CollaborationSession:
    """A single collaboration session within a room.

    Manages the session lifecycle, participant membership, message threads,
    and polling for group decisions.
    """

    id: str = field(default_factory=lambda: f"session-{uuid.uuid4().hex[:12]}")
    room_id: str = ""
    title: str = "New Session"
    description: str = ""
    status: SessionStatus = SessionStatus.CREATED
    participants: list[str] = field(default_factory=list)
    invited: list[str] = field(default_factory=list)
    messages: list[SessionMessage] = field(default_factory=list)
    polls: list[Poll] = field(default_factory=list)
    shared_artifact_ids: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def participant_count(self) -> int:
        return len(self.participants)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def add_participant(self, agent_id: str) -> bool:
        if agent_id in self.participants:
            return False
        self.participants.append(agent_id)
        if agent_id in self.invited:
            self.invited.remove(agent_id)
        return True

    def remove_participant(self, agent_id: str) -> bool:
        if agent_id not in self.participants:
            return False
        self.participants.remove(agent_id)
        return True

    def invite_agent(self, agent_id: str) -> bool:
        if agent_id in self.participants or agent_id in self.invited:
            return False
        self.invited.append(agent_id)
        return True

    def add_message(
        self,
        sender_id: str,
        content: str,
        role: MessageRole = MessageRole.COMMENT,
        sender_name: str = "",
        reply_to: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SessionMessage:
        msg = SessionMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            role=role,
            content=content,
            reply_to=reply_to,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        return msg

    def get_messages_by_role(self, role: MessageRole) -> list[SessionMessage]:
        return [m for m in self.messages if m.role == role]

    def get_action_items(self) -> list[SessionMessage]:
        return self.get_messages_by_role(MessageRole.ACTION_ITEM)

    def get_decisions(self) -> list[SessionMessage]:
        return self.get_messages_by_role(MessageRole.DECISION)

    def create_poll(self, question: str, options: list[str], created_by: str) -> Poll:
        poll = Poll(question=question, options=options, created_by=created_by)
        self.polls.append(poll)
        return poll

    def get_poll(self, poll_id: str) -> Poll | None:
        for p in self.polls:
            if p.id == poll_id:
                return p
        return None

    def share_artifact(self, artifact_id: str) -> None:
        if artifact_id not in self.shared_artifact_ids:
            self.shared_artifact_ids.append(artifact_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "participant_count": self.participant_count,
            "participants": self.participants,
            "invited": self.invited,
            "message_count": self.message_count,
            "poll_count": len(self.polls),
            "shared_artifact_count": len(self.shared_artifact_ids),
            "created_by": self.created_by,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes — Artifact Board
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ArtifactVersion:
    """A single version of an artifact."""

    version: int = 1
    content: str = ""
    updated_by: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    change_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "content_length": len(self.content),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at,
            "change_summary": self.change_summary,
        }


@dataclass
class Artifact:
    """A shared artifact in a collaboration room.

    Artifacts can be code snippets, documents, diagrams, data, links, or notes.
    Supports version tracking, tagging, and categorization.
    """

    id: str = field(default_factory=lambda: f"artifact-{uuid.uuid4().hex[:12]}")
    room_id: str = ""
    title: str = ""
    description: str = ""
    artifact_type: ArtifactType = ArtifactType.NOTE
    content: str = ""
    tags: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    versions: list[ArtifactVersion] = field(default_factory=list)
    current_version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.versions:
            self.versions.append(ArtifactVersion(
                version=1,
                content=self.content,
                updated_by=self.created_by,
                change_summary="Initial version",
            ))

    def update_content(self, content: str, updated_by: str, change_summary: str = "") -> None:
        self.content = content
        self.current_version += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.versions.append(ArtifactVersion(
            version=self.current_version,
            content=content,
            updated_by=updated_by,
            change_summary=change_summary,
        ))

    def get_version(self, version: int) -> ArtifactVersion | None:
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def get_latest_version(self) -> ArtifactVersion:
        return self.versions[-1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "title": self.title,
            "description": self.description,
            "artifact_type": self.artifact_type.value,
            "content_length": len(self.content),
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_version": self.current_version,
            "version_count": len(self.versions),
            "metadata": self.metadata,
        }


class ArtifactBoard:
    """Manages shared artifacts with versioning, tagging, and search.

    Provides a shared space for agents to create, update, and retrieve
    artifacts across collaboration sessions. Each artifact tracks its
    full version history.
    """

    def __init__(self, room_id: str):
        self.room_id = room_id
        self._artifacts: dict[str, Artifact] = {}

    def create_artifact(
        self,
        title: str,
        content: str,
        artifact_type: ArtifactType = ArtifactType.NOTE,
        created_by: str = "",
        description: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        artifact = Artifact(
            room_id=self.room_id,
            title=title,
            description=description,
            artifact_type=artifact_type,
            content=content,
            created_by=created_by,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._artifacts[artifact.id] = artifact
        logger.debug(f"Artifact created: {artifact.id} ({artifact.title})")
        return artifact

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        return self._artifacts.get(artifact_id)

    def update_artifact(
        self,
        artifact_id: str,
        content: str,
        updated_by: str,
        change_summary: str = "",
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> Artifact | None:
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None
        artifact.update_content(content, updated_by, change_summary)
        if title is not None:
            artifact.title = title
        if description is not None:
            artifact.description = description
        if tags is not None:
            artifact.tags = tags
        return artifact

    def delete_artifact(self, artifact_id: str) -> bool:
        if artifact_id in self._artifacts:
            del self._artifacts[artifact_id]
            return True
        return False

    def list_artifacts(
        self,
        artifact_type: ArtifactType | None = None,
        tag: str | None = None,
    ) -> list[Artifact]:
        results = list(self._artifacts.values())
        if artifact_type:
            results = [a for a in results if a.artifact_type == artifact_type]
        if tag:
            results = [a for a in results if tag in a.tags]
        return sorted(results, key=lambda a: a.updated_at, reverse=True)

    def search_artifacts(self, query: str) -> list[Artifact]:
        query_lower = query.lower()
        results = []
        for a in self._artifacts.values():
            if (query_lower in a.title.lower() or
                query_lower in a.description.lower() or
                query_lower in a.content.lower() or
                any(query_lower in t.lower() for t in a.tags)):
                results.append(a)
        return sorted(results, key=lambda a: a.updated_at, reverse=True)

    def get_by_tag(self, tag: str) -> list[Artifact]:
        return [a for a in self._artifacts.values() if tag in a.tags]

    def get_stats(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        all_tags: dict[str, int] = {}
        total_versions = 0
        for a in self._artifacts.values():
            t = a.artifact_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
            for tag in a.tags:
                all_tags[tag] = all_tags.get(tag, 0) + 1
            total_versions += len(a.versions)
        return {
            "total_artifacts": len(self._artifacts),
            "by_type": type_counts,
            "top_tags": dict(sorted(all_tags.items(), key=lambda x: -x[1])[:10]),
            "total_versions": total_versions,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes — Consensus Engine
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Proposal:
    """A proposal for group decision-making within a collaboration room."""

    id: str = field(default_factory=lambda: f"proposal-{uuid.uuid4().hex[:12]}")
    room_id: str = ""
    session_id: str = ""
    title: str = ""
    description: str = ""
    proposed_by: str = ""
    proposed_by_name: str = ""
    consensus_type: ConsensusType = ConsensusType.MAJORITY
    status: ProposalStatus = ProposalStatus.PENDING
    votes: dict[str, Vote] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    voting_started_at: str = ""
    resolved_at: str = ""
    resolution_note: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def vote_count(self) -> int:
        return len(self.votes)

    @property
    def agree_count(self) -> int:
        return sum(1 for v in self.votes.values() if v.option == VoteOption.AGREE)

    @property
    def disagree_count(self) -> int:
        return sum(1 for v in self.votes.values() if v.option == VoteOption.DISAGREE)

    @property
    def abstain_count(self) -> int:
        return sum(1 for v in self.votes.values() if v.option == VoteOption.ABSTAIN)

    @property
    def block_count(self) -> int:
        return sum(1 for v in self.votes.values() if v.option == VoteOption.BLOCK)

    def cast_vote(self, voter_id: str, voter_name: str, option: VoteOption, reason: str = "") -> Vote:
        vote = Vote(voter_id=voter_id, voter_name=voter_name, option=option, reason=reason)
        self.votes[voter_id] = vote
        return vote

    def has_voted(self, voter_id: str) -> bool:
        return voter_id in self.votes

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "session_id": self.session_id,
            "title": self.title,
            "description": self.description,
            "proposed_by": self.proposed_by,
            "proposed_by_name": self.proposed_by_name,
            "consensus_type": self.consensus_type.value,
            "status": self.status.value,
            "vote_count": self.vote_count,
            "agree_count": self.agree_count,
            "disagree_count": self.disagree_count,
            "abstain_count": self.abstain_count,
            "block_count": self.block_count,
            "votes": {vid: v.to_dict() for vid, v in self.votes.items()},
            "created_at": self.created_at,
            "voting_started_at": self.voting_started_at,
            "resolved_at": self.resolved_at,
            "resolution_note": self.resolution_note,
        }


class ConsensusEngine:
    """Group decision-making engine for collaboration rooms.

    Supports proposal creation, voting, consensus checking with multiple
    types (unanimous, majority, supermajority), and deadlock resolution.
    """

    def __init__(self, room_id: str):
        self.room_id = room_id
        self._proposals: dict[str, Proposal] = {}
        self._decisions: list[dict[str, Any]] = []

    def create_proposal(
        self,
        title: str,
        description: str,
        proposed_by: str,
        proposed_by_name: str = "",
        session_id: str = "",
        consensus_type: ConsensusType = ConsensusType.MAJORITY,
        metadata: dict[str, Any] | None = None,
    ) -> Proposal:
        proposal = Proposal(
            room_id=self.room_id,
            session_id=session_id,
            title=title,
            description=description,
            proposed_by=proposed_by,
            proposed_by_name=proposed_by_name,
            consensus_type=consensus_type,
            metadata=metadata or {},
        )
        self._proposals[proposal.id] = proposal
        logger.info(f"Proposal created: {proposal.id} ({proposal.title})")
        return proposal

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        return self._proposals.get(proposal_id)

    def start_voting(self, proposal_id: str) -> bool:
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.PENDING:
            return False
        proposal.status = ProposalStatus.VOTING
        proposal.voting_started_at = datetime.now(timezone.utc).isoformat()
        return True

    def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        voter_name: str,
        option: VoteOption,
        reason: str = "",
    ) -> bool:
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.VOTING:
            return False
        proposal.cast_vote(voter_id, voter_name, option, reason)
        return True

    def check_consensus(self, proposal_id: str, total_eligible: int) -> ProposalStatus | None:
        """Check if consensus has been reached for a proposal.

        Args:
            proposal_id: The proposal to check.
            total_eligible: Total number of eligible voters.

        Returns:
            The new status if consensus is reached, None if still voting.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.VOTING:
            return None

        voted = proposal.vote_count
        if voted < total_eligible:
            return None

        agree = proposal.agree_count
        blocks = proposal.block_count

        # Any block vetoes the proposal
        if blocks > 0:
            proposal.status = ProposalStatus.REJECTED
            proposal.resolved_at = datetime.now(timezone.utc).isoformat()
            proposal.resolution_note = f"Rejected due to {blocks} block vote(s)"
            return ProposalStatus.REJECTED

        if proposal.consensus_type == ConsensusType.UNANIMOUS:
            if agree == total_eligible:
                proposal.status = ProposalStatus.ACCEPTED
                proposal.resolved_at = datetime.now(timezone.utc).isoformat()
                proposal.resolution_note = "Accepted by unanimous consent"
                return ProposalStatus.ACCEPTED
            else:
                proposal.status = ProposalStatus.REJECTED
                proposal.resolved_at = datetime.now(timezone.utc).isoformat()
                proposal.resolution_note = "Rejected — unanimous consent not achieved"
                return ProposalStatus.REJECTED

        elif proposal.consensus_type == ConsensusType.SUPERMAJORITY:
            threshold = (2 * total_eligible) // 3  # Two-thirds
            if agree >= threshold:
                proposal.status = ProposalStatus.ACCEPTED
                proposal.resolved_at = datetime.now(timezone.utc).isoformat()
                proposal.resolution_note = f"Accepted by supermajority ({agree}/{total_eligible})"
                return ProposalStatus.ACCEPTED
            else:
                proposal.status = ProposalStatus.REJECTED
                proposal.resolved_at = datetime.now(timezone.utc).isoformat()
                proposal.resolution_note = "Rejected — supermajority not achieved"
                return ProposalStatus.REJECTED

        else:  # MAJORITY
            threshold = (total_eligible // 2) + 1
            if agree >= threshold:
                proposal.status = ProposalStatus.ACCEPTED
                proposal.resolved_at = datetime.now(timezone.utc).isoformat()
                proposal.resolution_note = f"Accepted by majority ({agree}/{total_eligible})"
                return ProposalStatus.ACCEPTED
            else:
                proposal.status = ProposalStatus.REJECTED
                proposal.resolved_at = datetime.now(timezone.utc).isoformat()
                proposal.resolution_note = "Rejected — majority not achieved"
                return ProposalStatus.REJECTED

    def resolve_deadlock(self, proposal_id: str, resolution: str) -> bool:
        """Resolve a deadlocked proposal with a manual resolution."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return False
        proposal.status = ProposalStatus.DEADLOCKED
        proposal.resolved_at = datetime.now(timezone.utc).isoformat()
        proposal.resolution_note = f"Deadlock resolved: {resolution}"
        self._decisions.append({
            "proposal_id": proposal_id,
            "title": proposal.title,
            "resolution": resolution,
            "resolved_at": proposal.resolved_at,
        })
        logger.info(f"Deadlock resolved for proposal {proposal_id}: {resolution}")
        return True

    def withdraw_proposal(self, proposal_id: str) -> bool:
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status not in (ProposalStatus.PENDING, ProposalStatus.VOTING):
            return False
        proposal.status = ProposalStatus.WITHDRAWN
        proposal.resolved_at = datetime.now(timezone.utc).isoformat()
        return True

    def record_decision(
        self,
        proposal_id: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        proposal = self._proposals.get(proposal_id)
        title = proposal.title if proposal else proposal_id
        self._decisions.append({
            "proposal_id": proposal_id,
            "title": title,
            "outcome": outcome,
            "details": details or {},
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })

    def list_proposals(
        self,
        status: ProposalStatus | None = None,
    ) -> list[Proposal]:
        results = list(self._proposals.values())
        if status:
            results = [p for p in results if p.status == status]
        return sorted(results, key=lambda p: p.created_at, reverse=True)

    def list_decisions(self) -> list[dict[str, Any]]:
        return list(self._decisions)

    def get_stats(self) -> dict[str, Any]:
        proposals = list(self._proposals.values())
        status_counts: dict[str, int] = {}
        for p in proposals:
            s = p.status.value
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "total_proposals": len(proposals),
            "by_status": status_counts,
            "total_decisions": len(self._decisions),
            "accepted_count": status_counts.get("accepted", 0),
            "rejected_count": status_counts.get("rejected", 0),
            "deadlocked_count": status_counts.get("deadlocked", 0),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Collaboration Analytics
# ═══════════════════════════════════════════════════════════════════════════

class CollaborationAnalytics:
    """Provides insights about collaboration within a room.

    Tracks participation metrics, contribution analysis, outcome quality,
    and collaboration patterns to help understand team dynamics.
    """

    def __init__(self):
        self._participation_log: dict[str, list[dict[str, Any]]] = {}  # agent_id -> events
        self._contribution_log: dict[str, list[dict[str, Any]]] = {}  # agent_id -> contributions
        self._session_outcomes: list[dict[str, Any]] = []

    def log_participation(
        self,
        agent_id: str,
        room_id: str,
        session_id: str,
        event_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "agent_id": agent_id,
            "room_id": room_id,
            "session_id": session_id,
            "event_type": event_type,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._participation_log.setdefault(agent_id, []).append(entry)

    def log_contribution(
        self,
        agent_id: str,
        room_id: str,
        contribution_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "agent_id": agent_id,
            "room_id": room_id,
            "contribution_type": contribution_type,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._contribution_log.setdefault(agent_id, []).append(entry)

    def record_session_outcome(
        self,
        session_id: str,
        room_id: str,
        quality_score: float,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._session_outcomes.append({
            "session_id": session_id,
            "room_id": room_id,
            "quality_score": quality_score,
            "notes": notes,
            "metadata": metadata or {},
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })

    def get_participation_metrics(
        self,
        agent_id: str | None = None,
        room_id: str | None = None,
    ) -> dict[str, Any]:
        events = []
        if agent_id:
            events = self._participation_log.get(agent_id, [])
        else:
            for agent_events in self._participation_log.values():
                events.extend(agent_events)

        if room_id:
            events = [e for e in events if e.get("room_id") == room_id]

        event_types: dict[str, int] = {}
        per_agent: dict[str, int] = {}
        for e in events:
            et = e["event_type"]
            event_types[et] = event_types.get(et, 0) + 1
            aid = e["agent_id"]
            per_agent[aid] = per_agent.get(aid, 0) + 1

        return {
            "total_events": len(events),
            "event_types": event_types,
            "events_per_agent": per_agent,
            "unique_agents": len(set(e["agent_id"] for e in events)),
        }

    def get_contribution_metrics(
        self,
        agent_id: str | None = None,
        room_id: str | None = None,
    ) -> dict[str, Any]:
        contributions = []
        if agent_id:
            contributions = self._contribution_log.get(agent_id, [])
        else:
            for agent_contribs in self._contribution_log.values():
                contributions.extend(agent_contribs)

        if room_id:
            contributions = [c for c in contributions if c.get("room_id") == room_id]

        type_counts: dict[str, int] = {}
        per_agent: dict[str, int] = {}
        for c in contributions:
            ct = c["contribution_type"]
            type_counts[ct] = type_counts.get(ct, 0) + 1
            aid = c["agent_id"]
            per_agent[aid] = per_agent.get(aid, 0) + 1

        return {
            "total_contributions": len(contributions),
            "by_type": type_counts,
            "by_agent": per_agent,
            "unique_contributors": len(set(c["agent_id"] for c in contributions)),
        }

    def get_outcome_quality(
        self,
        room_id: str | None = None,
    ) -> dict[str, Any]:
        outcomes = self._session_outcomes
        if room_id:
            outcomes = [o for o in outcomes if o.get("room_id") == room_id]

        if not outcomes:
            return {"total_sessions": 0, "message": "No session outcomes recorded"}

        scores = [o["quality_score"] for o in outcomes]
        return {
            "total_sessions": len(outcomes),
            "avg_quality": round(sum(scores) / len(scores), 2),
            "min_quality": min(scores),
            "max_quality": max(scores),
            "sessions_above_8": sum(1 for s in scores if s >= 8.0),
            "sessions_below_5": sum(1 for s in scores if s < 5.0),
        }

    def get_collaboration_patterns(
        self,
        room_id: str | None = None,
    ) -> dict[str, Any]:
        events = []
        for agent_events in self._participation_log.values():
            events.extend(agent_events)
        if room_id:
            events = [e for e in events if e.get("room_id") == room_id]

        # Analyze session participation patterns
        sessions: dict[str, set[str]] = {}
        for e in events:
            sid = e.get("session_id", "unknown")
            sessions.setdefault(sid, set()).add(e["agent_id"])

        session_sizes = [len(members) for members in sessions.values()]

        return {
            "total_sessions_analyzed": len(sessions),
            "avg_participants_per_session": round(
                sum(session_sizes) / max(len(session_sizes), 1), 1
            ),
            "max_participants_in_session": max(session_sizes) if session_sizes else 0,
            "solo_sessions": sum(1 for s in session_sizes if s == 1),
            "multi_agent_sessions": sum(1 for s in session_sizes if s > 1),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_participation_events": sum(
                len(events) for events in self._participation_log.values()
            ),
            "total_contributions": sum(
                len(contribs) for contribs in self._contribution_log.values()
            ),
            "total_session_outcomes": len(self._session_outcomes),
            "unique_agents_tracked": len(
                set(self._participation_log.keys()) | set(self._contribution_log.keys())
            ),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Collaboration Space (Facade)
# ═══════════════════════════════════════════════════════════════════════════

class CollaborationSpace:
    """Central facade for multi-agent collaboration management.

    Provides a unified interface for creating rooms, managing sessions,
    sharing artifacts, making group decisions, and analyzing collaboration.

    Usage:
        cs = CollaborationSpace()
        room = cs.create_room(name="Design Review", room_type=RoomType.CODE_REVIEW)
        session = cs.create_session(room.id, title="API Review")
        cs.add_participant(session.id, "agent-1")
        cs.add_message(session.id, "agent-1", "Let's review the endpoint design",
                       role=MessageRole.PROPOSAL)
        artifact = cs.create_artifact(room.id, "API Spec", content="...",
                                      artifact_type=ArtifactType.DOCUMENT)
        proposal = cs.create_proposal(room.id, "Use REST over GraphQL",
                                      "We should use REST for simpler tooling",
                                      proposed_by="agent-1")
        cs.start_voting(room.id, proposal.id)
        cs.cast_vote(room.id, proposal.id, "agent-2", "Agent 2", VoteOption.AGREE,
                     "REST is simpler for our use case")
        result = cs.check_consensus(room.id, proposal.id, total_eligible=3)
    """

    def __init__(self):
        self._rooms: dict[str, CollaborationRoom] = {}
        self._sessions: dict[str, CollaborationSession] = {}
        self._artifact_boards: dict[str, ArtifactBoard] = {}  # room_id -> board
        self._consensus_engines: dict[str, ConsensusEngine] = {}  # room_id -> engine
        self.analytics = CollaborationAnalytics()

    # ── Room Management ──

    def create_room(
        self,
        name: str,
        description: str = "",
        room_type: RoomType = RoomType.GENERAL,
        created_by: str = "",
        max_agents: int = 10,
        max_sessions: int = 5,
        tags: list[str] | None = None,
    ) -> CollaborationRoom:
        room = CollaborationRoom(
            name=name,
            description=description,
            room_type=room_type,
            created_by=created_by,
            max_agents=max_agents,
            max_sessions=max_sessions,
            tags=tags or [],
        )
        self._rooms[room.id] = room
        self._artifact_boards[room.id] = ArtifactBoard(room.id)
        self._consensus_engines[room.id] = ConsensusEngine(room.id)
        logger.info(f"Room created: {room.id} ({name})")
        return room

    def get_room(self, room_id: str) -> CollaborationRoom | None:
        return self._rooms.get(room_id)

    def list_rooms(
        self,
        room_type: RoomType | None = None,
        state: RoomState | None = None,
    ) -> list[CollaborationRoom]:
        results = list(self._rooms.values())
        if room_type:
            results = [r for r in results if r.room_type == room_type]
        if state:
            results = [r for r in results if r.state == state]
        return results

    def update_room_state(self, room_id: str, state: RoomState) -> bool:
        room = self._rooms.get(room_id)
        if not room:
            return False
        room.state = state
        room.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def add_agent_to_room(self, room_id: str, agent_id: str) -> bool:
        room = self._rooms.get(room_id)
        if not room:
            return False
        return room.add_agent(agent_id)

    def remove_agent_from_room(self, room_id: str, agent_id: str) -> bool:
        room = self._rooms.get(room_id)
        if not room:
            return False
        return room.remove_agent(agent_id)

    def update_room_context(self, room_id: str, key: str, value: Any) -> bool:
        room = self._rooms.get(room_id)
        if not room:
            return False
        room.update_context(key, value)
        return True

    def get_room_context(self, room_id: str, key: str, default: Any = None) -> Any:
        room = self._rooms.get(room_id)
        if not room:
            return default
        return room.get_context(key, default)

    # ── Session Management ──

    def create_session(
        self,
        room_id: str,
        title: str,
        description: str = "",
        created_by: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CollaborationSession | None:
        room = self._rooms.get(room_id)
        if not room or not room.can_create_session:
            return None

        session = CollaborationSession(
            room_id=room_id,
            title=title,
            description=description,
            created_by=created_by,
            metadata=metadata or {},
        )
        session.status = SessionStatus.ACTIVE
        session.started_at = datetime.now(timezone.utc).isoformat()
        self._sessions[session.id] = session
        room.add_session(session.id)
        logger.info(f"Session created: {session.id} in room {room_id}")
        return session

    def get_session(self, session_id: str) -> CollaborationSession | None:
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        room_id: str | None = None,
        status: SessionStatus | None = None,
    ) -> list[CollaborationSession]:
        results = list(self._sessions.values())
        if room_id:
            results = [s for s in results if s.room_id == room_id]
        if status:
            results = [s for s in results if s.status == status]
        return results

    def update_session_status(self, session_id: str, status: SessionStatus) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.status = status
        if status == SessionStatus.COMPLETED:
            session.completed_at = datetime.now(timezone.utc).isoformat()
        return True

    def add_participant(self, session_id: str, agent_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        return session.add_participant(agent_id)

    def remove_participant(self, session_id: str, agent_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        return session.remove_participant(agent_id)

    def invite_to_session(self, session_id: str, agent_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        return session.invite_agent(agent_id)

    # ── Messaging ──

    def add_message(
        self,
        session_id: str,
        sender_id: str,
        content: str,
        role: MessageRole = MessageRole.COMMENT,
        sender_name: str = "",
        reply_to: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SessionMessage | None:
        session = self._sessions.get(session_id)
        if not session:
            return None
        return session.add_message(
            sender_id=sender_id,
            content=content,
            role=role,
            sender_name=sender_name,
            reply_to=reply_to,
            metadata=metadata,
        )

    def get_session_messages(
        self,
        session_id: str,
        role: MessageRole | None = None,
    ) -> list[SessionMessage]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        if role:
            return session.get_messages_by_role(role)
        return session.messages

    # ── Polling ──

    def create_poll(
        self,
        session_id: str,
        question: str,
        options: list[str],
        created_by: str,
    ) -> Poll | None:
        session = self._sessions.get(session_id)
        if not session:
            return None
        return session.create_poll(question, options, created_by)

    def cast_poll_vote(
        self,
        session_id: str,
        poll_id: str,
        voter_id: str,
        option: str,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        poll = session.get_poll(poll_id)
        if not poll:
            return False
        return poll.cast_vote(voter_id, option)

    def close_poll(self, session_id: str, poll_id: str) -> dict[str, int] | None:
        session = self._sessions.get(session_id)
        if not session:
            return None
        poll = session.get_poll(poll_id)
        if not poll:
            return None
        return poll.close()

    # ── Artifact Management ──

    def _get_board(self, room_id: str) -> ArtifactBoard | None:
        return self._artifact_boards.get(room_id)

    def create_artifact(
        self,
        room_id: str,
        title: str,
        content: str,
        artifact_type: ArtifactType = ArtifactType.NOTE,
        created_by: str = "",
        description: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact | None:
        board = self._get_board(room_id)
        if not board:
            return None
        return board.create_artifact(
            title=title,
            content=content,
            artifact_type=artifact_type,
            created_by=created_by,
            description=description,
            tags=tags,
            metadata=metadata,
        )

    def get_artifact(self, room_id: str, artifact_id: str) -> Artifact | None:
        board = self._get_board(room_id)
        if not board:
            return None
        return board.get_artifact(artifact_id)

    def update_artifact(
        self,
        room_id: str,
        artifact_id: str,
        content: str,
        updated_by: str,
        change_summary: str = "",
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> Artifact | None:
        board = self._get_board(room_id)
        if not board:
            return None
        return board.update_artifact(
            artifact_id=artifact_id,
            content=content,
            updated_by=updated_by,
            change_summary=change_summary,
            title=title,
            description=description,
            tags=tags,
        )

    def delete_artifact(self, room_id: str, artifact_id: str) -> bool:
        board = self._get_board(room_id)
        if not board:
            return False
        return board.delete_artifact(artifact_id)

    def list_artifacts(
        self,
        room_id: str,
        artifact_type: ArtifactType | None = None,
        tag: str | None = None,
    ) -> list[Artifact]:
        board = self._get_board(room_id)
        if not board:
            return []
        return board.list_artifacts(artifact_type=artifact_type, tag=tag)

    def search_artifacts(self, room_id: str, query: str) -> list[Artifact]:
        board = self._get_board(room_id)
        if not board:
            return []
        return board.search_artifacts(query)

    def share_artifact_in_session(self, session_id: str, artifact_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.share_artifact(artifact_id)
        return True

    # ── Consensus & Decision Making ──

    def _get_consensus(self, room_id: str) -> ConsensusEngine | None:
        return self._consensus_engines.get(room_id)

    def create_proposal(
        self,
        room_id: str,
        title: str,
        description: str,
        proposed_by: str,
        proposed_by_name: str = "",
        session_id: str = "",
        consensus_type: ConsensusType = ConsensusType.MAJORITY,
        metadata: dict[str, Any] | None = None,
    ) -> Proposal | None:
        engine = self._get_consensus(room_id)
        if not engine:
            return None
        return engine.create_proposal(
            title=title,
            description=description,
            proposed_by=proposed_by,
            proposed_by_name=proposed_by_name,
            session_id=session_id,
            consensus_type=consensus_type,
            metadata=metadata,
        )

    def get_proposal(self, room_id: str, proposal_id: str) -> Proposal | None:
        engine = self._get_consensus(room_id)
        if not engine:
            return None
        return engine.get_proposal(proposal_id)

    def start_voting(self, room_id: str, proposal_id: str) -> bool:
        engine = self._get_consensus(room_id)
        if not engine:
            return False
        return engine.start_voting(proposal_id)

    def cast_vote(
        self,
        room_id: str,
        proposal_id: str,
        voter_id: str,
        voter_name: str,
        option: VoteOption,
        reason: str = "",
    ) -> bool:
        engine = self._get_consensus(room_id)
        if not engine:
            return False
        return engine.cast_vote(proposal_id, voter_id, voter_name, option, reason)

    def check_consensus(
        self,
        room_id: str,
        proposal_id: str,
        total_eligible: int,
    ) -> ProposalStatus | None:
        engine = self._get_consensus(room_id)
        if not engine:
            return None
        return engine.check_consensus(proposal_id, total_eligible)

    def resolve_deadlock(self, room_id: str, proposal_id: str, resolution: str) -> bool:
        engine = self._get_consensus(room_id)
        if not engine:
            return False
        return engine.resolve_deadlock(proposal_id, resolution)

    def withdraw_proposal(self, room_id: str, proposal_id: str) -> bool:
        engine = self._get_consensus(room_id)
        if not engine:
            return False
        return engine.withdraw_proposal(proposal_id)

    def list_proposals(
        self,
        room_id: str,
        status: ProposalStatus | None = None,
    ) -> list[Proposal]:
        engine = self._get_consensus(room_id)
        if not engine:
            return []
        return engine.list_proposals(status=status)

    def list_decisions(self, room_id: str) -> list[dict[str, Any]]:
        engine = self._get_consensus(room_id)
        if not engine:
            return []
        return engine.list_decisions()

    # ── Analytics ──

    def log_participation(
        self,
        agent_id: str,
        room_id: str,
        session_id: str,
        event_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.analytics.log_participation(agent_id, room_id, session_id, event_type, details)

    def log_contribution(
        self,
        agent_id: str,
        room_id: str,
        contribution_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.analytics.log_contribution(agent_id, room_id, contribution_type, details)

    def record_session_outcome(
        self,
        session_id: str,
        room_id: str,
        quality_score: float,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.analytics.record_session_outcome(session_id, room_id, quality_score, notes, metadata)

    # ── Statistics ──

    def get_room_stats(self) -> dict[str, Any]:
        rooms = list(self._rooms.values())
        state_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for r in rooms:
            st = r.state.value
            state_counts[st] = state_counts.get(st, 0) + 1
            rt = r.room_type.value
            type_counts[rt] = type_counts.get(rt, 0) + 1
        return {
            "total_rooms": len(rooms),
            "by_state": state_counts,
            "by_type": type_counts,
            "total_agents": sum(r.agent_count for r in rooms),
            "total_sessions": sum(r.session_count for r in rooms),
        }

    def get_session_stats(self) -> dict[str, Any]:
        sessions = list(self._sessions.values())
        status_counts: dict[str, int] = {}
        total_messages = 0
        for s in sessions:
            sc = s.status.value
            status_counts[sc] = status_counts.get(sc, 0) + 1
            total_messages += s.message_count
        return {
            "total_sessions": len(sessions),
            "by_status": status_counts,
            "total_messages": total_messages,
            "total_participants": sum(s.participant_count for s in sessions),
        }

    def get_artifact_stats(self) -> dict[str, Any]:
        total_artifacts = 0
        total_versions = 0
        type_counts: dict[str, int] = {}
        for board in self._artifact_boards.values():
            stats = board.get_stats()
            total_artifacts += stats["total_artifacts"]
            total_versions += stats["total_versions"]
            for atype, count in stats.get("by_type", {}).items():
                type_counts[atype] = type_counts.get(atype, 0) + count
        return {
            "total_artifacts": total_artifacts,
            "total_versions": total_versions,
            "by_type": type_counts,
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "rooms": self.get_room_stats(),
            "sessions": self.get_session_stats(),
            "artifacts": self.get_artifact_stats(),
            "analytics": self.analytics.get_stats(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

collab_space = CollaborationSpace()