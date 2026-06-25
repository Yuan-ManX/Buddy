"""Buddy Team Architect — AI-Native Agent Team Composition Engine

The Team Architect automatically generates optimized agent team configurations
from domain descriptions, selecting from six team architecture patterns to
create the most effective collaboration structure for any task domain.

Team Architecture Patterns:
- Pipeline: Sequential processing with stage gates
- Fan-out/Fan-in: Parallel execution with result aggregation
- Expert Pool: Specialized agents with intelligent routing
- Producer-Reviewer: Creation with quality assurance cycle
- Supervisor: Hierarchical oversight and coordination
- Hierarchical Delegation: Tree-based task decomposition

Core capabilities:
- Domain analysis and pattern matching
- Agent role generation with skill mapping
- Inter-agent communication protocol design
- Team evolution through delta feedback
- Progressive disclosure for context efficiency
- Dry-run validation and testing
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.team_architect")


# ── Core Enums ──────────────────────────────────────────────────────

class TeamPattern(str, Enum):
    """Six fundamental team architecture patterns."""
    PIPELINE = "pipeline"
    FAN_OUT_FAN_IN = "fan_out_fan_in"
    EXPERT_POOL = "expert_pool"
    PRODUCER_REVIEWER = "producer_reviewer"
    SUPERVISOR = "supervisor"
    HIERARCHICAL = "hierarchical"


class AgentRole(str, Enum):
    """Standard agent roles within team architectures."""
    COORDINATOR = "coordinator"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    ANALYST = "analyst"
    CREATOR = "creator"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    GATEKEEPER = "gatekeeper"
    SPECIALIST = "specialist"
    OBSERVER = "observer"


class CommunicationProtocol(str, Enum):
    """Inter-agent communication protocols."""
    DIRECT = "direct"
    BROADCAST = "broadcast"
    ROUND_ROBIN = "round_robin"
    PUBLISH_SUBSCRIBE = "publish_subscribe"
    REQUEST_RESPONSE = "request_response"
    EVENT_DRIVEN = "event_driven"


class ValidationLevel(str, Enum):
    """Validation rigor levels."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    COMPREHENSIVE = "comprehensive"


# ── Data Classes ────────────────────────────────────────────────────

@dataclass
class AgentDefinition:
    """Definition of a single agent within a team architecture."""
    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    model_preference: str = "auto"
    max_tokens: int = 4096
    temperature: float = 0.7
    context_window: int = 128000
    priority: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamConfiguration:
    """Complete team architecture configuration."""
    team_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    pattern: TeamPattern = TeamPattern.EXPERT_POOL
    domain: str = ""
    description: str = ""
    agents: list[AgentDefinition] = field(default_factory=list)
    communication_protocol: CommunicationProtocol = CommunicationProtocol.DIRECT
    coordination_rules: list[str] = field(default_factory=list)
    error_handling: str = "retry_once"
    max_parallel_agents: int = 4
    timeout_seconds: float = 300.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamEvolutionDelta:
    """Delta feedback from real team execution for evolution."""
    delta_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    team_id: str = ""
    original_pattern: TeamPattern = TeamPattern.EXPERT_POOL
    evolved_pattern: TeamPattern = TeamPattern.EXPERT_POOL
    changes: list[str] = field(default_factory=list)
    success_metrics: dict[str, float] = field(default_factory=dict)
    lessons_learned: list[str] = field(default_factory=list)
    agent_adjustments: dict[str, dict[str, Any]] = field(default_factory=dict)
    captured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TeamValidationResult:
    """Result of team architecture validation."""
    valid: bool = True
    pattern: TeamPattern = TeamPattern.EXPERT_POOL
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    coverage_score: float = 0.0
    efficiency_score: float = 0.0
    robustness_score: float = 0.0


# ── Pattern Templates ───────────────────────────────────────────────

