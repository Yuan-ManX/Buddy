"""
Buddy Trajectory — Execution History Compression & Learning

Captures agent execution traces, compresses them into meaningful
summary trajectories, and extracts learnable patterns for continuous
improvement. Trajectories are the raw material for the Forge — every
completed task becomes training data that makes the entire system smarter.

The trajectory system handles:
  - Raw trace capture with structured action/observation pairs
  - Intelligent compression for storage efficiency
  - Pattern extraction for the self-improving learning loop
  - Audit trail generation for white-box debugging
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.trajectory")


# ── Trace Models ──

class TraceAction(str, Enum):
    """Types of actions that can appear in an execution trace."""
    USER_MESSAGE = "user_message"
    THINK = "think"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ASSISTANT_MESSAGE = "assistant_message"
    PLANNING = "planning"
    DELEGATION = "delegation"
    REFLECTION = "reflection"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class TraceStep:
    """A single step in an execution trace."""
    step_id: str
    action: TraceAction
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: float = 0.0
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)

    def dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "action": self.action.value,
            "content": self.content[:500],  # Truncate for storage
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "tool_name": self.tool_name,
        }


@dataclass
class ExecutionTrace:
    """A complete execution trace for a single task."""
    trace_id: str
    agent_id: str
    task_id: str = ""
    steps: list[TraceStep] = field(default_factory=list)
    status: str = "in_progress"  # in_progress, completed, failed, cancelled
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    quality_score: float = 0.0

    def add_step(self, step: TraceStep):
        self.steps.append(step)
        self.total_tokens += step.tokens_used
        self.total_latency_ms += step.latency_ms

    def dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "step_count": len(self.steps),
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "quality_score": self.quality_score,
        }


# ── Compressed Trajectory ──

@dataclass
class CompressedTrajectory:
    """A compressed version of an execution trace for storage and learning."""
    original_trace_id: str
    agent_id: str
    summary: str
    key_decisions: list[str]
    tools_used: list[str]
    success: bool
    quality_score: float
    num_steps_original: int
    num_steps_compressed: int
    tokens_saved: int
    patterns_extracted: list[str]
    compressed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def dict(self) -> dict:
        return {
            "original_trace_id": self.original_trace_id,
            "agent_id": self.agent_id,
            "summary": self.summary,
            "key_decisions": self.key_decisions,
            "tools_used": self.tools_used,
            "success": self.success,
            "quality_score": self.quality_score,
            "num_steps_original": self.num_steps_original,
            "num_steps_compressed": self.num_steps_compressed,
            "tokens_saved": self.tokens_saved,
            "patterns_extracted": self.patterns_extracted,
            "compressed_at": self.compressed_at,
        }


# ── Trajectory Compressor ──

class BuddyTrajectory:
    """Execution trace capture, compression, and learning system.

    The Trajectory system records every agent execution as structured
    traces, then compresses them into compact summaries that preserve
    key decision points while discarding redundant intermediate steps.
    The compressed trajectories become input to the Forge for autonomous
    skill creation.

    This is the foundation of Buddy's white-box memory — every decision
    is traceable, every outcome is auditable.
    """

    def __init__(self):
        self._active_traces: dict[str, ExecutionTrace] = {}
        self._compressed: list[CompressedTrajectory] = []
        self._max_compressed = 1000

    # ── Trace Capture ──

    def start_trace(
        self,
        agent_id: str,
        task_id: str = "",
    ) -> ExecutionTrace:
        """Begin capturing an execution trace."""
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        trace = ExecutionTrace(
            trace_id=trace_id,
            agent_id=agent_id,
            task_id=task_id,
        )
        self._active_traces[trace_id] = trace
        logger.info(f"Trace started: {trace_id}")
        return trace

    def record_step(
        self,
        trace_id: str,
        action: TraceAction,
        content: str,
        tokens: int = 0,
        latency_ms: float = 0.0,
        tool_name: str = "",
        tool_args: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Record a step in an active trace."""
        trace = self._active_traces.get(trace_id)
        if not trace:
            return

        step = TraceStep(
            step_id=f"step-{len(trace.steps)+1:04d}",
            action=action,
            content=content,
            tokens_used=tokens,
            latency_ms=latency_ms,
            tool_name=tool_name,
            tool_args=tool_args or {},
            metadata=metadata or {},
        )
        trace.add_step(step)

    def complete_trace(
        self,
        trace_id: str,
        success: bool,
        quality_score: float = 1.0,
    ) -> ExecutionTrace | None:
        """Mark a trace as completed."""
        trace = self._active_traces.pop(trace_id, None)
        if not trace:
            return None

        trace.status = "completed" if success else "failed"
        trace.completed_at = datetime.now(timezone.utc).isoformat()
        trace.quality_score = quality_score

        logger.info(
            f"Trace {trace_id} {trace.status}: "
            f"{len(trace.steps)} steps, {trace.total_tokens} tokens"
        )
        return trace

    def cancel_trace(self, trace_id: str):
        """Cancel an active trace."""
        trace = self._active_traces.pop(trace_id, None)
        if trace:
            trace.status = "cancelled"
            trace.completed_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Trace cancelled: {trace_id}")

    def get_active_trace(self, trace_id: str) -> ExecutionTrace | None:
        return self._active_traces.get(trace_id)

    # ── Compression ──

    def compress_trace(self, trace: ExecutionTrace) -> CompressedTrajectory:
        """Compress an execution trace into a compact learning trajectory.

        The compression preserves:
          - The task summary (what was accomplished)
          - Key decision points (where the agent made important choices)
          - Tools used (what capabilities were exercised)
          - Extracted patterns (what can be learned)

        It discards:
          - Redundant intermediate observations
          - Repetitive tool call/result pairs
          - No-op content
        """
        # Extract key decision points
        key_decisions = []
        tools_used = []
        patterns = []

        for step in trace.steps:
            if step.action in (TraceAction.PLANNING, TraceAction.REFLECTION):
                key_decisions.append(step.content[:200])
            if step.action == TraceAction.TOOL_CALL and step.tool_name:
                tools_used.append(step.tool_name)
            if step.action == TraceAction.DELEGATION:
                key_decisions.append(f"Delegated: {step.content[:200]}")

        # Deduplicate tools
        tools_used = list(dict.fromkeys(tools_used))

        # Generate summary
        actions_taken = [s.action.value for s in trace.steps]
        pattern_signature = self._extract_pattern_signature(actions_taken)

        summary = self._generate_summary(trace, key_decisions, tools_used)

        # Calculate compression ratio
        original_content_len = sum(len(s.content) for s in trace.steps)
        compressed_len = len(summary) + sum(len(d) for d in key_decisions)

        compressed = CompressedTrajectory(
            original_trace_id=trace.trace_id,
            agent_id=trace.agent_id,
            summary=summary,
            key_decisions=key_decisions[:10],
            tools_used=tools_used,
            success=trace.status == "completed",
            quality_score=trace.quality_score,
            num_steps_original=len(trace.steps),
            num_steps_compressed=len(key_decisions) + 1,
            tokens_saved=max(0, original_content_len - compressed_len),
            patterns_extracted=[pattern_signature],
        )

        self._compressed.append(compressed)
        if len(self._compressed) > self._max_compressed:
            self._compressed = self._compressed[-self._max_compressed:]

        logger.info(
            f"Trace {trace.trace_id} compressed: "
            f"{len(trace.steps)} steps → {compressed.num_steps_compressed} points "
            f"({compressed.tokens_saved} chars saved)"
        )
        return compressed

    # ── Learning Interface ──

    def get_recent_trajectories(self, limit: int = 20) -> list[CompressedTrajectory]:
        """Get the most recent compressed trajectories for learning."""
        return self._compressed[-limit:]

    def get_successful_trajectories(self, limit: int = 50) -> list[CompressedTrajectory]:
        """Get successful trajectories for positive reinforcement learning."""
        return [t for t in self._compressed if t.success][-limit:]

    def get_failed_trajectories(self, limit: int = 20) -> list[CompressedTrajectory]:
        """Get failed trajectories for failure analysis."""
        return [t for t in self._compressed if not t.success][-limit:]

    def get_trajectories_by_agent(self, agent_id: str, limit: int = 50) -> list[CompressedTrajectory]:
        """Get trajectories for a specific agent."""
        return [t for t in self._compressed if t.agent_id == agent_id][-limit:]

    # ── Statistics ──

    def get_stats(self) -> dict:
        successful = len(self.get_successful_trajectories())
        failed = len(self.get_failed_trajectories())

        agent_stats: dict[str, dict] = {}
        for t in self._compressed:
            if t.agent_id not in agent_stats:
                agent_stats[t.agent_id] = {"total": 0, "success": 0}
            agent_stats[t.agent_id]["total"] += 1
            if t.success:
                agent_stats[t.agent_id]["success"] += 1

        return {
            "total_compressed": len(self._compressed),
            "active_traces": len(self._active_traces),
            "successful": successful,
            "failed": failed,
            "success_rate": (
                successful / max(successful + failed, 1)
            ),
            "avg_quality_score": (
                sum(t.quality_score for t in self._compressed) / max(len(self._compressed), 1)
            ),
            "total_tokens_saved": sum(t.tokens_saved for t in self._compressed),
            "by_agent": agent_stats,
        }

    # ── Internal ──

    @staticmethod
    def _generate_summary(
        trace: ExecutionTrace,
        decisions: list[str],
        tools: list[str],
    ) -> str:
        """Generate a human-readable summary from a trace."""
        user_msgs = [s.content[:100] for s in trace.steps if s.action == TraceAction.USER_MESSAGE]
        task = user_msgs[0] if user_msgs else "Unknown task"
        tool_str = ", ".join(tools[:5]) if tools else "no tools"
        decisions_str = "; ".join(decisions[:3]) if decisions else "no key decisions"

        return (
            f"Task: {task}. "
            f"Used {len(trace.steps)} steps. "
            f"Tools: {tool_str}. "
            f"Key decisions: {decisions_str}. "
            f"Result: {trace.status}."
        )

    @staticmethod
    def _extract_pattern_signature(actions: list[str]) -> str:
        """Create a hashable pattern signature from action sequences."""
        clean = [
            a.replace("tool_call", "TC")
            .replace("tool_result", "TR")
            .replace("think", "TH")
            .replace("user_message", "UM")
            .replace("assistant_message", "AM")
            for a in actions
        ]
        sequence = "→".join(clean)
        sig = hashlib.md5(sequence.encode()).hexdigest()[:8]
        return f"pattern:{sig}"