import React, { useState, useEffect, useCallback } from 'react';

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try { const parsed = JSON.parse(body); message = parsed.detail || parsed.error || body; } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

interface ConversationMemoryStats {
  total_conversations: number;
  total_messages: number;
  total_topics: number;
  total_summaries: number;
  active_conversations: number;
  avg_messages_per_conversation: number;
}

interface Conversation {
  id: string;
  title: string;
  agent_id: string;
  message_count: number;
  topic_count: number;
  last_message_at: string;
  created_at: string;
  summary: string;
}

interface Message {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  topic: string;
  importance: number;
  created_at: string;
}

interface Topic {
  id: string;
  name: string;
  conversation_id: string;
  message_count: number;
  summary: string;
  created_at: string;
}

interface Summary {
  id: string;
  conversation_id: string;
  content: string;
  message_range: string;
  created_at: string;
}

type Tab = 'overview' | 'conversations' | 'messages' | 'topics' | 'summaries';

export const ConversationMemoryPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview
  const [stats, setStats] = useState<ConversationMemoryStats | null>(null);

  // Conversations
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [convSearch, setConvSearch] = useState('');
  const [convPage, setConvPage] = useState(1);

  // Messages
  const [selectedConvId, setSelectedConvId] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [msgPage, setMsgPage] = useState(1);

  // Topics
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topicConvId, setTopicConvId] = useState('');

  // Summaries
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [summaryConvId, setSummaryConvId] = useState('');

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<ConversationMemoryStats>('/conversation-memory/stats');
      setStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set('page', String(convPage));
      params.set('page_size', '20');
      if (convSearch) params.set('search', convSearch);
      const data = await request<{ conversations: Conversation[]; total: number }>(`/conversation-memory/conversations?${params.toString()}`);
      setConversations(data.conversations || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  }, [convPage, convSearch]);

  const loadMessages = useCallback(async (convId: string) => {
    if (!convId) return;
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set('page', String(msgPage));
      params.set('page_size', '50');
      const data = await request<{ messages: Message[]; total: number }>(`/conversation-memory/conversations/${convId}/messages?${params.toString()}`);
      setMessages(data.messages || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  }, [msgPage]);

  const loadTopics = useCallback(async (convId: string) => {
    if (!convId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ topics: Topic[] }>(`/conversation-memory/conversations/${convId}/topics`);
      setTopics(data.topics || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load topics');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSummaries = useCallback(async (convId: string) => {
    if (!convId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ summaries: Summary[] }>(`/conversation-memory/conversations/${convId}/summaries`);
      setSummaries(data.summaries || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load summaries');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadConversations();
  }, []);

  const handleSearch = () => {
    setConvPage(1);
    loadConversations();
  };

  const handleGenerateSummary = async (convId: string) => {
    try {
      await request(`/conversation-memory/conversations/${convId}/summarize`, { method: 'POST' });
      loadSummaries(convId);
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to generate summary');
    }
  };

  const handleDeleteConversation = async (convId: string) => {
    if (!confirm('Delete this conversation and all its messages?')) return;
    try {
      await request(`/conversation-memory/conversations/${convId}`, { method: 'DELETE' });
      loadConversations();
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to delete conversation');
    }
  };

  const roleColor = (role: string) => {
    switch (role) {
      case 'user': return '#3b82f6';
      case 'assistant': return '#10b981';
      case 'system': return '#8b5cf6';
      default: return '#9ca3af';
    }
  };

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '8px 16px',
    background: activeTab === tab ? '#3b82f6' : '#f3f4f6',
    color: activeTab === tab ? '#fff' : '#374151',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    fontWeight: activeTab === tab ? 600 : 400,
    fontSize: 13,
  });

  const statCardStyle: React.CSSProperties = {
    flex: 1,
    background: '#f9fafb',
    borderRadius: 12,
    padding: 16,
    textAlign: 'center',
    border: '1px solid #e5e7eb',
  };

  if (loading && !stats && conversations.length === 0) {
    return <div style={{ padding: 24, color: '#6b7280' }}>Loading conversation memory data...</div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Conversation Memory</h2>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0', fontSize: 13 }}>Conversation history, topics, and summaries</p>
        </div>
        <button
          onClick={() => { loadStats(); loadConversations(); }}
          style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: '#fef2f2', borderRadius: 8, color: '#dc2626', marginBottom: 16, fontSize: 13 }}>
          {error}
          <button style={{ marginLeft: 12, color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {(['overview', 'conversations', 'messages', 'topics', 'summaries'] as Tab[]).map(tab => (
          <button key={tab} style={tabStyle(tab)} onClick={() => setActiveTab(tab)}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && stats && (
        <div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_conversations}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Conversations</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.total_messages.toLocaleString()}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Messages</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#059669' }}>{stats.total_topics}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Topics</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#ea580c' }}>{stats.total_summaries}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Summaries</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#dc2626' }}>{stats.active_conversations}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Active</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Memory Metrics</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Avg Messages / Conversation</span>
                  <span style={{ fontWeight: 600 }}>{stats.avg_messages_per_conversation.toFixed(1)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Topic Coverage</span>
                  <span style={{ fontWeight: 600 }}>
                    {stats.total_conversations > 0 ? (stats.total_topics / stats.total_conversations).toFixed(1) : '0'} per conv
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Summary Coverage</span>
                  <span style={{ fontWeight: 600 }}>
                    {stats.total_conversations > 0 ? ((stats.total_summaries / stats.total_conversations) * 100).toFixed(0) : '0'}%
                  </span>
                </div>
              </div>
            </div>
            <div style={{ flex: 2, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Recent Conversations</h3>
              {conversations.length === 0 ? (
                <div style={{ color: '#9ca3af', fontSize: 13 }}>No conversations yet.</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Title</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Messages</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Topics</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Last Active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {conversations.slice(0, 10).map(conv => (
                      <tr key={conv.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '6px 8px', fontWeight: 500 }}>{conv.title}</td>
                        <td style={{ padding: '6px 8px' }}>{conv.message_count}</td>
                        <td style={{ padding: '6px 8px' }}>{conv.topic_count}</td>
                        <td style={{ padding: '6px 8px', fontSize: 12, color: '#6b7280' }}>
                          {conv.last_message_at ? new Date(conv.last_message_at).toLocaleString() : 'Never'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Conversations Tab */}
      {activeTab === 'conversations' && (
        <div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
            <input
              value={convSearch}
              onChange={e => setConvSearch(e.target.value)}
              placeholder="Search conversations..."
              style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}
            >
              Search
            </button>
          </div>

          {conversations.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No conversations found.</div>
          ) : (
            <div>
              {conversations.map(conv => (
                <div key={conv.id} style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, border: '1px solid #e5e7eb' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <h4 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 4px 0' }}>{conv.title}</h4>
                      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 8, fontFamily: 'monospace' }}>ID: {conv.id}</div>
                      <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                        <span style={{ color: '#6b7280' }}>Agent: <strong>{conv.agent_id}</strong></span>
                        <span style={{ color: '#6b7280' }}>Messages: <strong>{conv.message_count}</strong></span>
                        <span style={{ color: '#6b7280' }}>Topics: <strong>{conv.topic_count}</strong></span>
                        <span style={{ color: '#6b7280' }}>Created: <strong>{new Date(conv.created_at).toLocaleDateString()}</strong></span>
                      </div>
                      {conv.summary && (
                        <div style={{ marginTop: 8, padding: '8px 12px', background: '#f0fdf4', borderRadius: 6, fontSize: 13, color: '#065f46' }}>
                          {conv.summary}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button
                        onClick={() => {
                          setSelectedConvId(conv.id);
                          setMsgPage(1);
                          loadMessages(conv.id);
                          setActiveTab('messages');
                        }}
                        style={{ padding: '6px 12px', background: '#eff6ff', color: '#2563eb', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
                      >
                        Messages
                      </button>
                      <button
                        onClick={() => {
                          setTopicConvId(conv.id);
                          loadTopics(conv.id);
                          setActiveTab('topics');
                        }}
                        style={{ padding: '6px 12px', background: '#f0fdf4', color: '#059669', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
                      >
                        Topics
                      </button>
                      <button
                        onClick={() => handleGenerateSummary(conv.id)}
                        style={{ padding: '6px 12px', background: '#fef3c7', color: '#d97706', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
                      >
                        Summarize
                      </button>
                      <button
                        onClick={() => handleDeleteConversation(conv.id)}
                        style={{ padding: '6px 12px', background: '#fef2f2', color: '#dc2626', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
                <button
                  onClick={() => setConvPage(p => Math.max(1, p - 1))}
                  disabled={convPage === 1}
                  style={{ padding: '6px 12px', background: convPage === 1 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: convPage === 1 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Previous
                </button>
                <span style={{ padding: '6px 12px', fontSize: 13, color: '#6b7280' }}>Page {convPage}</span>
                <button
                  onClick={() => { setConvPage(p => p + 1); loadConversations(); }}
                  disabled={conversations.length < 20}
                  style={{ padding: '6px 12px', background: conversations.length < 20 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: conversations.length < 20 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Messages Tab */}
      {activeTab === 'messages' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Messages {selectedConvId ? `for ${selectedConvId}` : ''}
            </h3>
            <select
              value={selectedConvId}
              onChange={e => {
                setSelectedConvId(e.target.value);
                setMsgPage(1);
                if (e.target.value) loadMessages(e.target.value);
              }}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">Select Conversation...</option>
              {conversations.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>

          {!selectedConvId ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Select a conversation to view its messages.</div>
          ) : messages.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No messages in this conversation.</div>
          ) : (
            <div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {messages.map(msg => (
                  <div key={msg.id} style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #e5e7eb', borderLeft: `4px solid ${roleColor(msg.role)}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 12,
                          background: roleColor(msg.role),
                          color: '#fff',
                          fontSize: 11,
                          fontWeight: 600,
                        }}>
                          {msg.role}
                        </span>
                        {msg.topic && (
                          <span style={{ fontSize: 11, color: '#6b7280', background: '#f3f4f6', padding: '2px 8px', borderRadius: 12 }}>
                            {msg.topic}
                          </span>
                        )}
                        {msg.importance > 0 && (
                          <span style={{ fontSize: 11, color: '#d97706' }}>Importance: {msg.importance.toFixed(1)}</span>
                        )}
                      </div>
                      <span style={{ fontSize: 11, color: '#9ca3af' }}>{new Date(msg.created_at).toLocaleString()}</span>
                    </div>
                    <div style={{ fontSize: 13, color: '#374151', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {msg.content.length > 500 ? msg.content.substring(0, 500) + '...' : msg.content}
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
                <button
                  onClick={() => { setMsgPage(p => Math.max(1, p - 1)); loadMessages(selectedConvId); }}
                  disabled={msgPage === 1}
                  style={{ padding: '6px 12px', background: msgPage === 1 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: msgPage === 1 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Previous
                </button>
                <span style={{ padding: '6px 12px', fontSize: 13, color: '#6b7280' }}>Page {msgPage}</span>
                <button
                  onClick={() => { setMsgPage(p => p + 1); loadMessages(selectedConvId); }}
                  disabled={messages.length < 50}
                  style={{ padding: '6px 12px', background: messages.length < 50 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: messages.length < 50 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Topics Tab */}
      {activeTab === 'topics' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Topics {topicConvId ? `for ${topicConvId}` : ''}
            </h3>
            <select
              value={topicConvId}
              onChange={e => {
                setTopicConvId(e.target.value);
                if (e.target.value) loadTopics(e.target.value);
              }}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">Select Conversation...</option>
              {conversations.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>

          {!topicConvId ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Select a conversation to view its topics.</div>
          ) : topics.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No topics extracted for this conversation.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {topics.map(topic => (
                <div key={topic.id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <h4 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>{topic.name}</h4>
                    <span style={{ fontSize: 12, color: '#6b7280', background: '#f3f4f6', padding: '4px 10px', borderRadius: 12 }}>
                      {topic.message_count} messages
                    </span>
                  </div>
                  {topic.summary && (
                    <p style={{ fontSize: 13, color: '#374151', margin: 0, lineHeight: 1.5 }}>{topic.summary}</p>
                  )}
                  <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8 }}>
                    Created: {new Date(topic.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Summaries Tab */}
      {activeTab === 'summaries' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Summaries {summaryConvId ? `for ${summaryConvId}` : ''}
            </h3>
            <select
              value={summaryConvId}
              onChange={e => {
                setSummaryConvId(e.target.value);
                if (e.target.value) loadSummaries(e.target.value);
              }}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">Select Conversation...</option>
              {conversations.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>

          {!summaryConvId ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Select a conversation to view its summaries.</div>
          ) : summaries.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No summaries for this conversation. Generate one from the Conversations tab.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {summaries.map(summary => (
                <div key={summary.id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb', borderLeft: '4px solid #8b5cf6' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 12, color: '#6b7280', background: '#f3f4f6', padding: '4px 8px', borderRadius: 6 }}>
                      Range: {summary.message_range}
                    </span>
                    <span style={{ fontSize: 12, color: '#9ca3af' }}>{new Date(summary.created_at).toLocaleString()}</span>
                  </div>
                  <p style={{ fontSize: 13, color: '#374151', margin: 0, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{summary.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};