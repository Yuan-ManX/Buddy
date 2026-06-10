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
- WebSocketManager: Real-time streaming and event broadcast
- SelfImprovementEngine: Autonomous skill generation from interaction patterns
- PersonaManager: Dynamic persona switching with behavior control
- GatewayHub: Multi-platform messaging integration
- DaemonManager: Background agent runtime management
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
from agent.websocket import WebSocketManager, ws_manager, MessageType as WsMessageType, WebSocketMessage, Connection
from agent.self_improvement import SelfImprovementEngine, self_improvement, LearningLoop, SkillStatus as LearningSkillStatus, PatternType, InteractionPattern, CandidateSkill
from agent.persona import PersonaManager, Persona, ToneMode, VerbosityLevel, create_persona_from_preset, PRESET_PERSONAS
from agent.gateway import GatewayHub, gateway_hub, MessagePlatform, GatewayMessage, GatewaySession, PlatformAdapter, TelegramAdapter, WebAdapter
from agent.daemon import DaemonManager, daemon_manager, DaemonStatus, AgentRuntime

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
    "WebSocketManager", "ws_manager", "WsMessageType", "WebSocketMessage", "Connection",
    "SelfImprovementEngine", "self_improvement", "LearningLoop", "LearningSkillStatus", "PatternType", "InteractionPattern", "CandidateSkill",
    "PersonaManager", "Persona", "ToneMode", "VerbosityLevel", "create_persona_from_preset", "PRESET_PERSONAS",
    "GatewayHub", "gateway_hub", "MessagePlatform", "GatewayMessage", "GatewaySession", "PlatformAdapter", "TelegramAdapter", "WebAdapter",
    "DaemonManager", "daemon_manager", "DaemonStatus", "AgentRuntime",
    "orchestrator", "skills_registry",
]