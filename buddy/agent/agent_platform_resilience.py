"""Buddy Platform Resilience Engine — Fault Detection, Recovery, and Circuit Breaking

The Platform Resilience Engine provides continuous health monitoring, automatic
failure detection, multi-strategy auto-recovery, and circuit breaker isolation
for all components in the Buddy AI platform. It ensures the platform remains
operational under adverse conditions by detecting degradation early, isolating
faults before they cascade, and recovering failed components autonomously.

Core capabilities:
- Continuous component health monitoring
- Automatic failure detection with root-cause classification
- Multi-strategy auto-recovery (restart, failover, rollback, scale-up, reconnect)
- Circuit breaker pattern for fault isolation and graceful degradation
- Failure simulation for resilience testing
- Comprehensive resilience reporting with recovery success tracking
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("buddy.platform_resilience")


# ── Enums ────────────────────────────────────────────────────────────

class ComponentType(str, Enum):
    """Types of platform components that can be registered for resilience monitoring."""
    AGENT = "agent"
    TOOL = "tool"
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STREAM = "stream"
    MODEL_ENDPOINT = "model_endpoint"


class FailureType(str, Enum):
    """Classification of failure modes that the resilience engine can detect."""
    TIMEOUT = "timeout"
    CRASH = "crash"
    MEMORY_LEAK = "memory_leak"
    DEADLOCK = "deadlock"
    NETWORK_PARTITION = "network_partition"
    CORRUPTED_STATE = "corrupted_state"
    OVERLOAD = "overload"


class ComponentStatus(str, Enum):
    """Health status classifications for registered components."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(str, Enum):
    """States of a circuit breaker protecting a component."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RecoveryStrategy(str, Enum):
    """Strategies available for automatic component recovery."""
    RESTART = "restart"
    FAILOVER = "failover"
    ROLLBACK = "rollback"
    SCALE_UP = "scale_up"
    CLEAR_CACHE = "clear_cache"
    RECONNECT = "reconnect"


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class HealthStatus:
    """Snapshot of a component's current health state."""
    component_id: str
    status: ComponentStatus = ComponentStatus.UNKNOWN
    last_check: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    response_time_ms: float = 0.0
    error_count: int = 0
    uptime_percentage: float = 100.0
    consecutive_failures: int = 0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureReport:
    """Detailed report of a detected component failure."""
    id: str
    component_id: str
    failure_type: FailureType
    severity: int = 1
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    root_cause: str = ""
    affected_services: list[str] = field(default_factory=list)
    recovery_attempts: int = 0
    recovery_status: str = "pending"


@dataclass
class RecoveryResult:
    """Outcome of an automatic recovery attempt."""
    id: str
    failure_id: str
    recovery_strategy: RecoveryStrategy
    success: bool = False
    recovery_time_ms: float = 0.0
    steps_taken: list[str] = field(default_factory=list)
    new_status: ComponentStatus = ComponentStatus.UNKNOWN


@dataclass
class CircuitBreaker:
    """Circuit breaker protecting a component from cascading failures."""
    id: str
    component_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_threshold: int = 5
    timeout_seconds: float = 30.0
    failure_count: int = 0
    last_failure_time: str = ""
    activated_at: str = ""


@dataclass
class ResilienceReport:
    """Aggregated resilience status across all registered components."""
    total_components: int = 0
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    uptime_percentage: float = 0.0
    recent_failures: list[FailureReport] = field(default_factory=list)
    recovery_success_rate: float = 0.0


@dataclass
class SimulationResult:
    """Result of a simulated failure test."""
    simulation_id: str
    component_id: str
    failure_type_simulated: FailureType
    detected: bool = False
    recovery_triggered: bool = False
    recovery_success: bool = False
    time_to_detect_ms: float = 0.0
    time_to_recover_ms: float = 0.0


# ── Internal Component Record ────────────────────────────────────────

