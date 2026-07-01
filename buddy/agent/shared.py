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
from agent.agent_reflection import AgentReflectionEngine, ReflectionRecord, ReflectionDimension, ErrorCategory, ReflectionStatus, QualityScore, DetectedError, reflection_engine
from agent.agent_intent import AgentIntentEngine, IntentResult, IntentCategory, IntentComplexity, IntentUrgency, IntentEntity, IntentSession, intent_engine
from agent.agent_fleet import AgentFleetManager, FleetAgent, FleetAgentStatus, FleetHealth, FleetLoadReport, FleetHealthReport, fleet_manager
from agent.event_pipeline import EventPipeline, PipelineEvent, EventSource, EventPriority, EventSubscription, DeadLetterEntry, event_pipeline
from agent.knowledge_network import KnowledgeNetwork, KnowledgeEntry, KnowledgeType, KnowledgeStatus, VerificationLevel, KnowledgeTopic, knowledge_network
from agent.agent_reasoning import AgentReasoningEngine, ReasoningTrace, ReasoningStep, ReasoningStrategy, Hypothesis, reasoning_engine
from agent.agent_tool_composer import AgentToolComposer, ToolPipeline, PipelineStage, ToolNode, PipelineResult, ExecutionMode as ToolExecutionMode, tool_composer
from agent.agent_context_manager import AgentContextManager, ContextItem, ContextType, ContextPriority, ContextSnapshot, context_manager
from agent.model_proxy import ModelProxyLayer, ModelProfile, ProviderType, ModelCapability, ProxyStrategy, ProxyRequest, ProxyResponse, model_proxy
from agent.skill_compiler import SkillCompiler, SkillDefinition, SkillStatus, SkillLanguage, SkillParameter, CompilationResult, skill_compiler
from agent.unified_runtime import UnifiedAgentRuntime, RuntimeSession, RuntimeMode, RuntimePhase, unified_runtime
from agent.agent_deep_reasoning import DeepReasoningEngine, DeepReasoningResult, ThoughtNode, ReasoningBranch, BranchStatus, VoteStrategy, deep_reasoning
from agent.agent_self_improve import SelfImprovementEngine, SynthesizedSkill, AgentNudge, NudgeType, NudgePriority, SkillOrigin, SkillLifecycle, ImprovementMetrics, self_improvement
from agent.agent_session import AgentSessionManager, CollaborativeSession, SessionMessage, SessionArtifact, SessionParticipant, SessionRole, SessionState, MessageRole, agent_session_manager
from agent.agent_unified_brain import UnifiedBrain, BrainContext, BrainPerception, BrainCognition, BrainAction, BrainReflection, BrainCycleResult, BrainMode, PerceptionType, CognitivePhase, unified_brain
from agent.agent_platform_core import PlatformCore, PlatformConfig, RuntimeInstance, RuntimeState, SandboxEnvironment, SandboxType, HealthReport, HealthStatus, PlatformAlert, AlertSeverity, ContextSyncEvent, platform_core

# New AI-native agent modules
from agent.agent_goal_decomposer import goal_decomposer, GoalDecomposer, GoalTree, SubGoal, DecompositionStrategy, SubGoalType, DependencyType
from agent.agent_self_reflection import self_reflection_engine, SelfReflectionEngine, SelfReflectionSession, ActionRecord, SelfReflectionInsight, ReflectionDepth, ReflectionPerspective, InsightType, ImprovementPriority
from agent.agent_memory_consolidator import memory_consolidator, MemoryConsolidator, MemoryEntry, ConsolidatedMemory, ConsolidationStrategy, MemoryImportance
from agent.agent_context_compressor import context_compressor, ContextCompressor, ContextChunk, CompressionResult, CompressionStrategy, ContentPriority

# Skill Forge, Policy Gateway, Dream Consolidator, Cross Review, Cost Optimizer
from agent.agent_skill_forge import get_skill_forge, reset_skill_forge, AgentSkillForge, SkillOrigin, SkillStatus, TestStatus, EvolutionStage, SkillCandidate, SkillTest, SkillEvolution, SkillDependency
from agent.agent_policy_gateway import get_policy_gateway, reset_policy_gateway, AgentPolicyGateway, PolicyLevel, PolicyAction, PolicyCategory, PolicyStatus, PolicyRule, ApprovalRequest, PolicyEvaluation, PolicyAuditEntry
from agent.agent_dream_consolidator import get_dream_consolidator, reset_dream_consolidator, AgentDreamConsolidator, DreamPhase, ConsolidationStrategy, MemoryTier, SnapshotType, MemoryEntry, DreamSession, MemorySnapshot, ConsolidationResult
from agent.agent_cross_review import get_cross_review, reset_cross_review, AgentCrossReview, ReviewStrategy, ReviewStatus, SeverityLevel, ReviewVerdict, ReviewItem, ReviewReport, ReviewSession, ReviewerProfile
from agent.agent_cost_optimizer import get_cost_optimizer, reset_cost_optimizer, AgentCostOptimizer, TaskComplexity, ModelTier, RoutingStrategy, OptimizationMetric, ModelProfile, TaskProfile, RoutingDecision, CostRecord, OptimizationReport

