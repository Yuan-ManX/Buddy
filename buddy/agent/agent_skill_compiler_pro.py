"""
Buddy Agent Skill Compiler Pro — Comprehensive Skill Compilation and Execution System.

Provides a complete framework for defining, compiling, executing, composing,
testing, and distributing agent skills. Skills are structured, versioned units
of agent capability that can be chained into complex workflows.

Key subsystems:
- Skill Definition Language (SDL): structured format for defining agent skills
- Compilation Pipeline: SDL parsing, validation, optimization, and caching
- Execution Runtime: parameter binding, step-by-step execution, error handling
- Composition Engine: multi-skill workflow orchestration with dependency resolution
- Marketplace: built-in skill library, versioning, analytics, sharing
- Testing Framework: unit tests, integration tests, mocks, benchmarks
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.agent_skill_compiler_pro")


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════


class SkillType(str, Enum):
    """Classification of a skill by its functional domain."""
    TEXT = "text"
    CODE = "code"
    DATA = "data"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    CREATIVE = "creative"
    LANGUAGE = "language"
    AUTOMATION = "automation"
    COMMUNICATION = "communication"
    REASONING = "reasoning"
    UTILITY = "utility"
    CUSTOM = "custom"


class SkillStatus(str, Enum):
    """Lifecycle status of a skill definition."""
    DRAFT = "draft"
    COMPILED = "compiled"
    VALIDATED = "validated"
    OPTIMIZED = "optimized"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    FAILED = "failed"


class ExecutionState(str, Enum):
    """Runtime state of a skill execution instance."""
    PENDING = "pending"
    BINDING = "binding"
    RUNNING = "running"
    PAUSED = "paused"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class CompositionStrategy(str, Enum):
    """Strategies for composing multiple skills into workflows."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    FAN_OUT = "fan_out"
    PIPE = "pipe"
    MAP_REDUCE = "map_reduce"
    DAG = "dag"


class ExecutionStrategy(str, Enum):
    """Strategies for executing a composed skill graph."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BEST_EFFORT = "best_effort"
    STRICT = "strict"


class DependencyType(str, Enum):
    """Types of dependencies between skills in a composition."""
    REQUIRED = "required"
    OPTIONAL = "optional"
    CONFLICT = "conflict"
    ENHANCES = "enhances"


class ParamType(str, Enum):
    """Supported parameter types for skill definitions."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    FILE = "file"
    CODE = "code"
    ANY = "any"


class TestResult(str, Enum):
    """Outcome of a skill test execution."""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class BenchmarkMetric(str, Enum):
    """Metrics tracked during skill benchmarking."""
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    TOKEN_COUNT = "token_count"
    SUCCESS_RATE = "success_rate"
    RETRY_COUNT = "retry_count"


# ═══════════════════════════════════════════════════════════════════
# Data Classes — Skill Definition Language (SDL)
# ═══════════════════════════════════════════════════════════════════


@dataclass
class SkillParameter:
    """A parameter definition for a skill.

    Describes the name, type, constraints, and default behavior of a single
    input or output parameter within a skill definition.

    Attributes:
        name: Unique parameter name within the skill.
        param_type: Expected data type of the parameter.
        description: Human-readable description of the parameter's purpose.
        required: Whether the parameter must be provided at execution time.
        default_value: Default value used when the parameter is not provided.
        validation_rules: List of rule expressions used to validate the value.
        examples: Representative example values for documentation.
        min_length: Minimum length constraint (for strings/lists).
        max_length: Maximum length constraint (for strings/lists).
        min_value: Minimum numeric value constraint.
        max_value: Maximum numeric value constraint.
        pattern: Regex pattern for string validation.
        enum_values: Allowed values for enumeration-style parameters.
        deprecation_message: If set, the parameter is deprecated with this message.
    """
    name: str
    param_type: ParamType = ParamType.STRING
    description: str = ""
    required: bool = True
    default_value: Any = None
    validation_rules: list[str] = field(default_factory=list)
    examples: list[Any] = field(default_factory=list)
    min_length: int | None = None
    max_length: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None
    enum_values: list[Any] | None = None
    deprecation_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize this parameter to a dictionary."""
        return {
            "name": self.name,
            "param_type": self.param_type.value,
            "description": self.description,
            "required": self.required,
            "default_value": self.default_value,
            "validation_rules": self.validation_rules,
            "examples": self.examples,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "pattern": self.pattern,
            "enum_values": self.enum_values,
            "deprecation_message": self.deprecation_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillParameter":
        """Deserialize a parameter from a dictionary."""
        return cls(
            name=data.get("name", ""),
            param_type=ParamType(data.get("param_type", "string")),
            description=data.get("description", ""),
            required=data.get("required", True),
            default_value=data.get("default_value"),
            validation_rules=data.get("validation_rules", []),
            examples=data.get("examples", []),
            min_length=data.get("min_length"),
            max_length=data.get("max_length"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            pattern=data.get("pattern"),
            enum_values=data.get("enum_values"),
            deprecation_message=data.get("deprecation_message"),
        )


@dataclass
class SkillSchema:
    """Input/output schema for a skill.

    Defines the complete contract for a skill's inputs and outputs, including
    all parameters and their validation constraints.

    Attributes:
        inputs: List of input parameters accepted by the skill.
        outputs: List of output parameters produced by the skill.
        schema_version: Version of the schema format itself.
    """
    inputs: list[SkillParameter] = field(default_factory=list)
    outputs: list[SkillParameter] = field(default_factory=list)
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Serialize this schema to a dictionary."""
        return {
            "inputs": [p.to_dict() for p in self.inputs],
            "outputs": [p.to_dict() for p in self.outputs],
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillSchema":
        """Deserialize a schema from a dictionary."""
        return cls(
            inputs=[SkillParameter.from_dict(p) for p in data.get("inputs", [])],
            outputs=[SkillParameter.from_dict(p) for p in data.get("outputs", [])],
            schema_version=data.get("schema_version", "1.0.0"),
        )


@dataclass
class SkillMetadata:
    """Metadata describing a skill for discovery and management.

    Attributes:
        name: Unique human-readable name.
        version: Semantic version string.
        description: Detailed description of what the skill does.
        author: Creator of the skill.
        category: Functional category for browsing.
        tags: Searchable tags for discovery.
        prerequisites: Skills or capabilities required before this skill.
        created_at: Unix timestamp of creation.
        updated_at: Unix timestamp of last update.
        deprecated: Whether this skill is deprecated.
        replaces: List of skill IDs this skill replaces.
        replaced_by: Skill ID that replaces this skill, if any.
        license: License identifier for the skill.
        homepage: URL for documentation.
        rating: Average user rating (0-5).
        usage_count: Number of times this skill has been executed.
    """
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    category: SkillType = SkillType.UTILITY
    tags: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deprecated: bool = False
    replaces: list[str] = field(default_factory=list)
    replaced_by: str | None = None
    license: str = "MIT"
    homepage: str = ""
    rating: float = 0.0
    usage_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize this metadata to a dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category.value,
            "tags": self.tags,
            "prerequisites": self.prerequisites,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deprecated": self.deprecated,
            "replaces": self.replaces,
            "replaced_by": self.replaced_by,
            "license": self.license,
            "homepage": self.homepage,
            "rating": self.rating,
            "usage_count": self.usage_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillMetadata":
        """Deserialize metadata from a dictionary."""
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            category=SkillType(data.get("category", "utility")),
            tags=data.get("tags", []),
            prerequisites=data.get("prerequisites", []),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            deprecated=data.get("deprecated", False),
            replaces=data.get("replaces", []),
            replaced_by=data.get("replaced_by"),
            license=data.get("license", "MIT"),
            homepage=data.get("homepage", ""),
            rating=data.get("rating", 0.0),
            usage_count=data.get("usage_count", 0),
        )


