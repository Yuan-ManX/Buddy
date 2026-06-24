export type TabView = 'chat' | 'tasks' | 'skills' | 'memory' | 'autopilot' | 'subagents' | 'tools' | 'plans' | 'workspace' | 'dream' | 'mcp' | 'collaboration' | 'approval' | 'events' | 'overview' | 'dashboard' | 'nexus' | 'forge' | 'identity' | 'trajectory' | 'squads' | 'guard' | 'pulse' | 'persona' | 'learning' | 'gateway' | 'daemon' | 'swarm' | 'knowledge' | 'runtime' | 'scheduler' | 'studio' | 'workflow' | 'board' | 'compounding' | 'whitememory' | 'pipeline' | 'capability' | 'kgraph' | 'memorysync' | 'phub' | 'costs' | 'workspaces' | 'agentdashboard' | 'proactive' | 'metacognition' | 'evolution' | 'kanban' | 'activity' | 'runtimemonitor' | 'skillmanager' | 'agent-comparison' | 'agentself' | 'plugins' | 'imhub' | 'marketplace' | 'taskqueue' | 'runtimebackend' | 'agentcore' | 'synthesis' | 'intelligence' | 'runtimepanel' | 'skillcompiler' | 'conversationsearch' | 'governance' | 'smartrouter' | 'identitycore' | 'agentmesh' | 'learningloop' | 'experience' | 'collabspace' | 'contextengine' | 'automation' | 'skillfabric' | 'usermodel' | 'evolvingskills' | 'subagentmesh' | 'protocol' | 'sandbox' | 'streaming' | 'toolexec' | 'browseragent' | 'terminalagent' | 'planexec' | 'modelorch' | 'deployment' | 'telemetry' | 'mcpconnector' | 'integrationhub' | 'productcomposer' | 'agentorchestrator' | 'dreammode' | 'whitememory' | 'reflection' | 'intent' | 'fleet' | 'eventpipeline' | 'knowledgenetwork' | 'reasoning' | 'modelproxy' | 'toolcomposer' | 'contextmanager' | 'unifiedconsole' | 'experiments' | 'unifiedbrain' | 'platformcore' | 'runtimecoordinator' | 'unifiedagent' | 'agentflow' | 'profile' | 'mcptools' | 'goalDecomposer' | 'selfReflection' | 'memoryConsolidator' | 'contextCompressor' | 'commandCenter' | 'unifiedSystem' | 'knowledgeFabric' | 'collaborativeIntelligence' | 'agentDashboard' | 'knowledgeGraphViz' | 'skillExplorer' | 'codeReview' | 'swarmConsole' | 'platformConsole';

export interface Agent {
  id: string;
  name: string;
  role: string;
  personality: string;
  instructions: string;
  avatar: string;
  is_active: boolean;
  created_at: string;
}

