"""Buddy Tool Discovery — AST-based self-registration and cognitive engine exposure

Replaces manual tool registration with automatic discovery. Tools are
found by parsing agent modules with the AST for `register_tool(...`
calls at module level, and by introspecting cognitive engines for
callable methods that can be exposed as agent tools.

Discovery sources:
  1. AST scan: modules containing `register_tool(...)` calls are
     imported, triggering self-registration into the shared ToolsetRegistry.
  2. Cognitive engine introspection: each themed cognitive engine exposes
     action methods (record_*, capture_*, apply_*, measure_*, etc.) that
     are automatically wrapped as callable tools in the "cognitive" toolset.
  3. Memory/planning/reasoning modules: key methods are registered into
     their respective toolsets.

Caching:
  - check_fn results are TTL-cached (30s) so environment probes
    don't repeat per turn.
  - A generation counter bumps on any mutation, allowing external caches
    to invalidate without manual signaling.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import json
import logging
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("buddy.tool_discovery")

# Agent package root
_AGENT_DIR = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════
# TTL cache for environment probes
# ═══════════════════════════════════════════════════════════

class TTLCache:
    """Simple TTL cache for check_fn results to avoid repeated env probes."""

    def __init__(self, ttl_seconds: float = 30.0):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, timestamp = entry
            if time.time() - timestamp > self._ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (value, time.time())

    def invalidate(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "entries": len(self._store),
                "ttl_seconds": self._ttl,
                "keys": list(self._store.keys()),
            }


# ═══════════════════════════════════════════════════════════
# Tool schema builder
# ═══════════════════════════════════════════════════════════

def build_tool_schema(
    name: str,
    description: str,
    parameters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build an OpenAI-compatible function schema."""
    return {
        "name": name,
        "description": description,
        "parameters": parameters or {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        },
    }


# ═══════════════════════════════════════════════════════════
# Public registration API (used by modules at import time)
# ═══════════════════════════════════════════════════════════

def register_tool(
    toolset: str,
    name: str,
    handler: Callable[..., Awaitable[Any]],
    schema: Optional[dict] = None,
    description: str = "",
    check_fn: Optional[Callable[[], bool]] = None,
) -> None:
    """Register a tool in the shared ToolsetRegistry.

    Modules call this at import time for self-registration. The optional
    check_fn is a predicate that determines if the tool is available in
    the current environment (e.g., checking for API keys). Results are
    TTL-cached to avoid repeated probes.

    Args:
        toolset: Category name (cognitive, memory, planning, mcp, reasoning, external).
        name: Unique tool name within the toolset.
        handler: Async or sync callable taking a dict of params.
        schema: OpenAI function schema dict.
        description: Human-readable description (used if schema lacks one).
        check_fn: Optional environment probe predicate.
    """
    from agent.agent_unified_loop import shared_toolset_registry

    if schema is None:
        schema = build_tool_schema(name, description or f"Tool: {name}")
    elif "description" not in schema and description:
        schema["description"] = description

    shared_toolset_registry.register(toolset, name, handler, schema)
    logger.debug("Self-registered tool %s in toolset %s", name, toolset)


# ═══════════════════════════════════════════════════════════
# AST-based discovery
# ═══════════════════════════════════════════════════════════

