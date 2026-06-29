from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ══════════════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════════════


class QuotaType(str, Enum):
    """Enumeration of the supported quota categories.

    Each category describes a dimension along which consumption can be
    measured and capped for a managed resource (typically a model or
    external API endpoint such as ``openai:gpt-4``).
    """

    REQUEST_COUNT = "REQUEST_COUNT"
    TOKEN_COUNT = "TOKEN_COUNT"
    COST_USD = "COST_USD"
    CONCURRENT = "CONCURRENT"
    CUSTOM = "CUSTOM"


class QuotaStatus(str, Enum):
    """Lifecycle status for a quota usage tracker.

    The status reflects the current ability of a resource to accept
    additional consumption within its active window.
    """

    ACTIVE = "ACTIVE"
    EXHAUSTED = "EXHAUSTED"
    THROTTLED = "THROTTLED"
    BLOCKED = "BLOCKED"
    COOLDOWN = "COOLDOWN"


class RetryStrategy(str, Enum):
    """Strategies for computing retry back-off delays.

    The strategy controls how the delay between successive retry attempts
    grows over time, balancing recovery speed against downstream pressure.
    """

    NONE = "NONE"
    FIXED = "FIXED"
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"
    EXPONENTIAL_JITTER = "EXPONENTIAL_JITTER"


class BackpressureLevel(str, Enum):
    """Coarse-grained backpressure indicators derived from aggregate usage.

    The level is computed across every active quota window and is intended
    as a quick signal for upstream callers to decide whether to shed load,
    queue requests, or proceed normally.
    """

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ══════════════════════════════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════════════════════════════


@dataclass
class QuotaLimit:
    """A quota definition for a specific resource.

    A limit describes the maximum amount of consumption permitted within
    a rolling ``window_seconds`` window. Multiple limits may be registered
    against the same resource (for example a request-count limit and a
    token-count limit); all of them must be satisfied for a request to
    be admitted.

    Attributes:
        limit_id: Unique identifier for this limit.
        resource: Fully qualified resource name, e.g. ``openai:gpt-4``.
        quota_type: The dimension being capped by this limit.
        max_value: Maximum consumption allowed within the window.
        window_seconds: Length of the rolling window in seconds.
        description: Optional human-readable description.
        created_at: Epoch timestamp (seconds) when the limit was created.
    """

    limit_id: str
    resource: str
    quota_type: QuotaType
    max_value: float
    window_seconds: float
    description: str
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize the limit to a plain dictionary.

        Enum fields are converted to their ``.value`` and any mutable
        containers are returned as fresh copies so the caller cannot
        mutate internal state.
        """
        return {
            "limit_id": self.limit_id,
            "resource": self.resource,
            "quota_type": (
                self.quota_type.value
                if isinstance(self.quota_type, QuotaType)
                else self.quota_type
            ),
            "max_value": self.max_value,
            "window_seconds": self.window_seconds,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class QuotaUsage:
    """Current consumption state for a single limit.

    The usage tracker is scoped to one ``limit_id`` and is reset whenever
    its active window expires. The ``status`` field gives callers a fast
    way to decide whether to attempt consumption or short-circuit.

    Attributes:
        usage_id: Unique identifier for this usage record.
        limit_id: Identifier of the :class:`QuotaLimit` being tracked.
        resource: Resource name this usage is associated with.
        current_value: Consumption accumulated within the current window.
        window_start: Epoch timestamp (seconds) marking window start.
        window_end: Epoch timestamp (seconds) marking window end.
        request_count: Number of admitted requests in the window.
        last_request_at: Epoch timestamp of the last admitted request,
            or ``None`` when no request has been admitted yet.
        status: Current :class:`QuotaStatus` for this usage.
    """

    usage_id: str
    limit_id: str
    resource: str
    current_value: float
    window_start: float
    window_end: float
    request_count: int
    last_request_at: float | None
    status: QuotaStatus

    def to_dict(self) -> dict[str, Any]:
        """Serialize usage to a plain dictionary with enums as values."""
        return {
            "usage_id": self.usage_id,
            "limit_id": self.limit_id,
            "resource": self.resource,
            "current_value": self.current_value,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "request_count": self.request_count,
            "last_request_at": self.last_request_at,
            "status": (
                self.status.value
                if isinstance(self.status, QuotaStatus)
                else self.status
            ),
        }


@dataclass
class RateLimitWindow:
    """Aggregate rate-limiting window for a single resource.

    Whereas :class:`QuotaUsage` tracks one limit, a window aggregates
    every admission decision for a resource across all quota types. It is
    the primary structure consulted by :meth:`AgentQuotaManager.get_window`
    and by the backpressure computation.

    Attributes:
        window_id: Unique identifier for this window.
        resource: Resource name this window covers.
        window_start: Epoch timestamp (seconds) marking window start.
        window_end: Epoch timestamp (seconds) marking window end.
        request_count: Total admitted requests in the window.
        token_count: Total tokens accounted for in the window.
        cost_usd: Total cost in USD accounted for in the window.
        blocked_count: Requests rejected because a limit was exhausted.
        throttled_count: Requests admitted while the resource was near a
            limit and therefore flagged for throttling.
    """

    window_id: str
    resource: str
    window_start: float
    window_end: float
    request_count: int
    token_count: float
    cost_usd: float
    blocked_count: int
    throttled_count: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the window to a plain dictionary with fresh copies."""
        return {
            "window_id": self.window_id,
            "resource": self.resource,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "request_count": self.request_count,
            "token_count": self.token_count,
            "cost_usd": self.cost_usd,
            "blocked_count": self.blocked_count,
            "throttled_count": self.throttled_count,
        }


