from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

"""
Agent Tracing Pipeline
======================

A self-contained, OpenTelemetry-style distributed tracing and observability
module for the Buddy AI agent runtime.

This module provides the building blocks required to record, correlate, and
introspect the execution of an AI agent as a tree of *spans* grouped into
*traces*. A trace represents a single end-to-end logical operation (for
example, handling one user request), while spans represent the finer-grained
steps that make up that operation (a tool call, a sub-agent invocation, a
reasoning step, etc.).

The design intentionally mirrors the core concepts of OpenTelemetry so that
the data produced here can be reasoned about using the same mental model:

  * ``SpanContext``      - immutable identity of a span within a trace.
  * ``SpanEvent``        - a timestamped log record attached to a span.
  * ``SpanLink``         - a cross-trace reference between two spans.
  * ``TraceSpan``        - a unit of work with timing, status, attributes.
  * ``Trace``            - a collection of spans sharing a single trace id.
  * ``TraceStats``       - aggregated statistics across all stored traces.

The :class:`AgentTracingPipeline` is the central, thread-safe registry that
owns all traces and active spans. It is exposed as a process-wide singleton
through :func:`get_tracing_pipeline` so that any component in the agent
runtime can record telemetry without explicit wiring.

Thread safety
-------------
Every mutating operation is guarded by a single reentrant-friendly
``threading.Lock``. Reads also acquire the lock so that callers observe a
consistent snapshot of the internal state. Returned objects are live
references; callers that need an isolated snapshot should use the
``to_dict`` helpers exposed by every dataclass.

The module has no third-party dependencies and is fully self-contained.
"""

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SpanKind(str, Enum):
    """Categorizes the role of a span within a trace.

    The values mirror the OpenTelemetry ``SpanKind`` enumeration and extend
    it with two agent-specific kinds (``AGENT`` and ``TOOL``).
    """

    # Internal work that does not cross a process or component boundary.
    INTERNAL = "internal"
    # The span represents handling of an incoming request.
    SERVER = "server"
    # The span represents an outgoing request to a remote system.
    CLIENT = "client"
    # The span produces work that is asynchronously consumed elsewhere.
    PRODUCER = "producer"
    # The span consumes work that was asynchronously produced elsewhere.
    CONSUMER = "consumer"
    # The span represents an agent-level operation (planning, reasoning...).
    AGENT = "agent"
    # The span represents a tool invocation performed by an agent.
    TOOL = "tool"


class SpanStatus(str, Enum):
    """The execution status of a span.

    These values follow the OpenTelemetry status code semantics.
    """

    # The status has not been set yet (still in flight or unset on purpose).
    UNSET = "unset"
    # The span completed successfully.
    OK = "ok"
    # The span completed with an error.
    ERROR = "error"
    # The span was cancelled before completing.
    CANCELLED = "cancelled"


class SamplingDecision(str, Enum):
    """Whether a trace/span should be sampled.

    Sampling controls which traces are recorded and exported. In this
    pipeline every created trace is recorded by default (``SAMPLED``), but
    the enum is kept for API completeness and future use.
    """

    # The trace is not sampled; no data is recorded.
    NOT_SAMPLED = "not_sampled"
    # The trace is sampled and recorded.
    SAMPLED = "sampled"
    # The trace is recorded but not flagged for export.
    RECORD_ONLY = "record_only"


class TraceFlags(str, Enum):
    """Bit-packed style trace flags.

    Only the ``SAMPLED`` flag is modeled here, matching the subset of
    OpenTelemetry trace flags that is relevant for this pipeline.
    """

    # No flags are set.
    NONE = "none"
    # The sampled flag is set.
    SAMPLED = "sampled"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SpanContext:
    """Immutable identity information for a span.

    A ``SpanContext`` carries the identifiers required to correlate a span
    with the rest of its trace and with linked traces.
    """

    trace_id: str = ""
    span_id: str = ""
    parent_span_id: str | None = None
    trace_flags: TraceFlags = TraceFlags.NONE
    sampling_decision: SamplingDecision = SamplingDecision.SAMPLED
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation with enums as their values."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_flags": self.trace_flags.value
            if isinstance(self.trace_flags, TraceFlags)
            else self.trace_flags,
            "sampling_decision": self.sampling_decision.value
            if isinstance(self.sampling_decision, SamplingDecision)
            else self.sampling_decision,
            "created_at": self.created_at,
        }