# Lifecycle Hooks, Session Fork, Alignment Engine, Context Provider, Interruptible Executor
from agent.agent_lifecycle_hooks import get_lifecycle_hooks, reset_lifecycle_hooks, AgentLifecycleHooks, HookEvent, HookPhase, HookPriority, HookExecutionMode, HookStatus, HookResult, HookFailurePolicy, HookContext, HookExecutionResult, HookRegistration, HookInvocation, HookChain
from agent.agent_session_fork import get_session_fork, reset_session_fork, AgentSessionFork, ForkStrategy, ForkStatus, MergeStrategy, MergeConflictPolicy, SessionNodeRole, ForkRelation, SessionMessage, ForkPoint, SessionNode, MergeRequest, MergeConflict, ForkTree
from agent.agent_alignment_engine import get_alignment_engine, reset_alignment_engine, AgentAlignmentEngine, AlignmentDimension, AlignmentStrength, AlignmentSource, AlignmentChange, AlignmentAction, ConflictResolution, AlignmentTrait, AlignmentProfile, AlignmentSignal, AlignmentCheck, AlignmentDriftReport, CalibrationSession
from agent.agent_context_provider import get_context_provider, reset_context_provider, AgentContextProvider, ContextSource, ContextPriority, EnrichmentStrategy, ContextFormat, AssemblyMode, QueryIntent, ProviderStatus, ContextFragment, ContextQuery, ContextBundle, SourceConnector, Disambiguation, ProviderStats
from agent.agent_interruptible import get_interruptible_executor, reset_interruptible_executor, AgentInterruptibleExecutor, ExecutionState, CancellationReason, InterruptSignal, CheckpointType, ResumeStrategy, ExecutionPriority, CancellationScope, CancellationToken, Checkpoint, ExecutionHandle, CancellationRequest, ExecutionStep

# Action Space, Goal Manager, Dialogue Manager, Benchmark Engine, Belief Engine
from agent.agent_action_space import get_action_space, reset_action_space, AgentActionSpace, ActionCategory, ActionStatus, FeasibilityLevel, ConstraintType, ValidationResult, RiskLevel, ActionConstraint, ActionDefinition, FeasibilityReport, ActionExecution, ActionSpaceStats
from agent.agent_goal_manager import get_goal_manager, reset_goal_manager, AgentGoalManager, GoalStatus, GoalPriority, GoalType, GoalOrigin, AchievementLevel, DependencyType, GoalMetric, GoalDependency, Goal, GoalReview, GoalManagerStats
from agent.agent_dialogue_manager import get_dialogue_manager, reset_dialogue_manager, AgentDialogueManager, DialogueState, DialogueAct, TurnType, ConversationPhase, StrategyType, TopicStatus, Topic, DialogueTurn, DialogueContext, TransitionRule, DialogueManagerStats
from agent.agent_benchmark import get_benchmark_engine, reset_benchmark_engine, AgentBenchmarkEngine, MetricCategory, EvaluationStatus, ScoreScale, ComparisonResult, BenchmarkType, TrendDirection, MetricDefinition, MetricResult, EvaluationRun, Benchmark, ComparisonReport, TrendAnalysis, BenchmarkStats
from agent.agent_belief_state import get_belief_engine, reset_belief_engine, AgentBeliefEngine, BeliefStatus, EvidenceType, EvidenceStrength, RevisionType, BeliefCategory, ConfidenceLevel, Evidence, Belief, BeliefRevision, BeliefNetwork, ConsistencyCheck, BeliefEngineStats

