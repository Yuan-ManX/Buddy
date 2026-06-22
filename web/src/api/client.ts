const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<import('../types').HealthResponse>('/health'),

  agents: {
    list: (page = 1, pageSize = 50) =>
      request<import('../types').PaginatedResponse<import('../types').Agent>>(
        `/agents?page=${page}&page_size=${pageSize}`
      ),
    get: (id: string) => request<import('../types').Agent>(`/agents/${id}`),
    create: (data: { name: string; role: string; personality: string; instructions: string }) =>
      request<import('../types').Agent>('/agents', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/agents/${id}`, { method: 'DELETE' }),
    update: (id: string, data: { name?: string; role?: string; personality?: string; instructions?: string }) =>
      request<import('../types').Agent>(`/agents/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },

  conversations: {
    list: (page = 1, pageSize = 50) =>
      request<import('../types').PaginatedResponse<import('../types').Conversation>>(
        `/conversations?page=${page}&page_size=${pageSize}`
      ),
    get: (id: string) => request<import('../types').Conversation>(`/conversations/${id}`),
    create: (data: { title: string; agent_ids: string[] }) =>
      request<import('../types').Conversation>('/conversations', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (convId: string, data: { title?: string; agent_ids?: string[] }) =>
      request<import('../types').Conversation>(`/conversations/${convId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (convId: string) =>
      request<void>(`/conversations/${convId}`, { method: 'DELETE' }),
    messages: (convId: string, page = 1, pageSize = 100) =>
      request<import('../types').PaginatedResponse<import('../types').Message>>(
        `/conversations/${convId}/messages?page=${page}&page_size=${pageSize}`
      ),
  },

  chat: (data: { agent_id: string; content: string; conversation_id?: string }) =>
    request<import('../types').ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  tasks: {
    list: (params?: { agent_id?: string; status?: string; kind?: string; page?: number; page_size?: number }) => {
      const qs = new URLSearchParams();
      if (params?.agent_id) qs.set('agent_id', params.agent_id);
      if (params?.status) qs.set('status', params.status);
      if (params?.kind) qs.set('kind', params.kind);
      if (params?.page) qs.set('page', String(params.page));
      if (params?.page_size) qs.set('page_size', String(params.page_size));
      return request<import('../types').PaginatedResponse<import('../types').Task>>(
        `/tasks?${qs.toString()}`
      );
    },
    get: (id: string) => request<import('../types').Task>(`/tasks/${id}`),
    create: (data: { agent_id: string; title: string; kind?: string; payload?: Record<string, unknown>; max_attempts?: number }) =>
      request<import('../types').Task>('/tasks', { method: 'POST', body: JSON.stringify(data) }),
    transition: (taskId: string, status: string, result?: Record<string, unknown>, error?: string) =>
      request<import('../types').Task>(`/tasks/${taskId}/transition`, {
        method: 'POST',
        body: JSON.stringify({ status, result, error }),
      }),
    cancel: (taskId: string) =>
      request<{ id: string; status: string }>(`/tasks/${taskId}/cancel`, { method: 'POST' }),
    retry: (taskId: string) =>
      request<{ id: string; status: string; attempt: number }>(`/tasks/${taskId}/retry`, { method: 'POST' }),
    claim: (agentId: string) =>
      request<import('../types').Task>(`/agents/${agentId}/claim`, { method: 'POST' }),
  },

  skills: {
    list: (category?: string) =>
      request<import('../types').Skill[]>(`/skills${category ? `?category=${category}` : ''}`),
    categories: () => request<string[]>('/skills/categories'),
    execute: (skillName: string, agentId: string, parameters: Record<string, unknown>) =>
      request<{ result: string }>('/skills/execute', {
        method: 'POST',
        body: JSON.stringify({ skill_name: skillName, agent_id: agentId, parameters }),
      }),
    pipeline: (steps: Array<{ name: string; params: Record<string, unknown> }>, agentId: string) =>
      request<{ result: string }>('/skills/pipeline', {
        method: 'POST',
        body: JSON.stringify({ steps, agent_id: agentId }),
      }),
  },

  memories: {
    list: (agentId: string, query?: string, limit?: number) => {
      const qs = new URLSearchParams();
      if (query) qs.set('query', query);
      if (limit) qs.set('limit', String(limit));
      return request<Array<import('../types').MemoryEntry>>(
        `/agents/${agentId}/memories?${qs.toString()}`
      );
    },
    stats: (agentId: string) =>
      request<import('../types').MemoryStats>(`/agents/${agentId}/memories/stats`),
    tags: (agentId: string) =>
      request<Array<{ tag: string; count: number }>>(`/agents/${agentId}/memories/tags`),
    search: (agentId: string, query: string, limit?: number) => {
      const qs = new URLSearchParams();
      qs.set('q', query);
      if (limit) qs.set('limit', String(limit));
      return request<Array<import('../types').MemoryEntry>>(
        `/agents/${agentId}/memories/search?${qs.toString()}`
      );
    },
    tag: (agentId: string, memoryId: string, tags: string[]) =>
      request<{ success: boolean }>(`/agents/${agentId}/memories/${memoryId}/tag`, {
        method: 'POST',
        body: JSON.stringify({ tags }),
      }),
    untag: (agentId: string, memoryId: string, tags: string[]) =>
      request<{ success: boolean }>(`/agents/${agentId}/memories/${memoryId}/tag`, {
        method: 'DELETE',
        body: JSON.stringify({ tags }),
      }),
    update: (agentId: string, memoryId: string, data: { content?: string; importance?: number }) =>
      request<{ success: boolean }>(`/agents/${agentId}/memories/${memoryId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (agentId: string, memoryId: string) =>
      request<void>(`/agents/${agentId}/memories/${memoryId}`, { method: 'DELETE' }),
    export: (agentId: string) =>
      request<Array<import('../types').MemoryEntry>>(`/agents/${agentId}/memories/export`, { method: 'POST' }),
    decay: (agentId: string, days?: number, rate?: number) => {
      const qs = new URLSearchParams();
      if (days) qs.set('days', String(days));
      if (rate) qs.set('rate', String(rate));
      return request<{ decayed: number }>(`/agents/${agentId}/memories/decay?${qs.toString()}`, { method: 'POST' });
    },
  },

  routing: {
    stats: () => request<import('../types').SystemOverview['routing']>('/routing/stats'),
    analyze: (message: string) => {
      const qs = new URLSearchParams();
      qs.set('message', message);
      return request<import('../types').RoutingAnalysis>(`/routing/analyze?${qs.toString()}`, { method: 'POST' });
    },
    analyzeDeep: (message: string, contextSummary?: string) => {
      const qs = new URLSearchParams();
      qs.set('message', message);
      if (contextSummary) qs.set('context_summary', contextSummary);
      return request<import('../types').RoutingAnalysis>(`/routing/analyze-deep?${qs.toString()}`, { method: 'POST' });
    },
    tiers: () => request<Record<string, { model: string; temperature: number; max_tokens: number; cost_multiplier: number; usage_count: number }>>('/routing/tiers'),
    updateTier: (tierName: string, data: { model?: string; temperature?: number; max_tokens?: number; cost_multiplier?: number }) =>
      request(`/routing/tiers/${tierName}`, { method: 'PUT', body: JSON.stringify(data) }),
  },

  autopilots: {
    list: (agentId?: string) => {
      const qs = agentId ? `?agent_id=${agentId}` : '';
      return request<Array<import('../types').AutopilotConfig>>(`/autopilots${qs}`);
    },
    get: (id: string) => request<import('../types').AutopilotConfig>(`/autopilots/${id}`),
    create: (data: { agent_id: string; name: string; task_template: string; trigger?: string; schedule?: string; max_runs?: number; description?: string }) =>
      request<import('../types').AutopilotConfig>('/autopilots', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    pause: (id: string) =>
      request<{ success: boolean }>(`/autopilots/${id}/pause`, { method: 'POST' }),
    resume: (id: string) =>
      request<{ success: boolean }>(`/autopilots/${id}/resume`, { method: 'POST' }),
    delete: (id: string) =>
      request<void>(`/autopilots/${id}`, { method: 'DELETE' }),
  },

  workspace: {
    stats: (agentId: string) =>
      request<{ agent_id: string; file_count: number; total_size: number; languages: string[] }>(
        `/agents/${agentId}/workspace`
      ),
    files: (agentId: string, subdir?: string) => {
      const qs = subdir ? `?subdir=${subdir}` : '';
      return request<Array<import('../types').WorkspaceFile>>(`/agents/${agentId}/workspace/files${qs}`);
    },
    getFile: (agentId: string, path: string) =>
      request<import('../types').WorkspaceFile>(`/agents/${agentId}/workspace/files/${encodeURIComponent(path)}`),
    createFile: (agentId: string, data: { name: string; content?: string; subdir?: string }) =>
      request<import('../types').WorkspaceFile>(`/agents/${agentId}/workspace/files`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateFile: (agentId: string, path: string, content: string) =>
      request<import('../types').WorkspaceFile>(`/agents/${agentId}/workspace/files/${encodeURIComponent(path)}`, {
        method: 'PUT',
        body: JSON.stringify({ content }),
      }),
    deleteFile: (agentId: string, path: string) =>
      request<void>(`/agents/${agentId}/workspace/files/${encodeURIComponent(path)}`, { method: 'DELETE' }),
    executePython: (agentId: string, code: string, timeout?: number) =>
      request<import('../types').ExecutionResult>(`/agents/${agentId}/workspace/execute/python`, {
        method: 'POST',
        body: JSON.stringify({ code, timeout }),
      }),
    executeShell: (agentId: string, command: string, timeout?: number) =>
      request<import('../types').ExecutionResult>(`/agents/${agentId}/workspace/execute/shell`, {
        method: 'POST',
        body: JSON.stringify({ command, timeout }),
      }),
  },

  workspaces: {
    list: () =>
      request<Array<import('../types').Workspace>>('/workspaces'),
    get: (id: string) =>
      request<import('../types').Workspace>(`/workspaces/${id}`),
    create: (data: { name: string; description: string }) =>
      request<import('../types').Workspace>('/workspaces', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/workspaces/${id}`, { method: 'DELETE' }),
    switch: (id: string) =>
      request<import('../types').Workspace>(`/workspaces/${id}/activate`, { method: 'POST' }),
    stats: () =>
      request<import('../types').WorkspaceStatsOverview>('/workspaces/stats'),
    export: (id: string) =>
      request<{ config: Record<string, unknown>; workspace: import('../types').Workspace }>(`/workspaces/${id}/export`),
  },

  subagents: {
    execute: (agentId: string, tasks: Array<{ name: string; instructions: string; task: string }>, model?: string) =>
      request<Array<import('../types').SubAgentResult>>(`/agents/${agentId}/subagents/execute`, {
        method: 'POST',
        body: JSON.stringify({ agent_id: agentId, tasks, model: model || 'gpt-4o-mini' }),
      }),
    aggregate: (agentId: string, tasks: Array<{ name: string; instructions: string; task: string }>, model?: string) =>
      request<{ aggregated: string; results: Array<{ agent_id: string; status: string; tokens_used: number }> }>(
        `/agents/${agentId}/subagents/aggregate`,
        {
          method: 'POST',
          body: JSON.stringify({ agent_id: agentId, tasks, model: model || 'gpt-4o-mini' }),
        }
      ),
  },

  tools: {
    list: (category?: string) => {
      const qs = category ? `?category=${category}` : '';
      return request<Array<import('../types').ToolDefinition>>(`/tools${qs}`);
    },
    categories: () => request<string[]>('/tools/categories'),
    execute: (name: string, arguments_: Record<string, unknown>) =>
      request<import('../types').ToolResult>('/tools/execute', {
        method: 'POST',
        body: JSON.stringify({ name, arguments: arguments_ }),
      }),
    executeBatch: (calls: Array<{ name: string; arguments: Record<string, unknown> }>) =>
      request<Array<import('../types').ToolResult>>('/tools/execute/batch', {
        method: 'POST',
        body: JSON.stringify(calls),
      }),
    stats: () => request<import('../types').ToolStats>('/tools/stats'),
  },

  plans: {
    list: (agentId?: string) => {
      const qs = agentId ? `?agent_id=${agentId}` : '';
      return request<Array<import('../types').ExecutionPlan>>(`/plans${qs}`);
    },
    get: (planId: string) => request<import('../types').ExecutionPlan>(`/plans/${planId}`),
    generate: (agentId: string, goal: string) =>
      request<import('../types').ExecutionPlan>('/plans/generate', {
        method: 'POST',
        body: JSON.stringify({ agent_id: agentId, goal }),
      }),
    execute: (planId: string, agentId: string) =>
      request<import('../types').ExecutionPlan>(`/plans/${planId}/execute`, {
        method: 'POST',
        body: JSON.stringify({ plan_id: planId, agent_id: agentId }),
      }),
    cancel: (planId: string) =>
      request<{ success: boolean }>(`/plans/${planId}/cancel`, { method: 'POST' }),
    delete: (planId: string) =>
      request<void>(`/plans/${planId}`, { method: 'DELETE' }),
    stats: () => request<import('../types').PlanStats>('/plans/stats/overview'),
  },

  mcp: {
    servers: () => request<Array<import('../types').MCPServerState>>('/mcp/servers'),
    tools: (serverId?: string) => {
      const qs = serverId ? `?server_id=${serverId}` : '';
      return request<Array<import('../types').MCPTool>>(`/mcp/tools${qs}`);
    },
    register: (data: { name: string; transport?: string; endpoint?: string; command?: string; env?: Record<string, string> }) =>
      request<import('../types').MCPServerState>('/mcp/servers', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    connect: (serverId: string) =>
      request<{ success: boolean; server_id: string }>(`/mcp/servers/${serverId}/connect`, { method: 'POST' }),
    disconnect: (serverId: string) =>
      request<{ success: boolean }>(`/mcp/servers/${serverId}/disconnect`, { method: 'POST' }),
    unregister: (serverId: string) =>
      request<void>(`/mcp/servers/${serverId}`, { method: 'DELETE' }),
    callTool: (toolName: string, arguments_: Record<string, unknown>) =>
      request<Record<string, unknown>>(`/mcp/tools/${toolName}/call`, {
        method: 'POST',
        body: JSON.stringify(arguments_),
      }),
    stats: () => request<any>('/mcp/stats'),
    listTools: (category?: string) => {
      const qs = category ? `?category=${category}` : '';
      return request<any>(`/mcp/tools${qs}`);
    },
    addServer: (data: { name: string; server_type: string; command?: string }) =>
      request<any>('/mcp/servers', { method: 'POST', body: JSON.stringify(data) }),
    addTool: (data: { name: string; description: string; category: string }) =>
      request<any>('/mcp/tools', { method: 'POST', body: JSON.stringify(data) }),
    executeTool: (name: string, args: Record<string, any>) =>
      request<any>(`/mcp/tools/${name}/execute`, { method: 'POST', body: JSON.stringify(args) }),
    connectServer: (name: string) =>
      request<any>(`/mcp/servers/${name}/connect`, { method: 'POST' }),
  },

  collaborate: {
    execute: (data: { query: string; agent_ids: string[]; max_rounds?: number }) =>
      request<import('../types').CollaborationResult>('/collaborate', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    transfer: (data: { from_agent_id: string; to_agent_id: string; context: string }) =>
      request<import('../types').TransferResult>('/transfer', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    verify: (data: { verification_agent_id: string; original_response: string; original_query: string }) =>
      request<import('../types').VerificationResult>('/verify', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    trust: (agentId: string) =>
      request<{ agent_id: string; trusted_agents: string[]; count: number }>(`/agents/${agentId}/trust`),
  },

  chatStream: (data: { agent_id: string; content: string; conversation_id?: string; enable_tools?: boolean; enable_reasoning?: boolean }) => {
    // SSE streaming via fetch
    return fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },

  chatPlan: (data: { agent_id: string; content: string; conversation_id?: string }) =>
    request<import('../types').ChatResponse>('/chat/plan', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  chatBrain: (data: { agent_id: string; content: string; conversation_id?: string; enable_tools?: boolean; enable_reasoning?: boolean; mode?: string }) =>
    request<import('../types').ChatResponse & { mode: string }>('/chat/brain', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  chatBrainStream: (data: { agent_id: string; content: string; conversation_id?: string; enable_tools?: boolean; enable_reasoning?: boolean; mode?: string }) =>
    fetch(`${BASE_URL}/chat/brain/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  chatBranches: (messageId: string) =>
    request<{ branches: Array<import('../types').MessageBranch> }>(`/chat/branches?message_id=${messageId}`),
  chatQuickReplies: (agentId: string) =>
    request<{ replies: Array<import('../types').QuickReply> }>(`/chat/quick-replies?agent_id=${agentId}`),

  system: {
    overview: () => request<import('../types').SystemOverview>('/system/overview'),
    health: () => request<import('../types').SystemHealthStatus>('/system/health'),
    tokenUsage: () => request<import('../types').TokenUsageData>('/system/token-usage'),
    activeAgents: () => request<{ agents: Array<import('../types').AgentState> }>('/system/active-agents'),
    recentActivity: (limit = 20) =>
      request<{ activities: Array<import('../types').ActivityFeedEntry> }>(`/system/recent-activity?limit=${limit}`),
  },

  dream: {
    status: (agentId: string) => request<import('../types').DreamStatus>(`/agents/${agentId}/dream/status`),
    insights: (agentId: string, limit: number = 20) =>
      request<Array<import('../types').DreamInsight>>(`/agents/${agentId}/dream/insights?limit=${limit}`),
    start: (agentId: string, interval: number = 3600) =>
      request<{ success: boolean; agent_id: string; interval: number }>(`/agents/${agentId}/dream/start?interval=${interval}`, { method: 'POST' }),
    stop: (agentId: string) =>
      request<{ success: boolean; agent_id: string }>(`/agents/${agentId}/dream/stop`, { method: 'POST' }),
    run: (agentId: string) =>
      request<import('../types').DreamCycleResult>(`/agents/${agentId}/dream/run`, { method: 'POST' }),
  },

  engine: {
    stats: (agentId: string) => request<import('../types').EngineStats>(`/agents/${agentId}/engine-stats`),
  },

  approval: {
    rules: () => request<Array<{ tool_name: string; level: string; risk: string; description: string }>>('/approval/rules'),
    check: (toolName: string, arguments_: Record<string, unknown>) =>
      request<{ approved: boolean; tool_name: string }>('/approval/check', {
        method: 'POST',
        body: JSON.stringify({ name: toolName, arguments: arguments_ }),
      }),
    clearSession: () =>
      request<{ success: boolean }>('/approval/session/clear', { method: 'POST' }),
  },

  events: {
    stats: () => request<{ total_events: number; listener_count: number; type_counts: Record<string, number> }>('/events/stats'),
    history: (eventType?: string, limit: number = 50) => {
      const qs = new URLSearchParams();
      if (eventType) qs.set('event_type', eventType);
      qs.set('limit', String(limit));
      return request<Array<{ id: string; type: string; source: string; data: Record<string, unknown>; timestamp: string }>>(`/events/history?${qs.toString()}`);
    },
  },

  semantic: {
    search: (agentId: string, query: string, limit: number = 10, minImportance: number = 0.0) => {
      const qs = new URLSearchParams();
      qs.set('q', query);
      qs.set('limit', String(limit));
      qs.set('min_importance', String(minImportance));
      return request<Array<import('../types').MemoryEntry & { similarity: number }>>(`/agents/${agentId}/memories/semantic?${qs.toString()}`);
    },
    consolidate: (agentId: string) =>
      request<{ consolidated: number; themes: string[]; total_processed: number }>(`/agents/${agentId}/memories/consolidate`, { method: 'POST' }),
  },

  ws: {
    connect: (): WebSocket => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      return new WebSocket(`${protocol}//${host}/api/ws`);
    },
  },

  nudge: {
    analyze: (agentId: string) =>
      request<Array<import('../types').NudgeSuggestion>>(`/agents/${agentId}/nudge/analyze`, { method: 'POST' }),
    suggestions: (agentId: string, status?: string) => {
      const qs = status ? `?status=${status}` : '';
      return request<Array<import('../types').NudgeSuggestion>>(`/agents/${agentId}/nudge/suggestions${qs}`);
    },
    stats: (agentId: string) =>
      request<import('../types').NudgeStats>(`/agents/${agentId}/nudge/stats`),
    apply: (agentId: string, nudgeId: string) =>
      request<{ success: boolean; nudge_id: string; type: string; actions: Array<Record<string, unknown>> }>(
        `/agents/${agentId}/nudge/${nudgeId}/apply`,
        { method: 'POST' }
      ),
    revert: (agentId: string, nudgeId: string) =>
      request<{ success: boolean; nudge_id: string; action: string; restored_memory_ids: string[] }>(
        `/agents/${agentId}/nudge/${nudgeId}/revert`,
        { method: 'POST' }
      ),
    dismiss: (agentId: string, nudgeId: string) =>
      request<{ success: boolean }>(`/agents/${agentId}/nudge/${nudgeId}/dismiss`, { method: 'POST' }),
  },

  // ── Nexus ──
  nexus: {
    summary: () => request<import('../types').NexusSummary>('/nexus/summary'),
    runtimes: (platform?: string, status?: string) => {
      const params = new URLSearchParams();
      if (platform) params.set('platform', platform);
      if (status) params.set('status', status);
      return request<Array<import('../types').RuntimeInfo>>(`/nexus/runtimes?${params}`);
    },
    runtime: (id: string) => request<import('../types').RuntimeInfo>(`/nexus/runtimes/${id}`),
    heartbeat: (id: string) => request<{ status: string }>(`/nexus/runtimes/${id}/heartbeat`, { method: 'POST' }),
  },

  // ── Forge ──
  forge: {
    skills: (category?: string, status?: string) => {
      const params = new URLSearchParams();
      if (category) params.set('category', category);
      if (status) params.set('status', status);
      return request<Array<import('../types').ForgedSkill>>(`/forge/skills?${params}`);
    },
    skill: (id: string) => request<import('../types').ForgedSkill>(`/forge/skills/${id}`),
    create: (data: { name: string; description: string; category: string; prompt_template: string; parameters?: Array<Record<string, unknown>>; author_agent_id?: string; tags?: string[] }) =>
      request<import('../types').ForgedSkill>('/forge/skills', { method: 'POST', body: JSON.stringify(data) }),
    evolve: (skillId: string, newPromptTemplate: string, reason?: string) => {
      const params = new URLSearchParams({ new_prompt_template: newPromptTemplate });
      if (reason) params.set('reason', reason);
      return request(`/forge/skills/${skillId}/evolve?${params}`, { method: 'POST' });
    },
    deprecate: (skillId: string) => request<{ success: boolean }>(`/forge/skills/${skillId}/deprecate`, { method: 'POST' }),
    archive: (skillId: string) => request<{ success: boolean }>(`/forge/skills/${skillId}/archive`, { method: 'POST' }),
    patterns: () => request<{ patterns: Array<import('../types').InteractionPattern>; promotable: Array<import('../types').InteractionPattern> }>('/forge/patterns'),
    promote: (patternId: string, name: string, description: string, promptTemplate: string) => {
      const params = new URLSearchParams({ name, description, prompt_template: promptTemplate });
      return request<import('../types').ForgedSkill>(`/forge/patterns/${patternId}/promote?${params}`, { method: 'POST' });
    },
    stats: () => request<import('../types').ForgeStats>('/forge/stats'),
    observe: (userMessage: string, actions: string, agentId?: string) => {
      const params = new URLSearchParams({ user_message: userMessage, actions });
      if (agentId) params.set('agent_id', agentId);
      return request<{ observed: boolean }>(`/forge/observe?${params}`, { method: 'POST' });
    },
    recordExecution: (skillId: string, version: number, success: boolean, tokens?: number, latencyMs?: number) => {
      const params = new URLSearchParams({ version: String(version), success: String(success) });
      if (tokens) params.set('tokens', String(tokens));
      if (latencyMs) params.set('latency_ms', String(latencyMs));
      return request<{ recorded: boolean }>(`/forge/skills/${skillId}/record?${params}`, { method: 'POST' });
    },
  },

  // ── Identity ──
  identity: {
    profile: (agentId: string, userId?: string) => {
      const params = userId ? `?user_id=${userId}` : '';
      return request<import('../types').IdentityProfile>(`/identity/profiles/${agentId}${params}`);
    },
    summary: (agentId: string, userId?: string) => {
      const params = userId ? `?user_id=${userId}` : '';
      return request(`/identity/profiles/${agentId}/summary${params}`);
    },
    setAttribute: (agentId: string, key: string, value: string, category?: string, confidence?: number) => {
      const params = new URLSearchParams({ key, value, category: category || 'preference', confidence: String(confidence || 0.7) });
      return request<{ success: boolean }>(`/identity/profiles/${agentId}/attributes?${params}`, { method: 'POST' });
    },
    getAttribute: (agentId: string, key: string) =>
      request(`/identity/profiles/${agentId}/attributes/${key}`),
    deleteAttribute: (agentId: string, key: string) =>
      request<{ success: boolean }>(`/identity/profiles/${agentId}/attributes/${key}`, { method: 'DELETE' }),
    lockAttribute: (agentId: string, key: string) =>
      request<{ success: boolean }>(`/identity/profiles/${agentId}/attributes/${key}/lock`, { method: 'POST' }),
    unlockAttribute: (agentId: string, key: string) =>
      request<{ success: boolean }>(`/identity/profiles/${agentId}/attributes/${key}/unlock`, { method: 'POST' }),
    addPersona: (agentId: string, data: { name: string; persona_type: string; description: string; tone: string; verbosity: string; expertise_areas: string[] }) =>
      request(`/identity/profiles/${agentId}/personas`, { method: 'POST', body: JSON.stringify(data) }),
    activatePersona: (agentId: string, personaName: string) =>
      request<{ success: boolean; active_persona: string }>(`/identity/profiles/${agentId}/personas/${personaName}/activate`, { method: 'POST' }),
    learn: (agentId: string, userMessage: string, insights: string) => {
      const params = new URLSearchParams({ user_message: userMessage, insights });
      return request<{ success: boolean }>(`/identity/profiles/${agentId}/learn?${params}`, { method: 'POST' });
    },
  },

  // ── Trajectory ──
  trajectory: {
    start: (agentId: string, taskId?: string) => {
      const params = new URLSearchParams({ agent_id: agentId });
      if (taskId) params.set('task_id', taskId);
      return request<import('../types').ExecutionTrace>(`/trajectory/start?${params}`, { method: 'POST' });
    },
    step: (traceId: string, action: string, content: string, tokens?: number, toolName?: string) => {
      const params = new URLSearchParams({ action, content, tokens: String(tokens || 0), tool_name: toolName || '' });
      return request<{ recorded: boolean }>(`/trajectory/${traceId}/step?${params}`, { method: 'POST' });
    },
    complete: (traceId: string, success: boolean, qualityScore?: number) => {
      const params = new URLSearchParams({ success: String(success), quality_score: String(qualityScore || 1.0) });
      return request<import('../types').CompressedTrajectory>(`/trajectory/${traceId}/complete?${params}`, { method: 'POST' });
    },
    cancel: (traceId: string) =>
      request<{ cancelled: boolean }>(`/trajectory/${traceId}/cancel`, { method: 'POST' }),
    get: (traceId: string) => request<import('../types').ExecutionTrace>(`/trajectory/${traceId}`),
    recent: (limit?: number) => request<Array<import('../types').CompressedTrajectory>>(`/trajectory/recent?limit=${limit || 20}`),
    successful: (limit?: number) => request<Array<import('../types').CompressedTrajectory>>(`/trajectory/successful?limit=${limit || 50}`),
    failed: (limit?: number) => request<Array<import('../types').CompressedTrajectory>>(`/trajectory/failed?limit=${limit || 20}`),
    byAgent: (agentId: string, limit?: number) => request<Array<import('../types').CompressedTrajectory>>(`/trajectory/by-agent/${agentId}?limit=${limit || 50}`),
    stats: () => request('/trajectory/stats'),
    clear: (agentId: string) =>
      request<{ agent_id: string; cleared: boolean }>(`/agents/${agentId}/trajectory/clear`, { method: 'POST' }),
  },

  // ── Guard ──
  guard: {
    stats: () => request('/guard/stats'),
    alerts: (agentId?: string, minSeverity?: string) => {
      const params = new URLSearchParams();
      if (agentId) params.set('agent_id', agentId);
      if (minSeverity) params.set('min_severity', minSeverity);
      return request<Array<any>>(`/guard/alerts?${params}`);
    },
    checkContent: (agentId: string, content: string) => {
      const params = new URLSearchParams({ agent_id: agentId, content });
      return request<any>(`/guard/check/content?${params}`, { method: 'POST' });
    },
    checkRateLimit: (agentId: string, windowSeconds?: number, maxRequests?: number) => {
      const params = new URLSearchParams({ agent_id: agentId });
      if (windowSeconds) params.set('window_seconds', String(windowSeconds));
      if (maxRequests) params.set('max_requests', String(maxRequests));
      return request<any>(`/guard/check/rate-limit?${params}`, { method: 'POST' });
    },
    checkQuota: (agentId: string, tokensUsed: number, maxTokens?: number) => {
      const params = new URLSearchParams({ agent_id: agentId, tokens_used: String(tokensUsed) });
      if (maxTokens) params.set('max_tokens', String(maxTokens));
      return request<any>(`/guard/check/quota?${params}`, { method: 'POST' });
    },
    audit: (agentId: string, actionName: string, details?: string) => {
      const params = new URLSearchParams({ agent_id: agentId, action_name: actionName, details: details || '{}' });
      return request<{ audited: boolean }>(`/guard/audit?${params}`, { method: 'POST' });
    },
    clearAlerts: (agentId?: string) => {
      const params = agentId ? `?agent_id=${agentId}` : '';
      return request<{ cleared: number }>(`/guard/alerts/clear${params}`, { method: 'POST' });
    },
  },

  // ── Pulse ──
  pulse: {
    health: () => request<any>('/pulse/health'),
    component: (componentId: string) => request<any>(`/pulse/components/${componentId}`),
    heartbeat: (componentId: string) =>
      request<{ status: string }>(`/pulse/components/${componentId}/heartbeat`, { method: 'POST' }),
    latency: (componentId: string) => request<any>(`/pulse/components/${componentId}/latency`),
    errors: (componentId: string) => request<any>(`/pulse/components/${componentId}/errors`),
    recordMetric: (componentId: string, name: string, value: number, unit?: string) => {
      const params = new URLSearchParams({ component_id: componentId, name, value: String(value), unit: unit || 'count' });
      return request<{ recorded: boolean }>(`/pulse/record?${params}`, { method: 'POST' });
    },
    anomalies: () => request<{ alerts: any[]; count: number }>('/pulse/anomalies'),
  },

  // ── Persona Management ──
  personas: {
    list: (agentId: string) =>
      request<Array<import('../types').Persona>>(`/agents/${agentId}/personas`),
    getActive: (agentId: string) =>
      request<import('../types').Persona>(`/agents/${agentId}/personas/active`),
    presets: () =>
      request<Array<import('../types').PersonaPreset>>('/agents/_/personas/presets'),
    activate: (agentId: string, personaId: string) =>
      request<{ success: boolean; active_persona_id: string }>(`/agents/${agentId}/personas/activate/${personaId}`, { method: 'POST' }),
    createFromPreset: (agentId: string, presetName: string) => {
      const params = new URLSearchParams({ preset_name: presetName });
      return request<import('../types').Persona>(`/agents/${agentId}/personas/create-from-preset?${params}`, { method: 'POST' });
    },
    create: (agentId: string, data: { name: string; tone?: string; verbosity?: string; description?: string; expertise_areas?: string[]; communication_style?: string }) =>
      request<import('../types').Persona>(`/agents/${agentId}/personas`, { method: 'POST', body: JSON.stringify(data) }),
    delete: (agentId: string, personaId: string) =>
      request<void>(`/agents/${agentId}/personas/${personaId}`, { method: 'DELETE' }),
  },

  // ── Learning (Self-Improvement) ──
  learning: {
    stats: (agentId: string) =>
      request<import('../types').LearningStats>(`/agents/${agentId}/learning/stats`),
    patterns: (agentId: string) =>
      request<Array<import('../types').InteractionPattern>>(`/agents/${agentId}/learning/patterns`),
    candidates: (agentId: string) =>
      request<Array<import('../types').CandidateSkill>>(`/agents/${agentId}/learning/candidates`),
    history: (limit?: number) =>
      request<Array<import('../types').LearningCycleResult>>(`/learning/history?limit=${limit || 20}`),
    recordInteraction: (agentId: string, userMessage: string, assistantResponse: string, toolsUsed?: string, success?: boolean) => {
      const params = new URLSearchParams({ user_message: userMessage, assistant_response: assistantResponse, tools_used: toolsUsed || '', success: String(success !== false) });
      return request<{ recorded: boolean }>(`/agents/${agentId}/learning/record?${params}`, { method: 'POST' });
    },
    runCycle: (agentId: string) =>
      request<import('../types').LearningCycleResult>(`/agents/${agentId}/learning/run-cycle`, { method: 'POST' }),
    runAll: () =>
      request<{ results: Array<import('../types').LearningCycleResult>; agents_processed: number }>('/learning/run-all', { method: 'POST' }),
  },

  // ── Gateway ──
  gateway: {
    stats: () =>
      request<any>('/gateway/platform-stats'),
    sessions: () =>
      request<Array<import('../types').GatewaySession>>('/gateway/sessions'),
    connectPlatform: (platform: string, config?: string) => {
      const params = new URLSearchParams({ platform, config: config || '{}' });
      return request<{ success: boolean; platform: string }>(`/gateway/platforms/connect?${params}`, { method: 'POST' });
    },
    sendMessage: (platform: string, userId: string, content: string) => {
      const params = new URLSearchParams({ platform, user_id: userId, content });
      return request<{ success: boolean }>(`/gateway/send?${params}`, { method: 'POST' });
    },
    providers: () => request<any>('/gateway/providers'),
    addProvider: (data: { name: string; provider_type: string; api_base?: string; api_key?: string; default_model?: string }) =>
      request<any>('/gateway/providers', { method: 'POST', body: JSON.stringify(data) }),
    removeProvider: (id: string) => request<any>(`/gateway/providers/${id}`, { method: 'DELETE' }),
    testRoute: (data: { model: string; messages: Record<string, any>[] }) =>
      request<any>('/gateway/route', { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── Daemon ──
  daemon: {
    stats: () =>
      request<import('../types').DaemonStats>('/daemon/stats'),
    getAgent: (agentId: string) =>
      request<import('../types').DaemonRuntime>(`/daemon/agents/${agentId}`),
    startAgent: (agentId: string, agentName?: string) => {
      const params = agentName ? `?agent_name=${encodeURIComponent(agentName)}` : '';
      return request<{ success: boolean; agent_id: string }>(`/daemon/agents/${agentId}/start${params}`, { method: 'POST' });
    },
    stopAgent: (agentId: string) =>
      request<{ success: boolean }>(`/daemon/agents/${agentId}/stop`, { method: 'POST' }),
    restartAgent: (agentId: string) =>
      request<{ success: boolean }>(`/daemon/agents/${agentId}/restart`, { method: 'POST' }),
    startAll: () =>
      request<{ success: boolean }>('/daemon/start-all', { method: 'POST' }),
    stopAll: () =>
      request<{ success: boolean }>('/daemon/stop-all', { method: 'POST' }),
  },

  // ── Squads ──
  squads: {
    form: (data: { name: string; description?: string; leader_id?: string }) =>
      request<import('../types').Squad>('/squads', { method: 'POST', body: JSON.stringify(data) }),
    list: (status?: string) => {
      const params = status ? `?status=${status}` : '';
      return request<Array<import('../types').Squad>>(`/squads${params}`);
    },
    get: (id: string) => request<import('../types').Squad>(`/squads/${id}`),
    activate: (id: string) => request<{ success: boolean }>(`/squads/${id}/activate`, { method: 'POST' }),
    pause: (id: string) => request<{ success: boolean }>(`/squads/${id}/pause`, { method: 'POST' }),
    dissolve: (id: string) => request<{ success: boolean }>(`/squads/${id}/dissolve`, { method: 'POST' }),
    addMember: (squadId: string, agentId: string, agentName?: string, role?: string, expertise?: string) => {
      const params = new URLSearchParams({ agent_id: agentId, agent_name: agentName || '', role: role || 'generalist', expertise: expertise || '' });
      return request<{ success: boolean }>(`/squads/${squadId}/members?${params}`, { method: 'POST' });
    },
    removeMember: (squadId: string, agentId: string) =>
      request<{ success: boolean }>(`/squads/${squadId}/members/${agentId}`, { method: 'DELETE' }),
    setLeader: (squadId: string, agentId: string) =>
      request<{ success: boolean }>(`/squads/${squadId}/leader/${agentId}`, { method: 'POST' }),
    delegate: (squadId: string, taskDescription: string, expertise?: string) => {
      const params = new URLSearchParams({ task_description: taskDescription, expertise: expertise || '' });
      return request(`/squads/${squadId}/delegate?${params}`, { method: 'POST' });
    },
    recordOutcome: (squadId: string, agentId: string, success: boolean) => {
      const params = new URLSearchParams({ agent_id: agentId, success: String(success) });
      return request<{ recorded: boolean }>(`/squads/${squadId}/record-outcome?${params}`, { method: 'POST' });
    },
    startDiscussion: (squadId: string, topic: string, createdBy: string, taskId?: string) => {
      const params = new URLSearchParams({ topic, created_by: createdBy, task_id: taskId || '' });
      return request<import('../types').DiscussionThread>(`/squads/${squadId}/discussions?${params}`, { method: 'POST' });
    },
    postToDiscussion: (squadId: string, threadId: string, agentId: string, content: string) => {
      const params = new URLSearchParams({ agent_id: agentId, content });
      return request<{ posted: boolean }>(`/squads/${squadId}/discussions/${threadId}/post?${params}`, { method: 'POST' });
    },
    resolveDiscussion: (squadId: string, threadId: string, resolution?: string) => {
      const params = new URLSearchParams({ resolution: resolution || '' });
      return request<{ resolved: boolean }>(`/squads/${squadId}/discussions/${threadId}/resolve?${params}`, { method: 'POST' });
    },
    stats: () => request('/squads/stats'),
    byAgent: (agentId: string) => request<Array<import('../types').Squad>>(`/squads/by-agent/${agentId}`),
  },

  // ── RAG Knowledge Base ──
  rag: {
    ingestText: (agentId: string, data: { content: string; title?: string; source?: string; metadata?: Record<string, unknown> }) =>
      request<import('../types').RAGDocument>(`/agents/${agentId}/rag/ingest-text`, { method: 'POST', body: JSON.stringify(data) }),
    ingestFile: (agentId: string, filePath: string) => {
      const params = new URLSearchParams({ file_path: filePath });
      return request<import('../types').RAGDocument>(`/agents/${agentId}/rag/ingest-file?${params}`, { method: 'POST' });
    },
    ingestUrl: (agentId: string, url: string) => {
      const params = new URLSearchParams({ url });
      return request<import('../types').RAGDocument>(`/agents/${agentId}/rag/ingest-url?${params}`, { method: 'POST' });
    },
    search: (agentId: string, query: string, topK?: number, hybrid?: boolean) => {
      const params = new URLSearchParams({ query });
      if (topK) params.set('top_k', String(topK));
      if (hybrid !== undefined) params.set('hybrid', String(hybrid));
      return request<{ agent_id: string; query: string; results: Array<import('../types').RAGSearchResult>; count: number }>(`/agents/${agentId}/rag/search?${params}`);
    },
    documents: (agentId: string) =>
      request<{ agent_id: string; documents: Array<import('../types').RAGDocument> }>(`/agents/${agentId}/rag/documents`),
    deleteDocument: (agentId: string, docId: string) =>
      request<void>(`/agents/${agentId}/rag/documents/${docId}`, { method: 'DELETE' }),
    stats: (agentId: string) =>
      request<import('../types').RAGStats>(`/agents/${agentId}/rag/stats`),
  },

  // ── Swarm Engine ──
  swarm: {
    form: (data: { name: string; goal: string; min_members?: number }) =>
      request<import('../types').SwarmSession>(`/swarm/form`, { method: 'POST', body: JSON.stringify(data) }),
    plan: (sessionId: string) =>
      request<{ session_id: string; tasks: Array<import('../types').SwarmTask>; count: number }>(`/swarm/${sessionId}/plan`, { method: 'POST' }),
    execute: (sessionId: string) =>
      request<import('../types').SwarmSession>(`/swarm/${sessionId}/execute`, { method: 'POST' }),
    get: (sessionId: string) =>
      request<import('../types').SwarmSession>(`/swarm/${sessionId}`),
    list: () =>
      request<{ sessions: Array<import('../types').SwarmSession> }>('/swarm/sessions'),
    stats: () =>
      request<import('../types').SwarmStats>('/swarm/stats'),
  },

  // ── Runtime Hub ──
  runtimes: {
    list: () =>
      request<{ runtimes: Array<import('../types').RuntimeItem> }>('/runtimes'),
    get: (id: string) =>
      request<import('../types').RuntimeItem>(`/runtimes/${id}`),
    create: (data: { name: string; backend?: string; workspace_dir?: string; image?: string; tags?: string[] }) =>
      request<import('../types').RuntimeItem>('/runtimes', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<{ success: boolean }>(`/runtimes/${id}`, { method: 'DELETE' }),
    execute: (data: { runtime_id: string; command?: string; code?: string; language?: string; timeout_sec?: number }) =>
      request<import('../types').ExecutionOutput>('/runtimes/execute', { method: 'POST', body: JSON.stringify(data) }),
    history: (id: string) =>
      request<{ history: Array<import('../types').ExecutionOutput> }>(`/runtimes/${id}/history`),
    discover: () =>
      request<{ discovered: Array<import('../types').RuntimeItem> }>('/runtimes/discover', { method: 'POST' }),
    stats: () =>
      request<import('../types').RuntimeHubStats>('/runtimes-stats'),
  },

  // ── Scheduler ──
  schedules: {
    list: () =>
      request<{ schedules: Array<import('../types').ScheduledTaskItem> }>('/schedules'),
    get: (id: string) =>
      request<import('../types').ScheduledTaskItem>(`/schedules/${id}`),
    create: (data: { name: string; prompt: string; agent_id?: string; description?: string; cron_expression?: string; interval_seconds?: number; schedule_type?: string; natural_schedule?: string; tags?: string[] }) =>
      request<import('../types').ScheduledTaskItem>('/schedules', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<{ success: boolean }>(`/schedules/${id}`, { method: 'DELETE' }),
    pause: (id: string) =>
      request<{ success: boolean }>(`/schedules/${id}/pause`, { method: 'POST' }),
    resume: (id: string) =>
      request<{ success: boolean }>(`/schedules/${id}/resume`, { method: 'POST' }),
    history: (id: string) =>
      request<{ history: Array<Record<string, unknown>> }>(`/schedules/${id}/history`),
    parse: (text: string) => {
      const params = new URLSearchParams({ text });
      return request<import('../types').ScheduleParseResult>(`/schedules/parse?${params}`, { method: 'POST' });
    },
    stats: () =>
      request<import('../types').SchedulerStats>('/schedules-stats'),
  },

  // ── Studio ──
  studios: {
    list: () =>
      request<{ studios: Array<import('../types').StudioInfoItem>; templates: Array<import('../types').StudioTemplate> }>('/studios'),
    get: (id: string) =>
      request<import('../types').StudioInfoItem>(`/studios/${id}`),
    create: (data: { name: string; description?: string; template_id?: string; icon?: string; tags?: string[] }) =>
      request<import('../types').StudioInfoItem>('/studios', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<{ success: boolean }>(`/studios/${id}`, { method: 'DELETE' }),
    analyze: (id: string) =>
      request<Record<string, unknown>>(`/studios/${id}/analyze`),
    memory: {
      list: (studioId: string, category?: string, search?: string) => {
        const params = new URLSearchParams();
        if (category) params.set('category', category);
        if (search) params.set('search', search);
        return request<{ entries: Array<import('../types').StudioMemoryEntry>; stats: Record<string, unknown> }>(`/studios/${studioId}/memory?${params}`);
      },
      create: (studioId: string, data: { key: string; value: string; category?: string; importance?: string; source?: string; tags?: string[]; context?: string; confidence?: number }) =>
        request<import('../types').StudioMemoryEntry>(`/studios/${studioId}/memory`, { method: 'POST', body: JSON.stringify(data) }),
      update: (studioId: string, entryId: string, data: { value?: string; category?: string; importance?: string; tags?: string[]; is_pinned?: boolean }) =>
        request<{ success: boolean; version: number }>(`/studios/${studioId}/memory/${entryId}`, { method: 'PUT', body: JSON.stringify(data) }),
      delete: (studioId: string, entryId: string) =>
        request<{ success: boolean }>(`/studios/${studioId}/memory/${entryId}`, { method: 'DELETE' }),
      pin: (studioId: string, entryId: string) =>
        request<{ success: boolean }>(`/studios/${studioId}/memory/${entryId}/pin`, { method: 'POST' }),
    },
    snapshots: {
      create: (studioId: string, label?: string, description?: string) => {
        const params = new URLSearchParams();
        if (label) params.set('label', label);
        if (description) params.set('description', description);
        return request<import('../types').StudioSnapshot>(`/studios/${studioId}/snapshots?${params}`, { method: 'POST' });
      },
      list: (studioId: string) =>
        request<{ snapshots: Array<import('../types').StudioSnapshot> }>(`/studios/${studioId}/snapshots`),
      rollback: (studioId: string, snapshotId: string) => {
        const params = new URLSearchParams({ snapshot_id: snapshotId });
        return request<{ success: boolean; entry_count: number }>(`/studios/${studioId}/snapshots/rollback?${params}`, { method: 'POST' });
      },
    },
    stats: () =>
      request<import('../types').StudioStats>('/studios-stats'),
  },

  // ── Workflow ──
  workflows: {
    list: (state?: string, priority?: string, assigned_agent?: string) => {
      const params = new URLSearchParams();
      if (state) params.set('state', state);
      if (priority) params.set('priority', priority);
      if (assigned_agent) params.set('assigned_agent', assigned_agent);
      return request<{ tasks: Array<import('../types').WorkflowTaskItem> }>(`/workflow/tasks?${params}`);
    },
    get: (id: string) =>
      request<import('../types').WorkflowTaskItem>(`/workflow/tasks/${id}`),
    create: (data: { title: string; description?: string; priority?: string; assigned_agent?: string; created_by?: string; dependencies?: string[]; tags?: string[]; studio_id?: string }) =>
      request<import('../types').WorkflowTaskItem>('/workflow/tasks', { method: 'POST', body: JSON.stringify(data) }),
    transition: (id: string, state: string) =>
      request<import('../types').WorkflowTaskItem>(`/workflow/tasks/${id}/transition`, { method: 'POST', body: JSON.stringify({ state }) }),
    assign: (id: string, agentId: string) =>
      request<import('../types').WorkflowTaskItem>(`/workflow/tasks/${id}/assign`, { method: 'POST', body: JSON.stringify({ agent_id: agentId }) }),
    delegate: (id: string, delegateAgentId: string) =>
      request(`/workflow/tasks/${id}/delegate`, { method: 'POST', body: JSON.stringify({ delegate_agent_id: delegateAgentId }) }),
    blockers: {
      list: (taskId: string) =>
        request<{ blockers: Array<import('../types').WorkflowBlocker> }>(`/workflow/tasks/${taskId}/blockers`),
      create: (taskId: string, blockerType: string, description: string, reportedBy?: string) =>
        request<import('../types').WorkflowBlocker>(`/workflow/tasks/${taskId}/blockers`, { method: 'POST', body: JSON.stringify({ blocker_type: blockerType, description, reported_by: reportedBy || '' }) }),
      resolve: (taskId: string, blockerId: string, resolution?: string) =>
        request<{ success: boolean }>(`/workflow/tasks/${taskId}/blockers/${blockerId}/resolve`, { method: 'POST', body: JSON.stringify({ resolution: resolution || '' }) }),
    },
    canStart: (id: string) =>
      request<{ can_start: boolean; reason: string; unmet_dependencies: string[] }>(`/workflow/tasks/${id}/can-start`),
    recent: (limit: number = 20) =>
      request<{ tasks: Array<import('../types').WorkflowTaskItem> }>(`/workflow/recent?limit=${limit}`),
    stats: () =>
      request<import('../types').WorkflowStats>('/workflow-stats'),
  },

  compressor: {
    compress: (agentId: string, conversationId?: string) => {
      const qs = new URLSearchParams();
      if (conversationId) qs.set('conversation_id', conversationId);
      return request<Record<string, unknown>>(`/agents/${agentId}/compressor/compress?${qs.toString()}`, { method: 'POST' });
    },
    trajectories: (agentId: string, limit?: number) => {
      const qs = new URLSearchParams();
      if (limit) qs.set('limit', String(limit));
      return request<{ agent_id: string; trajectories: Array<Record<string, unknown>> }>(`/agents/${agentId}/compressor/trajectories?${qs.toString()}`);
    },
    patterns: (agentId: string, patternType?: string) => {
      const qs = new URLSearchParams();
      if (patternType) qs.set('pattern_type', patternType);
      return request<{ agent_id: string; patterns: Array<Record<string, unknown>>; count: number }>(`/agents/${agentId}/compressor/patterns?${qs.toString()}`);
    },
    stats: () =>
      request<Record<string, unknown>>('/compressor/stats'),
    export: (agentId?: string, format?: string) => {
      const qs = new URLSearchParams();
      if (agentId) qs.set('agent_id', agentId);
      if (format) qs.set('format', format);
      return request<{ format: string; agent_id: string | null; data: string }>(`/compressor/export?${qs.toString()}`);
    },
  },

  // ── Costs ──
  costs: {
    overview: () => request<any>('/costs/overview'),
    breakdown: (period: string) => request<any>(`/costs/breakdown?period=${period}`),
    byTier: () => request<any>('/costs/by-tier'),
    suggestions: () => request<any>('/costs/suggestions'),
    budgets: () => request<any>('/costs/budgets'),
  },

  checkpoints: {
    save: (agentId: string, name?: string) => {
      const qs = new URLSearchParams();
      if (name) qs.set('name', name);
      return request<{ agent_id: string; checkpoint_id: string; name: string }>(`/agents/${agentId}/checkpoints?${qs.toString()}`, { method: 'POST' });
    },
    list: (agentId: string) =>
      request<{ agent_id: string; checkpoints: Array<{ id: string; name: string; timestamp: string }> }>(`/agents/${agentId}/checkpoints`),
    restore: (agentId: string, checkpointId: string) =>
      request<{ agent_id: string; restored: boolean; checkpoint_id: string }>(`/agents/${agentId}/checkpoints/${checkpointId}/restore`, { method: 'POST' }),
    delete: (agentId: string, checkpointId: string) =>
      request<{ agent_id: string; deleted: boolean }>(`/agents/${agentId}/checkpoints/${checkpointId}`, { method: 'DELETE' }),
  },

  board: {
    getBoard: () => request<Record<string, unknown>>('/board'),
    stats: () => request<Record<string, unknown>>('/board/stats'),
    createIssue: (data: { title: string; description?: string; priority?: string; tags?: string[]; workspace_id?: string; context?: Record<string, unknown>; auto_assign?: boolean }) =>
      request<Record<string, unknown>>('/board/issues', { method: 'POST', body: JSON.stringify(data) }),
    listIssues: (params?: { state?: string; agent_id?: string; workspace_id?: string; priority?: string }) => {
      const qs = new URLSearchParams();
      if (params?.state) qs.set('state', params.state);
      if (params?.agent_id) qs.set('agent_id', params.agent_id);
      if (params?.workspace_id) qs.set('workspace_id', params.workspace_id);
      if (params?.priority) qs.set('priority', params.priority);
      return request<{ issues: Array<Record<string, unknown>>; count: number }>(`/board/issues?${qs.toString()}`);
    },
    getIssue: (issueId: string) => request<Record<string, unknown>>(`/board/issues/${issueId}`),
    updateIssue: (issueId: string, data: Record<string, unknown>) =>
      request<Record<string, unknown>>(`/board/issues/${issueId}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deleteIssue: (issueId: string) =>
      request<{ deleted: boolean }>(`/board/issues/${issueId}`, { method: 'DELETE' }),
    moveIssue: (issueId: string, state: string) =>
      request<Record<string, unknown>>(`/board/issues/${issueId}/move?state=${state}`, { method: 'POST' }),
    assignIssue: (issueId: string, agentId: string) =>
      request<Record<string, unknown>>(`/board/issues/${issueId}/assign?agent_id=${agentId}`, { method: 'POST' }),
    claimIssue: (issueId: string, agentId: string) =>
      request<Record<string, unknown>>(`/board/issues/${issueId}/claim?agent_id=${agentId}`, { method: 'POST' }),
    completeIssue: (issueId: string) =>
      request<Record<string, unknown>>(`/board/issues/${issueId}/complete`, { method: 'POST' }),
    failIssue: (issueId: string, error?: string) => {
      const qs = error ? `?error=${encodeURIComponent(error)}` : '';
      return request<Record<string, unknown>>(`/board/issues/${issueId}/fail${qs}`, { method: 'POST' });
    },
    listAutopilot: () => request<{ rules: Array<Record<string, unknown>> }>('/board/autopilot'),
    createAutopilot: (data: { name: string; agent_id: string; filters?: Record<string, unknown>; max_concurrent?: number }) =>
      request<Record<string, unknown>>('/board/autopilot', { method: 'POST', body: JSON.stringify(data) }),
    deleteAutopilot: (ruleId: string) =>
      request<{ deleted: boolean }>(`/board/autopilot/${ruleId}`, { method: 'DELETE' }),
  },

  compounding: {
    stats: () => request<Record<string, unknown>>('/compounding/stats'),
    listSkills: (category?: string, minQuality?: number) => {
      const qs = new URLSearchParams();
      if (category) qs.set('category', category);
      if (minQuality !== undefined) qs.set('min_quality', String(minQuality));
      return request<{ skills: Array<Record<string, unknown>>; count: number }>(`/compounding/skills?${qs.toString()}`);
    },
    getSkill: (skillId: string) => request<Record<string, unknown>>(`/compounding/skills/${skillId}`),
    feedback: (skillId: string, success: boolean, feedback?: string) => {
      const qs = new URLSearchParams();
      qs.set('success', String(success));
      if (feedback) qs.set('feedback', feedback);
      return request<Record<string, unknown>>(`/compounding/skills/${skillId}/feedback?${qs.toString()}`, { method: 'POST' });
    },
    deprecateSkill: (skillId: string) =>
      request<{ deprecated: boolean }>(`/compounding/skills/${skillId}/deprecate`, { method: 'POST' }),
    deleteSkill: (skillId: string) =>
      request<{ deleted: boolean }>(`/compounding/skills/${skillId}`, { method: 'DELETE' }),
    recordInteraction: (data: { agent_id: string; task_description?: string; tool_calls?: Array<Record<string, unknown>>; success?: boolean; output_summary?: string; metadata?: Record<string, unknown> }) =>
      request<{ interaction_id: string }>('/compounding/interactions', { method: 'POST', body: JSON.stringify(data) }),
    generateSkills: () =>
      request<{ skills: Array<Record<string, unknown>>; count: number }>('/compounding/generate', { method: 'POST' }),
    getPatterns: () => request<{ patterns: Array<Record<string, unknown>> }>('/compounding/patterns'),
    searchSkills: (taskDescription: string, requiredTools?: string, limit?: number) => {
      const qs = new URLSearchParams();
      qs.set('task_description', taskDescription);
      if (requiredTools) qs.set('required_tools', requiredTools);
      if (limit) qs.set('limit', String(limit));
      return request<{ skills: Array<Record<string, unknown>>; count: number }>(`/compounding/search?${qs.toString()}`, { method: 'POST' });
    },
  },

  whiteboxMemory: {
    stats: () => request<Record<string, unknown>>('/whitebox-memory/stats'),
    listEntries: (params?: { workspace_id?: string; agent_id?: string; memory_type?: string; importance?: string; tags?: string; pinned_only?: boolean; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params?.workspace_id) qs.set('workspace_id', params.workspace_id);
      if (params?.agent_id) qs.set('agent_id', params.agent_id);
      if (params?.memory_type) qs.set('memory_type', params.memory_type);
      if (params?.importance) qs.set('importance', params.importance);
      if (params?.tags) qs.set('tags', params.tags);
      if (params?.pinned_only) qs.set('pinned_only', 'true');
      if (params?.limit) qs.set('limit', String(params.limit));
      if (params?.offset) qs.set('offset', String(params.offset));
      return request<{ entries: Array<Record<string, unknown>>; count: number; total: number }>(`/whitebox-memory/entries?${qs.toString()}`);
    },
    createEntry: (data: { content: string; memory_type?: string; importance?: string; workspace_id?: string; agent_id?: string; tags?: string[] }) =>
      request<Record<string, unknown>>('/whitebox-memory/entries', { method: 'POST', body: JSON.stringify(data) }),
    getEntry: (memoryId: string) => request<Record<string, unknown>>(`/whitebox-memory/entries/${memoryId}`),
    editContent: (memoryId: string, newContent: string) =>
      request<Record<string, unknown>>(`/whitebox-memory/entries/${memoryId}/edit?new_content=${encodeURIComponent(newContent)}`, { method: 'PUT' }),
    deleteEntry: (memoryId: string) =>
      request<{ deleted: boolean }>(`/whitebox-memory/entries/${memoryId}`, { method: 'DELETE' }),
    pinEntry: (memoryId: string) =>
      request<{ pinned: boolean }>(`/whitebox-memory/entries/${memoryId}/pin`, { method: 'POST' }),
    unpinEntry: (memoryId: string) =>
      request<{ unpinned: boolean }>(`/whitebox-memory/entries/${memoryId}/unpin`, { method: 'POST' }),
    search: (query: string, workspaceId?: string, limit?: number) => {
      const qs = new URLSearchParams();
      qs.set('query', query);
      if (workspaceId) qs.set('workspace_id', workspaceId);
      if (limit) qs.set('limit', String(limit));
      return request<{ results: Array<Record<string, unknown>>; count: number }>(`/whitebox-memory/search?${qs.toString()}`);
    },
    runDream: (workspaceId?: string) => {
      const qs = workspaceId ? `?workspace_id=${workspaceId}` : '';
      return request<Record<string, unknown>>(`/whitebox-memory/dream${qs}`, { method: 'POST' });
    },
    rollbackDream: () =>
      request<Record<string, unknown>>('/whitebox-memory/dream/rollback', { method: 'POST' }),
    getAuditTrail: (memoryId: string) =>
      request<{ trail: Array<Record<string, unknown>> }>(`/whitebox-memory/entries/${memoryId}/audit`),
    export: (format?: string) => {
      const qs = format ? `?format=${format}` : '';
      return request<Record<string, unknown>>(`/whitebox-memory/export${qs}`);
    },
  },

  pipelines: {
    list: () => request<{pipelines: any[]}>('/pipelines'),
    create: (data: {name: string; description?: string; steps: any[]}) =>
      request<{pipeline_id: string; name: string; step_count: number}>('/pipelines', {method: 'POST', body: JSON.stringify(data)}),
    get: (id: string) => request<any>(`/pipelines/${id}`),
    delete: (id: string) => request<{deleted: boolean}>(`/pipelines/${id}`, {method: 'DELETE'}),
    run: (data: {pipeline_id: string; initial_state?: Record<string, any>}) =>
      request<any>('/pipelines/run', {method: 'POST', body: JSON.stringify(data)}),
    getRun: (runId: string) => request<any>(`/pipelines/runs/${runId}`),
    listRuns: (pipelineId?: string, limit?: number) =>
      request<{runs: any[]}>(`/pipeline-runs${pipelineId ? `?pipeline_id=${pipelineId}` : ''}${limit ? `${pipelineId ? '&' : '?'}limit=${limit}` : ''}`),
    stats: () => request<any>('/pipeline-stats'),
  },

  cache: {
    stats: () => request<any>('/cache/stats'),
    invalidate: (agentId?: string) =>
      request<{invalidated: boolean}>(`/cache/invalidate${agentId ? `?agent_id=${agentId}` : ''}`, {method: 'POST'}),
  },

  capabilities: {
    list: (domain?: string) =>
      request<{capabilities: any[]}>(`/capabilities${domain ? `?domain=${domain}` : ''}`),
    domains: () => request<{domains: any[]}>('/capabilities/domains'),
    getProfile: (agentId: string) => request<any>(`/capabilities/profiles/${agentId}`),
    updateProfile: (agentId: string, data: {agent_name?: string}) =>
      request<any>(`/capabilities/profiles/${agentId}/update`, {method: 'POST', body: JSON.stringify(data)}),
    addCapability: (agentId: string, capabilityId: string, score?: number) =>
      request<any>(`/capabilities/profiles/${agentId}/capabilities?capability_id=${capabilityId}&score=${score || 0.5}`, {method: 'POST'}),
    recordUsage: (agentId: string, capabilityId: string, success?: boolean) =>
      request<any>(`/capabilities/profiles/${agentId}/record-usage?capability_id=${capabilityId}&success=${success !== false}`, {method: 'POST'}),
    match: (requiredCapabilities: string, minProficiency?: string) =>
      request<{matches: any[]}>(`/capabilities/match?required_capabilities=${requiredCapabilities}&min_proficiency=${minProficiency || 'intermediate'}`, {method: 'POST'}),
    getGaps: (agentId: string, domain?: string) =>
      request<{gaps: any[]}>(`/capabilities/profiles/${agentId}/gaps${domain ? `?domain=${domain}` : ''}`),
    applyDecay: () => request<{decay_applied: boolean}>('/capabilities/decay', {method: 'POST'}),
    stats: () => request<any>('/capability-stats'),
  },

  knowledgeGraph: {
    stats: () => request<any>('/kg/stats'),
    listEntities: (params?: {entity_type?: string; name_contains?: string; limit?: number}) => {
      const qs = new URLSearchParams();
      if (params?.entity_type) qs.set('entity_type', params.entity_type);
      if (params?.name_contains) qs.set('name_contains', params.name_contains);
      if (params?.limit) qs.set('limit', String(params.limit));
      return request<{entities: any[]; count: number}>(`/kg/entities?${qs.toString()}`);
    },
    createEntity: (data: {name: string; entity_type?: string; properties?: Record<string, any>; confidence?: number; source?: string}) =>
      request<{entity_id: string}>(`/kg/entities`, {method: 'POST', body: JSON.stringify(data)}),
    getEntity: (id: string) => request<any>(`/kg/entities/${id}`),
    updateEntity: (id: string, properties: Record<string, any>) =>
      request<{updated: boolean}>(`/kg/entities/${id}`, {method: 'PATCH', body: JSON.stringify(properties)}),
    deleteEntity: (id: string) =>
      request<{deleted: boolean}>(`/kg/entities/${id}`, {method: 'DELETE'}),
    createRelationship: (data: {source_id: string; target_id: string; relation_type?: string; weight?: number}) =>
      request<{relationship_id: string}>(`/kg/relationships`, {method: 'POST', body: JSON.stringify(data)}),
    getRelationships: (entityId: string) =>
      request<{relationships: any[]; count: number}>(`/kg/entities/${entityId}/relationships`),
    deleteRelationship: (relId: string) =>
      request<{deleted: boolean}>(`/kg/relationships/${relId}`, {method: 'DELETE'}),
    getNeighborhood: (entityId: string, depth?: number) =>
      request<any>(`/kg/entities/${entityId}/neighborhood?depth=${depth || 1}`),
    findPaths: (sourceId: string, targetId: string, maxDepth?: number) =>
      request<{paths: any[]; count: number}>(`/kg/paths?source_id=${sourceId}&target_id=${targetId}&max_depth=${maxDepth || 5}`),
    semanticSearch: (query: string, entityType?: string, topK?: number) =>
      request<{results: any[]; count: number}>(`/kg/search?query=${encodeURIComponent(query)}${entityType ? `&entity_type=${entityType}` : ''}&top_k=${topK || 10}`),
    extract: (text: string, source?: string) =>
      request<any>('/kg/extract', {method: 'POST', body: JSON.stringify({text, source: source || 'api'})}),
    export: (entityIds?: string, includeNeighbors?: boolean) =>
      request<any>(`/kg/export${entityIds ? `?entity_ids=${entityIds}` : ''}${includeNeighbors ? `${entityIds ? '&' : '?'}include_neighbors=true` : ''}`),
    clear: () => request<{cleared: boolean}>('/kg/clear', {method: 'POST'}),
  },

  // ── Memory Sync ──
  memorySync: {
    stats: () => request<any>('/memory-sync/stats'),
    config: () => request<any>('/memory-sync/config'),
    updateConfig: (params: {max_shared_per_agent?: number; max_broadcast_agents?: number; default_sync_interval?: number; auto_sync_enabled?: boolean}) => {
      const qs = new URLSearchParams();
      if (params.max_shared_per_agent) qs.set('max_shared_per_agent', String(params.max_shared_per_agent));
      if (params.max_broadcast_agents) qs.set('max_broadcast_agents', String(params.max_broadcast_agents));
      if (params.default_sync_interval) qs.set('default_sync_interval', String(params.default_sync_interval));
      if (params.auto_sync_enabled !== undefined) qs.set('auto_sync_enabled', String(params.auto_sync_enabled));
      return request<any>(`/memory-sync/config?${qs.toString()}`, {method: 'POST'});
    },
    share: (data: {source_agent_id: string; target_agent_id: string; content: string; memory_type?: string; importance?: number; tags?: string[]}) =>
      request<any>('/memory-sync/share', {method: 'POST', body: JSON.stringify(data)}),
    broadcast: (data: {source_agent_id: string; content: string; memory_type?: string; importance?: number; tags?: string[]; target_role?: string}) =>
      request<any>('/memory-sync/broadcast', {method: 'POST', body: JSON.stringify(data)}),
    search: (query: string, agentIds?: string[], limit?: number) => {
      const qs = new URLSearchParams();
      qs.set('query', query);
      if (agentIds?.length) qs.set('agent_ids', agentIds.join(','));
      if (limit) qs.set('limit', String(limit));
      return request<{results: any[]; count: number}>(`/memory-sync/search?${qs.toString()}`);
    },
    getContext: (agentId: string, topic: string, maxMemories?: number) => {
      const qs = new URLSearchParams({agent_id: agentId, topic});
      if (maxMemories) qs.set('max_memories', String(maxMemories));
      return request<{context: any; agent_id: string}>(`/memory-sync/context?${qs.toString()}`);
    },
    groups: {
      list: () => request<{groups: any[]}>('/memory-sync/groups'),
      create: (data: {name: string; agent_ids: string[]; sync_interval?: number; filters?: Record<string, unknown>}) =>
        request<{group_id: string}>(`/memory-sync/groups`, {method: 'POST', body: JSON.stringify(data)}),
      get: (groupId: string) => request<any>(`/memory-sync/groups/${groupId}`),
      update: (groupId: string, data: {name?: string; agent_ids?: string[]; sync_interval?: number; enabled?: boolean}) =>
        request<{updated: boolean}>(`/memory-sync/groups/${groupId}`, {method: 'PUT', body: JSON.stringify(data)}),
      delete: (groupId: string) =>
        request<{deleted: boolean}>(`/memory-sync/groups/${groupId}`, {method: 'DELETE'}),
      sync: (groupId: string) =>
        request<any>(`/memory-sync/groups/${groupId}/sync`, {method: 'POST'}),
    },
    records: (sourceAgentId?: string, targetAgentId?: string, limit?: number) => {
      const qs = new URLSearchParams();
      if (sourceAgentId) qs.set('source_agent_id', sourceAgentId);
      if (targetAgentId) qs.set('target_agent_id', targetAgentId);
      if (limit) qs.set('limit', String(limit));
      return request<{records: any[]; count: number}>(`/memory-sync/records?${qs.toString()}`);
    },
  },

  // ── Platform Hub ──
  platformHub: {
    health: () => request<any>('/platform/hub/health'),
    stats: () => request<any>('/platform/hub/stats'),
    config: () => request<any>('/platform/hub/config'),
    updateConfig: (data: Record<string, unknown>) =>
      request<any>('/platform/hub/config', { method: 'POST', body: JSON.stringify(data) }),
    subsystems: () => request<any>('/platform/hub/subsystems'),
    subsystem: (name: string) => request<any>(`/platform/hub/subsystems/${name}`),
    events: (eventType?: string, limit?: number) => {
      const qs = new URLSearchParams();
      if (eventType) qs.set('event_type', eventType);
      if (limit) qs.set('limit', String(limit));
      return request<any>(`/platform/hub/events?${qs.toString()}`);
    },
    start: () => request<any>('/platform/hub/start', { method: 'POST' }),
    stop: () => request<any>('/platform/hub/stop', { method: 'POST' }),
  },

  // ── Reactive Loop ──
  reactiveLoop: {
    stats: (agentId: string) => request<any>(`/reactive-loop/${agentId}/stats`),
    start: (agentId: string, data: { mode?: string; cycle_interval_ms?: number }) =>
      request<any>(`/reactive-loop/${agentId}/start`, { method: 'POST', body: JSON.stringify(data) }),
    stop: (agentId: string) =>
      request<any>(`/reactive-loop/${agentId}/stop`, { method: 'POST' }),
    observe: (agentId: string, data: { source: string; summary: string; priority?: number; data?: Record<string, unknown> }) =>
      request<any>(`/reactive-loop/${agentId}/observe`, { method: 'POST', body: JSON.stringify(data) }),
    enqueue: (agentId: string, data: { description: string; priority?: number; handler?: string; payload?: Record<string, unknown>; depends_on?: string[] }) =>
      request<any>(`/reactive-loop/${agentId}/enqueue`, { method: 'POST', body: JSON.stringify(data) }),
    actions: (agentId: string, limit?: number) =>
      request<{ agent_id: string; actions: any[] }>(`/reactive-loop/${agentId}/actions?limit=${limit || 20}`),
    cycles: (agentId: string, limit?: number) =>
      request<{ agent_id: string; cycles: any[] }>(`/reactive-loop/${agentId}/cycles?limit=${limit || 10}`),
    setMode: (agentId: string, mode: string) => {
      const qs = new URLSearchParams({ mode });
      return request<any>(`/reactive-loop/${agentId}/mode?${qs}`, { method: 'POST' });
    },
  },

  // ── Agent Dashboard ──
  agentDashboard: {
    overview: (agentId?: string) => {
      const qs = agentId ? `?agent_id=${agentId}` : '';
      return request<{ agents: any[]; total_agents: number; system_summary: any }>(`/agents/dashboard${qs}`);
    },
  },

  // ── Proactive Discovery ──
  proactive: {
    status: (agentId: string) => request<any>(`/agents/${agentId}/proactive/status`),
    tasks: (agentId: string, params?: { status?: string; source?: string; urgency?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set('status', params.status);
      if (params?.source) qs.set('source', params.source);
      if (params?.urgency) qs.set('urgency', params.urgency);
      if (params?.limit) qs.set('limit', String(params.limit));
      const q = qs.toString();
      return request<{ tasks: any[]; total: number }>(`/agents/${agentId}/proactive/tasks${q ? `?${q}` : ''}`);
    },
    insights: (agentId: string, limit?: number) => {
      const qs = limit ? `?limit=${limit}` : '';
      return request<{ insights: string[]; total: number }>(`/agents/${agentId}/proactive/insights${qs}`);
    },
    scan: (agentId: string) =>
      request<any>(`/agents/${agentId}/proactive/scan`, { method: 'POST' }),
    start: (agentId: string, interval?: number) => {
      const qs = interval ? `?interval=${interval}` : '';
      return request<{ status: string }>(`/agents/${agentId}/proactive/start${qs}`, { method: 'POST' });
    },
    stop: (agentId: string) =>
      request<{ status: string }>(`/agents/${agentId}/proactive/stop`, { method: 'POST' }),
    scheduleTask: (agentId: string, taskId: string) =>
      request<{ status: string }>(`/agents/${agentId}/proactive/tasks/${taskId}/schedule`, { method: 'POST' }),
    dismissTask: (agentId: string, taskId: string) =>
      request<{ status: string }>(`/agents/${agentId}/proactive/tasks/${taskId}/dismiss`, { method: 'POST' }),
    completeTask: (agentId: string, taskId: string) =>
      request<{ status: string }>(`/agents/${agentId}/proactive/tasks/${taskId}/complete`, { method: 'POST' }),
    interactions: (agentId: string, limit?: number) => {
      const qs = limit ? `?limit=${limit}` : '';
      return request<{ interactions: any[]; count: number }>(`/agents/${agentId}/proactive/interactions${qs}`);
    },
  },

  // ── Meta-Cognition ──
  metacognition: {
    stats: (agentId: string) => request<any>(`/agents/${agentId}/metacognition/stats`),
    insights: (agentId: string) =>
      request<{ agent_id: string; insights: string[]; count: number }>(`/agents/${agentId}/metacognition/insights`),
    decisions: (agentId: string, limit?: number) => {
      const qs = limit ? `?limit=${limit}` : '';
      return request<{ agent_id: string; decisions: any[]; count: number }>(`/agents/${agentId}/metacognition/decisions${qs}`);
    },
  },

  // ── Proactive-Autopilot Bridge ──
  bridge: {
    proactiveToAutopilot: (agentId: string, maxTasks?: number) => {
      const qs = maxTasks ? `?max_tasks=${maxTasks}` : '';
      return request<{ scheduled: number; total_pending: number; message: string }>(`/agents/${agentId}/bridge/proactive-to-autopilot${qs}`, { method: 'POST' });
    },
  },

  // ── Agent Evolution ──
  evolution: {
    stats: (agentId: string) => request<any>(`/agents/${agentId}/evolution/stats`),
    pathways: (agentId: string) =>
      request<{ agent_id: string; pathways: any[]; count: number }>(`/agents/${agentId}/evolution/pathways`),
    insights: (agentId: string) =>
      request<{ agent_id: string; insights: string[]; count: number }>(`/agents/${agentId}/evolution/insights`),
    runCycle: (agentId: string) =>
      request<any>(`/agents/${agentId}/evolution/run`, { method: 'POST' }),
  },

  // ── Agent Communication Protocol ──
  comm: {
    stats: () => request<any>('/comm/stats'),
    messages: (limit?: number) => request<any>(`/comm/messages?limit=${limit || 50}`),
    send: (data: { sender_id: string; recipient_id?: string; subject?: string; content: string; msg_type?: string; priority?: string }) => {
      const qs = new URLSearchParams();
      qs.set('sender_id', data.sender_id);
      if (data.recipient_id) qs.set('recipient_id', data.recipient_id);
      if (data.subject) qs.set('subject', data.subject);
      qs.set('content', data.content);
      qs.set('msg_type', data.msg_type || 'direct');
      qs.set('priority', data.priority || 'normal');
      return request<any>(`/comm/send?${qs.toString()}`, { method: 'POST' });
    },
    delegate: (data: { from_agent_id: string; to_agent_id: string; task_description: string; task_context?: Record<string, unknown>; required_capabilities?: string[]; priority?: string }) =>
      request<any>('/comm/delegate', { method: 'POST', body: JSON.stringify(data) }),
    pendingDelegations: (agentId: string) => request<any>(`/comm/delegations/pending?agent_id=${agentId}`),
    registerAgent: (agentId: string, capabilities?: string) => {
      const qs = new URLSearchParams({ agent_id: agentId });
      if (capabilities) qs.set('capabilities', capabilities);
      return request<any>(`/comm/agents/register?${qs.toString()}`, { method: 'POST' });
    },
    unregisterAgent: (agentId: string) =>
      request<any>(`/comm/agents/unregister?agent_id=${agentId}`, { method: 'POST' }),
    onlineAgents: () => request<any>('/comm/agents/online'),
  },

  // ── Resource Manager ──
  resources: {
    stats: () => request<any>('/resources/stats'),
    usage: (agentId: string) => request<any>(`/resources/usage?agent_id=${agentId}`),
    alerts: (limit?: number, severity?: string) => {
      const qs = new URLSearchParams();
      if (limit) qs.set('limit', String(limit));
      if (severity) qs.set('severity', severity);
      return request<any>(`/resources/alerts?${qs.toString()}`);
    },
    status: (resourceType: string) => request<any>(`/resources/status?resource_type=${resourceType}`),
    reset: () => request<any>('/resources/reset', { method: 'POST' }),
  },

  // ── Agent Self ──
  agentSelf: {
    profile: (agentId: string) =>
      request<import('../types').AgentSelfProfile>(`/agents/${agentId}/self/profile`),
    stats: (agentId: string) =>
      request<import('../types').AgentSelfStats>(`/agents/${agentId}/self/stats`),
    snapshot: (agentId: string) =>
      request<{ id: string; timestamp: string; trait_count: number; pattern_count: number; dominant_categories: string[]; evolution_step: number }>(`/agents/${agentId}/self/snapshot`, { method: 'POST' }),
    observe: (agentId: string, userMessage: string, agentResponse?: string, topic?: string, sentiment?: string, complexity?: string) => {
      const qs = new URLSearchParams({ user_message: userMessage, agent_response: agentResponse || '', topic: topic || '', sentiment: sentiment || '', complexity: complexity || '' });
      return request<{ agent_id: string; observed: boolean }>(`/agents/${agentId}/self/observe?${qs.toString()}`, { method: 'POST' });
    },
    export: (agentId: string) =>
      request<any>(`/agents/${agentId}/self/export`),
    import: (agentId: string, data: Record<string, unknown>) =>
      request<any>(`/agents/${agentId}/self/import`, { method: 'POST', body: JSON.stringify(data) }),
    registry: () =>
      request<{ agents: string[] }>('/agent-self/registry'),
  },

  // ── Plugin System ──
  plugins: {
    list: (status?: string) => {
      const qs = status ? `?status=${status}` : '';
      return request<{ plugins: Array<import('../types').PluginInfo> }>(`/plugins${qs}`);
    },
    stats: () =>
      request<import('../types').PluginStats>('/plugins/stats'),
    register: (data: { id: string; name: string; version?: string; description?: string; author?: string; homepage?: string; permissions?: string[]; capabilities?: string[]; entry_point?: string; tags?: string[] }) =>
      request<{ id: string; status: string }>('/plugins/register', { method: 'POST', body: JSON.stringify(data) }),
    install: (pluginId: string) =>
      request<{ plugin_id: string; installed: boolean }>(`/plugins/${pluginId}/install`, { method: 'POST' }),
    activate: (pluginId: string) =>
      request<{ plugin_id: string; activated: boolean }>(`/plugins/${pluginId}/activate`, { method: 'POST' }),
    deactivate: (pluginId: string) =>
      request<{ plugin_id: string; deactivated: boolean }>(`/plugins/${pluginId}/deactivate`, { method: 'POST' }),
    uninstall: (pluginId: string) =>
      request<{ plugin_id: string; uninstalled: boolean }>(`/plugins/${pluginId}`, { method: 'DELETE' }),
  },

  // ── IM Hub ──
  imHub: {
    stats: () =>
      request<import('../types').IMHubStats>('/im/stats'),
    platforms: () =>
      request<{ platforms: Array<import('../types').IMPlatformStatus> }>('/im/platforms'),
    messages: (platform?: string, limit?: number) => {
      const qs = new URLSearchParams();
      if (platform) qs.set('platform', platform);
      if (limit) qs.set('limit', String(limit));
      return request<{ messages: any[] }>(`/im/messages?${qs.toString()}`);
    },
    configure: (data: { platform: string; enabled?: boolean; bot_token?: string; app_id?: string; app_secret?: string; webhook_url?: string; allowed_chat_ids?: string[]; auto_reply?: boolean }) =>
      request<{ platform: string; configured: boolean }>('/im/platforms/configure', { method: 'POST', body: JSON.stringify(data) }),
    connect: (platform: string) =>
      request<{ platform: string; connected: boolean }>(`/im/platforms/${platform}/connect`, { method: 'POST' }),
    disconnect: (platform: string) =>
      request<{ platform: string; disconnected: boolean }>(`/im/platforms/${platform}/disconnect`, { method: 'POST' }),
    send: (platform: string, chatId: string, text: string) => {
      const qs = new URLSearchParams({ platform, chat_id: chatId, text });
      return request<{ sent: boolean }>(`/im/send?${qs.toString()}`, { method: 'POST' });
    },
    assignAgent: (chatId: string, agentId: string) => {
      const qs = new URLSearchParams({ chat_id: chatId, agent_id: agentId });
      return request<{ chat_id: string; agent_id: string; assigned: boolean }>(`/im/chats/assign?${qs.toString()}`, { method: 'POST' });
    },
  },

  // ── Skills Marketplace ──
  marketplace: {
    stats: () =>
      request<import('../types').MarketplaceStats>('/marketplace/stats'),
    search: (query?: string, category?: string, tags?: string, pricing?: string, sortBy?: string, page?: number, pageSize?: number) => {
      const qs = new URLSearchParams();
      if (query) qs.set('query', query);
      if (category) qs.set('category', category);
      if (tags) qs.set('tags', tags);
      if (pricing) qs.set('pricing', pricing);
      if (sortBy) qs.set('sort_by', sortBy);
      if (page) qs.set('page', String(page));
      if (pageSize) qs.set('page_size', String(pageSize));
      return request<{ skills: Array<import('../types').MarketplaceSkillInfo>; total: number; page: number; page_size: number }>(`/marketplace/skills?${qs.toString()}`);
    },
    featured: () =>
      request<{ skills: Array<import('../types').MarketplaceSkillInfo> }>('/marketplace/skills/featured'),
    get: (skillId: string) =>
      request<import('../types').MarketplaceSkillInfo>(`/marketplace/skills/${skillId}`),
    publish: (data: { name: string; description?: string; category?: string; version?: string; author?: string; author_id?: string; tags?: string[]; dependencies?: string[]; prompt_template?: string; tool_requirements?: string[] }) =>
      request<import('../types').MarketplaceSkillInfo>('/marketplace/skills/publish', { method: 'POST', body: JSON.stringify(data) }),
    review: (skillId: string, data: { reviewer_id?: string; reviewer_name?: string; rating: number; title?: string; content?: string }) =>
      request<{ id: string; rating: number; created_at: string }>(`/marketplace/skills/${skillId}/review`, { method: 'POST', body: JSON.stringify(data) }),
    reviews: (skillId: string, page?: number, pageSize?: number) => {
      const qs = new URLSearchParams();
      if (page) qs.set('page', String(page));
      if (pageSize) qs.set('page_size', String(pageSize));
      return request<{ reviews: Array<import('../types').SkillReview>; total: number }>(`/marketplace/skills/${skillId}/reviews?${qs.toString()}`);
    },
    publisher: (publisherId: string) =>
      request<any>(`/marketplace/publishers/${publisherId}`),
    categories: () =>
      request<{ categories: Array<{ category: string; count: number }> }>('/marketplace/categories'),
    download: (skillId: string) =>
      request<{ skill_id: string; recorded: boolean }>(`/marketplace/skills/${skillId}/download`, { method: 'POST' }),
  },

  // ── Task Queue ──
  taskQueue: {
    stats: () =>
      request<import('../types').TaskQueueStats>('/queue/stats'),
    listJobs: (params?: { status?: string; job_type?: string; priority?: string; agent_id?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set('status', params.status);
      if (params?.job_type) qs.set('job_type', params.job_type);
      if (params?.priority) qs.set('priority', params.priority);
      if (params?.agent_id) qs.set('agent_id', params.agent_id);
      if (params?.limit) qs.set('limit', String(params.limit));
      return request<{ jobs: Array<import('../types').QueuedJob> }>(`/queue/jobs?${qs.toString()}`);
    },
    getJob: (jobId: string) =>
      request<import('../types').QueuedJob>(`/queue/jobs/${jobId}`),
    submit: (data: { name: string; job_type?: string; payload?: Record<string, unknown>; priority?: string; agent_id?: string; max_retries?: number; timeout_seconds?: number; tags?: string[] }) =>
      request<import('../types').QueuedJob>('/queue/jobs/submit', { method: 'POST', body: JSON.stringify(data) }),
    submitBatch: (data: { name: string; jobs?: Array<{ name: string; job_type: string; payload?: Record<string, unknown> }>; priority?: string; agent_id?: string }) =>
      request<import('../types').BatchJobInfo>('/queue/jobs/batch', { method: 'POST', body: JSON.stringify(data) }),
    listBatches: (limit?: number) => {
      const qs = limit ? `?limit=${limit}` : '';
      return request<{ batches: Array<import('../types').BatchJobInfo> }>(`/queue/batches${qs}`);
    },
    getBatch: (batchId: string) =>
      request<import('../types').BatchJobInfo>(`/queue/batches/${batchId}`),
    cancelJob: (jobId: string) =>
      request<{ job_id: string; cancelled: boolean }>(`/queue/jobs/${jobId}/cancel`, { method: 'POST' }),
    updateProgress: (jobId: string, progress: number, message?: string) => {
      const qs = new URLSearchParams();
      qs.set('progress', String(progress));
      if (message) qs.set('message', message);
      return request<{ job_id: string; progress: number; updated: boolean }>(`/queue/jobs/${jobId}/progress?${qs.toString()}`, { method: 'PUT' });
    },
  },

  // ── Runtime Backend ──
  runtimeBackend: {
    stats: () =>
      request<import('../types').RuntimeBackendStats>('/runtime-backend/stats'),
    backends: () =>
      request<{ backends: Array<import('../types').RuntimeBackendInfo> }>('/runtime-backend/backends'),
    instances: (agentId?: string) => {
      const qs = agentId ? `?agent_id=${agentId}` : '';
      return request<{ instances: Array<import('../types').RuntimeInstanceInfo> }>(`/runtime-backend/instances${qs}`);
    },
    getInstance: (instanceId: string) =>
      request<import('../types').RuntimeInstanceInfo>(`/runtime-backend/instances/${instanceId}`),
    create: (data: { agent_id?: string; backend?: string; workspace_dir?: string; environment_vars?: Record<string, string>; installed_packages?: string[]; max_memory_mb?: number; max_cpu_cores?: number; timeout_seconds?: number }) =>
      request<{ id: string; backend: string; status: string; agent_id: string }>('/runtime-backend/instances/create', { method: 'POST', body: JSON.stringify(data) }),
    execute: (instanceId: string, data: { agent_config?: Record<string, unknown>; input_data?: Record<string, unknown> }) =>
      request<any>(`/runtime-backend/instances/${instanceId}/execute`, { method: 'POST', body: JSON.stringify(data) }),
    metrics: (instanceId: string) =>
      request<any>(`/runtime-backend/instances/${instanceId}/metrics`),
    terminate: (instanceId: string) =>
      request<{ instance_id: string; terminated: boolean }>(`/runtime-backend/instances/${instanceId}`, { method: 'DELETE' }),
  },

  // ── Agent Core ──
  agentCore: {
    stats: (agentId = 'default') =>
      request<import('../types').AgentCoreStats>(`/agent-core/stats?agent_id=${agentId}`),
    traces: (agentId = 'default', limit = 10) =>
      request<{ traces: Array<import('../types').CoreExecutionTrace> }>(`/agent-core/traces?agent_id=${agentId}&limit=${limit}`),
    insights: (agentId = 'default', limit = 20) =>
      request<{ insights: Array<import('../types').CoreInsight> }>(`/agent-core/insights?agent_id=${agentId}&limit=${limit}`),
    generateInsights: (agentId = 'default') =>
      request<{ generated: number; insights: Array<import('../types').CoreInsight> }>(`/agent-core/generate-insights?agent_id=${agentId}`, { method: 'POST' }),
    proactiveSignals: (agentId = 'default', limit = 10) =>
      request<{ signals: Array<import('../types').ProactiveSignal> }>(`/agent-core/proactive-signals?agent_id=${agentId}&limit=${limit}`),
    analyze: (prompt: string, agentId = 'default') =>
      request<import('../types').CoreAnalysis>(`/agent-core/analyze?prompt=${encodeURIComponent(prompt)}&agent_id=${agentId}`, { method: 'POST' }),
    planSequence: (task: string, agentId = 'default') =>
      request<{ sequence: string[][] }>(`/agent-core/plan-sequence?task=${encodeURIComponent(task)}&agent_id=${agentId}`, { method: 'POST' }),
    learn: (agentId: string, prompt: string, success: boolean, toolsUsed?: string) => {
      const qs = `agent_id=${agentId}&prompt=${encodeURIComponent(prompt)}&success=${success}${toolsUsed ? `&tools_used=${toolsUsed}` : ''}`;
      return request<{ agent_id: string; recorded: boolean }>(`/agent-core/learn?${qs}`, { method: 'POST' });
    },
    checkpoint: (agentId = 'default', name = 'manual') =>
      request<{ checkpoint_id: string; agent_id: string }>(`/agent-core/checkpoint?agent_id=${agentId}&name=${name}`, { method: 'POST' }),
    // Pipeline Runner
    runPipeline: (agentId: string, prompt: string) =>
      request<import('../types').PipelineRun>(`/agent-core/pipeline?agent_id=${agentId}&prompt=${encodeURIComponent(prompt)}`, { method: 'POST' }),
    crossTrace: (agentId: string, limit?: number) =>
      request<{ traces: Array<import('../types').ExecutionTimelineEntry> }>(`/agent-core/cross-trace?agent_id=${agentId}&limit=${limit || 20}`),
    reflect: (agentId: string) =>
      request<{ reflections: string[]; confidence: number }>(`/agent-core/reflect?agent_id=${agentId}`, { method: 'POST' }),
    strategyEffectiveness: (agentId: string) =>
      request<{ strategies: Array<import('../types').StrategyEffectiveness> }>(`/agent-core/strategy-effectiveness?agent_id=${agentId}`),
    timeline: (agentId: string, limit?: number) =>
      request<{ entries: Array<import('../types').ExecutionTimelineEntry> }>(`/agent-core/timeline?agent_id=${agentId}&limit=${limit || 15}`),
  },

  // ── Agent Synthesis ──
  synthesis: {
    stats: () =>
      request<import('../types').SynthesisStats>('/synthesis/stats'),
    reports: (limit = 5) =>
      request<{ reports: Array<import('../types').SynthesisReport> }>(`/synthesis/reports?limit=${limit}`),
    contribute: (agentId: string, agentName: string, content: string, insightType = 'strategy', confidence = 0.5) =>
      request<import('../types').SynthesisContribution>(`/synthesis/contribute?agent_id=${agentId}&agent_name=${agentName}&content=${encodeURIComponent(content)}&insight_type=${insightType}&confidence=${confidence}`, { method: 'POST' }),
    synthesize: (mode = 'aggregate') =>
      request<import('../types').SynthesisResult>(`/synthesis/synthesize?mode=${mode}`, { method: 'POST' }),
    recommendations: (agentId: string) =>
      request<{ recommendations: Array<import('../types').AgentRecommendation> }>(`/synthesis/recommendations/${agentId}`),
    conflicts: (limit = 20) =>
      request<{ conflicts: Array<import('../types').KnowledgeConflict> }>(`/synthesis/conflicts?limit=${limit}`),
    // Knowledge Fusion
    fuse: (agentIds: string[], topic?: string) => {
      const qs = new URLSearchParams();
      qs.set('agent_ids', agentIds.join(','));
      if (topic) qs.set('topic', topic);
      return request<import('../types').FusionResult>(`/synthesis/fuse?${qs.toString()}`, { method: 'POST' });
    },
    trustNetwork: () =>
      request<import('../types').TrustNetwork>('/synthesis/trust-network'),
    decide: (topic: string, options: string[], agentIds?: string[]) => {
      const qs = new URLSearchParams();
      qs.set('topic', topic);
      qs.set('options', options.join(','));
      if (agentIds) qs.set('agent_ids', agentIds.join(','));
      return request<import('../types').CollectiveDecision>(`/synthesis/decide?${qs.toString()}`, { method: 'POST' });
    },
    resolvedConflicts: (limit = 20) =>
      request<{ conflicts: Array<import('../types').ResolvedConflict> }>(`/synthesis/resolved-conflicts?limit=${limit}`),
    distill: (topic?: string, limit?: number) => {
      const qs = new URLSearchParams();
      if (topic) qs.set('topic', topic);
      if (limit) qs.set('limit', String(limit));
      return request<{ knowledge: Array<import('../types').DistilledKnowledge> }>(`/synthesis/distill?${qs.toString()}`);
    },
    collaborate: (query: string, agentIds: string[]) =>
      request<{ result: string; contributors: string[] }>(`/synthesis/collaborate?query=${encodeURIComponent(query)}&agent_ids=${agentIds.join(',')}`, { method: 'POST' }),
  },

  // ── Agent Intelligence ──
  intelligence: {
    stats: () =>
      request<import('../types').IntelligenceStats>('/intelligence/stats'),
    analyze: (prompt: string) =>
      request<import('../types').IntelligenceAnalysis>(`/intelligence/analyze?prompt=${encodeURIComponent(prompt)}`, { method: 'POST' }),
    insights: () =>
      request<import('../types').LearningInsights>('/intelligence/insights'),
    experiences: (limit = 10) =>
      request<{ experiences: Array<import('../types').Experience> }>(`/intelligence/experiences?limit=${limit}`),
    planTools: (task: string) =>
      request<{ sequence: string[][] }>(`/intelligence/plan-tools?task=${encodeURIComponent(task)}`, { method: 'POST' }),
    selectTools: (prompt: string, limit = 5) =>
      request<{ tools: Array<{ name: string; description: string }> }>(`/intelligence/select-tools?prompt=${encodeURIComponent(prompt)}&limit=${limit}`, { method: 'POST' }),
    strategyDispatch: () =>
      request<{ strategies: Array<import('../types').StrategyDispatch> }>('/intelligence/strategy-dispatch'),
    toolEffectiveness: () =>
      request<{ tools: Array<import('../types').ToolEffectiveness> }>('/intelligence/tool-effectiveness'),
    lessonsLearned: (limit = 20) =>
      request<{ lessons: Array<import('../types').LessonLearned> }>(`/intelligence/lessons?limit=${limit}`),
    uncertaintyGauge: (responseId: string) =>
      request<import('../types').UncertaintyGaugeData>(`/intelligence/uncertainty?response_id=${responseId}`),
    promptAnalyzer: (prompt: string) =>
      request<import('../types').PromptAnalysis>(`/intelligence/prompt-analyzer?prompt=${encodeURIComponent(prompt)}`, { method: 'POST' }),
  },

  // ── Runtime ──
  runtime: {
    registry: () =>
      request<{ runtimes: Array<import('../types').RuntimeInfo>; active_count: number; total_executions: number }>('/runtime/registry'),
    stats: (agentId: string) =>
      request<import('../types').RuntimeStats>(`/runtime/${agentId}/stats`),
    executions: (agentId: string, limit = 10) =>
      request<{ executions: Array<import('../types').RuntimeExecution> }>(`/runtime/${agentId}/executions?limit=${limit}`),
    checkpoints: (agentId: string) =>
      request<{ checkpoints: Array<{ id: string; name: string; timestamp: string }> }>(`/runtime/${agentId}/checkpoints`),
    saveCheckpoint: (agentId: string, name = 'manual') =>
      request<{ checkpoint_id: string; agent_id: string; saved: boolean }>(`/runtime/${agentId}/checkpoint?name=${name}`, { method: 'POST' }),
    pause: (agentId: string) =>
      request<{ agent_id: string; state: string }>(`/runtime/${agentId}/pause`, { method: 'POST' }),
    resume: (agentId: string) =>
      request<{ agent_id: string; state: string }>(`/runtime/${agentId}/resume`, { method: 'POST' }),
    refillTokens: (agentId: string, count = 10000) =>
      request<{ agent_id: string; token_budget_remaining: number }>(`/runtime/${agentId}/refill-tokens?count=${count}`, { method: 'POST' }),
    shutdown: (agentId: string) =>
      request<{ agent_id: string; shutdown: boolean }>(`/runtime/${agentId}/shutdown`, { method: 'POST' }),
    events: (agentId: string, limit = 20) =>
      request<{ events: Array<{ id: string; type: string; data: any; timestamp: string }>; agent_id: string }>(`/runtime/${agentId}/events?limit=${limit}`),
    intelligence: (agentId: string) =>
      request<import('../types').IntelligenceStats>(`/runtime/${agentId}/intelligence`),
    agentCore: (agentId: string) =>
      request<import('../types').AgentCoreStats>(`/runtime/${agentId}/agent-core`),
    dashboard: () =>
      request<import('../types').SystemDashboard>('/system/dashboard'),
    health: () =>
      request<import('../types').SystemHealth>('/system/health'),
  },

  // ── Skill Compiler ──
  skillCompiler: {
    listSkills: (category?: string, status?: string) => {
      let qs = '';
      if (category) qs += `&category=${category}`;
      if (status) qs += `&status=${status}`;
      return request<{ skills: Array<import('../types').CompiledSkillInfo> }>(`/skill-compiler/skills?${qs.replace(/^&/, '')}`);
    },
    listPipelines: () =>
      request<{ pipelines: Array<import('../types').PipelineInfo> }>('/skill-compiler/pipelines'),
    stats: () =>
      request<import('../types').SkillCompilerStats>('/skill-compiler/stats'),
    search: (query: string) =>
      request<{ skills: Array<import('../types').CompiledSkillInfo> }>(`/skill-compiler/search?query=${encodeURIComponent(query)}`),
    activate: (skillId: string) =>
      request<{ success: boolean }>(`/skill-compiler/skills/${skillId}/activate`, { method: 'POST' }),
    improve: (skillId: string) =>
      request<{ improved: boolean; skill: import('../types').CompiledSkillInfo }>(`/skill-compiler/skills/${skillId}/improve`, { method: 'POST' }),
    createPipeline: (name: string, skillIds: string[]) =>
      request<{ created: boolean; pipeline: import('../types').PipelineInfo }>(`/skill-compiler/pipelines?name=${encodeURIComponent(name)}&skill_ids=${skillIds.join(',')}`, { method: 'POST' }),
  },

  // ── Conversation Search ──
  conversationSearch: {
    list: (limit = 20) =>
      request<{ conversations: Array<import('../types').ConversationInfo> }>(`/conversation-search/list?limit=${limit}`),
    search: (query: string, limit = 10) =>
      request<{ results: Array<import('../types').SearchResultItem> }>(`/conversation-search/search?query=${encodeURIComponent(query)}&limit=${limit}`),
    searchByTopic: (topic: string, limit = 10) =>
      request<{ results: Array<import('../types').SearchResultItem> }>(`/conversation-search/search-by-topic?topic=${encodeURIComponent(topic)}&limit=${limit}`),
    recap: (query: string, daysBack = 30) =>
      request<import('../types').RecapResult>(`/conversation-search/recap?query=${encodeURIComponent(query)}&days_back=${daysBack}`),
    timeline: (daysBack = 30) =>
      request<{ timeline: Array<import('../types').TimelineEntry> }>(`/conversation-search/timeline?days_back=${daysBack}`),
    stats: () =>
      request<import('../types').ConversationSearchStats>('/conversation-search/stats'),
  },

  // ── MCP Bridge ──
  mcpBridge: {
    stats: () =>
      request<any>('/mcp-bridge/stats'),
    tools: (serverName?: string) =>
      request<{ tools: Array<{ name: string; description: string; server_name: string; input_schema: any }> }>(`/mcp-bridge/tools${serverName ? `?server_name=${serverName}` : ''}`),
    registerServer: (config: { name: string; transport: string; command?: string; args?: string[]; url?: string }) =>
      request<{ server_name: string; registered: boolean }>('/mcp-bridge/servers', { method: 'POST', body: JSON.stringify(config) }),
    connect: (serverName: string) =>
      request<{ server_name: string; connected: boolean }>(`/mcp-bridge/servers/${serverName}/connect`, { method: 'POST' }),
    disconnect: (serverName: string) =>
      request<{ server_name: string; disconnected: boolean }>(`/mcp-bridge/servers/${serverName}/disconnect`, { method: 'POST' }),
  },

  // ── Learning Orchestrator ──
  learningOrchestrator: {
    stats: () =>
      request<any>('/learning/stats'),
    insights: (category?: string, limit = 20) =>
      request<{ insights: Array<{ id: string; category: string; summary: string; confidence: number; impact_score: number; applied_count: number; success_rate_after: number; created_at: string }> }>(`/learning/insights?${category ? `category=${category}&` : ''}limit=${limit}`),
    strategies: (limit = 10) =>
      request<{ strategies: Array<{ id: string; task_pattern: string; preferred_style: string; preferred_model: string; preferred_mode: string; success_rate: number; total_attempts: number; avg_tokens: number; avg_latency_ms: number }> }>(`/learning/strategies?limit=${limit}`),
    consolidate: () =>
      request<any>('/learning/consolidate', { method: 'POST' }),
    bestStrategy: (prompt: string) =>
      request<{ found: boolean; strategy?: any; message?: string }>(`/learning/best-strategy?prompt=${encodeURIComponent(prompt)}`),
  },

  // ── Agent Persona (New) ──
  agentPersona: {
    list: (role?: string) =>
      request<{ personas: import('../types').AgentPersonaProfile[] }>(`/persona/list${role ? `?role=${role}` : ''}`),
    getActive: () =>
      request<import('../types').AgentPersonaProfile>('/persona/active'),
    activate: (personaId: string) =>
      request<{ success: boolean; active: import('../types').AgentPersonaProfile | null }>('/persona/activate', { method: 'POST', body: JSON.stringify({ persona_id: personaId }) }),
    match: (task: string) =>
      request<import('../types').AgentPersonaProfile>(`/persona/match?task=${encodeURIComponent(task)}`),
    create: (data: { name: string; description: string; traits: Record<string, number>; style?: string; decision?: string; role?: string }) =>
      request<import('../types').AgentPersonaProfile>('/persona/create', { method: 'POST', body: JSON.stringify(data) }),
    stats: () =>
      request<import('../types').PersonaStats>('/persona/stats'),
  },

  // ── Agent Governance ──
  governance: {
    stats: () =>
      request<import('../types').GovernanceStats>('/governance/stats'),
    approvals: (agentId?: string) => {
      const qs = agentId ? `?agent_id=${agentId}` : '';
      return request<{ approvals: import('../types').ApprovalRequest[] }>(`/governance/approvals${qs}`);
    },
    approve: (requestId: string) =>
      request<{ success: boolean; approval: import('../types').ApprovalRequest }>(`/governance/approvals/${requestId}/approve`, { method: 'POST' }),
    deny: (requestId: string) =>
      request<{ success: boolean; approval: import('../types').ApprovalRequest }>(`/governance/approvals/${requestId}/deny`, { method: 'POST' }),
    createPolicy: (data: {
      name: string; description?: string; category?: string; level?: string; action?: string;
      tool_patterns?: string[]; file_patterns?: string[]; domain_patterns?: string[];
      max_tokens_per_call?: number; max_tokens_per_session?: number;
      max_cost_per_session?: number; max_tool_calls_per_session?: number;
      require_approval_above_cost?: number; priority?: number;
    }) =>
      request<{ rule_id: string; name: string }>('/governance/policies', { method: 'POST', body: JSON.stringify(data) }),
    evaluate: (data: { context: Record<string, unknown>; agent_id?: string; session_id?: string }) =>
      request<import('../types').GovernanceEvaluation>('/governance/evaluate', { method: 'POST', body: JSON.stringify(data) }),
    budget: (agentId: string) =>
      request<import('../types').BudgetStatus>(`/governance/budget/${agentId}`),
    audit: (limit = 50) =>
      request<{ audit_log: Array<Record<string, unknown>> }>(`/governance/audit?limit=${limit}`),
  },

  // ── Smart Router ──
  smartRouter: {
    stats: () =>
      request<import('../types').SmartRouterStats>('/smart-router/stats'),
    select: (data: { prompt: string; provider?: string; require_tools?: boolean }) =>
      request<import('../types').RoutingDecision>('/smart-router/select', { method: 'POST', body: JSON.stringify(data) }),
    analyze: (prompt: string) =>
      request<import('../types').ComplexityAnalysis>('/smart-router/analyze', { method: 'POST', body: JSON.stringify({ prompt }) }),
    costSavings: () =>
      request<{ total_savings: number; per_model: Record<string, number>; total_routing_decisions: number }>('/smart-router/cost-savings'),
    registerModel: (data: { provider: string; model_name: string; tier: string; cost_per_1k_tokens?: number; max_tokens?: number; supports_tools?: boolean; supports_vision?: boolean; latency_ms?: number }) =>
      request<{ registered: boolean }>('/smart-router/register-model', { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── Identity Core ──
  identityCore: {
    stats: () =>
      request<import('../types').IdentityRegistryStats>('/identity-core/stats'),
    profile: (agentId: string) =>
      request<import('../types').IdentityCoreProfile>(`/identity-core/${agentId}/profile`),
    recordExperience: (agentId: string, data: { content: string; context?: Record<string, unknown>; importance?: number; emotional_valence?: number; agent_name?: string }) =>
      request<{ entry: import('../types').EpisodicEntry; traits_updated: boolean }>(`/identity-core/${agentId}/experience`, { method: 'POST', body: JSON.stringify(data) }),
    episodic: (agentId: string, keyword?: string, limit?: number) => {
      const qs = new URLSearchParams();
      if (keyword) qs.set('keyword', keyword);
      if (limit) qs.set('limit', String(limit));
      return request<{ entries: import('../types').EpisodicEntry[] }>(`/identity-core/${agentId}/episodic?${qs.toString()}`);
    },
    semantic: (agentId: string, concept?: string) => {
      const qs = concept ? `?concept=${encodeURIComponent(concept)}` : '';
      return request<{ nodes: import('../types').SemanticNode[] }>(`/identity-core/${agentId}/semantic${qs}`);
    },
    learnPattern: (agentId: string, data: { pattern_type: string; trigger_conditions: string[]; action_sequence: string[] }) =>
      request<import('../types').ProceduralPattern>(`/identity-core/${agentId}/pattern`, { method: 'POST', body: JSON.stringify(data) }),
    updateTrait: (agentId: string, data: { name: string; delta: number; confidence_delta?: number }) =>
      request<{ updated: boolean }>(`/identity-core/${agentId}/trait`, { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── WorkSpace Manager (New) ──
  workspaceManager: {
    stats: () =>
      request<import('../types').WorkSpaceManagerStats>('/workspace-manager/stats'),
    list: () =>
      request<{ workspaces: Array<import('../types').WorkSpaceManagerStats['workspaces'][0]> }>('/workspace-manager/list'),
    create: (data: { name: string; description?: string; isolate_files?: boolean; isolate_memory?: boolean; isolate_skills?: boolean; tags?: string[] }) =>
      request<{ workspace: import('../types').WorkSpaceManagerConfig }>('/workspace-manager/create', { method: 'POST', body: JSON.stringify(data) }),
    activate: (wsId: string) =>
      request<{ success: boolean }>('/workspace-manager/activate', { method: 'POST', body: JSON.stringify({ workspace_id: wsId }) }),
    delete: (wsId: string) =>
      request<{ deleted: boolean }>('/workspace-manager/delete', { method: 'POST', body: JSON.stringify({ workspace_id: wsId }) }),
    get: (wsId: string) =>
      request<import('../types').WorkSpaceManagerConfig>(`/workspace-manager/${wsId}`),
    writeFile: (wsId: string, path: string, content: string) =>
      request<{ success: boolean; path: string; size: number }>(`/workspace-manager/${wsId}/file`, { method: 'POST', body: JSON.stringify({ path, content }) }),
    readFile: (wsId: string, path: string) =>
      request<{ success: boolean; path: string; content: string }>(`/workspace-manager/${wsId}/file/read`, { method: 'POST', body: JSON.stringify({ path }) }),
    listFiles: (wsId: string, prefix?: string) => {
      const qs = prefix ? `?prefix=${encodeURIComponent(prefix)}` : '';
      return request<{ files: Array<{ path: string; size: number; modified_at: string }> }>(`/workspace-manager/${wsId}/files${qs}`);
    },
    addMemory: (wsId: string, key: string, value: unknown, tags?: string[]) =>
      request<{ success: boolean; key: string }>(`/workspace-manager/${wsId}/memory`, { method: 'POST', body: JSON.stringify({ key, value, tags }) }),
    listMemories: (wsId: string, tag?: string) => {
      const qs = tag ? `?tag=${encodeURIComponent(tag)}` : '';
      return request<{ memories: Array<Record<string, unknown>> }>(`/workspace-manager/${wsId}/memories${qs}`);
    },
    addSkill: (wsId: string, name: string, definition: Record<string, unknown>) =>
      request<{ success: boolean; name: string }>(`/workspace-manager/${wsId}/skill`, { method: 'POST', body: JSON.stringify({ name, definition }) }),
    snapshot: (wsId: string, description?: string) =>
      request<import('../types').WorkSpaceManagerSnapshot>(`/workspace-manager/${wsId}/snapshot`, { method: 'POST', body: JSON.stringify({ description }) }),
    wsStats: (wsId: string) =>
      request<Record<string, unknown>>(`/workspace-manager/${wsId}/stats`),
  },

  // ── Agent Mesh (New) ──
  agentMesh: {
    status: () =>
      request<import('../types').MeshStatus>('/mesh/status'),
    nodes: () =>
      request<{ nodes: import('../types').MeshNodeStatus[]; total: number }>('/mesh/nodes'),
    getNode: (agentId: string) =>
      request<import('../types').MeshNodeStatus>(`/mesh/nodes/${agentId}`),
    registerNode: (data: { agent_id: string; agent_name: string; role?: string; capabilities?: string[]; max_concurrent_tasks?: number; tags?: string[] }) =>
      request<import('../types').MeshNodeStatus>('/mesh/nodes/register', { method: 'POST', body: JSON.stringify(data) }),
    pauseNode: (agentId: string) =>
      request<{ status: string; agent_id: string }>(`/mesh/nodes/${agentId}/pause`, { method: 'POST' }),
    resumeNode: (agentId: string) =>
      request<{ status: string; agent_id: string }>(`/mesh/nodes/${agentId}/resume`, { method: 'POST' }),
    submitTask: (data: { title: string; description?: string; priority?: string; target_agent_id?: string; context?: Record<string, unknown> }) =>
      request<{ task_id: string; status: string }>('/mesh/tasks/submit', { method: 'POST', body: JSON.stringify(data) }),
    processTasks: () =>
      request<{ processed: number; results: Array<{ task_id: string; assigned_to: string; status: string }> }>('/mesh/tasks/process', { method: 'POST' }),
    pendingTasks: () =>
      request<{ pending: number; tasks: import('../types').MeshTask[] }>('/mesh/tasks/pending'),
    delegate: (fromAgentId: string, toAgentId: string, data: { title: string; description?: string; priority?: string; context?: Record<string, unknown> }) =>
      request<{ delegated: boolean; task_id: string }>('/mesh/delegate', { method: 'POST', body: JSON.stringify({ from_agent_id: fromAgentId, to_agent_id: toAgentId, ...data }) }),
    setStrategy: (strategy: string) =>
      request<{ strategy: string }>('/mesh/strategy', { method: 'PUT', body: JSON.stringify({ strategy }) }),
    events: (limit = 50) =>
      request<{ events: import('../types').MeshEvent[]; total: number }>(`/mesh/events?limit=${limit}`),
  },

  // ── Learning Loop (New) ──
  learningLoop: {
    status: () =>
      request<import('../types').LearningLoopStatus>('/learning/status'),
    observe: (data: { observation_type: string; agent_id: string; session_id?: string; content?: Record<string, unknown>; outcome?: string; metadata?: Record<string, unknown> }) =>
      request<{ observation_id: string; observation_type: string; recorded: boolean }>('/learning/observe', { method: 'POST', body: JSON.stringify(data) }),
    extract: (agentId?: string, sessionId?: string) =>
      request<{ patterns: import('../types').LearningPattern[]; total: number }>('/learning/extract', { method: 'POST', body: JSON.stringify({ agent_id: agentId, session_id: sessionId }) }),
    compound: (agentId: string) =>
      request<{ skill_id: string; name: string; confidence: number; steps: number } | { error: string }>('/learning/compound', { method: 'POST', body: JSON.stringify({ agent_id: agentId }) }),
    evolve: (agentId: string) =>
      request<{ improvements: Array<Record<string, unknown>>; agent_id: string }>('/learning/evolve', { method: 'POST', body: JSON.stringify({ agent_id: agentId }) }),
    nudges: () =>
      request<{ nudges: import('../types').LearningNudge[]; total: number }>('/learning/nudges'),
    dismissNudge: (nudgeId: string) =>
      request<{ dismissed: boolean; nudge_id: string }>(`/learning/nudges/${nudgeId}/dismiss`, { method: 'POST' }),
    actOnNudge: (nudgeId: string) =>
      request<{ acted_upon: boolean; nudge_id: string }>(`/learning/nudges/${nudgeId}/act`, { method: 'POST' }),
    runCycle: (agentId: string, sessionId?: string) =>
      request<Record<string, unknown>>('/learning/cycle', { method: 'POST', body: JSON.stringify({ agent_id: agentId, session_id: sessionId }) }),
    skills: (tag?: string) => {
      const qs = tag ? `?tag=${encodeURIComponent(tag)}` : '';
      return request<{ skills: import('../types').LearningSkill[]; total: number }>(`/learning/skills${qs}`);
    },
    patterns: (patternType?: string, minConfidence?: number) => {
      const params = new URLSearchParams();
      if (patternType) params.set('pattern_type', patternType);
      if (minConfidence !== undefined) params.set('min_confidence', String(minConfidence));
      const qs = params.toString();
      return request<{ patterns: import('../types').LearningPattern[]; total: number }>(`/learning/patterns${qs ? '?' + qs : ''}`);
    },
  },

  // ── Experiment Tracker ──
  experiments: {
    stats: () => request<any>('/experiments/stats'),
    list: () => request<{ experiments: any[] }>('/experiments'),
    get: (id: string) => request<any>(`/experiments/${id}`),
    create: (data: { name: string; description?: string; experiment_type?: string; control_config?: Record<string, unknown>; treatment_config?: Record<string, unknown>; metrics?: any[] }) =>
      request<any>('/experiments/create', { method: 'POST', body: JSON.stringify(data) }),
    start: (id: string) => request<any>(`/experiments/${id}/start`, { method: 'POST' }),
    pause: (id: string) => request<any>(`/experiments/${id}/pause`, { method: 'POST' }),
    complete: (id: string) => request<any>(`/experiments/${id}/complete`, { method: 'POST' }),
    recordTrial: (experimentId: string, data: { variant_id: string; metrics?: Record<string, unknown>; context?: Record<string, unknown>; success?: boolean; error_message?: string }) =>
      request<any>(`/experiments/${experimentId}/trials`, { method: 'POST', body: JSON.stringify(data) }),
    analysis: (id: string) => request<any>(`/experiments/${id}/analysis`),
    createPromptAB: (data: { name: string; description?: string; control_prompt: string; treatment_prompt: string; task_description?: string }) =>
      request<any>('/experiments/prompt-ab', { method: 'POST', body: JSON.stringify(data) }),
    createConfigAB: (data: { name: string; description?: string; control_config: Record<string, unknown>; treatment_config: Record<string, unknown> }) =>
      request<any>('/experiments/config-ab', { method: 'POST', body: JSON.stringify(data) }),
  },

  brain: {
    stats: () => request<any>('/brain/stats'),
    perceptions: () => request<any>('/brain/perceptions'),
    insights: () => request<any>('/brain/insights'),
    process: (data: { message: string; agent_id: string; agent_name?: string; mode?: string }) =>
      request<any>('/brain/process', { method: 'POST', body: JSON.stringify(data) }),
    processStream: (data: { message: string; agent_id: string; agent_name?: string; mode?: string }) =>
      fetch(`${BASE_URL}/brain/process/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
  },

  platform: {
    stats: () => request<any>('/platform/stats'),
    health: () => request<any>('/platform/health'),
    instances: () => request<any>('/platform/instances'),
    instanceDetails: (agentId: string) => request<any>(`/platform/instances/${agentId}`),
    sandboxes: (agentId?: string) => {
      const qs = agentId ? `?agent_id=${agentId}` : '';
      return request<any>(`/platform/sandboxes${qs}`);
    },
    alerts: (severity?: string, includeResolved?: boolean) => {
      const qs = new URLSearchParams();
      if (severity) qs.set('severity', severity);
      if (includeResolved) qs.set('include_resolved', 'true');
      return request<any>(`/platform/alerts?${qs.toString()}`);
    },
    acknowledgeAlert: (alertId: string) =>
      request<any>(`/platform/alerts/${alertId}/acknowledge`, { method: 'POST' }),
    resolveAlert: (alertId: string) =>
      request<any>(`/platform/alerts/${alertId}/resolve`, { method: 'POST' }),
    syncContext: (data: { source_agent_id: string; target_agent_ids: string[]; context_type: string; content: Record<string, unknown> }) =>
      request<any>('/platform/context/sync', { method: 'POST', body: JSON.stringify(data) }),
    syncEvents: (agentId?: string, contextType?: string) => {
      const qs = new URLSearchParams();
      if (agentId) qs.set('agent_id', agentId);
      if (contextType) qs.set('context_type', contextType);
      return request<any>(`/platform/context/events?${qs.toString()}`);
    },
  },

  coordinator: {
    stats: () => request<any>('/coordinator/stats'),
    status: () => request<any>('/coordinator/status'),
    initialize: () => request<any>('/coordinator/initialize', { method: 'POST' }),
    start: () => request<any>('/coordinator/start', { method: 'POST' }),
    pause: () => request<any>('/coordinator/pause', { method: 'POST' }),
    resume: () => request<any>('/coordinator/resume', { method: 'POST' }),
    stop: () => request<any>('/coordinator/stop', { method: 'POST' }),
    executions: (limit?: number) => {
      const qs = limit ? `?limit=${limit}` : '';
      return request<any>(`/coordinator/executions${qs}`);
    },
    agents: () => request<any>('/coordinator/agents'),
    execute: (data: { message: string; agent_id?: string; agent_name?: string; mode?: string; enable_reasoning?: boolean }) =>
      request<any>('/coordinator/execute', { method: 'POST', body: JSON.stringify(data) }),
    executeStream: (data: { message: string; agent_id?: string; agent_name?: string; mode?: string }) =>
      fetch(`${BASE_URL}/coordinator/execute/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    reset: () => request<any>('/coordinator/reset', { method: 'POST' }),
  },

  // ── Deep Reasoning ──
  reasoning: {
    adversarial: (agentId: string, data: { prompt: string; context?: string; num_counter_args?: number }) =>
      request<any>(`/agents/${agentId}/reasoning/adversarial`, { method: 'POST', body: JSON.stringify(data) }),
    causal: (agentId: string, data: { prompt: string; context?: string; max_chain_depth?: number }) =>
      request<any>(`/agents/${agentId}/reasoning/causal`, { method: 'POST', body: JSON.stringify(data) }),
    analogical: (agentId: string, data: { prompt: string; context?: string; domains?: string[]; num_analogies?: number }) =>
      request<any>(`/agents/${agentId}/reasoning/analogical`, { method: 'POST', body: JSON.stringify(data) }),
    synthesize: (agentId: string, data: { prompt: string; context?: string; strategies?: string[] }) =>
      request<any>(`/agents/${agentId}/reasoning/synthesize`, { method: 'POST', body: JSON.stringify(data) }),
    recommend: (agentId: string, data: { prompt: string; context?: string }) =>
      request<any>(`/agents/${agentId}/reasoning/recommend`, { method: 'POST', body: JSON.stringify(data) }),
    calibrate: (agentId: string, data: { result: any; past_accuracy_history?: number[] }) =>
      request<any>(`/agents/${agentId}/reasoning/calibrate`, { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── Self-Improvement ──
  improve: {
    compoundSkills: (agentId: string, data: { skill_ids: string[]; name: string; description?: string }) =>
      request<any>(`/agents/${agentId}/improve/compound-skills`, { method: 'POST', body: JSON.stringify(data) }),
    crossSkillSynthesize: (agentId: string, data: { category_a: string; category_b: string }) =>
      request<any>(`/agents/${agentId}/improve/cross-skill-synthesize`, { method: 'POST', body: JSON.stringify(data) }),
    benchmark: (agentId: string) =>
      request<any>(`/agents/${agentId}/improve/benchmark`, { method: 'POST' }),
    recommendSkill: (agentId: string, data: { task_description: string; top_k?: number }) =>
      request<any>(`/agents/${agentId}/improve/recommend-skill`, { method: 'POST', body: JSON.stringify(data) }),
    tuneThresholds: (agentId: string) =>
      request<any>(`/agents/${agentId}/improve/tune-thresholds`, { method: 'POST' }),
    trends: (agentId: string) =>
      request<any>(`/agents/${agentId}/improve/trends`, { method: 'POST' }),
  },

  // ── Session Management ──
  session: {
    delegate: (sessionId: string, data: { task_description: string; target_role?: string; priority?: string }) =>
      request<any>(`/sessions/${sessionId}/delegate`, { method: 'POST', body: JSON.stringify(data) }),
    vote: (sessionId: string, data: { action: string; topic?: string; options?: string[]; vote_id?: string; option?: string }) =>
      request<any>(`/sessions/${sessionId}/vote`, { method: 'POST', body: JSON.stringify(data) }),
    templates: () =>
      request<any>('/sessions/templates'),
    fromTemplate: (data: { template_name: string; orchestrator_id?: string }) =>
      request<any>('/sessions/from-template', { method: 'POST', body: JSON.stringify(data) }),
    summary: (sessionId: string) =>
      request<any>(`/sessions/${sessionId}/summary`),
    handoff: (sessionId: string, data: { from_agent_id: string; to_agent_id: string; context?: string }) =>
      request<any>(`/sessions/${sessionId}/handoff`, { method: 'POST', body: JSON.stringify(data) }),
    health: (sessionId: string) =>
      request<any>(`/sessions/${sessionId}/health`),
  },

  // ── Memory ──
  memory: {
    semanticSearch: (agentId: string, data: { query: string; similarity_threshold?: number; limit?: number }) =>
      request<any>(`/agents/${agentId}/memory/semantic-search`, { method: 'POST', body: JSON.stringify(data) }),
    detectConflicts: (agentId: string, data: { auto_flag?: boolean }) =>
      request<any>(`/agents/${agentId}/memory/detect-conflicts`, { method: 'POST', body: JSON.stringify(data) }),
    consolidate: (agentId: string, data: { similarity_threshold?: number; min_cluster_size?: number }) =>
      request<any>(`/agents/${agentId}/memory/consolidate`, { method: 'POST', body: JSON.stringify(data) }),
    decay: (agentId: string, data: { half_life_days?: number; min_importance?: number }) =>
      request<any>(`/agents/${agentId}/memory/decay`, { method: 'POST', body: JSON.stringify(data) }),
    graph: (agentId: string) =>
      request<any>(`/agents/${agentId}/memory/graph`),
    contextualRecall: (agentId: string, data: { context: string; limit?: number }) =>
      request<any>(`/agents/${agentId}/memory/contextual-recall`, { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── Experience ──
  experience: {
    trends: (agentId: string, data: { days?: number }) => {
      const qs = new URLSearchParams();
      if (data.days) qs.set('days', String(data.days));
      return request<any>(`/agents/${agentId}/experiences/trends?${qs.toString()}`);
    },
    predict: (agentId: string, data: { description: string; experience_type: string; tools_used?: string[]; top_k?: number }) =>
      request<any>(`/agents/${agentId}/experiences/predict`, { method: 'POST', body: JSON.stringify(data) }),
    recommend: (agentId: string, data: { description: string; experience_type?: string; limit?: number }) =>
      request<any>(`/agents/${agentId}/experiences/recommend`, { method: 'POST', body: JSON.stringify(data) }),
    crossDomain: (agentId: string, data: { source_type: string; target_type: string; min_reusability?: number; limit?: number }) => {
      const qs = new URLSearchParams();
      qs.set('source_type', data.source_type);
      qs.set('target_type', data.target_type);
      if (data.min_reusability !== undefined) qs.set('min_reusability', String(data.min_reusability));
      if (data.limit) qs.set('limit', String(data.limit));
      return request<any>(`/agents/${agentId}/experiences/cross-domain?${qs.toString()}`);
    },
    clusterSummary: (clusterId: string) =>
      request<any>(`/experiences/clusters/${clusterId}/summary`),
  },

  // ── Platform ──
  platformOps: {
    fleetOrchestrate: (data: { fleet_name: string; agent_ids: string[]; description?: string }) =>
      request<any>('/platform/fleet/orchestrate', { method: 'POST', body: JSON.stringify(data) }),
    fleetSyncKnowledge: (data: { fleet_id: string; conflict_strategy?: string }) =>
      request<any>('/platform/fleet/sync-knowledge', { method: 'POST', body: JSON.stringify(data) }),
    healthDashboard: () =>
      request<any>('/platform/health-dashboard'),
    autoScale: (data: { fleet_id: string; metric?: string; threshold?: number }) =>
      request<any>('/platform/auto-scale', { method: 'POST', body: JSON.stringify(data) }),
    quotas: () =>
      request<any>('/platform/quotas'),
    eventBroadcast: (data: { message: string; category: string; priority?: string }) =>
      request<any>('/platform/events/broadcast', { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── Agent Composer ──
  agentComposer: {
    execute: (data: { agent_id: string; message: string; mode?: string; strategy?: string; enable_tools?: boolean; enable_reasoning?: boolean; conversation_history?: any[] }) =>
      request<any>('/agents/compose/execute', { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── AgentFlow ──
  agentFlow: {
    stats: () => request<any>('/agent-flow/stats'),
    history: (limit?: number) => {
      const qs = limit ? `?limit=${limit}` : '';
      return request<any>(`/agent-flow/history${qs}`);
    },
    executeStructured: (data: {
      prompt: string;
      fields: Record<string, any>;
      required_fields: string[];
      schema_name?: string;
      strict_mode?: boolean;
      system_prompt?: string;
      max_retries?: number;
      temperature?: number;
    }) => request<any>('/agent-flow/execute-structured', { method: 'POST', body: JSON.stringify(data) }),
    reasonParallel: (data: {
      prompt: string;
      system_prompt?: string;
      strategies?: string[];
      num_paths?: number;
      synthesize?: boolean;
    }) => request<any>('/agent-flow/reason-parallel', { method: 'POST', body: JSON.stringify(data) }),
    executeToolChain: (data: {
      task: string;
      tools?: Record<string, any>[];
      system_prompt?: string;
      max_rounds?: number;
    }) => request<any>('/agent-flow/execute-tool-chain', { method: 'POST', body: JSON.stringify(data) }),
    executeWithCorrection: (data: {
      prompt: string;
      system_prompt?: string;
      quality_threshold?: number;
      max_corrections?: number;
    }) => request<any>('/agent-flow/execute-with-correction', { method: 'POST', body: JSON.stringify(data) }),
    stream: (data: { prompt: string; system_prompt?: string; tools?: Record<string, any>[] }) => {
      const controller = new AbortController();
      const response = fetch('/api/agent-flow/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        signal: controller.signal,
      });
      return response;
    },
    manageContext: (data: { messages: Record<string, any>[]; max_tokens?: number; preserve_system?: boolean }) =>
      request<any>('/agent-flow/manage-context', { method: 'POST', body: JSON.stringify(data) }),
    audit: (data: { flow_id?: string; include_tool_calls?: boolean; include_corrections?: boolean }) =>
      request<any>('/agent-flow/audit', { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── Profile ──
  profile: {
    list: () => request<any>('/profiles'),
    get: (id: string) => request<any>(`/profiles/${id}`),
    create: (data: { name: string; display_name?: string; description?: string; communication_style?: string }) =>
      request<any>('/profiles', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => request<any>(`/profiles/${id}`, { method: 'DELETE' }),
    generatePrompt: (id: string) => request<any>(`/profiles/${id}/generate-prompt`, { method: 'POST' }),
    createTemplate: (template: string) => request<any>(`/profiles/template/${template}`, { method: 'POST' }),
  },

  // ── Pipeline ──
  pipeline: {
    list: () => request<any>('/pipelines'),
    get: (id: string) => request<any>(`/pipelines/${id}`),
    create: (data: { name: string; pipeline_type?: string; description?: string }) =>
      request<any>('/pipelines', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => request<any>(`/pipelines/${id}`, { method: 'DELETE' }),
    execute: (id: string) => request<any>(`/pipelines/${id}/execute`, { method: 'POST' }),
    cancel: (id: string) => request<any>(`/pipelines/${id}/cancel`, { method: 'POST' }),
    progress: (id: string) => request<any>(`/pipelines/${id}/progress`),
  },

  goalDecomposer: {
    stats: () => request<import('../types').GoalDecomposerStats>('/goal-decomposer/stats'),
    trees: () => request<{ trees: import('../types').GoalTree[] }>('/goal-decomposer/trees'),
    tree: (goalId: string) => request<import('../types').GoalTree>(`/goal-decomposer/trees/${goalId}`),
    decompose: (data: { description: string; strategy?: string; context?: Record<string, unknown>; tags?: string[] }) =>
      request<import('../types').DecomposeResult>('/goal-decomposer/decompose', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    nextLayer: (goalId: string) => request<{ layer: string[]; progress: Record<string, unknown> }>(
      `/goal-decomposer/trees/${goalId}/next-layer`
    ),
    recompose: (goalId: string, description: string) =>
      request<import('../types').GoalTree>(`/goal-decomposer/trees/${goalId}/recompose`, {
        method: 'POST',
        body: JSON.stringify({ description }),
      }),
  },

  selfReflection: {
    stats: () => request<import('../types').SelfReflectionStats>('/self-reflection/stats'),
    startSession: (agentId: string) =>
      request<import('../types').SelfReflectionSession>('/self-reflection/sessions', {
        method: 'POST',
        body: JSON.stringify({ agent_id: agentId }),
      }),
    recordAction: (data: { session_id: string; action_type: string; description: string; context?: Record<string, unknown> }) =>
      request<import('../types').ActionRecord>('/self-reflection/actions', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    reflect: (sessionId: string) =>
      request<import('../types').ReflectionResult>(`/self-reflection/sessions/${sessionId}/reflect`, {
        method: 'POST',
      }),
    insights: (params?: { session_id?: string; perspective?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.session_id) qs.set('session_id', params.session_id);
      if (params?.perspective) qs.set('perspective', params.perspective);
      if (params?.limit) qs.set('limit', String(params.limit));
      return request<{ insights: import('../types').SelfReflectionInsight[] }>(
        `/self-reflection/insights?${qs.toString()}`
      );
    },
    applyInsight: (insightId: string) =>
      request<{ success: boolean }>(`/self-reflection/insights/${insightId}/apply`, { method: 'POST' }),
    history: (agentId: string) =>
      request<{ sessions: import('../types').SelfReflectionSession[] }>(`/self-reflection/history/${agentId}`),
  },

  memoryConsolidator: {
    stats: () => request<import('../types').MemoryConsolidatorStats>('/memory-consolidator/stats'),
    store: (data: { content: string; memory_type?: string; importance?: number; tags?: string[]; source_session?: string }) =>
      request<import('../types').MemoryEntryItem>('/memory-consolidator/store', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    search: (params: { query: string; memory_type?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      qs.set('query', params.query);
      if (params.memory_type) qs.set('memory_type', params.memory_type);
      if (params.limit) qs.set('limit', String(params.limit));
      return request<{ results: import('../types').MemoryEntryItem[] }>(
        `/memory-consolidator/search?${qs.toString()}`
      );
    },
    consolidate: (data: { strategy?: string; target_layer?: string; limit?: number }) =>
      request<{ consolidated: import('../types').ConsolidatedMemory[] }>('/memory-consolidator/consolidate', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    decay: (data: { threshold?: number }) =>
      request<{ removed: number }>('/memory-consolidator/decay', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    conceptMap: () => request<{ concepts: import('../types').ConceptNode[] }>('/memory-consolidator/concept-map'),
  },

  contextCompressor: {
    stats: () => request<import('../types').ContextCompressorStats>('/context-compressor/stats'),
    addChunk: (data: { content: string; priority?: string; source?: string }) =>
      request<import('../types').ContextChunk>('/context-compressor/chunks', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    compress: (data: { strategy?: string; target_tokens?: number }) =>
      request<import('../types').CompressionResult>('/context-compressor/compress', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    context: () => request<{ chunks: import('../types').ContextChunk[]; budget: import('../types').TokenBudget }>(
      '/context-compressor/context'
    ),
    clear: () => request<{ success: boolean }>('/context-compressor/clear', { method: 'POST' }),
    setBudget: (data: { max_tokens: number; auto_compress?: boolean }) =>
      request<import('../types').TokenBudget>('/context-compressor/budget', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },
};