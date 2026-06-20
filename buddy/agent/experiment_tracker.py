"""
Experiment Tracker - A/B Testing and Configuration Optimization for Buddy.

The Experiment Tracker enables systematic testing of different agent
configurations, prompt strategies, and execution paths. It tracks
experiments, measures outcomes, and identifies optimal configurations
through controlled comparison.

Core capabilities:
- Experiment definition with control and treatment groups
- Metric tracking with statistical analysis
- Configuration versioning and comparison
- Prompt strategy A/B testing
- Execution path optimization
- Results visualization and reporting
"""

import uuid
import time
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.experiment_tracker")


class ExperimentStatus(str, Enum):
    """Status of an experiment."""
    DRAFT = "draft"              # Being defined
    RUNNING = "running"          # Actively collecting data
    PAUSED = "paused"            # Temporarily stopped
    COMPLETED = "completed"      # Finished collecting data
    ANALYZED = "analyzed"        # Results have been analyzed
    ARCHIVED = "archived"        # Stored for reference


class ExperimentType(str, Enum):
    """Types of experiments."""
    PROMPT_AB = "prompt_ab"              # Compare different prompts
    CONFIG_AB = "config_ab"              # Compare different configurations
    MODEL_AB = "model_ab"                # Compare different models
    STRATEGY_AB = "strategy_ab"          # Compare different strategies
    TOOL_AB = "tool_ab"                  # Compare different tool selections
    MULTI_VARIANT = "multi_variant"      # Test multiple variants simultaneously


class MetricType(str, Enum):
    """Types of metrics to track."""
    SUCCESS_RATE = "success_rate"        # Task success rate
    RESPONSE_TIME = "response_time"      # Response latency
    TOKEN_USAGE = "token_usage"          # Token consumption
    COST = "cost"                        # Monetary cost
    QUALITY_SCORE = "quality_score"      # Output quality
    USER_SATISFACTION = "user_satisfaction"  # User feedback
    ERROR_RATE = "error_rate"            # Error frequency
    COMPLETION_RATE = "completion_rate"   # Task completion rate


@dataclass
class ExperimentVariant:
    """A single variant in an experiment."""
    variant_id: str
    name: str
    description: str
    configuration: dict[str, Any]
    is_control: bool = False
    traffic_allocation: float = 0.5      # Fraction of traffic to this variant


