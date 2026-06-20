import React, { useState, useEffect } from 'react';

interface IntentResult {
  intent_id: string;
  category: string;
  complexity: string;
  urgency: string;
  confidence: number;
  summary: string;
  suggested_tools: string[];
  suggested_skills: string[];
  follow_up_predictions: string[];
  entities: { name: string; type: string; value: string }[];
  constraints: { type: string; value: string; is_hard: boolean }[];
}

interface IntentSession {
  session_id: string;
  intent_count: number;
  intents: { intent_id: string; category: string; complexity: string; urgency: string; created_at: number }[];
}

export const IntentPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [result, setResult] = useState<IntentResult | null>(null);
  const [session, setSession] = useState<IntentSession | null>(null);
  const [query, setQuery] = useState('');
  const [agentId, setAgentId] = useState('buddy-coder');
  const [sessionId, setSessionId] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/intent/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch intent stats:', e); }
  };

  const analyzeIntent = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/intent/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, query, session_id: sessionId || undefined }),
      });
      const data = await res.json();
      setResult(data);
      setSessionId(data.intent_id);
      fetchStats();
    } catch (e) { console.error('Analyze failed:', e); }
    setLoading(false);
  };

  const fetchSession = async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(`/api/intent/session/${sessionId}`);
      setSession(await res.json());
    } catch (e) { console.error('Session fetch failed:', e); }
  };

  const categoryColor = (cat: string) => {
    const map: Record<string, string> = {
      information_query: '#3b82f6', task_execution: '#16a34a', creative_generation: '#8b5cf6',
      analysis: '#f59e0b', decision_support: '#ec4899', conversation: '#06b6d4',
      troubleshooting: '#ef4444', learning: '#7c3aed', planning: '#f97316', code_generation: '#2563eb',
    };
    return map[cat] || '#6b7280';
  };

  const urgencyColor = (urgency: string) => {
    const map: Record<string, string> = { low: '#16a34a', medium: '#f59e0b', high: '#f97316', critical: '#ef4444' };
    return map[urgency] || '#6b7280';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Intent Engine</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Deep intent recognition with multi-turn context tracking and proactive suggestions</p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_sessions}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Sessions</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_intents}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Intents</div>
          </div>
          <div style={{ flex: 1, background: '#faf5ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.active_agents || 0}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Active Agents</div>
          </div>
        </div>
      )}

      {/* Query Input */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 24, border: '1px solid #e2e8f0' }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input
            value={agentId}
            onChange={e => setAgentId(e.target.value)}
            placeholder="Agent ID"
            style={{ width: 150, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
          />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && analyzeIntent()}
            placeholder="Enter a query to analyze intent..."
            style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
          />
          <button onClick={analyzeIntent} disabled={loading} style={{ padding: '8px 20px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', whiteSpace: 'nowrap' }}>
            {loading ? 'Analyzing...' : 'Analyze Intent'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            value={sessionId}
            onChange={e => setSessionId(e.target.value)}
            placeholder="Session ID (optional)"
            style={{ width: 250, padding: '6px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 12 }}
          />
          <button onClick={fetchSession} style={{ padding: '6px 14px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 12 }}>Load Session</button>
        </div>
      </div>

      {/* Intent Result */}
      {result && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 24, border: '2px solid #2563eb' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Intent Analysis Result</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <span style={{ background: categoryColor(result.category), color: '#fff', padding: '4px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600 }}>{result.category.replace(/_/g, ' ')}</span>
            <span style={{ background: result.complexity === 'simple' ? '#e5e7eb' : '#fef3c7', color: '#333', padding: '4px 12px', borderRadius: 8, fontSize: 12 }}>{result.complexity}</span>
            <span style={{ background: urgencyColor(result.urgency), color: '#fff', padding: '4px 12px', borderRadius: 8, fontSize: 12 }}>{result.urgency}</span>
            <span style={{ background: '#f0fdf4', color: '#16a34a', padding: '4px 12px', borderRadius: 8, fontSize: 12 }}>{(result.confidence * 100).toFixed(0)}% confident</span>
          </div>
          <div style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>{result.summary}</div>

          {/* Entities */}
          {result.entities.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#888' }}>Entities</h4>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {result.entities.map((e, i) => (
                  <span key={i} style={{ background: '#eff6ff', padding: '3px 10px', borderRadius: 6, fontSize: 12, border: '1px solid #bfdbfe' }}>
                    {e.name} <span style={{ color: '#888' }}>({e.type})</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Constraints */}
          {result.constraints.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#888' }}>Constraints</h4>
              {result.constraints.map((c, i) => (
                <span key={i} style={{ background: c.is_hard ? '#fef2f2' : '#fefce8', padding: '3px 10px', borderRadius: 6, fontSize: 12, marginRight: 6, border: `1px solid ${c.is_hard ? '#fecaca' : '#fde68a'}` }}>
                  {c.type}: {c.value} {c.is_hard ? '(hard)' : '(soft)'}
                </span>
              ))}
            </div>
          )}

          {/* Suggestions */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {result.suggested_tools.length > 0 && (
              <div>
                <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#888' }}>Suggested Tools</h4>
                {result.suggested_tools.map((t, i) => (
                  <div key={i} style={{ fontSize: 12, padding: '2px 0', color: '#2563eb' }}>{t}</div>
                ))}
              </div>
            )}
            {result.suggested_skills.length > 0 && (
              <div>
                <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#888' }}>Suggested Skills</h4>
                {result.suggested_skills.map((s, i) => (
                  <div key={i} style={{ fontSize: 12, padding: '2px 0', color: '#7c3aed' }}>{s}</div>
                ))}
              </div>
            )}
            {result.follow_up_predictions.length > 0 && (
              <div>
                <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#888' }}>Predicted Follow-ups</h4>
                {result.follow_up_predictions.map((f, i) => (
                  <div key={i} style={{ fontSize: 12, padding: '2px 0', color: '#f59e0b' }}>{f}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Session History */}
      {session && (
        <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0', fontWeight: 600 }}>
            Session: {session.session_id} ({session.intent_count} intents)
          </div>
          <div style={{ maxHeight: 300, overflow: 'auto' }}>
            {session.intents.map(i => (
              <div key={i.intent_id} style={{ padding: '10px 16px', borderBottom: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ background: categoryColor(i.category), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{i.category.replace(/_/g, ' ')}</span>
                <span style={{ fontSize: 11, color: '#888' }}>{i.complexity} · {i.urgency}</span>
                <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#aaa', marginLeft: 'auto' }}>{i.intent_id}</span>
                <span style={{ fontSize: 11, color: '#999' }}>{new Date(i.created_at * 1000).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};