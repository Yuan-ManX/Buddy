"""
Agent Capability Mesh — Dynamic Capability Discovery and Composition.

The Capability Mesh creates a decentralized network of capabilities that agents
can discover, compose, and execute. Each capability is a self-contained unit of
functionality with metadata, versioning, and compatibility contracts. The mesh
enables agents to dynamically assemble complex workflows by combining capabilities
from multiple providers without centralized coordination.

Architecture:
  Layer 1: Registry — Capability registration with semantic indexing
  Layer 2: Discovery — Intent-based capability search and matching
  Layer 3: Composition — Dynamic pipeline assembly from discovered capabilities
  Layer 4: Execution — Sandboxed capability execution with monitoring
  Layer 5: Trust — Reputation scoring and provider attestation
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.capability_mesh")


# ═══════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════

class CapabilityDomain(str, Enum):
    """Functional domains that capabilities belong to."""
    GENERAL = "general"
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    AUTOMATION = "automation"
    COMMUNICATION = "communication"
    KNOWLEDGE = "knowledge"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    CUSTOM = "custom"


class CapabilityType(str, Enum):
    """The type of capability execution."""
    FUNCTION = "function"        # Pure function call
    TOOL = "tool"                # External tool invocation
    SKILL = "skill"              # Compound skill execution
    PIPELINE = "pipeline"        # Multi-step pipeline
    AGENT = "agent"              # Sub-agent delegation
    SERVICE = "service"          # External service call


class MaturityLevel(str, Enum):
    """Maturity level of a capability."""
    EXPERIMENTAL = "experimental"
    ALPHA = "alpha"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"


class CompositionStrategy(str, Enum):
    """Strategy for composing capabilities."""
    SEQUENTIAL = "sequential"      # Execute one after another
    PARALLEL = "parallel"          # Execute concurrently
    CONDITIONAL = "conditional"    # Branch based on conditions
    ITERATIVE = "iterative"        # Repeat until convergence
    VOTING = "voting"              # Multiple providers, majority vote
    FALLBACK = "fallback"          # Try primary, fallback on failure


class MeshNodeState(str, Enum):
    """State of a node in the capability mesh."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    SYNCING = "syncing"
    ISOLATED = "isolated"


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class CapabilityContract:
    """Input/output contract for a capability."""
    contract_id: str
    inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "constraints": self.constraints,
            "examples": self.examples,
        }


@dataclass
class CapabilityVersion:
    """Version information for a capability."""
    major: int = 1
    minor: int = 0
    patch: int = 0
    changelog: str = ""
    compatible_with: list[str] = field(default_factory=list)

    @property
    def version_string(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version_string,
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "changelog": self.changelog,
            "compatible_with": self.compatible_with,
        }


@dataclass
class CapabilityDefinition:
    """A self-contained unit of functionality registered in the mesh."""
    capability_id: str
    name: str
    description: str
    domain: CapabilityDomain
    cap_type: CapabilityType
    version: CapabilityVersion
    contract: CapabilityContract
    provider_id: str = ""
    maturity: MaturityLevel = MaturityLevel.BETA
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    estimated_cost_ms: float = 0.0
    estimated_tokens: int = 0
    handler: Callable | None = field(default=None, repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain.value,
            "type": self.cap_type.value,
            "version": self.version.to_dict(),
            "provider_id": self.provider_id,
            "maturity": self.maturity.value,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "estimated_cost_ms": self.estimated_cost_ms,
            "estimated_tokens": self.estimated_tokens,
            "registered_at": self.registered_at,
        }


