"""Cognitive Engine Routes — dynamically generated CRUD routes for all themed engines.

At import time, the CognitiveBridge discovers all themed engine singletons.
For each engine, this module introspects the singleton's list_/get_ methods to
derive the canonical noun for each collection, then registers POST/GET routes.
Both engine-specific URLs (e.g. /api/refraction/spectrum) and standardized URLs
(e.g. /api/canyon/plan, /api/aurora/shift) are registered so tests from every
round continue to pass.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("buddy.cognitive_engines")

router = APIRouter(prefix="/api", tags=["cognitive-engines"])


class EngineRequestBody(BaseModel):
    """Generic request body — all fields pass through to the engine method."""
    agent_id: str = ""
    model_config = {"extra": "allow"}


# ── Infrastructure method names that never get POST routes ────────────

_INFRA_METHODS: Set[str] = {
    "reset",
    "get_profile",
    "list_profiles",
    "update_profile",
    "get_stats",
    "take_snapshot",
    "list_snapshots",
    "get_snapshot",
    "get_reading",
    "list_readings",
    "get_plan",
    "list_plans",
    "record_reading",
}

_VERB_PREFIXES = (
    "record_",
    "capture_",
    "apply_",
    "measure_",
    "detect_",
    "rotate_",
    "mount_",
    "register_",
    "emit_",
    "trigger_",
)


# ── Noun helpers ──────────────────────────────────────────────────────


def _singularize(plural: str) -> str:
    """Best-effort singularize an English plural noun."""
    if plural.endswith("ies") and len(plural) > 3:
        return plural[:-3] + "y"
    if plural.endswith("s") and not plural.endswith("ss"):
        return plural[:-1]
    return plural


def _resolve_singular(singleton: Any, plural: str) -> str:
    """Determine the singular noun by checking get_<singular> candidates.

    The default singularize handles most cases, but words like 'focuses'
    (singular 'focus') and 'pulses' (singular 'pulse') need different
    rules. We try several candidates and pick the one whose get_<singular>
    method exists on the singleton.
    """
    candidates: List[str] = []
    if plural.endswith("ies") and len(plural) > 3:
        candidates.append(plural[:-3] + "y")
    if plural.endswith("ses") and len(plural) > 4:
        candidates.append(plural[:-2])  # focuses -> focus
        candidates.append(plural[:-1])  # pulses -> pulse
    if plural.endswith("s") and not plural.endswith("ss"):
        candidates.append(plural[:-1])
    candidates.append(plural)

    for c in candidates:
        if hasattr(singleton, f"get_{c}"):
            return c
    return candidates[0] if candidates else plural


def _verb_from_noun(noun: str) -> Optional[str]:
    """Derive a verb stem from a noun (rotation -> rotate, detection -> detect)."""
    if noun.endswith("tion"):
        base = noun[:-3]  # rotation -> rotat, detection -> detecte
        if base.endswith("e"):
            return base  # detecte -> detecte (won't match, fallback below)
        return base + "e"  # rotat -> rotate
    if noun.endswith("sion"):
        return noun[:-3] + "d"
    if noun.endswith("ance"):
        return noun[:-4]
    if noun.endswith("ence"):
        return noun[:-4]
    return None


def _noun_stem(noun: str) -> str:
    """Return the first min(5, len) chars of a noun for prefix matching."""
    return noun[:5] if len(noun) >= 5 else noun


def _is_list_method(name: str) -> bool:
    return name.startswith("list_") and name != "list_"


def _is_get_method(name: str) -> bool:
    return name.startswith("get_") and name != "get_"


def _is_plan_method(name: str) -> bool:
    return name.startswith("plan_") and name != "plan_"


def _list_plural(name: str) -> str:
    """Return the plural noun from a list_<plural> method name."""
    return name[len("list_"):]


def _get_singular(name: str) -> str:
    """Return the singular noun from a get_<noun> method name."""
    return name[len("get_"):]


def _plan_word(name: str) -> str:
    """Return the word from a plan_<word> method name."""
    return name[len("plan_"):]


# ── Action method discovery ───────────────────────────────────────────


def _find_action_method(
    singleton: Any,
    singular: str,
    excluded: Set[str],
) -> Optional[str]:
    """Find the POST action method for a singular noun.

    Tries (in order):
      1. record_<singular>
      2. any non-infra method ending with _<singular>
      3. verb-form matching: rotation -> rotate_*
      4. stem matching: detection -> detect_* (first 5 chars)
      5. first remaining unmatched non-infra callable
    """
    # 1. record_<singular>
    candidate = f"record_{singular}"
    if hasattr(singleton, candidate) and candidate not in excluded:
        return candidate

    # 2. any method ending with _<singular>
    for attr in dir(singleton):
        if attr.startswith("_") or attr in excluded or attr in _INFRA_METHODS:
            continue
        if not callable(getattr(singleton, attr)):
            continue
        if attr.endswith(f"_{singular}") and not _is_list_method(attr) and not _is_get_method(attr):
            return attr

    # 3. verb-form matching (rotation -> rotate_*)
    verb = _verb_from_noun(singular)
    if verb:
        for attr in dir(singleton):
            if attr.startswith("_") or attr in excluded or attr in _INFRA_METHODS:
                continue
            if not callable(getattr(singleton, attr)):
                continue
            if attr.startswith(f"{verb}_") and not _is_list_method(attr) and not _is_get_method(attr):
                return attr

    # 4. stem matching (detection -> detect_*)
    stem = _noun_stem(singular)
    if stem and len(stem) >= 4:
        for attr in dir(singleton):
            if attr.startswith("_") or attr in excluded or attr in _INFRA_METHODS:
                continue
            if not callable(getattr(singleton, attr)):
                continue
            if _is_list_method(attr) or _is_get_method(attr) or _is_plan_method(attr):
                continue
            if attr.startswith(stem) and not _is_list_method(attr) and not _is_get_method(attr):
                return attr

    # 5. first remaining unmatched action method
    for attr in sorted(dir(singleton)):
        if attr.startswith("_") or attr in excluded or attr in _INFRA_METHODS:
            continue
        if not callable(getattr(singleton, attr)):
            continue
        if _is_list_method(attr) or _is_get_method(attr) or _is_plan_method(attr):
            continue
        if attr == "take_snapshot":
            continue
        return attr
    return None


# ── Response normalization ────────────────────────────────────────────


def _to_dict(obj: Any) -> Any:
    """Normalize an engine return value to a JSON-friendly structure."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict()
        except Exception:
            pass
    if isinstance(obj, list):
        return [_to_dict(x) for x in obj]
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return obj


