import React, { useState, useEffect } from 'react';

interface ModelInfo {
  model_id: string;
  provider: string;
  capabilities: string[];
  context_window: number;
  enabled: boolean;
}

interface OrchestratorStats {
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  models: ModelInfo[];
}

export const ModelOrchestratorPanel: React.FC = () => {
  const [stats, setStats] = useState<OrchestratorStats | null>(null);
  const [messages, setMessages] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/model-orchestrator/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch orchestrator stats:', e); }
  };

  const processRequest = async () => {
    if (!messages) return;
    setLoading(true);
    try {
      const res = await fetch('/api/model-orchestrator/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: messages }],
          model_id: selectedModel || undefined,
          max_tokens: 1024,
          temperature: 0.7,
        }),
      });
      setResult(await res.json());
      fetchStats();
    } catch (e) { console.error('Process failed:', e); }
    setLoading(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>Model Orchestrator</h2>
      <p style={{ color: '#666', marginBottom: 24 }}>Multi-model coordination with intelligent routing and cost tracking</p>

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_requests}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Requests</div>
          </div>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_tokens.toLocaleString()}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Tokens</div>
          </div>
          <div style={{ flex: 1, background: '#fefce8', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#ca8a04' }}>${stats.total_cost.toFixed(4)}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Cost</div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Available Models</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
          {stats?.models.map(m => (
            <div key={m.model_id} style={{ background: m.enabled ? '#f8fafc' : '#f1f5f9', borderRadius: 10, padding: 12, border: '1px solid #e2e8f0', opacity: m.enabled ? 1 : 0.5 }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{m.model_id}</div>
              <div style={{ fontSize: 11, color: '#888' }}>{m.provider} | {m.context_window.toLocaleString()} ctx</div>
              <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                {m.capabilities.map(c => (
                  <span key={c} style={{ background: '#e0e7ff', color: '#3730a3', padding: '1px 6px', borderRadius: 4, fontSize: 10 }}>{c}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Message</label>
        <textarea
          value={messages}
          onChange={e => setMessages(e.target.value)}
          placeholder="Enter your message to process..."
          rows={3}
          style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', resize: 'vertical' }}
        />
      </div>

      <button onClick={processRequest} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
        {loading ? 'Processing...' : 'Send Request'}
      </button>

      {result && (
        <div style={{ marginTop: 16, background: '#f8fafc', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0' }}>
          <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>Response from {result.model_id} ({result.duration_ms?.toFixed(0)}ms, {result.tokens_input}+{result.tokens_output} tokens)</div>
          <div style={{ fontSize: 14, lineHeight: 1.6 }}>{result.content}</div>
        </div>
      )}
    </div>
  );
};