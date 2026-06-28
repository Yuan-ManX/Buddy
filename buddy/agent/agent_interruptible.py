"""Buddy Agent Interruptible Execution — cancellable, pausable, resumable agent operations

This module implements an Agent Interruptible Execution system that provides
fine-grained control over long-running agent operations. It enables API calls,
tool executions, model invocations, and multi-step plans to be cancelled,
paused, and resumed through a unified coordination layer.

Core capabilities:

- Cancellation tokens with hierarchical parent-child relationships and scoped
  propagation (self, children, entire tree)
- Execution handles that track the lifecycle of each operation from pending
  through to a terminal state
- Checkpointing of intermediate execution state for durable resume semantics
- Multi-step execution tracking with per-step status and error capture
- Interrupt detection that converts token cancellation or deadline expiry into
  actionable signals for the running execution
- Thread-safe state transitions guarded by an internal lock
- Statistics and retention management for completed executions

The module is intentionally dependency-free, relying only on the Python
standard library so it can be embedded in any Buddy runtime environment.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enums ─────────────────────────────────────────────────


class ExecutionState(Enum):
    """Lifecycle states for an execution."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CHECKPOINTED = "checkpointed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    INTERRUPTED = "interrupted"


class CancellationReason(Enum):
    """Reasons why an execution was cancelled."""

    USER_REQUEST = "user_request"
    TIMEOUT = "timeout"
    PARENT_CANCELLED = "parent_cancelled"
    RESOURCE_LIMIT = "resource_limit"
    POLICY_VIOLATION = "policy_violation"
    DEPENDENCY_FAILED = "dependency_failed"
    SYSTEM_SHUTDOWN = "system_shutdown"
    PREEMPTED = "preempted"


class InterruptSignal(Enum):
    """Signals that can be raised against a running execution."""

    CANCEL = "cancel"
    PAUSE = "pause"
    RESUME = "resume"
    CHECKPOINT = "checkpoint"
    TIMEOUT = "timeout"
    YIELD = "yield"


class CheckpointType(Enum):
    """Categorization of when a checkpoint was captured."""

    PRE_STEP = "pre_step"
    POST_STEP = "post_step"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    PRE_MODEL = "pre_model"
    POST_MODEL = "post_model"
    ON_ERROR = "on_error"
    USER_DEFINED = "user_defined"


class ResumeStrategy(Enum):
    """Strategies for resuming an execution from a checkpoint."""

    FROM_CHECKPOINT = "from_checkpoint"
    FROM_START = "from_start"
    FROM_LAST_SUCCESS = "from_last_success"
    INTERACTIVE = "interactive"
    ABANDON = "abandon"


