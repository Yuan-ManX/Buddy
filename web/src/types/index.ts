export interface Agent {
  id: string;
  name: string;
  role: string;
  personality: string;
  instructions: string;
  avatar: string;
  created_at: string;
  is_active: boolean;
}

export interface Message {
  id: string;
  agent_id: string;
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

export interface MemoryEntry {
  id: string;
  agent_id: string;
  conversation_id: string | null;
  content: string;
  memory_type: 'fact' | 'preference' | 'event' | 'decision';
  importance: number;
  created_at: string;
}

export interface Skill {
  name: string;
  description: string;
  parameters: Record<string, string>;
}

export interface ChatResponse {
  agent_id: string;
  content: string;
  conversation_id: string;
  tool_calls: Array<{ name: string; arguments: string; result: string }>;
}

export type WSMessage =
  | { type: 'thinking' }
  | { type: 'token'; content: string }
  | { type: 'done'; content: string }
  | { type: 'error'; content: string };