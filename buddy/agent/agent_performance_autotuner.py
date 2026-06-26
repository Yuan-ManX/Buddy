"""
Performance Autotuner - Automated Performance Profiling and Optimization for Buddy.

The Performance Autotuner continuously profiles agent components, detects
performance bottlenecks, and automatically applies optimization strategies
to improve throughput, latency, and resource utilization across the Buddy
AI platform.

Core capabilities:
- Automated performance profiling of all agent components
- Bottleneck detection using threshold-based analysis
- Intelligent optimization recommendation and application
- Before/after metric tracking with rollback support
- Comprehensive tuning reports and health dashboards
"""

from __future__ import annotations

import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.performance_autotuner")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ComponentType(str, Enum):
    """Types of components that can be profiled and tuned."""
    MODEL_ROUTER = "model_router"
    TOOL_EXECUTOR = "tool_executor"
    CACHE = "cache"
    MEMORY = "memory"
    PIPELINE = "pipeline"
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"
    STREAMING = "streaming"


class BottleneckType(str, Enum):
    """Categories of performance bottlenecks."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    RESOURCE = "resource"
    ERROR = "error"
    CACHE = "cache"


class Severity(str, Enum):
    """Severity levels for bottlenecks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OptimizationStrategy(str, Enum):
    """Strategies for resolving performance bottlenecks."""
    CACHE_AUGMENT = "cache_augment"
    BATCH_PROCESS = "batch_process"
    PARALLELIZE = "parallelize"
    COMPRESS = "compress"
    PRELOAD = "preload"
    THROTTLE = "throttle"
    RETRY = "retry"


class RiskLevel(str, Enum):
    """Risk levels associated with optimization recommendations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PerformanceProfile:
    """A snapshot of a component's performance metrics."""
    id: str
    component_id: str
    component_type: ComponentType
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_per_sec: float
    error_rate: float
    resource_usage: dict[str, float]
    cache_hit_rate: float
    created_at: datetime
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class Bottleneck:
    """A detected performance bottleneck in a component."""
    id: str
    component_id: str
    bottleneck_type: BottleneckType
    severity: Severity
    current_value: float
    threshold: float
    impact_description: str
    detected_at: datetime


@dataclass
class OptimizationRecommendation:
    """A recommendation for resolving a performance bottleneck."""
    id: str
    bottleneck_id: str
    strategy: OptimizationStrategy
    expected_improvement_pct: float
    implementation_complexity: str
    risk_level: RiskLevel
    estimated_cost: str


@dataclass
class OptimizationResult:
    """The result of applying an optimization."""
    id: str
    recommendation_id: str
    applied_at: datetime
    actual_improvement_pct: float
    before_metrics: dict[str, Any]
    after_metrics: dict[str, Any]
    success: bool


@dataclass
class TuningResult:
    """The result of auto-tuning a component."""
    component_id: str
    optimizations_applied: list[str]
    overall_improvement_pct: float
    recommendations: list[OptimizationRecommendation]


@dataclass
class TuningReport:
    """A comprehensive report of all tuning activity."""
    total_components: int
    bottlenecks_found: int
    optimizations_applied: int
    overall_improvement: float
    components_tuned: list[str]


# ---------------------------------------------------------------------------
# Performance Autotuner
# ---------------------------------------------------------------------------