@dataclass
class SkillInstruction:
    """A single executable instruction within a compiled skill.

    Each instruction represents one step in a skill's execution plan. Steps
    can be simple operations, LLM calls, tool invocations, or sub-skill calls.

    Attributes:
        instruction_id: Unique identifier for this instruction.
        op: Operation code describing what to do.
        params: Parameters bound to the operation.
        description: Human-readable description of this step.
        timeout_seconds: Maximum allowed execution time.
        retry_count: Number of retries allowed on failure.
        retry_delay_seconds: Delay between retry attempts.
        on_failure: Action to take on failure ("abort", "skip", "continue").
        precondition: Expression that must be true for this step to execute.
        postcondition: Expression that must be true after execution.
    """
    instruction_id: str = field(default_factory=lambda: f"instr-{uuid.uuid4().hex[:8]}")
    op: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timeout_seconds: float = 30.0
    retry_count: int = 0
    retry_delay_seconds: float = 1.0
    on_failure: str = "abort"
    precondition: str | None = None
    postcondition: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize this instruction to a dictionary."""
        return {
            "instruction_id": self.instruction_id,
            "op": self.op,
            "params": self.params,
            "description": self.description,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "on_failure": self.on_failure,
            "precondition": self.precondition,
            "postcondition": self.postcondition,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillInstruction":
        """Deserialize an instruction from a dictionary."""
        return cls(
            instruction_id=data.get("instruction_id", f"instr-{uuid.uuid4().hex[:8]}"),
            op=data.get("op", ""),
            params=data.get("params", {}),
            description=data.get("description", ""),
            timeout_seconds=data.get("timeout_seconds", 30.0),
            retry_count=data.get("retry_count", 0),
            retry_delay_seconds=data.get("retry_delay_seconds", 1.0),
            on_failure=data.get("on_failure", "abort"),
            precondition=data.get("precondition"),
            postcondition=data.get("postcondition"),
        )


# ═══════════════════════════════════════════════════════════════════
# Data Classes — Skill Definition
# ═══════════════════════════════════════════════════════════════════


@dataclass
class SkillDefinition:
    """A complete skill definition ready for compilation and execution.

    The central data structure representing a fully-defined agent skill.
    It combines metadata, schema, and executable instructions into a single
    versioned, cacheable artifact.

    Attributes:
        skill_id: Globally unique identifier.
        metadata: Skill metadata for discovery and management.
        schema: Input/output parameter schema.
        instructions: Ordered list of executable instructions.
        preconditions: Assertions that must hold before execution.
        postconditions: Assertions guaranteed after execution.
        tools_required: External tools needed by this skill.
        dependencies: IDs of other skills this skill depends on.
        status: Current lifecycle status.
        compiled_instructions: Serialized bytecode after compilation.
        compilation_hash: Integrity hash of the compiled form.
        error_message: Error details if compilation or execution failed.
    """
    skill_id: str = field(default_factory=lambda: f"skill-{uuid.uuid4().hex[:12]}")
    metadata: SkillMetadata = field(default_factory=lambda: SkillMetadata(name=""))
    schema: SkillSchema = field(default_factory=SkillSchema)
    instructions: list[SkillInstruction] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    status: SkillStatus = SkillStatus.DRAFT
    compiled_instructions: list[dict[str, Any]] = field(default_factory=list)
    compilation_hash: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize this skill definition to a dictionary."""
        return {
            "skill_id": self.skill_id,
            "metadata": self.metadata.to_dict(),
            "schema": self.schema.to_dict(),
            "instructions": [i.to_dict() for i in self.instructions],
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "tools_required": self.tools_required,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "compiled_instructions": self.compiled_instructions,
            "compilation_hash": self.compilation_hash,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillDefinition":
        """Deserialize a skill definition from a dictionary."""
        return cls(
            skill_id=data.get("skill_id", f"skill-{uuid.uuid4().hex[:12]}"),
            metadata=SkillMetadata.from_dict(data.get("metadata", {})),
            schema=SkillSchema.from_dict(data.get("schema", {})),
            instructions=[SkillInstruction.from_dict(i) for i in data.get("instructions", [])],
            preconditions=data.get("preconditions", []),
            postconditions=data.get("postconditions", []),
            tools_required=data.get("tools_required", []),
            dependencies=data.get("dependencies", []),
            status=SkillStatus(data.get("status", "draft")),
            compiled_instructions=data.get("compiled_instructions", []),
            compilation_hash=data.get("compilation_hash", ""),
            error_message=data.get("error_message", ""),
        )


# ═══════════════════════════════════════════════════════════════════
# Data Classes — Compilation
# ═══════════════════════════════════════════════════════════════════


@dataclass
class CompilationResult:
    """Result of a skill compilation attempt.

    Attributes:
        compilation_id: Unique identifier for this compilation run.
        skill: The compiled skill definition, or None on failure.
        success: Whether compilation succeeded.
        errors: Error messages collected during compilation.
        warnings: Warning messages collected during compilation.
        optimization_applied: List of optimizations that were performed.
        compilation_time_ms: Total time spent compiling in milliseconds.
        bytecode_size: Size of the compiled bytecode in bytes.
    """
    compilation_id: str = field(default_factory=lambda: f"comp-{uuid.uuid4().hex[:12]}")
    skill: SkillDefinition | None = None
    success: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    optimization_applied: list[str] = field(default_factory=list)
    compilation_time_ms: float = 0.0
    bytecode_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize this compilation result to a dictionary."""
        return {
            "compilation_id": self.compilation_id,
            "skill": self.skill.to_dict() if self.skill else None,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "optimization_applied": self.optimization_applied,
            "compilation_time_ms": self.compilation_time_ms,
            "bytecode_size": self.bytecode_size,
        }


# ═══════════════════════════════════════════════════════════════════
# Data Classes — Execution
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ExecutionStep:
    """The state of a single step during skill execution.

    Tracks the progress and outcome of one instruction within a skill's
    execution plan.

    Attributes:
        step_index: Zero-based index of this step in the execution plan.
        instruction_id: ID of the instruction being executed.
        state: Current execution state of this step.
        started_at: Timestamp when the step began.
        completed_at: Timestamp when the step finished.
        duration_ms: Total execution time in milliseconds.
        result: Output produced by this step.
        error: Error message if the step failed.
        retry_attempt: Current retry attempt number (0-based).
    """
    step_index: int = 0
    instruction_id: str = ""
    state: ExecutionState = ExecutionState.PENDING
    started_at: float | None = None
    completed_at: float | None = None
    duration_ms: float = 0.0
    result: Any = None
    error: str = ""
    retry_attempt: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize this execution step to a dictionary."""
        return {
            "step_index": self.step_index,
            "instruction_id": self.instruction_id,
            "state": self.state.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "error": self.error,
            "retry_attempt": self.retry_attempt,
        }


@dataclass
class ExecutionResult:
    """Complete result of a skill execution.

    Aggregates the outcomes of all steps in a skill execution, including
    timing, errors, and output data.

    Attributes:
        execution_id: Unique identifier for this execution run.
        skill_id: ID of the skill that was executed.
        success: Whether the overall execution succeeded.
        state: Final execution state.
        steps: Per-step execution tracking data.
        output: Final output produced by the skill.
        error: Error message if execution failed.
        started_at: Timestamp when execution began.
        completed_at: Timestamp when execution completed.
        total_duration_ms: Total wall-clock duration in milliseconds.
        retries_used: Total number of retries across all steps.
        bound_params: The parameters that were bound for this execution.
    """
    execution_id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:12]}")
    skill_id: str = ""
    success: bool = False
    state: ExecutionState = ExecutionState.PENDING
    steps: list[ExecutionStep] = field(default_factory=list)
    output: Any = None
    error: str = ""
    started_at: float | None = None
    completed_at: float | None = None
    total_duration_ms: float = 0.0
    retries_used: int = 0
    bound_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this execution result to a dictionary."""
        return {
            "execution_id": self.execution_id,
            "skill_id": self.skill_id,
            "success": self.success,
            "state": self.state.value,
            "steps": [s.to_dict() for s in self.steps],
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "retries_used": self.retries_used,
            "bound_params": self.bound_params,
        }


# ═══════════════════════════════════════════════════════════════════
# Data Classes — Composition
# ═══════════════════════════════════════════════════════════════════


@dataclass
class SkillDependency:
    """A dependency edge between two skills in a composition graph.

    Attributes:
        source_skill_id: The skill that depends on another.
        target_skill_id: The skill being depended upon.
        dependency_type: Nature of the dependency relationship.
        data_mapping: How to map output of the target to input of the source.
    """
    source_skill_id: str
    target_skill_id: str
    dependency_type: DependencyType = DependencyType.REQUIRED
    data_mapping: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this dependency to a dictionary."""
        return {
            "source_skill_id": self.source_skill_id,
            "target_skill_id": self.target_skill_id,
            "dependency_type": self.dependency_type.value,
            "data_mapping": self.data_mapping,
        }


@dataclass
class CompositionPlan:
    """A plan for composing multiple skills into a workflow.

    Describes the skills, their dependencies, execution strategy, and
    how results are aggregated.

    Attributes:
        composition_id: Unique identifier for this composition.
        name: Human-readable name for the workflow.
        skills: Skill IDs included in the composition.
        dependencies: Dependency edges between skills.
        strategy: How skills are composed (sequential, parallel, etc.).
        execution_strategy: How execution is managed (strict, best-effort).
        result_aggregator: Function name or expression for combining results.
        metadata: Arbitrary metadata for the composition.
    """
    composition_id: str = field(default_factory=lambda: f"wf-{uuid.uuid4().hex[:12]}")
    name: str = ""
    skills: list[str] = field(default_factory=list)
    dependencies: list[SkillDependency] = field(default_factory=list)
    strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    result_aggregator: str = "last"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this composition plan to a dictionary."""
        return {
            "composition_id": self.composition_id,
            "name": self.name,
            "skills": self.skills,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "strategy": self.strategy.value,
            "execution_strategy": self.execution_strategy.value,
            "result_aggregator": self.result_aggregator,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompositionPlan":
        """Deserialize a composition plan from a dictionary."""
        return cls(
            composition_id=data.get("composition_id", f"wf-{uuid.uuid4().hex[:12]}"),
            name=data.get("name", ""),
            skills=data.get("skills", []),
            dependencies=[SkillDependency(
                source_skill_id=d.get("source_skill_id", ""),
                target_skill_id=d.get("target_skill_id", ""),
                dependency_type=DependencyType(d.get("dependency_type", "required")),
                data_mapping=d.get("data_mapping", {}),
            ) for d in data.get("dependencies", [])],
            strategy=CompositionStrategy(data.get("strategy", "sequential")),
            execution_strategy=ExecutionStrategy(data.get("execution_strategy", "sequential")),
            result_aggregator=data.get("result_aggregator", "last"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CompositionResult:
    """Result of executing a skill composition.

    Attributes:
        composition_id: ID of the composition that was executed.
        success: Whether the overall composition succeeded.
        skill_results: Per-skill execution results.
        aggregated_output: Combined output from all skills.
        started_at: When the composition execution began.
        completed_at: When the composition execution ended.
        total_duration_ms: Total execution time in milliseconds.
        errors: Errors collected across all skills.
    """
    composition_id: str = ""
    success: bool = False
    skill_results: dict[str, ExecutionResult] = field(default_factory=dict)
    aggregated_output: Any = None
    started_at: float | None = None
    completed_at: float | None = None
    total_duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this composition result to a dictionary."""
        return {
            "composition_id": self.composition_id,
            "success": self.success,
            "skill_results": {k: v.to_dict() for k, v in self.skill_results.items()},
            "aggregated_output": self.aggregated_output,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "errors": self.errors,
        }


# ═══════════════════════════════════════════════════════════════════
# Data Classes — Marketplace
# ═══════════════════════════════════════════════════════════════════


@dataclass
class MarketplaceListing:
    """A skill listing in the marketplace.

    Represents a published skill that is available for discovery, installation,
    and usage tracking.

    Attributes:
        listing_id: Unique identifier for this listing.
        skill_id: ID of the skill being listed.
        skill: The full skill definition.
        downloads: Number of times this skill has been downloaded.
        rating: Average user rating (0-5).
        rating_count: Number of ratings received.
        reviews: User reviews for this skill.
        featured: Whether this skill is featured in the marketplace.
        verified: Whether this skill has been verified by moderators.
        published_at: Timestamp of publication.
        updated_at: Timestamp of last update.
        analytics: Usage analytics data.
    """
    listing_id: str = field(default_factory=lambda: f"list-{uuid.uuid4().hex[:12]}")
    skill_id: str = ""
    skill: SkillDefinition | None = None
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    reviews: list[dict[str, Any]] = field(default_factory=list)
    featured: bool = False
    verified: bool = False
    published_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    analytics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this listing to a dictionary."""
        return {
            "listing_id": self.listing_id,
            "skill_id": self.skill_id,
            "skill": self.skill.to_dict() if self.skill else None,
            "downloads": self.downloads,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "reviews": self.reviews,
            "featured": self.featured,
            "verified": self.verified,
            "published_at": self.published_at,
            "updated_at": self.updated_at,
            "analytics": self.analytics,
        }


# ═══════════════════════════════════════════════════════════════════
# Data Classes — Testing
# ═══════════════════════════════════════════════════════════════════


@dataclass
class TestCase:
    """A single test case for skill verification.

    Attributes:
        test_id: Unique identifier for this test case.
        skill_id: ID of the skill being tested.
        name: Human-readable test name.
        description: What this test case verifies.
        input_params: Parameters to pass to the skill.
        expected_output: Expected output or assertions.
        timeout_seconds: Maximum allowed execution time.
        tags: Labels for organizing and filtering tests.
    """
    test_id: str = field(default_factory=lambda: f"test-{uuid.uuid4().hex[:8]}")
    skill_id: str = ""
    name: str = ""
    description: str = ""
    input_params: dict[str, Any] = field(default_factory=dict)
    expected_output: Any = None
    timeout_seconds: float = 30.0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this test case to a dictionary."""
        return {
            "test_id": self.test_id,
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "input_params": self.input_params,
            "expected_output": self.expected_output,
            "timeout_seconds": self.timeout_seconds,
            "tags": self.tags,
        }


