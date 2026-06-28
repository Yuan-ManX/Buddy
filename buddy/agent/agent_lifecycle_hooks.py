"""
Buddy Agent Lifecycle Hooks System

A registration and dispatch framework that allows pre/post execution hooks to
be attached to the various stages of an agent's lifecycle. Hooks may observe,
intercept, transform, or short-circuit agent execution flow across events such
as tool execution, prompt submission, model calls, plan progression, memory
access, delegation, and session boundaries.

The system provides ordered, priority-sorted hook chains, per-hook failure
policies, invocation logging, and lightweight statistics so that platform
components can compose cross-cutting concerns (telemetry, governance,
transformation, audit) without modifying core agent code.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #


class HookEvent(Enum):
    """Lifecycle events that hooks may subscribe to."""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_PROMPT_SUBMIT = "user_prompt_submit"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_MODEL_CALL = "pre_model_call"
    POST_MODEL_CALL = "post_model_call"
    AGENT_RESPONSE = "agent_response"
    CONTEXT_ASSEMBLY = "context_assembly"
    PLAN_CREATED = "plan_created"
    PLAN_STEP_START = "plan_step_start"
    PLAN_STEP_END = "plan_step_end"
    ERROR_OCCURRED = "error_occurred"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"
    SKILL_INVOKED = "skill_invoked"
    DELEGATION_REQUESTED = "delegation_requested"
    TASK_COMPLETED = "task_completed"


class HookPhase(Enum):
    """Execution phase relative to the event (before, after, or around)."""

    PRE = "pre"
    POST = "post"
    AROUND = "around"


class HookPriority(Enum):
    """Hook execution priority. Lower integer value runs first."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class HookExecutionMode(Enum):
    """How a hook callback should be dispatched."""

    SYNC = "sync"
    ASYNC = "async"
    FIRE_AND_FORGET = "fire_and_forget"


class HookStatus(Enum):
    """Lifecycle status of a registered hook."""

    REGISTERED = "registered"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


class HookResult(Enum):
    """Outcome directive returned by a hook callback."""

    CONTINUE = "continue"
    SKIP = "skip"
    ABORT = "abort"
    RETRY = "retry"
    TRANSFORM = "transform"
    REDIRECT = "redirect"


class HookFailurePolicy(Enum):
    """Policy applied when a hook callback raises an exception."""

    PROPAGATE = "propagate"
    SWALLOW = "swallow"
    FALLBACK = "fallback"
    QUARANTINE = "quarantine"


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #


@dataclass
class HookContext:
    """Context object passed to every hook callback invocation."""

    event: HookEvent
    phase: HookPhase
    session_id: str
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_event_id: str | None = None
    trace_id: str | None = None


@dataclass
class HookExecutionResult:
    """Normalized return value produced by a hook callback."""

    result: HookResult
    transformed_payload: dict[str, Any] | None = None
    message: str = ""
    error: str | None = None
    should_skip: bool = False
    should_abort: bool = False
    retry_after_ms: int | None = None
    redirect_target: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookRegistration:
    """Persisted definition of a registered hook.

    The callback function itself is intentionally kept out of this dataclass so
    that the registration remains serializable and free of non-dataclass
    friendly fields. Callbacks live in a separate mapping keyed by hook_id.
    """

    hook_id: str
    name: str
    description: str
    event: HookEvent
    phase: HookPhase
    priority: HookPriority
    execution_mode: HookExecutionMode
    status: HookStatus
    failure_policy: HookFailurePolicy
    owner: str
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_invoked_at: float | None = None
    invocation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    max_retries: int = 0
    timeout_ms: int | None = None
    enabled: bool = True


@dataclass
class HookInvocation:
    """Record of a single hook execution for the invocation log."""

    invocation_id: str
    hook_id: str
    event: HookEvent
    phase: HookPhase
    trace_id: str | None
    started_at: float
    completed_at: float | None = None
    result: HookResult | None = None
    error: str | None = None
    transformed: bool = False
    latency_ms: float = 0.0


