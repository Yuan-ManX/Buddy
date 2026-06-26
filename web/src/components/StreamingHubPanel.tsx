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

interface StreamingHubStats {
  active_streams: number;
  total_events: number;
  total_bytes: number;
  active_sessions: number;
  total_sessions: number;
  events_per_second: number;
}

interface StreamSession {
  id: string;
  stream_id: string;
  name: string;
  status: string;
  event_count: number;
  bytes_transferred: number;
  created_at: string;
  last_event_at: string;
}

interface StreamEvent {
  id: string;
  session_id: string;
  event_type: string;
  payload: string;
  size_bytes: number;
  created_at: string;
}

type Tab = 'overview' | 'sessions' | 'events' | 'create';

export const StreamingHubPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview
  const [stats, setStats] = useState<StreamingHubStats | null>(null);

  // Sessions
  const [sessions, setSessions] = useState<StreamSession[]>([]);

  // Events
  const [selectedSessionId, setSelectedSessionId] = useState('');
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [eventPage, setEventPage] = useState(1);

  // Create Stream
  const [createForm, setCreateForm] = useState({ name: '', event_type: 'message', payload: '' });
  const [emitForm, setEmitForm] = useState({ session_id: '', event_type: 'message', payload: '' });
  const [emitResult, setEmitResult] = useState<any>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<StreamingHubStats>('/streaming-hub/stats');
      setStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load streaming hub stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ sessions: StreamSession[] }>('/streaming-hub/sessions');
      setSessions(data.sessions || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadEvents = useCallback(async (sessionId: string) => {
    if (!sessionId) return;
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set('page', String(eventPage));
      params.set('page_size', '50');
      const data = await request<{ events: StreamEvent[]; total: number }>(`/streaming-hub/sessions/${sessionId}/events?${params.toString()}`);
      setEvents(data.events || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load events');
    } finally {
      setLoading(false);
    }
  }, [eventPage]);

  useEffect(() => {
    loadStats();
    loadSessions();
  }, []);

  const handleCreateStream = async () => {
    if (!createForm.name.trim()) return;
    try {
      const data = await request<{ session_id: string }>('/streaming-hub/sessions', {
        method: 'POST',
        body: JSON.stringify({ name: createForm.name }),
      });
      setCreateForm({ name: '', event_type: 'message', payload: '' });
      loadSessions();
      loadStats();
      alert(`Stream created! Session ID: ${data.session_id}`);
    } catch (e: any) {
      setError(e.message || 'Failed to create stream');
    }
  };

  const handleEmitEvent = async () => {
    if (!emitForm.session_id || !emitForm.payload.trim()) return;
    try {
      const data = await request(`/streaming-hub/sessions/${emitForm.session_id}/events`, {
        method: 'POST',
        body: JSON.stringify({
          event_type: emitForm.event_type,
          payload: emitForm.payload,
        }),
      });
      setEmitResult(data);
      setEmitForm(prev => ({ ...prev, payload: '' }));
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to emit event');
    }
  };

  const handleCloseSession = async (sessionId: string) => {
    if (!confirm('Close this streaming session?')) return;
    try {
      await request(`/streaming-hub/sessions/${sessionId}`, { method: 'DELETE' });
      loadSessions();
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to close session');
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return '#10b981';
      case 'idle': return '#f59e0b';
      case 'closed': return '#6b7280';
      case 'error': return '#ef4444';
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

  if (loading && !stats && sessions.length === 0) {
    return <div style={{ padding: 24, color: '#6b7280' }}>Loading streaming hub data...</div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Streaming Hub</h2>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0', fontSize: 13 }}>Real-time event streaming and session management</p>
        </div>
        <button
          onClick={() => { loadStats(); loadSessions(); }}
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
        {(['overview', 'sessions', 'events', 'create'] as Tab[]).map(tab => (
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
              <div style={{ fontSize: 28, fontWeight: 700, color: '#10b981' }}>{stats.active_streams}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Active Streams</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_events.toLocaleString()}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Events</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{formatBytes(stats.total_bytes)}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Data Transferred</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#ea580c' }}>{stats.events_per_second.toFixed(1)}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Events/s</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Session Summary</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Active Sessions</span>
                  <span style={{ fontWeight: 600, color: '#10b981' }}>{stats.active_sessions}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Total Sessions</span>
                  <span style={{ fontWeight: 600 }}>{stats.total_sessions}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Avg Events / Session</span>
                  <span style={{ fontWeight: 600 }}>
                    {stats.total_sessions > 0 ? (stats.total_events / stats.total_sessions).toFixed(1) : '0'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Avg Bytes / Event</span>
                  <span style={{ fontWeight: 600 }}>
                    {stats.total_events > 0 ? formatBytes(stats.total_bytes / stats.total_events) : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
            <div style={{ flex: 2, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Active Sessions</h3>
              {sessions.filter(s => s.status === 'active').length === 0 ? (
                <div style={{ color: '#9ca3af', fontSize: 13 }}>No active streaming sessions.</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Name</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Events</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Data</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Last Event</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.filter(s => s.status === 'active').slice(0, 10).map(session => (
                      <tr key={session.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '6px 8px', fontWeight: 500 }}>{session.name}</td>
                        <td style={{ padding: '6px 8px' }}>{session.event_count}</td>
                        <td style={{ padding: '6px 8px', fontFamily: 'monospace', fontSize: 12 }}>{formatBytes(session.bytes_transferred)}</td>
                        <td style={{ padding: '6px 8px', fontSize: 12, color: '#6b7280' }}>
                          {session.last_event_at ? new Date(session.last_event_at).toLocaleString() : 'Never'}
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

      {/* Sessions Tab */}
      {activeTab === 'sessions' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>All Stream Sessions</h3>
            <button
              onClick={() => { setActiveTab('create'); }}
              style={{ padding: '8px 16px', background: '#10b981', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
            >
              + New Stream
            </button>
          </div>
          {sessions.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No streaming sessions. Create one from the Create tab.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Name</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Stream ID</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Status</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Events</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Data</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Created</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map(session => (
                  <tr key={session.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>{session.name}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>{session.stream_id}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: statusColor(session.status),
                        color: '#fff',
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {session.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>{session.event_count}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>{formatBytes(session.bytes_transferred)}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{new Date(session.created_at).toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          onClick={() => {
                            setSelectedSessionId(session.id);
                            setEventPage(1);
                            loadEvents(session.id);
                            setActiveTab('events');
                          }}
                          style={{ padding: '4px 8px', background: '#eff6ff', color: '#2563eb', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          Events
                        </button>
                        <button
                          onClick={() => {
                            setEmitForm({ session_id: session.id, event_type: 'message', payload: '' });
                            setActiveTab('create');
                          }}
                          style={{ padding: '4px 8px', background: '#f0fdf4', color: '#059669', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          Emit
                        </button>
                        {session.status !== 'closed' && (
                          <button
                            onClick={() => handleCloseSession(session.id)}
                            style={{ padding: '4px 8px', background: '#fef2f2', color: '#dc2626', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                          >
                            Close
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Events Tab */}
      {activeTab === 'events' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Events {selectedSessionId ? `for ${selectedSessionId}` : ''}
            </h3>
            <select
              value={selectedSessionId}
              onChange={e => {
                setSelectedSessionId(e.target.value);
                setEventPage(1);
                if (e.target.value) loadEvents(e.target.value);
              }}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">Select Session...</option>
              {sessions.map(s => <option key={s.id} value={s.id}>{s.name} ({s.stream_id})</option>)}
            </select>
          </div>

          {!selectedSessionId ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Select a session to view its events.</div>
          ) : events.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No events in this stream yet.</div>
          ) : (
            <div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {events.map(event => (
                  <div key={event.id} style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #e5e7eb' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 12,
                          background: '#3b82f6',
                          color: '#fff',
                          fontSize: 11,
                          fontWeight: 600,
                        }}>
                          {event.event_type}
                        </span>
                        <span style={{ fontSize: 11, color: '#9ca3af', fontFamily: 'monospace' }}>{event.id}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: '#6b7280' }}>{formatBytes(event.size_bytes)}</span>
                        <span style={{ fontSize: 11, color: '#9ca3af' }}>{new Date(event.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                    <div style={{ fontSize: 13, color: '#374151', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', background: '#f9fafb', padding: '8px 12px', borderRadius: 6 }}>
                      {event.payload.length > 1000 ? event.payload.substring(0, 1000) + '...' : event.payload}
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
                <button
                  onClick={() => { setEventPage(p => Math.max(1, p - 1)); loadEvents(selectedSessionId); }}
                  disabled={eventPage === 1}
                  style={{ padding: '6px 12px', background: eventPage === 1 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: eventPage === 1 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Previous
                </button>
                <span style={{ padding: '6px 12px', fontSize: 13, color: '#6b7280' }}>Page {eventPage}</span>
                <button
                  onClick={() => { setEventPage(p => p + 1); loadEvents(selectedSessionId); }}
                  disabled={events.length < 50}
                  style={{ padding: '6px 12px', background: events.length < 50 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: events.length < 50 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create Tab */}
      {activeTab === 'create' && (
        <div>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            {/* Create Stream */}
            <div style={{ flex: '1 1 300px', background: '#fff', borderRadius: 12, padding: 20, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px 0' }}>Create New Stream</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 4 }}>Stream Name</label>
                  <input
                    value={createForm.name}
                    onChange={e => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="My Stream"
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13, boxSizing: 'border-box' }}
                  />
                </div>
                <button
                  onClick={handleCreateStream}
                  disabled={!createForm.name.trim()}
                  style={{
                    padding: '10px 16px',
                    background: createForm.name.trim() ? '#10b981' : '#d1d5db',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 8,
                    cursor: createForm.name.trim() ? 'pointer' : 'default',
                    fontSize: 13,
                    fontWeight: 500,
                  }}
                >
                  Create Stream
                </button>
              </div>
            </div>

            {/* Emit Event */}
            <div style={{ flex: '1 1 300px', background: '#fff', borderRadius: 12, padding: 20, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px 0' }}>Emit Event</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 4 }}>Session</label>
                  <select
                    value={emitForm.session_id}
                    onChange={e => setEmitForm(prev => ({ ...prev, session_id: e.target.value }))}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13, boxSizing: 'border-box' }}
                  >
                    <option value="">Select Session...</option>
                    {sessions.filter(s => s.status === 'active').map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 4 }}>Event Type</label>
                  <select
                    value={emitForm.event_type}
                    onChange={e => setEmitForm(prev => ({ ...prev, event_type: e.target.value }))}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13, boxSizing: 'border-box' }}
                  >
                    <option value="message">Message</option>
                    <option value="data">Data</option>
                    <option value="error">Error</option>
                    <option value="status">Status</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 4 }}>Payload</label>
                  <textarea
                    value={emitForm.payload}
                    onChange={e => setEmitForm(prev => ({ ...prev, payload: e.target.value }))}
                    placeholder='{"key": "value"}'
                    rows={4}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13, fontFamily: 'monospace', resize: 'vertical', boxSizing: 'border-box' }}
                  />
                </div>
                <button
                  onClick={handleEmitEvent}
                  disabled={!emitForm.session_id || !emitForm.payload.trim()}
                  style={{
                    padding: '10px 16px',
                    background: (!emitForm.session_id || !emitForm.payload.trim()) ? '#d1d5db' : '#3b82f6',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 8,
                    cursor: (!emitForm.session_id || !emitForm.payload.trim()) ? 'default' : 'pointer',
                    fontSize: 13,
                    fontWeight: 500,
                  }}
                >
                  Emit Event
                </button>
              </div>
            </div>
          </div>

          {emitResult && (
            <div style={{ marginTop: 16, padding: 16, background: '#f0fdf4', borderRadius: 12, border: '1px solid #bbf7d0' }}>
              <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 8px 0', color: '#059669' }}>Event Emitted Successfully</h4>
              <pre style={{ margin: 0, fontSize: 12, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{JSON.stringify(emitResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};