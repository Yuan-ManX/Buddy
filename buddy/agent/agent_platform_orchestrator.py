"""Buddy AI-Native Platform Orchestration Core

Provides the central orchestration layer for the entire AI-native platform,
coordinating services, workflows, integrations, publishing, analytics, and
multi-tenant workspaces. Acts as the operating system of the Buddy ecosystem.

Modules:
    - Platform Service Registry: registration, discovery, health monitoring, versioning
    - Workflow Automation Engine: define, execute, monitor automated workflows
    - Integration Hub: external service connections, webhooks, credentials, rate limiting
    - Publishing Pipeline: content publishing workflow, multi-channel distribution
    - Analytics Dashboard: metrics, usage analytics, performance monitoring, cost tracking
    - Multi-Tenant Workspace: isolated workspaces, RBAC, cross-workspace collaboration
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.platform_orchestrator")

# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════


class ServiceType(str, Enum):
    """Types of platform services that can be registered."""
    AGENT = "agent"
    TOOL = "tool"
    SKILL = "skill"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"
    GATEWAY = "gateway"
    SCHEDULER = "scheduler"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    CUSTOM = "custom"


class ServiceHealth(str, Enum):
    """Health status of a registered platform service."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


class WorkflowState(str, Enum):
    """Execution states of a workflow."""
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TriggerType(str, Enum):
    """Types of triggers that can initiate workflow execution."""
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"
    CONDITIONAL = "conditional"
    MANUAL = "manual"
    WEBHOOK = "webhook"
    API_CALL = "api_call"
    SYSTEM_EVENT = "system_event"


class StepExecutionMode(str, Enum):
    """Execution mode for workflow steps."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    FAN_OUT = "fan_out"
    FAN_IN = "fan_in"


class IntegrationStatus(str, Enum):
    """Connection status of an integration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class CredentialType(str, Enum):
    """Types of credentials supported for integrations."""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    CUSTOM = "custom"


class PublishingState(str, Enum):
    """States in the content publishing pipeline."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    ARCHIVED = "archived"


class DistributionChannel(str, Enum):
    """Channels for content distribution."""
    API = "api"
    WEB = "web"
    EMAIL = "email"
    NOTIFICATION = "notification"
    SLACK = "slack"
    WEBHOOK = "webhook"
    RPC = "rpc"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """Types of platform metrics collected."""
    REQUEST_COUNT = "request_count"
    LATENCY_MS = "latency_ms"
    ERROR_COUNT = "error_count"
    TOKEN_USAGE = "token_usage"
    API_CALL_COUNT = "api_call_count"
    SESSION_COUNT = "session_count"
    WORKFLOW_COUNT = "workflow_count"
    PUBLISHING_COUNT = "publishing_count"
    USER_COUNT = "user_count"
    COST_USD = "cost_usd"


class AlertSeverity(str, Enum):
    """Severity levels for platform alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class WorkspaceRole(str, Enum):
    """Roles within a multi-tenant workspace."""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    CUSTOM = "custom"


class CollaborationMode(str, Enum):
    """Modes of collaboration between workspaces."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    SHARED_EXECUTION = "shared_execution"
    FEDERATED = "federated"


# ═══════════════════════════════════════════════════════════════
# Data Classes — Platform Service Registry
# ═══════════════════════════════════════════════════════════════


@dataclass
class ServiceVersion:
    """Semantic version information for a registered service.

    Attributes:
        major: Major version number (breaking changes).
        minor: Minor version number (backward-compatible features).
        patch: Patch version number (bug fixes).
        label: Optional pre-release label (e.g. "alpha", "beta").
    """
    major: int = 1
    minor: int = 0
    patch: int = 0
    label: str = ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.label}" if self.label else base

    def to_dict(self) -> dict[str, Any]:
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "label": self.label,
            "version_string": str(self),
        }

    def is_compatible_with(self, other: "ServiceVersion") -> bool:
        """Check if this version is backward-compatible with another."""
        return self.major == other.major and self.minor >= other.minor


@dataclass
class ServiceHeartbeat:
    """Heartbeat record for a registered service.

    Attributes:
        service_id: The service this heartbeat belongs to.
        timestamp: When the heartbeat was received.
        cpu_usage: CPU usage percentage at time of heartbeat.
        memory_usage_mb: Memory usage in MB at time of heartbeat.
        active_connections: Number of active connections.
        custom_metrics: Arbitrary additional metrics.
    """
    service_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    active_connections: int = 0
    custom_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "timestamp": self.timestamp,
            "cpu_usage": round(self.cpu_usage, 2),
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "active_connections": self.active_connections,
            "custom_metrics": self.custom_metrics,
        }


@dataclass
class ServiceRegistration:
    """A registered service in the platform service registry.

    Attributes:
        service_id: Unique identifier for the service.
        service_name: Human-readable name.
        service_type: Category of service.
        version: Semantic version of the service.
        host: Network host where the service runs.
        port: Network port.
        health_endpoint: Endpoint for health checks.
        dependencies: Service IDs this service depends on.
        metadata: Arbitrary key-value metadata.
        registered_at: ISO timestamp of registration.
        last_heartbeat: ISO timestamp of last heartbeat.
        health: Current health status.
        is_active: Whether the service is currently active.
        heartbeat_history: Recent heartbeat records.
        tags: Searchable tags for service discovery.
    """
    service_id: str = field(default_factory=lambda: f"svc-{uuid.uuid4().hex[:8]}")
    service_name: str = ""
    service_type: ServiceType = ServiceType.CUSTOM
    version: ServiceVersion = field(default_factory=ServiceVersion)
    host: str = ""
    port: int = 0
    health_endpoint: str = ""
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    health: ServiceHealth = ServiceHealth.UNKNOWN
    is_active: bool = True
    heartbeat_history: list[ServiceHeartbeat] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_type": self.service_type.value,
            "version": self.version.to_dict(),
            "host": self.host,
            "port": self.port,
            "health_endpoint": self.health_endpoint,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "health": self.health.value,
            "is_active": self.is_active,
            "tags": self.tags,
            "heartbeat_count": len(self.heartbeat_history),
        }


# ═══════════════════════════════════════════════════════════════
# Data Classes — Workflow Automation Engine
# ═══════════════════════════════════════════════════════════════


@dataclass
class WorkflowTrigger:
    """Trigger configuration for workflow execution.

    Attributes:
        trigger_id: Unique identifier for the trigger.
        trigger_type: Type of trigger.
        schedule: Cron expression for scheduled triggers.
        event_pattern: Pattern to match for event-driven triggers.
        condition_expression: Boolean expression for conditional triggers.
        source: Source identifier for the trigger (e.g. webhook URL, system event).
        is_enabled: Whether the trigger is currently active.
        last_fired_at: ISO timestamp of the last trigger activation.
        metadata: Arbitrary key-value metadata.
    """
    trigger_id: str = field(default_factory=lambda: f"trig-{uuid.uuid4().hex[:8]}")
    trigger_type: TriggerType = TriggerType.MANUAL
    schedule: str = ""
    event_pattern: str = ""
    condition_expression: str = ""
    source: str = ""
    is_enabled: bool = True
    last_fired_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "trigger_type": self.trigger_type.value,
            "schedule": self.schedule,
            "event_pattern": self.event_pattern,
            "condition_expression": self.condition_expression,
            "source": self.source,
            "is_enabled": self.is_enabled,
            "last_fired_at": self.last_fired_at,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowStep:
    """A single step within a workflow definition.

    Attributes:
        step_id: Unique identifier for this step.
        step_name: Human-readable name.
        description: What this step does.
        execution_mode: How this step executes relative to siblings.
        depends_on: Step IDs that must complete before this step runs.
        action: The action to perform (function name, service call, etc.).
        action_params: Parameters for the action.
        timeout_seconds: Maximum execution time before timeout.
        retry_count: Number of retries on failure.
        retry_delay_seconds: Delay between retries.
        on_failure: Behavior on failure ("abort", "skip", "continue").
        result: Output of the step after execution.
        metadata: Arbitrary key-value metadata.
    """
    step_id: str = field(default_factory=lambda: f"step-{uuid.uuid4().hex[:8]}")
    step_name: str = ""
    description: str = ""
    execution_mode: StepExecutionMode = StepExecutionMode.SEQUENTIAL
    depends_on: list[str] = field(default_factory=list)
    action: str = ""
    action_params: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_delay_seconds: int = 5
    on_failure: str = "abort"
    result: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "description": self.description,
            "execution_mode": self.execution_mode.value,
            "depends_on": self.depends_on,
            "action": self.action,
            "action_params": self.action_params,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "on_failure": self.on_failure,
            "result": self.result,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowDefinition:
    """Definition of an automated workflow.

    Attributes:
        workflow_id: Unique identifier for the workflow.
        workflow_name: Human-readable name.
        description: What the workflow accomplishes.
        steps: Ordered list of workflow steps.
        triggers: Triggers that initiate this workflow.
        version: Workflow version string.
        timeout_seconds: Global timeout for the entire workflow.
        tags: Searchable tags.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
        metadata: Arbitrary key-value metadata.
    """
    workflow_id: str = field(default_factory=lambda: f"wf-{uuid.uuid4().hex[:8]}")
    workflow_name: str = ""
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    triggers: list[WorkflowTrigger] = field(default_factory=list)
    version: str = "1.0.0"
    timeout_seconds: int = 3600
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "triggers": [t.to_dict() for t in self.triggers],
            "version": self.version,
            "timeout_seconds": self.timeout_seconds,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "step_count": len(self.steps),
        }


@dataclass
class WorkflowExecution:
    """A single execution instance of a workflow.

    Attributes:
        execution_id: Unique identifier for this execution.
        workflow_id: The workflow being executed.
        workflow_name: Name of the workflow (denormalized for convenience).
        state: Current execution state.
        trigger_type: What triggered this execution.
        started_at: ISO timestamp of execution start.
        completed_at: ISO timestamp of execution completion.
        step_results: Results of each step by step_id.
        current_step_id: Currently executing step, if any.
        error_message: Error message if the workflow failed.
        retry_attempt: Current retry attempt number.
        parameters: Parameter overrides for this execution.
        metadata: Arbitrary key-value metadata.
        execution_log: Chronological log entries for this execution.
    """
    execution_id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}")
    workflow_id: str = ""
    workflow_name: str = ""
    state: WorkflowState = WorkflowState.PENDING
    trigger_type: TriggerType = TriggerType.MANUAL
    started_at: str = ""
    completed_at: str = ""
    step_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    current_step_id: str = ""
    error_message: str = ""
    retry_attempt: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "state": self.state.value,
            "trigger_type": self.trigger_type.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "step_results": self.step_results,
            "current_step_id": self.current_step_id,
            "error_message": self.error_message[:500],
            "retry_attempt": self.retry_attempt,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "log_entry_count": len(self.execution_log),
        }


@dataclass
class WorkflowTemplate:
    """A parameterized workflow template for reusable workflow patterns.

    Attributes:
        template_id: Unique identifier for the template.
        template_name: Human-readable name.
        description: What the template represents.
        base_workflow: The underlying workflow definition.
        parameters: Parameter definitions (name -> type/default).
        category: Grouping category for the template.
        tags: Searchable tags.
        usage_count: How many times this template has been instantiated.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
        metadata: Arbitrary key-value metadata.
    """
    template_id: str = field(default_factory=lambda: f"tmpl-{uuid.uuid4().hex[:8]}")
    template_name: str = ""
    description: str = ""
    base_workflow: WorkflowDefinition = field(default_factory=WorkflowDefinition)
    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)
    category: str = ""
    tags: list[str] = field(default_factory=list)
    usage_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "description": self.description,
            "base_workflow": self.base_workflow.to_dict(),
            "parameters": self.parameters,
            "category": self.category,
            "tags": self.tags,
            "usage_count": self.usage_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


# ═══════════════════════════════════════════════════════════════
# Data Classes — Integration Hub
# ═══════════════════════════════════════════════════════════════


@dataclass
class ApiKeyBundle:
    """API key credential bundle.

    Attributes:
        key_name: Name/label for the key.
        api_key: The API key value (stored securely, never logged).
        key_header: HTTP header name for the key (e.g. "X-API-Key").
        expires_at: Optional expiration timestamp.
        rotation_policy: Key rotation policy (e.g. "90d").
        last_rotated_at: When the key was last rotated.
    """
    key_name: str = ""
    api_key: str = ""
    key_header: str = "X-API-Key"
    expires_at: str = ""
    rotation_policy: str = ""
    last_rotated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_name": self.key_name,
            "key_header": self.key_header,
            "expires_at": self.expires_at,
            "rotation_policy": self.rotation_policy,
            "last_rotated_at": self.last_rotated_at,
            "has_api_key": bool(self.api_key),
        }


@dataclass
class OAuthBundle:
    """OAuth2 credential bundle.

    Attributes:
        client_id: OAuth client identifier.
        client_secret: OAuth client secret (stored securely, never logged).
        token_url: Token endpoint URL.
        authorization_url: Authorization endpoint URL.
        scopes: Requested OAuth scopes.
        access_token: Current access token (stored securely).
        refresh_token: Current refresh token (stored securely).
        token_expires_at: When the access token expires.
        redirect_uri: OAuth redirect URI.
    """
    client_id: str = ""
    client_secret: str = ""
    token_url: str = ""
    authorization_url: str = ""
    scopes: list[str] = field(default_factory=list)
    access_token: str = ""
    refresh_token: str = ""
    token_expires_at: str = ""
    redirect_uri: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "token_url": self.token_url,
            "authorization_url": self.authorization_url,
            "scopes": self.scopes,
            "token_expires_at": self.token_expires_at,
            "redirect_uri": self.redirect_uri,
            "has_client_secret": bool(self.client_secret),
            "has_access_token": bool(self.access_token),
            "has_refresh_token": bool(self.refresh_token),
        }


@dataclass
class CredentialBundle:
    """Unified credential bundle for an integration.

    Attributes:
        credential_id: Unique identifier for this credential set.
        credential_type: Type of credential mechanism.
        api_key: API key bundle (if applicable).
        oauth: OAuth bundle (if applicable).
        custom_data: Arbitrary credential data for custom types.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """
    credential_id: str = field(default_factory=lambda: f"cred-{uuid.uuid4().hex[:8]}")
    credential_type: CredentialType = CredentialType.API_KEY
    api_key: ApiKeyBundle | None = None
    oauth: OAuthBundle | None = None
    custom_data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "credential_id": self.credential_id,
            "credential_type": self.credential_type.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.api_key:
            result["api_key"] = self.api_key.to_dict()
        if self.oauth:
            result["oauth"] = self.oauth.to_dict()
        if self.custom_data:
            result["custom_data_keys"] = list(self.custom_data.keys())
        return result


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for an integration.

    Attributes:
        max_requests_per_minute: Maximum requests per minute.
        max_requests_per_hour: Maximum requests per hour.
        max_requests_per_day: Maximum requests per day.
        burst_limit: Maximum burst requests beyond the steady rate.
        cooldown_seconds: Cooldown period after hitting limits.
        current_minute_count: Requests in the current minute window.
        current_hour_count: Requests in the current hour window.
        current_day_count: Requests in the current day window.
        last_reset_minute: ISO timestamp of last minute-window reset.
        last_reset_hour: ISO timestamp of last hour-window reset.
        last_reset_day: ISO timestamp of last day-window reset.
    """
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    max_requests_per_day: int = 10000
    burst_limit: int = 10
    cooldown_seconds: int = 60
    current_minute_count: int = 0
    current_hour_count: int = 0
    current_day_count: int = 0
    last_reset_minute: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_reset_hour: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_reset_day: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_requests_per_hour": self.max_requests_per_hour,
            "max_requests_per_day": self.max_requests_per_day,
            "burst_limit": self.burst_limit,
            "cooldown_seconds": self.cooldown_seconds,
            "current_minute_count": self.current_minute_count,
            "current_hour_count": self.current_hour_count,
            "current_day_count": self.current_day_count,
            "utilization_percent": self._utilization_percent(),
        }

    def _utilization_percent(self) -> float:
        """Calculate current utilization as a percentage."""
        if self.max_requests_per_minute == 0:
            return 0.0
        return round((self.current_minute_count / self.max_requests_per_minute) * 100, 1)


