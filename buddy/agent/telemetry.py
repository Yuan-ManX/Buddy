"""
Buddy Telemetry Engine - Observability and Monitoring

Provides comprehensive observability for all agent operations, including
metrics collection, tracing, logging, and performance monitoring across
the entire Buddy platform.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    """Types of telemetry metrics."""
    COUNTER = "counter"          # Monotonically increasing count
    GAUGE = "gauge"              # Point-in-time value
    HISTOGRAM = "histogram"      # Distribution of values
    TIMER = "timer"              # Duration measurement
    RATE = "rate"                # Rate per unit time


class TraceLevel(str, Enum):
    """Trace detail levels."""
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    labels: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class TraceSpan:
    """A single trace span for distributed tracing."""
    span_id: str
    trace_id: str
    name: str
    parent_id: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "ok"
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0

    def add_event(self, name: str, attributes: dict | None = None):
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def finish(self, status: str = "ok"):
        self.end_time = time.time()
        self.status = status


class MetricRegistry:
    """Registry for collecting and querying metrics."""

    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._timers: dict[str, list[float]] = defaultdict(list)
        self._rates: dict[str, list[tuple[float, float]]] = defaultdict(list)

    def increment(self, name: str, value: float = 1, labels: dict | None = None):
        """Increment a counter."""
        key = self._build_key(name, labels)
        self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: dict | None = None):
        """Set a gauge value."""
        key = self._build_key(name, labels)
        self._gauges[key] = value

    def record_histogram(self, name: str, value: float, labels: dict | None = None):
        """Record a histogram value."""
        key = self._build_key(name, labels)
        self._histograms[key].append(value)

    def record_timer(self, name: str, duration_ms: float, labels: dict | None = None):
        """Record a timer value."""
        key = self._build_key(name, labels)
        self._timers[key].append(duration_ms)

    def record_rate(self, name: str, count: float, labels: dict | None = None):
        """Record a rate measurement."""
        key = self._build_key(name, labels)
        self._rates[key].append((time.time(), count))

    def _build_key(self, name: str, labels: dict | None = None) -> str:
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def get_stats(self) -> dict:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histogram_counts": {k: len(v) for k, v in self._histograms.items()},
            "timer_counts": {k: len(v) for k, v in self._timers.items()},
        }


class TraceCollector:
    """Collects and manages distributed traces."""

    def __init__(self):
        self._traces: dict[str, list[TraceSpan]] = defaultdict(list)
        self._active_spans: dict[str, TraceSpan] = {}

    def start_trace(self, name: str, attributes: dict | None = None) -> TraceSpan:
        """Start a new trace."""
        trace_id = f"trace-{uuid.uuid4().hex[:16]}"
        span = TraceSpan(
            span_id=f"span-{uuid.uuid4().hex[:8]}",
            trace_id=trace_id,
            name=name,
            attributes=attributes or {},
        )
        self._traces[trace_id].append(span)
        self._active_spans[span.span_id] = span
        return span

    def start_span(self, name: str, parent_span: TraceSpan, attributes: dict | None = None) -> TraceSpan:
        """Start a child span."""
        span = TraceSpan(
            span_id=f"span-{uuid.uuid4().hex[:8]}",
            trace_id=parent_span.trace_id,
            name=name,
            parent_id=parent_span.span_id,
            attributes=attributes or {},
        )
        self._traces[parent_span.trace_id].append(span)
        self._active_spans[span.span_id] = span
        return span

    def finish_span(self, span: TraceSpan, status: str = "ok"):
        """Finish a span."""
        span.finish(status)
        self._active_spans.pop(span.span_id, None)

    def get_trace(self, trace_id: str) -> list[dict] | None:
        """Get all spans for a trace."""
        if trace_id in self._traces:
            return [
                {
                    "span_id": s.span_id,
                    "parent_id": s.parent_id,
                    "name": s.name,
                    "duration_ms": s.duration_ms,
                    "status": s.status,
                    "events": s.events,
                }
                for s in self._traces[trace_id]
            ]
        return None

    def get_stats(self) -> dict:
        return {
            "total_traces": len(self._traces),
            "active_spans": len(self._active_spans),
            "total_spans": sum(len(s) for s in self._traces.values()),
        }


class TelemetryEngine:
    """Central telemetry engine for Buddy platform observability.

    Collects metrics, traces, and logs from all agent operations,
    providing real-time monitoring, performance analysis, and
    debugging capabilities across the entire platform.
    """

    def __init__(self):
        self.metrics = MetricRegistry()
        self.traces = TraceCollector()
        self._event_log: list[dict] = []
        self._start_time = time.time()

    def record_agent_interaction(
        self,
        agent_id: str,
        operation: str,
        duration_ms: float,
        tokens_used: int = 0,
        success: bool = True,
    ):
        """Record an agent interaction metric."""
        self.metrics.increment("agent.interactions.total", labels={"agent_id": agent_id})
        self.metrics.record_timer("agent.interactions.duration", duration_ms, {"agent_id": agent_id, "operation": operation})
        if tokens_used:
            self.metrics.increment("agent.tokens.total", tokens_used, {"agent_id": agent_id})
        if not success:
            self.metrics.increment("agent.errors.total", labels={"agent_id": agent_id, "operation": operation})

    def record_tool_execution(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
    ):
        """Record a tool execution metric."""
        self.metrics.increment("tool.executions.total", labels={"tool": tool_name})
        self.metrics.record_timer("tool.executions.duration", duration_ms, {"tool": tool_name})
        if not success:
            self.metrics.increment("tool.errors.total", labels={"tool": tool_name})

    def record_model_request(
        self,
        model_id: str,
        tokens_input: int,
        tokens_output: int,
        duration_ms: float,
        cost: float,
    ):
        """Record a model request metric."""
        self.metrics.increment("model.requests.total", labels={"model": model_id})
        self.metrics.increment("model.tokens.input", tokens_input, {"model": model_id})
        self.metrics.increment("model.tokens.output", tokens_output, {"model": model_id})
        self.metrics.record_timer("model.requests.duration", duration_ms, {"model": model_id})
        self.metrics.increment("model.cost.total", cost, {"model": model_id})

    def log_event(self, level: TraceLevel, message: str, context: dict | None = None):
        """Log an event."""
        event = {
            "level": level.value,
            "message": message,
            "context": context or {},
            "timestamp": time.time(),
        }
        self._event_log.append(event)
        if len(self._event_log) > 10000:
            self._event_log = self._event_log[-5000:]

    def get_stats(self) -> dict:
        return {
            "uptime_seconds": time.time() - self._start_time,
            "metrics": self.metrics.get_stats(),
            "traces": self.traces.get_stats(),
            "event_count": len(self._event_log),
            "recent_events": self._event_log[-20:],
        }


# Global telemetry engine instance
_telemetry_engine: TelemetryEngine | None = None


def get_telemetry_engine() -> TelemetryEngine:
    """Get or create the global telemetry engine."""
    global _telemetry_engine
    if _telemetry_engine is None:
        _telemetry_engine = TelemetryEngine()
    return _telemetry_engine