class ExecutionPriority(Enum):
    """Execution priority levels (lower value = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class CancellationScope(Enum):
    """Scope of propagation when cancelling a token or execution."""

    SELF = "self"
    CHILDREN = "children"
    ENTIRE_TREE = "entire_tree"


# ── Data Classes ──────────────────────────────────────────


@dataclass
class CancellationToken:
    """Token used to coordinate cancellation across executions.

    Tokens form a tree through ``parent_token_id`` / ``children`` so that
    cancelling an ancestor can be propagated to descendants according to the
    cancellation scope.
    """

    token_id: str
    parent_token_id: str | None = None
    is_cancelled: bool = False
    cancel_reason: CancellationReason | None = None
    cancelled_at: float | None = None
    cancellation_scope: CancellationScope = CancellationScope.SELF
    created_at: float = field(default_factory=time.time)
    children: list[str] = field(default_factory=list)


@dataclass
class Checkpoint:
    """A saved execution state captured at a specific point in time."""

    checkpoint_id: str
    execution_id: str
    checkpoint_type: CheckpointType
    step_index: int
    step_description: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    size_bytes: int = 0


@dataclass
class ExecutionHandle:
    """Handle describing a registered execution and its current state."""

    execution_id: str
    name: str
    description: str = ""
    agent_id: str = ""
    session_id: str = ""
    parent_execution_id: str | None = None
    token_id: str = field(default_factory=lambda: f"tok-{uuid.uuid4().hex[:12]}")
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    state: ExecutionState = ExecutionState.PENDING
    started_at: float | None = None
    completed_at: float | None = None
    last_checkpoint_id: str | None = None
    checkpoints: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    total_steps: int = 0
    completed_steps: int = 0
    current_step: str = ""
    error: str | None = None
    result: dict[str, Any] | None = None
    timeout_seconds: float | None = None
    deadline: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class CancellationRequest:
    """A request to cancel an execution, recorded for audit purposes."""

    request_id: str
    execution_id: str
    reason: CancellationReason
    scope: CancellationScope = CancellationScope.SELF
    requested_by: str = "user"
    requested_at: float = field(default_factory=time.time)
    processed: bool = False
    processed_at: float | None = None
    result: str | None = None


@dataclass
class ExecutionStep:
    """A single step within a multi-step execution."""

    step_id: str
    execution_id: str
    index: int
    name: str
    description: str = ""
    status: ExecutionState = ExecutionState.PENDING
    started_at: float | None = None
    completed_at: float | None = None
    checkpoint_id: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


# ── Executor ──────────────────────────────────────────────


class AgentInterruptibleExecutor:
    """Coordinates interruptible agent executions.

    The executor maintains the canonical state for executions, cancellation
    tokens, checkpoints, steps, and cancellation requests. All mutating
    operations acquire an internal lock so the executor is safe to call from
    multiple threads.
    """

    MAX_EXECUTIONS = 10000
    MAX_CHECKPOINTS_PER_EXECUTION = 100
    MAX_TOTAL_CHECKPOINTS = 100000
    DEFAULT_TIMEOUT_SECONDS = 300
    CLEANUP_INTERVAL_SECONDS = 60
    MAX_COMPLETED_RETENTION = 3600  # 1 hour

    def __init__(self) -> None:
        """Initialize an empty executor with no executions or tokens."""
        self._executions: dict[str, ExecutionHandle] = {}
        self._tokens: dict[str, CancellationToken] = {}
        self._checkpoints: dict[str, Checkpoint] = {}
        self._steps: dict[str, list[ExecutionStep]] = {}
        self._cancellation_requests: list[CancellationRequest] = []
        # RLock allows public methods to call each other while holding the lock.
        self._lock = threading.RLock()

    # ── Token management ────────────────────────────────

    def create_token(
        self,
        parent_token_id: str | None = None,
        scope: CancellationScope = CancellationScope.SELF,
    ) -> CancellationToken:
        """Create a cancellation token, optionally linked to a parent.

        When a parent token id is supplied the new token is registered as a
        child of that parent so cancellation can be propagated downward.
        """
        token = CancellationToken(
            token_id=f"tok-{uuid.uuid4().hex[:12]}",
            parent_token_id=parent_token_id,
            cancellation_scope=scope,
        )
        with self._lock:
            self._tokens[token.token_id] = token
            if parent_token_id is not None:
                parent = self._tokens.get(parent_token_id)
                if parent is not None and token.token_id not in parent.children:
                    parent.children.append(token.token_id)
        return token

    def cancel_token(
        self,
        token_id: str,
        reason: CancellationReason = CancellationReason.USER_REQUEST,
        scope: CancellationScope = CancellationScope.SELF,
    ) -> CancellationToken | None:
        """Mark a token as cancelled, optionally propagating to descendants.

        ``scope`` controls propagation: ``SELF`` cancels only the named token,
        ``CHILDREN`` cancels its descendants, and ``ENTIRE_TREE`` cancels both
        the token and all of its descendants.
        """
        with self._lock:
            token = self._tokens.get(token_id)
            if token is None:
                return None

            now = time.time()
            if scope == CancellationScope.ENTIRE_TREE:
                self._cancel_token_recursive(token, reason, now)
            elif scope == CancellationScope.CHILDREN:
                for child_id in list(token.children):
                    child = self._tokens.get(child_id)
                    if child is not None:
                        self._cancel_token_recursive(child, reason, now)
            else:
                if not token.is_cancelled:
                    token.is_cancelled = True
                    token.cancel_reason = reason
                    token.cancelled_at = now
                    token.cancellation_scope = scope
            return token

    def _cancel_token_recursive(
        self,
        token: CancellationToken,
        reason: CancellationReason,
        now: float,
    ) -> None:
        """Recursively cancel a token and all of its descendants."""
        if not token.is_cancelled:
            token.is_cancelled = True
            token.cancel_reason = reason
            token.cancelled_at = now
        for child_id in list(token.children):
            child = self._tokens.get(child_id)
            if child is not None:
                self._cancel_token_recursive(child, reason, now)

    def is_cancelled(self, token_id: str) -> bool:
        """Return ``True`` if the token or any of its ancestors is cancelled."""
        with self._lock:
            current_id = token_id
            visited: set[str] = set()
            while current_id is not None and current_id not in visited:
                visited.add(current_id)
                token = self._tokens.get(current_id)
                if token is None:
                    return False
                if token.is_cancelled:
                    return True
                current_id = token.parent_token_id
            return False

    def get_token(self, token_id: str) -> CancellationToken | None:
        """Return the token with the given id, if it exists."""
        with self._lock:
            return self._tokens.get(token_id)

    # ── Execution lifecycle ─────────────────────────────

    def register_execution(
        self,
        name: str,
        description: str = "",
        agent_id: str = "",
        session_id: str = "",
        parent_execution_id: str | None = None,
        priority: ExecutionPriority = ExecutionPriority.NORMAL,
        timeout_seconds: float | None = None,
        token_id: str | None = None,
        total_steps: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionHandle:
        """Register a new execution and return its handle.

        If ``token_id`` is not provided a new token is created. When
        ``parent_execution_id`` is supplied the new token is linked as a child
        of the parent's token and the execution is recorded as a child of the
        parent. A deadline is computed when ``timeout_seconds`` is provided.

        Raises:
            ValueError: if ``name`` is empty.
        """
        if not name or not name.strip():
            raise ValueError("Execution name must not be empty")

        execution_id = f"exec-{uuid.uuid4().hex[:12]}"

        with self._lock:
            parent_token_id: str | None = None
            if parent_execution_id is not None:
                parent_handle = self._executions.get(parent_execution_id)
                if parent_handle is not None:
                    parent_token_id = parent_handle.token_id

            if token_id is None:
                token = self.create_token(
                    parent_token_id=parent_token_id,
                    scope=CancellationScope.SELF,
                )
                token_id = token.token_id
            else:
                # Ensure the token is tracked; create on demand if unknown.
                if token_id not in self._tokens:
                    self._tokens[token_id] = CancellationToken(
                        token_id=token_id,
                        parent_token_id=parent_token_id,
                    )
                elif parent_token_id is not None:
                    parent_token = self._tokens.get(parent_token_id)
                    if (
                        parent_token is not None
                        and token_id not in parent_token.children
                    ):
                        parent_token.children.append(token_id)

            deadline: float | None = None
            if timeout_seconds is not None and timeout_seconds > 0:
                deadline = time.time() + timeout_seconds

            handle = ExecutionHandle(
                execution_id=execution_id,
                name=name,
                description=description,
                agent_id=agent_id,
                session_id=session_id,
                parent_execution_id=parent_execution_id,
                token_id=token_id,
                priority=priority,
                state=ExecutionState.PENDING,
                total_steps=total_steps,
                timeout_seconds=timeout_seconds,
                deadline=deadline,
                metadata=dict(metadata) if metadata else {},
            )
            self._executions[execution_id] = handle
            self._steps[execution_id] = []

            if parent_execution_id is not None:
                parent_handle = self._executions.get(parent_execution_id)
                if parent_handle is not None and execution_id not in parent_handle.children:
                    parent_handle.children.append(execution_id)
                    parent_handle.updated_at = time.time()

            return handle

    def start_execution(self, execution_id: str) -> ExecutionHandle | None:
        """Transition an execution from ``PENDING`` to ``RUNNING``."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None
            if handle.state != ExecutionState.PENDING:
                return handle
            handle.state = ExecutionState.RUNNING
            handle.started_at = time.time()
            handle.updated_at = handle.started_at
            return handle

    def complete_execution(
        self,
        execution_id: str,
        result: dict[str, Any] | None = None,
    ) -> ExecutionHandle | None:
        """Transition an execution to ``COMPLETED`` and store its result."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None
            now = time.time()
            handle.state = ExecutionState.COMPLETED
            handle.result = result
            handle.completed_at = now
            handle.updated_at = now
            return handle

    def fail_execution(
        self,
        execution_id: str,
        error: str,
    ) -> ExecutionHandle | None:
        """Transition an execution to ``FAILED`` with the given error message."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None
            now = time.time()
            handle.state = ExecutionState.FAILED
            handle.error = error
            handle.completed_at = now
            handle.updated_at = now
            return handle

    def cancel_execution(
        self,
        execution_id: str,
        reason: CancellationReason = CancellationReason.USER_REQUEST,
        scope: CancellationScope = CancellationScope.SELF,
        requested_by: str = "user",
    ) -> CancellationRequest:
        """Cancel an execution and record a cancellation request.

        The execution's token is cancelled with the supplied scope and the
        execution transitions through ``CANCELLING`` into ``CANCELLED``.
        Descendant executions are cancelled when the scope is ``CHILDREN`` or
        ``ENTIRE_TREE``.
        """
        request = CancellationRequest(
            request_id=f"cancel-{uuid.uuid4().hex[:12]}",
            execution_id=execution_id,
            reason=reason,
            scope=scope,
            requested_by=requested_by,
        )

        with self._lock:
            handle = self._executions.get(execution_id)
            now = time.time()

            if handle is None:
                request.processed = True
                request.processed_at = now
                request.result = "execution_not_found"
                self._cancellation_requests.append(request)
                return request

            # Cancel the token (and descendants if scope requires).
            token = self._tokens.get(handle.token_id)
            if token is not None:
                self._cancel_token_recursive(token, reason, now)

            if scope in (CancellationScope.CHILDREN, CancellationScope.ENTIRE_TREE):
                for child_id in list(handle.children):
                    child = self._executions.get(child_id)
                    if child is not None:
                        child_token = self._tokens.get(child.token_id)
                        if child_token is not None:
                            self._cancel_token_recursive(child_token, reason, now)
                        if child.state not in (
                            ExecutionState.COMPLETED,
                            ExecutionState.FAILED,
                            ExecutionState.CANCELLED,
                        ):
                            child.state = ExecutionState.CANCELLED
                            child.completed_at = now
                            child.updated_at = now

            handle.state = ExecutionState.CANCELLING
            handle.updated_at = now
            handle.state = ExecutionState.CANCELLED
            handle.completed_at = now
            handle.updated_at = now

            request.processed = True
            request.processed_at = now
            request.result = "cancelled"
            self._cancellation_requests.append(request)
            return request

    def pause_execution(self, execution_id: str) -> ExecutionHandle | None:
        """Transition a ``RUNNING`` execution to ``PAUSED``."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None
            if handle.state != ExecutionState.RUNNING:
                return handle
            handle.state = ExecutionState.PAUSED
            handle.updated_at = time.time()
            return handle

    def resume_execution(self, execution_id: str) -> ExecutionHandle | None:
        """Transition a ``PAUSED`` execution back to ``RUNNING``."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None
            if handle.state != ExecutionState.PAUSED:
                return handle
            handle.state = ExecutionState.RUNNING
            handle.updated_at = time.time()
            return handle

    # ── Checkpoints ──────────────────────────────────────

    def checkpoint(
        self,
        execution_id: str,
        checkpoint_type: CheckpointType = CheckpointType.USER_DEFINED,
        step_index: int = 0,
        step_description: str = "",
        state: dict[str, Any] | None = None,
    ) -> Checkpoint | None:
        """Save a checkpoint for an execution.

        The number of checkpoints per execution is capped at
        ``MAX_CHECKPOINTS_PER_EXECUTION`` and the total number of checkpoints
        is capped at ``MAX_TOTAL_CHECKPOINTS``. The new checkpoint becomes the
        execution's ``last_checkpoint_id``.
        """
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None
            if len(handle.checkpoints) >= self.MAX_CHECKPOINTS_PER_EXECUTION:
                # Drop the oldest checkpoint for this execution.
                oldest_id = handle.checkpoints.pop(0)
                self._checkpoints.pop(oldest_id, None)
            if len(self._checkpoints) >= self.MAX_TOTAL_CHECKPOINTS:
                return None

            checkpoint = Checkpoint(
                checkpoint_id=f"ckpt-{uuid.uuid4().hex[:12]}",
                execution_id=execution_id,
                checkpoint_type=checkpoint_type,
                step_index=step_index,
                step_description=step_description,
                state=dict(state) if state else {},
            )
            self._checkpoints[checkpoint.checkpoint_id] = checkpoint
            handle.checkpoints.append(checkpoint.checkpoint_id)
            handle.last_checkpoint_id = checkpoint.checkpoint_id
            handle.updated_at = time.time()
            return checkpoint

    def restore_checkpoint(
        self,
        execution_id: str,
        checkpoint_id: str | None = None,
        strategy: ResumeStrategy = ResumeStrategy.FROM_CHECKPOINT,
    ) -> ExecutionHandle | None:
        """Restore an execution from a checkpoint using the given strategy.

        ``FROM_CHECKPOINT`` resets the execution to ``PENDING`` so it can be
        restarted from the chosen checkpoint. ``FROM_START`` clears checkpoint
        references and resets progress. ``FROM_LAST_SUCCESS`` finds the most
        recent completed step's checkpoint. ``INTERACTIVE`` pauses the
        execution for user interaction. ``ABANDON`` fails the execution.
        """
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None

            now = time.time()

            if strategy == ResumeStrategy.ABANDON:
                handle.state = ExecutionState.FAILED
                handle.error = "abandoned_after_checkpoint"
                handle.completed_at = now
                handle.updated_at = now
                return handle

            if strategy == ResumeStrategy.INTERACTIVE:
                handle.state = ExecutionState.PAUSED
                handle.updated_at = now
                return handle

            if strategy == ResumeStrategy.FROM_START:
                handle.last_checkpoint_id = None
                handle.checkpoints.clear()
                handle.completed_steps = 0
                handle.current_step = ""
                handle.state = ExecutionState.PENDING
                handle.started_at = None
                handle.completed_at = None
                handle.updated_at = now
                return handle

            if strategy == ResumeStrategy.FROM_LAST_SUCCESS:
                steps = self._steps.get(execution_id, [])
                last_completed: ExecutionStep | None = None
                for step in steps:
                    if step.status == ExecutionState.COMPLETED:
                        last_completed = step
                if last_completed is not None and last_completed.checkpoint_id:
                    handle.last_checkpoint_id = last_completed.checkpoint_id
                handle.state = ExecutionState.PENDING
                handle.updated_at = now
                return handle

            # Default: FROM_CHECKPOINT
            target_id = checkpoint_id or handle.last_checkpoint_id
            if target_id is None:
                return handle
            if target_id not in self._checkpoints:
                return handle
            handle.last_checkpoint_id = target_id
            handle.state = ExecutionState.CHECKPOINTED
            handle.updated_at = now
            return handle

    # ── Steps ────────────────────────────────────────────

    def record_step(
        self,
        execution_id: str,
        step_id: str,
        index: int,
        name: str,
        description: str = "",
    ) -> ExecutionStep | None:
        """Record a new step against an execution."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None
            step = ExecutionStep(
                step_id=step_id,
                execution_id=execution_id,
                index=index,
                name=name,
                description=description,
            )
            self._steps.setdefault(execution_id, []).append(step)
            handle.current_step = name
            handle.updated_at = time.time()
            return step

    def start_step(self, execution_id: str, step_id: str) -> ExecutionStep | None:
        """Mark a recorded step as ``RUNNING``."""
        with self._lock:
            steps = self._steps.get(execution_id, [])
            for step in steps:
                if step.step_id == step_id:
                    step.status = ExecutionState.RUNNING
                    step.started_at = time.time()
                    handle = self._executions.get(execution_id)
                    if handle is not None:
                        handle.current_step = step.name
                        handle.updated_at = step.started_at
                    return step
            return None

    def complete_step(
        self,
        execution_id: str,
        step_id: str,
        result: dict[str, Any] | None = None,
    ) -> ExecutionStep | None:
        """Mark a step as ``COMPLETED`` and bump the execution's progress."""
        with self._lock:
            steps = self._steps.get(execution_id, [])
            for step in steps:
                if step.step_id == step_id:
                    step.status = ExecutionState.COMPLETED
                    step.completed_at = time.time()
                    step.result = result
                    handle = self._executions.get(execution_id)
                    if handle is not None:
                        handle.completed_steps += 1
                        handle.updated_at = step.completed_at
                    return step
            return None

    def fail_step(
        self,
        execution_id: str,
        step_id: str,
        error: str,
    ) -> ExecutionStep | None:
        """Mark a step as ``FAILED`` with the supplied error message."""
        with self._lock:
            steps = self._steps.get(execution_id, [])
            for step in steps:
                if step.step_id == step_id:
                    step.status = ExecutionState.FAILED
                    step.completed_at = time.time()
                    step.error = error
                    handle = self._executions.get(execution_id)
                    if handle is not None:
                        handle.updated_at = step.completed_at
                    return step
            return None

    # ── Interrupt detection ─────────────────────────────

    def check_interrupt(self, execution_id: str) -> InterruptSignal | None:
        """Return an interrupt signal for the execution, if any.

        Token cancellation produces a ``CANCEL`` signal and an exceeded
        deadline produces a ``TIMEOUT`` signal. ``None`` is returned when the
        execution may continue.
        """
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return None
            if handle.state in (
                ExecutionState.COMPLETED,
                ExecutionState.FAILED,
                ExecutionState.CANCELLED,
                ExecutionState.TIMED_OUT,
            ):
                return None

            current_id = handle.token_id
            visited: set[str] = set()
            while current_id is not None and current_id not in visited:
                visited.add(current_id)
                ancestor = self._tokens.get(current_id)
                if ancestor is None:
                    break
                if ancestor.is_cancelled:
                    if ancestor.cancel_reason == CancellationReason.TIMEOUT:
                        return InterruptSignal.TIMEOUT
                    return InterruptSignal.CANCEL
                current_id = ancestor.parent_token_id

            if handle.deadline is not None and time.time() >= handle.deadline:
                return InterruptSignal.TIMEOUT

            return None

    # ── Queries ─────────────────────────────────────────

    def get_execution(self, execution_id: str) -> ExecutionHandle | None:
        """Return the execution handle for the given id."""
        with self._lock:
            return self._executions.get(execution_id)

    def list_executions(
        self,
        state: ExecutionState | None = None,
        agent_id: str | None = None,
        parent: str | None = None,
        limit: int = 100,
    ) -> list[ExecutionHandle]:
        """List executions filtered by state, agent, or parent.

        Results are returned in creation order (oldest first).
        """
        with self._lock:
            results: list[ExecutionHandle] = []
            for handle in self._executions.values():
                if state is not None and handle.state != state:
                    continue
                if agent_id is not None and handle.agent_id != agent_id:
                    continue
                if parent is not None and handle.parent_execution_id != parent:
                    continue
                results.append(handle)
                if len(results) >= limit:
                    break
            return results

    def get_children(self, execution_id: str) -> list[ExecutionHandle]:
        """Return the direct child executions of the given execution."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return []
            children: list[ExecutionHandle] = []
            for child_id in handle.children:
                child = self._executions.get(child_id)
                if child is not None:
                    children.append(child)
            return children

    def get_checkpoints(self, execution_id: str) -> list[Checkpoint]:
        """Return all checkpoints for an execution in creation order."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return []
            checkpoints: list[Checkpoint] = []
            for checkpoint_id in handle.checkpoints:
                checkpoint = self._checkpoints.get(checkpoint_id)
                if checkpoint is not None:
                    checkpoints.append(checkpoint)
            return checkpoints

    def get_steps(self, execution_id: str) -> list[ExecutionStep]:
        """Return all steps recorded for an execution."""
        with self._lock:
            return list(self._steps.get(execution_id, []))

    def get_cancellation_requests(
        self,
        execution_id: str | None = None,
        limit: int = 100,
    ) -> list[CancellationRequest]:
        """Return cancellation requests, optionally filtered by execution."""
        with self._lock:
            if execution_id is None:
                return list(self._cancellation_requests[-limit:])
            return [
                request
                for request in self._cancellation_requests
                if request.execution_id == execution_id
            ][-limit:]

    # ── Maintenance ──────────────────────────────────────

    def cleanup_expired(self) -> int:
        """Remove terminal executions older than ``MAX_COMPLETED_RETENTION``.

        Returns the number of executions that were removed.
        """
        cutoff = time.time() - self.MAX_COMPLETED_RETENTION
        terminal_states = {
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
            ExecutionState.TIMED_OUT,
            ExecutionState.INTERRUPTED,
        }
        with self._lock:
            to_remove: list[str] = []
            for execution_id, handle in self._executions.items():
                if handle.state not in terminal_states:
                    continue
                end_time = handle.completed_at or handle.updated_at
                if end_time < cutoff:
                    to_remove.append(execution_id)
            for execution_id in to_remove:
                handle = self._executions.pop(execution_id, None)
                if handle is not None:
                    for checkpoint_id in handle.checkpoints:
                        self._checkpoints.pop(checkpoint_id, None)
                self._steps.pop(execution_id, None)
            return len(to_remove)

    def get_execution_stats(self, execution_id: str) -> dict[str, Any]:
        """Return statistics for a single execution."""
        with self._lock:
            handle = self._executions.get(execution_id)
            if handle is None:
                return {}
            now = time.time()
            duration: float | None = None
            if handle.started_at is not None:
                end = handle.completed_at or now
                duration = end - handle.started_at
            return {
                "execution_id": execution_id,
                "state": handle.state.value,
                "duration": duration,
                "total_steps": handle.total_steps,
                "completed_steps": handle.completed_steps,
                "steps_progress": (
                    handle.completed_steps / handle.total_steps
                    if handle.total_steps > 0
                    else 0.0
                ),
                "checkpoint_count": len(handle.checkpoints),
                "has_children": len(handle.children) > 0,
                "is_cancelled": self._is_token_cancelled_unlocked(handle.token_id),
            }

    def _is_token_cancelled_unlocked(self, token_id: str) -> bool:
        """Check token cancellation without acquiring the lock."""
        current_id = token_id
        visited: set[str] = set()
        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            token = self._tokens.get(current_id)
            if token is None:
                return False
            if token.is_cancelled:
                return True
            current_id = token.parent_token_id
        return False

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all executions."""
        with self._lock:
            total = len(self._executions)
            by_state: dict[str, int] = {}
            by_priority: dict[str, int] = {}
            durations: list[float] = []
            cancellation_count = 0
            cutoff = time.time() - self.MAX_COMPLETED_RETENTION
            cleanup_candidates = 0
            terminal_states = {
                ExecutionState.COMPLETED,
                ExecutionState.FAILED,
                ExecutionState.CANCELLED,
                ExecutionState.TIMED_OUT,
                ExecutionState.INTERRUPTED,
            }

            for handle in self._executions.values():
                by_state[handle.state.value] = by_state.get(handle.state.value, 0) + 1
                by_priority[handle.priority.name] = (
                    by_priority.get(handle.priority.name, 0) + 1
                )
                if handle.state == ExecutionState.CANCELLED:
                    cancellation_count += 1
                if (
                    handle.state in terminal_states
                    and (handle.completed_at or handle.updated_at) < cutoff
                ):
                    cleanup_candidates += 1
                if handle.started_at is not None and handle.completed_at is not None:
                    durations.append(handle.completed_at - handle.started_at)

            avg_duration = (
                sum(durations) / len(durations) if durations else 0.0
            )

            return {
                "total_executions": total,
                "by_state": by_state,
                "by_priority": by_priority,
                "total_checkpoints": len(self._checkpoints),
                "total_cancellations": cancellation_count,
                "avg_duration": avg_duration,
                "cleanup_candidate_count": cleanup_candidates,
            }

    def reset(self) -> None:
        """Clear all executions, tokens, checkpoints, steps, and requests."""
        with self._lock:
            self._executions.clear()
            self._tokens.clear()
            self._checkpoints.clear()
            self._steps.clear()
            self._cancellation_requests.clear()


# ── Singleton ─────────────────────────────────────────────


_interruptible_executor: AgentInterruptibleExecutor | None = None


def get_interruptible_executor() -> AgentInterruptibleExecutor:
    """Return the shared :class:`AgentInterruptibleExecutor` instance."""
    global _interruptible_executor
    if _interruptible_executor is None:
        _interruptible_executor = AgentInterruptibleExecutor()
    return _interruptible_executor


def reset_interruptible_executor() -> None:
    """Reset the shared executor instance, clearing all in-memory state."""
    global _interruptible_executor
    if _interruptible_executor is not None:
        _interruptible_executor.reset()
    _interruptible_executor = None
