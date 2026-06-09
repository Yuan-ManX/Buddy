"""
Buddy Pulse — Health Monitoring and Metrics Collection System

Provides comprehensive health monitoring, performance metrics collection,
anomaly detection, and system status aggregation for the Buddy AI-native
agent platform. Monitors heartbeats, latencies, error rates, and resource
usage across all subsystems.

Key features:
- Heartbeat tracking for all registered components
- Percentile latency calculation and tracking
- Error rate monitoring and alerting
- Resource metrics collection (memory, connections, queues)
- System-wide health status aggregation
- Simple anomaly detection based on threshold deviations
"""

from __future__ import annotations
import logging
import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from collections import deque

# psutil is optional; system resource metrics are skipped if unavailable
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None  # type: ignore

logger = logging.getLogger("buddy.pulse")


class HealthStatus(str, Enum):
    """Overall health status of a component or the entire system."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ComponentHealth:
    """Health information for a single registered component."""
    component_id: str
    name: str
    status: HealthStatus
    last_heartbeat: str  # ISO format timestamp
    latency_p50_ms: float
    latency_p99_ms: float
    error_rate: float  # Errors per minute
    uptime_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PulseMetric:
    """A single metric data point recorded from a component."""
    name: str
    value: float
    unit: str
    timestamp: str  # ISO format timestamp
    component_id: str


@dataclass
class SystemHealth:
    """Aggregated health status for the entire system."""
    overall_status: HealthStatus
    components: list[ComponentHealth]
    total_uptime_seconds: float
    active_components: int
    degraded_components: int
    unhealthy_components: int
    recent_alerts: list[str] = field(default_factory=list)


class ComponentMetrics:
    """Internal storage for metrics from a single component."""

    def __init__(self, max_latency_samples: int = 1000):
        self.started_at: float = datetime.now(timezone.utc).timestamp()
        self.last_heartbeat: float = datetime.now(timezone.utc).timestamp()
        self.latencies: deque[float] = deque(maxlen=max_latency_samples)
        self.errors: deque[float] = deque(maxlen=1000)  # Timestamps of errors
        self.custom_metrics: list[PulseMetric] = []
        self.total_errors: int = 0

    def record_heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = datetime.now(timezone.utc).timestamp()

    def record_latency(self, duration_ms: float) -> None:
        """Record a latency measurement."""
        self.latencies.append(duration_ms)

    def record_error(self) -> None:
        """Record an error occurrence."""
        now = datetime.now(timezone.utc).timestamp()
        self.errors.append(now)
        self.total_errors += 1


class BuddyPulse:
    """Main health monitoring and metrics collection system.

    BuddyPulse monitors all registered subsystems, tracks performance
    metrics, detects anomalies, and aggregates overall system health.
    """

    def __init__(
        self,
        max_latency_samples: int = 1000,
        heartbeat_timeout_seconds: float = 120,
        max_alerts: int = 100,
    ):
        self._components: dict[str, ComponentMetrics] = {}
        self._component_names: dict[str, str] = {}
        self._start_time: float = datetime.now(timezone.utc).timestamp()
        self._max_latency_samples = max_latency_samples
        self._heartbeat_timeout = heartbeat_timeout_seconds
        self._max_alerts = max_alerts
        self._recent_alerts: deque[str] = deque(maxlen=max_alerts)
        self._monitoring_task: asyncio.Task | None = None
        self._monitoring_interval = 30
        self._monitoring_running = False

        # Thresholds for anomaly detection
        self._thresholds: dict[str, dict[str, float]] = {
            "latency_p99_ms": {"warning": 1000, "critical": 5000},
            "error_rate_per_min": {"warning": 5, "critical": 20},
            "heartbeat_stale_seconds": {"warning": 30, "critical": 120},
        }

    def register_component(self, component_id: str, name: str) -> ComponentHealth:
        """Register a new component for monitoring.

        Args:
            component_id: Unique identifier for the component
            name: Human-readable name for display

        Returns:
            Initial ComponentHealth for the registered component
        """
        if component_id in self._components:
            logger.warning(f"Component {component_id} already registered, reinitializing")

        self._components[component_id] = ComponentMetrics(
            max_latency_samples=self._max_latency_samples
        )
        self._component_names[component_id] = name

        logger.info(f"Component registered: {component_id} ({name})")
        return self.get_component_health(component_id)

    def heartbeat(self, component_id: str) -> bool:
        """Record a heartbeat from a component.

        Args:
            component_id: Component identifier

        Returns:
            True if component exists and heartbeat was recorded, False otherwise
        """
        component = self._components.get(component_id)
        if not component:
            return False

        component.record_heartbeat()
        return True

    def record_latency(self, component_id: str, operation_name: str, duration_ms: float) -> None:
        """Record an operation latency measurement.

        Args:
            component_id: Component identifier
            operation_name: Name of the operation (not stored per-operation currently)
            duration_ms: Operation duration in milliseconds
        """
        component = self._components.get(component_id)
        if not component:
            logger.debug(f"Cannot record latency: component {component_id} not registered")
            return

        component.record_latency(duration_ms)

    def record_error(self, component_id: str, error_type: str) -> None:
        """Record an error occurrence.

        Args:
            component_id: Component identifier
            error_type: Type/classification of the error (for future aggregation)
        """
        component = self._components.get(component_id)
        if not component:
            logger.debug(f"Cannot record error: component {component_id} not registered")
            return

        component.record_error()
        logger.debug(f"Error recorded for {component_id} ({error_type})")

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        component_id: str,
    ) -> None:
        """Record a custom metric.

        Args:
            name: Metric name
            value: Numeric value
            unit: Unit of measurement (e.g., "mb", "connections", "percent")
            component_id: Component that recorded this metric
        """
        component = self._components.get(component_id)
        if not component:
            logger.debug(f"Cannot record metric: component {component_id} not registered")
            return

        metric = PulseMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(timezone.utc).isoformat(),
            component_id=component_id,
        )
        component.custom_metrics.append(metric)
        # Keep last 1000 custom metrics per component
        if len(component.custom_metrics) > 1000:
            component.custom_metrics = component.custom_metrics[-1000:]

    def get_component_health(self, component_id: str) -> ComponentHealth | None:
        """Get current health for a specific component.

        Args:
            component_id: Component identifier

        Returns:
            ComponentHealth if component exists, None otherwise
        """
        component = self._components.get(component_id)
        if not component:
            return None

        name = self._component_names[component_id]
        now = datetime.now(timezone.utc).timestamp()
        uptime = now - component.started_at
        latency_stats = self._calculate_percentiles(list(component.latencies))
        error_stats = self._calculate_error_rate(component)

        # Determine status based on multiple factors
        status = self._determine_component_status(component_id, component)

        return ComponentHealth(
            component_id=component_id,
            name=name,
            status=status,
            last_heartbeat=datetime.fromtimestamp(
                component.last_heartbeat, tz=timezone.utc
            ).isoformat(),
            latency_p50_ms=latency_stats.get("p50", 0.0),
            latency_p99_ms=latency_stats.get("p99", 0.0),
            error_rate=error_stats["rate_per_minute"],
            uptime_seconds=uptime,
            metadata={},
        )

    def get_system_health(self) -> SystemHealth:
        """Get aggregated health status for the entire system.

        Aggregation rules:
        - HEALTHY: All components are healthy
        - DEGRADED: Any component is degraded, none unhealthy
        - UNHEALTHY: Any component is unhealthy
        - CRITICAL: Multiple components are unhealthy

        Returns:
            SystemHealth with overall status and per-component details
        """
        components = [
            self.get_component_health(cid)
            for cid in self._components.keys()
        ]
        components = [ch for ch in components if ch is not None]

        active = sum(1 for ch in components if ch.status == HealthStatus.HEALTHY)
        degraded = sum(1 for ch in components if ch.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for ch in components if ch.status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL))

        # Determine overall status according to rules
        if unhealthy > 1:
            overall = HealthStatus.CRITICAL
        elif unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        now = datetime.now(timezone.utc).timestamp()
        total_uptime = now - self._start_time

        return SystemHealth(
            overall_status=overall,
            components=components,
            total_uptime_seconds=total_uptime,
            active_components=active,
            degraded_components=degraded,
            unhealthy_components=unhealthy,
            recent_alerts=list(self._recent_alerts),
        )

    def get_latency_stats(self, component_id: str) -> dict[str, float]:
        """Get detailed latency statistics (p50, p90, p95, p99, max).

        Args:
            component_id: Component identifier

        Returns:
            Dictionary with percentile values, empty if no data or component
        """
        component = self._components.get(component_id)
        if not component or not component.latencies:
            return {
                "p50": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "max": 0.0,
            }

        return self._calculate_percentiles(list(component.latencies))

    def get_error_stats(self, component_id: str) -> dict[str, float]:
        """Get error statistics (total, rate per minute).

        Args:
            component_id: Component identifier

        Returns:
            Dictionary with total errors and current rate
        """
        component = self._components.get(component_id)
        if not component:
            return {"total": 0.0, "rate_per_minute": 0.0}

        return self._calculate_error_rate(component)

    def check_anomalies(self) -> list[str]:
        """Check all metrics for anomalies and return alert messages.

        Checks for:
        - Stale heartbeats beyond warning/critical thresholds
        - P99 latency exceeding warning/critical thresholds
        - Error rate exceeding warning/critical thresholds

        Returns:
            List of alert messages for detected anomalies
        """
        alerts = []
        now = datetime.now(timezone.utc).timestamp()

        for component_id, component in self._components.items():
            name = self._component_names[component_id]

            # Check for stale heartbeat
            heartbeat_age = now - component.last_heartbeat
            if heartbeat_age > self._thresholds["heartbeat_stale_seconds"]["critical"]:
                alert = f"CRITICAL: {name} ({component_id}) has not sent a heartbeat in {heartbeat_age:.1f}s"
                alerts.append(alert)
                self._add_alert(alert)
            elif heartbeat_age > self._thresholds["heartbeat_stale_seconds"]["warning"]:
                alert = f"WARNING: {name} ({component_id}) heartbeat is stale ({heartbeat_age:.1f}s)"
                alerts.append(alert)
                self._add_alert(alert)

            # Check latency
            if component.latencies:
                latency_stats = self._calculate_percentiles(list(component.latencies))
                p99 = latency_stats["p99"]
                if p99 > self._thresholds["latency_p99_ms"]["critical"]:
                    alert = f"CRITICAL: {name} ({component_id}) p99 latency is {p99:.1f}ms (threshold {self._thresholds['latency_p99_ms']['critical']}ms)"
                    alerts.append(alert)
                    self._add_alert(alert)
                elif p99 > self._thresholds["latency_p99_ms"]["warning"]:
                    alert = f"WARNING: {name} ({component_id}) p99 latency is {p99:.1f}ms (threshold {self._thresholds['latency_p99_ms']['warning']}ms)"
                    alerts.append(alert)
                    self._add_alert(alert)

            # Check error rate
            error_stats = self._calculate_error_rate(component)
            rate = error_stats["rate_per_minute"]
            if rate > self._thresholds["error_rate_per_min"]["critical"]:
                alert = f"CRITICAL: {name} ({component_id}) error rate is {rate:.1f}/min (threshold {self._thresholds['error_rate_per_min']['critical']}/min)"
                alerts.append(alert)
                self._add_alert(alert)
            elif rate > self._thresholds["error_rate_per_min"]["warning"]:
                alert = f"WARNING: {name} ({component_id}) error rate is {rate:.1f}/min (threshold {self._thresholds['error_rate_per_min']['warning']}/min)"
                alerts.append(alert)
                self._add_alert(alert)

        return alerts

    def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start background asynchronous monitoring.

        Runs periodic anomaly detection and resource monitoring at the
        specified interval. This should be called once at system startup.

        Args:
            interval_seconds: Interval between monitoring runs
        """
        if self._monitoring_running:
            logger.warning("Monitoring already running")
            return

        self._monitoring_interval = interval_seconds
        self._monitoring_running = True
        logger.info(f"Starting background monitoring with interval {interval_seconds}s")

        # Note: This creates an async task that should be awaited in the main loop.
        # The caller is responsible for having an active async event loop.
        try:
            loop = asyncio.get_event_loop()
            self._monitoring_task = loop.create_task(self._monitoring_loop())
        except RuntimeError:
            logger.warning("No running event loop, monitoring task not started")
            self._monitoring_running = False

    def stop_monitoring(self) -> None:
        """Stop the background monitoring task."""
        self._monitoring_running = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            logger.info("Background monitoring stopped")
        self._monitoring_task = None

    async def _monitoring_loop(self) -> None:
        """Internal background monitoring loop."""
        while self._monitoring_running:
            try:
                # Record system resource metrics
                self._collect_system_metrics()

                # Check for anomalies
                alerts = self.check_anomalies()
                if alerts:
                    logger.info(f"Anomaly check found {len(alerts)} alerts")

                # Check memory usage and record it
                if HAS_PSUTIL:
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    self.record_metric("memory_rss_mb", memory_mb, "mb", "system")

                # Give hints about overall status
                system_health = self.get_system_health()
                if system_health.overall_status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
                    logger.warning(
                        f"System health: {system_health.overall_status.value}, "
                        f"{system_health.unhealthy_components} unhealthy components"
                    )

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)

            try:
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                logger.debug("Monitoring loop cancelled")
                break

    def _collect_system_metrics(self) -> None:
        """Collect system-level resource metrics.

        Requires psutil to be installed. Silently skips collection otherwise.
        """
        if not HAS_PSUTIL:
            return

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self.record_metric("cpu_usage_percent", cpu_percent, "percent", "system")

        # System memory
        mem = psutil.virtual_memory()
        self.record_metric("system_memory_used_percent", mem.percent, "percent", "system")
        self.record_metric("system_memory_available_mb", mem.available / (1024 * 1024), "mb", "system")

        # Load averages
        load = psutil.getloadavg()
        self.record_metric("load_average_1m", load[0], "count", "system")
        self.record_metric("load_average_5m", load[1], "count", "system")

    def _add_alert(self, alert: str) -> None:
        """Add an alert to the recent alerts list."""
        self._recent_alerts.append(alert)

    def _determine_component_status(self, component_id: str, component: ComponentMetrics) -> HealthStatus:
        """Determine component status based on current metrics."""
        now = datetime.now(timezone.utc).timestamp()
        heartbeat_age = now - component.last_heartbeat
        alerts = 0
        critical = 0

        # Check heartbeat
        if heartbeat_age > self._thresholds["heartbeat_stale_seconds"]["critical"]:
            critical += 1
        elif heartbeat_age > self._thresholds["heartbeat_stale_seconds"]["warning"]:
            alerts += 1

        # Check latency
        if component.latencies:
            stats = self._calculate_percentiles(list(component.latencies))
            p99 = stats["p99"]
            if p99 > self._thresholds["latency_p99_ms"]["critical"]:
                critical += 1
            elif p99 > self._thresholds["latency_p99_ms"]["warning"]:
                alerts += 1

        # Check error rate
        error_stats = self._calculate_error_rate(component)
        rate = error_stats["rate_per_minute"]
        if rate > self._thresholds["error_rate_per_min"]["critical"]:
            critical += 1
        elif rate > self._thresholds["error_rate_per_min"]["warning"]:
            alerts += 1

        # Determine status based on counts
        if critical > 0:
            return HealthStatus.UNHEALTHY if critical == 1 else HealthStatus.CRITICAL
        elif alerts > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    @staticmethod
    def _calculate_percentiles(values: list[float]) -> dict[str, float]:
        """Calculate common percentiles from a list of values.

        Uses linear interpolation between nearest ranks for accuracy.
        """
        if not values:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        max_val = sorted_vals[-1]

        def get_percentile(p: float) -> float:
            """Get percentile p (0-100)."""
            if n == 0:
                return 0.0
            if n == 1:
                return sorted_vals[0]

            index = (p / 100) * (n - 1)
            floor_idx = math.floor(index)
            ceil_idx = math.ceil(index)

            if floor_idx == ceil_idx:
                return sorted_vals[int(index)]

            weight = index - floor_idx
            return (
                (1 - weight) * sorted_vals[int(floor_idx)] +
                weight * sorted_vals[int(ceil_idx)]
            )

        return {
            "p50": get_percentile(50),
            "p90": get_percentile(90),
            "p95": get_percentile(95),
            "p99": get_percentile(99),
            "max": max_val,
        }

    @staticmethod
    def _calculate_error_rate(component: ComponentMetrics) -> dict[str, float]:
        """Calculate error rate per minute over the sliding window."""
        if not component.errors:
            return {"total": float(component.total_errors), "rate_per_minute": 0.0}

        now = datetime.now(timezone.utc).timestamp()
        # Consider errors from last 10 minutes
        window_start = now - (10 * 60)
        recent_errors = [ts for ts in component.errors if ts > window_start]

        if not recent_errors:
            return {"total": float(component.total_errors), "rate_per_minute": 0.0}

        window_minutes = (now - window_start) / 60
        rate = len(recent_errors) / window_minutes

        return {"total": float(component.total_errors), "rate_per_minute": rate}


# Global singleton instance
pulse_system = BuddyPulse()
