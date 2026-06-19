"""Buddy Self-Evolving Skills — skills that auto-improve through usage

Skills that learn from every execution - tracking success patterns,
generating enhanced variants, and self-optimizing over time. Different
from the static skills registry, these skills have a life cycle of
continuous improvement.
"""
from __future__ import annotations
import logging
import uuid
import math
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.evolving_skills")


# ---------------------------------------------------------------------------
# Core Types
# ---------------------------------------------------------------------------

class SkillEvolutionStage(str, Enum):
    """Stages in a skill's evolutionary lifecycle."""
    SEED = "seed"              # Initial creation, untested
    SPROUTING = "sprouting"    # Run 1-5 times, gathering data
    GROWING = "growing"        # Run 5-20 times, identifying patterns
    MATURING = "maturing"      # Run 20-50 times, stable patterns
    REFINED = "refined"        # Run 50-100 times, highly optimized
    MASTERED = "mastered"      # Run 100+ times, near-optimal


class VariantStrategy(str, Enum):
    """Strategies for creating skill variants."""
    PROMPT_REFINEMENT = "prompt_refinement"     # Tweak prompt wording
    TEMPERATURE_TUNING = "temperature_tuning"   # Adjust temperature
    CONTEXT_EXPANSION = "context_expansion"     # Add context
    CONTEXT_REDUCTION = "context_reduction"     # Reduce context
    CHAIN_INSERTION = "chain_insertion"         # Add intermediate step
    CHAIN_SIMPLIFICATION = "chain_simplification"  # Remove step
    PARAMETER_SWEEP = "parameter_sweep"         # Vary parameters


@dataclass
class ExecutionRecord:
    """Record of a single skill execution."""
    execution_id: str
    skill_id: str
    variant_id: str
    input_summary: str
    output_summary: str
    success: bool
    quality_score: float  # 0.0-1.0
    latency_ms: int
    tokens_used: int
    user_feedback: float | None = None  # -1.0 to 1.0
    error_message: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillVariant:
    """A variant of a skill with specific parameters."""
    variant_id: str
    parent_skill_id: str
    strategy: VariantStrategy
    prompt_template: str
    temperature: float = 0.7
    max_tokens: int = 2048
    success_rate: float = 0.0
    avg_quality: float = 0.0
    avg_latency: float = 0.0
    avg_tokens: float = 0.0
    execution_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used: str | None = None
    is_active: bool = True
    generation: int = 0  # How many generations from the original


@dataclass
class EvolvingSkill:
    """A skill that evolves through usage and feedback."""
    skill_id: str
    name: str
    category: str
    description: str
    original_prompt: str
    stage: SkillEvolutionStage = SkillEvolutionStage.SEED
    variants: list[SkillVariant] = field(default_factory=list)
    execution_history: list[ExecutionRecord] = field(default_factory=list)
    total_executions: int = 0
    total_successes: int = 0
    best_variant_id: str | None = None
    evolution_metrics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_evolved: str | None = None

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_successes / self.total_executions

    @property
    def active_variant(self) -> SkillVariant | None:
        if self.best_variant_id:
            for v in self.variants:
                if v.variant_id == self.best_variant_id and v.is_active:
                    return v
        # Return most successful active variant
        best = None
        best_rate = -1.0
        for v in self.variants:
            if v.is_active and v.success_rate > best_rate:
                best_rate = v.success_rate
                best = v
        return best


# ---------------------------------------------------------------------------
# Variant Generator
# ---------------------------------------------------------------------------