PATTERN_TEMPLATES: dict[TeamPattern, dict[str, Any]] = {
    TeamPattern.PIPELINE: {
        "description": "Sequential processing with stage gates between phases",
        "best_for": [
            "multi-stage workflows",
            "data processing pipelines",
            "document generation chains",
            "approval workflows",
        ],
        "roles": [AgentRole.ANALYST, AgentRole.EXECUTOR, AgentRole.REVIEWER, AgentRole.GATEKEEPER],
        "protocol": CommunicationProtocol.DIRECT,
        "flow": "linear",
        "parallelism": 1,
    },
    TeamPattern.FAN_OUT_FAN_IN: {
        "description": "Parallel execution with centralized result aggregation",
        "best_for": [
            "parallel research tasks",
            "multi-perspective analysis",
            "distributed computation",
            "batch processing",
        ],
        "roles": [AgentRole.COORDINATOR, AgentRole.EXECUTOR, AgentRole.SYNTHESIZER],
        "protocol": CommunicationProtocol.BROADCAST,
        "flow": "fan_out",
        "parallelism": 8,
    },
    TeamPattern.EXPERT_POOL: {
        "description": "Specialized agents with intelligent task routing",
        "best_for": [
            "multi-domain projects",
            "complex problem-solving",
            "consulting-style work",
            "knowledge-intensive tasks",
        ],
        "roles": [AgentRole.COORDINATOR, AgentRole.SPECIALIST, AgentRole.ANALYST],
        "protocol": CommunicationProtocol.REQUEST_RESPONSE,
        "flow": "pooled",
        "parallelism": 4,
    },
    TeamPattern.PRODUCER_REVIEWER: {
        "description": "Creation agents paired with quality assurance reviewers",
        "best_for": [
            "content creation",
            "code generation",
            "design work",
            "quality-critical outputs",
        ],
        "roles": [AgentRole.CREATOR, AgentRole.REVIEWER, AgentRole.CRITIC],
        "protocol": CommunicationProtocol.DIRECT,
        "flow": "paired",
        "parallelism": 2,
    },
    TeamPattern.SUPERVISOR: {
        "description": "Hierarchical oversight with supervisor coordination",
        "best_for": [
            "complex multi-agent coordination",
            "mission-critical operations",
            "regulated environments",
            "large-scale deployments",
        ],
        "roles": [AgentRole.COORDINATOR, AgentRole.EXECUTOR, AgentRole.OBSERVER, AgentRole.REVIEWER],
        "protocol": CommunicationProtocol.ROUND_ROBIN,
        "flow": "supervised",
        "parallelism": 6,
    },
    TeamPattern.HIERARCHICAL: {
        "description": "Tree-based task decomposition with delegation chains",
        "best_for": [
            "large-scale project management",
            "organizational workflows",
            "complex system design",
            "enterprise deployments",
        ],
        "roles": [AgentRole.COORDINATOR, AgentRole.EXECUTOR, AgentRole.SPECIALIST, AgentRole.SYNTHESIZER],
        "protocol": CommunicationProtocol.EVENT_DRIVEN,
        "flow": "tree",
        "parallelism": 10,
    },
}


# ── Domain Analysis ─────────────────────────────────────────────────

DOMAIN_PATTERN_MAP: dict[str, list[tuple[TeamPattern, float]]] = {
    "software_development": [
        (TeamPattern.PRODUCER_REVIEWER, 0.95),
        (TeamPattern.PIPELINE, 0.85),
        (TeamPattern.EXPERT_POOL, 0.75),
    ],
    "data_science": [
        (TeamPattern.PIPELINE, 0.95),
        (TeamPattern.FAN_OUT_FAN_IN, 0.85),
        (TeamPattern.EXPERT_POOL, 0.70),
    ],
    "content_creation": [
        (TeamPattern.PRODUCER_REVIEWER, 0.95),
        (TeamPattern.PIPELINE, 0.80),
        (TeamPattern.FAN_OUT_FAN_IN, 0.65),
    ],
    "research": [
        (TeamPattern.FAN_OUT_FAN_IN, 0.95),
        (TeamPattern.EXPERT_POOL, 0.85),
        (TeamPattern.SUPERVISOR, 0.70),
    ],
    "enterprise": [
        (TeamPattern.HIERARCHICAL, 0.95),
        (TeamPattern.SUPERVISOR, 0.90),
        (TeamPattern.EXPERT_POOL, 0.70),
    ],
    "devops": [
        (TeamPattern.PIPELINE, 0.90),
        (TeamPattern.SUPERVISOR, 0.80),
        (TeamPattern.FAN_OUT_FAN_IN, 0.70),
    ],
    "design": [
        (TeamPattern.PRODUCER_REVIEWER, 0.90),
        (TeamPattern.FAN_OUT_FAN_IN, 0.75),
        (TeamPattern.EXPERT_POOL, 0.65),
    ],
    "education": [
        (TeamPattern.EXPERT_POOL, 0.85),
        (TeamPattern.PIPELINE, 0.75),
        (TeamPattern.SUPERVISOR, 0.65),
    ],
}


