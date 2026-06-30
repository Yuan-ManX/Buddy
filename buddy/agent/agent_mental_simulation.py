"""Agent Mental Simulation Engine - forward planning via imagined outcome simulation.

This engine lets the agent simulate outcomes in a mental model before acting. It
supports forward planning, consequence prediction, and hypothetical reasoning by
allowing the agent to "imagine" different scenarios and evaluate actions without
real-world consequences.

A mental model (MentalModel) captures an initial state plus a set of transition
rules that describe how the model's variables evolve. A simulation (Simulation)
runs against a model and is composed of a sequence of SimulationStep entries,
each describing an action, the pre/post state, an occurrence probability, and a
duration. Once a simulation has been stepped through, one or more
SimulationOutcome records capture the final state, valence, utility, probability,
and confidence of the imagined result.

The engine exposes operations to create/list/update/delete models, create and
step through simulations, record outcomes, compare and rank outcomes for a single
simulation, cancel simulations, and report aggregate usage statistics.

Typical usage::

    engine = get_mental_simulation_engine()
    model = engine.create_model(
        agent_id="agent-1",
        name="navigation-model",
        model_type=ModelType.HYBRID,
        initial_state={"position": 0, "fuel": 10},
        transition_rules=["move(position)", "consume(fuel)"],
    )
    sim = engine.create_simulation(
        model_id=model.model_id,
        agent_id="agent-1",
        simulation_type=SimulationType.PREDICTIVE,
        config={"horizon": 5},
    )
    engine.add_step(sim.simulation_id, "move_forward",
                    pre_state={"position": 0}, post_state={"position": 1},
                    probability=0.9, description="advance one cell")
    engine.record_outcome(
        simulation_id=sim.simulation_id,
        final_state={"position": 1, "fuel": 9},
        valence=OutcomeValence.POSITIVE,
        utility=8.0,
        probability=0.9,
        confidence=ConfidenceLevel.HIGH,
        key_events=["reached waypoint"],
        summary="reached the next waypoint with fuel to spare",
    )
    ranking = engine.compare_outcomes(sim.simulation_id)

All public state mutations are guarded by a threading.Lock to ensure thread safety
when the engine is shared across agent threads.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "SimulationType",
    "SimulationStatus",
    "ModelType",
    "OutcomeValence",
    "ConfidenceLevel",
    "ModelState",
    "SimulationStep",
    "SimulationOutcome",
    "MentalModel",
    "Simulation",
    "SimulationStats",
    "AgentMentalSimulationEngine",
    "get_mental_simulation_engine",
    "reset_mental_simulation_engine",
]


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class SimulationType(str, Enum):
    """Kinds of mental simulations the engine can run."""
    PREDICTIVE = "predictive"
    COUNTERFACTUAL = "counterfactual"
    HYPOTHETICAL = "hypothetical"
    RETROSPECTIVE = "retrospective"
    EXPLORATORY = "exploratory"


class SimulationStatus(str, Enum):
    """Lifecycle states of a mental simulation."""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelType(str, Enum):
    """Underlying model families used to drive state transitions."""
    DETERMINISTIC = "deterministic"
    PROBABILISTIC = "probabilistic"
    HEURISTIC = "heuristic"
    NEURAL = "neural"
    HYBRID = "hybrid"


class OutcomeValence(str, Enum):
    """Subjective valence assigned to a simulated outcome."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ConfidenceLevel(str, Enum):
    """Coarse confidence labels for a simulated outcome.

    Mapped to numeric weights via _CONFIDENCE_WEIGHTS so that aggregate
    statistics can be computed as averages.
    """
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# Numeric weights used to convert a ConfidenceLevel into a scalar in [0, 1] for
# averaging and ranking. Kept module-private to avoid polluting the public API.
_CONFIDENCE_WEIGHTS: dict[ConfidenceLevel, float] = {
    ConfidenceLevel.VERY_LOW: 0.1,
    ConfidenceLevel.LOW: 0.3,
    ConfidenceLevel.MEDIUM: 0.5,
    ConfidenceLevel.HIGH: 0.75,
    ConfidenceLevel.VERY_HIGH: 0.95,
}


