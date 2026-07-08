"""Expression router — REST endpoints for the Genome Expression Engine.

Exposes the trait→runtime-parameter translation layer under
``/api/v1/expression/...`` so the frontend can inspect how an agent's
cognitive genome manifests as concrete runtime knobs (temperature,
reasoning depth, retry budget, etc.).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/expression", tags=["expression"])


# ── Helpers ────────────────────────────────────────────

def _get_engine():
    """Lazy import to avoid circular dependencies at module load time."""
    from agent.agent_genome_expression import get_expression_engine
    return get_expression_engine()


# ── Endpoints ──────────────────────────────────────────

@router.get("")
async def list_profiles() -> dict[str, Any]:
    """List all cached expression profiles."""
    engine = _get_engine()
    profiles = engine.list_profiles()
    return {"profiles": profiles, "count": len(profiles)}


@router.get("/catalog")
async def get_parameter_catalog() -> dict[str, Any]:
    """Return the catalogue of all expressible runtime parameters."""
    engine = _get_engine()
    return {"parameters": engine.get_parameter_catalog()}


@router.get("/mapping")
async def get_trait_parameter_map() -> dict[str, Any]:
    """Return the gene→parameter mapping with descriptions."""
    engine = _get_engine()
    return {"mapping": engine.get_trait_parameter_map()}


@router.get("/{agent_id}")
async def get_expression_profile(agent_id: str) -> dict[str, Any]:
    """Return the expression profile for an agent.

    Computes on demand if no cached profile exists. Returns 404 if the
    agent has no genome yet.
    """
    engine = _get_engine()
    profile = engine.get_profile(agent_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No genome found for agent '{agent_id}'")
    return profile.to_dict()


@router.post("/{agent_id}/refresh")
async def refresh_expression_profile(agent_id: str) -> dict[str, Any]:
    """Force recompute the expression profile from the current genome."""
    engine = _get_engine()
    profile = engine.compute_profile(agent_id, source="refresh")
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No genome found for agent '{agent_id}'")
    return {
        "agent_id": agent_id,
        "parameters": profile.parameters,
        "genome_generation": profile.genome_generation,
        "computed_at": profile.computed_at,
        "refreshed": True,
    }


@router.get("/{agent_id}/history")
async def get_expression_history(
    agent_id: str,
    limit: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    """Return the expression event history for an agent."""
    engine = _get_engine()
    history = engine.get_history(agent_id, limit=limit)
    return {"agent_id": agent_id, "history": history, "count": len(history)}


@router.delete("/{agent_id}")
async def invalidate_expression_profile(agent_id: str) -> dict[str, Any]:
    """Drop the cached expression profile — next access recomputes from genome."""
    engine = _get_engine()
    engine.invalidate(agent_id)
    return {"agent_id": agent_id, "invalidated": True}