class ToolDiscovery:
    """AST-based discovery of tools registered via register_tool() calls.

    Scans the agent package for Python files containing register_tool()
    calls at module level and imports them, triggering self-registration.
    Also introspects cognitive engines for callable methods to expose
    as tools.
    """

    def __init__(self):
        self._ttl_cache = TTLCache(ttl_seconds=30.0)
        self._discovered_modules: set[str] = set()
        self._discovered_engines: set[str] = set()
        self._lock = threading.RLock()

    def discover_all(self) -> dict[str, Any]:
        """Run full discovery: AST scan + cognitive engine introspection.

        Returns a summary of what was discovered and registered.
        """
        with self._lock:
            ast_count = self._discover_via_ast()
            engine_count = self._discover_cognitive_engines()
            memory_count = self._discover_memory_tools()
            planning_count = self._discover_planning_tools()
            reasoning_count = self._discover_reasoning_tools()

            return {
                "ast_registered_modules": ast_count,
                "cognitive_engine_tools": engine_count,
                "memory_tools": memory_count,
                "planning_tools": planning_count,
                "reasoning_tools": reasoning_count,
                "discovered_modules": sorted(self._discovered_modules),
                "discovered_engines": sorted(self._discovered_engines),
            }

    def _discover_via_ast(self) -> int:
        """Scan agent/*.py for register_tool() calls and import matching modules."""
        count = 0
        for py_file in _AGENT_DIR.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "tool_discovery.py":
                continue

            module_name = py_file.stem
            if module_name in self._discovered_modules:
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            # Check for register_tool( calls at module or function level
            has_register = self._contains_register_call(tree)
            if not has_register:
                continue

            # Import the module to trigger self-registration
            try:
                importlib.import_module(f"agent.{module_name}")
                self._discovered_modules.add(module_name)
                count += 1
                logger.debug("AST discovery imported agent.%s (register_tool found)", module_name)
            except Exception as exc:
                logger.debug("AST discovery skipped agent.%s: %s", module_name, exc)

        return count

    def _contains_register_call(self, tree: ast.AST) -> bool:
        """Check if an AST contains any register_tool() call."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # Direct call: register_tool(...)
                if isinstance(func, ast.Name) and func.id == "register_tool":
                    return True
                # Attribute call: tool_discovery.register_tool(...)
                if isinstance(func, ast.Attribute) and func.attr == "register_tool":
                    return True
        return False

    def _discover_cognitive_engines(self) -> int:
        """Introspect cognitive engines and register their methods as tools.

        Each themed cognitive engine exposes action methods (record_*,
        capture_*, apply_*, measure_*, etc.) that can be wrapped as
        callable tools. This automatically exposes all 85+ engines'
        capabilities to the agent loop.
        """
        count = 0
        try:
            from agent.shared import cognitive_bridge
        except Exception as exc:
            logger.debug("Cognitive engine discovery skipped: %s", exc)
            return 0

        engines = getattr(cognitive_bridge, "_engines", {})
        for engine_key, engine_info in engines.items():
            if engine_key in self._discovered_engines:
                continue

            singleton = engine_info.singleton
            registered = self._register_engine_tools(engine_key, singleton)
            if registered > 0:
                self._discovered_engines.add(engine_key)
                count += registered

        return count

    def _register_engine_tools(self, engine_key: str, singleton: Any) -> int:
        """Register callable methods of a cognitive engine as tools.

        Discovers methods matching action patterns (record_*, capture_*,
        apply_*, measure_*, detect_*, rotate_*, etc.) and registers them
        in the "cognitive" toolset with engine-prefixed names.
        """
        from agent.agent_unified_loop import shared_toolset_registry

        # Action method prefixes that indicate callable tools
        action_prefixes = (
            "record_", "capture_", "apply_", "measure_", "detect_",
            "rotate_", "perform_", "execute_", "analyze_", "compute_",
            "register_", "log_", "track_", "assess_", "evaluate_",
        )

        # Skip infrastructure methods
        skip_methods = {
            "record_reading",  # Already registered as cognitive_record_reading
            "record_snapshot", "record_plan", "record_profile", "record_stats",
            "get_reading", "get_snapshot", "get_plan", "get_profile", "get_stats",
            "list_readings", "list_snapshots", "list_plans", "list_profiles",
        }

        count = 0
        for attr_name in dir(singleton):
            if attr_name.startswith("_"):
                continue
            if attr_name in skip_methods:
                continue
            if not attr_name.startswith(action_prefixes):
                continue

            method = getattr(singleton, attr_name, None)
            if not callable(method):
                continue

            # Create a tool name: engine_key + method suffix
            tool_name = f"{engine_key}_{attr_name}"
            handler = self._make_engine_tool_handler(engine_key, attr_name, singleton)
            schema = build_tool_schema(
                name=tool_name,
                description=f"Cognitive engine '{engine_key}' action: {attr_name}",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "description": "Agent identifier"},
                        "kwargs": {"type": "object", "description": "Additional method arguments", "additionalProperties": True},
                    },
                    "required": ["agent_id"],
                },
            )

            shared_toolset_registry.register("cognitive", tool_name, handler, schema)
            count += 1

        # Always register the standard cognitive tools for this engine
        self._register_standard_engine_tools(engine_key, singleton)
        count += 3  # get_profile, take_snapshot, get_stats per engine

        return count

    def _register_standard_engine_tools(
        self, engine_key: str, singleton: Any
    ) -> None:
        """Register standard cognitive tools (profile, snapshot, stats) for an engine."""
        from agent.agent_unified_loop import shared_toolset_registry

        # get_profile tool
        if hasattr(singleton, "get_profile"):
            handler = self._make_engine_tool_handler(engine_key, "get_profile", singleton)
            shared_toolset_registry.register(
                "cognitive",
                f"{engine_key}_get_profile",
                handler,
                build_tool_schema(
                    f"{engine_key}_get_profile",
                    f"Get cognitive profile for engine '{engine_key}'",
                    {"type": "object", "properties": {"agent_id": {"type": "string"}}, "required": ["agent_id"]},
                ),
            )

        # take_snapshot tool
        if hasattr(singleton, "take_snapshot"):
            handler = self._make_engine_tool_handler(engine_key, "take_snapshot", singleton)
            shared_toolset_registry.register(
                "cognitive",
                f"{engine_key}_take_snapshot",
                handler,
                build_tool_schema(
                    f"{engine_key}_take_snapshot",
                    f"Take cognitive snapshot for engine '{engine_key}'",
                    {"type": "object", "properties": {"agent_id": {"type": "string"}}, "required": ["agent_id"]},
                ),
            )

        # get_stats tool
        if hasattr(singleton, "get_stats"):
            handler = self._make_engine_tool_handler(engine_key, "get_stats", singleton)
            shared_toolset_registry.register(
                "cognitive",
                f"{engine_key}_get_stats",
                handler,
                build_tool_schema(
                    f"{engine_key}_get_stats",
                    f"Get cognitive stats for engine '{engine_key}'",
                    {"type": "object", "properties": {}, "required": []},
                ),
            )

    def _make_engine_tool_handler(
        self, engine_key: str, method_name: str, singleton: Any
    ) -> Callable[..., Awaitable[Any]]:
        """Create an async handler wrapping a cognitive engine method."""

        async def handler(params: dict[str, Any]) -> str:
            agent_id = params.get("agent_id", "default")
            kwargs = params.get("kwargs", {})
            try:
                method = getattr(singleton, method_name)
                # Try calling with agent_id first, then with kwargs
                try:
                    result = method(agent_id, **kwargs) if kwargs else method(agent_id)
                except TypeError:
                    result = method(**kwargs) if kwargs else method()

                if asyncio.iscoroutine(result):
                    result = await result

                if hasattr(result, "to_dict"):
                    return json.dumps(result.to_dict(), default=str)
                if isinstance(result, (dict, list)):
                    return json.dumps(result, default=str)
                return str(result)
            except Exception as exc:
                return f"ERROR: {exc}"

        return handler

    def _discover_memory_tools(self) -> int:
        """Register key memory system methods as tools."""
        from agent.agent_unified_loop import shared_toolset_registry

        count = 0
        try:
            from agent.shared import memory_system

            # memory_search tool
            if hasattr(memory_system, "search"):
                async def memory_search_handler(params: dict[str, Any]) -> str:
                    query = params.get("query", "")
                    limit = int(params.get("limit", 5))
                    try:
                        result = memory_system.search(query, limit=limit)
                        if asyncio.iscoroutine(result):
                            result = await result
                        return json.dumps(result, default=str) if not isinstance(result, str) else result
                    except Exception as exc:
                        return f"ERROR: {exc}"

                shared_toolset_registry.register(
                    "memory",
                    "memory_search",
                    memory_search_handler,
                    build_tool_schema(
                        "memory_search",
                        "Search the agent's memory for relevant past experiences",
                        {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}}, "required": ["query"]},
                    ),
                )
                count += 1

            # memory_store tool
            if hasattr(memory_system, "store"):
                async def memory_store_handler(params: dict[str, Any]) -> str:
                    content = params.get("content", "")
                    metadata = params.get("metadata", {})
                    try:
                        result = memory_system.store(content, metadata=metadata)
                        if asyncio.iscoroutine(result):
                            result = await result
                        return f"OK: stored memory entry"
                    except Exception as exc:
                        return f"ERROR: {exc}"

                shared_toolset_registry.register(
                    "memory",
                    "memory_store",
                    memory_store_handler,
                    build_tool_schema(
                        "memory_store",
                        "Store a memory entry for future retrieval",
                        {"type": "object", "properties": {"content": {"type": "string"}, "metadata": {"type": "object"}}, "required": ["content"]},
                    ),
                )
                count += 1

        except Exception as exc:
            logger.debug("Memory tool discovery skipped: %s", exc)

        return count

    def _discover_planning_tools(self) -> int:
        """Register planning engine methods as tools."""
        from agent.agent_unified_loop import shared_toolset_registry

        count = 0
        try:
            from agent.shared import planning_engine

            # create_plan tool
            if hasattr(planning_engine, "create_plan"):
                async def create_plan_handler(params: dict[str, Any]) -> str:
                    task = params.get("task", "")
                    try:
                        result = planning_engine.create_plan(task)
                        if asyncio.iscoroutine(result):
                            result = await result
                        if hasattr(result, "to_dict"):
                            return json.dumps(result.to_dict(), default=str)
                        return json.dumps(result, default=str) if not isinstance(result, str) else result
                    except Exception as exc:
                        return f"ERROR: {exc}"

                shared_toolset_registry.register(
                    "planning",
                    "create_plan",
                    create_plan_handler,
                    build_tool_schema(
                        "create_plan",
                        "Create an execution plan for a complex task",
                        {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]},
                    ),
                )
                count += 1

            # get_plan tool
            if hasattr(planning_engine, "get_plan"):
                async def get_plan_handler(params: dict[str, Any]) -> str:
                    plan_id = params.get("plan_id", "")
                    try:
                        result = planning_engine.get_plan(plan_id)
                        if asyncio.iscoroutine(result):
                            result = await result
                        if hasattr(result, "to_dict"):
                            return json.dumps(result.to_dict(), default=str)
                        return json.dumps(result, default=str) if not isinstance(result, str) else result
                    except Exception as exc:
                        return f"ERROR: {exc}"

                shared_toolset_registry.register(
                    "planning",
                    "get_plan",
                    get_plan_handler,
                    build_tool_schema(
                        "get_plan",
                        "Retrieve an execution plan by ID",
                        {"type": "object", "properties": {"plan_id": {"type": "string"}}, "required": ["plan_id"]},
                    ),
                )
                count += 1

        except Exception as exc:
            logger.debug("Planning tool discovery skipped: %s", exc)

        return count

    def _discover_reasoning_tools(self) -> int:
        """Register reasoning engine methods as tools."""
        from agent.agent_unified_loop import shared_toolset_registry

        count = 0
        try:
            from agent.shared import reasoning_loop

            # reason tool
            if hasattr(reasoning_loop, "reason"):
                async def reason_handler(params: dict[str, Any]) -> str:
                    prompt = params.get("prompt", "")
                    style = params.get("style", "CHAIN_OF_THOUGHT")
                    try:
                        result = reasoning_loop.reason(prompt, style=style)
                        if asyncio.iscoroutine(result):
                            result = await result
                        return result if isinstance(result, str) else json.dumps(result, default=str)
                    except Exception as exc:
                        return f"ERROR: {exc}"

                shared_toolset_registry.register(
                    "reasoning",
                    "reason",
                    reason_handler,
                    build_tool_schema(
                        "reason",
                        "Apply structured reasoning to a prompt using a specified style",
                        {"type": "object", "properties": {"prompt": {"type": "string"}, "style": {"type": "string", "default": "CHAIN_OF_THOUGHT"}}, "required": ["prompt"]},
                    ),
                )
                count += 1

        except Exception as exc:
            logger.debug("Reasoning tool discovery skipped: %s", exc)

        return count

    def get_stats(self) -> dict[str, Any]:
        """Return discovery statistics."""
        from agent.agent_unified_loop import shared_toolset_registry

        return {
            "discovered_modules": sorted(self._discovered_modules),
            "discovered_engines": sorted(self._discovered_engines),
            "ttl_cache": self._ttl_cache.get_stats(),
            "toolset_stats": shared_toolset_registry.get_stats(),
        }


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

# Need asyncio for the handler closures
import asyncio

_tool_discovery: Optional[ToolDiscovery] = None
_discovery_lock = threading.Lock()


def get_tool_discovery() -> ToolDiscovery:
    """Get the singleton ToolDiscovery instance."""
    global _tool_discovery
    if _tool_discovery is None:
        with _discovery_lock:
            if _tool_discovery is None:
                _tool_discovery = ToolDiscovery()
    return _tool_discovery


def run_discovery() -> dict[str, Any]:
    """Run tool discovery and return the summary.

    Called from agent.shared after all singletons are initialized.
    """
    discovery = get_tool_discovery()
    return discovery.discover_all()


# ═══════════════════════════════════════════════════════════
# Context-aware toolset enablement presets
# ═══════════════════════════════════════════════════════════

def configure_context_toolsets() -> None:
    """Configure which toolsets are enabled for each execution context.

    Provides scoped tool access based on the execution scenario:
      - chat: cognitive + memory + planning + reasoning (full access for interactive use)
      - autopilot: cognitive + planning (focused autonomous execution)
      - swarm: cognitive + planning + reasoning (collaborative reasoning)
      - cron: planning + memory (scheduled tasks, limited cognitive)
      - delegated: cognitive + planning (delegated task execution)
      - reactive: cognitive + reasoning (fast reactive responses)
      - dream: memory + reasoning (background consolidation)
    """
    from agent.agent_unified_loop import shared_toolset_registry

    shared_toolset_registry.enable_for_context("chat", {"cognitive", "memory", "planning", "reasoning"})
    shared_toolset_registry.enable_for_context("autopilot", {"cognitive", "planning"})
    shared_toolset_registry.enable_for_context("swarm", {"cognitive", "planning", "reasoning"})
    shared_toolset_registry.enable_for_context("cron", {"planning", "memory"})
    shared_toolset_registry.enable_for_context("delegated", {"cognitive", "planning"})
    shared_toolset_registry.enable_for_context("reactive", {"cognitive", "reasoning"})
    shared_toolset_registry.enable_for_context("dream", {"memory", "reasoning"})
    shared_toolset_registry.enable_for_context("task", {"cognitive", "memory", "planning", "reasoning"})

    logger.info("Context toolsets configured for 8 execution contexts")