@dataclass
class QuotaTracking:
    """Quota and usage tracking for an integration.

    Attributes:
        quota_id: Unique identifier for this quota.
        integration_id: The integration this quota applies to.
        total_quota: Total allowed usage.
        used_quota: Amount of quota used so far.
        quota_unit: Unit of measurement (e.g. "requests", "tokens", "bytes").
        reset_period: Reset period (e.g. "daily", "monthly", "never").
        last_reset_at: ISO timestamp of last quota reset.
        alerts_enabled: Whether to send alerts when approaching quota.
        alert_threshold_percent: Percentage threshold for quota alerts.
        metadata: Arbitrary key-value metadata.
    """
    quota_id: str = field(default_factory=lambda: f"quota-{uuid.uuid4().hex[:8]}")
    integration_id: str = ""
    total_quota: int = 0
    used_quota: int = 0
    quota_unit: str = "requests"
    reset_period: str = "monthly"
    last_reset_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    alerts_enabled: bool = True
    alert_threshold_percent: float = 80.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "quota_id": self.quota_id,
            "integration_id": self.integration_id,
            "total_quota": self.total_quota,
            "used_quota": self.used_quota,
            "quota_unit": self.quota_unit,
            "reset_period": self.reset_period,
            "last_reset_at": self.last_reset_at,
            "alerts_enabled": self.alerts_enabled,
            "alert_threshold_percent": self.alert_threshold_percent,
            "remaining_quota": self.total_quota - self.used_quota,
            "utilization_percent": self._utilization_percent(),
            "metadata": self.metadata,
        }

    def _utilization_percent(self) -> float:
        if self.total_quota == 0:
            return 0.0
        return round((self.used_quota / self.total_quota) * 100, 1)


@dataclass
class WebhookRegistration:
    """A registered webhook for inbound/outbound events.

    Attributes:
        webhook_id: Unique identifier for this webhook.
        integration_id: The integration this webhook belongs to.
        webhook_url: URL endpoint for the webhook.
        event_types: Event types this webhook listens for.
        secret: HMAC secret for webhook payload verification.
        is_active: Whether the webhook is currently enabled.
        direction: "inbound" or "outbound".
        retry_policy: Retry configuration for failed deliveries.
        last_triggered_at: ISO timestamp of last event.
        created_at: ISO timestamp of creation.
        metadata: Arbitrary key-value metadata.
    """
    webhook_id: str = field(default_factory=lambda: f"wh-{uuid.uuid4().hex[:8]}")
    integration_id: str = ""
    webhook_url: str = ""
    event_types: list[str] = field(default_factory=list)
    secret: str = ""
    is_active: bool = True
    direction: str = "inbound"
    retry_policy: dict[str, Any] = field(default_factory=dict)
    last_triggered_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "webhook_id": self.webhook_id,
            "integration_id": self.integration_id,
            "webhook_url": self.webhook_url,
            "event_types": self.event_types,
            "is_active": self.is_active,
            "direction": self.direction,
            "retry_policy": self.retry_policy,
            "last_triggered_at": self.last_triggered_at,
            "created_at": self.created_at,
            "has_secret": bool(self.secret),
            "metadata": self.metadata,
        }


@dataclass
class IntegrationConnection:
    """A connection to an external service or API.

    Attributes:
        integration_id: Unique identifier for this integration.
        integration_name: Human-readable name.
        service_url: Base URL of the external service.
        status: Current connection status.
        credential: Credential bundle for authentication.
        rate_limit: Rate limiting configuration.
        quota: Quota tracking for this integration.
        webhooks: Registered webhooks for this integration.
        connected_at: ISO timestamp of when the connection was established.
        last_used_at: ISO timestamp of last usage.
        error_count: Number of consecutive errors.
        last_error: Most recent error message.
        tags: Searchable tags.
        metadata: Arbitrary key-value metadata.
    """
    integration_id: str = field(default_factory=lambda: f"int-{uuid.uuid4().hex[:8]}")
    integration_name: str = ""
    service_url: str = ""
    status: IntegrationStatus = IntegrationStatus.DISCONNECTED
    credential: CredentialBundle | None = None
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    quota: QuotaTracking | None = None
    webhooks: list[WebhookRegistration] = field(default_factory=list)
    connected_at: str = ""
    last_used_at: str = ""
    error_count: int = 0
    last_error: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "integration_id": self.integration_id,
            "integration_name": self.integration_name,
            "service_url": self.service_url,
            "status": self.status.value,
            "rate_limit": self.rate_limit.to_dict(),
            "connected_at": self.connected_at,
            "last_used_at": self.last_used_at,
            "error_count": self.error_count,
            "last_error": self.last_error[:200],
            "tags": self.tags,
            "webhook_count": len(self.webhooks),
            "metadata": self.metadata,
        }
        if self.credential:
            result["credential"] = self.credential.to_dict()
        if self.quota:
            result["quota"] = self.quota.to_dict()
        return result


# ═══════════════════════════════════════════════════════════════
# Data Classes — Publishing Pipeline
# ═══════════════════════════════════════════════════════════════


@dataclass
class ContentVersion:
    """A specific version of published content for rollback support.

    Attributes:
        version_id: Unique identifier for this version.
        content_id: The content this version belongs to.
        version_number: Sequential version number.
        content_snapshot: Full snapshot of the content at this version.
        created_at: ISO timestamp of version creation.
        created_by: Identifier of the user/agent who created this version.
        comment: Optional comment describing the version.
    """
    version_id: str = field(default_factory=lambda: f"ver-{uuid.uuid4().hex[:8]}")
    content_id: str = ""
    version_number: int = 1
    content_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = ""
    comment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "content_id": self.content_id,
            "version_number": self.version_number,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "comment": self.comment,
            "snapshot_keys": list(self.content_snapshot.keys()),
        }


@dataclass
class PublishingSchedule:
    """Scheduling configuration for content publishing.

    Attributes:
        schedule_id: Unique identifier for this schedule.
        scheduled_at: ISO timestamp when publishing should occur.
        timezone: IANA timezone string (e.g. "America/New_York", "Asia/Shanghai").
        recurrence: Optional recurrence rule (cron expression).
        is_active: Whether the schedule is active.
        created_at: ISO timestamp of creation.
        metadata: Arbitrary key-value metadata.
    """
    schedule_id: str = field(default_factory=lambda: f"sched-{uuid.uuid4().hex[:8]}")
    scheduled_at: str = ""
    timezone: str = "UTC"
    recurrence: str = ""
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "scheduled_at": self.scheduled_at,
            "timezone": self.timezone,
            "recurrence": self.recurrence,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class DistributionTarget:
    """A target channel for content distribution.

    Attributes:
        target_id: Unique identifier for this distribution target.
        channel: Distribution channel type.
        channel_config: Channel-specific configuration.
        priority: Priority order for distribution (lower = higher priority).
        is_enabled: Whether this target is currently active.
        last_distributed_at: ISO timestamp of last distribution.
        delivery_status: Status of the last delivery.
        metadata: Arbitrary key-value metadata.
    """
    target_id: str = field(default_factory=lambda: f"dist-{uuid.uuid4().hex[:8]}")
    channel: DistributionChannel = DistributionChannel.API
    channel_config: dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    is_enabled: bool = True
    last_distributed_at: str = ""
    delivery_status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "channel": self.channel.value,
            "channel_config": self.channel_config,
            "priority": self.priority,
            "is_enabled": self.is_enabled,
            "last_distributed_at": self.last_distributed_at,
            "delivery_status": self.delivery_status,
            "metadata": self.metadata,
        }