# Tracing Pipeline, Quota Manager, Causal Engine, Temporal Engine, Anomaly Detector
from agent.agent_tracing_pipeline import get_tracing_pipeline, reset_tracing_pipeline, AgentTracingPipeline, SpanKind, SpanStatus, SamplingDecision, TraceFlags, SpanContext, SpanEvent, SpanLink, TraceSpan, Trace, TraceStats
from agent.agent_quota_manager import get_quota_manager, reset_quota_manager, AgentQuotaManager, QuotaType, QuotaStatus, RetryStrategy, BackpressureLevel, QuotaLimit, QuotaUsage, RateLimitWindow, RetryPolicy, RetryAttempt, QuotaManagerStats
from agent.agent_causal_reasoning import get_causal_engine, reset_causal_engine, AgentCausalEngine, CausalRelation, VariableType, InterventionStatus, EvidenceStrength as CausalEvidenceStrength, CounterfactualResult, CausalVariable, CausalEdge, CausalGraph, Intervention, Counterfactual, ConfounderReport, CausalEngineStats
from agent.agent_temporal_reasoning import get_temporal_engine, reset_temporal_engine, AgentTemporalEngine, TemporalRelation, TemporalConstraintType, EventStatus, TimeWindowType, TimeInterval, TemporalEvent, TemporalConstraint, TemporalPlan, ConsistencyReport, TemporalEngineStats
from agent.agent_anomaly_detector import get_anomaly_detector, reset_anomaly_detector, AgentAnomalyDetector, AnomalyType, AnomalySeverity, BaselineStatus, DiagnosisStatus, MetricDirection, BehaviorMetric, BehaviorBaseline, AnomalyEvent, DriftReport, DiagnosisReport, AnomalyEngineStats
from agent.agent_scenario_simulator import get_scenario_simulator, reset_scenario_simulator, AgentScenarioSimulator, ScenarioType, SimulationStatus, OutcomeType, VariableType as SimVariableType, DistributionType, ScenarioVariable, ScenarioAction, Scenario, SimulationOutcome, SimulationReport, SimulatorStats
from agent.agent_explanation_synthesizer import get_explanation_synthesizer, reset_explanation_synthesizer, AgentExplanationSynthesizer, ExplanationType, AudienceLevel, ConfidenceLevel, ExplanationStatus, EvidenceType, Evidence, ExplanationFactor, Explanation, ExplanationRequest, DecisionTrace, SynthesizerStats
from agent.agent_knowledge_distiller import get_knowledge_distiller, reset_knowledge_distiller, AgentKnowledgeDistiller, KnowledgeType, CompressionLevel, DistillationStatus, SourceType, TransferStatus, KnowledgeSource, DistilledKnowledge, DistillationSession, KnowledgeTransfer, KnowledgeQuery, DistillerStats
from agent.agent_attention_allocator import get_attention_allocator, reset_attention_allocator, AgentAttentionAllocator, AttentionMode, PriorityLevel, FocusType, AllocationStatus, DecayFunction, AttentionTarget, AttentionBudget, AttentionAllocation, AttentionSnapshot, AttentionEvent, AllocatorStats
from agent.agent_ethical_deliberation import get_ethical_deliberator, reset_ethical_deliberator, AgentEthicalDeliberator, EthicalFramework, DeliberationStatus, VerdictType, StakeholderImpact, PrincipleCategory, Stakeholder, EthicalPrinciple, ActionConsequence, EthicalDilemma, FrameworkAssessment, EthicalVerdict, DeliberatorStats
from agent.agent_concept_formation import get_concept_formation_engine, reset_concept_formation_engine, AgentConceptFormationEngine, ConceptType, FormationStatus, SimilarityMetric, AbstractionLevel, ClusterMethod, ConceptInstance, Concept, ConceptCluster, ConceptHierarchy, FormationSession, FormationStats
from agent.agent_analogy_engine import get_analogy_engine, reset_analogy_engine, AgentAnalogyEngine, MappingType, AnalogyStatus, DomainType, ConfidenceLevel as AnalogyConfidenceLevel, TransferStatus, DomainEntity, DomainRelation, Domain, AnalogyMapping, Analogy, AnalogyStats
from agent.agent_curiosity_engine import get_curiosity_engine, reset_curiosity_engine, AgentCuriosityEngine, CuriosityType, NoveltyMetric, ExplorationMode, CuriosityStatus, InformationGapType, NoveltyScore, InformationGap, ExplorationTarget, ExplorationResult, CuriosityProfile, CuriosityStats
from agent.agent_mental_simulation import get_mental_simulation_engine, reset_mental_simulation_engine, AgentMentalSimulationEngine, SimulationType, SimulationStatus, ModelType, OutcomeValence, ConfidenceLevel as SimConfidenceLevel, ModelState, SimulationStep, SimulationOutcome, MentalModel, Simulation, SimulationStats
from agent.agent_narrative_engine import get_narrative_engine, reset_narrative_engine, AgentNarrativeEngine, NarrativeType, NarrativeStatus, PlotArc, NarrativeTense, PerspectiveType, NarrativeEvent, NarrativeCharacter, NarrativeTheme, NarrativeThread, Narrative, NarrativeStats
from agent.agent_cognitive_mapping import get_cognitive_mapping_engine, reset_cognitive_mapping_engine, AgentCognitiveMapping, EnvironmentType, SpatialRelation, MapStatus, AnchorType, DeltaType, SpatialAnchor, MapPlace, MapEdge, CognitiveMap, MapDelta, MappingStats
from agent.agent_cognitive_bias_detector import get_bias_detector, reset_bias_detector, AgentCognitiveBiasDetector, BiasType, BiasSeverity, DebiasingStrategy, AuditStatus, EvidenceRole, BiasEvidence, BiasDetection, DebiasingAction, BiasProfile, ReasoningAudit, DetectorStats
from agent.agent_cognitive_affordance import get_affordance_engine, reset_affordance_engine, AgentCognitiveAffordance, AffordanceSource, AffordanceStatus, ConstraintType, SignatureType, RankingMetric, AffordanceConstraint, AffordanceSignature, Affordance, AffordanceContext, AffordanceMap, AffordanceStats
from agent.agent_cognitive_scaffolding import get_scaffolding_engine, reset_scaffolding_engine, AgentCognitiveScaffolding, ScaffoldingLevel, ScaffoldingStrategy, CompetenceLevel, FadingTrigger, ScaffoldStatus, CompetenceAssessment, FadingPlan, Scaffold, ScaffoldingSession, LearnerProfile, ScaffoldingStats
from agent.agent_affective_engine import get_affective_engine, reset_affective_engine, AgentAffectiveEngine, EmotionType, RegulationStrategy, AppraisalDimension, AffectiveMode, TriggerType, Appraisal, AffectiveState, RegulationAction, AffectiveTrajectory, AffectiveProfile, AffectiveStats
from agent.agent_cognitive_style_transfer import get_style_transfer_engine, reset_style_transfer_engine, AgentCognitiveStyleTransfer, StyleDimension, TransferStatus, FidelityMode, BlendStrategy, SourceType, ValidationStatus, StyleFeature, StyleFingerprint, CognitiveStyle, StyleTransfer, StyleBlend, TransferStats
from agent.agent_cognitive_prime import get_prime_engine, reset_prime_engine, AgentCognitivePrime, PrimeType, PrimeStrength, ActivationMode, InterferenceType, EffectDirection, PrimeTarget, PrimeActivation, PrimeEffect, PrimeContext, PrimeSession, PrimeStats
from agent.agent_cognitive_phase_transition import get_phase_transition_engine, reset_phase_transition_engine, AgentCognitivePhaseTransition, TransitionPhase, ParameterType, CatalystType, TransitionStatus, OrderParameter, CriticalPoint, TransitionCatalyst, PhaseTransitionEvent, TransitionContext, TransitionStats
from agent.agent_cognitive_gravity import get_gravity_engine, reset_gravity_engine, AgentCognitiveGravity, AttractorType, MassContribution, TrajectoryStatus, FieldState, ResonanceMode as GravityResonanceMode, IdeaMass, AttractorBasin, ThoughtTrajectory, GravitationalField, GravityContext, GravityStats
from agent.agent_cognitive_resonance import get_resonance_engine, reset_resonance_engine, AgentCognitiveResonance, ResonanceType, ResonanceMode, DetectionMethod, AmplificationStatus, ResonanceSignature, ResonanceEvent, AmplificationProfile, ResonanceCluster, ResonanceContext, ResonanceStats
from agent.agent_cognitive_workload import get_workload_engine, reset_workload_engine, AgentCognitiveWorkload, LoadType, WorkloadState, InterferenceType as WorkloadInterferenceType, AllocationStrategy, RecoveryAction, LoadMeasurement, WorkloadSnapshot, InterferenceAssessment, AllocationDecision, RecoveryPlan, WorkloadProfile, WorkloadStats
from agent.agent_cognitive_entropy import get_entropy_engine, reset_entropy_engine, AgentCognitiveEntropy, EntropyKind, EntropyRegime, FluxDirection, InferencePrinciple, CompressionStatus, DistributionSample, EntropyFluxRecord, InferenceResult, CompressionTrace, EntropyProfile, EntropyStats
from agent.agent_cognitive_horizon import get_horizon_engine, reset_horizon_engine, AgentCognitiveHorizon, KnowledgeDomain, EpistemicState, HorizonProximity, BoundaryResponse, CompetenceLevel, DomainCompetence, HorizonProbe, BoundaryEvent, LearningRequest, DeferDecision, HorizonProfile, HorizonStats
from agent.agent_cognitive_momentum import get_momentum_engine, reset_momentum_engine, AgentCognitiveMomentum, TrajectoryState, PerturbationType, MomentumRegime, EscapeStrategy, ProgressSignal, MomentumVector, TrajectoryPoint, StuckStateDetection, PerturbationEvent, EscapePlan, MomentumProfile, MomentumStats
from agent.agent_cognitive_friction import get_friction_engine, reset_friction_engine, AgentCognitiveFriction, FrictionSource, FrictionRegime, TransitionType, LubricationStrategy, RecoveryState, FrictionMeasurement, TransitionEvent, FrictionSnapshot, LubricationPlan, RecoveryAssessment, FrictionProfile, FrictionStats
from agent.agent_cognitive_tension import get_tension_engine, reset_tension_engine, AgentCognitiveTension, TensionKind, TensionState, ResolutionMode, TensionPolarity, HoldingStrategy, TensionPole, TensionPair, TensionSnapshot, ResolutionAttempt, HoldingDecision, TensionProfile, TensionStats
from agent.agent_cognitive_depth import get_depth_engine, reset_depth_engine, AgentCognitiveDepth, DepthDimension, DepthRegime, DeepeningMove, SurfacingMove, DepthTrajectory, DepthProbe, DepthAssessment, DeepeningAction, SurfacingAction, DepthTrajectoryRecord, DepthProfile, DepthStats
from agent.agent_cognitive_coherence import get_coherence_engine, reset_coherence_engine, AgentCognitiveCoherence, CoherenceFacet, CoherenceRegime, RelationType as CoherenceRelationType, RepairStrategy, CoherenceTrajectory, CoherenceNode, CoherenceRelation, CoherenceSnapshot, RepairAttempt, TrajectoryRecord, CoherenceProfile, CoherenceStats

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

