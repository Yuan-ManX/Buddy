"""Buddy Cognitive Bridge — wires themed cognitive engines into the agent platform

The CognitiveBridge is the integration layer between the 85 themed cognitive
engines (vortex, prism, tide, tundra, fjord, ...) and the rest of the agent
platform (orchestrator, memory, tools, reasoning). It exposes a unified
dispatch interface so that orchestrator/memory/tools/reasoning can consult
cognitive state without knowing each engine's individual API.

Core capabilities:
  - Auto-discovery of themed engines from agent.shared singletons
  - Unified profile aggregation across all engines for a given agent
  - Single-event dispatch to the correct engine by engine_key
  - Delegation consultation for orchestrator expertise routing
  - Snapshot persistence hook (delegates to observability + DB layer)
  - Thread-safe singleton with reset support for tests
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("buddy.cognitive_bridge")


@dataclass
class EngineInfo:
    """Metadata for a discovered themed cognitive engine."""

    engine_key: str            # public slug, e.g. "vortex", "prism"
    singleton: Any             # the engine instance from agent.shared
    secondary_singular: str    # e.g. "convergence" (record_convergence)
    tertiary_singular: str     # e.g. "spiral" (record_spiral_shift)


@dataclass
class DelegationAdvice:
    """Recommendation returned by consult_for_delegation."""

    agent_id: str
    recommended_engine: str
    confidence: float
    rationale: str
    profile_summary: Dict[str, Any] = field(default_factory=dict)


class CognitiveBridge:
    """Singleton bridge aggregating all themed cognitive engines.

    Engines are discovered by scanning agent.shared for attributes ending in
    "_engine" whose value exposes a `record_reading` callable. This auto-
    discovery keeps the bridge in sync as new themed engines are added
    without requiring manual registration.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._engines: Dict[str, EngineInfo] = {}
        self._last_profile_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds: float = 5.0
        self._cache_timestamps: Dict[str, float] = {}
        self._discover_engines()

    def _discover_engines(self) -> None:
        """Populate self._engines by scanning agent.shared for themed engines.

        A themed engine is identified by:
          1. An attribute on agent.shared ending in "_engine"
          2. The attribute value exposes a callable `record_reading`
          3. The attribute name (minus "_engine" suffix) is the engine_key
        """
        try:
            from agent import shared
        except Exception as exc:  # pragma: no cover - import guarded for tests
            logger.warning("CognitiveBridge could not import agent.shared: %s", exc)
            return

        for attr_name in dir(shared):
            if not attr_name.endswith("_engine"):
                continue
            singleton = getattr(shared, attr_name, None)
            if singleton is None:
                continue
            if not hasattr(singleton, "record_reading"):
                continue
            engine_key = attr_name[: -len("_engine")]
            secondary = self._detect_secondary(singleton, engine_key)
            tertiary = self._detect_tertiary(singleton, engine_key)
            self._engines[engine_key] = EngineInfo(
                engine_key=engine_key,
                singleton=singleton,
                secondary_singular=secondary,
                tertiary_singular=tertiary,
            )

        logger.info(
            "CognitiveBridge discovered %d themed cognitive engines",
            len(self._engines),
        )

    @staticmethod
    def _detect_secondary(singleton: Any, engine_key: str) -> str:
        """Infer the secondary record method name (e.g. 'convergence').

        Themed engines expose record_<secondary> in addition to record_reading.
        We scan public methods matching record_<word> and pick the first that
        is not 'reading' and does not end with '_shift'.
        """
        candidates: List[str] = []
        for attr in dir(singleton):
            if not attr.startswith("record_"):
                continue
            tail = attr[len("record_"):]
            if tail == "reading":
                continue
            if tail.endswith("_shift"):
                continue
            candidates.append(tail)
        if not candidates:
            return "event"
        return candidates[0]

    @staticmethod
    def _detect_tertiary(singleton: Any, engine_key: str) -> str:
        """Infer the tertiary shift method name (e.g. 'spiral').

        Themed engines expose record_<tertiary>_shift. We scan public methods
        matching record_<word>_shift and return <word>.
        """
        for attr in dir(singleton):
            if not attr.startswith("record_") or not attr.endswith("_shift"):
                continue
            middle = attr[len("record_") : -len("_shift")]
            if not middle:
                continue
            return middle
        return "phase"

    # ── Public API ────────────────────────────────────────────

    def list_engines(self) -> List[str]:
        """Return the sorted list of discovered engine keys."""
        with self._lock:
            return sorted(self._engines.keys())

    def get_engine_info(self, engine_key: str) -> Optional[EngineInfo]:
        """Return the EngineInfo for a given key, or None if unknown."""
        with self._lock:
            return self._engines.get(engine_key)

    def get_agent_cognitive_profile(self, agent_id: str) -> Dict[str, Any]:
        """Aggregate the latest cognitive profile across all engines.

        Returns a dict shaped like:
            {
              "agent_id": "...",
              "engines": {
                 "vortex": { "regime": "...", "score": 0.42, ... },
                 "prism":  { ... },
              },
              "dominant_engine": "vortex",
              "average_score": 0.42,
              "engine_count": 18,
            }

        Engines that raise on get_profile are silently skipped so one
        broken engine does not poison the aggregate.
        """
        with self._lock:
            cached = self._try_cache(agent_id)
            if cached is not None:
                return cached

        profile: Dict[str, Any] = {
            "agent_id": agent_id,
            "engines": {},
            "dominant_engine": None,
            "average_score": 0.0,
            "engine_count": 0,
        }
        scores: List[float] = []
        with self._lock:
            for key, info in self._engines.items():
                try:
                    snapshot = info.singleton.get_profile(agent_id)
                    if snapshot is None:
                        continue
                    entry = self._profile_to_dict(snapshot, key)
                    profile["engines"][key] = entry
                    score = entry.get("score")
                    if isinstance(score, (int, float)):
                        scores.append(float(score))
                except Exception as exc:
                    logger.debug(
                        "engine %s get_profile failed for %s: %s",
                        key, agent_id, exc,
                    )
                    continue

        profile["engine_count"] = len(profile["engines"])
        if scores:
            profile["average_score"] = sum(scores) / len(scores)
        if profile["engines"]:
            profile["dominant_engine"] = max(
                profile["engines"].items(),
                key=lambda kv: kv[1].get("score", 0.0) if isinstance(kv[1].get("score"), (int, float)) else 0.0,
            )[0]

        with self._lock:
            self._last_profile_cache[agent_id] = profile
            self._cache_timestamps[agent_id] = time.time()
        return profile

    @staticmethod
    def _profile_to_dict(snapshot: Any, engine_key: str) -> Dict[str, Any]:
        """Normalize a profile/snapshot object to a JSON-friendly dict."""
        if isinstance(snapshot, dict):
            return dict(snapshot)
        if hasattr(snapshot, "to_dict"):
            try:
                return dict(snapshot.to_dict())
            except Exception:
                pass
        if hasattr(snapshot, "__dict__"):
            return {k: v for k, v in vars(snapshot).items() if not k.startswith("_")}
        return {"value": str(snapshot)}

    def record_cognitive_event(
        self,
        agent_id: str,
        engine_key: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch a cognitive event to the correct engine.

        event_type is one of: "reading", "secondary", "snapshot", "plan",
        "shift". The payload is forwarded to the matching engine method.
        """
        info = self.get_engine_info(engine_key)
        if info is None:
            return {
                "ok": False,
                "error": f"unknown engine_key: {engine_key}",
            }

        method_name = self._resolve_event_method(info, event_type)
        if method_name is None:
            return {
                "ok": False,
                "error": f"unsupported event_type: {event_type}",
            }

        method = getattr(info.singleton, method_name, None)
        if method is None or not callable(method):
            return {
                "ok": False,
                "error": f"engine {engine_key} has no method {method_name}",
            }

        call_payload = dict(payload)
        call_payload.setdefault("agent_id", agent_id)

        try:
            result = method(**call_payload) if isinstance(call_payload, dict) else method(call_payload)
            self._invalidate_cache(agent_id)
            return {"ok": True, "result": self._profile_to_dict(result, engine_key)}
        except Exception as exc:
            logger.warning(
                "engine %s %s failed: %s", engine_key, method_name, exc,
            )
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _resolve_event_method(info: EngineInfo, event_type: str) -> Optional[str]:
        """Map an event_type to the matching engine method name."""
        if event_type == "reading":
            return "record_reading"
        if event_type == "secondary":
            return f"record_{info.secondary_singular}"
        if event_type == "snapshot":
            return "take_snapshot"
        if event_type == "plan":
            return f"plan_{info.secondary_singular}"
        if event_type == "shift":
            return f"record_{info.tertiary_singular}_shift"
        return None

    def consult_for_delegation(
        self,
        agent_id: str,
        task_domain: str = "",
    ) -> DelegationAdvice:
        """Return a delegation recommendation for the orchestrator.

        The recommendation picks the engine whose current regime best matches
        the task_domain keyword. If no domain hint is given, the engine with
        the highest average score is recommended.
        """
        profile = self.get_agent_cognitive_profile(agent_id)
        engines = profile.get("engines", {})

        if not engines:
            return DelegationAdvice(
                agent_id=agent_id,
                recommended_engine="vortex",
                confidence=0.0,
                rationale="no cognitive profile available; using default engine",
            )

        domain_lower = (task_domain or "").lower()
        best_engine: Optional[str] = None
        best_score: float = -1.0
        rationale = "highest cognitive score across engines"

        if domain_lower:
            for key, entry in engines.items():
                regime = str(entry.get("regime") or entry.get("dominant_regime") or "").lower()
                if domain_lower in regime or regime in domain_lower:
                    score = float(entry.get("score", 0.0) or 0.0)
                    if score > best_score:
                        best_score = score
                        best_engine = key
                        rationale = f"regime '{regime}' matches domain '{domain_lower}'"

        if best_engine is None:
            best_engine = profile.get("dominant_engine") or next(iter(engines.keys()))
            best_score = float(engines.get(best_engine, {}).get("score", 0.0) or 0.0)

        confidence = max(0.0, min(1.0, best_score))
        return DelegationAdvice(
            agent_id=agent_id,
            recommended_engine=best_engine,
            confidence=confidence,
            rationale=rationale,
            profile_summary={
                "engine_count": profile.get("engine_count", 0),
                "average_score": profile.get("average_score", 0.0),
                "dominant_engine": profile.get("dominant_engine"),
            },
        )

    def take_snapshot(self, agent_id: str, engine_key: str) -> Dict[str, Any]:
        """Take a snapshot on the specified engine and persist it.

        Persistence is delegated to the observability/DB layer when
        available; failures do not block the snapshot itself.
        """
        info = self.get_engine_info(engine_key)
        if info is None:
            return {"ok": False, "error": f"unknown engine_key: {engine_key}"}

        try:
            snapshot = info.singleton.take_snapshot(agent_id)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        snapshot_dict = self._profile_to_dict(snapshot, engine_key)
        snapshot_id = str(uuid.uuid4())
        snapshot_dict["snapshot_id"] = snapshot_id
        snapshot_dict["engine_key"] = engine_key
        snapshot_dict["agent_id"] = agent_id

        self._persist_snapshot(snapshot_id, agent_id, engine_key, snapshot_dict)
        self._invalidate_cache(agent_id)
        return {"ok": True, "result": snapshot_dict}

    def _persist_snapshot(
        self,
        snapshot_id: str,
        agent_id: str,
        engine_key: str,
        payload: Dict[str, Any],
    ) -> None:
        """Best-effort persistence of a cognitive snapshot to SQLite."""
        try:
            import asyncio
            import json

            from database.db import async_session
            from database.models import CognitiveSnapshot

            async def _write():
                async with async_session() as session:
                    row = CognitiveSnapshot(
                        id=snapshot_id,
                        agent_id=agent_id,
                        engine_key=engine_key,
                        regime=str(payload.get("regime") or payload.get("dominant_regime") or ""),
                        payload=json.dumps(payload, default=str),
                    )
                    session.add(row)
                    await session.commit()

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                asyncio.ensure_future(_write(), loop=loop)
            else:
                asyncio.run(_write())
        except Exception as exc:
            logger.debug("snapshot persistence skipped: %s", exc)

    # ── Cache helpers ─────────────────────────────────────────

    def _try_cache(self, agent_id: str) -> Optional[Dict[str, Any]]:
        if self._cache_ttl_seconds <= 0:
            return None
        ts = self._cache_timestamps.get(agent_id, 0.0)
        if time.time() - ts > self._cache_ttl_seconds:
            return None
        cached = self._last_profile_cache.get(agent_id)
        if cached is None:
            return None
        return dict(cached)

    def _invalidate_cache(self, agent_id: str) -> None:
        with self._lock:
            self._last_profile_cache.pop(agent_id, None)
            self._cache_timestamps.pop(agent_id, None)

    # ── Singleton plumbing ────────────────────────────────────

    def reset(self) -> None:
        """Reset the bridge state (for tests)."""
        with self._lock:
            self._engines.clear()
            self._last_profile_cache.clear()
            self._cache_timestamps.clear()
        self._discover_engines()


# ── Module-level singleton ─────────────────────────────────────

_bridge: Optional[CognitiveBridge] = None
_bridge_lock = threading.Lock()


def get_cognitive_bridge() -> CognitiveBridge:
    """Return the process-wide CognitiveBridge singleton."""
    global _bridge
    if _bridge is None:
        with _bridge_lock:
            if _bridge is None:
                _bridge = CognitiveBridge()
    return _bridge


def reset_cognitive_bridge() -> None:
    """Reset the singleton (for tests)."""
    global _bridge
    with _bridge_lock:
        if _bridge is not None:
            _bridge.reset()
        _bridge = None
