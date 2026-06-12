"""
Buddy Compressor — Execution History Compression and Learning

Compresses agent execution trajectories into compact, structured summaries
suitable for storage, retrieval, and downstream training. Extracts patterns
from tool calls, reasoning chains, and outcomes to build a searchable
execution knowledge base.

Capabilities:
  - Trajectory summarization with key decision points
  - Pattern extraction from repeated tool usage
  - Compression ratio reporting and quality scoring
  - Training data generation for tool-calling models
  - Cross-session pattern detection and reuse
"""
from __future__ import annotations

import json
import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("buddy.compressor")


@dataclass
class CompressedTrajectory:
    """A compressed representation of an agent execution trajectory."""

    id: str
    agent_id: str
    session_id: str
    created_at: str

    # Summary
    goal: str
    outcome: str  # "success", "partial", "failure"
    summary: str  # Human-readable summary

    # Key decision points
    key_decisions: list[dict[str, Any]] = field(default_factory=list)
    # Each: {"step": int, "decision": str, "reasoning": str, "impact": str}

    # Tool usage patterns
    tool_patterns: list[dict[str, Any]] = field(default_factory=list)
    # Each: {"tool": str, "count": int, "success_rate": float, "typical_args": dict}

    # Extracted insights
    insights: list[str] = field(default_factory=list)

    # Metrics
    total_steps: int = 0
    total_tool_calls: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    duration_seconds: float = 0.0

    # Compression metadata
    original_size_bytes: int = 0
    compressed_size_bytes: int = 0
    compression_ratio: float = 1.0
    quality_score: float = 1.0  # 0.0 to 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "goal": self.goal,
            "outcome": self.outcome,
            "summary": self.summary,
            "key_decisions": self.key_decisions,
            "tool_patterns": self.tool_patterns,
            "insights": self.insights,
            "total_steps": self.total_steps,
            "total_tool_calls": self.total_tool_calls,
            "total_tokens": self.total_tokens,
            "estimated_cost": self.estimated_cost,
            "duration_seconds": self.duration_seconds,
            "original_size_bytes": self.original_size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "compression_ratio": self.compression_ratio,
            "quality_score": self.quality_score,
        }


@dataclass
class ExecutionPattern:
    """A detected pattern from repeated agent executions."""

    pattern_id: str
    pattern_type: str  # "tool_sequence", "reasoning_chain", "error_recovery", "optimization"
    description: str
    frequency: int
    success_rate: float
    template: dict[str, Any] = field(default_factory=dict)
    related_trajectories: list[str] = field(default_factory=list)


@dataclass
class CompressionStats:
    """Statistics about the compression system."""

    total_trajectories_compressed: int = 0
    total_patterns_detected: int = 0
    average_compression_ratio: float = 0.0
    average_quality_score: float = 0.0
    total_bytes_saved: int = 0
    patterns_by_type: dict[str, int] = field(default_factory=dict)