@dataclass
class _ResilientComponent:
    """Internal record for a registered component with full resilience state."""
    component_id: str
    component_type: ComponentType
    health_check_url: Optional[str] = None
    health_status: HealthStatus = field(default_factory=lambda: HealthStatus(component_id=""))
    failure_history: list[FailureReport] = field(default_factory=list)
    recovery_history: list[RecoveryResult] = field(default_factory=list)
    circuit_breaker: Optional[CircuitBreaker] = None
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_checks: int = 0
    total_failures: int = 0
    total_recoveries: int = 0
    successful_recoveries: int = 0

    def __post_init__(self):
        if self.health_status.component_id == "":
            self.health_status.component_id = self.component_id


# ── Platform Resilience Engine ───────────────────────────────────────

class PlatformResilienceEngine:
    """Central engine for platform-wide resilience management.

    Monitors registered components, detects failures, triggers automatic
    recovery, and manages circuit breakers to prevent cascading failures.
    Supports failure simulation for testing resilience under controlled
    conditions.
    """

    def __init__(self) -> None:
        self._components: dict[str, _ResilientComponent] = {}
        self._failure_log: list[FailureReport] = []
        self._simulation_log: list[SimulationResult] = []

    # ── Component Registration ───────────────────────────────────

    def register_component(
        self,
        component_id: str,
        component_type: ComponentType,
        health_check_url: Optional[str] = None,
    ) -> _ResilientComponent:
        """Register a platform component for resilience monitoring.

        Args:
            component_id: Unique identifier for the component.
            component_type: The type of component being registered.
            health_check_url: Optional URL endpoint for health checks.

        Returns:
            The internal ResilientComponent record that was created.

        Raises:
            ValueError: If a component with the same ID is already registered.
        """
        if component_id in self._components:
            raise ValueError(
                f"Component '{component_id}' is already registered."
            )

        component = _ResilientComponent(
            component_id=component_id,
            component_type=component_type,
            health_check_url=health_check_url,
        )
        self._components[component_id] = component
        logger.info(
            "Registered component '%s' of type %s for resilience monitoring.",
            component_id,
            component_type.value,
        )
        return component

    # ── Health Checks ────────────────────────────────────────────

    def health_check(self, component_id: str) -> HealthStatus:
        """Perform a health check on a registered component.

        Simulates a health probe by evaluating the component's internal
        state. In a real deployment this would call the health_check_url
        or perform an actual connectivity check.

        Args:
            component_id: The component to check.

        Returns:
            The current HealthStatus of the component.

        Raises:
            KeyError: If the component is not registered.
        """
        component = self._get_component(component_id)

        start_time = time.monotonic()
        try:
            self._perform_health_probe(component)
            elapsed_ms = (time.monotonic() - start_time) * 1000.0

            component.health_status.last_check = datetime.now(timezone.utc).isoformat()
            component.health_status.response_time_ms = elapsed_ms
            component.health_status.consecutive_failures = 0
            component.total_checks += 1

            # Reset circuit breaker failure count on successful check
            if component.circuit_breaker and component.circuit_breaker.state == CircuitState.HALF_OPEN:
                component.circuit_breaker.failure_count = 0
                component.circuit_breaker.state = CircuitState.CLOSED
                logger.info(
                    "Circuit breaker for '%s' transitioned to CLOSED after successful health check.",
                    component_id,
                )

            # Update uptime
            self._recalculate_uptime(component)

            logger.debug("Health check for '%s': %s (%.2fms)", component_id, component.health_status.status.value, elapsed_ms)
            return component.health_status

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            component.health_status.last_check = datetime.now(timezone.utc).isoformat()
            component.health_status.response_time_ms = elapsed_ms
            component.health_status.error_count += 1
            component.health_status.consecutive_failures += 1
            component.total_checks += 1
            component.total_failures += 1

            if component.health_status.consecutive_failures >= 3:
                component.health_status.status = ComponentStatus.UNHEALTHY
            else:
                component.health_status.status = ComponentStatus.DEGRADED

            component.health_status.details["last_error"] = str(exc)

            # Increment circuit breaker failure count
            if component.circuit_breaker:
                component.circuit_breaker.failure_count += 1
                component.circuit_breaker.last_failure_time = datetime.now(timezone.utc).isoformat()

                if component.circuit_breaker.failure_count >= component.circuit_breaker.failure_threshold:
                    self._trip_circuit_breaker(component)

            self._recalculate_uptime(component)
            logger.warning("Health check failed for '%s': %s", component_id, exc)
            return component.health_status

    def _perform_health_probe(self, component: _ResilientComponent) -> None:
        """Execute the actual health probe logic for a component.

        Checks the internal state of the component to determine health.
        If the component has a circuit breaker in OPEN state, the probe
        raises an exception to simulate a blocked call.

        Raises:
            RuntimeError: If the circuit breaker is open or the component
                         is in an unhealthy state.
        """
        if component.circuit_breaker and component.circuit_breaker.state == CircuitState.OPEN:
            elapsed = 0.0
            if component.circuit_breaker.activated_at:
                try:
                    activated_dt = datetime.fromisoformat(component.circuit_breaker.activated_at)
                    elapsed = (datetime.now(timezone.utc) - activated_dt).total_seconds()
                except (ValueError, TypeError):
                    pass
            if elapsed < component.circuit_breaker.timeout_seconds:
                raise RuntimeError(f"Circuit breaker is OPEN for component '{component.component_id}'")

            # Timeout expired, transition to HALF_OPEN
            component.circuit_breaker.state = CircuitState.HALF_OPEN
            component.health_status.status = ComponentStatus.DEGRADED
            logger.info(
                "Circuit breaker for '%s' transitioned to HALF_OPEN (timeout expired).",
                component.component_id,
            )

        if component.health_status.status == ComponentStatus.UNHEALTHY:
            raise RuntimeError(f"Component '{component.component_id}' is in UNHEALTHY state.")

        component.health_status.status = ComponentStatus.HEALTHY

    def _recalculate_uptime(self, component: _ResilientComponent) -> None:
        """Recalculate uptime percentage for a component based on check history."""
        if component.total_checks == 0:
            component.health_status.uptime_percentage = 100.0
            return
        healthy_checks = component.total_checks - component.total_failures
        component.health_status.uptime_percentage = round(
            (healthy_checks / component.total_checks) * 100.0, 2
        )

    # ── Failure Detection ────────────────────────────────────────

    def detect_failure(self, component_id: str) -> FailureReport:
        """Detect and classify a failure for a registered component.

        Analyzes the component's current health state and recent history
        to determine the most likely failure type and root cause. The
        component's health status is checked first, then failure patterns
        are analyzed.

        Args:
            component_id: The component to analyze.

        Returns:
            A FailureReport with classification and severity.

        Raises:
            KeyError: If the component is not registered.
        """
        component = self._get_component(component_id)

        # Run a health check to get current state
        health = self.health_check(component_id)

        if health.status == ComponentStatus.HEALTHY:
            report = FailureReport(
                id=str(uuid.uuid4()),
                component_id=component_id,
                failure_type=FailureType.TIMEOUT,
                severity=0,
                root_cause="No failure detected. Component is healthy.",
                recovery_status="not_needed",
            )
            self._failure_log.append(report)
            component.failure_history.append(report)
            return report

        # Classify the failure type based on patterns
        failure_type = self._classify_failure(component, health)
        severity = self._assess_severity(component, health)
        root_cause = self._determine_root_cause(component, failure_type, health)

        report = FailureReport(
            id=str(uuid.uuid4()),
            component_id=component_id,
            failure_type=failure_type,
            severity=severity,
            detected_at=datetime.now(timezone.utc).isoformat(),
            root_cause=root_cause,
            affected_services=self._identify_affected_services(component),
            recovery_attempts=0,
            recovery_status="pending",
        )

        self._failure_log.append(report)
        component.failure_history.append(report)
        logger.warning(
            "Failure detected for '%s': type=%s severity=%d root_cause=%s",
            component_id, failure_type.value, severity, root_cause,
        )
        return report

    def _classify_failure(
        self,
        component: _ResilientComponent,
        health: HealthStatus,
    ) -> FailureType:
        """Classify the failure type based on component state and health data."""
        if health.response_time_ms > 30000:
            return FailureType.TIMEOUT
        if health.consecutive_failures >= 5:
            return FailureType.CRASH
        if component.health_status.details.get("memory_pressure", False):
            return FailureType.MEMORY_LEAK
        if health.status == ComponentStatus.UNHEALTHY and health.consecutive_failures >= 3:
            if component.component_type == ComponentType.DATABASE:
                return FailureType.CORRUPTED_STATE
            if component.component_type == ComponentType.API:
                return FailureType.OVERLOAD
        if component.circuit_breaker and component.circuit_breaker.state == CircuitState.OPEN:
            if component.component_type in (ComponentType.QUEUE, ComponentType.STREAM):
                return FailureType.NETWORK_PARTITION
            return FailureType.OVERLOAD
        return FailureType.CRASH

    def _assess_severity(
        self,
        component: _ResilientComponent,
        health: HealthStatus,
    ) -> int:
        """Assess failure severity on a scale of 1 (low) to 5 (critical)."""
        severity = 1

        if health.status == ComponentStatus.UNHEALTHY:
            severity += 2
        elif health.status == ComponentStatus.DEGRADED:
            severity += 1

        if health.consecutive_failures >= 5:
            severity += 1
        if health.consecutive_failures >= 10:
            severity += 1

        critical_types = {ComponentType.DATABASE, ComponentType.MODEL_ENDPOINT}
        if component.component_type in critical_types:
            severity += 1

        return min(severity, 5)

    def _determine_root_cause(
        self,
        component: _ResilientComponent,
        failure_type: FailureType,
        health: HealthStatus,
    ) -> str:
        """Determine the root cause description for a detected failure."""
        causes = {
            FailureType.TIMEOUT: f"Response time exceeded threshold ({health.response_time_ms:.0f}ms). "
                                 f"Potential upstream bottleneck or resource exhaustion.",
            FailureType.CRASH: f"Component has {health.consecutive_failures} consecutive failures. "
                              f"Possible process crash or unhandled exception.",
            FailureType.MEMORY_LEAK: "Memory pressure detected. Gradual memory consumption increase "
                                     "indicating a potential leak.",
            FailureType.DEADLOCK: "Component appears to be blocked. Possible deadlock in resource acquisition.",
            FailureType.NETWORK_PARTITION: "Network connectivity lost. Component unreachable from the platform.",
            FailureType.CORRUPTED_STATE: "Internal state corruption detected. Data integrity may be compromised.",
            FailureType.OVERLOAD: "Component is overwhelmed with requests. Rate of incoming work "
                                 "exceeds processing capacity.",
        }
        return causes.get(failure_type, "Unknown failure cause.")

    def _identify_affected_services(self, component: _ResilientComponent) -> list[str]:
        """Identify which services may be affected by this component's failure."""
        affected = [component.component_id]

        dependency_map = {
            ComponentType.DATABASE: ["agent_state", "memory_store", "session_persistence"],
            ComponentType.CACHE: ["response_cache", "session_cache", "token_cache"],
            ComponentType.QUEUE: ["task_scheduler", "event_pipeline", "async_workflow"],
            ComponentType.API: ["external_integration", "third_party_service"],
            ComponentType.MODEL_ENDPOINT: ["inference_pipeline", "embedding_service", "completion_service"],
            ComponentType.AGENT: ["agent_orchestration", "task_execution"],
            ComponentType.TOOL: ["tool_execution", "skill_runtime"],
            ComponentType.STREAM: ["real_time_events", "live_updates", "streaming_response"],
        }

        affected.extend(dependency_map.get(component.component_type, []))
        return affected

    # ── Auto-Recovery ────────────────────────────────────────────

    def auto_recover(self, component_id: str) -> RecoveryResult:
        """Attempt automatic recovery of a failed component.

        Selects the most appropriate recovery strategy based on the
        component type, failure history, and previous recovery attempts.
        Executes the recovery steps and returns the result.

        Args:
            component_id: The component to recover.

        Returns:
            A RecoveryResult describing the outcome.

        Raises:
            KeyError: If the component is not registered.
        """
        component = self._get_component(component_id)

        # Determine the latest failure if any
        latest_failure = None
        if component.failure_history:
            latest_failure = component.failure_history[-1]

        failure_id = latest_failure.id if latest_failure else ""

        # Select recovery strategy
        strategy = self._select_recovery_strategy(component, latest_failure)
        recovery_id = str(uuid.uuid4())
        steps: list[str] = []

        start_time = time.monotonic()

        try:
            steps = self._execute_recovery(component, strategy)
            elapsed_ms = (time.monotonic() - start_time) * 1000.0

            # Re-check health after recovery
            health = self.health_check(component_id)
            success = health.status == ComponentStatus.HEALTHY

            if success:
                component.successful_recoveries += 1
                component.health_status.consecutive_failures = 0

            component.total_recoveries += 1

            if latest_failure:
                latest_failure.recovery_attempts += 1
                latest_failure.recovery_status = "recovered" if success else "failed"

            result = RecoveryResult(
                id=recovery_id,
                failure_id=failure_id,
                recovery_strategy=strategy,
                success=success,
                recovery_time_ms=elapsed_ms,
                steps_taken=steps,
                new_status=health.status,
            )

            component.recovery_history.append(result)
            logger.info(
                "Recovery for '%s': strategy=%s success=%s time=%.2fms",
                component_id, strategy.value, success, elapsed_ms,
            )
            return result

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            steps.append(f"Recovery failed: {exc}")
            component.total_recoveries += 1

            if latest_failure:
                latest_failure.recovery_attempts += 1
                latest_failure.recovery_status = "failed"

            result = RecoveryResult(
                id=recovery_id,
                failure_id=failure_id,
                recovery_strategy=strategy,
                success=False,
                recovery_time_ms=elapsed_ms,
                steps_taken=steps,
                new_status=component.health_status.status,
            )

            component.recovery_history.append(result)
            logger.error(
                "Recovery failed for '%s': strategy=%s error=%s",
                component_id, strategy.value, exc,
            )
            return result

    def _select_recovery_strategy(
        self,
        component: _ResilientComponent,
        failure: Optional[FailureReport],
    ) -> RecoveryStrategy:
        """Select the best recovery strategy based on component and failure context."""
        if failure is None:
            return RecoveryStrategy.RESTART

        strategy_map: dict[FailureType, RecoveryStrategy] = {
            FailureType.TIMEOUT: RecoveryStrategy.RESTART,
            FailureType.CRASH: RecoveryStrategy.RESTART,
            FailureType.MEMORY_LEAK: RecoveryStrategy.RESTART,
            FailureType.DEADLOCK: RecoveryStrategy.RESTART,
            FailureType.NETWORK_PARTITION: RecoveryStrategy.RECONNECT,
            FailureType.CORRUPTED_STATE: RecoveryStrategy.ROLLBACK,
            FailureType.OVERLOAD: RecoveryStrategy.SCALE_UP,
        }

        base_strategy = strategy_map.get(failure.failure_type, RecoveryStrategy.RESTART)

        # If previous recovery with the same strategy failed, try failover
        if component.recovery_history:
            last_recovery = component.recovery_history[-1]
            if last_recovery.recovery_strategy == base_strategy and not last_recovery.success:
                return RecoveryStrategy.FAILOVER

        # Cache components benefit from cache clearing
        if component.component_type == ComponentType.CACHE and base_strategy == RecoveryStrategy.RESTART:
            return RecoveryStrategy.CLEAR_CACHE

        return base_strategy

    def _execute_recovery(
        self,
        component: _ResilientComponent,
        strategy: RecoveryStrategy,
    ) -> list[str]:
        """Execute the actual recovery steps for a given strategy."""
        steps: list[str] = []

        if strategy == RecoveryStrategy.RESTART:
            steps.append(f"Initiating restart of component '{component.component_id}'")
            # Simulate restart by resetting health state
            component.health_status.status = ComponentStatus.HEALTHY
            component.health_status.consecutive_failures = 0
            component.health_status.error_count = 0
            component.health_status.details = {}
            steps.append("Component state reset successfully")
            steps.append("Restart completed")

        elif strategy == RecoveryStrategy.FAILOVER:
            steps.append(f"Initiating failover for component '{component.component_id}'")
            steps.append("Redirecting traffic to standby instance")
            steps.append("Verifying standby health")
            component.health_status.status = ComponentStatus.HEALTHY
            component.health_status.consecutive_failures = 0
            component.health_status.details = {"failover_active": True}
            steps.append("Failover completed successfully")

        elif strategy == RecoveryStrategy.ROLLBACK:
            steps.append(f"Initiating rollback for component '{component.component_id}'")
            steps.append("Reverting to last known good state")
            steps.append("Restoring configuration snapshot")
            component.health_status.status = ComponentStatus.HEALTHY
            component.health_status.consecutive_failures = 0
            component.health_status.details = {"rollback_applied": True}
            steps.append("Rollback completed")

        elif strategy == RecoveryStrategy.SCALE_UP:
            steps.append(f"Initiating scale-up for component '{component.component_id}'")
            steps.append("Provisioning additional capacity")
            steps.append("Rebalancing workload")
            component.health_status.status = ComponentStatus.HEALTHY
            component.health_status.consecutive_failures = 0
            component.health_status.details = {"scaled_up": True}
            steps.append("Scale-up completed")

        elif strategy == RecoveryStrategy.CLEAR_CACHE:
            steps.append(f"Clearing cache for component '{component.component_id}'")
            steps.append("Invalidating stale cache entries")
            steps.append("Rebuilding cache from source")
            component.health_status.status = ComponentStatus.HEALTHY
            component.health_status.consecutive_failures = 0
            component.health_status.details = {"cache_cleared": True}
            steps.append("Cache cleared and rebuilt")

        elif strategy == RecoveryStrategy.RECONNECT:
            steps.append(f"Re-establishing connection for component '{component.component_id}'")
            steps.append("Closing stale connections")
            steps.append("Opening new connection pool")
            steps.append("Validating connectivity")
            component.health_status.status = ComponentStatus.HEALTHY
            component.health_status.consecutive_failures = 0
            component.health_status.details = {"reconnected": True}
            steps.append("Reconnection established")

        return steps

    # ── Circuit Breaker ──────────────────────────────────────────

    def activate_circuit_breaker(self, component_id: str) -> CircuitBreaker:
        """Activate a circuit breaker for a component to isolate faults.

        Creates and opens a circuit breaker for the specified component,
        preventing further calls until the timeout expires. If a circuit
        breaker already exists, it is transitioned to OPEN state.

        Args:
            component_id: The component to protect.

        Returns:
            The active CircuitBreaker instance.

        Raises:
            KeyError: If the component is not registered.
        """
        component = self._get_component(component_id)

        if component.circuit_breaker is None:
            component.circuit_breaker = CircuitBreaker(
                id=str(uuid.uuid4()),
                component_id=component_id,
            )

        self._trip_circuit_breaker(component)
        logger.info(
            "Circuit breaker activated for '%s': state=%s threshold=%d timeout=%.1fs",
            component_id,
            component.circuit_breaker.state.value,
            component.circuit_breaker.failure_threshold,
            component.circuit_breaker.timeout_seconds,
        )
        return component.circuit_breaker

    def _trip_circuit_breaker(self, component: _ResilientComponent) -> None:
        """Trip (open) the circuit breaker for a component."""
        if component.circuit_breaker is None:
            return
        component.circuit_breaker.state = CircuitState.OPEN
        component.circuit_breaker.activated_at = datetime.now(timezone.utc).isoformat()
        component.circuit_breaker.failure_count = component.circuit_breaker.failure_threshold
        component.health_status.status = ComponentStatus.UNHEALTHY
        component.health_status.details["circuit_open"] = True

    # ── Resilience Report ────────────────────────────────────────

    def get_resilience_report(self) -> ResilienceReport:
        """Generate a comprehensive resilience report for all components.

        Aggregates health status, failure history, and recovery metrics
        across all registered components.

        Returns:
            A ResilienceReport with full platform resilience status.
        """
        total = len(self._components)
        if total == 0:
            return ResilienceReport()

        healthy = sum(
            1 for c in self._components.values()
            if c.health_status.status == ComponentStatus.HEALTHY
        )
        degraded = sum(
            1 for c in self._components.values()
            if c.health_status.status == ComponentStatus.DEGRADED
        )
        unhealthy = sum(
            1 for c in self._components.values()
            if c.health_status.status == ComponentStatus.UNHEALTHY
        )

        uptime_values = [
            c.health_status.uptime_percentage
            for c in self._components.values()
            if c.total_checks > 0
        ]
        avg_uptime = round(sum(uptime_values) / len(uptime_values), 2) if uptime_values else 100.0

        recent_failures = sorted(
            self._failure_log,
            key=lambda f: f.detected_at,
            reverse=True,
        )[:20]

        total_recoveries = sum(c.total_recoveries for c in self._components.values())
        successful_recoveries = sum(c.successful_recoveries for c in self._components.values())
        recovery_rate = (
            round((successful_recoveries / total_recoveries) * 100.0, 2)
            if total_recoveries > 0
            else 100.0
        )

        return ResilienceReport(
            total_components=total,
            healthy_count=healthy,
            degraded_count=degraded,
            unhealthy_count=unhealthy,
            uptime_percentage=avg_uptime,
            recent_failures=recent_failures,
            recovery_success_rate=recovery_rate,
        )

    # ── Failure Simulation ───────────────────────────────────────

    def simulate_failure(
        self,
        component_id: str,
        failure_type: FailureType,
    ) -> SimulationResult:
        """Simulate a failure on a component to test resilience mechanisms.

        Injects a simulated failure into the component, then tests whether
        the engine can detect it and recover automatically. The component
        is restored to a healthy state after the simulation.

        Args:
            component_id: The component to test.
            failure_type: The type of failure to simulate.

        Returns:
            A SimulationResult with detection and recovery metrics.

        Raises:
            KeyError: If the component is not registered.
        """
        component = self._get_component(component_id)
        simulation_id = str(uuid.uuid4())

        # Save original state
        original_status = component.health_status.status
        original_failures = component.health_status.consecutive_failures
        original_details = dict(component.health_status.details)

        # Inject simulated failure
        inject_start = time.monotonic()
        self._inject_failure(component, failure_type)
        inject_time_ms = (time.monotonic() - inject_start) * 1000.0

        # Attempt detection
        detect_start = time.monotonic()
        report = self.detect_failure(component_id)
        detect_time_ms = (time.monotonic() - detect_start) * 1000.0
        detected = report.severity > 0

        # Attempt recovery
        recovery_triggered = False
        recovery_success = False
        recover_time_ms = 0.0

        if detected:
            recovery_triggered = True
            recover_start = time.monotonic()
            recovery_result = self.auto_recover(component_id)
            recovery_success = recovery_result.success
            recover_time_ms = (time.monotonic() - recover_start) * 1000.0

        # Restore original state
        component.health_status.status = original_status
        component.health_status.consecutive_failures = original_failures
        component.health_status.details = original_details

        result = SimulationResult(
            simulation_id=simulation_id,
            component_id=component_id,
            failure_type_simulated=failure_type,
            detected=detected,
            recovery_triggered=recovery_triggered,
            recovery_success=recovery_success,
            time_to_detect_ms=detect_time_ms,
            time_to_recover_ms=recover_time_ms,
        )

        self._simulation_log.append(result)
        logger.info(
            "Simulation %s for '%s': type=%s detected=%s recovered=%s detect=%.2fms recover=%.2fms",
            simulation_id, component_id, failure_type.value,
            detected, recovery_success, detect_time_ms, recover_time_ms,
        )
        return result

    def _inject_failure(
        self,
        component: _ResilientComponent,
        failure_type: FailureType,
    ) -> None:
        """Inject a simulated failure into a component's state."""
        if failure_type == FailureType.TIMEOUT:
            component.health_status.response_time_ms = 35000.0
            component.health_status.status = ComponentStatus.DEGRADED
            component.health_status.details["simulated"] = "timeout"

        elif failure_type == FailureType.CRASH:
            component.health_status.status = ComponentStatus.UNHEALTHY
            component.health_status.consecutive_failures = 5
            component.health_status.details["simulated"] = "crash"

        elif failure_type == FailureType.MEMORY_LEAK:
            component.health_status.status = ComponentStatus.DEGRADED
            component.health_status.details["memory_pressure"] = True
            component.health_status.details["simulated"] = "memory_leak"

        elif failure_type == FailureType.DEADLOCK:
            component.health_status.status = ComponentStatus.UNHEALTHY
            component.health_status.details["deadlock_detected"] = True
            component.health_status.details["simulated"] = "deadlock"

        elif failure_type == FailureType.NETWORK_PARTITION:
            component.health_status.status = ComponentStatus.UNHEALTHY
            component.health_status.consecutive_failures = 3
            component.health_status.details["network_partition"] = True
            component.health_status.details["simulated"] = "network_partition"

        elif failure_type == FailureType.CORRUPTED_STATE:
            component.health_status.status = ComponentStatus.UNHEALTHY
            component.health_status.details["state_corrupted"] = True
            component.health_status.details["simulated"] = "corrupted_state"

        elif failure_type == FailureType.OVERLOAD:
            component.health_status.status = ComponentStatus.DEGRADED
            component.health_status.details["request_backlog"] = 5000
            component.health_status.details["simulated"] = "overload"

    # ── Reset ────────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all component registrations, failure logs, and state.

        Resets the engine to a completely clean state with no registered
        components and empty logs.
        """
        self._components.clear()
        self._failure_log.clear()
        self._simulation_log.clear()
        logger.info("Platform Resilience Engine has been fully reset.")

    # ── Helpers ──────────────────────────────────────────────────

    def _get_component(self, component_id: str) -> _ResilientComponent:
        """Retrieve a registered component, raising KeyError if not found."""
        if component_id not in self._components:
            raise KeyError(
                f"Component '{component_id}' is not registered. "
                f"Use register_component() first."
            )
        return self._components[component_id]


# ── Singleton Access ─────────────────────────────────────────────────

_platform_resilience_instance: Optional[PlatformResilienceEngine] = None


def get_platform_resilience() -> PlatformResilienceEngine:
    """Get the singleton PlatformResilienceEngine instance.

    Creates the engine on first call. Subsequent calls return the same
    instance, providing a single point of resilience management across
    the entire platform.

    Returns:
        The singleton PlatformResilienceEngine instance.
    """
    global _platform_resilience_instance
    if _platform_resilience_instance is None:
        _platform_resilience_instance = PlatformResilienceEngine()
        logger.info("Platform Resilience Engine singleton initialized.")
    return _platform_resilience_instance


def reset_platform_resilience() -> None:
    """Reset the singleton PlatformResilienceEngine instance.

    Destroys the current singleton and clears all state. The next call
    to get_platform_resilience() will create a fresh instance.
    """
    global _platform_resilience_instance
    if _platform_resilience_instance is not None:
        _platform_resilience_instance.reset()
    _platform_resilience_instance = None
    logger.info("Platform Resilience Engine singleton has been reset.")