@dataclass
class PublishingRollback:
    """Rollback record for a publishing operation.

    Attributes:
        rollback_id: Unique identifier for this rollback.
        content_id: The content that was rolled back.
        rolled_back_from_version: Version number rolled back from.
        rolled_back_to_version: Version number rolled back to.
        reason: Reason for the rollback.
        performed_at: ISO timestamp of the rollback.
        performed_by: Identifier of who performed the rollback.
        affected_channels: Distribution channels affected by the rollback.
    """
    rollback_id: str = field(default_factory=lambda: f"rb-{uuid.uuid4().hex[:8]}")
    content_id: str = ""
    rolled_back_from_version: int = 0
    rolled_back_to_version: int = 0
    reason: str = ""
    performed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    performed_by: str = ""
    affected_channels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "content_id": self.content_id,
            "rolled_back_from_version": self.rolled_back_from_version,
            "rolled_back_to_version": self.rolled_back_to_version,
            "reason": self.reason,
            "performed_at": self.performed_at,
            "performed_by": self.performed_by,
            "affected_channels": self.affected_channels,
        }


@dataclass
class PublishingContent:
    """Content item going through the publishing pipeline.

    Attributes:
        content_id: Unique identifier for this content.
        title: Content title.
        content_type: Type of content (e.g. "blog", "release", "notification").
        body: Content body or payload.
        state: Current state in the publishing pipeline.
        author: Creator of the content.
        reviewer: Assigned reviewer, if any.
        versions: Version history for rollback support.
        schedule: Publishing schedule configuration.
        distribution_targets: Target channels for distribution.
        rollback_history: Record of past rollbacks.
        tags: Searchable tags.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
        published_at: ISO timestamp of when content was published.
        metadata: Arbitrary key-value metadata.
    """
    content_id: str = field(default_factory=lambda: f"content-{uuid.uuid4().hex[:8]}")
    title: str = ""
    content_type: str = ""
    body: dict[str, Any] = field(default_factory=dict)
    state: PublishingState = PublishingState.DRAFT
    author: str = ""
    reviewer: str = ""
    versions: list[ContentVersion] = field(default_factory=list)
    schedule: PublishingSchedule | None = None
    distribution_targets: list[DistributionTarget] = field(default_factory=list)
    rollback_history: list[PublishingRollback] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    published_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_id": self.content_id,
            "title": self.title,
            "content_type": self.content_type,
            "state": self.state.value,
            "author": self.author,
            "reviewer": self.reviewer,
            "versions": [v.to_dict() for v in self.versions],
            "schedule": self.schedule.to_dict() if self.schedule else None,
            "distribution_targets": [t.to_dict() for t in self.distribution_targets],
            "rollback_history": [r.to_dict() for r in self.rollback_history],
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "published_at": self.published_at,
            "metadata": self.metadata,
            "version_count": len(self.versions),
            "rollback_count": len(self.rollback_history),
        }


# ═══════════════════════════════════════════════════════════════
# Data Classes — Analytics Dashboard
# ═══════════════════════════════════════════════════════════════


@dataclass
class PlatformMetric:
    """A single platform metric data point.

    Attributes:
        metric_id: Unique identifier for this metric entry.
        metric_type: Type of metric being recorded.
        value: Numeric value of the metric.
        unit: Unit of measurement.
        source: Source of the metric (service_id, agent_id, user_id).
        source_type: Type of source (e.g. "service", "agent", "user").
        recorded_at: ISO timestamp of when the metric was recorded.
        tags: Dimension tags for filtering/grouping.
        metadata: Arbitrary key-value metadata.
    """
    metric_id: str = field(default_factory=lambda: f"metric-{uuid.uuid4().hex[:8]}")
    metric_type: MetricType = MetricType.REQUEST_COUNT
    value: float = 0.0
    unit: str = ""
    source: str = ""
    source_type: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "source_type": self.source_type,
            "recorded_at": self.recorded_at,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class UsageRecord:
    """Aggregated usage record for a service, agent, or user.

    Attributes:
        record_id: Unique identifier for this usage record.
        subject_id: The subject being tracked (service, agent, user).
        subject_type: Type of subject.
        period_start: Start of the usage period (ISO timestamp).
        period_end: End of the usage period (ISO timestamp).
        metrics: Aggregated metric values for the period.
        total_cost_usd: Total cost in USD for the period.
        metadata: Arbitrary key-value metadata.
    """
    record_id: str = field(default_factory=lambda: f"usage-{uuid.uuid4().hex[:8]}")
    subject_id: str = ""
    subject_type: str = ""
    period_start: str = ""
    period_end: str = ""
    metrics: dict[str, float] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "metrics": self.metrics,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "metadata": self.metadata,
        }


@dataclass
class PerformanceAlert:
    """A performance-related alert generated by the analytics system.

    Attributes:
        alert_id: Unique identifier for this alert.
        alert_type: Type of alert (e.g. "latency_spike", "error_rate_high").
        severity: Severity level.
        message: Human-readable alert message.
        metric_type: The metric that triggered the alert.
        threshold: The threshold value that was breached.
        actual_value: The actual value that triggered the alert.
        source: Source that triggered the alert.
        created_at: ISO timestamp of alert creation.
        acknowledged: Whether the alert has been acknowledged.
        acknowledged_by: Who acknowledged the alert.
        resolved_at: ISO timestamp of resolution.
        metadata: Arbitrary key-value metadata.
    """
    alert_id: str = field(default_factory=lambda: f"perf-alert-{uuid.uuid4().hex[:8]}")
    alert_type: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    metric_type: MetricType = MetricType.REQUEST_COUNT
    threshold: float = 0.0
    actual_value: float = 0.0
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged: bool = False
    acknowledged_by: str = ""
    resolved_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "message": self.message,
            "metric_type": self.metric_type.value,
            "threshold": self.threshold,
            "actual_value": self.actual_value,
            "source": self.source,
            "created_at": self.created_at,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at,
            "metadata": self.metadata,
        }


@dataclass
class CostReport:
    """Cost tracking report for a time period.

    Attributes:
        report_id: Unique identifier for this cost report.
        period_start: Start of the reporting period.
        period_end: End of the reporting period.
        total_cost_usd: Total cost in USD.
        breakdown: Cost breakdown by service/agent/user.
        currency: Currency code (default USD).
        generated_at: ISO timestamp of report generation.
        metadata: Arbitrary key-value metadata.
    """
    report_id: str = field(default_factory=lambda: f"cost-{uuid.uuid4().hex[:8]}")
    period_start: str = ""
    period_end: str = ""
    total_cost_usd: float = 0.0
    breakdown: dict[str, float] = field(default_factory=dict)
    currency: str = "USD"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "breakdown": self.breakdown,
            "currency": self.currency,
            "generated_at": self.generated_at,
            "metadata": self.metadata,
        }


@dataclass
class OptimizationSuggestion:
    """A cost or performance optimization suggestion.

    Attributes:
        suggestion_id: Unique identifier for this suggestion.
        category: Suggestion category (e.g. "cost", "performance", "resource").
        description: Human-readable description of the suggestion.
        estimated_savings_usd: Estimated cost savings per month.
        impact: Expected impact level ("low", "medium", "high").
        status: Current status of the suggestion.
        source: Source of the metric that led to this suggestion.
        created_at: ISO timestamp of creation.
        implemented_at: ISO timestamp of implementation, if applied.
        metadata: Arbitrary key-value metadata.
    """
    suggestion_id: str = field(default_factory=lambda: f"sug-{uuid.uuid4().hex[:8]}")
    category: str = ""
    description: str = ""
    estimated_savings_usd: float = 0.0
    impact: str = "medium"
    status: str = "pending"
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    implemented_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "category": self.category,
            "description": self.description,
            "estimated_savings_usd": round(self.estimated_savings_usd, 4),
            "impact": self.impact,
            "status": self.status,
            "source": self.source,
            "created_at": self.created_at,
            "implemented_at": self.implemented_at,
            "metadata": self.metadata,
        }


# ═══════════════════════════════════════════════════════════════
# Data Classes — Multi-Tenant Workspace
# ═══════════════════════════════════════════════════════════════


@dataclass
class WorkspaceRoleBinding:
    """A role binding for a member within a workspace.

    Attributes:
        binding_id: Unique identifier for this binding.
        user_id: The user this binding applies to.
        workspace_id: The workspace this binding belongs to.
        role: The assigned role.
        granted_at: ISO timestamp of when the role was granted.
        granted_by: Who granted the role.
        expires_at: Optional expiration timestamp.
        custom_permissions: Additional permissions beyond the base role.
        is_active: Whether this binding is currently active.
    """
    binding_id: str = field(default_factory=lambda: f"bind-{uuid.uuid4().hex[:8]}")
    user_id: str = ""
    workspace_id: str = ""
    role: WorkspaceRole = WorkspaceRole.VIEWER
    granted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    granted_by: str = ""
    expires_at: str = ""
    custom_permissions: list[str] = field(default_factory=list)
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "role": self.role.value,
            "granted_at": self.granted_at,
            "granted_by": self.granted_by,
            "expires_at": self.expires_at,
            "custom_permissions": self.custom_permissions,
            "is_active": self.is_active,
        }


@dataclass
class WorkspaceMember:
    """A member of a workspace with role information.

    Attributes:
        user_id: Unique identifier for the user.
        display_name: Human-readable display name.
        email: User's email address.
        role: Primary role in the workspace.
        role_bindings: All role bindings for this user in the workspace.
        joined_at: ISO timestamp of when the user joined.
        last_active_at: ISO timestamp of last activity.
        metadata: Arbitrary key-value metadata.
    """
    user_id: str = ""
    display_name: str = ""
    email: str = ""
    role: WorkspaceRole = WorkspaceRole.VIEWER
    role_bindings: list[WorkspaceRoleBinding] = field(default_factory=list)
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "email": self.email,
            "role": self.role.value,
            "role_bindings": [b.to_dict() for b in self.role_bindings],
            "joined_at": self.joined_at,
            "last_active_at": self.last_active_at,
            "metadata": self.metadata,
        }


@dataclass
class SharedResource:
    """A resource shared within or across workspaces.

    Attributes:
        resource_id: Unique identifier for the shared resource.
        resource_type: Type of resource (e.g. "workflow", "template", "skill").
        resource_name: Human-readable name.
        owner_workspace_id: The workspace that owns this resource.
        shared_with: Workspace IDs this resource is shared with.
        collaboration_mode: Access mode for shared workspaces.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
        metadata: Arbitrary key-value metadata.
    """
    resource_id: str = field(default_factory=lambda: f"res-{uuid.uuid4().hex[:8]}")
    resource_type: str = ""
    resource_name: str = ""
    owner_workspace_id: str = ""
    shared_with: list[str] = field(default_factory=list)
    collaboration_mode: CollaborationMode = CollaborationMode.READ_ONLY
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "owner_workspace_id": self.owner_workspace_id,
            "shared_with": self.shared_with,
            "collaboration_mode": self.collaboration_mode.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class CrossWorkspaceCollaboration:
    """A collaboration link between two workspaces.

    Attributes:
        collaboration_id: Unique identifier for this collaboration.
        source_workspace_id: The workspace initiating the collaboration.
        target_workspace_id: The workspace being collaborated with.
        mode: Collaboration access mode.
        shared_resources: Resources shared through this collaboration.
        established_at: ISO timestamp of when collaboration was established.
        established_by: Who established the collaboration.
        is_active: Whether the collaboration is currently active.
        metadata: Arbitrary key-value metadata.
    """
    collaboration_id: str = field(default_factory=lambda: f"collab-{uuid.uuid4().hex[:8]}")
    source_workspace_id: str = ""
    target_workspace_id: str = ""
    mode: CollaborationMode = CollaborationMode.READ_ONLY
    shared_resources: list[str] = field(default_factory=list)
    established_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    established_by: str = ""
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collaboration_id": self.collaboration_id,
            "source_workspace_id": self.source_workspace_id,
            "target_workspace_id": self.target_workspace_id,
            "mode": self.mode.value,
            "shared_resources": self.shared_resources,
            "established_at": self.established_at,
            "established_by": self.established_by,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


