from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import math


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class AnomalyType(str, Enum):
    """Types of anomalies detectable within the Buddy agent runtime."""
    OUTPUT_DRIFT = "output_drift"
    LATENCY_SPIKE = "latency_spike"
    ERROR_RATE = "error_rate"
    TOOL_FAILURE = "tool_failure"
    HALLUCINATION_PATTERN = "hallucination_pattern"
    BEHAVIORAL_DEVIATION = "behavioral_deviation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONTEXT_COLLAPSE = "context_collapse"
    REASONING_BREAKDOWN = "reasoning_breakdown"
    CALIBRATION_LOSS = "calibration_loss"


class AnomalySeverity(str, Enum):
    """Severity classifications for detected anomaly events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BaselineStatus(str, Enum):
    """Lifecycle status of a per-agent behavioral baseline."""
    LEARNING = "learning"
    STABLE = "stable"
    ADAPTING = "adapting"
    DEGRADED = "degraded"


class DiagnosisStatus(str, Enum):
    """Status of a self-diagnosis investigation tied to an anomaly."""
    PENDING = "pending"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class MetricDirection(str, Enum):
    """Expected directional behavior for a tracked metric."""
    INCREASE = "increase"
    DECREASE = "decrease"
    BIDIRECTIONAL = "bidirectional"


# ═══════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════

@dataclass
class BehaviorMetric:
    """A single tracked behavioral metric within an agent baseline.

    Baseline statistics (mean and standard deviation) are maintained
    incrementally via Welford's algorithm as new observations arrive.
    """

    metric_id: str
    name: str
    description: str
    direction: MetricDirection
    unit: str
    baseline_mean: float
    baseline_std: float
    sample_count: int
    last_value: float | None
    last_updated: float
    is_anomalous: bool
    observations: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the metric to a plain dictionary.

        Enum fields are reduced to their ``.value``, and the observation
        history is copied into a fresh list to avoid external mutation.
        """
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "description": self.description,
            "direction": self.direction.value if isinstance(self.direction, MetricDirection) else self.direction,
            "unit": self.unit,
            "baseline_mean": self.baseline_mean,
            "baseline_std": self.baseline_std,
            "sample_count": self.sample_count,
            "last_value": self.last_value,
            "last_updated": self.last_updated,
            "is_anomalous": self.is_anomalous,
            "observations": list(self.observations),
        }