# New agent reflection, intent, fleet, event, and knowledge modules
reflection_engine_instance = reflection_engine
intent_engine_instance = intent_engine
fleet_manager_instance = fleet_manager
event_pipeline_instance = event_pipeline
knowledge_network_instance = knowledge_network

# New reasoning, tool composer, context, model proxy, and skill compiler modules
reasoning_engine_instance = reasoning_engine
tool_composer_instance = tool_composer
agent_context_manager_instance = context_manager
model_proxy_instance = model_proxy
skill_compiler_instance = skill_compiler

# Unified runtime instance
unified_runtime_instance = unified_runtime

# New evolution, white memory, experience, protocol, and experiment modules
from agent.agent_evolution import AgentEvolutionEngine, EvolutionStage, EvolutionSkill, EvolutionPattern, OperationOutcome, OperationRecord, evolution_engine
from agent.white_memory import WhiteMemoryStore, MemoryCategory, MemoryStatus, MemoryEntry, MemorySnapshot, white_memory
from agent.experience_db import ExperienceDatabase, ExperienceType, ExperienceOutcome, ExperienceQuality, ExperienceRecord, ExperienceCluster, experience_db
from agent.agent_protocol import AgentProtocol, MessageType, MessagePriority, ProtocolVersion, AgentMessage as ProtoMessage, Conversation, AgentSession, agent_protocol
from agent.experiment_tracker import ExperimentTracker, ExperimentStatus, ExperimentType, MetricType, Experiment, ExperimentVariant, TrialResult, experiment_tracker

evolution_engine_instance = evolution_engine
white_memory_instance = white_memory
experience_db_instance = experience_db
agent_protocol_instance = agent_protocol
experiment_tracker_instance = experiment_tracker

# New unified brain and platform core instances
unified_brain_instance = unified_brain
platform_core_instance = platform_core

# Runtime coordinator instance
from agent.agent_runtime_coordinator import RuntimeCoordinator, CoordinatorState, ExecutionMode, ModuleType, CoordinatorConfig, ExecutionContext, ExecutionResult, CoordinatorStats, runtime_coordinator