# ── Team Architect Engine ───────────────────────────────────────────

class TeamArchitect:
    """Generates optimized agent team architectures from domain descriptions.

    Analyzes domain requirements, selects the best team pattern from six
    architectural options, generates agent definitions with skill mappings,
    and supports continuous evolution through delta feedback.
    """

    def __init__(self):
        self._team_registry: dict[str, TeamConfiguration] = {}
        self._evolution_history: list[TeamEvolutionDelta] = []
        self._validation_results: list[TeamValidationResult] = []
        self._total_teams_generated: int = 0
        self._pattern_usage: dict[str, int] = {p.value: 0 for p in TeamPattern}

    # ── Domain Analysis ────────────────────────────────────────

    def analyze_domain(self, domain_description: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Analyze a domain description to determine the best team pattern."""
        ctx = context or {}
        domain_lower = domain_description.lower()

        scored_patterns: list[tuple[TeamPattern, float]] = []

        for domain_key, patterns in DOMAIN_PATTERN_MAP.items():
            if domain_key in domain_lower:
                scored_patterns.extend(patterns)
                break

        if not scored_patterns:
            keywords = {
                "pipeline": TeamPattern.PIPELINE,
                "parallel": TeamPattern.FAN_OUT_FAN_IN,
                "review": TeamPattern.PRODUCER_REVIEWER,
                "quality": TeamPattern.PRODUCER_REVIEWER,
                "supervise": TeamPattern.SUPERVISOR,
                "manage": TeamPattern.SUPERVISOR,
                "hierarch": TeamPattern.HIERARCHICAL,
                "delegate": TeamPattern.HIERARCHICAL,
                "specialist": TeamPattern.EXPERT_POOL,
                "expert": TeamPattern.EXPERT_POOL,
            }
            for keyword, pattern in keywords.items():
                if keyword in domain_lower:
                    scored_patterns.append((pattern, 0.8))

        if not scored_patterns:
            scored_patterns = [(TeamPattern.EXPERT_POOL, 0.6)]

        scored_patterns.sort(key=lambda x: x[1], reverse=True)
        top_pattern = scored_patterns[0][0]

        complexity = ctx.get("complexity", "medium")
        scale = ctx.get("scale", "small")
        if complexity == "high" and scale == "large":
            top_pattern = TeamPattern.HIERARCHICAL
        elif complexity == "high":
            top_pattern = TeamPattern.SUPERVISOR

        template = PATTERN_TEMPLATES.get(top_pattern, PATTERN_TEMPLATES[TeamPattern.EXPERT_POOL])

        return {
            "recommended_pattern": top_pattern.value,
            "confidence": scored_patterns[0][1],
            "alternatives": [(p.value, s) for p, s in scored_patterns[1:4]],
            "template": template,
            "domain_keywords": [kw for kw in keywords if kw in domain_lower],
        }

    # ── Team Generation ─────────────────────────────────────────

    def generate_team(
        self,
        domain_description: str,
        team_name: str = "",
        preferred_pattern: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> TeamConfiguration:
        """Generate a complete team architecture from a domain description."""
        ctx = context or {}

        if preferred_pattern:
            try:
                pattern = TeamPattern(preferred_pattern)
            except ValueError:
                analysis = self.analyze_domain(domain_description, ctx)
                pattern = TeamPattern(analysis["recommended_pattern"])
        else:
            analysis = self.analyze_domain(domain_description, ctx)
            pattern = TeamPattern(analysis["recommended_pattern"])

        template = PATTERN_TEMPLATES[pattern]
        team = TeamConfiguration(
            name=team_name or f"Team-{pattern.value}-{self._total_teams_generated + 1}",
            pattern=pattern,
            domain=domain_description[:100],
            description=template["description"],
            communication_protocol=template["protocol"],
            max_parallel_agents=template["parallelism"],
        )

        agents = self._generate_agents(pattern, template, domain_description, ctx)
        team.agents = agents
        team.coordination_rules = self._generate_coordination_rules(pattern, agents)

        self._team_registry[team.team_id] = team
        self._total_teams_generated += 1
        self._pattern_usage[pattern.value] += 1

        logger.info(f"Team '{team.name}' generated with pattern {pattern.value}, {len(agents)} agents")
        return team

    def _generate_agents(
        self,
        pattern: TeamPattern,
        template: dict[str, Any],
        domain: str,
        context: dict[str, Any],
    ) -> list[AgentDefinition]:
        """Generate agent definitions for a team pattern."""
        agents: list[AgentDefinition] = []
        roles = template["roles"]
        agent_count = context.get("agent_count", len(roles))

        role_descriptions = {
            AgentRole.COORDINATOR: "Orchestrates team operations, routes tasks, and manages workflow",
            AgentRole.EXECUTOR: "Executes assigned tasks with precision and efficiency",
            AgentRole.REVIEWER: "Reviews outputs for quality, correctness, and completeness",
            AgentRole.ANALYST: "Analyzes requirements, data, and provides strategic insights",
            AgentRole.CREATOR: "Generates creative content, code, designs, and solutions",
            AgentRole.CRITIC: "Provides critical feedback and identifies improvement areas",
            AgentRole.SYNTHESIZER: "Combines multiple inputs into coherent unified outputs",
            AgentRole.GATEKEEPER: "Validates outputs against quality gates and standards",
            AgentRole.SPECIALIST: "Provides deep domain expertise in specific areas",
            AgentRole.OBSERVER: "Monitors team performance and reports metrics",
        }

        for i in range(min(agent_count, len(roles))):
            role = roles[i]
            agent = AgentDefinition(
                name=f"{role.value}-{i+1}",
                role=role,
                description=role_descriptions.get(role, f"{role.value} agent"),
                capabilities=self._infer_capabilities(role, domain),
                required_skills=self._infer_skills(role, pattern),
                model_preference="auto" if role != AgentRole.COORDINATOR else "flagship",
                priority=i + 1,
            )
            agents.append(agent)

        return agents

    def _infer_capabilities(self, role: AgentRole, domain: str) -> list[str]:
        """Infer agent capabilities based on role and domain."""
        base_capabilities = {
            AgentRole.COORDINATOR: ["task_routing", "team_orchestration", "workflow_management", "status_tracking"],
            AgentRole.EXECUTOR: ["task_execution", "tool_usage", "code_generation", "file_operations"],
            AgentRole.REVIEWER: ["quality_assessment", "error_detection", "code_review", "standards_enforcement"],
            AgentRole.ANALYST: ["data_analysis", "requirement_analysis", "strategy_development", "research"],
            AgentRole.CREATOR: ["content_generation", "design_creation", "creative_problem_solving", "prototyping"],
            AgentRole.CRITIC: ["critical_analysis", "edge_case_discovery", "risk_assessment", "improvement_suggestions"],
            AgentRole.SYNTHESIZER: ["information_integration", "summary_generation", "knowledge_consolidation", "report_writing"],
            AgentRole.GATEKEEPER: ["validation", "compliance_check", "threshold_testing", "approval_management"],
            AgentRole.SPECIALIST: ["domain_expertise", "deep_analysis", "technical_consulting", "best_practices"],
            AgentRole.OBSERVER: ["metric_collection", "performance_monitoring", "trend_analysis", "alerting"],
        }
        return base_capabilities.get(role, ["general_execution"])

    def _infer_skills(self, role: AgentRole, pattern: TeamPattern) -> list[str]:
        """Infer required skills based on role and team pattern."""
        skills: list[str] = []
        if role == AgentRole.COORDINATOR:
            skills.extend(["delegation", "scheduling", "progress_tracking"])
        if role == AgentRole.EXECUTOR:
            skills.extend(["tool_execution", "api_integration", "file_management"])
        if role == AgentRole.REVIEWER:
            skills.extend(["code_review", "quality_check", "error_analysis"])
        if pattern == TeamPattern.PIPELINE:
            skills.append("stage_handoff")
        if pattern == TeamPattern.FAN_OUT_FAN_IN:
            skills.append("result_aggregation")
        return skills

    def _generate_coordination_rules(
        self, pattern: TeamPattern, agents: list[AgentDefinition]
    ) -> list[str]:
        """Generate coordination rules for the team."""
        rules: list[str] = []
        rules.append("All agents must acknowledge task assignments within 5 seconds")
        rules.append("Critical errors must be escalated to coordinator immediately")

        if pattern == TeamPattern.PIPELINE:
            rules.append("Each stage must complete before the next begins")
            rules.append("Gatekeeper validates output at each stage boundary")
        elif pattern == TeamPattern.FAN_OUT_FAN_IN:
            rules.append("Coordinator broadcasts tasks to all executors simultaneously")
            rules.append("Synthesizer aggregates results when all executors complete")
        elif pattern == TeamPattern.PRODUCER_REVIEWER:
            rules.append("Creator produces output, Reviewer validates before release")
            rules.append("Maximum 3 review cycles per output")
        elif pattern == TeamPattern.SUPERVISOR:
            rules.append("Supervisor approves all major decisions")
            rules.append("Observer reports metrics to supervisor every cycle")
        elif pattern == TeamPattern.HIERARCHICAL:
            rules.append("Tasks flow down the hierarchy, results flow up")
            rules.append("Each level can delegate to sub-agents within scope")

        rules.append("Timeout triggers automatic escalation after 30 seconds")
        return rules

    # ── Team Management ─────────────────────────────────────────

    def get_team(self, team_id: str) -> Optional[TeamConfiguration]:
        """Retrieve a team configuration by ID."""
        return self._team_registry.get(team_id)

    def list_teams(self, pattern: str | None = None) -> list[TeamConfiguration]:
        """List all teams, optionally filtered by pattern."""
        teams = list(self._team_registry.values())
        if pattern:
            teams = [t for t in teams if t.pattern.value == pattern]
        return sorted(teams, key=lambda t: t.created_at, reverse=True)

    def clone_team(self, team_id: str, new_name: str = "") -> Optional[TeamConfiguration]:
        """Clone an existing team configuration with a new name."""
        original = self._team_registry.get(team_id)
        if not original:
            return None
        cloned = TeamConfiguration(
            name=new_name or f"{original.name}-clone",
            pattern=original.pattern,
            domain=original.domain,
            description=original.description,
            agents=[AgentDefinition(
                name=a.name,
                role=a.role,
                description=a.description,
                capabilities=list(a.capabilities),
                required_skills=list(a.required_skills),
                model_preference=a.model_preference,
                max_tokens=a.max_tokens,
                temperature=a.temperature,
                priority=a.priority,
                metadata=dict(a.metadata),
            ) for a in original.agents],
            communication_protocol=original.communication_protocol,
            coordination_rules=list(original.coordination_rules),
            max_parallel_agents=original.max_parallel_agents,
            timeout_seconds=original.timeout_seconds,
            version=original.version + 1,
        )
        self._team_registry[cloned.team_id] = cloned
        self._total_teams_generated += 1
        return cloned

    # ── Evolution & Delta Capture ───────────────────────────────

    def capture_evolution_delta(
        self,
        team_id: str,
        changes: list[str],
        success_metrics: dict[str, float],
        lessons_learned: list[str],
        agent_adjustments: dict[str, dict[str, Any]] | None = None,
    ) -> Optional[TeamEvolutionDelta]:
        """Capture evolution feedback from real team execution."""
        team = self._team_registry.get(team_id)
        if not team:
            logger.warning(f"Team {team_id} not found for evolution capture")
            return None

        delta = TeamEvolutionDelta(
            team_id=team_id,
            original_pattern=team.pattern,
            evolved_pattern=team.pattern,
            changes=changes,
            success_metrics=success_metrics,
            lessons_learned=lessons_learned,
            agent_adjustments=agent_adjustments or {},
        )
        self._evolution_history.append(delta)
        team.version += 1
        logger.info(f"Evolution delta captured for team {team.name} (v{team.version})")
        return delta

    def apply_evolution(self, team_id: str, delta_id: str) -> Optional[TeamConfiguration]:
        """Apply an evolution delta to update a team configuration."""
        team = self._team_registry.get(team_id)
        if not team:
            return None

        delta = next((d for d in self._evolution_history if d.delta_id == delta_id), None)
        if not delta:
            return None

        for agent_id, adjustments in delta.agent_adjustments.items():
            for agent in team.agents:
                if agent.agent_id == agent_id:
                    if "capabilities" in adjustments:
                        agent.capabilities = list(set(agent.capabilities + adjustments["capabilities"]))
                    if "skills" in adjustments:
                        agent.required_skills = list(set(agent.required_skills + adjustments["skills"]))
                    if "model_preference" in adjustments:
                        agent.model_preference = adjustments["model_preference"]

        team.version += 1
        team.metadata["last_evolved"] = datetime.now(timezone.utc).isoformat()
        team.metadata["evolution_count"] = team.metadata.get("evolution_count", 0) + 1
        logger.info(f"Evolution applied to team {team.name} (v{team.version})")
        return team

    # ── Validation ──────────────────────────────────────────────

    def validate_team(self, team_id: str) -> TeamValidationResult:
        """Validate a team architecture for correctness and completeness."""
        team = self._team_registry.get(team_id)
        if not team:
            return TeamValidationResult(valid=False, issues=["Team not found"])

        result = TeamValidationResult(pattern=team.pattern)
        issues: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        if not team.agents:
            issues.append("Team has no agents defined")
        if not team.coordination_rules:
            warnings.append("No coordination rules defined")
        if not team.name:
            warnings.append("Team name is empty")

        roles_seen = set()
        for agent in team.agents:
            if not agent.name:
                issues.append("Agent has no name")
            if not agent.capabilities:
                warnings.append(f"Agent {agent.name} has no capabilities")
            roles_seen.add(agent.role)

        template = PATTERN_TEMPLATES.get(team.pattern, {})
        expected_roles = set(template.get("roles", []))
        missing_roles = expected_roles - roles_seen
        if missing_roles:
            suggestions.append(f"Consider adding roles: {[r.value for r in missing_roles]}")

        has_coordinator = any(a.role == AgentRole.COORDINATOR for a in team.agents)
        if not has_coordinator:
            suggestions.append("Add a coordinator agent for task orchestration")

        result.issues = issues
        result.warnings = warnings
        result.suggestions = suggestions
        result.valid = len(issues) == 0
        result.coverage_score = len(roles_seen) / max(len(expected_roles), 1)
        result.efficiency_score = 0.8 if len(warnings) < 3 else 0.5
        result.robustness_score = 0.9 if has_coordinator else 0.6

        self._validation_results.append(result)
        return result

    # ── Statistics ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get team architect statistics."""
        return {
            "total_teams": len(self._team_registry),
            "total_generated": self._total_teams_generated,
            "pattern_usage": dict(self._pattern_usage),
            "evolution_deltas": len(self._evolution_history),
            "validation_count": len(self._validation_results),
            "active_patterns": list(set(t.pattern.value for t in self._team_registry.values())),
            "teams_by_pattern": {
                p.value: len([t for t in self._team_registry.values() if t.pattern == p])
                for p in TeamPattern
            },
        }

    def get_pattern_info(self, pattern_name: str) -> dict[str, Any]:
        """Get detailed information about a team pattern."""
        try:
            pattern = TeamPattern(pattern_name)
        except ValueError:
            return {"error": f"Unknown pattern: {pattern_name}"}

        template = PATTERN_TEMPLATES[pattern]
        teams_using = [t.name for t in self._team_registry.values() if t.pattern == pattern]
        return {
            "pattern": pattern.value,
            "description": template["description"],
            "best_for": template["best_for"],
            "roles": [r.value for r in template["roles"]],
            "protocol": template["protocol"].value,
            "flow": template["flow"],
            "max_parallelism": template["parallelism"],
            "teams_using": teams_using,
            "usage_count": self._pattern_usage.get(pattern.value, 0),
        }

    def reset(self) -> None:
        """Clear all internal state, reset counters, and reinitialize defaults."""
        self._team_registry.clear()
        self._evolution_history.clear()
        self._validation_results.clear()
        self._total_teams_generated = 0
        self._pattern_usage = {p.value: 0 for p in TeamPattern}
        logger.info("TeamArchitect state reset")


# ── Singleton ────────────────────────────────────────────────────────

team_architect = TeamArchitect()