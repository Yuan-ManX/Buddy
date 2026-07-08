"""Agent Team Resonance — cognitive DNA-based team formation.

The team resonance engine analyses agent cognitive genomes to find optimal
pairings for collaborative tasks. Two agents "resonate" when their
cognitive profiles complement each other — one's strength offsets the
other's weakness, producing a team that is more capable than either
agent alone.

Resonance is computed on pairs of traits:
  - analytical_depth × creative_divergence  → analysis + ideation
  - caution_bias × uncertainty_tolerance    → prudence + risk appetite
  - persistence × tool_affinity             → endurance + execution
  - collaboration_instinct × abstraction_lean → teamwork + vision
  - temporal_horizon × verbosity            → planning + communication

Each pair produces a resonance score in [0, 1]. The overall team score
is the weighted average across all active pairs. Higher scores indicate
stronger complementary pairing.

The engine also tracks collaboration outcomes — when a team completes a
task, the success/failure signal feeds back into the resonance weights,
so the system learns which trait combinations actually work well together
in practice.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from .agent_logging import get_logger
    _logger = get_logger("team_resonance")
except Exception:
    import logging
    _logger = logging.getLogger("team_resonance")


# ── Trait pair definitions ────────────────────────────

# Each entry: (trait_a, trait_b, weight, description)
# Resonance is highest when one trait is high and the other is low
# (complementary), OR when both are moderate (balanced).
RESONANCE_PAIRS: list[tuple[str, str, float, str]] = [
    ("analytical_depth", "creative_divergence", 1.2,
     "Analysis paired with ideation produces well-grounded innovation"),
    ("caution_bias", "uncertainty_tolerance", 1.0,
     "Prudence balanced with risk appetite enables decisive exploration"),
    ("persistence", "tool_affinity", 0.8,
     "Endurance combined with execution drive completes difficult tasks"),
    ("collaboration_instinct", "abstraction_lean", 0.9,
     "Teamwork instinct paired with vision enables coordinated strategy"),
    ("temporal_horizon", "verbosity", 0.7,
     "Long-range planning with clear communication aligns the team"),
]

# Default weights (can be adjusted by outcome learning)
DEFAULT_PAIR_WEIGHTS: dict[tuple[str, str], float] = {
    (a, b): w for a, b, w, _ in RESONANCE_PAIRS
}


# ── Data classes ───────────────────────────────────────

@dataclass
class TeamResonanceScore:
    """Resonance between two agents."""
    agent_a: str
    agent_b: str
    score: float  # [0, 1]
    pair_scores: dict[str, float] = field(default_factory=dict)
    dominant_synergy: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "score": round(self.score, 4),
            "pair_scores": {k: round(v, 4) for k, v in self.pair_scores.items()},
            "dominant_synergy": self.dominant_synergy,
        }


@dataclass
class TeamRecommendation:
    """Recommended team for a task."""
    task_summary: str
    agents: list[str]
    team_score: float
    pair_scores: list[dict[str, Any]]
    rationale: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_summary": self.task_summary,
            "agents": self.agents,
            "team_score": round(self.team_score, 4),
            "pair_scores": self.pair_scores,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class CollaborationOutcome:
    """Recorded outcome of a collaboration."""
    agents: list[str]
    success: bool
    task_summary: str = ""
    team_score_at_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": self.agents,
            "success": self.success,
            "task_summary": self.task_summary,
            "team_score_at_time": round(self.team_score_at_time, 4),
            "timestamp": self.timestamp,
        }


# ── Team resonance engine ─────────────────────────────

class TeamResonanceEngine:
    """Analyses agent genomes to find optimal collaborative pairings.

    The engine computes pairwise resonance scores based on complementary
    cognitive traits, recommends teams for tasks, and learns from
    collaboration outcomes to refine its recommendations over time.
    """

    MAX_OUTCOMES = 500

    def __init__(self):
        self._pair_weights: dict[tuple[str, str], float] = dict(DEFAULT_PAIR_WEIGHTS)
        self._outcomes: list[CollaborationOutcome] = []
        self._lock = threading.RLock()

    # ── Core scoring ───────────────────────────────────

    @staticmethod
    def _complementary_score(val_a: float, val_b: float) -> float:
        """Score how complementary two trait values are.

        Maximum resonance when one trait is high (>0.6) and the other is
        low (<0.4) — true complementarity. Moderate resonance when both
        are balanced (near 0.5). Lowest when both are extreme in the same
        direction (redundant).
        """
        diff = abs(val_a - val_b)
        avg = (val_a + val_b) / 2.0
        # Complementarity: high when values diverge
        complementarity = diff
        # Balance penalty: penalise when both are extreme (0 or 1)
        balance = 1.0 - abs(avg - 0.5) * 0.5
        return complementarity * 0.6 + balance * 0.4

    def compute_pair_score(self, agent_a: str, agent_b: str) -> Optional[TeamResonanceScore]:
        """Compute resonance between two agents based on their genomes."""
        from .agent_cognitive_genome import get_genome_manager

        mgr = get_genome_manager()
        genome_a = mgr.get_genome(agent_a)
        genome_b = mgr.get_genome(agent_b)
        if genome_a is None or genome_b is None:
            return None

        pair_scores: dict[str, float] = {}
        weighted_sum = 0.0
        total_weight = 0.0
        best_pair_key = ""
        best_pair_score = -1.0

        for trait_a, trait_b, weight, description in RESONANCE_PAIRS:
            if trait_a not in genome_a.genes or trait_b not in genome_b.genes:
                continue
            val_a = genome_a.genes[trait_a].value
            val_b = genome_b.genes[trait_b].value
            raw_score = self._complementary_score(val_a, val_b)

            # Also compute the reverse direction (trait_b from A, trait_a from B)
            if trait_b in genome_a.genes and trait_a in genome_b.genes:
                val_a_rev = genome_a.genes[trait_b].value
                val_b_rev = genome_b.genes[trait_a].value
                raw_score = (raw_score + self._complementary_score(val_a_rev, val_b_rev)) / 2.0

            pair_key = f"{trait_a}×{trait_b}"
            pair_scores[pair_key] = raw_score
            weighted_sum += raw_score * weight
            total_weight += weight

            if raw_score > best_pair_score:
                best_pair_score = raw_score
                best_pair_key = pair_key

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Find the dominant synergy description
        dominant_synergy = ""
        for trait_a, trait_b, _, desc in RESONANCE_PAIRS:
            if f"{trait_a}×{trait_b}" == best_pair_key:
                dominant_synergy = desc
                break

        return TeamResonanceScore(
            agent_a=agent_a,
            agent_b=agent_b,
            score=overall,
            pair_scores=pair_scores,
            dominant_synergy=dominant_synergy,
        )

    def get_best_partners(self, agent_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return the top-N best partners for an agent."""
        from .agent_cognitive_genome import get_genome_manager

        mgr = get_genome_manager()
        all_genomes = mgr.list_genomes()
        partner_ids = [g["agent_id"] for g in all_genomes if g["agent_id"] != agent_id]

        scores: list[TeamResonanceScore] = []
        for pid in partner_ids:
            score = self.compute_pair_score(agent_id, pid)
            if score is not None:
                scores.append(score)

        scores.sort(key=lambda s: s.score, reverse=True)
        return [s.to_dict() for s in scores[:limit]]

    def compute_matrix(self) -> dict[str, Any]:
        """Compute the full resonance matrix across all agents."""
        from .agent_cognitive_genome import get_genome_manager

        mgr = get_genome_manager()
        all_genomes = mgr.list_genomes()
        agent_ids = [g["agent_id"] for g in all_genomes]

        pairs: list[dict[str, Any]] = []
        for i, a in enumerate(agent_ids):
            for b in agent_ids[i + 1:]:
                score = self.compute_pair_score(a, b)
                if score is not None:
                    pairs.append(score.to_dict())

        return {
            "agents": agent_ids,
            "pairs": pairs,
            "pair_count": len(pairs),
        }

    # ── Team recommendation ────────────────────────────

    def recommend_team(
        self,
        task_summary: str,
        team_size: int = 2,
        candidate_ids: Optional[list[str]] = None,
    ) -> Optional[TeamRecommendation]:
        """Recommend the best team for a task.

        Uses a greedy algorithm: start with the agent whose genome is most
        balanced, then iteratively add the agent that maximises the team's
        average pairwise resonance.
        """
        from .agent_cognitive_genome import get_genome_manager

        mgr = get_genome_manager()
        all_genomes = mgr.list_genomes()

        if candidate_ids:
            pool = [g for g in all_genomes if g["agent_id"] in candidate_ids]
        else:
            pool = all_genomes

        if len(pool) < team_size:
            team_size = len(pool)

        if team_size < 2:
            return None

        # Start with the most balanced agent (closest to 0.5 on all traits)
        def balance_score(genome_dict: dict) -> float:
            genes = genome_dict.get("genes", {})
            if not genes:
                return 0.0
            return 1.0 - sum(abs(g.get("value", 0.5) - 0.5) for g in genes.values()) / len(genes)

        pool_sorted = sorted(pool, key=balance_score, reverse=True)
        selected = [pool_sorted[0]["agent_id"]]
        remaining = [g["agent_id"] for g in pool_sorted[1:]]

        while len(selected) < team_size and remaining:
            best_candidate = None
            best_avg_score = -1.0

            for candidate in remaining:
                scores = []
                for s in selected:
                    pair = self.compute_pair_score(s, candidate)
                    if pair is not None:
                        scores.append(pair.score)
                avg = sum(scores) / len(scores) if scores else 0.0
                if avg > best_avg_score:
                    best_avg_score = avg
                    best_candidate = candidate

            if best_candidate is None:
                break
            selected.append(best_candidate)
            remaining.remove(best_candidate)

        # Compute final pair scores
        pair_scores: list[dict[str, Any]] = []
        for i, a in enumerate(selected):
            for b in selected[i + 1:]:
                score = self.compute_pair_score(a, b)
                if score is not None:
                    pair_scores.append(score.to_dict())

        team_score = sum(p["score"] for p in pair_scores) / len(pair_scores) if pair_scores else 0.0

        rationale = self._build_rationale(selected, pair_scores, task_summary)

        return TeamRecommendation(
            task_summary=task_summary,
            agents=selected,
            team_score=team_score,
            pair_scores=pair_scores,
            rationale=rationale,
        )

    @staticmethod
    def _build_rationale(agents: list[str], pair_scores: list[dict], task: str) -> str:
        """Generate a human-readable rationale for the team selection."""
        if not pair_scores:
            return f"Team of {len(agents)} agents selected for task: {task[:80]}"

        best = max(pair_scores, key=lambda p: p["score"])
        worst = min(pair_scores, key=lambda p: p["score"])

        parts = [
            f"Team selected for: {task[:80]}",
            f"Strongest synergy: {best['agent_a']} + {best['agent_b']} ({best['score']:.2f})",
        ]
        if best.get("dominant_synergy"):
            parts.append(f"  -> {best['dominant_synergy']}")
        parts.append(f"Weakest pairing: {worst['agent_a']} + {worst['agent_b']} ({worst['score']:.2f})")
        return " | ".join(parts)

    # ── Outcome tracking ───────────────────────────────

    def record_outcome(
        self,
        agents: list[str],
        success: bool,
        task_summary: str = "",
    ) -> dict[str, Any]:
        """Record a collaboration outcome and adjust pair weights."""
        # Compute team score at time of outcome
        pair_scores = []
        for i, a in enumerate(agents):
            for b in agents[i + 1:]:
                score = self.compute_pair_score(a, b)
                if score is not None:
                    pair_scores.append(score)

        team_score = sum(s.score for s in pair_scores) / len(pair_scores) if pair_scores else 0.0

        outcome = CollaborationOutcome(
            agents=agents,
            success=success,
            task_summary=task_summary,
            team_score_at_time=team_score,
        )

        with self._lock:
            self._outcomes.append(outcome)
            if len(self._outcomes) > self.MAX_OUTCOMES:
                self._outcomes = self._outcomes[-self.MAX_OUTCOMES:]

        # Learn: if the team scored high but failed, reduce the weight of
        # the dominant pair; if scored low but succeeded, increase it.
        adjustment = 0.0
        if success and team_score < 0.4:
            adjustment = 0.02  # Underestimated synergy
        elif not success and team_score > 0.6:
            adjustment = -0.02  # Overestimated synergy

        if adjustment != 0.0:
            with self._lock:
                for score in pair_scores:
                    for pair_key in score.pair_scores:
                        for (ta, tb), _ in DEFAULT_PAIR_WEIGHTS.items():
                            if f"{ta}×{tb}" == pair_key:
                                old = self._pair_weights.get((ta, tb), 1.0)
                                self._pair_weights[(ta, tb)] = max(0.1, old + adjustment)

        return {
            "recorded": True,
            "team_score": round(team_score, 4),
            "success": success,
            "weight_adjustment": round(adjustment, 4),
        }

    def get_outcomes(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return [o.to_dict() for o in self._outcomes[-limit:]]

    # ── Stats ──────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            total_outcomes = len(self._outcomes)
            successes = sum(1 for o in self._outcomes if o.success)
            avg_score = (
                sum(o.team_score_at_time for o in self._outcomes) / total_outcomes
                if total_outcomes > 0
                else 0.0
            )

        return {
            "total_outcomes": total_outcomes,
            "successful": successes,
            "failed": total_outcomes - successes,
            "success_rate": round(successes / total_outcomes, 4) if total_outcomes > 0 else 0.0,
            "avg_team_score": round(avg_score, 4),
            "pair_count": len(RESONANCE_PAIRS),
            "pair_descriptions": {
                f"{a}×{b}": desc for a, b, _, desc in RESONANCE_PAIRS
            },
        }

    def get_pair_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "trait_a": a,
                "trait_b": b,
                "weight": w,
                "description": desc,
            }
            for a, b, w, desc in RESONANCE_PAIRS
        ]


# ── Singleton accessor ─────────────────────────────────

_manager: Optional[TeamResonanceEngine] = None
_singleton_lock = threading.Lock()


def get_team_resonance_engine() -> TeamResonanceEngine:
    """Return the process-wide TeamResonanceEngine singleton."""
    global _manager
    if _manager is None:
        with _singleton_lock:
            if _manager is None:
                _manager = TeamResonanceEngine()
    return _manager


def reset_team_resonance_engine() -> TeamResonanceEngine:
    """Reset the singleton — primarily for tests."""
    global _manager
    with _singleton_lock:
        _manager = TeamResonanceEngine()
    return _manager