# New AI-native unified agent system modules
from agent.agent_unified_system import (
    UnifiedAgentSystem, SystemMode, CognitivePhase, ExecutionStrategy,
    AgentCapability, PerceptionFrame, CognitiveState, ActionStep,
    ExecutionPlan, ReflectionInsight, SystemResult, unified_system,
)
from agent.agent_knowledge_fabric import (
    KnowledgeFabric, KnowledgeDomain, KnowledgeType, KnowledgeStatus,
    RelationType, KnowledgeNode, KnowledgeEdge, TopicCluster,
    KnowledgeQuery, KnowledgeQueryResult, knowledge_fabric,
)
from agent.agent_collaborative_intelligence import (
    CollaborativeIntelligence, CollaborationMode, AgentRole, ConsensusMethod,
    CollaborationPhase, Collaborator, CollaborationContext, Contribution,
    Vote, ConsensusResult, CollaborationSession, collaborative_intelligence,
)
from agent.agent_team_architect import (
    TeamArchitect, TeamConfiguration, TeamPattern, AgentRole as TeamAgentRole,
    CommunicationProtocol, TeamEvolutionDelta, TeamValidationResult,
    AgentDefinition, team_architect,
)
from agent.agent_evolution_loop import (
    EvolutionLoop, SkillDefinition, SkillStatus, LearningTrigger,
    LearningEvent, SkillImprovement, UserModel, NudgeType,
    ImprovementType, EvolutionConfig, evolution_loop,
)
from agent.agent_proactive_engine import (
    ProactiveEngine, ProactiveTask, ProactiveConfig, DiscoverySource,
    TaskCategory, TaskPriority, TaskStatus, ExecutionMode,
    MonitorConfig, proactive_engine,
)

# AI-native sentience and presence modules
from agent.agent_sentience_core import (
    AgentSentienceCore, SentienceState, PerceptionChannel, CognitiveMode,
    VolitionPriority, ActionType, PerceptionFrame, CognitiveContext,
    VolitionOutput, ActionResult, ReflectionInsight, SentienceCycle,
    SentienceConfig, SentienceStats, sentience_core,
)
from agent.agent_capability_mesh import (
    CapabilityMesh, CapabilityDomain, CapabilityType, MaturityLevel,
    CompositionStrategy, MeshNodeState, CapabilityContract, CapabilityVersion,
    CapabilityDefinition, CapabilityMatch, CompositionStep, CompositionPlan,
    StepResult, CompositionResult, ProviderReputation, MeshNode, MeshStats,
    capability_mesh,
)
from agent.agent_presence_engine import (
    PresenceEngine, PresenceState, ActivityType, AvailabilityMode,
    ContextCarryover, AgentProfile, PresenceStatus, ActivityRecord,
    AvailabilitySchedule, SessionContext, PresenceEvent, PresenceStats,
    presence_engine,
)

# Agent orchestration and lifecycle modules
from agent.agent_feedback_orchestrator import (
    FeedbackOrchestrator, FeedbackSource, FeedbackSeverity, ActionType,
    ActionStatus, TargetModule, RoutingRuleType, FeedbackSignal,
    RoutingRule, FeedbackAction, ActionResult, SignalTrend,
    FeedbackAnomaly, FeedbackAnalytics, FeedbackOrchestratorStats,
    feedback_orchestrator,
)
from agent.agent_session_commander import (
    SessionCommander, SessionGroup, BatchOpType, BatchOpStatus,
    SessionState, BatchOperation, SessionSnapshot, SessionBranch,
    SessionTemplate, SessionCommanderStats, session_commander,
)
from agent.agent_runtime_scheduler import (
    RuntimeScheduler, TaskPriority, DependencyType, TaskStatus,
    ScheduledTask, TaskDependency, ResourceQuota, ScheduleSlot,
    SchedulePlan, SchedulerStats, runtime_scheduler,
)
from agent.agent_workspace_nexus import (
    WorkspaceNexus, WorkspaceStatus, SubsystemType, ConnectionStatus,
    ContextPriority, Workspace, WorkspaceTemplate, SubsystemConnection,
    ContextFlow, WorkspaceAnalytics, WorkspaceNexusStats, workspace_nexus,
)

# Buddy Orchestrator instance
from agent.buddy_orchestrator import buddy_orchestrator, BuddyOrchestrator, OrchestrationMode, OrchestrationStatus, OrchestrationContext, OrchestrationResult

# Next-generation cognitive and platform modules
from agent.agent_cognitive_engine import (
    AgentCognitiveEngine, CognitivePhase, CognitiveStrategy, IntentLevel,
    ExecutionStrategy, ContextSource, ConfidenceLevel, PhaseState,
    CognitiveLoad, CognitiveEngineConfig, PerceptionInput, PerceptionResult,
    UnderstandingResult, ReasoningResult, PlanResult, ExecutionResult,
    ReflectionResult, ContextFragment, ContextFusion, IntentResolution,
    ToolSelection, ResponseSynthesis, CognitiveMetrics, CognitiveCycleResult,
    get_cognitive_engine, reset_cognitive_engine,
)
from agent.agent_platform_orchestrator import (
    PlatformOrchestrator, ServiceType, ServiceHealth, WorkflowState,
    TriggerType, StepExecutionMode, IntegrationStatus, CredentialType,
    PublishingState, DistributionChannel, MetricType, AlertSeverity,
    WorkspaceRole, CollaborationMode, ServiceVersion, ServiceHeartbeat,
    ServiceRegistration, WorkflowTrigger, WorkflowStep, WorkflowDefinition,
    WorkflowExecution, WorkflowTemplate, IntegrationConnection,
    PublishingContent, PlatformMetric, PerformanceAlert, CostReport,
    OptimizationSuggestion, Workspace,
    get_platform_orchestrator, reset_platform_orchestrator,
)
from agent.agent_skill_compiler_pro import (
    SkillCompilerPro, SkillType, SkillStatus, ExecutionState,
    CompositionStrategy, ExecutionStrategy as SkillExecutionStrategy,
    DependencyType as SkillDependencyType, ParamType, TestResult,
    BenchmarkMetric, SkillDefinition, SkillParameter, SkillSchema,
    SkillMetadata, SkillInstruction, CompilationResult, ExecutionStep,
    ExecutionResult as SkillExecutionResult, SkillDependency,
    CompositionPlan, CompositionResult, MarketplaceListing,
    TestCase, TestSuiteResult, BenchmarkResult, skill_compiler_pro,
)