@dataclass
class TrialResult:
    """Result of a single trial in an experiment."""
    trial_id: str
    experiment_id: str
    variant_id: str
    metrics: dict[str, float]            # Metric name -> value
    context: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "trial_id": self.trial_id,
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "metrics": self.metrics,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Experiment:
    """A complete experiment definition with results."""
    experiment_id: str
    name: str
    description: str
    experiment_type: ExperimentType
    variants: list[ExperimentVariant]
    metrics: list[MetricType]
    status: ExperimentStatus = ExperimentStatus.DRAFT
    trials: list[TrialResult] = field(default_factory=list)
    minimum_trials: int = 30
    confidence_level: float = 0.95
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    winner_variant_id: str | None = None
    analysis: dict[str, Any] = field(default_factory=dict)

    def add_trial(self, trial: TrialResult) -> None:
        """Add a trial result to the experiment."""
        self.trials.append(trial)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "experiment_type": self.experiment_type.value,
            "variants": [v.__dict__ for v in self.variants],
            "metrics": [m.value for m in self.metrics],
            "status": self.status.value,
            "trial_count": len(self.trials),
            "minimum_trials": self.minimum_trials,
            "confidence_level": self.confidence_level,
            "winner_variant_id": self.winner_variant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ExperimentTracker:
    """Systematic experiment tracking for Buddy agent optimization.

    Enables controlled testing of different agent configurations,
    prompt strategies, and execution paths with statistical analysis
    to identify optimal configurations through data-driven comparison.
    """

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}
        self._total_experiments = 0
        self._total_trials = 0

    # ── Experiment Management ───────────────────────────────────────

    def create_experiment(
        self,
        name: str,
        description: str,
        experiment_type: ExperimentType,
        variants: list[dict],
        metrics: list[MetricType],
        minimum_trials: int = 30,
        confidence_level: float = 0.95,
    ) -> Experiment:
        """Create a new experiment."""
        experiment_id = f"exp-{uuid.uuid4().hex[:12]}"

        experiment_variants = []
        total_allocation = 0.0
        for i, v in enumerate(variants):
            var = ExperimentVariant(
                variant_id=f"var-{uuid.uuid4().hex[:8]}",
                name=v["name"],
                description=v.get("description", ""),
                configuration=v.get("configuration", {}),
                is_control=v.get("is_control", i == 0),
                traffic_allocation=v.get("traffic_allocation", 1.0 / len(variants)),
            )
            experiment_variants.append(var)
            total_allocation += var.traffic_allocation

        # Normalize traffic allocations
        if total_allocation > 0:
            for var in experiment_variants:
                var.traffic_allocation /= total_allocation

        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            experiment_type=experiment_type,
            variants=experiment_variants,
            metrics=metrics,
            minimum_trials=minimum_trials,
            confidence_level=confidence_level,
        )
        self._experiments[experiment_id] = experiment
        self._total_experiments += 1

        return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment (begin collecting trials)."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        exp.status = ExperimentStatus.RUNNING
        return True

    def pause_experiment(self, experiment_id: str) -> bool:
        """Pause an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        exp.status = ExperimentStatus.PAUSED
        return True

    def complete_experiment(self, experiment_id: str) -> bool:
        """Complete an experiment and run analysis."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False

        exp.status = ExperimentStatus.COMPLETED
        self._analyze_experiment(experiment_id)
        return True

    # ── Trial Recording ─────────────────────────────────────────────

    def record_trial(
        self,
        experiment_id: str,
        variant_id: str,
        metrics: dict[str, float],
        context: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> TrialResult | None:
        """Record a trial result for an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        if exp.status != ExperimentStatus.RUNNING:
            return None

        # Verify variant exists
        variant_exists = any(v.variant_id == variant_id for v in exp.variants)
        if not variant_exists:
            return None

        trial_id = f"trial-{uuid.uuid4().hex[:12]}"
        trial = TrialResult(
            trial_id=trial_id,
            experiment_id=experiment_id,
            variant_id=variant_id,
            metrics=metrics,
            context=context or {},
            success=success,
            error_message=error_message,
        )
        exp.add_trial(trial)
        self._total_trials += 1

        # Auto-complete if minimum trials reached
        if len(exp.trials) >= exp.minimum_trials:
            exp.status = ExperimentStatus.COMPLETED
            self._analyze_experiment(experiment_id)

        return trial

    # ── Analysis ────────────────────────────────────────────────────

    def _analyze_experiment(self, experiment_id: str) -> dict:
        """Analyze experiment results to determine winner."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {}

        analysis: dict[str, Any] = {
            "experiment_id": experiment_id,
            "total_trials": len(exp.trials),
            "variant_results": {},
        }

        # Analyze each metric
        for metric in exp.metrics:
            metric_name = metric.value
            variant_scores: dict[str, list[float]] = {}

            for trial in exp.trials:
                if metric_name in trial.metrics:
                    if trial.variant_id not in variant_scores:
                        variant_scores[trial.variant_id] = []
                    variant_scores[trial.variant_id].append(trial.metrics[metric_name])

            # Calculate statistics per variant
            variant_stats = {}
            for var_id, scores in variant_scores.items():
                if len(scores) >= 2:
                    variant_stats[var_id] = {
                        "mean": statistics.mean(scores),
                        "median": statistics.median(scores),
                        "stdev": statistics.stdev(scores) if len(scores) > 1 else 0,
                        "min": min(scores),
                        "max": max(scores),
                        "count": len(scores),
                    }
                else:
                    variant_stats[var_id] = {
                        "mean": scores[0] if scores else 0,
                        "count": len(scores),
                    }

            analysis["variant_results"][metric_name] = variant_stats

        # Determine winner based on primary metric (first in list)
        primary_metric = exp.metrics[0].value
        best_score = -float("inf")
        best_variant = None

        for var_id, stats in analysis["variant_results"].get(primary_metric, {}).items():
            if stats.get("mean", 0) > best_score:
                best_score = stats["mean"]
                best_variant = var_id

        exp.winner_variant_id = best_variant
        exp.analysis = analysis
        exp.status = ExperimentStatus.ANALYZED

        return analysis

    def get_analysis(self, experiment_id: str) -> dict:
        """Get the analysis results for an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {}
        return exp.analysis

    # ── Prompt A/B Testing ──────────────────────────────────────────

    def create_prompt_ab_test(
        self,
        name: str,
        description: str,
        control_prompt: str,
        treatment_prompt: str,
        task_description: str,
    ) -> Experiment:
        """Create a prompt A/B test experiment."""
        return self.create_experiment(
            name=name,
            description=description,
            experiment_type=ExperimentType.PROMPT_AB,
            variants=[
                {
                    "name": "Control",
                    "description": "Original prompt",
                    "configuration": {"prompt": control_prompt, "task": task_description},
                    "is_control": True,
                    "traffic_allocation": 0.5,
                },
                {
                    "name": "Treatment",
                    "description": "New prompt",
                    "configuration": {"prompt": treatment_prompt, "task": task_description},
                    "is_control": False,
                    "traffic_allocation": 0.5,
                },
            ],
            metrics=[
                MetricType.SUCCESS_RATE,
                MetricType.QUALITY_SCORE,
                MetricType.TOKEN_USAGE,
            ],
            minimum_trials=30,
        )

    def create_config_ab_test(
        self,
        name: str,
        description: str,
        control_config: dict,
        treatment_config: dict,
    ) -> Experiment:
        """Create a configuration A/B test experiment."""
        return self.create_experiment(
            name=name,
            description=description,
            experiment_type=ExperimentType.CONFIG_AB,
            variants=[
                {
                    "name": "Control",
                    "description": "Current configuration",
                    "configuration": control_config,
                    "is_control": True,
                    "traffic_allocation": 0.5,
                },
                {
                    "name": "Treatment",
                    "description": "New configuration",
                    "configuration": treatment_config,
                    "is_control": False,
                    "traffic_allocation": 0.5,
                },
            ],
            metrics=[
                MetricType.SUCCESS_RATE,
                MetricType.RESPONSE_TIME,
                MetricType.COST,
            ],
            minimum_trials=20,
        )

    # ── Query Methods ───────────────────────────────────────────────

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Get an experiment by ID."""
        return self._experiments.get(experiment_id)

    def list_experiments(
        self,
        status: ExperimentStatus | None = None,
        experiment_type: ExperimentType | None = None,
    ) -> list[Experiment]:
        """List experiments with optional filters."""
        results = list(self._experiments.values())

        if status:
            results = [e for e in results if e.status == status]
        if experiment_type:
            results = [e for e in results if e.experiment_type == experiment_type]

        results.sort(key=lambda e: e.created_at, reverse=True)
        return results

    def get_trials(
        self, experiment_id: str, variant_id: str | None = None, limit: int = 100
    ) -> list[TrialResult]:
        """Get trials for an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return []

        trials = exp.trials
        if variant_id:
            trials = [t for t in trials if t.variant_id == variant_id]

        trials.sort(key=lambda t: t.created_at, reverse=True)
        return trials[:limit]

    def get_stats(self) -> dict:
        """Get experiment tracker statistics."""
        status_counts = {}
        for exp in self._experiments.values():
            s = exp.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        type_counts = {}
        for exp in self._experiments.values():
            t = exp.experiment_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_experiments": self._total_experiments,
            "total_trials": self._total_trials,
            "active_experiments": len([
                e for e in self._experiments.values()
                if e.status == ExperimentStatus.RUNNING
            ]),
            "completed_experiments": len([
                e for e in self._experiments.values()
                if e.status in (ExperimentStatus.ANALYZED,)
            ]),
            "by_status": status_counts,
            "by_type": type_counts,
            "experiments_with_winners": len([
                e for e in self._experiments.values()
                if e.winner_variant_id
            ]),
        }


# Singleton instance
experiment_tracker = ExperimentTracker()