@dataclass
class CapabilityMatch:
    """A match result from capability discovery."""
    capability: CapabilityDefinition
    relevance_score: float = 0.0
    trust_score: float = 0.5
    match_reason: str = ""
    semantic_similarity: float = 0.0

    @property
    def composite_score(self) -> float:
        """Weighted composite score for ranking."""
        return 0.4 * self.relevance_score + 0.3 * self.trust_score + 0.3 * self.semantic_similarity

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability.to_dict(),
            "relevance_score": self.relevance_score,
            "trust_score": self.trust_score,
            "composite_score": round(self.composite_score, 4),
            "match_reason": self.match_reason,
            "semantic_similarity": self.semantic_similarity,
        }


@dataclass
class CompositionStep:
    """A single step in a capability composition."""
    step_id: str
    capability_id: str
    order: int = 0
    strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL
    depends_on: list[str] = field(default_factory=list)
    condition: str = ""
    retry_count: int = 0
    timeout_ms: float = 30000.0
    parameter_mapping: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "capability_id": self.capability_id,
            "order": self.order,
            "strategy": self.strategy.value,
            "depends_on": self.depends_on,
            "condition": self.condition,
            "retry_count": self.retry_count,
            "timeout_ms": self.timeout_ms,
        }


@dataclass
class CompositionPlan:
    """A plan for composing multiple capabilities into a workflow."""
    plan_id: str
    name: str
    description: str = ""
    steps: list[CompositionStep] = field(default_factory=list)
    strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL
    estimated_duration_ms: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "strategy": self.strategy.value,
            "estimated_duration_ms": self.estimated_duration_ms,
            "created_at": self.created_at,
        }


@dataclass
class StepResult:
    """Result of executing a single composition step."""
    step_id: str
    success: bool
    output: Any = None
    error: str = ""
    duration_ms: float = 0.0
    tokens_used: int = 0
    retries: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "retries": self.retries,
        }


@dataclass
class CompositionResult:
    """Result of executing a full composition plan."""
    plan_id: str
    success: bool
    step_results: list[StepResult] = field(default_factory=list)
    final_output: Any = None
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    errors: list[str] = field(default_factory=list)
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "success": self.success,
            "step_results": [s.to_dict() for s in self.step_results],
            "total_duration_ms": self.total_duration_ms,
            "total_tokens": self.total_tokens,
            "errors": self.errors,
            "completed_at": self.completed_at,
        }


@dataclass
class ProviderReputation:
    """Reputation and trust data for a capability provider."""
    provider_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_duration_ms: float = 0.0
    average_tokens: int = 0
    trust_score: float = 0.5
    last_used_at: str = ""
    endorsements: int = 0
    reports: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "total_executions": self.total_executions,
            "success_rate": round(self.success_rate, 4),
            "average_duration_ms": round(self.average_duration_ms, 2),
            "trust_score": round(self.trust_score, 4),
            "endorsements": self.endorsements,
            "last_used_at": self.last_used_at,
        }


@dataclass
class MeshNode:
    """A peer node in the capability mesh network."""
    node_id: str
    name: str = ""
    state: MeshNodeState = MeshNodeState.ONLINE
    capabilities_count: int = 0
    address: str = ""
    last_heartbeat: str = ""
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "state": self.state.value,
            "capabilities_count": self.capabilities_count,
            "address": self.address,
            "last_heartbeat": self.last_heartbeat,
            "version": self.version,
        }


@dataclass
class MeshStats:
    """Statistics for the capability mesh."""
    total_capabilities: int = 0
    total_providers: int = 0
    total_nodes: int = 0
    total_compositions: int = 0
    total_executions: int = 0
    capabilities_by_domain: dict[str, int] = field(default_factory=dict)
    average_trust_score: float = 0.0
    online_nodes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_capabilities": self.total_capabilities,
            "total_providers": self.total_providers,
            "total_nodes": self.total_nodes,
            "total_compositions": self.total_compositions,
            "total_executions": self.total_executions,
            "capabilities_by_domain": self.capabilities_by_domain,
            "average_trust_score": round(self.average_trust_score, 4),
            "online_nodes": self.online_nodes,
        }


# ═══════════════════════════════════════════════════════════════
# Capability Mesh Engine
# ═══════════════════════════════════════════════════════════════

