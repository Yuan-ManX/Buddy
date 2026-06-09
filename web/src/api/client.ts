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

  system: {
    overview: () => request<import('../types').SystemOverview>('/system/overview'),
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
};