# ═══════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════

@dataclass
class ModelState:
    """A snapshot of the simulated world at a single point in time.

    `variables` holds the named state values, `constraints` lists invariant
    expressions that must hold for the state to be valid, and `parent_state_id`
    links the state to its predecessor for trajectory reconstruction.
    """
    state_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    variables: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    parent_state_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "variables": dict(self.variables),
            "constraints": list(self.constraints),
            "timestamp": self.timestamp,
            "parent_state_id": self.parent_state_id,
        }


@dataclass
class SimulationStep:
    """A single action applied within a mental simulation.

    `pre_state` and `post_state` are variable snapshots taken before and after
    the action is applied. `probability` is the likelihood that the action
    produces the recorded transition, and `duration` is the simulated time the
    action consumes in arbitrary units.
    """
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_number: int = 0
    action: str = ""
    pre_state: dict[str, Any] = field(default_factory=dict)
    post_state: dict[str, Any] = field(default_factory=dict)
    probability: float = 1.0
    duration: float = 0.0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "action": self.action,
            "pre_state": dict(self.pre_state),
            "post_state": dict(self.post_state),
            "probability": self.probability,
            "duration": self.duration,
            "description": self.description,
        }


@dataclass
class SimulationOutcome:
    """The result of imagining one possible future for a simulation.

    `utility` is a scalar reward signal for the final state, `probability` is
    the likelihood of reaching this outcome, and `confidence` reflects how much
    the agent trusts the prediction. `key_events` is a list of human-readable
    milestones and `summary` is a short prose description.
    """
    outcome_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    simulation_id: str = ""
    final_state: dict[str, Any] = field(default_factory=dict)
    valence: OutcomeValence = OutcomeValence.NEUTRAL
    utility: float = 0.0
    probability: float = 1.0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    key_events: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "simulation_id": self.simulation_id,
            "final_state": dict(self.final_state),
            "valence": self.valence.value,
            "utility": self.utility,
            "probability": self.probability,
            "confidence": self.confidence.value,
            "key_events": list(self.key_events),
            "summary": self.summary,
        }


@dataclass
class MentalModel:
    """A reusable mental model describing an initial state and transition rules.

    `transition_rules` is a list of rule expressions (free-form strings) that
    the agent interprets when stepping a simulation forward. `validity_range`
    is a dict that may carry bounds such as {"horizon": 10.0} describing how far
    into the future the model is considered reliable.
    """
    model_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    name: str = ""
    model_type: ModelType = ModelType.HEURISTIC
    initial_state: ModelState = field(default_factory=ModelState)
    transition_rules: list[str] = field(default_factory=list)
    validity_range: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "model_type": self.model_type.value,
            "initial_state": self.initial_state.to_dict(),
            "transition_rules": list(self.transition_rules),
            "validity_range": dict(self.validity_range),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Simulation:
    """A single mental simulation run against a MentalModel.

    Starts in DRAFT status, transitions to RUNNING once the first step is added,
    and to COMPLETED once at least one outcome has been recorded. `config` carries
    free-form per-simulation options such as depth limits or sampling strategy.
    """
    simulation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    model_id: str = ""
    agent_id: str = ""
    simulation_type: SimulationType = SimulationType.PREDICTIVE
    steps: list[SimulationStep] = field(default_factory=list)
    outcomes: list[SimulationOutcome] = field(default_factory=list)
    status: SimulationStatus = SimulationStatus.DRAFT
    started_at: float | None = None
    completed_at: float | None = None
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "model_id": self.model_id,
            "agent_id": self.agent_id,
            "simulation_type": self.simulation_type.value,
            "steps": [s.to_dict() for s in self.steps],
            "outcomes": [o.to_dict() for o in self.outcomes],
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "config": dict(self.config),
        }