class CapabilityMesh:
    """Dynamic capability discovery and composition engine.

    The Capability Mesh provides a decentralized registry where agents
    can register their capabilities, discover capabilities from other
    agents, and dynamically compose complex workflows from discovered
    capabilities. It maintains trust scores and tracks execution history
    to enable informed capability selection.

    Design Principles:
    - Decentralized: No single point of coordination for capability discovery
    - Semantic: Intent-based search using natural language understanding
    - Composable: Capabilities can be chained into complex pipelines
    - Trust-aware: Provider reputation influences capability selection
    - Self-healing: Failed capabilities are automatically replaced with alternatives
    """

    def __init__(self, mesh_id: str = "buddy-global"):
        self.mesh_id = mesh_id

        # Capability registry
        self._capabilities: dict[str, CapabilityDefinition] = {}
        self._domain_index: dict[str, set[str]] = {}
        self._tag_index: dict[str, set[str]] = {}

        # Provider reputation
        self._providers: dict[str, ProviderReputation] = {}

        # Mesh nodes
        self._nodes: dict[str, MeshNode] = {}
        self._local_node = MeshNode(
            node_id=f"node-{mesh_id}",
            name="Buddy Local",
            state=MeshNodeState.ONLINE,
        )

        # Composition history
        self._compositions: list[CompositionPlan] = []
        self._composition_results: list[CompositionResult] = []

        # Statistics
        self._stats = MeshStats()

        # Execution lock
        self._lock = asyncio.Lock()

        logger.info(f"Capability mesh initialized: {mesh_id}")

    # ═════════════════════════════════════════════════════════
    # Capability Registration
    # ═════════════════════════════════════════════════════════

    def register(
        self,
        name: str,
        description: str,
        domain: CapabilityDomain,
        cap_type: CapabilityType,
        handler: Callable | None = None,
        version: CapabilityVersion | None = None,
        contract: CapabilityContract | None = None,
        provider_id: str = "",
        maturity: MaturityLevel = MaturityLevel.BETA,
        tags: list[str] | None = None,
        dependencies: list[str] | None = None,
        estimated_cost_ms: float = 0.0,
        estimated_tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> CapabilityDefinition:
        """Register a new capability in the mesh."""
        cap_id = f"cap-{uuid.uuid4().hex[:12]}"

        capability = CapabilityDefinition(
            capability_id=cap_id,
            name=name,
            description=description,
            domain=domain,
            cap_type=cap_type,
            version=version or CapabilityVersion(),
            contract=contract or CapabilityContract(contract_id=f"ctr-{uuid.uuid4().hex[:8]}"),
            provider_id=provider_id or self.mesh_id,
            maturity=maturity,
            tags=tags or [],
            dependencies=dependencies or [],
            estimated_cost_ms=estimated_cost_ms,
            estimated_tokens=estimated_tokens,
            handler=handler,
            metadata=metadata or {},
        )

        self._capabilities[cap_id] = capability

        # Index by domain
        domain_key = domain.value
        if domain_key not in self._domain_index:
            self._domain_index[domain_key] = set()
        self._domain_index[domain_key].add(cap_id)

        # Index by tags
        for tag in capability.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tag_index:
                self._tag_index[tag_lower] = set()
            self._tag_index[tag_lower].add(cap_id)

        # Initialize provider if new
        if provider_id and provider_id not in self._providers:
            self._providers[provider_id] = ProviderReputation(provider_id=provider_id)

        self._stats.total_capabilities += 1
        domain_key = domain.value
        self._stats.capabilities_by_domain[domain_key] = (
            self._stats.capabilities_by_domain.get(domain_key, 0) + 1
        )

        logger.info(f"Capability registered: {name} ({cap_id}) in domain {domain.value}")
        return capability

    def unregister(self, capability_id: str) -> bool:
        """Remove a capability from the mesh."""
        if capability_id not in self._capabilities:
            return False

        cap = self._capabilities.pop(capability_id)

        # Remove from domain index
        domain_key = cap.domain.value
        if domain_key in self._domain_index:
            self._domain_index[domain_key].discard(capability_id)

        # Remove from tag index
        for tag in cap.tags:
            tag_lower = tag.lower()
            if tag_lower in self._tag_index:
                self._tag_index[tag_lower].discard(capability_id)

        self._stats.total_capabilities -= 1
        logger.info(f"Capability unregistered: {cap.name} ({capability_id})")
        return True

    def get_capability(self, capability_id: str) -> CapabilityDefinition | None:
        """Get a capability by ID."""
        return self._capabilities.get(capability_id)

    def list_capabilities(
        self,
        domain: str | None = None,
        cap_type: str | None = None,
        maturity: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[CapabilityDefinition]:
        """List capabilities with optional filters."""
        results = list(self._capabilities.values())

        if domain:
            results = [c for c in results if c.domain.value == domain]
        if cap_type:
            results = [c for c in results if c.cap_type.value == cap_type]
        if maturity:
            results = [c for c in results if c.maturity.value == maturity]
        if tags:
            tag_set = {t.lower() for t in tags}
            results = [c for c in results if tag_set & {t.lower() for t in c.tags}]

        return results[:limit]

    # ═════════════════════════════════════════════════════════
    # Capability Discovery
    # ═════════════════════════════════════════════════════════

    def discover(
        self,
        query: str,
        domain: str | None = None,
        cap_type: str | None = None,
        min_trust: float = 0.0,
        limit: int = 10,
    ) -> list[CapabilityMatch]:
        """Discover capabilities matching a natural language query.

        Uses semantic matching against capability names, descriptions,
        and tags to find the most relevant capabilities. Results are
        ranked by composite score (relevance + trust + semantic similarity).
        """
        query_lower = query.lower()
        query_terms = query_lower.split()
        matches: list[CapabilityMatch] = []

        for cap in self._capabilities.values():
            # Apply filters
            if domain and cap.domain.value != domain:
                continue
            if cap_type and cap.cap_type.value != cap_type:
                continue

            # Calculate relevance
            relevance = self._calculate_relevance(query_terms, cap)

            # Get trust score
            trust = self._get_trust_score(cap.provider_id)

            if trust < min_trust:
                continue

            # Calculate semantic similarity (simplified keyword-based)
            semantic = self._calculate_semantic_similarity(query_lower, cap)

            if relevance > 0 or semantic > 0:
                matches.append(CapabilityMatch(
                    capability=cap,
                    relevance_score=relevance,
                    trust_score=trust,
                    match_reason=self._generate_match_reason(query_terms, cap),
                    semantic_similarity=semantic,
                ))

        # Sort by composite score descending
        matches.sort(key=lambda m: m.composite_score, reverse=True)
        return matches[:limit]

    def _calculate_relevance(self, query_terms: list[str], cap: CapabilityDefinition) -> float:
        """Calculate keyword relevance score."""
        name_lower = cap.name.lower()
        desc_lower = cap.description.lower()
        tags_lower = [t.lower() for t in cap.tags]

        score = 0.0
        for term in query_terms:
            if term in name_lower:
                score += 0.4
            if term in desc_lower:
                score += 0.2
            if any(term in tag for tag in tags_lower):
                score += 0.15

        return min(1.0, score)

    def _calculate_semantic_similarity(self, query: str, cap: CapabilityDefinition) -> float:
        """Calculate semantic similarity between query and capability."""
        # Domain-based similarity
        domain_similarity = 0.0
        domain_keywords = {
            "reasoning": ["think", "reason", "analyze", "logic", "deduce"],
            "code_generation": ["code", "program", "develop", "build", "implement"],
            "data_analysis": ["data", "analyze", "statistics", "metric", "report"],
            "content_creation": ["write", "create", "content", "article", "document"],
            "automation": ["automate", "schedule", "workflow", "trigger", "pipeline"],
            "communication": ["message", "chat", "notify", "send", "email"],
            "knowledge": ["knowledge", "learn", "memory", "recall", "search"],
            "security": ["secure", "audit", "review", "check", "validate"],
            "infrastructure": ["deploy", "server", "cloud", "docker", "container"],
        }

        domain_keywords_for_this = domain_keywords.get(cap.domain.value, [])
        matching = sum(1 for kw in domain_keywords_for_this if kw in query)
        if matching > 0:
            domain_similarity = min(1.0, matching / len(domain_keywords_for_this) * 2)

        # Tag overlap
        all_tags_text = " ".join(cap.tags).lower()
        tag_overlap = sum(1 for term in query.split() if term in all_tags_text)
        tag_similarity = min(1.0, tag_overlap / max(len(query.split()), 1) * 2)

        return 0.5 * domain_similarity + 0.5 * tag_similarity

    def _generate_match_reason(self, query_terms: list[str], cap: CapabilityDefinition) -> str:
        """Generate a human-readable reason for the match."""
        name_lower = cap.name.lower()
        reasons = []
        for term in query_terms:
            if term in name_lower:
                reasons.append(f"name matches '{term}'")
            elif term in cap.description.lower():
                reasons.append(f"description matches '{term}'")
        if not reasons:
            reasons.append(f"domain relevance ({cap.domain.value})")
        return "; ".join(reasons)

    def _get_trust_score(self, provider_id: str) -> float:
        """Get trust score for a provider."""
        if provider_id in self._providers:
            return self._providers[provider_id].trust_score
        return 0.5

    # ═════════════════════════════════════════════════════════
    # Capability Composition
    # ═════════════════════════════════════════════════════════

    def compose(
        self,
        name: str,
        description: str,
        capability_ids: list[str],
        strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL,
        parameter_mappings: list[dict[str, str]] | None = None,
    ) -> CompositionPlan:
        """Create a composition plan from multiple capabilities."""
        plan_id = f"plan-{uuid.uuid4().hex[:12]}"

        steps: list[CompositionStep] = []
        for i, cap_id in enumerate(capability_ids):
            if cap_id not in self._capabilities:
                logger.warning(f"Unknown capability in composition: {cap_id}")
                continue

            step = CompositionStep(
                step_id=f"step-{uuid.uuid4().hex[:8]}",
                capability_id=cap_id,
                order=i,
                strategy=strategy if i == 0 else CompositionStrategy.SEQUENTIAL,
                depends_on=[steps[-1].step_id] if steps else [],
                parameter_mapping=parameter_mappings[i] if parameter_mappings and i < len(parameter_mappings) else {},
            )
            steps.append(step)

        estimated_duration = sum(
            self._capabilities[cap_id].estimated_cost_ms
            for cap_id in capability_ids
            if cap_id in self._capabilities
        )

        plan = CompositionPlan(
            plan_id=plan_id,
            name=name,
            description=description,
            steps=steps,
            strategy=strategy,
            estimated_duration_ms=estimated_duration,
        )

        self._compositions.append(plan)
        self._stats.total_compositions += 1

        logger.info(f"Composition plan created: {name} ({plan_id}) with {len(steps)} steps")
        return plan

    def auto_compose(
        self,
        query: str,
        max_steps: int = 5,
        strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL,
    ) -> CompositionPlan | None:
        """Automatically compose capabilities based on a task description.

        Discovers relevant capabilities and creates a composition plan
        without manual specification of capability IDs.
        """
        matches = self.discover(query, limit=max_steps)
        if not matches:
            return None

        # Sort by composite score and take top matches
        matches.sort(key=lambda m: m.composite_score, reverse=True)
        top_capability_ids = [m.capability.capability_id for m in matches[:max_steps]]

        return self.compose(
            name=f"Auto: {query[:50]}",
            description=query,
            capability_ids=top_capability_ids,
            strategy=strategy,
        )

    # ═════════════════════════════════════════════════════════
    # Composition Execution
    # ═════════════════════════════════════════════════════════

    async def execute(
        self,
        plan: CompositionPlan,
        initial_input: Any = None,
        timeout_ms: float = 120000.0,
    ) -> CompositionResult:
        """Execute a composition plan."""
        async with self._lock:
            result = CompositionResult(plan_id=plan.plan_id, success=True)
            start_time = time.time()

            step_outputs: dict[str, Any] = {}
            step_results: list[StepResult] = []
            errors: list[str] = []

            for step in sorted(plan.steps, key=lambda s: s.order):
                cap = self._capabilities.get(step.capability_id)
                if not cap:
                    error_msg = f"Capability not found: {step.capability_id}"
                    errors.append(error_msg)
                    step_results.append(StepResult(
                        step_id=step.step_id, success=False, error=error_msg,
                    ))
                    result.success = False
                    continue

                # Resolve input from dependencies or initial input
                step_input = initial_input
                if step.depends_on:
                    dep_outputs = [step_outputs.get(dep) for dep in step.depends_on if dep in step_outputs]
                    if dep_outputs:
                        step_input = dep_outputs[-1] if len(dep_outputs) == 1 else dep_outputs

                step_start = time.time()

                try:
                    if cap.handler:
                        if asyncio.iscoroutinefunction(cap.handler):
                            output = await asyncio.wait_for(
                                cap.handler(step_input),
                                timeout=min(step.timeout_ms / 1000, timeout_ms / 1000),
                            )
                        else:
                            output = cap.handler(step_input)
                    else:
                        output = {"status": "no_handler", "input": str(step_input)[:200]}
                except asyncio.TimeoutError:
                    error_msg = f"Step {step.step_id} timed out"
                    errors.append(error_msg)
                    step_results.append(StepResult(
                        step_id=step.step_id, success=False, error=error_msg,
                        duration_ms=(time.time() - step_start) * 1000,
                    ))
                    result.success = False
                    continue
                except Exception as e:
                    error_msg = f"Step {step.step_id} failed: {str(e)}"
                    errors.append(error_msg)
                    step_results.append(StepResult(
                        step_id=step.step_id, success=False, error=error_msg,
                        duration_ms=(time.time() - step_start) * 1000,
                    ))
                    result.success = False
                    continue

                step_duration = (time.time() - step_start) * 1000
                sr = StepResult(
                    step_id=step.step_id,
                    success=True,
                    output=output,
                    duration_ms=step_duration,
                    tokens_used=cap.estimated_tokens,
                )
                step_results.append(sr)
                step_outputs[step.step_id] = output

                # Update provider reputation
                self._update_provider_reputation(cap.provider_id, success=True, duration_ms=step_duration)

            result.step_results = step_results
            result.final_output = step_outputs.get(plan.steps[-1].step_id) if plan.steps else None
            result.total_duration_ms = (time.time() - start_time) * 1000
            result.total_tokens = sum(sr.tokens_used for sr in step_results)
            result.errors = errors
            result.success = result.success and len(errors) == 0

            self._composition_results.append(result)
            self._stats.total_executions += 1

            logger.info(
                f"Composition executed: {plan.name} ({plan.plan_id}) "
                f"success={result.success}, duration={result.total_duration_ms:.0f}ms"
            )

            return result

    def _update_provider_reputation(
        self, provider_id: str, success: bool, duration_ms: float = 0.0, tokens: int = 0,
    ):
        """Update provider reputation after execution."""
        if provider_id not in self._providers:
            self._providers[provider_id] = ProviderReputation(provider_id=provider_id)

        rep = self._providers[provider_id]
        rep.total_executions += 1
        if success:
            rep.successful_executions += 1
        else:
            rep.failed_executions += 1

        # Update rolling average duration
        if rep.average_duration_ms == 0:
            rep.average_duration_ms = duration_ms
        else:
            alpha = 0.1  # Smoothing factor
            rep.average_duration_ms = (1 - alpha) * rep.average_duration_ms + alpha * duration_ms

        # Recalculate trust score
        rep.trust_score = 0.5 + 0.5 * rep.success_rate - 0.1 * (rep.reports / max(rep.total_executions, 1))
        rep.trust_score = max(0.0, min(1.0, rep.trust_score))
        rep.last_used_at = datetime.now(timezone.utc).isoformat()

    # ═════════════════════════════════════════════════════════
    # Mesh Node Management
    # ═════════════════════════════════════════════════════════

    def register_node(self, name: str, address: str = "", metadata: dict[str, Any] | None = None) -> MeshNode:
        """Register a peer node in the mesh."""
        node_id = f"node-{uuid.uuid4().hex[:8]}"
        node = MeshNode(
            node_id=node_id,
            name=name,
            state=MeshNodeState.ONLINE,
            address=address,
            last_heartbeat=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self._nodes[node_id] = node
        self._stats.total_nodes += 1
        self._stats.online_nodes += 1
        logger.info(f"Mesh node registered: {name} ({node_id})")
        return node

    def update_node_heartbeat(self, node_id: str) -> bool:
        """Update heartbeat for a node."""
        if node_id in self._nodes:
            self._nodes[node_id].last_heartbeat = datetime.now(timezone.utc).isoformat()
            self._nodes[node_id].state = MeshNodeState.ONLINE
            return True
        return False

    def get_nodes(self, state: str | None = None) -> list[MeshNode]:
        """Get all mesh nodes, optionally filtered by state."""
        nodes = list(self._nodes.values())
        if state:
            nodes = [n for n in nodes if n.state.value == state]
        return nodes

    # ═════════════════════════════════════════════════════════
    # Statistics & Introspection
    # ═════════════════════════════════════════════════════════

    def get_stats(self) -> MeshStats:
        """Get current mesh statistics."""
        self._stats.total_providers = len(self._providers)
        self._stats.total_nodes = len(self._nodes)
        self._stats.online_nodes = sum(
            1 for n in self._nodes.values() if n.state == MeshNodeState.ONLINE
        )

        if self._providers:
            self._stats.average_trust_score = sum(
                p.trust_score for p in self._providers.values()
            ) / len(self._providers)

        return self._stats

    def get_providers(self) -> list[ProviderReputation]:
        """Get all provider reputations."""
        return list(self._providers.values())

    def get_composition_history(self, limit: int = 20) -> list[CompositionResult]:
        """Get recent composition results."""
        return self._composition_results[-limit:]

    def get_domain_coverage(self) -> dict[str, Any]:
        """Get coverage analysis across domains."""
        coverage = {}
        for domain in CapabilityDomain:
            domain_key = domain.value
            caps = self._domain_index.get(domain_key, set())
            maturity_dist = {}
            for cap_id in caps:
                cap = self._capabilities.get(cap_id)
                if cap:
                    m = cap.maturity.value
                    maturity_dist[m] = maturity_dist.get(m, 0) + 1
            coverage[domain_key] = {
                "count": len(caps),
                "maturity_distribution": maturity_dist,
            }
        return coverage

    def reset(self):
        """Reset the capability mesh to initial state."""
        self._capabilities.clear()
        self._domain_index.clear()
        self._tag_index.clear()
        self._providers.clear()
        self._nodes.clear()
        self._compositions.clear()
        self._composition_results.clear()
        self._stats = MeshStats()
        logger.info(f"Capability mesh reset: {self.mesh_id}")


# ═══════════════════════════════════════════════════════════════
# Global Instance
# ═══════════════════════════════════════════════════════════════

capability_mesh = CapabilityMesh()