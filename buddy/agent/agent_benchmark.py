"""Buddy Agent Benchmark & Evaluation Engine — standardized performance scoring,
benchmarking against baselines, and comparative analysis.

The Benchmark Engine provides a unified framework for evaluating agent
performance across multiple dimensions. It supports configurable metric
definitions, weighted scoring, head-to-head agent comparisons, longitudinal
trend analysis, and leaderboard generation.

Core capabilities:
  - Metric Management: register and track configurable metric definitions
  - Evaluation Runs: start, record, complete, and cancel evaluation runs
  - Weighted Scoring: normalize metric values and compute weighted scores
  - Comparative Analysis: compare runs and agents metric-by-metric
  - Trend Analysis: detect improving, stable, declining, or volatile trends
  - Leaderboards: rank agents by aggregated benchmark scores
  - Statistics: aggregate engine-wide and per-benchmark statistics
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.benchmark_engine")


# ═══════════════════════════════════════════════════════════
# Enums and Types
# ═══════════════════════════════════════════════════════════

class MetricCategory(str, Enum):
    """Categories of evaluation metrics."""
    ACCURACY = "accuracy"
    EFFICIENCY = "efficiency"
    LATENCY = "latency"
    COST = "cost"
    QUALITY = "quality"
    SAFETY = "safety"
    ROBUSTNESS = "robustness"
    COHERENCE = "coherence"
    HELPFULNESS = "helpfulness"
    CREATIVITY = "creativity"


class EvaluationStatus(str, Enum):
    """Lifecycle states of an evaluation run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScoreScale(str, Enum):
    """Supported score scales for metric definitions."""
    BINARY = "binary"
    PERCENTAGE = "percentage"
    RATING_5 = "rating_5"
    RATING_10 = "rating_10"
    CONTINUOUS = "continuous"


class ComparisonResult(str, Enum):
    """Outcomes when comparing two runs or agents."""
    SUPERIOR = "superior"
    EQUIVALENT = "equivalent"
    INFERIOR = "inferior"
    INCOMPARABLE = "incomparable"


class BenchmarkType(str, Enum):
    """Types of benchmarks supported by the engine."""
    SINGLE_RUN = "single_run"
    COMPARATIVE = "comparative"
    LONGITUDINAL = "longitudinal"
    A_B_TEST = "a_b_test"
    REGRESSION = "regression"