def _wrap_list(items: List[Any]) -> Dict[str, Any]:
    """Wrap a list into the {total, items} envelope tests expect."""
    wrapped = [_to_dict(x) for x in items]
    return {"total": len(wrapped), "items": wrapped}


# ── Handler factories ─────────────────────────────────────────────────


def _make_post_handler(engine_key: str, method_name: str, singleton: Any) -> Callable:
    """Return a FastAPI endpoint that calls singleton.<method_name>(**body)."""
    def handler(body: Dict[str, Any]):
        try:
            result = getattr(singleton, method_name)(**body)
            return _to_dict(result)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except TypeError as exc:
            raise HTTPException(status_code=400, detail=f"invalid payload: {exc}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    handler.__name__ = f"{engine_key}_{method_name}_post_{id(handler)}"
    return handler


def _make_list_handler(engine_key: str, method_name: str, singleton: Any) -> Callable:
    """Return a GET endpoint that lists records."""
    def handler(agent_id: Optional[str] = None, limit: int = 50):
        kwargs: Dict[str, Any] = {}
        if agent_id is not None:
            kwargs["agent_id"] = agent_id
        kwargs["limit"] = limit
        try:
            result = getattr(singleton, method_name)(**kwargs)
            return _wrap_list(result)
        except TypeError:
            kwargs.pop("limit", None)
            try:
                result = getattr(singleton, method_name)(**kwargs)
                return _wrap_list(result)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    handler.__name__ = f"{engine_key}_{method_name}_list_{id(handler)}"
    return handler


def _make_get_handler(engine_key: str, method_name: str, singleton: Any) -> Callable:
    """Return a GET endpoint that fetches a single record by id."""
    def handler(item_id: str):
        try:
            result = getattr(singleton, method_name)(item_id)
            if result is None:
                raise HTTPException(status_code=404, detail="not found")
            return _to_dict(result)
        except HTTPException:
            raise
        except ValueError:
            raise HTTPException(status_code=404, detail="not found")
        except KeyError:
            raise HTTPException(status_code=404, detail="not found")
        except LookupError:
            raise HTTPException(status_code=404, detail="not found")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    handler.__name__ = f"{engine_key}_{method_name}_get_{id(handler)}"
    return handler


def _make_stats_handler(engine_key: str, singleton: Any) -> Callable:
    """Return a GET endpoint that returns engine stats."""
    def handler():
        try:
            return _to_dict(singleton.get_stats())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    handler.__name__ = f"{engine_key}_stats_get_{id(handler)}"
    return handler


def _make_profile_get_handler(engine_key: str, singleton: Any) -> Callable:
    """Return a GET endpoint that returns the profile for an agent."""
    def handler(agent_id: str):
        try:
            profile = singleton.get_profile(agent_id)
            return _to_dict(profile)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    handler.__name__ = f"{engine_key}_profile_get_{id(handler)}"
    return handler


def _make_profile_put_handler(engine_key: str, singleton: Any) -> Callable:
    """Return a PUT endpoint that updates the profile for an agent."""
    def handler(agent_id: str, body: Dict[str, Any]):
        try:
            profile = singleton.update_profile(agent_id, **body)
            return _to_dict(profile)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except TypeError as exc:
            raise HTTPException(status_code=400, detail=f"invalid payload: {exc}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    handler.__name__ = f"{engine_key}_profile_put_{id(handler)}"
    return handler


def _make_profiles_list_handler(engine_key: str, singleton: Any) -> Callable:
    """Return a GET endpoint that lists all profiles."""
    def handler():
        try:
            return _wrap_list(singleton.list_profiles())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    handler.__name__ = f"{engine_key}_profiles_list_{id(handler)}"
    return handler


# ── Route registration ────────────────────────────────────────────────

def _route_exists(path: str, method: str) -> bool:
    """Check if a route with the given path and method is already registered."""
    for r in router.routes:
        if hasattr(r, "path") and r.path == path:
            if hasattr(r, "methods") and method in r.methods:
                return True
    return False


def _add_route(path: str, handler: Callable, methods: List[str]) -> None:
    """Register a route only if it doesn't already exist."""
    full_path = f"/api{path}" if not path.startswith("/api") else path
    for m in methods:
        if _route_exists(full_path, m):
            return
    router.add_api_route(path, handler, methods=methods)


def _register_engine_routes(engine_key: str, singleton: Any) -> None:
    """Register all CRUD routes for one engine."""
    used_methods: Set[str] = set()
    registered_nouns: Set[str] = set()

    # 1. Reading routes. Most engines use record_reading, but early engines
    # use read_<noun> (read_membrane, read_buoyancy) or detect_<noun>.
    reading_method: Optional[str] = None
    if hasattr(singleton, "record_reading"):
        reading_method = "record_reading"
    else:
        for attr in dir(singleton):
            if attr.startswith("read_") and callable(getattr(singleton, attr)):
                reading_method = attr
                break
    if reading_method:
        _add_route(
            f"/{engine_key}/reading",
            _make_post_handler(engine_key, reading_method, singleton),
            methods=["POST"],
        )
        used_methods.add(reading_method)
    if hasattr(singleton, "list_readings"):
        _add_route(
            f"/{engine_key}/readings",
            _make_list_handler(engine_key, "list_readings", singleton),
            methods=["GET"],
        )
    if hasattr(singleton, "get_reading"):
        _add_route(
            f"/{engine_key}/reading/{{item_id}}",
            _make_get_handler(engine_key, "get_reading", singleton),
            methods=["GET"],
        )

    # 2. Discover all get_<word> methods (excluding infra) — these define
    #    collections. Deriving URLs from the get method name (not the list
    #    plural) handles naming mismatches like list_crystals/get_crystallize.
    infra_singulars = {"reading", "snapshot", "plan", "profile", "stats"}
    collection_gets: List[Tuple[str, str]] = []  # (word, get_method)
    for attr in dir(singleton):
        if not _is_get_method(attr):
            continue
        word = _get_singular(attr)
        if word in infra_singulars:
            continue
        collection_gets.append((word, attr))

    # 3. Register POST and GET-by-id routes for each collection, using URL
    #    aliases derived from the get method name. Multiple aliases handle
    #    engines where tests expect different URL patterns:
    #      - solidity: get_crystallize -> URL /crystallize (not /crystal)
    #      - texture:  get_polish      -> URL /polish (not /polishe)
    #      - confluence: get_confluence == engine_key -> URL /record
    #      - tide:     get_phase_shift -> URL /phase (first word)
    #      - aurora:   get_curtain_shift -> URL /shift (standardized)
    #      - cascade:  get_tier_transition -> URL /transition (second word)
    for word, get_method in sorted(collection_gets):
        action_method = _find_action_method(singleton, word, used_methods)
        if action_method:
            used_methods.add(action_method)

        url_words: List[str] = [word]
        if word.endswith("_shift"):
            first_word = word.rsplit("_shift", 1)[0]
            if first_word and first_word not in url_words:
                url_words.append(first_word)
            if "shift" not in url_words:
                url_words.append("shift")
        elif "_" in word:
            tail = word.split("_", 1)[1]
            if tail and tail not in url_words:
                url_words.append(tail)
        if word == engine_key and "record" not in url_words:
            url_words.append("record")

        for url_word in url_words:
            if action_method:
                _add_route(
                    f"/{engine_key}/{url_word}",
                    _make_post_handler(engine_key, action_method, singleton),
                    methods=["POST"],
                )
                registered_nouns.add(url_word)
            _add_route(
                f"/{engine_key}/{url_word}/{{item_id}}",
                _make_get_handler(engine_key, get_method, singleton),
                methods=["GET"],
            )

    # 4. Register GET list routes from list_<plural> methods (excluding infra).
    infra_plurals = {"readings", "snapshots", "plans", "profiles"}
    for attr in dir(singleton):
        if not _is_list_method(attr):
            continue
        plural = _list_plural(attr)
        if plural in infra_plurals:
            continue
        _add_route(
            f"/{engine_key}/{plural}",
            _make_list_handler(engine_key, attr, singleton),
            methods=["GET"],
        )
        # Register /shifts alias for shift collections (e.g. aurora, forge).
        if plural.endswith("_shifts") and plural != "shifts":
            _add_route(
                f"/{engine_key}/shifts",
                _make_list_handler(engine_key, attr, singleton),
                methods=["GET"],
            )
        # Register /records alias when the singular equals the engine key.
        singular_for_plural = _resolve_singular(singleton, plural)
        if singular_for_plural == engine_key:
            _add_route(
                f"/{engine_key}/records",
                _make_list_handler(engine_key, attr, singleton),
                methods=["GET"],
            )

    # 5. Snapshot routes.
    if hasattr(singleton, "take_snapshot"):
        _add_route(
            f"/{engine_key}/snapshot",
            _make_post_handler(engine_key, "take_snapshot", singleton),
            methods=["POST"],
        )
        used_methods.add("take_snapshot")
    if hasattr(singleton, "list_snapshots"):
        _add_route(
            f"/{engine_key}/snapshots",
            _make_list_handler(engine_key, "list_snapshots", singleton),
            methods=["GET"],
        )
    if hasattr(singleton, "get_snapshot"):
        _add_route(
            f"/{engine_key}/snapshot/{{item_id}}",
            _make_get_handler(engine_key, "get_snapshot", singleton),
            methods=["GET"],
        )

    # 6. Plan routes.
    plan_method_name: Optional[str] = None
    plan_word: Optional[str] = None
    for attr in dir(singleton):
        if _is_plan_method(attr):
            plan_method_name = attr
            plan_word = _plan_word(attr)
            break

    if plan_method_name and plan_word:
        # Standardized /plan URL.
        _add_route(
            f"/{engine_key}/plan",
            _make_post_handler(engine_key, plan_method_name, singleton),
            methods=["POST"],
        )
        # Engine-specific URL (e.g. /api/refraction/correction) — only if not
        # already registered as an action noun.
        if plan_word not in registered_nouns and plan_word != "plan":
            _add_route(
                f"/{engine_key}/{plan_word}",
                _make_post_handler(engine_key, plan_method_name, singleton),
                methods=["POST"],
            )
            registered_nouns.add(plan_word)

    if hasattr(singleton, "list_plans"):
        _add_route(
            f"/{engine_key}/plans",
            _make_list_handler(engine_key, "list_plans", singleton),
            methods=["GET"],
        )
        # Engine-specific plan plural (e.g. /api/refraction/corrections).
        if plan_word and plan_word != "plan":
            plan_plural = f"{plan_word}s"
            _add_route(
                f"/{engine_key}/{plan_plural}",
                _make_list_handler(engine_key, "list_plans", singleton),
                methods=["GET"],
            )

    if hasattr(singleton, "get_plan"):
        _add_route(
            f"/{engine_key}/plan/{{item_id}}",
            _make_get_handler(engine_key, "get_plan", singleton),
            methods=["GET"],
        )
        if plan_word and plan_word != "plan":
            _add_route(
                f"/{engine_key}/{plan_word}/{{item_id}}",
                _make_get_handler(engine_key, "get_plan", singleton),
                methods=["GET"],
            )

    # 7. Profile routes.
    if hasattr(singleton, "get_profile"):
        _add_route(
            f"/{engine_key}/profile/{{agent_id}}",
            _make_profile_get_handler(engine_key, singleton),
            methods=["GET"],
        )
    if hasattr(singleton, "update_profile"):
        _add_route(
            f"/{engine_key}/profile/{{agent_id}}",
            _make_profile_put_handler(engine_key, singleton),
            methods=["PUT", "PATCH"],
        )
    if hasattr(singleton, "list_profiles"):
        _add_route(
            f"/{engine_key}/profiles",
            _make_profiles_list_handler(engine_key, singleton),
            methods=["GET"],
        )

    # 8. Stats route.
    if hasattr(singleton, "get_stats"):
        _add_route(
            f"/{engine_key}/stats",
            _make_stats_handler(engine_key, singleton),
            methods=["GET"],
        )


# ── Register routes for every discovered engine at import time ────────

def _register_all_engines() -> None:
    """Discover all themed engines and register their routes.

    Engines are discovered via the CognitiveBridge. Some early-round engines
    (osmosis, buoyancy, immunity) use alternative reading method names
    (read_membrane, read_buoyancy, detect_threat) instead of record_reading,
    so the bridge skips them. We fall back to scanning agent.shared for
    *_engine singletons the bridge missed and register their routes too.
    """
    count = 0
    registered_keys: Set[str] = set()

    try:
        from agent.cognitive_bridge import get_cognitive_bridge
        bridge = get_cognitive_bridge()
        for engine_key in bridge.list_engines():
            info = bridge.get_engine_info(engine_key)
            if info is None:
                continue
            try:
                _register_engine_routes(engine_key, info.singleton)
                registered_keys.add(engine_key)
                count += 1
            except Exception as exc:
                logger.warning("Failed to register routes for engine '%s': %s", engine_key, exc)
    except Exception as exc:
        logger.warning("CognitiveBridge unavailable: %s", exc)

    # Fallback: scan agent.shared for *_engine singletons the bridge missed.
    try:
        from agent import shared
        for attr_name in dir(shared):
            if not attr_name.endswith("_engine"):
                continue
            engine_key = attr_name[:-len("_engine")]
            if engine_key in registered_keys:
                continue
            singleton = getattr(shared, attr_name)
            if not callable(getattr(singleton, "take_snapshot", None)):
                continue
            try:
                _register_engine_routes(engine_key, singleton)
                registered_keys.add(engine_key)
                count += 1
            except Exception as exc:
                logger.warning("Failed to register routes for engine '%s': %s", engine_key, exc)
    except Exception as exc:
        logger.warning("agent.shared scan unavailable: %s", exc)

    logger.info("Cognitive engine routes registered for %d engines", count)


_register_all_engines()
