export type TabView = 'chat' | 'tasks' | 'skills' | 'memory' | 'autopilot' | 'subagents' | 'tools' | 'plans' | 'workspace' | 'dream' | 'mcp' | 'collaboration' | 'approval' | 'events' | 'overview' | 'dashboard' | 'nexus' | 'forge' | 'identity' | 'trajectory' | 'squads' | 'guard' | 'pulse';

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