@dataclass
class BehaviorBaseline:
    """A per-agent behavioral baseline aggregating multiple tracked metrics."""

    baseline_id: str
    agent_id: str
    metrics: dict[str, BehaviorMetric] = field(default_factory=dict)
    status: BaselineStatus = BaselineStatus.LEARNING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    sample_window: int = 100
    min_samples: int = 30

    def to_dict(self) -> dict[str, Any]:
        """Serialize the baseline to a plain dictionary.

        Nested metrics are serialized recursively, the metrics mapping is
        rebuilt as a fresh dictionary, and enum fields are reduced to their
        ``.value``.
        """
        return {
            "baseline_id": self.baseline_id,
            "agent_id": self.agent_id,
            "metrics": {name: metric.to_dict() for name, metric in self.metrics.items()},
            "status": self.status.value if isinstance(self.status, BaselineStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sample_window": self.sample_window,
            "min_samples": self.min_samples,
        }


@dataclass
class AnomalyEvent:
    """A single detected anomaly event tied to a specific metric observation."""

    anomaly_id: str
    agent_id: str
    metric_name: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    observed_value: float
    expected_value: float
    z_score: float
    deviation_pct: float
    timestamp: float
    context: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize the anomaly event to a plain dictionary.

        Enum fields are reduced to their ``.value`` and the context mapping
        is copied to a fresh dictionary to prevent external mutation.
        """
        return {
            "anomaly_id": self.anomaly_id,
            "agent_id": self.agent_id,
            "metric_name": self.metric_name,
            "anomaly_type": self.anomaly_type.value if isinstance(self.anomaly_type, AnomalyType) else self.anomaly_type,
            "severity": self.severity.value if isinstance(self.severity, AnomalySeverity) else self.severity,
            "observed_value": self.observed_value,
            "expected_value": self.expected_value,
            "z_score": self.z_score,
            "deviation_pct": self.deviation_pct,
            "timestamp": self.timestamp,
            "context": dict(self.context),
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
        }


@dataclass
class DriftReport:
    """A report summarizing sustained behavioral drift over a time window."""

    report_id: str
    agent_id: str
    start_time: float
    end_time: float
    drifted_metrics: list[str] = field(default_factory=list)
    avg_deviation: float = 0.0
    trend_direction: str = "stable"
    severity: AnomalySeverity = AnomalySeverity.WARNING
    sample_count: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the drift report to a plain dictionary.

        The drifted-metrics list and details mapping are copied into fresh
        containers, and the severity enum is reduced to its ``.value``.
        """
        return {
            "report_id": self.report_id,
            "agent_id": self.agent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "drifted_metrics": list(self.drifted_metrics),
            "avg_deviation": self.avg_deviation,
            "trend_direction": self.trend_direction,
            "severity": self.severity.value if isinstance(self.severity, AnomalySeverity) else self.severity,
            "sample_count": self.sample_count,
            "details": dict(self.details),
        }


@dataclass
class DiagnosisReport:
    """A self-diagnosis report investigating the root cause of an anomaly."""

    diagnosis_id: str
    anomaly_id: str
    agent_id: str
    status: DiagnosisStatus = DiagnosisStatus.PENDING
    root_cause: str = ""
    contributing_factors: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    resolved_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the diagnosis report to a plain dictionary.

        Enum fields are reduced to their ``.value``, and the contributing
        factors and recommended actions lists are copied into fresh lists.
        """
        return {
            "diagnosis_id": self.diagnosis_id,
            "anomaly_id": self.anomaly_id,
            "agent_id": self.agent_id,
            "status": self.status.value if isinstance(self.status, DiagnosisStatus) else self.status,
            "root_cause": self.root_cause,
            "contributing_factors": list(self.contributing_factors),
            "recommended_actions": list(self.recommended_actions),
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class AnomalyEngineStats:
    """Aggregate statistics describing the overall state of the anomaly engine."""

    total_baselines: int = 0
    total_metrics_tracked: int = 0
    total_anomalies: int = 0
    active_anomalies: int = 0
    critical_anomalies: int = 0
    total_drift_reports: int = 0
    total_diagnoses: int = 0
    resolved_diagnoses: int = 0
    avg_z_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the engine statistics to a plain dictionary."""
        return {
            "total_baselines": self.total_baselines,
            "total_metrics_tracked": self.total_metrics_tracked,
            "total_anomalies": self.total_anomalies,
            "active_anomalies": self.active_anomalies,
            "critical_anomalies": self.critical_anomalies,
            "total_drift_reports": self.total_drift_reports,
            "total_diagnoses": self.total_diagnoses,
            "resolved_diagnoses": self.resolved_diagnoses,
            "avg_z_score": self.avg_z_score,
        }


# ═══════════════════════════════════════════════════════════
# Anomaly Detector
# ═══════════════════════════════════════════════════════════

class AgentAnomalyDetector:
    """Behavioral anomaly detection and self-diagnosis engine for the Buddy agent.

    The detector maintains per-agent behavioral baselines composed of named
    metrics. As observations are recorded, baseline statistics are updated
    incrementally (Welford's algorithm) and point anomalies are flagged when
    the standardized distance of an observation from its baseline exceeds a
    configurable threshold. Sustained drift is identified by comparing the
    mean of a recent observation window against the established baseline.

    Self-diagnosis workflows allow the agent (or an operator) to investigate
    flagged anomalies, record root-cause hypotheses, propose remediation
    actions, and ultimately resolve or close out the investigation.

    All public operations are thread-safe; mutations of internal state are
    guarded by a single reentrant-capable lock acquired on every call.
    """

    # Numerical guard to avoid division-by-zero when standard deviation is zero.
    _EPSILON: float = 1e-9

    def __init__(self) -> None:
        """Initialize an empty anomaly detector with default thresholds."""
        self._baselines: dict[str, BehaviorBaseline] = {}
        self._anomalies: list[AnomalyEvent] = []
        self._drift_reports: list[DriftReport] = []
        self._diagnoses: dict[str, DiagnosisReport] = {}
        self._lock = threading.Lock()

        # Bounded retention limits to prevent unbounded memory growth.
        self.MAX_ANOMALIES: int = 5000
        self.MAX_DRIFT_REPORTS: int = 1000

        # Z-score thresholds governing anomaly detection and severity grading.
        self.Z_SCORE_THRESHOLD: float = 2.5
        self.CRITICAL_Z_SCORE: float = 4.0

    # ───────────────────────────────────────────────────────
    # Baseline management
    # ───────────────────────────────────────────────────────

    def create_baseline(
        self,
        agent_id: str,
        sample_window: int = 100,
        min_samples: int = 30,
    ) -> BehaviorBaseline:
        """Create a new behavioral baseline for the given agent.

        If a baseline already exists for the agent it is replaced with a
        fresh one. The returned baseline starts in the ``LEARNING`` status
        until enough samples have been recorded for statistical inference.

        Args:
            agent_id: Identifier of the agent the baseline belongs to.
            sample_window: Maximum number of recent observations retained
                per metric for drift analysis.
            min_samples: Minimum number of observations required before
                anomaly detection is enabled for a metric.

        Returns:
            The newly created :class:`BehaviorBaseline`.
        """
        with self._lock:
            now = time.time()
            baseline = BehaviorBaseline(
                baseline_id=f"bl-{uuid.uuid4().hex[:12]}",
                agent_id=agent_id,
                status=BaselineStatus.LEARNING,
                created_at=now,
                updated_at=now,
                sample_window=sample_window,
                min_samples=min_samples,
            )
            self._baselines[agent_id] = baseline
            return baseline

    def get_baseline(self, agent_id: str) -> BehaviorBaseline | None:
        """Return the baseline for ``agent_id`` or ``None`` if none exists."""
        with self._lock:
            return self._baselines.get(agent_id)

    def list_baselines(self) -> list[BehaviorBaseline]:
        """Return a list of all registered baselines (snapshot copy)."""
        with self._lock:
            return list(self._baselines.values())

    def register_metric(
        self,
        agent_id: str,
        name: str,
        description: str = "",
        direction: MetricDirection = MetricDirection.BIDIRECTIONAL,
        unit: str = "",
    ) -> BehaviorMetric | None:
        """Register a metric to track for an agent's baseline.

        If no baseline exists for the agent, ``None`` is returned. If a
        metric with the same name is already registered, the existing
        metric is returned unchanged.

        Args:
            agent_id: Identifier of the agent whose baseline should track
                the metric.
            name: Unique name of the metric within the baseline.
            description: Optional human-readable description of the metric.
            direction: Expected directional behavior of the metric.
            unit: Optional unit label (e.g. ``"ms"``, ``"count"``).

        Returns:
            The registered :class:`BehaviorMetric`, or ``None`` if no
            baseline exists for the agent.
        """
        with self._lock:
            baseline = self._baselines.get(agent_id)
            if baseline is None:
                return None
            if name in baseline.metrics:
                return baseline.metrics[name]
            now = time.time()
            metric = BehaviorMetric(
                metric_id=f"bm-{uuid.uuid4().hex[:12]}",
                name=name,
                description=description,
                direction=direction,
                unit=unit,
                baseline_mean=0.0,
                baseline_std=0.0,
                sample_count=0,
                last_value=None,
                last_updated=now,
                is_anomalous=False,
            )
            baseline.metrics[name] = metric
            baseline.updated_at = now
            if baseline.status == BaselineStatus.STABLE:
                baseline.status = BaselineStatus.LEARNING
            return metric

    # ───────────────────────────────────────────────────────
    # Observation recording and anomaly detection
    # ───────────────────────────────────────────────────────

    def record_observation(
        self,
        agent_id: str,
        metric_name: str,
        value: float,
        context: dict[str, Any] | None = None,
    ) -> AnomalyEvent | None:
        """Record an observation, update baseline stats, and detect anomalies.

        Baseline statistics (mean and standard deviation) are updated
        incrementally using Welford's algorithm. When the metric has
        accumulated at least ``min_samples`` observations and a non-zero
        standard deviation, the z-score of the new observation is computed.
        If the absolute z-score exceeds :attr:`Z_SCORE_THRESHOLD` an
        :class:`AnomalyEvent` is created, stored, and returned.

        Args:
            agent_id: Identifier of the agent whose metric is being observed.
            metric_name: Name of the metric being observed.
            value: The observed metric value.
            context: Optional contextual metadata attached to any anomaly
                generated from this observation.

        Returns:
            An :class:`AnomalyEvent` if the observation is anomalous, else
            ``None``. Also returns ``None`` if no baseline or metric exists.
        """
        with self._lock:
            baseline = self._baselines.get(agent_id)
            if baseline is None:
                return None
            metric = baseline.metrics.get(metric_name)
            if metric is None:
                return None

            now = time.time()
            self._update_baseline_stats(metric, value)

            metric.last_value = value
            metric.last_updated = now
            metric.observations.append(value)
            if len(metric.observations) > baseline.sample_window:
                # Trim to the most recent observations within the window.
                excess = len(metric.observations) - baseline.sample_window
                del metric.observations[:excess]

            baseline.updated_at = now
            self._refresh_baseline_status(baseline, metric)

            anomaly: AnomalyEvent | None = None
            if (
                metric.sample_count >= baseline.min_samples
                and metric.baseline_std > 0.0
            ):
                z_score = (value - metric.baseline_mean) / (metric.baseline_std + self._EPSILON)
                if abs(z_score) > self.Z_SCORE_THRESHOLD:
                    severity = self._classify_severity(abs(z_score))
                    anomaly_type = self._infer_anomaly_type(metric_name)
                    deviation_pct = self._compute_deviation_pct(
                        value, metric.baseline_mean
                    )
                    anomaly = AnomalyEvent(
                        anomaly_id=f"an-{uuid.uuid4().hex[:12]}",
                        agent_id=agent_id,
                        metric_name=metric_name,
                        anomaly_type=anomaly_type,
                        severity=severity,
                        observed_value=value,
                        expected_value=metric.baseline_mean,
                        z_score=z_score,
                        deviation_pct=deviation_pct,
                        timestamp=now,
                        context=dict(context) if context else {},
                    )
                    metric.is_anomalous = True
                    self._anomalies.append(anomaly)
                    if len(self._anomalies) > self.MAX_ANOMALIES:
                        excess = len(self._anomalies) - self.MAX_ANOMALIES
                        del self._anomalies[:excess]
                else:
                    metric.is_anomalous = False
            return anomaly

    def _update_baseline_stats(self, metric: BehaviorMetric, value: float) -> None:
        """Incrementally update a metric's mean/std using Welford's algorithm.

        The second central moment (M2) is reconstructed from the stored
        sample standard deviation prior to the update so that the dataclass
        does not need to persist the accumulator explicitly.
        """
        previous_count = metric.sample_count
        new_count = previous_count + 1

        if previous_count == 0:
            metric.baseline_mean = value
            metric.baseline_std = 0.0
            metric.sample_count = new_count
            return

        # Reconstruct M2 from the sample standard deviation.
        if previous_count > 1:
            m2 = metric.baseline_std ** 2 * (previous_count - 1)
        else:
            m2 = 0.0

        delta = value - metric.baseline_mean
        new_mean = metric.baseline_mean + delta / new_count
        delta2 = value - new_mean
        m2 += delta * delta2

        metric.baseline_mean = new_mean
        metric.baseline_std = math.sqrt(m2 / (new_count - 1)) if new_count > 1 else 0.0
        metric.sample_count = new_count

    def _refresh_baseline_status(
        self, baseline: BehaviorBaseline, metric: BehaviorMetric
    ) -> None:
        """Update the baseline status based on the latest metric state.

        A baseline stays in ``LEARNING`` until its metrics have collected
        sufficient samples, transitions to ``STABLE`` once enough samples
        are present, and is marked ``DEGRADED`` if the most recent
        observation was flagged as anomalous.
        """
        if metric.is_anomalous:
            baseline.status = BaselineStatus.DEGRADED
            return
        if metric.sample_count < baseline.min_samples:
            if baseline.status == BaselineStatus.STABLE:
                baseline.status = BaselineStatus.LEARNING
        else:
            if baseline.status == BaselineStatus.LEARNING:
                baseline.status = BaselineStatus.STABLE

    def _classify_severity(self, abs_z_score: float) -> AnomalySeverity:
        """Map an absolute z-score to an anomaly severity level."""
        if abs_z_score > self.CRITICAL_Z_SCORE:
            return AnomalySeverity.CRITICAL
        if abs_z_score > 3.5:
            return AnomalySeverity.ERROR
        if abs_z_score > 2.5:
            return AnomalySeverity.WARNING
        return AnomalySeverity.INFO

    def _infer_anomaly_type(self, metric_name: str) -> AnomalyType:
        """Heuristically infer the anomaly type from the metric name."""
        name_lower = metric_name.lower()
        if any(token in name_lower for token in ("latency", "duration", "elapsed", "time", "rtt")):
            return AnomalyType.LATENCY_SPIKE
        if any(token in name_lower for token in ("error", "exception", "failure_rate")):
            return AnomalyType.ERROR_RATE
        if any(token in name_lower for token in ("tool", "function_call", "invoke")):
            return AnomalyType.TOOL_FAILURE
        if any(token in name_lower for token in ("halluc", "fabrication", "invention")):
            return AnomalyType.HALLUCINATION_PATTERN
        if any(token in name_lower for token in ("memory", "cpu", "gpu", "resource", "disk", "token")):
            return AnomalyType.RESOURCE_EXHAUSTION
        if any(token in name_lower for token in ("context", "window", "retention")):
            return AnomalyType.CONTEXT_COLLAPSE
        if any(token in name_lower for token in ("reason", "logic", "inference", "chain")):
            return AnomalyType.REASONING_BREAKDOWN
        if any(token in name_lower for token in ("calib", "confidence", "score")):
            return AnomalyType.CALIBRATION_LOSS
        if any(token in name_lower for token in ("drift", "output", "response", "generation")):
            return AnomalyType.OUTPUT_DRIFT
        return AnomalyType.BEHAVIORAL_DEVIATION

    def _compute_deviation_pct(self, observed: float, expected: float) -> float:
        """Compute the percentage deviation of an observation from its baseline."""
        if abs(expected) < self._EPSILON:
            return 0.0
        return ((observed - expected) / abs(expected)) * 100.0

    def detect_drift(self, agent_id: str, window_size: int = 20) -> DriftReport | None:
        """Compare recent observations against baseline to detect sustained drift.

        For each metric with at least ``window_size`` recent observations,
        the mean of the recent window is compared against the established
        baseline mean. Metrics whose recent-mean z-score exceeds a relaxed
        threshold (80% of :attr:`Z_SCORE_THRESHOLD`) are considered to have
        drifted. If at least one metric has drifted, a :class:`DriftReport`
        is generated and stored.

        Args:
            agent_id: Identifier of the agent to analyze.
            window_size: Number of recent observations to consider.

        Returns:
            A :class:`DriftReport` if drift is detected, else ``None``.
        """
        with self._lock:
            baseline = self._baselines.get(agent_id)
            if baseline is None:
                return None

            drifted_metrics: list[str] = []
            per_metric_deviations: list[float] = []
            trends: list[str] = []
            per_metric_details: dict[str, Any] = {}

            for name, metric in baseline.metrics.items():
                if len(metric.observations) < window_size:
                    continue
                if metric.baseline_std <= 0.0:
                    continue
                recent = metric.observations[-window_size:]
                recent_mean = sum(recent) / len(recent)
                z_score = abs(
                    (recent_mean - metric.baseline_mean)
                    / (metric.baseline_std + self._EPSILON)
                )
                drift_threshold = self.Z_SCORE_THRESHOLD * 0.8
                if z_score <= drift_threshold:
                    continue

                drifted_metrics.append(name)
                deviation_pct = self._compute_deviation_pct(
                    recent_mean, metric.baseline_mean
                )
                per_metric_deviations.append(abs(deviation_pct))
                if recent_mean > metric.baseline_mean:
                    trends.append("increasing")
                elif recent_mean < metric.baseline_mean:
                    trends.append("decreasing")
                else:
                    trends.append("stable")
                per_metric_details[name] = {
                    "recent_mean": recent_mean,
                    "baseline_mean": metric.baseline_mean,
                    "z_score": z_score,
                    "deviation_pct": deviation_pct,
                }

            if not drifted_metrics:
                return None

            avg_deviation = (
                sum(per_metric_deviations) / len(per_metric_deviations)
                if per_metric_deviations
                else 0.0
            )
            trend_direction = self._summarize_trend(trends)
            severity = self._classify_drift_severity(avg_deviation)
            now = time.time()
            report = DriftReport(
                report_id=f"dr-{uuid.uuid4().hex[:12]}",
                agent_id=agent_id,
                start_time=now,
                end_time=now,
                drifted_metrics=drifted_metrics,
                avg_deviation=avg_deviation,
                trend_direction=trend_direction,
                severity=severity,
                sample_count=len(drifted_metrics),
                details=per_metric_details,
            )
            self._drift_reports.append(report)
            if len(self._drift_reports) > self.MAX_DRIFT_REPORTS:
                excess = len(self._drift_reports) - self.MAX_DRIFT_REPORTS
                del self._drift_reports[:excess]
            baseline.status = BaselineStatus.ADAPTING
            baseline.updated_at = now
            return report

    def _summarize_trend(self, trends: list[str]) -> str:
        """Reduce a list of per-metric trends to a single summary direction."""
        if not trends:
            return "stable"
        increasing = trends.count("increasing")
        decreasing = trends.count("decreasing")
        if increasing == decreasing:
            return "mixed"
        if increasing > decreasing:
            return "increasing"
        return "decreasing"

    def _classify_drift_severity(self, avg_deviation: float) -> AnomalySeverity:
        """Classify the severity of a drift report from its average deviation."""
        if avg_deviation > 100.0:
            return AnomalySeverity.CRITICAL
        if avg_deviation > 50.0:
            return AnomalySeverity.ERROR
        if avg_deviation > 20.0:
            return AnomalySeverity.WARNING
        return AnomalySeverity.INFO

    # ───────────────────────────────────────────────────────
    # Anomaly lifecycle
    # ───────────────────────────────────────────────────────

    def get_anomaly(self, anomaly_id: str) -> AnomalyEvent | None:
        """Return the anomaly event with the given id, or ``None``."""
        with self._lock:
            for anomaly in self._anomalies:
                if anomaly.anomaly_id == anomaly_id:
                    return anomaly
            return None

    def list_anomalies(
        self,
        agent_id: str | None = None,
        severity: AnomalySeverity | None = None,
        resolved: bool | None = None,
        limit: int = 100,
    ) -> list[AnomalyEvent]:
        """List anomaly events filtered by optional criteria.

        Results are returned in reverse-chronological order (most recent
        first) and capped at ``limit`` entries.

        Args:
            agent_id: Restrict results to the given agent.
            severity: Restrict results to the given severity.
            resolved: Filter by resolved state (``True``/``False``).
            limit: Maximum number of anomalies to return.
        """
        with self._lock:
            results: list[AnomalyEvent] = []
            for anomaly in reversed(self._anomalies):
                if agent_id is not None and anomaly.agent_id != agent_id:
                    continue
                if severity is not None and anomaly.severity != severity:
                    continue
                if resolved is not None and anomaly.resolved != resolved:
                    continue
                results.append(anomaly)
                if len(results) >= limit:
                    break
            return results

    def acknowledge_anomaly(self, anomaly_id: str) -> bool:
        """Mark an anomaly as acknowledged. Returns ``True`` on success."""
        with self._lock:
            anomaly = self._find_anomaly(anomaly_id)
            if anomaly is None:
                return False
            anomaly.acknowledged = True
            return True

    def resolve_anomaly(self, anomaly_id: str) -> bool:
        """Mark an anomaly as resolved. Returns ``True`` on success."""
        with self._lock:
            anomaly = self._find_anomaly(anomaly_id)
            if anomaly is None:
                return False
            anomaly.resolved = True
            return True

    def _find_anomaly(self, anomaly_id: str) -> AnomalyEvent | None:
        """Locate an anomaly by id. Caller must hold the lock."""
        for anomaly in self._anomalies:
            if anomaly.anomaly_id == anomaly_id:
                return anomaly
        return None

    # ───────────────────────────────────────────────────────
    # Self-diagnosis workflows
    # ───────────────────────────────────────────────────────

    def start_diagnosis(self, anomaly_id: str) -> DiagnosisReport | None:
        """Create a diagnosis report for an anomaly.

        The diagnosis begins in the ``PENDING`` status awaiting
        investigation. If the referenced anomaly does not exist, ``None``
        is returned.

        Args:
            anomaly_id: Identifier of the anomaly to diagnose.

        Returns:
            A new :class:`DiagnosisReport`, or ``None`` if the anomaly
            cannot be found.
        """
        with self._lock:
            anomaly = self._find_anomaly(anomaly_id)
            if anomaly is None:
                return None
            now = time.time()
            report = DiagnosisReport(
                diagnosis_id=f"dx-{uuid.uuid4().hex[:12]}",
                anomaly_id=anomaly_id,
                agent_id=anomaly.agent_id,
                status=DiagnosisStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            self._diagnoses[report.diagnosis_id] = report
            return report

    def update_diagnosis(
        self,
        diagnosis_id: str,
        root_cause: str = "",
        contributing_factors: list[str] | None = None,
        recommended_actions: list[str] | None = None,
        confidence: float = 0.0,
        status: DiagnosisStatus = DiagnosisStatus.INVESTIGATING,
    ) -> DiagnosisReport | None:
        """Update an existing diagnosis report with new findings.

        If ``status`` is set to ``RESOLVED`` the diagnosis is automatically
        marked resolved (including a resolved timestamp) and the linked
        anomaly is resolved as well.

        Args:
            diagnosis_id: Identifier of the diagnosis to update.
            root_cause: Hypothesized root cause of the anomaly.
            contributing_factors: List of contributing factors.
            recommended_actions: List of recommended remediation actions.
            confidence: Confidence score in ``[0.0, 1.0]``.
            status: New diagnosis status.

        Returns:
            The updated :class:`DiagnosisReport`, or ``None`` if not found.
        """
        with self._lock:
            report = self._diagnoses.get(diagnosis_id)
            if report is None:
                return None
            now = time.time()
            if root_cause:
                report.root_cause = root_cause
            if contributing_factors is not None:
                report.contributing_factors = list(contributing_factors)
            if recommended_actions is not None:
                report.recommended_actions = list(recommended_actions)
            report.confidence = max(0.0, min(1.0, float(confidence)))
            report.status = status
            report.updated_at = now
            if status == DiagnosisStatus.RESOLVED:
                report.resolved_at = now
                anomaly = self._find_anomaly(report.anomaly_id)
                if anomaly is not None:
                    anomaly.resolved = True
            return report

    def resolve_diagnosis(self, diagnosis_id: str, resolution: str = "") -> DiagnosisReport | None:
        """Resolve a diagnosis, optionally recording a root-cause resolution.

        Args:
            diagnosis_id: Identifier of the diagnosis to resolve.
            resolution: Optional textual resolution / root cause summary.

        Returns:
            The resolved :class:`DiagnosisReport`, or ``None`` if not found.
        """
        with self._lock:
            report = self._diagnoses.get(diagnosis_id)
            if report is None:
                return None
            now = time.time()
            if resolution:
                report.root_cause = resolution
            report.status = DiagnosisStatus.RESOLVED
            report.updated_at = now
            report.resolved_at = now
            anomaly = self._find_anomaly(report.anomaly_id)
            if anomaly is not None:
                anomaly.resolved = True
            return report

    def get_diagnosis(self, diagnosis_id: str) -> DiagnosisReport | None:
        """Return the diagnosis report with the given id, or ``None``."""
        with self._lock:
            return self._diagnoses.get(diagnosis_id)

    def list_diagnoses(
        self,
        anomaly_id: str | None = None,
        status: DiagnosisStatus | None = None,
    ) -> list[DiagnosisReport]:
        """List diagnosis reports filtered by optional criteria.

        Args:
            anomaly_id: Restrict results to diagnoses for the given anomaly.
            status: Restrict results to the given diagnosis status.
        """
        with self._lock:
            results: list[DiagnosisReport] = []
            for report in self._diagnoses.values():
                if anomaly_id is not None and report.anomaly_id != anomaly_id:
                    continue
                if status is not None and report.status != status:
                    continue
                results.append(report)
            return results

    # ───────────────────────────────────────────────────────
    # Summaries and statistics
    # ───────────────────────────────────────────────────────

    def get_baseline_summary(self, agent_id: str) -> dict[str, Any]:
        """Return a summary of an agent's baseline health.

        The summary includes the baseline status, the number of tracked
        metrics, how many are currently flagged anomalous, and per-metric
        snapshots of their current baseline statistics.
        """
        with self._lock:
            baseline = self._baselines.get(agent_id)
            if baseline is None:
                return {
                    "agent_id": agent_id,
                    "exists": False,
                    "status": None,
                    "metrics": {},
                }
            anomalous_metrics = [
                name for name, metric in baseline.metrics.items() if metric.is_anomalous
            ]
            metric_summaries: dict[str, Any] = {}
            for name, metric in baseline.metrics.items():
                metric_summaries[name] = {
                    "sample_count": metric.sample_count,
                    "baseline_mean": metric.baseline_mean,
                    "baseline_std": metric.baseline_std,
                    "last_value": metric.last_value,
                    "is_anomalous": metric.is_anomalous,
                    "last_updated": metric.last_updated,
                }
            return {
                "agent_id": agent_id,
                "exists": True,
                "baseline_id": baseline.baseline_id,
                "status": baseline.status.value if isinstance(baseline.status, BaselineStatus) else baseline.status,
                "created_at": baseline.created_at,
                "updated_at": baseline.updated_at,
                "sample_window": baseline.sample_window,
                "min_samples": baseline.min_samples,
                "total_metrics": len(baseline.metrics),
                "anomalous_metrics": list(anomalous_metrics),
                "anomalous_count": len(anomalous_metrics),
                "metrics": metric_summaries,
            }

    def get_stats(self) -> AnomalyEngineStats:
        """Compute and return aggregate statistics for the anomaly engine."""
        with self._lock:
            total_baselines = len(self._baselines)
            total_metrics_tracked = sum(
                len(baseline.metrics) for baseline in self._baselines.values()
            )
            total_anomalies = len(self._anomalies)
            active_anomalies = sum(
                1 for anomaly in self._anomalies if not anomaly.resolved
            )
            critical_anomalies = sum(
                1
                for anomaly in self._anomalies
                if anomaly.severity == AnomalySeverity.CRITICAL and not anomaly.resolved
            )
            total_drift_reports = len(self._drift_reports)
            total_diagnoses = len(self._diagnoses)
            resolved_diagnoses = sum(
                1
                for report in self._diagnoses.values()
                if report.status == DiagnosisStatus.RESOLVED
            )
            if self._anomalies:
                avg_z_score = sum(
                    anomaly.z_score for anomaly in self._anomalies
                ) / len(self._anomalies)
            else:
                avg_z_score = 0.0
            return AnomalyEngineStats(
                total_baselines=total_baselines,
                total_metrics_tracked=total_metrics_tracked,
                total_anomalies=total_anomalies,
                active_anomalies=active_anomalies,
                critical_anomalies=critical_anomalies,
                total_drift_reports=total_drift_reports,
                total_diagnoses=total_diagnoses,
                resolved_diagnoses=resolved_diagnoses,
                avg_z_score=avg_z_score,
            )

    # ───────────────────────────────────────────────────────
    # Maintenance
    # ───────────────────────────────────────────────────────

    def clear(self) -> int:
        """Clear all stored state from the detector.

        Returns:
            The total number of items removed (baselines, anomalies, drift
            reports, and diagnoses).
        """
        with self._lock:
            removed = (
                len(self._baselines)
                + len(self._anomalies)
                + len(self._drift_reports)
                + len(self._diagnoses)
            )
            self._baselines.clear()
            self._anomalies.clear()
            self._drift_reports.clear()
            self._diagnoses.clear()
            return removed


# ═══════════════════════════════════════════════════════════
# Singleton accessors
# ═══════════════════════════════════════════════════════════

_global_anomaly_detector: AgentAnomalyDetector | None = None


def get_anomaly_detector() -> AgentAnomalyDetector:
    """Get or create the global AgentAnomalyDetector singleton instance."""
    global _global_anomaly_detector
    if _global_anomaly_detector is None:
        _global_anomaly_detector = AgentAnomalyDetector()
    return _global_anomaly_detector


def reset_anomaly_detector() -> None:
    """Reset the global AgentAnomalyDetector singleton instance."""
    global _global_anomaly_detector
    _global_anomaly_detector = None
