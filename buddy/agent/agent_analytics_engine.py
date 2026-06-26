"""Buddy Agent Analytics Engine — real-time analytics, metrics, and insights

The Analytics Engine provides comprehensive monitoring, metrics collection,
and insight generation for the entire agent ecosystem. It tracks performance,
usage patterns, quality metrics, and generates actionable recommendations.

Core capabilities:
  - Real-Time Metrics: continuous collection of performance and usage data
  - Quality Scoring: automated quality assessment of agent outputs
  - Usage Analytics: user engagement, feature adoption, and trend analysis
  - Performance Monitoring: latency, throughput, and resource utilization
  - Insight Generation: pattern detection and actionable recommendations
  - Dashboard Data: pre-computed data for visualization dashboards
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.analytics_engine")


# ═══════════════════════════════════════════════════════════
# Enums and Types
# ═══════════════════════════════════════════════════════════

class MetricType(str, Enum):
    """Types of analytics metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"


class MetricCategory(str, Enum):
    """Categories of metrics."""
    PERFORMANCE = "performance"
    USAGE = "usage"
    QUALITY = "quality"
    RESOURCE = "resource"
    BUSINESS = "business"
    SECURITY = "security"


class InsightType(str, Enum):
    """Types of generated insights."""
    TREND = "trend"
    ANOMALY = "anomaly"
    RECOMMENDATION = "recommendation"
    ALERT = "alert"
    SUMMARY = "summary"