@dataclass
class SpanEvent:
    """A timestamped log record attached to a span.

    Events are useful for recording discrete observations that occur during
    the lifetime of a span, such as a checkpoint, a warning, or a decision
    point.
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    level: str = "info"

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation with fresh container copies."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "name": self.name,
            "payload": dict(self.payload),
            "level": self.level,
        }


@dataclass
class SpanLink:
    """A cross-trace link between two spans.

    Links are used to express causal relationships that cross trace
    boundaries, for example a long-running operation that fans out into
    multiple independent traces.
    """

    link_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: str = ""
    span_id: str = ""
    relationship: str = "follows_from"
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation with fresh container copies."""
        return {
            "link_id": self.link_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "relationship": self.relationship,
            "attributes": dict(self.attributes),
        }


@dataclass
class TraceSpan:
    """A unit of work within a trace.

    A ``TraceSpan`` records the start/end timing, status, structured
    attributes, events, and links for a single step of execution.
    """

    span_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: str = ""
    parent_span_id: str | None = None
    name: str = ""
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    links: list[SpanLink] = field(default_factory=list)
    duration_ms: float | None = None
    agent_id: str = ""
    resource: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation.

        Enum fields are converted to their ``.value`` and every list/dict
        is replaced with a fresh copy so the returned object can be safely
        mutated by callers without affecting internal state.
        """
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value if isinstance(self.kind, SpanKind) else self.kind,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value
            if isinstance(self.status, SpanStatus)
            else self.status,
            "status_message": self.status_message,
            "attributes": dict(self.attributes),
            "events": [e.to_dict() if isinstance(e, SpanEvent) else e for e in self.events],
            "links": [l.to_dict() if isinstance(l, SpanLink) else l for l in self.links],
            "duration_ms": self.duration_ms,
            "agent_id": self.agent_id,
            "resource": self.resource,
        }


@dataclass
class Trace:
    """A collection of spans sharing a single trace id.

    Every trace has exactly one root span (the span with no parent) and an
    arbitrary number of child spans organized as a tree.
    """

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    root_span_id: str = ""
    spans: dict[str, TraceSpan] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: SpanStatus = SpanStatus.UNSET
    span_count: int = 0
    error_count: int = 0
    agent_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation with fresh container copies."""
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "spans": {
                k: (v.to_dict() if isinstance(v, TraceSpan) else v)
                for k, v in self.spans.items()
            },
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value
            if isinstance(self.status, SpanStatus)
            else self.status,
            "span_count": self.span_count,
            "error_count": self.error_count,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
        }


