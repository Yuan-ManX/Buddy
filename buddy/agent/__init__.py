"""Buddy Agent Package — AI-native agent system

Core components:
- AgentEngine: LLM reasoning and tool execution
- HierarchicalMemory: 3-tier memory (short-term, long-term, episodic)
- Orchestrator: Multi-agent coordination and delegation
- SkillsRegistry: Composable skills with pipeline support
- TaskLifecycle: 6-state task management
- ModelRouter: Intelligent model routing based on complexity
- SubAgentOrchestrator: Parallel task delegation
- AutopilotEngine: Scheduled background task execution
- ContextManager: Intelligent context window management
- AgentWorkspace: Sandboxed file operations and code execution
- DreamEngine: Background memory consolidation and creative synthesis
- BuddyNexus: Central coordination hub for runtime management
- BuddyForge: Self-improving skill creation and pattern detection
- BuddyIdentity: Personal AI identity with hierarchical memory
- BuddyTrajectory: Execution trace capture and compression
- BuddySquads: Collaborative agent teams with trust scoring
- BuddyGuard: Safety monitoring, rate limiting, and audit system
- BuddyPulse: Health monitoring and metrics collection
"""
from agent.engine import AgentEngine
from agent.memory import HierarchicalMemory, MemorySystem, MemoryLayer
from agent.orchestrator import Orchestrator
from agent.skills import SkillsRegistry
from agent.task import TaskLifecycle, TaskStatus, TaskKind
from agent.routing import ModelRouter, TaskComplexity, ModelTier, RoutingDecision, model_router
from agent.subagent import SubAgent, SubAgentOrchestrator, SubAgentStatus, SubAgentResult
from agent.autopilot import AutopilotEngine, AutopilotConfig, AutopilotStatus, AutopilotTrigger, autopilot_engine
from agent.context import ContextManager, ContextConfig, context_manager
from agent.workspace import AgentWorkspace, WorkspaceFile, ExecutionResult
from agent.dream import DreamEngine, DreamPhase, DreamInsight, DreamCycleResult
from agent.shared import orchestrator, skills_registry
from agent.guard import BuddyGuard, guard_system
from agent.pulse import BuddyPulse, pulse_system, HealthStatus

__all__ = [
    "AgentEngine",
    "HierarchicalMemory", "MemorySystem", "MemoryLayer",
    "Orchestrator",
    "SkillsRegistry",
    "TaskLifecycle", "TaskStatus", "TaskKind",
    "ModelRouter", "TaskComplexity", "ModelTier", "RoutingDecision", "model_router",
    "SubAgent", "SubAgentOrchestrator", "SubAgentStatus", "SubAgentResult",
    "AutopilotEngine", "AutopilotConfig", "AutopilotStatus", "AutopilotTrigger", "autopilot_engine",
    "ContextManager", "ContextConfig", "context_manager",
    "AgentWorkspace", "WorkspaceFile", "ExecutionResult",
    "DreamEngine", "DreamPhase", "DreamInsight", "DreamCycleResult",
    "BuddyGuard", "guard_system",
    "BuddyPulse", "pulse_system", "HealthStatus",
    "orchestrator", "skills_registry",
]