@dataclass
class SimulationStats:
    """Aggregate usage statistics for the entire mental simulation engine."""
    total_models: int = 0
    total_simulations: int = 0
    total_outcomes: int = 0
    simulations_by_type: dict[str, int] = field(default_factory=dict)
    simulations_by_status: dict[str, int] = field(default_factory=dict)
    avg_utility: float = 0.0
    avg_confidence: float = 0.0
    avg_steps: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_models": self.total_models,
            "total_simulations": self.total_simulations,
            "total_outcomes": self.total_outcomes,
            "simulations_by_type": dict(self.simulations_by_type),
            "simulations_by_status": dict(self.simulations_by_status),
            "avg_utility": self.avg_utility,
            "avg_confidence": self.avg_confidence,
            "avg_steps": self.avg_steps,
        }


# ═══════════════════════════════════════════════════════════
# Main Engine Class
# ═══════════════════════════════════════════════════════════

class AgentMentalSimulationEngine:
    """Mental simulation engine for imagining outcomes before acting.

    Maintains a registry of MentalModel objects keyed by model id, and a registry
    of Simulation objects keyed by simulation id. Each simulation references a
    model and accumulates SimulationStep entries as the agent imagines acting, and
    SimulationOutcome entries as it imagines results. Outcomes can be compared and
    ranked to support forward planning, counterfactual reasoning, and hypothetical
    evaluation without real-world side effects.

    The engine enforces soft capacity limits to bound memory usage: once the model
    or simulation registries reach their cap, the oldest entries are evicted.

    All state mutations are guarded by a threading.Lock to ensure thread safety
    when the engine is shared across agent threads.
    """

    # Soft capacity caps to bound memory usage in long-running agents.
    MAX_MODELS: int = 2000
    MAX_SIMULATIONS: int = 5000
    MAX_STEPS_PER_SIMULATION: int = 1000
    MAX_OUTCOMES_PER_SIMULATION: int = 500

    def __init__(self) -> None:
        self._models: dict[str, MentalModel] = {}
        self._simulations: dict[str, Simulation] = {}
        self._lock = threading.Lock()
        # Aggregate counters used to compute SimulationStats without rescanning.
        self._total_outcomes: int = 0

    # ── Model management ───────────────────────────────────

    def create_model(
        self,
        agent_id: str,
        name: str,
        model_type: ModelType,
        initial_state: dict[str, Any] | None = None,
        transition_rules: list[str] | None = None,
    ) -> MentalModel:
        """Create and register a new MentalModel.

        `initial_state` is treated as the variable map for the model's initial
        ModelState. `transition_rules` is a list of free-form rule expressions
        interpreted by the caller when stepping a simulation forward.

        Args:
            agent_id: Owning agent identifier; may be empty for shared models.
            name: Human-readable model name; must be non-empty.
            model_type: Family of the underlying transition model.
            initial_state: Optional variable map seed for the model's initial
                ModelState. Defaults to an empty variable map.
            transition_rules: Optional list of rule expression strings. Defaults
                to an empty list.

        Returns:
            The newly created and registered MentalModel.

        Raises:
            ValueError: if `name` is empty.
        """
        if not name:
            raise ValueError("model name must not be empty")

        with self._lock:
            # Evict the oldest model if we are at capacity.
            if len(self._models) >= self.MAX_MODELS:
                oldest_id = min(
                    self._models.keys(),
                    key=lambda mid: self._models[mid].created_at,
                )
                self._models.pop(oldest_id, None)

            state = ModelState(
                variables=dict(initial_state) if initial_state else {},
            )
            model = MentalModel(
                agent_id=agent_id,
                name=name,
                model_type=model_type,
                initial_state=state,
                transition_rules=list(transition_rules) if transition_rules else [],
            )
            self._models[model.model_id] = model
            return model

    def get_model(self, model_id: str) -> MentalModel | None:
        """Retrieve a model by id, or None if not found."""
        with self._lock:
            return self._models.get(model_id)

    def list_models(self, agent_id: str | None = None) -> list[MentalModel]:
        """List registered models, optionally filtered by agent id.

        Returns a fresh list. When `agent_id` is None, all models are returned.
        """
        with self._lock:
            if agent_id is None:
                return list(self._models.values())
            return [m for m in self._models.values() if m.agent_id == agent_id]

    def update_model(
        self,
        model_id: str,
        initial_state: dict[str, Any] | None = None,
        transition_rules: list[str] | None = None,
    ) -> MentalModel:
        """Update a model's initial state and/or transition rules.

        Either `initial_state` or `transition_rules` may be None to leave that
        field unchanged. When `initial_state` is provided, the existing
        ModelState is replaced with a fresh one that preserves the original
        state id, constraints, and parent linkage while refreshing the variable
        map and timestamp. The model's `updated_at` timestamp is always refreshed.

        Args:
            model_id: Id of the model to update.
            initial_state: Optional new variable map; None leaves it unchanged.
            transition_rules: Optional new rule list; None leaves it unchanged.

        Returns:
            The updated MentalModel.

        Raises:
            KeyError: if the model does not exist.
        """
        with self._lock:
            model = self._models.get(model_id)
            if model is None:
                raise KeyError(f"Model not found: {model_id}")

            if initial_state is not None:
                # Preserve the existing state id and lineage where possible.
                existing = model.initial_state
                model.initial_state = ModelState(
                    state_id=existing.state_id,
                    variables=dict(initial_state),
                    constraints=list(existing.constraints),
                    timestamp=time.time(),
                    parent_state_id=existing.parent_state_id,
                )
            if transition_rules is not None:
                model.transition_rules = list(transition_rules)
            model.updated_at = time.time()
            return model

    def delete_model(self, model_id: str) -> bool:
        """Delete a model. Returns True if it existed and was deleted.

        Note: simulations referencing the deleted model are not removed; callers
        that need a full cleanup should delete dependent simulations first.
        """
        with self._lock:
            return self._models.pop(model_id, None) is not None

    # ── Simulation management ──────────────────────────────

    def create_simulation(
        self,
        model_id: str,
        agent_id: str,
        simulation_type: SimulationType,
        config: dict[str, Any] | None = None,
    ) -> Simulation:
        """Create and register a new Simulation against an existing model.

        The simulation starts in DRAFT status with `started_at` unset. It
        transitions to RUNNING when the first step is added and to COMPLETED
        when the first outcome is recorded.

        Args:
            model_id: Id of the MentalModel this simulation runs against.
            agent_id: Owning agent identifier.
            simulation_type: Kind of mental simulation to run.
            config: Optional free-form per-simulation options (e.g. depth
                limits or sampling strategy). Defaults to an empty dict.

        Returns:
            The newly created and registered Simulation.

        Raises:
            KeyError: if the referenced model does not exist.
        """
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model not found: {model_id}")

            # Evict the oldest simulation if we are at capacity.
            if len(self._simulations) >= self.MAX_SIMULATIONS:
                oldest_id = min(
                    self._simulations.keys(),
                    key=lambda sid: (
                        self._simulations[sid].started_at
                        if self._simulations[sid].started_at is not None
                        else float("inf")
                    ),
                )
                old = self._simulations.pop(oldest_id, None)
                if old is not None:
                    self._total_outcomes -= len(old.outcomes)

            simulation = Simulation(
                model_id=model_id,
                agent_id=agent_id,
                simulation_type=simulation_type,
                config=dict(config) if config else {},
            )
            self._simulations[simulation.simulation_id] = simulation
            return simulation

    def get_simulation(self, simulation_id: str) -> Simulation | None:
        """Retrieve a simulation by id, or None if not found."""
        with self._lock:
            return self._simulations.get(simulation_id)

    def list_simulations(
        self,
        agent_id: str | None = None,
        status: SimulationStatus | None = None,
    ) -> list[Simulation]:
        """List simulations, optionally filtered by agent id and/or status.

        Returns a fresh list. Either filter may be None to skip that filter.
        """
        with self._lock:
            results: list[Simulation] = []
            for sim in self._simulations.values():
                if agent_id is not None and sim.agent_id != agent_id:
                    continue
                if status is not None and sim.status != status:
                    continue
                results.append(sim)
            return results

    # ── Step management ────────────────────────────────────

    def add_step(
        self,
        simulation_id: str,
        action: str,
        pre_state: dict[str, Any] | None = None,
        post_state: dict[str, Any] | None = None,
        probability: float = 1.0,
        description: str = "",
    ) -> SimulationStep:
        """Append a SimulationStep to a simulation.

        The step number is assigned automatically as one plus the current step
        count. Adding the first step transitions the simulation from DRAFT to
        RUNNING and records `started_at`. Steps cannot be added to a simulation
        that has already reached a terminal status.

        Args:
            simulation_id: Id of the simulation to extend.
            action: Name of the imagined action.
            pre_state: Optional variable snapshot before the action.
            post_state: Optional variable snapshot after the action.
            probability: Likelihood of the action producing this transition;
                must be in [0, 1].
            description: Optional human-readable description of the step.

        Returns:
            The newly created SimulationStep.

        Raises:
            KeyError: if the simulation does not exist.
            ValueError: if `probability` is outside [0, 1], if the simulation
                is terminal (completed/failed/cancelled), or if the step cap
                (MAX_STEPS_PER_SIMULATION) is reached.
        """
        if not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be in [0, 1]")

        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                raise KeyError(f"Simulation not found: {simulation_id}")

            if sim.status in (
                SimulationStatus.COMPLETED,
                SimulationStatus.FAILED,
                SimulationStatus.CANCELLED,
            ):
                raise ValueError(
                    f"cannot add step to terminal simulation ({sim.status.value})"
                )

            if len(sim.steps) >= self.MAX_STEPS_PER_SIMULATION:
                raise ValueError(
                    f"step cap reached ({self.MAX_STEPS_PER_SIMULATION})"
                )

            # Transition DRAFT -> RUNNING on the first step.
            if sim.status == SimulationStatus.DRAFT:
                sim.status = SimulationStatus.RUNNING
                sim.started_at = time.time()

            step = SimulationStep(
                step_number=len(sim.steps) + 1,
                action=action,
                pre_state=dict(pre_state) if pre_state else {},
                post_state=dict(post_state) if post_state else {},
                probability=probability,
                description=description,
            )
            sim.steps.append(step)
            return step

    def list_steps(self, simulation_id: str) -> list[SimulationStep]:
        """List all steps in a simulation as a fresh list.

        Returns an empty list if the simulation does not exist.
        """
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                return []
            return list(sim.steps)

    # ── Outcome management ─────────────────────────────────

    def record_outcome(
        self,
        simulation_id: str,
        final_state: dict[str, Any] | None = None,
        valence: OutcomeValence = OutcomeValence.NEUTRAL,
        utility: float = 0.0,
        probability: float = 1.0,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        key_events: list[str] | None = None,
        summary: str = "",
    ) -> SimulationOutcome:
        """Record a SimulationOutcome for a simulation.

        Recording the first outcome transitions the simulation to COMPLETED and
        sets `completed_at` (it is left unchanged if already set). Additional
        outcomes are appended to support multi-outcome hypothetical comparisons,
        for example when ranking several imagined futures against each other.
        Outcomes cannot be recorded for a CANCELLED simulation.

        Args:
            simulation_id: Id of the simulation the outcome belongs to.
            final_state: Optional variable snapshot at the end of the imagined
                future.
            valence: Subjective valence of the outcome.
            utility: Scalar reward signal for the final state.
            probability: Likelihood of reaching this outcome; must be in [0, 1].
            confidence: Coarse confidence label for the prediction.
            key_events: Optional list of human-readable milestone strings.
            summary: Optional short prose description of the outcome.

        Returns:
            The newly created SimulationOutcome.

        Raises:
            KeyError: if the simulation does not exist.
            ValueError: if `probability` is outside [0, 1], the simulation is
                CANCELLED, or the outcome cap (MAX_OUTCOMES_PER_SIMULATION) is
                reached.
        """
        if not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be in [0, 1]")

        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                raise KeyError(f"Simulation not found: {simulation_id}")

            if sim.status == SimulationStatus.CANCELLED:
                raise ValueError("cannot record outcome for a cancelled simulation")

            if len(sim.outcomes) >= self.MAX_OUTCOMES_PER_SIMULATION:
                raise ValueError(
                    f"outcome cap reached ({self.MAX_OUTCOMES_PER_SIMULATION})"
                )

            outcome = SimulationOutcome(
                simulation_id=simulation_id,
                final_state=dict(final_state) if final_state else {},
                valence=valence,
                utility=utility,
                probability=probability,
                confidence=confidence,
                key_events=list(key_events) if key_events else [],
                summary=summary,
            )
            sim.outcomes.append(outcome)
            self._total_outcomes += 1

            # Transition to COMPLETED on the first recorded outcome.
            if sim.status != SimulationStatus.COMPLETED:
                sim.status = SimulationStatus.COMPLETED
            if sim.completed_at is None:
                sim.completed_at = time.time()
            if sim.started_at is None:
                sim.started_at = sim.completed_at

            return outcome

    def list_outcomes(self, simulation_id: str) -> list[SimulationOutcome]:
        """List all outcomes for a simulation as a fresh list.

        Returns an empty list if the simulation does not exist.
        """
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                return []
            return list(sim.outcomes)

    def compare_outcomes(self, simulation_id: str) -> dict[str, Any]:
        """Compare and rank all outcomes recorded for a simulation.

        Each outcome is scored by a composite of utility, probability, and the
        numeric confidence weight:

            score = utility * probability * confidence_weight

        Returns a dict with:
          - "simulation_id": the queried id
          - "available": whether the simulation exists
          - "outcome_count": number of outcomes compared
          - "ranked": outcomes sorted by score descending (each as to_dict)
          - "best": highest-scoring outcome (or None)
          - "worst": lowest-scoring outcome (or None)
          - "avg_utility", "avg_probability", "avg_confidence": scalar means
          - "valence_distribution": count of outcomes per valence
          - "ranking_metric": description of the score formula
        """
        # Snapshot the outcomes under the lock, then compute outside the lock.
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                return {
                    "simulation_id": simulation_id,
                    "available": False,
                    "outcome_count": 0,
                    "ranked": [],
                    "best": None,
                    "worst": None,
                    "avg_utility": 0.0,
                    "avg_probability": 0.0,
                    "avg_confidence": 0.0,
                    "valence_distribution": {},
                    "ranking_metric": "utility * probability * confidence_weight",
                }
            outcomes = list(sim.outcomes)

        # Score and rank each outcome. Ties are broken by outcome id for stability.
        scored = []
        for outcome in outcomes:
            weight = _CONFIDENCE_WEIGHTS.get(outcome.confidence, 0.5)
            score = outcome.utility * outcome.probability * weight
            scored.append((score, outcome))
        scored.sort(key=lambda pair: (-pair[0], pair[1].outcome_id))

        ranked = [o.to_dict() for _, o in scored]

        count = len(outcomes)
        if count == 0:
            return {
                "simulation_id": simulation_id,
                "available": True,
                "outcome_count": 0,
                "ranked": [],
                "best": None,
                "worst": None,
                "avg_utility": 0.0,
                "avg_probability": 0.0,
                "avg_confidence": 0.0,
                "valence_distribution": {},
                "ranking_metric": "utility * probability * confidence_weight",
            }

        avg_utility = sum(o.utility for o in outcomes) / count
        avg_probability = sum(o.probability for o in outcomes) / count
        avg_confidence = (
            sum(_CONFIDENCE_WEIGHTS.get(o.confidence, 0.5) for o in outcomes) / count
        )

        valence_distribution: dict[str, int] = {}
        for outcome in outcomes:
            key = outcome.valence.value
            valence_distribution[key] = valence_distribution.get(key, 0) + 1

        best = scored[0][1].to_dict()
        worst = scored[-1][1].to_dict()

        return {
            "simulation_id": simulation_id,
            "available": True,
            "outcome_count": count,
            "ranked": ranked,
            "best": best,
            "worst": worst,
            "avg_utility": avg_utility,
            "avg_probability": avg_probability,
            "avg_confidence": avg_confidence,
            "valence_distribution": valence_distribution,
            "ranking_metric": "utility * probability * confidence_weight",
        }

    def cancel_simulation(self, simulation_id: str) -> Simulation:
        """Mark a simulation as CANCELLED and record its completion time.

        Returns the updated simulation. A simulation that is already terminal
        (completed/failed/cancelled) is returned unchanged.

        Raises KeyError if the simulation does not exist.
        """
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim is None:
                raise KeyError(f"Simulation not found: {simulation_id}")

            if sim.status not in (
                SimulationStatus.COMPLETED,
                SimulationStatus.FAILED,
                SimulationStatus.CANCELLED,
            ):
                sim.status = SimulationStatus.CANCELLED
                now = time.time()
                if sim.completed_at is None:
                    sim.completed_at = now
                if sim.started_at is None:
                    sim.started_at = now
            return sim

    # ── Statistics ─────────────────────────────────────────

    def get_stats(self) -> SimulationStats:
        """Return aggregate usage statistics about the engine.

        Computes model/simulation/outcome totals, distributions of simulations by
        type and status, and the average utility, confidence weight, and step
        count across all simulations that have at least one outcome or step.
        """
        with self._lock:
            total_models = len(self._models)
            total_simulations = len(self._simulations)
            total_outcomes = self._total_outcomes

            simulations_by_type: dict[str, int] = {}
            simulations_by_status: dict[str, int] = {}
            utility_sum = 0.0
            utility_count = 0
            confidence_sum = 0.0
            confidence_count = 0
            step_sum = 0
            step_count = 0

            for sim in self._simulations.values():
                tkey = sim.simulation_type.value
                simulations_by_type[tkey] = simulations_by_type.get(tkey, 0) + 1
                skey = sim.status.value
                simulations_by_status[skey] = simulations_by_status.get(skey, 0) + 1

                if sim.outcomes:
                    for outcome in sim.outcomes:
                        utility_sum += outcome.utility
                        confidence_sum += _CONFIDENCE_WEIGHTS.get(
                            outcome.confidence, 0.5
                        )
                    utility_count += len(sim.outcomes)
                    confidence_count += len(sim.outcomes)

                if sim.steps:
                    step_sum += len(sim.steps)
                    step_count += 1

        avg_utility = utility_sum / utility_count if utility_count > 0 else 0.0
        avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0.0
        avg_steps = step_sum / step_count if step_count > 0 else 0.0

        return SimulationStats(
            total_models=total_models,
            total_simulations=total_simulations,
            total_outcomes=total_outcomes,
            simulations_by_type=simulations_by_type,
            simulations_by_status=simulations_by_status,
            avg_utility=avg_utility,
            avg_confidence=avg_confidence,
            avg_steps=avg_steps,
        )


# ═══════════════════════════════════════════════════════════
# Module-level Singleton
# ═══════════════════════════════════════════════════════════

_global_mental_simulation_engine: AgentMentalSimulationEngine | None = None
_global_mental_simulation_engine_lock = threading.Lock()


def get_mental_simulation_engine() -> AgentMentalSimulationEngine:
    """Return the process-wide singleton AgentMentalSimulationEngine instance."""
    global _global_mental_simulation_engine
    with _global_mental_simulation_engine_lock:
        if _global_mental_simulation_engine is None:
            _global_mental_simulation_engine = AgentMentalSimulationEngine()
        return _global_mental_simulation_engine


def reset_mental_simulation_engine() -> None:
    """Reset the process-wide singleton, discarding all models and simulations."""
    global _global_mental_simulation_engine
    with _global_mental_simulation_engine_lock:
        _global_mental_simulation_engine = None
