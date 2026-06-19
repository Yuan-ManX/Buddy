import React, { useState, useEffect } from 'react';

interface SandboxStats {
  active_sessions: number;
  total_executions: number;
  total_errors: number;
  sessions: Array<{ id: string; agent_id: string; policy: string }>;
}

export const SandboxPanel: React.FC = () => {
  const [stats, setStats] = useState<SandboxStats | null>(null);
  const [command, setCommand] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/sandbox/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch sandbox stats:', e); }
  };

  const createSession = async () => {
    const res = await fetch('/api/sandbox/create-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: 'default', policy: 'standard' }),
    });
    const data = await res.json();
    setSessionId(data.session_id);
    fetchStats();
  };

  const executeCommand = async () => {
    if (!command || !sessionId) return;
    setLoading(true);
    try {
      const res = await fetch('/api/sandbox/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, command }),
      });
      setResult(await res.json());
      fetchStats();
    } catch (e) { console.error('Execute failed:', e); }
    setLoading(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>Sandbox Engine</h2>
      <p style={{ color: '#666', marginBottom: 24 }}>Secure execution environment for agent operations</p>

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.active_sessions}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Active Sessions</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_executions}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Executions</div>
          </div>
          <div style={{ flex: 1, background: '#fef2f2', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#dc2626' }}>{stats.total_errors}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Errors</div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <button onClick={createSession} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', marginRight: 8 }}>
          Create Session
        </button>
        {sessionId && <span style={{ fontSize: 12, color: '#16a34a' }}>Session: {sessionId}</span>}
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={command}
          onChange={e => setCommand(e.target.value)}
          placeholder="Enter command to execute..."
          style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontFamily: 'monospace' }}
          onKeyDown={e => e.key === 'Enter' && executeCommand()}
        />
        <button onClick={executeCommand} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#16a34a', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
          {loading ? 'Running...' : 'Execute'}
        </button>
      </div>

      {result && (
        <div style={{ background: '#1e1e1e', borderRadius: 12, padding: 16, color: '#d4d4d4', fontFamily: 'monospace', fontSize: 13, maxHeight: 300, overflow: 'auto' }}>
          <div style={{ color: '#888', marginBottom: 8 }}>Result {result.success ? 'OK' : 'FAILED'} (exit: {result.exit_code}, {result.duration_ms?.toFixed(0)}ms)</div>
          {result.stdout && <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{result.stdout}</pre>}
          {result.stderr && <pre style={{ margin: 0, color: '#f87171', whiteSpace: 'pre-wrap' }}>{result.stderr}</pre>}
          {result.error && <pre style={{ margin: 0, color: '#f87171', whiteSpace: 'pre-wrap' }}>{result.error}</pre>}
        </div>
      )}
    </div>
  );
};