@dataclass
class Workspace:
    """An isolated workspace for a project or team.

    Attributes:
        workspace_id: Unique identifier for the workspace.
        workspace_name: Human-readable name.
        description: Description of the workspace's purpose.
        owner_id: User ID of the workspace owner.
        members: Members of the workspace with their roles.
        shared_resources: Resources shared within this workspace.
        collaborations: Cross-workspace collaboration links.
        settings: Workspace-specific settings.
        is_active: Whether the workspace is currently active.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
        metadata: Arbitrary key-value metadata.
    """
    workspace_id: str = field(default_factory=lambda: f"ws-{uuid.uuid4().hex[:8]}")
    workspace_name: str = ""
    description: str = ""
    owner_id: str = ""
    members: list[WorkspaceMember] = field(default_factory=list)
    shared_resources: list[SharedResource] = field(default_factory=list)
    collaborations: list[CrossWorkspaceCollaboration] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "description": self.description,
            "owner_id": self.owner_id,
            "members": [m.to_dict() for m in self.members],
            "shared_resources": [r.to_dict() for r in self.shared_resources],
            "collaborations": [c.to_dict() for c in self.collaborations],
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "member_count": len(self.members),
            "resource_count": len(self.shared_resources),
            "collaboration_count": len(self.collaborations),
            "metadata": self.metadata,
            "settings": self.settings,
        }


# ═══════════════════════════════════════════════════════════════
# Platform Orchestrator
# ═══════════════════════════════════════════════════════════════


