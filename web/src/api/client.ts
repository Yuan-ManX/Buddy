import type { Agent, Conversation, Message, ChatResponse, Skill, MemoryEntry } from '../types';

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<{ status: string; service: string }>('/health'),

  agents: {
    list: () => request<Agent[]>('/agents'),
    get: (id: string) => request<Agent>(`/agents/${id}`),
    create: (data: { name: string; role: string; personality: string; instructions: string }) =>
      request<Agent>('/agents', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/agents/${id}`, { method: 'DELETE' }),
  },

  conversations: {
    list: () => request<Conversation[]>('/conversations'),
    get: (id: string) => request<Conversation>(`/conversations/${id}`),
    create: (data: { title: string; agent_ids: string[] }) =>
      request<Conversation>('/conversations', { method: 'POST', body: JSON.stringify(data) }),
    messages: (convId: string) => request<Message[]>(`/conversations/${convId}/messages`),
  },

  chat: (data: { agent_id: string; content: string; conversation_id?: string }) =>
    request<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify(data) }),

  memories: {
    list: (agentId: string, query?: string) =>
      request<MemoryEntry[]>(`/agents/${agentId}/memories${query ? `?query=${encodeURIComponent(query)}` : ''}`),
  },

  skills: {
    list: () => request<Skill[]>('/skills'),
    execute: (data: { skill_name: string; agent_id: string; parameters: Record<string, unknown> }) =>
      request<{ result: string }>('/skills/execute', { method: 'POST', body: JSON.stringify(data) }),
  },
};