class VariantGenerator:
    """Generates skill variants using different strategies."""

    def generate(
        self,
        skill: EvolvingSkill,
        strategy: VariantStrategy,
        base_variant: SkillVariant | None = None,
    ) -> SkillVariant:
        """Generate a new variant of a skill."""
        base = base_variant or skill.active_variant
        if not base:
            return self._create_seed_variant(skill, 0)

        generation = (base.generation or 0) + 1

        if strategy == VariantStrategy.PROMPT_REFINEMENT:
            return self._refine_prompt(skill, base, generation)
        elif strategy == VariantStrategy.TEMPERATURE_TUNING:
            return self._tune_temperature(base, generation)
        elif strategy == VariantStrategy.CONTEXT_EXPANSION:
            return self._expand_context(base, generation)
        elif strategy == VariantStrategy.CONTEXT_REDUCTION:
            return self._reduce_context(base, generation)
        elif strategy == VariantStrategy.PARAMETER_SWEEP:
            return self._sweep_parameters(base, generation)
        else:
            return self._create_seed_variant(skill, generation)

    def _create_seed_variant(self, skill: EvolvingSkill, generation: int) -> SkillVariant:
        return SkillVariant(
            variant_id=f"var-{uuid.uuid4().hex[:12]}",
            parent_skill_id=skill.skill_id,
            strategy=VariantStrategy.PROMPT_REFINEMENT,
            prompt_template=skill.original_prompt,
            generation=generation,
        )

    def _refine_prompt(self, skill: EvolvingSkill, base: SkillVariant, generation: int) -> SkillVariant:
        """Refine prompt by analyzing successful executions."""
        # Collect successful execution patterns
        successes = [e for e in skill.execution_history[-50:] if e.success]
        if not successes:
            return SkillVariant(
                variant_id=f"var-{uuid.uuid4().hex[:12]}",
                parent_skill_id=skill.skill_id,
                strategy=VariantStrategy.PROMPT_REFINEMENT,
                prompt_template=base.prompt_template,
                temperature=base.temperature,
                max_tokens=base.max_tokens,
                generation=generation,
            )

        # Build refinement hints from successful outputs
        avg_quality = sum(e.quality_score for e in successes) / len(successes)
        if avg_quality < 0.6:
            refined_prompt = base.prompt_template + "\n\nBe more thorough and detailed."
        elif avg_quality < 0.8:
            refined_prompt = base.prompt_template + "\n\nFocus on clarity and precision."
        else:
            refined_prompt = base.prompt_template

        return SkillVariant(
            variant_id=f"var-{uuid.uuid4().hex[:12]}",
            parent_skill_id=skill.skill_id,
            strategy=VariantStrategy.PROMPT_REFINEMENT,
            prompt_template=refined_prompt,
            temperature=base.temperature,
            max_tokens=base.max_tokens,
            generation=generation,
        )

    def _tune_temperature(self, base: SkillVariant, generation: int) -> SkillVariant:
        """Adjust temperature based on performance."""
        new_temp = base.temperature
        if base.success_rate < 0.5:
            new_temp = max(0.1, base.temperature - 0.1)
        elif base.success_rate > 0.9:
            new_temp = min(1.5, base.temperature + 0.1)
        return SkillVariant(
            variant_id=f"var-{uuid.uuid4().hex[:12]}",
            parent_skill_id=base.parent_skill_id,
            strategy=VariantStrategy.TEMPERATURE_TUNING,
            prompt_template=base.prompt_template,
            temperature=new_temp,
            max_tokens=base.max_tokens,
            generation=generation,
        )

    def _expand_context(self, base: SkillVariant, generation: int) -> SkillVariant:
        return SkillVariant(
            variant_id=f"var-{uuid.uuid4().hex[:12]}",
            parent_skill_id=base.parent_skill_id,
            strategy=VariantStrategy.CONTEXT_EXPANSION,
            prompt_template=base.prompt_template,
            temperature=base.temperature,
            max_tokens=base.max_tokens * 2,
            generation=generation,
        )

    def _reduce_context(self, base: SkillVariant, generation: int) -> SkillVariant:
        return SkillVariant(
            variant_id=f"var-{uuid.uuid4().hex[:12]}",
            parent_skill_id=base.parent_skill_id,
            strategy=VariantStrategy.CONTEXT_REDUCTION,
            prompt_template=base.prompt_template,
            temperature=base.temperature,
            max_tokens=max(256, base.max_tokens // 2),
            generation=generation,
        )

    def _sweep_parameters(self, base: SkillVariant, generation: int) -> SkillVariant:
        import random
        return SkillVariant(
            variant_id=f"var-{uuid.uuid4().hex[:12]}",
            parent_skill_id=base.parent_skill_id,
            strategy=VariantStrategy.PARAMETER_SWEEP,
            prompt_template=base.prompt_template,
            temperature=round(random.uniform(0.1, 1.5), 2),
            max_tokens=random.choice([512, 1024, 2048, 4096]),
            generation=generation,
        )


# ---------------------------------------------------------------------------
# Evolution Engine
# ---------------------------------------------------------------------------

class EvolutionEngine:
    """Drives the evolution of skills based on execution data."""

    def __init__(self):
        self.generator = VariantGenerator()
        self._evolution_thresholds = {
            SkillEvolutionStage.SEED: 5,
            SkillEvolutionStage.SPROUTING: 20,
            SkillEvolutionStage.GROWING: 50,
            SkillEvolutionStage.MATURING: 100,
            SkillEvolutionStage.REFINED: 200,
        }

    def should_evolve(self, skill: EvolvingSkill) -> bool:
        """Check if a skill should evolve to the next stage."""
        threshold = self._evolution_thresholds.get(skill.stage, 1000)
        return skill.total_executions >= threshold

    def evolve(self, skill: EvolvingSkill) -> EvolvingSkill:
        """Evolve a skill to the next stage or generate better variants."""
        now = datetime.now(timezone.utc).isoformat()

        # Stage progression
        if self.should_evolve(skill):
            skill.stage = self._next_stage(skill.stage)

        # Generate variants based on current performance
        if skill.success_rate < 0.5:
            # Low success - try different strategies
            new_variant = self.generator.generate(skill, VariantStrategy.TEMPERATURE_TUNING)
            skill.variants.append(new_variant)
            new_variant2 = self.generator.generate(skill, VariantStrategy.PROMPT_REFINEMENT)
            skill.variants.append(new_variant2)
        elif skill.success_rate < 0.8:
            # Moderate success - refine and optimize
            new_variant = self.generator.generate(skill, VariantStrategy.PROMPT_REFINEMENT)
            skill.variants.append(new_variant)
        else:
            # High success - try parameter sweeps for optimization
            new_variant = self.generator.generate(skill, VariantStrategy.PARAMETER_SWEEP)
            skill.variants.append(new_variant)

        # Update best variant
        self._update_best_variant(skill)

        # Update metrics
        skill.last_evolved = now
        skill.evolution_metrics = {
            "stage": skill.stage.value,
            "success_rate": skill.success_rate,
            "variant_count": len(skill.variants),
            "active_variants": sum(1 for v in skill.variants if v.is_active),
            "best_variant_id": skill.best_variant_id,
        }

        return skill

    def _next_stage(self, current: SkillEvolutionStage) -> SkillEvolutionStage:
        stages = list(SkillEvolutionStage)
        try:
            idx = stages.index(current)
            return stages[min(idx + 1, len(stages) - 1)]
        except ValueError:
            return SkillEvolutionStage.SPROUTING

    def _update_best_variant(self, skill: EvolvingSkill):
        """Identify the best performing variant."""
        best_id = None
        best_score = -1.0

        for variant in skill.variants:
            if variant.execution_count < 3:
                continue
            # Composite score: success rate + quality - cost
            cost_penalty = variant.avg_tokens / 10000.0
            score = (variant.success_rate * 0.5 + variant.avg_quality * 0.4 - cost_penalty * 0.1)
            if score > best_score:
                best_score = score
                best_id = variant.variant_id

        skill.best_variant_id = best_id

    def prune_variants(self, skill: EvolvingSkill, max_variants: int = 10):
        """Remove underperforming variants to keep the skill lean."""
        if len(skill.variants) <= max_variants:
            return

        scored = []
        for v in skill.variants:
            score = (v.success_rate * 0.4 + v.avg_quality * 0.3 + v.execution_count / 100.0 * 0.3)
            scored.append((v, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        skill.variants = [v for v, _ in scored[:max_variants]]


# ---------------------------------------------------------------------------
# Self-Evolving Skill Registry
# ---------------------------------------------------------------------------

class SelfEvolvingSkillRegistry:
    """Registry of all self-evolving skills with lifecycle management."""

    def __init__(self):
        self._skills: dict[str, EvolvingSkill] = {}
        self.evolution_engine = EvolutionEngine()
        self._total_executions = 0
        self._total_evolutions = 0

    def create_skill(self, name: str, category: str, description: str, prompt_template: str) -> EvolvingSkill:
        """Create a new evolving skill."""
        skill = EvolvingSkill(
            skill_id=f"skill-{uuid.uuid4().hex[:12]}",
            name=name,
            category=category,
            description=description,
            original_prompt=prompt_template,
        )
        # Create seed variant
        seed = self.evolution_engine.generator.generate(skill, VariantStrategy.PROMPT_REFINEMENT)
        skill.variants.append(seed)
        self._skills[skill.skill_id] = skill
        return skill

    def get_skill(self, skill_id: str) -> EvolvingSkill | None:
        return self._skills.get(skill_id)

    def list_skills(self, category: str | None = None) -> list[EvolvingSkill]:
        if category:
            return [s for s in self._skills.values() if s.category == category]
        return list(self._skills.values())

    def record_execution(
        self,
        skill_id: str,
        variant_id: str,
        input_summary: str,
        output_summary: str,
        success: bool,
        quality_score: float,
        latency_ms: int,
        tokens_used: int,
        user_feedback: float | None = None,
        error_message: str | None = None,
    ) -> ExecutionRecord | None:
        """Record a skill execution and update metrics."""
        skill = self._skills.get(skill_id)
        if not skill:
            return None

        record = ExecutionRecord(
            execution_id=f"exec-{uuid.uuid4().hex[:12]}",
            skill_id=skill_id,
            variant_id=variant_id,
            input_summary=input_summary,
            output_summary=output_summary,
            success=success,
            quality_score=quality_score,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            user_feedback=user_feedback,
            error_message=error_message,
        )

        skill.execution_history.append(record)
        skill.total_executions += 1
        if success:
            skill.total_successes += 1
        self._total_executions += 1

        # Update variant metrics
        for variant in skill.variants:
            if variant.variant_id == variant_id:
                variant.execution_count += 1
                variant.last_used = record.timestamp
                # Exponential moving average
                alpha = 0.1
                variant.success_rate = variant.success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
                variant.avg_quality = variant.avg_quality * (1 - alpha) + quality_score * alpha
                variant.avg_latency = variant.avg_latency * (1 - alpha) + latency_ms * alpha
                variant.avg_tokens = variant.avg_tokens * (1 - alpha) + tokens_used * alpha
                break

        # Check if evolution is needed
        if self.evolution_engine.should_evolve(skill) and skill.total_executions % 10 == 0:
            self.evolution_engine.evolve(skill)
            self._total_evolutions += 1

        # Keep history manageable
        if len(skill.execution_history) > 200:
            skill.execution_history = skill.execution_history[-200:]

        return record

    def get_evolution_summary(self, skill_id: str) -> dict[str, Any]:
        """Get detailed evolution summary for a skill."""
        skill = self._skills.get(skill_id)
        if not skill:
            return {"error": "Skill not found"}

        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "category": skill.category,
            "stage": skill.stage.value,
            "total_executions": skill.total_executions,
            "success_rate": round(skill.success_rate, 3),
            "variant_count": len(skill.variants),
            "best_variant_id": skill.best_variant_id,
            "evolution_metrics": skill.evolution_metrics,
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "strategy": v.strategy.value,
                    "success_rate": round(v.success_rate, 3),
                    "avg_quality": round(v.avg_quality, 3),
                    "avg_latency": round(v.avg_latency, 1),
                    "avg_tokens": round(v.avg_tokens, 1),
                    "execution_count": v.execution_count,
                    "generation": v.generation,
                    "is_active": v.is_active,
                }
                for v in skill.variants
            ],
            "recent_executions": [
                {
                    "execution_id": e.execution_id,
                    "success": e.success,
                    "quality": e.quality_score,
                    "latency_ms": e.latency_ms,
                    "tokens": e.tokens_used,
                    "timestamp": e.timestamp,
                }
                for e in skill.execution_history[-10:]
            ],
        }

    def get_global_stats(self) -> dict[str, Any]:
        """Get global statistics for the evolving skills registry."""
        return {
            "total_skills": len(self._skills),
            "total_executions": self._total_executions,
            "total_evolutions": self._total_evolutions,
            "skills_by_stage": self._count_by_stage(),
            "skills_by_category": self._count_by_category(),
            "top_skills": [
                {
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "stage": s.stage.value,
                    "success_rate": round(s.success_rate, 3),
                    "executions": s.total_executions,
                }
                for s in sorted(
                    self._skills.values(),
                    key=lambda x: x.success_rate,
                    reverse=True,
                )[:10]
            ],
        }

    def _count_by_stage(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for skill in self._skills.values():
            stage = skill.stage.value
            counts[stage] = counts.get(stage, 0) + 1
        return counts

    def _count_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for skill in self._skills.values():
            counts[skill.category] = counts.get(skill.category, 0) + 1
        return counts


# Global instance
evolving_skills = SelfEvolvingSkillRegistry()