class PlatformOrchestrator:
    """AI-Native Platform Orchestration Core.

    Central orchestrator that coordinates all platform subsystems:
    service registry, workflow automation, integration hub, publishing pipeline,
    analytics dashboard, and multi-tenant workspace management.

    Provides a unified API for registering services, executing workflows,
    managing integrations, publishing content, collecting analytics, and
    managing isolated workspaces.

    Usage:
        orchestrator = get_platform_orchestrator()
        orchestrator.register_service(...)
        orchestrator.execute_workflow(...)
    """

    def __init__(self):
        # ── Service Registry ──────────────────────────────
        self._services: dict[str, ServiceRegistration] = {}
        self._heartbeat_interval_seconds: int = 30
        self._max_heartbeat_history: int = 50

        # ── Workflow Engine ───────────────────────────────
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._executions: dict[str, WorkflowExecution] = {}
        self._templates: dict[str, WorkflowTemplate] = {}
        self._execution_history: list[WorkflowExecution] = []
        self._max_execution_history: int = 500
        self._trigger_listeners: dict[str, list[Callable[[WorkflowTrigger], None]]] = {}

        # ── Integration Hub ───────────────────────────────
        self._integrations: dict[str, IntegrationConnection] = {}
        self._webhooks: dict[str, WebhookRegistration] = {}
        self._rate_limiters: dict[str, RateLimitConfig] = {}
        self._quota_trackers: dict[str, QuotaTracking] = {}

        # ── Publishing Pipeline ───────────────────────────
        self._published_content: dict[str, PublishingContent] = {}
        self._publishing_schedules: dict[str, PublishingSchedule] = {}

        # ── Analytics ─────────────────────────────────────
        self._metrics: list[PlatformMetric] = []
        self._max_metrics: int = 10000
        self._usage_records: dict[str, list[UsageRecord]] = {}
        self._performance_alerts: list[PerformanceAlert] = []
        self._max_alerts: int = 500
        self._cost_reports: list[CostReport] = []
        self._optimization_suggestions: list[OptimizationSuggestion] = []

        # ── Workspaces ────────────────────────────────────
        self._workspaces: dict[str, Workspace] = {}
        self._collaborations: dict[str, CrossWorkspaceCollaboration] = {}

        # ── General ───────────────────────────────────────
        self._is_running: bool = False
        self._startup_time: str = ""
        self._event_listeners: dict[str, list[Callable[..., None]]] = {}

        logger.info("PlatformOrchestrator initialized")

    # ─────────────────────────────────────────────────────────
    # Service Registry
    # ─────────────────────────────────────────────────────────

    def register_service(
        self,
        service_name: str,
        service_type: ServiceType,
        host: str = "",
        port: int = 0,
        version: ServiceVersion | None = None,
        health_endpoint: str = "",
        dependencies: list[str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceRegistration:
        """Register a new platform service.

        Args:
            service_name: Human-readable service name.
            service_type: Category of service being registered.
            host: Network host where the service runs.
            port: Network port number.
            version: Semantic version. Defaults to 1.0.0.
            health_endpoint: Endpoint path for health checks.
            dependencies: Service IDs this service depends on.
            tags: Searchable tags for service discovery.
            metadata: Arbitrary key-value metadata.

        Returns:
            The registered ServiceRegistration object.

        Raises:
            ValueError: If a service with the same name and type already exists.
        """
        for existing in self._services.values():
            if existing.service_name == service_name and existing.service_type == service_type:
                raise ValueError(
                    f"Service '{service_name}' of type '{service_type.value}' already registered "
                    f"(id={existing.service_id})"
                )

        registration = ServiceRegistration(
            service_name=service_name,
            service_type=service_type,
            version=version or ServiceVersion(),
            host=host,
            port=port,
            health_endpoint=health_endpoint,
            dependencies=dependencies or [],
            tags=tags or [],
            metadata=metadata or {},
        )
        self._services[registration.service_id] = registration
        logger.info(
            f"Service registered: {service_name} (id={registration.service_id}, "
            f"type={service_type.value}, version={registration.version})"
        )
        self._emit_event("service.registered", {"service_id": registration.service_id})
        return registration

    def discover_services(
        self,
        service_type: ServiceType | None = None,
        tags: list[str] | None = None,
        active_only: bool = True,
    ) -> list[ServiceRegistration]:
        """Discover registered services with optional filtering.

        Args:
            service_type: Filter by service type. None returns all types.
            tags: Filter by tags (services must have all specified tags).
            active_only: If True, only return active services.

        Returns:
            List of matching ServiceRegistration objects.
        """
        results = []
        for svc in self._services.values():
            if active_only and not svc.is_active:
                continue
            if service_type is not None and svc.service_type != service_type:
                continue
            if tags:
                if not all(t in svc.tags for t in tags):
                    continue
            results.append(svc)
        return results

    def get_service(self, service_id: str) -> ServiceRegistration | None:
        """Get a service by its ID.

        Args:
            service_id: The service's unique identifier.

        Returns:
            The ServiceRegistration if found, None otherwise.
        """
        return self._services.get(service_id)

    def deregister_service(self, service_id: str) -> bool:
        """Remove a service from the registry.

        Args:
            service_id: The service's unique identifier.

        Returns:
            True if the service was removed, False if not found.
        """
        if service_id in self._services:
            svc = self._services.pop(service_id)
            logger.info(f"Service deregistered: {svc.service_name} (id={service_id})")
            self._emit_event("service.deregistered", {"service_id": service_id})
            return True
        return False

    def record_heartbeat(
        self,
        service_id: str,
        cpu_usage: float = 0.0,
        memory_usage_mb: float = 0.0,
        active_connections: int = 0,
        custom_metrics: dict[str, Any] | None = None,
    ) -> ServiceHeartbeat | None:
        """Record a heartbeat for a registered service.

        Args:
            service_id: The service's unique identifier.
            cpu_usage: CPU usage percentage.
            memory_usage_mb: Memory usage in MB.
            active_connections: Number of active connections.
            custom_metrics: Arbitrary additional metrics.

        Returns:
            The ServiceHeartbeat record, or None if service not found.
        """
        svc = self._services.get(service_id)
        if svc is None:
            logger.warning(f"Heartbeat received for unknown service: {service_id}")
            return None

        heartbeat = ServiceHeartbeat(
            service_id=service_id,
            cpu_usage=cpu_usage,
            memory_usage_mb=memory_usage_mb,
            active_connections=active_connections,
            custom_metrics=custom_metrics or {},
        )
        svc.last_heartbeat = heartbeat.timestamp
        svc.heartbeat_history.append(heartbeat)

        # Trim heartbeat history
        if len(svc.heartbeat_history) > self._max_heartbeat_history:
            svc.heartbeat_history = svc.heartbeat_history[-self._max_heartbeat_history:]

        # Update health based on heartbeat
        if cpu_usage > 90 or memory_usage_mb > 1000:
            svc.health = ServiceHealth.DEGRADED
        else:
            svc.health = ServiceHealth.HEALTHY

        return heartbeat

    def check_service_health(self, service_id: str) -> ServiceHealth:
        """Check the health status of a service.

        Args:
            service_id: The service's unique identifier.

        Returns:
            Current ServiceHealth status. Returns UNKNOWN if service not found.
        """
        svc = self._services.get(service_id)
        if svc is None:
            return ServiceHealth.UNKNOWN

        # Check if heartbeat is stale
        if svc.last_heartbeat:
            try:
                last_hb = datetime.fromisoformat(svc.last_heartbeat)
                elapsed = (datetime.now(timezone.utc) - last_hb).total_seconds()
                if elapsed > self._heartbeat_interval_seconds * 3:
                    svc.health = ServiceHealth.UNHEALTHY
                    logger.warning(
                        f"Service {svc.service_name} (id={service_id}) heartbeat stale "
                        f"({elapsed:.0f}s elapsed)"
                    )
            except (ValueError, TypeError):
                pass

        return svc.health

    def check_version_compatibility(
        self, service_id: str, required_version: ServiceVersion
    ) -> bool:
        """Check if a service's version is compatible with a required version.

        Args:
            service_id: The service's unique identifier.
            required_version: The minimum required version.

        Returns:
            True if compatible, False otherwise.
        """
        svc = self._services.get(service_id)
        if svc is None:
            return False
        return svc.version.is_compatible_with(required_version)

    def get_service_stats(self) -> dict[str, Any]:
        """Get aggregate statistics about the service registry.

        Returns:
            Dictionary with count by type, health distribution, and totals.
        """
        type_counts: dict[str, int] = {}
        health_counts: dict[str, int] = {}
        for svc in self._services.values():
            t = svc.service_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
            h = svc.health.value
            health_counts[h] = health_counts.get(h, 0) + 1

        return {
            "total_services": len(self._services),
            "by_type": type_counts,
            "by_health": health_counts,
            "active_count": sum(1 for s in self._services.values() if s.is_active),
        }

    # ─────────────────────────────────────────────────────────
    # Workflow Automation Engine
    # ─────────────────────────────────────────────────────────

    def define_workflow(
        self,
        workflow_name: str,
        steps: list[WorkflowStep],
        description: str = "",
        triggers: list[WorkflowTrigger] | None = None,
        timeout_seconds: int = 3600,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowDefinition:
        """Define a new automated workflow.

        Args:
            workflow_name: Human-readable name for the workflow.
            steps: Ordered list of workflow steps.
            description: What the workflow accomplishes.
            triggers: Triggers that initiate this workflow.
            timeout_seconds: Global timeout in seconds.
            tags: Searchable tags.
            metadata: Arbitrary key-value metadata.

        Returns:
            The created WorkflowDefinition.
        """
        workflow = WorkflowDefinition(
            workflow_name=workflow_name,
            description=description,
            steps=steps,
            triggers=triggers or [],
            timeout_seconds=timeout_seconds,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._workflows[workflow.workflow_id] = workflow
        logger.info(
            f"Workflow defined: {workflow_name} (id={workflow.workflow_id}, "
            f"steps={len(steps)})"
        )
        self._emit_event("workflow.defined", {"workflow_id": workflow.workflow_id})
        return workflow

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Get a workflow definition by ID.

        Args:
            workflow_id: The workflow's unique identifier.

        Returns:
            The WorkflowDefinition if found, None otherwise.
        """
        return self._workflows.get(workflow_id)

    def list_workflows(self, tags: list[str] | None = None) -> list[WorkflowDefinition]:
        """List all workflow definitions, optionally filtered by tags.

        Args:
            tags: Filter by tags (workflows must have all specified tags).

        Returns:
            List of matching WorkflowDefinition objects.
        """
        if not tags:
            return list(self._workflows.values())
        return [
            wf for wf in self._workflows.values()
            if all(t in wf.tags for t in tags)
        ]

    def execute_workflow(
        self,
        workflow_id: str,
        trigger_type: TriggerType = TriggerType.MANUAL,
        parameters: dict[str, Any] | None = None,
    ) -> WorkflowExecution | None:
        """Execute a workflow by creating a new execution instance.

        Args:
            workflow_id: The workflow to execute.
            trigger_type: What triggered this execution.
            parameters: Parameter overrides for this execution.

        Returns:
            The WorkflowExecution if the workflow was found, None otherwise.
        """
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            logger.error(f"Workflow not found: {workflow_id}")
            return None

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_name=workflow.workflow_name,
            trigger_type=trigger_type,
            started_at=datetime.now(timezone.utc).isoformat(),
            parameters=parameters or {},
        )
        execution.state = WorkflowState.RUNNING
        execution.execution_log.append(
            f"[{execution.started_at}] Execution started (trigger={trigger_type.value})"
        )

        self._executions[execution.execution_id] = execution
        self._execution_history.append(execution)

        if len(self._execution_history) > self._max_execution_history:
            self._execution_history = self._execution_history[-self._max_execution_history:]

        logger.info(
            f"Workflow execution started: {workflow.workflow_name} "
            f"(exec_id={execution.execution_id}, wf_id={workflow_id})"
        )
        self._emit_event("workflow.execution.started", {
            "execution_id": execution.execution_id,
            "workflow_id": workflow_id,
        })
        return execution

    def complete_workflow_step(
        self,
        execution_id: str,
        step_id: str,
        result: dict[str, Any],
        success: bool = True,
    ) -> bool:
        """Record the completion of a workflow step.

        Args:
            execution_id: The execution's unique identifier.
            step_id: The step's unique identifier.
            result: The result data from the step.
            success: Whether the step completed successfully.

        Returns:
            True if the execution was found and updated, False otherwise.
        """
        execution = self._executions.get(execution_id)
        if execution is None:
            logger.error(f"Execution not found: {execution_id}")
            return False

        execution.step_results[step_id] = {
            "result": result,
            "success": success,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        execution.execution_log.append(
            f"[{datetime.now(timezone.utc).isoformat()}] Step {step_id} "
            f"{'completed' if success else 'failed'}"
        )
        return True

    def update_workflow_execution_state(
        self, execution_id: str, state: WorkflowState, error_message: str = ""
    ) -> bool:
        """Update the state of a workflow execution.

        Args:
            execution_id: The execution's unique identifier.
            state: New state to set.
            error_message: Error message if transitioning to FAILED.

        Returns:
            True if the execution was found and updated, False otherwise.
        """
        execution = self._executions.get(execution_id)
        if execution is None:
            logger.error(f"Execution not found: {execution_id}")
            return False

        execution.state = state
        if state == WorkflowState.FAILED:
            execution.error_message = error_message
        if state in (WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED):
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            execution.execution_log.append(
                f"[{execution.completed_at}] Execution {state.value}"
            )

        logger.info(f"Workflow execution {execution_id} -> {state.value}")
        self._emit_event("workflow.execution.state_changed", {
            "execution_id": execution_id,
            "state": state.value,
        })
        return True

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """Get a workflow execution by ID.

        Args:
            execution_id: The execution's unique identifier.

        Returns:
            The WorkflowExecution if found, None otherwise.
        """
        return self._executions.get(execution_id)

    def get_execution_history(
        self, workflow_id: str | None = None, limit: int = 50
    ) -> list[WorkflowExecution]:
        """Get execution history, optionally filtered by workflow.

        Args:
            workflow_id: Filter by workflow. None returns all.
            limit: Maximum number of results to return.

        Returns:
            List of WorkflowExecution objects, most recent first.
        """
        history = self._execution_history
        if workflow_id:
            history = [e for e in history if e.workflow_id == workflow_id]
        return history[-limit:][::-1]

    def create_workflow_template(
        self,
        template_name: str,
        base_workflow: WorkflowDefinition,
        description: str = "",
        parameters: dict[str, dict[str, Any]] | None = None,
        category: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowTemplate:
        """Create a parameterized workflow template.

        Args:
            template_name: Human-readable name for the template.
            base_workflow: The underlying workflow definition.
            description: What the template represents.
            parameters: Parameter definitions mapping name -> {type, default, description}.
            category: Grouping category.
            tags: Searchable tags.
            metadata: Arbitrary key-value metadata.

        Returns:
            The created WorkflowTemplate.
        """
        template = WorkflowTemplate(
            template_name=template_name,
            description=description,
            base_workflow=base_workflow,
            parameters=parameters or {},
            category=category,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._templates[template.template_id] = template
        logger.info(f"Workflow template created: {template_name} (id={template.template_id})")
        return template

    def instantiate_template(
        self, template_id: str, parameter_values: dict[str, Any] | None = None
    ) -> WorkflowDefinition | None:
        """Instantiate a workflow from a template with parameter values.

        Args:
            template_id: The template's unique identifier.
            parameter_values: Values for the template's parameters.

        Returns:
            A new WorkflowDefinition, or None if template not found.
        """
        template = self._templates.get(template_id)
        if template is None:
            logger.error(f"Template not found: {template_id}")
            return None

        template.usage_count += 1
        template.updated_at = datetime.now(timezone.utc).isoformat()

        # Create a new workflow from the template
        workflow = WorkflowDefinition(
            workflow_name=f"{template.template_name} (instance)",
            description=template.description,
            steps=template.base_workflow.steps,
            triggers=template.base_workflow.triggers,
            timeout_seconds=template.base_workflow.timeout_seconds,
            tags=template.base_workflow.tags,
            metadata={
                "template_id": template_id,
                "parameter_values": parameter_values or {},
                **(template.base_workflow.metadata),
            },
        )
        self._workflows[workflow.workflow_id] = workflow
        logger.info(
            f"Template instantiated: {template.template_name} -> "
            f"{workflow.workflow_id} (usage={template.usage_count})"
        )
        return workflow

    def register_trigger_listener(
        self, trigger_type: TriggerType, callback: Callable[[WorkflowTrigger], None]
    ) -> None:
        """Register a listener for a specific trigger type.

        Args:
            trigger_type: The trigger type to listen for.
            callback: Function to call when the trigger fires.
        """
        key = trigger_type.value
        if key not in self._trigger_listeners:
            self._trigger_listeners[key] = []
        self._trigger_listeners[key].append(callback)
        logger.debug(f"Trigger listener registered for '{key}'")

    # ─────────────────────────────────────────────────────────
    # Integration Hub
    # ─────────────────────────────────────────────────────────

    def register_integration(
        self,
        integration_name: str,
        service_url: str,
        credential: CredentialBundle | None = None,
        rate_limit: RateLimitConfig | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IntegrationConnection:
        """Register a new external integration connection.

        Args:
            integration_name: Human-readable name for the integration.
            service_url: Base URL of the external service.
            credential: Credential bundle for authentication.
            rate_limit: Rate limiting configuration.
            tags: Searchable tags.
            metadata: Arbitrary key-value metadata.

        Returns:
            The created IntegrationConnection.
        """
        integration = IntegrationConnection(
            integration_name=integration_name,
            service_url=service_url,
            credential=credential,
            rate_limit=rate_limit or RateLimitConfig(),
            tags=tags or [],
            metadata=metadata or {},
        )
        self._integrations[integration.integration_id] = integration
        logger.info(
            f"Integration registered: {integration_name} (id={integration.integration_id})"
        )
        self._emit_event("integration.registered", {"integration_id": integration.integration_id})
        return integration

    def get_integration(self, integration_id: str) -> IntegrationConnection | None:
        """Get an integration by ID.

        Args:
            integration_id: The integration's unique identifier.

        Returns:
            The IntegrationConnection if found, None otherwise.
        """
        return self._integrations.get(integration_id)

    def connect_integration(self, integration_id: str) -> bool:
        """Mark an integration as connected.

        Args:
            integration_id: The integration's unique identifier.

        Returns:
            True if the integration was found and connected, False otherwise.
        """
        integration = self._integrations.get(integration_id)
        if integration is None:
            logger.error(f"Integration not found: {integration_id}")
            return False

        integration.status = IntegrationStatus.CONNECTING
        integration.connected_at = datetime.now(timezone.utc).isoformat()
        integration.status = IntegrationStatus.CONNECTED
        integration.error_count = 0
        integration.last_error = ""
        logger.info(f"Integration connected: {integration.integration_name} (id={integration_id})")
        self._emit_event("integration.connected", {"integration_id": integration_id})
        return True

    def disconnect_integration(self, integration_id: str) -> bool:
        """Disconnect an integration.

        Args:
            integration_id: The integration's unique identifier.

        Returns:
            True if the integration was found and disconnected, False otherwise.
        """
        integration = self._integrations.get(integration_id)
        if integration is None:
            return False
        integration.status = IntegrationStatus.DISCONNECTED
        logger.info(f"Integration disconnected: {integration.integration_name}")
        self._emit_event("integration.disconnected", {"integration_id": integration_id})
        return True

    def record_integration_error(self, integration_id: str, error_message: str) -> bool:
        """Record an error for an integration connection.

        Args:
            integration_id: The integration's unique identifier.
            error_message: The error message.

        Returns:
            True if the integration was found, False otherwise.
        """
        integration = self._integrations.get(integration_id)
        if integration is None:
            return False
        integration.error_count += 1
        integration.last_error = error_message
        if integration.error_count > 5:
            integration.status = IntegrationStatus.ERROR
        logger.warning(
            f"Integration error: {integration.integration_name} "
            f"(count={integration.error_count}): {error_message[:100]}"
        )
        return True

    def register_webhook(
        self,
        integration_id: str,
        webhook_url: str,
        event_types: list[str],
        direction: str = "inbound",
        secret: str = "",
        retry_policy: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WebhookRegistration | None:
        """Register a webhook for an integration.

        Args:
            integration_id: The integration this webhook belongs to.
            webhook_url: URL endpoint for the webhook.
            event_types: Event types this webhook listens for.
            direction: "inbound" or "outbound".
            secret: HMAC secret for payload verification.
            retry_policy: Retry configuration for failed deliveries.
            metadata: Arbitrary key-value metadata.

        Returns:
            The WebhookRegistration, or None if integration not found.
        """
        integration = self._integrations.get(integration_id)
        if integration is None:
            logger.error(f"Integration not found for webhook: {integration_id}")
            return None

        webhook = WebhookRegistration(
            integration_id=integration_id,
            webhook_url=webhook_url,
            event_types=event_types,
            secret=secret,
            direction=direction,
            retry_policy=retry_policy or {},
            metadata=metadata or {},
        )
        self._webhooks[webhook.webhook_id] = webhook
        integration.webhooks.append(webhook)
        logger.info(
            f"Webhook registered: {webhook_url} for {integration.integration_name} "
            f"(events={event_types})"
        )
        return webhook

    def trigger_webhook(self, webhook_id: str, event_type: str, payload: dict[str, Any]) -> bool:
        """Trigger a webhook delivery.

        Args:
            webhook_id: The webhook's unique identifier.
            event_type: The event type being delivered.
            payload: The payload to deliver.

        Returns:
            True if the webhook was found and triggered, False otherwise.
        """
        webhook = self._webhooks.get(webhook_id)
        if webhook is None:
            logger.error(f"Webhook not found: {webhook_id}")
            return False

        if not webhook.is_active:
            logger.warning(f"Webhook {webhook_id} is not active")
            return False

        webhook.last_triggered_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Webhook triggered: {webhook_id} event={event_type} "
            f"url={webhook.webhook_url}"
        )
        self._emit_event("webhook.triggered", {
            "webhook_id": webhook_id,
            "event_type": event_type,
        })
        return True

    def set_rate_limit(
        self,
        integration_id: str,
        max_per_minute: int = 60,
        max_per_hour: int = 1000,
        max_per_day: int = 10000,
        burst_limit: int = 10,
    ) -> RateLimitConfig | None:
        """Configure rate limiting for an integration.

        Args:
            integration_id: The integration's unique identifier.
            max_per_minute: Maximum requests per minute.
            max_per_hour: Maximum requests per hour.
            max_per_day: Maximum requests per day.
            burst_limit: Maximum burst requests beyond the steady rate.

        Returns:
            The RateLimitConfig, or None if integration not found.
        """
        integration = self._integrations.get(integration_id)
        if integration is None:
            return None

        integration.rate_limit = RateLimitConfig(
            max_requests_per_minute=max_per_minute,
            max_requests_per_hour=max_per_hour,
            max_requests_per_day=max_per_day,
            burst_limit=burst_limit,
        )
        self._rate_limiters[integration_id] = integration.rate_limit
        logger.info(f"Rate limit configured for {integration.integration_name}")
        return integration.rate_limit

    def check_rate_limit(self, integration_id: str) -> bool:
        """Check if an integration is within its rate limits.

        Args:
            integration_id: The integration's unique identifier.

        Returns:
            True if the integration is within limits, False if rate limited.
        """
        integration = self._integrations.get(integration_id)
        if integration is None:
            return True

        rl = integration.rate_limit
        now = datetime.now(timezone.utc)

        # Reset counters if windows have elapsed
        try:
            last_min = datetime.fromisoformat(rl.last_reset_minute)
            if (now - last_min).total_seconds() >= 60:
                rl.current_minute_count = 0
                rl.last_reset_minute = now.isoformat()
            last_hour = datetime.fromisoformat(rl.last_reset_hour)
            if (now - last_hour).total_seconds() >= 3600:
                rl.current_hour_count = 0
                rl.last_reset_hour = now.isoformat()
            last_day = datetime.fromisoformat(rl.last_reset_day)
            if (now - last_day).total_seconds() >= 86400:
                rl.current_day_count = 0
                rl.last_reset_day = now.isoformat()
        except (ValueError, TypeError):
            pass

        if rl.current_minute_count >= rl.max_requests_per_minute:
            return False
        if rl.current_hour_count >= rl.max_requests_per_hour:
            return False
        if rl.current_day_count >= rl.max_requests_per_day:
            return False

        rl.current_minute_count += 1
        rl.current_hour_count += 1
        rl.current_day_count += 1
        return True

    def set_quota(
        self,
        integration_id: str,
        total_quota: int,
        quota_unit: str = "requests",
        reset_period: str = "monthly",
        alert_threshold_percent: float = 80.0,
    ) -> QuotaTracking | None:
        """Set quota tracking for an integration.

        Args:
            integration_id: The integration's unique identifier.
            total_quota: Total allowed usage.
            quota_unit: Unit of measurement (e.g. "requests", "tokens").
            reset_period: Reset period (e.g. "daily", "monthly").
            alert_threshold_percent: Percentage threshold for alerts.

        Returns:
            The QuotaTracking object, or None if integration not found.
        """
        integration = self._integrations.get(integration_id)
        if integration is None:
            return None

        quota = QuotaTracking(
            integration_id=integration_id,
            total_quota=total_quota,
            quota_unit=quota_unit,
            reset_period=reset_period,
            alert_threshold_percent=alert_threshold_percent,
        )
        integration.quota = quota
        self._quota_trackers[integration_id] = quota
        logger.info(f"Quota set for {integration.integration_name}: {total_quota} {quota_unit}")
        return quota

    def track_quota_usage(self, integration_id: str, amount: int = 1) -> bool:
        """Track quota usage for an integration.

        Args:
            integration_id: The integration's unique identifier.
            amount: Amount of quota consumed.

        Returns:
            True if within quota, False if quota exceeded.
        """
        integration = self._integrations.get(integration_id)
        if integration is None or integration.quota is None:
            return True

        quota = integration.quota
        quota.used_quota += amount

        if quota.used_quota >= quota.total_quota:
            logger.warning(
                f"Quota exceeded for {integration.integration_name}: "
                f"{quota.used_quota}/{quota.total_quota} {quota.quota_unit}"
            )
            return False
        return True

    def get_integration_summary(self) -> dict[str, Any]:
        """Get a summary of all integrations and their statuses.

        Returns:
            Dictionary with total count, status breakdown, and per-integration info.
        """
        status_counts: dict[str, int] = {}
        for integration in self._integrations.values():
            s = integration.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            "total_integrations": len(self._integrations),
            "status_breakdown": status_counts,
            "total_webhooks": len(self._webhooks),
            "total_quota_trackers": len(self._quota_trackers),
        }

    # ─────────────────────────────────────────────────────────
    # Publishing Pipeline
    # ─────────────────────────────────────────────────────────

    def create_content(
        self,
        title: str,
        content_type: str,
        body: dict[str, Any],
        author: str = "",
        tags: list[str] | None = None,
        distribution_targets: list[DistributionTarget] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PublishingContent:
        """Create new content in the publishing pipeline.

        Args:
            title: Content title.
            content_type: Type of content (e.g. "blog", "release").
            body: Content body or payload.
            author: Creator of the content.
            tags: Searchable tags.
            distribution_targets: Target channels for distribution.
            metadata: Arbitrary key-value metadata.

        Returns:
            The created PublishingContent in DRAFT state.
        """
        content = PublishingContent(
            title=title,
            content_type=content_type,
            body=body,
            state=PublishingState.DRAFT,
            author=author,
            tags=tags or [],
            distribution_targets=distribution_targets or [],
            metadata=metadata or {},
        )
        self._published_content[content.content_id] = content
        logger.info(f"Content created: {title} (id={content.content_id}, type={content_type})")
        self._emit_event("publishing.content.created", {"content_id": content.content_id})
        return content

    def submit_for_review(self, content_id: str, reviewer: str = "") -> bool:
        """Submit content for review.

        Args:
            content_id: The content's unique identifier.
            reviewer: Assigned reviewer.

        Returns:
            True if the content was found and submitted, False otherwise.
        """
        content = self._published_content.get(content_id)
        if content is None:
            logger.error(f"Content not found: {content_id}")
            return False

        if content.state != PublishingState.DRAFT:
            logger.warning(
                f"Content {content_id} not in DRAFT state (current={content.state.value})"
            )
            return False

        content.state = PublishingState.IN_REVIEW
        content.reviewer = reviewer
        content.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Content submitted for review: {content.title} (reviewer={reviewer})")
        self._emit_event("publishing.content.review_requested", {"content_id": content_id})
        return True

    def approve_content(self, content_id: str, reviewer_comment: str = "") -> bool:
        """Approve content for publishing.

        Args:
            content_id: The content's unique identifier.
            reviewer_comment: Optional comment from the reviewer.

        Returns:
            True if the content was found and approved, False otherwise.
        """
        content = self._published_content.get(content_id)
        if content is None:
            return False

        if content.state != PublishingState.IN_REVIEW:
            return False

        # Create a version snapshot
        version = ContentVersion(
            content_id=content_id,
            version_number=len(content.versions) + 1,
            content_snapshot={"body": content.body, "title": content.title},
            created_by=content.reviewer,
            comment=reviewer_comment,
        )
        content.versions.append(version)
        content.state = PublishingState.APPROVED
        content.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Content approved: {content.title} (version={version.version_number})")
        self._emit_event("publishing.content.approved", {"content_id": content_id})
        return True

    def reject_content(self, content_id: str, reason: str = "") -> bool:
        """Reject content during review.

        Args:
            content_id: The content's unique identifier.
            reason: Reason for rejection.

        Returns:
            True if the content was found and rejected, False otherwise.
        """
        content = self._published_content.get(content_id)
        if content is None:
            return False

        if content.state != PublishingState.IN_REVIEW:
            return False

        content.state = PublishingState.REJECTED
        content.updated_at = datetime.now(timezone.utc).isoformat()
        content.metadata["rejection_reason"] = reason
        logger.info(f"Content rejected: {content.title} (reason={reason})")
        self._emit_event("publishing.content.rejected", {"content_id": content_id})
        return True

    def schedule_publishing(
        self,
        content_id: str,
        scheduled_at: str,
        timezone_str: str = "UTC",
        recurrence: str = "",
    ) -> PublishingSchedule | None:
        """Schedule content for publishing at a specific time.

        Args:
            content_id: The content's unique identifier.
            scheduled_at: ISO timestamp when publishing should occur.
            timezone_str: IANA timezone string (e.g. "Asia/Shanghai").
            recurrence: Optional cron expression for recurring publishing.

        Returns:
            The PublishingSchedule, or None if content not found.
        """
        content = self._published_content.get(content_id)
        if content is None:
            return None

        schedule = PublishingSchedule(
            scheduled_at=scheduled_at,
            timezone=timezone_str,
            recurrence=recurrence,
        )
        content.schedule = schedule
        content.state = PublishingState.SCHEDULED
        content.updated_at = datetime.now(timezone.utc).isoformat()
        self._publishing_schedules[schedule.schedule_id] = schedule
        logger.info(
            f"Content scheduled for publishing: {content.title} at {scheduled_at} "
            f"({timezone_str})"
        )
        self._emit_event("publishing.content.scheduled", {"content_id": content_id})
        return schedule

    def publish_content(self, content_id: str) -> bool:
        """Publish content to all configured distribution targets.

        Args:
            content_id: The content's unique identifier.

        Returns:
            True if published successfully, False otherwise.
        """
        content = self._published_content.get(content_id)
        if content is None:
            return False

        if content.state not in (PublishingState.APPROVED, PublishingState.SCHEDULED):
            logger.warning(
                f"Content {content_id} not in publishable state (current={content.state.value})"
            )
            return False

        content.state = PublishingState.PUBLISHING
        content.published_at = datetime.now(timezone.utc).isoformat()

        # Distribute to all enabled targets
        for target in content.distribution_targets:
            if target.is_enabled:
                target.last_distributed_at = content.published_at
                target.delivery_status = "delivered"
                logger.info(
                    f"Content distributed to {target.channel.value}: {content.title}"
                )

        content.state = PublishingState.PUBLISHED
        content.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Content published: {content.title} (id={content_id})")
        self._emit_event("publishing.content.published", {"content_id": content_id})
        return True

    def rollback_content(self, content_id: str, reason: str = "", performed_by: str = "") -> bool:
        """Roll back published content to the previous version.

        Args:
            content_id: The content's unique identifier.
            reason: Reason for the rollback.
            performed_by: Identifier of who performed the rollback.

        Returns:
            True if rolled back successfully, False otherwise.
        """
        content = self._published_content.get(content_id)
        if content is None:
            return False

        if content.state != PublishingState.PUBLISHED:
            return False

        if len(content.versions) < 2:
            logger.warning(f"Content {content_id} has no previous version to roll back to")
            return False

        content.state = PublishingState.ROLLING_BACK

        current_version = content.versions[-1]
        previous_version = content.versions[-2]

        rollback = PublishingRollback(
            content_id=content_id,
            rolled_back_from_version=current_version.version_number,
            rolled_back_to_version=previous_version.version_number,
            reason=reason,
            performed_by=performed_by,
            affected_channels=[t.channel.value for t in content.distribution_targets],
        )
        content.rollback_history.append(rollback)

        # Restore previous version content
        content.body = previous_version.content_snapshot.get("body", {})
        content.title = previous_version.content_snapshot.get("title", content.title)

        content.state = PublishingState.ROLLED_BACK
        content.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Content rolled back: {content.title} from v{rollback.rolled_back_from_version} "
            f"to v{rollback.rolled_back_to_version}"
        )
        self._emit_event("publishing.content.rolled_back", {"content_id": content_id})
        return True

    def get_content(self, content_id: str) -> PublishingContent | None:
        """Get content by ID.

        Args:
            content_id: The content's unique identifier.

        Returns:
            The PublishingContent if found, None otherwise.
        """
        return self._published_content.get(content_id)

    def list_content(
        self, state: PublishingState | None = None, content_type: str | None = None
    ) -> list[PublishingContent]:
        """List content items with optional filtering.

        Args:
            state: Filter by publishing state.
            content_type: Filter by content type.

        Returns:
            List of matching PublishingContent objects.
        """
        results = list(self._published_content.values())
        if state is not None:
            results = [c for c in results if c.state == state]
        if content_type is not None:
            results = [c for c in results if c.content_type == content_type]
        return results

    def add_distribution_target(
        self,
        content_id: str,
        channel: DistributionChannel,
        channel_config: dict[str, Any] | None = None,
        priority: int = 5,
    ) -> DistributionTarget | None:
        """Add a distribution target to content.

        Args:
            content_id: The content's unique identifier.
            channel: Distribution channel type.
            channel_config: Channel-specific configuration.
            priority: Priority order for distribution.

        Returns:
            The DistributionTarget, or None if content not found.
        """
        content = self._published_content.get(content_id)
        if content is None:
            return None

        target = DistributionTarget(
            channel=channel,
            channel_config=channel_config or {},
            priority=priority,
        )
        content.distribution_targets.append(target)
        content.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Distribution target added: {channel.value} to {content.title}")
        return target

    # ─────────────────────────────────────────────────────────
    # Analytics Dashboard
    # ─────────────────────────────────────────────────────────

    def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        source: str = "",
        source_type: str = "",
        unit: str = "",
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PlatformMetric:
        """Record a platform metric data point.

        Args:
            metric_type: Type of metric being recorded.
            value: Numeric value.
            source: Source of the metric (service_id, agent_id, etc.).
            source_type: Type of source (e.g. "service", "agent").
            unit: Unit of measurement.
            tags: Dimension tags for filtering/grouping.
            metadata: Arbitrary key-value metadata.

        Returns:
            The recorded PlatformMetric.
        """
        metric = PlatformMetric(
            metric_type=metric_type,
            value=value,
            unit=unit,
            source=source,
            source_type=source_type,
            tags=tags or {},
            metadata=metadata or {},
        )
        self._metrics.append(metric)

        # Trim metrics if exceeding max
        if len(self._metrics) > self._max_metrics:
            self._metrics = self._metrics[-self._max_metrics:]

        logger.debug(f"Metric recorded: {metric_type.value}={value}{unit} from {source}")
        return metric

    def get_metrics(
        self,
        metric_type: MetricType | None = None,
        source: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[PlatformMetric]:
        """Query metrics with optional filtering.

        Args:
            metric_type: Filter by metric type.
            source: Filter by source.
            since: ISO timestamp - only return metrics after this time.
            limit: Maximum number of results.

        Returns:
            List of matching PlatformMetric objects, most recent first.
        """
        results = self._metrics
        if metric_type is not None:
            results = [m for m in results if m.metric_type == metric_type]
        if source is not None:
            results = [m for m in results if m.source == source]
        if since is not None:
            results = [m for m in results if m.recorded_at >= since]
        return list(reversed(results[-limit:]))

    def get_aggregated_metrics(
        self, metric_type: MetricType, since: str | None = None
    ) -> dict[str, Any]:
        """Get aggregated statistics for a metric type.

        Args:
            metric_type: Type of metric to aggregate.
            since: ISO timestamp - only aggregate metrics after this time.

        Returns:
            Dictionary with count, sum, avg, min, max.
        """
        metrics = self.get_metrics(metric_type=metric_type, since=since, limit=100000)
        if not metrics:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}

        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "sum": round(sum(values), 2),
            "avg": round(sum(values) / len(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
        }

    def record_usage(
        self,
        subject_id: str,
        subject_type: str,
        period_start: str,
        period_end: str,
        metrics: dict[str, float],
        total_cost_usd: float = 0.0,
    ) -> UsageRecord:
        """Record a usage report for a subject.

        Args:
            subject_id: The subject being tracked.
            subject_type: Type of subject.
            period_start: Start of the usage period.
            period_end: End of the usage period.
            metrics: Aggregated metric values.
            total_cost_usd: Total cost in USD.

        Returns:
            The created UsageRecord.
        """
        record = UsageRecord(
            subject_id=subject_id,
            subject_type=subject_type,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
            total_cost_usd=total_cost_usd,
        )
        if subject_id not in self._usage_records:
            self._usage_records[subject_id] = []
        self._usage_records[subject_id].append(record)
        logger.debug(f"Usage recorded for {subject_type}/{subject_id}: ${total_cost_usd:.4f}")
        return record

    def get_usage(self, subject_id: str) -> list[UsageRecord]:
        """Get usage records for a specific subject.

        Args:
            subject_id: The subject's unique identifier.

        Returns:
            List of UsageRecord objects.
        """
        return self._usage_records.get(subject_id, [])

    def create_performance_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        metric_type: MetricType,
        threshold: float,
        actual_value: float,
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> PerformanceAlert:
        """Create a performance alert.

        Args:
            alert_type: Type of alert (e.g. "latency_spike").
            severity: Severity level.
            message: Human-readable message.
            metric_type: The metric that triggered this alert.
            threshold: The threshold value breached.
            actual_value: The actual observed value.
            source: Source that triggered the alert.
            metadata: Arbitrary key-value metadata.

        Returns:
            The created PerformanceAlert.
        """
        alert = PerformanceAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            metric_type=metric_type,
            threshold=threshold,
            actual_value=actual_value,
            source=source,
            metadata=metadata or {},
        )
        self._performance_alerts.append(alert)

        if len(self._performance_alerts) > self._max_alerts:
            self._performance_alerts = self._performance_alerts[-self._max_alerts:]

        logger.warning(
            f"Performance alert [{severity.value}]: {message} "
            f"(actual={actual_value}, threshold={threshold})"
        )
        self._emit_event("analytics.alert.created", {"alert_id": alert.alert_id})
        return alert

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "") -> bool:
        """Acknowledge a performance alert.

        Args:
            alert_id: The alert's unique identifier.
            acknowledged_by: Who acknowledged the alert.

        Returns:
            True if acknowledged, False if not found.
        """
        for alert in self._performance_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a performance alert.

        Args:
            alert_id: The alert's unique identifier.

        Returns:
            True if resolved, False if not found.
        """
        for alert in self._performance_alerts:
            if alert.alert_id == alert_id:
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False

    def get_active_alerts(self) -> list[PerformanceAlert]:
        """Get all unresolved, unacknowledged alerts.

        Returns:
            List of active PerformanceAlert objects.
        """
        return [a for a in self._performance_alerts if not a.resolved_at]

    def generate_cost_report(
        self,
        period_start: str,
        period_end: str,
        breakdown: dict[str, float] | None = None,
    ) -> CostReport:
        """Generate a cost tracking report for a time period.

        Args:
            period_start: Start of the reporting period.
            period_end: End of the reporting period.
            breakdown: Cost breakdown by service/agent/user.

        Returns:
            The generated CostReport.
        """
        total = sum(breakdown.values()) if breakdown else 0.0
        report = CostReport(
            period_start=period_start,
            period_end=period_end,
            total_cost_usd=total,
            breakdown=breakdown or {},
        )
        self._cost_reports.append(report)
        logger.info(f"Cost report generated: ${total:.4f} ({period_start} to {period_end})")
        return report

    def get_cost_reports(self, limit: int = 10) -> list[CostReport]:
        """Get recent cost reports.

        Args:
            limit: Maximum number of reports to return.

        Returns:
            List of CostReport objects, most recent first.
        """
        return list(reversed(self._cost_reports[-limit:]))

    def create_optimization_suggestion(
        self,
        category: str,
        description: str,
        estimated_savings_usd: float = 0.0,
        impact: str = "medium",
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> OptimizationSuggestion:
        """Create a cost or performance optimization suggestion.

        Args:
            category: Suggestion category (e.g. "cost", "performance").
            description: Human-readable description.
            estimated_savings_usd: Estimated savings per month.
            impact: Expected impact level ("low", "medium", "high").
            source: Source that led to this suggestion.
            metadata: Arbitrary key-value metadata.

        Returns:
            The created OptimizationSuggestion.
        """
        suggestion = OptimizationSuggestion(
            category=category,
            description=description,
            estimated_savings_usd=estimated_savings_usd,
            impact=impact,
            source=source,
            metadata=metadata or {},
        )
        self._optimization_suggestions.append(suggestion)
        logger.info(
            f"Optimization suggestion: {category} - ${estimated_savings_usd:.2f}/mo "
            f"(impact={impact})"
        )
        return suggestion

    def get_optimization_suggestions(
        self, status: str | None = None, category: str | None = None
    ) -> list[OptimizationSuggestion]:
        """Get optimization suggestions with optional filtering.

        Args:
            status: Filter by status (e.g. "pending", "implemented").
            category: Filter by category.

        Returns:
            List of matching OptimizationSuggestion objects.
        """
        results = self._optimization_suggestions
        if status is not None:
            results = [s for s in results if s.status == status]
        if category is not None:
            results = [s for s in results if s.category == category]
        return results

    def get_platform_analytics_summary(self) -> dict[str, Any]:
        """Get a high-level summary of platform analytics.

        Returns:
            Dictionary with metric counts, alert counts, cost totals, and suggestions.
        """
        total_cost = sum(r.total_cost_usd for r in self._cost_reports)
        return {
            "total_metrics": len(self._metrics),
            "total_usage_records": sum(len(v) for v in self._usage_records.values()),
            "active_alerts": len(self.get_active_alerts()),
            "total_alerts": len(self._performance_alerts),
            "total_cost_reports": len(self._cost_reports),
            "cumulative_cost_usd": round(total_cost, 4),
            "total_suggestions": len(self._optimization_suggestions),
            "pending_suggestions": len(
                [s for s in self._optimization_suggestions if s.status == "pending"]
            ),
        }

    # ─────────────────────────────────────────────────────────
    # Multi-Tenant Workspace
    # ─────────────────────────────────────────────────────────

    def create_workspace(
        self,
        workspace_name: str,
        owner_id: str,
        description: str = "",
        settings: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Workspace:
        """Create a new isolated workspace.

        Args:
            workspace_name: Human-readable name.
            owner_id: User ID of the workspace owner.
            description: Description of the workspace's purpose.
            settings: Workspace-specific settings.
            metadata: Arbitrary key-value metadata.

        Returns:
            The created Workspace.
        """
        workspace = Workspace(
            workspace_name=workspace_name,
            description=description,
            owner_id=owner_id,
            settings=settings or {},
            metadata=metadata or {},
        )
        # Auto-add owner as a member with OWNER role
        owner_binding = WorkspaceRoleBinding(
            user_id=owner_id,
            workspace_id=workspace.workspace_id,
            role=WorkspaceRole.OWNER,
            granted_by="system",
        )
        owner_member = WorkspaceMember(
            user_id=owner_id,
            display_name=owner_id,
            role=WorkspaceRole.OWNER,
            role_bindings=[owner_binding],
        )
        workspace.members.append(owner_member)
        self._workspaces[workspace.workspace_id] = workspace
        logger.info(
            f"Workspace created: {workspace_name} (id={workspace.workspace_id}, "
            f"owner={owner_id})"
        )
        self._emit_event("workspace.created", {"workspace_id": workspace.workspace_id})
        return workspace

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Get a workspace by ID.

        Args:
            workspace_id: The workspace's unique identifier.

        Returns:
            The Workspace if found, None otherwise.
        """
        return self._workspaces.get(workspace_id)

    def list_workspaces(self, active_only: bool = True) -> list[Workspace]:
        """List all workspaces.

        Args:
            active_only: If True, only return active workspaces.

        Returns:
            List of Workspace objects.
        """
        if active_only:
            return [w for w in self._workspaces.values() if w.is_active]
        return list(self._workspaces.values())

    def add_workspace_member(
        self,
        workspace_id: str,
        user_id: str,
        role: WorkspaceRole,
        display_name: str = "",
        email: str = "",
        granted_by: str = "",
        custom_permissions: list[str] | None = None,
    ) -> WorkspaceMember | None:
        """Add a member to a workspace with a role.

        Args:
            workspace_id: The workspace's unique identifier.
            user_id: The user's unique identifier.
            role: The role to assign.
            display_name: Human-readable display name.
            email: User's email address.
            granted_by: Who granted the role.
            custom_permissions: Additional custom permissions.

        Returns:
            The WorkspaceMember if added, None if workspace not found or already a member.
        """
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            logger.error(f"Workspace not found: {workspace_id}")
            return None

        # Check if already a member
        for member in workspace.members:
            if member.user_id == user_id:
                logger.warning(f"User {user_id} is already a member of workspace {workspace_id}")
                return None

        binding = WorkspaceRoleBinding(
            user_id=user_id,
            workspace_id=workspace_id,
            role=role,
            granted_by=granted_by,
            custom_permissions=custom_permissions or [],
        )
        member = WorkspaceMember(
            user_id=user_id,
            display_name=display_name or user_id,
            email=email,
            role=role,
            role_bindings=[binding],
        )
        workspace.members.append(member)
        workspace.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Member added to workspace {workspace.workspace_name}: "
            f"{user_id} as {role.value}"
        )
        self._emit_event("workspace.member.added", {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": role.value,
        })
        return member

    def remove_workspace_member(self, workspace_id: str, user_id: str) -> bool:
        """Remove a member from a workspace.

        Args:
            workspace_id: The workspace's unique identifier.
            user_id: The user's unique identifier.

        Returns:
            True if removed, False if workspace or member not found.
        """
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            return False

        for i, member in enumerate(workspace.members):
            if member.user_id == user_id:
                workspace.members.pop(i)
                workspace.updated_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"Member removed from workspace {workspace_id}: {user_id}")
                self._emit_event("workspace.member.removed", {
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                })
                return True
        return False

    def get_user_role(self, workspace_id: str, user_id: str) -> WorkspaceRole | None:
        """Get a user's role in a workspace.

        Args:
            workspace_id: The workspace's unique identifier.
            user_id: The user's unique identifier.

        Returns:
            The WorkspaceRole if found, None otherwise.
        """
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            return None
        for member in workspace.members:
            if member.user_id == user_id:
                return member.role
        return None

    def share_resource(
        self,
        resource_type: str,
        resource_name: str,
        owner_workspace_id: str,
        shared_with: list[str],
        collaboration_mode: CollaborationMode = CollaborationMode.READ_ONLY,
        metadata: dict[str, Any] | None = None,
    ) -> SharedResource | None:
        """Share a resource from one workspace with others.

        Args:
            resource_type: Type of resource.
            resource_name: Human-readable name.
            owner_workspace_id: The workspace that owns the resource.
            shared_with: Workspace IDs to share with.
            collaboration_mode: Access mode for shared workspaces.
            metadata: Arbitrary key-value metadata.

        Returns:
            The SharedResource, or None if owner workspace not found.
        """
        workspace = self._workspaces.get(owner_workspace_id)
        if workspace is None:
            logger.error(f"Owner workspace not found: {owner_workspace_id}")
            return None

        resource = SharedResource(
            resource_type=resource_type,
            resource_name=resource_name,
            owner_workspace_id=owner_workspace_id,
            shared_with=shared_with,
            collaboration_mode=collaboration_mode,
            metadata=metadata or {},
        )
        workspace.shared_resources.append(resource)
        workspace.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Resource shared: {resource_name} ({resource_type}) from "
            f"{owner_workspace_id} to {len(shared_with)} workspace(s)"
        )
        self._emit_event("workspace.resource.shared", {
            "resource_id": resource.resource_id,
            "owner_workspace_id": owner_workspace_id,
        })
        return resource

    def establish_collaboration(
        self,
        source_workspace_id: str,
        target_workspace_id: str,
        mode: CollaborationMode = CollaborationMode.READ_ONLY,
        established_by: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CrossWorkspaceCollaboration | None:
        """Establish a collaboration link between two workspaces.

        Args:
            source_workspace_id: The workspace initiating the collaboration.
            target_workspace_id: The workspace being collaborated with.
            mode: Collaboration access mode.
            established_by: Who established the collaboration.
            metadata: Arbitrary key-value metadata.

        Returns:
            The CrossWorkspaceCollaboration, or None if either workspace not found.
        """
        if source_workspace_id not in self._workspaces:
            logger.error(f"Source workspace not found: {source_workspace_id}")
            return None
        if target_workspace_id not in self._workspaces:
            logger.error(f"Target workspace not found: {target_workspace_id}")
            return None

        collaboration = CrossWorkspaceCollaboration(
            source_workspace_id=source_workspace_id,
            target_workspace_id=target_workspace_id,
            mode=mode,
            established_by=established_by,
            metadata=metadata or {},
        )
        self._collaborations[collaboration.collaboration_id] = collaboration

        source_ws = self._workspaces[source_workspace_id]
        target_ws = self._workspaces[target_workspace_id]
        source_ws.collaborations.append(collaboration)
        target_ws.collaborations.append(collaboration)
        source_ws.updated_at = datetime.now(timezone.utc).isoformat()
        target_ws.updated_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Collaboration established: {source_workspace_id} <-> {target_workspace_id} "
            f"(mode={mode.value})"
        )
        self._emit_event("workspace.collaboration.established", {
            "collaboration_id": collaboration.collaboration_id,
        })
        return collaboration

    def get_workspace_summary(self) -> dict[str, Any]:
        """Get a summary of all workspaces and collaborations.

        Returns:
            Dictionary with workspace count, member counts, and collaboration stats.
        """
        total_members = sum(len(w.members) for w in self._workspaces.values())
        return {
            "total_workspaces": len(self._workspaces),
            "active_workspaces": sum(1 for w in self._workspaces.values() if w.is_active),
            "total_members": total_members,
            "total_collaborations": len(self._collaborations),
            "total_shared_resources": sum(
                len(w.shared_resources) for w in self._workspaces.values()
            ),
        }

    # ─────────────────────────────────────────────────────────
    # Lifecycle & Events
    # ─────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """Whether the platform orchestrator is currently running."""
        return self._is_running

    def start(self) -> None:
        """Start the platform orchestrator."""
        if self._is_running:
            return
        self._is_running = True
        self._startup_time = datetime.now(timezone.utc).isoformat()
        logger.info("Platform Orchestrator started")
        self._emit_event("platform.started", {"startup_time": self._startup_time})

    def stop(self) -> None:
        """Gracefully stop the platform orchestrator."""
        if not self._is_running:
            return
        self._is_running = False
        logger.info("Platform Orchestrator stopped")
        self._emit_event("platform.stopped", {
            "stop_time": datetime.now(timezone.utc).isoformat()
        })

    def on_event(self, event_type: str, callback: Callable[..., None]) -> None:
        """Register a listener for a platform event type.

        Args:
            event_type: The event type to listen for (e.g. "service.registered").
            callback: Function to call when the event occurs.
        """
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event to all registered listeners.

        Args:
            event_type: The event type.
            data: Event payload data.
        """
        listeners = self._event_listeners.get(event_type, [])
        for callback in listeners:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event listener for '{event_type}': {e}")

    def get_platform_status(self) -> dict[str, Any]:
        """Get a comprehensive status report of the entire platform.

        Returns:
            Dictionary with status of all subsystems.
        """
        return {
            "is_running": self._is_running,
            "startup_time": self._startup_time,
            "service_registry": self.get_service_stats(),
            "workflow_engine": {
                "total_workflows": len(self._workflows),
                "total_templates": len(self._templates),
                "active_executions": len(self._executions),
                "execution_history_count": len(self._execution_history),
            },
            "integration_hub": self.get_integration_summary(),
            "publishing_pipeline": {
                "total_content": len(self._published_content),
                "by_state": self._content_state_breakdown(),
            },
            "analytics": self.get_platform_analytics_summary(),
            "workspaces": self.get_workspace_summary(),
        }

    def _content_state_breakdown(self) -> dict[str, int]:
        """Get a breakdown of content by publishing state."""
        breakdown: dict[str, int] = {}
        for content in self._published_content.values():
            s = content.state.value
            breakdown[s] = breakdown.get(s, 0) + 1
        return breakdown

    def reset(self) -> None:
        """Reset the platform orchestrator to its initial state.

        Clears all registrations, workflows, executions, integrations,
        content, metrics, workspaces, and all other state.
        """
        self._services.clear()
        self._workflows.clear()
        self._executions.clear()
        self._templates.clear()
        self._execution_history.clear()
        self._trigger_listeners.clear()
        self._integrations.clear()
        self._webhooks.clear()
        self._rate_limiters.clear()
        self._quota_trackers.clear()
        self._published_content.clear()
        self._publishing_schedules.clear()
        self._metrics.clear()
        self._usage_records.clear()
        self._performance_alerts.clear()
        self._cost_reports.clear()
        self._optimization_suggestions.clear()
        self._workspaces.clear()
        self._collaborations.clear()
        self._event_listeners.clear()
        self._is_running = False
        self._startup_time = ""
        logger.info("Platform Orchestrator reset to initial state")


# ═══════════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════════

_platform_orchestrator: PlatformOrchestrator | None = None


def get_platform_orchestrator() -> PlatformOrchestrator:
    """Get the global singleton PlatformOrchestrator instance.

    Creates the instance on first call and returns the same instance
    on subsequent calls.

    Returns:
        The global PlatformOrchestrator singleton.
    """
    global _platform_orchestrator
    if _platform_orchestrator is None:
        _platform_orchestrator = PlatformOrchestrator()
    return _platform_orchestrator


def reset_platform_orchestrator() -> None:
    """Reset the global singleton PlatformOrchestrator instance.

    Calls reset() on the singleton, clearing all state. The instance
    is preserved but returned to its initial state.
    """
    global _platform_orchestrator
    if _platform_orchestrator is not None:
        _platform_orchestrator.reset()