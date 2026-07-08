"""Buddy Cognitive Tools — agent-callable tools for cognitive state access

Registers four tools on the shared ToolRegistry that let agents query and
mutate cognitive state during reasoning:

  - cognitive_get_profile(agent_id)
  - cognitive_record_reading(agent_id, engine_key, axis, score, source)
  - cognitive_take_snapshot(agent_id, engine_key)
  - cognitive_compose(agent_id, composition_name)

Tools are registered lazily via register_cognitive_tools() which is called
from agent.shared after the tool_registry singleton is constructed.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("buddy.cognitive_tools")


async def _cognitive_get_profile(params: dict[str, Any]) -> str:
    """Return the cognitive profile for an agent across all engines."""
    agent_id = params.get("agent_id", "")
    if not agent_id:
        return "ERROR: agent_id is required"
    try:
        from agent.shared import cognitive_bridge
        import json
        profile = cognitive_bridge.get_agent_cognitive_profile(agent_id)
        return json.dumps(profile, default=str)
    except Exception as exc:
        return f"ERROR: {exc}"


async def _cognitive_record_reading(params: dict[str, Any]) -> str:
    """Record a cognitive reading on the specified engine."""
    agent_id = params.get("agent_id", "")
    engine_key = params.get("engine_key", "")
    if not agent_id or not engine_key:
        return "ERROR: agent_id and engine_key are required"
    payload = {
        "axis": params.get("axis", "FLOW"),
        "score": float(params.get("score", 0.5)),
        "source": params.get("source", "AUTO"),
        "intensity": float(params.get("intensity", 0.5)),
    }
    try:
        from agent.shared import cognitive_bridge
        result = cognitive_bridge.record_cognitive_event(
            agent_id=agent_id,
            engine_key=engine_key,
            event_type="reading",
            payload=payload,
        )
        return f"OK: {result.get('ok')} engine={engine_key} agent={agent_id}"
    except Exception as exc:
        return f"ERROR: {exc}"


async def _cognitive_take_snapshot(params: dict[str, Any]) -> str:
    """Take a snapshot on the specified engine for the given agent."""
    agent_id = params.get("agent_id", "")
    engine_key = params.get("engine_key", "")
    if not agent_id or not engine_key:
        return "ERROR: agent_id and engine_key are required"
    try:
        from agent.shared import cognitive_bridge
        result = cognitive_bridge.take_snapshot(agent_id, engine_key)
        import json
        if result.get("ok"):
            return f"OK: snapshot_id={result['result'].get('snapshot_id')}"
        return f"ERROR: {result.get('error')}"
    except Exception as exc:
        return f"ERROR: {exc}"


async def _cognitive_compose(params: dict[str, Any]) -> str:
    """Evaluate a named cognitive composition for the given agent."""
    agent_id = params.get("agent_id", "")
    composition_name = params.get("composition_name", "holistic")
    if not agent_id:
        return "ERROR: agent_id is required"
    try:
        from agent.shared import cognitive_composer
        result = cognitive_composer.evaluate(agent_id, composition_name)
        import json
        return json.dumps({
            "composition": result.composition_name,
            "fused_score": result.fused_score,
            "fused_regime": result.fused_regime,
            "contributing_engines": result.contributing_engines,
            "notes": result.notes,
        }, default=str)
    except Exception as exc:
        return f"ERROR: {exc}"


def register_cognitive_tools(tool_registry: Any) -> None:
    """Register all four cognitive tools on the given ToolRegistry.

    Idempotent: re-registration replaces existing tools with the same name.
    """
    try:
        from agent.tools import ToolCategory, ToolDefinition, ToolParameter
    except Exception as exc:
        logger.warning("Cannot register cognitive tools, tools module missing: %s", exc)
        return

    tools = [
        ToolDefinition(
            name="cognitive_get_profile",
            description="Query the aggregate cognitive profile for an agent across all themed cognitive engines.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(name="agent_id", type="string", description="The agent ID to query", required=True),
            ],
        ),
        ToolDefinition(
            name="cognitive_record_reading",
            description="Record a cognitive reading on a specific themed cognitive engine for an agent.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(name="agent_id", type="string", description="The agent ID", required=True),
                ToolParameter(name="engine_key", type="string", description="Engine key, e.g. 'vortex' or 'prism'", required=True),
                ToolParameter(name="axis", type="string", description="Cognitive axis (engine-specific uppercase enum)", required=False),
                ToolParameter(name="score", type="number", description="Reading score in 0..1", required=False),
                ToolParameter(name="source", type="string", description="Source enum value", required=False),
                ToolParameter(name="intensity", type="number", description="Intensity in 0..1", required=False),
            ],
        ),
        ToolDefinition(
            name="cognitive_take_snapshot",
            description="Take a cognitive snapshot on a specific themed engine for an agent. The snapshot is persisted to SQLite.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(name="agent_id", type="string", description="The agent ID", required=True),
                ToolParameter(name="engine_key", type="string", description="Engine key, e.g. 'tundra'", required=True),
            ],
        ),
        ToolDefinition(
            name="cognitive_compose",
            description="Evaluate a named cognitive composition (holistic / analytical / creative) for an agent, fusing outputs across multiple engines.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(name="agent_id", type="string", description="The agent ID", required=True),
                ToolParameter(name="composition_name", type="string", description="Composition name: holistic, analytical, or creative", required=False),
            ],
        ),
    ]

    for tool_def in tools:
        try:
            handler = {
                "cognitive_get_profile": _cognitive_get_profile,
                "cognitive_record_reading": _cognitive_record_reading,
                "cognitive_take_snapshot": _cognitive_take_snapshot,
                "cognitive_compose": _cognitive_compose,
            }[tool_def.name]
            # ToolRegistry.define() returns a decorator; call it directly.
            tool_registry._tools[tool_def.name] = tool_def
            # Stash the handler so execute() can find it. The registry's
            # define() decorator normally wires this; we replicate the storage.
            if not hasattr(tool_registry, "_cognitive_handlers"):
                tool_registry._cognitive_handlers = {}
            tool_registry._cognitive_handlers[tool_def.name] = handler
            logger.info("Cognitive tool registered: %s", tool_def.name)
        except Exception as exc:
            logger.warning("Failed to register cognitive tool %s: %s", tool_def.name, exc)