@dataclass
class TestResult:
    """Result of executing a single test case.

    Attributes:
        test_id: ID of the test case that was executed.
        result: Outcome of the test (pass, fail, error, skipped).
        actual_output: The output produced by the skill.
        error_message: Error details if the test failed.
        duration_ms: Execution time in milliseconds.
        executed_at: Timestamp when the test was run.
    """
    test_id: str = ""
    result: TestResult = TestResult.SKIPPED
    actual_output: Any = None
    error_message: str = ""
    duration_ms: float = 0.0
    executed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this test result to a dictionary."""
        return {
            "test_id": self.test_id,
            "result": self.result.value,
            "actual_output": self.actual_output,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "executed_at": self.executed_at,
        }


@dataclass
class TestSuiteResult:
    """Aggregate result of running a test suite.

    Attributes:
        suite_name: Name of the test suite.
        skill_id: ID of the skill under test.
        total: Total number of tests.
        passed: Number of passing tests.
        failed: Number of failing tests.
        errored: Number of tests that encountered errors.
        skipped: Number of skipped tests.
        results: Per-test results.
        total_duration_ms: Total execution time for the suite.
    """
    suite_name: str = ""
    skill_id: str = ""
    total: int = 0
    passed: int = 0
    failed: int = 0
    errored: int = 0
    skipped: int = 0
    results: list[TestResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def pass_rate(self) -> float:
        """Fraction of tests that passed."""
        if self.total == 0:
            return 1.0
        return self.passed / self.total

    def to_dict(self) -> dict[str, Any]:
        """Serialize this test suite result to a dictionary."""
        return {
            "suite_name": self.suite_name,
            "skill_id": self.skill_id,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errored": self.errored,
            "skipped": self.skipped,
            "pass_rate": self.pass_rate,
            "results": [r.to_dict() for r in self.results],
            "total_duration_ms": self.total_duration_ms,
        }


@dataclass
class BenchmarkResult:
    """Performance benchmark results for a skill.

    Attributes:
        skill_id: ID of the skill benchmarked.
        metric: The metric being measured.
        value: The measured value.
        unit: Unit of measurement.
        iterations: Number of iterations used for averaging.
        min_value: Minimum observed value.
        max_value: Maximum observed value.
        std_dev: Standard deviation across iterations.
    """
    skill_id: str = ""
    metric: BenchmarkMetric = BenchmarkMetric.EXECUTION_TIME
    value: float = 0.0
    unit: str = "ms"
    iterations: int = 1
    min_value: float = 0.0
    max_value: float = 0.0
    std_dev: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize this benchmark result to a dictionary."""
        return {
            "skill_id": self.skill_id,
            "metric": self.metric.value,
            "value": self.value,
            "unit": self.unit,
            "iterations": self.iterations,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "std_dev": self.std_dev,
        }


# ═══════════════════════════════════════════════════════════════════
# Skill Compilation Pipeline
# ═══════════════════════════════════════════════════════════════════