class TrendDirection(str, Enum):
    """Detected directions for metric trends over time."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class MetricDefinition:
    """Definition of a single evaluation metric.

    A metric definition describes how a particular aspect of agent performance
    is measured, including its scale, range, unit, and relative weight when
    aggregated into a composite score.
    """
    metric_id: str = field(default_factory=lambda: f"metric-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    category: MetricCategory = MetricCategory.QUALITY
    scale: ScoreScale = ScoreScale.CONTINUOUS
    min_value: float = 0.0
    max_value: float = 1.0
    unit: str = ""
    weight: float = 1.0
    aggregation_method: str = "mean"

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "scale": self.scale.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "unit": self.unit,
            "weight": self.weight,
            "aggregation_method": self.aggregation_method,
        }


@dataclass
class MetricResult:
    """A recorded result for a single metric within an evaluation run."""
    result_id: str = field(default_factory=lambda: f"result-{uuid.uuid4().hex[:8]}")
    metric_id: str = ""
    value: float = 0.0
    normalized_score: float = 0.0
    raw_data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "metric_id": self.metric_id,
            "value": self.value,
            "normalized_score": self.normalized_score,
            "raw_data": self.raw_data,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class EvaluationRun:
    """A single evaluation run of an agent against a benchmark."""
    run_id: str = field(default_factory=lambda: f"run-{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    benchmark_id: str = ""
    status: EvaluationStatus = EvaluationStatus.PENDING
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    results: list[MetricResult] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "benchmark_id": self.benchmark_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": [r.to_dict() for r in self.results],
            "context": self.context,
            "error": self.error,
        }


@dataclass
class Benchmark:
    """A benchmark definition with associated metric definitions."""
    benchmark_id: str = field(default_factory=lambda: f"bench-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    benchmark_type: BenchmarkType = BenchmarkType.SINGLE_RUN
    metric_definitions: list[MetricDefinition] = field(default_factory=list)
    baseline_agent_id: str | None = None
    target_score: float | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    total_runs: int = 0
    last_run_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "description": self.description,
            "benchmark_type": self.benchmark_type.value,
            "metric_definitions": [m.to_dict() for m in self.metric_definitions],
            "baseline_agent_id": self.baseline_agent_id,
            "target_score": self.target_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_runs": self.total_runs,
            "last_run_at": self.last_run_at,
        }


@dataclass
class ComparisonReport:
    """A report comparing two evaluation runs metric-by-metric."""
    report_id: str = field(default_factory=lambda: f"cmp-{uuid.uuid4().hex[:8]}")
    benchmark_id: str = ""
    agent_a_id: str = ""
    agent_b_id: str = ""
    run_a_id: str = ""
    run_b_id: str = ""
    results: dict[str, Any] = field(default_factory=dict)
    overall_comparison: ComparisonResult = ComparisonResult.INCOMPARABLE
    score_a: float = 0.0
    score_b: float = 0.0
    summary: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "benchmark_id": self.benchmark_id,
            "agent_a_id": self.agent_a_id,
            "agent_b_id": self.agent_b_id,
            "run_a_id": self.run_a_id,
            "run_b_id": self.run_b_id,
            "results": self.results,
            "overall_comparison": self.overall_comparison.value,
            "score_a": self.score_a,
            "score_b": self.score_b,
            "summary": self.summary,
            "created_at": self.created_at,
        }


@dataclass
class TrendAnalysis:
    """Analysis of how a metric trends over time for an agent."""
    agent_id: str = ""
    metric_id: str = ""
    direction: TrendDirection = TrendDirection.STABLE
    slope: float = 0.0
    confidence: float = 0.0
    data_points: list[tuple[float, float]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "metric_id": self.metric_id,
            "direction": self.direction.value,
            "slope": self.slope,
            "confidence": self.confidence,
            "data_points": self.data_points,
            "summary": self.summary,
        }


@dataclass
class BenchmarkStats:
    """Aggregate statistics for the benchmark engine."""
    total_benchmarks: int = 0
    total_runs: int = 0
    completed_runs: int = 0
    avg_score: float = 0.0
    benchmarks_by_type: dict[str, int] = field(default_factory=dict)
    metric_coverage: dict[str, int] = field(default_factory=dict)
    comparison_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_benchmarks": self.total_benchmarks,
            "total_runs": self.total_runs,
            "completed_runs": self.completed_runs,
            "avg_score": self.avg_score,
            "benchmarks_by_type": self.benchmarks_by_type,
            "metric_coverage": self.metric_coverage,
            "comparison_count": self.comparison_count,
        }


# ═══════════════════════════════════════════════════════════
# Benchmark Engine Implementation
# ═══════════════════════════════════════════════════════════

class AgentBenchmarkEngine:
    """Standardized performance scoring, benchmarking, and comparative analysis.

    The engine maintains an in-memory registry of benchmarks, evaluation runs,
    and comparison reports. All state mutations are guarded by a reentrant
    lock to ensure thread safety.
    """

    MAX_BENCHMARKS = 200
    MAX_RUNS = 5000
    MAX_COMPARISONS = 1000

    # Slope threshold below which a trend is considered stable
    _STABLE_SLOPE_THRESHOLD: float = 1e-9
    # Coefficient of variation above which a trend is considered volatile
    _VOLATILITY_THRESHOLD: float = 0.5

    def __init__(self) -> None:
        self._benchmarks: dict[str, Benchmark] = {}
        self._runs: dict[str, EvaluationRun] = {}
        self._comparisons: dict[str, ComparisonReport] = {}
        self._lock = threading.Lock()
        self._start_time: float = time.monotonic()
        logger.info("AgentBenchmarkEngine initialized")

    # ── Benchmark Management ─────────────────────────────

    def create_benchmark(
        self,
        name: str,
        description: str,
        benchmark_type: BenchmarkType,
        metric_defs: list[MetricDefinition] | None = None,
        baseline_agent_id: str | None = None,
        target_score: float | None = None,
    ) -> Benchmark:
        """Create and register a new benchmark definition."""
        now = time.time()
        benchmark = Benchmark(
            benchmark_id=f"bench-{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            benchmark_type=benchmark_type,
            metric_definitions=list(metric_defs) if metric_defs else [],
            baseline_agent_id=baseline_agent_id,
            target_score=target_score,
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            if len(self._benchmarks) >= self.MAX_BENCHMARKS:
                # Evict the oldest benchmark to stay under the cap
                oldest_id = min(
                    self._benchmarks.keys(),
                    key=lambda bid: self._benchmarks[bid].created_at,
                )
                del self._benchmarks[oldest_id]
                logger.warning("Evicted oldest benchmark %s to stay under cap", oldest_id)

            self._benchmarks[benchmark.benchmark_id] = benchmark
            logger.info("Created benchmark %s (%s)", benchmark.benchmark_id, name)

        return benchmark

    def get_benchmark(self, benchmark_id: str) -> Benchmark | None:
        """Retrieve a benchmark by id."""
        with self._lock:
            return self._benchmarks.get(benchmark_id)

    def update_benchmark(self, benchmark_id: str, **kwargs: Any) -> Benchmark | None:
        """Update mutable fields on an existing benchmark.

        Accepted keyword arguments: name, description, benchmark_type,
        baseline_agent_id, target_score.
        """
        with self._lock:
            benchmark = self._benchmarks.get(benchmark_id)
            if benchmark is None:
                return None

            allowed = {
                "name",
                "description",
                "benchmark_type",
                "baseline_agent_id",
                "target_score",
            }
            for key, value in kwargs.items():
                if key in allowed:
                    setattr(benchmark, key, value)
                else:
                    logger.warning("Ignoring unknown benchmark field: %s", key)

            benchmark.updated_at = time.time()
            return benchmark

    def delete_benchmark(self, benchmark_id: str) -> bool:
        """Delete a benchmark. Returns True if a benchmark was removed."""
        with self._lock:
            if benchmark_id not in self._benchmarks:
                return False
            del self._benchmarks[benchmark_id]
            logger.info("Deleted benchmark %s", benchmark_id)
            return True

    def list_benchmarks(
        self, benchmark_type: BenchmarkType | None = None
    ) -> list[Benchmark]:
        """List benchmarks, optionally filtered by type."""
        with self._lock:
            benchmarks = list(self._benchmarks.values())
        if benchmark_type is not None:
            benchmarks = [b for b in benchmarks if b.benchmark_type == benchmark_type]
        benchmarks.sort(key=lambda b: b.created_at, reverse=True)
        return benchmarks

    # ── Metric Management ────────────────────────────────

    def register_metric(
        self,
        benchmark_id: str,
        name: str,
        description: str,
        category: MetricCategory,
        scale: ScoreScale,
        min_value: float,
        max_value: float,
        unit: str,
        weight: float,
        aggregation_method: str,
    ) -> MetricDefinition:
        """Register a new metric definition on an existing benchmark."""
        metric = MetricDefinition(
            metric_id=f"metric-{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            category=category,
            scale=scale,
            min_value=min_value,
            max_value=max_value,
            unit=unit,
            weight=weight,
            aggregation_method=aggregation_method,
        )

        with self._lock:
            benchmark = self._benchmarks.get(benchmark_id)
            if benchmark is None:
                raise ValueError(f"Benchmark {benchmark_id} not found")
            benchmark.metric_definitions.append(metric)
            benchmark.updated_at = time.time()
            logger.info(
                "Registered metric %s on benchmark %s", metric.metric_id, benchmark_id
            )

        return metric

    # ── Evaluation Runs ──────────────────────────────────

    def start_evaluation(
        self,
        benchmark_id: str,
        agent_id: str,
        context: dict[str, Any] | None = None,
    ) -> EvaluationRun:
        """Start a new evaluation run for an agent against a benchmark."""
        with self._lock:
            benchmark = self._benchmarks.get(benchmark_id)
            if benchmark is None:
                raise ValueError(f"Benchmark {benchmark_id} not found")

            if len(self._runs) >= self.MAX_RUNS:
                # Evict the oldest run to stay under the cap
                oldest_id = min(
                    self._runs.keys(),
                    key=lambda rid: self._runs[rid].started_at,
                )
                del self._runs[oldest_id]
                logger.warning("Evicted oldest run %s to stay under cap", oldest_id)

            run = EvaluationRun(
                run_id=f"run-{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                benchmark_id=benchmark_id,
                status=EvaluationStatus.RUNNING,
                started_at=time.time(),
                context=context or {},
            )
            self._runs[run.run_id] = run

            benchmark.total_runs += 1
            benchmark.last_run_at = run.started_at
            benchmark.updated_at = run.started_at

            logger.info(
                "Started evaluation %s for agent %s on benchmark %s",
                run.run_id,
                agent_id,
                benchmark_id,
            )
            return run

    def record_metric_result(
        self,
        run_id: str,
        metric_id: str,
        value: float,
        raw_data: dict[str, Any] | None = None,
        notes: str = "",
    ) -> MetricResult:
        """Record a metric result against an in-progress evaluation run."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise ValueError(f"Run {run_id} not found")
            if run.status != EvaluationStatus.RUNNING:
                raise ValueError(
                    f"Run {run_id} is not running (status={run.status.value})"
                )

            benchmark = self._benchmarks.get(run.benchmark_id)
            normalized = self._normalize(value, metric_id, benchmark)

            result = MetricResult(
                result_id=f"result-{uuid.uuid4().hex[:8]}",
                metric_id=metric_id,
                value=value,
                normalized_score=normalized,
                raw_data=raw_data or {},
                timestamp=time.time(),
                notes=notes,
            )
            run.results.append(result)
            logger.debug(
                "Recorded metric %s=%.4f (normalized=%.4f) for run %s",
                metric_id,
                value,
                normalized,
                run_id,
            )
            return result

    def complete_evaluation(
        self, run_id: str, error: str | None = None
    ) -> EvaluationRun:
        """Mark an evaluation run as completed or failed."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise ValueError(f"Run {run_id} not found")

            run.completed_at = time.time()
            if error is not None:
                run.status = EvaluationStatus.FAILED
                run.error = error
            else:
                run.status = EvaluationStatus.COMPLETED

            logger.info(
                "Completed evaluation %s with status %s",
                run_id,
                run.status.value,
            )
            return run

    def cancel_evaluation(self, run_id: str) -> EvaluationRun:
        """Cancel an in-progress evaluation run."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise ValueError(f"Run {run_id} not found")

            run.status = EvaluationStatus.CANCELLED
            run.completed_at = time.time()
            logger.info("Cancelled evaluation %s", run_id)
            return run

    def get_run(self, run_id: str) -> EvaluationRun | None:
        """Retrieve an evaluation run by id."""
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(
        self,
        benchmark_id: str | None = None,
        agent_id: str | None = None,
        status: EvaluationStatus | None = None,
        limit: int = 100,
    ) -> list[EvaluationRun]:
        """List evaluation runs with optional filters."""
        with self._lock:
            runs = list(self._runs.values())

        if benchmark_id is not None:
            runs = [r for r in runs if r.benchmark_id == benchmark_id]
        if agent_id is not None:
            runs = [r for r in runs if r.agent_id == agent_id]
        if status is not None:
            runs = [r for r in runs if r.status == status]

        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs[:limit]

    # ── Scoring ──────────────────────────────────────────

    def calculate_score(self, run_id: str) -> float:
        """Compute the weighted normalized score for a run.

        Steps:
          1. Retrieve the run and its benchmark.
          2. Normalize each metric value to 0.0-1.0 based on min/max.
          3. Apply metric weights and return the weighted average.

        Returns 0.0 if the run has no metric results or no metric
        definitions with a positive weight.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise ValueError(f"Run {run_id} not found")

            benchmark = self._benchmarks.get(run.benchmark_id)
            if benchmark is None:
                return 0.0

            # Map metric definitions by id for weight lookup
            defs_by_id: dict[str, MetricDefinition] = {
                md.metric_id: md for md in benchmark.metric_definitions
            }

            results = list(run.results)
            if not results:
                return 0.0

            total_weight = 0.0
            weighted_sum = 0.0

            for result in results:
                md = defs_by_id.get(result.metric_id)
                if md is None:
                    # Fall back to the already-normalized score with unit weight
                    score = max(0.0, min(1.0, result.normalized_score))
                    weight = 1.0
                else:
                    score = self._normalize_with_def(result.value, md)
                    weight = md.weight
                    # Persist the normalized score on the result
                    result.normalized_score = score

                if weight <= 0:
                    continue

                weighted_sum += score * weight
                total_weight += weight

            if total_weight <= 0:
                return 0.0

            return weighted_sum / total_weight

    # ── Comparison ───────────────────────────────────────

    def compare_runs(self, run_a_id: str, run_b_id: str) -> ComparisonReport:
        """Compare two evaluation runs metric-by-metric.

        Steps:
          1. Calculate weighted scores for both runs.
          2. Compare each shared metric's normalized score.
          3. Determine the overall comparison result.
          4. Generate a human-readable summary.
        """
        with self._lock:
            run_a = self._runs.get(run_a_id)
            run_b = self._runs.get(run_b_id)
            if run_a is None:
                raise ValueError(f"Run {run_a_id} not found")
            if run_b is None:
                raise ValueError(f"Run {run_b_id} not found")

            # Compute scores (already inside the lock)
            score_a = self._calculate_score_unlocked(run_a)
            score_b = self._calculate_score_unlocked(run_b)

            results_a = {r.metric_id: r for r in run_a.results}
            results_b = {r.metric_id: r for r in run_b.results}

            metric_comparisons: dict[str, Any] = {}
            superior_count = 0
            inferior_count = 0
            equivalent_count = 0

            for metric_id in set(results_a.keys()) | set(results_b.keys()):
                ra = results_a.get(metric_id)
                rb = results_b.get(metric_id)

                if ra is not None and rb is not None:
                    if ra.normalized_score > rb.normalized_score:
                        result = ComparisonResult.SUPERIOR
                        superior_count += 1
                    elif ra.normalized_score < rb.normalized_score:
                        result = ComparisonResult.INFERIOR
                        inferior_count += 1
                    else:
                        result = ComparisonResult.EQUIVALENT
                        equivalent_count += 1

                    metric_comparisons[metric_id] = {
                        "value_a": ra.value,
                        "value_b": rb.value,
                        "score_a": ra.normalized_score,
                        "score_b": rb.normalized_score,
                        "result": result.value,
                    }
                else:
                    metric_comparisons[metric_id] = {
                        "value_a": ra.value if ra else None,
                        "value_b": rb.value if rb else None,
                        "score_a": ra.normalized_score if ra else None,
                        "score_b": rb.normalized_score if rb else None,
                        "result": ComparisonResult.INCOMPARABLE.value,
                    }

            # Determine overall comparison result
            if superior_count > inferior_count:
                overall = ComparisonResult.SUPERIOR
            elif inferior_count > superior_count:
                overall = ComparisonResult.INFERIOR
            elif superior_count > 0 and superior_count == inferior_count:
                overall = ComparisonResult.EQUIVALENT
            elif equivalent_count > 0 and superior_count == 0 and inferior_count == 0:
                overall = ComparisonResult.EQUIVALENT
            else:
                overall = ComparisonResult.INCOMPARABLE

            summary = (
                f"Agent A ({run_a.agent_id}) score={score_a:.4f}, "
                f"Agent B ({run_b.agent_id}) score={score_b:.4f}. "
                f"Overall: {overall.value}. "
                f"Metrics — superior={superior_count}, "
                f"equivalent={equivalent_count}, inferior={inferior_count}."
            )

            report = ComparisonReport(
                report_id=f"cmp-{uuid.uuid4().hex[:8]}",
                benchmark_id=run_a.benchmark_id,
                agent_a_id=run_a.agent_id,
                agent_b_id=run_b.agent_id,
                run_a_id=run_a_id,
                run_b_id=run_b_id,
                results=metric_comparisons,
                overall_comparison=overall,
                score_a=score_a,
                score_b=score_b,
                summary=summary,
                created_at=time.time(),
            )

            if len(self._comparisons) >= self.MAX_COMPARISONS:
                oldest_id = min(
                    self._comparisons.keys(),
                    key=lambda cid: self._comparisons[cid].created_at,
                )
                del self._comparisons[oldest_id]
                logger.warning(
                    "Evicted oldest comparison %s to stay under cap", oldest_id
                )

            self._comparisons[report.report_id] = report
            logger.info(
                "Generated comparison report %s (%s)",
                report.report_id,
                overall.value,
            )
            return report

    def compare_agents(
        self,
        benchmark_id: str,
        agent_a_id: str,
        agent_b_id: str,
    ) -> ComparisonReport:
        """Compare two agents on a benchmark using their latest completed runs."""
        with self._lock:
            runs = list(self._runs.values())

        runs_a = [
            r
            for r in runs
            if r.benchmark_id == benchmark_id
            and r.agent_id == agent_a_id
            and r.status == EvaluationStatus.COMPLETED
        ]
        runs_b = [
            r
            for r in runs
            if r.benchmark_id == benchmark_id
            and r.agent_id == agent_b_id
            and r.status == EvaluationStatus.COMPLETED
        ]

        if not runs_a:
            raise ValueError(
                f"No completed runs found for agent {agent_a_id} on benchmark {benchmark_id}"
            )
        if not runs_b:
            raise ValueError(
                f"No completed runs found for agent {agent_b_id} on benchmark {benchmark_id}"
            )

        run_a = max(runs_a, key=lambda r: r.started_at)
        run_b = max(runs_b, key=lambda r: r.started_at)
        return self.compare_runs(run_a.run_id, run_b.run_id)

    # ── Trend Analysis ───────────────────────────────────

    def analyze_trend(
        self,
        agent_id: str,
        metric_id: str,
        window: int = 10,
    ) -> TrendAnalysis:
        """Analyze the trend of a metric for an agent over recent runs.

        Steps:
          1. Gather historical completed runs for the agent.
          2. Extract (timestamp, value) data points for the metric.
          3. Fit a simple linear regression to compute the slope.
          4. Classify the direction (improving/stable/declining/volatile).
          5. Estimate confidence from R^2 and sample size.
        """
        with self._lock:
            runs = [
                r
                for r in self._runs.values()
                if r.agent_id == agent_id
                and r.status == EvaluationStatus.COMPLETED
            ]

        runs.sort(key=lambda r: r.started_at)
        runs = runs[-window:]

        data_points: list[tuple[float, float]] = []
        for run in runs:
            for result in run.results:
                if result.metric_id == metric_id:
                    data_points.append((run.started_at, result.value))

        if len(data_points) < 2:
            return TrendAnalysis(
                agent_id=agent_id,
                metric_id=metric_id,
                direction=TrendDirection.STABLE,
                slope=0.0,
                confidence=0.0,
                data_points=data_points,
                summary=(
                    f"Insufficient data ({len(data_points)} point(s)) "
                    f"to compute a trend for metric {metric_id}."
                ),
            )

        n = len(data_points)
        xs = [p[0] for p in data_points]
        ys = [p[1] for p in data_points]

        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        sum_x2 = sum(x * x for x in xs)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator

        intercept = (sum_y - slope * sum_x) / n if n > 0 else 0.0
        mean_y = sum_y / n

        # Total sum of squares and residual sum of squares for R^2
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        if r_squared < 0.0:
            r_squared = 0.0

        # Confidence blends fit quality with sample coverage
        sample_factor = min(1.0, n / max(1, window))
        confidence = max(0.0, min(1.0, r_squared * sample_factor))

        # Determine whether higher is better for this metric
        higher_is_better = self._is_higher_better(metric_id)

        # Classify direction
        if ss_tot > 0 and mean_y != 0:
            cv = (ss_tot / n) ** 0.5 / abs(mean_y)
        else:
            cv = 0.0

        if cv > self._VOLATILITY_THRESHOLD:
            direction = TrendDirection.VOLATILE
        elif abs(slope) < self._STABLE_SLOPE_THRESHOLD:
            direction = TrendDirection.STABLE
        elif higher_is_better:
            direction = (
                TrendDirection.IMPROVING if slope > 0 else TrendDirection.DECLINING
            )
        else:
            # For metrics where lower is better (latency, cost)
            direction = (
                TrendDirection.IMPROVING if slope < 0 else TrendDirection.DECLINING
            )

        summary = (
            f"Trend for metric {metric_id} on agent {agent_id}: "
            f"{direction.value} (slope={slope:.6f}, confidence={confidence:.2f}, "
            f"points={n})."
        )

        return TrendAnalysis(
            agent_id=agent_id,
            metric_id=metric_id,
            direction=direction,
            slope=slope,
            confidence=confidence,
            data_points=data_points,
            summary=summary,
        )

    # ── Leaderboard & Stats ──────────────────────────────

    def get_leaderboard(
        self, benchmark_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return the top agents for a benchmark, ranked by best score."""
        with self._lock:
            runs = [
                r
                for r in self._runs.values()
                if r.benchmark_id == benchmark_id
                and r.status == EvaluationStatus.COMPLETED
            ]

        agent_best: dict[str, dict[str, Any]] = {}
        for run in runs:
            score = self.calculate_score(run.run_id)
            existing = agent_best.get(run.agent_id)
            if existing is None or score > existing["score"]:
                agent_best[run.agent_id] = {
                    "agent_id": run.agent_id,
                    "run_id": run.run_id,
                    "score": score,
                    "started_at": run.started_at,
                    "result_count": len(run.results),
                }

        leaderboard = list(agent_best.values())
        leaderboard.sort(key=lambda entry: entry["score"], reverse=True)
        return leaderboard[:limit]

    def get_benchmark_stats(self, benchmark_id: str) -> dict[str, Any]:
        """Return aggregate statistics for a specific benchmark."""
        with self._lock:
            benchmark = self._benchmarks.get(benchmark_id)
            if benchmark is None:
                return {}

            runs = [
                r for r in self._runs.values() if r.benchmark_id == benchmark_id
            ]
            completed = [
                r for r in runs if r.status == EvaluationStatus.COMPLETED
            ]
            comparisons = [
                c
                for c in self._comparisons.values()
                if c.benchmark_id == benchmark_id
            ]

        scores = [self.calculate_score(r.run_id) for r in completed]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        best_score = max(scores) if scores else 0.0
        worst_score = min(scores) if scores else 0.0

        # Metric coverage: number of completed runs reporting each metric
        metric_coverage: dict[str, int] = {}
        for md in benchmark.metric_definitions:
            count = sum(
                1
                for r in completed
                for result in r.results
                if result.metric_id == md.metric_id
            )
            metric_coverage[md.metric_id] = count

        # Agent participation
        unique_agents = {r.agent_id for r in runs}

        return {
            "benchmark_id": benchmark_id,
            "name": benchmark.name,
            "benchmark_type": benchmark.benchmark_type.value,
            "total_runs": len(runs),
            "completed_runs": len(completed),
            "failed_runs": sum(
                1 for r in runs if r.status == EvaluationStatus.FAILED
            ),
            "cancelled_runs": sum(
                1 for r in runs if r.status == EvaluationStatus.CANCELLED
            ),
            "unique_agents": len(unique_agents),
            "metric_count": len(benchmark.metric_definitions),
            "metric_coverage": metric_coverage,
            "avg_score": avg_score,
            "best_score": best_score,
            "worst_score": worst_score,
            "target_score": benchmark.target_score,
            "comparison_count": len(comparisons),
            "created_at": benchmark.created_at,
            "last_run_at": benchmark.last_run_at,
        }

    def get_stats(self) -> BenchmarkStats:
        """Return aggregate statistics for the entire engine."""
        with self._lock:
            benchmarks = list(self._benchmarks.values())
            runs = list(self._runs.values())
            comparisons = list(self._comparisons.values())

            completed_runs = [
                r for r in runs if r.status == EvaluationStatus.COMPLETED
            ]

            # Aggregate scores across completed runs
            scores: list[float] = []
            for run in completed_runs:
                score = self._calculate_score_unlocked(run)
                if score > 0:
                    scores.append(score)
            avg_score = sum(scores) / len(scores) if scores else 0.0

            # Benchmarks grouped by type
            by_type: dict[str, int] = {}
            for b in benchmarks:
                key = b.benchmark_type.value
                by_type[key] = by_type.get(key, 0) + 1

            # Metric coverage across all benchmarks
            metric_coverage: dict[str, int] = {}
            for b in benchmarks:
                for md in b.metric_definitions:
                    metric_coverage[md.metric_id] = (
                        metric_coverage.get(md.metric_id, 0) + 1
                    )

        return BenchmarkStats(
            total_benchmarks=len(benchmarks),
            total_runs=len(runs),
            completed_runs=len(completed_runs),
            avg_score=avg_score,
            benchmarks_by_type=by_type,
            metric_coverage=metric_coverage,
            comparison_count=len(comparisons),
        )

    # ── Reset ────────────────────────────────────────────

    def reset(self) -> None:
        """Reset the benchmark engine, clearing all stored state."""
        with self._lock:
            self._benchmarks.clear()
            self._runs.clear()
            self._comparisons.clear()
            self._start_time = time.monotonic()
        logger.info("AgentBenchmarkEngine reset")

    # ── Internal Helpers ─────────────────────────────────

    def _normalize(
        self,
        value: float,
        metric_id: str,
        benchmark: Benchmark | None,
    ) -> float:
        """Normalize a metric value to 0.0-1.0 using the benchmark's definition."""
        if benchmark is None:
            return 0.0
        for md in benchmark.metric_definitions:
            if md.metric_id == metric_id:
                return self._normalize_with_def(value, md)
        # No matching definition: clamp to [0, 1]
        return max(0.0, min(1.0, value))

    @staticmethod
    def _normalize_with_def(value: float, md: MetricDefinition) -> float:
        """Normalize a value using a specific metric definition."""
        span = md.max_value - md.min_value
        if span <= 0:
            return 0.0
        normalized = (value - md.min_value) / span
        if normalized < 0.0:
            return 0.0
        if normalized > 1.0:
            return 1.0
        return normalized

    def _calculate_score_unlocked(self, run: EvaluationRun) -> float:
        """Compute the weighted normalized score without acquiring the lock.

        Assumes the caller already holds ``self._lock``.
        """
        benchmark = self._benchmarks.get(run.benchmark_id)
        if benchmark is None:
            return 0.0

        defs_by_id: dict[str, MetricDefinition] = {
            md.metric_id: md for md in benchmark.metric_definitions
        }

        results = run.results
        if not results:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for result in results:
            md = defs_by_id.get(result.metric_id)
            if md is None:
                score = max(0.0, min(1.0, result.normalized_score))
                weight = 1.0
            else:
                score = self._normalize_with_def(result.value, md)
                weight = md.weight
                result.normalized_score = score

            if weight <= 0:
                continue

            weighted_sum += score * weight
            total_weight += weight

        if total_weight <= 0:
            return 0.0

        return weighted_sum / total_weight

    def _is_higher_better(self, metric_id: str) -> bool:
        """Determine whether higher values are better for a metric.

        For LATENCY and COST categories, lower is better. For all other
        categories, higher is better. Returns True by default if the metric
        cannot be located.
        """
        for benchmark in self._benchmarks.values():
            for md in benchmark.metric_definitions:
                if md.metric_id == metric_id:
                    return md.category not in (
                        MetricCategory.LATENCY,
                        MetricCategory.COST,
                    )
        return True


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_benchmark_engine: AgentBenchmarkEngine | None = None
_singleton_lock = threading.Lock()


def get_benchmark_engine() -> AgentBenchmarkEngine:
    """Get or create the global Benchmark Engine instance."""
    global _benchmark_engine
    if _benchmark_engine is None:
        with _singleton_lock:
            if _benchmark_engine is None:
                _benchmark_engine = AgentBenchmarkEngine()
    return _benchmark_engine


def reset_benchmark_engine() -> None:
    """Reset the global Benchmark Engine instance."""
    global _benchmark_engine
    with _singleton_lock:
        if _benchmark_engine is not None:
            _benchmark_engine.reset()
        _benchmark_engine = None