@dataclass
class TraceStats:
    """Aggregated statistics across all traces held by the pipeline."""

    total_traces: int = 0
    total_spans: int = 0
    spans_by_kind: dict[str, int] = field(default_factory=dict)
    spans_by_status: dict[str, int] = field(default_factory=dict)
    avg_trace_duration_ms: float = 0.0
    error_rate: float = 0.0
    sampled_traces: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation with fresh container copies."""
        return {
            "total_traces": self.total_traces,
            "total_spans": self.total_spans,
            "spans_by_kind": dict(self.spans_by_kind),
            "spans_by_status": dict(self.spans_by_status),
            "avg_trace_duration_ms": self.avg_trace_duration_ms,
            "error_rate": self.error_rate,
            "sampled_traces": self.sampled_traces,
        }


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class AgentTracingPipeline:
    """Thread-safe registry for agent execution traces.

    The pipeline is the single owner of all :class:`Trace` and active
    :class:`TraceSpan` objects in the process. It exposes a small, focused
    API for starting/ending traces and spans, annotating them with events,
    attributes and links, and querying the recorded data.

    Capacity is bounded by ``MAX_TRACES`` (oldest traces are evicted) and
    ``MAX_SPANS_PER_TRACE`` (attempting to exceed the limit returns
    ``None`` from :meth:`start_span`).

    All public methods are thread-safe.
    """

    def __init__(self) -> None:
        """Initialize an empty pipeline with default capacity limits."""
        # Map of trace_id -> Trace for all recorded traces.
        self._traces: dict[str, Trace] = {}
        # Map of span_id -> TraceSpan for spans that have not ended yet.
        self._active_spans: dict[str, TraceSpan] = {}
        # Single lock guarding every mutation of internal state.
        self._lock = threading.Lock()
        # Maximum number of traces retained. Older traces are evicted.
        self.MAX_TRACES = 500
        # Maximum number of spans allowed within a single trace.
        self.MAX_SPANS_PER_TRACE = 200

    # ------------------------------------------------------------------
    # Trace lifecycle
    # ------------------------------------------------------------------

    def start_trace(
        self,
        agent_id: str,
        root_span_name: str,
        resource: str = "",
        attributes: dict | None = None,
    ) -> Trace:
        """Create a new trace and its root span.

        The root span is created with :attr:`SpanKind.AGENT` and registered
        as an active span so it can be ended through :meth:`end_span`.

        Args:
            agent_id: Identifier of the agent owning this trace.
            root_span_name: Human-readable name of the root span.
            resource: Optional resource descriptor (e.g. model or tool name).
            attributes: Optional initial attributes for the root span.

        Returns:
            The newly created :class:`Trace`.
        """
        with self._lock:
            trace_id = uuid.uuid4().hex
            root_span_id = uuid.uuid4().hex
            now = time.time()
            attrs = dict(attributes) if attributes else {}

            root_span = TraceSpan(
                span_id=root_span_id,
                trace_id=trace_id,
                parent_span_id=None,
                name=root_span_name,
                kind=SpanKind.AGENT,
                start_time=now,
                end_time=None,
                status=SpanStatus.UNSET,
                status_message="",
                attributes=attrs,
                events=[],
                links=[],
                duration_ms=None,
                agent_id=agent_id,
                resource=resource,
            )

            trace = Trace(
                trace_id=trace_id,
                root_span_id=root_span_id,
                spans={root_span_id: root_span},
                start_time=now,
                end_time=None,
                status=SpanStatus.UNSET,
                span_count=1,
                error_count=0,
                agent_id=agent_id,
                created_at=now,
            )

            self._traces[trace_id] = trace
            self._active_spans[root_span_id] = root_span

            # Evict the oldest trace if we exceeded the capacity.
            if len(self._traces) > self.MAX_TRACES:
                oldest_id = min(
                    self._traces, key=lambda tid: self._traces[tid].created_at
                )
                evicted = self._traces.pop(oldest_id, None)
                if evicted is not None:
                    # Drop any still-active spans belonging to the evicted trace.
                    for sid in list(self._active_spans.keys()):
                        if sid in evicted.spans:
                            self._active_spans.pop(sid, None)

            return trace

    def start_span(
        self,
        trace_id: str,
        name: str,
        parent_span_id: str | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        agent_id: str = "",
        resource: str = "",
        attributes: dict | None = None,
    ) -> TraceSpan | None:
        """Create a child span under ``parent_span_id`` within ``trace_id``.

        Args:
            trace_id: The trace the new span belongs to.
            name: Human-readable name of the span.
            parent_span_id: Parent span id. ``None`` creates an additional
                root-like span (rare; prefer :meth:`start_trace`).
            kind: The :class:`SpanKind` for this span.
            agent_id: Agent id. Falls back to the trace's agent id if empty.
            resource: Optional resource descriptor.
            attributes: Optional initial attributes.

        Returns:
            The new :class:`TraceSpan`, or ``None`` if the trace does not
            exist or the per-trace span cap has been reached.
        """
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return None
            if trace.span_count >= self.MAX_SPANS_PER_TRACE:
                return None

            span_id = uuid.uuid4().hex
            now = time.time()
            attrs = dict(attributes) if attributes else {}
            effective_agent_id = agent_id if agent_id else trace.agent_id

            span = TraceSpan(
                span_id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                name=name,
                kind=kind,
                start_time=now,
                end_time=None,
                status=SpanStatus.UNSET,
                status_message="",
                attributes=attrs,
                events=[],
                links=[],
                duration_ms=None,
                agent_id=effective_agent_id,
                resource=resource,
            )

            trace.spans[span_id] = span
            trace.span_count = len(trace.spans)
            self._active_spans[span_id] = span
            return span

    def end_span(
        self,
        span_id: str,
        status: SpanStatus = SpanStatus.OK,
        status_message: str = "",
    ) -> TraceSpan | None:
        """Finalize an active span.

        Sets ``end_time``, ``duration_ms``, ``status`` and
        ``status_message`` on the span, removes it from the active set, and
        updates the owning trace (error bookkeeping and root-span closing).

        Args:
            span_id: The id of the span to end.
            status: Final status of the span.
            status_message: Optional human-readable status detail.

        Returns:
            The ended :class:`TraceSpan`, or ``None`` if no active span with
            that id was found.
        """
        with self._lock:
            span = self._active_spans.pop(span_id, None)
            if span is None:
                return None

            now = time.time()
            span.end_time = now
            span.duration_ms = (now - span.start_time) * 1000.0
            span.status = status
            span.status_message = status_message

            trace = self._traces.get(span.trace_id)
            if trace is not None:
                if status == SpanStatus.ERROR:
                    trace.error_count += 1
                    trace.status = SpanStatus.ERROR
                elif status == SpanStatus.CANCELLED:
                    if trace.status == SpanStatus.UNSET:
                        trace.status = SpanStatus.CANCELLED
                elif status == SpanStatus.OK and trace.status == SpanStatus.UNSET:
                    trace.status = SpanStatus.OK

                # Closing the root span closes the trace.
                if span.span_id == trace.root_span_id:
                    trace.end_time = now
                    if trace.status == SpanStatus.UNSET:
                        trace.status = status

            return span

    # ------------------------------------------------------------------
    # Span annotation
    # ------------------------------------------------------------------

    def add_span_event(
        self,
        span_id: str,
        name: str,
        payload: dict | None = None,
        level: str = "info",
    ) -> SpanEvent | None:
        """Append a :class:`SpanEvent` to a span.

        The span may be active or already ended; events can be attached to
        any span currently known to the pipeline.

        Args:
            span_id: The target span id.
            name: Event name.
            payload: Optional structured payload.
            level: Severity level string (e.g. ``"info"``, ``"warn"``).

        Returns:
            The created :class:`SpanEvent`, or ``None`` if the span was not
            found.
        """
        with self._lock:
            span = self._find_span(span_id)
            if span is None:
                return None
            event = SpanEvent(
                event_id=uuid.uuid4().hex,
                timestamp=time.time(),
                name=name,
                payload=dict(payload) if payload else {},
                level=level,
            )
            span.events.append(event)
            return event

    def add_span_attribute(self, span_id: str, key: str, value: Any) -> bool:
        """Set or update a single attribute on a span.

        Args:
            span_id: The target span id.
            key: Attribute key.
            value: Attribute value (any JSON-serializable value).

        Returns:
            ``True`` if the attribute was set, ``False`` if the span was not
            found.
        """
        with self._lock:
            span = self._find_span(span_id)
            if span is None:
                return False
            span.attributes[key] = value
            return True

    def link_spans(
        self,
        span_id: str,
        linked_trace_id: str,
        linked_span_id: str,
        relationship: str = "follows_from",
    ) -> SpanLink | None:
        """Add a cross-trace :class:`SpanLink` to a span.

        Args:
            span_id: The span to attach the link to.
            linked_trace_id: Trace id of the linked span.
            linked_span_id: Span id of the linked span.
            relationship: Relationship type (default ``"follows_from"``).

        Returns:
            The created :class:`SpanLink`, or ``None`` if the source span
            was not found.
        """
        with self._lock:
            span = self._find_span(span_id)
            if span is None:
                return None
            link = SpanLink(
                link_id=uuid.uuid4().hex,
                trace_id=linked_trace_id,
                span_id=linked_span_id,
                relationship=relationship,
                attributes={},
            )
            span.links.append(link)
            return link

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_trace(self, trace_id: str) -> Trace | None:
        """Return the trace with ``trace_id`` or ``None``."""
        with self._lock:
            return self._traces.get(trace_id)

    def get_span(self, span_id: str) -> TraceSpan | None:
        """Return the span with ``span_id`` or ``None``."""
        with self._lock:
            return self._find_span(span_id)

    def list_traces(
        self,
        agent_id: str | None = None,
        status: SpanStatus | None = None,
        limit: int = 100,
    ) -> list[Trace]:
        """Return traces optionally filtered by agent and/or status.

        Results are ordered most-recent-first and truncated to ``limit``.

        Args:
            agent_id: Optional agent id filter.
            status: Optional status filter.
            limit: Maximum number of traces to return.

        Returns:
            A list of matching :class:`Trace` objects.
        """
        with self._lock:
            results: list[Trace] = []
            for trace in self._traces.values():
                if agent_id is not None and trace.agent_id != agent_id:
                    continue
                if status is not None and trace.status != status:
                    continue
                results.append(trace)
            results.sort(key=lambda t: t.created_at, reverse=True)
            return results[:limit]

    def get_trace_summary(self, trace_id: str) -> dict:
        """Return a compact summary dict for a trace.

        The summary includes the trace id, span count, total duration in
        milliseconds, error count, and the *critical path* - the list of
        span names along the root-to-leaf path with the greatest cumulative
        duration.

        Args:
            trace_id: The trace to summarize.

        Returns:
            A summary dict, or an empty dict if the trace was not found.
        """
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return {}

            duration_ms: float | None = None
            if trace.end_time is not None:
                duration_ms = (trace.end_time - trace.start_time) * 1000.0

            critical_path = self._compute_critical_path(trace)

            return {
                "trace_id": trace.trace_id,
                "span_count": trace.span_count,
                "duration_ms": duration_ms,
                "error_count": trace.error_count,
                "critical_path": critical_path,
            }

    def get_stats(self) -> TraceStats:
        """Aggregate statistics across all recorded traces.

        Returns:
            A :class:`TraceStats` instance summarizing totals, per-kind and
            per-status span counts, average trace duration, error rate, and
            the number of sampled traces.
        """
        with self._lock:
            total_traces = len(self._traces)
            total_spans = 0
            spans_by_kind: dict[str, int] = {}
            spans_by_status: dict[str, int] = {}
            durations: list[float] = []
            error_traces = 0

            for trace in self._traces.values():
                total_spans += trace.span_count
                if trace.status == SpanStatus.ERROR:
                    error_traces += 1
                if trace.end_time is not None:
                    durations.append((trace.end_time - trace.start_time) * 1000.0)
                for span in trace.spans.values():
                    kind_key = (
                        span.kind.value
                        if isinstance(span.kind, SpanKind)
                        else str(span.kind)
                    )
                    status_key = (
                        span.status.value
                        if isinstance(span.status, SpanStatus)
                        else str(span.status)
                    )
                    spans_by_kind[kind_key] = spans_by_kind.get(kind_key, 0) + 1
                    spans_by_status[status_key] = spans_by_status.get(status_key, 0) + 1

            avg_dur = sum(durations) / len(durations) if durations else 0.0
            error_rate = (error_traces / total_traces) if total_traces else 0.0
            # All recorded traces are considered sampled (100% sampling).
            sampled_traces = total_traces

            return TraceStats(
                total_traces=total_traces,
                total_spans=total_spans,
                spans_by_kind=spans_by_kind,
                spans_by_status=spans_by_status,
                avg_trace_duration_ms=avg_dur,
                error_rate=error_rate,
                sampled_traces=sampled_traces,
            )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> int:
        """Remove all traces and active spans.

        Returns:
            The number of traces that were cleared.
        """
        with self._lock:
            count = len(self._traces)
            self._traces.clear()
            self._active_spans.clear()
            return count

    # ------------------------------------------------------------------
    # Internal helpers (must be called with the lock held)
    # ------------------------------------------------------------------

    def _find_span(self, span_id: str) -> TraceSpan | None:
        """Locate a span by id, active or completed.

        Assumes the caller already holds ``self._lock``.
        """
        span = self._active_spans.get(span_id)
        if span is not None:
            return span
        for trace in self._traces.values():
            span = trace.spans.get(span_id)
            if span is not None:
                return span
        return None

    def _compute_critical_path(self, trace: Trace) -> list[str]:
        """Return the span names along the longest-duration root-to-leaf path.

        "Longest" is defined by the maximum cumulative span duration. Spans
        whose duration is not yet known (still active) contribute zero.

        Assumes the caller already holds ``self._lock``.
        """
        # Build a children map keyed by parent_span_id.
        children: dict[str | None, list[str]] = {}
        for span in trace.spans.values():
            children.setdefault(span.parent_span_id, []).append(span.span_id)

        def span_duration(span: TraceSpan) -> float:
            if span.duration_ms is not None:
                return span.duration_ms
            if span.end_time is not None:
                return (span.end_time - span.start_time) * 1000.0
            return 0.0

        best_path: list[str] = []
        best_duration: float = -1.0

        def dfs(span_id: str, path: list[str], total: float) -> None:
            nonlocal best_path, best_duration
            span = trace.spans.get(span_id)
            if span is None:
                return
            path = path + [span.name]
            total = total + span_duration(span)
            kids = children.get(span_id, [])
            if not kids:
                if total > best_duration:
                    best_duration = total
                    best_path = path
                return
            for kid in kids:
                dfs(kid, path, total)

        root_id = trace.root_span_id
        if root_id and root_id in trace.spans:
            dfs(root_id, [], 0.0)
        return best_path


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------

_global_tracing_pipeline: AgentTracingPipeline | None = None


def get_tracing_pipeline() -> AgentTracingPipeline:
    """Return the process-wide :class:`AgentTracingPipeline` singleton."""
    global _global_tracing_pipeline
    if _global_tracing_pipeline is None:
        _global_tracing_pipeline = AgentTracingPipeline()
    return _global_tracing_pipeline


def reset_tracing_pipeline() -> None:
    """Reset the process-wide singleton to ``None``.

    The next call to :func:`get_tracing_pipeline` will create a fresh
    pipeline. This is primarily useful for tests.
    """
    global _global_tracing_pipeline
    _global_tracing_pipeline = None