class TrajectoryCompressor:
    """Compresses agent execution trajectories into structured summaries.

    Usage:
        compressor = TrajectoryCompressor()
        compressed = compressor.compress(trajectory_data, agent_id, session_id)
        patterns = compressor.detect_patterns(agent_id)
    """

    # Minimum number of trajectories needed before pattern detection
    MIN_TRAJECTORIES_FOR_PATTERNS = 3

    # Thresholds for compression quality
    MIN_QUALITY_SCORE = 0.3

    def __init__(self):
        self._compressed: dict[str, CompressedTrajectory] = {}
        self._patterns: dict[str, ExecutionPattern] = {}
        self._stats = CompressionStats()

    def _generate_id(self, prefix: str = "ct") -> str:
        """Generate a unique ID for compressed trajectories."""
        timestamp = datetime.now(timezone.utc).isoformat()
        raw = f"{prefix}-{timestamp}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def compress(
        self,
        trajectory: dict[str, Any],
        agent_id: str,
        session_id: str,
    ) -> CompressedTrajectory:
        """Compress a raw trajectory into a structured summary.

        Args:
            trajectory: Raw trajectory data with steps, messages, tool calls
            agent_id: The agent that executed the trajectory
            session_id: The conversation session ID

        Returns:
            CompressedTrajectory with extracted patterns and insights
        """
        trajectory_id = self._generate_id("ct")

        # Extract steps
        steps = trajectory.get("steps", [])
        messages = trajectory.get("messages", [])
        tool_calls_data = trajectory.get("tool_calls", [])

        # Calculate original size
        original_json = json.dumps(trajectory, default=str)
        original_size = len(original_json.encode("utf-8"))

        # Extract goal from first user message
        goal = "Unknown task"
        for msg in messages:
            if msg.get("role") == "user":
                goal = msg.get("content", "Unknown task")[:200]
                break

        # Determine outcome from last step status
        outcome = "success"
        if steps:
            last_step = steps[-1]
            step_status = last_step.get("status", "success")
            if step_status == "error":
                outcome = "failure"
            elif step_status == "partial":
                outcome = "partial"

        # Extract key decisions (significant reasoning points)
        key_decisions = self._extract_key_decisions(steps, messages)

        # Analyze tool usage patterns
        tool_patterns = self._analyze_tool_patterns(tool_calls_data)

        # Generate insights
        insights = self._generate_insights(steps, tool_calls_data, outcome)

        # Calculate metrics
        total_steps = len(steps)
        total_tool_calls = len(tool_calls_data)
        total_tokens = trajectory.get("total_tokens", 0)
        estimated_cost = trajectory.get("estimated_cost", 0.0)
        duration = trajectory.get("duration_seconds", 0.0)

        # Generate summary
        summary = self._generate_summary(goal, outcome, key_decisions, tool_patterns)

        # Build compressed trajectory
        compressed = CompressedTrajectory(
            id=trajectory_id,
            agent_id=agent_id,
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            goal=goal,
            outcome=outcome,
            summary=summary,
            key_decisions=key_decisions,
            tool_patterns=tool_patterns,
            insights=insights,
            total_steps=total_steps,
            total_tool_calls=total_tool_calls,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            duration_seconds=duration,
            original_size_bytes=original_size,
        )

        # Calculate compression metrics
        compressed_json = json.dumps(compressed.to_dict(), default=str)
        compressed_size = len(compressed_json.encode("utf-8"))
        compressed.compressed_size_bytes = compressed_size
        compressed.compression_ratio = (
            original_size / compressed_size if compressed_size > 0 else 1.0
        )
        compressed.quality_score = self._calculate_quality(compressed)

        # Store
        self._compressed[trajectory_id] = compressed
        self._stats.total_trajectories_compressed += 1
        self._stats.total_bytes_saved += original_size - compressed_size

        # Update average stats
        n = self._stats.total_trajectories_compressed
        self._stats.average_compression_ratio = (
            (self._stats.average_compression_ratio * (n - 1) + compressed.compression_ratio) / n
        )
        self._stats.average_quality_score = (
            (self._stats.average_quality_score * (n - 1) + compressed.quality_score) / n
        )

        logger.info(
            f"Compressed trajectory {trajectory_id}: "
            f"{original_size} -> {compressed_size} bytes "
            f"({compressed.compression_ratio:.1f}x, quality={compressed.quality_score:.2f})"
        )

        return compressed

    def _extract_key_decisions(
        self,
        steps: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract significant decision points from steps."""
        decisions = []
        for i, step in enumerate(steps):
            reasoning = step.get("reasoning", "")
            action = step.get("action", "")

            # Identify steps with tool calls or significant reasoning
            if reasoning and len(reasoning) > 50:
                decisions.append({
                    "step": i,
                    "decision": action or reasoning[:100],
                    "reasoning": reasoning[:300],
                    "impact": step.get("outcome", "unknown"),
                })

        return decisions[:10]  # Limit to top 10

    def _analyze_tool_patterns(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Analyze tool usage to find patterns."""
        tool_stats: dict[str, dict[str, Any]] = {}

        for call in tool_calls:
            tool_name = call.get("name", call.get("tool", "unknown"))
            success = call.get("success", call.get("status") == "done")

            if tool_name not in tool_stats:
                tool_stats[tool_name] = {
                    "tool": tool_name,
                    "count": 0,
                    "successes": 0,
                    "arg_keys": [],
                }

            tool_stats[tool_name]["count"] += 1
            if success:
                tool_stats[tool_name]["successes"] += 1

            # Track common argument patterns
            args = call.get("args", call.get("arguments", {}))
            if isinstance(args, dict):
                for key in args:
                    if key not in tool_stats[tool_name]["arg_keys"]:
                        tool_stats[tool_name]["arg_keys"].append(key)

        patterns = []
        for name, stats in tool_stats.items():
            count = stats["count"]
            success_rate = stats["successes"] / count if count > 0 else 0.0
            patterns.append({
                "tool": name,
                "count": count,
                "success_rate": round(success_rate, 2),
                "typical_args": stats["arg_keys"][:5],
            })

        return patterns

    def _generate_insights(
        self,
        steps: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]],
        outcome: str,
    ) -> list[str]:
        """Generate actionable insights from the trajectory."""
        insights = []

        # Outcome-based insight
        if outcome == "success":
            insights.append("Task completed successfully with efficient tool usage")
        elif outcome == "partial":
            insights.append("Task partially completed; some steps could be optimized")
        else:
            insights.append("Task failed; review error patterns for improvement")

        # Tool efficiency insight
        if len(steps) > 0 and len(tool_calls) > 0:
            ratio = len(tool_calls) / len(steps)
            if ratio > 2:
                insights.append(f"High tool call density ({ratio:.1f} calls/step); consider batching")
            elif ratio < 0.5:
                insights.append("Low tool utilization; more tools could accelerate workflow")

        # Error recovery insight
        errors = [s for s in steps if s.get("status") == "error"]
        if errors:
            insights.append(f"Encountered {len(errors)} errors; common failure patterns should be addressed")

        return insights

    def _generate_summary(
        self,
        goal: str,
        outcome: str,
        key_decisions: list[dict[str, Any]],
        tool_patterns: list[dict[str, Any]],
    ) -> str:
        """Generate a human-readable summary of the trajectory."""
        parts = [f"Goal: {goal}"]

        # Tool summary
        if tool_patterns:
            tool_names = [p["tool"] for p in tool_patterns[:5]]
            parts.append(f"Tools used: {', '.join(tool_names)}")

        # Decision summary
        if key_decisions:
            parts.append(f"Key decisions: {len(key_decisions)} significant turns")

        # Outcome
        parts.append(f"Outcome: {outcome}")

        return " | ".join(parts)

    def _calculate_quality(self, compressed: CompressedTrajectory) -> float:
        """Calculate the quality score of a compressed trajectory."""
        score = 0.5  # Base score

        # Bonus for having insights
        if compressed.insights:
            score += 0.2

        # Bonus for tool patterns detected
        if compressed.tool_patterns:
            score += 0.15

        # Bonus for key decisions extracted
        if compressed.key_decisions:
            score += 0.15

        # Penalty for very low compression ratio (no meaningful compression)
        if compressed.compression_ratio < 1.5:
            score -= 0.1

        return min(max(score, 0.0), 1.0)

    def detect_patterns(self, agent_id: str) -> list[ExecutionPattern]:
        """Detect recurring patterns across compressed trajectories.

        Requires at least MIN_TRAJECTORIES_FOR_PATTERNS compressed trajectories
        for the given agent before patterns can be detected.
        """
        agent_trajectories = [
            ct for ct in self._compressed.values() if ct.agent_id == agent_id
        ]

        if len(agent_trajectories) < self.MIN_TRAJECTORIES_FOR_PATTERNS:
            return []

        patterns = []

        # Detect tool sequence patterns
        tool_sequences = self._find_recurring_tool_sequences(agent_trajectories)
        for seq in tool_sequences:
            pattern_id = self._generate_id("pat")
            pattern = ExecutionPattern(
                pattern_id=pattern_id,
                pattern_type="tool_sequence",
                description=f"Recurring tool sequence: {' -> '.join(seq['tools'])}",
                frequency=seq["frequency"],
                success_rate=seq["success_rate"],
                template={"tools": seq["tools"], "order": seq["order"]},
                related_trajectories=seq["trajectory_ids"],
            )
            patterns.append(pattern)
            self._patterns[pattern_id] = pattern

        # Detect error recovery patterns
        recovery_patterns = self._find_error_recovery_patterns(agent_trajectories)
        for rec in recovery_patterns:
            pattern_id = self._generate_id("pat")
            pattern = ExecutionPattern(
                pattern_id=pattern_id,
                pattern_type="error_recovery",
                description=f"Error recovery: {rec['error_tool']} -> {rec['recovery_tool']}",
                frequency=rec["frequency"],
                success_rate=rec["success_rate"],
                template={"error": rec["error_tool"], "recovery": rec["recovery_tool"]},
                related_trajectories=rec["trajectory_ids"],
            )
            patterns.append(pattern)
            self._patterns[pattern_id] = pattern

        self._stats.total_patterns_detected += len(patterns)

        for p in patterns:
            ptype = p.pattern_type
            self._stats.patterns_by_type[ptype] = self._stats.patterns_by_type.get(ptype, 0) + 1

        return patterns

    def _find_recurring_tool_sequences(
        self,
        trajectories: list[CompressedTrajectory],
    ) -> list[dict[str, Any]]:
        """Find recurring sequences of tool usage across trajectories."""
        if not trajectories:
            return []

        # Collect all tool sequences
        sequences: list[tuple[str, ...]] = []
        for ct in trajectories:
            tools = tuple(p["tool"] for p in ct.tool_patterns)
            if tools:
                sequences.append(tools)

        # Count frequencies
        from collections import Counter
        seq_counter = Counter(sequences)

        patterns = []
        for seq, count in seq_counter.most_common(5):
            if count >= 2:  # Must appear at least twice
                related_ids = [
                    ct.id for ct in trajectories
                    if tuple(p["tool"] for p in ct.tool_patterns) == seq
                ]
                success_count = sum(
                    1 for ct in trajectories
                    if tuple(p["tool"] for p in ct.tool_patterns) == seq
                    and ct.outcome == "success"
                )
                patterns.append({
                    "tools": list(seq),
                    "order": list(range(len(seq))),
                    "frequency": count,
                    "success_rate": success_count / count if count > 0 else 0.0,
                    "trajectory_ids": related_ids,
                })

        return patterns

    def _find_error_recovery_patterns(
        self,
        trajectories: list[CompressedTrajectory],
    ) -> list[dict[str, Any]]:
        """Find patterns in how agents recover from errors."""
        patterns = []
        for ct in trajectories:
            if ct.outcome == "failure" and len(ct.tool_patterns) >= 2:
                # Look for tool calls that might represent recovery attempts
                tools = ct.tool_patterns
                for i in range(len(tools) - 1):
                    if tools[i]["success_rate"] < 0.5 and tools[i + 1]["success_rate"] > 0.5:
                        patterns.append({
                            "error_tool": tools[i]["tool"],
                            "recovery_tool": tools[i + 1]["tool"],
                            "frequency": 1,
                            "success_rate": tools[i + 1]["success_rate"],
                            "trajectory_ids": [ct.id],
                        })

        return patterns[:5]

    def get_compressed(self, trajectory_id: str) -> CompressedTrajectory | None:
        """Get a compressed trajectory by ID."""
        return self._compressed.get(trajectory_id)

    def list_compressed(
        self,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[CompressedTrajectory]:
        """List compressed trajectories, optionally filtered by agent."""
        results = list(self._compressed.values())
        if agent_id:
            results = [ct for ct in results if ct.agent_id == agent_id]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    def get_patterns(
        self,
        pattern_type: str | None = None,
    ) -> list[ExecutionPattern]:
        """Get detected patterns, optionally filtered by type."""
        patterns = list(self._patterns.values())
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        return patterns

    def get_stats(self) -> dict[str, Any]:
        """Get compression statistics."""
        return {
            "total_trajectories_compressed": self._stats.total_trajectories_compressed,
            "total_patterns_detected": self._stats.total_patterns_detected,
            "average_compression_ratio": round(self._stats.average_compression_ratio, 2),
            "average_quality_score": round(self._stats.average_quality_score, 2),
            "total_bytes_saved": self._stats.total_bytes_saved,
            "patterns_by_type": self._stats.patterns_by_type,
            "stored_trajectories": len(self._compressed),
            "stored_patterns": len(self._patterns),
        }

    def export_training_data(
        self,
        agent_id: str | None = None,
        format: str = "jsonl",
    ) -> str:
        """Export compressed trajectories as training data.

        Args:
            agent_id: Filter by agent, or None for all
            format: Output format ("jsonl" or "json")

        Returns:
            Formatted training data string
        """
        trajectories = self.list_compressed(agent_id=agent_id, limit=1000)

        if format == "jsonl":
            lines = []
            for ct in trajectories:
                entry = {
                    "messages": [
                        {"role": "system", "content": "You are an AI agent with tool-calling capabilities."},
                        {"role": "user", "content": ct.goal},
                        {"role": "assistant", "content": ct.summary},
                    ],
                    "metadata": {
                        "tool_patterns": ct.tool_patterns,
                        "outcome": ct.outcome,
                        "quality_score": ct.quality_score,
                    },
                }
                lines.append(json.dumps(entry, ensure_ascii=False))
            return "\n".join(lines)

        else:
            entries = []
            for ct in trajectories:
                entries.append({
                    "goal": ct.goal,
                    "outcome": ct.outcome,
                    "summary": ct.summary,
                    "tool_patterns": ct.tool_patterns,
                    "insights": ct.insights,
                })
            return json.dumps(entries, ensure_ascii=False, indent=2)


# Singleton
trajectory_compressor = TrajectoryCompressor()