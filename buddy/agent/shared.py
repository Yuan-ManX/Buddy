"""Buddy Shared Agent Instances — singleton orchestrator, tool, and plan registries"""
from agent.orchestrator import Orchestrator
from agent.skills import SkillsRegistry
from agent.routing import model_router
from agent.autopilot import autopilot_engine
from agent.context import context_manager
from agent.tools import tool_registry
from agent.reasoning import ReasoningLoop, ReasoningStyle
from agent.planning import planning_engine
from agent.mcp import mcp_registry
from agent.approval import approval_engine
from agent.events import event_bus, EventType, Event
from agent.nexus import BuddyNexus, NexusConfig, PlatformType, RuntimeStatus, RuntimeInfo
from agent.forge import BuddyForge, SkillCategory as ForgeSkillCategory, SkillStatus as ForgeSkillStatus
from agent.identity import BuddyIdentity, PersonaType, IdentityProfile
from agent.trajectory import BuddyTrajectory, TraceAction
from agent.squad import BuddySquads, SquadStatus, MemberRole
from agent.guard import BuddyGuard, guard_system, GuardAction, Severity as GuardSeverity
from agent.guardrails import GuardrailsEngine, guardrails_engine, GuardrailResult, ContentCategory, ViolationType
from agent.pulse import BuddyPulse, pulse_system, HealthStatus, ComponentHealth, SystemHealth
from agent.websocket import ws_manager
from agent.self_improvement import self_improvement
from agent.gateway import gateway_hub
from agent.daemon import daemon_manager
from agent.swarm import SwarmEngine, SwarmRole, SwarmSession
from agent.runtime_hub import RuntimeHub, runtime_hub, RuntimeBackend, RuntimeStatus as RtStatus
from agent.scheduler import BuddyScheduler, buddy_scheduler, ScheduleType as SchedType
from agent.studio import BuddyStudio, buddy_studio, StudioStatus, MemoryEntry, MemoryCategory, MemorySnapshot
from agent.workflow import WorkflowEngine, workflow_engine, TaskState, WorkflowPriority, BlockerType, WorkflowTask
from agent.pipeline import pipeline_engine, PipelineEngine, PipelineDefinition, PipelineRun, StepConfig, StepKind, StepStatus, ErrorPolicy
from agent.semantic_cache import semantic_cache, SemanticCache
from agent.capability import capability_registry, CapabilityRegistry, CapabilityDomain, ProficiencyLevel
from agent.knowledge_graph import KnowledgeGraph
from agent.memory_sync import MemorySyncHub, SyncGroup, SharedMemory
from agent.platform_hub import PlatformHub, platform_hub, PlatformSubsystem, SubsystemStatus, PlatformEvent
from agent.session_search import SessionSearcher, SessionEntry, SessionRecap, session_searcher
from agent.enterprise import EnterpriseHub, Workspace, WorkspaceStats, enterprise_hub
from agent.cost_tracker import CostTracker, CostEntry, CostSummary, OptimizationSuggestion, cost_tracker
from agent.proactive import ProactiveDiscoveryEngine
from agent.agent_evolution import AgentEvolution, ExperienceType, ExperienceOutcome
from agent.comm_protocol import AgentCommProtocol, agent_comm, MessageType as CommMessageType, MessagePriority as CommMessagePriority, AgentMessage, DelegationRequest, ContextShare
from agent.resource_manager import ResourceManager, resource_manager, ResourceType as ResType, ResourceStatus as ResStatus, ResourceQuota, ResourceAlert
from agent.agent_self import agent_self_registry, AgentSelfRegistry, AgentSelf, SelfTrait, SelfTraitCategory, TraitOrigin, BehavioralPattern
from agent.plugin_system import plugin_system, PluginSystem, PluginManifest, PluginInstance, PluginStatus, PluginPermission
from agent.im_hub import im_hub, IMHub, IMPlatform, IMConnectionStatus, IMMessageType, IMChatMessage, IMChannelConfig
from agent.skills_marketplace import skills_marketplace, SkillsMarketplace, MarketplaceSkill, SkillCategory as MktSkillCategory, SkillPricing, SkillReview
from agent.task_queue import task_queue, TaskQueue, Job, JobType, JobPriority, JobStatus as QJobStatus, BatchJob
from agent.runtime_backend import runtime_backend_hub, RuntimeBackendHub, RuntimeBackend as RtBackend, RuntimeBackendKind, RuntimeConfig, RuntimeInstance, RuntimeStatus as RtInstStatus
from agent.agent_intelligence import AgentIntelligence, IntelligenceConfig, IntelligenceMode, ReasoningStrategy
from agent.agent_core import AgentCore, AgentCoreConfig, AgentState, ExecutionContext, AgentCapability, ExecutionStep, ExecutionTrace, AgentInsight, ProactiveSignal
from agent.agent_synthesis import AgentSynthesis, agent_synthesis, SynthesisMode, InsightType, SynthesisInsight, AgentContribution
from agent.agent_runtime import AgentRuntime, RuntimeRegistry, RuntimeConfig, RuntimeState, ExecutionMode, RuntimeEventType, RuntimeMetrics, runtime_registry

orchestrator = Orchestrator()
skills_registry = SkillsRegistry()
context_manager_instance = context_manager
swarm_engine = SwarmEngine()

nexus = BuddyNexus(NexusConfig())
forge = BuddyForge()
identity = BuddyIdentity()
trajectory = BuddyTrajectory()
squads = BuddySquads()
knowledge_graph = KnowledgeGraph()

memory_sync_hub = MemorySyncHub(orchestrator=orchestrator)

# Global intelligence core instance
intelligence = AgentIntelligence(IntelligenceConfig(
    max_reasoning_steps=10,
    max_parallel_branches=5,
    enable_self_critique=True,
    enable_experience_replay=True,
    enable_strategy_adaptation=True,
))