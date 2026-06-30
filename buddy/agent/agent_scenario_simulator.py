"""Agent Scenario Simulator - Monte Carlo scenario simulation engine for the Buddy AI agent platform.

Allows the agent to project possible futures by running stochastic simulations of action
sequences. Supports deterministic, stochastic, and adversarial scenario types with Monte
Carlo sampling. For each scenario, the simulator performs `num_simulations` independent
runs, sampling initial variable values from their configured distributions and executing
the configured actions up to `max_steps` times per run. Outcomes are classified and
aggregated into a report containing success rates, average cost/duration, variable
statistics, and the best/worst outcomes observed.

All public state mutations are guarded by a threading.Lock to ensure thread safety when
the simulator is shared across agent threads.
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class ScenarioType(str, Enum):
    """Types of scenarios supported by the simulator."""
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"
    ADVERSARIAL = "adversarial"
    MONTE_CARLO = "monte_carlo"


class SimulationStatus(str, Enum):
    """Lifecycle states of a scenario simulation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutcomeType(str, Enum):
    """Possible outcomes for a single simulation run."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


class VariableType(str, Enum):
    """Types of variables that can be modeled in a scenario."""
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    CATEGORICAL = "categorical"
    BINARY = "binary"


class DistributionType(str, Enum):
    """Probability distributions used for sampling variable values."""
    UNIFORM = "uniform"
    NORMAL = "normal"
    TRIANGULAR = "triangular"
    EXPONENTIAL = "exponential"
    CATEGORICAL = "categorical"


# ═══════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════

@dataclass
class ScenarioVariable:
    """A stochastic variable in a scenario, sampled from a configured distribution.

    The variable's `current_value` is populated during simulation runs and reflects
    the most recent sample drawn from `distribution`.
    """
    variable_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    variable_type: VariableType = VariableType.CONTINUOUS
    distribution: DistributionType = DistributionType.UNIFORM
    min_value: float | None = None
    max_value: float | None = None
    mean: float | None = None
    std: float | None = None
    categories: list[str] = field(default_factory=list)
    current_value: Any = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "name": self.name,
            "description": self.description,
            "variable_type": self.variable_type.value,
            "distribution": self.distribution.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean": self.mean,
            "std": self.std,
            "categories": list(self.categories),
            "current_value": self.current_value,
            "created_at": self.created_at,
        }


@dataclass
class ScenarioAction:
    """An action executable within a scenario, with preconditions and probabilistic effects.

    Effects map variable names to numeric deltas that are added to the current state when
    the action succeeds. `probability` controls the success chance sampled per execution.
    """
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    preconditions: list[str] = field(default_factory=list)
    effects: dict[str, float] = field(default_factory=dict)
    probability: float = 1.0
    cost: float = 0.0
    duration: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "preconditions": list(self.preconditions),
            "effects": dict(self.effects),
            "probability": self.probability,
            "cost": self.cost,
            "duration": self.duration,
            "created_at": self.created_at,
        }


@dataclass
class Scenario:
    """A simulation scenario containing variables, actions, and run configuration."""
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    scenario_type: ScenarioType = ScenarioType.MONTE_CARLO
    variables: dict[str, ScenarioVariable] = field(default_factory=dict)
    actions: list[ScenarioAction] = field(default_factory=list)
    max_steps: int = 20
    num_simulations: int = 100
    seed: int | None = None
    status: SimulationStatus = SimulationStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type.value,
            "variables": {k: v.to_dict() for k, v in self.variables.items()},
            "actions": [a.to_dict() for a in self.actions],
            "max_steps": self.max_steps,
            "num_simulations": self.num_simulations,
            "seed": self.seed,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SimulationOutcome:
    """The outcome of a single Monte Carlo simulation run."""
    outcome_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario_id: str = ""
    run_index: int = 0
    outcome_type: OutcomeType = OutcomeType.SUCCESS
    final_state: dict[str, Any] = field(default_factory=dict)
    total_cost: float = 0.0
    total_duration: float = 0.0
    steps_taken: int = 0
    action_history: list[str] = field(default_factory=list)
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "scenario_id": self.scenario_id,
            "run_index": self.run_index,
            "outcome_type": self.outcome_type.value,
            "final_state": dict(self.final_state),
            "total_cost": self.total_cost,
            "total_duration": self.total_duration,
            "steps_taken": self.steps_taken,
            "action_history": list(self.action_history),
            "score": self.score,
            "timestamp": self.timestamp,
        }


@dataclass
class SimulationReport:
    """Aggregated report across all Monte Carlo runs of a scenario."""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario_id: str = ""
    total_runs: int = 0
    completed_runs: int = 0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    avg_cost: float = 0.0
    avg_duration: float = 0.0
    avg_score: float = 0.0
    outcome_distribution: dict[str, int] = field(default_factory=dict)
    variable_stats: dict[str, dict[str, float]] = field(default_factory=dict)
    best_outcome: SimulationOutcome | None = None
    worst_outcome: SimulationOutcome | None = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "scenario_id": self.scenario_id,
            "total_runs": self.total_runs,
            "completed_runs": self.completed_runs,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "avg_cost": self.avg_cost,
            "avg_duration": self.avg_duration,
            "avg_score": self.avg_score,
            "outcome_distribution": dict(self.outcome_distribution),
            "variable_stats": {k: dict(v) for k, v in self.variable_stats.items()},
            "best_outcome": self.best_outcome.to_dict() if self.best_outcome else None,
            "worst_outcome": self.worst_outcome.to_dict() if self.worst_outcome else None,
            "created_at": self.created_at,
        }


@dataclass
class SimulatorStats:
    """Aggregate usage statistics for the entire simulator."""
    total_scenarios: int = 0
    total_simulations: int = 0
    total_successful: int = 0
    total_failed: int = 0
    avg_success_rate: float = 0.0
    avg_simulation_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_scenarios": self.total_scenarios,
            "total_simulations": self.total_simulations,
            "total_successful": self.total_successful,
            "total_failed": self.total_failed,
            "avg_success_rate": self.avg_success_rate,
            "avg_simulation_time": self.avg_simulation_time,
        }


# ═══════════════════════════════════════════════════════════
# Main Simulator Class
# ═══════════════════════════════════════════════════════════

class AgentScenarioSimulator:
    """Monte Carlo scenario simulation engine for projecting possible agent futures.

    Runs stochastic simulations of action sequences across deterministic, stochastic,
    and adversarial scenarios. Each scenario defines a set of random variables and a
    sequence of actions with preconditions, probabilistic effects, costs, and durations.

    The simulator performs `num_simulations` Monte Carlo runs per scenario, sampling
    initial variable values from their configured distributions and executing actions
    up to `max_steps` times per run. Outcomes are classified and aggregated into a
    report with success rates, cost/duration averages, and variable statistics.

    All state mutations are guarded by a threading.Lock to ensure thread safety when
    the simulator is shared across agent threads.
    """

    MAX_OUTCOMES_PER_SCENARIO: int = 10000
    MAX_SCENARIOS: int = 1000

    # Cost threshold below which a full-success run is classified as SUCCESS rather
    # than PARTIAL_SUCCESS. Tuned for typical small-cost scenarios.
    SUCCESS_COST_THRESHOLD: float = 100.0

    def __init__(self) -> None:
        self._scenarios: dict[str, Scenario] = {}
        self._outcomes: dict[str, list[SimulationOutcome]] = {}
        self._reports: dict[str, SimulationReport] = {}
        self._lock = threading.Lock()
        # Aggregate stats tracking across all simulations.
        self._total_simulations: int = 0
        self._total_successful: int = 0
        self._total_failed: int = 0
        self._total_simulation_time: float = 0.0

    # ── Scenario management ────────────────────────────────

    def create_scenario(
        self,
        name: str,
        description: str,
        scenario_type: ScenarioType,
        max_steps: int = 20,
        num_simulations: int = 100,
        seed: int | None = None,
    ) -> Scenario:
        """Create and register a new scenario.

        Raises ValueError if max_steps or num_simulations are non-positive.
        """
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        if num_simulations <= 0:
            raise ValueError("num_simulations must be positive")

        with self._lock:
            # Evict the oldest scenario if we are at capacity.
            if len(self._scenarios) >= self.MAX_SCENARIOS:
                oldest_id = min(
                    self._scenarios.keys(),
                    key=lambda sid: self._scenarios[sid].created_at,
                )
                self._scenarios.pop(oldest_id, None)
                self._outcomes.pop(oldest_id, None)
                self._reports.pop(oldest_id, None)

            scenario = Scenario(
                name=name,
                description=description,
                scenario_type=scenario_type,
                max_steps=max_steps,
                num_simulations=num_simulations,
                seed=seed,
            )
            self._scenarios[scenario.scenario_id] = scenario
            self._outcomes[scenario.scenario_id] = []
            return scenario

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        """Retrieve a scenario by id, or None if not found."""
        with self._lock:
            return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> list[Scenario]:
        """List all registered scenarios as a fresh list."""
        with self._lock:
            return list(self._scenarios.values())

    def delete_scenario(self, scenario_id: str) -> bool:
        """Delete a scenario and any associated outcomes/reports.

        Returns True if the scenario existed and was deleted, False otherwise.
        """
        with self._lock:
            if scenario_id not in self._scenarios:
                return False
            self._scenarios.pop(scenario_id, None)
            self._outcomes.pop(scenario_id, None)
            self._reports.pop(scenario_id, None)
            return True

    # ── Variable management ────────────────────────────────

    def add_variable(
        self,
        scenario_id: str,
        name: str,
        description: str,
        variable_type: VariableType,
        distribution: DistributionType,
        min_value: float | None = None,
        max_value: float | None = None,
        mean: float | None = None,
        std: float | None = None,
        categories: list[str] | None = None,
    ) -> ScenarioVariable:
        """Add a new stochastic variable to a scenario.

        Raises KeyError if the scenario does not exist.
        Raises ValueError if a categorical distribution is requested without categories.
        """
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                raise KeyError(f"Scenario not found: {scenario_id}")

            if distribution == DistributionType.CATEGORICAL and not categories:
                raise ValueError(
                    "categories must be provided for categorical distribution"
                )

            variable = ScenarioVariable(
                name=name,
                description=description,
                variable_type=variable_type,
                distribution=distribution,
                min_value=min_value,
                max_value=max_value,
                mean=mean,
                std=std,
                categories=list(categories) if categories else [],
            )
            scenario.variables[variable.variable_id] = variable
            scenario.updated_at = time.time()
            return variable

    def get_variable(self, scenario_id: str, variable_id: str) -> ScenarioVariable | None:
        """Retrieve a variable by id from a scenario, or None if not found."""
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return None
            return scenario.variables.get(variable_id)

    def list_variables(self, scenario_id: str) -> list[ScenarioVariable]:
        """List all variables in a scenario as a fresh list."""
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return []
            return list(scenario.variables.values())

    # ── Action management ──────────────────────────────────

    def add_action(
        self,
        scenario_id: str,
        name: str,
        description: str,
        preconditions: list[str] | None = None,
        effects: dict[str, float] | None = None,
        probability: float = 1.0,
        cost: float = 0.0,
        duration: float = 1.0,
    ) -> ScenarioAction:
        """Add a new action to a scenario.

        Raises KeyError if the scenario does not exist.
        Raises ValueError if probability is outside [0, 1] or cost/duration are negative.
        """
        if not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be in [0, 1]")
        if cost < 0.0:
            raise ValueError("cost must be non-negative")
        if duration < 0.0:
            raise ValueError("duration must be non-negative")

        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                raise KeyError(f"Scenario not found: {scenario_id}")

            action = ScenarioAction(
                name=name,
                description=description,
                preconditions=list(preconditions) if preconditions else [],
                effects=dict(effects) if effects else {},
                probability=probability,
                cost=cost,
                duration=duration,
            )
            scenario.actions.append(action)
            scenario.updated_at = time.time()
            return action

    def list_actions(self, scenario_id: str) -> list[ScenarioAction]:
        """List all actions in a scenario as a fresh list."""
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return []
            return list(scenario.actions)

    # ── Simulation execution ───────────────────────────────

    def run_simulation(self, scenario_id: str) -> SimulationReport:
        """Run num_simulations Monte Carlo runs of the scenario.

        For each run:
          - Sample initial variable values from their distributions.
          - Execute up to max_steps actions, sampling each action's success via its
            probability.
          - Apply effects, accumulate cost/duration, and record the action history.
          - Classify the run outcome and compute a score.

        Aggregates all outcomes into a SimulationReport and persists it for later
        retrieval via get_report().

        Raises KeyError if the scenario does not exist.
        """
        # Snapshot the inputs under the lock, then run the simulation without holding
        # the lock so concurrent simulations on other scenarios are not blocked.
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                raise KeyError(f"Scenario not found: {scenario_id}")

            scenario.status = SimulationStatus.RUNNING
            scenario.updated_at = time.time()

            variables_snapshot = {vid: v for vid, v in scenario.variables.items()}
            actions_snapshot = list(scenario.actions)
            max_steps = scenario.max_steps
            num_simulations = scenario.num_simulations
            seed = scenario.seed
            scenario_type = scenario.scenario_type

        # Set up the RNG for reproducibility. A None seed uses OS entropy.
        rng = random.Random(seed)
        start_time = time.time()
        outcomes: list[SimulationOutcome] = []

        try:
            for run_index in range(num_simulations):
                outcome = self._run_single_simulation(
                    scenario_id=scenario_id,
                    run_index=run_index,
                    variables=variables_snapshot,
                    actions=actions_snapshot,
                    max_steps=max_steps,
                    scenario_type=scenario_type,
                    rng=rng,
                )
                outcomes.append(outcome)
        except Exception:
            # Mark the scenario as failed on any unexpected error and re-raise.
            with self._lock:
                scenario = self._scenarios.get(scenario_id)
                if scenario is not None:
                    scenario.status = SimulationStatus.FAILED
                    scenario.updated_at = time.time()
            raise

        elapsed = time.time() - start_time
        report = self._aggregate_outcomes(scenario_id, outcomes, elapsed)

        # Persist outcomes, the report, and update aggregate stats under the lock.
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is not None:
                scenario.status = SimulationStatus.COMPLETED
                scenario.updated_at = time.time()

            existing = self._outcomes.get(scenario_id, [])
            combined = existing + outcomes
            if len(combined) > self.MAX_OUTCOMES_PER_SCENARIO:
                # Keep only the most recent outcomes.
                combined = combined[-self.MAX_OUTCOMES_PER_SCENARIO:]
            self._outcomes[scenario_id] = combined
            self._reports[scenario_id] = report

            self._total_simulations += len(outcomes)
            self._total_successful += sum(
                1 for o in outcomes if o.outcome_type == OutcomeType.SUCCESS
            )
            self._total_failed += sum(
                1 for o in outcomes
                if o.outcome_type in (OutcomeType.FAILURE, OutcomeType.ERROR, OutcomeType.TIMEOUT)
            )
            self._total_simulation_time += elapsed

        return report

    def cancel_simulation(self, scenario_id: str) -> bool:
        """Mark a scenario as cancelled.

        Returns True if the scenario existed and was not already completed/failed.
        Note: this does not interrupt an in-progress run_simulation call; it only
        updates the persisted status for scenarios that have not yet been run.
        """
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return False
            if scenario.status in (SimulationStatus.COMPLETED, SimulationStatus.FAILED):
                return False
            scenario.status = SimulationStatus.CANCELLED
            scenario.updated_at = time.time()
            return True

    def _run_single_simulation(
        self,
        scenario_id: str,
        run_index: int,
        variables: dict[str, ScenarioVariable],
        actions: list[ScenarioAction],
        max_steps: int,
        scenario_type: ScenarioType,
        rng: random.Random,
    ) -> SimulationOutcome:
        """Execute a single Monte Carlo run and produce a SimulationOutcome.

        Executes actions in sequence up to max_steps (or until the action list is
        exhausted, whichever comes first). For each action, preconditions are checked,
        success is sampled via the action's probability (adjusted for scenario type),
        and effects are applied on success.
        """
        # Initialize the run state by sampling each variable from its distribution.
        state: dict[str, Any] = {}
        for variable in variables.values():
            state[variable.name] = self._sample_variable_value(variable, rng)

        action_history: list[str] = []
        total_cost = 0.0
        total_duration = 0.0
        steps_taken = 0
        actions_succeeded = 0
        actions_attempted = 0
        effects_applied = 0

        # Pre-count total effects across all actions for score normalization.
        total_effects = sum(len(action.effects) for action in actions)

        # Execute actions in sequence up to max_steps.
        for step in range(max_steps):
            if step >= len(actions):
                # No more actions to execute; stop early.
                break

            action = actions[step]
            steps_taken += 1
            actions_attempted += 1

            # Check preconditions against the current state.
            if not self._evaluate_preconditions(action, state):
                action_history.append(f"skip:{action.name}")
                continue

            # Compute the effective probability based on the scenario type.
            effective_probability = action.probability
            if scenario_type == ScenarioType.DETERMINISTIC:
                # Deterministic scenarios always succeed if preconditions pass.
                effective_probability = 1.0 if action.probability > 0 else 0.0
            elif scenario_type == ScenarioType.ADVERSARIAL:
                # Adversarial scenarios model an opponent that halves success rates.
                effective_probability = max(0.0, action.probability * 0.5)
            # STOCHASTIC and MONTE_CARLO use the action's configured probability.

            if rng.random() < effective_probability:
                # Action succeeded - apply effects and accumulate full cost/duration.
                state = self._apply_effects(action, state)
                effects_applied += len(action.effects)
                actions_succeeded += 1
                total_cost += action.cost
                total_duration += action.duration
                action_history.append(f"ok:{action.name}")
            else:
                # Action failed - incur half cost/duration but apply no effects.
                total_cost += action.cost * 0.5
                total_duration += action.duration * 0.5
                action_history.append(f"fail:{action.name}")

        # Classify the run outcome.
        outcome_type = self._classify_outcome(
            run_state=state,
            steps=steps_taken,
            max_steps=max_steps,
            actions_succeeded=actions_succeeded,
            actions_attempted=actions_attempted,
        )

        # Compute the score: fraction of effects applied scaled to 100, minus a
        # cost penalty. A higher score is better.
        if total_effects > 0:
            score = (effects_applied / total_effects) * 100.0 - total_cost * 0.1
        else:
            # No effects defined - score is purely the negative cost penalty.
            score = 0.0 - total_cost * 0.1

        return SimulationOutcome(
            scenario_id=scenario_id,
            run_index=run_index,
            outcome_type=outcome_type,
            final_state=dict(state),
            total_cost=total_cost,
            total_duration=total_duration,
            steps_taken=steps_taken,
            action_history=action_history,
            score=score,
        )

    def _sample_variable_value(self, variable: ScenarioVariable, rng: random.Random) -> Any:
        """Sample a single value from the variable's configured distribution.

        - uniform:      random.uniform(min, max)
        - normal:       random.gauss(mean, std)
        - triangular:   random.triangular(min, max, mean)  (mean used as the mode)
        - exponential:  random.expovariate(1 / mean)
        - categorical:  random.choice(categories)
        """
        dist = variable.distribution

        if dist == DistributionType.UNIFORM:
            lo = variable.min_value if variable.min_value is not None else 0.0
            hi = variable.max_value if variable.max_value is not None else 1.0
            if hi < lo:
                lo, hi = hi, lo
            return rng.uniform(lo, hi)

        if dist == DistributionType.NORMAL:
            mean = variable.mean if variable.mean is not None else 0.0
            std = variable.std if variable.std is not None else 1.0
            if std < 0.0:
                std = 0.0
            return rng.gauss(mean, std)

        if dist == DistributionType.TRIANGULAR:
            lo = variable.min_value if variable.min_value is not None else 0.0
            hi = variable.max_value if variable.max_value is not None else 1.0
            if hi < lo:
                lo, hi = hi, lo
            mode = variable.mean if variable.mean is not None else (lo + hi) / 2.0
            # Clamp the mode to [lo, hi] to satisfy random.triangular's contract.
            mode = max(lo, min(hi, mode))
            return rng.triangular(lo, hi, mode)

        if dist == DistributionType.EXPONENTIAL:
            mean = variable.mean if variable.mean is not None else 1.0
            if mean <= 0:
                mean = 1e-9
            return rng.expovariate(1.0 / mean)

        if dist == DistributionType.CATEGORICAL:
            if not variable.categories:
                return None
            return rng.choice(variable.categories)

        # Fallback for unknown distributions.
        return variable.current_value

    def _evaluate_preconditions(self, action: ScenarioAction, state: dict[str, Any]) -> bool:
        """Evaluate simple preconditions: all referenced variable values must be > 0.

        Returns True if the action has no preconditions, or if every named precondition
        variable exists in the state and has a numeric value greater than zero.
        """
        if not action.preconditions:
            return True

        for precondition in action.preconditions:
            value = state.get(precondition)
            if value is None:
                return False
            try:
                if not (float(value) > 0):
                    return False
            except (TypeError, ValueError):
                # Non-numeric precondition values are treated as unsatisfied.
                return False
        return True

    def _apply_effects(self, action: ScenarioAction, state: dict[str, Any]) -> dict[str, Any]:
        """Apply an action's effects to a copy of the state and return the new state.

        Each effect adds its delta to the current value of the named variable. If the
        current value is non-numeric, the delta replaces it.
        """
        new_state = dict(state)
        for variable_name, delta in action.effects.items():
            current = new_state.get(variable_name, 0.0)
            try:
                new_state[variable_name] = float(current) + delta
            except (TypeError, ValueError):
                new_state[variable_name] = delta
        return new_state

    def _classify_outcome(
        self,
        run_state: dict[str, Any],
        steps: int,
        max_steps: int,
        actions_succeeded: int,
        actions_attempted: int,
    ) -> OutcomeType:
        """Classify the outcome of a run based on action success and step count.

        Classification rules (in priority order):
          1. TIMEOUT  - if the run consumed all available steps without succeeding
                        on every attempted action.
          2. FAILURE  - if no attempted actions succeeded.
          3. SUCCESS  - if all attempted actions succeeded and at least one was attempted.
          4. PARTIAL_SUCCESS - if some but not all attempted actions succeeded.

        For runs with no attempted actions (empty action list), SUCCESS is returned
        if the run state is empty, otherwise PARTIAL_SUCCESS.
        """
        # No actions were executed at all.
        if actions_attempted == 0:
            return OutcomeType.SUCCESS if not run_state else OutcomeType.PARTIAL_SUCCESS

        # TIMEOUT takes precedence if max_steps was reached and not all actions succeeded.
        if steps >= max_steps and actions_succeeded < actions_attempted:
            return OutcomeType.TIMEOUT

        # No actions succeeded -> failure.
        if actions_succeeded == 0:
            return OutcomeType.FAILURE

        # All attempted actions succeeded -> success.
        if actions_succeeded == actions_attempted:
            return OutcomeType.SUCCESS

        # Some but not all actions succeeded -> partial success.
        return OutcomeType.PARTIAL_SUCCESS

    def _aggregate_outcomes(
        self,
        scenario_id: str,
        outcomes: list[SimulationOutcome],
        elapsed: float,
    ) -> SimulationReport:
        """Aggregate a list of outcomes into a SimulationReport with statistics."""
        total_runs = len(outcomes)
        if total_runs == 0:
            return SimulationReport(
                scenario_id=scenario_id,
                total_runs=0,
                completed_runs=0,
                created_at=time.time(),
            )

        completed_runs = sum(
            1 for o in outcomes if o.outcome_type != OutcomeType.ERROR
        )
        success_count = sum(
            1 for o in outcomes if o.outcome_type == OutcomeType.SUCCESS
        )
        failure_count = sum(
            1 for o in outcomes
            if o.outcome_type in (OutcomeType.FAILURE, OutcomeType.ERROR, OutcomeType.TIMEOUT)
        )

        success_rate = success_count / total_runs
        failure_rate = failure_count / total_runs
        avg_cost = sum(o.total_cost for o in outcomes) / total_runs
        avg_duration = sum(o.total_duration for o in outcomes) / total_runs
        avg_score = sum(o.score for o in outcomes) / total_runs

        # Build the outcome distribution histogram.
        outcome_distribution: dict[str, int] = {}
        for outcome in outcomes:
            key = outcome.outcome_type.value
            outcome_distribution[key] = outcome_distribution.get(key, 0) + 1

        # Compute per-variable statistics from the numeric entries in final states.
        variable_stats: dict[str, dict[str, float]] = {}
        numeric_values: dict[str, list[float]] = {}
        for outcome in outcomes:
            for var_name, value in outcome.final_state.items():
                try:
                    numeric_values.setdefault(var_name, []).append(float(value))
                except (TypeError, ValueError):
                    continue

        for var_name, values in numeric_values.items():
            if not values:
                continue
            count = len(values)
            mean = sum(values) / count
            variance = sum((v - mean) ** 2 for v in values) / count
            std = math.sqrt(variance)
            variable_stats[var_name] = {
                "mean": mean,
                "std": std,
                "min": min(values),
                "max": max(values),
            }

        # Best and worst outcomes by score.
        best_outcome = max(outcomes, key=lambda o: o.score)
        worst_outcome = min(outcomes, key=lambda o: o.score)

        return SimulationReport(
            scenario_id=scenario_id,
            total_runs=total_runs,
            completed_runs=completed_runs,
            success_rate=success_rate,
            failure_rate=failure_rate,
            avg_cost=avg_cost,
            avg_duration=avg_duration,
            avg_score=avg_score,
            outcome_distribution=outcome_distribution,
            variable_stats=variable_stats,
            best_outcome=best_outcome,
            worst_outcome=worst_outcome,
            created_at=time.time(),
        )

    # ── Reporting and stats ────────────────────────────────

    def get_report(self, scenario_id: str) -> SimulationReport | None:
        """Retrieve the most recent simulation report for a scenario, or None."""
        with self._lock:
            return self._reports.get(scenario_id)

    def list_outcomes(self, scenario_id: str) -> list[SimulationOutcome]:
        """List all stored outcomes for a scenario as a fresh list."""
        with self._lock:
            outcomes = self._outcomes.get(scenario_id, [])
            return list(outcomes)

    def compare_scenarios(self, scenario_ids: list[str]) -> dict[str, Any]:
        """Compare success rates, avg costs, and avg scores across multiple scenarios.

        Returns a dict mapping each scenario_id to a summary dict. A `_ranking` key
        lists the scenario ids with the best success rate, best average score, and
        lowest average cost among the available scenarios.
        """
        # Snapshot the relevant data under the lock.
        with self._lock:
            scenario_ids_copy = list(scenario_ids)
            reports = {
                sid: self._reports.get(sid) for sid in scenario_ids_copy
            }
            scenarios = {
                sid: self._scenarios.get(sid) for sid in scenario_ids_copy
            }

        comparison: dict[str, Any] = {}
        for sid in scenario_ids_copy:
            report = reports.get(sid)
            scenario = scenarios.get(sid)
            if report is None or scenario is None:
                comparison[sid] = {
                    "scenario_id": sid,
                    "name": scenario.name if scenario else "",
                    "available": False,
                }
                continue

            comparison[sid] = {
                "scenario_id": sid,
                "name": scenario.name,
                "scenario_type": scenario.scenario_type.value,
                "available": True,
                "total_runs": report.total_runs,
                "success_rate": report.success_rate,
                "failure_rate": report.failure_rate,
                "avg_cost": report.avg_cost,
                "avg_duration": report.avg_duration,
                "avg_score": report.avg_score,
                "outcome_distribution": dict(report.outcome_distribution),
            }

        # Compute relative rankings across the available scenarios.
        available = {
            sid: data for sid, data in comparison.items() if data.get("available")
        }
        if available:
            best_success_sid = max(
                available.keys(), key=lambda s: available[s]["success_rate"]
            )
            best_score_sid = max(
                available.keys(), key=lambda s: available[s]["avg_score"]
            )
            lowest_cost_sid = min(
                available.keys(), key=lambda s: available[s]["avg_cost"]
            )
            comparison["_ranking"] = {
                "best_success_rate": best_success_sid,
                "best_avg_score": best_score_sid,
                "lowest_avg_cost": lowest_cost_sid,
            }
        else:
            comparison["_ranking"] = {}

        return comparison

    def get_stats(self) -> SimulatorStats:
        """Return aggregate statistics about simulator usage.

        Includes total scenario count, total simulations run, success/failure totals,
        the overall average success rate, and the average wall-clock time per run.
        """
        with self._lock:
            total_scenarios = len(self._scenarios)
            total_simulations = self._total_simulations
            total_successful = self._total_successful
            total_failed = self._total_failed
            total_time = self._total_simulation_time

        if total_simulations > 0:
            avg_success_rate = total_successful / total_simulations
            avg_simulation_time = total_time / total_simulations
        else:
            avg_success_rate = 0.0
            avg_simulation_time = 0.0

        return SimulatorStats(
            total_scenarios=total_scenarios,
            total_simulations=total_simulations,
            total_successful=total_successful,
            total_failed=total_failed,
            avg_success_rate=avg_success_rate,
            avg_simulation_time=avg_simulation_time,
        )


# ═══════════════════════════════════════════════════════════
# Module-level Singleton
# ═══════════════════════════════════════════════════════════

_global_simulator: AgentScenarioSimulator | None = None
_global_simulator_lock = threading.Lock()


def get_scenario_simulator() -> AgentScenarioSimulator:
    """Return the process-wide singleton AgentScenarioSimulator instance."""
    global _global_simulator
    with _global_simulator_lock:
        if _global_simulator is None:
            _global_simulator = AgentScenarioSimulator()
        return _global_simulator


def reset_scenario_simulator() -> None:
    """Reset the process-wide singleton, discarding all scenarios and outcomes."""
    global _global_simulator
    with _global_simulator_lock:
        _global_simulator = None