class PerformanceAutotuner:
    """
    Automated performance profiling and optimization engine.

    Profiles agent components, identifies bottlenecks, recommends and
    applies optimizations, and tracks before/after metrics with full
    rollback support.
    """

    # Thresholds for bottleneck detection (per component type)
    _LATENCY_THRESHOLDS: dict[ComponentType, float] = {
        ComponentType.MODEL_ROUTER: 200.0,
        ComponentType.TOOL_EXECUTOR: 500.0,
        ComponentType.CACHE: 10.0,
        ComponentType.MEMORY: 50.0,
        ComponentType.PIPELINE: 1000.0,
        ComponentType.API_ENDPOINT: 300.0,
        ComponentType.DATABASE: 100.0,
        ComponentType.STREAMING: 150.0,
    }

    _THROUGHPUT_THRESHOLDS: dict[ComponentType, float] = {
        ComponentType.MODEL_ROUTER: 50.0,
        ComponentType.TOOL_EXECUTOR: 20.0,
        ComponentType.CACHE: 1000.0,
        ComponentType.MEMORY: 500.0,
        ComponentType.PIPELINE: 10.0,
        ComponentType.API_ENDPOINT: 100.0,
        ComponentType.DATABASE: 200.0,
        ComponentType.STREAMING: 30.0,
    }

    _ERROR_RATE_THRESHOLD: float = 0.05
    _CACHE_HIT_RATE_THRESHOLD: float = 0.70
    _CPU_THRESHOLD: float = 80.0
    _MEMORY_THRESHOLD: float = 85.0

    def __init__(self):
        self._profiles: dict[str, PerformanceProfile] = {}
        self._bottlenecks: dict[str, Bottleneck] = {}
        self._recommendations: dict[str, OptimizationRecommendation] = {}
        self._optimization_results: dict[str, OptimizationResult] = {}
        self._component_bottlenecks: dict[str, list[str]] = {}
        self._bottleneck_recommendations: dict[str, list[str]] = {}
        self._component_optimizations: dict[str, list[str]] = {}
        self._rolled_back: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def profile(self, component_id: str, component_type: ComponentType) -> PerformanceProfile:
        """Profile a component and return its performance snapshot.

        Simulates realistic performance metrics based on the component type
        to produce a measurable profile.
        """
        profile_id = f"prof-{uuid.uuid4().hex[:12]}"

        base_latency = self._simulate_base_latency(component_type)
        avg_latency = round(base_latency + random.uniform(-20, 40), 2)
        p95_latency = round(avg_latency * random.uniform(1.5, 3.0), 2)
        p99_latency = round(avg_latency * random.uniform(2.5, 5.5), 2)

        throughput = round(self._simulate_throughput(component_type), 2)
        error_rate = round(random.uniform(0.0, 0.12), 4)
        cache_hit_rate = round(random.uniform(0.40, 0.95), 4)

        resource_usage = {
            "cpu_percent": round(random.uniform(20.0, 92.0), 1),
            "memory_percent": round(random.uniform(30.0, 90.0), 1),
        }

        metrics = {
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "throughput_per_sec": throughput,
            "error_rate": error_rate,
            "cache_hit_rate": cache_hit_rate,
            "cpu_percent": resource_usage["cpu_percent"],
            "memory_percent": resource_usage["memory_percent"],
            "request_count": random.randint(100, 10000),
            "active_connections": random.randint(1, 200),
        }

        profile = PerformanceProfile(
            id=profile_id,
            component_id=component_id,
            component_type=component_type,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            throughput_per_sec=throughput,
            error_rate=error_rate,
            resource_usage=resource_usage,
            cache_hit_rate=cache_hit_rate,
            created_at=datetime.now(timezone.utc),
            metrics=metrics,
        )

        self._profiles[profile_id] = profile
        logger.info(
            "Profiled component %s (%s): avg_latency=%.2fms, throughput=%.2f/s",
            component_id, component_type.value, avg_latency, throughput,
        )
        return profile

    def detect_bottlenecks(self) -> list[Bottleneck]:
        """Detect performance bottlenecks across all profiled components.

        Returns a list of all bottlenecks found, ordered by severity.
        """
        bottlenecks: list[Bottleneck] = []

        for profile in self._profiles.values():
            detected = self._analyze_profile(profile)
            for b in detected:
                self._bottlenecks[b.id] = b
                self._component_bottlenecks.setdefault(profile.component_id, []).append(b.id)
                bottlenecks.append(b)

        # Sort by severity: critical > high > medium > low
        severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
        bottlenecks.sort(key=lambda b: severity_order[b.severity])

        logger.info(
            "Bottleneck detection complete: %d bottlenecks found across %d components",
            len(bottlenecks), len(self._component_bottlenecks),
        )
        return bottlenecks

    def recommend_optimizations(self, bottleneck_id: str) -> list[OptimizationRecommendation]:
        """Generate optimization recommendations for a specific bottleneck.

        Returns a list of recommended strategies, each with expected
        improvement, complexity, risk, and cost estimates.
        """
        bottleneck = self._bottlenecks.get(bottleneck_id)
        if bottleneck is None:
            raise ValueError(f"Bottleneck not found: {bottleneck_id}")

        recommendations = self._generate_recommendations(bottleneck)
        self._bottleneck_recommendations[bottleneck_id] = [r.id for r in recommendations]
        for rec in recommendations:
            self._recommendations[rec.id] = rec

        logger.info(
            "Generated %d optimization recommendations for bottleneck %s",
            len(recommendations), bottleneck_id,
        )
        return recommendations

    def apply_optimization(self, recommendation_id: str) -> OptimizationResult:
        """Apply an optimization recommendation and measure its effect.

        Simulates applying the optimization and returns before/after metrics
        along with the actual improvement achieved.
        """
        recommendation = self._recommendations.get(recommendation_id)
        if recommendation is None:
            raise ValueError(f"Recommendation not found: {recommendation_id}")

        bottleneck = self._bottlenecks.get(recommendation.bottleneck_id)
        if bottleneck is None:
            raise ValueError(f"Bottleneck not found for recommendation: {recommendation_id}")

        profile = self._find_profile_for_bottleneck(bottleneck)
        if profile is None:
            raise ValueError(f"No profile found for bottleneck {bottleneck.id}")

        result_id = f"opt-{uuid.uuid4().hex[:12]}"

        before_metrics = dict(profile.metrics)
        actual_improvement = self._simulate_improvement(recommendation)
        actual_improvement = round(actual_improvement, 2)

        after_metrics = self._compute_after_metrics(before_metrics, recommendation, actual_improvement)

        result = OptimizationResult(
            id=result_id,
            recommendation_id=recommendation_id,
            applied_at=datetime.now(timezone.utc),
            actual_improvement_pct=actual_improvement,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            success=actual_improvement > 0,
        )

        self._optimization_results[result_id] = result
        self._component_optimizations.setdefault(bottleneck.component_id, []).append(result_id)

        # Update the profile with improved metrics
        profile.metrics = after_metrics
        profile.avg_latency_ms = after_metrics.get("avg_latency_ms", profile.avg_latency_ms)
        profile.p95_latency_ms = after_metrics.get("p95_latency_ms", profile.p95_latency_ms)
        profile.p99_latency_ms = after_metrics.get("p99_latency_ms", profile.p99_latency_ms)
        profile.throughput_per_sec = after_metrics.get("throughput_per_sec", profile.throughput_per_sec)
        profile.error_rate = after_metrics.get("error_rate", profile.error_rate)
        profile.cache_hit_rate = after_metrics.get("cache_hit_rate", profile.cache_hit_rate)
        if "cpu_percent" in after_metrics:
            profile.resource_usage["cpu_percent"] = after_metrics["cpu_percent"]
        if "memory_percent" in after_metrics:
            profile.resource_usage["memory_percent"] = after_metrics["memory_percent"]

        logger.info(
            "Applied optimization %s: improvement=%.2f%%, success=%s",
            recommendation_id, actual_improvement, result.success,
        )
        return result

    def auto_tune(self, component_id: str) -> TuningResult:
        """Automatically profile, detect bottlenecks, and apply the best
        optimization for a single component.

        Returns a TuningResult with all applied optimizations and the
        overall improvement achieved.
        """
        bottleneck_ids = self._component_bottlenecks.get(component_id, [])
        if not bottleneck_ids:
            logger.info("No bottlenecks registered for component %s; nothing to tune", component_id)
            return TuningResult(
                component_id=component_id,
                optimizations_applied=[],
                overall_improvement_pct=0.0,
                recommendations=[],
            )

        applied_ids: list[str] = []
        all_recommendations: list[OptimizationRecommendation] = []
        total_improvement = 0.0

        for b_id in bottleneck_ids:
            recs = self.recommend_optimizations(b_id)
            if not recs:
                continue

            # Select the best recommendation: highest expected improvement
            # with acceptable risk
            best = self._select_best_recommendation(recs)
            if best is None:
                continue

            all_recommendations.append(best)
            result = self.apply_optimization(best.id)
            if result.success:
                applied_ids.append(result.id)
                total_improvement += result.actual_improvement_pct

        overall = round(total_improvement / max(len(applied_ids), 1), 2)

        logger.info(
            "Auto-tuned component %s: %d optimizations applied, overall %.2f%% improvement",
            component_id, len(applied_ids), overall,
        )
        return TuningResult(
            component_id=component_id,
            optimizations_applied=applied_ids,
            overall_improvement_pct=overall,
            recommendations=all_recommendations,
        )

    def get_tuning_report(self) -> TuningReport:
        """Generate a comprehensive tuning report across all components."""
        total_components = len(set(p.component_id for p in self._profiles.values()))
        total_bottlenecks = len(self._bottlenecks)
        total_optimizations = len(self._optimization_results)

        improvements = [
            r.actual_improvement_pct
            for r in self._optimization_results.values()
            if r.success
        ]
        overall_improvement = (
            round(sum(improvements) / len(improvements), 2) if improvements else 0.0
        )

        components_tuned = list(self._component_optimizations.keys())

        report = TuningReport(
            total_components=total_components,
            bottlenecks_found=total_bottlenecks,
            optimizations_applied=total_optimizations,
            overall_improvement=overall_improvement,
            components_tuned=components_tuned,
        )

        logger.info(
            "Tuning report: %d components, %d bottlenecks, %d optimizations, %.2f%% avg improvement",
            total_components, total_bottlenecks, total_optimizations, overall_improvement,
        )
        return report

    def rollback(self, optimization_id: str) -> RollbackResult:
        """Rollback a previously applied optimization.

        Restores the component's metrics to their pre-optimization state.
        """
        result = self._optimization_results.get(optimization_id)
        if result is None:
            raise ValueError(f"Optimization result not found: {optimization_id}")

        if optimization_id in self._rolled_back:
            raise ValueError(f"Optimization already rolled back: {optimization_id}")

        recommendation = self._recommendations.get(result.recommendation_id)
        if recommendation is None:
            raise ValueError(f"Recommendation not found for optimization: {optimization_id}")

        bottleneck = self._bottlenecks.get(recommendation.bottleneck_id)
        if bottleneck is None:
            raise ValueError(f"Bottleneck not found for optimization: {optimization_id}")

        profile = self._find_profile_for_bottleneck(bottleneck)
        if profile is not None:
            before = result.before_metrics
            profile.metrics = before
            profile.avg_latency_ms = before.get("avg_latency_ms", profile.avg_latency_ms)
            profile.p95_latency_ms = before.get("p95_latency_ms", profile.p95_latency_ms)
            profile.p99_latency_ms = before.get("p99_latency_ms", profile.p99_latency_ms)
            profile.throughput_per_sec = before.get("throughput_per_sec", profile.throughput_per_sec)
            profile.error_rate = before.get("error_rate", profile.error_rate)
            profile.cache_hit_rate = before.get("cache_hit_rate", profile.cache_hit_rate)
            if "cpu_percent" in before:
                profile.resource_usage["cpu_percent"] = before["cpu_percent"]
            if "memory_percent" in before:
                profile.resource_usage["memory_percent"] = before["memory_percent"]

        self._rolled_back.add(optimization_id)

        rollback_result = RollbackResult(
            optimization_id=optimization_id,
            rolled_back_at=datetime.now(timezone.utc),
            component_id=bottleneck.component_id,
            restored_metrics=result.before_metrics,
            success=True,
        )

        logger.info(
            "Rolled back optimization %s for component %s",
            optimization_id, bottleneck.component_id,
        )
        return rollback_result

    def reset(self) -> None:
        """Clear all state: profiles, bottlenecks, recommendations, and results."""
        self._profiles.clear()
        self._bottlenecks.clear()
        self._recommendations.clear()
        self._optimization_results.clear()
        self._component_bottlenecks.clear()
        self._bottleneck_recommendations.clear()
        self._component_optimizations.clear()
        self._rolled_back.clear()
        logger.info("PerformanceAutotuner state has been reset")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _analyze_profile(self, profile: PerformanceProfile) -> list[Bottleneck]:
        """Analyze a single profile and return any detected bottlenecks."""
        bottlenecks: list[Bottleneck] = []
        now = datetime.now(timezone.utc)

        # Latency check
        latency_threshold = self._LATENCY_THRESHOLDS.get(profile.component_type, 500.0)
        if profile.avg_latency_ms > latency_threshold:
            severity = self._compute_severity(profile.avg_latency_ms, latency_threshold)
            bottlenecks.append(Bottleneck(
                id=f"bn-{uuid.uuid4().hex[:12]}",
                component_id=profile.component_id,
                bottleneck_type=BottleneckType.LATENCY,
                severity=severity,
                current_value=profile.avg_latency_ms,
                threshold=latency_threshold,
                impact_description=f"Average latency of {profile.avg_latency_ms:.1f}ms exceeds threshold of {latency_threshold:.1f}ms",
                detected_at=now,
            ))

        # Throughput check
        throughput_threshold = self._THROUGHPUT_THRESHOLDS.get(profile.component_type, 50.0)
        if profile.throughput_per_sec < throughput_threshold:
            severity = self._compute_severity_inverted(profile.throughput_per_sec, throughput_threshold)
            bottlenecks.append(Bottleneck(
                id=f"bn-{uuid.uuid4().hex[:12]}",
                component_id=profile.component_id,
                bottleneck_type=BottleneckType.THROUGHPUT,
                severity=severity,
                current_value=profile.throughput_per_sec,
                threshold=throughput_threshold,
                impact_description=f"Throughput of {profile.throughput_per_sec:.1f}/s is below threshold of {throughput_threshold:.1f}/s",
                detected_at=now,
            ))

        # Error rate check
        if profile.error_rate > self._ERROR_RATE_THRESHOLD:
            severity = self._compute_severity(profile.error_rate, self._ERROR_RATE_THRESHOLD)
            bottlenecks.append(Bottleneck(
                id=f"bn-{uuid.uuid4().hex[:12]}",
                component_id=profile.component_id,
                bottleneck_type=BottleneckType.ERROR,
                severity=severity,
                current_value=profile.error_rate,
                threshold=self._ERROR_RATE_THRESHOLD,
                impact_description=f"Error rate of {profile.error_rate:.4f} exceeds threshold of {self._ERROR_RATE_THRESHOLD}",
                detected_at=now,
            ))

        # Resource checks
        cpu = profile.resource_usage.get("cpu_percent", 0.0)
        if cpu > self._CPU_THRESHOLD:
            severity = self._compute_severity(cpu, self._CPU_THRESHOLD)
            bottlenecks.append(Bottleneck(
                id=f"bn-{uuid.uuid4().hex[:12]}",
                component_id=profile.component_id,
                bottleneck_type=BottleneckType.RESOURCE,
                severity=severity,
                current_value=cpu,
                threshold=self._CPU_THRESHOLD,
                impact_description=f"CPU usage of {cpu:.1f}% exceeds threshold of {self._CPU_THRESHOLD}%",
                detected_at=now,
            ))

        memory = profile.resource_usage.get("memory_percent", 0.0)
        if memory > self._MEMORY_THRESHOLD:
            severity = self._compute_severity(memory, self._MEMORY_THRESHOLD)
            bottlenecks.append(Bottleneck(
                id=f"bn-{uuid.uuid4().hex[:12]}",
                component_id=profile.component_id,
                bottleneck_type=BottleneckType.RESOURCE,
                severity=severity,
                current_value=memory,
                threshold=self._MEMORY_THRESHOLD,
                impact_description=f"Memory usage of {memory:.1f}% exceeds threshold of {self._MEMORY_THRESHOLD}%",
                detected_at=now,
            ))

        # Cache hit rate check
        if profile.component_type in (ComponentType.CACHE, ComponentType.MEMORY, ComponentType.DATABASE):
            if profile.cache_hit_rate < self._CACHE_HIT_RATE_THRESHOLD:
                severity = self._compute_severity_inverted(profile.cache_hit_rate, self._CACHE_HIT_RATE_THRESHOLD)
                bottlenecks.append(Bottleneck(
                    id=f"bn-{uuid.uuid4().hex[:12]}",
                    component_id=profile.component_id,
                    bottleneck_type=BottleneckType.CACHE,
                    severity=severity,
                    current_value=profile.cache_hit_rate,
                    threshold=self._CACHE_HIT_RATE_THRESHOLD,
                    impact_description=f"Cache hit rate of {profile.cache_hit_rate:.2%} is below threshold of {self._CACHE_HIT_RATE_THRESHOLD:.2%}",
                    detected_at=now,
                ))

        return bottlenecks

    def _generate_recommendations(self, bottleneck: Bottleneck) -> list[OptimizationRecommendation]:
        """Generate optimization recommendations for a given bottleneck."""
        strategy_map: dict[BottleneckType, list[OptimizationStrategy]] = {
            BottleneckType.LATENCY: [
                OptimizationStrategy.CACHE_AUGMENT,
                OptimizationStrategy.PARALLELIZE,
                OptimizationStrategy.PRELOAD,
                OptimizationStrategy.COMPRESS,
            ],
            BottleneckType.THROUGHPUT: [
                OptimizationStrategy.BATCH_PROCESS,
                OptimizationStrategy.PARALLELIZE,
                OptimizationStrategy.CACHE_AUGMENT,
            ],
            BottleneckType.RESOURCE: [
                OptimizationStrategy.COMPRESS,
                OptimizationStrategy.THROTTLE,
                OptimizationStrategy.CACHE_AUGMENT,
            ],
            BottleneckType.ERROR: [
                OptimizationStrategy.RETRY,
                OptimizationStrategy.THROTTLE,
            ],
            BottleneckType.CACHE: [
                OptimizationStrategy.CACHE_AUGMENT,
                OptimizationStrategy.PRELOAD,
            ],
        }

        strategies = strategy_map.get(bottleneck.bottleneck_type, [OptimizationStrategy.CACHE_AUGMENT])
        recommendations: list[OptimizationRecommendation] = []

        for i, strategy in enumerate(strategies):
            improvement = self._estimate_improvement(strategy, bottleneck)
            complexity, risk, cost = self._strategy_metadata(strategy, i)

            recommendations.append(OptimizationRecommendation(
                id=f"rec-{uuid.uuid4().hex[:12]}",
                bottleneck_id=bottleneck.id,
                strategy=strategy,
                expected_improvement_pct=improvement,
                implementation_complexity=complexity,
                risk_level=risk,
                estimated_cost=cost,
            ))

        return recommendations

    def _select_best_recommendation(
        self, recommendations: list[OptimizationRecommendation],
    ) -> OptimizationRecommendation | None:
        """Select the best recommendation based on improvement and risk."""
        if not recommendations:
            return None

        # Score: improvement - risk penalty - complexity penalty
        risk_penalty = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 10, RiskLevel.HIGH: 25}
        complexity_penalty = {"low": 0, "medium": 5, "high": 15}

        def score(rec: OptimizationRecommendation) -> float:
            return (
                rec.expected_improvement_pct
                - risk_penalty.get(rec.risk_level, 0)
                - complexity_penalty.get(rec.implementation_complexity, 0)
            )

        best = max(recommendations, key=score)
        return best if score(best) > 0 else None

    def _find_profile_for_bottleneck(self, bottleneck: Bottleneck) -> PerformanceProfile | None:
        """Find the most recent profile for a bottleneck's component."""
        for profile in sorted(
            self._profiles.values(),
            key=lambda p: p.created_at,
            reverse=True,
        ):
            if profile.component_id == bottleneck.component_id:
                return profile
        return None

    # ------------------------------------------------------------------
    # Simulation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _simulate_base_latency(component_type: ComponentType) -> float:
        """Return a realistic base latency for a component type."""
        latencies = {
            ComponentType.MODEL_ROUTER: 150.0,
            ComponentType.TOOL_EXECUTOR: 350.0,
            ComponentType.CACHE: 5.0,
            ComponentType.MEMORY: 30.0,
            ComponentType.PIPELINE: 800.0,
            ComponentType.API_ENDPOINT: 200.0,
            ComponentType.DATABASE: 60.0,
            ComponentType.STREAMING: 100.0,
        }
        return latencies.get(component_type, 200.0)

    @staticmethod
    def _simulate_throughput(component_type: ComponentType) -> float:
        """Return a realistic throughput for a component type."""
        throughputs = {
            ComponentType.MODEL_ROUTER: 60.0,
            ComponentType.TOOL_EXECUTOR: 25.0,
            ComponentType.CACHE: 1200.0,
            ComponentType.MEMORY: 600.0,
            ComponentType.PIPELINE: 15.0,
            ComponentType.API_ENDPOINT: 120.0,
            ComponentType.DATABASE: 250.0,
            ComponentType.STREAMING: 40.0,
        }
        return throughputs.get(component_type, 50.0) * random.uniform(0.6, 1.4)

    @staticmethod
    def _compute_severity(current: float, threshold: float) -> Severity:
        """Compute severity based on how much current exceeds threshold."""
        ratio = current / threshold if threshold > 0 else 1.0
        if ratio >= 3.0:
            return Severity.CRITICAL
        if ratio >= 2.0:
            return Severity.HIGH
        if ratio >= 1.5:
            return Severity.MEDIUM
        return Severity.LOW

    @staticmethod
    def _compute_severity_inverted(current: float, threshold: float) -> Severity:
        """Compute severity when lower is worse (throughput, cache hit rate)."""
        ratio = threshold / current if current > 0 else 3.0
        if ratio >= 3.0:
            return Severity.CRITICAL
        if ratio >= 2.0:
            return Severity.HIGH
        if ratio >= 1.5:
            return Severity.MEDIUM
        return Severity.LOW

    @staticmethod
    def _estimate_improvement(
        strategy: OptimizationStrategy, bottleneck: Bottleneck,
    ) -> float:
        """Estimate the expected improvement percentage for a strategy."""
        base_improvements = {
            OptimizationStrategy.CACHE_AUGMENT: 35.0,
            OptimizationStrategy.BATCH_PROCESS: 25.0,
            OptimizationStrategy.PARALLELIZE: 30.0,
            OptimizationStrategy.COMPRESS: 20.0,
            OptimizationStrategy.PRELOAD: 28.0,
            OptimizationStrategy.THROTTLE: 15.0,
            OptimizationStrategy.RETRY: 18.0,
        }
        base = base_improvements.get(strategy, 20.0)
        severity_multiplier = {
            Severity.CRITICAL: 1.3,
            Severity.HIGH: 1.1,
            Severity.MEDIUM: 1.0,
            Severity.LOW: 0.8,
        }
        multiplier = severity_multiplier.get(bottleneck.severity, 1.0)
        return round(base * multiplier * random.uniform(0.85, 1.15), 1)

    @staticmethod
    def _simulate_improvement(recommendation: OptimizationRecommendation) -> float:
        """Simulate actual improvement from applying a recommendation."""
        variance = random.uniform(0.6, 1.3)
        return round(recommendation.expected_improvement_pct * variance, 1)

    @staticmethod
    def _strategy_metadata(
        strategy: OptimizationStrategy, rank: int,
    ) -> tuple[str, RiskLevel, str]:
        """Return (complexity, risk, cost) for a strategy at a given rank."""
        metadata = {
            OptimizationStrategy.CACHE_AUGMENT: ("low", RiskLevel.LOW, "low"),
            OptimizationStrategy.BATCH_PROCESS: ("medium", RiskLevel.LOW, "medium"),
            OptimizationStrategy.PARALLELIZE: ("high", RiskLevel.MEDIUM, "medium"),
            OptimizationStrategy.COMPRESS: ("low", RiskLevel.LOW, "low"),
            OptimizationStrategy.PRELOAD: ("medium", RiskLevel.MEDIUM, "medium"),
            OptimizationStrategy.THROTTLE: ("low", RiskLevel.LOW, "low"),
            OptimizationStrategy.RETRY: ("medium", RiskLevel.MEDIUM, "medium"),
        }
        return metadata.get(strategy, ("medium", RiskLevel.MEDIUM, "medium"))

    @staticmethod
    def _compute_after_metrics(
        before: dict[str, Any],
        recommendation: OptimizationRecommendation,
        improvement_pct: float,
    ) -> dict[str, Any]:
        """Compute projected after-metrics based on the improvement."""
        factor = 1.0 - (improvement_pct / 100.0)
        throughput_factor = 1.0 + (improvement_pct / 100.0)

        after: dict[str, Any] = {}
        for key, value in before.items():
            if isinstance(value, (int, float)):
                if key in ("avg_latency_ms", "p95_latency_ms", "p99_latency_ms", "error_rate"):
                    after[key] = round(value * factor, 4)
                elif key in ("throughput_per_sec", "cache_hit_rate"):
                    after[key] = round(min(value * throughput_factor, value * 3.0), 4)
                elif key in ("cpu_percent", "memory_percent"):
                    after[key] = round(value * factor, 1)
                else:
                    after[key] = value
            else:
                after[key] = value

        return after


# ---------------------------------------------------------------------------
# RollbackResult
# ---------------------------------------------------------------------------


@dataclass
class RollbackResult:
    """The result of rolling back an optimization."""
    optimization_id: str
    rolled_back_at: datetime
    component_id: str
    restored_metrics: dict[str, Any]
    success: bool


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------


_autotuner_instance: PerformanceAutotuner | None = None


def get_performance_autotuner() -> PerformanceAutotuner:
    """Get or create the global PerformanceAutotuner singleton instance.

    Returns:
        The global PerformanceAutotuner singleton.
    """
    global _autotuner_instance
    if _autotuner_instance is None:
        _autotuner_instance = PerformanceAutotuner()
        logger.info("Global PerformanceAutotuner singleton created")
    return _autotuner_instance


def reset_performance_autotuner() -> None:
    """Reset the global PerformanceAutotuner singleton instance.

    Clears all internal state and discards the current instance.
    """
    global _autotuner_instance
    if _autotuner_instance is not None:
        _autotuner_instance.reset()
    _autotuner_instance = None
    logger.info("Global PerformanceAutotuner singleton reset")