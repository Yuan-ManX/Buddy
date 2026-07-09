"""Cognitive History router — persisted snapshot history endpoint

Allows callers to query the SQLite-persisted cognitive snapshots for a
given agent + engine pair, with optional time-range filtering.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, desc

router = APIRouter(prefix="/cognitive", tags=["cognitive-history"])


@router.get("/{engine_key}/snapshots/{agent_id}/history")
async def snapshot_history(
    engine_key: str,
    agent_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Return persisted cognitive snapshots for an agent+engine pair."""
    try:
        from database.db import async_session
        from database.models import CognitiveSnapshot
        import json

        async with async_session() as session:
            stmt = (
                select(CognitiveSnapshot)
                .where(
                    CognitiveSnapshot.agent_id == agent_id,
                    CognitiveSnapshot.engine_key == engine_key,
                )
                .order_by(desc(CognitiveSnapshot.created_at))
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        items = []
        for row in rows:
            try:
                payload = json.loads(row.payload) if row.payload else {}
            except Exception:
                payload = {"raw": row.payload}
            items.append({
                "id": row.id,
                "agent_id": row.agent_id,
                "engine_key": row.engine_key,
                "regime": row.regime,
                "payload": payload,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        return {
            "engine_key": engine_key,
            "agent_id": agent_id,
            "count": len(items),
            "items": items,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{engine_key}/snapshots/{agent_id}/latest")
async def latest_snapshot(engine_key: str, agent_id: str) -> dict:
    """Return the most recent persisted snapshot for an agent+engine pair."""
    try:
        from database.db import async_session
        from database.models import CognitiveSnapshot
        import json

        async with async_session() as session:
            stmt = (
                select(CognitiveSnapshot)
                .where(
                    CognitiveSnapshot.agent_id == agent_id,
                    CognitiveSnapshot.engine_key == engine_key,
                )
                .order_by(desc(CognitiveSnapshot.created_at))
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalars().first()

        if row is None:
            raise HTTPException(status_code=404, detail="no snapshot found")

        try:
            payload = json.loads(row.payload) if row.payload else {}
        except Exception:
            payload = {"raw": row.payload}

        return {
            "id": row.id,
            "agent_id": row.agent_id,
            "engine_key": row.engine_key,
            "regime": row.regime,
            "payload": payload,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
