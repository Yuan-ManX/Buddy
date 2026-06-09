"""Buddy Cost Tracking — per-agent, per-task token and cost accounting

Provides comprehensive cost estimation and tracking across all agent activities,
model routing decisions, task-level attribution, and cumulative reporting.
"""
from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Cost per 1K tokens for common models (in USD)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
}


@dataclass
class TaskCost:
    """Cost breakdown for a single task execution."""
    task_id: str
    agent_id: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    tool_calls: int = 0
    reasoning_steps: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentCostSummary:
    """Aggregated cost summary for an agent."""
    agent_id: str
    total_tasks: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_cost_per_task: float = 0.0
    model_breakdown: dict[str, dict] = field(default_factory=dict)


class CostTracker:
    """Tracks and reports costs across the entire agent system."""

    def __init__(self):
        self._task_costs: dict[str, TaskCost] = {}
        self._agent_summaries: dict[str, AgentCostSummary] = {}
        self._system_total_cost = 0.0
        self._system_total_tokens = 0

    def estimate_cost(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> float:
        """Estimate cost for a model call based on token counts."""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING.get("gpt-4o-mini", {"input": 0.0002, "output": 0.0008}))
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def record_task(
        self,
        task_id: str,
        agent_id: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        tool_calls: int = 0,
        reasoning_steps: int = 0,
    ) -> TaskCost:
        """Record cost for a completed task."""
        total_tokens = input_tokens + output_tokens
        cost = self.estimate_cost(model, input_tokens, output_tokens)

        task_cost = TaskCost(
            task_id=task_id,
            agent_id=agent_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=cost,
            tool_calls=tool_calls,
            reasoning_steps=reasoning_steps,
        )
        self._task_costs[task_id] = task_cost

        # Update agent summary
        if agent_id not in self._agent_summaries:
            self._agent_summaries[agent_id] = AgentCostSummary(agent_id=agent_id)

        summary = self._agent_summaries[agent_id]
        summary.total_tasks += 1
        summary.total_input_tokens += input_tokens
        summary.total_output_tokens += output_tokens
        summary.total_tokens += total_tokens
        summary.total_cost += cost
        summary.avg_cost_per_task = round(summary.total_cost / summary.total_tasks, 6)

        # Model breakdown
        if model not in summary.model_breakdown:
            summary.model_breakdown[model] = {"calls": 0, "tokens": 0, "cost": 0.0}
        summary.model_breakdown[model]["calls"] += 1
        summary.model_breakdown[model]["tokens"] += total_tokens
        summary.model_breakdown[model]["cost"] += cost

        # System totals
        self._system_total_cost += cost
        self._system_total_tokens += total_tokens

        return task_cost

    def get_agent_summary(self, agent_id: str) -> dict:
        """Get cost summary for a specific agent."""
        summary = self._agent_summaries.get(agent_id)
        if not summary:
            return {"agent_id": agent_id, "total_tasks": 0, "total_cost": 0.0}
        return {
            "agent_id": summary.agent_id,
            "total_tasks": summary.total_tasks,
            "total_input_tokens": summary.total_input_tokens,
            "total_output_tokens": summary.total_output_tokens,
            "total_tokens": summary.total_tokens,
            "total_cost": round(summary.total_cost, 6),
            "avg_cost_per_task": summary.avg_cost_per_task,
            "model_breakdown": summary.model_breakdown,
        }

    def get_system_summary(self) -> dict:
        """Get system-wide cost summary."""
        return {
            "total_cost": round(self._system_total_cost, 6),
            "total_tokens": self._system_total_tokens,
            "total_tasks": len(self._task_costs),
            "agent_count": len(self._agent_summaries),
            "agents": [
                {
                    "agent_id": aid,
                    "total_cost": round(s.total_cost, 6),
                    "total_tasks": s.total_tasks,
                    "total_tokens": s.total_tokens,
                }
                for aid, s in self._agent_summaries.items()
            ],
            "estimated_monthly": round(self._system_total_cost * 30, 2) if self._system_total_cost > 0 else 0.0,
        }

    def get_task_cost(self, task_id: str) -> dict | None:
        """Get cost for a specific task."""
        tc = self._task_costs.get(task_id)
        if not tc:
            return None
        return {
            "task_id": tc.task_id,
            "agent_id": tc.agent_id,
            "model": tc.model,
            "input_tokens": tc.input_tokens,
            "output_tokens": tc.output_tokens,
            "total_tokens": tc.total_tokens,
            "estimated_cost": tc.estimated_cost,
            "tool_calls": tc.tool_calls,
            "reasoning_steps": tc.reasoning_steps,
            "created_at": tc.created_at,
        }

    def reset_agent(self, agent_id: str) -> None:
        """Reset cost tracking for an agent."""
        self._agent_summaries.pop(agent_id, None)
        keys_to_remove = [k for k, v in self._task_costs.items() if v.agent_id == agent_id]
        for k in keys_to_remove:
            self._task_costs.pop(k, None)


# Global cost tracker
cost_tracker = CostTracker()