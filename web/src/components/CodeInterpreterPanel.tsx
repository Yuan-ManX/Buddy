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

interface CodeInterpreterStats {
  total_sessions: number;
  active_sessions: number;
  total_executions: number;
  total_successful: number;
  total_failed: number;
  languages: Record<string, number>;
}

interface InterpreterSession {
  id: string;
  name: string;
  status: string;
  language: string;
  execution_count: number;
  created_at: string;
  last_execution_at: string;
}

interface ExecutionResult {
  id: string;
  session_id: string;
  language: string;
  code: string;
  success: boolean;
  stdout: string;
  stderr: string;
  result: string;
  duration_ms: number;
  error: string;
  created_at: string;
}

type Tab = 'editor' | 'sessions' | 'history';

export const CodeInterpreterPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('editor');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Stats
  const [stats, setStats] = useState<CodeInterpreterStats | null>(null);

  // Editor
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);

  // Sessions
  const [sessions, setSessions] = useState<InterpreterSession[]>([]);
  const [newSessionName, setNewSessionName] = useState('');

  // History
  const [executions, setExecutions] = useState<ExecutionResult[]>([]);
  const [historySessionId, setHistorySessionId] = useState('');
  const [historyPage, setHistoryPage] = useState(1);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<CodeInterpreterStats>('/code-interpreter/stats');
      setStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load code interpreter stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ sessions: InterpreterSession[] }>('/code-interpreter/sessions');
      setSessions(data.sessions || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadExecutions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set('page', String(historyPage));
      params.set('page_size', '20');
      if (historySessionId) params.set('session_id', historySessionId);
      const data = await request<{ executions: ExecutionResult[]; total: number }>(`/code-interpreter/executions?${params.toString()}`);
      setExecutions(data.executions || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load executions');
    } finally {
      setLoading(false);
    }
  }, [historyPage, historySessionId]);

  useEffect(() => {
    loadStats();
    loadSessions();
  }, []);

  const handleExecute = async () => {
    if (!code.trim()) return;
    setExecuting(true);
    setError(null);
    setResult(null);
    try {
      const data = await request<ExecutionResult>('/code-interpreter/execute', {
        method: 'POST',
        body: JSON.stringify({
          language,
          code,
          session_id: sessionId || undefined,
        }),
      });
      setResult(data);
      loadStats();
      loadSessions();
    } catch (e: any) {
      setError(e.message || 'Execution failed');
    } finally {
      setExecuting(false);
    }
  };

  const handleCreateSession = async () => {
    if (!newSessionName.trim()) return;
    try {
      await request('/code-interpreter/sessions', {
        method: 'POST',
        body: JSON.stringify({ name: newSessionName, language }),
      });
      setNewSessionName('');
      loadSessions();
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to create session');
    }
  };

  const handleDeleteSession = async (id: string) => {
    if (!confirm('Delete this session and all its executions?')) return;
    try {
      await request(`/code-interpreter/sessions/${id}`, { method: 'DELETE' });
      if (sessionId === id) setSessionId('');
      loadSessions();
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to delete session');
    }
  };

  const languageOptions = [
    { value: 'python', label: 'Python', color: '#3776AB' },
    { value: 'javascript', label: 'JavaScript', color: '#F7DF1E' },
    { value: 'bash', label: 'Bash', color: '#4EAA25' },
    { value: 'sql', label: 'SQL', color: '#E38C00' },
  ];

  const languageColor = (lang: string) => {
    const found = languageOptions.find(l => l.value === lang);
    return found ? found.color : '#9ca3af';
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return '#10b981';
      case 'idle': return '#f59e0b';
      case 'closed': return '#6b7280';
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
    return <div style={{ padding: 24, color: '#6b7280' }}>Loading code interpreter data...</div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Code Interpreter</h2>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0', fontSize: 13 }}>Multi-language code execution environment</p>
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

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_executions.toLocaleString()}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Executions</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#10b981' }}>{stats.total_successful}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Successful</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#ef4444' }}>{stats.total_failed}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Failed</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.active_sessions}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Active Sessions</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {(['editor', 'sessions', 'history'] as Tab[]).map(tab => (
          <button key={tab} style={tabStyle(tab)} onClick={() => {
            setActiveTab(tab);
            if (tab === 'history') loadExecutions();
          }}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Editor Tab */}
      {activeTab === 'editor' && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 500px', minWidth: 300 }}>
            <div style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: 4 }}>
                  {languageOptions.map(lang => (
                    <button
                      key={lang.value}
                      onClick={() => setLanguage(lang.value)}
                      style={{
                        padding: '6px 14px',
                        background: language === lang.value ? lang.color : '#f3f4f6',
                        color: language === lang.value ? '#fff' : '#374151',
                        border: 'none',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontSize: 13,
                        fontWeight: language === lang.value ? 600 : 400,
                      }}
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
                <div style={{ flex: 1 }} />
                <select
                  value={sessionId}
                  onChange={e => setSessionId(e.target.value)}
                  style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
                >
                  <option value="">No Session (ephemeral)</option>
                  {sessions.filter(s => s.status === 'active').map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>

              <textarea
                value={code}
                onChange={e => setCode(e.target.value)}
                placeholder={`Enter ${languageOptions.find(l => l.value === language)?.label} code here...`}
                rows={14}
                style={{
                  width: '100%',
                  padding: 12,
                  borderRadius: 8,
                  border: '1px solid #d1d5db',
                  fontSize: 13,
                  fontFamily: '"SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas, monospace',
                  resize: 'vertical',
                  boxSizing: 'border-box',
                  background: '#1e1e1e',
                  color: '#d4d4d4',
                  lineHeight: 1.5,
                  tabSize: 4,
                }}
                onKeyDown={e => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    handleExecute();
                  }
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: '#9ca3af' }}>Cmd/Ctrl+Enter to execute</span>
                <button
                  onClick={handleExecute}
                  disabled={executing || !code.trim()}
                  style={{
                    padding: '10px 24px',
                    background: (executing || !code.trim()) ? '#d1d5db' : '#10b981',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 8,
                    cursor: (executing || !code.trim()) ? 'default' : 'pointer',
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  {executing ? 'Running...' : 'Run Code'}
                </button>
              </div>
            </div>

            {result && (
              <div style={{ marginTop: 16 }}>
                <div style={{
                  background: '#1e1e1e',
                  borderRadius: 12,
                  padding: 16,
                  border: `2px solid ${result.success ? '#10b981' : '#ef4444'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: result.success ? '#10b981' : '#ef4444',
                        color: '#fff',
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {result.success ? 'SUCCESS' : 'FAILED'}
                      </span>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: languageColor(result.language),
                        color: '#fff',
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {result.language}
                      </span>
                      <span style={{ color: '#9ca3af', fontSize: 12 }}>{result.duration_ms}ms</span>
                    </div>
                    <span style={{ color: '#6b7280', fontSize: 11 }}>{new Date(result.created_at).toLocaleString()}</span>
                  </div>

                  {result.stdout && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ color: '#6b7280', fontSize: 11, marginBottom: 4 }}>STDOUT</div>
                      <pre style={{
                        margin: 0,
                        padding: '8px 12px',
                        background: '#111',
                        borderRadius: 6,
                        color: '#d4d4d4',
                        fontSize: 12,
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        maxHeight: 200,
                        overflow: 'auto',
                      }}>
                        {result.stdout}
                      </pre>
                    </div>
                  )}

                  {result.stderr && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ color: '#ef4444', fontSize: 11, marginBottom: 4 }}>STDERR</div>
                      <pre style={{
                        margin: 0,
                        padding: '8px 12px',
                        background: '#111',
                        borderRadius: 6,
                        color: '#f87171',
                        fontSize: 12,
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        maxHeight: 200,
                        overflow: 'auto',
                      }}>
                        {result.stderr}
                      </pre>
                    </div>
                  )}

                  {result.result && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ color: '#10b981', fontSize: 11, marginBottom: 4 }}>RESULT</div>
                      <pre style={{
                        margin: 0,
                        padding: '8px 12px',
                        background: '#111',
                        borderRadius: 6,
                        color: '#6ee7b7',
                        fontSize: 12,
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        maxHeight: 200,
                        overflow: 'auto',
                      }}>
                        {result.result}
                      </pre>
                    </div>
                  )}

                  {result.error && (
                    <div>
                      <div style={{ color: '#ef4444', fontSize: 11, marginBottom: 4 }}>ERROR</div>
                      <pre style={{
                        margin: 0,
                        padding: '8px 12px',
                        background: '#111',
                        borderRadius: 6,
                        color: '#f87171',
                        fontSize: 12,
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}>
                        {result.error}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div style={{ flex: '0 0 260px' }}>
            <div style={{ background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Language Usage</h3>
              {stats && stats.languages ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {Object.entries(stats.languages).map(([lang, count]) => (
                    <div key={lang} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
                          background: languageColor(lang),
                          display: 'inline-block',
                        }} />
                        <span style={{ textTransform: 'capitalize' }}>{lang}</span>
                      </div>
                      <span style={{ fontWeight: 600 }}>{count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: '#9ca3af', fontSize: 13 }}>No language data available.</div>
              )}

              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e5e7eb' }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 8px 0' }}>Quick Create Session</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <input
                    value={newSessionName}
                    onChange={e => setNewSessionName(e.target.value)}
                    placeholder="Session name..."
                    style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
                    onKeyDown={e => e.key === 'Enter' && handleCreateSession()}
                  />
                  <button
                    onClick={handleCreateSession}
                    disabled={!newSessionName.trim()}
                    style={{
                      padding: '8px 16px',
                      background: newSessionName.trim() ? '#7c3aed' : '#d1d5db',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 8,
                      cursor: newSessionName.trim() ? 'pointer' : 'default',
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                  >
                    Create Session
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sessions Tab */}
      {activeTab === 'sessions' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Interpreter Sessions</h3>
            <button
              onClick={() => setActiveTab('editor')}
              style={{ padding: '8px 16px', background: '#10b981', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}
            >
              Open Editor
            </button>
          </div>

          {sessions.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No interpreter sessions. Create one from the Editor tab.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Name</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Language</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Status</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Executions</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Created</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Last Execution</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map(session => (
                  <tr key={session.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>{session.name}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: languageColor(session.language),
                        color: '#fff',
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {session.language}
                      </span>
                    </td>
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
                    <td style={{ padding: '10px 12px' }}>{session.execution_count}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{new Date(session.created_at).toLocaleString()}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>
                      {session.last_execution_at ? new Date(session.last_execution_at).toLocaleString() : 'Never'}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          onClick={() => {
                            setSessionId(session.id);
                            setActiveTab('editor');
                          }}
                          style={{ padding: '4px 8px', background: '#eff6ff', color: '#2563eb', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          Use
                        </button>
                        <button
                          onClick={() => {
                            setHistorySessionId(session.id);
                            setHistoryPage(1);
                            loadExecutions();
                            setActiveTab('history');
                          }}
                          style={{ padding: '4px 8px', background: '#f0fdf4', color: '#059669', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          History
                        </button>
                        <button
                          onClick={() => handleDeleteSession(session.id)}
                          style={{ padding: '4px 8px', background: '#fef2f2', color: '#dc2626', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Execution History</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <select
                value={historySessionId}
                onChange={e => { setHistorySessionId(e.target.value); setHistoryPage(1); }}
                style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
              >
                <option value="">All Sessions</option>
                {sessions.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <button
                onClick={loadExecutions}
                style={{ padding: '6px 12px', background: '#f3f4f6', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
              >
                Refresh
              </button>
            </div>
          </div>

          {executions.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No execution history yet. Run some code from the Editor tab.</div>
          ) : (
            <div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
                <thead>
                  <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Language</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Status</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Duration</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Code</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Result</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {executions.map(exec => (
                    <tr key={exec.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 12,
                          background: languageColor(exec.language),
                          color: '#fff',
                          fontSize: 11,
                          fontWeight: 600,
                        }}>
                          {exec.language}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ color: exec.success ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                          {exec.success ? 'OK' : 'FAIL'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>{exec.duration_ms}ms</td>
                      <td style={{ padding: '10px 12px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>
                        {exec.code}
                      </td>
                      <td style={{ padding: '10px 12px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>
                        {exec.result || exec.stdout || exec.error || '-'}
                      </td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{new Date(exec.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
                <button
                  onClick={() => { setHistoryPage(p => Math.max(1, p - 1)); loadExecutions(); }}
                  disabled={historyPage === 1}
                  style={{ padding: '6px 12px', background: historyPage === 1 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: historyPage === 1 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Previous
                </button>
                <span style={{ padding: '6px 12px', fontSize: 13, color: '#6b7280' }}>Page {historyPage}</span>
                <button
                  onClick={() => { setHistoryPage(p => p + 1); loadExecutions(); }}
                  disabled={executions.length < 20}
                  style={{ padding: '6px 12px', background: executions.length < 20 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: executions.length < 20 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};