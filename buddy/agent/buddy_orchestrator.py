"""BuddyOrchestrator — Central AI-Native Coordination Hub

The BuddyOrchestrator is the supreme coordination layer that unifies all agent
capabilities into a single, coherent runtime. It integrates:
- Profile & Persona: Agent identity and behavior configuration
- MCP Tools: Model Context Protocol tool execution
- Autonomous Loop: Goal-driven autonomous execution
- Permission & Governance: Policy-based access control and approval
- Smart Router: Intelligent model selection and routing
- Identity Core: Self-awareness and memory management
- Workspace Manager: Isolated workspace environments
- Platform Gateway: Multi-provider API gateway with routing
- Pipeline Engine: Training and deployment pipeline management
- Learning Loop: Continuous self-improvement cycle
- Agent Mesh: Multi-agent collaboration and delegation
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.orchestrator")


class OrchestrationMode(str, Enum):
    """Execution mode for the orchestrator."""
    CHAT = "chat"
    TASK = "task"
    AUTONOMOUS = "autonomous"
    PIPELINE = "pipeline"
    COLLABORATIVE = "collaborative"
    REFLECTIVE = "reflective"


class OrchestrationStatus(str, Enum):
    """Status of an orchestration session."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OrchestrationContext:
    """Context for an orchestration session."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    mode: OrchestrationMode = OrchestrationMode.CHAT
    status: OrchestrationStatus = OrchestrationStatus.IDLE
    profile_id: str = ""
    persona_id: str = ""
    workspace_id: str = ""
    model_name: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    """Result of an orchestration execution."""
    session_id: str
    mode: OrchestrationMode
    success: bool
    content: str = ""
    error: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float = 0.0
    model_used: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BuddyOrchestrator:
    """Central coordination hub for the entire Buddy AI-native platform.

    Integrates all agent subsystems into a unified execution runtime
    with intelligent routing, autonomous execution, and self-improvement.
    """

    def __init__(self):
        self._active_sessions: dict[str, OrchestrationContext] = {}
        self._session_history: list[OrchestrationResult] = []
        self._hooks: dict[str, list[Callable]] = {
            "pre_execute": [],
            "post_execute": [],
            "on_error": [],
            "on_complete": [],
        }
        self._total_sessions: int = 0
        self._total_tokens: int = 0
        self._lock = asyncio.Lock()

    # ── Session Management ──────────────────────────────────────

    def create_session(
        self,
        agent_id: str,
        mode: OrchestrationMode = OrchestrationMode.CHAT,
        profile_id: str = "",
        persona_id: str = "",
        workspace_id: str = "",
    ) -> OrchestrationContext:
        """Create a new orchestration session."""
        ctx = OrchestrationContext(
            agent_id=agent_id,
            mode=mode,
            profile_id=profile_id,
            persona_id=persona_id,
            workspace_id=workspace_id,
        )
        self._active_sessions[ctx.session_id] = ctx
        self._total_sessions += 1
        logger.info(f"Orchestration session {ctx.session_id} created for agent {agent_id}")
        return ctx

    def get_session(self, session_id: str) -> Optional[OrchestrationContext]:
        """Get an active session by ID."""
        return self._active_sessions.get(session_id)

    def close_session(self, session_id: str):
        """Close an orchestration session."""
        self._active_sessions.pop(session_id, None)

    # ── Profile & Persona Integration ───────────────────────────

    def get_agent_profile(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Get the agent profile for an agent."""
        try:
            from agent.agent_profile import profile_manager
            for profile in profile_manager.list_profiles():
                if profile.name == agent_id or profile.profile_id == agent_id:
                    return profile.to_dict()
            return None
        except Exception as e:
            logger.warning(f"Profile lookup failed for {agent_id}: {e}")
            return None

    def get_agent_persona(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Get the active persona for an agent."""
        try:
            from agent.agent_persona import persona_registry
            profile = persona_registry.get_profile(agent_id)
            if profile:
                return {
                    "persona_id": profile.persona_id,
                    "name": profile.name,
                    "traits": profile.traits,
                    "interaction_style": profile.interaction_style.value,
                    "decision_style": profile.decision_style.value,
                }
            return None
        except Exception as e:
            logger.warning(f"Persona lookup failed for {agent_id}: {e}")
            return None

    # ── MCP Tool Execution ──────────────────────────────────────

    async def execute_mcp_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        session_id: str = "",
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute an MCP tool with governance checks."""
        try:
            from agent.agent_mcp import mcp_registry

            # Check governance policies
            if session_id:
                permitted = await self._check_governance(session_id, tool_name, arguments)
                if not permitted:
                    return {"success": False, "error": "Action blocked by governance policy"}

            result = await mcp_registry.execute_tool(tool_name, arguments, timeout=timeout)
            return {
                "tool_name": result.tool_name,
                "success": result.success,
                "content": result.content,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }
        except Exception as e:
            logger.error(f"MCP tool execution failed: {e}")
            return {"success": False, "error": str(e)}

    async def list_mcp_tools(self, category: str = "") -> list[dict[str, Any]]:
        """List available MCP tools."""
        try:
            from agent.agent_mcp import mcp_registry, MCPToolCategory
            cat = None
            if category:
                try:
                    cat = MCPToolCategory(category)
                except ValueError:
                    pass
            tools = mcp_registry.list_tools(category=cat)
            return [
                {"name": t.name, "description": t.description, "category": t.category.value}
                for t in tools
            ]
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")
            return []

    # ── Autonomous Loop Integration ─────────────────────────────

    async def execute_autonomous_goal(
        self,
        agent_id: str,
        goal_description: str,
        max_iterations: int = 10,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Execute a goal autonomously through the loop engine."""
        try:
            from agent.agent_autonomous_loop import AutonomousGoal, autonomous_loop

            goal = AutonomousGoal(
                description=goal_description,
                agent_id=agent_id,
                max_iterations=max_iterations,
            )
            result = await autonomous_loop.execute_goal(goal)
            return result
        except Exception as e:
            logger.error(f"Autonomous goal execution failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Permission & Governance ─────────────────────────────────

    async def _check_governance(
        self,
        session_id: str,
        action: str,
        context: dict[str, Any],
    ) -> bool:
        """Check if an action is permitted by governance policies."""
        try:
            from agent.agent_governance import governance_engine
            result = governance_engine.evaluate(
                session_id=session_id,
                action=action,
                context=context,
            )
            return result.get("permitted", True)
        except Exception as e:
            logger.warning(f"Governance check failed: {e}")
            return True  # Default to permit if governance unavailable

    def check_permission(
        self,
        agent_id: str,
        action: str,
        risk_level: str = "medium",
    ) -> dict[str, Any]:
        """Check if an agent has permission for an action."""
        try:
            from agent.agent_permission import permission_manager
            permitted = permission_manager.check(agent_id, action, risk_level)
            return {"permitted": permitted, "action": action, "agent_id": agent_id}
        except Exception as e:
            logger.warning(f"Permission check failed: {e}")
            return {"permitted": True, "action": action, "agent_id": agent_id}

    # ── Smart Routing ───────────────────────────────────────────

    def route_task(
        self,
        task_description: str,
        agent_id: str = "",
        preferred_model: str = "",
    ) -> dict[str, Any]:
        """Route a task to the optimal model based on complexity."""
        try:
            from agent.smart_router import smart_router
            decision = smart_router.route(
                task=task_description,
                agent_id=agent_id,
                preferred_model=preferred_model,
            )
            return {
                "model": decision.selected_model.model_name if decision.selected_model else "default",
                "tier": decision.selected_model.tier if decision.selected_model else "standard",
                "complexity": decision.task_complexity,
                "estimated_cost": decision.estimated_cost,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
            }
        except Exception as e:
            logger.warning(f"Smart routing failed: {e}")
            return {"model": "default", "tier": "standard", "complexity": "unknown"}

    # ── Identity Core ───────────────────────────────────────────

    def get_identity(self, agent_id: str) -> dict[str, Any]:
        """Get agent identity and self-awareness data."""
        try:
            from agent.identity_core import identity_registry
            identity = identity_registry.get_identity(agent_id)
            if identity:
                return {
                    "agent_id": identity.agent_id,
                    "self_awareness": identity.self_awareness,
                    "identity_coherence": identity.identity_coherence,
                    "traits": {
                        k: {"value": v.value, "confidence": v.confidence, "stability": v.stability}
                        for k, v in identity.traits.items()
                    } if hasattr(identity, 'traits') else {},
                    "memory_stats": identity.memory_stats if hasattr(identity, 'memory_stats') else {},
                }
            return {"agent_id": agent_id, "found": False}
        except Exception as e:
            logger.warning(f"Identity lookup failed: {e}")
            return {"agent_id": agent_id, "found": False}

    # ── Workspace Management ────────────────────────────────────

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Get workspace information."""
        try:
            from agent.workspace_manager import workspace_manager
            ws = workspace_manager.get_workspace(workspace_id)
            if ws:
                return {
                    "workspace_id": ws.workspace_id,
                    "name": ws.name,
                    "description": ws.description,
                    "is_active": ws.is_active,
                    "file_count": ws.file_count,
                    "memory_entries": ws.memory_entries,
                    "skill_count": ws.skill_count,
                    "tags": ws.tags,
                }
            return {"workspace_id": workspace_id, "found": False}
        except Exception as e:
            logger.warning(f"Workspace lookup failed: {e}")
            return {"workspace_id": workspace_id, "found": False}

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all workspaces."""
        try:
            from agent.workspace_manager import workspace_manager
            return [
                {
                    "workspace_id": ws.workspace_id,
                    "name": ws.name,
                    "description": ws.description,
                    "is_active": ws.is_active,
                }
                for ws in workspace_manager.list_workspaces()
            ]
        except Exception as e:
            logger.warning(f"Workspace listing failed: {e}")
            return []

    # ── Platform Gateway ────────────────────────────────────────

    async def route_gateway_request(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Route a request through the platform gateway."""
        try:
            from agent.platform_gateway import platform_gateway, GatewayRequest
            request = GatewayRequest(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response = await platform_gateway.route_request(request)
            return {
                "request_id": response.request_id,
                "provider_id": response.provider_id,
                "model": response.model,
                "content": response.content,
                "success": response.success,
                "latency_ms": response.latency_ms,
            }
        except Exception as e:
            logger.error(f"Gateway routing failed: {e}")
            return {"success": False, "error": str(e)}

    def get_gateway_stats(self) -> dict[str, Any]:
        """Get platform gateway statistics."""
        try:
            from agent.platform_gateway import platform_gateway
            return platform_gateway.get_stats()
        except Exception as e:
            logger.warning(f"Gateway stats failed: {e}")
            return {}

    # ── Pipeline Management ─────────────────────────────────────

    async def execute_pipeline(self, pipeline_id: str) -> dict[str, Any]:
        """Execute a pipeline."""
        try:
            from agent.platform_pipeline import pipeline_engine
            return await pipeline_engine.execute_pipeline(pipeline_id)
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return {"error": str(e)}

    def list_pipelines(self) -> list[dict[str, Any]]:
        """List all pipelines."""
        try:
            from agent.platform_pipeline import pipeline_engine
            return [
                {
                    "pipeline_id": p.pipeline_id,
                    "name": p.name,
                    "status": p.status.value,
                    "pipeline_type": p.pipeline_type.value,
                }
                for p in pipeline_engine.list_pipelines()
            ]
        except Exception as e:
            logger.warning(f"Pipeline listing failed: {e}")
            return []

    # ── Agent Mesh ──────────────────────────────────────────────

    def get_mesh_status(self) -> dict[str, Any]:
        """Get agent mesh status."""
        try:
            from agent.agent_mesh import agent_mesh
            return agent_mesh.get_mesh_status()
        except Exception as e:
            logger.warning(f"Mesh status failed: {e}")
            return {"nodes": [], "total_nodes": 0}

    async def delegate_to_mesh(
        self,
        task: str,
        priority: str = "normal",
        target_agent: str = "",
    ) -> dict[str, Any]:
        """Delegate a task to the agent mesh."""
        try:
            from agent.agent_mesh import agent_mesh, MeshTask, TaskPriority
            task_priority = TaskPriority.HIGH if priority == "high" else (
                TaskPriority.LOW if priority == "low" else TaskPriority.NORMAL
            )
            mesh_task = MeshTask(
                title=task[:100],
                description=task,
                priority=task_priority,
                target_agent_id=target_agent if target_agent else None,
            )
            agent_mesh.submit_task(mesh_task)
            node = agent_mesh.route_task(mesh_task)
            return {
                "success": True,
                "task_id": mesh_task.task_id,
                "routed_to": node.config.agent_id if node else None,
                "status": mesh_task.status.value if hasattr(mesh_task, 'status') else "submitted",
            }
        except Exception as e:
            logger.error(f"Mesh delegation failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Learning Loop ───────────────────────────────────────────

    def get_learning_status(self) -> dict[str, Any]:
        """Get learning loop status."""
        try:
            from agent.learning_loop import learning_loop
            return learning_loop.get_status()
        except Exception as e:
            logger.warning(f"Learning status failed: {e}")
            return {"running": False}

    async def trigger_learning_cycle(self, agent_id: str = "", session_id: str = "") -> dict[str, Any]:
        """Trigger a learning cycle."""
        try:
            from agent.learning_loop import learning_loop
            result = await learning_loop.run_cycle(agent_id=agent_id, session_id=session_id)
            return result
        except Exception as e:
            logger.error(f"Learning cycle failed: {e}")
            return {"success": False, "error": str(e)}

    # ── New Module Integrations ─────────────────────────────────

    def get_goal_decomposer_stats(self) -> dict[str, Any]:
        """Get goal decomposer statistics."""
        try:
            from agent.agent_goal_decomposer import goal_decomposer
            return goal_decomposer.get_stats()
        except Exception as e:
            logger.warning(f"Goal decomposer stats failed: {e}")
            return {"total_decompositions": 0}

    def decompose_goal(
        self,
        description: str,
        strategy: str = "dependency_first",
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Decompose a goal using the Goal Decomposer."""
        try:
            from agent.agent_goal_decomposer import goal_decomposer, DecompositionStrategy
            tree = goal_decomposer.decompose(
                description=description,
                strategy=DecompositionStrategy(strategy),
                context=context,
                tags=tags,
            )
            return {
                "goal_id": tree.goal_id,
                "sub_goals": len(tree.sub_goals),
                "execution_order": [[sg_id for sg_id in layer] for layer in tree.execution_order],
                "critical_path": tree.get_critical_path(),
                "progress": tree.get_progress(),
            }
        except Exception as e:
            logger.error(f"Goal decomposition failed: {e}")
            return {"error": str(e)}

    def get_self_reflection_stats(self) -> dict[str, Any]:
        """Get self-reflection engine statistics."""
        try:
            from agent.agent_self_reflection import self_reflection_engine
            return self_reflection_engine.get_stats()
        except Exception as e:
            logger.warning(f"Self-reflection stats failed: {e}")
            return {"total_sessions": 0}

    def start_reflection_session(self, agent_id: str) -> dict[str, Any]:
        """Start a self-reflection session."""
        try:
            from agent.agent_self_reflection import self_reflection_engine
            session = self_reflection_engine.start_session(agent_id=agent_id)
            return {"session_id": session.session_id, "agent_id": session.agent_id}
        except Exception as e:
            logger.error(f"Reflection session failed: {e}")
            return {"error": str(e)}

    def get_memory_consolidator_stats(self) -> dict[str, Any]:
        """Get memory consolidator statistics."""
        try:
            from agent.agent_memory_consolidator import memory_consolidator
            return memory_consolidator.get_stats()
        except Exception as e:
            logger.warning(f"Memory consolidator stats failed: {e}")
            return {"episodic_count": 0}

    def get_context_compressor_stats(self) -> dict[str, Any]:
        """Get context compressor statistics."""
        try:
            from agent.agent_context_compressor import context_compressor
            return context_compressor.get_stats()
        except Exception as e:
            logger.warning(f"Context compressor stats failed: {e}")
            return {"total_chunks": 0}

    # ── Unified Agent System Integration ───────────────────────

    def get_unified_system_stats(self) -> dict[str, Any]:
        """Get unified agent system statistics."""
        try:
            from agent.agent_unified_system import unified_system
            return unified_system.get_stats()
        except Exception as e:
            logger.warning(f"Unified system stats failed: {e}")
            return {"total_executions": 0}

    async def run_unified_cycle(
        self,
        content: str,
        agent_id: str = "",
        mode: str = "reactive",
        enable_tools: bool = True,
        enable_reasoning: bool = True,
        enable_reflection: bool = True,
    ) -> dict[str, Any]:
        """Run a complete unified agent cognitive cycle."""
        try:
            from agent.agent_unified_system import unified_system, SystemMode
            system_mode = SystemMode(mode) if mode in [m.value for m in SystemMode] else SystemMode.REACTIVE
            result = await unified_system.run(
                content=content,
                agent_id=agent_id,
                mode=system_mode,
                enable_tools=enable_tools,
                enable_reasoning=enable_reasoning,
                enable_reflection=enable_reflection,
            )
            return {
                "session_id": result.session_id,
                "mode": result.mode.value,
                "success": result.success,
                "content": result.content,
                "error": result.error,
                "latency_ms": result.latency_ms,
                "metadata": result.metadata,
                "insights": [
                    {"category": i.category, "description": i.description, "severity": i.severity}
                    for i in result.insights
                ] if result.insights else [],
            }
        except Exception as e:
            logger.error(f"Unified cycle failed: {e}")
            return {"success": False, "error": str(e)}

    def get_recent_insights(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent insights from the unified system."""
        try:
            from agent.agent_unified_system import unified_system
            return unified_system.get_recent_insights(limit)
        except Exception as e:
            logger.warning(f"Recent insights failed: {e}")
            return []

    # ── Knowledge Fabric Integration ───────────────────────────

    def get_knowledge_fabric_stats(self) -> dict[str, Any]:
        """Get knowledge fabric statistics."""
        try:
            from agent.agent_knowledge_fabric import knowledge_fabric
            return knowledge_fabric.get_stats()
        except Exception as e:
            logger.warning(f"Knowledge fabric stats failed: {e}")
            return {"total_nodes": 0}

    def query_knowledge_fabric(
        self,
        query_text: str = "",
        domains: list[str] | None = None,
        knowledge_types: list[str] | None = None,
        tags: list[str] | None = None,
        max_results: int = 10,
        include_related: bool = True,
    ) -> dict[str, Any]:
        """Query the knowledge fabric."""
        try:
            from agent.agent_knowledge_fabric import (
                knowledge_fabric, KnowledgeQuery, KnowledgeDomain, KnowledgeType
            )
            query = KnowledgeQuery(
                text=query_text,
                domains=[KnowledgeDomain(d) for d in domains] if domains else [],
                knowledge_types=[KnowledgeType(k) for k in knowledge_types] if knowledge_types else [],
                tags=tags or [],
                max_results=max_results,
                include_related=include_related,
            )
            result = knowledge_fabric.query(query)
            return {
                "query_id": result.query_id,
                "total_matches": result.total_matches,
                "query_time_ms": result.query_time_ms,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "title": n.title,
                        "summary": n.summary,
                        "domain": n.domain.value,
                        "knowledge_type": n.knowledge_type.value,
                        "confidence": n.confidence,
                        "tags": n.tags,
                    }
                    for n in result.nodes
                ],
                "suggested_related": result.suggested_related,
            }
        except Exception as e:
            logger.error(f"Knowledge fabric query failed: {e}")
            return {"error": str(e)}

    def synthesize_knowledge(self, query_text: str, max_sources: int = 5) -> dict[str, Any]:
        """Synthesize knowledge from the fabric."""
        try:
            from agent.agent_knowledge_fabric import knowledge_fabric
            return knowledge_fabric.synthesize(query_text, max_sources)
        except Exception as e:
            logger.error(f"Knowledge synthesis failed: {e}")
            return {"summary": "", "sources": []}

    def auto_link_knowledge(self) -> dict[str, Any]:
        """Auto-link knowledge nodes in the fabric."""
        try:
            from agent.agent_knowledge_fabric import knowledge_fabric
            new_edges = knowledge_fabric.auto_link_nodes()
            return {"new_edges": new_edges}
        except Exception as e:
            logger.error(f"Auto-link failed: {e}")
            return {"new_edges": 0}

    # ── Collaborative Intelligence Integration ─────────────────

    def get_collaborative_intelligence_stats(self) -> dict[str, Any]:
        """Get collaborative intelligence statistics."""
        try:
            from agent.agent_collaborative_intelligence import collaborative_intelligence
            return collaborative_intelligence.get_stats()
        except Exception as e:
            logger.warning(f"Collaborative intelligence stats failed: {e}")
            return {"total_sessions": 0}

    def create_collaboration_session(
        self,
        topic: str,
        goal: str = "",
        mode: str = "roundtable",
        agent_ids: list[str] | None = None,
        shared_knowledge: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a multi-agent collaboration session."""
        try:
            from agent.agent_collaborative_intelligence import (
                collaborative_intelligence, CollaborationMode
            )
            collab_mode = CollaborationMode(mode) if mode in [m.value for m in CollaborationMode] else CollaborationMode.ROUNDTABLE
            session = collaborative_intelligence.create_session(
                topic=topic,
                goal=goal,
                mode=collab_mode,
                agent_ids=agent_ids,
                shared_knowledge=shared_knowledge,
            )
            return {
                "session_id": session.session_id,
                "mode": session.mode.value,
                "topic": session.context.topic,
                "collaborators": len(session.collaborators),
                "phase": session.phase.value,
            }
        except Exception as e:
            logger.error(f"Collaboration session creation failed: {e}")
            return {"error": str(e)}

    def add_collaboration_contribution(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        content_type: str = "text",
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Add a contribution to a collaboration session."""
        try:
            from agent.agent_collaborative_intelligence import collaborative_intelligence
            contribution = collaborative_intelligence.add_contribution(
                session_id=session_id,
                agent_id=agent_id,
                content=content,
                content_type=content_type,
                confidence=confidence,
            )
            if contribution:
                return {
                    "contribution_id": contribution.contribution_id,
                    "agent_id": contribution.agent_id,
                    "role": contribution.role.value,
                    "phase": contribution.phase.value,
                }
            return {"error": "Session not found"}
        except Exception as e:
            logger.error(f"Contribution failed: {e}")
            return {"error": str(e)}

    def build_collaboration_consensus(
        self,
        session_id: str,
        method: str = "weighted_vote",
    ) -> dict[str, Any]:
        """Build consensus in a collaboration session."""
        try:
            from agent.agent_collaborative_intelligence import (
                collaborative_intelligence, ConsensusMethod
            )
            consensus_method = ConsensusMethod(method) if method in [m.value for m in ConsensusMethod] else ConsensusMethod.WEIGHTED_VOTE
            result = collaborative_intelligence.build_consensus(
                session_id=session_id,
                method=consensus_method,
            )
            return {
                "decision": result.decision,
                "confidence": result.confidence,
                "achieved": result.achieved,
                "vote_distribution": result.vote_distribution,
                "dissenting_opinions": result.dissenting_opinions,
                "rounds_needed": result.rounds_needed,
            }
        except Exception as e:
            logger.error(f"Consensus building failed: {e}")
            return {"error": str(e)}

    def synthesize_collaboration(self, session_id: str) -> dict[str, Any]:
        """Synthesize collaboration session results."""
        try:
            from agent.agent_collaborative_intelligence import collaborative_intelligence
            output = collaborative_intelligence.synthesize(session_id)
            return {"output": output}
        except Exception as e:
            logger.error(f"Collaboration synthesis failed: {e}")
            return {"error": str(e)}

    def get_collaboration_summary(self, session_id: str) -> dict[str, Any]:
        """Get a collaboration session summary."""
        try:
            from agent.agent_collaborative_intelligence import collaborative_intelligence
            return collaborative_intelligence.get_session_summary(session_id)
        except Exception as e:
            logger.error(f"Collaboration summary failed: {e}")
            return {"found": False}

    async def run_debate(
        self,
        topic: str,
        agent_ids: list[str],
        max_rounds: int = 3,
    ) -> dict[str, Any]:
        """Run a multi-agent debate."""
        try:
            from agent.agent_collaborative_intelligence import collaborative_intelligence
            session = await collaborative_intelligence.run_debate(
                topic=topic,
                agent_ids=agent_ids,
                max_rounds=max_rounds,
            )
            return {
                "session_id": session.session_id,
                "consensus": {
                    "decision": session.consensus.decision,
                    "confidence": session.consensus.confidence,
                    "achieved": session.consensus.achieved,
                } if session.consensus else None,
                "contributions": len(session.contributions),
                "final_output": session.final_output[:500],
            }
        except Exception as e:
            logger.error(f"Debate failed: {e}")
            return {"error": str(e)}

    async def run_roundtable(
        self,
        topic: str,
        agent_ids: list[str],
        roles: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Run a multi-agent roundtable."""
        try:
            from agent.agent_collaborative_intelligence import (
                collaborative_intelligence, AgentRole
            )
            parsed_roles = None
            if roles:
                parsed_roles = {
                    aid: AgentRole(r) for aid, r in roles.items()
                    if r in [ar.value for ar in AgentRole]
                }
            session = await collaborative_intelligence.run_roundtable(
                topic=topic,
                agent_ids=agent_ids,
                roles=parsed_roles,
            )
            return {
                "session_id": session.session_id,
                "collaborators": [
                    {"agent_id": c.agent_id, "name": c.name, "role": c.role.value}
                    for c in session.collaborators
                ],
                "contributions": len(session.contributions),
                "final_output": session.final_output[:500],
            }
        except Exception as e:
            logger.error(f"Roundtable failed: {e}")
            return {"error": str(e)}

    # ── Comprehensive Execution ─────────────────────────────────

    async def execute(
        self,
        agent_id: str,
        content: str,
        mode: OrchestrationMode = OrchestrationMode.CHAT,
        enable_tools: bool = True,
        enable_reasoning: bool = False,
        profile_id: str = "",
        workspace_id: str = "",
    ) -> OrchestrationResult:
        """Execute a comprehensive orchestration flow.

        This is the primary entry point that routes through all subsystems:
        1. Create session with profile/workspace binding
        2. Route to optimal model via Smart Router
        3. Execute with MCP tools if enabled
        4. Apply governance policies
        5. Record learning observations
        6. Return unified result
        """
        start_time = time.time()

        # Create session
        ctx = self.create_session(
            agent_id=agent_id,
            mode=mode,
            profile_id=profile_id,
            workspace_id=workspace_id,
        )

        try:
            # Route to optimal model
            routing = self.route_task(content, agent_id)
            model_name = routing.get("model", "")

            # Execute pre-hooks
            for hook in self._hooks.get("pre_execute", []):
                try:
                    await hook(ctx)
                except Exception as e:
                    logger.warning(f"Pre-execute hook failed: {e}")

            # Build result based on mode
            result_content = ""
            tool_calls = []

            if mode == OrchestrationMode.AUTONOMOUS:
                auto_result = await self.execute_autonomous_goal(
                    agent_id=agent_id,
                    goal_description=content,
                    session_id=ctx.session_id,
                )
                result_content = auto_result.get("summary", str(auto_result))
            elif mode == OrchestrationMode.PIPELINE:
                pipe_result = await self.execute_pipeline(content)
                result_content = str(pipe_result)
            elif mode == OrchestrationMode.COLLABORATIVE:
                mesh_result = await self.delegate_to_mesh(content)
                result_content = str(mesh_result)
            else:
                # Default chat/task mode - delegate to engine
                try:
                    from agent.shared import orchestrator
                    from database.db import async_session
                    from database.models import Agent as AgentModel
                    from sqlalchemy import select

                    async with async_session() as session:
                        result = await session.execute(
                            select(AgentModel).where(AgentModel.id == agent_id)
                        )
                        agent = result.scalars().first()
                        if agent:
                            engine = orchestrator.get_engine(
                                agent_id=agent.id,
                                agent_name=agent.name,
                                instructions=agent.instructions or "",
                            )
                            response = await engine.chat(
                                content,
                                enable_tools=enable_tools,
                                enable_reasoning=enable_reasoning,
                            )
                            result_content = response if isinstance(response, str) else ""
                        else:
                            result_content = "Agent not found"
                except Exception as e:
                    result_content = f"Execution error: {e}"

            latency_ms = (time.time() - start_time) * 1000

            result = OrchestrationResult(
                session_id=ctx.session_id,
                mode=mode,
                success=True,
                content=result_content,
                tool_calls=tool_calls,
                latency_ms=latency_ms,
                model_used=model_name,
            )

            # Execute post-hooks
            for hook in self._hooks.get("post_execute", []):
                try:
                    await hook(ctx, result)
                except Exception as e:
                    logger.warning(f"Post-execute hook failed: {e}")

            # Record session
            self._session_history.append(result)
            if len(self._session_history) > 1000:
                self._session_history = self._session_history[-500:]

            ctx.status = OrchestrationStatus.COMPLETED
            ctx.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        except Exception as e:
            logger.error(f"Orchestration execution failed: {e}")
            ctx.status = OrchestrationStatus.FAILED

            # Execute error hooks
            for hook in self._hooks.get("on_error", []):
                try:
                    await hook(ctx, str(e))
                except Exception:
                    pass

            latency_ms = (time.time() - start_time) * 1000
            return OrchestrationResult(
                session_id=ctx.session_id,
                mode=mode,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    # ── Hook System ─────────────────────────────────────────────

    def register_hook(self, event: str, callback: Callable):
        """Register a hook callback for lifecycle events."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    def remove_hook(self, event: str, callback: Callable):
        """Remove a hook callback."""
        if event in self._hooks:
            self._hooks[event] = [h for h in self._hooks[event] if h != callback]

    # ── Statistics ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "total_sessions": self._total_sessions,
            "active_sessions": len(self._active_sessions),
            "total_tokens": self._total_tokens,
            "session_history_count": len(self._session_history),
            "recent_success_rate": (
                sum(1 for r in self._session_history[-100:] if r.success) / max(len(self._session_history[-100:]), 1)
                if self._session_history else 0
            ),
            "system_status": {
                "gateway": bool(self.get_gateway_stats()),
                "mesh": bool(self.get_mesh_status().get("nodes")),
                "learning": self.get_learning_status().get("running", False),
            },
        }

    def get_recent_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent orchestration sessions."""
        return [
            {
                "session_id": r.session_id,
                "mode": r.mode.value,
                "success": r.success,
                "latency_ms": r.latency_ms,
                "model_used": r.model_used,
                "tokens_used": r.tokens_used,
            }
            for r in self._session_history[-limit:]
        ]

    # ═══ Code Review Integration ═══════════════════════════════════

    def get_code_review_stats(self) -> dict[str, Any]:
        """Get code review engine statistics."""
        try:
            from agent.agent_code_review import code_review_engine
            return code_review_engine.get_review_stats()
        except Exception as e:
            logger.error(f"Code review stats failed: {e}")
            return {"error": str(e)}

    async def run_code_review(
        self,
        content: str,
        file_path: str = "",
        language: str = "python",
        use_llm: bool = False,
    ) -> dict[str, Any]:
        """Run a code review on the given content."""
        try:
            from agent.agent_code_review import code_review_engine
            result = await code_review_engine.review_code(
                content=content,
                file_path=file_path,
                language=language,
                use_llm=use_llm,
            )
            return result.to_dict()
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return {"error": str(e)}

    async def run_code_review_diff(
        self,
        diff_content: str,
        file_paths: list[str] | None = None,
        language: str = "python",
    ) -> dict[str, Any]:
        """Run a code review on a diff."""
        try:
            from agent.agent_code_review import code_review_engine
            result = await code_review_engine.review_diff(
                diff_content=diff_content,
                file_paths=file_paths or [],
                language=language,
            )
            return result.to_dict()
        except Exception as e:
            logger.error(f"Diff review failed: {e}")
            return {"error": str(e)}

    # ═══ Swarm Orchestration Integration ══════════════════════════

    def get_swarm_orchestrator_stats(self) -> dict[str, Any]:
        """Get swarm orchestrator metrics."""
        try:
            from agent.agent_swarm_orchestrator import swarm_orchestrator
            return swarm_orchestrator.get_swarm_metrics()
        except Exception as e:
            logger.error(f"Swarm stats failed: {e}")
            return {"error": str(e)}

    async def form_agent_swarm(
        self,
        topic: str,
        required_capabilities: list[str] | None = None,
        min_members: int = 3,
        max_members: int = 8,
    ) -> dict[str, Any]:
        """Form a new agent swarm for collaborative problem solving."""
        try:
            from agent.agent_swarm_orchestrator import swarm_orchestrator
            result = await swarm_orchestrator.form_swarm(
                topic=topic,
                required_capabilities=required_capabilities or [],
                min_members=min_members,
                max_members=max_members,
            )
            return {
                "swarm_id": result.session_id,
                "topic": result.topic,
                "member_count": len(result.members),
                "state": result.state.value,
                "members": [m.to_dict() if hasattr(m, 'to_dict') else {"agent_id": m.agent_id, "role": m.role.value} for m in result.members],
            }
        except Exception as e:
            logger.error(f"Swarm formation failed: {e}")
            return {"error": str(e)}

    async def reach_swarm_consensus(
        self,
        swarm_id: str,
        question: str,
        options: list[str] | None = None,
        method: str = "majority",
    ) -> dict[str, Any]:
        """Reach consensus within a swarm."""
        try:
            from agent.agent_swarm_orchestrator import swarm_orchestrator, ConsensusMethod
            cons_method = ConsensusMethod(method) if method in [m.value for m in ConsensusMethod] else ConsensusMethod.MAJORITY
            result = await swarm_orchestrator.reach_consensus(
                swarm_id=swarm_id,
                question=question,
                options=options or [],
                method=cons_method,
            )
            return result.to_dict() if hasattr(result, 'to_dict') else {"decision": result.decision, "confidence": result.confidence}
        except Exception as e:
            logger.error(f"Consensus failed: {e}")
            return {"error": str(e)}

    async def execute_swarm_task(
        self,
        swarm_id: str,
        task_description: str,
    ) -> dict[str, Any]:
        """Execute a task across the swarm."""
        try:
            from agent.agent_swarm_orchestrator import swarm_orchestrator
            result = await swarm_orchestrator.execute_swarm_task(
                swarm_id=swarm_id,
                task_description=task_description,
            )
            return result.to_dict() if hasattr(result, 'to_dict') else {"status": "completed", "task_id": result.task_id}
        except Exception as e:
            logger.error(f"Swarm task failed: {e}")
            return {"error": str(e)}

    # ═══ Platform Console Integration ═════════════════════════════

    async def get_platform_health(self) -> dict[str, Any]:
        """Get comprehensive platform health report."""
        try:
            from agent.platform_console import platform_console
            result = await platform_console.get_system_health()
            return {
                "overall_status": result.overall_status.value,
                "components": {c.component.value: c.status.value for c in result.components},
                "uptime_seconds": result.uptime_seconds,
                "active_agents": result.active_agents,
                "total_requests": result.total_requests,
                "error_rate": result.error_rate,
            }
        except Exception as e:
            logger.error(f"Platform health check failed: {e}")
            return {"error": str(e)}

    async def get_platform_resources(self) -> dict[str, Any]:
        """Get current resource snapshot."""
        try:
            from agent.platform_console import platform_console
            result = await platform_console.get_resource_snapshot()
            return {
                "cpu_percent": result.cpu_percent,
                "memory_percent": result.memory_percent,
                "disk_percent": result.disk_percent,
                "active_connections": result.active_connections,
                "queue_depth": result.queue_depth,
                "token_usage": result.token_usage,
            }
        except Exception as e:
            logger.error(f"Resource snapshot failed: {e}")
            return {"error": str(e)}

    async def get_platform_fleet(self) -> dict[str, Any]:
        """Get agent fleet status."""
        try:
            from agent.platform_console import platform_console
            return await platform_console.get_agent_fleet_status()
        except Exception as e:
            logger.error(f"Fleet status failed: {e}")
            return {"error": str(e)}

    async def run_platform_diagnostics(self) -> dict[str, Any]:
        """Run full system diagnostics."""
        try:
            from agent.platform_console import platform_console
            return await platform_console.run_diagnostics()
        except Exception as e:
            logger.error(f"Diagnostics failed: {e}")
            return {"error": str(e)}

    # ── Team Architect Integration ───────────────────────────────

    def generate_agent_team(
        self,
        domain_description: str,
        team_name: str = "",
        preferred_pattern: str = "",
        complexity: str = "medium",
        scale: str = "small",
    ) -> dict[str, Any]:
        """Generate an agent team architecture from a domain description."""
        try:
            from agent.agent_team_architect import team_architect
            team = team_architect.generate_team(
                domain_description=domain_description,
                team_name=team_name,
                preferred_pattern=preferred_pattern or None,
                context={"complexity": complexity, "scale": scale},
            )
            return {
                "team_id": team.team_id,
                "name": team.name,
                "pattern": team.pattern.value,
                "domain": team.domain,
                "description": team.description,
                "agent_count": len(team.agents),
                "agents": [
                    {
                        "agent_id": a.agent_id,
                        "name": a.name,
                        "role": a.role.value,
                        "description": a.description,
                        "capabilities": a.capabilities,
                        "required_skills": a.required_skills,
                        "model_preference": a.model_preference,
                        "priority": a.priority,
                    }
                    for a in team.agents
                ],
                "communication_protocol": team.communication_protocol.value,
                "coordination_rules": team.coordination_rules,
                "max_parallel_agents": team.max_parallel_agents,
                "version": team.version,
                "created_at": team.created_at,
            }
        except Exception as e:
            logger.error(f"Team generation failed: {e}")
            return {"error": str(e)}

    def get_team_architect_stats(self) -> dict[str, Any]:
        """Get team architect statistics."""
        try:
            from agent.agent_team_architect import team_architect
            return team_architect.get_stats()
        except Exception as e:
            logger.error(f"Team stats failed: {e}")
            return {}

    # ── Evolution Loop Integration ───────────────────────────────

    def capture_learning_event(
        self,
        description: str,
        context: str = "",
        outcome: str = "success",
        complexity_score: float = 0.0,
        agent_id: str = "",
        skills_used: list[str] | None = None,
        novel_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Capture a learning event for the evolution loop."""
        try:
            from agent.agent_evolution_loop import evolution_loop, LearningEvent, LearningTrigger
            event = LearningEvent(
                trigger=LearningTrigger.TASK_COMPLETION,
                agent_id=agent_id,
                description=description,
                context=context,
                outcome=outcome,
                complexity_score=complexity_score,
                skills_used=skills_used or [],
                novel_patterns=novel_patterns or [],
            )
            event_id = evolution_loop.capture_event(event)
            return {"event_id": event_id, "success": True}
        except Exception as e:
            logger.error(f"Learning event capture failed: {e}")
            return {"error": str(e)}

    def get_evolution_stats(self) -> dict[str, Any]:
        """Get evolution loop statistics."""
        try:
            from agent.agent_evolution_loop import evolution_loop
            return evolution_loop.get_stats()
        except Exception as e:
            logger.error(f"Evolution stats failed: {e}")
            return {}

    def check_evolution_nudges(self) -> dict[str, Any]:
        """Check for pending evolution nudges."""
        try:
            from agent.agent_evolution_loop import evolution_loop
            nudges = evolution_loop.check_nudges()
            return {"nudges": nudges, "count": len(nudges)}
        except Exception as e:
            logger.error(f"Nudge check failed: {e}")
            return {"nudges": [], "count": 0}

    # ── Proactive Engine Integration ─────────────────────────────

    async def start_proactive_discovery(self) -> dict[str, Any]:
        """Start the proactive task discovery engine."""
        try:
            from agent.agent_proactive_engine import proactive_engine
            await proactive_engine.start()
            tasks = await proactive_engine.discover_tasks()
            return {
                "status": "started",
                "discovered": len(tasks),
                "tasks": [t.title for t in tasks],
            }
        except Exception as e:
            logger.error(f"Proactive engine start failed: {e}")
            return {"error": str(e)}

    async def stop_proactive_discovery(self) -> dict[str, Any]:
        """Stop the proactive task discovery engine."""
        try:
            from agent.agent_proactive_engine import proactive_engine
            await proactive_engine.stop()
            return {"status": "stopped"}
        except Exception as e:
            logger.error(f"Proactive engine stop failed: {e}")
            return {"error": str(e)}

    def get_proactive_stats(self) -> dict[str, Any]:
        """Get proactive engine statistics."""
        try:
            from agent.agent_proactive_engine import proactive_engine
            return proactive_engine.get_stats()
        except Exception as e:
            logger.error(f"Proactive stats failed: {e}")
            return {}


# Global orchestrator instance
buddy_orchestrator = BuddyOrchestrator()