@dataclass
class RetryPolicy:
    """Policy describing how failed requests should be retried.

    Attributes:
        policy_id: Unique identifier for this policy.
        max_retries: Maximum number of retry attempts permitted.
        base_delay_ms: Base delay in milliseconds between attempts.
        max_delay_ms: Hard cap on the computed delay in milliseconds.
        strategy: :class:`RetryStrategy` used to compute delays.
        retryable_status_codes: HTTP-style status codes eligible for
            retry. An empty list means every failure is retryable.
        created_at: Epoch timestamp (seconds) when the policy was created.
    """

    policy_id: str
    max_retries: int
    base_delay_ms: float
    max_delay_ms: float
    strategy: RetryStrategy
    retryable_status_codes: list[int] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the policy to a plain dictionary.

        The ``retryable_status_codes`` list is returned as a fresh copy so
        the caller cannot mutate the policy's internal state.
        """
        return {
            "policy_id": self.policy_id,
            "max_retries": self.max_retries,
            "base_delay_ms": self.base_delay_ms,
            "max_delay_ms": self.max_delay_ms,
            "strategy": (
                self.strategy.value
                if isinstance(self.strategy, RetryStrategy)
                else self.strategy
            ),
            "retryable_status_codes": list(self.retryable_status_codes),
            "created_at": self.created_at,
        }


@dataclass
class RetryAttempt:
    """Record of a single retry attempt against a :class:`RetryPolicy`.

    Attributes:
        attempt_id: Unique identifier for this attempt record.
        policy_id: Identifier of the policy that produced this attempt.
        attempt_number: 1-based index of this attempt within the sequence.
        status_code: HTTP-style status code observed, or ``None`` if the
            failure was not associated with a status code.
        delay_ms: Delay in milliseconds applied before this attempt.
        success: Whether the attempt succeeded.
        timestamp: Epoch timestamp (seconds) when the attempt was recorded.
        error: Optional human-readable error message.
    """

    attempt_id: str
    policy_id: str
    attempt_number: int
    status_code: int | None
    delay_ms: float
    success: bool
    timestamp: float
    error: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the attempt to a plain dictionary."""
        return {
            "attempt_id": self.attempt_id,
            "policy_id": self.policy_id,
            "attempt_number": self.attempt_number,
            "status_code": self.status_code,
            "delay_ms": self.delay_ms,
            "success": self.success,
            "timestamp": self.timestamp,
            "error": self.error,
        }


@dataclass
class QuotaManagerStats:
    """Aggregate statistics describing manager state at a point in time.

    Attributes:
        total_resources: Number of distinct resources currently tracked.
        total_limits: Number of registered quota limits.
        active_windows: Number of currently active rate-limit windows.
        total_requests: Lifetime count of admitted consumption requests.
        blocked_requests: Lifetime count of rejected consumption requests.
        throttled_requests: Lifetime count of throttled consumption requests.
        avg_latency_ms: Average processing latency in milliseconds across
            recently observed consumption requests.
        backpressure_level: Current :class:`BackpressureLevel`.
    """

    total_resources: int
    total_limits: int
    active_windows: int
    total_requests: int
    blocked_requests: int
    throttled_requests: int
    avg_latency_ms: float
    backpressure_level: BackpressureLevel

    def to_dict(self) -> dict[str, Any]:
        """Serialize stats to a plain dictionary with enums as values."""
        return {
            "total_resources": self.total_resources,
            "total_limits": self.total_limits,
            "active_windows": self.active_windows,
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "throttled_requests": self.throttled_requests,
            "avg_latency_ms": self.avg_latency_ms,
            "backpressure_level": (
                self.backpressure_level.value
                if isinstance(self.backpressure_level, BackpressureLevel)
                else self.backpressure_level
            ),
        }


