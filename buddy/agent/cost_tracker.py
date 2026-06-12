"""Buddy Token Cost Tracking & Optimization System

Comprehensive cost tracking, budgeting, and optimization for LLM usage
across all agents, tasks, workspaces, and model tiers. Provides real-time
cost visibility, usage projections, budget alerts, and optimization
suggestions driven by actual usage patterns.

Integrates with model_router from agent.shared for tier-aware cost
analysis and model-tier optimization recommendations.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

from agent.routing import model_router, ModelTier

logger = logging.getLogger("buddy.cost_tracker")

# ══════════════════════════════════════════════════════════════════════
# Model Pricing Table  (cost per 1K tokens, USD)
# ══════════════════════════════════════════════════════════════════════

MODEL_PRICING_TABLE: dict[str, dict[str, float]] = {
    # ── OpenAI ───────────────────────────────────────────────────
    "gpt-4o":                {"input": 0.0025,  "output": 0.01,    "tier": "premium"},
    "gpt-4o-mini":           {"input": 0.00015, "output": 0.0006,  "tier": "light"},
    "gpt-4-turbo":           {"input": 0.01,    "output": 0.03,    "tier": "premium"},
    "gpt-4":                 {"input": 0.03,    "output": 0.06,    "tier": "premium"},
    "gpt-4-32k":             {"input": 0.06,    "output": 0.12,    "tier": "premium"},
    "gpt-3.5-turbo":         {"input": 0.0005,  "output": 0.0015,  "tier": "light"},
    "gpt-3.5-turbo-16k":     {"input": 0.003,   "output": 0.004,   "tier": "light"},
    "o1-preview":            {"input": 0.015,   "output": 0.06,    "tier": "premium"},
    "o1-mini":               {"input": 0.003,   "output": 0.012,   "tier": "standard"},
    "o3-mini":               {"input": 0.0011,  "output": 0.0044,  "tier": "standard"},

    # ── Anthropic Claude ─────────────────────────────────────────
    "claude-3-opus":         {"input": 0.015,   "output": 0.075,   "tier": "premium"},
    "claude-3-sonnet":       {"input": 0.003,   "output": 0.015,   "tier": "standard"},
    "claude-3-haiku":        {"input": 0.00025, "output": 0.00125, "tier": "light"},
    "claude-3.5-sonnet":     {"input": 0.003,   "output": 0.015,   "tier": "standard"},
    "claude-3.5-haiku":      {"input": 0.0008,  "output": 0.004,   "tier": "light"},
    "claude-4-opus":         {"input": 0.015,   "output": 0.075,   "tier": "premium"},
    "claude-4-sonnet":       {"input": 0.003,   "output": 0.015,   "tier": "standard"},

    # ── Google Gemini ────────────────────────────────────────────
    "gemini-1.5-pro":        {"input": 0.00125, "output": 0.005,   "tier": "standard"},
    "gemini-1.5-flash":      {"input": 0.000075,"output": 0.0003,  "tier": "light"},
    "gemini-2.0-flash":      {"input": 0.0001,  "output": 0.0004,  "tier": "light"},
    "gemini-2.5-pro":        {"input": 0.00125, "output": 0.01,    "tier": "premium"},

    # ── Open-source / self-hosted (approximate inference cost) ───
    "llama-3-70b":           {"input": 0.00059, "output": 0.00079, "tier": "standard"},
    "llama-3-8b":            {"input": 0.00006, "output": 0.00006, "tier": "light"},
    "mixtral-8x7b":          {"input": 0.00024, "output": 0.00024, "tier": "standard"},
    "deepseek-v3":           {"input": 0.00027, "output": 0.0011,  "tier": "standard"},
    "deepseek-r1":           {"input": 0.00055, "output": 0.00219, "tier": "standard"},

    # ── Via cloud marketplaces (Bedrock / Vertex approximate) ────
    "claude-via-bedrock":    {"input": 0.003,   "output": 0.015,   "tier": "standard"},
}

# ══════════════════════════════════════════════════════════════════════
# Default Budget Thresholds
# ══════════════════════════════════════════════════════════════════════

DEFAULT_DAILY_BUDGET   = 10.0    # USD
DEFAULT_WEEKLY_BUDGET  = 50.0    # USD
DEFAULT_MONTHLY_BUDGET = 200.0   # USD

BUDGET_WARNING_THRESHOLD  = 0.75   # 75 % of budget → warning
BUDGET_CRITICAL_THRESHOLD = 0.90   # 90 % of budget → critical


# ══════════════════════════════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════════════════════════════

@dataclass
class CostEntry:
    """Single cost record for one model invocation."""
    id: str
    agent_id: str
    task_id: Optional[str]
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    timestamp: str
    task_description: str
    workspace_id: Optional[str]


@dataclass
class CostSummary:
    """Aggregated cost summary over a time period or scope."""
    total_cost: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    request_count: int
    model_breakdown: dict[str, dict]
    avg_cost_per_request: float


@dataclass
class OptimizationSuggestion:
    """Actionable recommendation for reducing token costs."""
    type: str               # "model_tier" | "prompt_engineering" | "caching" | "batching" | "routing"
    description: str        # human-readable explanation of the finding
    estimated_savings: float  # estimated monthly savings in USD
    action: str             # concrete step the user can take


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _resolve_model_tier(model_name: str) -> str:
    """Resolve a model name to its tier label.

    Checks the pricing table first, then falls back to heuristics
    and finally to the model_router tier configuration.
    """
    pricing = MODEL_PRICING_TABLE.get(model_name)
    if pricing and "tier" in pricing:
        return pricing["tier"]

    # Heuristic fallback based on naming conventions
    model_lower = model_name.lower()
    if any(kw in model_lower for kw in ("mini", "flash", "haiku", "light", "nano")):
        return "light"
    if any(kw in model_lower for kw in ("opus", "preview", "ultra", "pro")):
        return "premium"

    # Check model_router tiers for a matching model name
    for tier in ModelTier:
        config = model_router.tiers.get(tier)
        if config and config.model == model_name:
            return tier.value

    return "standard"


def _estimate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Compute estimated cost for a model call based on token counts."""
    pricing = MODEL_PRICING_TABLE.get(
        model_name,
        {"input": 0.001, "output": 0.004},  # sensible default fallback
    )
    input_cost = (prompt_tokens / 1000) * pricing["input"]
    output_cost = (completion_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)


