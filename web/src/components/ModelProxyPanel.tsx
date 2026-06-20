import React, { useState, useEffect } from 'react';

interface ModelInfo {
  model_id: string;
  provider: string;
  model_name: string;
  capabilities: string[];
  health_score: number;
  is_available: boolean;
  current_load: number;
  success_rate: number;
  avg_latency_ms: number;
  cost_per_1k: number;
}

interface ProxyStats {
  total_models: number;
  total_providers: number;
  total_requests: number;
  total_failures: number;
  total_cost: number;
  success_rate: number;
  models: ModelInfo[];
}

export const ModelProxyPanel: React.FC = () => {
  const [stats, setStats] = useState<ProxyStats | null>(null);
  const [showRegister, setShowRegister] = useState(false);
  const [showRoute, setShowRoute] = useState(false);
  const [formData, setFormData] = useState({
    model_id: '', provider: 'openai', model_name: '', capabilities: 'text_generation',
    cost_per_1k: 0.0, max_tokens: 4096, context_window: 8192, max_concurrent: 10,
  });
  const [routeForm, setRouteForm] = useState({ query: '', strategy: 'capability_match', required_capabilities: '' });
  const [routeResult, setRouteResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);
  const fetchStats = async () => {
    try {
      const res = await fetch('/api/model-proxy/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch proxy stats:', e); }
  };

  const registerModel = async () => {
    setLoading(true);
    try {
      await fetch('/api/model-proxy/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          capabilities: formData.capabilities.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setShowRegister(false);
      setFormData({ model_id: '', provider: 'openai', model_name: '', capabilities: 'text_generation', cost_per_1k: 0.0, max_tokens: 4096, context_window: 8192, max_concurrent: 10 });
      fetchStats();
    } catch (e) { console.error('Register failed:', e); }
    setLoading(false);
  };

  const routeRequest = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/model-proxy/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: routeForm.query,
          strategy: routeForm.strategy,
          required_capabilities: routeForm.required_capabilities.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setRouteResult(await res.json());
      fetchStats();
    } catch (e) { console.error('Route failed:', e); }
    setLoading(false);
  };

  const providerColor = (p: string) => {
    const map: Record<string, string> = { openai: '#10a37f', anthropic: '#d97706', local: '#6b7280', together: '#3b82f6', groq: '#f97316', custom: '#8b5cf6' };
    return map[p] || '#6b7280';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Model Proxy</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Unified LLM provider interface with cost-aware routing and automatic failover</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setShowRoute(true)} style={{ padding: '8px 16px', background: '#6b7280', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Route Request</button>
          <button onClick={() => setShowRegister(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>+ Register Model</button>
        </div>
      </div>

      {stats && (
        <>
          <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
            <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_models}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Models</div>
            </div>
            <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_providers}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Providers</div>
            </div>
            <div style={{ flex: 1, background: '#fef3c7', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#d97706' }}>{stats.total_requests}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Requests</div>
            </div>
            <div style={{ flex: 1, background: '#faf5ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{(stats.success_rate * 100).toFixed(0)}%</div>
              <div style={{ fontSize: 12, color: '#666' }}>Success Rate</div>
            </div>
            <div style={{ flex: 1, background: '#fdf2f8', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#db2777' }}>${stats.total_cost.toFixed(4)}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Total Cost</div>
            </div>
          </div>

          {/* Model Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
            {stats.models.map(model => (
              <div key={model.model_id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{model.model_name}</div>
                    <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#888' }}>{model.model_id}</div>
                  </div>
                  <span style={{ background: providerColor(model.provider), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{model.provider}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12, color: '#666', marginBottom: 8 }}>
                  <div>Health: <strong style={{ color: model.health_score > 0.7 ? '#16a34a' : '#ef4444' }}>{(model.health_score * 100).toFixed(0)}%</strong></div>
                  <div>Success: <strong>{(model.success_rate * 100).toFixed(0)}%</strong></div>
                  <div>Load: <strong>{model.current_load}</strong></div>
                  <div>Latency: <strong>{model.avg_latency_ms}ms</strong></div>
                  <div>Cost: <strong>${model.cost_per_1k}/1k</strong></div>
                  <div>Status: <strong style={{ color: model.is_available ? '#16a34a' : '#ef4444' }}>{model.is_available ? 'Available' : 'Offline'}</strong></div>
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {model.capabilities.map(cap => (
                    <span key={cap} style={{ background: '#eff6ff', color: '#2563eb', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{cap.replace(/_/g, ' ')}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Route Result */}
      {routeResult && (
        <div style={{ position: 'fixed', bottom: 24, right: 24, background: '#fff', borderRadius: 12, padding: 16, boxShadow: '0 4px 20px rgba(0,0,0,0.15)', maxWidth: 400, zIndex: 900 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontWeight: 600 }}>Route Result</span>
            <button onClick={() => setRouteResult(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: 16 }}>x</button>
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>
            <div>Model: <strong>{routeResult.model_id}</strong></div>
            <div>Provider: <strong style={{ color: providerColor(routeResult.provider) }}>{routeResult.provider}</strong></div>
            <div>Latency: <strong>{routeResult.latency_ms}ms</strong></div>
            <div>Cost: <strong>${routeResult.cost.toFixed(6)}</strong></div>
            {routeResult.is_fallback && <div style={{ color: '#f59e0b' }}>Fallback route used</div>}
            <div style={{ marginTop: 8, padding: 8, background: '#f8fafc', borderRadius: 8 }}>{routeResult.content}</div>
          </div>
        </div>
      )}

      {/* Register Modal */}
      {showRegister && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 450, maxHeight: '80vh', overflow: 'auto' }}>
            <h3 style={{ marginBottom: 16 }}>Register Model</h3>
            <div style={{ display: 'grid', gap: 10 }}>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Model ID</label><input value={formData.model_id} onChange={e => setFormData({ ...formData, model_id: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Provider</label><select value={formData.provider} onChange={e => setFormData({ ...formData, provider: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }}>{['openai', 'anthropic', 'local', 'together', 'groq', 'custom'].map(p => <option key={p}>{p}</option>)}</select></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Model Name</label><input value={formData.model_name} onChange={e => setFormData({ ...formData, model_name: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Capabilities (comma-separated)</label><input value={formData.capabilities} onChange={e => setFormData({ ...formData, capabilities: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Cost/1k tokens</label><input type="number" step="0.0001" value={formData.cost_per_1k} onChange={e => setFormData({ ...formData, cost_per_1k: parseFloat(e.target.value) })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
                <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Max Tokens</label><input type="number" value={formData.max_tokens} onChange={e => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button onClick={() => setShowRegister(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={registerModel} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Register</button>
            </div>
          </div>
        </div>
      )}

      {/* Route Modal */}
      {showRoute && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 450 }}>
            <h3 style={{ marginBottom: 16 }}>Route Request</h3>
            <div style={{ display: 'grid', gap: 10 }}>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Query</label><textarea value={routeForm.query} onChange={e => setRouteForm({ ...routeForm, query: e.target.value })} rows={3} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', resize: 'vertical' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Strategy</label><select value={routeForm.strategy} onChange={e => setRouteForm({ ...routeForm, strategy: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }}>{['cost_optimal', 'performance', 'capability_match', 'round_robin', 'least_loaded'].map(s => <option key={s}>{s.replace(/_/g, ' ')}</option>)}</select></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Required Capabilities</label><input value={routeForm.required_capabilities} onChange={e => setRouteForm({ ...routeForm, required_capabilities: e.target.value })} placeholder="text_generation, code_generation" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button onClick={() => setShowRoute(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={routeRequest} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Route</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};