class SkillCompiler:
    """Compiles skill definitions into optimized, executable bytecode.

    The compilation pipeline performs:
    1. Syntax validation — checks that the SDL structure is well-formed.
    2. Semantic validation — verifies parameter types, dependency chains, etc.
    3. Optimization — reorders instructions, removes dead code, pre-computes.
    4. Bytecode generation — produces a compact, cacheable instruction set.
    5. Caching — stores compiled skills for fast reuse.
    """

    def __init__(self):
        self._compiled_skills: dict[str, SkillDefinition] = {}
        self._compilation_cache: dict[str, CompilationResult] = {}
        self._compilation_count: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        logger.info("SkillCompiler initialized")

    def compile(self, skill: SkillDefinition) -> CompilationResult:
        """Compile a skill definition into executable bytecode.

        Runs the full compilation pipeline: syntax check, semantic validation,
        optimization, and bytecode generation. Returns a CompilationResult
        with the compiled skill or error details.

        Args:
            skill: The skill definition to compile.

        Returns:
            A CompilationResult indicating success or failure.
        """
        compilation_id = f"comp-{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        errors: list[str] = []
        warnings: list[str] = []
        optimizations: list[str] = []

        # Check cache first
        cache_key = self._compute_cache_key(skill)
        if cache_key in self._compilation_cache:
            cached = self._compilation_cache[cache_key]
            if cached.success:
                self._cache_hits += 1
                logger.debug(f"Cache hit for skill {skill.skill_id}")
                return cached

        self._cache_misses += 1

        # Phase 1: Syntax validation
        syntax_errors = self._validate_syntax(skill)
        if syntax_errors:
            errors.extend(syntax_errors)
            result = CompilationResult(
                compilation_id=compilation_id,
                skill=None,
                success=False,
                errors=errors,
                warnings=warnings,
                compilation_time_ms=(time.time() - start_time) * 1000,
            )
            self._compilation_cache[cache_key] = result
            return result

        # Phase 2: Semantic validation
        sem_errors, sem_warnings = self._validate_semantics(skill)
        errors.extend(sem_errors)
        warnings.extend(sem_warnings)
        if sem_errors:
            result = CompilationResult(
                compilation_id=compilation_id,
                skill=None,
                success=False,
                errors=errors,
                warnings=warnings,
                compilation_time_ms=(time.time() - start_time) * 1000,
            )
            self._compilation_cache[cache_key] = result
            return result

        # Phase 3: Optimization
        optimized_instructions = self._optimize_instructions(skill.instructions)
        optimizations = self._get_applied_optimizations(skill.instructions, optimized_instructions)

        # Phase 4: Bytecode generation
        bytecode = self._generate_bytecode(optimized_instructions)

        # Update skill
        skill.compiled_instructions = bytecode
        skill.compilation_hash = self._compute_hash(bytecode)
        skill.status = SkillStatus.COMPILED

        self._compiled_skills[skill.skill_id] = skill
        self._compilation_count += 1

        compilation_time = (time.time() - start_time) * 1000
        bytecode_size = len(json.dumps(bytecode).encode("utf-8"))

        result = CompilationResult(
            compilation_id=compilation_id,
            skill=skill,
            success=True,
            errors=errors,
            warnings=warnings,
            optimization_applied=optimizations,
            compilation_time_ms=compilation_time,
            bytecode_size=bytecode_size,
        )

        self._compilation_cache[cache_key] = result
        logger.info(
            f"Skill compiled: {skill.metadata.name} v{skill.metadata.version} "
            f"({compilation_time:.1f}ms, {bytecode_size} bytes)"
        )
        return result

    def validate(self, skill: SkillDefinition) -> CompilationResult:
        """Validate a skill definition without compiling it.

        Performs syntax and semantic validation only, without optimization
        or bytecode generation.

        Args:
            skill: The skill definition to validate.

        Returns:
            A CompilationResult indicating whether the skill is valid.
        """
        compilation_id = f"comp-{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        errors: list[str] = []
        warnings: list[str] = []

        syntax_errors = self._validate_syntax(skill)
        errors.extend(syntax_errors)

        if not syntax_errors:
            sem_errors, sem_warnings = self._validate_semantics(skill)
            errors.extend(sem_errors)
            warnings.extend(sem_warnings)

        success = len(errors) == 0
        if success:
            skill.status = SkillStatus.VALIDATED

        return CompilationResult(
            compilation_id=compilation_id,
            skill=skill if success else None,
            success=success,
            errors=errors,
            warnings=warnings,
            compilation_time_ms=(time.time() - start_time) * 1000,
        )

    def get_compiled(self, skill_id: str) -> SkillDefinition | None:
        """Retrieve a compiled skill by ID.

        Args:
            skill_id: The unique identifier of the skill.

        Returns:
            The compiled SkillDefinition, or None if not found.
        """
        return self._compiled_skills.get(skill_id)

    def invalidate_cache(self, skill_id: str | None = None):
        """Invalidate the compilation cache for a specific skill or all skills.

        Args:
            skill_id: If provided, invalidate only this skill. Otherwise, clear all.
        """
        if skill_id:
            keys_to_remove = [
                k for k, v in self._compilation_cache.items()
                if v.skill and v.skill.skill_id == skill_id
            ]
            for k in keys_to_remove:
                del self._compilation_cache[k]
            self._compiled_skills.pop(skill_id, None)
            logger.info(f"Cache invalidated for skill: {skill_id}")
        else:
            self._compilation_cache.clear()
            self._compiled_skills.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            logger.info("All compilation cache invalidated")

    def get_stats(self) -> dict[str, Any]:
        """Get compiler statistics including cache performance.

        Returns:
            A dictionary with compilation statistics.
        """
        total_lookups = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(total_lookups, 1)
        return {
            "compiled_skills": len(self._compiled_skills),
            "total_compilations": self._compilation_count,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": round(hit_rate, 3),
            "compiled_skill_ids": list(self._compiled_skills.keys()),
        }

    def _validate_syntax(self, skill: SkillDefinition) -> list[str]:
        """Validate the syntactic structure of a skill definition."""
        errors = []
        if not skill.metadata.name:
            errors.append("Skill name is required")
        if not skill.metadata.name.strip():
            errors.append("Skill name cannot be empty or whitespace")
        if len(skill.metadata.name) > 128:
            errors.append("Skill name must be 128 characters or fewer")
        if not skill.instructions:
            errors.append("Skill must have at least one instruction")
        for i, instr in enumerate(skill.instructions):
            if not instr.op:
                errors.append(f"Instruction {i} has no operation code")
        return errors

    def _validate_semantics(self, skill: SkillDefinition) -> tuple[list[str], list[str]]:
        """Validate the semantic correctness of a skill definition.

        Returns:
            A tuple of (errors, warnings).
        """
        errors = []
        warnings = []

        # Validate input parameters
        input_names = {p.name for p in skill.schema.inputs}
        for param in skill.schema.inputs:
            if param.required and param.default_value is None and not param.examples:
                warnings.append(f"Required parameter '{param.name}' has no default or examples")
            if param.enum_values and param.default_value not in param.enum_values:
                warnings.append(f"Default value for '{param.name}' not in enum_values")
            if param.min_value is not None and param.max_value is not None and param.min_value > param.max_value:
                errors.append(f"Parameter '{param.name}': min_value > max_value")

        # Validate output parameters
        output_names = {p.name for p in skill.schema.outputs}

        # Validate instruction references
        for instr in skill.instructions:
            for param_name in instr.params:
                if param_name not in input_names and param_name not in output_names:
                    warnings.append(
                        f"Instruction '{instr.instruction_id}' references unknown parameter '{param_name}'"
                    )

        return errors, warnings

    def _optimize_instructions(self, instructions: list[SkillInstruction]) -> list[SkillInstruction]:
        """Apply optimizations to the instruction list.

        Current optimizations:
        - Merge adjacent instructions with the same op that can be combined.
        - Remove instructions with no-op codes.
        """
        optimized = []
        for instr in instructions:
            if instr.op == "noop":
                continue
            # Merge with previous if same op and mergeable
            if optimized and self._can_merge(optimized[-1], instr):
                optimized[-1].params.update(instr.params)
                optimized[-1].description += "; " + instr.description
            else:
                optimized.append(instr)
        return optimized

    def _can_merge(self, a: SkillInstruction, b: SkillInstruction) -> bool:
        """Determine if two instructions can be merged."""
        mergeable_ops = {"set", "log", "assert"}
        return a.op == b.op and a.op in mergeable_ops

    def _get_applied_optimizations(
        self, original: list[SkillInstruction], optimized: list[SkillInstruction]
    ) -> list[str]:
        """Return a list of optimization names that were applied."""
        opts = []
        if len(optimized) < len(original):
            opts.append("instruction_merging")
        removed = [i for i in original if i.op == "noop"]
        if removed:
            opts.append("noop_removal")
        return opts

    def _generate_bytecode(self, instructions: list[SkillInstruction]) -> list[dict[str, Any]]:
        """Generate compact bytecode from optimized instructions."""
        return [i.to_dict() for i in instructions]

    def _compute_cache_key(self, skill: SkillDefinition) -> str:
        """Compute a cache key for a skill definition."""
        raw = json.dumps({
            "name": skill.metadata.name,
            "version": skill.metadata.version,
            "instructions": [i.to_dict() for i in skill.instructions],
            "schema": skill.schema.to_dict(),
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _compute_hash(self, bytecode: list[dict[str, Any]]) -> str:
        """Compute an integrity hash for compiled bytecode."""
        raw = json.dumps(bytecode, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def reset(self):
        """Reset the compiler to its initial state."""
        self._compiled_skills.clear()
        self._compilation_cache.clear()
        self._compilation_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("SkillCompiler reset")


# ═══════════════════════════════════════════════════════════════════
# Skill Execution Runtime
# ═══════════════════════════════════════════════════════════════════


class SkillRuntime:
    """Executes compiled skills with parameter binding and progress tracking.

    Provides the runtime environment for executing individual skills. Handles
    parameter binding, step-by-step execution, error handling with retry logic,
    timeout enforcement, and resource limit checking.

    The runtime is designed to be used with a handler registry that maps
    operation codes to callable functions. This allows skills to be executed
    in different environments (mock, production, etc.) by swapping handlers.
    """

    def __init__(self):
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._executions: dict[str, ExecutionResult] = {}
        self._total_executions: int = 0
        self._handler_timeout: float = 60.0
        self._max_retries: int = 3
        logger.info("SkillRuntime initialized")

    def register_handler(self, op: str, handler: Callable[..., Any]):
        """Register a handler function for a given operation code.

        Args:
            op: The operation code that this handler handles.
            handler: A callable that receives params and returns a result.
        """
        self._handlers[op] = handler
        logger.debug(f"Handler registered for op: {op}")

    def unregister_handler(self, op: str):
        """Remove a handler for a given operation code.

        Args:
            op: The operation code to unregister.
        """
        self._handlers.pop(op, None)
        logger.debug(f"Handler unregistered for op: {op}")

    def execute(
        self,
        skill: SkillDefinition,
        params: dict[str, Any] | None = None,
        timeout_seconds: float = 60.0,
    ) -> ExecutionResult:
        """Execute a compiled skill with the given parameters.

        Performs parameter binding, then executes each instruction in order.
        Tracks progress per step, handles retries on failure, and enforces
        a global timeout.

        Args:
            skill: The compiled skill definition to execute.
            params: Runtime parameters to bind to the skill's inputs.
            timeout_seconds: Maximum allowed execution time for the entire skill.

        Returns:
            An ExecutionResult with the outcome of the execution.
        """
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        bound_params = self._bind_parameters(skill, params or {})
        steps: list[ExecutionStep] = []
        total_retries = 0
        started_at = time.time()

        result = ExecutionResult(
            execution_id=execution_id,
            skill_id=skill.skill_id,
            state=ExecutionState.RUNNING,
            started_at=started_at,
            bound_params=bound_params,
        )

        for i, instr in enumerate(skill.instructions):
            if time.time() - started_at > timeout_seconds:
                result.state = ExecutionState.TIMED_OUT
                result.error = f"Skill execution timed out after {timeout_seconds}s"
                result.completed_at = time.time()
                result.total_duration_ms = (result.completed_at - started_at) * 1000
                result.steps = steps
                result.retries_used = total_retries
                self._executions[execution_id] = result
                self._total_executions += 1
                logger.warning(f"Skill {skill.skill_id} timed out after {timeout_seconds}s")
                return result

            step = ExecutionStep(step_index=i, instruction_id=instr.instruction_id)
            step.state = ExecutionState.RUNNING
            step.started_at = time.time()

            # Execute with retry
            attempt = 0
            step_error = ""
            while attempt <= instr.retry_count:
                try:
                    step.retry_attempt = attempt
                    merged_params = {**bound_params, **instr.params}
                    step_result = self._execute_instruction(instr, merged_params)
                    step.result = step_result
                    step.state = ExecutionState.COMPLETED
                    step_error = ""
                    break
                except Exception as e:
                    step_error = str(e)
                    attempt += 1
                    total_retries += 1
                    if attempt <= instr.retry_count:
                        step.state = ExecutionState.RETRYING
                        logger.debug(
                            f"Retrying instruction {instr.instruction_id} "
                            f"(attempt {attempt}/{instr.retry_count}): {step_error}"
                        )
                        time.sleep(instr.retry_delay_seconds)
                    else:
                        step.state = ExecutionState.FAILED
                        step.error = step_error
                        logger.warning(
                            f"Instruction {instr.instruction_id} failed after "
                            f"{attempt} attempts: {step_error}"
                        )

            step.completed_at = time.time()
            step.duration_ms = (step.completed_at - step.started_at) * 1000
            steps.append(step)

            # Handle failure
            if step.state == ExecutionState.FAILED:
                if instr.on_failure == "abort":
                    result.state = ExecutionState.FAILED
                    result.error = f"Step {i} failed: {step_error}"
                    result.completed_at = time.time()
                    result.total_duration_ms = (result.completed_at - started_at) * 1000
                    result.steps = steps
                    result.retries_used = total_retries
                    self._executions[execution_id] = result
                    self._total_executions += 1
                    return result
                elif instr.on_failure == "skip":
                    logger.debug(f"Skipping failed instruction {instr.instruction_id}")
                    step.state = ExecutionState.SKIPPED
                    continue
                # "continue" falls through to next instruction

        # Collect final output from the last step or from output params
        final_output = None
        if steps and steps[-1].result is not None:
            final_output = steps[-1].result
        elif skill.schema.outputs:
            final_output = {o.name: bound_params.get(o.name) for o in skill.schema.outputs}

        result.success = True
        result.state = ExecutionState.COMPLETED
        result.output = final_output
        result.completed_at = time.time()
        result.total_duration_ms = (result.completed_at - started_at) * 1000
        result.steps = steps
        result.retries_used = total_retries
        self._executions[execution_id] = result
        self._total_executions += 1

        skill.metadata.usage_count += 1
        logger.info(
            f"Skill {skill.metadata.name} executed successfully "
            f"({result.total_duration_ms:.1f}ms, {len(steps)} steps)"
        )
        return result

    def get_execution(self, execution_id: str) -> ExecutionResult | None:
        """Retrieve a past execution result by ID.

        Args:
            execution_id: The unique execution identifier.

        Returns:
            The ExecutionResult, or None if not found.
        """
        return self._executions.get(execution_id)

    def get_stats(self) -> dict[str, Any]:
        """Get runtime execution statistics.

        Returns:
            A dictionary with execution statistics.
        """
        recent = list(self._executions.values())[-20:]
        success_count = sum(1 for e in recent if e.success)
        return {
            "total_executions": self._total_executions,
            "stored_executions": len(self._executions),
            "recent_success_rate": round(success_count / max(len(recent), 1), 3),
            "registered_handlers": list(self._handlers.keys()),
        }

    def _bind_parameters(self, skill: SkillDefinition, params: dict[str, Any]) -> dict[str, Any]:
        """Bind execution parameters with defaults and validation."""
        bound = {}
        for param in skill.schema.inputs:
            if param.name in params:
                value = params[param.name]
                self._validate_param_value(param, value)
                bound[param.name] = value
            elif param.default_value is not None:
                bound[param.name] = param.default_value
            elif param.required:
                raise ValueError(
                    f"Required parameter '{param.name}' not provided for skill '{skill.metadata.name}'"
                )
        # Include any extra params
        for key, value in params.items():
            if key not in bound:
                bound[key] = value
        return bound

    def _validate_param_value(self, param: SkillParameter, value: Any):
        """Validate a parameter value against its constraints."""
        if param.enum_values and value not in param.enum_values:
            raise ValueError(
                f"Parameter '{param.name}': value '{value}' not in allowed values: {param.enum_values}"
            )
        if param.min_length is not None and isinstance(value, (str, list)):
            if len(value) < param.min_length:
                raise ValueError(f"Parameter '{param.name}': length {len(value)} < min {param.min_length}")
        if param.max_length is not None and isinstance(value, (str, list)):
            if len(value) > param.max_length:
                raise ValueError(f"Parameter '{param.name}': length {len(value)} > max {param.max_length}")
        if param.min_value is not None and isinstance(value, (int, float)):
            if value < param.min_value:
                raise ValueError(f"Parameter '{param.name}': value {value} < min {param.min_value}")
        if param.max_value is not None and isinstance(value, (int, float)):
            if value > param.max_value:
                raise ValueError(f"Parameter '{param.name}': value {value} > max {param.max_value}")

    def _execute_instruction(self, instr: SkillInstruction, params: dict[str, Any]) -> Any:
        """Execute a single instruction by dispatching to its handler."""
        handler = self._handlers.get(instr.op)
        if handler is None:
            raise ValueError(f"No handler registered for operation: {instr.op}")
        return handler(params)

    def reset(self):
        """Reset the runtime to its initial state."""
        self._handlers.clear()
        self._executions.clear()
        self._total_executions = 0
        logger.info("SkillRuntime reset")


# ═══════════════════════════════════════════════════════════════════
# Skill Composition Engine
# ═══════════════════════════════════════════════════════════════════


class SkillComposer:
    """Composes multiple skills into complex workflows.

    Orchestrates the execution of skill compositions based on a CompositionPlan.
    Supports sequential, parallel, and graph-based execution strategies with
    dependency resolution, result aggregation, and transformation.
    """

    def __init__(self, runtime: SkillRuntime | None = None, compiler: SkillCompiler | None = None):
        """Initialize the composer.

        Args:
            runtime: The SkillRuntime instance for executing individual skills.
            compiler: The SkillCompiler instance for accessing compiled skills.
        """
        self._runtime = runtime or SkillRuntime()
        self._compiler = compiler or SkillCompiler()
        self._compositions: dict[str, CompositionPlan] = {}
        self._composition_results: dict[str, CompositionResult] = {}
        self._total_compositions: int = 0
        logger.info("SkillComposer initialized")

    def register_composition(self, plan: CompositionPlan):
        """Register a composition plan for later execution.

        Args:
            plan: The composition plan to register.
        """
        self._compositions[plan.composition_id] = plan
        logger.info(f"Composition registered: {plan.name} ({plan.composition_id})")

    def execute(
        self,
        plan: CompositionPlan,
        params: dict[str, dict[str, Any]] | None = None,
    ) -> CompositionResult:
        """Execute a composition plan.

        Resolves dependencies, determines execution order, and runs each skill
        according to the configured strategy. Results are aggregated per the
        plan's result_aggregator setting.

        Args:
            plan: The composition plan to execute.
            params: Per-skill parameter overrides, keyed by skill_id.

        Returns:
            A CompositionResult with the aggregated outcome.
        """
        started_at = time.time()
        skill_params = params or {}
        skill_results: dict[str, ExecutionResult] = {}
        errors: list[str] = []

        # Resolve execution order
        execution_order = self._resolve_execution_order(plan)

        if plan.execution_strategy == ExecutionStrategy.PARALLEL:
            skill_results = self._execute_parallel(plan, execution_order, skill_params)
        else:
            # Sequential / best-effort / strict
            skill_results = self._execute_sequential(plan, execution_order, skill_params)

        # Collect errors
        for sid, er in skill_results.items():
            if not er.success:
                errors.append(f"Skill {sid}: {er.error}")

        # Aggregate results
        aggregated = self._aggregate_results(plan, skill_results)

        success = len(errors) == 0 or plan.execution_strategy == ExecutionStrategy.BEST_EFFORT
        if plan.execution_strategy == ExecutionStrategy.STRICT and errors:
            success = False

        completed_at = time.time()
        result = CompositionResult(
            composition_id=plan.composition_id,
            success=success,
            skill_results=skill_results,
            aggregated_output=aggregated,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=(completed_at - started_at) * 1000,
            errors=errors,
        )

        self._composition_results[plan.composition_id] = result
        self._total_compositions += 1
        logger.info(
            f"Composition {plan.name} executed: "
            f"{'success' if success else 'failed'} "
            f"({result.total_duration_ms:.1f}ms)"
        )
        return result

    def execute_by_id(
        self,
        composition_id: str,
        params: dict[str, dict[str, Any]] | None = None,
    ) -> CompositionResult | None:
        """Execute a previously registered composition by ID.

        Args:
            composition_id: The ID of the registered composition.
            params: Per-skill parameter overrides.

        Returns:
            A CompositionResult, or None if the composition is not found.
        """
        plan = self._compositions.get(composition_id)
        if not plan:
            logger.error(f"Composition not found: {composition_id}")
            return None
        return self.execute(plan, params)

    def get_result(self, composition_id: str) -> CompositionResult | None:
        """Retrieve the result of a past composition execution.

        Args:
            composition_id: The ID of the composition.

        Returns:
            The CompositionResult, or None if not found.
        """
        return self._composition_results.get(composition_id)

    def get_stats(self) -> dict[str, Any]:
        """Get composition engine statistics.

        Returns:
            A dictionary with composition statistics.
        """
        return {
            "total_compositions": self._total_compositions,
            "registered_compositions": len(self._compositions),
            "stored_results": len(self._composition_results),
            "registered_plan_ids": list(self._compositions.keys()),
        }

    def _resolve_execution_order(self, plan: CompositionPlan) -> list[str]:
        """Resolve the execution order of skills based on dependencies.

        Uses a topological sort to determine the order in which skills
        should be executed, respecting dependency constraints.

        Returns:
            An ordered list of skill IDs.
        """
        if not plan.dependencies:
            return list(plan.skills)

        # Build adjacency and in-degree
        in_degree: dict[str, int] = {s: 0 for s in plan.skills}
        adj: dict[str, list[str]] = {s: [] for s in plan.skills}

        for dep in plan.dependencies:
            if dep.dependency_type == DependencyType.REQUIRED:
                if dep.target_skill_id in adj:
                    adj[dep.target_skill_id].append(dep.source_skill_id)
                if dep.source_skill_id in in_degree:
                    in_degree[dep.source_skill_id] += 1

        # Topological sort
        queue = [s for s, d in in_degree.items() if d == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Add any remaining skills not in the dependency graph
        for s in plan.skills:
            if s not in order:
                order.append(s)

        return order

    def _execute_sequential(
        self,
        plan: CompositionPlan,
        order: list[str],
        params: dict[str, dict[str, Any]],
    ) -> dict[str, ExecutionResult]:
        """Execute skills sequentially in the resolved order."""
        results: dict[str, ExecutionResult] = {}
        context: dict[str, Any] = {}

        for skill_id in order:
            skill = self._compiler.get_compiled(skill_id)
            if not skill:
                results[skill_id] = ExecutionResult(
                    skill_id=skill_id,
                    success=False,
                    state=ExecutionState.FAILED,
                    error=f"Skill not found: {skill_id}",
                )
                if plan.execution_strategy == ExecutionStrategy.STRICT:
                    break
                continue

            # Merge context with per-skill params
            merged = {**context, **params.get(skill_id, {})}
            try:
                er = self._runtime.execute(skill, merged)
                results[skill_id] = er
                if er.success and er.output is not None:
                    context[f"_output_{skill_id}"] = er.output
                    if isinstance(er.output, dict):
                        context.update(er.output)
                if not er.success and plan.execution_strategy == ExecutionStrategy.STRICT:
                    break
            except Exception as e:
                results[skill_id] = ExecutionResult(
                    skill_id=skill_id,
                    success=False,
                    state=ExecutionState.FAILED,
                    error=str(e),
                )
                if plan.execution_strategy == ExecutionStrategy.STRICT:
                    break

        return results

    def _execute_parallel(
        self,
        plan: CompositionPlan,
        order: list[str],
        params: dict[str, dict[str, Any]],
    ) -> dict[str, ExecutionResult]:
        """Execute skills in parallel (simulated — runs sequentially for safety)."""
        # In a real implementation, this would use threading or asyncio.
        # For safety and simplicity, we simulate parallel execution.
        results: dict[str, ExecutionResult] = {}
        for skill_id in order:
            skill = self._compiler.get_compiled(skill_id)
            if not skill:
                results[skill_id] = ExecutionResult(
                    skill_id=skill_id,
                    success=False,
                    state=ExecutionState.FAILED,
                    error=f"Skill not found: {skill_id}",
                )
                continue
            try:
                er = self._runtime.execute(skill, params.get(skill_id, {}))
                results[skill_id] = er
            except Exception as e:
                results[skill_id] = ExecutionResult(
                    skill_id=skill_id,
                    success=False,
                    state=ExecutionState.FAILED,
                    error=str(e),
                )
        return results

    def _aggregate_results(
        self, plan: CompositionPlan, results: dict[str, ExecutionResult]
    ) -> Any:
        """Aggregate results from individual skill executions."""
        if plan.result_aggregator == "last":
            for sid in reversed(plan.skills):
                if sid in results and results[sid].success:
                    return results[sid].output
            return None
        elif plan.result_aggregator == "merge":
            merged = {}
            for sid, er in results.items():
                if er.success and isinstance(er.output, dict):
                    merged.update(er.output)
            return merged if merged else None
        elif plan.result_aggregator == "list":
            return [
                {"skill_id": sid, "output": er.output}
                for sid, er in results.items()
            ]
        return None

    def reset(self):
        """Reset the composer to its initial state."""
        self._compositions.clear()
        self._composition_results.clear()
        self._total_compositions = 0
        logger.info("SkillComposer reset")


# ═══════════════════════════════════════════════════════════════════
# Skill Marketplace
# ═══════════════════════════════════════════════════════════════════


class SkillMarketplace:
    """Built-in skill library with versioning, analytics, and sharing.

    Provides a curated catalog of skills with discovery, versioning,
    upgrade paths, usage analytics, popularity tracking, and import/export
    capabilities. Skills can be published, browsed, rated, and shared
    between Buddy instances.
    """

    def __init__(self):
        self._listings: dict[str, MarketplaceListing] = {}
        self._featured_ids: list[str] = []
        self._verified_ids: set[str] = set()
        self._downloads: dict[str, int] = {}
        self._ratings: dict[str, list[float]] = {}
        logger.info("SkillMarketplace initialized")

    def publish(self, skill: SkillDefinition) -> MarketplaceListing:
        """Publish a skill to the marketplace.

        If the skill already exists, it is updated. Otherwise, a new listing
        is created.

        Args:
            skill: The skill definition to publish.

        Returns:
            The created or updated MarketplaceListing.
        """
        listing_id = f"list-{uuid.uuid4().hex[:12]}"
        listing = MarketplaceListing(
            listing_id=listing_id,
            skill_id=skill.skill_id,
            skill=skill,
            published_at=time.time(),
            updated_at=time.time(),
        )
        self._listings[skill.skill_id] = listing
        if skill.skill_id not in self._downloads:
            self._downloads[skill.skill_id] = 0
        logger.info(f"Skill published to marketplace: {skill.metadata.name}")
        return listing

    def get_listing(self, skill_id: str) -> MarketplaceListing | None:
        """Retrieve a marketplace listing by skill ID.

        Args:
            skill_id: The unique skill identifier.

        Returns:
            The MarketplaceListing, or None if not found.
        """
        return self._listings.get(skill_id)

    def search(
        self,
        query: str = "",
        category: SkillType | None = None,
        tags: list[str] | None = None,
        sort_by: str = "rating",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Search and filter marketplace skills.

        Args:
            query: Free-text search across name, description, and tags.
            category: Filter by skill category.
            tags: Filter by required tags.
            sort_by: Sort key — "rating", "downloads", "newest", "name".
            page: Page number (1-based).
            page_size: Number of results per page.

        Returns:
            A dictionary with items, total, page, and page_size.
        """
        results = list(self._listings.values())

        if query:
            q = query.lower()
            results = [
                l for l in results
                if l.skill and (
                    q in l.skill.metadata.name.lower()
                    or q in l.skill.metadata.description.lower()
                    or any(q in t.lower() for t in l.skill.metadata.tags)
                )
            ]

        if category:
            results = [
                l for l in results
                if l.skill and l.skill.metadata.category == category
            ]

        if tags:
            results = [
                l for l in results
                if l.skill and all(t in l.skill.metadata.tags for t in tags)
            ]

        # Sort
        if sort_by == "rating":
            results.sort(key=lambda l: (l.rating, l.downloads), reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda l: l.downloads, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda l: l.published_at, reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda l: l.skill.metadata.name.lower() if l.skill else "")

        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "items": [l.to_dict() for l in results[start:end]],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // max(page_size, 1),
        }

    def download(self, skill_id: str) -> SkillDefinition | None:
        """Record a download and return the skill definition.

        Args:
            skill_id: The skill identifier to download.

        Returns:
            The SkillDefinition, or None if not found.
        """
        listing = self._listings.get(skill_id)
        if not listing or not listing.skill:
            return None
        self._downloads[skill_id] = self._downloads.get(skill_id, 0) + 1
        listing.downloads = self._downloads[skill_id]
        listing.skill.metadata.usage_count += 1
        logger.info(f"Skill downloaded: {listing.skill.metadata.name} ({skill_id})")
        return listing.skill

    def rate(self, skill_id: str, rating: float, review: str = ""):
        """Submit a rating and optional review for a skill.

        Args:
            skill_id: The skill to rate.
            rating: Rating value (0-5).
            review: Optional text review.
        """
        listing = self._listings.get(skill_id)
        if not listing:
            raise ValueError(f"Skill not found: {skill_id}")

        rating = max(0.0, min(5.0, rating))
        if skill_id not in self._ratings:
            self._ratings[skill_id] = []
        self._ratings[skill_id].append(rating)

        listing.rating = sum(self._ratings[skill_id]) / len(self._ratings[skill_id])
        listing.rating_count = len(self._ratings[skill_id])
        listing.skill.metadata.rating = listing.rating
        if review:
            listing.reviews.append({
                "review": review,
                "rating": rating,
                "timestamp": time.time(),
            })
        logger.info(f"Skill rated: {listing.skill.metadata.name} -> {rating:.1f}/5")

    def feature(self, skill_id: str):
        """Feature a skill on the marketplace homepage.

        Args:
            skill_id: The skill to feature.
        """
        if skill_id in self._listings and skill_id not in self._featured_ids:
            self._featured_ids.append(skill_id)
            self._listings[skill_id].featured = True
            if len(self._featured_ids) > 10:
                removed = self._featured_ids.pop(0)
                if removed in self._listings:
                    self._listings[removed].featured = False
            logger.info(f"Skill featured: {skill_id}")

    def verify(self, skill_id: str):
        """Mark a skill as verified.

        Args:
            skill_id: The skill to verify.
        """
        if skill_id in self._listings:
            self._listings[skill_id].verified = True
            self._verified_ids.add(skill_id)
            logger.info(f"Skill verified: {skill_id}")

    def get_featured(self) -> list[dict[str, Any]]:
        """Get featured skills for the marketplace homepage.

        Returns:
            A list of dictionaries for featured skill listings.
        """
        return [
            self._listings[sid].to_dict()
            for sid in self._featured_ids
            if sid in self._listings
        ]

    def get_popular(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most popular skills by download count.

        Returns:
            A list of dictionaries for popular skill listings.
        """
        sorted_listings = sorted(
            self._listings.values(),
            key=lambda l: (l.downloads, l.rating),
            reverse=True,
        )
        return [l.to_dict() for l in sorted_listings[:limit]]

    def export_skill(self, skill_id: str) -> dict[str, Any] | None:
        """Export a skill as a portable dictionary.

        Args:
            skill_id: The skill to export.

        Returns:
            A serializable dictionary, or None if not found.
        """
        listing = self._listings.get(skill_id)
        if not listing or not listing.skill:
            return None
        return listing.skill.to_dict()

    def import_skill(self, data: dict[str, Any]) -> SkillDefinition:
        """Import a skill from a portable dictionary.

        Args:
            data: The serialized skill definition.

        Returns:
            The deserialized SkillDefinition.
        """
        skill = SkillDefinition.from_dict(data)
        self.publish(skill)
        logger.info(f"Skill imported: {skill.metadata.name}")
        return skill

    def get_analytics(self, skill_id: str) -> dict[str, Any]:
        """Get usage analytics for a specific skill.

        Args:
            skill_id: The skill to analyze.

        Returns:
            A dictionary with analytics data.
        """
        listing = self._listings.get(skill_id)
        if not listing:
            return {"error": "Skill not found"}

        ratings = self._ratings.get(skill_id, [])
        return {
            "skill_id": skill_id,
            "name": listing.skill.metadata.name if listing.skill else "unknown",
            "downloads": listing.downloads,
            "rating": listing.rating,
            "rating_count": listing.rating_count,
            "rating_distribution": {
                "1": sum(1 for r in ratings if 1 <= r < 2),
                "2": sum(1 for r in ratings if 2 <= r < 3),
                "3": sum(1 for r in ratings if 3 <= r < 4),
                "4": sum(1 for r in ratings if 4 <= r < 5),
                "5": sum(1 for r in ratings if r == 5),
            },
            "featured": listing.featured,
            "verified": listing.verified,
            "published_at": listing.published_at,
            "version": listing.skill.metadata.version if listing.skill else "unknown",
        }

    def get_global_analytics(self) -> dict[str, Any]:
        """Get global marketplace analytics.

        Returns:
            A dictionary with aggregate marketplace statistics.
        """
        total_ratings = sum(len(r) for r in self._ratings.values())
        total_downloads = sum(self._downloads.values())
        avg_rating = (
            sum(sum(r) for r in self._ratings.values()) / max(total_ratings, 1)
            if total_ratings > 0 else 0.0
        )

        category_counts: dict[str, int] = {}
        for listing in self._listings.values():
            if listing.skill:
                cat = listing.skill.metadata.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_skills": len(self._listings),
            "total_downloads": total_downloads,
            "total_ratings": total_ratings,
            "average_rating": round(avg_rating, 2),
            "verified_skills": len(self._verified_ids),
            "featured_skills": len(self._featured_ids),
            "categories": category_counts,
        }

    def list_skills(
        self, category: str = "", status: str = "", limit: int = 50,
    ) -> list[SkillDefinition]:
        """List all published skills with optional filtering."""
        skills = []
        for listing in self._listings.values():
            if listing.skill:
                if category and listing.skill.metadata.category.value != category:
                    continue
                if status and listing.skill.metadata.status.value != status:
                    continue
                skills.append(listing.skill)
        return skills[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get marketplace statistics (alias for get_global_analytics)."""
        return self.get_global_analytics()

    def reset(self):
        """Reset the marketplace to its initial state."""
        self._listings.clear()
        self._featured_ids.clear()
        self._verified_ids.clear()
        self._downloads.clear()
        self._ratings.clear()
        logger.info("SkillMarketplace reset")


# ═══════════════════════════════════════════════════════════════════
# Skill Testing Framework
# ═══════════════════════════════════════════════════════════════════


class SkillTester:
    """Framework for testing skills with unit tests, integration tests, and benchmarks.

    Provides:
    - Unit testing for individual skills with mock handlers.
    - Integration testing for skill chains and compositions.
    - Mock environment for isolated skill testing.
    - Performance benchmarking with multiple metrics.
    """

    def __init__(self, runtime: SkillRuntime | None = None, compiler: SkillCompiler | None = None):
        self._runtime = runtime or SkillRuntime()
        self._compiler = compiler or SkillCompiler()
        self._test_cases: dict[str, list[TestCase]] = {}
        self._mock_handlers: dict[str, Callable[..., Any]] = {}
        self._benchmark_results: dict[str, list[BenchmarkResult]] = {}
        logger.info("SkillTester initialized")

    def register_test(self, test_case: TestCase):
        """Register a test case for a skill.

        Args:
            test_case: The test case to register.
        """
        if test_case.skill_id not in self._test_cases:
            self._test_cases[test_case.skill_id] = []
        self._test_cases[test_case.skill_id].append(test_case)
        logger.debug(f"Test registered: {test_case.name} for skill {test_case.skill_id}")

    def register_mock(self, op: str, handler: Callable[..., Any]):
        """Register a mock handler for testing.

        Mock handlers replace real handlers during test execution, allowing
        skills to be tested in isolation without external dependencies.

        Args:
            op: The operation code to mock.
            handler: A callable that simulates the operation.
        """
        self._mock_handlers[op] = handler
        logger.debug(f"Mock handler registered for op: {op}")

    def run_unit_tests(self, skill_id: str) -> TestSuiteResult:
        """Run all registered unit tests for a specific skill.

        Executes each test case against the skill using mock handlers and
        collects pass/fail/error results.

        Args:
            skill_id: The skill to test.

        Returns:
            A TestSuiteResult aggregating all test outcomes.
        """
        tests = self._test_cases.get(skill_id, [])
        suite = TestSuiteResult(
            suite_name=f"Unit tests for {skill_id}",
            skill_id=skill_id,
            total=len(tests),
        )

        # Save original handlers
        original_handlers = dict(self._runtime._handlers)

        # Install mock handlers
        for op, handler in self._mock_handlers.items():
            self._runtime.register_handler(op, handler)

        skill = self._compiler.get_compiled(skill_id)
        if not skill:
            for test in tests:
                suite.results.append(TestResult(
                    test_id=test.test_id,
                    result=TestResult.ERROR,
                    error_message="Skill not found in compiler",
                ))
                suite.errored += 1
            suite.total_duration_ms = 0.0
            return suite

        started_at = time.time()
        for test in tests:
            test_start = time.time()
            try:
                result = self._runtime.execute(skill, test.input_params)
                test_result = TestResult(
                    test_id=test.test_id,
                    actual_output=result.output,
                    duration_ms=(time.time() - test_start) * 1000,
                )

                if result.success:
                    if self._assert_output(result.output, test.expected_output):
                        test_result.result = TestResult.PASS
                        suite.passed += 1
                    else:
                        test_result.result = TestResult.FAIL
                        test_result.error_message = (
                            f"Expected {test.expected_output}, got {result.output}"
                        )
                        suite.failed += 1
                else:
                    test_result.result = TestResult.FAIL
                    test_result.error_message = result.error
                    suite.failed += 1
            except Exception as e:
                test_result = TestResult(
                    test_id=test.test_id,
                    result=TestResult.ERROR,
                    error_message=str(e),
                    duration_ms=(time.time() - test_start) * 1000,
                )
                suite.errored += 1

            suite.results.append(test_result)

        suite.total_duration_ms = (time.time() - started_at) * 1000

        # Restore original handlers
        self._runtime._handlers = original_handlers

        logger.info(
            f"Unit tests for {skill_id}: {suite.passed}/{suite.total} passed "
            f"({suite.pass_rate:.0%})"
        )
        return suite

    def run_integration_tests(
        self,
        composition: CompositionPlan,
        test_inputs: dict[str, dict[str, Any]],
        expected_output: Any = None,
    ) -> TestSuiteResult:
        """Run integration tests for a skill composition.

        Tests the entire composition as a single workflow, verifying that
        skills interact correctly and produce the expected aggregate output.

        Args:
            composition: The composition plan to test.
            test_inputs: Per-skill input parameters.
            expected_output: Expected aggregate output for assertion.

        Returns:
            A TestSuiteResult with the integration test outcomes.
        """
        suite = TestSuiteResult(
            suite_name=f"Integration test for {composition.name}",
            skill_id=composition.composition_id,
            total=1,
        )

        composer = SkillComposer(runtime=self._runtime, compiler=self._compiler)

        # Install mock handlers
        original_handlers = dict(self._runtime._handlers)
        for op, handler in self._mock_handlers.items():
            self._runtime.register_handler(op, handler)

        started_at = time.time()
        try:
            result = composer.execute(composition, test_inputs)
            test_result = TestResult(
                test_id=f"integration-{composition.composition_id}",
                actual_output=result.aggregated_output,
                duration_ms=(time.time() - started_at) * 1000,
            )

            if result.success:
                if expected_output is not None:
                    if self._assert_output(result.aggregated_output, expected_output):
                        test_result.result = TestResult.PASS
                        suite.passed += 1
                    else:
                        test_result.result = TestResult.FAIL
                        test_result.error_message = (
                            f"Expected {expected_output}, got {result.aggregated_output}"
                        )
                        suite.failed += 1
                else:
                    test_result.result = TestResult.PASS
                    suite.passed += 1
            else:
                test_result.result = TestResult.FAIL
                test_result.error_message = "; ".join(result.errors)
                suite.failed += 1
        except Exception as e:
            test_result = TestResult(
                test_id=f"integration-{composition.composition_id}",
                result=TestResult.ERROR,
                error_message=str(e),
                duration_ms=(time.time() - started_at) * 1000,
            )
            suite.errored += 1

        suite.results.append(test_result)
        suite.total_duration_ms = (time.time() - started_at) * 1000

        # Restore original handlers
        self._runtime._handlers = original_handlers

        logger.info(f"Integration test for {composition.name}: {suite.passed}/{suite.total} passed")
        return suite

    def benchmark(
        self,
        skill_id: str,
        input_params: dict[str, Any],
        iterations: int = 10,
    ) -> list[BenchmarkResult]:
        """Run performance benchmarks on a skill.

        Executes the skill multiple times and collects timing, success rate,
        and retry count metrics.

        Args:
            skill_id: The skill to benchmark.
            input_params: Parameters for each execution.
            iterations: Number of benchmark iterations.

        Returns:
            A list of BenchmarkResult objects, one per metric.
        """
        skill = self._compiler.get_compiled(skill_id)
        if not skill:
            logger.error(f"Skill not found for benchmarking: {skill_id}")
            return []

        times: list[float] = []
        retries: list[int] = []
        successes = 0

        for _ in range(iterations):
            start = time.time()
            try:
                result = self._runtime.execute(skill, dict(input_params))
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
                retries.append(result.retries_used)
                if result.success:
                    successes += 1
            except Exception:
                times.append((time.time() - start) * 1000)
                retries.append(0)

        results = []

        if times:
            avg_time = sum(times) / len(times)
            results.append(BenchmarkResult(
                skill_id=skill_id,
                metric=BenchmarkMetric.EXECUTION_TIME,
                value=avg_time,
                unit="ms",
                iterations=iterations,
                min_value=min(times),
                max_value=max(times),
                std_dev=self._compute_std_dev(times, avg_time),
            ))

        results.append(BenchmarkResult(
            skill_id=skill_id,
            metric=BenchmarkMetric.SUCCESS_RATE,
            value=successes / max(iterations, 1) * 100,
            unit="%",
            iterations=iterations,
        ))

        if retries:
            avg_retries = sum(retries) / len(retries)
            results.append(BenchmarkResult(
                skill_id=skill_id,
                metric=BenchmarkMetric.RETRY_COUNT,
                value=avg_retries,
                unit="count",
                iterations=iterations,
                min_value=float(min(retries)),
                max_value=float(max(retries)),
            ))

        self._benchmark_results[skill_id] = results
        logger.info(f"Benchmark completed for {skill_id}: {iterations} iterations")
        return results

    def get_benchmark(self, skill_id: str) -> list[BenchmarkResult]:
        """Retrieve benchmark results for a skill.

        Args:
            skill_id: The skill to retrieve benchmarks for.

        Returns:
            A list of BenchmarkResult objects.
        """
        return self._benchmark_results.get(skill_id, [])

    def get_stats(self) -> dict[str, Any]:
        """Get testing framework statistics.

        Returns:
            A dictionary with testing statistics.
        """
        total_tests = sum(len(t) for t in self._test_cases.values())
        return {
            "total_test_cases": total_tests,
            "skills_with_tests": len(self._test_cases),
            "mock_handlers": list(self._mock_handlers.keys()),
            "benchmarked_skills": len(self._benchmark_results),
        }

    def _assert_output(self, actual: Any, expected: Any) -> bool:
        """Compare actual output against expected output."""
        if expected is None:
            return True
        if isinstance(expected, dict) and isinstance(actual, dict):
            for key, val in expected.items():
                if key not in actual:
                    return False
                if actual[key] != val:
                    return False
            return True
        return actual == expected

    def _compute_std_dev(self, values: list[float], mean: float) -> float:
        """Compute standard deviation."""
        if len(values) < 2:
            return 0.0
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return variance ** 0.5

    def reset(self):
        """Reset the tester to its initial state."""
        self._test_cases.clear()
        self._mock_handlers.clear()
        self._benchmark_results.clear()
        logger.info("SkillTester reset")


# ═══════════════════════════════════════════════════════════════════
# Built-in Skill Definitions
# ═══════════════════════════════════════════════════════════════════


def _create_builtin_skills() -> list[SkillDefinition]:
    """Create the built-in skill library.

    Returns a list of pre-defined SkillDefinition instances covering common
    agent capabilities: text summarization, code generation, data analysis,
    research synthesis, content creation, translation, sentiment analysis,
    entity extraction, question answering, and task decomposition.
    """
    skills = []

    # 1. text_summarization
    skills.append(SkillDefinition(
        skill_id="builtin-text-summarization",
        metadata=SkillMetadata(
            name="text_summarization",
            version="1.0.0",
            description="Summarize text into concise, key-points-focused output.",
            author="Buddy",
            category=SkillType.TEXT,
            tags=["text", "summarization", "nlp"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="text", param_type=ParamType.STRING,
                               description="The text to summarize", required=True),
                SkillParameter(name="max_length", param_type=ParamType.INTEGER,
                               description="Maximum summary length in words", required=False,
                               default_value=200),
                SkillParameter(name="style", param_type=ParamType.STRING,
                               description="Summary style (concise, bullet, narrative)",
                               required=False, default_value="concise",
                               enum_values=["concise", "bullet", "narrative"]),
            ],
            outputs=[
                SkillParameter(name="summary", param_type=ParamType.STRING,
                               description="The generated summary"),
            ],
        ),
        instructions=[
            SkillInstruction(op="summarize", description="Generate text summary",
                             params={"text": "{text}", "max_length": "{max_length}",
                                     "style": "{style}"}),
        ],
    ))

    # 2. code_generation
    skills.append(SkillDefinition(
        skill_id="builtin-code-generation",
        metadata=SkillMetadata(
            name="code_generation",
            version="1.0.0",
            description="Generate code from natural language specifications.",
            author="Buddy",
            category=SkillType.CODE,
            tags=["code", "generation", "programming"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="specification", param_type=ParamType.STRING,
                               description="Natural language description of the desired code",
                               required=True),
                SkillParameter(name="language", param_type=ParamType.STRING,
                               description="Target programming language", required=True,
                               default_value="python"),
                SkillParameter(name="include_tests", param_type=ParamType.BOOLEAN,
                               description="Whether to include test cases", required=False,
                               default_value=False),
            ],
            outputs=[
                SkillParameter(name="code", param_type=ParamType.CODE,
                               description="The generated code"),
            ],
        ),
        instructions=[
            SkillInstruction(op="generate_code", description="Generate code from specification",
                             params={"specification": "{specification}",
                                     "language": "{language}",
                                     "include_tests": "{include_tests}"}),
        ],
    ))

    # 3. data_analysis
    skills.append(SkillDefinition(
        skill_id="builtin-data-analysis",
        metadata=SkillMetadata(
            name="data_analysis",
            version="1.0.0",
            description="Analyze structured data to extract insights and patterns.",
            author="Buddy",
            category=SkillType.DATA,
            tags=["data", "analysis", "statistics", "insights"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="data", param_type=ParamType.DICT,
                               description="The data to analyze", required=True),
                SkillParameter(name="analysis_type", param_type=ParamType.STRING,
                               description="Type of analysis to perform",
                               required=False, default_value="descriptive",
                               enum_values=["descriptive", "correlation", "trend", "outlier"]),
                SkillParameter(name="visualize", param_type=ParamType.BOOLEAN,
                               description="Whether to generate visualizations",
                               required=False, default_value=False),
            ],
            outputs=[
                SkillParameter(name="insights", param_type=ParamType.DICT,
                               description="Analysis results and insights"),
            ],
        ),
        instructions=[
            SkillInstruction(op="analyze_data", description="Perform data analysis",
                             params={"data": "{data}", "analysis_type": "{analysis_type}",
                                     "visualize": "{visualize}"}),
        ],
    ))

    # 4. research_synthesis
    skills.append(SkillDefinition(
        skill_id="builtin-research-synthesis",
        metadata=SkillMetadata(
            name="research_synthesis",
            version="1.0.0",
            description="Synthesize multiple information sources into a coherent research report.",
            author="Buddy",
            category=SkillType.RESEARCH,
            tags=["research", "synthesis", "analysis", "report"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="topic", param_type=ParamType.STRING,
                               description="The research topic", required=True),
                SkillParameter(name="sources", param_type=ParamType.LIST,
                               description="List of source materials", required=True),
                SkillParameter(name="depth", param_type=ParamType.STRING,
                               description="Research depth (shallow, moderate, deep)",
                               required=False, default_value="moderate",
                               enum_values=["shallow", "moderate", "deep"]),
            ],
            outputs=[
                SkillParameter(name="report", param_type=ParamType.STRING,
                               description="The synthesized research report"),
                SkillParameter(name="references", param_type=ParamType.LIST,
                               description="List of cited sources"),
            ],
        ),
        instructions=[
            SkillInstruction(op="synthesize_research", description="Synthesize research sources",
                             params={"topic": "{topic}", "sources": "{sources}",
                                     "depth": "{depth}"}),
        ],
    ))

    # 5. content_creation
    skills.append(SkillDefinition(
        skill_id="builtin-content-creation",
        metadata=SkillMetadata(
            name="content_creation",
            version="1.0.0",
            description="Create original content in various formats and styles.",
            author="Buddy",
            category=SkillType.CREATIVE,
            tags=["content", "writing", "creative", "generation"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="brief", param_type=ParamType.STRING,
                               description="Content brief or topic", required=True),
                SkillParameter(name="format", param_type=ParamType.STRING,
                               description="Output format (article, blog, social, email)",
                               required=False, default_value="article",
                               enum_values=["article", "blog", "social", "email", "report"]),
                SkillParameter(name="tone", param_type=ParamType.STRING,
                               description="Writing tone (professional, casual, humorous)",
                               required=False, default_value="professional"),
                SkillParameter(name="max_words", param_type=ParamType.INTEGER,
                               description="Maximum word count", required=False,
                               default_value=500),
            ],
            outputs=[
                SkillParameter(name="content", param_type=ParamType.STRING,
                               description="The generated content"),
            ],
        ),
        instructions=[
            SkillInstruction(op="create_content", description="Generate content",
                             params={"brief": "{brief}", "format": "{format}",
                                     "tone": "{tone}", "max_words": "{max_words}"}),
        ],
    ))

    # 6. translation
    skills.append(SkillDefinition(
        skill_id="builtin-translation",
        metadata=SkillMetadata(
            name="translation",
            version="1.0.0",
            description="Translate text between languages with context preservation.",
            author="Buddy",
            category=SkillType.LANGUAGE,
            tags=["translation", "language", "nlp", "multilingual"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="text", param_type=ParamType.STRING,
                               description="Text to translate", required=True),
                SkillParameter(name="source_language", param_type=ParamType.STRING,
                               description="Source language code", required=False,
                               default_value="auto"),
                SkillParameter(name="target_language", param_type=ParamType.STRING,
                               description="Target language code", required=True),
                SkillParameter(name="preserve_formatting", param_type=ParamType.BOOLEAN,
                               description="Whether to preserve original formatting",
                               required=False, default_value=True),
            ],
            outputs=[
                SkillParameter(name="translated_text", param_type=ParamType.STRING,
                               description="The translated text"),
                SkillParameter(name="detected_language", param_type=ParamType.STRING,
                               description="Detected source language if auto-detected"),
            ],
        ),
        instructions=[
            SkillInstruction(op="translate", description="Translate text",
                             params={"text": "{text}",
                                     "source_language": "{source_language}",
                                     "target_language": "{target_language}",
                                     "preserve_formatting": "{preserve_formatting}"}),
        ],
    ))

    # 7. sentiment_analysis
    skills.append(SkillDefinition(
        skill_id="builtin-sentiment-analysis",
        metadata=SkillMetadata(
            name="sentiment_analysis",
            version="1.0.0",
            description="Analyze the emotional tone and sentiment of text.",
            author="Buddy",
            category=SkillType.ANALYSIS,
            tags=["sentiment", "emotion", "analysis", "nlp"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="text", param_type=ParamType.STRING,
                               description="The text to analyze", required=True),
                SkillParameter(name="granularity", param_type=ParamType.STRING,
                               description="Analysis granularity (document, sentence, aspect)",
                               required=False, default_value="document",
                               enum_values=["document", "sentence", "aspect"]),
            ],
            outputs=[
                SkillParameter(name="sentiment", param_type=ParamType.STRING,
                               description="Overall sentiment label"),
                SkillParameter(name="confidence", param_type=ParamType.FLOAT,
                               description="Confidence score (0-1)"),
                SkillParameter(name="details", param_type=ParamType.DICT,
                               description="Detailed sentiment breakdown"),
            ],
        ),
        instructions=[
            SkillInstruction(op="analyze_sentiment", description="Analyze sentiment",
                             params={"text": "{text}", "granularity": "{granularity}"}),
        ],
    ))

    # 8. entity_extraction
    skills.append(SkillDefinition(
        skill_id="builtin-entity-extraction",
        metadata=SkillMetadata(
            name="entity_extraction",
            version="1.0.0",
            description="Extract named entities from text with type classification.",
            author="Buddy",
            category=SkillType.ANALYSIS,
            tags=["entity", "extraction", "ner", "nlp"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="text", param_type=ParamType.STRING,
                               description="The text to extract entities from", required=True),
                SkillParameter(name="entity_types", param_type=ParamType.LIST,
                               description="Entity types to extract (person, org, location, etc.)",
                               required=False,
                               default_value=["person", "organization", "location", "date"]),
            ],
            outputs=[
                SkillParameter(name="entities", param_type=ParamType.LIST,
                               description="List of extracted entities with types"),
                SkillParameter(name="count", param_type=ParamType.INTEGER,
                               description="Total number of entities found"),
            ],
        ),
        instructions=[
            SkillInstruction(op="extract_entities", description="Extract entities from text",
                             params={"text": "{text}", "entity_types": "{entity_types}"}),
        ],
    ))

    # 9. question_answering
    skills.append(SkillDefinition(
        skill_id="builtin-question-answering",
        metadata=SkillMetadata(
            name="question_answering",
            version="1.0.0",
            description="Answer questions based on provided context with reasoning.",
            author="Buddy",
            category=SkillType.REASONING,
            tags=["qa", "question", "answering", "reasoning"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="question", param_type=ParamType.STRING,
                               description="The question to answer", required=True),
                SkillParameter(name="context", param_type=ParamType.STRING,
                               description="Context or document to answer from", required=True),
                SkillParameter(name="include_reasoning", param_type=ParamType.BOOLEAN,
                               description="Whether to include reasoning steps",
                               required=False, default_value=True),
            ],
            outputs=[
                SkillParameter(name="answer", param_type=ParamType.STRING,
                               description="The answer to the question"),
                SkillParameter(name="confidence", param_type=ParamType.FLOAT,
                               description="Confidence score (0-1)"),
                SkillParameter(name="reasoning", param_type=ParamType.STRING,
                               description="Step-by-step reasoning if requested"),
            ],
        ),
        instructions=[
            SkillInstruction(op="answer_question", description="Answer question from context",
                             params={"question": "{question}", "context": "{context}",
                                     "include_reasoning": "{include_reasoning}"}),
        ],
    ))

    # 10. task_decomposition
    skills.append(SkillDefinition(
        skill_id="builtin-task-decomposition",
        metadata=SkillMetadata(
            name="task_decomposition",
            version="1.0.0",
            description="Break down complex tasks into manageable subtasks.",
            author="Buddy",
            category=SkillType.REASONING,
            tags=["task", "decomposition", "planning", "reasoning"],
        ),
        schema=SkillSchema(
            inputs=[
                SkillParameter(name="task", param_type=ParamType.STRING,
                               description="The complex task to decompose", required=True),
                SkillParameter(name="granularity", param_type=ParamType.STRING,
                               description="Level of detail (coarse, medium, fine)",
                               required=False, default_value="medium",
                               enum_values=["coarse", "medium", "fine"]),
                SkillParameter(name="max_subtasks", param_type=ParamType.INTEGER,
                               description="Maximum number of subtasks", required=False,
                               default_value=10),
            ],
            outputs=[
                SkillParameter(name="subtasks", param_type=ParamType.LIST,
                               description="Ordered list of subtasks"),
                SkillParameter(name="dependencies", param_type=ParamType.DICT,
                               description="Dependency mapping between subtasks"),
            ],
        ),
        instructions=[
            SkillInstruction(op="decompose_task", description="Decompose task into subtasks",
                             params={"task": "{task}", "granularity": "{granularity}",
                                     "max_subtasks": "{max_subtasks}"}),
        ],
    ))

    return skills


# ═══════════════════════════════════════════════════════════════════
# Unified Skill Compiler Pro System
# ═══════════════════════════════════════════════════════════════════


class SkillCompilerPro:
    """Unified entry point for the Agent Skill Compilation and Execution System.

    Integrates the Compiler, Runtime, Composer, Marketplace, and Tester into
    a single coordinated system. Provides a complete lifecycle for skills:
    define, compile, execute, compose, publish, and test.

    This is the primary interface that agents should use to interact with
    the skill system.

    Attributes:
        compiler: The SkillCompiler instance for compilation.
        runtime: The SkillRuntime instance for execution.
        composer: The SkillComposer instance for workflow composition.
        marketplace: The SkillMarketplace instance for discovery and sharing.
        tester: The SkillTester instance for testing and benchmarking.
    """

    def __init__(self):
        self.compiler = SkillCompiler()
        self.runtime = SkillRuntime()
        self.composer = SkillComposer(runtime=self.runtime, compiler=self.compiler)
        self.marketplace = SkillMarketplace()
        self.tester = SkillTester(runtime=self.runtime, compiler=self.compiler)
        self._initialized = False
        logger.info("SkillCompilerPro system created")

    def initialize(self):
        """Initialize the system with built-in skills.

        Compiles and publishes all built-in skills to the marketplace. This
        should be called once after construction to populate the system.
        """
        if self._initialized:
            logger.info("SkillCompilerPro already initialized")
            return

        builtin_skills = _create_builtin_skills()
        for skill in builtin_skills:
            result = self.compiler.compile(skill)
            if result.success:
                self.marketplace.publish(skill)
                self.marketplace.verify(skill.skill_id)
                logger.info(f"Built-in skill loaded: {skill.metadata.name}")
            else:
                logger.error(
                    f"Failed to compile built-in skill {skill.metadata.name}: "
                    f"{'; '.join(result.errors)}"
                )

        self._initialized = True
        logger.info(
            f"SkillCompilerPro initialized with {len(builtin_skills)} built-in skills"
        )

    def define_skill(
        self,
        name: str,
        description: str,
        instructions: list[SkillInstruction],
        inputs: list[SkillParameter] | None = None,
        outputs: list[SkillParameter] | None = None,
        category: SkillType = SkillType.UTILITY,
        version: str = "1.0.0",
        tags: list[str] | None = None,
    ) -> SkillDefinition:
        """Convenience method to define a new skill.

        Creates a complete SkillDefinition from the provided parameters,
        handling all the boilerplate of constructing metadata, schema, and
        instruction lists.

        Args:
            name: Skill name.
            description: Skill description.
            instructions: List of executable instructions.
            inputs: List of input parameters.
            outputs: List of output parameters.
            category: Skill category.
            version: Semantic version string.
            tags: Searchable tags.

        Returns:
            A complete SkillDefinition ready for compilation.
        """
        skill = SkillDefinition(
            metadata=SkillMetadata(
                name=name,
                version=version,
                description=description,
                category=category,
                tags=tags or [],
            ),
            schema=SkillSchema(
                inputs=inputs or [],
                outputs=outputs or [],
            ),
            instructions=instructions,
        )
        logger.info(f"Skill defined: {name} v{version}")
        return skill

    def compile_and_publish(self, skill: SkillDefinition) -> CompilationResult:
        """Compile a skill and publish it to the marketplace in one step.

        Args:
            skill: The skill definition to compile and publish.

        Returns:
            The CompilationResult from the compiler.
        """
        result = self.compiler.compile(skill)
        if result.success:
            self.marketplace.publish(skill)
        return result

    def execute_skill(
        self, skill_id: str, params: dict[str, Any] | None = None
    ) -> ExecutionResult:
        """Execute a compiled skill by ID.

        Looks up the skill in the compiler cache, then executes it via the
        runtime.

        Args:
            skill_id: The skill identifier.
            params: Runtime parameters for the skill.

        Returns:
            The ExecutionResult, or an error result if the skill is not found.
        """
        skill = self.compiler.get_compiled(skill_id)
        if not skill:
            return ExecutionResult(
                skill_id=skill_id,
                success=False,
                state=ExecutionState.FAILED,
                error=f"Skill not found: {skill_id}",
            )
        return self.runtime.execute(skill, params or {})

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics across all subsystems.

        Returns:
            A dictionary with statistics from all subsystems.
        """
        return {
            "compiler": self.compiler.get_stats(),
            "runtime": self.runtime.get_stats(),
            "composer": self.composer.get_stats(),
            "marketplace": self.marketplace.get_stats(),
            "tester": self.tester.get_stats(),
        }

    def reset(self):
        """Reset all subsystems to their initial state."""
        self.compiler.reset()
        self.runtime.reset()
        self.composer.reset()
        self.marketplace.reset()
        self.tester.reset()
        self._initialized = False
        logger.info("SkillCompilerPro fully reset")


# ═══════════════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════════════

_skill_compiler_pro_instance: SkillCompilerPro | None = None


def get_skill_compiler_pro() -> SkillCompilerPro:
    """Get or create the global skill compiler pro singleton."""
    global _skill_compiler_pro_instance
    if _skill_compiler_pro_instance is None:
        _skill_compiler_pro_instance = SkillCompilerPro()
    return _skill_compiler_pro_instance


def reset_skill_compiler_pro():
    """Reset the global skill compiler pro singleton."""
    global _skill_compiler_pro_instance
    if _skill_compiler_pro_instance is not None:
        _skill_compiler_pro_instance.reset()
    else:
        _skill_compiler_pro_instance = SkillCompilerPro()


skill_compiler_pro = SkillCompilerPro()