export interface Message {
  id: string;
  agent_id: string;
  conversation_id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  agent_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  agent_id: string;
  title: string;
  status: 'queued' | 'dispatched' | 'running' | 'completed' | 'failed' | 'cancelled';
  kind: 'chat' | 'direct' | 'autopilot' | 'quick';
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  conversation_id: string | null;
  attempt: number;
  max_attempts: number;
  parent_task_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Skill {
  name: string;
  description: string;
  category: string;
  parameters: Record<string, string>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ChatResponse {
  agent_id: string;
  content: string;
  conversation_id: string;
  tool_calls: Array<Record<string, unknown>>;
}

export interface HealthResponse {
  status: string;
  service: string;
  active_agents: number;
}

export interface MemoryEntry {
  id: string;
  agent_id: string;
  content: string;
  memory_type: string;
  importance: number;
  tags: string[];
  created_at: string;
}

export interface MemoryStats {
  agent_id: string;
  total_memories: number;
  average_importance: number;
  layer_distribution: Record<string, number>;
  tags: Array<{ tag: string; count: number }>;
  consolidation_threshold: number;
  short_term_buffer_size: number;
}

export interface AutopilotConfig {
  id: string;
  agent_id: string;
  name: string;
  description: string;
  trigger: 'cron' | 'interval' | 'webhook' | 'manual';
  schedule: string;
  task_template: string;
  status: 'active' | 'paused' | 'completed' | 'failed';
  max_runs: number;
  run_count: number;
  last_run_at: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceFile {
  name: string;
  path: string;
  content?: string;
  language: string;
  size: number;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceStats {
  total_files: number;
  total_memories: number;
  total_skills: number;
  last_activity: string;
}

export interface Workspace {
  id: string;
  name: string;
  description: string;
  filesystem_path: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  stats?: WorkspaceStats;
}

export interface WorkspaceStatsOverview {
  total_workspaces: number;
  active_workspaces: number;
  total_files: number;
  total_memories: number;
}

export interface SubAgentResult {
  agent_id: string;
  task: string;
  result: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  tokens_used: number;
  started_at: string;
  completed_at: string;
}

export interface SystemOverview {
  service: string;
  version: string;
  agents: { total: number; active: number };
  tasks: { total: number; active: number };
  conversations: { total: number };
  memories: { total: number };
  autopilots: { total: number };
  plans: { total: number };
  mcp_servers: { total: number };
  templates: { total: number };
  costs: { total_cost: number; total_tokens: number; total_tasks: number; agent_count: number; estimated_monthly: number };
  routing: {
    total_requests: number;
    tier_distribution: Record<string, number>;
    average_cost: string;
  };
  tools: { total_executions: number; successful: number; failed: number; success_rate: string };
  orchestrator: { active_agents: number; trust_relationships: number; collaboration_threads: number };
  nexus: { total_runtimes: number; connected_platforms: number; monitor_running: boolean; total_requests: number; total_errors: number };
  forge: { total_skills: number; total_patterns: number; patterns_ready_for_promotion: number; total_executions: number; avg_success_rate: number };
  squads: { total_squads: number; total_members: number; total_tasks_processed: number; avg_trust_score: number };
  trajectory: { total_compressed: number; active_traces: number; successful: number; failed: number; success_rate: number; avg_quality_score: number };
  compressor: { total_trajectories_compressed: number; total_patterns_detected: number; average_compression_ratio: number; average_quality_score: number; total_bytes_saved: number; patterns_by_type: Record<string, number>; stored_trajectories: number; stored_patterns: number };
}

// ── Nexus Types ──

export interface RuntimeInfo {
  runtime_id: string;
  platform: string;
  status: string;
  agent_id: string;
  capabilities: string[];
  connected_at: string;
  last_heartbeat: string;
  request_count: number;
  error_count: number;
}

export interface NexusSummary {
  total_runtimes: number;
  connected_platforms: number;
  platform_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  monitor_running: boolean;
  total_requests: number;
  total_errors: number;
}

// ── Forge Types ──

export interface ForgedSkill {
  skill_id: string;
  name: string;
  description: string;
  category: string;
  status: string;
  tags: string[];
  versions: Array<{
    version: number;
    prompt_template: string;
    parameters: Array<{ name: string; type: string; description: string; required: boolean }>;
    created_at: string;
    success_rate: number;
    execution_count: number;
    avg_tokens: number;
    avg_latency_ms: number;
  }>;
  parent_skill_id: string;
  author_agent_id: string;
  created_at: string;
  updated_at: string;
  total_executions: number;
  average_rating: number;
  latest_success_rate: number;
}

export interface InteractionPattern {
  pattern_id: string;
  description: string;
  trigger_phrases: string[];
  action_sequence: string[];
  frequency: number;
  confidence: number;
  suggested_category: string;
  first_seen: string;
  last_seen: string;
}

export interface ForgeStats {
  total_skills: number;
  total_patterns: number;
  patterns_ready_for_promotion: number;
  by_category: Record<string, number>;
  by_status: Record<string, number>;
  total_executions: number;
  avg_success_rate: number;
}

// ── Identity Types ──

export interface IdentityProfile {
  profile_id: string;
  agent_id: string;
  user_id: string;
  display_name: string;
  attributes: Record<string, {
    key: string;
    value: unknown;
    category: string;
    confidence: number;
    source: string;
    evidence_count: number;
    first_observed: string;
    last_updated: string;
    is_locked: boolean;
  }>;
  attributes_count: number;
  personas: Array<{
    name: string;
    type: string;
    description: string;
    tone: string;
    verbosity: string;
    expertise_areas: string[];
    is_active: boolean;
    created_at: string;
  }>;
  active_persona: string;
  total_interactions: number;
  created_at: string;
  updated_at: string;
}

// ── Trajectory Types ──

export interface ExecutionTrace {
  trace_id: string;
  agent_id: string;
  task_id: string;
  step_count: number;
  status: string;
  started_at: string;
  completed_at: string;
  total_tokens: number;
  total_latency_ms: number;
  quality_score: number;
}

export interface CompressedTrajectory {
  original_trace_id: string;
  agent_id: string;
  summary: string;
  key_decisions: string[];
  tools_used: string[];
  success: boolean;
  quality_score: number;
  num_steps_original: number;
  num_steps_compressed: number;
  tokens_saved: number;
  patterns_extracted: string[];
  compressed_at: string;
}

// ── Squad Types ──

export interface SquadMember {
  agent_id: string;
  agent_name: string;
  role: string;
  trust_score: number;
  tasks_completed: number;
  tasks_failed: number;
  success_rate: number;
  expertise: string[];
  joined_at: string;
}

export interface DiscussionThread {
  thread_id: string;
  squad_id: string;
  task_id: string;
  topic: string;
  status: string;
  message_count: number;
  created_by: string;
  created_at: string;
  resolved_at: string;
  resolution: string;
}

export interface Squad {
  squad_id: string;
  name: string;
  description: string;
  status: string;
  member_count: number;
  members: SquadMember[];
  leader_id: string;
  discussions: DiscussionThread[];
  total_tasks: number;
  created_at: string;
  updated_at: string;
}

export interface RoutingAnalysis {
  message: string;
  complexity: string;
  routing: {
    tier: string;
    model: string;
    temperature: number;
    max_tokens: number;
    reasoning: string;
  };
}

export interface ExecutionResult {
  success: boolean;
  output: string;
  error: string;
  exit_code: number;
  execution_time: number;
}

// ── Tool System ──

export interface ToolDefinition {
  name: string;
  description: string;
  category: string;
  parameters: Array<{ name: string; type: string; description: string; required: boolean }>;
}

export interface ToolResult {
  name: string;
  success: boolean;
  output: string;
  error: string;
  duration_ms: number;
}

export interface ToolStats {
  total_executions: number;
  successful: number;
  failed: number;
  success_rate: string;
  recent_log: Array<{ name: string; success: boolean; duration_ms: number }>;
}

// ── Plans ──

export interface PlanStep {
  id: string;
  title: string;
  description: string;
  status: string;
  depends_on: string[];
  result: string;
  started_at: string;
  completed_at: string;
  assigned_agent: string;
  metadata: Record<string, unknown>;
}

export interface ExecutionPlan {
  id: string;
  title: string;
  goal: string;
  status: string;
  steps: PlanStep[];
  created_by: string;
  created_at: string;
  completed_at: string;
  progress: {
    total: number;
    completed: number;
    in_progress: number;
    pending: number;
    failed: number;
    percentage: number;
  };
  metadata: Record<string, unknown>;
}

export interface PlanStats {
  total_plans: number;
  by_status: Record<string, number>;
  average_steps: number;
}

// ── MCP ──

export interface MCPServerState {
  id: string;
  name: string;
  transport: string;
  endpoint: string;
  status: string;
  tool_count: number;
  resource_count: number;
  connected_at: string;
  last_error: string;
}

export interface MCPTool {
  name: string;
  description: string;
  server_id: string;
  input_schema: Record<string, unknown>;
}

// ── Collaboration ──

export interface CollaborationResult {
  thread_id: string;
  query: string;
  participants: string[];
  rounds: number;
  consensus: string;
  discussion: Array<{
    round: number;
    responses: Array<{ agent: string; response: string }>;
  }>;
}

export interface TransferResult {
  success: boolean;
  error?: string;
  from_agent: string;
  from_name: string;
  to_agent: string;
  to_name: string;
  acknowledgment: string;
  context: string;
}

export interface VerificationResult {
  verified: boolean;
  confidence: number;
  issues: string[];
  suggestions: string;
}

// ── Dream Engine ──

export interface DreamStatus {
  agent_id: string;
  is_running: boolean;
  interval_seconds: number;
  total_insights: number;
  latest_insight: string;
}

export interface DreamInsight {
  id: string;
  phase: string;
  content: string;
  source_memories: string[];
  confidence: number;
  created_at: string;
}

export interface DreamCycleResult {
  agent_id: string;
  insights: DreamInsight[];
  memories_processed: number;
  memories_consolidated: number;
  duration_seconds: number;
}

// ── Nudge System ──

export interface NudgeSuggestion {
  id: string;
  agent_id: string;
  type: 'consolidate' | 'cleanup' | 'reorganize' | 'summarize';
  title: string;
  description: string;
  affected_memory_ids: string[];
  priority: number;
  auto_apply: boolean;
  status: 'pending' | 'applied' | 'reverted' | 'dismissed';
  created_at: string;
  applied_at: string | null;
  reverted_at: string | null;
}

export interface NudgeStats {
  agent_id: string;
  total_suggestions: number;
  by_status: Record<string, number>;
  active_snapshots: number;
  last_analysis: string | null;
}

// ── Engine Stats ──

export interface EngineStats {
  agent_id: string;
  agent_name: string;
  routing: { total_requests: number; tier_distribution: Record<string, number>; average_cost: string };
  context: { messages_processed: number; summaries_generated: number; cache_hits: number };
  tools: { total_executions: number; successful: number; failed: number; success_rate: string };
  reasoning: { total_traces: number; successful: number; failed: number; success_rate: string; avg_time_ms: number; style: string };
  memory: { total: number; stats: Record<string, unknown> | null };
  workspace: { total_files: number; total_size: number; languages: string[] };
  dream: { agent_id: string; is_running: boolean; interval_seconds: number; total_insights: number; latest_insight: string };
}

// ── Persona Types ──

export interface Persona {
  id: string;
  name: string;
  tone: string;
  verbosity: string;
  description: string;
  expertise_areas: string[];
  communication_style: string;
  is_active: boolean;
  created_at: string;
}

export interface PersonaPreset {
  key: string;
  name: string;
  description: string;
  tone: string;
}

// ── Learning (Self-Improvement) Types ──

export interface LearningStats {
  agent_id: string;
  total_interactions: number;
  detected_patterns: number;
  generated_candidates: number;
  promoted_skills: number;
  cycle_count: number;
  last_cycle_at: string | null;
}

export interface InteractionPattern {
  pattern_id: string;
  frequency: number;
  success_rate: number;
  typical_actions: string[];
  average_tokens: number;
  last_seen: string;
  promotable: boolean;
}

export interface CandidateSkill {
  candidate_id: string;
  name: string;
  description: string;
  prompt_template: string;
  confidence: number;
  source_patterns: string[];
  created_at: string;
}

export interface LearningCycleResult {
  agent_id: string;
  patterns_detected: number;
  candidates_generated: number;
  skills_promoted: number;
  cycle_duration_ms: number;
}

// ── Gateway Types ──

export interface GatewayStats {
  platforms: Record<string, string>;
  active_sessions: number;
  total_messages: number;
  running: boolean;
}

export interface GatewaySession {
  id: string;
  platform: string;
  platform_user_id: string;
  agent_id: string;
  conversation_id: string | null;
  message_count: number;
  created_at: string;
  last_active: string;
}

// ── Daemon Types ──

export interface DaemonRuntime {
  agent_id: string;
  agent_name: string;
  status: string;
  uptime_seconds: number;
  total_runtime: number;
  tasks_completed: number;
  tasks_failed: number;
  success_rate: number;
  restart_count: number;
  concurrency: { current: number; max: number };
  started_at: string;
  last_active: string;
  auto_restart: boolean;
}

export interface DaemonStats {
  total_agents: number;
  active_agents: number;
  status_distribution: Record<string, number>;
  total_concurrency: number;
  max_total_concurrency: number;
  runtimes: DaemonRuntime[];
}

// ── RAG Types ──

export interface RAGDocument {
  id: string;
  title: string;
  source: string;
  chunk_count: number;
  total_tokens: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface RAGSearchResult {
  chunk_id: string;
  document_id: string;
  content: string;
  similarity: number;
  title: string;
  source: string;
  chunk_index: number;
}

export interface RAGStats {
  agent_id: string;
  document_count: number;
  chunk_count: number;
  embedded_chunks: number;
  total_tokens: number;
  embedding_model: string;
}

// ── Swarm Types ──

export interface SwarmMember {
  agent_id: string;
  agent_name: string;
  role: string;
  status: string;
}

export interface SwarmTask {
  id: string;
  description: string;
  required_roles: string[];
  dependencies: string[];
  priority: number;
  status: string;
}

export interface SwarmSession {
  session_id: string;
  name: string;
  goal: string;
  members: SwarmMember[];
  tasks: SwarmTask[];
  results: Array<{ task_id: string; result: string }>;
  status: string;
  created_at: string;
  completed_at: string;
}

export interface SwarmStats {
  total_sessions: number;
  active_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  average_members: number;
}

// ── Runtime Hub Types ──

export interface RuntimeItem {
  id: string;
  name: string;
  backend: string;
  status: string;
  workspace_dir: string;
  image: string;
  tags: string[];
  metadata: Record<string, string>;
  execution_count: number;
  last_execution_at: string;
  created_at: string;
}

export interface RuntimeHubStats {
  total_runtimes: number;
  runtimes_by_backend: Record<string, number>;
  runtimes_by_status: Record<string, number>;
  total_executions: number;
  monitor_enabled: boolean;
}

export interface ExecutionOutput {
  execution_id: string;
  exit_code: number;
  success: boolean;
  stdout: string;
  stderr: string;
  duration_ms: number;
  error_message: string;
  started_at: string;
  finished_at: string;
}

// ── Scheduler Types ──

export interface ScheduledTaskItem {
  id: string;
  name: string;
  prompt: string;
  agent_id: string;
  description: string;
  cron_expression: string;
  interval_seconds: number;
  schedule_type: string;
  tags: string[];
  status: string;
  run_count: number;
  max_runs: number;
  last_run_at: string;
  next_run_at: string;
  created_at: string;
  updated_at: string;
}

export interface SchedulerStats {
  total_tasks: number;
  active_tasks: number;
  paused_tasks: number;
  completed_tasks: number;
  status_distribution: Record<string, number>;
  engine_running: boolean;
}

export interface ScheduleParseResult {
  text: string;
  schedule_type: string;
  cron_expression: string;
  interval_seconds: number;
}

// ── Studio Types ──

export interface StudioInfoItem {
  id: string;
  name: string;
  description: string;
  icon: string;
  template_id: string;
  tags: string[];
  status: string;
  memory_entry_count: number;
  snapshot_count: number;
  created_at: string;
  updated_at: string;
}

export interface StudioTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
}

export interface StudioMemoryEntry {
  id: string;
  key: string;
  value: string;
  category: string;
  importance: string;
  source: string;
  tags: string[];
  confidence: number;
  version: number;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudioSnapshot {
  snapshot_id: string;
  label: string;
  description: string;
  entry_count: number;
  created_at: string;
}

export interface StudioStats {
  total_studios: number;
  active_studios: number;
  archived_studios: number;
  total_memory_entries: number;
  total_snapshots: number;
}

// ── Workflow Types ──

export interface WorkflowTaskItem {
  id: string;
  title: string;
  description: string;
  state: string;
  priority: string;
  assigned_agent: string;
  created_by: string;
  dependencies: string[];
  tags: string[];
  studio_id: string;
  blockers: Array<{
    type: string;
    description: string;
    is_resolved: boolean;
    resolved_at: string;
    created_at: string;
  }>;
  blocker_count: number;
  active_blockers: number;
  planned_hours: number;
  actual_hours: number;
  created_at: string;
  updated_at: string;
  started_at: string;
  completed_at: string;
  activity_count: number;
}

export interface WorkflowBlocker {
  id: string;
  task_id: string;
  blocker_type: string;
  description: string;
  reported_by: string;
  resolved_by: string;
  resolution: string;
  resolved: boolean;
  created_at: string;
  resolved_at: string;
}

export interface WorkflowStats {
  total_tasks: number;
  tasks_by_state: Record<string, number>;
  tasks_by_priority: Record<string, number>;
  total_blockers: number;
  unresolved_blockers: number;
}

// ── Agent Self Types ──

export interface AgentSelfProfile {
  agent_id: string;
  agent_name: string;
  traits: Record<string, { name: string; value: string; category: string; confidence: number; origin: string }>;
  patterns: Record<string, { pattern_type: string; frequency: number; avg_success_rate: number; description: string }>;
  evolution_step: number;
  interaction_count: number;
  alignment_score: number;
  snapshot_count: number;
}

export interface AgentSelfStats {
  agent_id: string;
  agent_name: string;
  total_traits: number;
  total_patterns: number;
  evolution_step: number;
  interaction_count: number;
  alignment_score: number;
  snapshot_count: number;
}

// ── Plugin System Types ──

export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  status: string;
  permissions: string[];
  capabilities: string[];
  tags: string[];
  homepage: string;
  installed_at: string;
  last_error: string;
}

export interface PluginStats {
  total_plugins: number;
  by_status: Record<string, number>;
  active_hooks: Record<string, number>;
}

// ── IM Hub Types ──

export interface IMPlatformStatus {
  platform: string;
  config_status: string;
  connection_status: string;
  message_count: number;
  online_users: number;
  active_chats: number;
}

export interface IMHubStats {
  connected_platforms: number;
  platforms: Record<string, string>;
  total_messages: number;
  active_chats: number;
}

// ── Skills Marketplace Types ──

export interface MarketplaceSkillInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  author: string;
  author_id: string;
  tags: string[];
  rating: number;
  review_count: number;
  download_count: number;
  pricing: string;
  dependencies: string[];
  verified: boolean;
  published_at: string;
}

export interface MarketplaceStats {
  total_skills: number;
  total_publishers: number;
  total_reviews: number;
  total_downloads: number;
  avg_rating: number;
  by_category: Record<string, number>;
}

export interface SkillReview {
  id: string;
  skill_id: string;
  reviewer_name: string;
  rating: number;
  title: string;
  content: string;
  created_at: string;
}

// ── Task Queue Types ──

export interface QueuedJob {
  id: string;
  job_type: string;
  name: string;
  priority: string;
  status: string;
  agent_id: string;
  progress: number;
  progress_message: string;
  tags: string[];
  created_at: string;
  started_at: string;
  completed_at: string;
  retry_count: number;
  max_retries: number;
  error_message: string;
}

export interface BatchJobInfo {
  id: string;
  name: string;
  status: string;
  progress: number;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  job_ids: string[];
}

export interface TaskQueueStats {
  total_jobs: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  active_workers: number;
  max_concurrent: number;
}

// ── Runtime Backend Types ──

export interface RuntimeBackendInfo {
  kind: string;
  display_name: string;
  capabilities: string[];
  instance_count: number;
  active_count: number;
}

export interface RuntimeInstanceInfo {
  id: string;
  backend: string;
  status: string;
  agent_id: string;
  created_at: string;
  started_at: string;
  error: string;
}

export interface RuntimeBackendStats {
  total_instances: number;
  by_status: Record<string, number>;
  by_backend: Record<string, number>;
}

// ── Agent Core Types ──

export interface AgentCoreStats {
  agent_id: string;
  agent_name: string;
  state: string;
  capabilities: string[];
  executions: { total: number; successful: number; success_rate: number };
  performance: { total_tokens: number; total_tool_calls: number; avg_response_time_ms: number };
  learning: { insights: number; task_patterns: number; tool_patterns: number };
  strategies: Record<string, { successes: number; failures: number; avg_tokens: number; avg_time_ms: number }>;
  checkpoints: number;
  proactive_signals: number;
}

export interface CoreExecutionTrace {
  id: string;
  context: string;
  prompt: string;
  steps: number;
  success: boolean;
  confidence: number;
  total_time_ms: number;
  tools_used: string[];
  insights: string[];
  timestamp: string;
}

export interface CoreInsight {
  id: string;
  category: string;
  content: string;
  confidence: number;
  evidence_count: number;
  timestamp: string;
}

export interface ProactiveSignal {
  id: string;
  type: string;
  description: string;
  priority: number;
  suggested_action: string;
  timestamp: string;
}

export interface CoreAnalysis {
  fingerprint: string;
  strategy: string;
  source: string;
  confidence: number;
  relevant_tools: Array<{ tool: string; score: number; reason: string }>;
}

// ── Agent Synthesis Types ──

export interface SynthesisStats {
  total_contributions: number;
  total_synthesis_reports: number;
  total_conflicts: number;
  resolved_conflicts: number;
  active_agents: number;
  agent_trust_scores: Record<string, number>;
  recent_insights: number;
}

export interface SynthesisReport {
  id: string;
  total_agents: number;
  total_contributions: number;
  insights_count: number;
  conflicts_count: number;
  emergent_patterns: string[];
  recommendations: string[];
  timestamp: string;
}

export interface SynthesisContribution {
  contribution_id: string;
  insight_type: string;
  confidence: number;
}

export interface SynthesisResult {
  report_id: string;
  total_agents: number;
  insights: number;
  conflicts: number;
  emergent_patterns: string[];
}

export interface AgentRecommendation {
  from_agent: string;
  insight_type: string;
  content: string;
  confidence: number;
  source_trust: number;
}

export interface KnowledgeConflict {
  id: string;
  topic: string;
  agent_a: string;
  agent_b: string;
  resolved: boolean;
  resolution: string;
  timestamp: string;
}

// ── Agent Intelligence Types ──

export interface IntelligenceStats {
  total_experiences: number;
  success_rate: number;
  active_traces: number;
  task_patterns: Record<string, number>;
  strategies: Record<string, { successes: number; failures: number }>;
  tools_tracked: number;
}

export interface IntelligenceAnalysis {
  complexity: string;
  recommended_strategy: string;
  relevant_tools: Array<{ name: string; score: number; reason: string }>;
  mode: string;
  estimated_steps: number;
}

export interface LearningInsights {
  total_experiences: number;
  overall_success_rate?: number;
  insights: string[];
  strategy_effectiveness?: Record<string, { success_rate: number; avg_duration: number; attempts: number }>;
  recent_lessons?: string[];
}

export interface Experience {
  pattern: string;
  strategy: string;
  outcome: string;
  lessons: string[];
}

// ── Runtime Types ──

export interface RuntimeInfo {
  agent_id: string;
  agent_name: string;
  state: string;
  executions: number;
  uptime: number;
}

export interface RuntimeStats {
  agent_id: string;
  agent_name: string;
  state: string;
  uptime_seconds: number;
  executions: {
    total: number;
    successful: number;
    failed: number;
    success_rate: number;
  };
  performance: {
    avg_response_time_ms: number;
    avg_tokens_per_execution: number;
    total_tokens_used: number;
    total_tool_calls: number;
    total_tool_errors: number;
  };
  resources: {
    token_budget_remaining: number;
    token_budget_total: number;
    token_budget_percent: number;
    active_executions: number;
    max_parallel_tasks: number;
  };
  checkpoints: number;
  event_listeners: number;
}

export interface RuntimeExecution {
  id: string;
  mode: string;
  prompt: string;
  success: boolean;
  tokens_used: number;
  tool_calls: number;
  elapsed: string;
  error: string;
}

export interface SystemDashboard {
  timestamp: string;
  runtime: {
    active_runtimes: number;
    total_executions: number;
    runtimes: RuntimeInfo[];
  };
  platform: Record<string, any>;
  costs: Record<string, any>;
  synthesis: Record<string, any>;
  guard: Record<string, any>;
  pulse: Record<string, any>;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  components: Record<string, string>;
}

// ── Skill Compiler Types ──

export interface CompiledSkillInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  status: string;
  parameters: string[];
  usage_count: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  avg_tokens: number;
  avg_latency_ms: number;
  validation_score: number;
  tags: string[];
  created_at: string;
}

export interface PipelineInfo {
  id: string;
  name: string;
  description: string;
  skills: string[];
  usage_count: number;
  success_count: number;
  success_rate: number;
  created_at: string;
}

export interface SkillCompilerStats {
  total_skills: number;
  total_pipelines: number;
  total_skills_created: number;
  total_skills_improved: number;
  skills_by_status: Record<string, number>;
  skills_by_category: Record<string, number>;
  total_usage: number;
  total_success: number;
}

// ── Conversation Search Types ──

export interface ConversationInfo {
  conversation_id: string;
  title: string;
  summary: string;
  topics: string[];
  entry_count: number;
  total_tokens: number;
  last_message_at: string;
  tags: string[];
}

export interface SearchResultItem {
  conversation_id: string;
  role: string;
  content: string;
  summary: string;
  topics: string[];
  relevance_score: number;
  timestamp: string;
  conversation_title: string;
}

export interface RecapResult {
  query: string;
  found: boolean;
  result_count?: number;
  summary?: string;
  key_decisions?: string[];
  action_items?: string[];
  relevance?: string;
  sources?: Array<{
    conversation_id: string;
    title: string;
    relevance: number;
    timestamp: string;
  }>;
  message?: string;
}

export interface TimelineEntry {
  conversation_id: string;
  title: string;
  summary: string;
  topics: string[];
  entry_count: number;
  total_tokens: number;
  last_message_at: string;
  first_message_at: string;
  tags: string[];
}

export interface ConversationSearchStats {
  total_entries: number;
  total_conversations: number;
  indexed_entries: number;
  indexed_conversations: number;
  unique_topics: number;
  unique_keywords: number;
  last_indexed_at: string;
}

// ── Pipeline Execution Types ──

export interface PipelineStep {
  step: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface PipelineRun {
  run_id: string;
  agent_id: string;
  status: string;
  steps: PipelineStep[];
  started_at: string;
  completed_at?: string;
}

export interface StrategyEffectiveness {
  strategy: string;
  success_rate: number;
  attempts: number;
  avg_tokens: number;
  avg_time_ms: number;
}

export interface ExecutionTimelineEntry {
  id: string;
  context: string;
  prompt: string;
  steps: number;
  success: boolean;
  confidence: number;
  total_time_ms: number;
  tools_used: string[];
  timestamp: string;
}

// ── Synthesis Types ──

export interface FusionResult {
  fusion_id: string;
  source_agents: string[];
  synthetic_knowledge: string;
  confidence: number;
  supporting_evidence: string[];
  timestamp: string;
}

export interface TrustNetworkNode {
  agent_id: string;
  agent_name: string;
  trust_score: number;
  connections: Array<{ target: string; weight: number }>;
}

export interface TrustNetwork {
  nodes: TrustNetworkNode[];
  edges: Array<{ source: string; target: string; weight: number }>;
  avg_trust: number;
}

export interface CollectiveDecision {
  decision_id: string;
  topic: string;
  options: string[];
  votes: Record<string, Record<string, number>>;
  winner: string;
  confidence: number;
  timestamp: string;
}

export interface ResolvedConflict {
  id: string;
  topic: string;
  agent_a: string;
  agent_b: string;
  resolution: string;
  resolution_strategy: string;
  resolved_at: string;
}

export interface DistilledKnowledge {
  id: string;
  topic: string;
  summary: string;
  source_agents: string[];
  confidence: number;
  created_at: string;
}

// ── Intelligence Types ──

export interface StrategyDispatch {
  strategy: string;
  usage_count: number;
  success_rate: number;
  avg_tokens: number;
  avg_latency_ms: number;
}

export interface ToolEffectiveness {
  tool_name: string;
  total_calls: number;
  success_rate: number;
  avg_duration_ms: number;
  error_rate: number;
}

export interface LessonLearned {
  id: string;
  category: string;
  lesson: string;
  impact: number;
  source: string;
  timestamp: string;
}

export interface UncertaintyGaugeData {
  response_id: string;
  confidence: number;
  factors: Array<{ name: string; impact: number; direction: string }>;
  overall: string;
}

export interface PromptAnalysis {
  original: string;
  complexity: string;
  clarity_score: number;
  suggestions: string[];
  optimized_version: string;
}

// ── Dashboard Types ──

export interface SystemHealthStatus {
  overall: string;
  components: Record<string, { status: string; latency_ms: number; last_checked: string }>;
  uptime_seconds: number;
}

export interface TokenUsageData {
  daily: Array<{ date: string; tokens: number; cost: number }>;
  monthly_total: number;
  monthly_cost: number;
  projected_cost: number;
  by_model: Record<string, { tokens: number; cost: number }>;
}

export interface AgentState {
  agent_id: string;
  agent_name: string;
  state: string;
  current_task: string;
  last_active: string;
  uptime_seconds: number;
}

export interface ActivityFeedEntry {
  id: string;
  type: string;
  agent_id: string;
  agent_name: string;
  description: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

// ── Chat Types ──

export interface MessageBranch {
  branch_id: string;
  parent_message_id: string;
  messages: Array<{ role: string; content: string }>;
  created_at: string;
}

export interface QuickReply {
  id: string;
  text: string;
  category: string;
  confidence: number;
}

// ── Agent Persona (New) Types ──

export interface AgentPersonaProfile {
  persona_id: string;
  name: string;
  description: string;
  traits: Record<string, number>;
  interaction_style: string;
  decision_style: string;
  role: string;
  domain_expertise: string[];
  languages: string[];
  tone_guidelines: string[];
  response_rules: string[];
  forbidden_topics: string[];
  created_at: string;
  updated_at: string;
  interaction_count: number;
  adaptation_history: Array<Record<string, unknown>>;
}

export interface PersonaStats {
  total_personas: number;
  active_persona: string;
  roles: Record<string, number>;
  personas: AgentPersonaProfile[];
}

// ── Agent Governance Types ──

export interface PolicyRule {
  rule_id: string;
  name: string;
  description: string;
  category: string;
  level: string;
  action: string;
  tool_patterns: string[];
  file_patterns: string[];
  domain_patterns: string[];
  max_tokens_per_call: number;
  max_tokens_per_session: number;
  max_cost_per_session: number;
  max_tool_calls_per_session: number;
  require_approval_above_cost: number;
  enabled: boolean;
  priority: number;
  created_at: string;
}

export interface ApprovalRequest {
  request_id: string;
  rule_id: string;
  agent_id: string;
  session_id: string;
  action_description: string;
  context: Record<string, unknown>;
  status: string;
  created_at: string;
  resolved_at: string | null;
  resolution: string | null;
}

export interface BudgetStatus {
  agent_id: string;
  budget_limit: number;
  total_spent: number;
  remaining: number;
  total_tokens: number;
  total_tool_calls: number;
  warnings_issued: number;
  budget_exceeded: boolean;
}

export interface GovernanceStats {
  total_server_policies: number;
  total_agent_policies: number;
  total_session_policies: number;
  pending_approvals: number;
  total_approvals_processed: number;
  active_budgets: number;
  budgets: Record<string, BudgetStatus>;
  recent_audit: Array<Record<string, unknown>>;
}

export interface GovernanceEvaluation {
  action: string;
  reason: string;
  triggered_rules: PolicyRule[];
}

// ── Smart Router Types ──

export interface RouterModelConfig {
  provider: string;
  model_name: string;
  tier: string;
  cost_per_1k_tokens: number;
  max_tokens: number;
  supports_tools: boolean;
  supports_vision: boolean;
  latency_ms: number;
  reliability_score: number;
}

export interface RoutingDecision {
  task_complexity: string;
  selected_model: RouterModelConfig;
  alternative_model: RouterModelConfig | null;
  estimated_cost: number;
  estimated_tokens: number;
  confidence: number;
  reasoning: string;
  timestamp: string;
}

export interface SmartRouterStats {
  total_models: number;
  models_by_tier: Record<string, RouterModelConfig[]>;
  total_decisions: number;
  distribution: Record<string, number>;
  cost_savings: {
    total_savings: number;
    per_model: Record<string, number>;
    total_routing_decisions: number;
  };
  recent_decisions: RoutingDecision[];
}

export interface ComplexityAnalysis {
  complexity: string;
  score: number;
  recommended_tier: string;
}

// ── Identity Core Types ──

export interface IdentityTrait {
  trait_id: string;
  name: string;
  category: string;
  value: number;
  confidence: number;
  source_experiences: string[];
  last_updated: string;
  stability: number;
}

export interface EpisodicEntry {
  entry_id: string;
  content: string;
  context: Record<string, unknown>;
  emotional_valence: number;
  importance: number;
  timestamp: string;
}

export interface SemanticNode {
  node_id: string;
  concept: string;
  relationships: Record<string, number>;
  confidence: number;
  source_episodes: string[];
  timestamp: string;
}

export interface ProceduralPattern {
  pattern_id: string;
  pattern_type: string;
  trigger_conditions: string[];
  action_sequence: string[];
  success_rate: number;
  execution_count: number;
  timestamp: string;
}

export interface IdentityCoreProfile {
  agent_id: string;
  agent_name: string;
  self_awareness: number;
  identity_coherence: number;
  traits: Record<string, IdentityTrait>;
  memory_stats: {
    episodic_entries: number;
    semantic_nodes: number;
    procedural_patterns: number;
    total_experiences: number;
    total_abstractions: number;
  };
  evolution_history: Array<Record<string, unknown>>;
}

export interface IdentityCoreStats {
  agent_id: string;
  agent_name: string;
  self_awareness: number;
  identity_coherence: number;
  total_traits: number;
  episodic_entries: number;
  semantic_nodes: number;
  procedural_patterns: number;
  total_experiences: number;
  total_abstractions: number;
  traits: Record<string, { value: number; confidence: number; stability: number; category: string }>;
}

export interface IdentityRegistryStats {
  total_identities: number;
  identities: Record<string, IdentityCoreStats>;
}

// ── WorkSpace Manager Types ──

export interface WorkSpaceManagerConfig {
  workspace_id: string;
  name: string;
  description: string;
  isolate_files: boolean;
  isolate_memory: boolean;
  isolate_skills: boolean;
  isolate_models: boolean;
  max_file_size_mb: number;
  max_total_size_mb: number;
  max_memory_entries: number;
  max_skills: number;
  auto_cleanup_days: number;
  auto_snapshot_enabled: boolean;
  snapshot_interval_hours: number;
  created_at: string;
  updated_at: string;
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface WorkSpaceManagerSnapshot {
  snapshot_id: string;
  workspace_id: string;
  description: string;
  created_at: string;
  file_count: number;
  memory_entries: number;
  skill_count: number;
  total_size_bytes: number;
  metadata: Record<string, unknown>;
}

export interface WorkSpaceManagerStats {
  total_workspaces: number;
  active_workspace: string;
  total_files: number;
  total_memories: number;
  total_skills: number;
  workspaces: Array<{
    workspace_id: string;
    name: string;
    description: string;
    file_count: number;
    memory_entries: number;
    skill_count: number;
    is_active: boolean;
    created_at: string;
    tags: string[];
  }>;
}

// ── Agent Mesh Types ──

export interface MeshNodeStatus {
  agent_id: string;
  agent_name: string;
  role: string;
  state: string;
  capabilities: string[];
  metrics: {
    total_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    success_rate: number;
    current_load: number;
    max_concurrent: number;
    avg_response_time_ms: number;
    total_cost: number;
    health_score: number;
    uptime_seconds: number;
  };
  active_tasks: number;
  peers: number;
  started_at: string | null;
  tags: string[];
}

export interface MeshStatus {
  total_nodes: number;
  healthy_nodes: number;
  degraded_nodes: number;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  pending_tasks: number;
  overall_success_rate: number;
  delegation_strategy: string;
  nodes: MeshNodeStatus[];
  recent_events: MeshEvent[];
}

export interface MeshEvent {
  event_type: string;
  agent_id: string | null;
  task_id: string | null;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface MeshTask {
  task_id: string;
  title: string;
  priority: string;
  target_agent_id: string | null;
  created_at: string;
}

// ── Learning Loop Types ──

export interface LearningLoopStatus {
  observation: {
    total_observations: number;
    by_type: Record<string, number>;
    unique_agents: number;
    unique_sessions: number;
  };
  extraction: {
    total_patterns: number;
    by_type: Record<string, number>;
    avg_confidence: number;
  };
  compounding: {
    total_skills: number;
    by_source: Record<string, number>;
    avg_confidence: number;
  };
  evolution: {
    total_evolutions: number;
    agents_evolved: number;
  };
  nudge: {
    total_nudges: number;
    active_nudges: number;
    dismissed: number;
    acted_upon: number;
  };
  user_model: {
    interaction_count: number;
    session_count: number;
    feedback_count: number;
    last_active: string;
  };
  running: boolean;
}

export interface LearningNudge {
  nudge_id: string;
  category: string;
  priority: string;
  message: string;
  suggested_action: string;
  created_at: string;
}

export interface LearningPattern {
  pattern_id: string;
  pattern_type: string;
  description: string;
  confidence: number;
  frequency: number;
  related_agents: string[];
}

export interface LearningSkill {
  skill_id: string;
  name: string;
  description: string;
  confidence: number;
  usage_count: number;
  success_rate: number;
  skill_source: string;
  tools_required: string[];
}

// ── Goal Decomposer Types ──
export interface GoalDecomposerStats {
  total_decompositions: number;
  active_trees: number;
  completed_trees: number;
  failed_trees: number;
  by_strategy: Record<string, number>;
}
export interface SubGoalInfo {
  sub_goal_id: string;
  description: string;
  sub_goal_type: string;
  status: string;
  dependencies: string[];
  assigned_agent: string;
  priority: number;
  estimated_effort: string;
  tags: string[];
}
export interface GoalTree {
  goal_id: string;
  description: string;
  strategy: string;
  sub_goals: SubGoalInfo[];
  execution_order: string[][];
  critical_path: string[];
  progress: { total: number; completed: number; in_progress: number; pending: number; failed: number; percentage: number };
  tags: string[];
  created_at: string;
  updated_at: string;
}
export interface DecomposeResult {
  goal_id: string;
  sub_goals: number;
  execution_order: string[][];
  critical_path: string[];
  progress: { total: number; completed: number; in_progress: number; pending: number; failed: number; percentage: number };
}

// ── Self-Reflection Types ──
export interface SelfReflectionStats {
  total_sessions: number;
  active_sessions: number;
  total_actions: number;
  total_insights: number;
  average_confidence: number;
  by_perspective: Record<string, number>;
}
export interface SelfReflectionSession {
  session_id: string;
  agent_id: string;
  status: string;
  action_count: number;
  insight_count: number;
  created_at: string;
}
export interface ActionRecord {
  action_id: string;
  session_id: string;
  action_type: string;
  description: string;
  context: Record<string, unknown>;
  timestamp: string;
}
export interface SelfReflectionInsight {
  insight_id: string;
  session_id: string;
  type: string;
  perspective: string;
  description: string;
  confidence: number;
  priority: string;
  actionable: boolean;
  applied: boolean;
  created_at: string;
}
export interface ReflectionResult {
  session_id: string;
  insights: SelfReflectionInsight[];
  total_insights: number;
  average_confidence: number;
}

// ── Memory Consolidator Types ──
export interface MemoryConsolidatorStats {
  episodic_count: number;
  semantic_count: number;
  procedural_count: number;
  total_consolidations: number;
  memory_usage: number;
  by_strategy: Record<string, number>;
}
export interface MemoryEntryItem {
  entry_id: string;
  content: string;
  memory_type: string;
  importance: number;
  tags: string[];
  source_session: string;
  access_count: number;
  last_accessed: string;
  created_at: string;
}
export interface ConsolidatedMemory {
  consolidated_id: string;
  source_entries: string[];
  summary: string;
  strategy: string;
  quality_score: number;
  entry_count: number;
  created_at: string;
}
export interface ConceptNode {
  concept: string;
  weight: number;
  connections: Array<{ concept: string; strength: number }>;
  entry_count: number;
}

// ── Context Compressor Types ──
export interface ContextCompressorStats {
  total_chunks: number;
  active_chunks: number;
  total_compressions: number;
  total_tokens_saved: number;
  average_compression_ratio: number;
  by_strategy: Record<string, number>;
}
export interface ContextChunk {
  chunk_id: string;
  content: string;
  priority: string;
  source: string;
  token_count: number;
  created_at: string;
}
export interface CompressionResult {
  compression_id: string;
  strategy: string;
  original_tokens: number;
  compressed_tokens: number;
  compression_ratio: number;
  tokens_saved: number;
  summary: string;
  created_at: string;
}
export interface TokenBudget {
  max_tokens: number;
  current_tokens: number;
  remaining: number;
  usage_percent: number;
  auto_compress: boolean;
}