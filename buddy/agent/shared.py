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
from agent.agent_persona import PersonaRegistry, PersonaProfile, PersonaTrait, InteractionStyle, DecisionStyle, persona_registry
from agent.agent_governance import GovernanceEngine, PolicyRule, PolicyLevel, PolicyAction, PolicyCategory, ApprovalRequest, BudgetTracker, governance_engine
from agent.workspace_manager import WorkSpaceManager, WorkSpace, WorkSpaceConfig, WorkSpaceSnapshot, workspace_manager
from agent.smart_router import SmartRouter, TaskComplexity, ModelTier, ModelConfig, RoutingDecision, smart_router
from agent.identity_core import IdentityCore, IdentityRegistry, MemoryLayer, TraitCategory, IdentityTrait, EpisodicEntry, SemanticNode, ProceduralPattern, identity_registry
from agent.agent_mesh import AgentMesh, MeshNode, MeshNodeConfig, MeshNodeState, MeshTask, TaskPriority, DelegationStrategy, agent_mesh
from agent.learning_loop import LearningLoop, ObservationEngine, ExtractionEngine, CompoundingEngine, EvolutionEngine, NudgeEngine, ObservationType, SkillSource, NudgePriority, NudgeCategory, learning_loop
from agent.kgraph import KnowledgeGraph, EntityStore, RelationStore, InferenceEngine, EntityType, RelationType, Entity, Relation, knowledge_graph
from agent.experience_engine import ExperienceEngine, ExperienceRecorder, ExperienceReplayBuffer, AgentTrajectoryCompressor, ExperienceEvolver, ExperienceAnalytics, ExperienceKind, ExperienceResult, EmotionalValence, experience_engine
from agent.collab_space import CollaborationSpace, CollaborationRoom, CollaborationSession, ArtifactBoard, ConsensusEngine, CollaborationAnalytics, RoomType, RoomState, SessionStatus, MessageRole, ArtifactType, collab_space
from agent.context_engine import ContextEngine, ContextAssembler, ContextCompressor, ContextInjector, ContextWindow, ContextAnalytics, ContextSource, ContextPriority, CompressionStrategy, context_engine
from agent.automation_core import AutomationCore, AutomationRegistry, CronScheduler, AutomationRunner, EventWatcher, AutomationAnalytics, AutomationType, TriggerType, AutomationLifecycle, automation_core
from agent.skill_fabric import SkillFabric, SkillForge, SkillBundleManager, SkillMarket, SkillComposer, SkillAnalytics, SkillType, SkillLifecycleStatus, PricingModel, skill_fabric
from agent.user_model import UserModelEngine, user_model_engine, TraitDimension, ConfidenceLevel, UserTrait, UserProfile, InteractionSnapshot
from agent.evolving_skills import SelfEvolvingSkillRegistry, EvolvingSkill, SkillVariant, SkillEvolutionStage, VariantStrategy, ExecutionRecord, evolving_skills
from agent.agent_protocol import ProtocolEngine, MessageRouter, EventBus, ComponentRegistry, StateSynchronizer, ProtocolMessage, MessageType, MessagePriority, ComponentState, ComponentInfo, protocol_engine
from agent.subagent import SubAgentMesh, Workstream, WorkstreamStatus, WorkstreamManager, get_subagent_mesh
from agent.sandbox import SandboxEngine, SandboxSession, SandboxConfig, SandboxPolicy, get_sandbox_engine
from agent.streaming import StreamingEngine, StreamSession, StreamEvent, StreamEventType, get_streaming_engine
from agent.tool_executor import ToolExecutor, ToolRegistry, ToolDefinition, ToolCategory, ToolRisk, ToolExecution, get_tool_executor
from agent.browser_agent import BrowserAgent, BrowserSession, BrowserAction, BrowserState, get_browser_agent
from agent.terminal_agent import TerminalAgent, TerminalSession, TerminalConfig, TerminalMode, TerminalResult, get_terminal_agent
from agent.plan_executor import PlanExecutor, ExecutionPlan, PlanStep, PlanStatus, StepType, PlanGenerator, get_plan_executor
from agent.model_orchestrator import ModelOrchestrator, ModelRouter, ModelConfig, ModelProvider, ModelCapability, ModelRequest, ModelResponse, get_model_orchestrator
from agent.deployment import DeploymentPipeline, Deployment, DeploymentConfig, DeploymentStatus, DeploymentTarget, get_deployment_pipeline
from agent.telemetry import TelemetryEngine, MetricRegistry, TraceCollector, MetricType, TraceLevel, TraceSpan, get_telemetry_engine
from agent.mcp_connector import MCPConnector, MCPServerConnection, MCPServerConfig, MCPTool, MCPResource, MCPConnectionState, MCPTransport, get_mcp_connector
from agent.integration_hub import IntegrationHub, Integration, IntegrationConfig, IntegrationType, AuthMethod, get_integration_hub
from agent.product_composer import ProductComposer, ProductDefinition, ProductComponent, ComponentType, ProductStatus, get_product_composer
from agent.agent_orchestrator import AgentOrchestrator, SubAgentProfile, Workstream, WorkstreamType, Squad, AgentLifecycle, agent_orchestrator
from agent.dream_mode import DreamMode, DreamSession, DreamPhase, MemoryEntry, ProactiveTask, dream_mode
from agent.white_memory import WhiteMemory, WhiteMemoryEntry, MemoryCategory, MemoryLifecycleStage, MemoryProvenance, MemoryAuditEntry, white_memory

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

# New core module instances
sandbox_engine = get_sandbox_engine()
streaming_engine = get_streaming_engine()
tool_executor = get_tool_executor()
browser_agent = get_browser_agent()
terminal_agent = get_terminal_agent()
plan_executor = get_plan_executor()
model_orchestrator = get_model_orchestrator()
deployment_pipeline = get_deployment_pipeline()
telemetry_engine = get_telemetry_engine()
mcp_connector = get_mcp_connector()
integration_hub = get_integration_hub()
product_composer = get_product_composer()

# New agent orchestration and memory modules
agent_orchestrator_instance = agent_orchestrator
dream_mode_instance = dream_mode
white_memory_instance = white_memory