# ══════════════════════════════════════════════════════════════════════
# CostTracker
# ══════════════════════════════════════════════════════════════════════

class CostTracker:
    """Comprehensive token cost tracker with projections, budgeting,
    optimization suggestions, and model-tier breakdowns.

    Integrates with the model_router from agent.shared for tier-aware
    cost analysis and optimization recommendations.
    """

    def __init__(
        self,
        daily_budget: float = DEFAULT_DAILY_BUDGET,
        weekly_budget: float = DEFAULT_WEEKLY_BUDGET,
        monthly_budget: float = DEFAULT_MONTHLY_BUDGET,
    ):
        self._entries: dict[str, CostEntry] = {}
        self._daily_budget = daily_budget
        self._weekly_budget = weekly_budget
        self._monthly_budget = monthly_budget

    # ── Budget configuration ─────────────────────────────────────
    def set_budgets(
        self,
        daily: Optional[float] = None,
        weekly: Optional[float] = None,
        monthly: Optional[float] = None,
    ) -> None:
        """Update one or more budget thresholds."""
        if daily is not None:
            self._daily_budget = daily
        if weekly is not None:
            self._weekly_budget = weekly
        if monthly is not None:
            self._monthly_budget = monthly

    # ── Core recording ───────────────────────────────────────────
    def record_usage(
        self,
        agent_id: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        task_id: Optional[str] = None,
        description: str = "",
        workspace_id: Optional[str] = None,
    ) -> CostEntry:
        """Record a model usage event and return the created CostEntry.

        Automatically computes total_tokens and estimated_cost, assigns
        a unique ID, and timestamps the entry. Budget alerts are checked
        after each recording.
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = _estimate_cost(model_name, prompt_tokens, completion_tokens)
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        entry = CostEntry(
            id=entry_id,
            agent_id=agent_id,
            task_id=task_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=cost,
            timestamp=now.isoformat(),
            task_description=description,
            workspace_id=workspace_id,
        )
        self._entries[entry_id] = entry

        self._check_budget_alerts()
        return entry

    # ── Internal query helpers ───────────────────────────────────
    def _entries_in_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[CostEntry]:
        """Return entries whose timestamp falls within [start_date, end_date]."""
        result: list[CostEntry] = []
        for entry in self._entries.values():
            ts = datetime.fromisoformat(entry.timestamp)
            if start_date is not None and ts < start_date:
                continue
            if end_date is not None and ts > end_date:
                continue
            result.append(entry)
        return result

    def _build_summary(self, entries: list[CostEntry]) -> CostSummary:
        """Aggregate a list of entries into a CostSummary."""
        if not entries:
            return CostSummary(
                total_cost=0.0,
                total_tokens=0,
                prompt_tokens=0,
                completion_tokens=0,
                request_count=0,
                model_breakdown={},
                avg_cost_per_request=0.0,
            )

        total_cost = 0.0
        total_tokens = 0
        total_prompt = 0
        total_completion = 0
        model_map: dict[str, dict] = defaultdict(
            lambda: {"calls": 0, "tokens": 0, "cost": 0.0, "tier": ""}
        )

        for e in entries:
            total_cost += e.estimated_cost
            total_tokens += e.total_tokens
            total_prompt += e.prompt_tokens
            total_completion += e.completion_tokens

            mb = model_map[e.model_name]
            mb["calls"] += 1
            mb["tokens"] += e.total_tokens
            mb["cost"] += e.estimated_cost
            if not mb["tier"]:
                mb["tier"] = _resolve_model_tier(e.model_name)

        # Round costs in the breakdown
        for m in model_map.values():
            m["cost"] = round(m["cost"], 6)

        count = len(entries)
        return CostSummary(
            total_cost=round(total_cost, 6),
            total_tokens=total_tokens,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            request_count=count,
            model_breakdown=dict(model_map),
            avg_cost_per_request=round(total_cost / count, 6),
        )

    # ── Public query methods ─────────────────────────────────────

    def get_agent_costs(
        self,
        agent_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CostSummary:
        """Get aggregated cost summary for a specific agent."""
        entries = [
            e for e in self._entries_in_range(start_date, end_date)
            if e.agent_id == agent_id
        ]
        return self._build_summary(entries)

    def get_task_costs(self, task_id: str) -> CostSummary:
        """Get aggregated cost summary for a specific task."""
        entries = [e for e in self._entries.values() if e.task_id == task_id]
        return self._build_summary(entries)

    def get_daily_costs(self, date: Optional[datetime] = None) -> CostSummary:
        """Get cost summary for a specific day (defaults to today in UTC)."""
        target = date or datetime.now(timezone.utc)
        start = target.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return self._build_summary(self._entries_in_range(start, end))

    def get_workspace_costs(self, workspace_id: str) -> CostSummary:
        """Get aggregated cost summary for a workspace."""
        entries = [e for e in self._entries.values() if e.workspace_id == workspace_id]
        return self._build_summary(entries)

    # ── Cost breakdown by period ─────────────────────────────────
    def get_cost_breakdown(self, period: str = "daily") -> dict:
        """Return cost breakdown bucketed by period.

        Args:
            period: One of ``"daily"``, ``"weekly"``, or ``"monthly"``.

        Returns:
            Dict mapping period keys (e.g. ``"2026-06-11"``) to
            summary dicts with keys: total_cost, total_tokens,
            prompt_tokens, completion_tokens, request_count,
            avg_cost_per_request.
        """
        if not self._entries:
            return {}

        buckets: dict[str, list[CostEntry]] = defaultdict(list)

        for entry in self._entries.values():
            ts = datetime.fromisoformat(entry.timestamp)
            if period == "daily":
                key = ts.strftime("%Y-%m-%d")
            elif period == "weekly":
                key = ts.strftime("%Y-W%W")  # ISO year-week
            elif period == "monthly":
                key = ts.strftime("%Y-%m")
            else:
                key = ts.strftime("%Y-%m-%d")  # fallback to daily

            buckets[key].append(entry)

        return {
            key: {
                "total_cost": round(sum(e.estimated_cost for e in entries), 6),
                "total_tokens": sum(e.total_tokens for e in entries),
                "prompt_tokens": sum(e.prompt_tokens for e in entries),
                "completion_tokens": sum(e.completion_tokens for e in entries),
                "request_count": len(entries),
                "avg_cost_per_request": (
                    round(sum(e.estimated_cost for e in entries) / len(entries), 6)
                    if entries else 0.0
                ),
            }
            for key, entries in sorted(buckets.items())
        }

    # ── Cost projections ─────────────────────────────────────────
    def project_costs(self, days: int = 30) -> dict:
        """Project future costs based on recent usage patterns.

        Uses the average daily cost from the last 7 days of activity
        to project costs over the specified number of days.
        """
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        recent = self._entries_in_range(seven_days_ago, now)
        if not recent:
            return {
                "projected_cost": 0.0,
                "projection_days": days,
                "avg_daily_cost": 0.0,
                "confidence": "low",
                "note": "Insufficient data for projection — no entries in the last 7 days.",
            }

        # Group by day to get per-day spend
        daily_costs: dict[str, float] = defaultdict(float)
        for e in recent:
            day_key = datetime.fromisoformat(e.timestamp).strftime("%Y-%m-%d")
            daily_costs[day_key] += e.estimated_cost

        active_days = len(daily_costs)
        total_recent = sum(daily_costs.values())
        avg_daily = total_recent / max(active_days, 1)

        if active_days >= 5:
            confidence = "high"
        elif active_days >= 3:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "projected_cost": round(avg_daily * days, 2),
            "projection_days": days,
            "avg_daily_cost": round(avg_daily, 6),
            "recent_total": round(total_recent, 6),
            "active_days": active_days,
            "confidence": confidence,
        }

    # ── Budget alerting ──────────────────────────────────────────
    def _check_budget_alerts(self) -> list[dict]:
        """Check current spending against budgets and return active alerts."""
        now = datetime.now(timezone.utc)
        alerts: list[dict] = []

        # ── Daily ──
        daily = self.get_daily_costs(now)
        if self._daily_budget > 0:
            ratio = daily.total_cost / self._daily_budget
            alert = self._build_alert("daily", daily.total_cost, self._daily_budget, ratio)
            if alert:
                alerts.append(alert)

        # ── Weekly ──
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        weekly = self._build_summary(self._entries_in_range(week_start, now + timedelta(days=1)))
        if self._weekly_budget > 0:
            ratio = weekly.total_cost / self._weekly_budget
            alert = self._build_alert("weekly", weekly.total_cost, self._weekly_budget, ratio)
            if alert:
                alerts.append(alert)

        # ── Monthly ──
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly = self._build_summary(self._entries_in_range(month_start, now + timedelta(days=1)))
        if self._monthly_budget > 0:
            ratio = monthly.total_cost / self._monthly_budget
            alert = self._build_alert("monthly", monthly.total_cost, self._monthly_budget, ratio)
            if alert:
                alerts.append(alert)

        for alert in alerts:
            logger.warning("Budget alert [%s]: %s", alert["level"], alert["message"])

        return alerts

    @staticmethod
    def _build_alert(period: str, current: float, budget: float, ratio: float) -> Optional[dict]:
        """Build a single budget alert dict if threshold is exceeded."""
        if ratio >= BUDGET_CRITICAL_THRESHOLD:
            return {
                "level": "critical",
                "period": period,
                "current_cost": current,
                "budget": budget,
                "usage_pct": round(ratio * 100, 1),
                "message": (
                    f"{period.capitalize()} spending at {ratio * 100:.1f}% "
                    f"of ${budget:.2f} budget"
                ),
            }
        if ratio >= BUDGET_WARNING_THRESHOLD:
            return {
                "level": "warning",
                "period": period,
                "current_cost": current,
                "budget": budget,
                "usage_pct": round(ratio * 100, 1),
                "message": (
                    f"{period.capitalize()} spending at {ratio * 100:.1f}% "
                    f"of ${budget:.2f} budget"
                ),
            }
        return None

    def get_budget_status(self) -> dict:
        """Return current budget status across all periods with alerts."""
        now = datetime.now(timezone.utc)

        daily = self.get_daily_costs(now)

        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        weekly = self._build_summary(self._entries_in_range(week_start, now + timedelta(days=1)))

        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly = self._build_summary(self._entries_in_range(month_start, now + timedelta(days=1)))

        return {
            "daily": {
                "spent": daily.total_cost,
                "budget": self._daily_budget,
                "remaining": round(self._daily_budget - daily.total_cost, 6),
                "usage_pct": (
                    round(daily.total_cost / self._daily_budget * 100, 1)
                    if self._daily_budget > 0 else 0.0
                ),
            },
            "weekly": {
                "spent": weekly.total_cost,
                "budget": self._weekly_budget,
                "remaining": round(self._weekly_budget - weekly.total_cost, 6),
                "usage_pct": (
                    round(weekly.total_cost / self._weekly_budget * 100, 1)
                    if self._weekly_budget > 0 else 0.0
                ),
            },
            "monthly": {
                "spent": monthly.total_cost,
                "budget": self._monthly_budget,
                "remaining": round(self._monthly_budget - monthly.total_cost, 6),
                "usage_pct": (
                    round(monthly.total_cost / self._monthly_budget * 100, 1)
                    if self._monthly_budget > 0 else 0.0
                ),
            },
            "alerts": self._check_budget_alerts(),
        }

    # ── Cost per model tier ──────────────────────────────────────
    def get_cost_by_tier(self) -> dict[str, CostSummary]:
        """Break down costs by model tier (light / standard / premium).

        Integrates with model_router tier configuration for accurate
        tier assignment of routed models.
        """
        tier_entries: dict[str, list[CostEntry]] = defaultdict(list)

        for entry in self._entries.values():
            tier = _resolve_model_tier(entry.model_name)
            tier_entries[tier].append(entry)

        return {
            tier: self._build_summary(entries)
            for tier, entries in sorted(tier_entries.items())
        }

    # ── Optimization suggestions ─────────────────────────────────
    def get_optimization_suggestions(self) -> list[OptimizationSuggestion]:
        """Analyze usage patterns and return actionable cost-optimization
        suggestions.

        Checks for:
        - Overuse of premium-tier models for simple tasks
        - Opportunities to use lighter models via tier routing
        - High prompt-to-completion ratios suggesting prompt bloat
        - Repeated use of the same model (caching opportunity)
        """
        suggestions: list[OptimizationSuggestion] = []

        entries = list(self._entries.values())
        if not entries:
            return suggestions

        total_cost = sum(e.estimated_cost for e in entries)
        if total_cost == 0:
            return suggestions

        # ── Premium-tier overuse ──
        tier_costs = self.get_cost_by_tier()
        premium = tier_costs.get("premium")
        if premium and premium.total_cost > 0:
            premium_pct = premium.total_cost / total_cost
            if premium_pct > 0.6:
                suggestions.append(OptimizationSuggestion(
                    type="model_tier",
                    description=(
                        f"Premium-tier models account for {premium_pct * 100:.0f}% "
                        f"of costs. Consider routing non-expert tasks to standard "
                        f"or light models."
                    ),
                    estimated_savings=round(premium.total_cost * 0.5, 2),
                    action=(
                        "Adjust model_router complexity thresholds so moderate "
                        "tasks default to the standard tier."
                    ),
                ))

        # ── Prompt bloat detection ──
        total_prompt = sum(e.prompt_tokens for e in entries)
        total_completion = sum(e.completion_tokens for e in entries)
        if total_completion > 0 and (total_prompt / total_completion) > 20:
            suggestions.append(OptimizationSuggestion(
                type="prompt_engineering",
                description=(
                    f"High prompt-to-completion ratio "
                    f"({total_prompt / total_completion:.1f}:1). "
                    f"Large prompts relative to output suggest potential bloat."
                ),
                estimated_savings=round(total_cost * 0.15, 2),
                action=(
                    "Review system prompts for conciseness. Use context "
                    "compression for long conversations."
                ),
            ))

        # ── Light-model under-utilization ──
        light = tier_costs.get("light")
        light_pct = (light.total_cost / total_cost) if (light and light.total_cost > 0) else 0.0
        if light_pct < 0.1 and len(entries) > 20:
            suggestions.append(OptimizationSuggestion(
                type="routing",
                description=(
                    f"Light-tier models account for only {light_pct * 100:.0f}% "
                    f"of usage. Many simple queries may be over-routed to more "
                    f"expensive models."
                ),
                estimated_savings=round(total_cost * 0.2, 2),
                action=(
                    "Enable model_router's fast-analysis path for simple queries "
                    "to increase light-tier usage."
                ),
            ))

        # ── Caching opportunity ──
        model_counts: dict[str, int] = defaultdict(int)
        for e in entries:
            model_counts[e.model_name] += 1
        if len(entries) > 50:
            dominant_model = max(model_counts, key=model_counts.get)
            dominant_pct = model_counts[dominant_model] / len(entries)
            if dominant_pct > 0.5:
                suggestions.append(OptimizationSuggestion(
                    type="caching",
                    description=(
                        f"Model '{dominant_model}' used for "
                        f"{model_counts[dominant_model]} calls "
                        f"({dominant_pct * 100:.0f}%). Consider enabling "
                        f"semantic cache for repeated similar queries."
                    ),
                    estimated_savings=round(total_cost * 0.1, 2),
                    action=(
                        "Enable semantic_cache from agent.shared for repeated "
                        "query patterns."
                    ),
                ))

        return suggestions

    # ── Full system overview ─────────────────────────────────────
    def get_system_overview(self) -> dict:
        """Return a comprehensive system-wide cost overview."""
        if not self._entries:
            return {
                "total_cost": 0.0,
                "total_tokens": 0,
                "total_entries": 0,
                "unique_agents": 0,
                "unique_models": [],
                "unique_workspaces": 0,
                "tier_breakdown": {},
                "budget_status": self.get_budget_status(),
                "projection": self.project_costs(30),
            }

        all_entries = list(self._entries.values())
        total_cost = sum(e.estimated_cost for e in all_entries)
        total_tokens = sum(e.total_tokens for e in all_entries)

        agents = {e.agent_id for e in all_entries}
        models = sorted({e.model_name for e in all_entries})
        workspaces = {e.workspace_id for e in all_entries if e.workspace_id}

        return {
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "total_entries": len(all_entries),
            "unique_agents": len(agents),
            "unique_models": models,
            "unique_workspaces": len(workspaces),
            "tier_breakdown": {
                tier: {
                    "cost": s.total_cost,
                    "tokens": s.total_tokens,
                    "requests": s.request_count,
                }
                for tier, s in self.get_cost_by_tier().items()
            },
            "budget_status": self.get_budget_status(),
            "projection": self.project_costs(30),
        }

    # ── Data management ──────────────────────────────────────────
    def get_all_entries(self) -> list[CostEntry]:
        """Return all recorded cost entries."""
        return list(self._entries.values())

    def get_entry(self, entry_id: str) -> Optional[CostEntry]:
        """Retrieve a single cost entry by ID."""
        return self._entries.get(entry_id)

    def clear_entries(self) -> None:
        """Remove all recorded entries (use with caution)."""
        self._entries.clear()
        logger.info("All cost entries cleared.")


# ── Global singleton ─────────────────────────────────────────────────
cost_tracker = CostTracker()