@dataclass
class HookChain:
    """Ordered sequence of hooks bound to a specific event and phase."""

    event: HookEvent
    phase: HookPhase
    hook_ids: list[str] = field(default_factory=list)
    total_latency_ms: float = 0.0
    last_executed_at: float | None = None
    execution_count: int = 0


# --------------------------------------------------------------------------- #
# Hook registry / dispatcher
# --------------------------------------------------------------------------- #


class AgentLifecycleHooks:
    """Central registry and dispatcher for agent lifecycle hooks.

    Maintains registered hooks, their callbacks, ordered execution chains per
    (event, phase), an invocation log, and aggregate statistics. The class is
    intended to be used as a process-wide singleton via
    :func:`get_lifecycle_hooks`, but can also be instantiated directly for
    testing or isolated scenarios.
    """

    MAX_HOOKS = 500
    MAX_INVOCATIONS_LOG = 10000
    MAX_CHAIN_LATENCY_MS = 5000
    DEFAULT_TIMEOUT_MS = 30000

    def __init__(self) -> None:
        """Initialize empty registries for hooks, callbacks, chains, and logs."""
        self._hooks: dict[str, HookRegistration] = {}
        self._callbacks: dict[str, Callable[[HookContext], HookExecutionResult | HookResult | dict[str, Any] | None]] = {}
        self._chains: dict[tuple[HookEvent, HookPhase], HookChain] = {}
        self._invocations: list[HookInvocation] = []

    # ------------------------------------------------------------------ #
    # Registration management
    # ------------------------------------------------------------------ #

    def register_hook(
        self,
        name: str,
        description: str,
        event: HookEvent,
        phase: HookPhase,
        priority: HookPriority = HookPriority.NORMAL,
        execution_mode: HookExecutionMode = HookExecutionMode.SYNC,
        failure_policy: HookFailurePolicy = HookFailurePolicy.PROPAGATE,
        owner: str = "system",
        tags: list[str] | None = None,
        max_retries: int = 0,
        timeout_ms: int | None = None,
        callback: Callable[[HookContext], HookExecutionResult | HookResult | dict[str, Any] | None] | None = None,
    ) -> HookRegistration:
        """Register a new hook and return its registration record.

        Stores the callback (if provided) in the internal callback mapping
        keyed by hook_id, keeping the dataclass registration serializable.

        Raises:
            ValueError: if the name is empty or a hook with the same name and
                event/phase binding already exists.
        """
        if not name or not name.strip():
            raise ValueError("Hook name must not be empty")

        # Reject duplicates keyed by (name, event, phase) to avoid ambiguous
        # registrations for the same lifecycle point.
        for existing in self._hooks.values():
            if (
                existing.name == name
                and existing.event == event
                and existing.phase == phase
            ):
                raise ValueError(
                    f"Hook named '{name}' already registered for "
                    f"{event.value}/{phase.value}"
                )

        if len(self._hooks) >= self.MAX_HOOKS:
            raise ValueError(
                f"Maximum number of hooks ({self.MAX_HOOKS}) reached"
            )

        hook_id = f"hook_{uuid.uuid4().hex}"
        now = time.time()
        registration = HookRegistration(
            hook_id=hook_id,
            name=name,
            description=description,
            event=event,
            phase=phase,
            priority=priority,
            execution_mode=execution_mode,
            status=HookStatus.REGISTERED,
            failure_policy=failure_policy,
            owner=owner,
            tags=list(tags) if tags else [],
            max_retries=max_retries,
            timeout_ms=timeout_ms,
            created_at=now,
            updated_at=now,
        )
        self._hooks[hook_id] = registration
        if callback is not None:
            self._callbacks[hook_id] = callback

        # Ensure a chain entry exists for this (event, phase).
        chain_key = (event, phase)
        chain = self._chains.get(chain_key)
        if chain is None:
            chain = HookChain(event=event, phase=phase)
            self._chains[chain_key] = chain
        if hook_id not in chain.hook_ids:
            chain.hook_ids.append(hook_id)

        return registration

    def unregister_hook(self, hook_id: str) -> bool:
        """Remove a hook registration and its callback.

        Returns:
            True if a hook was removed, False if the hook_id was unknown.
        """
        registration = self._hooks.pop(hook_id, None)
        if registration is None:
            return False
        self._callbacks.pop(hook_id, None)
        chain = self._chains.get((registration.event, registration.phase))
        if chain is not None and hook_id in chain.hook_ids:
            chain.hook_ids.remove(hook_id)
        return True

    def update_hook(self, hook_id: str, **kwargs: Any) -> HookRegistration | None:
        """Update mutable fields of a registered hook.

        Accepts keyword arguments for any of: priority, status, failure_policy,
        tags, enabled, description, owner, max_retries, timeout_ms,
        execution_mode. Returns the updated registration, or None if the
        hook_id is unknown.
        """
        registration = self._hooks.get(hook_id)
        if registration is None:
            return None

        allowed = {
            "priority",
            "status",
            "failure_policy",
            "tags",
            "enabled",
            "description",
            "owner",
            "max_retries",
            "timeout_ms",
            "execution_mode",
        }
        for key, value in kwargs.items():
            if key in allowed:
                setattr(registration, key, value)
        registration.updated_at = time.time()

        # Keep the chain membership in sync when priority/status/enabled change.
        chain = self._chains.get((registration.event, registration.phase))
        if chain is not None and hook_id not in chain.hook_ids:
            chain.hook_ids.append(hook_id)

        return registration

    def get_hook(self, hook_id: str) -> HookRegistration | None:
        """Return the registration for a hook_id, or None if not found."""
        return self._hooks.get(hook_id)

    def list_hooks(
        self,
        event: HookEvent | None = None,
        phase: HookPhase | None = None,
        status: HookStatus | None = None,
        owner: str | None = None,
    ) -> list[HookRegistration]:
        """Return a filtered list of hook registrations.

        All filter arguments are optional; when omitted, that dimension is not
        filtered. Results are sorted by priority (ascending) then name.
        """
        results: list[HookRegistration] = []
        for registration in self._hooks.values():
            if event is not None and registration.event != event:
                continue
            if phase is not None and registration.phase != phase:
                continue
            if status is not None and registration.status != status:
                continue
            if owner is not None and registration.owner != owner:
                continue
            results.append(registration)
        results.sort(
            key=lambda r: (r.priority.value, r.name)
        )
        return results

    def set_hook_status(
        self, hook_id: str, status: HookStatus
    ) -> HookRegistration | None:
        """Transition a hook to a new status (pause/resume/disable/etc.).

        Returns the updated registration, or None if the hook_id is unknown.
        """
        return self.update_hook(hook_id, status=status)

    # ------------------------------------------------------------------ #
    # Invocation
    # ------------------------------------------------------------------ #

    def invoke(
        self,
        event: HookEvent,
        phase: HookPhase,
        session_id: str,
        agent_id: str,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> list[HookExecutionResult]:
        """Main entry point: dispatch a lifecycle event to its hook chain.

        Builds a :class:`HookContext`, resolves the priority-sorted chain for
        the given event and phase, and invokes each enabled callback in turn.
        Per-hook failures are handled according to the hook's failure_policy.
        The returned list contains one :class:`HookExecutionResult` per hook
        that actually executed.

        Result directives are interpreted as follows:
            * CONTINUE  -> proceed to the next hook in the chain.
            * TRANSFORM -> merge transformed_payload into the running context
              payload, then continue.
            * SKIP      -> stop executing remaining hooks.
            * ABORT     -> stop executing remaining hooks.
            * REDIRECT  -> stop executing remaining hooks.
            * RETRY     -> recorded but treated as CONTINUE for chain flow.
        """
        context = HookContext(
            event=event,
            phase=phase,
            session_id=session_id,
            agent_id=agent_id,
            payload=dict(payload) if payload else {},
            metadata=dict(metadata) if metadata else {},
            trace_id=trace_id,
        )

        chain = self._chains.get((event, phase))
        chain_start = time.time()
        results: list[HookExecutionResult] = []

        ordered = self._build_chain(event, phase)

        for registration in ordered:
            if not registration.enabled:
                continue
            if registration.status not in (HookStatus.REGISTERED, HookStatus.ACTIVE):
                continue

            invocation_id = f"inv_{uuid.uuid4().hex}"
            started_at = time.time()
            error: str | None = None
            transformed = False
            result: HookExecutionResult

            try:
                result = self._invoke_callback(registration.hook_id, context)
            except Exception as exc:  # noqa: BLE001 - broad catch is intentional
                error = str(exc)
                result = self._apply_failure_policy(registration, error)

            completed_at = time.time()
            latency_ms = (completed_at - started_at) * 1000.0

            # Apply transformation to the running context payload.
            if (
                result.result == HookResult.TRANSFORM
                and result.transformed_payload is not None
            ):
                transformed = True
                context.payload = {
                    **context.payload,
                    **result.transformed_payload,
                }

            # Update per-hook statistics.
            registration.last_invoked_at = completed_at
            registration.updated_at = completed_at
            registration.invocation_count += 1
            if error is None and result.error is None:
                registration.success_count += 1
            else:
                registration.failure_count += 1
            count = registration.invocation_count
            registration.avg_latency_ms = (
                (registration.avg_latency_ms * (count - 1) + latency_ms) / count
                if count > 0
                else registration.avg_latency_ms
            )

            # Log the invocation.
            invocation = HookInvocation(
                invocation_id=invocation_id,
                hook_id=registration.hook_id,
                event=event,
                phase=phase,
                trace_id=trace_id,
                started_at=started_at,
                completed_at=completed_at,
                result=result.result,
                error=error if error is not None else result.error,
                transformed=transformed,
                latency_ms=latency_ms,
            )
            self._log_invocation(invocation)

            results.append(result)

            # Interpret the result directive for chain flow control.
            if result.result == HookResult.SKIP or result.should_skip:
                break
            if result.result == HookResult.ABORT or result.should_abort:
                break
            if result.result == HookResult.REDIRECT:
                break
            # CONTINUE, TRANSFORM, and RETRY continue to the next hook.

        # Update chain-level statistics.
        chain_latency_ms = (time.time() - chain_start) * 1000.0
        if chain is not None:
            chain.execution_count += 1
            chain.last_executed_at = time.time()
            # Running average of chain latency.
            chain.total_latency_ms = (
                (chain.total_latency_ms * (chain.execution_count - 1) + chain_latency_ms)
                / chain.execution_count
                if chain.execution_count > 0
                else chain.total_latency_ms
            )

        return results

    def _invoke_callback(
        self, hook_id: str, context: HookContext
    ) -> HookExecutionResult:
        """Invoke the callback for hook_id and normalize its return value.

        Callbacks may return a :class:`HookExecutionResult`, a
        :class:`HookResult`, a dict, or None. All variants are normalized to a
        :class:`HookExecutionResult`. If no callback is registered, a default
        CONTINUE result is returned.
        """
        callback = self._callbacks.get(hook_id)
        if callback is None:
            return HookExecutionResult(
                result=HookResult.CONTINUE,
                message="no callback registered",
            )
        raw = callback(context)
        return self._normalize_result(raw)

    @staticmethod
    def _normalize_result(
        raw: HookExecutionResult | HookResult | dict[str, Any] | None,
    ) -> HookExecutionResult:
        """Coerce a callback's return value into a HookExecutionResult."""
        if raw is None:
            return HookExecutionResult(result=HookResult.CONTINUE)
        if isinstance(raw, HookExecutionResult):
            return raw
        if isinstance(raw, HookResult):
            return HookExecutionResult(result=raw)
        if isinstance(raw, dict):
            result_value = raw.get("result", HookResult.CONTINUE)
            if isinstance(result_value, str):
                try:
                    result_value = HookResult[result_value.upper()]
                except KeyError:
                    result_value = HookResult.CONTINUE
            return HookExecutionResult(
                result=result_value,
                transformed_payload=raw.get("transformed_payload"),
                message=raw.get("message", ""),
                error=raw.get("error"),
                should_skip=bool(raw.get("should_skip", False)),
                should_abort=bool(raw.get("should_abort", False)),
                retry_after_ms=raw.get("retry_after_ms"),
                redirect_target=raw.get("redirect_target"),
                metadata=raw.get("metadata", {}) or {},
            )
        # Unknown return types default to CONTINUE.
        return HookExecutionResult(result=HookResult.CONTINUE)

    def _apply_failure_policy(
        self, registration: HookRegistration, error: str
    ) -> HookExecutionResult:
        """Translate a callback exception into a HookExecutionResult.

        PROPAGATE  -> produce an ABORT result (the exception is caught and
          logged at the invocation record rather than re-raised).
        SWALLOW    -> produce a CONTINUE result carrying the error message.
        FALLBACK   -> produce a clean CONTINUE result with a fallback marker.
        QUARANTINE -> disable the offending hook and produce a CONTINUE result.
        """
        policy = registration.failure_policy
        if policy == HookFailurePolicy.PROPAGATE:
            return HookExecutionResult(
                result=HookResult.ABORT,
                error=error,
                should_abort=True,
            )
        if policy == HookFailurePolicy.SWALLOW:
            return HookExecutionResult(
                result=HookResult.CONTINUE,
                error=error,
            )
        if policy == HookFailurePolicy.FALLBACK:
            return HookExecutionResult(
                result=HookResult.CONTINUE,
                message="fallback applied",
            )
        if policy == HookFailurePolicy.QUARANTINE:
            registration.status = HookStatus.DISABLED
            registration.enabled = False
            registration.updated_at = time.time()
            return HookExecutionResult(
                result=HookResult.CONTINUE,
                error=error,
                message="hook quarantined and disabled",
            )
        # Defensive default for any future policy values.
        return HookExecutionResult(
            result=HookResult.CONTINUE,
            error=error,
        )

    def _build_chain(
        self, event: HookEvent, phase: HookPhase
    ) -> list[HookRegistration]:
        """Return enabled hooks for (event, phase) sorted by priority.

        CRITICAL (0) runs first, BACKGROUND (4) runs last. Only hooks that are
        enabled and in an active-ish status (REGISTERED or ACTIVE) are
        included.
        """
        matching = [
            registration
            for registration in self._hooks.values()
            if registration.event == event
            and registration.phase == phase
            and registration.enabled
            and registration.status
            in (HookStatus.REGISTERED, HookStatus.ACTIVE)
        ]
        matching.sort(key=lambda r: r.priority.value)
        return matching

    def _log_invocation(self, invocation: HookInvocation) -> None:
        """Append an invocation record to the log, enforcing the size cap."""
        self._invocations.append(invocation)
        if len(self._invocations) > self.MAX_INVOCATIONS_LOG:
            # Drop the oldest records to stay within the cap.
            overflow = len(self._invocations) - self.MAX_INVOCATIONS_LOG
            del self._invocations[:overflow]

    def get_invocation_log(
        self,
        hook_id: str | None = None,
        event: HookEvent | None = None,
        limit: int = 100,
    ) -> list[HookInvocation]:
        """Return recent invocations, optionally filtered by hook or event.

        Results are returned newest-first, up to `limit` records.
        """
        if limit <= 0:
            return []
        filtered: list[HookInvocation] = []
        for invocation in reversed(self._invocations):
            if hook_id is not None and invocation.hook_id != hook_id:
                continue
            if event is not None and invocation.event != event:
                continue
            filtered.append(invocation)
            if len(filtered) >= limit:
                break
        return filtered

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #

    def get_hook_stats(self, hook_id: str) -> dict[str, Any]:
        """Return per-hook statistics for diagnostics and dashboards."""
        registration = self._hooks.get(hook_id)
        if registration is None:
            return {}
        total = registration.invocation_count
        success_rate = (
            registration.success_count / total if total > 0 else 0.0
        )
        recent = self.get_invocation_log(hook_id=hook_id, limit=20)
        recent_results = [
            {
                "invocation_id": inv.invocation_id,
                "result": inv.result.value if inv.result else None,
                "error": inv.error,
                "latency_ms": inv.latency_ms,
                "transformed": inv.transformed,
                "started_at": inv.started_at,
            }
            for inv in recent
        ]
        return {
            "hook_id": hook_id,
            "name": registration.name,
            "event": registration.event.value,
            "phase": registration.phase.value,
            "status": registration.status.value,
            "enabled": registration.enabled,
            "invocation_count": registration.invocation_count,
            "success_count": registration.success_count,
            "failure_count": registration.failure_count,
            "success_rate": success_rate,
            "avg_latency_ms": registration.avg_latency_ms,
            "last_invoked_at": registration.last_invoked_at,
            "recent_results": recent_results,
        }

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all registered hooks."""
        hooks_by_event: dict[str, int] = {}
        hooks_by_status: dict[str, int] = {}
        for registration in self._hooks.values():
            event_key = registration.event.value
            status_key = registration.status.value
            hooks_by_event[event_key] = hooks_by_event.get(event_key, 0) + 1
            hooks_by_status[status_key] = hooks_by_status.get(status_key, 0) + 1

        total_invocations = len(self._invocations)

        avg_chain_latency_ms = 0.0
        if self._chains:
            active_latencies = [
                chain.total_latency_ms
                for chain in self._chains.values()
                if chain.execution_count > 0
            ]
            if active_latencies:
                avg_chain_latency_ms = sum(active_latencies) / len(active_latencies)

        top_hooks_by_invocation = sorted(
            (
                {
                    "hook_id": r.hook_id,
                    "name": r.name,
                    "invocation_count": r.invocation_count,
                    "avg_latency_ms": r.avg_latency_ms,
                }
                for r in self._hooks.values()
            ),
            key=lambda item: item["invocation_count"],
            reverse=True,
        )[:10]

        return {
            "total_hooks": len(self._hooks),
            "hooks_by_event": hooks_by_event,
            "hooks_by_status": hooks_by_status,
            "total_invocations": total_invocations,
            "avg_chain_latency_ms": avg_chain_latency_ms,
            "top_hooks_by_invocation": top_hooks_by_invocation,
        }

    def reset(self) -> None:
        """Clear all hooks, callbacks, chains, and invocation history."""
        self._hooks.clear()
        self._callbacks.clear()
        self._chains.clear()
        self._invocations.clear()


# --------------------------------------------------------------------------- #
# Process-wide singleton
# --------------------------------------------------------------------------- #

_lifecycle_hooks: AgentLifecycleHooks | None = None


def get_lifecycle_hooks() -> AgentLifecycleHooks:
    """Return the process-wide :class:`AgentLifecycleHooks` singleton.

    A new instance is lazily created on first access.
    """
    global _lifecycle_hooks
    if _lifecycle_hooks is None:
        _lifecycle_hooks = AgentLifecycleHooks()
    return _lifecycle_hooks


def reset_lifecycle_hooks() -> None:
    """Reset and discard the process-wide singleton.

    Calls :meth:`AgentLifecycleHooks.reset` on the existing instance (if any)
    to release references, then clears the singleton so the next
    :func:`get_lifecycle_hooks` call creates a fresh one.
    """
    global _lifecycle_hooks
    if _lifecycle_hooks is not None:
        _lifecycle_hooks.reset()
    _lifecycle_hooks = None