# Comprehensive AI-native runtime modules
from agent.agent_runtime_store import (
    AgentRuntimeStore, StoreBackend, SnapshotType, StateStatus,
    CompressionMode, RuntimeStoreConfig, StateSnapshot, StateDiff,
    AgentStateRecord, StoreStats, get_runtime_store, reset_runtime_store,
)
from agent.agent_conversation_memory import (
    AgentConversationMemory, MessageRole, MemoryImportance, ConversationStatus,
    SearchMode, ConversationMemoryConfig, ConversationMessage, ConversationTopic,
    ConversationSummary, Conversation, SearchResult, ConversationMemoryStats,
    get_conversation_memory, reset_conversation_memory,
)
from agent.agent_streaming_hub import (
    AgentStreamingHub, StreamProtocol, StreamEventType, StreamState,
    PipelineStage, StreamingHubConfig, StreamEvent, StreamSession,
    StreamPipeline, StreamingHubStats, get_streaming_hub, reset_streaming_hub,
)
from agent.agent_tool_network import (
    AgentToolNetwork, ToolCategory, ToolRisk, ToolStatus,
    ExecutionStrategy as NetworkExecStrategy, CacheStrategy,
    ToolNetworkConfig, ToolParameter, ToolDefinition, ToolExecution,
    ToolChain, ToolNetworkStats, get_tool_network, reset_tool_network,
)
from agent.agent_code_interpreter import (
    AgentCodeInterpreter, Language, ExecutionStatus, SessionMode,
    CodeInterpreterConfig, CodeExecution, CodeSession, CodeInterpreterStats,
    get_code_interpreter, reset_code_interpreter,
)
from agent.agent_analytics_engine import (
    AgentAnalyticsEngine, MetricType, MetricCategory, InsightType,
    InsightSeverity, TimeRange, AnalyticsConfig, MetricPoint, MetricSeries,
    AnalyticsInsight, AgentPerformance, AnalyticsSummary,
    get_analytics_engine, reset_analytics_engine,
)
from agent.agent_execution_compiler import (
    ExecutionCompiler, ExecutionStrategy, NodeType, NodeStatus,
    CompileOptimization, CachePolicy, ExecutionCompilerConfig,
    ExecutionNode, ExecutionGraph, CompileResult, ExecutionStats,
    get_execution_compiler, reset_execution_compiler,
)
from agent.agent_verification_pipeline import (
    VerificationPipeline, VerificationStage, VerdictCode, SeverityLevel,
    CorrectionStrategy, FactSource, VerificationPipelineConfig,
    VerificationIssue, StageResult, VerificationResult, VerificationProfile,
    VerificationStats, get_verification_pipeline, reset_verification_pipeline,
)
from agent.agent_multi_model_conductor import (
    MultiModelConductor, TaskComplexity, ModelTier, RoutingStrategy,
    ProviderHealth, EnsembleMethod, ConductorConfig, ModelEndpoint,
    RoutingDecision, ModelExecution, ConductorStats,
    get_multi_model_conductor, reset_multi_model_conductor,
)
from agent.agent_context_weaver import (
    ContextWeaver, ContextSource, ContextPriority, WeaveStrategy,
    CompressionMethod, ContextWeaverConfig, ContextItem, ContextBundle,
    WeaveConfig, WeaverStats, get_context_weaver, reset_context_weaver,
)
from agent.agent_autonomy_framework import (
    AutonomyFramework, AutonomyLevel, ActionCategory, ApprovalStatus,
    RiskLevel, GuardrailType, EscalationReason, AutonomyConfig,
    AutonomyPolicy, Guardrail, ApprovalRequest, ActionAuditEntry,
    TrustScore, AutonomyStats, get_autonomy_framework, reset_autonomy_framework,
)
from agent.agent_platform_intelligence_hub import (
    PlatformIntelligenceHub, IntelligenceType, IntelligencePriority,
    IntelligenceStatus, ConfidenceLevel, SignalSource, IntelligenceHubConfig,
    IntelligenceSignal, IntelligenceReport, HubStats,
    get_intelligence_hub, reset_intelligence_hub,
)
from agent.agent_adaptive_workflows import (
    AdaptiveWorkflowEngine, WorkflowNodeType, WorkflowStatus, TriggerType,
    OptimizationStrategy, WorkflowEngineConfig, WorkflowNode,
    WorkflowDefinition, WorkflowExecution, WorkflowTemplate, WorkflowStats,
    get_adaptive_workflows, reset_adaptive_workflows,
)
from agent.agent_cross_connector import (
    PlatformCrossConnector, IntegrationProtocol, ConnectionState,
    CommunicationMode, DataFormat, CrossConnectorConfig,
    IntegrationConnection, SchemaMapping, IntegrationEvent,
    IntegrationRequest, ConnectorStats,
    get_cross_connector, reset_cross_connector,
)

# Singleton instances for new runtime modules
runtime_store = get_runtime_store()
conversation_memory = get_conversation_memory()
streaming_hub = get_streaming_hub()
tool_network = get_tool_network()
code_interpreter = get_code_interpreter()
analytics_engine = get_analytics_engine()
execution_compiler = get_execution_compiler()
verification_pipeline = get_verification_pipeline()
multi_model_conductor = get_multi_model_conductor()
context_weaver = get_context_weaver()
autonomy_framework = get_autonomy_framework()
intelligence_hub = get_intelligence_hub()
adaptive_workflows = get_adaptive_workflows()
cross_connector = get_cross_connector()

