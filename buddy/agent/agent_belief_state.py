"""Agent Belief State — epistemic belief tracking, revision, and propagation.

Implements an Epistemic Belief State system for the AI Agent that tracks
beliefs about the world, revises beliefs based on evidence, manages
uncertainty, and propagates belief updates across related propositions.

Core capabilities:
  - Belief Networks: per-agent graphs of propositions and their relationships.
  - Evidence Management: typed evidence with strength and reliability scoring.
  - Bayesian-style Revision: simplified posterior updates from evidence.
  - Consistency Checking: detect conflicting beliefs and resolve them.
  - Belief Propagation: cascade confidence changes to related beliefs.
  - Dependency Chains: traverse belief dependency graphs.
  - Query and Ranking: search beliefs and rank by confidence.

Architecture:
    AgentBeliefEngine (singleton)
    ├── BeliefNetwork (per-agent belief graph)
    │   ├── Belief (proposition + confidence + status)
    │   └── adjacency (related-belief edges)
    ├── Evidence (global evidence store)
    └── BeliefRevision (append-only revision log)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class BeliefStatus(str, Enum):
    """Lifecycle states of a belief."""
    ACTIVE = "active"                # currently held and usable
    SUSPENDED = "suspended"          # temporarily set aside pending evidence
    RETRACTED = "retracted"          # withdrawn but retained for history
    CONFIRMED = "confirmed"          # strongly validated by evidence
    FALSIFIED = "falsified"          # refuted by contradicting evidence
    TENTATIVE = "tentative"          # provisional, awaiting validation


class EvidenceType(str, Enum):
    """Types of evidence that can revise a belief."""
    OBSERVATION = "observation"      # direct sensory or system observation
    TESTIMONY = "testimony"          # reported by another agent or source
    INFERENCE = "inference"          # derived through reasoning
    INTUITION = "intuition"          # heuristic or gut-feeling prior
    AUTHORITY = "authority"          # stated by a trusted authority
    EMPIRICAL = "empirical"          # measured through experiment
    DEDUCTIVE = "deductive"          # logically entailed


class EvidenceStrength(Enum):
    """Strength of a piece of evidence (lower value = stronger)."""
    OVERWHELMING = 0                 # near-decisive evidence
    STRONG = 1                       # highly persuasive
    MODERATE = 2                     # meaningfully persuasive
    WEAK = 3                         # marginally relevant
    NEGLIGIBLE = 4                   # barely moves confidence


class RevisionType(str, Enum):
    """Types of belief revisions."""
    INITIAL = "initial"              # belief first established
    STRENGTHENING = "strengthening"  # confidence increased
    WEAKENING = "weakening"          # confidence decreased
    REVISION = "revision"            # general revision (e.g. propagated)
    RETRACTION = "retraction"        # belief withdrawn
    CONFIRMATION = "confirmation"    # belief confirmed to near-certainty
    FALSIFICATION = "falsification"  # belief refuted to near-zero


class BeliefCategory(str, Enum):
    """Epistemic categories of beliefs."""
    FACTUAL = "factual"              # claims about facts in the world
    PROCEDURAL = "procedural"        # how-to / method knowledge
    CAUSAL = "causal"                # cause-and-effect relationships
    TEMPORAL = "temporal"            # time-ordered relationships
    SPATIAL = "spatial"             # location / layout knowledge
    SOCIAL = "social"               # beliefs about agents and people
    NORMATIVE = "normative"          # rules, norms, obligations
    INTENTIONAL = "intentional"      # goals, plans, intentions
    ABSTRACT = "abstract"            # conceptual / mathematical


class ConfidenceLevel(Enum):
    """Reference confidence thresholds."""
    CERTAIN = 0.95                   # near-certain
    HIGH = 0.8                       # high confidence
    MODERATE = 0.6                   # moderate confidence
    LOW = 0.4                        # low confidence
    UNCERTAIN = 0.2                  # largely uncertain
    UNKNOWN = 0.0                    # no information


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Evidence:
    """A piece of evidence that can support or contradict a belief.

    Evidence is stored globally and may be linked to multiple beliefs. The
    `corroborating` and `contradicting` lists reference other evidence_ids and
    encode evidence-evidence relationships used to infer support direction.
    """
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    content: str = ""
    source: str = ""
    reliability: float = 0.5
    timestamp: float = field(default_factory=time.time)
    corroborating: list[str] = field(default_factory=list)
    contradicting: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value
            if isinstance(self.evidence_type, EvidenceType)
            else str(self.evidence_type),
            "strength": int(self.strength.value)
            if isinstance(self.strength, EvidenceStrength)
            else int(self.strength),
            "content": self.content,
            "source": self.source,
            "reliability": self.reliability,
            "timestamp": self.timestamp,
            "corroborating": list(self.corroborating),
            "contradicting": list(self.contradicting),
        }


@dataclass
class Belief:
    """A single belief held by an agent.

    A belief is a proposition with an associated confidence value in [0, 1],
    a lifecycle status, linked evidence, and relationships to other beliefs.
    The `prior_confidence` field records the confidence before the most recent
    revision, enabling delta analysis.
    """
    belief_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    proposition: str = ""
    description: str = ""
    category: BeliefCategory = BeliefCategory.FACTUAL
    status: BeliefStatus = BeliefStatus.TENTATIVE
    confidence: float = 0.5
    prior_confidence: float = 0.5
    evidence_ids: list[str] = field(default_factory=list)
    related_beliefs: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    agent_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    revision_count: int = 0
    last_revision_type: RevisionType | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "belief_id": self.belief_id,
            "proposition": self.proposition,
            "description": self.description,
            "category": self.category.value
            if isinstance(self.category, BeliefCategory)
            else str(self.category),
            "status": self.status.value
            if isinstance(self.status, BeliefStatus)
            else str(self.status),
            "confidence": self.confidence,
            "prior_confidence": self.prior_confidence,
            "evidence_ids": list(self.evidence_ids),
            "related_beliefs": list(self.related_beliefs),
            "dependencies": list(self.dependencies),
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "revision_count": self.revision_count,
            "last_revision_type": self.last_revision_type.value
            if self.last_revision_type is not None
            and isinstance(self.last_revision_type, RevisionType)
            else (str(self.last_revision_type) if self.last_revision_type is not None else None),
            "metadata": dict(self.metadata),
        }


@dataclass
class BeliefRevision:
    """An immutable record of a single belief revision."""
    revision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    belief_id: str = ""
    revision_type: RevisionType = RevisionType.INITIAL
    old_confidence: float = 0.0
    new_confidence: float = 0.0
    evidence_id: str | None = None
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "belief_id": self.belief_id,
            "revision_type": self.revision_type.value
            if isinstance(self.revision_type, RevisionType)
            else str(self.revision_type),
            "old_confidence": self.old_confidence,
            "new_confidence": self.new_confidence,
            "evidence_id": self.evidence_id,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }


@dataclass
class BeliefNetwork:
    """A per-agent network of beliefs and their relationships.

    The adjacency map encodes directed edges from a belief_id to the list of
    belief_ids it is related to. This graph drives consistency checks and
    propagation.
    """
    network_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    beliefs: dict[str, Belief] = field(default_factory=dict)
    adjacency: dict[str, list[str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    total_revisions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "network_id": self.network_id,
            "agent_id": self.agent_id,
            "beliefs": {
                bid: b.to_dict() if hasattr(b, "to_dict") else dict(b)
                for bid, b in self.beliefs.items()
            },
            "adjacency": {k: list(v) for k, v in self.adjacency.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_revisions": self.total_revisions,
        }


@dataclass
class ConsistencyCheck:
    """Result of a consistency check over a belief network."""
    check_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    network_id: str = ""
    conflicting_beliefs: list[tuple[str, str]] = field(default_factory=list)
    inconsistency_score: float = 0.0
    resolved: bool = False
    resolution_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "network_id": self.network_id,
            "conflicting_beliefs": [list(pair) for pair in self.conflicting_beliefs],
            "inconsistency_score": self.inconsistency_score,
            "resolved": self.resolved,
            "resolution_notes": self.resolution_notes,
        }


@dataclass
class BeliefEngineStats:
    """Aggregate statistics across the entire belief engine."""
    total_networks: int = 0
    total_beliefs: int = 0
    beliefs_by_status: dict[str, int] = field(default_factory=dict)
    beliefs_by_category: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    total_revisions: int = 0
    total_evidence: int = 0
    consistency_issues: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_networks": self.total_networks,
            "total_beliefs": self.total_beliefs,
            "beliefs_by_status": dict(self.beliefs_by_status),
            "beliefs_by_category": dict(self.beliefs_by_category),
            "avg_confidence": self.avg_confidence,
            "total_revisions": self.total_revisions,
            "total_evidence": self.total_evidence,
            "consistency_issues": self.consistency_issues,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Agent Belief Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentBeliefEngine:
    """Epistemic belief engine with Bayesian-style revision and propagation.

    Maintains per-agent belief networks, a global evidence store, and an
    append-only revision log. All state mutations are guarded by a single
    reentrant-safe lock to ensure thread safety.

    The engine implements a simplified Bayesian update for belief revision:
    evidence of a given strength and reliability shifts the posterior
    confidence toward 1 (supporting) or toward 0 (contradicting). Confidence
    changes can be propagated to related beliefs, and conflicting beliefs are
    surfaced through consistency checks.
    """

    # Capacity limits
    MAX_BELIEFS_PER_NETWORK: int = 1000
    MAX_EVIDENCE: int = 5000
    MAX_REVISIONS_LOG: int = 10000

    # Tuning constants
    _CONSISTENCY_GAP_THRESHOLD: float = 0.5   # min |Δconfidence| to flag a conflict
    _PROPAGATION_FACTOR: float = 0.25         # fraction of delta applied to neighbors
    _CONFIRMATION_THRESHOLD: float = 0.95     # confidence at/below which -> CONFIRMED
    _FALSIFICATION_THRESHOLD: float = 0.05    # confidence at/above which -> falsified/retracted

    def __init__(self) -> None:
        self._networks: dict[str, BeliefNetwork] = {}
        self._evidence: dict[str, Evidence] = {}
        self._revisions: list[BeliefRevision] = []
        self._consistency_checks: dict[str, ConsistencyCheck] = {}
        self._agent_networks: dict[str, str] = {}  # agent_id -> network_id
        self._lock = threading.Lock()

    # ── Network Management ───────────────────────────────────────────

    def create_network(self, agent_id: str = "") -> BeliefNetwork:
        """Create a new belief network for an agent.

        Args:
            agent_id: Optional agent identifier owning this network.

        Returns:
            A new BeliefNetwork registered with the engine.
        """
        with self._lock:
            network = BeliefNetwork(agent_id=agent_id)
            self._networks[network.network_id] = network
            if agent_id:
                self._agent_networks[agent_id] = network.network_id
            return network

    def get_network(self, network_id: str) -> BeliefNetwork | None:
        """Retrieve a belief network by its identifier."""
        with self._lock:
            return self._networks.get(network_id)

    def get_network_by_agent(self, agent_id: str) -> BeliefNetwork | None:
        """Retrieve the belief network associated with an agent."""
        with self._lock:
            network_id = self._agent_networks.get(agent_id)
            if network_id is None:
                return None
            return self._networks.get(network_id)

    def list_networks(self) -> list[BeliefNetwork]:
        """List all registered belief networks."""
        with self._lock:
            return list(self._networks.values())

    # ── Belief CRUD ──────────────────────────────────────────────────

    def add_belief(
        self,
        network_id: str,
        proposition: str,
        description: str = "",
        category: BeliefCategory = BeliefCategory.FACTUAL,
        initial_confidence: float = 0.5,
        related_beliefs: list[str] | None = None,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Belief | None:
        """Add a new belief to a network.

        Args:
            network_id: The network to add the belief to.
            proposition: The proposition this belief represents.
            description: Human-readable description of the belief.
            category: Epistemic category of the belief.
            initial_confidence: Starting confidence in [0, 1].
            related_beliefs: IDs of beliefs related to this one.
            dependencies: IDs of beliefs this belief depends on.
            metadata: Arbitrary metadata to attach.

        Returns:
            The created Belief, or None if the network is missing or full.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return None
            if len(network.beliefs) >= self.MAX_BELIEFS_PER_NETWORK:
                return None

            confidence = max(0.0, min(1.0, float(initial_confidence)))
            related = list(related_beliefs) if related_beliefs else []
            deps = list(dependencies) if dependencies else []
            meta = dict(metadata) if metadata else {}

            belief = Belief(
                proposition=proposition,
                description=description,
                category=category,
                status=BeliefStatus.TENTATIVE,
                confidence=confidence,
                prior_confidence=confidence,
                related_beliefs=related,
                dependencies=deps,
                agent_id=network.agent_id,
                metadata=meta,
                last_revision_type=RevisionType.INITIAL,
            )
            network.beliefs[belief.belief_id] = belief

            # Record adjacency edges (bidirectional for related beliefs).
            self._register_adjacency(network, belief.belief_id, related)

            # Dependencies are directional; ensure they exist as nodes in adjacency.
            for dep_id in deps:
                network.adjacency.setdefault(dep_id, [])

            network.updated_at = time.time()
            return belief

    def get_belief(self, network_id: str, belief_id: str) -> Belief | None:
        """Retrieve a belief by its identifier within a network."""
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return None
            return network.beliefs.get(belief_id)

    def update_belief(self, network_id: str, belief_id: str, **kwargs: Any) -> Belief | None:
        """Update mutable fields of a belief.

        Accepts keyword arguments for any of: proposition, description,
        category, status, confidence, related_beliefs, dependencies, metadata.
        Unknown keys are ignored. Confidence is clamped to [0, 1].

        Returns:
            The updated Belief, or None if not found.
        """
        allowed = {
            "proposition", "description", "category", "status", "confidence",
            "related_beliefs", "dependencies", "metadata",
        }
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return None
            belief = network.beliefs.get(belief_id)
            if belief is None:
                return None

            for key, value in kwargs.items():
                if key not in allowed:
                    continue
                if key == "confidence":
                    value = max(0.0, min(1.0, float(value)))
                if key == "status" and isinstance(value, str):
                    value = BeliefStatus(value)
                if key == "category" and isinstance(value, str):
                    value = BeliefCategory(value)
                if key == "related_beliefs":
                    value = list(value) if value else []
                    self._register_adjacency(network, belief_id, value)
                if key == "dependencies":
                    value = list(value) if value else []
                if key == "metadata":
                    value = dict(value) if value else {}
                setattr(belief, key, value)

            belief.updated_at = time.time()
            network.updated_at = time.time()
            return belief

    def remove_belief(self, network_id: str, belief_id: str) -> bool:
        """Remove a belief from a network.

        Also removes references to it from adjacency maps of other beliefs.

        Returns:
            True if the belief was removed, False if not found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return False
            if belief_id not in network.beliefs:
                return False

            del network.beliefs[belief_id]
            network.adjacency.pop(belief_id, None)

            # Remove dangling references in other beliefs and adjacency lists.
            for other in network.beliefs.values():
                if belief_id in other.related_beliefs:
                    other.related_beliefs.remove(belief_id)
                if belief_id in other.dependencies:
                    other.dependencies.remove(belief_id)
            for src, neighbors in network.adjacency.items():
                if belief_id in neighbors:
                    neighbors.remove(belief_id)

            network.updated_at = time.time()
            return True

    def set_belief_status(
        self,
        network_id: str,
        belief_id: str,
        status: BeliefStatus,
    ) -> Belief | None:
        """Set the lifecycle status of a belief.

        Returns:
            The updated Belief, or None if not found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return None
            belief = network.beliefs.get(belief_id)
            if belief is None:
                return None
            belief.status = status
            belief.updated_at = time.time()
            network.updated_at = time.time()
            return belief

    def list_beliefs(
        self,
        network_id: str,
        category: BeliefCategory | None = None,
        status: BeliefStatus | None = None,
        min_confidence: float | None = None,
    ) -> list[Belief]:
        """List beliefs in a network with optional filters.

        Args:
            network_id: The network to query.
            category: If set, only return beliefs in this category.
            status: If set, only return beliefs with this status.
            min_confidence: If set, only return beliefs with confidence >= this.

        Returns:
            A list of matching Belief objects.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return []
            results: list[Belief] = []
            for belief in network.beliefs.values():
                if category is not None and belief.category != category:
                    continue
                if status is not None and belief.status != status:
                    continue
                if min_confidence is not None and belief.confidence < min_confidence:
                    continue
                results.append(belief)
            return results

    # ── Evidence Management ──────────────────────────────────────────

    def add_evidence(
        self,
        evidence_type: EvidenceType = EvidenceType.OBSERVATION,
        strength: EvidenceStrength = EvidenceStrength.MODERATE,
        content: str = "",
        source: str = "",
        reliability: float = 0.5,
    ) -> Evidence:
        """Create and store a new piece of evidence.

        Evidence is stored globally and may be linked to multiple beliefs.
        When the global evidence store exceeds MAX_EVIDENCE, the oldest
        entries are evicted.

        Returns:
            The created Evidence.
        """
        with self._lock:
            evidence = Evidence(
                evidence_type=evidence_type,
                strength=strength,
                content=content,
                source=source,
                reliability=max(0.0, min(1.0, float(reliability))),
            )
            self._evidence[evidence.evidence_id] = evidence
            self._evict_evidence_locked()
            return evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        """Retrieve a piece of evidence by its identifier."""
        with self._lock:
            return self._evidence.get(evidence_id)

    def link_evidence(
        self,
        network_id: str,
        belief_id: str,
        evidence_id: str,
    ) -> Belief | None:
        """Link a piece of evidence to a belief.

        Returns:
            The updated Belief, or None if the network, belief, or evidence
            cannot be found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return None
            belief = network.beliefs.get(belief_id)
            if belief is None:
                return None
            if evidence_id not in self._evidence:
                return None
            if evidence_id not in belief.evidence_ids:
                belief.evidence_ids.append(evidence_id)
            belief.updated_at = time.time()
            network.updated_at = time.time()
            return belief

    # ── Belief Revision ──────────────────────────────────────────────

    def revise_belief(
        self,
        network_id: str,
        belief_id: str,
        evidence_id: str,
        reasoning: str = "",
    ) -> BeliefRevision | None:
        """Revise a belief's confidence using a simplified Bayesian update.

        The update rule:
            evidence_weight = (1 - strength_value / 4) * reliability
            supporting:     posterior = prior + evidence_weight * (1 - prior)
            contradicting:  posterior = prior - evidence_weight * prior

        Strength values: 0 = overwhelming, 4 = negligible. The resulting
        confidence is clamped to [0, 1], and a revision record is appended
        to the global log. The belief's status may transition to CONFIRMED,
        FALSIFIED, or RETRACTED depending on the posterior.

        Args:
            network_id: The network containing the belief.
            belief_id: The belief to revise.
            evidence_id: The evidence driving the revision.
            reasoning: Human-readable justification for the revision.

        Returns:
            The created BeliefRevision, or None if inputs are invalid.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return None
            belief = network.beliefs.get(belief_id)
            if belief is None:
                return None
            evidence = self._evidence.get(evidence_id)
            if evidence is None:
                return None

            prior = belief.confidence
            supports = self._evidence_supports_locked(belief, evidence)

            # Evidence weight: (1 - strength_value / 4) * reliability.
            strength_value = evidence.strength.value
            reliability = max(0.0, min(1.0, evidence.reliability))
            evidence_weight = (1.0 - (strength_value / 4.0)) * reliability

            if supports:
                posterior = prior + (evidence_weight * (1.0 - prior))
            else:
                posterior = prior - (evidence_weight * prior)
            posterior = max(0.0, min(1.0, posterior))

            old_confidence = belief.confidence
            belief.prior_confidence = old_confidence
            belief.confidence = posterior
            belief.revision_count += 1
            belief.updated_at = time.time()

            revision_type = self._determine_revision_type(old_confidence, posterior, supports)
            belief.last_revision_type = revision_type

            # Transition lifecycle status based on the revision outcome.
            if revision_type == RevisionType.CONFIRMATION:
                belief.status = BeliefStatus.CONFIRMED
            elif revision_type == RevisionType.FALSIFICATION:
                belief.status = BeliefStatus.FALSIFIED
            elif revision_type == RevisionType.RETRACTION:
                belief.status = BeliefStatus.RETRACTED
            elif belief.status in (BeliefStatus.TENTATIVE, BeliefStatus.SUSPENDED):
                # A meaningful revision promotes a tentative belief to active.
                if 0.05 < posterior < 0.95:
                    belief.status = BeliefStatus.ACTIVE

            # Ensure the evidence is linked to the belief.
            if evidence_id not in belief.evidence_ids:
                belief.evidence_ids.append(evidence_id)

            revision = BeliefRevision(
                belief_id=belief_id,
                revision_type=revision_type,
                old_confidence=old_confidence,
                new_confidence=posterior,
                evidence_id=evidence_id,
                reasoning=reasoning,
            )
            self._append_revision_locked(revision)

            network.total_revisions += 1
            network.updated_at = time.time()
            return revision

    def get_revisions(
        self,
        network_id: str,
        belief_id: str,
    ) -> list[BeliefRevision]:
        """Get the revision history for a belief, oldest first.

        Returns an empty list if the network or belief cannot be found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return []
            if belief_id not in network.beliefs:
                return []
            return [r for r in self._revisions if r.belief_id == belief_id]

    # ── Consistency Management ───────────────────────────────────────

    def check_consistency(self, network_id: str) -> ConsistencyCheck | None:
        """Check a network for internal consistency.

        Flags pairs of related beliefs whose confidence levels differ by more
        than the consistency gap threshold. The inconsistency score is the
        ratio of conflicting pairs to total related pairs in [0, 1].

        Returns:
            A ConsistencyCheck, or None if the network cannot be found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return None

            conflicting: list[tuple[str, str]] = []
            total_pairs = 0
            gap_sum = 0.0
            visited_pairs: set[tuple[str, str]] = set()

            for source_id, neighbors in network.adjacency.items():
                source = network.beliefs.get(source_id)
                if source is None:
                    continue
                for neighbor_id in neighbors:
                    pair = tuple(sorted((source_id, neighbor_id)))
                    if pair in visited_pairs:
                        continue
                    visited_pairs.add(pair)
                    neighbor = network.beliefs.get(neighbor_id)
                    if neighbor is None:
                        continue
                    total_pairs += 1
                    gap = abs(source.confidence - neighbor.confidence)
                    gap_sum += gap
                    if gap > self._CONSISTENCY_GAP_THRESHOLD:
                        conflicting.append((source_id, neighbor_id))

            if total_pairs > 0:
                # Score blends the conflict ratio with the average gap.
                conflict_ratio = len(conflicting) / total_pairs
                avg_gap = gap_sum / total_pairs
                inconsistency_score = max(conflict_ratio, avg_gap)
            else:
                inconsistency_score = 0.0

            check = ConsistencyCheck(
                network_id=network_id,
                conflicting_beliefs=conflicting,
                inconsistency_score=round(inconsistency_score, 4),
                resolved=False,
                resolution_notes="",
            )
            self._consistency_checks[check.check_id] = check
            return check

    def resolve_conflict(
        self,
        network_id: str,
        belief_id_a: str,
        belief_id_b: str,
        resolution: str,
        notes: str = "",
    ) -> ConsistencyCheck | None:
        """Resolve a conflict between two beliefs.

        The `resolution` string selects a strategy:
            - "keep_a": lower belief B's confidence toward A's.
            - "keep_b": lower belief A's confidence toward B's.
            - "merge": average both confidences.
            - "suspend": set both beliefs to SUSPENDED.
            - "retract_a" / "retract_b": retract one of the beliefs.

        A revision record is created for each adjusted belief, and a resolved
        ConsistencyCheck is returned.

        Returns:
            A resolved ConsistencyCheck, or None if inputs are invalid.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return None
            belief_a = network.beliefs.get(belief_id_a)
            belief_b = network.beliefs.get(belief_id_b)
            if belief_a is None or belief_b is None:
                return None

            now = time.time()
            resolution = (resolution or "").strip().lower()

            if resolution == "keep_a":
                self._apply_propagated_confidence_locked(
                    network, belief_b, belief_a.confidence, now,
                    reasoning=f"Conflict resolved keeping {belief_id_a}",
                )
            elif resolution == "keep_b":
                self._apply_propagated_confidence_locked(
                    network, belief_a, belief_b.confidence, now,
                    reasoning=f"Conflict resolved keeping {belief_id_b}",
                )
            elif resolution == "merge":
                merged = (belief_a.confidence + belief_b.confidence) / 2.0
                self._apply_propagated_confidence_locked(
                    network, belief_a, merged, now,
                    reasoning="Conflict resolved by merging",
                )
                self._apply_propagated_confidence_locked(
                    network, belief_b, merged, now,
                    reasoning="Conflict resolved by merging",
                )
            elif resolution == "suspend":
                belief_a.status = BeliefStatus.SUSPENDED
                belief_b.status = BeliefStatus.SUSPENDED
                belief_a.updated_at = now
                belief_b.updated_at = now
            elif resolution == "retract_a":
                self._retract_belief_locked(network, belief_a, now, notes)
            elif resolution == "retract_b":
                self._retract_belief_locked(network, belief_b, now, notes)
            else:
                # Unknown resolution: record notes only, no confidence change.
                pass

            network.updated_at = now

            check = ConsistencyCheck(
                network_id=network_id,
                conflicting_beliefs=[(belief_id_a, belief_id_b)],
                inconsistency_score=0.0,
                resolved=True,
                resolution_notes=notes or resolution,
            )
            self._consistency_checks[check.check_id] = check
            return check

    # ── Propagation & Chains ─────────────────────────────────────────

    def propagate_update(self, network_id: str, belief_id: str) -> list[str]:
        """Propagate a belief's confidence to its directly related beliefs.

        Each neighbor's confidence is moved a fraction
        (_PROPAGATION_FACTOR) of the way toward the source belief's
        confidence. A revision record is created for each updated neighbor.

        Returns:
            A list of belief IDs whose confidence changed. Returns an empty
            list if the network or belief cannot be found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return []
            source = network.beliefs.get(belief_id)
            if source is None:
                return []

            updated: list[str] = []
            now = time.time()

            related_ids = set(source.related_beliefs)
            related_ids.update(network.adjacency.get(belief_id, []))

            for rid in related_ids:
                if rid == belief_id:
                    continue
                related = network.beliefs.get(rid)
                if related is None:
                    continue
                if related.status in (BeliefStatus.RETRACTED, BeliefStatus.FALSIFIED):
                    continue

                old = related.confidence
                new = old + self._PROPAGATION_FACTOR * (source.confidence - old)
                new = max(0.0, min(1.0, new))
                if abs(new - old) < 1e-6:
                    continue

                related.prior_confidence = old
                related.confidence = new
                related.revision_count += 1
                related.updated_at = now
                related.last_revision_type = RevisionType.REVISION

                revision = BeliefRevision(
                    belief_id=rid,
                    revision_type=RevisionType.REVISION,
                    old_confidence=old,
                    new_confidence=new,
                    evidence_id=None,
                    reasoning=f"Propagated from belief {belief_id}",
                )
                self._append_revision_locked(revision)
                network.total_revisions += 1
                updated.append(rid)

            if updated:
                network.updated_at = now
            return updated

    def get_belief_chain(self, network_id: str, belief_id: str) -> list[Belief]:
        """Get the dependency chain for a belief.

        Performs a breadth-first traversal of the belief's `dependencies`
        graph and returns beliefs in dependency order (dependencies first,
        the queried belief last). Cycles are broken with a visited set.

        Returns:
            An ordered list of Belief objects. Empty if not found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return []
            if belief_id not in network.beliefs:
                return []

            visited: set[str] = set()
            order: list[str] = []
            queue: list[str] = [belief_id]

            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)
                current = network.beliefs.get(current_id)
                if current is None:
                    continue
                order.append(current_id)
                for dep_id in current.dependencies:
                    if dep_id not in visited:
                        queue.append(dep_id)

            # Reverse so that root dependencies come first.
            chain: list[Belief] = []
            for bid in reversed(order):
                belief = network.beliefs.get(bid)
                if belief is not None:
                    chain.append(belief)
            return chain

    # ── Query & Ranking ──────────────────────────────────────────────

    def query_beliefs(
        self,
        network_id: str,
        proposition_substring: str,
    ) -> list[Belief]:
        """Find beliefs whose proposition contains a substring (case-insensitive).

        Returns an empty list if the network cannot be found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return []
            needle = (proposition_substring or "").lower()
            if not needle:
                return []
            return [
                b for b in network.beliefs.values()
                if needle in b.proposition.lower() or needle in b.description.lower()
            ]

    def get_most_confident(
        self,
        network_id: str,
        category: BeliefCategory | None = None,
        limit: int = 10,
    ) -> list[Belief]:
        """Get the most confident beliefs in a network, descending."""
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return []
            beliefs = list(network.beliefs.values())
            if category is not None:
                beliefs = [b for b in beliefs if b.category == category]
            beliefs.sort(key=lambda b: b.confidence, reverse=True)
            return beliefs[:max(0, limit)]

    def get_least_confident(
        self,
        network_id: str,
        category: BeliefCategory | None = None,
        limit: int = 10,
    ) -> list[Belief]:
        """Get the least confident beliefs in a network, ascending."""
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return []
            beliefs = list(network.beliefs.values())
            if category is not None:
                beliefs = [b for b in beliefs if b.category == category]
            beliefs.sort(key=lambda b: b.confidence)
            return beliefs[:max(0, limit)]

    # ── Statistics ───────────────────────────────────────────────────

    def get_network_stats(self, network_id: str) -> dict[str, Any]:
        """Get statistics for a single belief network.

        Returns an empty dict if the network cannot be found.
        """
        with self._lock:
            network = self._networks.get(network_id)
            if network is None:
                return {}

            beliefs = list(network.beliefs.values())
            total = len(beliefs)
            by_status: dict[str, int] = {}
            by_category: dict[str, int] = {}
            confidence_sum = 0.0
            for belief in beliefs:
                by_status[belief.status.value] = by_status.get(belief.status.value, 0) + 1
                by_category[belief.category.value] = by_category.get(belief.category.value, 0) + 1
                confidence_sum += belief.confidence

            avg_confidence = (confidence_sum / total) if total > 0 else 0.0
            active = sum(
                1 for b in beliefs
                if b.status in (BeliefStatus.ACTIVE, BeliefStatus.CONFIRMED)
            )
            confirmed = sum(1 for b in beliefs if b.status == BeliefStatus.CONFIRMED)
            falsified = sum(1 for b in beliefs if b.status == BeliefStatus.FALSIFIED)

            linked_evidence = set()
            for belief in beliefs:
                linked_evidence.update(belief.evidence_ids)

            return {
                "network_id": network.network_id,
                "agent_id": network.agent_id,
                "total_beliefs": total,
                "active_beliefs": active,
                "confirmed_beliefs": confirmed,
                "falsified_beliefs": falsified,
                "beliefs_by_status": by_status,
                "beliefs_by_category": by_category,
                "avg_confidence": round(avg_confidence, 4),
                "total_revisions": network.total_revisions,
                "linked_evidence_count": len(linked_evidence),
                "adjacency_edges": sum(len(v) for v in network.adjacency.values()),
                "created_at": network.created_at,
                "updated_at": network.updated_at,
            }

    def get_stats(self) -> BeliefEngineStats:
        """Get aggregate statistics across all networks and evidence."""
        with self._lock:
            total_networks = len(self._networks)
            total_beliefs = 0
            by_status: dict[str, int] = {}
            by_category: dict[str, int] = {}
            confidence_sum = 0.0
            total_revisions = 0

            for network in self._networks.values():
                total_beliefs += len(network.beliefs)
                total_revisions += network.total_revisions
                for belief in network.beliefs.values():
                    by_status[belief.status.value] = by_status.get(belief.status.value, 0) + 1
                    by_category[belief.category.value] = by_category.get(belief.category.value, 0) + 1
                    confidence_sum += belief.confidence

            avg_confidence = (confidence_sum / total_beliefs) if total_beliefs > 0 else 0.0
            unresolved_issues = sum(
                1 for c in self._consistency_checks.values()
                if not c.resolved
            )

            return BeliefEngineStats(
                total_networks=total_networks,
                total_beliefs=total_beliefs,
                beliefs_by_status=by_status,
                beliefs_by_category=by_category,
                avg_confidence=round(avg_confidence, 4),
                total_revisions=total_revisions,
                total_evidence=len(self._evidence),
                consistency_issues=unresolved_issues,
            )

    # ── Reset ────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset the engine to its initial empty state."""
        with self._lock:
            self._networks.clear()
            self._evidence.clear()
            self._revisions.clear()
            self._consistency_checks.clear()
            self._agent_networks.clear()

    # ── Internal Helpers (no lock acquisition) ───────────────────────

    def _register_adjacency(
        self,
        network: BeliefNetwork,
        belief_id: str,
        related: list[str],
    ) -> None:
        """Register bidirectional adjacency edges for a belief (internal)."""
        neighbors = list(related)
        network.adjacency[belief_id] = neighbors
        for other_id in neighbors:
            other_list = network.adjacency.setdefault(other_id, [])
            if belief_id not in other_list:
                other_list.append(belief_id)

    def _evict_evidence_locked(self) -> None:
        """Evict oldest evidence when the store exceeds capacity (internal)."""
        if len(self._evidence) <= self.MAX_EVIDENCE:
            return
        # Sort by timestamp and drop the oldest entries.
        sorted_ids = sorted(
            self._evidence.keys(),
            key=lambda eid: self._evidence[eid].timestamp,
        )
        excess = len(self._evidence) - self.MAX_EVIDENCE
        for eid in sorted_ids[:excess]:
            self._evidence.pop(eid, None)

    def _append_revision_locked(self, revision: BeliefRevision) -> None:
        """Append a revision, trimming the log to the configured max (internal)."""
        self._revisions.append(revision)
        if len(self._revisions) > self.MAX_REVISIONS_LOG:
            # Keep only the most recent entries.
            self._revisions = self._revisions[-self.MAX_REVISIONS_LOG:]

    def _evidence_supports_locked(self, belief: Belief, evidence: Evidence) -> bool:
        """Determine whether evidence supports or contradicts a belief.

        Evidence is treated as contradicting if it explicitly lists, in its
        `contradicting` field, an evidence_id already linked to the belief, or
        if an already-linked evidence piece lists this evidence in its own
        `contradicting` field. Otherwise the evidence is treated as supporting.

        Must be called while holding the lock.
        """
        for ev_id in belief.evidence_ids:
            if ev_id == evidence.evidence_id:
                continue
            if ev_id in evidence.contradicting:
                return False
            existing = self._evidence.get(ev_id)
            if existing is not None and evidence.evidence_id in existing.contradicting:
                return False
        return True

    def _determine_revision_type(
        self,
        old: float,
        new: float,
        supports: bool,
    ) -> RevisionType:
        """Classify a revision based on the confidence delta (internal)."""
        if new >= self._CONFIRMATION_THRESHOLD:
            return RevisionType.CONFIRMATION
        if new <= self._FALSIFICATION_THRESHOLD:
            if supports:
                return RevisionType.RETRACTION
            return RevisionType.FALSIFICATION
        if new > old:
            return RevisionType.STRENGTHENING
        if new < old:
            return RevisionType.WEAKENING
        return RevisionType.REVISION

    def _apply_propagated_confidence_locked(
        self,
        network: BeliefNetwork,
        belief: Belief,
        target: float,
        now: float,
        reasoning: str,
    ) -> None:
        """Move a belief's confidence toward a target and log a revision (internal)."""
        old = belief.confidence
        new = max(0.0, min(1.0, float(target)))
        if abs(new - old) < 1e-6:
            belief.updated_at = now
            return
        belief.prior_confidence = old
        belief.confidence = new
        belief.revision_count += 1
        belief.updated_at = now
        belief.last_revision_type = RevisionType.REVISION
        revision = BeliefRevision(
            belief_id=belief.belief_id,
            revision_type=RevisionType.REVISION,
            old_confidence=old,
            new_confidence=new,
            evidence_id=None,
            reasoning=reasoning,
        )
        self._append_revision_locked(revision)
        network.total_revisions += 1

    def _retract_belief_locked(
        self,
        network: BeliefNetwork,
        belief: Belief,
        now: float,
        notes: str,
    ) -> None:
        """Retract a belief and log the retraction (internal)."""
        old = belief.confidence
        belief.prior_confidence = old
        belief.confidence = 0.0
        belief.status = BeliefStatus.RETRACTED
        belief.revision_count += 1
        belief.updated_at = now
        belief.last_revision_type = RevisionType.RETRACTION
        revision = BeliefRevision(
            belief_id=belief.belief_id,
            revision_type=RevisionType.RETRACTION,
            old_confidence=old,
            new_confidence=0.0,
            evidence_id=None,
            reasoning=notes or "Belief retracted during conflict resolution",
        )
        self._append_revision_locked(revision)
        network.total_revisions += 1


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_belief_engine: AgentBeliefEngine | None = None


def get_belief_engine() -> AgentBeliefEngine:
    """Get or create the singleton AgentBeliefEngine instance."""
    global _belief_engine
    if _belief_engine is None:
        _belief_engine = AgentBeliefEngine()
    return _belief_engine


def reset_belief_engine() -> None:
    """Reset the singleton AgentBeliefEngine instance."""
    global _belief_engine
    if _belief_engine:
        _belief_engine.reset()
    _belief_engine = None