class InsightSeverity(str, Enum):
    """Severity levels for insights."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class TimeRange(str, Enum):
    """Time ranges for analytics queries."""
    LAST_HOUR = "1h"
    LAST_DAY = "24h"
    LAST_WEEK = "7d"
    LAST_MONTH = "30d"
    ALL_TIME = "all"


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class AnalyticsConfig:
    """Configuration for the Analytics Engine."""
    collection_interval_seconds: int = 60
    retention_days: int = 90
    max_metrics_per_type: int = 10000
    anomaly_detection_threshold: float = 2.0  # Standard deviations
    trend_window_size: int = 100
    enable_auto_insights: bool = True
    insight_generation_interval: int = 300  # 5 minutes


@dataclass
class MetricPoint:
    """A single metric data point."""
    metric_id: str = field(default_factory=lambda: f"metric-{uuid.uuid4().hex[:8]}")
    name: str = ""
    metric_type: MetricType = MetricType.COUNTER
    category: MetricCategory = MetricCategory.PERFORMANCE
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "type": self.metric_type.value,
            "category": self.category.value,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


@dataclass
class MetricSeries:
    """A time series of metric points."""
    name: str = ""
    metric_type: MetricType = MetricType.COUNTER
    category: MetricCategory = MetricCategory.PERFORMANCE
    points: list[MetricPoint] = field(default_factory=list)
    total: float = 0.0
    min_value: float = float("inf")
    max_value: float = float("-inf")
    avg_value: float = 0.0
    count: int = 0
    latest: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "category": self.category.value,
            "point_count": len(self.points),
            "total": self.total,
            "min": self.min_value if self.min_value != float("inf") else 0,
            "max": self.max_value if self.max_value != float("-inf") else 0,
            "avg": self.avg_value,
            "latest": self.latest,
        }


@dataclass
class AnalyticsInsight:
    """A generated insight from analytics data."""
    insight_id: str = field(default_factory=lambda: f"insight-{uuid.uuid4().hex[:8]}")
    insight_type: InsightType = InsightType.TREND
    severity: InsightSeverity = InsightSeverity.INFO
    title: str = ""
    description: str = ""
    metrics: list[str] = field(default_factory=list)
    recommendation: str = ""
    confidence: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "type": self.insight_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "metrics": self.metrics,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "data": self.data,
            "created_at": self.created_at,
        }


@dataclass
class AgentPerformance:
    """Performance metrics for a specific agent."""
    agent_id: str = ""
    agent_name: str = ""
    total_requests: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0
    error_count: int = 0
    tool_usage_count: int = 0
    avg_tokens_per_request: float = 0.0
    last_active: str = ""
    uptime_percentage: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": self.success_rate,
            "error_count": self.error_count,
            "tool_usage_count": self.tool_usage_count,
            "avg_tokens_per_request": self.avg_tokens_per_request,
            "last_active": self.last_active,
            "uptime_percentage": self.uptime_percentage,
        }


@dataclass
class AnalyticsSummary:
    """Comprehensive analytics summary."""
    total_requests: int = 0
    total_tokens: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0
    active_agents: int = 0
    total_conversations: int = 0
    total_tools_used: int = 0
    top_agents: list[AgentPerformance] = field(default_factory=list)
    metrics_count: int = 0
    insights_count: int = 0
    period: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_errors": self.total_errors,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": self.success_rate,
            "active_agents": self.active_agents,
            "total_conversations": self.total_conversations,
            "total_tools_used": self.total_tools_used,
            "top_agents": [a.to_dict() for a in self.top_agents],
            "metrics_count": self.metrics_count,
            "insights_count": self.insights_count,
            "period": self.period,
        }


# ═══════════════════════════════════════════════════════════
# Analytics Engine Implementation
# ═══════════════════════════════════════════════════════════

class AgentAnalyticsEngine:
    """Real-time analytics, metrics, and insight generation."""

    def __init__(self, config: AnalyticsConfig | None = None):
        self.config = config or AnalyticsConfig()
        self._metrics: dict[str, list[MetricPoint]] = defaultdict(list)
        self._insights: list[AnalyticsInsight] = []
        self._agent_performance: dict[str, AgentPerformance] = {}
        self._start_time: float = time.monotonic()
        self._total_requests: int = 0
        self._total_tokens: int = 0
        self._total_errors: int = 0
        self._total_latency: float = 0.0
        self._total_tools: int = 0
        logger.info("AgentAnalyticsEngine initialized")

    # ── Metric Recording ─────────────────────────────────

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.COUNTER,
        category: MetricCategory = MetricCategory.PERFORMANCE,
        labels: dict[str, str] | None = None,
    ) -> MetricPoint:
        """Record a metric data point."""
        point = MetricPoint(
            name=name,
            metric_type=metric_type,
            category=category,
            value=value,
            labels=labels or {},
        )

        self._metrics[name].append(point)

        # Enforce limit
        if len(self._metrics[name]) > self.config.max_metrics_per_type:
            self._metrics[name] = self._metrics[name][-self.config.max_metrics_per_type:]

        return point

    def record_request(
        self,
        agent_id: str,
        agent_name: str = "",
        latency_ms: float = 0.0,
        tokens: int = 0,
        success: bool = True,
        tools_used: int = 0,
    ) -> None:
        """Record a complete request with all relevant metrics."""
        self._total_requests += 1
        self._total_tokens += tokens
        self._total_latency += latency_ms
        self._total_tools += tools_used

        if not success:
            self._total_errors += 1

        # Update agent performance
        if agent_id not in self._agent_performance:
            self._agent_performance[agent_id] = AgentPerformance(
                agent_id=agent_id,
                agent_name=agent_name,
            )

        perf = self._agent_performance[agent_id]
        perf.total_requests += 1
        perf.total_tokens += tokens
        perf.avg_latency_ms = (
            (perf.avg_latency_ms * (perf.total_requests - 1) + latency_ms)
            / perf.total_requests
        )
        perf.error_count += 0 if success else 1
        perf.success_rate = (
            (perf.total_requests - perf.error_count) / perf.total_requests * 100
        )
        perf.tool_usage_count += tools_used
        perf.avg_tokens_per_request = perf.total_tokens / perf.total_requests
        perf.last_active = datetime.now(timezone.utc).isoformat()

        # Record individual metrics
        self.record_metric("request_count", 1, MetricType.COUNTER, MetricCategory.USAGE,
                          {"agent_id": agent_id})
        self.record_metric("latency_ms", latency_ms, MetricType.HISTOGRAM, MetricCategory.PERFORMANCE,
                          {"agent_id": agent_id})
        self.record_metric("token_usage", tokens, MetricType.COUNTER, MetricCategory.USAGE,
                          {"agent_id": agent_id})
        if not success:
            self.record_metric("error_count", 1, MetricType.COUNTER, MetricCategory.QUALITY,
                              {"agent_id": agent_id})

    def record_tool_usage(self, tool_name: str, success: bool, duration_ms: float) -> None:
        """Record tool usage metrics."""
        self.record_metric("tool_usage", 1, MetricType.COUNTER, MetricCategory.USAGE,
                          {"tool": tool_name, "success": str(success)})
        self.record_metric("tool_duration_ms", duration_ms, MetricType.HISTOGRAM,
                          MetricCategory.PERFORMANCE, {"tool": tool_name})

    # ── Metric Queries ───────────────────────────────────

    def get_metric(
        self,
        name: str,
        time_range: TimeRange = TimeRange.LAST_HOUR,
    ) -> MetricSeries:
        """Get a metric series for the specified time range."""
        points = self._metrics.get(name, [])
        cutoff = self._get_cutoff_time(time_range)

        filtered = [p for p in points if p.timestamp >= cutoff]
        return self._compute_series(name, filtered)

    def get_all_metrics(self, category: MetricCategory | None = None) -> dict[str, MetricSeries]:
        """Get all metric series."""
        result: dict[str, MetricSeries] = {}
        for name, points in self._metrics.items():
            if category and points and points[0].category != category:
                continue
            result[name] = self._compute_series(name, points[-100:])
        return result

    def get_metric_names(self) -> list[str]:
        """Get all metric names."""
        return list(self._metrics.keys())

    def get_latest_value(self, name: str) -> float | None:
        """Get the latest value for a metric."""
        points = self._metrics.get(name, [])
        if points:
            return points[-1].value
        return None

    # ── Agent Performance ────────────────────────────────

    def get_agent_performance(self, agent_id: str) -> AgentPerformance | None:
        """Get performance data for a specific agent."""
        return self._agent_performance.get(agent_id)

    def get_all_agent_performance(self) -> list[AgentPerformance]:
        """Get performance data for all agents."""
        return list(self._agent_performance.values())

    def get_top_agents(self, limit: int = 10, sort_by: str = "total_requests") -> list[AgentPerformance]:
        """Get top-performing agents sorted by a metric."""
        agents = list(self._agent_performance.values())
        if sort_by == "success_rate":
            agents.sort(key=lambda a: a.success_rate, reverse=True)
        elif sort_by == "avg_latency_ms":
            agents.sort(key=lambda a: a.avg_latency_ms)
        else:
            agents.sort(key=lambda a: a.total_requests, reverse=True)
        return agents[:limit]

    # ── Insight Generation ───────────────────────────────

    def generate_insights(self) -> list[AnalyticsInsight]:
        """Generate insights from collected metrics."""
        insights: list[AnalyticsInsight] = []

        # Check for high error rates
        if self._total_requests > 0:
            error_rate = (self._total_errors / self._total_requests) * 100
            if error_rate > 10:
                insights.append(AnalyticsInsight(
                    insight_type=InsightType.ALERT,
                    severity=InsightSeverity.CRITICAL if error_rate > 25 else InsightSeverity.WARNING,
                    title="High Error Rate Detected",
                    description=f"Error rate is {error_rate:.1f}% across {self._total_requests} requests",
                    recommendation="Review recent error logs and check API connectivity",
                    confidence=0.95,
                    data={"error_rate": error_rate, "total_errors": self._total_errors},
                ))

        # Check for latency spikes
        if self._total_requests > 0:
            avg_latency = self._total_latency / self._total_requests
            if avg_latency > 5000:
                insights.append(AnalyticsInsight(
                    insight_type=InsightType.ANOMALY,
                    severity=InsightSeverity.WARNING,
                    title="High Average Latency",
                    description=f"Average latency is {avg_latency:.0f}ms",
                    recommendation="Consider optimizing model selection or reducing context size",
                    confidence=0.85,
                ))

        # Check for underutilized agents
        for agent_id, perf in self._agent_performance.items():
            if perf.total_requests < 5 and perf.last_active:
                # Check if agent was created recently
                try:
                    last_active = datetime.fromisoformat(perf.last_active)
                    if (datetime.now(timezone.utc) - last_active).days > 7:
                        insights.append(AnalyticsInsight(
                            insight_type=InsightType.RECOMMENDATION,
                            severity=InsightSeverity.INFO,
                            title=f"Underutilized Agent: {perf.agent_name}",
                            description=f"Agent {perf.agent_name} has only {perf.total_requests} requests",
                            recommendation="Consider removing or repurposing this agent",
                            confidence=0.7,
                        ))
                except (ValueError, TypeError):
                    pass

        # Trend insight
        if self._total_requests > 100:
            insights.append(AnalyticsInsight(
                insight_type=InsightType.SUMMARY,
                severity=InsightSeverity.INFO,
                title="System Health Summary",
                description=f"Processed {self._total_requests} requests with {self._total_errors} errors",
                recommendation="System is operating within normal parameters",
                confidence=0.9,
                data={
                    "total_requests": self._total_requests,
                    "total_tokens": self._total_tokens,
                    "total_errors": self._total_errors,
                },
            ))

        self._insights = insights
        return insights

    def get_insights(
        self,
        insight_type: InsightType | None = None,
        severity: InsightSeverity | None = None,
        limit: int = 50,
    ) -> list[AnalyticsInsight]:
        """Get generated insights with filtering."""
        insights = self._insights
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]
        if severity:
            insights = [i for i in insights if i.severity == severity]

        insights.sort(key=lambda i: i.created_at, reverse=True)
        return insights[:limit]

    # ── Summary and Dashboard ────────────────────────────

    def get_summary(self) -> AnalyticsSummary:
        """Get comprehensive analytics summary."""
        summary = AnalyticsSummary()
        summary.total_requests = self._total_requests
        summary.total_tokens = self._total_tokens
        summary.total_errors = self._total_errors
        summary.total_tools_used = self._total_tools
        summary.metrics_count = sum(len(p) for p in self._metrics.values())
        summary.insights_count = len(self._insights)
        summary.active_agents = sum(
            1 for p in self._agent_performance.values() if p.total_requests > 0
        )
        summary.period = f"Since {datetime.fromtimestamp(self._start_time, timezone.utc).isoformat()}"

        if self._total_requests > 0:
            summary.avg_latency_ms = self._total_latency / self._total_requests
            summary.success_rate = (
                (self._total_requests - self._total_errors) / self._total_requests * 100
            )

        summary.top_agents = self.get_top_agents(5)
        return summary

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get pre-computed data for dashboard visualization."""
        summary = self.get_summary()

        # Time series for charts
        request_timeseries = []
        for point in self._metrics.get("request_count", [])[-50:]:
            request_timeseries.append({
                "timestamp": point.timestamp,
                "value": point.value,
            })

        latency_timeseries = []
        for point in self._metrics.get("latency_ms", [])[-50:]:
            latency_timeseries.append({
                "timestamp": point.timestamp,
                "value": point.value,
            })

        # Agent breakdown
        agent_breakdown = []
        for perf in self.get_top_agents(10):
            agent_breakdown.append({
                "name": perf.agent_name,
                "requests": perf.total_requests,
                "success_rate": perf.success_rate,
                "avg_latency_ms": perf.avg_latency_ms,
            })

        return {
            "summary": summary.to_dict(),
            "request_timeseries": request_timeseries,
            "latency_timeseries": latency_timeseries,
            "agent_breakdown": agent_breakdown,
            "insights": [i.to_dict() for i in self._insights[-5:]],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_metrics": sum(len(p) for p in self._metrics.values()),
            "unique_metric_names": len(self._metrics),
            "total_insights": len(self._insights),
            "tracked_agents": len(self._agent_performance),
            "uptime_seconds": time.monotonic() - self._start_time,
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
        }

    def reset(self) -> None:
        """Reset the analytics engine."""
        self._metrics.clear()
        self._insights.clear()
        self._agent_performance.clear()
        self._start_time = time.monotonic()
        self._total_requests = 0
        self._total_tokens = 0
        self._total_errors = 0
        self._total_latency = 0.0
        self._total_tools = 0
        logger.info("AgentAnalyticsEngine reset")

    # ── Internal Helpers ─────────────────────────────────

    def _get_cutoff_time(self, time_range: TimeRange) -> str:
        """Get cutoff timestamp for a time range."""
        now = datetime.now(timezone.utc)
        if time_range == TimeRange.LAST_HOUR:
            cutoff = now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_DAY:
            cutoff = now - timedelta(days=1)
        elif time_range == TimeRange.LAST_WEEK:
            cutoff = now - timedelta(days=7)
        elif time_range == TimeRange.LAST_MONTH:
            cutoff = now - timedelta(days=30)
        else:
            return "1970-01-01T00:00:00+00:00"
        return cutoff.isoformat()

    def _compute_series(self, name: str, points: list[MetricPoint]) -> MetricSeries:
        """Compute a metric series from points."""
        if not points:
            return MetricSeries(name=name)

        series = MetricSeries(
            name=name,
            metric_type=points[0].metric_type if points else MetricType.COUNTER,
            category=points[0].category if points else MetricCategory.PERFORMANCE,
            points=points,
            count=len(points),
            latest=points[-1].value,
        )

        values = [p.value for p in points]
        series.total = sum(values)
        series.min_value = min(values)
        series.max_value = max(values)
        series.avg_value = series.total / len(values)

        return series


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_analytics_engine: AgentAnalyticsEngine | None = None


def get_analytics_engine() -> AgentAnalyticsEngine:
    """Get or create the global Analytics Engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AgentAnalyticsEngine()
    return _analytics_engine


def reset_analytics_engine() -> None:
    """Reset the global Analytics Engine instance."""
    global _analytics_engine
    if _analytics_engine:
        _analytics_engine.reset()
    _analytics_engine = None