# Advanced reasoning and intent modules
from agent.agent_chain_of_thought import (
    ChainOfThoughtEngine, ReasoningStrategy, ThoughtType, ThoughtStep,
    QualityScore, ThoughtResult, get_chain_of_thought, reset_chain_of_thought,
)
from agent.agent_intent_resolution import (
    IntentResolutionEngine, IntentCategory, ComplexityLevel, UrgencyLevel,
    SignalType, Entity, SubIntent, IntentResult, IntentProfile,
    get_intent_resolution, reset_intent_resolution,
)
from agent.agent_dynamic_adaptation import (
    DynamicAdaptationEngine, DeviationType, AdaptationStrategy, Severity,
    DeviationReport, AdaptedPlan, MonitorSession, AdaptationLesson,
    get_dynamic_adaptation, reset_dynamic_adaptation,
)
from agent.agent_uncertainty_quantifier import (
    UncertaintyQuantifier, UncertaintySource, VerificationPriority, RiskLevel,
    CalibrationMethod, UncertaintyAssessment, CalibratedAssessment,
    Alternative, RiskProfile, UncertaintyMetrics,
    get_uncertainty_quantifier, reset_uncertainty_quantifier,
)

chain_of_thought = get_chain_of_thought()
intent_resolution = get_intent_resolution()
dynamic_adaptation = get_dynamic_adaptation()
uncertainty_quantifier = get_uncertainty_quantifier()

# Platform intelligence and resilience modules
from agent.agent_federated_knowledge import (
    FederatedKnowledgeExchange, KnowledgeType, AccessLevel, MergeStrategy,
    ConflictResolutionMethod, KnowledgeShare, Subscription, PublishedEntry,
    MergedKnowledge, ResolvedKnowledge, FederationStats,
    get_federated_knowledge, reset_federated_knowledge,
)
from agent.agent_emergent_behavior import (
    EmergentBehaviorDetector, PatternType, PatternStatus, PatternCategory,
    Observation, EmergentPattern, PatternClassification, UtilityAssessment,
    PromotedPattern, SuppressedPattern, EmergenceReport,
    get_emergent_behavior, reset_emergent_behavior,
)
from agent.agent_performance_autotuner import (
    PerformanceAutotuner, ComponentType as AutotunerComponentType,
    BottleneckType, Severity as AutotunerSeverity, OptimizationStrategy,
    RiskLevel as AutotunerRiskLevel, PerformanceProfile, Bottleneck,
    OptimizationRecommendation, OptimizationResult, TuningResult, TuningReport,
    get_performance_autotuner, reset_performance_autotuner,
)
from agent.agent_platform_resilience import (
    PlatformResilienceEngine, ComponentType as ResilienceComponentType,
    FailureType, ComponentStatus, CircuitState, RecoveryStrategy,
    HealthStatus, FailureReport, RecoveryResult, CircuitBreaker,
    ResilienceReport, SimulationResult,
    get_platform_resilience, reset_platform_resilience,
)

federated_knowledge = get_federated_knowledge()
emergent_behavior = get_emergent_behavior()
performance_autotuner = get_performance_autotuner()
platform_resilience = get_platform_resilience()

# AI-native personal companion modules
from agent.agent_personal_memory import (
    PersonalMemoryEngine, MemoryDimension, MemoryStrength, AccessLevel,
    ConsolidationStrategy, MemoryEntry, MemoryChain, PersonalProfile,
    ConsolidationReport, get_personal_memory, reset_personal_memory,
)
from agent.agent_voice_interface import (
    VoiceInterfaceEngine, VoiceCommand, AudioFormat, VoiceProfile,
    EmotionTone, SpeechLanguage, TranscriptionResult, SynthesisRequest,
    SynthesisResult, ToneAnalysis, VoiceSession, get_voice_interface,
    reset_voice_interface,
)
from agent.agent_document_intelligence import (
    DocumentIntelligenceEngine, DocumentFormat, DocumentCategory,
    ExtractionType, DocumentStatus, DocumentInfo, ExtractionResult,
    DocumentSummary, SearchResult, CompareResult,
    get_document_intelligence, reset_document_intelligence,
)
from agent.agent_notification_hub import (
    NotificationHub, NotificationChannel, NotificationPriority,
    NotificationStatus, NotificationTopic, Notification, Subscription,
    NotificationTemplate, Digest, get_notification_hub,
    reset_notification_hub,
)
from agent.agent_prompt_studio import (
    PromptStudio, PromptType, PromptCategory, OptimizationStrategy,
    ABTestStatus, Prompt, PromptVersion, ABTest, OptimizationResult,
    PromptChain, get_prompt_studio, reset_prompt_studio,
)
from agent.agent_terminal_interface import (
    TerminalInterface, TerminalMode, OutputFormat, CommandCategory,
    TerminalCommand, CommandResult, REPLSession, TerminalScript,
    ScriptResult, get_terminal_interface, reset_terminal_interface,
)
from agent.agent_reasoning_network import (
    AgenticReasoningNetwork, ReasoningStrategy, NodeStatus, PathStatus,
    ReasoningNode, ReasoningPath, ReasoningResult, NetworkStats,
    get_reasoning_network, reset_reasoning_network,
)
from agent.agent_synthesis_engine import (
    CollaborativeSynthesisEngine, FusionStrategy, ConflictResolution,
    ContributionRole, AgentContribution, SynthesisSession, SynthesisResult,
    get_synthesis_engine, reset_synthesis_engine,
)
from agent.agent_research_engine import (
    AutonomousResearchEngine, ResearchPhase, SourceType, EvidenceQuality,
    ResearchSource, ResearchHypothesis, ResearchTask, ResearchProject,
    ResearchReport, get_research_engine, reset_research_engine,
)
from agent.agent_learning_loop import (
    InteractiveLearningLoop, FeedbackType, LearningSignal, AdaptationType,
    LearningEvent, AdaptationRule, LearningSession, UserPreferenceProfile,
    get_learning_loop, reset_learning_loop,
)
from agent.agent_memory_graph import (
    ContextualMemoryGraph, EdgeType, NodeCategory, RetrievalStrategy,
    MemoryNode, MemoryEdge, MemorySubgraph, RetrievalResult,
    get_memory_graph, reset_memory_graph,
)
from agent.agent_understanding_engine import (
    MultiModalUnderstandingEngine, InputModality, ProcessingMode,
    ModalityInput, UnderstandingResult, FusionResult,
    get_understanding_engine, reset_understanding_engine,
)
from agent.agent_hypothesis_engine import (
    AgentHypothesisEngine, HypothesisStatus, EvidenceType, TestOutcome,
    Evidence, HypothesisTest, Hypothesis, HypothesisSession,
    get_hypothesis_engine, reset_hypothesis_engine,
)
from agent.agent_negotiation import (
    AgentNegotiationProtocol, NegotiationStrategy, RoundType, DelegateRole,
    ResolutionType, Delegate, Proposal, NegotiationRound, NegotiationSession,
    get_negotiation_protocol, reset_negotiation_protocol,
)
from agent.agent_ai_twin import (
    PlatformAITwin, MirrorDimension, SyncFrequency, MirrorAccuracy,
    MirrorSnapshot, LearningSignal, TwinProfile,
    get_ai_twin, reset_ai_twin,
)
from agent.agent_code_synthesis import (
    AgentCodeSynthesis, SynthesisStage, LanguageTarget, TestStatus,
    CodeComponent, ArchitecturePlan, SynthesisProject,
    get_code_synthesis, reset_code_synthesis,
)
from agent.agent_workflow_composer import (
    PlatformWorkflowComposer, NodeType, ExecutionStatus, TriggerType,
    WorkflowNode, WorkflowEdge, WorkflowExecution, WorkflowDefinition,
    get_workflow_composer, reset_workflow_composer,
)