# ══════════════════════════════════════════════════════════════════════
# Manager
# ══════════════════════════════════════════════════════════════════════


class AgentQuotaManager:
    """Thread-safe resource quota and rate-limit manager for the Buddy agent.

    The manager owns four primary registries:

      * ``_limits``   — registered :class:`QuotaLimit` definitions.
      * ``_usage``    — live :class:`QuotaUsage` trackers keyed by limit id.
      * ``_windows``  — per-resource :class:`RateLimitWindow` aggregates.
      * ``_policies`` — registered :class:`RetryPolicy` definitions.

    It additionally maintains a bounded :class:`RetryAttempt` history and a
    small set of aggregate counters used to compute :class:`QuotaManagerStats`
    and :class:`BackpressureLevel`.

    All public methods are guarded by a single reentrant-friendly mutex
    (``self._lock``). Internal helpers assume the lock is already held and
    must not be called from outside a ``with self._lock:`` block.
    """

    #: Maximum number of per-resource windows retained at any time.
    MAX_WINDOWS: int = 1000

    #: Maximum number of retry attempt records retained at any time.
    MAX_RETRY_HISTORY: int = 5000

    #: Default duration (seconds) of a rate-limit window when no limit
    #: provides a window length for the resource.
    DEFAULT_WINDOW_SECONDS: float = 60.0

    #: Number of latency samples retained for the rolling average.
    MAX_LATENCY_SAMPLES: int = 1000

    #: Usage ratio at and above which a resource is considered "near" its
    #: limit and contributes to HIGH backpressure.
    NEAR_LIMIT_RATIO: float = 0.8

    #: Usage ratio at and above which a resource contributes to MEDIUM
    #: backpressure.
    MID_LIMIT_RATIO: float = 0.5

    def __init__(self) -> None:
        """Initialize an empty quota manager."""
        self._limits: dict[str, QuotaLimit] = {}
        self._usage: dict[str, QuotaUsage] = {}
        self._windows: dict[str, RateLimitWindow] = {}
        self._policies: dict[str, RetryPolicy] = {}
        self._retry_history: list[RetryAttempt] = []
        self._lock = threading.Lock()

        # Aggregate counters used for stats and backpressure computation.
        self._total_requests: int = 0
        self._blocked_requests: int = 0
        self._throttled_requests: int = 0
        self._latency_samples: list[float] = []

    # ────────────────────────────────────────────────────────────────
    # Internal helpers (must be called with the lock held)
    # ────────────────────────────────────────────────────────────────

    def _matching_limits(
        self, resource: str, quota_type: QuotaType
    ) -> list[QuotaLimit]:
        """Return every limit registered for the given resource and type."""
        return [
            limit
            for limit in self._limits.values()
            if limit.resource == resource and limit.quota_type == quota_type
        ]

    def _resolve_usage(self, limit: QuotaLimit, now: float) -> QuotaUsage:
        """Return the usage tracker for ``limit``, resetting expired windows.

        A new tracker is created on first access. When the existing tracker
        has passed its ``window_end`` it is rolled over: counters reset and
        the window is advanced by the limit's ``window_seconds``.
        """
        usage = self._usage.get(limit.limit_id)
        if usage is None:
            usage = QuotaUsage(
                usage_id=str(uuid.uuid4()),
                limit_id=limit.limit_id,
                resource=limit.resource,
                current_value=0.0,
                window_start=now,
                window_end=now + limit.window_seconds,
                request_count=0,
                last_request_at=None,
                status=QuotaStatus.ACTIVE,
            )
            self._usage[limit.limit_id] = usage
            return usage

        if now >= usage.window_end:
            # Window expired: roll it forward and reset consumption.
            usage.current_value = 0.0
            usage.request_count = 0
            usage.last_request_at = None
            usage.window_start = now
            usage.window_end = now + limit.window_seconds
            usage.status = QuotaStatus.ACTIVE
        return usage

    def _resolve_window(self, resource: str, now: float) -> RateLimitWindow:
        """Return the rate-limit window for ``resource``, resetting if expired.

        A new window is created on first access. Expired windows are rolled
        forward to the current time with all counters zeroed. When the
        global :attr:`MAX_WINDOWS` cap is reached the oldest window is
        evicted before a new one is created.
        """
        window = self._windows.get(resource)
        if window is not None:
            if now < window.window_end:
                return window
            # Roll the expired window forward.
            window.window_start = now
            window.window_end = now + self.DEFAULT_WINDOW_SECONDS
            window.request_count = 0
            window.token_count = 0.0
            window.cost_usd = 0.0
            window.blocked_count = 0
            window.throttled_count = 0
            return window

        # First window for this resource — evict oldest if necessary.
        if len(self._windows) >= self.MAX_WINDOWS:
            oldest_resource = min(
                self._windows, key=lambda r: self._windows[r].window_start
            )
            del self._windows[oldest_resource]

        window = RateLimitWindow(
            window_id=str(uuid.uuid4()),
            resource=resource,
            window_start=now,
            window_end=now + self.DEFAULT_WINDOW_SECONDS,
            request_count=0,
            token_count=0.0,
            cost_usd=0.0,
            blocked_count=0,
            throttled_count=0,
        )
        self._windows[resource] = window
        return window

    def _update_usage_status(
        self, usage: QuotaUsage, limit: QuotaLimit
    ) -> None:
        """Recompute the status of ``usage`` based on its ratio to ``limit``."""
        if limit.max_value <= 0:
            ratio = 1.0
        else:
            ratio = usage.current_value / limit.max_value
        if usage.current_value >= limit.max_value:
            usage.status = QuotaStatus.EXHAUSTED
        elif ratio >= self.NEAR_LIMIT_RATIO:
            usage.status = QuotaStatus.THROTTLED
        else:
            usage.status = QuotaStatus.ACTIVE

    def _is_throttled(self, usage: QuotaUsage, limit: QuotaLimit) -> bool:
        """Return ``True`` when ``usage`` is near but not at its limit."""
        if limit.max_value <= 0:
            return False
        ratio = usage.current_value / limit.max_value
        return self.NEAR_LIMIT_RATIO <= ratio < 1.0

    def _record_latency(self, latency_ms: float) -> None:
        """Append a latency sample, trimming to the rolling-sample cap."""
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > self.MAX_LATENCY_SAMPLES:
            # Drop oldest samples to keep memory bounded.
            del self._latency_samples[
                : len(self._latency_samples) - self.MAX_LATENCY_SAMPLES
            ]

    def _jitter(self, base: float) -> float:
        """Derive a pseudo-random jitter in ``[0, 0.25 * base)``.

        The jitter is derived from a fresh UUID4 without importing the
        ``random`` module, keeping the dependency surface minimal while
        still providing enough entropy to decorrelate concurrent retries.
        """
        raw = uuid.uuid4().int
        fraction = (raw & ((1 << 64) - 1)) / float(1 << 64)
        return fraction * 0.25 * base

    # ────────────────────────────────────────────────────────────────
    # Limit lifecycle
    # ────────────────────────────────────────────────────────────────

    def register_limit(
        self,
        resource: str,
        quota_type: QuotaType,
        max_value: float,
        window_seconds: float = 60.0,
        description: str = "",
    ) -> QuotaLimit:
        """Create and register a new :class:`QuotaLimit`.

        Args:
            resource: Fully qualified resource name, e.g. ``openai:gpt-4``.
            quota_type: The dimension being capped.
            max_value: Maximum consumption permitted within the window.
            window_seconds: Length of the rolling window in seconds.
            description: Optional human-readable description.

        Returns:
            The newly created and registered :class:`QuotaLimit`.
        """
        limit = QuotaLimit(
            limit_id=str(uuid.uuid4()),
            resource=resource,
            quota_type=quota_type,
            max_value=float(max_value),
            window_seconds=float(window_seconds),
            description=description,
            created_at=time.time(),
        )
        with self._lock:
            self._limits[limit.limit_id] = limit
        return limit

    def unregister_limit(self, limit_id: str) -> bool:
        """Remove a limit and its associated usage tracker.

        Args:
            limit_id: Identifier of the limit to remove.

        Returns:
            ``True`` if a limit was removed, ``False`` otherwise.
        """
        with self._lock:
            if limit_id not in self._limits:
                return False
            del self._limits[limit_id]
            self._usage.pop(limit_id, None)
            return True

    def get_limit(self, limit_id: str) -> QuotaLimit | None:
        """Return the limit with the given id, or ``None`` if not found."""
        with self._lock:
            return self._limits.get(limit_id)

    def list_limits(self, resource: str | None = None) -> list[QuotaLimit]:
        """List registered limits, optionally filtered by resource.

        Args:
            resource: When provided, only limits for this resource are
                returned. When ``None``, every registered limit is returned.

        Returns:
            A fresh list of matching :class:`QuotaLimit` objects.
        """
        with self._lock:
            if resource is None:
                return list(self._limits.values())
            return [
                limit for limit in self._limits.values() if limit.resource == resource
            ]

    # ────────────────────────────────────────────────────────────────
    # Quota check / consume / release
    # ────────────────────────────────────────────────────────────────

    def check_quota(
        self,
        resource: str,
        quota_type: QuotaType,
        amount: float = 1.0,
    ) -> bool:
        """Check whether a request would be within quota.

        This is a non-mutating probe: it does not consume any quota. Use
        :meth:`consume_quota` for an atomic check-and-consume.

        Args:
            resource: Resource the request targets.
            quota_type: Dimension being checked.
            amount: Consumption the request would add.

        Returns:
            ``True`` if every matching limit can accommodate ``amount``
            within its current window, ``False`` otherwise (including
            when no limit is registered, which is treated as unbounded).
        """
        with self._lock:
            now = time.time()
            limits = self._matching_limits(resource, quota_type)
            for limit in limits:
                usage = self._resolve_usage(limit, now)
                if usage.current_value + amount > limit.max_value:
                    return False
            return True

    def consume_quota(
        self,
        resource: str,
        quota_type: QuotaType,
        amount: float = 1.0,
    ) -> QuotaUsage | None:
        """Atomically check and consume quota for a request.

        When every matching limit can accommodate ``amount`` the consumption
        is recorded against each limit's usage tracker, the resource's
        rate-limit window is updated, and the (first) updated usage is
        returned. When any limit would be exceeded the request is blocked:
        the window's ``blocked_count`` is incremented and ``None`` is
        returned.

        Args:
            resource: Resource the request targets.
            quota_type: Dimension being consumed.
            amount: Consumption to record.

        Returns:
            The updated :class:`QuotaUsage` for the first matching limit,
            or ``None`` if the request was blocked.
        """
        start = time.time()
        with self._lock:
            now = start
            limits = self._matching_limits(resource, quota_type)

            # Pre-check every limit so the consume step is all-or-nothing.
            would_block = False
            resolved: list[tuple[QuotaLimit, QuotaUsage]] = []
            for limit in limits:
                usage = self._resolve_usage(limit, now)
                resolved.append((limit, usage))
                if usage.current_value + amount > limit.max_value:
                    would_block = True

            window = self._resolve_window(resource, now)

            if would_block or not limits:
                if limits:
                    # Only count as blocked when at least one limit exists
                    # and was violated. A missing limit means unbounded.
                    window.blocked_count += 1
                    self._blocked_requests += 1
                    # Mark exhausted usages accordingly for visibility.
                    for limit, usage in resolved:
                        if usage.current_value + amount > limit.max_value:
                            usage.status = QuotaStatus.EXHAUSTED
                    self._record_latency((time.time() - start) * 1000.0)
                    return None
                # No limits registered: treat as unbounded admission, but
                # still record the activity in the window.
                window.request_count += 1
                self._total_requests += 1
                self._record_latency((time.time() - start) * 1000.0)
                # Synthesize a transient usage snapshot for the caller.
                return QuotaUsage(
                    usage_id=str(uuid.uuid4()),
                    limit_id="",
                    resource=resource,
                    current_value=amount,
                    window_start=window.window_start,
                    window_end=window.window_end,
                    request_count=1,
                    last_request_at=now,
                    status=QuotaStatus.ACTIVE,
                )

            # Admit: apply consumption to every matching limit.
            throttled = False
            for limit, usage in resolved:
                usage.current_value += amount
                usage.request_count += 1
                usage.last_request_at = now
                self._update_usage_status(usage, limit)
                if self._is_throttled(usage, limit):
                    throttled = True

            window.request_count += 1
            if quota_type == QuotaType.TOKEN_COUNT:
                window.token_count += amount
            elif quota_type == QuotaType.COST_USD:
                window.cost_usd += amount
            if throttled:
                window.throttled_count += 1
                self._throttled_requests += 1

            self._total_requests += 1
            self._record_latency((time.time() - start) * 1000.0)
            return resolved[0][1]

    def release_quota(
        self,
        resource: str,
        quota_type: QuotaType,
        amount: float = 1.0,
    ) -> bool:
        """Release previously consumed quota.

        This is intended for compensating consumption recorded for requests
        that ultimately failed downstream, so the failed request does not
        permanently count against the rolling window.

        Args:
            resource: Resource the original request targeted.
            quota_type: Dimension being released.
            amount: Consumption to release.

        Returns:
            ``True`` if at least one usage tracker was adjusted,
            ``False`` otherwise.
        """
        with self._lock:
            now = time.time()
            limits = self._matching_limits(resource, quota_type)
            adjusted = False
            for limit in limits:
                usage = self._resolve_usage(limit, now)
                if usage.current_value <= 0:
                    continue
                usage.current_value = max(0.0, usage.current_value - amount)
                if usage.request_count > 0:
                    usage.request_count -= 1
                self._update_usage_status(usage, limit)
                adjusted = True
            return adjusted

    def get_usage(
        self, resource: str, quota_type: QuotaType
    ) -> QuotaUsage | None:
        """Return the current usage for a resource and quota type.

        When multiple limits match, the usage for the first one encountered
        is returned. Expired windows are rolled forward before returning so
        callers always observe a current view.

        Args:
            resource: Resource to inspect.
            quota_type: Dimension to inspect.

        Returns:
            The matching :class:`QuotaUsage`, or ``None`` if no limit is
            registered for the resource and type.
        """
        with self._lock:
            now = time.time()
            limits = self._matching_limits(resource, quota_type)
            if not limits:
                return None
            return self._resolve_usage(limits[0], now)

    def get_window(self, resource: str) -> RateLimitWindow | None:
        """Return the rate-limit window for ``resource``, or ``None``."""
        with self._lock:
            return self._windows.get(resource)

    def list_windows(self, resource: str | None = None) -> list[RateLimitWindow]:
        """List rate-limit windows, optionally filtered by resource.

        Args:
            resource: When provided, only the window for this resource is
                returned (at most one). When ``None``, every window is
                returned.

        Returns:
            A fresh list of matching :class:`RateLimitWindow` objects.
        """
        with self._lock:
            if resource is None:
                return list(self._windows.values())
            window = self._windows.get(resource)
            return [window] if window is not None else []

    # ────────────────────────────────────────────────────────────────
    # Retry policies
    # ────────────────────────────────────────────────────────────────

    def register_retry_policy(
        self,
        name: str,
        max_retries: int,
        base_delay_ms: float,
        max_delay_ms: float,
        strategy: RetryStrategy,
        retryable_status_codes: list[int] | None = None,
    ) -> RetryPolicy:
        """Create and register a new :class:`RetryPolicy`.

        Args:
            name: Human-readable name for the policy. Kept for caller
                convenience; it is not stored on the policy itself.
            max_retries: Maximum retry attempts permitted.
            base_delay_ms: Base delay in milliseconds between attempts.
            max_delay_ms: Hard cap on the computed delay in milliseconds.
            strategy: :class:`RetryStrategy` used to compute delays.
            retryable_status_codes: Optional list of HTTP-style status
                codes eligible for retry. ``None`` means any failure is
                retryable (subject to ``max_retries``).

        Returns:
            The newly created and registered :class:`RetryPolicy`.
        """
        del name  # Reserved for caller-facing identification only.
        policy = RetryPolicy(
            policy_id=str(uuid.uuid4()),
            max_retries=int(max_retries),
            base_delay_ms=float(base_delay_ms),
            max_delay_ms=float(max_delay_ms),
            strategy=strategy,
            retryable_status_codes=list(retryable_status_codes)
            if retryable_status_codes is not None
            else [],
            created_at=time.time(),
        )
        with self._lock:
            self._policies[policy.policy_id] = policy
        return policy

    def compute_retry_delay(
        self,
        policy_id: str,
        attempt_number: int,
        last_status_code: int | None = None,
    ) -> float | None:
        """Compute the delay (in ms) before the next retry attempt.

        The computation honours the policy's ``max_retries`` cap and its
        ``retryable_status_codes`` filter. When ``last_status_code`` is
        provided and the policy declares a non-empty list of retryable
        codes, a status not in that list suppresses the retry (returns
        ``None``).

        Delay strategies:

          * :attr:`RetryStrategy.NONE` — never retry, returns ``None``.
          * :attr:`RetryStrategy.FIXED` — ``base_delay_ms``.
          * :attr:`RetryStrategy.LINEAR` — ``base_delay_ms * attempt``.
          * :attr:`RetryStrategy.EXPONENTIAL` —
            ``base_delay_ms * 2 ** (attempt - 1)``, capped at
            ``max_delay_ms``.
          * :attr:`RetryStrategy.EXPONENTIAL_JITTER` — exponential delay
            plus a pseudo-random jitter of up to 25% of ``base_delay_ms``,
            capped at ``max_delay_ms``.

        Args:
            policy_id: Identifier of the policy to apply.
            attempt_number: 1-based index of the upcoming attempt.
            last_status_code: Status code observed on the previous attempt,
                or ``None`` if not applicable.

        Returns:
            The delay in milliseconds, or ``None`` when no retry should be
            performed.
        """
        with self._lock:
            policy = self._policies.get(policy_id)
            if policy is None:
                return None
            if policy.strategy == RetryStrategy.NONE:
                return None
            if attempt_number < 1 or attempt_number > policy.max_retries:
                return None
            if (
                last_status_code is not None
                and policy.retryable_status_codes
                and last_status_code not in policy.retryable_status_codes
            ):
                return None

            base = policy.base_delay_ms
            if policy.strategy == RetryStrategy.FIXED:
                delay = base
            elif policy.strategy == RetryStrategy.LINEAR:
                delay = base * attempt_number
            elif policy.strategy == RetryStrategy.EXPONENTIAL:
                delay = base * (2 ** (attempt_number - 1))
            elif policy.strategy == RetryStrategy.EXPONENTIAL_JITTER:
                delay = base * (2 ** (attempt_number - 1)) + self._jitter(base)
            else:
                return None

            return float(min(delay, policy.max_delay_ms))

    def record_retry_attempt(
        self,
        policy_id: str,
        attempt_number: int,
        status_code: int | None,
        delay_ms: float,
        success: bool,
        error: str = "",
    ) -> RetryAttempt:
        """Record a single retry attempt and append it to the history.

        The history is bounded by :attr:`MAX_RETRY_HISTORY`; the oldest
        records are dropped when the cap is exceeded.

        Args:
            policy_id: Identifier of the policy that produced the attempt.
            attempt_number: 1-based index of the attempt.
            status_code: HTTP-style status code observed, or ``None``.
            delay_ms: Delay applied before the attempt, in milliseconds.
            success: Whether the attempt succeeded.
            error: Optional human-readable error message.

        Returns:
            The newly created :class:`RetryAttempt`.
        """
        attempt = RetryAttempt(
            attempt_id=str(uuid.uuid4()),
            policy_id=policy_id,
            attempt_number=attempt_number,
            status_code=status_code,
            delay_ms=float(delay_ms),
            success=success,
            timestamp=time.time(),
            error=error,
        )
        with self._lock:
            self._retry_history.append(attempt)
            if len(self._retry_history) > self.MAX_RETRY_HISTORY:
                del self._retry_history[
                    : len(self._retry_history) - self.MAX_RETRY_HISTORY
                ]
        return attempt

    # ────────────────────────────────────────────────────────────────
    # Backpressure & stats
    # ────────────────────────────────────────────────────────────────

    def get_backpressure_level(self) -> BackpressureLevel:
        """Compute the aggregate backpressure level across all resources.

        The level is derived from the usage ratio of every active, non-
        expired usage tracker:

          * Any tracker in :attr:`QuotaStatus.EXHAUSTED` or
            :attr:`QuotaStatus.BLOCKED` state yields
            :attr:`BackpressureLevel.CRITICAL`.
          * If at least half of the trackers are at or above
            :attr:`NEAR_LIMIT_RATIO`, the level is
            :attr:`BackpressureLevel.HIGH`.
          * If at least half of the trackers are at or above
            :attr:`MID_LIMIT_RATIO`, the level is
            :attr:`BackpressureLevel.MEDIUM`.
          * When at least one tracker exists but none of the above
            thresholds are met, the level is
            :attr:`BackpressureLevel.LOW`.
          * With no trackers, the level is
            :attr:`BackpressureLevel.NONE`.

        Returns:
            The current :class:`BackpressureLevel`.
        """
        with self._lock:
            now = time.time()
            ratios: list[float] = []
            any_exhausted = False
            for limit in self._limits.values():
                usage = self._usage.get(limit.limit_id)
                if usage is None:
                    continue
                if now >= usage.window_end:
                    # Expired windows exert no current pressure.
                    continue
                if usage.status in (
                    QuotaStatus.EXHAUSTED,
                    QuotaStatus.BLOCKED,
                ):
                    any_exhausted = True
                    continue
                if limit.max_value <= 0:
                    ratios.append(1.0)
                    continue
                ratios.append(usage.current_value / limit.max_value)

            if any_exhausted:
                return BackpressureLevel.CRITICAL
            if not ratios:
                return BackpressureLevel.NONE

            total = len(ratios)
            near = sum(1 for r in ratios if r >= self.NEAR_LIMIT_RATIO)
            mid = sum(1 for r in ratios if r >= self.MID_LIMIT_RATIO)

            if near / total >= 0.5:
                return BackpressureLevel.HIGH
            if mid / total >= 0.5:
                return BackpressureLevel.MEDIUM
            return BackpressureLevel.LOW

    def get_stats(self) -> QuotaManagerStats:
        """Return an aggregate snapshot of manager state.

        Returns:
            A :class:`QuotaManagerStats` populated with current counters,
            the active window count, the rolling average latency and the
            current backpressure level.
        """
        with self._lock:
            resources = {limit.resource for limit in self._limits.values()}
            if self._latency_samples:
                avg_latency = sum(self._latency_samples) / len(
                    self._latency_samples
                )
            else:
                avg_latency = 0.0

            # Compute backpressure inline to avoid re-acquiring the lock.
            now = time.time()
            ratios: list[float] = []
            any_exhausted = False
            for limit in self._limits.values():
                usage = self._usage.get(limit.limit_id)
                if usage is None:
                    continue
                if now >= usage.window_end:
                    continue
                if usage.status in (
                    QuotaStatus.EXHAUSTED,
                    QuotaStatus.BLOCKED,
                ):
                    any_exhausted = True
                    continue
                if limit.max_value <= 0:
                    ratios.append(1.0)
                    continue
                ratios.append(usage.current_value / limit.max_value)

            if any_exhausted:
                level = BackpressureLevel.CRITICAL
            elif not ratios:
                level = BackpressureLevel.NONE
            else:
                total = len(ratios)
                near = sum(1 for r in ratios if r >= self.NEAR_LIMIT_RATIO)
                mid = sum(1 for r in ratios if r >= self.MID_LIMIT_RATIO)
                if near / total >= 0.5:
                    level = BackpressureLevel.HIGH
                elif mid / total >= 0.5:
                    level = BackpressureLevel.MEDIUM
                else:
                    level = BackpressureLevel.LOW

            return QuotaManagerStats(
                total_resources=len(resources),
                total_limits=len(self._limits),
                active_windows=len(self._windows),
                total_requests=self._total_requests,
                blocked_requests=self._blocked_requests,
                throttled_requests=self._throttled_requests,
                avg_latency_ms=avg_latency,
                backpressure_level=level,
            )

    # ────────────────────────────────────────────────────────────────
    # Maintenance
    # ────────────────────────────────────────────────────────────────

    def clear(self) -> int:
        """Clear all manager state.

        Returns:
            The number of top-level entries removed (limits + windows +
            policies + retry-history records).
        """
        with self._lock:
            cleared = (
                len(self._limits)
                + len(self._windows)
                + len(self._policies)
                + len(self._retry_history)
            )
            self._limits.clear()
            self._usage.clear()
            self._windows.clear()
            self._policies.clear()
            self._retry_history.clear()
            self._total_requests = 0
            self._blocked_requests = 0
            self._throttled_requests = 0
            self._latency_samples.clear()
            return cleared


# ══════════════════════════════════════════════════════════════════════
# Singleton accessors
# ══════════════════════════════════════════════════════════════════════


_global_quota_manager: AgentQuotaManager | None = None


def get_quota_manager() -> AgentQuotaManager:
    """Return the process-wide :class:`AgentQuotaManager` singleton.

    The singleton is lazily instantiated on first access.
    """
    global _global_quota_manager
    if _global_quota_manager is None:
        _global_quota_manager = AgentQuotaManager()
    return _global_quota_manager


def reset_quota_manager() -> None:
    """Reset the process-wide singleton.

    Primarily intended for tests: the next call to
    :func:`get_quota_manager` will create a fresh instance.
    """
    global _global_quota_manager
    _global_quota_manager = None
