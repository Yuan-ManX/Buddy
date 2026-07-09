"""Cognitive Composer router — composition management and evaluation endpoints

Exposes the CognitiveComposer (cross-engine fusion layer) over HTTP so the
frontend and external callers can list, register, and evaluate compositions.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/cognitive/composer", tags=["cognitive-composer"])


class CompositionSpec(BaseModel):
    name: str = Field(..., description="Unique composition name")
    engine_weights: dict[str, float] = Field(default_factory=dict)
    fusion_strategy: str = Field("weighted_avg", description="weighted_avg | max_confidence | voting")
    description: str = ""


class EvaluateRequest(BaseModel):
    agent_id: str
    composition_name: str = "holistic"


@router.get("/compositions")
async def list_compositions() -> dict:
    """List all registered composition names with their metadata."""
    try:
        from agent.shared import cognitive_composer
        names = cognitive_composer.list_compositions()
        out = []
        for name in names:
            comp = cognitive_composer.get_composition(name)
            out.append({
                "name": name,
                "fusion_strategy": comp.fusion_strategy if comp else "weighted_avg",
                "engine_count": len(comp.engine_weights) if comp else 0,
                "description": comp.description if comp else "",
            })
        return {"compositions": out}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/compositions")
async def register_composition(spec: CompositionSpec) -> dict:
    """Register a new named composition."""
    try:
        from agent.shared import cognitive_composer, CognitiveComposition
        comp = CognitiveComposition(
            name=spec.name,
            engine_weights=spec.engine_weights,
            fusion_strategy=spec.fusion_strategy,  # type: ignore[arg-type]
            description=spec.description,
        )
        ok = cognitive_composer.register_composition(comp)
        if not ok:
            raise HTTPException(status_code=409, detail=f"composition '{spec.name}' already exists")
        return {"ok": True, "name": spec.name}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/compositions/{name}")
async def remove_composition(name: str) -> dict:
    """Remove a named composition (built-ins cannot be removed)."""
    try:
        from agent.shared import cognitive_composer
        if name in ("holistic", "analytical", "creative"):
            raise HTTPException(status_code=400, detail="cannot remove built-in composition")
        ok = cognitive_composer.remove_composition(name)
        if not ok:
            raise HTTPException(status_code=404, detail=f"composition '{name}' not found")
        return {"ok": True, "removed": name}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/evaluate")
async def evaluate(req: EvaluateRequest) -> dict:
    """Evaluate a named composition for a given agent."""
    try:
        from agent.shared import cognitive_composer
        result = cognitive_composer.evaluate(req.agent_id, req.composition_name)
        return {
            "composition_name": result.composition_name,
            "agent_id": result.agent_id,
            "fusion_strategy": result.fusion_strategy,
            "fused_score": result.fused_score,
            "fused_regime": result.fused_regime,
            "contributing_engines": result.contributing_engines,
            "engine_results": result.engine_results,
            "notes": result.notes,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/engines")
async def list_engines() -> dict:
    """List all themed cognitive engines discovered by the bridge."""
    try:
        from agent.shared import cognitive_bridge
        keys = cognitive_bridge.list_engines()
        return {"engines": keys, "count": len(keys)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/profile/{agent_id}")
async def get_profile(agent_id: str) -> dict:
    """Return the aggregate cognitive profile for an agent."""
    try:
        from agent.shared import cognitive_bridge
        return cognitive_bridge.get_agent_cognitive_profile(agent_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