personal_memory = get_personal_memory()
voice_interface = get_voice_interface()
document_intelligence = get_document_intelligence()
notification_hub = get_notification_hub()
prompt_studio = get_prompt_studio()
terminal_interface = get_terminal_interface()
reasoning_network = get_reasoning_network()
synthesis_engine = get_synthesis_engine()
research_engine = get_research_engine()
learning_loop = get_learning_loop()
memory_graph = get_memory_graph()
understanding_engine = get_understanding_engine()
hypothesis_engine = get_hypothesis_engine()
negotiation_protocol = get_negotiation_protocol()
ai_twin = get_ai_twin()
code_synthesis = get_code_synthesis()
workflow_composer = get_workflow_composer()

# Skill Forge, Policy Gateway, Dream Consolidator, Cross Review, Cost Optimizer instances
skill_forge = get_skill_forge()
policy_gateway = get_policy_gateway()
dream_consolidator = get_dream_consolidator()
cross_review = get_cross_review()
cost_optimizer = get_cost_optimizer()

# Lifecycle Hooks, Session Fork, Alignment Engine, Context Provider, Interruptible Executor instances
lifecycle_hooks = get_lifecycle_hooks()
session_fork = get_session_fork()
alignment_engine = get_alignment_engine()
context_provider = get_context_provider()
interruptible_executor = get_interruptible_executor()

# Action Space, Goal Manager, Dialogue Manager, Benchmark Engine, Belief Engine instances
action_space = get_action_space()
goal_manager = get_goal_manager()
dialogue_manager = get_dialogue_manager()
benchmark_engine = get_benchmark_engine()
belief_engine = get_belief_engine()

# Tracing Pipeline, Quota Manager, Causal Engine, Temporal Engine, Anomaly Detector instances
tracing_pipeline = get_tracing_pipeline()
quota_manager = get_quota_manager()
causal_engine = get_causal_engine()
temporal_engine = get_temporal_engine()
anomaly_detector = get_anomaly_detector()

# Scenario Simulator, Explanation Synthesizer, Knowledge Distiller,
# Attention Allocator, Ethical Deliberator instances
scenario_simulator = get_scenario_simulator()
explanation_synthesizer = get_explanation_synthesizer()
knowledge_distiller = get_knowledge_distiller()
attention_allocator = get_attention_allocator()
ethical_deliberator = get_ethical_deliberator()
concept_formation_engine = get_concept_formation_engine()
analogy_engine = get_analogy_engine()
curiosity_engine = get_curiosity_engine()
mental_simulation_engine = get_mental_simulation_engine()
narrative_engine = get_narrative_engine()
cognitive_mapping_engine = get_cognitive_mapping_engine()
bias_detector = get_bias_detector()
affordance_engine = get_affordance_engine()
scaffolding_engine = get_scaffolding_engine()
affective_engine = get_affective_engine()
style_transfer_engine = get_style_transfer_engine()
prime_engine = get_prime_engine()
phase_transition_engine = get_phase_transition_engine()
gravity_engine = get_gravity_engine()
resonance_engine = get_resonance_engine()
workload_engine = get_workload_engine()
entropy_engine = get_entropy_engine()
horizon_engine = get_horizon_engine()
momentum_engine = get_momentum_engine()
friction_engine = get_friction_engine()
tension_engine = get_tension_engine()
depth_engine = get_depth_engine()
coherence_engine = get_coherence_engine()